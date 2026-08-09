# gh-platform-control architecture

Zero-cost, GitHub-only IDP control plane. **One** control repo for intake;
**per-env workload repos** (one AWS account each) own OpenTofu / thin Terragrunt
stacks and apply.

## Layers

| Repo | Role | Release unit |
| --- | --- | --- |
| `gh-platform-control` | IssueOps/EnvOps intake (`src/gh_platform_control`), catalog, pins, codegen, status | Config + workflows on `main` |
| `infra-<env>` (workload) | GitOps stacks + `tofu-pipeline` + `drift-reconcile` | Protected `main` per account |
| `gh-platform-actions` | Reusable `tofu-pipeline`, `drift-reconcile`, policies | Commit **SHA** |
| `gh-platform-modules` | OpenTofu modules | Annotated SemVer tags (`s3/vX.Y.Z`) |

## Dual runners

| Catalog `runner` | Stack layout | Workload CI |
| --- | --- | --- |
| `tofu` (default) | Rendered OpenTofu root (`main.tf`, …) | `tofu-pipeline` (`iac_tool: auto`) |
| `terragrunt` | Thin `terragrunt.hcl` + repo `root.hcl` | Same pipeline; detects `terragrunt.hcl` |

Demo products: `s3-bucket` (tofu) and `s3-bucket-tg` (terragrunt). Bucket uniqueness is
env-scoped across both. No Gruntwork live `dependency` graphs in v1.

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
| `config/catalog/products/*.yaml` | Product allowlists + module pin + `runner` |
| `templates/<product>/` | Codegen skeletons |
| `examples/infra-dev/`, `examples/infra-prod/` | Workload starters (dev + prod only; include `root.hcl` for TG) |

## Extensibility

MVP unit is **environment = AWS account**. Prefer **EnvOps** (Onboard environment Issue Form +
`envops` label) to create `infra-<env>`, ruleset, variables, and a control PR that adds the
`environments.yaml` row. Manual registry edits remain supported.

## Break-glass

Do not run OpenTofu inside the **control** repo.

- **Day-2 value changes** on onboarded stacks: users (and owners) PR edits under existing `stacks/<id>/`.
- **New stacks:** IssueOps only (`issueops/*` branch). No human DIY create — including owners/admins. Enforce with `guard-new-stacks` + rulesets that **deny admin bypass** ([docs/WORKLOAD_RULESETS.md](docs/WORKLOAD_RULESETS.md)).
- Apply still goes through workload `tofu-pipeline` + Environment gates.
