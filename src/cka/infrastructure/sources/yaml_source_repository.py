from pathlib import Path
from typing import Any

import yaml

from cka.domain.source import Source
from cka.domain.source_repository import SourceRepository


class YamlSourceRepository(SourceRepository):
    """Reads the governed Source Registry from a YAML file.

    See ADR-001 — sources are only ingestible when explicitly approved in the
    registry (status == "approved" and allowed_for_ingestion == True).
    """

    def __init__(self, registry_path: str | Path) -> None:
        self._registry_path = Path(registry_path)
        self._sources: dict[str, Source] | None = None

    def _load(self) -> dict[str, Source]:
        if self._sources is not None:
            return self._sources

        raw = yaml.safe_load(self._registry_path.read_text(encoding="utf-8")) or {}
        entries: list[dict[str, Any]] = raw.get("sources", [])

        sources = {
            entry["id"]: Source(
                id=entry["id"],
                name=entry["name"],
                organization=entry["organization"],
                source_type=entry["source_type"],
                url=entry["url"],
                license=entry["license"],
                access_level=entry["access_level"],
                status=entry["status"],
                allowed_for_ingestion=bool(entry["allowed_for_ingestion"]),
            )
            for entry in entries
        }
        self._sources = sources
        return sources

    def get_by_id(self, source_id: str) -> Source | None:
        return self._load().get(source_id)

    def list_sources(self) -> list[Source]:
        return list(self._load().values())
