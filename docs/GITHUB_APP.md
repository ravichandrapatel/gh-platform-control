# Control GitHub App

Cross-repository PRs require a GitHub App (not a user PAT).

## Create

1. Org / user settings → Developer settings → GitHub Apps → New.
2. Name: `gh-platform-control` (or similar).
3. Permissions:
   - Repository **Contents**: Read & write
   - Repository **Pull requests**: Read & write
   - Repository **Metadata**: Read
4. Install on every workload repo (`infra-dev`, `infra-prod`, …).
5. Generate a private key. Copy the App **Client ID** (not the numeric App ID).

## Secrets / variables (**gh-platform-control** only)

These must be on the **control** repository (where `issue-provision` runs), not on workload repos.

| Name | Type | Value |
| --- | --- | --- |
| `CONTROL_CLIENT_ID` | Repository **variable** | GitHub App **Client ID** (e.g. `Iv23…`) |
| `CONTROL_APP_PRIVATE_KEY` | Repository **secret** | PEM private key |

```bash
gh variable set CONTROL_CLIENT_ID -R OWNER/gh-platform-control --body 'Iv23…'
gh secret set CONTROL_APP_PRIVATE_KEY -R OWNER/gh-platform-control < app-private-key.pem
```

Workflow uses `actions/create-github-app-token` **v3** with `client-id` (legacy `app-id` is deprecated).

The mint step scopes the token to the target workload repository from `config/environments.yaml`.
Workloads do **not** need these App credentials for IssueOps intake.

## Cost

GitHub Apps are free. No hosted runner of your own is required beyond GitHub Actions minutes.
