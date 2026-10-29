# Runtime difference from saved live snapshot

```json
{
  "added": [
    "app/services/form_safety.py",
    "app/services/quota_usage.py",
    "data/business_time.py",
    "data/flock_quantity.py",
    "data/record_safety.py"
  ],
  "removed": [],
  "modified": [
    "app/navigation.py",
    "app/pages/11_Facilities.py",
    "app/pages/13_Facility_Details.py",
    "app/pages/18_Farm_Locations.py",
    "app/pages/1_Production_Import.py",
    "app/pages/21_Record_History.py",
    "app/pages/3_Accounts_Facilities_Flocks.py",
    "app/pages/4_Reports.py",
    "app/pages/5_Flocks.py",
    "app/pages/6_Flock_Transactions.py",
    "app/pages/7_Quota_Registrations.py",
    "app/pages/8_Quota_Transactions.py",
    "app/pages/9_Salmonella_Tests.py",
    "app/services/authorized_repository.py",
    "app/services/report_center.py",
    "app/ui.py",
    "data/operational_flock_quota_import.py",
    "data/production_intake.py",
    "data/repositories/base.py",
    "data/repositories/continuity.py",
    "data/repositories/mock.py",
    "data/repositories/snowflake.py",
    "data/validation.py"
  ]
}
```

The review copy differs in four disabled authentication seed literals; the deployment candidate does not.
