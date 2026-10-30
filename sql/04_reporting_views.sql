-- ============================================================
-- EFNS Internal Data System Prototype v0.1
-- 04_reporting_views.sql — Views for the Reporting Schema
-- ============================================================
-- PROVISIONAL
-- ============================================================

USE DATABASE EFNS_DEV;

-- -----------------------------------------------------------
-- VW_PRODUCTION_SUMMARY — flattened production for reporting
-- -----------------------------------------------------------
CREATE OR REPLACE VIEW EFNS_DEV.REPORTING.VW_PRODUCTION_SUMMARY COPY GRANTS AS
SELECT
    pr.PRODUCTION_ID,
    pr.IMPORT_ID,
    pr.SOURCE_FILE_ID,
    pr.RAW_ROW_ID,
    pr.MATCH_METHOD,
    pr.MATCH_BASIS,
    ib.FILENAME,
    ib.SOURCE,
    pr.REPORTING_YEAR,
    pr.REPORTING_WEEK,
    ib.UPLOAD_TIMESTAMP,
    pr.GRADER_NUMBER,
    pr.PRODUCER_NUMBER,
    pr.PRODUCER_ACCOUNT_ID,
    pr.GRADER_ACCOUNT_ID,
    pr.FACILITY_ID,
    pr.FLOCK_ID,
    pr.BARN_IDENTITY,
    pr.FLOCK_AGE,
    pr.EGG_COLOUR,
    pr.NET_WEIGHT,
    pr.NET_BOXES,
    pr.NET_PER_BOX,
    pr.TOTAL_RECEIVED,
    pr.REJECTED,
    pr.LOSS,
    pr.LEGACY_REJECT_LOSS_TOTAL,
    pr.TOTAL_ACCEPTED,
    pr.SOURCE_TYPE,
    pr.MATCH_STATUS,
    pr.SOURCE_ROW_NUMBER,
    pr.CREATED_AT,
    pr.UPDATED_AT,
    pr.TOTAL
FROM EFNS_DEV.CORE.PRODUCTION_RECORD pr
LEFT JOIN EFNS_DEV.RAW.IMPORT_BATCH ib ON pr.IMPORT_ID = ib.IMPORT_ID;

-- -----------------------------------------------------------
-- VW_PRODUCTION_SIZE_DETAIL — production with size breakdowns
-- -----------------------------------------------------------
CREATE OR REPLACE VIEW EFNS_DEV.REPORTING.VW_PRODUCTION_SIZE_DETAIL COPY GRANTS AS
SELECT
    pr.PRODUCTION_ID,
    pr.GRADER_NUMBER,
    pr.BARN_IDENTITY,
    pr.EGG_COLOUR,
    psb.SIZE_BREAKDOWN_ID,
    psb.SIZE_BAND,
    psb.QUANTITY,
    pr.REPORTING_YEAR,
    pr.REPORTING_WEEK
FROM EFNS_DEV.CORE.PRODUCTION_RECORD pr
LEFT JOIN EFNS_DEV.CORE.PRODUCTION_SIZE_BREAKDOWN psb ON pr.PRODUCTION_ID = psb.PRODUCTION_ID;

-- -----------------------------------------------------------
-- VW_ACCOUNT_FACILITY — Accounts with their facilities
-- -----------------------------------------------------------
CREATE OR REPLACE VIEW EFNS_DEV.REPORTING.VW_ACCOUNT_FACILITY COPY GRANTS AS
SELECT
    a.ACCOUNT_ID,
    a.REGISTRATION_NUMBER,
    a.ORGANIZATION_NAME,
    a.CITY,
    a.PROVINCE,
    a.CONTACT_NAME,
    a.CONTACT_PHONE,
    a.CONTACT_EMAIL,
    a.LICENCE_NUMBER,
    a.PRODUCER_ROLE,
    a.BREEDER_ROLE,
    a.HATCHERY_ROLE,
    a.GRADER_ROLE,
    a.STATUS          AS ACCOUNT_STATUS,
    f.FACILITY_ID,
    f.FACILITY_NAME,
    f.FACILITY_TYPE,
    f.STATUS          AS FACILITY_STATUS,
    f.ACTIVATION_DATE,
    f.CLOSURE_DATE
FROM EFNS_DEV.CORE.ACCOUNT a
LEFT JOIN EFNS_DEV.CORE.FACILITY f ON a.ACCOUNT_ID = f.ACCOUNT_ID;

-- -----------------------------------------------------------
-- VW_FLOCK_DETAIL — Flocks with account and facility info
-- -----------------------------------------------------------
CREATE OR REPLACE VIEW EFNS_DEV.REPORTING.VW_FLOCK_DETAIL COPY GRANTS AS
SELECT
    fl.FLOCK_ID,
    fl.FLOCK_NUMBER,
    fl.PERMIT_NUMBER,
    fl.PERMIT_DATE,
    fl.BIRD_COUNT,
    fl.PLACEMENT_DATE,
    fl.HATCH_DATE,
    fl.EGG_COLOUR,
    fl.EST_DISPOSAL,
    fl.DISPOSAL_DATE,
    fl.DISPOSAL_METHOD,
    fl.STATUS                AS FLOCK_STATUS,
    fl.ACCOUNT_ID,
    a.REGISTRATION_NUMBER,
    a.ORGANIZATION_NAME,
    fl.FACILITY_ID,
    f.FACILITY_NAME,
    f.FACILITY_TYPE,
    fl.ACCOUNT_ID            AS FLOCK_ACCOUNT_ID,
    a.ORGANIZATION_NAME      AS FLOCK_ACCOUNT_NAME,
    f.ACCOUNT_ID             AS FACILITY_ACCOUNT_ID,
    fa.ORGANIZATION_NAME     AS FACILITY_ACCOUNT_NAME
FROM EFNS_DEV.CORE.FLOCK fl
LEFT JOIN EFNS_DEV.CORE.ACCOUNT a ON fl.ACCOUNT_ID = a.ACCOUNT_ID
LEFT JOIN EFNS_DEV.CORE.FACILITY f ON fl.FACILITY_ID = f.FACILITY_ID
LEFT JOIN EFNS_DEV.CORE.ACCOUNT fa ON f.ACCOUNT_ID = fa.ACCOUNT_ID;

SELECT 'Reporting views created (PROVISIONAL).' AS status;
