-- Review/apply separately; not executed by the app or this task.
-- Existing NULL methods remain Allocation. No backfill or data update.
ALTER TABLE EFNS_DEV.CORE.QUOTA_TRANSACTION
    ADD COLUMN IF NOT EXISTS TRANSACTION_METHOD VARCHAR(20);
