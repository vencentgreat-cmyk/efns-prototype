"""Legacy Facility presentation through both real entrypoints, synthetic data only."""
import datetime as dt
from decimal import Decimal
import json

import pandas as pd
import pytest

from app.navigation import timestamp_column
from tests.test_facility_housing_view import facility, facility_app, ENTRYPOINTS
from tests.test_staff_workflows import chain


@pytest.fixture
def legacy_facility(facility):
    repo,fid=facility
    row=repo._facilities.iloc[0].to_dict()
    row.update(FARM_LOCATION_ID='synthetic-location', CONSTRUCTION_DATE=dt.date(2000,2,29),
        RENOVATION_DATE=dt.date(2024,3,1), MANURE_DISPOSAL='Belt',
        FACILITY_QUOTA=Decimal('1234.50'), COMMENTS='Synthetic barn comment')
    repo._facilities=pd.DataFrame([row])
    repo._farm_locations=pd.DataFrame([dict(FARM_LOCATION_ID='synthetic-location',
        ACCOUNT_ID=row['ACCOUNT_ID'],LOCATION_NAME='Synthetic farm location',STATUS='Active')])
    return repo,fid


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_legacy_list_order_labels_and_linked_values(legacy_facility,tmp_path,monkeypatch,entrypoint,prefix):
    repo,fid=legacy_facility; before=repo._facilities.copy(deep=True)
    app=facility_app(repo,fid,tmp_path,monkeypatch,entrypoint,prefix)
    assert not app.exception and not app.error
    grid=app.dataframe[0]; labels=json.loads(grid.proto.columns)
    assert [labels[col]['label'] for col in grid.value.columns]==[
        'Registration Number','Account','Facility Name','Farm Location',
        'Facility Type','Facility Layout','Status',timestamp_column('Created On')['label']]
    assert grid.value.iloc[0].REGISTRATION_NUMBER=='001'
    assert grid.value.iloc[0].FARM_LOCATION_NAME=='Synthetic farm location'
    assert 'ACTIVATION_DATE' not in grid.value and 'CLOSURE_DATE' not in grid.value
    assert app.session_state['facility_list_row_ids']==[fid]
    pd.testing.assert_frame_equal(before,repo._facilities)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_summary_shows_available_legacy_fields_read_only(legacy_facility,tmp_path,monkeypatch,entrypoint,prefix):
    repo,fid=legacy_facility; before=repo._facilities.copy(deep=True)
    app=facility_app(repo,fid,tmp_path,monkeypatch,entrypoint,prefix,'detail')
    assert not app.exception and not app.error
    text=[block.value for block in app.tabs[0].get('markdown')]
    for label,value in [('Registration Number','001'),('Farm Location','Synthetic farm location'),
        ('Facility Layout','Enriched'),('Construction Date','2000-02-29'),
        ('Renovation Date','2024-03-01'),('Manure Disposal','Belt'),
        ('Facility Quota','1234.50'),('Comments','Synthetic barn comment')]:
        assert f'**{label}**  \n{value}' in text
    for label in ('Activation Date','Closure Date','Created On'):
        assert any(line.startswith(f'**{label}**') for line in text)
    assert not any('**Housing System**' in line for line in text)
    pd.testing.assert_frame_equal(before,repo._facilities)


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_optional_legacy_fields_render_dash(legacy_facility,tmp_path,monkeypatch,entrypoint,prefix):
    repo,fid=legacy_facility
    for field in ('FARM_LOCATION_ID','CONSTRUCTION_DATE','RENOVATION_DATE','MANURE_DISPOSAL',
                  'FACILITY_QUOTA','COMMENTS','ACTIVATION_DATE','CLOSURE_DATE','STATUS'):
        repo._facilities[field]=None
    app=facility_app(repo,fid,tmp_path,monkeypatch,entrypoint,prefix,'detail')
    assert not app.exception and not app.error
    text=[block.value for block in app.tabs[0].get('markdown')]
    for label in ('Farm Location','Construction Date','Renovation Date','Manure Disposal',
                  'Facility Quota','Comments','Activation Date','Closure Date','Status'):
        assert f'**{label}**  \n—' in text


@pytest.mark.parametrize('entrypoint,prefix',ENTRYPOINTS)
def test_row_selection_edit_save_and_form_options_are_unchanged(legacy_facility,tmp_path,monkeypatch,entrypoint,prefix):
    import app.navigation
    repo,fid=legacy_facility
    monkeypatch.setattr(app.navigation,'selected_row_index',lambda key:0)
    app=facility_app(repo,fid,tmp_path,monkeypatch,entrypoint,prefix)
    app.button(key='facility_list_view').click().run()
    assert app.session_state['_efns_record_11_Facilities_id']==fid
    app.switch_page(f'{prefix}/11_Facilities.py').run()
    app.button(key='facility_record_edit').click().run()
    assert not app.exception and not app.error
    assert app.selectbox(key='facility_form_type').options==['Pullet','Layer','Other']
    assert app.selectbox(key='facility_form_type').value=='Layer'
    assert app.selectbox(key='facility_form_status').options==['Active','Inactive','Closed']
    before=repo.get_facility(fid)
    app.text_input(key='facility_form_name').input('Synthetic renamed barn')
    app.text_input(key='facility_form_revision_reason').input('Synthetic display regression test')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    after=repo.get_facility(fid)
    assert after['FACILITY_NAME']=='Synthetic renamed barn'
    for field in ('ACCOUNT_ID','FARM_LOCATION_ID','HOUSING_SYSTEM','FACILITY_TYPE',
                  'RENOVATION_DATE','FACILITY_QUOTA','MANURE_DISPOSAL','COMMENTS'):
        assert after[field]==before[field]
    app.session_state['_efns_record_11_Facilities_view']='new'
    app.session_state['_efns_record_11_Facilities_id']=None
    app.run()
    assert not app.exception and not app.error
    assert app.selectbox(key='facility_form_type').options==['Pullet','Layer','Other']
    assert not any(widget.label in {'Housing System','Facility Layout','Manure Disposal'}
        for widget in app.selectbox)
