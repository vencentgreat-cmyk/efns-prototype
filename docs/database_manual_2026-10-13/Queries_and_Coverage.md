# Queries and Coverage

All examples below are read-only and executed through the current SELECT-only verification against real DEV using a saved deployed code snapshot. The execution date/time is in receipts. No browser acceptance or business balance formula is inferred.

## SQL-1 contacts

Result: 1 rows; query ID `01c7b538-0003-02c7-0003-b7060012889e`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT CONTACT_ID,ACCOUNT_ID FROM EFNS_DEV.CORE.CONTACT WHERE ACCOUNT_ID='3549413D-CDE6-E511-80E1-C4346BAC339C';
```

## SQL-1 locations

Result: 3 rows; query ID `01c7b538-0003-02c7-0003-b706001288a2`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT FARM_LOCATION_ID,ACCOUNT_ID FROM EFNS_DEV.CORE.FARM_LOCATION WHERE ACCOUNT_ID='3549413D-CDE6-E511-80E1-C4346BAC339C';
```

## SQL-1 facilities

Result: 14 rows; query ID `01c7b538-0003-03ac-0003-b706001251da`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT FACILITY_ID,ACCOUNT_ID FROM EFNS_DEV.CORE.FACILITY WHERE ACCOUNT_ID='3549413D-CDE6-E511-80E1-C4346BAC339C';
```

## SQL-2 facility flocks

Result: 19 rows; query ID `01c7b538-0003-02c7-0003-b706001288a6`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT FLOCK_ID,ACCOUNT_ID,FACILITY_ID,PLACEMENT_DATE,DISPOSAL_DATE,EST_DISPOSAL FROM EFNS_DEV.CORE.FLOCK WHERE FACILITY_ID='3F786E7B-E954-E611-80EF-C4346BAC0574';
```

## SQL-3 quota history

Result: 46 rows; query ID `01c7b538-0003-02c7-0003-b706001288aa`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT QUOTA_TRANSACTION_ID,QUOTA_ID,QUOTA_COUNT FROM EFNS_DEV.CORE.QUOTA_TRANSACTION WHERE QUOTA_ID='EC6DC544-8254-E811-814A-E0071B6AF2A1';
```

## SQL-4 Source Total

Result: 23 rows; query ID `01c7b538-0003-02c7-0003-b706001288ae`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT PRODUCER_ACCOUNT_ID,COUNT(*) ROW_COUNT,COUNT(TOTAL) KNOWN,SUM(TOTAL) TOTAL FROM EFNS_DEV.CORE.PRODUCTION_RECORD WHERE REPORTING_YEAR=2017 AND REPORTING_WEEK=15 GROUP BY PRODUCER_ACCOUNT_ID;
```

## SQL-5 lineage

Result: 14 rows; query ID `01c7b538-0003-03ac-0003-b706001251de`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT SOURCE_ENTITY,COUNT(*) LINEAGES,COUNT(DISTINCT TARGET_ID) TARGETS FROM EFNS_DEV.RAW.MIGRATION_ID_MAP WHERE MIGRATION_BATCH_ID='DEV_MIGRATION_255ef9b50a52e766a7dff9' GROUP BY SOURCE_ENTITY;
```

## PVQ-03a transactions

Result: 12 rows; query ID `01c7b538-0003-03ac-0003-b706001251e2`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT FLOCK_TRANSACTION_ID,FLOCK_ID,QUANTITY FROM EFNS_DEV.CORE.FLOCK_TRANSACTION WHERE FLOCK_ID IN (SELECT FLOCK_ID FROM EFNS_DEV.CORE.FLOCK WHERE FACILITY_ID='3F786E7B-E954-E611-80EF-C4346BAC0574');
```

## PVQ-04 test/sample list

Result: 4 rows; query ID `01c7b538-0003-02c7-0003-b706001288b2`. List/sum structure supported and automatically executed; units, inventory/quota balance and business completeness remain separate.

```sql
SELECT t.SALMONELLA_TEST_ID,t.FLOCK_ID,t.ACCOUNT_ID,s.SALMONELLA_TEST_SAMPLE_ID FROM EFNS_DEV.CORE.SALMONELLA_TEST t LEFT JOIN EFNS_DEV.CORE.SALMONELLA_TEST_SAMPLE s ON t.SALMONELLA_TEST_ID=s.SALMONELLA_TEST_ID WHERE t.FLOCK_ID IN (SELECT FLOCK_ID FROM EFNS_DEV.CORE.FLOCK WHERE FACILITY_ID='3F786E7B-E954-E611-80EF-C4346BAC0574');
```
