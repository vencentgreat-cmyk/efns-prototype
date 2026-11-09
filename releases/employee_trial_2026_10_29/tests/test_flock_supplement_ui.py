"""Synthetic AppTest controls; not deployed-browser acceptance."""
from io import BytesIO
from pathlib import Path

from streamlit.testing.v1 import AppTest
import streamlit as st

from app.auth import SESSION_TOKEN_KEY
from tests.auth_support import authenticated_app
from tests.test_flock_transaction_supplement import repo,workbook,BINDING


def test_admin_preview_confirmation_and_commit_ui(repo,tmp_path,monkeypatch):
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local')
    monkeypatch.setenv('REPOSITORY_MODE','mock')
    home=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    upload=BytesIO(workbook());upload.name='synthetic.xlsx'
    monkeypatch.setattr(st,'file_uploader',lambda *args,**kwargs: upload)
    app=AppTest.from_string('''
from app.auth import require_authenticated,ensure_authorized_repository
from app.services.flock_supplement_workspace import render_flock_supplement
user=require_authenticated()
render_flock_supplement(ensure_authorized_repository(user),user)
''',default_timeout=20)
    app.session_state[SESSION_TOKEN_KEY]=home.session_state[SESSION_TOKEN_KEY]
    app.session_state['_base_repo']=repo
    app.run()
    assert not app.exception
    app.text_input(key='ft_supplement_original_batch').input(BINDING['original_batch_id'])
    app.text_input(key='ft_supplement_flock').input(BINDING['flock_id'])
    app.text_input(key='ft_supplement_anchor').input(BINDING['anchor_transaction_id'])
    app.text_area(key='ft_supplement_basis').input(BINDING['basis'])
    app.button(key='ft_supplement_preview').click().run()
    assert not app.exception
    assert app.session_state.ft_supplement_report['counts']['NEW']==12
    assert repo.get_source_files().empty and len(repo._flock_transactions)==1
    assert app.button(key='ft_supplement_commit').disabled
    token=app.session_state.ft_supplement_report['review_token']
    app.checkbox(key=f'ft_supplement_confirm_{token}').check().run()
    app.text_area(key='ft_supplement_basis').input('Changed after review').run()
    assert app.button(key='ft_supplement_commit').disabled
    app.text_area(key='ft_supplement_basis').input(BINDING['basis']).run()
    app.button(key='ft_supplement_commit').click().run()
    assert not app.exception and not app.error
    assert len(repo._flock_transactions)==13
    assert repo._supplement_audit[0]['ACTOR_EMAIL']=='test.admin@nsegg.ca'
    assert any('12 new; 1 existing matches; 0 updated' in message.value for message in app.success)
