"""Offline projections of user-supplied legacy examples; no live DEV evidence."""
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.flock_age_report import build_flock_age_report
from app.services.flock_reports import (
    STATUS_COLUMNS, COUNTED_COLUMNS, NEEDING_COLUMNS, DISPOSAL_COLUMNS,
    build_flock_status_report, build_flocks_counted_report,
    build_flocks_needing_counts_report, build_flock_disposals_report,
    provisional_disposal_age,
)
from app.services.report_center import report_csv, report_xlsx, report_definition
from tests.test_report_center import user

DAY = date(2026, 11, 5)


def flock(number='40370', owner='a', **extra):
    row = dict(FLOCK_ID=number, FLOCK_NUMBER=number, PERMIT_NUMBER=number,
        ACCOUNT_ID=owner, FACILITY_ID='facility', FLOCK_QUOTA_TYPE='Egg Production',
        STATUS='Active', HATCH_DATE='2025-09-15', PLACEMENT_DATE='2026-01-01',
        EST_DISPOSAL='2027-01-01', DISPOSAL_DATE=None, BIRD_COUNT=38895)
    return dict(row, **extra)


def transaction(identity='t', parent='40370', when='2026-09-04', source='Producer', **extra):
    return dict(dict(FLOCK_TRANSACTION_ID=identity, FLOCK_ID=parent,
        TRANSACTION_TYPE='Count', TRANSACTION_DATE=when, COUNT_SOURCE_LABEL=source,
        QUANTITY=38895), **extra)


def accounts():
    return pd.DataFrame([
        dict(ACCOUNT_ID='a', ORGANIZATION_NAME='Zulu', REGISTRATION_NUMBER='7107', PRODUCER_ROLE=True),
        dict(ACCOUNT_ID='b', ORGANIZATION_NAME='Alpha', REGISTRATION_NUMBER='7065', PRODUCER_ROLE=True)])


def facilities():
    return pd.DataFrame([dict(FACILITY_ID='facility', FACILITY_NAME='Synthetic barn')])


def test_status_reuses_age_summary_and_puts_account_totals_first_by_registration():
    f = pd.DataFrame([flock('40370'), flock('40371'), flock('40350', 'b')])
    t = pd.DataFrame([transaction(parent=n, identity=n) for n in f.FLOCK_ID])
    a, quotas = accounts(), {'a': 77862, 'b': 40981}
    snapshots = [frame.copy(deep=True) for frame in (f, t, a)]
    age, expected_summary = build_flock_age_report(f, t, a, facilities(), quotas, DAY)
    status, summary = build_flock_status_report(f, t, a, facilities(), quotas, DAY)
    assert list(status) == STATUS_COLUMNS
    assert summary == expected_summary
    assert status['Reg No'].tolist() == ['7065', '7065', '7107', '7107', '7107']
    assert status['Permit No'].tolist() == ['Total', '40350', 'Total', '40370', '40371']
    assert status.Sold.tolist() == [''] * 5
    assert status.iloc[3]['Facility Name'] == 'Synthetic barn'
    for permit in ('40350', '40370', '40371'):
        for column in ('Inventory', 'Quota', 'Flock Age', 'Up. Flocks', 'Util.', 'Disp. Date'):
            assert status.loc[status['Permit No'].eq(permit), column].iloc[0] == age.loc[age['Permit No'].eq(permit), column].iloc[0]
    for actual, before in zip((f, t, a), snapshots):
        pd.testing.assert_frame_equal(actual, before)


def test_counted_40370_inclusive_range_every_transaction_and_explicit_test_exclusion():
    f = pd.DataFrame([flock(), flock('test', FLOCK_NUMBER='DEV_TEST_counted'),
                      flock('other', FLOCK_QUOTA_TYPE='Commercial Pullet Grower')])
    t = pd.DataFrame([transaction(), transaction('board', source='Board'),
        transaction('start', when='2026-09-01'), transaction('end', when='2026-11-05'),
        transaction('before', when='2026-08-31'), transaction('future', when='2026-11-06'),
        transaction('delivery', TRANSACTION_TYPE='Delivery'), transaction('test', parent='test'),
        transaction('other', parent='other')])
    result = build_flocks_counted_report(f, t, accounts(), {'a': 77862}, '2026-09-01', DAY)
    assert list(result) == COUNTED_COLUMNS and len(result) == 4
    example = result.loc[result['Transaction Date'].eq('2026-09-04')]
    assert example['Flock Age'].tolist() == [50, 50]
    assert example['Birds Counted'].tolist() == [38895, 38895]
    assert result.Quota.tolist() == [77862] * 4
    assert result.Inspector.tolist() == [''] * 4
    assert set(result['Count Type']) == {'Producer', 'Board'}
    assert len(build_flocks_counted_report(f, t, accounts(), {}, '2026-09-01', DAY, 'All')) == 5
    unknown = build_flocks_counted_report(f, t, accounts(), {}, '2026-09-01', DAY)
    assert unknown.Quota.tolist() == ['—'] * 4


def needing_sources():
    birds = {'40396': 39772, '40395': 19968, '40402': 1979, '40382': 6840,
             '40377': 14712, '40394': 45123, '40393': 51072}
    # Unprovided dates are synthetic within-scope values; these fixtures verify
    # Count-type absence and original Bird Count, not full live-data parity.
    f = pd.DataFrame([flock(n, HATCH_DATE='2026-05-04', PLACEMENT_DATE='2026-09-14',
        BIRD_COUNT=value) for n, value in birds.items()])
    t = pd.DataFrame([transaction(n, n, source='Board') for n in ('40377','40382','40393','40394')]
        + [transaction('delivery', '40402', TRANSACTION_TYPE='Delivery'),
           transaction('future-count', '40402', when='2026-11-06')])
    return f, t, birds


def test_needing_counts_legacy_permit_sets_and_original_bird_counts():
    f, t, birds = needing_sources()
    board = build_flocks_needing_counts_report(f, t, accounts(), DAY, count_type='Board')
    producer = build_flocks_needing_counts_report(f, t, accounts(), DAY, count_type='Producer')
    assert list(board) == NEEDING_COLUMNS
    assert board['Permit No'].tolist() == ['40395','40396','40402']
    assert producer['Permit No'].tolist() == ['40377','40382','40393','40394','40395','40396','40402']
    assert producer.set_index('Permit No')['Bird Count'].to_dict() == birds
    # Multiple matching Counts do not multiply the Flock result.
    t = pd.concat([t, t.iloc[:1]])
    assert build_flocks_needing_counts_report(f, t, accounts(), DAY)['Permit No'].tolist() == ['40395','40396','40402']


def test_needing_counts_age_placement_disposal_and_other_source_rules():
    f, t, _ = needing_sources()
    extra = [flock('planned', STATUS='Planned'), flock('future', PLACEMENT_DATE='2027-01-01'),
             flock('disposed', DISPOSAL_DATE=DAY), flock('special', FLOCK_QUOTA_TYPE='Special Permit'),
             flock('young', HATCH_DATE=DAY-timedelta(weeks=18)),
             flock('old', HATCH_DATE=DAY-timedelta(weeks=300))]
    f = pd.concat([f, pd.DataFrame(extra)])
    t = pd.concat([t, pd.DataFrame([transaction('efc', '40395', source='EFC'),
                                    transaction('blank', '40396', source=None)])])
    result = build_flocks_needing_counts_report(f, t, accounts(), DAY, count_type='EFC/CEMA')
    assert set(result['Permit No']) == {'40377','40382','40393','40394','40402'}
    assert build_flocks_needing_counts_report(f, t, accounts(), DAY)['Permit No'].tolist() == ['40402']
    # Age boundaries are inclusive, and actual disposal overrides an old estimate.
    row = pd.DataFrame([flock('boundary', HATCH_DATE=DAY-timedelta(weeks=19),
        EST_DISPOSAL='2026-01-01', DISPOSAL_DATE='2026-12-03')])
    result = build_flocks_needing_counts_report(row, pd.DataFrame(), accounts(), DAY, from_age=19, to_age=19)
    assert result.iloc[0]['Disposal Date'] == '2026-12-03'


DISPOSALS = [
    ('40350','7065','Scotia Poultry',20832,15356,'In-Barn CO2','2026-09-03'),
    ('40351','7106','Southview',12500,11229,'','2026-08-07'),
    ('40348','7107','Atlantic Poultry',30573,48820,'','2026-10-06'),
    ('40357','7159','Registration 7159',44808,38108,'S.F Rendering','2026-09-24'),
    ('40366','7159','Registration 7159',5100,5196,'S.F Rendering','2026-09-24'),
    ('40358','7168','Registration 7168',25792,24052,'','2026-09-24'),
    ('40369','7402','Registration 7402',1979,1851,'CO2 Chamber','2026-10-08')]


def test_disposals_legacy_rows_and_account_totals_without_capping_disposed():
    # Hatches/placements not supplied in this output excerpt are synthetic.
    f = pd.DataFrame([flock(n, reg, HATCH_DATE='2025-07-21', PLACEMENT_DATE='2025-11-01',
        BIRD_COUNT=placed, BIRDS_DISPOSED=disposed, DISPOSAL_PLANT=plant,
        DISPOSAL_DATE=when, STATUS='Inactive') for n,reg,_,placed,disposed,plant,when in DISPOSALS])
    a = pd.DataFrame([dict(ACCOUNT_ID=reg, REGISTRATION_NUMBER=reg, ORGANIZATION_NAME=name)
                      for reg,name in dict((r[1],r[2]) for r in DISPOSALS).items()])
    quotas = {'7065':40981,'7106':12500,'7107':77862,'7159':42980,'7168':55171,'7402':1790}
    result = build_flock_disposals_report(f, a, quotas, '2026-08-01', DAY)
    assert list(result) == DISPOSAL_COLUMNS and len(result) == 13
    assert result['Reg No'].tolist() == sorted(result['Reg No'].tolist())
    for permit,reg,_,placed,disposed,plant,when in DISPOSALS:
        row = result.loc[result['Permit No'].eq(permit)].iloc[0]
        assert (row.Placed,row.Disposed,row['Disposal Plant'],row['Disposal Date'],row.Quota) == (placed,disposed,plant,when,quotas[reg])
    total = result.loc[result['Reg No'].eq('7159')].iloc[-1]
    assert total['Permit No'] == 'Total'
    assert (total.Placed,total.Disposed,total.Quota) == (49908,43304,42980)
    assert provisional_disposal_age('2025-07-21','2026-09-24') == 61  # Legacy 80 is NOT claimed.
    assert provisional_disposal_age('2025-07-21','2026-10-08') == 63  # Legacy 82 is NOT claimed.


def test_disposals_require_actual_dates_and_include_range_endpoints():
    f = pd.DataFrame([flock('start', DISPOSAL_DATE='2026-08-01'), flock('end', DISPOSAL_DATE=DAY),
        flock('estimated-only', EST_DISPOSAL='2026-09-01'), flock('after', DISPOSAL_DATE='2026-11-06'),
        flock('other-type', DISPOSAL_DATE='2026-09-01', FLOCK_QUOTA_TYPE='Commercial Pullet Grower')])
    result = build_flock_disposals_report(f, accounts(), {}, '2026-08-01', DAY)
    assert result['Permit No'].tolist() == ['start','end','Total']
    assert result.Quota.tolist() == ['—'] * 3
    assert result.iloc[-1].Disposed == '—'
    assert build_flock_disposals_report(f, accounts(), {}, '2027-01-01','2027-01-02').empty


@pytest.mark.parametrize('builder', ['counted','disposals','needing'])
def test_invalid_parameter_ranges_are_rejected(builder):
    with pytest.raises(ValueError):
        if builder == 'counted':
            build_flocks_counted_report(pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),{},DAY,'2026-01-01')
        elif builder == 'disposals':
            build_flock_disposals_report(pd.DataFrame(),pd.DataFrame(),{},DAY,'2026-01-01')
        else:
            build_flocks_needing_counts_report(pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),DAY,from_age=30,to_age=19)


def test_all_new_reports_formula_safe_exports_and_available_catalog():
    f, a = pd.DataFrame([flock()]), accounts()
    a.loc[0,'REGISTRATION_NUMBER'] = '=1+1'
    t = pd.DataFrame([transaction()])
    status,_ = build_flock_status_report(f,t,a,facilities(),{'a':77862},DAY)
    counted = build_flocks_counted_report(f,t,a,{},'2026-09-01',DAY)
    needing = build_flocks_needing_counts_report(f,t.iloc[:0],a,DAY)
    disposed_flocks = f.assign(DISPOSAL_DATE='2026-09-24', BIRDS_DISPOSED=100)
    disposed = build_flock_disposals_report(disposed_flocks,a,{},'2026-08-01',DAY)
    for report_id, frame in zip(('flock-status','flocks-counted','flocks-needing-counts','flock-disposals'),
                                 (status,counted,needing,disposed)):
        definition = report_definition(report_id)
        assert definition.status == 'Available' and definition.export_formats == ('CSV','XLSX')
        assert pd.read_csv(BytesIO(report_csv(user(),frame))).iloc[0,0] == "'=1+1"
        assert pd.read_excel(BytesIO(report_xlsx(user(),frame))).iloc[0,0] == "'=1+1"


@pytest.mark.parametrize('handler', ['flock_status','flocks_counted','flocks_needing_counts','flock_disposals'])
def test_report_center_wiring_only_result_frames_and_no_audit_writes(handler,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from data.repositories.mock import MockRepository
    from app.auth import get_auth_store
    root = Path(__file__).resolve().parents[1]
    app = authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    f, a = pd.DataFrame([flock(DISPOSAL_DATE='2026-09-24') if handler=='flock_disposals' else flock()]), accounts()
    repo = MockRepository()
    repo.get_flocks = lambda:f
    repo.get_accounts = lambda:a
    repo.get_facilities = facilities
    repo.get_flock_transactions = lambda:pd.DataFrame([transaction()]) if handler!='flocks_needing_counts' else pd.DataFrame()
    repo.get_quota_registrations = lambda:pd.DataFrame([dict(QUOTA_ID='q',ACCOUNT_ID='a',QUOTA_TYPE='Egg Production',STATUS='Active')])
    repo.get_quota_transactions = lambda:pd.DataFrame([
        dict(QUOTA_TRANSACTION_ID='base',QUOTA_ID='q',OWNER_ACCOUNT_ID='a',TRANSACTION_TYPE='Base',QUOTA_COUNT=100,EFFECTIVE_DATE='2026-08-01'),
        dict(QUOTA_TRANSACTION_ID='future-adjustment',QUOTA_ID='q',OWNER_ACCOUNT_ID='a',TRANSACTION_TYPE='Adjustment',QUOTA_COUNT=10,EFFECTIVE_DATE='2026-10-01')])
    app.session_state['_base_repo'] = repo
    app.switch_page('app/pages/4_Reports.py').run()
    monkeypatch.setattr(get_auth_store(),'record_action',lambda *args,**kwargs:pytest.fail('Read-only reports cannot audit/write'))
    app.session_state['report_center_open_report'] = handler.replace('_','-')
    app.run()
    if handler in {'flocks_counted','flock_disposals'}:
        app.date_input(key=handler+'_start').set_value(date(2026,9,1))
        app.date_input(key=handler+'_end').set_value(date(2026,9,30))
    else:
        app.date_input(key=handler+'_date').set_value(DAY)
    app.button(key='run_'+handler).click().run()
    assert not app.exception and not app.error
    assert len(app.dataframe) == 1 and not app.dataframe[0].value.empty
    assert 'FLOCK_ID' not in app.dataframe[0].value
    if handler in {'flocks_counted','flock_disposals'}:
        assert app.dataframe[0].value.iloc[0].Quota == 100  # Position at end date, not today.
    if handler == 'flock_status':
        assert len(app.metric) == 5
    if handler == 'flock_disposals':
        assert any('PROVISIONAL Disposal Age' in warning.value for warning in app.warning)
        f.loc[0,'DISPOSAL_DATE'] = None
        app.button(key='run_'+handler).click().run()
        assert not app.exception and not app.error
        assert any('No flocks disposed in this range.' == info.value for info in app.info)
