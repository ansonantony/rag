"""Evaluation dataset: schema, loading, and validation for RAG golden/candidate sets."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

QUESTION_TYPES = ("fact_lookup", "multi_chunk", "synthesis", "ambiguous", "unanswerable")
GENERATION_METHODS = ("manual", "llm_assisted")
VALIDATION_STATUSES = ("pending", "reviewed", "rejected")


class EvalRecord(BaseModel):
    """A single evaluation case with a question, reference answer, and evidence."""

    id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=10000)
    reference_answer: str | None = Field(default=None, max_length=4000)
    source_document_ids: list[str] = Field(default_factory=list)
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    answerable: bool = Field(default=True)
    question_type: str = Field(default="fact_lookup")
    generation_method: str = Field(default="manual")
    validation_status: str = Field(default="pending")
    evidence_quote: str | None = Field(default=None, max_length=2000)
    review_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("id must be a non-empty string")
        return cleaned

    @field_validator("question_type")
    @classmethod
    def _validate_question_type(cls, value: str) -> str:
        if value not in QUESTION_TYPES:
            raise ValueError(f"question_type must be one of {QUESTION_TYPES}")
        return value

    @field_validator("generation_method")
    @classmethod
    def _validate_generation_method(cls, value: str) -> str:
        if value not in GENERATION_METHODS:
            raise ValueError(f"generation_method must be one of {GENERATION_METHODS}")
        return value

    @field_validator("validation_status")
    @classmethod
    def _validate_validation_status(cls, value: str) -> str:
        if value not in VALIDATION_STATUSES:
            raise ValueError(f"validation_status must be one of {VALIDATION_STATUSES}")
        return value

    @model_validator(mode="after")
    def _validate_semantics(self) -> "EvalRecord":
        if self.question_type == "unanswerable":
            if self.answerable:
                raise ValueError("Unanswerable records must set answerable=False")
            if self.relevant_chunk_ids:
                raise ValueError("Unanswerable records must not define relevant_chunk_ids")
        else:
            if not self.answerable:
                raise ValueError("Only unanswerable records may set answerable=False")
            if not (self.reference_answer or "").strip():
                raise ValueError("Answerable records require a non-empty reference_answer")
            if not self.relevant_chunk_ids:
                raise ValueError("Answerable records require at least one relevant_chunk_id")
        return self


def load_eval_records(path: str | Path) -> list[EvalRecord]:
    """Load evaluation records from a JSONL file with one JSON object per line."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {file_path}")
    records: list[EvalRecord] = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                records.append(EvalRecord.model_validate_json(line))
            except ValidationError as exc:
                raise ValueError(f"Invalid evaluation record at {file_path}:{line_number}: {exc}") from exc
    return records


def validate_eval_records(raw_records: list[dict[str, Any]]) -> tuple[list[EvalRecord], list[str]]:
    """Validate raw evaluation dictionaries. Returns (valid_records, error_messages)."""
    valid: list[EvalRecord] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_records):
        try:
            record = EvalRecord.model_validate(raw)
        except ValidationError as exc:
            errors.append(f"record[{index}]: {exc}")
            continue
        if record.id in seen_ids:
            errors.append(f"record[{index}]: duplicate id {record.id}")
            continue
        seen_ids.add(record.id)
        valid.append(record)
    return valid, errors
