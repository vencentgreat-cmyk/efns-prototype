"""Confirmed legacy cases, scoped fake SQL and unavailable-evidence behavior."""
import json
from copy import deepcopy

import pandas as pd
import pytest

from app.services.quota_state import get_inactive_quota_transaction_ids
from app.services.flock_age_report import build_flock_age_quotas, build_flock_age_report
from data.confirmed_quota_position import confirmed_quota_position
from data.quota_position import load_rules
from data.repositories.mock import MockRepository
from tests.test_report_center import user
from tests.test_flock_current_report import sources, FIXTURES

DAY = '2026-11-05'


def tx(identity, kind, amount, effective='2020-02-23', **extra):
    return dict(QUOTA_TRANSACTION_ID=identity,QUOTA_ID='q',OWNER_ACCOUNT_ID='owner',
        TRANSACTION_TYPE=kind,QUOTA_COUNT=amount,EFFECTIVE_DATE=effective,
        CREATED_AT=effective+'T12:00:00',END_DATE=None,**extra)


def regs():
    return [dict(QUOTA_ID='q',ACCOUNT_ID='owner',QUOTA_TYPE='Egg Production',STATUS='Active')]


def position(rows, inactive=(), registrations=None, date=DAY):
    return confirmed_quota_position(registrations or regs(),rows,'owner','Egg Production',
        date,None if inactive is None else set(inactive),load_rules())


def real_case(number):
    if number in {'7038','7176'}:
        # Supplied facts give duplicate Adjustment and final net, not all other
        # transactions. This synthetic Base represents their remaining subtotal.
        net, adjustment = (16152,27) if number=='7038' else (1319,1)
        return [tx('base','Base',net-adjustment,'2019-01-01'),
                tx('active-adjustment','Adjustment',adjustment),
                tx('inactive-adjustment','Adjustment',adjustment)], {'inactive-adjustment'}, net
    if number=='7402':
        rows=[tx('b1','Base',500,'2017-06-27'),tx('b2','Base',1500,'2019-02-24'),
              tx('pre-base','Adjustment',500,'2017-06-24')]
        values=[41,3,11,1,19,38,36,3,65,34,39]
        return rows+[tx('adjustment-'+str(i),'Adjustment',v,'2021-01-01') for i,v in enumerate(values)],set(),1790
    if number=='7404':
        rows=[tx('base','Base',1500,'2020-01-01'),tx('inactive-base','Base',1500,'2020-01-01'),
              tx('inactive-41','Adjustment',41,'2019-02-24'),tx('active-41','Adjustment',41,'2020-01-01'),
              dict(tx('expired','Lease (In)',1139,'2025-01-01'),END_DATE='2026-06-01')]
        values=[3,11,1,19,38,3,36,65,34,39]
        return rows+[tx('adjustment-'+str(i),'Adjustment',v,'2021-01-01') for i,v in enumerate(values)],{'inactive-base','inactive-41'},1790
    return [tx('base','Base',15511,'2019-01-01'),tx('adjustment','Adjustment',8502),
            tx('buy','Purchase',15005),tx('sell','Sale',25271),tx('out','Lease (Out)',1247)],set(),12500


@pytest.mark.parametrize('number',['7038','7176','7402','7404','7106'])
def test_five_legacy_transaction_cases(number):
    rows,inactive,expected=real_case(number)
    before=deepcopy(rows)
    result=position(rows,inactive)
    assert not result['reasons']
    assert result['net_position']==expected
    assert rows==before
    if number in {'7038','7176'}:
        assert position(rows)['net_position']>expected


def test_base_tiebreaker_and_same_day_activity():
    rows=[tx('b1','Base',500,'2020-01-01'),
          dict(tx('b2','Base',1500,'2020-01-01'),CREATED_AT='2020-01-01T13:00:00'),
          tx('same-day','Adjustment',41,'2020-01-01')]
    assert position(rows)['net_position']==1541
    rows[1]['CREATED_AT']=rows[0]['CREATED_AT']
    assert position(rows)['net_position'] is None
    rows[1]['CREATED_AT']=None
    assert position(rows)['net_position'] is None


@pytest.mark.parametrize('number,components,expected',[
    ('7172',[('Adjustment',15343),('Purchase',45659)],61002),
    ('7173',[('Adjustment',62406),('Purchase',172507)],234913),
    ('7174',[('Adjustment',4178),('Purchase',12557)],16735),
    ('7177',[('Adjustment',2680),('Purchase',24466),('Lease (In)',3452)],30598),
    ('7178',[('Purchase',45495)],45495),
    # Remaining subtotal is synthetic: only duplicate +1 and net were supplied.
    ('7176',[('Adjustment',1318),('Adjustment',1)],1319),
])
def test_legacy_cases_without_active_base(number,components,expected):
    rows=[tx(number+'-'+str(i),kind,value) for i,(kind,value) in enumerate(components)]
    inactive=set()
    if number=='7176':
        rows.append(tx('inactive-duplicate','Adjustment',1))
        inactive.add('inactive-duplicate')
    result=position(rows,inactive)
    assert result['net_position']==expected
    assert not result['reasons'] and result['selected_bases']=={}


def test_no_active_base_still_applies_signs_dates_and_inactive_exclusion():
    rows=[tx('inactive-base','Base',9999,'2019-01-01'),
          tx('future-base','Base',9999,'2027-01-01'),
          tx('adjustment','Adjustment',10),tx('global','Global Adjustment',2),
          tx('purchase','Purchase',20),tx('sale','Sale',3),
          tx('lease-in','Lease (In)',7),tx('lease-out','Lease (Out)',4),
          dict(tx('expired','Lease (In)',999),END_DATE='2026-11-04'),
          tx('terminate','Terminate Quota',999),tx('allocation','National Allocation',999)]
    assert position(rows,{'inactive-base'})['net_position']==32
    assert position([])['net_position']==0


def test_lease_boundaries_signs_allocation_exclusions_and_future_rows():
    rows=[tx('base','Base',100,'2019-01-01'),tx('global','Global Adjustment',5),
          tx('adjustment','Adjustment',-2),tx('in','Lease (In)',7),
          dict(tx('out','Lease (Out)',3),END_DATE=DAY),
          dict(tx('expired','Lease (In)',999),END_DATE='2026-11-04'),
          tx('future','Purchase',999,'2027-01-01'),tx('terminate','Terminate Quota',999),
          tx('national','National Allocation',999),tx('provincial','Provincial Allocation',999)]
    assert position(rows)['net_position']==107
    assert position(rows,date='2026-11-06')['net_position']==110


def test_only_active_registrations_and_owner_transactions_count():
    registrations=regs()+[dict(regs()[0],QUOTA_ID='inactive-q',STATUS='Inactive')]
    rows=[tx('base','Base',100),dict(tx('foreign','Purchase',999),OWNER_ACCOUNT_ID='other'),
          dict(tx('inactive','Base',999),QUOTA_ID='inactive-q')]
    assert position(rows,registrations=registrations)['net_position']==100
    assert position(rows,None)['net_position'] is None
    assert position([tx('no-base','Purchase',100)])['net_position']==100


def test_missing_evidence_unconfirmed_rules_or_bad_quantity_stays_unknown():
    assert position([tx('base','Base',100)],None)['net_position'] is None
    assert position([tx('base','Base','NaN')])['net_position'] is None
    rules=load_rules()
    rules['status']='PENDING'
    assert confirmed_quota_position(regs(),[tx('base','Base',100)],'owner','Egg Production',DAY,set(),rules)['net_position'] is None


class SQL:
    _is_memory=False
    schema_raw='RAW'
    def __init__(self,rows=None,error=False):
        self.rows=rows or []
        self.calls=[]
        self.error=error
    def _table(self,table,schema):
        return 'EFNS_DEV.'+schema+'.'+table
    def _query(self,sql,params):
        self.calls.append((sql,params))
        if self.error:
            raise RuntimeError('Synthetic query unavailable')
        return pd.DataFrame(self.rows)


def test_state_reader_is_read_only_parameterized_and_scoped():
    repo=SQL([dict(TRANSACTION_ID='A',TRANSACTION_STATE='inactive'),
              dict(TRANSACTION_ID='B',TRANSACTION_STATE='active')])
    assert get_inactive_quota_transaction_ids(repo,['A','b','new'],user=user())=={'a'}
    sql,params=repo.calls[0]
    assert sql.startswith('SELECT ')
    assert 'RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR' in sql
    assert 'SOURCE_ENTITY=%s' in sql and 'UPPER(TARGET_ID) IN' in sql
    assert params[0]=='QUOTA_TRANSACTION'
    assert json.loads(params[1])==['A','B','NEW']
    assert 'SELECT *' not in sql
    assert get_inactive_quota_transaction_ids(SQL(),['new'],user=user())==set()
    assert get_inactive_quota_transaction_ids(MockRepository(),['any'],user=user())==set()


@pytest.mark.parametrize('repo',[SQL(error=True),SQL([dict(TRANSACTION_ID='A',TRANSACTION_STATE=None)]),
    SQL([dict(TRANSACTION_ID='A',TRANSACTION_STATE='active'),dict(TRANSACTION_ID='A',TRANSACTION_STATE='inactive')])])
def test_state_reader_unavailable_unknown_or_conflicting_evidence(repo):
    assert get_inactive_quota_transaction_ids(repo,['A'],user=user()) is None


def test_age_report_uses_confirmed_quota_and_unknown_state_stays_unknown():
    rows,inactive,expected=real_case('7402')
    f,t,a=sources([FIXTURES[0]])
    f['ACCOUNT_ID']='owner'
    a['ACCOUNT_ID']='owner'
    a['PRODUCER_ROLE']=True
    quotas,count,reasons=build_flock_age_quotas(pd.DataFrame(regs()),pd.DataFrame(rows),a,DAY,inactive,load_rules())
    assert quotas=={'owner':expected} and count==1 and not reasons['owner']
    report,summary=build_flock_age_report(f,t,a,pd.DataFrame(),quotas,DAY)
    assert report.iloc[0].Quota==1790 and report.iloc[0]['Util.']!='—'
    assert summary['NFPMC Allocation']==1790
    quotas,_,_=build_flock_age_quotas(pd.DataFrame(regs()),pd.DataFrame(rows),a,DAY,None,load_rules())
    report,summary=build_flock_age_report(f,t,a,pd.DataFrame(),quotas,DAY)
    assert report.iloc[0].Quota==report.iloc[0]['Util.']=='—'
    assert summary['NFPMC Allocation'] is None


def test_inactive_viewer_cannot_read_raw_state():
    from app.security import AuthorizationError
    repo=SQL()
    with pytest.raises(AuthorizationError):
        get_inactive_quota_transaction_ids(repo,['A'],user=user(active=False))
    assert repo.calls==[]


def test_producer_count_excludes_zero_negative_unknown_and_non_producer_positions():
    identities=['positive','zero','negative','unknown','not-producer']
    registrations=pd.DataFrame([dict(QUOTA_ID=n,ACCOUNT_ID=n,QUOTA_TYPE='Egg Production',STATUS='Active') for n in identities])
    rows=[]
    for identity,value in zip(identities,[10,0,-2,None,20]):
        rows.append(dict(tx(identity,'Adjustment',value),QUOTA_ID=identity,OWNER_ACCOUNT_ID=identity))
    accounts=pd.DataFrame([dict(ACCOUNT_ID=n,PRODUCER_ROLE=n!='not-producer') for n in identities])
    quotas,count,_=build_flock_age_quotas(registrations,pd.DataFrame(rows),accounts,DAY,set(),load_rules())
    assert quotas=={'positive':10,'zero':0,'negative':-2,'unknown':None,'not-producer':20}
    assert count==1
    _,summary=build_flock_age_report(pd.DataFrame(),pd.DataFrame(),accounts,pd.DataFrame(),quotas,DAY)
    assert summary['Producers with Quota']==1


def test_flock_age_ui_computes_quota_from_transactions(tmp_path,monkeypatch):
    from pathlib import Path
    from tests.auth_support import authenticated_app
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    f,t,a=sources([FIXTURES[0]])
    f['ACCOUNT_ID']='owner'
    a['ACCOUNT_ID']='owner'
    a['PRODUCER_ROLE']=True
    rows,_,_=real_case('7402')
    repo=MockRepository()
    repo.get_flocks=lambda:f
    repo.get_flock_transactions=lambda:t
    repo.get_accounts=lambda:a
    repo.get_facilities=lambda:pd.DataFrame()
    repo.get_quota_registrations=lambda:pd.DataFrame(regs())
    repo.get_quota_transactions=lambda:pd.DataFrame(rows)
    repo.get_quota_summary=lambda *args,**kwargs:pytest.fail('Age report must use confirmed transactions')
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    app.session_state['report_center_open_report']='flock-age'
    app.run()
    app.date_input(key='flock_age_date').set_value(pd.Timestamp(DAY).date())
    app.button(key='run_flock_age').click().run()
    assert not app.exception and not app.error
    assert app.dataframe[0].value.iloc[0].Quota==1790
    assert app.dataframe[0].value.iloc[0]['Util.']!='—'
