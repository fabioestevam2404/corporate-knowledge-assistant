import time

from cka.infrastructure.security.rate_limiter import RateLimiter


def test_allows_requests_under_the_limit() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60)

    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is True


def test_blocks_requests_over_the_limit() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is False


def test_limits_are_independent_per_key() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    assert limiter.allow("user-1") is True
    assert limiter.allow("user-2") is True  # different user, own budget
    assert limiter.allow("user-1") is False


def test_old_hits_expire_out_of_the_window() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=0.2)

    assert limiter.allow("user-1") is True
    assert limiter.allow("user-1") is False

    time.sleep(0.25)

    assert limiter.allow("user-1") is True
