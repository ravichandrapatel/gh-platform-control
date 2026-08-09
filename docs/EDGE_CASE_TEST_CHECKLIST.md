# Edge-case test checklist — gh-platform-control

**Scope:** Python app (`src/gh_platform_control`), IssueOps, EnvOps, CI, GitHub UI.  
**Rule:** If any case fails → fix → **restart from T00** (do not skip).

**Legend:** `[ ]` pending · `[x]` pass · `[F]` fail · `[S]` skipped (blocked / no env) · `[N/A]` not applicable

---

## T00 — Preconditions

| ID | Case | How | Pass criteria |
| --- | --- | --- | --- |
| T00.1 | Repo pushed; PR or main HEAD includes `src/` and no flat `scripts/` | `gh api` / UI | Tree matches local |
| T00.2 | `gh auth` as operator who can open issues / see Actions | `gh auth status` | Logged in |
| T00.3 | Control secrets present for live IssueOps (optional for T1–T3) | UI Settings → Secrets | `CONTROL_CLIENT_ID` + `CONTROL_APP_PRIVATE_KEY` (App installed on modules) |
| T00.4 | Labels exist | `gh label list` | `issueops`, `envops`, status labels |

---

## T1 — Local CLI: config gates

| ID | Case | Command / action | Pass criteria |
| --- | --- | --- | --- |
| T1.1 | Pins accept SHA + SemVer | `validate-pins` (ALLOW placeholders) | Exit 0 |
| T1.2 | Floating ref rejected | temp pins with `ref: main` | Exit 1, error mentions floating |
| T1.3 | Placeholder rejected without allow | unset ALLOW, placeholder ref | Exit 1 |
| T1.4 | Control config OK | `validate-control` ALLOW=1 | Exit 0, form `--check` OK |
| T1.5 | Form drift detected | mutate `provision.yml` then `--check` | Exit 1; restore file |
| T1.6 | Product id ≠ filename | broken catalog temp | Exit 1 |
| T1.7 | Bad runner value | `runner: helm` | Exit 1 |

---

## T2 — Local CLI: parse / validate / render (stack)

| ID | Case | Pass criteria |
| --- | --- | --- |
| T2.1 | Happy path parse Product/Env/fields | JSON keys present |
| T2.2 | HTML comment in body ignored | Product still parsed |
| T2.3 | `_No response_` → empty | Empty string |
| T2.4 | Valid tofu product → stack_id natural key | `s3-bucket-…`, no `issue-` |
| T2.5 | Terragrunt product → `runner=terragrunt` + `terragrunt.hcl` | Files exist |
| T2.6 | Missing required bucket_name | Exit 1 |
| T2.7 | Bad enum (versioning) | Exit 1 |
| T2.8 | Pattern fail (bucket uppercase) | Exit 1 |
| T2.9 | Unknown environment | Exit 1 |
| T2.10 | Product CLI ≠ body | Exit 1 |
| T2.11 | Path traversal product `../etc/passwd` | Exit 1, “invalid product” |
| T2.12 | Unsafe template id in resolved | render Exit 1 |
| T2.13 | Template dir escape attempt | render Exit 1 |

---

## T3 — Local CLI: EnvOps validate / scaffold

| ID | Case | Pass criteria |
| --- | --- | --- |
| T3.1 | Valid staging non-prod resolve | `infra-staging`, example infra-dev |
| T3.2 | Prod profile → infra-prod example | example=infra-prod, tagging PROD |
| T3.3 | Slug too short / uppercase / starts digit | Exit 1 |
| T3.4 | Account not 12 digits | Exit 1 |
| T3.5 | ARN account ≠ account field | Exit 1 |
| T3.6 | Env key already in environments.yaml (`dev`) | Exit 1 |
| T3.7 | Scaffold substitutes role/region/env/actions SHA | Spot-check tofu.yml |
| T3.8 | patch-environments adds row (temp copy) | YAML contains new key |
| T3.9 | patch-environments duplicate key | Exit 1 |

---

## T4 — GitHub CI (after push)

| ID | Case | How | Pass criteria |
| --- | --- | --- | --- |
| T4.1 | `ci` workflow runs on PR/push | `gh run list` | New run exists |
| T4.2 | Validate pins step green | `gh run view --log` | OK pins |
| T4.3 | Validate control green | same | OK control |
| T4.4 | Smoke parse/validate/render tofu+tg | same | natural-key + terragrunt ok |
| T4.5 | Path-traversal rejection in CI | same | “path-traversal rejection ok” |
| T4.6 | No references to deleted `scripts/*.py` in workflows | `gh api` contents / local | Clean |

---

## T5 — GitHub UI: templates & navigation

| ID | Case | How | Pass criteria |
| --- | --- | --- | --- |
| T5.1 | Issues → New → **Provision infrastructure** | Browser | Form loads; Product + Environment dropdowns |
| T5.2 | Issues → New → **Onboard environment** | Browser | EnvOps fields present |
| T5.3 | Blank issues disabled | Browser / config.yml | No free-form blank |
| T5.4 | Actions tab shows `ci`, `issue-provision`, `issue-env-onboard` | Browser | Workflows listed |
| T5.5 | `src/gh_platform_control/` visible on branch | Browser code | Flat modules, no `gitops/` |

---

## T6 — IssueOps live (stack) — edge + happy

**Requires:** App install, operators, workload `infra-dev` (or registered env).

| ID | Case | How | Pass criteria |
| --- | --- | --- | --- |
| T6.1 | Open provision issue **without** `issueops` | Form only | **No** `issue-provision` run |
| T6.2 | Add `issueops` as unauthorized author | (if alt user) | `status:validation-failed` / authz |
| T6.3 | Authorized + `issueops` + unique bucket | Label issue | PR on `issueops/<stack_id>`; `status:pr-open` |
| T6.4 | Same natural key second issue | New issue same bucket | Fail+attach; duplicate comment |
| T6.5 | Re-label / edit same issue | Edit body | Attaches/refreshes same PR (same-issue) |
| T6.6 | Missing Product field body | Malformed | validation-failed |
| T6.7 | Invalid product slug in body | `../x` | validation-failed |
| T6.8 | TG product end-to-end | Product s3-bucket-tg | PR contains `terragrunt.hcl` |
| T6.9 | Workload DIY new stack branch (non-issueops) | PR on infra-* | `guard-new-stacks` fails (if ruleset/CI live) |

---

## T7 — EnvOps live — edge + happy

**Requires:** App Admin/Environments/Secrets perms; App installed on modules repo (or All repos).

| ID | Case | How | Pass criteria |
| --- | --- | --- | --- |
| T7.1 | Open onboard form without `envops` | Form only | No `issue-env-onboard` run |
| T7.2 | `envops` + env name `dev` (exists) | Label | Fail closed; validation |
| T7.3 | `envops` + repo already exists | Pre-create empty `infra-testenv` | Fail; issue comment |
| T7.4 | Happy path unique slug (e.g. `ciqa`) | Label | Repo created; ruleset; secret; registry PR `envops/ciqa`; `status:env-ready` |
| T7.5 | Bad ARN / account mismatch | Form | validation-failed before create |
| T7.6 | Missing CONTROL_APP_PRIVATE_KEY | (if removable) | status:config-error |
| T7.7 | Registry PR regenerates provision.yml | PR files | environments.yaml + provision.yml |

---

## T8 — Negative / security edges

| ID | Case | Pass criteria |
| --- | --- | --- |
| T8.1 | Actor login injection `/` or spaces | authorize Exit 1 |
| T8.2 | Invalid repository string | authorize Exit 1 |
| T8.3 | stack_path with `..` refused in workload_pr | Exit 1 (unit/integration) |
| T8.4 | Control never applies AWS (no OIDC on control workflows) | Workflow YAML review |
| T8.5 | `provision.yml` regenerate comments cite `-m gh_platform_control` | File grep |

---

## T9 — Regression restart gate

| ID | Case | Pass criteria |
| --- | --- | --- |
| T9.1 | After any `[F]`, all prior `[x]` re-run | Full pass from T00 |
| T9.2 | Final `validate-control` + latest CI green | Both green |

---

## Execution log

| Pass | Date | Notes |
| --- | --- | --- |
| 1 | 2026-08-09 | Local T1–T3/T8 green. CI PR#16/#20 green. Twin-run push race found → fixed concurrency + attach (#20). Restart: T6.1 skip, T6.3 PR#11 success (single success run), T6.4 dup fail+attach, T6.7 bad product validation-failed, T7.1 skip, T7.2 existing `dev` validation-failed, T7.6 missing `MODULES_GIT_TOKEN` → config-error (no repo). Browser UI T5 blocked (IDE browser not signed into GitHub); templates/workflows verified via API. |
| | | **Unblocked for App mint:** T7.4 EnvOps happy path needs control App credentials (no `MODULES_GIT_TOKEN` required). |
| | | **Skipped (no live ruleset proof):** T6.9 DIY new stack on infra-dev. |
| | | **Skipped (needs alt user):** T6.2 unauthorized author. |
