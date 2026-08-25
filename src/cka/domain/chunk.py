from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    """A chunk of a processed Document, ready for embedding/retrieval.

    source_id is denormalized here (not just on Document) so retrieval can
    filter by AccessScope.allowed_source_ids without a join on the hot path —
    matches the flat shape RetrievalResult exposes for the same reason.
    """

    id: str
    document_id: str
    source_id: str
    chunk_index: int
    content: str
    page_number: int | None
    token_count: int
    embedding: list[float] | None = None
