# EFNS Data Dictionary

**Status:** provisional until Dataverse metadata is available. Python and DEV SQL use the same uppercase internal names. Every persisted entity has `CREATED_AT` and `UPDATED_AT` (`TIMESTAMP_NTZ`); the UI labels these “Created On” and “Last Updated”.

| Entity | Primary key | Required fields | Foreign keys | Main optional fields |
|---|---|---|---|---|
| Account | `ACCOUNT_ID` | `ORGANIZATION_NAME` | self lookups through `PARENT_ACCOUNT_ID`, `GRADING_STATION_ACCOUNT_ID`, `PULLET_GROWER_ACCOUNT_ID` | registration; email/phone/fax/website; three address lines, city, province, postal code, country, latitude/longitude; Province of Registration; Spent Fowl Plans; Default on Reports; No SVG; description; status; 14 role flags |
| Facility | `FACILITY_ID` | account, name | Account | type, status, lifecycle dates |
| Facility Detail | `FACILITY_DETAIL_ID` | facility, name | Facility | type, status, comments |
| Quota Registration | `QUOTA_ID` | registration, account, type | Account | name, status, effective/end dates, comments |
| Flock | `FLOCK_ID` | number, account, facility, permit, hatch date, bird count | Account, Facility; optional Detail/Quota | quota/status, lifecycle dates, egg colour, strain, parties, disposal, comments |
| Flock Transaction | `FLOCK_TRANSACTION_ID` | flock, type, quantity, date | Flock | notes |
| Quota Transaction | `QUOTA_TRANSACTION_ID` | type, quota, effective date, count, owner/related accounts | Quota, Account | end date, related quota/transaction, price, lease type, comments |
| Salmonella Test | `SALMONELLA_TEST_ID` | flock, account, permit, testing date, sample count, result | Flock, Account | inspector, received/sent, case/invoice, comments |
| Test Sample | `SALMONELLA_TEST_SAMPLE_ID` | test | Salmonella Test | reference, comments |
| Import Batch | `IMPORT_ID` | filename | — | source, SHA-256 hash, size, worksheet, period, counts, status, notes |
| Import Raw Row | `RAW_ROW_ID` | import, source row, RAW VARIANT | Import Batch | validation/match state, messages, matched IDs, audit |
| Production Record | `PRODUCTION_ID` | import, source type | Import; nullable Account/Facility/Flock | normalized EIMS fields, period, match audit |
| Production Size Breakdown | `SIZE_BREAKDOWN_ID` | production, size band | Production Record | quantity |

IDs are provisional `VARCHAR(36)` values. Quantities/counts are Snowflake `NUMBER`, business dates are `DATE`, and audit values are `TIMESTAMP_NTZ`. Exact column definitions and constraints are in `sql/02_core_tables.sql` and `sql/03_production_tables.sql`.

`MATCH_STATUS` values are `UNMATCHED`, `UNIQUE_CANDIDATE`, `NO_CANDIDATE`, `MULTIPLE_CANDIDATES`, and `CONFIRMED`. EIMS imports start `UNMATCHED`; no relationship ID is invented.

Dataverse names, choices, requiredness, cardinalities, alternate keys, deletion behavior, sample fields, and identity mapping remain provisional. RAW, CORE, history and reporting sources use standard Snowflake tables. Hybrid Tables may be evaluated after workload and constraint testing; this design does not depend on them.
