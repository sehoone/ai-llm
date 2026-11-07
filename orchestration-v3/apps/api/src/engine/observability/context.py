"""트레이스 컨텍스트 값 객체 (ADR-0007).

LLM 트레이스에 붙일 호출 컨텍스트. **도메인(HTTP 경계)이 생성해 engine에 값으로 주입**한다.
engine은 요청/인증 상태를 직접 읽지 않는다(ADR-0005 §4 — ModelConfig 주입과 동일 패턴).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TraceContext:
    """단일 LLM 실행에 귀속되는 관측 컨텍스트.

    - `user_id`: 로컬 `users.id` (IdP sub가 아님).
    - `session_id`: 대화/실행 세션 식별자 (chat 세션 등).
    - `tags`: Langfuse 트레이스 태그.
    - `extra`: 트레이스 metadata에 그대로 병합할 추가 키.
    """

    user_id: int | None = None
    session_id: str | None = None
    tags: tuple[str, ...] = ()
    extra: dict[str, str] = field(default_factory=dict)
