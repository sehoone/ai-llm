"""하이브리드 검색 RRF 융합 순수 로직 단위 테스트 (DB·LLM 비의존)."""

from __future__ import annotations

from src.domains.ai_overview.service import _rrf_fuse


def _doc(doc_id: int, score: float = 0.0) -> dict:
    return {"id": doc_id, "title": f"doc{doc_id}", "content": "", "source_url": None, "score": score}


def test_doc_in_both_rankings_ranks_highest():
    trgm = [_doc(1), _doc(2), _doc(3)]
    vector = [_doc(2), _doc(4)]
    fused = _rrf_fuse([trgm, vector], limit=10)
    # doc 2는 두 랭킹 모두 상위 → 최상위
    assert fused[0]["id"] == 2


def test_limit_is_respected():
    trgm = [_doc(i) for i in range(1, 11)]
    fused = _rrf_fuse([trgm, []], limit=5)
    assert len(fused) == 5


def test_empty_vector_axis_falls_back_to_trgm_order():
    trgm = [_doc(1), _doc(2), _doc(3)]
    fused = _rrf_fuse([trgm, []], limit=10)
    assert [d["id"] for d in fused] == [1, 2, 3]


def test_fused_score_replaces_item_score():
    fused = _rrf_fuse([[_doc(1, score=0.9)], []], limit=1)
    # RRF 점수는 1/(k+1)로 교체됨 — 원래 trgm score가 아님
    assert fused[0]["score"] == 1.0 / (60 + 1)


def test_union_of_both_rankings():
    fused = _rrf_fuse([[_doc(1)], [_doc(2)]], limit=10)
    assert {d["id"] for d in fused} == {1, 2}
