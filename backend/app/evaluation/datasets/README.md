# RAG Evaluation Datasets

This directory holds the RAG evaluation datasets used by the evaluation layer.

- `candidate_dataset.jsonl`: AI-assisted generated candidate question-answer pairs, kept as `pending` until human review.
- `golden_dataset.jsonl`: reviewed golden question-answer pairs used as the fixed baseline for retrieval and answer evaluation.

## Record schema

Each JSONL line is a single evaluation record:

```json
{
  "id": "rag-eval-0001",
  "question": "What is the title of the source publication?",
  "reference_answer": "Advanced Software Engineering Principles.",
  "source_document_ids": ["sample"],
  "relevant_chunk_ids": ["chunk_2"],
  "answerable": true,
  "question_type": "fact_lookup",
  "generation_method": "manual",
  "validation_status": "reviewed",
  "evidence_quote": "Advanced Software Engineering Principles",
  "review_notes": "Authoritative title from the source document."
}
```

Field notes:

- `id`: stable unique evaluation case identifier.
- `question`: user question sent to the RAG application.
- `reference_answer`: concise, source-supported answer.
- `source_document_ids`: source documents containing the evidence.
- `relevant_chunk_ids`: all chunks considered necessary evidence (multiple IDs allowed for multi-chunk cases).
- `answerable`: whether the answer is supported by the available source documents.
- `question_type`: `fact_lookup`, `multi_chunk`, `synthesis`, `ambiguous`, or `unanswerable`.
- `generation_method`: `manual` or `llm_assisted`.
- `validation_status`: `pending`, `reviewed`, or `rejected`.
- `evidence_quote`: short quote supporting the reference answer.
- `review_notes`: reviewer notes.

## Usage

- Candidates are generated and validated, then reviewed before promotion to the golden dataset.
- Unanswerable cases have no `relevant_chunk_ids` and are excluded from retrieval metric denominators.
- Official benchmark runs use `golden_dataset.jsonl`.
