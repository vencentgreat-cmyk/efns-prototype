"""Offline coverage for Snowflake viewer authorization and persistence SQL."""

from __future__ import annotations

from contextlib import contextmanager

import pandas as pd
import pytest

from app.runtime import RuntimeConfigurationError, RuntimeMode, resolve_runtime_mode
from app.security import AuthorizationError, Role, User, UserValidationError
from app.snowflake_security import SnowflakeAuthStore
from data.connection import SqlExecutor


def user(role=Role.ADMIN, *, email="admin@nsegg.ca", active=True):
    return User("u-admin", email, "Admin", role, active, False, "2026-01-01", "2026-01-01", None)


def user_frame(user_id="u-1", email="person@nsegg.ca", role="Data Editor", active=True):
    return pd.DataFrame([{
        "USER_ID": user_id,
        "EMAIL": email,
        "DISPLAY_NAME": "Person",
        "ROLE": role,
        "ACTIVE": active,
        "CREATED_AT": "2026-01-01T00:00:00+00:00",
        "UPDATED_AT": "2026-01-01T00:00:00+00:00",
        "LAST_LOGIN_AT": None,
    }])


class QueueExecutor(SqlExecutor):
    runtime_name = "Offline Snowflake"

    def __init__(self, frames=()):
        self.frames = list(frames)
        self.calls = []
        self.commits = 0
        self.rollbacks = 0

    def query(self, sql, params=None):
        self.calls.append(("query", sql, tuple(params or ())))
        return self.frames.pop(0) if self.frames else pd.DataFrame()

    def execute(self, sql, params=None):
        self.calls.append(("execute", sql, tuple(params or ())))
        return 1

    def executemany(self, sql, rows, *, batch_size=500):
        self.calls.append(("executemany", sql, list(rows)))
        return 1

    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1

    @contextmanager
    def transaction(self):
        self.calls.append(("begin", "", ()))
        try:
            yield self
            self.commits += 1
        except Exception:
            self.rollbacks += 1
            raise


def test_runtime_mode_is_explicit_or_uses_viewer_identity():
    assert resolve_runtime_mode("local", "person@nsegg.ca") == RuntimeMode.LOCAL
    assert resolve_runtime_mode("snowflake", None) == RuntimeMode.SNOWFLAKE
    assert resolve_runtime_mode("auto", "person@nsegg.ca", True) == RuntimeMode.SNOWFLAKE
    assert resolve_runtime_mode("auto", "person@nsegg.ca", False) == RuntimeMode.LOCAL
    assert resolve_runtime_mode("auto", None, True) == RuntimeMode.LOCAL
    with pytest.raises(RuntimeConfigurationError):
        resolve_runtime_mode("invalid", None)


def test_snowflake_identity_requires_internal_active_user(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "EFNS_DEV")
    executor = QueueExecutor([user_frame(), user_frame(active=False)])
    store = SnowflakeAuthStore(executor)
    resolved = store.resolve_identity(" Person@NSEGG.CA ")
    assert resolved.email == "person@nsegg.ca"
    assert store.resolve_identity("person@nsegg.ca") is None
    before = len(executor.calls)
    assert store.resolve_identity("outsider@example.ca") is None
    assert len(executor.calls) == before
    assert executor.calls[0][2] == ("person@nsegg.ca",)


def test_snowflake_user_create_and_audit_are_bound_and_transactional():
    executor = QueueExecutor([pd.DataFrame(), pd.DataFrame(), user_frame()])
    store = SnowflakeAuthStore(executor)
    created, temporary_password = store.create_user(
        user(), " Person@NSEGG.CA ", "Person", Role.DATA_EDITOR
    )
    assert created.email == "person@nsegg.ca"
    assert temporary_password is None
    assert executor.commits == 1
    writes = [call for call in executor.calls if call[0] == "execute"]
    assert len(writes) == 2
    assert "person@nsegg.ca" not in writes[0][1]
    assert "person@nsegg.ca" in writes[0][2]
    assert writes[1][2][2] == "admin@nsegg.ca"


def test_snowflake_user_management_still_enforces_application_permissions():
    reporter = user(Role.REPORTING_VIEWER)
    store = SnowflakeAuthStore(QueueExecutor())
    with pytest.raises(AuthorizationError):
        store.list_users(reporter)
    inactive = user(Role.ADMIN, active=False)
    with pytest.raises(AuthorizationError):
        store.record_action(inactive, "UPDATE", "ACCOUNT")


def test_snowflake_audit_uses_bound_viewer_email_and_utc_database_timestamp():
    executor = QueueExecutor()
    store = SnowflakeAuthStore(executor)
    store.record_action(user(), "IMPORT", "PRODUCTION", "batch-1", {"rows": 3})
    write = next(call for call in executor.calls if call[0] == "execute")
    assert "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())" in write[1]
    assert "admin@nsegg.ca" not in write[1]
    assert write[2][2] == "admin@nsegg.ca"
    assert write[2][5] == "batch-1"


def test_snowflake_audit_binds_valid_json_when_details_are_omitted():
    executor = QueueExecutor()
    store = SnowflakeAuthStore(executor)
    store.record_action(user(), "CREATE", "ACCOUNT", "account-1")
    write = next(call for call in executor.calls if call[0] == "execute")
    assert "PARSE_JSON(%s)" in write[1]
    assert write[2][-1] == "{}"


def test_snowflake_user_update_delete_and_password_boundary():
    target = user_frame(user_id="u-target", role="Data Editor")
    updated = user_frame(user_id="u-target", role="Reporting Viewer", active=False)
    executor = QueueExecutor([target, updated, updated])
    store = SnowflakeAuthStore(executor)
    result = store.update_user(
        user(), "u-target", role=Role.REPORTING_VIEWER, active=False
    )
    assert result.role == Role.REPORTING_VIEWER
    assert result.active is False
    store.delete_user(user(), "u-target")
    writes = [call for call in executor.calls if call[0] == "execute"]
    assert any("UPDATE" in call[1] and call[2][-1] == "u-target" for call in writes)
    assert any("DELETE" in call[1] and call[2] == ("u-target",) for call in writes)
    with pytest.raises(UserValidationError, match="managed by Snowflake identity"):
        store.reset_temporary_password(user(), "u-target")
