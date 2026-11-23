"""Manual quota entry boundaries; historical bulk writers remain separate."""
from data.producer_identity import text
from data.quota_leases import is_lease
from data.repositories.base import RepositoryError

LEGACY_LEASE_TYPES = frozenset({'lease (in)', 'lease (out)', 'lease in', 'lease out'})
MANUAL_LEASE_MESSAGE = 'New leases must use Method = Lease. Legacy Lease (In)/(Out) rows cannot be created as an Allocation.'


def allocation_types(options, editing=False):
    return list(options) if editing else [value for value in options
        if (text(value) or '').casefold() not in LEGACY_LEASE_TYPES]


def reject_new_allocation_lease(record, before=None):
    if before is None and not is_lease(record) and (text(record.get('TRANSACTION_TYPE')) or '').casefold() in LEGACY_LEASE_TYPES:
        raise RepositoryError(MANUAL_LEASE_MESSAGE)


def manual_upsert(repo, record, method, *args, **kwargs):
    """Authorized direct manual upserts join the same boundary as form creation."""
    from data.record_safety import read_record
    with repo._continuity_transaction() as tx:
        identity = record.get('QUOTA_TRANSACTION_ID')
        before = read_record(repo, 'QUOTA_TRANSACTION', identity, tx) if identity else None
        reject_new_allocation_lease(record, before)
        from data.quota_allocation_capacity import guard_allocation_change
        guard_allocation_change(repo,tx,before,dict(before or {},**record))
        return method(record, *args, **kwargs)
