#!/usr/bin/env python3
# FILE_NAME: render_stack.py
# DESCRIPTION: Render product templates into a stack directory.
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def render(text: str, mapping: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in mapping:
            raise KeyError(f"missing template variable {{{{{key}}}}}")
        return mapping[key]

    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", repl, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    with open(args.resolved_json, encoding="utf-8") as f:
        resolved = json.load(f)

    inputs = resolved.get("inputs") or {}
    mapping = {
        "CONTROL_REPO": str(resolved["control_repo"]),
        "ISSUE_NUMBER": str(resolved["issue_number"]),
        "ENVIRONMENT": str(resolved["environment"]),
        "STACK_ID": str(resolved["stack_id"]),
        "AWS_REGION": str(resolved["aws_region"]),
        "MODULES_REPOSITORY": str(resolved["modules_repository"]),
        "MODULE_REF": str(resolved["module_ref"]),
        "TAGGING_MODULE_REF": str(resolved["tagging_module_ref"]),
        "TAGGING_ENVIRONMENT": str(resolved["tagging_environment"]),
        "BUCKET_NAME": str(inputs.get("bucket_name", "")),
        "PROJECT": str(inputs.get("project", "")),
        "ENABLE_VERSIONING": str(inputs.get("enable_versioning", "true")).lower(),
        "STATE_BUCKET": f"tfstate-{resolved.get('aws_account_id', 'ACCOUNT')}-{resolved['environment']}",
    }

    tmpl_dir = root / "templates" / resolved["template"]
    if not tmpl_dir.is_dir():
        print(f"ERROR: missing template dir {tmpl_dir}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for src in sorted(tmpl_dir.iterdir()):
        if not src.is_file():
            continue
        name = src.name
        if name.endswith(".tmpl"):
            name = name[: -len(".tmpl")]
        content = render(src.read_text(encoding="utf-8"), mapping)
        (out_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {out_dir / name}")

    meta = {
        "product": resolved["product"],
        "environment": resolved["environment"],
        "issue": f"{resolved['control_repo']}#{resolved['issue_number']}",
        "stack_id": resolved["stack_id"],
    }
    (out_dir / "stack-metadata.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
