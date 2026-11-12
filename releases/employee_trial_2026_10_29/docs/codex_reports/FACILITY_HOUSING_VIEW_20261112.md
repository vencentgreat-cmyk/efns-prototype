# Parent Facility Housing System display — 2026-11-12

Branch: `codex-facility-housing-view-20261112`; separate worktree `.local/facility-housing-view-worktree`.
Base: latest fetched origin/main **3791ca501c2e8e7ba05adf817677bbd19c566adb** (PR #27), verified to contain Production PDF commits a7e667d and 91b555b. No other branch/worktree changed. No deployment, PR creation, Snowflake access or real-data additions.

## Investigation and change

CORE.FACILITY already has HOUSING_SYSTEM (`sql/10_EIMS_V3_DEV_Deployment.sql:102`, additive statement at line 398). Snowflake `get_facilities` delegates to the existing `_filtered('FACILITY', ...)` SELECT * with bound account/status conditions; mock `get_facilities` copies its stored frame. No new repository method, SQL, schema or data change is needed. An older mock frame without the column is safely displayed with a dash.

Only `app/pages/11_Facilities.py` changes at runtime. The list labels FACILITY_TYPE as **Facility Type**, immediately followed by **Housing System**. The Summary tab relabels **Type** to **Facility Type** and adds the same read-only Housing System row beneath it. Both use the existing `facility_detail_value` formatter from `app/services/facility_detail_display.py`, which remains unchanged. None/NA/NaT/NaN/empty/whitespace values display **—**. No values are inferred from Facility Details, production, or another field.

Screenshot-equivalent synthetic example:

| Facility Name | Account | Facility Type | Housing System | Status |
|---|---|---|---|---|
| Example barn | Example producer | Layer | Enriched | Active |

The existing activation/closure/created columns follow Status as before. In Summary the left column shows Facility Name, Account, Facility Type **Layer**, Housing System **Enriched**; the right column retains Status and dates. Missing housing shows **—** in both places. Housing is not added to the create/edit form.

Filters operate on the original stored data before display formatting; row order, row IDs and selection behavior are retained. Permission checks, save/delete paths, Facility Details page/service, all calculations and stored values are unchanged. There are no explicit CSV/XLSX export controls on the parent Facilities page. Report Center datasets and CSV/XLSX columns remain unchanged, verified by an export regression. Per user clarification, Streamlit’s built-in table download may include the newly visible Housing System column; no special native-download handling was added.

## Validation

Focused synthetic tests: **16 passed**. Coverage: both app entrypoints; Admin and Reporting Viewer read-only Summary; adjacent friendly list headers; nullable/missing housing columns; existing type filter, row order/identity and edit controls; empty-list message; existing Snowflake read through an injected offline query; unchanged Report Center facility export columns and unchanged repository frames.

Full release suite: **2,071 passed, 1 skipped, 0 failed/errors** (604.80s), using Python 3.12.14: `python -m pytest -q --basetemp ../../.local/housing-release-temp` from the release directory. Full root suite: **706 passed, 0 failed/errors** (158.57s), using the existing isolated Python 3.11 CI environment: `python -m pytest -q --basetemp .local/housing-root-temp` from root. The last full baseline check of the merged base code was 2,055 passed / 1 skipped at release and 706 passed at root; this task adds 16 passing cases.

## Shipped-file byte proof

Before editing, every file selected by snowflake.yml artifacts plus streamlit_app.py, environment.yml and .streamlit/config.toml was hashed using raw SHA-256. **116 files before and after; 115 existing shipped files are byte-identical.** Exactly one shipped path changed:

| Shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| `app/pages/11_Facilities.py` | `001e0bf62b2620daa71cb6451e7851d76a4b0d85a445fb27d643e5bc0fca4e7d` | `d85330484c916f374430098ff7cb14a3efe150be23b62486e2b7999353d38295` |

The other changed files are the new synthetic test file, this report and regenerated DELIVERY_RUNTIME_DIFF_20261030.json. Main’s manifest entries are preserved; every candidate hash is recalculated from the final file bytes with CRLF normalized to LF. There are **99 candidate hashes**. Historical captured-source manifests are untouched.

## Uncertainty / limits

No live data was inspected, so completeness or correctness of existing facility housing values is unverified. Parent Facility Type displays FACILITY.FACILITY_TYPE exactly as stored; Housing System displays FACILITY.HOUSING_SYSTEM. No attempt is made to reconcile legacy naming or derive housing from FACILITY_DETAIL.DETAIL_TYPE or PRODUCTION_RECORD.HOUSING_SYSTEM. Blank stored values remain unknown (dash). No other uncertainty affects this display-only change.
