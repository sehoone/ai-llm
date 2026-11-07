"""chat 도메인 서비스 — 그래프 구동 + 승인(HITL) 조율 (ADR-0008).

도메인 책임(ADR-0005): HTTP 경계·영속·인가. AI 연산·정책은 engine에 위임한다.
- interrupt(승인 필요) → SSE `approval_required`로 변환 + `chat_approval` 영속.
- 사용자 승인 POST → 소유자·PENDING·만료 검증 후 `Command(resume=…)`로 재개.
"""

from __future__ import annotations

import base64
import json
import logging
import uuid
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from sqlmodel import Session

from src.core.config import settings
from src.core.storage import FileStorage
from src.domains.chat.model import ApprovalStatus, ChatSession
from src.domains.chat.repository import ChatRepository
from src.domains.chat.schema import (
    ALL_SUPPORTED_TYPES,
    MAX_FILE_SIZE,
    SUPPORTED_IMAGE_TYPES,
    SUPPORTED_TEXT_TYPES,
    ApprovalDecision,
    FileAttachment,
)
from src.domains.artifact.repository import ArtifactRepository
from src.domains.llm_resource.model import LlmResource
from src.domains.llm_resource.repository import LlmResourceRepository
from src.domains.rag.service import RagService
from src.domains.user.model import User, UserRole
from src.engine.artifact import ArtifactStreamParser, EventType
from src.engine.agent.policy import ApprovalPolicy
from src.engine.agent.tools import default_registry
from src.engine.graph.chat_graph import build_chat_graph
from src.engine.graph.checkpointer import build_checkpointer
from src.engine.graph.fake_model import FakeToolCallingModel
from src.engine.llm import build_default_chat_model, build_model_for, generate_title
from src.engine.llm.config import LlmConfig

logger = logging.getLogger(__name__)


def _build_default_model():
    """실 LLM(설정 시) 또는 FakeToolCallingModel(폴백) — ADR-0010 §3.

    키가 있으면 실 LLM, 없거나 조립 실패 시 결정적 데모 모델로 안전 폴백(로컬·CI·HITL 테스트 불변).
    """
    if settings.llm_is_configured:
        try:
            model = build_default_chat_model()
            if model is not None:
                logger.info(
                    "chat_model_real_llm", extra={"provider": settings.llm_provider, "model": settings.llm_model}
                )
                return model
        except Exception:
            logger.exception("chat_model_real_llm_init_failed_falling_back_to_fake")
    else:
        logger.info("chat_model_fake_fallback_llm_not_configured")
    return FakeToolCallingModel()


_default_model = _build_default_model()
# per-request 모델 캐시 (LlmConfig는 frozen → 해시 가능). ADR-0011 §4.
_model_cache: dict[LlmConfig, Any] = {}


def _model_for_config(cfg: LlmConfig) -> Any:
    m = _model_cache.get(cfg)
    if m is None:
        m = build_model_for(cfg)
        _model_cache[cfg] = m
    return m


def _resolve_model(config: Any) -> Any:
    """config.configurable에 주입된 LlmConfig가 있으면 그 모델, 없으면 기본 모델 (ADR-0011 §4).

    도메인이 `llm_resource_id`를 해석해 LlmConfig를 주입한다(engine은 DB 미조회 — ADR-0005).
    """
    cfg = (config or {}).get("configurable", {}).get("llm_config")
    if cfg is not None:
        try:
            return _model_for_config(cfg)
        except Exception:
            logger.exception("per_request_model_build_failed_falling_back_to_default")
    return _default_model


def _config_from_resource(r: LlmResource) -> LlmConfig:
    """llm_resource 행 → LlmConfig (azure는 deployment_name을 model로)."""
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


# ── engine 조립 (프로세스 단일) ──
# InMemorySaver는 인프로세스 상태를 유지하므로 그래프는 모듈 싱글턴으로 둔다(ADR-0008 §2).
# model은 리졸버 — 요청별 주입된 LlmConfig를 해석(ADR-0011 §4).
_registry = default_registry()
_policy = ApprovalPolicy(_registry)
_graph = build_chat_graph(
    model=_resolve_model,
    registry=_registry,
    policy=_policy,
    checkpointer=build_checkpointer(settings.chat_checkpointer),
)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _chunk_text(chunk: Any) -> str:
    """`stream_mode="messages"` 조각에서 assistant 토큰 텍스트를 뽑는다(ADR-0011 §2).

    chunk은 `(message_chunk, metadata)`. AIMessage(청크)만 대상으로 하고, content가 블록 리스트인
    provider도 text만 모은다.
    """
    try:
        msg_chunk, _meta = chunk
    except (TypeError, ValueError):
        return ""
    if not isinstance(msg_chunk, AIMessage):
        return ""
    content = msg_chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for p in content:
            if isinstance(p, str):
                parts.append(p)
            elif isinstance(p, dict) and p.get("type") == "text":
                parts.append(str(p.get("text", "")))
        return "".join(parts)
    return ""


def _auto_approve_for(role: UserRole) -> frozenset[str]:
    """역할 기반 CONFIRM 면제 목록. 현재는 없음(모두 승인 요구) — 정책 확장 지점."""
    return frozenset()


def _build_graph_content(text: str, files: list[FileAttachment] | None) -> Any:
    """파일이 있으면 멀티모달 블록 리스트, 없으면 텍스트 (ADR-0014 §3)."""
    if not files:
        return text
    parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for f in files:
        if f.content_type in SUPPORTED_IMAGE_TYPES:
            parts.append(
                {"type": "image_url", "image_url": {"url": f"data:{f.content_type};base64,{f.data}"}}
            )
        elif f.content_type in SUPPORTED_TEXT_TYPES:
            try:
                decoded = base64.b64decode(f.data).decode("utf-8", errors="replace")
            except Exception:
                decoded = ""
            parts.append(
                {"type": "text", "text": f"\n\n--- {f.filename} ---\n{decoded}\n--- end of {f.filename} ---"}
            )
        else:  # PDF 등 — 추출 미구현(placeholder, V2 동일)
            parts.append(
                {"type": "text", "text": f"\n\n[PDF attached: {f.filename}. Content extraction not implemented.]"}
            )
    return parts


class ChatService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = ChatRepository(session)

    # ── 세션/메시지 조회 ──
    def create_session(self, user: User, title: str | None) -> ChatSession:
        return self.repo.create_session(user.id, title or "New chat")

    def list_sessions(self, user: User) -> list[ChatSession]:
        return self.repo.list_sessions(user.id)

    def rename_session(self, session_id: int, user: User, title: str) -> ChatSession:
        s = self.get_session_owned(session_id, user)
        return self.repo.rename_session(s, title)

    def delete_session(self, session_id: int, user: User) -> None:
        s = self.get_session_owned(session_id, user)
        storage = FileStorage()
        for att in self.repo.list_session_attachments(s.id):
            storage.delete(att.storage_path)  # 파일 정리 (메타는 repo가 삭제)
        self.repo.delete_session(s)

    def get_session_owned(self, session_id: int, user: User) -> ChatSession:
        s = self.repo.get_session(session_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if s.user_id != user.id and user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            raise HTTPException(status_code=403, detail="Not your chat session")
        return s

    def messages(self, session_id: int, user: User) -> list:
        self.get_session_owned(session_id, user)
        return self.repo.list_messages(session_id)

    def attachments_for(self, message_ids: list[int]) -> dict:
        """메시지 id별 첨부 메타 (배치 조회) — ADR-0014."""
        return self.repo.attachments_by_message_ids(message_ids)

    def download_attachment(self, user: User, attachment_id: int) -> tuple:
        """다운로드용 (절대경로, filename, content_type). 소유자 또는 관리자만 (ADR-0014 §4)."""
        att = self.repo.get_attachment(attachment_id)
        if att is None:
            raise HTTPException(status_code=404, detail="Attachment not found")
        if user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
            session = self.repo.get_session(att.session_id)
            if session is None or session.user_id != user.id:
                raise HTTPException(status_code=403, detail="Access denied")
        path = FileStorage().absolute_path(att.storage_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found on server")
        return path, att.filename, att.content_type

    # ── 메시지 전송 (SSE) ──
    def stream_message(
        self,
        session_id: int,
        user: User,
        content: str,
        llm_resource_id: int | None = None,
        rag_group: str | None = None,
        files: list[FileAttachment] | None = None,
    ) -> Iterator[str]:
        session = self.get_session_owned(session_id, user)
        # 첫 왕복(이 턴 전 메시지 0건)이면 종료 후 제목 자동생성 (ADR-0011 §3).
        is_first = len(self.repo.list_messages(session.id)) == 0
        # 원문(clean)만 영속 — 사전 주입 컨텍스트·첨부 바이트는 그래프 입력/스토리지에만.
        user_msg = self.repo.add_message(session.id, "user", content)
        self._persist_attachments(session, user_msg.id, files)
        llm_config = self._resolve_llm_config(llm_resource_id)
        text = self._augment_with_rag(user, content, rag_group)
        graph_content = _build_graph_content(text, files)  # 파일 있으면 멀티모달 (ADR-0014)
        graph_input: Any = {"messages": [HumanMessage(content=graph_content)]}
        yield from self._run(
            session, user, graph_input, user_content=content, is_first=is_first, llm_config=llm_config
        )

    def _persist_attachments(
        self, session: ChatSession, message_id: int, files: list[FileAttachment] | None
    ) -> None:
        """첨부 검증·저장·메타 영속 (ADR-0014)."""
        if not files:
            return
        storage = FileStorage()
        for f in files:
            if f.content_type not in ALL_SUPPORTED_TYPES:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {f.content_type}")
            storage_path, size = storage.save_base64(f.data, session.id, f.filename)
            if size > MAX_FILE_SIZE:
                storage.delete(storage_path)
                raise HTTPException(
                    status_code=400, detail=f"File {f.filename} exceeds {MAX_FILE_SIZE // (1024 * 1024)}MB"
                )
            self.repo.add_attachment(
                message_id=message_id,
                session_id=session.id,
                filename=f.filename,
                content_type=f.content_type,
                file_size=size,
                storage_path=storage_path,
            )

    def _augment_with_rag(self, user: User, content: str, rag_group: str | None) -> str:
        """rag_group이 있으면 검색 컨텍스트를 사전 주입 (ADR-0012 §1). 결과 없으면 원문 그대로."""
        if not rag_group:
            return content
        context = RagService(self.session).rag_context(user, rag_group, content)
        if not context:
            return content
        return f"{content}\n\nContext from knowledge base:\n{context}"

    def _resolve_llm_config(self, llm_resource_id: int | None) -> LlmConfig | None:
        """요청의 llm_resource_id → LlmConfig. 없음/비활성/비chat이면 None(기본 모델) — ADR-0011 §4."""
        if llm_resource_id is None:
            return None
        resource = LlmResourceRepository(self.session).get(llm_resource_id)
        if resource is None or not resource.is_active or resource.resource_type != "chat":
            return None
        return _config_from_resource(resource)

    # ── 승인 결정 → 재개 (SSE) ──
    def resume(self, session_id: int, user: User, group_key: str, decisions: list[ApprovalDecision]) -> Iterator[str]:
        session = self.get_session_owned(session_id, user)
        pending = {row.tool_call_id: row for row in self.repo.pending_by_group(session.id, group_key)}
        if not pending:
            raise HTTPException(status_code=409, detail="No pending approvals for this group")

        now = datetime.utcnow()
        decision_map: dict[str, dict[str, Any]] = {}
        for d in decisions:
            row = pending.get(d.tool_call_id)
            if row is None:
                continue  # 알 수 없는 tool_call_id는 무시
            if row.expires_at and row.expires_at < now:
                self.repo.mark(row, ApprovalStatus.EXPIRED, user.id)
                decision_map[d.tool_call_id] = {"approved": False, "reason": "만료됨"}
                continue
            approved = d.approved
            args = d.args if (row.allow_edit and d.args) else row.args
            self.repo.mark(
                row,
                ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED,
                user.id,
            )
            decision_map[d.tool_call_id] = {
                "approved": approved,
                "args": args,
                "reason": None if approved else "사용자 거부",
            }

        # 결정 누락된 PENDING은 거부로 마킹 (fail-safe, ADR-0008 §5)
        for tool_call_id, row in pending.items():
            if tool_call_id not in decision_map:
                self.repo.mark(row, ApprovalStatus.REJECTED, user.id)
                decision_map[tool_call_id] = {"approved": False, "reason": "미결정(기본 거부)"}

        yield from self._run(session, user, Command(resume=decision_map))

    # ── 공통 그래프 실행 루프 (토큰 스트리밍 + HITL + 제목, ADR-0011) ──
    def _run(
        self,
        session: ChatSession,
        user: User,
        graph_input: Any,
        *,
        user_content: str | None = None,
        is_first: bool = False,
        llm_config: LlmConfig | None = None,
    ) -> Iterator[str]:
        configurable: dict[str, Any] = {
            "thread_id": str(session.id),
            "role": str(user.role),
            "auto_approve_tools": list(_auto_approve_for(user.role)),
        }
        if llm_config is not None:
            configurable["llm_config"] = llm_config  # 리졸버가 해석 (ADR-0011 §4)
        config = {"configurable": configurable}

        # 아티팩트 파서(ADR-0013): assistant 토큰을 chat 본문과 아티팩트 이벤트로 가른다.
        parser = ArtifactStreamParser()
        art_repo = ArtifactRepository(self.session)
        display_parts: list[str] = []          # 칩 포함 chat 본문(영속·제목용)
        created_version_rows: list[int] = []   # 이번 assistant 턴에 생성된 아티팩트 버전 행
        current_artifact: dict[str, Any] | None = None
        streamed_any = False                   # 현재 assistant 턴에 토큰이 흘렀는지(fake 폴백 판정)
        full_answer = ""                       # 전체 답변(제목 입력)

        def _emit(events: Any) -> Iterator[str]:
            """파서 이벤트 → SSE. ARTIFACT_END에서 버전 영속."""
            nonlocal current_artifact
            for ev in events:
                if ev.type is EventType.CONTENT:
                    display_parts.append(ev.text)
                    yield _sse("content", {"delta": ev.text})
                elif ev.type is EventType.ARTIFACT_START:
                    current_artifact = {
                        "identifier": ev.identifier or "artifact",
                        "type": ev.artifact_type or "text/markdown",
                        "title": ev.title or "",
                        "content": "",
                    }
                    label = current_artifact["title"] or current_artifact["identifier"]
                    chip = f"\n\n[📎 {label}](artifact:{current_artifact['identifier']})\n\n"
                    display_parts.append(chip)  # 버블엔 칩만, 본문은 캔버스로
                    yield _sse("content", {"delta": chip})
                    yield _sse(
                        "artifact_start",
                        {
                            "identifier": current_artifact["identifier"],
                            "artifact_type": current_artifact["type"],
                            "title": current_artifact["title"],
                        },
                    )
                elif ev.type is EventType.ARTIFACT_DELTA:
                    if current_artifact is not None:
                        current_artifact["content"] += ev.text
                    yield _sse(
                        "artifact_delta",
                        {
                            "identifier": current_artifact["identifier"] if current_artifact else None,
                            "delta": ev.text,
                        },
                    )
                elif ev.type is EventType.ARTIFACT_END:
                    version = None
                    ident = None
                    if current_artifact is not None:
                        ident = current_artifact["identifier"]
                        try:
                            res = art_repo.upsert_version(
                                session_id=session.id,
                                user_id=user.id,
                                identifier=ident,
                                artifact_type=current_artifact["type"],
                                title=current_artifact["title"],
                                content=current_artifact["content"],
                            )
                            created_version_rows.append(res["version_row_id"])
                            version = res["version"]
                        except Exception:
                            logger.exception("artifact_persist_failed")
                    current_artifact = None
                    yield _sse("artifact_end", {"identifier": ident, "version": version})

        try:
            for mode, chunk in _graph.stream(graph_input, config=config, stream_mode=["updates", "messages"]):
                if mode == "messages":
                    text = _chunk_text(chunk)
                    if text:
                        streamed_any = True
                        yield from _emit(parser.feed(text))
                    continue

                # mode == "updates"
                if "__interrupt__" in chunk:
                    payload = chunk["__interrupt__"][0].value
                    group_key = uuid.uuid4().hex
                    self.repo.save_approvals(
                        session.id,
                        user.id,
                        group_key,
                        payload["requests"],
                        settings.chat_approval_ttl_seconds,
                    )
                    yield _sse("approval_required", {"group_key": group_key, **payload})
                    return  # 스트림 종료 → 승인 POST로 재개

                for update in chunk.values():
                    if not isinstance(update, dict):
                        continue
                    for msg in update.get("messages", []) or []:
                        if isinstance(msg, AIMessage):
                            # 토큰이 안 나온 모델(fake)은 완결본을 파서에 통과시킨다.
                            if not streamed_any:
                                yield from _emit(parser.feed(msg.content or ""))
                            yield from _emit(parser.flush())
                            display = "".join(display_parts)
                            full_answer += display
                            tool_calls = getattr(msg, "tool_calls", None) or None
                            saved = self.repo.add_message(session.id, "assistant", display, tool_calls)
                            if created_version_rows:
                                try:
                                    art_repo.set_versions_message_id(created_version_rows, saved.id)
                                except Exception:
                                    logger.exception("artifact_link_failed")
                            # 다음 assistant 턴(툴 루프) 대비 리셋
                            parser = ArtifactStreamParser()
                            display_parts = []
                            created_version_rows = []
                            current_artifact = None
                            streamed_any = False
                        else:  # ToolMessage 등
                            self.repo.add_message(session.id, "tool", msg.content or "", None)
                            yield _sse("message", {"role": "tool", "content": msg.content, "tool_calls": None})

            # 스트림 정상 종료 — 첫 대화면 제목 자동생성 (ADR-0011 §3).
            if is_first and user_content and full_answer.strip():
                title = self._maybe_generate_title(session, user_content, full_answer)
                if title:
                    yield _sse("title", {"title": title})
            yield _sse("done", {"session_id": session.id})
        except Exception as e:  # noqa: BLE001 — SSE로 오류 통지 후 종료
            logger.exception("chat_stream_failed")
            yield _sse("error", {"detail": str(e)})

    def _maybe_generate_title(self, session: ChatSession, user_content: str, answer: str) -> str | None:
        """첫 대화 제목 생성 + 세션에 반영. 미구성/실패 시 None."""
        if not settings.llm_is_configured:
            return None
        title = generate_title(user_content, answer)
        if title:
            self.repo.rename_session(session, title)
            return title
        return None
