"""Account lookups: GUID evidence, review candidates and optional saved links.

Legacy SPENT_FOWL_PLANS text is retained separately. This module does not
write migrations or silently promote a display-name candidate to a GUID.
"""
from uuid import UUID
from data.producer_identity import text
from data.repositories.base import RepositoryError

FIELD = 'SPENT_FOWL_PLANS_ACCOUNT_ID'


def account_link_options(accounts, current_id=None):
    options = {'Not selected': None}
    for row in accounts.to_dict('records'):
        aid = text(row.get('ACCOUNT_ID'))
        if aid:
            options[f"{row.get('ORGANIZATION_NAME') or 'Unnamed Account'} · {aid}"] = aid
    value = text(current_id)
    if value and value not in options.values():
        options[f'Unavailable linked Account · {value}'] = value
    return options


def validate_spent_fowl_link(repo, record):
    from data.validation import normalize_optional_account_links
    result = normalize_optional_account_links(record)
    if FIELD not in result or result[FIELD] is None:
        return result
    value = str(result[FIELD]).strip()
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise RepositoryError('Spent Fowl Plans must use an existing Account ID, not a name.') from exc
    if repo.get_account(value) is None:
        raise RepositoryError('Spent Fowl Plans must reference an existing Account.')
    result[FIELD] = value
    return result


def resolve_spent_fowl_source(source, accounts):
    """Resolve original lookup GUID; labels can only suggest review candidates.

    A blank source is NO_CHANGE, never an instruction to clear a stored link.
    All writes still require original-source review plus the normal FF9 CAS,
    authenticated actor, reason and transactional revision/audit path.
    """
    raw = {str(k).casefold(): v for k, v in source.items()}
    original = text(raw.get('efns_spentfowlplans'))
    label = text(raw.get('efns_spentfowlplansname'))
    by_id = {str(r['ACCOUNT_ID']).strip().casefold(): r for r in accounts.to_dict('records')}
    if original:
        try:
            UUID(original)
        except ValueError:
            return dict(status='INVALID_SOURCE_ID', target_id=None, candidates=[])
        target = by_id.get(original.casefold())
        if target is None:
            return dict(status='MISSING_TARGET', target_id=None, candidates=[], original_guid=original)
        if label and (text(target.get('ORGANIZATION_NAME')) or '').casefold() != label.casefold():
            return dict(status='GUID_LABEL_CONFLICT', target_id=None,
                        candidates=[target['ACCOUNT_ID']], original_guid=original)
        return dict(status='SOURCE_GUID', target_id=target['ACCOUNT_ID'], candidates=[], original_guid=original)
    if not label:
        return dict(status='NO_CHANGE', target_id=None, candidates=[])
    candidates = [r['ACCOUNT_ID'] for r in by_id.values()
                  if (text(r.get('ORGANIZATION_NAME')) or '').casefold() == label.casefold()]
    return dict(status='NAME_CANDIDATE_REVIEW_ONLY', target_id=None, candidates=candidates)
