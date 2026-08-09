# FILE_NAME: env_registry_pr.py
# DESCRIPTION: PR on control — add environments.yaml row + regenerate Issue Form.
# VERSION: 0.2.0
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from gh_platform_control.generate_form import write_or_check
from gh_platform_control.patch_environments import patch_environments
from gh_platform_control.util import fail


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=check,
        capture_output=capture,
        text=True,
    )


def open_env_registry_pr(
    *,
    root: Path,
    resolved: dict,
    token: str,
) -> str:
    """INTENT: Open control PR registering environment + regenerating Issue Form.
    INPUT: Control root for artifacts, resolved env plan, GH token.
    OUTPUT: PR URL.
    ROLE: EnvOps registry GitOps.
    SIDE_EFFECTS: Clones control; pushes envops branch; writes .env-registry-* artifacts.
    """
    control_repo = str(resolved.get("control_repo", "")).strip()
    env_name = str(resolved.get("environment", "")).strip()
    branch = str(resolved.get("branch", "")).strip()
    workload_repository = str(resolved.get("workload_repository", "")).strip()
    issue_number = str(resolved.get("issue_number", "")).strip()
    base_branch = "main"

    if not issue_number.isdigit():
        fail(f"invalid issue_number {issue_number}")
    if not branch.startswith("envops/") or ".." in branch:
        fail(f"unsafe branch {branch}")

    env = os.environ.copy()
    env["GH_TOKEN"] = token
    env["GIT_TERMINAL_PROMPT"] = "0"

    work = Path(tempfile.mkdtemp(prefix="env-registry-pr-"))
    try:
        _run(["gh", "auth", "setup-git"], env=env, check=True, capture=True)
        _run(
            [
                "gh",
                "repo",
                "clone",
                control_repo,
                str(work / "repo"),
                "--",
                "--depth",
                "1",
            ],
            env=env,
        )
        repo_dir = work / "repo"
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

        _run(
            ["git", "fetch", "--depth", "1", "origin", base_branch],
            cwd=repo_dir,
            env=env,
        )
        ls = _run(
            ["git", "ls-remote", "--exit-code", "origin", f"refs/heads/{branch}"],
            cwd=repo_dir,
            env=env,
            check=False,
            capture=True,
        )
        if ls.returncode == 0:
            fail(f"branch already exists: {branch}")
        _run(
            ["git", "checkout", "-B", branch, f"origin/{base_branch}"],
            cwd=repo_dir,
            env=env,
        )

        patch_environments(
            resolved=resolved,
            environments_yaml=repo_dir / "config" / "environments.yaml",
        )
        write_or_check(repo_dir, check=False)

        _run(
            [
                "git",
                "add",
                "config/environments.yaml",
                ".github/ISSUE_TEMPLATE/provision.yml",
            ],
            cwd=repo_dir,
            env=env,
        )
        diff = _run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_dir,
            env=env,
            check=False,
            capture=True,
        )
        if diff.returncode == 0:
            fail("no registry/form changes to commit")

        commit_msg = (
            f"chore(envops): register environment {env_name}\n\n"
            f"Add {workload_repository} to environments.yaml and regenerate provision Issue Form.\n"
            f"Source: {control_repo}#{issue_number}\n"
        )
        _run(["git", "commit", "-m", commit_msg], cwd=repo_dir, env=env)
        _run(["git", "push", "-u", "origin", branch], cwd=repo_dir, env=env)

        body = (
            f"## Summary\n"
            f"- Register environment `{env_name}` → `{workload_repository}`\n"
            f"- Regenerate stack provision Issue Form from catalog + environments\n"
            f"\n"
            f"## Source\n"
            f"- Issue: https://github.com/{control_repo}/issues/{issue_number}\n"
            f"\n"
            f"## After merge\n"
            f"1. Confirm Environment dropdown includes `{env_name}`.\n"
            f"2. Complete AWS OIDC trust for "
            f"`repo:{workload_repository}:environment:{env_name}`.\n"
            f"3. (Prod) add Environment reviewers on the workload repo if required.\n"
        )
        pr_proc = _run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                control_repo,
                "--base",
                base_branch,
                "--head",
                branch,
                "--title",
                f"chore(envops): register {env_name}",
                "--body",
                body,
            ],
            env=env,
            capture=True,
        )
        pr_url = (pr_proc.stdout or "").strip()
        (root / ".env-registry-pr-url").write_text(pr_url + "\n", encoding="utf-8")
        (root / ".env-registry-branch").write_text(branch + "\n", encoding="utf-8")
        print(f"OK: control PR {pr_url}")
        return pr_url
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PR on control — add environments.yaml row + regenerate Issue Form."
    )
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)

    resolved = json.loads(Path(args.resolved_json).read_text(encoding="utf-8"))
    open_env_registry_pr(root=Path(args.root), resolved=resolved, token=args.token)
    return 0


def main() -> int:
    return run()
