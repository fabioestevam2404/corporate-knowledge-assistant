import structlog

from cka.domain.user_repository import UserRepository
from cka.infrastructure.security.jwt import create_access_token
from cka.infrastructure.security.password_hashing import hash_password, verify_password

logger = structlog.get_logger(__name__)

# A real Argon2id hash of an unguessable, never-used password. Verifying
# against this when the username doesn't exist keeps login timing roughly
# constant whether or not the account is real — otherwise "no such user"
# (fast, skips hashing) is distinguishable from "wrong password" (slow,
# hashes) by response time, leaking which usernames exist.
_DUMMY_HASH = hash_password("not-a-real-password-used-only-for-timing-normalization")


class InvalidCredentialsError(Exception):
    pass


class AuthenticateUser:
    """Verifies credentials and issues a JWT. Never logs the password, and
    logs the same generic failure for "user not found" and "wrong password"
    (AUTH_FAILURE audit event per ADR-009) so failed logins don't reveal
    which usernames exist — including via response timing.
    """

    def __init__(
        self, user_repository: UserRepository, secret_key: str, expire_minutes: int
    ) -> None:
        self._user_repository = user_repository
        self._secret_key = secret_key
        self._expire_minutes = expire_minutes

    def __call__(self, username: str, password: str) -> str:
        user = self._user_repository.get_by_username(username)
        password_hash = user.password_hash if user is not None else _DUMMY_HASH

        password_is_valid = verify_password(password, password_hash)

        if user is None or not user.active or not password_is_valid:
            logger.warning("auth_failure", username=username)
            raise InvalidCredentialsError()

        logger.info("auth_success", user_id=user.id, role=user.role)
        return create_access_token(user.id, user.role, self._secret_key, self._expire_minutes)
