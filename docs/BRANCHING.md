# Security branching rules — gh-platform-control

## Model

**Trunk-based development** with a single long-lived branch: `main`.

All production-relevant history lands on `main` only through pull requests. Direct pushes, force-pushes, and branch deletion on `main` are forbidden (enforce with GitHub Rulesets after the remote exists — see [GITHUB_RULESETS.md](GITHUB_RULESETS.md)).

## Allowed branch names

| Pattern | Purpose |
| --- | --- |
| `feature/<ticket-or-slug>` | New capability |
| `fix/<ticket-or-slug>` | Bug fix |
| `chore/<slug>` | Tooling, deps, CI |
| `docs/<slug>` | Documentation only |
| `security/<slug>` | Vulnerability fix / hardening |

Forbidden: committing directly to `main`; long-lived personal branches; `tmp` / `wip` without a PR within 7 days.

## Control-plane-specific rules

- \`config/pins.yaml\` changes are security-sensitive: require CODEOWNER review.
- Never set \`modules_ref\` or \`actions_ref\` to \`main\` / \`master\` / \`latest\`.
- \`apply\` / \`destroy\` workflows MUST use GitHub Environments with required reviewers.
- Prefer \`workflow_dispatch\` for mutating operations; avoid push-to-main auto-apply.

## Pull request requirements

1. PR from an allowed branch into `main` (never the reverse for feature work).
2. At least **one** approving review from a CODEOWNER (dismiss stale reviews on new commits).
3. All required status checks green.
4. Conversations resolved before merge.
5. **Squash merge** preferred (linear history on `main`).
6. No merge commits from untrusted forks without review of every commit.

## Tags and releases

- Create **annotated** SemVer tags only from commits already on `main`.
- Never retag / move a published tag; cut a new patch instead.
- Floating refs (`main`, `latest`) are **not** valid pins for consumers.

## Local developer rules

1. `git checkout -b feature/<slug>` from up-to-date `main`.
2. Keep commits small; do not commit secrets, `.env`, or cloud keys.
3. Open a PR; do not push to `main`.
4. After merge, delete the feature branch.

## Secrets and credentials

- Never store AWS keys in the repo.
- Prefer GitHub OIDC → IAM roles.
- Rotation / incidents: revoke, rotate, then open a `security/` PR documenting impact.
