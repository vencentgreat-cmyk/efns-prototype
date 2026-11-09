"""Finite manual relationship corrections; never change source identity."""
import json

FIELDS = {
    "FLOCK": ("ACCOUNT_ID", "FACILITY_ID"),
    "FLOCK_TRANSACTION": ("FLOCK_ID",),
    "QUOTA_TRANSACTION": ("QUOTA_ID",),
}


def validated_changes(entity, changes):
    if entity not in FIELDS or not isinstance(changes, dict) or not changes:
        raise ValueError("Select a supported relationship correction.")
    if set(changes) - set(FIELDS[entity]):
        raise ValueError("Only the displayed relationship fields may be corrected; target IDs and Owner cannot be edited.")
    result = {}
    for field, value in changes.items():
        if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 36):
            raise ValueError(f"{field} must be an existing record identifier or an explicit empty relationship.")
        result[field] = value.strip() if value is not None else None
    return result


def decision_json(value):
    return json.dumps(value, default=str, sort_keys=True)
