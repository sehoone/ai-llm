"""gpts 도메인 서비스 — 커스텀 GPT CRUD·세션·채팅 (V2 포팅).

도메인 책임(ADR-0005): HTTP 경계·인가·관계형 영속. AI 연산(모델 조립·토큰 스트리밍)은
engine/llm에 위임하고, 관측 컨텍스트는 engine/observability에 값으로 주입한다.

GPT 채팅은 도구·HITL 없는 단순 Q/A다 — chat 도메인의 승인 그래프(ADR-0008)를 쓰지 않고
`engine/llm`의 직접 토큰 스트리밍(`LlmChatModel.stream`)으로 처리한다. `gpt.instructions`는
system prompt로 주입한다.

스트리밍 SSE는 현재 web(V2 기준)이 기대하는 `data: {content, done, type?, title?}` 포맷을
따른다. web의 v3 재매핑(ADR-0011 event 포맷) 시 함께 정렬한다.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from sqlmodel import Session

from src.core.config import settings
from src.core.exceptions import NotFoundError, PermissionDeniedError
from src.domains.gpts.model import CustomGpt, GptSession
from src.domains.gpts.repository import GptsRepository
from src.domains.gpts.schema import (
    CustomGptCreateRequest,
    CustomGptUpdateRequest,
    GptMessage,
)
from src.engine.llm import build_chat_model, generate_title
from src.engine.llm.config import LlmConfig
from src.engine.observability import TraceContext, build_run_config
from src.platform.authz import assert_owner_or_admin
from src.platform.llm_resource.model import LlmResource
from src.platform.llm_resource.repository import LlmResourceRepository
from src.platform.user.model import User, UserRole

logger = logging.getLogger(__name__)


def _config_from_resource(r: LlmResource) -> LlmConfig:
    """llm_resource 행 → LlmConfig (azure는 deployment_name을 model로). chat 도메인과 동일 규칙."""
    model = r.deployment_name if r.provider == "azure" else (r.model_name or r.name)
    return LlmConfig(
        provider=r.provider,
        model=model or r.name,
        api_key=r.api_key or None,
        api_base=r.api_base or None,
        api_version=r.api_version or None,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens or None,
    )


def _sse(data: dict[str, Any]) -> str:
    """V2 호환 SSE 프레임 — web `createSSEProgressHandler`가 `data: {json}`을 파싱한다."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


class GptsService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = GptsRepository(session)

    # ── CustomGPT CRUD ──
    def create_gpt(self, user: User, req: CustomGptCreateRequest) -> CustomGpt:
        gpt = CustomGpt(
            user_id=user.id,
            name=req.name,
            description=req.description,
            instructions=req.instructions,
            rag_key=req.rag_key or f"gpt_{uuid.uuid4().hex}",
            is_public=req.is_public,
            model=req.model or "gpt-4o-mini",
        )
        return self.repo.create_gpt(gpt)

    def list_gpts(self, user: User) -> list[CustomGpt]:
        return self.repo.list_gpts(user.id)

    def get_readable_gpt(self, gpt_id: str, user: User) -> CustomGpt:
        """조회 접근: 공개 GPT는 누구나, 비공개는 소유자/관리자만."""
        gpt = self.repo.get_gpt(gpt_id)
        if gpt is None:
            raise NotFoundError("Custom GPT not found")
        if (
            not gpt.is_public
            and gpt.user_id != user.id
            and user.role
            not in (
                UserRole.ADMIN,
                UserRole.SUPERADMIN,
            )
        ):
            raise PermissionDeniedError("Access denied")
        return gpt

    def _get_owned_gpt(self, gpt_id: str, user: User) -> CustomGpt:
        """수정/삭제 접근: 소유자/관리자만."""
        gpt = self.repo.get_gpt(gpt_id)
        if gpt is None:
            raise NotFoundError("Custom GPT not found")
        assert_owner_or_admin(user, gpt.user_id, message="Custom GPT not found or access denied")
        return gpt

    def update_gpt(self, gpt_id: str, user: User, req: CustomGptUpdateRequest) -> CustomGpt:
        gpt = self._get_owned_gpt(gpt_id, user)
        for key, value in req.model_dump(exclude_unset=True).items():
            setattr(gpt, key, value)
        return self.repo.save_gpt(gpt)

    def delete_gpt(self, gpt_id: str, user: User) -> None:
        gpt = self._get_owned_gpt(gpt_id, user)
        self.repo.delete_gpt(gpt)

    # ── 세션 ──
    def create_session(self, gpt_id: str, user: User) -> GptSession:
        self.get_readable_gpt(gpt_id, user)
        s = GptSession(id=str(uuid.uuid4()), user_id=user.id, custom_gpt_id=gpt_id, name="")
        return self.repo.create_session(s)

    def list_sessions(self, gpt_id: str, user: User) -> list[GptSession]:
        self.get_readable_gpt(gpt_id, user)
        return self.repo.list_sessions(gpt_id, user.id)

    def _get_owned_session(self, session_id: str, gpt_id: str, user: User) -> GptSession:
        s = self.repo.get_session(session_id)
        if s is None or s.custom_gpt_id != gpt_id:
            raise NotFoundError("Session not found")
        assert_owner_or_admin(user, s.user_id, message="Cannot access other sessions")
        return s

    def rename_session(self, gpt_id: str, session_id: str, user: User, name: str) -> GptSession:
        s = self._get_owned_session(session_id, gpt_id, user)
        return self.repo.rename_session(s, name)

    def delete_session(self, gpt_id: str, session_id: str, user: User) -> None:
        s = self._get_owned_session(session_id, gpt_id, user)
        self.repo.delete_session(s)

    # ── 메시지 이력 ──
    def messages(self, gpt_id: str, session_id: str, user: User) -> list[GptMessage]:
        self._get_owned_session(session_id, gpt_id, user)
        out: list[GptMessage] = []
        for m in self.repo.list_messages(session_id):
            out.append(GptMessage(role="user", content=m.question))
            out.append(GptMessage(role="assistant", content=m.answer))
        return out

    def clear_messages(self, gpt_id: str, session_id: str, user: User) -> None:
        self._get_owned_session(session_id, gpt_id, user)
        self.repo.clear_messages(session_id)

    # ── 모델 해석 ──
    def _resolve_llm_config(self, llm_resource_id: int | None) -> LlmConfig | None:
        """요청 llm_resource_id → LlmConfig. 미지정/무효면 기본 chat 리소스. 없으면 None."""
        repo = LlmResourceRepository(self.session)
        resource: LlmResource | None = None
        if llm_resource_id is not None:
            r = repo.get(llm_resource_id)
            if r is not None and r.is_active and r.resource_type == "chat":
                resource = r
        if resource is None:
            resource = repo.default_chat_model()
        return _config_from_resource(resource) if resource is not None else None

    # ── 채팅 (SSE 스트리밍) ──
    def stream_chat(
        self,
        gpt_id: str,
        user: User,
        session_id: str,
        messages: list[GptMessage],
        llm_resource_id: int | None = None,
    ) -> Iterator[str]:
        gpt = self.get_readable_gpt(gpt_id, user)
        session = self._get_owned_session(session_id, gpt_id, user)

        cfg = self._resolve_llm_config(llm_resource_id)
        if cfg is None:
            yield _sse(
                {
                    "content": "활성 chat LLM 리소스가 없습니다. 관리자에게 LLM 리소스 등록을 요청하세요.",
                    "done": True,
                }
            )
            return

        last_user = messages[-1].content if messages else ""
        is_first = len(self.repo.list_messages(session_id)) == 0

        # gpt.instructions를 system prompt로 주입, 요청 대화 이력을 LLM 메시지로 변환.
        model = build_chat_model(cfg, system_prompt=gpt.instructions or None)
        lc_messages = [
            AIMessage(content=m.content)
            if m.role == "assistant"
            else HumanMessage(content=m.content)
            for m in messages
        ]
        # 관측(ADR-0007): 도메인이 컨텍스트 값 주입, 비활성 시 {} 반환.
        run_cfg = build_run_config(
            TraceContext(user_id=user.id, session_id=session_id, tags=("gpts",))
        )

        full_response = ""
        try:
            for token in model.stream(lc_messages, config=run_cfg or None):
                full_response += token
                yield _sse({"content": token, "done": False})

            if last_user and full_response:
                self.repo.add_message(session_id, last_user, full_response)
                # 첫 왕복이면 제목 자동생성 (ADR-0011 §3).
                if is_first:
                    title = generate_title(last_user, full_response, config=cfg)
                    if title:
                        self.repo.rename_session(session, title)
                        yield _sse({"content": "", "done": False, "type": "title", "title": title})

            yield _sse({"content": "", "done": True})
        except Exception as e:  # noqa: BLE001 — SSE로 오류 통지 후 종료
            logger.exception("gpt_stream_chat_failed")
            yield _sse({"content": str(e), "done": True})
