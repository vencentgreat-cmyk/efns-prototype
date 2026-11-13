"""Confirmed legacy Count choice and visible explanations; no database access."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from app.services.flock_current_report import build_flock_current_report, latest_observation
from app.services.flock_reports import build_flock_status_report, build_flock_status_by_producer_report
from app.services.report_pdf import note_lines
from tests.test_flock_status_asof import example

ROOT=Path(__file__).resolve().parents[1]
DAY=date(2026,7,31)


def fixture():
    # Placement/hatch are synthetic past dates; the two Counts are user-confirmed.
    f,t,a=example('40357',38866,placement='2026-01-01',hatch='2025-09-01')
    a['REGISTRATION_NUMBER']='7159'
    row=dict(t.iloc[0],TRANSACTION_DATE='2026-07-10',COUNT_SOURCE_LABEL='Producer',UPDATED_AT='2026-10-30')
    t=pd.DataFrame([dict(row,QUANTITY=39440,COUNT_SOURCE_LABEL=None,UPDATED_AT='2026-10-21'),row])
    return f,t,a


def status(f,t,a):
    return build_flock_status_report(f,t,a,pd.DataFrame(),{'bayview':42980},DAY)


@pytest.mark.parametrize('reverse',[False,True])
def test_40357_sourced_count_yields_legacy_inventory_and_context_note(reverse):
    f,t,a=fixture();before=t.copy(deep=True)
    if reverse:t=t.iloc[::-1]
    when,chosen,counted,note=latest_observation(t.to_dict('records'))
    assert when==date(2026,7,10) and counted==38866
    assert chosen['COUNT_SOURCE_LABEL']=='Producer' and 'sourced record was used' in note
    current=build_flock_current_report(f,t,a,DAY)
    assert current.iloc[0].Counted==38866 and current.iloc[0].Inventory==38758
    result,summary=status(f,t,a)
    assert result.iloc[1].Inventory==38758 and summary['Inventory Birds']==38758
    expected='7159, permit 40357: 2 Counts on 2026-07-10 with different quantities; the sourced record was used'
    assert expected in summary['Notes'] and result.attrs['notes']==[expected]
    assert note_lines(result)==[expected]  # Existing PDF footnotes see the same note.
    selected,selected_summary=build_flock_status_by_producer_report(f,t,a,pd.DataFrame(),
        {'bayview':42980},DAY,'bayview')
    pd.testing.assert_frame_equal(selected,result)
    assert expected in selected_summary['Notes']
    pd.testing.assert_frame_equal(t.sort_index(),before.sort_index())


def test_one_distinct_sourced_quantity_wins_even_when_blank_record_is_newer():
    f,t,a=fixture();t.loc[0,'UPDATED_AT']='2026-11-01'
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[1],COUNT_SOURCE_LABEL='Board')])],ignore_index=True)
    row=build_flock_current_report(f,t,a,DAY).iloc[0]
    assert row.Counted==38866 and row.Inventory==38758
    assert '3 Counts' in row.Notes and 'sourced record' in row.Notes


def test_both_blank_use_latest_updated_with_note():
    f,t,a=fixture();t['COUNT_SOURCE_LABEL']=[None,'   ']
    result,summary=status(f,t,a)
    assert result.iloc[1].Inventory==38758
    assert 'most recently updated record was used' in summary['Notes']
    assert '7159, permit 40357' in summary['Notes']
    assert latest_observation(t.to_dict('records'))[2]==38866


@pytest.mark.parametrize('sources',[['Producer','Board'],[None,'']])
def test_differing_latest_timestamp_tie_stays_conflict(sources):
    f,t,a=fixture();t['COUNT_SOURCE_LABEL']=sources;t['UPDATED_AT']='2026-10-30T12:00:00Z'
    current=build_flock_current_report(f,t,a,DAY)
    assert current.iloc[0].Counted==current.iloc[0].Inventory=='—'
    assert current.iloc[0].Notes=='Count conflict'
    result,summary=status(f,t,a)
    assert result.iloc[1].Inventory=='—'
    assert '7159, permit 40357: Count conflict' in summary['Notes']


def test_multiple_sourced_quantities_then_newest_row_wins():
    f,t,a=fixture();t.loc[0,'COUNT_SOURCE_LABEL']='Board'
    assert latest_observation(t.to_dict('records'))[2]==38866
    assert 'most recently updated record' in status(f,t,a)[1]['Notes']
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],QUANTITY=38000,COUNT_SOURCE_LABEL=None,
        UPDATED_AT='2026-11-01')])],ignore_index=True)
    assert latest_observation(t.to_dict('records'))[2]==38000


def test_newest_timestamp_rows_agree_quantity_so_sources_do_not_conflict():
    f,t,a=fixture();t['COUNT_SOURCE_LABEL']='Producer'
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[1],COUNT_SOURCE_LABEL='Board')])],ignore_index=True)
    assert latest_observation(t.to_dict('records'))[2]==38866
    assert 'most recently updated record' in status(f,t,a)[1]['Notes']


def test_timestamp_order_normalizes_utc_without_changing_business_date():
    f,t,a=fixture();t['COUNT_SOURCE_LABEL']=['Producer','Board']
    t['UPDATED_AT']=['2026-10-30T15:00:00Z','2026-10-30T12:00:00-03:00']
    assert latest_observation(t.to_dict('records'))[2] is None
    t.loc[1,'UPDATED_AT']='2026-10-30T12:00:01-03:00'
    when,_,counted,_=latest_observation(t.to_dict('records'))
    assert when==date(2026,7,10) and counted==38866


@pytest.mark.parametrize('bad',[None,'not-a-date',pd.NaT])
def test_missing_or_invalid_ordering_evidence_keeps_conflict(bad):
    f,t,a=fixture();t['COUNT_SOURCE_LABEL']=['Producer','Board'];t.loc[0,'UPDATED_AT']=bad
    row=build_flock_current_report(f,t,a,DAY).iloc[0]
    assert row.Counted==row.Inventory=='—' and row.Notes=='Count conflict'


@pytest.mark.parametrize('bad',[None,-1,1.5])
def test_invalid_quantities_still_flagged_despite_sourced_or_latest_record(bad):
    f,t,a=fixture();t['QUANTITY']=t.QUANTITY.astype(object);t.loc[0,'QUANTITY']=bad
    row=build_flock_current_report(f,t,a,DAY).iloc[0]
    assert row.Counted==row.Inventory=='—' and row.Notes=='Invalid Count quantity'


def test_equal_quantities_need_no_tie_break_or_extra_note():
    f,t,a=fixture();t['QUANTITY']=38866;t['UPDATED_AT']=None
    _,chosen,counted,note=latest_observation(t.to_dict('records'))
    assert counted==38866 and chosen['COUNT_SOURCE_LABEL']=='Producer' and note==''
    result,summary=status(f,t,a)
    assert result.iloc[1].Inventory==38758 and not result.attrs.get('notes')
    assert summary['Notes']=='0 Account quota(s) unavailable; 0 flock Inventory value(s) excluded'


def test_note_uses_account_name_when_registration_is_missing():
    f,t,a=fixture();a['REGISTRATION_NUMBER']=None
    result,summary=status(f,t,a)
    assert 'Bayview, permit 40357:' in summary['Notes']
    assert result.iloc[1].Inventory==38758


def test_latest_business_date_and_count_priority_stay_ahead_of_update_time():
    f,t,a=fixture()
    extra=[dict(t.iloc[0],TRANSACTION_TYPE='Delivery',QUANTITY=1,COUNT_SOURCE_LABEL='Board',UPDATED_AT='2030-01-01'),
           dict(t.iloc[0],TRANSACTION_DATE='2026-07-01',QUANTITY=2,UPDATED_AT='2030-01-01'),
           dict(t.iloc[0],TRANSACTION_DATE='2026-08-01',QUANTITY=3,UPDATED_AT='2030-01-01')]
    t=pd.concat([t,pd.DataFrame(extra)],ignore_index=True)
    row=build_flock_current_report(f,t,a,DAY).iloc[0]
    assert row.Counted==38866 and row['Count Date']=='2026-07-10' and row.Inventory==38758


@pytest.mark.parametrize('handler',['flock_status','flock_status_producer'])
def test_tie_break_note_is_visible_in_report_center(handler,tmp_path,monkeypatch):
    from data.repositories.mock import MockRepository
    from tests.auth_support import authenticated_app
    f,t,a=fixture();repo=MockRepository()
    repo.get_flocks=lambda:f;repo.get_accounts=lambda:a
    repo.get_facilities=lambda:pd.DataFrame();repo.get_flock_transactions=lambda:t
    repo.get_quota_registrations=lambda:pd.DataFrame([dict(QUOTA_ID='q',ACCOUNT_ID='bayview',
        QUOTA_TYPE='Egg Production',STATUS='Active')])
    repo.get_quota_transactions=lambda:pd.DataFrame([dict(QUOTA_TRANSACTION_ID='base',QUOTA_ID='q',
        OWNER_ACCOUNT_ID='bayview',TRANSACTION_TYPE='Base',QUOTA_COUNT=42980,EFFECTIVE_DATE='2020-01-01')])
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    app.session_state['report_center_open_report']=handler.replace('_','-')
    app.run()
    if handler=='flock_status_producer':app.selectbox(key=handler+'_account').set_value('bayview').run()
    app.date_input(key=handler+'_date').set_value(DAY)
    app.button(key='run_'+handler).click().run()
    assert not app.exception and not app.error
    assert any('7159, permit 40357: 2 Counts on 2026-07-10 with different quantities; '
        'the sourced record was used' in caption.value for caption in app.caption)
    assert app.dataframe[0].value.iloc[1].Inventory==38758
