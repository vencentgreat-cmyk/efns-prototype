"""Catalog-wide PDF validity, exact values, pagination and export safeguards."""
import csv
from datetime import datetime,timezone
from decimal import Decimal
from io import BytesIO,StringIO
from pathlib import Path
import hashlib
import json
import re

import pandas as pd
import pytest
from pypdf import PdfReader
from pypdf.generic import ContentStream

from app.services.report_center import REPORT_CATALOG,report_csv,report_xlsx
from app.services.report_pdf import (render_report_pdf,csv_display_rows,table_layout,is_total_row,
    note_lines,MIN_FONT_SIZE,MAX_PDF_ROWS,PDFExportError,ROW_LIMIT_MESSAGE)
from app.services.report_pdf_ui import pdf_download_button,audit_pdf_export
from app.services.printable_forms import FORM_HANDLERS,render_form_pdf
from tests.test_report_smoke import smoke_repository,run_report
from tests.test_printable_forms import example_form
from tests.test_report_center import user
from app.security import Role,AuthorizationError

AVAILABLE=[r for r in REPORT_CATALOG if r.status=='Available']
SUBTITLE='For Egg Production as 01/01/2026 to 09/11/2026'
NOW=datetime(2026,1,2,1,2,3,tzinfo=timezone.utc)
ROOT=Path(__file__).resolve().parents[1]


def read_pdf(data):
    reader=PdfReader(BytesIO(data))
    return reader,'\n'.join(page.extract_text() for page in reader.pages)


@pytest.mark.parametrize('definition',AVAILABLE,ids=lambda r:r.report_id)
@pytest.mark.parametrize('case',['normal','empty','nulls','no_rows','over_limit'])
def test_every_available_report_pdf(definition,case):
    source=run_report(definition,smoke_repository('normal' if case=='over_limit' else case),'normal' if case=='over_limit' else case)
    frame=source[0] if isinstance(source,tuple) else source
    if case=='over_limit':
        frame=pd.DataFrame({str(column):['']*(MAX_PDF_ROWS+1) for column in frame.columns})
        if not len(frame.columns):frame=pd.DataFrame({'Value':['']*(MAX_PDF_ROWS+1)})
        with pytest.raises(PDFExportError,match='CSV or XLSX'):
            render_report_pdf(definition.name,[SUBTITLE],frame)
        return
    original=frame.copy(deep=True)
    csv_before=report_csv(user(),frame)
    xlsx_before=report_xlsx(user(),frame)
    reader,text=read_pdf(render_report_pdf(definition.name,[SUBTITLE],frame,generated_at=NOW))
    assert reader.pages and definition.name in ' '.join(text.split())
    assert SUBTITLE in ' '.join(text.split())
    assert not re.search(r'(?<!\w)(None|nan|NaT|<NA>)(?!\w)',text)
    flat=re.sub(r'\s+','',text)
    for column in frame.columns:assert re.sub(r'\s+','',str(column)) in flat
    if frame.empty:assert 'No records found' in text
    assert tuple(map(int,(reader.pages[0].mediabox.width,reader.pages[0].mediabox.height)))==((792,612) if len(frame.columns)>7 else (612,792))
    pd.testing.assert_frame_equal(frame,original)
    assert report_csv(user(),frame)==csv_before
    # XLSX zip timestamps are not part of table values; compare every cell.
    pd.testing.assert_frame_equal(pd.read_excel(BytesIO(xlsx_before)),pd.read_excel(BytesIO(report_xlsx(user(),frame))))


def test_exact_csv_values_html_escaping_and_missing_cells():
    frame=pd.DataFrame({'Account':['<b>A & B</b>','Total',None],
        'Precise':[Decimal('1234567.1234567890123456789'),Decimal('0.00000000000001'),None],
        'Registration':['0001','0002',pd.NA], 'Date':[pd.Timestamp('2026-11-09'),pd.NaT,pd.NaT]})
    expected=list(csv.reader(StringIO(frame.to_csv(index=False))))
    rows=csv_display_rows(frame)
    assert rows==expected
    _,text=read_pdf(render_report_pdf('Precision',[SUBTITLE],frame,notes=['None','nan','NaT','<NA>']))
    compact=re.sub(r'\s+','',text)
    for value in ('1234567.1234567890123456789',expected[2][1],'0001','<b>A & B</b>'):
        assert re.sub(r'\s+','',value) in compact
    assert not re.search(r'(?<!\w)(None|nan|NaT|<NA>)(?!\w)',text)


def test_pages_repeat_headers_and_halifax_page_count_footer():
    frame=pd.DataFrame({'Account':['Wrapped farm name with several words']*150,'Amount':range(150)})
    frame.attrs['notes']=['Evidence note']
    reader,text=read_pdf(render_report_pdf('Paged',[SUBTITLE],frame,notes=['Extra note'],generated_at=NOW))
    assert len(reader.pages)>1
    for n,page in enumerate(reader.pages,1):
        content=page.extract_text()
        assert f'Page {n} of {len(reader.pages)}' in content
        assert '2026-01-01 21:02:03 AST (America/Halifax)' in content
        assert 'Account' in content and 'Amount' in content and SUBTITLE in content
    assert text.rfind('Extra note')>text.rfind('149')
    assert note_lines(frame,['Evidence note','Extra note'])==['Evidence note','Extra note']


@pytest.mark.parametrize('label',['Total','Totals','Subtotal','Account Total','Quota Total','Grand Total','Week Total','Producer Total','Grader Total','Total Bird Count','Producers: 24'])
def test_existing_total_labels_get_bold_grey_rows(label):
    assert is_total_row(['Reg No','Account Name'],['',label])
    reader,_=read_pdf(render_report_pdf('Totals',[],pd.DataFrame({'Account Name':['Farm',label],'Amount':[1,1]})))
    ops=ContentStream(reader.pages[0].get_contents(),reader).operations
    assert any(op==b'rg' and all(abs(float(v)-.866667)<.00001 for v in args) for args,op in ops if len(args)==3)
    assert not is_total_row(['Account Name'],['Total Egg Farm Ltd.'])


def test_wide_table_has_no_columns_outside_letter_and_font_floor():
    frame=pd.DataFrame({f'Long header {i}':['Long text and quantity 123456789.12345'] for i in range(35)})
    size,widths=table_layout(csv_display_rows(frame),744)
    assert size>=MIN_FONT_SIZE and abs(sum(widths)-744)<.00001
    reader,text=read_pdf(render_report_pdf('Wide',[SUBTITLE],frame))
    compact=re.sub(r'\s+','',text)
    for column in frame.columns:assert re.sub(r'\s+','',column) in compact
    # Check extracted glyph coordinates, not merely the presence of PDF bytes.
    from pypdf._text_extraction import mult
    for page in reader.pages:
        def visitor(text,cm,tm,font,size):
            x=mult(tm,cm)[4]
            if text.strip():assert 0<=x<=792
        page.extract_text(visitor_text=visitor)


def test_production_week_codes_and_totals_do_not_wrap_or_round():
    from tests.production_report_fixtures import mock_fixture
    from app.services.production_reports import build_production_report
    records,accounts,_=mock_fixture('summary')
    frame,metadata=build_production_report(records,accounts,202601,202602)
    _,text=read_pdf(render_report_pdf('Production',metadata['headers'],frame))
    assert '202601' in text and '202602' in text and '1288762' in text


def test_forms_keep_specialized_layout_and_apply_row_guard():
    for handler in FORM_HANDLERS:
        form=example_form(handler)
        assert PdfReader(BytesIO(render_form_pdf(form))).pages
        key=next(iter(form.tables))
        form.tables[key]=[form.tables[key][0]]*(MAX_PDF_ROWS+1)
        with pytest.raises(PDFExportError,match='CSV or XLSX'):render_form_pdf(form)


class FakeUI:
    def __init__(self,clicked=False):self.clicked=clicked;self.downloads=[];self.messages=[]
    def download_button(self,*args,**kwargs):self.downloads.append((args,kwargs));return self.clicked
    def info(self,message):self.messages.append(message)
    def button(self,*args,**kwargs):assert kwargs['disabled']


def test_pdf_permission_audit_and_oversize_ui(monkeypatch):
    import app.auth
    calls=[]
    class Store:
        def record_action(self,*args):calls.append(args)
    monkeypatch.setattr(app.auth,'get_auth_store',lambda:Store())
    frame=pd.DataFrame({'Account':['Farm']})
    target=FakeUI(clicked=True)
    pdf_download_button(user(),frame,'Report',[SUBTITLE],'report.pdf','quota-summary',target=target)
    assert calls[-1][1:]==('EXPORT','REPORT','quota-summary',{'format':'PDF','row_count':1})
    assert target.downloads[0][0][0]=='Export PDF'
    denied=user(active=False)
    with pytest.raises(AuthorizationError):audit_pdf_export(denied,'quota-summary',1)
    target=FakeUI(clicked=True)
    pdf_download_button(denied,frame,'Report',[],'report.pdf','quota-summary',target=target)
    assert not target.downloads and len(calls)==1
    target=FakeUI()
    pdf_download_button(user(),pd.DataFrame({'Value':['']*5001}),'Report',[],'report.pdf','quota-summary',target=target)
    assert target.messages==[ROW_LIMIT_MESSAGE] and not target.downloads


def test_pdf_manifest_artifacts():
    manifest=json.loads((ROOT/'DELIVERY_RUNTIME_DIFF_20261030.json').read_text())
    for entry in manifest['report_pdf_artifacts']:
        raw=(ROOT/entry['path']).read_bytes().replace(b'\r\n',b'\n')
        assert hashlib.sha256(raw).hexdigest()==entry['candidate_lf_sha256'],entry['path']
