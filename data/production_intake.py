"""Source-preserving workbook preparation, independent of database writes."""
import uuid

import pandas as pd

from data.importing import build_raw_rows, normalize_eims_records, validate_eims_records
from data.producer_identity import resolve_producer


def prepare_workbook(raw, file_id, accounts):
    errors, warnings = validate_eims_records(raw)
    records = normalize_eims_records(raw)
    raw_rows = build_raw_rows(raw, "VALID", errors + warnings)
    accepted = []
    for record, source in zip(records.to_dict("records"), raw_rows):
        ordinal = int(record["SOURCE_ROW_NUMBER"])
        record["PRODUCTION_ID"] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"efns:{file_id}:{ordinal}"))
        record["SOURCE_FILE_ID"] = file_id
        record["RAW_ROW_ID"] = str(uuid.uuid5(uuid.NAMESPACE_URL, f"efns:raw:{file_id}:{ordinal}"))
        source.update(SOURCE_FILE_ID=file_id, RAW_ROW_ID=record["RAW_ROW_ID"])
        decision = resolve_producer(record, accounts)
        record.update(PRODUCER_ACCOUNT_ID=decision["account_id"], MATCH_STATUS=decision["status"],
                      MATCH_METHOD=decision["method"], MATCH_BASIS=decision["basis"])
        source["MATCH_STATUS"] = decision["status"]
        row_errors = [error for error in errors if error.startswith(f"Excel row {ordinal}:") or error.startswith("Missing required columns:")]
        source["VALIDATION_STATUS"] = "REJECTED" if row_errors else "VALID"
        source["TARGET_ENTITY"] = "PRODUCTION_RECORD" if not row_errors else None
        source["TARGET_ID"] = record["PRODUCTION_ID"] if not row_errors else None
        # A retained RAW row is not a validated business record.
        if not row_errors:
            accepted.append(record)
    return pd.DataFrame(accepted, columns=records.columns.tolist() + ["SOURCE_FILE_ID", "RAW_ROW_ID", "MATCH_METHOD", "MATCH_BASIS"]), raw_rows, errors, warnings
