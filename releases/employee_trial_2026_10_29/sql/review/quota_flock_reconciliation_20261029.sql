-- SUPERSEDED CANDIDATE ARITHMETIC (2026-10-30): the additive Base candidate below
-- is superseded by the confirmed latest-Base snapshot rule and MUST NOT be used
-- as a position. Retained SQL is for source/link reconciliation only.
-- READ ONLY – run manually
-- No connection, DDL, DML, SET/USE, temporary objects or business writes.
-- Database/schema are explicit. Use an authorized role with SELECT on the named RAW/CORE tables.
-- Scope is ONLY the named original migration batch, not the full company database.
-- Inspect identity first; stop unless the five company values and database are correct.
-- Source dates use the first YYYY-MM-DD portion: NO timezone conversion.
-- COUNT_IF counts are explicitly coalesced to 0 (counts only, never unknown quantities).
-- Reference: https://docs.snowflake.com/en/sql-reference/functions/count_if
-- Missing text: NULL, nan, none, nat, <NA>, empty. Numeric zero is preserved.
-- A composite batch + RAW-row identity is used in EVERY mapping join.
-- Missing owner cannot be recovered from Related Account or a display label.
-- No query treats source status as proof of lifecycle or a quota direction.
SELECT CURRENT_ORGANIZATION_NAME() AS organization, CURRENT_ACCOUNT_NAME() AS account_name,
       CURRENT_ACCOUNT() AS locator, CURRENT_REGION() AS region, CURRENT_DATABASE() AS database_name,
       CURRENT_ROLE() AS role_name, CURRENT_TIMESTAMP() AS queried_at;
-- Expected: QDCTNKN / UW19058 / CB12755 / AWS_CA_CENTRAL_1 / EFNS_DEV.
-- If database_name differs, choose EFNS_DEV in the Worksheet context before continuing.

-- T1e FIRST: every source row without an actual CORE target, including rejected/unmapped rows.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), quota_raw AS (
 SELECT r.*,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR) END) AS original_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR) END AS initial_flag,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR) END) AS owner_registration_id,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR) END,38,6) AS source_quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR) END,10)) AS source_date,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR) END,10)) AS source_end_date,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR) END AS credit_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR) END AS reserve_quota,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR) END AS related_transaction_guid,
        IFF(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END IN
            ('National Allocation','Provincial Allocation'),TRUE,FALSE) AS excluded_allocation
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_quotatransactions.csv'
), quota_registration AS (
 SELECT LOWER(TRIM(QUOTA_ID)) AS quota_id,COUNT(*) AS registration_rows,
        IFF(COUNT(*)=1,MIN(LOWER(TRIM(ACCOUNT_ID))),NULL) AS owner_account_id,
        IFF(COUNT(*)=1,MIN(QUOTA_TYPE),NULL) AS quota_type,
        MIN(STATUS) AS registration_status,MIN(END_DATE) AS registration_end_date
 FROM EFNS_DEV.CORE.QUOTA_REGISTRATION GROUP BY 1
), quota_core_matches AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,COUNT(c.QUOTA_TRANSACTION_ID) AS core_rows,
        COUNT(DISTINCT LOWER(c.QUOTA_TRANSACTION_ID)) AS core_target_ids,
        IFF(COUNT(c.QUOTA_TRANSACTION_ID)=1,MIN(c.QUOTA_TRANSACTION_ID),NULL) AS core_target_id
 FROM quota_raw r LEFT JOIN EFNS_DEV.CORE.QUOTA_TRANSACTION c
 ON LOWER(TRIM(c.QUOTA_TRANSACTION_ID)) IN (r.source_guid,r.target_guid,r.map_target,r.original_guid)
 GROUP BY 1,2
), quota_trace AS (
 SELECT r.*,c.core_rows,c.core_target_ids,c.core_target_id,
        q.owner_account_id,q.quota_type,q.registration_rows,q.registration_status,q.registration_end_date
 FROM quota_raw r JOIN quota_core_matches c
 ON c.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND c.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
 LEFT JOIN quota_registration q ON q.quota_id=r.owner_registration_id
)
SELECT MIGRATION_BATCH_ID,MIGRATION_RAW_ROW_ID,SOURCE_FILENAME,SOURCE_ROW_NUMBER,
       SOURCE_ID,TARGET_ID,original_guid,map_target,map_target_count,source_type,initial_flag,
       owner_registration_id,owner_account_id,quota_type,registration_rows,source_quantity,
       source_date,raw_state,excluded_allocation,VALIDATION_STATUS,VALIDATION_MESSAGES
FROM quota_trace WHERE core_rows=0 ORDER BY source_type,SOURCE_ROW_NUMBER;

-- T1e summary: NULL owner is UNRESOLVED, never assigned to a producer by name.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), quota_raw AS (
 SELECT r.*,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR) END) AS original_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR) END AS initial_flag,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR) END) AS owner_registration_id,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR) END,38,6) AS source_quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR) END,10)) AS source_date,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR) END,10)) AS source_end_date,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR) END AS credit_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR) END AS reserve_quota,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR) END AS related_transaction_guid,
        IFF(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END IN
            ('National Allocation','Provincial Allocation'),TRUE,FALSE) AS excluded_allocation
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_quotatransactions.csv'
), quota_registration AS (
 SELECT LOWER(TRIM(QUOTA_ID)) AS quota_id,COUNT(*) AS registration_rows,
        IFF(COUNT(*)=1,MIN(LOWER(TRIM(ACCOUNT_ID))),NULL) AS owner_account_id,
        IFF(COUNT(*)=1,MIN(QUOTA_TYPE),NULL) AS quota_type,
        MIN(STATUS) AS registration_status,MIN(END_DATE) AS registration_end_date
 FROM EFNS_DEV.CORE.QUOTA_REGISTRATION GROUP BY 1
), quota_core_matches AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,COUNT(c.QUOTA_TRANSACTION_ID) AS core_rows,
        COUNT(DISTINCT LOWER(c.QUOTA_TRANSACTION_ID)) AS core_target_ids,
        IFF(COUNT(c.QUOTA_TRANSACTION_ID)=1,MIN(c.QUOTA_TRANSACTION_ID),NULL) AS core_target_id
 FROM quota_raw r LEFT JOIN EFNS_DEV.CORE.QUOTA_TRANSACTION c
 ON LOWER(TRIM(c.QUOTA_TRANSACTION_ID)) IN (r.source_guid,r.target_guid,r.map_target,r.original_guid)
 GROUP BY 1,2
), quota_trace AS (
 SELECT r.*,c.core_rows,c.core_target_ids,c.core_target_id,
        q.owner_account_id,q.quota_type,q.registration_rows,q.registration_status,q.registration_end_date
 FROM quota_raw r JOIN quota_core_matches c
 ON c.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND c.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
 LEFT JOIN quota_registration q ON q.quota_id=r.owner_registration_id
)
SELECT owner_account_id,owner_registration_id,quota_type,source_type,excluded_allocation,
       COUNT(*) AS missing_source_rows,COUNT(source_quantity) AS known_quantity_rows,
       COALESCE(COUNT_IF(source_quantity IS NULL),0) AS missing_quantity_rows,SUM(source_quantity) AS missing_quantity,
       COALESCE(COUNT_IF(LOWER(COALESCE(raw_state,'')) IN ('inactive','1')),0) AS inactive_rows,
       COALESCE(COUNT_IF(VALIDATION_STATUS<>'READY'),0) AS pending_rejected_rows
FROM quota_trace WHERE core_rows=0 GROUP BY 1,2,3,4,5 ORDER BY 1,2,4;

-- Uniqueness/completeness guard: MUST inspect; duplicate counts are not silently resolved.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), quota_raw AS (
 SELECT r.*,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR) END) AS original_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR) END AS initial_flag,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR) END) AS owner_registration_id,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR) END,38,6) AS source_quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR) END,10)) AS source_date,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR) END,10)) AS source_end_date,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR) END AS credit_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR) END AS reserve_quota,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR) END AS related_transaction_guid,
        IFF(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END IN
            ('National Allocation','Provincial Allocation'),TRUE,FALSE) AS excluded_allocation
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_quotatransactions.csv'
), quota_registration AS (
 SELECT LOWER(TRIM(QUOTA_ID)) AS quota_id,COUNT(*) AS registration_rows,
        IFF(COUNT(*)=1,MIN(LOWER(TRIM(ACCOUNT_ID))),NULL) AS owner_account_id,
        IFF(COUNT(*)=1,MIN(QUOTA_TYPE),NULL) AS quota_type,
        MIN(STATUS) AS registration_status,MIN(END_DATE) AS registration_end_date
 FROM EFNS_DEV.CORE.QUOTA_REGISTRATION GROUP BY 1
), quota_core_matches AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,COUNT(c.QUOTA_TRANSACTION_ID) AS core_rows,
        COUNT(DISTINCT LOWER(c.QUOTA_TRANSACTION_ID)) AS core_target_ids,
        IFF(COUNT(c.QUOTA_TRANSACTION_ID)=1,MIN(c.QUOTA_TRANSACTION_ID),NULL) AS core_target_id
 FROM quota_raw r LEFT JOIN EFNS_DEV.CORE.QUOTA_TRANSACTION c
 ON LOWER(TRIM(c.QUOTA_TRANSACTION_ID)) IN (r.source_guid,r.target_guid,r.map_target,r.original_guid)
 GROUP BY 1,2
), quota_trace AS (
 SELECT r.*,c.core_rows,c.core_target_ids,c.core_target_id,
        q.owner_account_id,q.quota_type,q.registration_rows,q.registration_status,q.registration_end_date
 FROM quota_raw r JOIN quota_core_matches c
 ON c.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND c.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
 LEFT JOIN quota_registration q ON q.quota_id=r.owner_registration_id
)
SELECT MIGRATION_BATCH_ID,MIGRATION_RAW_ROW_ID,original_guid,map_rows,map_target_count,core_rows,registration_rows
FROM quota_trace WHERE COALESCE(map_rows,0)>1 OR COALESCE(map_target_count,0)>1 OR core_rows>1 OR COALESCE(registration_rows,0)>1;

-- T1a full per-Flock comparison; original rollup is reference ONLY. Inactive transactions excluded.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), flock_raw AS (
 SELECT r.*,LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR) END) AS flock_guid,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR) END,38,6) AS old_system_reference,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR) END AS old_reference_date_raw,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR) END AS old_rollup_state,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR) END AS permit_active,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR) END AS source_actual_disposal_raw
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocks.csv'
), flock_core AS (
 SELECT LOWER(FLOCK_ID) AS flock_guid,COUNT(*) AS core_rows,
        IFF(COUNT(*)=1,MIN(BIRD_COUNT),NULL) AS core_bird_count,
        IFF(COUNT(*)=1,MIN(DISPOSAL_DATE),NULL) AS core_actual_disposal,
        IFF(COUNT(*)=1,MIN(STATUS),NULL) AS core_record_status
 FROM EFNS_DEV.CORE.FLOCK GROUP BY 1
), flock_tx AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,r.SOURCE_ROW_NUMBER,r.SOURCE_ID,r.TARGET_ID,
        r.source_guid,r.target_guid,r.map_target,r.map_target_count,r.raw_state,
        r.VALIDATION_STATUS,r.VALIDATION_MESSAGES,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR) END) AS original_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR) END) AS flock_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR) END AS count_source,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR) END,38,6) AS quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DATE::VARCHAR) END,10)) AS source_date
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocktransaction.csv'
), eligible_tx AS (
 SELECT t.* FROM flock_tx t CROSS JOIN scope s
 WHERE LOWER(COALESCE(t.raw_state,'')) NOT IN ('inactive','1') AND t.source_date<=s.as_of_date
), count_days AS (
 SELECT flock_guid,source_date,
        COUNT(DISTINCT COALESCE(count_source,'[unknown]')) AS count_sources,
        COUNT(DISTINCT quantity) AS quantities,
        COALESCE(COUNT_IF(quantity IS NULL),0) AS missing_quantities,
        MIN(quantity) AS min_count,
        ARRAY_AGG(OBJECT_CONSTRUCT_KEEP_NULL('transaction_guid',original_guid,'source',count_source,'quantity',quantity)) AS observations
 FROM eligible_tx WHERE source_type='Count' GROUP BY 1,2
), latest_count AS (
 SELECT * FROM count_days
 QUALIFY ROW_NUMBER() OVER (PARTITION BY flock_guid ORDER BY source_date DESC)=1
), tx_totals AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(source_type='Delivery'),0) AS delivery_rows,
        COALESCE(COUNT_IF(source_type='Removal'),0) AS removal_rows,COALESCE(COUNT_IF(source_type='Sale'),0) AS sale_rows,
        SUM(IFF(source_type='Delivery',quantity,NULL)) AS delivery_sum,
        SUM(IFF(source_type='Removal',quantity,NULL)) AS removal_sum,
        SUM(IFF(source_type='Sale',quantity,NULL)) AS sale_sum,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale') AND quantity IS NULL),0) AS missing_event_qty,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale')),0) AS event_rows,
        SUM(CASE WHEN source_type='Delivery' THEN quantity WHEN source_type IN ('Removal','Sale') THEN -quantity END) AS signed_event_sum
 FROM eligible_tx t GROUP BY 1
), after_count AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(t.source_date=c.source_date AND t.source_type<>'Count'),0) AS same_day_activity,
        COALESCE(COUNT_IF(t.source_date>c.source_date AND t.quantity IS NULL AND t.source_type<>'Count'),0) AS after_missing_qty,
        COALESCE(SUM(CASE WHEN t.source_date>c.source_date AND t.source_type='Delivery' THEN t.quantity
                         WHEN t.source_date>c.source_date AND t.source_type IN ('Removal','Sale') THEN -t.quantity END),0) AS later_signed_changes
 FROM eligible_tx t JOIN latest_count c ON t.flock_guid=c.flock_guid GROUP BY 1
), source_quality AS (
 SELECT flock_guid,COALESCE(COUNT_IF(LOWER(COALESCE(raw_state,'')) IN ('inactive','1')),0) AS inactive_rows,
        COALESCE(COUNT_IF(source_date IS NULL),0) AS unknown_date_rows
 FROM flock_tx GROUP BY 1
), source_counts AS (
 SELECT flock_guid,COUNT(*) AS raw_flock_rows FROM flock_raw GROUP BY 1
), reconciliation AS (
 SELECT f.MIGRATION_BATCH_ID,f.MIGRATION_RAW_ROW_ID,f.flock_guid,f.permit_active,
        f.old_system_reference,f.old_reference_date_raw,f.old_rollup_state,f.source_actual_disposal_raw,
        c.core_bird_count,c.core_rows,c.core_record_status,
        (c.core_actual_disposal IS NOT NULL) AS has_disposal_date,
        sc.raw_flock_rows,lc.source_date AS latest_count_date,lc.observations AS latest_counts_by_source,
        COALESCE(lc.count_sources>1 OR lc.quantities>1 OR lc.missing_quantities>0,FALSE) AS latest_count_conflict,
        (SELECT COUNT(*) FROM count_days d WHERE d.flock_guid=f.flock_guid AND d.count_sources>1) AS multi_source_conflict_days,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0,lc.min_count,NULL) AS latest_count,
        t.delivery_rows,t.removal_rows,t.sale_rows,t.delivery_sum,t.removal_sum,t.sale_sum,
        IFF(t.missing_event_qty=0,t.signed_event_sum,NULL) AS event_candidate_unconfirmed,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0 AND a.same_day_activity=0
            AND a.after_missing_qty=0,lc.min_count+a.later_signed_changes,NULL) AS count_plus_later_candidate_unconfirmed,
        q.inactive_rows,q.unknown_date_rows,
        'OBSERVATION/RECONCILIATION ONLY - NOT CURRENT STOCK' AS interpretation
 FROM flock_raw f LEFT JOIN flock_core c ON c.flock_guid IN (f.flock_guid,f.source_guid,f.target_guid,f.map_target)
 LEFT JOIN source_counts sc ON sc.flock_guid=f.flock_guid
 LEFT JOIN latest_count lc ON lc.flock_guid=f.flock_guid
 LEFT JOIN tx_totals t ON t.flock_guid=f.flock_guid
 LEFT JOIN after_count a ON a.flock_guid=f.flock_guid
 LEFT JOIN source_quality q ON q.flock_guid=f.flock_guid
)
SELECT * FROM reconciliation ORDER BY flock_guid;

-- T1a match counts (0 / within 1 percent / mismatch / unknown), split by permit and disposal.
-- Identity-duplicate Flocks are excluded from match bands, but retained in the full result.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), flock_raw AS (
 SELECT r.*,LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR) END) AS flock_guid,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR) END,38,6) AS old_system_reference,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR) END AS old_reference_date_raw,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR) END AS old_rollup_state,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR) END AS permit_active,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR) END AS source_actual_disposal_raw
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocks.csv'
), flock_core AS (
 SELECT LOWER(FLOCK_ID) AS flock_guid,COUNT(*) AS core_rows,
        IFF(COUNT(*)=1,MIN(BIRD_COUNT),NULL) AS core_bird_count,
        IFF(COUNT(*)=1,MIN(DISPOSAL_DATE),NULL) AS core_actual_disposal,
        IFF(COUNT(*)=1,MIN(STATUS),NULL) AS core_record_status
 FROM EFNS_DEV.CORE.FLOCK GROUP BY 1
), flock_tx AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,r.SOURCE_ROW_NUMBER,r.SOURCE_ID,r.TARGET_ID,
        r.source_guid,r.target_guid,r.map_target,r.map_target_count,r.raw_state,
        r.VALIDATION_STATUS,r.VALIDATION_MESSAGES,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR) END) AS original_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR) END) AS flock_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR) END AS count_source,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR) END,38,6) AS quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DATE::VARCHAR) END,10)) AS source_date
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocktransaction.csv'
), eligible_tx AS (
 SELECT t.* FROM flock_tx t CROSS JOIN scope s
 WHERE LOWER(COALESCE(t.raw_state,'')) NOT IN ('inactive','1') AND t.source_date<=s.as_of_date
), count_days AS (
 SELECT flock_guid,source_date,
        COUNT(DISTINCT COALESCE(count_source,'[unknown]')) AS count_sources,
        COUNT(DISTINCT quantity) AS quantities,
        COALESCE(COUNT_IF(quantity IS NULL),0) AS missing_quantities,
        MIN(quantity) AS min_count,
        ARRAY_AGG(OBJECT_CONSTRUCT_KEEP_NULL('transaction_guid',original_guid,'source',count_source,'quantity',quantity)) AS observations
 FROM eligible_tx WHERE source_type='Count' GROUP BY 1,2
), latest_count AS (
 SELECT * FROM count_days
 QUALIFY ROW_NUMBER() OVER (PARTITION BY flock_guid ORDER BY source_date DESC)=1
), tx_totals AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(source_type='Delivery'),0) AS delivery_rows,
        COALESCE(COUNT_IF(source_type='Removal'),0) AS removal_rows,COALESCE(COUNT_IF(source_type='Sale'),0) AS sale_rows,
        SUM(IFF(source_type='Delivery',quantity,NULL)) AS delivery_sum,
        SUM(IFF(source_type='Removal',quantity,NULL)) AS removal_sum,
        SUM(IFF(source_type='Sale',quantity,NULL)) AS sale_sum,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale') AND quantity IS NULL),0) AS missing_event_qty,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale')),0) AS event_rows,
        SUM(CASE WHEN source_type='Delivery' THEN quantity WHEN source_type IN ('Removal','Sale') THEN -quantity END) AS signed_event_sum
 FROM eligible_tx t GROUP BY 1
), after_count AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(t.source_date=c.source_date AND t.source_type<>'Count'),0) AS same_day_activity,
        COALESCE(COUNT_IF(t.source_date>c.source_date AND t.quantity IS NULL AND t.source_type<>'Count'),0) AS after_missing_qty,
        COALESCE(SUM(CASE WHEN t.source_date>c.source_date AND t.source_type='Delivery' THEN t.quantity
                         WHEN t.source_date>c.source_date AND t.source_type IN ('Removal','Sale') THEN -t.quantity END),0) AS later_signed_changes
 FROM eligible_tx t JOIN latest_count c ON t.flock_guid=c.flock_guid GROUP BY 1
), source_quality AS (
 SELECT flock_guid,COALESCE(COUNT_IF(LOWER(COALESCE(raw_state,'')) IN ('inactive','1')),0) AS inactive_rows,
        COALESCE(COUNT_IF(source_date IS NULL),0) AS unknown_date_rows
 FROM flock_tx GROUP BY 1
), source_counts AS (
 SELECT flock_guid,COUNT(*) AS raw_flock_rows FROM flock_raw GROUP BY 1
), reconciliation AS (
 SELECT f.MIGRATION_BATCH_ID,f.MIGRATION_RAW_ROW_ID,f.flock_guid,f.permit_active,
        f.old_system_reference,f.old_reference_date_raw,f.old_rollup_state,f.source_actual_disposal_raw,
        c.core_bird_count,c.core_rows,c.core_record_status,
        (c.core_actual_disposal IS NOT NULL) AS has_disposal_date,
        sc.raw_flock_rows,lc.source_date AS latest_count_date,lc.observations AS latest_counts_by_source,
        COALESCE(lc.count_sources>1 OR lc.quantities>1 OR lc.missing_quantities>0,FALSE) AS latest_count_conflict,
        (SELECT COUNT(*) FROM count_days d WHERE d.flock_guid=f.flock_guid AND d.count_sources>1) AS multi_source_conflict_days,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0,lc.min_count,NULL) AS latest_count,
        t.delivery_rows,t.removal_rows,t.sale_rows,t.delivery_sum,t.removal_sum,t.sale_sum,
        IFF(t.missing_event_qty=0,t.signed_event_sum,NULL) AS event_candidate_unconfirmed,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0 AND a.same_day_activity=0
            AND a.after_missing_qty=0,lc.min_count+a.later_signed_changes,NULL) AS count_plus_later_candidate_unconfirmed,
        q.inactive_rows,q.unknown_date_rows,
        'OBSERVATION/RECONCILIATION ONLY - NOT CURRENT STOCK' AS interpretation
 FROM flock_raw f LEFT JOIN flock_core c ON c.flock_guid IN (f.flock_guid,f.source_guid,f.target_guid,f.map_target)
 LEFT JOIN source_counts sc ON sc.flock_guid=f.flock_guid
 LEFT JOIN latest_count lc ON lc.flock_guid=f.flock_guid
 LEFT JOIN tx_totals t ON t.flock_guid=f.flock_guid
 LEFT JOIN after_count a ON a.flock_guid=f.flock_guid
 LEFT JOIN source_quality q ON q.flock_guid=f.flock_guid
), comparisons AS (
 SELECT r.*,v.value:metric::VARCHAR AS metric,TRY_TO_DECIMAL(v.value:quantity::VARCHAR,38,6) AS compared_quantity
 FROM reconciliation r,LATERAL FLATTEN(INPUT=>ARRAY_CONSTRUCT(
  OBJECT_CONSTRUCT_KEEP_NULL('metric','CORE BIRD_COUNT','quantity',core_bird_count),
  OBJECT_CONSTRUCT_KEEP_NULL('metric','Latest Count','quantity',latest_count),
  OBJECT_CONSTRUCT_KEEP_NULL('metric','Delivery - Removal - Sale','quantity',event_candidate_unconfirmed),
  OBJECT_CONSTRUCT_KEEP_NULL('metric','Count + later activity','quantity',count_plus_later_candidate_unconfirmed))) v
)
SELECT permit_active,has_disposal_date,metric,COUNT(*) AS source_flocks,
 COALESCE(COUNT_IF(old_system_reference IS NULL OR compared_quantity IS NULL),0) AS unknown,
 COALESCE(COUNT_IF(compared_quantity=old_system_reference),0) AS exact_match,
 COALESCE(COUNT_IF(compared_quantity<>old_system_reference AND ABS(compared_quantity-old_system_reference)<=ABS(old_system_reference)*0.01),0) AS within_one_percent_not_exact,
 COALESCE(COUNT_IF(ABS(compared_quantity-old_system_reference)>ABS(old_system_reference)*0.01),0) AS mismatch,
 SUM(multi_source_conflict_days) AS multi_source_conflict_days,
 COALESCE(COUNT_IF(core_rows IS NULL OR core_rows=0),0) AS missing_core_flocks
FROM comparisons WHERE raw_flock_rows=1 AND COALESCE(core_rows,0)<=1
GROUP BY 1,2,3 ORDER BY 1,2,3;

-- T1a 20 example IDs only, not names; no proof of business formula.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), flock_raw AS (
 SELECT r.*,LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR) END) AS flock_guid,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR) END,38,6) AS old_system_reference,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR) END AS old_reference_date_raw,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR) END AS old_rollup_state,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR) END AS permit_active,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR) END AS source_actual_disposal_raw
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocks.csv'
), flock_core AS (
 SELECT LOWER(FLOCK_ID) AS flock_guid,COUNT(*) AS core_rows,
        IFF(COUNT(*)=1,MIN(BIRD_COUNT),NULL) AS core_bird_count,
        IFF(COUNT(*)=1,MIN(DISPOSAL_DATE),NULL) AS core_actual_disposal,
        IFF(COUNT(*)=1,MIN(STATUS),NULL) AS core_record_status
 FROM EFNS_DEV.CORE.FLOCK GROUP BY 1
), flock_tx AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,r.SOURCE_ROW_NUMBER,r.SOURCE_ID,r.TARGET_ID,
        r.source_guid,r.target_guid,r.map_target,r.map_target_count,r.raw_state,
        r.VALIDATION_STATUS,r.VALIDATION_MESSAGES,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR) END) AS original_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR) END) AS flock_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR) END AS count_source,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR) END,38,6) AS quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DATE::VARCHAR) END,10)) AS source_date
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocktransaction.csv'
), eligible_tx AS (
 SELECT t.* FROM flock_tx t CROSS JOIN scope s
 WHERE LOWER(COALESCE(t.raw_state,'')) NOT IN ('inactive','1') AND t.source_date<=s.as_of_date
), count_days AS (
 SELECT flock_guid,source_date,
        COUNT(DISTINCT COALESCE(count_source,'[unknown]')) AS count_sources,
        COUNT(DISTINCT quantity) AS quantities,
        COALESCE(COUNT_IF(quantity IS NULL),0) AS missing_quantities,
        MIN(quantity) AS min_count,
        ARRAY_AGG(OBJECT_CONSTRUCT_KEEP_NULL('transaction_guid',original_guid,'source',count_source,'quantity',quantity)) AS observations
 FROM eligible_tx WHERE source_type='Count' GROUP BY 1,2
), latest_count AS (
 SELECT * FROM count_days
 QUALIFY ROW_NUMBER() OVER (PARTITION BY flock_guid ORDER BY source_date DESC)=1
), tx_totals AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(source_type='Delivery'),0) AS delivery_rows,
        COALESCE(COUNT_IF(source_type='Removal'),0) AS removal_rows,COALESCE(COUNT_IF(source_type='Sale'),0) AS sale_rows,
        SUM(IFF(source_type='Delivery',quantity,NULL)) AS delivery_sum,
        SUM(IFF(source_type='Removal',quantity,NULL)) AS removal_sum,
        SUM(IFF(source_type='Sale',quantity,NULL)) AS sale_sum,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale') AND quantity IS NULL),0) AS missing_event_qty,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale')),0) AS event_rows,
        SUM(CASE WHEN source_type='Delivery' THEN quantity WHEN source_type IN ('Removal','Sale') THEN -quantity END) AS signed_event_sum
 FROM eligible_tx t GROUP BY 1
), after_count AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(t.source_date=c.source_date AND t.source_type<>'Count'),0) AS same_day_activity,
        COALESCE(COUNT_IF(t.source_date>c.source_date AND t.quantity IS NULL AND t.source_type<>'Count'),0) AS after_missing_qty,
        COALESCE(SUM(CASE WHEN t.source_date>c.source_date AND t.source_type='Delivery' THEN t.quantity
                         WHEN t.source_date>c.source_date AND t.source_type IN ('Removal','Sale') THEN -t.quantity END),0) AS later_signed_changes
 FROM eligible_tx t JOIN latest_count c ON t.flock_guid=c.flock_guid GROUP BY 1
), source_quality AS (
 SELECT flock_guid,COALESCE(COUNT_IF(LOWER(COALESCE(raw_state,'')) IN ('inactive','1')),0) AS inactive_rows,
        COALESCE(COUNT_IF(source_date IS NULL),0) AS unknown_date_rows
 FROM flock_tx GROUP BY 1
), source_counts AS (
 SELECT flock_guid,COUNT(*) AS raw_flock_rows FROM flock_raw GROUP BY 1
), reconciliation AS (
 SELECT f.MIGRATION_BATCH_ID,f.MIGRATION_RAW_ROW_ID,f.flock_guid,f.permit_active,
        f.old_system_reference,f.old_reference_date_raw,f.old_rollup_state,f.source_actual_disposal_raw,
        c.core_bird_count,c.core_rows,c.core_record_status,
        (c.core_actual_disposal IS NOT NULL) AS has_disposal_date,
        sc.raw_flock_rows,lc.source_date AS latest_count_date,lc.observations AS latest_counts_by_source,
        COALESCE(lc.count_sources>1 OR lc.quantities>1 OR lc.missing_quantities>0,FALSE) AS latest_count_conflict,
        (SELECT COUNT(*) FROM count_days d WHERE d.flock_guid=f.flock_guid AND d.count_sources>1) AS multi_source_conflict_days,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0,lc.min_count,NULL) AS latest_count,
        t.delivery_rows,t.removal_rows,t.sale_rows,t.delivery_sum,t.removal_sum,t.sale_sum,
        IFF(t.missing_event_qty=0,t.signed_event_sum,NULL) AS event_candidate_unconfirmed,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0 AND a.same_day_activity=0
            AND a.after_missing_qty=0,lc.min_count+a.later_signed_changes,NULL) AS count_plus_later_candidate_unconfirmed,
        q.inactive_rows,q.unknown_date_rows,
        'OBSERVATION/RECONCILIATION ONLY - NOT CURRENT STOCK' AS interpretation
 FROM flock_raw f LEFT JOIN flock_core c ON c.flock_guid IN (f.flock_guid,f.source_guid,f.target_guid,f.map_target)
 LEFT JOIN source_counts sc ON sc.flock_guid=f.flock_guid
 LEFT JOIN latest_count lc ON lc.flock_guid=f.flock_guid
 LEFT JOIN tx_totals t ON t.flock_guid=f.flock_guid
 LEFT JOIN after_count a ON a.flock_guid=f.flock_guid
 LEFT JOIN source_quality q ON q.flock_guid=f.flock_guid
)
SELECT DISTINCT flock_guid FROM reconciliation
WHERE core_bird_count<>old_system_reference OR event_candidate_unconfirmed<>old_system_reference
 OR latest_count_conflict OR multi_source_conflict_days>0
ORDER BY flock_guid LIMIT 20;

-- T1b repeated Delivery values are review candidates, NOT confirmed duplicate observations.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), flock_raw AS (
 SELECT r.*,LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR) END) AS flock_guid,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR) END,38,6) AS old_system_reference,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR) END AS old_reference_date_raw,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR) END AS old_rollup_state,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR) END AS permit_active,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR) END AS source_actual_disposal_raw
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocks.csv'
), flock_core AS (
 SELECT LOWER(FLOCK_ID) AS flock_guid,COUNT(*) AS core_rows,
        IFF(COUNT(*)=1,MIN(BIRD_COUNT),NULL) AS core_bird_count,
        IFF(COUNT(*)=1,MIN(DISPOSAL_DATE),NULL) AS core_actual_disposal,
        IFF(COUNT(*)=1,MIN(STATUS),NULL) AS core_record_status
 FROM EFNS_DEV.CORE.FLOCK GROUP BY 1
), flock_tx AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,r.SOURCE_ROW_NUMBER,r.SOURCE_ID,r.TARGET_ID,
        r.source_guid,r.target_guid,r.map_target,r.map_target_count,r.raw_state,
        r.VALIDATION_STATUS,r.VALIDATION_MESSAGES,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR) END) AS original_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR) END) AS flock_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR) END AS count_source,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR) END,38,6) AS quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DATE::VARCHAR) END,10)) AS source_date
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocktransaction.csv'
), eligible_tx AS (
 SELECT t.* FROM flock_tx t CROSS JOIN scope s
 WHERE LOWER(COALESCE(t.raw_state,'')) NOT IN ('inactive','1') AND t.source_date<=s.as_of_date
), count_days AS (
 SELECT flock_guid,source_date,
        COUNT(DISTINCT COALESCE(count_source,'[unknown]')) AS count_sources,
        COUNT(DISTINCT quantity) AS quantities,
        COALESCE(COUNT_IF(quantity IS NULL),0) AS missing_quantities,
        MIN(quantity) AS min_count,
        ARRAY_AGG(OBJECT_CONSTRUCT_KEEP_NULL('transaction_guid',original_guid,'source',count_source,'quantity',quantity)) AS observations
 FROM eligible_tx WHERE source_type='Count' GROUP BY 1,2
), latest_count AS (
 SELECT * FROM count_days
 QUALIFY ROW_NUMBER() OVER (PARTITION BY flock_guid ORDER BY source_date DESC)=1
), tx_totals AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(source_type='Delivery'),0) AS delivery_rows,
        COALESCE(COUNT_IF(source_type='Removal'),0) AS removal_rows,COALESCE(COUNT_IF(source_type='Sale'),0) AS sale_rows,
        SUM(IFF(source_type='Delivery',quantity,NULL)) AS delivery_sum,
        SUM(IFF(source_type='Removal',quantity,NULL)) AS removal_sum,
        SUM(IFF(source_type='Sale',quantity,NULL)) AS sale_sum,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale') AND quantity IS NULL),0) AS missing_event_qty,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale')),0) AS event_rows,
        SUM(CASE WHEN source_type='Delivery' THEN quantity WHEN source_type IN ('Removal','Sale') THEN -quantity END) AS signed_event_sum
 FROM eligible_tx t GROUP BY 1
), after_count AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(t.source_date=c.source_date AND t.source_type<>'Count'),0) AS same_day_activity,
        COALESCE(COUNT_IF(t.source_date>c.source_date AND t.quantity IS NULL AND t.source_type<>'Count'),0) AS after_missing_qty,
        COALESCE(SUM(CASE WHEN t.source_date>c.source_date AND t.source_type='Delivery' THEN t.quantity
                         WHEN t.source_date>c.source_date AND t.source_type IN ('Removal','Sale') THEN -t.quantity END),0) AS later_signed_changes
 FROM eligible_tx t JOIN latest_count c ON t.flock_guid=c.flock_guid GROUP BY 1
), source_quality AS (
 SELECT flock_guid,COALESCE(COUNT_IF(LOWER(COALESCE(raw_state,'')) IN ('inactive','1')),0) AS inactive_rows,
        COALESCE(COUNT_IF(source_date IS NULL),0) AS unknown_date_rows
 FROM flock_tx GROUP BY 1
), source_counts AS (
 SELECT flock_guid,COUNT(*) AS raw_flock_rows FROM flock_raw GROUP BY 1
), reconciliation AS (
 SELECT f.MIGRATION_BATCH_ID,f.MIGRATION_RAW_ROW_ID,f.flock_guid,f.permit_active,
        f.old_system_reference,f.old_reference_date_raw,f.old_rollup_state,f.source_actual_disposal_raw,
        c.core_bird_count,c.core_rows,c.core_record_status,
        (c.core_actual_disposal IS NOT NULL) AS has_disposal_date,
        sc.raw_flock_rows,lc.source_date AS latest_count_date,lc.observations AS latest_counts_by_source,
        COALESCE(lc.count_sources>1 OR lc.quantities>1 OR lc.missing_quantities>0,FALSE) AS latest_count_conflict,
        (SELECT COUNT(*) FROM count_days d WHERE d.flock_guid=f.flock_guid AND d.count_sources>1) AS multi_source_conflict_days,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0,lc.min_count,NULL) AS latest_count,
        t.delivery_rows,t.removal_rows,t.sale_rows,t.delivery_sum,t.removal_sum,t.sale_sum,
        IFF(t.missing_event_qty=0,t.signed_event_sum,NULL) AS event_candidate_unconfirmed,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0 AND a.same_day_activity=0
            AND a.after_missing_qty=0,lc.min_count+a.later_signed_changes,NULL) AS count_plus_later_candidate_unconfirmed,
        q.inactive_rows,q.unknown_date_rows,
        'OBSERVATION/RECONCILIATION ONLY - NOT CURRENT STOCK' AS interpretation
 FROM flock_raw f LEFT JOIN flock_core c ON c.flock_guid IN (f.flock_guid,f.source_guid,f.target_guid,f.map_target)
 LEFT JOIN source_counts sc ON sc.flock_guid=f.flock_guid
 LEFT JOIN latest_count lc ON lc.flock_guid=f.flock_guid
 LEFT JOIN tx_totals t ON t.flock_guid=f.flock_guid
 LEFT JOIN after_count a ON a.flock_guid=f.flock_guid
 LEFT JOIN source_quality q ON q.flock_guid=f.flock_guid
)
SELECT t.flock_guid,COUNT(*) AS delivery_rows,
       COALESCE(COUNT_IF(t.quantity=c.core_bird_count),0) AS deliveries_equal_core_bird_count,
       ARRAY_AGG(t.original_guid) AS delivery_guids
FROM eligible_tx t LEFT JOIN flock_core c ON c.flock_guid=t.flock_guid
WHERE t.source_type='Delivery' GROUP BY 1 HAVING COUNT(*)>1 ORDER BY 2 DESC,1;

-- T1c source-owned components; same original scope, no generated/sample rows.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), quota_raw AS (
 SELECT r.*,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR) END) AS original_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR) END AS initial_flag,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR) END) AS owner_registration_id,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR) END,38,6) AS source_quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR) END,10)) AS source_date,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR) END,10)) AS source_end_date,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR) END AS credit_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR) END AS reserve_quota,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR) END AS related_transaction_guid,
        IFF(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END IN
            ('National Allocation','Provincial Allocation'),TRUE,FALSE) AS excluded_allocation
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_quotatransactions.csv'
), quota_registration AS (
 SELECT LOWER(TRIM(QUOTA_ID)) AS quota_id,COUNT(*) AS registration_rows,
        IFF(COUNT(*)=1,MIN(LOWER(TRIM(ACCOUNT_ID))),NULL) AS owner_account_id,
        IFF(COUNT(*)=1,MIN(QUOTA_TYPE),NULL) AS quota_type,
        MIN(STATUS) AS registration_status,MIN(END_DATE) AS registration_end_date
 FROM EFNS_DEV.CORE.QUOTA_REGISTRATION GROUP BY 1
), quota_core_matches AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,COUNT(c.QUOTA_TRANSACTION_ID) AS core_rows,
        COUNT(DISTINCT LOWER(c.QUOTA_TRANSACTION_ID)) AS core_target_ids,
        IFF(COUNT(c.QUOTA_TRANSACTION_ID)=1,MIN(c.QUOTA_TRANSACTION_ID),NULL) AS core_target_id
 FROM quota_raw r LEFT JOIN EFNS_DEV.CORE.QUOTA_TRANSACTION c
 ON LOWER(TRIM(c.QUOTA_TRANSACTION_ID)) IN (r.source_guid,r.target_guid,r.map_target,r.original_guid)
 GROUP BY 1,2
), quota_trace AS (
 SELECT r.*,c.core_rows,c.core_target_ids,c.core_target_id,
        q.owner_account_id,q.quota_type,q.registration_rows,q.registration_status,q.registration_end_date
 FROM quota_raw r JOIN quota_core_matches c
 ON c.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND c.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
 LEFT JOIN quota_registration q ON q.quota_id=r.owner_registration_id
), components AS (
 SELECT q.*,
        (source_type IN ('Lease (In)','Lease (Out)')) AS is_lease,
        IFF(source_date<=s.as_of_date AND source_end_date>=s.as_of_date,TRUE,FALSE) AS lease_active,
        CASE source_type WHEN 'Base' THEN source_quantity WHEN 'Adjustment' THEN source_quantity
         WHEN 'Global Adjustment' THEN source_quantity WHEN 'Purchase' THEN source_quantity
         WHEN 'Sale' THEN -source_quantity
         WHEN 'Lease (In)' THEN IFF(lease_active,source_quantity,0)
         WHEN 'Lease (Out)' THEN IFF(lease_active,-source_quantity,0) END AS signed_candidate
 FROM quota_trace q CROSS JOIN scope s
 WHERE NOT excluded_allocation AND (source_date<=s.as_of_date OR source_date IS NULL)
)
SELECT owner_account_id,quota_type,source_type,COUNT(*) AS raw_rows,
 COALESCE(COUNT_IF(core_rows=0),0) AS source_rows_not_in_core,COALESCE(COUNT_IF(VALIDATION_STATUS<>'READY'),0) AS original_validation_not_ready,
 COALESCE(COUNT_IF(LOWER(COALESCE(raw_state,'')) IN ('inactive','1')),0) AS inactive_blockers,
 COALESCE(COUNT_IF(is_lease AND lease_active),0) AS active_lease_rows,SUM(source_quantity) AS recorded_source_quantity,
 SUM(IFF(core_rows=1 AND LOWER(COALESCE(raw_state,'')) NOT IN ('inactive','1'),signed_candidate,NULL)) AS candidate_component_unconfirmed,
 'CANDIDATE - UNCONFIRMED; not account entitlement. Missing unknown-owner rows block attribution; no UI position.' AS warning
FROM components GROUP BY 1,2,3 ORDER BY 1,2,3;

-- T1d Terminate Quota: zero does not establish cancellation or its effect.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), quota_raw AS (
 SELECT r.*,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR) END) AS original_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR) END AS initial_flag,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR) END) AS owner_registration_id,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR) END,38,6) AS source_quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR) END,10)) AS source_date,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR) END,10)) AS source_end_date,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR) END AS credit_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR) END AS reserve_quota,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR) END AS related_transaction_guid,
        IFF(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END IN
            ('National Allocation','Provincial Allocation'),TRUE,FALSE) AS excluded_allocation
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_quotatransactions.csv'
), quota_registration AS (
 SELECT LOWER(TRIM(QUOTA_ID)) AS quota_id,COUNT(*) AS registration_rows,
        IFF(COUNT(*)=1,MIN(LOWER(TRIM(ACCOUNT_ID))),NULL) AS owner_account_id,
        IFF(COUNT(*)=1,MIN(QUOTA_TYPE),NULL) AS quota_type,
        MIN(STATUS) AS registration_status,MIN(END_DATE) AS registration_end_date
 FROM EFNS_DEV.CORE.QUOTA_REGISTRATION GROUP BY 1
), quota_core_matches AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,COUNT(c.QUOTA_TRANSACTION_ID) AS core_rows,
        COUNT(DISTINCT LOWER(c.QUOTA_TRANSACTION_ID)) AS core_target_ids,
        IFF(COUNT(c.QUOTA_TRANSACTION_ID)=1,MIN(c.QUOTA_TRANSACTION_ID),NULL) AS core_target_id
 FROM quota_raw r LEFT JOIN EFNS_DEV.CORE.QUOTA_TRANSACTION c
 ON LOWER(TRIM(c.QUOTA_TRANSACTION_ID)) IN (r.source_guid,r.target_guid,r.map_target,r.original_guid)
 GROUP BY 1,2
), quota_trace AS (
 SELECT r.*,c.core_rows,c.core_target_ids,c.core_target_id,
        q.owner_account_id,q.quota_type,q.registration_rows,q.registration_status,q.registration_end_date
 FROM quota_raw r JOIN quota_core_matches c
 ON c.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND c.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
 LEFT JOIN quota_registration q ON q.quota_id=r.owner_registration_id
)
SELECT original_guid,owner_registration_id,owner_account_id,source_date,source_end_date,source_quantity,
       registration_status,registration_end_date,core_target_id,raw_state,VALIDATION_STATUS
FROM quota_trace WHERE source_type='Terminate Quota' ORDER BY source_date,original_guid;

-- T1f Inactive quota transactions, actual CORE presence and original owner identity.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), quota_raw AS (
 SELECT r.*,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR) END) AS original_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR) END AS initial_flag,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR) END) AS owner_registration_id,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR) END,38,6) AS source_quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR) END,10)) AS source_date,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR) END,10)) AS source_end_date,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR) END AS credit_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR) END AS reserve_quota,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR) END AS related_transaction_guid,
        IFF(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END IN
            ('National Allocation','Provincial Allocation'),TRUE,FALSE) AS excluded_allocation
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_quotatransactions.csv'
), quota_registration AS (
 SELECT LOWER(TRIM(QUOTA_ID)) AS quota_id,COUNT(*) AS registration_rows,
        IFF(COUNT(*)=1,MIN(LOWER(TRIM(ACCOUNT_ID))),NULL) AS owner_account_id,
        IFF(COUNT(*)=1,MIN(QUOTA_TYPE),NULL) AS quota_type,
        MIN(STATUS) AS registration_status,MIN(END_DATE) AS registration_end_date
 FROM EFNS_DEV.CORE.QUOTA_REGISTRATION GROUP BY 1
), quota_core_matches AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,COUNT(c.QUOTA_TRANSACTION_ID) AS core_rows,
        COUNT(DISTINCT LOWER(c.QUOTA_TRANSACTION_ID)) AS core_target_ids,
        IFF(COUNT(c.QUOTA_TRANSACTION_ID)=1,MIN(c.QUOTA_TRANSACTION_ID),NULL) AS core_target_id
 FROM quota_raw r LEFT JOIN EFNS_DEV.CORE.QUOTA_TRANSACTION c
 ON LOWER(TRIM(c.QUOTA_TRANSACTION_ID)) IN (r.source_guid,r.target_guid,r.map_target,r.original_guid)
 GROUP BY 1,2
), quota_trace AS (
 SELECT r.*,c.core_rows,c.core_target_ids,c.core_target_id,
        q.owner_account_id,q.quota_type,q.registration_rows,q.registration_status,q.registration_end_date
 FROM quota_raw r JOIN quota_core_matches c
 ON c.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND c.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
 LEFT JOIN quota_registration q ON q.quota_id=r.owner_registration_id
)
SELECT MIGRATION_BATCH_ID,MIGRATION_RAW_ROW_ID,original_guid,source_type,source_quantity,
       owner_registration_id,owner_account_id,raw_state,core_rows,core_target_id,VALIDATION_STATUS,VALIDATION_MESSAGES
FROM quota_trace WHERE LOWER(raw_state) IN ('inactive','1') ORDER BY original_guid;

-- T1f Inactive Flock transactions, including rejected or unmapped sources.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), flock_raw AS (
 SELECT r.*,LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKSID::VARCHAR) END) AS flock_guid,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT::VARCHAR) END,38,6) AS old_system_reference,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_DATE::VARCHAR) END AS old_reference_date_raw,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_NETBIRDCOUNT_STATE::VARCHAR) END AS old_rollup_state,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_PERMITACTIVE_DISPLAYNAME::VARCHAR) END AS permit_active,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DISPOSALDATE::VARCHAR) END AS source_actual_disposal_raw
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocks.csv'
), flock_core AS (
 SELECT LOWER(FLOCK_ID) AS flock_guid,COUNT(*) AS core_rows,
        IFF(COUNT(*)=1,MIN(BIRD_COUNT),NULL) AS core_bird_count,
        IFF(COUNT(*)=1,MIN(DISPOSAL_DATE),NULL) AS core_actual_disposal,
        IFF(COUNT(*)=1,MIN(STATUS),NULL) AS core_record_status
 FROM EFNS_DEV.CORE.FLOCK GROUP BY 1
), flock_tx AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,r.SOURCE_ROW_NUMBER,r.SOURCE_ID,r.TARGET_ID,
        r.source_guid,r.target_guid,r.map_target,r.map_target_count,r.raw_state,
        r.VALIDATION_STATUS,r.VALIDATION_MESSAGES,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONID::VARCHAR) END) AS original_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKIDID::VARCHAR) END) AS flock_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_FLOCKTRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_FLOCKCOUNTTYPE_DISPLAYNAME::VARCHAR) END AS count_source,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_BIRDCOUNT::VARCHAR) END,38,6) AS quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_DATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_DATE::VARCHAR) END,10)) AS source_date
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_flocktransaction.csv'
), eligible_tx AS (
 SELECT t.* FROM flock_tx t CROSS JOIN scope s
 WHERE LOWER(COALESCE(t.raw_state,'')) NOT IN ('inactive','1') AND t.source_date<=s.as_of_date
), count_days AS (
 SELECT flock_guid,source_date,
        COUNT(DISTINCT COALESCE(count_source,'[unknown]')) AS count_sources,
        COUNT(DISTINCT quantity) AS quantities,
        COALESCE(COUNT_IF(quantity IS NULL),0) AS missing_quantities,
        MIN(quantity) AS min_count,
        ARRAY_AGG(OBJECT_CONSTRUCT_KEEP_NULL('transaction_guid',original_guid,'source',count_source,'quantity',quantity)) AS observations
 FROM eligible_tx WHERE source_type='Count' GROUP BY 1,2
), latest_count AS (
 SELECT * FROM count_days
 QUALIFY ROW_NUMBER() OVER (PARTITION BY flock_guid ORDER BY source_date DESC)=1
), tx_totals AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(source_type='Delivery'),0) AS delivery_rows,
        COALESCE(COUNT_IF(source_type='Removal'),0) AS removal_rows,COALESCE(COUNT_IF(source_type='Sale'),0) AS sale_rows,
        SUM(IFF(source_type='Delivery',quantity,NULL)) AS delivery_sum,
        SUM(IFF(source_type='Removal',quantity,NULL)) AS removal_sum,
        SUM(IFF(source_type='Sale',quantity,NULL)) AS sale_sum,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale') AND quantity IS NULL),0) AS missing_event_qty,
        COALESCE(COUNT_IF(source_type IN ('Delivery','Removal','Sale')),0) AS event_rows,
        SUM(CASE WHEN source_type='Delivery' THEN quantity WHEN source_type IN ('Removal','Sale') THEN -quantity END) AS signed_event_sum
 FROM eligible_tx t GROUP BY 1
), after_count AS (
 SELECT t.flock_guid,
        COALESCE(COUNT_IF(t.source_date=c.source_date AND t.source_type<>'Count'),0) AS same_day_activity,
        COALESCE(COUNT_IF(t.source_date>c.source_date AND t.quantity IS NULL AND t.source_type<>'Count'),0) AS after_missing_qty,
        COALESCE(SUM(CASE WHEN t.source_date>c.source_date AND t.source_type='Delivery' THEN t.quantity
                         WHEN t.source_date>c.source_date AND t.source_type IN ('Removal','Sale') THEN -t.quantity END),0) AS later_signed_changes
 FROM eligible_tx t JOIN latest_count c ON t.flock_guid=c.flock_guid GROUP BY 1
), source_quality AS (
 SELECT flock_guid,COALESCE(COUNT_IF(LOWER(COALESCE(raw_state,'')) IN ('inactive','1')),0) AS inactive_rows,
        COALESCE(COUNT_IF(source_date IS NULL),0) AS unknown_date_rows
 FROM flock_tx GROUP BY 1
), source_counts AS (
 SELECT flock_guid,COUNT(*) AS raw_flock_rows FROM flock_raw GROUP BY 1
), reconciliation AS (
 SELECT f.MIGRATION_BATCH_ID,f.MIGRATION_RAW_ROW_ID,f.flock_guid,f.permit_active,
        f.old_system_reference,f.old_reference_date_raw,f.old_rollup_state,f.source_actual_disposal_raw,
        c.core_bird_count,c.core_rows,c.core_record_status,
        (c.core_actual_disposal IS NOT NULL) AS has_disposal_date,
        sc.raw_flock_rows,lc.source_date AS latest_count_date,lc.observations AS latest_counts_by_source,
        COALESCE(lc.count_sources>1 OR lc.quantities>1 OR lc.missing_quantities>0,FALSE) AS latest_count_conflict,
        (SELECT COUNT(*) FROM count_days d WHERE d.flock_guid=f.flock_guid AND d.count_sources>1) AS multi_source_conflict_days,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0,lc.min_count,NULL) AS latest_count,
        t.delivery_rows,t.removal_rows,t.sale_rows,t.delivery_sum,t.removal_sum,t.sale_sum,
        IFF(t.missing_event_qty=0,t.signed_event_sum,NULL) AS event_candidate_unconfirmed,
        IFF(lc.count_sources=1 AND lc.quantities=1 AND lc.missing_quantities=0 AND a.same_day_activity=0
            AND a.after_missing_qty=0,lc.min_count+a.later_signed_changes,NULL) AS count_plus_later_candidate_unconfirmed,
        q.inactive_rows,q.unknown_date_rows,
        'OBSERVATION/RECONCILIATION ONLY - NOT CURRENT STOCK' AS interpretation
 FROM flock_raw f LEFT JOIN flock_core c ON c.flock_guid IN (f.flock_guid,f.source_guid,f.target_guid,f.map_target)
 LEFT JOIN source_counts sc ON sc.flock_guid=f.flock_guid
 LEFT JOIN latest_count lc ON lc.flock_guid=f.flock_guid
 LEFT JOIN tx_totals t ON t.flock_guid=f.flock_guid
 LEFT JOIN after_count a ON a.flock_guid=f.flock_guid
 LEFT JOIN source_quality q ON q.flock_guid=f.flock_guid
)
SELECT t.MIGRATION_BATCH_ID,t.MIGRATION_RAW_ROW_ID,t.original_guid,t.source_type,t.quantity,t.flock_guid,t.raw_state,
       COUNT(c.FLOCK_TRANSACTION_ID) AS core_rows,ARRAY_AGG(c.FLOCK_TRANSACTION_ID) AS core_target_ids,
       t.VALIDATION_STATUS,t.VALIDATION_MESSAGES
FROM flock_tx t LEFT JOIN EFNS_DEV.CORE.FLOCK_TRANSACTION c
 ON LOWER(TRIM(c.FLOCK_TRANSACTION_ID)) IN (t.source_guid,t.target_guid,t.map_target,t.original_guid)
WHERE LOWER(t.raw_state) IN ('inactive','1')
GROUP BY t.MIGRATION_BATCH_ID,t.MIGRATION_RAW_ROW_ID,t.original_guid,t.source_type,t.quantity,t.flock_guid,t.raw_state,t.VALIDATION_STATUS,t.VALIDATION_MESSAGES
ORDER BY t.original_guid;

-- T1c current CORE owner/type components over the original batch targets only.
-- Diagnostic candidate is NOT net_position; rules remain PENDING even with no gaps.
WITH scope AS (
 SELECT 'DEV_MIGRATION_255ef9b50a52e766a7dff9' AS batch_id,
        CURRENT_DATE() AS as_of_date
), id_map AS (
 SELECT m.MIGRATION_BATCH_ID,m.MIGRATION_RAW_ROW_ID,
        COUNT(*) AS map_rows,COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID))) AS map_target_count,
        IFF(COUNT(DISTINCT LOWER(TRIM(m.TARGET_ID)))=1,MIN(LOWER(TRIM(m.TARGET_ID))),NULL) AS map_target
 FROM EFNS_DEV.RAW.MIGRATION_ID_MAP m JOIN scope s ON m.MIGRATION_BATCH_ID=s.batch_id
 GROUP BY 1,2
), raw_base AS (
 SELECT r.*, m.map_rows,m.map_target_count,m.map_target,
        LOWER(CASE WHEN LOWER(TRIM(r.SOURCE_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.SOURCE_ID::VARCHAR) END) AS source_guid,
        LOWER(CASE WHEN LOWER(TRIM(r.TARGET_ID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.TARGET_ID::VARCHAR) END) AS target_guid,
        COALESCE(CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR) END,CASE WHEN LOWER(TRIM(r.RAW_DATA:STATECODE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:STATECODE::VARCHAR) END) AS raw_state
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW r JOIN scope s ON r.MIGRATION_BATCH_ID=s.batch_id
 LEFT JOIN id_map m ON m.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID
                   AND m.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
), quota_raw AS (
 SELECT r.*,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONSID::VARCHAR) END) AS original_guid,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END AS source_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_TRANSACTIONINITIALFLAG_DISPLAYNAME::VARCHAR) END AS initial_flag,
        LOWER(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSID::VARCHAR) END) AS owner_registration_id,
        TRY_TO_DECIMAL(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTACOUNT::VARCHAR) END,38,6) AS source_quantity,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_TRANSACTIONDATE::VARCHAR) END,10)) AS source_date,
        TRY_TO_DATE(LEFT(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_ENDDATE::VARCHAR) END,10)) AS source_end_date,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_CREDITTYPE_DISPLAYNAME::VARCHAR) END AS credit_type,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_RESERVEQUOTA::VARCHAR) END AS reserve_quota,
        CASE WHEN LOWER(TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:EFC_RELATEDTRANSACTION::VARCHAR) END AS related_transaction_guid,
        IFF(CASE WHEN LOWER(TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR)) IN ('', 'null', 'nan', 'none', 'nat', '<na>') THEN NULL ELSE TRIM(r.RAW_DATA:NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME::VARCHAR) END IN
            ('National Allocation','Provincial Allocation'),TRUE,FALSE) AS excluded_allocation
 FROM raw_base r WHERE LOWER(r.SOURCE_FILENAME)='new_quotatransactions.csv'
), quota_registration AS (
 SELECT LOWER(TRIM(QUOTA_ID)) AS quota_id,COUNT(*) AS registration_rows,
        IFF(COUNT(*)=1,MIN(LOWER(TRIM(ACCOUNT_ID))),NULL) AS owner_account_id,
        IFF(COUNT(*)=1,MIN(QUOTA_TYPE),NULL) AS quota_type,
        MIN(STATUS) AS registration_status,MIN(END_DATE) AS registration_end_date
 FROM EFNS_DEV.CORE.QUOTA_REGISTRATION GROUP BY 1
), quota_core_matches AS (
 SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,COUNT(c.QUOTA_TRANSACTION_ID) AS core_rows,
        COUNT(DISTINCT LOWER(c.QUOTA_TRANSACTION_ID)) AS core_target_ids,
        IFF(COUNT(c.QUOTA_TRANSACTION_ID)=1,MIN(c.QUOTA_TRANSACTION_ID),NULL) AS core_target_id
 FROM quota_raw r LEFT JOIN EFNS_DEV.CORE.QUOTA_TRANSACTION c
 ON LOWER(TRIM(c.QUOTA_TRANSACTION_ID)) IN (r.source_guid,r.target_guid,r.map_target,r.original_guid)
 GROUP BY 1,2
), quota_trace AS (
 SELECT r.*,c.core_rows,c.core_target_ids,c.core_target_id,
        q.owner_account_id,q.quota_type,q.registration_rows,q.registration_status,q.registration_end_date
 FROM quota_raw r JOIN quota_core_matches c
 ON c.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND c.MIGRATION_RAW_ROW_ID=r.MIGRATION_RAW_ROW_ID
 LEFT JOIN quota_registration q ON q.quota_id=r.owner_registration_id
), current_components AS (
 SELECT r.owner_account_id,r.quota_type,c.TRANSACTION_TYPE,
        COUNT(*) AS core_rows,SUM(c.QUOTA_COUNT) AS core_quantity,
        SUM(CASE
          WHEN c.TRANSACTION_TYPE IN ('Base','Adjustment','Global Adjustment','Purchase') THEN c.QUOTA_COUNT
          WHEN c.TRANSACTION_TYPE='Sale' THEN -c.QUOTA_COUNT
          WHEN c.TRANSACTION_TYPE='Lease (In)' AND c.END_DATE>=s.as_of_date THEN c.QUOTA_COUNT
          WHEN c.TRANSACTION_TYPE='Lease (Out)' AND c.END_DATE>=s.as_of_date THEN -c.QUOTA_COUNT
          WHEN c.TRANSACTION_TYPE IN ('Lease (In)','Lease (Out)') AND c.END_DATE<s.as_of_date THEN 0
        END) AS candidate_component_unconfirmed,
        COUNT(CASE WHEN c.TRANSACTION_TYPE IN ('Lease (In)','Lease (Out)') AND c.END_DATE IS NULL THEN 1 END) AS invalid_lease_rows,
        COUNT(CASE WHEN c.TRANSACTION_TYPE NOT IN ('Base','Adjustment','Global Adjustment','Purchase','Sale','Lease (In)','Lease (Out)') THEN 1 END) AS unknown_formula_rows
 FROM quota_trace r JOIN EFNS_DEV.CORE.QUOTA_TRANSACTION c ON c.QUOTA_TRANSACTION_ID=r.core_target_id
 CROSS JOIN scope s
 WHERE r.core_rows=1 AND r.registration_rows=1 AND NOT r.excluded_allocation
   AND LOWER(c.OWNER_ACCOUNT_ID)=r.owner_account_id AND LOWER(c.QUOTA_ID)=r.owner_registration_id
   AND LOWER(COALESCE(r.raw_state,'')) NOT IN ('inactive','1') AND c.EFFECTIVE_DATE<=s.as_of_date
   AND c.TRANSACTION_TYPE NOT IN ('National Allocation','Provincial Allocation')
 GROUP BY 1,2,3
), gaps AS (
 SELECT owner_account_id,quota_type,COUNT(CASE WHEN core_rows=0 THEN 1 END) AS missing_rows,
        COUNT(CASE WHEN LOWER(COALESCE(raw_state,'')) IN ('inactive','1') THEN 1 END) AS inactive_rows,
        COUNT(CASE WHEN core_rows>1 OR COALESCE(map_rows,0)>1 OR COALESCE(registration_rows,0)>1 THEN 1 END) AS identity_problems
 FROM quota_trace WHERE NOT excluded_allocation GROUP BY 1,2
)
SELECT c.*,g.missing_rows,g.inactive_rows,g.identity_problems,
       (SELECT COUNT(*) FROM quota_trace WHERE core_rows=0 AND NOT excluded_allocation AND owner_account_id IS NULL) AS unresolved_owner_gaps,
       NULL::NUMBER(38,6) AS net_position,
       'CANDIDATE - UNCONFIRMED. Missing/inactive/unattributed RAW rows block certification; no units/lifecycle rule inferred.' AS reason
FROM current_components c LEFT JOIN gaps g ON g.owner_account_id=c.owner_account_id AND g.quota_type=c.quota_type
ORDER BY 1,2,3;
