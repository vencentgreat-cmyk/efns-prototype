"""Synthetic legacy list/field labels; no database connection or real-data files."""
from copy import deepcopy
import datetime as dt
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path

import pandas as pd
import pytest

from app.navigation import timestamp_column
from app.services.legacy_view_labels import ACCOUNT_COLUMNS, FLOCK_COLUMNS, column_labels, field_label
from app.services.report_center import build_custom_report, report_csv, report_xlsx
from tests.auth_support import authenticated_app
from tests.test_report_center import user
from tests.test_staff_workflows import chain

ROOT=Path(__file__).resolve().parents[1]
ENTRIES=[('streamlit_app.py','app/pages'),('app/Home.py','pages')]


@pytest.mark.parametrize('field,expected',[
    ('BARN_IDENTITY','Barn Identity'), ('PRODUCER_IDENTITY_LABEL','Producer Identity Label'),
    ('IDENTITY','Identity'), ('IDENTIFIER','Identifier'), ('IDLE_TIME','Idle Time'),
    ('ACCOUNT_ID','Account ID'), ('ID','ID'), ('ID_NUMBER','ID Number'),
    ('IDENTITY_ID','Identity ID'),
])
def test_id_capitalization_only_matches_a_whole_word(field,expected):
    assert field_label(field)==expected
    assert column_labels([field])[field]==expected


@pytest.fixture
def legacy_chain(chain):
    repo,account,other,facility,quota,flock,_=chain
    idx=repo._accounts.ACCOUNT_ID.eq(account)
    for key,value in dict(ADDRESS_LINE1='Synthetic street',CITY='Synthetic city',PROVINCE='NS',
        POSTAL_CODE='A0A 0A0',CONTACT_PHONE='555-0100',CONTACT_NAME='Synthetic contact',
        CONTACT_EMAIL='account@example.invalid',BREEDER_ROLE=True,GRADER_ROLE=False,
        HATCHERY_ROLE=False,PRODUCER_ROLE=True).items():
        repo._accounts.loc[idx,key]=value
    repo._facilities['FARM_LOCATION_ID']='synthetic-location'
    repo._farm_locations=pd.DataFrame([dict(FARM_LOCATION_ID='synthetic-location',
        ACCOUNT_ID=account,LOCATION_NAME='Synthetic farm',STATUS='Active')])
    for key,value in dict(PLACEMENT_DATE=dt.date(2026,5,14),EST_DISPOSAL=dt.date(2027,5,13),
        DISPOSAL_DATE=None,COMMENTS='Synthetic comment',HATCHERY='Synthetic hatchery',
        BREEDER='Synthetic breeder',DISPOSAL_PLANT='Synthetic plant').items():
        repo._flocks[key]=value
    repo.upsert_flock_transaction(dict(FLOCK_ID=flock,TRANSACTION_TYPE='Count',
        TRANSACTION_DATE=dt.date(2026,6,1),QUANTITY=10,SOURCE_LABEL='Producer'))
    return repo,account,facility,flock


def open_page(data,tmp_path,monkeypatch,entry,prefix,page,view='list'):
    repo,account,facility,flock=data
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local');monkeypatch.setenv('REPOSITORY_MODE','mock')
    app=authenticated_app(ROOT/entry,tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    scope='5_Flocks' if page=='flock' else '3_Accounts_Facilities_Flocks'
    app.session_state[f'_efns_record_{scope}_view']=view
    app.session_state[f'_efns_record_{scope}_id']=(flock if page=='flock' else account) if view!='list' else None
    return app.switch_page(f'{prefix}/{scope}.py').run()


@pytest.mark.parametrize('entry,prefix',ENTRIES)
@pytest.mark.parametrize('page',['flock','account'])
def test_exact_legacy_order_labels_and_values(legacy_chain,tmp_path,monkeypatch,entry,prefix,page):
    repo,account,_,flock=legacy_chain
    before={key:deepcopy(getattr(repo,key)) for key in ('_accounts','_flocks','_facilities','_farm_locations')}
    app=open_page(legacy_chain,tmp_path,monkeypatch,entry,prefix,page)
    assert not app.error and not app.exception
    grid=app.dataframe[0];config=json.loads(grid.proto.columns)
    columns=FLOCK_COLUMNS if page=='flock' else ACCOUNT_COLUMNS
    assert list(grid.value.columns)==list(columns)
    expected=column_labels(columns,flock=page=='flock')
    expected['CREATED_AT']=timestamp_column('Created On')['label']
    if page=='account':expected['UPDATED_AT']=timestamp_column('Modified On')['label']
    assert [config[col]['label'] for col in columns]==[expected[col] for col in columns]
    if page=='flock':
        assert grid.value.iloc[0].LOCATION=='Synthetic farm'
        assert grid.value.iloc[0].REGISTRATION_NUMBER=='001'
        assert grid.value.iloc[0].BIRD_COUNT==10
        assert app.session_state['flock_list_row_ids']==[flock]
    else:
        row=grid.value.loc[grid.value.REGISTRATION_NUMBER.eq('001')].iloc[0]
        assert row.CONTACT_NAME=='Synthetic contact' and row.CONTACT_EMAIL=='account@example.invalid'
        assert 'Email (Primary Contact)' not in [value.get('label') for value in config.values()]
        assert app.session_state['account_list_row_ids']==repo.get_accounts(statuses=['Active']).ACCOUNT_ID.tolist()
    for key,value in before.items():pd.testing.assert_frame_equal(value,getattr(repo,key))


@pytest.mark.parametrize('entry,prefix',ENTRIES)
def test_location_missing_links_are_dash(legacy_chain,tmp_path,monkeypatch,entry,prefix):
    repo,account,facility,flock=legacy_chain
    first=repo._flocks.iloc[0].to_dict()
    repo._flocks=pd.DataFrame([dict(first,FLOCK_ID='unassigned',FACILITY_ID=None),
        dict(first,FLOCK_ID='no-location',FACILITY_ID=facility)])
    repo._facilities['FARM_LOCATION_ID']=None
    app=open_page(legacy_chain,tmp_path,monkeypatch,entry,prefix,'flock')
    assert not app.error and not app.exception
    assert app.dataframe[0].value.LOCATION.tolist()==['—','—']
    assert app.session_state['flock_list_row_ids']==['unassigned','no-location']


@pytest.mark.parametrize('entry,prefix',ENTRIES)
@pytest.mark.parametrize('page',['flock','account'])
def test_detail_related_headers_and_form_labels(legacy_chain,tmp_path,monkeypatch,entry,prefix,page):
    app=open_page(legacy_chain,tmp_path,monkeypatch,entry,prefix,page,'detail')
    assert not app.error and not app.exception
    for grid in app.dataframe:
        config=json.loads(grid.proto.columns)
        for column in grid.value.columns:
            label=config.get(column,{}).get('label',column)
            assert '_' not in label
    text='\n'.join(block.value for block in app.markdown)
    if page=='flock':
        assert '**Flock Colour**' in text and '**Facility Name**' in text
        fields=next(grid.value for grid in app.dataframe if 'Field' in grid.value)
        assert 'Estimated Disposal Date' in fields.Field.tolist()
        assert 'Flock Colour' in fields.Field.tolist()
        app.button(key='flock_record_edit').click().run()
        assert app.selectbox(key='flock_form_colour').label=='Flock Colour'
        assert app.selectbox(key='flock_form_facility').label=='Facility Name *'
    else:
        assert '**Account Email**' in text and '**Main Phone**' in text
        assert '**Primary Contact**' in text
        app.button(key='account_record_edit').click().run()
        assert app.text_input(key='account_form_phone').label=='Main Phone'
        assert app.text_input(key='account_form_email').label=='Account Email'
        assert app.text_input(key='account_form_street1').label=='Address 1: Street'
    assert not app.error and not app.exception


@pytest.mark.parametrize('entry,prefix',ENTRIES)
@pytest.mark.parametrize('page',['flock','account'])
def test_filters_selection_and_edit_save_keep_same_record(legacy_chain,tmp_path,monkeypatch,entry,prefix,page):
    import app.navigation as navigation
    repo,account,facility,flock=legacy_chain
    app=open_page(legacy_chain,tmp_path,monkeypatch,entry,prefix,page)
    if page=='flock':
        app.selectbox(key='flock_filter_colour').select('White').run()
        app.text_input(key='flock_filter_keyword').input('DEV_TEST').run()
        ids=app.session_state['flock_list_row_ids'];assert ids==[flock]
    else:
        app.text_input(key='account_filter_keyword').input('001').run()
        ids=app.session_state['account_list_row_ids'];assert ids==[account]
    monkeypatch.setattr(navigation,'selected_row_index',lambda key:0)
    app.run()
    stem='flock' if page=='flock' else 'account'
    app.button(key=stem+'_list_view').click().run()
    scope='5_Flocks' if page=='flock' else '3_Accounts_Facilities_Flocks'
    assert app.session_state[f'_efns_record_{scope}_id']==ids[0]
    app.switch_page(f'{prefix}/{scope}.py').run()
    app.button(key=stem+'_record_edit').click().run()
    before=repo.get_flock(flock) if page=='flock' else repo.get_account(account)
    if page=='flock':app.text_area(key='flock_form_comments').input('Synthetic revised comment')
    else:app.text_input(key='account_form_name').input('Synthetic renamed account')
    app.text_input(key=stem+'_form_revision_reason').input('Synthetic label regression test')
    app.button(key=stem+'_record_save').click().run()
    assert not app.exception and not app.error
    after=repo.get_flock(flock) if page=='flock' else repo.get_account(account)
    retained=('BIRD_COUNT','HATCH_DATE','PLACEMENT_DATE','EST_DISPOSAL','ACCOUNT_ID','FACILITY_ID') if page=='flock' else ('REGISTRATION_NUMBER','CONTACT_PHONE','CONTACT_EMAIL','ADDRESS_LINE1')
    for field in retained:assert before[field]==after[field]


def test_report_center_csv_xlsx_fields_values_and_source_frames_unchanged(legacy_chain):
    repo,_,_,_=legacy_chain
    for dataset,fields in [('Accounts',['ACCOUNT_ID','ORGANIZATION_NAME','REGISTRATION_NUMBER','CITY','CONTACT_PHONE']),
                           ('Flocks',['FLOCK_ID','FLOCK_NUMBER','BIRD_COUNT','EST_DISPOSAL'])]:
        result=build_custom_report(repo,user=user(),dataset=dataset,selected_fields=fields)
        before=result.copy(deep=True);csv=report_csv(user(),result)
        xlsx=pd.read_excel(BytesIO(report_xlsx(user(),result)))
        assert report_csv(user(),result)==csv
        pd.testing.assert_frame_equal(xlsx,pd.read_excel(BytesIO(report_xlsx(user(),result))))
        pd.testing.assert_frame_equal(before,result)
        expected=(['Account ID','Account Name','Registration Number','City','Phone'] if dataset=='Accounts'
                  else ['Flock ID','Flock Number','Bird Count','Estimated Disposal Date'])
        assert result.columns.tolist()==expected
