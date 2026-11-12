"""Synthetic legacy-shaped Production PDFs, without database connections."""
from io import BytesIO
import re
from uuid import UUID

import pandas as pd
import pytest
from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from app.services.production_reports import build_production_report, COMPONENTS, AMOUNTS
from app.services.production_pdf import (PDF_COLUMNS, PDF_LABELS, production_pdf_rows,
    production_table_layout, MIN_PRODUCTION_FONT)
from app.services.report_pdf import render_report_pdf, pdf_display_rows
from app.services.report_pdf_ui import pdf_download_button
from app.services.report_center import report_csv, report_xlsx
from tests.test_report_center import user
from tests.test_report_pdf import FakeUI


def synthetic_source(count=4):
    account=str(UUID(int=1))
    records=[]
    for index in range(count):
        row={field:(index % 13 + 1) * 100 for field in COMPONENTS.values()}
        row.update(PRODUCTION_ID=str(UUID(int=index+100)), IMPORT_ID=None,
            PRODUCER_ACCOUNT_ID=account, SOURCE_WEEK_CODE=202601+index % 53,
            MARKETING_TYPE='Regulated', EGG_TYPE='Regular', HOUSING_SYSTEM='Enriched',
            EGG_COLOUR='White', TOTAL=sum(row.values()))
        records.append(row)
    return pd.DataFrame(records), pd.DataFrame([dict(ACCOUNT_ID=account,
        REGISTRATION_NUMBER='0001', ORGANIZATION_NAME='Synthetic Farm')])


def example(layout, count=4):
    records,accounts=synthetic_source(count)
    return build_production_report(records,accounts,202601,202653,['Regulated'],layout=layout)


@pytest.mark.parametrize('layout',['summary','details'])
@pytest.mark.parametrize('path',['mock','snowflake'])
def test_existing_repository_reads_reach_pdf_without_new_sql(layout,path):
    from data.repositories.mock import MockRepository
    from data.repositories.snowflake import SnowflakeRepository
    records,accounts=synthetic_source()
    if path=='mock':
        repo=MockRepository();repo._production=records;repo._import_batches=[]
    else:
        repo=SnowflakeRepository.__new__(SnowflakeRepository)
        repo.database='EFNS_DEV';repo.schema_core='CORE'
        def offline_query(sql,params):
            assert params==(202601,202653)
            assert 'BETWEEN %s AND %s' in sql and 'EFNS_DEV.CORE.PRODUCTION_RECORD' in sql
            return records.copy()
        repo._query=offline_query
    frame,meta=build_production_report(repo.get_production_report_records(202601,202653),
        accounts,202601,202653,['Regulated'],layout=layout)
    pdf=render_report_pdf('Production Management '+layout.title(),meta['headers'],frame,
        report_id='production-management-'+layout)
    assert PdfReader(BytesIO(pdf)).pages


@pytest.mark.parametrize('layout',['summary','details'])
def test_pdf_projection_preserves_every_total_and_export(layout):
    frame,meta=example(layout)
    original=frame.copy(deep=True)
    csv_before=report_csv(user(),frame)
    xlsx_before=pd.read_excel(BytesIO(report_xlsx(user(),frame)))
    display=pdf_display_rows(frame,'production-management-'+layout)
    rows,weeks,totals=production_pdf_rows(display)
    assert rows[0]==[PDF_LABELS.get(column,column) for column in PDF_COLUMNS]
    assert not {'Account Name','Grading Station','J2','Week','Row Type'} & set(rows[0])
    projected=[row for index,row in enumerate(rows[1:],1) if index not in weeks]
    for source,row in zip(display[1:],projected):
        for col in PDF_COLUMNS[5:]:
            assert row[PDF_COLUMNS.index(col)]==source[display[0].index(col)]
    assert len(projected)==len(frame) and totals
    pdf=render_report_pdf('Production Management '+layout.title(),meta['headers'],frame,
        report_id='production-management-'+layout)
    reader=PdfReader(BytesIO(pdf));text='\n'.join(page.extract_text() for page in reader.pages)
    for value in ('Production Week: 202601 to 202653','Type: Regulated','In Dozens',
                  'provisional HALF_UP','Grand Total','0001'):
        assert value in text
    assert 'J2' not in rows[0]  # It remains disclosed in the provisional wording.
    # Verify actual PDF text for every total value, without suppressing unknowns.
    for index in totals:
        for value in rows[index][5:]:
            assert value and value in text
    assert all(tuple(map(int,(page.mediabox.width,page.mediabox.height)))==(792,612) for page in reader.pages)
    pd.testing.assert_frame_equal(original,frame)
    assert report_csv(user(),frame)==csv_before
    pd.testing.assert_frame_equal(xlsx_before,pd.read_excel(BytesIO(report_xlsx(user(),frame))))


@pytest.mark.parametrize('layout',['summary','details'])
def test_small_pdf_has_no_empty_second_page(layout):
    frame,meta=example(layout,1)
    reader=PdfReader(BytesIO(render_report_pdf('Small Production',meta['headers'],frame,
        report_id='production-management-'+layout)))
    assert len(reader.pages)==1 and 'Grand Total' in reader.pages[0].extract_text()


def test_long_numeric_registration_preserves_leading_zeros_on_one_line():
    frame,meta=example('summary',1)
    frame.loc[frame['Row Type'].eq('Data'),'Reg No']='0000000123456789'
    pdf=render_report_pdf('Registration',meta['headers'],frame,report_id='production-management-summary')
    text=PdfReader(BytesIO(pdf)).pages[0].extract_text()
    assert '0000000123456789' in text


@pytest.mark.parametrize('layout',['summary','details'])
def test_full_year_paginates_repeats_headers_and_keeps_numeric_cells_atomic(layout):
    frame,meta=example(layout,1300)
    rows,_,_=production_pdf_rows(pdf_display_rows(frame,'production-management-'+layout))
    size,widths=production_table_layout(rows,744)
    assert size>=MIN_PRODUCTION_FONT and abs(sum(widths)-744)<.001
    for row in rows[1:]:
        for col,value in enumerate(row[5:],5):
            assert stringWidth(value,'Helvetica-Bold',size)+4<=widths[col]
    reader=PdfReader(BytesIO(render_report_pdf('Full Year Production',meta['headers'],frame,
        report_id='production-management-'+layout)))
    assert len(reader.pages)>1
    for page in reader.pages:
        text=page.extract_text()
        assert 'REG#' in text and 'Non Levy' in text and 'In Dozens' in text
        assert re.search(r'Production Week: 2026\d{2}\n|Grand Total',text)
    assert 'Grand Total' in reader.pages[-1].extract_text()


@pytest.mark.parametrize('layout',['summary','details'])
def test_legal_only_when_letter_cannot_fit_numbers(layout):
    frame,meta=example(layout,1)
    for column in AMOUNTS:frame[column]=10**8
    rows,_,_=production_pdf_rows(pdf_display_rows(frame,'production-management-'+layout))
    assert production_table_layout(rows,744) is None
    assert production_table_layout(rows,960) is not None
    reader=PdfReader(BytesIO(render_report_pdf('Large Quantities',meta['headers'],frame,
        report_id='production-management-'+layout)))
    assert tuple(map(int,(reader.pages[0].mediabox.width,reader.pages[0].mediabox.height)))==(1008,612)
    assert '100,000,000' in reader.pages[0].extract_text()


@pytest.mark.parametrize('layout',['summary','details'])
def test_refuse_when_even_legal_cannot_preserve_numbers(layout):
    from app.services.report_pdf import PDFExportError
    frame,meta=example(layout,1)
    for column in AMOUNTS:frame[column]=10**12
    with pytest.raises(PDFExportError,match='CSV or XLSX'):
        render_report_pdf('Too wide',meta['headers'],frame,report_id='production-management-'+layout)


@pytest.mark.parametrize('layout',['summary','details'])
def test_empty_pdf_control_is_a_clear_message_without_download(layout):
    frame,meta=example(layout)
    target=FakeUI()
    pdf_download_button(user(),frame.iloc[:0],'Empty',meta['headers'],'report.pdf',
        'production-management-'+layout,target=target)
    assert not target.downloads
    assert target.messages==['No production records match the selected parameters; PDF export is unavailable.']


@pytest.mark.parametrize('layout',['summary','details'])
def test_pdf_export_keeps_permission_and_audit(layout,monkeypatch):
    import app.auth
    calls=[]
    class Store:
        def record_action(self,*args):calls.append(args)
    monkeypatch.setattr(app.auth,'get_auth_store',lambda:Store())
    frame,meta=example(layout,1);target=FakeUI(clicked=True)
    report_id='production-management-'+layout
    pdf_download_button(user(),frame,'Production',meta['headers'],'report.pdf',report_id,target=target)
    assert target.downloads[0][0][1].startswith(b'%PDF-')
    assert calls[0][1:]==('EXPORT','REPORT',report_id,{'format':'PDF','row_count':len(frame)})
    denied=FakeUI()
    pdf_download_button(user(active=False),frame,'Production',[],'report.pdf',report_id,target=denied)
    assert not denied.downloads and len(calls)==1
