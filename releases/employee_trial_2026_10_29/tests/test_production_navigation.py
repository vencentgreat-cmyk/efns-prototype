"""Production navigation protocol checks, using synthetic local sessions only.

AppTest does not render the browser sidebar. Capture the real navigation message
to distinguish missing page registration from a client-side rendering problem.
"""
from pathlib import Path

import pytest
from streamlit.proto.Navigation_pb2 import Navigation
from streamlit.runtime.scriptrunner_utils.script_run_context import ScriptRunContext

from app.security import Permission, ROLE_PERMISSIONS, Role
from tests.auth_support import authenticated_app


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("entrypoint,prefix", [
    ("streamlit_app.py", "app/pages"), ("app/Home.py", "pages"),
])
@pytest.mark.parametrize("role", list(Role))
def test_production_entries_sent_to_sidebar_and_remain_registered(
        entrypoint, prefix, role, tmp_path, monkeypatch):
    monkeypatch.setenv("EFNS_RUNTIME_MODE", "local")
    monkeypatch.setenv("REPOSITORY_MODE", "mock")
    messages = []
    enqueue = ScriptRunContext.enqueue

    def capture(context, message):
        if message.WhichOneof("type") == "navigation":
            copy = Navigation()
            copy.CopyFrom(message.navigation)
            messages.append(copy)
        return enqueue(context, message)

    monkeypatch.setattr(ScriptRunContext, "enqueue", capture)
    app = authenticated_app(ROOT / entrypoint, tmp_path, monkeypatch, role)
    assert not app.exception
    can_import = Permission.IMPORT_DATA in ROLE_PERMISSIONS[role]
    expected = (["Production Import"] if can_import else []) + ["Production Data"]

    def assert_sidebar_message():
        message = messages[-1]
        assert message.position == Navigation.SIDEBAR
        assert "Production" in message.sections
        production = [page for page in message.app_pages if page.section_header == "Production"]
        assert [page.page_name for page in production] == expected
        assert len({page.page_script_hash for page in message.app_pages}) == len(message.app_pages)
        assert len({page.url_pathname for page in message.app_pages}) == len(message.app_pages)
        assert [page.url_pathname for page in production] == (
            ["Production_Import"] if can_import else []) + ["Production_Data"]
        assert all(page.icon for page in production)
        return {page.page_name: page for page in production}

    production = assert_sidebar_message()
    # Dashboard links resolve to exactly the same registered pages as the menu.
    links = {link.proto.label: link.proto for link in app.get("page_link")}
    assert links["Open Production Data"].page_script_hash == production["Production Data"].page_script_hash
    if can_import:
        assert links["Open Production Import"].page_script_hash == production["Production Import"].page_script_hash
    else:
        assert "Open Production Import" not in links

    app.run()
    assert not app.exception
    assert_sidebar_message()
    app.switch_page(f"{prefix}/2_Production_Data.py").run()
    assert not app.exception
    assert_sidebar_message()
    assert any("Production Data" in item.value for item in app.markdown)
    if can_import:
        app.switch_page(f"{prefix}/1_Production_Import.py").run()
        assert not app.exception
        assert_sidebar_message()
