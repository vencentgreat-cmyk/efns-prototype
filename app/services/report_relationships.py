"""Read-only report lookups with explicit ownership and stable row grains."""

import pandas as pd


def _parent_lookup(frame, parent, key, columns):
    # Null child keys must not match null parent keys; duplicate parent IDs fail
    # instead of multiplying a report's quantities.
    fields = [key, *[field for field in columns if field in parent.columns]]
    return frame.astype({key: object}).merge(parent.loc[parent[key].notna(), fields].astype({key: object}), on=key,
                       how="left", validate="many_to_one")


def report_relationships(repo, frame: pd.DataFrame, entity: str) -> pd.DataFrame:
    """Add display-only relationship roles, never substitute the business owner."""
    result = frame.copy()
    accounts = repo.get_accounts()[["ACCOUNT_ID", "ORGANIZATION_NAME"]]
    if entity == "FLOCK":
        result["FLOCK_ACCOUNT_ID"] = result["ACCOUNT_ID"]
        result["REPORT_FACILITY_ID"] = result["FACILITY_ID"]
    elif entity in {"FLOCK_TRANSACTION", "PRODUCTION_RECORD", "SALMONELLA_TEST"}:
        if "FLOCK_ID" not in result:
            result["FLOCK_ID"] = None
        fields = ["FLOCK_ID", "FLOCK_NUMBER", "ACCOUNT_ID", "FACILITY_ID", "STATUS",
                  "BIRD_COUNT", "HATCH_DATE", "PLACEMENT_DATE", "EST_DISPOSAL",
                  "DISPOSAL_DATE", "DISPOSAL_METHOD", "EGG_COLOUR", "QUOTA_ID"]
        flocks = repo.get_flocks()
        flocks = flocks[[field for field in fields if field in flocks.columns]].rename(columns={
            "ACCOUNT_ID": "FLOCK_ACCOUNT_ID", "FACILITY_ID": "FLOCK_FACILITY_ID",
            "STATUS": "STATUS_FLOCK", "EGG_COLOUR": "EGG_COLOUR_FLOCK",
        })
        result = _parent_lookup(result, flocks, "FLOCK_ID", flocks.columns.drop("FLOCK_ID"))
        result["REPORT_FACILITY_ID"] = result["FLOCK_FACILITY_ID"]
        if entity == "PRODUCTION_RECORD":
            if "FACILITY_ID" not in result:
                result["FACILITY_ID"] = None
            result["REPORT_FACILITY_ID"] = result["FACILITY_ID"].combine_first(result["FLOCK_FACILITY_ID"])
            direct = result["FACILITY_ID"].notna()
            linked = result["FLOCK_FACILITY_ID"].notna()
            result["REPORT_FACILITY_SOURCE"] = "No available reference"
            result.loc[linked, "REPORT_FACILITY_SOURCE"] = "Linked Flock"
            result.loc[direct, "REPORT_FACILITY_SOURCE"] = "Production record"
            result["FACILITY_REFERENCE_DIFFERENCE"] = "Not comparable"
            comparable = direct & linked
            result.loc[comparable, "FACILITY_REFERENCE_DIFFERENCE"] = "Same reference"
            different = comparable & result["FACILITY_ID"].astype("string").str.casefold().ne(
                result["FLOCK_FACILITY_ID"].astype("string").str.casefold())
            result.loc[different, "FACILITY_REFERENCE_DIFFERENCE"] = "Different references - review"
    elif entity == "FACILITY":
        result["FACILITY_ACCOUNT_ID"] = result["ACCOUNT_ID"]

    if entity != "FACILITY":
        facilities = repo.get_facilities().rename(columns={
            "FACILITY_ID": "REPORT_FACILITY_ID", "ACCOUNT_ID": "FACILITY_ACCOUNT_ID",
            "STATUS": "STATUS_FAC",
        })
        fields = ["FACILITY_ACCOUNT_ID", "FACILITY_NAME", "FACILITY_TYPE", "STATUS_FAC",
                  "ACTIVATION_DATE", "CLOSURE_DATE"]
        result = _parent_lookup(result, facilities, "REPORT_FACILITY_ID", fields)
        result["FACILITY_NAME"] = result["FACILITY_NAME"].fillna("Unassigned")

    for role in ("FLOCK", "FACILITY", "PRODUCER"):
        key = f"{role}_ACCOUNT_ID"
        if key in result:
            parent = accounts.rename(columns={"ACCOUNT_ID": key, "ORGANIZATION_NAME": f"{role}_ACCOUNT_NAME"})
            result = _parent_lookup(result, parent, key, [f"{role}_ACCOUNT_NAME"])
    return result
