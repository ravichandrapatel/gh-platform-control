# Edge-case test checklist — gh-platform-control

**Scope:** Python app (`src/gh_platform_control`), IssueOps, EnvOps, CI, GitHub UI, adversarial abuse.  
**Rule:** If any case fails → fix → **restart from T00** (do not skip).

**Legend:** `[ ]` pending · `[x]` pass · `[F]` fail · `[S]` skipped · `[N/A]` not applicable

---

## T00 — Preconditions

| ID | Result |
| --- | --- |
| T00.1–T00.4 | [x] |

---

## T1–T5

| Suite | Result |
| --- | --- |
| T1 config gates | [x] |
| T2 parse/validate/render | [x] (+ empty body product now denied — see T10.1) |
| T3 EnvOps local | [x] |
| T4 CI | [x] |
| T5 templates (API) | [x] |

---

## T6 — IssueOps live

| ID | Result | Evidence |
| --- | --- | --- |
| T6.1 | [x] | No label → skipped |
| T6.2 | [x] | Issue #53 author `srt-coder-devops` → authorization failed |
| T6.3 | [x] | Prior + T6.5 happy path |
| T6.4 | [x] | Dup fail+attach |
| T6.5 | [x] | Issue #55 re-edit → attach/reuse [infra-dev#20](https://github.com/ravichandrapatel/infra-dev/pull/20) |
| T6.6 | [x] | Issue #54 missing Product → validation-failed |
| T6.7 | [x] | Bad product `../x` |
| T6.8 | [x] | Terragrunt product |
| T6.9 | [x] | DIY non-issueops branch → guard fail |
| T6.9b | [x] | **Hole then fix:** human `issueops/*` DIY passed guard → hardened; retest [PR#19](https://github.com/ravichandrapatel/infra-dev/pull/19) guard **fail**; App PR#20 still **pass** |

---

## T7 — EnvOps live

| ID | Result | Evidence |
| --- | --- | --- |
| T7.1–T7.5, T7.7 | [x] | Prior pass-2 |
| T7.4 | [x] | `infra-ciqa01315` + registry PR#48 |
| T7.6 | [x] | Workflow `require-creds` fails closed if `CONTROL_APP_PRIVATE_KEY` absent (static + gate review; live delete skipped to avoid losing PEM) |

---

## T8 — Negative / security (local)

| ID | Result |
| --- | --- |
| T8.1–T8.5 | [x] |

---

## T10 — Adversarial / loophole hunt (pass 3)

| ID | Persona | Attack | Result |
| --- | --- | --- | --- |
| T10.1 | Hacker | Empty body product + CLI `--product` override | [x] denied after fix (`validate-request`) |
| T10.2 | Hacker | Actor/repo path injection in authorize | [x] denied |
| T10.3 | Novice | XSS / shell metachar / spaces in inputs | [x] pattern/enum reject |
| T10.4 | Hacker | EnvOps `../../etc`, reserved `main`/`control`, long slug | [x] denied |
| T10.5 | Owner loophole | Branch `issueops-not-really` / `Issueops/` / nested path | [x] denied |
| T10.6 | Owner loophole | Human opens `issueops/<stack>` + forges metadata | [x] **was hole** → fixed: require `[bot]` actor ([control#52](https://github.com/ravichandrapatel/gh-platform-control/pull/52), [infra-dev#18](https://github.com/ravichandrapatel/infra-dev/pull/18)) |
| T10.7 | Hacker | Unregistered Environment in Issue Form | [x] #56 validation-failed |
| T10.8 | Hacker | Unauthorized EnvOps author | [x] #57 authorization failed |
| T10.9 | Hacker | Spoof `product:s3-bucket` label vs body `s3-bucket-tg` | [x] body wins → TG PR#21 + label synced to `product:s3-bucket-tg` |
| T10.10 | Residual | Forge App `[bot]` identity | Residual: GitHub prevents humans registering `[bot]` logins; forged metadata alone insufficient without bot actor |

---

## T9 — Regression gate

| ID | Result |
| --- | --- |
| T9.1 | [x] Restarted after security harden |
| T9.2 | [x] App IssueOps guard still green on PR#20 |

---

## Execution log

| Pass | Date | Notes |
| --- | --- | --- |
| 1–2 | 2026-08-09 | App mint + EnvOps personal-account path. |
| 3 | 2026-08-10 | **Adversarial:** closed human `issueops/*` DIY hole; empty-product CLI hole; finished T6.2/5/6; F1–F3 abuse cases. |
