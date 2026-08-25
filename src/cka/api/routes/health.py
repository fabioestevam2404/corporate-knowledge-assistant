from fastapi import APIRouter, Request, Response

from cka.infrastructure.database.connection import check_database_connection

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "corporate-knowledge-assistant"}


@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready")
def health_ready(request: Request, response: Response) -> dict[str, str]:
    engine = request.app.state.engine
    if check_database_connection(engine):
        return {"status": "ready"}

    response.status_code = 503
    return {"status": "not_ready"}
