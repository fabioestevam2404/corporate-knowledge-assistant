from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    chunk_id: str
    document_id: str
    source_id: str
    content: str
    page_number: int | None
    score: float


@dataclass(frozen=True)
class SourceReference:
    source_id: str
    document_id: str
    page_number: int | None
    chunk_id: str


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    sources: list[SourceReference]
    confidence: str
    grounded: bool
