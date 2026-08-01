#!/usr/bin/env python3
# FILE_NAME: authorize_requester.py
# DESCRIPTION: Fail closed unless issue author is an allowed IssueOps operator.
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from lib_yaml import load_yaml_file


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def gh_api(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gh-platform-control-authorize",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        if e.code == 404:
            return {}
        fail(f"GitHub API {path} failed ({e.code}): {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--actor", required=True, help="Issue author login")
    parser.add_argument("--repository", required=True, help="owner/repo")
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN", "") or os.environ.get("GH_TOKEN", ""),
    )
    parser.add_argument(
        "--mode",
        choices=("operators_or_write", "operators_only", "write_only"),
        default="operators_or_write",
        help="Authorization policy (default: allowlist OR repo write+)",
    )
    args = parser.parse_args()

    actor = args.actor.strip().lstrip("@")
    if not actor:
        fail("empty actor")

    root = Path(args.root)
    ops_path = root / "config/operators.yaml"
    operators: list[str] = []
    if ops_path.is_file():
        data = load_yaml_file(str(ops_path))
        raw = data.get("operators") or []
        if isinstance(raw, list):
            operators = [str(x).strip().lstrip("@").lower() for x in raw if str(x).strip()]

    in_allowlist = actor.lower() in operators
    permission = ""
    write_ok = False

    if args.mode in ("operators_or_write", "write_only"):
        if not args.token:
            fail("missing GITHUB_TOKEN for collaborator permission check")
        data = gh_api(
            f"/repos/{args.repository}/collaborators/{actor}/permission",
            args.token,
        )
        permission = str(data.get("permission") or "")
        write_ok = permission in ("admin", "maintain", "write")

    allowed = False
    if args.mode == "operators_only":
        allowed = in_allowlist
    elif args.mode == "write_only":
        allowed = write_ok
    else:
        allowed = in_allowlist or write_ok

    result = {
        "actor": actor,
        "in_allowlist": in_allowlist,
        "permission": permission or None,
        "write_ok": write_ok,
        "mode": args.mode,
        "allowed": allowed,
    }
    print(json.dumps(result, sort_keys=True))

    if not allowed:
        fail(
            f"actor '{actor}' is not authorized for IssueOps on {args.repository} "
            f"(mode={args.mode}; allowlist={bool(operators)}; permission={permission or 'none'}). "
            "Public demo: only listed operators or repo write collaborators may provision."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
