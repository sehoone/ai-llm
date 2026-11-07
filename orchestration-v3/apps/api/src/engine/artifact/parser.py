"""토큰 스트림을 chat 본문과 아티팩트 이벤트로 가르는 스트리밍 상태머신 (ADR-0013 §1).

LLM은 자립적 산출물을 인라인 태그로 감싼다:

    <artifact identifier="sales-dashboard" type="text/html" title="매출 대시보드">
    ...content...
    </artifact>

토큰 스트림이라 여는/닫는 태그가 임의 청크 경계에서 쪼개질 수 있다. 이 파서는 형성 중일 수 있는
태그의 최소 꼬리만 버퍼링하고, 호출자가 SSE로 바꿀 평면 이벤트열을 방출한다. (V2 계승 — 순수·DB 무의존)
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum

OPEN_PREFIX = "<artifact"
CLOSE_TOKEN = "</artifact>"

# 완전히 버퍼된 여는 태그의 속성 파싱: <artifact identifier="x" type="text/html" title="제목">
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


class EventType(str, Enum):
    CONTENT = "content"
    ARTIFACT_START = "artifact_start"
    ARTIFACT_DELTA = "artifact_delta"
    ARTIFACT_END = "artifact_end"


@dataclass
class ParserEvent:
    """분류된 스트림 한 단위."""

    type: EventType
    text: str = ""
    identifier: str | None = None
    artifact_type: str | None = None
    title: str | None = None


class _State(str, Enum):
    OUTSIDE = "outside"
    INSIDE = "inside"


def _longest_suffix_prefix(s: str, token: str) -> int:
    """`s`의 접미사이면서 `token`의 접두사인 최장 길이. 다음 청크로 이어질 수 있는 꼬리를 얼마나 쥐고 있을지 결정."""
    max_k = min(len(s), len(token) - 1)
    for k in range(max_k, 0, -1):
        if s[-k:] == token[:k]:
            return k
    return 0


class ArtifactStreamParser:
    """raw LLM 청크를 넣으면 분류된 `ParserEvent`를 낸다. 스트림당 인스턴스 1개(스레드 비안전)."""

    def __init__(self) -> None:
        self._buffer = ""
        self._state = _State.OUTSIDE

    def feed(self, chunk: str) -> Iterator[ParserEvent]:
        """청크를 소비하고 완전히 해소되는 이벤트를 방출."""
        if not chunk:
            return
        self._buffer += chunk
        yield from self._drain(final=False)

    def flush(self) -> Iterator[ParserEvent]:
        """상류 스트림 종료 시 남은 것을 방출. 미종료 아티팩트는 닫아 클라가 대기하지 않게 한다."""
        yield from self._drain(final=True)
        if self._buffer:
            if self._state is _State.OUTSIDE:
                yield ParserEvent(EventType.CONTENT, text=self._buffer)
            else:
                yield ParserEvent(EventType.ARTIFACT_DELTA, text=self._buffer)
            self._buffer = ""
        # 닫는 태그가 누락된 아티팩트도 END를 내 항상 영속되게 한다.
        if self._state is _State.INSIDE:
            yield ParserEvent(EventType.ARTIFACT_END)
            self._state = _State.OUTSIDE

    # ── internals ──
    def _drain(self, final: bool) -> Iterator[ParserEvent]:
        while True:
            before = (self._state, len(self._buffer))
            if self._state is _State.OUTSIDE:
                yield from self._drain_outside(final)
            else:
                yield from self._drain_inside(final)
            if (self._state, len(self._buffer)) == before:
                break

    def _drain_outside(self, final: bool) -> Iterator[ParserEvent]:
        idx = self._buffer.find(OPEN_PREFIX)

        if idx == -1:
            hold = 0 if final else _longest_suffix_prefix(self._buffer, OPEN_PREFIX)
            emit_len = len(self._buffer) - hold
            if emit_len > 0:
                yield ParserEvent(EventType.CONTENT, text=self._buffer[:emit_len])
                self._buffer = self._buffer[emit_len:]
            return

        if idx > 0:
            yield ParserEvent(EventType.CONTENT, text=self._buffer[:idx])
            self._buffer = self._buffer[idx:]

        gt = self._buffer.find(">")
        if gt == -1:
            return  # 더 많은 토큰 대기

        open_tag = self._buffer[: gt + 1]
        attrs = dict(_ATTR_RE.findall(open_tag))

        # 오탐 방지: 모델은 identifier와 type을 항상 넣도록 지시됨. 둘 다 없으면 산문 속 "<artifact…>"로 간주.
        if not attrs.get("identifier") and not attrs.get("type"):
            yield ParserEvent(EventType.CONTENT, text=open_tag)
            self._buffer = self._buffer[gt + 1 :]
            return

        self._buffer = self._buffer[gt + 1 :]
        self._state = _State.INSIDE
        yield ParserEvent(
            EventType.ARTIFACT_START,
            identifier=attrs.get("identifier"),
            artifact_type=attrs.get("type"),
            title=attrs.get("title"),
        )

    def _drain_inside(self, final: bool) -> Iterator[ParserEvent]:
        idx = self._buffer.find(CLOSE_TOKEN)

        if idx == -1:
            hold = 0 if final else _longest_suffix_prefix(self._buffer, CLOSE_TOKEN)
            emit_len = len(self._buffer) - hold
            if emit_len > 0:
                yield ParserEvent(EventType.ARTIFACT_DELTA, text=self._buffer[:emit_len])
                self._buffer = self._buffer[emit_len:]
            return

        if idx > 0:
            yield ParserEvent(EventType.ARTIFACT_DELTA, text=self._buffer[:idx])
        self._buffer = self._buffer[idx + len(CLOSE_TOKEN) :]
        self._state = _State.OUTSIDE
        yield ParserEvent(EventType.ARTIFACT_END)
