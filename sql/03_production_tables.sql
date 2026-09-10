-- ============================================================
-- EFNS Internal Data System Prototype v0.1
-- 03_production_tables.sql — Production & Ingestion
-- ============================================================
-- PROVISIONAL MODEL
-- ============================================================

USE DATABASE EFNS_DEV;

-- ============================================================
-- IMPORT_BATCH — metadata for each CSV import
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.RAW.IMPORT_BATCH (
    IMPORT_ID       VARCHAR(36)    NOT NULL,
    FILENAME        VARCHAR(500)   NOT NULL,
    SOURCE          VARCHAR(255),               -- e.g. grader name / farm
    REPORTING_YEAR  INTEGER,
    REPORTING_WEEK  INTEGER,
    UPLOAD_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    STATUS          VARCHAR(50)    DEFAULT 'Uploaded',  -- Uploaded | Validated | Committed | Error
    ROW_COUNT       INTEGER,
    ERROR_COUNT     INTEGER,
    NOTES           VARCHAR(1000),
    CONSTRAINT PK_IMPORT_BATCH PRIMARY KEY (IMPORT_ID)
)
COMMENT = 'Import metadata — one row per uploaded CSV file.';

-- ============================================================
-- IMPORT_RAW_ROW — source-preserving raw rows
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.RAW.IMPORT_RAW_ROW (
    RAW_ROW_ID      VARCHAR(36)    NOT NULL,
    IMPORT_ID       VARCHAR(36)    NOT NULL,
    ROW_NUMBER      INTEGER,                   -- line number in source CSV
    RAW_DATA        VARIANT,                   -- full row as JSON (flexible schema)
    CONSTRAINT PK_IMPORT_RAW_ROW PRIMARY KEY (RAW_ROW_ID),
    CONSTRAINT FK_RAW_ROW_IMPORT
        FOREIGN KEY (IMPORT_ID) REFERENCES EFNS_DEV.RAW.IMPORT_BATCH (IMPORT_ID)
)
COMMENT = 'Source-preserving raw CSV rows stored as VARIANT (JSON).';

-- ============================================================
-- PRODUCTION_RECORD — normalized production row
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.CORE.PRODUCTION_RECORD (
    PRODUCTION_ID           VARCHAR(36)    NOT NULL,
    IMPORT_ID               VARCHAR(36)    NOT NULL,
    FLOCK_ID                VARCHAR(36),               -- PROVISIONAL link to FLOCK (unconfirmed)
    GRADER_NUMBER           VARCHAR(50),
    BARN_IDENTITY           VARCHAR(100),
    FLOCK_AGE               INTEGER,               -- age in weeks
    EGG_COLOUR              VARCHAR(50),
    NET_WEIGHT              NUMBER(12, 4),
    NET_BOXES               NUMBER(12, 4),
    NET_PER_BOX             NUMBER(12, 4),
    TOTAL_RECEIVED          NUMBER(12, 4),
    REJECTED                NUMBER(12, 4),
    LOSS                    NUMBER(12, 4),
    LEGACY_REJECT_LOSS_TOTAL NUMBER(12, 4),        -- historical combined; NULL when separated
    TOTAL_ACCEPTED          NUMBER(12, 4),
    CREATED_AT              TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_PRODUCTION_RECORD PRIMARY KEY (PRODUCTION_ID),
    CONSTRAINT FK_PRODUCTION_IMPORT
        FOREIGN KEY (IMPORT_ID) REFERENCES EFNS_DEV.RAW.IMPORT_BATCH (IMPORT_ID)
)
COMMENT = 'Normalized production record per row. PROVISIONAL.';

-- ============================================================
-- PRODUCTION_SIZE_BREAKDOWN — normalized egg size bands
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.CORE.PRODUCTION_SIZE_BREAKDOWN (
    SIZE_BREAKDOWN_ID VARCHAR(36)    NOT NULL,
    PRODUCTION_ID     VARCHAR(36)    NOT NULL,
    SIZE_BAND         VARCHAR(50),               -- e.g. Jumbo | Extra Large | Large | Medium | Small | PeeWee
    QUANTITY          NUMBER(12, 4),
    CONSTRAINT PK_PRODUCTION_SIZE_BREAKDOWN PRIMARY KEY (SIZE_BREAKDOWN_ID),
    CONSTRAINT FK_SIZE_PRODUCTION
        FOREIGN KEY (PRODUCTION_ID) REFERENCES EFNS_DEV.CORE.PRODUCTION_RECORD (PRODUCTION_ID)
)
COMMENT = 'Egg size breakdown per production record. Normalized (not wide). PROVISIONAL.';

SELECT 'Production tables created (PROVISIONAL).' AS status;