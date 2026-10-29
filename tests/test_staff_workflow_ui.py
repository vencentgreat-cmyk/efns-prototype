"""Real local pages/controls on isolated Mock state; not company acceptance."""
from pathlib import Path
import pandas as pd
from app.security import Role
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain


def test_employee_pages_save_cancel_and_refresh(chain,tmp_path,monkeypatch):
    r,a,o,f,q,flock,record=chain
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local'); monkeypatch.setenv('REPOSITORY_MODE','mock')
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=r
    # Edit a Facility through its actual form, retaining its Account and history.
    app.session_state['_efns_record_11_Facilities_view']='edit'
    app.session_state['_efns_record_11_Facilities_id']=f
    app.switch_page('app/pages/11_Facilities.py').run()
    assert not app.exception
    app.text_input(key='facility_form_name').input('DEV_TEST edited barn')
    app.text_input(key='facility_form_revision_reason').input('Synthetic acceptance correction')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    assert r.get_facility(f)['FACILITY_NAME']=='DEV_TEST edited barn'
    assert r.get_facility(f)['ACCOUNT_ID']==a
    assert len(r.get_record_revisions())==1
    app.session_state['_efns_record_5_Flocks_view']='edit'
    app.session_state['_efns_record_5_Flocks_id']=flock
    app.switch_page('app/pages/5_Flocks.py').run()
    assert not app.exception
    app.text_input(key='flock_form_number').input('DEV_TEST edited flock')
    app.text_input(key='flock_form_revision_reason').input('Synthetic name correction')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    assert r.get_flock(flock)['FLOCK_NUMBER']=='DEV_TEST edited flock'
    # A real supported Count entry does not masquerade as inventory mutation.
    app.session_state['_efns_record_6_Flock_Transactions_view']='new'
    app.switch_page('app/pages/6_Flock_Transactions.py').run()
    assert not app.exception
    app.number_input(key='flock_tx_form_quantity').set_value(9)
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert len(r.get_flock_transactions(flock_id=flock))==1
    assert r.get_flock(flock)['BIRD_COUNT']==10
    app.run()
    assert len(r.get_flock_transactions(flock_id=flock))==1
    # Cancel a second entry; do not call the repository writer.
    app.session_state['_efns_record_6_Flock_Transactions_view']='new'
    app.session_state['_efns_record_6_Flock_Transactions_id']=None
    app.switch_page('app/pages/6_Flock_Transactions.py').run()
    app.number_input(key='flock_tx_form_quantity').set_value(100)
    app.button(key='flock_tx_record_cancel').click().run()
    assert not app.exception
    assert len(r.get_flock_transactions(flock_id=flock))==1
    app.session_state['_efns_record_6_Flock_Transactions_view']='new'
    app.session_state['_efns_record_6_Flock_Transactions_id']=None
    app.switch_page('app/pages/6_Flock_Transactions.py').run()
    app.selectbox(key='flock_tx_form_type').select('Removal').run()
    app.number_input(key='flock_tx_form_quantity').set_value(3)
    app.checkbox(key='flock_tx_form_apply_'+flock).check()
    app.text_input(key='flock_tx_form_quantity_reason').input('Synthetic partial disposal; current quantity checked')
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert r.get_flock(flock)['BIRD_COUNT']==7
    # Flock re-read shows the newly added, deliberately guarded usage panel.
    app.session_state['_efns_record_5_Flocks_view']='detail'
    app.session_state['_efns_record_5_Flocks_id']=flock
    app.switch_page('app/pages/5_Flocks.py').run()
    assert not app.exception and not app.error
    assert any(m.label=='Account usage' and m.value=='Cannot calculate' for m in app.metric)
    assert any(m.label=='Known Bird Count' and m.value=='7' for m in app.metric)
    assert any('Account-wide' in c.value for c in app.caption)
    # Salmonella actual page rejects missing required sample count, then saves.
    app.session_state['_efns_record_9_Salmonella_Tests_view']='new'
    app.switch_page('app/pages/9_Salmonella_Tests.py').run()
    app.button(key='salmonella_record_save').click().run()
    assert app.error and len(r.get_salmonella_tests(flock_id=flock))==0
    app.number_input(key='salmonella_form_samples').set_value(1)
    app.button(key='salmonella_record_save').click().run()
    assert not app.exception and not app.error
    assert len(r.get_salmonella_tests(flock_id=flock))==1
    app.switch_page('app/pages/9_Salmonella_Tests.py').run()
    app.button(key='salmonella_record_edit').click().run()
    app.selectbox(key='salmonella_form_result').select('Negative')
    app.text_input(key='salmonella_form_revision_reason').input('Synthetic result correction evidence')
    app.button(key='salmonella_record_save').click().run()
    assert not app.exception and not app.error
    assert r.get_salmonella_tests(flock_id=flock).iloc[0].TEST_RESULT=='Negative'
    app.session_state['_efns_record_8_Quota_Transactions_view']='new'
    app.switch_page('app/pages/8_Quota_Transactions.py').run()
    assert not app.exception
    app.number_input(key='quota_tx_form_count').set_value(2)
    selected=next(v for v in app.selectbox(key='quota_tx_form_related_account').options if 'counterparty' in v)
    app.selectbox(key='quota_tx_form_related_account').select(selected)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert len(r.get_quota_transactions(quota_id=q))==1
    # Report Center is still reachable with exact same registered navigation.
    app.switch_page('app/pages/4_Reports.py').run()
    assert not app.exception


def test_reporting_viewer_cannot_open_a_new_transaction(tmp_path,monkeypatch):
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local');monkeypatch.setenv('REPOSITORY_MODE','mock')
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch,Role.REPORTING_VIEWER)
    app.session_state['_efns_record_6_Flock_Transactions_view']='new'
    app.switch_page('app/pages/6_Flock_Transactions.py').run()
    assert not app.exception
    assert app.button(key='flock_tx_record_save').disabled
