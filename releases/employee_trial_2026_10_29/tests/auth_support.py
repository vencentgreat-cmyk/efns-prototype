"""Helpers for authenticated, isolated Streamlit AppTests."""

from pathlib import Path
from uuid import uuid4

from streamlit.testing.v1 import AppTest

from app.auth import SESSION_TOKEN_KEY
from app.security import Role, SQLiteAuthStore, UserSeed, generate_temporary_password, hash_password


def authenticated_app(entrypoint: Path, tmp_path, monkeypatch, role: Role = Role.ADMIN) -> AppTest:
    password = generate_temporary_password()
    database_path = tmp_path / f"auth-{role.name}-{uuid4().hex}.db"
    store = SQLiteAuthStore(
        database_path,
        seeds=[UserSeed(f"test.{role.name.casefold()}@nsegg.ca", "Test User", role, hash_password(password))],
    )
    user, token = store.login(f"test.{role.name.casefold()}@nsegg.ca", password)
    store.change_own_password(user, generate_temporary_password())
    monkeypatch.setenv("EFNS_AUTH_DB", str(database_path))
    app = AppTest.from_file(entrypoint, default_timeout=20)
    app.session_state[SESSION_TOKEN_KEY] = token
    return app.run()
