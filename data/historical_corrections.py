"""Confirmed exception handling for rejected historical EIMS rows.

This module never mutates the original migration batch. It rebuilds values from
preserved RAW payloads and classifies each rejected row for a separate,
traceable correction batch.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

import pandas as pd

from data.migration import load_mapping, normalize_migration_row, correction_mapping
from data.migration_identity import scoped_raw_rows


READY_CORE = "READY_CORE"
ALREADY_COMMITTED = "ALREADY_COMMITTED"
PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"


@dataclass
class HistoricalCorrectionPreview:
    batch_id: str
    correction_batch_id: str
    rows: list[dict]
    mapping_revision: str = ""

    @property
    def review_token(self) -> str:
        """Fingerprint the reviewed values, decisions and validation outcome."""
        return hashlib.sha256(json.dumps(dict(mapping_revision=self.mapping_revision, rows=self.rows), default=str, sort_keys=True).encode()).hexdigest()

    @property
    def core_rows(self) -> list[dict]:
        return [row for row in self.rows if row["DISPOSITION"] == READY_CORE]

    @property
    def pending_rows(self) -> list[dict]:
        return [row for row in self.rows if row["DISPOSITION"] == PENDING_CONFIRMATION]

    @property
    def committed_rows(self) -> list[dict]:
        return [row for row in self.rows if row["DISPOSITION"] == ALREADY_COMMITTED]

    @property
    def summary(self) -> pd.DataFrame:
        if not self.rows:
            return pd.DataFrame(columns=["SOURCE_ENTITY", "DISPOSITION", "ROW_COUNT"])
        frame = pd.DataFrame(self.rows)
        return (
            frame.groupby(["SOURCE_ENTITY", "DISPOSITION"], dropna=False)
            .size().rename("ROW_COUNT").reset_index()
            .sort_values(["SOURCE_ENTITY", "DISPOSITION"], ignore_index=True)
        )

    @property
    def review_frame(self) -> pd.DataFrame:
        """Return source, relationship, and business fields for human review."""
        if not self.rows:
            return pd.DataFrame()
        frame = pd.DataFrame(self.rows)
        business = pd.json_normalize(frame["CORRECTED_DATA"].map(_variant))
        business = business.loc[:, [
            column for column in business.columns
            if not business[column].isna().all()
        ]]
        base_columns = [
            "SOURCE_FILENAME", "SOURCE_ENTITY", "SOURCE_ROW_NUMBER",
            "MIGRATION_RAW_ROW_ID", "SOURCE_ID", "TARGET_ID",
            "DISPOSITION", "RELATION_STATUS", "REASON",
            "ORIGINAL_VALIDATION_MESSAGES",
            "CURRENT_VALIDATION_MESSAGES",
        ]
        return pd.concat(
            [frame[base_columns].reset_index(drop=True), business.reset_index(drop=True)],
            axis=1,
        )


def _variant(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return {}
    if isinstance(value, str):
        parsed = json.loads(value)
        return dict(parsed) if isinstance(parsed, dict) else {}
    try:
        if pd.isna(value):
            return {}
    except (TypeError, ValueError):
        pass
    return dict(value)


def _identifier(value) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return None if text.casefold() in {"", "none", "null", "nan", "nat"} else text


def _messages(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return [str(item) for item in parsed] if isinstance(parsed, list) else [str(parsed)]
    return [str(value)]


def _key(value) -> str | None:
    text = _identifier(value)
    return text.casefold() if text else None


def _correction_id(batch_id: str, raw_row_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"efns-eims-correction:{batch_id}:{raw_row_id}"))


def _required_errors(record: dict, required: list[str]) -> list[str]:
    return [f"{field} is required." for field in required if _identifier(record.get(field)) is None]


def build_historical_correction_preview(
    batch_id: str,
    raw_rows: pd.DataFrame | list[dict],
    existing_ids: dict[str, set[str]],
    *,
    quota_accounts: dict[str, str] | None = None,
    mapping: dict | None = None,
    correction_history: list[dict] | None = None,
    correction_batches: list[dict] | None = None,
    manual_decisions: list[dict] | None = None,
    facility_accounts: dict[str, str] | None = None,
) -> HistoricalCorrectionPreview:
    """Apply only confirmed historical exceptions to rejected RAW rows."""
    contract = correction_mapping(mapping or load_mapping())
    source_rows = scoped_raw_rows(batch_id, raw_rows)
    rejected = [row for row in source_rows if str(row.get("VALIDATION_STATUS", "")).upper() == "REJECTED"]
    available = {
        entity: {_key(value) for value in values if _key(value)}
        for entity, values in existing_ids.items()
    }
    quota_owner = {
        _key(quota_id): _identifier(account_id)
        for quota_id, account_id in (quota_accounts or {}).items()
        if _key(quota_id)
    }
    committed_batches = {
        row["MIGRATION_CORRECTION_BATCH_ID"]: row
        for row in (correction_batches or [])
        if str(row.get("STATUS", "")).upper() in {"COMMITTED", "COMMITTED_WITH_PENDING"}
        and _identifier(row.get("COMMITTED_AT")) is not None
        and row.get("ORIGINAL_MIGRATION_BATCH_ID") == batch_id
    }
    committed = {
        str(row["MIGRATION_RAW_ROW_ID"]): row
        for row in (correction_history or [])
        if row.get("MIGRATION_CORRECTION_BATCH_ID") in committed_batches
        and row.get("ORIGINAL_MIGRATION_BATCH_ID") == batch_id
        and row.get("DISPOSITION") == READY_CORE
        and row.get("RELATION_STATUS") == VERIFIED
    }

    rebuilt: dict[str, tuple[dict, list[str]]] = {}
    decisions = {}
    seen_versions = set()
    rejected_ids = {str(row['MIGRATION_RAW_ROW_ID']) for row in rejected}
    for decision in manual_decisions or []:
        if decision.get("ORIGINAL_MIGRATION_BATCH_ID") != batch_id:
            raise ValueError("Manual decision belongs to another migration batch.")
        key = str(decision["MIGRATION_RAW_ROW_ID"])
        if key not in rejected_ids:
            raise ValueError('Manual decision does not resolve to a rejected source row in this batch.')
        version_key=(key,int(decision['VERSION']))
        if version_key in seen_versions:
            raise ValueError('Duplicate manual decision version within the original batch.')
        seen_versions.add(version_key)
        previous = decisions.get(key)
        if previous and int(previous["VERSION"]) == int(decision["VERSION"]):
            raise ValueError("Ambiguous manual decision version; investigate before proceeding.")
        if previous is None or int(previous["VERSION"]) < int(decision["VERSION"]):
            decisions[key] = decision
    for row in rejected:
        entity = str(row["SOURCE_ENTITY"])
        payload = _variant(row.get("RAW_DATA"))
        decision = decisions.get(str(row["MIGRATION_RAW_ROW_ID"]))
        if decision:
            if decision.get("SOURCE_ENTITY") != entity or not str(decision.get("BASIS") or "").strip():
                raise ValueError("Manual decision entity or confirmation basis is invalid.")
            from data.correction_decisions import validated_changes
            for field, value in validated_changes(entity, _variant(decision.get("CHANGES"))).items():
                payload[contract["entities"][entity]["field_map"][field].upper()] = value
        rebuilt[str(row["MIGRATION_RAW_ROW_ID"])] = normalize_migration_row(
            entity,
            payload,
            int(row.get("SOURCE_ROW_NUMBER") or 0),
            contract,
        )

    # Confirmed nullable quota numbers are accepted only in this historical path.
    accepted_quota_rows: set[str] = set()
    for row in rejected:
        if row["SOURCE_ENTITY"] != "QUOTA_REGISTRATION":
            continue
        raw_row_id = str(row["MIGRATION_RAW_ROW_ID"])
        if raw_row_id in committed:
            continue
        record, errors = rebuilt[raw_row_id]
        required = [name for name in contract["entities"]["QUOTA_REGISTRATION"]["required"] if name != "REGISTRATION_NUMBER"]
        errors = [*errors, *_required_errors(record, required)]
        if _key(record.get("ACCOUNT_ID")) not in available.get("ACCOUNT", set()):
            errors.append("ACCOUNT_ID references a missing ACCOUNT.")
        if not errors:
            accepted_quota_rows.add(raw_row_id)
            available.setdefault("QUOTA_REGISTRATION", set()).add(_key(record["QUOTA_ID"]))
            quota_owner[_key(record["QUOTA_ID"])] = _identifier(record.get("ACCOUNT_ID"))

    candidates: dict[str, tuple[dict, list[str]]] = {}
    dispositions: dict[str, tuple[str, str, str]] = {}
    current_errors: dict[str, list[str]] = {}
    for row in rejected:
        raw_row_id = str(row["MIGRATION_RAW_ROW_ID"])
        entity = str(row["SOURCE_ENTITY"])
        record, conversion_errors = rebuilt[raw_row_id]
        spec = contract["entities"][entity]
        errors = list(conversion_errors)
        if raw_row_id in decisions:
            from data.migration import _valid_source_id
            if not _valid_source_id(record.get(spec['id_field']),contract.get('id_policy','guid')):
                errors.append('The original target identifier is invalid; a relationship decision cannot replace it.')
        current_errors[raw_row_id] = errors
        if raw_row_id in committed:
            previous = committed[raw_row_id]
            if (
                previous.get("SOURCE_ENTITY") != entity
                or _key(previous.get("SOURCE_ID")) != _key(row.get("SOURCE_ID"))
                or _key(previous.get("TARGET_ID")) != _key(record.get(spec["id_field"]))
                or (previous.get('DECISION_ID') and (
                    previous.get('DECISION_ID') != decisions.get(raw_row_id,{}).get('DECISION_ID')
                    or int(previous.get('DECISION_VERSION') or 0) != int(decisions.get(raw_row_id,{}).get('VERSION') or 0)
                ))
            ):
                errors.append("Committed correction identifiers do not match the preserved source row; investigate the trace.")
                dispositions[raw_row_id] = (PENDING_CONFIRMATION, UNVERIFIED, errors[-1])
            elif _key(previous.get("TARGET_ID")) in available.get(entity, set()):
                dispositions[raw_row_id] = (
                    ALREADY_COMMITTED, VERIFIED,
                    "Verified committed correction and existing CORE target; excluded from new writes.",
                )
                rebuilt[raw_row_id] = (_variant(previous.get("CORRECTED_DATA")), [])
            else:
                errors.append("A previously committed correction target is missing from CORE; investigate before retrying.")
                dispositions[raw_row_id] = (PENDING_CONFIRMATION, UNVERIFIED, errors[-1])
            continue

        if entity == "QUOTA_REGISTRATION":
            errors.extend(_required_errors(record, [field for field in spec.get("required", ()) if field != "REGISTRATION_NUMBER"]))
            if _key(record.get("ACCOUNT_ID")) not in available.get("ACCOUNT", set()):
                errors.append("ACCOUNT_ID references a missing ACCOUNT.")
            if raw_row_id in accepted_quota_rows:
                dispositions[raw_row_id] = (READY_CORE, VERIFIED, "Confirmed historical quota registration with no business registration number.")
            else:
                dispositions[raw_row_id] = (PENDING_CONFIRMATION, UNVERIFIED, "Quota registration still has validation or parent-reference errors.")
            continue

        if entity == "QUOTA_TRANSACTION":
            quota_id = _key(record.get("QUOTA_ID"))
            if quota_id in quota_owner:
                record["OWNER_ACCOUNT_ID"] = quota_owner[quota_id]
        errors.extend(_required_errors(record, list(spec.get("required", ()))))
        for field, (parent, _parent_key) in spec.get("foreign_keys", {}).items():
            parent_id = _key(record.get(field))
            if parent == entity:
                continue
            if parent_id and parent_id not in available.get(parent, set()):
                errors.append(f"{field} references a missing {parent}.")
        if entity == "FLOCK":
            decision = decisions.get(raw_row_id)
            if decision:
                facility_id = _key(record.get("FACILITY_ID"))
                owners = {_key(key): _key(value) for key,value in (facility_accounts or {}).items()}
                if facility_id and owners.get(facility_id) != _key(record.get("ACCOUNT_ID")):
                    errors.append("FACILITY_ID does not belong to ACCOUNT_ID. Historical ownership changes require separate confirmation; this workflow cannot express them.")
                dispositions[raw_row_id] = ((READY_CORE, VERIFIED, "Saved manual relationship decision passed historical validation.")
                                           if not errors else (PENDING_CONFIRMATION, UNVERIFIED, "Saved decision still has validation errors."))
            else:
                dispositions[raw_row_id] = (
                    PENDING_CONFIRMATION, UNVERIFIED,
                    "Flock and Facility accounts conflict; original references are preserved for business confirmation.",
                )
        elif entity == "SALMONELLA_TEST":
            if _key(record.get("FLOCK_ID")) not in available.get("FLOCK", set()):
                errors.append("FLOCK_ID references a missing FLOCK.")
            if _key(record.get("ACCOUNT_ID")) not in available.get("ACCOUNT", set()):
                errors.append("ACCOUNT_ID references a missing ACCOUNT.")
            dispositions[raw_row_id] = (
                (READY_CORE, VERIFIED, "Historical Salmonella Account may differ from the referenced Flock Account.")
                if not errors else
                (PENDING_CONFIRMATION, UNVERIFIED, "Salmonella test still has validation or missing-reference errors.")
            )
        elif entity == "FLOCK_TRANSACTION":
            if _key(record.get("FLOCK_ID")) not in available.get("FLOCK", set()):
                errors.append("FLOCK_ID is missing or does not resolve to a committed Flock.")
            dispositions[raw_row_id] = (
                (READY_CORE, VERIFIED, "Previously missing Flock reference now resolves.")
                if not errors else
                (PENDING_CONFIRMATION, UNVERIFIED, "Flock relationship is unverified; excluded from inventory calculations.")
            )
        elif entity == "QUOTA_TRANSACTION":
            quota_id = _key(record.get("QUOTA_ID"))
            if quota_id not in available.get("QUOTA_REGISTRATION", set()):
                errors.append("QUOTA_ID is missing or does not resolve to a committed Quota Registration.")
            related_quota = _key(record.get("RELATED_QUOTA_ID"))
            if related_quota and related_quota not in available.get("QUOTA_REGISTRATION", set()):
                errors.append("RELATED_QUOTA_ID does not resolve to a committed Quota Registration.")
            candidates[raw_row_id] = (record, errors)
        else:
            dispositions[raw_row_id] = (
                PENDING_CONFIRMATION, UNVERIFIED,
                "No confirmed historical correction rule applies to this entity.",
            )

    # Resolve quota-transaction self references in dependency order. A child of
    # an unresolved transaction stays pending and is never marked verified.
    resolved_transactions = set(available.get("QUOTA_TRANSACTION", set()))
    pending = set(candidates)
    progressed = True
    while progressed:
        progressed = False
        for raw_row_id in list(pending):
            record, errors = candidates[raw_row_id]
            related = _key(record.get("RELATED_TRANSACTION_ID"))
            if not errors and (related is None or related in resolved_transactions):
                dispositions[raw_row_id] = (READY_CORE, VERIFIED, "Previously rejected quota relationships now resolve.")
                resolved_transactions.add(_key(record.get("QUOTA_TRANSACTION_ID")))
                pending.remove(raw_row_id)
                progressed = True
    for raw_row_id in pending:
        record, errors = candidates[raw_row_id]
        related = _key(record.get("RELATED_TRANSACTION_ID"))
        reason = (
            "Related Quota Transaction remains unverified because its parent transaction is pending."
            if not errors and related not in resolved_transactions
            else "Quota relationship is unverified; excluded from quota calculations."
        )
        if related and related not in resolved_transactions:
            current_errors[raw_row_id].append("RELATED_TRANSACTION_ID references an unresolved QUOTA_TRANSACTION.")
        dispositions[raw_row_id] = (PENDING_CONFIRMATION, UNVERIFIED, reason)

    target_sources = {}
    for row in rejected:
        entity=row['SOURCE_ENTITY']
        row_id=str(row['MIGRATION_RAW_ROW_ID'])
        target=_key(rebuilt[row_id][0].get(contract['entities'][entity]['id_field']))
        if target:
            target_sources.setdefault((entity,target),set()).add(row_id)
    for row_id, (disposition, _relation, _reason) in list(dispositions.items()):
        source_row = next(row for row in rejected if str(row["MIGRATION_RAW_ROW_ID"]) == row_id)
        entity = source_row["SOURCE_ENTITY"]
        target_id = _key(rebuilt[row_id][0].get(contract["entities"][entity]["id_field"]))
        if disposition == READY_CORE and len(target_sources.get((entity,target_id),()))>1:
            reason = 'More than one original source row claims this target GUID; investigate source identity before committing.'
            dispositions[row_id] = (PENDING_CONFIRMATION, UNVERIFIED, reason)
            current_errors[row_id].append(reason)
        if disposition == READY_CORE and target_id in {_key(value) for value in existing_ids.get(entity, set())}:
            reason = "Target GUID already exists without a committed correction trace; verify its values and provenance."
            dispositions[row_id] = (PENDING_CONFIRMATION, UNVERIFIED, reason)
            current_errors[row_id].append(reason)

    correction_batch_id = f"{batch_id}_CORRECTION_1"
    if committed_batches:
        ready_values = [
            (row_id, rebuilt[row_id][0]) for row_id, value in dispositions.items()
            if value[0] == READY_CORE
        ]
        if ready_values:
            signature = hashlib.sha256(json.dumps(
                sorted(ready_values), default=str, sort_keys=True,
            ).encode("utf-8")).hexdigest()[:12]
            correction_batch_id = f"{batch_id}_CORRECTION_{signature}"
        else:
            correction_batch_id = max(
                committed_batches.values(), key=lambda row: str(row.get("COMMITTED_AT") or ""),
            )["MIGRATION_CORRECTION_BATCH_ID"]
    output: list[dict] = []
    for row in rejected:
        raw_row_id = str(row["MIGRATION_RAW_ROW_ID"])
        record, _errors = rebuilt[raw_row_id]
        disposition, relation_status, reason = dispositions[raw_row_id]
        target_id = _identifier(record.get(contract["entities"][row["SOURCE_ENTITY"]]["id_field"]))
        row_identity_batch = batch_id if correction_batch_id == f"{batch_id}_CORRECTION_1" else correction_batch_id
        output.append({
            "MIGRATION_CORRECTION_ROW_ID": _correction_id(row_identity_batch, raw_row_id),
            "MIGRATION_CORRECTION_BATCH_ID": correction_batch_id,
            "ORIGINAL_MIGRATION_BATCH_ID": batch_id,
            "MIGRATION_RAW_ROW_ID": raw_row_id,
            "SOURCE_FILENAME": row.get("SOURCE_FILENAME"),
            "SOURCE_ENTITY": row.get("SOURCE_ENTITY"),
            "SOURCE_ROW_NUMBER": int(row.get("SOURCE_ROW_NUMBER") or 0),
            "SOURCE_ID": _identifier(row.get("SOURCE_ID")) or target_id,
            "TARGET_ID": target_id,
            "DISPOSITION": disposition,
            "RELATION_STATUS": relation_status,
            "REASON": reason,
            "ORIGINAL_VALIDATION_MESSAGES": _messages(row.get("VALIDATION_MESSAGES")),
            "CURRENT_VALIDATION_MESSAGES": list(dict.fromkeys(current_errors[raw_row_id])),
            "CORRECTED_DATA": record,
            "DECISION_ID": decisions.get(raw_row_id, {}).get("DECISION_ID"),
            "DECISION_VERSION": decisions.get(raw_row_id, {}).get("VERSION", 0),
        })
    return HistoricalCorrectionPreview(batch_id, correction_batch_id, output, contract.get('schema_version',''))
