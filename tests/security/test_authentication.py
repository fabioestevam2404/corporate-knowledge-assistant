import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cka.core.config import get_settings
from cka.domain.user import EMPLOYEE, User
from cka.infrastructure.database.user_repository import SqlAlchemyUserRepository
from cka.infrastructure.security.jwt import decode_access_token
from cka.infrastructure.security.password_hashing import hash_password
from cka.main import app


def _seed_user(db_session: Session, username: str, password: str, role: str = EMPLOYEE) -> str:
    user_id = str(uuid.uuid4())
    repo = SqlAlchemyUserRepository(db_session)
    repo.save(
        User(
            id=user_id,
            username=username,
            password_hash=hash_password(password),
            role=role,
            active=True,
        )
    )
    db_session.commit()
    return user_id


def test_login_with_real_seeded_user_and_argon2_hash_succeeds(db_session: Session) -> None:
    user_id = _seed_user(db_session, "real.employee", "a-real-strong-password")

    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"username": "real.employee", "password": "a-real-strong-password"},
        )

    assert response.status_code == 200
    body = response.json()
    payload = decode_access_token(body["access_token"], get_settings().jwt_secret_key)
    assert payload.user_id == user_id
    assert payload.role == EMPLOYEE


def test_login_with_wrong_password_is_rejected(db_session: Session) -> None:
    _seed_user(db_session, "real.employee2", "correct-password")

    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"username": "real.employee2", "password": "wrong-password"}
        )

    assert response.status_code == 401
    assert "access_token" not in response.json()


def test_login_with_unknown_username_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"username": "does-not-exist", "password": "anything"}
        )

    assert response.status_code == 401


def test_inactive_user_cannot_login(db_session: Session) -> None:
    user_id = str(uuid.uuid4())
    repo = SqlAlchemyUserRepository(db_session)
    repo.save(
        User(
            id=user_id,
            username="disabled.user",
            password_hash=hash_password("some-password"),
            role=EMPLOYEE,
            active=False,
        )
    )
    db_session.commit()

    with TestClient(app) as client:
        response = client.post(
            "/auth/login", json={"username": "disabled.user", "password": "some-password"}
        )

    assert response.status_code == 401


def test_expired_token_is_rejected_by_protected_endpoints() -> None:
    from cka.infrastructure.security.jwt import create_access_token

    settings = get_settings()
    expired_token = create_access_token(
        "some-user", EMPLOYEE, settings.jwt_secret_key, expire_minutes=-1
    )

    with TestClient(app) as client:
        response = client.post(
            "/retrieve",
            json={"query": "anything", "top_k": 3},
            headers={"Authorization": f"Bearer {expired_token}"},
        )

    assert response.status_code == 401


def test_malformed_bearer_token_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/retrieve",
            json={"query": "anything", "top_k": 3},
            headers={"Authorization": "Bearer not-a-real-jwt"},
        )

    assert response.status_code == 401
