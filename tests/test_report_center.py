"""Focused contracts for the internal Report Center."""

from __future__ import annotations

import datetime as dt
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.navigation import format_timestamp
from app.security import AuthorizationError, Permission, Role, User
from app.services.report_center import (
    CUSTOM_DATASETS,
    REPORT_CATALOG,
    build_custom_report,
    build_quota_summary,
    report_csv,
    report_xlsx,
    visible_catalog,
)
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository


def user(role=Role.REPORTING_VIEWER, *, active=True):
    return User("report-user", "reporter@nsegg.ca", "Reporter", role, active, False, "now", "now", None)


def test_catalog_contains_only_confirmed_and_existing_report_names():
    names = {report.name for report in REPORT_CATALOG}
    assert names == {
        "EIMS Salmonella Testing Form",
        "EIMS Salmonella Testing Letter",
        "EIMS License Application Form",
        "Flock Permit Form",
        "Flock Age Report",
        "Flock Current Report",
        "Flock Current Report by Producer",
        "Quota Summary Report",
        "Salmonella Test Report",
        "Customize Report",
    }
    assert len({report.report_id for report in REPORT_CATALOG}) == len(REPORT_CATALOG)
    assert all(report.permission in {Permission.VIEW_REPORTS, Permission.USE_REPORT_BUILDER} for report in REPORT_CATALOG)


def test_catalog_and_report_execution_apply_permissions():
    inactive = user(active=False)
    assert visible_catalog(inactive) == ()
    with pytest.raises(AuthorizationError):
        build_quota_summary(
            MockRepository(), user=inactive, as_of_date=dt.date.today(), quota_type="Egg Production"
        )


class QuotaSummaryRepository:
    def __init__(self):
        self.arguments = None

    def get_quota_summary(self, as_of_date, quota_type, account_id=None, status="Active"):
        self.arguments = (as_of_date, quota_type, account_id, status)
        return pd.DataFrame(
            [
                {
                    "QUOTA_ID": "quota-1", "ACCOUNT_ID": "account-1",
                    "REGISTRATION_NUMBER": "REG-1", "ACCOUNT_NAME": "Synthetic One",
                    "ADDRESS": "1 Test Road", "CITY": "Truro", "PROVINCE": "NS",
                    "POSTAL_CODE": "B2N 1A1", "PHONE": "555-0100", "FAX": None,
                    "PRODUCER_ROLE": True, "ISSUANCE": 12,
                },
                {
                    "QUOTA_ID": "quota-1", "ACCOUNT_ID": "account-1",
                    "REGISTRATION_NUMBER": "REG-1", "ACCOUNT_NAME": "Synthetic One",
                    "ADDRESS": "1 Test Road", "CITY": "Truro", "PROVINCE": "NS",
                    "POSTAL_CODE": "B2N 1A1", "PHONE": "555-0100", "FAX": None,
                    "PRODUCER_ROLE": True, "ISSUANCE": 12,
                },
                {
                    "QUOTA_ID": "quota-2", "ACCOUNT_ID": "account-1",
                    "REGISTRATION_NUMBER": "REG-2", "ACCOUNT_NAME": "Synthetic One",
                    "ADDRESS": "1 Test Road", "CITY": "Truro", "PROVINCE": "NS",
                    "POSTAL_CODE": "B2N 1A1", "PHONE": "555-0100", "FAX": None,
                    "PRODUCER_ROLE": True, "ISSUANCE": 8,
                },
            ]
        )


def test_quota_summary_forwards_parameters_and_avoids_join_duplication():
    repo = QuotaSummaryRepository()
    as_of = dt.date(2026, 9, 15)
    result, metrics = build_quota_summary(
        repo, user=user(), as_of_date=as_of, quota_type="Egg Production",
        account_id="account-1", status="Active",
    )
    assert repo.arguments == (as_of, "Egg Production", "account-1", "Active")
    assert len(result) == 2
    assert metrics == {"producer_count": 1, "total_issuance": 20}
    assert list(result.columns) == [
        "REGISTRATION_NUMBER", "ACCOUNT_NAME", "ADDRESS", "CITY", "PROVINCE",
        "POSTAL_CODE", "PHONE", "FAX", "ISSUANCE",
    ]


def test_quota_summary_empty_and_invalid_parameters():
    repo = QuotaSummaryRepository()
    repo.get_quota_summary = lambda *args, **kwargs: pd.DataFrame()
    result, metrics = build_quota_summary(
        repo, user=user(), as_of_date=dt.date.today(), quota_type="Egg Production"
    )
    assert result.empty
    assert metrics == {"producer_count": 0, "total_issuance": None}
    with pytest.raises(ValueError, match="As of Date"):
        build_quota_summary(repo, user=user(), as_of_date=None, quota_type="Egg Production")
    with pytest.raises(ValueError, match="Quota Type"):
        build_quota_summary(repo, user=user(), as_of_date=dt.date.today(), quota_type="Invented")


def test_mock_quota_summary_uses_deterministic_location_and_as_of_filters():
    repo = MockRepository(seed=42)
    quota = repo.get_quota_registrations(status="Active").iloc[0]
    account_id = quota["ACCOUNT_ID"]
    quota_type = quota["QUOTA_TYPE"]
    locations = repo.get_farm_locations(account_id=account_id)
    expected = locations.assign(
        _rank=locations["STATUS"].ne("Active").astype(int)
    ).sort_values(["_rank", "FARM_LOCATION_ID"]).iloc[0]
    result, _metrics = build_quota_summary(
        repo,
        user=user(),
        as_of_date=dt.date(2100, 1, 1),
        quota_type=quota_type,
        account_id=account_id,
    )
    assert not result.empty
    assert set(result["ADDRESS"]) == {expected["ADDRESS_1"]}
    before_effective, _ = build_quota_summary(
        repo,
        user=user(),
        as_of_date=dt.date(1900, 1, 1),
        quota_type=quota_type,
        account_id=account_id,
    )
    assert before_effective.empty


def test_snowflake_quota_summary_is_parameter_bound_and_has_one_location():
    repo = SnowflakeRepository.__new__(SnowflakeRepository)
    repo.database = "EFNS_DEV"; repo.schema_core = "CORE"
    captured = {}
    repo._query = lambda sql, params=None: captured.update(sql=sql, params=params) or pd.DataFrame()
    repo.get_quota_summary(dt.date(2026, 9, 15), "Egg Production", "account'1", "Active")
    assert "ROW_NUMBER() OVER" in captured["sql"]
    assert "fl.LOCATION_RANK = 1" in captured["sql"]
    assert "account'1" not in captured["sql"]
    assert captured["params"] == (
        "Egg Production", dt.date(2026, 9, 15), dt.date(2026, 9, 15), "account'1", "Active"
    )


class CustomRepository:
    def __init__(self):
        self.filters = None

    def get_accounts(self, **filters):
        self.filters = filters
        return pd.DataFrame(
            [
                {"ACCOUNT_ID": "a1", "ORGANIZATION_NAME": "Beta", "STATUS": "Active", "CITY": "Truro"},
                {"ACCOUNT_ID": "a2", "ORGANIZATION_NAME": "Alpha", "STATUS": "Active", "CITY": "Kentville"},
            ]
        )


def test_custom_builder_enforces_dataset_fields_filters_sort_and_column_order():
    repo = CustomRepository()
    result = build_custom_report(
        repo,
        user=user(),
        dataset="Accounts",
        selected_fields=["ORGANIZATION_NAME", "CITY"],
        filters={"statuses": ("Active",), "quota_type": "ignored"},
        sort_by="ORGANIZATION_NAME",
    )
    assert repo.filters == {"statuses": ("Active",)}
    assert list(result.columns) == ["Account Name", "City"]
    assert result["Account Name"].tolist() == ["Alpha", "Beta"]
    with pytest.raises(ValueError, match="Dataset"):
        build_custom_report(repo, user=user(), dataset="CORE.ACCOUNT", selected_fields=["ACCOUNT_ID"])
    with pytest.raises(ValueError, match="allowlisted"):
        build_custom_report(repo, user=user(), dataset="Accounts", selected_fields=["PASSWORD_HASH"])


def test_custom_builder_aggregation_and_export_match_visible_result():
    class ProductionRepository:
        def get_production_records(self, **_filters):
            return pd.DataFrame([
                {"PRODUCTION_ID": "p1", "REPORTING_YEAR": 2026, "TOTAL_RECEIVED": 4},
                {"PRODUCTION_ID": "p2", "REPORTING_YEAR": 2026, "TOTAL_RECEIVED": 6},
            ])

    result = build_custom_report(
        ProductionRepository(), user=user(), dataset="Production Records",
        selected_fields=["REPORTING_YEAR", "TOTAL_RECEIVED"],
        group_by=["REPORTING_YEAR"], aggregations={"TOTAL_RECEIVED": "sum"},
    )
    assert result.to_dict("records") == [{"Reporting Year": 2026, "Total Received": 10}]
    exported = pd.read_csv(BytesIO(report_csv(user(), result)))
    pd.testing.assert_frame_equal(exported, result)
    exported_xlsx = pd.read_excel(BytesIO(report_xlsx(user(), result)))
    pd.testing.assert_frame_equal(exported_xlsx, result)
    with pytest.raises(AuthorizationError):
        report_csv(user(active=False), result)


def test_execution_timestamp_is_explicitly_halifax():
    displayed = format_timestamp("2026-01-15T16:00:00+00:00")
    assert displayed == "2026-01-15 12:00 AST (America/Halifax)"


def test_report_page_uses_internal_navigation_and_no_external_links():
    source = Path("app/pages/4_Reports.py").read_text(encoding="utf-8")
    assert "st.switch_page" in source
    for forbidden in ("LinkColumn", "href=", "snowflake.app", "http://", "https://", "/Accounts"):
        assert forbidden not in source
    assert "st.session_state.report_center_open_report" in source
    assert "not stored in Snowflake" in source


def test_all_custom_datasets_use_named_repository_methods_and_allowlisted_fields():
    assert len(CUSTOM_DATASETS) == 10
    for method, identifier, fields in CUSTOM_DATASETS.values():
        assert method.startswith("get_")
        assert identifier in {field.source for field in fields}
        assert len({field.source for field in fields}) == len(fields)
        assert all(field.permission == Permission.VIEW_DATA for field in fields)
        assert all(field.export for field in fields)
