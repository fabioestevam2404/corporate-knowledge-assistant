import math

from cka.infrastructure.embeddings.fake_embedding_service import FakeEmbeddingService


def test_embed_one_returns_vector_of_expected_dimension() -> None:
    service = FakeEmbeddingService()

    vector = service.embed_one("remote work policy")

    assert len(vector) == service.dimension


def test_embed_one_is_deterministic() -> None:
    service = FakeEmbeddingService()

    assert service.embed_one("same text") == service.embed_one("same text")


def test_embed_one_differs_for_different_text() -> None:
    service = FakeEmbeddingService()

    assert service.embed_one("text a") != service.embed_one("text b")


def test_embed_one_returns_a_normalized_vector() -> None:
    service = FakeEmbeddingService()

    vector = service.embed_one("normalize me")
    norm = math.sqrt(sum(v * v for v in vector))

    assert math.isclose(norm, 1.0, rel_tol=1e-6)


def test_embed_batches_multiple_texts() -> None:
    service = FakeEmbeddingService()

    vectors = service.embed(["a", "b", "c"])

    assert len(vectors) == 3
    assert all(len(v) == service.dimension for v in vectors)
