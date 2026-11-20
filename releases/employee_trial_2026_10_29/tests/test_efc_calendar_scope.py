"""Synthetic calendar edges must not invalidate unrelated stock snapshots."""
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import pytest

from data.efc_calendar import (synthetic_efc_calendar, efc_weeks,
    resolve_production_week, default_flock_summary_weeks)
from app.services.flock_summary_report import build_flock_summary_report
from app.services.report_center import report_csv
from tests.test_flock_summary_report import sources
from tests.test_report_center import user


def calendar_with_bad_edge():
    # Deliberately synthetic final-year week: Sunday followed by ten more days.
    edge = pd.DataFrame([dict(DAY=date(2030,12,29)+timedelta(days=i),
        EFC_YEAR=2031,EFC_WEEK_NUMBER=1) for i in range(11)])
    return pd.concat([synthetic_efc_calendar(2026),edge],ignore_index=True)


@pytest.mark.parametrize('grouped',[False,True])
def test_bad_final_week_does_not_change_earlier_report_values_or_csv(grouped):
    clean=synthetic_efc_calendar(2026);edge=calendar_with_bad_edge()
    assert resolve_production_week(edge,202601)==resolve_production_week(clean,202601)
    assert efc_weeks(edge,202601,202603)==efc_weeks(clean,202601,202603)
    args=sources()
    expected=build_flock_summary_report(*args,clean,202601,202603,group_by_producer=grouped)
    actual=build_flock_summary_report(*args,edge,202601,202603,group_by_producer=grouped)
    pd.testing.assert_frame_equal(actual,expected)
    assert actual.attrs==expected.attrs
    assert report_csv(user(),actual)==report_csv(user(),expected)


@pytest.mark.parametrize('operation',['single','range','defaults','report'])
def test_requested_bad_week_names_it_and_never_builds_inventory(operation,monkeypatch):
    import app.services.flock_summary_report as report
    monkeypatch.setattr(report,'build_flock_status_report',lambda *a,**k:pytest.fail('No numbers for an invalid range'))
    calendar=calendar_with_bad_edge()
    with pytest.raises(ValueError,match=r'Week 203101 is not a complete Sunday-to-Saturday week'):
        if operation=='single':resolve_production_week(calendar,203101)
        elif operation=='range':efc_weeks(calendar,203101,203101)
        elif operation=='defaults':default_flock_summary_weeks(calendar,date(2031,1,2))
        else:report.build_flock_summary_report(*sources(),calendar,202652,203101)


def test_defaults_ignore_bad_edge_and_do_not_validate_future_weeks_in_same_year():
    calendar=calendar_with_bad_edge()
    assert default_flock_summary_weeks(calendar,date(2026,1,2))==(202601,202601)
    assert default_flock_summary_weeks(calendar,date(2026,11,20))==default_flock_summary_weeks(synthetic_efc_calendar(2026),date(2026,11,20))
    future_bad=calendar.loc[calendar.EFC_YEAR.eq(2031)].copy()
    future_bad['EFC_YEAR']=2026;future_bad['EFC_WEEK_NUMBER']=53
    same_year=pd.concat([synthetic_efc_calendar(2026),future_bad],ignore_index=True)
    assert default_flock_summary_weeks(same_year,date(2026,1,2))==(202601,202601)
    assert efc_weeks(same_year,202601,202602)==efc_weeks(synthetic_efc_calendar(2026),202601,202602)


@pytest.mark.parametrize('change',['missing-day','invalid-day','missing-week','gap','overlap'])
def test_bad_requested_range_rejected_with_week_named(change):
    calendar=synthetic_efc_calendar(2026)
    selected=calendar.EFC_WEEK_NUMBER.eq(2)
    if change=='missing-day':calendar=calendar.drop(calendar.loc[selected].index[0])
    elif change=='invalid-day':calendar.loc[calendar.loc[selected].index[0],'DAY']=None
    elif change=='missing-week':calendar=calendar.loc[~selected]
    else:
        offset=7 if change=='gap' else -7
        calendar.loc[selected,'DAY']=calendar.loc[selected,'DAY'].map(lambda value:value+timedelta(days=offset))
    with pytest.raises(ValueError,match='Week 202602'):
        efc_weeks(calendar,202601,202603)
    # Neither a missing day nor inconsistent dates in week 2 invalidate week 1.
    assert resolve_production_week(calendar,202601)==(date(2025,12,28),date(2026,1,3))


def test_defaults_validate_incomplete_current_week_even_when_today_is_missing():
    calendar=synthetic_efc_calendar(2026)
    calendar=calendar.loc[calendar.DAY.ne(date(2026,1,5))]
    with pytest.raises(ValueError,match='Week 202602'):
        default_flock_summary_weeks(calendar,date(2026,1,5))


def test_defaults_do_not_require_historical_week_one_before_a_range_is_chosen():
    calendar=synthetic_efc_calendar(2026)
    calendar=calendar.loc[calendar.DAY.ne(date(2026,1,2))]
    assert default_flock_summary_weeks(calendar,date(2026,1,7))==(202601,202602)
    assert list(efc_weeks(calendar,202602,202602))==[202602]
    with pytest.raises(ValueError,match='Week 202601'):
        efc_weeks(calendar,202601,202602)


@pytest.mark.parametrize('last,first',[(202253,202301),(202652,202701)])
def test_52_and_53_week_year_boundaries_remain_contiguous(last,first):
    calendar=pd.concat([synthetic_efc_calendar(last//100),synthetic_efc_calendar(first//100),
        calendar_with_bad_edge().loc[lambda frame:frame.EFC_YEAR.eq(2031)]],ignore_index=True)
    weeks=efc_weeks(calendar,last,first)
    assert list(weeks)==[last,first]
    assert weeks[last][1]+timedelta(days=1)==weeks[first][0]
    assert default_flock_summary_weeks(calendar,weeks[last][1])==(last//100*100+1,last)


def test_missing_year_inside_range_is_not_silently_skipped():
    calendar=pd.concat([synthetic_efc_calendar(2026),synthetic_efc_calendar(2028)])
    with pytest.raises(ValueError,match='Week 202701'):
        efc_weeks(calendar,202652,202801)


@pytest.mark.parametrize('entrypoint',['streamlit_app.py','app/Home.py'])
@pytest.mark.parametrize('bad_first',[False,True],ids=['future-edge','historical-week-one'])
def test_page_uses_scoped_defaults_and_clear_requested_week_message(entrypoint,bad_first,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from data.repositories.mock import MockRepository
    import data.business_time as business_time
    monkeypatch.setattr(business_time,'halifax_today',lambda:date(2026,1,7) if bad_first else date(2026,1,2))
    root=Path(__file__).parents[1];repo=MockRepository()
    repo._flocks,repo._flock_transactions,repo._accounts,repo._facilities=sources()
    repo._efc_dates=calendar_with_bad_edge()
    if bad_first:repo._efc_dates=repo._efc_dates.loc[repo._efc_dates.DAY.ne(date(2026,1,2))]
    app=authenticated_app(root/entrypoint,tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    prefix='app/pages/' if entrypoint=='streamlit_app.py' else 'pages/'
    app.switch_page(prefix+'4_Reports.py').run()
    app.session_state['report_center_open_report']='flock-summary'
    app.run()
    assert not app.exception and not app.error
    assert app.text_input(key='flock_summary_start').value=='202601'
    if bad_first:app.text_input(key='flock_summary_start').set_value('202602')
    app.button(key='run_flock_summary').click().run()
    assert not app.exception and not app.error
    assert app.session_state['flock_summary_result'].Week.tolist()==[202602 if bad_first else 202601]
    app.text_input(key='flock_summary_start').set_value('203101')
    app.text_input(key='flock_summary_end').set_value('203101')
    app.button(key='run_flock_summary').click().run()
    assert not app.exception and not app.error
    assert any('Week 203101 is not a complete Sunday-to-Saturday week' in item.value for item in app.info)
    assert app.session_state.filtered_state.get('flock_summary_result') is None
