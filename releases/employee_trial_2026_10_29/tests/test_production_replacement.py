"""Synthetic producer/week replacement, durable evidence and rollback."""
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json

import pandas as pd
import pytest

from data.constants import EIMS_REQUIRED_COLUMNS
from data.production_intake import prepare_workbook
from data.production_replacement import BACKUP_TABLE, upload_errors
from data.repositories.production_replacement import replace_sets
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import RepositoryError
from data.source_evidence import evidence_json
from app.services.production_import_review import summary_text


def repo():
    result=MockRepository()
    from tests.history_actor_support import MemoryUsers
    result._history_auth_store = MemoryUsers('staff', 'synthetic-staff')
    result._accounts=pd.DataFrame([dict(ACCOUNT_ID=a,REGISTRATION_NUMBER=n,STATUS='Active') for a,n in [('a','001'),('b','002')]])
    result._production=result._production.iloc[:0].copy()
    result._size_breakdown=result._size_breakdown.iloc[:0].copy()
    return result


def raw(rows):
    frame=pd.DataFrame(rows)
    for column in EIMS_REQUIRED_COLUMNS:
        if column not in frame:frame[column]=None
    frame['SOURCE_ROW_NUMBER']=range(11,11+len(frame))
    return frame


def stage(r,frame):
    archive=r.archive_source_file('synthetic.xlsx',evidence_json(frame.to_dict('records')).encode(),'PRODUCTION_WORKBOOK','staff')
    records,rows,errors,warnings=prepare_workbook(frame,archive['SOURCE_FILE_ID'],r.get_accounts())
    batch=r.stage_production_upload(dict(SOURCE_FILE_ID=archive['SOURCE_FILE_ID'],FILE_HASH=archive['FILE_HASH'],SOURCE_RECORD_COUNT=len(rows)),rows)
    return batch,records,errors


def existing(identity,owner='a',week=202601,total=7,**extra):
    return dict(PRODUCTION_ID=identity,PRODUCER_ACCOUNT_ID=owner,PRODUCER_NUMBER='001' if owner=='a' else '002',
        SOURCE_WEEK_CODE=str(week),REPORTING_YEAR=week//100,REPORTING_WEEK=week%100,TOTAL=total,IMPORT_ID='previous',**extra)


def test_complete_set_mixed_upload_summary_backup_children_and_idempotency():
    r=repo()
    rows=[existing('old-1'),existing('old-2',total=9),existing('other-producer','b'),existing('other-week',week=202602)]
    r._production=pd.DataFrame(rows)
    r._size_breakdown=pd.DataFrame([dict(SIZE_BREAKDOWN_ID='child',PRODUCTION_ID='old-2',SIZE_BAND='L',QUANTITY=Decimal('9.125'))])
    batch,_,_=stage(r,raw([{'Producer #':'001','Week':202601,'Total':Decimal('3.125')},
        {'Producer #':'001','Week':202603,'Total':Decimal('2.75')}]))
    assert r.commit_staged_production(batch,'staff')==(batch,2)
    assert set(r._production.PRODUCTION_ID)&{'old-1','old-2'}==set()
    assert r._production.loc[r._production.PRODUCTION_ID=='other-producer'].iloc[0].TOTAL==7
    assert r._production.loc[r._production.PRODUCTION_ID=='other-week'].iloc[0].TOTAL==7
    assert sorted(r._production.TOTAL.tolist())==[Decimal('2.75'),Decimal('3.125'),7,7]
    backups=r.get_production_replacement_backups(batch)
    assert len(backups)==2 and set(backups.REPLACED_BY)=={'staff'}
    assert [row['TOTAL'] for row in backups.OLD_VALUES]==[7,9]
    assert backups.iloc[1].SIZE_BREAKDOWN_ROWS[0]['QUANTITY']==Decimal('9.125')
    assert r._size_breakdown.empty
    summary=r.get_production_import_summary(batch)
    assert summary==dict(import_id=batch,rows_inserted=1,rows_replaced=2,rows_written=2,
        rows_unchanged=2,producer_weeks_replaced=1,week_start=202601,week_end=202601)
    assert '2 old rows replaced' in summary_text(summary)
    assert len(r.get_record_revisions())==1 and len(r._migration_review_audit)==1
    assert r.commit_staged_production(batch,'staff')==(batch,2)
    assert len(r.get_production_replacement_backups(batch))==2 and len(r._production)==4


@pytest.mark.parametrize('failure',['insert','matching','audit','partial-insert'])
def test_failure_restores_production_children_backup_and_batch(monkeypatch,failure):
    r=repo();r._production=pd.DataFrame([existing('old')])
    r._size_breakdown=pd.DataFrame([dict(PRODUCTION_ID='old',QUANTITY=4)])
    before=r._production.copy(deep=True);children=r._size_breakdown.copy(deep=True)
    batch,_,_=stage(r,raw([{'Producer #':'001','Week':202601,'Total':3}]))
    def fail(*args,**kwargs):raise RepositoryError('Synthetic failure')
    if failure=='partial-insert':monkeypatch.setattr(r,'insert_production_records',lambda *args:0)
    else:monkeypatch.setattr(r,{'insert':'insert_production_records','matching':'_append_match','audit':'_review_insert'}[failure],fail)
    with pytest.raises(RepositoryError):r.commit_staged_production(batch,'staff')
    pd.testing.assert_frame_equal(r._production,before)
    pd.testing.assert_frame_equal(r._size_breakdown,children)
    assert r.get_production_replacement_backups(batch).empty and r.get_record_revisions().empty
    assert r.find_import_by_hash(r._import_batches[-1]['FILE_HASH'])['STATUS']=='Staged'


def test_missing_backup_refuses_only_overwrite_and_new_only_works():
    r=repo();r._production=pd.DataFrame([existing('old')]);del r._continuity_rows[BACKUP_TABLE]
    batch,_,_=stage(r,raw([{'Producer #':'001','Week':202601,'Total':3}]))
    with pytest.raises(RepositoryError,match='schema update'):r.commit_staged_production(batch,'staff')
    assert list(r._production.PRODUCTION_ID)==['old']
    other,_,_=stage(r,raw([{'Producer #':'001','Week':202602,'Total':3}]))
    assert r.commit_staged_production(other,'staff')==(other,1)
    assert len(r._production)==2 and r.get_production_import_summary(other)['rows_replaced']==0


@pytest.mark.parametrize('changes',[
    {'Producer #':'unknown'}, {'Producer #':None}, {'Week':202654}, {'Week':'202601x'},
    {'Total':-1}, {'Total':'invalid'},
])
def test_validation_errors_block_entire_file(changes):
    r=repo();frame=raw([dict({'Producer #':'001','Week':202601,'Total':3},**changes),
        {'Producer #':'002','Week':202601,'Total':4}])
    batch,records,errors=stage(r,frame)
    assert upload_errors(frame,records,errors)
    with pytest.raises(RepositoryError,match='Import blocked'):r.commit_staged_production(batch,'staff')
    assert r._production.empty


def test_duplicate_rows_rejected_but_distinct_details_same_producer_week_retained():
    r=repo();row={'Producer #':'001','Week':202601,'Total':3}
    batch,_,_=stage(r,raw([row,row]))
    with pytest.raises(RepositoryError,match='duplicated inside'):r.commit_staged_production(batch,'staff')
    batch,_,_=stage(r,raw([row,dict(row,Total=4)]))
    assert r.commit_staged_production(batch,'staff')==(batch,2)
    assert list(r._production.TOTAL)==[3,4]


def test_legacy_unlinked_exact_registration_and_year_week_fallback():
    r=repo();r._production=pd.DataFrame([existing('old',owner=None)])
    r._production.loc[0,'PRODUCER_NUMBER']='001';r._production.loc[0,'SOURCE_WEEK_CODE']=None
    batch,_,_=stage(r,raw([{'Producer #':'001','Week':202601,'Total':3}]))
    r.commit_staged_production(batch,'staff')
    assert len(r._production)==1 and r._production.iloc[0].TOTAL==3
    assert r.get_production_replacement_backups(batch).iloc[0].OLD_VALUES['PRODUCER_ACCOUNT_ID'] is None


def test_concurrent_uploads_each_replace_one_complete_set():
    r=repo()
    batches=[stage(r,raw([{'Producer #':'001','Week':202601,'Total':n}]))[0] for n in (3,4)]
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda batch:r.commit_staged_production(batch,'staff'),batches))
    assert len(r._production)==1 and r._production.iloc[0].TOTAL in (3,4)
    assert sum(len(r.get_production_replacement_backups(batch)) for batch in batches)==1


def test_snowflake_replacement_backup_precedes_delete_and_all_queries_are_bound():
    r=SnowflakeRepository();accounts=repo().get_accounts();old=existing('old');calls=[]
    class Tx:
        def query(self,sql,params=None):
            calls.append(('query',sql,params))
            if 'COUNT(*)' in sql:return pd.DataFrame([{'N':2}])
            if 'WHERE 1=0' in sql:return pd.DataFrame(columns=['REPLACEMENT_ID'])
            if 'SIZE_BREAKDOWN' in sql:return pd.DataFrame([dict(PRODUCTION_ID='old',QUANTITY=7)])
            return pd.DataFrame([old])
        def execute(self,sql,params):calls.append(('execute',sql,params));return 1
    records,_,_,_=prepare_workbook(raw([{'Producer #':'001','Week':202601,'Total':3}]),'file',accounts)
    with replace_sets(r,Tx(),records,accounts,'batch','staff') as summary:
        assert summary['rows_replaced']==1
    mutations=[sql for kind,sql,_ in calls if kind=='execute']
    assert mutations[0].startswith('INSERT INTO EFNS_DEV.RAW.PRODUCTION_REPLACEMENT_BACKUP')
    assert mutations[1].startswith('DELETE FROM EFNS_DEV.CORE.PRODUCTION_SIZE_BREAKDOWN')
    assert mutations[2].startswith('DELETE FROM EFNS_DEV.CORE.PRODUCTION_RECORD')
    assert 'PARSE_JSON(%s)' in calls[0][1] and calls[0][2]


def test_import_page_has_no_confirmation_prompt_and_has_backup_viewer(tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo()
    app.switch_page('app/pages/1_Production_Import.py').run()
    assert not app.exception
    assert app.text_input(key='production_backup_batch').label=='Import Batch ID'
    assert not any('independent new observations' in c.label for c in app.checkbox)
    source=(root/'app/pages/1_Production_Import.py').read_text(encoding='utf-8')
    assert 'confirm_import' not in source and 'new_observations_confirmed=' not in source
