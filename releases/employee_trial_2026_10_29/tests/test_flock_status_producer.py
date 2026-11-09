"""Producer Status projection, real Bayview flock observations, offline only."""
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.security import Permission
from app.services.flock_reports import (
    STATUS_COLUMNS, build_flock_status_report, build_flock_status_by_producer_report,
)
from app.services.report_center import report_definition, report_csv, report_xlsx
from tests.test_flock_reports import flock, transaction
from tests.test_report_center import user

DAY = date(2026,11,6)


def bayview():
    accounts = pd.DataFrame([
        dict(ACCOUNT_ID='a',ORGANIZATION_NAME='Bayview Poultry Farm Ltd.',REGISTRATION_NUMBER='7038',PRODUCER_ROLE=True),
        dict(ACCOUNT_ID='b',ORGANIZATION_NAME='Other producer',REGISTRATION_NUMBER='9999',PRODUCER_ROLE=True)])
    flocks = pd.DataFrame([
        flock('40407',FACILITY_ID='two',HATCH_DATE='2026-09-08',PLACEMENT_DATE='2027-01-19',EST_DISPOSAL='2028-01-18'),
        flock('40382',FACILITY_ID='one',HATCH_DATE='2026-02-10',PLACEMENT_DATE='2026-06-23',EST_DISPOSAL='2027-06-22'),
        flock('40368',FACILITY_ID='two',HATCH_DATE='2025-08-26',PLACEMENT_DATE='2026-01-06',EST_DISPOSAL='2027-01-05'),
        flock('other',owner='b')])
    transactions = pd.DataFrame([
        transaction('delivery','40407','2026-09-08',TRANSACTION_TYPE='Delivery',QUANTITY=11000),
        transaction('count2','40382','2026-07-08',QUANTITY=6840),
        transaction('count1','40368','2026-07-08',QUANTITY=9988),
        transaction('other','other',str(DAY),QUANTITY=500)])
    facilities = pd.DataFrame([dict(FACILITY_ID='one',FACILITY_NAME='7038 - 1'),
                               dict(FACILITY_ID='two',FACILITY_NAME='7038 - 2')])
    # Synthetic remaining-province quota, to test the supplied allocation
    # without claiming to reconstruct the 24 underlying live positions.
    quotas = {'a':16152,'b':1027985-16152}
    return flocks,transactions,accounts,facilities,quotas


def test_bayview_legacy_rows_and_producer_summary():
    f,t,a,b,q = bayview()
    originals = [frame.copy(deep=True) for frame in (f,t,a,b)]
    result,summary = build_flock_status_by_producer_report(f,t,a,b,q,DAY,'a')
    assert list(result) == STATUS_COLUMNS
    assert result['Permit No'].tolist() == ['Total','40368','40382','40407']
    assert result.Account.tolist() == ['Bayview Poultry Farm Ltd.']*4
    assert result['Reg No'].tolist() == ['7038']*4
    assert result.Inventory.tolist() == [16560,9829,6731,0]
    assert result.Quota.tolist() == [16152]*4
    assert result['Up. Flocks'].tolist() == [11000,0,0,11000]
    assert result['Util.'].tolist() == ['102.53%','60.85%','41.67%','0.00%']
    assert result['Facility Name'].tolist()[1:] == ['7038 - 2','7038 - 1','7038 - 2']
    assert result['Placement Date'].tolist()[1:] == ['2026-01-06','2026-06-23','2027-01-19']
    assert result['Flock Age'].tolist()[1:] == [62,38,8]
    assert result['Hatch Date'].tolist()[1:] == ['2025-08-26','2026-02-10','2026-09-08']
    assert result['Disp. Date'].tolist()[1:] == ['2027-01-05','2027-06-22','2028-01-18']
    assert {key:summary[key] for key in ('Inventory Birds','NFPMC Allocation','Provincial Utilization',
        'Issuance for Province','Producers with Quota')} == {
        'Inventory Birds':16560,'NFPMC Allocation':1027985,'Provincial Utilization':'1.61%',
        'Issuance for Province':16152,'Producers with Quota':1}
    province,province_summary = build_flock_status_report(f,t,a,b,q,DAY)
    pd.testing.assert_frame_equal(result.reset_index(drop=True),province.loc[province['Reg No'].eq('7038')].reset_index(drop=True))
    assert summary['NFPMC Allocation'] == province_summary['NFPMC Allocation']
    assert province_summary['Inventory Birds'] == 17060
    for actual,before in zip((f,t,a,b),originals):
        pd.testing.assert_frame_equal(actual,before)


@pytest.mark.parametrize('own,other,allocation,issuance,count,util',[
    (None,100,None,None,0,'—'),(16152,None,None,16152,1,'—'),
    (0,100,100,0,0,'16560.00%'),(0,0,0,0,0,'—')])
def test_unknown_and_zero_quotas(own,other,allocation,issuance,count,util):
    f,t,a,b,_ = bayview()
    _,summary = build_flock_status_by_producer_report(f,t,a,b,{'a':own,'b':other},DAY,'a')
    assert summary['NFPMC Allocation'] == allocation
    assert summary['Issuance for Province'] == issuance
    assert summary['Producers with Quota'] == count
    assert summary['Provincial Utilization'] == util


def test_unknown_inventory_and_missing_other_account_quota_match_province():
    f,t,a,b,q = bayview()
    t = t.loc[t.FLOCK_ID.ne('40382')]
    q.pop('b')
    result,summary = build_flock_status_by_producer_report(f,t,a,b,q,DAY,'a')
    assert result.Inventory.tolist() == [9829,9829,'—',0]
    assert summary['Inventory Birds'] == 9829
    assert summary['NFPMC Allocation'] is None
    assert '1 flock Inventory value(s) excluded' in summary['Notes']


@pytest.mark.parametrize('identity',[None,'','missing'])
def test_empty_or_unavailable_account_selection(identity):
    f,t,a,b,q = bayview()
    result,summary = build_flock_status_by_producer_report(f,t,a,b,q,DAY,identity)
    assert result.empty and list(result) == STATUS_COLUMNS and summary is None


def test_account_without_flocks_and_duplicate_display_names_use_stable_id():
    f,t,a,b,q = bayview()
    a.loc[1,['ORGANIZATION_NAME','REGISTRATION_NUMBER']] = ['Bayview Poultry Farm Ltd.','7038']
    result,summary = build_flock_status_by_producer_report(f,t,a,b,q,DAY,'b')
    assert result['Permit No'].tolist() == ['Total','other']
    assert summary['Inventory Birds'] == 500
    result,summary = build_flock_status_by_producer_report(f.loc[f.ACCOUNT_ID.ne('b')],t,a,b,q,DAY,'b')
    assert result.empty and summary['Inventory Birds'] is None
    assert summary['Issuance for Province'] == q['b']


def test_catalog_and_formula_safe_exports():
    definition = report_definition('flock-status-producer')
    assert definition.name == 'Flock Status Report by Producer'
    assert definition.status == 'Available' and definition.permission == Permission.VIEW_REPORTS
    assert definition.export_formats == ('CSV','XLSX','PDF')
    f,t,a,b,q = bayview()
    a.loc[0,'ORGANIZATION_NAME'] = '=1+1'
    result,_ = build_flock_status_by_producer_report(f,t,a,b,q,DAY,'a')
    for frame in (pd.read_csv(BytesIO(report_csv(user(),result))),pd.read_excel(BytesIO(report_xlsx(user(),result)))):
        assert frame.Account.tolist() == ["'=1+1"]*4


def test_page_selection_summary_exports_and_empty_message(tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from data.repositories.mock import MockRepository
    from app.auth import get_auth_store
    root = Path(__file__).resolve().parents[1]
    app = authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    f,t,a,b,q = bayview()
    repo = MockRepository()
    repo.get_flocks,repo.get_flock_transactions = lambda:f,lambda:t
    repo.get_accounts,repo.get_facilities = lambda:a,lambda:b
    repo.get_quota_registrations = lambda:pd.DataFrame([
        dict(QUOTA_ID=identity,ACCOUNT_ID=identity,QUOTA_TYPE='Egg Production',STATUS='Active') for identity in q])
    repo.get_quota_transactions = lambda:pd.DataFrame([
        dict(QUOTA_TRANSACTION_ID=identity,QUOTA_ID=identity,OWNER_ACCOUNT_ID=identity,
            TRANSACTION_TYPE='Base',QUOTA_COUNT=value,EFFECTIVE_DATE='2026-01-01') for identity,value in q.items()])
    app.session_state['_base_repo'] = repo
    app.switch_page('app/pages/4_Reports.py').run()
    monkeypatch.setattr(get_auth_store(),'record_action',lambda *args,**kwargs:pytest.fail('Report must remain read-only'))
    app.session_state['report_center_open_report'] = 'flock-status-producer'
    app.run()
    assert not app.exception and not app.error
    assert any('Select an Account' in info.value for info in app.info)
    assert app.button(key='run_flock_status_producer').disabled
    assert not app.dataframe
    assert app.text_input(key='flock_status_producer_mortality').value == '0.4'
    assert app.selectbox(key='flock_status_producer_type').value == 'Egg Production'
    assert app.date_input(key='flock_status_producer_date').label == 'Report Date'
    app.selectbox(key='flock_status_producer_account').set_value('a')
    app.date_input(key='flock_status_producer_date').set_value(DAY)
    app.run()
    app.button(key='run_flock_status_producer').click().run()
    assert not app.exception and not app.error
    assert len(app.dataframe) == 1
    result = app.dataframe[0].value
    assert result['Permit No'].tolist() == ['Total','40368','40382','40407']
    assert 'FLOCK_ID' not in result
    assert {metric.label:metric.value for metric in app.metric} == {
        'Inventory Birds':'16560','NFPMC Allocation':'1027985','Provincial Utilization':'1.61%',
        'Issuance for Province':'16152','Producers with Quota':'1'}
    assert len(app.get('download_button')) == 3
    app.selectbox(key='flock_status_producer_account').set_value(None).run()
    assert not app.exception and not app.error and not app.dataframe
    assert any('Select an Account' in info.value for info in app.info)
