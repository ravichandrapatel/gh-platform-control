# FILE_NAME: cli.py
# DESCRIPTION: argparse subcommands for gh-platform-control.
# VERSION: 0.1.0
from __future__ import annotations

import argparse
import importlib
import sys


DISPATCH: dict[str, tuple[str, str]] = {
    "authorize": ("gh_platform_control.authz", "run"),
    "parse-issue": ("gh_platform_control.parse", "run"),
    "validate-request": ("gh_platform_control.validate_request", "run"),
    "validate-env": ("gh_platform_control.validate_env", "run"),
    "render-stack": ("gh_platform_control.render", "run"),
    "check-duplicate": ("gh_platform_control.duplicate", "run"),
    "generate-issue-form": ("gh_platform_control.generate_form", "run"),
    "validate-pins": ("gh_platform_control.pins", "run"),
    "validate-control": ("gh_platform_control.control_config", "run"),
    "scaffold-infra": ("gh_platform_control.scaffold", "run"),
    "patch-environments": ("gh_platform_control.patch_environments", "run"),
    "open-workload-pr": ("gh_platform_control.workload_pr", "run"),
    "onboard-environment": ("gh_platform_control.env_onboard", "run"),
    "open-env-registry-pr": ("gh_platform_control.env_registry_pr", "run"),
    "bootstrap-labels": ("gh_platform_control.labels", "run"),
}


def main(argv: list[str] | None = None) -> int:
    """INTENT: Dispatch CLI subcommands to module run() handlers.
    INPUT: Optional argv (defaults to sys.argv[1:]).
    OUTPUT: Process exit code.
    ROLE: Package CLI entry.
    SIDE_EFFECTS: Delegates to subcommand modules.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="gh_platform_control",
        description="GitHub-only IDP control plane (IssueOps / EnvOps).",
    )
    parser.add_argument(
        "command",
        choices=sorted(DISPATCH.keys()),
        help="Subcommand to run",
    )
    # Parse only the command token so module argparse owns flags/--help.
    if not args or args[0] in ("-h", "--help"):
        parser.print_help()
        return 0 if args else 2

    command = args[0]
    if command not in DISPATCH:
        parser.error(f"invalid command {command!r}")

    rest = args[1:]
    mod_name, attr = DISPATCH[command]
    mod = importlib.import_module(mod_name)
    return int(getattr(mod, attr)(rest))
