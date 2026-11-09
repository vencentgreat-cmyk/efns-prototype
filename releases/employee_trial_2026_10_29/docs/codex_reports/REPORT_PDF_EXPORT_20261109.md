# Report PDF exports

Base: `codex-printable-forms-20261109` (`3367b70`). No database access, SQL changes, deployment, report calculation changes or CSV/XLSX payload changes.

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
- Each tabular PDF receives the identical DataFrame passed to CSV export. Pandas CSV cell text is used without numeric conversion, rounding, aggregation or row/column removal. The DataFrame and its attrs are not mutated. Spreadsheet formula-escaping apostrophes are unnecessary in PDF; literal text is HTML-escaped for ReportLab instead.
- Headers show the catalog report title and the applied/run parameters rather than subsequently edited widget values. Every page repeats the EFNS header and table column headings while the table continues. Footers show Page x of y and the PDF generation time explicitly converted to America/Halifax.
- Letter landscape is used for more than seven columns; otherwise Letter portrait. Content-based widths wrap text, preserve numeric values as single tokens, and use a minimum 7pt font. Totals/subtotals already present in the DataFrame are bold with grey fill. No totals are recomputed.
- Notes from DataFrame.attrs and supplied report metadata are appended after the table. Production PDF notes include the existing compact caption, rounding summary, record diagnostics and source notes, like the existing XLSX Notes content. Notes never become CSV rows.
- Empty tables retain headers and print No records found. Missing scalars and standalone missing-value tokens are blank. More than 5,000 rows is refused before rendering, with a CSV/XLSX recommendation; existing CSV/XLSX exports keep working. Specialized forms use the same limit across their data tables.
- A table whose numeric values and column count cannot fit on Letter at 7pt is refused with a clear CSV/XLSX recommendation rather than splitting numbers, cutting columns or shrinking below the font floor. All catalog fixture tables fit.
- PDF buttons require EXPORT_REPORT. A click records the existing EXPORT / REPORT event with format PDF and row_count, using the existing authentication store. No authentication, connection, transaction, lock or repository implementation was modified.

## Comparison limits

- PDF values match the CSV representations. Production and quota transaction/lease/history pages apply comma grouping via a screen-only Styler; PDFs retain the CSV number strings. Customize Report timestamp columns likewise retain CSV timestamps rather than browser-specific display formatting. No numeric precision is lost.
- Metric cards outside the export DataFrame are not reconstructed as table rows. Existing summaries and table subtotal rows remain exactly as exported. The shared renderer follows the supplied SSRS-style design rather than reproducing a separate pixel-specific RDL layout for each report. Helvetica remains the available base font instead of legacy Arial.
- The three printable forms keep their original specialized layouts and content from the requested base; this branch does not pull in corrections from another branch.

## Verification

Catalog-wide tests exercise normal, empty, nullable, nonmatching-range and over-limit frames; validate title, parameters, every column heading, orientation and missing-value handling; and compare DataFrames and CSV/XLSX values before/after rendering. Additional tests cover precision, leading zeros, markup escaping, unchanged numeric tokens, multi-page headers and exact page counts, Halifax time conversion, subtotal styling, wide-column bounds, specialized-form limits, permissions and audit events. Authenticated page smoke checks require an Export PDF button for every runnable tabular report. Representative Flock, Quota, Salmonella and real legacy Production fixtures are rendered to PNG for visual inspection.
