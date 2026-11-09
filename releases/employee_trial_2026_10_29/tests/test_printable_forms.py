"""Offline legacy-form fixtures, extracted text, NULL safety and UI downloads."""
from datetime import date
from io import BytesIO
from pathlib import Path
import hashlib
import json
import re

import pandas as pd
import pytest
from pypdf import PdfReader
from pypdf.generic import ContentStream

from app.services import printable_form_text as w
from app.services.printable_forms import (FORM_HANDLERS, build_printable_form,
    build_license_application, build_flock_permit, build_salmonella_form,
    matching_pullet_permits, render_form_pdf, PrintableForm)
from data.repositories.mock import MockRepository
from data.quota_position import load_rules
from tests.test_report_center import user

ROOT = Path(__file__).resolve().parents[1]


def legacy_form_repository():
    repo = MockRepository(seed=42)
    repo._accounts = pd.DataFrame([
        dict(ACCOUNT_ID='maritime',REGISTRATION_NUMBER='7173',ORGANIZATION_NAME='Maritime Pride Poultry Inc.',
             ADDRESS_LINE1='623 Travis Rd',CITY='Amherst',PROVINCE='NS',POSTAL_CODE='B4H 3Y3',
             CONTACT_NAME='Pierre-David Cyr',CONTACT_PHONE='506 740-1462',CONTACT_EMAIL='Pierre-David.Cyr@groupewestco.com',
             GRADING_STATION_ACCOUNT_ID='grader',SPENT_FOWL_PLANS='In-Barn CO2',PULLET_GROWER_ACCOUNT_ID='maritime',STATUS='Active'),
        dict(ACCOUNT_ID='grader',ORGANIZATION_NAME='Maritime Pride Eggs Inc.'),
        dict(ACCOUNT_ID='layer',REGISTRATION_NUMBER='7165',ORGANIZATION_NAME='Centerbrook Poultry Ltd.'),
        dict(ACCOUNT_ID='pullet',REGISTRATION_NUMBER='7325',ORGANIZATION_NAME='Jeffrey Clarke'),
        dict(ACCOUNT_ID='salmonella',REGISTRATION_NUMBER='7107',ORGANIZATION_NAME='Ueffing')])
    repo._farm_locations = pd.DataFrame([
        dict(FARM_LOCATION_ID='maritime-address',ACCOUNT_ID='maritime',ADDRESS_1='623 Travis Rd',CITY='Amherst',PROVINCE='Nova Scotia'),
        dict(FARM_LOCATION_ID='layer-address',ACCOUNT_ID='layer',ADDRESS_1='612 Marsh Road',CITY='Annapolis Royal',PROVINCE='NS'),
        dict(FARM_LOCATION_ID='pullet-address',ACCOUNT_ID='pullet',ADDRESS_1='Jeffrey Clarke St',CITY='Aylseford',PROVINCE='NS')])
    repo._facilities = pd.DataFrame([
        *[dict(FACILITY_ID='maritime-'+str(i),ACCOUNT_ID='maritime',FACILITY_NAME='7173 - A'+str(i),STATUS='Active',FACILITY_TYPE='Layers',HOUSING_SYSTEM='Enriched',FARM_LOCATION_ID='maritime-address') for i in range(1,5)],
        *[dict(FACILITY_ID='excluded-'+name,ACCOUNT_ID='maritime',FACILITY_NAME='7173 - '+name,STATUS=status,FACILITY_TYPE=kind,HOUSING_SYSTEM='Excluded housing',FARM_LOCATION_ID='maritime-address')
          for name,status,kind in [('AP1','Active','Pullets'),('AP2','Active','Pullets'),('CV1','Inactive','Layers'),('M1','Inactive','Layers'),('Org1','Inactive','Layers')]],
        dict(FACILITY_ID='layer-barn',ACCOUNT_ID='layer',FACILITY_NAME='7165 - 1',FARM_LOCATION_ID='layer-address'),
        dict(FACILITY_ID='pullet-barn',ACCOUNT_ID='pullet',FACILITY_NAME='7325 - P1',FARM_LOCATION_ID='pullet-address'),
        dict(FACILITY_ID='salmonella-barn',ACCOUNT_ID='salmonella',FACILITY_NAME='7107-Ueffing')])
    common = dict(HATCH_DATE='2023-08-24',PLACEMENT_DATE='2024-01-04',BIRD_COUNT=10000,EGG_COLOUR='White',BIRD_STRAIN='Lohmann',HATCHERY='Atlantic Poultry Incorporated - NB Hatchery')
    repo._flocks = pd.DataFrame([
        dict(common,FLOCK_ID='layer-flock',PERMIT_NUMBER='40289',ACCOUNT_ID='layer',FACILITY_ID='layer-barn'),
        dict(common,FLOCK_ID='pullet-flock',PERMIT_NUMBER='30289',ACCOUNT_ID='pullet',FACILITY_ID='pullet-barn'),
        dict(common,FLOCK_ID='salmonella-flock',PERMIT_NUMBER='40285',ACCOUNT_ID='salmonella',FACILITY_ID='salmonella-barn')])
    repo._quota_registrations = pd.DataFrame([dict(QUOTA_ID='quota',ACCOUNT_ID='maritime',QUOTA_TYPE='Egg Production',STATUS='Active')])
    repo._quota_transactions = pd.DataFrame([dict(QUOTA_TRANSACTION_ID='base',QUOTA_ID='quota',OWNER_ACCOUNT_ID='maritime',TRANSACTION_TYPE='Base',EFFECTIVE_DATE='2020-01-01',QUOTA_COUNT=234913)])
    repo._salmonella_tests = pd.DataFrame([
        dict(SALMONELLA_TEST_ID='s1',ACCOUNT_ID='salmonella',FLOCK_ID='salmonella-flock',PERMIT_NUMBER='40285',TESTING_DATE='2024-01-03',TEST_RESULT='Negative',DATE_RESULT_SENT='2024-01-08'),
        dict(SALMONELLA_TEST_ID='s2',ACCOUNT_ID='salmonella',FLOCK_ID='salmonella-flock',PERMIT_NUMBER='40285',TESTING_DATE='2024-12-04',TEST_RESULT='Negative',DATE_RESULT_SENT='2024-12-10')])
    return repo


def example_form(handler):
    repo = legacy_form_repository()
    return build_printable_form(repo,handler,user=user(),registration='7173' if handler=='license_application_pdf' else '7107',
        report_date=date(2027,1,1),layer_permit='40289' if handler=='flock_permit_pdf' else '40285')


def pdf_text(form):
    reader = PdfReader(BytesIO(render_form_pdf(form)))
    return reader, '\n'.join(page.extract_text() for page in reader.pages)


@pytest.mark.parametrize('handler',FORM_HANDLERS)
def test_legacy_pdf_text_layout_and_logo(handler):
    form = example_form(handler)
    reader, content = pdf_text(form)
    page = reader.pages[0]
    assert len(reader.pages)==1
    assert tuple(map(int,(page.mediabox.width,page.mediabox.height)))==((792,612) if handler=='flock_permit_pdf' else (612,792))
    assert page.images
    assert not re.search(r'(?<!\w)(None|nan|NaT|<NA>)(?!\w)',content)
    expected = (w.LICENSE_TITLE+(*w.DECLARATIONS,'complaince','234,913','Maritime Pride Poultry Inc.','Pierre-David Cyr','Friday, January 1, 2027') if handler=='license_application_pdf'
        else (w.PERMIT_TITLE,*w.PERMIT_SECTIONS,'40289','30289','Centerbrook Poultry Ltd.','Jeffrey Clarke','10000','Atlantic Poultry Incorporated - NB Hatchery') if handler=='flock_permit_pdf'
        else (*w.SALMONELLA_TITLE,w.NOTIFICATION,w.MARKET_RESTRICTION,w.FARM_GATE,w.RESULT_CLOSING,'7107','40285','7107-Ueffing','1/3/2024','1/8/2024','12/4/2024','12/10/2024','Negative'))
    flat=' '.join(content.split())
    for value in expected:assert ' '.join(value.split()) in flat
    fills=[tuple(float(x) for x in args) for args,op in ContentStream(page.get_contents(),reader).operations if op==b'rg']
    assert (w.LICENSE_BLUE if handler=='license_application_pdf' else w.FORM_BLUE) in fills


def test_fixed_wording_is_present_in_legacy_sources():
    legacy = {'license': 'EIMSLicenseApplicationForm.pdf','permit':'EIMSFlockPermitForm.pdf','salmonella':'EIMSFlockSalmonellaTestingForm.pdf'}
    expected = {'license':(*w.LICENSE_TITLE,*w.DECLARATIONS), 'permit':(w.PERMIT_TITLE,*w.PERMIT_SECTIONS),
                'salmonella':(*w.SALMONELLA_TITLE,w.NOTIFICATION,w.MARKET_RESTRICTION,w.FARM_GATE,w.RESULT_CLOSING)}
    for kind,name in legacy.items():
        content=' '.join(PdfReader(ROOT/'tests/fixtures/legacy_forms'/name).pages[0].extract_text().split())
        for text in expected[kind]:assert ' '.join(text.split()) in content


@pytest.mark.parametrize('handler',FORM_HANDLERS)
def test_empty_forms_generate_valid_pdf_with_clear_message(handler):
    repo=legacy_form_repository()
    for name,value in list(vars(repo).items()):
        if isinstance(value,pd.DataFrame):setattr(repo,name,value.iloc[:0].copy())
    form=build_printable_form(repo,handler,user=user(),registration='missing',report_date=date(2027,1,1),layer_permit='missing')
    assert not form.has_data and form.preview.empty
    reader,text=pdf_text(form)
    assert len(reader.pages)==1 and w.NO_DATA in text


def test_missing_state_evidence_leaves_quota_unknown():
    repo=legacy_form_repository()
    form=build_license_application(repo._accounts,repo._facilities,repo._farm_locations,repo._quota_registrations,
        repo._quota_transactions,'7173',date(2027,1,1),None,load_rules())
    assert form.fields['Quota']==''
    assert 'Transaction state evidence unavailable' in form.notes


def test_7173_license_barns_only_active_layers_and_show_housing_system():
    form=example_form('license_application_pdf')
    assert form.tables['barns']==[
        ['7173 - A'+str(i),'Enriched','623 Travis Rd\nAmherst\nNova Scotia'] for i in range(1,5)]
    _,content=pdf_text(form)
    assert 'Enriched' in content
    for excluded in ('AP1','AP2','CV1','M1','Org1'):
        assert '7173 - '+excluded not in content


def test_null_housing_system_keeps_barn_and_discloses_blank(tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    repo=legacy_form_repository()
    repo._facilities.loc[repo._facilities.FACILITY_ID.eq('maritime-1'),'HOUSING_SYSTEM']=None
    form=build_printable_form(repo,'license_application_pdf',user=user(),registration='7173',report_date=date(2027,1,1))
    assert len(form.tables['barns'])==4
    assert form.tables['barns'][0][1]==''
    assert 'Housing System (Facility Type column)' in form.missing_fields
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    app.button(key='open_report_license-application').click().run()
    app.selectbox(key='print_license_application_pdf_registration').set_value('7173').run()
    app.button(key='run_license_application_pdf').click().run()
    assert not app.exception and not app.error
    assert any('Housing System (Facility Type column)' in item.value for item in app.info)


@pytest.mark.parametrize('value',['Self',' self ','sELF'])
@pytest.mark.parametrize('mode',['literal','linked'])
def test_license_self_relationships_use_own_organization(value,mode):
    repo=legacy_form_repository()
    if mode=='literal':
        repo._accounts.loc[0,'PULLET_GROWER_ACCOUNT_ID']=value
        repo._accounts.loc[0,'GRADING_STATION_ACCOUNT_ID']=value
        repo._accounts.loc[0,'SPENT_FOWL_PLANS']=value
    else:
        repo._accounts=pd.concat([repo._accounts,pd.DataFrame([dict(ACCOUNT_ID='self-source',ORGANIZATION_NAME=value)])],ignore_index=True)
        for column in ('PULLET_GROWER_ACCOUNT_ID','GRADING_STATION_ACCOUNT_ID','SPENT_FOWL_PLANS_ACCOUNT_ID'):
            repo._accounts.loc[0,column]='self-source'
    original=repo._accounts.copy(deep=True)
    form=build_printable_form(repo,'license_application_pdf',user=user(),registration='7173',report_date=date(2027,1,1))
    for label in w.RELATIONSHIP_HEADERS:assert form.fields[label]=='Maritime Pride Poultry Inc.'
    pd.testing.assert_frame_equal(repo._accounts,original)


def test_nullable_fields_are_blank_and_disclosed_without_inferred_addresses():
    repo=legacy_form_repository()
    repo._accounts.loc[0,['CONTACT_NAME','CONTACT_PHONE','CONTACT_EMAIL','ADDRESS_LINE1','CITY','PROVINCE','POSTAL_CODE']]=None
    repo._facilities['FARM_LOCATION_ID']=None
    form=build_printable_form(repo,'license_application_pdf',user=user(),registration='7173',report_date=date(2027,1,1))
    assert form.fields['Primary Contact']=='' and form.fields['Mailing Address']==''
    assert 'Primary Contact' in form.missing_fields
    assert 'Barn Address (linked Farm Location)' in form.missing_fields
    assert all(row[2]=='' for row in form.tables['barns'])
    _,text=pdf_text(form)
    assert 'None' not in text and 'nan' not in text


def test_paired_suffixed_pullet_permits_are_all_retained():
    repo=legacy_form_repository()
    base=repo._flocks.iloc[1].to_dict()
    repo._flocks=pd.DataFrame([dict(repo._flocks.iloc[0],PERMIT_NUMBER='40403'),
        *[dict(base,PERMIT_NUMBER=p,FLOCK_ID=p) for p in ('30403a','30403b','30404')]])
    assert matching_pullet_permits(repo._flocks,'40403')==['30403a','30403b']
    form=build_flock_permit(repo._accounts,repo._flocks,repo._facilities,repo._farm_locations,'40403')
    assert [r[0] for r in form.tables['pullets']]==['30403a','30403b']
    assert [r[0] for r in form.tables['hatcheries']]==['30403a','30403b']
    one=build_flock_permit(repo._accounts,repo._flocks,repo._facilities,repo._farm_locations,'40403',['30403b'])
    assert [r[0] for r in one.tables['pullets']]==['30403b']
    with pytest.raises(ValueError,match='must match'):build_flock_permit(repo._accounts,repo._flocks,repo._facilities,repo._farm_locations,'40403',['30404'])


def test_permit_null_dates_quantities_and_owner_fields_stay_blank():
    repo=legacy_form_repository()
    repo._flocks[['HATCH_DATE','PLACEMENT_DATE','BIRD_COUNT','EGG_COLOUR','BIRD_STRAIN','HATCHERY']]=None
    repo._accounts['REGISTRATION_NUMBER']=None
    form=build_flock_permit(repo._accounts,repo._flocks,repo._facilities,repo._farm_locations,'40289')
    assert form.tables['layers'][0][1]==''
    assert form.tables['layers'][0][3:8]==['']*5
    assert 'Birds' in form.missing_fields and 'Hatchery' in form.missing_fields
    _,content=pdf_text(form)
    assert not re.search(r'(?<!\w)(None|nan|NaT|<NA>)(?!\w)',content)


def test_salmonella_null_sample_date_result_and_comments_are_blank():
    repo=legacy_form_repository()
    repo._salmonella_tests[['TESTING_DATE','TEST_RESULT','COMMENTS','DATE_RESULT_SENT','DATE_RECEIVED']]=None
    form=build_salmonella_form(repo._accounts,repo._flocks,repo._facilities,repo._salmonella_tests,'7107','40285')
    assert form.has_data and all(row[3:]==['']*4 for row in form.tables['results'])
    assert 'Sample Date' in form.missing_fields and 'Sample Result' in form.missing_fields
    _,content=pdf_text(form)
    assert not re.search(r'(?<!\w)(None|nan|NaT|<NA>)(?!\w)',content)


def test_salmonella_filters_and_result_sent_date():
    repo=legacy_form_repository()
    form=build_salmonella_form(repo._accounts,repo._flocks,repo._facilities,repo._salmonella_tests,
        '7107','40285','Pass',date(2024,1,1),date(2024,1,31))
    assert len(form.tables['results'])==1
    assert form.tables['results'][0][3:] == ['1/3/2024','1/8/2024','Negative','']
    assert 'Date Result' not in form.missing_fields
    all_rows=build_salmonella_form(repo._accounts,repo._flocks,repo._facilities,repo._salmonella_tests,'7107','40285').tables['results']
    assert [[row[3],row[4]] for row in all_rows]==[['1/3/2024','1/8/2024'],['12/4/2024','12/10/2024']]
    assert not build_salmonella_form(repo._accounts,repo._flocks,repo._facilities,repo._salmonella_tests,'7107','40285','Fail').has_data
    with pytest.raises(ValueError,match='start'):build_salmonella_form(repo._accounts,repo._flocks,repo._facilities,repo._salmonella_tests,'7107','40285','All',date(2025,1,1),date(2024,1,1))


@pytest.mark.parametrize('sent,received,expected',[
    ('2024-01-08','2099-01-01','1/8/2024'),
    (None,'2023-06-17','6/17/2023'),
    (pd.NaT,'2023-07-12','7/12/2023'),
    (pd.NA,'2024-12-10','12/10/2024'),
    (None,None,''),
])
def test_40285_result_date_sent_priority_and_null_received_fallback(sent,received,expected):
    repo=legacy_form_repository()
    repo._salmonella_tests=repo._salmonella_tests.iloc[:1].copy()
    repo._salmonella_tests['DATE_RESULT_SENT']=sent
    repo._salmonella_tests['DATE_RECEIVED']=received
    if expected in {'6/17/2023','7/12/2023'}:
        # Only result dates were supplied for the 2023 rows; do not invent their sample dates.
        repo._salmonella_tests['TESTING_DATE']=None
    form=build_salmonella_form(repo._accounts,repo._flocks,repo._facilities,repo._salmonella_tests,'7107','40285')
    assert form.tables['results'][0][4]==expected
    assert ('Date Result' in form.missing_fields)==(expected=='')
    _,content=pdf_text(form)
    if expected:assert expected in content
    assert 'None' not in content and 'NaT' not in content and '<NA>' not in content


def test_more_barns_paginate_without_dropping_declarations():
    form=example_form('license_application_pdf')
    form.tables['barns']*=12
    reader,text=pdf_text(form)
    assert len(reader.pages)>1
    assert 'complaince' in text and 'Signature' in text


@pytest.mark.parametrize('stored,choice',[('Pass','Pass'),('Negative','Pass'),('Fail','Fail'),('Positive','Fail')])
def test_salmonella_result_aliases_preserve_stored_text(stored,choice):
    repo=legacy_form_repository()
    repo._salmonella_tests=repo._salmonella_tests.iloc[:1].copy()
    repo._salmonella_tests['TEST_RESULT']=stored
    form=build_salmonella_form(repo._accounts,repo._flocks,repo._facilities,repo._salmonella_tests,'7107','40285',choice)
    assert form.tables['results'][0][5]==stored


def test_pullet_selector_offers_one_or_all_and_clears_stale_pdf(tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    repo=legacy_form_repository()
    repo._flocks=pd.concat([repo._flocks,pd.DataFrame([dict(repo._flocks.iloc[1],FLOCK_ID='second',PERMIT_NUMBER='30289a')])],ignore_index=True)
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/4_Reports.py').run()
    app.button(key='open_report_flock-permit').click().run()
    widget=app.selectbox(key='print_flock_permit_pdf_pullets_40285')
    assert any('no matching Pullet permit' in item.value for item in app.info)
    app.selectbox(key='print_flock_permit_pdf_layer').set_value('40289').run()
    widget=app.selectbox(key='print_flock_permit_pdf_pullets_40289')
    assert widget.options==['All matching pullet permits','30289','30289a']
    app.button(key='run_flock_permit_pdf').click().run()
    assert len(app.session_state['print_flock_permit_pdf_document'].tables['pullets'])==2
    app.selectbox(key=widget.key).set_value('30289a').run()
    assert not app.get('download_button')
    app.button(key='run_flock_permit_pdf').click().run()
    assert len(app.session_state['print_flock_permit_pdf_document'].tables['pullets'])==1
    assert not app.exception and not app.error


@pytest.mark.parametrize('handler',FORM_HANDLERS)
def test_form_page_generates_download(handler,tmp_path,monkeypatch):
    from tests.auth_support import authenticated_app
    from app.services.report_center import REPORT_CATALOG
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=legacy_form_repository()
    app.switch_page('app/pages/4_Reports.py').run()
    report=next(r for r in REPORT_CATALOG if r.handler==handler)
    assert report.status=='Available' and report.export_formats==('PDF',)
    app.button(key='open_report_'+report.report_id).click().run()
    if handler!='flock_permit_pdf':
        app.selectbox(key='print_'+handler+'_registration').set_value('7173' if handler=='license_application_pdf' else '7107').run()
    app.button(key='run_'+handler).click().run()
    assert not app.exception and not app.error
    assert any(button.label=='Download PDF' for button in app.get('download_button'))
    assert app.dataframe


def test_form_artifact_hashes_and_shipped_dependencies():
    import yaml
    manifest=json.loads((ROOT/'DELIVERY_RUNTIME_DIFF_20261030.json').read_text())
    for entry in manifest['printable_form_artifacts']:
        raw=(ROOT/entry['path']).read_bytes()
        if 'candidate_lf_sha256' in entry:raw=raw.replace(b'\r\n',b'\n')
        assert hashlib.sha256(raw).hexdigest()==entry.get('candidate_lf_sha256',entry.get('candidate_sha256'))
    env=yaml.safe_load((ROOT/'environment.yml').read_text())
    assert 'reportlab=5.0.0' in env['dependencies']
    cfg=yaml.safe_load((ROOT/'snowflake.yml').read_text())
    assert {'src':'app/assets/*.png','dest':'app/assets/'} in cfg['entities']['efns_dev']['artifacts']
