"""Curated EFNS report catalog and safe report execution services."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import io
import pandas as pd

from app.security import Permission, User, has_permission, require_permission
from app.services.export import spreadsheet_safe
from data.constants import QUOTA_TYPES


@dataclass(frozen=True)
class ReportDefinition:
    report_id: str
    name: str
    category: str
    report_type: str
    description: str
    parameters: tuple[str, ...]
    permission: Permission
    status: str
    handler: str | None
    export_formats: tuple[str, ...]
    input_entity: str | None = None


REPORT_CATALOG = (
    ReportDefinition("quota-summary", "Quota Summary Report", "Quota", "Summary Report", "Account and quota registration summary at a selected date. Issuance awaits a confirmed rule.", ("As of Date", "Quota Type", "Account", "Status"), Permission.VIEW_REPORTS, "Available · provisional calculations", "quota_summary", ("CSV", "XLSX")),
    ReportDefinition("flock-age", "Flock Age Report", "Flock", "Operational Report", "Legacy definition of flock age and as-of behavior requires confirmation.", ("As of Date",), Permission.VIEW_REPORTS, "Business rule confirmation required", None, ()),
    ReportDefinition("flock-current", "Flock Current Report", "Flock", "Operational Report", "Legacy meaning of current requires lifecycle-history confirmation.", ("As of Date",), Permission.VIEW_REPORTS, "Business rule confirmation required", None, ()),
    ReportDefinition("flock-current-producer", "Flock Current Report by Producer", "Flock", "Operational Report", "Producer grouping is known; historical current-state semantics require confirmation.", ("As of Date", "Account"), Permission.VIEW_REPORTS, "Business rule confirmation required", None, ()),
    ReportDefinition("salmonella-report", "Salmonella Test Report", "Salmonella", "Operational Report", "Existing filterable Salmonella testing report.", ("Testing Date", "Result", "Account", "Facility", "Flock"), Permission.VIEW_REPORTS, "Available", "salmonella_report", ("CSV", "XLSX"), "SALMONELLA_TEST"),
    ReportDefinition("salmonella-form", "EIMS Salmonella Testing Form", "Forms and Letters", "Form", "Printable source template and approved wording are required.", ("Salmonella Test" ,), Permission.VIEW_REPORTS, "Template confirmation required", None, (), "SALMONELLA_TEST"),
    ReportDefinition("salmonella-letter", "EIMS Salmonella Testing Letter", "Forms and Letters", "Letter", "Printable source template, recipient rules, and approved wording are required.", ("Salmonella Test",), Permission.VIEW_REPORTS, "Template confirmation required", None, (), "SALMONELLA_TEST"),
    ReportDefinition("license-application", "EIMS License Application Form", "Forms and Letters", "Form", "Official layout, declarations, signatures, and licence source record are required.", ("Account",), Permission.VIEW_REPORTS, "Template confirmation required", None, (), "ACCOUNT"),
    ReportDefinition("flock-permit", "Flock Permit Form", "Forms and Letters", "Form", "Official permit layout, declarations, and signature requirements are required.", ("Flock",), Permission.VIEW_REPORTS, "Template confirmation required", None, (), "FLOCK"),
    ReportDefinition("custom-builder", "Customize Report", "Custom", "Custom Report", "Build a report from curated datasets and allowlisted fields.", ("Dataset", "Fields", "Filters", "Grouping", "Sorting", "Aggregations"), Permission.USE_REPORT_BUILDER, "Available", "custom", ("CSV", "XLSX")),
)


@dataclass(frozen=True)
class FieldDefinition:
    label: str
    source: str
    data_type: str = "text"
    aggregations: tuple[str, ...] = ()
    supported_filters: tuple[str, ...] = ()
    permission: Permission = Permission.VIEW_DATA
    export: bool = True


CUSTOM_DATASETS = {
    "Accounts": ("get_accounts", "ACCOUNT_ID", (
        FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Account Name", "ORGANIZATION_NAME"), FieldDefinition("Registration Number", "REGISTRATION_NUMBER"), FieldDefinition("City", "CITY"), FieldDefinition("Province", "PROVINCE"), FieldDefinition("Phone", "CONTACT_PHONE"), FieldDefinition("Status", "STATUS"))),
    "Farm Locations": ("get_farm_locations", "FARM_LOCATION_ID", (
        FieldDefinition("Farm Location ID", "FARM_LOCATION_ID"), FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Location Name", "LOCATION_NAME"), FieldDefinition("Address", "ADDRESS_1"), FieldDefinition("City", "CITY"), FieldDefinition("Province", "PROVINCE"), FieldDefinition("Postal Code", "POSTAL_CODE"), FieldDefinition("Phone", "PHONE"), FieldDefinition("Status", "STATUS"))),
    "Facilities": ("get_facilities", "FACILITY_ID", (
        FieldDefinition("Facility ID", "FACILITY_ID"), FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Facility Name", "FACILITY_NAME"), FieldDefinition("Facility Type", "FACILITY_TYPE"), FieldDefinition("Status", "STATUS"))),
    "Facility Details": ("get_facility_details", "FACILITY_DETAIL_ID", (
        FieldDefinition("Facility Detail ID", "FACILITY_DETAIL_ID"), FieldDefinition("Facility ID", "FACILITY_ID"), FieldDefinition("Detail Name", "DETAIL_NAME"), FieldDefinition("Detail Type", "DETAIL_TYPE"), FieldDefinition("Status", "STATUS"))),
    "Flocks": ("get_flocks", "FLOCK_ID", (
        FieldDefinition("Flock ID", "FLOCK_ID"), FieldDefinition("Flock Number", "FLOCK_NUMBER"), FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Facility ID", "FACILITY_ID"), FieldDefinition("Quota ID", "QUOTA_ID"), FieldDefinition("Status", "STATUS"), FieldDefinition("Hatch Date", "HATCH_DATE", "date"), FieldDefinition("Bird Count", "BIRD_COUNT", "number", ("sum", "min", "max", "mean")))),
    "Flock Transactions": ("get_flock_transactions", "FLOCK_TRANSACTION_ID", (
        FieldDefinition("Transaction ID", "FLOCK_TRANSACTION_ID"), FieldDefinition("Flock ID", "FLOCK_ID"), FieldDefinition("Transaction Type", "TRANSACTION_TYPE"), FieldDefinition("Transaction Date", "TRANSACTION_DATE", "date"), FieldDefinition("Quantity", "QUANTITY", "number", ("sum", "min", "max", "mean")))),
    "Quota Registrations": ("get_quota_registrations", "QUOTA_ID", (
        FieldDefinition("Quota ID", "QUOTA_ID"), FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Registration Number", "REGISTRATION_NUMBER"), FieldDefinition("Quota Name", "QUOTA_NAME"), FieldDefinition("Quota Type", "QUOTA_TYPE"), FieldDefinition("Status", "STATUS"), FieldDefinition("Effective Date", "EFFECTIVE_DATE", "date"), FieldDefinition("End Date", "END_DATE", "date"))),
    "Quota Transactions": ("get_quota_transactions", "QUOTA_TRANSACTION_ID", (
        FieldDefinition("Transaction ID", "QUOTA_TRANSACTION_ID"), FieldDefinition("Quota ID", "QUOTA_ID"), FieldDefinition("Owner Account ID", "OWNER_ACCOUNT_ID"), FieldDefinition("Transaction Type", "TRANSACTION_TYPE"), FieldDefinition("Effective Date", "EFFECTIVE_DATE", "date"), FieldDefinition("Quota Count", "QUOTA_COUNT", "number", ("sum", "min", "max", "mean")), FieldDefinition("Price", "PRICE", "number", ("sum", "min", "max", "mean")))),
    "Salmonella Tests": ("get_salmonella_tests", "SALMONELLA_TEST_ID", (
        FieldDefinition("Test ID", "SALMONELLA_TEST_ID"), FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Flock ID", "FLOCK_ID"), FieldDefinition("Permit Number", "PERMIT_NUMBER"), FieldDefinition("Testing Date", "TESTING_DATE", "date"), FieldDefinition("Result", "TEST_RESULT"), FieldDefinition("Number of Samples", "NUMBER_OF_SAMPLES", "number", ("sum", "min", "max", "mean")))),
    "Production Records": ("get_production_records", "PRODUCTION_ID", (
        FieldDefinition("Production ID", "PRODUCTION_ID"), FieldDefinition("Producer Account ID", "PRODUCER_ACCOUNT_ID"), FieldDefinition("Facility ID", "FACILITY_ID"), FieldDefinition("Flock ID", "FLOCK_ID"), FieldDefinition("Reporting Year", "REPORTING_YEAR", "number"), FieldDefinition("Reporting Week", "REPORTING_WEEK", "number"), FieldDefinition("Total Received", "TOTAL_RECEIVED", "number", ("sum", "min", "max", "mean")), FieldDefinition("Total Accepted", "TOTAL_ACCEPTED", "number", ("sum", "min", "max", "mean")), FieldDefinition("Match Status", "MATCH_STATUS"))),
}


def visible_catalog(user: User) -> tuple[ReportDefinition, ...]:
    return tuple(report for report in REPORT_CATALOG if has_permission(user, report.permission))


def report_definition(report_id: str) -> ReportDefinition:
    try:
        return next(report for report in REPORT_CATALOG if report.report_id == report_id)
    except StopIteration as exc:
        raise ValueError("Unknown report definition.") from exc


def build_quota_summary(
    repo,
    *,
    user: User,
    as_of_date,
    quota_type: str,
    account_id=None,
    status="Active",
):
    require_permission(user, Permission.VIEW_REPORTS)
    if not isinstance(as_of_date, (dt.date, dt.datetime, pd.Timestamp)):
        raise ValueError("As of Date is required.")
    if quota_type not in QUOTA_TYPES:
        raise ValueError("Quota Type must be selected from the supported values.")
    frame = repo.get_quota_summary(as_of_date, quota_type, account_id=account_id, status=status)
    if frame.empty:
        return frame, {"producer_count": 0, "total_issuance": None}
    frame = frame.drop_duplicates("QUOTA_ID").reset_index(drop=True)
    producer_count = frame.loc[frame["PRODUCER_ROLE"].fillna(False).astype(bool), "ACCOUNT_ID"].nunique()
    issuance = pd.to_numeric(frame["ISSUANCE"], errors="coerce") if "ISSUANCE" in frame else pd.Series(dtype=float)
    total_issuance = None if issuance.notna().sum() == 0 else issuance.sum()
    columns = ["REGISTRATION_NUMBER", "ACCOUNT_NAME", "ADDRESS", "CITY", "PROVINCE", "POSTAL_CODE", "PHONE", "FAX", "ISSUANCE"]
    return frame[[column for column in columns if column in frame]], {
        "producer_count": int(producer_count), "total_issuance": total_issuance,
    }


def _query_dataset(repo, name: str, filters: dict) -> pd.DataFrame:
    method_name, _id, _fields = CUSTOM_DATASETS[name]
    method = getattr(repo, method_name)
    supported = {
        "Accounts": ("statuses", "role_field", "keyword"),
        "Farm Locations": ("farm_location_id", "account_id", "statuses", "keyword"),
        "Facilities": ("account_id", "statuses"),
        "Facility Details": ("facility_id", "account_id", "statuses"),
        "Flocks": ("account_id", "facility_id", "facility_detail_id", "statuses"),
        "Flock Transactions": ("flock_id", "account_id", "transaction_type", "date_from", "date_to"),
        "Quota Registrations": ("account_id", "quota_type", "statuses"),
        "Quota Transactions": ("account_id", "quota_id", "quota_type", "transaction_type", "date_from", "date_to"),
        "Salmonella Tests": ("account_id", "facility_id", "flock_id", "test_result", "date_from", "date_to"),
        "Production Records": ("reporting_year", "reporting_week", "grader_number", "barn_identity", "egg_colour", "account_id"),
    }[name]
    return method(**{key: value for key, value in filters.items() if key in supported and value not in (None, "", ())})


def build_custom_report(
    repo,
    *,
    user: User,
    dataset: str,
    selected_fields: list[str],
    filters=None,
    sort_by=None,
    ascending=True,
    group_by=None,
    aggregations=None,
) -> pd.DataFrame:
    require_permission(user, Permission.USE_REPORT_BUILDER)
    if dataset not in CUSTOM_DATASETS:
        raise ValueError("Dataset is not available for custom reporting.")
    _method, id_field, definitions = CUSTOM_DATASETS[dataset]
    fields = {field.source: field for field in definitions}
    if not selected_fields or any(field not in fields for field in selected_fields):
        raise ValueError("Select one or more allowlisted report fields.")
    for field in selected_fields:
        require_permission(user, fields[field].permission)
    frame = _query_dataset(repo, dataset, filters or {})
    if id_field in frame.columns:
        frame = frame.drop_duplicates(id_field)
    group_by = list(group_by or [])
    aggregations = dict(aggregations or {})
    if any(field not in fields for field in group_by):
        raise ValueError("Grouping field is not allowlisted.")
    for field, operation in aggregations.items():
        if field not in fields or operation not in fields[field].aggregations:
            raise ValueError("Aggregation is not supported for the selected field.")
    if aggregations:
        if not group_by:
            raise ValueError("Choose at least one grouping field for aggregations.")
        frame = frame.groupby(group_by, dropna=False, as_index=False).agg(aggregations)
        selected_fields = [*group_by, *[field for field in aggregations if field not in group_by]]
    available = [field for field in selected_fields if field in frame.columns]
    result = frame[available].copy() if available else pd.DataFrame(columns=selected_fields)
    if sort_by:
        if sort_by not in result.columns:
            raise ValueError("Sort field must be included in the report output.")
        result = result.sort_values(sort_by, ascending=bool(ascending), kind="stable")
    return result.rename(columns={source: fields[source].label for source in available}).reset_index(drop=True)


def report_csv(user: User, frame: pd.DataFrame) -> bytes:
    require_permission(user, Permission.EXPORT_REPORT)
    return spreadsheet_safe(frame).to_csv(index=False).encode("utf-8-sig")


def report_xlsx(user: User, frame: pd.DataFrame, sheet_name="EFNS Report") -> bytes:
    require_permission(user, Permission.EXPORT_REPORT)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        spreadsheet_safe(frame).to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return buffer.getvalue()
