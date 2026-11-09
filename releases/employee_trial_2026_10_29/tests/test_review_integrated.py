"""Expected-behavior regressions across real local pages and transaction doubles."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import datetime as dt
from decimal import Decimal
from types import SimpleNamespace
import pandas as pd
import pytest
from tests.test_staff_workflows import chain
from tests.test_account_usage_quantity import ACTOR
from tests.test_review_findings import editing,daily
from tests.auth_support import authenticated_app
from tests.test_report_center import user
from tests.test_continuity import workbook
from app.services.authorized_repository import AuthorizedRepository
from app.security import Role
from data.business_time import halifax_today
from data.repositories.base import RepositoryError,ConcurrencyError
from data.repositories.snowflake import MODEL

ROOT=Path(__file__).resolve().parents[1]

def new_transaction_page(r,tmp_path,monkeypatch):
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=r
    app.session_state['_efns_record_6_Flock_Transactions_view']='new'
    app.switch_page('app/pages/6_Flock_Transactions.py').run()
    assert not app.exception
    return app

def test_D9_reload_requires_actual_new_confirmation_and_preserves_draft(chain,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    app=new_transaction_page(r,tmp_path,monkeypatch)
    version=r.get_flock(fid)['UPDATED_AT']
    r._flocks.loc[r._flocks.FLOCK_ID==fid,'BIRD_COUNT']=15
    r._flocks.loc[r._flocks.FLOCK_ID==fid,'UPDATED_AT']=pd.Timestamp(version)+pd.Timedelta(seconds=1)
    app.number_input(key='flock_tx_form_quantity').set_value(0)
    app.checkbox(key='flock_tx_form_apply_'+fid).check()
    app.text_input(key='flock_tx_form_quantity_reason').input('Synthetic current observation')
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and app.warning and r._flock_transactions.empty
    assert app.session_state['flock_tx_form_quantity_review_'+fid]['BIRD_COUNT']==10
    app.button(key='flock_tx_form_reload_quantity').click().run()
    assert not app.exception
    assert app.session_state['flock_tx_form_quantity_review_'+fid]['BIRD_COUNT']==15
    assert app.number_input(key='flock_tx_form_quantity').value==0
    assert not app.checkbox(key='flock_tx_form_apply_'+fid).value
    app.checkbox(key='flock_tx_form_apply_'+fid).check()
    assert app.text_input(key='flock_tx_form_quantity_reason').value
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error, [x.value for x in app.error]
    assert r.get_flock(fid)['BIRD_COUNT']==0 and len(r._flock_transactions)==1

def test_U2_changed_count_is_rejected_even_with_identical_version(chain):
    r,a,o,f,q,fid,_=chain
    version=r.get_flock(fid)['UPDATED_AT']
    r._flocks.loc[r._flocks.FLOCK_ID==fid,'BIRD_COUNT']=15
    with pytest.raises(ConcurrencyError,match='Bird Count changed'):
        r.record_current_flock_quantity(dict(FLOCK_ID=fid,TRANSACTION_TYPE='Count',QUANTITY=12,TRANSACTION_DATE=halifax_today()),'new-request',version,'Synthetic',confirmed=True,actor=ACTOR,expected_bird_count=10)
    assert r._flock_transactions.empty and r.get_record_revisions().empty

@pytest.mark.parametrize('instant,day',[
 ('2026-10-29T01:30:00Z',dt.date(2026,10,28)),
 ('2026-06-18T02:00:00Z',dt.date(2026,6,17)),
 ('2027-01-01T02:30:00Z',dt.date(2026,12,31)),
 ('2026-10-29T14:30:00Z',dt.date(2026,10,29)),
])
def test_U3_business_day_does_not_use_host_utc_date(instant,day):
    assert halifax_today(pd.Timestamp(instant))==day

def test_D3_manual_page_continuous_second_entry_and_same_payload_retry(chain,tmp_path,monkeypatch):
    r,a,*_=chain
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=r
    app.switch_page('app/pages/21_Record_History.py').run()
    choices=app.selectbox(key='manual_producer').options
    app.selectbox(key='manual_producer').select(next(x for x in choices if a in x))
    next(x for x in app.number_input if x.label=='Reporting week').set_value(40)
    next(x for x in app.text_input if x.label=='Source Total').input('100')
    next(x for x in app.button if x.label=='Save new production record').click().run()
    assert not app.exception and not app.error and len(r._production)==1
    next(x for x in app.button if x.label=='Save new production record').click().run()
    assert len(r._production)==1
    next(x for x in app.number_input if x.label=='Reporting week').set_value(41)
    next(x for x in app.text_input if x.label=='Source Total').input('250')
    next(x for x in app.button if x.label=='Save new production record').click().run()
    assert not app.exception and not app.error
    assert sorted(r._production.TOTAL.tolist())==[100,250]
    assert len(r.get_production_match_decisions())==2

def test_D4_attribute_page_two_corrections_get_distinct_requests(chain,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=r
    app.switch_page('app/pages/21_Record_History.py').run()
    next(x for x in app.selectbox if x.label=='Attribute').select('COMMENTS')
    next(x for x in app.text_input if x.label=='Corrected value').input('first')
    app.text_area(key='revision_reason').input('Synthetic correction evidence')
    next(x for x in app.button if x.label=='Save attribute correction').click().run()
    assert not app.exception and not app.error
    next(x for x in app.text_input if x.label=='Corrected value').input('second')
    next(x for x in app.button if x.label=='Save attribute correction').click().run()
    assert not app.exception and not app.error
    assert r.get_flock(fid)['COMMENTS']=='second'
    assert len(r.get_record_revisions())==2

@pytest.mark.parametrize('entity',list(('ACCOUNT','FACILITY','FARM_LOCATION','FACILITY_DETAIL','FLOCK','FLOCK_TRANSACTION','QUOTA_REGISTRATION','QUOTA_TRANSACTION','SALMONELLA_TEST')))
def test_U4_all_form_create_apis_are_replay_safe_and_reject_changed_payload(chain,entity):
    r,a,o,f,q,fid,flock=chain
    rows={
      'ACCOUNT':dict(ORGANIZATION_NAME='Synthetic new account',REGISTRATION_NUMBER='003',STATUS='Active'),
      'FACILITY':dict(ACCOUNT_ID=a,FACILITY_NAME='Synthetic new barn',FACILITY_TYPE='Layer',STATUS='Active'),
      'FARM_LOCATION':dict(ACCOUNT_ID=a,LOCATION_NAME='Synthetic new location',STATUS='Active'),
      'FACILITY_DETAIL':dict(FACILITY_ID=f,DETAIL_NAME='Synthetic detail',STATUS='Active'),
      'FLOCK':dict(flock,FLOCK_NUMBER='Synthetic new flock',PERMIT_NUMBER='NEW-SYNTHETIC'),
      'FLOCK_TRANSACTION':dict(FLOCK_ID=fid,TRANSACTION_TYPE='Delivery',QUANTITY=2,TRANSACTION_DATE=halifax_today()),
      'QUOTA_REGISTRATION':dict(ACCOUNT_ID=a,REGISTRATION_NUMBER='NEW-QUOTA',QUOTA_NAME='Synthetic new quota',QUOTA_TYPE='Egg Production',STATUS='Active'),
      'QUOTA_TRANSACTION':dict(QUOTA_ID=q,TRANSACTION_TYPE='Purchase',QUOTA_COUNT=1,RELATED_ACCOUNT_ID=o,EFFECTIVE_DATE=halifax_today()),
      'SALMONELLA_TEST':dict(FLOCK_ID=fid,ACCOUNT_ID=a,PERMIT_NUMBER=r.get_flock(fid)['PERMIT_NUMBER'],TESTING_DATE=halifax_today(),NUMBER_OF_SAMPLES=1,TEST_RESULT='Pending'),
    }
    proxy=AuthorizedRepository(r,SimpleNamespace(),user(Role.ADMIN))
    data=rows[entity];result=proxy.create_record_once(entity,data,'same-create-request')
    assert proxy.create_record_once(entity,data,'same-create-request')==result
    assert len(r.get_record_revisions())==1 and len(r._migration_review_audit)==1
    changed=dict(data);field=next(iter(changed));changed[field]='different'
    with pytest.raises(RepositoryError,match='different'):
        proxy.create_record_once(entity,changed,'same-create-request')
    assert len(r.get_record_revisions())==1 and len(r._migration_review_audit)==1

def test_U4_navigation_failure_does_not_resubmit_new_activity(chain,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    app=new_transaction_page(r,tmp_path,monkeypatch)
    app.selectbox(key='flock_tx_form_type').select('Delivery')
    app.number_input(key='flock_tx_form_quantity').set_value(2)
    import app.navigation as navigation
    real=navigation.open_view
    monkeypatch.setattr(navigation,'open_view',lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('Synthetic navigation interruption')))
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and app.success and app.warning
    assert len(r._flock_transactions)==1
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and len(r._flock_transactions)==1
    assert len(r.get_record_revisions())==len(r._migration_review_audit)==1

def test_D8_mandatory_audit_failure_rolls_back_record_and_revision(chain,monkeypatch):
    r,a,o,f,q,fid,_=chain
    before=r._flock_transactions.copy(deep=True)
    monkeypatch.setattr(r,'_review_insert',lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('Synthetic mandatory audit unavailable')))
    with pytest.raises(RuntimeError):
        r.create_record_once('FLOCK_TRANSACTION',dict(FLOCK_ID=fid,TRANSACTION_TYPE='Delivery',QUANTITY=2,TRANSACTION_DATE=halifax_today()),'fail-create',ACTOR)
    pd.testing.assert_frame_equal(before,r._flock_transactions)
    assert r.get_record_revisions().empty and not r._migration_review_audit

def test_D12_delete_retains_before_image_and_audit_atomically(chain,monkeypatch):
    r,a,o,f,q,fid,_=chain
    tid=r.upsert_flock_transaction(dict(FLOCK_ID=fid,TRANSACTION_TYPE='Delivery',QUANTITY=2,TRANSACTION_DATE=halifax_today()))
    proxy=AuthorizedRepository(r,SimpleNamespace(record_action=lambda *a:None),user(Role.ADMIN))
    assert proxy.delete_flock_transaction(tid,reason='Synthetic confirmed deletion',request_id='delete-once')
    history=r.get_record_revisions()
    assert len(history)==1 and history.iloc[0].BEFORE_DATA['FLOCK_TRANSACTION_ID']==tid
    assert history.iloc[0].AFTER_DATA is None and len(r._migration_review_audit)==1
    assert not proxy.delete_flock_transaction(tid,reason='Synthetic confirmed deletion',request_id='delete-once')
    assert len(r.get_record_revisions())==1

def test_D12_quantity_protected_delete_has_confirmation_and_friendly_error(chain,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    tid=r.record_current_flock_quantity(dict(FLOCK_ID=fid,TRANSACTION_TYPE='Count',QUANTITY=3,TRANSACTION_DATE=halifax_today()),'count-entry',r.get_flock(fid)['UPDATED_AT'],'Synthetic',confirmed=True,actor=ACTOR,expected_bird_count=10)
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=r
    app.session_state['_efns_record_6_Flock_Transactions_view']='detail'
    app.session_state['_efns_record_6_Flock_Transactions_id']=tid
    app.switch_page('app/pages/6_Flock_Transactions.py').run()
    app.button(key='flock_tx_record_delete').click().run()
    assert not app.exception and len(r._flock_transactions)==1
    app.text_input(key='flock_tx_form___delete_reason').input('Synthetic delete request')
    app.checkbox(key='flock_tx_form___delete_confirmed').check().run()
    app.button(key='flock_tx_form___delete_confirm').click().run()
    assert not app.exception and (app.warning or app.error)
    assert len(r._flock_transactions)==1 and r.get_flock(fid)['BIRD_COUNT']==3

def test_U6_matching_changes_after_preview_block_commit_until_explicit_review(chain):
    r,a,o,f,q,fid,_=chain
    from data.importing import read_eims_workbook
    from data.production_intake import prepare_workbook
    content=workbook()
    archive=r.archive_source_file('synthetic.xlsx',content,'PRODUCTION_WORKBOOK','synthetic')
    raw=read_eims_workbook(BytesIO(content))
    _,rows,_,_=prepare_workbook(raw,archive['SOURCE_FILE_ID'],r.get_accounts())
    batch=dict(SOURCE_FILE_ID=archive['SOURCE_FILE_ID'],FILE_HASH=archive['FILE_HASH'],SOURCE_RECORD_COUNT=len(rows))
    bid=r.stage_production_upload(batch,rows)
    before=deepcopy(r._raw_rows)
    r._accounts.loc[r._accounts.ACCOUNT_ID==a,'REGISTRATION_NUMBER']='source-key-changed'
    with pytest.raises(ConcurrencyError,match='matching|preview'):
        r.commit_staged_production(bid,'synthetic',new_observations_confirmed=True)
    assert r._production.empty and r._raw_rows==before
    _,reviewed,_,_=prepare_workbook(raw,archive['SOURCE_FILE_ID'],r.get_accounts())
    assert r.stage_production_upload(batch,reviewed,actor='synthetic',review_again=True)==bid
    result=r.commit_staged_production(bid,'synthetic',new_observations_confirmed=True)
    assert result[1]>=0 and r._raw_rows==before
