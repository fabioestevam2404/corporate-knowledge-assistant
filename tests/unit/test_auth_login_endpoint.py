from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cka.api.dependencies import get_user_repository
from cka.domain.user import EMPLOYEE, User
from cka.domain.user_repository import UserRepository
from cka.infrastructure.security.jwt import decode_access_token
from cka.infrastructure.security.password_hashing import hash_password
from cka.main import app

SECRET = "dev-only-insecure-secret-change-me"  # matches Settings default


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: list[User]) -> None:
        self._users = {u.username: u for u in users}

    def get_by_username(self, username: str) -> User | None:
        return self._users.get(username)

    def save(self, user: User) -> None:
        self._users[user.username] = user


@pytest.fixture
def client() -> Iterator[TestClient]:
    repo = InMemoryUserRepository(
        [
            User(
                id="user-1",
                username="alice",
                password_hash=hash_password("correct-password"),
                role=EMPLOYEE,
                active=True,
            )
        ]
    )
    app.dependency_overrides[get_user_repository] = lambda: repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_user_repository, None)


def test_login_with_correct_credentials_returns_a_valid_token(client: TestClient) -> None:
    response = client.post(
        "/auth/login", json={"username": "alice", "password": "correct-password"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    payload = decode_access_token(body["access_token"], SECRET)
    assert payload.user_id == "user-1"
    assert payload.role == EMPLOYEE


def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "alice", "password": "wrong"})

    assert response.status_code == 401


def test_login_with_unknown_username_returns_401(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "ghost", "password": "anything"})

    assert response.status_code == 401
