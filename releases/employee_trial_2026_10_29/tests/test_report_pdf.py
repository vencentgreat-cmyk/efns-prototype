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
    note_lines,MIN_FONT_SIZE,MAX_PDF_ROWS,PDFExportError,ROW_LIMIT_MESSAGE,
    QUANTITY_COLUMNS_BY_REPORT,PRODUCTION_QUANTITIES,NEST_RUN_QUANTITIES,group_quantity,pdf_display_rows)
from app.services.report_pdf_ui import pdf_download_button,audit_pdf_export,custom_parameter_lines
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
    reader,text=read_pdf(render_report_pdf(definition.name,[SUBTITLE],frame,generated_at=NOW,report_id=definition.report_id))
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
    _,text=read_pdf(render_report_pdf('Production',metadata['headers'],frame,report_id='production-management-summary'))
    assert '202601' in text and '202602' in text and '1,288,762' in text


@pytest.mark.parametrize('value,expected',[
    ('34526','34,526'),('34526.00','34,526'),('34526.0','34,526'),
    ('1027985.0000','1,027,985'),('1234.5000','1,234.5000'),
    ('-34526.00','-34,526'),('-1234.5000','-1,234.5000'),('+34526.00','+34,526'),
    ('0.00','0'),('-0.00','-0'),('.1250','0.1250'),('1.23E-5','0.0000123'),
    ('1E6','1,000,000'),('1,027,985.00','1,027,985'),('', ''),('—','—'),
    ('12,34','12,34'),('12.50%','12.50%'),('2026-11-09','2026-11-09'),
    ('123456789012345678901234567890.12345678901234567890',
     '123,456,789,012,345,678,901,234,567,890.12345678901234567890'),
])
def test_quantity_grouping_rules_without_rounding(value,expected):
    assert group_quantity(value)==expected


@pytest.mark.parametrize('definition',AVAILABLE,ids=lambda r:r.report_id)
def test_explicit_allowlist_per_report_and_identifier_columns_unchanged(definition):
    allowed=QUANTITY_COLUMNS_BY_REPORT[definition.report_id]
    ungrouped={'Reg No':'07173','Registration Number':'07173','Permit No':'000040285',
        'Flock Number':'000040285','Week':'202601','Year':'2026','Flock Age':'1000',
        'Disposal Age':'1000','Start Date Age':'1000','End Date Age':'1000','Age':'1000',
        'Transaction Date':'20261109','Account ID':'1234567890','Util.':'102.53%',
        'Phone':'9028956341','Not Allowlisted':'34526.00'}
    frame=pd.DataFrame([{**ungrouped,**{label:'34526.00' for label in allowed}}])
    original=csv_display_rows(frame)
    grouped=pdf_display_rows(frame,definition.report_id)
    assert grouped[0]==original[0]
    for index,label in enumerate(grouped[0]):
        assert grouped[1][index]==('34,526' if label in allowed else original[1][index])


def test_allowlist_catalog_and_actual_report_columns():
    from app.services.report_center import CUSTOM_DATASETS,FLOCK_RECORD_COUNT_LABEL
    from app.services.production_reports import AMOUNTS,NEST_FIELDS
    assert set(QUANTITY_COLUMNS_BY_REPORT)=={r.report_id for r in AVAILABLE}
    assert PRODUCTION_QUANTITIES==tuple(AMOUNTS)
    assert NEST_RUN_QUANTITIES==tuple(NEST_FIELDS)
    for definition in AVAILABLE:
        allowed=set(QUANTITY_COLUMNS_BY_REPORT[definition.report_id])
        if definition.report_id=='custom-builder':
            labels={f.label for _,_,fields in CUSTOM_DATASETS.values() for f in fields}
            labels.update({FLOCK_RECORD_COUNT_LABEL,'Record count','Source Total known count','Source Total missing count'})
            assert allowed<=labels
        elif definition.handler not in FORM_HANDLERS:
            source=run_report(definition,smoke_repository('normal'),'normal')
            frame=source[0] if isinstance(source,tuple) else source
            assert allowed<=set(frame.columns),(definition.report_id,allowed-set(frame.columns))
        else:
            assert not allowed  # Preserve specialized legacy form formatting.


def test_grouped_detail_and_total_pdf_keeps_csv_xlsx_and_source_unchanged():
    row={'Reg No':'07173','Account':'Farm','Permit No':'000040285','Counted':Decimal('34526.00'),
         'Inventory':Decimal('1027985.1250'),'Up. Flocks':Decimal('-1234.00'),'Util.':'102.53%','Flock Age':'1000'}
    frame=pd.DataFrame([row,dict(row,Account='Account Total',**{'Reg No':'—','Permit No':'—'})])
    original=frame.copy(deep=True)
    csv_before=report_csv(user(),frame)
    xlsx_before=pd.read_excel(BytesIO(report_xlsx(user(),frame)))
    _,text=read_pdf(render_report_pdf('Flock Current Report',[SUBTITLE],frame,report_id='flock-current'))
    for value in ('34,526','1,027,985.1250','-1,234'):
        assert text.count(value)==2
    for value in ('07173','000040285','102.53%','1000'):assert value in text
    assert '40,285' not in text and '2,026' not in text
    pd.testing.assert_frame_equal(frame,original)
    assert report_csv(user(),frame)==csv_before
    pd.testing.assert_frame_equal(pd.read_excel(BytesIO(report_xlsx(user(),frame))),xlsx_before)


def test_unknown_report_and_missing_context_never_infer_quantities():
    frame=pd.DataFrame({'Inventory':['34526.00'],'Permit No':['000040285']})
    assert pdf_display_rows(frame)==csv_display_rows(frame)
    assert pdf_display_rows(frame,'unregistered-report')==csv_display_rows(frame)


def test_pdf_adapter_passes_explicit_catalog_id(monkeypatch):
    import app.services.report_pdf_ui as adapter
    captured=[]
    def render(*args,**kwargs):captured.append(kwargs['report_id']);return b'fixture'
    monkeypatch.setattr(adapter,'render_report_pdf',render)
    adapter.pdf_download_button(user(),pd.DataFrame({'Issuance':['34526.00']}),'Quota',[],
        'quota.pdf','quota-summary',target=FakeUI())
    assert captured==['quota-summary']


def test_custom_pdf_friendly_subtitles_headers_and_unbroken_guid():
    guid='421FEF51-ABCD-1234-ABCD-123456789ABC'
    configuration={'dataset':'Accounts','selected_fields':['ACCOUNT_ID','ORGANIZATION_NAME','PROVINCE'],
        'filters':{'province':'NS','statuses':['Active']},'sort_by':'ORGANIZATION_NAME',
        'ascending':True,'count_records':False,'group_by':['PROVINCE'],'aggregations':{}}
    expected=['Dataset: Accounts','Province: NS','Status: Active',
              'Sorted by: Account Name (ascending)','Grouped by: Province']
    assert custom_parameter_lines(configuration)==expected
    frame=pd.DataFrame({'Account ID':[guid],'Account Name':['Example Farm'],'Province':['NS']})
    original=frame.copy(deep=True)
    csv_before=report_csv(user(),frame)
    xlsx_before=report_xlsx(user(),frame)
    _,text=read_pdf(render_report_pdf('Custom Report',expected,frame,report_id='custom-builder'))
    subtitle=text.split('Dataset: Accounts',1)[1].split('Account ID',1)[0]
    for line in expected:assert line in text
    for forbidden in ('selected_fields','count_records','ascending:','[',']','ACCOUNT_ID','Fields:'):
        assert forbidden not in subtitle
    for header in frame.columns:assert header in text
    assert guid in [line.strip() for line in text.splitlines()]
    pd.testing.assert_frame_equal(frame,original)
    assert report_csv(user(),frame)==csv_before
    pd.testing.assert_frame_equal(pd.read_excel(BytesIO(report_xlsx(user(),frame))),
                                  pd.read_excel(BytesIO(xlsx_before)))


def test_custom_pdf_date_filters_and_internal_flags_are_not_parameters():
    configuration={'dataset':'Flocks','selected_fields':['PLACEMENT_DATE'],
        'filters':{'date_from':'2026-01-01','date_to':'2026-11-09','date_field':'PLACEMENT_DATE',
                   'quota_type':'Egg Production','statuses':('Active','Planned'),'facility_id':None},
        'sort_by':'PLACEMENT_DATE','ascending':False,'group_by':[], 'count_records':True}
    assert custom_parameter_lines(configuration)==['Dataset: Flocks','Quota Type: Egg Production',
        'Status: Active, Planned','Placement Date: 2026-01-01 to 2026-11-09',
        'Sorted by: Placement Date (descending)']
    assert custom_parameter_lines({'dataset':'Accounts','filters':{'province':'All','unknown':{'x':1}},
        'sort_by':None,'group_by':[],'ascending':False,'count_records':False})==['Dataset: Accounts']


def test_custom_pdf_identifiers_trigger_landscape_and_preserve_sparse_outlier():
    guid='AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA'
    frame=pd.DataFrame({header:[guid] for header in ('Account ID','Facility ID','Quota ID','Flock ID')})
    frame['Account Name']='Example Farm'
    frame['Province']='NS'
    reader,text=read_pdf(render_report_pdf('Custom Report',['Dataset: Flocks'],frame,report_id='custom-builder'))
    assert tuple(map(int,(reader.pages[0].mediabox.width,reader.pages[0].mediabox.height)))==(792,612)
    assert [line.strip() for line in text.splitlines()].count(guid)==4
    sparse=pd.DataFrame({'Account ID':['a']*150+[guid]+['a']*5,'Account Name':['Farm']*156})
    _,text=read_pdf(render_report_pdf('Custom Report',[],sparse,report_id='custom-builder'))
    assert guid in [line.strip() for line in text.splitlines()]


def test_custom_pdf_refuses_identifiers_that_cannot_fit_landscape():
    frame=pd.DataFrame({f'Identifier {i} ID':['A'*100] for i in range(6)})
    with pytest.raises(PDFExportError,match='CSV or XLSX'):
        render_report_pdf('Custom Report',[],frame,report_id='custom-builder')


def test_custom_and_saved_pdf_use_applied_configuration(tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    import app.services.report_pdf_ui as adapter
    captured=[]
    def capture(title,lines,frame,*args,**kwargs):
        captured.append((list(lines),frame.copy(deep=True)))
        return b'fixture PDF'
    monkeypatch.setattr(adapter,'render_report_pdf',capture)
    app=authenticated_app(ROOT/'app'/'Home.py',tmp_path,monkeypatch)
    app.switch_page('pages/4_Reports.py').run()
    app.radio(key='report_center_section').set_value('Customize Report').run()
    app.selectbox(key='custom_filter_status').set_value('Active').run()
    app.selectbox(key='custom_report_sort').set_value('Account Name').run()
    next(button for button in app.button if button.label=='Run Report').click().run()
    assert not app.exception and not app.error
    expected=['Dataset: Accounts','Status: Active','Sorted by: Account Name (ascending)']
    assert captured[-1][0]==expected
    applied=captured[-1][1]
    app.text_input(key='custom_report_save_name').set_value('Staff accounts').run()
    next(button for button in app.button if button.label=='Save configuration').click().run()
    app.selectbox(key='custom_filter_status').set_value('Inactive').run()
    assert captured[-1][0]==expected  # Unapplied widgets must not relabel the PDF.
    app.radio(key='report_center_section').set_value('Saved Reports').run()
    next(button for button in app.button if button.label=='Run saved report').click().run()
    assert not app.exception and not app.error
    assert captured[-1][0]==expected
    pd.testing.assert_frame_equal(captured[-1][1],applied)


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
