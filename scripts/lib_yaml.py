# FILE_NAME: lib_yaml.py
# DESCRIPTION: Minimal YAML subset loader (stdlib only) for control config.
# VERSION: 0.1.0
from __future__ import annotations

import re
from typing import Any


def load_simple_yaml(text: str) -> Any:
    """Parse a constrained YAML subset used by this repo (mappings, lists, scalars)."""
    lines = text.splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    def parse_scalar(raw: str) -> Any:
        s = raw.strip()
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
        if s.startswith("'") and s.endswith("'"):
            return s[1:-1]
        if s in ("true", "True"):
            return True
        if s in ("false", "False"):
            return False
        if s in ("null", "~", ""):
            return None
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        return s

    for lineno, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ValueError(f"line {lineno}: indent underflow")

        parent = stack[-1][1]

        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"line {lineno}: list item under non-list")
            item_raw = content[2:].strip()
            if ": " in item_raw or item_raw.endswith(":"):
                raise ValueError(f"line {lineno}: nested list maps not supported")
            parent.append(parse_scalar(item_raw))
            continue

        if ":" not in content:
            raise ValueError(f"line {lineno}: expected key:")

        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest == "":
            # Peek: next non-empty line decides list vs map
            nxt = None
            for peek in lines[lineno:]:
                if not peek.strip() or peek.lstrip().startswith("#"):
                    continue
                nxt = peek
                break
            if nxt is not None and nxt.strip().startswith("- "):
                node: Any = []
            else:
                node = {}
            if isinstance(parent, dict):
                parent[key] = node
            else:
                raise ValueError(f"line {lineno}: map key under non-map")
            stack.append((indent, node))
            continue

        value = parse_scalar(rest)
        if isinstance(parent, dict):
            parent[key] = value
        else:
            raise ValueError(f"line {lineno}: scalar under non-map")

    return root


def load_yaml_file(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return load_simple_yaml(f.read())
