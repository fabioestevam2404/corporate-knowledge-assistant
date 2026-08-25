from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessScope:
    """Who is asking, and which sources they're allowed to see.

    Full RBAC/ACL enforcement lands in Block 3 (Sprint 09). Until then, this
    is a real domain contract that retrieval always threads through — never
    bypassed — but the only scope constructed today is "every approved
    source" (see application/access_scope.py).
    """

    user_id: str
    role: str
    allowed_source_ids: frozenset[str]


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    top_k: int = 5
    access_scope: AccessScope | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    document_id: str
    source_id: str
    content: str
    page_number: int | None
    chunk_index: int
    score: float


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]: ...
