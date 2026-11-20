"""Offline viewer role mapping: synthetic identities, no live Snowflake calls."""
from contextlib import contextmanager
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from types import SimpleNamespace
import re

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import app.auth as auth
from app.runtime import RuntimeMode
from app.security import Role, User, UserValidationError, AuthorizationError, SQLiteAuthStore
from app.snowflake_identity import (MAIN_SNOWFLAKE_ADMIN_USERNAME, main_admin_user,
    normalize_snowflake_username, resolve_snowflake_username)
from app.snowflake_security import SnowflakeAuthStore
from app.services.authorized_repository import AuthorizedRepository
from data.repositories.base import RepositoryError
from data.repositories.mock import MockRepository

ROOT=Path(__file__).resolve().parents[1]
PAGES=sorted((ROOT/'app/pages').glob('*.py'))
DENIED='You do not have access to the EFNS app yet. Please contact the administrator.'


def entry(name='USER_A',role=Role.DATA_EDITOR,active=True,user_id='synthetic-a'):
    return dict(USER_ID=user_id,EMAIL=name.lower()+'@nsegg.ca',DISPLAY_NAME=name,
        ROLE=role.value,ACTIVE=active,SNOWFLAKE_USERNAME=name,
        CREATED_AT='2026-01-01',UPDATED_AT='2026-01-01',LAST_LOGIN_AT=None)


class Directory:
    """SQL-protocol fake including the existing shared transaction/lock boundary."""
    def __init__(self,users=(),*,schema=True,sql_user='EFNSDATABASE'):
        self.users=deepcopy(list(users));self.schema=schema;self.sql_user=sql_user
        self.calls=[];self.audits=[];self.lock=RLock()
    def query(self,sql,params=None):
        params=tuple(params or ());self.calls.append((sql,params))
        if 'CURRENT_USER()' in sql:return pd.DataFrame([{'USER_NAME':self.sql_user}])
        if 'SNOWFLAKE_USERNAME' in sql and not self.schema:raise RepositoryError('Synthetic missing mapping column')
        rows=deepcopy(self.users)
        if 'UPPER(TRIM(SNOWFLAKE_USERNAME))' in sql:
            rows=[r for r in rows if str(r.get('SNOWFLAKE_USERNAME') or '').strip().upper()==params[0]]
            if 'USER_ID <>' in sql:rows=[r for r in rows if r['USER_ID']!=params[1]]
        elif 'WHERE USER_ID = %s' in sql:rows=[r for r in rows if r['USER_ID']==params[0]]
        elif 'LOWER(EMAIL)' in sql:rows=[r for r in rows if r['EMAIL'].lower()==params[0]]
        if 'ADMIN_COUNT' in sql:return pd.DataFrame([{'ADMIN_COUNT':sum(r['ROLE']=='Admin' and r['ACTIVE'] and r['USER_ID']!=params[-1] for r in rows)}])
        if 'LIMIT 2' in sql:rows=rows[:2]
        columns=list(entry())
        if not self.schema:
            columns.remove('SNOWFLAKE_USERNAME')
            for row in rows:row.pop('SNOWFLAKE_USERNAME',None)
        return pd.DataFrame(rows,columns=columns)
    def execute(self,sql,params=None):
        params=tuple(params or ());self.calls.append((sql,params))
        if 'INTAKE_LOCK' in sql:return 1
        if 'AUDIT_EVENT' in sql:self.audits.append(params);return 1
        if sql.startswith('INSERT INTO'):
            fields=sql.split('(',1)[1].split(')',1)[0].replace(' ','').split(',')
            bindings=fields[:5] if 'SNOWFLAKE_USERNAME' in fields else fields[:4]
            row=dict(zip(bindings,params));row.update(ACTIVE=True,CREATED_AT='2026-01-01',UPDATED_AT='2026-01-01',LAST_LOGIN_AT=None)
            row.setdefault('SNOWFLAKE_USERNAME',None);self.users.append(row);return 1
        if sql.startswith('UPDATE'):
            target=next(r for r in self.users if r['USER_ID']==params[-1])
            target.update(ROLE=params[0],ACTIVE=params[1])
            if 'SNOWFLAKE_USERNAME' in sql:target['SNOWFLAKE_USERNAME']=params[2]
            return 1
        if sql.startswith('DELETE'):
            self.users=[r for r in self.users if r['USER_ID']!=params[0]];return 1
        raise AssertionError(sql)
    @contextmanager
    def transaction(self):
        with self.lock:
            before=deepcopy(self.users),deepcopy(self.audits)
            try:yield self
            except Exception:self.users,self.audits=before;raise
    intake_transaction=transaction


def fake_runtime(monkeypatch,directory,username='USER_A'):
    store=SnowflakeAuthStore(directory)
    monkeypatch.setattr(auth,'current_runtime_mode',lambda:RuntimeMode.SNOWFLAKE)
    monkeypatch.setattr(auth,'get_auth_store',lambda:store)
    monkeypatch.setattr(st,'user',SimpleNamespace(user_name=username))
    monkeypatch.setattr(st,'experimental_user',SimpleNamespace())
    return store


def test_supported_viewer_api_preferred_over_legacy_and_sql():
    details={}
    profile=SimpleNamespace(user=SimpleNamespace(user_name=' user_a '),experimental_user=SimpleNamespace(user_name='USER_B'))
    def forbidden():pytest.fail('SQL fallback must not run for a viewer identity')
    assert resolve_snowflake_username(profile,executor_factory=forbidden,diagnostics=details)=='USER_A'
    assert details['source']=='st.user.user_name'


def test_legacy_viewer_api_supported_when_modern_username_unavailable():
    details={}
    assert resolve_snowflake_username(SimpleNamespace(user={},experimental_user={'user_name':'USER_A'}),diagnostics=details)=='USER_A'
    assert details['source']=='st.experimental_user.user_name'


@pytest.mark.parametrize('sql_user',['USER_A',MAIN_SNOWFLAKE_ADMIN_USERNAME,None])
def test_unverifiable_sql_result_never_grants_a_role_or_main_override(sql_user):
    directory=Directory([entry(role=Role.ADMIN)],sql_user=sql_user);details={}
    assert resolve_snowflake_username(SimpleNamespace(user={}),executor_factory=lambda:directory,diagnostics=details) is None
    assert directory.calls==[('SELECT CURRENT_USER() AS USER_NAME',())]
    assert details['username'] is None and 'unverified' in details['source']


@pytest.mark.parametrize('role',list(Role))
def test_mapped_username_gets_exact_existing_role_and_trimmed_case_match(role):
    directory=Directory([entry(name=' user_a ',role=role)]);store=SnowflakeAuthStore(directory)
    mapped=store.resolve_identity(' UsEr_A ')
    assert mapped.user_id=='synthetic-a' and mapped.role is role
    assert mapped.snowflake_username=='USER_A'
    assert directory.calls[0][1]==('USER_A',)
    assert store.resolve_identity('user_a@nsegg.ca') is None  # No email-based fallback.


@pytest.mark.parametrize('active',[False,0,None,'false','disabled'])
def test_inactive_disabled_or_missing_activation_denied(active):
    assert SnowflakeAuthStore(Directory([entry(active=active)])).resolve_identity('USER_A') is None


def test_ambiguous_mapping_denied_even_if_one_is_active():
    rows=[entry(),entry(active=False,user_id='synthetic-other')]
    assert SnowflakeAuthStore(Directory(rows)).resolve_identity('USER_A') is None


def test_main_override_named_and_independent_of_user_management_schema():
    assert MAIN_SNOWFLAKE_ADMIN_USERNAME=='EFNSDATABASE'
    directory=Directory(schema=False);store=SnowflakeAuthStore(directory)
    main=store.resolve_identity('EFNSDATABASE')
    assert main.role is Role.ADMIN and main.active and not directory.calls
    assert store.resolve_identity('USER_A') is None
    assert store.username_mapping_available is False


@pytest.mark.parametrize('value',['USER A','USER_A@nsegg.ca',"USER_A';",'1USER','USER_A\nB','A'*256,False])
def test_username_validation_rejects_unsupported_identifiers(value):
    with pytest.raises(UserValidationError):normalize_snowflake_username(value)


def test_snowflake_create_update_unique_across_inactive_entries_and_blank_unmapping():
    directory=Directory([entry(active=False)]);store=SnowflakeAuthStore(directory);admin=main_admin_user()
    with pytest.raises(UserValidationError,match='already assigned'):
        store.create_user(admin,'user_b@nsegg.ca','USER_B',Role.DATA_EDITOR,snowflake_username=' user_a ')
    created,_=store.create_user(admin,'user_b@nsegg.ca','USER_B',Role.REPORTING_VIEWER,snowflake_username=' user_b ')
    assert created.snowflake_username=='USER_B'
    assert any('INTAKE_LOCK' in sql for sql,_ in directory.calls)
    with pytest.raises(UserValidationError,match='already assigned'):
        store.update_user(admin,created.user_id,role=created.role,active=True,snowflake_username='USER_A')
    updated=store.update_user(admin,created.user_id,role=Role.DATA_EDITOR,active=True)
    assert updated.snowflake_username=='USER_B'
    updated=store.update_user(admin,created.user_id,role=updated.role,active=True,snowflake_username='')
    assert updated.snowflake_username is None and store.resolve_identity('USER_B') is None
    assert len(directory.audits)==3  # Existing create/update events only.


def test_concurrent_duplicate_mapping_has_one_winner():
    directory=Directory();stores=[SnowflakeAuthStore(directory),SnowflakeAuthStore(directory)]
    def create(index):
        try:return stores[index].create_user(main_admin_user(),f'user_{index}@nsegg.ca',f'USER_{index}',Role.DATA_EDITOR,snowflake_username='USER_A')[0]
        except UserValidationError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(create,(0,1)))
    assert sum(value is not None for value in results)==1 and len(directory.users)==1


def test_local_user_management_metadata_preserves_password_session_behavior(tmp_path):
    store=SQLiteAuthStore(tmp_path/'synthetic.db',seeds=[]);admin=main_admin_user()
    first,password=store.create_user(admin,'user_a@nsegg.ca','USER_A',Role.DATA_EDITOR,snowflake_username=' user_a ')
    assert first.snowflake_username=='USER_A'
    with pytest.raises(UserValidationError,match='already assigned'):
        store.create_user(admin,'user_b@nsegg.ca','USER_B',Role.DATA_EDITOR,snowflake_username='USER_A')
    logged,token=store.login(first.email,password)
    assert store.resolve_session(token).user_id==first.user_id
    updated=store.update_user(admin,first.user_id,role=Role.REPORTING_VIEWER,active=True)
    assert updated.snowflake_username=='USER_A' and store.resolve_session(token).role is Role.REPORTING_VIEWER


def test_audit_and_history_actor_is_the_mapped_signed_in_user(monkeypatch):
    directory=Directory([entry()]);store=fake_runtime(monkeypatch,directory)
    mapped=auth.current_user();assert mapped.user_id=='synthetic-a'
    base=MockRepository();repo=AuthorizedRepository(base,store,mapped)
    identity=repo.create_record_once('ACCOUNT',dict(ORGANIZATION_NAME='SYNTHETIC ACCOUNT',REGISTRATION_NUMBER='SYNTHETIC-001',STATUS='Active'),'synthetic-create')
    history=base.get_record_revisions_for('ACCOUNT',identity)
    assert history.iloc[0].RECORDED_BY==mapped.user_id
    assert base._migration_review_audit[-1]['ACTOR_USER_ID']==mapped.user_id
    store.record_action(mapped,'EXPORT','REPORT','synthetic-report')
    assert directory.audits[-1][1:3]==(mapped.user_id,mapped.email)


class NoBusinessReads:
    def __getattr__(self,name):
        if name=='executor':return None
        raise AssertionError('Business storage accessed before authentication: '+name)


@pytest.mark.parametrize('page',PAGES,ids=lambda p:p.stem)
@pytest.mark.parametrize('scenario',['unknown','inactive','disabled','missing-identity','missing-column'])
def test_every_page_denies_without_business_data_menus_or_downloads(monkeypatch,page,scenario):
    rows=[] if scenario=='unknown' else [entry(active=scenario not in {'inactive','disabled'})]
    directory=Directory(rows,schema=scenario!='missing-column')
    store=fake_runtime(monkeypatch,directory,username=None if scenario=='missing-identity' else 'USER_A')
    app=AppTest.from_file(page,default_timeout=20)
    app.session_state['_base_repo']=NoBusinessReads()
    app.session_state['_snowflake_auth_store']=store
    app.run()
    assert not app.exception
    assert [message.value for message in app.error]==[DENIED]
    assert not app.dataframe and not app.get('download_button') and not app.selectbox
    assert not app.get('page_link') and not app.get('file_uploader')
    assert not any(expander.label=='Sign-in diagnostics' for expander in app.expander)


@pytest.mark.parametrize('entrypoint',['streamlit_app.py','app/Home.py'])
def test_entrypoints_fail_closed_with_no_identity_even_with_old_session_state(monkeypatch,entrypoint):
    directory=Directory([entry(role=Role.ADMIN)])
    store=fake_runtime(monkeypatch,directory,username=None)
    app=AppTest.from_file(ROOT/entrypoint,default_timeout=20)
    app.session_state[auth.SESSION_TOKEN_KEY]='synthetic-old-local-token'
    app.session_state['_base_repo']=NoBusinessReads();app.session_state['_snowflake_auth_store']=store
    app.run()
    assert not app.exception and [message.value for message in app.error]==[DENIED]
    assert not app.dataframe and not app.get('page_link')


@pytest.mark.parametrize('role',[Role.ADMIN,Role.REPORTING_VIEWER])
def test_sidebar_identity_and_admin_only_signin_diagnostics(monkeypatch,role):
    store=fake_runtime(monkeypatch,Directory([entry(role=role)]))
    app=AppTest.from_file(ROOT/'streamlit_app.py',default_timeout=20)
    app.session_state['_base_repo']=MockRepository();app.session_state['_snowflake_auth_store']=store
    app.run()
    assert not app.exception
    assert any('USER_A' in caption.value for caption in app.sidebar.caption)
    assert any(role.value in caption.value for caption in app.sidebar.caption)
    assert any(expander.label=='Sign-in diagnostics' for expander in app.expander)==(role is Role.ADMIN)


def test_main_can_open_empty_or_old_schema_user_management(monkeypatch):
    store=fake_runtime(monkeypatch,Directory(schema=False),MAIN_SNOWFLAKE_ADMIN_USERNAME)
    app=AppTest.from_file(ROOT/'app/pages/15_User_Management.py',default_timeout=20)
    app.session_state['_base_repo']=MockRepository();app.session_state['_snowflake_auth_store']=store
    app.run()
    assert not app.exception and any(button.label=='Add user' for button in app.button)
    assert app.text_input(key='user_create_snowflake_username').disabled
    assert any('schema update' in info.value for info in app.info)


def test_schema_missing_mapping_write_rejected_but_main_role_stays_available():
    directory=Directory(schema=False);store=SnowflakeAuthStore(directory)
    with pytest.raises(UserValidationError,match='schema update'):
        store.create_user(main_admin_user(),'user_a@nsegg.ca','USER_A',Role.DATA_EDITOR,snowflake_username='USER_A')
    assert not directory.users and not directory.audits
    assert store.resolve_identity(MAIN_SNOWFLAKE_ADMIN_USERNAME).role is Role.ADMIN


def test_invalid_primary_identity_does_not_select_another_identity():
    profile=SimpleNamespace(user={'user_name':'USER A'},experimental_user={'user_name':MAIN_SNOWFLAKE_ADMIN_USERNAME})
    assert resolve_snowflake_username(profile) is None


def test_admin_user_management_username_create_edit_and_list(monkeypatch):
    directory=Directory();store=fake_runtime(monkeypatch,directory,MAIN_SNOWFLAKE_ADMIN_USERNAME)
    app=AppTest.from_file(ROOT/'app/pages/15_User_Management.py',default_timeout=20)
    app.session_state['_base_repo']=MockRepository();app.session_state['_snowflake_auth_store']=store
    app.run()
    assert not app.exception
    next(field for field in app.text_input if field.label=='Internal email address').input('user_a@nsegg.ca')
    next(field for field in app.text_input if field.label=='Display name').input('USER_A')
    app.text_input(key='user_create_snowflake_username').input(' user_a ')
    next(field for field in app.selectbox if field.label=='Role').select(Role.DATA_EDITOR.value)
    next(button for button in app.button if button.label=='Add user').click().run()
    assert not app.exception and not app.error and len(directory.users)==1
    assert directory.users[0]['SNOWFLAKE_USERNAME']=='USER_A'
    assert 'SNOWFLAKE_USERNAME' in app.dataframe[0].value.columns
    identity=directory.users[0]['USER_ID']
    app.text_input(key='user_mapping_'+identity).input('USER_B')
    next(button for button in app.button if button.label=='Save access settings').click().run()
    assert not app.exception and not app.error
    assert directory.users[0]['SNOWFLAKE_USERNAME']=='USER_B'


def test_revoked_mapping_removes_previously_rendered_business_navigation(monkeypatch):
    directory=Directory([entry(role=Role.ADMIN)]);store=fake_runtime(monkeypatch,directory)
    app=AppTest.from_file(ROOT/'streamlit_app.py',default_timeout=20)
    app.session_state['_base_repo']=MockRepository();app.session_state['_snowflake_auth_store']=store
    app.run()
    assert not app.exception and app.dataframe
    directory.users[0]['ACTIVE']=False
    app.run()
    assert not app.exception and [message.value for message in app.error]==[DENIED]
    assert not app.dataframe and not app.get('page_link') and not app.get('download_button')
    assert not any(expander.label=='Sign-in diagnostics' for expander in app.expander)


@pytest.mark.parametrize('principal',['efnsdatabase','EfnsDatabase',' EFNSDATABASE','EFNSDATABASE '])
def test_case_sensitive_main_lookalike_never_gets_implicit_admin(principal):
    profile=SimpleNamespace(user={'user_name':principal})
    assert resolve_snowflake_username(profile) is None
    directory=Directory()
    assert SnowflakeAuthStore(directory).resolve_identity(principal) is None
    assert not directory.calls


def test_revocation_between_entrypoint_and_page_guard_still_denies_cleanly(monkeypatch):
    class ChangingDirectory(Directory):
        remaining=None
        def query(self,sql,params=None):
            if 'UPPER(TRIM(SNOWFLAKE_USERNAME))' in sql and self.remaining is not None:
                self.remaining-=1
                if self.remaining<0:self.users[0]['ACTIVE']=False
            return super().query(sql,params)
    directory=ChangingDirectory([entry(role=Role.ADMIN)])
    store=fake_runtime(monkeypatch,directory)
    app=AppTest.from_file(ROOT/'streamlit_app.py',default_timeout=20)
    app.session_state['_base_repo']=MockRepository();app.session_state['_snowflake_auth_store']=store
    app.run()
    directory.remaining=1
    app.switch_page('app/pages/2_Production_Data.py').run()
    assert not app.exception and [message.value for message in app.error]==[DENIED]
    assert not app.dataframe and not app.get('page_link') and not app.get('download_button')
