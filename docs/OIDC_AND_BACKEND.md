# OIDC and OpenTofu state (scaffold)

## Auth

Use GitHub Actions OIDC → AWS IAM roles. Do **not** store long-lived access keys in GitHub secrets.

Condition the role trust on:

- `token.actions.githubusercontent.com:aud = sts.amazonaws.com`
- `sub` like `repo:OWNER/gh-platform-control:environment:sandbox` (and a separate role for `prod`)

Wire `aws_role_arn` in `config/environments/*.yaml`.

## State backend

Prefer a remote S3 backend with locking (S3 native lock or DynamoDB). Place backend config outside git secrets:

- Example file: `config/backend.hcl.example`
- Real `backend.hcl` stays local / in a secured store — never commit account-specific secrets.

Until AWS accounts exist, Commons/`tofu init` may use local state for dry validation only.
