# Production PDF polish — 2026-11-13

Branch: `codex-production-pdf-polish-20261113`. Base: latest fetched `origin/main`, `abe11664f9b5dbcad7f054e576fe40574672c7ab`.

## Changes and scope

Only the Summary and Details PDF profiles change. Their existing structured Rounding summary is printed once, using the screen wording verbatim. The per-record `Rounding differences` appendix is omitted; any GUID in other source-note text is replaced by “source record”. The passed notes, full screen diagnostics, XLSX Notes sheet, CSV, report builders, filters and on-screen data remain unchanged. No new dependency, SQL, repository read, permission or audit change.

The width calculation measures complete header words, metadata words and every formatted numeric cell in bold, including totals. Housing reserves enough space for Conventional, Enrichable and Free Run. Production paragraphs cannot split long words. Extra space is distributed after these minimums fit. Week headings, Week Total, Grand Total, repeated headers, logo, parameters and Halifax footer remain.

Both profiles use landscape Letter (792 × 612 points), with 24-point side margins. Font selection is 8, 7.5, 7, then 6.5pt; the minimum is 6.5pt. Legal fallback is removed for these two reports. An unfit table produces a clear “Use CSV or XLSX” refusal rather than clipping/splitting numbers or silently switching paper.

## Reproducible synthetic full-year comparison

Identical inputs before/after: 1,300 synthetic stored rows across weeks 202601–202653; Conventional/Enrichable/Free Run; 1,300 stored-total differences of 1–5 dozens; fixed generation timestamp. No real producer data. Summary has 1,354 output rows including totals; Details has 1,301. Timing includes rendering and PDF text extraction, on this local machine.

| PDF | Before pages | After pages | Before seconds | After seconds | Paper / table font |
|---|---:|---:|---:|---:|---|
| Summary | 84 | 46 | 7.777 | 8.136 | Letter landscape / 6.5pt |
| Details | 83 | 44 | 8.471 | 6.911 | Letter landscape / 6.5pt |

The final footnote is: “1,300 source rows have a stored TOTAL that differs from the displayed component sum by rounding (largest difference 5 dozens).” It remains on the final table page in this fixture. First pages and the final Summary page were rendered with Poppler and inspected: complete codes/words, quantities, totals and footer; no diagnostic appendix. The staff PDF was not attached, so its exact new page count cannot be measured here; the user's reported 70-page run is not this synthetic benchmark.

## Validation

Full release suite (Python 3.12): **2,136 passed, 1 skipped, 0 failed**, 701.12 seconds. Full root suite (Python 3.11): **706 passed, 0 skipped, 0 failed**, 173.91 seconds. Focused Production/shared PDF suite: **233 passed**. Commands: `python -m pytest -q` from each directory, with separate worktree-local `--basetemp` paths. Targeted tests cover summary count/max, absent GUIDs/per-record lines, metadata and complete number widths, totals projection, unmodified DataFrame/CSV/XLSX including Notes, pagination, empty results, permissions/audit and Letter refusal. Other report PDF profiles retain their existing note handling.

## Shipped-file byte proof

Raw SHA-256 captured before edits for all 116 files expanded from `snowflake.yml` artifacts, including `streamlit_app.py`, `environment.yml` and `.streamlit/config.toml`. Exactly these two shipped files differ; the other 114 are byte-identical to the base. Tests, this document and the live integrity manifest are not shipped artifacts.

| Shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| `app/services/production_pdf.py` | `8c560723d97cf3d2e22e6901e226367c6958ffee5f803494d41a86018fafb498` | `f8d3543277fe876e24178e239402808f17f366aee47c3f09f23534f19cbc9014` |
| `app/services/report_pdf.py` | `09e38bb5dc62a626f30983294eb652189fc3b15c3f99206b962ce724e761d0f4` | `ce7f767971574fa403a7ac7b926a270bfccd63b601d953b0c43a698faf4191e7` |

The live `DELIVERY_RUNTIME_DIFF_20261030.json` is regenerated using LF-normalized final bytes for all **104** candidate hash entries, preserving the main branch's entries. No historical manifest is rewritten. No real data files added; no Snowflake access, deployment or PR.
