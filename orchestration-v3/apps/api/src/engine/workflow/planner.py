"""노드/엣지 → 위상 구조 + 사이클 검출 (ADR-0019 §1, V2 _build_structures 계승).

React Flow `{nodes, edges}` 정의에서 인접/선행/condition-edge 맵을 만들고, Kahn 알고리즘으로
비순환(acyclic)을 검증한다. DAG만 허용.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GraphStructures:
    nodes_by_id: dict[str, dict]
    adjacency: dict[str, list[str]]          # src → [tgt]
    predecessors: dict[str, set[str]]        # nid → {src}
    condition_edges: dict[str, list[dict]]   # condition_nid → outgoing edges(true/false handle)


def build_structures(nodes_def: list[dict], edges_def: list[dict]) -> GraphStructures:
    """인접·선행·condition-edge 구조 생성 + 사이클 검증(ValueError on cycle)."""
    nodes_by_id: dict[str, dict] = {n["id"]: n for n in nodes_def}
    adjacency: dict[str, list[str]] = defaultdict(list)
    predecessors: dict[str, set[str]] = defaultdict(set)
    condition_edges: dict[str, list[dict]] = defaultdict(list)

    for edge in edges_def:
        src = edge["source"]
        tgt = edge["target"]
        adjacency[src].append(tgt)
        predecessors[tgt].add(src)
        if edge.get("sourceHandle") in ("true", "false"):
            condition_edges[src].append(edge)

    # Kahn 위상 정렬로 사이클 검출
    in_degree = {nid: len(predecessors.get(nid, set())) for nid in nodes_by_id}
    queue: deque[str] = deque(nid for nid, d in in_degree.items() if d == 0)
    visited = 0
    while queue:
        nid = queue.popleft()
        visited += 1
        for tgt in adjacency.get(nid, []):
            in_degree[tgt] -= 1
            if in_degree[tgt] == 0:
                queue.append(tgt)

    if visited != len(nodes_by_id):
        raise ValueError("Workflow definition contains a cycle — acyclic graphs only.")

    return GraphStructures(
        nodes_by_id=dict(nodes_by_id),
        adjacency=dict(adjacency),
        predecessors=dict(predecessors),
        condition_edges=dict(condition_edges),
    )
