# FILE_NAME: env_onboard.py
# DESCRIPTION: Create infra-<env> repo, push scaffold, env/vars/secret/ruleset.
# VERSION: 0.3.0
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from gh_platform_control.util import fail


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = False,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=check,
        capture_output=capture,
        text=True,
        input=input_text,
    )


def set_env_var(
    workload_repository: str,
    gh_environment: str,
    name: str,
    value: str,
    env: dict[str, str],
) -> None:
    exists = _run(
        [
            "gh",
            "api",
            f"/repos/{workload_repository}/environments/{gh_environment}/variables/{name}",
        ],
        env=env,
        check=False,
        capture=True,
    )
    if exists.returncode == 0:
        _run(
            [
                "gh",
                "api",
                "--method",
                "PATCH",
                f"/repos/{workload_repository}/environments/{gh_environment}/variables/{name}",
                "-f",
                f"name={name}",
                "-f",
                f"value={value}",
            ],
            env=env,
            capture=True,
        )
    else:
        _run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                f"/repos/{workload_repository}/environments/{gh_environment}/variables",
                "-f",
                f"name={name}",
                "-f",
                f"value={value}",
            ],
            env=env,
            capture=True,
        )


def onboard_environment(
    *,
    root: Path,
    resolved: dict,
    scaffold_dir: Path,
    token: str,
    app_client_id: str,
    app_private_key: str,
    ruleset_json: Path,
    modules_token: str = "",
) -> None:
    """INTENT: Create workload repo and configure env/vars/secret/ruleset.
    INPUT: Control root, resolved env plan, scaffold tree, App creds, ruleset path.
    OUTPUT: None.
    ROLE: EnvOps onboard.
    SIDE_EFFECTS: Creates GitHub repo; pushes main; writes .workload-* artifacts.
    """
    workload_repository = str(resolved.get("workload_repository", "")).strip()
    env_name = str(resolved.get("environment", "")).strip()
    gh_environment = str(resolved.get("github_environment", "")).strip()
    role_arn = str(resolved.get("aws_role_arn", "")).strip()
    region = str(resolved.get("aws_region", "")).strip()
    account_id = str(resolved.get("aws_account_id", "")).strip()
    control_repo = str(resolved.get("control_repo", "")).strip()
    modules_repository = str(resolved.get("modules_repository", "")).strip()
    client_id = app_client_id.strip()
    private_key = app_private_key.strip()

    owner, _, repo_name = workload_repository.partition("/")
    if not owner or not repo_name:
        fail(f"unexpected workload_repository {workload_repository}")
    if not re.fullmatch(r".*/infra-.+", workload_repository):
        fail(f"unexpected workload_repository {workload_repository}")
    if not re.fullmatch(r"^[a-z][a-z0-9-]{1,30}$", env_name):
        fail(f"invalid environment {env_name}")
    if not scaffold_dir.is_dir():
        fail("missing scaffold dir")
    if not ruleset_json.is_file():
        fail(f"missing ruleset json {ruleset_json}")

    env = os.environ.copy()
    env["GH_TOKEN"] = token
    env["GIT_TERMINAL_PROMPT"] = "0"

    exists = _run(
        ["gh", "api", f"repos/{workload_repository}"],
        env=env,
        check=False,
        capture=True,
    )
    if exists.returncode == 0:
        fail(f"repository already exists: {workload_repository}")

    owner_type_proc = _run(
        ["gh", "api", f"users/{owner}", "--jq", ".type"],
        env=env,
        capture=True,
    )
    owner_type = (owner_type_proc.stdout or "").strip()
    print(f"Creating {workload_repository} (owner type={owner_type})")

    if owner_type == "Organization":
        _run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                f"/orgs/{owner}/repos",
                "-f",
                f"name={repo_name}",
                "-F",
                "private=true",
                "-F",
                "auto_init=false",
                "-f",
                f"description=GitOps workload for environment {env_name}",
            ],
            env=env,
            capture=True,
        )
    else:
        _run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                "/user/repos",
                "-f",
                f"name={repo_name}",
                "-F",
                "private=true",
                "-F",
                "auto_init=false",
                "-f",
                f"description=GitOps workload for environment {env_name}",
            ],
            env=env,
            capture=True,
        )

    work = Path(tempfile.mkdtemp(prefix="env-onboard-"))
    try:
        repo_dir = work / "repo"
        repo_dir.mkdir(parents=True)
        _run(["git", "init", "-q"], cwd=repo_dir, env=env)
        _run(["git", "checkout", "-b", "main"], cwd=repo_dir, env=env)
        # Auth via gh credential helper — do not embed token in remote URL.
        _run(["gh", "auth", "setup-git"], env=env, check=True, capture=True)
        _run(
            [
                "git",
                "remote",
                "add",
                "origin",
                f"https://github.com/{workload_repository}.git",
            ],
            cwd=repo_dir,
            env=env,
        )
        _run(
            ["git", "config", "user.name", "gh-platform-control[bot]"],
            cwd=repo_dir,
            env=env,
        )
        _run(
            [
                "git",
                "config",
                "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com",
            ],
            cwd=repo_dir,
            env=env,
        )

        for item in scaffold_dir.iterdir():
            target = repo_dir / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)

        _run(["git", "add", "-A"], cwd=repo_dir, env=env)
        commit_msg = (
            f"chore(envops): scaffold {repo_name}\n\n"
            f"Bootstrap from control examples for environment {env_name}.\n"
            f"Source: {control_repo}\n"
        )
        _run(["git", "commit", "-m", commit_msg], cwd=repo_dir, env=env)
        _run(["git", "push", "-u", "origin", "main"], cwd=repo_dir, env=env)

        env_body = json.dumps(
            {
                "wait_timer": 0,
                "prevent_self_review": False,
                "reviewers": [],
                "deployment_branch_policy": None,
            }
        )
        _run(
            [
                "gh",
                "api",
                "--method",
                "PUT",
                f"/repos/{workload_repository}/environments/{gh_environment}",
                "--input",
                "-",
            ],
            env=env,
            input_text=env_body,
            capture=True,
        )

        if not client_id:
            fail("CONTROL_CLIENT_ID empty; cannot set workload App variable")
        if not private_key:
            fail("CONTROL_APP_PRIVATE_KEY empty; cannot copy App key to workload")
        if not modules_repository or "/" not in modules_repository:
            fail(
                "modules_repository missing or invalid in resolved plan "
                "(expected owner/name from pins.yaml)"
            )

        for name, value in (
            ("CONTROL_REPOSITORY", control_repo),
            ("ENVIRONMENT_NAME", env_name),
            ("AWS_ACCOUNT_ID", account_id),
            ("CONTROL_CLIENT_ID", client_id),
            ("MODULES_GIT_REPOSITORY", modules_repository),
        ):
            _run(
                [
                    "gh",
                    "variable",
                    "set",
                    name,
                    "-R",
                    workload_repository,
                    "--body",
                    value,
                ],
                env=env,
            )

        set_env_var(workload_repository, gh_environment, "AWS_ROLE_ARN", role_arn, env)
        set_env_var(workload_repository, gh_environment, "AWS_REGION", region, env)

        _run(
            [
                "gh",
                "secret",
                "set",
                "CONTROL_APP_PRIVATE_KEY",
                "-R",
                workload_repository,
            ],
            env=env,
            input_text=private_key,
        )
        # Optional PAT fallback for callers still using modules_git_token.
        if modules_token.strip():
            _run(
                [
                    "gh",
                    "secret",
                    "set",
                    "MODULES_GIT_TOKEN",
                    "-R",
                    workload_repository,
                ],
                env=env,
                input_text=modules_token,
            )

        rulesets = _run(
            ["gh", "api", f"/repos/{workload_repository}/rulesets", "--jq", ".[].name"],
            env=env,
            check=False,
            capture=True,
        )
        names = {
            ln.strip()
            for ln in (rulesets.stdout or "").splitlines()
            if ln.strip()
        }
        if "protect-main" in names:
            print("WARN: ruleset protect-main already exists; leaving as-is")
        else:
            _run(
                [
                    "gh",
                    "api",
                    "--method",
                    "POST",
                    f"/repos/{workload_repository}/rulesets",
                    "--input",
                    str(ruleset_json),
                ],
                env=env,
                capture=True,
            )
            print("OK: ruleset protect-main applied")

        (root / ".workload-repo").write_text(workload_repository + "\n", encoding="utf-8")
        (root / ".workload-url").write_text(
            f"https://github.com/{workload_repository}\n", encoding="utf-8"
        )
        print(f"OK: onboarded {workload_repository}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create infra-<env> repo, push scaffold, env/vars/secret/ruleset."
    )
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--scaffold-dir", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--app-client-id", required=True)
    parser.add_argument("--app-private-key", required=True)
    parser.add_argument(
        "--modules-token",
        default="",
        help="Optional PAT fallback copied as MODULES_GIT_TOKEN",
    )
    parser.add_argument("--ruleset-json", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)

    resolved = json.loads(Path(args.resolved_json).read_text(encoding="utf-8"))
    onboard_environment(
        root=Path(args.root),
        resolved=resolved,
        scaffold_dir=Path(args.scaffold_dir),
        token=args.token,
        app_client_id=args.app_client_id,
        app_private_key=args.app_private_key,
        modules_token=args.modules_token,
        ruleset_json=Path(args.ruleset_json),
    )
    return 0


def main() -> int:
    return run()
