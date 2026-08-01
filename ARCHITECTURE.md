# gh-platform architecture

## Repos

| Repo | Layer | Release unit |
| --- | --- | --- |
| `gh-platform-modules` | IaC (OpenTofu) | Annotated SemVer tags |
| `gh-platform-actions` | Commons + Actions + reusable workflows | Commit SHA or immutable tags |
| `gh-platform-control` | Deployment / control | Config + workflows on `main` |

## Flow

1. Operator runs `workflow_dispatch` on control (`plan` / `apply` / `destroy`).
2. Control reads `config/pins.yaml` (or workflow inputs that must match allowed pins).
3. Control checks out `gh-platform-actions` at `actions_ref` (SHA).
4. Action runs Commons → checks out `gh-platform-modules` at `modules_ref` (tag).
5. OpenTofu `plan` by default; `apply`/`destroy` require `confirm_apply=APPLY` + Environment approval.

## Bumping pins

1. Release modules tag from `gh-platform-modules` `main`.
2. Merge actions changes; note the commit SHA on `gh-platform-actions` `main`.
3. Open a PR on **this** repo updating `config/pins.yaml`.
4. Merge via protected `main`; then run `plan` before any `apply`.
