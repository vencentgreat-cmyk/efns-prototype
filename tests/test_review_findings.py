"""Report 8f3733e scenarios reconstructed from its text; all data synthetic.

The separately referenced external repro .py was not supplied/found. These
assert correct behavior and were run first against the frozen faulty baseline.
"""
import datetime as dt
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
import pytest
from tests.test_staff_workflows import chain
from tests.auth_support import authenticated_app
from tests.test_report_center import user
from tests.test_operational_flock_quota_import import csv_upload
from app.services.authorized_repository import AuthorizedRepository
from app.services.report_center import build_custom_report
from app.security import Role
from data.repositories.base import RepositoryError,ConcurrencyError
from data.repositories.snowflake import normalize_timestamp_bind
from data.operational_flock_quota_import import analyze_operational_files

ROOT=Path(__file__).resolve().parents[1]

def editing(r,page,scope,key,record_id,tmp_path,monkeypatch):
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=r
    app.session_state[f'_efns_record_{scope}_view']='edit'
    app.session_state[f'_efns_record_{scope}_id']=record_id
    app.switch_page('app/pages/'+page).run()
    assert not app.exception
    return app

def test_D1_flock_notes_preserve_legacy_fields(chain,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    r._flocks=r._flocks.astype(object)
    for field,value in dict(HATCH_DATE=None,EGG_COLOUR=None,STATUS='Inactive',FLOCK_QUOTA_TYPE=None).items():r._flocks.loc[r._flocks.FLOCK_ID==fid,field]=value
    r._quota_registrations.loc[r._quota_registrations.QUOTA_ID==q,'STATUS']='Inactive'
    before=r.get_flock(fid)
    app=editing(r,'5_Flocks.py','5_Flocks','flock',fid,tmp_path,monkeypatch)
    app.text_area(key='flock_form_comments').input('Synthetic note only')
    app.text_input(key='flock_form_revision_reason').input('Synthetic note correction')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    after=r.get_flock(fid)
    for field in ('HATCH_DATE','EGG_COLOUR','STATUS','FLOCK_QUOTA_TYPE','QUOTA_ID'):
        assert (pd.isna(before[field]) and pd.isna(after[field])) or after[field]==before[field],field

@pytest.mark.parametrize('quantity',[None,0,Decimal('2.5')])
def test_D1_transaction_notes_preserve_legacy_quantity(chain,quantity,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    tid='synthetic-legacy-transaction'
    r._flock_transactions=pd.DataFrame([dict(FLOCK_TRANSACTION_ID=tid,FLOCK_ID=fid,TRANSACTION_TYPE='Removal',QUANTITY=quantity,TRANSACTION_DATE=dt.date(2019,1,1),NOTES=None,CREATED_AT=dt.datetime(2020,1,1),UPDATED_AT=dt.datetime(2020,1,1))])
    app=editing(r,'6_Flock_Transactions.py','6_Flock_Transactions','flock_tx',tid,tmp_path,monkeypatch)
    app.text_area(key='flock_tx_form_notes').input('Synthetic note only')
    if any(x.key=='flock_tx_form_revision_reason' for x in app.text_input):app.text_input(key='flock_tx_form_revision_reason').input('Synthetic note correction')
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error
    value=r.get_flock_transactions().set_index('FLOCK_TRANSACTION_ID').loc[tid,'QUANTITY']
    assert pd.isna(value) if quantity is None else Decimal(str(value))==quantity

def test_D2_salmonella_notes_preserve_event_identity_and_history(chain,tmp_path,monkeypatch):
    r,a,o,f,q,fid,_=chain
    original_permit=r.get_flock(fid)['PERMIT_NUMBER']
    tid=r.upsert_salmonella_test(dict(FLOCK_ID=fid,ACCOUNT_ID=a,PERMIT_NUMBER=original_permit,TESTING_DATE=dt.date(2020,1,1),NUMBER_OF_SAMPLES=1,TEST_RESULT='Pending'))
    r._salmonella_tests.loc[r._salmonella_tests.SALMONELLA_TEST_ID==tid,'TEST_RESULT']='Not Tested'
    r._flocks.loc[r._flocks.FLOCK_ID==fid,'PERMIT_NUMBER']='NEW-PERMIT'
    app=editing(r,'9_Salmonella_Tests.py','9_Salmonella_Tests','salmonella',tid,tmp_path,monkeypatch)
    app.text_area(key='salmonella_form_comments').input('Synthetic note only')
    if any(x.key=='salmonella_form_revision_reason' for x in app.text_input):app.text_input(key='salmonella_form_revision_reason').input('Keep historical attribution')
    app.button(key='salmonella_record_save').click().run()
    assert not app.exception and not app.error
    after=r.get_salmonella_test(tid)
    assert after['PERMIT_NUMBER']==original_permit and after['TEST_RESULT']=='Not Tested'
    history=r.get_record_revisions()
    assert len(history)==1 and history.iloc[0].BEFORE_DATA['PERMIT_NUMBER']==original_permit

def test_D3_manual_production_reused_request_must_compare_content(chain):
    r,a,*_=chain
    p=dict(PRODUCER_ACCOUNT_ID=a,REPORTING_YEAR=2026,REPORTING_WEEK=40,TOTAL=Decimal(100))
    result=r.create_manual_production(p,'same-production-request','synthetic')
    assert r.create_manual_production(p,'same-production-request','synthetic')==result
    with pytest.raises(RepositoryError,match='different|already|request'):
        r.create_manual_production(dict(p,REPORTING_WEEK=41,TOTAL=250),'same-production-request','synthetic')

def test_D4_attribute_reused_request_must_compare_content(chain):
    r,a,o,f,q,fid,_=chain
    old=r.get_flock(fid)['UPDATED_AT']
    r.revise_record('FLOCK',fid,{'COMMENTS':'first'},'Synthetic correction','same-revision','synthetic',expected_updated_at=old)
    assert r.revise_record('FLOCK',fid,{'COMMENTS':'first'},'Synthetic correction','same-revision','synthetic',expected_updated_at=old)==fid
    with pytest.raises(RepositoryError,match='different|already|request'):
        r.revise_record('FLOCK',fid,{'COMMENTS':'second'},'Synthetic correction','same-revision','synthetic',expected_updated_at=old)

def daily(r,rows,selection):
    return analyze_operational_files([csv_upload('synthetic.csv',rows)],selection,r)

def test_D5_daily_update_preserves_unknown_values(chain):
    r,a,o,f,q,fid,_=chain
    r._flocks=r._flocks.astype(object)
    r._flocks.loc[r._flocks.FLOCK_ID==fid,['STATUS','BIRDS_DISPOSED']]=None
    report=daily(r,[dict(Action='UPDATE',FLOCK_ID=fid,Comments='Synthetic note')],'Flocks')
    assert len(report.ready_rows)==1
    record=report.ready_rows[0].write_record
    assert pd.isna(record['STATUS']) and pd.isna(record['BIRDS_DISPOSED'])

def test_D6_daily_note_update_does_not_compare_cumulative_disposal_to_current_count(chain):
    r,a,o,f,q,fid,_=chain
    r._flocks.loc[r._flocks.FLOCK_ID==fid,['BIRD_COUNT','BIRDS_DISPOSED']]=[0,120]
    report=daily(r,[dict(Action='UPDATE',FLOCK_ID=fid,Comments='Synthetic note')],'Flocks')
    assert len(report.ready_rows)==1

@pytest.mark.parametrize('kind,quantity',[('Removal',0),('Removal',Decimal('2.5')),('Mortality',1)])
def test_D7_daily_transactions_use_entry_validation(chain,kind,quantity):
    r,a,o,f,q,fid,_=chain
    report=daily(r,[dict(Action='CREATE',FLOCK_ID=fid,FLOCK_TRANSACTION_ID='synthetic-transaction',TRANSACTION_TYPE=kind,QUANTITY=quantity,TRANSACTION_DATE='2026-01-01')],'Flock Transactions')
    assert len(report.ready_rows)==0 and len(report.rows)==1 and report.rows[0].status=='Rejected'

def test_D8_committed_save_is_not_reported_as_failed_audit(chain):
    r,a,o,f,q,fid,_=chain
    class BrokenAudit:
        def record_action(self,*args,**kwargs):raise RuntimeError('Synthetic audit unavailable')
    proxy=AuthorizedRepository(r,BrokenAudit(),user(Role.ADMIN))
    result=proxy.upsert_flock_transaction(dict(FLOCK_ID=fid,TRANSACTION_TYPE='Delivery',QUANTITY=2,TRANSACTION_DATE=dt.date.today()))
    assert result and proxy.last_audit_warning
    assert len(r.get_flock_transactions(fid))==1

def test_D10_account_with_production_cannot_be_deleted(chain):
    r,a,o,f,q,fid,_=chain
    r.create_manual_production(dict(PRODUCER_ACCOUNT_ID=a,REPORTING_YEAR=2026,REPORTING_WEEK=40,TOTAL=1),'production-reference','synthetic')
    for attr in ('_facilities','_flocks','_quota_registrations','_salmonella_tests','_farm_locations'):
        setattr(r,attr,getattr(r,attr).iloc[:0])
    with pytest.raises(RepositoryError,match='related|referenc|cannot'):
        r.delete_account(a)

@pytest.mark.parametrize('dataset,filters',[('Accounts',{'account_id':'not-found'}),('Facilities',{'facility_id':'not-found'}),('Quota Registrations',{'date_from':dt.date(2020,1,1)})])
def test_D11_nonempty_unsupported_filter_is_not_silently_dropped(chain,dataset,filters):
    r,*_=chain
    with pytest.raises(ValueError,match='filter|support'):
        build_custom_report(r,user=user(),dataset=dataset,selected_fields=[{'Accounts':'ACCOUNT_ID','Facilities':'FACILITY_ID','Quota Registrations':'QUOTA_ID'}[dataset]],filters=filters)

def test_U1_timestamp_binding_preserves_nanoseconds():
    expected=pd.Timestamp('2026-10-28T12:34:56.123456789')
    assert pd.Timestamp(normalize_timestamp_bind(expected))==expected
