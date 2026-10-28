"""Registered-page navigation must never depend on browser URLs."""

from pathlib import Path
from types import SimpleNamespace
import os
import runpy
import ast

import pytest

import app.navigation as navigation


class RerunRequested(Exception):
    pass


def fake_streamlit():
    def rerun():
        raise RerunRequested

    return SimpleNamespace(session_state={}, rerun=rerun, switch_page=lambda page: None)


def test_record_selection_is_kept_in_page_local_session_state(monkeypatch):
    fake = fake_streamlit()
    monkeypatch.setattr(navigation, "st", fake)
    monkeypatch.setattr(navigation, "_caller_scope", lambda: "3_Accounts_Facilities_Flocks")

    assert navigation.read_record_view() == navigation.RecordView("list", None)
    with pytest.raises(RerunRequested):
        navigation.open_view("detail", "account-123")
    assert navigation.read_record_view() == navigation.RecordView("detail", "account-123")

    with pytest.raises(RerunRequested):
        navigation.open_view("list")
    assert navigation.read_record_view() == navigation.RecordView("list", None)


def test_registered_page_switch_sets_target_state_without_url(monkeypatch):
    switched = []
    fake = fake_streamlit()
    fake.switch_page = switched.append
    monkeypatch.setattr(navigation, "st", fake)

    navigation.open_module("Quota_Transactions", "new", quota_id="quota-1")

    scope = "8_Quota_Transactions"
    assert fake.session_state[navigation._view_key(scope, "view")] == "new"
    assert fake.session_state[navigation._view_key(scope, "parameter_quota_id")] == "quota-1"
    assert switched == [navigation.page_file("8_Quota_Transactions.py")]


@pytest.mark.parametrize('prefix', [None, 'pages', 'app/pages', 'app/pages/', 'stale/pages'])
@pytest.mark.parametrize('cwd', ['.', 'app'])
def test_registered_switch_is_independent_of_prefix_and_cwd(monkeypatch,prefix,cwd):
    root=Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root/cwd)
    if prefix is None:
        monkeypatch.delenv('EFNS_PAGE_PREFIX',raising=False)
    else:
        monkeypatch.setenv('EFNS_PAGE_PREFIX',prefix)
    fake=fake_streamlit()
    switched=[]
    fake.switch_page=switched.append
    monkeypatch.setattr(navigation,'st',fake)
    navigation.open_module('Flock_Transactions','detail','synthetic-delivery')
    assert switched==[str(root/'app/pages/6_Flock_Transactions.py')]
    assert fake.session_state['_efns_record_6_Flock_Transactions_id']=='synthetic-delivery'
    assert fake.session_state['_efns_record_6_Flock_Transactions_view']=='detail'


@pytest.mark.parametrize('previous_prefix', [None, 'pages', 'stale/pages'])
def test_switch_after_root_entrypoint_restores_environment(monkeypatch,previous_prefix):
    root=Path(__file__).resolve().parents[1]
    if previous_prefix is None:
        monkeypatch.delenv('EFNS_PAGE_PREFIX',raising=False)
    else:
        monkeypatch.setenv('EFNS_PAGE_PREFIX',previous_prefix)
    seen=[]
    original_run_path=runpy.run_path
    def home_stub(path,**_kwargs):
        assert Path(path)==root/'app/Home.py'
        seen.append(os.environ.get('EFNS_PAGE_PREFIX'))
        return {}
    monkeypatch.setattr(runpy,'run_path',home_stub)
    original_run_path(str(root/'streamlit_app.py'),run_name='__main__')
    assert seen==['app/pages']
    assert os.environ.get('EFNS_PAGE_PREFIX')==previous_prefix
    fake=fake_streamlit()
    switched=[]
    fake.switch_page=switched.append
    monkeypatch.setattr(navigation,'st',fake)
    navigation.open_module('Flock_Transactions','detail','synthetic-delivery')
    assert switched==[navigation.page_file('6_Flock_Transactions.py')]


def test_all_module_targets_exist_and_home_uses_shared_resolver():
    for filename in navigation._PAGE_FILES.values():
        assert Path(navigation.page_file(filename)).is_file()
    home=(Path(__file__).resolve().parents[1]/'app/Home.py').read_text(encoding='utf-8')
    assert 'from app.navigation import page_file, timestamp_column' in home
    assert 'def page_file(' not in home


def test_all_file_page_registrations_links_and_switches_share_path_resolver():
    root=Path(__file__).resolve().parents[1]
    for source in (root/'app').rglob('*.py'):
        tree=ast.parse(source.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if not (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
                    and isinstance(node.func.value,ast.Name) and node.func.value.id=='st'
                    and node.func.attr in {'Page','page_link','switch_page'}):
                continue
            target=node.args[0]
            if isinstance(target,ast.Name) and target.id=='dashboard':
                assert node.func.attr=='Page'
            elif isinstance(target,ast.Subscript):
                assert ast.unparse(target)=='st.session_state[\'_efns_dashboard_page\']'
                assert node.func.attr=='switch_page'
            else:
                assert isinstance(target,ast.Call) and isinstance(target.func,ast.Name) and target.func.id=='page_file', (source,node.lineno)
                if isinstance(target.args[0],ast.Constant):
                    assert Path(navigation.page_file(target.args[0].value)).is_file()


def test_operational_pages_do_not_generate_browser_record_links():
    root = Path(__file__).parents[1]
    pages = [
        root / "app/pages/3_Accounts_Facilities_Flocks.py",
        root / "app/pages/5_Flocks.py",
        root / "app/pages/6_Flock_Transactions.py",
        root / "app/pages/7_Quota_Registrations.py",
        root / "app/pages/8_Quota_Transactions.py",
        root / "app/pages/9_Salmonella_Tests.py",
        root / "app/pages/11_Facilities.py",
        root / "app/pages/13_Facility_Details.py",
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in pages)
    for forbidden in (
        "LinkColumn",
        "current_page_url",
        "module_url",
        "module_view_url",
        "snowflake.app",
        "href=",
    ):
        assert forbidden not in source


def test_account_list_uses_selection_and_plain_account_name():
    source = (
        Path(__file__).parents[1] / "app/pages/3_Accounts_Facilities_Flocks.py"
    ).read_text(encoding="utf-8")
    assert 'selection_mode="single-row"' in source
    assert 'st.session_state["account_selected_id"] = selected_id' in source
    assert 'open_view("detail", selected_id)' in source
    assert '"ORGANIZATION_NAME": st.column_config.TextColumn("Account Name"' in source
