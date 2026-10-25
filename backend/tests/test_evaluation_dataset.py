from pathlib import Path

from app.evaluation.dataset import EvalRecord, load_eval_records, validate_eval_records


def _base_record(**overrides):
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
    return base


def test_valid_answerable_record_passes_validation():
    valid, errors = validate_eval_records([_base_record()])
    assert len(valid) == 1
    assert errors == []


def test_answerable_record_requires_reference_answer():
    valid, errors = validate_eval_records([_base_record(reference_answer=None)])
    assert valid == []
    assert errors


def test_answerable_record_requires_relevant_chunk():
    valid, errors = validate_eval_records([_base_record(relevant_chunk_ids=[])])
    assert valid == []
    assert errors


def test_unanswerable_record_must_not_carry_relevant_chunks():
    valid, errors = validate_eval_records(
        [
            _base_record(
                answerable=False,
                question_type="unanswerable",
                reference_answer=None,
                relevant_chunk_ids=[],
            )
        ]
    )
    assert len(valid) == 1
    assert errors == []


def test_duplicate_ids_are_reported():
    valid, errors = validate_eval_records([_base_record(), _base_record()])
    assert len(valid) == 1
    assert any("duplicate id" in error for error in errors)


def test_load_eval_records_from_jsonl(tmp_path: Path):
    dataset_path = tmp_path / "golden_dataset.jsonl"
    dataset_path.write_text(
        "\n".join(
            [
                '{"id":"rag-eval-0001","question":"What database does the application use?","reference_answer":"PostgreSQL","source_document_ids":["doc-1"],"relevant_chunk_ids":["chunk-1"],"answerable":true,"question_type":"fact_lookup","generation_method":"manual","validation_status":"reviewed","evidence_quote":"PostgreSQL","review_notes":null}',
                "",
            ]
        ),
        encoding="utf-8",
    )
    records = load_eval_records(dataset_path)
    assert len(records) == 1
    assert records[0].id == "rag-eval-0001"
    assert records[0].answerable is True
