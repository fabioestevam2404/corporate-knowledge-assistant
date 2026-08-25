from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    dimension: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_one(self, text: str) -> list[float]: ...
