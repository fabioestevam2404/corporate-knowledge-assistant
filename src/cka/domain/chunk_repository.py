from abc import ABC, abstractmethod

from cka.domain.chunk import DocumentChunk


class ChunkRepository(ABC):
    @abstractmethod
    def save_many(self, chunks: list[DocumentChunk]) -> None: ...

    @abstractmethod
    def get_by_document_id(self, document_id: str) -> list[DocumentChunk]: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def delete_by_document_id(self, document_id: str) -> None: ...
