from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadedPage:
    text: str
    page_number: int | None


class DocumentLoader(ABC):
    @abstractmethod
    def supports(self, filename: str) -> bool: ...

    @abstractmethod
    def load(self, path: Path) -> list[LoadedPage]: ...
