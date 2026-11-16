"""Legacy Facility form round trips on isolated synthetic repositories."""
import datetime as dt
from decimal import Decimal

import pandas as pd
import pytest

from app.security import Role
from data.repositories.base import RepositoryError
from tests.test_facility_housing_view import facility, facility_app, ENTRYPOINTS
from tests.test_staff_workflows import chain


@pytest.fixture
def form_facility(facility):
    repo,fid=facility
    row=repo._facilities.iloc[0].to_dict()
    row.update(FACILITY_TYPE='Layers',HOUSING_SYSTEM='Organic',MANURE_DISPOSAL='Belt',
        FARM_LOCATION_ID='synthetic-location',FACILITY_QUOTA=Decimal('12.3456'),
        RENOVATION_DATE=dt.date(2020,2,29),COMMENTS='Original synthetic comment',
        DESTRUCTION_DATE=dt.date(2025,1,1))
    repo._facilities=pd.DataFrame([row])
    repo._farm_locations=pd.DataFrame([dict(FARM_LOCATION_ID='synthetic-location',
        ACCOUNT_ID=row['ACCOUNT_ID'],LOCATION_NAME='Synthetic farm',STATUS='Active')])
    return repo,fid


def new_form(data,tmp_path,monkeypatch,entry,prefix,role=Role.ADMIN):
    repo,fid=data
    app=facility_app(repo,fid,tmp_path,monkeypatch,entry,prefix,role=role)
    app.session_state['_efns_record_11_Facilities_view']='new'
    app.session_state['_efns_record_11_Facilities_id']=None
    return app.run()


def facility_audits(repo,fid):
    return [row for row in repo._migration_review_audit
        if row['ENTITY_TYPE']=='FACILITY' and row['ENTITY_ID']==fid]


@pytest.mark.parametrize('entry,prefix',ENTRYPOINTS)
def test_create_then_edit_all_new_fields_and_history(form_facility,tmp_path,monkeypatch,entry,prefix):
    repo,_=form_facility
    app=new_form(form_facility,tmp_path,monkeypatch,entry,prefix)
    assert not app.exception and not app.error
    assert app.selectbox(key='facility_form_type').options==['—','Breeder','Hatchery','Layers','Pullets']
    assert app.selectbox(key='facility_form_layout').options==['—','Organic','Conventional','Free Range','Enriched','Free Run']
    assert app.selectbox(key='facility_form_manure').options==['—','Belt','Shallow Pit','Deep Pit','Belts and Gutter']
    assert app.selectbox(key='facility_form_location').label=='Farm Location'
    app.text_input(key='facility_form_name').input('Synthetic created legacy barn')
    app.selectbox(key='facility_form_type').select('Pullets')
    app.selectbox(key='facility_form_layout').select('Enriched')
    app.selectbox(key='facility_form_manure').select('Belts and Gutter')
    location=next(label for label in app.selectbox(key='facility_form_location').options if label.startswith('Synthetic farm'))
    app.selectbox(key='facility_form_location').select(location)
    app.date_input(key='facility_form_renovation').set_value(dt.date(2024,2,29))
    app.text_input(key='facility_form_quota').input('99999999999999.1234')
    app.text_area(key='facility_form_comments').input('  Synthetic exact comment\nsecond line  ')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    fid=app.session_state['_efns_record_11_Facilities_id']
    current=repo.get_facility(fid)
    expected=dict(FACILITY_TYPE='Pullets',HOUSING_SYSTEM='Enriched',MANURE_DISPOSAL='Belts and Gutter',
        FARM_LOCATION_ID='synthetic-location',RENOVATION_DATE=dt.date(2024,2,29),
        FACILITY_QUOTA=Decimal('99999999999999.1234'),COMMENTS='  Synthetic exact comment\nsecond line  ')
    for field,value in expected.items():assert current[field]==value
    history=repo.get_record_revisions().query('ENTITY_ID == @fid')
    assert len(history)==1 and history.iloc[0].CHANGE_KIND=='CREATE'
    assert history.iloc[0].BEFORE_DATA is None
    for field,value in expected.items():assert history.iloc[0].AFTER_DATA[field]==value
    actor=app.session_state.repo.actor
    assert history.iloc[0].RECORDED_BY==actor.user_id
    audit=facility_audits(repo,fid)
    assert len(audit)==1 and audit[0]['ACTION']=='CREATE'
    assert audit[0]['ACTOR_USER_ID']==actor.user_id and audit[0]['ACTOR_EMAIL']==actor.email
    app.switch_page(f'{prefix}/11_Facilities.py').run()
    app.button(key='facility_record_edit').click().run()
    app.selectbox(key='facility_form_type').select('Layers')
    app.selectbox(key='facility_form_layout').select('Free Run')
    app.selectbox(key='facility_form_manure').select('Deep Pit')
    app.selectbox(key='facility_form_location').select('Not selected')
    app.date_input(key='facility_form_renovation').set_value(dt.date(2026,11,13))
    app.text_input(key='facility_form_quota').input('-3.1250')
    app.text_area(key='facility_form_comments').input('Revised synthetic comment')
    app.text_input(key='facility_form_revision_reason').input('Synthetic legacy form correction')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    after=repo.get_facility(fid)
    edited=dict(FACILITY_TYPE='Layers',HOUSING_SYSTEM='Free Run',MANURE_DISPOSAL='Deep Pit',
        FARM_LOCATION_ID=None,RENOVATION_DATE=dt.date(2026,11,13),
        FACILITY_QUOTA=Decimal('-3.1250'),COMMENTS='Revised synthetic comment')
    for field,value in edited.items():assert after[field]==value
    history=repo.get_record_revisions().query('ENTITY_ID == @fid')
    correction=history.loc[history.CHANGE_KIND.eq('ATTRIBUTE_CORRECTION')].iloc[0]
    assert len(history)==2 and correction.REASON=='Synthetic legacy form correction'
    for field,value in expected.items():assert correction.BEFORE_DATA[field]==value
    for field,value in edited.items():assert correction.AFTER_DATA[field]==value
    audit=facility_audits(repo,fid)
    assert [row['ACTION'] for row in audit]==['CREATE','UPDATE']
    assert audit[-1]['DETAILS']['reason']=='Synthetic legacy form correction'
    assert audit[-1]['DETAILS']['history_kind']=='ATTRIBUTE_CORRECTION'
    assert audit[-1]['ACTOR_USER_ID']==actor.user_id


@pytest.mark.parametrize('entry,prefix',ENTRYPOINTS)
@pytest.mark.parametrize('historical',['Pullet','Layer','Other','Historical special type',None])
def test_historical_values_and_unshown_fields_survive_name_edit(form_facility,tmp_path,monkeypatch,entry,prefix,historical):
    repo,fid=form_facility
    repo._facilities['FACILITY_TYPE']=historical
    repo._facilities['HOUSING_SYSTEM']='Historical layout'
    repo._facilities['MANURE_DISPOSAL']='Historical manure'
    before=repo.get_facility(fid)
    app=facility_app(repo,fid,tmp_path,monkeypatch,entry,prefix,'edit')
    assert not app.exception and not app.error
    assert app.selectbox(key='facility_form_type').value==historical
    assert app.selectbox(key='facility_form_layout').value=='Historical layout'
    assert app.selectbox(key='facility_form_manure').value=='Historical manure'
    app.text_input(key='facility_form_name').input('Synthetic name-only correction')
    app.text_input(key='facility_form_revision_reason').input('Name only')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    after=repo.get_facility(fid)
    for field,value in before.items():
        if field not in {'FACILITY_NAME','UPDATED_AT'}:
            assert after[field]==value or pd.isna(after[field]) and pd.isna(value)
    assert after['DESTRUCTION_DATE']==dt.date(2025,1,1)
    revision=repo.get_record_revisions().iloc[0]
    for field in ('FACILITY_TYPE','HOUSING_SYSTEM','MANURE_DISPOSAL','FACILITY_QUOTA','DESTRUCTION_DATE'):
        assert revision.BEFORE_DATA[field]==revision.AFTER_DATA[field]


@pytest.mark.parametrize('entry,prefix',ENTRYPOINTS)
def test_optional_fields_and_location_do_not_block_create(form_facility,tmp_path,monkeypatch,entry,prefix):
    repo,_=form_facility
    app=new_form(form_facility,tmp_path,monkeypatch,entry,prefix)
    app.button(key='facility_record_save').click().run()
    assert any('Facility Name is required' in error.value for error in app.error)
    assert repo.get_record_revisions().empty
    app.text_input(key='facility_form_name').input('Synthetic optional blank barn')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    row=repo.get_facility(app.session_state['_efns_record_11_Facilities_id'])
    for field in ('FARM_LOCATION_ID','HOUSING_SYSTEM','MANURE_DISPOSAL','FACILITY_QUOTA','RENOVATION_DATE'):
        assert row[field] is None or pd.isna(row[field])
    assert not any(widget.label in {'Facility Description','Status Reason'} for widget in app.text_input)


@pytest.mark.parametrize('entry,prefix',ENTRYPOINTS)
def test_stale_location_and_invalid_untouched_quota_are_preserved(form_facility,tmp_path,monkeypatch,entry,prefix):
    repo,fid=form_facility
    repo._facilities['FARM_LOCATION_ID']='synthetic-missing-location'
    repo._facilities['FACILITY_QUOTA']='Historical unparsed value'
    app=facility_app(repo,fid,tmp_path,monkeypatch,entry,prefix,'edit')
    assert app.selectbox(key='facility_form_location').value=='synthetic-missing-location (not found)'
    app.text_input(key='facility_form_name').input('Synthetic preserved historical quota')
    app.text_input(key='facility_form_revision_reason').input('Name only')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_facility(fid)['FARM_LOCATION_ID']=='synthetic-missing-location'
    assert repo.get_facility(fid)['FACILITY_QUOTA']=='Historical unparsed value'


@pytest.mark.parametrize('entry,prefix',ENTRYPOINTS)
def test_clear_new_optional_fields_round_trip(form_facility,tmp_path,monkeypatch,entry,prefix):
    repo,fid=form_facility
    app=facility_app(repo,fid,tmp_path,monkeypatch,entry,prefix,'edit')
    app.selectbox(key='facility_form_layout').select_index(0)
    app.selectbox(key='facility_form_manure').select_index(0)
    app.selectbox(key='facility_form_location').select('Not selected')
    app.date_input(key='facility_form_renovation').set_value(None)
    app.text_input(key='facility_form_quota').input('')
    app.text_area(key='facility_form_comments').input('')
    app.text_input(key='facility_form_revision_reason').input('Clear optional synthetic fields')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    row=repo.get_facility(fid)
    for field in ('FARM_LOCATION_ID','HOUSING_SYSTEM','MANURE_DISPOSAL','RENOVATION_DATE','FACILITY_QUOTA'):
        assert row[field] is None or pd.isna(row[field])
    assert row['COMMENTS']==''
    assert row['DESTRUCTION_DATE']==dt.date(2025,1,1)


@pytest.mark.parametrize('entry,prefix',ENTRYPOINTS)
def test_unchanged_null_widgets_are_noop_without_revision_or_audit(form_facility,tmp_path,monkeypatch,entry,prefix):
    repo,fid=form_facility
    for field in ('FACILITY_TYPE','FARM_LOCATION_ID','HOUSING_SYSTEM','MANURE_DISPOSAL',
                  'FACILITY_QUOTA','RENOVATION_DATE','COMMENTS'):
        repo._facilities[field]=None
    before=repo._facilities.copy(deep=True)
    app=facility_app(repo,fid,tmp_path,monkeypatch,entry,prefix,'edit')
    app.button(key='facility_record_save').click().run()
    assert not app.exception and not app.error
    pd.testing.assert_frame_equal(before,repo._facilities)
    assert repo.get_record_revisions().empty and not facility_audits(repo,fid)


@pytest.mark.parametrize('entry,prefix',ENTRYPOINTS)
@pytest.mark.parametrize('view',['new','edit'])
def test_reporting_viewer_cannot_save_or_bypass_permissions(form_facility,tmp_path,monkeypatch,entry,prefix,view):
    repo,fid=form_facility;before=repo._facilities.copy(deep=True)
    app=(new_form(form_facility,tmp_path,monkeypatch,entry,prefix,Role.REPORTING_VIEWER)
         if view=='new' else facility_app(repo,fid,tmp_path,monkeypatch,entry,prefix,'edit',Role.REPORTING_VIEWER))
    assert not app.exception and not app.error
    assert app.button(key='facility_record_save').disabled
    authorized=app.session_state.repo
    with pytest.raises(RepositoryError):
        if view=='new':authorized.create_record_once('FACILITY',{'FACILITY_NAME':'Blocked'},'synthetic-denied')
        else:authorized.revise_record('FACILITY',fid,{'HOUSING_SYSTEM':'Free Run'},'Blocked','synthetic-denied',expected_updated_at=before.iloc[0].UPDATED_AT)
    pd.testing.assert_frame_equal(before,repo._facilities)
    assert repo.get_record_revisions().empty and not facility_audits(repo,fid)
