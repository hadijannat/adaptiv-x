"""Test configuration for repo-level tests."""

from __future__ import annotations

import sys
from pathlib import Path

LIBS_PATH = Path(__file__).resolve().parents[1] / "libs" / "aas_contract" / "src"
if str(LIBS_PATH) not in sys.path:
    sys.path.insert(0, str(LIBS_PATH))
