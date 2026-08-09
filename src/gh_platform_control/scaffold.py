# FILE_NAME: scaffold.py
# DESCRIPTION: Copy examples/infra-* into an out dir with env-specific substitutions.
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from gh_platform_control.util import fail

TEXT_SUFFIXES = {".yml", ".yaml", ".md", ".hcl", ".tf", ".json", ".py", ".sh"}


def should_rewrite(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name == "check_new_stacks.py"


def rewrite(
    text: str,
    *,
    env: str,
    account: str,
    role: str,
    region: str,
    control: str,
    owner: str,
    actions_repo: str,
    actions_ref: str,
    example_env: str,
) -> str:
    out = text
    out = out.replace("REPLACE_ACCOUNT_ID", account)
    out = out.replace("OWNER/gh-platform-control", control)
    out = out.replace("OWNER/infra-dev", f"{owner}/infra-{env}")
    out = out.replace("OWNER/infra-prod", f"{owner}/infra-{env}")

    # Full role ARNs from starters (after account substitution or still placeholder).
    for old_role in (
        f"arn:aws:iam::{account}:role/gh-platform-dev",
        f"arn:aws:iam::{account}:role/gh-platform-prod",
        "arn:aws:iam::REPLACE_ACCOUNT_ID:role/gh-platform-dev",
        "arn:aws:iam::REPLACE_ACCOUNT_ID:role/gh-platform-prod",
    ):
        out = out.replace(old_role, role)

    if example_env == "dev":
        out = out.replace("environment: dev", f"environment: {env}")
        out = out.replace('environment  = "dev"', f'environment  = "{env}"')
        out = out.replace("name: dev\n", f"name: {env}\n")
        out = out.replace("github_environment: dev\n", f"github_environment: {env}\n")
    else:
        out = out.replace("environment: prod", f"environment: {env}")
        out = out.replace('environment  = "prod"', f'environment  = "{env}"')
        out = out.replace("name: prod\n", f"name: {env}\n")
        out = out.replace("github_environment: prod\n", f"github_environment: {env}\n")

    out = out.replace("aws_region: us-east-1", f"aws_region: {region}")
    out = out.replace('aws_region   = "us-east-1"', f'aws_region   = "{region}"')
    out = out.replace('aws_account  = "REPLACE_ACCOUNT_ID"', f'aws_account  = "{account}"')

    out = re.sub(
        r"(uses:\s+)([^\s]+)/\.github/workflows/([^\s]+)@[0-9a-f]{40}",
        rf"\1{actions_repo}/.github/workflows/\3@{actions_ref}",
        out,
    )
    return out


def scaffold_infra(*, resolved: dict, out_dir: Path) -> None:
    """INTENT: Copy example tree and rewrite env-specific placeholders.
    INPUT: Resolved env onboard dict; destination path.
    OUTPUT: None (raises via fail on error).
    ROLE: EnvOps scaffolding.
    SIDE_EFFECTS: Writes/replaces out_dir tree.
    """
    src = Path(resolved["example_dir"])
    if not src.is_dir():
        fail(f"missing example {src}")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(src, out_dir)

    example_env = "dev" if resolved["example"] == "infra-dev" else "prod"
    env = resolved["environment"]
    account = resolved["aws_account_id"]
    role = resolved["aws_role_arn"]
    region = resolved["aws_region"]
    control = resolved["control_repo"]
    owner = control.split("/", 1)[0]
    actions_repo = resolved["actions_repository"]
    actions_ref = resolved["actions_ref"]

    for path in out_dir.rglob("*"):
        if not path.is_file() or not should_rewrite(path):
            continue
        text = path.read_text(encoding="utf-8")
        new = rewrite(
            text,
            env=env,
            account=account,
            role=role,
            region=region,
            control=control,
            owner=owner,
            actions_repo=actions_repo,
            actions_ref=actions_ref,
            example_env=example_env,
        )
        if new != text:
            path.write_text(new, encoding="utf-8")

    env_yaml = out_dir / "config" / "environment.yaml"
    env_yaml.parent.mkdir(parents=True, exist_ok=True)
    env_yaml.write_text(
        "\n".join(
            [
                f"# Mirror of `{env}` row from {control} config/environments.yaml",
                f"name: {env}",
                f"github_environment: {env}",
                f"aws_role_arn: {role}",
                f"aws_region: {region}",
                f"control_repository: {control}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    stacks = out_dir / "stacks"
    stacks.mkdir(exist_ok=True)
    if not any(stacks.iterdir()):
        (stacks / ".gitkeep").write_text("", encoding="utf-8")

    print(f"OK: scaffolded {out_dir} from {src.name}")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy examples/infra-* into an out dir with env-specific substitutions."
    )
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    resolved = json.loads(Path(args.resolved_json).read_text(encoding="utf-8"))
    scaffold_infra(resolved=resolved, out_dir=Path(args.out_dir))
    return 0


def main() -> int:
    return run()
