from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

ALGORITHM = "HS256"


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenPayload:
    user_id: str
    role: str


def create_access_token(user_id: str, role: str, secret_key: str, expire_minutes: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    try:
        return TokenPayload(user_id=payload["sub"], role=payload["role"])
    except KeyError as exc:
        raise InvalidTokenError(f"missing claim: {exc}") from exc
