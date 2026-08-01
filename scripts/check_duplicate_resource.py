#!/usr/bin/env python3
# FILE_NAME: check_duplicate_resource.py
# DESCRIPTION: Fail+attach when natural key is claimed (control issues, open PRs, main).
# VERSION: 0.2.0
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


BUCKET_RE = re.compile(r'bucket_name\s*=\s*"([^"]+)"')
ISSUE_REF_RE = re.compile(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)")
ISSUE_HASH_RE = re.compile(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)")

CLAIM_LABELS = frozenset({"status:pending-validation", "status:pr-open"})


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def gh_api(
    path: str,
    token: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:
    url = f"https://api.github.com{path}"
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gh-platform-control-duplicate-check",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        if e.code == 404:
            return None
        fail(f"GitHub API {method} {path} failed ({e.code}): {detail}")


def list_stack_dirs(repo: str, ref: str, token: str) -> list[str]:
    data = gh_api(f"/repos/{repo}/contents/stacks?ref={urllib.parse.quote(ref)}", token)
    if not isinstance(data, list):
        return []
    return [item["name"] for item in data if item.get("type") == "dir"]


def read_main_tf(repo: str, stack_name: str, ref: str, token: str) -> str:
    path = (
        f"/repos/{repo}/contents/stacks/{urllib.parse.quote(stack_name)}/main.tf"
        f"?ref={urllib.parse.quote(ref)}"
    )
    data = gh_api(path, token)
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return ""
    raw = data.get("content") or ""
    return base64.b64decode(raw.replace("\n", "")).decode("utf-8", errors="replace")


def bucket_in_tf(tf: str) -> str | None:
    m = BUCKET_RE.search(tf)
    return m.group(1) if m else None


def find_bucket_stacks(repo: str, ref: str, bucket: str, token: str) -> list[str]:
    hits: list[str] = []
    for name in list_stack_dirs(repo, ref, token):
        tf = read_main_tf(repo, name, ref, token)
        if bucket_in_tf(tf) == bucket:
            hits.append(f"stacks/{name}")
    return hits


def open_prs(repo: str, token: str) -> list[dict[str, Any]]:
    data = gh_api(f"/repos/{repo}/pulls?state=open&per_page=100", token)
    return data if isinstance(data, list) else []


def parse_issue_fields(body: str) -> dict[str, str]:
    # Local import path when run under PYTHONPATH=scripts
    from parse_issue import parse_issue_body

    return parse_issue_body(body or "")


def owning_issue_from_text(text: str, control_repo: str) -> str | None:
    for m in ISSUE_REF_RE.finditer(text or ""):
        if m.group(1).lower() == control_repo.lower():
            return m.group(2)
    for m in ISSUE_HASH_RE.finditer(text or ""):
        if m.group(1).lower() == control_repo.lower():
            return m.group(2)
    return None


def post_comment(repo: str, issue: str, body: str, token: str) -> None:
    gh_api(
        f"/repos/{repo}/issues/{issue}/comments",
        token,
        method="POST",
        data={"body": body},
    )


def list_control_claims(
    control_repo: str,
    product: str,
    environment: str,
    bucket: str,
    self_issue: str,
    token: str,
) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    label = urllib.parse.quote(f"issueops,product:{product}")
    data = gh_api(
        f"/repos/{control_repo}/issues?state=open&labels={label}&per_page=100",
        token,
    )
    if not isinstance(data, list):
        return conflicts

    for issue in data:
        if "pull_request" in issue:
            continue
        number = str(issue.get("number", ""))
        if not number or number == self_issue:
            continue
        labels = {lbl.get("name", "") for lbl in (issue.get("labels") or [])}
        if not (labels & CLAIM_LABELS):
            continue
        fields = parse_issue_fields(issue.get("body") or "")
        if fields.get("environment") != environment:
            continue
        if fields.get("bucket_name") != bucket:
            continue
        conflicts.append(
            {
                "where": f"control issue #{number}",
                "path": ",".join(sorted(labels & CLAIM_LABELS)) or "claimed",
                "url": issue.get("html_url") or f"https://github.com/{control_repo}/issues/{number}",
                "owner_issue": number,
            }
        )
    return conflicts


def format_conflict_markdown(
    *,
    natural_key: str,
    bucket: str,
    conflicts: list[dict[str, str]],
    self_issue_url: str,
) -> str:
    lines = [
        "### IssueOps failed (`duplicate`)",
        "",
        f"Natural key `{natural_key}` is already claimed (fail + attach).",
        "",
        f"Bucket: `{bucket}`",
        "",
        "| Claim | Path / labels | Link |",
        "| --- | --- | --- |",
    ]
    for c in conflicts:
        lines.append(f"| {c['where']} | `{c.get('path', '')}` | {c['url']} |")
    lines.extend(
        [
            "",
            f"This request: {self_issue_url}",
            "",
            "Close or merge the existing claim before retrying. "
            "Same-issue re-runs attach to the existing PR.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN", ""))
    parser.add_argument(
        "--control-token",
        default=os.environ.get("CONTROL_TOKEN", "") or os.environ.get("GITHUB_TOKEN", ""),
    )
    parser.add_argument("--attach", action="store_true")
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args()

    if not args.token:
        fail("missing workload GitHub token (pass --token or GH_TOKEN)")
    control_token = args.control_token or args.token

    with open(args.resolved_json, encoding="utf-8") as f:
        resolved = json.load(f)

    product = resolved.get("product")
    if product != "s3-bucket":
        print(json.dumps({"skipped": True, "reason": f"no uniqueness rule for {product}"}))
        return 0

    bucket = str((resolved.get("inputs") or {}).get("bucket_name", "")).strip()
    if not bucket:
        fail("bucket_name missing from resolved inputs")

    repo = resolved["workload_repository"]
    control_repo = resolved["control_repo"]
    self_issue = str(resolved["issue_number"])
    environment = resolved["environment"]
    own_stack = resolved["stack_path"]
    natural_key = resolved.get("natural_key") or f"{product}:{environment}:{bucket}"
    out_dir = Path(args.out_dir)

    conflicts: list[dict[str, str]] = []

    # 1) In-flight control issues (claim labels).
    conflicts.extend(
        list_control_claims(
            control_repo,
            product,
            environment,
            bucket,
            self_issue,
            control_token,
        )
    )

    # 2) Already on main — always a conflict (even if path == own_stack).
    for path in find_bucket_stacks(repo, "main", bucket, args.token):
        conflicts.append(
            {
                "where": "main",
                "path": path,
                "url": f"https://github.com/{repo}/tree/main/{path}",
                "owner_issue": owning_issue_from_text(
                    read_main_tf(repo, path.split("/", 1)[1], "main", args.token),
                    control_repo,
                )
                or "",
            }
        )

    # 3) Open workload PRs — allow only when PR is owned by this issue.
    for pr in open_prs(repo, args.token):
        head = (pr.get("head") or {}).get("ref") or ""
        if not head:
            continue
        pr_url = pr.get("html_url") or f"https://github.com/{repo}/pull/{pr.get('number')}"
        paths = find_bucket_stacks(repo, head, bucket, args.token)
        if not paths:
            # Natural-key branch may exist before files are readable; also match branch name.
            if head.rstrip("/") == f"issueops/{resolved['stack_id']}" or head.endswith(
                f"/{resolved['stack_id']}"
            ):
                paths = [own_stack]
            else:
                continue

        owner = owning_issue_from_text(pr.get("body") or "", control_repo)
        if not owner:
            # Fall back to stack file header on the PR head.
            for path in paths:
                name = path.split("/", 1)[-1]
                owner = owning_issue_from_text(
                    read_main_tf(repo, name, head, args.token),
                    control_repo,
                )
                if owner:
                    break

        if owner == self_issue:
            # Same issue re-run → attach/reuse in open_workload_pr.
            continue

        for path in paths:
            conflicts.append(
                {
                    "where": f"PR #{pr.get('number')}",
                    "path": path,
                    "url": pr_url,
                    "owner_issue": owner or "",
                }
            )

    # De-dupe by url+path
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for c in conflicts:
        key = (c.get("url", ""), c.get("path", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    conflicts = unique

    result = {
        "ok": not conflicts,
        "natural_key": natural_key,
        "bucket_name": bucket,
        "workload_repository": repo,
        "conflicts": conflicts,
    }
    (out_dir / ".duplicate-result.json").write_text(json.dumps(result, indent=2) + "\n")

    if not conflicts:
        print(json.dumps(result))
        return 0

    self_url = f"https://github.com/{control_repo}/issues/{self_issue}"
    md = format_conflict_markdown(
        natural_key=natural_key,
        bucket=bucket,
        conflicts=conflicts,
        self_issue_url=self_url,
    )
    (out_dir / ".duplicate-conflicts.md").write_text(md)

    if args.attach:
        post_comment(control_repo, self_issue, md, control_token)
        # Attach on owning issues (fail + attach both sides).
        owners = {c.get("owner_issue") or "" for c in conflicts}
        owners.discard("")
        owners.discard(self_issue)
        for owner in sorted(owners):
            attach_body = (
                f"### Duplicate request attached\n\n"
                f"Another IssueOps request for the same natural key tried to proceed:\n\n"
                f"- Duplicate issue: {self_url}\n"
                f"- Natural key: `{natural_key}`\n\n"
                f"That request was rejected (`status:validation-failed`). "
                f"This issue remains the claim holder.\n"
            )
            post_comment(control_repo, owner, attach_body, control_token)

        result["attached"] = True
        (out_dir / ".duplicate-result.json").write_text(json.dumps(result, indent=2) + "\n")

    lines = [f"duplicate natural key '{natural_key}' already claimed:"]
    for c in conflicts:
        lines.append(f"  - {c['where']}: {c.get('path', '')} ({c['url']})")
    fail("\n".join(lines))
    return 1


if __name__ == "__main__":
    sys.exit(main())
