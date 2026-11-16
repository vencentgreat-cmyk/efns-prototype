"""Flock entry choices and page-level duplicate messages; no repository writes."""
import pandas as pd

def permit_text(value):
    """Trim identifiers without reinterpreting literal words as missing values."""
    return '' if value is None or pd.isna(value) else str(value).strip()


def creation_retry_id(record, request=None, initial_request=None):
    """Exclude only this creation request's target; writers still verify replay."""
    from data.repositories.continuity import stable_id
    from data.source_evidence import evidence_json
    if initial_request:
        return stable_id('initial-flock', initial_request)
    if request and request.get('fingerprint') == evidence_json(dict(entity='FLOCK', record=record)):
        return stable_id('record-create', 'FLOCK', request['id'])
    return None


def role_account_names(accounts, role):
    names = {row['ORGANIZATION_NAME'] for row in accounts.to_dict('records')
             if pd.notna(row.get(role)) and row.get(role) == True
             and permit_text(row.get('ORGANIZATION_NAME'))}
    return (None, *sorted(names, key=lambda name: (name.casefold(), name)))


def duplicate_permit_errors(permit, flocks, accounts, facilities, current_id=None):
    """Fresh-read UI guard only: not an atomic/concurrent uniqueness guarantee."""
    wanted = permit_text(permit).casefold()
    if not wanted:
        return []
    owners = {row['ACCOUNT_ID']: row for row in accounts.to_dict('records')}
    barns = {row['FACILITY_ID']: row for row in facilities.to_dict('records')}
    errors = []
    for flock in flocks.to_dict('records'):
        if current_id is not None and str(flock.get('FLOCK_ID')) == str(current_id):
            continue
        if permit_text(flock.get('PERMIT_NUMBER')).casefold() != wanted:
            continue
        owner = owners.get(flock.get('ACCOUNT_ID'), {})
        barn = barns.get(flock.get('FACILITY_ID'), {})
        errors.append(f"Permit Number {permit_text(permit)} is already used by an existing flock: "
            f"Account {permit_text(owner.get('ORGANIZATION_NAME')) or permit_text(flock.get('ACCOUNT_ID')) or '—'} "
            f"(Registration Number {permit_text(owner.get('REGISTRATION_NUMBER')) or '—'}); "
            f"Facility {permit_text(barn.get('FACILITY_NAME')) or permit_text(flock.get('FACILITY_ID')) or '—'}.")
    return errors
