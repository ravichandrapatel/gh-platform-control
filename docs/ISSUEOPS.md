# IssueOps

Primary self-service paths for this control plane.

## Request (stack provision)

1. **Issues → New issue → Provision infrastructure** (single form; pick **Product** in the body).
2. An **authorized operator** labels the issue `issueops` (+ `status:pending-validation`).
   The public form does **not** auto-apply those labels (prevents drive-by provision on a public demo).
3. Workflow `issue-provision` runs with `issueops` **and** passes author authz
   (`config/operators.yaml` and/or repo write collaborator). Product comes from the form field;
   the workflow syncs `product:<id>` for filters.
4. On success: workload PR link, tracking Deployment id (`issueops-<env>`), label `status:pr-open`.
5. On failure: label `status:validation-failed` + run link.

## Request (environment onboard — EnvOps)

1. **Issues → New issue → Onboard environment** (slug, profile, AWS account/role/region).
2. Operator labels **`envops`** (same authz as stack IssueOps).
3. Workflow `issue-env-onboard` creates `infra-<env>`, applies ruleset/vars/secret, opens control PR
   `envops/<env>` for `environments.yaml` + regenerated provision form. Label `status:env-ready`.
4. If `infra-<env>` or the registry key already exists → **fail closed**.
5. AWS OIDC / state remain manual ([OIDC_AND_BACKEND.md](OIDC_AND_BACKEND.md)).

Labels: `python3 -m gh_platform_control bootstrap-labels` creates `issueops`, `envops`, and status labels.

## Runners (`tofu` vs `terragrunt`)

| Product | `runner` | Template | Workload needs |
| --- | --- | --- | --- |
| `s3-bucket` | `tofu` | OpenTofu root (`main.tf.tmpl`, …) | — |
| `s3-bucket-tg` | `terragrunt` | Thin `terragrunt.hcl.tmpl` | Repo-root `root.hcl` (see examples) |

Catalog field `runner` defaults to `tofu`. Pipeline auto-detects `terragrunt.hcl` in the stack dir.
Bucket uniqueness is shared across both S3 products in the same environment.

## Public demo security

| Control | Purpose |
| --- | --- |
| No auto `issueops` labels on the Issue Form | Random public users cannot trigger the workflow by opening a form |
| `config/operators.yaml` + collaborator write check | Issue **author** must be allowlisted or have write/maintain/admin |
| Private workload repos (`infra-*`) | Generated PRs land in private GitOps repos |
| GitHub App scoped to workload repos | Control never applies to AWS; App cannot be invoked without authz step |

Still treat public control as demo-only: rotate App credentials if leaked; keep AWS roles on private workloads.

### Control Environments vs workload Environments

| Repo | Environment name | Purpose |
| --- | --- | --- |
| `gh-platform-control` | `issueops-dev`, `issueops-prod` | **Tracking only** (issue ↔ PR status). No OIDC, no apply. |
| `infra-dev` / `infra-prod` | `dev` / `prod` | **Real deploy gates** + AWS OIDC. |

If control shows a bare `dev` Environment (“Ready to deploy to dev”), that was a mistaken
tracking name — remove it; new runs use `issueops-<env>` only.

## Natural key (Git source of truth)

Stack path and branch are **deterministic** from the product catalog (no issue suffix):

- Stack: `stacks/<product>-<bucket_name>/`
- Branch: `issueops/<product>-<bucket_name>`
- Natural key: `<product>:<environment>:<bucket_name>`

Environment scopes uniqueness (each env = its own workload repo / AWS account).  
Control **does not** query AWS for existence.

## Validation layers

| Layer | Where | What |
| --- | --- | --- |
| Form schema | Issue Form YAML | required fields, dropdowns |
| Catalog | `validate-request` | patterns, enums, env allowlist, natural-key stack id |
| Duplicate key | `check-duplicate` | control claim issues + open PRs + `main` |
| Control CI | `validate-control.sh` | registry + templates exist |
| Workload CI | `tofu-pipeline` | Checkov, plan, Conftest |
| Apply gate | Workload Environment + `confirm_apply` | human approval on prod |

## Uniqueness edge matrix

| Edge | Behavior |
| --- | --- |
| Different issue, same key, open control claim (`pending-validation` / `pr-open`) | **Fail** + comment on both issues (**attach**) |
| Different issue, same key, open workload PR | **Fail** + attach links / owner comment |
| Same key already on `main` (merged / deployed via GitOps) | **Fail** + attach link to `main` stack |
| Same issue re-run / edit | **Attach**: refresh stack on existing PR, keep one PR |
| Concurrent two issues (race) | Natural-key branch + ownership check; loser **fails** (or loses PR create) |
| Closed / unmerged PR (no open claim) | Allowed — key is free again |
| Failed issue left open (`validation-failed` / `config-error` / `provision-failed`) | Does **not** hold claim |
| Same bucket name in **different** environment | Allowed (different workload repo) |
| AWS orphan (exists in AWS, not in git) | **Non-goal** for GitHub-only control; catch at plan/apply |

Policy summary: **fail** for a different issue; **attach** cross-links on fail; **attach/reuse** for the same issue.

## Labels

| Label | Meaning |
| --- | --- |
| `issueops` | Intake issue |
| `product:s3-bucket` | Synced from form (OpenTofu S3) |
| `product:s3-bucket-tg` | Synced from form (Terragrunt S3) |
| `status:pending-validation` | Form submitted |
| `status:pr-open` | Workload PR opened |
| `status:plan-ok` / `plan-failed` | From `status-sync` |
| `status:applied` / `apply-failed` | From `status-sync` |
| `status:validation-failed` | Control rejected request |

## Bootstrap labels

```bash
PYTHONPATH=src python3 -m gh_platform_control bootstrap-labels OWNER/gh-platform-control
```

Creates `issueops`, `product:*`, and `status:*` labels (including `status:config-error` vs `status:validation-failed`).

## Failure labels

| Label | Meaning |
| --- | --- |
| `status:validation-failed` | Form/catalog/render/duplicate failed |
| `status:config-error` | Pins/App token/credentials failed |
| `status:provision-failed` | Workload PR or Deployment failed |

## Adding a product

1. `config/catalog/products/<id>.yaml` — inputs, `runner`, module pins, stack/uniqueness keys
2. `templates/<id>/*.tmpl`
3. Regenerate the Issue Form: `PYTHONPATH=src python3 -m gh_platform_control generate-issue-form`
4. Extend `check_duplicate_resource.py` if uniqueness is not `bucket_name`
5. `PYTHONPATH=src python3 -m gh_platform_control bootstrap-labels` for `product:<id>`
6. Terragrunt products: ensure workload examples ship `root.hcl`

Do **not** hand-edit `.github/ISSUE_TEMPLATE/provision.yml` — it is generated from the catalog + `environments.yaml`. CI runs `python3 -m gh_platform_control generate-issue-form --check`.
