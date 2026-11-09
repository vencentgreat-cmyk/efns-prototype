# Field Evidence Index

M = storage; P = mapping; C = local code; Q = saved executed result/count; B = specific business confirmation. Missing categories are not asserted. No new database queries were run for this dictionary revision.

## F001 APP.AUDIT_EVENT.AUDIT_ID

**Metadata**

- E01 dev_evidence.json /columns/0: APP.AUDIT_EVENT.AUDIT_ID; GET_DDL APP.AUDIT_EVENT

**Code**

- E05 app/snowflake_security.py:223-254 (_insert_audit)

**Executed query**

- E01 /field_usage: APP.AUDIT_EVENT.AUDIT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F002 APP.AUDIT_EVENT.ACTOR_USER_ID

**Metadata**

- E01 dev_evidence.json /columns/1: APP.AUDIT_EVENT.ACTOR_USER_ID; GET_DDL APP.AUDIT_EVENT

**Code**

- E05 app/snowflake_security.py:223-254 (_insert_audit)

**Executed query**

- E01 /field_usage: APP.AUDIT_EVENT.ACTOR_USER_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F003 APP.AUDIT_EVENT.ACTOR_EMAIL

**Metadata**

- E01 dev_evidence.json /columns/2: APP.AUDIT_EVENT.ACTOR_EMAIL; GET_DDL APP.AUDIT_EVENT

**Code**

- E05 app/snowflake_security.py:223-254 (_insert_audit)

**Executed query**

- E01 /field_usage: APP.AUDIT_EVENT.ACTOR_EMAIL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F004 APP.AUDIT_EVENT.ACTION

**Metadata**

- E01 dev_evidence.json /columns/3: APP.AUDIT_EVENT.ACTION; GET_DDL APP.AUDIT_EVENT

**Code**

- E05 app/snowflake_security.py:223-254 (_insert_audit)

**Executed query**

- E01 /field_usage: APP.AUDIT_EVENT.ACTION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F005 APP.AUDIT_EVENT.ENTITY_TYPE

**Metadata**

- E01 dev_evidence.json /columns/4: APP.AUDIT_EVENT.ENTITY_TYPE; GET_DDL APP.AUDIT_EVENT

**Code**

- E05 app/snowflake_security.py:223-254 (_insert_audit)

**Executed query**

- E01 /field_usage: APP.AUDIT_EVENT.ENTITY_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F006 APP.AUDIT_EVENT.ENTITY_ID

**Metadata**

- E01 dev_evidence.json /columns/5: APP.AUDIT_EVENT.ENTITY_ID; GET_DDL APP.AUDIT_EVENT

**Code**

- E05 app/snowflake_security.py:223-254 (_insert_audit)
- E05 app/services/authorized_repository.py:111-151 (_authorized_import)

**Executed query**

- E01 /field_usage: APP.AUDIT_EVENT.ENTITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F007 APP.AUDIT_EVENT.DETAILS

**Metadata**

- E01 dev_evidence.json /columns/6: APP.AUDIT_EVENT.DETAILS; GET_DDL APP.AUDIT_EVENT

**Code**

- E05 app/snowflake_security.py:223-254 (_insert_audit)

**Executed query**

- E01 /field_usage: APP.AUDIT_EVENT.DETAILS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F008 APP.AUDIT_EVENT.OCCURRED_AT

**Metadata**

- E01 dev_evidence.json /columns/7: APP.AUDIT_EVENT.OCCURRED_AT; GET_DDL APP.AUDIT_EVENT

**Code**

- E05 app/snowflake_security.py:223-254 (_insert_audit)

**Executed query**

- E01 /field_usage: APP.AUDIT_EVENT.OCCURRED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F009 CORE.ACCOUNT.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/8: CORE.ACCOUNT.ACCOUNT_ID; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:334 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:89 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F010 CORE.ACCOUNT.REGISTRATION_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/9: CORE.ACCOUNT.REGISTRATION_NUMBER; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/REGISTRATION_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:340 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:90 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.REGISTRATION_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F011 CORE.ACCOUNT.ORGANIZATION_NAME

**Metadata**

- E01 dev_evidence.json /columns/10: CORE.ACCOUNT.ORGANIZATION_NAME; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ORGANIZATION_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:335 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:91 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.ORGANIZATION_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F012 CORE.ACCOUNT.ADDRESS_LINE1

**Metadata**

- E01 dev_evidence.json /columns/11: CORE.ACCOUNT.ADDRESS_LINE1; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ADDRESS_LINE1

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:350 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:92 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.ADDRESS_LINE1, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F013 CORE.ACCOUNT.ADDRESS_LINE2

**Metadata**

- E01 dev_evidence.json /columns/12: CORE.ACCOUNT.ADDRESS_LINE2; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ADDRESS_LINE2

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:351 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:93 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.ADDRESS_LINE2, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F014 CORE.ACCOUNT.ADDRESS_LINE3

**Metadata**

- E01 dev_evidence.json /columns/13: CORE.ACCOUNT.ADDRESS_LINE3; GET_DDL CORE.ACCOUNT

**Code**

- E05 app/pages/3_Accounts_Facilities_Flocks.py:352 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:94 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.ADDRESS_LINE3, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F015 CORE.ACCOUNT.CITY

**Metadata**

- E01 dev_evidence.json /columns/14: CORE.ACCOUNT.CITY; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/CITY

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:353 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:95 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.CITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F016 CORE.ACCOUNT.PROVINCE

**Metadata**

- E01 dev_evidence.json /columns/15: CORE.ACCOUNT.PROVINCE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PROVINCE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:354 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:96 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.PROVINCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F017 CORE.ACCOUNT.POSTAL_CODE

**Metadata**

- E01 dev_evidence.json /columns/16: CORE.ACCOUNT.POSTAL_CODE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/POSTAL_CODE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:355 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:97 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.POSTAL_CODE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F018 CORE.ACCOUNT.COUNTRY_REGION

**Metadata**

- E01 dev_evidence.json /columns/17: CORE.ACCOUNT.COUNTRY_REGION; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/COUNTRY_REGION

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:356 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:98 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.COUNTRY_REGION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F019 CORE.ACCOUNT.LATITUDE

**Metadata**

- E01 dev_evidence.json /columns/18: CORE.ACCOUNT.LATITUDE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/LATITUDE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/LATITUDE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:99 (generate_accounts, fabricated only)
- E05 data/validation.py:33-49 (parse_optional_coordinate)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.LATITUDE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F020 CORE.ACCOUNT.LONGITUDE

**Metadata**

- E01 dev_evidence.json /columns/19: CORE.ACCOUNT.LONGITUDE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/LONGITUDE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/LONGITUDE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:100 (generate_accounts, fabricated only)
- E05 data/validation.py:33-49 (parse_optional_coordinate)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.LONGITUDE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F021 CORE.ACCOUNT.CONTACT_NAME

**Metadata**

- E01 dev_evidence.json /columns/20: CORE.ACCOUNT.CONTACT_NAME; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/CONTACT_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:101 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.CONTACT_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F022 CORE.ACCOUNT.CONTACT_PHONE

**Metadata**

- E01 dev_evidence.json /columns/21: CORE.ACCOUNT.CONTACT_PHONE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/CONTACT_PHONE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:337 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:102 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.CONTACT_PHONE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F023 CORE.ACCOUNT.CONTACT_EMAIL

**Metadata**

- E01 dev_evidence.json /columns/22: CORE.ACCOUNT.CONTACT_EMAIL; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/CONTACT_EMAIL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:336 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:103 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.CONTACT_EMAIL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F024 CORE.ACCOUNT.FAX

**Metadata**

- E01 dev_evidence.json /columns/23: CORE.ACCOUNT.FAX; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/FAX

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:338 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:104 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.FAX, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F025 CORE.ACCOUNT.WEBSITE

**Metadata**

- E01 dev_evidence.json /columns/24: CORE.ACCOUNT.WEBSITE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/WEBSITE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:339 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:105 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.WEBSITE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F026 CORE.ACCOUNT.LICENCE_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/25: CORE.ACCOUNT.LICENCE_NUMBER; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/LICENCE_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:106 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.LICENCE_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F027 CORE.ACCOUNT.PARENT_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/26: CORE.ACCOUNT.PARENT_ACCOUNT_ID; GET_DDL CORE.ACCOUNT

**Code**

- E05 app/pages/3_Accounts_Facilities_Flocks.py:342 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:107 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.PARENT_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F028 CORE.ACCOUNT.GRADING_STATION_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/27: CORE.ACCOUNT.GRADING_STATION_ACCOUNT_ID; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/GRADING_STATION_ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:343 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:108 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.GRADING_STATION_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F029 CORE.ACCOUNT.PULLET_GROWER_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/28: CORE.ACCOUNT.PULLET_GROWER_ACCOUNT_ID; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PULLET_GROWER_ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:344 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:109 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.PULLET_GROWER_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F030 CORE.ACCOUNT.PROVINCE_OF_REGISTRATION

**Metadata**

- E01 dev_evidence.json /columns/29: CORE.ACCOUNT.PROVINCE_OF_REGISTRATION; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PROVINCE_OF_REGISTRATION

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:341 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:110 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.PROVINCE_OF_REGISTRATION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F031 CORE.ACCOUNT.SPENT_FOWL_PLANS

**Metadata**

- E01 dev_evidence.json /columns/30: CORE.ACCOUNT.SPENT_FOWL_PLANS; GET_DDL CORE.ACCOUNT

**Code**

- E05 app/pages/3_Accounts_Facilities_Flocks.py:345 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:111 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.SPENT_FOWL_PLANS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F032 CORE.ACCOUNT.DEFAULT_ON_REPORTS

**Metadata**

- E01 dev_evidence.json /columns/31: CORE.ACCOUNT.DEFAULT_ON_REPORTS; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/DEFAULT_ON_REPORTS
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/DEFAULT_ON_REPORTS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:346 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:112 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.DEFAULT_ON_REPORTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F033 CORE.ACCOUNT.NO_SVG

**Metadata**

- E01 dev_evidence.json /columns/32: CORE.ACCOUNT.NO_SVG; GET_DDL CORE.ACCOUNT

**Code**

- E05 app/pages/3_Accounts_Facilities_Flocks.py:347 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:113 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.NO_SVG, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F034 CORE.ACCOUNT.DESCRIPTION

**Metadata**

- E01 dev_evidence.json /columns/33: CORE.ACCOUNT.DESCRIPTION; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/DESCRIPTION

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:349 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:114 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.DESCRIPTION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F035 CORE.ACCOUNT.PRODUCER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/34: CORE.ACCOUNT.PRODUCER_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PRODUCER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/PRODUCER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:115 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.PRODUCER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F036 CORE.ACCOUNT.BREEDER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/35: CORE.ACCOUNT.BREEDER_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/BREEDER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/BREEDER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:116 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.BREEDER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F037 CORE.ACCOUNT.HATCHERY_ROLE

**Metadata**

- E01 dev_evidence.json /columns/36: CORE.ACCOUNT.HATCHERY_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/HATCHERY_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/HATCHERY_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:117 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.HATCHERY_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F038 CORE.ACCOUNT.PULLET_GROWER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/37: CORE.ACCOUNT.PULLET_GROWER_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PULLET_GROWER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/PULLET_GROWER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:118 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.PULLET_GROWER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F039 CORE.ACCOUNT.GRADER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/38: CORE.ACCOUNT.GRADER_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/GRADER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/GRADER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:119 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.GRADER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F040 CORE.ACCOUNT.PROCESSOR_BREAKER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/39: CORE.ACCOUNT.PROCESSOR_BREAKER_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PROCESSOR_BREAKER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/PROCESSOR_BREAKER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:120 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.PROCESSOR_BREAKER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F041 CORE.ACCOUNT.DISPOSAL_PLANT_ROLE

**Metadata**

- E01 dev_evidence.json /columns/40: CORE.ACCOUNT.DISPOSAL_PLANT_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/DISPOSAL_PLANT_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/DISPOSAL_PLANT_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:121 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.DISPOSAL_PLANT_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F042 CORE.ACCOUNT.UNREGULATED_ROLE

**Metadata**

- E01 dev_evidence.json /columns/41: CORE.ACCOUNT.UNREGULATED_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/UNREGULATED_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/UNREGULATED_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:122 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.UNREGULATED_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F043 CORE.ACCOUNT.PROV_BOARD_EFC_ROLE

**Metadata**

- E01 dev_evidence.json /columns/42: CORE.ACCOUNT.PROV_BOARD_EFC_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PROV_BOARD_EFC_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/PROV_BOARD_EFC_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:123 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.PROV_BOARD_EFC_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F044 CORE.ACCOUNT.GOVERNMENT_ROLE

**Metadata**

- E01 dev_evidence.json /columns/43: CORE.ACCOUNT.GOVERNMENT_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/GOVERNMENT_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/GOVERNMENT_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:124 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.GOVERNMENT_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F045 CORE.ACCOUNT.VENDOR_ROLE

**Metadata**

- E01 dev_evidence.json /columns/44: CORE.ACCOUNT.VENDOR_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/VENDOR_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/VENDOR_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:125 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.VENDOR_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F046 CORE.ACCOUNT.RESEARCH_EXEMPT_ROLE

**Metadata**

- E01 dev_evidence.json /columns/45: CORE.ACCOUNT.RESEARCH_EXEMPT_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/RESEARCH_EXEMPT_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/RESEARCH_EXEMPT_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:126 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.RESEARCH_EXEMPT_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F047 CORE.ACCOUNT.SHIPPER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/46: CORE.ACCOUNT.SHIPPER_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/SHIPPER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/SHIPPER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:127 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.SHIPPER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F048 CORE.ACCOUNT.OTHER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/47: CORE.ACCOUNT.OTHER_ROLE; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/OTHER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/OTHER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:128 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.OTHER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F049 CORE.ACCOUNT.STATUS

**Metadata**

- E01 dev_evidence.json /columns/48: CORE.ACCOUNT.STATUS; GET_DDL CORE.ACCOUNT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:348 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:129 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F050 CORE.ACCOUNT.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/49: CORE.ACCOUNT.CREATED_AT; GET_DDL CORE.ACCOUNT

**Code**

- E05 app/pages/3_Accounts_Facilities_Flocks.py:151 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F051 CORE.ACCOUNT.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/50: CORE.ACCOUNT.UPDATED_AT; GET_DDL CORE.ACCOUNT

**Code**

- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.ACCOUNT.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F052 CORE.CONTACT.CONTACT_ID

**Metadata**

- E01 dev_evidence.json /columns/51: CORE.CONTACT.CONTACT_ID; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/CONTACT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.CONTACT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F053 CORE.CONTACT.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/52: CORE.CONTACT.ACCOUNT_ID; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F054 CORE.CONTACT.FULL_NAME

**Metadata**

- E01 dev_evidence.json /columns/53: CORE.CONTACT.FULL_NAME; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/FULL_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.FULL_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F055 CORE.CONTACT.FIRST_NAME

**Metadata**

- E01 dev_evidence.json /columns/54: CORE.CONTACT.FIRST_NAME; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/FIRST_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.FIRST_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F056 CORE.CONTACT.MIDDLE_NAME

**Metadata**

- E01 dev_evidence.json /columns/55: CORE.CONTACT.MIDDLE_NAME; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/MIDDLE_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.MIDDLE_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F057 CORE.CONTACT.LAST_NAME

**Metadata**

- E01 dev_evidence.json /columns/56: CORE.CONTACT.LAST_NAME; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/LAST_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.LAST_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F058 CORE.CONTACT.JOB_TITLE

**Metadata**

- E01 dev_evidence.json /columns/57: CORE.CONTACT.JOB_TITLE; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/JOB_TITLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.JOB_TITLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F059 CORE.CONTACT.EMAIL

**Metadata**

- E01 dev_evidence.json /columns/58: CORE.CONTACT.EMAIL; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/EMAIL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.EMAIL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F060 CORE.CONTACT.PHONE

**Metadata**

- E01 dev_evidence.json /columns/59: CORE.CONTACT.PHONE; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/PHONE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.PHONE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F061 CORE.CONTACT.MOBILE_PHONE

**Metadata**

- E01 dev_evidence.json /columns/60: CORE.CONTACT.MOBILE_PHONE; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/MOBILE_PHONE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.MOBILE_PHONE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F062 CORE.CONTACT.FAX

**Metadata**

- E01 dev_evidence.json /columns/61: CORE.CONTACT.FAX; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/FAX

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.FAX, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F063 CORE.CONTACT.ADDRESS_LINE1

**Metadata**

- E01 dev_evidence.json /columns/62: CORE.CONTACT.ADDRESS_LINE1; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/ADDRESS_LINE1

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.ADDRESS_LINE1, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F064 CORE.CONTACT.ADDRESS_LINE2

**Metadata**

- E01 dev_evidence.json /columns/63: CORE.CONTACT.ADDRESS_LINE2; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/ADDRESS_LINE2

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.ADDRESS_LINE2, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F065 CORE.CONTACT.CITY

**Metadata**

- E01 dev_evidence.json /columns/64: CORE.CONTACT.CITY; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/CITY

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.CITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F066 CORE.CONTACT.PROVINCE

**Metadata**

- E01 dev_evidence.json /columns/65: CORE.CONTACT.PROVINCE; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/PROVINCE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.PROVINCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F067 CORE.CONTACT.POSTAL_CODE

**Metadata**

- E01 dev_evidence.json /columns/66: CORE.CONTACT.POSTAL_CODE; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/POSTAL_CODE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.POSTAL_CODE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F068 CORE.CONTACT.COUNTRY_REGION

**Metadata**

- E01 dev_evidence.json /columns/67: CORE.CONTACT.COUNTRY_REGION; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/COUNTRY_REGION

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.COUNTRY_REGION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F069 CORE.CONTACT.EIMS_CONTACT_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/68: CORE.CONTACT.EIMS_CONTACT_NUMBER; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/EIMS_CONTACT_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.EIMS_CONTACT_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F070 CORE.CONTACT.LANGUAGE_PREFERENCE

**Metadata**

- E01 dev_evidence.json /columns/69: CORE.CONTACT.LANGUAGE_PREFERENCE; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/LANGUAGE_PREFERENCE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.LANGUAGE_PREFERENCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F071 CORE.CONTACT.PRIME_CONTACT

**Metadata**

- E01 dev_evidence.json /columns/70: CORE.CONTACT.PRIME_CONTACT; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/PRIME_CONTACT
- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_types/PRIME_CONTACT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.PRIME_CONTACT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F072 CORE.CONTACT.STATUS

**Metadata**

- E01 dev_evidence.json /columns/71: CORE.CONTACT.STATUS; GET_DDL CORE.CONTACT

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/CONTACT/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.CONTACT.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F073 CORE.CONTACT.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/72: CORE.CONTACT.CREATED_AT; GET_DDL CORE.CONTACT

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.CONTACT.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F074 CORE.CONTACT.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/73: CORE.CONTACT.UPDATED_AT; GET_DDL CORE.CONTACT

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.CONTACT.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F075 CORE.DIM_EFC_DATE.DAY

**Metadata**

- E01 dev_evidence.json /columns/74: CORE.DIM_EFC_DATE.DAY; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/DAY
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/DAY

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.DAY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F076 CORE.DIM_EFC_DATE.EFC_YEAR

**Metadata**

- E01 dev_evidence.json /columns/75: CORE.DIM_EFC_DATE.EFC_YEAR; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/EFC_YEAR
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/EFC_YEAR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.EFC_YEAR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F077 CORE.DIM_EFC_DATE.EFC_WEEK_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/76: CORE.DIM_EFC_DATE.EFC_WEEK_NUMBER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/EFC_WEEK_NUMBER
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/EFC_WEEK_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.EFC_WEEK_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F078 CORE.DIM_EFC_DATE.EFC_WEEK

**Metadata**

- E01 dev_evidence.json /columns/77: CORE.DIM_EFC_DATE.EFC_WEEK; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/EFC_WEEK

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.EFC_WEEK, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F079 CORE.DIM_EFC_DATE.EFC_WEEK_LABEL

**Metadata**

- E01 dev_evidence.json /columns/78: CORE.DIM_EFC_DATE.EFC_WEEK_LABEL; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/EFC_WEEK_LABEL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.EFC_WEEK_LABEL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F080 CORE.DIM_EFC_DATE.EFC_LONG_NAME

**Metadata**

- E01 dev_evidence.json /columns/79: CORE.DIM_EFC_DATE.EFC_LONG_NAME; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/EFC_LONG_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.EFC_LONG_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F081 CORE.DIM_EFC_DATE.EFC_PERIOD

**Metadata**

- E01 dev_evidence.json /columns/80: CORE.DIM_EFC_DATE.EFC_PERIOD; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/EFC_PERIOD
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/EFC_PERIOD

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.EFC_PERIOD, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F082 CORE.DIM_EFC_DATE.EFC_PERIOD_ALIAS

**Metadata**

- E01 dev_evidence.json /columns/81: CORE.DIM_EFC_DATE.EFC_PERIOD_ALIAS; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/EFC_PERIOD_ALIAS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.EFC_PERIOD_ALIAS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F083 CORE.DIM_EFC_DATE.EFC_QUARTER

**Metadata**

- E01 dev_evidence.json /columns/82: CORE.DIM_EFC_DATE.EFC_QUARTER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/EFC_QUARTER
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/EFC_QUARTER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.EFC_QUARTER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F084 CORE.DIM_EFC_DATE.ELEMENT_CODE

**Metadata**

- E01 dev_evidence.json /columns/83: CORE.DIM_EFC_DATE.ELEMENT_CODE; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/ELEMENT_CODE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.ELEMENT_CODE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F085 CORE.DIM_EFC_DATE.ELEMENT_CODES

**Metadata**

- E01 dev_evidence.json /columns/84: CORE.DIM_EFC_DATE.ELEMENT_CODES; GET_DDL CORE.DIM_EFC_DATE

**Code**

- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.ELEMENT_CODES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F086 CORE.DIM_EFC_DATE.PREVIOUS_QUARTER

**Metadata**

- E01 dev_evidence.json /columns/85: CORE.DIM_EFC_DATE.PREVIOUS_QUARTER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/PREVIOUS_QUARTER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.PREVIOUS_QUARTER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F087 CORE.DIM_EFC_DATE.PREV_YEAR

**Metadata**

- E01 dev_evidence.json /columns/86: CORE.DIM_EFC_DATE.PREV_YEAR; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/PREV_YEAR
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/PREV_YEAR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.PREV_YEAR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F088 CORE.DIM_EFC_DATE.PREV_WEEK

**Metadata**

- E01 dev_evidence.json /columns/87: CORE.DIM_EFC_DATE.PREV_WEEK; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/PREV_WEEK
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/PREV_WEEK

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.PREV_WEEK, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F089 CORE.DIM_EFC_DATE.PREV_QUARTER

**Metadata**

- E01 dev_evidence.json /columns/88: CORE.DIM_EFC_DATE.PREV_QUARTER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/PREV_QUARTER
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/PREV_QUARTER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.PREV_QUARTER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F090 CORE.DIM_EFC_DATE.DATE_VALUE

**Metadata**

- E01 dev_evidence.json /columns/89: CORE.DIM_EFC_DATE.DATE_VALUE; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/DATE_VALUE
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/DATE_VALUE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.DATE_VALUE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F091 CORE.DIM_EFC_DATE.MONTH_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/90: CORE.DIM_EFC_DATE.MONTH_NUMBER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/MONTH_NUMBER
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/MONTH_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.MONTH_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F092 CORE.DIM_EFC_DATE.MONTH_TEXT

**Metadata**

- E01 dev_evidence.json /columns/91: CORE.DIM_EFC_DATE.MONTH_TEXT; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/MONTH_TEXT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.MONTH_TEXT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F093 CORE.DIM_EFC_DATE.DAYS_IN_MONTH

**Metadata**

- E01 dev_evidence.json /columns/92: CORE.DIM_EFC_DATE.DAYS_IN_MONTH; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/DAYS_IN_MONTH
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/DAYS_IN_MONTH

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.DAYS_IN_MONTH, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F094 CORE.DIM_EFC_DATE.YEAR_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/93: CORE.DIM_EFC_DATE.YEAR_NUMBER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/YEAR_NUMBER
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/YEAR_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.YEAR_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F095 CORE.DIM_EFC_DATE.YEAR_MONTH

**Metadata**

- E01 dev_evidence.json /columns/94: CORE.DIM_EFC_DATE.YEAR_MONTH; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/YEAR_MONTH

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.YEAR_MONTH, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F096 CORE.DIM_EFC_DATE.QUARTER_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/95: CORE.DIM_EFC_DATE.QUARTER_NUMBER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/QUARTER_NUMBER
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/QUARTER_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.QUARTER_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F097 CORE.DIM_EFC_DATE.DAYS_IN_QUARTER

**Metadata**

- E01 dev_evidence.json /columns/96: CORE.DIM_EFC_DATE.DAYS_IN_QUARTER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/DAYS_IN_QUARTER
- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_types/DAYS_IN_QUARTER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.DAYS_IN_QUARTER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F098 CORE.DIM_EFC_DATE.YEAR_QUARTER

**Metadata**

- E01 dev_evidence.json /columns/97: CORE.DIM_EFC_DATE.YEAR_QUARTER; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/YEAR_QUARTER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.YEAR_QUARTER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F099 CORE.DIM_EFC_DATE.DAY_STRING

**Metadata**

- E01 dev_evidence.json /columns/98: CORE.DIM_EFC_DATE.DAY_STRING; GET_DDL CORE.DIM_EFC_DATE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/DIM_EFC_DATE/field_map/DAY_STRING

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.DAY_STRING, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F100 CORE.DIM_EFC_DATE.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/99: CORE.DIM_EFC_DATE.CREATED_AT; GET_DDL CORE.DIM_EFC_DATE

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F101 CORE.DIM_EFC_DATE.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/100: CORE.DIM_EFC_DATE.UPDATED_AT; GET_DDL CORE.DIM_EFC_DATE

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.DIM_EFC_DATE.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F102 CORE.FACILITY.FACILITY_ID

**Metadata**

- E01 dev_evidence.json /columns/101: CORE.FACILITY.FACILITY_ID; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:155 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.FACILITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F103 CORE.FACILITY.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/102: CORE.FACILITY.ACCOUNT_ID; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:156 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F104 CORE.FACILITY.FACILITY_NAME

**Metadata**

- E01 dev_evidence.json /columns/103: CORE.FACILITY.FACILITY_NAME; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:157 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.FACILITY_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F105 CORE.FACILITY.FACILITY_TYPE

**Metadata**

- E01 dev_evidence.json /columns/104: CORE.FACILITY.FACILITY_TYPE; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:158 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.FACILITY_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F106 CORE.FACILITY.STATUS

**Metadata**

- E01 dev_evidence.json /columns/105: CORE.FACILITY.STATUS; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:159 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F107 CORE.FACILITY.ACTIVATION_DATE

**Metadata**

- E01 dev_evidence.json /columns/106: CORE.FACILITY.ACTIVATION_DATE; GET_DDL CORE.FACILITY

**Code**

- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:160 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.ACTIVATION_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F108 CORE.FACILITY.CONSTRUCTION_DATE

**Metadata**

- E01 dev_evidence.json /columns/107: CORE.FACILITY.CONSTRUCTION_DATE; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/CONSTRUCTION_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_types/CONSTRUCTION_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:161 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.CONSTRUCTION_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F109 CORE.FACILITY.CLOSURE_DATE

**Metadata**

- E01 dev_evidence.json /columns/108: CORE.FACILITY.CLOSURE_DATE; GET_DDL CORE.FACILITY

**Code**

- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:162 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.CLOSURE_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F110 CORE.FACILITY.DESTRUCTION_DATE

**Metadata**

- E01 dev_evidence.json /columns/109: CORE.FACILITY.DESTRUCTION_DATE; GET_DDL CORE.FACILITY

**Code**

- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:163 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.DESTRUCTION_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F111 CORE.FACILITY.INACTIVE_DATE

**Metadata**

- E01 dev_evidence.json /columns/110: CORE.FACILITY.INACTIVE_DATE; GET_DDL CORE.FACILITY

**Code**

- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:164 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY.INACTIVE_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F112 CORE.FACILITY.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/111: CORE.FACILITY.CREATED_AT; GET_DDL CORE.FACILITY

**Code**

- E05 app/pages/11_Facilities.py:80 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FACILITY.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F113 CORE.FACILITY.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/112: CORE.FACILITY.UPDATED_AT; GET_DDL CORE.FACILITY

**Code**

- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FACILITY.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F114 CORE.FACILITY.FARM_LOCATION_ID

**Metadata**

- E01 dev_evidence.json /columns/113: CORE.FACILITY.FARM_LOCATION_ID; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FARM_LOCATION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)

**Executed query**

- E01 /field_usage: CORE.FACILITY.FARM_LOCATION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F115 CORE.FACILITY.HOUSING_SYSTEM

**Metadata**

- E01 dev_evidence.json /columns/114: CORE.FACILITY.HOUSING_SYSTEM; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/HOUSING_SYSTEM

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)

**Executed query**

- E01 /field_usage: CORE.FACILITY.HOUSING_SYSTEM, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F116 CORE.FACILITY.RENOVATION_DATE

**Metadata**

- E01 dev_evidence.json /columns/115: CORE.FACILITY.RENOVATION_DATE; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/RENOVATION_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_types/RENOVATION_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)

**Executed query**

- E01 /field_usage: CORE.FACILITY.RENOVATION_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F117 CORE.FACILITY.FACILITY_QUOTA

**Metadata**

- E01 dev_evidence.json /columns/116: CORE.FACILITY.FACILITY_QUOTA; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_QUOTA
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_types/FACILITY_QUOTA

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)

**Executed query**

- E01 /field_usage: CORE.FACILITY.FACILITY_QUOTA, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F118 CORE.FACILITY.MANURE_DISPOSAL

**Metadata**

- E01 dev_evidence.json /columns/117: CORE.FACILITY.MANURE_DISPOSAL; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/MANURE_DISPOSAL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)

**Executed query**

- E01 /field_usage: CORE.FACILITY.MANURE_DISPOSAL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F119 CORE.FACILITY.COMMENTS

**Metadata**

- E01 dev_evidence.json /columns/118: CORE.FACILITY.COMMENTS; GET_DDL CORE.FACILITY

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/COMMENTS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)

**Executed query**

- E01 /field_usage: CORE.FACILITY.COMMENTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F120 CORE.FACILITY_DETAIL.FACILITY_DETAIL_ID

**Metadata**

- E01 dev_evidence.json /columns/119: CORE.FACILITY_DETAIL.FACILITY_DETAIL_ID; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/FACILITY_DETAIL_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/13_Facility_Details.py:139 (record payload assignment)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:182 (generate_facility_details, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.FACILITY_DETAIL_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F121 CORE.FACILITY_DETAIL.FACILITY_ID

**Metadata**

- E01 dev_evidence.json /columns/120: CORE.FACILITY_DETAIL.FACILITY_ID; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/FACILITY_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/13_Facility_Details.py:139 (record payload assignment)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:183 (generate_facility_details, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.FACILITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F122 CORE.FACILITY_DETAIL.DETAIL_NAME

**Metadata**

- E01 dev_evidence.json /columns/121: CORE.FACILITY_DETAIL.DETAIL_NAME; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/DETAIL_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/13_Facility_Details.py:139 (record payload assignment)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:184 (generate_facility_details, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.DETAIL_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F123 CORE.FACILITY_DETAIL.DETAIL_TYPE

**Metadata**

- E01 dev_evidence.json /columns/122: CORE.FACILITY_DETAIL.DETAIL_TYPE; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/DETAIL_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/13_Facility_Details.py:139 (record payload assignment)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:185 (generate_facility_details, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.DETAIL_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F124 CORE.FACILITY_DETAIL.STATUS

**Metadata**

- E01 dev_evidence.json /columns/123: CORE.FACILITY_DETAIL.STATUS; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/13_Facility_Details.py:139 (record payload assignment)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:186 (generate_facility_details, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F125 CORE.FACILITY_DETAIL.COMMENTS

**Metadata**

- E01 dev_evidence.json /columns/124: CORE.FACILITY_DETAIL.COMMENTS; GET_DDL CORE.FACILITY_DETAIL

**Code**

- E05 app/pages/13_Facility_Details.py:139 (record payload assignment)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:187 (generate_facility_details, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.COMMENTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F126 CORE.FACILITY_DETAIL.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/125: CORE.FACILITY_DETAIL.CREATED_AT; GET_DDL CORE.FACILITY_DETAIL

**Code**

- E05 app/pages/13_Facility_Details.py:81 (record payload assignment)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F127 CORE.FACILITY_DETAIL.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/126: CORE.FACILITY_DETAIL.UPDATED_AT; GET_DDL CORE.FACILITY_DETAIL

**Code**

- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F128 CORE.FACILITY_DETAIL.EIMS_FACILITY_DETAIL_ID

**Metadata**

- E01 dev_evidence.json /columns/127: CORE.FACILITY_DETAIL.EIMS_FACILITY_DETAIL_ID; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/EIMS_FACILITY_DETAIL_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.EIMS_FACILITY_DETAIL_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F129 CORE.FACILITY_DETAIL.BIRD_COLOUR

**Metadata**

- E01 dev_evidence.json /columns/128: CORE.FACILITY_DETAIL.BIRD_COLOUR; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/BIRD_COLOUR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.BIRD_COLOUR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F130 CORE.FACILITY_DETAIL.BIRDS_HOUSED

**Metadata**

- E01 dev_evidence.json /columns/129: CORE.FACILITY_DETAIL.BIRDS_HOUSED; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/BIRDS_HOUSED
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_types/BIRDS_HOUSED

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.BIRDS_HOUSED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F131 CORE.FACILITY_DETAIL.CAGE_BRAND

**Metadata**

- E01 dev_evidence.json /columns/130: CORE.FACILITY_DETAIL.CAGE_BRAND; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/CAGE_BRAND

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.CAGE_BRAND, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F132 CORE.FACILITY_DETAIL.DATE_INSTALLED

**Metadata**

- E01 dev_evidence.json /columns/131: CORE.FACILITY_DETAIL.DATE_INSTALLED; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/DATE_INSTALLED
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_types/DATE_INSTALLED

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.DATE_INSTALLED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F133 CORE.FACILITY_DETAIL.HEIGHT

**Metadata**

- E01 dev_evidence.json /columns/132: CORE.FACILITY_DETAIL.HEIGHT; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/HEIGHT
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_types/HEIGHT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.HEIGHT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F134 CORE.FACILITY_DETAIL.HIGHEST_BIRDS_PER_CAGE

**Metadata**

- E01 dev_evidence.json /columns/133: CORE.FACILITY_DETAIL.HIGHEST_BIRDS_PER_CAGE; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/HIGHEST_BIRDS_PER_CAGE
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_types/HIGHEST_BIRDS_PER_CAGE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.HIGHEST_BIRDS_PER_CAGE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F135 CORE.FACILITY_DETAIL.LENGTH

**Metadata**

- E01 dev_evidence.json /columns/134: CORE.FACILITY_DETAIL.LENGTH; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/LENGTH
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_types/LENGTH

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.LENGTH, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F136 CORE.FACILITY_DETAIL.NUMBER_OF_CAGES

**Metadata**

- E01 dev_evidence.json /columns/135: CORE.FACILITY_DETAIL.NUMBER_OF_CAGES; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/NUMBER_OF_CAGES
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_types/NUMBER_OF_CAGES

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.NUMBER_OF_CAGES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F137 CORE.FACILITY_DETAIL.SQUARE_INCHES

**Metadata**

- E01 dev_evidence.json /columns/136: CORE.FACILITY_DETAIL.SQUARE_INCHES; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/SQUARE_INCHES
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_types/SQUARE_INCHES

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.SQUARE_INCHES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F138 CORE.FACILITY_DETAIL.WIDTH

**Metadata**

- E01 dev_evidence.json /columns/137: CORE.FACILITY_DETAIL.WIDTH; GET_DDL CORE.FACILITY_DETAIL

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_map/WIDTH
- E05 config/eims_migration_mapping_v3.json /entities/FACILITY_DETAIL/field_types/WIDTH

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:538-538 (upsert_facility_detail)

**Executed query**

- E01 /field_usage: CORE.FACILITY_DETAIL.WIDTH, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F139 CORE.FARM_LOCATION.FARM_LOCATION_ID

**Metadata**

- E01 dev_evidence.json /columns/138: CORE.FARM_LOCATION.FARM_LOCATION_ID; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/FARM_LOCATION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:154 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:336 (generate_farm_locations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.FARM_LOCATION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F140 CORE.FARM_LOCATION.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/139: CORE.FARM_LOCATION.ACCOUNT_ID; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:154 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:337 (generate_farm_locations, fabricated only)
- E05 data/validation.py:52-62 (validate_farm_location)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F141 CORE.FARM_LOCATION.LOCATION_NAME

**Metadata**

- E01 dev_evidence.json /columns/140: CORE.FARM_LOCATION.LOCATION_NAME; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/LOCATION_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:92 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:338 (generate_farm_locations, fabricated only)
- E05 data/validation.py:52-62 (validate_farm_location)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.LOCATION_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F142 CORE.FARM_LOCATION.ADDRESS_1

**Metadata**

- E01 dev_evidence.json /columns/141: CORE.FARM_LOCATION.ADDRESS_1; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/ADDRESS_1

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:155 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:339 (generate_farm_locations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.ADDRESS_1, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F143 CORE.FARM_LOCATION.ADDRESS_2

**Metadata**

- E01 dev_evidence.json /columns/142: CORE.FARM_LOCATION.ADDRESS_2; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/ADDRESS_2

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:156 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:340 (generate_farm_locations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.ADDRESS_2, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F144 CORE.FARM_LOCATION.CITY

**Metadata**

- E01 dev_evidence.json /columns/143: CORE.FARM_LOCATION.CITY; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/CITY

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:156 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:341 (generate_farm_locations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.CITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F145 CORE.FARM_LOCATION.PROVINCE

**Metadata**

- E01 dev_evidence.json /columns/144: CORE.FARM_LOCATION.PROVINCE; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/PROVINCE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:157 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:342 (generate_farm_locations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.PROVINCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F146 CORE.FARM_LOCATION.POSTAL_CODE

**Metadata**

- E01 dev_evidence.json /columns/145: CORE.FARM_LOCATION.POSTAL_CODE; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/POSTAL_CODE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:157 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:343 (generate_farm_locations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.POSTAL_CODE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F147 CORE.FARM_LOCATION.PHONE

**Metadata**

- E01 dev_evidence.json /columns/146: CORE.FARM_LOCATION.PHONE; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/PHONE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:158 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:344 (generate_farm_locations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.PHONE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F148 CORE.FARM_LOCATION.STATUS

**Metadata**

- E01 dev_evidence.json /columns/147: CORE.FARM_LOCATION.STATUS; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/18_Farm_Locations.py:158 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:345 (generate_farm_locations, fabricated only)
- E05 data/validation.py:52-62 (validate_farm_location)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F149 CORE.FARM_LOCATION.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/148: CORE.FARM_LOCATION.CREATED_AT; GET_DDL CORE.FARM_LOCATION

**Code**

- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F150 CORE.FARM_LOCATION.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/149: CORE.FARM_LOCATION.UPDATED_AT; GET_DDL CORE.FARM_LOCATION

**Code**

- E05 app/pages/18_Farm_Locations.py:92 (record payload assignment)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F151 CORE.FARM_LOCATION.FAX

**Metadata**

- E01 dev_evidence.json /columns/150: CORE.FARM_LOCATION.FAX; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/FAX

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.FAX, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F152 CORE.FARM_LOCATION.EIMS_LOCATION_ID

**Metadata**

- E01 dev_evidence.json /columns/151: CORE.FARM_LOCATION.EIMS_LOCATION_ID; GET_DDL CORE.FARM_LOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FARM_LOCATION/field_map/EIMS_LOCATION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:521-524 (upsert_farm_location)

**Executed query**

- E01 /field_usage: CORE.FARM_LOCATION.EIMS_LOCATION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F153 CORE.FLOCK.FLOCK_ID

**Metadata**

- E01 dev_evidence.json /columns/152: CORE.FLOCK.FLOCK_ID; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/FLOCK_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:255 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.FLOCK_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F154 CORE.FLOCK.FLOCK_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/153: CORE.FLOCK.FLOCK_NUMBER; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/fallbacks/FLOCK_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:80 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:261 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.FLOCK_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F155 CORE.FLOCK.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/154: CORE.FLOCK.ACCOUNT_ID; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:256 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/FACILITY_FLOCK_DESIGN.md: Sara 8 October permits sequential/concurrent Flocks; cross-Account use not approved.

## F156 CORE.FLOCK.FACILITY_ID

**Metadata**

- E01 dev_evidence.json /columns/155: CORE.FLOCK.FACILITY_ID; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/FACILITY_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:257 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.FACILITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/FACILITY_FLOCK_DESIGN.md: Sara 8 October permits sequential/concurrent Flocks; cross-Account use not approved.

## F157 CORE.FLOCK.FACILITY_DETAIL_ID

**Metadata**

- E01 dev_evidence.json /columns/156: CORE.FLOCK.FACILITY_DETAIL_ID; GET_DDL CORE.FLOCK

**Code**

- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:258 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.FACILITY_DETAIL_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F158 CORE.FLOCK.QUOTA_ID

**Metadata**

- E01 dev_evidence.json /columns/157: CORE.FLOCK.QUOTA_ID; GET_DDL CORE.FLOCK

**Code**

- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:259 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.QUOTA_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F159 CORE.FLOCK.FLOCK_QUOTA_TYPE

**Metadata**

- E01 dev_evidence.json /columns/158: CORE.FLOCK.FLOCK_QUOTA_TYPE; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/FLOCK_QUOTA_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:260 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.FLOCK_QUOTA_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F160 CORE.FLOCK.STATUS

**Metadata**

- E01 dev_evidence.json /columns/159: CORE.FLOCK.STATUS; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:291 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F161 CORE.FLOCK.CREATE_DELIVERY_TRANSACTION

**Metadata**

- E01 dev_evidence.json /columns/160: CORE.FLOCK.CREATE_DELIVERY_TRANSACTION; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/CREATE_DELIVERY_TRANSACTION
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/CREATE_DELIVERY_TRANSACTION

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:289 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.CREATE_DELIVERY_TRANSACTION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F162 CORE.FLOCK.PERMIT_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/161: CORE.FLOCK.PERMIT_NUMBER; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/PERMIT_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:262 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.PERMIT_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F163 CORE.FLOCK.PERMIT_DATE

**Metadata**

- E01 dev_evidence.json /columns/162: CORE.FLOCK.PERMIT_DATE; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/PERMIT_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/PERMIT_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:263 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.PERMIT_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F164 CORE.FLOCK.HATCH_DATE

**Metadata**

- E01 dev_evidence.json /columns/163: CORE.FLOCK.HATCH_DATE; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/HATCH_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/HATCH_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:268 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.HATCH_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F165 CORE.FLOCK.DATE_ORDERED

**Metadata**

- E01 dev_evidence.json /columns/164: CORE.FLOCK.DATE_ORDERED; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/DATE_ORDERED
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/DATE_ORDERED

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:264 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.DATE_ORDERED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F166 CORE.FLOCK.BIRD_COUNT

**Metadata**

- E01 dev_evidence.json /columns/165: CORE.FLOCK.BIRD_COUNT; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/BIRD_COUNT
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/BIRD_COUNT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:266 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.BIRD_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F167 CORE.FLOCK.EGG_COLOUR

**Metadata**

- E01 dev_evidence.json /columns/166: CORE.FLOCK.EGG_COLOUR; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/EGG_COLOUR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:269 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.EGG_COLOUR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F168 CORE.FLOCK.BIRD_STRAIN

**Metadata**

- E01 dev_evidence.json /columns/167: CORE.FLOCK.BIRD_STRAIN; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/BIRD_STRAIN

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:283 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.BIRD_STRAIN, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F169 CORE.FLOCK.PLACEMENT_DATE

**Metadata**

- E01 dev_evidence.json /columns/168: CORE.FLOCK.PLACEMENT_DATE; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/PLACEMENT_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/PLACEMENT_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:267 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.PLACEMENT_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F170 CORE.FLOCK.EST_DISPOSAL

**Metadata**

- E01 dev_evidence.json /columns/169: CORE.FLOCK.EST_DISPOSAL; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/EST_DISPOSAL
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/EST_DISPOSAL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:271 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.EST_DISPOSAL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F171 CORE.FLOCK.DISPOSAL_DATE

**Metadata**

- E01 dev_evidence.json /columns/170: CORE.FLOCK.DISPOSAL_DATE; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/DISPOSAL_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/DISPOSAL_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:277 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.DISPOSAL_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F172 CORE.FLOCK.BIRDS_DISPOSED

**Metadata**

- E01 dev_evidence.json /columns/171: CORE.FLOCK.BIRDS_DISPOSED; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/BIRDS_DISPOSED
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/BIRDS_DISPOSED

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:282 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: CORE.FLOCK.BIRDS_DISPOSED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F173 CORE.FLOCK.BREEDER

**Metadata**

- E01 dev_evidence.json /columns/172: CORE.FLOCK.BREEDER; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/BREEDER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/synthetic.py:284 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.BREEDER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F174 CORE.FLOCK.HATCHERY

**Metadata**

- E01 dev_evidence.json /columns/173: CORE.FLOCK.HATCHERY; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/HATCHERY

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/synthetic.py:285 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.HATCHERY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F175 CORE.FLOCK.PULLET_GROWER

**Metadata**

- E01 dev_evidence.json /columns/174: CORE.FLOCK.PULLET_GROWER; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/PULLET_GROWER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/synthetic.py:286 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.PULLET_GROWER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F176 CORE.FLOCK.DISPOSAL_PLANT

**Metadata**

- E01 dev_evidence.json /columns/175: CORE.FLOCK.DISPOSAL_PLANT; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/DISPOSAL_PLANT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/synthetic.py:287 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.DISPOSAL_PLANT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F177 CORE.FLOCK.DISPOSAL_METHOD

**Metadata**

- E01 dev_evidence.json /columns/176: CORE.FLOCK.DISPOSAL_METHOD; GET_DDL CORE.FLOCK

**Code**

- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:290 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.DISPOSAL_METHOD, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F178 CORE.FLOCK.COMMENTS

**Metadata**

- E01 dev_evidence.json /columns/177: CORE.FLOCK.COMMENTS; GET_DDL CORE.FLOCK

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/COMMENTS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:288 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK.COMMENTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F179 CORE.FLOCK.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/178: CORE.FLOCK.CREATED_AT; GET_DDL CORE.FLOCK

**Code**

- E05 app/pages/5_Flocks.py:80 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FLOCK.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F180 CORE.FLOCK.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/179: CORE.FLOCK.UPDATED_AT; GET_DDL CORE.FLOCK

**Code**

- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FLOCK.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F181 CORE.FLOCK_TRANSACTION.FLOCK_TRANSACTION_ID

**Metadata**

- E01 dev_evidence.json /columns/180: CORE.FLOCK_TRANSACTION.FLOCK_TRANSACTION_ID; GET_DDL CORE.FLOCK_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/field_map/FLOCK_TRANSACTION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/6_Flock_Transactions.py:89 (record payload assignment)
- E05 data/repositories/snowflake.py:558-562 (upsert_flock_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:313 (generate_flock_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK_TRANSACTION.FLOCK_TRANSACTION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F182 CORE.FLOCK_TRANSACTION.FLOCK_ID

**Metadata**

- E01 dev_evidence.json /columns/181: CORE.FLOCK_TRANSACTION.FLOCK_ID; GET_DDL CORE.FLOCK_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/field_map/FLOCK_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/6_Flock_Transactions.py:89 (record payload assignment)
- E05 data/repositories/snowflake.py:558-562 (upsert_flock_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:314 (generate_flock_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK_TRANSACTION.FLOCK_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F183 CORE.FLOCK_TRANSACTION.TRANSACTION_TYPE

**Metadata**

- E01 dev_evidence.json /columns/182: CORE.FLOCK_TRANSACTION.TRANSACTION_TYPE; GET_DDL CORE.FLOCK_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/field_map/TRANSACTION_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/6_Flock_Transactions.py:89 (record payload assignment)
- E05 data/repositories/snowflake.py:558-562 (upsert_flock_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:315 (generate_flock_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK_TRANSACTION.TRANSACTION_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F184 CORE.FLOCK_TRANSACTION.QUANTITY

**Metadata**

- E01 dev_evidence.json /columns/183: CORE.FLOCK_TRANSACTION.QUANTITY; GET_DDL CORE.FLOCK_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/field_map/QUANTITY
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/field_types/QUANTITY
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/numeric_rules/QUANTITY

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/6_Flock_Transactions.py:89 (record payload assignment)
- E05 data/repositories/snowflake.py:558-562 (upsert_flock_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:316 (generate_flock_transactions, fabricated only)
- E05 data/migration.py:244-254 (_rule_error)

**Executed query**

- E01 /field_usage: CORE.FLOCK_TRANSACTION.QUANTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F185 CORE.FLOCK_TRANSACTION.TRANSACTION_DATE

**Metadata**

- E01 dev_evidence.json /columns/184: CORE.FLOCK_TRANSACTION.TRANSACTION_DATE; GET_DDL CORE.FLOCK_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/field_map/TRANSACTION_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/field_types/TRANSACTION_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/6_Flock_Transactions.py:89 (record payload assignment)
- E05 data/repositories/snowflake.py:558-562 (upsert_flock_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:317 (generate_flock_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK_TRANSACTION.TRANSACTION_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F186 CORE.FLOCK_TRANSACTION.NOTES

**Metadata**

- E01 dev_evidence.json /columns/185: CORE.FLOCK_TRANSACTION.NOTES; GET_DDL CORE.FLOCK_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK_TRANSACTION/field_map/NOTES

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/6_Flock_Transactions.py:89 (record payload assignment)
- E05 data/repositories/snowflake.py:558-562 (upsert_flock_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:318 (generate_flock_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.FLOCK_TRANSACTION.NOTES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F187 CORE.FLOCK_TRANSACTION.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/186: CORE.FLOCK_TRANSACTION.CREATED_AT; GET_DDL CORE.FLOCK_TRANSACTION

**Code**

- E05 app/pages/6_Flock_Transactions.py:52 (record payload assignment)
- E05 data/repositories/snowflake.py:558-562 (upsert_flock_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FLOCK_TRANSACTION.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F188 CORE.FLOCK_TRANSACTION.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/187: CORE.FLOCK_TRANSACTION.UPDATED_AT; GET_DDL CORE.FLOCK_TRANSACTION

**Code**

- E05 data/repositories/snowflake.py:558-562 (upsert_flock_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.FLOCK_TRANSACTION.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F189 CORE.PRODUCTION_RECORD.PRODUCTION_ID

**Metadata**

- E01 dev_evidence.json /columns/188: CORE.PRODUCTION_RECORD.PRODUCTION_ID; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/PRODUCTION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:468 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.PRODUCTION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F190 CORE.PRODUCTION_RECORD.IMPORT_ID

**Metadata**

- E01 dev_evidence.json /columns/189: CORE.PRODUCTION_RECORD.IMPORT_ID; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:469 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.IMPORT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E02 /results/production_reference_IMPORT_ID: non-null, matched and orphan counts only.

## F191 CORE.PRODUCTION_RECORD.PRODUCER_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/190: CORE.PRODUCTION_RECORD.PRODUCER_ACCOUNT_ID; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/PRODUCER_ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:471 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.PRODUCER_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.
- E02 /results/production_reference_PRODUCER_ACCOUNT_ID: non-null, matched and orphan counts only.

## F192 CORE.PRODUCTION_RECORD.GRADER_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/191: CORE.PRODUCTION_RECORD.GRADER_ACCOUNT_ID; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/GRADER_ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:472 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.GRADER_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E02 /results/production_reference_GRADER_ACCOUNT_ID: non-null, matched and orphan counts only.

## F193 CORE.PRODUCTION_RECORD.FACILITY_ID

**Metadata**

- E01 dev_evidence.json /columns/192: CORE.PRODUCTION_RECORD.FACILITY_ID; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:473 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.FACILITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E02 /results/production_reference_FACILITY_ID: non-null, matched and orphan counts only.

## F194 CORE.PRODUCTION_RECORD.FLOCK_ID

**Metadata**

- E01 dev_evidence.json /columns/193: CORE.PRODUCTION_RECORD.FLOCK_ID; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:474 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.FLOCK_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E02 /results/production_reference_FLOCK_ID: non-null, matched and orphan counts only.

## F195 CORE.PRODUCTION_RECORD.GRADER_NAME

**Metadata**

- E01 dev_evidence.json /columns/194: CORE.PRODUCTION_RECORD.GRADER_NAME; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/GRADER_NAME
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.GRADER_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F196 CORE.PRODUCTION_RECORD.PRODUCER_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/195: CORE.PRODUCTION_RECORD.PRODUCER_NUMBER; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:470 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/PRODUCER_NUMBER
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.PRODUCER_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F197 CORE.PRODUCTION_RECORD.GRADER_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/196: CORE.PRODUCTION_RECORD.GRADER_NUMBER; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:475 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/GRADER_NUMBER
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.GRADER_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F198 CORE.PRODUCTION_RECORD.BARN_IDENTITY

**Metadata**

- E01 dev_evidence.json /columns/197: CORE.PRODUCTION_RECORD.BARN_IDENTITY; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:476 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.BARN_IDENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F199 CORE.PRODUCTION_RECORD.SOURCE_WEEK_CODE

**Metadata**

- E01 dev_evidence.json /columns/198: CORE.PRODUCTION_RECORD.SOURCE_WEEK_CODE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/SOURCE_WEEK_CODE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:492 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/SOURCE_WEEK_CODE
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.SOURCE_WEEK_CODE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F200 CORE.PRODUCTION_RECORD.REPORTING_YEAR

**Metadata**

- E01 dev_evidence.json /columns/199: CORE.PRODUCTION_RECORD.REPORTING_YEAR; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/REPORTING_YEAR
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/REPORTING_YEAR
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/numeric_rules/REPORTING_YEAR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/migration.py:193-203 (parse_reporting_period)
- E05 data/synthetic.py:487 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/migration.py:244-254 (_rule_error)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.REPORTING_YEAR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F201 CORE.PRODUCTION_RECORD.REPORTING_WEEK

**Metadata**

- E01 dev_evidence.json /columns/200: CORE.PRODUCTION_RECORD.REPORTING_WEEK; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/REPORTING_WEEK
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/REPORTING_WEEK
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/numeric_rules/REPORTING_WEEK

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/migration.py:193-203 (parse_reporting_period)
- E05 data/synthetic.py:488 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/migration.py:244-254 (_rule_error)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.REPORTING_WEEK, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F202 CORE.PRODUCTION_RECORD.MARKETING_TYPE

**Metadata**

- E01 dev_evidence.json /columns/201: CORE.PRODUCTION_RECORD.MARKETING_TYPE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/MARKETING_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/MARKETING_TYPE
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.MARKETING_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F203 CORE.PRODUCTION_RECORD.HOUSING_SYSTEM

**Metadata**

- E01 dev_evidence.json /columns/202: CORE.PRODUCTION_RECORD.HOUSING_SYSTEM; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/HOUSING_SYSTEM

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/HOUSING_SYSTEM
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.HOUSING_SYSTEM, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F204 CORE.PRODUCTION_RECORD.EGG_TYPE

**Metadata**

- E01 dev_evidence.json /columns/203: CORE.PRODUCTION_RECORD.EGG_TYPE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/EGG_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/EGG_TYPE
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.EGG_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F205 CORE.PRODUCTION_RECORD.EGG_COLOUR

**Metadata**

- E01 dev_evidence.json /columns/204: CORE.PRODUCTION_RECORD.EGG_COLOUR; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/EGG_COLOUR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:478 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/EGG_COLOUR
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.EGG_COLOUR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F206 CORE.PRODUCTION_RECORD.FLOCK_AGE

**Metadata**

- E01 dev_evidence.json /columns/205: CORE.PRODUCTION_RECORD.FLOCK_AGE; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:477 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.FLOCK_AGE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F207 CORE.PRODUCTION_RECORD.NET_WEIGHT

**Metadata**

- E01 dev_evidence.json /columns/206: CORE.PRODUCTION_RECORD.NET_WEIGHT; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:479 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NET_WEIGHT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F208 CORE.PRODUCTION_RECORD.NET_BOXES

**Metadata**

- E01 dev_evidence.json /columns/207: CORE.PRODUCTION_RECORD.NET_BOXES; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:480 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NET_BOXES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F209 CORE.PRODUCTION_RECORD.NET_PER_BOX

**Metadata**

- E01 dev_evidence.json /columns/208: CORE.PRODUCTION_RECORD.NET_PER_BOX; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:481 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NET_PER_BOX, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F210 CORE.PRODUCTION_RECORD.JUMBO

**Metadata**

- E01 dev_evidence.json /columns/209: CORE.PRODUCTION_RECORD.JUMBO; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/JUMBO
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/JUMBO

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/JUMBO
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.JUMBO, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F211 CORE.PRODUCTION_RECORD.EXTRA_LARGE

**Metadata**

- E01 dev_evidence.json /columns/210: CORE.PRODUCTION_RECORD.EXTRA_LARGE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/EXTRA_LARGE
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/EXTRA_LARGE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/EXTRA_LARGE
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.EXTRA_LARGE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F212 CORE.PRODUCTION_RECORD.LARGE

**Metadata**

- E01 dev_evidence.json /columns/211: CORE.PRODUCTION_RECORD.LARGE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/LARGE
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/LARGE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/LARGE
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.LARGE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F213 CORE.PRODUCTION_RECORD.MEDIUM

**Metadata**

- E01 dev_evidence.json /columns/212: CORE.PRODUCTION_RECORD.MEDIUM; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/MEDIUM
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/MEDIUM

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/MEDIUM
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.MEDIUM, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F214 CORE.PRODUCTION_RECORD.SMALL

**Metadata**

- E01 dev_evidence.json /columns/213: CORE.PRODUCTION_RECORD.SMALL; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/SMALL
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/SMALL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/SMALL
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.SMALL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F215 CORE.PRODUCTION_RECORD.PEEWEE

**Metadata**

- E01 dev_evidence.json /columns/214: CORE.PRODUCTION_RECORD.PEEWEE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/PEEWEE
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/PEEWEE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/PEEWEE
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.PEEWEE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F216 CORE.PRODUCTION_RECORD.GRADE_B

**Metadata**

- E01 dev_evidence.json /columns/215: CORE.PRODUCTION_RECORD.GRADE_B; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/GRADE_B
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/GRADE_B

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/GRADE_B
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.GRADE_B, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F217 CORE.PRODUCTION_RECORD.GRADE_C

**Metadata**

- E01 dev_evidence.json /columns/216: CORE.PRODUCTION_RECORD.GRADE_C; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/GRADE_C
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/GRADE_C

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/GRADE_C
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.GRADE_C, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F218 CORE.PRODUCTION_RECORD.CRACKS

**Metadata**

- E01 dev_evidence.json /columns/217: CORE.PRODUCTION_RECORD.CRACKS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/CRACKS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/CRACKS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/CRACKS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.CRACKS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F219 CORE.PRODUCTION_RECORD.NEST_RUN

**Metadata**

- E01 dev_evidence.json /columns/218: CORE.PRODUCTION_RECORD.NEST_RUN; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F220 CORE.PRODUCTION_RECORD.NEST_RUN_25_PLUS

**Metadata**

- E01 dev_evidence.json /columns/219: CORE.PRODUCTION_RECORD.NEST_RUN_25_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_25_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_25_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_25_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_25_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F221 CORE.PRODUCTION_RECORD.NEST_RUN_24_PLUS

**Metadata**

- E01 dev_evidence.json /columns/220: CORE.PRODUCTION_RECORD.NEST_RUN_24_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_24_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_24_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_24_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_24_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F222 CORE.PRODUCTION_RECORD.NEST_RUN_23_PLUS

**Metadata**

- E01 dev_evidence.json /columns/221: CORE.PRODUCTION_RECORD.NEST_RUN_23_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_23_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_23_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_23_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_23_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F223 CORE.PRODUCTION_RECORD.NEST_RUN_22_PLUS

**Metadata**

- E01 dev_evidence.json /columns/222: CORE.PRODUCTION_RECORD.NEST_RUN_22_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_22_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_22_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_22_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_22_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F224 CORE.PRODUCTION_RECORD.NEST_RUN_21_PLUS

**Metadata**

- E01 dev_evidence.json /columns/223: CORE.PRODUCTION_RECORD.NEST_RUN_21_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_21_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_21_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_21_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_21_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F225 CORE.PRODUCTION_RECORD.NEST_RUN_20_PLUS

**Metadata**

- E01 dev_evidence.json /columns/224: CORE.PRODUCTION_RECORD.NEST_RUN_20_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_20_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_20_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_20_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_20_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F226 CORE.PRODUCTION_RECORD.NEST_RUN_19_PLUS

**Metadata**

- E01 dev_evidence.json /columns/225: CORE.PRODUCTION_RECORD.NEST_RUN_19_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_19_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_19_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_19_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_19_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F227 CORE.PRODUCTION_RECORD.NEST_RUN_18_PLUS

**Metadata**

- E01 dev_evidence.json /columns/226: CORE.PRODUCTION_RECORD.NEST_RUN_18_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_18_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_18_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_18_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_18_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F228 CORE.PRODUCTION_RECORD.NEST_RUN_17_PLUS

**Metadata**

- E01 dev_evidence.json /columns/227: CORE.PRODUCTION_RECORD.NEST_RUN_17_PLUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/NEST_RUN_17_PLUS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/NEST_RUN_17_PLUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/NEST_RUN_17_PLUS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.NEST_RUN_17_PLUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F229 CORE.PRODUCTION_RECORD.OTHER_LEVIABLE

**Metadata**

- E01 dev_evidence.json /columns/228: CORE.PRODUCTION_RECORD.OTHER_LEVIABLE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/OTHER_LEVIABLE
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/OTHER_LEVIABLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/OTHER_LEVIABLE
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.OTHER_LEVIABLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F230 CORE.PRODUCTION_RECORD.OTHER_NON_LEVIABLE

**Metadata**

- E01 dev_evidence.json /columns/229: CORE.PRODUCTION_RECORD.OTHER_NON_LEVIABLE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/OTHER_NON_LEVIABLE
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/OTHER_NON_LEVIABLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/OTHER_NON_LEVIABLE
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.OTHER_NON_LEVIABLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F231 CORE.PRODUCTION_RECORD.FARM_GATE_SALES

**Metadata**

- E01 dev_evidence.json /columns/230: CORE.PRODUCTION_RECORD.FARM_GATE_SALES; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/FARM_GATE_SALES
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/FARM_GATE_SALES

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/FARM_GATE_SALES
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.FARM_GATE_SALES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F232 CORE.PRODUCTION_RECORD.ON_FARM_CONSUMPTION

**Metadata**

- E01 dev_evidence.json /columns/231: CORE.PRODUCTION_RECORD.ON_FARM_CONSUMPTION; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/ON_FARM_CONSUMPTION
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/ON_FARM_CONSUMPTION

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/ON_FARM_CONSUMPTION
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.ON_FARM_CONSUMPTION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F233 CORE.PRODUCTION_RECORD.SUBTOTAL

**Metadata**

- E01 dev_evidence.json /columns/232: CORE.PRODUCTION_RECORD.SUBTOTAL; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/SUBTOTAL
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.SUBTOTAL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F234 CORE.PRODUCTION_RECORD.REJECTS

**Metadata**

- E01 dev_evidence.json /columns/233: CORE.PRODUCTION_RECORD.REJECTS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/REJECTS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/REJECTS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/REJECTS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.REJECTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F235 CORE.PRODUCTION_RECORD.LEAKERS

**Metadata**

- E01 dev_evidence.json /columns/234: CORE.PRODUCTION_RECORD.LEAKERS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/LEAKERS
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/LEAKERS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/LEAKERS
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.LEAKERS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F236 CORE.PRODUCTION_RECORD.TOTAL

**Metadata**

- E01 dev_evidence.json /columns/235: CORE.PRODUCTION_RECORD.TOTAL; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/TOTAL
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/TOTAL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/TOTAL
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.TOTAL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F237 CORE.PRODUCTION_RECORD.TOTAL_RECEIVED

**Metadata**

- E01 dev_evidence.json /columns/236: CORE.PRODUCTION_RECORD.TOTAL_RECEIVED; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:482 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.TOTAL_RECEIVED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F238 CORE.PRODUCTION_RECORD.REJECTED

**Metadata**

- E01 dev_evidence.json /columns/237: CORE.PRODUCTION_RECORD.REJECTED; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:483 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.REJECTED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F239 CORE.PRODUCTION_RECORD.LOSS

**Metadata**

- E01 dev_evidence.json /columns/238: CORE.PRODUCTION_RECORD.LOSS; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:484 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.LOSS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F240 CORE.PRODUCTION_RECORD.LEGACY_REJECT_LOSS_TOTAL

**Metadata**

- E01 dev_evidence.json /columns/239: CORE.PRODUCTION_RECORD.LEGACY_REJECT_LOSS_TOTAL; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:485 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.LEGACY_REJECT_LOSS_TOTAL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F241 CORE.PRODUCTION_RECORD.TOTAL_ACCEPTED

**Metadata**

- E01 dev_evidence.json /columns/240: CORE.PRODUCTION_RECORD.TOTAL_ACCEPTED; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/synthetic.py:486 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.TOTAL_ACCEPTED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F242 CORE.PRODUCTION_RECORD.SOURCE_TYPE

**Metadata**

- E01 dev_evidence.json /columns/241: CORE.PRODUCTION_RECORD.SOURCE_TYPE; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/constants/SOURCE_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:489 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.SOURCE_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F243 CORE.PRODUCTION_RECORD.MATCH_STATUS

**Metadata**

- E01 dev_evidence.json /columns/242: CORE.PRODUCTION_RECORD.MATCH_STATUS; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/constants/MATCH_STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:490 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.MATCH_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F244 CORE.PRODUCTION_RECORD.SOURCE_ROW_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/243: CORE.PRODUCTION_RECORD.SOURCE_ROW_NUMBER; GET_DDL CORE.PRODUCTION_RECORD

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/row_number_fields
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/SOURCE_ROW_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:491 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.SOURCE_ROW_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F245 CORE.PRODUCTION_RECORD.MATCH_CONFIRMED_AT

**Metadata**

- E01 dev_evidence.json /columns/244: CORE.PRODUCTION_RECORD.MATCH_CONFIRMED_AT; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.MATCH_CONFIRMED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F246 CORE.PRODUCTION_RECORD.MATCH_CONFIRMED_BY

**Metadata**

- E01 dev_evidence.json /columns/245: CORE.PRODUCTION_RECORD.MATCH_CONFIRMED_BY; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.MATCH_CONFIRMED_BY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F247 CORE.PRODUCTION_RECORD.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/246: CORE.PRODUCTION_RECORD.CREATED_AT; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F248 CORE.PRODUCTION_RECORD.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/247: CORE.PRODUCTION_RECORD.UPDATED_AT; GET_DDL CORE.PRODUCTION_RECORD

**Code**

- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_RECORD.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F249 CORE.PRODUCTION_SIZE_BREAKDOWN.SIZE_BREAKDOWN_ID

**Metadata**

- E01 dev_evidence.json /columns/248: CORE.PRODUCTION_SIZE_BREAKDOWN.SIZE_BREAKDOWN_ID; GET_DDL CORE.PRODUCTION_SIZE_BREAKDOWN

**Code**

- E05 data/synthetic.py:515 (generate_size_breakdown, fabricated only)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_SIZE_BREAKDOWN.SIZE_BREAKDOWN_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F250 CORE.PRODUCTION_SIZE_BREAKDOWN.PRODUCTION_ID

**Metadata**

- E01 dev_evidence.json /columns/249: CORE.PRODUCTION_SIZE_BREAKDOWN.PRODUCTION_ID; GET_DDL CORE.PRODUCTION_SIZE_BREAKDOWN

**Code**

- E05 data/synthetic.py:516 (generate_size_breakdown, fabricated only)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_SIZE_BREAKDOWN.PRODUCTION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F251 CORE.PRODUCTION_SIZE_BREAKDOWN.SIZE_BAND

**Metadata**

- E01 dev_evidence.json /columns/250: CORE.PRODUCTION_SIZE_BREAKDOWN.SIZE_BAND; GET_DDL CORE.PRODUCTION_SIZE_BREAKDOWN

**Code**

- E05 data/synthetic.py:517 (generate_size_breakdown, fabricated only)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_SIZE_BREAKDOWN.SIZE_BAND, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F252 CORE.PRODUCTION_SIZE_BREAKDOWN.QUANTITY

**Metadata**

- E01 dev_evidence.json /columns/251: CORE.PRODUCTION_SIZE_BREAKDOWN.QUANTITY; GET_DDL CORE.PRODUCTION_SIZE_BREAKDOWN

**Code**

- E05 data/synthetic.py:518 (generate_size_breakdown, fabricated only)

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_SIZE_BREAKDOWN.QUANTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F253 CORE.PRODUCTION_SIZE_BREAKDOWN.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/252: CORE.PRODUCTION_SIZE_BREAKDOWN.CREATED_AT; GET_DDL CORE.PRODUCTION_SIZE_BREAKDOWN

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_SIZE_BREAKDOWN.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F254 CORE.PRODUCTION_SIZE_BREAKDOWN.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/253: CORE.PRODUCTION_SIZE_BREAKDOWN.UPDATED_AT; GET_DDL CORE.PRODUCTION_SIZE_BREAKDOWN

**Executed query**

- E01 /field_usage: CORE.PRODUCTION_SIZE_BREAKDOWN.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F255 CORE.QUOTA_ALLOCATION.QUOTA_ALLOCATION_ID

**Metadata**

- E01 dev_evidence.json /columns/254: CORE.QUOTA_ALLOCATION.QUOTA_ALLOCATION_ID; GET_DDL CORE.QUOTA_ALLOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_map/QUOTA_ALLOCATION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.QUOTA_ALLOCATION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F256 CORE.QUOTA_ALLOCATION.ALLOCATION_COUNT

**Metadata**

- E01 dev_evidence.json /columns/255: CORE.QUOTA_ALLOCATION.ALLOCATION_COUNT; GET_DDL CORE.QUOTA_ALLOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_map/ALLOCATION_COUNT
- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_types/ALLOCATION_COUNT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.ALLOCATION_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F257 CORE.QUOTA_ALLOCATION.COMMENTS

**Metadata**

- E01 dev_evidence.json /columns/256: CORE.QUOTA_ALLOCATION.COMMENTS; GET_DDL CORE.QUOTA_ALLOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_map/COMMENTS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.COMMENTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F258 CORE.QUOTA_ALLOCATION.EFFECTIVE_DATE

**Metadata**

- E01 dev_evidence.json /columns/257: CORE.QUOTA_ALLOCATION.EFFECTIVE_DATE; GET_DDL CORE.QUOTA_ALLOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_map/EFFECTIVE_DATE
- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_types/EFFECTIVE_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.EFFECTIVE_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F259 CORE.QUOTA_ALLOCATION.EIMS_ALLOCATION_ID

**Metadata**

- E01 dev_evidence.json /columns/258: CORE.QUOTA_ALLOCATION.EIMS_ALLOCATION_ID; GET_DDL CORE.QUOTA_ALLOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_map/EIMS_ALLOCATION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.EIMS_ALLOCATION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F260 CORE.QUOTA_ALLOCATION.PROVINCE

**Metadata**

- E01 dev_evidence.json /columns/259: CORE.QUOTA_ALLOCATION.PROVINCE; GET_DDL CORE.QUOTA_ALLOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_map/PROVINCE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.PROVINCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F261 CORE.QUOTA_ALLOCATION.QUOTA_TYPE

**Metadata**

- E01 dev_evidence.json /columns/260: CORE.QUOTA_ALLOCATION.QUOTA_TYPE; GET_DDL CORE.QUOTA_ALLOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_map/QUOTA_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.QUOTA_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F262 CORE.QUOTA_ALLOCATION.STATUS

**Metadata**

- E01 dev_evidence.json /columns/261: CORE.QUOTA_ALLOCATION.STATUS; GET_DDL CORE.QUOTA_ALLOCATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_ALLOCATION/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F263 CORE.QUOTA_ALLOCATION.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/262: CORE.QUOTA_ALLOCATION.CREATED_AT; GET_DDL CORE.QUOTA_ALLOCATION

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F264 CORE.QUOTA_ALLOCATION.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/263: CORE.QUOTA_ALLOCATION.UPDATED_AT; GET_DDL CORE.QUOTA_ALLOCATION

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.QUOTA_ALLOCATION.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F265 CORE.QUOTA_REGISTRATION.QUOTA_ID

**Metadata**

- E01 dev_evidence.json /columns/264: CORE.QUOTA_REGISTRATION.QUOTA_ID; GET_DDL CORE.QUOTA_REGISTRATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_map/QUOTA_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/7_Quota_Registrations.py:212 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:203 (generate_quota_registrations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.QUOTA_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F266 CORE.QUOTA_REGISTRATION.REGISTRATION_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/265: CORE.QUOTA_REGISTRATION.REGISTRATION_NUMBER; GET_DDL CORE.QUOTA_REGISTRATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_map/REGISTRATION_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/7_Quota_Registrations.py:127 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:204 (generate_quota_registrations, fabricated only)
- E05 data/validation.py:169-182 (validate_quota_registration)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.REGISTRATION_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 historical correction confirmation / docs/eims_historical_corrections.md: history may lack registration number.

## F267 CORE.QUOTA_REGISTRATION.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/266: CORE.QUOTA_REGISTRATION.ACCOUNT_ID; GET_DDL CORE.QUOTA_REGISTRATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/7_Quota_Registrations.py:212 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:205 (generate_quota_registrations, fabricated only)
- E05 data/validation.py:169-182 (validate_quota_registration)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F268 CORE.QUOTA_REGISTRATION.QUOTA_NAME

**Metadata**

- E01 dev_evidence.json /columns/267: CORE.QUOTA_REGISTRATION.QUOTA_NAME; GET_DDL CORE.QUOTA_REGISTRATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_map/QUOTA_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/7_Quota_Registrations.py:128 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:206 (generate_quota_registrations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.QUOTA_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F269 CORE.QUOTA_REGISTRATION.QUOTA_TYPE

**Metadata**

- E01 dev_evidence.json /columns/268: CORE.QUOTA_REGISTRATION.QUOTA_TYPE; GET_DDL CORE.QUOTA_REGISTRATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_map/QUOTA_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/7_Quota_Registrations.py:212 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:207 (generate_quota_registrations, fabricated only)
- E05 data/validation.py:169-182 (validate_quota_registration)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.QUOTA_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F270 CORE.QUOTA_REGISTRATION.STATUS

**Metadata**

- E01 dev_evidence.json /columns/269: CORE.QUOTA_REGISTRATION.STATUS; GET_DDL CORE.QUOTA_REGISTRATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/7_Quota_Registrations.py:212 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:208 (generate_quota_registrations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F271 CORE.QUOTA_REGISTRATION.EFFECTIVE_DATE

**Metadata**

- E01 dev_evidence.json /columns/270: CORE.QUOTA_REGISTRATION.EFFECTIVE_DATE; GET_DDL CORE.QUOTA_REGISTRATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_map/EFFECTIVE_DATE
- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_types/EFFECTIVE_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/7_Quota_Registrations.py:130 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:209 (generate_quota_registrations, fabricated only)
- E05 data/validation.py:169-182 (validate_quota_registration)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.EFFECTIVE_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F272 CORE.QUOTA_REGISTRATION.END_DATE

**Metadata**

- E01 dev_evidence.json /columns/271: CORE.QUOTA_REGISTRATION.END_DATE; GET_DDL CORE.QUOTA_REGISTRATION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_map/END_DATE
- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_REGISTRATION/field_types/END_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/7_Quota_Registrations.py:131 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:210 (generate_quota_registrations, fabricated only)
- E05 data/validation.py:169-182 (validate_quota_registration)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.END_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F273 CORE.QUOTA_REGISTRATION.COMMENTS

**Metadata**

- E01 dev_evidence.json /columns/272: CORE.QUOTA_REGISTRATION.COMMENTS; GET_DDL CORE.QUOTA_REGISTRATION

**Code**

- E05 app/pages/7_Quota_Registrations.py:212 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:211 (generate_quota_registrations, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.COMMENTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F274 CORE.QUOTA_REGISTRATION.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/273: CORE.QUOTA_REGISTRATION.CREATED_AT; GET_DDL CORE.QUOTA_REGISTRATION

**Code**

- E05 app/pages/7_Quota_Registrations.py:132 (record payload assignment)
- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F275 CORE.QUOTA_REGISTRATION.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/274: CORE.QUOTA_REGISTRATION.UPDATED_AT; GET_DDL CORE.QUOTA_REGISTRATION

**Code**

- E05 data/repositories/snowflake.py:573-577 (upsert_quota_registration)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.QUOTA_REGISTRATION.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F276 CORE.QUOTA_TRANSACTION.QUOTA_TRANSACTION_ID

**Metadata**

- E01 dev_evidence.json /columns/275: CORE.QUOTA_TRANSACTION.QUOTA_TRANSACTION_ID; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/QUOTA_TRANSACTION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:366 (generate_quota_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.QUOTA_TRANSACTION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F277 CORE.QUOTA_TRANSACTION.TRANSACTION_TYPE

**Metadata**

- E01 dev_evidence.json /columns/276: CORE.QUOTA_TRANSACTION.TRANSACTION_TYPE; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/TRANSACTION_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:367 (generate_quota_transactions, fabricated only)
- E05 data/validation.py:185-202 (validate_quota_transaction)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.TRANSACTION_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F278 CORE.QUOTA_TRANSACTION.QUOTA_ID

**Metadata**

- E01 dev_evidence.json /columns/277: CORE.QUOTA_TRANSACTION.QUOTA_ID; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/QUOTA_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:368 (generate_quota_transactions, fabricated only)
- E05 data/validation.py:185-202 (validate_quota_transaction)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.QUOTA_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F279 CORE.QUOTA_TRANSACTION.EFFECTIVE_DATE

**Metadata**

- E01 dev_evidence.json /columns/278: CORE.QUOTA_TRANSACTION.EFFECTIVE_DATE; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/EFFECTIVE_DATE
- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_types/EFFECTIVE_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:122 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:369 (generate_quota_transactions, fabricated only)
- E05 data/validation.py:185-202 (validate_quota_transaction)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.EFFECTIVE_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F280 CORE.QUOTA_TRANSACTION.END_DATE

**Metadata**

- E01 dev_evidence.json /columns/279: CORE.QUOTA_TRANSACTION.END_DATE; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/END_DATE
- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_types/END_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:370 (generate_quota_transactions, fabricated only)
- E05 data/validation.py:185-202 (validate_quota_transaction)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.END_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F281 CORE.QUOTA_TRANSACTION.QUOTA_COUNT

**Metadata**

- E01 dev_evidence.json /columns/280: CORE.QUOTA_TRANSACTION.QUOTA_COUNT; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/QUOTA_COUNT
- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_types/QUOTA_COUNT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:122 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:371 (generate_quota_transactions, fabricated only)
- E05 data/validation.py:185-202 (validate_quota_transaction)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.QUOTA_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F282 CORE.QUOTA_TRANSACTION.OWNER_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/281: CORE.QUOTA_TRANSACTION.OWNER_ACCOUNT_ID; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/derive_parent_fields/OWNER_ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:372 (generate_quota_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.OWNER_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F283 CORE.QUOTA_TRANSACTION.RELATED_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/282: CORE.QUOTA_TRANSACTION.RELATED_ACCOUNT_ID; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/RELATED_ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:373 (generate_quota_transactions, fabricated only)
- E05 data/validation.py:185-202 (validate_quota_transaction)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.RELATED_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F284 CORE.QUOTA_TRANSACTION.RELATED_QUOTA_ID

**Metadata**

- E01 dev_evidence.json /columns/283: CORE.QUOTA_TRANSACTION.RELATED_QUOTA_ID; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/RELATED_QUOTA_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:374 (generate_quota_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.RELATED_QUOTA_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F285 CORE.QUOTA_TRANSACTION.RELATED_TRANSACTION_ID

**Metadata**

- E01 dev_evidence.json /columns/284: CORE.QUOTA_TRANSACTION.RELATED_TRANSACTION_ID; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/RELATED_TRANSACTION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:375 (generate_quota_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.RELATED_TRANSACTION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F286 CORE.QUOTA_TRANSACTION.PRICE

**Metadata**

- E01 dev_evidence.json /columns/285: CORE.QUOTA_TRANSACTION.PRICE; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/PRICE
- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_types/PRICE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:122 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:376 (generate_quota_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.PRICE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F287 CORE.QUOTA_TRANSACTION.QUOTA_LEASE_TYPE

**Metadata**

- E01 dev_evidence.json /columns/286: CORE.QUOTA_TRANSACTION.QUOTA_LEASE_TYPE; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/QUOTA_LEASE_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:377 (generate_quota_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.QUOTA_LEASE_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F288 CORE.QUOTA_TRANSACTION.COMMENTS

**Metadata**

- E01 dev_evidence.json /columns/287: CORE.QUOTA_TRANSACTION.COMMENTS; GET_DDL CORE.QUOTA_TRANSACTION

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/QUOTA_TRANSACTION/field_map/COMMENTS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/8_Quota_Transactions.py:216 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:378 (generate_quota_transactions, fabricated only)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.COMMENTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F289 CORE.QUOTA_TRANSACTION.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/288: CORE.QUOTA_TRANSACTION.CREATED_AT; GET_DDL CORE.QUOTA_TRANSACTION

**Code**

- E05 app/pages/8_Quota_Transactions.py:122 (record payload assignment)
- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F290 CORE.QUOTA_TRANSACTION.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/289: CORE.QUOTA_TRANSACTION.UPDATED_AT; GET_DDL CORE.QUOTA_TRANSACTION

**Code**

- E05 data/repositories/snowflake.py:589-596 (upsert_quota_transaction)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.QUOTA_TRANSACTION.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F291 CORE.SALMONELLA_TEST.SALMONELLA_TEST_ID

**Metadata**

- E01 dev_evidence.json /columns/290: CORE.SALMONELLA_TEST.SALMONELLA_TEST_ID; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/SALMONELLA_TEST_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:395 (generate_salmonella_tests, fabricated only)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.SALMONELLA_TEST_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F292 CORE.SALMONELLA_TEST.FLOCK_ID

**Metadata**

- E01 dev_evidence.json /columns/291: CORE.SALMONELLA_TEST.FLOCK_ID; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/FLOCK_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:396 (generate_salmonella_tests, fabricated only)
- E05 data/validation.py:205-227 (validate_salmonella_test)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.FLOCK_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/eims_historical_corrections.md: confirmed historical Account mismatch and nullable count/result exception; not normal entry waiver.

## F293 CORE.SALMONELLA_TEST.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/292: CORE.SALMONELLA_TEST.ACCOUNT_ID; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:397 (generate_salmonella_tests, fabricated only)
- E05 data/validation.py:205-227 (validate_salmonella_test)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/eims_historical_corrections.md: confirmed historical Account mismatch and nullable count/result exception; not normal entry waiver.

## F294 CORE.SALMONELLA_TEST.PERMIT_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/293: CORE.SALMONELLA_TEST.PERMIT_NUMBER; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/PERMIT_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:398 (generate_salmonella_tests, fabricated only)
- E05 data/validation.py:205-227 (validate_salmonella_test)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.PERMIT_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F295 CORE.SALMONELLA_TEST.TESTING_DATE

**Metadata**

- E01 dev_evidence.json /columns/294: CORE.SALMONELLA_TEST.TESTING_DATE; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/TESTING_DATE
- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_types/TESTING_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:399 (generate_salmonella_tests, fabricated only)
- E05 data/validation.py:205-227 (validate_salmonella_test)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.TESTING_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F296 CORE.SALMONELLA_TEST.INSPECTOR

**Metadata**

- E01 dev_evidence.json /columns/295: CORE.SALMONELLA_TEST.INSPECTOR; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/INSPECTOR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:400 (generate_salmonella_tests, fabricated only)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.INSPECTOR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F297 CORE.SALMONELLA_TEST.NUMBER_OF_SAMPLES

**Metadata**

- E01 dev_evidence.json /columns/296: CORE.SALMONELLA_TEST.NUMBER_OF_SAMPLES; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/NUMBER_OF_SAMPLES
- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_types/NUMBER_OF_SAMPLES
- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/numeric_rules/NUMBER_OF_SAMPLES

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:401 (generate_salmonella_tests, fabricated only)
- E05 data/validation.py:205-227 (validate_salmonella_test)
- E05 data/migration.py:244-254 (_rule_error)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.NUMBER_OF_SAMPLES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/eims_historical_corrections.md: confirmed historical Account mismatch and nullable count/result exception; not normal entry waiver.

## F298 CORE.SALMONELLA_TEST.TEST_RESULT

**Metadata**

- E01 dev_evidence.json /columns/297: CORE.SALMONELLA_TEST.TEST_RESULT; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/TEST_RESULT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:402 (generate_salmonella_tests, fabricated only)
- E05 data/validation.py:205-227 (validate_salmonella_test)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.TEST_RESULT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/eims_historical_corrections.md: confirmed historical Account mismatch and nullable count/result exception; not normal entry waiver.

## F299 CORE.SALMONELLA_TEST.DATE_RESULT_SENT

**Metadata**

- E01 dev_evidence.json /columns/298: CORE.SALMONELLA_TEST.DATE_RESULT_SENT; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/DATE_RESULT_SENT
- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_types/DATE_RESULT_SENT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:403 (generate_salmonella_tests, fabricated only)
- E05 data/validation.py:205-227 (validate_salmonella_test)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.DATE_RESULT_SENT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F300 CORE.SALMONELLA_TEST.DATE_RECEIVED

**Metadata**

- E01 dev_evidence.json /columns/299: CORE.SALMONELLA_TEST.DATE_RECEIVED; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/DATE_RECEIVED
- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_types/DATE_RECEIVED

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:404 (generate_salmonella_tests, fabricated only)
- E05 data/validation.py:205-227 (validate_salmonella_test)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.DATE_RECEIVED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F301 CORE.SALMONELLA_TEST.CASE_FILE_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/300: CORE.SALMONELLA_TEST.CASE_FILE_NUMBER; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/CASE_FILE_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:405 (generate_salmonella_tests, fabricated only)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.CASE_FILE_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F302 CORE.SALMONELLA_TEST.INVOICE_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/301: CORE.SALMONELLA_TEST.INVOICE_NUMBER; GET_DDL CORE.SALMONELLA_TEST

**Code**

- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:406 (generate_salmonella_tests, fabricated only)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.INVOICE_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F303 CORE.SALMONELLA_TEST.INVOICE_DATE

**Metadata**

- E01 dev_evidence.json /columns/302: CORE.SALMONELLA_TEST.INVOICE_DATE; GET_DDL CORE.SALMONELLA_TEST

**Code**

- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:407 (generate_salmonella_tests, fabricated only)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.INVOICE_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F304 CORE.SALMONELLA_TEST.COMMENTS

**Metadata**

- E01 dev_evidence.json /columns/303: CORE.SALMONELLA_TEST.COMMENTS; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/COMMENTS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/9_Salmonella_Tests.py:163 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:408 (generate_salmonella_tests, fabricated only)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.COMMENTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F305 CORE.SALMONELLA_TEST.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/304: CORE.SALMONELLA_TEST.CREATED_AT; GET_DDL CORE.SALMONELLA_TEST

**Code**

- E05 app/pages/9_Salmonella_Tests.py:90 (record payload assignment)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F306 CORE.SALMONELLA_TEST.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/305: CORE.SALMONELLA_TEST.UPDATED_AT; GET_DDL CORE.SALMONELLA_TEST

**Code**

- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F307 CORE.SALMONELLA_TEST.TEST_TYPE

**Metadata**

- E01 dev_evidence.json /columns/306: CORE.SALMONELLA_TEST.TEST_TYPE; GET_DDL CORE.SALMONELLA_TEST

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST/field_map/TEST_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:642-646 (upsert_salmonella_test)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST.TEST_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F308 CORE.SALMONELLA_TEST_SAMPLE.SALMONELLA_TEST_SAMPLE_ID

**Metadata**

- E01 dev_evidence.json /columns/307: CORE.SALMONELLA_TEST_SAMPLE.SALMONELLA_TEST_SAMPLE_ID; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST_SAMPLE/field_map/SALMONELLA_TEST_SAMPLE_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.SALMONELLA_TEST_SAMPLE_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F309 CORE.SALMONELLA_TEST_SAMPLE.SALMONELLA_TEST_ID

**Metadata**

- E01 dev_evidence.json /columns/308: CORE.SALMONELLA_TEST_SAMPLE.SALMONELLA_TEST_ID; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST_SAMPLE/field_map/SALMONELLA_TEST_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.SALMONELLA_TEST_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F310 CORE.SALMONELLA_TEST_SAMPLE.SAMPLE_REFERENCE

**Metadata**

- E01 dev_evidence.json /columns/309: CORE.SALMONELLA_TEST_SAMPLE.SAMPLE_REFERENCE; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST_SAMPLE/field_map/SAMPLE_REFERENCE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.SAMPLE_REFERENCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F311 CORE.SALMONELLA_TEST_SAMPLE.COMMENTS

**Metadata**

- E01 dev_evidence.json /columns/310: CORE.SALMONELLA_TEST_SAMPLE.COMMENTS; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.COMMENTS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F312 CORE.SALMONELLA_TEST_SAMPLE.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/311: CORE.SALMONELLA_TEST_SAMPLE.CREATED_AT; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F313 CORE.SALMONELLA_TEST_SAMPLE.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/312: CORE.SALMONELLA_TEST_SAMPLE.UPDATED_AT; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Code**

- E05 data/repositories/snowflake.py:1193-1214 (_insert_migration_core)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F314 CORE.SALMONELLA_TEST_SAMPLE.TEST_AREA

**Metadata**

- E01 dev_evidence.json /columns/313: CORE.SALMONELLA_TEST_SAMPLE.TEST_AREA; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST_SAMPLE/field_map/TEST_AREA

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.TEST_AREA, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F315 CORE.SALMONELLA_TEST_SAMPLE.SEROTYPE

**Metadata**

- E01 dev_evidence.json /columns/314: CORE.SALMONELLA_TEST_SAMPLE.SEROTYPE; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST_SAMPLE/field_map/SEROTYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.SEROTYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F316 CORE.SALMONELLA_TEST_SAMPLE.PHAGE

**Metadata**

- E01 dev_evidence.json /columns/315: CORE.SALMONELLA_TEST_SAMPLE.PHAGE; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST_SAMPLE/field_map/PHAGE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.PHAGE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F317 CORE.SALMONELLA_TEST_SAMPLE.STATUS

**Metadata**

- E01 dev_evidence.json /columns/316: CORE.SALMONELLA_TEST_SAMPLE.STATUS; GET_DDL CORE.SALMONELLA_TEST_SAMPLE

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/SALMONELLA_TEST_SAMPLE/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)

**Executed query**

- E01 /field_usage: CORE.SALMONELLA_TEST_SAMPLE.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F318 RAW.IMPORT_BATCH.IMPORT_ID

**Metadata**

- E01 dev_evidence.json /columns/317: RAW.IMPORT_BATCH.IMPORT_ID; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.IMPORT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F319 RAW.IMPORT_BATCH.FILENAME

**Metadata**

- E01 dev_evidence.json /columns/318: RAW.IMPORT_BATCH.FILENAME; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.FILENAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F320 RAW.IMPORT_BATCH.SOURCE

**Metadata**

- E01 dev_evidence.json /columns/319: RAW.IMPORT_BATCH.SOURCE; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.SOURCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F321 RAW.IMPORT_BATCH.FILE_HASH

**Metadata**

- E01 dev_evidence.json /columns/320: RAW.IMPORT_BATCH.FILE_HASH; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.FILE_HASH, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F322 RAW.IMPORT_BATCH.FILE_SIZE_BYTES

**Metadata**

- E01 dev_evidence.json /columns/321: RAW.IMPORT_BATCH.FILE_SIZE_BYTES; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.FILE_SIZE_BYTES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F323 RAW.IMPORT_BATCH.WORKSHEET_NAME

**Metadata**

- E01 dev_evidence.json /columns/322: RAW.IMPORT_BATCH.WORKSHEET_NAME; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.WORKSHEET_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F324 RAW.IMPORT_BATCH.REPORTING_YEAR

**Metadata**

- E01 dev_evidence.json /columns/323: RAW.IMPORT_BATCH.REPORTING_YEAR; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.REPORTING_YEAR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F325 RAW.IMPORT_BATCH.REPORTING_WEEK

**Metadata**

- E01 dev_evidence.json /columns/324: RAW.IMPORT_BATCH.REPORTING_WEEK; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.REPORTING_WEEK, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F326 RAW.IMPORT_BATCH.SOURCE_RECORD_COUNT

**Metadata**

- E01 dev_evidence.json /columns/325: RAW.IMPORT_BATCH.SOURCE_RECORD_COUNT; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.SOURCE_RECORD_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F327 RAW.IMPORT_BATCH.ROW_COUNT

**Metadata**

- E01 dev_evidence.json /columns/326: RAW.IMPORT_BATCH.ROW_COUNT; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.ROW_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F328 RAW.IMPORT_BATCH.ERROR_COUNT

**Metadata**

- E01 dev_evidence.json /columns/327: RAW.IMPORT_BATCH.ERROR_COUNT; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.ERROR_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F329 RAW.IMPORT_BATCH.STATUS

**Metadata**

- E01 dev_evidence.json /columns/328: RAW.IMPORT_BATCH.STATUS; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F330 RAW.IMPORT_BATCH.NOTES

**Metadata**

- E01 dev_evidence.json /columns/329: RAW.IMPORT_BATCH.NOTES; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.NOTES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F331 RAW.IMPORT_BATCH.UPLOAD_TIMESTAMP

**Metadata**

- E01 dev_evidence.json /columns/330: RAW.IMPORT_BATCH.UPLOAD_TIMESTAMP; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.UPLOAD_TIMESTAMP, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F332 RAW.IMPORT_BATCH.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/331: RAW.IMPORT_BATCH.CREATED_AT; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F333 RAW.IMPORT_BATCH.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/332: RAW.IMPORT_BATCH.UPDATED_AT; GET_DDL RAW.IMPORT_BATCH

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: RAW.IMPORT_BATCH.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F334 RAW.IMPORT_RAW_ROW.RAW_ROW_ID

**Metadata**

- E01 dev_evidence.json /columns/333: RAW.IMPORT_RAW_ROW.RAW_ROW_ID; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.RAW_ROW_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F335 RAW.IMPORT_RAW_ROW.IMPORT_ID

**Metadata**

- E01 dev_evidence.json /columns/334: RAW.IMPORT_RAW_ROW.IMPORT_ID; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.IMPORT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F336 RAW.IMPORT_RAW_ROW.SOURCE_ROW_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/335: RAW.IMPORT_RAW_ROW.SOURCE_ROW_NUMBER; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.SOURCE_ROW_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F337 RAW.IMPORT_RAW_ROW.RAW_DATA

**Metadata**

- E01 dev_evidence.json /columns/336: RAW.IMPORT_RAW_ROW.RAW_DATA; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.RAW_DATA, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F338 RAW.IMPORT_RAW_ROW.VALIDATION_STATUS

**Metadata**

- E01 dev_evidence.json /columns/337: RAW.IMPORT_RAW_ROW.VALIDATION_STATUS; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.VALIDATION_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F339 RAW.IMPORT_RAW_ROW.MATCH_STATUS

**Metadata**

- E01 dev_evidence.json /columns/338: RAW.IMPORT_RAW_ROW.MATCH_STATUS; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.MATCH_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F340 RAW.IMPORT_RAW_ROW.VALIDATION_MESSAGES

**Metadata**

- E01 dev_evidence.json /columns/339: RAW.IMPORT_RAW_ROW.VALIDATION_MESSAGES; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.VALIDATION_MESSAGES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F341 RAW.IMPORT_RAW_ROW.MATCHED_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/340: RAW.IMPORT_RAW_ROW.MATCHED_ACCOUNT_ID; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.MATCHED_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F342 RAW.IMPORT_RAW_ROW.MATCHED_FACILITY_ID

**Metadata**

- E01 dev_evidence.json /columns/341: RAW.IMPORT_RAW_ROW.MATCHED_FACILITY_ID; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.MATCHED_FACILITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F343 RAW.IMPORT_RAW_ROW.MATCHED_FLOCK_ID

**Metadata**

- E01 dev_evidence.json /columns/342: RAW.IMPORT_RAW_ROW.MATCHED_FLOCK_ID; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.MATCHED_FLOCK_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F344 RAW.IMPORT_RAW_ROW.MATCH_CONFIRMED_AT

**Metadata**

- E01 dev_evidence.json /columns/343: RAW.IMPORT_RAW_ROW.MATCH_CONFIRMED_AT; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.MATCH_CONFIRMED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F345 RAW.IMPORT_RAW_ROW.MATCH_CONFIRMED_BY

**Metadata**

- E01 dev_evidence.json /columns/344: RAW.IMPORT_RAW_ROW.MATCH_CONFIRMED_BY; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.MATCH_CONFIRMED_BY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F346 RAW.IMPORT_RAW_ROW.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/345: RAW.IMPORT_RAW_ROW.CREATED_AT; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F347 RAW.IMPORT_RAW_ROW.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/346: RAW.IMPORT_RAW_ROW.UPDATED_AT; GET_DDL RAW.IMPORT_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:664-667 (_insert_raw)
- E05 data/importing.py:146-166 (build_raw_rows)

**Executed query**

- E01 /field_usage: RAW.IMPORT_RAW_ROW.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F348 RAW.MIGRATION_BATCH.MIGRATION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/347: RAW.MIGRATION_BATCH.MIGRATION_BATCH_ID; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.MIGRATION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F349 RAW.MIGRATION_BATCH.PACKAGE_HASH

**Metadata**

- E01 dev_evidence.json /columns/348: RAW.MIGRATION_BATCH.PACKAGE_HASH; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.PACKAGE_HASH, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F350 RAW.MIGRATION_BATCH.SCHEMA_VERSION

**Metadata**

- E01 dev_evidence.json /columns/349: RAW.MIGRATION_BATCH.SCHEMA_VERSION; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.SCHEMA_VERSION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F351 RAW.MIGRATION_BATCH.STATUS

**Metadata**

- E01 dev_evidence.json /columns/350: RAW.MIGRATION_BATCH.STATUS; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F352 RAW.MIGRATION_BATCH.SOURCE_FILE_COUNT

**Metadata**

- E01 dev_evidence.json /columns/351: RAW.MIGRATION_BATCH.SOURCE_FILE_COUNT; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.SOURCE_FILE_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F353 RAW.MIGRATION_BATCH.SOURCE_ROW_COUNT

**Metadata**

- E01 dev_evidence.json /columns/352: RAW.MIGRATION_BATCH.SOURCE_ROW_COUNT; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.SOURCE_ROW_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F354 RAW.MIGRATION_BATCH.READY_ROW_COUNT

**Metadata**

- E01 dev_evidence.json /columns/353: RAW.MIGRATION_BATCH.READY_ROW_COUNT; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.READY_ROW_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F355 RAW.MIGRATION_BATCH.REJECTED_ROW_COUNT

**Metadata**

- E01 dev_evidence.json /columns/354: RAW.MIGRATION_BATCH.REJECTED_ROW_COUNT; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.REJECTED_ROW_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F356 RAW.MIGRATION_BATCH.CREATED_BY

**Metadata**

- E01 dev_evidence.json /columns/355: RAW.MIGRATION_BATCH.CREATED_BY; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.CREATED_BY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F357 RAW.MIGRATION_BATCH.COMMITTED_AT

**Metadata**

- E01 dev_evidence.json /columns/356: RAW.MIGRATION_BATCH.COMMITTED_AT; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.COMMITTED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F358 RAW.MIGRATION_BATCH.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/357: RAW.MIGRATION_BATCH.CREATED_AT; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F359 RAW.MIGRATION_BATCH.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/358: RAW.MIGRATION_BATCH.UPDATED_AT; GET_DDL RAW.MIGRATION_BATCH

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_BATCH.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F360 RAW.MIGRATION_CORRECTION_BATCH.MIGRATION_CORRECTION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/359: RAW.MIGRATION_CORRECTION_BATCH.MIGRATION_CORRECTION_BATCH_ID; GET_DDL RAW.MIGRATION_CORRECTION_BATCH

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_BATCH.MIGRATION_CORRECTION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F361 RAW.MIGRATION_CORRECTION_BATCH.ORIGINAL_MIGRATION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/360: RAW.MIGRATION_CORRECTION_BATCH.ORIGINAL_MIGRATION_BATCH_ID; GET_DDL RAW.MIGRATION_CORRECTION_BATCH

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_BATCH.ORIGINAL_MIGRATION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F362 RAW.MIGRATION_CORRECTION_BATCH.STATUS

**Metadata**

- E01 dev_evidence.json /columns/361: RAW.MIGRATION_CORRECTION_BATCH.STATUS; GET_DDL RAW.MIGRATION_CORRECTION_BATCH

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_BATCH.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F363 RAW.MIGRATION_CORRECTION_BATCH.READY_ROW_COUNT

**Metadata**

- E01 dev_evidence.json /columns/362: RAW.MIGRATION_CORRECTION_BATCH.READY_ROW_COUNT; GET_DDL RAW.MIGRATION_CORRECTION_BATCH

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_BATCH.READY_ROW_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F364 RAW.MIGRATION_CORRECTION_BATCH.PENDING_ROW_COUNT

**Metadata**

- E01 dev_evidence.json /columns/363: RAW.MIGRATION_CORRECTION_BATCH.PENDING_ROW_COUNT; GET_DDL RAW.MIGRATION_CORRECTION_BATCH

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_BATCH.PENDING_ROW_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F365 RAW.MIGRATION_CORRECTION_BATCH.COMMITTED_AT

**Metadata**

- E01 dev_evidence.json /columns/364: RAW.MIGRATION_CORRECTION_BATCH.COMMITTED_AT; GET_DDL RAW.MIGRATION_CORRECTION_BATCH

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_BATCH.COMMITTED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F366 RAW.MIGRATION_CORRECTION_BATCH.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/365: RAW.MIGRATION_CORRECTION_BATCH.CREATED_AT; GET_DDL RAW.MIGRATION_CORRECTION_BATCH

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_BATCH.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F367 RAW.MIGRATION_CORRECTION_BATCH.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/366: RAW.MIGRATION_CORRECTION_BATCH.UPDATED_AT; GET_DDL RAW.MIGRATION_CORRECTION_BATCH

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_BATCH.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F368 RAW.MIGRATION_CORRECTION_ROW.MIGRATION_CORRECTION_ROW_ID

**Metadata**

- E01 dev_evidence.json /columns/367: RAW.MIGRATION_CORRECTION_ROW.MIGRATION_CORRECTION_ROW_ID; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.MIGRATION_CORRECTION_ROW_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F369 RAW.MIGRATION_CORRECTION_ROW.MIGRATION_CORRECTION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/368: RAW.MIGRATION_CORRECTION_ROW.MIGRATION_CORRECTION_BATCH_ID; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.MIGRATION_CORRECTION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F370 RAW.MIGRATION_CORRECTION_ROW.ORIGINAL_MIGRATION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/369: RAW.MIGRATION_CORRECTION_ROW.ORIGINAL_MIGRATION_BATCH_ID; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.ORIGINAL_MIGRATION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F371 RAW.MIGRATION_CORRECTION_ROW.MIGRATION_RAW_ROW_ID

**Metadata**

- E01 dev_evidence.json /columns/370: RAW.MIGRATION_CORRECTION_ROW.MIGRATION_RAW_ROW_ID; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.MIGRATION_RAW_ROW_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F372 RAW.MIGRATION_CORRECTION_ROW.SOURCE_FILENAME

**Metadata**

- E01 dev_evidence.json /columns/371: RAW.MIGRATION_CORRECTION_ROW.SOURCE_FILENAME; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.SOURCE_FILENAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F373 RAW.MIGRATION_CORRECTION_ROW.SOURCE_ENTITY

**Metadata**

- E01 dev_evidence.json /columns/372: RAW.MIGRATION_CORRECTION_ROW.SOURCE_ENTITY; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.SOURCE_ENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F374 RAW.MIGRATION_CORRECTION_ROW.SOURCE_ROW_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/373: RAW.MIGRATION_CORRECTION_ROW.SOURCE_ROW_NUMBER; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.SOURCE_ROW_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F375 RAW.MIGRATION_CORRECTION_ROW.SOURCE_ID

**Metadata**

- E01 dev_evidence.json /columns/374: RAW.MIGRATION_CORRECTION_ROW.SOURCE_ID; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.SOURCE_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F376 RAW.MIGRATION_CORRECTION_ROW.TARGET_ID

**Metadata**

- E01 dev_evidence.json /columns/375: RAW.MIGRATION_CORRECTION_ROW.TARGET_ID; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.TARGET_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F377 RAW.MIGRATION_CORRECTION_ROW.DISPOSITION

**Metadata**

- E01 dev_evidence.json /columns/376: RAW.MIGRATION_CORRECTION_ROW.DISPOSITION; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.DISPOSITION, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F378 RAW.MIGRATION_CORRECTION_ROW.RELATION_STATUS

**Metadata**

- E01 dev_evidence.json /columns/377: RAW.MIGRATION_CORRECTION_ROW.RELATION_STATUS; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.RELATION_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F379 RAW.MIGRATION_CORRECTION_ROW.REASON

**Metadata**

- E01 dev_evidence.json /columns/378: RAW.MIGRATION_CORRECTION_ROW.REASON; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.REASON, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F380 RAW.MIGRATION_CORRECTION_ROW.CORRECTED_DATA

**Metadata**

- E01 dev_evidence.json /columns/379: RAW.MIGRATION_CORRECTION_ROW.CORRECTED_DATA; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.CORRECTED_DATA, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F381 RAW.MIGRATION_CORRECTION_ROW.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/380: RAW.MIGRATION_CORRECTION_ROW.CREATED_AT; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F382 RAW.MIGRATION_CORRECTION_ROW.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/381: RAW.MIGRATION_CORRECTION_ROW.UPDATED_AT; GET_DDL RAW.MIGRATION_CORRECTION_ROW

**Code**

- E05 data/repositories/snowflake.py:1348-1435 (commit_historical_corrections)
- E05 data/historical_corrections.py:137-367 (build_historical_correction_preview)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_CORRECTION_ROW.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /correction_preview and /correction_targets: saved 112 committed /159 pending classifications and target existence.

## F383 RAW.MIGRATION_ERROR.MIGRATION_ERROR_ID

**Metadata**

- E01 dev_evidence.json /columns/382: RAW.MIGRATION_ERROR.MIGRATION_ERROR_ID; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.MIGRATION_ERROR_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F384 RAW.MIGRATION_ERROR.MIGRATION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/383: RAW.MIGRATION_ERROR.MIGRATION_BATCH_ID; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.MIGRATION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F385 RAW.MIGRATION_ERROR.SOURCE_FILENAME

**Metadata**

- E01 dev_evidence.json /columns/384: RAW.MIGRATION_ERROR.SOURCE_FILENAME; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.SOURCE_FILENAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F386 RAW.MIGRATION_ERROR.SOURCE_ENTITY

**Metadata**

- E01 dev_evidence.json /columns/385: RAW.MIGRATION_ERROR.SOURCE_ENTITY; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.SOURCE_ENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F387 RAW.MIGRATION_ERROR.SOURCE_ROW_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/386: RAW.MIGRATION_ERROR.SOURCE_ROW_NUMBER; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.SOURCE_ROW_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F388 RAW.MIGRATION_ERROR.FIELD_NAME

**Metadata**

- E01 dev_evidence.json /columns/387: RAW.MIGRATION_ERROR.FIELD_NAME; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.FIELD_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F389 RAW.MIGRATION_ERROR.ERROR_CATEGORY

**Metadata**

- E01 dev_evidence.json /columns/388: RAW.MIGRATION_ERROR.ERROR_CATEGORY; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.ERROR_CATEGORY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F390 RAW.MIGRATION_ERROR.ERROR_MESSAGE

**Metadata**

- E01 dev_evidence.json /columns/389: RAW.MIGRATION_ERROR.ERROR_MESSAGE; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.ERROR_MESSAGE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F391 RAW.MIGRATION_ERROR.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/390: RAW.MIGRATION_ERROR.CREATED_AT; GET_DDL RAW.MIGRATION_ERROR

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:1216-1285 (commit_migration_batch)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ERROR.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F392 RAW.MIGRATION_FILE.MIGRATION_FILE_ID

**Metadata**

- E01 dev_evidence.json /columns/391: RAW.MIGRATION_FILE.MIGRATION_FILE_ID; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.MIGRATION_FILE_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F393 RAW.MIGRATION_FILE.MIGRATION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/392: RAW.MIGRATION_FILE.MIGRATION_BATCH_ID; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.MIGRATION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F394 RAW.MIGRATION_FILE.SOURCE_FILENAME

**Metadata**

- E01 dev_evidence.json /columns/393: RAW.MIGRATION_FILE.SOURCE_FILENAME; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.SOURCE_FILENAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F395 RAW.MIGRATION_FILE.SOURCE_ENTITY

**Metadata**

- E01 dev_evidence.json /columns/394: RAW.MIGRATION_FILE.SOURCE_ENTITY; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.SOURCE_ENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F396 RAW.MIGRATION_FILE.FILE_HASH

**Metadata**

- E01 dev_evidence.json /columns/395: RAW.MIGRATION_FILE.FILE_HASH; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.FILE_HASH, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F397 RAW.MIGRATION_FILE.FILE_SIZE_BYTES

**Metadata**

- E01 dev_evidence.json /columns/396: RAW.MIGRATION_FILE.FILE_SIZE_BYTES; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.FILE_SIZE_BYTES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F398 RAW.MIGRATION_FILE.SOURCE_ROW_COUNT

**Metadata**

- E01 dev_evidence.json /columns/397: RAW.MIGRATION_FILE.SOURCE_ROW_COUNT; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.SOURCE_ROW_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F399 RAW.MIGRATION_FILE.STAGE_PATH

**Metadata**

- E01 dev_evidence.json /columns/398: RAW.MIGRATION_FILE.STAGE_PATH; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)
- E05 data/repositories/snowflake.py:700-704 (stage_migration_file)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.STAGE_PATH, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F400 RAW.MIGRATION_FILE.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/399: RAW.MIGRATION_FILE.CREATED_AT; GET_DDL RAW.MIGRATION_FILE

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_FILE.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F401 RAW.MIGRATION_ID_MAP.MIGRATION_ID_MAP_ID

**Metadata**

- E01 dev_evidence.json /columns/400: RAW.MIGRATION_ID_MAP.MIGRATION_ID_MAP_ID; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.MIGRATION_ID_MAP_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F402 RAW.MIGRATION_ID_MAP.MIGRATION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/401: RAW.MIGRATION_ID_MAP.MIGRATION_BATCH_ID; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.MIGRATION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F403 RAW.MIGRATION_ID_MAP.SOURCE_ENTITY

**Metadata**

- E01 dev_evidence.json /columns/402: RAW.MIGRATION_ID_MAP.SOURCE_ENTITY; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.SOURCE_ENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F404 RAW.MIGRATION_ID_MAP.SOURCE_ID

**Metadata**

- E01 dev_evidence.json /columns/403: RAW.MIGRATION_ID_MAP.SOURCE_ID; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.SOURCE_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F405 RAW.MIGRATION_ID_MAP.TARGET_ID

**Metadata**

- E01 dev_evidence.json /columns/404: RAW.MIGRATION_ID_MAP.TARGET_ID; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.TARGET_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F406 RAW.MIGRATION_ID_MAP.STATUS

**Metadata**

- E01 dev_evidence.json /columns/405: RAW.MIGRATION_ID_MAP.STATUS; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F407 RAW.MIGRATION_ID_MAP.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/406: RAW.MIGRATION_ID_MAP.CREATED_AT; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F408 RAW.MIGRATION_ID_MAP.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/407: RAW.MIGRATION_ID_MAP.UPDATED_AT; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F409 RAW.MIGRATION_ID_MAP.MIGRATION_RAW_ROW_ID

**Metadata**

- E01 dev_evidence.json /columns/408: RAW.MIGRATION_ID_MAP.MIGRATION_RAW_ROW_ID; GET_DDL RAW.MIGRATION_ID_MAP

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_ID_MAP.MIGRATION_RAW_ROW_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F410 RAW.MIGRATION_RAW_ROW.MIGRATION_RAW_ROW_ID

**Metadata**

- E01 dev_evidence.json /columns/409: RAW.MIGRATION_RAW_ROW.MIGRATION_RAW_ROW_ID; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.MIGRATION_RAW_ROW_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F411 RAW.MIGRATION_RAW_ROW.MIGRATION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/410: RAW.MIGRATION_RAW_ROW.MIGRATION_BATCH_ID; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.MIGRATION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F412 RAW.MIGRATION_RAW_ROW.SOURCE_FILENAME

**Metadata**

- E01 dev_evidence.json /columns/411: RAW.MIGRATION_RAW_ROW.SOURCE_FILENAME; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.SOURCE_FILENAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F413 RAW.MIGRATION_RAW_ROW.SOURCE_ENTITY

**Metadata**

- E01 dev_evidence.json /columns/412: RAW.MIGRATION_RAW_ROW.SOURCE_ENTITY; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.SOURCE_ENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F414 RAW.MIGRATION_RAW_ROW.SOURCE_ROW_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/413: RAW.MIGRATION_RAW_ROW.SOURCE_ROW_NUMBER; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.SOURCE_ROW_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F415 RAW.MIGRATION_RAW_ROW.SOURCE_ID

**Metadata**

- E01 dev_evidence.json /columns/414: RAW.MIGRATION_RAW_ROW.SOURCE_ID; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.SOURCE_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F416 RAW.MIGRATION_RAW_ROW.TARGET_ID

**Metadata**

- E01 dev_evidence.json /columns/415: RAW.MIGRATION_RAW_ROW.TARGET_ID; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.TARGET_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F417 RAW.MIGRATION_RAW_ROW.RAW_DATA

**Metadata**

- E01 dev_evidence.json /columns/416: RAW.MIGRATION_RAW_ROW.RAW_DATA; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.RAW_DATA, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F418 RAW.MIGRATION_RAW_ROW.NORMALIZED_DATA

**Metadata**

- E01 dev_evidence.json /columns/417: RAW.MIGRATION_RAW_ROW.NORMALIZED_DATA; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.NORMALIZED_DATA, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F419 RAW.MIGRATION_RAW_ROW.VALIDATION_STATUS

**Metadata**

- E01 dev_evidence.json /columns/418: RAW.MIGRATION_RAW_ROW.VALIDATION_STATUS; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.VALIDATION_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F420 RAW.MIGRATION_RAW_ROW.MATCH_STATUS

**Metadata**

- E01 dev_evidence.json /columns/419: RAW.MIGRATION_RAW_ROW.MATCH_STATUS; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.MATCH_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F421 RAW.MIGRATION_RAW_ROW.VALIDATION_MESSAGES

**Metadata**

- E01 dev_evidence.json /columns/420: RAW.MIGRATION_RAW_ROW.VALIDATION_MESSAGES; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.VALIDATION_MESSAGES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F422 RAW.MIGRATION_RAW_ROW.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/421: RAW.MIGRATION_RAW_ROW.CREATED_AT; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F423 RAW.MIGRATION_RAW_ROW.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/422: RAW.MIGRATION_RAW_ROW.UPDATED_AT; GET_DDL RAW.MIGRATION_RAW_ROW

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RAW_ROW.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F424 RAW.MIGRATION_RECONCILIATION.MIGRATION_RECONCILIATION_ID

**Metadata**

- E01 dev_evidence.json /columns/423: RAW.MIGRATION_RECONCILIATION.MIGRATION_RECONCILIATION_ID; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.MIGRATION_RECONCILIATION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F425 RAW.MIGRATION_RECONCILIATION.MIGRATION_BATCH_ID

**Metadata**

- E01 dev_evidence.json /columns/424: RAW.MIGRATION_RECONCILIATION.MIGRATION_BATCH_ID; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.MIGRATION_BATCH_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F426 RAW.MIGRATION_RECONCILIATION.SOURCE_ENTITY

**Metadata**

- E01 dev_evidence.json /columns/425: RAW.MIGRATION_RECONCILIATION.SOURCE_ENTITY; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.SOURCE_ENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F427 RAW.MIGRATION_RECONCILIATION.SOURCE_ROWS

**Metadata**

- E01 dev_evidence.json /columns/426: RAW.MIGRATION_RECONCILIATION.SOURCE_ROWS; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.SOURCE_ROWS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F428 RAW.MIGRATION_RECONCILIATION.READY_ROWS

**Metadata**

- E01 dev_evidence.json /columns/427: RAW.MIGRATION_RECONCILIATION.READY_ROWS; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.READY_ROWS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F429 RAW.MIGRATION_RECONCILIATION.REJECTED_ROWS

**Metadata**

- E01 dev_evidence.json /columns/428: RAW.MIGRATION_RECONCILIATION.REJECTED_ROWS; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.REJECTED_ROWS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F430 RAW.MIGRATION_RECONCILIATION.INSERTED_ROWS

**Metadata**

- E01 dev_evidence.json /columns/429: RAW.MIGRATION_RECONCILIATION.INSERTED_ROWS; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.INSERTED_ROWS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F431 RAW.MIGRATION_RECONCILIATION.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/430: RAW.MIGRATION_RECONCILIATION.CREATED_AT; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F432 RAW.MIGRATION_RECONCILIATION.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/431: RAW.MIGRATION_RECONCILIATION.UPDATED_AT; GET_DDL RAW.MIGRATION_RECONCILIATION

**Code**

- E05 data/repositories/snowflake.py:706-790 (prepare_migration_batch)
- E05 data/migration.py:283-527 (analyze_migration_files)

**Executed query**

- E01 /field_usage: RAW.MIGRATION_RECONCILIATION.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F433 REPORTING.VW_ACCOUNT_FACILITY.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/432: REPORTING.VW_ACCOUNT_FACILITY.ACCOUNT_ID; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:334 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:89 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F434 REPORTING.VW_ACCOUNT_FACILITY.REGISTRATION_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/433: REPORTING.VW_ACCOUNT_FACILITY.REGISTRATION_NUMBER; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/REGISTRATION_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:340 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:90 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.REGISTRATION_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F435 REPORTING.VW_ACCOUNT_FACILITY.ORGANIZATION_NAME

**Metadata**

- E01 dev_evidence.json /columns/434: REPORTING.VW_ACCOUNT_FACILITY.ORGANIZATION_NAME; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ORGANIZATION_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:335 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:91 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.ORGANIZATION_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F436 REPORTING.VW_ACCOUNT_FACILITY.CITY

**Metadata**

- E01 dev_evidence.json /columns/435: REPORTING.VW_ACCOUNT_FACILITY.CITY; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/CITY

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:353 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:95 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.CITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F437 REPORTING.VW_ACCOUNT_FACILITY.PROVINCE

**Metadata**

- E01 dev_evidence.json /columns/436: REPORTING.VW_ACCOUNT_FACILITY.PROVINCE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PROVINCE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:354 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:96 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.PROVINCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F438 REPORTING.VW_ACCOUNT_FACILITY.CONTACT_NAME

**Metadata**

- E01 dev_evidence.json /columns/437: REPORTING.VW_ACCOUNT_FACILITY.CONTACT_NAME; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/CONTACT_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:101 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.CONTACT_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F439 REPORTING.VW_ACCOUNT_FACILITY.CONTACT_PHONE

**Metadata**

- E01 dev_evidence.json /columns/438: REPORTING.VW_ACCOUNT_FACILITY.CONTACT_PHONE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/CONTACT_PHONE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:337 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:102 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.CONTACT_PHONE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F440 REPORTING.VW_ACCOUNT_FACILITY.CONTACT_EMAIL

**Metadata**

- E01 dev_evidence.json /columns/439: REPORTING.VW_ACCOUNT_FACILITY.CONTACT_EMAIL; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/CONTACT_EMAIL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:336 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:103 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.CONTACT_EMAIL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F441 REPORTING.VW_ACCOUNT_FACILITY.LICENCE_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/440: REPORTING.VW_ACCOUNT_FACILITY.LICENCE_NUMBER; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/LICENCE_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:106 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.LICENCE_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F442 REPORTING.VW_ACCOUNT_FACILITY.PRODUCER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/441: REPORTING.VW_ACCOUNT_FACILITY.PRODUCER_ROLE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/PRODUCER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/PRODUCER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:115 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.PRODUCER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F443 REPORTING.VW_ACCOUNT_FACILITY.BREEDER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/442: REPORTING.VW_ACCOUNT_FACILITY.BREEDER_ROLE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/BREEDER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/BREEDER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:116 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.BREEDER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F444 REPORTING.VW_ACCOUNT_FACILITY.HATCHERY_ROLE

**Metadata**

- E01 dev_evidence.json /columns/443: REPORTING.VW_ACCOUNT_FACILITY.HATCHERY_ROLE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/HATCHERY_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/HATCHERY_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:117 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.HATCHERY_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F445 REPORTING.VW_ACCOUNT_FACILITY.GRADER_ROLE

**Metadata**

- E01 dev_evidence.json /columns/444: REPORTING.VW_ACCOUNT_FACILITY.GRADER_ROLE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/GRADER_ROLE
- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_types/GRADER_ROLE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/synthetic.py:119 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.GRADER_ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F446 REPORTING.VW_ACCOUNT_FACILITY.ACCOUNT_STATUS

**Metadata**

- E01 dev_evidence.json /columns/445: REPORTING.VW_ACCOUNT_FACILITY.ACCOUNT_STATUS; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:348 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:129 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.ACCOUNT_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F447 REPORTING.VW_ACCOUNT_FACILITY.FACILITY_ID

**Metadata**

- E01 dev_evidence.json /columns/446: REPORTING.VW_ACCOUNT_FACILITY.FACILITY_ID; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:155 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.FACILITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F448 REPORTING.VW_ACCOUNT_FACILITY.FACILITY_NAME

**Metadata**

- E01 dev_evidence.json /columns/447: REPORTING.VW_ACCOUNT_FACILITY.FACILITY_NAME; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:157 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.FACILITY_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F449 REPORTING.VW_ACCOUNT_FACILITY.FACILITY_TYPE

**Metadata**

- E01 dev_evidence.json /columns/448: REPORTING.VW_ACCOUNT_FACILITY.FACILITY_TYPE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:158 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.FACILITY_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F450 REPORTING.VW_ACCOUNT_FACILITY.FACILITY_STATUS

**Metadata**

- E01 dev_evidence.json /columns/449: REPORTING.VW_ACCOUNT_FACILITY.FACILITY_STATUS; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:159 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.FACILITY_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F451 REPORTING.VW_ACCOUNT_FACILITY.ACTIVATION_DATE

**Metadata**

- E01 dev_evidence.json /columns/450: REPORTING.VW_ACCOUNT_FACILITY.ACTIVATION_DATE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Code**

- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:160 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.ACTIVATION_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F452 REPORTING.VW_ACCOUNT_FACILITY.CLOSURE_DATE

**Metadata**

- E01 dev_evidence.json /columns/451: REPORTING.VW_ACCOUNT_FACILITY.CLOSURE_DATE; GET_DDL REPORTING.VW_ACCOUNT_FACILITY
- E01 /ddl/REPORTING.VW_ACCOUNT_FACILITY output expression

**Code**

- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:162 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_ACCOUNT_FACILITY.CLOSURE_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F453 REPORTING.VW_FLOCK_DETAIL.FLOCK_ID

**Metadata**

- E01 dev_evidence.json /columns/452: REPORTING.VW_FLOCK_DETAIL.FLOCK_ID; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/FLOCK_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:255 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FLOCK_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F454 REPORTING.VW_FLOCK_DETAIL.FLOCK_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/453: REPORTING.VW_FLOCK_DETAIL.FLOCK_NUMBER; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/fallbacks/FLOCK_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:80 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:261 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FLOCK_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F455 REPORTING.VW_FLOCK_DETAIL.PERMIT_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/454: REPORTING.VW_FLOCK_DETAIL.PERMIT_NUMBER; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/PERMIT_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:262 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.PERMIT_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F456 REPORTING.VW_FLOCK_DETAIL.PERMIT_DATE

**Metadata**

- E01 dev_evidence.json /columns/455: REPORTING.VW_FLOCK_DETAIL.PERMIT_DATE; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/PERMIT_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/PERMIT_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:263 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.PERMIT_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F457 REPORTING.VW_FLOCK_DETAIL.BIRD_COUNT

**Metadata**

- E01 dev_evidence.json /columns/456: REPORTING.VW_FLOCK_DETAIL.BIRD_COUNT; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/BIRD_COUNT
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/BIRD_COUNT

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:266 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.BIRD_COUNT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F458 REPORTING.VW_FLOCK_DETAIL.PLACEMENT_DATE

**Metadata**

- E01 dev_evidence.json /columns/457: REPORTING.VW_FLOCK_DETAIL.PLACEMENT_DATE; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/PLACEMENT_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/PLACEMENT_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:267 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.PLACEMENT_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F459 REPORTING.VW_FLOCK_DETAIL.HATCH_DATE

**Metadata**

- E01 dev_evidence.json /columns/458: REPORTING.VW_FLOCK_DETAIL.HATCH_DATE; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/HATCH_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/HATCH_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:268 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.HATCH_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F460 REPORTING.VW_FLOCK_DETAIL.EGG_COLOUR

**Metadata**

- E01 dev_evidence.json /columns/459: REPORTING.VW_FLOCK_DETAIL.EGG_COLOUR; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/EGG_COLOUR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:269 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.EGG_COLOUR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F461 REPORTING.VW_FLOCK_DETAIL.EST_DISPOSAL

**Metadata**

- E01 dev_evidence.json /columns/460: REPORTING.VW_FLOCK_DETAIL.EST_DISPOSAL; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/EST_DISPOSAL
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/EST_DISPOSAL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:271 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.EST_DISPOSAL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F462 REPORTING.VW_FLOCK_DETAIL.DISPOSAL_DATE

**Metadata**

- E01 dev_evidence.json /columns/461: REPORTING.VW_FLOCK_DETAIL.DISPOSAL_DATE; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/DISPOSAL_DATE
- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_types/DISPOSAL_DATE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:277 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.DISPOSAL_DATE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F463 REPORTING.VW_FLOCK_DETAIL.DISPOSAL_METHOD

**Metadata**

- E01 dev_evidence.json /columns/462: REPORTING.VW_FLOCK_DETAIL.DISPOSAL_METHOD; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Code**

- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:290 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.DISPOSAL_METHOD, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F464 REPORTING.VW_FLOCK_DETAIL.FLOCK_STATUS

**Metadata**

- E01 dev_evidence.json /columns/463: REPORTING.VW_FLOCK_DETAIL.FLOCK_STATUS; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:291 (generate_flocks, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FLOCK_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F465 REPORTING.VW_FLOCK_DETAIL.ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/464: REPORTING.VW_FLOCK_DETAIL.ACCOUNT_ID; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:256 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/FACILITY_FLOCK_DESIGN.md: Sara 8 October permits sequential/concurrent Flocks; cross-Account use not approved.

## F466 REPORTING.VW_FLOCK_DETAIL.REGISTRATION_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/465: REPORTING.VW_FLOCK_DETAIL.REGISTRATION_NUMBER; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/REGISTRATION_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:340 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:90 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.REGISTRATION_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F467 REPORTING.VW_FLOCK_DETAIL.ORGANIZATION_NAME

**Metadata**

- E01 dev_evidence.json /columns/466: REPORTING.VW_FLOCK_DETAIL.ORGANIZATION_NAME; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ORGANIZATION_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:335 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:91 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.ORGANIZATION_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F468 REPORTING.VW_FLOCK_DETAIL.FACILITY_ID

**Metadata**

- E01 dev_evidence.json /columns/467: REPORTING.VW_FLOCK_DETAIL.FACILITY_ID; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/FACILITY_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:257 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FACILITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/FACILITY_FLOCK_DESIGN.md: Sara 8 October permits sequential/concurrent Flocks; cross-Account use not approved.

## F469 REPORTING.VW_FLOCK_DETAIL.FACILITY_NAME

**Metadata**

- E01 dev_evidence.json /columns/468: REPORTING.VW_FLOCK_DETAIL.FACILITY_NAME; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:157 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FACILITY_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F470 REPORTING.VW_FLOCK_DETAIL.FACILITY_TYPE

**Metadata**

- E01 dev_evidence.json /columns/469: REPORTING.VW_FLOCK_DETAIL.FACILITY_TYPE; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/FACILITY_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:158 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FACILITY_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F471 REPORTING.VW_FLOCK_DETAIL.FLOCK_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/470: REPORTING.VW_FLOCK_DETAIL.FLOCK_ACCOUNT_ID; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FLOCK/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/5_Flocks.py:170 (record payload assignment)
- E05 data/repositories/snowflake.py:543-547 (upsert_flock)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:256 (generate_flocks, fabricated only)
- E05 data/validation.py:118-166 (validate_flock)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FLOCK_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

**Business**

- E09 docs/FACILITY_FLOCK_DESIGN.md: Sara 8 October permits sequential/concurrent Flocks; cross-Account use not approved.

## F472 REPORTING.VW_FLOCK_DETAIL.FLOCK_ACCOUNT_NAME

**Metadata**

- E01 dev_evidence.json /columns/471: REPORTING.VW_FLOCK_DETAIL.FLOCK_ACCOUNT_NAME; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ORGANIZATION_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:335 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:91 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FLOCK_ACCOUNT_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F473 REPORTING.VW_FLOCK_DETAIL.FACILITY_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/472: REPORTING.VW_FLOCK_DETAIL.FACILITY_ACCOUNT_ID; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/FACILITY/field_map/ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/11_Facilities.py:136 (record payload assignment)
- E05 data/repositories/snowflake.py:528-528 (upsert_facility)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:156 (generate_facilities, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FACILITY_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F474 REPORTING.VW_FLOCK_DETAIL.FACILITY_ACCOUNT_NAME

**Metadata**

- E01 dev_evidence.json /columns/473: REPORTING.VW_FLOCK_DETAIL.FACILITY_ACCOUNT_NAME; GET_DDL REPORTING.VW_FLOCK_DETAIL
- E01 /ddl/REPORTING.VW_FLOCK_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/ACCOUNT/field_map/ORGANIZATION_NAME

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 app/pages/3_Accounts_Facilities_Flocks.py:335 (record payload assignment)
- E05 data/repositories/snowflake.py:475-491 (upsert_account)
- E05 data/repositories/snowflake.py:300-417 (_upsert_with_executor)
- E05 data/synthetic.py:91 (generate_accounts, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_FLOCK_DETAIL.FACILITY_ACCOUNT_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F475 REPORTING.VW_PRODUCTION_SIZE_DETAIL.PRODUCTION_ID

**Metadata**

- E01 dev_evidence.json /columns/474: REPORTING.VW_PRODUCTION_SIZE_DETAIL.PRODUCTION_ID; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/PRODUCTION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:468 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.PRODUCTION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F476 REPORTING.VW_PRODUCTION_SIZE_DETAIL.GRADER_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/475: REPORTING.VW_PRODUCTION_SIZE_DETAIL.GRADER_NUMBER; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Code**

- E05 data/synthetic.py:475 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/GRADER_NUMBER
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.GRADER_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F477 REPORTING.VW_PRODUCTION_SIZE_DETAIL.BARN_IDENTITY

**Metadata**

- E01 dev_evidence.json /columns/476: REPORTING.VW_PRODUCTION_SIZE_DETAIL.BARN_IDENTITY; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Code**

- E05 data/synthetic.py:476 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.BARN_IDENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F478 REPORTING.VW_PRODUCTION_SIZE_DETAIL.EGG_COLOUR

**Metadata**

- E01 dev_evidence.json /columns/477: REPORTING.VW_PRODUCTION_SIZE_DETAIL.EGG_COLOUR; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/EGG_COLOUR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:478 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/EGG_COLOUR
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.EGG_COLOUR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F479 REPORTING.VW_PRODUCTION_SIZE_DETAIL.SIZE_BREAKDOWN_ID

**Metadata**

- E01 dev_evidence.json /columns/478: REPORTING.VW_PRODUCTION_SIZE_DETAIL.SIZE_BREAKDOWN_ID; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Code**

- E05 data/synthetic.py:515 (generate_size_breakdown, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.SIZE_BREAKDOWN_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F480 REPORTING.VW_PRODUCTION_SIZE_DETAIL.SIZE_BAND

**Metadata**

- E01 dev_evidence.json /columns/479: REPORTING.VW_PRODUCTION_SIZE_DETAIL.SIZE_BAND; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Code**

- E05 data/synthetic.py:517 (generate_size_breakdown, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.SIZE_BAND, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F481 REPORTING.VW_PRODUCTION_SIZE_DETAIL.QUANTITY

**Metadata**

- E01 dev_evidence.json /columns/480: REPORTING.VW_PRODUCTION_SIZE_DETAIL.QUANTITY; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Code**

- E05 data/synthetic.py:518 (generate_size_breakdown, fabricated only)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.QUANTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F482 REPORTING.VW_PRODUCTION_SIZE_DETAIL.REPORTING_YEAR

**Metadata**

- E01 dev_evidence.json /columns/481: REPORTING.VW_PRODUCTION_SIZE_DETAIL.REPORTING_YEAR; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/REPORTING_YEAR
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/REPORTING_YEAR
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/numeric_rules/REPORTING_YEAR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/migration.py:193-203 (parse_reporting_period)
- E05 data/synthetic.py:487 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/migration.py:244-254 (_rule_error)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.REPORTING_YEAR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F483 REPORTING.VW_PRODUCTION_SIZE_DETAIL.REPORTING_WEEK

**Metadata**

- E01 dev_evidence.json /columns/482: REPORTING.VW_PRODUCTION_SIZE_DETAIL.REPORTING_WEEK; GET_DDL REPORTING.VW_PRODUCTION_SIZE_DETAIL
- E01 /ddl/REPORTING.VW_PRODUCTION_SIZE_DETAIL output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/REPORTING_WEEK
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/REPORTING_WEEK
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/numeric_rules/REPORTING_WEEK

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/migration.py:193-203 (parse_reporting_period)
- E05 data/synthetic.py:488 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/migration.py:244-254 (_rule_error)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SIZE_DETAIL.REPORTING_WEEK, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F484 REPORTING.VW_PRODUCTION_SUMMARY.PRODUCTION_ID

**Metadata**

- E01 dev_evidence.json /columns/483: REPORTING.VW_PRODUCTION_SUMMARY.PRODUCTION_ID; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/PRODUCTION_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:468 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.PRODUCTION_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F485 REPORTING.VW_PRODUCTION_SUMMARY.FILENAME

**Metadata**

- E01 dev_evidence.json /columns/484: REPORTING.VW_PRODUCTION_SUMMARY.FILENAME; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.FILENAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F486 REPORTING.VW_PRODUCTION_SUMMARY.SOURCE

**Metadata**

- E01 dev_evidence.json /columns/485: REPORTING.VW_PRODUCTION_SUMMARY.SOURCE; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.SOURCE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F487 REPORTING.VW_PRODUCTION_SUMMARY.REPORTING_YEAR

**Metadata**

- E01 dev_evidence.json /columns/486: REPORTING.VW_PRODUCTION_SUMMARY.REPORTING_YEAR; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/REPORTING_YEAR
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/REPORTING_YEAR
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/numeric_rules/REPORTING_YEAR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/migration.py:193-203 (parse_reporting_period)
- E05 data/synthetic.py:487 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/migration.py:244-254 (_rule_error)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.REPORTING_YEAR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F488 REPORTING.VW_PRODUCTION_SUMMARY.REPORTING_WEEK

**Metadata**

- E01 dev_evidence.json /columns/487: REPORTING.VW_PRODUCTION_SUMMARY.REPORTING_WEEK; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/REPORTING_WEEK
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/REPORTING_WEEK
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/numeric_rules/REPORTING_WEEK

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/migration.py:193-203 (parse_reporting_period)
- E05 data/synthetic.py:488 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/migration.py:244-254 (_rule_error)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.REPORTING_WEEK, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F489 REPORTING.VW_PRODUCTION_SUMMARY.UPLOAD_TIMESTAMP

**Metadata**

- E01 dev_evidence.json /columns/488: REPORTING.VW_PRODUCTION_SUMMARY.UPLOAD_TIMESTAMP; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/repositories/snowflake.py:650-655 (_insert_batch)
- E05 data/repositories/snowflake.py:1614-1729 (import_operational_flock_quota_batch)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.UPLOAD_TIMESTAMP, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F490 REPORTING.VW_PRODUCTION_SUMMARY.GRADER_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/489: REPORTING.VW_PRODUCTION_SUMMARY.GRADER_NUMBER; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:475 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/GRADER_NUMBER
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.GRADER_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F491 REPORTING.VW_PRODUCTION_SUMMARY.PRODUCER_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/490: REPORTING.VW_PRODUCTION_SUMMARY.PRODUCER_NUMBER; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:470 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/PRODUCER_NUMBER
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.PRODUCER_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F492 REPORTING.VW_PRODUCTION_SUMMARY.PRODUCER_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/491: REPORTING.VW_PRODUCTION_SUMMARY.PRODUCER_ACCOUNT_ID; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/PRODUCER_ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:471 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.PRODUCER_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F493 REPORTING.VW_PRODUCTION_SUMMARY.GRADER_ACCOUNT_ID

**Metadata**

- E01 dev_evidence.json /columns/492: REPORTING.VW_PRODUCTION_SUMMARY.GRADER_ACCOUNT_ID; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/GRADER_ACCOUNT_ID

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:472 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.GRADER_ACCOUNT_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F494 REPORTING.VW_PRODUCTION_SUMMARY.FACILITY_ID

**Metadata**

- E01 dev_evidence.json /columns/493: REPORTING.VW_PRODUCTION_SUMMARY.FACILITY_ID; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:473 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.FACILITY_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F495 REPORTING.VW_PRODUCTION_SUMMARY.FLOCK_ID

**Metadata**

- E01 dev_evidence.json /columns/494: REPORTING.VW_PRODUCTION_SUMMARY.FLOCK_ID; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:474 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.FLOCK_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F496 REPORTING.VW_PRODUCTION_SUMMARY.BARN_IDENTITY

**Metadata**

- E01 dev_evidence.json /columns/495: REPORTING.VW_PRODUCTION_SUMMARY.BARN_IDENTITY; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:476 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.BARN_IDENTITY, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F497 REPORTING.VW_PRODUCTION_SUMMARY.FLOCK_AGE

**Metadata**

- E01 dev_evidence.json /columns/496: REPORTING.VW_PRODUCTION_SUMMARY.FLOCK_AGE; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:477 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.FLOCK_AGE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F498 REPORTING.VW_PRODUCTION_SUMMARY.EGG_COLOUR

**Metadata**

- E01 dev_evidence.json /columns/497: REPORTING.VW_PRODUCTION_SUMMARY.EGG_COLOUR; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/EGG_COLOUR

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:478 (generate_production, fabricated only)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/EGG_COLOUR
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.EGG_COLOUR, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F499 REPORTING.VW_PRODUCTION_SUMMARY.NET_WEIGHT

**Metadata**

- E01 dev_evidence.json /columns/498: REPORTING.VW_PRODUCTION_SUMMARY.NET_WEIGHT; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:479 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.NET_WEIGHT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F500 REPORTING.VW_PRODUCTION_SUMMARY.NET_BOXES

**Metadata**

- E01 dev_evidence.json /columns/499: REPORTING.VW_PRODUCTION_SUMMARY.NET_BOXES; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:480 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.NET_BOXES, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F501 REPORTING.VW_PRODUCTION_SUMMARY.NET_PER_BOX

**Metadata**

- E01 dev_evidence.json /columns/500: REPORTING.VW_PRODUCTION_SUMMARY.NET_PER_BOX; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:481 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.NET_PER_BOX, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F502 REPORTING.VW_PRODUCTION_SUMMARY.TOTAL_RECEIVED

**Metadata**

- E01 dev_evidence.json /columns/501: REPORTING.VW_PRODUCTION_SUMMARY.TOTAL_RECEIVED; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:482 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.TOTAL_RECEIVED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F503 REPORTING.VW_PRODUCTION_SUMMARY.REJECTED

**Metadata**

- E01 dev_evidence.json /columns/502: REPORTING.VW_PRODUCTION_SUMMARY.REJECTED; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:483 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.REJECTED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F504 REPORTING.VW_PRODUCTION_SUMMARY.LOSS

**Metadata**

- E01 dev_evidence.json /columns/503: REPORTING.VW_PRODUCTION_SUMMARY.LOSS; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:484 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.LOSS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F505 REPORTING.VW_PRODUCTION_SUMMARY.LEGACY_REJECT_LOSS_TOTAL

**Metadata**

- E01 dev_evidence.json /columns/504: REPORTING.VW_PRODUCTION_SUMMARY.LEGACY_REJECT_LOSS_TOTAL; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:485 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.LEGACY_REJECT_LOSS_TOTAL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F506 REPORTING.VW_PRODUCTION_SUMMARY.TOTAL_ACCEPTED

**Metadata**

- E01 dev_evidence.json /columns/505: REPORTING.VW_PRODUCTION_SUMMARY.TOTAL_ACCEPTED; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/synthetic.py:486 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.TOTAL_ACCEPTED, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F507 REPORTING.VW_PRODUCTION_SUMMARY.SOURCE_TYPE

**Metadata**

- E01 dev_evidence.json /columns/506: REPORTING.VW_PRODUCTION_SUMMARY.SOURCE_TYPE; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/constants/SOURCE_TYPE

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:489 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.SOURCE_TYPE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F508 REPORTING.VW_PRODUCTION_SUMMARY.MATCH_STATUS

**Metadata**

- E01 dev_evidence.json /columns/507: REPORTING.VW_PRODUCTION_SUMMARY.MATCH_STATUS; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/constants/MATCH_STATUS

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:490 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)
- E05 data/importing.py:65-107 (normalize_eims_records)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.MATCH_STATUS, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F509 REPORTING.VW_PRODUCTION_SUMMARY.SOURCE_ROW_NUMBER

**Metadata**

- E01 dev_evidence.json /columns/508: REPORTING.VW_PRODUCTION_SUMMARY.SOURCE_ROW_NUMBER; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/row_number_fields
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/SOURCE_ROW_NUMBER

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/synthetic.py:491 (generate_production, fabricated only)
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.SOURCE_ROW_NUMBER, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F510 REPORTING.VW_PRODUCTION_SUMMARY.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/509: REPORTING.VW_PRODUCTION_SUMMARY.CREATED_AT; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F511 REPORTING.VW_PRODUCTION_SUMMARY.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/510: REPORTING.VW_PRODUCTION_SUMMARY.UPDATED_AT; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Code**

- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F512 REPORTING.VW_PRODUCTION_SUMMARY.TOTAL

**Metadata**

- E01 dev_evidence.json /columns/511: REPORTING.VW_PRODUCTION_SUMMARY.TOTAL; GET_DDL REPORTING.VW_PRODUCTION_SUMMARY
- E01 /ddl/REPORTING.VW_PRODUCTION_SUMMARY output expression

**Mapping**

- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_map/TOTAL
- E05 config/eims_migration_mapping_v3.json /entities/PRODUCTION_RECORD/field_types/TOTAL

**Code**

- E05 data/migration.py:215-233 (_source_value)
- E05 data/migration.py:142-179 (_convert)
- E05 data/importing.py:65-107 (normalize_eims_records)
- E05 data/constants.py EIMS_COLUMN_MAPPING/TOTAL
- E05 data/repositories/snowflake.py:1442-1464 (_insert_production)

**Executed query**

- E01 /field_usage: REPORTING.VW_PRODUCTION_SUMMARY.TOTAL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
- E03 /reports: 1999/21 and 2017/15 grouped TOTAL/CSV/XLSX; saved execution, not a new browser check.

## F513 SECURITY.APP_USER.USER_ID

**Metadata**

- E01 dev_evidence.json /columns/512: SECURITY.APP_USER.USER_ID; GET_DDL SECURITY.APP_USER

**Code**

- E05 app/snowflake_security.py:118-145 (create_user)

**Executed query**

- E01 /field_usage: SECURITY.APP_USER.USER_ID, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F514 SECURITY.APP_USER.EMAIL

**Metadata**

- E01 dev_evidence.json /columns/513: SECURITY.APP_USER.EMAIL; GET_DDL SECURITY.APP_USER

**Code**

- E05 app/snowflake_security.py:118-145 (create_user)

**Executed query**

- E01 /field_usage: SECURITY.APP_USER.EMAIL, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F515 SECURITY.APP_USER.DISPLAY_NAME

**Metadata**

- E01 dev_evidence.json /columns/514: SECURITY.APP_USER.DISPLAY_NAME; GET_DDL SECURITY.APP_USER

**Code**

- E05 app/snowflake_security.py:118-145 (create_user)

**Executed query**

- E01 /field_usage: SECURITY.APP_USER.DISPLAY_NAME, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F516 SECURITY.APP_USER.ROLE

**Metadata**

- E01 dev_evidence.json /columns/515: SECURITY.APP_USER.ROLE; GET_DDL SECURITY.APP_USER

**Code**

- E05 app/snowflake_security.py:118-145 (create_user)
- E05 app/snowflake_security.py:156-182 (update_user)

**Executed query**

- E01 /field_usage: SECURITY.APP_USER.ROLE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F517 SECURITY.APP_USER.ACTIVE

**Metadata**

- E01 dev_evidence.json /columns/516: SECURITY.APP_USER.ACTIVE; GET_DDL SECURITY.APP_USER

**Code**

- E05 app/snowflake_security.py:118-145 (create_user)
- E05 app/snowflake_security.py:156-182 (update_user)

**Executed query**

- E01 /field_usage: SECURITY.APP_USER.ACTIVE, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F518 SECURITY.APP_USER.LAST_LOGIN_AT

**Metadata**

- E01 dev_evidence.json /columns/517: SECURITY.APP_USER.LAST_LOGIN_AT; GET_DDL SECURITY.APP_USER

**Code**

- E05 app/snowflake_security.py:91-97 (resolve_identity)

**Executed query**

- E01 /field_usage: SECURITY.APP_USER.LAST_LOGIN_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F519 SECURITY.APP_USER.CREATED_AT

**Metadata**

- E01 dev_evidence.json /columns/518: SECURITY.APP_USER.CREATED_AT; GET_DDL SECURITY.APP_USER

**Code**

- E05 app/snowflake_security.py:118-145 (create_user)

**Executed query**

- E01 /field_usage: SECURITY.APP_USER.CREATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.

## F520 SECURITY.APP_USER.UPDATED_AT

**Metadata**

- E01 dev_evidence.json /columns/519: SECURITY.APP_USER.UPDATED_AT; GET_DDL SECURITY.APP_USER

**Code**

- E05 app/snowflake_security.py:118-145 (create_user)
- E05 app/snowflake_security.py:156-182 (update_user)

**Executed query**

- E01 /field_usage: SECURITY.APP_USER.UPDATED_AT, non-null/zero counts in the saved 13 October scan; not re-executed in this revision.
