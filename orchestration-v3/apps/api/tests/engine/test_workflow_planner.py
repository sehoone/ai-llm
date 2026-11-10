"""워크플로우 플래너(위상/사이클) 단위 테스트 (ADR-0019). 순수 로직."""

import pytest

from src.engine.workflow.planner import build_structures


def test_linear_structure():
    nodes = [{"id": "a", "type": "start"}, {"id": "b", "type": "end"}]
    edges = [{"source": "a", "target": "b"}]
    g = build_structures(nodes, edges)
    assert g.adjacency["a"] == ["b"]
    assert g.predecessors["b"] == {"a"}


def test_condition_edges_captured():
    nodes = [{"id": "c", "type": "condition"}, {"id": "t", "type": "end"}, {"id": "f", "type": "end"}]
    edges = [
        {"source": "c", "target": "t", "sourceHandle": "true"},
        {"source": "c", "target": "f", "sourceHandle": "false"},
    ]
    g = build_structures(nodes, edges)
    handles = {e["sourceHandle"] for e in g.condition_edges["c"]}
    assert handles == {"true", "false"}


def test_cycle_detection_raises():
    nodes = [{"id": "a", "type": "code"}, {"id": "b", "type": "code"}]
    edges = [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]
    with pytest.raises(ValueError, match="cycle"):
        build_structures(nodes, edges)
