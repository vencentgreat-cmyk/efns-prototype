# Review fixes — 2026-11-23

Base: origin/main `cbee3a86ac1713a2bb0cf6040bf98fa3da22ce48`. Branch: `codex-review-fixes-20261123`.

## A — manual legacy-style leases

New Allocation forms omit Lease (In), Lease (Out), Lease In and Lease Out. Manual creation (`data/record_safety.py::create_once`) rejects these types server-side. The authorized direct upsert compatibility entry point joins the continuity transaction and applies the same new-record-only check (`data/manual_quota.py`). Permissions and the Developer Method=Lease route are unchanged. Existing stored legacy rows retain the old edit choices and may still receive note edits.

Writers deliberately unchanged: low-level Mock/Snowflake upsert methods (compatibility and internal setup/bulk callers), Daily Flock & Quota `import_operational_flock_quota_batch` / staged commit, original quota/flock bulk import, migration `_insert_migration_core` / `commit_migration_batch`, historical correction/supplement writes. These remain historical bulk paths, not the manual form boundary. No global transaction-type constant or common import validator changed. Authorized direct manual upserts are guarded even if they supply a new target ID.

Tests use synthetic records only, including a blocked 500 Allocation Lease (Out) against own quota 100, existing legacy note editing, and accepted historical Daily/Migration writes. Review dependencies installed in an isolated local environment. Full-suite results will be recorded after all six parts.
