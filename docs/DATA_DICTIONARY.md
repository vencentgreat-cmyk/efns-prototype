# EFNS Data Dictionary

**Status:** implemented DEV structure, with remaining business definitions requiring confirmation. This introductory matrix is not the full physical dictionary. The 12 October 2026 metadata-backed workbook covers 27 deployed tables (440 fields) and four views (80 outputs). Repository writes explicitly generate future business timestamps in UTC; updates preserve `CREATED_AT`. Historical NTZ values with unverified provenance remain stored-time values, not presumed UTC. Aware timestamps can be displayed in `America/Halifax`; unknown-basis NTZ is labelled as unverified. Security/audit use `TIMESTAMP_TZ`.

| Entity | Primary key | Required fields | Foreign keys | Main optional fields |
|---|---|---|---|---|
| Account | `ACCOUNT_ID` | `ORGANIZATION_NAME` | self lookups through `PARENT_ACCOUNT_ID`, `GRADING_STATION_ACCOUNT_ID`, `PULLET_GROWER_ACCOUNT_ID` | registration; email/phone/fax/website; three address lines, city, province, postal code, country, latitude/longitude; Province of Registration; Spent Fowl Plans; Default on Reports; No SVG; description; status; 14 role flags |
| Farm Location | `FARM_LOCATION_ID` | account, location name | Account | two address lines, city, province, postal code, phone, status |
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
| Migration Batch | `MIGRATION_BATCH_ID` | package hash, mapping version, workflow status, counts | — | operator, commit time |
| Migration File | `MIGRATION_FILE_ID` | batch, filename, entity, SHA-256 | Migration Batch | size, row count, internal-stage path |
| Migration Raw Row | `(MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID)` | batch, file, entity, source row, raw JSON, validation status | Migration Batch | source/target ID, normalized JSON, match state and messages |
| Migration ID Map | `MIGRATION_ID_MAP_ID` | batch, RAW row ID, entity, source ID, target ID | Migration Batch; composite RAW source identity | commit status; one lineage per Ready source row, not one per date target |

Business GUID identities use deployed text columns; RAW batch/row and correction IDs have their own lengths. `DIM_EFC_DATE.DAY` is a DATE identity, not a GUID. Exact deployed lengths, precision, nullable status and defaults are in the metadata-backed dictionary and GET_DDL export. Repository date bindings preserve SQL NULL. Account self-link placeholders are normalized separately, with real unknown parent IDs rejected rather than erased.

`MATCH_STATUS` values are `UNMATCHED`, `UNIQUE_CANDIDATE`, `NO_CANDIDATE`, `MULTIPLE_CANDIDATES`, and `CONFIRMED`. EIMS imports start `UNMATCHED`; no relationship ID is invented.

Dataverse names, choices, requiredness, cardinalities, alternate keys, deletion behavior, sample fields, and identity mapping remain provisional. RAW, CORE, history and reporting sources use standard Snowflake tables. Hybrid Tables may be evaluated after workload and constraint testing; this design does not depend on them.

Historical field rules live in explicit versioned contracts. V3 uses the verified logical headers in the complete 14-file Jensen export; V1/V2 compatibility remains available. Historical, daily Flock/Quota and Production imports are separate workflows. Confirmed logical field names do not by themselves confirm every unit, state code or balance formula.

## Facility/Flock clarification (9 October 2026)

The introductory required-field matrix describes daily entry, not all historical
nullability. The following deployed properties were read from DEV metadata on
9 October 2026; no DDL was executed. Sara's 8 October confirmation supersedes
any permanent one-Flock-per-Facility assumption.

| Table / field | Grain or definition | Deployed type / nullable | Relationship / rule |
| --- | --- | --- | --- |
| FACILITY | One identified facility, owned by one Account | See actual column inventory | Zero to many Flocks, sequential or concurrent; no confirmed maximum |
| FLOCK | One identified flock, not a facility slot | See actual column inventory | Original GUID retained; no overwrite of earlier flocks |
| FLOCK.FACILITY_ID | Optional reference to one facility | VARCHAR / YES | FK_FLOCK_FACILITY -> CORE.FACILITY.FACILITY_ID; no UNIQUE; daily entry requires it |
| FLOCK.ACCOUNT_ID | Flock's recorded Account | VARCHAR / NO | FK_FLOCK_ACCOUNT -> CORE.ACCOUNT.ACCOUNT_ID; equality with facility owner checked by application/migration |
| FACILITY.ACCOUNT_ID | Facility's recorded Account | VARCHAR / NO | FK_FACILITY_ACCOUNT -> CORE.ACCOUNT.ACCOUNT_ID; sharing is not cross-Account authorization |
| FLOCK.PLACEMENT_DATE | Recorded placement date, when available | DATE / YES | Unknown remains null; overlapping flocks are permitted |
| FLOCK.DISPOSAL_DATE | Recorded disposal date, when available | DATE / YES | Never filled from estimate; whether this ends all occupancy requires confirmation |
| FLOCK.EST_DISPOSAL | Forecast disposal date | DATE / YES | Not actual disposal and not evidence a facility is vacant |

These standard-table PK/FK declarations describe relationships; application
checks provide reference/ownership validation. SQL nullability is distinct from
daily requiredness. See [design review and ERD](FACILITY_FLOCK_DESIGN.md).

Report output aliases (not new CORE columns): `FLOCK_ACCOUNT_ID/NAME` refer to
the Flock's Account; `FACILITY_ACCOUNT_ID/NAME` refer to the referenced Facility's
Account; `PRODUCER_ACCOUNT_NAME` resolves the production record's unchanged
`PRODUCER_ACCOUNT_ID`. `REPORT_FACILITY_ID` is display-only, using the production
Facility reference or, when null, its linked Flock's Facility. This does not
change stored relationships or business ownership. The prepared VW_FLOCK_DETAIL
SQL exposes both Account roles; it has not been applied to DEV in this change.

Prepared production report aliases: `REPORT_FACILITY_SOURCE` identifies a direct
production reference, linked Flock reference, or no available reference.
`FACILITY_REFERENCE_DIFFERENCE` compares both original references only when
both are present; differing references remain an unresolved review flag, not
proof of an error. `FLOCK_FACILITY_ID` preserves the Flock-side reference alongside
the unmodified production `FACILITY_ID`. These are display-only, not CORE fields.

Prepared size-view outputs add the exact child `SIZE_BREAKDOWN_ID`; null denotes
a no-size placeholder, not a persisted child. Both year and week come from
PRODUCTION_RECORD. Prepared summary output adds `TOTAL` as Source Total, distinct
from TOTAL_RECEIVED; its business units/meaning are not newly inferred.
