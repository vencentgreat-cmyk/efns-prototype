# Dataverse Discovery Checklist

> **Purpose:** Everything we need to extract from the existing EIMS
> (Microsoft Dynamics 365 / Power Apps / Dataverse) environment before the
> target model can be finalized.

## How to Obtain This Information

- **Option A: Metadata export** — From Power Platform admin center / solution
  export (unmanaged solution as XML).
- **Option B: Dataverse Web API** — Query `EntityDefinitions`, `AttributeMetadata`,
  `RelationshipDefinitions` endpoints.
- **Option C: Power Apps Maker Portal** — Manually inspect Tables, Columns,
  Relationships, Views, and Flows.
- **Option D: Solution export** — Export the managed/unmanaged solution and
  inspect the customizations XML.

---

## 1. Tables

- [ ] Complete list of all Dataverse tables (logical name + display name + schema name)
- [ ] Which tables are custom vs system/standard (e.g., `account`, `contact`)
- [ ] Which tables are "activity" tables
- [ ] Total count of tables
- [ ] For each table: primary key / primary name column
- [ ] For each table: whether it is user-owned, organization-owned, or business-unit-owned

## 2. Columns

- [ ] Complete column list per table (logical name + display name)
- [ ] Column data types (Text, Whole Number, Decimal, Currency, Date Only, Date Time,
      Choice, Lookup, Boolean, Memo, etc.)
- [ ] Max lengths / precision for text and numeric columns
- [ ] Which columns are custom vs system (e.g., `createdon`, `modifiedon`, `ownerid`)
- [ ] Alternate keys

## 3. Primary Keys

- [ ] Primary key column name per table
- [ ] Whether keys are GUIDs (default Dataverse) or custom auto-numbers
- [ ] Any composite/alternate keys used for external identification

## 4. Relationships

- [ ] All 1:N relationships (parent table, child table, lookup column name)
- [ ] All N:N relationships (tables involved, intersect entity name)
- [ ] Relationship behavior (Cascade, Restrict, Remove Link)
- [ ] Which lookups are polymorphic (e.g., `customerid` → account or contact)
- [ ] Whether relationship uses business key vs GUID

## 5. Lookup Targets

- [ ] For every lookup column, the target table(s)
- [ ] Whether lookups are single or multi-select

## 6. Choices / Option Sets

- [ ] All local (per-column) choice fields with their integer values + labels
- [ ] All global option sets and where they are used
- [ ] Multi-select choice fields
- [ ] Default values
- [ ] Any custom ordering

Specific choices to confirm:
- [ ] Facility type values (pullet / layer / other — actual labels + values)
- [ ] Egg/bird colour classification values
- [ ] Flock status values
- [ ] Transaction type values (count / delivery / removal / sale — confirm)
- [ ] Disposal method values
- [ ] Account/producer status values
- [ ] Role flags or role choice (producer / breeder / hatchery / grader)
- [ ] Egg size band values
- [ ] Salmonella test result values

## 7. Required Fields

- [ ] For each table, which columns are required (business-required vs system-required)
- [ ] Which columns have default values
- [ ] Which are read-only / system-managed

## 8. Calculated / Rollup Fields

- [ ] Calculated columns (formula)?
- [ ] Rollup columns (aggregations over related records)?
- [ ] Which are synced vs real-time

## 9. Views

- [ ] All system views per table
- [ ] All custom/personal views that staff rely on
- [ ] View filters and sorting
- [ ] Which views are used in Model-Driven App forms

## 10. Business Rules

- [ ] Table-level business rules (conditions + actions)
- [ ] Form-level business rules
- [ ] Any JavaScript web resources performing validation/logic
- [ ] Plugin registrations (if accessible)

## 11. Power Automate Flows

- [ ] All cloud flows (solution-aware) related to EIMS
- [ ] Trigger type (Dataverse row created/modified, scheduled, manual)
- [ ] What each flow writes or transforms
- [ ] Any flows that create/update production, flock, or quota data
- [ ] Any scheduled flows that generate reports or notifications

## 12. Record Counts

- [ ] Approximate row count per table (for sizing the Snowflake migration)
- [ ] Historical depth (how many years of data)
- [ ] Growth rate estimates

## 13. Import / Export Mechanisms

- [ ] How data currently enters EIMS (manual entry, CSV import, integration)
- [ ] Any Excel templates used by staff
- [ ] Any external system integrations
- [ ] Export formats used for reporting
- [ ] Sample production CSV files (from Sara)

## 14. Attachments / Files

- [ ] Note attachment tables
- [ ] File columns (images, documents)
- [ ] SharePoint/OneDrive integrations
- [ ] Approximate storage volume

## 15. Audit / History Behavior

- [ ] Dataverse audit enabled? At which tables/columns?
- [ ] How much history is retained?
- [ ] Any custom history/versioning tables
- [ ] Whether flock transaction "history" is a custom table or audit-driven

---

## Priority Order

1. **High** — Tables, columns, primary keys, relationships (Sections 1-4)
2. **High** — Choice/option sets (Section 6) — needed for correct classification
3. **High** — Sample production CSVs (Section 13) — needed to finalize ingestion
4. **Medium** — Business rules, Power Automate flows (Sections 10-11)
5. **Medium** — Views, required fields (Sections 7, 9)
6. **Lower** — Record counts, audit behavior (Sections 12, 15)

## Deliverable Format

Please provide (any combination):
- Exported unmanaged solution (.zip)
- Dataverse metadata JSON (EntityDefinitions + AttributeMetadata + RelationshipDefinitions)
- Screenshots of table/column definitions from the Maker Portal
- Sample production CSV files with realistic (or anonymized) data
- A list of custom flows with descriptions