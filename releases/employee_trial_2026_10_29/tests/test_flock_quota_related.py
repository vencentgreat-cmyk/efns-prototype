"""Synthetic Flock quota display/navigation and offline repository coverage."""
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from app.security import AuthorizationError, Permission, Role
from app.services.flock_related import flock_quota_link
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain

ROOT = Path(__file__).resolve().parents[1]
QUOTA = dict(QUOTA_ID='synthetic-quota', QUOTA_NAME='Synthetic layer registration',
             REGISTRATION_NUMBER='SYN-Q-001', QUOTA_TYPE='Egg Production', STATUS='Inactive')
FLOCK = dict(QUOTA_ID=QUOTA['QUOTA_ID'], FLOCK_QUOTA_TYPE='Special Permit')


class QuotaReadDouble:
    """Only the existing single-record read may run; never opens a connection."""
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def query(self, sql, params=None):
        assert sql.lstrip().upper().startswith('SELECT')
        assert 'CORE.QUOTA_REGISTRATION' in sql and 'WHERE QUOTA_ID = %s' in sql
        assert params and len(params) == 1
        self.calls.append((sql, params))
        return pd.DataFrame([r for r in self.rows if r['QUOTA_ID'] == params[0]])

    def execute(self, *args, **kwargs):
        raise AssertionError('A display lookup must never write')


@pytest.fixture(params=['mock', 'snowflake'])
def quota_repo(request, monkeypatch):
    def build(rows):
        if request.param == 'mock':
            repo = MockRepository()
            repo._quota_registrations = pd.DataFrame(rows, columns=QUOTA)
        else:
            monkeypatch.setenv('SNOWFLAKE_DATABASE', 'EFNS_DEV')
            monkeypatch.setenv('SNOWFLAKE_SCHEMA_CORE', 'CORE')
            monkeypatch.setattr('data.repositories.snowflake.create_executor',
                                lambda: pytest.fail('No Snowflake executor may be created'))
            repo = SnowflakeRepository(executor=QuotaReadDouble(rows))
        return repo
    return build


def test_linked_quota_both_repository_paths(quota_repo):
    repo = quota_repo([QUOTA])
    before = deepcopy(getattr(repo, '_quota_registrations', None))
    result = flock_quota_link(repo, FLOCK)
    assert result.label == QUOTA['QUOTA_NAME'] and result.quota_id == QUOTA['QUOTA_ID']
    assert result.flock_quota_type == 'Special Permit'  # Not the registration's type.
    assert result.can_open and result.note is None  # Inactive linked quotas still resolve.
    if isinstance(repo, MockRepository):
        pd.testing.assert_frame_equal(repo._quota_registrations, before)
    else:
        assert len(repo.executor.calls) == 1
        assert repo.executor.calls[0][1] == (QUOTA['QUOTA_ID'],)


@pytest.mark.parametrize('missing', [None, '', pd.NA, float('nan')])
def test_no_quota_is_dash_without_lookup(quota_repo, monkeypatch, missing):
    repo = quota_repo([])
    monkeypatch.setattr(repo, 'get_quota_registration', lambda *_: pytest.fail('No ID: no lookup'))
    result = flock_quota_link(repo, dict(FLOCK, QUOTA_ID=missing))
    assert result.label == '—' and result.quota_id is None and not result.can_open
    assert result.note is None


def test_stale_quota_is_id_and_note_both_paths(quota_repo):
    result = flock_quota_link(quota_repo([]), FLOCK)
    assert result.label == QUOTA['QUOTA_ID'] and not result.can_open
    assert result.note == 'Quota Registration not found.'


@pytest.mark.parametrize('name,number,expected', [
    (None, 'SYN-Q-001', 'SYN-Q-001'), ('', None, 'Quota Registration'),
    (pd.NA, pd.NA, 'Quota Registration'),
])
def test_title_precedence_and_null_type(quota_repo, name, number, expected):
    repo = quota_repo([dict(QUOTA, QUOTA_NAME=name, REGISTRATION_NUMBER=number)])
    result = flock_quota_link(repo, dict(FLOCK, FLOCK_QUOTA_TYPE=pd.NA))
    assert result.label == expected and result.flock_quota_type == '—'


def test_permission_flag_prevents_lookup():
    class Forbidden:
        def get_quota_registration(self, *_):
            pytest.fail('Denied viewer must not query Quota Registrations')
    result = flock_quota_link(Forbidden(), FLOCK, can_view=False)
    assert result.label == '—' and result.quota_id is None and not result.can_open
    assert result.note == 'Quota details are not available for your role.'


def test_repository_permission_denial_does_not_expose_label():
    class Denied:
        def get_quota_registration(self, *_):
            raise AuthorizationError('Synthetic restricted registration')
    result = flock_quota_link(Denied(), FLOCK)
    assert result.label == '—' and result.quota_id is None and not result.can_open
    assert result.note == 'Quota details are not available for your role.'


def flock_app(repo, flock_id, tmp_path, monkeypatch, role=Role.ADMIN,
              entrypoint='streamlit_app.py', prefix='app/pages'):
    monkeypatch.setenv('EFNS_RUNTIME_MODE', 'local')
    monkeypatch.setenv('REPOSITORY_MODE', 'mock')
    app = authenticated_app(ROOT/entrypoint, tmp_path, monkeypatch, role)
    app.session_state['_base_repo'] = repo
    app.session_state['_efns_record_5_Flocks_view'] = 'detail'
    app.session_state['_efns_record_5_Flocks_id'] = flock_id
    return app.switch_page(f'{prefix}/5_Flocks.py').run()


def quota_blocks(app, kind):
    return [block.value for tab in (app.tabs[0], app.tabs[2]) for block in tab.get(kind)]


@pytest.mark.parametrize('state', ['linked', 'none', 'stale'])
def test_both_tabs_display_quota_without_changing_records(chain,tmp_path,monkeypatch,state):
    repo,_,_,_,quota,flock,_ = chain
    if state != 'linked':
        repo._flocks.loc[repo._flocks.FLOCK_ID.eq(flock),'QUOTA_ID'] = None if state == 'none' else 'synthetic-stale-id'
    snapshots = {name: getattr(repo,name).copy(deep=True) for name in
                 ('_accounts','_facilities','_flocks','_quota_registrations','_flock_transactions')}
    calls=[]
    read=repo.get_quota_registration
    monkeypatch.setattr(repo,'get_quota_registration',lambda identity: calls.append(identity) or read(identity))
    app = flock_app(repo,flock,tmp_path,monkeypatch)
    assert not app.exception and not app.error
    label = 'DEV_TEST register' if state == 'linked' else '—' if state == 'none' else 'synthetic-stale-id'
    for tab in (app.tabs[0],app.tabs[2]):
        markdown=[block.value for block in tab.get('markdown')]
        assert '**Quota**  \n'+label in markdown
        assert '**Flock Quota Type**  \nEgg Production' in markdown
    assert len(calls) == (0 if state == 'none' else 1)
    keys={button.key for button in app.button}
    assert ('flock_parent_quota' in keys) == (state == 'linked')
    assert ('flock_related_quota' in keys) == (state == 'linked')
    if state == 'stale':
        assert quota_blocks(app,'caption').count('Quota Registration not found.') == 2
    for name,before in snapshots.items():
        pd.testing.assert_frame_equal(before,getattr(repo,name))


@pytest.mark.parametrize('role', list(Role))
def test_existing_read_roles_can_see_quota(chain,tmp_path,monkeypatch,role):
    repo,_,_,_,_,flock,_ = chain
    app=flock_app(repo,flock,tmp_path,monkeypatch,role)
    assert not app.exception and not app.error
    assert quota_blocks(app,'markdown').count('**Quota**  \nDEV_TEST register') == 2
    assert app.button(key='flock_related_quota').label == 'View Quota Registration'


@pytest.mark.parametrize('entrypoint,prefix', [('streamlit_app.py','app/pages'),('app/Home.py','pages')])
@pytest.mark.parametrize('key', ['flock_parent_quota', 'flock_related_quota'])
def test_open_quota_uses_existing_registered_navigation(chain,tmp_path,monkeypatch,entrypoint,prefix,key):
    repo,_,_,_,quota,flock,_ = chain
    before=repo._flocks.copy(deep=True)
    app=flock_app(repo,flock,tmp_path,monkeypatch,entrypoint=entrypoint,prefix=prefix)
    app.button(key=key).click().run()
    assert not app.exception and not app.error
    assert app.session_state['_efns_record_7_Quota_Registrations_view']=='detail'
    assert app.session_state['_efns_record_7_Quota_Registrations_id']==quota
    assert any('DEV_TEST register' in block.value for block in app.markdown)
    pd.testing.assert_frame_equal(before,repo._flocks)


def test_denied_quota_lookup_has_no_new_label_or_link(chain,tmp_path,monkeypatch):
    repo,_,_,_,_,flock,_ = chain
    def deny(*_):
        raise AuthorizationError('Synthetic denied quota lookup')
    monkeypatch.setattr(repo,'get_quota_registration',deny)
    app=flock_app(repo,flock,tmp_path,monkeypatch)
    assert not app.exception and not app.error
    assert quota_blocks(app,'markdown').count('**Quota**  \n—') == 2
    assert quota_blocks(app,'caption').count('Quota details are not available for your role.') == 2
    assert not any(button.key in {'flock_parent_quota','flock_related_quota'} for button in app.button)
