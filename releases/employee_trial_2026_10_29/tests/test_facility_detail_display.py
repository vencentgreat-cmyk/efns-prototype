"""Synthetic Facility Detail display regressions; no live data or Snowflake."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from app.navigation import format_timestamp
from app.security import Role
from app.services.facility_detail_display import (
    FACILITY_DETAIL_FIELDS, facility_detail_value, facility_detail_values, facility_detail_frame,
)
from data.repositories.snowflake import MODEL
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain

ROOT = Path(__file__).resolve().parents[1]
LABELS = ['Name','Facility','Account','Facility Type','Date Installed','Bird Colour',
          'Width','Length','Height','Cage Brand','Highest # Birds per Cage','Number of Cages',
          'Birds Housed','Square Inches (W*L)','EIMS Facility Detail ID','Status','Comments','Created On']


@pytest.fixture
def detail_record(chain):
    repo,account,other,facility,quota,flock,_ = chain
    record = dict(FACILITY_DETAIL_ID='SYNTHETIC-detail',FACILITY_ID=facility,
                  DETAIL_NAME='Synthetic cage block',DETAIL_TYPE='Enriched',STATUS='Active',
                  COMMENTS='Synthetic comments',DATE_INSTALLED=date(2024,2,29),BIRD_COLOUR='Brown',
                  WIDTH=Decimal('12.3456'),LENGTH=Decimal('20.1250'),HEIGHT=Decimal('7.5000'),
                  CAGE_BRAND='Synthetic cage brand',HIGHEST_BIRDS_PER_CAGE=Decimal('6.5000'),
                  NUMBER_OF_CAGES=0,BIRDS_HOUSED=0,SQUARE_INCHES=Decimal('999.9999'),
                  EIMS_FACILITY_DETAIL_ID='000SYN-DETAIL',CREATED_AT=pd.Timestamp('2026-01-05T16:00:00Z'),
                  UPDATED_AT=pd.Timestamp('2026-01-05T16:00:00Z'))
    repo._facility_details=pd.DataFrame([record])
    return repo,record


def test_only_existing_data_fields_have_friendly_labels():
    assert [label for _,label in FACILITY_DETAIL_FIELDS]==LABELS
    stored={field for field,_ in FACILITY_DETAIL_FIELDS}-{'FACILITY_NAME','ACCOUNT_NAME','CREATED_AT'}
    assert stored <= set(MODEL['FACILITY_DETAIL'][1].split())
    assert not any(label in LABELS for label in ['Nest Box Length','Nest Box Width','Square Inch per Bird'])


@pytest.mark.parametrize('missing',[None,pd.NA,pd.NaT,float('nan'),'', '   ','None','nan','<NA>'])
def test_empty_values_are_dash(missing):
    for field,_ in FACILITY_DETAIL_FIELDS:
        assert facility_detail_value(field,missing,timestamp_formatter=format_timestamp)=='—'


def test_stored_decimal_zero_and_area_are_not_recomputed(detail_record):
    repo,record=detail_record
    before=repo._facility_details.copy(deep=True)
    values=facility_detail_values(record,timestamp_formatter=format_timestamp)
    assert values['Date Installed']=='2024-02-29'
    assert values['Width']=='12.3456' and values['Length']=='20.1250' and values['Height']=='7.5000'
    assert values['Highest # Birds per Cage']=='6.5000'
    assert values['Number of Cages']=='0' and values['Birds Housed']=='0'
    assert values['Square Inches (W*L)']=='999.9999'
    assert Decimal(values['Square Inches (W*L)'])!=record['WIDTH']*record['LENGTH']
    assert values['EIMS Facility Detail ID']=='000SYN-DETAIL'
    pd.testing.assert_frame_equal(before,repo._facility_details)


def test_old_mock_shape_and_empty_frame():
    frame=facility_detail_frame(pd.DataFrame([dict(DETAIL_NAME='Old synthetic detail',DETAIL_TYPE='Legacy choice')]))
    assert frame.columns.tolist()==LABELS and frame.iloc[0]['Facility Type']=='Legacy choice'
    assert frame.iloc[0]['Width']=='—' and frame.iloc[0]['Date Installed']=='—'
    empty=facility_detail_frame(pd.DataFrame())
    assert empty.empty and empty.columns.tolist()==LABELS


@pytest.mark.parametrize('value', ['not-a-date', 1234])
def test_invalid_date_is_not_invented(value):
    assert facility_detail_value('DATE_INSTALLED',value)==str(value)


def detail_app(repo,tmp_path,monkeypatch,entrypoint,prefix,view='list',role=Role.ADMIN):
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local')
    monkeypatch.setenv('REPOSITORY_MODE','mock')
    app=authenticated_app(ROOT/entrypoint,tmp_path,monkeypatch,role)
    app.session_state['_base_repo']=repo
    app.session_state['_efns_record_13_Facility_Details_view']=view
    app.session_state['_efns_record_13_Facility_Details_id']='SYNTHETIC-detail' if view=='detail' else None
    return app.switch_page(f'{prefix}/13_Facility_Details.py').run()


ENTRYPOINTS=[('streamlit_app.py','app/pages'),('app/Home.py','pages')]


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_list_labels_all_stored_fields_and_row_identity(detail_record,tmp_path,monkeypatch,entrypoint,prefix):
    repo,record=detail_record;before=repo._facility_details.copy(deep=True)
    app=detail_app(repo,tmp_path,monkeypatch,entrypoint,prefix)
    assert not app.exception and not app.error
    shown=app.dataframe[0].value
    assert shown.columns.tolist()==LABELS
    assert shown.iloc[0]['Facility Type']=='Enriched'
    assert shown.iloc[0]['Date Installed']=='2024-02-29'
    assert shown.iloc[0]['Cage Brand']=='Synthetic cage brand'
    assert shown.iloc[0]['Bird Colour']=='Brown'
    assert shown.iloc[0]['Number of Cages']=='0' and shown.iloc[0]['Birds Housed']=='0'
    assert shown.iloc[0]['Square Inches (W*L)']=='999.9999'
    assert shown.iloc[0]['EIMS Facility Detail ID']=='000SYN-DETAIL'
    assert shown.iloc[0]['Created On']==format_timestamp(record['CREATED_AT'])
    assert app.session_state['facility_detail_list_row_ids']==['SYNTHETIC-detail']
    assert not set(shown.columns)&{'DETAIL_TYPE','STATUS','COMMENTS'}
    pd.testing.assert_frame_equal(before,repo._facility_details)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_detail_has_all_readonly_fields(detail_record,tmp_path,monkeypatch,entrypoint,prefix):
    repo,record=detail_record;before=repo._facility_details.copy(deep=True)
    app=detail_app(repo,tmp_path,monkeypatch,entrypoint,prefix,'detail')
    assert not app.exception and not app.error
    shown=[block.value for block in app.tabs[0].get('markdown')]
    expected=facility_detail_values(record,timestamp_formatter=format_timestamp)
    for label in LABELS:
        if label in {'Created On','Facility','Account'}:continue
        escaped=label.replace('*',r'\*')
        assert '**'+escaped+'**  \n'+expected[label] in shown
    assert any('**Facility**' in value and 'DEV_TEST barn' in value for value in shown)
    assert any('**Account**' in value and 'DEV_TEST staff producer' in value for value in shown)
    assert not any(widget.label in LABELS for widget in app.text_input)
    pd.testing.assert_frame_equal(before,repo._facility_details)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_null_cells_and_null_detail_name_do_not_crash(detail_record,tmp_path,monkeypatch,entrypoint,prefix):
    repo,record=detail_record
    for field in record:
        if field not in {'FACILITY_DETAIL_ID','FACILITY_ID'}:
            repo._facility_details[field]=pd.Series([pd.NA],dtype=object)
    app=detail_app(repo,tmp_path,monkeypatch,entrypoint,prefix)
    app.selectbox(key='facility_detail_saved_view').select('All Facility Details').run()
    assert not app.exception and not app.error
    row=app.dataframe[0].value.iloc[0]
    for label in LABELS:
        if label not in {'Facility','Account'}:assert row[label]=='—'
    app.session_state['_efns_record_13_Facility_Details_view']='detail'
    app.session_state['_efns_record_13_Facility_Details_id']='SYNTHETIC-detail'
    app.run()
    assert not app.exception and not app.error
    shown=[block.value for block in app.tabs[0].get('markdown')]
    assert '**Name**  \n—' in shown and '**Date Installed**  \n—' in shown
    assert '**Comments**  \n—' in shown and '**Status**  \n—' in shown


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_empty_mock_results_show_clear_message(detail_record,tmp_path,monkeypatch,entrypoint,prefix):
    repo,_=detail_record;repo._facility_details=repo._facility_details.iloc[0:0].copy()
    app=detail_app(repo,tmp_path,monkeypatch,entrypoint,prefix)
    assert not app.exception and not app.error
    assert any('No Facility Details match' in info.value for info in app.info)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_reporting_viewer_sees_fields_without_mutating_data(detail_record,tmp_path,monkeypatch,entrypoint,prefix):
    repo,_=detail_record;before=repo._facility_details.copy(deep=True)
    app=detail_app(repo,tmp_path,monkeypatch,entrypoint,prefix,'detail',Role.REPORTING_VIEWER)
    assert not app.exception and not app.error
    assert any('**Facility Type**  \nEnriched'==block.value for block in app.markdown)
    assert not any(widget.label=='Width' for widget in app.number_input)
    pd.testing.assert_frame_equal(before,repo._facility_details)
