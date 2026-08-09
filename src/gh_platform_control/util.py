# FILE_NAME: util.py
# DESCRIPTION: Shared helpers for gh-platform-control CLI modules.
# VERSION: 0.1.0
from __future__ import annotations

import sys


def fail(msg: str) -> None:
    """INTENT: Print ERROR and exit non-zero.
    INPUT: Human-readable failure message.
    OUTPUT: Never returns (raises SystemExit(1)).
    ROLE: Shared fail-closed helper.
    SIDE_EFFECTS: Writes to stderr; terminates process.
    """
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)
