"""Snowflake runtime discovery and parameter-bound SQL execution.

The repository writes SQL using the connector ``%s`` placeholder. Executors
adapt it to the runtime they own; Snowpark uses qmark binding while the Python
connector keeps ``%s``. Runtime discovery is lazy so selecting Snowflake mode
does not contact a real account until a repository operation is requested.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
import os
import re
from typing import Callable, Iterable, Iterator, Sequence

import pandas as pd

from data.repositories.base import RepositoryConfigurationError, RepositoryConnectionError, RepositoryError


Params = Sequence[object] | None
ParamRows = Iterable[Sequence[object]]


@dataclass(frozen=True)
class SnowflakeSettings:
    connection_name: str | None
    account: str | None
    user: str | None
    password: str | None
    authenticator: str | None
    private_key_file: str | None
    private_key_file_pwd: str | None
    warehouse: str | None
    database: str
    role: str | None

    @classmethod
    def from_env(cls) -> "SnowflakeSettings":
        value = lambda name: os.getenv(name) or None
        return cls(
            connection_name=value("SNOWFLAKE_CONNECTION_NAME"),
            account=value("SNOWFLAKE_ACCOUNT"),
            user=value("SNOWFLAKE_USER"),
            password=value("SNOWFLAKE_PASSWORD"),
            authenticator=value("SNOWFLAKE_AUTHENTICATOR"),
            private_key_file=value("SNOWFLAKE_PRIVATE_KEY_FILE"),
            private_key_file_pwd=value("SNOWFLAKE_PRIVATE_KEY_FILE_PWD"),
            warehouse=value("SNOWFLAKE_WAREHOUSE"),
            database=value("SNOWFLAKE_DATABASE") or "EFNS_DEV",
            role=value("SNOWFLAKE_ROLE"),
        )

    def connector_kwargs(self) -> dict:
        if self.connection_name:
            return {"connection_name": self.connection_name, "autocommit": False}
        if not self.account or not self.user:
            raise RepositoryConfigurationError(
                "Snowflake is not configured. Set a connection name or provide account and user settings."
            )
        credentials = bool(self.password or self.private_key_file or self.authenticator)
        if not credentials:
            raise RepositoryConfigurationError(
                "Snowflake authentication is not configured. Use SSO, key-pair authentication, or an optional development password."
            )
        values = {
            "account": self.account,
            "user": self.user,
            "password": self.password,
            "authenticator": self.authenticator,
            "private_key_file": self.private_key_file,
            "private_key_file_pwd": self.private_key_file_pwd,
            "warehouse": self.warehouse,
            "database": self.database,
            "role": self.role,
            "autocommit": False,
        }
        return {key: value for key, value in values.items() if value is not None}

    @property
    def configured(self) -> bool:
        if self.connection_name:
            return True
        return bool(self.account and self.user and (self.password or self.private_key_file or self.authenticator))


class SqlExecutor(ABC):
    """Small execution contract shared by connector and Snowpark runtimes."""

    runtime_name = "Unknown"

    @abstractmethod
    def query(self, sql: str, params: Params = None) -> pd.DataFrame: ...

    @abstractmethod
    def execute(self, sql: str, params: Params = None) -> int: ...

    @abstractmethod
    def executemany(self, sql: str, rows: ParamRows, *, batch_size: int = 500) -> int: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def transaction(self) -> Iterator["SqlExecutor"]: ...

    def check_connection(self) -> None:
        self.query("SELECT CURRENT_VERSION() AS VERSION")


class ConnectorExecutor(SqlExecutor):
    runtime_name = "Connector"

    def __init__(self, connection_factory: Callable[[], object]):
        self._connection_factory = connection_factory
        self._connection = None

    def _connect(self):
        if self._connection is None:
            try:
                self._connection = self._connection_factory()
            except RepositoryError:
                raise
            except Exception as exc:
                raise RepositoryConnectionError(
                    "Snowflake connection failed. Check the configured authentication, network access, and account permissions."
                ) from exc
        return self._connection

    @contextmanager
    def _cursor(self):
        cursor = None
        try:
            cursor = self._connect().cursor()
            yield cursor
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError(
                "Snowflake operation failed. Check SQL compatibility and assigned privileges."
            ) from exc
        finally:
            if cursor is not None:
                cursor.close()

    def query(self, sql: str, params: Params = None) -> pd.DataFrame:
        with self._cursor() as cursor:
            cursor.execute(sql, tuple(params or ()))
            rows = cursor.fetchall()
            columns = [column[0] for column in (cursor.description or [])]
            # Some lightweight offline cursor doubles expose only fetchone.
            if not rows and not columns and hasattr(cursor, "fetchone"):
                first = cursor.fetchone()
                rows = [] if first is None else [first]
            if rows and not columns:
                columns = [f"COLUMN_{index + 1}" for index in range(len(rows[0]))]
            return pd.DataFrame.from_records(rows, columns=columns)

    def execute(self, sql: str, params: Params = None) -> int:
        with self._cursor() as cursor:
            cursor.execute(sql, tuple(params or ()))
            return int(cursor.rowcount if cursor.rowcount is not None else -1)

    def executemany(self, sql: str, rows: ParamRows, *, batch_size: int = 500) -> int:
        del batch_size
        values = list(rows)
        if not values:
            return 0
        with self._cursor() as cursor:
            cursor.executemany(sql, values)
            rowcount = cursor.rowcount
            return len(values) if rowcount is None or rowcount < 0 else int(rowcount)

    def commit(self) -> None:
        try:
            self._connect().commit()
        except Exception as exc:
            raise RepositoryError("Snowflake could not commit the transaction.") from exc

    def rollback(self) -> None:
        try:
            self._connect().rollback()
        except Exception as exc:
            raise RepositoryError("Snowflake could not roll back the transaction.") from exc

    @contextmanager
    def transaction(self) -> Iterator["ConnectorExecutor"]:
        try:
            yield self
            self.commit()
        except Exception:
            try:
                self.rollback()
            finally:
                raise


def _qmark(sql: str) -> str:
    return sql.replace("%s", "?")


def _affected_rows(rows: list[object]) -> int:
    if not rows:
        return 0
    row = rows[0]
    values = row.as_dict() if hasattr(row, "as_dict") else dict(row) if isinstance(row, dict) else {}
    total = 0
    found = False
    for key, value in values.items():
        normalized = str(key).lower().replace("_", " ")
        if "number of rows" in normalized and any(word in normalized for word in ("insert", "update", "delete", "merge")):
            total += int(value or 0)
            found = True
    return total if found else -1


class SnowparkExecutor(SqlExecutor):
    runtime_name = "Warehouse Session"
    _VALUES = re.compile(r"^(.*?\bVALUES\s*)(\(.*\))(\s*;?\s*)$", re.IGNORECASE | re.DOTALL)

    def __init__(self, session, runtime_name: str | None = None):
        self.session = session
        if runtime_name:
            self.runtime_name = runtime_name

    def _collect(self, sql: str, params: Params = None) -> list:
        try:
            return list(self.session.sql(_qmark(sql), params=list(params or ())).collect())
        except Exception as exc:
            raise RepositoryError(
                "Snowflake operation failed. Check SQL compatibility and assigned privileges."
            ) from exc

    def query(self, sql: str, params: Params = None) -> pd.DataFrame:
        try:
            statement = self.session.sql(_qmark(sql), params=list(params or ()))
            rows = list(statement.collect())
            columns = [field.name for field in statement.schema.fields]
        except Exception as exc:
            raise RepositoryError(
                "Snowflake operation failed. Check SQL compatibility and assigned privileges."
            ) from exc
        if not rows:
            return pd.DataFrame(columns=columns)
        dictionaries = [row.as_dict() if hasattr(row, "as_dict") else dict(row) for row in rows]
        return pd.DataFrame(dictionaries, columns=columns)

    def execute(self, sql: str, params: Params = None) -> int:
        return _affected_rows(self._collect(sql, params))

    def executemany(self, sql: str, rows: ParamRows, *, batch_size: int = 500) -> int:
        values = list(rows)
        if not values:
            return 0
        match = self._VALUES.match(sql.strip())
        if not match:
            raise RepositoryError(
                "Snowpark bulk writes require an INSERT statement with a VALUES clause; row-by-row fallback is disabled."
            )
        prefix, group, suffix = match.groups()
        total = 0
        for start in range(0, len(values), batch_size):
            batch = values[start : start + batch_size]
            statement = prefix + ", ".join([group] * len(batch)) + suffix
            parameters = [value for row in batch for value in row]
            affected = self.execute(statement, parameters)
            total += len(batch) if affected < 0 else affected
        return total

    def commit(self) -> None:
        self._collect("COMMIT")

    def rollback(self) -> None:
        self._collect("ROLLBACK")

    @contextmanager
    def transaction(self) -> Iterator["SnowparkExecutor"]:
        self._collect("BEGIN")
        try:
            yield self
            self.commit()
        except Exception:
            try:
                self.rollback()
            finally:
                raise


def _streamlit_runtime_active() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx(suppress_warning=True) is not None
    except (ImportError, RuntimeError):
        return False


def streamlit_connection_configured(name: str | None = None) -> bool:
    """Check for named Streamlit connection metadata without opening it."""
    if not _streamlit_runtime_active():
        return False
    try:
        import streamlit as st
        connections = st.secrets.get("connections", {})
        return (name or os.getenv("SNOWFLAKE_STREAMLIT_CONNECTION", "snowflake")) in connections
    except Exception:
        return False


def _missing_runtime(exc: Exception) -> bool:
    names = {type(exc).__name__, type(exc).__qualname__}
    missing_streamlit_config = (
        type(exc).__name__ == "StreamlitAPIException"
        and getattr(exc, "error_id", None) == "snowflake-missing-connection-config"
    )
    return missing_streamlit_config or isinstance(exc, (ImportError, ModuleNotFoundError)) or bool(
        names & {"StreamlitSecretNotFoundError", "SnowparkSessionException"}
    )


def _resolve_executor(settings: SnowflakeSettings) -> SqlExecutor:
    if _streamlit_runtime_active():
        try:
            import streamlit as st
            name = os.getenv("SNOWFLAKE_STREAMLIT_CONNECTION", "snowflake")
            return SnowparkExecutor(st.connection(name, type="snowflake").session(), "Streamlit Connection")
        except Exception as exc:
            if not _missing_runtime(exc):
                raise RepositoryConnectionError(
                    "The configured Streamlit Snowflake connection could not be opened."
                ) from exc
    try:
        from snowflake.snowpark.context import get_active_session
        return SnowparkExecutor(get_active_session(), "Warehouse Session")
    except (ImportError, ModuleNotFoundError):
        pass
    except Exception as exc:
        if not _missing_runtime(exc):
            raise RepositoryConnectionError("The active Snowflake warehouse session could not be opened.") from exc

    kwargs = settings.connector_kwargs()

    def connect():
        import snowflake.connector
        return snowflake.connector.connect(**kwargs)

    return ConnectorExecutor(connect)


class LazySqlExecutor(SqlExecutor):
    """Resolve the supported Snowflake runtime on the first SQL operation."""

    runtime_name = "Not connected"

    def __init__(self, settings: SnowflakeSettings | None = None):
        self.settings = settings or SnowflakeSettings.from_env()
        self._resolved: SqlExecutor | None = None

    @property
    def is_resolved(self) -> bool:
        return self._resolved is not None

    @property
    def resolved(self) -> SqlExecutor:
        if self._resolved is None:
            self._resolved = _resolve_executor(self.settings)
            self.runtime_name = self._resolved.runtime_name
        return self._resolved

    def query(self, sql, params=None): return self.resolved.query(sql, params)
    def execute(self, sql, params=None): return self.resolved.execute(sql, params)
    def executemany(self, sql, rows, *, batch_size=500): return self.resolved.executemany(sql, rows, batch_size=batch_size)
    def commit(self): self.resolved.commit()
    def rollback(self): self.resolved.rollback()

    @contextmanager
    def transaction(self):
        with self.resolved.transaction() as executor:
            yield executor


def create_executor(settings: SnowflakeSettings | None = None) -> LazySqlExecutor:
    return LazySqlExecutor(settings)
