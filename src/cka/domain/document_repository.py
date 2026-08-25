from abc import ABC, abstractmethod

from cka.domain.document import Document


class DocumentRepository(ABC):
    @abstractmethod
    def save(self, document: Document) -> None: ...

    @abstractmethod
    def get_by_id(self, document_id: str) -> Document | None: ...

    @abstractmethod
    def get_by_sha256(self, sha256: str) -> Document | None: ...

    @abstractmethod
    def delete(self, document_id: str) -> None: ...
