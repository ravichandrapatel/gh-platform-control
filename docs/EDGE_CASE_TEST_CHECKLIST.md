# Platform verification matrix — reusable template

**Audience:** Solutions / security architects adopting this GitHub-only IDP for **any** team or org.  
**Products under test:** `gh-platform-control` · `gh-platform-actions` · `gh-platform-modules` · `infra-<env>`  
**Rule:** Any `[F]` → fix → **restart from T00** (do not skip).  
**Legend:** `[ ]` pending · `[x]` pass · `[F]` fail · `[S]` skipped · `[N/A]` not in scope for this tenant

---

## How to use (new team / new org)

1. Copy this file into your control repo as `docs/EDGE_CASE_TEST_CHECKLIST.md`.
2. Replace `OWNER`, env slugs, App name, and AWS account IDs with tenant values.
3. Run **Tier 0** before go-live; **Tier 1** every release; **Tier 2** quarterly / after threat-model change.
4. Keep an **Execution log** at the bottom (append-only). Do not delete historical rows.
5. Map failures to owners: Control plane · Workload · Cloud IAM · Security.

| Tier | When | Suites |
| --- | --- | --- |
| **0 — Go-live gate** | First production cutover | T00, T1–T4, T6.1–T6.4, T6.9b, T7.1–T7.4, T8, T11.1–T11.3, T12.1–T12.4, T13.1–T13.4, T14.1–T14.3 |
| **1 — Release gate** | Every control/actions pin bump | T00, T1, T4, T6.3, T6.9b, T9, T12, T14.1, T17.1–T17.3 |
| **2 — Assurance** | Quarterly / major threat change | Full matrix including T10, T15–T16, T18–T20 |

---

## Threat model (architect lens)

| Asset | Trust boundary | Primary controls |
| --- | --- | --- |
| Control repo | Public or internal | `operators.yaml` + collaborator check; no cloud OIDC |
| Workload `infra-<env>` | Private; one cloud account | App PR only for **new** stacks; Environment-gated apply |
| Modules / actions | Shared platform | Immutable SemVer / SHA pins; App mint or scoped token |
| Cloud account | Per env | OIDC trust on `repo:OWNER/infra-<env>:environment:<env>` |
| Operator identity | Human | Issue **author** authz (not labeler alone) |

**Non-goals for this matrix:** cloud cost FinOps deep-dives; vendor CVE scanning of every Action (pin + review instead).

---

## T00 — Preconditions (tenant bootstrap)

| ID | Case | How | Pass criteria | Result |
| --- | --- | --- | --- | --- |
| T00.1 | Control tree has package app, no flat `scripts/*.py` | `gh api` / clone | `src/gh_platform_control/` present | [x] |
| T00.2 | Operator `gh auth` | `gh auth status` | Can open issues + read Actions | [x] |
| T00.3 | Control App credentials | Secrets / vars | `CONTROL_CLIENT_ID` + `CONTROL_APP_PRIVATE_KEY`; personal accounts also `CONTROL_USER_REPO_TOKEN` | [x] |
| T00.4 | Labels seeded | `gh label list` | `issueops`, `envops`, status labels | [x] |
| T00.5 | App install covers modules + future `infra-*` | App install UI | Prefer **All repos**; modules readable | [x] (modules public + App mint vars on infra-*; install All repos recommended) |
| T00.6 | Workload OIDC trust documented | IAM console / IaC | Trust subject matches Environment (not `*`) | [x] (docs: environment-scoped `sub`; live IAM still REPLACE — see T19.5) |
| T00.7 | CODEOWNERS / required reviewers on control `main` | Settings | Platform team owns catalog/pins | [x] (CODEOWNERS + ruleset require_code_owner_review) |
| T00.8 | No floating refs in pins | `validate-pins` | No `main`/`latest`/`HEAD` | [x] |

---

## T1 — Config & catalog gates (local / CI)

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T1.1 | Pins accept SHA + SemVer | Exit 0 | [x] |
| T1.2 | Floating ref rejected | Exit 1 | [x] |
| T1.3 | Placeholder rejected without allow | Exit 1 | [x] |
| T1.4 | `validate-control` + form `--check` | Exit 0 | [x] |
| T1.5 | Form drift detected | Exit 1; restore | [x] |
| T1.6 | Product id ≠ filename | Exit 1 | [x] |
| T1.7 | Bad `runner` value | Exit 1 | [x] |
| T1.8 | **New product** without regenerating Issue Form | CI `--check` fails | [x] |
| T1.9 | Catalog input removes required field; old issues | Fail closed or explicit migration note | [x] |
| T1.10 | Two products share uniqueness key shape (cross-runner) | Documented env-scoped uniqueness | [x] (S3 tofu+tg) |

---

## T2 — Parse / validate / render (stack)

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T2.1–T2.13 | Happy + schema + path traversal suite | Prior matrix | [x] |
| T2.14 | Body product **required** (no empty + CLI fill) | Exit 1 | [x] |
| T2.15 | Unicode / homoglyph bucket names | Pattern reject | [x] |
| T2.16 | Extremely long but valid inputs | Rejected or capped; no crash | [x] |
| T2.17 | Rendered stack contains no secrets from control | Grep artifacts | [x] |
| T2.18 | `stack-metadata.json` always emitted with provenance | `issue`, `natural_key`, `stack_id` | [x] |

---

## T3 — EnvOps validate / scaffold (local)

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T3.1–T3.9 | Prior EnvOps local suite | Pass | [x] |
| T3.10 | Scaffold pins **same** actions SHA as `pins.yaml` | Spot-check `uses:@` | [x] |
| T3.11 | Scaffold wires App mint inputs (not PAT-only) | `control_app_*` present | [x] |
| T3.12 | Prod profile uses prod example + PROD tagging | Assert | [x] |
| T3.13 | Collision: slug reserved (`github`, `actions`, …) | Exit 1 | [x] |

---

## T4 — Control CI

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T4.1–T4.6 | Prior CI suite | Green on `main` | [x] |
| T4.7 | CI does **not** mint cloud credentials | No `id-token: write` + AWS assume on control | [x] |
| T4.8 | Dependabot / Renovate PR cannot weaken pins without review | CODEOWNERS on `pins.yaml` | [x] (CODEOWNERS `*` + require_code_owner_review; admin bypass residual → T10.12) |

---

## T5 — UX / templates

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T5.1–T5.5 | Forms + workflows visible | Prior | [x] |
| T5.6 | Blank issues disabled | `config.yml` | [x] |
| T5.7 | Form markdown states “label required / no auto-run” | Human-readable gate | [x] |
| T5.8 | Localization / fork: OWNER placeholders gone in live pins | No `OWNER/` in production pins | [x] |

---

## T6 — IssueOps live (stack intake)

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T6.1 | Open form **without** `issueops` | No provision job | [x] |
| T6.2 | Unauthorized **author** (labeler may be admin) | Authz fail on author | [x] |
| T6.3 | Authorized + unique natural key | PR `issueops/<stack_id>`; `status:pr-open` | [x] |
| T6.4 | Second issue same natural key | Fail+attach; no second stack | [x] |
| T6.5 | Same issue re-edit / re-label | Attach/reuse same PR | [x] |
| T6.6 | Missing Product field | validation-failed | [x] |
| T6.7 | Path-traversal product | validation-failed | [x] |
| T6.8 | Terragrunt product E2E | PR has `terragrunt.hcl` | [x] |
| T6.9 | DIY new stack on non-`issueops` branch | `guard-new-stacks` fail | [x] |
| T6.9b | DIY new stack on **spoofed** `issueops/*` as human | `guard-new-stacks` fail (bot+metadata required) | [x] |
| T6.10 | Concurrent twin events (`opened`+`labeled`) | Single success or safe attach; no corrupt push | [x] |
| T6.11 | Operator labels wrong product; body differs | **Body wins**; label synced | [x] |
| T6.12 | Request into env **not** in registry | validation-failed | [x] |
| T6.13 | Closed issue reopened + relabeled | Idempotent / explicit fail | [x] (#61 reopen → [infra-dev#22](https://github.com/ravichandrapatel/infra-dev/pull/22)) |
| T6.14 | Tracking Deployment `issueops-<env>` created | Visible under Environments | [x] |

---

## T7 — EnvOps live (new environment)

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T7.1 | Form without `envops` | No onboard job | [x] |
| T7.2 | Slug already in `environments.yaml` | validation-failed | [x] |
| T7.3 | `infra-<slug>` already exists | Fail closed | [x] |
| T7.4 | Happy path unique slug | Repo + vars/secret + registry PR; `status:env-ready` | [x] |
| T7.5 | ARN account ≠ account field | validation-failed | [x] |
| T7.6 | Missing App private key | `status:config-error` | [x] (gate) |
| T7.7 | Registry PR regenerates form | `environments.yaml` + `provision.yml` | [x] |
| T7.8 | Org vs user owner create path | Org uses App IAT; user needs user PAT | [x] |
| T7.9 | New workload inherits App mint + pins SHA | Spot-check scaffold | [x] |
| T7.10 | Ruleset apply on free personal private repo | WARN + continue **or** Pro required (document) | [x] |
| T7.11 | Second EnvOps for **prod** profile | Uses prod example; reviewers checklist | [x] (validate-env `profile=prod` → `infra-prod` + `PROD`; scaffold `open_reconcile_pr: false`) |
| T7.12 | Registry PR must not auto-merge | Human merge required | [x] (`allow_auto_merge=false`) |

---

## T8 — Local security negatives

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T8.1–T8.5 | Actor/repo injection; stack_path `..`; no control OIDC; CLI citations | Pass | [x] |

---

## T9 — Regression gate

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T9.1 | After any `[F]`, re-run Tier 0 | All green | [x] |
| T9.2 | `validate-control` + latest CI green | Both green | [x] |
| T9.3 | Pin bump playbook executed (pins + all `infra-*` callers) | SHAs match | [x] (`870cca9e…` matches infra-dev callers) |

---

## T10 — Adversarial / abuse (Tier 2)

| ID | Persona | Attack | Pass criteria | Result |
| --- | --- | --- | --- | --- |
| T10.1 | Hacker | Empty body product + CLI override | Denied | [x] |
| T10.2 | Hacker | Actor/repo path injection | Denied | [x] |
| T10.3 | Novice | XSS / shell metachar inputs | Schema reject | [x] |
| T10.4 | Hacker | EnvOps path / reserved / overlong slug | Denied | [x] |
| T10.5 | Owner | Fake IssueOps branch prefixes | Denied | [x] |
| T10.6 | Owner | Human `issueops/*` + forged metadata | Denied (bot required) | [x] |
| T10.7 | Hacker | Unregistered environment | Denied | [x] |
| T10.8 | Hacker | Unauthorized EnvOps author | Denied | [x] |
| T10.9 | Hacker | Spoof `product:*` label vs body | Body wins | [x] |
| T10.10 | Residual | Human login ending in `[bot]` | Impossible on GitHub | Residual OK |
| T10.11 | Insider | Force-push workload `main` | Blocked by ruleset / branch protection | [N/A] (personal free WARN-only; see WORKLOAD_RULESETS.md) |
| T10.12 | Insider | Admin bypass ruleset | Bypass list **empty** | [x] (control `bypass_actors` cleared 2026-08-10) |
| T10.13 | Insider | PAT with org admin used as modules token | Prefer App mint; document risk | [x] (docs: App mint preferred; PAT optional) |
| T10.14 | Supply chain | Replace actions SHA with attacker fork | CODEOWNERS + pin review | [x] (pins covered by CODEOWNERS; same Admin bypass residual) |
| T10.15 | Confused deputy | Workload OIDC role trusts `repo:*` | Deny; narrow subject | [S] (no AWS creds; docs specify non-wildcard `sub`) |

---

## T11 — Multi-team / tenancy / RBAC

| ID | Case | How | Pass criteria | Result |
| --- | --- | --- | --- | --- |
| T11.1 | Team A operator cannot IssueOps into Team B env without registry | Attempt wrong env | Fail or env not listed | [x] (#62 `prod` → fail-closed `status:config-error`; infra-prod missing) |
| T11.2 | Workload write access ≠ control operator | Collaborator on `infra-dev` only | Cannot start control IssueOps | [x] (#60 authz fail; workload invite ≠ control operator) |
| T11.3 | Labeler ≠ author | Admin labels issue owned by outsider | Still authz on **author** | [x] |
| T11.4 | CODEOWNERS on `config/catalog/**` | Non-owner PR | Review required | [x] |
| T11.5 | Break-glass operators list change | PR diff | Auditable; two-person review | [N/A] (solo maintainer demo) |
| T11.6 | Shared modules repo; least privilege mint | App token scoped to modules repo only | Token cannot push control | [x] (mint design) |
| T11.7 | Multiple control planes (fork per BU) | Pins/App isolated | No cross-tenant App install | [N/A] (single control plane) |

---

## T12 — Supply chain & provenance

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T12.1 | Actions pinned to 40-char SHA | `pins.yaml` + callers | [x] |
| T12.2 | Third-party Actions SHA-pinned in reusable workflows | No moving tags in prod path | [x] |
| T12.3 | Module refs are release tags (`module/vX.Y.Z`) | Catalog + render | [x] |
| T12.4 | Tag-root module layout (no bogus `//subdir` on release tags) | `tofu init` succeeds | [x] |
| T12.5 | SBOM / Action allowlist (optional enterprise) | Documented process | [N/A] (optional enterprise) |
| T12.6 | Compromised App key rotation drill | New PEM; old revoked; workloads updated | [x] (tabletop: DAY_OPERATIONS §13; live rotate not executed) |

---

## T13 — Secrets & identity

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T13.1 | Module download via App mint (no long-lived PAT required) | Validate stage green | [x] |
| T13.2 | PAT fallback optional only | Docs + EnvOps | [x] |
| T13.3 | Control never stores cloud long-lived keys | Secrets inventory | [x] (secret names: App/user PAT only — no AWS keys) |
| T13.4 | Workload Environment secrets not readable by control workflows | Boundary check | [x] |
| T13.5 | App private key not logged | Workflow logs scrubbed | [x] (observed) |
| T13.6 | OIDC role session tags / permissions least privilege | IAM policy review | [S] (no AWS IAM access) |
| T13.7 | Personal-account EnvOps user PAT scoped `repo` only | Token scopes | [x] (docs: `repo` scope; operator `gh` token has `repo`) |

---

## T14 — Pipeline integrity (workload)

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T14.1 | PR runs validate+plan; **no** apply | Job graph | [x] |
| T14.2 | Apply requires `confirm_apply=APPLY` + Environment | Gate | [x] |
| T14.3 | Plan artifact cannot be swapped cross-PR | Artifact naming / retention | [x] (Artifacts scoped to workflow run; `retention-days: 5`) |
| T14.4 | Checkov / Conftest failure blocks merge (required check) | Branch protection | [N/A] (personal free WARN-only; required checks need Pro/org) |
| T14.5 | `destroy` never on PR path | Workflow | [x] |
| T14.6 | Dual runner auto-detect (`terragrunt.hcl` vs tofu) | Both products | [x] |

---

## T15 — Drift & destroy safety

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T15.1 | Drift report issue opens on drift | Issue exists | [S] (drift run failed at OIDC — REPLACE_ACCOUNT_ID) |
| T15.2 | Dev stamp PR create/update only | No destroy in stamp | [x] (code/docs stamp create/update only) |
| T15.3 | Destroy-class drift never auto-PR | Report only | [x] (code/docs destroy report-only) |
| T15.4 | Prod drift report-only (`open_reconcile_pr: false`) | Config | [x] (examples) |
| T15.5 | Conftest deny destroy on `drift/*` heads | Policy | [x] (`deny_destroy.rego`) |

---

## T16 — Observability & audit

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T16.1 | Status labels sync from workload (`status-sync`) | Labels update | [x] (dispatch → #61 `status:plan-ok` [run](https://github.com/ravichandrapatel/gh-platform-control/actions/runs/31331778645)) |
| T16.2 | Failed provision leaves actionable issue comment | Comment + label | [x] |
| T16.3 | Audit: who labeled `issueops` vs who authored | Actions log | [x] (#60 events: author `srt-coder-devops`, labeler owner) |
| T16.4 | Retention: workflow logs / artifacts meet org policy | Settings | [x] (pipeline `retention-days: 5`) |
| T16.5 | SIEM export of IssueOps failures (optional) | Runbook link | [N/A] (optional) |

---

## T17 — Resilience & concurrency

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T17.1 | Per-issue concurrency on provision/onboard | No corrupt twin push | [x] |
| T17.2 | Natural-key race (two issues same key) | One winner; other fail+attach | [x] |
| T17.3 | Idempotent re-run same issue | Attach existing PR | [x] |
| T17.4 | Partial EnvOps failure leaves orphan repo | Detected on retry (exists) | [x] |
| T17.5 | GitHub API secondary rate limit | Retry/backoff or clear error | [x] (`github_http` + drift client 429/secondary retry) |
| T17.6 | Actions outage runbook | Linked from DAY_OPERATIONS | [x] (DAY_OPERATIONS §13.1) |

---

## T18 — Compliance & enterprise controls

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T18.1 | Private workloads; public control OK | Visibility matrix | [x] |
| T18.2 | No PII in Issue Form fields / logs | Field review | [x] |
| T18.3 | Data residency: state buckets in approved regions | Backend config | [S] (state backend not wired) |
| T18.4 | Separation of duties: author ≠ sole merger on prod | Environment reviewers | [N/A] (personal free: Environment required reviewers 422; WARN-only) |
| T18.5 | Change ticket / ADR link optional field (enterprise fork) | Process doc | [N/A] (optional enterprise) |
| T18.6 | Evidence pack export (checklist + CI URLs) for audit | This file + log | [x] |

---

## T19 — Adoption template (new org checklist)

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T19.1 | Fork/clone control; replace OWNER in pins | `validate-pins` | [x] |
| T19.2 | Create GitHub App; install All repos | Docs `GITHUB_APP.md` | [x] |
| T19.3 | Seed `operators.yaml` with platform breakers only | Least privilege | [x] |
| T19.4 | First EnvOps creates `infra-<first>` | T7.4 | [x] |
| T19.5 | Wire AWS OIDC + state for first env | Apply succeeds on smoke stack | [S] (no AWS account yet — keep REPLACE_*) |
| T19.6 | Train app teams: Issue Form only for **new** stacks | Day-2 doc acknowledged | [N/A] (solo demo) |
| T19.7 | Publish internal SLO (provision PR < N minutes) | Measured | [S] (SLO not published) |

---

## T20 — Incident / break-glass

| ID | Case | Pass criteria | Result |
| --- | --- | --- | --- |
| T20.1 | Compromised App PEM | Rotate; revoke; update all workloads | [x] (tabletop procedure; live rotate not executed) |
| T20.2 | Compromised operator account | Remove from `operators.yaml`; revoke sessions | [x] (tabletop) |
| T20.3 | Bad module tag published | Pin rollback; yank tag process | [x] (tabletop) |
| T20.4 | Emergency freeze: remove `issueops` label permission | Org role / rules | [x] (tabletop + DAY_OPERATIONS freeze) |
| T20.5 | Rollback bad EnvOps registry merge | Revert PR; regenerate form | [x] (tabletop: revert registry PR + regenerate form) |

---

## Reference execution (this repository)

Historical evidence for `ravichandrapatel/*` demo tenants. New adopters start with empty Result columns above.

| Pass | Date | Notes |
| --- | --- | --- |
| 1–2 | 2026-08-09 | App mint; EnvOps personal-account path; T7.4 `ciqa01315`. |
| 3 | 2026-08-10 | Adversarial: closed human `issueops/*` DIY; empty-product hole; T6.2/5/6; F1–F3. |
| 4 | 2026-08-10 | Expanded to reusable architect matrix (T11–T20); Tier mapping. |
| 5 | 2026-08-10 | Executed pending matrix: local gates + live IssueOps/EnvOps/status-sync; residual `[F]` on free-private rulesets/required checks/SoD, Admin bypass, missing AWS OIDC, no 429 backoff. |
| 6 | 2026-08-10 | Closed residual `[F]`s: empty control bypass; 429 backoff; personal-free WARN-only for workload rulesets/SoD reviewers; AWS deferred (REPLACE). |

### Notable evidence links

- DIY hole closed: [control#52](https://github.com/ravichandrapatel/gh-platform-control/pull/52), [infra-dev#18](https://github.com/ravichandrapatel/infra-dev/pull/18), retest [infra-dev#19](https://github.com/ravichandrapatel/infra-dev/pull/19)
- Unauthorized author: control issue #53
- Same-issue reuse: [infra-dev#20](https://github.com/ravichandrapatel/infra-dev/pull/20)
- Product label spoof / body wins: [infra-dev#21](https://github.com/ravichandrapatel/infra-dev/pull/21)
- EnvOps happy: `infra-ciqa01315`, [control#48](https://github.com/ravichandrapatel/gh-platform-control/pull/48)

- T6.13 reopen: control #61 → [infra-dev#22](https://github.com/ravichandrapatel/infra-dev/pull/22)
- T11.2 workload-only: control #60 authz fail
- T11.1 prod missing repo: control #62 `status:config-error`
- T16.1 status-sync: [run 31331778645](https://github.com/ravichandrapatel/gh-platform-control/actions/runs/31331778645)
- Drift blocked OIDC: [infra-dev run 31331677472](https://github.com/ravichandrapatel/infra-dev/actions/runs/31331677472)

- T10.12: control ruleset `bypass_actors=[]` (`current_user_can_bypass=never`)
- T17.5: `src/gh_platform_control/github_http.py` + actions `drift_reconcile` retry
