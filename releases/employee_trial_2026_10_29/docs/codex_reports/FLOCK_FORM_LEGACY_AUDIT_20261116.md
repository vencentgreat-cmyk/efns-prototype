# Flock form legacy audit — before implementation

Branch: `codex-flock-form-legacy-20261116`. Base: fetched `origin/main`, `164fd5d` (blank-null display PR #35). `git merge-base --is-ancestor 28449d2 origin/main` succeeded. The existing native null placeholders will not be redone.

This records the read-only code audit made before implementation, against base `164fd5d`. At audit completion no shipped file, SQL, schema, data, repository, report, export helper or test had changed. The user's counts (2,220 stored flocks, three differing identifiers) are supplied business context, not independently checked against Snowflake.

## Findings requiring the user's decision

1. **Ordinary form creation currently has no duplicate-number guard.** `validate_flock` requires FLOCK_NUMBER and PERMIT_NUMBER but does not check uniqueness (`data/validation.py:123`). Ordinary `upsert_flock` validates and saves (`data/repositories/mock.py:385`, `data/repositories/snowflake.py:593`). Both ordinary `create_record_once` and confirmed-initial-position creation use those paths. Existing duplicate checks are in **batch import**, not ordinary form creation. Adding a page-level Permit Number guard can stay within scope and block sequential UI duplicates, but cannot atomically reject two simultaneous sessions; an atomic guarantee would require a separately authorized repository/write-boundary change.
2. **Editing Permit Number while preserving FLOCK_NUMBER can leave different labels/order elsewhere.** Relationships use FLOCK_ID, so their foreign-key links stay intact. Several other pages and report/export projections still display or sort by FLOCK_NUMBER; imports also use it as a matching key. Those modules are explicitly outside scope. Confirm whether Permit Number edits should be allowed with FLOCK_NUMBER preserved and those downstream uses left unchanged, or whether Permit Number editing should be disabled pending a separate decision. No automatic synchronization is proposed.

The user resolved both decisions before code edits: add a page-level, trimmed/case-insensitive Permit Number check on create only, document its concurrency limit, and make Permit Number read-only on edit. Existing FLOCK_NUMBER is never synchronized or rewritten. An edit must not be blocked by pre-existing duplicate permits. The current implementation/test results are recorded separately in `FLOCK_FORM_LEGACY_20261116.md`; the inventory below remains the pre-change audit snapshot.

## Usage and effect summary

| Use | Locations | Finding / proposed compatibility boundary |
|---|---|---|
| Required create/edit data | data/validation.py:128; data/record_safety.py:61; repository MODEL | FLOCK_NUMBER remains maintained and required internally. Creating it from Permit Number satisfies the existing required-field contract; existing records must preserve their original value. |
| Ordinary creation idempotency | app/services/form_safety.py:71; data/record_safety.py:132 | Stable target/revision IDs use entity + request ID, not FLOCK_NUMBER. The complete record is included in the replay fingerprint; deriving the same number from the same permit is deterministic. Duplicate business identifiers with different requests are not blocked by idempotency. |
| Confirmed initial-position creation | data/repositories/continuity.py:481 | Stable target/event identities use the request ID and FLOCK_ID; retries compare the submitted record. Preserve the existing call, request identity and initial-position/Delivery behavior. |
| Batch import uniqueness and matching | data/flock_quota_import.py:395,526,538,599,608; data/repositories/mock.py:726; data/repositories/snowflake.py:1556 | DEV workbook matching uses FLOCK_NUMBER; both duplicate Flock Number and Permit Number checks exist. Leave these paths unchanged. |
| Migration contracts | data/operational_flock_quota_import.py:69,75,84,374; config/eims_migration_mapping*.json | Older mappings use FLOCK_NUMBER as a natural key; V3 falls back through efc_flocknumber, new_name and source GUID. Not a form concern; no mapping/import edits. |
| Flock list/form/detail | app/pages/5_Flocks.py:89,115,127,210,244,252; app/services/legacy_view_labels.py:8 | Current keyword filter searches both identifiers, the title and Summary show FLOCK_NUMBER, the form enters it and captures/saves it. Proposed changes are limited to display/input removal and create-only derivation; keep filter semantics and preserve existing values on edit. |
| Related labels and selectors | Accounts, Facilities, Facility Details, Flock Transactions, Quota Registrations, Salmonella Tests/Report, Reports, Record History | These use FLOCK_NUMBER for labels; targets and joins use FLOCK_ID. The Accounts page does not share the Flock form; its related table currently labels flocks with FLOCK_NUMBER. Leave outside pages unchanged unless scope is explicitly expanded. |
| Flock Current ordering | app/services/flock_current_report.py:149,174 | Uses FLOCK_NUMBER to order rows within Account/Quota Type groups. Permit Number is the displayed permit. No report logic/order changes permitted. |
| Count Report test-data scope | app/services/flock_reports.py:235 | Excludes explicit DEV_TEST prefixes in either identifier. Keep logic unchanged; a newly created record no longer has an independently entered test prefix, so its permit supplies the derived FLOCK_NUMBER as requested. |
| Report/export projections | app/services/report_builder.py:54; report_center.py:99; report_relationships.py:24; salmonella_reporting.py:33,44; sql/04_reporting_views.sql:103 | FLOCK_NUMBER remains an explicit selectable/exported field or a FLOCK_ID-joined label. Do not remove or relabel it in reports/exports. |
| Record History / correction workspace | app/pages/21_Record_History.py:87,158,224; app/services/revision_history.py:95; historical_correction_workspace.py:49 | History selectors/labels and a correction attribute still include FLOCK_NUMBER. Existing history capability is outside this form task and remains unchanged. |
| Supplement workspace | app/services/flock_supplement_workspace.py:31 | Read-only target display includes FLOCK_NUMBER. No change. |
| Synthetic generation / SQL seeds | data/synthetic.py:261; sql/09_dev_synthetic_seed.sql; scripts/generate_fake_eims_export.py | Fixtures may deliberately use distinct flock and permit numbers. Retain them to prove old records are not converted. |
| UI tests using the removed widget | tests/test_facility_flock_relationships.py:109; tests/test_flock_date_defaults.py:106,123; tests/test_staff_workflow_ui.py:32 | These currently enter/edit flock_form_number and will need intention-preserving updates. Existing legacy-label/list tests also expect the field in the default view. Full fixture/validation/import/report tests must continue preserving internal FLOCK_NUMBER semantics. |

All tracked Python/SQL/JSON/YAML references in the repository (including root legacy code and tests) are indexed below, without copying record values. Main working-tree source remains unchanged. Markdown reports and CSV/XLSX/PDF data fixtures are not runtime symbol uses and are not included in this source inventory.

## Hatchery / Breeder plan (not implemented)

Use existing get_accounts results and HATCHERY_ROLE / BREEDER_ROLE flags. Optional selectors would store the exact selected ORGANIZATION_NAME text in HATCHERY / BREEDER. Stored values absent from role-account choices must stay selected/selectable, with a blank/clear choice. Add both to the existing capture_form snapshot so unchanged values are preserved and not rewritten. No new account lookup SQL, account foreign key, self-placeholder inference or role mutation is proposed.

## Complete tracked source-reference inventory

| Tracked file | Lines containing FLOCK_NUMBER |
|---|---|
| app/pages/10_Salmonella_Report.py | 31 |
| app/pages/11_Facilities.py | 116 |
| app/pages/13_Facility_Details.py | 113 |
| app/pages/21_Record_History.py | 63, 121 |
| app/pages/3_Accounts_Facilities_Flocks.py | 233 |
| app/pages/4_Reports.py | 54, 162 |
| app/pages/5_Flocks.py | 74, 85, 93, 106, 157, 190 |
| app/pages/6_Flock_Transactions.py | 21, 22, 44, 45, 53 |
| app/pages/7_Quota_Registrations.py | 191 |
| app/pages/9_Salmonella_Tests.py | 27, 29, 74, 79, 90, 113, 127 |
| app/services/flock_supplement_workspace.py | 31 |
| app/services/historical_correction_workspace.py | 49 |
| app/services/report_builder.py | 54 |
| app/services/report_center.py | 68 |
| app/services/report_relationships.py | 24 |
| app/services/salmonella_reporting.py | 33, 44 |
| config/eims_migration_mapping.json | 159, 167, 171 |
| config/eims_migration_mapping_v1.json | 43, 44, 45 |
| config/eims_migration_mapping_v2.json | 159, 167, 171 |
| config/eims_migration_mapping_v3.json | 123, 141 |
| data/flock_quota_import.py | 47, 394, 396, 525, 537, 639 |
| data/operational_flock_quota_import.py | 69, 75, 84, 374, 375, 378 |
| data/repositories/continuity.py | 577 |
| data/repositories/mock.py | 737, 743 |
| data/repositories/snowflake.py | 49, 1567, 1573 |
| data/synthetic.py | 261 |
| data/validation.py | 124 |
| docs/database_manual_2026-10-13/metadata/actual_get_ddl.sql | 204, 667, 691 |
| docs/database_manual_2026-10-13/metadata/enhanced_dictionary.json | 8951, 8966, 8969, 8978, 8979, 8983, 8986, 8998, 9003, 24238, 24264, 26326, 26328, 26341, 26343, 26344, 26350, 26353, 26354, 26358, 26362, 26374, 26379 |
| docs/database_manual_2026-10-13/metadata/erd_spec.json | 3451 |
| docs/database_manual_2026-10-13/metadata/field_claim_evidence.json | 2982, 2985, 2988, 3000, 8657, 8660, 8664, 8676 |
| docs/database_manual_2026-10-13/metadata/structure_metadata.json | 2356, 6556, 9096, 9116 |
| docs/database_manual_2026-10-13/verification.sql | 48, 108 |
| docs/identity_history_2026-10-14/Actual_ERD_Spec.json | 2344, 6816 |
| docs/identity_history_2026-10-14/Actual_Get_DDL.sql | 217, 751, 775 |
| docs/identity_history_2026-10-14/Latest_Data_Dictionary.json | 3102, 3109, 3113, 9638, 9640, 9645, 9649 |
| releases/employee_trial_2026_10_29/app/pages/10_Salmonella_Report.py | 33 |
| releases/employee_trial_2026_10_29/app/pages/11_Facilities.py | 129 |
| releases/employee_trial_2026_10_29/app/pages/13_Facility_Details.py | 110 |
| releases/employee_trial_2026_10_29/app/pages/21_Record_History.py | 87, 158, 224 |
| releases/employee_trial_2026_10_29/app/pages/3_Accounts_Facilities_Flocks.py | 245 |
| releases/employee_trial_2026_10_29/app/pages/4_Reports.py | 88, 559 |
| releases/employee_trial_2026_10_29/app/pages/5_Flocks.py | 89, 115, 127, 210, 244, 252 |
| releases/employee_trial_2026_10_29/app/pages/6_Flock_Transactions.py | 28, 29, 50, 51, 59 |
| releases/employee_trial_2026_10_29/app/pages/7_Quota_Registrations.py | 172 |
| releases/employee_trial_2026_10_29/app/pages/9_Salmonella_Tests.py | 32, 34, 68, 73, 84, 105, 119 |
| releases/employee_trial_2026_10_29/app/services/flock_current_report.py | 149 |
| releases/employee_trial_2026_10_29/app/services/flock_reports.py | 235 |
| releases/employee_trial_2026_10_29/app/services/flock_supplement_workspace.py | 31 |
| releases/employee_trial_2026_10_29/app/services/historical_correction_workspace.py | 49 |
| releases/employee_trial_2026_10_29/app/services/legacy_view_labels.py | 8, 18 |
| releases/employee_trial_2026_10_29/app/services/report_builder.py | 54 |
| releases/employee_trial_2026_10_29/app/services/report_center.py | 99 |
| releases/employee_trial_2026_10_29/app/services/report_relationships.py | 24 |
| releases/employee_trial_2026_10_29/app/services/revision_history.py | 95 |
| releases/employee_trial_2026_10_29/app/services/salmonella_reporting.py | 33, 44 |
| releases/employee_trial_2026_10_29/config/eims_migration_mapping.json | 159, 167, 171 |
| releases/employee_trial_2026_10_29/config/eims_migration_mapping_v1.json | 43, 44, 45 |
| releases/employee_trial_2026_10_29/config/eims_migration_mapping_v2.json | 159, 167, 171 |
| releases/employee_trial_2026_10_29/config/eims_migration_mapping_v3.json | 123, 141 |
| releases/employee_trial_2026_10_29/data/flock_quota_import.py | 48, 395, 397, 526, 538, 640 |
| releases/employee_trial_2026_10_29/data/operational_flock_quota_import.py | 69, 75, 84, 374, 375, 378 |
| releases/employee_trial_2026_10_29/data/record_safety.py | 61 |
| releases/employee_trial_2026_10_29/data/repositories/mock.py | 774, 780 |
| releases/employee_trial_2026_10_29/data/repositories/snowflake.py | 54, 1608, 1614 |
| releases/employee_trial_2026_10_29/data/synthetic.py | 261 |
| releases/employee_trial_2026_10_29/data/validation.py | 128 |
| releases/employee_trial_2026_10_29/docs/audit/repro/test_staff_audit.py | 64 |
| releases/employee_trial_2026_10_29/docs/audit/repro/test_staff_audit_r3_locators.py | 64 |
| releases/employee_trial_2026_10_29/scripts/generate_fake_eims_export.py | 88, 174 |
| releases/employee_trial_2026_10_29/sql/02_core_tables.sql | 163 |
| releases/employee_trial_2026_10_29/sql/04_reporting_views.sql | 103 |
| releases/employee_trial_2026_10_29/sql/09_dev_synthetic_seed.sql | 149, 187, 193, 350 |
| releases/employee_trial_2026_10_29/sql/10_EIMS_V3_DEV_Deployment.sql | 141, 422, 875 |
| releases/employee_trial_2026_10_29/tests/test_account_usage_quantity.py | 37, 38, 42 |
| releases/employee_trial_2026_10_29/tests/test_continuity.py | 113, 161, 163, 164, 166 |
| releases/employee_trial_2026_10_29/tests/test_current_count_zero.py | 82 |
| releases/employee_trial_2026_10_29/tests/test_delivery_quota_types.py | 39 |
| releases/employee_trial_2026_10_29/tests/test_eims_migration.py | 48, 68 |
| releases/employee_trial_2026_10_29/tests/test_enterprise_modules.py | 47, 64, 177 |
| releases/employee_trial_2026_10_29/tests/test_facility_flock_relationships.py | 27, 85, 88, 98, 114, 139 |
| releases/employee_trial_2026_10_29/tests/test_flock_current_report.py | 26 |
| releases/employee_trial_2026_10_29/tests/test_flock_date_batching.py | 31 |
| releases/employee_trial_2026_10_29/tests/test_flock_date_defaults.py | 114, 132 |
| releases/employee_trial_2026_10_29/tests/test_flock_date_repair.py | 39, 216 |
| releases/employee_trial_2026_10_29/tests/test_flock_quota_import.py | 70, 98, 101, 148, 371 |
| releases/employee_trial_2026_10_29/tests/test_flock_report_record_count.py | 37, 40 |
| releases/employee_trial_2026_10_29/tests/test_flock_reports.py | 23, 69 |
| releases/employee_trial_2026_10_29/tests/test_flock_reports_2.py | 27 |
| releases/employee_trial_2026_10_29/tests/test_flock_transaction_supplement.py | 51 |
| releases/employee_trial_2026_10_29/tests/test_flocks_accounts_legacy_labels.py | 170 |
| releases/employee_trial_2026_10_29/tests/test_historical_corrections.py | 59 |
| releases/employee_trial_2026_10_29/tests/test_manual_historical_corrections.py | 34 |
| releases/employee_trial_2026_10_29/tests/test_operational_flock_quota_import.py | 101 |
| releases/employee_trial_2026_10_29/tests/test_phase1_2_regressions.py | 34, 49, 55 |
| releases/employee_trial_2026_10_29/tests/test_r3_audit_fixes.py | 119 |
| releases/employee_trial_2026_10_29/tests/test_related_record_navigation.py | 35 |
| releases/employee_trial_2026_10_29/tests/test_report_account_roles.py | 28, 29, 30, 67, 149 |
| releases/employee_trial_2026_10_29/tests/test_report_smoke.py | 38, 42 |
| releases/employee_trial_2026_10_29/tests/test_review_integrated.py | 116 |
| releases/employee_trial_2026_10_29/tests/test_round2.py | 139, 179, 360 |
| releases/employee_trial_2026_10_29/tests/test_round2_boundaries.py | 34, 181, 218 |
| releases/employee_trial_2026_10_29/tests/test_round3.py | 54 |
| releases/employee_trial_2026_10_29/tests/test_snowflake_write_contracts.py | 649, 690, 705 |
| releases/employee_trial_2026_10_29/tests/test_staff_workflow_ui.py | 36 |
| releases/employee_trial_2026_10_29/tests/test_staff_workflows.py | 29, 90, 94, 124, 140 |
| releases/employee_trial_2026_10_29/tests/test_v6_consistency.py | 128, 220, 227 |
| scripts/build_design_handoff.py | 84 |
| scripts/generate_fake_eims_export.py | 88, 174 |
| scripts/verify_continuity_dev.py | 44 |
| sql/02_core_tables.sql | 160 |
| sql/04_reporting_views.sql | 103 |
| sql/09_dev_synthetic_seed.sql | 149, 187, 193, 350 |
| sql/10_EIMS_V3_DEV_Deployment.sql | 140, 421, 874 |
| tests/test_continuity.py | 113, 161, 162, 163, 165 |
| tests/test_eims_migration.py | 50, 70 |
| tests/test_enterprise_modules.py | 47, 64, 177 |
| tests/test_facility_flock_relationships.py | 26, 84, 87, 97, 113, 136 |
| tests/test_flock_date_repair.py | 39, 216 |
| tests/test_flock_quota_import.py | 70, 98, 101, 148, 367 |
| tests/test_flock_report_record_count.py | 37, 40 |
| tests/test_flock_transaction_supplement.py | 51 |
| tests/test_historical_corrections.py | 59 |
| tests/test_manual_historical_corrections.py | 34 |
| tests/test_operational_flock_quota_import.py | 101 |
| tests/test_phase1_2_regressions.py | 34, 49, 55 |
| tests/test_related_record_navigation.py | 35 |
| tests/test_report_account_roles.py | 28, 29, 30, 67, 149 |
| tests/test_snowflake_write_contracts.py | 649, 690, 705 |
| tests/test_v6_consistency.py | 128, 220, 227 |

Inventory: 130 files, 333 matching lines. No row values are reproduced.
