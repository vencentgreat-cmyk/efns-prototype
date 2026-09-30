"""EIMS migration parsing, validation, lineage, and reconciliation.

Field rules are intentionally isolated in ``config/eims_migration_mapping.json``
so authoritative EIMS metadata can replace this provisional contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING_PATH = ROOT / "config" / "eims_migration_mapping_v3.json"
V1_MAPPING_PATH = ROOT / "config" / "eims_migration_mapping_v1.json"
V2_MAPPING_PATH = ROOT / "config" / "eims_migration_mapping_v2.json"
V3_MAPPING_PATH = DEFAULT_MAPPING_PATH
SYNTHETIC_PREFIXES = ("DEV_MIGRATION_", "DEV_SYNTH_")
WORKFLOW_STATUSES = (
    "UPLOADED", "PARSED", "VALIDATED", "READY", "COMMITTED",
    "PARTIAL", "REJECTED", "FAILED",
)
_NULL_TEXT = frozenset({"", "none", "null", "nan", "nat"})
_NUMBER = re.compile(r"^[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$")
_GUID = re.compile(r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$")


@dataclass(frozen=True)
class MigrationSourceFile:
    name: str
    content: bytes


@dataclass
class MigrationAnalysis:
    batch_id: str
    package_hash: str
    schema_version: str
    files: list[dict]
    raw_rows: list[dict]
    records: dict[str, list[dict]]
    errors: pd.DataFrame
    reconciliation: pd.DataFrame

    @property
    def rejected_count(self) -> int:
        return sum(row["VALIDATION_STATUS"] == "REJECTED" for row in self.raw_rows)

    @property
    def ready_count(self) -> int:
        return sum(row["VALIDATION_STATUS"] == "READY" for row in self.raw_rows)


def load_mapping(path: Path = DEFAULT_MAPPING_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_mapping_for_version(schema_version: str | None) -> dict:
    """Resolve the explicit migration contract without ambiguous file sets."""
    for path in (V3_MAPPING_PATH, V2_MAPPING_PATH, V1_MAPPING_PATH):
        contract = load_mapping(path)
        if schema_version == contract["schema_version"]:
            return contract
    raise ValueError("The migration package schema version is not supported.")


def expected_filenames(mapping: dict | None = None) -> list[str]:
    contract = mapping or load_mapping()
    return [contract["entities"][name]["filename"] for name in contract["entity_order"]]


def _source_file(value) -> MigrationSourceFile:
    if isinstance(value, MigrationSourceFile):
        return value
    name = Path(str(getattr(value, "name", ""))).name
    if not name:
        raise ValueError("Every migration upload requires a filename.")
    if hasattr(value, "getvalue"):
        content = value.getvalue()
    elif hasattr(value, "read"):
        content = value.read()
    else:
        content = bytes(value)
    return MigrationSourceFile(name, bytes(content))


def safe_stage_component(value: str) -> str:
    name = Path(str(value or "")).name
    if name != value or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.$-]{0,199}", name):
        raise ValueError("Migration filename is not safe for the internal stage.")
    return name


def migration_stage_path(batch_id: str, filename: str) -> str:
    if not str(batch_id).startswith("DEV_MIGRATION_") or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(batch_id)):
        raise ValueError("Only DEV_MIGRATION_ batches can use the prototype migration stage.")
    return f"@EFNS_DEV.RAW.EIMS_MIGRATION_FILES/{batch_id}/{safe_stage_component(filename)}"


def migration_stage_prefix(batch_id: str) -> str:
    if not str(batch_id).startswith("DEV_MIGRATION_") or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(batch_id)):
        raise ValueError("Only DEV_MIGRATION_ batches can use the prototype migration stage.")
    return f"@EFNS_DEV.RAW.EIMS_MIGRATION_FILES/{batch_id}/"


def _read_frame(source: MigrationSourceFile, spec: dict) -> pd.DataFrame:
    if source.name.lower().endswith(".csv"):
        return pd.read_csv(
            io.BytesIO(source.content), header=0, dtype=object,
            keep_default_na=False, encoding="utf-8-sig",
        )
    if source.name.lower().endswith((".xlsx", ".xlsm")):
        return pd.read_excel(
            io.BytesIO(source.content),
            sheet_name=spec.get("worksheet", 0),
            dtype=object,
            engine="openpyxl",
        )
    raise ValueError(f"{source.name}: only CSV and XLSX migration files are supported.")


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and value.strip().casefold() in _NULL_TEXT


def _convert(value, kind: str, field: str) -> tuple[object, str | None]:
    if _missing(value):
        return None, None
    if kind == "string" or kind == "choice":
        return str(value).strip(), None
    if kind == "boolean":
        if isinstance(value, bool):
            return value, None
        text = str(value).strip().casefold()
        if text in {"true", "1", "1.0", "yes"}:
            return True, None
        if text in {"false", "0", "0.0", "no"}:
            return False, None
        return None, f"{field} must be a boolean."
    if kind == "date":
        if isinstance(value, dt.datetime):
            return value.date(), None
        if isinstance(value, dt.date):
            return value, None
        try:
            parsed = pd.to_datetime(str(value).strip(), errors="raise")
            return parsed.date(), None
        except (TypeError, ValueError):
            return None, f"{field} must contain a valid ISO date or datetime."
    if kind in {"integer", "decimal"}:
        text = str(value).strip()
        if not _NUMBER.fullmatch(text):
            return None, f"{field} must contain a valid number."
        try:
            number = Decimal(text.replace(",", ""))
        except InvalidOperation:
            return None, f"{field} must contain a valid number."
        if kind == "integer":
            if number != number.to_integral_value():
                return None, f"{field} must contain a whole number."
            return int(number), None
        return number, None
    return None, f"{field} has an unsupported provisional type."


def _field_types(spec: dict) -> dict[str, str]:
    if "field_map" in spec:
        fields = {field: "string" for field in spec["field_map"]}
        fields.update({field: "string" for field in spec.get("fallbacks", {})})
        fields.update({field: "string" for field in spec.get("constants", {})})
        fields.update({field: "string" for field in spec.get("derive_parent_fields", {})})
        fields.update(spec.get("field_types", {}))
        return fields
    return spec["fields"]


def _source_value(raw: dict, spec: dict, field: str, source_row: int):
    if field in spec.get("constants", {}):
        return spec["constants"][field]
    if field in spec.get("row_number_fields", ()):
        return source_row
    if field in spec.get("fallbacks", {}):
        for source_field in spec["fallbacks"][field]:
            value = raw.get(str(source_field).upper())
            if not _missing(value):
                return value
        return None
    source_field = spec.get("field_map", {}).get(field, field)
    value = raw.get(str(source_field).upper())
    period_part = spec.get("period_fields", {}).get(field)
    if period_part and not _missing(value):
        text = str(value).strip()
        if re.fullmatch(r"\d{6}", text):
            return text[:4] if period_part == "year" else text[4:]
    return value


def _valid_source_id(value, policy: str) -> bool:
    if policy == "guid":
        return bool(_GUID.fullmatch(str(value)))
    if policy == "date":
        return isinstance(value, dt.date)
    return any(str(value).startswith(prefix) for prefix in SYNTHETIC_PREFIXES)


def _rule_error(field: str, value, rule: dict) -> str | None:
    if value is None or not rule:
        return None
    number = Decimal(str(value))
    if "min" in rule and number < Decimal(str(rule["min"])):
        return f"{field} must be at least {rule['min']}."
    if "min_exclusive" in rule and number <= Decimal(str(rule["min_exclusive"])):
        return f"{field} must be greater than {rule['min_exclusive']}."
    if "max" in rule and number > Decimal(str(rule["max"])):
        return f"{field} must be no more than {rule['max']}."
    return None


def analyze_migration_files(files: Iterable, mapping: dict | None = None) -> MigrationAnalysis:
    sources = [_source_file(value) for value in files]
    if mapping is None:
        supplied = {source.name for source in sources}
        contracts = [load_mapping(path) for path in (V3_MAPPING_PATH, V2_MAPPING_PATH, V1_MAPPING_PATH)]
        contract = next(
            (candidate for candidate in contracts if supplied == set(expected_filenames(candidate))),
            load_mapping(),
        )
    else:
        contract = mapping
    by_name = {safe_stage_component(source.name): source for source in sources}
    if len(by_name) != len(sources):
        raise ValueError("Duplicate migration filenames are not allowed.")
    missing_files = sorted(set(expected_filenames(contract)) - set(by_name))
    if missing_files:
        raise ValueError("Missing migration files: " + ", ".join(missing_files))

    file_entries = []
    digest = hashlib.sha256()
    parsed: dict[str, list[dict]] = {}
    row_errors: dict[tuple[str, int], list[str]] = {}
    row_normalized: dict[tuple[str, int], dict] = {}
    source_ids: dict[str, dict[str, list[int]]] = {}

    for entity in contract["entity_order"]:
        spec = contract["entities"][entity]
        source = by_name[spec["filename"]]
        file_hash = hashlib.sha256(source.content).hexdigest()
        digest.update(source.name.encode("utf-8")); digest.update(file_hash.encode("ascii"))
        frame = _read_frame(source, spec)
        frame.columns = [str(column).strip().upper() for column in frame.columns]
        if len(frame.columns) != len(set(frame.columns)):
            raise ValueError(f"{source.name}: duplicate column names are not allowed.")
        parsed[entity] = frame.to_dict("records")
        file_entries.append({
            "SOURCE_FILENAME": source.name,
            "SOURCE_ENTITY": entity,
            "FILE_HASH": file_hash,
            "FILE_SIZE_BYTES": len(source.content),
            "SOURCE_ROW_COUNT": len(frame),
            "STAGE_PATH": None,
            "CONTENT": source.content,
        })
        id_field = spec["id_field"]
        fields = _field_types(spec)
        source_ids[entity] = {}
        natural_values: dict[tuple, list[int]] = {}
        for offset, raw in enumerate(parsed[entity], 2):
            key = (entity, offset)
            messages: list[str] = []
            normalized = {}
            expected_source_fields = {
                str(value).upper() for value in spec.get("field_map", {}).values()
            } or set(fields)
            expected_source_fields.update(
                str(value).upper()
                for values in spec.get("fallbacks", {}).values()
                for value in values
            )
            unknown = sorted(set(raw) - expected_source_fields)
            if unknown and not (spec.get("allow_extra_columns") or contract.get("allow_extra_columns")):
                messages.append("Unknown columns: " + ", ".join(unknown) + ".")
            for field, kind in fields.items():
                value, error = _convert(_source_value(raw, spec, field, offset), kind, field)
                normalized[field] = value
                if error:
                    messages.append(error)
                choices = spec.get("choices", {}).get(field)
                if value is not None and choices and value not in choices:
                    messages.append(f"{field} contains an unknown choice value.")
                rule_error = _rule_error(field, value, spec.get("numeric_rules", {}).get(field, {}))
                if rule_error:
                    messages.append(rule_error)
            source_id = normalized.get(id_field)
            if source_id:
                id_policy = spec.get("id_policy", contract.get("id_policy", "synthetic"))
                if not _valid_source_id(source_id, id_policy):
                    messages.append(f"{id_field} does not match the required {id_policy} identifier format.")
                source_ids[entity].setdefault(str(source_id), []).append(offset)
            natural_key = tuple(normalized.get(field) for field in spec.get("natural_key", ()))
            if natural_key and all(value is not None for value in natural_key):
                natural_values.setdefault(natural_key, []).append(offset)
            row_errors[key] = messages
            row_normalized[key] = normalized
        for duplicate_rows in source_ids[entity].values():
            if len(duplicate_rows) > 1 and not spec.get("deduplicate_by"):
                for source_row in duplicate_rows:
                    row_errors[(entity, source_row)].append(f"Duplicate {id_field} in source file.")
        for duplicate_rows in natural_values.values():
            if len(duplicate_rows) > 1:
                for source_row in duplicate_rows:
                    row_errors[(entity, source_row)].append("Repeated provisional natural key.")

    normalized_indexes: dict[str, dict[str, dict]] = {}
    for entity in contract["entity_order"]:
        id_field = contract["entities"][entity]["id_field"]
        normalized_indexes[entity] = {
            str(value[id_field]): value
            for (row_entity, _), value in row_normalized.items()
            if row_entity == entity and value.get(id_field) is not None
        }

    for entity in contract["entity_order"]:
        spec = contract["entities"][entity]
        for offset, _raw in enumerate(parsed[entity], 2):
            key = (entity, offset)
            normalized = row_normalized[key]
            for target_field, rule in spec.get("derive_parent_fields", {}).items():
                source_field, parent_entity, parent_key, parent_field = rule
                source_id = normalized.get(source_field)
                parent = normalized_indexes[parent_entity].get(str(source_id)) if source_id is not None else None
                if parent and str(parent.get(parent_key)) == str(source_id):
                    normalized[target_field] = parent.get(parent_field)
            for field in spec.get("required", ()):
                if normalized.get(field) is None:
                    row_errors[key].append(f"{field} is required.")

    valid_ids: dict[str, set[str]] = {entity: set() for entity in contract["entity_order"]}
    for entity in contract["entity_order"]:
        spec = contract["entities"][entity]
        for offset, _raw in enumerate(parsed[entity], 2):
            key = (entity, offset)
            normalized = row_normalized[key]
            for field, (parent_entity, _parent_field) in spec.get("foreign_keys", {}).items():
                parent_id = normalized.get(field)
                if parent_id is not None and str(parent_id) not in valid_ids[parent_entity] and not (
                    parent_entity == entity and str(parent_id) in source_ids[parent_entity]
                ):
                    row_errors[key].append(f"{field} references a missing or rejected {parent_entity}.")

            if entity == "FLOCK" and not row_errors[key]:
                facility = normalized_indexes.get("FACILITY", {}).get(str(normalized.get("FACILITY_ID")))
                detail = normalized_indexes.get("FACILITY_DETAIL", {}).get(str(normalized.get("FACILITY_DETAIL_ID")))
                quota = normalized_indexes.get("QUOTA_REGISTRATION", {}).get(str(normalized.get("QUOTA_ID")))
                if facility and facility.get("ACCOUNT_ID") != normalized.get("ACCOUNT_ID"):
                    row_errors[key].append("FACILITY_ID does not belong to ACCOUNT_ID.")
                if detail and detail.get("FACILITY_ID") != normalized.get("FACILITY_ID"):
                    row_errors[key].append("FACILITY_DETAIL_ID does not belong to FACILITY_ID.")
                if quota and quota.get("ACCOUNT_ID") != normalized.get("ACCOUNT_ID"):
                    row_errors[key].append("QUOTA_ID does not belong to ACCOUNT_ID.")
            if entity == "SALMONELLA_TEST" and not row_errors[key]:
                flock = normalized_indexes.get("FLOCK", {}).get(str(normalized.get("FLOCK_ID")))
                if flock and flock.get("ACCOUNT_ID") != normalized.get("ACCOUNT_ID"):
                    row_errors[key].append("FLOCK_ID does not belong to ACCOUNT_ID.")
            if entity == "QUOTA_TRANSACTION" and not row_errors[key]:
                quota = normalized_indexes.get("QUOTA_REGISTRATION", {}).get(str(normalized.get("QUOTA_ID")))
                if quota and quota.get("ACCOUNT_ID") != normalized.get("OWNER_ACCOUNT_ID"):
                    row_errors[key].append("OWNER_ACCOUNT_ID does not own QUOTA_ID.")
            if not row_errors[key]:
                valid_ids[entity].add(str(normalized[spec["id_field"]]))

    # Forward self-references are allowed, but only when the referenced row is
    # itself valid. This second pass prevents a rejected transaction from being
    # used as a seemingly valid relationship target.
    for entity in contract["entity_order"]:
        spec = contract["entities"][entity]
        self_fields = {
            field for field, (parent, _parent_field) in spec.get("foreign_keys", {}).items()
            if parent == entity
        }
        for offset, _raw in enumerate(parsed[entity], 2):
            key = (entity, offset)
            normalized = row_normalized[key]
            for field in self_fields:
                parent_id = normalized.get(field)
                parent_rows = source_ids[entity].get(str(parent_id), []) if parent_id is not None else []
                if parent_id is not None and (
                    not parent_rows or all(row_errors[(entity, parent_row)] for parent_row in parent_rows)
                ):
                    message = f"{field} references a missing or rejected {entity}."
                    if message not in row_errors[key]:
                        row_errors[key].append(message)

    package_hash = digest.hexdigest()
    batch_id = f"DEV_MIGRATION_{package_hash[:22]}"
    raw_rows: list[dict] = []
    records: dict[str, list[dict]] = {entity: [] for entity in contract["entity_order"]}
    error_rows: list[dict] = []
    reconciliation_rows: list[dict] = []
    for entity in contract["entity_order"]:
        filename = contract["entities"][entity]["filename"]
        ready = rejected = 0
        for offset, raw in enumerate(parsed[entity], 2):
            key = (entity, offset); messages = row_errors[key]
            normalized = row_normalized[key]
            status = "REJECTED" if messages else "READY"
            ready += status == "READY"; rejected += status == "REJECTED"
            if status == "READY":
                records[entity].append(normalized)
            for message in messages:
                error_rows.append({"SOURCE_FILE": filename, "SOURCE_ENTITY": entity, "SOURCE_ROW_NUMBER": offset, "FIELD_MESSAGE": message})
            source_id = normalized.get(contract["entities"][entity]["id_field"])
            raw_rows.append({
                "MIGRATION_RAW_ROW_ID": f"DEV_MIGRATION_RAW_{len(raw_rows)+1:07d}",
                "SOURCE_FILENAME": filename, "SOURCE_ENTITY": entity,
                "SOURCE_ROW_NUMBER": offset, "SOURCE_ID": source_id,
                "TARGET_ID": source_id if status == "READY" else None,
                "RAW_DATA": raw, "NORMALIZED_DATA": normalized if status == "READY" else None,
                "VALIDATION_STATUS": status,
                "MATCH_STATUS": "CONFIRMED" if status == "READY" else "NO_CANDIDATE",
                "VALIDATION_MESSAGES": messages,
            })
        deduplicate_by = contract["entities"][entity].get("deduplicate_by")
        if deduplicate_by:
            grouped: dict[object, dict] = {}
            element_codes: dict[object, set[str]] = {}
            for record in records[entity]:
                key_value = record[deduplicate_by]
                grouped.setdefault(key_value, record)
                if record.get("ELEMENT_CODE"):
                    element_codes.setdefault(key_value, set()).add(str(record["ELEMENT_CODE"]))
            records[entity] = []
            for key_value, record in grouped.items():
                stored = dict(record)
                stored["ELEMENT_CODES"] = ",".join(sorted(element_codes.get(key_value, set())))
                records[entity].append(stored)
            canonical = {record[deduplicate_by]: record for record in records[entity]}
            seen: set[object] = set()
            for raw_row in raw_rows:
                if raw_row["SOURCE_ENTITY"] != entity or raw_row["VALIDATION_STATUS"] != "READY":
                    continue
                key_value = raw_row["NORMALIZED_DATA"][deduplicate_by]
                if key_value in seen:
                    raw_row["NORMALIZED_DATA"] = None
                else:
                    raw_row["NORMALIZED_DATA"] = canonical[key_value]
                    seen.add(key_value)
        unmatched = sum(
            1 for row in raw_rows
            if row["SOURCE_ENTITY"] == entity and row.get("MATCH_STATUS") not in {"CONFIRMED", None}
        )
        reconciliation_rows.append({
            "SOURCE_ENTITY": entity, "SOURCE_ROWS": len(parsed[entity]),
            "RAW_ROWS": len(parsed[entity]), "READY_ROWS": ready,
            "COMMITTED_ROWS": 0, "REJECTED_ROWS": rejected,
            "UNMATCHED_ROWS": unmatched,
        })
    return MigrationAnalysis(
        batch_id=batch_id, package_hash=package_hash,
        schema_version=contract["schema_version"], files=file_entries,
        raw_rows=raw_rows, records=records,
        errors=pd.DataFrame(error_rows, columns=["SOURCE_FILE","SOURCE_ENTITY","SOURCE_ROW_NUMBER","FIELD_MESSAGE"]),
        reconciliation=pd.DataFrame(reconciliation_rows),
    )
