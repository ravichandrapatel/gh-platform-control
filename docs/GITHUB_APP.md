# Control GitHub App

Cross-repository PRs require a GitHub App (not a user PAT).

## Create

1. Org settings → Developer settings → GitHub Apps → New.
2. Name: `gh-platform-control` (or similar).
3. Permissions:
   - Repository **Contents**: Read & write
   - Repository **Pull requests**: Read & write
   - Repository **Metadata**: Read
4. Install on:
   - `gh-platform-control` (optional)
   - every workload repo (`infra-dev`, `infra-prod`)
5. Generate a private key.

## Secrets / variables (control repo)

| Name | Type | Value |
| --- | --- | --- |
| `CONTROL_APP_ID` | Repository variable | App ID |
| `CONTROL_APP_PRIVATE_KEY` | Repository secret | PEM private key |

Workflow uses `actions/create-github-app-token` to mint a short-lived installation token.

## Cost

GitHub Apps are free. No hosted runner of your own is required beyond GitHub Actions minutes.
