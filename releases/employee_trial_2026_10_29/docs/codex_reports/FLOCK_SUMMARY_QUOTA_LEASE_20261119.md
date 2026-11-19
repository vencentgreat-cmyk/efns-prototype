# Flock Summary and quota lease work - 19 November 2026

Base: fetched origin/main `6b5b8883d663552bdb651bd3e560541f94c1e808`, containing Task 1 `fd1637506533095134c88d5fd8fdc545f591dd6b`. Branch: `codex-flock-summary-lease-20261119`.

## Current quota calculation and persistence map

| Area | Current path | Meaning before Part E |
|---|---|---|
| Confirmed quota | `data/confirmed_quota_position.py:16` | Active owner registrations and transactions; RAW migrated inactive-state exclusion; latest Active Base by effective/creation date, or all eligible transactions if no Base; signed amounts, effective-date cutoff and lease expiry. Missing state evidence remains unknown. |
| Quota Summary / Details | `app/services/report_center.py:165`, `:218`, `:234` | Repository accounts/registrations/transactions plus bounded state evidence feed confirmed position. Summary is net; Details preserves gross increasing-type sums and repeated account totals. |
| Flock Age / Status utilization | `app/services/flock_age_report.py:22`; `app/pages/4_Reports.py:76` | Confirmed Egg Production owner positions supply account Quota, allocation and Inventory/Quota utilization. Shared inventory computation is separate. |
| Producers Over Quota | `app/services/producers_over_quota_report.py:20` | Same confirmed quota basis, existing Flock Status summary, producer inventory/confirmed quota, and the Task 1 overall total. |
| Quota transaction/lease/history reports | `app/services/quota_reports.py:59` | Active owner/registration scope; stored legacy Lease (In)/(Out) types, dates and signed confirmed-position evidence. History retains its existing running-balance/snapshot distinction. |
| Historical quota usage panel | `app/services/quota_usage.py:19`; `data/quota_position.py:89` | Separate evidence-gated draft. UI remains hidden; current occupancy/units and flock_stock remain PENDING. It is not the established report utilization calculation. |
| Entry, atomic save and history | `app/pages/8_Quota_Transactions.py`; `app/services/form_safety.py:71`; `data/record_safety.py`; `data/repositories/continuity.py:285` | Existing quota rows are stored in CORE.QUOTA_TRANSACTION, linked to the owner's registration, with related counterparty/date/count fields. Forms use idempotent creation or revision, existing serialization, permission checks and audit/revision conventions. |

## Part D: stopped at the explicitly required calendar gate

No Flock Summary report was made Available, and catalog counts were not changed. The existing production-week functions at `app/services/production_reports.py:62-95` validate YYYYWW, enforce start <= end, and obtain reporting year/week codes; they do not return week start/end dates. `app/services/report_center.py:317` explicitly rejects inferring calendar date ranges for Production reports.

CORE.DIM_EFC_DATE (`sql/02_core_tables.sql:301`) and its existing read method (`data/repositories/snowflake.py:1846`) contain DAY, EFC_YEAR, EFC_WEEK_NUMBER and other labels. The v3 migration maps these source attributes (`config/eims_migration_mapping_v3.json:258`). However, no existing tested resolver establishes production SOURCE_WEEK_CODE -> EFC day membership -> complete week start/end boundaries. The dimension's presence alone does not authorize choosing ISO weeks, a weekday anchor, or min/max dates from potentially partial mappings.

The requested instruction was to stop Part D if existing production-week logic does not provide start/end dates. Accordingly this commit records the gap instead of inventing a calendar or shipping a misleading runnable report. Completion needs a confirmed relation between production week codes and a verified complete date dimension (including year boundaries), plus synthetic week-boundary tests. No stock is summed across weeks and no zero-filled inventory is invented.

## Part E status

Calculation mapping is complete. Safe persistence requires a whole-period availability check inside the existing atomic quota-write boundary. The earlier explicit protected-write-path restriction is still unresolved; narrow authorization has been requested. Authentication, connection handling and lock implementation will not be changed.

No real names, producer quantities, new exports or legacy source files are included. No Snowflake calls, DDL execution, deployment or PR. Part D changes only this document and its live integrity-manifest entry. Part E will have a separate commit after the persistence boundary is resolved.
