"""Read-only, ID-scoped RAW state projection using the existing query interface."""
import json
import logging

from app.security import Permission, require_permission
from data.position_evidence import guid


def get_inactive_quota_transaction_ids(repo, transaction_ids, *, user):
    """Return a verified inactive set, or None if evidence cannot be established.

    Mock has no migrated state: return an empty set. A successful RAW lookup
    with no matching row means a newly created Active transaction per policy.
    No original RAW payloads are loaded or returned to the browser.
    """
    require_permission(user, Permission.VIEW_DATA)
    require_permission(user, Permission.VIEW_REPORTS)
    ids = sorted({value.upper() for value in map(guid, transaction_ids) if value})
    if not ids or repo._is_memory:
        return set()
    try:
        rows = repo._query(
            'SELECT UPPER(TARGET_ID) AS TRANSACTION_ID, '
            'LOWER(TRIM(RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) AS TRANSACTION_STATE '
            f"FROM {repo._table('MIGRATION_RAW_ROW', repo.schema_raw)} "
            'WHERE SOURCE_ENTITY=%s AND UPPER(TARGET_ID) IN '
            '(SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))',
            ('QUOTA_TRANSACTION', json.dumps(ids)))
        states = {}
        for row in rows.to_dict('records'):
            identity = guid(row.get('TRANSACTION_ID'))
            state = guid(row.get('TRANSACTION_STATE'))
            if identity is None or identity.upper() not in ids or state not in {'active', 'inactive'}:
                return None
            states.setdefault(identity, set()).add(state)
        if any(len(values) != 1 for values in states.values()):
            return None
        return {identity for identity, values in states.items() if values == {'inactive'}}
    except Exception as exc:
        logging.getLogger(__name__).warning('Quota state evidence unavailable (%s).', type(exc).__name__)
        return None
