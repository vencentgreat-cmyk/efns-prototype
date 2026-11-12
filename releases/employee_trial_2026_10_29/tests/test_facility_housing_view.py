"""Read-only parent Facility housing display; synthetic AppTest data only."""
from io import BytesIO
import json
from pathlib import Path

import pandas as pd
import pytest

from app.security import Role
from app.services.report_center import build_custom_report, report_csv, report_xlsx
from data.repositories.snowflake import SnowflakeRepository
from tests.auth_support import authenticated_app
from tests.test_report_center import user
from tests.test_staff_workflows import chain

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINTS = [('streamlit_app.py', 'app/pages'), ('app/Home.py', 'pages')]


@pytest.fixture
def facility(chain):
    repo,account,other,facility_id,*_=chain
    repo._facilities['HOUSING_SYSTEM']='Enriched'
    return repo,facility_id


def facility_app(repo,facility_id,tmp_path,monkeypatch,entrypoint,prefix,view='list',role=Role.ADMIN):
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local')
    monkeypatch.setenv('REPOSITORY_MODE','mock')
    app=authenticated_app(ROOT/entrypoint,tmp_path,monkeypatch,role)
    app.session_state['_base_repo']=repo
    app.session_state['_efns_record_11_Facilities_view']=view
    app.session_state['_efns_record_11_Facilities_id']=facility_id if view!='list' else None
    return app.switch_page(f'{prefix}/11_Facilities.py').run()


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_list_has_adjacent_friendly_columns_without_mutating_source(facility,tmp_path,monkeypatch,entrypoint,prefix):
    repo,facility_id=facility;before=repo._facilities.copy(deep=True)
    app=facility_app(repo,facility_id,tmp_path,monkeypatch,entrypoint,prefix)
    assert not app.error and not app.exception
    grid=app.dataframe[0];shown=grid.value
    assert shown.columns.tolist()==['FACILITY_NAME','ACCOUNT_NAME','FACILITY_TYPE','HOUSING_SYSTEM',
        'STATUS','ACTIVATION_DATE','CLOSURE_DATE','CREATED_AT']
    labels=json.loads(grid.proto.columns)
    assert labels['FACILITY_TYPE']['label']=='Facility Type'
    assert labels['HOUSING_SYSTEM']['label']=='Housing System'
    assert shown.iloc[0].FACILITY_TYPE=='Layer' and shown.iloc[0].HOUSING_SYSTEM=='Enriched'
    assert app.session_state['facility_list_row_ids']==[facility_id]
    pd.testing.assert_frame_equal(repo._facilities,before)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
@pytest.mark.parametrize('role',[Role.ADMIN,Role.REPORTING_VIEWER])
def test_summary_housing_is_read_only_for_existing_roles(facility,tmp_path,monkeypatch,entrypoint,prefix,role):
    repo,facility_id=facility;before=repo._facilities.copy(deep=True)
    app=facility_app(repo,facility_id,tmp_path,monkeypatch,entrypoint,prefix,'detail',role)
    assert not app.error and not app.exception
    text=[block.value for block in app.tabs[0].get('markdown')]
    assert '**Facility Type**  \nLayer' in text
    assert '**Housing System**  \nEnriched' in text
    assert not any(block.startswith('**Type**') for block in text)
    assert not any(widget.label=='Housing System' for widget in app.text_input)
    pd.testing.assert_frame_equal(repo._facilities,before)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_all_missing_representations_are_dash_in_list_and_summary(facility,tmp_path,monkeypatch,entrypoint,prefix):
    repo,facility_id=facility
    row=repo._facilities.iloc[0].to_dict()
    rows=[dict(row,FACILITY_ID=facility_id if index==0 else f'synthetic-facility-{index}',
        FACILITY_TYPE=missing,HOUSING_SYSTEM=missing)
        for index,missing in enumerate([None,pd.NA,pd.NaT,float('nan'),'','  '])]
    repo._facilities=pd.DataFrame(rows,dtype=object);before=repo._facilities.copy(deep=True)
    app=facility_app(repo,facility_id,tmp_path,monkeypatch,entrypoint,prefix)
    assert not app.error and not app.exception
    for field in ('FACILITY_TYPE','HOUSING_SYSTEM'):
        assert app.dataframe[0].value[field].tolist()==['—']*len(rows)
    app.session_state['_efns_record_11_Facilities_view']='detail'
    app.session_state['_efns_record_11_Facilities_id']=facility_id
    app.run()
    assert not app.error and not app.exception
    text=[block.value for block in app.tabs[0].get('markdown')]
    assert '**Facility Type**  \n—' in text and '**Housing System**  \n—' in text
    pd.testing.assert_frame_equal(repo._facilities,before)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_older_mock_shape_without_housing_column_is_safe(facility,tmp_path,monkeypatch,entrypoint,prefix):
    repo,facility_id=facility;repo._facilities=repo._facilities.drop(columns='HOUSING_SYSTEM')
    app=facility_app(repo,facility_id,tmp_path,monkeypatch,entrypoint,prefix)
    assert not app.error and not app.exception
    assert app.dataframe[0].value.iloc[0].HOUSING_SYSTEM=='—'
    assert 'HOUSING_SYSTEM' not in repo._facilities


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_existing_filter_row_identity_and_edit_controls_stay_unchanged(facility,tmp_path,monkeypatch,entrypoint,prefix):
    repo,facility_id=facility;row=repo._facilities.iloc[0].to_dict()
    repo._facilities=pd.DataFrame([row,dict(row,FACILITY_ID='synthetic-pullet',FACILITY_NAME='Synthetic pullet barn',
        FACILITY_TYPE='Pullet',HOUSING_SYSTEM='Free Run')])
    before=repo._facilities.copy(deep=True)
    app=facility_app(repo,facility_id,tmp_path,monkeypatch,entrypoint,prefix)
    assert app.session_state['facility_list_row_ids']==[facility_id,'synthetic-pullet']
    app.selectbox(key='facility_filter_type').select('Pullet').run()
    assert not app.error and not app.exception
    assert app.session_state['facility_list_row_ids']==['synthetic-pullet']
    assert app.dataframe[0].value.iloc[0].HOUSING_SYSTEM=='Free Run'
    app.session_state['_efns_record_11_Facilities_view']='edit'
    app.session_state['_efns_record_11_Facilities_id']=facility_id
    app.run()
    assert not app.error and not app.exception
    assert app.selectbox(key='facility_form_type').value=='Layer'
    assert not any(widget.label=='Housing System' for widget in app.text_input)
    assert not any(widget.label=='Housing System' for widget in app.selectbox)
    pd.testing.assert_frame_equal(repo._facilities,before)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_empty_facility_list_has_existing_message(facility,tmp_path,monkeypatch,entrypoint,prefix):
    repo,facility_id=facility;repo._facilities=repo._facilities.iloc[:0]
    app=facility_app(repo,facility_id,tmp_path,monkeypatch,entrypoint,prefix)
    assert not app.error and not app.exception and not app.dataframe
    assert any(info.value=='No Facilities match the current filters.' for info in app.info)


def test_existing_snowflake_read_returns_housing_with_bound_filter(facility):
    repo,facility_id=facility;calls=[]
    snow=SnowflakeRepository.__new__(SnowflakeRepository)
    snow.database='EFNS_DEV';snow.schema_core='CORE'
    def offline_query(sql,params):
        calls.append((sql,params))
        return repo._facilities.copy()
    snow._query=offline_query
    result=snow.get_facilities(account_id=repo._facilities.iloc[0].ACCOUNT_ID,statuses=['Active'])
    assert result.iloc[0].HOUSING_SYSTEM=='Enriched'
    assert calls==[('SELECT * FROM EFNS_DEV.CORE.FACILITY WHERE ACCOUNT_ID = %s AND STATUS IN (%s)',
        (repo._facilities.iloc[0].ACCOUNT_ID,'Active'))]


def test_report_center_facility_export_fields_are_unchanged(facility):
    repo,_=facility
    fields=['FACILITY_ID','ACCOUNT_ID','FACILITY_NAME','FACILITY_TYPE','STATUS']
    result=build_custom_report(repo,user=user(),dataset='Facilities',selected_fields=fields)
    assert result.columns.tolist()==['Facility ID','Account ID','Facility Name','Facility Type','Status']
    assert pd.read_csv(BytesIO(report_csv(user(),result))).columns.tolist()==result.columns.tolist()
    assert pd.read_excel(BytesIO(report_xlsx(user(),result))).columns.tolist()==result.columns.tolist()
    assert 'HOUSING_SYSTEM' not in result and 'Housing System' not in result
