import time

import pytest

from cka.application.authenticate_user import AuthenticateUser, InvalidCredentialsError
from cka.domain.user import User
from cka.domain.user_repository import UserRepository
from cka.infrastructure.security.jwt import decode_access_token
from cka.infrastructure.security.password_hashing import hash_password

SECRET = "test-secret-key"


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: list[User]) -> None:
        self._users = {u.username: u for u in users}

    def get_by_username(self, username: str) -> User | None:
        return self._users.get(username)

    def save(self, user: User) -> None:
        self._users[user.username] = user


def make_user(**overrides: object) -> User:
    defaults: dict[str, object] = {
        "id": "user-1",
        "username": "alice",
        "password_hash": hash_password("correct-password"),
        "role": "employee",
        "active": True,
    }
    defaults.update(overrides)
    return User(**defaults)  # type: ignore[arg-type]


def test_valid_credentials_return_a_decodable_token() -> None:
    authenticate = AuthenticateUser(
        InMemoryUserRepository([make_user()]), SECRET, expire_minutes=30
    )

    token = authenticate("alice", "correct-password")

    payload = decode_access_token(token, SECRET)
    assert payload.user_id == "user-1"
    assert payload.role == "employee"


def test_wrong_password_raises_invalid_credentials() -> None:
    authenticate = AuthenticateUser(
        InMemoryUserRepository([make_user()]), SECRET, expire_minutes=30
    )

    with pytest.raises(InvalidCredentialsError):
        authenticate("alice", "wrong-password")


def test_unknown_username_raises_invalid_credentials() -> None:
    authenticate = AuthenticateUser(InMemoryUserRepository([]), SECRET, expire_minutes=30)

    with pytest.raises(InvalidCredentialsError):
        authenticate("ghost", "anything")


def test_inactive_user_cannot_authenticate() -> None:
    authenticate = AuthenticateUser(
        InMemoryUserRepository([make_user(active=False)]), SECRET, expire_minutes=30
    )

    with pytest.raises(InvalidCredentialsError):
        authenticate("alice", "correct-password")


def test_unknown_and_wrong_password_take_similar_time() -> None:
    # Regression guard for the username-enumeration timing side-channel:
    # both paths must run password verification, not short-circuit.
    authenticate = AuthenticateUser(
        InMemoryUserRepository([make_user()]), SECRET, expire_minutes=30
    )

    start = time.perf_counter()
    with pytest.raises(InvalidCredentialsError):
        authenticate("ghost", "anything")
    unknown_user_duration = time.perf_counter() - start

    start = time.perf_counter()
    with pytest.raises(InvalidCredentialsError):
        authenticate("alice", "wrong-password")
    wrong_password_duration = time.perf_counter() - start

    # Both involve a real Argon2 hash verification; allow generous slack
    # since this is a coarse, environment-sensitive signal, not a precise
    # timing-attack benchmark.
    assert unknown_user_duration > wrong_password_duration * 0.5
