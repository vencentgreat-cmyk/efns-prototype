# Repository tidy audit — 2026-11-11

Branch: `codex-repo-tidy-20261111`; base `origin/main` at `ed07dda9ca380ca378e94cfb91dc5f5b0be3ea88`. Separate worktree: `.local/repo-tidy-worktree`.

**Audit written and committed as `b4b3699` before any tracked file was moved.** Only the SAFE moves below are authorized for this pass. No code/comment/docstring cleanup, configuration changes, Snowflake access or deployment. No existing data fixture/export will be moved, copied, added or deleted.

## Decision summary

- SAFE: archive 8 dated delivery/status Markdown reports (71,983 bytes before relocation). No deletion proposed.
- NEEDS-REVIEW: retain the root legacy app because current CI, root entrypoint, tests and deployment packaging still use it.
- KEEP: all manifest/test-referenced reports, README/deployment guidance, current reference documents and all shipped files.
- No one-off script meets the strict safe-move threshold in this pass: unreferenced candidates have location-sensitive or historical deployment/evidence dependencies, and protected design-document contents are outside the reference scan. They remain NEEDS-REVIEW rather than being moved on incomplete evidence.
- Two relative Markdown destinations in the archived HANDOVER draft will be retargeted to the same unchanged SQL/confirmation files, so moving it does not break its links. No prose or code is changed.

## Scope and reference evidence

Inventory uses tracked paths from `git ls-files -z` and filesystem byte sizes. Reference checks use case-insensitive fixed basename matching (and Python/JS stem matching for imports) across tracked code, tests, CI, scripts, docs, configuration and manifests. Self-references are excluded. Ambiguous same-basename hits are retained conservatively. Binary/data contents are not searched. Protected design directories are measured only; their contents were not inspected. Therefore an empty reference result is scoped, not proof about those excluded deliverables.

Initial `rg` checks included:

```text
rg -n "from app|app/Home.py|streamlit_app.py|scripts/" tests .github/workflows/tests.yml streamlit_app.py
rg -n "DELIVERY_REPORT|OVERNIGHT_REPORT|HANDOVER_DRAFT|HISTORY_VIEW_FIX|quota_flock_review|quota_rules_confirmation|docs/(codex_reports|audit|handoff)" tests releases/employee_trial_2026_10_29/tests scripts .github
rg -n "account_relationship_supplement_v1|eims_migration_mapping_v2.json|eims_migration_mapping.json" app data tests config scripts .github releases/employee_trial_2026_10_29/app releases/employee_trial_2026_10_29/data releases/employee_trial_2026_10_29/tests releases/employee_trial_2026_10_29/snowflake.yml
```

CI `.github/workflows/tests.yml:19` runs `python -m pytest -v` from the root; `pytest.ini:2` selects root `tests`, and `pytest.ini:3` excludes `releases`. Root `streamlit_app.py:15` runs root `app/Home.py`. Examples: `tests/auth_support.py:8` imports root app auth; `tests/test_company_deployment.py:11` imports packaging; `scripts/prepare_company_deployment.py:190` expands root deployment artifacts. These prevent deleting root `app/`.

## A. Root legacy app

| Directory | Files | Bytes | Verdict | Evidence |
| --- | ---: | ---: | --- | --- |
| `app/` | 40 | 375,160 | NEEDS-REVIEW | Root entrypoint, root tests, CI and packaging still use this tree. |
| `releases/employee_trial_2026_10_29/app/` | 61 | 911,439 | KEEP | Current release; shipped artifact freeze. |

The two app trees are not interchangeable: 40 matching relative files, 17 byte-identical and 23 different; 21 release-only files. Nothing under either app tree will change.

## B. Reports and root documentation

All rows below show pre-move byte sizes. A reference is `path:line` plus its source category; test/manifest matches are explicitly identified. No protected-directory contents are listed.

| Path before move | Bytes | Verdict | Evidence / action |
| --- | ---: | --- | --- |
| `docs/ASSUMPTIONS_AND_GAPS.md` | 7,472 | KEEP | Retain in place. docs: 1. `README.md:114` (docs) |
| `docs/AS_IS_MODEL.md` | 3,401 | KEEP | Retain in place. docs: 1. `README.md:111` (docs) |
| `docs/AUTHENTICATION.md` | 2,831 | KEEP | Retain in place. docs: 1. `README.md:190` (docs) |
| `docs/BUSINESS_RULES.md` | 5,953 | KEEP | Retain in place. docs: 1; scripts: 1. `README.md:112` (docs); `scripts/build_design_handoff.py:261` (scripts) |
| `docs/CLAUDE_REVIEW_GUIDE.md` | 15,062 | KEEP | Retain in place. docs: 3. `README.md:10` (docs); `releases/employee_trial_2026_10_29/README.md:5` (docs); `sample_data/README.md:5` (docs) |
| `docs/CONNECTION_ARCHITECTURE.md` | 3,399 | KEEP | Retain in place. docs: 1. `README.md:152` (docs) |
| `docs/DATAVERSE_DISCOVERY_CHECKLIST.md` | 5,814 | KEEP | Retain in place. docs: 2. `README.md:113` (docs); `README.md:250` (docs) |
| `docs/DATAVERSE_TO_TARGET_MAPPING.csv` | 4,455 | KEEP | Retain in place. docs: 2. `README.md:119` (docs); `docs/ASSUMPTIONS_AND_GAPS.md:110` (docs) |
| `docs/DATA_DICTIONARY.md` | 8,143 | KEEP | Retain in place. docs: 2. `README.md:116` (docs); `docs/TARGET_MODEL_DRAFT.md:8` (docs) |
| `docs/FACILITY_FLOCK_DESIGN.md` | 4,626 | KEEP | Retain in place. docs: 3. `docs/BUSINESS_RULES.md:102` (docs); `docs/DATA_DICTIONARY.md:54` (docs); `docs/TARGET_MODEL_DRAFT.md:12` (docs) |
| `docs/KNOWN_ISSUES.md` | 5,261 | KEEP | Retain in place. No scoped incoming references. |
| `docs/PROJECT_STATUS.md` | 4,586 | KEEP | Retain in place. No scoped incoming references. |
| `docs/REPORT_CENTER.md` | 8,781 | KEEP | Retain in place. docs: 2. `README.md:170` (docs); `docs/ASSUMPTIONS_AND_GAPS.md:64` (docs) |
| `docs/SNOWFLAKE_COMPATIBILITY.md` | 4,325 | KEEP | Retain in place. No scoped incoming references. |
| `docs/SNOWFLAKE_DEPLOYMENT.md` | 10,493 | KEEP | Retain in place. docs: 1. `README.md:204` (docs) |
| `docs/SNOWFLAKE_SMOKE_TEST.md` | 8,112 | KEEP | Retain in place. docs: 1. `docs/SNOWFLAKE_DEPLOYMENT.md:113` (docs) |
| `docs/TARGET_MODEL_DRAFT.md` | 1,853 | KEEP | Retain in place. docs: 1. `README.md:115` (docs) |
| `docs/eims_historical_corrections.md` | 5,496 | KEEP | Retain in place. docs: 1. `docs/historical_manual_corrections.md:201` (docs) |
| `docs/eims_metadata_meeting_checklist.md` | 913 | KEEP | Retain in place. docs: 1. `README.md:117` (docs) |
| `docs/eims_source_identity.md` | 2,644 | KEEP | Retain in place. code/config: 2. `releases/employee_trial_2026_10_29/sql/14_EIMS_Source_Identity.sql:3` (code/config); `sql/14_EIMS_Source_Identity.sql:3` (code/config) |
| `docs/eims_v3_dev_deployment.md` | 2,182 | KEEP | Retain in place. No scoped incoming references. |
| `docs/facility_flock_erd.mmd` | 1,241 | KEEP | Retain in place. docs: 1. `docs/FACILITY_FLOCK_DESIGN.md:12` (docs) |
| `docs/historical_manual_corrections.md` | 14,440 | KEEP | Retain in place. docs: 1. `docs/eims_historical_corrections.md:103` (docs) |
| `docs/light_theme_20261027.md` | 8,545 | SAFE | Move to `docs/archive/light_theme_20261027.md`. No scoped incoming references. |
| `docs/source_to_target_mapping_template.csv` | 110 | KEEP | Retain in place. docs: 1. `README.md:118` (docs) |
| `docs/v6_consistency_2026-10-15/Dictionary_Semantics_Delta.csv` | 2,801 | KEEP | Retain design/evidence deliverable; report only. No scoped incoming references. |
| `docs/v6_consistency_2026-10-15/Implementation_File_Manifest.json` | 4,912 | KEEP | Retain design/evidence deliverable; report only. No scoped incoming references. |
| `docs/v6_consistency_2026-10-15/Relationship_Check_Coverage.md` | 5,891 | KEEP | Retain design/evidence deliverable; report only. No scoped incoming references. |
| `docs/v6_consistency_2026-10-15/Validation_Results.json` | 1,308 | KEEP | Retain design/evidence deliverable; report only. No scoped incoming references. |
| `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_20261030.md` | 13,283 | SAFE | Move to `releases/employee_trial_2026_10_29/docs/archive/DELIVERY_REPORT_20261030.md`. No scoped incoming references. |
| `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R2_20261030.md` | 9,088 | SAFE | Move to `releases/employee_trial_2026_10_29/docs/archive/DELIVERY_REPORT_R2_20261030.md`. No scoped incoming references. |
| `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R3_20261030.md` | 9,498 | SAFE | Move to `releases/employee_trial_2026_10_29/docs/archive/DELIVERY_REPORT_R3_20261030.md`. No scoped incoming references. |
| `releases/employee_trial_2026_10_29/docs/DEPLOYMENT_CHECKLIST_20261030.md` | 12,593 | KEEP | Retain in place. docs: 4. `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_20261030.md:49` (docs); `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_20261030.md:89` (docs); `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_20261030.md:195` (docs); `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R2_20261030.md:23` (docs) |
| `releases/employee_trial_2026_10_29/docs/HANDOVER_DRAFT_20261030.md` | 13,915 | SAFE | Move to `releases/employee_trial_2026_10_29/docs/archive/HANDOVER_DRAFT_20261030.md`. docs: 5. `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_20261030.md:43` (docs); `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_20261030.md:197` (docs); `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R2_20261030.md:23` (docs); `releases/employee_trial_2026_10_29/docs/OVERNIGHT_REPORT_20261030.md:79` (docs); further matches retained. |
| `releases/employee_trial_2026_10_29/docs/HISTORY_VIEW_FIX_20261102.md` | 5,470 | SAFE | Move to `releases/employee_trial_2026_10_29/docs/archive/HISTORY_VIEW_FIX_20261102.md`. No scoped incoming references. |
| `releases/employee_trial_2026_10_29/docs/OVERNIGHT_REPORT_20261030.md` | 9,055 | SAFE | Move to `releases/employee_trial_2026_10_29/docs/archive/OVERNIGHT_REPORT_20261030.md`. No scoped incoming references. |
| `releases/employee_trial_2026_10_29/docs/audit/repro/test_staff_audit.py` | 8,484 | NEEDS-REVIEW | Executable audit reproducer, not a status report; preserve its location. docs: 2. `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R3_20261030.md:72` (docs); `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R3_20261030.md:73` (docs) |
| `releases/employee_trial_2026_10_29/docs/audit/repro/test_staff_audit_r3_locators.py` | 8,514 | NEEDS-REVIEW | Executable audit reproducer, not a status report; preserve its location. docs: 1. `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R3_20261030.md:73` (docs) |
| `releases/employee_trial_2026_10_29/docs/codex_reports/FLOCK_DATE_DEFAULTS_20261111.md` | 3,285 | KEEP | Retain in place. manifest: 1. `releases/employee_trial_2026_10_29/DELIVERY_RUNTIME_DIFF_20261030.json:587` (manifest) |
| `releases/employee_trial_2026_10_29/docs/codex_reports/PRINTABLE_FORMS_20261109.md` | 6,244 | KEEP | Retain in place. manifest: 1. `releases/employee_trial_2026_10_29/DELIVERY_RUNTIME_DIFF_20261030.json:362` (manifest) |
| `releases/employee_trial_2026_10_29/docs/codex_reports/PRODUCERS_OVER_QUOTA_20261110.md` | 1,637 | KEEP | Retain in place. manifest: 1. `releases/employee_trial_2026_10_29/DELIVERY_RUNTIME_DIFF_20261030.json:485` (manifest) |
| `releases/employee_trial_2026_10_29/docs/codex_reports/PRODUCERS_OVER_QUOTA_PARITY_20261110.md` | 11,460 | KEEP | Retain in place. docs: 1; manifest: 1. `releases/employee_trial_2026_10_29/DELIVERY_RUNTIME_DIFF_20261030.json:561` (manifest); `releases/employee_trial_2026_10_29/docs/codex_reports/PRODUCERS_OVER_QUOTA_20261110.md:9` (docs) |
| `releases/employee_trial_2026_10_29/docs/codex_reports/REPORT_PDF_EXPORT_20261109.md` | 8,685 | KEEP | Retain in place. manifest: 1. `releases/employee_trial_2026_10_29/DELIVERY_RUNTIME_DIFF_20261030.json:411` (manifest) |
| `releases/employee_trial_2026_10_29/docs/codex_reports/SARA_FEEDBACK_FIXES_20261110.md` | 8,590 | KEEP | Retain in place. manifest: 1. `releases/employee_trial_2026_10_29/DELIVERY_RUNTIME_DIFF_20261030.json:523` (manifest) |
| `releases/employee_trial_2026_10_29/docs/codex_reports/TRIAL_READINESS_STATIC_SCAN_20261109.md` | 3,377 | KEEP | Retain in place. manifest: 1; tests: 1. `releases/employee_trial_2026_10_29/DELIVERY_RUNTIME_DIFF_20261030.json:348` (manifest); `releases/employee_trial_2026_10_29/tests/test_report_smoke.py:257` (tests) |
| `releases/employee_trial_2026_10_29/docs/handoff/TRIAL_BUILD_20261104.md` | 3,129 | SAFE | Move to `releases/employee_trial_2026_10_29/docs/archive/handoff/TRIAL_BUILD_20261104.md`. No scoped incoming references. |
| `releases/employee_trial_2026_10_29/docs/quota_flock_review_20261029.md` | 9,241 | KEEP | Retain in place. docs: 2; manifest: 1. `releases/employee_trial_2026_10_29/QUOTA_FLOCK_PATCH_MANIFEST.json:71` (manifest); `releases/employee_trial_2026_10_29/README.md:3` (docs); `releases/employee_trial_2026_10_29/docs/OVERNIGHT_REPORT_20261030.md:35` (docs) |
| `releases/employee_trial_2026_10_29/docs/quota_rules_confirmation_20261029.md` | 3,308 | KEEP | Retain in place. docs: 3; manifest: 1. `releases/employee_trial_2026_10_29/QUOTA_FLOCK_PATCH_MANIFEST.json:75` (manifest); `releases/employee_trial_2026_10_29/docs/HANDOVER_DRAFT_20261030.md:123` (docs); `releases/employee_trial_2026_10_29/docs/OVERNIGHT_REPORT_20261030.md:35` (docs); `releases/employee_trial_2026_10_29/docs/quota_flock_review_20261029.md:105` (docs) |

HANDOVER has incoming references only from the delivery/overnight reports moved with it. OVERNIGHT’s relative link to HANDOVER remains valid. HANDOVER’s two outgoing links need the documented relative-path adjustment. Deployment checklist stays in place. Quota review/confirmation are pinned by `QUOTA_FLOCK_PATCH_MANIFEST.json:71,75`; codex reports are pinned by the runtime-diff manifest, including the smoke-test-referenced trial static scan.

Protected deliverables — **size only**, unchanged:

| Directory | Tracked files | Total bytes | Verdict |
| --- | ---: | ---: | --- |
| `docs/database_manual_2026-10-13/` | 303 | 45,781,098 | KEEP — protected |
| `docs/identity_history_2026-10-14/` | 24 | 3,562,149 | KEEP — protected |

## C. Root scripts

Prefix candidates: `prepare_*`, `verify_*`, `apply_*`, `finalize_*`, `recover_*`. No operational CLI script is run, edited or deleted. The required offline suites may import and test packaging helpers. Reference-bearing scripts stay; location-sensitive scripts and scripts that generate/validate historical evidence remain NEEDS-REVIEW. The protected-document exclusion prevents a repository-wide claim that an apparently unreferenced script has no documentation consumers.

| Script | Bytes | Verdict | Reference evidence / reason |
| --- | ---: | --- | --- |
| `scripts/apply_continuity_evidence.py` | 5,535 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/apply_design_repairs.py` | 5,192 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/build_continuity_handoff.py` | 17,850 | NEEDS-REVIEW | No scoped incoming references; retain historical utility pending dependency/protected-reference review. |
| `scripts/build_design_handoff.py` | 24,256 | KEEP | Referenced utility or outside the named one-off prefixes. scripts: 1. `scripts/build_continuity_handoff.py:9` (scripts) |
| `scripts/check_recovered_workbook.py` | 1,670 | NEEDS-REVIEW | No scoped incoming references; retain historical utility pending dependency/protected-reference review. |
| `scripts/check_snowflake_readiness.py` | 18,802 | KEEP | Referenced utility or outside the named one-off prefixes. docs: 16; tests: 2. `docs/CLAUDE_REVIEW_GUIDE.md:82` (docs); `docs/SNOWFLAKE_COMPATIBILITY.md:69` (docs); `docs/SNOWFLAKE_DEPLOYMENT.md:73` (docs); `docs/historical_manual_corrections.md:115` (docs); further matches retained. |
| `scripts/company_application_deployment.py` | 9,117 | KEEP | Referenced utility or outside the named one-off prefixes. docs: 1; scripts: 2; tests: 1. `docs/historical_manual_corrections.md:197` (docs); `scripts/company_connection_check.py:102` (scripts); `scripts/company_connection_check.py:104` (scripts); `tests/test_company_application_deployment.py:5` (tests) |
| `scripts/company_connection_check.py` | 9,361 | KEEP | Referenced utility or outside the named one-off prefixes. scripts: 1; tests: 2. `scripts/company_database_deployment.py:3` (scripts); `tests/test_company_deployment.py:10` (tests); `tests/test_company_deployment.py:129` (tests) |
| `scripts/company_database_deployment.py` | 14,046 | KEEP | Referenced utility or outside the named one-off prefixes. docs: 1; scripts: 4; tests: 3. `docs/historical_manual_corrections.md:196` (docs); `releases/employee_trial_2026_10_29/tests/test_manual_historical_corrections.py:394` (tests); `scripts/company_application_deployment.py:16` (scripts); `scripts/company_application_deployment.py:18` (scripts); further matches retained. |
| `scripts/company_recovery_preview.py` | 6,091 | NEEDS-REVIEW | No scoped incoming references; retain historical utility pending dependency/protected-reference review. |
| `scripts/continuity_dev_evidence.py` | 2,126 | NEEDS-REVIEW | No scoped incoming references; retain historical utility pending dependency/protected-reference review. |
| `scripts/export_design_evidence.py` | 7,184 | NEEDS-REVIEW | No scoped incoming references; retain historical utility pending dependency/protected-reference review. |
| `scripts/finalize_continuity_handoff.py` | 5,190 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/finalize_design_handoff.py` | 5,422 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/generate_fake_eims_export.py` | 14,186 | KEEP | Referenced utility or outside the named one-off prefixes. docs: 3; tests: 5. `README.md:175` (docs); `docs/SNOWFLAKE_SMOKE_TEST.md:112` (docs); `releases/employee_trial_2026_10_29/tests/test_eims_migration.py:26` (tests); `releases/employee_trial_2026_10_29/tests/test_eims_migration.py:279` (tests); further matches retained. |
| `scripts/prepare_company_deployment.py` | 13,361 | KEEP | Referenced utility or outside the named one-off prefixes. docs: 1; scripts: 2; tests: 4. `docs/historical_manual_corrections.md:195` (docs); `releases/employee_trial_2026_10_29/tests/test_manual_historical_corrections.py:393` (tests); `scripts/company_database_deployment.py:18` (scripts); `scripts/company_database_deployment.py:20` (scripts); further matches retained. |
| `scripts/prepare_company_snowsight.py` | 4,726 | KEEP | Referenced utility or outside the named one-off prefixes. tests: 2. `tests/test_company_application_deployment.py:57` (tests); `tests/test_company_deployment.py:213` (tests) |
| `scripts/prepare_continuity_deployment.py` | 1,945 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/prepare_design_deployment.py` | 4,273 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/production_match_preview.py` | 1,778 | NEEDS-REVIEW | No scoped incoming references; retain historical utility pending dependency/protected-reference review. |
| `scripts/recover_omitted_workbook_rows.py` | 3,140 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/render_continuity_erd.mjs` | 3,384 | NEEDS-REVIEW | No scoped incoming references; retain historical utility pending dependency/protected-reference review. |
| `scripts/run_dev_migration_smoke.py` | 3,351 | NEEDS-REVIEW | No scoped incoming references; retain historical utility pending dependency/protected-reference review. |
| `scripts/verify_continuity_dev.py` | 6,956 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/verify_deployed_design_repairs.py` | 11,541 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/verify_deployed_report_filters.py` | 5,703 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/verify_design_permissions.py` | 2,402 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/verify_preserved_historical_values.py` | 2,764 | NEEDS-REVIEW | No scoped incoming references; historical deployment/evidence dependencies or location sensitivity; protected-document references not inspected. No scoped incoming references. |
| `scripts/verify_snowpark_null_binding.py` | 4,519 | KEEP | Referenced utility or outside the named one-off prefixes. docs: 1. `docs/SNOWFLAKE_SMOKE_TEST.md:104` (docs) |

Examples: `scripts/finalize_continuity_handoff.py:8` targets a protected deliverable; `scripts/prepare_design_deployment.py:13` derives the repository root from its current file location; `scripts/apply_design_repairs.py:46` locates SQL relative to its current parent. Archiving these without code changes can alter their behavior if rerun. No script archive move is justified on this evidence.

## D. Shipped duplicate/unused configuration — report only

| File | Bytes | Verdict | Evidence |
| --- | ---: | --- | --- |
| `releases/employee_trial_2026_10_29/config/eims_migration_mapping.json` | 12,623 | KEEP | Both files have exactly the same raw SHA-256: `1b8a5bc36a1bf1c7773781c7fd43153db026a8b8f0eef1000960df08ea348eb9`. Shipped separately; migration uses the v2 path (`data/migration.py:27`), and readiness tooling checks both filenames. |
| `releases/employee_trial_2026_10_29/config/eims_migration_mapping_v2.json` | 12,623 | KEEP | Both files have exactly the same raw SHA-256: `1b8a5bc36a1bf1c7773781c7fd43153db026a8b8f0eef1000960df08ea348eb9`. Shipped separately; migration uses the v2 path (`data/migration.py:27`), and readiness tooling checks both filenames. |
| `releases/employee_trial_2026_10_29/config/account_relationship_supplement_v1.json` | 548 | KEEP | Shipped by snowflake.yml:49–50; no filename/stem references in release app/data/tests. Retain; runtime usage cannot be disproved from filename search alone. |

No shipped config is removed, merged or edited, regardless of duplicate content.

## E. Non-runtime PNG/SVG/DOT/CSV/Excel files — size only

All existing files in these groups stay unchanged. Totals exclude shipped artifacts. Protected groups are aggregated without reading their contents. PDF fixtures are outside the requested extension set and remain untouched.

| Folder | Files | Bytes | Verdict |
| --- | ---: | ---: | --- |
| `docs` | 2 | 4,565 | KEEP — report only |
| `docs/database_manual_2026-10-13 (protected; size only)` | 277 | 39,566,770 | KEEP — report only |
| `docs/identity_history_2026-10-14 (protected; size only)` | 13 | 1,619,556 | KEEP — report only |
| `docs/v6_consistency_2026-10-15` | 1 | 2,801 | KEEP — report only |
| `releases/employee_trial_2026_10_29/tests/fixtures/flock_disposals` | 3 | 11,833 | KEEP — report only |
| `releases/employee_trial_2026_10_29/tests/fixtures/legacy_forms` | 1 | 13,267 | KEEP — report only |
| `releases/employee_trial_2026_10_29/tests/fixtures/legacy_reports` | 1 | 7,363 | KEEP — report only |
| `releases/employee_trial_2026_10_29/tests/fixtures/producers_over_quota` | 2 | 11,062 | KEEP — report only |
| `releases/employee_trial_2026_10_29/tests/fixtures/production_reports` | 4 | 164,813 | KEEP — report only |
| `sample_data` | 7 | 136,060 | KEEP — report only |
| `sample_data/fake_eims_export/clean` | 10 | 806,822 | KEEP — report only |
| `sample_data/fake_eims_export/edge_cases` | 10 | 9,915 | KEEP — report only |

Total in the listed extension set: **331 files, 42,354,827 bytes**. No real producer/flock exports are added.

## Safe move plan

| Original | Destination | Bytes before |
| --- | --- | ---: |
| `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_20261030.md` | `releases/employee_trial_2026_10_29/docs/archive/DELIVERY_REPORT_20261030.md` | 13,283 |
| `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R2_20261030.md` | `releases/employee_trial_2026_10_29/docs/archive/DELIVERY_REPORT_R2_20261030.md` | 9,088 |
| `releases/employee_trial_2026_10_29/docs/DELIVERY_REPORT_R3_20261030.md` | `releases/employee_trial_2026_10_29/docs/archive/DELIVERY_REPORT_R3_20261030.md` | 9,498 |
| `releases/employee_trial_2026_10_29/docs/OVERNIGHT_REPORT_20261030.md` | `releases/employee_trial_2026_10_29/docs/archive/OVERNIGHT_REPORT_20261030.md` | 9,055 |
| `releases/employee_trial_2026_10_29/docs/HANDOVER_DRAFT_20261030.md` | `releases/employee_trial_2026_10_29/docs/archive/HANDOVER_DRAFT_20261030.md` | 13,915 |
| `releases/employee_trial_2026_10_29/docs/HISTORY_VIEW_FIX_20261102.md` | `releases/employee_trial_2026_10_29/docs/archive/HISTORY_VIEW_FIX_20261102.md` | 5,470 |
| `releases/employee_trial_2026_10_29/docs/handoff/TRIAL_BUILD_20261104.md` | `releases/employee_trial_2026_10_29/docs/archive/handoff/TRIAL_BUILD_20261104.md` | 3,129 |
| `docs/light_theme_20261027.md` | `docs/archive/light_theme_20261027.md` | 8,545 |

Use `git mv`; keep content byte-identical except the two relative Markdown link destinations in HANDOVER. Add one short root `docs/README.md` index. Delete nothing. All referenced runtime/patch/baseline manifest paths stay in place. The candidate LF hashes will be regenerated from final files; immutable historical captured-source hashes will not be rewritten to describe current code.

## Validation and shipped-file proof

Before-tidy suites passed on the original code/file locations: release **1,980 passed, 1 skipped, 0 failed, 0 errors** (1,183.40 s); root **706 passed, 0 skipped, 0 failed, 0 errors** (232.21 s). After-tidy suites passed with exactly matching counts (table below). No tests have been updated.

The eight `git mv` operations are complete. Seven destinations retain exactly the original raw bytes. HANDOVER differs only in the two relative Markdown link destinations described above; reversing those two substitutions reproduces its original raw SHA-256. All original report text is retained.

`docs/README.md` is the only new index. No script, fixture, CSV/XLSX, runtime source, code comment/docstring, configuration or SQL changed. Protected deliverable directories have no Git changes. No deletion was performed.

Before snapshot: **113 files, 1,661,854 bytes**. Matches are the union of every artifact `src` glob in release `snowflake.yml`, plus the three explicitly named files, deduplicated by path. SHA-256 is over **raw bytes**, not LF-normalized bytes. The final comparison must have identical path sets and identical hashes, or the offending change is reverted.

| Shipped file (relative to release) | Bytes | Before raw SHA-256 | After raw SHA-256 | Result |
| --- | ---: | --- | --- | --- |
| `.streamlit/config.toml` | 439 | `d201803c6cce73748851884805aedc40ca3f4a732c69bf4ab7cba9792cacc362` | `d201803c6cce73748851884805aedc40ca3f4a732c69bf4ab7cba9792cacc362` | IDENTICAL |
| `app/__init__.py` | 43 | `a220443f03f8f390d40258d89f720dea2faddcb5b529fda79419a87f1c86a1e9` | `a220443f03f8f390d40258d89f720dea2faddcb5b529fda79419a87f1c86a1e9` | IDENTICAL |
| `app/assets/efns_logo.png` | 295,015 | `674ed2f97cef8249e6803749b9e6c2c7ef0874cc260ce1aef55447ed49d83b61` | `674ed2f97cef8249e6803749b9e6c2c7ef0874cc260ce1aef55447ed49d83b61` | IDENTICAL |
| `app/auth.py` | 8,845 | `9f7b9578cdf8d8bbda5c6bef795bbbc2cabe6ea21276b38b01288d177210d48e` | `9f7b9578cdf8d8bbda5c6bef795bbbc2cabe6ea21276b38b01288d177210d48e` | IDENTICAL |
| `app/Home.py` | 10,547 | `1b8660709ab948969ae90e0cd55eb656887d84a4ac6745f02d4f621f87268064` | `1b8660709ab948969ae90e0cd55eb656887d84a4ac6745f02d4f621f87268064` | IDENTICAL |
| `app/navigation.py` | 11,633 | `711e9624c9e5f47aae0c5a7ff980ca2216e5785c2442420f5adf7bda7769c321` | `711e9624c9e5f47aae0c5a7ff980ca2216e5785c2442420f5adf7bda7769c321` | IDENTICAL |
| `app/pages/10_Salmonella_Report.py` | 4,948 | `70c6e116971fe04e46b417263ed6eac8aed83d9805c92585abb4e43a24ebdc37` | `70c6e116971fe04e46b417263ed6eac8aed83d9805c92585abb4e43a24ebdc37` | IDENTICAL |
| `app/pages/11_Facilities.py` | 11,317 | `001e0bf62b2620daa71cb6451e7851d76a4b0d85a445fb27d643e5bc0fca4e7d` | `001e0bf62b2620daa71cb6451e7851d76a4b0d85a445fb27d643e5bc0fca4e7d` | IDENTICAL |
| `app/pages/12_System_Status.py` | 2,962 | `faf18dd03d3b74ec0908e813d734ec0fa734c97944aa471c7f2093df779cd049` | `faf18dd03d3b74ec0908e813d734ec0fa734c97944aa471c7f2093df779cd049` | IDENTICAL |
| `app/pages/13_Facility_Details.py` | 11,209 | `d5bc46aa869ebaa2195a2c04036325b6c400c4652126b234759190daa6c63faf` | `d5bc46aa869ebaa2195a2c04036325b6c400c4652126b234759190daa6c63faf` | IDENTICAL |
| `app/pages/14_Source_Data_Profiler.py` | 4,834 | `4a340a8561c8393e9397ce093f45c502ceb9798d12868e46b9cf5056e8c50c8a` | `4a340a8561c8393e9397ce093f45c502ceb9798d12868e46b9cf5056e8c50c8a` | IDENTICAL |
| `app/pages/15_User_Management.py` | 5,983 | `c2cf52bd570483dd21740bf0701379742929f5b6c678fa0ebfbc438da1d9b869` | `c2cf52bd570483dd21740bf0701379742929f5b6c678fa0ebfbc438da1d9b869` | IDENTICAL |
| `app/pages/16_Audit_Log.py` | 2,516 | `f5bc9931958fd5030837831b4fb635fb1b4be4c05d6ea604bd398189eb5613ec` | `f5bc9931958fd5030837831b4fb635fb1b4be4c05d6ea604bd398189eb5613ec` | IDENTICAL |
| `app/pages/17_Migration_Import.py` | 23,131 | `e323ae8d3b7019333a51375dec9e7bcb1f41394f0a96144af651476d8c61b459` | `e323ae8d3b7019333a51375dec9e7bcb1f41394f0a96144af651476d8c61b459` | IDENTICAL |
| `app/pages/18_Farm_Locations.py` | 10,808 | `9b05d80c9e134d1906b19ee85571734566252141555406de5665659446b0681e` | `9b05d80c9e134d1906b19ee85571734566252141555406de5665659446b0681e` | IDENTICAL |
| `app/pages/19_Daily_Flock_Quota_Import.py` | 12,022 | `fc5625bed420ec6831b0c2d1ba4bb46b53f3ae1ad9636876cac0dbd707c457e0` | `fc5625bed420ec6831b0c2d1ba4bb46b53f3ae1ad9636876cac0dbd707c457e0` | IDENTICAL |
| `app/pages/1_Production_Import.py` | 9,050 | `2e53787bca9bf25f6cf52c8945a8273026de45254f60825c4eb02c94cbc275db` | `2e53787bca9bf25f6cf52c8945a8273026de45254f60825c4eb02c94cbc275db` | IDENTICAL |
| `app/pages/20_EIMS_Reference_Data.py` | 2,203 | `5c55d5dcd07a76d558a078c97f805a4b88c645a7a4abf9880594d44e7ac9e918` | `5c55d5dcd07a76d558a078c97f805a4b88c645a7a4abf9880594d44e7ac9e918` | IDENTICAL |
| `app/pages/21_Record_History.py` | 18,546 | `0ffbb85891f298bac1345079a1a912102774258b5e17bb5cb8c9b31b6dc041f0` | `0ffbb85891f298bac1345079a1a912102774258b5e17bb5cb8c9b31b6dc041f0` | IDENTICAL |
| `app/pages/2_Production_Data.py` | 8,331 | `8fcf219d55d8ef283a785edae838b0a0e03f7891e110451bc57d09474a7db1e6` | `8fcf219d55d8ef283a785edae838b0a0e03f7891e110451bc57d09474a7db1e6` | IDENTICAL |
| `app/pages/3_Accounts_Facilities_Flocks.py` | 26,136 | `3405c92c03b89f19595ce9563aa7fdd93fe9af0284bbb16f6225817a14842523` | `3405c92c03b89f19595ce9563aa7fdd93fe9af0284bbb16f6225817a14842523` | IDENTICAL |
| `app/pages/4_Reports.py` | 57,394 | `ede87b9cd26fddb5608b883b521fcbaf948d0609ee512c85baba98dc2af108b4` | `ede87b9cd26fddb5608b883b521fcbaf948d0609ee512c85baba98dc2af108b4` | IDENTICAL |
| `app/pages/5_Flocks.py` | 22,296 | `d0931c039d4838d43c66f629759327666a52d291d9190dc4a0f9838ca18692aa` | `d0931c039d4838d43c66f629759327666a52d291d9190dc4a0f9838ca18692aa` | IDENTICAL |
| `app/pages/6_Flock_Transactions.py` | 13,609 | `04838cb9aa707bf1eb7c16b574da614680c6e979a1871a62eb5d8c8bec81e072` | `04838cb9aa707bf1eb7c16b574da614680c6e979a1871a62eb5d8c8bec81e072` | IDENTICAL |
| `app/pages/7_Quota_Registrations.py` | 13,490 | `fc652ac7fae2000bd2ba44fc8baa22e91b0f1626b226c99e8bf5e61acc43b9b1` | `fc652ac7fae2000bd2ba44fc8baa22e91b0f1626b226c99e8bf5e61acc43b9b1` | IDENTICAL |
| `app/pages/8_Quota_Transactions.py` | 20,597 | `ccc3808a8afb35fba9ee6a9915c54059af5239035db35b56eaac3c6bab022af3` | `ccc3808a8afb35fba9ee6a9915c54059af5239035db35b56eaac3c6bab022af3` | IDENTICAL |
| `app/pages/9_Salmonella_Tests.py` | 13,955 | `58697e1aea9a173900f19d76947d4a670de1e8fcbb73d5fac410d7d0478c7cd2` | `58697e1aea9a173900f19d76947d4a670de1e8fcbb73d5fac410d7d0478c7cd2` | IDENTICAL |
| `app/runtime.py` | 2,236 | `066a03769b20a1c152ae8bb85a3b5df0437ba6f5a02416031f936121a1806304` | `066a03769b20a1c152ae8bb85a3b5df0437ba6f5a02416031f936121a1806304` | IDENTICAL |
| `app/security.py` | 23,500 | `e130c85e92307fce54553ca2b8a122a3dd021eefe2275791c3fa6b8e6669b045` | `e130c85e92307fce54553ca2b8a122a3dd021eefe2275791c3fa6b8e6669b045` | IDENTICAL |
| `app/services/__init__.py` | 55 | `010341e8ef26d5b500c53b0a06d00fcafefc583422451a91a8cf7c92eb93463a` | `010341e8ef26d5b500c53b0a06d00fcafefc583422451a91a8cf7c92eb93463a` | IDENTICAL |
| `app/services/authorized_repository.py` | 15,746 | `fee29011c309c5563bc5ae5fd098900075fcd21dfc20daa0162303f712a52d76` | `fee29011c309c5563bc5ae5fd098900075fcd21dfc20daa0162303f712a52d76` | IDENTICAL |
| `app/services/entry_fields.py` | 1,526 | `56ce47b0d01ccff79794ec527f7f74bcd7ea6b51f43c785d2f44561b83bb9e3b` | `56ce47b0d01ccff79794ec527f7f74bcd7ea6b51f43c785d2f44561b83bb9e3b` | IDENTICAL |
| `app/services/export.py` | 674 | `3b70a3eab08668aadbaa06d18a74ac5ed6cd1b70a4ae38dc10006085ceaee1d6` | `3b70a3eab08668aadbaa06d18a74ac5ed6cd1b70a4ae38dc10006085ceaee1d6` | IDENTICAL |
| `app/services/facility_source_description.py` | 1,516 | `27b5a0ef8beaa365bb5d24b126bdc0f99b4960f87a2cc0afbf2af08f09b87e18` | `27b5a0ef8beaa365bb5d24b126bdc0f99b4960f87a2cc0afbf2af08f09b87e18` | IDENTICAL |
| `app/services/flock_age_report.py` | 7,016 | `542aba673bacfc56cb75fee4625b04191f57b48538693ef3bf6f81c84caa2453` | `542aba673bacfc56cb75fee4625b04191f57b48538693ef3bf6f81c84caa2453` | IDENTICAL |
| `app/services/flock_current_report.py` | 7,479 | `be6d68d90a61d0eaebc6ef29597fa2c3a2dae6daa545bdc3f44eebad2e8dc4e8` | `be6d68d90a61d0eaebc6ef29597fa2c3a2dae6daa545bdc3f44eebad2e8dc4e8` | IDENTICAL |
| `app/services/flock_date_defaults.py` | 1,672 | `f834541f4718633e41e66642625b9df42fe672cc3ecf106a92b00243496a6096` | `f834541f4718633e41e66642625b9df42fe672cc3ecf106a92b00243496a6096` | IDENTICAL |
| `app/services/flock_date_repair_workspace.py` | 7,271 | `1aa98081b0ced36075d2b8a6654c3f546c446061fca27b454f3aba5e5e236e9e` | `1aa98081b0ced36075d2b8a6654c3f546c446061fca27b454f3aba5e5e236e9e` | IDENTICAL |
| `app/services/flock_reports.py` | 18,596 | `b297542a7e46bd652e84b2d61b3c0638e3f97c21f6222d4d43aef99bc56c8b96` | `b297542a7e46bd652e84b2d61b3c0638e3f97c21f6222d4d43aef99bc56c8b96` | IDENTICAL |
| `app/services/flock_supplement_workspace.py` | 3,733 | `01b544e53598d2e280ee4f9037c698ecbe0e7d5d209a9479712a49fde4ca7823` | `01b544e53598d2e280ee4f9037c698ecbe0e7d5d209a9479712a49fde4ca7823` | IDENTICAL |
| `app/services/form_safety.py` | 5,261 | `e6531362430f173feef227b799c90d21c43070a7834982a30c20aac7cc780d03` | `e6531362430f173feef227b799c90d21c43070a7834982a30c20aac7cc780d03` | IDENTICAL |
| `app/services/historical_correction_workspace.py` | 6,063 | `326c94d11ccc52cce12f464eb6723b62340f82ed3fca1dcb22a78ccee9afbc8e` | `326c94d11ccc52cce12f464eb6723b62340f82ed3fca1dcb22a78ccee9afbc8e` | IDENTICAL |
| `app/services/printable_form_text.py` | 2,461 | `9f23cb725930247bb08ac8ecb394f47eba5714ea823e4f8e5d5e18ebed216621` | `9f23cb725930247bb08ac8ecb394f47eba5714ea823e4f8e5d5e18ebed216621` | IDENTICAL |
| `app/services/printable_form_ui.py` | 6,230 | `8ebf9895c2d54e463e2328fca8879d42181e0500891642e725a99806fa3068fa` | `8ebf9895c2d54e463e2328fca8879d42181e0500891642e725a99806fa3068fa` | IDENTICAL |
| `app/services/printable_forms.py` | 21,752 | `4e7dab6ebabc72f4566af23439410a7da085bba6b295e6926781c51f227411eb` | `4e7dab6ebabc72f4566af23439410a7da085bba6b295e6926781c51f227411eb` | IDENTICAL |
| `app/services/producers_over_quota_report.py` | 7,500 | `f006f59d204ec40e11a69a5bdf73786c61ede820ff7e3c551abd3dc53783a607` | `f006f59d204ec40e11a69a5bdf73786c61ede820ff7e3c551abd3dc53783a607` | IDENTICAL |
| `app/services/production_data_display.py` | 2,741 | `0853091695abcb82ecc4d0e8841ec5e4731694c5e9cb94a273972f80b1e43504` | `0853091695abcb82ecc4d0e8841ec5e4731694c5e9cb94a273972f80b1e43504` | IDENTICAL |
| `app/services/production_reports.py` | 15,607 | `9de92ff6852313991970494f113281e6489cb7018be741cf4815060c5256a71e` | `9de92ff6852313991970494f113281e6489cb7018be741cf4815060c5256a71e` | IDENTICAL |
| `app/services/profiling_export.py` | 2,713 | `e07b1ac9903007d58b69992827364dd94e7a8a6d741747a5552eaaa21fb22642` | `e07b1ac9903007d58b69992827364dd94e7a8a6d741747a5552eaaa21fb22642` | IDENTICAL |
| `app/services/quota_reports.py` | 11,218 | `899d73a0a0f0e56d1c0f0f733dd8c7a0b52c7537765da62baa08cf0a11401971` | `899d73a0a0f0e56d1c0f0f733dd8c7a0b52c7537765da62baa08cf0a11401971` | IDENTICAL |
| `app/services/quota_state.py` | 2,031 | `2a9f9a6ce50ac43eb8c36049bca2ea36dbe5b0c9692dce404da71276114bd4fd` | `2a9f9a6ce50ac43eb8c36049bca2ea36dbe5b0c9692dce404da71276114bd4fd` | IDENTICAL |
| `app/services/quota_usage.py` | 10,987 | `49b9ecad80315a49aaf72b1ca7ca84636612e0f4d3a944ef63962eba98af8248` | `49b9ecad80315a49aaf72b1ca7ca84636612e0f4d3a944ef63962eba98af8248` | IDENTICAL |
| `app/services/report_builder.py` | 15,573 | `492f5bf18bb19506b6fb6e6f7fe11082fb4a0107c30a00ee4130dcf373787473` | `492f5bf18bb19506b6fb6e6f7fe11082fb4a0107c30a00ee4130dcf373787473` | IDENTICAL |
| `app/services/report_center.py` | 34,727 | `e8f4383b0032095591ed254f18c104731b247d327820a211baff314a0cdfcd29` | `e8f4383b0032095591ed254f18c104731b247d327820a211baff314a0cdfcd29` | IDENTICAL |
| `app/services/report_pdf.py` | 16,875 | `73284c37073feac1572f31d1ad1c193476a63911967ab9965e4bf73aba4ed1a7` | `73284c37073feac1572f31d1ad1c193476a63911967ab9965e4bf73aba4ed1a7` | IDENTICAL |
| `app/services/report_pdf_ui.py` | 4,271 | `ec40552b9f7c69fc883764c08e80f4a336830b23c50b3b4f55944ca108c99830` | `ec40552b9f7c69fc883764c08e80f4a336830b23c50b3b4f55944ca108c99830` | IDENTICAL |
| `app/services/report_relationships.py` | 3,859 | `18ff5b80a5e341333d65f19108af91f346a0ef14bc0115ae67368fe0e5081ed8` | `18ff5b80a5e341333d65f19108af91f346a0ef14bc0115ae67368fe0e5081ed8` | IDENTICAL |
| `app/services/revision_history.py` | 6,131 | `35e3ebc470f18c672652018c76eaeee50349f4add386dee7092191776468e30e` | `35e3ebc470f18c672652018c76eaeee50349f4add386dee7092191776468e30e` | IDENTICAL |
| `app/services/salmonella_reporting.py` | 2,085 | `eca03dcfb8d85ff5db981d0961d04c3b9751180f838ffee18170e6464870aaab` | `eca03dcfb8d85ff5db981d0961d04c3b9751180f838ffee18170e6464870aaab` | IDENTICAL |
| `app/services/selector_options.py` | 2,352 | `bd2176288e5486bf10a13738b95fff61bdc38af323b47ff25d5cdd95aa8915f4` | `bd2176288e5486bf10a13738b95fff61bdc38af323b47ff25d5cdd95aa8915f4` | IDENTICAL |
| `app/snowflake_security.py` | 12,603 | `56a8c290f21c1e6cb9cc4437f52b5fed6bf7beba67dc0f570d510100943f048e` | `56a8c290f21c1e6cb9cc4437f52b5fed6bf7beba67dc0f570d510100943f048e` | IDENTICAL |
| `app/ui.py` | 5,959 | `7c90f2848ee009b80ab03c98691471c43fc0597fb3472c46a172bbc715843ace` | `7c90f2848ee009b80ab03c98691471c43fc0597fb3472c46a172bbc715843ace` | IDENTICAL |
| `config/account_relationship_supplement_v1.json` | 548 | `2793b239c9f303d158f6ace20997b181c782334b781550363dd6e60ddef39fa5` | `2793b239c9f303d158f6ace20997b181c782334b781550363dd6e60ddef39fa5` | IDENTICAL |
| `config/eims_migration_mapping.json` | 12,623 | `1b8a5bc36a1bf1c7773781c7fd43153db026a8b8f0eef1000960df08ea348eb9` | `1b8a5bc36a1bf1c7773781c7fd43153db026a8b8f0eef1000960df08ea348eb9` | IDENTICAL |
| `config/eims_migration_mapping_v1.json` | 7,439 | `ae1b3549911e07e1d2fdd78e92e20089e22e03c4213dc9a21f7945655ea7e17c` | `ae1b3549911e07e1d2fdd78e92e20089e22e03c4213dc9a21f7945655ea7e17c` | IDENTICAL |
| `config/eims_migration_mapping_v2.json` | 12,623 | `1b8a5bc36a1bf1c7773781c7fd43153db026a8b8f0eef1000960df08ea348eb9` | `1b8a5bc36a1bf1c7773781c7fd43153db026a8b8f0eef1000960df08ea348eb9` | IDENTICAL |
| `config/eims_migration_mapping_v3.json` | 18,335 | `805a2aa8eaf30c2152db09c24abf22c778f3c79dfefe49a57c67a5cdc6ce93cc` | `805a2aa8eaf30c2152db09c24abf22c778f3c79dfefe49a57c67a5cdc6ce93cc` | IDENTICAL |
| `config/eims_migration_mapping_v3_count_source_r1.json` | 525 | `b4888faea938db91c951c1560f6161de7d0c8250dafa2b0220926f0823a97129` | `b4888faea938db91c951c1560f6161de7d0c8250dafa2b0220926f0823a97129` | IDENTICAL |
| `config/eims_migration_mapping_v3_disposal_r1.json` | 475 | `8ec7a20da18aead72595225488aefe9735f6b1fe5cae8e057c6864f5808dc6ab` | `8ec7a20da18aead72595225488aefe9735f6b1fe5cae8e057c6864f5808dc6ab` | IDENTICAL |
| `config/quota_rules.json` | 1,673 | `54089137e8569b4f99cd7713ede0adbea2e82a78a94f1f571462074903752bb0` | `54089137e8569b4f99cd7713ede0adbea2e82a78a94f1f571462074903752bb0` | IDENTICAL |
| `config/source_provenance.json` | 583 | `284b8b867e88b4db2e4dd7b0900f174037f3bf08b44e2aa8c47b8079de521905` | `284b8b867e88b4db2e4dd7b0900f174037f3bf08b44e2aa8c47b8079de521905` | IDENTICAL |
| `data/__init__.py` | 80 | `fd0c0d2e0921177dd5b0f648b203268f423bdfce31186c4d7e4ec3207b7145a6` | `fd0c0d2e0921177dd5b0f648b203268f423bdfce31186c4d7e4ec3207b7145a6` | IDENTICAL |
| `data/account_relationships.py` | 3,208 | `65eed020f47610e29d01ef4a2a5d3a30834a941996b994e09b58a48bbf17fd60` | `65eed020f47610e29d01ef4a2a5d3a30834a941996b994e09b58a48bbf17fd60` | IDENTICAL |
| `data/business_time.py` | 2,187 | `5c4d5765e686629e168e7be4896a54abfa70eaece01c22361a904d01367f9273` | `5c4d5765e686629e168e7be4896a54abfa70eaece01c22361a904d01367f9273` | IDENTICAL |
| `data/confirmed_quota_position.py` | 5,554 | `2651a20e2025fb3196faffcbbc3a99dd38ab1e676c6dc6dbe702047910243c1e` | `2651a20e2025fb3196faffcbbc3a99dd38ab1e676c6dc6dbe702047910243c1e` | IDENTICAL |
| `data/connection.py` | 35,760 | `4998d6f0f92ae5230e02eddf930344cfa43e95b9b4e792ffa25a68e983679bd7` | `4998d6f0f92ae5230e02eddf930344cfa43e95b9b4e792ffa25a68e983679bd7` | IDENTICAL |
| `data/constants.py` | 4,768 | `1ce89ee761ce412848ca8e710e851da21ae391a63211915fb70e48f7058edd47` | `1ce89ee761ce412848ca8e710e851da21ae391a63211915fb70e48f7058edd47` | IDENTICAL |
| `data/controlled_case.py` | 11,575 | `220c5e68c915787fa36d9586c930e6c9a9209566a710f7490cd7bf7c6d4dea3b` | `220c5e68c915787fa36d9586c930e6c9a9209566a710f7490cd7bf7c6d4dea3b` | IDENTICAL |
| `data/controlled_primitives.py` | 1,104 | `452a97f3862d2306f4b34686e0c9e76fe75c5ff5f80d73222107ce619a3736f4` | `452a97f3862d2306f4b34686e0c9e76fe75c5ff5f80d73222107ce619a3736f4` | IDENTICAL |
| `data/correction_decisions.py` | 1,056 | `f9b9d742c6cc7fe19976a91347212de89d62341c1e40c47718519bff4fd0ae66` | `f9b9d742c6cc7fe19976a91347212de89d62341c1e40c47718519bff4fd0ae66` | IDENTICAL |
| `data/count_source_supplement.py` | 5,873 | `c12b8539fb7d941b79e84b0da6820b702461f37cffcd24fadfb8ff0865dbbdf4` | `c12b8539fb7d941b79e84b0da6820b702461f37cffcd24fadfb8ff0865dbbdf4` | IDENTICAL |
| `data/flock_quantity.py` | 7,945 | `5fc2a989236c76b2e465d9bcbf7c49bf96d0cd52d30c3e6488647261540c7b4b` | `5fc2a989236c76b2e465d9bcbf7c49bf96d0cd52d30c3e6488647261540c7b4b` | IDENTICAL |
| `data/flock_quota_import.py` | 31,927 | `c92faba8527bed71cfff6de6512e2ca9b5f2e2e4c1f3e3f8c67e975ae7c0ddbc` | `c92faba8527bed71cfff6de6512e2ca9b5f2e2e4c1f3e3f8c67e975ae7c0ddbc` | IDENTICAL |
| `data/flock_stock.py` | 4,907 | `f25c2241968724b906c7163bcfbd827ddd4d27fad24ebfbbb5f4e055bf7e8e82` | `f25c2241968724b906c7163bcfbd827ddd4d27fad24ebfbbb5f4e055bf7e8e82` | IDENTICAL |
| `data/flock_transaction_supplement.py` | 12,751 | `5834991e5097303e560167693a8c4c8ce8367b1d52187723c14636a1123f8352` | `5834991e5097303e560167693a8c4c8ce8367b1d52187723c14636a1123f8352` | IDENTICAL |
| `data/historical_corrections.py` | 21,537 | `4421f2e6c6e6f650cf0a7f46d7efc41ff12d04eed5572a6b1e6f321e35a6f360` | `4421f2e6c6e6f650cf0a7f46d7efc41ff12d04eed5572a6b1e6f321e35a6f360` | IDENTICAL |
| `data/importing.py` | 6,428 | `d38f19cc3ad630b00bdb7caf1578ac6da6cb3ee6ee2871026bb6883d96315cb3` | `d38f19cc3ad630b00bdb7caf1578ac6da6cb3ee6ee2871026bb6883d96315cb3` | IDENTICAL |
| `data/migration.py` | 26,785 | `892a7d2a9b3dbd1e3100ba436d97ead769d3a3d95af86b6df310d25839cad5a6` | `892a7d2a9b3dbd1e3100ba436d97ead769d3a3d95af86b6df310d25839cad5a6` | IDENTICAL |
| `data/migration_identity.py` | 2,243 | `efc0725205d5466f2a07d58786b94418fd839477622211d247dc9881a84b2294` | `efc0725205d5466f2a07d58786b94418fd839477622211d247dc9881a84b2294` | IDENTICAL |
| `data/operational_flock_quota_import.py` | 28,028 | `56f2fee37c0c1539117b78cd142f8dee7b963cd7ff9aa3fd60d9b1858deb4e39` | `56f2fee37c0c1539117b78cd142f8dee7b963cd7ff9aa3fd60d9b1858deb4e39` | IDENTICAL |
| `data/position_evidence.py` | 1,249 | `83b0a30c5568be9ba0df76453d38955a1cf21288e64c41799223b100cfaaf08f` | `83b0a30c5568be9ba0df76453d38955a1cf21288e64c41799223b100cfaaf08f` | IDENTICAL |
| `data/producer_identity.py` | 3,602 | `93e9e730569a7f8b4037b36c31e8cae809af1506bbc889521d12dd45968910b3` | `93e9e730569a7f8b4037b36c31e8cae809af1506bbc889521d12dd45968910b3` | IDENTICAL |
| `data/production_intake.py` | 2,387 | `921674913c50a7801bfebb161fadc0c49c29cbe9633156a7d748f0e610413fce` | `921674913c50a7801bfebb161fadc0c49c29cbe9633156a7d748f0e610413fce` | IDENTICAL |
| `data/profiling.py` | 10,466 | `87cf1aa18f97698deeec7f0ae70bb351b9e10a7ce30638d5d3f30e52bd93e930` | `87cf1aa18f97698deeec7f0ae70bb351b9e10a7ce30638d5d3f30e52bd93e930` | IDENTICAL |
| `data/quota_position.py` | 12,209 | `fb25c77e0ef28b20e571e916ffc5237bbd6ace5fdc840f81e1c35d7b72608db2` | `fb25c77e0ef28b20e571e916ffc5237bbd6ace5fdc840f81e1c35d7b72608db2` | IDENTICAL |
| `data/quota_types.py` | 892 | `a9c7e52f204c18c05b959f8f8b2e0c67c13f4f29ce66e35687feed786a9772d6` | `a9c7e52f204c18c05b959f8f8b2e0c67c13f4f29ce66e35687feed786a9772d6` | IDENTICAL |
| `data/record_safety.py` | 20,593 | `24d0ca02707582b9f0f98e132bb3438329afd017fa0fa57dca29baef1010b9a3` | `24d0ca02707582b9f0f98e132bb3438329afd017fa0fa57dca29baef1010b9a3` | IDENTICAL |
| `data/repositories/__init__.py` | 1,419 | `65bc74b32b3238732fa1c10b6a109f8a0c86111b464c4412756626715c0d9b50` | `65bc74b32b3238732fa1c10b6a109f8a0c86111b464c4412756626715c0d9b50` | IDENTICAL |
| `data/repositories/base.py` | 21,981 | `390cedadd20952f844a2117b0ff30d8970ff80ecff6190115830a5ccc481203b` | `390cedadd20952f844a2117b0ff30d8970ff80ecff6190115830a5ccc481203b` | IDENTICAL |
| `data/repositories/continuity.py` | 51,900 | `07ba5f44404e3d3ca8c680d897df6fb430fc64f8fe8f8fff660af3e0d3c3c99b` | `07ba5f44404e3d3ca8c680d897df6fb430fc64f8fe8f8fff660af3e0d3c3c99b` | IDENTICAL |
| `data/repositories/controlled_supplements.py` | 39,215 | `6b42eb3f3714c00b50d187687e2d6eb116d0e3b811e67ab06058b84e94f0f771` | `6b42eb3f3714c00b50d187687e2d6eb116d0e3b811e67ab06058b84e94f0f771` | IDENTICAL |
| `data/repositories/correction_review.py` | 17,068 | `b1abf67db89e59a29bd2229c0d32eb3705186df9f9eac02b65cc88cd0841d8d7` | `b1abf67db89e59a29bd2229c0d32eb3705186df9f9eac02b65cc88cd0841d8d7` | IDENTICAL |
| `data/repositories/flock_date_repair.py` | 31,628 | `3121d29139d0fe3e88bbaf63aafa2b68b8841274a0f0c3d438a980b2f3408201` | `3121d29139d0fe3e88bbaf63aafa2b68b8841274a0f0c3d438a980b2f3408201` | IDENTICAL |
| `data/repositories/flock_supplement.py` | 12,018 | `599c04f7fd51f2e5da512cc913dd3d777234a2135bb789ccb9d0594d03354076` | `599c04f7fd51f2e5da512cc913dd3d777234a2135bb789ccb9d0594d03354076` | IDENTICAL |
| `data/repositories/mock.py` | 85,309 | `290190b38ddf439c32b52add6313bf20072c7eb6061772546a6c529a241fb653` | `290190b38ddf439c32b52add6313bf20072c7eb6061772546a6c529a241fb653` | IDENTICAL |
| `data/repositories/snowflake.py` | 113,120 | `442e35ca4158383cc274ae10bb65de88bfb1f4390c2c3d4266351bc0a66a2d70` | `442e35ca4158383cc274ae10bb65de88bfb1f4390c2c3d4266351bc0a66a2d70` | IDENTICAL |
| `data/source_evidence.py` | 860 | `d2a5f25ea9142cdcf6cabcf4e3a041960579007ad22bb962b9cb892dcc2433b5` | `d2a5f25ea9142cdcf6cabcf4e3a041960579007ad22bb962b9cb892dcc2433b5` | IDENTICAL |
| `data/source_scope.py` | 917 | `68d362ce3c75bebb1f4cfefa60fbe5f953419ff0a7f679bdb72800437e68179a` | `68d362ce3c75bebb1f4cfefa60fbe5f953419ff0a7f679bdb72800437e68179a` | IDENTICAL |
| `data/source_trace.py` | 13,046 | `8b76f1d6c00c1b5db8d917e93931f759859e2e2b2bd99d1a5da1b9ddf9dab4ec` | `8b76f1d6c00c1b5db8d917e93931f759859e2e2b2bd99d1a5da1b9ddf9dab4ec` | IDENTICAL |
| `data/synthetic.py` | 25,426 | `552765f2b394b0b44e28b1baba95975f1a927b422db024aed9dbb79d50d17cbf` | `552765f2b394b0b44e28b1baba95975f1a927b422db024aed9dbb79d50d17cbf` | IDENTICAL |
| `data/validation.py` | 15,131 | `82b43bd919f2538234c5f1d406da31c54b565c75508319bb9660ac07c945d419` | `82b43bd919f2538234c5f1d406da31c54b565c75508319bb9660ac07c945d419` | IDENTICAL |
| `environment.yml` | 186 | `9ea45e0d1c1be258e4fe672cbb1eafe5bec185338273bf821df941c21ab3681f` | `9ea45e0d1c1be258e4fe672cbb1eafe5bec185338273bf821df941c21ab3681f` | IDENTICAL |
| `streamlit_app.py` | 814 | `5f57b260db8a1fb8f74320fdd0a60853042efef7340419b4a964d64e85dc54bc` | `5f57b260db8a1fb8f74320fdd0a60853042efef7340419b4a964d64e85dc54bc` | IDENTICAL |

### Aggregate verification

| Measure | Before | After | Result |
| --- | --- | --- | --- |
| Shipped path count | 113 | 113 | IDENTICAL |
| Shipped bytes | 1,661,854 | 1,661,854 | IDENTICAL |
| SHA-256 of sorted `repository-relative path + NUL + raw SHA-256 + newline` records | `3fef475184b13b9ec753c7ba67b1f6bfb8a75d10713ae5abca858d23ecdcd4f3` | `3fef475184b13b9ec753c7ba67b1f6bfb8a75d10713ae5abca858d23ecdcd4f3` | IDENTICAL |
| Live candidate LF hashes regenerated | 88 | 88 | Values unchanged; manifest bytes preserved |

Historical captured-source and patch manifests retain their main-branch bytes. Their baseline snapshots were not relabeled as current source. No manifest conflicts occurred; the candidate regeneration started from main's unchanged version.

### Before/after suite comparison

| Suite | Before passed / skipped / failed / errors | After passed / skipped / failed / errors | Result |
| --- | --- | --- | --- |
| Full release directory | 1,980 / 1 / 0 / 0 | 1,980 / 1 / 0 / 0 | MATCH |
| Full root | 706 / 0 / 0 / 0 | 706 / 0 / 0 / 0 | MATCH |

Release elapsed time: 1,183.40 s before, 1,175.28 s after. Root elapsed time: 232.21 s before, 200.08 s after. Commands were `python -m pytest -q` in each directory using the existing release environment and root Python 3.11 CI environment. **Tests changed for moved paths: none.**

Final outcome: eight report moves, one short docs index, two relative Markdown link retargets, zero deletions, zero script moves, zero runtime/code/comment/config/SQL/data changes. The root app, unverified historical scripts and executable audit reproducers remain NEEDS-REVIEW. No real producer/flock data files were added. No PR, Snowflake access or deployment.
