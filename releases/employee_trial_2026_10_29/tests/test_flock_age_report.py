"""User-supplied legacy values plus explicit synthetic quota-provider fixtures."""
from io import BytesIO
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from app.services.flock_age_report import build_flock_age_report, quota_from_summary
from app.services.flock_current_report import build_flock_current_report, effective_disposal_date, flock_is_in_current_report
from app.services.report_center import build_quota_summary, report_csv, report_xlsx
from data.repositories.mock import MockRepository
from tests.test_report_center import user
from tests.test_flock_current_report import sources, FIXTURES

DAY = pd.Timestamp('2026-11-05').date()
QUOTAS = dict(zip('7159 7177 7107 7167 7038 7174 7022 7165 7113 7178 7050 7161 7173 7158 7168 7169 7176 7078 7101 7065 7172 7402 7106 7404'.split(),
    [42980,30598,77862,41921,16152,16735,34526,15311,27703,45495,33823,16512,234913,40751,55171,74316,1319,57600,46234,40981,61002,1790,12500,1790]))
NEW = [
    ('40394','2026-06-01','2026-10-12','2026-10-20',45773,22,45676,0),
    ('40375','2025-11-10','2026-03-23','2026-10-02',21194,51,21099,0),
    ('40362','2025-07-07','2025-11-17','2026-10-19',102076,69,101847,0),
]
KNOWN = [tuple(list(r[:6])+[{'40368':9830,'40382':6732,'40390':12383,'40407':0}[r[0]],r[7]])
         for r in FIXTURES if r[0] in {'40368','40382','40390','40407'}]


@pytest.mark.parametrize('fixture',NEW+KNOWN)
def test_legacy_age_inventory_and_shared_current_calculations(fixture):
    f,t,a=sources([fixture])
    f['FACILITY_ID']='facility'
    if fixture[0]=='40375':
        f['EST_DISPOSAL']=None
        f['DISPOSAL_DATE']='2027-03-22'  # Stored date; legacy May 27 discrepancy is open.
    if fixture[0]=='40362':
        f['EST_DISPOSAL']='2026-11-16'
        f['DISPOSAL_DATE']='2027-01-07'
    if fixture[0]=='40394':
        f['EST_DISPOSAL']='2027-10-11'
    facility=pd.DataFrame([dict(FACILITY_ID='facility',FACILITY_NAME='Synthetic barn')])
    result,_=build_flock_age_report(f,t,a,facility,{'bayview':77862},DAY)
    row=result.iloc[0]
    assert (row['Flock Age'],row.Inventory,row['Up. Flocks'])==fixture[5:]
    assert row['Facility name']=='Synthetic barn'
    assert row.Inventory==build_flock_current_report(f,t,a,DAY).iloc[0].Inventory
    if fixture[0]=='40375':
        assert row['Util.']=='27.10%'
        assert row['Disp. Date']=='2027-03-22'
    if fixture[0]=='40362':
        assert row['Disp. Date']=='2027-01-07'
    if fixture[0]=='40394':
        assert row['Disp. Date']=='2027-10-11'


@pytest.mark.parametrize('number,hatch,placement,estimate,actual',[
    ('40356','2025-05-26','2025-10-06','2026-10-05','2026-12-03'),
    ('40359','2025-06-16','2025-10-27','2026-10-26','2026-12-03'),
    ('40362','2025-07-07','2025-11-17','2026-11-16','2027-01-07'),
])
def test_actual_disposal_overrides_estimate_for_inclusion_and_display(number,hatch,placement,estimate,actual):
    f,t,a=sources([(number,hatch,placement,'2026-11-01',100,0,0,0)])
    f['EST_DISPOSAL']=estimate
    f['DISPOSAL_DATE']=actual
    row=f.iloc[0].to_dict()
    assert flock_is_in_current_report(row,DAY,'Egg Production')
    assert effective_disposal_date(row).isoformat()==actual
    assert build_flock_current_report(f,t,a,DAY).iloc[0]['Disp. Date']==actual
    assert not flock_is_in_current_report(row,pd.Timestamp(actual).date(),'Egg Production')


def test_24_supplied_quota_values_are_inputs_not_claimed_repository_calculations():
    # Provider fixture injects issuance into the existing summary interface.
    class Provider:
        def get_quota_summary(self,*args,**kwargs):
            return pd.DataFrame([dict(QUOTA_ID=number,ACCOUNT_ID=number,REGISTRATION_NUMBER=number,
                ACCOUNT_NAME=number,PRODUCER_ROLE=True,ISSUANCE=value) for number,value in QUOTAS.items()])
    quotas={}
    for number,value in QUOTAS.items():
        class One(Provider):
            def get_quota_summary(self,*args,**kwargs):
                return super().get_quota_summary().loc[lambda frame:frame.ACCOUNT_ID.eq(number)]
        frame=One().get_quota_summary()
        metrics={'total_issuance':value}
        quotas[number]=quota_from_summary(frame,metrics)
        assert quotas[number]==value
    f,t,a=sources([NEW[1]])
    a.loc[0,'ACCOUNT_ID']='7107'
    f.loc[0,'ACCOUNT_ID']='7107'
    a=pd.DataFrame([dict(ACCOUNT_ID=n,ORGANIZATION_NAME=n,REGISTRATION_NUMBER=n,PRODUCER_ROLE=True) for n in QUOTAS])
    result,summary=build_flock_age_report(f,t,a,pd.DataFrame(),quotas,DAY)
    assert summary['NFPMC Allocation']==sum(QUOTAS.values())
    assert summary['Issuance for Province']==sum(QUOTAS.values())
    assert summary['Producers with Quota']==24
    assert result.iloc[0]['Util.']=='27.10%'
    assert result.iloc[-1].Quota==77862


def test_mock_without_owner_transactions_has_confirmed_zero_positions():
    repo=MockRepository()
    template=repo._quota_registrations.iloc[0].to_dict()
    account=repo._accounts.iloc[0].to_dict()
    repo._accounts=pd.DataFrame([dict(account,ACCOUNT_ID=n,REGISTRATION_NUMBER=n) for n in QUOTAS])
    repo._quota_registrations=pd.DataFrame([dict(template,QUOTA_ID=n,ACCOUNT_ID=n,
        QUOTA_TYPE='Egg Production',STATUS='Active',EFFECTIVE_DATE=None,END_DATE=None) for n in QUOTAS])
    for number in QUOTAS:
        frame,metrics=build_quota_summary(repo,user=user(),as_of_date=DAY,quota_type='Egg Production',account_id=number)
        assert not frame.empty
        assert metrics['total_issuance'] == 0
        assert frame.iloc[1]['Issuance'] == 0


def test_quota_once_per_account_unknowns_special_permit_and_exports():
    f,t,a=sources(NEW[:2])
    f.loc[1,'FLOCK_QUOTA_TYPE']='Special Permit'
    result,summary=build_flock_age_report(f,t,a,pd.DataFrame(),{'bayview':None},DAY,quota_type='All')
    assert len(result)==2
    assert result['Quota'].tolist()==['—','—']
    assert result['Util.'].tolist()==['—','—']
    assert summary['NFPMC Allocation'] is None
    assert summary['Producers with Quota']==0
    f.loc[1,'FLOCK_QUOTA_TYPE']='Egg Production'
    a.loc[0,'ORGANIZATION_NAME']='=1+1'
    result,summary=build_flock_age_report(f,t,a,pd.DataFrame(),{'bayview':77862},DAY)
    assert result.iloc[-1]['Quota']==77862
    assert summary['NFPMC Allocation']==77862
    assert result.iloc[-1].Inventory==sum(result.iloc[:-1].Inventory)
    assert pd.read_csv(BytesIO(report_csv(user(),result))).iloc[0].Account=="'=1+1"
    assert pd.read_excel(BytesIO(report_xlsx(user(),result))).iloc[0].Account=="'=1+1"


def test_total_notes_omit_zero_exclusions_but_keep_missing_quota_and_inventory():
    f,t,a=sources([NEW[0]])
    result,_=build_flock_age_report(f,t,a,pd.DataFrame(),{'bayview':100},DAY)
    assert result.iloc[-1].Notes==''
    result,_=build_flock_age_report(f,t,a,pd.DataFrame(),{'bayview':None},DAY)
    assert result.iloc[-1].Notes=='Quota position unavailable'
    result,_=build_flock_age_report(f,t.iloc[:0],a,pd.DataFrame(),{'bayview':100},DAY)
    assert result.iloc[-1].Notes=='Excludes 1 flock(s) without known Inventory'


@pytest.mark.parametrize('report_id',['flock-age','flock-current-producer'])
def test_new_reports_render_results_without_audit_writes(report_id,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from app.auth import get_auth_store
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    f,t,a=sources([NEW[0]])
    repo=MockRepository()
    repo.get_flocks=lambda: f
    repo.get_flock_transactions=lambda: t
    repo.get_accounts=lambda: a
    repo.get_facilities=lambda: pd.DataFrame()
    repo.get_quota_summary=lambda *args,**kwargs: pd.DataFrame([
        dict(QUOTA_ID='q',ACCOUNT_ID='bayview',REGISTRATION_NUMBER='123',ACCOUNT_NAME='Bayview',PRODUCER_ROLE=True,ISSUANCE=None)])
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    monkeypatch.setattr(get_auth_store(),'record_action',lambda *args,**kwargs: pytest.fail('No audit writes'))
    app.session_state['report_center_open_report']=report_id
    app.run()
    prefix='flock_age' if report_id=='flock-age' else 'flock_current_producer'
    app.date_input(key=prefix+'_date').set_value(DAY)
    app.button(key='run_'+prefix).click().run()
    assert not app.exception and not app.error
    assert len(app.dataframe)==1
    assert app.dataframe[0].value.iloc[0]['Inventory']==45676
    assert 'FLOCK_ID' not in app.dataframe[0].value
    if report_id=='flock-age':
        assert app.dataframe[0].value.iloc[0]['Quota']=='—'
        assert app.dataframe[0].value.iloc[0]['Util.']=='—'


def test_by_producer_limits_report_to_selected_account(tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    f,t,a=sources(NEW[:2])
    f.loc[1,'ACCOUNT_ID']='other'
    a=pd.concat([a,pd.DataFrame([dict(ACCOUNT_ID='other',ORGANIZATION_NAME='Other',REGISTRATION_NUMBER='456')])])
    repo=MockRepository()
    repo.get_flocks=lambda:f
    repo.get_flock_transactions=lambda:t
    repo.get_accounts=lambda:a
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    app.session_state['report_center_open_report']='flock-current-producer'
    app.run()
    app.selectbox(key='flock_current_producer_account').select('other')
    app.date_input(key='flock_current_producer_date').set_value(DAY)
    app.button(key='run_flock_current_producer').click().run()
    assert not app.exception and not app.error
    details=app.dataframe[0].value
    assert details.loc[details.Account=='Other','Permit No'].tolist()==['40375']
    assert '40394' not in details['Permit No'].tolist()
