from abc import ABC, abstractmethod

from cka.domain.retrieval import RetrievalResult


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query_text: str, results: list[RetrievalResult]) -> list[RetrievalResult]: ...
