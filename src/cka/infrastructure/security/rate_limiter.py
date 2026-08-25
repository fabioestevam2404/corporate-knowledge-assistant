import threading
import time


class RateLimiter:
    """In-memory sliding-window rate limiter, keyed by user_id (per ADR-009 —
    keying by user_id rather than IP, since users sit behind corporate NAT).

    Single-process only by design (Redis explicitly rejected for the MVP —
    see ADR-002); a multi-instance deployment would need a shared store.
    """

    def __init__(self, max_requests: int, window_seconds: float = 60.0) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            timestamps = self._hits.setdefault(key, [])
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)

            if len(timestamps) >= self._max_requests:
                return False

            timestamps.append(now)
            return True
