# Facility Details display — 2026-11-12

Branch: `codex-facility-details-display-20261112`; base `origin/main` at `d5ffbe19dbd1ee83308c58c409928cfdcef9185b`. Separate worktree: `.local/facility-details-display-worktree`.

## Investigation: legacy field coverage

“SQL” means the repository’s declared v3/additive schema, not an inspection of live Snowflake. `sql/10_EIMS_V3_DEV_Deployment.sql:113` defines the expanded table; `sql/12_real_eims_additive_migration.sql:122` adds its physical fields. The original `sql/02_core_tables.sql:129` has only the earlier basic fields.

V3 field mappings are in `config/eims_migration_mapping_v3.json:90`. Its disposal/count-source overlays inherit these Facility Detail mappings unchanged. V1/V2 and the unversioned v2 contract only cover the basic fields; they do not map the eleven later physical/legacy-ID fields. `data/migration.py:210` enumerates mapped fields and applies declared types; `:243` resolves their source columns. No mapping or migration code is changed.

Both repository interfaces return whole existing records: Mock copies/filters its stored frame (`data/repositories/mock.py:325,336`); Snowflake uses existing filtered/single-row reads (`data/repositories/snowflake.py:581–587`). Its `MODEL` at `:53` already includes all fields added to this display. Default mock seeds omit physical values; the display uses “—” rather than inventing them. Synthetic tests supply schema-valid values in memory.

| Legacy field | Exists in SQL schema? | Mapped by migration? | Returned by repository? | Displayed before → after |
| --- | --- | --- | --- | --- |
| Facility | Yes: `FACILITY_ID` | `efc_facilityid` | Yes, when stored (mock and Snowflake) | Yes → Yes |
| Facility Type | Yes: `DETAIL_TYPE` | `efc_facilitytype_displayname` | Yes, when stored (mock and Snowflake) | Detail Type → Facility Type |
| Date Installed | Yes: `DATE_INSTALLED` | `efc_dateinstalled` | Yes, when stored (mock and Snowflake) | No → Yes |
| Bird Colour | Yes: `BIRD_COLOUR` | `efc_birdcolour_displayname` | Yes, when stored (mock and Snowflake) | No → Yes |
| Width | Yes: `WIDTH` | `efc_width` | Yes, when stored (mock and Snowflake) | No → Yes |
| Length | Yes: `LENGTH` | `efc_length` | Yes, when stored (mock and Snowflake) | No → Yes |
| Height | Yes: `HEIGHT` | `efc_height` | Yes, when stored (mock and Snowflake) | No → Yes |
| Cage Brand | Yes: `CAGE_BRAND` | `efc_cagebrand_displayname` | Yes, when stored (mock and Snowflake) | No → Yes |
| Highest # Birds per Cage | Yes: `HIGHEST_BIRDS_PER_CAGE` | `efc_highestbirdspercage` | Yes, when stored (mock and Snowflake) | No → Yes |
| Number of Cages | Yes: `NUMBER_OF_CAGES` | `efc_numberofcages` | Yes, when stored (mock and Snowflake) | No → Yes |
| Birds Housed | Yes: `BIRDS_HOUSED` | `efc_birdshoused` | Yes, when stored (mock and Snowflake) | No → Yes |
| Comments | Yes: `COMMENTS` | `V1/V2: COMMENTS; v3: not mapped` | Yes, when stored (mock and Snowflake) | Yes → Yes |
| Name | Yes: `DETAIL_NAME` | `efc_facilityidname (lookup display name)` | Yes, when stored (mock and Snowflake) | Detail Name → Name |
| Nest Box Length | No | No | No normalized field | No → No |
| Nest Box Width | No | No | No normalized field | No → No |
| Square Inch per Bird | No | No | No normalized field | No → No |
| Square Inches (W*L) | Yes: `SQUARE_INCHES` | `efc_squareinches` | Yes, when stored (mock and Snowflake) | No → Yes; stored value only |
| Status | Yes: `STATUS` | `V3: statuscode_displayname; statecode is not mapped` | Yes, when stored (mock and Snowflake) | Yes → Yes |
| Status Reason | Yes: `STATUS (no separate column)` | `V3: statuscode_displayname → STATUS` | Yes, when stored (mock and Snowflake) | Already visible as Status; no duplicate field added |
| EIMS Facility Detail ID | Yes: `EIMS_FACILITY_DETAIL_ID` | `efc_eimsfacilitydetailid` | Yes, when stored (mock and Snowflake) | No → Yes |

### Important distinctions / missing data

- **Facility Type is verified:** `DETAIL_TYPE` maps to legacy `efc_facilitytype_displayname`. The UI label is therefore “Facility Type”, not a guessed substitute. Values remain exactly the stored choices; no dropdown, validation or edit-form choices were added.
- **Missing from normalized data, needs a re-import:** Nest Box Length, Nest Box Width and Square Inch per Bird. They have no Facility Detail schema column, repository field or migration mapping. Future schema/mapping review is needed before a re-import can expose them. No dimensions or per-bird values are calculated or fabricated now.
- **Comments migration gap:** the schema/repository field already exists and remains displayed, but the real v3 Facility Detail mapping omits legacy Comments. If legacy Comments are needed, this is missing from the v3 import and needs a mapping/re-import review. Existing stored/new-app Comments are preserved and shown.
- **Status versus Status Reason:** v3 maps `statuscode_displayname` into the existing `STATUS` column. Dataverse defines statuscode as Status Reason and statecode as Status; see [Microsoft’s state/status documentation](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/define-custom-state-model-transitions). A separate legacy statecode Status value is not imported. Existing “Status” labeling/filter behavior is retained, and no second field is filled with a duplicate/guessed state. Separate state/reason parity is missing from normalized data and needs mapping/re-import review after the trial.
- **Name source:** the existing `DETAIL_NAME` comes from the Facility lookup display name (`efc_facilityidname`), not a separately mapped legacy primary-name attribute. Relabeling it “Name” does not replace its value; parity with any distinct legacy primary Name is unconfirmed.
- Unmapped values might remain in archived source/RAW evidence; no live rows were inspected. “Missing” above refers to the CORE/repository representation available to this page, not proof that original source evidence has been lost.

## Display change

The list now has friendly headers: Name, Facility, Account, Facility Type, Date Installed, Bird Colour, Width, Length, Height, Cage Brand, Highest # Birds per Cage, Number of Cages, Birds Housed, Square Inches (W*L), EIMS Facility Detail ID, Status, Comments and Created On. The detail Summary exposes the same stored fields; existing timestamp captions remain.

Example with synthetic values: **Facility Type: Enriched; Date Installed: 2024-02-29; Width: 12.3456; Cage Brand: Synthetic cage brand; Number of Cages: 0; Birds Housed: 0; Square Inches (W*L): 999.9999; EIMS Facility Detail ID: 000SYN-DETAIL.**

Empty/NULL/whitespace values render “—”, including old mock rows without physical columns. Zero stays zero; Decimal precision and leading zeros in identifiers are preserved. Dates display as stored calendar dates (YYYY-MM-DD); Created On uses the existing timestamp formatter. Invalid dates are not replaced by guessed dates. The list is a read-only string presentation; numeric values are not rounded or recomputed. In particular, Square Inches displays its stored value and is not multiplied from Width and Length. Units are not inferred.

The list’s source filtering, row order/record IDs, selection controls, related navigation and VIEW_DATA page/repository permission checks stay unchanged. The create/edit/save block is unchanged, and no new physical-field editing controls are introduced. No repository, schema, SQL, migration, config, data seed or other page is changed.

## Parent Facility gap — explicitly deferred

Per the user’s scope clarification, **app/pages/11_Facilities.py is not edited**. Its Summary shows `FACILITY_TYPE` under “Type” (e.g. Layers), not the parent’s housing field `HOUSING_SYSTEM`. The latter is already returned and maps from `new_facilitytype_displayname` (`config/eims_migration_mapping_v3.json:80`). Its Related Facility Details table can also contain child `DETAIL_TYPE`, with generic raw headers.

A future view-only parent-page change could show the stored `HOUSING_SYSTEM` and/or add a friendly child Facility Type heading using existing reads. No new SQL would be needed. Choosing how to present differing parent/child values is left to that follow-up; no aggregation or guess is introduced here.

## Tests and guarantees

- Focused new-display tests: **24 passed** (14.33 s). Existing related-navigation and Facility relationship focused checks also passed.
- Before: full release **2,012 passed, 1 skipped, 0 failed, 0 errors** (569.71 s); full root **706 passed, 0 skipped, 0 failed, 0 errors** (169.50 s).
- After: full release **2,036 passed, 1 skipped, 0 failed, 0 errors** (558.46 s); full root **706 passed, 0 skipped, 0 failed, 0 errors** (153.30 s). The increase is exactly **24 new synthetic tests**, with no existing test changes. Synthetic tests cover stored fields/friendly labels, old mock shapes, NULL/empty values, zero/precision/leading-zero preservation, no area calculation, both entrypoints, empty results and Reporting Viewer access. Frame comparisons verify no record mutation.
- No real producer/flock data files were added; new fixtures are synthetic only. No Snowflake access, deployment or PR. No schema/data change.

## Changed shipped-file hashes

Raw SHA-256 was captured before edits for every file matched by release snowflake.yml artifacts plus the entrypoint, environment and theme config. Only these shipped files change:

| Shipped file | Before raw SHA-256 | After raw SHA-256 |
| --- | --- | --- |
| `app/pages/13_Facility_Details.py` | `d5bc46aa869ebaa2195a2c04036325b6c400c4652126b234759190daa6c63faf` | `b0e495528926edee89e75a75622153af52622f8c55245bb2d40d134834b66135` |
| `app/services/facility_detail_display.py` | — (new file) | `6e95de96d1b2589a3bad88b913be0917dc9434628da2d4fe8ea19d7e29ba96ed` |

**114 shipped files before; 115 after:** one modified Facility Details page, one new view service, zero removed files, and **113 other shipped files byte-identical**, including the parent Facility page. Unchanged-set digest (sorted release-relative path + NUL + raw SHA-256 + newline): `db80c6688892ae34f44424c212b8c7cd5b1a581f98e5e769cd643e9157a6fee5` before and after.

The new service is included by the existing app/services/*.py artifact pattern. The live runtime-diff manifest is regenerated from LF-normalized final files, preserving main’s entries and adding the new service, synthetic tests and this report: **94 candidate hashes**. Historical captured-source and patch manifests stay baseline evidence. No manifest conflict or hand-merge occurred.

### Before/after suites

| Suite | Before passed / skipped / failed / errors | After passed / skipped / failed / errors |
| --- | --- | --- |
| Full release | 2,012 / 1 / 0 / 0 | 2,036 / 1 / 0 / 0 |
| Full root | 706 / 0 / 0 / 0 | 706 / 0 / 0 / 0 |

Commands: `python -m pytest -q` from the release directory and root, using the existing release environment and root Python 3.11 CI environment respectively. Final documentation/manifest updates were followed by the integrity guard and an independent check of every candidate hash and the unchanged form/save block.
