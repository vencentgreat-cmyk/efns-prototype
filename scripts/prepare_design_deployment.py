"""Back up the actual live DEV package and overlay only reviewed repair files."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import snowflake.connector
import yaml


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = (
    "data/migration_identity.py", "data/historical_corrections.py",
    "data/repositories/mock.py", "data/repositories/snowflake.py", "data/validation.py",
    "app/pages/17_Migration_Import.py", "app/pages/2_Production_Data.py",
    "app/navigation.py",
)
URI = "snow://streamlit/EFNS_DEV.APP.EFNS_INTERNAL_APP/versions/live/"


def main(output, snapshot_only=False):
    old, deploy = output / "old_app", output / "deploy_app"
    if old.exists() or deploy.exists():
        raise ValueError("Use a new output directory; never overwrite the rollback package.")
    old.mkdir(parents=True)
    connection = snowflake.connector.connect(connection_name="efns-dev", role="EFNS_DEV_DEPLOYER", warehouse="EFNS_DEV_WH", database="EFNS_DEV")
    cursor = connection.cursor()

    def query(sql):
        cursor.execute(sql)
        return [dict(zip([c[0] for c in cursor.description],row)) for row in cursor.fetchall()]

    try:
        cursor.execute("USE SECONDARY ROLES NONE")
        for key, sql in (("old_description", "DESCRIBE STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP"), ("old_grants", "SHOW GRANTS ON STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP"), ("old_manifest", f"LIST '{URI}'")):
            result = query(sql)
            (output / (key + ".json")).write_text(json.dumps(result,default=str,indent=2),encoding="utf-8")
            if key == "old_manifest":
                manifest = result
        for entry in manifest:
            relative = entry["name"].split("/versions/live/",1)[1]
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe live package path.")
            destination = old / path
            destination.parent.mkdir(parents=True,exist_ok=True)
            cursor.execute(f"GET '{URI+relative}' 'file://{destination.parent.resolve().as_posix()}/' OVERWRITE=TRUE")
            downloads = cursor.fetchall()
            if not destination.is_file() or not downloads:
                raise ValueError("Live file download did not complete.")
        final_manifest = query(f"LIST '{URI}'")
        if [(r["name"],r["md5"],r["size"]) for r in manifest] != [(r["name"],r["md5"],r["size"]) for r in final_manifest]:
            raise ValueError("Live package changed during backup.")
        # LIST metadata hashes differ from GET bytes for this Streamlit source
        # stage. Save both; never claim they are local content checksums.
        checksums = {str(p.relative_to(old)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in old.rglob('*') if p.is_file()}
        (output/"downloaded_sha256.json").write_text(json.dumps(checksums,indent=2),encoding="utf-8")
    finally:
        connection.close()
    if snapshot_only:
        print(json.dumps({"downloaded_files":len(manifest),"source":str(old)}))
        return
    shutil.copytree(old,deploy)
    scope = []
    for relative in OVERLAY:
        target = deploy / relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT / relative,target)
        previous = old / relative
        scope.append({"path":relative,"changed":not previous.exists() or previous.read_bytes()!=target.read_bytes()})
    project = yaml.safe_load((ROOT / "snowflake.yml").read_text(encoding="utf-8"))
    project["entities"]["efns_dev"].pop("grants",None)
    for directory in (old,deploy):
        (directory / "snowflake.yml").write_text(yaml.safe_dump(project,sort_keys=False),encoding="utf-8")
    (output/"package_scope.json").write_text(json.dumps(scope,indent=2),encoding="utf-8")
    print(json.dumps({"old_files":len(manifest),"overlaid":scope,"grants":"unchanged"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--snapshot-only",action="store_true")
    args=parser.parse_args()
    main(args.output,args.snapshot_only)
