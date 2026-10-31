# Read-only staff workflow audit — 30 October 2026

## Result and boundaries

**Do not treat the frozen delivery candidate as cleared by this audit.** Four
P1 staff-flow findings and one P1 conditional administrative race warrant review.
Nine new safety assertions fail reproducibly offline; eight SQL-static tests pass.
No finding is fixed here. No company connection, SQL execution, business write,
deployment, company script or external lookup was performed.

Audit branch: `audit-20261030`, created from frozen
`7b14864713779253b329e2243af3fca62b416cbb`. The
`delivery-candidate-r2-20261030` branch is not changed. Paths/line numbers below
are relative to `releases/employee_trial_2026_10_29` at that commit.
Only `docs/audit/` and `sql/review/data_health_20261030.sql` are added.

The exclusion list is the literal result of `git diff --name-only 19a4a9c -- .`,
saved in [SCOPE_20261030.json](SCOPE_20261030.json). Changed files are excluded
from a fresh whole-file audit. In particular Report Center/builder, quota usage,
quota calculation, record_safety, validation, migration and both main repository
implementations are not re-audited. Existing supporting code/tests in these
files were read only to understand call boundaries. The unchanged Flock form,
related-record and save blocks were inspected; its newly added Count draft
block was excluded. The unchanged Daily parser/identity/Flock branches were
inspected; its R2 quota validation block was excluded. The Daily page itself is
unchanged and is in scope.

Priorities: P1 = address before affected staff/admin use; P2 = before delivery;
P3 = later improvement. A conditional risk is not evidence that company data
already meets the triggering condition. No business formula is inferred.

## Findings, sorted by severity

| ID | Severity / evidence | File:line | Concrete failure scenario and impact | Reproducing test / next check |
|---|---|---|---|---|
| A01 | **P1 — reproduced error handling** | `app/pages/19_Daily_Flock_Quota_Import.py:203–206`; executor context `data/connection.py:274` | A lost COMMIT acknowledgement raises the executor's explicit outcome-unknown error. The page discards it, clears the submitted hash and states **No business rows were committed**. This is not proof of rollback and invites another submission. Batch guards may prevent duplication, but misleading recovery instructions remain unsafe. | `test_A01_daily_commit_unknown_is_not_reported_as_rollback` injects outcome-unknown at the actual page commit boundary; fails because the page claims no commit. Receipt lookup before retry is required; no real COMMIT loss was induced. |
| A02 | **P1 — reproduced stale confirmation** | `app/pages/21_Record_History.py:32,38–43` | Confirm producer evidence for source row A, then select row B. The Account, reason and checked confirmation remain; Save can now staff-confirm B without a fresh confirmation. The backend validates existence/trusted actor, not whether that checkbox was reviewed for B. | `test_A02_producer_confirmation_is_cleared_on_record_switch` fails: checkbox is still True for B. Extend with changed target Account/evidence and verify no write until explicitly re-reviewed. |
| A03 | **P1 — reproduced stale confirmation; additional review-time risk** | `app/pages/21_Record_History.py:73–93`; `data/repositories/continuity.py:538–585` | Move evidence checkbox survives switching Flocks. It is also not reset when destination/time changes. Backend reads the latest Flock at submit and CAS-protects that internal snapshot, but the entry accepts no user-reviewed version/origin. A concurrent move before submit can become the new FROM Facility even if the user confirmed the older origin. | `test_A03_flock_event_confirmation_is_cleared_on_switch` fails on record switch. Separate future test: review A, change current Facility externally in synthetic state, submit a move based on A; require conflict, not adoption of the latest origin. Live concurrency was not tested. |
| A04 | **P1 — reproduced administrative wrong-target confirmation** | `app/pages/15_User_Management.py:91,121–130` | Check Confirm deletion for user A, switch to deletable user B: confirmation remains checked and Delete user is enabled for B. Backend blocks self/last-admin deletion, but does not bind this confirmation to B. | `test_A04_user_delete_confirmation_is_bound_to_user` fails. Test does not click Delete or delete any user; it proves the stale confirmation. Reconfirm on target switch. |
| A07 | **P1 — conditional admin-integrity race; call order reproduced** | `app/snowflake_security.py:147–167,184–194` | Two active Admins can concurrently demote/delete the other. Each counts another active Admin **before** entering its write transaction; there is no shared invariant lock. Both can pass the check. Single-session last-admin protection works and is not a concurrency guarantee. | `test_A07_last_admin_check_is_inside_write_transaction` captures the actual call order and fails (count before BEGIN). Future two-session isolated engine test must prove the invariant; merely moving COUNT into BEGIN alone is not a proven fix. No real race was executed. |
| A05 | **P2 — reproduced filter identity collision** | `app/pages/10_Salmonella_Report.py:29–31`; similar patterns `app/pages/6_Flock_Transactions.py:28`, `app/pages/9_Salmonella_Tests.py:33`, `app/pages/13_Facility_Details.py:31` | Dictionaries keyed only by names/combined non-unique labels silently keep the last ID. Two same-name Facilities yield one report option; one cannot be selected independently. Other cited selectors have the same conditional collision pattern, not a claim of current duplicate business names. | `test_A05_salmonella_facility_filter_keeps_same_name_identities` fails: 2 Facilities yield 1 selectable identity. Follow-up tests should cover repeated Flock Number/Account labels and show IDs in labels rather than guessing or merging. |
| A06 | **P2 — missing admin CAS reproduced** | `app/pages/15_User_Management.py:92–104`; `app/snowflake_security.py:156–176` | Administrator A reviews role/active settings; B changes them; A saves an older form. SQL WHERE checks only USER_ID, so the newer settings can be silently overwritten. UPDATED_AT is assigned, not compared; no reviewed version is accepted. | `test_A06_user_update_has_review_version_predicate` fails against captured real method SQL using a fake executor. Add two reviewed snapshots to require a conflict. This is SQL-shape evidence, not engine concurrency validation. |
| A08 | **P2 — reproduced historical-choice gap** | `app/pages/10_Salmonella_Report.py:42`; list equivalent `app/pages/9_Salmonella_Tests.py:62`; `app/pages/11_Facilities.py:64` | Salmonella report only offers current constants. A stored historical result visible in All cannot be selected as a result filter. Similar constant-only Facility-type filtering can omit historical types. Existing edit forms use stored_options and preserve old values: this finding concerns filtering, not notes-edit loss. | `test_A08_salmonella_historical_result_remains_filterable` fails on a synthetic non-constant result. Inventory actual labels with Q06 before deciding whether a value is a valid current input; do not expand entry choices automatically. |
| A09 | **P2 — conditional count amplification reproduced** | `app/services/salmonella_reporting.py:31–39` | One test joined to two identical parent Flock rows yields two report rows. Account/Facility duplicates can similarly amplify results because merges have no cardinality validation. Declared standard-table PKs do not prove uniqueness. No company duplicate was found or asserted. | `test_A09_salmonella_report_cannot_multiply_on_duplicate_parent` fails: 1 test becomes 2 rows. Require explicit unique-parent validation/diagnostic, or a demonstrably safe identical-parent policy; never silently choose conflicting parents. Run Q01 before trusting joined health/report totals. |
| A10 | **P3 — static visibility limitation** | `app/pages/16_Audit_Log.py:23,39–54`; `app/snowflake_security.py:256–263` | Audit filters are applied after loading only the latest 5,000 events. An older action can appear absent; the UI does not say that its search scope is truncated. No claim is made that current DEV exceeds this count. | Future test: 5,001 synthetic events, older unique action; require explicit limited-history wording or server-side filtered/paged retrieval. Not run here; no runtime bug fix proposed in this branch. |

## What was inspected and found OK (within stated limits)

These are code observations and specific local tests, not complete business
acceptance. A repository path with conditional invariants is not certified by
having a page. References to changed dependencies below describe existing
context rather than expanding Part A's audit scope.

| Page / service | Checks and evidence / remaining boundaries |
|---|---|
| Accounts (`3_Accounts_Facilities_Flocks.py:269–319,321–405`) | Stored option helpers and capture/preserve form protect untouched NULL/0/legacy attributes and links. Coordinate edits parse optional numeric values. Save uses create-once/revise with reviewed form snapshot. Account relationship display and notes-only tests in existing round2 pass. No fresh database uniqueness/role test. |
| Farm Locations (`18_Farm_Locations.py:91–174`) | Form context reset, stored status preservation, reviewed version setdefault, create/revise/delete confirmation path. Existing Farm Location tests cover CRUD, optimistic conflict, validation, reference protection and authorization; all pass offline. |
| Facilities (`11_Facilities.py:115–147`) | Stored type/status choices, nullable date inputs, original snapshot and shared save helper. Unexposed fields are not included in the save record. Description-source display is read-only. No claim that source description equals current comments. |
| Facility Details (`13_Facility_Details.py:111–159`) | Text detail type stays free text, historical status is included, unchanged fields are preserved, form-bound reviewed version and reason reach save helper. Parent-label collision remains a conditional A05 concern. |
| Flocks, unchanged blocks (`5_Flocks.py:151–227` and related block) | Form uses stored options, capture/preserve, reviewed version; business movement/end is separate. Existing notes-only fidelity test passes, including no lifecycle mutation. New draft calculation block and quota usage service excluded. |
| Flock Transactions (`6_Flock_Transactions.py:85–146`) | Edit quantity text and shared preserve helper keep historical decimals/NULL; confirmed current quantity uses reviewed Bird Count/version, explicit intent and request. Reload clears confirmation and refuses silent downgrade. Existing Reload-without-confirmation and notes-edit fidelity tests pass. Label collisions remain conditional A05. No new stock/lifecycle policy is approved. |
| Quota Registrations (`7_Quota_Registrations.py:175–209`) | Edit includes stored type/status; original capture supplies correction version and keeps unchanged historical dates. Future entry type choices come from changed constants, excluded from this audit. No re-audit of R2 quota transactions. |
| Salmonella Tests (`9_Salmonella_Tests.py:128–167`) | Untouched Flock selection preserves test-time Account/Permit via capture/preserve, despite record builder reading current Flock. Edit sample count is text; old result retained. Existing notes-only fidelity test proves preserved Permit/Account/history. List historical filters remain A08. |
| Salmonella Test Report (`10_Salmonella_Report.py:50–68`) | CSV/XLSX use the same filtered report frame after spreadsheet safety conversion. No separate export query with different filters. A05/A08 affect selectable scope and A09 affects row multiplicity before export; consistent export does not establish correct scope. |
| Production Import (`1_Production_Import.py:63–88,184–199`; `data/production_intake.py:16–42`) | Source archive/retained RAW is distinct from CORE commit. Staged rows and accepted targets remain separate. Explicit independent-observation checkbox; commit invokes staged path. RepositoryError (including unknown outcome) is shown through safe error renderer, unlike A01. Actual file PUT and database rollback not tested. |
| Production Data (`2_Production_Data.py:39–108,121,176–187`) | Period/attribute options derive from stored values; source scope is applied before display/metrics/export. SUM uses min_count=1; NULL not coerced to 0. Page/CSV/XLSX take the same selected columns and rows. Existing source-scope behavior remains evidence-dependent; no source is newly certified here. |
| Daily Import, unchanged parts (`19_Daily_Flock_Quota_Import.py`; unchanged `data/operational_flock_quota_import.py` portions) | Per-package confirmation, explicit valid/rejected distinction, accepted-row commit and retained source identity. `commit_staged_operational` compares submitted writes with staged normalized review; committed batch returns prior result. A01 is the unresolved failure-feedback issue. R2 quota validation additions excluded. |
| Record Review & History (`21_Record_History.py:46–68,105–182`) | Manual production uses payload-aware request and Start another action. Attribute correction has per-record reviewed version and reload. Production correction retains version and explicit Reload. Original files use source-trace helper; no RAW-only target is newly asserted as CORE. Producer/Flock confirmations are A02/A03. No complete file retrieval test here. |
| Audit Log / User Management | VIEW_AUDIT / MANAGE_USERS enforced. Sequential self/last-admin restrictions are present and covered by existing local auth tests. Admin update/delete audit shares the auth-store transaction; concurrency and user-bound confirmation remain A04/A06/A07. Audit has A10 limit. |
| Shared form safety (`app/services/form_safety.py:20–100`) | begin_form isolates record contexts; capture_form records review version; preserve_form restores untouched values; request_for/finish_request support identical retry and new-content flow; navigation-after-save warning does not claim unsaved. Existing second edit, duplicate legitimate entry, conflict and deletion before-image tests pass. |
| Authorization (`app/auth.py:201–227`; `app/services/authorized_repository.py:94–151,183–245`) | App reruns install AuthorizedRepository using authenticated user. Create/update/delete/import methods require permissions; actor values are overwritten from authenticated identity. User administration deliberately uses AuthStore with MANAGE_USERS, not business repository. Secondary audit failure reports committed state and attempts durable warning. No new permission bypass reproduced. |
| Concurrency/transaction context (`data/repositories/continuity.py:68–100,388–427,614–659`) | Existing business correction SQL compares FF9 expected versions, uses strictly advancing versions and owns revision/audit transaction. Producer match CAS uses its transaction-time snapshot; it does not cure UI stale confirmation (A02). Flock event CAS similarly does not prove review-time protection (A03). No engine transaction was run. |
| Referenced deletion context | Existing guards list Account self-links, Contact, Farm Location, Facilities, Flocks, Production producer/grader, Salmonella and Quota links; Facility has Detail/Flock/Production/event children; Flock has transaction/test/production/event; Quota/transaction/sample children are listed. Existing Account-with-Production and delete-before-image tests pass. `data/record_safety.py` changed since base, so this is context, not a fresh audit proving every child edge. Legacy disposal text is not asserted to be a declared FK; Q07 identifies candidates for review. |

No fresh universal statement that **every** write is CAS-protected or every
possible reference is blocked is justified: admin updates are A06, review-time
confirmation is A02/A03, and several repository implementations were excluded.
Sequential local success is not two-session Snowflake concurrency proof.

## Reproduction and supporting test results

Run from this release directory (Python 3.12 project environment):

```powershell
& '../../.venv/Scripts/python.exe' -m pytest docs/audit/repro -q --tb=short
& '../../.venv/Scripts/python.exe' -m pytest tests/test_farm_locations.py tests/test_authentication.py tests/test_round2.py -q --tb=short
git diff --check
```

- New audit probes: **9 failed, 8 passed in 9.22s**. Each failed assertion is
  retained, unskipped, un-xfailed; it expresses the desired safety behavior.
  A07 asserts check ordering; it does not claim a real concurrency race.
- SQL static tests: **8 passed** (included above); after adding disposal-method text coverage, a separate static rerun also passed **8 in 0.02s**, covering SELECT/WITH-only,
  negative control statements and all 16 declared CORE primary-ID checks.
- Supporting existing tests: **41 passed, 4 warnings in 28.56s**. These exercise
  local CRUD/permissions/fidelity/retry safeguards; they do not negate the new
  failed probes or certify every business path. No full suite was rerun.
- The Daily-page probe substitutes an equivalent selectbox for its display-only
  segmented row filter because this installed AppTest cannot serialize that
  segmented control on rerun. Business commit/error code is the unmodified
  actual page. An explicit unknown-outcome error is injected; no real failure
  is manufactured on company records. Other AppTests use native controls.
- Raw initial run exposed that harness limitation; it was corrected only in the
  new repro harness. No application code, assertion or protection was weakened.
- Default pytest configuration uses `testpaths=tests`; these intentional audit
  failures in docs are run explicitly and do not alter the frozen test suite.
- Streamlit local skill discovery found a missing bundled SKILL.md. No web
  fallback or package installation was performed; source/local tests suffice
  for the bounded findings above.

Sanitized results: [repro/REPRO_RESULTS_20261030.txt](repro/REPRO_RESULTS_20261030.txt).
Raw local traces can contain synthetic session details and are not pushed.

## Read-only data health SQL

[../../sql/review/data_health_20261030.sql](../../sql/review/data_health_20261030.sql)
contains **11 standalone SELECT/WITH statements**, generated only from local
DDL/choice definitions by [build_data_health.py](build_data_health.py).
It has not been executed or engine-syntax-validated. No assertion is made that
company data is clean, duplicate, orphaned, or equal to a local example.

1. In a separately authorized Worksheet choose an existing company SELECT role
   and usable warehouse, with access to EFNS_DEV.CORE. Do not request new grants
   or run initialization. This audit does not change session role/database.
2. Run **Q00 first**. Expect QDCTNKN / UW19058 / CB12755 / AWS_CA_CENTRAL_1;
   session database EFNS_DEV. Stop if identity differs. All table references
   are explicitly EFNS_DEV even though current context is checked.
3. Run **Q09** inventory compatibility gate (only role-visible objects), then
   **Q01 / Q01b** before joins. Local DDL declares 16 CORE tables, including
   FLOCK_EVENT. Unknown future tables require extending the audit; no live
   inventory was collected. A missing column/object means stop that query,
   inspect metadata and update this audit SQL only; do not modify the schema.
4. Run remaining labelled statements separately. Non-empty interpretations are
   in comments. Q02 checks optional nonempty references with NOT EXISTS; missing
   required values are Q03. Q04 multiple Deliveries are clues, not duplicates
   to delete. Q05 compares owner versus registration, not counterparty.
5. Q06 inventories non-current labels; historical labels are not automatically
   invalid. Q07 compares both disposal plant/method text to Account GUID/name; names are only
   candidates. Q08 finds top-level DEV_TEST prefixes, not every test record;
   it is a review list, not permission to delete anything.
6. Save results privately with query IDs/time/role and maintain source context.
   Do not commit business rows or personal data. Large-table scans are expected;
   no schedule or automatic repair is installed. NULL quantities remain NULL;
   COALESCE is used only for a count indicator, never to invent quantities.

The static guard rejects write/session/control commands even inside a WITH
statement. It does not prove reference compatibility, uniqueness, business
meaning, privilege sufficiency, execution cost or query success in Snowflake.
Standard-table declared PK/FK metadata is not enforcement evidence.

## Next decisions and delivery

- Restrict the affected matching/movement/import-error recovery paths until P1
  findings are reviewed and fixed in a **different** authorized branch.
- Admin concurrency/confirmation findings concern access maintenance, not a
  request for broader application privileges or parameter changes.
- Business meanings for stock, quota, source priority, inactive rows and legacy
  labels remain pending. This audit neither implements a formula nor expands
  new-entry transaction lists.
- Push only `audit-20261030`, normally, preserving the frozen R2 branch and all
  existing history. The exact pushed SHA is verified by git ls-remote and
  printed in the final response (a report cannot embed its own commit hash).
