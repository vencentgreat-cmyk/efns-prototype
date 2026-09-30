"""Parse and validate ordinary Flock and Quota files without database writes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5

import pandas as pd


SUPPORTED_ENTITIES = (
    "FLOCK",
    "QUOTA_REGISTRATION",
    "FLOCK_TRANSACTION",
    "QUOTA_TRANSACTION",
)
ENTITY_LABELS = {
    "Auto-detect": None,
    "Flocks": "FLOCK",
    "Quota Registrations": "QUOTA_REGISTRATION",
    "Flock Transactions": "FLOCK_TRANSACTION",
    "Quota Transactions": "QUOTA_TRANSACTION",
}
ENTITY_DISPLAY = {
    "FLOCK": "Flocks",
    "QUOTA_REGISTRATION": "Quota Registrations",
    "FLOCK_TRANSACTION": "Flock Transactions",
    "QUOTA_TRANSACTION": "Quota Transactions",
}
IMPORT_ORDER = SUPPORTED_ENTITIES
DEFAULT_MAX_FILE_BYTES = 200 * 1024 * 1024

_FRIENDLY_ALIASES = {
    "FLOCK": {
        "ACCOUNT": "ACCOUNT_ID", "FACILITY": "FACILITY_ID",
        "FACILITY_DETAIL": "FACILITY_DETAIL_ID", "QUOTA_REGISTRATION": "QUOTA_ID",
        "FLOCK_STATUS": "STATUS", "ESTIMATED_DISPOSAL_DATE": "EST_DISPOSAL",
    },
    "QUOTA_REGISTRATION": {"ACCOUNT": "ACCOUNT_ID", "QUOTA_STATUS": "STATUS"},
    "FLOCK_TRANSACTION": {"FLOCK": "FLOCK_ID"},
    "QUOTA_TRANSACTION": {
        "QUOTA_REGISTRATION": "QUOTA_ID", "OWNER_ACCOUNT": "OWNER_ACCOUNT_ID",
        "RELATED_ACCOUNT": "RELATED_ACCOUNT_ID", "RELATED_QUOTA": "RELATED_QUOTA_ID",
        "RELATED_TRANSACTION": "RELATED_TRANSACTION_ID",
    },
}
_OPERATIONAL_FIELDS = {
    "FLOCK": "FLOCK_ID FLOCK_NUMBER ACCOUNT_ID FACILITY_ID FACILITY_DETAIL_ID QUOTA_ID FLOCK_QUOTA_TYPE STATUS CREATE_DELIVERY_TRANSACTION PERMIT_NUMBER PERMIT_DATE HATCH_DATE DATE_ORDERED BIRD_COUNT EGG_COLOUR BIRD_STRAIN PLACEMENT_DATE EST_DISPOSAL DISPOSAL_DATE BIRDS_DISPOSED BREEDER HATCHERY PULLET_GROWER DISPOSAL_PLANT DISPOSAL_METHOD COMMENTS".split(),
    "QUOTA_REGISTRATION": "QUOTA_ID REGISTRATION_NUMBER ACCOUNT_ID QUOTA_NAME QUOTA_TYPE STATUS EFFECTIVE_DATE END_DATE COMMENTS".split(),
    "FLOCK_TRANSACTION": "FLOCK_TRANSACTION_ID FLOCK_ID TRANSACTION_TYPE QUANTITY TRANSACTION_DATE NOTES".split(),
    "QUOTA_TRANSACTION": "QUOTA_TRANSACTION_ID TRANSACTION_TYPE QUOTA_ID EFFECTIVE_DATE END_DATE QUOTA_COUNT OWNER_ACCOUNT_ID RELATED_ACCOUNT_ID RELATED_QUOTA_ID RELATED_TRANSACTION_ID PRICE QUOTA_LEASE_TYPE COMMENTS".split(),
}
_BUSINESS_KEYS = {
    "FLOCK": ("FLOCK_NUMBER", "PERMIT_NUMBER"),
    "QUOTA_REGISTRATION": ("REGISTRATION_NUMBER",),
    "FLOCK_TRANSACTION": (),
    "QUOTA_TRANSACTION": (),
}
_LOOKUPS = {
    "ACCOUNT": ("ACCOUNT_ID", "REGISTRATION_NUMBER", "ORGANIZATION_NAME"),
    "FACILITY": ("FACILITY_ID", "FACILITY_NAME"),
    "FACILITY_DETAIL": ("FACILITY_DETAIL_ID", "DETAIL_NAME"),
    "FLOCK": ("FLOCK_ID", "FLOCK_NUMBER", "PERMIT_NUMBER"),
    "QUOTA_REGISTRATION": ("QUOTA_ID", "REGISTRATION_NUMBER", "QUOTA_NAME"),
    "QUOTA_TRANSACTION": ("QUOTA_TRANSACTION_ID",),
}
_NULL_TEXT = {"", "null", "none", "nan", "nat"}


class OperationalImportError(ValueError):
    """An uploaded operational file could not be read safely."""


@dataclass
class OperationalFile:
    filename: str
    entity: str | None
    row_count: int
    columns: list[str]
    preview: pd.DataFrame
    file_hash: str
    file_size: int
    errors: list[str] = field(default_factory=list)


@dataclass
class OperationalRow:
    filename: str
    row_number: int
    entity: str
    action: str
    identifier: str | None
    status: str
    messages: list[str]
    raw_data: dict[str, Any]
    write_record: dict[str, Any] | None = None


@dataclass
class OperationalReport:
    files: list[OperationalFile]
    rows: list[OperationalRow]
    package_hash: str

    @property
    def ready_rows(self) -> list[OperationalRow]:
        return [row for row in self.rows if row.status == "Ready"]

    @property
    def rejected_rows(self) -> list[OperationalRow]:
        return [row for row in self.rows if row.status == "Rejected"]

    @property
    def records_by_entity(self) -> dict[str, list[dict[str, Any]]]:
        return {
            entity: [dict(row.write_record or {}) for row in self.ready_rows if row.entity == entity]
            for entity in IMPORT_ORDER
        }

    @property
    def raw_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "SOURCE_ROW_NUMBER": row.row_number,
                "RAW_DATA": {
                    "source_filename": row.filename,
                    "source_entity": row.entity,
                    "values": row.raw_data,
                },
                "VALIDATION_STATUS": row.status.upper(),
                "MATCH_STATUS": row.action or "UNRESOLVED",
                "VALIDATION_MESSAGES": row.messages,
            }
            for row in self.rows
        ]

    def rows_frame(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "FILE_NAME": row.filename,
                "ROW_NUMBER": row.row_number,
                "ENTITY": ENTITY_DISPLAY.get(row.entity, row.entity),
                "ACTION": row.action,
                "IDENTIFIER": row.identifier,
                "STATUS": row.status,
                "ERROR": " ".join(row.messages),
            }
            for row in self.rows
        ])


def _header(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in _NULL_TEXT
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _text(value: Any) -> str | None:
    return None if _missing(value) else str(value).strip()


def _key(value: Any) -> str:
    return (_text(value) or "").casefold()


def _mapping() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "config" / "eims_migration_mapping_v3.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _aliases(entity: str, contract: dict[str, Any]) -> dict[str, str]:
    spec = contract["entities"][entity]
    aliases: dict[str, str] = {"ACTION": "ACTION"}
    for target, source in spec.get("field_map", {}).items():
        aliases[_header(target)] = target
        aliases[_header(target.replace("_", " "))] = target
        aliases[_header(source)] = target
    for target in (spec.get("required", []) + [spec["id_field"]]):
        aliases[_header(target)] = target
    for target in _OPERATIONAL_FIELDS[entity]:
        aliases[_header(target)] = target
        aliases[_header(target.replace("_", " "))] = target
    for target, fallbacks in spec.get("fallbacks", {}).items():
        for fallback in fallbacks:
            aliases.setdefault(_header(fallback), target)
    aliases.update(_FRIENDLY_ALIASES.get(entity, {}))
    return aliases


def _detect_entity(headers: Iterable[str], contract: dict[str, Any]) -> tuple[str | None, str | None]:
    normalized = {_header(value) for value in headers if _header(value)}
    scores: list[tuple[int, int, str]] = []
    for entity in SUPPORTED_ENTITIES:
        spec = contract["entities"][entity]
        aliases = _aliases(entity, contract)
        mapped = {aliases[name] for name in normalized if name in aliases}
        required_hits = len(mapped.intersection(spec["required"]))
        scores.append((required_hits, len(mapped), entity))
    scores.sort(reverse=True)
    best = scores[0]
    tied = [item for item in scores if item[:2] == best[:2]]
    if best[1] < 2:
        return None, "The file does not contain enough recognized columns to identify its contents."
    if len(tied) > 1:
        return None, "The columns match more than one record type. Select the record type and validate again."
    return best[2], None


def _read_file(filename: str, content: bytes) -> pd.DataFrame:
    suffix = Path(filename).suffix.casefold()
    try:
        if suffix == ".csv":
            return pd.read_csv(io.BytesIO(content), header=0, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        if suffix in {".xlsx", ".xlsm"}:
            return pd.read_excel(io.BytesIO(content), sheet_name=0, header=0, dtype=str, keep_default_na=False)
    except Exception as exc:
        raise OperationalImportError(f"{filename} could not be read. Check that it is not damaged or password-protected.") from exc
    raise OperationalImportError(f"{filename} is not a supported CSV, XLSX, or XLSM file.")


def _convert(value: Any, kind: str, label: str, errors: list[str]) -> Any:
    if _missing(value):
        return None
    if kind == "date":
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            errors.append(f"{label} must be a valid date.")
            return None
        return parsed.date()
    if kind in {"integer", "decimal"}:
        try:
            number = Decimal(str(value).replace(",", ""))
            if not number.is_finite() or (kind == "integer" and number != number.to_integral_value()):
                raise InvalidOperation
            return int(number) if kind == "integer" else number
        except (InvalidOperation, ValueError):
            errors.append(f"{label} must be a valid {kind}.")
            return None
    if kind == "boolean":
        normalized = _key(value)
        if normalized in {"true", "yes", "y", "1"}:
            return True
        if normalized in {"false", "no", "n", "0"}:
            return False
        errors.append(f"{label} must be Yes or No.")
        return None
    return _text(value)


def _match(frame: pd.DataFrame, columns: Iterable[str], value: Any) -> tuple[dict[str, Any] | None, bool]:
    if frame.empty or _missing(value):
        return None, False
    wanted = _key(value)
    masks = []
    for column in columns:
        if column in frame.columns:
            masks.append(frame[column].fillna("").astype(str).str.strip().str.casefold() == wanted)
    if not masks:
        return None, False
    mask = masks[0]
    for other in masks[1:]:
        mask = mask | other
    found = frame[mask]
    return (found.iloc[0].to_dict(), False) if len(found) == 1 else (None, len(found) > 1)


def _resolve_reference(
    frame: pd.DataFrame, columns: Iterable[str], value: Any, label: str, errors: list[str], required: bool = False,
) -> dict[str, Any] | None:
    if _missing(value):
        if required:
            errors.append(f"{label} is required.")
        return None
    match, ambiguous = _match(frame, columns, value)
    if ambiguous:
        errors.append(f"{label} matches more than one existing record; use its ID instead.")
    elif match is None:
        errors.append(f"{label} was not found in the current system.")
    return match


def _deterministic_id(entity: str, values: dict[str, Any], id_field: str) -> str:
    supplied = _text(values.get(id_field))
    if supplied:
        return supplied
    business = next((_text(values.get(name)) for name in _BUSINESS_KEYS[entity] if _text(values.get(name))), None)
    if business is None:
        parts = [str(values.get(name) or "") for name in sorted(values) if name not in {"ACTION", id_field}]
        business = "|".join(parts)
    return str(uuid5(NAMESPACE_URL, f"efns-operational:{entity}:{business.casefold()}"))


def _existing_record(entity: str, values: dict[str, Any], frames: dict[str, pd.DataFrame], id_field: str) -> tuple[dict[str, Any] | None, bool]:
    frame = frames[entity]
    candidate = values.get(id_field)
    if not _missing(candidate):
        match, ambiguous = _match(frame, (id_field,), candidate)
        if match or ambiguous:
            return match, ambiguous
    for field in _BUSINESS_KEYS[entity]:
        if not _missing(values.get(field)):
            match, ambiguous = _match(frame, (field,), values[field])
            if match or ambiguous:
                return match, ambiguous
    return None, False


def _validate_row(
    entity: str, raw: dict[str, Any], filename: str, row_number: int,
    contract: dict[str, Any], frames: dict[str, pd.DataFrame], seen: Counter,
) -> OperationalRow:
    spec = contract["entities"][entity]
    aliases = _aliases(entity, contract)
    values: dict[str, Any] = {}
    errors: list[str] = []
    for source_name, source_value in raw.items():
        target = aliases.get(_header(source_name))
        if target and target != "ACTION" and target not in values:
            values[target] = _convert(source_value, spec.get("field_types", {}).get(target, "text"), target.replace("_", " ").title(), errors)
    if entity == "FLOCK" and _missing(values.get("FLOCK_NUMBER")):
        for fallback in spec.get("fallbacks", {}).get("FLOCK_NUMBER", []):
            source_value = next((v for k, v in raw.items() if _header(k) == _header(fallback)), None)
            if not _missing(source_value):
                values["FLOCK_NUMBER"] = _text(source_value)
                break

    id_field = spec["id_field"]
    existing, ambiguous = _existing_record(entity, values, frames, id_field)
    requested_action = (_text(next((v for k, v in raw.items() if _header(k) == "ACTION"), None)) or "").upper()
    entity_id = existing.get(id_field) if existing else _deterministic_id(entity, values, id_field)
    if existing is None and not ambiguous:
        generated_match, generated_ambiguous = _match(frames[entity], (id_field,), entity_id)
        existing = generated_match
        ambiguous = generated_ambiguous
    action = requested_action or ("UPDATE" if existing else "CREATE")
    if requested_action and requested_action not in {"CREATE", "UPDATE"}:
        errors.append("Action must be Create or Update.")
    if ambiguous:
        errors.append("The business identifier matches more than one existing record.")
    if action == "CREATE" and existing:
        errors.append("This record already exists. Remove Create to update it safely.")
    if action == "UPDATE" and existing is None:
        errors.append("The record selected for update was not found.")

    merged = dict(existing or {})
    merged.update({name: value for name, value in values.items() if not _missing(value)})
    entity_id = existing.get(id_field) if existing else entity_id
    merged[id_field] = entity_id
    values[id_field] = entity_id

    accounts = frames["ACCOUNT"]
    facilities = frames["FACILITY"]
    facility_details = frames["FACILITY_DETAIL"]
    flocks = frames["FLOCK"]
    quotas = frames["QUOTA_REGISTRATION"]
    quota_transactions = frames["QUOTA_TRANSACTION"]
    if entity == "QUOTA_REGISTRATION":
        account = _resolve_reference(accounts, _LOOKUPS["ACCOUNT"], merged.get("ACCOUNT_ID"), "Account", errors, True)
        if account:
            values["ACCOUNT_ID"] = account["ACCOUNT_ID"]
            merged["ACCOUNT_ID"] = account["ACCOUNT_ID"]
        values.setdefault("STATUS", merged.get("STATUS") or "Active")
        values.setdefault("QUOTA_NAME", merged.get("QUOTA_NAME") or merged.get("REGISTRATION_NUMBER"))
        merged.update({"STATUS": values["STATUS"], "QUOTA_NAME": values["QUOTA_NAME"]})
    elif entity == "FLOCK":
        account = _resolve_reference(accounts, _LOOKUPS["ACCOUNT"], merged.get("ACCOUNT_ID"), "Account", errors, True)
        if account:
            values["ACCOUNT_ID"] = account["ACCOUNT_ID"]
            merged["ACCOUNT_ID"] = account["ACCOUNT_ID"]
        facility = _resolve_reference(facilities, _LOOKUPS["FACILITY"], merged.get("FACILITY_ID"), "Facility", errors)
        if facility:
            values["FACILITY_ID"] = facility["FACILITY_ID"]
            merged["FACILITY_ID"] = facility["FACILITY_ID"]
            if account and str(facility.get("ACCOUNT_ID")) != str(account.get("ACCOUNT_ID")):
                errors.append("Facility does not belong to the selected Account.")
        detail = _resolve_reference(
            facility_details, _LOOKUPS["FACILITY_DETAIL"], merged.get("FACILITY_DETAIL_ID"),
            "Facility Detail", errors,
        )
        if detail:
            values["FACILITY_DETAIL_ID"] = detail["FACILITY_DETAIL_ID"]
            merged["FACILITY_DETAIL_ID"] = detail["FACILITY_DETAIL_ID"]
            if facility and str(detail.get("FACILITY_ID")) != str(facility.get("FACILITY_ID")):
                errors.append("Facility Detail does not belong to the selected Facility.")
        quota = _resolve_reference(quotas, _LOOKUPS["QUOTA_REGISTRATION"], merged.get("QUOTA_ID"), "Quota Registration", errors)
        if quota:
            values["QUOTA_ID"] = quota["QUOTA_ID"]
            merged["QUOTA_ID"] = quota["QUOTA_ID"]
            if account and str(quota.get("ACCOUNT_ID")) != str(account.get("ACCOUNT_ID")):
                errors.append("Quota Registration does not belong to the selected Account.")
        values.setdefault("STATUS", merged.get("STATUS") or "Planned")
        values.setdefault("BIRDS_DISPOSED", merged.get("BIRDS_DISPOSED") or 0)
        merged.update({"STATUS": values["STATUS"], "BIRDS_DISPOSED": values["BIRDS_DISPOSED"]})
        if _missing(merged.get("FACILITY_ID")):
            errors.append("Facility is required.")
        bird_count = merged.get("BIRD_COUNT")
        birds_disposed = merged.get("BIRDS_DISPOSED") or 0
        if bird_count is not None and bird_count < 0:
            errors.append("Bird Count cannot be negative.")
        if birds_disposed < 0:
            errors.append("Birds Disposed cannot be negative.")
        if bird_count is not None and birds_disposed > bird_count:
            errors.append("Birds Disposed cannot exceed Bird Count.")
        hatch, placement, disposal = merged.get("HATCH_DATE"), merged.get("PLACEMENT_DATE"), merged.get("DISPOSAL_DATE")
        if isinstance(disposal, dt.date) and isinstance(hatch, dt.date) and disposal < hatch:
            errors.append("Disposal Date cannot be earlier than Hatch Date.")
        if isinstance(disposal, dt.date) and isinstance(placement, dt.date) and disposal < placement:
            errors.append("Disposal Date cannot be earlier than Placement Date.")
    elif entity == "FLOCK_TRANSACTION":
        flock = _resolve_reference(flocks, _LOOKUPS["FLOCK"], merged.get("FLOCK_ID"), "Flock", errors, True)
        if flock:
            values["FLOCK_ID"] = flock["FLOCK_ID"]
            merged["FLOCK_ID"] = flock["FLOCK_ID"]
        quantity = merged.get("QUANTITY")
        if quantity is not None and quantity < 0:
            errors.append("Quantity cannot be negative.")
    elif entity == "QUOTA_TRANSACTION":
        quota = _resolve_reference(quotas, _LOOKUPS["QUOTA_REGISTRATION"], merged.get("QUOTA_ID"), "Quota Registration", errors, True)
        if quota:
            values["QUOTA_ID"] = quota["QUOTA_ID"]
            values["OWNER_ACCOUNT_ID"] = quota.get("ACCOUNT_ID")
            merged.update({"QUOTA_ID": quota["QUOTA_ID"], "OWNER_ACCOUNT_ID": quota.get("ACCOUNT_ID")})
        for field, frame, lookup, label in (
            ("RELATED_ACCOUNT_ID", accounts, _LOOKUPS["ACCOUNT"], "Related Account"),
            ("RELATED_QUOTA_ID", quotas, _LOOKUPS["QUOTA_REGISTRATION"], "Related Quota"),
            ("RELATED_TRANSACTION_ID", quota_transactions, _LOOKUPS["QUOTA_TRANSACTION"], "Related Transaction"),
        ):
            related = _resolve_reference(frame, lookup, merged.get(field), label, errors)
            if related:
                target_id = lookup[0]
                values[field] = related[target_id]
                merged[field] = related[target_id]

    for required in spec["required"]:
        if _missing(merged.get(required)):
            errors.append(f"{required.replace('_', ' ').title()} is required.")
    for field, rule in spec.get("numeric_rules", {}).items():
        number = merged.get(field)
        if number is not None and "min" in rule and number < Decimal(str(rule["min"])):
            errors.append(f"{field.replace('_', ' ').title()} must be at least {rule['min']}.")
    start = merged.get("EFFECTIVE_DATE")
    end = merged.get("END_DATE")
    if isinstance(start, dt.date) and isinstance(end, dt.date) and end < start:
        errors.append("End Date cannot be earlier than Effective Date.")

    duplicate_key = (entity, str(entity_id).casefold())
    seen[duplicate_key] += 1
    if seen[duplicate_key] > 1:
        errors.append("This record is duplicated within the uploaded files.")
    write_values = dict(merged)
    if existing and action == "UPDATE":
        write_values["EXPECTED_UPDATED_AT"] = existing.get("UPDATED_AT")
    write_record = dict(write_values, ACTION=action) if not errors else None
    return OperationalRow(filename, row_number, entity, action, str(entity_id), "Rejected" if errors else "Ready", errors, raw, write_record)


def analyze_operational_files(
    uploads: Iterable[Any], selection: str, repo, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> OperationalReport:
    """Read and validate independent operational files; this function never writes."""
    contract = _mapping()
    selected_entity = ENTITY_LABELS.get(selection, selection if selection in SUPPORTED_ENTITIES else None)
    frames = {
        "ACCOUNT": repo.get_accounts(), "FACILITY": repo.get_facilities(),
        "FACILITY_DETAIL": repo.get_facility_details(),
        "FLOCK": repo.get_flocks(), "QUOTA_REGISTRATION": repo.get_quota_registrations(),
        "FLOCK_TRANSACTION": repo.get_flock_transactions(),
        "QUOTA_TRANSACTION": repo.get_quota_transactions(),
    }
    files: list[OperationalFile] = []
    pending: list[tuple[str, str, int, dict[str, Any]]] = []
    invalid_rows: list[OperationalRow] = []
    fingerprints: list[str] = []
    for upload in uploads:
        filename = Path(upload.name).name
        content = upload.getvalue()
        content_hash = hashlib.sha256(content).hexdigest()
        if not content:
            fingerprints.append(f"{content_hash}:EMPTY")
            files.append(OperationalFile(filename, None, 0, [], pd.DataFrame(), content_hash, 0, ["The file is empty."]))
            continue
        if len(content) > max_file_bytes:
            fingerprints.append(f"{content_hash}:TOO_LARGE")
            files.append(OperationalFile(filename, None, 0, [], pd.DataFrame(), content_hash, len(content), ["The file exceeds the configured upload limit."]))
            continue
        frame = _read_file(filename, content)
        original_columns = [str(value) for value in frame.columns]
        normalized = [_header(value) for value in original_columns]
        duplicate_headers = sorted(name for name, count in Counter(normalized).items() if name and count > 1)
        entity, detection_error = (selected_entity, None) if selected_entity else _detect_entity(original_columns, contract)
        errors = ([detection_error] if detection_error else []) + (["Duplicate columns: " + ", ".join(duplicate_headers) + "."] if duplicate_headers else [])
        digest = content_hash
        fingerprints.append(f"{digest}:{entity or 'UNKNOWN'}")
        files.append(OperationalFile(filename, entity, len(frame), original_columns, frame.head(20), digest, len(content), errors))
        if entity and not errors:
            for index, row in frame.iterrows():
                pending.append((filename, entity, int(index) + 2, {str(k): v for k, v in row.to_dict().items()}))
        elif errors:
            for index, row in frame.iterrows():
                invalid_rows.append(OperationalRow(
                    filename, int(index) + 2, entity or "UNKNOWN", "", None,
                    "Rejected", list(errors), {str(k): v for k, v in row.to_dict().items()}, None,
                ))
    package_hash = hashlib.sha256("|".join(sorted(fingerprints)).encode("utf-8")).hexdigest()
    seen: Counter = Counter()
    rows = [
        _validate_row(entity, raw, filename, row_number, contract, frames, seen)
        for filename, entity, row_number, raw in pending
    ] + invalid_rows
    return OperationalReport(files, rows, package_hash)
