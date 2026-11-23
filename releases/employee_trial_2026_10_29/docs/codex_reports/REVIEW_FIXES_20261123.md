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
