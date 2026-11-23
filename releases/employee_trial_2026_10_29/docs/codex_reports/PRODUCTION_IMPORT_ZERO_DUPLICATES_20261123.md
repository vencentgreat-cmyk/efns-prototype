# Production Import zero-only duplicate validation — 2026-11-23

Base: origin/main `99f6402a9ed26d7eec2152de89a5fabcfd5464fe`.
Branch: `codex-production-import-zero-duplicate-20261123`.

## Change

Production Import keeps identical rows when every production quantity is blank or zero. Each row keeps its own Excel source row number, RAW row and normalized record. A non-blocking warning lists all source rows in each duplicate group, including the first. Any non-zero quantity retains the existing blocking duplicate message. Blank/zero equivalence is used only for classifying zero-only warnings; input values are not rewritten.

Quantity fields follow the maintained production decimal fields, including sizes, nest-run bands, totals and optional net-weight/box quantities. Account IDs, week/year, flock age and source row numbers are not quantities. Invalid nonblank quantities do not qualify for this exemption.

## Scope and identity

- `data/production_replacement.py::upload_errors`: used by Production Import preview and again by the existing locked commit path in `data/repositories/continuity.py::commit_staged_production`.
- `data/production_intake.py::prepare_workbook`: adds the warning to the existing warning list; the existing page displays it and counts it as a warning, not a blocking error.
- Daily Flock & Quota Import uses independent checks in `data/flock_quota_import.py`; Migration Import uses independent source-key/GUID handling in `data/migration.py`. Neither shares this duplicate check or changes.
- Production and RAW identities already use deterministic UUID5 keys from file ID plus Excel source row ordinal (`efns:<file_id>:<ordinal>` / `efns:raw:<file_id>:<ordinal>`). Identical content on different rows cannot collide. No identity change was needed.
- Existing producer/week replacement backs up every old row and its children. Exact-file retry returns the saved import and row count without inserting, replacing or backing up again. Synthetic tests cover distinct-file replacement including all zero rows, preservation of other producer/weeks, and exact-file retries.

## Validation

Synthetic workbooks are built in memory only; no real data or workbook files were added. Tests cover four-row White/Brown pairs, three identical zeros, separate producers/weeks, blank/zero cells, every maintained numeric quantity, non-zero rejection, per-row RAW/CORE identity, mock replacement/backup/retry, offline Snowflake insert bindings and both UI entrypoints.

Report calculation modules are unchanged. Synthetic comparisons exercise all four Production Management layouts in both Dozens and Boxes and Nest Run: added zero detail rows do not change producer/week/grader/grand totals or production measures. Existing legacy fixture tests remain unchanged.

Focused validation: 88 passed. Full release suite: 2,463 passed, 1 skipped, 0 failed, 0 errors (Python 3.12). Root suite: 706 passed, 0 skipped, 0 failed, 0 errors (Python 3.11). Existing fixture expectations were not edited. The regenerated manifest contains 164 candidate hashes.

Changed runtime files only: `data/production_intake.py`, `data/production_replacement.py`. Repository persistence, SQL, authentication, connections, locks, report calculations and exports are unchanged. Manifest regenerated from the base manifest with LF-normalized candidate hashes, retaining all existing entries.

## Shipped-file proof against base

Git-tree/LF text hashes (binary assets compared unchanged): 131 shipped files checked; 129 unchanged. Only the following differ.

| File | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| `data/production_intake.py` | `3df4810b197aee1047a55b1ba75511166e34b92047e7d4cc03e0067820d97683` | `a4599c6f72f16d2adc82ecf4b54c6682181879c497a0f70d5ff8c460aa780fac` |
| `data/production_replacement.py` | `59a60fb1c1c209a2d968824db01c9884324f75b67ac34828fac42ffae4755396` | `6d80a6cf7f5a8709fa66f362509b8049f58a909afdf7e6ad55244f6ab1d4330a` |
