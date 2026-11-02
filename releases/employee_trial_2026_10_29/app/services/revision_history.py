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


def revision_changes(df):
    """Flatten business-field changes; never return raw VARIANT snapshots.

    Revision writers store UTC RECORDED_AT (including naive UTC NTZ values).
    The display explicitly converts that instant to America/Halifax, with its
    seasonal UTC offset. No historical business date is recalculated.
    """
    rows = []
    for revision in df.to_dict('records'):
        before, after = (_snapshot(revision.get(key)) for key in ('BEFORE_DATA', 'AFTER_DATA'))
        stamp = pd.to_datetime(revision.get('RECORDED_AT'), utc=True, errors='coerce')
        context = dict(zip(COLUMNS[:4], [
            stamp.tz_convert('America/Halifax').isoformat() if pd.notna(stamp) else '—',
            _display(revision.get('RECORDED_BY')), _display(revision.get('CHANGE_KIND')),
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
