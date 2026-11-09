"""Snowflake-compatible root entry point for the EFNS Streamlit application."""

from __future__ import annotations

import os
from pathlib import Path
import runpy


_previous_prefix = os.environ.get("EFNS_PAGE_PREFIX")
_previous_entrypoint = os.environ.get("EFNS_ENTRYPOINT")
try:
    os.environ["EFNS_PAGE_PREFIX"] = "app/pages"
    os.environ["EFNS_ENTRYPOINT"] = "streamlit_app.py"
    runpy.run_path(str(Path(__file__).parent / "app" / "Home.py"), run_name="__main__")
finally:
    if _previous_prefix is None:
        os.environ.pop("EFNS_PAGE_PREFIX", None)
    else:
        os.environ["EFNS_PAGE_PREFIX"] = _previous_prefix
    if _previous_entrypoint is None:
        os.environ.pop("EFNS_ENTRYPOINT", None)
    else:
        os.environ["EFNS_ENTRYPOINT"] = _previous_entrypoint
