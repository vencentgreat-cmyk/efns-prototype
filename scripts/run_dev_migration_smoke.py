"""Load, verify, and clean one generated DEV_MIGRATION_ package in EFNS_DEV."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.migration import MigrationSourceFile, analyze_migration_files
from data.repositories.snowflake import SnowflakeRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection", default="efns-dev")
    parser.add_argument("--dataset", type=Path, default=ROOT / "sample_data" / "fake_eims_export" / "clean")
    parser.add_argument("--role", choices=["EFNS_DEV_APP_OWNER"], default="EFNS_DEV_APP_OWNER")
    parser.add_argument("--confirm-dev-dml", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    if not args.confirm_dev_dml:
        parser.error("--confirm-dev-dml is required; this command writes synthetic EFNS_DEV rows.")

    os.environ["SNOWFLAKE_CONNECTION_NAME"] = args.connection
    os.environ["SNOWFLAKE_DATABASE"] = "EFNS_DEV"
    files = [MigrationSourceFile(path.name, path.read_bytes()) for path in sorted(args.dataset.iterdir()) if path.is_file()]
    analysis = analyze_migration_files(files)
    if not analysis.batch_id.startswith("DEV_MIGRATION_") or analysis.rejected_count:
        raise RuntimeError("The DEV smoke command accepts only a clean DEV_MIGRATION_ package.")

    repository = SnowflakeRepository()
    repository._executor().execute("USE ROLE EFNS_DEV_APP_OWNER")
    if repository.find_migration_by_hash(analysis.package_hash):
        raise RuntimeError("This migration package already exists; inspect or clean that exact batch before retrying.")

    prepared = False
    try:
        file_rows = []
        for source in analysis.files:
            stage_path = repository.stage_migration_file(
                analysis.batch_id, source["SOURCE_FILENAME"], source["CONTENT"]
            )
            file_rows.append({**source, "STAGE_PATH": stage_path})
        repository.prepare_migration_batch(
            {
                "MIGRATION_BATCH_ID": analysis.batch_id,
                "PACKAGE_HASH": analysis.package_hash,
                "SCHEMA_VERSION": analysis.schema_version,
                "STATUS": "READY",
                "CREATED_BY": "DEV_MIGRATION_SMOKE",
            },
            file_rows,
            analysis.raw_rows,
        )
        prepared = True
        result = repository.commit_migration_batch(analysis.batch_id)
        raw_count = len(repository.get_migration_raw_rows(analysis.batch_id))
        expected = len(analysis.raw_rows)
        if raw_count != expected or sum(result["counts"].values()) != expected:
            raise RuntimeError("Migration reconciliation failed.")
        print(json.dumps({"batch_id": analysis.batch_id, "raw_rows": raw_count, **result}, indent=2, default=str))
    finally:
        if args.cleanup and prepared:
            repository.cleanup_synthetic_migration(analysis.batch_id)
            print(json.dumps({"batch_id": analysis.batch_id, "cleanup": "CLEANED"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
