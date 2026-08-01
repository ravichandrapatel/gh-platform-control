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

## Secrets / variables (control repo)

| Name | Type | Value |
| --- | --- | --- |
| `CONTROL_CLIENT_ID` | Repository variable | GitHub App **Client ID** |
| `CONTROL_APP_PRIVATE_KEY` | Repository secret | PEM private key |

Workflow uses `actions/create-github-app-token` **v3** with `client-id` (legacy `app-id` is deprecated).

The mint step scopes the token to the target workload repository from `config/environments.yaml`.

## Cost

GitHub Apps are free. No hosted runner of your own is required beyond GitHub Actions minutes.
