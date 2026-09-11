"""Shared EFNS constants, including provisional business choices."""

UNASSIGNED_LABEL = "Unassigned"

ACCOUNT_STATUSES = ("Active", "Inactive")
FACILITY_STATUSES = ("Active", "Inactive", "Closed")
FLOCK_STATUSES = ("Planned", "Active", "Depopulated")
EGG_COLOURS = ("White", "Brown", "Mostly White", "Mostly Brown")
FLOCK_QUOTA_TYPES = (
    "Egg Production",
    "Non-Commercial Pullet",
    "Commercial Pullet",
)
QUOTA_TYPES = FLOCK_QUOTA_TYPES
QUOTA_STATUSES = ("Active", "Inactive", "Expired")
QUOTA_TRANSACTION_TYPES = ("Purchase", "Sale", "Lease In", "Lease Out")
QUOTA_LEASE_TYPES = ("Fixed Term", "Open Ended", "Seasonal")
SALMONELLA_RESULTS = ("Pending", "Negative", "Positive", "Inconclusive")
FLOCK_TRANSACTION_TYPES = ("Count", "Delivery", "Removal", "Sale")

SOURCE_TYPE_SYNTHETIC = "SYNTHETIC"
SOURCE_TYPE_EIMS_IMPORT = "EIMS_IMPORT"
MATCH_STATUS_UNMATCHED = "UNMATCHED"

EIMS_WORKSHEET_NAME = "EIMS 3"
EIMS_SOURCE_COLUMNS = (
    "Grader",
    "Producer #",
    "Grader#",
    "Week",
    "MarketingType",
    "Housing system",
    "Egg Type",
    "Colour",
    "J",
    "XL",
    "L",
    "M",
    "S",
    "PW",
    "B",
    "C",
    "CR",
    "NestRun",
    "NR25+",
    "NR24+",
    "NR23+",
    "NR22+",
    "NR21+",
    "NR20+",
    "NR19+",
    "NR18+",
    "NR17+",
    "OL",
    "ON",
    "FG",
    "FC",
    "Subtotal",
    "RJ",
    "LK",
    "Total",
)

EIMS_REQUIRED_COLUMNS = (
    "Grader",
    "Producer #",
    "Grader#",
    "Week",
    "MarketingType",
    "Housing system",
    "Egg Type",
    "Colour",
    "J",
    "XL",
    "L",
    "M",
    "S",
    "PW",
    "B",
    "C",
    "CR",
    "NestRun",
    "RJ",
    "LK",
    "Total",
)

EIMS_COLUMN_MAPPING = {
    "Grader": "GRADER_NAME",
    "Producer #": "PRODUCER_NUMBER",
    "Grader#": "GRADER_NUMBER",
    "Week": "SOURCE_WEEK_CODE",
    "MarketingType": "MARKETING_TYPE",
    "Housing system": "HOUSING_SYSTEM",
    "Egg Type": "EGG_TYPE",
    "Colour": "EGG_COLOUR",
    "J": "JUMBO",
    "XL": "EXTRA_LARGE",
    "L": "LARGE",
    "M": "MEDIUM",
    "S": "SMALL",
    "PW": "PEEWEE",
    "B": "GRADE_B",
    "C": "GRADE_C",
    "CR": "CRACKS",
    "NestRun": "NEST_RUN",
    "NR25+": "NEST_RUN_25_PLUS",
    "NR24+": "NEST_RUN_24_PLUS",
    "NR23+": "NEST_RUN_23_PLUS",
    "NR22+": "NEST_RUN_22_PLUS",
    "NR21+": "NEST_RUN_21_PLUS",
    "NR20+": "NEST_RUN_20_PLUS",
    "NR19+": "NEST_RUN_19_PLUS",
    "NR18+": "NEST_RUN_18_PLUS",
    "NR17+": "NEST_RUN_17_PLUS",
    "OL": "OTHER_LEVIABLE",
    "ON": "OTHER_NON_LEVIABLE",
    "FG": "FARM_GATE_SALES",
    "FC": "ON_FARM_CONSUMPTION",
    "Subtotal": "SUBTOTAL",
    "RJ": "REJECTS",
    "LK": "LEAKERS",
    "Total": "TOTAL",
}

EIMS_NUMERIC_COLUMNS = tuple(EIMS_SOURCE_COLUMNS[8:])
