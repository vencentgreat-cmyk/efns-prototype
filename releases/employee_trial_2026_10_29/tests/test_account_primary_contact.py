"""Synthetic Account form contact and existing licence-PDF integration."""
import datetime as dt
from io import BytesIO
from pathlib import Path
import re

import pytest
from pypdf import PdfReader

from app.services.printable_forms import build_printable_form, render_form_pdf
from data.business_time import same_value
from data.repositories.snowflake import MODEL
from tests.auth_support import authenticated_app
from tests.test_report_center import user
from tests.test_staff_workflows import chain


ROOT = Path(__file__).resolve().parents[1]
PAGE = 'app/pages/3_Accounts_Facilities_Flocks.py'


def account_page(repo, tmp_path, monkeypatch, entry, account=None):
    app = authenticated_app(ROOT / entry, tmp_path, monkeypatch)
    app.session_state['_base_repo'] = repo
    app.session_state['_efns_record_3_Accounts_Facilities_Flocks_view'] = 'edit' if account else 'new'
    app.session_state['_efns_record_3_Accounts_Facilities_Flocks_id'] = account
    app.switch_page(PAGE.removeprefix('app/') if entry == 'app/Home.py' else PAGE).run()
    assert not app.exception
    labels = [w.label for w in app.text_input]
    assert labels.index('Primary Contact') + 1 == labels.index('Account Email')
    return app


def licence(repo, registration):
    return build_printable_form(repo, 'license_application_pdf', user=user(),
                                registration=registration, report_date=dt.date(2026, 11, 27))


@pytest.mark.parametrize('entry', ['streamlit_app.py', 'app/Home.py'])
def test_create_contact_is_saved_shown_and_printed(chain, tmp_path, monkeypatch, entry):
    repo, *_ = chain
    app = account_page(repo, tmp_path, monkeypatch, entry)
    app.text_input(key='account_form_name').input('Synthetic applicant')
    app.text_input(key='account_form_registration').input('SYNTHETIC-PRIMARY')
    app.text_input(key='account_form_contact_name').input('  USER_A  ')
    app.button(key='account_record_save').click().run()
    assert not app.exception and not app.error
    account = repo.find_accounts_by_registration_number('SYNTHETIC-PRIMARY').iloc[0]
    assert account.CONTACT_NAME == 'USER_A'
    assert any('Primary Contact' in m.value and 'USER_A' in m.value for m in app.markdown)
    form = licence(repo, 'SYNTHETIC-PRIMARY')
    assert form.fields['Primary Contact'] == 'USER_A'
    assert 'Primary Contact' not in form.missing_fields
    text = '\n'.join(p.extract_text() for p in PdfReader(BytesIO(render_form_pdf(form))).pages)
    assert 'USER_A' in text


@pytest.mark.parametrize('entry', ['streamlit_app.py', 'app/Home.py'])
def test_contact_only_revision_requires_reason_and_can_clear_to_null(chain, tmp_path, monkeypatch, entry):
    repo, account, *_ = chain
    app = account_page(repo, tmp_path, monkeypatch, entry, account)
    app.text_input(key='account_form_contact_name').input('USER_B')
    app.text_input(key='account_form_revision_reason').input('Synthetic contact correction')
    app.button(key='account_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_account(account)['CONTACT_NAME'] == 'USER_B'
    assert any('Primary Contact' in m.value and 'USER_B' in m.value for m in app.markdown)
    revisions = repo.get_record_revisions_for('ACCOUNT', account)
    assert len(revisions) == len(repo._migration_review_audit) == 1
    revision = revisions.iloc[0]
    assert revision.REASON == 'Synthetic contact correction'
    assert revision.AFTER_DATA['CONTACT_NAME'] == 'USER_B'
    assert {field for field in MODEL['ACCOUNT'][1].split()
            if not same_value(revision.BEFORE_DATA.get(field), revision.AFTER_DATA.get(field))} == {'CONTACT_NAME'}
    audit = repo._migration_review_audit[0]
    assert audit['ENTITY_ID'] == account and audit['DETAILS']['reason'] == revision.REASON
    assert licence(repo, '001').fields['Primary Contact'] == 'USER_B'
    assert 'Primary Contact' not in licence(repo, '001').missing_fields

    app = account_page(repo, tmp_path, monkeypatch, entry, account)
    assert app.text_input(key='account_form_contact_name').value == 'USER_B'
    app.text_input(key='account_form_contact_name').input('   ')
    app.text_input(key='account_form_revision_reason').input('Synthetic contact cleared')
    app.button(key='account_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_account(account)['CONTACT_NAME'] is None
    assert len(repo.get_record_revisions_for('ACCOUNT', account)) == len(repo._migration_review_audit) == 2
    assert 'Primary Contact' in licence(repo, '001').missing_fields


@pytest.mark.parametrize('length,valid', [(255, True), (256, False)])
def test_contact_length_matches_existing_schema(chain, tmp_path, monkeypatch, length, valid):
    assert 'CONTACT_NAME' in MODEL['ACCOUNT'][1].split()
    assert re.search(r'CONTACT_NAME\s+VARCHAR\(255\)', (ROOT/'sql/02_core_tables.sql').read_text())
    repo, account, *_ = chain
    app = account_page(repo, tmp_path, monkeypatch, 'streamlit_app.py', account)
    app.text_input(key='account_form_contact_name').input('X' * length)
    app.text_input(key='account_form_revision_reason').input('Synthetic length check')
    app.button(key='account_record_save').click().run()
    assert not app.exception
    if valid:
        assert not app.error and repo.get_account(account)['CONTACT_NAME'] == 'X' * length
    else:
        assert any('Primary Contact must be 255' in e.value for e in app.error)
        assert repo.get_record_revisions_for('ACCOUNT', account).empty


def test_unchanged_contact_retains_stored_value_on_other_correction(chain, tmp_path, monkeypatch):
    repo, account, *_ = chain
    repo._accounts.loc[repo._accounts.ACCOUNT_ID.eq(account), 'CONTACT_NAME'] = '  USER_C  '
    app = account_page(repo, tmp_path, monkeypatch, 'streamlit_app.py', account)
    app.text_area(key='account_form_description').input('Synthetic note only')
    app.text_input(key='account_form_revision_reason').input('Synthetic unrelated correction')
    app.button(key='account_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_account(account)['CONTACT_NAME'] == '  USER_C  '


def test_contact_correction_without_reason_is_rejected(chain, tmp_path, monkeypatch):
    repo, account, *_ = chain
    app = account_page(repo, tmp_path, monkeypatch, 'streamlit_app.py', account)
    app.text_input(key='account_form_contact_name').input('USER_D')
    app.button(key='account_record_save').click().run()
    assert not app.exception and app.error
    assert repo.get_record_revisions_for('ACCOUNT', account).empty
    assert not getattr(repo, '_migration_review_audit', [])
