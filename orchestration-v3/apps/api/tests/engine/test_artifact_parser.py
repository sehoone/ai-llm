"""ArtifactStreamParser 단위 테스트 (ADR-0013)."""

from __future__ import annotations

from src.engine.artifact import ArtifactStreamParser, EventType


def _run(chunks: list[str]):
    p = ArtifactStreamParser()
    events = []
    for c in chunks:
        events.extend(p.feed(c))
    events.extend(p.flush())
    return events


def test_plain_content_passes_through():
    events = _run(["Hello ", "world"])
    assert all(e.type is EventType.CONTENT for e in events)
    assert "".join(e.text for e in events) == "Hello world"


def test_full_artifact_single_chunk():
    stream = 'Intro.<artifact identifier="a1" type="text/html" title="T">BODY</artifact>Done.'
    events = _run([stream])
    types = [e.type for e in events]
    assert EventType.ARTIFACT_START in types
    assert EventType.ARTIFACT_END in types
    start = next(e for e in events if e.type is EventType.ARTIFACT_START)
    assert start.identifier == "a1"
    assert start.artifact_type == "text/html"
    assert start.title == "T"
    body = "".join(e.text for e in events if e.type is EventType.ARTIFACT_DELTA)
    assert body == "BODY"
    content = "".join(e.text for e in events if e.type is EventType.CONTENT)
    assert content == "Intro.Done."


def test_tag_split_across_chunks():
    # 여는/닫는 태그가 청크 경계에서 쪼개져도 복원되어야 한다.
    chunks = ['Pre <arti', 'fact identifier="x" type="text/mark', 'down" title="Doc">he', 'llo</arti', 'fact> post']
    events = _run(chunks)
    start = next(e for e in events if e.type is EventType.ARTIFACT_START)
    assert start.identifier == "x"
    assert start.artifact_type == "text/markdown"
    body = "".join(e.text for e in events if e.type is EventType.ARTIFACT_DELTA)
    assert body == "hello"
    content = "".join(e.text for e in events if e.type is EventType.CONTENT)
    assert content == "Pre  post"


def test_false_positive_without_attrs_is_content():
    # identifier/type 없는 "<artifact>"는 아티팩트가 아니라 평문.
    events = _run(["talking about <artifact> tags in prose"])
    assert all(e.type is EventType.CONTENT for e in events)
    assert "".join(e.text for e in events) == "talking about <artifact> tags in prose"


def test_unterminated_artifact_is_closed_on_flush():
    events = _run(['x<artifact identifier="a" type="text/plain">body never closed'])
    types = [e.type for e in events]
    assert types.count(EventType.ARTIFACT_END) == 1
    body = "".join(e.text for e in events if e.type is EventType.ARTIFACT_DELTA)
    assert body == "body never closed"
