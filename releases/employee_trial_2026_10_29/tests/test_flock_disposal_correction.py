"""Offline disposal correction authoring, original exports and inventory outcomes."""
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import re

import pandas as pd
import pytest

from scripts.generate_flock_disposal_correction import (read_inputs,reconcile,generate,generate_sql,
    verification_sql,UNKNOWN,KEEP,FIELDS,receipts)
from data.migration import load_mapping,load_mapping_for_version,correction_mapping
from app.services.producers_over_quota_report import build_producers_over_quota_report
from tests.test_flock_age_report import QUOTAS

ROOT=Path(__file__).resolve().parents[1]
FIXTURES=ROOT/'tests/fixtures/flock_disposal_correction'
LEGACY=FIXTURES/'Active Flocks 11-10-2026 11-48-38 AM.xlsx'
EXPORTED=FIXTURES/'efns_custom_report (10).csv'
REVIEW=ROOT/'sql/review/flock_disposal_correction_20261110'
BIRDS={'40329':73764,'40346':15985,'40348':48820,'40350':15356,
       '40357':38108,'40358':24052,'40366':5196,'40369':1851}


@pytest.fixture(scope='module')
def analysis():
    old,new,bindings=read_inputs(LEGACY,EXPORTED)
    return old,new,bindings,reconcile(old,new)


def test_full_2172_row_comparison_and_scope(analysis):
    old,new,bindings,(rows,summary,differences,missing,duplicates)=analysis
    assert (len(old),len(new),summary['uniquely_matched'])==(2197,2219,2172)
    assert summary['field_mismatch_counts']==dict(EST_DISPOSAL=14,DISPOSAL_DATE=14,
        PLACEMENT_DATE=12,HATCH_DATE=0,BIRD_COUNT=0,QUOTA_TYPE=0,ACCOUNT=0)
    assert summary['mapping_pattern_counts']==dict(legacy_dates_distinct=1781,
        already_correct_distinct_pair=1767,indistinguishable_equal_legacy_dates=391,
        informative_exact_swap=8,legacy_nonblank_birds_disposed=1825)
    assert len(differences)==17 and len(rows)==14
    assert {r['permit'] for r in rows}==set(BIRDS)|{'30368','30371','30372','30374','30375','40375'}
    assert {r['permit'] for r in duplicates if r['legacy_count']>1}=={'30133','30171','30193','30348','30355','40027'}
    assert {'30157','40055','NF'}<={r['permit'] for r in duplicates}
    assert all(r['old']['BIRDS_DISPOSED']==UNKNOWN for r in rows)
    assert {r['permit']:r['new']['BIRDS_DISPOSED'] for r in rows if 'BIRDS_DISPOSED' in r['changed_fields']}==BIRDS
    assert all(r['new']['BIRDS_DISPOSED']==KEEP for r in rows if r['permit'] not in BIRDS)
    assert all('PLACEMENT_DATE' not in r['changed_fields'] for r in rows)
    assert len(missing)==10
    bayview=[r for r in missing if r['Permit Number'] in {'40407','30407'}]
    assert {r['SOURCE_EXCEL_ROW'] for r in bayview}=={11,12}
    assert all(r['Bird Count']==11000 and r['Registration Number (Account) (Account)']=='7038' for r in bayview)
    assert {r['Flock Quota Type'] for r in bayview}=={'Egg Production','Non Commercial Pullet Quota'}
    assert all(r['Placement Date'].date().isoformat()=='2027-01-19' for r in bayview)


def test_mapping_root_cause_is_general_but_current_revision_already_fixes_it(analysis):
    _,_,bindings,_=analysis
    assert bindings=={'new_disposaldate':'Disposal Date','new_disposaldate2':'Estimated Disposal Date','efc_birdsdisposed':'Birds Disposed'}
    old=load_mapping_for_version('EFNS-EIMS-DATAVERSE-3')
    revised=load_mapping()
    assert old['entities']['FLOCK']['field_map']['EST_DISPOSAL']=='new_disposaldate'
    assert old['entities']['FLOCK']['field_map']['DISPOSAL_DATE']=='new_disposaldate2'
    assert revised['entities']['FLOCK']['field_map']['EST_DISPOSAL']=='new_disposaldate2'
    assert revised['entities']['FLOCK']['field_map']['DISPOSAL_DATE']=='new_disposaldate'
    assert correction_mapping(old)['entities']['FLOCK']['field_map']==revised['entities']['FLOCK']['field_map']
    assert old['entities']['FLOCK']['field_map']['BIRDS_DISPOSED']==revised['entities']['FLOCK']['field_map']['BIRDS_DISPOSED']=='efc_birdsdisposed'


def test_generator_is_read_only_and_checked_in_outputs_reproduce(tmp_path):
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (LEGACY,EXPORTED)}
    rows,summary=generate(LEGACY,EXPORTED,tmp_path/'plan')
    assert hashes=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in hashes}
    for path in (tmp_path/'plan').iterdir():
        assert path.read_bytes().replace(b'\r\n',b'\n')==(REVIEW/path.name).read_bytes().replace(b'\r\n',b'\n'),path.name
    csv_rows=list(csv.DictReader((tmp_path/'plan/corrections.csv').read_text(encoding='utf-8-sig').splitlines()))
    assert len(csv_rows)==14 and all(r['old_BIRDS_DISPOSED']==UNKNOWN for r in csv_rows)
    assert all('ACCOUNT_ID=' in r['FLOCK_ID_LOOKUP'] and 'PERMIT_NUMBER=' in r['FLOCK_ID_LOOKUP'] for r in csv_rows)
    assert all(r['new_UPDATED_AT']=='<UTC_EXECUTION_TIMESTAMP>' for r in csv_rows)


def test_sql_backup_transaction_cas_audit_idempotence_and_rollback(analysis):
    rows=analysis[3][0]
    apply=generate_sql(rows,'test-plan');undo=generate_sql(rows,'test-plan',rollback=True)
    assert apply.index('CURRENT_TRANSACTION()')<apply.index('CREATE TABLE IF NOT EXISTS')<apply.index('BEGIN TRANSACTION;')<apply.index('UPDATE EFNS_DEV.CORE.FLOCK')
    assert 'CREATE OR REPLACE' not in apply and 'DROP TABLE' not in apply and 'TRUNCATE' not in apply
    assert 'AS SELECT f.* FROM EFNS_DEV.CORE.FLOCK' in apply
    assert 'FLOCK_BACKUP_20261110' in apply and 'FLOCK_BACKUP_20261110' in undo
    assert 'CREATE TABLE' not in undo and 'b.BIRDS_DISPOSED' in undo
    for sql in (apply,undo):
        assert sql.count('UPDATE EFNS_DEV.CORE.FLOCK AS f SET ')==14
        assert sql.count('n := SQLROWCOUNT;')==42  # UPDATE + mandatory revision + mandatory audit, per row.
        assert sql.count('IF (n <> 1)')>=56
        assert sql.count('INSERT INTO EFNS_DEV.APP.RECORD_REVISION')==sql.count('INSERT INTO EFNS_DEV.APP.AUDIT_EVENT')==14
        assert 'IF (receipt_count=1 AND audit_count=1)' in sql
        assert "ENTITY_TYPE,ENTITY_ID,CHANGE_KIND" in sql and ':before_row,:after_row' in sql
        assert 'CONVERT_TIMEZONE(\'UTC\',CURRENT_TIMESTAMP())' in sql
        assert 'IF (started) THEN ROLLBACK; END IF;' in sql and '    RAISE;' in sql
        assert '__SET_APP_USER_ID__' in sql and '__SET_APP_USER_EMAIL__' in sql
        updates=re.findall(r'UPDATE EFNS_DEV.CORE.FLOCK AS f SET (.*?)\n\s*FROM .*?;',sql,re.S)
        for row,assignment in zip(rows,updates):
            assert {v.split('=')[0].strip() for v in assignment.split(', ') if '=' in v}==set(row['changed_fields'])|{'UPDATED_AT'}
        for row in rows:
            assert f"f.PERMIT_NUMBER='{row['permit']}' AND f.ACCOUNT_ID='{row['account_id']}' AND f.FLOCK_ID='{row['flock_id']}'" in sql
    assert 'BEFORE_DATA INTO :backup_receipt' in undo and 'Do not restore a changed or mismatched backup' in undo
    assert 'b.FLOCK_ID=f.FLOCK_ID' in undo
    assert 'EQUAL_NULL(f.UPDATED_AT,b.UPDATED_AT)' in apply
    assert 'receipt_after' in undo  # Refuse restoration after subsequent app edits.
    assert receipts('test-plan',rows[0],'apply')==receipts('test-plan',deepcopy(rows[0]),'apply')
    assert receipts('test-plan',rows[0],'apply')!=receipts('test-plan',rows[0],'rollback')


def test_precheck_has_only_read_only_queries_and_both_business_keys(analysis):
    sql=verification_sql(analysis[3][0])
    assert not re.search(r'\b(UPDATE|INSERT|DELETE|MERGE|CREATE|DROP|ALTER|CALL)\b',sql,re.I)
    assert 'f.PERMIT_NUMBER=t.PERMIT_NUMBER AND f.ACCOUNT_ID=t.ACCOUNT_ID' in sql
    assert 'f.BIRDS_DISPOSED' in sql and 'ROW_MATCHES' in sql and 'FLOCK_ID_MATCH' in sql


def test_wrong_scope_ambiguous_permits_and_sql_values_fail_safely(analysis,tmp_path):
    old,new,_,_=analysis
    with pytest.raises(ValueError,match='Expected 13'):reconcile(old,new,expected_rows=13)
    # Duplicating a target excludes it rather than selecting either row.
    duplicate=next(r for r in new if r['Flock Number']=='40366')
    rows,summary,*_=reconcile(old,[*new,duplicate],expected_rows=13)
    assert '40366' not in {r['permit'] for r in rows}
    with pytest.raises(ValueError,match='must not contain'):generate(LEGACY,EXPORTED,FIXTURES)
    row=deepcopy(analysis[3][0][0]);row['account']="O'Brien\nDROP TABLE x;"
    sql=generate_sql([row],'test-plan')
    assert '\nDROP TABLE x' not in sql  # Names cannot escape SQL comments.
    with pytest.raises(ValueError,match='identifier'):generate_sql([row],'test',database='X;DROP')
    with pytest.raises(ValueError,match='identifier'):verification_sql([row],database='X;DROP')


def inventory_inputs(current):
    by_permit={r['Flock Number']:r for r in current}
    exported=list(csv.DictReader((FIXTURES/'flock_current_report (2).csv').read_text(encoding='utf-8-sig').splitlines()))
    f=[];t=[];a={};q={}
    for observation in exported:
        permit=observation['Permit No']
        if not permit.isdecimal():continue
        source=by_permit[permit];owner=source['Account ID']
        a[owner]=dict(ACCOUNT_ID=owner,ORGANIZATION_NAME=source['Flock Account'],
            REGISTRATION_NUMBER=observation['Reg No'],PRODUCER_ROLE=True)
        if observation['Reg No'] in QUOTAS:q[owner]=QUOTAS[observation['Reg No']]
        f.append(dict(FLOCK_ID=source['Flock ID'],PERMIT_NUMBER=permit,ACCOUNT_ID=owner,
            FLOCK_QUOTA_TYPE=source['Quota Type'],STATUS=source['Status'],HATCH_DATE=source['Hatch Date'],
            PLACEMENT_DATE=source['Placement Date'],EST_DISPOSAL=source['Estimated Disposal Date'],
            DISPOSAL_DATE=source['Actual Disposal Date']))
        try:quantity=int(observation['Counted'])
        except ValueError:continue
        t.append(dict(FLOCK_TRANSACTION_ID=permit,FLOCK_ID=source['Flock ID'],QUANTITY=quantity,
            TRANSACTION_DATE=observation['Count Date'],TRANSACTION_TYPE='Delivery' if 'Initial Delivery' in observation['Notes'] else 'Count',COUNT_SOURCE_LABEL='Exported observation'))
    return pd.DataFrame(f),pd.DataFrame(t),pd.DataFrame(list(a.values())),pd.DataFrame(),q


def test_corrected_fixture_inventory_is_legacy_minus_only_newer_count_gap(analysis):
    _,current,_,(corrections,*_)=analysis
    f,t,a,b,q=inventory_inputs(current);before=f.copy(deep=True)
    _,original=build_producers_over_quota_report(f,t,a,b,q,'2026-11-10')
    assert original['Inventory Birds']==1059266
    revised=f.copy(deep=True)
    for correction in corrections:
        mask=revised.FLOCK_ID.eq(correction['flock_id'])
        for field in correction['changed_fields']:revised.loc[mask,field]=correction['new'][field]
    result,summary=build_producers_over_quota_report(revised,t,a,b,q,'2026-11-10',mortality='0.4',quota_type='Egg Production')
    assert summary['Inventory Birds']==1052229==1052372-143
    assert {'40366','40369','40407','30407'}.isdisjoint(result['Permit No'])
    assert set(revised.FLOCK_ID)==set(f.FLOCK_ID)  # No missing flock is created.
    assert revised.PLACEMENT_DATE.equals(f.PLACEMENT_DATE)
    pd.testing.assert_frame_equal(f,before)


def test_user_difference_csv_is_exactly_the_same_17_row_evidence(analysis):
    reference=list(csv.DictReader((FIXTURES/'flock_differences_legacy_vs_new.csv').read_text(encoding='utf-8-sig').splitlines()))
    by_permit={r['permit']:r for r in reference}
    rows,_,differences,*_=analysis[3]
    assert {r['permit'] for r in differences}==set(by_permit)
    for row in rows:
        ref=by_permit[row['permit']]
        for field,before,after in [('EST_DISPOSAL','new_est_disposal','legacy_est_disposal'),
                                   ('DISPOSAL_DATE','new_actual_disposal','legacy_actual_disposal')]:
            assert row['old'][field]==(ref[before] or None)
            assert row['new'][field]==(ref[after] or None)


def test_actor_validation_and_declared_version_metadata(analysis,tmp_path):
    with pytest.raises(ValueError):generate(LEGACY,EXPORTED,tmp_path/'bad',actor_id='not-a-uuid')
    with pytest.raises(ValueError):generate(LEGACY,EXPORTED,tmp_path/'bad',actor_email='not-an-email')
    for row in analysis[3][0]:
        assert row['old']['UPDATED_AT']==UNKNOWN
        assert row['new']['UPDATED_AT']=='<UTC_EXECUTION_TIMESTAMP>'
    apply=generate_sql(analysis[3][0],'test-plan')
    assert apply.index("actor_id='__SET_APP_USER_ID__'")<apply.index('CREATE TABLE IF NOT EXISTS')
    assert 'f.PERMIT_NUMBER=\'30133\'' not in apply and 'f.PERMIT_NUMBER=\'30348\'' not in apply


def test_sql_delimiters_and_changing_inputs_leave_existing_plan_untouched(analysis,tmp_path,monkeypatch):
    import scripts.generate_flock_disposal_correction as module
    row=deepcopy(analysis[3][0][0]);row['account']='Bad $$ delimiter'
    with pytest.raises(ValueError,match='Dollar-quote'):generate_sql([row],'test-plan')
    with pytest.raises(ValueError,match='plan identifier'):generate_sql([analysis[3][0][0]],'bad\nDROP')
    folder=tmp_path/'review';folder.mkdir();sentinel=folder/'apply.sql';sentinel.write_text('original review')
    with pytest.raises(ValueError,match='Dollar-quote'):
        generate(LEGACY,EXPORTED,folder,actor_email='bad$$@example.test')
    assert sentinel.read_text()=='original review' and list(folder.iterdir())==[sentinel]
    legacy=tmp_path/LEGACY.name;legacy.write_bytes(LEGACY.read_bytes())
    exported=tmp_path/EXPORTED.name;exported.write_bytes(EXPORTED.read_bytes())
    original_read=module.read_inputs
    def changed(*args):
        result=original_read(*args);exported.write_bytes(exported.read_bytes()+b'\n');return result
    monkeypatch.setattr(module,'read_inputs',changed)
    with pytest.raises(RuntimeError,match='input changed'):generate(legacy,exported,folder)
    assert sentinel.read_text()=='original review' and list(folder.iterdir())==[sentinel]
