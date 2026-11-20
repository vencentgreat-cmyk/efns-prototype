-- Review only. No user mappings, roles, passwords or sessions are changed here.
ALTER TABLE EFNS_DEV.SECURITY.APP_USER
    ADD COLUMN IF NOT EXISTS SNOWFLAKE_USERNAME VARCHAR(255);
-- Standard Snowflake UNIQUE constraints are not enforced. The application
-- normalizes and checks uniqueness inside the existing continuity transaction.
-- No additional grants: reuse the existing APP_USER and intake-lock grants.
