"""Offline structural checks for the EFNS Snowflake deployment bundle."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (ROOT / "streamlit_app.py", ROOT / "app", ROOT / "data")


def runtime_python_files():
    for item in RUNTIME_ROOTS:
        if item.is_file():
            yield item
        else:
            yield from item.rglob("*.py")


def check() -> list[str]:
    errors: list[str] = []
    required = ("snowflake.yml", "environment.yml", "streamlit_app.py")
    for name in required:
        if not (ROOT / name).is_file():
            errors.append(f"Missing required deployment file: {name}")

    environment = (ROOT / "environment.yml").read_text(encoding="utf-8")
    if re.search(r"(?mi)^\s*-\s*python\s*(?:[=<>!~].*)?$", environment):
        errors.append(
            "environment.yml must let the Snowflake warehouse runtime provide Python."
        )
    if "streamlit=1.52.2" not in environment:
        errors.append("environment.yml must pin the reviewed warehouse Streamlit version.")

    project = (ROOT / "snowflake.yml").read_text(encoding="utf-8")
    if "main_file: streamlit_app.py" not in project:
        errors.append("snowflake.yml must use the root streamlit_app.py entry point.")
    if "runtime_name: SYSTEM$WAREHOUSE_RUNTIME" not in project:
        errors.append("snowflake.yml must explicitly select the warehouse runtime.")
    for forbidden in ("ROOT_LOCATION", ".env", ".local", "tests/", "secrets.toml"):
        if forbidden in project:
            errors.append(f"snowflake.yml must not deploy {forbidden}.")

    post_deploy_path = ROOT / "sql" / "08_post_deploy_grants.sql"
    if not post_deploy_path.is_file():
        errors.append("Missing required post-deployment SQL: sql/08_post_deploy_grants.sql")
    else:
        post_deploy = " ".join(
            post_deploy_path.read_text(encoding="utf-8").upper().split()
        )
        deployer_role = "USE ROLE EFNS_DEV_DEPLOYER;"
        runtime_alter = (
            "ALTER STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP "
            "SET RUNTIME_NAME = 'SYSTEM$WAREHOUSE_RUNTIME';"
        )
        security_role = "USE ROLE SECURITYADMIN;"
        if runtime_alter not in post_deploy:
            errors.append(
                "Post-deployment SQL must explicitly enforce SYSTEM$WAREHOUSE_RUNTIME."
            )
        elif not (
            0 <= post_deploy.find(deployer_role)
            < post_deploy.find(runtime_alter)
            < post_deploy.find(security_role)
        ):
            errors.append(
                "Post-deployment runtime enforcement must run as EFNS_DEV_DEPLOYER "
                "before viewer grants."
            )

    foundation = (ROOT / "sql" / "00_dev_foundation.sql").read_text(encoding="utf-8")
    if "WITH CREDIT_QUOTA = 10" not in foundation:
        errors.append("The EFNS DEV resource monitor must use the reviewed 10-credit quota.")

    grants = (ROOT / "sql" / "06_least_privilege_grants.sql").read_text(encoding="utf-8")
    normalized_grants = " ".join(grants.upper().split())
    broad_runtime_grants = re.findall(
        r"GRANT\s+[^;]+?\s+ON\s+(?:ALL|FUTURE)\s+(?:TABLES|VIEWS|SCHEMAS)\s+IN\s+DATABASE\s+EFNS_DEV",
        normalized_grants,
    )
    if broad_runtime_grants:
        errors.append("Runtime role must not receive database-wide current or future object grants.")
    audit_grants = re.findall(
        r"GRANT\s+([^;]+?)\s+ON\s+TABLE\s+EFNS_DEV\.APP\.AUDIT_EVENT\s+TO\s+ROLE\s+EFNS_DEV_APP_OWNER;",
        normalized_grants,
    )
    audit_privileges = {
        privilege.strip()
        for grant in audit_grants
        for privilege in grant.split(",")
    }
    if audit_privileges != {"SELECT", "INSERT"}:
        errors.append("APP.AUDIT_EVENT must grant only SELECT and INSERT to the app owner.")

    utc_ntz = "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ"
    for ddl_name in ("02_core_tables.sql", "03_production_tables.sql"):
        ddl = (ROOT / "sql" / ddl_name).read_text(encoding="utf-8")
        if "DEFAULT CURRENT_TIMESTAMP()" in ddl:
            errors.append(f"{ddl_name} contains a session-timezone timestamp default.")
        timestamp_defaults = re.findall(
            r"\b(?:CREATED_AT|UPDATED_AT|UPLOAD_TIMESTAMP)\s+TIMESTAMP_NTZ\s+DEFAULT\s+([^\n]+)",
            ddl,
            flags=re.IGNORECASE,
        )
        if not timestamp_defaults or any(utc_ntz not in value.upper() for value in timestamp_defaults):
            errors.append(f"{ddl_name} must generate persisted TIMESTAMP_NTZ values in UTC.")

    repository = (ROOT / "data" / "repositories" / "snowflake.py").read_text(encoding="utf-8")
    if f'UTC_NOW_NTZ = "{utc_ntz}"' not in repository:
        errors.append("SnowflakeRepository must use the reviewed server-side UTC expression.")
    if "DATE_FIELDS" not in repository or "normalize_date_bind" not in repository:
        errors.append("SnowflakeRepository must normalize typed DATE bind values at its boundary.")

    synthetic_seed = (ROOT / "sql" / "09_dev_synthetic_seed.sql").read_text(encoding="utf-8")
    if "TO_TIMESTAMP_NTZ('2026-01-01 00:00:00')" in synthetic_seed:
        errors.append("The DEV synthetic seed must not use a fixed creation timestamp.")
    if utc_ntz not in synthetic_seed:
        errors.append("The DEV synthetic seed must assign timestamps from Snowflake UTC time.")

    navigation = (ROOT / "app" / "navigation.py").read_text(encoding="utf-8")
    if 'DISPLAY_TIMEZONE = "America/Halifax"' not in navigation:
        errors.append("The UI must explicitly display persisted timestamps in America/Halifax.")

    for path in runtime_python_files():
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 11))
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f"Python 3.11 parse failed for {path.relative_to(ROOT)}: {exc}")
    return errors


if __name__ == "__main__":
    failures = check()
    if failures:
        print("Snowflake readiness checks failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("Snowflake readiness checks passed.")
