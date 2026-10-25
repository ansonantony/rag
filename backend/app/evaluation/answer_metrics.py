"""Answer-quality metrics: normalized exact match and supporting token overlap."""

import unicodedata


def normalize_answer(answer: str | None) -> str:
    """Normalize an answer for comparison.

    - Unicode normalization (NFKC).
    - Whitespace collapsing and trimming.
    - Case-insensitive comparison via casefold.

    Meaningful content such as numbers, negation, units, and technical terms is preserved.
    """
    if not answer:
        return ""
    text = unicodedata.normalize("NFKC", answer)
    text = " ".join(text.split())
    return text.strip().casefold()


def normalized_exact_match(generated: str | None, reference: str | None) -> bool:
    """Return True when the normalized generated answer equals the normalized reference answer."""
    return normalize_answer(generated) == normalize_answer(reference)


def answer_token_overlap(generated: str | None, reference: str | None) -> float:
    """Return token-level overlap between generated and reference answers (supporting diagnostic)."""
    generated_tokens = set(normalize_answer(generated).split())
    reference_tokens = set(normalize_answer(reference).split())
    if not reference_tokens:
        return 0.0
    return len(generated_tokens & reference_tokens) / len(reference_tokens)
