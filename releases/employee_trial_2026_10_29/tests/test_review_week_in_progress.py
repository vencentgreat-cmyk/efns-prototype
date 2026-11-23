"""Synthetic current/future weekly snapshots; no quota or inventory formula change."""
from datetime import date
from io import BytesIO
import pandas as pd
import pytest
from openpyxl import load_workbook
from pypdf import PdfReader
from data.efc_calendar import synthetic_efc_calendar
from app.services.flock_summary_report import build_flock_summary_report
from app.services.flock_reports import build_flock_status_report
from app.services.report_center import report_csv,report_xlsx
from app.services.report_pdf import render_report_pdf
from tests.test_flock_summary_report import sources
from tests.test_report_center import user

LABEL='as of today (week in progress)'


@pytest.mark.parametrize('today,week,expected,capped',[
    (date(2026,1,5),202602,'2026-01-05',True),
    (date(2026,1,12),202601,'2026-01-02',False),
    (date(2026,1,5),202603,'2026-01-05',True),
    (date(2025,12,31),202601,'2025-12-31',True),
    (date(2026,1,2),202601,'2026-01-02',False),
    (date(2026,1,3),202601,'2026-01-02',False),
])
def test_snapshot_cap_and_completed_weeks(today,week,expected,capped):
    args=sources();result=build_flock_summary_report(*args,synthetic_efc_calendar(2026),week,week,today=today)
    assert result['As-of Date'].tolist()==[expected]
    assert ('As-of Note' in result.columns)==capped
    if capped:assert result['As-of Note'].tolist()==[LABEL]
    _,reference=build_flock_status_report(*args,{},date.fromisoformat(expected))
    assert result['Total Inventory'].tolist()==[reference['Inventory Birds']]


def test_mixed_weeks_preserve_completed_row_and_never_add_week_totals():
    args=sources();calendar=synthetic_efc_calendar(2026)
    completed=build_flock_summary_report(*args,calendar,202601,202601,today=date(2026,1,5))
    mixed=build_flock_summary_report(*args,calendar,202601,202603,today=date(2026,1,5))
    pd.testing.assert_frame_equal(completed,mixed.iloc[:1][completed.columns].reset_index(drop=True))
    assert mixed.Week.tolist()==[202601,202602,202603]
    assert mixed['As-of Note'].tolist()==['',LABEL,LABEL]


def test_capped_label_and_date_are_in_csv_xlsx_and_pdf():
    result=build_flock_summary_report(*sources(),synthetic_efc_calendar(2026),202602,202602,today=date(2026,1,5))
    csv=pd.read_csv(BytesIO(report_csv(user(),result)))
    assert csv['As-of Note'].tolist()==[LABEL] and csv['As-of Date'].tolist()==['2026-01-05']
    book=load_workbook(BytesIO(report_xlsx(user(),result,notes=pd.DataFrame({'Note':result.attrs['notes']}))))
    assert LABEL in list(book['EFNS Report'].values)[1]
    pdf=render_report_pdf('Flock Summary',[],result,notes=result.attrs['notes'],report_id='flock-summary')
    text=' '.join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert LABEL in ' '.join(text.split()) and '2026-01-05' in text
