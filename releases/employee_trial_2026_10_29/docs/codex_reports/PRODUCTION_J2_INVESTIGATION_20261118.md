# Production J / J2 investigation — 2026-11-18

Branch: `codex-remove-duplicate-j2-20261118`. Base: latest fetched `origin/main`, `e906481f3a46da8d08521e0ee6e979d680c2b414`.

## Decision

No column removed. The user explicitly required no removal if the legacy layout contains both columns. The preserved legacy Summary CSV contains both J and J2 and all 79 data rows have equal nonblank values. The other three preserved legacy CSVs have only J2. Consequently the evidence does not support deleting the duplicate across all these reports under the stated condition. All runtime and test source bytes, report filters, calculations, totals and export behavior are unchanged. Only this report and its regenerated live-manifest entry change.

## Source and shared report paths

- `app/services/production_reports.py:13`: J maps to the stored `JUMBO` component. At lines 160–161 it is rounded by the existing per-component HALF_UP rule, then J2 is assigned exactly that same value: `measures['J2'] = measures['J']`. J2 is a presentation alias, not another database field or another size category.
- `data/repositories/snowflake.py:63`: the existing production read columns include JUMBO, not a separate J2 field. No repository or SQL change is needed or made.
- `app/services/production_reports.py:16`: shared AMOUNTS includes both J and J2. `build_production_report` returns that shared column list at line 233 for Summary, by Producer, Details and Details by Grader. This shared projection causes both columns to appear even where the legacy export contains only one. Nest Run Details has its own NEST_FIELDS and no J/J2 columns (line 258).
- `app/pages/4_Reports.py:193`: the displayed frame uses these columns; CSV and XLSX export the same result at lines 197–198, and the PDF adapter receives it at lines 199–200. There is no independent per-report J2 database calculation.
- `app/services/production_reports.py:162`: Levy sums the eight original size components, counting J once and excluding J2. NonLevy and Total at lines 163–164 also do not double-count J2. Account/producer and grand totals sum the existing measures via `_total` at line 189. No totals bug was found.

## Legacy evidence, read directly without modifying fixtures

| Preserved legacy CSV | Header line | Data rows | Jumbo columns |
|---|---:|---:|---|
| `tests/fixtures/production_reports/EIMSProductionManagementReport.csv` | 4 | 79 | Both J and J2; equal on every data row |
| `tests/fixtures/production_reports/EIMSProductionManagementReportbyProducer.csv` | 4 | 79 | J2 only |
| `tests/fixtures/production_reports/EIMSProductionManagementDetails.csv` | 1 | 25 | J2 only |
| `tests/fixtures/production_reports/EIMSProductionManagementDetailsbyGrader.csv` | 1 | 129 | J2 only |

Inspection uses csv.DictReader from the Production_Week header, retaining rows with MarketingType. No producer values are reproduced in this report. SSRS CSV headers are evidence of exported columns; they do not prove that the original rendered PDF displayed every SSRS field. There is no original Production Management legacy PDF committed in tests/fixtures; the legacy PDFs there are printable forms and Producers Over Quota. Thus the original Production PDF's visible jumbo header cannot be independently verified from a committed PDF.

The existing legacy-PDF decision is documented in `docs/codex_reports/PRODUCTION_MGMT_PDF_20261112.md:21`: Summary and Details PDFs keep J and omit J2, Account Name and Grading Station. `app/services/production_pdf.py:5–8` implements this shared PDF-only column projection. Both PDFs already have one jumbo column, J; both remain unchanged. Other production report PDFs use the generic export profile and remain unchanged too.

## Validation

The existing `tests/test_production_reports.py:17` parametrizes all four legacy fixtures, checks every displayed numeric component, asserts J equals J2, verifies grand totals against displayed rows, and verifies legacy per-producer/weekly repeated subtotals independently. `tests/test_production_mgmt_pdf.py` additionally checks the PDF-only projection excludes J2. These tests are retained without weakening. Since no report implementation changes, before/after report and export behavior is identical by source-byte comparison; no new before/after-calculation test is necessary for this investigation-only outcome.

Full release suite: **2,216 passed, 1 skipped, 0 failed/errors**, 803.14 seconds (Python 3.12). Full root suite: **706 passed, 0 failed/errors**, 170.22 seconds (Python 3.11). Both ran `python -m pytest -q` with separate worktree-local `--basetemp` directories. No tests or expectations were changed.

Shipped-file proof: **all 118 shipped files are byte-identical** to the pre-investigation snapshot. The artifact file set is unchanged; there are no modified shipped paths. This proves all report builders and PDF/CSV/XLSX implementation bytes, including per-producer and grand-total calculation paths, remain unchanged. The live runtime-diff manifest is regenerated from main's entries plus this document's entry, computing every candidate SHA-256 from LF-normalized final file bytes. No historical manifests are rewritten.

No Snowflake connection, queries, deployment or PR. No real-data files added; existing fixtures were read only. All other branches and worktrees remain untouched.
