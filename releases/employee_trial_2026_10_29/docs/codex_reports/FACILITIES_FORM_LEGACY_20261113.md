# Facilities legacy create/edit form — 2026-11-13

Branch: `codex-facilities-form-legacy-20261113`. Base: latest fetched `origin/main`, `36752ad`, including Facilities labels PR #32 and Flocks/Accounts labels PR #33. Only `app/pages/11_Facilities.py` changes at runtime; existing helpers and persistence, authorization, audit and revision implementations are unchanged.

## Before / after

| Field | Before create/edit form | After create/edit form |
|---|---|---|
| Account | Required existing Account selector | Unchanged, required |
| Facility Name | Required text | Unchanged, required |
| Farm Location | Not editable; visible in Summary | Optional existing Farm Location lookup, with Not selected / clear choice; no new validation or Account filter |
| Facility Type | Pullet, Layer, Other (plus stored historical values on edit) | Breeder, Hatchery, Layers, Pullets, plus a blank choice. All other stored values, including Pullet / Layer / Other, remain selectable and selected when editing; no silent conversion. |
| Facility Layout | Not editable; stored HOUSING_SYSTEM visible in Summary | Optional Organic, Conventional, Free Range, Enriched, Free Run; writes HOUSING_SYSTEM. Other stored values remain selectable on edit. |
| Manure Disposal | Not editable; stored value visible in Summary | Optional Belt, Shallow Pit, Deep Pit, Belts and Gutter; writes MANURE_DISPOSAL. Other stored values remain selectable on edit. |
| Construction Date | Existing optional date | Unchanged |
| Renovation Date | Not editable; stored value visible in Summary | Optional date; writes RENOVATION_DATE |
| Facility Quota | Not editable; stored value visible in Summary | Optional text input parsed through the existing numeric-bind helper as Decimal; writes FACILITY_QUOTA, no formula or float conversion |
| Comments | Not editable; stored value visible in Summary | Editable text area; writes COMMENTS without stripping entered text |
| Status | Existing Active, Inactive, Closed and historical preservation | Unchanged |
| Activation Date, Closure Date, Inactive Date | Existing date inputs | Unchanged |
| Reason for correction | Existing edit-only input | Unchanged; same save/revision requirements |
| Facility Description | No maintained field/input | Not added. Historical source-description evidence remains in the existing read-only, permission-gated detail expander. |
| Status Reason | No separate maintained field/input | Not added. Existing STATUS and its behavior remain unchanged. |

Null choices display a dash for Type/Layout/Manure; no optional field becomes required. Legacy entry options apply only to the form: the existing Facility Type list-filter choices and historical-filter behavior remain unchanged.

## Data sources, preservation and save contract

The existing maintained fields are confirmed in `sql/10_EIMS_V3_DEV_Deployment.sql:97`, `data/repositories/snowflake.py:52` (MODEL), and the V3 Facility migration map. No schema, mapping, SQL or repository changes.

Farm Location uses existing `get_farm_locations()` for both mock and Snowflake interfaces. Labels include the linked Account name; the existing `unique_identity_options` helper disambiguates duplicate labels. No new lookup query is defined, and no per-row lookup is used. An unresolved stored Farm Location ID appears as “ID (not found)” with a preservation note; it stays unchanged unless the user explicitly selects a different value or clears it. No required/ownership/active-only validation is added to this selector.

All six added maintained fields are included in the existing `capture_form` snapshot. The existing `preserve_form` restores original values for unchanged widgets, including NULLs and unusual historical values. Unchanged Facility Quota is not reparsed. The existing `save_form` still computes allowed changed attributes, requests the same optimistic-version check, and calls the same `create_record_once` / `revise_record` methods. Fields not shown, such as DESTRUCTION_DATE, are not included in a changed edit payload and remain intact. Existing fields' payload construction is unchanged.

Facility Quota uses `normalize_numeric_bind(..., integer=False)` exactly as a typed numeric parser: no quota calculation, rounding, positivity rule or new business validation. Blank input is NULL. Large/fractional and negative Decimal values round-trip in synthetic tests; no float conversion is introduced. The maintained database column remains NUMBER(18,4); its existing storage limits are unchanged, not expanded by this form. No unsupported-precision storage promise is made.

CREATE remains a CREATE revision with before=NULL and the saved fields in AFTER_DATA. An edit remains ATTRIBUTE_CORRECTION with the same authenticated recorder, reason, before/after images and one UPDATE audit event. Field permissions and server authorization wrappers are unchanged; Reporting Viewer still cannot save or bypass authorization. A no-op edit still creates no revision/audit and does not require a correction reason.

## Fixture inventory and uncertainty

The shipped default `MockRepository(seed=42)` has **18 Facility rows and 3 distinct non-null Facility Type values: Layer, Other, Pullet**. The synthetic generator's configured type pool is the same three values. New tests explicitly construct the new plural values and additional historical values; these are synthetic test cases, not observations from DEV. No live stored-value count is claimed because there were no Snowflake calls.

The new entry options use the user-specified legacy spellings and plurals exactly. Facility Description and separate Status Reason remain missing from the maintained model; adding them would require a separate schema/mapping decision. Their omission here is deliberate. This task does not alter Facility list/Summary display, Report Center exports, calculations, existing row selection/filter/sort behavior or any existing stored records outside isolated mock tests.

## Validation

Full release suite (Python 3.12): **2,192 passed, 1 skipped, 0 failed**, 1548.14 seconds. Full root suite (Python 3.11): **706 passed, 0 skipped, 0 failed**, 191.81 seconds. Initial focused Facilities form/display tests: **44 passed**; additional clear/no-op cases: **4 passed**. Tests exercise both entrypoints (`streamlit_app.py`, `app/Home.py`), create/edit round trips for all added fields, exact Decimal quantities and comment whitespace, historical types/layout/manure values, stale location IDs, unchanged/unshown fields, nullable clears/no-op saves, required name/optional field behavior, server permission rejection, and complete CREATE/UPDATE revision/audit contents. Existing display tests retain their checks, with only superseded form-option assertions updated.

Test commands are `python -m pytest -q` from release/root with isolated worktree-local `--basetemp` paths. No test connects to Snowflake. Audit and revision assertions use the existing in-memory repository's history/audit implementation rather than bypassing the writer.

## Shipped-file byte proof

SHA-256 captured before edits for all expanded `snowflake.yml` artifacts plus `streamlit_app.py`, `environment.yml` and `.streamlit/config.toml`: **117 files before and after**. Only one shipped file differs; the other **116 are byte-identical**.

| Changed shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| app/pages/11_Facilities.py | 06dcbd08cf5f829e64b5ae7654a942bedeb49d607bbea7b733145989e6f9a423 | 74135068998c40302fdd3896a11ff3c728855613c0a2a2f3f67264bb2758a449 |

Only that page, synthetic tests, this report and the live runtime-diff manifest change. All existing manifest entries are preserved and **112 candidate hashes** regenerated from final LF-normalized bytes. No real-data files added, no protected write/auth/lock/connection service changes, no deployment or PR, and no Snowflake calls.
