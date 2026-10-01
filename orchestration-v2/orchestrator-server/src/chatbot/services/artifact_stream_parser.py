"""Streaming state-machine parser that splits an LLM token stream into chat
content and artifact events.

The LLM wraps substantial, self-contained outputs in an inline tag:

    <artifact identifier="sales-dashboard" type="text/html" title="매출 대시보드">
    ...content...
    </artifact>

Because the upstream LLM stream is tokenised, the opening/closing tags can be
split across arbitrary chunk boundaries. This parser buffers the minimal tail
needed to detect a tag that may be mid-formation, and emits a flat sequence of
typed events the caller turns into SSE frames.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, Optional


OPEN_PREFIX = "<artifact"
CLOSE_TOKEN = "</artifact>"

# Parses the attributes of a fully-buffered opening tag, e.g.
#   <artifact identifier="x" type="text/html" title="제목">
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


class EventType(str, Enum):
    CONTENT = "content"
    ARTIFACT_START = "artifact_start"
    ARTIFACT_DELTA = "artifact_delta"
    ARTIFACT_END = "artifact_end"


@dataclass
class ParserEvent:
    """A single classified unit of the stream."""

    type: EventType
    text: str = ""
    identifier: Optional[str] = None
    artifact_type: Optional[str] = None
    title: Optional[str] = None


class _State(str, Enum):
    OUTSIDE = "outside"
    INSIDE = "inside"


def _longest_suffix_prefix(s: str, token: str) -> int:
    """Length of the longest suffix of ``s`` that is also a prefix of ``token``.

    Used to decide how much of the tail must be held back because it could be
    the beginning of ``token`` continued in a later chunk.
    """
    max_k = min(len(s), len(token) - 1)
    for k in range(max_k, 0, -1):
        if s[-k:] == token[:k]:
            return k
    return 0


class ArtifactStreamParser:
    """Feed raw LLM chunks in, get classified ``ParserEvent``s out.

    Not thread-safe; use one instance per stream.
    """

    def __init__(self) -> None:
        self._buffer = ""
        self._state = _State.OUTSIDE

    def feed(self, chunk: str) -> Iterator[ParserEvent]:
        """Consume a chunk and yield any events that can be fully resolved."""
        if not chunk:
            return
        self._buffer += chunk
        yield from self._drain(final=False)

    def flush(self) -> Iterator[ParserEvent]:
        """Emit whatever remains once the upstream stream is exhausted.

        Any unterminated artifact is closed so the client is never left waiting,
        and any trailing buffer is emitted as plain content.
        """
        yield from self._drain(final=True)
        if self._buffer:
            if self._state is _State.OUTSIDE:
                yield ParserEvent(EventType.CONTENT, text=self._buffer)
            else:
                yield ParserEvent(EventType.ARTIFACT_DELTA, text=self._buffer)
            self._buffer = ""
        # Finalise an artifact the model left unclosed (missing </artifact>) —
        # even with an empty trailing buffer — so it is always persisted, not
        # just streamed. Without this, a dropped closing tag means no END event
        # and the artifact never reaches the database.
        if self._state is _State.INSIDE:
            yield ParserEvent(EventType.ARTIFACT_END)
            self._state = _State.OUTSIDE

    # ── internals ───────────────────────────────────────────────────────────

    def _drain(self, final: bool) -> Iterator[ParserEvent]:
        """Repeatedly consume the buffer until no further progress is possible."""
        while True:
            before = (self._state, len(self._buffer))
            if self._state is _State.OUTSIDE:
                yield from self._drain_outside(final)
            else:
                yield from self._drain_inside(final)
            if (self._state, len(self._buffer)) == before:
                break

    def _drain_outside(self, final: bool) -> Iterator[ParserEvent]:
        """Emit content up to the next opening tag; transition on a full tag."""
        idx = self._buffer.find(OPEN_PREFIX)

        if idx == -1:
            # No opening tag in view. Emit everything except a tail that could
            # be a partial "<artifact" continued in the next chunk.
            hold = 0 if final else _longest_suffix_prefix(self._buffer, OPEN_PREFIX)
            emit_len = len(self._buffer) - hold
            if emit_len > 0:
                yield ParserEvent(EventType.CONTENT, text=self._buffer[:emit_len])
                self._buffer = self._buffer[emit_len:]
            return

        # Emit any content preceding the tag.
        if idx > 0:
            yield ParserEvent(EventType.CONTENT, text=self._buffer[:idx])
            self._buffer = self._buffer[idx:]

        # Need the full opening tag (up to '>') before we can parse attributes.
        gt = self._buffer.find(">")
        if gt == -1:
            return  # wait for more tokens

        open_tag = self._buffer[: gt + 1]
        attrs = dict(_ATTR_RE.findall(open_tag))
        self._buffer = self._buffer[gt + 1:]
        self._state = _State.INSIDE
        yield ParserEvent(
            EventType.ARTIFACT_START,
            identifier=attrs.get("identifier"),
            artifact_type=attrs.get("type"),
            title=attrs.get("title"),
        )

    def _drain_inside(self, final: bool) -> Iterator[ParserEvent]:
        """Emit artifact body up to the closing tag; transition on a full tag."""
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
        self._buffer = self._buffer[idx + len(CLOSE_TOKEN):]
        self._state = _State.OUTSIDE
        yield ParserEvent(EventType.ARTIFACT_END)
