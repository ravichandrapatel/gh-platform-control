# Control GitHub App

Cross-repository PRs, EnvOps onboarding, and **private module download** use a GitHub App (not a long-lived modules PAT).

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

4. Install on the **owner** (prefer **All repositories** so new `infra-*` repos and **`gh-platform-modules`** are covered). After changing permissions, click **Accept** on the installation.
5. Generate a private key. Copy the App **Client ID** (not the numeric App ID).

## Secrets / variables

### Control (`gh-platform-control`)

| Name | Type | Value |
| --- | --- | --- |
| `CONTROL_CLIENT_ID` | Repository **variable** | GitHub App **Client ID** (e.g. `Iv23…`) |
| `CONTROL_APP_PRIVATE_KEY` | Repository **secret** | PEM private key |
| `MODULES_GIT_TOKEN` | Repository **secret** (optional) | PAT fallback; EnvOps copies only if set |
| `CONTROL_USER_REPO_TOKEN` | Repository **secret** (personal accounts) | User PAT for `POST /user/repos` — **required** when control owner is a user; App installation tokens cannot create personal repos. Org owners use the App alone. |

```bash
gh variable set CONTROL_CLIENT_ID -R OWNER/gh-platform-control --body 'Iv23…'
gh secret set CONTROL_APP_PRIVATE_KEY -R OWNER/gh-platform-control < app-private-key.pem
```

### Workloads (`infra-*`) — set by EnvOps

| Name | Type | Purpose |
| --- | --- | --- |
| `CONTROL_CLIENT_ID` | Variable | Passed to `tofu-pipeline` / `drift-reconcile` as `control_app_client_id` |
| `MODULES_GIT_REPOSITORY` | Variable | `owner/gh-platform-modules` from `config/pins.yaml` |
| `CONTROL_APP_PRIVATE_KEY` | Secret | Mint short-lived installation token scoped to the modules repo |

Workflows use `actions/create-github-app-token` **v3** with `client-id` (legacy `app-id` is deprecated).

- **Stack provision:** mint scopes the token to the target workload from `config/environments.yaml`.
- **Env onboard:** mint uses installation scope for the owner (create repo + control registry PR); copies App client id / key / modules repo onto the new workload.
- **Module download (workload CI):** mint scopes to `MODULES_GIT_REPOSITORY` only.

## Cost

GitHub Apps are free. No hosted runner of your own is required beyond GitHub Actions minutes.

## Personal-account EnvOps limits

- Set `CONTROL_USER_REPO_TOKEN` (user PAT with `repo`) — App installation tokens cannot `POST /user/repos`.
- Repository **rulesets** and Environment **required reviewers** on private personal repos require GitHub Pro (or an org); EnvOps warns and continues if rulesets are blocked. See [WORKLOAD_RULESETS.md](WORKLOAD_RULESETS.md).
