# Review guide — challenge the fixes

Start with `review/PROCESSING_MATRIX.md` for D1–D12, U1–U6 and business boundaries. The external report was available, but its referenced `repros/test_review_repros.py` was not supplied; `tests/test_review_findings.py` and `tests/test_review_integrated.py` reconstruct the scenarios with project-relative paths and synthetic fixtures. The first 18 correct-behavior assertions failed on the baseline; the corrected package passed the complete offline suite.

Inspect `app/services/form_safety.py`, the nine entity pages and `app/pages/21_Record_History.py` for edit preservation, request identity and explicit reload. Inspect `data/record_safety.py`, `data/repositories/continuity.py`, `snowflake.py`, `mock.py` and `app/services/authorized_repository.py` for atomic revisions/audit, reference checks and serialized business writes. Inspect `data/operational_flock_quota_import.py`, `data/production_intake.py` and `app/services/report_center.py` for daily validation, producer preview consistency and unsupported filters. Tests are evidence only for the stated local scenarios; no live transaction, grant or concurrent-session write was performed.

Protected work from the saved live baseline remains: date batch repair/R1, identity guards, the 40053 supplement, source trace, navigation, report count and light theme. Compare the expanded deployment candidate separately before any future deployment. Do not deploy this review copy; it has disabled seed hashes.

Key questions remain: quota direction/units/effective dates, whether ended Flocks count in actual occupancy, who may alter registered Bird Count, and historical ownership exceptions. The application labels registered Bird Count as such and does not claim a certified capacity percentage.
