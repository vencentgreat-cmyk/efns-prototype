"""New synthetic acceptance scenarios; never connects to company Snowflake."""
import datetime as dt
from io import BytesIO
from copy import deepcopy
import pandas as pd
import pytest

from app.security import Role
from app.services.authorized_repository import AuthorizedRepository
from app.services.report_center import build_custom_report, report_csv, report_xlsx
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import RepositoryError, ConcurrencyError
from tests.test_report_center import user
from tests.test_continuity import workbook
from data.importing import read_eims_workbook
from data.production_intake import prepare_workbook


@pytest.fixture
def chain():
    r=MockRepository()
    for attr in ('_accounts','_facilities','_flocks','_flock_transactions','_quota_registrations','_quota_transactions','_salmonella_tests','_production'):
        setattr(r,attr,getattr(r,attr).iloc[:0].copy())
    a=r.upsert_account(dict(ORGANIZATION_NAME='DEV_TEST staff producer',REGISTRATION_NUMBER='001',STATUS='Active'))
    other=r.upsert_account(dict(ORGANIZATION_NAME='DEV_TEST counterparty',REGISTRATION_NUMBER='002',STATUS='Active'))
    f=r.upsert_facility(dict(ACCOUNT_ID=a,FACILITY_NAME='DEV_TEST barn',FACILITY_TYPE='Layer',STATUS='Active'))
    q=r.upsert_quota_registration(dict(ACCOUNT_ID=a,REGISTRATION_NUMBER='DEV_TEST quota',QUOTA_NAME='DEV_TEST register',QUOTA_TYPE='Egg Production',STATUS='Active',EFFECTIVE_DATE=dt.date(2020,1,1),END_DATE=None))
    record=dict(ACCOUNT_ID=a,FACILITY_ID=f,QUOTA_ID=q,FLOCK_QUOTA_TYPE='Egg Production',FLOCK_NUMBER='DEV_TEST flock',PERMIT_NUMBER='DEV_TEST permit',HATCH_DATE=dt.date(2026,1,1),BIRD_COUNT=10,STATUS='Active',EGG_COLOUR='White')
    flock=r.upsert_flock(record)
    return r,a,other,f,q,flock,record


@pytest.mark.parametrize('problem',['parent','type','quantity'])
def test_snowflake_transaction_rejects_before_writer(problem):
    r=SnowflakeRepository(); calls=[]
    r.get_flock=lambda fid: None if problem=='parent' else {'FLOCK_ID':fid}
    r._upsert=lambda *args: calls.append(args) or 'unsafe'
    record=dict(FLOCK_ID='synthetic',TRANSACTION_TYPE='bad' if problem=='type' else 'Count',QUANTITY=float('nan') if problem=='quantity' else 10,TRANSACTION_DATE=dt.date(2026,1,1))
    with pytest.raises(RepositoryError): r.upsert_flock_transaction(record)
    assert not calls


def test_mock_transaction_requires_date(chain):
    r,a,o,f,q,flock,_=chain
    with pytest.raises((ValueError,RepositoryError)):
        r.upsert_flock_transaction(dict(FLOCK_ID=flock,TRANSACTION_TYPE='Count',QUANTITY=10,TRANSACTION_DATE=None))


def test_continuous_production_chain_matching_query_and_revision(chain):
    r,a,o,f,q,flock,_=chain
    pid=r.create_manual_production(dict(PRODUCER_ACCOUNT_ID=a,REPORTING_YEAR=2026,REPORTING_WEEK=15,TOTAL=600),'manual-1','staff')
    assert r.create_manual_production(dict(PRODUCER_ACCOUNT_ID=a,REPORTING_YEAR=2026,REPORTING_WEEK=15,TOTAL=600),'manual-1','staff')==pid
    current=r._production[r._production.PRODUCTION_ID==pid].iloc[0]
    r.revise_record('PRODUCTION_RECORD',pid,{'TOTAL':650},'Synthetic source correction','rev-1',actor='staff',expected_updated_at=current.UPDATED_AT)
    from data.constants import EIMS_REQUIRED_COLUMNS
    source=pd.DataFrame([{'Producer #':'001','Week':'1526','Total':400,'MarketingType':'DEV_TEST recorded category'},{'Producer #':None,'Week':'1526','Total':12}])
    for column in EIMS_REQUIRED_COLUMNS:
        if column not in source: source[column]=None
    buffer=BytesIO()
    with pd.ExcelWriter(buffer,engine='openpyxl') as writer:
        source.to_excel(writer,sheet_name='EIMS 3',startrow=9,index=False)
    original=buffer.getvalue()
    archive=r.archive_source_file('DEV_TEST production.xlsx',original,'PRODUCTION_WORKBOOK',actor='staff')
    frame=read_eims_workbook(BytesIO(original))
    accepted,rows,errors,_=prepare_workbook(frame,archive['SOURCE_FILE_ID'],r.get_accounts())
    assert len(rows)==2 and len(accepted)==1 and accepted.iloc[0].PRODUCER_ACCOUNT_ID==a
    assert accepted.iloc[0].MARKETING_TYPE=='DEV_TEST recorded category'
    batch=r.stage_production_upload(dict(SOURCE_FILE_ID=archive['SOURCE_FILE_ID'],FILE_HASH=archive['FILE_HASH']),rows)
    before=len(r._production)
    r.commit_staged_production(batch,'staff',new_observations_confirmed=True)
    r.commit_staged_production(batch,'staff',new_observations_confirmed=True)
    assert len(r._production)==before+1 and len(r.get_raw_rows(batch))==2
    result=build_custom_report(r,user=user(),dataset='Production Records',selected_fields=['PRODUCTION_ID','TOTAL'])
    assert sorted(result['Source Total'].tolist())==[400,650]
    assert r.get_source_file_bytes(archive['SOURCE_FILE_ID'])==original
    assert len(r.get_record_revisions())==1


def test_flock_transactions_are_activity_not_automatic_inventory(chain):
    r,a,o,f,q,flock,record=chain
    before=r.get_flock(flock)
    for kind,qty in [('Count',9),('Delivery',4),('Removal',2),('Sale',1)]:
        txid='DEV_TEST_'+kind
        transaction=dict(FLOCK_TRANSACTION_ID=txid,FLOCK_ID=flock,TRANSACTION_TYPE=kind,QUANTITY=qty,TRANSACTION_DATE=dt.date(2026,2,1))
        r.upsert_flock_transaction(transaction); r.upsert_flock_transaction(transaction)
    assert len(r.get_flock_transactions(flock_id=flock))==4
    assert r.get_flock(flock)['BIRD_COUNT']==before['BIRD_COUNT']==10
    assert r.get_flock(flock)['STATUS']==before['STATUS']
    r.upsert_flock(dict(record,FLOCK_NUMBER='DEV_TEST concurrent',PERMIT_NUMBER='DEV_TEST second'))
    assert len(r.get_flocks(facility_id=f))==2
    wrong=r.upsert_facility(dict(ACCOUNT_ID=o,FACILITY_NAME='DEV_TEST other barn',STATUS='Active'))
    with pytest.raises((ValueError,RepositoryError)):
        r.upsert_flock(dict(record,FACILITY_ID=wrong,FLOCK_NUMBER='DEV_TEST invalid'))


def test_quota_activity_and_salmonella_query_report(chain):
    r,a,o,f,q,flock,_=chain
    for kind in ('Purchase','Sale','Lease In','Lease Out'):
        r.upsert_quota_transaction(dict(QUOTA_TRANSACTION_ID='DEV_TEST_'+kind,QUOTA_ID=q,TRANSACTION_TYPE=kind,QUOTA_COUNT=2,RELATED_ACCOUNT_ID=o,EFFECTIVE_DATE=dt.date(2026,1,1),END_DATE=dt.date(2026,12,31)))
    assert len(r.get_quota_transactions(quota_id=q))==4
    assert r.get_quota_transactions(quota_id=q).OWNER_ACCOUNT_ID.eq(a).all()
    tid=r.upsert_salmonella_test(dict(FLOCK_ID=flock,ACCOUNT_ID=a,PERMIT_NUMBER='DEV_TEST permit',TESTING_DATE=dt.date(2026,3,1),NUMBER_OF_SAMPLES=1,TEST_RESULT='Pending'))
    old=r.get_salmonella_tests(flock_id=flock).iloc[0].to_dict()
    r.upsert_salmonella_test(dict(old,TEST_RESULT='Negative',EXPECTED_UPDATED_AT=old['UPDATED_AT']))
    result=build_custom_report(r,user=user(),dataset='Salmonella Tests',selected_fields=['SALMONELLA_TEST_ID','FLOCK_ID','TEST_RESULT'])
    assert len(result)==1 and result.iloc[0]['Result']=='Negative'
    assert b'Negative' in report_csv(user(),result)
    exported=pd.read_excel(BytesIO(report_xlsx(user(),result)))
    assert exported['Result'].tolist()==result['Result'].tolist()
    assert len(r.get_salmonella_tests(flock_id=flock))==1


def test_permissions_and_invalid_requiredness_do_not_write(chain):
    r,a,o,f,q,flock,record=chain
    class Audit:
        def record_action(self,*args,**kwargs): pass
    view=AuthorizedRepository(r,Audit(),user(Role.REPORTING_VIEWER))
    before=deepcopy(r._flock_transactions)
    with pytest.raises(RepositoryError,match='permission'):
        view.upsert_flock_transaction(dict(FLOCK_ID=flock,TRANSACTION_TYPE='Count',QUANTITY=1,TRANSACTION_DATE=dt.date.today()))
    pd.testing.assert_frame_equal(before,r._flock_transactions)
    with pytest.raises((ValueError,RepositoryError)):
        r.upsert_flock(dict(record,FLOCK_NUMBER=None))
    with pytest.raises(RepositoryError): r.create_manual_production({'TOTAL':600},'no-producer','staff')


@pytest.mark.parametrize('count',[float('nan'),float('inf'),-1,0,None,'bad'])
def test_daily_quota_count_invalid_values_are_rejected(chain,count):
    r,a,o,f,q,flock,record=chain
    with pytest.raises((ValueError,RepositoryError)):
        r.upsert_quota_transaction(dict(QUOTA_ID=q,TRANSACTION_TYPE='Purchase',QUOTA_COUNT=count,RELATED_ACCOUNT_ID=o,EFFECTIVE_DATE=dt.date(2026,1,1)))


def test_usage_fresh_shared_context_does_not_invent_a_formula(chain):
    from app.services.quota_usage import quota_usage_context
    r,a,o,f,q,flock,record=chain
    first=quota_usage_context(r,r.get_flock(flock))
    assert first['linked_flocks']==1 and first['transaction_count']==0
    r.upsert_flock(dict(record,FLOCK_NUMBER='DEV_TEST second',PERMIT_NUMBER='DEV_TEST second',BIRD_COUNT=0))
    for kind in ('Purchase','Sale'):
        r.upsert_quota_transaction(dict(QUOTA_ID=q,TRANSACTION_TYPE=kind,QUOTA_COUNT=100,RELATED_ACCOUNT_ID=o,EFFECTIVE_DATE=dt.date(2026,1,1)))
    after=quota_usage_context(r,r.get_flock(flock))
    assert after['linked_flocks']==2 and after['transaction_count']==2
    assert all(after[k] is None for k in ('applicable_quota','remaining_capacity','usage_percent'))
    assert after['current_occupancy'] is None
    assert sum(v['known_bird_count'] for v in after['summaries'])==10
    assert 'Account-wide' in after['scope']


@pytest.mark.parametrize('case',['unlinked','missing quota','different type','zero bird count','unknown bird count','large bird count'])
def test_usage_uncertain_and_zero_cases_never_divide_or_claim_overquota(chain,case):
    from app.services.quota_usage import quota_usage_context
    r,a,o,f,q,flock,record=chain
    source=r.get_flock(flock)
    if case=='unlinked': source['QUOTA_ID']=None
    if case=='missing quota': source['QUOTA_ID']='DEV_TEST absent'
    if case=='different type': source['FLOCK_QUOTA_TYPE']='Commercial Pullet'
    if case=='zero bird count': source['BIRD_COUNT']=0
    if case=='unknown bird count': source['BIRD_COUNT']=None
    if case=='large bird count': source['BIRD_COUNT']=999999
    actual=quota_usage_context(r,source)
    assert actual['usage_percent'] is None and actual['scope'].startswith('Account-wide')
    assert actual['recorded_bird_count']==source['BIRD_COUNT']
