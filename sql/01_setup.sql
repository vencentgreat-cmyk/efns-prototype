-- ============================================================
-- EFNS Internal Data System Prototype v0.1
-- 01_setup.sql — Database & Schema Creation
-- ============================================================
-- TARGET: Snowflake
-- PROVISIONAL: All schema is draft until Dataverse metadata is obtained.
-- ============================================================

USE ROLE SYSADMIN;

CREATE DATABASE IF NOT EXISTS EFNS_DEV
  COMMENT = 'EFNS Internal Data System — Development Environment';

CREATE SCHEMA IF NOT EXISTS EFNS_DEV.RAW
  COMMENT = 'Raw ingested data — source-preserving records';

CREATE SCHEMA IF NOT EXISTS EFNS_DEV.CORE
  COMMENT = 'Core operational and business entities';

CREATE SCHEMA IF NOT EXISTS EFNS_DEV.REPORTING
  COMMENT = 'Reporting views and report-ready datasets';

CREATE SCHEMA IF NOT EXISTS EFNS_DEV.SECURITY
  COMMENT = 'Application users and authorization';

CREATE SCHEMA IF NOT EXISTS EFNS_DEV.APP
  COMMENT = 'Application stages, audit events, and Streamlit object';

-- ============================================================
-- NOTE: The following USE statements are for context in scripts.
-- In Snowflake, schemas are fully qualified as DATABASE.SCHEMA.
-- ============================================================

SELECT 'EFNS schema setup ready. Run remaining .sql files in order.' AS status;
