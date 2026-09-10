# AS-IS Model (Current EIMS)

> **STATUS: PROVISIONAL — Based on observed/conversational understanding only.**
> The actual Dataverse schema has NOT yet been reverse-engineered.

## System

- Application: **EIMS**
- Platform: **Microsoft Dynamics 365 / Power Apps**
- Data store: **Dataverse** (confirmed)

## Known Limitations of This Document

This document is derived from what has been *observed or described*, not from
inspecting the actual Dataverse environment. It is a starting hypothesis only.

## Observed Operational Areas

### 1. Accounts / Producers

An account represents a farm, business, or producer organization.

Observed concepts:
- Account / organization name
- Registration number
- Address
- Contact information
- Licence information
- Producer role
- Breeder role
- Hatchery role
- Grader role

### 2. Facilities

An Account can have one or more facilities.

Observed concepts:
- Facility identifier
- Related account
- Facility name
- Facility type (pullet / layer / other)
- Status
- Activation / construction dates
- Closure / destruction / inactive dates

**Provisional interpretation:** ACCOUNT 1:N FACILITY

### 3. Flocks

Facilities/accounts have flocks.

Observed concepts:
- Flock number
- Licence number
- Account
- Facility
- Bird count
- Placement date
- Hatch date
- Egg/bird colour classification (White, Brown, Mostly White, Mostly Brown)
- Estimated production completion
- Estimated disposal
- Actual disposal
- Disposal method
- Status

**Provisional interpretation:** ACCOUNT → FACILITY → FLOCK

### 4. Flock Transactions

Observed transaction types:
- Count
- Delivery
- Removal
- Sale

Transactions represent **history** rather than simply overwriting flock values.

**Provisional interpretation:** FLOCK 1:N FLOCK_TRANSACTION

### 5. Quota

Two major concepts:

- **QUOTA_REGISTRATION** — quota officially registered/allocated to a producer
- **QUOTA_TRANSACTION** — allocation, increase, decrease, transfer, temporary lease

Leasing must support source producer, destination producer, quantity, start/end
dates, and history.

**Status: NOT modeled in v0.1** — documented as Phase 2.

### 6. Salmonella / Disease Testing

Records exist, with concepts:
- Producer/account
- Facility or flock
- Test date
- Positive/negative result

**Detailed business rules NOT yet confirmed. Do NOT invent them.**

## Production / CSV Workflow (As Described)

```
External farm/grader CSV
        ↓
EFNS staff receives files
        ↓
Staff manually consolidates info into a larger spreadsheet
        ↓
Calculations / classification
        ↓
Current EIMS
        ↓
Sara manually enters/updates related operational info (e.g. flock transactions)
```

The CSV may contain: grader number, barn identity, flock age, egg colour,
net weight, net boxes, net per box, egg size/weight bands, totals, and
production classifications.

Reporting concepts: Total Received, Rejected, Loss, Total Accepted, egg
categories/sizes, percentages, boxes, dozens.

Historical data may contain a **combined "Rejects/Loss"** value.

## Reporting (As Described)

A major requested improvement: customizable reporting. The current system can
generate reports with many fields, but staff wants to control which fields or
sections are included.