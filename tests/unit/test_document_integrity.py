import hashlib

from cka.application.document_integrity import calculate_sha256


def test_calculate_sha256_is_deterministic() -> None:
    content = b"corporate knowledge assistant sample content"

    assert calculate_sha256(content) == calculate_sha256(content)


def test_calculate_sha256_matches_hashlib_reference() -> None:
    content = b"corporate knowledge assistant sample content"

    assert calculate_sha256(content) == hashlib.sha256(content).hexdigest()


def test_calculate_sha256_differs_for_different_content() -> None:
    assert calculate_sha256(b"content-a") != calculate_sha256(b"content-b")
