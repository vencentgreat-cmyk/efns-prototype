"""Synthetic AppTest, not a company browser or DEV write test."""
from io import BytesIO
from pathlib import Path
import streamlit as st
from streamlit.testing.v1 import AppTest
from app.auth import SESSION_TOKEN_KEY
from tests.auth_support import authenticated_app
from tests.test_flock_date_repair import repo,BATCH,BASIS


def test_preview_confirmation_and_commit_are_separate(repo,tmp_path,monkeypatch):
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local');monkeypatch.setenv('REPOSITORY_MODE','mock')
    home=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    upload=BytesIO(b'FLOCK_ID,REASON\n');upload.name='synthetic-empty-reviewed-exclusions.csv'
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:upload)
    app=AppTest.from_string('''
from app.auth import require_authenticated,ensure_authorized_repository
from app.services.flock_date_repair_workspace import render_flock_date_repair
user=require_authenticated()
render_flock_date_repair(ensure_authorized_repository(user),user)
''',default_timeout=20)
    app.session_state[SESSION_TOKEN_KEY]=home.session_state[SESSION_TOKEN_KEY];app.session_state['_base_repo']=repo
    app.run();assert not app.exception
    app.button(key='date_repair_runtime').click().run()
    assert not app.exception and not app.error
    assert app.session_state.date_repair_runtime_report['runtime']=='Mock'
    assert not app.session_state.date_repair_runtime_report['verified']
    app.text_input(key='date_repair_batch').input(BATCH)
    app.text_area(key='date_repair_basis').input(BASIS)
    app.button(key='date_repair_preview').click().run();assert not app.exception
    assert app.session_state.date_repair_report['counts']['READY']==2
    assert not repo._continuity_rows['RECORD_REVISION']
    assert app.button(key='date_repair_commit').disabled
    token=app.session_state.date_repair_report['review_token']
    app.checkbox(key='date_repair_confirm_'+token).check().run()
    app.text_area(key='date_repair_basis').input('Changed evidence').run()
    assert app.button(key='date_repair_commit').disabled
    app.text_area(key='date_repair_basis').input(BASIS).run()
    app.button(key='date_repair_commit').click().run()
    assert not app.exception and not app.error
    progress=app.get('progress')[0].proto
    assert progress.value==100 and 'Commit confirmed: 2' in progress.text
    assert 'committed: 2' in app.success[0].value
    assert len(repo._continuity_rows['RECORD_REVISION'])==2
    assert repo._migration_review_audit[0]['ACTOR_EMAIL']=='test.admin@nsegg.ca'
