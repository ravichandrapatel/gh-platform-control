# Control GitHub App

Cross-repository PRs and EnvOps onboarding require a GitHub App (not a user PAT).

## Create

1. Org / user settings → Developer settings → GitHub Apps → New.
2. Name: `gh-platform-control` (or similar).
3. Permissions:

   **Stack IssueOps (minimum)**
   - Repository **Contents**: Read & write
   - Repository **Pull requests**: Read & write
   - Repository **Metadata**: Read

   **EnvOps onboard (additional)** — `issue-env-onboard.yml`
   - Repository **Administration**: Read & write (create repo + rulesets)
   - Repository **Environments**: Read & write
   - Repository **Secrets**: Read & write (Actions secrets)
   - Repository **Variables**: Read & write
   - Organization **Administration** (orgs only): Read & write — needed to **create** repositories under the org

4. Install on the **owner** (prefer **All repositories** so new `infra-*` repos are covered automatically). After changing permissions, click **Accept** on the installation.
5. Generate a private key. Copy the App **Client ID** (not the numeric App ID).

## Secrets / variables (**gh-platform-control** only)

These must be on the **control** repository (where IssueOps / EnvOps workflows run), not on workload repos.

| Name | Type | Value |
| --- | --- | --- |
| `CONTROL_CLIENT_ID` | Repository **variable** | GitHub App **Client ID** (e.g. `Iv23…`) |
| `CONTROL_APP_PRIVATE_KEY` | Repository **secret** | PEM private key |
| `MODULES_GIT_TOKEN` | Repository **secret** | Token with `contents:read` on `gh-platform-modules` — **copied** to new `infra-*` repos by EnvOps |

```bash
gh variable set CONTROL_CLIENT_ID -R OWNER/gh-platform-control --body 'Iv23…'
gh secret set CONTROL_APP_PRIVATE_KEY -R OWNER/gh-platform-control < app-private-key.pem
gh secret set MODULES_GIT_TOKEN -R OWNER/gh-platform-control --body 'ghp_…'
```

Workflow uses `actions/create-github-app-token` **v3** with `client-id` (legacy `app-id` is deprecated).

- **Stack provision:** mint scopes the token to the target workload from `config/environments.yaml`.
- **Env onboard:** mint uses installation scope for the owner (create repo + control registry PR).

Workloads do **not** need App credentials for intake.

## Cost

GitHub Apps are free. No hosted runner of your own is required beyond GitHub Actions minutes.
