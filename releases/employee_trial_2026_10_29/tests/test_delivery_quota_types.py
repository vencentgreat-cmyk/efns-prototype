"""Synthetic label compatibility; views may group aliases but never rewrite rows."""
from pathlib import Path
import datetime as dt

import pandas as pd
import pytest

from app.services.quota_usage import account_usage_context
from app.services.report_center import build_custom_report
from data.constants import QUOTA_TYPES, FLOCK_QUOTA_TYPES
from data.quota_types import quota_type_key
from data.repositories.snowflake import SnowflakeRepository
from data.operational_flock_quota_import import analyze_operational_files
from tests.test_operational_flock_quota_import import csv_upload
from tests.test_round2 import _commit_daily
from tests.test_report_center import user
from tests.test_staff_workflows import chain
from tests.auth_support import authenticated_app


PAIRS = [('Non Commercial Pullet Quota', 'Non-Commercial Pullet'),
         ('Commercial Pullet Grower', 'Commercial Pullet')]


def test_exact_new_entry_quota_choices():
    assert QUOTA_TYPES == FLOCK_QUOTA_TYPES == (
        'Egg Production', 'Non Commercial Pullet Quota', 'Commercial Pullet Grower')


@pytest.mark.parametrize('canonical,legacy', PAIRS)
def test_mock_filter_usage_and_report_group_aliases_without_rewrite(chain, canonical, legacy):
    repo, account, other, facility, quota, flock, record = chain
    first = repo.upsert_quota_registration(dict(ACCOUNT_ID=account, REGISTRATION_NUMBER='DEV_TEST legacy', QUOTA_TYPE=legacy))
    second = repo.upsert_quota_registration(dict(ACCOUNT_ID=account, REGISTRATION_NUMBER='DEV_TEST canonical', QUOTA_TYPE=canonical))
    for name in (canonical, legacy):
        assert {first, second} <= set(repo.get_quota_registrations(quota_type=name).QUOTA_ID)
        assert quota_type_key(name) == canonical
    for i, kind in enumerate((canonical, legacy)):
        repo.upsert_flock(dict(record, FLOCK_NUMBER=f'DEV_TEST type {i}', PERMIT_NUMBER=f'DEV_TEST type {i}',
                             QUOTA_ID=None, FLOCK_QUOTA_TYPE=kind, BIRD_COUNT=5))
    context = account_usage_context(repo, account)
    summary = next(r for r in context['summaries'] if r['quota_type'] == canonical)
    assert summary['flock_count'] == 2 and summary['known_bird_count'] == 10
    result = build_custom_report(repo, user=user(), dataset='Flocks',
        selected_fields=['FLOCK_QUOTA_TYPE', 'BIRD_COUNT'], filters={'quota_type':canonical},
        group_by=['FLOCK_QUOTA_TYPE'], aggregations={'BIRD_COUNT':'sum'})
    assert len(result) == 1 and result.iloc[0]['Quota Type'] == canonical and result.iloc[0]['Bird Count'] == 10
    assert repo.get_quota_registration(first)['QUOTA_TYPE'] == legacy
    assert legacy in repo.get_flocks().FLOCK_QUOTA_TYPE.tolist()


@pytest.mark.parametrize('canonical,legacy', PAIRS)
def test_native_read_predicates_bind_both_spellings(chain, canonical, legacy):
    repo = SnowflakeRepository()
    calls = []
    repo._query = lambda sql, params=None: calls.append((sql, params)) or pd.DataFrame()
    repo.get_quota_registrations(quota_type=canonical)
    repo.get_quota_registrations(quota_type=legacy, active_only=True)
    repo.get_quota_transactions(quota_type=canonical)
    repo.get_quota_summary(dt.date(2026, 10, 30), canonical)
    repo.get_quota_allocations(quota_type=legacy)
    assert len(calls) == 5
    for sql, params in calls:
        assert 'QUOTA_TYPE IN' in sql and canonical in params and legacy in params
        assert canonical not in sql and legacy not in sql


@pytest.mark.parametrize('label', ['Non Commercial Pullet Quota', 'Non-Commercial Pullet',
                                  'Commercial Pullet Grower', 'Commercial Pullet'])
def test_daily_quota_create_update_commits_without_relabeling(chain, label):
    repo, account, *_ = chain
    row = {'ACTION':'CREATE', 'Registration Number':'DEV_TEST daily quota',
           'Account':account, 'Quota Type':label, 'Effective Date':'2020-01-01'}
    report = analyze_operational_files([csv_upload('synthetic.csv',[row])], 'Quota Registrations', repo)
    assert len(report.ready_rows) == 1 and not report.rejected_rows
    _commit_daily(repo, report, 'synthetic.csv')
    saved = repo.get_quota_registrations()
    saved = saved[saved.REGISTRATION_NUMBER == row['Registration Number']].iloc[0]
    assert saved.QUOTA_TYPE == label
    update = {'ACTION':'UPDATE', 'Quota ID':saved.QUOTA_ID, 'Registration Number':row['Registration Number'],
              'Account':account, 'Comments':'DEV_TEST notes only'}
    report = analyze_operational_files([csv_upload('update.csv',[update])], 'Quota Registrations', repo)
    assert len(report.ready_rows) == 1 and not report.rejected_rows
    _commit_daily(repo, report, 'update.csv')
    assert repo.get_quota_registration(saved.QUOTA_ID)['QUOTA_TYPE'] == label


def test_legacy_registration_edit_keeps_value_visible(chain, tmp_path, monkeypatch):
    repo, account, *_ = chain
    identity = repo.upsert_quota_registration(dict(ACCOUNT_ID=account, REGISTRATION_NUMBER='DEV_TEST old quota',
        QUOTA_NAME='DEV_TEST old quota', QUOTA_TYPE='Non-Commercial Pullet'))
    app = authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py', tmp_path, monkeypatch)
    app.session_state['_base_repo'] = repo
    app.session_state['_efns_record_7_Quota_Registrations_view'] = 'edit'
    app.session_state['_efns_record_7_Quota_Registrations_id'] = identity
    app.switch_page('app/pages/7_Quota_Registrations.py').run()
    assert not app.exception and app.selectbox(key='quota_reg_form_type').value == 'Non-Commercial Pullet'
    app.text_area(key='quota_reg_form_comments').input('DEV_TEST preserved type')
    app.text_input(key='quota_reg_form_revision_reason').input('DEV_TEST notes')
    app.button(key='quota_reg_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_quota_registration(identity)['QUOTA_TYPE'] == 'Non-Commercial Pullet'
