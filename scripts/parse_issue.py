#!/usr/bin/env python3
# FILE_NAME: parse_issue.py
# DESCRIPTION: Parse GitHub Issue Form markdown body into JSON.
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import json
import re
import sys


HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")


def slug_key(label: str) -> str:
    key = label.strip().lower()
    key = key.replace(" ", "_")
    key = re.sub(r"[^a-z0-9_]+", "", key)
    aliases = {
        "bucket_name": "bucket_name",
        "environment": "environment",
        "project": "project",
        "enable_versioning": "enable_versioning",
        "product": "product",
    }
    return aliases.get(key, key)


def parse_issue_body(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal current, buf
        if current is None:
            return
        value = "\n".join(buf).strip()
        if value in ("_No response_", "None"):
            value = ""
        fields[current] = value
        current = None
        buf = []

    for line in body.splitlines():
        m = HEADING_RE.match(line)
        if m:
            flush()
            current = slug_key(m.group(1))
            buf = []
            continue
        if current is not None:
            buf.append(line)
    flush()
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with open(args.body_file, encoding="utf-8") as f:
        body = f.read()
    data = parse_issue_body(body)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(data, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
