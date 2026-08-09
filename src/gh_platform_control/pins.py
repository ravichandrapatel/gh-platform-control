# FILE_NAME: pins.py
# DESCRIPTION: Reject floating git refs in config/pins.yaml
# VERSION: 0.1.1
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from gh_platform_control.util import fail

REF_KEY_RE = re.compile(r"^[\s]*(?:ref|tagging_ref):\s*(.+?)\s*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+([.-].*)?$")
MODULE_SEMVER_RE = re.compile(r"^[A-Za-z0-9._-]+/v[0-9]+\.[0-9]+\.[0-9]+([.-].*)?$")
FLOATING = frozenset({"main", "master", "HEAD", "latest"})
PLACEHOLDERS = frozenset(
    {"REPLACE_WITH_ACTIONS_COMMIT_SHA", "v0.0.0"}
)


def _is_placeholder(ref: str) -> bool:
    if ref in PLACEHOLDERS:
        return True
    if ref.endswith("/v0.0.0"):
        return True
    return False


def extract_refs(text: str) -> list[str]:
    refs: list[str] = []
    for line in text.splitlines():
        m = REF_KEY_RE.match(line)
        if not m:
            continue
        raw = m.group(1).strip().strip("\"'")
        if raw:
            refs.append(raw)
    return refs


def validate_pins(root: Path, *, allow_placeholders: bool = False) -> None:
    """INTENT: Reject floating / invalid refs in pins.yaml.
    INPUT: Control repo root; whether placeholders are allowed.
    OUTPUT: None (raises via fail on error).
    ROLE: Pin policy gate.
    SIDE_EFFECTS: Reads config/pins.yaml; may print WARN.
    """
    pins = root / "config" / "pins.yaml"
    if not pins.is_file():
        fail(f"missing {pins}")

    refs = extract_refs(pins.read_text(encoding="utf-8"))
    if not refs:
        fail("no ref keys found in pins.yaml")

    for ref in refs:
        if ref in FLOATING:
            fail(f"floating ref '{ref}' is forbidden")
        if _is_placeholder(ref):
            if allow_placeholders:
                print(f"WARN: placeholder ref '{ref}' allowed (ALLOW_PIN_PLACEHOLDERS=1)")
                continue
            fail(f"placeholder ref '{ref}' - set real pins before apply")
        if SHA_RE.fullmatch(ref):
            continue
        if SEMVER_RE.fullmatch(ref):
            continue
        if MODULE_SEMVER_RE.fullmatch(ref):
            continue
        fail(
            f"ref '{ref}' must be a 40-char SHA or SemVer tag "
            "(vX.Y.Z or module/vX.Y.Z)"
        )

    print("OK: pins.yaml refs accepted")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reject floating git refs in config/pins.yaml"
    )
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Allow placeholder refs (also via ALLOW_PIN_PLACEHOLDERS=1)",
    )
    args = parser.parse_args(argv)
    allow = (
        os.environ.get("ALLOW_PIN_PLACEHOLDERS", "0") == "1" or args.allow_placeholders
    )
    validate_pins(Path(args.root), allow_placeholders=allow)
    return 0


def main() -> int:
    return run()
