# Flock Status as-of investigation — checkpoint, not a completed fix

Base: latest fetched main `2c75cf9ea93ec919448571a39fdada3e8c5fda35`, including Production PDF and Facility Housing. Branch: `codex-flock-status-asof-20261112`. Read-only source/fixture investigation; no Snowflake queries, deployment, application edits or data changes.

## 40378 / producer registration 7169 / 2026-06-19

The exact data-specific cause is **not yet confirmed**. No DEV query results for this flock at this date are available in this task. The committed fixture `releases/employee_trial_2026_10_29/tests/fixtures/producers_over_quota/DEV_FlockCurrent.csv:52` shows placement 2026-04-16, hatch 2025-12-04 and Count Date 2026-10-02. That is a later report projection, not the complete transaction history. It does not prove that an earlier Count/Delivery is absent.

Verified code path: `app/services/flock_reports.py::build_flock_status_report` calls `flock_age_report.py::build_flock_age_report`, which calls `flock_current_report.py::build_flock_current_report`. Paths in this paragraph are relative to `releases/employee_trial_2026_10_29/`.

The shared builder keeps Count/Delivery observations only when their transaction date is on or before the report date. It prefers Count when both types share the latest date. With no observation it reports “No Count or Delivery on or before report date”; a same-day quantity/source conflict or invalid quantity also leaves Counted unknown. With a known Placement Date, Inventory is still calculated only when Counted is usable. Unknown Inventory is displayed as “—”. Missing placement is another possible reason, but the committed projection has a placement date for 40378.

Consequently the October observation cannot supply June 19 inventory. Establishing whether the June display is a correct unknown, missing source data or a separate defect requires the flock row and its complete dated Count/Delivery rows. No June quantity has been fabricated or inferred from the October quantity or FLOCK.BIRD_COUNT.

## Upcoming flocks

The requested change is **not implemented in this checkpoint**. Main already compares Placement Date to the report date, and uses Hatch Date only to calculate Flock Age; there is no explicit Hatch Date inclusion filter. However, the future-placement branch is nested under the usable-Counted condition. Thus a future placement without a usable observation on/before the report date currently has Inventory/Up. Flocks unknown, rather than guaranteed Inventory 0.

Current Up. Flocks holds the bird quantity, not the number of flock rows. A future implementation should preserve that established unit unless a different rule is explicitly requested. Inventory 0 for future placement can be separated from observation availability, but the quantity source for Up. Flocks when no dated observation yet qualifies must be settled rather than guessed (for example an initial Delivery after the as-of date versus a stored Bird Count). Shared-builder changes would also affect Flock Current, by Producer, Flock Age, Flock Status/by Producer and downstream report callers, so they require regression coverage before pushing code.

## Data needed — draft read-only checks, not executed

These queries distinguish the flock's stored fields from actual transaction evidence, matching both permit and producer registration rather than assuming permit uniqueness. Inspect every returned flock identity if more than one is returned.

```sql
SELECT f.FLOCK_ID, f.PERMIT_NUMBER, a.REGISTRATION_NUMBER,
       f.STATUS, f.FLOCK_QUOTA_TYPE, f.HATCH_DATE, f.PLACEMENT_DATE,
       f.EST_DISPOSAL, f.DISPOSAL_DATE, f.BIRD_COUNT
FROM EFNS_DEV.CORE.FLOCK f
JOIN EFNS_DEV.CORE.ACCOUNT a ON a.ACCOUNT_ID = f.ACCOUNT_ID
WHERE f.PERMIT_NUMBER = '40378' AND a.REGISTRATION_NUMBER = '7169';

SELECT ft.FLOCK_ID, ft.FLOCK_TRANSACTION_ID, ft.TRANSACTION_TYPE,
       ft.TRANSACTION_DATE, ft.QUANTITY, ft.COUNT_SOURCE_LABEL
FROM EFNS_DEV.CORE.FLOCK_TRANSACTION ft
JOIN EFNS_DEV.CORE.FLOCK f ON f.FLOCK_ID = ft.FLOCK_ID
JOIN EFNS_DEV.CORE.ACCOUNT a ON a.ACCOUNT_ID = f.ACCOUNT_ID
WHERE f.PERMIT_NUMBER = '40378' AND a.REGISTRATION_NUMBER = '7169'
  AND ft.TRANSACTION_TYPE IN ('Count', 'Delivery')
ORDER BY ft.TRANSACTION_DATE, ft.TRANSACTION_TYPE, ft.FLOCK_TRANSACTION_ID;
```

Keep future rows in the second query so a late first Delivery can be distinguished from no Delivery. Only observations through 2026-06-19 qualify under the current rule. An existing CSV export containing these fields is sufficient; no direct Snowflake access is needed by this agent.

## Tests, shipping and blockers

No application change is complete and no fix-specific tests or full suites have run for this checkpoint. No shipped files changed, and no manifest changed. The only committed change is this investigation document at repository-root docs/codex_reports. Previously reported main-baseline test results are not claimed as validation of an as-of fix.

Still required: source evidence for 40378; a confirmed upcoming-quantity fallback when all transactions are future-dated; implementation and synthetic as-of/future-hatch/unknown/conflict regressions; a full release and root run and manifest regeneration for any eventual runtime changes. A missing earlier observation would be a source-data gap, not a justification to substitute a later Count silently. That classification cannot yet be made from the available projection alone.
