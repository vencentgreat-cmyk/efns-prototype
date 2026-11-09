# Claude Handoff: Produce the Word Manual and PDF

Create an editable English DOCX and matching PDF for Dr. Lu Yang and future EFNS
maintainers, using this complete documentation package. Do not convert the former
presentation into one page per slide. Title: **EFNS Database Design and Maintenance
Manual**. Date: **13 October 2026**. Status: **Working documentation draft - Not approved**.

The primary manuscript is `EFNS_Database_Design_Manual.md`. It contains explanatory
paragraphs, all 27 table specifications and the full dictionary of 440 table fields
plus 80 view outputs. Do not omit the dictionary or replace it with an Excel link.
The standalone dictionary duplicates Section 8 for convenient reading; do not
append it a second time. The JSON/CSV, exact view DDL, relation list and evidence
receipts are factual backing, not extra prose to indiscriminately paste.

## Required Word Structure

Use the revised per-object A/B/C dictionary tables, not the retired repeated
field cards. Reorganise narrow complementary tables keyed by exact field name
for Word pagination; do not copy redundant boilerplate once per field. Keep all
440 table fields and 80 view outputs, each concrete input path, specific rule,
example and claim-specific evidence/status. Shared conventions belong at the
dictionary opening. Metadata, unit, code and business/source confirmation must
not collapse back to one universal unknown/verified statement.

- Use true Word Heading 1/2/3 styles, an updateable table of contents, numbered
  tables/figures, cross-references, page numbers and consistent headers/footers.
- Preserve full explanations of grain, input route, optional references, historical
  exceptions, numerical semantics and limitations. Avoid turning paragraphs back
  into presentation fragments.
- Include the complete dictionary in the DOCX. It can occupy a substantial technical
  chapter/appendix. Do not omit null, zero-heavy or currently unused fields.
- Use the table-grouped storage metadata and complementary definition/source/rule
  tables; do not recreate one repeated property card per field. Avoid one 20-column
  table. Keep exact type, default, nullable, source, keys/references and scope.
- Use at least normal readable body text (about 10.5-11 points), repeat table
  headers, break only at safe rows, and use landscape sections where genuinely
  necessary. Do not shrink the complete dictionary or ERD to fit an arbitrary
  page budget. Do not duplicate boilerplate to create pages.
- SQL should use a readable monospace style and wrapped lines without changing
  exact identifiers. Reference-only GET_DDL is not an executable deployment instruction.

## Diagram Handling

Use `erd/overview.svg` for orientation, then module sheets and exact FK relationship
sheets. The complete reference poster is not suitable as a reduced Word thumbnail.
Use editable SVG or high-resolution PNG; preserve DOT sources in the handoff.
Each Rxx label resolves through `erd/relationship_atlas.json`. Every declared FK
must be documented once in the full relationship appendix/list, including both
members of composite keys and all self-reference roles.

The 39 single-FK sheets are supporting material, not a requirement for 39 separate
Word pages. Select figures where they clarify the explanation; keep a complete
relationship list and all necessary composite/self-reference descriptions. Do
not mechanically put each FK on one page or omit a relationship to save space.

If a module becomes too small at the page width, split it into the supplied
individual relationship sheets and retain the module overview only as orientation.
The `erd/full/` panels split full field lists into at most 18 columns-per-panel
(meaning field entries, not a horizontal 18-column table). Do not merge them back
into an illegible poster. The 60-field Production list needs several panels.

Keep non-identifying relations dashed, identifying ones solid, repeated parent
tables grey with a solid border, optionality/Crow's Foot notation and labelled
self-loops. RAW_ROW→BATCH is identifying because its FK is part of the composite
PK; map/correction→RAW remain non-identifying. Do not add Allocation/Calendar FKs
or infer new connections by matching names. Query JOIN dependencies are distinct
from declared FK lines.

## Factual Boundaries

Use the regenerated counts and current read-only results, not older slides. Do not
claim a fresh 13 October live-source download, a new browser acceptance, a database
write/deployment, or an approved unit/formula. The current application checks used
a previously saved deployed source snapshot against current DEV. Local differences
are listed separately. Keep the evidence dates and IDs.

Preserve 85,962 original targets +112 correction targets +675 additional date
lineages +159 pending =86,908 source rows. The 675 are not new date targets. The
159 are still unresolved; reporting changes did not resolve ownership conflicts.
Production all-DEV association counts are not original-batch association counts.
TOTAL is Source Total, never substituted with received or accepted values; all-null
sums remain NULL, while actual zeros/negative adjustments stay numeric.

Unconfirmed meanings should state precisely what remains unknown, who should
confirm it and which business output it affects. Do not invent original design
motives or assert strict 3NF. The database is implemented in DEV, not an unbuilt
proposal. Future options must remain clearly labelled recommendations.

## Final QA and Deliverables

Produce DOCX and corresponding PDF. Render every page and inspect text/table
overflow, orphan headings, overly dense rows, cropped columns and unreadable
figures. Check relationship endpoints/labels against the same metadata, not just
that files open. Update the TOC and references after pagination. Check all 27
tables, 520 entries and 39 FK relationships remain represented using Coverage_Check.
Preserve source evidence and return the DOCX/PDF plus a short rendering/coverage
check report. Do not modify the database, code or original source documents.
