-- ============================================================
-- EFNS Internal Data System Prototype v0.1
-- 01_setup.sql — Database & Schema Creation
-- ============================================================
-- TARGET: Snowflake
-- PROVISIONAL: All schema is draft until Dataverse metadata is obtained.
-- ============================================================

/*
  Run these commands manually or via Snowsight/SnowSQL
  before deploying the remaining SQL scripts.

-- Step 1: Create database (if not already present)
CREATE DATABASE IF NOT EXISTS EFNS_DEV
  COMMENT = 'EFNS Internal Data System — Development Environment';

-- Step 2: Create schemas
CREATE SCHEMA IF NOT EXISTS EFNS_DEV.RAW
  COMMENT = 'Raw ingested data — source-preserving records';

CREATE SCHEMA IF NOT EXISTS EFNS_DEV.CORE
  COMMENT = 'Core operational and business entities';

CREATE SCHEMA IF NOT EXISTS EFNS_DEV.REPORTING
  COMMENT = 'Reporting views and report-ready datasets';

-- Step 3: Create warehouse (optional, for dedicated compute)
CREATE WAREHOUSE IF NOT EXISTS EFNS_DEV_WH
  WITH WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 300
  AUTO_RESUME = TRUE
  COMMENT = 'EFNS development warehouse';
*/

-- ============================================================
-- NOTE: The following USE statements are for context in scripts.
-- In Snowflake, schemas are fully qualified as DATABASE.SCHEMA.
-- ============================================================

SELECT 'EFNS schema setup ready. Run remaining .sql files in order.' AS status;