# OIDC and OpenTofu state

## Auth (workload repos)

Use GitHub Actions OIDC → AWS IAM roles. Do **not** store long-lived access keys.

Trust each role on the **workload** repository (not control):

- `token.actions.githubusercontent.com:aud = sts.amazonaws.com`
- `sub` like `repo:OWNER/infra-dev:environment:dev`
- Separate role + trust for `repo:OWNER/infra-prod:environment:prod`

Wire ARNs in control `config/environments.yaml` and the workload
`config/environment.yaml` mirror.

Control IssueOps does **not** need AWS credentials.

## State backend

Prefer remote S3 backend with locking (`use_lockfile` or DynamoDB).

- Generated stacks include `backend "s3" {}` and an example `backend.hcl`.
- Real backend config stays in secured store / Actions variables — never commit secrets.
- Suggested key layout: `stacks/<stack_id>/terraform.tfstate` per account bucket.

Until accounts exist, local state is fine for dry validation only.
