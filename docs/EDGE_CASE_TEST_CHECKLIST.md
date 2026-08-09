# Edge-case test checklist — gh-platform-control

**Scope:** Python app (`src/gh_platform_control`), IssueOps, EnvOps, CI, GitHub UI.  
**Rule:** If any case fails → fix → **restart from T00** (do not skip).

**Legend:** `[ ]` pending · `[x]` pass · `[F]` fail · `[S]` skipped (blocked / no env) · `[N/A]` not applicable

---

## T00 — Preconditions

| ID | Case | How | Pass criteria | Result |
| --- | --- | --- | --- | --- |
| T00.1 | Repo pushed; PR or main HEAD includes `src/` and no flat `scripts/` | `gh api` / UI | Tree matches local | [x] |
| T00.2 | `gh auth` as operator who can open issues / see Actions | `gh auth status` | Logged in | [x] |
| T00.3 | Control secrets present for live IssueOps | UI / `gh secret list` | `CONTROL_CLIENT_ID` + `CONTROL_APP_PRIVATE_KEY` (+ `CONTROL_USER_REPO_TOKEN` on personal accounts) | [x] |
| T00.4 | Labels exist | `gh label list` | `issueops`, `envops`, status labels | [x] |

---

## T1 — Local CLI: config gates

| ID | Result |
| --- | --- |
| T1.1–T1.7 | [x] (2026-08-09 restart) |

---

## T2 — Local CLI: parse / validate / render (stack)

| ID | Result |
| --- | --- |
| T2.1–T2.13 | [x] |

---

## T3 — Local CLI: EnvOps validate / scaffold

| ID | Result |
| --- | --- |
| T3.1–T3.9 | [x] (scaffold includes App mint inputs + actions SHA `870cca9e…`) |

---

## T4 — GitHub CI (after push)

| ID | Result | Evidence |
| --- | --- | --- |
| T4.1–T4.5 | [x] | [ci run 31329167929](https://github.com/ravichandrapatel/gh-platform-control/actions/runs/31329167929) |
| T4.6 | [x] | No top-level `scripts/*.py` / `gitops/` package |

---

## T5 — GitHub UI: templates & navigation

| ID | Result | Notes |
| --- | --- | --- |
| T5.1–T5.5 | [x] | Verified via API (browser not signed in) |

---

## T6 — IssueOps live (stack)

| ID | Result | Evidence |
| --- | --- | --- |
| T6.1 | [x] | Issue #30 → workflow **skipped** (no `issueops`) |
| T6.2 | [S] | Needs alternate unauthorized user |
| T6.3 | [x] | Issue #31 → [infra-dev#13](https://github.com/ravichandrapatel/infra-dev/pull/13) `status:pr-open` |
| T6.4 | [x] | Issue #32 → duplicate fail+attach to #31 / PR#13 |
| T6.5 | [S] | Covered by same-issue attach on #31 twin-run |
| T6.6 | [S] | Not re-run this pass |
| T6.7 | [x] | Issue #33 → `status:validation-failed` |
| T6.8 | [x] | Issue #34 → [infra-dev#14](https://github.com/ravichandrapatel/infra-dev/pull/14) has `terragrunt.hcl` |
| T6.9 | [x] | [infra-dev#15](https://github.com/ravichandrapatel/infra-dev/pull/15) `guard-new-stacks` **fail** |

**App mint proof:** IssueOps stack [edge-mintfix-6300739](https://github.com/ravichandrapatel/infra-dev/actions/runs/31329587072) — **validate pass** after tag-root module source fix (plan may pend on AWS OIDC).

---

## T7 — EnvOps live

| ID | Result | Evidence |
| --- | --- | --- |
| T7.1 | [x] | Issue #35 → **skipped** (no `envops`) |
| T7.2 | [x] | Issue #36 → validation-failed (`dev` exists) |
| T7.3 | [x] | Issue #50 → provision-failed (repo `infra-ciqa01242` exists) |
| T7.4 | [x] | Issue #47 → `status:env-ready`; repo `infra-ciqa01315`; [registry PR#48](https://github.com/ravichandrapatel/gh-platform-control/pull/48) |
| T7.5 | [x] | Issue #49 → validation-failed (ARN account mismatch) |
| T7.6 | [S] | Not removing live `CONTROL_APP_PRIVATE_KEY` |
| T7.7 | [x] | PR#48 files: `environments.yaml` + `provision.yml` |

**Personal-account notes (this demo):**
- `CONTROL_USER_REPO_TOKEN` required (`POST /user/repos` needs user PAT, not App IAT).
- Private-repo **rulesets** need GitHub Pro — EnvOps continues with WARN.
- Bare Environments (no protection-rule fields) for free plan.

---

## T8 — Negative / security edges

| ID | Result |
| --- | --- |
| T8.1–T8.5 | [x] |

---

## T9 — Regression restart gate

| ID | Result |
| --- | --- |
| T9.1 | [x] | Restarted after App mint + template + EnvOps personal-account fixes |
| T9.2 | [x] | `validate-control` local OK; CI green on main |

---

## Execution log

| Pass | Date | Notes |
| --- | --- | --- |
| 1 | 2026-08-09 | Earlier pass; T7.4 blocked on `MODULES_GIT_TOKEN`. |
| 2 | 2026-08-09/10 | **App mint:** live `infra-dev` updated ([PR#12](https://github.com/ravichandrapatel/infra-dev/pull/12)); actions pin `870cca9e…`. Module sources fixed to tag-root ([control#37](https://github.com/ravichandrapatel/gh-platform-control/pull/37)). EnvOps personal-account: user PAT + bare Environment + best-effort ruleset. T7.4 happy path `ciqa01315`. `infra-prod` **N/A** (repo does not exist). |
