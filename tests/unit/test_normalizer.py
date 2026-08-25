from cka.infrastructure.processing.normalizer import normalize_text


def test_collapses_multiple_blank_lines() -> None:
    assert normalize_text("a\n\n\n\n\nb") == "a\n\nb"


def test_collapses_multiple_spaces() -> None:
    assert normalize_text("a    b") == "a b"


def test_strips_trailing_whitespace_on_lines() -> None:
    assert normalize_text("a   \nb") == "a\nb"


def test_normalizes_windows_line_endings() -> None:
    assert normalize_text("a\r\nb") == "a\nb"


def test_strips_leading_and_trailing_whitespace() -> None:
    assert normalize_text("  \n hello \n  ") == "hello"
