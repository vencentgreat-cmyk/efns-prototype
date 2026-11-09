"""Round-2 independent re-review at 9b04611 (synthetic Mock data only).

Part A ports the round-1 reproductions (repros/test_review_repros.py) and now
asserts the CORRECT behaviour. Part B adds scenarios not covered by the
candidate's own tests. A failing test is a finding.
"""
import datetime as dt
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from app.security import Role, User
from app.services.authorized_repository import AuthorizedRepository
from app.services.report_center import build_custom_report
from data.business_time import halifax_today
from data.operational_flock_quota_import import analyze_operational_files
from data.repositories.base import RepositoryError
from tests.auth_support import authenticated_app
from tests.test_operational_flock_quota_import import csv_upload
from tests.test_report_center import user as report_user
from tests.test_staff_workflows import chain  # noqa: F401
from tests.test_account_usage_quantity import ACTOR

ROOT = Path(__file__).resolve().parents[1]
EDITOR = User('u1', 'editor@nsegg.ca', 'Editor', Role.DATA_EDITOR, True, False, 'now', 'now', None)


def _set(repo, attr, key, record_id, **values):
    frame = getattr(repo, attr)
    for column, value in values.items():
        if column not in frame:
            frame[column] = None
        frame[column] = frame[column].astype(object)
        frame.loc[frame[key] == record_id, column] = value


def _app(r, tmp_path, monkeypatch):
    app = authenticated_app(ROOT / 'streamlit_app.py', tmp_path, monkeypatch)
    app.session_state['_base_repo'] = r
    return app


def _open(app, page, record_id, view='edit'):
    slug = page.removesuffix('.py').split('/')[-1]
    app.session_state[f'_efns_record_{slug}_view'] = view
    app.session_state[f'_efns_record_{slug}_id'] = record_id
    return app.switch_page(page).run()


MOCK_NOTE = 'Mock data is stored only in this browser session.'


def _msgs(app):
    return [m.value for m in (*app.error, *app.warning) if m.value != MOCK_NOTE]


# ======================= Part A: round-1 reproductions, correct assertions ====
def test_A_D1_flock_comment_edit_preserves_everything_else(chain, tmp_path, monkeypatch):
    r, a, o, f, q, flock, record = chain
    _set(r, '_quota_registrations', 'QUOTA_ID', q, STATUS='Inactive')
    _set(r, '_flocks', 'FLOCK_ID', flock, HATCH_DATE=None, EGG_COLOUR=None, STATUS='Inactive',
         FLOCK_QUOTA_TYPE=None, BIRDS_DISPOSED=None, CREATE_DELIVERY_TRANSACTION=None)
    before = r.get_flock(flock)
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/5_Flocks.py', flock)
    assert not app.exception
    app.text_area(key='flock_form_comments').input('Only the comment changed')
    app.text_input(key='flock_form_revision_reason').input('Add a comment')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error, _msgs(app)
    after = r.get_flock(flock)
    assert after['COMMENTS'] == 'Only the comment changed'
    for field in ('HATCH_DATE', 'EGG_COLOUR', 'STATUS', 'FLOCK_QUOTA_TYPE', 'QUOTA_ID', 'BIRDS_DISPOSED', 'CREATE_DELIVERY_TRANSACTION', 'BIRD_COUNT'):
        assert (pd.isna(before[field]) and pd.isna(after[field])) or before[field] == after[field], field


def test_A_D1_D2_salmonella_comment_edit_keeps_result_permit_and_records_history(chain, tmp_path, monkeypatch):
    r, a, o, f, q, flock, record = chain
    test_id = r.upsert_salmonella_test(dict(FLOCK_ID=flock, ACCOUNT_ID=a, PERMIT_NUMBER=record['PERMIT_NUMBER'],
                                            TESTING_DATE=dt.date(2026, 1, 5), NUMBER_OF_SAMPLES=2, TEST_RESULT='Negative'))
    _set(r, '_salmonella_tests', 'SALMONELLA_TEST_ID', test_id, TEST_RESULT='Not Tested')
    _set(r, '_flocks', 'FLOCK_ID', flock, PERMIT_NUMBER='NEW-PERMIT-2026')
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/9_Salmonella_Tests.py', test_id)
    assert not app.exception
    app.text_area(key='salmonella_form_comments').input('Typo fix in comment')
    reason = [t for t in app.text_input if 'reason' in (t.key or '').lower()]
    if reason:
        reason[0].input('Comment typo')
    app.button(key='salmonella_record_save').click().run()
    assert not app.exception and not app.error, _msgs(app)
    saved = r.get_salmonella_test(test_id)
    assert saved['COMMENTS'] == 'Typo fix in comment'
    assert saved['TEST_RESULT'] == 'Not Tested'
    assert saved['PERMIT_NUMBER'] == record['PERMIT_NUMBER']
    revisions = r.get_record_revisions()
    assert (revisions.ENTITY_ID == test_id).any()


@pytest.mark.parametrize('stored', [None, 0, 2.5])
def test_A_D1_flock_transaction_note_edit_keeps_historical_quantity(chain, tmp_path, monkeypatch, stored):
    r, a, o, f, q, flock, record = chain
    tx = r._upsert_frame('_flock_transactions', 'FLOCK_TRANSACTION_ID',
                         dict(FLOCK_ID=flock, TRANSACTION_TYPE='Removal', QUANTITY=stored,
                              TRANSACTION_DATE=dt.date(2025, 3, 1), NOTES=None))
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/6_Flock_Transactions.py', tx)
    assert not app.exception
    app.text_area(key='flock_tx_form_notes').input('Clarify source')
    app.text_input(key='flock_tx_form_revision_reason').input('Note added')
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error, _msgs(app)
    row = r.get_flock_transactions(flock_id=flock).set_index('FLOCK_TRANSACTION_ID').loc[tx]
    assert row.NOTES == 'Clarify source'
    assert (stored is None and pd.isna(row.QUANTITY)) or row.QUANTITY == stored


def test_A_D3_reused_manual_request_with_new_content_is_not_silent(chain):
    r, a, *_ = chain
    r.create_manual_production(dict(PRODUCER_ACCOUNT_ID=a, REPORTING_YEAR=2026, REPORTING_WEEK=40, TOTAL=Decimal('100')), 'req-1', actor=ACTOR)
    with pytest.raises(RepositoryError):
        r.create_manual_production(dict(PRODUCER_ACCOUNT_ID=a, REPORTING_YEAR=2026, REPORTING_WEEK=41, TOTAL=Decimal('250')), 'req-1', actor=ACTOR)
    r.create_manual_production(dict(PRODUCER_ACCOUNT_ID=a, REPORTING_YEAR=2026, REPORTING_WEEK=41, TOTAL=Decimal('250')), 'req-2', actor=ACTOR)
    assert sorted(int(x) for x in r._production.REPORTING_WEEK) == [40, 41]


def test_A_D4_reused_attribute_request_with_new_content_is_not_silent(chain):
    r, a, o, f, q, flock, record = chain
    v = r.get_flock(flock)['UPDATED_AT']
    r.revise_record('FLOCK', flock, {'COMMENTS': 'first'}, 'reason one', 'same-request', actor=ACTOR, expected_updated_at=v)
    with pytest.raises(RepositoryError):
        r.revise_record('FLOCK', flock, {'COMMENTS': 'second'}, 'reason two', 'same-request', actor=ACTOR,
                        expected_updated_at=r.get_flock(flock)['UPDATED_AT'])
    assert r.get_flock(flock)['COMMENTS'] == 'first'


def _flock_update(repo, flock, **extra):
    current = repo.get_flock(flock)
    row = {'Flock Number': current['FLOCK_NUMBER'], 'Account': current['ACCOUNT_ID'], 'Comments': 'daily update'}
    row.update(extra)
    return analyze_operational_files([csv_upload('flocks.csv', [row])], 'Flocks', repo)


def _commit_daily(repo, report, name='flocks.csv'):
    from tests.test_operational_review_persistence import prepare
    upload = csv_upload(name, [r.raw_data for r in report.ready_rows + report.rejected_rows])
    batch, staged, _ = prepare(repo, upload)
    return repo.commit_staged_operational(batch, staged.records_by_entity, actor='staff')


def test_A_D5_daily_update_keeps_unknown_disposed_and_status_through_commit(chain):
    r, a, o, f, q, flock, record = chain
    _set(r, '_flocks', 'FLOCK_ID', flock, BIRDS_DISPOSED=None, STATUS=None, FACILITY_DETAIL_ID=None)
    report = _flock_update(r, flock)
    assert len(report.ready_rows) == 1
    write = report.ready_rows[0].write_record
    assert pd.isna(write.get('BIRDS_DISPOSED')) and pd.isna(write.get('STATUS'))
    _commit_daily(r, report)
    after = r.get_flock(flock)
    assert after['COMMENTS'] == 'daily update'
    assert pd.isna(after['BIRDS_DISPOSED']) and pd.isna(after['STATUS'])


def test_A_D6_after_count_zero_daily_update_is_accepted_and_commits(chain):
    r, a, o, f, q, flock, record = chain
    _set(r, '_flocks', 'FLOCK_ID', flock, BIRDS_DISPOSED=120, FACILITY_DETAIL_ID=None)
    r.record_current_flock_quantity(dict(FLOCK_ID=flock, TRANSACTION_TYPE='Count', QUANTITY=0, TRANSACTION_DATE=halifax_today()),
                                    'zero', r.get_flock(flock)['UPDATED_AT'], 'Barn empty', confirmed=True, actor=ACTOR,
                                    expected_bird_count=10)
    report = _flock_update(r, flock)
    assert len(report.ready_rows) == 1
    _commit_daily(r, report)
    after = r.get_flock(flock)
    assert after['BIRD_COUNT'] == 0 and after['BIRDS_DISPOSED'] == 120 and after['COMMENTS'] == 'daily update'


def test_A_D7_daily_transactions_follow_form_rules_in_preview(chain):
    r, a, o, f, q, flock, record = chain
    number = r.get_flock(flock)['FLOCK_NUMBER']
    rows = [{'Flock': number, 'Transaction Type': kind, 'Quantity': qty, 'Transaction Date': '2026-10-01'}
            for kind, qty in (('Removal', '0'), ('Removal', '2.5'), ('Mortality', '5'))]
    report = analyze_operational_files([csv_upload('tx.csv', rows)], 'Flock Transactions', r)
    assert not report.ready_rows and len(report.rejected_rows) == 3


class _FailingAudit:
    def record_action(self, *args, **kwargs):
        raise RuntimeError('audit store unavailable')


def test_A_D8_secondary_audit_failure_does_not_raise_or_duplicate(chain):
    r, a, o, f, q, flock, record = chain
    repo = AuthorizedRepository(r, _FailingAudit(), EDITOR)
    entry = dict(FLOCK_ID=flock, TRANSACTION_TYPE='Delivery', QUANTITY=500, TRANSACTION_DATE=dt.date(2026, 10, 1))
    repo.upsert_flock_transaction(dict(entry))
    assert len(r.get_flock_transactions(flock_id=flock)) == 1 and repo.last_audit_warning


def test_A_D9_after_concurrent_count_reload_then_reconfirm_applies(chain, tmp_path, monkeypatch):
    r, a, o, f, q, flock, record = chain
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/6_Flock_Transactions.py', None, view='new')
    app.selectbox(key='flock_tx_form_type').select('Count').run()
    r.record_current_flock_quantity(dict(FLOCK_ID=flock, TRANSACTION_TYPE='Count', QUANTITY=8, TRANSACTION_DATE=halifax_today()),
                                    'other-user', r.get_flock(flock)['UPDATED_AT'], 'other count', confirmed=True, actor=ACTOR,
                                    expected_bird_count=10)
    app.number_input(key='flock_tx_form_quantity').set_value(7)
    app.checkbox(key='flock_tx_form_apply_' + flock).check()
    app.text_input(key='flock_tx_form_quantity_reason').input('my count')
    app.button(key='flock_tx_record_save').click().run()
    assert any('changed' in m.lower() for m in _msgs(app)) and r.get_flock(flock)['BIRD_COUNT'] == 8
    app.button(key='flock_tx_form_reload_quantity').click().run()
    app.checkbox(key='flock_tx_form_apply_' + flock).check()
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error, _msgs(app)
    assert r.get_flock(flock)['BIRD_COUNT'] == 7


def test_A_D10_account_with_production_cannot_be_deleted(chain):
    r, a, o, f, q, flock, record = chain
    r.create_manual_production(dict(PRODUCER_ACCOUNT_ID=o, REPORTING_YEAR=2026, REPORTING_WEEK=40, TOTAL=Decimal('10')), 'p', actor=ACTOR)
    with pytest.raises((RepositoryError, ValueError)):
        r.delete_account(o)
    assert r.get_account(o) is not None


@pytest.mark.parametrize('dataset, filters', [
    ('Accounts', {'account_id': 'X'}),
    ('Facilities', {'facility_id': 'X'}),
    ('Quota Registrations', {'date_from': dt.date(2030, 1, 1), 'date_to': dt.date(2030, 12, 31)}),
])
def test_A_D11_unsupported_filters_rejected(chain, dataset, filters):
    r, *_ = chain
    key = {'Accounts': 'ACCOUNT_ID', 'Facilities': 'FACILITY_ID', 'Quota Registrations': 'QUOTA_ID'}[dataset]
    with pytest.raises(ValueError):
        build_custom_report(r, user=report_user(), dataset=dataset, selected_fields=[key], filters=filters)


# ======================= Part B: new scenarios =================================
def test_B1_second_edit_in_same_session_succeeds(chain, tmp_path, monkeypatch):
    """Edit -> save -> Edit again -> save: both changes must land, no stale-version block."""
    r, a, o, f, q, flock, record = chain
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/5_Flocks.py', flock)
    app.text_area(key='flock_form_comments').input('one')
    app.text_input(key='flock_form_revision_reason').input('first')
    app.button(key='flock_record_save').click().run()
    assert not app.error and r.get_flock(flock)['COMMENTS'] == 'one'
    app.button(key='flock_record_edit').click().run()
    app.text_area(key='flock_form_comments').input('two')
    app.text_input(key='flock_form_revision_reason').input('second')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not _msgs(app), _msgs(app)
    assert r.get_flock(flock)['COMMENTS'] == 'two'


def test_B2_two_identical_legitimate_transactions_via_new(chain, tmp_path, monkeypatch):
    """Two real, identical Deliveries entered one after another through New must both be saved."""
    r, a, o, f, q, flock, record = chain
    app = _app(r, tmp_path, monkeypatch)
    for _ in range(2):
        app = _open(app, 'app/pages/6_Flock_Transactions.py', None, view='list')
        app.button(key='flock_tx_list_new').click().run()
        app.selectbox(key='flock_tx_form_type').select('Delivery').run()
        app.number_input(key='flock_tx_form_quantity').set_value(500)
        app.date_input(key='flock_tx_form_date').set_value(dt.date(2026, 10, 1))
        app.button(key='flock_tx_record_save').click().run()
        assert not app.exception and not app.error, _msgs(app)
    assert len(r.get_flock_transactions(flock_id=flock)) == 2


def test_B3_record_page_delete_requires_reason_and_keeps_before_image(chain, tmp_path, monkeypatch):
    r, a, o, f, q, flock, record = chain
    tx = r.upsert_flock_transaction(dict(FLOCK_ID=flock, TRANSACTION_TYPE='Delivery', QUANTITY=5, TRANSACTION_DATE=dt.date(2026, 9, 1)))
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/6_Flock_Transactions.py', tx, view='detail')
    app.button(key='flock_tx_record_delete').click().run()
    assert len(r.get_flock_transactions(flock_id=flock)) == 1          # nothing deleted before confirmation
    app.text_input(key='flock_tx_form___delete_reason').input('Entered against wrong flock')
    app.checkbox(key='flock_tx_form___delete_confirmed').check()
    app.button(key='flock_tx_form___delete_confirm').click().run()
    assert not app.exception, _msgs(app)
    assert r.get_flock_transactions(flock_id=flock).empty
    rev = r.get_record_revisions()
    deleted = rev[(rev.ENTITY_ID == tx) & (rev.CHANGE_KIND == 'DELETE')]
    assert len(deleted) == 1 and deleted.iloc[0].BEFORE_DATA['QUANTITY'] == 5


def test_B4_account_relationship_display_and_navigation_preserved(chain, tmp_path, monkeypatch):
    r, a, o, f, q, flock, record = chain
    _set(r, '_accounts', 'ACCOUNT_ID', a, GRADING_STATION_ACCOUNT_ID=o, PULLET_GROWER_ACCOUNT_ID=o)
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/3_Accounts_Facilities_Flocks.py', a, view='detail')
    assert not app.exception
    labels = [b.label for b in app.button]
    assert 'Open Grading Station' in labels and 'Open Pullet Grower Account' in labels
    next(b for b in app.button if b.label == 'Open Grading Station').click().run()
    assert app.session_state['_efns_record_3_Accounts_Facilities_Flocks_id'] == o


def test_B5_account_edit_keeps_relationship_links_when_untouched(chain, tmp_path, monkeypatch):
    r, a, o, f, q, flock, record = chain
    _set(r, '_accounts', 'ACCOUNT_ID', a, GRADING_STATION_ACCOUNT_ID=o, PULLET_GROWER_ACCOUNT_ID=o, PROVINCE_OF_REGISTRATION=None)
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/3_Accounts_Facilities_Flocks.py', a)
    assert not app.exception
    app.text_area(key='account_form_description').input('note')
    reason = [t for t in app.text_input if 'reason' in (t.key or '').lower()]
    if reason:
        reason[0].input('desc')
    app.button(key='account_record_save').click().run()
    assert not app.exception and not app.error, _msgs(app)
    after = r.get_account(a)
    assert after['DESCRIPTION'] == 'note'
    assert after['GRADING_STATION_ACCOUNT_ID'] == o and after['PULLET_GROWER_ACCOUNT_ID'] == o
    assert pd.isna(after['PROVINCE_OF_REGISTRATION'])


def test_B6_reload_without_reconfirm_does_not_silently_save_plain_activity(chain, tmp_path, monkeypatch):
    """After 'Reload reviewed Bird Count' the apply box is cleared. If the user then presses Save,
    the page should not silently create an unapplied Count activity that looks like success."""
    r, a, o, f, q, flock, record = chain
    app = _open(_app(r, tmp_path, monkeypatch), 'app/pages/6_Flock_Transactions.py', None, view='new')
    app.selectbox(key='flock_tx_form_type').select('Count').run()
    r.record_current_flock_quantity(dict(FLOCK_ID=flock, TRANSACTION_TYPE='Count', QUANTITY=8, TRANSACTION_DATE=halifax_today()),
                                    'other', r.get_flock(flock)['UPDATED_AT'], 'other', confirmed=True, actor=ACTOR, expected_bird_count=10)
    app.number_input(key='flock_tx_form_quantity').set_value(7)
    app.checkbox(key='flock_tx_form_apply_' + flock).check()
    app.text_input(key='flock_tx_form_quantity_reason').input('my count')
    app.button(key='flock_tx_record_save').click().run()
    app.button(key='flock_tx_form_reload_quantity').click().run()
    before = len(r.get_flock_transactions(flock_id=flock))
    app.button(key='flock_tx_record_save').click().run()     # user forgets to re-tick
    created = len(r.get_flock_transactions(flock_id=flock)) - before
    assert created == 0 and _msgs(app), ('plain Count activity saved silently', created)


def test_B7_snowflake_alias_list_queries_keep_ff9_versions():
    """Aliased edit baselines and single-record reads use the same lossless FF9 projection."""
    from data.repositories.snowflake import SnowflakeRepository
    seen = []

    class Exec:
        runtime_name = 'fake'
        def query(self, sql, params=None):
            seen.append(sql)
            return pd.DataFrame()
    repo = SnowflakeRepository(Exec())
    repo.get_flock_transactions()
    repo.get_salmonella_tests()
    repo.get_flock('x')
    assert 'FF9' in seen[2]
    assert all('FF9' in sql for sql in seen[:2])   # corrected version projection


def test_B8_daily_created_flock_without_detail_can_later_be_updated(chain):
    """Mock path: a Flock created by Daily Import with no Facility Detail column, then updated by Daily Import."""
    r, a, o, f, q, flock, record = chain
    from tests.test_operational_review_persistence import prepare
    row = {'Flock Number': 'DAILY-NEW-1', 'Account': a, 'Facility': f, 'Permit Number': 'DP-1',
           'Hatch Date': '2026-08-01', 'Bird Count': '100'}
    up = csv_upload('create.csv', [row])
    batch, staged, _ = prepare(r, up)
    r.commit_staged_operational(batch, staged.records_by_entity, actor='staff')
    created = r.get_flocks()[r.get_flocks().FLOCK_NUMBER == 'DAILY-NEW-1'].iloc[0]
    up2 = csv_upload('update.csv', [{'Flock Number': 'DAILY-NEW-1', 'Account': a, 'Comments': 'later note'}])
    preview = analyze_operational_files([up2], 'Flocks', r)
    assert len(preview.ready_rows) == 1
    batch2, staged2, _ = prepare(r, up2)
    r.commit_staged_operational(batch2, staged2.records_by_entity, actor='staff')
    assert r.get_flock(created.FLOCK_ID)['COMMENTS'] == 'later note'


def test_C_B2_count_after_end_still_accepted_pending_business_rule(chain):
    """Not a defect: documents that B2 is still open (Count accepted after END; ended Flock still summed)."""
    from app.services.quota_usage import account_usage_context
    r, a, o, f, q, flock, record = chain
    r.record_flock_event(flock, 'INITIAL_POSITION', dt.datetime(2026, 1, 2, 12, tzinfo=ZoneInfo('America/Halifax')),
                         'placement evidence', 'init', to_facility_id=f, actor='staff', position_confirmed=True)
    r.record_flock_event(flock, 'END', dt.datetime(2026, 9, 30, 12, tzinfo=ZoneInfo('America/Halifax')),
                         'shipped', 'end', actor='staff')
    r.record_current_flock_quantity(dict(FLOCK_ID=flock, TRANSACTION_TYPE='Count', QUANTITY=500, TRANSACTION_DATE=halifax_today()),
                                    'after-end', r.get_flock(flock)['UPDATED_AT'], 'count', confirmed=True, actor=ACTOR,
                                    expected_bird_count=10)
    assert r.get_flock(flock)['BIRD_COUNT'] == 500
    assert account_usage_context(r, a)['summaries'][0]['known_bird_count'] == 500
