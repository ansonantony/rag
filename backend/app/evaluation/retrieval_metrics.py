"""Retrieval quality metrics for the RAG evaluation pipeline."""

from dataclasses import dataclass
from typing import Sequence

DEFAULT_K = 5


@dataclass(frozen=True)
class RetrievalResult:
    """Retrieved chunks and the known relevant chunks for one question."""

    question_id: str
    retrieved_chunk_ids: list[str]
    relevant_chunk_ids: list[str]
    k: int = DEFAULT_K


@dataclass(frozen=True)
class RetrievalMetrics:
    k: int
    recall: float
    precision: float
    hit_rate: float
    reciprocal_rank: float
    retrieved_count: int
    relevant_count: int
    found: bool


def _dedupe(chunk_ids: Sequence[str]) -> list[str]:
    """Deduplicate chunk ids while preserving retrieval order."""
    return list(dict.fromkeys([chunk_id for chunk_id in chunk_ids if chunk_id]))


def recall_at_k(relevant_ids: set[str] | list[str], retrieved_ids: Sequence[str], k: int) -> float:
    """Recall@K = |R_k| / |R|, where R_k is the set of relevant chunks in the top K results."""
    relevant = {chunk_id for chunk_id in relevant_ids if chunk_id}
    if not relevant:
        return 0.0
    top_k = _dedupe(retrieved_ids)[:k]
    hits = len(relevant.intersection(set(top_k)))
    return hits / len(relevant)


def precision_at_k(relevant_ids: set[str] | list[str], retrieved_ids: Sequence[str], k: int) -> float:
    """Precision@K = |R_k| / |top_k|, using the number of retrieved results actually present."""
    top_k = _dedupe(retrieved_ids)[:k]
    if not top_k:
        return 0.0
    return len(set(top_k).intersection(set(relevant_ids))) / len(top_k)


def hit_rate_at_k(relevant_ids: set[str] | list[str], retrieved_ids: Sequence[str], k: int) -> float:
    """Hit Rate@K is 1.0 when at least one relevant chunk appears in the top K results."""
    top_k = set(_dedupe(retrieved_ids)[:k])
    return 1.0 if top_k.intersection(set(relevant_ids)) else 0.0


def reciprocal_rank(relevant_ids: set[str] | list[str], retrieved_ids: Sequence[str], k: int) -> float:
    """MRR contribution: 1 / (rank of first relevant chunk), or 0.0 when nothing relevant is found."""
    top_k = _dedupe(retrieved_ids)[:k]
    relevant = set(relevant_ids)
    for rank, chunk_id in enumerate(top_k, start=1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def evaluate_retrieval(result: RetrievalResult, k: int | None = None) -> RetrievalMetrics:
    """Compute retrieval metrics for a single question, deduplicating retrieved chunk ids."""
    effective_k = k if k and k > 0 else result.k or DEFAULT_K
    retrieved_all = _dedupe(result.retrieved_chunk_ids)
    top_k = retrieved_all[:effective_k]
    relevant = set(result.relevant_chunk_ids)
    return RetrievalMetrics(
        k=effective_k,
        recall=recall_at_k(relevant, retrieved_all, effective_k),
        precision=precision_at_k(relevant, retrieved_all, effective_k),
        hit_rate=hit_rate_at_k(relevant, retrieved_all, effective_k),
        reciprocal_rank=reciprocal_rank(relevant, retrieved_all, effective_k),
        retrieved_count=len(retrieved_all),
        relevant_count=len(relevant),
        found=bool(relevant.intersection(set(top_k))),
    )
