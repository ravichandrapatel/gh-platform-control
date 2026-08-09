# FILE_NAME: render.py
# DESCRIPTION: Render product templates into a stack directory.
# VERSION: 0.2.0
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def render(text: str, mapping: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in mapping:
            raise KeyError(f"missing template variable {{{{{key}}}}}")
        return mapping[key]

    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", repl, text)


def render_stack(*, root: Path, resolved: dict, out_dir: Path) -> int:
    """INTENT: Materialize template files for a resolved stack.
    INPUT: Control root, resolved request dict, output directory.
    OUTPUT: 0 on success, 1 on error.
    ROLE: Stack codegen.
    SIDE_EFFECTS: Writes files under out_dir.
    """
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

    template = str(resolved.get("template") or "").strip()
    if not SAFE_ID_RE.fullmatch(template):
        print(f"ERROR: invalid template id {template!r}", file=sys.stderr)
        return 1

    templates_root = (root / "templates").resolve()
    tmpl_dir = (templates_root / template).resolve()
    try:
        tmpl_dir.relative_to(templates_root)
    except ValueError:
        print(f"ERROR: template path escapes templates/: {template}", file=sys.stderr)
        return 1
    if not tmpl_dir.is_dir():
        print(f"ERROR: missing template dir {tmpl_dir}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    for src in sorted(tmpl_dir.iterdir()):
        if not src.is_file() or src.name.startswith("."):
            continue
        name = src.name
        if name.endswith(".tmpl"):
            name = name[: -len(".tmpl")]
        if "/" in name or name in (".", ".."):
            print(f"ERROR: refusing unsafe template filename {src.name!r}", file=sys.stderr)
            return 1
        content = render(src.read_text(encoding="utf-8"), mapping)
        (out_dir / name).write_text(content, encoding="utf-8")
        print(f"wrote {out_dir / name}")

    meta = {
        "product": resolved["product"],
        "environment": resolved["environment"],
        "issue": f"{resolved['control_repo']}#{resolved['issue_number']}",
        "stack_id": resolved["stack_id"],
        "runner": str(resolved.get("runner") or "tofu"),
        "natural_key": resolved.get("natural_key"),
        "uniqueness_inputs": resolved.get("uniqueness_inputs") or {},
        "bucket_name": str(inputs.get("bucket_name", "")),
    }
    (out_dir / "stack-metadata.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render product templates into a stack directory."
    )
    parser.add_argument("--resolved-json", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    with open(args.resolved_json, encoding="utf-8") as f:
        resolved = json.load(f)
    return render_stack(
        root=Path(args.root),
        resolved=resolved,
        out_dir=Path(args.out_dir),
    )


def main() -> int:
    return run()
