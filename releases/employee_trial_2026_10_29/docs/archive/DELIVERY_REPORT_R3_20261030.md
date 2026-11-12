# Delivery candidate R3 — audit fixes (30 October 2026)

## Status and scope

Branch `delivery-candidate-r3-20261030`, based on frozen R2
`7b14864713779253b329e2243af3fca62b416cbb`. Work is confined to
`releases/employee_trial_2026_10_29`. No company connection, company script,
SQL execution, deployment, schema/permission/parameter change or business data
change was performed. This is a local release candidate, not a deployed fix.
The R2 and audit branch references remain unchanged.

## Fix commits and file scope

| Task | Commit | Files / behavior |
|---|---|---|
| F1 / A01 | `81fc5b2` | `app/pages/19_Daily_Flock_Quota_Import.py`, `tests/test_r3_audit_fixes.py`: recognize existing RepositoryError `COMMIT outcome is unknown.` marker; preserve submitted hash and persistent per-package unknown-outcome guard; show the required administrator/history reference. Re-review cannot unlock that package within the session. Only explicit `System busy: no write transaction started` evidence permits a no-write claim; unclassified errors use show_data_error and retain the guard. No executor changes. |
| F2 / A02 | `11dc5b6` | `app/pages/21_Record_History.py`, R3 tests: Account/evidence/confirmation keyed by production record and cleared on switch. Save stays disabled until the selected record has Account, evidence and fresh confirmation. |
| F3 / A03 UI | `77c2d17` | `app/pages/21_Record_History.py`, R3 tests: Flock-specific event widgets; confirmation resets on Flock, destination, event type, business date/time changes. Movement/end needs fresh UI confirmation. Backend origin/version gap remains deferred. |
| F4 / A04 | `679cc44` | `app/pages/15_User_Management.py`, R3 tests: delete checkbox keyed by selected user; switch clears old confirmation and disables Delete. Tests never click Delete and verify all synthetic user IDs remain. Auth-store code unchanged. |
| F5 / A05 | `b16f770` | `app/services/selector_options.py`; pages `10_Salmonella_Report.py`, `6_Flock_Transactions.py`, `9_Salmonella_Tests.py`, `13_Facility_Details.py`; R3 tests: collision-only stable ID suffixes prevent label-to-ID overwrite. Shared ID prefixes expand; natural-label/suffix and All-sentinel collisions are handled. Normal labels remain unchanged. |
| F6 / A08 | `55d23fc` | Selector helper; pages `10_Salmonella_Report.py`, `9_Salmonella_Tests.py`, `11_Facilities.py`; R3 tests: current choices first, then sorted historical filter labels; no new-entry choice expansion. |
| F7 / A10 | `ae9864b` | `app/pages/16_Audit_Log.py`, R3 tests: one caption discloses latest 5,000 loaded-event filter scope; query unchanged. |
| Verification / handover | commit containing this report | Runtime hash manifest, deployment checklist, handover deferred items, exact package-count expectation, original audit repro and locator-only companion, this report. No additional runtime fix. |

All relevant original audit assertions were migrated to
`tests/test_r3_audit_fixes.py`. They failed before each corresponding fix and
pass after it. A04's two widget lookups use the unchanged visible label because
its old shared key is precisely what F4 replaces. No safety assertion was
removed, weakened, skipped or xfailed.

## Local verification

From the release directory, using the existing Python 3.12 venv:

```powershell
& '../../.venv/Scripts/python.exe' -m pytest tests/test_r3_audit_fixes.py -q --tb=short
& '../../.venv/Scripts/python.exe' -m pytest -q
& '../../.venv/Scripts/python.exe' scripts/check_snowflake_readiness.py
git diff --check
```

| Check | Actual result |
|---|---|
| F1 unknown/busy/unclassified failure paths | 4 passed in 6.24s |
| F2 record switch, disabled save until re-confirmation, no matching write | 1 passed in 3.57s |
| F3 Flock switch and destination/type/date/time changes | 5 passed in 7.77s |
| F4 delete target switch; all synthetic users retained | 1 passed in 3.37s |
| F5 same-name IDs, shared prefixes/natural labels, all four pages | 5 passed in 5.82s |
| F6 historical filters and unchanged new-entry choices | 4 passed in 4.95s |
| Combined R3 regressions, including F7 | **21 passed in 21.62s** |
| Full offline suite | **1181 passed, 1 pre-existing skip, 31 warnings, 0 failed in 266.53s (4m26s)** |
| Snowflake readiness (static, offline) | Passed |
| git diff --check | Passed |
| Protected runtime | 34 files have unchanged repository bytes against R2; existing LF/CRLF checkout variants are retained. No protected working file was written. |

The pre-existing environment-dependent installer test remains skipped because
its private fresh-install/GET_DDL evidence is not shared. No new skip is added.
Mock/AppTest, fake-executor and static checks are not Snowflake engine,
transaction, concurrent-write or employee-browser acceptance.

The F4 new no-deletion assertion initially assumed three users, but the existing
auth store also seeds prototype users. It now compares the exact before/after
user-ID sets instead of guessing a count. No original audit assertion changed.
The local Streamlit skill discovery again reported its missing bundled skill
file; no web fallback or package installation was performed.

## Original audit repro against R3

Both files are kept under docs, outside the unchanged default `testpaths=tests`:

```powershell
& '../../.venv/Scripts/python.exe' -m pytest docs/audit/repro/test_staff_audit.py -q --tb=short --basetemp=.local/r3-audit-original-temp
& '../../.venv/Scripts/python.exe' -m pytest docs/audit/repro/test_staff_audit_r3_locators.py -q --tb=short --basetemp=.local/r3-audit-locator-temp
```

- **Unmodified audit file:** 5 passed, 4 failed in 9.64s. A01/A02/A03/A05/A08
  pass; A06/A07/A09 fail as deferred. A04 raises KeyError for the obsolete
  `admin_confirm_user_delete` key, rather than failing the old True/False
  assertion. This is a stale locator caused by the required user-specific key.
- **Locator-only companion:** 6 passed, 3 failed in 10.54s. Only the two A04
  checkbox lookups change to find the same visible label; every original
  assertion remains. A01/A02/A03/A04/A05/A08 pass; A06/A07/A09 still fail.
- The Daily-page audit harness substitutes an equivalent native selectbox for
  the display-only segmented row filter because installed AppTest cannot
  serialize that control on rerun. Actual page commit/error code remains in use.
- These intentional deferred failures are retained and reported, not hidden by
  xfail/skip or counted as full-suite passes. The full-suite default test paths
  are unchanged from R2; run the separate docs probes explicitly as shown.

## Runtime manifest and deployment boundary

The candidate has **95 runtime artifacts**: one more than R2, the pure selector
helper included automatically by the existing `app/services/*.py` artifact rule.
Against the saved 89-file deployment manifest, there are **23 modified, 6 new,
0 deleted** files. All reasons and current hashes are updated in
`DELIVERY_RUNTIME_DIFF_20261030.json` and the checklist table.
The exact artifact-count assertion changes from 94 to 95 to reflect that added
module; baseline count, per-file hash checks and the no-deletion assertion remain.
No target, entry, runtime, warehouse, authentication or grants change.

The protected source comparison includes connection/continuity/record safety,
authentication/security, navigation/entry, migration/mappings, date repair,
supplements and quota_position/flock_stock/rules. R2 and audit commits remain
`7b14864713779253b329e2243af3fca62b416cbb` and
`3e0705953dedac05d1c125f783caa2250f9bcf52` respectively.
No fresh live source snapshot was obtained or claimed.

The checklist adds required manual checks for producer-record confirmation
reset, user-delete target confirmation reset, and historical Salmonella result
filter visibility. These are future checks, not completed browser acceptance.
Company deployment requires separate authorization and a then-current drift/
rollback check. Do not run migrations, SQL08/SQL18, date repairs or supplements
for this UI release.

## Deferred / human decisions

The handover's Known issues for later now records:

- **A06:** Admin updates lack reviewed-version CAS; backend unchanged.
- **A07:** Two-admin last-admin invariant can race; backend unchanged. The
  separate fake-executor probe proves call order, not a real engine race.
- **A09:** Duplicate parent IDs can multiply Salmonella reports; actual data
  health Q01 has not been run and no live duplicates are asserted.
- **A03 backend:** UI reconfirmation does not provide a reviewed origin/version
  to Flock event persistence; concurrent review-time origin protection remains.

No new business answers were invented. Stock inclusion, Count priority, quota
units/opening evidence/lease policy and the existing provisional entry policy
remain as documented; the calculation stays unestablished. No authentic user,
historical record or relationship was changed in testing.

## Git delivery

Push only `delivery-candidate-r3-20261030` normally to the existing origin. No
force-push, main merge, frozen-branch change or settings change is allowed.
The commit containing this report cannot embed its own SHA; after normal push,
verify and print the exact remote SHA with:

```powershell
git ls-remote origin delivery-candidate-r3-20261030
```

The final delivery message records that independently checked hash.
