# Public demo hardening

`gh-platform-control` may be **public** for demos. That does **not** mean anyone should provision.

## Threat

On a public repo, any GitHub user can open Issues. If the Issue Form auto-applies
`issueops` labels, the provision workflow runs for strangers (Actions minutes, App
token mint, workload PRs).

## Controls in this repo

1. Issue Form labels are empty — maintainers add `issueops` after triage (product is chosen in the form; workflow syncs `product:*`).
2. `python3 -m gh_platform_control authorize` fails closed unless the **issue author** is in
   [`config/operators.yaml`](../config/operators.yaml) or has write+ on the control repo.
3. Workload repos (`infra-dev` / `infra-prod`) should stay **private**.
4. App private key stays in control Actions secrets (never in git).

## Operator checklist

1. Add demos users to `config/operators.yaml` (and grant write if you want collaborator path).
2. After a public user files a request you approve, either:
   - ask them to become a collaborator / be allowlisted, **or**
   - re-file the issue as yourself and label it (author must be authorized).
3. Prefer GitHub **Interaction limits** (Settings → Moderation) during busy demos.
