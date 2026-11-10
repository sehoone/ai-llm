"""ExecutionContext 템플릿 리졸버 단위 테스트 (ADR-0019). 순수 로직 — 외부 의존 없음."""

from src.engine.workflow.context import ExecutionContext


def _ctx() -> ExecutionContext:
    ctx = ExecutionContext(execution_id="e1", input_data={"name": "Ada", "n": 3})
    ctx.set_node_output("llm-1", {"text": "hello", "meta": {"lang": "ko"}})
    return ctx


def test_input_substitution_in_string():
    ctx = _ctx()
    assert ctx.resolve("Hi {{input.name}}!") == "Hi Ada!"


def test_single_placeholder_preserves_type():
    ctx = _ctx()
    # 전체가 단일 placeholder → 원시 타입(int) 보존
    assert ctx.resolve("{{input.n}}") == 3
    # dict 전체 반환
    assert ctx.resolve("{{nodes.llm-1.output.meta}}") == {"lang": "ko"}


def test_node_output_lookup_and_nested():
    ctx = _ctx()
    assert ctx.resolve("{{nodes.llm-1.output.text}}") == "hello"
    assert ctx.resolve("{{nodes.llm-1.output.meta.lang}}") == "ko"


def test_recursive_dict_and_list_resolution():
    ctx = _ctx()
    out = ctx.resolve({"greeting": "Hi {{input.name}}", "items": ["{{input.n}}", "x"]})
    assert out == {"greeting": "Hi Ada", "items": [3, "x"]}


def test_unknown_path_resolves_empty():
    ctx = _ctx()
    # 여러 placeholder → None은 빈 문자열로
    assert ctx.resolve("[{{input.missing}}]") == "[]"
