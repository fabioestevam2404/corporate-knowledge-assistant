from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from cka.api.dependencies import get_rate_limiter
from cka.infrastructure.security.rate_limiter import RateLimiter
from cka.main import app


@pytest.fixture
def client_with_tiny_rate_limit() -> Iterator[TestClient]:
    # A real end-to-end 429 test shouldn't need to send 60 real requests to
    # prove the limiter is wired up — override with a small, real limiter
    # instance (same class, same enforce_rate_limit code path). The instance
    # is created once and captured by the lambda — creating a fresh one per
    # call (`lambda: RateLimiter(...)`) would give every request its own
    # empty limiter and the test would never actually see a 429.
    shared_limiter = RateLimiter(max_requests=2)
    app.dependency_overrides[get_rate_limiter] = lambda: shared_limiter
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_rate_limiter, None)


def test_requests_over_the_limit_get_429(
    client_with_tiny_rate_limit: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    headers = auth_headers("employee", user_id="rate-limit-test-user")

    first = client_with_tiny_rate_limit.post(
        "/retrieve", json={"query": "q1", "top_k": 3}, headers=headers
    )
    second = client_with_tiny_rate_limit.post(
        "/retrieve", json={"query": "q2", "top_k": 3}, headers=headers
    )
    third = client_with_tiny_rate_limit.post(
        "/retrieve", json={"query": "q3", "top_k": 3}, headers=headers
    )

    assert first.status_code in (200, 401, 422)  # not rate-limited yet
    assert second.status_code in (200, 401, 422)
    assert third.status_code == 429


def test_rate_limit_is_scoped_per_user(
    client_with_tiny_rate_limit: TestClient, auth_headers: Callable[..., dict[str, str]]
) -> None:
    user_a = auth_headers("employee", user_id="user-a")
    user_b = auth_headers("employee", user_id="user-b")

    client_with_tiny_rate_limit.post("/retrieve", json={"query": "q", "top_k": 3}, headers=user_a)
    client_with_tiny_rate_limit.post("/retrieve", json={"query": "q", "top_k": 3}, headers=user_a)
    exhausted = client_with_tiny_rate_limit.post(
        "/retrieve", json={"query": "q", "top_k": 3}, headers=user_a
    )
    still_fresh = client_with_tiny_rate_limit.post(
        "/retrieve", json={"query": "q", "top_k": 3}, headers=user_b
    )

    assert exhausted.status_code == 429
    assert still_fresh.status_code != 429
