import copy,json,uuid
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from data.count_source_supplement import preview,verify_reviewed_plan,chunks,checksum
from data.migration import load_mapping,load_mapping_for_version,load_new_package_mapping,normalize_migration_row,V3_MAPPING_PATH,correction_mapping
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import RepositoryError
from app.security import User,Role,AuthorizationError
from app.services.authorized_repository import AuthorizedRepository

def fixture(size=1):
    raw=[];maps=[];targets=[]
    for i in range(size):
        guid=str(uuid.uuid5(uuid.NAMESPACE_URL,'synthetic-count-'+str(i))).upper();rid=str(i)
        raw.append(dict(MIGRATION_BATCH_ID='b',MIGRATION_RAW_ROW_ID=rid,SOURCE_ENTITY='FLOCK_TRANSACTION',SOURCE_ID=guid,TARGET_ID=guid,SOURCE_FILENAME='transactions.csv',SOURCE_ROW_NUMBER=i+2,VALIDATION_STATUS='READY',RAW_DATA={'EFC_FLOCKCOUNTTYPE_DISPLAYNAME':'Board'},NORMALIZED_DATA={'FLOCK_TRANSACTION_ID':guid}))
        maps.append(dict(MIGRATION_BATCH_ID='b',MIGRATION_RAW_ROW_ID=rid,SOURCE_ENTITY='FLOCK_TRANSACTION',SOURCE_ID=guid,TARGET_ID=guid,STATUS='COMMITTED'))
        targets.append(dict(FLOCK_TRANSACTION_ID=guid,COUNT_SOURCE_LABEL=None,QUANTITY=-10,UPDATED_AT='2026-01-01T00:00:00.123456789'))
    files=[dict(MIGRATION_BATCH_ID='b',SOURCE_FILENAME='transactions.csv',SOURCE_ENTITY='FLOCK_TRANSACTION',FILE_HASH='a'*64)]
    return dict(scope_ids=[r['SOURCE_ID'] for r in raw],raw_rows=raw,mappings=maps,current_rows=targets,files=files,batches=[dict(MIGRATION_BATCH_ID='b',STATUS='COMMITTED')],batch_id='b',source_file_hash='a'*64)

def test_count_plan_is_read_only_explicit_identity_and_nanosecond_bound():
    args=fixture();before=copy.deepcopy(args);p=preview(**args)
    assert args==before
    assert p['records'][0]['disposition']=='READY_FOR_REVIEW'
    assert p['records'][0]['expected_updated_at_ff9'].endswith('123456789')
    assert p['records'][0]['raw_sha256']==checksum(args['raw_rows'][0]['RAW_DATA'])
    assert verify_reviewed_plan(p,preview(**args))

@pytest.mark.parametrize('bad',['raw','mapping','targetduplicate','rawduplicate','filehash','versionmissing'])
def test_invalid_evidence_never_becomes_eligible(bad):
    a=fixture()
    if bad=='raw':a['raw_rows'][0]['TARGET_ID']='wrong'
    elif bad=='mapping':a['mappings'][0]['MIGRATION_BATCH_ID']='other'
    elif bad=='targetduplicate':a['current_rows']*=2
    elif bad=='rawduplicate':a['raw_rows']*=2
    elif bad=='filehash':a['source_file_hash']='b'*64
    else:a['current_rows'][0]['UPDATED_AT']=None
    assert preview(**a)['records'][0]['disposition']=='HOLD'

@pytest.mark.parametrize('value',[None,float('nan'),pd.NA,''])
def test_blank_values_can_be_reviewed_and_real_zero_is_unchanged(value):
    a=fixture();a['current_rows'][0]['COUNT_SOURCE_LABEL']=value
    assert preview(**a)['records'][0]['disposition']=='READY_FOR_REVIEW'
    assert a['current_rows'][0]['QUANTITY']==-10

def test_existing_label_is_protected_even_when_different_and_source_unknown_labels_preserved():
    a=fixture();a['current_rows'][0]['COUNT_SOURCE_LABEL']='Producer'
    assert preview(**a)['records'][0]['disposition']=='KEEP_EXISTING'
    a['current_rows'][0]['COUNT_SOURCE_LABEL']=None;a['raw_rows'][0]['RAW_DATA']['EFC_FLOCKCOUNTTYPE_DISPLAYNAME']='Legacy source X'
    assert preview(**a)['records'][0]['proposed_value']=='Legacy source X'

def test_stale_ff9_and_source_changes_are_not_rebased():
    a=fixture();old=preview(**a);a['current_rows'][0]['UPDATED_AT']='2026-01-01T00:00:00.123456790'
    with pytest.raises(RepositoryError,match='do not rebase'):verify_reviewed_plan(old,preview(**a))
    old['records'][0]['proposed_value']='wrong'
    with pytest.raises(RepositoryError,match='content changed'):verify_reviewed_plan(old,old)

def test_13556_preview_has_28_bounded_chunks_and_no_commit_entry():
    p=preview(**fixture(13556));parts=chunks(p)
    assert len(parts)==28 and len(parts[-1])==56
    assert sum(map(len,parts))==13556
    assert not hasattr(__import__('data.count_source_supplement',fromlist=['commit']),'commit')

def test_future_mapping_has_label_old_versions_and_date_interpretation_are_frozen():
    old=load_mapping(V3_MAPPING_PATH);r1=load_mapping();new=load_new_package_mapping()
    assert 'COUNT_SOURCE_LABEL' not in old['entities']['FLOCK_TRANSACTION']['field_map']
    assert 'COUNT_SOURCE_LABEL' not in r1['entities']['FLOCK_TRANSACTION']['field_map']
    parsed,errors=normalize_migration_row('FLOCK_TRANSACTION',{'efc_flockcounttype_displayname':'Producer'},2,new)
    assert parsed['COUNT_SOURCE_LABEL']=='Producer'
    assert load_mapping_for_version(r1['schema_version'])==r1
    assert load_mapping_for_version(new['schema_version'])==new
    assert correction_mapping(old)['schema_version']==r1['schema_version']
    assert new['entities']['FLOCK']['field_map']['EST_DISPOSAL']==r1['entities']['FLOCK']['field_map']['EST_DISPOSAL']

def facility_repo():
    r=MockRepository();r._facilities=pd.DataFrame([dict(FACILITY_ID='f',COMMENTS='Current note')]);r._migration_batches=[dict(MIGRATION_BATCH_ID='b',STATUS='COMMITTED')]
    r._migration_files=[dict(MIGRATION_BATCH_ID='b',SOURCE_FILENAME='facility.csv',SOURCE_ENTITY='FACILITY',FILE_HASH='a'*64)]
    r._migration_raw_rows=[dict(MIGRATION_BATCH_ID='b',MIGRATION_RAW_ROW_ID='shared',SOURCE_ID='f',TARGET_ID='f',SOURCE_ENTITY='FACILITY',SOURCE_FILENAME='facility.csv',SOURCE_ROW_NUMBER=3,VALIDATION_STATUS='READY',RAW_DATA={'EFC_FACILITYDESCRIPTION':'Historical source text'})]
    r._migration_id_map=[dict(MIGRATION_BATCH_ID='b',MIGRATION_RAW_ROW_ID='shared',SOURCE_ENTITY='FACILITY',SOURCE_ID='f',TARGET_ID='f',STATUS='COMMITTED')]
    return r

def test_facility_description_is_source_scoped_and_does_not_overwrite_comments():
    r=facility_repo();before=copy.deepcopy(r._migration_raw_rows)
    r._migration_raw_rows.append(dict(before[0],MIGRATION_BATCH_ID='unrelated',RAW_DATA={'EFC_FACILITYDESCRIPTION':'Must not leak'}))
    rows=r.get_facility_source_descriptions('f')
    assert rows.DESCRIPTION.tolist()==['Historical source text']
    assert r.get_facility('f')['COMMENTS']=='Current note' and r._migration_raw_rows[0]==before[0]

def test_facility_ambiguous_or_invalid_identity_is_rejected():
    r=facility_repo();r._migration_id_map*=2
    with pytest.raises(RepositoryError,match='ambiguous'):r.get_facility_source_descriptions('f')
    r=facility_repo();r._migration_raw_rows[0]['TARGET_ID']='wrong'
    with pytest.raises(RepositoryError,match='identity'):r.get_facility_source_descriptions('f')

def test_facility_source_permission_is_not_broadened_to_viewers():
    r=facility_repo();user=User('viewer','viewer@nsegg.ca','Viewer',Role.REPORTING_VIEWER,True,False,'now','now',None)
    with pytest.raises(RepositoryError,match='permission'):AuthorizedRepository(r,None,user).get_facility_source_descriptions('f')

def test_facility_source_block_actually_renders_and_is_not_an_editable_current_value():
    app=AppTest.from_string("import streamlit as st\nfrom app.services.facility_source_description import render_source_description\nrender_source_description(st,st.session_state.test_repo,'f')")
    app.session_state.test_repo=facility_repo();app.run()
    assert not app.exception
    assert app.text[0].value=='Historical source text'
    assert any('not the current maintained description' in x.value for x in app.caption)
    assert len(app.text_area)==0 and len(app.button)==0
    page=(Path(__file__).resolve().parents[1]/'app/pages/11_Facilities.py').read_text()
    assert 'render_source_description(st,repo,view.record_id)' in page

def test_facility_sql_has_selected_guid_and_full_compound_identity():
    class Ex:
        def __init__(self):self.calls=[]
        def query(self,sql,params=None):
            self.calls.append((sql,params))
            if 'FROM EFNS_DEV.CORE.FACILITY ' in sql:return pd.DataFrame([{'FACILITY_ID':'f'}])
            return pd.DataFrame()
    ex=Ex();assert SnowflakeRepository(ex).get_facility_source_descriptions('f').empty
    assert len(ex.calls)==2
    sql,params=ex.calls[-1]
    assert params==('F',) and 'r.MIGRATION_BATCH_ID=m.MIGRATION_BATCH_ID' in sql and 'r.MIGRATION_RAW_ROW_ID=m.MIGRATION_RAW_ROW_ID' in sql
    assert 'f.FILE_HASH' in sql and 'm.SOURCE_ENTITY=\'FACILITY\'' in sql

def test_daily_create_and_sparse_update_retain_count_source_label():
    from data.operational_flock_quota_import import analyze_operational_files
    from tests.test_operational_flock_quota_import import csv_upload,references
    r=MockRepository();ref=references(r);id=str(uuid.uuid4())
    values={'ACTION':'CREATE','FLOCK_TRANSACTION_ID':id,'Flock':ref['flock']['FLOCK_ID'],'Transaction Type':'Count','Quantity':'5','Transaction Date':'2026-09-20','efc_flockcounttype_displayname':'Board'}
    report=analyze_operational_files([csv_upload('new.csv',[values])],'Flock Transactions',r)
    assert not report.rejected_rows and len(report.ready_rows)==1
    r.import_operational_flock_quota_batch({'FILENAME':'new.csv','FILE_HASH':report.package_hash},report.records_by_entity,report.raw_rows)
    assert r.get_flock_transactions().set_index('FLOCK_TRANSACTION_ID').loc[id,'COUNT_SOURCE_LABEL']=='Board'
    changed={'ACTION':'UPDATE','FLOCK_TRANSACTION_ID':id,'Notes':'Changed note'}
    report=analyze_operational_files([csv_upload('update.csv',[changed])],'Flock Transactions',r)
    assert len(report.ready_rows)==1
    r.import_operational_flock_quota_batch({'FILENAME':'update.csv','FILE_HASH':report.package_hash},report.records_by_entity,report.raw_rows)
    assert r.get_flock_transactions().set_index('FLOCK_TRANSACTION_ID').loc[id,'COUNT_SOURCE_LABEL']=='Board'


def test_existing_report_preview_csv_and_xlsx_already_support_source_labels():
    from io import BytesIO
    from app.services.report_center import build_custom_report,report_csv,report_xlsx
    class Repo:
        def get_flock_transactions(self,**kwargs):
            return pd.DataFrame([{'FLOCK_TRANSACTION_ID':'one','COUNT_SOURCE_LABEL':'Board','QUANTITY':0},{'FLOCK_TRANSACTION_ID':'two','COUNT_SOURCE_LABEL':None,'QUANTITY':-2},{'FLOCK_TRANSACTION_ID':'three','COUNT_SOURCE_LABEL':'Legacy source X','QUANTITY':3}])
    user=User('u','u@nsegg.ca','Synthetic admin',Role.ADMIN,True,False,'now','now',None)
    frame=build_custom_report(Repo(),user=user,dataset='Flock Transactions',selected_fields=['FLOCK_TRANSACTION_ID','COUNT_SOURCE_LABEL','QUANTITY'])
    assert frame['Count Source'].tolist()==['Board',None,'Legacy source X']
    assert frame.Quantity.tolist()==[0,-2,3]
    a=pd.read_csv(BytesIO(report_csv(user,frame)));b=pd.read_excel(BytesIO(report_xlsx(user,frame)))
    pd.testing.assert_frame_equal(a,b)
    assert pd.isna(a.loc[1,'Count Source']) and a.loc[0,'Quantity']==0
