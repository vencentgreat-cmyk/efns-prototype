# Project Status

## Implemented

- Python 3.12 project environment and 26-test regression suite.
- Grouped Streamlit navigation with a consistent Dynamics-inspired layout.
- EIMS 3 workbook reader for the 35 source columns in A:AI.
- Pure normalization and technical validation helpers.
- Source and relationship fields: `SOURCE_TYPE`, `MATCH_STATUS`, source row/week,
  producer/grader account IDs, facility ID, flock ID, import ID, and audit timestamps.
- Source-preserving RAW rows in `MockRepository`.
- Registration-number candidate lookup that returns zero, one, or many accounts.
- Transitional production-column union so imports do not silently lose fields.
- Correct row-level year/week filtering and connected account/flock reporting.
- Spreadsheet-safe CSV and Excel exports.

## Current boundary

The application is a mock-mode prototype. The Snowflake repository remains a
partial adapter, and the SQL model has deliberately not been changed. The
authoritative provisional Dataverse mapping is
`docs/DATAVERSE_TO_TARGET_MAPPING.csv`.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/Home.py
```
