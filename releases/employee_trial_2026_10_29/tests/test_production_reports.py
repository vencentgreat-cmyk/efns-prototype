from collections import Counter
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.production_reports import (build_production_report,build_nest_run_report,
    prepare_production,production_grader_options,production_week,validate_week,COMPONENTS,AMOUNTS,NEST_FIELDS)
from app.services.report_center import report_csv,report_xlsx,report_definition
from tests.production_report_fixtures import mock_fixture,read_fixture,amount,MEASURES,expected_signature
from tests.test_report_center import user


@pytest.mark.parametrize('layout,count',[('summary',79),('producer',79),('details',25),('grader',129)])
def test_every_fixture_detail_number_and_displayed_totals(layout,count):
    records,accounts,expected=mock_fixture(layout)
    start,end=(202601,202610) if layout=='grader' else (202601,202602)
    grader=next(iter(production_grader_options(records,accounts,start,end))) if layout=='grader' else None
    frame,meta=build_production_report(records,accounts,start,end,layout=layout,grader_key=grader)
    details=frame.loc[frame['Row Type'].eq('Data')]
    actual=[(row['Reg No'],row['Week'],row['Marketing Type'],*[row[key] for key in MEASURES]) for row in details.to_dict('records')]
    assert len(details)==count
    assert Counter(actual)==Counter(expected_signature(row,layout) for row in expected)
    assert not meta['notes']
    assert details.J.tolist()==details.J2.tolist()
    grand=frame.iloc[-1]
    for key in AMOUNTS:
        assert grand[key]==details[key].sum()
    for row in expected:
        # Verify every SSRS repeated subtotal number where its scope can be
        # reconstructed from supplied detail fields; never feed it to builder.
        week=int(row.get('Production_Week2') or row.get('Production_Week1'))
        reg=row['Registration_Number'] if layout=='summary' else row['Production_Week']
        scoped=details.loc[details['Reg No'].eq(reg)&details.Week.eq(week)&details['Marketing Type'].eq(row['MarketingType'])]
        if layout=='summary':
            scoped=scoped.loc[scoped.Specialty.eq(row['SpecialtyType1'])&scoped['Housing System'].eq(row['HousingSystemType'])&scoped.Colour.eq(row['Colour1'])]
        for key,index in zip(MEASURES,range(171,190)):
            assert scoped[key].sum()==amount(row[f'Textbox{index}'])
        if layout=='summary':
            scoped=details.loc[details.Week.eq(week)]
            for key,index in zip(MEASURES,range(216,235)):
                assert scoped[key].sum()==amount(row[f'Textbox{index}'])
            for key,index in zip(MEASURES,range(3,22)):
                assert grand[key]==amount(row[f'Textbox{index}'])
        elif layout in ('producer','grader','details'):
            scoped=details.loc[details['Reg No'].eq(reg)]
            for key,index in zip(MEASURES,range(216,235)):
                assert scoped[key].sum()==amount(row[f'Textbox{index}'])
        if layout=='grader':
            indexes=[*range(10,23),*range(27,33)]
            for key,index in zip(MEASURES,indexes):
                assert grand[key]==amount(row[f'Textbox{index}'])


def test_summary_week_totals_first_and_producer_totals_once():
    records,accounts,_=mock_fixture('summary')
    frame,_=build_production_report(records,accounts,202601,202602)
    assert frame.iloc[0]['Row Type']=='Week Total'
    assert frame.loc[frame.Week.eq(202602)].iloc[0]['Row Type']=='Week Total'
    assert frame.iloc[-1].Total==1288762
    frame,_=build_production_report(records,accounts,202601,202602,layout='producer')
    assert len(frame.loc[frame['Row Type'].eq('Producer Total')])==26


def test_7022_rounding_stored_total_mismatch_and_half_up_is_provisional():
    records,accounts,_=mock_fixture('grader')
    target=records.PRODUCER_NUMBER.eq('7022')&records.SOURCE_WEEK_CODE.eq(202602)
    records.loc[target,'TOTAL']=24945
    rows,meta=prepare_production(records,accounts,202601,202610)
    row=next(row for row in rows if row['Reg No']=='7022' and row['Week']==202602)
    assert row['Levy']==24502 and row['NonLevy']==442 and row['Total']==24944
    assert meta['notes']==[]
    assert len(meta['rounding_differences'])==1 and meta['rounding_differences'][0]['Difference']==-1
    one=records.loc[target].copy()
    one.loc[:,list(COMPONENTS.values())]=Decimal('0.5')
    rows,meta=prepare_production(one,accounts,202601,202610)
    assert rows[0]['Levy']==8 and rows[0]['NonLevy']==8 and rows[0]['Total']==16
    assert 'PROVISIONAL' in meta['rounding']


def test_nest_run_zero_leghorn_rows_activity_inclusion_and_absent_weeks():
    records,accounts,_=mock_fixture('producer')
    frame,meta=build_nest_run_report(records,accounts,2026,202601,202610)
    details=frame.loc[frame['Row Type'].eq('Data')]
    assert details['Reg No'].tolist()==['7082','7082']
    assert details.Week.tolist()==[202601,202602]
    assert details[list(NEST_FIELDS)].eq(0).all().all()
    assert any('PROVISIONAL Nest Run' in note for note in meta['notes'])
    records.loc[0,'NEST_RUN_25_PLUS']=Decimal('3')
    frame,_=build_nest_run_report(records,accounts,2026,202601,202610)
    assert frame.loc[frame['Row Type'].eq('Data'),'NR25'].sum()==3
    with pytest.raises(ValueError): build_nest_run_report(records,accounts,2025,202601,202610)


def test_nulls_tests_identity_separation_filters_and_input_immutability():
    records,accounts,_=mock_fixture('details')
    before=records.copy(deep=True)
    filtered,_=build_production_report(records,accounts,202601,202602,marketing_types=['Leghorn Breeder'])
    assert filtered.loc[filtered['Row Type'].eq('Data'),'Reg No'].tolist()==['7082']
    pd.testing.assert_frame_equal(records,before)
    records=records.iloc[:2].copy()
    records.loc[0,'PRODUCER_ACCOUNT_ID']=None
    records.loc[0,'PRODUCER_NUMBER']=None
    records.loc[0,'JUMBO']=None
    records.loc[1,'PRODUCTION_ID']='DEV_TEST_record'
    rows,meta=prepare_production(records,accounts,202601,202602)
    assert len(rows)==1 and rows[0]['J'] is None and rows[0]['Total'] is None
    assert rows[0]['_producer'].startswith('UNIDENTIFIED:') and meta['notes']
    with pytest.raises(ValueError): build_production_report(records,accounts,202601,202602,layout='grader')
    empty,_=build_production_report(records,accounts,202601,202602,marketing_types=[])
    assert empty.empty


@pytest.mark.parametrize('value',[202600,202654,None,'invalid'])
def test_invalid_weeks(value):
    with pytest.raises(ValueError): validate_week(value)


def test_week_sources_and_fallback():
    assert production_week({'SOURCE_WEEK_CODE':'2026-W01'})==202601
    assert production_week({'SOURCE_WEEK_CODE':202601.0})==202601
    assert production_week({'REPORTING_YEAR':2026,'REPORTING_WEEK':2})==202602


def test_bound_repository_read_and_mock_fixture_coverage():
    from data.repositories.snowflake import SnowflakeRepository,PRODUCTION_COLUMNS
    from data.repositories.mock import MockRepository
    records,accounts,_=mock_fixture('grader')
    repo=MockRepository()
    repo._production=records.assign(IMPORT_ID=None)
    repo._import_batches=[]
    actual=repo.get_production_report_records(202601,202610)
    assert len(actual)==129 and 'NEST_RUN_17_PLUS' in actual
    repository=SnowflakeRepository.__new__(SnowflakeRepository)
    repository.database='EFNS_DEV';repository.schema_core='CORE'
    captured={}
    repository._query=lambda sql,params:captured.update(sql=sql,params=params) or pd.DataFrame()
    repository.get_production_report_records(202601,202610)
    assert captured['params']==(202601,202610)
    assert 'EFNS_DEV.CORE.PRODUCTION_RECORD' in captured['sql']
    assert 'SELECT *' not in captured['sql'] and 'BETWEEN %s AND %s' in captured['sql']
    projection=captured['sql'].split('SELECT ',1)[1].split(' FROM ',1)[0].split(', ')
    assert len(projection)==len(set(projection))
    for field in ['PRODUCTION_ID','IMPORT_ID','SOURCE_FILE_ID',*PRODUCTION_COLUMNS]:
        assert field in captured['sql']


@pytest.mark.parametrize('layout',['summary','producer','details','grader','nest_run'])
def test_catalog_page_and_formula_safe_exports(layout,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from tests.test_confirmed_quota_reports import Repository
    from app.auth import get_auth_store
    records,accounts,_=mock_fixture('grader' if layout=='grader' else 'producer')
    accounts.loc[0,'ORGANIZATION_NAME']='=1+1'
    report_id='production-nest-run' if layout=='nest_run' else 'production-management-'+layout
    definition=report_definition(report_id)
    assert definition.status=='Available' and definition.export_formats==('CSV','XLSX','PDF')
    repo=Repository()
    repo.accounts=accounts
    repo.get_production_report_records=lambda start,end:records
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    monkeypatch.setattr(get_auth_store(),'record_action',lambda *args,**kwargs:pytest.fail('Report must remain read-only'))
    app.session_state['report_center_open_report']=report_id
    app.run()
    prefix=definition.handler
    app.text_input(key=prefix+'_start').set_value('202601')
    app.text_input(key=prefix+'_end').set_value('202610')
    if layout=='grader':
        assert app.button(key='run_'+prefix).disabled
        selector=app.selectbox(key=prefix+'_grader')
        selector.set_value(next(key for key in production_grader_options(records,accounts,202601,202610)))
        app.run()
    app.button(key='run_'+prefix).click().run()
    assert not app.error and not app.exception and len(app.dataframe)==1
    assert len(app.get('download_button'))==3
    assert 'PRODUCTION_ID' not in app.dataframe[0].value
    frame=app.session_state[prefix+'_result']
    if layout!='nest_run':
        for exported in [pd.read_csv(BytesIO(report_csv(user(),frame))),pd.read_excel(BytesIO(report_xlsx(user(),frame)))]:
            assert "'=1+1" in exported['Account Name'].tolist()
