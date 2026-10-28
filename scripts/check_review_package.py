"""Verify the allowlisted shared source without querying any cloud service."""
from pathlib import Path
import hashlib,json,re,sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    manifest=json.loads((ROOT/'review/SUBMISSION_MANIFEST.json').read_text())
    missing=[];changed=[]
    for row in manifest:
        p=ROOT/row['path']
        if not p.is_file():missing.append(row['path'])
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:changed.append(row['path'])
    paths={r['path'] for r in manifest}
    extra=[]
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(ROOT).as_posix()
        if any(part in {'.git','.local','.venv','venv','__pycache__','.pytest_cache'} for part in p.relative_to(ROOT).parts):continue
        if rel not in paths and rel!='review/SUBMISSION_MANIFEST.json':extra.append(rel)
    result=dict(files=len(paths),missing=missing,changed=changed,unexpected=extra)
    print(json.dumps(result,indent=2))
    return int(bool(missing or changed or extra))

if __name__=='__main__':sys.exit(main())
