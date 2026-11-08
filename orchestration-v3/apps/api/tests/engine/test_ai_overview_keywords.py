"""ai_overview 키워드 LLM JSON 파싱 단위 테스트 (LLM 비의존)."""

from __future__ import annotations

import pytest

from src.engine.ai_overview.keywords import _message_text, _parse_llm_json


def test_parse_plain_json():
    data = _parse_llm_json('{"keywords": ["a", "b"], "synonyms": {"a": ["x"]}}')
    assert data["keywords"] == ["a", "b"]
    assert data["synonyms"] == {"a": ["x"]}


def test_parse_json_code_fence():
    raw = '```json\n{"keywords": ["a"]}\n```'
    assert _parse_llm_json(raw)["keywords"] == ["a"]


def test_parse_bare_code_fence():
    raw = '```\n{"keywords": ["a"]}\n```'
    assert _parse_llm_json(raw)["keywords"] == ["a"]


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError):
        _parse_llm_json("not json at all")


def test_message_text_from_block_list():
    content = [{"text": "hello "}, {"text": "world"}]
    assert _message_text(content) == "hello  world"


def test_message_text_from_string():
    assert _message_text("plain") == "plain"
