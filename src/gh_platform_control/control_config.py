# FILE_NAME: control_config.py
# DESCRIPTION: Validate environments registry, catalog products, and templates.
# VERSION: 0.2.0
from __future__ import annotations

import argparse
import os
from pathlib import Path

from gh_platform_control.generate_form import write_or_check
from gh_platform_control.util import fail
from gh_platform_control.yamlutil import load_yaml_file


def validate_control(root: Path, *, allow_placeholders: bool = False) -> None:
    """INTENT: Validate environments, catalog products, templates, and Issue Form.
    INPUT: Control repo root; whether placeholders are allowed.
    OUTPUT: None (raises via fail on error).
    ROLE: Control-plane config gate.
    SIDE_EFFECTS: Reads config/templates; may regenerate-check Issue Form.
    """
    if not (root / "config/environments.yaml").is_file():
        fail("missing config/environments.yaml")
    if not (root / "config/catalog/products").is_dir():
        fail("missing config/catalog/products")
    if not (root / "templates").is_dir():
        fail("missing templates/")

    envs = load_yaml_file(str(root / "config/environments.yaml")).get("environments") or {}
    if not envs:
        fail("no environments defined")

    required_env_keys = (
        "workload_repository",
        "github_environment",
        "aws_role_arn",
        "aws_region",
        "tagging_environment",
    )

    for name, cfg in envs.items():
        if not isinstance(cfg, dict):
            fail(f"environment {name} must be a mapping")
        for key in required_env_keys:
            if key not in cfg:
                fail(f"environment {name} missing {key}")
        repo = str(cfg["workload_repository"])
        role = str(cfg["aws_role_arn"])
        if not allow_placeholders:
            if "OWNER" in repo or "REPLACE" in repo:
                fail(f"placeholder workload_repository for {name}")
            if "REPLACE" in role:
                fail(f"placeholder aws_role_arn for {name}")

    products = list((root / "config/catalog/products").glob("*.yaml"))
    if not products:
        fail("no catalog products")

    for path in products:
        prod = load_yaml_file(str(path))
        for key in ("id", "template", "inputs", "module"):
            if key not in prod:
                fail(f"{path} missing {key}")
        if str(prod["id"]) != path.stem:
            fail(f"{path} id={prod['id']!r} must match filename stem {path.stem!r}")
        runner = str(prod.get("runner") or "tofu").strip().lower()
        if runner not in ("tofu", "terragrunt"):
            fail(f"{path} runner={runner!r} must be tofu or terragrunt")
        tmpl = root / "templates" / str(prod["template"])
        if not tmpl.is_dir():
            fail(f"template dir missing for {prod['id']}: {tmpl}")
        if not any(tmpl.glob("*.tmpl")):
            fail(f"no .tmpl files in {tmpl}")
        if runner == "terragrunt" and not (tmpl / "terragrunt.hcl.tmpl").is_file():
            fail(f"terragrunt product {prod['id']} missing terragrunt.hcl.tmpl in {tmpl}")
        if runner == "tofu" and not any(
            p.name.endswith(".tf.tmpl") for p in tmpl.iterdir() if p.is_file()
        ):
            fail(f"tofu product {prod['id']} missing *.tf.tmpl in {tmpl}")
        mod = prod["module"]
        if not isinstance(mod, dict) or "path" not in mod or "ref" not in mod:
            fail(f"{path} module needs path+ref")
        if not allow_placeholders and str(mod["ref"]).endswith("/v0.0.0"):
            fail(f"placeholder module.ref in {path}")

    print(f"OK: {len(envs)} environments, {len(products)} products")

    # Issue Form must be generated from catalog + environments (not hand-edited).
    write_or_check(root, check=True)
    print("OK: control config accepted")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate environments registry, catalog products, and templates."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="Allow placeholder repos/roles/module refs (also via ALLOW_PLACEHOLDERS=1)",
    )
    args = parser.parse_args(argv)
    allow = (
        os.environ.get("ALLOW_PLACEHOLDERS", "0") == "1" or bool(args.allow_placeholders)
    )
    validate_control(Path(args.root), allow_placeholders=allow)
    return 0


def main() -> int:
    return run()
