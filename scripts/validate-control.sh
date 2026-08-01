#!/usr/bin/env bash
# FILE_NAME: validate-control.sh
# DESCRIPTION: Validate environments registry, catalog products, and templates.
# VERSION: 0.1.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALLOW_PLACEHOLDERS="${ALLOW_PLACEHOLDERS:-0}"
cd "${ROOT}"

fail() { echo "ERROR: $*" >&2; exit 1; }

[[ -f config/environments.yaml ]] || fail "missing config/environments.yaml"
[[ -d config/catalog/products ]] || fail "missing config/catalog/products"
[[ -d templates ]] || fail "missing templates/"

python3 - <<'PY'
from __future__ import annotations
import os
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
from lib_yaml import load_yaml_file

allow = os.environ.get("ALLOW_PLACEHOLDERS", "0") == "1"
root = Path(".")
envs = load_yaml_file("config/environments.yaml").get("environments") or {}
if not envs:
    raise SystemExit("ERROR: no environments defined")

required_env_keys = (
    "workload_repository",
    "github_environment",
    "aws_role_arn",
    "aws_region",
    "tagging_environment",
)

for name, cfg in envs.items():
    if not isinstance(cfg, dict):
        raise SystemExit(f"ERROR: environment {name} must be a mapping")
    for key in required_env_keys:
        if key not in cfg:
            raise SystemExit(f"ERROR: environment {name} missing {key}")
    repo = str(cfg["workload_repository"])
    role = str(cfg["aws_role_arn"])
    if not allow:
        if "OWNER" in repo or "REPLACE" in repo:
            raise SystemExit(f"ERROR: placeholder workload_repository for {name}")
        if "REPLACE" in role:
            raise SystemExit(f"ERROR: placeholder aws_role_arn for {name}")

products = list(Path("config/catalog/products").glob("*.yaml"))
if not products:
    raise SystemExit("ERROR: no catalog products")

for path in products:
    prod = load_yaml_file(str(path))
    for key in ("id", "template", "inputs", "module"):
        if key not in prod:
            raise SystemExit(f"ERROR: {path} missing {key}")
    tmpl = Path("templates") / str(prod["template"])
    if not tmpl.is_dir():
        raise SystemExit(f"ERROR: template dir missing for {prod['id']}: {tmpl}")
    if not any(tmpl.glob("*.tmpl")):
        raise SystemExit(f"ERROR: no .tmpl files in {tmpl}")
    mod = prod["module"]
    if not isinstance(mod, dict) or "path" not in mod or "ref" not in mod:
        raise SystemExit(f"ERROR: {path} module needs path+ref")
    if not allow and str(mod["ref"]).endswith("/v0.0.0"):
        raise SystemExit(f"ERROR: placeholder module.ref in {path}")

print(f"OK: {len(envs)} environments, {len(products)} products")
PY

echo "OK: control config accepted"
