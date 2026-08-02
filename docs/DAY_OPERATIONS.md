# Day-to-day platform operations

Operator runbook for the GitHub-only IDP: **control → workload → AWS**.

Use this as the daily reference. Deep dives stay in the linked docs.

---

## 1. What you are operating

```text
Operator (allowlisted)
        │
        ▼
gh-platform-control          Issue Form → validate → codegen → App PR
        │                    tracking Deployment: issueops-<env>
        ▼
infra-<env> (private)        PR plan (validate→plan→OPA) → merge → apply
        │                    tofu-pipeline@pinned-SHA
        ▼
AWS account for that env     OIDC role; S3 state per stack
```

| Repo | Visibility (demo) | Daily role |
| --- | --- | --- |
| `gh-platform-control` | Public OK | Intake, catalog, pins, operators |
| `gh-platform-actions` | Public OK | Reusable multi-stage pipeline + Conftest |
| `gh-platform-modules` | Public or private | SemVer modules (`s3/vX.Y.Z`) |
| `infra-dev` / `infra-prod` | **Private** | GitOps truth + real deploy Environments |

Control **never** applies to AWS. Workloads own OIDC, state, and Environment approvals.

---

## 2. Morning checklist (healthy platform)

- [ ] You (or the demo presenter) are in [`config/operators.yaml`](../config/operators.yaml).
- [ ] Control secrets present: `CONTROL_CLIENT_ID` (variable), `CONTROL_APP_PRIVATE_KEY` (secret). See [GITHUB_APP.md](GITHUB_APP.md).
- [ ] Workload secret `MODULES_GIT_TOKEN` set (read access to module repo). See [tofu-pipeline module download](../../gh-platform-actions/docs/workflows/tofu-pipeline.md).
- [ ] Workload GitHub Environments `dev` / `prod` exist (protection on prod as needed).
- [ ] Pins are immutable SHAs/tags — no `main` / `latest` in [`config/pins.yaml`](../config/pins.yaml).
- [ ] Control Environments page shows only `issueops-*` tracking envs (not bare `dev` as a deploy target). See [ISSUEOPS.md](ISSUEOPS.md).

Local sanity:

```bash
cd gh-platform-control
ALLOW_PIN_PLACEHOLDERS=1 ./scripts/validate-pins.sh
ALLOW_PLACEHOLDERS=1 ./scripts/validate-control.sh
```

---

## 3. Provision a resource (happy path)

### 3.1 Who may request

| Step | Rule |
| --- | --- |
| Open Issue Form | Anyone on a public control repo (form alone does **not** provision) |
| Start automation | Issue must be labeled `issueops` + `product:<id>` |
| Author authz | Issue **author** must be in `config/operators.yaml` **or** have write/maintain/admin on control |

See [PUBLIC_DEMO.md](PUBLIC_DEMO.md).

### 3.2 Steps

1. **Issues → New issue → Provision S3 bucket** (or another product form).
2. Fill environment (`dev` / `prod`), inputs; submit.
3. As an authorized operator, add labels:
   - `issueops`
   - `product:s3-bucket` (match the product)
   - `status:pending-validation` (optional but useful)
4. Watch Actions → `issue-provision`.
5. On success:
   - Issue comment with workload PR URL
   - Label `status:pr-open`
   - Tracking Deployment under `issueops-<env>`
6. On the **workload** PR:
   - CI runs `tofu-pipeline`: **validate** → **plan** (+ OPA) — no Environment wait on plan
   - Review plan; merge when green
7. On merge to workload `main`:
   - **apply** job runs (Environment gate / reviewers on prod)
8. When workload status callbacks exist, control labels move to `status:plan-ok` / `status:applied` via `status-sync` ([ISSUEOPS.md](ISSUEOPS.md)).

### 3.3 Natural key (idempotency)

| Concept | Value (S3 example) |
| --- | --- |
| Natural key | `s3-bucket:<env>:<bucket_name>` |
| Stack path | `stacks/s3-bucket-<bucket_name>/` |
| Branch | `issueops/s3-bucket-<bucket_name>` |

| Situation | Result |
| --- | --- |
| Other open claim (issue / PR / `main`) | **Fail** + attach links on both issues |
| Same issue re-edited | **Attach** — refresh same PR |
| Same name, different env | Allowed (different workload repo) |
| Closed unmerged PR | Name free again |
| Exists only in AWS, not in git | Not checked by control (Git is SoT) |

### 3.4 Drift detection (day-2)

Workload cron (`drift.yml`) calls pinned **`drift-reconcile`** — control never plans or applies.

| Env | Report issue | Stamp PR (`drift/reconcile`) |
| --- | --- | --- |
| `infra-dev` | Yes | Yes — **create/update only** |
| `infra-prod` | Yes | **No** (report only) |

| Plan class | What to do |
| --- | --- |
| Safe (create/update) | Dev: review/merge stamp PR → Environment-gated apply. Prod: open a human PR. |
| Destroy (any delete) | **Never** auto-PR. Triage ClickOps vs Git; explicit workload PR if destroy is intentional. |
| Clean | Drift issue / stale stamp PR closed |

`tofu-pipeline` also runs Conftest **deny destroy** on any PR whose head branch starts with `drift/`.

Docs: [drift-reconcile](https://github.com/ravichandrapatel/gh-platform-actions/blob/main/docs/workflows/drift-reconcile.md).

---

## 4. Day labels cheat sheet

| Label | Meaning |
| --- | --- |
| `issueops` | Eligible for provision workflow |
| `product:s3-bucket` | Product router |
| `status:pending-validation` | Submitted / waiting |
| `status:pr-open` | Workload PR opened |
| `status:plan-ok` / `plan-failed` | From workload callback |
| `status:applied` / `apply-failed` | From workload callback |
| `status:validation-failed` | Authz, form, catalog, duplicate, etc. |
| `status:config-error` | Pins / App credentials |
| `status:provision-failed` | PR or Deployment create failed |

Bootstrap: `./scripts/bootstrap-labels.sh OWNER/gh-platform-control`

---

## 5. Release a new module version (e.g. S3)

Modules release as per-module SemVer tags: `{module}/vX.Y.Z` (example `s3/v1.1.0`).  
Release process lives in `gh-platform-modules` ([MODULE_RELEASE.md](https://github.com/ravichandrapatel/gh-platform-modules/blob/main/docs/MODULE_RELEASE.md) when present).

### 5.1 Ship the module

1. PR to `gh-platform-modules` `main`.
2. Releaser cuts tag e.g. `s3/v1.1.0`.
3. Confirm tag exists:

```bash
gh api repos/ravichandrapatel/gh-platform-modules/git/refs/tags/s3/v1.1.0 --jq .ref
```

### 5.2 Point control at the new tag (new requests only)

**Product module** (S3, etc.):

```yaml
# config/catalog/products/s3-bucket.yaml
module:
  path: s3
  ref: s3/v1.1.0    # was s3/v1.0.0
```

**Shared tagging module** (all products):

```yaml
# config/pins.yaml
modules:
  repository: ravichandrapatel/gh-platform-modules
  tagging_ref: tagging/v1.1.0
```

4. Open a PR on **control** (CODEOWNERS / pin review).
5. Merge to `main`.

### 5.3 Existing stacks

Catalog pins do **not** rewrite stacks already on `infra-*`. Those still have:

```hcl
source = "git::https://github.com/.../gh-platform-modules.git//s3?ref=s3/v1.0.0"
```

To upgrade an existing stack:

- Prefer a dedicated change PR on the workload repo (bump `ref=`), **or**
- Re-run IssueOps only if your process regenerates that stack intentionally (same natural key → attach/fail rules still apply).

---

## 6. Release a new actions / pipeline version

Pipeline lives in `gh-platform-actions` (`.github/workflows/tofu-pipeline.yml`). Consumers pin a **40-character commit SHA**.

### 6.1 Ship the pipeline

1. PR → `main` on `gh-platform-actions` (ruleset may require review).
2. Note merge commit SHA:

```bash
gh api repos/ravichandrapatel/gh-platform-actions/commits/main --jq .sha
```

### 6.2 Update control pin

```yaml
# config/pins.yaml
actions:
  repository: ravichandrapatel/gh-platform-actions
  ref: <40-char-sha>
```

```bash
./scripts/validate-pins.sh   # must pass (no floating refs)
```

### 6.3 Update every workload caller

The pin in `pins.yaml` is the **source of truth for docs/examples**, but live workloads hardcode the SHA in their workflow:

| Location | Update |
| --- | --- |
| `examples/infra-dev/.github/workflows/tofu.yml` | `uses: .../tofu-pipeline.yml@<sha>` |
| `examples/infra-prod/.github/workflows/tofu.yml` | same |
| Live `infra-dev` / `infra-prod` `.github/workflows/tofu.yml` | same (PR or controlled push) |

Also keep:

```yaml
permissions:
  contents: read
  id-token: write
  actions: write          # plan artifact between jobs
secrets:
  modules_git_token: ${{ secrets.MODULES_GIT_TOKEN }}
```

### 6.4 Verify

1. Open a small PR on `infra-dev` that touches a stack.
2. Confirm jobs: `validate` → `plan` (OPA) run; Environment approval only on apply after merge.

---

## 7. Pin map (where truth lives)

| Pin | File | Format | Affects |
| --- | --- | --- | --- |
| Actions pipeline | `config/pins.yaml` → `actions.ref` | 40-char SHA | Docs + should match workload `uses:` |
| Tagging module | `config/pins.yaml` → `modules.tagging_ref` | `tagging/vX.Y.Z` | New IssueOps codegen |
| Product module | `config/catalog/products/<id>.yaml` → `module.ref` | `<module>/vX.Y.Z` | New IssueOps codegen |
| Workload pipeline | `infra-*/.github/workflows/tofu.yml` | same SHA as actions pin | Actual CI |
| Operators | `config/operators.yaml` | GitHub logins | Who may provision |
| Env → repo/account | `config/environments.yaml` | registry rows | Where PRs go |

Forbidden: `main`, `master`, `latest`, `HEAD` as pins ([`validate-pins.sh`](../scripts/validate-pins.sh)).

---

## 8. Workload CI stages (what you see in Actions)

| Job | Contents | Environment gate? |
| --- | --- | --- |
| `validate` | `tofu fmt -check`, `init -backend=false`, `validate`, Checkov | No |
| `plan` | Full `init`, `plan`, Conftest/OPA, upload `tfplan` | No |
| `apply` | Download plan, `apply` | **Yes** (`dev` / `prod` on workload) |

Caller: `command: plan` on PR; `command: apply` + `confirm_apply: APPLY` on `main` push.

Details: [gh-platform-actions tofu-pipeline.md](https://github.com/ravichandrapatel/gh-platform-actions/blob/main/docs/workflows/tofu-pipeline.md).

---

## 9. Add a new product (rare day task)

1. Module released in `gh-platform-modules` with tag.
2. `config/catalog/products/<id>.yaml` — inputs, `module.path` / `module.ref`, `stack_id_from`, `uniqueness_key_from`.
3. `templates/<id>/*.tmpl` — codegen.
4. `.github/ISSUE_TEMPLATE/<id>.yml` — **no** auto `issueops` labels.
5. Extend `issue-provision.yml` `if:` (or generalize product detection).
6. Extend `check_duplicate_resource.py` if uniqueness is not `bucket_name`.
7. `./scripts/bootstrap-labels.sh` for `product:<id>`.
8. Document in [ISSUEOPS.md](ISSUEOPS.md).

---

## 10. Add / change an environment

MVP: **one env = one AWS account = one workload repo**.

1. Create `infra-<env>` from [`examples/infra-dev/`](../examples/infra-dev/) (or prod).
2. Wire OIDC + backend ([OIDC_AND_BACKEND.md](OIDC_AND_BACKEND.md)).
3. Install GitHub App on that repo ([GITHUB_APP.md](GITHUB_APP.md)).
4. Add row to [`config/environments.yaml`](../config/environments.yaml).
5. Add Environment option to Issue Forms.
6. Set `MODULES_GIT_TOKEN` on the workload repo.

---

## 11. Public demo day

1. Keep workloads **private**; control may be public.
2. Confirm Issue Form has **empty** `labels:` (no auto `issueops`).
3. Presenter login is in `operators.yaml`.
4. Narrate: open form → label → PR → plan → merge → apply.
5. Optional: GitHub interaction limits during the talk ([PUBLIC_DEMO.md](PUBLIC_DEMO.md)).
6. Do not paste App private keys or `MODULES_GIT_TOKEN` into slides/chat.

---

## 12. Troubleshooting (fast)

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Form opened, nothing runs | No `issueops` / `product:*` labels | Add labels (authorized author) |
| `authorization` failure | Author not in operators / no write | Add login to `operators.yaml` or grant write |
| `status:config-error` | Missing App var/secret | Set `CONTROL_CLIENT_ID` / `CONTROL_APP_PRIVATE_KEY` on **control** |
| PR create fails | App missing Pull requests: write | Update App permissions; re-accept install on workload |
| Duplicate validation-failed | Natural key claimed | Close/merge existing claim or pick new name |
| Module download fails in validate | Missing `MODULES_GIT_TOKEN` | Set secret; pass `modules_git_token` in caller |
| Plan waits on Environment | Old single-job pipeline pin | Bump to multi-stage SHA (`validate`/`plan` without env) |
| Control shows “Ready to deploy to dev” | Bare `dev` Environment on control | Use `issueops-dev` tracking only; delete bare `dev` |
| Existing stack still on old module | Catalog bump doesn’t rewrite git | PR bump `ref=` on workload stack |

---

## 13. Break-glass

- Do **not** run OpenTofu inside `gh-platform-control`.
- Emergency infra change: PR directly on `infra-<env>` (same pipeline gates).
- Compromised App key: rotate App private key; update `CONTROL_APP_PRIVATE_KEY`; revoke old key in App settings.

---

## 14. Doc index

| Doc | When to open it |
| --- | --- |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | System shape |
| [ISSUEOPS.md](ISSUEOPS.md) | Labels, uniqueness, validation layers |
| [PUBLIC_DEMO.md](PUBLIC_DEMO.md) | Public control hardening |
| [WORKLOAD_REPOS.md](WORKLOAD_REPOS.md) | Workload layout + secrets |
| [GITHUB_APP.md](GITHUB_APP.md) | Cross-repo PR bot |
| [OIDC_AND_BACKEND.md](OIDC_AND_BACKEND.md) | AWS auth + state |
| [BRANCHING.md](BRANCHING.md) / [GITHUB_RULESETS.md](GITHUB_RULESETS.md) | Branch protection |
| This file | Daily operations |

---

## 15. End-of-day closeout

- [ ] No stray open IssueOps claims you meant to close (`status:pr-open` with abandoned PRs).
- [ ] Pin PRs merged or parked with clear owners.
- [ ] No secrets committed; `gh secret list` only for expected names.
- [ ] If you demoed, note any allowlist users to remove from `operators.yaml`.
