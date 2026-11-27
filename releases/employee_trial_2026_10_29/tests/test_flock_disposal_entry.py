"""Synthetic disposal-form acceptance; no Snowflake access."""
import datetime as dt
import pandas as pd
import pytest

from tests.test_staff_workflows import chain
from tests.test_review_findings import editing
from data.repositories.base import RepositoryError


def disposal_form(chain, tmp_path, monkeypatch):
    repo, account, other, facility, quota, flock, record = chain
    repo._flocks = repo._flocks.astype(object)
    repo._flocks.loc[repo._flocks.FLOCK_ID.eq(flock), 'BIRD_COUNT'] = 2000
    app = editing(repo, '5_Flocks.py', '5_Flocks', 'flock', flock, tmp_path, monkeypatch)
    app.date_input(key='flock_form_disposal').set_value(dt.date(2026, 11, 21))
    app.text_input(key='flock_form_disposed_text').input('1901')
    app.text_input(key='flock_form_revision_reason').input('disposal entry')
    return repo, flock, app


def test_one_save_corrects_quantity_and_records_one_actual_end(chain, tmp_path, monkeypatch):
    repo, flock, app = disposal_form(chain, tmp_path, monkeypatch)
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    saved = repo.get_flock(flock)
    assert pd.Timestamp(saved['DISPOSAL_DATE']).date() == dt.date(2026, 11, 21)
    assert saved['BIRDS_DISPOSED'] == 1901 and saved['BIRD_COUNT'] == 2000
    assert saved['STATUS'] == 'Active'
    events = repo.get_flock_events(flock)
    assert len(events) == 1 and events.iloc[0].EVENT_TYPE == 'END'
    assert pd.Timestamp(events.iloc[0].EFFECTIVE_AT).hour == 16  # noon Halifax in November
    revisions = repo.get_record_revisions_for('FLOCK', flock)
    assert len(revisions) == 1 and revisions.iloc[0].CHANGE_KIND == 'QUANTITY_CORRECTION'
    assert revisions.iloc[0].REASON == 'disposal entry'
    assert pd.isna(revisions.iloc[0].AFTER_DATA.get('DISPOSAL_DATE'))
    assert repo._migration_review_audit
    assert app.session_state['flock_form_disposal_pending']['event_saved']


def test_changed_date_supersedes_active_end(chain, tmp_path, monkeypatch):
    repo, flock, app = disposal_form(chain, tmp_path, monkeypatch)
    first = repo.record_flock_event(flock, 'END', dt.datetime(2026, 11, 20, 16, tzinfo=dt.timezone.utc),
                                   'prior disposal', 'prior-end', actor='user-a')
    # Reopen so the ordinary correction sees the latest stored version.
    app = editing(repo, '5_Flocks.py', '5_Flocks', 'flock', flock, tmp_path, monkeypatch)
    app.date_input(key='flock_form_disposal').set_value(dt.date(2026, 11, 21))
    app.text_input(key='flock_form_revision_reason').input('correct date')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    events = repo.get_flock_events(flock)
    assert len(events) == 2
    assert events.iloc[-1].SUPERSEDES_EVENT_ID == first


@pytest.mark.parametrize('mode', ['future', 'clear', 'facility'])
def test_invalid_disposal_or_movement_is_rejected_before_any_write(mode, chain, tmp_path, monkeypatch):
    repo, flock, app = disposal_form(chain, tmp_path, monkeypatch)
    if mode == 'future':
        from data.business_time import halifax_today
        app.date_input(key='flock_form_disposal').set_value(halifax_today() + dt.timedelta(days=1))
    elif mode == 'clear':
        repo._flocks.loc[repo._flocks.FLOCK_ID.eq(flock), 'DISPOSAL_DATE'] = dt.date(2026, 11, 20)
        app = editing(repo, '5_Flocks.py', '5_Flocks', 'flock', flock, tmp_path, monkeypatch)
        app.date_input(key='flock_form_disposal').set_value(None)
        app.text_input(key='flock_form_revision_reason').input('clear date')
    else:
        app.selectbox(key='flock_form_facility').select('Unassigned')
    before = repo.get_flock(flock)
    app.button(key='flock_record_save').click().run()
    assert not app.exception and app.error
    assert repo.get_flock_events(flock).empty and repo.get_record_revisions_for('FLOCK', flock).empty
    pd.testing.assert_series_equal(pd.Series(repo.get_flock(flock)), pd.Series(before))


def test_partial_event_failure_has_no_overall_success_and_retries_once(chain, tmp_path, monkeypatch):
    repo, flock, app = disposal_form(chain, tmp_path, monkeypatch)
    original = repo.record_flock_event
    attempts = []
    def fail(*args, **kwargs):
        attempts.append((args, kwargs))
        raise RepositoryError('Use chronological business events; a correction must not invalidate later movements.')
    monkeypatch.setattr(repo, 'record_flock_event', fail)
    app.button(key='flock_record_save').click().run()
    assert not app.exception and app.error and not app.success
    assert 'BIRDS_DISPOSED' in app.error[0].value and 'NOT confirmed' in app.error[0].value
    assert 'Use chronological business events' in app.error[0].value
    assert repo.get_flock(flock)['BIRDS_DISPOSED'] == 1901
    assert pd.isna(repo.get_flock(flock).get('DISPOSAL_DATE'))
    assert len(repo.get_record_revisions_for('FLOCK', flock)) == 1
    request = attempts[0][0][4]
    monkeypatch.setattr(repo, 'record_flock_event', original)
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    assert app.session_state['flock_form_disposal_pending']['request_id'] == request
    assert len(repo.get_flock_events(flock)) == 1
    event = repo.get_flock_events(flock).iloc[0]
    original(flock, 'END', dt.datetime(2026, 11, 21, 16, tzinfo=dt.timezone.utc),
             'disposal entry', request, actor='user-a')
    assert len(repo.get_flock_events(flock)) == 1
