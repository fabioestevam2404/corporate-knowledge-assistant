from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from cka.api.dependencies import AccessScopeDep, AskKnowledgeBaseDep, RateLimitDep
from cka.core.config import get_settings
from cka.observability.tracing import current_trace_id

router = APIRouter()


class AskRequest(BaseModel):
    query: str = Field(min_length=1)


class SourceReferenceResponse(BaseModel):
    document_id: str
    page_number: int | None
    chunk_id: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceReferenceResponse]
    confidence: str
    grounded: bool
    trace_id: str


@router.post("/ask", response_model=AskResponse)
def ask(
    request_body: AskRequest,
    request: Request,
    ask_knowledge_base: AskKnowledgeBaseDep,
    access_scope: AccessScopeDep,
    _rate_limit: RateLimitDep,
) -> AskResponse:
    settings = get_settings()
    if len(request_body.query) > settings.max_query_length:
        raise HTTPException(status_code=400, detail="Query exceeds maximum allowed length.")

    # Real OpenTelemetry trace id (see main.py's FastAPIInstrumentor) — falls
    # back to the request-id correlation from Block 1/2's middleware only if
    # tracing somehow produced no active span (should not happen in normal
    # operation).
    trace_id = current_trace_id() or request.state.request_id

    result = ask_knowledge_base(request_body.query, access_scope, trace_id)

    return AskResponse(
        answer=result.answer,
        sources=[
            SourceReferenceResponse(
                document_id=s.document_id, page_number=s.page_number, chunk_id=s.chunk_id
            )
            for s in result.sources
        ],
        confidence=result.confidence,
        grounded=result.grounded,
        trace_id=trace_id,
    )
