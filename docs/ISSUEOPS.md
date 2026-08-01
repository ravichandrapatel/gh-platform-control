# IssueOps

Primary self-service path for this control plane.

## Request

1. **Issues → New issue → Provision S3 bucket** (add products by cloning the form + catalog entry + template).
2. Workflow `issue-provision` runs when labels include `issueops` and `product:<id>`.
3. On success: workload PR link, Deployment id, label `status:pr-open`.
4. On failure: label `status:validation-failed` + run link.

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
| Catalog | `scripts/validate_request.py` | patterns, enums, env allowlist, natural-key stack id |
| Duplicate key | `scripts/check_duplicate_resource.py` | control claim issues + open PRs + `main` |
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
| `product:s3-bucket` | Product router |
| `status:pending-validation` | Form submitted |
| `status:pr-open` | Workload PR opened |
| `status:plan-ok` / `plan-failed` | From `status-sync` |
| `status:applied` / `apply-failed` | From `status-sync` |
| `status:validation-failed` | Control rejected request |

## Bootstrap labels

```bash
./scripts/bootstrap-labels.sh OWNER/gh-platform-control
```

Creates `issueops`, `product:*`, and `status:*` labels (including `status:config-error` vs `status:validation-failed`).

## Failure labels

| Label | Meaning |
| --- | --- |
| `status:validation-failed` | Form/catalog/render/duplicate failed |
| `status:config-error` | Pins/App token/credentials failed |
| `status:provision-failed` | Workload PR or Deployment failed |

## Adding a product

1. `config/catalog/products/<id>.yaml` — set `stack_id_from` + `uniqueness_key_from`
2. `templates/<id>/*.tmpl`
3. `.github/ISSUE_TEMPLATE/<id>.yml` with labels `issueops` + `product:<id>`
4. Extend `issue-provision.yml` `if:` (or generalize product detection from labels).
5. Extend `check_duplicate_resource.py` if the product’s natural key is not `bucket_name`.
6. `./scripts/bootstrap-labels.sh` for any new `product:*` label.
