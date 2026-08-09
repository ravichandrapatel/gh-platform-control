# FILE_NAME: labels.py
# DESCRIPTION: Create IssueOps labels on the control repository.
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from gh_platform_control.util import fail

# (name, color, description) — duplicates from bootstrap-labels.sh removed.
LABELS: list[tuple[str, str, str]] = [
    ("issueops", "0E8A16", "IssueOps intake (stack provision)"),
    ("envops", "5319E7", "EnvOps intake (onboard environment)"),
    ("product:s3-bucket", "1D76DB", "Product: S3 bucket"),
    ("product:s3-bucket-tg", "0052CC", "Product: S3 bucket (Terragrunt)"),
    ("status:pending-validation", "FBCA04", "Awaiting control validation"),
    ("status:validation-failed", "D93F0B", "Catalog/schema validation failed"),
    ("status:config-error", "B60205", "Missing App/secrets/pins/config"),
    ("status:provision-failed", "E99695", "PR/deployment step failed"),
    ("status:env-ready", "0E8A16", "Workload repo onboarded; control registry PR open"),
    ("status:pr-open", "0075CA", "Workload PR opened"),
    ("status:plan-ok", "0E8A16", "Workload plan succeeded"),
    ("status:plan-failed", "D93F0B", "Workload plan failed"),
    ("status:applied", "0E8A16", "Apply succeeded"),
    ("status:apply-failed", "D93F0B", "Apply failed"),
]


def create_label(repo: str, name: str, color: str, desc: str, *, env: dict[str, str]) -> None:
    subprocess.run(
        [
            "gh",
            "label",
            "create",
            name,
            "--repo",
            repo,
            "--color",
            color,
            "--description",
            desc,
            "--force",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        env=env,
    )
    print(f"OK label {name}")


def bootstrap_labels(repo: str, *, token: str | None = None) -> None:
    """INTENT: Ensure IssueOps/EnvOps labels exist on the control repo.
    INPUT: owner/repo; optional GH token.
    OUTPUT: None.
    ROLE: Label bootstrap.
    SIDE_EFFECTS: Creates/updates labels via gh CLI.
    """
    if not repo:
        fail("Usage: bootstrap-labels OWNER/gh-platform-control")

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    if token:
        env["GH_TOKEN"] = token

    for name, color, desc in LABELS:
        create_label(repo, name, color, desc, env=env)

    print(f"OK: IssueOps labels ready on {repo}")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create IssueOps labels on the control repository."
    )
    parser.add_argument(
        "repository",
        nargs="?",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="OWNER/repo (default: GITHUB_REPOSITORY)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GH_TOKEN", "") or os.environ.get("GITHUB_TOKEN", ""),
    )
    args = parser.parse_args(argv)
    if not args.repository:
        print(
            "Usage: python -m gh_platform_control bootstrap-labels OWNER/gh-platform-control",
            file=sys.stderr,
        )
        return 1
    bootstrap_labels(args.repository, token=args.token or None)
    return 0


def main() -> int:
    return run()
