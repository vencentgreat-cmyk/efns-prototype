# ============================================================
# EFNS Prototype v0.1 — Synthetic Data Generator
# ============================================================
"""
Generates realistic *fake* data for the prototype.

IMPORTANT: This contains NO real EFNS producer information.
All names, numbers, and records are fabricated for demonstration only.

The generator is deterministic (seeded) so results are reproducible.
"""

from __future__ import annotations

import datetime as dt
import random
import uuid
from typing import Optional

import pandas as pd

# ----------------------------------------------------------------------
# Fabricated name pools (clearly synthetic)
# ----------------------------------------------------------------------
_ORG_PREFIXES = [
    "Maple", "Highland", "Sunnybrook", "Riverside", "Cobequid", "Annapolis",
    "Bras d'Or", "Northumberland", "Fundy", "LaHave", "Wentworth", "Musquodoboit",
    "Kings", "Colchester", "Pictou", "Antigonish", "Lunenburg", "Queens",
    "Shelburne", "Digby", "Hants", "Cumberland", "Richmond", "Inverness",
]

_ORG_SUFFIXES = [
    "Egg Farm", "Poultry Ltd.", "Eggs Inc.", "Family Farm", "Producers Co-op",
    "Poultry Farm", "Layer Farm", "Hatchery", "Eggs Ltd.", "Farm Ltd.",
]

_CITIES = [
    ("Truro", "NS", "B2N"), ("Kentville", "NS", "B4N"), ("Sydney", "NS", "B1P"),
    ("Yarmouth", "NS", "B5A"), ("New Glasgow", "NS", "B2H"), ("Bridgewater", "NS", "B4V"),
    ("Amherst", "NS", "B4H"), ("Antigonish", "NS", "B2G"), ("Windsor", "NS", "B0N"),
    ("Wolfville", "NS", "B4P"), ("Digby", "NS", "B0V"), ("Port Hawkesbury", "NS", "B9A"),
]

_FIRST_NAMES = [
    "Alex", "Jordan", "Casey", "Morgan", "Taylor", "Sara", "Chris", "Pat",
    "Dana", "Robin", "Jamie", "Lee", "Sam", "Drew", "Kim", "Terry",
]

_LAST_NAMES = [
    "MacDonald", "Fraser", "Cameron", "MacLeod", "Grant", "Ross", "Murray",
    "Sinclair", "Ferguson", "Campbell", "Stewart", "MacKenzie", "Gordon", "Blair",
]

_FACILITY_TYPES = ["Pullet", "Layer", "Other"]
_EGG_COLOURS = ["White", "Brown", "Mostly White", "Mostly Brown"]
_DISPOSAL_METHODS = ["Cull", "Render", "Sold Live", "Compost", "Natural"]
_SIZE_BANDS = ["Jumbo", "Extra Large", "Large", "Medium", "Small", "PeeWee"]
_TRANSACTION_TYPES = ["Count", "Delivery", "Removal", "Sale"]


def _make_id(rng: random.Random) -> str:
    """Generate a deterministic unique ID from the seedable RNG."""
    hex_str = f"{rng.randint(0, 2**128 - 1):032x}"
    return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"


def generate_accounts(n: int = 12, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        org = f"{rng.choice(_ORG_PREFIXES)} {rng.choice(_ORG_SUFFIXES)}"
        city, prov, postal_prefix = rng.choice(_CITIES)
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        # Ensure roles are plausible: most are producers; some have extra roles
        is_producer = rng.random() < 0.9
        is_breeder = rng.random() < 0.25
        is_hatchery = rng.random() < 0.20
        is_grader = rng.random() < 0.30
        rows.append(
            {
                "ACCOUNT_ID": _make_id(rng),
                "REGISTRATION_NUMBER": f"NS-{1000 + i}",
                "ORGANIZATION_NAME": org,
                "ADDRESS_LINE1": f"{rng.randint(1, 999)} {rng.choice(['Main St', 'Rural Route', 'Highway', 'Farm Rd', 'Church St'])}",
                "ADDRESS_LINE2": rng.choice(["", "", "Unit A", "Site 2"]),
                "CITY": city,
                "PROVINCE": prov,
                "POSTAL_CODE": f"{postal_prefix} {rng.randint(0, 9)}{rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{rng.randint(0, 9)}",
                "CONTACT_NAME": f"{first} {last}",
                "CONTACT_PHONE": f"(902) {rng.randint(200, 999)}-{rng.randint(1000, 9999)}",
                "CONTACT_EMAIL": f"{first.lower()}.{last.lower()}@example-farm.ca",
                "LICENCE_NUMBER": f"LIC-{rng.randint(10000, 99999)}",
                "PRODUCER_ROLE": is_producer,
                "BREEDER_ROLE": is_breeder,
                "HATCHERY_ROLE": is_hatchery,
                "GRADER_ROLE": is_grader,
                "STATUS": "Active" if rng.random() < 0.85 else "Inactive",
            }
        )
    df = pd.DataFrame(rows)
    now = dt.datetime.now()
    df["CREATED_AT"] = now
    df["UPDATED_AT"] = now
    return df


def generate_facilities(accounts: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed + 1)
    rows = []
    for _, acc in accounts.iterrows():
        n_fac = rng.randint(1, 3)
        for j in range(n_fac):
            ftype = rng.choice(_FACILITY_TYPES)
            activation = dt.date.today() - dt.timedelta(days=rng.randint(400, 4000))
            status = rng.choice(["Active", "Active", "Active", "Inactive", "Closed"])
            closure = (
                dt.date.today() - dt.timedelta(days=rng.randint(10, 300))
                if status in ("Inactive", "Closed")
                else None
            )
            rows.append(
                {
                    "FACILITY_ID": _make_id(rng),
                    "ACCOUNT_ID": acc["ACCOUNT_ID"],
                    "FACILITY_NAME": f"{acc['ORGANIZATION_NAME'].split()[0]} {ftype} Barn {j + 1}",
                    "FACILITY_TYPE": ftype,
                    "STATUS": status,
                    "ACTIVATION_DATE": activation,
                    "CONSTRUCTION_DATE": activation - dt.timedelta(days=rng.randint(60, 400)),
                    "CLOSURE_DATE": closure,
                    "DESTRUCTION_DATE": None,
                    "INACTIVE_DATE": closure,
                }
            )
    df = pd.DataFrame(rows)
    now = dt.datetime.now()
    df["CREATED_AT"] = now
    df["UPDATED_AT"] = now
    return df


def generate_flocks(
    accounts: pd.DataFrame, facilities: pd.DataFrame, seed: int = 42
) -> pd.DataFrame:
    rng = random.Random(seed + 2)
    rows = []
    flock_counter = 1
    for _, acc in accounts.iterrows():
        acc_facilities = facilities[facilities["ACCOUNT_ID"] == acc["ACCOUNT_ID"]]
        n_flocks = rng.randint(1, 3)
        for _ in range(n_flocks):
            fac_row = acc_facilities.sample(n=1, random_state=rng.randint(0, 10**6)).iloc[0] \
                if len(acc_facilities) else None
            hatch = dt.date.today() - dt.timedelta(days=rng.randint(30, 900))
            placement = hatch + dt.timedelta(days=rng.randint(1, 21))
            bird_count = rng.randint(4000, 25000)
            est_completion = placement + dt.timedelta(days=rng.randint(400, 560))
            status = rng.choice(["Active", "Active", "Active", "Depopulated", "Planned"])
            rows.append(
                {
                    "FLOCK_ID": _make_id(rng),
                    "ACCOUNT_ID": acc["ACCOUNT_ID"],
                    "FACILITY_ID": fac_row["FACILITY_ID"] if fac_row is not None else None,
                    "FLOCK_NUMBER": f"F-{flock_counter:04d}",
                    "LICENCE_NUMBER": acc["LICENCE_NUMBER"],
                    "BIRD_COUNT": bird_count,
                    "PLACEMENT_DATE": placement,
                    "HATCH_DATE": hatch,
                    "EGG_COLOUR": rng.choice(_EGG_COLOURS),
                    "EST_PROD_COMPLETION": est_completion,
                    "EST_DISPOSAL": est_completion + dt.timedelta(days=rng.randint(0, 30)),
                    "ACTUAL_DISPOSAL": (
                        est_completion + dt.timedelta(days=rng.randint(-5, 40))
                        if status == "Depopulated"
                        else None
                    ),
                    "DISPOSAL_METHOD": rng.choice(_DISPOSAL_METHODS) if status == "Depopulated" else None,
                    "STATUS": status,
                }
            )
            flock_counter += 1
    df = pd.DataFrame(rows)
    now = dt.datetime.now()
    df["CREATED_AT"] = now
    df["UPDATED_AT"] = now
    return df


def generate_flock_transactions(flocks: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed + 3)
    rows = []
    for _, fl in flocks.iterrows():
        n_tx = rng.randint(0, 5)
        base_date = fl["PLACEMENT_DATE"]
        if base_date is None or pd.isna(base_date):
            base_date = dt.date.today()
        for _ in range(n_tx):
            rows.append(
                {
                    "FLOCK_TRANSACTION_ID": _make_id(rng),
                    "FLOCK_ID": fl["FLOCK_ID"],
                    "TRANSACTION_TYPE": rng.choice(_TRANSACTION_TYPES),
                    "QUANTITY": rng.randint(50, 2000),
                    "TRANSACTION_DATE": base_date + dt.timedelta(days=rng.randint(1, 400)),
                    "NOTES": rng.choice(["", "", "Routine", "Weekly count", "Partial removal"]),
                }
            )
    df = pd.DataFrame(rows)
    df["CREATED_AT"] = dt.datetime.now()
    return df


def generate_production(
    n: int = 200, seed: int = 42, reporting_year: Optional[int] = None,
    flocks: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Generate normalized production records (as they would appear in CORE).

    If `flocks` is provided, each production row is provisionally linked to a
    random flock via FLOCK_ID. This link is PROVISIONAL/FAKE and exists only so
    the mixed-area report prototype is demonstrable; it will be replaced once
    the real Dataverse relationship is known.
    """
    rng = random.Random(seed + 4)
    year = reporting_year or dt.date.today().year
    flock_ids = None
    if flocks is not None and not flocks.empty and "FLOCK_ID" in flocks.columns:
        flock_ids = flocks["FLOCK_ID"].tolist()
    rows = []
    for _ in range(n):
        week = rng.randint(1, 52)
        net_weight = round(rng.uniform(800, 4000), 2)
        net_boxes = round(rng.uniform(40, 220), 2)
        net_per_box = round(net_weight / net_boxes, 2) if net_boxes else 0.0
        total_received = net_boxes
        # Decide whether this row has separated rejected/loss or a legacy combined value
        legacy = rng.random() < 0.35
        if legacy:
            rejected = None
            loss = None
            legacy_total = round(rng.uniform(0.5, 6.0), 2)
            total_accepted = round(total_received - legacy_total, 2)
        else:
            rejected = round(rng.uniform(0.0, 4.0), 2)
            loss = round(rng.uniform(0.0, 3.0), 2)
            legacy_total = None
            total_accepted = round(total_received - rejected - loss, 2)
        rows.append(
            {
                "PRODUCTION_ID": _make_id(rng),
                "IMPORT_ID": None,  # filled by repository
                "FLOCK_ID": rng.choice(flock_ids) if flock_ids else None,  # PROVISIONAL
                "GRADER_NUMBER": f"G-{rng.randint(100, 130)}",
                "BARN_IDENTITY": f"Barn-{rng.choice('ABCDEFGH')}{rng.randint(1, 6)}",
                "FLOCK_AGE": rng.randint(18, 90),
                "EGG_COLOUR": rng.choice(_EGG_COLOURS),
                "NET_WEIGHT": net_weight,
                "NET_BOXES": net_boxes,
                "NET_PER_BOX": net_per_box,
                "TOTAL_RECEIVED": total_received,
                "REJECTED": rejected,
                "LOSS": loss,
                "LEGACY_REJECT_LOSS_TOTAL": legacy_total,
                "TOTAL_ACCEPTED": total_accepted,
                "REPORTING_YEAR": year,
                "REPORTING_WEEK": week,
            }
        )
    df = pd.DataFrame(rows)
    df["CREATED_AT"] = dt.datetime.now()
    return df


def generate_size_breakdown(production: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed + 5)
    rows = []
    for _, pr in production.iterrows():
        base = pr["TOTAL_ACCEPTED"] if pr["TOTAL_ACCEPTED"] else 100
        # distribute across size bands using a rough normal-ish weighting
        weights = {band: rng.uniform(0.02, 0.30) for band in _SIZE_BANDS}
        total_w = sum(weights.values())
        for band, w in weights.items():
            if rng.random() < 0.25:
                continue  # some bands may be absent
            rows.append(
                {
                    "SIZE_BREAKDOWN_ID": _make_id(rng),
                    "PRODUCTION_ID": pr["PRODUCTION_ID"],
                    "SIZE_BAND": band,
                    "QUANTITY": round(base * (w / total_w), 2),
                }
            )
    return pd.DataFrame(rows)


def generate_all(seed: int = 42) -> dict:
    """Generate a complete consistent synthetic dataset."""
    accounts = generate_accounts(seed=seed)
    facilities = generate_facilities(accounts, seed=seed)
    flocks = generate_flocks(accounts, facilities, seed=seed)
    transactions = generate_flock_transactions(flocks, seed=seed)
    production = generate_production(seed=seed, flocks=flocks)
    sizes = generate_size_breakdown(production, seed=seed)
    return {
        "accounts": accounts,
        "facilities": facilities,
        "flocks": flocks,
        "flock_transactions": transactions,
        "production": production,
        "size_breakdown": sizes,
    }