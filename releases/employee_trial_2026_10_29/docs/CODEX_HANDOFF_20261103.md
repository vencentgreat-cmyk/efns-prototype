# Codex handoff — 3 November 2026

## 1. Start here / live version

Repository: https://github.com/vencentgreat-cmyk/efns-prototype
Local root: `C:\Users\Egg Farmers\Desktop\efns\efns-prototype`.
Work only in `releases/employee_trial_2026_10_29`; root app/data/config/sql are
older development context, not the deployment source.

EFNS is an internal Streamlit/Snowflake system for Accounts, Facilities, Flocks,
transactions, quota registrations/activity, Production intake, Salmonella tests,
reports and traceable source/change history.

**User-confirmed live:** `history-view-fix-20261102` at
`5922230942309f02a009ebdd85fbd9de2eae3dbd`, deployed **2026-11-02**.
It is R3 (`a7b0abb`) plus the per-record Change history fix. Declared target:
`EFNS_DEV.APP.EFNS_INTERNAL_APP`, entry `streamlit_app.py`, warehouse
`EFNS_DEV_WH`, warehouse runtime. Live was not queried in this handoff;
independent live hash/config/browser acceptance: **to verify**.

This handoff branch adds documentation only and has identical runtime to 5922230.

## 2. Branch map and merge plan

Remote heads were checked on 2026-11-03; this does not verify deployment.

| Branch | Tip | Contents / status |
|---|---|---|
| `main` | `46af180` | Merge PR #14, older daily-import work; NOT the current live baseline. |
| `codex/identity-history-archives` | `19a4a9c` | Employee-trial source/review snapshot; superseded by later delivery branches. |
| `quota-flock-review-20261030` | `99f9b64` | Activity-only UI, PENDING calculation draft, reconciliation SQL; superseded. |
| `daily-entry-fixes-20261030` | `24f2047` | Daily entry fidelity/report fixes and handover; superseded. |
| `delivery-candidate-20261030` | `8985521` | Delivery candidate including signed Adjustment follow-up; superseded. |
| `delivery-candidate-r2-20261030` | `7b14864` | Rules fallback, draft guards, daily quota parity and smoke tests; superseded by R3. |
| `audit-20261030` | `3e07059` | Read-only audit, repros and health SQL; evidence branch, not deployment source. |
| `delivery-candidate-r3-20261030` | `a7b0abb` | Audit UI fixes F1–F7; superseded by history-view-fix. |
| `history-view-fix-20261102` | `5922230` | Latest live source: R3 plus bounded per-record history. Start future code work here. |
| `codex/offline-review-20261028` | `41a9c88` | Historical independent review copy; disabled authentication seeds; NEVER deploy it. |
| `feature/daily-flock-quota-import` | `123108c` | Older import/connection work; ancestor of live source, superseded as baseline. |
| `feature/snowflake-execution-adapter` | `662a37d` | Older persistence/execution work; ancestor of live source, superseded as baseline. |
| `codex-handoff-20261103` | this document commit | Based on 5922230; one handoff file only. |

Additional local-only legacy branches exist: `codex/efns-design-repairs`,
`codex/snowflake-dev-synthetic-data`, `feature/auth-snowflake-deployment-readiness`,
`feature/eims-connected-import-upgrade`, `feature/schema-agnostic-readiness`,
`feature/snowflake-persistence-foundation`, `fix/phase1-2-validation-reporting`.
Their individual delivery status is **to verify**; do not use them as live source.
Local `main` is stale (`5041d2e`); some remote-tracking refs are stale too.

Git ancestry confirms **5922230 is not merged into remote main 46af180**.
Recommended, not executed: review a normal PR from history-view-fix into main;
inspect both sides and protect the release tree rather than copying old root
code over it. Resolve conflicts only with authorization, rerun full tests and
readiness after integration, then merge the documentation branch separately.
Conflict details are **to verify**. Do not force-push or merge automatically.

## 3. Latest offline verification

At 5922230: **1202 passed, 1 pre-existing skip, 31 warnings, 0 failed in
248.65s (4m08s)**. New history tests: **21 passed in 5.48s**. Readiness and
`git diff --check` passed. No full test rerun for this documentation-only commit.
The skip needs unshared installer/GET_DDL evidence; it was not introduced to
hide a failure. Mock/AppTest/fake SQL is not real Snowflake concurrency or UAT.

From the release directory, using the existing project venv:

```powershell
& '../../.venv/Scripts/python.exe' -m pytest -q
& '../../.venv/Scripts/python.exe' scripts/check_snowflake_readiness.py
git diff --check
```

On another machine use Python 3.12 and `requirements-review.txt`. The offline
conftest blocks network. Intentional deferred audit repro failures are under
`docs/audit/repro`, outside default `testpaths=tests`; do not relabel them passes.

## 4. Deployment / authentication

**The user deploys; the next Codex session must not execute this command.**

```powershell
Set-Location 'C:\Users\Egg Farmers\Desktop\efns\efns-prototype\releases\employee_trial_2026_10_29'
snow streamlit deploy --connection efns-company --replace --authenticator snowflake
```

User reports the `efns-company` profile still has
`authenticator=EXTERNALBROWSER`, which fails with **390190**. The explicit
`--authenticator snowflake` override is required. This supersedes the shorter
command in the older history-fix note. Profile/authentication were not inspected
or tested here (**to verify** if independently confirming); do not read/print
credentials or silently edit the profile. Never use the old personal `efns-dev`.
Use the release's existing `snowflake.yml`; no initialization, DDL or SQL08/18
is required for the history UI fix. Retain rollback source and check drift before
any separately authorized deployment. Do not deploy the sharing/review copy.

## 5. Key code (paths relative to the release)

- `data/repositories/base.py`, `mock.py`, `snowflake.py`: repository interface,
  synthetic implementation and persistent access; `continuity.py`: source,
  revisions and shared transaction support. `data/record_safety.py` and
  `app/services/form_safety.py`: guarded writes, review versions and retry IDs.
- `app/services/authorized_repository.py`: permissions and trusted actor boundary.
- `app/pages/21_Record_History.py`: producer decisions, events, corrections,
  originals and Change history. `app/services/revision_history.py`: pure field
  differences. `get_record_revisions_for(type,id,limit=50)` filters/limits in SQL;
  max 200. Old `get_record_revisions()` remains for existing callers/tests but
  must NOT be used for page-wide display. Raw BEFORE_DATA/AFTER_DATA are not sent
  by the two revision displays. Time is displayed in America/Halifax.
- `data/validation.py`, `operational_flock_quota_import.py`, `production_intake.py`,
  `importing.py`: daily/workbook validation and intake; do not rewrite historical
  contracts to enforce a new daily rule. `data/quota_types.py`: legacy/canonical
  type compatibility without rewriting stored labels.
- `data/quota_position.py`, `data/flock_stock.py`, `config/quota_rules.json`:
  PENDING drafts, not certified balances/current stock. `quota_usage.py` is under
  `app/services`; recorded Bird Count is not verified current occupancy.
- `app/services/report_center.py`, `report_builder.py`, `app/pages/4_Reports.py`:
  selected scope, grouping/counts, NULL-aware totals, CSV/XLSX. Unknown is not 0.

## 6. Known issues and December scope

- **A03 backend:** Flock events CAS-check submit-time state, not a user-reviewed
  origin/version. R3 UI confirmation resets do not close that backend gap.
- **A06/A07:** Admin updates lack reviewed-version CAS; concurrent admin changes
  can race the last-active-admin check. Real concurrency behavior: **to verify**.
- **A09:** Duplicate parent IDs can multiply Salmonella report rows. Actual
  company duplicates: **to verify** via health Q01; do not assume they exist.
- Change history's **Changed by** currently shows stored recorder user ID, not
  a resolved staff name. Do not invent identities for missing historical values.
- Other eager tabs, especially **Producer matching** and **Original files**, may
  still exceed Streamlit's message limit with large frames. This is a risk,
  **to verify**, not a reproduced failure in those tabs. Do not raise limits or
  load whole history tables as a workaround.

**Quota usage calculation is OUT of the December scope.** Focus on daily
records, reliable saving and reports. Existing quota registrations/transactions
remain usable as records/activity. Do not enable the PENDING formulas, infer
current stock from historical sums, or make missing quota rules block staff UAT.

## 7. Open user-side tasks (not completed by this handoff)

1. Complete the user's **14-step manual test** on live 5922230; record actual
   outcomes. Exact plan/location: **to verify**. The checked-in deployment
   checklist contains an older **15-step** plan, not proof of this 14-step test.
2. Run `data_health_20261030.sql` manually: **Q00 identity first, then Q01
   duplicate IDs**; stop on wrong identity. Obtain it from
   `audit-20261030:releases/employee_trial_2026_10_29/sql/review/data_health_20261030.sql`
   (not present on the live source branch). Results/query IDs: **to verify**;
   save privately, never infer a repair or write from diagnostic results alone.
3. Meisners registration check: recover exact missing Quota Registration GUIDs
   with source evidence; do not guess from names/counterparties/quantities.
   Current resolution: **to verify**.
4. Prepare an old-versus-new feature gap list for actual staff workflows, with
   evidence, impact and priority. Coverage/status: **to verify**; do not clone
   unused EIMS features or reopen broad historical investigations automatically.
5. Prepare staff testing: intended roles/access, approved test data, a few daily
   scenarios and a simple issue log. Read-only review is separate from write
   testing; synthetic test writes need explicit authorization. Staff readiness
   and full browser acceptance: **to verify**.

## 8. Working rules for the next session

- Read this handoff and check Git status before work. Preserve all existing
  modifications. Use the release tree and a **new branch**, never overwrite the
  live/frozen/audit branches. No force-push, main merge or history rewrite.
- **No Snowflake connection, company scripts, deployment, data changes, DDL,
  permission/parameter changes or historical operation reruns. The user deploys.**
- Keep connection/continuity/write-safety, authentication/security, navigation,
  frozen mappings/migration, date repair, supplements and PENDING quota/stock
  rules protected. Any exception needs explicit new authorization, not an
  inference from a previous narrow fix. Do not repeat approved historical fixes.
- Keep changes small and tied to staff feedback. Do not delete/skip/xfail safety
  tests. Run relevant offline tests; run full regression before a release fix.
  Distinguish code inspection, Mock/AppTest, engine evidence and manual UAT.
- Push only an explicitly authorized new branch. Never commit credentials,
  originals, business exports, private plans/evidence, logs, caches or .local.
- Record business decisions as open questions and continue independent work;
  do not invent units, ownership, quota formulas, stock or historical dates.
