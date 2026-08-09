#!/usr/bin/env python3
# FILE_NAME: check_new_stacks.py
# DESCRIPTION: Fail PRs that add new stacks/* unless they are real control IssueOps.
# VERSION: 0.3.0
# No owner/admin escape hatch — new stacks only via control GitHub App IssueOps PRs.
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BRANCH_RE = re.compile(r"^issueops/([a-z0-9][a-z0-9-]{0,127})$")
ISSUE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9][0-9]*$")


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


def is_github_app_actor(actor: str) -> bool:
    # Humans cannot register logins containing '[' — App actors end with [bot].
    a = (actor or "").strip()
    return a.endswith("[bot]")


def validate_metadata(stack_name: str) -> None:
    path = Path("stacks") / stack_name / "stack-metadata.json"
    if not path.is_file():
        fail(
            f"new stack '{stack_name}' missing stack-metadata.json "
            "(IssueOps renders this; humans must not DIY new stacks)"
        )
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"stack-metadata.json for '{stack_name}' is not valid JSON: {e}")
    if not isinstance(meta, dict):
        fail(f"stack-metadata.json for '{stack_name}' must be an object")

    stack_id = str(meta.get("stack_id") or "").strip()
    if stack_id != stack_name:
        fail(
            f"stack-metadata.json stack_id={stack_id!r} must equal directory {stack_name!r}"
        )

    issue = str(meta.get("issue") or "").strip()
    if not ISSUE_RE.fullmatch(issue):
        fail(
            f"stack-metadata.json issue={issue!r} must look like "
            "owner/control-repo#123 (control IssueOps provenance)"
        )

    for key in ("product", "natural_key", "environment", "runner"):
        if not str(meta.get(key) or "").strip():
            fail(f"stack-metadata.json missing required field {key!r}")


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
    parser.add_argument(
        "--actor",
        default="",
        help="github.actor — must be a GitHub App bot for new stacks",
    )
    args = parser.parse_args()

    base_stacks = list_stack_dirs(args.base_ref)
    head_stacks = list_stack_dirs("HEAD")
    new_stacks = sorted(head_stacks - base_stacks)

    if not new_stacks:
        print("OK: no new stacks/* directories (edits to existing stacks allowed)")
        return 0

    head = (args.head_ref_name or "").strip()
    m = BRANCH_RE.fullmatch(head)
    if not m:
        fail(
            "new stack directories are forbidden for humans (including repo owners/admins). "
            "Only control IssueOps may create stacks "
            "(branch must match issueops/<stack_id>). "
            f"Refused branch={head!r} stacks={', '.join(new_stacks)}."
        )

    stack_id = m.group(1)
    if new_stacks != [stack_id]:
        fail(
            "IssueOps PRs must add exactly one new stack matching the branch suffix. "
            f"branch stack_id={stack_id!r} new_stacks={new_stacks}"
        )

    actor = (args.actor or "").strip()
    if not is_github_app_actor(actor):
        fail(
            "new stacks require a GitHub App PR author (login ending in [bot]). "
            f"Human actor={actor!r} cannot open issueops/* DIY stacks. "
            "Use the control Issue Form."
        )

    validate_metadata(stack_id)
    print(
        f"OK: IssueOps new stack allowed "
        f"branch={head} actor={actor} stack={stack_id}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
