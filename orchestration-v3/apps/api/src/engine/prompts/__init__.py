"""prompts: 프롬프트 템플릿 (Git 버전관리, 로직과 분리) + 로더 — ADR-0005.

`system.md`를 읽어 플레이스홀더를 렌더한다. 본문에 리터럴 중괄호(코드/JSON 예시)가 있을 수 있어
모든 중괄호를 이스케이프한 뒤 알려진 플레이스홀더만 복원해 `str.format`에 넘긴다(V2 로더 계승).

engine 모듈 — `domains`·FastAPI 비의존(ADR-0005).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_SYSTEM_MD = Path(__file__).parent / "system.md"

# Phase 0 기본 에이전트명 (설정화는 후속).
_DEFAULT_AGENT_NAME = "LLM Orchestration Agent"


def load_system_prompt(*, agent_name: str | None = None, long_term_memory: str = "", **kwargs: str) -> str:
    """시스템 프롬프트를 렌더해 반환 (ADR-0010 §4).

    Args:
        agent_name: 에이전트 표시명(기본값 사용 가능).
        long_term_memory: 장기 메모리 블록(Phase 5 전까지 빈 문자열).
        **kwargs: 추가 플레이스홀더(이름=값).
    """
    values: dict[str, str] = {
        "agent_name": agent_name or _DEFAULT_AGENT_NAME,
        "current_date_and_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "long_term_memory": long_term_memory,
        **kwargs,
    }
    placeholders = set(values)

    text = _SYSTEM_MD.read_text(encoding="utf-8")
    # 리터럴 중괄호 보호 → 알려진 플레이스홀더만 복원.
    text = text.replace("{", "{{").replace("}", "}}")
    for key in placeholders:
        text = text.replace("{{" + key + "}}", "{" + key + "}")

    return text.format(**values)


__all__ = ["load_system_prompt"]
