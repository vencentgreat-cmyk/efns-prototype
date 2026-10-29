# Current findings and boundaries

The D1–D12 reproductions and U1–U6 engineering checks are tracked in `PROCESSING_MATRIX.md`. All included offline tests pass except one explicit company-snapshot skip; there are no expected failures. This does not certify company Snowflake isolation, permissions, all real data, or browser UAT. In particular, generic writes outside the application continuity lock protocol can bypass application-level reference protection. Real two-session tests and minimal company write validation require separate authorization.

Quota availability, units, transfer direction, ended-Flock occupancy and staff approval policy remain business decisions. No historical records were changed and no company connection was made during this local fix.
