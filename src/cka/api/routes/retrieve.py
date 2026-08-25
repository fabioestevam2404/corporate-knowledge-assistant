from fastapi import APIRouter
from pydantic import BaseModel, Field

from cka.api.dependencies import AccessScopeDep, RateLimitDep, RetrieveKnowledgeDep

router = APIRouter()


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalResponse(BaseModel):
    query: str
    results: list[dict[str, object]]


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(
    request: RetrievalRequest,
    retrieve_knowledge: RetrieveKnowledgeDep,
    access_scope: AccessScopeDep,
    _rate_limit: RateLimitDep,
) -> RetrievalResponse:
    results = retrieve_knowledge(request.query, access_scope, top_k=request.top_k)
    return RetrievalResponse(
        query=request.query,
        results=[
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "source_id": r.source_id,
                "content": r.content,
                "page_number": r.page_number,
                "chunk_index": r.chunk_index,
                "score": r.score,
            }
            for r in results
        ],
    )
