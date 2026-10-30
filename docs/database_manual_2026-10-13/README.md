# EFNS Database Documentation Handoff

Prepared 13 October 2026 for Dr. Lu Yang and future maintainers.

Targeted dictionary revision: 520 fields are organised by per-object A/B/C narrow
tables, with concrete input paths, typed examples and claim-specific evidence.
The database snapshot and executed-query dates are unchanged; no new scan or
deployment took place. See Dictionary_Revision_Check.json and the explicit
source-explanation gaps. Detailed ERD files and all 39 relationships remain intact.

## Start Here

- **English manual:** [EFNS_Database_Design_Manual.md](EFNS_Database_Design_Manual.md)
- **Chinese review guide:** [Chinese_Review_Guide.md](Chinese_Review_Guide.md)
- **Word-production instructions:** [Claude_Word_Production_Prompt.md](Claude_Word_Production_Prompt.md)
- **Readable full dictionary:** [Complete_Data_Dictionary.html](Complete_Data_Dictionary.html)
- **Exact enhanced fields:** [metadata/enhanced_dictionary.csv](metadata/enhanced_dictionary.csv)
- **Unified structure:** [metadata/structure_metadata.json](metadata/structure_metadata.json)
- **Coverage:** [Coverage_Check.json](Coverage_Check.json)
- **Read-only SQL:** [verification.sql](verification.sql)
- **Evidence index:** [Evidence_Index.md](Evidence_Index.md)
- **Field claim evidence:** [Field_Evidence_Index.md](Field_Evidence_Index.md)
- **Unlocated assignment paths:** [metadata/source_explanation_gaps.csv](metadata/source_explanation_gaps.csv)

The manuscript includes every deployed table and embeds all 520 field entries.
The standalone dictionary is a duplicate reading format; do not append it a
second time to Word. Original documents remain untouched. This package is the
requested Word-production source, not a newly authored DOCX/PDF.

## Diagrams

`erd/overview.*` is orientation, not a complete FK map. Eight module sets cover
the business/tracking/support areas; `erd/complete_core_poster.*` contains the
full CORE key map for zoomed reference. `erd/relationships/` contains one exact
sheet per FK including composite/self-reference cases. `erd/full/` covers every
table field in manageable panels. DOT and SVG are editable; PNG is available
for insertion. Use relationship sheets when a module is too wide for a normal
Word page. Never reduce the reference poster until text is illegible.

`erd/relationship_atlas.json` resolves every Rxx label. `erd/render_validation.json`
records image sizes/counts. Module endpoints express the declaration's intended
cardinality, not a guarantee of engine enforcement or current data completeness.

## Evidence and Scope

Fresh DEV metadata/aggregate checks are saved under `evidence/current/` with query
IDs. Current application-output checks use the saved 12 October deployed package
and real DEV reads under EFNS_DEV_DEPLOYER/secondary roles NONE; they do not imply
a fresh download or browser acceptance on 13 October. Local/snapshot hash differences
are separate in `metadata/local_vs_deployed.csv`.

`evidence/prior/` is dated previous execution evidence, including the original
dictionary workbook. It is not relabelled as a current enhanced workbook. The
material inventory contains hashes, actual paths, dates, workbook sheets and
archive members. A corresponding v1.4 PPTX was not found in Downloads.

No application logic, database data, DDL, view, permission, import or deployment
was changed. No new business records were created. Original RAW/rejected rows,
675 additional date lineages and 159 pending records are retained. No Git commit
or push occurred. Query logs contain schema/count/identity parameters, not raw
PII or credential values; treat IDs and query receipts as internal review material.

## Generation / Reverification

The scripts under `generation/` are document/diagram generators or SELECT/SHOW-only
checks. They are not application code and are not uploaded to Streamlit. Review
their evidence paths and runtime dependencies before rerunning on another computer.
Original metadata exporter/build helpers are repository tools; generated content
is already included, so Claude need not run database connections or install products.

Exported `metadata/actual_get_ddl.sql` is **reference only**. It includes CREATE OR
REPLACE statements and must not be executed as part of documentation review.
`verification.sql` is read-only, and the Worksheet context should be EFNS_DEV /
EFNS_DEV_WH with an authorized role. ACCOUNTADMIN is for metadata in the saved
evidence, not proof of ordinary application authorization.
