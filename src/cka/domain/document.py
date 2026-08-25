from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Document:
    id: str
    source_id: str
    filename: str
    content_type: str
    sha256: str
    ingested_at: datetime
