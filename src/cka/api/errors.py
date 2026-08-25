import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            error_type=type(exc).__name__,
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error."},
        )
