# FILE_NAME: generate_form.py
# DESCRIPTION: Generate .github/ISSUE_TEMPLATE/provision.yml from catalog + environments.
# VERSION: 0.2.0
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from gh_platform_control.util import fail
from gh_platform_control.yamlutil import load_yaml_file

OUT_REL = Path(".github/ISSUE_TEMPLATE/provision.yml")
REGEN_CMD = "PYTHONPATH=src python3 -m gh_platform_control generate-issue-form"
CHECK_CMD = "PYTHONPATH=src python3 -m gh_platform_control generate-issue-form --check"


def load_products(catalog_dir: Path) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for path in sorted(catalog_dir.glob("*.yaml")):
        prod = load_yaml_file(str(path))
        if not isinstance(prod, dict) or not prod.get("id"):
            fail(f"{path}: missing id")
        # Normalize enums early (stdlib YAML subset requires block lists).
        inputs = prod.get("inputs") or {}
        if isinstance(inputs, dict):
            for name, spec in inputs.items():
                if not isinstance(spec, dict):
                    continue
                enum = spec.get("enum")
                if enum is not None and not isinstance(enum, list):
                    fail(
                        f"{path}: inputs.{name}.enum must be a YAML list "
                        f'(e.g. enum:\\n  - "true"), not inline JSON'
                    )
        products.append(prod)
    if not products:
        fail(f"no products under {catalog_dir}")
    return sorted(products, key=lambda p: str(p["id"]))


def yaml_quote(value: str) -> str:
    """Emit a YAML double-quoted scalar when needed for Issue Form options."""
    if value in ("true", "false", "null", "yes", "no") or any(
        c in value for c in (":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|", ">", "'", '"', "%", "@", "`")
    ):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def humanize(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


def merge_input_specs(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Union of catalog inputs (excluding environment — sourced from environments.yaml).

    Form-level `required` is true only when *every* product defines the input and
    marks it required. Product-specific fields stay optional on the shared form;
    `validate-request` still enforces per-product required inputs.
    """
    merged: dict[str, dict[str, Any]] = {}
    product_ids = [str(p["id"]) for p in products]
    for prod in products:
        inputs = prod.get("inputs") or {}
        if not isinstance(inputs, dict):
            fail(f"product {prod['id']}: inputs must be a mapping")
        for name, spec in inputs.items():
            if name == "environment":
                continue
            if not isinstance(spec, dict):
                fail(f"product {prod['id']}: input {name} must be a mapping")
            if name not in merged:
                merged[name] = dict(spec)
                merged[name]["_products"] = [prod["id"]]
                merged[name]["_required_products"] = (
                    [prod["id"]] if spec.get("required") else []
                )
                continue
            prev = merged[name]
            prev["_products"].append(prod["id"])
            if spec.get("required"):
                prev.setdefault("_required_products", []).append(prod["id"])
            if spec.get("enum") is not None:
                enum = spec["enum"]
                if not isinstance(enum, list):
                    fail(
                        f"product {prod['id']}: input {name} enum must be a YAML list "
                        f"(use block style under enum:), got {type(enum).__name__}"
                    )
                if prev.get("enum") is not None and list(prev["enum"]) != list(enum):
                    fail(
                        f"input {name!r} enum mismatch across products "
                        f"{prev['_products']}: {prev.get('enum')} vs {enum}"
                    )
                prev["enum"] = list(enum)
            if spec.get("pattern") is not None:
                if prev.get("pattern") is not None and prev["pattern"] != spec["pattern"]:
                    fail(
                        f"input {name!r} pattern mismatch across products "
                        f"{prev['_products']}"
                    )
                prev["pattern"] = spec["pattern"]
            if spec.get("description") and not prev.get("description"):
                prev["description"] = spec["description"]
            if spec.get("placeholder") and not prev.get("placeholder"):
                prev["placeholder"] = spec["placeholder"]
            if spec.get("label") and not prev.get("label"):
                prev["label"] = spec["label"]
    for name, spec in list(merged.items()):
        enum = spec.get("enum")
        if enum is not None and not isinstance(enum, list):
            fail(f"input {name!r}: enum must be a YAML list, got {type(enum).__name__}")
        owners = list(spec.pop("_products", []))
        required_owners = list(spec.pop("_required_products", []))
        # Shared-required only: every catalog product defines + requires this input.
        spec["required"] = (
            set(owners) == set(product_ids) and set(required_owners) == set(product_ids)
        )
        if owners and not spec["required"]:
            only = ", ".join(f"`{p}`" for p in owners)
            hint = f"Used by: {only}."
            desc = str(spec.get("description") or "").strip()
            spec["description"] = f"{desc} {hint}".strip() if desc else hint
    return merged


def render_form(
    *,
    products: list[dict[str, Any]],
    env_names: list[str],
    inputs: dict[str, dict[str, Any]],
) -> str:
    products = sorted(products, key=lambda p: str(p["id"]))
    product_ids = [str(p["id"]) for p in products]
    lines: list[str] = [
        "# GENERATED FILE — do not edit by hand.",
        "# Source of truth: config/catalog/products/*.yaml + config/environments.yaml",
        f"# Regenerate: {REGEN_CMD}",
        f"# Check drift: {CHECK_CMD}",
        "name: Provision infrastructure",
        "description: Request a catalog product (authorized operators only — public demo is gated).",
        'title: "[provision] "',
        "# Do NOT auto-apply issueops labels — maintainers add: issueops, status:pending-validation",
        "labels: []",
        "body:",
        "  - type: markdown",
        "    attributes:",
        "      value: |",
        "        **Public demo gate:** opening this form does **not** start provisioning.",
        "        An authorized operator must label the issue with `issueops` (and be listed in",
        "        `config/operators.yaml` or have write access on this repo).",
        "",
        "        **Product** and **Environment** options are generated from the control catalog",
        "        and `config/environments.yaml`. Flow: validate → codegen → GitOps PR.",
        "",
        "        Catalog products:",
    ]
    for p in products:
        title = str(p.get("title") or p["id"])
        runner = str(p.get("runner") or "tofu")
        desc = str(p.get("description") or "").strip()
        extra = f" — {desc}" if desc else ""
        lines.append(f"        - `{p['id']}` ({title}, runner={runner}){extra}")

    lines.extend(
        [
            "  - type: dropdown",
            "    id: product",
            "    attributes:",
            "      label: Product",
            "      description: Catalog product id (see list above).",
            "      options:",
        ]
    )
    for pid in product_ids:
        lines.append(f"        - {yaml_quote(pid)}")
    lines.extend(
        [
            "    validations:",
            "      required: true",
            "  - type: dropdown",
            "    id: environment",
            "    attributes:",
            "      label: Environment",
            "      description: Maps to an AWS account + workload repository.",
            "      options:",
        ]
    )
    for name in env_names:
        lines.append(f"        - {yaml_quote(name)}")
    lines.extend(
        [
            "    validations:",
            "      required: true",
        ]
    )

    # Stable field order: shared keys first, then product-specific alpha.
    preferred = (
        "project",
        "bucket_name",
        "enable_versioning",
        "vpc_name",
        "cidr_block",
        "create_nat_gateway",
        "cluster_name",
        "enable_container_insights",
        "secret_name",
        "secret_description",
    )
    ordered = [k for k in preferred if k in inputs] + sorted(
        k for k in inputs if k not in preferred
    )

    for name in ordered:
        spec = inputs[name]
        label = str(spec.get("label") or humanize(name))
        description = str(spec.get("description") or "").strip()
        required = bool(spec.get("required"))
        enum = spec.get("enum")

        if isinstance(enum, list) and enum:
            lines.extend(
                [
                    "  - type: dropdown",
                    f"    id: {name}",
                    "    attributes:",
                    f"      label: {label}",
                ]
            )
            if description:
                lines.append(f"      description: {description}")
            lines.append("      options:")
            for opt in enum:
                lines.append(f"        - {yaml_quote(str(opt))}")
            lines.append("      default: 0")
            lines.extend(
                [
                    "    validations:",
                    f"      required: {'true' if required else 'false'}",
                ]
            )
            continue

        lines.extend(
            [
                "  - type: input",
                f"    id: {name}",
                "    attributes:",
                f"      label: {label}",
            ]
        )
        if description:
            lines.append(f"      description: {description}")
        elif spec.get("pattern"):
            lines.append(f"      description: Must match `{spec['pattern']}`.")
        if spec.get("placeholder"):
            lines.append(f"      placeholder: {spec['placeholder']}")
        lines.extend(
            [
                "    validations:",
                f"      required: {'true' if required else 'false'}",
            ]
        )

    return "\n".join(lines) + "\n"


def build(root: Path) -> str:
    products = load_products(root / "config/catalog/products")
    envs = load_yaml_file(str(root / "config/environments.yaml")).get("environments") or {}
    if not isinstance(envs, dict) or not envs:
        fail("no environments in config/environments.yaml")
    env_names = sorted(str(k) for k in envs.keys())
    inputs = merge_input_specs(products)
    return render_form(products=products, env_names=env_names, inputs=inputs)


def write_or_check(root: Path, *, check: bool) -> int:
    out = root / OUT_REL
    rendered = build(root)

    if check:
        if not out.is_file():
            fail(f"missing {out}; run: {REGEN_CMD}")
        existing = out.read_text(encoding="utf-8")
        if existing != rendered:
            fail(
                f"{out} is out of date with catalog/environments. "
                f"Run: {REGEN_CMD}"
            )
        print(f"OK: {out} matches catalog + environments")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    print(f"wrote {out}")
    return 0


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate .github/ISSUE_TEMPLATE/provision.yml from catalog + environments."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if provision.yml does not match catalog/environments",
    )
    args = parser.parse_args(argv)
    return write_or_check(Path(args.root), check=args.check)


def main() -> int:
    return run()
