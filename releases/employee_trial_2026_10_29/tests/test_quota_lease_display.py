"""Synthetic read-only lease relationships; never connect to Snowflake."""
import datetime as dt
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from app.services.quota_lease_display import incoming_lease_activity, lease_activity
from app.services.report_center import build_quota_summary, build_quota_summary_details, report_csv
from app.services.flock_age_report import build_flock_age_quotas
from app.security import Role
from data.quota_position import load_rules
from data.repositories.snowflake import SnowflakeRepository
from tests.test_quota_leases import lease, pos
from tests.test_quota_lease_void import saved, void
from tests.test_quota_lease_adjustments import adjust
from tests.test_report_center import user
from tests.auth_support import authenticated_app

WHEN = dt.date(2026, 12, 23)
ROOT = Path(__file__).parents[1]


def incoming(repo, when=WHEN, quota='qb'):
    return incoming_lease_activity(repo.get_quota_registration(quota), repo.get_quota_registrations(),
        repo.get_quota_transactions(account_id='b'), repo.get_accounts(), when)


@pytest.mark.parametrize('change,quantity,end,status', [
    ('none','20','2027-01-10','Active'),
    ('partial','13','2027-01-10','Active · adjusted'),
    ('early','0','2026-12-22','Ended · early-ended'),
    ('void','0','2027-01-10','Voided'),
    ('full','0','2026-12-21','Ended · adjusted'),
])
def test_effective_values_reuse_calculation_resolver(change,quantity,end,status):
    repo, identity = saved()
    if change=='partial':adjust(repo,identity)
    if change=='early':adjust(repo,identity,'Ended early','2026-12-22',None)
    if change=='void':void(repo,identity)
    if change=='full':adjust(repo,identity,amount=20)
    before = deepcopy(repo._continuity_rows)
    frame = incoming(repo)
    row = frame.iloc[0]
    assert row['_LEASE_ID']==identity and row['Transaction Type']=='Lease (In)'
    assert row['Lessor Account']=='Synthetic a' and row['Start Date']=='2026-12-20'
    assert row['Current Quantity']==quantity and row['Effective End Date']==end and row['Status']==status
    assert pos(repo.get_quota_registrations(),repo.get_quota_transactions(),'b',WHEN)['net_position']==50+int(quantity)
    assert len(repo.get_quota_transactions(quota_id='qb'))==1
    assert repo._continuity_rows==before
    if change=='void':assert row['Note']=='No longer affects quota.'


def test_partial_return_is_not_applied_before_its_effective_day_and_future_is_scheduled():
    repo,identity=saved();adjust(repo,identity)
    assert incoming(repo,dt.date(2026,12,21)).iloc[0]['Current Quantity']=='20'
    future=incoming(repo,dt.date(2026,12,19)).iloc[0]
    assert future['Status']=='Scheduled · adjusted' and future['Current Quantity']=='0'


def test_legacy_rows_and_lessor_stored_rows_unchanged_no_registration_or_wrong_type():
    repo,identity=saved()
    legacy=[dict(lease(),QUOTA_TRANSACTION_ID='legacy-out',TRANSACTION_METHOD=None),
        dict(lease(),QUOTA_TRANSACTION_ID='legacy-in',TRANSACTION_METHOD=None,
            TRANSACTION_TYPE='Lease (In)',QUOTA_ID='qb',OWNER_ACCOUNT_ID='b',RELATED_ACCOUNT_ID='a')]
    repo._quota_transactions=pd.concat([repo._quota_transactions,pd.DataFrame(legacy)],ignore_index=True)
    before=repo.get_quota_transactions(quota_id='qa').copy(deep=True)
    assert incoming(repo)._LEASE_ID.tolist()==[identity]
    assert incoming(repo,quota='qa').empty
    assert incoming(repo,quota='missing').empty
    pd.testing.assert_frame_equal(before,repo.get_quota_transactions(quota_id='qa'))
    assert len(repo.get_quota_transactions(quota_id='qb'))==2
    repo._quota_registrations.loc[repo._quota_registrations.QUOTA_ID.eq('qb'),'QUOTA_TYPE']='Commercial Pullet Grower'
    assert incoming(repo).empty


def test_missing_names_and_invalid_evidence_are_displayed_without_assuming_quota():
    row=dict(lease(),_LEASE_ADJUSTMENTS=None)
    frame=lease_activity([row],pd.DataFrame(),WHEN,incoming=True)
    assert frame.iloc[0]['Status']=='Needs review' and frame.iloc[0]['Current Quantity']=='—'
    assert 'could not be verified' in frame.iloc[0]['Note']
    for field in ('OWNER_ACCOUNT_ID','EFFECTIVE_DATE','END_DATE','QUOTA_COUNT'):
        row=dict(lease(),**{field:None})
        result=lease_activity([row],pd.DataFrame(),WHEN,incoming=True)
        assert not any(token in str(result.to_dict('records')) for token in ('nan','NaT','<NA>'))


def test_display_does_not_mutate_data_or_change_any_quota_report_numbers():
    repo,identity=saved();adjust(repo,identity)
    regs,tx,accounts=repo.get_quota_registrations(),repo.get_quota_transactions(),repo.get_accounts()
    kwargs=dict(user=user(),as_of_date=WHEN,quota_type='Egg Production')
    before=[report_csv(user(),build_quota_summary(repo,**kwargs)[0]),report_csv(user(),build_quota_summary_details(repo,**kwargs)[0])]
    quotas=build_flock_age_quotas(regs,tx,accounts,WHEN,set(),load_rules())
    snapshot=repo._quota_transactions.copy(deep=True)
    incoming(repo)
    lease_activity(repo.get_quota_transactions(quota_id='qa'),accounts,WHEN,incoming=False)
    assert before==[report_csv(user(),build_quota_summary(repo,**kwargs)[0]),report_csv(user(),build_quota_summary_details(repo,**kwargs)[0])]
    assert quotas==build_flock_age_quotas(repo.get_quota_registrations(),repo.get_quota_transactions(),accounts,WHEN,set(),load_rules())
    pd.testing.assert_frame_equal(snapshot,repo._quota_transactions)


def test_existing_snowflake_read_is_account_bounded_and_resolves_adjustments_offline(monkeypatch):
    memory,identity=saved();adjust(memory,identity)
    calls=[];snow=SnowflakeRepository()
    def query(sql,params=None):
        calls.append((sql,params))
        return memory._quota_transactions.copy(deep=True)
    monkeypatch.setattr(snow,'_query',query)
    class Executor:
        def query(self,sql,params):
            calls.append((sql,params))
            return pd.DataFrame([row for row in memory._continuity_rows['RECORD_REVISION']
                if row['CHANGE_KIND'] in {'Ended early','Partial return'}])
    monkeypatch.setattr(snow,'_executor',lambda:Executor())
    tx=snow.get_quota_transactions(account_id='b')
    result=incoming_lease_activity(memory.get_quota_registration('qb'),memory.get_quota_registrations(),tx,memory.get_accounts(),WHEN)
    assert result.iloc[0]['Current Quantity']=='13'
    assert calls[0][1]==('b','b') and 'OWNER_ACCOUNT_ID = %s OR qt.RELATED_ACCOUNT_ID = %s' in calls[0][0]
    assert len(calls)==2 and 'RECORD_REVISION' in calls[1][0]


def page(repo,tmp_path,monkeypatch,entrypoint='streamlit_app.py',quota='qb',role=Role.ADMIN):
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local');monkeypatch.setenv('REPOSITORY_MODE','mock')
    monkeypatch.setattr('data.business_time.halifax_today',lambda:WHEN)
    app=authenticated_app(ROOT/entrypoint,tmp_path,monkeypatch,role)
    app.session_state['_base_repo']=repo
    app.session_state['_efns_record_7_Quota_Registrations_view']='detail'
    app.session_state['_efns_record_7_Quota_Registrations_id']=quota
    prefix='app/pages/' if entrypoint=='streamlit_app.py' else 'pages/'
    return app.switch_page(prefix+'7_Quota_Registrations.py').run()


@pytest.mark.parametrize('entrypoint',['streamlit_app.py','app/Home.py'])
@pytest.mark.parametrize('role',[Role.ADMIN,Role.REPORTING_VIEWER])
def test_lessee_page_stored_count_separate_derived_section_and_original_link(tmp_path,monkeypatch,entrypoint,role):
    repo,identity=saved();adjust(repo,identity)
    original=repo._quota_transactions.copy(deep=True)
    app=page(repo,tmp_path,monkeypatch,entrypoint,role=role)
    assert not app.exception and not app.error
    markdown=[item.value for item in app.markdown]
    assert '**Quota Transactions (1)**' in markdown
    assert '**Leased in (from lease records) (1)**' in markdown
    frame=next(item.value for item in app.dataframe if 'Current Quantity' in item.value)
    assert frame.iloc[0]['Current Quantity']=='13' and frame.iloc[0]['Transaction Type']=='Lease (In)'
    assert not app.get('data_editor')
    if role==Role.REPORTING_VIEWER:
        assert next(button for button in app.button if button.key=='quota_reg_record_edit').disabled
    monkeypatch.setattr('app.navigation.selected_row_index',lambda key:0 if key=='quota_incoming_leases' else None)
    app.run()
    next(button for button in app.button if button.key=='quota_incoming_leases_open').click().run()
    assert not app.exception
    assert app.session_state['_efns_record_8_Quota_Transactions_id']==identity
    assert any(item.value=='**Current lease status (1)**' for item in app.markdown)
    if role==Role.REPORTING_VIEWER:
        assert next(button for button in app.button if button.key=='quota_tx_record_edit').disabled
        assert not any(button.label in {'Save lease adjustment','Void lease'} for button in app.button)
    pd.testing.assert_frame_equal(original,repo._quota_transactions)


def test_lessor_status_visible_without_changing_stored_table_and_missing_registration(tmp_path,monkeypatch):
    repo,identity=saved();void(repo,identity)
    app=page(repo,tmp_path,monkeypatch,quota='qa')
    assert not app.exception
    assert any(item.value=='**Quota Transactions (2)**' for item in app.markdown)
    assert any(item.value=='**Leased in (from lease records) (0)**' for item in app.markdown)
    frame=next(item.value for item in app.dataframe if 'Current Quantity' in item.value)
    assert frame.iloc[0]['Status']=='Voided' and frame.iloc[0]['Current Quantity']=='0'
    app=page(repo,tmp_path,monkeypatch,quota='missing')
    assert not app.exception and any('Quota Registration Not Found' in item.value for item in app.markdown)
