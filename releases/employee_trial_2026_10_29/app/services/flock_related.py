"""Read-only linked Quota presentation for the Flock detail view."""
from dataclasses import dataclass

from app.security import AuthorizationError
from data.producer_identity import text


@dataclass(frozen=True)
class FlockQuotaLink:
    quota_id: str | None
    label: str
    flock_quota_type: str
    can_open: bool = False
    note: str | None = None


def flock_quota_link(repo, flock, *, can_view=True):
    """Resolve only the stored quota, using the Quota page's title precedence.

    The flock's own type is displayed independently of the registration type.
    Missing relationships never trigger an all-registrations lookup.
    """
    kind = text(flock.get('FLOCK_QUOTA_TYPE')) or '—'
    if not can_view:
        return FlockQuotaLink(None, '—', kind, note='Quota details are not available for your role.')
    quota_id = text(flock.get('QUOTA_ID'))
    if not quota_id:
        return FlockQuotaLink(None, '—', kind)
    try:
        quota = repo.get_quota_registration(quota_id)
    except AuthorizationError:
        return FlockQuotaLink(None, '—', kind, note='Quota details are not available for your role.')
    if quota is None:
        return FlockQuotaLink(quota_id, quota_id, kind, note='Quota Registration not found.')
    label = text(quota.get('QUOTA_NAME')) or text(quota.get('REGISTRATION_NUMBER')) or 'Quota Registration'
    return FlockQuotaLink(quota_id, label, kind, can_open=True)
