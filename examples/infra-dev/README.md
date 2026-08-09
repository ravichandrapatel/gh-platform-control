# infra-dev (workload)

GitOps workload repo for the **dev** environment (own AWS account).

Copy this tree to `OWNER/infra-dev`, then replace placeholders and wire OIDC.

## Layout

```text
stacks/                      # Onboarded stacks (edit OK; new dirs via IssueOps only)
root.hcl                     # Terragrunt remote state + provider (TG products)
.github/workflows/tofu.yml   # guard-new-stacks action + tofu-pipeline (actions SHA)
.github/workflows/drift.yml  # Drift report + stamp PR (create/update only)
config/environment.yaml      # Role / region for this env
```

## Setup

1. Create empty repo `OWNER/infra-dev`.
2. Copy these files; set `OWNER`, actions SHA, and account/role ARN.
3. Add GitHub Environment `dev` (optional reviewers).
4. OIDC trust: `repo:OWNER/infra-dev:environment:dev` → `gh-platform-dev` role.
5. Confirm control `config/environments.yaml` has the `dev` row.
6. Install the control GitHub App on this repo (contents + pull requests write).
7. Copy `drift.yml`; pin the same actions SHA as `tofu.yml`. Ensure OIDC trust allows
   schedule/dispatch on `main` (detect has no Environment gate). Dev sets
   `open_reconcile_pr: true` — destroy plans stay report-only.

## Drift

Weekday cron opens/updates **Infrastructure Drift Report**. Safe (create/update) drift also
opens `drift/reconcile` stamp PR → normal plan → Environment-gated apply. Any destroy →
issue only. See [drift-reconcile](https://github.com/ravichandrapatel/gh-platform-actions/blob/main/docs/workflows/drift-reconcile.md).

## Status callback

Notify control after plan/apply (same payload shape as other workloads):

```bash
gh api --method POST \
  -H "Accept: application/vnd.github+json" \
  "/repos/OWNER/gh-platform-control/dispatches" \
  -f event_type=issueops_status \
  -f client_payload[issue_number]=123 \
  -f client_payload[state]=plan_ok \
  -f client_payload[deployment_id]=456 \
  -f client_payload[log_url]="$RUN_URL"
```
