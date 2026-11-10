"""engine/llm 스트리밍 어댑터 순수 로직 단위 테스트 (LLM·네트워크 비의존).

`LlmChatModel.stream`은 주입된 Runnable의 조각을 텍스트로 변환해 yield하고, system prompt를
선주입한다. 실제 LLM 대신 Fake runnable로 동작을 검증한다.
"""

from __future__ import annotations

from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage

from src.engine.llm.model import LlmChatModel, _chunk_text


def test_chunk_text_plain_string():
    assert _chunk_text("hello") == "hello"


def test_chunk_text_block_list_collects_text_only():
    content = [{"type": "text", "text": "a"}, {"type": "image", "url": "x"}, {"type": "text", "text": "b"}]
    assert _chunk_text(content) == "ab"


def test_chunk_text_other_returns_empty():
    assert _chunk_text(None) == ""
    assert _chunk_text(123) == ""


class _FakeRunnable:
    """content 조각을 순차 방출하는 최소 Runnable 스텁."""

    def __init__(self, parts: list[str]) -> None:
        self.parts = parts
        self.seen_messages: list = []

    def stream(self, messages, config=None):
        self.seen_messages = list(messages)
        for p in self.parts:
            yield AIMessageChunk(content=p)


def test_stream_yields_nonempty_text_chunks():
    runnable = _FakeRunnable(["Hel", "", "lo"])
    model = LlmChatModel(runnable)
    out = list(model.stream([HumanMessage(content="hi")]))
    assert out == ["Hel", "lo"]  # 빈 조각은 건너뜀


def test_stream_prepends_system_prompt_when_absent():
    runnable = _FakeRunnable(["x"])
    model = LlmChatModel(runnable, system_prompt="SYS")
    list(model.stream([HumanMessage(content="hi")]))
    assert isinstance(runnable.seen_messages[0], SystemMessage)
    assert runnable.seen_messages[0].content == "SYS"


def test_stream_does_not_duplicate_existing_system_prompt():
    runnable = _FakeRunnable(["x"])
    model = LlmChatModel(runnable, system_prompt="SYS")
    list(model.stream([SystemMessage(content="ORIG"), HumanMessage(content="hi")]))
    system_msgs = [m for m in runnable.seen_messages if isinstance(m, SystemMessage)]
    assert len(system_msgs) == 1
    assert system_msgs[0].content == "ORIG"
