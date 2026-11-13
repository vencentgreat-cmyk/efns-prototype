# Facilities legacy wording and layout — 2026-11-13

Branch: `codex-facilities-legacy-labels-20261113`. Base: fetched `origin/main` at `283f49526f6bddaf2ae511784509a1749838213a` (includes Production PDF polish PR #31).

## What staff see

The default Facilities list is now **Registration Number | Account | Facility Name | Farm Location | Facility Type | Facility Layout | Status | Created On**. Account registration and Farm Location names come from existing read interfaces; source row order, filtering and row-ID selection are unchanged. Activation Date and Closure Date are no longer default columns; both remain in Summary. Created On retains the existing timestamp column formatting.

Summary displays Registration Number, Account, Facility Name, Facility Type, Facility Layout, Farm Location, Status, Construction Date, Renovation Date, Manure Disposal, Facility Quota, Comments, Activation Date, Closure Date and Created On. Empty values use the existing `facility_detail_value` dash formatter. These additions are read-only; the create/edit controls and save payload are unchanged.

| Location | Before visible label | After visible label |
|---|---|---|
| List and Summary | Housing System | Facility Layout |
| List filter | Facility type | Facility Type |
| List | STATUS | Status |
| List | ACTIVATION_DATE | Removed from default list; existing Activation Date remains in Summary |
| List | CLOSURE_DATE | Removed from default list; existing Closure Date remains in Summary |

Facility Name, Account, Facility Type, Status in Summary, Created On and all form labels were already friendly and remain unchanged. Registration Number and Farm Location are new list/Summary labels; Construction Date, Renovation Date, Manure Disposal, Facility Quota and Comments are new Summary rows rather than renamed fields. There was no Housing System input on this form to rename.

## Available and missing legacy fields

Evidence: `sql/10_EIMS_V3_DEV_Deployment.sql:97` defines the current Facility model; `config/eims_migration_mapping_v3.json:74` maps the legacy Facility export. `data/repositories/snowflake.py:52` lists maintained Facility fields; `get_facilities` returns the existing full Facility row. Older mapping versions contain fewer fields; no migration/mapping changes are made.

| Legacy field | Existing source / mapping | Display after change |
|---|---|---|
| Registration Number, Account | Existing `get_accounts()`; ACCOUNT.REGISTRATION_NUMBER / ORGANIZATION_NAME | List and Summary |
| Facility Name | FACILITY_NAME ← new_name | List and Summary |
| Farm Location / Other Address | FARM_LOCATION_ID ← new_farmlocationidid; existing `get_farm_locations()` supplies LOCATION_NAME | Farm Location in list and Summary |
| Facility Type | FACILITY_TYPE ← efc_facilitytype_displayname | List, Summary and existing form |
| Facility Layout | HOUSING_SYSTEM ← new_facilitytype_displayname | List and Summary; stored field/values unchanged |
| Construction Date | CONSTRUCTION_DATE ← new_constructionday | Summary and existing form |
| Renovation Date | RENOVATION_DATE ← new_renovationdate | Summary |
| Manure Disposal | MANURE_DISPOSAL ← new_manuredisposal_displayname | Summary |
| Facility Quota | FACILITY_QUOTA ← efc_facilityquota | Summary; stored value only, no calculation |
| Comments | COMMENTS ← efc_comments | Summary |
| Status | Existing STATUS ← statuscode_displayname | Friendly Status label; existing filters/options unchanged |
| Created On | Existing CREATED_AT | List, Summary and existing timestamp caption |
| Facility Description | **Missing from maintained CORE.FACILITY model and v3 field map** | Existing permission-gated “Original migration source description” expander remains. It reads archived efc_facilitydescription evidence, explicitly not maintained description/Comments. No copying or relabeling as current data. Needs schema/mapping/re-import review for maintained parity. |
| Separate Status Reason | **No separate column**; statuscode_displayname is already mapped to STATUS | No duplicate or invented value. Separate Status/Status Reason parity needs mapping/re-import review. |

All other legacy fields listed in the request exist in the current Facility model. Populated values in a deployed database have not been checked: there were no Snowflake calls. Missing values are displayed as dashes, not inferred.

## Form differences — reported only

| Field | Legacy choices / requirement | Current create/edit form (unchanged) |
|---|---|---|
| Facility Type | Breeder, Hatchery, Layers, Pullets | Pullet, Layer, Other. Existing historical values are preserved on edit; filter includes stored historical values. No singular/plural conversion or new options. |
| Facility Layout | Organic, Conventional, Free Range, Enriched, Free Run | No dropdown/input on this form. Stored HOUSING_SYSTEM is now visible read-only as Facility Layout. |
| Manure Disposal | Belt, Shallow Pit, Deep Pit, Belts and Gutter | No dropdown/input on this form; stored value shown in Summary. |
| Farm Location / Other Address | Required legacy lookup | No input on this form; existing stored link is shown read-only. No new required validation. |
| Renovation Date, Facility Quota, Comments, Facility Description | Legacy form fields | No maintained input on this form; available stored fields are shown in Summary only. |
| Status | Legacy lists Status and Status Reason separately | Existing Active, Inactive, Closed choices remain unchanged. |

Account and Facility Name remain required; Construction Date remains editable. Existing Activation Date, Closure Date and Inactive Date inputs are retained. No option values, validation, permissions, save/revision behavior, schema, calculation or repository implementation changes.

## Reads, exports and validation

No SQL is added or edited. The page reuses `get_accounts`, `get_facilities` and one `get_farm_locations()` read for list/detail views, rather than a per-facility lookup. Existing authorization wrappers apply. Create/edit does not load the new location lookup. The source-description permission check remains untouched.

Report Center CSV/XLSX exports and builders are byte-identical. The Facilities page has no explicit CSV/XLSX export buttons; as previously accepted, Streamlit's built-in table download follows the visible list columns. Tests retain the existing Report Center export-column assertions.

Full release suite (Python 3.12): **2,144 passed, 1 skipped, 0 failed**, 657.66 seconds. Full root suite (Python 3.11): **706 passed, 0 skipped, 0 failed**, 180.30 seconds. Focused Facilities/legacy/filter regressions: **45 passed**. Commands: `python -m pytest -q` from each directory, using separate worktree-local `--basetemp` paths. Synthetic AppTest coverage exercises both entrypoints (`streamlit_app.py`, `app/Home.py`), exact labels/order, linked registration/location, available/empty Summary fields, existing filtering, simulated row selection followed by actual View/Edit/Save controls, form options and preservation of undisplayed stored fields. Existing offline Snowflake-read coverage remains; no database connection is used.

## Shipped-file byte proof

SHA-256 was captured before edits for every expanded `snowflake.yml` artifact plus `streamlit_app.py`, `environment.yml` and `.streamlit/config.toml`: **116 files**. Only one shipped file changes; the other **115 are byte-identical** to the base.

| Changed shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| `app/pages/11_Facilities.py` | `d85330484c916f374430098ff7cb14a3efe150be23b62486e2b7999353d38295` | `06dcbd08cf5f829e64b5ae7654a942bedeb49d607bbea7b733145989e6f9a423` |

Only that page, synthetic tests, this report and the live runtime-diff manifest change. All existing manifest entries are retained and **106 candidate hashes** regenerated from final LF-normalized bytes. No real-data files, deployment, PR or Snowflake calls.
