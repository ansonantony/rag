"""RAG evaluation toolkit."""

from app.evaluation.answer_metrics import (
    answer_token_overlap,
    normalized_exact_match,
    normalize_answer,
)
from app.evaluation.dataset import (
    EvalRecord,
    load_eval_records,
    validate_eval_records,
)
from app.evaluation.retrieval_metrics import (
    DEFAULT_K,
    RetrievalMetrics,
    RetrievalResult,
    evaluate_retrieval,
    hit_rate_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

__all__ = [
    "DEFAULT_K",
    "EvalRecord",
    "RetrievalMetrics",
    "RetrievalResult",
    "answer_token_overlap",
    "evaluate_retrieval",
    "hit_rate_at_k",
    "load_eval_records",
    "normalized_exact_match",
    "normalize_answer",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "validate_eval_records",
]
