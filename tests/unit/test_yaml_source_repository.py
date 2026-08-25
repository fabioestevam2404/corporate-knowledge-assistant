from pathlib import Path

from cka.infrastructure.sources.yaml_source_repository import YamlSourceRepository

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "sources" / "registry.yaml"


def test_registry_loads_real_registry_file() -> None:
    repo = YamlSourceRepository(REGISTRY_PATH)

    sources = repo.list_sources()

    assert len(sources) >= 3
    assert {s.id for s in sources} >= {
        "SRC-SAMPLE-001",
        "SRC-SAMPLE-002",
        "SRC-SAMPLE-003",
    }


def test_get_by_id_returns_matching_source() -> None:
    repo = YamlSourceRepository(REGISTRY_PATH)

    source = repo.get_by_id("SRC-SAMPLE-001")

    assert source is not None
    assert source.status == "approved"
    assert source.allowed_for_ingestion is True


def test_get_by_id_returns_none_for_unknown_source() -> None:
    repo = YamlSourceRepository(REGISTRY_PATH)

    assert repo.get_by_id("SRC-DOES-NOT-EXIST") is None
