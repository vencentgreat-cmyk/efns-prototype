# Task 5: Flock Summary and lease adjustments

Base: origin/main a4b0e35 (Task 3 merged); separate worktree and branch codex-flock-summary-lease-adjust-20261120. No live Snowflake, deployment, operational DDL or real-data files.

## Initial findings

- Migration parse_reporting_period splits YYYYWW; production_week uses REPORTING_YEAR*100+REPORTING_WEEK. Mapping v3 maps efc_productionweek to SOURCE_WEEK_CODE and EFCYear/EFCWkNumber to the calendar. No inconsistent date/ISO-week derivation is used for these report codes. Historical CYYWW remains an explicit supported legacy format, unrelated to EFC date resolution.
- Existing get_efc_dates reads CORE.DIM_EFC_DATE. The new resolver validates complete Sunday-Saturday weeks; Saturday is the inventory date, never a sum over time. Mock calendar is explicitly synthetic, not a new production calendar rule.
- Admin and Data Editor currently have CREATE_DATA; Developer does not. Part I requires a lease-only authorization route, preserving all other permissions and Admin-only void.
- Details currently includes positive legacy Lease (In) and omits legacy Lease (Out); legacy types/values must remain unchanged. New-method leases currently contribute only incoming amounts to Details.

## Part H

Flock Summary reuses Flock Status inventory for each EFC week end. Stock is never summed over weeks. Grouped rows use stable Account identity internally, then show Account and registration labels. Known inventory totals follow existing Status handling; unavailable values remain a dash and are disclosed. Quota-type columns are exhaustive for eligible types in the input, including an explicit Not specified category; Special Permit remains excluded exactly as Flock Status. Non-selected type columns show zero. Weeks without included flocks have no row.

Production resolves dates only from the maintained calendar; the synthetic mock fixture is generated for adjacent local years and is not evidence of any unexported production calendar dates. Empty/unknown calendars display a clear message. CSV retains the data columns; XLSX Notes and PDF include the Saturday caption.

Part H focused validation: 463 passed (builders, Report Center, all report smoke cases and PDF exports). No existing report fixture values were edited. Final full suites follow Parts I/J.

## Part I: append-only daily lease adjustments

No DDL is needed: APP.RECORD_REVISION already has CHANGE_KIND, ENTITY_ID, BEFORE_DATA/AFTER_DATA VARIANT and audit fields. New Ended early / Partial return revisions retain the original lease row and carry typed effective dates/amounts in a private JSON evidence key. Record History shows plain change types and named return/end fields; the lease detail shows the adjustment list and current end. Mandatory history is verified exactly once and mandatory audit is inserted inside the existing continuity transaction. An audit/history failure rolls back both. A deterministic receipt makes same-request retries idempotent; stale versions or adjustment IDs require reload.

The new read is one bounded query per transaction result containing new-method leases, filtered by their IDs, ENTITY_TYPE and the two change kinds. No leases means no extra history read and no added metadata column. Unreadable/malformed adjustment history fails closed instead of assuming the original amount. Snowflake save/void evidence reads pass the owning transaction to the same history reader. No new connection/session/lock implementation is introduced.

Availability is confirmed owned allocations/Base less eligible legacy outgoing leases and other new outgoing leases. Legacy/new incoming leases are excluded from capacity. All transaction dates, expiry+1 and adjustment-effective dates in the proposed period are checked under the existing lock. Confirmed positions, provisional quota components and all report projections share effective_lease_amount. Voided leases ignore all their adjustments while retaining their history.

Conservative defaults: an early end cannot move before an already-recorded partial return; no adjustment is accepted on a voided/legacy lease; a full return ends effective availability on the previous day. Backdated partial returns must remain valid against every already-recorded return (total never exceeds original amount). For date-range transaction reports, an adjusted lease shows its effective amount on the last overlapping day of the requested range; it is not a daily sum. Reports with a single as-of date use that date. Recorded allocations and historical Lease (In)/(Out) rows are not rewritten.

Roles: the permission sets remain byte-identical. Lease-only create/adjust routes allow active Admin, Data Editor and Developer with VIEW_DATA; Reporting Viewer is denied. Developer receives no general CREATE_DATA/UPDATE_DATA and cannot save allocations or void leases. Void stays Admin-only. The Quota Transactions page adds New lease and a dedicated Developer Save lease control, with Allocation unavailable in that route. Both app entrypoints exercise actual creation and adjustment.

Existing tests changed: Snowflake lease fakes now explicitly return empty revision evidence when there are no adjustments. The void dependency test seeds an already-saved onward lease directly, representing a commitment made before this rule; the same void rejection assertion remains. New creation of such an onward lease is separately asserted to fail. Existing authentication/role-permission tests are unchanged.

### Protected-area files and narrow reasons

| File | Reason |
|---|---|
| data/quota_leases.py | Shared daily amount, adjusted projections and own-only capacity validation. |
| data/quota_lease_adjustments.py | Append-only adjustment evidence and atomic mandatory history/audit action. |
| data/quota_lease_persistence.py | Validate against adjustment history using the owning transaction; reject injected adjustment metadata. |
| data/quota_lease_void.py | Load adjustment history in the existing void evidence read; void/lock logic unchanged. |
| data/repositories/continuity.py | Add forwarding methods for bounded adjustment reads and the dedicated action; lock body unchanged. |
| data/repositories/mock.py | Read-only attachment of adjustment evidence to new-method leases. |
| data/repositories/snowflake.py | Same bounded read-only attachment; allocation writes unchanged. |
| app/services/authorized_repository.py | Narrow lease-only role checks and actor injection; all other write permissions retained. |
| app/pages/8_Quota_Transactions.py | Lease-only Developer entry route and adjustment controls; no authentication code changes. |
| app/services/quota_lease_entry.py, app/services/quota_lease_adjustment_ui.py | Plain own-quota caption and explicit adjustment UI. |

DDL to review: **none**. Existing APP.RECORD_REVISION and APP.AUDIT_EVENT persistence is reused; no SQL schema, authentication, connection, session or lock implementation is changed.

Part I focused validation: **82 passed**, including the existing lease/void/authentication tests, synthetic adjustment cases and integrity guards. No global permission-set changes were necessary.
