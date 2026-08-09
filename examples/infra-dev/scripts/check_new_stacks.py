#!/usr/bin/env python3
# FILE_NAME: check_new_stacks.py
# DESCRIPTION: Fail PRs that add new stacks/* dirs unless the branch is issueops/*.
# VERSION: 0.2.0
# No owner/admin escape hatch — new stacks only via control IssueOps App PRs.
from __future__ import annotations

import argparse
import subprocess
import sys


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def list_stack_dirs(ref: str) -> set[str]:
    """Return one-level stack names under stacks/ at ref (empty if stacks missing)."""
    proc = subprocess.run(
        ["git", "ls-tree", "-d", "--name-only", f"{ref}:stacks"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return set()
    return {ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref",
        required=True,
        help="Git ref for PR base (e.g. origin/main)",
    )
    parser.add_argument(
        "--head-ref-name",
        default="",
        help="PR head branch name (github.head_ref)",
    )
    args = parser.parse_args()

    base_stacks = list_stack_dirs(args.base_ref)
    head_stacks = list_stack_dirs("HEAD")
    new_stacks = sorted(head_stacks - base_stacks)

    if not new_stacks:
        print("OK: no new stacks/* directories (edits to existing stacks allowed)")
        return 0

    head = (args.head_ref_name or "").strip()
    if head.startswith("issueops/"):
        print(f"OK: new stacks allowed via IssueOps branch {head}: {', '.join(new_stacks)}")
        return 0

    fail(
        "new stack directories are forbidden for humans (including repo owners/admins). "
        "Only control IssueOps may create stacks (PR branch must be issueops/<stack_id>). "
        f"Refused: {', '.join(new_stacks)}. "
        "Edit existing stacks/** for day-2 changes, or open a control Issue Form to provision new ones."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
