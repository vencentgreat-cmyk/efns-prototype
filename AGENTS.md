# Independent source review

Review offline. Do not connect to Snowflake, execute SQL, deploy, or attempt to
recover credentials. `pytest` installs a network-blocking audit hook. Use the
included synthetic fixtures and fake SQL executors; do not weaken runtime
company identity checks to make synthetic tests pass.

Start with README.md, REVIEW_GUIDE.md, review/BASELINE.json and
review/SOURCE_ORIGINS.json. Application files match the frozen candidate except
four disabled prototype seed hash literals in app/security.py (sharing only).
This directory is not the original development Git tree.
Do not assume the candidate is deployed, or that local tests prove real-engine,
distributed concurrency or human browser acceptance.

SQL is static review context, not an installation instruction. Some historical
upgrade scripts update metadata and have privileged role switches. No SQL is
run by the offline suite. Company deployment/GET_DDL evidence is not included.

Audit business boundaries and missing tests independently; use concrete file
and function references. Do not treat existing passing assertions as a proof.
