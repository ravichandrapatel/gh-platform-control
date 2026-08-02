# gh-platform-control architecture

Zero-cost, GitHub-only IDP control plane. **One** control repo for intake;
**per-env workload repos** (one AWS account each) own OpenTofu roots and apply.

## Layers

| Repo | Role | Release unit |
| --- | --- | --- |
| `gh-platform-control` | IssueOps intake, catalog, pins, codegen, status | Config + workflows on `main` |
| `infra-<env>` (workload) | GitOps stacks + `tofu-pipeline` + `drift-reconcile` | Protected `main` per account |
| `gh-platform-actions` | Reusable `tofu-pipeline`, `drift-reconcile`, policies | Commit SHA |
| `gh-platform-modules` | OpenTofu modules | Annotated SemVer tags (`s3/vX.Y.Z`) |

## Flow

```text
Issue Form → validate → render template → GitHub App PR → workload CI
                                                              ↓
                                         Checkov → plan → Conftest → gated apply
                                                              ↓
                              status-sync ← repository_dispatch ← workload
                                         → issue labels + Deployment
```

1. Operator opens an Issue Form (product + environment + params).
2. Control parses the body, validates against `config/catalog/` + `config/environments.yaml`.
3. Control renders `templates/<product>/` into a **natural-key** stack path
   (`stacks/<product>-<key>/`) on the target workload repo (no issue suffix).
4. Uniqueness: fail+attach if the key is claimed by another open control issue,
   an open workload PR, or `main`. Same-issue re-runs attach/reuse one PR.
5. Control opens a PR (GitHub App) and a **tracking** Deployment named `issueops-<env>`
   (status only — not an AWS deploy; do not put protection rules here).
6. Workload CI calls pinned `tofu-pipeline` (plan on PR; apply after merge + Environment gate).
7. Workload notifies control via `repository_dispatch`; control updates the issue + Deployment.
8. Day-2: workload cron runs pinned `drift-reconcile` — Drift Report issue; **dev** may open a
   create/update-only stamp PR; **prod** is report-only; any destroy stays human-triaged.
   Control never plans or applies for drift.

Control **never** assumes AWS roles for apply. OIDC trust and real GitHub Environments
(`dev` / `prod`) live on the **workload** repos (`infra-<env>`), not on control.


## Config map

| Path | Purpose |
| --- | --- |
| `config/pins.yaml` | Immutable `gh-platform-actions` SHA |
| `config/environments.yaml` | env → workload repo, account, role, region |
| `config/catalog/products/*.yaml` | Product allowlists + module pin hints |
| `templates/<product>/` | Codegen skeletons |
| `examples/infra-dev/`, `examples/infra-prod/` | Workload starters (dev + prod only) |

## Extensibility

MVP unit is **environment = AWS account**. Add rows to `environments.yaml` (and later
team/product dimensions) without copying this control plane.

## Break-glass

Do not run OpenTofu inside this repo. Emergency changes: PR directly on the
workload repo (same `tofu-pipeline` gates).
