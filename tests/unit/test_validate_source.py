import pytest

from cka.application.validate_source import ValidateSource
from cka.domain.exceptions import SourceNotApprovedError, SourceNotFoundError
from cka.domain.source import Source
from cka.domain.source_repository import SourceRepository


class InMemorySourceRepository(SourceRepository):
    def __init__(self, sources: list[Source]) -> None:
        self._sources = {source.id: source for source in sources}

    def get_by_id(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def list_sources(self) -> list[Source]:
        return list(self._sources.values())


def make_source(**overrides: object) -> Source:
    defaults: dict[str, object] = {
        "id": "SRC-001",
        "name": "Sample Source",
        "organization": "Acme",
        "source_type": "internal_policy",
        "url": "data/raw/samples/sample.txt",
        "license": "CC0-1.0",
        "access_level": "public",
        "status": "approved",
        "allowed_for_ingestion": True,
    }
    defaults.update(overrides)
    return Source(**defaults)  # type: ignore[arg-type]


def test_validate_source_returns_source_when_approved() -> None:
    source = make_source()
    validate = ValidateSource(InMemorySourceRepository([source]))

    result = validate("SRC-001")

    assert result == source


def test_validate_source_raises_when_not_found() -> None:
    validate = ValidateSource(InMemorySourceRepository([]))

    with pytest.raises(SourceNotFoundError):
        validate("SRC-UNKNOWN")


def test_validate_source_raises_when_not_approved() -> None:
    source = make_source(status="pending")
    validate = ValidateSource(InMemorySourceRepository([source]))

    with pytest.raises(SourceNotApprovedError):
        validate("SRC-001")


def test_validate_source_raises_when_not_allowed_for_ingestion() -> None:
    source = make_source(allowed_for_ingestion=False)
    validate = ValidateSource(InMemorySourceRepository([source]))

    with pytest.raises(SourceNotApprovedError):
        validate("SRC-001")
