"""Smoke coverage for the application shell and safe exports."""

from pathlib import Path
import tomllib

import pandas as pd
from streamlit.testing.v1 import AppTest

from app.services.export import spreadsheet_safe
from tests.auth_support import authenticated_app


def test_home_page_renders_without_exception(tmp_path, monkeypatch):
    entrypoint = Path(__file__).parents[1] / "app" / "Home.py"
    app = authenticated_app(entrypoint, tmp_path, monkeypatch)
    assert list(app.exception) == []
    assert any("Operations Dashboard" in block.value for block in app.markdown)


def test_all_navigation_pages_render_without_exception(tmp_path, monkeypatch):
    entrypoint = Path(__file__).parents[1] / "app" / "Home.py"
    app = authenticated_app(entrypoint, tmp_path, monkeypatch)
    for page in (
        "pages/1_Production_Import.py",
        "pages/2_Production_Data.py",
        "pages/3_Accounts_Facilities_Flocks.py",
        "pages/4_Reports.py",
        "pages/5_Flocks.py",
        "pages/6_Flock_Transactions.py",
        "pages/7_Quota_Registrations.py",
        "pages/8_Quota_Transactions.py",
        "pages/9_Salmonella_Tests.py",
        "pages/10_Salmonella_Report.py",
    ):
        app.switch_page(page).run()
        assert list(app.exception) == [], page


def test_spreadsheet_export_escapes_formula_prefixes():
    source = pd.DataFrame(
        {"VALUE": ["=1+1", "+cmd", "-2+3", "@SUM(A1:A2)", "ordinary"]}
    )
    safe = spreadsheet_safe(source)

    assert safe["VALUE"].tolist() == [
        "'=1+1",
        "'+cmd",
        "'-2+3",
        "'@SUM(A1:A2)",
        "ordinary",
    ]


def test_native_light_theme_and_scoped_custom_css():
    project_root = Path(__file__).parents[1]
    config = tomllib.loads(
        (project_root / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    )
    assert config["theme"] == {
        "base": "light",
        "primaryColor": "#3F56D9",
        "backgroundColor": "#F6F8FC",
        "secondaryBackgroundColor": "#FFFFFF",
        "textColor": "#172033",
        "font": "sans serif",
    }

    ui_source = (project_root / "app" / "ui.py").read_text(encoding="utf-8")
    assert "data-testid" not in ui_source
    assert "!important" not in ui_source
    assert "header[" not in ui_source


def test_primary_workflows_expose_clear_controls(tmp_path, monkeypatch):
    entrypoint = Path(__file__).parents[1] / "app" / "Home.py"
    app = authenticated_app(entrypoint, tmp_path, monkeypatch)

    app.switch_page("pages/2_Production_Data.py").run()
    assert any(button.label == "Reset filters" for button in app.button)

    app.switch_page("pages/3_Accounts_Facilities_Flocks.py").run()
    source = (Path(__file__).parents[1] / "app" / "pages" / "3_Accounts_Facilities_Flocks.py").read_text(encoding="utf-8")
    # The account workspace is now a Dynamics-style record page with a
    # structured edit form; Facilities live on their own dedicated page.
    assert 'st.tabs(["Account Information", "Address", "Account Roles"])' in source
    assert (Path(__file__).parents[1] / "app" / "pages" / "11_Facilities.py").exists()
    assert "Add New Flock" not in source

    app.switch_page("pages/4_Reports.py").run()
    assert any("Selected fields: 0" in caption.value for caption in app.caption)
