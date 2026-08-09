# FILE_NAME: workload_pr.py
# DESCRIPTION: Commit rendered stack into workload repo and open a PR via gh.
# VERSION: 0.4.0
from __future__ import annotations

import argparse
import json
import os
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


def _gh_json(cmd: list[str], env: dict[str, str]) -> object:
    proc = _run(cmd, env=env, check=False, capture=True)
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return []
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []


def pr_owned_by_this_issue(pr_body: str, control_repo: str, issue_number: str) -> bool:
    marker_a = f"https://github.com/{control_repo}/issues/{issue_number}"
    marker_b = f"{control_repo}#{issue_number}"
    return marker_a in pr_body or marker_b in pr_body


def stack_exists_on_ref(repo_dir: Path, ref: str, stack_path: str, env: dict[str, str]) -> bool:
    for marker in ("main.tf", "terragrunt.hcl", "stack-metadata.json"):
        proc = _run(
            ["git", "cat-file", "-e", f"{ref}:{stack_path}/{marker}"],
            cwd=repo_dir,
            env=env,
            check=False,
            capture=True,
        )
        if proc.returncode == 0:
            return True
    return False


def write_pr_artifacts(
    root: Path,
    *,
    url: str,
    branch: str,
    workload_repository: str,
    mode: str,
) -> None:
    print(f"PR_URL={url}")
    (root / ".pr-url").write_text(url + "\n", encoding="utf-8")
    (root / ".pr-branch").write_text(branch + "\n", encoding="utf-8")
    (root / ".workload-repo").write_text(workload_repository + "\n", encoding="utf-8")
    (root / ".pr-mode").write_text(mode + "\n", encoding="utf-8")


def open_workload_pr(
    *,
    root: Path,
    resolved: dict,
    stack_src: Path,
    token: str,
) -> str:
    """INTENT: Push rendered stack and open/attach workload PR.
    INPUT: Control root for artifacts, resolved JSON, stack dir, GH token.
    OUTPUT: PR URL.
    ROLE: IssueOps GitOps PR.
    SIDE_EFFECTS: Clones workload repo; pushes branch; writes .pr-* artifacts.
    """
    workload_repository = str(resolved.get("workload_repository", "")).strip()
    stack_path = str(resolved.get("stack_path", "")).strip()
    stack_id = str(resolved.get("stack_id", "")).strip()
    issue_number = str(resolved.get("issue_number", "")).strip()
    control_repo = str(resolved.get("control_repo", "")).strip()
    environment = str(resolved.get("environment", "")).strip()
    product = str(resolved.get("product", "")).strip()
    natural_key = str(resolved.get("natural_key", "")).strip()

    if not workload_repository or not stack_path or not stack_id:
        fail("resolved json missing workload/stack fields")
    if not issue_number.isdigit():
        fail(f"invalid issue_number {issue_number}")
    if not stack_path.startswith("stacks/") or ".." in stack_path:
        fail(f"unsafe stack_path {stack_path}")
    if not stack_src.is_dir():
        fail(f"missing stack source dir {stack_src}")

    owner = workload_repository.split("/", 1)[0]
    base_branch = "main"
    branch = f"issueops/{stack_id}"

    env = os.environ.copy()
    env["GH_TOKEN"] = token
    env["GIT_TERMINAL_PROMPT"] = "0"

    existing = _gh_json(
        [
            "gh",
            "api",
            f"repos/{workload_repository}/pulls?state=open&head={owner}:{branch}",
        ],
        env,
    )
    existing_pr = ""
    existing_body = ""
    if isinstance(existing, list) and existing and isinstance(existing[0], dict):
        existing_pr = str(existing[0].get("html_url") or "")
        existing_body = str(existing[0].get("body") or "")

    mode = "created"
    if existing_pr.startswith("https://"):
        if not pr_owned_by_this_issue(existing_body, control_repo, issue_number):
            fail(
                f"natural-key branch already has open PR owned by another issue: {existing_pr}"
            )
        mode = "attached"
        print(f"ATTACH: refreshing stack on same-issue PR {existing_pr}")

    work = Path(tempfile.mkdtemp(prefix="workload-pr-"))
    try:
        # Clone without embedding the token in the remote URL.
        _run(["gh", "auth", "setup-git"], env=env, check=True, capture=True)
        _run(
            [
                "gh",
                "repo",
                "clone",
                workload_repository,
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
            _run(
                [
                    "git",
                    "fetch",
                    "--depth",
                    "1",
                    "origin",
                    f"refs/heads/{branch}:refs/remotes/origin/{branch}",
                ],
                cwd=repo_dir,
                env=env,
            )
            _run(
                ["git", "checkout", "-B", branch, f"origin/{branch}"],
                cwd=repo_dir,
                env=env,
            )
        else:
            _run(
                ["git", "checkout", "-B", branch, f"origin/{base_branch}"],
                cwd=repo_dir,
                env=env,
            )

        if stack_exists_on_ref(repo_dir, f"origin/{base_branch}", stack_path, env):
            fail(f"stack already exists on {base_branch}: {stack_path}")

        dest = repo_dir / stack_path
        dest.mkdir(parents=True, exist_ok=True)
        for item in stack_src.iterdir():
            target = dest / item.name
            if item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)

        _run(["git", "add", stack_path], cwd=repo_dir, env=env)
        diff = _run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_dir,
            env=env,
            check=False,
            capture=True,
        )
        if diff.returncode == 0:
            if mode == "attached" and existing_pr.startswith("https://"):
                print(f"ATTACH: no file changes; keeping {existing_pr}")
                write_pr_artifacts(
                    root,
                    url=existing_pr,
                    branch=branch,
                    workload_repository=workload_repository,
                    mode=mode,
                )
                return existing_pr
            ls2 = _run(
                ["git", "ls-remote", "--exit-code", "origin", f"refs/heads/{branch}"],
                cwd=repo_dir,
                env=env,
                check=False,
                capture=True,
            )
            if ls2.returncode == 0:
                print(
                    f"WARN: no new commits; opening PR from existing remote branch {branch}"
                )
                _run(
                    ["git", "push", "-u", "origin", branch],
                    cwd=repo_dir,
                    env=env,
                    check=False,
                )
            else:
                fail(f"no changes to commit (stack may already exist on {base_branch})")
        else:
            msg = (
                f"feat(issueops): add {stack_id}\n\n"
                f"Provision {product} for {environment} from {control_repo}#{issue_number}.\n"
                f"Natural-key: {natural_key}\n"
            )
            _run(["git", "commit", "-m", msg], cwd=repo_dir, env=env)
            _run(["git", "push", "-u", "origin", branch], cwd=repo_dir, env=env)

        if mode == "attached" and existing_pr.startswith("https://"):
            write_pr_artifacts(
                root,
                url=existing_pr,
                branch=branch,
                workload_repository=workload_repository,
                mode=mode,
            )
            return existing_pr

        title = f"feat(issueops): {stack_id}"
        body = (
            f"## Summary\n"
            f"- Product: `{product}`\n"
            f"- Environment: `{environment}`\n"
            f"- Stack: `{stack_path}`\n"
            f"- Natural key: `{natural_key}`\n"
            f"- Request: https://github.com/{control_repo}/issues/{issue_number}\n"
            f"\n"
            f"## Test plan\n"
            f"- [ ] Review generated OpenTofu / Terragrunt root\n"
            f"- [ ] Confirm CI plan (Checkov / Conftest / tofu plan) is green\n"
            f"- [ ] Merge to apply (prod requires Environment approval)\n"
        )

        pr_proc = _run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                f"repos/{workload_repository}/pulls",
                "-f",
                f"title={title}",
                "-f",
                f"head={branch}",
                "-f",
                f"base={base_branch}",
                "-f",
                f"body={body}",
                "--jq",
                ".html_url",
            ],
            env=env,
            check=False,
            capture=True,
        )
        pr_url = (pr_proc.stdout or "").strip()
        if not pr_url.startswith("https://"):
            race = _gh_json(
                [
                    "gh",
                    "api",
                    f"repos/{workload_repository}/pulls?state=open&head={owner}:{branch}",
                ],
                env,
            )
            race_pr = ""
            race_body = ""
            if isinstance(race, list) and race and isinstance(race[0], dict):
                race_pr = str(race[0].get("html_url") or "")
                race_body = str(race[0].get("body") or "")
            if race_pr.startswith("https://") and pr_owned_by_this_issue(
                race_body, control_repo, issue_number
            ):
                print(f"ATTACH: raced to existing same-issue PR {race_pr}")
                pr_url = race_pr
                mode = "attached"
            else:
                print(
                    "ERROR: failed to open PR. Ensure the GitHub App has "
                    f"Pull requests: Read and write on {workload_repository}.",
                    flush=True,
                )
                print(
                    f"Branch pushed: https://github.com/{workload_repository}/"
                    f"compare/{base_branch}...{branch}?expand=1",
                    flush=True,
                )
                if pr_proc.stderr:
                    print(pr_proc.stderr, end="", flush=True)
                raise SystemExit(1)

        write_pr_artifacts(
            root,
            url=pr_url,
            branch=branch,
            workload_repository=workload_repository,
            mode=mode,
        )
        return pr_url
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Commit rendered stack into workload repo and open a PR via gh."
    )
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--stack-src", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)

    resolved = json.loads(Path(args.resolved_json).read_text(encoding="utf-8"))
    open_workload_pr(
        root=Path(args.root),
        resolved=resolved,
        stack_src=Path(args.stack_src),
        token=args.token,
    )
    return 0


def main() -> int:
    return run()
