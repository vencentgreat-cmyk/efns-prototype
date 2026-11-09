"""Read/validation compatibility for confirmed quota labels; never rewrite rows."""
from data.producer_identity import text


ALIASES = {
    'Egg Production': 'Egg Production',
    'Non Commercial Pullet Quota': 'Non Commercial Pullet Quota',
    'Non-Commercial Pullet': 'Non Commercial Pullet Quota',
    'Commercial Pullet Grower': 'Commercial Pullet Grower',
    'Commercial Pullet': 'Commercial Pullet Grower',
}


def quota_type_key(value):
    label = text(value)
    return ALIASES.get(label, label)


def quota_type_filter(value):
    """One bound value or the exact recognized legacy/canonical aliases."""
    canonical = quota_type_key(value)
    matches = tuple(label for label, target in ALIASES.items() if target == canonical)
    return matches if len(matches) > 1 else canonical


def supported_quota_type(value):
    return text(value) in ALIASES
