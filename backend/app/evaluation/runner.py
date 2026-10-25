"""Retrieval evaluation runner for the RAG evaluation pipeline."""

import uuid
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.evaluation.dataset import EvalRecord
from app.evaluation.retrieval_metrics import DEFAULT_K, RetrievalMetrics, RetrievalResult, evaluate_retrieval
from app.services.retrieval_service import retrieve

RetrieverFn = Callable[[str, str], list[dict[str, Any]]]


@dataclass(frozen=True)
class RetrievalEvalCaseResult:
    question_id: str
    question: str
    answerable: bool
    retrieved_chunk_ids: list[str]
    relevant_chunk_ids: list[str]
    metrics: RetrievalMetrics | None = None
    error: str | None = None


@dataclass(frozen=True)
class RetrievalAggregateMetrics:
    evaluated: int
    answerable: int
    unanswerable: int
    recall_at_k: float
    precision_at_k: float
    hit_rate_at_k: float
    mrr: float


@dataclass(frozen=True)
class RetrievalEvaluationRun:
    k: int
    results: list[RetrievalEvalCaseResult]
    aggregate: RetrievalAggregateMetrics
    errors: list[str]


def _aggregate(metrics_list: list[RetrievalMetrics], unanswerable: int) -> RetrievalAggregateMetrics:
    evaluated = len(metrics_list)
    if evaluated == 0:
        return RetrievalAggregateMetrics(
            evaluated=0,
            answerable=0,
            unanswerable=unanswerable,
            recall_at_k=0.0,
            precision_at_k=0.0,
            hit_rate_at_k=0.0,
            mrr=0.0,
        )
    return RetrievalAggregateMetrics(
        evaluated=evaluated,
        answerable=evaluated,
        unanswerable=unanswerable,
        recall_at_k=sum(metric.recall for metric in metrics_list) / len(metrics_list),
        precision_at_k=sum(metric.precision for metric in metrics_list) / len(metrics_list),
        hit_rate_at_k=sum(metric.hit_rate for metric in metrics_list) / len(metrics_list),
        mrr=sum(metric.reciprocal_rank for metric in metrics_list) / len(metrics_list),
    )


def run_retrieval_evaluation(cases: list[EvalRecord], retriever: RetrieverFn, k: int = DEFAULT_K) -> RetrievalEvaluationRun:
    """Run retrieval evaluation over validated evaluation cases."""
    results: list[RetrievalEvalCaseResult] = []
    errors: list[str] = []
    metrics_list: list[RetrievalMetrics] = []
    unanswerable = 0

    for case in cases:
        if case.question_type == "unanswerable" or not case.answerable:
            unanswerable += 1
            results.append(
                RetrievalEvalCaseResult(
                    question_id=case.id,
                    question=case.question,
                    answerable=False,
                    retrieved_chunk_ids=list(case.relevant_chunk_ids),
                    relevant_chunk_ids=list(case.relevant_chunk_ids),
                )
            )
            continue

        if not case.source_document_ids:
            error = f"{case.id}: answerable evaluation case is missing source_document_ids"
            errors.append(error)
            results.append(
                RetrievalEvalCaseResult(
                    question_id=case.id,
                    question=case.question,
                    answerable=True,
                    retrieved_chunk_ids=[],
                    relevant_chunk_ids=list(case.relevant_chunk_ids),
                    error=error,
                )
            )
            continue

        try:
            chunks = retriever(case.question, case.source_document_ids[0]) or []
            retrieved_chunk_ids = [
                str(chunk["chunk_id"])
                for chunk in chunks
                if isinstance(chunk, dict) and chunk.get("chunk_id")
            ]
            metrics = evaluate_retrieval(
                RetrievalResult(
                    question_id=case.id,
                    retrieved_chunk_ids=retrieved_chunk_ids,
                    relevant_chunk_ids=case.relevant_chunk_ids,
                    k=k,
                ),
                k=k,
            )
        except Exception as exc:  # noqa: BLE001 - evaluation runner aggregates per-case failures
            error = f"{case.id}: {exc}"
            errors.append(error)
            results.append(
                RetrievalEvalCaseResult(
                    question_id=case.id,
                    question=case.question,
                    answerable=True,
                    retrieved_chunk_ids=[],
                    relevant_chunk_ids=list(case.relevant_chunk_ids),
                    error=error,
                )
            )
            continue

        results.append(
            RetrievalEvalCaseResult(
                question_id=case.id,
                question=case.question,
                answerable=True,
                retrieved_chunk_ids=retrieved_chunk_ids,
                relevant_chunk_ids=list(case.relevant_chunk_ids),
                metrics=metrics,
            )
        )
        metrics_list.append(metrics)

    return RetrievalEvaluationRun(k=k, results=results, aggregate=_aggregate(metrics_list, unanswerable), errors=errors)


def create_retriever(user_id: str, db: Session, k: int = 5) -> RetrieverFn:
    """Build a retriever callable that reuses the production retrieval logic."""

    def retriever(question: str, document_id: str) -> list[dict[str, Any]]:
        document_uuid = uuid.UUID(document_id)
        user_uuid = uuid.UUID(user_id)
        chunks = retrieve(
            question,
            user_id=user_uuid,
            document_id=document_uuid,
            limit=k,
            db=db,
        )
        return [chunk for chunk in (chunks or []) if isinstance(chunk, dict)]

    return retriever
