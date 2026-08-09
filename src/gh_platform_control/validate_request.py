# FILE_NAME: validate_request.py
# DESCRIPTION: Validate parsed Issue Form JSON against catalog + environments.
# VERSION: 0.4.1
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from gh_platform_control.util import fail
from gh_platform_control.yamlutil import load_yaml_file

ALLOWED_RUNNERS = frozenset({"tofu", "terragrunt"})
# Product ids / template dirs must be single path segments (no traversal).
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
SAFE_STACK_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")


def load_product(catalog_dir: Path, product_id: str) -> dict:
    if not SAFE_ID_RE.fullmatch(product_id):
        fail(
            f"invalid product id {product_id!r} "
            "(expected lowercase alnum/hyphen, single path segment)"
        )
    path = (catalog_dir / f"{product_id}.yaml").resolve()
    try:
        path.relative_to(catalog_dir.resolve())
    except ValueError:
        fail(f"product path escapes catalog dir: {product_id}")
    if not path.is_file():
        fail(f"unknown product '{product_id}' (missing {path})")
    return load_yaml_file(str(path))


def slug_part(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def build_parts(product: dict, product_id: str, req: dict, keys: list[str]) -> list[str]:
    parts: list[str] = []
    for key in keys:
        if key == "product":
            parts.append(product_id)
        else:
            if key not in req or not str(req.get(key, "")).strip():
                fail(f"stack/natural key field '{key}' missing from request")
            parts.append(slug_part(str(req[key])))
    return [p for p in parts if p]


def validate_request(
    *,
    root: Path,
    req: dict,
    product_id: str,
    issue_number: str,
    control_repo: str,
) -> dict:
    """INTENT: Resolve catalog+env request into a stack plan.
    INPUT: Control root, parsed request, product, issue, control repo.
    OUTPUT: Resolved dict written by run() to --out.
    ROLE: IssueOps validation.
    SIDE_EFFECTS: Reads catalog/environments/pins YAML.
    """
    if not str(issue_number).isdigit():
        fail(f"issue-number must be digits, got {issue_number!r}")

    if not isinstance(req, dict):
        fail("request JSON must be an object")

    body_product = str(req.get("product", "")).strip()
    if not body_product:
        fail("product missing from request body (Issue Form Product is required)")
    if body_product != product_id:
        fail(f"product mismatch: --product={product_id!r} vs body={body_product!r}")

    product = load_product(root / "config/catalog/products", product_id)
    catalog_id = str(product.get("id") or "").strip()
    if catalog_id and catalog_id != product_id:
        fail(f"catalog id {catalog_id!r} does not match product file stem {product_id!r}")

    envs = load_yaml_file(str(root / "config/environments.yaml")).get("environments") or {}
    if not isinstance(envs, dict) or not envs:
        fail("no environments in config/environments.yaml")
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
        if enum is not None and not isinstance(enum, list):
            fail(f"input '{name}' enum must be a YAML list in catalog")
        if enum and val not in enum:
            fail(f"input '{name}'={val!r} not in {enum}")
        pattern = spec.get("pattern")
        if pattern and not re.fullmatch(pattern, val):
            fail(f"input '{name}'={val!r} failed pattern {pattern}")

    environment = str(req.get("environment", "")).strip()
    if not environment:
        fail("missing required input 'environment'")
    if environment not in envs:
        fail(f"environment '{environment}' not in config/environments.yaml")
    env_cfg = envs[environment]
    if not isinstance(env_cfg, dict):
        fail(f"environment '{environment}' must be a mapping")
    for key in ("workload_repository", "aws_role_arn"):
        if key not in env_cfg or not str(env_cfg.get(key, "")).strip():
            fail(f"environment '{environment}' missing {key}")

    stack_keys = product.get("stack_id_from") or ["product"]
    stack_parts = build_parts(product, product_id, req, stack_keys)
    stack_id = "-".join(stack_parts)
    if not SAFE_STACK_RE.fullmatch(stack_id):
        fail(f"derived stack_id {stack_id!r} is empty or unsafe")

    uniq_keys = product.get("uniqueness_key_from") or [
        k for k in stack_keys if k != "product"
    ]
    uniq_parts = build_parts(product, product_id, req, uniq_keys)
    natural_key = f"{product_id}:{environment}:{':'.join(uniq_parts)}"

    modules_repo = (pins.get("modules") or {}).get("repository") or "OWNER/gh-platform-modules"
    tagging_ref = (pins.get("modules") or {}).get("tagging_ref") or "tagging/v0.0.0"
    module = product.get("module") or {}

    runner = str(product.get("runner") or "tofu").strip().lower()
    if runner not in ALLOWED_RUNNERS:
        fail(f"product '{product_id}' runner={runner!r} not in {sorted(ALLOWED_RUNNERS)}")

    template = str(product.get("template") or product_id).strip()
    if not SAFE_ID_RE.fullmatch(template):
        fail(f"invalid template id {template!r}")

    return {
        "product": product_id,
        "environment": environment,
        "stack_id": stack_id,
        "stack_path": f"stacks/{stack_id}",
        "natural_key": natural_key,
        "uniqueness_inputs": {k: str(req.get(k, "")).strip() for k in uniq_keys if k != "product"},
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
        "template": template,
        "runner": runner,
        "control_repo": control_repo,
        "issue_number": str(issue_number),
        "inputs": req,
    }


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate parsed Issue Form JSON against catalog + environments."
    )
    parser.add_argument("--request-json", required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", required=True)
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--control-repo", required=True)
    args = parser.parse_args(argv)

    with open(args.request_json, encoding="utf-8") as f:
        req = json.load(f)

    resolved = validate_request(
        root=Path(args.root),
        req=req,
        product_id=args.product,
        issue_number=args.issue_number,
        control_repo=args.control_repo,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2, sort_keys=True)
        f.write("\n")
    print(
        json.dumps(
            {
                "stack_id": resolved["stack_id"],
                "natural_key": resolved["natural_key"],
                "workload_repository": resolved["workload_repository"],
            }
        )
    )
    return 0


def main() -> int:
    return run()
