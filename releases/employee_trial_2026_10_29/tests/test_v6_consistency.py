"""Isolated synthetic regression cases for the v6 review corrections."""
import datetime as dt
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pandas as pd
import pytest

from app.services.report_center import build_custom_report, report_csv, report_xlsx
from data.repositories.base import ConcurrencyError, RepositoryError
from data.source_scope import scope_production, PROVENANCE
from tests.test_continuity import repo, history_repo, workbook
from tests.test_report_center import user
from data.importing import read_eims_workbook
from data.production_intake import prepare_workbook


def observation(repo):
    repo._production = pd.DataFrame([dict(PRODUCTION_ID='p',PRODUCER_ACCOUNT_ID='a',PRODUCER_NUMBER='001',IMPORT_ID='source',TOTAL=600,REPORTING_YEAR=2026,REPORTING_WEEK=15,UPDATED_AT=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc))])
    return repo._production.iloc[0].UPDATED_AT


def report(repo, **kwargs):
    return build_custom_report(repo,user=user(),dataset='Production Records',selected_fields=['PRODUCER_ACCOUNT_ID','TOTAL'],group_by=['PRODUCER_ACCOUNT_ID'],aggregations={'TOTAL':'sum'},**kwargs)


def test_production_correction_updates_not_adds_and_retries(repo):
    version = observation(repo)
    repo.revise_record('PRODUCTION_RECORD','p',{'TOTAL':'650'},'Source correction','r',actor='staff',expected_updated_at=version)
    repo.revise_record('PRODUCTION_RECORD','p',{'TOTAL':'650'},'Source correction','r',actor='staff',expected_updated_at=version)
    assert len(repo._production) == 1 and report(repo).iloc[0]['Source Total'] == 650
    revision = repo.get_record_revisions().iloc[0]
    assert revision.BEFORE_DATA['TOTAL'] == 600 and revision.AFTER_DATA['TOTAL'] == 650
    assert revision.RECORDED_BY == 'staff' and revision.REASON == 'Source correction'
    with pytest.raises(RepositoryError):
        repo.revise_record('PRODUCTION_RECORD','p',{'TOTAL':700},'Changed retry','r',actor='staff',expected_updated_at=version)
    with pytest.raises(ConcurrencyError):
        repo.revise_record('PRODUCTION_RECORD','p',{'TOTAL':700},'Stale','other',actor='staff',expected_updated_at=version)


def test_production_correction_rollback(repo,monkeypatch):
    version=observation(repo)
    def fail(*args): raise RuntimeError('Synthetic history failure')
    monkeypatch.setattr(repo,'_append_history',fail)
    with pytest.raises(RuntimeError): repo.revise_record('PRODUCTION_RECORD','p',{'TOTAL':650},'Fix','r',actor='staff',expected_updated_at=version)
    assert repo._production.iloc[0].TOTAL == 600 and repo.get_record_revisions().empty


def test_concurrent_corrections_have_one_winner(repo):
    version=observation(repo)
    def correct(value):
        try:
            repo.revise_record('PRODUCTION_RECORD','p',{'TOTAL':value},'Fix',str(value),actor='staff',expected_updated_at=version)
            return 'saved'
        except ConcurrencyError: return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(correct,[650,700])) == ['conflict','saved']
    assert len(repo.get_record_revisions()) == 1


def test_modified_workbook_requires_explicit_intent_not_fuzzy_dedupe(repo):
    observation(repo)
    content=workbook()
    original=repo.archive_source_file('changed.xlsx',content,'PRODUCTION_WORKBOOK')
    _,rows,_,_=prepare_workbook(read_eims_workbook(BytesIO(content)),original['SOURCE_FILE_ID'],repo._accounts)
    batch=repo.stage_production_upload(dict(SOURCE_FILE_ID=original['SOURCE_FILE_ID'],FILE_HASH=original['FILE_HASH'],SOURCE_RECORD_COUNT=len(rows)),rows)
    with pytest.raises(RepositoryError,match='original Production ID'):
        repo.commit_staged_production(batch,actor='staff')
    assert len(repo._production) == 1 and len(repo.get_raw_rows(batch)) == 3
    assert repo.find_import_by_hash(original['FILE_HASH'])['STATUS'] == 'Staged'
    repo.commit_staged_production(batch,actor='staff',new_observations_confirmed=True)
    repo.commit_staged_production(batch,actor='staff',new_observations_confirmed=True)
    assert len(repo._production) == 2  # Two independent observations, not one producer/week identity.


@pytest.mark.parametrize('values,expected,known,missing', [([600,None,400],1000,2,1),([None,None],None,0,2),([0,None],0,1,1),([-3,3],0,2,0)])
def test_known_sum_and_missing_counts_same_in_exports(repo,values,expected,known,missing):
    repo._production=pd.DataFrame([dict(PRODUCTION_ID=str(i),PRODUCER_ACCOUNT_ID='a',IMPORT_ID='unknown',TOTAL=v) for i,v in enumerate(values)])
    result=report(repo)
    for frame in [result,pd.read_csv(BytesIO(report_csv(user(),result))),pd.read_excel(BytesIO(report_xlsx(user(),result)))]:
        row=frame.iloc[0]
        assert pd.isna(row['Source Total']) if expected is None else row['Source Total'] == expected
        assert row['Record count']==len(values) and row['Source Total known count']==known and row['Source Total missing count']==missing


def test_source_type_is_not_source_authentication(repo):
    ids=list(PROVENANCE['batches'])
    repo._production=pd.DataFrame([dict(PRODUCTION_ID=str(i),PRODUCER_ACCOUNT_ID='a',IMPORT_ID=batch,TOTAL=1,SOURCE_TYPE='EIMS_IMPORT') for i,batch in enumerate(ids+['unknown'])])
    assert len(scope_production(repo._production,'Confirmed historical package'))==1
    assert len(scope_production(repo._production,'DEV test data'))==2
    assert len(scope_production(repo._production,'Unclassified source'))==1
    assert report(repo,filters={'source_scope':'Confirmed historical package'}).iloc[0]['Source Total']==1


def test_legacy_manifest_rows_and_supplement_are_both_visible(repo):
    file_id,imports=next(iter(PROVENANCE['legacy_file_imports'].items()))
    repo._raw_rows=[dict(IMPORT_ID=imports[0],RAW_ROW_ID='old',SOURCE_ROW_NUMBER=11,SOURCE_FILE_ID=None),dict(IMPORT_ID='supplement',RAW_ROW_ID='extra',SOURCE_ROW_NUMBER=71,SOURCE_FILE_ID=file_id)]
    result=repo.get_source_review_rows(file_id)
    assert set(result.RAW_ROW_ID)=={'old','extra'} and result.TRACE_METHOD.nunique()==2
    assert repo._raw_rows[0]['SOURCE_FILE_ID'] is None


def test_initial_position_and_timeline_rejects_unsafe_changes(repo):
    repo=history_repo(repo)
    # Call the unwrapped method because history_repo wraps MOVE confirmation.
    from data.repositories.continuity import ContinuityRepository
    record=lambda kind,time,token,target=None,**kw: ContinuityRepository.record_flock_event(repo,'f',kind,time,'Synthetic evidence',token,target,actor='staff',position_confirmed=True,**kw)
    january=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
    june=dt.datetime(2026,6,1,tzinfo=dt.timezone.utc)
    august=dt.datetime(2026,8,1,tzinfo=dt.timezone.utc)
    record('INITIAL_POSITION',january,'initial','old')
    first=record('MOVE',june,'move1','new')
    record('MOVE',august,'move2','old')
    with pytest.raises(RepositoryError): record('MOVE',june,'backfill','new')
    with pytest.raises(RepositoryError): record('MOVE',june,'correct','old',supersedes_event_id=first)
    assert repo._flocks.iloc[0].FACILITY_ID=='old'
    assert repo.get_flock_position('f',january)['FACILITY_ID']=='old'
    record('END',dt.datetime(2026,9,1,tzinfo=dt.timezone.utc),'end')
    with pytest.raises(RepositoryError): record('MOVE',dt.datetime(2026,9,2,tzinfo=dt.timezone.utc),'after-end','new')
    with pytest.raises(RepositoryError): record('MOVE',dt.datetime(2099,1,1,tzinfo=dt.timezone.utc),'future','new')
    assert len(repo.get_flock_events('f')) == 4


def test_new_flock_and_initial_position_are_atomic_and_retryable(repo,monkeypatch):
    from data.repositories.continuity import ContinuityRepository
    repo=history_repo(repo)
    repo.record_flock_event=ContinuityRepository.record_flock_event.__get__(repo)
    record=dict(FLOCK_NUMBER='Synthetic initial',ACCOUNT_ID='a',FACILITY_ID='old',PERMIT_NUMBER='Synthetic',HATCH_DATE=dt.date(2025,1,1),BIRD_COUNT=10)
    at=dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)
    saved=repo.create_flock_with_initial_position(record,at,'Verified source','create',actor='staff')
    assert repo.create_flock_with_initial_position(record,at,'Verified source','create',actor='staff')==saved
    assert repo.get_flock_position(saved,at)['FACILITY_ID']=='old'
    assert len(repo.get_flock_events(saved))==1
    count=len(repo._flocks)
    def fail(*args): raise RuntimeError('Synthetic append failure')
    monkeypatch.setattr(repo,'_append_history',fail)
    with pytest.raises(RuntimeError): repo.create_flock_with_initial_position(record,at,'Verified source','failure',actor='staff')
    assert len(repo._flocks)==count


def test_ordinary_facility_owner_change_cannot_bypass_flock_guard(repo):
    repo=history_repo(repo)
    with pytest.raises(RepositoryError,match='ownership'):
        repo.upsert_facility(dict(FACILITY_ID='old',ACCOUNT_ID='b'))
    assert repo.get_facility('old')['ACCOUNT_ID']=='a'
    with pytest.raises(RepositoryError,match='existing Account'):
        repo.upsert_facility(dict(ACCOUNT_ID='missing',FACILITY_NAME='Synthetic'))


def test_text_producer_number_keeps_leading_zero_before_resolution(repo):
    source=read_eims_workbook(BytesIO(workbook()))
    assert source.iloc[0]['Producer #']=='001'
    accepted,_,_,_=prepare_workbook(source,'synthetic-file',repo._accounts)
    assert accepted.iloc[0].PRODUCER_ACCOUNT_ID=='a'
    assert accepted.iloc[0].MATCH_STATUS=='UNIQUE_MATCHED'


def test_source_row_without_identity_stays_raw_not_reported(repo):
    source=read_eims_workbook(BytesIO(workbook()))
    accepted,rows,_,_=prepare_workbook(source,'synthetic-file',repo._accounts)
    missing=rows[1]
    assert missing['VALIDATION_STATUS']=='REJECTED' and missing['TARGET_ID'] is None
    assert len(accepted)==1 and 12 not in accepted.SOURCE_ROW_NUMBER.tolist()


def test_identical_independent_rows_within_file_are_not_deduplicated(repo):
    from data.constants import EIMS_REQUIRED_COLUMNS
    raw=pd.DataFrame([dict.fromkeys(EIMS_REQUIRED_COLUMNS) for _ in range(2)])
    raw['Week']='202615'; raw['Producer #']='001'; raw['Total']=600
    raw['SOURCE_ROW_NUMBER']=[11,12]
    accepted,rows,_,_=prepare_workbook(raw,'synthetic-source',repo._accounts)
    assert len(accepted)==2 and accepted.PRODUCTION_ID.nunique()==2 and accepted.TOTAL.sum()==1200


def test_sql_production_correction_uses_same_transaction_and_native_binds():
    from contextlib import contextmanager
    from data.repositories.snowflake import SnowflakeRepository
    class SQL:
        def __init__(self): self.calls=[]; self.active=False; self.total=600
        @contextmanager
        def transaction(self):
            self.active=True
            try: yield self
            finally: self.active=False
        def query(self,sql,params=None):
            assert self.active
            if 'RECORD_REVISION' in sql: return pd.DataFrame()
            return pd.DataFrame([dict(PRODUCTION_ID='p',TOTAL=self.total,UPDATED_AT=pd.Timestamp('2026-01-01'))])
        def execute(self,sql,params=None):
            assert self.active
            self.calls.append((sql,params))
            if 'UPDATE EFNS_DEV.CORE.PRODUCTION_RECORD' in sql:
                assert params[-1] == '2026-01-01T00:00:00'
                self.total=params[0]
            return 1
    executor=SQL(); repository=SnowflakeRepository(executor)
    repository.revise_record('PRODUCTION_RECORD','p',{'TOTAL':650},'Synthetic correction','r',actor='staff',expected_updated_at=pd.Timestamp('2026-01-01'))
    writes=[sql for sql,_ in executor.calls]
    assert sum('UPDATE EFNS_DEV.CORE.PRODUCTION_RECORD' in sql for sql in writes)==1
    assert sum('INSERT INTO EFNS_DEV.APP.RECORD_REVISION' in sql for sql in writes)==1
    assert not any('INSERT INTO EFNS_DEV.CORE.PRODUCTION_RECORD' in sql for sql in writes)


def test_operational_flock_update_retains_revision_and_rolls_back(repo,monkeypatch):
    from tests.test_operational_flock_quota_import import flock_row, csv_upload
    from tests.test_operational_review_persistence import prepare
    # Use an existing valid synthetic Flock with its source GUID, not a guessed number match.
    from data.repositories.mock import MockRepository
    repo=MockRepository()
    current=repo._flocks.iloc[0].to_dict()
    row=flock_row(repo,'Synthetic updated')
    row['Flock ID']=current['FLOCK_ID']
    row.update({'Account':current['ACCOUNT_ID'],'Facility':current['FACILITY_ID'],'Permit Number':current['PERMIT_NUMBER'],'Hatch Date':current['HATCH_DATE'],'Bird Count':current['BIRD_COUNT']})
    batch,review,_=prepare(repo,csv_upload('synthetic-update.csv',[row]))
    assert len(review.ready_rows)==1
    before=repo.get_flock(current['FLOCK_ID'])
    repo.commit_staged_operational(batch,review.records_by_entity,actor='staff')
    revisions=repo.get_record_revisions()
    assert len(revisions)==1 and revisions.iloc[0].RECORDED_BY=='staff'
    assert revisions.iloc[0].BEFORE_DATA['FLOCK_NUMBER']==before['FLOCK_NUMBER']
    assert repo.commit_staged_operational(batch,review.records_by_entity,actor='staff')['already_committed']
    row['Flock Number']='Synthetic second correction'
    second,next_review,_=prepare(repo,csv_upload('synthetic-update-2.csv',[row]))
    def fail(*args): raise RuntimeError('Synthetic revision failure')
    monkeypatch.setattr(repo,'_append_history',fail)
    with pytest.raises(RuntimeError): repo.commit_staged_operational(second,next_review.records_by_entity,actor='staff')
    assert repo.get_flock(current['FLOCK_ID'])['FLOCK_NUMBER']==revisions.iloc[0].AFTER_DATA['FLOCK_NUMBER']
    assert len(repo.get_record_revisions())==1
    assert repo.find_import_by_hash(next_review.package_hash)['STATUS']=='Staged'
