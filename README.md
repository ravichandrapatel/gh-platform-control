# gh-platform-control

**IssueOps control plane** for a zero-cost, GitHub-only internal developer platform (IDP).

- Users submit **Issue Forms** to request resources.
- Control **validates**, **generates** OpenTofu stack roots, and **opens PRs** on per-env workload repos (`infra-dev` / `infra-prod`).
- Workloads run pinned **`tofu-pipeline`** (plan/apply) in their own AWS account via OIDC.
- Control **updates issue + Deployment status** from workload callbacks.

Does **not** vendor module/action source or apply infrastructure itself.

## Related repos

| Repo | What it does |
| --- | --- |
| [`gh-platform-modules`](https://github.com/ravichandrapatel/gh-platform-modules) | Versioned OpenTofu/AWS modules (IaC library) |
| [`gh-platform-actions`](https://github.com/ravichandrapatel/gh-platform-actions) | Reusable `tofu-pipeline` + Conftest policies |
| **This repo** | Intake, catalog, codegen, pins, env→workload registry |

## Quick start (after remotes exist)

1. Replace `OWNER` / placeholders in `config/pins.yaml` and `config/environments.yaml`.
2. Create workload repos from [`examples/infra-dev/`](examples/infra-dev/) and [`examples/infra-prod/`](examples/infra-prod/).
3. Install the control GitHub App ([docs/GITHUB_APP.md](docs/GITHUB_APP.md)).
4. Wire OIDC on **workload** repos ([docs/OIDC_AND_BACKEND.md](docs/OIDC_AND_BACKEND.md)).
5. Open **Issues → New → Provision S3 bucket**.

## Docs

| Doc | Topic |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Control vs workload split |
| [docs/ISSUEOPS.md](docs/ISSUEOPS.md) | Forms, labels, validation |
| [docs/WORKLOAD_REPOS.md](docs/WORKLOAD_REPOS.md) | Env workload layout |
| [docs/GITHUB_APP.md](docs/GITHUB_APP.md) | Cross-repo PR bot |
| [docs/OIDC_AND_BACKEND.md](docs/OIDC_AND_BACKEND.md) | AWS auth + state |
| [docs/BRANCHING.md](docs/BRANCHING.md) | Branch protection |
| [docs/GITHUB_RULESETS.md](docs/GITHUB_RULESETS.md) | Rulesets |

## Local checks

```bash
ALLOW_PIN_PLACEHOLDERS=1 ./scripts/validate-pins.sh
ALLOW_PLACEHOLDERS=1 ./scripts/validate-control.sh
```
