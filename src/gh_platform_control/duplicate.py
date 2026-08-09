# FILE_NAME: duplicate.py
# DESCRIPTION: Fail+attach when natural key is claimed (control issues, open PRs, main).
# VERSION: 0.4.1
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any

from gh_platform_control.github_http import gh_request
from gh_platform_control.parse import parse_issue_body
from gh_platform_control.util import fail

# Matches tofu module args and terragrunt inputs (spaces around '=' allowed).
BUCKET_RE = re.compile(r'bucket_name\s*=\s*"([^"]+)"')
ISSUE_REF_RE = re.compile(r"https://github\.com/([^/]+/[^/]+)/issues/(\d+)")
ISSUE_HASH_RE = re.compile(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)")

CLAIM_LABELS = frozenset({"status:pending-validation", "status:pr-open"})
MAX_GH_PAGES = 5


def gh_api(
    path: str,
    token: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:
    return gh_request(
        path,
        token,
        method=method,
        data=data,
        user_agent="gh-platform-control-duplicate-check",
    )


def gh_api_paginated(path: str, token: str, *, per_page: int = 100) -> list[Any]:
    """Fetch up to MAX_GH_PAGES of a list endpoint (Link-header free, page= N)."""
    items: list[Any] = []
    sep = "&" if "?" in path else "?"
    for page in range(1, MAX_GH_PAGES + 1):
        data = gh_api(f"{path}{sep}per_page={per_page}&page={page}", token)
        if not isinstance(data, list) or not data:
            break
        items.extend(data)
        if len(data) < per_page:
            break
    return items


def list_stack_dirs(repo: str, ref: str, token: str) -> list[str]:
    data = gh_api(f"/repos/{repo}/contents/stacks?ref={urllib.parse.quote(ref)}", token)
    if not isinstance(data, list):
        return []
    return [item["name"] for item in data if item.get("type") == "dir"]


def read_repo_file(repo: str, path: str, ref: str, token: str) -> str:
    api = (
        f"/repos/{repo}/contents/{urllib.parse.quote(path)}"
        f"?ref={urllib.parse.quote(ref)}"
    )
    data = gh_api(api, token)
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return ""
    raw = data.get("content") or ""
    return base64.b64decode(raw.replace("\n", "")).decode("utf-8", errors="replace")


def bucket_from_text(text: str) -> str | None:
    if not text:
        return None
    m = BUCKET_RE.search(text)
    return m.group(1) if m else None


def bucket_from_metadata(text: str) -> str | None:
    if not text.strip():
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    direct = str(data.get("bucket_name") or "").strip()
    if direct:
        return direct
    uniq = data.get("uniqueness_inputs") or {}
    if isinstance(uniq, dict):
        nested = str(uniq.get("bucket_name") or "").strip()
        if nested:
            return nested
    return None


def bucket_in_stack(repo: str, stack_name: str, ref: str, token: str) -> str | None:
    """Resolve bucket_name from tofu main.tf, terragrunt.hcl, or stack-metadata.json."""
    meta = read_repo_file(repo, f"stacks/{stack_name}/stack-metadata.json", ref, token)
    hit = bucket_from_metadata(meta)
    if hit:
        return hit
    for rel in ("main.tf", "terragrunt.hcl"):
        body = read_repo_file(repo, f"stacks/{stack_name}/{rel}", ref, token)
        hit = bucket_from_text(body)
        if hit:
            return hit
    return None


def stack_ownership_text(repo: str, stack_name: str, ref: str, token: str) -> str:
    """Prefer main.tf / terragrunt.hcl headers for issue ownership markers."""
    parts: list[str] = []
    for rel in ("main.tf", "terragrunt.hcl", "README.md"):
        parts.append(read_repo_file(repo, f"stacks/{stack_name}/{rel}", ref, token))
    meta = read_repo_file(repo, f"stacks/{stack_name}/stack-metadata.json", ref, token)
    if meta:
        parts.append(meta)
    return "\n".join(parts)


def find_bucket_stacks(repo: str, ref: str, bucket: str, token: str) -> list[str]:
    hits: list[str] = []
    for name in list_stack_dirs(repo, ref, token):
        if bucket_in_stack(repo, name, ref, token) == bucket:
            hits.append(f"stacks/{name}")
    return hits


def open_prs(repo: str, token: str) -> list[dict[str, Any]]:
    data = gh_api_paginated(f"/repos/{repo}/pulls?state=open", token)
    return [item for item in data if isinstance(item, dict)]


def parse_issue_fields(body: str) -> dict[str, str]:
    return parse_issue_body(body or "")


def owning_issue_from_text(text: str, control_repo: str) -> str | None:
    for m in ISSUE_REF_RE.finditer(text or ""):
        if m.group(1).lower() == control_repo.lower():
            return m.group(2)
    for m in ISSUE_HASH_RE.finditer(text or ""):
        if m.group(1).lower() == control_repo.lower():
            return m.group(2)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            issue = str(data.get("issue") or "")
            if "#" in issue:
                repo_part, _, num = issue.partition("#")
                if repo_part.lower() == control_repo.lower() and num.isdigit():
                    return num
    except (json.JSONDecodeError, TypeError):
        pass
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
    """Scan open IssueOps claims for the same bucket+env (any S3 product / runner)."""
    del product  # bucket uniqueness is env-scoped across tofu + terragrunt products
    conflicts: list[dict[str, str]] = []
    label = urllib.parse.quote("issueops")
    data = gh_api_paginated(
        f"/repos/{control_repo}/issues?state=open&labels={label}",
        token,
    )

    for issue in data:
        if not isinstance(issue, dict):
            continue
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


def check_duplicate(
    *,
    resolved: dict,
    token: str,
    control_token: str,
    attach: bool,
    out_dir: Path,
) -> dict:
    """INTENT: Detect natural-key conflicts across issues/PRs/main.
    INPUT: Resolved stack request, tokens, attach flag, artifact dir.
    OUTPUT: Result dict (raises SystemExit via fail on conflict).
    ROLE: Duplicate gate.
    SIDE_EFFECTS: Writes .duplicate-* artifacts; may post issue comments.
    """
    product = resolved.get("product")
    if product not in ("s3-bucket", "s3-bucket-tg"):
        result = {"skipped": True, "reason": f"no uniqueness rule for {product}"}
        print(json.dumps(result))
        return result

    bucket = str((resolved.get("inputs") or {}).get("bucket_name", "")).strip()
    if not bucket:
        fail("bucket_name missing from resolved inputs")

    repo = resolved["workload_repository"]
    control_repo = resolved["control_repo"]
    self_issue = str(resolved["issue_number"])
    environment = resolved["environment"]
    own_stack = resolved["stack_path"]
    natural_key = resolved.get("natural_key") or f"{product}:{environment}:{bucket}"

    conflicts: list[dict[str, str]] = []

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

    for path in find_bucket_stacks(repo, "main", bucket, token):
        stack_name = path.split("/", 1)[1]
        conflicts.append(
            {
                "where": "main",
                "path": path,
                "url": f"https://github.com/{repo}/tree/main/{path}",
                "owner_issue": owning_issue_from_text(
                    stack_ownership_text(repo, stack_name, "main", token),
                    control_repo,
                )
                or "",
            }
        )

    for pr in open_prs(repo, token):
        head = (pr.get("head") or {}).get("ref") or ""
        if not head:
            continue
        pr_url = pr.get("html_url") or f"https://github.com/{repo}/pull/{pr.get('number')}"
        paths = find_bucket_stacks(repo, head, bucket, token)
        if not paths:
            if head.rstrip("/") == f"issueops/{resolved['stack_id']}" or head.endswith(
                f"/{resolved['stack_id']}"
            ):
                paths = [own_stack]
            else:
                continue

        owner = owning_issue_from_text(pr.get("body") or "", control_repo)
        if not owner:
            for path in paths:
                name = path.split("/", 1)[-1]
                owner = owning_issue_from_text(
                    stack_ownership_text(repo, name, head, token),
                    control_repo,
                )
                if owner:
                    break

        if owner == self_issue:
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
        return result

    self_url = f"https://github.com/{control_repo}/issues/{self_issue}"
    md = format_conflict_markdown(
        natural_key=natural_key,
        bucket=bucket,
        conflicts=conflicts,
        self_issue_url=self_url,
    )
    (out_dir / ".duplicate-conflicts.md").write_text(md)

    if attach:
        post_comment(control_repo, self_issue, md, control_token)
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
    return result


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail+attach when natural key is claimed (control issues, open PRs, main)."
    )
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN", ""))
    parser.add_argument(
        "--control-token",
        default=os.environ.get("CONTROL_TOKEN", "") or os.environ.get("GITHUB_TOKEN", ""),
    )
    parser.add_argument("--attach", action="store_true")
    parser.add_argument("--out-dir", default=".")
    args = parser.parse_args(argv)

    if not args.token:
        fail("missing workload GitHub token (pass --token or GH_TOKEN)")
    control_token = args.control_token or args.token

    with open(args.resolved_json, encoding="utf-8") as f:
        resolved = json.load(f)

    check_duplicate(
        resolved=resolved,
        token=args.token,
        control_token=control_token,
        attach=args.attach,
        out_dir=Path(args.out_dir),
    )
    return 0


def main() -> int:
    return run()
