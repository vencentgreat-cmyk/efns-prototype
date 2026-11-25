# UI polish A — 25 November 2026

## Base and scope

Branch: `codex-ui-polish-a-20261125`. Base: fetched `origin/main`, `5f18fba4d3e703d357a9fd094dd9d79966af493c` (PR #49). `git merge-base --is-ancestor f14243c origin/main` returned 0 before work started. This branch uses a separate worktree; other branches and worktrees were not edited.

Implementation HEAD verified by the full suites: `a0b4350dc2fa87734833aafec6294b4a6d36853e`. The final delivery reply supplies the final branch HEAD, including the report/manifest-only follow-up; that follow-up does not change shipped files.

Presentation only. No changes to business logic, SQL, data writes, authorization, calculations, validation rules, audit logging, stored values, export schemas or report output. No connection, authentication, lock or repository file changed. No new dependency, component, external font/asset, dialog, fragment, cache, DDL, live Snowflake access, merge, deployment or PR.

## Approved items completed

| IDs | Result |
|---|---|
| U11 | Shared header has no shadowed box; it ends in one accent rule. Production Import has one bordered review area, without extra borders inside previews. Quota Registration read/form surfaces, Report Library/saved-item wrappers and the dashboard recent-import wrapper no longer add a border to every section. Native tables, inputs, tabs and their selection behavior remain intact. |
| U12 | `section_intro` produces escaped semantic H2 headings, or H3 when explicitly requested for subsections. Report Library has an H2 above H3 report names. The duplicate quota-report title becomes “Results”. The embedded migration correction heading uses the same helper. One H1 and no skipped heading levels are tested on every default page through both entrypoints. |
| U27 | Shared secondary text is 14px, with less decorative header styling. Dashboard, Facility Details, Salmonella and Farm Location copy uses plain wording while retaining genuine provisional limitations. No business warning or recovery instruction was removed. |
| U05 | Blocking/warning lists remain capped at 30 each, with “Showing 30 of N” when capped. The unchanged complete issue download appears at the start of the validation area. |
| U09 | The existing producer/week replacement consequence is normal-size text immediately above the unchanged import button. No new confirmation or stage. |
| U13 | Production Records / Blocking Errors / Warnings lead the review. Column count and import/batch identifiers are in collapsed technical/reference expanders. Existing import-summary numbers and `summary_text` remain unchanged. |
| U15 | Lease terminology is retained. Lessor/Lessee have “leases out” / “leases in” help. Required markers reflect the existing lease validator, including both dates. The full inclusive-date, capacity and onward-leasing explanation remains available under Calculation details. |
| U16 | Quota Registration copy describes managing registrations and points to Quota Summary for the confirmed position, without adding a balance. Report calculation explanations are labelled/collapsed. Genuine provisional inclusion/legacy-age limitations and unavailable-evidence warnings remain visible. Stored transactions and derived incoming lease sections/counts remain separate. |
| U17 | Production and Flock Summary week fields explain “Production Week (YYYYWW)”. Mortality labels say “Mortality (% per month)”. Friday and week-in-progress wording from main is unchanged. |
| U19 | Flock and Salmonella form tabs use Summary / Details; Quota Transaction detail uses Summary / Related Records. Widget keys, values and the actual controls are unchanged. |
| U22 | Filtered Audit Log and all three reference tabs show “No records match these filters” for zero rows. The latest-5,000-event scope warning and genuinely empty-log message remain. |

Not implemented: any unapproved audit item, catalog chooser redesign, form-validation behavior change, permission-affordance change, persistent success-message flow, caching, dialogs/fragments or Tier C work. Existing distinct Account Information / Address / Account Roles groups remain because their meanings differ. The disabled historical quota-usage panel stays disabled and its renderer/calculations are untouched. Existing native low-emphasis rendering is not overridden with internal CSS; its contrast limitations are recorded below.

## Accent, typography and contrast

The existing logo was read, not copied or modified. Counting saturated non-background pixels in `tests/fixtures/legacy_forms/efns_logo.png` gave dominant RGB `(25, 88, 171)`, **#1958AB**. Chosen accent: **#225C80**. Compared with proposed #225C70, it moves slightly toward the logo's blue while retaining a restrained, dark blue-green appearance and strong white-text contrast.

Theme: warm canvas #F7F6F2, white inputs/surfaces, ink #202C32, EFNS secondary text #55636B, divider #CBD2D1. Native status text/background colors are explicitly configured, with unchanged textual success/warning/error/information messages. Code/reference text is explicitly neutral instead of inheriting a status color. New styles are confined to `app/ui.py` and `.streamlit/config.toml`; no selector targets native Streamlit internals. Removing the shared CSS/theme values reverts the new visual styling; retain the semantic-heading helper API if reverting styles alone.

The installed and pinned Streamlit version is **1.52.2**, unchanged. Its bundled CSS supplies Source Sans and Source Serif font faces. A hidden local Chrome preview, using synthetic controls and no repository or connection, confirmed H1 **28px Source Serif** with generic fallbacks, H2 **20px Source Sans**, body **16px**, and captions **14px**. Only page titles use serif; native headings remain sans-serif. The spacing rules use 8/16/24px multiples; no new assets or network font requests were added. The existing Snowflake-only sleep setting produces its usual local Streamlit warning; it was not changed.

Contrast uses relative luminance and alpha compositing, with computed browser styles for native controls/status messages and unit checks for the configured pairs. Ratios below are rounded for reporting; test comparisons use unrounded values.

| Foreground / background | Use / state | Ratio | Result |
|---|---|---:|---|
| #202C32 / #F7F6F2 | Ink on canvas, headings and control labels | 13.23 | Pass normal-text 4.5:1 |
| #202C32 / #FFFFFF | Ink on white input | 14.31 | Pass |
| #202C32 / #EEF2F1 | Ink on configured table-header surface | 12.68 | Pass for this configured pair; native canvas text has its own faded styling |
| #55636B / #F7F6F2 | EFNS-owned secondary text | 5.74 | Pass |
| #55636B / #FFFFFF | Secondary text on white | 6.21 | Pass |
| #FFFFFF / #225C80 | Native primary action | 7.22 | Pass |
| #225C80 / #F7F6F2 | Accent rule/link on canvas | 6.67 | Pass |
| #225C80 / #FFFFFF | Link / focused input border | 7.22 | Pass text and solid focus-border contrast |
| #FFFFFF / #123144 | Observed focused primary action | 13.56 | Pass |
| #202C32 / #FBFBF9 | Observed native secondary action surface | 13.81 | Pass |
| #202C32 / #EEEDE5 | Selected dropdown option, native alpha shade over the canvas-colored popover; flat screenshot background sampled | 12.18 | Pass |
| #2E6B4E / #EAF0ED | Success text/background | 5.46 | Pass |
| #7A5417 / #F2EEE8 | Warning text/background | 5.85 | Pass |
| #9D3640 / #F5EBEC | Error text/background | 5.92 | Pass |
| #375E7A / #EBEFF2 | Information text/background | 5.97 | Pass |
| #A1A5A5 / #F7F6F2 | Observed native disabled buttons/label, 40% ink | 2.30 | Below normal-text threshold; inactive-control exemption, not a 4.5:1 pass |
| #767D7F / #F7F6F2 | Observed native caption, alpha-composited | 3.88 | Existing native low-emphasis limitation; not a normal-text pass |
| #CBD2D1 / #FFFFFF | Divider/native default border | 1.54 | Decorative divider; do not treat as a strong focus indicator |

Disabled controls are explicitly exempt from the text criterion; ordinary captions are not. [W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) Native captions, faded grid labels, disabled opacity and the supplementary translucent focus halo are owned by Streamlit 1.52.2. They were inspected, not repainted via forbidden internal selectors. Critical import replacement guidance and the lease explanation now use body text; new capped-list notices use escaped EFNS-owned 14px secondary text (5.74:1). This is not a claim of full accessibility compliance for every native table cell or the hosted Snowsight shell. Native table focus/selection and 125% zoom remain in the manual checklist. There is no new logic tied to color.

## Before / after for every directly changed page

Shared styling and semantic section headings affect other pages too; their page files and data paths are unchanged.

| Page | Before | After |
|---|---|---|
| Dashboard (`app/Home.py`) | Boxed header/recent-import area, developer terminology and prototype branding | Quiet header, unboxed recent-import wrapper, plainer copy; same counts, navigation, roles and explicit database-load action |
| Production Import (`1`) | Many bordered panels, four equal metrics, capped lists without disclosure, replacement consequence in a caption | Choose workbook / Review validation / Import records; one bordered review, three leading metrics, explicit cap, full issue download, body-size replacement consequence, secondary references |
| Report Center (`4`) | H3 catalog names without a parent H2, repeated quota title, inconsistent mortality wording, dense calculation captions | H2/H3 outline, Results heading, unit/week help, labelled calculation details and visible limitations; same catalog order/opening, run buttons, results and export calls |
| Flocks (`5`) | Form tabs “Summary & Relationships” / “Flock Details” | “Summary” / “Details”; no field or value change |
| Quota Registrations (`7`) | Broad provisional allocation wording and bordered read/form surfaces | Task-first wording, explanation of where the confirmed position is found, unboxed surfaces; stored/derived transaction sections unchanged |
| Quota Transactions (`8`) | Detail tab “Relationships” | “Related Records”; lease fields additionally receive required markers/help from the shared entry helper; Allocation/counterparty behavior unchanged |
| Salmonella Tests (`9`) | “Summary & Relationship” / “Result & Invoice”; metadata jargon | Summary / Details and plain-English provisional field warning; same fields, read-only permit confirmation and payload |
| Facility Details (`13`) | Provisional wording embedded in title descriptions | Clear task descriptions with a separate visible provisional-field notice |
| Audit Log (`16`) | Zero filtered rows showed only an empty table | Explicit no-match message; original table and 5,000-event scope retained |
| Farm Locations (`18`) | “one confirmed relationship: its parent Account” | “linked to its parent Account”; same relationship/navigation |
| EIMS Reference Data (`20`) | Empty contact/allocation/calendar tables without explanation | Separate no-match message in each tab, using existing returned row counts |
| Migration Import (`17`, helper only) | Embedded correction title used a native H3 | Shared semantic H2; no edit to migration page logic or correction operations |

Shared service changes: `app/ui.py` (styling/headings); `app/services/production_import_review.py` (batch reference secondary; summary function unchanged); `app/services/quota_lease_entry.py` (labels/help/explanation only); `app/services/historical_correction_workspace.py` (heading only).

## Files and integrity

Changed shipped files: the 16 paths in the hash table below. All other **119 of 135** expanded `snowflake.yml` artifacts are unchanged. A separate raw-byte comparison using `git cat-file --filters` to reconstruct base checkout bytes also confirmed exactly 16 changed files and 119 byte-identical files, with no extra newline-only changes. No artifact pattern, dependency, asset or runtime module was added. New files contain synthetic tests and this report only.

Additional non-shipped changes: `tests/test_light_theme.py`, `tests/test_ui_and_export.py`, new `tests/test_ui_polish_a.py`, this report and regenerated `DELIVERY_RUNTIME_DIFF_20261030.json`. Existing palette assertions were updated to the approved values; contrast and no-broad-selector checks remain and the latter now also rejects `data-testid` selectors. Existing numeric fixture expectations were not edited.

The runtime diff is regenerated from the fetched main version, preserving every main entry, refreshing every listed candidate hash from final LF-normalized bytes and expanding the actual artifact globs. The immutable `RELEASE_SOURCE_MANIFEST.json` is untouched. Final count: **191 candidate-hash entries**, **135 shipped artifacts**. The exhaustive baseline-or-runtime-diff coverage guard passes for every shipped file.

Shipped-file hashes against base main (SHA-256, LF-normalized text, the same normalization as the runtime manifest):

| Shipped path | Base SHA-256 | Candidate SHA-256 |
|---|---|---|
| `.streamlit/config.toml` | `1c03edd1669cbb70594b6115f2a16734234297cde61e2c57e060f1223b5987e6` | `f2bb19709adeeb05360011fa85da4d63c413d194eed7b6431f421af1fcf8bd4a` |
| `app/Home.py` | `b32b99b494c5d83ae48dee173d87beb5f07782784930e5edbf4d9b7243da6ddf` | `06c7469af7fd5982a62d80c25839a745744050d89ce63fea855bf33d22bd167d` |
| `app/pages/13_Facility_Details.py` | `01027b55961a97951d5dcb6221fe8f88ee3acd92070e3c4622a865d013ecdfe2` | `ca5bd9564fef332c67d787088ed83f7f76653a9971ee1d5e14600c785635e746` |
| `app/pages/16_Audit_Log.py` | `ae974abdca91bd2bee5fd61fe938afe0d4abbae9de40e67f918c192a96630437` | `36ff39ef90afa5cf5640d3d24114c0ef5465a4306776804de8ac299ce869e180` |
| `app/pages/18_Farm_Locations.py` | `808a14a129a94805e2d3567d1f8cc957e12a0adb73f402f9539f1f8fbc534164` | `8e821f5c2df620a198efde101c833666a53d9b6921848a7b033274eb517dee67` |
| `app/pages/1_Production_Import.py` | `d87fa42c4d0198f0a9a9a7a38930be08e0993cb288b21c30755ea4a6d72f096d` | `f30d8a2e3a633c86d8cc4ef4c55005bb57b4f912606a46a2ab115e39c9d1542f` |
| `app/pages/20_EIMS_Reference_Data.py` | `38008ff1c58acd3a338001569942a3dd5357d6a5f5b7298871c2cc59e43a7147` | `cddfb174684b9c2708474b069ccf591fd29752f79bf87285d3f880def09b2658` |
| `app/pages/4_Reports.py` | `76005b17aaf6d79793a733be6957e73d03ed5103977d37f0a92c0cd8a2352fd5` | `3f27f5d0715a101403238f6c95ad069a4856483c9be0a085ac3d00d2c1fe2273` |
| `app/pages/5_Flocks.py` | `6d023457aaf72617271989c82dae0f8b653456fad0b16d85709d2b36d195de2a` | `a26e5f8e8e264436ea7c8617e670c8f20cdd944b8a2aa630e5e4653c2b027119` |
| `app/pages/7_Quota_Registrations.py` | `7956534faf4674445a36016c07867805f54d34d8d25adb1686c542f961a73dbd` | `51c274b8ce3b8240fc2f8d83eef4a625a71a4f54a20b2d2cfb20d633301af513` |
| `app/pages/8_Quota_Transactions.py` | `647649c21c64c71a4f030e3798140be8a0d17e2ebae2cb0e06c1a0b6ecbc9e6f` | `5016fdee473997ad3efd68b146524e5a1e2eeba80fa2ea7ea7228491d6951fd6` |
| `app/pages/9_Salmonella_Tests.py` | `d1ba4bddf360fc3a2e476c08317584cdb6fdf357c0efe3ff2d475a69ad231b9f` | `84ea3890237c6887057d65dce5aaf013d526b592aa44c5c25fb4fe12ab87072d` |
| `app/services/historical_correction_workspace.py` | `c1f218fdadc524b9b7fb2f7929b38df4317ab2612f877e9d899b666bce71deff` | `32426a5aad20b5cde3e55f74f0ade5c5032a76696c5328fbe5e30d05de5cde61` |
| `app/services/production_import_review.py` | `5d30566d1beccdc8b8b83bfcc94e3cd6ccc5b7eb5316206e18d923e804c0f9c2` | `e3236143d78827c3fe04780a0e8bc985746681d6cd3978494c22af7997fad78f` |
| `app/services/quota_lease_entry.py` | `ecda96f9e7be4e36549224e4d7aeca0b81e3f4db28ebb0682188a4a2288875aa` | `8e87fecff94d05af0a861c339905e95022668d2b736d7bc8d10e9bae8b1f5f4e` |
| `app/ui.py` | `761a3b9a151bf9016c7af9345516e160ddf2e9cab0fa76c6833961a438b611d3` | `ef471e65bd3ea0f3ab6b9d98c23786991b2c115fad7adac5c788b301ca34e522` |

Static AST comparison also found identical explicit widget-key expressions and identical repository/persistence/calculation call arguments in each changed app file. This supplements the tests; it is not a substitute for role, workflow and numeric regressions.

## Verification

- Final preflight: **48 passed**, including presentation, theme, existing UI/export and manifest guards. Covered both entrypoints, every default page outline, escaped headings/supporting text, no duplicate H1, synthetic ready/error/warning/empty/committed import states, unchanged preview values/staging rows/button disable conditions, complete issue download, secondary references, filtered Audit Log and all reference empty states. Separate Flock/UI focused regressions also passed (64 tests). No existing numeric fixture expectation was edited.
- Full release suite: **2,562 passed, 1 skipped, 0 failed, 0 errors**. Summary: `2562 passed, 1 skipped, 150 warnings in 813.41s (0:13:33)`. The existing skip remains; no test was removed or newly skipped.
- Full root suite: **706 passed, 0 skipped, 0 failed, 0 errors** (also 706 passed before the presentation edits).
- Commands: Python 3.12 in the existing isolated review environment, `python -m pytest -q` from the release and root directories, with `OPENPYXL_LXML=False` for the existing standard XML-writer setup. Final full-suite temporary roots were `.local/ui-complete-a0b4350` (release) and `.local/ui-root-a0b4350` (root); diagnostic runs use different temporary roots to prevent SQLite-file collisions. No requirements or version changed.
- Local browser preview: synthetic controls only, Streamlit 1.52.2; no live app/data. Computed styles and screenshot inspected locally. Scratch preview/browser files are ignored under `.local/` and are not committed.
- Final manifest guards: **8 passed** after the report and final hashes were regenerated. The 190-entry implementation manifest gained this report entry; no runtime bytes changed in the report-only follow-up.

## Manual click-through checklist (not a deployment instruction)

- [ ] Production Import: select a saved synthetic workbook; macro warning remains near upload; see the three section headings and unchanged source/import previews. Errors disable Import; warnings do not. More than 30 errors/warnings show the cap and a complete issue download. The replacement consequence is directly above the button. Refresh matching still uses the existing action. A successful mock import shows the original counts, with references secondary. Never retry an uncertain save as a new request.
- [ ] Quota Registrations: filter, select, open Summary/Related Records and edit/cancel. Registration values, dates and correction reasons persist. Stored Quota Transactions count remains distinct from “Leased in (from lease records)”; its derived rows remain read-only. Inspect unavailable/provisional notes without adding a balance here.
- [ ] Quota Transactions: Allocation default/options remain as merged from review fixes. Changing registration updates the read-only owner. Lease entry shows lessor/lessee help and required dates; submit/cancel still uses the original keys and permission rules. Open the current/original lease and existing end/return/void controls; capacity guards, past-date confirmation and audit behavior are untouched.
- [ ] Reports: open Production, Quota, Flock Summary, Flock Age/Current and Disposals; verify week-format help, mortality units, visible provisional/unknown warnings and labelled explanations. Friday/week-in-progress wording, report numbers, columns, applied parameters, totals and CSV/XLSX/PDF exports remain the same. No automatic run or new calculation.
- [ ] Dashboard: one quiet title, correct metrics, same role-gated links; explicit Snowflake-load action remains explicit. Check the sidebar and logout controls.
- [ ] Across pages: keyboard focus, table selection, disabled actions, 125% zoom and narrow Snowsight content width. Verify the hosted font/config rendering before any release decision. Native caption/faded-table contrast remains a documented limitation.

## Deployment notes

No DDL, schema migration, data backfill or new package is expected. Nothing was deployed or merged. The existing bundle already includes the changed UI/config/service files. Any later deployment needs the normal owner-controlled process and the hosted manual checks above; the sleep setting, runtime version, authentication and permission model remain unchanged.
