# Target Model Draft

> **STATUS: PROVISIONAL v0.1**
> This document describes the proposed Snowflake schema. All table/column names,
> relationships, and constraints are drafts. They will be finalized after Dataverse
> metadata is obtained.

---

## Design Principles

1. **Schema separation:** RAW (ingestion) → CORE (normalized) → REPORTING (derived)
2. **Snowflake-native:** Use VARIANT for flexible ingestion, TIMESTAMP_NTZ for audit
3. **Normalized:** Production size bands in child table, not wide columns
4. **History-preserving:** Flock transactions vs overwriting
5. **Modular:** Repository pattern insulates UI from backend

---

## RAW Schema

### IMPORT_BATCH

| Column | Type | Notes |
|--------|------|-------|
| IMPORT_ID | VARCHAR(36) PK | Surrogate |
| FILENAME | VARCHAR(500) | Original CSV filename |
| SOURCE | VARCHAR(255) | Grader name / source identifier |
| REPORTING_YEAR | INTEGER | |
| REPORTING_WEEK | INTEGER | |
| UPLOAD_TIMESTAMP | TIMESTAMP_NTZ | |
| STATUS | VARCHAR(50) | Uploaded / Validated / Committed / Error |
| ROW_COUNT | INTEGER | |
| ERROR_COUNT | INTEGER | |
| NOTES | VARCHAR(1000) | |

### IMPORT_RAW_ROW

| Column | Type | Notes |
|--------|------|-------|
| RAW_ROW_ID | VARCHAR(36) PK | Surrogate |
| IMPORT_ID | VARCHAR(36) FK | → IMPORT_BATCH |
| ROW_NUMBER | INTEGER | Line number in source CSV |
| RAW_DATA | VARIANT | Full row as JSON (schema-flexible) |

---

## CORE Schema

### ACCOUNT

| Column | Type | Notes |
|--------|------|-------|
| ACCOUNT_ID | VARCHAR(36) PK | PROVISIONAL |
| REGISTRATION_NUMBER | VARCHAR(64) | PROVISIONAL |
| ORGANIZATION_NAME | VARCHAR(255) NOT NULL | |
| ADDRESS_LINE1 | VARCHAR(255) | |
| CITY | VARCHAR(100) | |
| PROVINCE | VARCHAR(50) | |
| POSTAL_CODE | VARCHAR(20) | |
| CONTACT_NAME | VARCHAR(255) | |
| CONTACT_PHONE | VARCHAR(50) | |
| CONTACT_EMAIL | VARCHAR(255) | |
| LICENCE_NUMBER | VARCHAR(64) | PROVISIONAL |
| PRODUCER_ROLE | BOOLEAN | |
| BREEDER_ROLE | BOOLEAN | |
| HATCHERY_ROLE | BOOLEAN | |
| GRADER_ROLE | BOOLEAN | |
| STATUS | VARCHAR(50) | PROVISIONAL |
| CREATED_AT | TIMESTAMP_NTZ | |
| UPDATED_AT | TIMESTAMP_NTZ | |

### FACILITY

| Column | Type | Notes |
|--------|------|-------|
| FACILITY_ID | VARCHAR(36) PK | |
| ACCOUNT_ID | VARCHAR(36) FK | → ACCOUNT |
| FACILITY_NAME | VARCHAR(255) NOT NULL | |
| FACILITY_TYPE | VARCHAR(50) | pullet / layer / other (PROVISIONAL) |
| STATUS | VARCHAR(50) | |
| ACTIVATION_DATE | DATE | |
| CONSTRUCTION_DATE | DATE | |
| CLOSURE_DATE | DATE | |
| DESTRUCTION_DATE | DATE | |
| INACTIVE_DATE | DATE | |

### FLOCK

| Column | Type | Notes |
|--------|------|-------|
| FLOCK_ID | VARCHAR(36) PK | |
| ACCOUNT_ID | VARCHAR(36) FK | → ACCOUNT |
| FACILITY_ID | VARCHAR(36) FK | → FACILITY (nullable) |
| FLOCK_NUMBER | VARCHAR(64) | Business number |
| LICENCE_NUMBER | VARCHAR(64) | PROVISIONAL |
| BIRD_COUNT | INTEGER | |
| PLACEMENT_DATE | DATE | |
| HATCH_DATE | DATE | |
| EGG_COLOUR | VARCHAR(50) | PROVISIONAL |
| EST_PROD_COMPLETION | DATE | |
| EST_DISPOSAL | DATE | |
| ACTUAL_DISPOSAL | DATE | |
| DISPOSAL_METHOD | VARCHAR(100) | |
| STATUS | VARCHAR(50) | PROVISIONAL |

### FLOCK_TRANSACTION

| Column | Type | Notes |
|--------|------|-------|
| FLOCK_TRANSACTION_ID | VARCHAR(36) PK | |
| FLOCK_ID | VARCHAR(36) FK | → FLOCK |
| TRANSACTION_TYPE | VARCHAR(50) | PROVISIONAL |
| QUANTITY | INTEGER | |
| TRANSACTION_DATE | DATE | |
| NOTES | VARCHAR(500) | |

### PRODUCTION_RECORD

| Column | Type | Notes |
|--------|------|-------|
| PRODUCTION_ID | VARCHAR(36) PK | |
| IMPORT_ID | VARCHAR(36) FK | → IMPORT_BATCH |
| FLOCK_ID | VARCHAR(36) FK(?) | **PROVISIONAL** — fabricate for demo |
| GRADER_NUMBER | VARCHAR(50) | |
| BARN_IDENTITY | VARCHAR(100) | |
| FLOCK_AGE | INTEGER | weeks |
| EGG_COLOUR | VARCHAR(50) | |
| NET_WEIGHT | NUMBER(12,4) | |
| NET_BOXES | NUMBER(12,4) | |
| NET_PER_BOX | NUMBER(12,4) | |
| TOTAL_RECEIVED | NUMBER(12,4) | |
| REJECTED | NUMBER(12,4) | NULL if legacy combined value used |
| LOSS | NUMBER(12,4) | NULL if legacy combined value used |
| LEGACY_REJECT_LOSS_TOTAL | NUMBER(12,4) | Historical; NULL when separated |
| TOTAL_ACCEPTED | NUMBER(12,4) | |
| CREATED_AT | TIMESTAMP_NTZ | |

### PRODUCTION_SIZE_BREAKDOWN

| Column | Type | Notes |
|--------|------|-------|
| SIZE_BREAKDOWN_ID | VARCHAR(36) PK | |
| PRODUCTION_ID | VARCHAR(36) FK | → PRODUCTION_RECORD |
| SIZE_BAND | VARCHAR(50) | PROVISIONAL |
| QUANTITY | NUMBER(12,4) | |

### Quota Placeholders (Phase 2)

QUOTA_REGISTRATION, QUOTA_TRANSACTION — see `sql/02_core_tables.sql`.

### Disease Testing Placeholder (Phase 2)

DISEASE_TEST — see `sql/02_core_tables.sql`.

---

## REPORTING Schema

Four views:
1. `VW_PRODUCTION_SUMMARY` — flattened production + import metadata
2. `VW_PRODUCTION_SIZE_DETAIL` — production with normalized size breakdowns
3. `VW_ACCOUNT_FACILITY` — accounts with their facilities
4. `VW_FLOCK_DETAIL` — flocks with account and facility context

See `sql/04_reporting_views.sql`.

---

## Entity Relationship Diagram (Provisional)

```
IMPORT_BATCH
     │ 1:N
     ↓
PRODUCTION_RECORD ←── PRODUCTION_SIZE_BREAKDOWN
     │                         (1:N)
     │ PROVISIONAL FLOCK_ID
     ↓ (provisional)
FLOCK ────────────── FLOCK_TRANSACTION
  │                        (1:N)
  │ 1:N
  ↓
FACILITY
  │ 1:N
  ↓
ACCOUNT
```

Direct relationships (confirmed for v0.1 purposes):
- ACCOUNT 1:N FACILITY (PROVISIONAL)
- FACILITY 1:N FLOCK (PROVISIONAL)
- FLOCK 1:N FLOCK_TRANSACTION (PROVISIONAL)
- IMPORT_BATCH 1:N PRODUCTION_RECORD
- PRODUCTION_RECORD 1:N PRODUCTION_SIZE_BREAKDOWN

**IMPORTANT:** The FLOCK → PRODUCTION_RECORD link (via FLOCK_ID) is
completely fabricated for this prototype. The actual EIMS may use a
different mechanism entirely.

---

## Migration Notes

When Dataverse metadata becomes available:

1. Map Dataverse logical names → our provisional column names
2. Add columns we missed; remove columns that don't correspond to reality
3. Correct data types (e.g., Dataverse Whole Number → INTEGER, Decimal → NUMBER)
4. Wire real foreign keys
5. Replace GUIDs with actual Dataverse GUIDs if needed
6. Map choice/integer values to labels
7. Handle polymorphic lookups (e.g., `regardingobjectid` → multiple target tables)
8. Implement real business rules and validation