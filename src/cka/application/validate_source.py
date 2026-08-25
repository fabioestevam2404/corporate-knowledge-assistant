from cka.domain.exceptions import SourceNotApprovedError, SourceNotFoundError
from cka.domain.source import Source
from cka.domain.source_repository import SourceRepository


class ValidateSource:
    """Enforces ADR-001: a source must exist in the registry, be approved, and
    be explicitly marked allowed_for_ingestion before any document from it can
    be ingested.
    """

    def __init__(self, source_repository: SourceRepository) -> None:
        self._source_repository = source_repository

    def __call__(self, source_id: str) -> Source:
        source = self._source_repository.get_by_id(source_id)
        if source is None:
            raise SourceNotFoundError(source_id)

        if source.status != "approved" or not source.allowed_for_ingestion:
            raise SourceNotApprovedError(source_id)

        return source
