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
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open http://localhost:8501 in a browser.

Sign in with one of the four seeded `prototype.*@nsegg.ca` accounts using the
temporary credentials supplied separately. A password change is required on
first login. The local user/audit database is created under `.local/` and is not
tracked by Git.

---

## What This Prototype Demonstrates

| Feature | Status |
|---------|--------|
| Logical data model (ACCOUNT, FACILITY, FLOCK, PRODUCTION) | PROVISIONAL |
| EIMS workbook ingestion (RAW → normalized union model) | Working (mock) |
| Production data search/filter | Working |
| Accounts/Facilities/Facility Details record workflows | Working |
| Flock, transaction, Quota and Salmonella record workflows | Working (provisional rules) |
| Customizable report builder with CSV & Excel export | Working |
| Snowflake SQL (RAW, CORE, REPORTING, SECURITY, APP) | Reviewed DEV foundation; not executed |
| Synthetic data generator (deterministic, seeded) | Working |
| Modular repository pattern (Mock ↔ Snowflake) | Shared executor, parameterized CRUD/import adapter; DEV integration pending |
| Multi-user edit protection | Account, Facility, Facility Detail, Flock, transactions, Quota and Salmonella |
| System diagnostics | User-triggered, credential-safe status page |
| Schema-agnostic source profiling | In-memory CSV/XLSX/XLSM profiling and profile-only exports |
| Prototype application security | Internal-domain login, roles, protected pages, user administration and audit log |

---

## Project Structure

```
efns-prototype/
├── app/
│   ├── Home.py                   # Application shell + grouped navigation
│   ├── auth.py                   # Streamlit session and page guards
│   ├── security.py               # Replaceable auth contract + local SQLite backend
│   ├── snowflake_security.py     # Snowflake viewer roles and audit persistence
│   ├── ui.py                     # Shared visual system
│   ├── pages/
│   │   ├── 1_Production_Import.py
│   │   ├── 2_Production_Data.py
│   │   ├── 3_Accounts_Facilities_Flocks.py
│   │   ├── 4_Reports.py
│   │   └── 14_Source_Data_Profiler.py
│   └── services/
│       ├── export.py             # Spreadsheet-safe exports
│       ├── authorized_repository.py # Permission/audit repository proxy
│       ├── profiling_export.py   # Profile-only CSV/Excel exports
│       └── report_builder.py     # Dynamic report assembly
│
├── data/
│   ├── constants.py              # EIMS import constants and mappings
│   ├── connection.py             # Lazy Snowpark/connector execution boundary
│   ├── importing.py              # Workbook read/normalize/validate helpers
│   ├── profiling.py              # Pure in-memory tabular profiler
│   ├── repositories/
│   │   ├── __init__.py           # Factory: get_repository()
│   │   ├── base.py               # Abstract BaseRepository
│   │   ├── mock.py               # In-memory MockRepository
│   │   └── snowflake.py          # Snowflake CRUD/import adapter
│   └── synthetic.py              # Synthetic data generator
│
├── sql/
│   ├── 00_dev_foundation.sql     # DEV roles, warehouse, schemas, cost monitor
│   ├── 01_setup.sql              # Idempotent database & schemas
│   ├── 02_core_tables.sql        # Operational entities (PROVISIONAL)
│   ├── 03_production_tables.sql  # Production & import tables
│   ├── 04_reporting_views.sql    # Reporting views
│   └── 05-08_*.sql               # Security tables, grants, bootstrap and app grants
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
│   ├── eims_metadata_meeting_checklist.md
│   ├── source_to_target_mapping_template.csv
│   └── DATAVERSE_TO_TARGET_MAPPING.csv
│
├── tests/
│   ├── test_phase1_2_regressions.py
│   ├── test_phase1_domain.py
│   ├── test_connection.py
│   ├── test_profiling.py
│   └── test_synthetic.py
│
├── requirements.txt
├── environment.yml              # Snowflake warehouse runtime dependencies
├── snowflake.yml                # Snowflake CLI deployment definition
├── streamlit_app.py             # Root deployment/local entry point
├── .env.example
└── README.md
```

---

## Architecture

### Repository Pattern

The UI talks to `BaseRepository`. Two implementations:

- **MockRepository** — in-memory pandas DataFrames. Used for local development.
- **SnowflakeRepository** — parameterized CRUD, filtered reads, protected updates,
  deletion checks and atomic imports through a shared SQL executor.

Set `REPOSITORY_MODE=snowflake` in `.env` to switch (requires credentials).

Snowflake runtime selection is lazy and ordered: Streamlit named connection,
active warehouse Snowpark session, then Python connector. See
`docs/CONNECTION_ARCHITECTURE.md` for authentication and deployment details.

The application floor and Snowflake warehouse pin are Streamlit `1.52.2` on the
warehouse runtime's default Python 3.11. `environment.yml` intentionally leaves
Python unpinned. Newer compatible Streamlit versions remain usable in local mode.

### Source Data Profiler

The Administration profiler reads CSV, XLSX and XLSM source files in memory,
profiles every worksheet, and suggests possible keys and relationship-shaped
columns. Suggestions are advisory and contain no EIMS mappings. Downloads contain
profile summaries and limited sample values rather than the complete source data.

### Historical EIMS migration

`scripts/generate_fake_eims_export.py` creates a deterministic, fully fictional
clean package plus controlled rejected-row cases. The separate Migration Import
workspace stages source files, preserves RAW JSON, validates the versioned
provisional contract, and commits Ready records to CORE in dependency order.
Generated samples are intentionally excluded from the Snowflake app artifact.

### Prototype authentication and authorization

Every page requires an active `@nsegg.ca` identity. Local mode uses the SQLite
password/session backend. Streamlit in Snowflake uses `st.user.email`, then reads
role and active status from `EFNS_DEV.SECURITY.APP_USER`; it never presents a
second password form. Role-aware navigation improves
the interface, while page guards and the authorized repository proxy enforce
access independently of hidden buttons. Important creates, updates, deletes,
imports, logins and user-management changes are written to the local audit store.
See `docs/AUTHENTICATION.md` for the permission matrix and prototype limitations.

### Configuration and deployment

- Local mock: keep `REPOSITORY_MODE=mock`; data lasts for the Streamlit session.
- Local Streamlit: prefer a named Streamlit connection or SSO/external browser.
- Warehouse runtime: `streamlit_app.py`, `snowflake.yml`, and `environment.yml`
  use the current `FROM`-based Snowflake CLI deployment path and active Snowpark
  session. Only runtime source files are uploaded.
- Container runtime: inject connector configuration with the platform secret
  manager. Do not copy `.env`, `secrets.toml`, tokens, or private keys into an image.

Use `.env.example` for local configuration. `snowflake.yml` is a credential-free
deployment definition; Snowflake CLI credentials belong in the user-level CLI
configuration. See `docs/SNOWFLAKE_DEPLOYMENT.md` for setup and rollback.

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

Historical exports follow a separate path:

```
Uploaded package → encrypted internal stage → migration RAW rows → validation
                 → Ready / Rejected → atomic dependency-ordered CORE commit
                 → reconciliation and reporting
```

### Schema

| Schema | Purpose |
|--------|---------|
| `EFNS_DEV.RAW` | Source-preserving import records |
| `EFNS_DEV.CORE` | Normalized operational/business entities |
| `EFNS_DEV.REPORTING` | Views and report-ready datasets |
| `EFNS_DEV.SECURITY` | Snowflake viewer application roles and active status |
| `EFNS_DEV.APP` | Audit events, deployment stage, and Streamlit object |

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
7. **Business rules** — current validation, quota and Salmonella rules remain provisional
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
