# infra-prod (workload)

GitOps workload repo for the **prod** environment (own AWS account).

Copy this tree to `OWNER/infra-prod`, then replace placeholders and wire OIDC.

## Layout

```text
stacks/                     # IssueOps-generated OpenTofu roots
.github/workflows/tofu.yml  # Calls pinned tofu-pipeline
config/environment.yaml     # Role / region for this env
```

## Setup

1. Create empty repo `OWNER/infra-prod`.
2. Copy these files; set `OWNER`, actions SHA, and account/role ARN.
3. Add GitHub Environment `prod` with required reviewers.
4. OIDC trust: `repo:OWNER/infra-prod:environment:prod` → `gh-platform-prod` role.
5. Confirm control `config/environments.yaml` has the `prod` row.
6. Install the control GitHub App on this repo (contents + pull requests write).

## Status callback

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
