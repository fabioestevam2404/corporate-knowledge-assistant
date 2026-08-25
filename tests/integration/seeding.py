"""Shared real-corpus seeding helper for integration tests.

Ingests + chunks + embeds the actual Block 1/2 sample documents into the
real Postgres+pgvector database via the real use cases — not fixtures with
pre-baked rows, so every test using this exercises the genuine pipeline.
"""

from pathlib import Path

from sqlalchemy.orm import Session

from cka.application.ingest_document import IngestDocument
from cka.application.process_document import ProcessDocument
from cka.application.validate_source import ValidateSource
from cka.infrastructure.database.chunk_repository import SqlAlchemyChunkRepository
from cka.infrastructure.database.document_repository import SqlAlchemyDocumentRepository
from cka.infrastructure.embeddings.embedding_service import EmbeddingService
from cka.infrastructure.processing.chunker import TextChunker
from cka.infrastructure.processing.pdf_loader import PdfDocumentLoader
from cka.infrastructure.processing.text_loader import PlainTextLoader
from cka.infrastructure.sources.yaml_source_repository import YamlSourceRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "data" / "sources" / "registry.yaml"
SAMPLES_DIR = REPO_ROOT / "data" / "raw" / "samples"

SAMPLES = [
    ("SRC-SAMPLE-001", "remote-work-policy.txt", "text/plain"),
    ("SRC-SAMPLE-002", "information-security-policy.txt", "text/plain"),
    ("SRC-SAMPLE-003", "executive-compensation-framework.txt", "text/plain"),
    ("SRC-SAMPLE-004", "expense-reimbursement-policy.pdf", "application/pdf"),
    ("SRC-SAMPLE-005", "adversarial-injection-sample.txt", "text/plain"),
]

ALL_SOURCE_IDS = frozenset(s[0] for s in SAMPLES)


def seed_full_corpus(db_session: Session, embedding_service: EmbeddingService) -> None:
    source_repository = YamlSourceRepository(REGISTRY_PATH)
    ingest = IngestDocument(
        ValidateSource(source_repository), SqlAlchemyDocumentRepository(db_session)
    )
    process = ProcessDocument(
        loaders=[PlainTextLoader(), PdfDocumentLoader()],
        chunker=TextChunker(),
        embedding_service=embedding_service,
        chunk_repository=SqlAlchemyChunkRepository(db_session),
    )

    for source_id, filename, content_type in SAMPLES:
        path = SAMPLES_DIR / filename
        document = ingest(
            source_id=source_id,
            filename=filename,
            content_type=content_type,
            content=path.read_bytes(),
        )
        # Flush so the document row physically exists before chunks
        # FK-reference it: DocumentModel/ChunkModel have no ORM relationship()
        # between them, so SQLAlchemy can't auto-order document-before-chunk
        # inserts within a single flush.
        db_session.flush()
        process(document, path)

    db_session.commit()
