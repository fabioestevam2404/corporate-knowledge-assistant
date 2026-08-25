from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    organization: str
    source_type: str
    url: str
    license: str
    access_level: str
    status: str
    allowed_for_ingestion: bool
