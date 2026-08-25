class DomainError(Exception):
    """Base class for all domain-level errors."""


class SourceNotFoundError(DomainError):
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        super().__init__(f"Source not found: {source_id}")


class SourceNotApprovedError(DomainError):
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        super().__init__(f"Source not approved for ingestion: {source_id}")
