"""Synthetic evidence only: identity, original bytes, retry and business history."""
import datetime as dt
from io import BytesIO

import pandas as pd
import pytest

from data.importing import read_eims_workbook
from data.producer_identity import production_identities, resolve_producer
from data.production_intake import prepare_workbook
from data.repositories.base import RepositoryError
from data.repositories.mock import MockRepository
from app.services.report_center import build_custom_report, report_csv, report_xlsx
from tests.test_report_center import user


@pytest.fixture
def repo():
    result = MockRepository()
    result._accounts = pd.DataFrame([
        dict(ACCOUNT_ID='a',REGISTRATION_NUMBER='001',ORGANIZATION_NAME='Synthetic A'),
        dict(ACCOUNT_ID='b',REGISTRATION_NUMBER='002',ORGANIZATION_NAME='Synthetic B'),
        dict(ACCOUNT_ID='c',REGISTRATION_NUMBER='002',ORGANIZATION_NAME='Synthetic C'),
    ])
    return result


@pytest.mark.parametrize('source,status,account', [('001','UNIQUE_MATCHED','a'),('002','MULTIPLE_CANDIDATES',None),('003','NO_CANDIDATE',None),(None,'MISSING_SOURCE_ID',None)])
def test_exact_resolution(repo,source,status,account):
    decision = resolve_producer({'PRODUCER_NUMBER':source},repo._accounts)
    assert decision['status'] == status and decision['account_id'] == account


def test_source_identities_do_not_merge():
    frame = pd.DataFrame([
        dict(PRODUCTION_ID=str(i),PRODUCER_ACCOUNT_ID=None,PRODUCER_NUMBER=n,IMPORT_ID=batch)
        for i,(n,batch) in enumerate([('001','one'),('002','one'),('001','two'),(None,'one'),(None,'one')])
    ])
    assert production_identities(frame).PRODUCER_IDENTITY_KEY.nunique() == 5


def workbook():
    buffer = BytesIO()
    frame = pd.DataFrame([{'Week':'202615','Producer #':'001','Total':0}, {'Week':'202615','Producer #':None,'Total':7}, {'Week':'202615','Producer #':'003','Total':-2}])
    from data.constants import EIMS_REQUIRED_COLUMNS
    for column in EIMS_REQUIRED_COLUMNS:
        if column not in frame: frame[column] = None
    for i in range(35-len(frame.columns)): frame[f'Unused {i}']=None
    with pd.ExcelWriter(buffer,engine='openpyxl') as writer:
        frame.to_excel(writer,sheet_name='EIMS 3',startrow=9,index=False)
    return buffer.getvalue()


def test_original_bytes_rows_validation_and_retry(repo):
    original = workbook()
    archive = repo.archive_source_file('synthetic.xlsm',original,'PRODUCTION_WORKBOOK',actor='test')
    assert repo.get_source_file_bytes(archive['SOURCE_FILE_ID']) == original
    assert repo.archive_source_file('synthetic.xlsm',original,'PRODUCTION_WORKBOOK')['SOURCE_FILE_ID'] == archive['SOURCE_FILE_ID']
    assert repo.archive_source_file('synthetic.xlsm',original+b'other','PRODUCTION_WORKBOOK')['SOURCE_FILE_ID'] != archive['SOURCE_FILE_ID']
    raw = read_eims_workbook(BytesIO(original))
    assert len(raw)==3 and list(raw.SOURCE_ROW_NUMBER)==[11,12,13]
    accepted,rows,errors,_ = prepare_workbook(raw,archive['SOURCE_FILE_ID'],repo._accounts)
    assert len(rows)==3 and len(accepted)==1 and accepted.iloc[0].TOTAL==0
    assert any('Producer # is missing' in error for error in errors)
    batch = dict(SOURCE_FILE_ID=archive['SOURCE_FILE_ID'],FILE_HASH=archive['FILE_HASH'],FILENAME='synthetic.xlsm')
    import_id=repo.stage_production_upload(batch,rows)
    before=len(repo._production)
    assert len(repo.get_raw_rows(import_id))==3 and len(repo._production)==before
    assert repo.commit_staged_production(import_id,'test',new_observations_confirmed=True) == (import_id,1)
    assert repo.commit_staged_production(import_id,'test') == (import_id,1)
    assert len(repo._production)==before+1
    match=repo.get_production_match_decisions().iloc[0]
    assert match.HANDLING=='AUTO'
    assert pd.isna(repo._production.iloc[-1].get('MATCH_CONFIRMED_AT'))


def test_failed_commit_keeps_original_raw(repo,monkeypatch):
    original=workbook()
    archive=repo.archive_source_file('x.xlsx',original,'PRODUCTION_WORKBOOK')
    _,rows,_,_=prepare_workbook(read_eims_workbook(BytesIO(original)),archive['SOURCE_FILE_ID'],repo._accounts)
    batch=repo.stage_production_upload(dict(SOURCE_FILE_ID=archive['SOURCE_FILE_ID'],FILE_HASH=archive['FILE_HASH']),rows)
    before=len(repo._production)
    def fail(*args): raise RuntimeError('synthetic write failure')
    monkeypatch.setattr(repo,'_append_match',fail)
    with pytest.raises(RuntimeError):repo.commit_staged_production(batch,'test',new_observations_confirmed=True)
    assert len(repo._production)==before and len(repo.get_raw_rows(batch))==3
    assert repo.find_import_by_hash(archive['FILE_HASH'])['STATUS']=='Staged'
    assert repo.get_source_file_bytes(archive['SOURCE_FILE_ID'])==original


def test_missing_manual_producer_and_later_match_without_double_count(repo):
    with pytest.raises(RepositoryError): repo.create_manual_production({'TOTAL':0},'request','staff')
    repo._production=pd.DataFrame([dict(PRODUCTION_ID='p',PRODUCER_ACCOUNT_ID=None,PRODUCER_NUMBER='001',TOTAL=-3,UPDATED_AT=dt.datetime.now(dt.timezone.utc))])
    result=repo.match_production_producer('p',actor='staff')
    assert result['account_id']=='a' and len(repo._production)==1 and repo._production.iloc[0].TOTAL==-3
    assert pd.isna(repo._production.iloc[0].MATCH_CONFIRMED_AT)
    with pytest.raises(RepositoryError):repo.match_production_producer('p',actor='staff')


def test_unidentified_groups_and_exports(repo):
    repo._production=pd.DataFrame([dict(PRODUCTION_ID=str(i),PRODUCER_ACCOUNT_ID=None,PRODUCER_NUMBER=n,IMPORT_ID='upload',TOTAL=v,FLOCK_ID=None,FACILITY_ID=None) for i,(n,v) in enumerate([('003',None),('004',0),('003',None),(None,-3),(None,3)])])
    result=build_custom_report(repo,user=user(),dataset='Production Records',selected_fields=['PRODUCER_ACCOUNT_ID','TOTAL'],group_by=['PRODUCER_ACCOUNT_ID'],aggregations={'TOTAL':'sum'})
    assert len(result)==4 and result['Source Total'].isna().sum()==1
    csv=pd.read_csv(BytesIO(report_csv(user(),result)))
    xlsx=pd.read_excel(BytesIO(report_xlsx(user(),result)))
    assert csv['Source Total'].isna().sum()==xlsx['Source Total'].isna().sum()==1
    assert csv['Source Total'].sum()==xlsx['Source Total'].sum()==0


def history_repo(repo):
    record_event=repo.record_flock_event
    repo.record_flock_event=lambda *args,**kwargs: record_event(*args,position_confirmed=True,**kwargs)
    repo._flocks=pd.DataFrame([dict(FLOCK_ID='f',FLOCK_NUMBER='Synthetic',ACCOUNT_ID='a',FACILITY_ID='old',DISPOSAL_DATE=None,EST_DISPOSAL=dt.date(2000,1,1))])
    repo._facilities=pd.DataFrame([dict(FACILITY_ID='old',ACCOUNT_ID='a'),dict(FACILITY_ID='new',ACCOUNT_ID='a'),dict(FACILITY_ID='other',ACCOUNT_ID='b')])
    return repo


def test_move_end_history_retry_multiple_flocks(repo):
    repo=history_repo(repo)
    first=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
    second=dt.datetime(2026,2,1,tzinfo=dt.timezone.utc)
    assert repo.get_flock_position('f',first)['STATUS']=='NO_PROVEN_HISTORY'
    event=repo.record_flock_event('f','MOVE',first,'Source-backed move','r1','new',actor='staff')
    assert repo.record_flock_event('f','MOVE',first,'Source-backed move','r1','new',actor='staff')==event
    assert len(repo.get_flock_events('f'))==1
    assert repo.get_flock_events('f').iloc[0].FROM_FACILITY_ID=='old'
    assert repo.get_flock_position('f',first)['FACILITY_ID']=='new'
    repo._flocks=pd.concat([repo._flocks,pd.DataFrame([dict(FLOCK_ID='f2',ACCOUNT_ID='a',FACILITY_ID='old')])],ignore_index=True)
    repo.record_flock_event('f2','MOVE',first,'Same building allowed','r2','new',actor='staff')
    repo.record_flock_event('f','END',second,'Actual end','r3',actor='staff')
    assert repo.get_flock_position('f',second)['STATUS']=='END'
    assert repo.get_flock_position('f',first)['FACILITY_ID']=='new'


def test_event_rollback_and_cross_account_guard(repo,monkeypatch):
    repo=history_repo(repo)
    time=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
    with pytest.raises(RepositoryError):repo.record_flock_event('f','MOVE',time,'Not confirmed','r','other',actor='staff')
    def fail(*args):raise RuntimeError('synthetic failure')
    monkeypatch.setattr(repo,'_append_history',fail)
    with pytest.raises(RuntimeError):repo.record_flock_event('f','MOVE',time,'Move','r','new',actor='staff')
    assert repo._flocks.iloc[0].FACILITY_ID=='old' and repo.get_flock_events('f').empty


def test_event_correction_and_immutable_old_history(repo):
    repo=history_repo(repo)
    moment=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
    original=repo.record_flock_event('f','MOVE',moment,'Wrong destination','request','new',actor='staff')
    corrected=repo.record_flock_event('f','MOVE',moment,'Correction evidence','correction','old',supersedes_event_id=original,actor='staff')
    assert corrected != original and len(repo.get_flock_events('f'))==2
    assert repo.get_flock_position('f',moment)['FACILITY_ID']=='old'
    assert repo.get_flock_events('f').iloc[0].TO_FACILITY_ID=='new'
    with pytest.raises(RepositoryError):repo.delete_flock('f')
    with pytest.raises(RepositoryError):repo.delete_facility('new')
    with pytest.raises(RepositoryError):repo.record_flock_event('f','MOVE',moment,'Different retry','correction','new',actor='staff')


def test_revision_preserves_unknown_history_and_retry(repo):
    repo=history_repo(repo)
    repo._flocks.loc[0,'BIRDS_DISPOSED']=-5
    repo._flocks.loc[0,'FLOCK_NUMBER']='Original'
    repo.revise_record('FLOCK','f',{'FLOCK_NUMBER':'Corrected'},'Source correction','same',actor='staff')
    repo.revise_record('FLOCK','f',{'FLOCK_NUMBER':'Corrected'},'Source correction','same',actor='staff')
    revisions=repo.get_record_revisions()
    assert len(revisions)==1 and revisions.iloc[0].BEFORE_DATA['FLOCK_NUMBER']=='Original'
    assert repo._flocks.iloc[0].BIRDS_DISPOSED==-5
    assert pd.isna(revisions.iloc[0].BUSINESS_AT)
    assert repo.get_flock_events('f').empty


def test_manual_save_identity_and_idempotence(repo):
    record=dict(PRODUCER_ACCOUNT_ID='a',REPORTING_YEAR=2026,REPORTING_WEEK=1,TOTAL=0)
    before=len(repo._production)
    first=repo.create_manual_production(record,'unique','staff')
    assert first==repo.create_manual_production(record,'unique','staff')
    assert len(repo._production)==before+1
    assert repo._production.iloc[-1].TOTAL==0
    assert repo._production.iloc[-1].MATCH_CONFIRMED_BY=='staff'


def test_review_page_mock_renders(tmp_path,monkeypatch):
    from pathlib import Path
    from tests.auth_support import authenticated_app
    app=authenticated_app(Path(__file__).parents[1]/'app/Home.py',tmp_path,monkeypatch)
    app.switch_page('pages/21_Record_History.py').run()
    assert not app.exception
