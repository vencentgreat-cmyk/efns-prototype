"""Create a synthetic local reviewer, never a Snowflake/company identity."""
from getpass import getpass
from pathlib import Path
import os
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.security import SQLiteAuthStore,UserSeed,Role,hash_password

def main():
    path=ROOT/'.local/reviewer_auth.db'
    if path.exists():
        raise SystemExit('Reviewer database already exists; preserving it. Use the previous local password.')
    password=getpass('Choose a local review-only password (not any company password): ')
    if len(password)<16:
        raise SystemExit('Choose at least 16 characters for this local review.')
    if password!=getpass('Repeat local password: '):
        raise SystemExit('Passwords differ; nothing created.')
    path.parent.mkdir(exist_ok=True)
    SQLiteAuthStore(path,seeds=[UserSeed('reviewer@nsegg.ca','Synthetic Offline Reviewer',Role.ADMIN,hash_password(password))])
    print('Synthetic local user reviewer@nsegg.ca created. Set EFNS_AUTH_DB to .local/reviewer_auth.db in the app shell.')
    print('First login requires the existing password-change step; no password is written to a source file.')

if __name__=='__main__':main()
