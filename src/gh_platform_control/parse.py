# FILE_NAME: parse.py
# DESCRIPTION: Parse GitHub Issue Form markdown body into JSON.
# VERSION: 0.1.1
from __future__ import annotations

import argparse
import json
import re

HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")


def slug_key(label: str) -> str:
    key = label.strip().lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "", key)


def parse_issue_body(body: str) -> dict[str, str]:
    # Drop HTML comments (e.g. <!-- retest ... -->) so they never join field values.
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)

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
        # Issue Forms are single-line scalars; keep the first non-empty line only.
        if value:
            value = next((ln.strip() for ln in value.splitlines() if ln.strip()), "")
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


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse GitHub Issue Form markdown body into JSON."
    )
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    with open(args.body_file, encoding="utf-8") as f:
        body = f.read()
    data = parse_issue_body(body)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(data, sort_keys=True))
    return 0


def main() -> int:
    return run()
