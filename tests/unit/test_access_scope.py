from cka.application.access_scope import build_access_scope_for_user
from cka.domain.source import Source
from cka.domain.source_repository import SourceRepository
from cka.domain.user import ADMIN, EMPLOYEE, MANAGER


class InMemorySourceRepository(SourceRepository):
    def __init__(self, sources: list[Source]) -> None:
        self._sources = {s.id: s for s in sources}

    def get_by_id(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def list_sources(self) -> list[Source]:
        return list(self._sources.values())


def make_source(**overrides: object) -> Source:
    defaults: dict[str, object] = {
        "id": "SRC-1",
        "name": "Sample",
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


CORPUS = [
    make_source(id="SRC-PUBLIC", access_level="public"),
    make_source(id="SRC-INTERNAL", access_level="internal"),
    make_source(id="SRC-MANAGEMENT", access_level="management"),
]


def test_employee_scope_excludes_management_source() -> None:
    scope = build_access_scope_for_user("u1", EMPLOYEE, InMemorySourceRepository(CORPUS))

    assert "SRC-MANAGEMENT" not in scope.allowed_source_ids
    assert "SRC-PUBLIC" in scope.allowed_source_ids
    assert "SRC-INTERNAL" in scope.allowed_source_ids


def test_manager_scope_includes_management_source() -> None:
    scope = build_access_scope_for_user("u1", MANAGER, InMemorySourceRepository(CORPUS))

    assert "SRC-MANAGEMENT" in scope.allowed_source_ids


def test_admin_scope_includes_everything() -> None:
    scope = build_access_scope_for_user("u1", ADMIN, InMemorySourceRepository(CORPUS))

    assert scope.allowed_source_ids == {"SRC-PUBLIC", "SRC-INTERNAL", "SRC-MANAGEMENT"}


def test_scope_excludes_unapproved_source_regardless_of_role() -> None:
    corpus = [*CORPUS, make_source(id="SRC-PENDING", access_level="public", status="pending")]

    scope = build_access_scope_for_user("u1", ADMIN, InMemorySourceRepository(corpus))

    assert "SRC-PENDING" not in scope.allowed_source_ids


def test_scope_carries_user_id_and_role() -> None:
    scope = build_access_scope_for_user("u42", MANAGER, InMemorySourceRepository(CORPUS))

    assert scope.user_id == "u42"
    assert scope.role == MANAGER
