# Blank/null list display — 2026-11-16

Branch: `codex-blank-null-display-20261116`. Base: latest fetched `origin/main`, `9c78d30` (includes Facilities form PR #34).

The main Flocks and Accounts list tables now pass `placeholder="—"` to `st.dataframe`. The pinned and installed Streamlit version is 1.52.2; its existing API/protobuf supports a null placeholder. No library/config change or formatting helper is needed.

Missing cells in Comments, Disposal Plant, other text, numeric or date columns now display an em dash rather than Streamlit's default “None”. Empty strings stay empty; ordinary text, zero and False remain intact. Literal staff-entered text is not treated as a null marker. Related tables, forms and Report Center are unchanged.

The original DataFrames, dtypes and raw values are passed through unchanged. There is no fillna, string conversion, replacement, sorting/filtering change or storage mutation. The existing table/selection keys, row-ID mapping and on_select behavior remain. CSV/XLSX helpers and Report Center outputs are unchanged, including the null values underlying the built-in table download.

The installed Streamlit 1.52.2 frontend was also inspected: CSV export reads each column's getCellValue, while the null placeholder is passed separately to the grid's drawing renderer. It does not become a CSV value.

## Validation

Full release suite (Python 3.12): **2,196 passed, 1 skipped, 0 failed**, 754.81 seconds. Full root suite (Python 3.11): **706 passed, 0 skipped, 0 failed**, 227.23 seconds. Focused null/legacy-label/related-navigation suite: **36 passed**. Synthetic AppTests cover both entrypoints and both main lists, with None/NaN/pd.NA in text cells, missing dates, empty strings, ordinary text, zero and False. Each test reruns the same page while removing only the placeholder argument to reproduce its previous rendering call, then compares identical Arrow data bytes, table values, row IDs, CSV bytes, XLSX cell values and unmodified repository frames. Existing legacy-label, selection/filter/edit and related-navigation tests remain in the focused/full suites.

Full suites are run as `python -m pytest -q` from release/root, with separate worktree-local `--basetemp` paths. All data used in the new tests is synthetic; no Snowflake calls or live-data inspection.

## Shipped-file byte proof

SHA-256 captured before edits for every expanded snowflake.yml artifact plus streamlit_app.py, environment.yml and .streamlit/config.toml: **117 files before/after**. Only the following two shipped pages change; the other **115 are byte-identical**.

| Shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| app/pages/5_Flocks.py | 3e3a960db93ecfa6ddca61f349e1871fa3cd79affe434c2ba4b0e34df33bb1f6 | 38afca802dd1e2b28dda0e257a4a6756ed062aca5e01a089686427f55b8e0f08 |
| app/pages/3_Accounts_Facilities_Flocks.py | e17ff0477d9338a27f8873e7bfaa05e559818e6ad674f07ff1284dc840b65e7e | ae301bbfc7d3325007d092f0b981bdfcc23cb88175174473ef24d8da1f134ea7 |

Only these pages, `tests/test_blank_null_display.py`, this report and the live runtime-diff manifest change. Main's manifest entries are retained and **114 candidate hashes** regenerated from final LF-normalized bytes, without hand-merging. No schema, data, repository, calculation, permission, audit or export changes. No real-data files, deployment, PR or Snowflake calls.
