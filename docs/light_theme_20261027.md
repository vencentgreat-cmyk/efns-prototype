# EFNS light interface — local release review

Status: prepared and locally rendered, not deployed by this task.

## Baseline and scope

Fresh company live snapshot: `.local/light_theme_deployment_20261027/live-rollback-20261027T205618Z`.
The read-only snapshot verified QDCTNKN / UW19058 / CB12755 /
AWS_CA_CENTRAL_1 / EFNS_DEV and a stable 75-file runtime listing before/after
download. All 75 hashes match the latest Original files trace release. This
therefore preserves that deployed trace fix as well as the date batching/R1
mapping/identity protections, 40053 supplement, navigation and report counting.

Only these deployment files change:

| File | Purpose |
|---|---|
| `app/ui.py` | Light sidebar branding, darker supporting copy, scoped high-specificity dark title on white cards |
| `.streamlit/config.toml` | Native light palette, explicit light sidebar, widget borders and pale table headers |
| `snowflake.yml` | Explicitly include **only** `.streamlit/config.toml` at its exact path |

The theme file already existed locally but was absent from the old deployment
descriptor and fresh live listing. Native widgets could consequently follow a
dark runtime theme while EFNS cards remained white. The title rule previously
used a low-specificity class selector. It now targets only EFNS title markup;
there is no global heading/text recoloring or repainting of native widgets.

The app uses Streamlit 1.52.2, unchanged. Theme sections drive inputs, popup
menus (including portals), table canvases, tabs, alerts, buttons, focus and
disabled states. Native primary action remains blue. CSS is limited to
EFNS-owned markup and the existing responsive rules. There are no page,
navigation, authorization, repository, export, business-rule, schema or data
changes. No framework or dependency upgrade is involved.

Official support references (consulted 27 October 2026):
[Snowflake configuration](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/secrets-and-configuration)
supports `[theme]` and `[theme.sidebar]` in warehouse runtimes;
[Streamlit theme colors](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-colors-and-borders)
documents native foreground/background/sidebar behavior. Every selected option
was also checked against the installed 1.52.2 configuration registry and an
actual local browser render, rather than relying solely on newer docs.

## Actual local validation

Isolated full app: `.local/light_theme_deployment_20261027/validation`.
It is a copy of the complete candidate plus **local-only** QA support outside
the deployment ZIP. The real root application and actual pages run using the
existing Mock repository and a temporary SQLite synthetic admin. No Snowflake
connection is made by the rendering harness; synthetic archive rows are in
memory only. No business forms were saved. A separate native-state gallery
checks errors, selections, disabled fields, buttons and unknown/zero quantities.

Actual browser checks, at a 1440×1000 desktop viewport:

- Dashboard: white title card with dark heading, light sidebar and brand block.
- Report Center → Customize Report: expanded Dataset menu, selected output
  tags, 24 synthetic Flock result rows, table and CSV/XLSX controls.
- Flocks: selectable table, disabled View/Delete, blue New action; new form,
  tabs, native Account dropdown. No Flock saved.
- Record Review & History: Flock history controls and Original files; the
  synthetic source includes one READY and one REJECTED row, both displayed.
- Quota Registrations, Quota Transactions, Salmonella Tests and Salmonella Test
  Report: titles, filters, table headers, rows, informational alerts, action bars
  and applicable export controls.
- Native state gallery: red error, blue information, yellow warning, green
  success, selected tags, disabled controls, current tab, normal and hovered
  primary action, white secondary action. Table retains distinct unknown, 0
  and −5 values; no quantity transformation is introduced by styling.

Read-only DOM computed styles confirmed title text `rgb(23,32,51)` on a white
card; sidebar `rgb(241,245,249)`; primary `rgb(63,86,217)` with white text.
The actual hovered and focused primary action changed to `rgb(34,54,170)`
with white text, not an inferred CSS state. Normal body/copy/link/primary and
hover text combinations meet the tested 4.5:1 contrast threshold. Disabled
controls keep Streamlit's disabled appearance and semantics; their text uses
native reduced opacity and is not claimed to meet active-control contrast.

Screenshots are actual browser captures, not mockups:

| Evidence | File under `.local/light_theme_deployment_20261027/screenshots/` |
|---|---|
| Desktop dashboard | `01_dashboard_desktop.jpg` |
| Expanded report menu | `02_report_dataset_menu.jpg` |
| Report table and export controls | `03_report_table_exports.jpg` |
| Flocks list | `04_flocks_list.jpg` |
| Flock form dropdown | `05_flock_form_menu.jpg` |
| History tab | `06_record_history.jpg` |
| Quota registrations | `07_quota_registrations.jpg` |
| Salmonella tests | `08_salmonella_tests.jpg` |
| Original file trace | `09_original_files.jpg` |
| Native states | `10_native_states.jpg` |
| Hover and focus | `11_primary_hover_focus.jpg` |
| Native table and alerts | `12_native_null_zero_negative_table.jpg` |
| Quota transactions | `13_quota_transactions.jpg` |
| Salmonella report | `14_salmonella_report.jpg` |

The initial `01_dashboard.jpg` records a narrow browser with its native sidebar
overlay open, not the desktop acceptance view. The desktop view is named
explicitly above. Screenshots and render metadata stay outside the app ZIP.

Candidate regression command:

```text
python -m pytest tests/test_light_theme.py tests/test_flock_report_record_count.py tests/test_source_history_trace.py tests/test_report_center.py tests/test_related_record_navigation.py -q
```

Result: **58 passed** before the additional hover-color contrast assertion.
Supplementary final candidate checks (including that observed hover color and
NULL/zero report semantics): **26 passed**, 9.33 seconds:

```text
python -m pytest tests/test_light_theme.py tests/test_report_nullable_sum.py tests/test_summary_null_semantics.py -q
```

The two commands overlap in theme tests; they are not 84 distinct test cases.
Both root and candidate Snowflake static readiness passed. Full unrelated
business tests were not rerun for this presentation-only change.
Root `git diff --check` and the candidate/rollback CRLF-aware whitespace check
passed. ZIP contents/hashes were checked against both frozen manifests, and AST
comparison confirmed `apply_theme` is the only changed function in `app/ui.py`.

## Independent candidate and rollback

Folder: `.local/light_theme_deployment_20261027/`.
Candidate has 76 runtime files plus CLI descriptor; rollback has the saved
75 runtime files plus the prior verified descriptor. The only added runtime
file is the theme configuration. All other live runtime files except `app/ui.py`
are byte-identical. Three older root date files were excluded rather than used
to overwrite deployed functionality. Previous local work is untouched.

Candidate and rollback ZIPs contain no real CSV/XLSX, source exports, credentials,
tests, QA login/harness/database, screenshots or deployment evidence.
The only TOML artifact is the reviewed theme-only configuration. Do not replace
it with a wildcard over `.streamlit/`; never include `secrets.toml`.

Deployment instructions are in
`.local/light_theme_deployment_20261027/DEPLOYMENT_INSTRUCTIONS.md`.
No SQL schema migration or new privilege is necessary. The existing post-deploy
SQL08 remains a separately authorized operational step, not executed here.

## Still requires company browser acceptance

After a separately authorized deployment and exact live hash verification,
open the company app and repeat the key page checks, including open menus,
selection/focus/hover, disabled controls and error visibility. Snowflake's outer
site chrome is separate from the app; this release themes the Streamlit app.
If that browser retained an explicit old Dark theme preference, check the app's
Settings → Theme and select its configured custom/light theme. This release
does not modify browser or operating-system preferences.

Local screenshots and automated tests are **not** company browser acceptance.
