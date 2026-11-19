-- Review-only additive DDL. NULL means active; only new-method Lease rows use this field.
ALTER TABLE EFNS_DEV.CORE.QUOTA_TRANSACTION
    ADD COLUMN IF NOT EXISTS LEASE_STATUS VARCHAR(20);
