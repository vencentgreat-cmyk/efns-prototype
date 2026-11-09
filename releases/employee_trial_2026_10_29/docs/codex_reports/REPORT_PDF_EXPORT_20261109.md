# Report PDF exports

Base: `codex-printable-forms-20261109` (`3367b70`). No database access, SQL changes, deployment, report calculation changes or CSV/XLSX payload changes.

Final trial integration: `codex-trial-final-20261109` starts at `bdd451e` and merges `c9e18f6` in merge commit `b68c734`. Both printable-form corrections and Export PDF integration are retained. The manifest keeps the union of entries from both parents and recomputes every candidate LF-normalized hash; raw binary hashes are also retained.

## Available reports with Export PDF

| Group | Reports |
| --- | --- |
| Production (5 new) | Production Management Summary; Production Management by Producer; Production Management Details; Production Management Details by Grader; Nest Run Details |
| Quota (6 new) | Quota Transactions Report; Quota Leases Report; Quota Leases Sorted by End Date; Quota History Report; Quota Summary Report; Quota Summary Details |
| Flock (10 new) | Flock Status Report by Producer; Flock Salmonella Testing Schedule; Scheduled Flock Placements; Flock Age Report; Flock Status Report; Flocks Counted Report; Flocks Needing Counts Report; Flock Disposals Report; Flock Current Report; Flock Current Report by Producer |
| Salmonella (1 new) | Salmonella Test Report, on its dedicated report page |
| Custom (1 new) | Customize Report preview; saved configurations also expose PDF export |
| Existing printable forms (3 labels standardized) | EIMS License Application Form; Flock Permit Form; EIMS Salmonella Testing Form retain their specialized legacy PDF layouts and now use the Export PDF label and REPORT export audit event |

Salmonella Testing Letter remains Not included in this trial. All 26 Available catalog entries declare PDF capability.

## Data and presentation

- Shared renderer: `app/services/report_pdf.py::render_report_pdf`; UI permission/audit adapter: `app/services/report_pdf_ui.py`. ReportLab, the PNG logo and header RGB are reused from the printable forms implementation. No dependencies were added.
- Each tabular PDF receives the identical DataFrame passed to CSV export. CSV cell text is unchanged except for exact per-report quantity-column formatting in PDF: thousands separators, and removal of redundant fractional zeros only when the value is whole. Decimal text parsing avoids float conversion and fractional rounding. The DataFrame and its attrs are not mutated; CSV, XLSX and on-screen output are unchanged. Spreadsheet formula-escaping apostrophes are unnecessary in PDF; literal text is HTML-escaped for ReportLab instead.
- Headers show the catalog report title and the applied/run parameters rather than subsequently edited widget values. Every page repeats the EFNS header and table column headings while the table continues. Footers show Page x of y and the PDF generation time explicitly converted to America/Halifax.
- Letter landscape is used for more than seven columns; otherwise Letter portrait. Content-based widths wrap text, preserve numeric values as single tokens, and use a minimum 7pt font. Totals/subtotals already present in the DataFrame are bold with grey fill. No totals are recomputed.
- Notes from DataFrame.attrs and supplied report metadata are appended after the table. Production PDF notes include the existing compact caption, rounding summary, record diagnostics and source notes, like the existing XLSX Notes content. Notes never become CSV rows.
- Empty tables retain headers and print No records found. Missing scalars and standalone missing-value tokens are blank. More than 5,000 rows is refused before rendering, with a CSV/XLSX recommendation; existing CSV/XLSX exports keep working. Specialized forms use the same limit across their data tables.
- A table whose numeric values and column count cannot fit on Letter at 7pt is refused with a clear CSV/XLSX recommendation rather than splitting numbers, cutting columns or shrinking below the font floor. All catalog fixture tables fit.
- PDF buttons require EXPORT_REPORT. A click records the existing EXPORT / REPORT event with format PDF and row_count, using the existing authentication store. No authentication, connection, transaction, lock or repository implementation was modified.

## PDF quantity allowlist per report

The mapping is `QUANTITY_COLUMNS_BY_REPORT` in `app/services/report_pdf.py`, keyed by catalog report ID and exact exported column label. The UI passes that ID explicitly. Unknown reports or calls without an ID do not infer quantities. Detail and total rows use the same rules; notes and parameters are not reformatted. Properly grouped numeric input is accepted, negative signs and genuine fractional precision are preserved, and blank/non-numeric values remain unchanged. For example: `34526.00` -> `34,526`; `-1234.5000` -> `-1,234.5000`.

| Catalog report ID(s) | Allowlisted columns |
| --- | --- |
| production-management-summary; production-management-producer; production-management-details; production-management-grader | J, J2, XL, L, M, S, PW, B, C, NR, CR, OL, ON, RJ, LK, FG, FC, NonLevy, Levy, Total |
| production-nest-run | NR, NR25, NR24, NR23, NR22, NR21, NR20, NR19, NR18, NR17, FG, FC |
| quota-transactions | Bird Count |
| quota-leases; quota-leases-by-end-date | Price, Bird Count |
| quota-history | Bird Count, Quota Count Adjust, Running Balance, Current Quota |
| quota-summary | Issuance |
| quota-summary-details | Account Total, Quota Bird Count |
| flock-status; flock-status-producer | Sold, Inventory, Quota, Up. Flocks |
| flock-age | Inventory, Quota, Up. Flocks |
| flock-current; flock-current-producer | Counted, Inventory, Up. Flocks |
| flock-salmonella-schedule | Inventory |
| scheduled-flock-placements | Inventory, Quota, Total Producers, Total Flocks, Total Birds |
| flocks-counted | Quota, Birds Counted |
| flocks-needing-counts | Bird Count |
| flock-disposals | Quota, Placed, Disposed |
| salmonella-report | Number of Samples |
| custom-builder (including saved configurations) | Bird Count, Quantity, Quota Count, Price, Number of Samples, Total Received, Total Accepted, Source Total, Flock record count, Record count, Source Total known count, Source Total missing count |
| license-application; flock-permit; salmonella-form | None in the shared tabular renderer. Specialized legacy form formatting is retained: licence quota already uses commas, permit Birds retains its legacy form representation, and the Salmonella form has no quantity column. |

Everything outside this allowlist remains CSV text. Reg No, Registration Number, Permit No, Flock Number, Week, Year, ages, dates, IDs, percentages and phone numbers are never grouped. Custom report formatting applies only when an allowlisted column is actually selected; the allowlist is not expanded from numeric field types.

## Comparison limits

- PDF quantities now use the explicit grouping rules above without changing their numeric values. Fields outside the allowlist retain CSV representations. Customize Report timestamp columns retain CSV timestamps rather than browser-specific display formatting. No numeric precision is lost.
- Metric cards outside the export DataFrame are not reconstructed as table rows. Existing summaries and table subtotal rows remain exactly as exported. The shared renderer follows the supplied SSRS-style design rather than reproducing a separate pixel-specific RDL layout for each report. Helvetica remains the available base font instead of legacy Arial.
- The three printable forms retain their specialized layouts and include the merged Active Layers/housing-system, Self-resolution and result-date fallback fixes, plus the Export PDF labels and audit behavior.

## Verification

Catalog-wide tests exercise normal, empty, nullable, nonmatching-range and over-limit frames; validate title, parameters, every column heading, orientation and missing-value handling; and compare DataFrames and CSV/XLSX values before/after rendering. Additional tests cover per-report allowlist coverage against catalog/schema labels, exact grouping, whole-value zero removal, fractional precision, signs, protected identifier/date/age/percentage/phone fields, unknown reports, detail and total rows, leading zeros, markup escaping, intact numeric tokens, multi-page headers and exact page counts, Halifax time conversion, subtotal styling, wide-column bounds, specialized-form limits, permissions and audit events. Authenticated page smoke checks require an Export PDF button for every runnable tabular report. Representative Flock, Quota, Salmonella and real legacy Production fixtures are rendered to PNG for visual inspection.
