import pytest

from app.evaluation.retrieval_metrics import (
    DEFAULT_K,
    RetrievalResult,
    evaluate_retrieval,
    hit_rate_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k_counts_relevant_chunks_in_top_k():
    relevant = {"c1", "c2"}
    retrieved = ["c3", "c1", "c2"]
    assert recall_at_k(relevant, retrieved, k=5) == pytest.approx(1.0)


def test_recall_at_k_partial_coverage():
    relevant = {"c1", "c2"}
    retrieved = ["c3", "c1"]
    assert recall_at_k(relevant, retrieved, k=5) == pytest.approx(0.5)


def test_precision_at_k_counts_relevance_in_top_k():
    relevant = {"c1"}
    retrieved = ["c1", "c2", "c3"]
    assert precision_at_k(relevant, retrieved, k=3) == pytest.approx(1.0 / 3.0)


def test_hit_rate_at_k_true_when_relevant_chunk_is_in_top_k():
    assert hit_rate_at_k({"c1"}, ["c2", "c1"], k=5) == 1.0
    assert hit_rate_at_k({"c1"}, ["c2", "c3"], k=5) == 0.0


def test_reciprocal_rank_uses_first_relevant_rank():
    assert reciprocal_rank({"c2"}, ["c1", "c2"], k=5) == pytest.approx(0.5)
    assert reciprocal_rank({"c2"}, ["c1", "c3", "c2"], k=5) == pytest.approx(1.0 / 3.0)
    assert reciprocal_rank({"c2"}, ["c1", "c3"], k=5) == 0.0


def test_evaluate_retrieval_dedupes_and_applies_k():
    result = RetrievalResult(question_id="q1", retrieved_chunk_ids=["c1", "c1", "c2"], relevant_chunk_ids=["c2"], k=5)
    metrics = evaluate_retrieval(result, k=2)
    assert metrics.k == 2
    assert metrics.retrieved_count == 2
    assert metrics.hit_rate == 1.0
    assert metrics.found is True


def test_evaluate_retrieval_defaults_to_default_k():
    result = RetrievalResult(question_id="q1", retrieved_chunk_ids=["c1"], relevant_chunk_ids=["c1"], k=DEFAULT_K)
    assert evaluate_retrieval(result).k == DEFAULT_K
