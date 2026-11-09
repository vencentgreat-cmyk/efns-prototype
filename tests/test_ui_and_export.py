"""Smoke coverage for the application shell and safe exports."""

from pathlib import Path
import re
import tomllib

import pandas as pd
import pytest
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
        "pages/19_Daily_Flock_Quota_Import.py",
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
        "borderColor": "#C7D0DF",
        "dataframeHeaderBackgroundColor": "#E8EEF7",
        "showWidgetBorder": True,
        "linkColor": "#2453BE",
        "sidebar": {
            "primaryColor": "#3F56D9",
            "backgroundColor": "#F1F5F9",
            "secondaryBackgroundColor": "#FFFFFF",
            "textColor": "#172033",
            "borderColor": "#C7D0DF",
        },
    }

    ui_source = (project_root / "app" / "ui.py").read_text(encoding="utf-8")
    styles = re.findall(r'<style>(.*?)</style>', ui_source, re.S)
    assert len(styles) == 1
    _assert_scoped_custom_css(styles[0])
    assert 'class="efns-page-title"' in ui_source


def _assert_scoped_custom_css(css):
    """Allow the intentional title override, never native-widget-wide CSS."""
    title = '[data-testid="stMarkdownContainer"] .efns-page-header h1.efns-page-title'
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    rules = re.findall(r'([^{}]+)\{([^{}]*)\}', css)
    assert rules
    assert 'header[' not in css
    assert not re.search(r'@(import|font-face|keyframes)\b', css)
    important = []
    for selectors, declarations in rules:
        for selector in selectors.split(','):
            selector = selector.strip()
            assert selector == title or re.fullmatch(r'\.efns-[\w-]+(?:\s+(?:small|strong|span))?', selector), selector
            for declaration in declarations.split(';'):
                if '!important' in declaration:
                    assert selector == title
                    assert declaration.strip() == 'color: #172033 !important'
                    important.append(declaration.strip())
    assert important == ['color: #172033 !important']


@pytest.mark.parametrize('selector',[
    '[data-testid="stButton"] button',
    'header[data-testid="stHeader"]',
    '[data-testid="stMarkdownContainer"] h1',
    '.efns-brand, button',
    '.efns-brand',
])
def test_scoped_css_guard_rejects_native_selectors_and_other_important_rules(selector):
    with pytest.raises(AssertionError):
        _assert_scoped_custom_css(selector+' { color: #172033 !important; }')


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
    assert any(radio.label == "Report Center section" for radio in app.radio)
    report_source = (Path(__file__).parents[1] / "app" / "pages" / "4_Reports.py").read_text(encoding="utf-8")
    assert '["Report Library", "Customize Report", "Saved Reports"]' in report_source
    assert "LinkColumn" not in report_source
