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


def test_process_real_text_document_end_to_end_with_real_embedding_model(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    source_repository = YamlSourceRepository(REGISTRY_PATH)
    ingest = IngestDocument(
        ValidateSource(source_repository), SqlAlchemyDocumentRepository(db_session)
    )
    process = ProcessDocument(
        loaders=[PlainTextLoader(), PdfDocumentLoader()],
        chunker=TextChunker(),
        embedding_service=real_embedding_service,
        chunk_repository=SqlAlchemyChunkRepository(db_session),
    )
    sample_path = SAMPLES_DIR / "remote-work-policy.txt"

    document = ingest(
        source_id="SRC-SAMPLE-001",
        filename=sample_path.name,
        content_type="text/plain",
        content=sample_path.read_bytes(),
    )
    db_session.commit()

    chunks = process(document, sample_path)
    db_session.commit()

    assert len(chunks) >= 1
    chunk_repository = SqlAlchemyChunkRepository(db_session)
    persisted = chunk_repository.get_by_document_id(document.id)
    assert len(persisted) == len(chunks)
    assert chunk_repository.count() == len(chunks)
    for chunk in persisted:
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 384


def test_process_real_pdf_document_preserves_page_numbers_in_postgres(
    db_session: Session, real_embedding_service: EmbeddingService
) -> None:
    source_repository = YamlSourceRepository(REGISTRY_PATH)
    ingest = IngestDocument(
        ValidateSource(source_repository), SqlAlchemyDocumentRepository(db_session)
    )
    process = ProcessDocument(
        loaders=[PlainTextLoader(), PdfDocumentLoader()],
        chunker=TextChunker(),
        embedding_service=real_embedding_service,
        chunk_repository=SqlAlchemyChunkRepository(db_session),
    )
    sample_path = SAMPLES_DIR / "expense-reimbursement-policy.pdf"

    document = ingest(
        source_id="SRC-SAMPLE-004",
        filename=sample_path.name,
        content_type="application/pdf",
        content=sample_path.read_bytes(),
    )
    db_session.commit()

    process(document, sample_path)
    db_session.commit()

    persisted = SqlAlchemyChunkRepository(db_session).get_by_document_id(document.id)
    page_numbers = {chunk.page_number for chunk in persisted}
    assert page_numbers == {1, 2}
