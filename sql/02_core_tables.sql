-- ============================================================
-- EFNS Internal Data System Prototype v0.1
-- 02_core_tables.sql — Core Operational Entities
-- ============================================================
-- PROVISIONAL MODEL: All tables, columns, relationships, and
-- business rules are DRAFT. They will be revised after the
-- Dataverse (EIMS) metadata is reverse-engineered.
--
-- Logical names are intentionally clean; do NOT treat these as
-- a clone of Microsoft Dataverse internals.
-- ============================================================

USE DATABASE EFNS_DEV;

-- ============================================================
-- ACCOUNT (Producer / Farm / Organization)
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.CORE.ACCOUNT (
    ACCOUNT_ID          VARCHAR(36)   NOT NULL,   -- surrogate/provisional PK
    REGISTRATION_NUMBER VARCHAR(64),              -- PROVISIONAL: from EIMS
    ORGANIZATION_NAME   VARCHAR(255)  NOT NULL,   -- account / org name
    ADDRESS_LINE1       VARCHAR(255),
    ADDRESS_LINE2       VARCHAR(255),
    CITY                VARCHAR(100),
    PROVINCE            VARCHAR(50),
    POSTAL_CODE         VARCHAR(20),
    CONTACT_NAME        VARCHAR(255),
    CONTACT_PHONE       VARCHAR(50),
    CONTACT_EMAIL       VARCHAR(255),
    LICENCE_NUMBER      VARCHAR(64),              -- PROVISIONAL
    PRODUCER_ROLE       BOOLEAN       DEFAULT FALSE, -- role flags (PROVISIONAL)
    BREEDER_ROLE        BOOLEAN       DEFAULT FALSE,
    HATCHERY_ROLE       BOOLEAN       DEFAULT FALSE,
    GRADER_ROLE         BOOLEAN       DEFAULT FALSE,
    STATUS              VARCHAR(50)   DEFAULT 'Active',  -- PROVISIONAL status
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_ACCOUNT PRIMARY KEY (ACCOUNT_ID)
)
COMMENT = 'Producers / farms / producer organizations. PROVISIONAL.';

-- ============================================================
-- FACILITY
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.CORE.FACILITY (
    FACILITY_ID         VARCHAR(36)   NOT NULL,   -- surrogate/provisional PK
    ACCOUNT_ID          VARCHAR(36)   NOT NULL,   -- FK -> ACCOUNT
    FACILITY_NAME       VARCHAR(255)  NOT NULL,
    FACILITY_TYPE       VARCHAR(50),              -- pullet | layer | other (PROVISIONAL)
    STATUS              VARCHAR(50)   DEFAULT 'Active',
    ACTIVATION_DATE     DATE,
    CONSTRUCTION_DATE   DATE,
    CLOSURE_DATE        DATE,
    DESTRUCTION_DATE    DATE,
    INACTIVE_DATE       DATE,
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_FACILITY PRIMARY KEY (FACILITY_ID),
    CONSTRAINT FK_FACILITY_ACCOUNT
        FOREIGN KEY (ACCOUNT_ID) REFERENCES EFNS_DEV.CORE.ACCOUNT (ACCOUNT_ID)
)
COMMENT = 'Facilities belonging to an account. ACCOUNT 1:N FACILITY (PROVISIONAL).';

-- ============================================================
-- FLOCK
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.CORE.FLOCK (
    FLOCK_ID            VARCHAR(36)   NOT NULL,   -- surrogate/provisional PK
    ACCOUNT_ID          VARCHAR(36)   NOT NULL,   -- FK -> ACCOUNT
    FACILITY_ID         VARCHAR(36),              -- FK -> FACILITY (nullable, PROVISIONAL)
    FLOCK_NUMBER        VARCHAR(64),              -- business flock number
    LICENCE_NUMBER      VARCHAR(64),              -- PROVISIONAL
    BIRD_COUNT          INTEGER,
    PLACEMENT_DATE      DATE,
    HATCH_DATE          DATE,
    EGG_COLOUR          VARCHAR(50),              -- White | Brown | Mostly White | Mostly Brown
    EST_PROD_COMPLETION DATE,
    EST_DISPOSAL        DATE,
    ACTUAL_DISPOSAL     DATE,
    DISPOSAL_METHOD     VARCHAR(100),
    STATUS              VARCHAR(50)   DEFAULT 'Active',
    CREATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UPDATED_AT          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_FLOCK PRIMARY KEY (FLOCK_ID),
    CONSTRAINT FK_FLOCK_ACCOUNT
        FOREIGN KEY (ACCOUNT_ID) REFERENCES EFNS_DEV.CORE.ACCOUNT (ACCOUNT_ID),
    CONSTRAINT FK_FLOCK_FACILITY
        FOREIGN KEY (FACILITY_ID) REFERENCES EFNS_DEV.CORE.FACILITY (FACILITY_ID)
)
COMMENT = 'Flocks. ACCOUNT -> FACILITY -> FLOCK (PROVISIONAL).';

-- ============================================================
-- FLOCK_TRANSACTION
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.CORE.FLOCK_TRANSACTION (
    FLOCK_TRANSACTION_ID VARCHAR(36)  NOT NULL,   -- surrogate/provisional PK
    FLOCK_ID             VARCHAR(36)  NOT NULL,   -- FK -> FLOCK
    TRANSACTION_TYPE     VARCHAR(50),             -- Count | Delivery | Removal | Sale
    QUANTITY             INTEGER,
    TRANSACTION_DATE     DATE,
    NOTES                VARCHAR(500),
    CREATED_AT           TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_FLOCK_TRANSACTION PRIMARY KEY (FLOCK_TRANSACTION_ID),
    CONSTRAINT FK_FLOCK_TRANSACTION_FLOCK
        FOREIGN KEY (FLOCK_ID) REFERENCES EFNS_DEV.CORE.FLOCK (FLOCK_ID)
)
COMMENT = 'Historical transactions on flocks. FLOCK 1:N FLOCK_TRANSACTION (PROVISIONAL).';

-- ============================================================
-- QUOTA (Phase 2 placeholders — do NOT build logic yet)
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.CORE.QUOTA_REGISTRATION (
    QUOTA_REGISTRATION_ID VARCHAR(36)  NOT NULL,
    ACCOUNT_ID            VARCHAR(36)  NOT NULL,
    QUOTA_TYPE            VARCHAR(50),            -- PROVISIONAL
    QUANTITY              NUMBER(18, 4),
    EFFECTIVE_DATE        DATE,
    STATUS                VARCHAR(50),
    CREATED_AT            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_QUOTA_REGISTRATION PRIMARY KEY (QUOTA_REGISTRATION_ID)
)
COMMENT = 'PHASE 2 placeholder — quota registrations. DO NOT populate logic yet.';

CREATE OR REPLACE TABLE EFNS_DEV.CORE.QUOTA_TRANSACTION (
    QUOTA_TRANSACTION_ID   VARCHAR(36)  NOT NULL,
    SOURCE_ACCOUNT_ID      VARCHAR(36),
    DESTINATION_ACCOUNT_ID VARCHAR(36),
    TRANSACTION_TYPE       VARCHAR(50),          -- allocation | increase | decrease | transfer | lease
    QUANTITY               NUMBER(18, 4),
    EFFECTIVE_DATE         DATE,
    END_DATE               DATE,                 -- for leases
    CREATED_AT             TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_QUOTA_TRANSACTION PRIMARY KEY (QUOTA_TRANSACTION_ID)
)
COMMENT = 'PHASE 2 placeholder — quota transactions (incl. leases). DO NOT populate logic yet.';

-- ============================================================
-- SALMONELLA / DISEASE TESTING (Phase 2 placeholder)
-- ============================================================
CREATE OR REPLACE TABLE EFNS_DEV.CORE.DISEASE_TEST (
    DISEASE_TEST_ID  VARCHAR(36)  NOT NULL,
    ACCOUNT_ID       VARCHAR(36),
    FACILITY_ID      VARCHAR(36),
    FLOCK_ID         VARCHAR(36),
    TEST_TYPE        VARCHAR(50),                -- PROVISIONAL (e.g. Salmonella)
    TEST_DATE        DATE,
    RESULT           VARCHAR(20),                -- positive | negative (PROVISIONAL)
    CREATED_AT       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_DISEASE_TEST PRIMARY KEY (DISEASE_TEST_ID)
)
COMMENT = 'PHASE 2 placeholder — disease testing. Business rules NOT yet confirmed.';

SELECT 'Core tables created (PROVISIONAL).' AS status;