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

## Part G: void a saved new-method lease

`LEASE_STATUS` is nullable: NULL retains the existing active behavior. Only a new-method Lease can be marked Voided. Allocation rows and historical Lease (In)/(Out) rows are refused by this action. Existing lease entry does not write the new field; setting a status while creating a lease is rejected. Ordinary lease edit/delete remain blocked, including clearing a Voided status. There is no undo action.

A saved lease's Summary exposes Void lease only to an application Admin and requires a reason. The existing authorized repository checks UPDATE_DATA plus the exact Admin role and supplies the actual actor. The data boundary also requires an Admin actor. No role permissions, authentication, sessions, connection or lock implementation changed.

The void writer reuses the existing continuity transaction, checks the reviewed version, checks the status column before writing, and verifies the update. It changes only LEASE_STATUS and the normal update timestamp. Mandatory Record History stores full before/after evidence, reason, recorder and UTC time; mandatory audit is inside the same transaction. An identical request/actor/reason is replay-safe; a different request against a Voided lease is refused. The operational list/detail and Record History picker show Voided; its history change type is also Voided.

`data/quota_leases.py::lease_active` excludes Voided records at the shared calculation entry point. This removes them from confirmed net/gross quota, quota history/transaction/lease reports, the hidden evidence-gated usage draft, and every Flock Age/Status/Producers Over Quota utilization caller. Original inventory math and legacy allocation rules are untouched. Tests compare every quota projection/export and representative Flock Age/Status/Producers Over Quota output with the pre-lease baseline after void.

### Dependency guard and assumptions

Voiding is a correction of the entire original period (including past report dates), not an early termination from today's date. To end a valid lease early requires a separately confirmed policy, not this action. Before voiding, check both parties at every effective-date/expiry boundary inside that original period. Reject newly negative or worsened negative quota caused by other saved transactions, including legacy outgoing leases or Sales. Also check overlapping new-method onward leases of the lessee against available quota for their whole periods with the candidate voided. Missing/contradictory state, unresolved positions or incomplete commitment evidence refuse the void rather than guessing. No dependent record is changed automatically.

The same existing lock serializes void and lease creation. A synthetic race test proves they cannot both succeed when the onward commitment needs the original lease. SQL executor tests verify void validation, status update and audit use the same owning executor. No live database behavior is claimed as tested.

Review `sql/34_quota_lease_void_20261119.sql` (also reflected in canonical `sql/02_core_tables.sql`):

```sql
ALTER TABLE EFNS_DEV.CORE.QUOTA_TRANSACTION
    ADD COLUMN IF NOT EXISTS LEASE_STATUS VARCHAR(20);
```

No DDL was run. Missing column refuses the void with a schema-update message and writes nothing; existing allocation and active-lease calculation continues with absent/NULL status. Existing quota UPDATE privileges are reused.

## Protected-area changes

| File | Scoped reason |
|---|---|
| `app/pages/1_Production_Import.py` | Remove intent prompts, enforce blocking errors and show replacement receipt/read-only evidence. |
| `app/services/authorized_repository.py` | Apply existing IMPORT_DATA to the new evidence readers and Admin/UPDATE_DATA to void only. |
| `data/repositories/production_replacement.py` | New producer-week backup/delete and scoped child rollback inside the existing import transaction; pure keys/validation remain in `data/production_replacement.py`. |
| `data/repositories/continuity.py` | Integrate replacement in staged production commit, expose evidence reads and the void bridge; lock code unchanged. |
| `data/repositories/mock.py` | Model backup-table availability and nullable lease status for offline tests. |
| `data/quota_lease_void.py` | New atomic, versioned, dependency-checked void and mandatory history/audit. |
| `data/quota_lease_persistence.py` | Reject status assignment on new lease creation so void cannot be bypassed. |
| `data/repositories/snowflake.py` | Add LEASE_STATUS to the existing quota field allowlist; allocation writer unchanged. |
| `app/pages/8_Quota_Transactions.py` | Present the scoped void action/Voided label on saved new-method leases. |
| `app/services/production_import_review.py` | Read-only replacement evidence and count summary; no writes. |
| `app/services/quota_lease_void_ui.py` | Admin-only reason entry and dispatch to the protected void method. |
| `app/services/revision_history.py` | Label Voided leases in the existing history picker; read-only. |
| `data/production_replacement.py` | Pure upload validation and exact producer-week keys; no private storage access. |
| `data/quota_leases.py` | Exclude Voided transfers through the shared active-lease guard; no other quota rule changes. |

Other changed services are read-only presentation and shared void-state calculation. No other write/transaction path changed.

## Validation and shipped bytes

Part F commit: `e8d6c33`. No dependencies changed; Streamlit remains pinned to 1.52.2 and the implementation uses existing APIs. Full combined suite results and the shipped-file proof follow below. All new fixtures are synthetic; no real farm/producer names, quantities, exports or legacy files were added. No Snowflake calls, DDL execution, deployment or PR.

The full-run architecture guard identified private production access in the first helper location. Persistence was moved into the repository layer; the pure module retains only validation/identity. The guard test was not weakened, and 59 focused tests including the guard passed after the split. The unpublished Part F commit was updated before Part G.

| Shipped file | Base SHA-256 | Final SHA-256 |
|---|---|---|
| `app/pages/1_Production_Import.py` | `2e53787bca9bf25f6cf52c8945a8273026de45254f60825c4eb02c94cbc275db` | `0a21b9616c4244305d6d9cadab1e461d5bc185e621dd69755b54ba17448e91eb` |
| `app/pages/8_Quota_Transactions.py` | `60b780a3f25f156c62d3f6b9f202022d692899788449eb6f58aa5128c4f4ea7a` | `0b7cd07fb31986ed502066ad412b5b4fedf1e21ec2e09aa06f721cc2642263a0` |
| `app/services/authorized_repository.py` | `fee29011c309c5563bc5ae5fd098900075fcd21dfc20daa0162303f712a52d76` | `9eb4b94af95a13d163131909adab2b770acc7e82dc27fbbd240a4fbdfe3940df` |
| `app/services/production_import_review.py` | `NEW` | `5d30566d1beccdc8b8b83bfcc94e3cd6ccc5b7eb5316206e18d923e804c0f9c2` |
| `app/services/quota_lease_void_ui.py` | `NEW` | `a18b502015b6f23d4baa043c17bf54342bfd43a33839b3cff555d1deef2221fa` |
| `app/services/revision_history.py` | `35e3ebc470f18c672652018c76eaeee50349f4add386dee7092191776468e30e` | `7c42e39095927a63b96d735268070bce41664ce2669967dd72f639157caef296` |
| `data/production_replacement.py` | `NEW` | `7793c2c61c51ff0ba08aedd83b34f31a9802a7290b06c8a8cf29c2a2dc253dad` |
| `data/quota_lease_persistence.py` | `42738cc97e8bb5fb1b045e35fb0c820e701e69bb1e0c50c9b098c9148fb97e70` | `19d92f3c515f2f51f060023471c9467f39f98b9d73d86b17e3cc0f093ac8466d` |
| `data/quota_lease_void.py` | `NEW` | `004f9fd54c248e6fa7b71c3522ef79ff15c10e62bb96fb860926bc1f9212de1b` |
| `data/quota_leases.py` | `3b01905f7b738df888fab8d85422a423e73b776e42e32247ecc71d9a6bbae7cb` | `23a8d49e87d7b9d27d602ac0f8af1245379428e9827956441179583c37458090` |
| `data/repositories/continuity.py` | `07ba5f44404e3d3ca8c680d897df6fb430fc64f8fe8f8fff660af3e0d3c3c99b` | `1348e04b4f5eeecec4d719992ee6065cc54e9becc43f5c354ced6f23c293b611` |
| `data/repositories/mock.py` | `029f40236fc40ac78a151c174f5dc4b87cfaa94369bd93f251282406d6130164` | `5d502bdef358c4ece88a96f1069c4bb6802e27fa9f880c7bf8c72b8b95f01e94` |
| `data/repositories/production_replacement.py` | `NEW` | `96f74f3b54f40a2b129382445c5ade9092f267adbbb8c8c7b38d9180a0331cc6` |
| `data/repositories/snowflake.py` | `4af1c3fcbeab77b5d6c13456442a1ea92f29ace076ec0c80c50d9c9e1621cd0e` | `f07116326603981201d8ec2408230032f542ed06670a6cd6fd69cd2e07a6e842` |

14 shipped paths changed/added; all 113 other shipped files are byte-identical; no shipped file was removed.

## Final verification

| Suite | Base | Final | Failed/errors |
|---|---|---|---|
| Release (Python 3.12) | 2,298 passed, 1 skipped | 2,334 passed, 1 skipped | 0 / 0 |
| Root (Python 3.11) | 706 passed | 706 passed | 0 / 0 |

Final release elapsed: 648.39 seconds. Final root elapsed: 120.17 seconds. All 36 new cases are synthetic. The four updated existing test modules are explained in Part F; no existing report calculation fixture or expected number was changed. The final manifest has 151 candidate LF SHA-256 entries, regenerated from actual final contents. The lock implementation/initialization, authentication, connection handling and unrelated shipped files are unchanged.

### Exact changed files (25)

- `DELIVERY_RUNTIME_DIFF_20261030.json`
- `app/pages/1_Production_Import.py`
- `app/pages/8_Quota_Transactions.py`
- `app/services/authorized_repository.py`
- `app/services/production_import_review.py`
- `app/services/quota_lease_void_ui.py`
- `app/services/revision_history.py`
- `data/production_replacement.py`
- `data/quota_lease_persistence.py`
- `data/quota_lease_void.py`
- `data/quota_leases.py`
- `data/repositories/continuity.py`
- `data/repositories/mock.py`
- `data/repositories/production_replacement.py`
- `data/repositories/snowflake.py`
- `docs/codex_reports/IMPORT_OVERWRITE_LEASE_VOID_20261119.md`
- `sql/02_core_tables.sql`
- `sql/33_production_replacement_backup_20261119.sql`
- `sql/34_quota_lease_void_20261119.sql`
- `tests/test_continuity.py`
- `tests/test_production_replacement.py`
- `tests/test_quota_lease_void.py`
- `tests/test_review_integrated.py`
- `tests/test_staff_workflows.py`
- `tests/test_v6_consistency.py`

The branch has two commits: Part F `e8d6c33`, and a separate Part G commit. No PR, deployment, Snowflake access or DDL execution. No real-data or legacy fixture files were added.

Outside the explicitly requested behavior, other producer-weeks, new-only valid import row values, exact-file retries, allocations, legacy lease types, stock/quota calculation rules and report formulas remain unchanged. A Void changes adjusted quota and utilization only because the explicitly corrected lease is excluded. The review-only DDL is `sql/33_production_replacement_backup_20261119.sql` (backup and narrowly required owner grants) plus `sql/34_quota_lease_void_20261119.sql` (nullable lease status); canonical `sql/02_core_tables.sql` includes that new status for fresh installations. Applying or restoring anything is a later reviewed operation.
