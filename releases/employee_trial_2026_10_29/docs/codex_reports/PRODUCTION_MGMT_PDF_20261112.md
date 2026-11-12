# Production Management PDF — 2026-11-12

Original base: origin/main `d5ffbe19dbd1ee83308c58c409928cfdcef9185b`; isolated branch `codex-production-mgmt-pdf-20261112`, worktree `.local/production-mgmt-pdf-worktree`. Offline only; no deployment, PR, Snowflake calls or real-data additions.

## Audit and scope

No Production report entirely lacks PDF wiring on this base: the catalog appends PDF to Available CSV reports, and the Reports page already offers three export controls for all five. However, Summary and Details could refuse PDF because all 29 columns, including repeated J2 and long account/grader names, cannot fit Letter. A synthetic one-million-quantity row reproduces this refusal before the change.

| Report | PDF before | This change / follow-up |
|---|---|---|
| Production Management Summary | Shared PDF button; wide-table refusal reproducible | Compact legacy PDF layout, week headings, Letter-first sizing |
| Production Management Details | Shared PDF button; wide-table refusal reproducible | Compact legacy PDF layout, week headings, Letter-first sizing |
| Production Management by Producer | Shared PDF button | Unchanged; compact-layout/scale review is a follow-up |
| Production Management Details by Grader | Shared PDF button | Unchanged; compact-layout/scale review is a follow-up |
| Nest Run Details | Shared PDF button | Unchanged; compact-layout/scale review is a follow-up |

There is no separate catalog entry called “Details by Producer”. No other Production report was found.

## PDF-only presentation

`app/services/production_pdf.py` projects already-exported strings; it does not calculate measures. Headers: REG#, Type, Specialty Type, Housing System, Colour, J, XL, L, M, S, PW, B, C, NR, CR, OL, ON, RJ, LK, FG, FC, Non Levy, Levy, Total. Account Name, Grading Station and J2 are omitted only in these two PDFs, as requested. Row Type becomes a bold grey total label; Week becomes a blue section heading. Summary keeps each existing Week Total first, followed by detail rows, then Grand Total. Details preserves its existing producer/week row order; a week heading repeats on each week transition rather than reordering records. Headers repeat across pages.

Title, Production Week range, selected Type names, In Dozens and the existing provisional HALF_UP/J2/DEV_TEST caption appear above the table. Existing notes remain footnotes. Existing logo, Halifax timestamp, Page x of y footer, permission check and REPORT/PDF audit event are reused. Existing page controls already place PDF beside CSV/XLSX. Empty Summary/Details results now show “No production records match the selected parameters; PDF export is unavailable.” rather than offering an empty PDF. The generic renderer’s empty-PDF behavior remains available for other callers.

Both use landscape Letter first (24pt side margins), trying 8, 7.5, 7, then 6.5pt. Every quantity, including totals and sparse outliers, is measured in bold and assigned sufficient width for the complete value; no number is truncated or split. Only if Letter cannot fit at 6.5pt is landscape Legal tried. If Legal also fails, a clear CSV/XLSX message remains. Synthetic 100,000,000 values in every quantity column exercise Legal at 6.5pt; trillion-sized values exercise the safe refusal. Ordinary small reports use Letter at 8pt; full-year fixtures use Letter at 6.5pt. No new dependency.

## Validation

Before: release **2,012 passed, 1 skipped, 0 failed** (641.00s); root **706 passed, 0 failed/errors** (190.83s).

After: release **2,031 passed, 1 skipped, 0 failed** (533.37s); root **706 passed, 0 failed/errors** (195.17s). All 19 added cases pass. Release uses Python 3.12.14; root uses the existing isolated Python 3.11 CI environment. Commands: `python -m pytest -q` at root; `python -m pytest -q --basetemp ../../.local/release-complete-temp` in the release. An earlier overlapping targeted/full run collided on the configured Windows temporary auth database; the final full run used its own temporary directory and passed without application changes.

New synthetic coverage verifies mock and offline Snowflake repository paths (existing bound read, fake executor only), every projected detail/subtotal/grand-total value, unchanged DataFrame/CSV/XLSX, header text, repeated headers, empty results, permissions/audit, no blank second page for small reports, 1,300-source-row pagination, atomic numeric widths, Legal fallback and refusal. Existing catalog-wide PDF tests now expect only the approved PDF-only column aliases/omissions for these two reports; other report header assertions are unchanged.

Measured PDF rendering only, local Python 3.12.14 / ReportLab 5.0.0 (the existing environment.yml pin), 1,300 synthetic source rows over 202601–202653:

| Report | Existing result rows | Time | PDF pages | PDF bytes | Paper | Minimum font |
|---|---:|---:|---:|---:|---|---:|
| Summary | 1,354 | 5.232s | 46 | 617,759 | Landscape Letter | 6.5pt |
| Details | 1,301 | 5.139s | 44 | 602,019 | Landscape Letter | 6.5pt |

Peak traced allocations in a separate instrumented full-year render: Summary 115.30 MiB; Details 107.89 MiB. Tracing increases execution time (37.109s / 31.741s), so the table reports uninstrumented timings. Times are local measurements, not a Snowflake latency guarantee. Layout retains the existing 5,000 exported-result-row safety limit. Small and full-year first/last pages were rendered with Poppler and visually reviewed for borders, header/logo, totals, spacing, page footer and clipping. A separate PDF text extraction comparison verified all 54 Summary total rows and the Details grand total, every quantity exactly equal to the source result. Synthetic generated PDFs/PNGs stay ignored under this worktree’s `.local/`.

## Original shipped byte proof (d5ffbe1)

All `snowflake.yml` artifact globs plus streamlit_app.py, environment.yml and .streamlit/config.toml were hashed before edits. Before: 114 files; after: 115 (one new service). **112 existing shipped files are byte-identical**, including builders, repositories, SQL, configuration, pages, data, existing CSV/XLSX code and logo. Only these shipped paths change:

| Shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| `app/services/production_pdf.py` | `NEW` | `e1723c2a3cf9d23ba34b5717aad524ce933de4d1af32a95871017a87d830c841` |
| `app/services/report_pdf.py` | `73284c37073feac1572f31d1ad1c193476a63911967ab9965e4bf73aba4ed1a7` | `09e38bb5dc62a626f30983294eb652189fc3b15c3f99206b962ce724e761d0f4` |
| `app/services/report_pdf_ui.py` | `ec40552b9f7c69fc883764c08e80f4a336830b23c50b3b4f55944ca108c99830` | `f085964556fc2eb4fcdfc44ca894d7b24c69c56927c31a5a5b27009d15825068` |

Other changes are two test files, this report and the live runtime-diff manifest. No schema, data, report calculations, filters, screen values or CSV/XLSX output changed. No real producer/flock files added. Other worktrees/branches untouched.

The original DELIVERY_RUNTIME_DIFF_20261030.json was regenerated from final LF-normalized bytes, preserving main’s entries and adding three new paths, for **94 candidate hashes**. Historical captured-source manifests remain baseline evidence and are unchanged.


## Main integration — 2026-11-12

Merged `origin/main` **b2aefd984cdb56668118138f5f890a39e2644715** (Facility Details PR #26) into the existing Production PDF branch; history is preserved for a normal push. Only DELIVERY_RUNTIME_DIFF_20261030.json conflicted. The conflict was resolved by taking main’s whole version, adding the three Production PDF artifact paths programmatically, and recomputing every candidate hash from final LF-normalized bytes. No JSON/hash conflict was hand-merged. All of main’s Facility Details entries remain, including its service, tests and documentation. The resulting live manifest has **97 candidate hashes**; captured historical manifests are unchanged.

Integration validation: release **2,055 passed, 1 skipped, 0 failed/errors** (587.55s); root **706 passed, 0 failed/errors** (158.35s). Both suites ran in full with dedicated temporary directories: `python -m pytest -q --basetemp ../../.local/integration-release-temp` from the release and `python -m pytest -q --basetemp .local/integration-root-temp` from root. The 24 Facility Details cases and 19 Production PDF cases pass together. All three Production PDF shipped source files are unchanged from a7e667d. No report calculation, production display, Facility Details implementation, repository, SQL or dependency was changed to integrate main.

### Shipped proof against new main

The raw-byte baseline is the original pre-edit artifact snapshot, updated with the non-overlapping Facility Details files imported from main. These main changes do not intersect any Production PDF shipped path. Every other shipped file was also independently compared with main’s stored content (accounting for the established local LF/CRLF checkout representation). Main has **115** shipped artifacts; the integrated candidate has **116**. **113 existing shipped files remain byte-identical**. Exactly these three paths differ from new main:

| Shipped path | Main baseline raw SHA-256 | Integrated raw SHA-256 |
|---|---|---|
| `app/services/production_pdf.py` | `NEW` | `e1723c2a3cf9d23ba34b5717aad524ce933de4d1af32a95871017a87d830c841` |
| `app/services/report_pdf.py` | `73284c37073feac1572f31d1ad1c193476a63911967ab9965e4bf73aba4ed1a7` | `09e38bb5dc62a626f30983294eb652189fc3b15c3f99206b962ce724e761d0f4` |
| `app/services/report_pdf_ui.py` | `ec40552b9f7c69fc883764c08e80f4a336830b23c50b3b4f55944ca108c99830` | `f085964556fc2eb4fcdfc44ca894d7b24c69c56927c31a5a5b27009d15825068` |

The new-main comparison confirms the Facility Details page and helper remain exactly as merged on main. No other branch/worktree was edited, no real data files were added, and no deployment/Snowflake calls were made.
