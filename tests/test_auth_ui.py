"""Headless Streamlit coverage for login and protected application pages."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.security import Role, SQLiteAuthStore, UserSeed, generate_temporary_password, hash_password
from tests.auth_support import authenticated_app


ROOT = Path(__file__).parents[1]


def test_home_requires_login(tmp_path, monkeypatch):
    monkeypatch.setenv("EFNS_AUTH_DB", str(tmp_path / "unauthenticated.db"))
    app = AppTest.from_file(ROOT / "app" / "Home.py", default_timeout=20).run()
    assert list(app.exception) == []
    assert any("Sign in to EFNS" in block.value for block in app.markdown)
    assert not any("Operations Dashboard" in block.value for block in app.markdown)


def test_snowflake_mode_never_renders_second_password_login(monkeypatch):
    monkeypatch.setenv("EFNS_RUNTIME_MODE", "snowflake")
    app = AppTest.from_file(ROOT / "app" / "Home.py", default_timeout=20).run()
    assert list(app.exception) == []
    assert any("Access not provisioned" in block.value for block in app.markdown)
    assert not any(item.label == "Password" for item in app.text_input)


def test_root_snowflake_entrypoint_preserves_local_login(monkeypatch, tmp_path):
    monkeypatch.setenv("EFNS_RUNTIME_MODE", "local")
    monkeypatch.setenv("EFNS_AUTH_DB", str(tmp_path / "root-entry.db"))
    app = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=20).run()
    assert list(app.exception) == []
    assert any("Sign in to EFNS" in block.value for block in app.markdown)


def test_valid_login_creates_session_and_requires_password_change(tmp_path, monkeypatch):
    password = generate_temporary_password()
    database_path = tmp_path / "login.db"
    SQLiteAuthStore(
        database_path,
        seeds=[UserSeed("login.user@nsegg.ca", "Login User", Role.REPORTING_VIEWER, hash_password(password))],
    )
    monkeypatch.setenv("EFNS_AUTH_DB", str(database_path))
    app = AppTest.from_file(ROOT / "app" / "Home.py", default_timeout=20).run()
    app.text_input(key="auth_login_email").set_value("login.user@nsegg.ca")
    app.text_input(key="auth_login_password").set_value(password)
    app.button(key="FormSubmitter:efns_login_form-Sign in").click().run()
    assert list(app.exception) == []
    assert any("Change temporary password" in block.value for block in app.markdown)


def test_logout_clears_protected_application(tmp_path, monkeypatch):
    app = authenticated_app(ROOT / "app" / "Home.py", tmp_path, monkeypatch, Role.ADMIN)
    assert any("Operations Dashboard" in block.value for block in app.markdown)
    app.button(key="efns_logout").click().run()
    assert list(app.exception) == []
    assert any("Sign in to EFNS" in block.value for block in app.markdown)


def test_reporting_viewer_cannot_open_import_page_directly(tmp_path, monkeypatch):
    page = ROOT / "app" / "pages" / "1_Production_Import.py"
    app = authenticated_app(page, tmp_path, monkeypatch, Role.REPORTING_VIEWER)
    assert list(app.exception) == []
    assert any("Access denied" in block.value for block in app.markdown)
    assert not any("Production Import" in block.value for block in app.markdown)


def test_reporting_viewer_can_open_flock_quota_preview_page(tmp_path, monkeypatch):
    page = ROOT / "app" / "pages" / "19_Flock_Quota_Import.py"
    app = authenticated_app(page, tmp_path, monkeypatch, Role.REPORTING_VIEWER)
    assert list(app.exception) == []
    assert not any("Access denied" in block.value for block in app.markdown)
    assert any("Upload and validation never write" in caption.value for caption in app.caption)


def test_developer_can_open_audit_but_not_user_management(tmp_path, monkeypatch):
    audit = authenticated_app(
        ROOT / "app" / "pages" / "16_Audit_Log.py", tmp_path, monkeypatch, Role.DEVELOPER
    )
    assert list(audit.exception) == []
    assert any("Audit Log" in block.value for block in audit.markdown)

    users = authenticated_app(
        ROOT / "app" / "pages" / "15_User_Management.py", tmp_path, monkeypatch, Role.DEVELOPER
    )
    assert list(users.exception) == []
    assert any("Access denied" in block.value for block in users.markdown)


def test_admin_can_open_user_management(tmp_path, monkeypatch):
    users = authenticated_app(
        ROOT / "app" / "pages" / "15_User_Management.py", tmp_path, monkeypatch, Role.ADMIN
    )
    assert list(users.exception) == []
    assert any("User Management" in block.value for block in users.markdown)
    assert any(button.label == "Add user" for button in users.button)
