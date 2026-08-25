from typing import TYPE_CHECKING

from cka.infrastructure.embeddings.embedding_service import EmbeddingService

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class SentenceTransformerEmbeddingService(EmbeddingService):
    """Real embedding backend, per ADR-006: all-MiniLM-L6-v2, dim 384, normalized.

    Both the `sentence_transformers` import and the model itself are deferred
    to first use, not construction/module-import time. `sentence_transformers`
    pulls in torch, which costs ~15s to import alone — paying that just to
    boot the app for a /health check (as every TestClient(app) unit test
    does, since main.py constructs this service in its lifespan) would tax
    every unit test run for a dependency those tests never touch.
    """

    dimension = 384

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> "SentenceTransformer":
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._get_model().encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
