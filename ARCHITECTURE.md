# gh-platform-control architecture

Zero-cost, GitHub-only IDP control plane. **One** control repo for intake;
**per-env workload repos** (one AWS account each) own OpenTofu roots and apply.

## Layers

| Repo | Role | Release unit |
| --- | --- | --- |
| `gh-platform-control` | IssueOps intake, catalog, pins, codegen, status | Config + workflows on `main` |
| `infra-<env>` (workload) | GitOps stacks + `tofu-pipeline` CI | Protected `main` per account |
| `gh-platform-actions` | Reusable `tofu-pipeline` + policies | Commit SHA |
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
3. Control renders `templates/<product>/` into `stacks/<id>/` on the target workload repo.
4. Control opens a PR (GitHub App) and creates a GitHub Deployment (`queued`).
5. Workload CI calls pinned `tofu-pipeline` (plan on PR; apply after merge + Environment gate).
6. Workload notifies control via `repository_dispatch`; control updates the issue + Deployment.

Control **never** assumes AWS roles for apply. OIDC trust lives on the workload repo.

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
