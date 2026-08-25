from dataclasses import dataclass

EMPLOYEE = "employee"
MANAGER = "manager"
ADMIN = "admin"

ROLES = frozenset({EMPLOYEE, MANAGER, ADMIN})

# Permission strings per role (Sprint 09 spec).
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    EMPLOYEE: frozenset({"knowledge:read"}),
    MANAGER: frozenset({"knowledge:read", "knowledge:manager"}),
    ADMIN: frozenset(
        {
            "knowledge:read",
            "knowledge:manager",
            "documents:write",
            "documents:delete",
            "evaluation:read",
        }
    ),
}

# Document Source.access_level values each role may retrieve (the Access
# Matrix from the roadmap's Sprint 09 — see ADR-009). This is deliberately
# separate from ROLE_PERMISSIONS: RBAC alone is not document authorization.
ACCESS_LEVELS_BY_ROLE: dict[str, frozenset[str]] = {
    EMPLOYEE: frozenset({"public", "internal"}),
    MANAGER: frozenset({"public", "internal", "management"}),
    ADMIN: frozenset({"public", "internal", "management"}),
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


@dataclass(frozen=True)
class User:
    id: str
    username: str
    password_hash: str
    role: str
    active: bool
