import time
import uuid

import structlog
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from cka.observability.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware:
    """Binds a request/trace id to structlog context and echoes it back to the client.

    Uses raw ASGI (not BaseHTTPMiddleware) so contextvars set here are visible to
    everything downstream in the same task, including exception handlers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        # Exposed via request.state so route handlers can reuse it as trace_id
        # without re-parsing headers (see api/routes/ask.py).
        request.state.request_id = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        status_holder = {"code": 0}

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                headers = message.setdefault("headers", [])
                headers.append((REQUEST_ID_HEADER.encode("latin-1"), request_id.encode("latin-1")))
            await send(message)

        logger.info("request_started")
        try:
            await self.app(scope, receive, send_with_header)
        finally:
            duration_seconds = time.perf_counter() - start
            logger.info("request_finished", duration_ms=round(duration_seconds * 1000, 2))

            path = request.url.path
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method, path=path, status_code=str(status_holder["code"])
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, path=path).observe(
                duration_seconds
            )

            structlog.contextvars.clear_contextvars()
