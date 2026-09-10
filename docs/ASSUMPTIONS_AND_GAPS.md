# Assumptions and Gaps

> All entries below are **inferences or placeholders** until the actual Dataverse
> (EIMS) metadata is obtained and inspected.

## Design Assumptions

### Data Model

1. **ACCOUNT 1:N FACILITY 1:N FLOCK** — This parent-child chain is inferred from
   observation. Dataverse may use different relationship names, cardinalities, or
   intermediary entities.

2. **FLOCK 1:N FLOCK_TRANSACTION** — Inferred. Actual EIMS may use a different
   transaction model or embed transaction data directly.

3. **PRODUCTION_RECORD.FLOCK_ID** — This is a **wholly fabricated** provisional link.
   The actual EIMS may link production to flock, facility, or account via different
   keys, or may store production data in a completely different structure (e.g.,
   denormalized form-based records).

4. **Surrogate UUID primary keys** — Dataverse uses GUIDs. Our UUIDs are stand-ins.
   The actual mapping from our `*_ID` columns to Dataverse GUIDs is unknown.

5. **Column data types** — Approximations. VARCHAR lengths, NUMBER precision, and
   DATE vs DATETIME choices are guesses.

6. **Choice/Option-set values** — Statuses ("Active", "Inactive", "Closed", "Depopulated",
   "Planned"), facility types ("Pullet", "Layer", "Other"), egg colours, disposal
   methods, size bands, and transaction types are educated guesses based on
   domain knowledge. Actual EIMS option sets may differ.

### Production Workflow

7. **CSV Column Format** — The expected columns in the production CSV template are
   inferred. The actual format may differ. CSV ingestion is designed to gracefully
   handle missing/extra columns.

8. **Rejected vs Loss Separation** — We support separate `REJECTED` and `LOSS` values
   as well as a legacy `LEGACY_REJECT_LOSS_TOTAL`. The actual EIMS may have different
   names for these metrics.

9. **Egg Size Breakdown** — Modeled as a normalized child table. EIMS may use wide
   columns or a different structure entirely.

### Reporting

10. **Field groups** — The report builder groups fields into Account, Contact,
    Facility, Flock, and Production areas. These groupings are logical and may
    not reflect the actual EIMS form/page structure.

## Known Gaps

| # | Gap | Impact | Resolution |
|---|-----|--------|------------|
| G1 | Unknown Dataverse table names | All CREATE TABLE statements use provisional logical names | Wait for Dataverse metadata |
| G2 | Unknown Dataverse column names | Column naming convention is our best guess | Wait for Dataverse metadata |
| G3 | Unknown relationship cardinality | 1:N assumptions may need revision (N:N, polymorphic lookups) | Wait for Dataverse metadata |
| G4 | Unknown required/optional rules | All columns default to nullable; validation is minimal | Wait for Dataverse metadata + business input |
| G5 | Unknown lookup targets | Lookup fields unknown; we treat everything as direct references | Wait for Dataverse metadata |
| G6 | Unknown calculated fields | No calculated/rollup fields replicated | Wait for Dataverse metadata |
| G7 | Unknown Power Automate flows | Import/transform/notification logic unknown | Wait for Dataverse metadata |
| G8 | Unknown import/export mechanisms | Our CSV pipeline may not match existing EIMS processes | Obtain sample CSVs + process documentation |
| G9 | Unknown record counts | Synthetic data scale is arbitrary | Get approximate EIMS record counts |
| G10 | Unknown quota business rules | Quota module is placeholder only | Phase 2 — requires business analysis |
| G11 | Unknown Salmonella business rules | Disease test module is placeholder only | Phase 2 — requires business analysis |
| G12 | No real CSV samples | CSV template format is inferred | Obtain sample production CSVs from Sara |
| G13 | Unknown barn/grader identity encoding | Grader numbers and barn identities are synthetic | Obtain real identity conventions |

## Temporary Workarounds

1. **MockRepository** — All data is in-memory and ephemeral. No persistence.
2. **Synthetic data** — Generated from seeded random pools. Not representative of real patterns.
3. **PRODUCTION-to-FLOCK provisional link** — Fabricated random assignment for report demo.
4. **No authentication** — Not needed for v0.1 prototype.
5. **No error handling on Snowflake path** — SnowflakeRepository stub raises NotImplementedError
   for write operations.