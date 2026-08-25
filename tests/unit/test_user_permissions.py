from cka.domain.user import ACCESS_LEVELS_BY_ROLE, ADMIN, EMPLOYEE, MANAGER, has_permission


def test_employee_can_read_knowledge_but_not_manage() -> None:
    assert has_permission(EMPLOYEE, "knowledge:read") is True
    assert has_permission(EMPLOYEE, "documents:write") is False


def test_manager_has_broader_permissions_than_employee() -> None:
    assert has_permission(MANAGER, "knowledge:read") is True
    assert has_permission(MANAGER, "knowledge:manager") is True
    assert has_permission(MANAGER, "documents:write") is False


def test_admin_has_document_write_and_delete() -> None:
    assert has_permission(ADMIN, "documents:write") is True
    assert has_permission(ADMIN, "documents:delete") is True


def test_unknown_role_has_no_permissions() -> None:
    assert has_permission("not-a-real-role", "knowledge:read") is False


def test_access_matrix_employee_excludes_management() -> None:
    assert "management" not in ACCESS_LEVELS_BY_ROLE[EMPLOYEE]
    assert "public" in ACCESS_LEVELS_BY_ROLE[EMPLOYEE]
    assert "internal" in ACCESS_LEVELS_BY_ROLE[EMPLOYEE]


def test_access_matrix_manager_includes_management() -> None:
    assert "management" in ACCESS_LEVELS_BY_ROLE[MANAGER]


def test_access_matrix_admin_sees_everything_manager_sees() -> None:
    assert ACCESS_LEVELS_BY_ROLE[ADMIN] >= ACCESS_LEVELS_BY_ROLE[MANAGER]
