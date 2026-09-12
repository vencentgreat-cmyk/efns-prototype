"""Fully offline coverage for Snowflake runtime discovery and SQL executors."""

from __future__ import annotations

from contextlib import contextmanager
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

import data.connection as connection
from data.repositories.base import (
    RepositoryConfigurationError,
    RepositoryConnectionError,
    RepositoryError,
)


ENV_NAMES = (
    "SNOWFLAKE_CONNECTION_NAME",
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_AUTHENTICATOR",
    "SNOWFLAKE_PRIVATE_KEY_FILE",
    "SNOWFLAKE_PRIVATE_KEY_FILE_PWD",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_STREAMLIT_CONNECTION",
)


@pytest.fixture(autouse=True)
def clean_snowflake_environment(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_settings_defaults_are_unconfigured():
    settings = connection.SnowflakeSettings.from_env()
    assert settings.database == "EFNS_DEV"
    assert settings.connection_name is None
    assert settings.configured is False


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"SNOWFLAKE_CONNECTION_NAME": "efns_dev"}, {"connection_name": "efns_dev", "autocommit": False}),
        (
            {"SNOWFLAKE_ACCOUNT": "org-account", "SNOWFLAKE_USER": "dev", "SNOWFLAKE_PASSWORD": "secret"},
            {"account": "org-account", "user": "dev", "password": "secret"},
        ),
        (
            {"SNOWFLAKE_ACCOUNT": "org-account", "SNOWFLAKE_USER": "dev", "SNOWFLAKE_AUTHENTICATOR": "externalbrowser"},
            {"account": "org-account", "user": "dev", "authenticator": "externalbrowser"},
        ),
        (
            {"SNOWFLAKE_ACCOUNT": "org-account", "SNOWFLAKE_USER": "dev", "SNOWFLAKE_PRIVATE_KEY_FILE": "key.p8"},
            {"account": "org-account", "user": "dev", "private_key_file": "key.p8"},
        ),
    ],
)
def test_supported_settings_are_configured(monkeypatch, values, expected):
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    settings = connection.SnowflakeSettings.from_env()
    assert settings.configured is True
    kwargs = settings.connector_kwargs()
    assert all(kwargs[key] == value for key, value in expected.items())
    assert all(value is not None and value != "" for value in kwargs.values())


def test_settings_require_account_and_user(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "secret")
    with pytest.raises(RepositoryConfigurationError, match="account and user"):
        connection.SnowflakeSettings.from_env().connector_kwargs()


def test_settings_require_authentication(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "org-account")
    monkeypatch.setenv("SNOWFLAKE_USER", "dev")
    with pytest.raises(RepositoryConfigurationError, match="authentication"):
        connection.SnowflakeSettings.from_env().connector_kwargs()


class FakeCursor:
    def __init__(self, *, rows=None, description=None, rowcount=0, failure=None):
        self.rows = list(rows or [])
        self.description = description or []
        self.rowcount = rowcount
        self.failure = failure
        self.calls = []
        self.closed = False

    def execute(self, sql, params=()):
        self.calls.append(("execute", sql, params))
        if self.failure:
            raise self.failure
        return self

    def executemany(self, sql, rows):
        self.calls.append(("executemany", sql, list(rows)))
        if self.failure:
            raise self.failure
        return self

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor=None):
        self.cursor_value = cursor or FakeCursor()
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_connector_query_labels_dataframe():
    cursor = FakeCursor(rows=[(1, "A")], description=[("ID",), ("NAME",)])
    executor = connection.ConnectorExecutor(lambda: FakeConnection(cursor))
    result = executor.query("SELECT %s, %s", (1, "A"))
    pd.testing.assert_frame_equal(result, pd.DataFrame({"ID": [1], "NAME": ["A"]}))


def test_connector_execute_and_executemany_counts():
    cursor = FakeCursor(rowcount=2)
    executor = connection.ConnectorExecutor(lambda: FakeConnection(cursor))
    assert executor.execute("DELETE FROM T WHERE ID = %s", (1,)) == 2
    assert executor.executemany("INSERT INTO T VALUES (%s, %s)", ((i, str(i)) for i in range(3))) == 2


def test_connector_commit_rollback_and_transaction():
    db = FakeConnection()
    executor = connection.ConnectorExecutor(lambda: db)
    executor.commit()
    executor.rollback()
    with executor.transaction():
        pass
    assert (db.commits, db.rollbacks) == (2, 1)


def test_connector_failed_transaction_rolls_back():
    db = FakeConnection()
    executor = connection.ConnectorExecutor(lambda: db)
    with pytest.raises(RuntimeError, match="failed"):
        with executor.transaction():
            raise RuntimeError("failed")
    assert (db.commits, db.rollbacks) == (0, 1)


def test_connector_wraps_operation_and_connection_failures():
    executor = connection.ConnectorExecutor(lambda: (_ for _ in ()).throw(RuntimeError("network secret")))
    with pytest.raises(RepositoryConnectionError, match="connection failed"):
        executor.query("SELECT 1")

    original = RepositoryError("safe existing error")
    executor = connection.ConnectorExecutor(lambda: FakeConnection(FakeCursor(failure=original)))
    with pytest.raises(RepositoryError) as captured:
        executor.execute("SELECT 1")
    assert captured.value is original


@pytest.mark.parametrize(
    "rows",
    [
        [(1,), (2, 3)],
        [(1,)],
    ],
)
def test_connector_executemany_rejects_bad_row_shapes(rows):
    executor = connection.ConnectorExecutor(lambda: FakeConnection())
    with pytest.raises(RepositoryError, match="number of values|bind count"):
        executor.executemany("INSERT INTO T VALUES (%s, %s)", rows)


def test_connector_placeholder_count_ignores_quoted_text_and_empty_rows():
    cursor = FakeCursor(rowcount=-1)
    executor = connection.ConnectorExecutor(lambda: FakeConnection(cursor))
    sql = "INSERT INTO T VALUES (%s, 'literal %s', \"identifier%s\")"
    assert executor.executemany(sql, [(1,)]) == 1
    before = len(cursor.calls)
    assert executor.executemany("INSERT INTO T VALUES (%s)", []) == 0
    assert len(cursor.calls) == before


class FakeRow:
    def __init__(self, **values):
        self.values = values

    def as_dict(self):
        return dict(self.values)


class FakeStatement:
    def __init__(self, rows, columns):
        self._rows = list(rows)
        self.schema = SimpleNamespace(fields=[SimpleNamespace(name=name) for name in columns])

    def collect(self):
        return list(self._rows)


class FakeSession:
    def __init__(self, responder=None):
        self.calls = []
        self.responder = responder or (lambda sql, params: FakeStatement([], []))

    def sql(self, text, params=None):
        parameters = list(params or [])
        self.calls.append((text, parameters))
        return self.responder(text, parameters)


def test_snowpark_query_converts_binds_and_preserves_schema():
    def respond(sql, params):
        assert sql == "SELECT ? AS ID, '%s' AS EXAMPLE"
        assert params == [7]
        return FakeStatement([FakeRow(ID=7, NAME="A")], ["ID", "NAME"])

    executor = connection.SnowparkExecutor(FakeSession(respond))
    result = executor.query("SELECT %s AS ID, '%s' AS EXAMPLE", (7,))
    pd.testing.assert_frame_equal(result, pd.DataFrame({"ID": [7], "NAME": ["A"]}))

    empty = connection.SnowparkExecutor(
        FakeSession(lambda sql, params: FakeStatement([], ["ID", "NAME"]))
    ).query("SELECT 1")
    assert list(empty.columns) == ["ID", "NAME"]


def test_snowpark_execute_and_transactions():
    def respond(sql, params):
        if sql.startswith("UPDATE"):
            return FakeStatement([FakeRow(**{"number of rows updated": 3})], ["number of rows updated"])
        return FakeStatement([], [])

    session = FakeSession(respond)
    executor = connection.SnowparkExecutor(session)
    assert executor.execute("UPDATE T SET A = %s", (1,)) == 3
    with executor.transaction():
        pass
    assert [call[0] for call in session.calls[-2:]] == ["BEGIN", "COMMIT"]


def test_snowpark_failed_transaction_rolls_back():
    session = FakeSession()
    executor = connection.SnowparkExecutor(session)
    with pytest.raises(RuntimeError):
        with executor.transaction():
            raise RuntimeError("failed")
    assert [call[0] for call in session.calls] == ["BEGIN", "ROLLBACK"]


def test_snowpark_preserves_repository_errors_and_wraps_other_errors():
    existing = RepositoryError("safe")
    with pytest.raises(RepositoryError) as captured:
        connection.SnowparkExecutor(FakeSession(lambda sql, params: (_ for _ in ()).throw(existing))).query("SELECT 1")
    assert captured.value is existing

    with pytest.raises(RepositoryError, match="operation failed"):
        connection.SnowparkExecutor(FakeSession(lambda sql, params: (_ for _ in ()).throw(RuntimeError("secret")))).query("SELECT 1")


def test_snowpark_executemany_batches_nested_values():
    def respond(sql, params):
        count = sql.count("PARSE_JSON(?)")
        return FakeStatement([FakeRow(**{"number of rows inserted": count})], [])

    session = FakeSession(respond)
    executor = connection.SnowparkExecutor(session)
    rows = [(1, '{"a":1}'), (2, '{"a":2}'), (3, '{"a":3}')]
    result = executor.executemany(
        "INSERT INTO T (ID, RAW) VALUES (%s, PARSE_JSON(%s))",
        (row for row in rows),
        batch_size=2,
    )
    assert result == 3
    assert len(session.calls) == 2
    assert session.calls[0][1] == [1, '{"a":1}', 2, '{"a":2}']
    assert session.calls[1][1] == [3, '{"a":3}']


def test_snowpark_executemany_rejects_invalid_input_without_execution():
    session = FakeSession()
    executor = connection.SnowparkExecutor(session)
    with pytest.raises(RepositoryError, match="INSERT statement"):
        executor.executemany("UPDATE T SET A = %s", [(1,)])
    with pytest.raises(RepositoryError, match="same number"):
        executor.executemany("INSERT INTO T VALUES (%s, %s)", [(1, 2), (3,)])
    with pytest.raises(RepositoryError, match="bind count"):
        executor.executemany("INSERT INTO T VALUES (%s, %s)", [(1,)])
    assert executor.executemany("INSERT INTO T VALUES (%s)", []) == 0
    assert session.calls == []


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([], 0),
        ([FakeRow(**{"number of rows inserted": 2})], 2),
        ([FakeRow(**{"number of rows updated": 3})], 3),
        ([FakeRow(**{"number of rows deleted": 4})], 4),
        ([FakeRow(**{"number of rows inserted": 2, "number of rows updated": 3})], 5),
        ([FakeRow(status="ok")], -1),
    ],
)
def test_affected_row_formats(rows, expected):
    assert connection._affected_rows(rows) == expected


def configured_settings():
    return connection.SnowflakeSettings(
        connection_name="efns_dev", account=None, user=None, password=None,
        authenticator=None, private_key_file=None, private_key_file_pwd=None,
        warehouse=None, database="EFNS_DEV", role=None,
    )


def test_runtime_resolution_prefers_streamlit_connection(monkeypatch):
    session = FakeSession()
    fake_streamlit = SimpleNamespace(connection=lambda name, type: SimpleNamespace(session=lambda: session))
    monkeypatch.setattr(connection, "_streamlit_runtime_active", lambda: True)
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    resolved = connection._resolve_executor(configured_settings())
    assert isinstance(resolved, connection.SnowparkExecutor)
    assert resolved.runtime_name == "Streamlit Connection"


def test_missing_streamlit_runtime_falls_through_to_warehouse(monkeypatch):
    import snowflake.snowpark.context as context

    class StreamlitAPIException(Exception):
        error_id = "snowflake-missing-connection-config"

    monkeypatch.setattr(connection, "_streamlit_runtime_active", lambda: True)
    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(connection=lambda *args, **kwargs: (_ for _ in ()).throw(StreamlitAPIException())),
    )
    monkeypatch.setattr(context, "get_active_session", lambda: FakeSession())
    assert connection._resolve_executor(configured_settings()).runtime_name == "Warehouse Session"


def test_runtime_resolution_uses_warehouse_then_connector(monkeypatch):
    import snowflake.snowpark.context as context

    monkeypatch.setattr(connection, "_streamlit_runtime_active", lambda: False)
    monkeypatch.setattr(context, "get_active_session", lambda: FakeSession())
    assert connection._resolve_executor(configured_settings()).runtime_name == "Warehouse Session"

    class SnowparkSessionException(Exception):
        pass

    monkeypatch.setattr(context, "get_active_session", lambda: (_ for _ in ()).throw(SnowparkSessionException()))
    assert isinstance(connection._resolve_executor(configured_settings()), connection.ConnectorExecutor)


def test_runtime_resolution_does_not_hide_real_errors(monkeypatch):
    monkeypatch.setattr(connection, "_streamlit_runtime_active", lambda: True)
    monkeypatch.setitem(
        sys.modules,
        "streamlit",
        SimpleNamespace(connection=lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError("denied"))),
    )
    with pytest.raises(RepositoryConnectionError, match="Streamlit"):
        connection._resolve_executor(configured_settings())


def test_missing_runtime_contract():
    class SnowparkSessionException(Exception):
        pass

    class StreamlitAPIException(Exception):
        error_id = "snowflake-missing-connection-config"

    assert connection._missing_runtime(ImportError())
    assert connection._missing_runtime(SnowparkSessionException())
    assert connection._missing_runtime(StreamlitAPIException())
    assert not connection._missing_runtime(PermissionError())


class DelegatedExecutor(connection.SqlExecutor):
    runtime_name = "Fake Runtime"

    def __init__(self):
        self.calls = []

    def query(self, sql, params=None): self.calls.append(("query", sql)); return pd.DataFrame()
    def execute(self, sql, params=None): self.calls.append(("execute", sql)); return 1
    def executemany(self, sql, rows, *, batch_size=500): self.calls.append(("executemany", sql)); return 1
    def commit(self): self.calls.append(("commit", None))
    def rollback(self): self.calls.append(("rollback", None))

    @contextmanager
    def transaction(self):
        self.calls.append(("transaction", None))
        yield self


def test_lazy_executor_resolves_once_and_delegates(monkeypatch):
    delegated = DelegatedExecutor()
    resolutions = []
    monkeypatch.setattr(connection, "_resolve_executor", lambda settings: resolutions.append(settings) or delegated)
    lazy = connection.LazySqlExecutor(configured_settings())
    assert lazy.is_resolved is False
    assert lazy.runtime_name == "Not connected"
    lazy.execute("UPDATE T")
    lazy.query("SELECT 1")
    lazy.check_connection()
    with lazy.transaction() as executor:
        assert executor is delegated
    assert len(resolutions) == 1
    assert lazy.runtime_name == "Fake Runtime"
    assert [call[0] for call in delegated.calls] == ["execute", "query", "query", "transaction"]


def test_repository_mode_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("REPOSITORY_MODE", raising=False)
    from data.repositories import get_repository
    from data.repositories.mock import MockRepository

    assert isinstance(get_repository(), MockRepository)
