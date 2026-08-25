"""Seeds one real user per role, for real login/RBAC/ACL testing.

Passwords are generated randomly and printed once (never stored in the repo,
never logged, never reused). Run with: uv run python scripts/seed_users.py

Re-running is safe: existing usernames are left untouched (not reset).
"""

import secrets
import uuid

from cka.core.config import get_settings
from cka.domain.user import ADMIN, EMPLOYEE, MANAGER, User
from cka.infrastructure.database.connection import make_engine, make_session_factory
from cka.infrastructure.database.user_repository import SqlAlchemyUserRepository
from cka.infrastructure.security.password_hashing import hash_password

SEED_USERS = [
    ("employee.test", EMPLOYEE),
    ("manager.test", MANAGER),
    ("admin.test", ADMIN),
]


def main() -> None:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session = make_session_factory(engine)()
    repository = SqlAlchemyUserRepository(session)

    print("Seeding test users (test-only accounts, not for production use):\n")
    for username, role in SEED_USERS:
        if repository.get_by_username(username) is not None:
            print(f"  {username} ({role}): already exists, skipped")
            continue

        password = secrets.token_urlsafe(16)
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=hash_password(password),
            role=role,
            active=True,
        )
        repository.save(user)
        print(f"  {username} ({role}): password = {password}")

    session.commit()
    print("\nDone. These passwords are shown only this once — save them if you need them.")


if __name__ == "__main__":
    main()
