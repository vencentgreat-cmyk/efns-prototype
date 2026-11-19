# Production weekly totals, units and overall quota total - 19 November 2026

Branch: `codex-prod-week-totals-units-20261119`. Base: fetched `origin/main`, `00137e61af49177e897407399bbbec8444acae4d`.

## Before changing presentation

| Report | Screen, CSV and XLSX existing rows | Existing PDF |
|---|---|---|
| Summary | Week Total before each observed week, detail rows, Grand Total | Same measures/rows in compact legacy layout with week headings |
| By Producer | Producer-grouped details, Producer Total per group, Grand Total | Same rows, generic layout |
| Details | Producer-grouped details, Grand Total; no producer totals | Same measures/rows in compact layout; no weekly-total block |
| Details by Grader | Producer Header, producer-grouped details, Grader Total; no producer totals | Same rows, generic layout |

All four already have J only in displayed/exported columns. Internal J2 remains a calculation alias. Production detail source reads, filters, rounding and Dozens builders are unchanged. Nest Run is out of scope and does not use the new controls or projection.

## Approved presentation

Unit of Measure defaults to Dozens; Weekly totals only defaults off. Summary reuses its existing Week Total rows. The other three append a labelled Week Totals block before their existing final total. Every old Dozens row/value and its relative order is preserved. Weekly-only shows week totals plus a final Grand Total in all four formats.

Boxes uses the staff-confirmed legacy rule for all four reports: named constant DOZENS_PER_BOX = 15; floor each existing detail-row component independently, derive Levy/NonLevy/Total from converted components, and sum converted rows for all aggregates. It does not divide aggregate Dozens totals. All-zero rows remain correct zeros; no legacy subtotal-copy quirk is reproduced. Integer-ratio arithmetic avoids float rounding and Decimal division-context surprises.

CSV starts with its column header. Dozens headers are unchanged; only Boxes quantity headings gain the suffix (Boxes). Screen/PDF subtitles identify the unit; XLSX keeps its numeric data-sheet structure and records unit/caption in the Notes sheet. The required Boxes caption is shared by screen, PDF and XLSX Notes. Retained source TOTAL diagnostics remain explicitly in Dozens.

Producers Over Quota appends one final Total row: sum of listed producer totals, divided by the sum of those same producers' confirmed quotas counted once. Red percentage styling uses the existing strict, unrounded comparison. Prior producer rows and provincial summary metrics are unchanged. If the listed-producer aggregate differs from the province summary, report notes disclose the inventory/allocation difference and utilization discrepancy; no forced reconciliation occurs. Existing tests explicitly distinguish producer-level rows from the new final aggregate.

## Assumptions and boundaries

1. Only observed weeks in the selected/filtered detail rows receive totals; empty weeks are not zero-filled, preserving the existing absent-week policy. Weekly totals sum detail rows once, never subtotals or headings.
2. Conversion starts from each existing report-row Dozens component, after the unchanged source-component rounding. Raw stored quantities are not rewritten.
3. Missing components stay unknown. Existing known-value subtotal behavior is retained; no missing amount is fabricated as zero.
4. Weekly-only calls the selected-grader final aggregate Grand Total; the full grader view retains its original Grader Total label and value.
5. XLSX unit information is in Notes so its data header stays on the first row and its numeric table columns remain stable.
6. No listed producers means no artificial overall zero row. Positive-quota producers with no current flocks retain their existing zero producer total. Overall totals with no known Inventory remain blank.
7. All pre-existing Dozens rows/values are preserved, as explicitly clarified; adding requested totals necessarily changes the complete file bytes/row count. The CSV data bytes of the old rows alone remain identical.

## Validation

All new tests use synthetic identities and synthetic quantities. No real farm names, quantities or new legacy extracts were copied. Existing legacy expected values were not rewritten. Default Dozens, Boxes component/aggregate invariants, weekly-only, unit-labelled CSV/XLSX/PDF, screen controls, red overall-total styling and a synthetic province-summary disagreement are covered.

Full release suite (Python 3.12): **2,274 passed, 1 skipped, 0 failed**, 809.11 seconds. Full root suite (Python 3.11): **706 passed, 0 failed**, 180.34 seconds. Focused production/POQ checks: **133 passed**. Both full suites used `python -m pytest -q` with separate worktree-local temporary directories. Existing numeric fixture expectations were unchanged. Direct comparisons against main verified every original Dozens row/value and old-row CSV bytes, plus every original POQ row and provincial summary. Both existing POQ parity fixtures agree with the new overall total; the synthetic scope-difference test demonstrates an explicit difference note without forcing the summary.
Shipped-file comparison: **112 existing shipped files byte-identical**, six existing shipped files changed, one new service shipped through the existing wildcard. **128 candidate LF-normalized hashes** regenerated from main entries plus the new artifacts; historical captured manifests unchanged. Synthetic Boxes PDFs were generated and visually checked in full and weekly-only modes; no real input files were added.

No Snowflake access, deployment or PR. Other branches/worktrees are unchanged.

## Exact changed files and shipped-byte proof

| Shipped file | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| `app/pages/4_Reports.py` | `328bb47009c28e6ec8abf75522dd31ca3ded726a52f3bf10c0aa730ab15f5c58` | `378adbfaeba8ac16ebea2c477cb81ee79a053603efcfb330d09d9343bcd42ad6` |
| `app/services/producers_over_quota_report.py` | `cd1b18832dbb19f57818b6d34b7774891f28ce5d307c7497ab7a442af27513c5` | `848ff83f1554fd32a70a879d2497b60f5067f8912438fd38b3aa1f6c01ee2769` |
| `app/services/production_pdf.py` | `aa693fbb03c00b04996a668d6a2516cd0cf3ac344df04a296649a0bf516d7b1d` | `f74b93fecf687f97d921db328fbc80f3dfd6aa5d02e24a199d2b08c44dfd79aa` |
| `app/services/production_reports.py` | `5dfbf970327375c9a7d004ac9c8bc4dce0c1d2a1d6fbd66b9f7f28a68053bc64` | `ae04664e2205e7574f25f9ecacf9a3eb8e5777ea8e657efb165789f0890479a5` |
| `app/services/report_center.py` | `e8f4383b0032095591ed254f18c104731b247d327820a211baff314a0cdfcd29` | `06babe00262179307431fbfc6feb95c245967db6f5cfec928aae304b36ddd0cb` |
| `app/services/report_pdf.py` | `4b9ac5b69284687b1355da5364578cee38203f18095258fad23a1db98ee807c0` | `1140a53b38a52ef2bfb8f0ea2179485fbad616c1403cf822ad3d444961c63414` |
| `app/services/production_presentation.py` | `NEW` | `97e165e5129acdb4eda1b1320f41ca1c58e3bef121a0a434596c051b36f8d40f` |

Other changed files: `tests/test_producers_over_quota.py`, `tests/test_poq_parity.py`, `tests/test_production_units_week_totals.py` (new), `tests/test_producers_over_quota_overall_total.py` (new), this report, and `DELIVERY_RUNTIME_DIFF_20261030.json`. No other shipped file changed.
