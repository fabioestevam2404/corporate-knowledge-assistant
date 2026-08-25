import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from cka.api.dependencies import (
    DeleteDocumentDep,
    IngestDocumentDep,
    ProcessDocumentDep,
    require_permission,
)
from cka.application.delete_document import DocumentNotFoundError
from cka.domain.exceptions import SourceNotApprovedError, SourceNotFoundError
from cka.infrastructure.security.jwt import TokenPayload

router = APIRouter()

RequireWrite = Annotated[TokenPayload, Depends(require_permission("documents:write"))]
RequireDelete = Annotated[TokenPayload, Depends(require_permission("documents:delete"))]


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int


@router.post("/documents", response_model=DocumentResponse, status_code=201)
def upload_document(
    ingest_document: IngestDocumentDep,
    process_document: ProcessDocumentDep,
    _current_user: RequireWrite,
    source_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> DocumentResponse:
    content = file.file.read()
    filename = file.filename or "upload"

    try:
        document = ingest_document(
            source_id=source_id,
            filename=filename,
            content_type=file.content_type or "application/octet-stream",
            content=content,
        )
    except (SourceNotFoundError, SourceNotApprovedError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ProcessDocument's loaders read from a real path (page-aware PDF
    # extraction needs a real file, not just bytes) — the upload is only
    # ever in memory/a request-scoped temp file, cleaned up right after.
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        chunks = process_document(document, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return DocumentResponse(document_id=document.id, filename=filename, chunk_count=len(chunks))


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    delete_document_use_case: DeleteDocumentDep,
    _current_user: RequireDelete,
) -> None:
    try:
        delete_document_use_case(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
