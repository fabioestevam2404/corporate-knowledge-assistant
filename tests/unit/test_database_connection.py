from cka.infrastructure.database.connection import check_database_connection, make_engine


def test_check_database_connection_returns_false_for_unreachable_database() -> None:
    engine = make_engine("postgresql+psycopg://cka:cka@localhost:1/cka")

    assert check_database_connection(engine) is False


def test_health_ready_returns_503_when_database_unreachable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://cka:cka@localhost:1/cka")

    from cka.core.config import get_settings

    get_settings.cache_clear()

    from fastapi.testclient import TestClient

    from cka.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}

    get_settings.cache_clear()
