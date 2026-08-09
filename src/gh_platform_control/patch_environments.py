# FILE_NAME: patch_environments.py
# DESCRIPTION: Add an environment row to config/environments.yaml (stdlib YAML subset).
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import json
from pathlib import Path

from gh_platform_control.util import fail
from gh_platform_control.yamlutil import load_simple_yaml


HEADER = """# Environment registry: env name → AWS account + workload GitOps repo.
# MVP: one env = one AWS account = one workload repo.
# Rows may be added by EnvOps (issue form + envops label).

"""


def emit(envs: dict) -> str:
    lines = [HEADER.rstrip(), "", "environments:"]
    for name, row in envs.items():
        lines.append(f"  # workload: {row.get('workload_repository', '')}")
        lines.append(f"  {name}:")
        for key in (
            "workload_repository",
            "github_environment",
            "aws_account_id",
            "aws_role_arn",
            "aws_region",
            "tagging_environment",
        ):
            val = row.get(key, "")
            if key == "aws_account_id":
                lines.append(f'    {key}: "{val}"')
            else:
                lines.append(f"    {key}: {val}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def patch_environments(*, resolved: dict, environments_yaml: Path) -> None:
    """INTENT: Append a new environment row to environments.yaml.
    INPUT: Resolved onboard dict; path to environments.yaml.
    OUTPUT: None.
    ROLE: Registry mutation helper.
    SIDE_EFFECTS: Rewrites environments_yaml.
    """
    data = load_simple_yaml(environments_yaml.read_text(encoding="utf-8"))
    envs = dict(data.get("environments") or {})
    slug = resolved["environment"]
    if slug in envs:
        fail(f"environment {slug!r} already present in {environments_yaml}")

    envs[slug] = {
        "workload_repository": resolved["workload_repository"],
        "github_environment": resolved["github_environment"],
        "aws_account_id": resolved["aws_account_id"],
        "aws_role_arn": resolved["aws_role_arn"],
        "aws_region": resolved["aws_region"],
        "tagging_environment": resolved["tagging_environment"],
    }
    environments_yaml.write_text(emit(envs), encoding="utf-8")
    print(f"OK: added environments.{slug} → {environments_yaml}")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add an environment row to config/environments.yaml (stdlib YAML subset)."
    )
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--environments-yaml", required=True)
    args = parser.parse_args(argv)

    resolved = json.loads(Path(args.resolved_json).read_text(encoding="utf-8"))
    patch_environments(
        resolved=resolved,
        environments_yaml=Path(args.environments_yaml),
    )
    return 0


def main() -> int:
    return run()
