from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.production_reports import (build_production_report,build_nest_run_report,
    production_rounding_summary,production_compact_caption,production_notes_frame,
    production_grader_options)
from app.services.report_center import report_csv,report_xlsx,report_definition
from tests.production_report_fixtures import mock_fixture
from tests.test_report_center import user


def noisy_source(count=80,*,nest=False):
    records,accounts,_=mock_fixture('grader')
    row=records.iloc[0].to_dict()
    rows=[]
    for i in range(count):
        rows.append(dict(row,PRODUCTION_ID=f'{i:08x}-0000-4000-8000-000000000000',
            TOTAL=row['TOTAL']+(-Decimal('0.25') if i%2 else Decimal('2')),
            MARKETING_TYPE='LB' if nest else 'RE'))
    return pd.DataFrame(rows),accounts


def build(layout,records,accounts):
    if layout=='nest_run':
        return build_nest_run_report(records,accounts,2026,202601,202610)
    grader=next(iter(production_grader_options(records,accounts,202601,202610))) if layout=='grader' else None
    return build_production_report(records,accounts,202601,202610,layout=layout,grader_key=grader)


def test_400_differences_have_one_summary_and_exact_largest_absolute_difference():
    records,accounts=noisy_source(400)
    frame,metadata=build('summary',records,accounts)
    summary=production_rounding_summary(metadata)
    assert summary==('400 source rows have a stored TOTAL that differs from the displayed component sum '
                     'by rounding (largest difference 2 dozens).')
    assert '\n' not in summary and metadata['notes']==[]
    assert len(metadata['rounding_differences'])==400
    assert metadata['rounding_differences'][0]['Difference']==-2
    assert metadata['rounding_differences'][1]['Difference']==Decimal('0.25')
    assert not any(identity in summary for identity in records.PRODUCTION_ID)
    assert frame.loc[frame['Row Type'].eq('Data'),'Total'].eq(1800).all()


@pytest.mark.parametrize('layout',['summary','producer','details','grader','nest_run'])
def test_all_five_exports_have_last_notes_sheet_and_data_only_csv(layout):
    records,accounts=noisy_source(nest=layout=='nest_run')
    frame,metadata=build(layout,records,accounts)
    notes=production_notes_frame(metadata)
    workbook=report_xlsx(user(),frame,notes=notes)
    reader=pd.ExcelFile(BytesIO(workbook))
    assert reader.sheet_names==['EFNS Report','Notes']
    exported=pd.read_excel(reader,sheet_name='EFNS Report',keep_default_na=False)
    assert list(exported)==list(frame) and len(exported)==len(frame)
    exported_notes=pd.read_excel(reader,sheet_name='Notes',keep_default_na=False)
    assert len(exported_notes.loc[exported_notes.Section.eq('Rounding differences')])==80
    assert production_rounding_summary(metadata) in exported_notes.Note.tolist()
    assert any(records.iloc[0].PRODUCTION_ID in note for note in exported_notes.Note)
    csv_bytes=report_csv(user(),frame)
    csv_frame=pd.read_csv(BytesIO(csv_bytes),keep_default_na=False)
    assert len(csv_frame)==len(frame) and list(csv_frame)==list(frame)
    assert b'stored TOTAL' not in csv_bytes and b'Rounding differences' not in csv_bytes
    assert records.iloc[0].PRODUCTION_ID.encode() not in csv_bytes
    pd.testing.assert_frame_equal(exported.astype(str),csv_frame.astype(str))


def test_no_differences_and_nonproduction_workbooks_stay_compatible():
    records,accounts,_=mock_fixture('summary')
    frame,metadata=build('summary',records,accounts)
    assert production_rounding_summary(metadata)==''
    assert metadata['rounding_differences']==[]
    reader=pd.ExcelFile(BytesIO(report_xlsx(user(),frame)))
    assert reader.sheet_names==['EFNS Report']
    reader=pd.ExcelFile(BytesIO(report_xlsx(user(),frame,notes=production_notes_frame(metadata))))
    assert reader.sheet_names[-1]=='Notes'


def test_source_notes_do_not_embed_ids_in_compact_caption_and_notes_formula_escaped():
    records,accounts=noisy_source(1)
    records.loc[0,'JUMBO']=None
    records.loc[0,'PRODUCTION_ID']='=1+1'
    frame,metadata=build('summary',records,accounts)
    caption=production_compact_caption(metadata)
    assert '=1+1' not in caption and 'unknown' in caption
    assert metadata['record_notes']
    notes=pd.read_excel(BytesIO(report_xlsx(user(),frame,notes=production_notes_frame(metadata))),sheet_name='Notes')
    assert any(note.startswith("'=1+1") for note in notes.Note)


def test_nest_rounding_summary_only_counts_included_nest_sources():
    records,accounts=noisy_source(3,nest=True)
    records.loc[0,'MARKETING_TYPE']='RE'
    _,metadata=build('nest_run',records,accounts)
    assert len(metadata['rounding_differences'])==2
    assert records.iloc[0].PRODUCTION_ID not in [item['Production ID'] for item in metadata['rounding_differences']]


@pytest.mark.parametrize('layout',['summary','producer','details','grader','nest_run'])
def test_page_notes_are_one_summary_with_collapsed_details_and_notes_export(layout,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from tests.test_confirmed_quota_reports import Repository
    import app.services.report_center as reports
    records,accounts=noisy_source(nest=layout=='nest_run')
    repo=Repository()
    repo.accounts=accounts
    repo.get_production_report_records=lambda start,end:records
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    report_id='production-nest-run' if layout=='nest_run' else 'production-management-'+layout
    app.session_state['report_center_open_report']=report_id
    exports=[]
    csv_exports=[]
    pdf_frames=[]
    import app.services.report_pdf_ui as pdf_ui
    original_pdf=pdf_ui.pdf_download_button
    def captured_pdf(user,frame,*args,**kwargs):
        pdf_frames.append(frame.copy(deep=True))
        return original_pdf(user,frame,*args,**kwargs)
    monkeypatch.setattr(pdf_ui,'pdf_download_button',captured_pdf)
    original_csv=reports.report_csv
    def captured_csv(*args,**kwargs):
        content=original_csv(*args,**kwargs)
        csv_exports.append(content)
        return content
    monkeypatch.setattr(reports,'report_csv',captured_csv)
    original=reports.report_xlsx
    def captured(*args,**kwargs):
        content=original(*args,**kwargs)
        exports.append(content)
        return content
    monkeypatch.setattr(reports,'report_xlsx',captured)
    app.run()
    prefix=report_definition(report_id).handler
    app.text_input(key=prefix+'_start').set_value('202601')
    app.text_input(key=prefix+'_end').set_value('202610')
    if layout=='grader':
        app.selectbox(key=prefix+'_grader').set_value(next(iter(production_grader_options(records,accounts,202601,202610))))
        app.run()
    app.button(key='run_'+prefix).click().run()
    assert not app.error and not app.exception
    summaries=[item.value for item in app.info if 'stored TOTAL' in item.value]
    assert len(summaries)==1 and summaries[0].startswith('80 source rows')
    assert '\n' not in summaries[0]
    assert all('J2 repeats J' not in item.value for item in app.caption)
    for item in [*app.caption,*app.info,*app.markdown]:
        assert not any(identity in item.value for identity in records.PRODUCTION_ID)
    expander=next(item for item in app.expander if item.label=='Rounding differences')
    assert not expander.proto.expanded
    assert len(app.get('download_button'))==3
    assert exports and pd.ExcelFile(BytesIO(exports[-1])).sheet_names[-1]=='Notes'

    raw=app.session_state[prefix+'_result']
    displayed=app.dataframe[-1].value
    assert 'J2' not in displayed
    assert ('J' in displayed) == (layout != 'nest_run')
    csv_frame=pd.read_csv(BytesIO(csv_exports[-1]),keep_default_na=False)
    xlsx_frame=pd.read_excel(BytesIO(exports[-1]),sheet_name='EFNS Report',keep_default_na=False)
    assert list(displayed)==list(csv_frame)==list(xlsx_frame)
    assert 'J2' not in csv_frame and 'J2' not in xlsx_frame
    # PDF/table/download projections agree; internal calculation alias is retained.
    assert pdf_frames and 'J2' not in pdf_frames[-1]
    pd.testing.assert_frame_equal(pdf_frames[-1],raw.drop(columns=['J2'],errors='ignore'),check_exact=True)
    notes=pd.read_excel(BytesIO(exports[-1]),sheet_name='Notes',keep_default_na=False)
    assert not notes.Note.str.contains('J2',regex=False).any()
    assert len(notes.loc[notes.Section.eq('Rounding differences')])==80
    if layout != 'nest_run':
        assert 'J2' in raw and 'J' in raw


@pytest.mark.parametrize('layout',['summary','producer','details','grader','nest_run'])
def test_all_production_pdfs_have_one_rounding_summary_and_no_internal_diagnostics(layout):
    from pypdf import PdfReader
    from app.services.report_pdf import render_report_pdf
    from app.services.production_reports import production_table_frame
    records,accounts=noisy_source(nest=layout=='nest_run')
    # This produces a source-note ID too; neither ID category belongs in the PDF.
    records.loc[0,'JUMBO']=None
    records.loc[0,'PRODUCTION_ID']='internal-source-note-id'
    frame,metadata=build(layout,records,accounts)
    before=frame.copy(deep=True)
    notes=production_notes_frame(metadata)
    original_notes=notes.copy(deep=True)
    report_id='production-nest-run' if layout=='nest_run' else 'production-management-'+layout
    pdf=render_report_pdf('Production audit',metadata['headers'],frame,notes,report_id=report_id)
    text=' '.join(' '.join(page.extract_text().split()) for page in PdfReader(BytesIO(pdf)).pages)
    summary=production_rounding_summary(metadata)
    assert summary==('79 source rows have a stored TOTAL that differs from the displayed component sum '
                     'by rounding (largest difference 2 dozens).')
    assert text.count(summary)==1
    assert 'Rounding differences:' not in text and 'Source notes:' not in text
    assert 'J2' not in text
    assert not any(identity in text for identity in records.PRODUCTION_ID)
    pd.testing.assert_frame_equal(frame,before,check_exact=True)
    pd.testing.assert_frame_equal(notes,original_notes,check_exact=True)
    # Detailed diagnostics remain available to both the screen expander and XLSX.
    assert metadata['record_notes'] and metadata['rounding_differences']
    assert notes.loc[notes.Section.eq('Source notes'),'Note'].str.contains('internal-source-note-id',regex=False).any()
    workbook=report_xlsx(user(),production_table_frame(frame),notes=notes)
    exported=pd.read_excel(BytesIO(workbook),sheet_name='Notes',keep_default_na=False)
    pd.testing.assert_frame_equal(exported,notes,check_exact=True)
