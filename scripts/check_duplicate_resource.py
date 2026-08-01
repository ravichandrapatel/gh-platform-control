#!/usr/bin/env python3
# FILE_NAME: check_duplicate_resource.py
# DESCRIPTION: Reject requests whose natural key already exists on main or an open PR.
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import json
import base64
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


BUCKET_RE = re.compile(r'bucket_name\s*=\s*"([^"]+)"')


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def gh_api(path: str, token: str) -> Any:
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "gh-platform-control-duplicate-check",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        if e.code == 404:
            return None
        fail(f"GitHub API {path} failed ({e.code}): {detail}")


def list_stack_dirs(repo: str, ref: str, token: str) -> list[str]:
    data = gh_api(f"/repos/{repo}/contents/stacks?ref={urllib.parse.quote(ref)}", token)
    if not isinstance(data, list):
        return []
    return [item["name"] for item in data if item.get("type") == "dir"]


def read_main_tf(repo: str, stack_name: str, ref: str, token: str) -> str:
    path = f"/repos/{repo}/contents/stacks/{urllib.parse.quote(stack_name)}/main.tf"
    path += f"?ref={urllib.parse.quote(ref)}"
    data = gh_api(path, token)
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return ""
    raw = data.get("content") or ""
    return base64.b64decode(raw.replace("\n", "")).decode("utf-8", errors="replace")


def find_bucket_in_ref(repo: str, ref: str, bucket: str, token: str) -> list[str]:
    hits: list[str] = []
    for name in list_stack_dirs(repo, ref, token):
        tf = read_main_tf(repo, name, ref, token)
        m = BUCKET_RE.search(tf)
        if m and m.group(1) == bucket:
            hits.append(f"stacks/{name}")
    return hits


def open_prs(repo: str, token: str) -> list[dict[str, Any]]:
    data = gh_api(f"/repos/{repo}/pulls?state=open&per_page=100", token)
    return data if isinstance(data, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN", ""))
    args = parser.parse_args()

    if not args.token:
        fail("missing GitHub token (pass --token or GH_TOKEN)")

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
    own_stack = resolved["stack_path"]  # stacks/<id>
    conflicts: list[dict[str, str]] = []

    for path in find_bucket_in_ref(repo, "main", bucket, args.token):
        if path == own_stack:
            continue
        conflicts.append({"where": "main", "path": path, "url": f"https://github.com/{repo}/tree/main/{path}"})

    for pr in open_prs(repo, args.token):
        head = (pr.get("head") or {}).get("ref") or ""
        if not head:
            continue
        for path in find_bucket_in_ref(repo, head, bucket, args.token):
            if path == own_stack:
                # Same issue re-run / same stack id — allow open_workload_pr reuse.
                continue
            conflicts.append(
                {
                    "where": f"PR #{pr.get('number')}",
                    "path": path,
                    "url": pr.get("html_url") or f"https://github.com/{repo}/pull/{pr.get('number')}",
                }
            )

    if conflicts:
        lines = [f"duplicate bucket_name '{bucket}' already requested/provisioned:"]
        for c in conflicts:
            lines.append(f"  - {c['where']}: {c['path']} ({c['url']})")
        fail("\n".join(lines))

    print(json.dumps({"ok": True, "bucket_name": bucket, "workload_repository": repo}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
