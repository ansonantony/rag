"""Evaluation report rendering for the RAG retrieval evaluation run."""

from app.evaluation.runner import RetrievalEvaluationRun


def build_retrieval_report(run: RetrievalEvaluationRun) -> dict:
    aggregate = run.aggregate
    return {
        "k": run.k,
        "evaluated": aggregate.evaluated,
        "answerable": aggregate.answerable,
        "unanswerable": aggregate.unanswerable,
        "retrieval": {
            "recall_at_k": aggregate.recall_at_k,
            "precision_at_k": aggregate.precision_at_k,
            "hit_rate_at_k": aggregate.hit_rate_at_k,
            "mrr": aggregate.mrr,
        },
        "errors": run.errors,
    }


def render_retrieval_report_markdown(run: RetrievalEvaluationRun) -> str:
    report = build_retrieval_report(run)
    aggregate = run.aggregate
    lines = [
        "# RAG Retrieval Evaluation Report",
        "",
        f"- Retrieval cut-off (K): {run.k}",
        f"- Answerable cases evaluated: {report['answerable']}",
        f"- Unanswerable cases (excluded from retrieval aggregates): {report['unanswerable']}",
        "",
        "## Retrieval metrics",
        "",
        f"- Recall@{run.k}: {report['retrieval']['recall_at_k']:.4f}",
        f"- Precision@{run.k}: {report['retrieval']['precision_at_k']:.4f}",
        f"- Hit Rate@{run.k}: {report['retrieval']['hit_rate_at_k']:.4f}",
        f"- MRR@{run.k}: {report['retrieval']['mrr']:.4f}",
        "",
        "## Per-case results",
        "",
    ]
    for result in run.results:
        if result.error:
            lines.append(f"- `{result.question_id}`: ERROR {result.error}")
            continue
        if result.metrics is None:
            lines.append(f"- `{result.question_id}`: not evaluated (answerable={result.answerable})")
            continue
        lines.append(
            "- `{question_id}`: recall={recall:.4f} precision={precision:.4f} "
            "hit_rate={hit_rate:.4f} mrr={mrr:.4f} retrieved={retrieved}".format(
                question_id=result.question_id,
                recall=result.metrics.recall,
                precision=result.metrics.precision,
                hit_rate=result.metrics.hit_rate,
                mrr=result.metrics.reciprocal_rank,
                retrieved=result.metrics.retrieved_count,
            )
        )
    if run.errors:
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for error in run.errors:
            lines.append(f"- {error}")
    return "\n".join(lines)
