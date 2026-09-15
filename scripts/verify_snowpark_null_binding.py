"""Controlled EFNS_DEV verification for Snowpark NULL bulk bindings.

The writes are intentionally rolled back. This script refuses non-DEV targets
and uses only generated ``DEV_VERIFY_`` identifiers.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import uuid

import pandas as pd
import snowflake.connector
from snowflake.snowpark import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.connection import SnowparkExecutor
from data.repositories.snowflake import SnowflakeRepository


class VerificationRollback(Exception):
    """End the verification transaction without retaining synthetic rows."""


def verification_id() -> str:
    return f"DEV_VERIFY_{uuid.uuid4().hex[:25]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection", default="efns-dev")
    parser.add_argument("--role", default="EFNS_DEV_DEPLOYER")
    parser.add_argument("--warehouse", default="EFNS_DEV_WH")
    parser.add_argument("--database", default="EFNS_DEV")
    parser.add_argument("--confirm-dev-dml", action="store_true")
    args = parser.parse_args()
    if args.database.upper() != "EFNS_DEV" or not args.confirm_dev_dml:
        raise SystemExit("Refusing to run without EFNS_DEV and --confirm-dev-dml.")

    connection = snowflake.connector.connect(
        connection_name=args.connection,
        role=args.role,
        warehouse=args.warehouse,
        database=args.database,
        paramstyle="qmark",
        autocommit=False,
    )
    session = Session.builder.config("connection", connection).create()
    executor = SnowparkExecutor(session, "DEV verification")
    repository = SnowflakeRepository(executor=executor)
    if repository.database.upper() != args.database.upper():
        raise SystemExit("Configured repository database does not match the DEV target.")
    import_id = verification_id()
    production_id = verification_id()
    observed_null = False
    try:
        try:
            with executor.transaction() as tx:
                repository._insert_batch(tx, import_id, {
                    "FILENAME": f"{import_id}.synthetic.xlsm",
                    "SOURCE": "DEV_VERIFY_SNOWPARK_NULL_BINDING",
                    "STATUS": "Validated",
                    "SOURCE_RECORD_COUNT": 1,
                })
                inserted = repository._insert_production(tx, [{
                    "PRODUCTION_ID": production_id,
                    "SOURCE_TYPE": "EIMS_IMPORT",
                    "MATCH_STATUS": "UNMATCHED",
                    "SOURCE_ROW_NUMBER": 1,
                    "REPORTING_YEAR": 2026,
                    "REPORTING_WEEK": 1,
                    "FLOCK_AGE": None,
                }], import_id)
                result = tx.query(
                    "SELECT FLOCK_AGE FROM EFNS_DEV.CORE.PRODUCTION_RECORD "
                    "WHERE PRODUCTION_ID = %s AND IMPORT_ID = %s",
                    (production_id, import_id),
                )
                observed_null = (
                    inserted == 1
                    and len(result) == 1
                    and pd.isna(result.iloc[0]["FLOCK_AGE"])
                )
                if not observed_null:
                    raise RuntimeError("DEV verification did not observe one SQL NULL FLOCK_AGE row.")
                raise VerificationRollback()
        except VerificationRollback:
            pass

        remaining_production = executor.query(
            "SELECT COUNT(*) AS RECORD_COUNT FROM EFNS_DEV.CORE.PRODUCTION_RECORD "
            "WHERE PRODUCTION_ID = %s",
            (production_id,),
        )
        remaining_batch = executor.query(
            "SELECT COUNT(*) AS RECORD_COUNT FROM EFNS_DEV.RAW.IMPORT_BATCH "
            "WHERE IMPORT_ID = %s",
            (import_id,),
        )
        cleaned = (
            int(remaining_production.iloc[0]["RECORD_COUNT"]) == 0
            and int(remaining_batch.iloc[0]["RECORD_COUNT"]) == 0
        )
        if not cleaned:
            raise RuntimeError("DEV verification rollback left synthetic rows behind.")
        print("Snowpark NULL binding verified: FLOCK_AGE stored as SQL NULL.")
        print("Transaction rollback verified: no DEV_VERIFY_ rows remain.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
