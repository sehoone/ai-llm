"""MCP 커넥터 로더 (ADR-0022) — 사내 MCP 서버의 tool을 ToolSpec으로 래핑.

engine 규칙(ADR-0005): domains·FastAPI 비의존. 서버 좌표·토큰은 도메인이 값으로 주입한다.

도구 위험도(ADR-0008 §1): MCP 도구는 외부 부수효과이므로 **기본 CONFIRM**(HITL 경유). 큐레이션으로만
AUTO 승격(후속). MCP 클라이언트는 선택 의존성(`langchain-mcp-adapters`)이며, 미설치·연결 실패 시
빈 목록으로 degrade해 챗을 막지 않는다(RAG degrade와 동일 철학).

NOTE(통합 현황): 현재 chat 그래프는 모듈 싱글턴이고 실모델에 도구를 bind하지 않는다(_registry만
사용, FakeToolCallingModel 경로). 로드된 커넥터 도구를 라이브 대화에 실제로 노출하려면
① MCP 클라이언트 의존성 추가, ② per-request 모델 bind_tools, ③ 그래프의 per-request registry/policy
해석이 필요하다. 본 모듈은 ①의 로더 seam을 제공한다 — 그래프 wiring은 후속(ADR-0022 후속 작업).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.engine.agent.registry import RiskTier, ToolSpec

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class McpServer:
    """MCP 서버 접속 좌표 — 도메인이 connector 행에서 주입."""

    url: str
    token: str | None = None
    name: str = ""


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _run_async(coro: Any) -> Any:
    """동기 컨텍스트(FastAPI 스레드풀/그래프 tools 노드)에서 async 호출 실행."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # 이미 러닝 루프 안이면 별도 루프로 실행(드문 경로).
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def load_mcp_specs(servers: Sequence[McpServer]) -> list[ToolSpec]:
    """여러 MCP 서버의 도구를 ToolSpec 목록으로 로드. 이름 충돌·실패는 건너뛴다.

    `langchain-mcp-adapters` 미설치 시 빈 목록을 반환(로그만). 각 도구는 CONFIRM 티어.
    """
    if not servers:
        return []
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore
    except ImportError:
        logger.warning("mcp_adapters_not_installed — 커넥터 도구 로드 생략(langchain-mcp-adapters 필요)")
        return []

    connections: dict[str, dict[str, Any]] = {}
    for i, s in enumerate(servers):
        if not s.url:
            continue
        key = s.name or f"mcp_{i}"
        connections[key] = {"transport": "streamable_http", "url": s.url, "headers": _headers(s.token)}
    if not connections:
        return []

    try:
        client = MultiServerMCPClient(connections)
        tools = _run_async(client.get_tools())
    except Exception:
        logger.exception("mcp_tools_load_failed")
        return []

    specs: list[ToolSpec] = []
    seen: set[str] = set()
    for tool in tools:
        name = getattr(tool, "name", None)
        if not name or name in seen:
            continue
        seen.add(name)
        specs.append(
            ToolSpec(
                name=name,
                description=getattr(tool, "description", "") or "",
                handler=_make_handler(tool),
                risk=RiskTier.CONFIRM,  # 외부 부수효과 — HITL 경유 (ADR-0008 §1)
                allow_edit=True,
            )
        )
    return specs


def _make_handler(tool: Any):
    """LangChain MCP 도구 → 동기 handler(그래프 tools 노드가 sync 호출)."""

    def handler(**kwargs: Any) -> str:
        try:
            return str(tool.invoke(kwargs))
        except Exception as e:  # noqa: BLE001 — 도구 오류를 모델에 되돌려 복구 기회
            return f"[오류] MCP 도구 실행 실패: {e}"

    return handler
