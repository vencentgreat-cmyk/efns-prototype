"""Production unit/weekly invariants from synthetic data only."""
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from pypdf import PdfReader

from app.services.production_reports import (AMOUNTS, COMPONENTS, build_production_report,
    production_grader_options, production_table_frame, production_notes_frame)
from app.services.production_presentation import (DOZENS_PER_BOX, BOXES_CAPTION,
    boxes_from_dozens, production_units_frame, production_report_view,
    production_view_metadata, production_csv_frame)
from app.services.report_center import report_csv, report_xlsx
from app.services.report_pdf import render_report_pdf
from tests.test_report_center import user

LAYOUTS = ('summary', 'producer', 'details', 'grader')


def synthetic_source():
    accounts = pd.DataFrame([
        dict(ACCOUNT_ID='account-'+key, ORGANIZATION_NAME='Synthetic '+key,
             REGISTRATION_NUMBER='R-'+key, GRADER_ROLE=key=='g') for key in ('a','b','g')])
    records = []
    for i,(owner,week) in enumerate([('a',202601),('a',202602),('b',202601),('b',202602)]):
        row = dict(PRODUCTION_ID='synthetic-'+str(i), IMPORT_ID=None,
            PRODUCER_ACCOUNT_ID='account-'+owner, PRODUCER_NUMBER='R-'+owner,
            GRADER_ACCOUNT_ID='account-g', GRADER_NAME='Synthetic g', GRADER_NUMBER='R-g',
            SOURCE_WEEK_CODE=week, MARKETING_TYPE='RE', EGG_TYPE='', HOUSING_SYSTEM='', EGG_COLOUR='')
        row.update({field:Decimal((29,30,44,45)[(i+j)%4]) for j,field in enumerate(COMPONENTS.values())})
        row['TOTAL'] = sum(row[field] for field in COMPONENTS.values())
        records.append(row)
    return pd.DataFrame(records), accounts


def build(layout):
    records,accounts=synthetic_source()
    grader=next(iter(production_grader_options(records,accounts,202601,202602))) if layout=='grader' else None
    frame,metadata=build_production_report(records,accounts,202601,202602,layout=layout,grader_key=grader)
    return frame,metadata


@pytest.mark.parametrize('dozens,boxes',[(29,1),(30,2),(44,2),(45,3),(0,0),(-1,-1)])
def test_named_box_factor_and_exact_floor(dozens,boxes):
    assert type(DOZENS_PER_BOX) is int and DOZENS_PER_BOX==15
    assert boxes_from_dozens(Decimal(dozens))==boxes
    assert boxes_from_dozens(None) is None


@pytest.mark.parametrize('layout',LAYOUTS)
def test_dozens_preserves_every_existing_row_and_csv_value(layout):
    before,_=build(layout)
    pd.testing.assert_frame_equal(production_units_frame(before),before,check_exact=True)
    assert production_units_frame(before).to_csv(index=False)==before.to_csv(index=False)
    shown=production_report_view(before)
    if layout!='summary':
        shown=shown.loc[~shown['Row Type'].isin(['Week Totals','Week Total'])].reset_index(drop=True)
    pd.testing.assert_frame_equal(shown,before,check_exact=True)
    assert report_csv(user(),production_csv_frame(production_table_frame(shown)))==report_csv(user(),production_table_frame(before))


@pytest.mark.parametrize('layout',LAYOUTS)
@pytest.mark.parametrize('unit',['Dozens','Boxes'])
def test_week_producer_grand_invariants_and_boxes_are_sums_of_converted_rows(layout,unit):
    original,_=build(layout)
    view=production_report_view(original,unit)
    data=view.loc[view['Row Type'].eq('Data')]
    assert len(data)==4
    weeks=view.loc[view['Row Type'].eq('Week Total')]
    assert weeks.Week.tolist()==[202601,202602]
    final=view.iloc[-1]
    for col in AMOUNTS:
        for _,row in weeks.iterrows(): assert row[col]==data.loc[data.Week.eq(row.Week),col].sum()
        assert final[col]==data[col].sum()==weeks[col].sum()
    if layout=='producer':
        for _,row in view.loc[view['Row Type'].eq('Producer Total')].iterrows():
            for col in AMOUNTS: assert row[col]==data.loc[data['Reg No'].eq(row['Reg No']),col].sum()
    if unit=='Boxes':
        old=original.loc[original['Row Type'].eq('Data')].reset_index(drop=True)
        converted=data.reset_index(drop=True)
        for i in range(len(old)):
            for col in COMPONENTS: assert converted.loc[i,col]==old.loc[i,col]//DOZENS_PER_BOX
            assert converted.loc[i,'Levy']==sum(converted.loc[i,list(COMPONENTS)[:8]])
            assert converted.loc[i,'NonLevy']==sum(converted.loc[i,list(COMPONENTS)[8:]])
            assert converted.loc[i,'Total']==converted.loc[i,'Levy']+converted.loc[i,'NonLevy']
        assert final['Total'] < original.iloc[-1]['Total']//DOZENS_PER_BOX
        pd.testing.assert_frame_equal(converted.drop(columns=AMOUNTS),old.drop(columns=AMOUNTS),check_exact=True)
    assert 'J2' not in production_table_frame(view)


@pytest.mark.parametrize('layout',LAYOUTS)
@pytest.mark.parametrize('unit',['Dozens','Boxes'])
def test_weekly_only_all_exports_headers_and_pdf(layout,unit):
    frame,metadata=build(layout)
    frame=production_report_view(frame,unit,weekly_totals_only=True)
    metadata=production_view_metadata(metadata,unit,weekly_totals_only=True)
    assert frame['Row Type'].tolist()==['Week Total','Week Total','Grand Total']
    shown=production_table_frame(frame)
    csv=report_csv(user(),production_csv_frame(shown))
    csv_frame=pd.read_csv(BytesIO(csv),keep_default_na=False)
    expected=[col+' (Boxes)' if unit=='Boxes' and col in AMOUNTS else col for col in shown]
    assert list(csv_frame)==expected
    assert csv.decode('utf-8-sig').splitlines()[0].startswith('Row Type,Week,')
    assert ('J (Boxes)' in csv_frame)==(unit=='Boxes')
    notes=production_notes_frame(metadata)
    workbook=report_xlsx(user(),shown,notes=notes)
    excel=pd.read_excel(BytesIO(workbook),keep_default_na=False)
    assert list(excel)==list(shown) and len(excel)==3
    pd.testing.assert_frame_equal(excel.astype(str).rename(columns=dict(zip(shown,expected))),csv_frame.astype(str))
    assert ('In '+unit) in notes.iloc[0].Note
    if unit=='Boxes':assert BOXES_CAPTION in notes.iloc[0].Note
    pdf=render_report_pdf('Synthetic Production',metadata['headers'],shown,notes,
        report_id='production-management-'+layout)
    text=' '.join(' '.join(page.extract_text().split()) for page in PdfReader(BytesIO(pdf)).pages)
    assert 'In '+unit in text and 'Week Total' in text and 'Grand Total' in text
    assert 'J2' not in text
    if unit=='Boxes':assert BOXES_CAPTION in text and 'In Dozens' not in text


def test_null_zero_empty_and_invalid_unit_do_not_invent_values():
    frame,_=build('producer')
    frame.loc[frame['Row Type'].eq('Data'),list(AMOUNTS)]=0
    view=production_report_view(frame,'Boxes')
    assert view.loc[view['Row Type'].eq('Data'),list(AMOUNTS)].eq(0).all().all()
    frame.loc[frame['Row Type'].eq('Data'),'J']=''
    assert production_report_view(frame,'Boxes').loc[lambda f:f['Row Type'].eq('Data'),'J'].eq('').all()
    empty=production_report_view(frame.iloc[:0],'Boxes',weekly_totals_only=True)
    assert empty.empty and list(empty)==list(frame)
    with pytest.raises(ValueError):production_report_view(frame,'Unknown')


@pytest.mark.parametrize('layout',LAYOUTS)
@pytest.mark.parametrize('unit,weekly_only',[('Dozens',False),('Boxes',True)])
def test_page_unit_and_weekly_controls_drive_all_export_paths(layout,unit,weekly_only,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from tests.test_report_smoke import smoke_repository
    import app.services.report_center as exports
    from app.services.production_reports import production_grader_options
    repo=smoke_repository('normal');records,accounts=synthetic_source()
    repo._accounts=accounts
    repo.get_production_report_records=lambda start,end:records.copy(deep=True)
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    app.session_state['report_center_open_report']='production-management-'+layout
    app.run();prefix='production_management_'+layout
    assert app.selectbox(key=prefix+'_unit').value=='Dozens'
    assert app.checkbox(key=prefix+'_weekly_only').value is False
    app.selectbox(key=prefix+'_unit').set_value(unit)
    app.checkbox(key=prefix+'_weekly_only').set_value(weekly_only)
    app.text_input(key=prefix+'_start').set_value('202601')
    app.text_input(key=prefix+'_end').set_value('202602')
    if layout=='grader':
        app.selectbox(key=prefix+'_grader').set_value(next(iter(production_grader_options(records,accounts,202601,202602))))
    calls=[];original=exports.report_csv
    def capture(user,frame):
        calls.append(frame.copy(deep=True));return original(user,frame)
    monkeypatch.setattr(exports,'report_csv',capture)
    app.button(key='run_'+prefix).click().run()
    assert not app.exception and not app.error
    result=app.session_state[prefix+'_result']
    assert result.attrs['unit']==unit
    assert ('Data' not in result['Row Type'].tolist())==weekly_only
    assert result['Row Type'].eq('Week Total').sum()==2
    assert calls and ('J (Boxes)' in calls[-1])==(unit=='Boxes')
    assert any(item.value=='In '+unit for item in app.markdown)
