"""Synthetic Friday snapshots with unchanged Sunday-Saturday calendar boundaries."""
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook
from pypdf import PdfReader

from data.efc_calendar import (INVENTORY_AS_OF_WEEK_DAY, EFC_WEEK_END_WEEK_DAY,
    WEEKLY_INVENTORY_CAPTION, synthetic_efc_calendar, resolve_production_week)
from app.services.flock_summary_report import build_flock_summary_report
from app.services.flock_reports import build_flock_status_report
from app.services.report_center import report_csv, report_xlsx, report_definition
from app.services.report_pdf import render_report_pdf
from tests.test_flock_summary_report import sources
from tests.test_report_center import user


@pytest.mark.parametrize('grouped',[False,True])
def test_friday_uses_friday_count_not_saturday_and_exports_same_snapshot(grouped):
    flocks,tx,accounts,facilities=sources()
    tx.loc[tx.FLOCK_ID.eq('a'),['TRANSACTION_DATE','QUANTITY']]=['2026-01-02',120]
    saturday=dict(tx.iloc[0],FLOCK_TRANSACTION_ID='synthetic-saturday',
        TRANSACTION_DATE='2026-01-03',QUANTITY=180)
    tx=pd.concat([tx,pd.DataFrame([saturday])],ignore_index=True)
    calendar=synthetic_efc_calendar(2026)
    assert INVENTORY_AS_OF_WEEK_DAY==4 and EFC_WEEK_END_WEEK_DAY==5
    assert resolve_production_week(calendar,202601)==(date(2025,12,28),date(2026,1,3))
    result=build_flock_summary_report(flocks,tx,accounts,facilities,calendar,202601,202601,
        group_by_producer=grouped)
    assert result['As-of Date'].tolist()==['2026-01-02']
    assert result['Week Start'].tolist()==['2025-12-28']
    assert result['Total Inventory'].tolist()==[120]
    assert ('Account' in result.columns)==grouped
    assert result.attrs['notes']==[WEEKLY_INVENTORY_CAPTION]
    assert 'Friday' in WEEKLY_INVENTORY_CAPTION and 'last day' not in WEEKLY_INVENTORY_CAPTION
    assert 'Friday' in report_definition('flock-summary').description
    csv=pd.read_csv(BytesIO(report_csv(user(),result)))
    assert csv['As-of Date'].tolist()==['2026-01-02'] and csv['Total Inventory'].tolist()==[120]
    book=load_workbook(BytesIO(report_xlsx(user(),result,notes=pd.DataFrame({'Note':result.attrs['notes']}))))
    rows=list(book['EFNS Report'].values)
    assert rows[1][rows[0].index('As-of Date')]=='2026-01-02'
    assert str(rows[1][rows[0].index('Total Inventory')])=='120'
    assert any('Friday' in str(value) for row in book['Notes'].values for value in row)
    pdf=render_report_pdf('Flock Summary',[WEEKLY_INVENTORY_CAPTION],result,
        notes=result.attrs['notes'],report_id='flock-summary')
    text=' '.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert 'Friday' in text and '2026-01-02' in text and '2026-01-03' not in text


@pytest.mark.parametrize('grouped',[False,True])
def test_each_week_reuses_status_at_friday_without_summing_weeks(grouped):
    flocks,tx,accounts,facilities=sources();calendar=synthetic_efc_calendar(2026)
    result=build_flock_summary_report(flocks,tx,accounts,facilities,calendar,202601,202603,
        quota_type='All',group_by_producer=grouped)
    assert set(result.Week)=={202601,202602,202603}
    assert len(result)==(6 if grouped else 3)
    for code,rows in result.groupby('Week'):
        start,end=resolve_production_week(calendar,code)
        friday=start+timedelta(days=5)
        assert friday.weekday()==4 and end.weekday()==5 and (end-start).days==6
        assert set(rows['As-of Date'])=={friday.isoformat()}
        _,expected=build_flock_status_report(flocks,tx,accounts,facilities,{},friday,quota_type='All')
        assert sum(rows['Total Inventory'])==expected['Inventory Birds']
        assert all(row['Total Inventory']==row['Egg Production']+row['Commercial Pullet Grower']
            for row in rows.to_dict('records'))
    assert not result.Week.astype(str).str.contains('Total').any()


@pytest.mark.parametrize('last,first',[(202253,202301),(202652,202701)])
def test_friday_date_across_52_and_53_week_year_boundary(last,first,monkeypatch):
    import app.services.flock_summary_report as module
    calendar=pd.concat([synthetic_efc_calendar(last//100),synthetic_efc_calendar(first//100)])
    seen=[];original=module.build_flock_status_report
    def status(*args,**kwargs):
        seen.append(args[5]);return original(*args,**kwargs)
    monkeypatch.setattr(module,'build_flock_status_report',status)
    build_flock_summary_report(*sources(),calendar,last,first)
    assert seen==[resolve_production_week(calendar,code)[0]+timedelta(days=5) for code in (last,first)]
    assert resolve_production_week(calendar,last)[1]+timedelta(days=1)==resolve_production_week(calendar,first)[0]


@pytest.mark.parametrize('entrypoint',['streamlit_app.py','app/Home.py'])
def test_page_caption_parameters_and_both_downloads_use_friday(entrypoint,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from data.repositories.mock import MockRepository
    import app.services.report_center as exports
    root=Path(__file__).parents[1];repo=MockRepository()
    repo._flocks,repo._flock_transactions,repo._accounts,repo._facilities=sources()
    repo._efc_dates=synthetic_efc_calendar(2026)
    monkeypatch.setattr('data.business_time.halifax_today',lambda:date(2026,1,2))
    captured={};csv_original=exports.report_csv;xlsx_original=exports.report_xlsx
    def csv_export(actor,frame):
        captured['csv']=csv_original(actor,frame);return captured['csv']
    def xlsx_export(actor,frame,**kwargs):
        captured['xlsx']=xlsx_original(actor,frame,**kwargs);return captured['xlsx']
    monkeypatch.setattr(exports,'report_csv',csv_export)
    monkeypatch.setattr(exports,'report_xlsx',xlsx_export)
    app=authenticated_app(root/entrypoint,tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page(('app/pages/' if entrypoint=='streamlit_app.py' else 'pages/')+'4_Reports.py').run()
    app.session_state['report_center_open_report']='flock-summary';app.run()
    assert any(item.value==WEEKLY_INVENTORY_CAPTION for item in app.caption)
    app.button(key='run_flock_summary').click().run()
    assert not app.exception and not app.error
    assert app.session_state['flock_summary_result']['As-of Date'].tolist()==['2026-01-02']
    assert WEEKLY_INVENTORY_CAPTION in app.session_state['flock_summary_parameters']
    assert pd.read_csv(BytesIO(captured['csv']))['As-of Date'].tolist()==['2026-01-02']
    book=load_workbook(BytesIO(captured['xlsx']))
    assert any(WEEKLY_INVENTORY_CAPTION in row for row in book['Notes'].values)
