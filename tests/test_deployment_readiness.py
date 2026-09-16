"""Structural deployment checks that require no Snowflake account."""

from scripts.check_snowflake_readiness import check
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_snowflake_deployment_bundle_is_python_311_compatible():
    assert check() == []


def test_app_owner_grants_match_repository_access_and_keep_audit_append_only():
    grants = (ROOT / "sql" / "06_least_privilege_grants.sql").read_text(encoding="utf-8").upper()

    assert not re.search(
        r"GRANT\s+[^;]+?\s+ON\s+(?:ALL|FUTURE)\s+(?:TABLES|VIEWS|SCHEMAS)\s+IN\s+DATABASE",
        grants,
    )

    operational_tables = (
        "ACCOUNT",
        "FARM_LOCATION",
        "FACILITY",
        "FACILITY_DETAIL",
        "FLOCK",
        "FLOCK_TRANSACTION",
        "QUOTA_REGISTRATION",
        "QUOTA_TRANSACTION",
        "SALMONELLA_TEST",
    )
    for table in operational_tables:
        assert (
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE EFNS_DEV.CORE.{table} "
            "TO ROLE EFNS_DEV_APP_OWNER;"
        ) in grants

    required_limited_grants = (
        "GRANT SELECT ON TABLE EFNS_DEV.CORE.SALMONELLA_TEST_SAMPLE TO ROLE EFNS_DEV_APP_OWNER;",
        "GRANT SELECT, INSERT ON TABLE EFNS_DEV.CORE.PRODUCTION_RECORD TO ROLE EFNS_DEV_APP_OWNER;",
        "GRANT SELECT, INSERT, UPDATE ON TABLE EFNS_DEV.RAW.IMPORT_BATCH TO ROLE EFNS_DEV_APP_OWNER;",
        "GRANT SELECT, INSERT ON TABLE EFNS_DEV.RAW.IMPORT_RAW_ROW TO ROLE EFNS_DEV_APP_OWNER;",
        "GRANT SELECT ON VIEW EFNS_DEV.REPORTING.VW_PRODUCTION_SUMMARY TO ROLE EFNS_DEV_APP_OWNER;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE EFNS_DEV.SECURITY.APP_USER TO ROLE EFNS_DEV_APP_OWNER;",
    )
    for statement in required_limited_grants:
        assert statement in grants

    assert (
        "GRANT SELECT, INSERT ON TABLE EFNS_DEV.APP.AUDIT_EVENT "
        "TO ROLE EFNS_DEV_APP_OWNER;"
    ) in grants
    audit_grants = re.findall(
        r"GRANT\s+([^;]+?)\s+ON\s+TABLE\s+EFNS_DEV\.APP\.AUDIT_EVENT\s+TO\s+ROLE\s+EFNS_DEV_APP_OWNER;",
        grants,
    )
    assert {
        privilege.strip()
        for grant in audit_grants
        for privilege in grant.split(",")
    } == {"SELECT", "INSERT"}
    assert (
        "REVOKE UPDATE, DELETE ON TABLE EFNS_DEV.APP.AUDIT_EVENT "
        "FROM ROLE EFNS_DEV_APP_OWNER;"
    ) in grants


def test_ordinary_account_roles_receive_no_data_object_privileges():
    grants = (ROOT / "sql" / "08_post_deploy_grants.sql").read_text(encoding="utf-8").upper()
    assert not re.search(
        r"GRANT\s+[^;]*(?:SELECT|INSERT|UPDATE|DELETE)[^;]*\s+ON\s+(?:TABLE|VIEW)",
        grants,
    )


def test_runtime_and_monitor_are_explicitly_bounded():
    project = (ROOT / "snowflake.yml").read_text(encoding="utf-8")
    environment = (ROOT / "environment.yml").read_text(encoding="utf-8")
    foundation = (ROOT / "sql" / "00_dev_foundation.sql").read_text(encoding="utf-8")
    post_deploy = " ".join(
        (ROOT / "sql" / "08_post_deploy_grants.sql")
        .read_text(encoding="utf-8")
        .upper()
        .split()
    )

    assert "runtime_name: SYSTEM$WAREHOUSE_RUNTIME" in project
    assert not re.search(r"(?mi)^\s*-\s*python\s*(?:[=<>!~].*)?$", environment)
    assert "streamlit=1.52.2" in environment
    for dependency in (
        "pandas=2.*",
        "numpy=2.*",
        "snowflake-snowpark-python",
        "openpyxl",
    ):
        assert dependency in environment

    deployer_role = "USE ROLE EFNS_DEV_DEPLOYER;"
    runtime_alter = (
        "ALTER STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP "
        "SET RUNTIME_NAME = 'SYSTEM$WAREHOUSE_RUNTIME';"
    )
    security_role = "USE ROLE SECURITYADMIN;"
    assert 0 <= post_deploy.find(deployer_role) < post_deploy.find(runtime_alter)
    assert post_deploy.find(runtime_alter) < post_deploy.find(security_role)

    assert "WITH CREDIT_QUOTA = 10" in foundation
    assert "ALTER RESOURCE MONITOR EFNS_DEV_MONTHLY_MONITOR SET CREDIT_QUOTA = 10" in foundation
    assert "ON 75 PERCENT DO NOTIFY" in foundation
    assert "ON 100 PERCENT DO SUSPEND" in foundation
