# Streamlit message-size audit — 2026-11-03

Static inspection only. No database was queried. Snowflake repository reads
return pandas DataFrames; no `.to_pandas()` call exists in this release. Unless
noted below, the shared repository methods use `SELECT *` with no `LIMIT`
(`data/repositories/snowflake.py:482-499`). A UI filter applied after that call
does not reduce the database result or initial Python memory use.

Risk ratings describe the chance of a large Streamlit browser message, not data
correctness or write safety.

## High risk

| Page / service | UI and query evidence | Table/result and scope | Risk |
|---|---|---|---|
| Record Review — Producer matching | `app/pages/21_Record_History.py:30-32`; repository at `data/repositories/snowflake.py:1838` | Whole `REPORTING.VW_PRODUCTION_SUMMARY`; no filter or limit; all unmatched/candidate columns are sent to `st.dataframe`. | **High** — production can grow continuously and the grid is eager. |
| Record Review — Original files | `app/pages/21_Record_History.py:180-198`; `data/repositories/continuity.py:156-157,273-275,295-328` | Whole `APP.SOURCE_FILE` metadata has no limit. The selected file is filtered, but every linked `RAW.IMPORT_RAW_ROW` / historical `RAW.MIGRATION_RAW_ROW` is rendered; expanded details include `RAW_DATA`, `NORMALIZED_DATA` and validation VARIANT values. | **High** — a single large file can produce a very large Arrow message; the detail expander does not provide server-side pagination. |
| Flock — Matched Production Records | `app/pages/5_Flocks.py:138-142`; repository at `data/repositories/snowflake.py:1838` | Loads the whole production summary, then filters `FLOCK_ID` in pandas; no SQL filter or limit. All columns for matches are rendered. | **High** — every Flock detail visit first materializes the full production table. |
| Production Data | `app/pages/2_Production_Data.py:28,155`; repository at `data/repositories/snowflake.py:1838` | Whole production summary is loaded, filtered in pandas, and displayed; no limit. | **High** — primary production browse path grows without a bound. |
| Report Center and custom report service | `app/pages/4_Reports.py:137,253,293`; `app/services/report_center.py:146-179,190-298`; `app/services/report_builder.py:215-260,290-351` | Custom reports call whole-table methods when users leave filters blank. Legacy report builder eagerly loads Accounts, Facilities and Flocks and may also load all Production, Quota Registration, Quota Transaction or Salmonella rows before joining. No row cap before `st.dataframe`. | **High** — joins can widen/multiply frames and the final result has no browser row limit. |
| Migration history / RAW review | `app/pages/17_Migration_Import.py:202-281,340,382`; `data/repositories/snowflake.py:745-750,1389-1399` | Whole `RAW.MIGRATION_BATCH` history has no limit. Selected-batch rows are filtered but unbounded and can contain `RAW_DATA`, `NORMALIZED_DATA`, `CORRECTED_DATA`, validation messages, and error text. | **High** — large migration batches can carry multiple VARIANT payloads per row. |

## Medium risk

| Page / service | UI and query evidence | Table/result and scope | Risk |
|---|---|---|---|
| Flock Transactions | `app/pages/6_Flock_Transactions.py:25,59`; repository at `data/repositories/snowflake.py:605-612` | Whole `CORE.FLOCK_TRANSACTION` plus whole Flock, Account and Facility lookup tables; list filtering is in pandas; no limit. Grid sends selected transaction columns. | **Medium** — unbounded activity table, although the displayed frame is narrow. |
| Quota Registrations | `app/pages/7_Quota_Registrations.py:43-44,113`; repository at `data/repositories/snowflake.py:624-632` | Whole `CORE.QUOTA_REGISTRATION` and Accounts; no limit. | **Medium** — unbounded list with a moderate column set. |
| Quota Transactions and quota-usage service | `app/pages/8_Quota_Transactions.py:32-34,140,151`; `app/services/quota_usage.py:55-95,123-140`; repository at `data/repositories/snowflake.py:641-655` | Whole `CORE.QUOTA_TRANSACTION`, Quota Registration and Account tables; no limit. The list is narrowed in pandas. Usage renders small summaries but first consumes all owner activity for the Account. | **Medium** — the activity table is unbounded; summary rendering reduces the browser payload but not the backend fetch. |
| Audit Log | `app/pages/16_Audit_Log.py:23-66` | `APP_USER_AUDIT` through `store.list_audit(..., limit=5000)`; explicit 5,000-event cap, filters applied after load; `DETAILS` is rendered and originates from a VARIANT field. | **Medium** — bounded, but 5,000 rows with large details can still exceed a practical message size. |
| Flocks, Facilities, Facility Details and Farm Locations lists | `app/pages/5_Flocks.py:37-39,81`; `app/pages/11_Facilities.py:32-33,77`; `app/pages/13_Facility_Details.py:26-28,75`; `app/pages/18_Farm_Locations.py:30,80` | Whole corresponding CORE tables and lookup tables; no SQL limit. Keyword/account filters are generally applied after retrieval. | **Medium** — bounded-width grids, but all master rows are loaded and sent. |
| Salmonella browse and report service | `app/pages/9_Salmonella_Tests.py:28-29,84`; `app/pages/10_Salmonella_Report.py:29,62`; `app/services/salmonella_reporting.py:32-36`; repository at `data/repositories/snowflake.py:701-710` | Whole `CORE.SALMONELLA_TEST`, Flock, Account and Facility tables when filters are blank; no limit. | **Medium** — the report can send the full joined result. |
| EIMS Reference Data | `app/pages/20_EIMS_Reference_Data.py:33,46,59`; repository methods at `data/repositories/snowflake.py:539-551,695-699,1839-1845` | Contacts, Quota Allocations and `CORE.DIM_EFC_DATE`; optional filters, no limit. | **Medium** — date dimensions and contacts can be large, though each displayed grid is comparatively narrow. |
| Change history candidate selectors | `app/pages/21_Record_History.py:210-242` | The selected entity method loads the whole candidate table without a limit before one ID is chosen. Per-record revisions are safely filtered and capped at 50 by `data/repositories/continuity.py:526-552`. | **Medium** — bounded history payload, unbounded selector source. |
| Accounts / relationships page | `app/pages/3_Accounts_Facilities_Flocks.py:74,125,241-265` | Whole Account list; related tables are account/Flock filtered, but the Matched Production section is rendered without a row limit. | **Medium** — relation filters help, while large accounts can still return many activity rows. |

## Low risk or bounded paths

| Page / service | Evidence | Reason |
|---|---|---|
| Dashboard recent imports | `app/Home.py:146-150` | The repository may load all import batches, but only `.head(10)` is sent to the browser. **Low** browser-message risk. |
| Production Import preview | `app/pages/1_Production_Import.py:138,162` | Raw preview uses `.head(50)`; accepted/rejected preview is tied to one uploaded workbook. **Low** for ordinary files, although upload size itself is not capped here. |
| Daily Flock & Quota Import | `app/pages/19_Daily_Flock_Quota_Import.py:115-173` | Main review grid uses `.head(500)` and persisted rows are import-scoped. **Low/medium**, depending on per-file preview sizes. |
| Per-record Change history | `app/pages/21_Record_History.py:238-242`; `data/repositories/continuity.py:526-552` | SQL filters by entity type and ID and applies `LIMIT 50` (maximum allowed request 200); displayed differences omit raw BEFORE/AFTER payloads. **Low**. |
| Flock event history and latest Count rows | `app/pages/21_Record_History.py:91`; `app/pages/5_Flocks.py:113-123` | Flock-ID scoped; latest Count grid is latest-day only. No numeric limit, but normal cardinality is per record. **Low**. |

## Cross-cutting finding

The common source of the risk is the generic `_filtered()` implementation at
`data/repositories/snowflake.py:482-499`: an empty filter set becomes unbounded
`SELECT *`. No shared pagination contract exists. This report makes no change to
that repository because connection and data-access code is protected by the task.
