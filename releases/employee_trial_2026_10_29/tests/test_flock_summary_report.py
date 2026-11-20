"""Synthetic weekly stock invariants; no source exports."""
from datetime import date, timedelta
import pandas as pd
import pytest
from data.efc_calendar import synthetic_efc_calendar, resolve_production_week, default_flock_summary_weeks
from app.services.flock_summary_report import build_flock_summary_report
from app.services.flock_reports import build_flock_status_report
from data.migration import parse_reporting_period
from app.services.production_reports import production_week


def sources():
    accounts = pd.DataFrame([dict(ACCOUNT_ID=k, ORGANIZATION_NAME='Synthetic '+k,
        REGISTRATION_NUMBER=str(i), PRODUCER_ROLE=True) for i,k in enumerate(('a','b'),1)])
    flocks = pd.DataFrame([dict(FLOCK_ID=k,PERMIT_NUMBER=k,FLOCK_NUMBER=k,ACCOUNT_ID=k,
        FACILITY_ID='barn',STATUS='Active',FLOCK_QUOTA_TYPE=t,HATCH_DATE='2025-01-01',
        PLACEMENT_DATE='2025-06-01',EST_DISPOSAL='2027-01-01',DISPOSAL_DATE=None,BIRD_COUNT=90)
        for k,t in [('a','Egg Production'),('b','Commercial Pullet Grower')]])
    activity = pd.DataFrame([dict(FLOCK_TRANSACTION_ID=k,FLOCK_ID=k,TRANSACTION_DATE='2025-12-01',
        TRANSACTION_TYPE='Count',QUANTITY=90,COUNT_SOURCE_LABEL='Producer') for k in ('a','b')])
    return flocks,activity,accounts,pd.DataFrame([dict(FACILITY_ID='barn',FACILITY_NAME='Synthetic barn')])


def test_calendar_mapping_defaults_53_weeks_and_boundary():
    calendar = pd.concat([synthetic_efc_calendar(y) for y in (2022,2023,2026)])
    assert parse_reporting_period('202601') == (2026,1)
    assert production_week({'SOURCE_WEEK_CODE':'202601'}) == 2026*100+1
    assert resolve_production_week(calendar,202601) == (date(2025,12,28),date(2026,1,3))
    assert resolve_production_week(calendar,202253)[1]+timedelta(days=1) == resolve_production_week(calendar,202301)[0]
    assert default_flock_summary_weeks(calendar,date(2025,12,31)) == (202601,202601)
    assert default_flock_summary_weeks(calendar,date(2022,12,31)) == (202201,202253)


@pytest.mark.parametrize('grouped',[False,True])
def test_stock_reuses_status_and_type_columns_and_producers_add_up(grouped):
    f,t,a,b = sources(); calendar = synthetic_efc_calendar(2026)
    result = build_flock_summary_report(f,t,a,b,calendar,202601,202602,quota_type='All',group_by_producer=grouped)
    assert len(result) == (4 if grouped else 2)
    for code,rows in result.groupby('Week'):
        _,summary = build_flock_status_report(f,t,a,b,{},resolve_production_week(calendar,code)[1],quota_type='All')
        assert sum(rows['Total Inventory']) == summary['Inventory Birds']
        assert all(row['Total Inventory'] == row['Egg Production']+row['Commercial Pullet Grower'] for row in rows.to_dict('records'))
    assert not result.Week.map(str).str.contains('Total').any()
    originals = [x.copy(deep=True) for x in (f,t,a,b)]
    build_flock_summary_report(f,t,a,b,calendar,202601,202601)
    for x,y in zip((f,t,a,b),originals): pd.testing.assert_frame_equal(x,y)


@pytest.mark.parametrize('start,end',[(202602,202601),(202654,202654),('',202601)])
def test_invalid_ranges(start,end):
    with pytest.raises(ValueError): build_flock_summary_report(*sources(),synthetic_efc_calendar(2026),start,end)


def test_empty_and_calendar_gaps():
    f,t,a,b = sources()
    assert build_flock_summary_report(f.iloc[:0],t,a,b,synthetic_efc_calendar(2026),202601,202602).empty
    with pytest.raises(ValueError,match='Sunday-to-Saturday'):
        resolve_production_week(synthetic_efc_calendar(2026).iloc[1:],202601)


@pytest.mark.parametrize('grouped',[False,True])
def test_absent_type_zero_does_not_turn_unknown_stock_into_zero(grouped):
    f,t,a,b=sources()
    f.loc[f.FLOCK_ID.eq('b'),'STATUS']='Inactive'
    t.loc[t.FLOCK_ID.eq('a'),'QUANTITY']=None
    _,summary=build_flock_status_report(f,t,a,b,{},date(2026,1,3))
    assert summary['Inventory Birds'] is None
    result=build_flock_summary_report(f,t,a,b,synthetic_efc_calendar(2026),202601,202601,group_by_producer=grouped)
    assert result['Total Inventory'].tolist()==['—']
    assert result['Commercial Pullet Grower'].tolist()==[0]


def test_partial_known_total_retains_stock_value_and_discloses_excluded_unknown():
    f,t,a,b=sources()
    f.loc[f.FLOCK_ID.eq('b'),'STATUS']='Inactive'
    t.loc[t.FLOCK_ID.eq('a'),'QUANTITY']=None
    extra=dict(f.iloc[0],FLOCK_ID='known',PERMIT_NUMBER='known',FLOCK_NUMBER='known')
    f=pd.concat([f,pd.DataFrame([extra])],ignore_index=True)
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],FLOCK_ID='known',FLOCK_TRANSACTION_ID='known',QUANTITY=10)])],ignore_index=True)
    result=build_flock_summary_report(f,t,a,b,synthetic_efc_calendar(2026),202601,202601,mortality='0')
    assert result['Total Inventory'].tolist()==[10]
    assert sum('unavailable' in note for note in result.attrs['notes'])==1
