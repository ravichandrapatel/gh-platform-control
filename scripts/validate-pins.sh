#!/usr/bin/env bash
# FILE: validate-pins.sh
# DESCRIPTION: Reject floating git refs in config/pins.yaml
# VERSION: 0.1.0
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PINS="${ROOT}/config/pins.yaml"
ALLOW_PLACEHOLDERS="${ALLOW_PIN_PLACEHOLDERS:-0}"

fail() { echo "ERROR: $*" >&2; exit 1; }

[[ -f "${PINS}" ]] || fail "missing ${PINS}"

refs="$(awk -F': ' '/^[[:space:]]*ref:/{print $2}' "${PINS}" | tr -d '"'"'"')"
[[ -n "${refs}" ]] || fail "no ref keys found in pins.yaml"

while IFS= read -r ref; do
  [[ -n "${ref}" ]] || continue
  case "${ref}" in
    main|master|HEAD|latest)
      fail "floating ref '${ref}' is forbidden"
      ;;
    REPLACE_WITH_ACTIONS_COMMIT_SHA|v0.0.0)
      if [[ "${ALLOW_PLACEHOLDERS}" == "1" ]]; then
        echo "WARN: placeholder ref '${ref}' allowed (ALLOW_PIN_PLACEHOLDERS=1)"
        continue
      fi
      fail "placeholder ref '${ref}' — set real pins before apply"
      ;;
  esac
  if [[ "${ref}" =~ ^[0-9a-f]{40}$ ]]; then
    continue
  fi
  if [[ "${ref}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([.-].*)?$ ]]; then
    continue
  fi
  fail "ref '${ref}' must be a 40-char SHA or SemVer tag (vX.Y.Z)"
done <<< "${refs}"

echo "OK: pins.yaml refs accepted"
