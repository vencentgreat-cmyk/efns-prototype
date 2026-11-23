# Task 5: Flock Summary and lease adjustments

Base: origin/main a4b0e35 (Task 3 merged); separate worktree and branch codex-flock-summary-lease-adjust-20261120. No live Snowflake, deployment, operational DDL or real-data files.

## Initial findings

- Migration parse_reporting_period splits YYYYWW; production_week uses REPORTING_YEAR*100+REPORTING_WEEK. Mapping v3 maps efc_productionweek to SOURCE_WEEK_CODE and EFCYear/EFCWkNumber to the calendar. No inconsistent date/ISO-week derivation is used for these report codes. Historical CYYWW remains an explicit supported legacy format, unrelated to EFC date resolution.
- Existing get_efc_dates reads CORE.DIM_EFC_DATE. The new resolver validates complete Sunday-Saturday weeks; Friday is the inventory date (staff decision updated 2026-11-23), never a sum over time. Mock calendar is explicitly synthetic, not a new production calendar rule.
- Admin and Data Editor currently have CREATE_DATA; Developer does not. Part I requires a lease-only authorization route, preserving all other permissions and Admin-only void.
- Details currently includes positive legacy Lease (In) and omits legacy Lease (Out); legacy types/values must remain unchanged. New-method leases currently contribute only incoming amounts to Details.

## Part H

Flock Summary reuses Flock Status inventory for the Friday of each EFC week. Stock is never summed over weeks. Grouped rows use stable Account identity internally, then show Account and registration labels. Known inventory totals follow existing Status handling; unavailable values remain a dash and are disclosed. Quota-type columns are exhaustive for eligible types in the input, including an explicit Not specified category; Special Permit remains excluded exactly as Flock Status. Non-selected type columns show zero. Weeks without included flocks have no row.

Production resolves dates only from the maintained calendar; the synthetic mock fixture is generated for adjacent local years and is not evidence of any unexported production calendar dates. Empty/unknown calendars display a clear message. CSV retains the data columns; XLSX Notes and PDF include the Friday caption.

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

## Part J: signed new-method leases in Quota Summary Details

Confirmed position already computes the effective new-method incoming/outgoing amounts with the shared lease function. Details now includes the negative outgoing sum in its existing Quota Transaction Type / Quota Bird Count columns, after the increasing types. Account Total includes both sides; the grand total sums each Account once. Screen, CSV, XLSX and PDF share that same frame. The catalog/page describe the distinction.

Historical Lease (In) remains positive in the gross types, and historical Lease (Out), Sale and Terminate Quota remain excluded exactly as before. Therefore pre-existing legacy gross-versus-net differences remain; the new-method lease itself conserves the Details grand total. It would contradict the instruction to preserve legacy values to force the full legacy gross result to equal net Issuance. Synthetic tests prove conservation, signed sides, partial/early-end/void behavior, all exports and unchanged output before/after the lease period.

Additional protected-area file: data/confirmed_quota_position.py adds the already-calculated negative new-method lease side to Details type sums only; net quota, legacy eligibility and no-new-lease results are unchanged. No DDL is required for Part J.

Final invariant review added an all-unknown stock case: zero-filled columns for absent quota types must not turn an unknown total into zero. Flock Summary now computes the weekly total from actual included inventory evidence, before adding presentation zeros. Both province and grouped cases have synthetic regression tests; this does not change any existing report or inventory rule. The full release suite was restarted after this correction.

The first completed full run found one compatibility issue in an existing XLSX test spy: unrelated reports were being passed an unnecessary notes=None keyword. The adapter now supplies notes only for Flock Summary and preserves the original call contract for all other reports. The existing saved-configuration/export test was not changed. The full suites are rerun after this correction.

## Final validation and complete file scope

- Release suite (Python 3.12): **2,389 passed, 1 skipped, 0 failed, 0 errors**; 10m27s.
- Root suite (Python 3.11): **706 passed, 0 failed, 0 errors**; 1m56s.
- Baseline release count was 2,334 passed / 1 skipped; 55 added cases account for the increase. Existing fixture expectations for report quantities were not changed.
- Final targeted export/stock/adjustment tests: **54 passed**. Previous combined quota-focused run: **121 passed**.
- Live manifest: **159 LF-normalized candidate hashes**, regenerated with all original base entries retained.
- Authentication, runtime mode, global permission sets, Snowflake security, connection handling and environment are unchanged. AST comparisons also confirm the existing continuity methods (including the lock body) and repository write methods are unchanged; only the stated forwarding/read methods and quota-lease helpers change.
- Existing numbers remain unchanged with no new-method lease. Existing lease calculations without adjustments remain unchanged except the explicitly requested Details outgoing display and own-only availability policy. CSV byte parity and XLSX data parity are tested; existing production fixture values are untouched.
- No Snowflake calls, deployment, PR, real-data exports/fixtures or operational DDL. New tests use synthetic Accounts and amounts only.

Changed files (all under releases/employee_trial_2026_10_29):

- `DELIVERY_RUNTIME_DIFF_20261030.json`
- `app/pages/4_Reports.py`
- `app/pages/8_Quota_Transactions.py`
- `app/services/authorized_repository.py`
- `app/services/flock_summary_report.py`
- `app/services/quota_lease_adjustment_ui.py`
- `app/services/quota_lease_entry.py`
- `app/services/report_center.py`
- `app/services/report_pdf.py`
- `data/confirmed_quota_position.py`
- `data/efc_calendar.py`
- `data/quota_lease_adjustments.py`
- `data/quota_lease_persistence.py`
- `data/quota_lease_void.py`
- `data/quota_leases.py`
- `data/repositories/continuity.py`
- `data/repositories/mock.py`
- `data/repositories/snowflake.py`
- `docs/codex_reports/FLOCK_SUMMARY_LEASE_ADJUST_20261120.md`
- `tests/test_flock_summary_report.py`
- `tests/test_quota_details_new_leases.py`
- `tests/test_quota_lease_adjustments.py`
- `tests/test_quota_lease_void.py`
- `tests/test_quota_leases.py`
- `tests/test_report_center.py`
- `tests/test_report_smoke.py`

## Bounded read added for adjustment evidence

The default-database form below is the query template, not executed SQL. Transaction IDs and change kinds are bound parameters. Creation, adjustment and void validation pass the owning transaction explicitly. The existing revision/audit INSERT helpers are reused without changing their SQL or the lock implementation.

```sql
SELECT REVISION_ID, ENTITY_ID, AFTER_DATA
FROM EFNS_DEV.APP.RECORD_REVISION
WHERE ENTITY_TYPE = %s
  AND CHANGE_KIND IN (%s, %s)
  AND LOWER(ENTITY_ID) IN (
    SELECT VALUE::VARCHAR
    FROM TABLE(FLATTEN(INPUT => PARSE_JSON(%s)))
  );
```

DDL to review: none; the existing revision and audit tables already support the append-only records.

## Shipped-file byte proof

SHA-256 below is over raw worktree bytes. The runtime-diff manifest separately uses LF-normalized bytes. Seventeen shipped files changed or were added; all 114 other shipped files are byte-identical, with none removed. No configuration, dependency, schema or data files changed.

| Shipped file | Base SHA-256 | Final SHA-256 |
|---|---|---|
| `app/pages/4_Reports.py` | `378adbfaeba8ac16ebea2c477cb81ee79a053603efcfb330d09d9343bcd42ad6` | `5988706f41c133aa3e2d0266733ee74cb705f81d9716ed791d58d1c1d3c26d83` |
| `app/pages/8_Quota_Transactions.py` | `0b7cd07fb31986ed502066ad412b5b4fedf1e21ec2e09aa06f721cc2642263a0` | `c71193cda4a3e1a5dc15eb79d118a0b14c4aed724846f0b580ca2fff74d5d8c7` |
| `app/services/authorized_repository.py` | `9eb4b94af95a13d163131909adab2b770acc7e82dc27fbbd240a4fbdfe3940df` | `a1ad6a3e3fb904e06a2521be3bba688c9146d25eac8c96d90ffeccad65a5234f` |
| `app/services/flock_summary_report.py` | `NEW` | `c2169a24b41b25e43ef779bb83c066d9b4dadd8dc590577e3109ed0c0d6673de` |
| `app/services/quota_lease_adjustment_ui.py` | `NEW` | `501838fc42f3954a4f862e77a1910c71910582cb5af1cc13d3dfafeec31aadfc` |
| `app/services/quota_lease_entry.py` | `892843c400bdb9451f95d16289c9466c5de9ec6ed8ff6e7776b704a1665d0919` | `f9c34fc475ea058c58e8df9ca886daa10e0cadc006ce32fff01550b6fc9c6278` |
| `app/services/report_center.py` | `06babe00262179307431fbfc6feb95c245967db6f5cfec928aae304b36ddd0cb` | `74408adbe90467074b6e413e8f2c04e176fa8c9e1dd593f2560dd8344464406e` |
| `app/services/report_pdf.py` | `1140a53b38a52ef2bfb8f0ea2179485fbad616c1403cf822ad3d444961c63414` | `973bce319e73c0cb2cba57834db5ccc6c43909d8900e7d2915340132451425fb` |
| `data/confirmed_quota_position.py` | `a897495664724ab0101bf735b22a3c42bae816f5ac9da3bf13d97c7c3207fb55` | `ccdc8193e0844227e9e3e86ac95b6df993bcfe080c1187df21b7ef228fbfd471` |
| `data/efc_calendar.py` | `NEW` | `dd517e46724e5e7c3de68398113378bfe4f814d93427850c10a6e72efc9a98f2` |
| `data/quota_lease_adjustments.py` | `NEW` | `1fae02dc5e7f767c50a21485719022eec94b0c1e1f463b359f909daa09846393` |
| `data/quota_lease_persistence.py` | `19d92f3c515f2f51f060023471c9467f39f98b9d73d86b17e3cc0f093ac8466d` | `ac7b4a7734945e41a93fc969740f75ee66829e883a58d7877d2b4cb4ed69c7f9` |
| `data/quota_lease_void.py` | `4e394318377de4d6bcbd4b00b844355204d427e370b8e9cb458907477c565c5e` | `a5cf653d3bd49ecbca3b87601b4924745b3ac85f7b3aa5a1b2d9515804bc01d5` |
| `data/quota_leases.py` | `23a8d49e87d7b9d27d602ac0f8af1245379428e9827956441179583c37458090` | `999f26ea148d1a5b65e11cd12ecb924f65581cdbfe0813a8f3f8f070a8ce6dab` |
| `data/repositories/continuity.py` | `1348e04b4f5eeecec4d719992ee6065cc54e9becc43f5c354ced6f23c293b611` | `63f79c2cfa43e6261ef4ed4b5f3c683ada1c5354bc928a709e789e31210dc6b0` |
| `data/repositories/mock.py` | `5d502bdef358c4ece88a96f1069c4bb6802e27fa9f880c7bf8c72b8b95f01e94` | `f8c3f40ff23b450ec744f51ecb2929dcc98d3c7111895cdddf1f9e7d6452cc0e` |
| `data/repositories/snowflake.py` | `f07116326603981201d8ec2408230032f542ed06670a6cd6fd69cd2e07a6e842` | `36635b6d0b4e752eea2ea4522655ac41f14680bea607fd415644744f671da65d` |
