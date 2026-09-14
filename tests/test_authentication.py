"""Prototype authentication, role, user-management, and audit tests."""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from app.security import (
    DEFAULT_USER_SEEDS,
    AuthenticationError,
    AuthorizationError,
    Permission,
    Role,
    SQLiteAuthStore,
    UserSeed,
    UserValidationError,
    generate_temporary_password,
    has_permission,
    hash_password,
    validate_internal_email,
    verify_password,
)
from app.services.authorized_repository import AuthorizedRepository
from data.repositories.base import RepositoryError


@pytest.fixture
def auth_context(tmp_path):
    passwords = {role: generate_temporary_password() for role in Role}
    seeds = [
        UserSeed(
            f"test.{role.name.casefold()}@nsegg.ca",
            f"Test {role.value}",
            role,
            hash_password(passwords[role]),
        )
        for role in Role
    ]
    store = SQLiteAuthStore(tmp_path / "auth.db", seeds=seeds)
    users = {}
    tokens = {}
    for role in Role:
        users[role], tokens[role] = store.login(
            f"test.{role.name.casefold()}@nsegg.ca", passwords[role]
        )
    return store, users, tokens


def test_only_internal_email_domain_is_valid():
    assert validate_internal_email(" Person@NSEGG.CA ") == "person@nsegg.ca"
    for invalid in ("person@example.ca", "person@nsegg.ca.example.org", "@nsegg.ca", "person@@nsegg.ca"):
        with pytest.raises(UserValidationError, match="@nsegg.ca"):
            validate_internal_email(invalid)


def test_password_hashing_is_salted_and_verifiable():
    password = generate_temporary_password()
    first = hash_password(password)
    second = hash_password(password)
    assert password not in first
    assert first != second
    assert verify_password(password, first)
    assert not verify_password(generate_temporary_password(), first)


def test_default_accounts_contain_hashes_only_and_expected_roles(tmp_path):
    assert {seed.email for seed in DEFAULT_USER_SEEDS} == {
        "prototype.admin@nsegg.ca",
        "prototype.editor@nsegg.ca",
        "prototype.reporter@nsegg.ca",
        "prototype.developer@nsegg.ca",
    }
    assert {seed.role for seed in DEFAULT_USER_SEEDS} == set(Role)
    assert all(seed.password_hash.startswith("pbkdf2_sha256$600000$") for seed in DEFAULT_USER_SEEDS)
    store = SQLiteAuthStore(tmp_path / "seeded.db")
    with sqlite3.connect(store.database_path) as database:
        values = database.execute("SELECT email, password_hash FROM app_user").fetchall()
    assert len(values) == 4
    assert all(email not in password_hash for email, password_hash in values)


def test_login_session_logout_and_generic_failures(auth_context):
    store, users, tokens = auth_context
    reporter = users[Role.REPORTING_VIEWER]
    token = tokens[Role.REPORTING_VIEWER]
    assert store.resolve_session(token).user_id == reporter.user_id
    store.logout(token)
    assert store.resolve_session(token) is None
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        store.login(reporter.email, generate_temporary_password())
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        store.login("outsider@example.ca", generate_temporary_password())


def test_role_permission_matrix(auth_context):
    _, users, _ = auth_context
    admin = users[Role.ADMIN]
    editor = users[Role.DATA_EDITOR]
    reporter = users[Role.REPORTING_VIEWER]
    developer = users[Role.DEVELOPER]
    assert all(has_permission(admin, permission) for permission in Permission)
    assert has_permission(editor, Permission.IMPORT_DATA)
    assert has_permission(editor, Permission.CREATE_DATA)
    assert not has_permission(editor, Permission.DELETE_DATA)
    assert has_permission(reporter, Permission.VIEW_REPORTS)
    assert not has_permission(reporter, Permission.UPDATE_DATA)
    assert has_permission(developer, Permission.USE_PROFILER)
    assert has_permission(developer, Permission.VIEW_DIAGNOSTICS)
    assert has_permission(developer, Permission.VIEW_AUDIT)
    assert not has_permission(developer, Permission.MANAGE_USERS)


def test_admin_user_management_and_session_revocation(auth_context):
    store, users, _ = auth_context
    admin = users[Role.ADMIN]
    reporter = users[Role.REPORTING_VIEWER]
    created, temporary = store.create_user(
        admin, "new.user@nsegg.ca", "New User", Role.DATA_EDITOR
    )
    assert temporary not in created.email
    logged_in, token = store.login(created.email, temporary)
    assert logged_in.must_change_password
    updated = store.update_user(admin, created.user_id, role=Role.REPORTING_VIEWER, active=True)
    assert updated.role == Role.REPORTING_VIEWER
    reset = store.reset_temporary_password(admin, created.user_id)
    assert store.resolve_session(token) is None
    assert store.login(created.email, reset)[0].must_change_password
    store.delete_user(admin, created.user_id)
    assert store.get_user(created.user_id) is None
    with pytest.raises(AuthorizationError):
        store.list_users(reporter)


def test_admin_cannot_create_external_delete_self_or_remove_last_admin(auth_context):
    store, users, _ = auth_context
    admin = users[Role.ADMIN]
    with pytest.raises(UserValidationError, match="@nsegg.ca"):
        store.create_user(admin, "external@example.ca", "External", Role.DATA_EDITOR)
    with pytest.raises(UserValidationError, match="own account"):
        store.delete_user(admin, admin.user_id)
    with pytest.raises(UserValidationError, match="active Admin"):
        store.update_user(admin, admin.user_id, role=Role.REPORTING_VIEWER, active=True)


class FakeRepository:
    def __init__(self):
        self.calls = []

    def get_accounts(self):
        self.calls.append("get")
        return pd.DataFrame()

    def upsert_account(self, record):
        self.calls.append("upsert")
        return record.get("ACCOUNT_ID") or "new-account"

    def delete_account(self, account_id):
        self.calls.append("delete")
        return True

    def import_production_bundle(self, *args, **kwargs):
        self.calls.append("import")
        return "import-1", 2

    def check_connection(self):
        self.calls.append("diagnostics")


def test_repository_proxy_enforces_writes_and_records_audit(auth_context):
    store, users, _ = auth_context
    repository = FakeRepository()
    reporter_repo = AuthorizedRepository(repository, store, users[Role.REPORTING_VIEWER])
    assert reporter_repo.get_accounts().empty
    with pytest.raises(RepositoryError, match="permission"):
        reporter_repo.upsert_account({"ORGANIZATION_NAME": "Blocked"})
    assert "upsert" not in repository.calls

    editor_repo = AuthorizedRepository(repository, store, users[Role.DATA_EDITOR])
    assert editor_repo.upsert_account({"ORGANIZATION_NAME": "Created"}) == "new-account"
    assert editor_repo.upsert_account({"ACCOUNT_ID": "a1"}) == "a1"
    assert editor_repo.import_production_bundle({}, [], pd.DataFrame()) == ("import-1", 2)
    with pytest.raises(RepositoryError, match="permission"):
        editor_repo.delete_account("a1")

    admin_repo = AuthorizedRepository(repository, store, users[Role.ADMIN])
    assert admin_repo.delete_account("a1")
    actions = [event.action for event in store.list_audit(users[Role.ADMIN])]
    assert {"CREATE", "UPDATE", "IMPORT", "DELETE"}.issubset(actions)


def test_audit_visibility_and_user_management_events(auth_context):
    store, users, _ = auth_context
    admin = users[Role.ADMIN]
    developer = users[Role.DEVELOPER]
    reporter = users[Role.REPORTING_VIEWER]
    created, _ = store.create_user(admin, "audit.user@nsegg.ca", "Audit User", Role.DATA_EDITOR)
    store.update_user(admin, created.user_id, role=Role.DATA_EDITOR, active=False)
    actions = {event.action for event in store.list_audit(developer)}
    assert {"CREATE_USER", "UPDATE_USER", "LOGIN"}.issubset(actions)
    with pytest.raises(AuthorizationError):
        store.list_audit(reporter)
