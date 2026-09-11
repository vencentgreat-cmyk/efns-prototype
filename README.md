# EFNS Internal Data System — Prototype v0.2

**Egg Farmers of Nova Scotia (EFNS)**

A Streamlit-based prototype for the next-generation internal data system,
targeting Snowflake as the cloud data platform.

---

## Quick Start

```powershell
# Run from the repository root
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m streamlit run app/Home.py
```

Open http://localhost:8501 in a browser.

---

## What This Prototype Demonstrates

| Feature | Status |
|---------|--------|
| Logical data model (ACCOUNT, FACILITY, FLOCK, PRODUCTION) | PROVISIONAL |
| EIMS workbook ingestion (RAW → normalized union model) | Working (mock) |
| Production data search/filter | Working |
| Accounts/Facilities/Facility Details CRUD | Working |
| Flock, transaction, Quota and Salmonella workspaces | Working (provisional rules) |
| Customizable report builder with CSV & Excel export | Working |
| Snowflake SQL (schemas: RAW, CORE, REPORTING) | Provisional DEV definitions; not executed |
| Synthetic data generator (deterministic, seeded) | Working |
| Modular repository pattern (Mock ↔ Snowflake) | Parameterized CRUD/import adapter; integration pending |

---

## Project Structure

```
efns-prototype/
├── app/
│   ├── Home.py                   # Entry point + grouped navigation
│   ├── ui.py                     # Shared visual system
│   ├── pages/
│   │   ├── 1_Production_Import.py
│   │   ├── 2_Production_Data.py
│   │   ├── 3_Accounts_Facilities_Flocks.py
│   │   └── 4_Reports.py
│   └── services/
│       ├── export.py             # Spreadsheet-safe exports
│       └── report_builder.py     # Dynamic report assembly
│
├── data/
│   ├── constants.py              # EIMS import constants and mappings
│   ├── importing.py              # Workbook read/normalize/validate helpers
│   ├── repositories/
│   │   ├── __init__.py           # Factory: get_repository()
│   │   ├── base.py               # Abstract BaseRepository
│   │   ├── mock.py               # In-memory MockRepository
│   │   └── snowflake.py          # Snowflake CRUD/import adapter
│   └── synthetic.py              # Synthetic data generator
│
├── sql/
│   ├── 01_setup.sql              # Database & schemas
│   ├── 02_core_tables.sql        # Operational entities (PROVISIONAL)
│   ├── 03_production_tables.sql  # Production & import tables
│   └── 04_reporting_views.sql    # Reporting views
│
├── sample_data/
│   └── production_sample_2025.csv
│
├── docs/
│   ├── AS_IS_MODEL.md
│   ├── BUSINESS_RULES.md
│   ├── DATAVERSE_DISCOVERY_CHECKLIST.md
│   ├── ASSUMPTIONS_AND_GAPS.md
│   ├── TARGET_MODEL_DRAFT.md
│   ├── DATA_DICTIONARY.md
│   └── DATAVERSE_TO_TARGET_MAPPING.csv
│
├── tests/
│   ├── test_phase1_2_regressions.py
│   ├── test_phase1_domain.py
│   └── test_synthetic.py
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## Architecture

### Repository Pattern

The UI talks to `BaseRepository`. Two implementations:

- **MockRepository** — in-memory pandas DataFrames. Used for local development.
- **SnowflakeRepository** — connects to Snowflake. Stub in v0.1, ready to expand.

Set `REPOSITORY_MODE=snowflake` in `.env` to switch (requires credentials).

### Data Flow

```
EIMS Workbook → Python Ingestion → RAW source rows (MockRepository)
                                       ↓
                               Validation / Transformation
                                       ↓
                               Transitional normalized production union
                                       ↓
                               REPORTING (Views, Report Builder)
                                       ↓
                               Streamlit Report / Export
```

### Schema

| Schema | Purpose |
|--------|---------|
| `EFNS_DEV.RAW` | Source-preserving import records |
| `EFNS_DEV.CORE` | Normalized operational/business entities |
| `EFNS_DEV.REPORTING` | Views and report-ready datasets |

---

## Important Notes

### Everything is PROVISIONAL

All table schemas, column names, relationships, and business rules are drafts.
**Do not treat these as the final model.** They will be revised after the
existing EIMS Dataverse metadata is reverse-engineered.

### What Needs Revision After Dataverse Access

See `docs/DATAVERSE_DISCOVERY_CHECKLIST.md` for the full list, but key items:

1. **Table names** — current logical names may not match Dataverse schema names
2. **Primary keys** — currently use UUID surrogates; actual EIMS may use GUIDs or other IDs
3. **Relationships** — all FKs are provisional; relationships may be 1:N, N:N, or have different cardinality
4. **Column types** — approximate; need actual Dataverse column types
5. **Choice/option-set values** — statuses, roles, types are educated guesses
6. **Required vs optional** — not yet confirmed
7. **Business rules** — data validation, quotas, Salmonella testing logic is not implemented
8. **Production-to-flock link** — FLOCK_ID on PRODUCTION_RECORD is a fabricated provisional key

### Production Pipeline Context

The current workbook workflow involves:
- External farm/grader CSV
- EFNS staff consolidation into a larger spreadsheet
- Calculations / classification
- Manual entry into EIMS by Sara

This prototype reads the 35 saved source columns from the `EIMS 3` worksheet.
Incoming source fields are preserved by the mock repository while the final
Dataverse-to-Snowflake schema remains unresolved.

---

## Synthetic Data

All data in this prototype is **completely synthetic**. It contains **zero**
real EFNS producer information. Names, registration numbers, barn identities,
and production values are generated from seeded random pools.

---

## License

Proprietary — EFNS Internal Use Only.
