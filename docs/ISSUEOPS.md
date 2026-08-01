# IssueOps

Primary self-service path for this control plane.

## Request

1. **Issues → New issue → Provision S3 bucket** (add products by cloning the form + catalog entry + template).
2. Workflow `issue-provision` runs when labels include `issueops` and `product:<id>`.
3. On success: workload PR link, Deployment id, label `status:pr-open`.
4. On failure: label `status:validation-failed` + run link.

## Validation layers

| Layer | Where | What |
| --- | --- | --- |
| Form schema | Issue Form YAML | required fields, dropdowns |
| Catalog | `scripts/validate_request.py` | patterns, enums, env allowlist |
| Control CI | `validate-control.sh` | registry + templates exist |
| Workload CI | `tofu-pipeline` | Checkov, plan, Conftest |
| Apply gate | Workload Environment + `confirm_apply` | human approval on prod |

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
| `status:validation-failed` | Form/catalog/render failed |
| `status:config-error` | Pins/App token/credentials failed |
| `status:provision-failed` | Workload PR or Deployment failed |

## Adding a product

1. `config/catalog/products/<id>.yaml`
2. `templates/<id>/*.tmpl`
3. `.github/ISSUE_TEMPLATE/<id>.yml` with labels `issueops` + `product:<id>`
4. Extend `issue-provision.yml` `if:` (or generalize product detection from labels).
5. `./scripts/bootstrap-labels.sh` for any new `product:*` label.
