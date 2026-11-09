"""Pure quota projections using supplied two-party legacy rows; no live access."""
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.quota_reports import (build_quota_transactions_report,
    build_quota_leases_report, build_quota_history_report, TRANSACTION_COLUMNS,
    LEASE_COLUMNS, HISTORY_COLUMNS)
from app.services.report_center import report_definition, report_csv, report_xlsx
from app.security import Permission
from data.confirmed_quota_position import confirmed_quota_position
from data.quota_position import load_rules
from tests.test_report_center import user

DAY = date(2026,11,6)
# Reg, type, date, end, related, count. Empty Sale/Purchase ends are supplied
# as '--' or omitted in the source fixture; both mean no End Date here.
EXPECTED = '''7038|Lease (In)|19/12/2024|19/01/2026|7106|200
7065|Lease (Out)|20/01/2025|20/02/2026|7167|950
7078|Lease (Out)|13/09/2026|25/10/2027|7177|2205
7106|Lease (Out)|13/09/2026|25/10/2027|7177|1247
7106|Lease (Out)|19/12/2024|19/01/2026|7038|200
7106|Lease (Out)|24/07/2025|24/08/2026|7177|1538
7106|Sale|27/08/2026||7176|805
7107|Lease (Out)|01/06/2026|01/06/2026|7404|1139
7128|Sale|08/07/2026||7178|45495
7161|Lease (Out)|26/02/2026|26/03/2027|7165|4403
7161|Lease (Out)|24/02/2025|23/03/2026|7165|1487
7165|Lease (In)|24/02/2025|23/03/2026|7161|1487
7165|Lease (In)|26/02/2026|26/03/2027|7161|4403
7167|Lease (In)|20/01/2025|20/02/2026|7065|950
7168|Sale|17/08/2026||7169|1500
7168|Sale|16/04/2026||7169|1851
7169|Purchase|17/08/2026||7168|1500
7169|Purchase|16/04/2026||7168|1851
7176|Purchase|27/08/2026||7106|805
7177|Lease (In)|13/09/2026|25/10/2027|7106|1247
7177|Lease (In)|24/07/2025|24/08/2026|7106|1538
7177|Lease (In)|13/09/2026|25/10/2027|7078|2205
7178|Purchase|08/07/2026||7128|45495
7404|Lease (In)|01/06/2026|01/06/2026|7107|1139'''


def iso(value):
    return pd.to_datetime(value,format='%d/%m/%Y').date().isoformat() if value else None


def transaction(identity,owner='7106',kind='Purchase',when='2026-01-01',count=100,**extra):
    return dict(dict(QUOTA_TRANSACTION_ID=identity,QUOTA_ID=owner,OWNER_ACCOUNT_ID=owner,
        TRANSACTION_TYPE=kind,EFFECTIVE_DATE=when,END_DATE=None,QUOTA_COUNT=count,
        RELATED_ACCOUNT_ID=None,COMMENTS=None,PRICE=None,CREATED_AT='2020-01-01'),**extra)


def fixture():
    expected = [line.split('|') for line in EXPECTED.splitlines()]
    ids = sorted({row[0] for row in expected}|{row[4] for row in expected})
    accounts = pd.DataFrame([dict(ACCOUNT_ID=n,REGISTRATION_NUMBER=n,ORGANIZATION_NAME='Account '+n) for n in ids])
    registrations = pd.DataFrame([dict(QUOTA_ID=n,ACCOUNT_ID=n,QUOTA_TYPE='Egg Production',STATUS='Active',
        EFFECTIVE_DATE='2200-01-01',END_DATE='2000-01-01') for n in ids])
    transactions = pd.DataFrame([transaction(str(i),row[0],row[1],iso(row[2]),int(row[5]),
        END_DATE=iso(row[3]),RELATED_ACCOUNT_ID=row[4]) for i,row in enumerate(expected)])
    return accounts,registrations,transactions


def test_transactions_all_24_legacy_rows_both_parties_and_overlap():
    a,r,t = fixture()
    snapshots = [frame.copy(deep=True) for frame in (a,r,t)]
    frame,metadata = build_quota_transactions_report(a,r,t,set(),'2026-01-01',DAY)
    assert list(frame) == TRANSACTION_COLUMNS and len(frame) == 24
    actual = [(row['Reg No'],row['Quota Transaction Type'],row['Transaction Date'],row['Quota End Date'],
               row['Related Reg No'],int(row['Bird Count'])) for row in frame.to_dict('records')]
    expected = [tuple([*row[:5],int(row[5])]) for row in (line.split('|') for line in EXPECTED.splitlines())]
    assert sorted(actual) == sorted(expected)
    assert metadata['header'] == 'For Egg Production as of 01/01/2026 to 06/11/2026'
    assert metadata['notes'] == []
    keys = [(row[0],row[1],iso(row[2])) for row in actual]
    assert keys == sorted(keys)
    for actual_frame,before in zip((a,r,t),snapshots):
        pd.testing.assert_frame_equal(actual_frame,before)


def test_eight_legacy_leases_future_starts_and_total_13169():
    a,r,t = fixture()
    ordinary,meta = build_quota_leases_report(a,r,t,set(),'2026-01-01')
    by_end,sorted_meta = build_quota_leases_report(a,r,t,set(),'2026-01-01',by_end_date=True)
    assert list(ordinary) == LEASE_COLUMNS and len(ordinary) == 9
    assert ordinary.iloc[-1]['Account Name'] == 'Total Bird Count'
    assert ordinary.iloc[-1]['Bird Count'] == meta['total_birds'] == 13169
    assert sorted_meta == meta
    assert list(by_end)[0] == 'Quota End Date'
    assert by_end['Quota End Date'].tolist()[:3] == ['25/10/2027','25/10/2027','26/03/2027']
    assert by_end['Reg No'].tolist()[:2] == ['7078','7106']
    assert '13/09/2026' in ordinary['Transaction Date'].tolist()
    assert set(ordinary['Related Reg No']) == {'7167','7177','7038','7404','7165',''}
    pd.testing.assert_frame_equal(ordinary.iloc[:-1].sort_values(['Reg No','Transaction Date']).reset_index(drop=True),
        by_end[LEASE_COLUMNS].iloc[:-1].sort_values(['Reg No','Transaction Date']).reset_index(drop=True))


def test_lease_end_date_ties_use_registration_order():
    a,r,t = fixture()
    frame,_ = build_quota_leases_report(a,r,t,set(),'2026-01-01',by_end_date=True)
    assert frame.iloc[:2]['Reg No'].tolist() == ['7078','7106']


def history_fixture():
    a,r,t = fixture()
    bases = [transaction('base'+owner,owner,'Base','2020-01-01',100000) for owner in a.ACCOUNT_ID]
    additions = [transaction('old-base','7106','Base','2015-01-01',500),
        transaction('pre-base','7106','Adjustment','2019-01-01',100),
        transaction('global','7106','Global Adjustment','2020-01-01',20),
        transaction('term','7106','Terminate Quota','2025-01-01',999),
        transaction('excluded','7106','National Allocation','2025-01-01',999),
        transaction('future','7106','Purchase','2027-01-01',999),
        transaction('inactive','7106','Adjustment','2025-01-01',999)]
    t = pd.concat([t,pd.DataFrame([*bases,*additions])],ignore_index=True)
    return a,r,t


def test_history_every_account_reconciles_to_confirmed_position():
    a,r,t = history_fixture()
    frame,meta = build_quota_history_report(a,r,t,{'inactive'},DAY,rules=load_rules())
    assert list(frame) == HISTORY_COLUMNS and not meta['notes']
    for owner in a.ACCOUNT_ID:
        rows = frame.loc[frame['Reg No'].eq(owner)]
        position = confirmed_quota_position(r,t,owner,'Egg Production',DAY,{'inactive'},load_rules())
        assert rows.iloc[-1]['Running Balance'] == position['net_position']
        assert set(rows['Current Quota']) == {position['net_position']}
        assert rows['Quota Count Adjust'].sum() == position['net_position']
    own = frame.loc[frame['Reg No'].eq('7106')]
    assert own.iloc[:2]['Quota Count Adjust'].tolist() == [0,0]
    expired = own.loc[own['Quota End Date'].isin(['19/01/2026','24/08/2026'])]
    assert expired['Quota Count Adjust'].tolist() == [0,0]
    terminate = frame.loc[frame['Quota Transaction Type'].eq('Terminate Quota')]
    assert terminate['Bird Count'].tolist() == [999] and terminate['Quota Count Adjust'].tolist() == [0]
    assert frame.loc[frame['Bird Count'].eq(999),'Quota Transaction Type'].tolist() == ['Terminate Quota']


def test_history_no_base_zero_effect_terminate_signed_adjustment_and_tie_order():
    a,r,_ = fixture()
    t = pd.DataFrame([transaction('b',kind='Purchase',count=50,CREATED_AT='2026-01-01T02:00:00Z'),
        transaction('a',kind='Adjustment',count=-2,CREATED_AT='2026-01-01T01:00:00Z'),
        transaction('c',kind='Terminate Quota',count=999,CREATED_AT='2026-01-01T03:00:00Z')])
    frame,_ = build_quota_history_report(a,r,t,set(),DAY,account_id='7106',rules=load_rules())
    assert frame['Quota Transaction Type'].tolist() == ['Adjustment','Purchase','Terminate Quota']
    assert frame['Quota Count Adjust'].tolist() == [-2,50,0]
    assert frame['Running Balance'].tolist() == [-2,48,48]


def test_missing_end_dates_explicit_test_rows_inactive_registrations_and_unknown_state():
    a,r,t = fixture()
    r.loc[r.ACCOUNT_ID.eq('7038'),'STATUS'] = 'Inactive'
    t = pd.concat([t,pd.DataFrame([
        transaction('open',kind='Lease (Out)',when='2020-01-01',END_DATE=None),
        transaction('test',kind='Lease (Out)',COMMENTS='DEV_TEST_example'),
        transaction('boundary',kind='Sale',when=str(DAY)),
        transaction('after',kind='Sale',when='2026-11-07')])],ignore_index=True)
    frame,meta = build_quota_leases_report(a,r,t,set(),DAY,by_end_date=True)
    assert frame.iloc[-2]['Quota End Date'] == ''
    assert any('1 lease(s) with no Quota End Date' in note for note in meta['notes'])
    trades,_ = build_quota_transactions_report(a,r,t,{'boundary'},'2026-01-01',DAY)
    assert '7038' not in trades['Reg No'].tolist()
    assert len(trades) == 24  # one inactive-registration row removed, one open lease added
    assert not trades['Quota End Date'].str.contains('00/',regex=False).any()
    for builder,args in [(build_quota_transactions_report,('2026-01-01',DAY)),(build_quota_leases_report,(DAY,))]:
        unknown,notes = builder(a,r,t,None,*args)
        assert unknown.empty and any('evidence unavailable' in note for note in notes['notes'])


def test_unknown_base_evidence_blanks_balances_and_null_fields():
    a,r,t = fixture()
    a.loc[a.ACCOUNT_ID.eq('7106'),['REGISTRATION_NUMBER','ORGANIZATION_NAME']] = None
    t = pd.DataFrame([transaction('tie1',kind='Base'),transaction('tie2',kind='Base')])
    frame,meta = build_quota_history_report(a,r,t,set(),DAY,rules=load_rules())
    assert frame['Reg No'].tolist() == ['',''] and frame['Account Name'].tolist() == ['','']
    assert frame['Quota Count Adjust'].tolist() == ['','']
    assert frame['Running Balance'].tolist() == ['',''] and meta['notes']


def test_all_reports_active_registrations_test_accounts_and_selected_quota_type():
    a,r,t = fixture()
    r.loc[r.ACCOUNT_ID.eq('7106'),'STATUS'] = 'Inactive'
    a.loc[a.ACCOUNT_ID.eq('7078'),'ORGANIZATION_NAME'] = 'DEV_TEST_account'
    ordinary,_ = build_quota_transactions_report(a,r,t,set(),'2026-01-01',DAY)
    leases,_ = build_quota_leases_report(a,r,t,set(),'2026-01-01')
    history,_ = build_quota_history_report(a,r,t,set(),DAY,rules=load_rules())
    for frame in (ordinary,leases,history):
        assert not frame['Reg No'].isin(['7106','7078']).any()
        assert not frame['Related Reg No'].eq('7078').any()
    empty,_ = build_quota_transactions_report(a,r,t,set(),'2026-01-01',DAY,'Commercial Pullet Grower')
    assert empty.empty


def test_history_multiple_registrations_missing_timestamps_and_account_filter():
    a,r,t = fixture()
    r = pd.concat([r,pd.DataFrame([dict(QUOTA_ID='second',ACCOUNT_ID='7106',QUOTA_TYPE='Egg Production',STATUS='Active')])])
    t = pd.DataFrame([transaction('z',kind='Base',when='2025-01-01',count=100,CREATED_AT=None),
        transaction('a',kind='Adjustment',when='2025-01-01',count=3,CREATED_AT=None),
        transaction('other-base',kind='Base',when='2020-01-01',count=50,QUOTA_ID='second'),
        transaction('other-adjustment',kind='Adjustment',when='2021-01-01',count=7,QUOTA_ID='second')])
    frame,_ = build_quota_history_report(a,r,t,set(),DAY,account_id='7106',rules=load_rules())
    position = confirmed_quota_position(r,t,'7106','Egg Production',DAY,set(),load_rules())
    assert frame['Bird Count'].tolist() == [50,7,3,100]
    assert frame.iloc[-1]['Running Balance'] == position['net_position'] == 160
    empty,_ = build_quota_history_report(a,r,t,set(),DAY,account_id='7038',rules=load_rules())
    assert empty.empty
    unavailable,meta = build_quota_history_report(a,r,t,None,DAY,rules=load_rules())
    assert unavailable.empty and meta['notes']


def test_only_stored_rows_no_counterparty_synthesis_or_qil_split():
    a,r,_ = fixture()
    t = pd.DataFrame([transaction('stored',kind='Purchase',count=3500,RELATED_ACCOUNT_ID='7038',PRICE=0)])
    frame,_ = build_quota_transactions_report(a,r,t,set(),DAY,DAY)
    assert frame.empty  # Transaction is January 1.
    frame,_ = build_quota_transactions_report(a,r,t,set(),'2026-01-01',DAY)
    assert len(frame) == 1 and frame.iloc[0]['Bird Count'] == 3500
    t.loc[0,'TRANSACTION_TYPE'] = 'Lease (Out)'
    leases,meta = build_quota_leases_report(a,r,t,set(),DAY)
    assert leases.iloc[0].Price == 0 and leases.iloc[0]['Comments'] == ''


@pytest.mark.parametrize('report_id',['quota-transactions','quota-leases','quota-leases-by-end-date','quota-history'])
def test_catalog_exports_and_page_wiring(report_id,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from tests.test_confirmed_quota_reports import Repository
    from app.auth import get_auth_store
    a,r,t = fixture()
    a.loc[a.ACCOUNT_ID.eq('7106'),'ORGANIZATION_NAME'] = '=1+1'
    kwargs = {}
    if report_id == 'quota-transactions':
        frame,_ = build_quota_transactions_report(a,r,t,set(),'2026-01-01',DAY)
    elif report_id == 'quota-history':
        frame,_ = build_quota_history_report(a,r,t,set(),DAY,rules=load_rules())
    else:
        frame,_ = build_quota_leases_report(a,r,t,set(),'2026-01-01',by_end_date=report_id.endswith('by-end-date'))
    definition = report_definition(report_id)
    assert definition.permission == Permission.VIEW_REPORTS and definition.status == 'Available'
    assert definition.export_formats == ('CSV','XLSX','PDF')
    for exported in (pd.read_csv(BytesIO(report_csv(user(),frame)),keep_default_na=False),
                     pd.read_excel(BytesIO(report_xlsx(user(),frame)),keep_default_na=False)):
        assert "'=1+1" in exported['Account Name'].tolist()
        assert set(exported['Transaction Date']) <= set(frame['Transaction Date'])
    repo = Repository()
    repo.accounts,repo.registrations,repo.transactions = a,r,t
    root = Path(__file__).resolve().parents[1]
    app = authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo'] = repo
    app.switch_page('app/pages/4_Reports.py').run()
    monkeypatch.setattr(get_auth_store(),'record_action',lambda *args,**kwargs:pytest.fail('Read-only report cannot write'))
    app.session_state['report_center_open_report'] = report_id
    app.run()
    prefix = definition.handler
    assert app.selectbox(key=prefix+'_type').value == 'Egg Production'
    if prefix == 'quota_transactions':
        app.date_input(key=prefix+'_start').set_value(date(2026,1,1))
        app.date_input(key=prefix+'_end').set_value(DAY)
    else:
        app.date_input(key=prefix+'_date').set_value(date(2026,1,1) if prefix.startswith('quota_leases') else DAY)
    app.button(key='run_'+prefix).click().run()
    assert not app.exception and not app.error and len(app.dataframe) == 1
    assert len(app.get('download_button')) == 3
    assert 'QUOTA_TRANSACTION_ID' not in app.dataframe[0].value
    import pyarrow.ipc as ipc
    display = ipc.open_stream(app.dataframe[0].proto.styler.display_values).read_all().to_pandas()
    assert display['Bird Count'].str.contains(',',regex=False).any()


def test_invalid_range_and_parent_identity_rejected():
    a,r,t = fixture()
    with pytest.raises(ValueError):
        build_quota_transactions_report(a,r,t,set(),DAY,'2026-01-01')
    with pytest.raises(ValueError):
        build_quota_leases_report(a,r,pd.concat([t,t]),set(),DAY)
