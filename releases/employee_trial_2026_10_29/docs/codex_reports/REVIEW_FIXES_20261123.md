# Review fixes — 2026-11-23

Base: origin/main `cbee3a86ac1713a2bb0cf6040bf98fa3da22ce48`. Branch: `codex-review-fixes-20261123`.

## A — manual legacy-style leases

New Allocation forms omit Lease (In), Lease (Out), Lease In and Lease Out. Manual creation (`data/record_safety.py::create_once`) rejects these types server-side. The authorized direct upsert compatibility entry point joins the continuity transaction and applies the same new-record-only check (`data/manual_quota.py`). Permissions and the Developer Method=Lease route are unchanged. Existing stored legacy rows retain the old edit choices and may still receive note edits.

Writers deliberately unchanged: low-level Mock/Snowflake upsert methods (compatibility and internal setup/bulk callers), Daily Flock & Quota `import_operational_flock_quota_batch` / staged commit, original quota/flock bulk import, migration `_insert_migration_core` / `commit_migration_batch`, historical correction/supplement writes. These remain historical bulk paths, not the manual form boundary. No global transaction-type constant or common import validator changed. Authorized direct manual upserts are guarded even if they supply a new target ID.

Tests use synthetic records only, including a blocked 500 Allocation Lease (Out) against own quota 100, existing legacy note editing, and accepted historical Daily/Migration writes. Review dependencies installed in an isolated local environment. Full-suite results will be recorded after all six parts.

## B — delivery completeness

The artifact count is now derived from snowflake.yml globs (132 on base main; 133 after A adds the manual-entry helper). The missing Accounts page is registered. The guard checks every shipped source against the immutable baseline canonical repository bytes (LF for text; raw bytes for binary assets), or requires a matching runtime-diff entry. All diff sections are checked, not only runtime_changes. Binary artifacts additionally carry a raw SHA-256. Synthetic negative tests prove that unregistered modified/new files and incorrect hashes fail. Eight guard tests passed. Later parts regenerate the actual count if another runtime module is added. No runtime calculation changed.

## C — Flock Summary week in progress

Friday remains the planned day, but the actual snapshot is min(Friday, today in America/Halifax). Capped rows carry an As-of Note column with "as of today (week in progress)" and the actual date in screen/CSV/XLSX/PDF. Completed-only reports keep the existing columns and values; in mixed reports their new note cells are blank. Explicitly selected future weeks also cap at today (even before their Sunday start), following the stated all-future-Friday rule rather than inventing a different future-week policy. There is still no sum across weeks. The shared caption/catalog explain the cap. Forty-seven focused tests passed, including past/current/future/Friday/Saturday/year-boundary cases and exports.

The review requirements are installed locally and pip check passes. lxml was installed locally for root legacy-HTML workbook tests; no runtime requirement file was changed.

## D — authorization coverage guard (tests only)

The test enumerates every public method on BaseRepository plus each concrete repository, and checks that the proxy returns an authorized wrapper rather than passing the original callable through. Read-prefix and explicit write rules remain unchanged. A synthetic new unguarded writer is proven to fail the guard; no repository method body is invoked. Three tests passed.

Current exact pass-through allow-list:

- preview_historical_corrections — read-only preview.
- check_facility_history — read-only validation.
- check_facility_ownership — read-only validation.
- check_flock_reference_change — read-only validation.
- append_operational_flock_revision — append-only history used inside guarded import writes.

No runtime authorization or permission change was made for D. The A manual-upsert routing change enforces entry validation after the existing permission check; it does not change roles/permissions.

## F — retrospective report acknowledgement

Past-date partial returns, early ends and voids remain permitted, but require an explicit checkbox and server-side reports_confirmed=True. The existing transactional audit records required/confirmed flags, business date, confirming actor and timestamp; other audit calls retain their existing contents. Confirmation is bound into the action request fingerprint only when true, preserving previous false/default retry fingerprints. No amount/date eligibility rule or existing void dependency check changed. Sixty focused tests passed, including UI/server enforcement, today/future actions, audit contents and exact retries.

Conservative confirmation-date choice: early end uses the selected inclusive New Quota End Date (so a past selected end warns even if the first changed day is today); its existing effective next-day rule is untouched. Partial return uses Return Date. Void uses original Start Date because it corrects the whole original period. Checkbox state resets when quantitative adjustment inputs/date change.

Protected-area files for F: data/quota_lease_adjustments.py and data/quota_lease_void.py enforce/store the acknowledgement; data/repositories/continuity.py forwards the optional flag; data/record_safety.py adds the optional audit detail only for these calls. Authentication, connections and lock implementation are unchanged.

## E — protect lease capacity from later manual Allocation changes

Manual create_once, revise_entity and delete_with_history now evaluate prospective quota state under their existing continuity transaction before writing. Authorized direct manual upserts use the same protected boundary. Notes-only edits skip the capacity check. Source registration changes check both old and new owner/type contexts. No implementation of authentication, connections or locks changed.

The confirmed quota resolver is reused. The existing lease-creation capacity filter was extracted unchanged into own_quota_capacity_rows and shared: incoming new-method and historical leased-in quota is excluded. All non-voided, Active outgoing leases of the owner/type are considered over their effective periods, including historical and future periods. Early ends/full returns shorten those periods; partial returns change daily amounts through the existing adjustment resolver. The guard sweeps allocation effective dates, lease start/end/expiry boundaries, Base dates and adjustment effective dates. Quota position is constant between these boundaries, so this checks every covered day without iterating decades of individual days. The first failing date reports the shortfall and overlapping lease IDs, with instructions to end/reduce/void first. Unverifiable state/evidence fails closed.

Only the owner/type is read, through the owning tx executor: source QUOTA_REGISTRATION by QUOTA_ID; registrations by quota-type aliases; owned QUOTA_TRANSACTION rows joined to registrations of those aliases; bounded RAW.MIGRATION_RAW_ROW state lookup; and the existing bounded RECORD_REVISION adjustment lookup. The RAW/history reads are skipped when no non-voided new-method outgoing lease exists, preserving legacy-only/schema compatibility. No new SQL write or DDL was added for this check.

E does not wrap void/end/return actions; they retain their existing dependency/eligibility checks and increase the lessor capacity normally. Terminate Quota remains the confirmed zero effect; it is not reinterpreted as setting quota to zero, and the old new-manual-type restriction remains. Safe decreases and Sales effective after the adjusted lease period are allowed. A different owner/type is unaffected. Eighty-six focused lease tests passed, including mock and offline two-session Snowflake races in both orderings.

### Deliberate bulk gap (A and E)

Daily/staged operational imports, migration commit/insert, historical correction and supplemental bulk writers are unchanged and do not call these manual guards. Their low-level unwrapped repository upserts/inserts remain compatible with historical records. Quota Registration editing is also unchanged: this request protects Allocation transaction changes, not registration lifecycle/type changes. They can therefore introduce/reveal an invalid leased capacity; this is an explicit requested gap, not a database constraint. Subsequent quota-affecting manual changes fail closed while a covered period is negative. Staff-facing create/revise/delete and authorized direct manual upsert routes are protected. No report/position resolver rule or stored record was rewritten.

Protected-area files for E: data/record_safety.py adds QUOTA_TRANSACTION-only guards inside the existing create/edit/delete boundary; data/manual_quota.py invokes the same guard for the authorized direct manual upsert path; new data/quota_allocation_capacity.py holds bounded read evidence and prospective validation; data/quota_leases.py only extracts the unchanged capacity-row filter for reuse. The original continuity-lock function is unchanged.

## Final validation

Full release suite: 2,538 passed, 1 skipped, 0 failed, 0 errors (13m20s). Full root suite: 706 passed, 0 skipped, 0 failed, 0 errors (1m51s). Both ran on Python 3.12 in the isolated review environment with the documented standard XML writer setting. Final manifest: 183 candidate hashes; candidate_artifacts: 135. All added tests/data are synthetic. No real data, Snowflake calls, DDL, deployment or PR. Code/report numbers are unchanged except the requested capped Flock Summary snapshot, rejected manual writes and retrospective-confirmation metadata/UI. The manifest is regenerated from base main and expanded globs; final counts will follow.

### Reproducible test environment

Python 3.12, requirements-review.txt installed into the task-local virtual environment; pip check passes. The optional lxml package was added for root workbook tests. Its presence switches openpyxl to an accelerator that made the existing synthetic migration generator emit an unbound xsi namespace. With OPENPYXL_LXML=False, openpyxl uses its standard-library writer and the 25 migration tests pass without changing runtime code, input data, parser strictness or expected values. Full suites are rerun with PYTHONUTF8=1 and OPENPYXL_LXML=False. The earlier accelerator run was aborted after identifying the setup failure and is not counted as a passing validation.

## Shipped-file proof

Expanded artifacts: 135 (132 on base main plus three new helpers). Compared with base Git-tree bytes, with LF-normalized text and raw binary assets: 120 unchanged, 12 modified and 3 new. The continuity-lock implementation was independently compared and is unchanged.

| Runtime path | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| `app/pages/8_Quota_Transactions.py` | `de513832417025d5ea45e649fbe4eb5fd7c5772bef33de72344232a35fc9b172` | `647649c21c64c71a4f030e3798140be8a0d17e2ebae2cb0e06c1a0b6ecbc9e6f` |
| `app/services/authorized_repository.py` | `1a3893e7504d893410fa67eaf68b3132a81d7c36a582375d55ec789326edfd75` | `91202b32251cfc5c9ac3ebdffbba4513d543724c03ad41fecd3d0554ace6868f` |
| `app/services/flock_summary_report.py` | `d3d288e747d7af9c9dbef4c597b954eeff1bac29a27c47513f9989b00bcf617f` | `88435548cd738ab8c876f3a651588da0c51e16330f851c9c38d5b452b4b88d93` |
| `app/services/quota_lease_adjustment_ui.py` | `447cc3177fdf82574e08598b1c4d5ea76c0e51130d82d4b46cac902059a6932e` | `a68158b2d6b7ff004fec22ba003452d476bd2528aef6471d888921b4b54e5e1e` |
| `app/services/quota_lease_void_ui.py` | `a18b502015b6f23d4baa043c17bf54342bfd43a33839b3cff555d1deef2221fa` | `b369709db16d667de361782c21befb85b2d0579a43578831cd87a83f386083a8` |
| `app/services/report_center.py` | `b7a3af568a4061637be6bc6a076e3579e752cf7c81718592f0c768b25ac7a4af` | `39fb22ea9cc760fee81172e1ea34a9234bd42609b9691f9d830b8b62fee092c2` |
| `data/efc_calendar.py` | `c4ef27c804ddc514563d4399e8d687cd4c5242fdc6da397eba7f21e9d7ba2760` | `46dd486d5f3fababc6f641df1c48ee35aebb4b1c030face74da6f7ae6ec3047d` |
| `data/lease_confirmation.py` | `new` | `4f2f1aac55994997321e191ee525f4a90ce13370d0b15e19745092f0663aa1ed` |
| `data/manual_quota.py` | `new` | `a2c8c41f2a286f5351597f3d7982cb5e6287a750668de4b7452bce26e4be9965` |
| `data/quota_allocation_capacity.py` | `new` | `018dbf8f0f7909294bc56db893d27b9c25d6c7789b5486d27ed71b9b22ba87a0` |
| `data/quota_lease_adjustments.py` | `811b1ed854d5b530472e109f1f4f1ea93751eea64d568d197fc9dba867a2baf8` | `37e3770eaba69b64cd341418d45e593c4f06e3101001ee1b10d241a0806749ed` |
| `data/quota_lease_void.py` | `fc9da7a324e0655790d69e09d8bc0f528dad6c0ff43c70623cb67a57a94b4251` | `61be0fa3485ca1798109ee24b298d7e2e1bba51cfd9f35609b0411af3e0113e5` |
| `data/quota_leases.py` | `e470c250e09a8d1844bdf819428aaed0caf281778f036ba806f10069e4cac44a` | `ba1ad2aaeb1acb0fa3733b99c8c058795580ce0fb7361896dac1504922f3e260` |
| `data/record_safety.py` | `aa9b8eb097b6e4ccc753dc0cce8be95da18b43401882a1953fa06ae4dfdfd65a` | `28a399d34d13a475a5ff10b30d4625793f2d2dac384c516b61d621c7638a0b0b` |
| `data/repositories/continuity.py` | `5419eaa9b6229148943e279eee9cefc69babae22d1de748e258012dfe1ab8d23` | `9a58e24f8f05b4d45be08aebefd94ee455d2f625a47578b48b31c73c68b73cf1` |

## Complete changed-file list

All paths below are relative to releases/employee_trial_2026_10_29/.

- `DELIVERY_RUNTIME_DIFF_20261030.json`
- `app/pages/8_Quota_Transactions.py`
- `app/services/authorized_repository.py`
- `app/services/flock_summary_report.py`
- `app/services/quota_lease_adjustment_ui.py`
- `app/services/quota_lease_void_ui.py`
- `app/services/report_center.py`
- `data/efc_calendar.py`
- `data/lease_confirmation.py`
- `data/manual_quota.py`
- `data/quota_allocation_capacity.py`
- `data/quota_lease_adjustments.py`
- `data/quota_lease_void.py`
- `data/quota_leases.py`
- `data/record_safety.py`
- `data/repositories/continuity.py`
- `docs/codex_reports/REVIEW_FIXES_20261123.md`
- `tests/test_authorization_proxy_coverage.py`
- `tests/test_daily_entry_boundaries.py`
- `tests/test_delivery_package_guards.py`
- `tests/test_delivery_transaction_choices.py`
- `tests/test_flock_summary_friday.py`
- `tests/test_review_allocation_capacity.py`
- `tests/test_review_lease_confirmation.py`
- `tests/test_review_manual_leases.py`
- `tests/test_review_week_in_progress.py`
