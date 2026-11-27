"""Explicit two-step disposal entry; ordinary edits never replace lifecycle history."""
import datetime as dt
import uuid
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from app.services.form_safety import preserve_form, save_form
from data.business_time import halifax_today
from data.repositories.base import RepositoryError
from data.repositories.continuity import changed_attributes
from data.source_evidence import evidence_json


class DisposalEventSaveError(RepositoryError):
    """The ordinary save completed, but the requested disposal event did not."""


def save_flock_edit(repo, record, current, reason, *, actor, prefix='flock_form_'):
    record = preserve_form(record, current, prefix)
    baseline = st.session_state[prefix+'__review']['original']
    changes = changed_attributes(baseline, record)
    if 'DISPOSAL_DATE' not in changes:
        repo.check_flock_reference_change(record)
        return save_form(repo, 'FLOCK', record, current, prefix, reason)

    value = record.get('DISPOSAL_DATE')
    if value is None or pd.isna(value):
        raise RepositoryError('Clearing Disposal Date is not supported here. Use Record Review & History to correct the actual end event.')
    try:
        day = pd.Timestamp(value).date()
    except (TypeError, ValueError, OverflowError) as exc:
        raise RepositoryError('Disposal Date must be a valid date.') from exc
    if day > halifax_today():
        raise RepositoryError('Disposal Date cannot be in the future (America/Halifax).')
    if not str(reason or '').strip():
        raise RepositoryError('A reason for the correction is required.')

    ordinary = {key: value for key, value in record.items() if key != 'DISPOSAL_DATE'}
    repo.check_flock_reference_change(ordinary)  # Preserve the existing Facility movement guard.
    fingerprint = evidence_json(dict(record=ordinary, disposal_date=day, reason=reason, actor=actor))
    pending_key = prefix+'disposal_pending'
    pending = st.session_state.get(pending_key)
    if pending and pending['fingerprint'] != fingerprint and pending['fields_saved']:
        raise RepositoryError('A disposal save is partly complete. Retry the same values, or cancel and reopen the Flock to review the saved fields before making a different correction.')
    if not pending or pending['fingerprint'] != fingerprint:
        history = repo.get_flock_events(current['FLOCK_ID'])
        active = history[~history.EVENT_ID.isin(set(history.SUPERSEDES_EVENT_ID.dropna()))] if not history.empty else history
        ends = active[active.EVENT_TYPE.eq('END')] if not active.empty else active
        if len(ends) > 1:
            raise RepositoryError('More than one active end event exists. Review Record Review & History before saving.')
        pending = dict(fingerprint=fingerprint, request_id=uuid.uuid4().hex,
                       supersedes=ends.iloc[0].EVENT_ID if len(ends) else None,
                       fields_saved=False, event_saved=False,
                       fields=sorted(set(changed_attributes(baseline, ordinary)) - {'FLOCK_ID'}))
        st.session_state[pending_key] = pending
    if pending['event_saved']:
        return current['FLOCK_ID']
    if not pending['fields_saved']:
        save_form(repo, 'FLOCK', ordinary, current, prefix, reason)
        pending['fields_saved'] = True
    try:
        refreshed = repo.get_flock(current['FLOCK_ID'])
        if not refreshed:
            raise RepositoryError('The saved Flock could not be re-read. Reload before retrying the disposal event.')
        repo.record_flock_event(current['FLOCK_ID'], 'END',
            dt.datetime.combine(day, dt.time(12, 0), ZoneInfo('America/Halifax')),
            reason, pending['request_id'], supersedes_event_id=pending['supersedes'], actor=actor)
    except Exception as exc:
        saved = 'Saved field changes: '+', '.join(pending['fields'])+'.' if pending['fields'] else 'No ordinary field changes were needed.'
        raise DisposalEventSaveError(saved+' Disposal Date/event save was NOT confirmed. Retry the same save or review Record Review & History; do not start a new request blindly. '+str(exc)) from exc
    pending['event_saved'] = True
    return current['FLOCK_ID']
