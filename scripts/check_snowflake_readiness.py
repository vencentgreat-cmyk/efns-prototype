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
    if "python=3.11" not in environment:
        errors.append("environment.yml must pin Python 3.11.")
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
