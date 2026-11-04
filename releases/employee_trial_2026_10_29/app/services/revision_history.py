"""Pure, display-only projection of selected record revisions; no repository I/O."""
import json
import pandas as pd

COLUMNS = ['Changed at (America/Halifax)', 'Changed by', 'Change type', 'Reason',
           'Field', 'Old value', 'New value']
IGNORED = {'UPDATED_AT', 'CREATED_AT', 'UPDATED_BY', 'CREATED_BY'}


def _null(value):
    if isinstance(value, (dict, list, tuple)):
        return False
    try:
        return value is None or bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _snapshot(value):
    if _null(value):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            raise ValueError('A recorded change snapshot is not valid JSON.') from None
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError('A recorded change snapshot must be a JSON object or NULL.')
    return value


def _same(old, new):
    if _null(old) or _null(new):
        return _null(old) and _null(new)
    if isinstance(old, bool) != isinstance(new, bool):
        return False
    try:
        return bool(old == new)
    except (ValueError, TypeError):
        return False


def _display(value):
    if _null(value):
        return '—'
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return str(value)


def revision_actor_labels(df, user_lookup):
    """Resolve only actor IDs present in this bounded revision frame."""
    labels = {}
    if 'RECORDED_BY' not in df:
        return labels
    for value in df['RECORDED_BY'].tolist():
        if _null(value):
            continue
        actor_id = str(value).strip()
        if not actor_id or actor_id in labels:
            continue
        user = user_lookup(actor_id)
        if user is None:
            labels[actor_id] = actor_id
            continue
        labels[actor_id] = (str(getattr(user, 'display_name', '') or '').strip()
                            or str(getattr(user, 'email', '') or '').strip()
                            or actor_id)
    return labels


def _short_id(value):
    return str(value or '')[:8].upper()


def _label_parts(*values):
    return [str(value).strip() for value in values if not _null(value) and str(value).strip()]


def record_option_label(entity_type, row, id_column, quota_numbers=None):
    """Build a compact staff-facing label while retaining the full ID as value."""
    identity = row[id_column]
    short = _short_id(identity)
    quota_numbers = quota_numbers or {}
    fields = {
        'ACCOUNT': (row.get('ORGANIZATION_NAME'), row.get('REGISTRATION_NUMBER'), short),
        'FACILITY': (row.get('FACILITY_NAME'), row.get('FACILITY_TYPE'), short),
        'FACILITY_DETAIL': (row.get('DETAIL_NAME'), row.get('DETAIL_TYPE'), short),
        'FLOCK': (row.get('FLOCK_NUMBER'), row.get('PERMIT_NUMBER'), short),
        'FLOCK_TRANSACTION': (row.get('TRANSACTION_TYPE'), short,
                              row.get('TRANSACTION_DATE'), row.get('QUANTITY')),
        'QUOTA_REGISTRATION': (row.get('QUOTA_NAME'), row.get('REGISTRATION_NUMBER'), short),
        'QUOTA_TRANSACTION': (row.get('TRANSACTION_TYPE'), short, row.get('EFFECTIVE_DATE'),
                              quota_numbers.get(str(row.get('QUOTA_ID')))),
        'SALMONELLA_TEST': (row.get('TEST_RESULT') or row.get('TEST_TYPE'), short,
                            row.get('TESTING_DATE'), row.get('PERMIT_NUMBER')),
        'PRODUCTION_RECORD': (row.get('PRODUCER_NUMBER'), short,
                              row.get('REPORTING_YEAR'), row.get('REPORTING_WEEK')),
    }
    parts = _label_parts(*fields.get(entity_type, (short,)))
    return ' · '.join(parts) if parts else short


def record_options(entity_type, candidates, id_column, quota_numbers=None):
    """Map unique display labels to complete record IDs."""
    options = {}
    for row in candidates.to_dict('records'):
        identity = str(row[id_column])
        label = record_option_label(entity_type, row, id_column, quota_numbers)
        if label in options and options[label] != identity:
            label = f'{label} · {identity}'
        options[label] = identity
    return options


def revision_changes(df, actor_labels=None):
    """Flatten business-field changes; never return raw VARIANT snapshots.

    Revision writers store UTC RECORDED_AT (including naive UTC NTZ values).
    The display explicitly converts that instant to America/Halifax, with its
    seasonal UTC offset. No historical business date is recalculated.
    """
    rows = []
    for revision in df.to_dict('records'):
        before, after = (_snapshot(revision.get(key)) for key in ('BEFORE_DATA', 'AFTER_DATA'))
        stamp = pd.to_datetime(revision.get('RECORDED_AT'), utc=True, errors='coerce')
        actor = revision.get('RECORDED_BY')
        actor_key = None if _null(actor) else str(actor).strip()
        context = dict(zip(COLUMNS[:4], [
            stamp.tz_convert('America/Halifax').isoformat() if pd.notna(stamp) else '—',
            _display((actor_labels or {}).get(actor_key, actor)), _display(revision.get('CHANGE_KIND')),
            _display(revision.get('REASON'))]))
        fields = [key for key in sorted(before.keys() | after.keys())
                  if key.upper() not in IGNORED and not key.startswith('_')
                  and not _same(before.get(key), after.get(key))]
        if fields:
            rows.extend(dict(context, Field=key, **{'Old value': _display(before.get(key)),
                                                   'New value': _display(after.get(key))}) for key in fields)
        else:
            rows.append(dict(context, Field='—', **{'Old value': '—', 'New value': '—'}))
    return pd.DataFrame(rows, columns=COLUMNS)
