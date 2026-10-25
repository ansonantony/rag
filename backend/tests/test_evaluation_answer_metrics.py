from app.evaluation.answer_metrics import answer_token_overlap, normalize_answer, normalized_exact_match


def test_normalize_answer_collapses_whitespace_and_trims():
    assert normalize_answer("  Hello   World \n") == "hello world"


def test_normalized_exact_match_is_case_insensitive_and_whitespace_insensitive():
    assert normalized_exact_match("  PostgreSQL  ", "postgresql") is True
    assert normalized_exact_match("The database is PostgreSQL", "the database is postgresql") is True


def test_normalized_exact_match_handles_unicode_composition():
    assert normalized_exact_match("café", "café") is True


def test_normalized_exact_match_preserves_numbers_and_negation():
    assert normalized_exact_match("Do not use version 5", "do not use version 5") is True
    assert normalized_exact_match("The answer is 42", "The answer is forty two") is False


def test_answer_token_overlap_returns_fraction():
    assert answer_token_overlap("PostgreSQL is the database", "PostgreSQL") == 1.0
    assert answer_token_overlap("Unrelated answer", "PostgreSQL") == 0.0
    assert answer_token_overlap(None, "PostgreSQL") == 0.0
