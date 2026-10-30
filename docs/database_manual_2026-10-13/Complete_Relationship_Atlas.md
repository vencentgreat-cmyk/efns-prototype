# Complete Declared Relationship Atlas

13 October 2026 metadata; one line/sheet per complete FK. Declarations are not standard-table engine enforcement.

## R01 FK_ACCOUNT_PARENT

`CORE.ACCOUNT (PARENT_ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R01](erd/relationships/R01_FK_ACCOUNT_PARENT.png)

## R02 FK_ACCOUNT_GRADING_STATION

`CORE.ACCOUNT (GRADING_STATION_ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R02](erd/relationships/R02_FK_ACCOUNT_GRADING_STATION.png)

## R03 FK_ACCOUNT_PULLET_GROWER

`CORE.ACCOUNT (PULLET_GROWER_ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R03](erd/relationships/R03_FK_ACCOUNT_PULLET_GROWER.png)

## R04 FK_FACILITY_ACCOUNT

`CORE.FACILITY (ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R04](erd/relationships/R04_FK_FACILITY_ACCOUNT.png)

## R05 FK_PRODUCTION_ACCOUNT

`CORE.PRODUCTION_RECORD (PRODUCER_ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R05](erd/relationships/R05_FK_PRODUCTION_ACCOUNT.png)

## R06 FK_QUOTA_ACCOUNT

`CORE.QUOTA_REGISTRATION (ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R06](erd/relationships/R06_FK_QUOTA_ACCOUNT.png)

## R07 FK_FLOCK_ACCOUNT

`CORE.FLOCK (ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R07](erd/relationships/R07_FK_FLOCK_ACCOUNT.png)

## R08 FK_QUOTA_TRANSACTION_OWNER

`CORE.QUOTA_TRANSACTION (OWNER_ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R08](erd/relationships/R08_FK_QUOTA_TRANSACTION_OWNER.png)

## R09 FK_QUOTA_TRANSACTION_RELATED_ACCOUNT

`CORE.QUOTA_TRANSACTION (RELATED_ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R09](erd/relationships/R09_FK_QUOTA_TRANSACTION_RELATED_ACCOUNT.png)

## R10 FK_SALMONELLA_TEST_ACCOUNT

`CORE.SALMONELLA_TEST (ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R10](erd/relationships/R10_FK_SALMONELLA_TEST_ACCOUNT.png)

## R11 FK_FARM_LOCATION_ACCOUNT

`CORE.FARM_LOCATION (ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R11](erd/relationships/R11_FK_FARM_LOCATION_ACCOUNT.png)

## R12 FK_CONTACT_ACCOUNT

`CORE.CONTACT (ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R12](erd/relationships/R12_FK_CONTACT_ACCOUNT.png)

## R13 FK_PRODUCTION_GRADER_ACCOUNT

`CORE.PRODUCTION_RECORD (GRADER_ACCOUNT_ID)` -> `CORE.ACCOUNT (ACCOUNT_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R13](erd/relationships/R13_FK_PRODUCTION_GRADER_ACCOUNT.png)

## R14 FK_FACILITY_DETAIL_FACILITY

`CORE.FACILITY_DETAIL (FACILITY_ID)` -> `CORE.FACILITY (FACILITY_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R14](erd/relationships/R14_FK_FACILITY_DETAIL_FACILITY.png)

## R15 FK_PRODUCTION_FACILITY

`CORE.PRODUCTION_RECORD (FACILITY_ID)` -> `CORE.FACILITY (FACILITY_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R15](erd/relationships/R15_FK_PRODUCTION_FACILITY.png)

## R16 FK_FLOCK_FACILITY

`CORE.FLOCK (FACILITY_ID)` -> `CORE.FACILITY (FACILITY_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R16](erd/relationships/R16_FK_FLOCK_FACILITY.png)

## R17 FK_FLOCK_DETAIL

`CORE.FLOCK (FACILITY_DETAIL_ID)` -> `CORE.FACILITY_DETAIL (FACILITY_DETAIL_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R17](erd/relationships/R17_FK_FLOCK_DETAIL.png)

## R18 FK_FACILITY_FARM_LOCATION

`CORE.FACILITY (FARM_LOCATION_ID)` -> `CORE.FARM_LOCATION (FARM_LOCATION_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R18](erd/relationships/R18_FK_FACILITY_FARM_LOCATION.png)

## R19 FK_FLOCK_TRANSACTION_FLOCK

`CORE.FLOCK_TRANSACTION (FLOCK_ID)` -> `CORE.FLOCK (FLOCK_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R19](erd/relationships/R19_FK_FLOCK_TRANSACTION_FLOCK.png)

## R20 FK_PRODUCTION_FLOCK

`CORE.PRODUCTION_RECORD (FLOCK_ID)` -> `CORE.FLOCK (FLOCK_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R20](erd/relationships/R20_FK_PRODUCTION_FLOCK.png)

## R21 FK_SALMONELLA_TEST_FLOCK

`CORE.SALMONELLA_TEST (FLOCK_ID)` -> `CORE.FLOCK (FLOCK_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R21](erd/relationships/R21_FK_SALMONELLA_TEST_FLOCK.png)

## R22 FK_SIZE_PRODUCTION

`CORE.PRODUCTION_SIZE_BREAKDOWN (PRODUCTION_ID)` -> `CORE.PRODUCTION_RECORD (PRODUCTION_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R22](erd/relationships/R22_FK_SIZE_PRODUCTION.png)

## R23 FK_FLOCK_QUOTA

`CORE.FLOCK (QUOTA_ID)` -> `CORE.QUOTA_REGISTRATION (QUOTA_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R23](erd/relationships/R23_FK_FLOCK_QUOTA.png)

## R24 FK_QUOTA_TRANSACTION_QUOTA

`CORE.QUOTA_TRANSACTION (QUOTA_ID)` -> `CORE.QUOTA_REGISTRATION (QUOTA_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R24](erd/relationships/R24_FK_QUOTA_TRANSACTION_QUOTA.png)

## R25 FK_QUOTA_TRANSACTION_RELATED_QUOTA

`CORE.QUOTA_TRANSACTION (RELATED_QUOTA_ID)` -> `CORE.QUOTA_REGISTRATION (QUOTA_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R25](erd/relationships/R25_FK_QUOTA_TRANSACTION_RELATED_QUOTA.png)

## R26 FK_QUOTA_TRANSACTION_RELATED_TRANSACTION

`CORE.QUOTA_TRANSACTION (RELATED_TRANSACTION_ID)` -> `CORE.QUOTA_TRANSACTION (QUOTA_TRANSACTION_ID)`. Parent per child: 0..1; children per parent: 0..many. Non-identifying.

![R26](erd/relationships/R26_FK_QUOTA_TRANSACTION_RELATED_TRANSACTION.png)

## R27 FK_SALMONELLA_SAMPLE_TEST

`CORE.SALMONELLA_TEST_SAMPLE (SALMONELLA_TEST_ID)` -> `CORE.SALMONELLA_TEST (SALMONELLA_TEST_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R27](erd/relationships/R27_FK_SALMONELLA_SAMPLE_TEST.png)

## R28 FK_PRODUCTION_IMPORT

`CORE.PRODUCTION_RECORD (IMPORT_ID)` -> `RAW.IMPORT_BATCH (IMPORT_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R28](erd/relationships/R28_FK_PRODUCTION_IMPORT.png)

## R29 FK_RAW_ROW_IMPORT

`RAW.IMPORT_RAW_ROW (IMPORT_ID)` -> `RAW.IMPORT_BATCH (IMPORT_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R29](erd/relationships/R29_FK_RAW_ROW_IMPORT.png)

## R30 FK_MIGRATION_RAW_ROW_BATCH

`RAW.MIGRATION_RAW_ROW (MIGRATION_BATCH_ID)` -> `RAW.MIGRATION_BATCH (MIGRATION_BATCH_ID)`. Parent per child: 1; children per parent: 0..many. Identifying.

![R30](erd/relationships/R30_FK_MIGRATION_RAW_ROW_BATCH.png)

## R31 FK_MIGRATION_ID_MAP_BATCH

`RAW.MIGRATION_ID_MAP (MIGRATION_BATCH_ID)` -> `RAW.MIGRATION_BATCH (MIGRATION_BATCH_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R31](erd/relationships/R31_FK_MIGRATION_ID_MAP_BATCH.png)

## R32 FK_MIGRATION_FILE_BATCH

`RAW.MIGRATION_FILE (MIGRATION_BATCH_ID)` -> `RAW.MIGRATION_BATCH (MIGRATION_BATCH_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R32](erd/relationships/R32_FK_MIGRATION_FILE_BATCH.png)

## R33 FK_MIGRATION_RECONCILIATION_BATCH

`RAW.MIGRATION_RECONCILIATION (MIGRATION_BATCH_ID)` -> `RAW.MIGRATION_BATCH (MIGRATION_BATCH_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R33](erd/relationships/R33_FK_MIGRATION_RECONCILIATION_BATCH.png)

## R34 FK_MIGRATION_ERROR_BATCH

`RAW.MIGRATION_ERROR (MIGRATION_BATCH_ID)` -> `RAW.MIGRATION_BATCH (MIGRATION_BATCH_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R34](erd/relationships/R34_FK_MIGRATION_ERROR_BATCH.png)

## R35 FK_MIGRATION_CORRECTION_ORIGINAL_BATCH

`RAW.MIGRATION_CORRECTION_BATCH (ORIGINAL_MIGRATION_BATCH_ID)` -> `RAW.MIGRATION_BATCH (MIGRATION_BATCH_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R35](erd/relationships/R35_FK_MIGRATION_CORRECTION_ORIGINAL_BATCH.png)

## R36 FK_MIGRATION_CORRECTION_ROW_ORIGINAL_BATCH

`RAW.MIGRATION_CORRECTION_ROW (ORIGINAL_MIGRATION_BATCH_ID)` -> `RAW.MIGRATION_BATCH (MIGRATION_BATCH_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R36](erd/relationships/R36_FK_MIGRATION_CORRECTION_ROW_ORIGINAL_BATCH.png)

## R37 FK_MIGRATION_CORRECTION_ROW_BATCH

`RAW.MIGRATION_CORRECTION_ROW (MIGRATION_CORRECTION_BATCH_ID)` -> `RAW.MIGRATION_CORRECTION_BATCH (MIGRATION_CORRECTION_BATCH_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R37](erd/relationships/R37_FK_MIGRATION_CORRECTION_ROW_BATCH.png)

## R38 FK_MIGRATION_CORRECTION_RAW_ROW

`RAW.MIGRATION_CORRECTION_ROW (ORIGINAL_MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID)` -> `RAW.MIGRATION_RAW_ROW (MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID)`. Parent per child: 1; children per parent: 0..many. Non-identifying.

![R38](erd/relationships/R38_FK_MIGRATION_CORRECTION_RAW_ROW.png)

## R39 FK_MIGRATION_ID_MAP_RAW_ROW

`RAW.MIGRATION_ID_MAP (MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID)` -> `RAW.MIGRATION_RAW_ROW (MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID)`. Parent per child: 1; children per parent: 0..1. Non-identifying.

![R39](erd/relationships/R39_FK_MIGRATION_ID_MAP_RAW_ROW.png)
