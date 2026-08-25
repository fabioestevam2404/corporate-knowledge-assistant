import hashlib
import math

from cka.infrastructure.embeddings.embedding_service import EmbeddingService


class FakeEmbeddingService(EmbeddingService):
    """Deterministic, model-free embedding double for fast unit tests.

    Same dimension as the real service so code paths that assert on
    dimension consistency exercise the same contract. Not semantically
    meaningful — identical text always yields the identical vector, distinct
    text yields distinct vectors, nothing more is guaranteed.
    """

    dimension = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_one(text) for text in texts]

    def embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [digest[i % len(digest)] / 255.0 for i in range(self.dimension)]
        norm = math.sqrt(sum(value * value for value in raw)) or 1.0
        return [value / norm for value in raw]
