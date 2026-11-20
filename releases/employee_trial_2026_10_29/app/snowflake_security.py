"""Snowflake-backed EFNS application users, roles, and audit events."""

from __future__ import annotations

import json
from contextlib import contextmanager
import os
import re
from uuid import uuid4

import pandas as pd

from app.security import (
    AuditEvent,
    AuthenticationError,
    AuthStore,
    AuthorizationError,
    Permission,
    Role,
    User,
    UserValidationError,
    require_permission,
    validate_internal_email,
)
from data.connection import SqlExecutor, create_executor
from app.snowflake_identity import normalize_snowflake_username, MAIN_SNOWFLAKE_ADMIN_USERNAME, MAIN_ADMIN_USER_ID, main_admin_user
from data.repositories.base import RepositoryError


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def _identifier(value: str, label: str) -> str:
    if not _IDENTIFIER.fullmatch(value or ""):
        raise RepositoryError(f"Invalid Snowflake {label} identifier in configuration.")
    return value


def _timestamp(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    converted = pd.Timestamp(value)
    if converted.tzinfo is None:
        converted = converted.tz_localize("UTC")
    else:
        converted = converted.tz_convert("UTC")
    return converted.isoformat(timespec="seconds")


class SnowflakeAuthStore(AuthStore):
    """Application authorization for identities supplied by ``st.user``."""

    authentication_mode = "Snowflake viewer"
    supports_passwords = False

    def __init__(self, executor: SqlExecutor | None = None):
        self.executor = executor or create_executor()
        database = _identifier(os.getenv("SNOWFLAKE_DATABASE", "EFNS_DEV"), "database")
        security_schema = _identifier(os.getenv("SNOWFLAKE_SCHEMA_SECURITY", "SECURITY"), "SECURITY schema")
        app_schema = _identifier(os.getenv("SNOWFLAKE_SCHEMA_APP", "APP"), "APP schema")
        self.user_table = f"{database}.{security_schema}.APP_USER"
        self.audit_table = f"{database}.{app_schema}.AUDIT_EVENT"
        self.username_mapping_available = None

    @staticmethod
    def _user_from_row(row: dict | None) -> User | None:
        if row is None:
            return None
        values = {str(key).upper(): value for key, value in row.items()}
        return User(
            user_id=str(values["USER_ID"]),
            email=str(values["EMAIL"]).casefold(),
            display_name=str(values["DISPLAY_NAME"]),
            role=Role(str(values["ROLE"])),
            active=str(values.get("ACTIVE",False)).strip().casefold() in {"true","1"},
            must_change_password=False,
            created_at=_timestamp(values.get("CREATED_AT")) or "",
            updated_at=_timestamp(values.get("UPDATED_AT")) or "",
            last_login_at=_timestamp(values.get("LAST_LOGIN_AT")),
            snowflake_username=(str(values["SNOWFLAKE_USERNAME"]).strip().upper() if pd.notna(values.get("SNOWFLAKE_USERNAME")) else None),
        )

    def _one(self, column: str, value: str, executor: SqlExecutor | None = None) -> User | None:
        query_executor = executor or self.executor
        frame = query_executor.query(
            f"SELECT * "
            f"FROM {self.user_table} WHERE {column} = %s LIMIT 1",
            (value,),
        )
        return None if frame.empty else self._user_from_row(frame.iloc[0].to_dict())

    def get_user(self, user_id: str) -> User | None:
        if user_id==MAIN_ADMIN_USER_ID:
            return main_admin_user()
        return self._one("USER_ID", str(user_id))

    def resolve_identity(self, username: str) -> User | None:
        try:
            normalized = normalize_snowflake_username(username,allow_main=True)
        except UserValidationError:
            return None
        if not normalized:return None
        if normalized==MAIN_SNOWFLAKE_ADMIN_USERNAME:
            return main_admin_user() if username==MAIN_SNOWFLAKE_ADMIN_USERNAME else None
        try:
            frame=self.executor.query(f"SELECT * FROM {self.user_table} WHERE UPPER(TRIM(SNOWFLAKE_USERNAME)) = %s LIMIT 2",(normalized,))
        except Exception:
            self.username_mapping_available=False
            return None
        self.username_mapping_available='SNOWFLAKE_USERNAME' in frame.columns
        if not self.username_mapping_available or len(frame)!=1:return None
        try:
            user=self._user_from_row(frame.iloc[0].to_dict())
        except (ValueError,KeyError,TypeError):
            return None
        return user if user and user.active else None

    @contextmanager
    def _username_transaction(self):
        # Reuse the established global app write boundary; no new lock/session.
        from data.repositories.snowflake import SnowflakeRepository
        with SnowflakeRepository(self.executor)._continuity_transaction() as tx:
            yield tx

    def _check_username(self, tx, username, user_id):
        try:
            frame=tx.query(f"SELECT USER_ID FROM {self.user_table} WHERE UPPER(TRIM(SNOWFLAKE_USERNAME)) = %s AND USER_ID <> %s",(username,user_id))
        except Exception as exc:
            self.username_mapping_available=False
            raise UserValidationError('Snowflake username mapping requires the reviewed schema update and existing app-owner access.') from exc
        if not frame.empty:
            raise UserValidationError('Snowflake username is already assigned to another user.')
        self.username_mapping_available=True

    def login(self, email: str, password: str) -> tuple[User, str]:
        del email, password
        raise AuthenticationError("Snowflake mode uses the authenticated Snowflake viewer.")

    def resolve_session(self, token: str | None) -> User | None:
        del token
        return None

    def logout(self, token: str | None) -> None:
        del token

    def list_users(self, actor: User) -> list[User]:
        require_permission(actor, Permission.MANAGE_USERS)
        frame = self.executor.query(
            f"SELECT * "
            f"FROM {self.user_table} ORDER BY EMAIL"
        )
        self.username_mapping_available="SNOWFLAKE_USERNAME" in frame.columns
        return [self._user_from_row(row) for row in frame.to_dict("records")]

    def create_user(self, actor: User, email: str, display_name: str, role: Role, *, snowflake_username=...) -> tuple[User, str | None]:
        require_permission(actor, Permission.MANAGE_USERS)
        normalized = validate_internal_email(email)
        name = str(display_name or "").strip()
        if not name:
            raise UserValidationError("Display name is required.")
        if self._one("LOWER(EMAIL)", normalized):
            raise UserValidationError("A user with this email address already exists.")
        user_id = str(uuid4())
        assigned_role = Role(role)
        mapping=None if snowflake_username is ... else normalize_snowflake_username(snowflake_username)
        transaction=self.executor.transaction if snowflake_username is ... else self._username_transaction
        with transaction() as tx:
            if snowflake_username is not ...:self._check_username(tx,mapping,user_id)
            affected = tx.execute(
                f"INSERT INTO {self.user_table} "
                f"(USER_ID, EMAIL, DISPLAY_NAME, ROLE, {'SNOWFLAKE_USERNAME, ' if snowflake_username is not ... else ''}ACTIVE, CREATED_AT, UPDATED_AT) "
                f"VALUES (%s, %s, %s, %s, {'%s, ' if snowflake_username is not ... else ''}TRUE, "
                "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP()), CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP()))",
                (user_id, normalized, name, assigned_role.value, *([mapping] if snowflake_username is not ... else [])),
            )
            if affected == 0:
                raise RepositoryError("Snowflake did not create the application user.")
            self._insert_audit(
                tx, actor, "CREATE_USER", "USER", user_id,
                {"email": normalized, "role": assigned_role.value},
            )
        created = self.get_user(user_id)
        if created is None:
            raise RepositoryError("Snowflake did not return the newly created application user.")
        return created, None

    def _ensure_another_active_admin(self, excluded_user_id: str) -> None:
        frame = self.executor.query(
            f"SELECT COUNT(*) AS ADMIN_COUNT FROM {self.user_table} "
            "WHERE ROLE = %s AND ACTIVE = TRUE AND USER_ID <> %s",
            (Role.ADMIN.value, excluded_user_id),
        )
        if frame.empty or int(frame.iloc[0].get("ADMIN_COUNT", 0)) < 1:
            raise UserValidationError("At least one active Admin account must remain.")

    def update_user(self, actor: User, user_id: str, *, role: Role, active: bool, snowflake_username=...) -> User:
        require_permission(actor, Permission.MANAGE_USERS)
        if user_id==MAIN_ADMIN_USER_ID:
            raise UserValidationError('The main Snowflake Admin is an explicit runtime identity and cannot be modified in User Management.')
        current = self.get_user(user_id)
        if current is None:
            raise UserValidationError("The selected user no longer exists.")
        assigned_role = Role(role)
        if actor.user_id == user_id and not active:
            raise UserValidationError("You cannot deactivate your own account.")
        if current.role == Role.ADMIN and current.active and (assigned_role != Role.ADMIN or not active):
            self._ensure_another_active_admin(user_id)
        mapping=current.snowflake_username if snowflake_username is ... else normalize_snowflake_username(snowflake_username)
        transaction=self.executor.transaction if snowflake_username is ... else self._username_transaction
        with transaction() as tx:
            if snowflake_username is not ...:self._check_username(tx,mapping,user_id)
            affected = tx.execute(
                f"UPDATE {self.user_table} SET ROLE = %s, ACTIVE = %s, {'SNOWFLAKE_USERNAME = %s, ' if snowflake_username is not ... else ''}"
                "UPDATED_AT = CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP()) "
                "WHERE USER_ID = %s",
                (assigned_role.value, bool(active), *([mapping] if snowflake_username is not ... else []), user_id),
            )
            if affected == 0:
                raise RepositoryError("Snowflake did not update the application user.")
            self._insert_audit(
                tx, actor, "UPDATE_USER", "USER", user_id,
                {"email": current.email, "role": assigned_role.value, "active": bool(active)},
            )
        updated = self.get_user(user_id)
        if updated is None:
            raise RepositoryError("Snowflake did not return the updated application user.")
        return updated

    def delete_user(self, actor: User, user_id: str) -> None:
        require_permission(actor, Permission.MANAGE_USERS)
        if user_id==MAIN_ADMIN_USER_ID:
            raise UserValidationError('The main Snowflake Admin is an explicit runtime identity and cannot be modified in User Management.')
        current = self.get_user(user_id)
        if current is None:
            raise UserValidationError("The selected user no longer exists.")
        if actor.user_id == user_id:
            raise UserValidationError("You cannot delete your own account.")
        if current.role == Role.ADMIN and current.active:
            self._ensure_another_active_admin(user_id)
        with self.executor.transaction() as tx:
            self._insert_audit(tx, actor, "DELETE_USER", "USER", user_id, {"email": current.email})
            affected = tx.execute(f"DELETE FROM {self.user_table} WHERE USER_ID = %s", (user_id,))
            if affected == 0:
                raise RepositoryError("Snowflake did not delete the application user.")
            if affected < 0 and self._one("USER_ID", user_id, tx) is not None:
                raise RepositoryError("Snowflake could not confirm deletion of the application user.")

    def reset_temporary_password(self, actor: User, user_id: str) -> str:
        require_permission(actor, Permission.MANAGE_USERS)
        del user_id
        raise UserValidationError("Passwords are managed by Snowflake identity in this runtime.")

    def change_own_password(self, user: User, new_password: str) -> None:
        del user, new_password
        raise UserValidationError("Passwords are managed by Snowflake identity in this runtime.")

    def record_action(
        self,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        if not actor.active:
            raise AuthorizationError("This account is inactive.")
        with self.executor.transaction() as tx:
            self._insert_audit(tx, actor, action, entity_type, entity_id, details)

    def _insert_audit(
        self,
        executor: SqlExecutor,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        audit_id = str(uuid4())
        # Always bind valid JSON text. An untyped NULL passed to PARSE_JSON can
        # fail Snowpark bind inference after the business write has succeeded.
        details_json = json.dumps(details or {}, sort_keys=True)
        affected = executor.execute(
            f"INSERT INTO {self.audit_table} "
            "(AUDIT_ID, ACTOR_USER_ID, ACTOR_EMAIL, ACTION, ENTITY_TYPE, ENTITY_ID, DETAILS, OCCURRED_AT) "
            "SELECT %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), "
            "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())",
            (
                audit_id, actor.user_id, actor.email, str(action), str(entity_type),
                entity_id, details_json,
            ),
        )
        if affected == 0:
            raise RepositoryError("Snowflake did not append the audit event.")
        if affected < 0:
            confirmation = executor.query(
                f"SELECT AUDIT_ID FROM {self.audit_table} WHERE AUDIT_ID = %s LIMIT 1",
                (audit_id,),
            )
            if confirmation.empty:
                raise RepositoryError("Snowflake could not confirm the audit event.")

    def list_audit(self, actor: User, limit: int = 1000) -> list[AuditEvent]:
        require_permission(actor, Permission.VIEW_AUDIT)
        safe_limit = min(max(int(limit), 1), 5000)
        frame = self.executor.query(
            f"SELECT AUDIT_ID, ACTOR_EMAIL, ACTION, ENTITY_TYPE, ENTITY_ID, DETAILS, OCCURRED_AT "
            f"FROM {self.audit_table} ORDER BY OCCURRED_AT DESC, AUDIT_ID DESC LIMIT %s",
            (safe_limit,),
        )
        events = []
        for row in frame.to_dict("records"):
            values = {str(key).upper(): value for key, value in row.items()}
            details = values.get("DETAILS")
            if isinstance(details, (dict, list)):
                details = json.dumps(details, sort_keys=True)
            events.append(
                AuditEvent(
                    audit_id=str(values["AUDIT_ID"]),
                    actor_email=str(values["ACTOR_EMAIL"]),
                    action=str(values["ACTION"]),
                    entity_type=str(values["ENTITY_TYPE"]),
                    entity_id=None if pd.isna(values.get("ENTITY_ID")) else str(values.get("ENTITY_ID")),
                    details=None if details is None or pd.isna(details) else str(details),
                    occurred_at=_timestamp(values.get("OCCURRED_AT")) or "",
                )
            )
        return events
