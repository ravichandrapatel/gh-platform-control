#!/usr/bin/env python3
# FILE_NAME: validate_request.py
# DESCRIPTION: Validate parsed Issue Form JSON against catalog + environments.
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from lib_yaml import load_yaml_file


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_product(catalog_dir: Path, product_id: str) -> dict:
    path = catalog_dir / f"{product_id}.yaml"
    if not path.is_file():
        fail(f"unknown product '{product_id}' (missing {path})")
    return load_yaml_file(str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-json", required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", required=True)
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--control-repo", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    with open(args.request_json, encoding="utf-8") as f:
        req = json.load(f)

    product = load_product(root / "config/catalog/products", args.product)
    envs = load_yaml_file(str(root / "config/environments.yaml")).get("environments") or {}
    pins = load_yaml_file(str(root / "config/pins.yaml"))

    inputs_spec = product.get("inputs") or {}
    for name, spec in inputs_spec.items():
        if not isinstance(spec, dict):
            continue
        val = str(req.get(name, "")).strip()
        if spec.get("required") and not val:
            fail(f"missing required input '{name}'")
        if not val:
            continue
        if spec.get("from_environments") and val not in envs:
            fail(f"environment '{val}' not in config/environments.yaml")
        enum = spec.get("enum")
        if enum and val not in enum:
            fail(f"input '{name}'={val!r} not in {enum}")
        pattern = spec.get("pattern")
        if pattern and not re.fullmatch(pattern, val):
            fail(f"input '{name}'={val!r} failed pattern {pattern}")

    environment = str(req.get("environment", "")).strip()
    env_cfg = envs[environment]

    stack_parts = []
    for key in product.get("stack_id_from") or ["product"]:
        if key == "product":
            stack_parts.append(args.product)
        else:
            stack_parts.append(re.sub(r"[^a-z0-9-]+", "-", str(req[key]).lower()).strip("-"))
    stack_parts.append(f"issue-{args.issue_number}")
    stack_id = "-".join(p for p in stack_parts if p)

    modules_repo = (pins.get("modules") or {}).get("repository") or "OWNER/gh-platform-modules"
    tagging_ref = (pins.get("modules") or {}).get("tagging_ref") or "tagging/v0.0.0"
    module = product.get("module") or {}

    resolved = {
        "product": args.product,
        "environment": environment,
        "stack_id": stack_id,
        "stack_path": f"stacks/{stack_id}",
        "workload_repository": env_cfg["workload_repository"],
        "github_environment": env_cfg.get("github_environment", environment),
        "aws_role_arn": env_cfg["aws_role_arn"],
        "aws_region": env_cfg.get("aws_region", "us-east-1"),
        "aws_account_id": str(env_cfg.get("aws_account_id", "")),
        "tagging_environment": env_cfg.get("tagging_environment", "NON-PROD"),
        "modules_repository": modules_repo,
        "module_path": module.get("path", ""),
        "module_ref": module.get("ref", ""),
        "tagging_module_ref": tagging_ref,
        "template": product.get("template", args.product),
        "control_repo": args.control_repo,
        "issue_number": str(args.issue_number),
        "inputs": req,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps({"stack_id": stack_id, "workload_repository": resolved["workload_repository"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
