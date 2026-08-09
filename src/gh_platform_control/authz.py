# FILE_NAME: authz.py
# DESCRIPTION: Fail closed unless issue author is an allowed IssueOps operator.
# VERSION: 0.2.1
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from gh_platform_control.github_http import gh_request
from gh_platform_control.util import fail
from gh_platform_control.yamlutil import load_yaml_file

# GitHub login: alnum / hyphen; 1–39 chars. Rejects injection into API paths.
ACTOR_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def gh_api(path: str, token: str) -> dict:
    data = gh_request(
        path,
        token,
        timeout=30,
        user_agent="gh-platform-control-authorize",
        not_found=lambda: {},
    )
    return data if isinstance(data, dict) else {}


def authorize(
    *,
    root: Path,
    actor: str,
    repository: str,
    token: str,
    mode: str = "operators_or_write",
) -> dict:
    """INTENT: Decide if actor may run IssueOps on repository.
    INPUT: root (operators.yaml), actor login, repo, token, mode.
    OUTPUT: Result dict including allowed bool (also printed by run).
    ROLE: Authorization gate.
    SIDE_EFFECTS: May call GitHub API.
    """
    actor = actor.strip().lstrip("@")
    if not actor or not ACTOR_RE.fullmatch(actor):
        fail(f"invalid actor login {actor!r}")
    if not REPO_RE.fullmatch(repository.strip()):
        fail(f"invalid repository {repository!r}")

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

    if mode in ("operators_or_write", "write_only"):
        if not token:
            fail("missing GITHUB_TOKEN for collaborator permission check")
        data = gh_api(
            f"/repos/{repository}/collaborators/{actor}/permission",
            token,
        )
        permission = str(data.get("permission") or "")
        write_ok = permission in ("admin", "maintain", "write")

    allowed = False
    if mode == "operators_only":
        allowed = in_allowlist
    elif mode == "write_only":
        allowed = write_ok
    else:
        allowed = in_allowlist or write_ok

    return {
        "actor": actor,
        "in_allowlist": in_allowlist,
        "permission": permission or None,
        "write_ok": write_ok,
        "mode": mode,
        "allowed": allowed,
        "operators_configured": bool(operators),
        "repository": repository,
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed unless issue author is an allowed IssueOps operator."
    )
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
    args = parser.parse_args(argv)

    result = authorize(
        root=Path(args.root),
        actor=args.actor,
        repository=args.repository,
        token=args.token,
        mode=args.mode,
    )
    # Match prior CLI shape (no operators_configured / repository in print).
    printed = {
        "actor": result["actor"],
        "in_allowlist": result["in_allowlist"],
        "permission": result["permission"],
        "write_ok": result["write_ok"],
        "mode": result["mode"],
        "allowed": result["allowed"],
    }
    print(json.dumps(printed, sort_keys=True))

    if not result["allowed"]:
        fail(
            f"actor '{result['actor']}' is not authorized for IssueOps on {args.repository} "
            f"(mode={args.mode}; allowlist={result['operators_configured']}; "
            f"permission={result['permission'] or 'none'}). "
            "Public demo: only listed operators or repo write collaborators may provision."
        )
    return 0


def main() -> int:
    return run()
