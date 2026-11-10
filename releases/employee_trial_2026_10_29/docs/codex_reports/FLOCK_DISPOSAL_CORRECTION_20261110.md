# Flock disposal correction review — 2026-11-10

Branch `codex-flock-disposal-correction-20261110`, based on `origin/main` b60e5da.
Only offline authoring, original fixture copies, tests and review artifacts are
added. No Snowflake command, connection, SQL execution, deployment or runtime data
change occurred. Existing branches/worktrees, mapping files, import logic,
repository writers, authentication and locking services are unchanged.

## Inputs and reproducible comparison

Original files are copied unchanged under `tests/fixtures/flock_disposal_correction/`:

- `Active Flocks 11-10-2026 11-48-38 AM.xlsx` — 2,197 data rows.
- `efns_custom_report (10).csv` — 2,219 rows.
- `flock_differences_legacy_vs_new.csv` — user's derived difference reference.
- `flock_current_report (2).csv` — existing local report observations used only by
  inventory regression tests; Counted/Count Date are not reverse-solved from Inventory.

A fixture-local `.gitattributes` disables line-ending conversion, preserving the
original input bytes and reproducible SHA256/plan IDs across platforms. The script
opens the workbook read-only, closes it, hashes both comparison inputs before and
after generation, and never writes either input. No source worksheet is authored.

Match `Permit Number` in the workbook to `Flock Number` in the app export. Exclude
a permit if duplicated on either side; never choose the first duplicate. Normalize
only comparison whitespace in Account names; preserve original copied data. Date
comparison uses the exported calendar date without timezone conversion.

| Comparison | Count |
|---|---:|
| Uniquely matched permits | 2,172 |
| Legacy rows excluded because of ambiguity on either side | 15 |
| New-system rows on ambiguous permits | 19 |
| Legacy rows with no matching permit in export | 10 |
| New-system-only rows (including the duplicate-only NF rows) | 30 |
| Estimated Disposal Date differences | 14 |
| Actual Disposal Date differences | 14 |
| Distinct flocks requiring disposal correction | 14 |
| Placement Date differences, intentionally unchanged | 12 |
| Hatch Date / Bird Count / Quota Type / Account differences | 0 / 0 / 0 / 0 |
| Matched flocks whose two disposal fields already agree | 2,158 |

The six duplicated legacy permits are 30133, 30171, 30193, 30348, 30355 and 40027.
The current export also duplicates 30157, 40055 and NF. All are excluded from
unique matching. The additional eight missing historical permits are 40205,
40162, 40137, 40092, 40043, 40003, 22444p and 22445p. They are reported only,
not created, corrected or used to expand the 14-row correction scope. These are
unmatched permit keys, not necessarily missing records: the source GUIDs of
22444p and 22445p are present in the app export under Flock Number NF. The other
six historical GUIDs are absent from that export. Both Bayview GUIDs (40407 and
30407) are absent as well as their permit keys. No live table was queried.

`comparison.json` contains exact input hashes, matching counts and workbook field
bindings. `comparison_differences.csv` lists the 17 uniquely matched rows with
any compared-field difference (14 disposal rows plus three placement-only rows).
`duplicate_permits.csv` and `unmatched_legacy_rows.csv` retain excluded-row evidence.

## Root cause and limits of attribution

The workbook's hidden Dynamics metadata explicitly identifies:

| Physical legacy field | Verified display meaning | Original V3 destination | Current disposal-R1 destination |
|---|---|---|---|
| new_disposaldate | Disposal Date (actual) | EST_DISPOSAL | DISPOSAL_DATE |
| new_disposaldate2 | Estimated Disposal Date | DISPOSAL_DATE | EST_DISPOSAL |
| efc_birdsdisposed | Birds Disposed | BIRDS_DISPOSED | BIRDS_DISPOSED |

**Confirmed general mapping bug in original V3:** the two date destinations are
reversed in `config/eims_migration_mapping_v3.json`. This is an entity-wide rule,
not a permit-specific condition. **The current mapping is already corrected:**
`eims_migration_mapping_v3_disposal_r1.json` explicitly overrides those bindings;
`eims_migration_mapping_v3_count_source_r1.json` retains the corrected date bindings.
`data/migration.py::load_mapping_for_version` intentionally resolves old batches
with their original version. `correction_mapping` supplies an explicit corrected
interpretation. Loading a revised JSON contract does not retroactively rewrite
committed CORE records. No further mapping change is justified or included.

Across the 2,172 matches, 1,781 legacy rows have distinct estimated/actual dates:
1,767 now agree with CORE, and 14 differ. Another 391 have equal legacy date
values and cannot independently identify which historical mapping was applied.
Eight of the 14 discrepancies are exact informative swaps; six also have an
absent/stale value in the estimated column relative to the current workbook.
All 14 current actual-column values equal the workbook's estimated dates.
Consequently it is incorrect to say all 2,172 stored rows remain swapped.
The files cannot identify the exact original batch, RAW payload or which repair
receipt applied to each row. Historical mapping plus source changes after the
migration/repair are possible together; retained RAW and repair receipts are
needed for complete per-row causal attribution. No git-history scan was used.

**Birds Disposed is not omitted by the mapping.** Both contracts map the correct
`efc_birdsdisposed` field. The existing date-repair repository's FIELDS contains
only EST_DISPOSAL and DISPOSAL_DATE, so a date-only repair does not backfill that
quantity. There are 1,825 nonblank legacy Birds Disposed values among the matched
rows, but the current export has no such column. It cannot establish whether any
of those current values are NULL, stale or already correct. We therefore do not
claim all missing quantities are a mapping failure. Only the eight user-specified
quantities on the 14 date targets are proposed; the pre-check must reveal their
current values. Six rows with blank legacy quantities keep their current quantity.

## Per-flock business corrections

Unknown old quantities are deliberately marked `<CAPTURE_FROM_BACKUP>`, never
assumed to be NULL or zero. `<UNCHANGED>` does not clear a field. The reviewed
correction CSV also declares UPDATED_AT as system metadata: its old value is
captured in the backup and its new value is the UTC execution timestamp. This
protects the application's optimistic-concurrency token without changing any
additional business field. Placement, Hatch Date, Bird Count, Account, Quota,
Status, flock events and transaction quantities are never assigned.

| Permit | Account | EST_DISPOSAL old → new | DISPOSAL_DATE old → new | BIRDS_DISPOSED old → new |
|---|---|---|---|---|
| 30368 | Bayview Poultry Farm Ltd. | NULL → 2027-01-05 | 2027-01-05 → NULL | Unknown (backup) → unchanged |
| 30371 | Mr. Christopher Eyking & Mr. Nicolaas Eyking | NULL → 2027-02-15 | 2027-02-15 → NULL | Unknown (backup) → unchanged |
| 30372 | Maritime Pride Poultry Inc. | NULL → 2027-03-29 | 2027-03-29 → NULL | Unknown (backup) → unchanged |
| 30374 | Cox Brothers Poultry Farm Ltd. | NULL → 2027-03-15 | 2027-03-15 → NULL | Unknown (backup) → unchanged |
| 30375 | Atlantic Poultry Incorporated | NULL → 2027-03-22 | 2027-03-22 → NULL | Unknown (backup) → unchanged |
| 40329 | Maritime Pride Poultry Inc. | 2025-11-09 → 2025-12-22 | 2025-12-22 → 2025-11-09 | Unknown (backup) → 73764 |
| 40346 | L. B. Meek & Son Farm Ltd | 2026-07-31 → 2026-07-16 | 2026-07-16 → 2026-07-31 | Unknown (backup) → 15985 |
| 40348 | Atlantic Poultry Incorporated | 2026-09-09 → 2026-07-27 | 2026-07-27 → 2026-10-06 | Unknown (backup) → 48820 |
| 40350 | Scotia Poultry Farm Ltd. | 2026-09-03 → 2026-07-30 | 2026-07-30 → 2026-09-03 | Unknown (backup) → 15356 |
| 40357 | 2405272 Nova Scotia Ltd. | NULL → 2026-10-12 | 2026-10-12 → 2026-09-24 | Unknown (backup) → 38108 |
| 40358 | Mr. Christopher Eyking & Mr. Nicolaas Eyking | NULL → 2026-10-15 | 2026-10-15 → 2026-09-24 | Unknown (backup) → 24052 |
| 40366 | 2405272 Nova Scotia Ltd. | NULL → 2026-11-30 | 2026-11-30 → 2026-09-24 | Unknown (backup) → 5196 |
| 40369 | Six Maples Farm | 2026-10-05 → 2026-11-30 | 2026-11-30 → 2026-10-08 | Unknown (backup) → 1851 |
| 40375 | Atlantic Poultry Incorporated | NULL → 2027-03-22 | 2027-03-22 → 2027-05-27 | Unknown (backup) → unchanged |

## Rows deliberately not changed

All 12 placement differences are treated as the user-confirmed legacy export
timezone artifact. Original timestamps remain in the copied workbook; the script
reports calendar differences and makes no placement assignment or hatch-based
estimate. No account, quota, hatch date or Bird Count discrepancy was found in
the uniquely matched cohort.

The following missing workbook rows are **listed only**. Their complete original
23 source columns plus SOURCE_EXCEL_ROW are in `unmatched_legacy_rows.csv` and the
unchanged workbook. No INSERT or quota/account inference is generated.

| Excel row | Permit | Account / registration | Quota type | Facility | Placement | Birds |
|---|---|---|---|---|---|---:|
| 11 | 30407 | Bayview Poultry Farm Ltd. / 7038 | Non Commercial Pullet Quota | 7038 - P | 2027-01-19 01:00:00 | 11,000 |
| 12 | 40407 | Bayview Poultry Farm Ltd. / 7038 | Egg Production | 7038 - 2 | 2027-01-19 01:00:00 | 11,000 |

Both have Hatch Date 2026-09-08, Estimated Disposal Date 2028-01-18, blank actual
disposal and Active status. The workbook supplies quota types, not CORE QUOTA_IDs;
no new quota relationship is invented. Their missing zero-inventory future rows
do not change the expected current provincial Inventory total.

## Generated review artifacts

Directory: `sql/review/flock_disposal_correction_20261110/`.

- `corrections.csv`: 14 identities, expected exported old dates, proposed new dates,
  eight proposed Birds Disposed values, explicit unknown/unchanged markers,
  declared UTC version-token metadata and a FLOCK_ID lookup keyed by permit AND
  Account ID AND the exported Flock ID. A live ID mismatch is never silently used.
- `precheck.sql`: SELECT-only; lists all 14 current date/quantity/version values,
  proposed values, identity match and match count per permit+Account. **This is
  the next review step. Send its result for confirmation before running apply.**
- `apply.sql`: guarded SQL text only. It first rejects an existing transaction
  and unset actor placeholders. It creates
  `EFNS_DEV.CORE.FLOCK_BACKUP_20261110 AS SELECT f.*` only if absent, then starts
  the DML transaction. The backup is full-column and never replaced, truncated
  or refreshed on rerun. It preserves the genuinely old Birds Disposed values.
- `rollback.sql`: restores only each row's changed business fields from the
  backup by FLOCK_ID. It also advances UPDATED_AT, rather than reviving an old
  concurrency token. It does not overwrite unrelated later business edits.
- `verification.sql`: SELECT-only post-check, also safe as another pre-check.

### Guards, transaction and history convention

The backup must contain exactly 14 rows and one of every reviewed identity.
Each live permit+Account must resolve to exactly one row, and that row must match
the exported FLOCK_ID. Expected old date values are checked against the backup.
The UPDATE compares all three disposal fields and UPDATED_AT with the backup;
a change after backup causes a zero-row update and aborts the entire DML batch.
Every UPDATE and mandatory history/audit INSERT immediately captures SQLROWCOUNT
and requires exactly one affected row. Any failure rolls back all DML in the block;
the pre-transaction backup remains for diagnosis.

CTAS is deliberately before BEGIN TRANSACTION because Snowflake DDL commits an
active transaction; see [Snowflake transactions](https://docs.snowflake.com/en/sql-reference/transactions).
The generator captures SQLROWCOUNT immediately before any intervening SELECT,
as required by the current [DML status semantics](https://docs.snowflake.com/en/developer-guide/snowflake-scripting/dml-status).
No SQL was submitted to Snowflake to validate syntax or execute these artifacts.

Direct SQL does not automatically call application revision services. The script
therefore includes equivalent append-only inserts into APP.RECORD_REVISION and
APP.AUDIT_EVENT, in the same DML transaction, for **every changed FLOCK**. These
use complete before/after snapshots, full nine-digit UTC UPDATED_AT tokens,
ENTITY_TYPE FLOCK, ENTITY_ID FLOCK_ID, reason, authenticated app actor UUID/email
provided by the reviewer, UTC timestamps and UPDATE audit action. Change kinds
follow the existing date-repair convention: MIGRATION_DATE_MAPPING_CORRECTION /
MIGRATION_DATE_MAPPING_REVERSAL. Record History projects these snapshots normally.
The operator must choose a real app actor identity; placeholders refuse execution.

Stable plan-specific revision/audit UUIDs make exact reruns no-ops with no duplicate
history. A receipt without its matching audit, or a current row no longer matching
the recorded after-state, raises an exception instead. Rollback requires the apply
receipt and verifies that the backup still matches its recorded before-state.
It refuses to overwrite edits made after apply. Repeating rollback checks its own
receipt/after-state. Reapplying the same plan after rollback deliberately refuses;
a newly reviewed operation is needed, not deletion of append-only receipts.

**Workflow gap:** these are reviewed DBA scripts, not an app operation. They do not
acquire app leases/record locks, create RAW migration/date-repair batch receipts,
or call lifecycle/end-event services. Pause staff writes and close editors for the
reviewed maintenance operation. Timestamp and field compare-and-set checks guard
races after the snapshot, and version advancement prevents stale app saves.
Do not attempt to undo this through the app's RAW-backed date-repair receipt UI;
use the matching generated rollback script. No protected service was changed.

### How to generate (offline, release-directory working directory)

```powershell
python scripts/generate_flock_disposal_correction.py `
  --legacy "tests/fixtures/flock_disposal_correction/Active Flocks 11-10-2026 11-48-38 AM.xlsx" `
  --flocks "tests/fixtures/flock_disposal_correction/efns_custom_report (10).csv" `
  --output "sql/review/flock_disposal_correction_20261110"
```

Defaults expect exactly 14 corrections and stop if input scope changes. Original
input hashes and the deterministic plan ID appear in comparison.json. Generated
SQL is intentionally blocked until `--actor-id <reviewed app UUID>` and
`--actor-email <reviewed app email>` are supplied to regenerate it (or the exact
placeholders are reviewed and replaced in both SQL files). Generation only
writes local files; it has no connector import, network client or execute-SQL option.
All SQL documents are validated before any output is written. SQL dollar-quote
delimiters in values and unsafe identifiers are rejected. Input hashes are taken
before parsing and rechecked before writing; a change detected before writing,
or SQL validation failure, leaves an existing reviewed plan untouched. A final
hash check also detects changes during physical output writing; if that check
fails, discard the output set and regenerate from stable input copies.

### How to apply / verify / roll back later (description only)

1. Review comparison.json, the 14-row CSV and original source rows. Run only
   precheck.sql in Snowsight and return the current-field output for confirmation.
2. After confirmation, review actor identity, expected EFNS_DEV account/schema,
   CREATE TABLE/UPDATE/SELECT and history INSERT privileges, and pause staff writes.
3. Run the apply block standalone. Retain its full backup and both history/audit
   receipts. Any guard failure requires investigation; never replace an existing
   backup or remove history to bypass a guard.
4. Run verification.sql. Confirm row matches/IDs, dates and the eight quantities.
   Export the reports with the same date/mortality parameters.
5. To reverse a confirmed apply, review and run rollback.sql standalone. It reads
   the existing backup, refuses intervening edits and appends inverse history/audit.
   Verify against the backup's old business values. Keep the backup after rollback.

## Expected report outcome and fixture tests

With the unchanged shared builders at Egg Production, report date **2026-11-10**,
mortality **0.4**: exported observations and current FLOCK fields reproduce
**1,059,266 Inventory Birds** before correction. Applying the proposed values to
**copies of fixtures only** produces **1,052,229**, excludes 40366/40369, creates no
flocks and preserves all placement values. The remaining **143 below legacy
1,052,372** is account 7168's newer 2026-11-03 Count snapshot gap; it is not patched.
The correction branch does not change any inventory formula, report filter,
confirmed quota rule, import mapping, account or transaction data.

Tests compare all seven requested fields across 2,172 matches, mapping metadata,
all 14 target identities/eight quantities, duplicate exclusions, original-input
hashes, deterministic regenerated artifacts, SELECT-only pre-checks, SQL field
scope, backup-before-DML ordering, per-statement counts, append-only receipts,
rollback snapshot/version guards, SQL literal/comment/delimiter escaping,
changing-input rejection before output, and the expected
inventory result with the real pure builders. SQL checks are offline structural
checks, not a claim of live database execution or server-side SQL compilation.
