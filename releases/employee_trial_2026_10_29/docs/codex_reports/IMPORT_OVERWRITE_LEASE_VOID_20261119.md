# Production replacement and lease void - 19 November 2026

Base: fetched main `8b1f3ee`, containing Task 2 `5e1fea3`. Isolated branch: `codex-import-overwrite-lease-void-20261119`.

## Import before this change

`app/pages/1_Production_Import.py` checks exact file bytes with FILE_HASH. `data/production_intake.py::prepare_workbook` derives PRODUCTION_ID from SOURCE_FILE_ID + original sheet row number. `data/repositories/continuity.py::commit_staged_production` checks staged review evidence and requires `new_observations_confirmed=True`; it then appends rows. There is no producer/week replacement check. The page asks for independent-new-observation confirmation and a validation-review checkbox; leaving either unchecked disables the import. There is no separate replacement Cancel action: abandoning the page leaves the original/RAW staged and CORE unchanged.

The old implementation can commit technically valid rows while other source rows are invalid or unmatched. It checks duplicate source-row identities but has no exact-business-row duplicate rejection. Those differ from the requested all-valid, uniquely matched upload. This task explicitly blocks such uploads at both preview and server commit, while retaining original RAW and validation messages for review. Multiple *different* detail rows for one producer/week remain allowed; only identical business rows are duplicate errors.

## Confirmed replacement key and plan

The replacement key is canonical Producer Account ID + production week (SOURCE_WEEK_CODE, falling back to REPORTING_YEAR/REPORTING_WEEK for older rows). Existing unlinked source numbers are resolved only with the existing exact identity helper. No name/fuzzy match is introduced. All records in an uploaded producer-week are replaced as one set, irrespective of grader, barn, colour or size; other producer-weeks remain unchanged. Exact-file replays remain idempotent rather than overwriting newer work again.

The existing continuity transaction/lock is reused without changes. Before deleting an old CORE row, retain all old values and its size-breakdown children in RAW.PRODUCTION_REPLACEMENT_BACKUP. Keep RAW originals, source matching decisions and revision history as historical evidence. Refuse replacement when backup schema/permissions are unavailable; a new-only import does not access that table. The new summary persists in batch metadata; a read-only batch viewer supplies old values. No restore button.

Part F and Part G implementation, assumptions, review-only DDL and verification follow below after completion. No Snowflake calls, DDL execution, deployment, PR or real-data files.

## Part F implementation and assumptions

- Overwrite key: exact-resolved canonical Producer Account ID + source production week; source week takes precedence over reporting year/week fallback. Case/whitespace normalization uses the existing exact identity helper. Different details for the same key are retained as an uploaded set; identical normalized business rows are rejected. Unknown producers and any blocking error refuse the whole commit. Existing non-blocking warnings stay warnings.
- The explicit Import button remains; both intent/review checkbox prompts are removed. Refreshing stale producer matching remains a validation review, not overwrite approval. Exact committed file hashes remain replay-safe, returning the original receipt instead of superseding a newer batch again.
- Old rows and their size breakdowns are backed up before deletion, in the existing owning transaction. Raw source/matching decisions and previous revisions remain historical evidence referencing the backed-up Production IDs. Child size rows are removed with their old parent; replacement workbook quantities stay in the same existing CORE fields. No orphan size rows are introduced.
- The mock's existing transaction already snapshots production/history. A scoped copy restores the size-breakdown frame on failure because that frame was not part of the old snapshot; no lock implementation or other write path is changed.
- Summary labels distinguish uploaded rows for new keys (`rows_inserted`), old removed/backed-up rows (`rows_replaced`), total uploaded rows saved (`rows_written`), untouched old rows (`rows_unchanged`), and replaced key count/minimum-to-maximum week. The displayed range can have gaps. Exact-file retries show the original persisted summary.
- Batch metadata stores the summary without a new summary table. Replacement also writes mandatory Record History and an audit event in the same transaction. The read-only viewer is limited by the existing Import Data permission and selects backups by a bound batch ID. There is no restore action.

### DDL and restore review

Review `sql/33_production_replacement_backup_20261119.sql`: new RAW.PRODUCTION_REPLACEMENT_BACKUP, full old values/size children in VARIANT, batch/producer/week, recorder and UTC time. SELECT/INSERT on the backup plus DELETE on CORE.PRODUCTION_RECORD and SELECT/DELETE on CORE.PRODUCTION_SIZE_BREAKDOWN are review-only app-owner grants required for replacement. Application permissions are unchanged. No DDL is run. Missing table/access blocks replacement before deletion, while new-only uploads do not need the table.

Restore would require a separately approved, atomic, audited correction: review whether later batches/manual edits superseded each target producer-week; back up its current set; replace only those reviewed keys from OLD_VALUES and SIZE_BREAKDOWN_ROWS with explicit type casts; preserve source/match history; record the restore batch and actor. Blindly inserting backup rows could duplicate later records, so no restore SQL/button is invented.

Existing tests updated deliberately: `tests/test_continuity.py` now asserts invalid whole-file blocking and retries a separate valid source; `tests/test_v6_consistency.py` replaces the obsolete independent-observations expectation with producer-week replacement/backup; `tests/test_staff_workflows.py` uses a valid YYYYWW and asserts full set replacement; `tests/test_review_integrated.py` verifies re-review cannot bypass unresolved/invalid source rows. Their original evidence, rollback, identity and matching checks remain.

Part F focused regression tests passed before its commit; full combined counts follow after Part G.
