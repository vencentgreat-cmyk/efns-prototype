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

from data.repositories.base import (
    RepositoryConfigurationError,
    RepositoryConnectionError,
    RepositoryError,
    RepositoryOperationError,
)


Params = Sequence[object] | None
ParamRows = Iterable[Sequence[object]]


_SQL_OPERATION = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|MERGE|BEGIN|COMMIT|ROLLBACK)\b", re.IGNORECASE)
_SQL_ENTITY = re.compile(
    r"\b(?:FROM|INTO|UPDATE|MERGE\s+INTO)\s+([A-Za-z_][A-Za-z0-9_$.]*)",
    re.IGNORECASE,
)
_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _safe_reference(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if _SAFE_REFERENCE.fullmatch(text) else None


def _operation_context(sql: str) -> tuple[str, str]:
    operation_match = _SQL_OPERATION.search(sql or "")
    entity_match = _SQL_ENTITY.search(sql or "")
    operation = operation_match.group(1).upper() if operation_match else "SQL"
    entity = entity_match.group(1).split(".")[-1].upper() if entity_match else "TRANSACTION"
    return operation, entity


def _operation_error(exc: Exception, sql: str, cursor=None) -> RepositoryOperationError:
    operation, entity = _operation_context(sql)
    query_id = next(
        (
            _safe_reference(getattr(source, attribute, None))
            for source in (exc, cursor)
            for attribute in ("query_id", "sfqid")
            if _safe_reference(getattr(source, attribute, None))
        ),
        None,
    )
    error_code = next(
        (
            _safe_reference(getattr(exc, attribute, None))
            for attribute in ("errno", "sql_error_code")
            if _safe_reference(getattr(exc, attribute, None))
        ),
        None,
    )
    sql_state = next(
        (
            _safe_reference(getattr(exc, attribute, None))
            for attribute in ("sqlstate", "sql_state")
            if _safe_reference(getattr(exc, attribute, None))
        ),
        None,
    )
    return RepositoryOperationError(
        operation,
        entity,
        query_id=query_id,
        error_code=error_code,
        sql_state=sql_state,
        error_type=type(exc).__name__,
    )


def _rewrite_placeholders(sql: str, source: str, target: str | None = None) -> tuple[str, int]:
    """Rewrite/count bind markers outside quoted SQL literals.

    This intentionally small scanner understands Snowflake's single-quoted
    string literals and double-quoted identifiers, including doubled quote
    escapes. Bind-looking text inside either form is left untouched.
    """
    output: list[str] = []
    count = 0
    index = 0
    quote: str | None = None
    while index < len(sql):
        char = sql[index]
        if quote:
            output.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    output.append(sql[index + 1])
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            output.append(char)
            index += 1
            continue
        if sql.startswith(source, index):
            output.append(source if target is None else target)
            count += 1
            index += len(source)
            continue
        output.append(char)
        index += 1
    return "".join(output), count


def _validated_rows(sql: str, rows: ParamRows, marker: str) -> list[tuple[object, ...]]:
    """Materialize a row iterable once and validate its bind shape."""
    try:
        values = [tuple(row) for row in rows]
    except TypeError as exc:
        raise RepositoryError("Bulk write rows must each be a sequence of bound values.") from exc
    if not values:
        return []
    _, placeholder_count = _rewrite_placeholders(sql, marker)
    row_length = len(values[0])
    if any(len(row) != row_length for row in values):
        raise RepositoryError("Bulk write rows must all contain the same number of values.")
    if row_length != placeholder_count:
        raise RepositoryError(
            f"Bulk write row length ({row_length}) does not match the SQL bind count ({placeholder_count})."
        )
    return values


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
            raise RepositoryConnectionError(
                "Snowflake could not open a SQL cursor for this operation."
            ) from exc
        finally:
            if cursor is not None:
                cursor.close()

    def query(self, sql: str, params: Params = None) -> pd.DataFrame:
        with self._cursor() as cursor:
            try:
                cursor.execute(sql, tuple(params or ()))
            except RepositoryError:
                raise
            except Exception as exc:
                raise _operation_error(exc, sql, cursor) from exc
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
            try:
                cursor.execute(sql, tuple(params or ()))
            except RepositoryError:
                raise
            except Exception as exc:
                raise _operation_error(exc, sql, cursor) from exc
            return int(cursor.rowcount if cursor.rowcount is not None else -1)

    def executemany(self, sql: str, rows: ParamRows, *, batch_size: int = 500) -> int:
        del batch_size
        values = _validated_rows(sql, rows, "%s")
        if not values:
            return 0
        with self._cursor() as cursor:
            try:
                cursor.executemany(sql, values)
            except RepositoryError:
                raise
            except Exception as exc:
                raise _operation_error(exc, sql, cursor) from exc
            rowcount = cursor.rowcount
            return len(values) if rowcount is None or rowcount < 0 else int(rowcount)

    def commit(self) -> None:
        try:
            self._connect().commit()
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError("Snowflake could not commit the transaction.") from exc

    def rollback(self) -> None:
        try:
            self._connect().rollback()
        except RepositoryError:
            raise
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
    return _rewrite_placeholders(sql, "%s", "?")[0]


def _affected_rows(rows: list[object]) -> int:
    if not rows:
        return 0
    row = rows[0]
    values = row.as_dict() if hasattr(row, "as_dict") else dict(row) if isinstance(row, dict) else {}
    total = 0
    found = False
    for key, value in values.items():
        normalized = str(key).lower().replace("_", " ").replace('"', "")
        row_count_label = "number of rows" in normalized or "rows affected" in normalized
        if row_count_label and any(word in normalized for word in ("insert", "update", "delete", "merge", "affect")):
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
        except RepositoryError:
            raise
        except Exception as exc:
            raise _operation_error(exc, sql) from exc

    def query(self, sql: str, params: Params = None) -> pd.DataFrame:
        try:
            statement = self.session.sql(_qmark(sql), params=list(params or ()))
            rows = list(statement.collect())
            columns = [field.name for field in statement.schema.fields]
        except RepositoryError:
            raise
        except Exception as exc:
            raise _operation_error(exc, sql) from exc
        if not rows:
            return pd.DataFrame(columns=columns)
        dictionaries = [row.as_dict() if hasattr(row, "as_dict") else dict(row) for row in rows]
        return pd.DataFrame(dictionaries, columns=columns)

    def execute(self, sql: str, params: Params = None) -> int:
        return _affected_rows(self._collect(sql, params))

    def executemany(self, sql: str, rows: ParamRows, *, batch_size: int = 500) -> int:
        if batch_size < 1:
            raise RepositoryError("Snowpark bulk-write batch size must be at least one.")
        qmark_sql = _qmark(sql)
        values = _validated_rows(qmark_sql, rows, "?")
        if not values:
            return 0
        match = self._VALUES.match(qmark_sql.strip())
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
