# FILE_NAME: validate_env.py
# DESCRIPTION: Validate env-onboard Issue Form fields; resolve template + registry row.
# VERSION: 0.3.0
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from gh_platform_control.util import fail
from gh_platform_control.yamlutil import load_simple_yaml

ENV_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
ACCOUNT_RE = re.compile(r"^\d{12}$")
ARN_RE = re.compile(r"^arn:aws:iam::\d{12}:role/[A-Za-z0-9+=,.@_-]+$")
REGION_RE = re.compile(r"^[a-z]{2}(-[a-z]+)+-\d+$")
RESERVED_SLUGS = frozenset({"main", "master", "github", "actions", "control"})


def load_yaml(path: Path) -> dict:
    return load_simple_yaml(path.read_text(encoding="utf-8"))


def validate_env_request(
    *,
    root: Path,
    req: dict,
    issue_number: str,
    control_repo: str,
) -> dict:
    """INTENT: Validate EnvOps form fields and build resolved onboard plan.
    INPUT: Control root, parsed request, issue number, control repo.
    OUTPUT: Resolved env onboard dict.
    ROLE: EnvOps validation.
    SIDE_EFFECTS: Reads environments.yaml and pins.yaml.
    """
    if not str(issue_number).isdigit():
        fail(f"issue-number must be digits, got {issue_number!r}")

    if not isinstance(req, dict):
        fail("request JSON must be an object")

    slug = (req.get("environment_name") or "").strip().lower()
    profile = (req.get("profile") or "").strip().lower()
    account = (req.get("aws_account_id") or "").strip()
    role_arn = (req.get("aws_role_arn") or "").strip()
    region = (req.get("aws_region") or "").strip() or "us-east-1"

    if not ENV_SLUG_RE.fullmatch(slug):
        fail(
            "Environment name must match ^[a-z][a-z0-9-]{1,30}$ "
            f"(got {slug!r})"
        )
    if slug in RESERVED_SLUGS:
        fail(f"environment name {slug!r} is reserved")
    if profile not in ("non-prod", "prod"):
        fail(f"Profile must be non-prod or prod (got {profile!r})")
    if not ACCOUNT_RE.fullmatch(account):
        fail(f"AWS account ID must be 12 digits (got {account!r})")
    if not ARN_RE.fullmatch(role_arn):
        fail(f"AWS role ARN looks invalid (got {role_arn!r})")
    if f"arn:aws:iam::{account}:role/" not in role_arn:
        fail("AWS role ARN account id must match AWS account ID field")
    if not REGION_RE.fullmatch(region):
        fail(f"AWS region looks invalid (got {region!r})")

    envs_path = root / "config" / "environments.yaml"
    envs = load_yaml(envs_path).get("environments") or {}
    if slug in envs:
        fail(f"environment {slug!r} already registered in config/environments.yaml")

    pins = load_yaml(root / "config" / "pins.yaml")
    actions_repo = ((pins.get("actions") or {}).get("repository") or "").strip()
    actions_ref = ((pins.get("actions") or {}).get("ref") or "").strip()
    modules_repo = ((pins.get("modules") or {}).get("repository") or "").strip()
    if not actions_repo or not actions_ref or len(actions_ref) != 40:
        fail("config/pins.yaml actions.repository/ref missing or ref not 40-char SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", actions_ref):
        fail("config/pins.yaml actions.ref must be a lowercase 40-char hex SHA")
    if not modules_repo or "/" not in modules_repo:
        fail("config/pins.yaml modules.repository missing or not owner/name")

    owner = control_repo.split("/", 1)[0]
    workload_repository = f"{owner}/infra-{slug}"
    example = "infra-dev" if profile == "non-prod" else "infra-prod"
    tagging = "NON-PROD" if profile == "non-prod" else "PROD"
    examples_root = (root / "examples").resolve()
    example_dir = (examples_root / example).resolve()
    try:
        example_dir.relative_to(examples_root)
    except ValueError:
        fail(f"example path escapes examples/: {example}")
    if not example_dir.is_dir():
        fail(f"missing starter tree {example_dir}")

    return {
        "environment": slug,
        "profile": profile,
        "tagging_environment": tagging,
        "example": example,
        "example_dir": str(example_dir),
        "workload_repository": workload_repository,
        "github_environment": slug,
        "aws_account_id": account,
        "aws_role_arn": role_arn,
        "aws_region": region,
        "actions_repository": actions_repo,
        "actions_ref": actions_ref,
        "modules_repository": modules_repo,
        "control_repo": control_repo,
        "issue_number": str(issue_number),
        "branch": f"envops/{slug}",
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate env-onboard Issue Form fields; resolve template + registry row."
    )
    parser.add_argument("--request-json", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--control-repo", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    req = json.loads(Path(args.request_json).read_text(encoding="utf-8"))
    resolved = validate_env_request(
        root=Path(args.root),
        req=req,
        issue_number=args.issue_number,
        control_repo=args.control_repo,
    )
    Path(args.out).write_text(
        json.dumps(resolved, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(resolved, sort_keys=True))
    return 0


def main() -> int:
    return run()
