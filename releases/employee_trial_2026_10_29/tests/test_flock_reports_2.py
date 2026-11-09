"""Offline report fixtures; no live-data or full 37-flock parity assertion."""
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.flock_reports import (
    build_flock_salmonella_schedule, build_scheduled_flock_placements,
    SALMONELLA_SCHEDULE_COLUMNS, PLACEMENT_COLUMNS,
)
from app.services.report_center import report_csv, report_xlsx, report_definition
from tests.test_flock_reports import flock, transaction, accounts, facilities, DAY
from tests.test_report_center import user


def test_salmonella_actual_inventory_fixtures_delivery_and_inclusion():
    f = pd.DataFrame([
        flock('40402', HATCH_DATE='2026-06-18', PLACEMENT_DATE='2026-10-29'),
        flock('40390', HATCH_DATE='2026-05-04', PLACEMENT_DATE='2026-09-14'),
        flock('40362', HATCH_DATE='2025-07-07', PLACEMENT_DATE='2025-11-17',
              EST_DISPOSAL='2026-11-16', DISPOSAL_DATE='2027-01-07'),
        flock('young', HATCH_DATE='2026-09-08'),
        flock('unknown'), flock('inactive', STATUS='Inactive'),
        flock('special', FLOCK_QUOTA_TYPE='Special Permit'),
        flock('dev', FLOCK_NUMBER='DEV_TEST_schedule')])
    t = pd.DataFrame([
        transaction('delivery', '40402', '2026-06-18', TRANSACTION_TYPE='Delivery', QUANTITY=1979),
        transaction('count', '40390', '2026-10-02', QUANTITY=12439),
        transaction('legacy', '40362', '2026-10-19', QUANTITY=102076),
        *[transaction(n, n) for n in ('young','inactive','special','dev')]])
    original = [frame.copy(deep=True) for frame in (f,t)]
    result = build_flock_salmonella_schedule(f,t,accounts(),facilities(),DAY)
    assert list(result) == SALMONELLA_SCHEDULE_COLUMNS
    assert set(result['Permit No']) == {'40402','40390','40362','dev'}
    indexed = result.set_index('Permit No')
    for permit, age, inventory in [('40402',20,1942),('40390',26,12383),('40362',69,101847)]:
        assert indexed.loc[permit,'Flock Age'] == age
        assert indexed.loc[permit,'Inventory'] == inventory
    for actual, before in zip((f,t),original):
        pd.testing.assert_frame_equal(actual,before)


def test_salmonella_supplied_legacy_projection_order(monkeypatch):
    # These are output fixtures, not reconstructed transactions. Missing legacy
    # Inventory/Hatch values are synthetic and used only to test ordering.
    fixtures = [('7101','Ross Cox','40356',75,44369,'2025-05-26'),
        ('7172','Seaview','40359',72,39018,'2025-06-16'),
        ('7172','Seaview','40360',70,32456,'2025-07-03'),
        ('7173','Maritime Pride','40362',69,101847,'2025-07-07'),
        ('7050','Floyd Dickie','40364',66,1,'2025-07-31'),
        ('7178','DeLong','40363',66,1,'2025-07-31'),
        ('7038','Bayview','40382',38,6732,'2026-02-10'),
        ('7404','Windy Bay','40383',38,1,'2026-02-10'),
        ('7106','Southview','40390',26,12383,'2026-05-04'),
        ('7176','Oultons','40392',26,1,'2026-05-04'),
        ('7177','3C-Side','40391',26,1,'2026-05-04'),
        ('7168','Example','40395',22,1,'2026-06-01'),
        ('7402','Example','40402',20,1942,'2026-06-18'),
        ('7107','Example','40396',19,1,'2026-06-22')]
    rows = [dict(zip(['Reg No','Account','Permit No','Flock Age','Inventory','Hatch Date'],row)) for row in fixtures]
    rows += [dict(rows[-1], **{'Permit No':'young','Flock Age':18}),
             dict(rows[-1], **{'Permit No':'old','Flock Age':256}),
             dict(rows[-1], **{'Permit No':'missing','Inventory':'—'}),
             dict(rows[-1], **{'Permit No':'—','Account':'Total'})]
    monkeypatch.setattr('app.services.flock_reports.build_flock_age_report',
                        lambda *args: (pd.DataFrame(list(reversed(rows))),{}))
    result = build_flock_salmonella_schedule(pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),DAY)
    assert result['Permit No'].tolist() == [row[2] for row in fixtures]
    assert result.iloc[0]['Inventory'] == 44369


def test_salmonella_age_bounds_inclusive_and_mortality_forwarded():
    f = pd.DataFrame([flock('lower',HATCH_DATE=str(DAY-timedelta(weeks=19))),
                      flock('upper',HATCH_DATE=str(DAY-timedelta(weeks=255)))])
    t = pd.DataFrame([transaction(n,n,when=str(DAY),QUANTITY=10) for n in f.FLOCK_ID])
    result = build_flock_salmonella_schedule(f,t,accounts(),facilities(),DAY,mortality='0')
    assert result['Flock Age'].tolist() == [255,19]
    assert result.Inventory.tolist() == [10,10]
    with pytest.raises(ValueError):
        build_flock_salmonella_schedule(f,t,accounts(),facilities(),DAY,minimum_age=30,maximum_age=19)


def placement_fixture():
    a = accounts().iloc[:1].copy()
    a.loc[0,['REGISTRATION_NUMBER','ORGANIZATION_NAME']] = ['7050','Floyd Dickie & Sons Ltd.']
    f = pd.DataFrame([flock('40397',HATCH_DATE='2026-07-23',PLACEMENT_DATE='2026-12-03',
        HATCHERY='Atlantic Poultry Incorporated - NB Hatchery',PULLET_GROWER=None,BIRD_COUNT=1)])
    # Delivery dates are synthetic; deliberately after the range to exercise
    # the user's confirmed all-recorded-Deliveries rule.
    t = pd.DataFrame([transaction('d','40397','2027-01-01',TRANSACTION_TYPE='Delivery',QUANTITY=15674),
                      transaction('old','40397','2026-07-23',TRANSACTION_TYPE='Delivery',QUANTITY=100),
                      transaction('c','40397','2027-02-01',QUANTITY=20000)])
    barns = facilities().assign(FACILITY_NAME='7050 - 1')
    return f,t,a,barns


def test_placements_legacy_40397_initial_delivery_and_totals():
    f,t,a,barns = placement_fixture()
    result = build_scheduled_flock_placements(f,t,a,barns,{'a':33823},DAY,'2026-12-05')
    assert list(result) == PLACEMENT_COLUMNS
    row,total,grand = result.to_dict('records')
    assert [row[c] for c in PLACEMENT_COLUMNS[:11]] == [
        '7050','Floyd Dickie & Sons Ltd.',15,19,'40397','7050 - 1','2026-12-03',
        '2026-07-23','Atlantic Poultry Incorporated - NB Hatchery','',15674]
    assert total['Permit No'] == 'TOTAL' and total['Quota'] == 33823 and total['Inventory'] == 15674
    assert [grand[c] for c in ('Total Producers','Total Flocks','Total Birds')] == [1,1,15674]
    pd.testing.assert_frame_equal(result,build_scheduled_flock_placements(f,t,a,barns,{'a':33823},DAY,'2026-12-05',mortality='100'))


def test_placements_inclusive_scope_sort_disposal_fallback_and_unknown_totals():
    f = pd.DataFrame([
        flock('end',PLACEMENT_DATE='2026-12-05',BIRD_COUNT=2),
        flock('start',PLACEMENT_DATE=str(DAY),BIRD_COUNT=3,EST_DISPOSAL='2026-01-01',DISPOSAL_DATE='2027-01-01'),
        flock('unknown','b',PLACEMENT_DATE=str(DAY),BIRD_COUNT=None),
        flock('before',PLACEMENT_DATE='2026-11-04'),flock('after',PLACEMENT_DATE='2026-12-06'),
        flock('inactive',PLACEMENT_DATE=str(DAY),STATUS='Inactive'),
        flock('disposed',PLACEMENT_DATE=str(DAY),DISPOSAL_DATE=str(DAY)),
        flock('estimated',PLACEMENT_DATE=str(DAY),EST_DISPOSAL=str(DAY)),
        flock('other',PLACEMENT_DATE=str(DAY),FLOCK_QUOTA_TYPE='Special Permit')])
    result = build_scheduled_flock_placements(f,pd.DataFrame(),accounts(),facilities(),{},DAY,'2026-12-05')
    assert result['Permit No'].tolist() == ['unknown','TOTAL','start','end','TOTAL','—']
    assert result.Inventory.tolist() == ['—','—',3,2,5,5]
    assert result.iloc[-1]['Total Producers'] == 2 and result.iloc[-1]['Total Flocks'] == 3
    assert result.iloc[1].Quota == '—'
    assert build_scheduled_flock_placements(f,pd.DataFrame(),accounts(),facilities(),{},'2028-01-01','2028-01-02').empty


def test_placements_conflicting_latest_deliveries_do_not_fall_back_to_bird_count():
    f,t,a,barns = placement_fixture()
    t = pd.concat([t,pd.DataFrame([transaction('conflict','40397','2027-01-01',TRANSACTION_TYPE='Delivery',QUANTITY=200)])])
    result = build_scheduled_flock_placements(f,t,a,barns,{},DAY,'2026-12-05')
    assert result.Inventory.tolist() == ['—','—','—']
    assert result.iloc[-1]['Total Birds'] == '—'


@pytest.mark.parametrize('mortality',['NaN','Infinity','-1','bad'])
def test_placements_invalid_mortality(mortality):
    with pytest.raises(ValueError):
        build_scheduled_flock_placements(pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),{},DAY,DAY,mortality)


def test_placements_reversed_range():
    with pytest.raises(ValueError):
        build_scheduled_flock_placements(pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),{},'2026-12-05',DAY)


@pytest.mark.parametrize('kind',['flock-salmonella-schedule','scheduled-flock-placements'])
def test_new_reports_catalog_and_formula_safe_exports(kind):
    a = accounts()
    a.loc[0,'REGISTRATION_NUMBER'] = '=1+1'
    a.loc[0,'ORGANIZATION_NAME'] = '@SUM(1)'
    f = pd.DataFrame([flock(PLACEMENT_DATE=str(DAY))])
    if kind == 'flock-salmonella-schedule':
        result = build_flock_salmonella_schedule(f,pd.DataFrame([transaction()]),a,facilities(),DAY)
    else:
        result = build_scheduled_flock_placements(f,pd.DataFrame(),a,facilities(),{},DAY,DAY)
    definition = report_definition(kind)
    assert definition.status == 'Available' and definition.export_formats == ('CSV','XLSX','PDF')
    for exported in (pd.read_csv(BytesIO(report_csv(user(),result))),pd.read_excel(BytesIO(report_xlsx(user(),result)))):
        assert exported.iloc[0]['Reg No'] == "'=1+1"
        assert exported.iloc[0]['Account Name'] == "'@SUM(1)"


@pytest.mark.parametrize('handler',['flock_salmonella_schedule','scheduled_flock_placements'])
def test_new_report_page_controls_results_and_empty_placements(handler,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from data.repositories.mock import MockRepository
    from app.auth import get_auth_store
    root = Path(__file__).resolve().parents[1]
    app = authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    repo = MockRepository()
    f,t,a,barns = placement_fixture()
    if handler == 'flock_salmonella_schedule':
        f.loc[0,'PLACEMENT_DATE'] = '2026-11-01'
        f.loc[0,'HATCH_DATE'] = '2026-06-01'
        t.loc[0,'TRANSACTION_DATE'] = '2026-11-01'
    repo.get_flocks,repo.get_accounts,repo.get_facilities,repo.get_flock_transactions = lambda:f,lambda:a,lambda:barns,lambda:t
    repo.get_quota_registrations = lambda:pd.DataFrame([dict(QUOTA_ID='q',ACCOUNT_ID='a',QUOTA_TYPE='Egg Production',STATUS='Active')])
    repo.get_quota_transactions = lambda:pd.DataFrame([
        dict(QUOTA_TRANSACTION_ID='base',QUOTA_ID='q',OWNER_ACCOUNT_ID='a',TRANSACTION_TYPE='Base',QUOTA_COUNT=33823,EFFECTIVE_DATE='2026-08-01'),
        dict(QUOTA_TRANSACTION_ID='later',QUOTA_ID='q',OWNER_ACCOUNT_ID='a',TRANSACTION_TYPE='Adjustment',QUOTA_COUNT=10,EFFECTIVE_DATE='2026-11-20')])
    app.session_state['_base_repo'] = repo
    app.switch_page('app/pages/4_Reports.py').run()
    monkeypatch.setattr(get_auth_store(),'record_action',lambda *args,**kwargs:pytest.fail('Read-only report wrote audit'))
    app.session_state['report_center_open_report'] = handler.replace('_','-')
    app.run()
    if handler == 'scheduled_flock_placements':
        app.date_input(key=handler+'_start').set_value(DAY)
        app.date_input(key=handler+'_end').set_value(date(2026,12,5))
    else:
        assert app.number_input(key=handler+'_from_age').value == 19
        assert app.number_input(key=handler+'_to_age').value == 255
        app.date_input(key=handler+'_date').set_value(DAY)
    assert app.text_input(key=handler+'_mortality').value == '0.4'
    assert app.selectbox(key=handler+'_type').value == 'Egg Production'
    app.button(key='run_'+handler).click().run()
    assert not app.exception and not app.error
    assert len(app.dataframe) == 1 and not app.dataframe[0].value.empty
    assert 'FLOCK_ID' not in app.dataframe[0].value
    if handler == 'scheduled_flock_placements':
        assert str(app.dataframe[0].value.iloc[1].Quota) == '33823'  # Start, not end; Arrow stringifies mixed columns.
        f.loc[0,'PLACEMENT_DATE'] = '2027-01-01'
        app.button(key='run_'+handler).click().run()
        assert not app.exception and not app.error
        assert any('No scheduled placements' in info.value for info in app.info)
