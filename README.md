# gh-platform-control

Thin **control plane** for gh-platform: scripts, dispatch workflows, pins, OIDC/environment wiring.

Does **not** vendor module or action source for runtime — it pins immutable refs from:

- `gh-platform-modules`
- `gh-platform-actions`

## Security branching

See [docs/BRANCHING.md](docs/BRANCHING.md). Apply [docs/GITHUB_RULESETS.md](docs/GITHUB_RULESETS.md) after the remote exists.

## Quick map

See [ARCHITECTURE.md](ARCHITECTURE.md).
