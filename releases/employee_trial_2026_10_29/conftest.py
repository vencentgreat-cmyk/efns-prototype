"""Review harness only: force isolated local defaults and fail on network I/O.

Production authentication is preserved unchanged. Tests may replace executors
with synthetic doubles and create their own local test users. No Snowflake credentials, SDK session, cloud service, or browser needed.
"""
import os
import sys
import time
from pathlib import Path

import pytest

for name in tuple(os.environ):
    if name.startswith('SNOWFLAKE_') or name in ('EFNS_AUTH_DB','EFNS_RUNTIME_MODE','REPOSITORY_MODE'):
        os.environ.pop(name,None)
os.environ['EFNS_RUNTIME_MODE']='local'
os.environ['REPOSITORY_MODE']='mock'
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
os.environ['PYTHON_DOTENV_DISABLED']='1'
os.environ['TZ']='America/Halifax'
if hasattr(time,'tzset'):
    time.tzset()
_local=Path(__file__).resolve().parent/'.local'
_local.mkdir(exist_ok=True)
os.environ['EFNS_AUTH_DB']=str(_local/'offline-default-auth.db')


def reject_network(event,args):
    if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):
        raise RuntimeError('Offline review forbids network access; use a synthetic executor/session.')


sys.addaudithook(reject_network)


def pytest_collection_modifyitems(items):
    for item in items:
        if item.name=='test_upgrade_and_fresh_schema_have_identical_manual_decision_columns':
            item.add_marker(pytest.mark.skip(reason='Company-specific fresh-install builder and dated GET_DDL evidence are not shared. Not a local runtime test.'))
