"""Generate deterministic, fictional EIMS migration packages for EFNS DEV."""

from __future__ import annotations

import argparse
import datetime as dt
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import sys
import zipfile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.migration import V2_MAPPING_PATH, analyze_migration_files, load_mapping


FIXED_GENERATION_TIME = "2026-09-15T00:00:00Z"


def identifier(code: str, number: int) -> str:
    return f"DEV_MIGRATION_{code}_{number:05d}"


def clean_frames() -> dict[str, pd.DataFrame]:
    accounts = [{
        "ACCOUNT_ID": identifier("A", i), "REGISTRATION_NUMBER": f"DM-A-{i:05d}",
        "ORGANIZATION_NAME": f"Fictional Migration Producer {i:03d}",
        "CITY": f"Synthetic City {(i-1)%10+1:02d}", "PROVINCE": "NS",
        "CONTACT_EMAIL": f"producer{i:03d}@example.invalid", "PRODUCER_ROLE": True,
        "STATUS": "Active",
    } for i in range(1, 51)]
    facilities = []
    farm_locations = []
    for i in range(1, 126):
        account_no = (i - 1) % 50 + 1
        farm_locations.append({
            "FARM_LOCATION_ID": identifier("L", i),
            "ACCOUNT_ID": identifier("A", account_no),
            "LOCATION_NAME": f"Synthetic Farm Location {i:03d}",
            "ADDRESS_1": f"{100 + i} Fictional Migration Road",
            "ADDRESS_2": "" if i % 4 == 0 else f"Synthetic Site {(i-1)%9+1}",
            "CITY": f"Synthetic City {(account_no-1)%10+1:02d}",
            "PROVINCE": "NS", "POSTAL_CODE": f"B0B 1A{i%10}",
            "PHONE": f"902-555-{i:04d}",
            "STATUS": "Inactive" if i % 10 == 0 else "Active",
        })
    for i in range(1, 101):
        account_no = (i - 1) // 2 + 1
        facilities.append({
            "FACILITY_ID": identifier("F", i), "ACCOUNT_ID": identifier("A", account_no),
            "FACILITY_NAME": f"Synthetic Facility {i:03d}", "FACILITY_TYPE": "Layer",
            "STATUS": "Active", "ACTIVATION_DATE": f"2020-{(i-1)%12+1:02d}-01",
        })
    details = []
    for i in range(1, 151):
        facility_no = (i - 1) % 100 + 1
        details.append({
            "FACILITY_DETAIL_ID": identifier("D", i), "FACILITY_ID": identifier("F", facility_no),
            "DETAIL_NAME": f"Synthetic Barn {i:03d}", "DETAIL_TYPE": "Barn",
            "STATUS": "Active", "COMMENTS": "Fully fictional migration fixture.",
        })
    quotas = []
    for i in range(1, 101):
        account_no = (i - 1) // 2 + 1
        quotas.append({
            "QUOTA_ID": identifier("Q", i), "REGISTRATION_NUMBER": f"DM-Q-{i:05d}",
            "ACCOUNT_ID": identifier("A", account_no), "QUOTA_NAME": f"Synthetic Quota {i:03d}",
            "QUOTA_TYPE": "Egg Production", "STATUS": "Active",
            "EFFECTIVE_DATE": "2024-01-01", "END_DATE": "",
            "COMMENTS": "Fictional quota fixture.",
        })
    flocks = []
    for i in range(1, 501):
        account_no = (i - 1) // 10 + 1
        facility_no = (account_no - 1) * 2 + ((i - 1) % 2) + 1
        available_details = [n for n in range(1, 151) if (n - 1) % 100 + 1 == facility_no]
        detail_no = available_details[(i - 1) % len(available_details)]
        quota_no = (account_no - 1) * 2 + ((i - 1) % 2) + 1
        flocks.append({
            "FLOCK_ID": identifier("FL", i), "FLOCK_NUMBER": f"DM-FLOCK-{i:05d}",
            "ACCOUNT_ID": identifier("A", account_no), "FACILITY_ID": identifier("F", facility_no),
            "FACILITY_DETAIL_ID": identifier("D", detail_no), "QUOTA_ID": identifier("Q", quota_no),
            "FLOCK_QUOTA_TYPE": "Egg Production", "STATUS": "Active",
            "PERMIT_NUMBER": f"DM-PERMIT-{i:05d}", "PERMIT_DATE": "2025-01-01",
            "HATCH_DATE": "2025-01-15", "DATE_ORDERED": "2024-12-01",
            "BIRD_COUNT": 1000 + i, "EGG_COLOUR": "Brown" if i % 2 else "White",
            "PLACEMENT_DATE": "2025-02-01", "EST_DISPOSAL": "2026-08-01",
            "DISPOSAL_DATE": "", "BIRDS_DISPOSED": 0,
            "COMMENTS": "Fictional flock fixture.",
        })
    flock_transactions = [{
        "FLOCK_TRANSACTION_ID": identifier("FT", i),
        "FLOCK_ID": identifier("FL", (i - 1) // 4 + 1),
        "TRANSACTION_TYPE": ("Count", "Delivery", "Removal", "Sale")[(i - 1) % 4],
        "QUANTITY": 100 + (i % 25), "TRANSACTION_DATE": f"2025-{(i-1)%12+1:02d}-{(i-1)%28+1:02d}",
        "NOTES": "Fictional transaction fixture.",
    } for i in range(1, 2001)]
    quota_transactions = [{
        "QUOTA_TRANSACTION_ID": identifier("QT", i),
        "TRANSACTION_TYPE": ("Purchase", "Sale", "Lease In")[(i - 1) % 3],
        "QUOTA_ID": identifier("Q", (i - 1) // 3 + 1),
        "EFFECTIVE_DATE": "2025-01-01", "END_DATE": "",
        "QUOTA_COUNT": 100 + i, "OWNER_ACCOUNT_ID": identifier("A", (i - 1) // 6 + 1),
        "RELATED_ACCOUNT_ID": identifier("A", (i % 50) + 1),
        "RELATED_QUOTA_ID": "", "RELATED_TRANSACTION_ID": "", "PRICE": "1,234.50",
        "QUOTA_LEASE_TYPE": "Fixed Term", "COMMENTS": "Fictional quota activity.",
    } for i in range(1, 301)]
    salmonella = [{
        "SALMONELLA_TEST_ID": identifier("S", i), "FLOCK_ID": identifier("FL", i),
        "ACCOUNT_ID": identifier("A", (i - 1) // 10 + 1), "PERMIT_NUMBER": f"DM-PERMIT-{i:05d}",
        "TESTING_DATE": "2025-06-01", "INSPECTOR": f"Synthetic Inspector {(i-1)%5+1}",
        "NUMBER_OF_SAMPLES": 5, "TEST_RESULT": "Negative", "DATE_RESULT_SENT": "2025-06-05",
        "DATE_RECEIVED": "2025-06-02", "CASE_FILE_NUMBER": f"DM-CASE-{i:05d}",
        "COMMENTS": "Fictional test fixture.",
    } for i in range(1, 251)]
    production = []
    for i in range(1, 5001):
        flock_no = (i - 1) // 10 + 1
        account_no = (flock_no - 1) // 10 + 1
        facility_no = (account_no - 1) * 2 + ((flock_no - 1) % 2) + 1
        production.append({
            "PRODUCTION_ID": identifier("P", i), "PRODUCER_ACCOUNT_ID": identifier("A", account_no),
            "GRADER_ACCOUNT_ID": identifier("A", 1), "FACILITY_ID": identifier("F", facility_no),
            "FLOCK_ID": identifier("FL", flock_no), "REPORTING_YEAR": 2025,
            "REPORTING_WEEK": (i - 1) % 52 + 1, "FLOCK_AGE": 20 + (i % 60),
            "TOTAL": 1000 + (i % 200), "TOTAL_RECEIVED": 1000 + (i % 200),
            "TOTAL_ACCEPTED": 990 + (i % 200), "SOURCE_TYPE": "EIMS_IMPORT",
            "MATCH_STATUS": "CONFIRMED", "SOURCE_ROW_NUMBER": i + 1,
        })
    return {
        "ACCOUNT": pd.DataFrame(accounts), "FARM_LOCATION": pd.DataFrame(farm_locations), "FACILITY": pd.DataFrame(facilities),
        "FACILITY_DETAIL": pd.DataFrame(details), "QUOTA_REGISTRATION": pd.DataFrame(quotas),
        "FLOCK": pd.DataFrame(flocks), "FLOCK_TRANSACTION": pd.DataFrame(flock_transactions),
        "QUOTA_TRANSACTION": pd.DataFrame(quota_transactions), "SALMONELLA_TEST": pd.DataFrame(salmonella),
        "PRODUCTION_RECORD": pd.DataFrame(production),
    }


def edge_frames() -> dict[str, pd.DataFrame]:
    frames = {name: frame.head(2).copy().astype(object) for name, frame in clean_frames().items()}
    accounts = frames["ACCOUNT"]
    accounts = pd.concat([accounts, pd.DataFrame([
        {**accounts.iloc[0].to_dict(), "ORGANIZATION_NAME": "Duplicate Source ID"},
        {"ACCOUNT_ID": identifier("A", 90001), "REGISTRATION_NUMBER": "DM-EDGE-REPEAT", "ORGANIZATION_NAME": "", "STATUS": "Unknown"},
        {"ACCOUNT_ID": identifier("A", 90002), "REGISTRATION_NUMBER": "DM-EDGE-REPEAT", "ORGANIZATION_NAME": "Repeated Key", "STATUS": "Active"},
    ])], ignore_index=True)
    frames["ACCOUNT"] = accounts
    locations = frames["FARM_LOCATION"]
    locations.loc[0, "ADDRESS_2"] = ""
    locations.loc[0, "PHONE"] = ""
    locations.loc[1, "STATUS"] = "Unknown"
    duplicate_location = locations.iloc[0].to_dict()
    orphan_location = locations.iloc[0].to_dict()
    orphan_location.update({"FARM_LOCATION_ID": identifier("L", 90001), "LOCATION_NAME": "Orphan Farm Location", "ACCOUNT_ID": identifier("A", 99999)})
    frames["FARM_LOCATION"] = pd.concat([locations, pd.DataFrame([duplicate_location, orphan_location])], ignore_index=True)
    frames["FACILITY"].loc[0, "ACTIVATION_DATE"] = "not-a-date"
    frames["FACILITY"].loc[1, "ACCOUNT_ID"] = identifier("A", 99999)
    frames["FACILITY_DETAIL"].loc[1, "FACILITY_ID"] = identifier("F", 99999)
    frames["QUOTA_REGISTRATION"].loc[0, "QUOTA_TYPE"] = "Unknown quota"
    frames["FLOCK"].loc[0, "BIRD_COUNT"] = "1,234"
    frames["FLOCK"].loc[0, "BIRDS_DISPOSED"] = "None"
    frames["FLOCK"].loc[0, "EST_DISPOSAL"] = ""
    frames["FLOCK"].loc[1, "BIRD_COUNT"] = "invalid-number"
    frames["FLOCK"].loc[1, "HATCH_DATE"] = "2025-99-99"
    extra_flock = frames["FLOCK"].iloc[0].to_dict()
    extra_flock.update({"FLOCK_ID": identifier("FL", 90001), "FLOCK_NUMBER": "DM-EDGE-NEGATIVE", "ACCOUNT_ID": identifier("A", 99999), "BIRD_COUNT": -5, "STATUS": "Unknown"})
    frames["FLOCK"] = pd.concat([frames["FLOCK"], pd.DataFrame([extra_flock])], ignore_index=True)
    frames["FLOCK_TRANSACTION"].loc[0, "FLOCK_ID"] = identifier("FL", 99999)
    frames["FLOCK_TRANSACTION"].loc[1, "QUANTITY"] = -1
    frames["QUOTA_TRANSACTION"].loc[0, "QUOTA_COUNT"] = "bad"
    frames["QUOTA_TRANSACTION"].loc[1, "TRANSACTION_TYPE"] = "Unknown"
    frames["SALMONELLA_TEST"].loc[0, "FLOCK_ID"] = identifier("FL", 99999)
    frames["SALMONELLA_TEST"].loc[1, "NUMBER_OF_SAMPLES"] = 0
    production = frames["PRODUCTION_RECORD"]
    production.loc[0, "FLOCK_AGE"] = "NaN"
    production.loc[0, "TOTAL"] = "1,234.50"
    production.loc[1, "FLOCK_AGE"] = "bad-age"
    production.loc[1, "FLOCK_ID"] = identifier("FL", 99999)
    extra = production.iloc[0].to_dict()
    extra.update({"PRODUCTION_ID": identifier("P", 90001), "FLOCK_AGE": "null", "TOTAL": "", "REPORTING_WEEK": 54})
    frames["PRODUCTION_RECORD"] = pd.concat([production, pd.DataFrame([extra])], ignore_index=True)
    return frames


def deterministic_xlsx(frame: pd.DataFrame, sheet_name: str) -> bytes:
    temporary = io.BytesIO()
    with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name=sheet_name, index=False)
        fixed = dt.datetime(2026, 9, 15, tzinfo=dt.timezone.utc)
        writer.book.properties.created = fixed
        writer.book.properties.modified = fixed
    source = zipfile.ZipFile(io.BytesIO(temporary.getvalue()), "r")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name in sorted(source.namelist()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = source.getinfo(name).external_attr
            content = source.read(name)
            if name == "docProps/core.xml":
                content = re.sub(
                    rb"<dcterms:(created|modified)[^>]*>.*?</dcterms:\1>",
                    rb"<dcterms:\1 xsi:type='dcterms:W3CDTF'>2026-09-15T00:00:00Z</dcterms:\1>",
                    content,
                )
            target.writestr(info, content)
    source.close()
    return output.getvalue()


def package_bytes(frames: dict[str, pd.DataFrame], mapping: dict) -> dict[str, bytes]:
    files = {}
    for entity in mapping["entity_order"]:
        spec = mapping["entities"][entity]
        filename = spec["filename"]
        if filename.endswith(".xlsx"):
            files[filename] = deterministic_xlsx(frames[entity], spec.get("worksheet", "production"))
        else:
            files[filename] = frames[entity].to_csv(index=False, lineterminator="\n").encode("utf-8")
    return files


def write_dataset(root: Path, name: str, frames: dict[str, pd.DataFrame], mapping: dict) -> dict:
    destination = root / name
    destination.mkdir(parents=True, exist_ok=True)
    files = package_bytes(frames, mapping)
    for filename, content in files.items():
        (destination / filename).write_bytes(content)
    uploaded = [type("GeneratedFile", (), {"name": filename, "getvalue": lambda self, value=content: value})() for filename, content in files.items()]
    analysis = analyze_migration_files(uploaded, mapping)
    return {
        "files": {filename: {"sha256": sha256(content).hexdigest(), "rows": len(frames[entity])} for entity in mapping["entity_order"] for filename, content in [(mapping["entities"][entity]["filename"], files[mapping["entities"][entity]["filename"]])]},
        "expected_reconciliation": analysis.reconciliation.to_dict("records"),
        "ready_rows": analysis.ready_count, "rejected_rows": analysis.rejected_count,
        "package_hash": analysis.package_hash,
    }


def generate(output: Path) -> dict:
    mapping = load_mapping(V2_MAPPING_PATH)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": mapping["schema_version"],
        "generation_time_utc": FIXED_GENERATION_TIME,
        "random_seed": 20260915,
        "synthetic_only": True,
        "datasets": {
            "clean": write_dataset(output, "clean", clean_frames(), mapping),
            "edge_cases": write_dataset(output, "edge_cases", edge_frames(), mapping),
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "sample_data" / "fake_eims_export")
    arguments = parser.parse_args()
    result = generate(arguments.output)
    print(json.dumps({name: {"ready": value["ready_rows"], "rejected": value["rejected_rows"]} for name, value in result["datasets"].items()}, indent=2))
