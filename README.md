# gh-platform-control

**IssueOps control plane** for a zero-cost, GitHub-only internal developer platform (IDP).

- Authorized operators submit **Issue Forms** to request resources (public demos are gated).
- **EnvOps** onboards new `infra-<env>` repos (ruleset, Environment, variables, modules token) and opens a registry PR.
- Control **validates**, **generates** OpenTofu/Terragrunt stack roots, and **opens PRs** on per-env workload repos.
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

1. Replace placeholders in `config/pins.yaml` and seed `config/environments.yaml` (or onboard envs via EnvOps).
2. Install the control GitHub App ([docs/GITHUB_APP.md](docs/GITHUB_APP.md)); set `MODULES_GIT_TOKEN` on control.
3. Onboard workloads: **Issues → Onboard environment** → label `envops` (or copy [`examples/infra-dev/`](examples/infra-dev/) manually).
4. Wire OIDC on **workload** repos ([docs/OIDC_AND_BACKEND.md](docs/OIDC_AND_BACKEND.md)).
5. Add yourself to [`config/operators.yaml`](config/operators.yaml).
6. Open **Issues → Provision infrastructure**, pick Product, then label `issueops`.

## Docs

| Doc | Topic |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Control vs workload split |
| [docs/DAY_OPERATIONS.md](docs/DAY_OPERATIONS.md) | **Day-to-day runbook** (provision, pins, releases, demo) |
| [docs/ISSUEOPS.md](docs/ISSUEOPS.md) | Forms, labels, validation |
| [docs/PUBLIC_DEMO.md](docs/PUBLIC_DEMO.md) | Public-repo IssueOps hardening |
| [docs/WORKLOAD_REPOS.md](docs/WORKLOAD_REPOS.md) | Env workload layout |
| [docs/WORKLOAD_RULESETS.md](docs/WORKLOAD_RULESETS.md) | Workload `main` rulesets — no admin bypass for new stacks |
| [docs/GITHUB_APP.md](docs/GITHUB_APP.md) | Cross-repo PR bot |
| [docs/OIDC_AND_BACKEND.md](docs/OIDC_AND_BACKEND.md) | AWS auth + state |
| [docs/BRANCHING.md](docs/BRANCHING.md) | Branch protection |
| [docs/GITHUB_RULESETS.md](docs/GITHUB_RULESETS.md) | Rulesets |

## Local checks

```bash
export PYTHONPATH=src
ALLOW_PIN_PLACEHOLDERS=1 python3 -m gh_platform_control validate-pins
ALLOW_PLACEHOLDERS=1 python3 -m gh_platform_control validate-control
python3 -m gh_platform_control --help
```

App package: `src/gh_platform_control/` (stdlib, flat modules). Workflows set `PYTHONPATH=src`.
