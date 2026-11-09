# Evidence Index

| ID | Evidence | Scope and limitation |
| --- | --- | --- |
| E01 | evidence/current/dev_evidence.json | Fresh read-only ACCOUNTADMIN metadata, GET_DDL, counts and PK/UK/FK scans; capture time is in file. Not a normal-user access test. |
| E02 | evidence/current/documentation_queries.json | Fresh SELECT/SHOW production associations, provenance aggregates, pending split, counts and timestamp precision. Query IDs and parameters preserved. |
| E03 | evidence/current/code_queries/deployed_verification.json | Fresh SELECT-only reads using saved deployed source and EFNS_DEV_DEPLOYER, secondary roles NONE; correction/target/query/export checks. Snapshot code, not new live download or browser run. |
| E04 | evidence/prior/deployment_scope.json, permissions.json, preserved_values.json, final_supplement.json | Prior 12 October executed deployment/permission/value evidence; not rerun as writes in this work. |
| E05 | evidence/material_inventory.json; metadata/local_vs_deployed.csv; source_code_index.csv | Actual local files/hashes/line references. Local behavior is not deployment proof. |
| E06 | Downloads/Database Developer Work Plan.pdf; evidence/source_text/Database Developer Work Plan.txt | Original collected scope by Dr. Lu, dated source; not formula approval. |
| E07 | Downloads/EFNS_DEV_Database_Design_Review_v1.4.pdf; evidence/source_text/EFNS_DEV_Database_Design_Review_v1.4.txt | 26-page 13 October presentation read fully; secondary design summary. Matching PPTX not found in Downloads. |
| E08 | Prior EFNS_DEV_Data_Dictionary_2026-10-12.xlsx and claude_handoff.zip; material inventory | Existing files inspected including workbook sheets and archive members; prior dictionary, not enhanced current wording. |
| E09 | docs/BUSINESS_RULES.md; docs/FACILITY_FLOCK_DESIGN.md; dated user confirmations in material provenance notes | Sara 8 October Facility rule and user-reported acceptance; repository notes include stale deployment descriptions, not independently authoritative for current views. |
| E10 | External_References.md | Documentation methods and official Snowflake constraint behavior only, not EFNS business definitions. |
