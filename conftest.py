"""
Pytest bootstrap for Calypso.

The engine uses flat imports (`import constants`, `from geo import ...`), and the
runtime entry point (flight_plan_maker.py) puts `src/` on sys.path so those resolve.
Tests need the same, independent of the directory pytest is launched from or whether
the package is installed. pytest auto-loads this file from the rootdir before it
collects any tests, so inserting src/ here makes every `src/` module importable in
the suite with zero per-test boilerplate.
"""

import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))