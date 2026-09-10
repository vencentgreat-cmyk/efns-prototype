# EFNS Internal Data System — Prototype v0.1

**Egg Farmers of Nova Scotia (EFNS)**

A Streamlit-based prototype for the next-generation internal data system,
targeting Snowflake as the cloud data platform.

---

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and review configuration
cp .env.example .env

# 4. Run the Streamlit app (mock mode — no Snowflake needed)
streamlit run app/app.py
```

Open http://localhost:8501 in a browser.

---

## What This Prototype Demonstrates

| Feature | Status |
|---------|--------|
| Logical data model (ACCOUNT, FACILITY, FLOCK, PRODUCTION) | PROVISIONAL |
| CSV ingestion pipeline (RAW → CORE) | Working (mock) |
| Production data search/filter | Working |
| Accounts/Facilities/Flocks CRUD views | Working |
| Customizable report builder with CSV & Excel export | Working |
| Snowflake-ready SQL (schemas: RAW, CORE, REPORTING) | Ready to deploy |
| Synthetic data generator (deterministic, seeded) | Working |
| Modular repository pattern (Mock ↔ Snowflake) | Stub ready |

---

## Project Structure

```
efns-prototype/
├── app/
│   ├── app.py                    # Home page + navigation
│   ├── pages/
│   │   ├── 1_Production_Import.py
│   │   ├── 2_Production_Data.py
│   │   ├── 3_Accounts_Facilities_Flocks.py
│   │   └── 4_Reports.py
│   └── services/
│       └── report_builder.py     # Dynamic report assembly
│
├── data/
│   ├── repositories/
│   │   ├── __init__.py           # Factory: get_repository()
│   │   ├── base.py               # Abstract BaseRepository
│   │   ├── mock.py               # In-memory MockRepository
│   │   └── snowflake.py          # Snowflake stub (not yet active)
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
│   └── DATAVERSE_TO_TARGET_MAPPING.csv
│
├── tests/
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
CSV Upload → Python Ingestion → RAW (IMPORT_BATCH, IMPORT_RAW_ROW)
                                       ↓
                               Validation / Transformation
                                       ↓
                               CORE (PRODUCTION_RECORD, SIZE_BREAKDOWN)
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

The current CSV workflow involves:
- External farm/grader CSV
- EFNS staff consolidation into a larger spreadsheet
- Calculations / classification
- Manual entry into EIMS by Sara

This prototype models the CSV ingestion path, but the actual production CSV
format and column mapping will need to be refined based on real file samples.

---

## Synthetic Data

All data in this prototype is **completely synthetic**. It contains **zero**
real EFNS producer information. Names, registration numbers, barn identities,
and production values are generated from seeded random pools.

---

## License

Proprietary — EFNS Internal Use Only.