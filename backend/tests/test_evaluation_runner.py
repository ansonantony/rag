from app.evaluation.dataset import EvalRecord
from app.evaluation.runner import run_retrieval_evaluation


def _case(**overrides):
    base = {
        "id": "rag-eval-0001",
        "question": "What database does the application use?",
        "reference_answer": "PostgreSQL",
        "source_document_ids": ["doc-1"],
        "relevant_chunk_ids": ["chunk-1"],
        "answerable": True,
        "question_type": "fact_lookup",
        "generation_method": "manual",
        "validation_status": "reviewed",
        "evidence_quote": "PostgreSQL",
        "review_notes": None,
    }
    base.update(overrides)
    return EvalRecord.model_validate(base)


def test_runner_computes_retrieval_metrics_for_answerable_case():
    def retriever(question: str, document_id: str):
        assert document_id == "doc-1"
        return [{"chunk_id": "chunk-1", "source_text": "PostgreSQL", "similarity_score": 0.9}]

    run = run_retrieval_evaluation([_case()], retriever, k=3)

    assert len(run.results) == 1
    result = run.results[0]
    assert result.error is None
    assert result.metrics is not None
    assert result.metrics.found is True
    assert result.metrics.recall == 1.0
    assert result.metrics.precision == 1.0
    assert result.metrics.hit_rate == 1.0
    assert result.metrics.reciprocal_rank == 1.0
    assert run.aggregate.evaluated == 1
    assert run.aggregate.answerable == 1


def test_runner_skips_unanswerable_cases():
    run = run_retrieval_evaluation([_case(question_type="unanswerable", answerable=False, relevant_chunk_ids=[])], lambda q, d: [], k=5)

    assert len(run.results) == 1
    assert run.results[0].answerable is False
    assert run.results[0].metrics is None
    assert run.aggregate.unanswerable == 1
    assert run.aggregate.evaluated == 0
