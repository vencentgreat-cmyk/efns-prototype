"""Prototype authentication, authorization, sessions, and audit persistence.

The Streamlit layer depends on the ``AuthStore`` contract so this local SQLite
implementation can be replaced by an organizational identity provider later.
No Snowflake or repository APIs are used here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import hashlib
import hmac
import json
from pathlib import Path
import re
import secrets
try:
    import sqlite3
except ImportError:  # Optional in Snowflake mode; required only by local auth.
    sqlite3 = None
from typing import Iterable
from uuid import uuid4


ALLOWED_EMAIL_DOMAIN = "nsegg.ca"
PASSWORD_ITERATIONS = 600_000
SESSION_HOURS = 8


class Role(StrEnum):
    ADMIN = "Admin"
    DATA_EDITOR = "Data Editor"
    REPORTING_VIEWER = "Reporting Viewer"
    DEVELOPER = "Developer"


class Permission(StrEnum):
    VIEW_DATA = "view_data"
    VIEW_REPORTS = "view_reports"
    IMPORT_DATA = "import_data"
    CREATE_DATA = "create_data"
    UPDATE_DATA = "update_data"
    DELETE_DATA = "delete_data"
    USE_PROFILER = "use_profiler"
    VIEW_DIAGNOSTICS = "view_diagnostics"
    VIEW_AUDIT = "view_audit"
    MANAGE_USERS = "manage_users"
    USE_DEVELOPER_TOOLS = "use_developer_tools"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.DATA_EDITOR: frozenset(
        {
            Permission.VIEW_DATA,
            Permission.VIEW_REPORTS,
            Permission.IMPORT_DATA,
            Permission.CREATE_DATA,
            Permission.UPDATE_DATA,
        }
    ),
    Role.REPORTING_VIEWER: frozenset(
        {Permission.VIEW_DATA, Permission.VIEW_REPORTS}
    ),
    Role.DEVELOPER: frozenset(
        {
            Permission.VIEW_DATA,
            Permission.VIEW_REPORTS,
            Permission.USE_PROFILER,
            Permission.VIEW_DIAGNOSTICS,
            Permission.VIEW_AUDIT,
            Permission.USE_DEVELOPER_TOOLS,
        }
    ),
}


class AuthenticationError(Exception):
    """Raised for a failed prototype login without revealing account state."""


class AuthorizationError(Exception):
    """Raised when an authenticated user lacks an application permission."""


class UserValidationError(Exception):
    """Raised for a safe, user-correctable account-management error."""


@dataclass(frozen=True)
class User:
    user_id: str
    email: str
    display_name: str
    role: Role
    active: bool
    must_change_password: bool
    created_at: str
    updated_at: str
    last_login_at: str | None


@dataclass(frozen=True)
class AuditEvent:
    audit_id: str
    actor_email: str
    action: str
    entity_type: str
    entity_id: str | None
    details: str | None
    occurred_at: str


@dataclass(frozen=True)
class UserSeed:
    email: str
    display_name: str
    role: Role
    password_hash: str


# The corresponding one-time passwords are intentionally not tracked. They are
# supplied to the prototype owner out-of-band and must be changed after login.
DEFAULT_USER_SEEDS = (
    UserSeed(
        "prototype.admin@nsegg.ca",
        "Prototype Admin",
        Role.ADMIN,
        "pbkdf2_sha256$600000$PZL-oxlmRlsGR43euOUcQA$0B4O5I0EzaItEEN3kJ09B1AMdcsD2HenAETUq2-zhdk",
    ),
    UserSeed(
        "prototype.editor@nsegg.ca",
        "Prototype Data Editor",
        Role.DATA_EDITOR,
        "pbkdf2_sha256$600000$nOn__1B_GIUwOQ2nrpUiFA$ltou_ZmLKonRCvJKCeiT49zuBKQp1XSQelwthqJwZwU",
    ),
    UserSeed(
        "prototype.reporter@nsegg.ca",
        "Prototype Reporting Viewer",
        Role.REPORTING_VIEWER,
        "pbkdf2_sha256$600000$J3OAQIpb2XiOtbls5YaAFA$mgHaLM4bYc6wnF_VqQ1tjNXaS7LV-xmrXZ7xK2ErQCs",
    ),
    UserSeed(
        "prototype.developer@nsegg.ca",
        "Prototype Developer",
        Role.DEVELOPER,
        "pbkdf2_sha256$600000$Mul9RG44upQBsDnZ1i26dw$ndn5ITp1zw55XoXJvweg_PL4eVMkThQl3-9YbMkP0HU",
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_email(email: str) -> str:
    return str(email or "").strip().casefold()


def validate_internal_email(email: str) -> str:
    normalized = normalize_email(email)
    if not re.fullmatch(r"[^@\s]+@nsegg\.ca", normalized):
        raise UserValidationError("Only @nsegg.ca email addresses are allowed.")
    return normalized


def validate_password(password: str) -> None:
    value = str(password or "")
    checks = (
        len(value) >= 14,
        any(char.islower() for char in value),
        any(char.isupper() for char in value),
        any(char.isdigit() for char in value),
        any(not char.isalnum() for char in value),
    )
    if not all(checks):
        raise UserValidationError(
            "Passwords must be at least 14 characters and include upper-case, lower-case, numeric, and special characters."
        )


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    validate_password(password)
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${encode(salt)}${encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            decode(salt_text),
            int(iterations),
        )
        return hmac.compare_digest(actual, decode(digest_text))
    except (TypeError, ValueError):
        return False


def generate_temporary_password() -> str:
    characters = [
        secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        secrets.choice("abcdefghijklmnopqrstuvwxyz"),
        secrets.choice("0123456789"),
        secrets.choice("!@#$%^&*"),
        *[secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") for _ in range(16)],
    ]
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


def has_permission(user: User, permission: Permission) -> bool:
    return bool(user.active and permission in ROLE_PERMISSIONS[user.role])


def require_permission(user: User, permission: Permission) -> None:
    if not has_permission(user, permission):
        raise AuthorizationError("You do not have permission to perform this action.")


class AuthStore(ABC):
    """Replaceable application identity and audit contract."""

    authentication_mode = "Local password"
    supports_passwords = True

    def resolve_identity(self, email: str) -> User | None:
        """Resolve a trusted runtime identity when the backend supports one."""
        del email
        return None

    @abstractmethod
    def login(self, email: str, password: str) -> tuple[User, str]: ...

    @abstractmethod
    def resolve_session(self, token: str | None) -> User | None: ...

    @abstractmethod
    def logout(self, token: str | None) -> None: ...

    @abstractmethod
    def list_users(self, actor: User) -> list[User]: ...

    @abstractmethod
    def create_user(self, actor: User, email: str, display_name: str, role: Role) -> tuple[User, str | None]: ...

    @abstractmethod
    def update_user(self, actor: User, user_id: str, *, role: Role, active: bool) -> User: ...

    @abstractmethod
    def delete_user(self, actor: User, user_id: str) -> None: ...

    @abstractmethod
    def reset_temporary_password(self, actor: User, user_id: str) -> str: ...

    @abstractmethod
    def change_own_password(self, user: User, new_password: str) -> None: ...

    @abstractmethod
    def list_audit(self, actor: User, limit: int = 1000) -> list[AuditEvent]: ...

    @abstractmethod
    def record_action(
        self,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: dict | None = None,
    ) -> None: ...


class SQLiteAuthStore(AuthStore):
    """Local prototype backend stored outside tracked project files."""

    def __init__(self, database_path: str | Path, seeds: Iterable[UserSeed] = DEFAULT_USER_SEEDS):
        if sqlite3 is None:
            raise RuntimeError("Local authentication requires Python SQLite support.")
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._seeds = tuple(seeds)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as database:
            database.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_user (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    must_change_password INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT
                );
                CREATE TABLE IF NOT EXISTS app_session (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES app_user(user_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT
                );
                CREATE TABLE IF NOT EXISTS audit_event (
                    audit_id TEXT PRIMARY KEY,
                    actor_user_id TEXT,
                    actor_email TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    details TEXT,
                    occurred_at TEXT NOT NULL
                );
                """
            )
            now = utc_now()
            for seed in self._seeds:
                email = validate_internal_email(seed.email)
                database.execute(
                    """
                    INSERT OR IGNORE INTO app_user
                    (user_id, email, display_name, role, password_hash, active,
                     must_change_password, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
                    """,
                    (
                        str(uuid4()), email, seed.display_name, seed.role.value,
                        seed.password_hash, now, now,
                    ),
                )

    @staticmethod
    def _user(row: sqlite3.Row | None) -> User | None:
        if row is None:
            return None
        return User(
            user_id=row["user_id"],
            email=row["email"],
            display_name=row["display_name"],
            role=Role(row["role"]),
            active=bool(row["active"]),
            must_change_password=bool(row["must_change_password"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_login_at=row["last_login_at"],
        )

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def get_user(self, user_id: str) -> User | None:
        with self._connect() as database:
            return self._user(database.execute("SELECT * FROM app_user WHERE user_id = ?", (user_id,)).fetchone())

    def resolve_identity(self, email: str) -> User | None:
        try:
            normalized = validate_internal_email(email)
        except UserValidationError:
            return None
        with self._connect() as database:
            row = database.execute(
                "SELECT * FROM app_user WHERE email = ? AND active = 1", (normalized,)
            ).fetchone()
        return self._user(row)

    def login(self, email: str, password: str) -> tuple[User, str]:
        try:
            normalized = validate_internal_email(email)
        except UserValidationError as exc:
            raise AuthenticationError("Invalid email or password.") from exc
        with self._connect() as database:
            row = database.execute("SELECT * FROM app_user WHERE email = ?", (normalized,)).fetchone()
            if row is None or not bool(row["active"]) or not verify_password(password, row["password_hash"]):
                raise AuthenticationError("Invalid email or password.")
            now = utc_now()
            token = secrets.token_urlsafe(32)
            expires = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
            database.execute("UPDATE app_user SET last_login_at = ?, updated_at = ? WHERE user_id = ?", (now, now, row["user_id"]))
            database.execute(
                "INSERT INTO app_session (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (self._token_hash(token), row["user_id"], now, expires),
            )
            updated = database.execute("SELECT * FROM app_user WHERE user_id = ?", (row["user_id"],)).fetchone()
            user = self._user(updated)
            self._insert_audit(database, user, "LOGIN", "SESSION")
            return user, token

    def resolve_session(self, token: str | None) -> User | None:
        if not token:
            return None
        now = utc_now()
        with self._connect() as database:
            row = database.execute(
                """
                SELECT u.* FROM app_session s
                JOIN app_user u ON u.user_id = s.user_id
                WHERE s.token_hash = ? AND s.revoked_at IS NULL
                  AND s.expires_at > ? AND u.active = 1
                """,
                (self._token_hash(token), now),
            ).fetchone()
            return self._user(row)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self._connect() as database:
            row = database.execute(
                """SELECT u.* FROM app_session s JOIN app_user u ON u.user_id = s.user_id
                   WHERE s.token_hash = ? AND s.revoked_at IS NULL""",
                (self._token_hash(token),),
            ).fetchone()
            database.execute(
                "UPDATE app_session SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (utc_now(), self._token_hash(token)),
            )
            user = self._user(row)
            if user:
                self._insert_audit(database, user, "LOGOUT", "SESSION")

    def list_users(self, actor: User) -> list[User]:
        require_permission(actor, Permission.MANAGE_USERS)
        with self._connect() as database:
            return [self._user(row) for row in database.execute("SELECT * FROM app_user ORDER BY email").fetchall()]

    def create_user(self, actor: User, email: str, display_name: str, role: Role) -> tuple[User, str]:
        require_permission(actor, Permission.MANAGE_USERS)
        normalized = validate_internal_email(email)
        name = str(display_name or "").strip()
        if not name:
            raise UserValidationError("Display name is required.")
        role = Role(role)
        temporary_password = generate_temporary_password()
        now = utc_now()
        user_id = str(uuid4())
        try:
            with self._connect() as database:
                database.execute(
                    """INSERT INTO app_user
                       (user_id, email, display_name, role, password_hash, active,
                        must_change_password, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)""",
                    (user_id, normalized, name, role.value, hash_password(temporary_password), now, now),
                )
                user = self._user(database.execute("SELECT * FROM app_user WHERE user_id = ?", (user_id,)).fetchone())
                self._insert_audit(database, actor, "CREATE_USER", "USER", user_id, {"email": normalized, "role": role.value})
        except sqlite3.IntegrityError as exc:
            raise UserValidationError("A user with this email address already exists.") from exc
        return user, temporary_password

    def update_user(self, actor: User, user_id: str, *, role: Role, active: bool) -> User:
        require_permission(actor, Permission.MANAGE_USERS)
        current = self.get_user(user_id)
        if current is None:
            raise UserValidationError("The selected user no longer exists.")
        role = Role(role)
        if actor.user_id == user_id and not active:
            raise UserValidationError("You cannot deactivate your own account.")
        if current.role == Role.ADMIN and current.active and (role != Role.ADMIN or not active):
            self._ensure_another_active_admin(user_id)
        now = utc_now()
        with self._connect() as database:
            database.execute(
                "UPDATE app_user SET role = ?, active = ?, updated_at = ? WHERE user_id = ?",
                (role.value, int(active), now, user_id),
            )
            updated = self._user(database.execute("SELECT * FROM app_user WHERE user_id = ?", (user_id,)).fetchone())
            self._insert_audit(
                database, actor, "UPDATE_USER", "USER", user_id,
                {"email": updated.email, "role": role.value, "active": bool(active)},
            )
        return updated

    def delete_user(self, actor: User, user_id: str) -> None:
        require_permission(actor, Permission.MANAGE_USERS)
        current = self.get_user(user_id)
        if current is None:
            raise UserValidationError("The selected user no longer exists.")
        if actor.user_id == user_id:
            raise UserValidationError("You cannot delete your own account.")
        if current.role == Role.ADMIN and current.active:
            self._ensure_another_active_admin(user_id)
        with self._connect() as database:
            self._insert_audit(database, actor, "DELETE_USER", "USER", user_id, {"email": current.email})
            database.execute("DELETE FROM app_user WHERE user_id = ?", (user_id,))

    def reset_temporary_password(self, actor: User, user_id: str) -> str:
        require_permission(actor, Permission.MANAGE_USERS)
        target = self.get_user(user_id)
        if target is None:
            raise UserValidationError("The selected user no longer exists.")
        temporary_password = generate_temporary_password()
        with self._connect() as database:
            database.execute(
                "UPDATE app_user SET password_hash = ?, must_change_password = 1, updated_at = ? WHERE user_id = ?",
                (hash_password(temporary_password), utc_now(), user_id),
            )
            database.execute("UPDATE app_session SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (utc_now(), user_id))
            self._insert_audit(database, actor, "RESET_PASSWORD", "USER", user_id, {"email": target.email})
        return temporary_password

    def change_own_password(self, user: User, new_password: str) -> None:
        current = self.get_user(user.user_id)
        if current is None or not current.active or current.email != user.email:
            raise AuthorizationError("This account is inactive.")
        encoded = hash_password(new_password)
        with self._connect() as database:
            database.execute(
                "UPDATE app_user SET password_hash = ?, must_change_password = 0, updated_at = ? WHERE user_id = ?",
                (encoded, utc_now(), current.user_id),
            )
            self._insert_audit(database, current, "CHANGE_PASSWORD", "USER", current.user_id)

    def _ensure_another_active_admin(self, excluded_user_id: str) -> None:
        with self._connect() as database:
            count = database.execute(
                "SELECT COUNT(*) FROM app_user WHERE role = ? AND active = 1 AND user_id <> ?",
                (Role.ADMIN.value, excluded_user_id),
            ).fetchone()[0]
        if not count:
            raise UserValidationError("At least one active Admin account must remain.")

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
        with self._connect() as database:
            self._insert_audit(database, actor, action, entity_type, entity_id, details)

    def _insert_audit(
        self,
        database,
        actor: User,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        safe_details = json.dumps(details, sort_keys=True) if details else None
        database.execute(
            """INSERT INTO audit_event
               (audit_id, actor_user_id, actor_email, action, entity_type, entity_id, details, occurred_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid4()), actor.user_id, actor.email, str(action), str(entity_type), entity_id, safe_details, utc_now()),
        )

    def list_audit(self, actor: User, limit: int = 1000) -> list[AuditEvent]:
        require_permission(actor, Permission.VIEW_AUDIT)
        safe_limit = min(max(int(limit), 1), 5000)
        with self._connect() as database:
            rows = database.execute(
                "SELECT * FROM audit_event ORDER BY occurred_at DESC, audit_id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [
            AuditEvent(
                audit_id=row["audit_id"], actor_email=row["actor_email"],
                action=row["action"], entity_type=row["entity_type"],
                entity_id=row["entity_id"], details=row["details"],
                occurred_at=row["occurred_at"],
            )
            for row in rows
        ]
