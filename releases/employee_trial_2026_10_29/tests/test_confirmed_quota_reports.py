"""Offline confirmed quota reports; supplied aggregates are not live-data verification."""
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.report_center import (build_quota_summary, build_quota_summary_details,
    QUOTA_ACCOUNT_COLUMNS, QUOTA_DETAIL_COLUMNS, report_definition, report_csv, report_xlsx)
from data.confirmed_quota_position import confirmed_quota_position, INCREASING_TYPES
from data.quota_position import load_rules
from app.security import AuthorizationError
from tests.test_report_center import user

DAY = date(2026,11,6)
LEGACY_NET = dict(zip('7022 7038 7050 7065 7078 7101 7106 7107 7113 7114 7128 7158 7159 7161 7165 7167 7168 7169 7172 7173 7174 7176 7177 7178 7326 7402 7404'.split(),
    [34526,16152,33823,40981,57600,46234,12500,77862,27703,0,0,40751,42980,16512,15311,41921,55171,74316,61002,234913,16735,1319,30598,45495,0,1790,1790]))
LEGACY_GROSS = {
    '7022': [22044,8307,3500,675,None], '7106':[15511,7697,15005,805,None],
    '7114':[8456,271,None,128,None], '7165':[4367,2722,3578,241,4403],
    '7172':[None,14393,45659,950,None], '7173':[None,57201,172507,5205,None],
    '7177':[None,2680,24466,None,3452], '7178':[None,None,45495,None,None],
    '7326':[None,None,390,2,None]}


def tx(identity,owner,kind,value,**extra):
    return dict(dict(QUOTA_TRANSACTION_ID=identity,QUOTA_ID=owner,OWNER_ACCOUNT_ID=owner,
        TRANSACTION_TYPE=kind,QUOTA_COUNT=value,EFFECTIVE_DATE='2020-01-01',END_DATE=None),**extra)


class Repository:
    _is_memory = True
    def __init__(self,values=None):
        values = values or {'a':100}
        self.accounts = pd.DataFrame([dict(ACCOUNT_ID=n,REGISTRATION_NUMBER=n,ORGANIZATION_NAME=n,
            ADDRESS_LINE1='Account address',CITY='City',PROVINCE='NS',POSTAL_CODE='B0N 1T0',CONTACT_PHONE='phone',FAX='') for n in values])
        self.registrations = pd.DataFrame([dict(QUOTA_ID=n,ACCOUNT_ID=n,QUOTA_TYPE='Egg Production',STATUS='Active',
            EFFECTIVE_DATE='2200-01-01',END_DATE='2000-01-01') for n in values])
        # Synthetic Base observations seeded from supplied net aggregates.
        self.transactions = pd.DataFrame([tx(n,n,'Base',value) for n,value in values.items()])
    def get_accounts(self): return self.accounts.copy(deep=True)
    def get_quota_registrations(self): return self.registrations.copy(deep=True)
    def get_quota_transactions(self): return self.transactions.copy(deep=True)


def report(repo,builder=build_quota_summary,**kwargs):
    return builder(repo,user=user(),as_of_date=DAY,quota_type='Egg Production',**kwargs)


def test_27_supplied_net_aggregates_zero_rows_totals_and_account_addresses():
    repo = Repository(dict(reversed(list(LEGACY_NET.items()))))
    repo.accounts.loc[repo.accounts.ACCOUNT_ID.eq('7022'),['ORGANIZATION_NAME','ADDRESS_LINE1','CITY','CONTACT_PHONE']] = ['CDS Poultry Ltd.','7580 Hwy 215','Maitland','902-261-2823']
    repo.accounts.loc[repo.accounts.ACCOUNT_ID.eq('7101'),['ORGANIZATION_NAME','ADDRESS_LINE1','CITY','CONTACT_PHONE','FAX']] = ['Ross Cox Poultry Farm Ltd.','7580 Highway 215','Stirling Brook','902 261-2823','902 261-2409']
    result,metrics = report(repo)
    assert list(result) == [*QUOTA_ACCOUNT_COLUMNS,'Issuance']
    assert len(result) == 28 and metrics == {'producer_count':24,'total_issuance':1027985,'notes':[]}
    assert result.iloc[0]['Account Name'] == 'Producers: 24' and result.iloc[0].Issuance == 1027985
    assert result['Reg No'].tolist()[1:] == list(LEGACY_NET)
    assert dict(zip(result['Reg No'][1:],result.Issuance[1:])) == LEGACY_NET
    indexed = result.set_index('Reg No')
    assert indexed.loc['7022',QUOTA_ACCOUNT_COLUMNS[1:]].tolist() == ['CDS Poultry Ltd.','7580 Hwy 215','Maitland','NS','B0N 1T0','902-261-2823','']
    assert indexed.loc['7101','Fax'] == '902 261-2409'


def test_supplied_gross_type_fixtures_and_total_once_per_account():
    repo = Repository({n:0 for n in LEGACY_GROSS})
    repo.transactions = pd.DataFrame([tx(n+kind,n,kind,value) for n,values in LEGACY_GROSS.items()
        for kind,value in zip(INCREASING_TYPES,values) if value is not None])
    result,metrics = report(repo,build_quota_summary_details)
    assert list(result) == QUOTA_DETAIL_COLUMNS
    expected = {'7022':34526,'7106':39018,'7114':8855,'7165':15311,'7172':61002,
                '7173':234913,'7177':30598,'7178':45495,'7326':392}
    assert metrics['total_issuance'] == sum(expected.values())
    assert result.iloc[0]['Account Total'] == sum(expected.values())
    for account,values in LEGACY_GROSS.items():
        rows = result.loc[result['Reg No'].eq(account)]
        assert rows['Quota Transaction Type'].tolist() == [kind for kind,value in zip(INCREASING_TYPES,values) if value is not None]
        assert rows['Quota Bird Count'].tolist() == [value for value in values if value is not None]
        assert rows['Account Total'].tolist() == [expected[account]]*len(rows)


def test_shared_eligibility_latest_base_dates_state_lease_and_owner(monkeypatch):
    repo = Repository()
    repo.transactions = pd.DataFrame([
        tx('oldbase','a','Base',100,EFFECTIVE_DATE='2017-01-01'),
        tx('prebase','a','Adjustment',500,EFFECTIVE_DATE='2018-01-01'),
        tx('base','a','Base',1500),tx('inactive','a','Adjustment',41),
        tx('adj','a','Adjustment',41),tx('global','a','Global Adjustment',3),
        tx('expired','a','Lease (In)',1139,END_DATE='2026-06-01'),
        tx('lease','a','Lease (In)',10,END_DATE=str(DAY)),
        tx('future','a','Purchase',999,EFFECTIVE_DATE='2027-01-01'),
        tx('foreign','a','Purchase',999,OWNER_ACCOUNT_ID='b'),
        tx('national','a','National Allocation',999),
        tx('sale','a','Sale',20),tx('out','a','Lease (Out)',5),
        tx('terminate','a','Terminate Quota',999)])
    monkeypatch.setattr('app.services.report_center.get_inactive_quota_transaction_ids',lambda *args,**kwargs:{'inactive'})
    net,_ = report(repo)
    gross,_ = report(repo,build_quota_summary_details)
    assert net.iloc[1].Issuance == 1529
    assert gross.iloc[0]['Account Total'] == 1554
    assert gross['Quota Transaction Type'].tolist()[1:] == ['Base','Adjustment','Global Adjustment','Lease (In)']
    assert gross['Quota Bird Count'].tolist()[1:] == [1500,41,3,10]


def test_sale_subtracted_and_terminate_zero_effect_only_in_net():
    repo = Repository()
    repo.transactions = pd.DataFrame([tx('base','a','Base',100),tx('adj','a','Adjustment',10),
        tx('sale','a','Sale',25),tx('terminate','a','Terminate Quota',999)])
    net,_ = report(repo)
    gross,_ = report(repo,build_quota_summary_details)
    assert net.iloc[1].Issuance == 85
    assert gross.iloc[0]['Account Total'] == 110
    assert gross['Quota Transaction Type'].tolist()[1:] == ['Base','Adjustment']


def test_base_cutoff_is_per_registration_and_tie_uses_created_at():
    repo = Repository()
    repo.registrations = pd.concat([repo.registrations,pd.DataFrame([
        dict(QUOTA_ID='second',ACCOUNT_ID='a',QUOTA_TYPE='Egg Production',STATUS='Active')])])
    repo.transactions = pd.DataFrame([
        tx('base','a','Base',20,EFFECTIVE_DATE='2021-01-01',CREATED_AT='2021-01-02'),
        tx('older-created','a','Base',999,EFFECTIVE_DATE='2021-01-01',CREATED_AT='2021-01-01'),
        tx('excluded','a','Adjustment',999),
        tx('second-base','a','Base',50,QUOTA_ID='second'),
        tx('second-adjustment','a','Adjustment',7,QUOTA_ID='second')])
    frame,_ = report(repo,build_quota_summary_details)
    assert frame['Quota Bird Count'].tolist()[1:] == [70,7]
    assert frame.iloc[0]['Account Total'] == 77
    assert report(repo)[0].iloc[1].Issuance == 77


@pytest.mark.parametrize('unknown',['state','base_tie','invalid_quantity'])
def test_unknown_blanks_notes_and_sum_known_values(unknown,monkeypatch):
    repo = Repository({'a':100,'b':50})
    if unknown == 'state':
        monkeypatch.setattr('app.services.report_center.get_inactive_quota_transaction_ids',lambda *args,**kwargs:None)
    elif unknown == 'base_tie':
        repo.transactions = pd.concat([repo.transactions,pd.DataFrame([tx('tie','a','Base',120)])])
    else:
        repo.transactions.loc[repo.transactions.OWNER_ACCOUNT_ID.eq('a'),'QUOTA_COUNT'] = None
    for builder,amount in [(build_quota_summary,'Issuance'),(build_quota_summary_details,'Account Total')]:
        frame,metrics = report(repo,builder)
        assert frame.loc[frame['Reg No'].eq('a'),amount].tolist() == ['']
        assert metrics['notes']
        assert frame.iloc[0][amount] == ('' if unknown == 'state' else 50)
        assert metrics['total_issuance'] == (None if unknown == 'state' else 50)


def test_filters_membership_dates_multiple_registrations_numeric_sort_and_other_type():
    repo = Repository({'10':10,'2':2,'a':5})
    more = repo.registrations.iloc[0].to_dict()
    repo.registrations = pd.concat([repo.registrations,pd.DataFrame([dict(more,QUOTA_ID='extra')])])
    frame,_ = report(repo)
    assert frame['Reg No'].tolist() == ['', '2','10','a']
    assert report(repo,account_id='10')[0].Issuance.tolist() == [10,10]
    repo.registrations.loc[repo.registrations.ACCOUNT_ID.eq('2'),'STATUS'] = 'Inactive'
    assert report(repo,status='Inactive')[0].Issuance.tolist() == [0,0]
    assert len(report(repo,status=None)[0]) == 4
    repo.registrations['QUOTA_TYPE'] = 'Commercial Pullet Grower'
    assert report(repo)[0].empty
    frame,_ = build_quota_summary(repo,user=user(),as_of_date=DAY,quota_type='Commercial Pullet Grower')
    assert frame['Reg No'].tolist() == ['', '10','a']


@pytest.mark.parametrize('builder',[build_quota_summary,build_quota_summary_details])
def test_empty_permissions_validation_and_formula_safe_exports(builder):
    repo = Repository()
    repo.accounts.loc[0,'ORGANIZATION_NAME'] = '=1+1'
    result,_ = report(repo,builder)
    for exported in (pd.read_csv(BytesIO(report_csv(user(),result))),pd.read_excel(BytesIO(report_xlsx(user(),result)))):
        assert exported.iloc[1]['Account Name'] == "'=1+1"
    assert report(repo,builder,account_id='missing')[0].empty
    with pytest.raises(ValueError):
        report(repo,builder,status='Invented')
    with pytest.raises(AuthorizationError):
        builder(repo,user=user(active=False),as_of_date=DAY,quota_type='Egg Production')


@pytest.mark.parametrize('report_id',['quota-summary','quota-summary-details'])
def test_catalog_and_page_wiring(report_id,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    root = Path(__file__).resolve().parents[1]
    definition = report_definition(report_id)
    assert definition.status == 'Available' and definition.export_formats == ('CSV','XLSX')
    assert 'provisional' not in definition.description.lower()
    app = authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo'] = Repository({'7022':34526,'7114':0})
    app.switch_page('app/pages/4_Reports.py').run()
    app.session_state['report_center_open_report'] = report_id
    app.run()
    prefix = definition.handler
    app.date_input(key=prefix+'_as_of').set_value(DAY)
    app.button(key='run_'+prefix).click().run()
    assert not app.error and not app.exception
    assert len(app.dataframe) == 1 and len(app.get('download_button')) == 2
    assert not any('pending confirmation' in caption.value.lower() for caption in app.caption)
    assert 'QUOTA_TRANSACTION_ID' not in app.dataframe[0].value
    app.selectbox(key=prefix+'_account').set_value('7022 · 7022')
    app.button(key='run_'+prefix).click().run()
    assert not app.error and not app.exception
    assert set(app.dataframe[0].value['Reg No']) == {'','7022'}
