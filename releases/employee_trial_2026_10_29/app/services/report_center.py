"""Curated EFNS report catalog and safe report execution services."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import io
import pandas as pd

from app.security import Permission, User, has_permission, require_permission
from app.services.export import spreadsheet_safe
from data.constants import QUOTA_TYPES
from data.quota_types import quota_type_key, supported_quota_type
from app.services.report_relationships import report_relationships
from data.producer_identity import production_identities, text as stored_text
from data.source_scope import scope_production


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
        FieldDefinition("Flock ID", "FLOCK_ID"), FieldDefinition("Flock Number", "FLOCK_NUMBER"), FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Facility ID", "FACILITY_ID"), FieldDefinition("Quota ID", "QUOTA_ID"), FieldDefinition("Quota Type", "FLOCK_QUOTA_TYPE"), FieldDefinition("Status", "STATUS"), FieldDefinition("Hatch Date", "HATCH_DATE", "date"), FieldDefinition("Placement Date", "PLACEMENT_DATE", "date"), FieldDefinition("Estimated Disposal Date", "EST_DISPOSAL", "date"), FieldDefinition("Actual Disposal Date", "DISPOSAL_DATE", "date"), FieldDefinition("Bird Count", "BIRD_COUNT", "number", ("sum", "min", "max", "mean")))),
    "Flock Transactions": ("get_flock_transactions", "FLOCK_TRANSACTION_ID", (
        FieldDefinition("Transaction ID", "FLOCK_TRANSACTION_ID"), FieldDefinition("Flock ID", "FLOCK_ID"), FieldDefinition("Transaction Type", "TRANSACTION_TYPE"), FieldDefinition("Transaction Date", "TRANSACTION_DATE", "date"), FieldDefinition("Quantity", "QUANTITY", "number", ("sum", "min", "max", "mean")), FieldDefinition("Count Source", "COUNT_SOURCE_LABEL"))),
    "Quota Registrations": ("get_quota_registrations", "QUOTA_ID", (
        FieldDefinition("Quota ID", "QUOTA_ID"), FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Registration Number", "REGISTRATION_NUMBER"), FieldDefinition("Quota Name", "QUOTA_NAME"), FieldDefinition("Quota Type", "QUOTA_TYPE"), FieldDefinition("Status", "STATUS"), FieldDefinition("Effective Date", "EFFECTIVE_DATE", "date"), FieldDefinition("End Date", "END_DATE", "date"))),
    "Quota Transactions": ("get_quota_transactions", "QUOTA_TRANSACTION_ID", (
        FieldDefinition("Transaction ID", "QUOTA_TRANSACTION_ID"), FieldDefinition("Quota ID", "QUOTA_ID"), FieldDefinition("Owner Account ID", "OWNER_ACCOUNT_ID"), FieldDefinition("Transaction Type", "TRANSACTION_TYPE"), FieldDefinition("Effective Date", "EFFECTIVE_DATE", "date"), FieldDefinition("Quota Count", "QUOTA_COUNT", "number", ("sum", "min", "max", "mean")), FieldDefinition("Price", "PRICE", "number", ("sum", "min", "max", "mean")), FieldDefinition("Credit Type", "QUOTA_LEASE_TYPE"))),
    "Salmonella Tests": ("get_salmonella_tests", "SALMONELLA_TEST_ID", (
        FieldDefinition("Test ID", "SALMONELLA_TEST_ID"), FieldDefinition("Account ID", "ACCOUNT_ID"), FieldDefinition("Flock ID", "FLOCK_ID"), FieldDefinition("Permit Number", "PERMIT_NUMBER"), FieldDefinition("Testing Date", "TESTING_DATE", "date"), FieldDefinition("Result", "TEST_RESULT"), FieldDefinition("Number of Samples", "NUMBER_OF_SAMPLES", "number", ("sum", "min", "max", "mean")))),
    "Production Records": ("get_production_records", "PRODUCTION_ID", (
        FieldDefinition("Producer identity", "PRODUCER_IDENTITY_LABEL"), FieldDefinition("Producer identity key", "PRODUCER_IDENTITY_KEY"), FieldDefinition("Producer identity status", "PRODUCER_IDENTITY_STATUS"), FieldDefinition("Source Producer #", "PRODUCER_NUMBER"),
        FieldDefinition("Production ID", "PRODUCTION_ID"), FieldDefinition("Producer Account ID", "PRODUCER_ACCOUNT_ID"), FieldDefinition("Facility ID", "FACILITY_ID"), FieldDefinition("Flock ID", "FLOCK_ID"), FieldDefinition("Reporting Year", "REPORTING_YEAR", "number"), FieldDefinition("Reporting Week", "REPORTING_WEEK", "number"), FieldDefinition("Total Received", "TOTAL_RECEIVED", "number", ("sum", "min", "max", "mean")), FieldDefinition("Total Accepted", "TOTAL_ACCEPTED", "number", ("sum", "min", "max", "mean")), FieldDefinition("Match Status", "MATCH_STATUS"), FieldDefinition("Source scope", "SOURCE_SCOPE"), FieldDefinition("Import ID", "IMPORT_ID"))),
}

_RELATIONSHIP_DATASETS = {
    "Flocks": "FLOCK", "Flock Transactions": "FLOCK_TRANSACTION",
    "Production Records": "PRODUCTION_RECORD",
}
for _dataset in _RELATIONSHIP_DATASETS:
    _method, _key, _fields = CUSTOM_DATASETS[_dataset]
    if _dataset == "Production Records":
        _fields = tuple(FieldDefinition("Production Facility ID", field.source) if field.source == "FACILITY_ID" else field
                        for field in _fields)
    CUSTOM_DATASETS[_dataset] = (_method, _key, (*_fields,
        FieldDefinition("Flock Account ID", "FLOCK_ACCOUNT_ID"),
        FieldDefinition("Flock Account", "FLOCK_ACCOUNT_NAME"),
        FieldDefinition("Facility Account ID", "FACILITY_ACCOUNT_ID"),
        FieldDefinition("Facility Account", "FACILITY_ACCOUNT_NAME"),
        FieldDefinition("Facility Name", "FACILITY_NAME"),
        FieldDefinition("Report Facility ID", "REPORT_FACILITY_ID"),
        *([FieldDefinition("Producer Account", "PRODUCER_ACCOUNT_NAME"),
           FieldDefinition("Source Total", "TOTAL", "number", ("sum", "min", "max", "mean")),
           FieldDefinition("Flock Facility ID", "FLOCK_FACILITY_ID"),
           FieldDefinition("Facility Source", "REPORT_FACILITY_SOURCE"),
           FieldDefinition("Facility Reference Comparison", "FACILITY_REFERENCE_DIFFERENCE")]
          if _dataset == "Production Records" else []),
    ))


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
    if not supported_quota_type(quota_type):
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


def transaction_type_options(repo, dataset: str) -> tuple[str, ...]:
    """Report filters describe stored activity, not the new-entry allowlist."""
    methods = {'Flock Transactions': 'get_flock_transactions',
               'Quota Transactions': 'get_quota_transactions'}
    if dataset not in methods:
        return ()
    frame = getattr(repo, methods[dataset])()
    values = frame.get('TRANSACTION_TYPE', pd.Series(dtype=object))
    return tuple(sorted({stored_text(value) for value in values if stored_text(value)}))


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
    derived=set()
    if name in {'Flocks','Flock Transactions','Production Records'}:
        derived.update(('facility_id','flock_id','facility_account_id','flock_account_id'))
    if name=='Flocks':derived.update(('date_from','date_to','date_field','quota_type'))
    if name=='Production Records':derived.add('source_scope')
    unsupported=[key for key,value in filters.items() if value not in (None,'',(),[],False) and key not in set(supported)|derived]
    if unsupported:raise ValueError('Unsupported filter(s) for this dataset: '+', '.join(unsupported))
    return method(**{key: value for key, value in filters.items() if key in supported and value not in (None, "", ())})


def _sum_known_values(values: pd.Series):
    return values.sum(min_count=1)


FLOCK_RECORD_COUNT = "_FLOCK_RECORD_COUNT"
FLOCK_RECORD_COUNT_LABEL = "Flock record count"


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
    count_records=False,
) -> pd.DataFrame:
    require_permission(user, Permission.USE_REPORT_BUILDER)
    if dataset not in CUSTOM_DATASETS:
        raise ValueError("Dataset is not available for custom reporting.")
    if dataset == "Production Records" and any((filters or {}).get(key) not in (None, "") for key in ("date_from", "date_to")):
        raise ValueError("Production reports use Reporting Year and Reporting Week, not an inferred calendar date range.")
    _method, id_field, definitions = CUSTOM_DATASETS[dataset]
    fields = {field.source: field for field in definitions}
    if not selected_fields or any(field not in fields for field in selected_fields):
        raise ValueError("Select one or more allowlisted report fields.")
    for field in selected_fields:
        require_permission(user, fields[field].permission)
    frame = _query_dataset(repo, dataset, filters or {})
    if dataset == 'Flocks' and any((filters or {}).get(k) not in (None,'') for k in ('date_from','date_to')):
        date_field=(filters or {}).get('date_field')
        if date_field not in {'HATCH_DATE','PLACEMENT_DATE','EST_DISPOSAL','DISPOSAL_DATE'}:
            raise ValueError('Choose the Flock date field for the date range.')
        dates=pd.to_datetime(frame[date_field],errors='coerce').dt.date
        for bound,op in (('date_from','ge'),('date_to','le')):
            if (filters or {}).get(bound) not in (None,''):
                value=pd.Timestamp(filters[bound]).date()
                frame=frame.loc[dates.ge(value) if op=='ge' else dates.le(value)]
                dates=dates.loc[frame.index]
    if dataset == 'Flocks' and (filters or {}).get('quota_type'):
        frame = frame[frame['FLOCK_QUOTA_TYPE'].map(quota_type_key) == quota_type_key(filters['quota_type'])]
    if id_field in frame.columns:
        if dataset in _RELATIONSHIP_DATASETS and frame[id_field].duplicated().any():
            raise ValueError("Duplicate report record identifiers; resolve the data issue before aggregating.")
        frame = frame.drop_duplicates(id_field)
    relationship_fields = {"FLOCK_ACCOUNT_ID", "FLOCK_ACCOUNT_NAME", "FACILITY_ACCOUNT_ID",
                           "FACILITY_ACCOUNT_NAME", "FACILITY_NAME", "REPORT_FACILITY_ID",
                           "PRODUCER_ACCOUNT_NAME", "FLOCK_FACILITY_ID", "REPORT_FACILITY_SOURCE",
                           "FACILITY_REFERENCE_DIFFERENCE"}
    relationship_filters = {"flock_account_id", "facility_account_id", "facility_id", "flock_id"}
    needs_relationships = bool(relationship_fields.intersection([*selected_fields, *(group_by or [])])) or any(
        (filters or {}).get(key) not in (None, "") for key in relationship_filters
    )
    if dataset in _RELATIONSHIP_DATASETS and needs_relationships:
        frame = report_relationships(repo, frame, _RELATIONSHIP_DATASETS[dataset])
        role_filters = {"flock_account_id": "FLOCK_ACCOUNT_ID", "facility_account_id": "FACILITY_ACCOUNT_ID",
                        "facility_id": "REPORT_FACILITY_ID", "flock_id": "FLOCK_ID"}
        for parameter, column in role_filters.items():
            value = (filters or {}).get(parameter)
            if value not in (None, ""):
                frame = frame.loc[frame[column] == value]
    group_by = list(group_by or [])
    if dataset == "Production Records":
        frame = production_identities(frame)
        frame = scope_production(frame, (filters or {}).get('source_scope', 'All DEV records (mixed sources)'))
    aggregations = dict(aggregations or {})
    if count_records and dataset != "Flocks":
        raise ValueError("Flock record count is only available for Flocks.")
    if any(field not in fields for field in group_by):
        raise ValueError("Grouping field is not allowlisted.")
    for field, operation in aggregations.items():
        if field not in fields or operation not in fields[field].aggregations:
            raise ValueError("Aggregation is not supported for the selected field.")
    # Legacy grouped Flock configurations with no numeric aggregation also
    # mean record counts, never a silent return to detail rows.
    count_records = count_records or (dataset == "Flocks" and bool(group_by) and not aggregations)
    if count_records:
        if not group_by:
            raise ValueError("Choose at least one grouping field for Flock record count.")
        if aggregations:
            raise ValueError("Choose either Flock record count or a numeric aggregation.")
        frame = frame.groupby(group_by, dropna=False, observed=True).size().reset_index(name=FLOCK_RECORD_COUNT)
        fields[FLOCK_RECORD_COUNT] = FieldDefinition(FLOCK_RECORD_COUNT_LABEL, FLOCK_RECORD_COUNT, "number")
        selected_fields = [*group_by, FLOCK_RECORD_COUNT]
    elif aggregations:
        if not group_by:
            raise ValueError("Choose at least one grouping field for aggregations.")
        operations = {
            field: _sum_known_values if operation == "sum" else operation
            for field, operation in aggregations.items()
        }
        if dataset == 'Production Records' and aggregations.get('TOTAL') == 'sum':
            frame = frame.assign(_RECORD_COUNT=1,_TOTAL_KNOWN=frame.TOTAL.notna().astype(int),_TOTAL_MISSING=frame.TOTAL.isna().astype(int))
            operations.update(_RECORD_COUNT='sum',_TOTAL_KNOWN='sum',_TOTAL_MISSING='sum')
            fields.update({key:FieldDefinition(label,key) for key,label in [('_RECORD_COUNT','Record count'),('_TOTAL_KNOWN','Source Total known count'),('_TOTAL_MISSING','Source Total missing count')]})
        for quota_column in ('QUOTA_TYPE', 'FLOCK_QUOTA_TYPE'):
            if quota_column in group_by and quota_column in frame:
                frame[quota_column] = frame[quota_column].map(quota_type_key)
        internal_group = group_by.copy()
        if dataset == "Production Records" and {"PRODUCER_ACCOUNT_ID", "PRODUCER_ACCOUNT_NAME"}.intersection(group_by) and frame.PRODUCER_ACCOUNT_ID.isna().any():
            if "PRODUCER_IDENTITY_KEY" not in internal_group: internal_group.append("PRODUCER_IDENTITY_KEY")
            if "PRODUCER_IDENTITY_LABEL" not in internal_group: internal_group.append("PRODUCER_IDENTITY_LABEL")
        frame = frame.groupby(internal_group, dropna=False, as_index=False).agg(operations)
        group_by = internal_group
        selected_fields = [*group_by, *[field for field in aggregations if field not in group_by]]
        if '_RECORD_COUNT' in operations: selected_fields += ['_RECORD_COUNT','_TOTAL_KNOWN','_TOTAL_MISSING']
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
