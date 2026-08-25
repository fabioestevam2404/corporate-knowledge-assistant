from abc import ABC, abstractmethod

from cka.domain.source import Source


class SourceRepository(ABC):
    @abstractmethod
    def get_by_id(self, source_id: str) -> Source | None: ...

    @abstractmethod
    def list_sources(self) -> list[Source]: ...
