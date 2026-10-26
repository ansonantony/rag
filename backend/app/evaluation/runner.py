"""Retrieval evaluation runner for the RAG evaluation pipeline."""

import argparse
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.evaluation.answer_metrics import answer_token_overlap, normalized_exact_match
from app.evaluation.dataset import EvalRecord, load_eval_records
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


@dataclass(frozen=True)
class AnswerEvalCaseResult:
    question_id: str
    question: str
    answerable: bool
    generated_answer: str | None
    normalized_exact_match: bool
    token_overlap: float
    retrieved_chunk_ids: list[str]
    relevant_chunk_ids: list[str]
    metrics: RetrievalMetrics | None = None
    error: str | None = None


@dataclass(frozen=True)
class AnswerAggregateMetrics:
    evaluated: int
    normalized_exact_match_accuracy: float
    abstained: int


@dataclass(frozen=True)
class EndToEndEvaluationRun:
    k: int
    retrieval_results: list[RetrievalEvalCaseResult]
    answer_results: list[AnswerEvalCaseResult]
    retrieval_aggregate: RetrievalAggregateMetrics
    answer_aggregate: AnswerAggregateMetrics
    errors: list[str]


AnswerGeneratorFn = Callable[[str, list[str]], str]


def run_end_to_end_evaluation(cases: list[EvalRecord], retriever: RetrieverFn, generate_answer: AnswerGeneratorFn, k: int = DEFAULT_K) -> EndToEndEvaluationRun:
    """Run retrieval and answer evaluation together for a set of evaluation cases."""
    retrieval_run = run_retrieval_evaluation(cases, retriever, k=k)
    answer_results: list[AnswerEvalCaseResult] = []
    errors: list[str] = list(retrieval_run.errors)
    answer_aggregate = AnswerAggregateMetrics(evaluated=0, normalized_exact_match_accuracy=0.0, abstained=0)
    answer_matches: list[bool] = []

    for retrieval_result, case in zip(retrieval_run.results, cases):
        answerable = case.answerable and case.question_type != "unanswerable"
        if not answerable:
            answer_results.append(
                AnswerEvalCaseResult(
                    question_id=case.id,
                    question=case.question,
                    answerable=False,
                    generated_answer=None,
                    normalized_exact_match=False,
                    token_overlap=0.0,
                    retrieved_chunk_ids=list(case.relevant_chunk_ids),
                    relevant_chunk_ids=list(case.relevant_chunk_ids),
                )
            )
            answer_aggregate = AnswerAggregateMetrics(
                evaluated=answer_aggregate.evaluated,
                normalized_exact_match_accuracy=answer_aggregate.normalized_exact_match_accuracy,
                abstained=answer_aggregate.abstained + 1,
            )
            continue

        if retrieval_result.error or retrieval_result.metrics is None:
            error = retrieval_result.error or f"{case.id}: missing retrieval result"
            errors.append(error)
            answer_results.append(
                AnswerEvalCaseResult(
                    question_id=case.id,
                    question=case.question,
                    answerable=True,
                    generated_answer=None,
                    normalized_exact_match=False,
                    token_overlap=0.0,
                    retrieved_chunk_ids=[],
                    relevant_chunk_ids=list(case.relevant_chunk_ids),
                    metrics=None,
                    error=error,
                )
            )
            continue

        try:
            generated_answer = generate_answer(case.question, retrieval_result.retrieved_chunk_ids)
            exact_match = normalized_exact_match(generated_answer, case.reference_answer)
            token_overlap = answer_token_overlap(generated_answer, case.reference_answer)
            answer_results.append(
                AnswerEvalCaseResult(
                    question_id=case.id,
                    question=case.question,
                    answerable=True,
                    generated_answer=generated_answer,
                    normalized_exact_match=exact_match,
                    token_overlap=token_overlap,
                    retrieved_chunk_ids=retrieval_result.retrieved_chunk_ids,
                    relevant_chunk_ids=list(case.relevant_chunk_ids),
                    metrics=retrieval_result.metrics,
                )
            )
            answer_matches.append(exact_match)
        except Exception as exc:  # noqa: BLE001 - evaluation runner aggregates per-case failures
            error = f"{case.id}: {exc}"
            errors.append(error)
            answer_results.append(
                AnswerEvalCaseResult(
                    question_id=case.id,
                    question=case.question,
                    answerable=True,
                    generated_answer=None,
                    normalized_exact_match=False,
                    token_overlap=0.0,
                    retrieved_chunk_ids=[],
                    relevant_chunk_ids=list(case.relevant_chunk_ids),
                    metrics=None,
                    error=error,
                )
            )

    answer_aggregate = AnswerAggregateMetrics(
        evaluated=len(answer_matches),
        normalized_exact_match_accuracy=(sum(1 for matched in answer_matches if matched) / len(answer_matches)) if answer_matches else 0.0,
        abstained=answer_aggregate.abstained,
    )
    return EndToEndEvaluationRun(
        k=k,
        retrieval_results=retrieval_run.results,
        answer_results=answer_results,
        retrieval_aggregate=retrieval_run.aggregate,
        answer_aggregate=answer_aggregate,
        errors=errors,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the RAG retrieval evaluation.")
    parser.add_argument("--dataset", default="app/evaluation/datasets/golden_dataset.jsonl", help="Path to the JSONL evaluation dataset.")
    parser.add_argument("--k", type=int, default=5, help="Retrieval cut-off K used for metrics.")
    return parser


def main(argv: list[str] | None = None) -> int:
    from app.evaluation.report import build_retrieval_report, render_retrieval_report_markdown

    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    cases = load_eval_records(args.dataset)
    evaluated = [case for case in cases if case.answerable and case.source_document_ids]

    def retriever(question: str, document_id: str) -> list[dict[str, Any]]:
        raise RuntimeError("Retriever backend not configured for CLI evaluation; provide a retriever callable in application code.")

    run = run_retrieval_evaluation(evaluated, retriever, k=args.k)
    report = build_retrieval_report(run)
    print(render_retrieval_report_markdown(run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
