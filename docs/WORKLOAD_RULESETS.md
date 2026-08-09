# GitHub Rulesets — workload repos (`infra-*`)

Apply on **every** `infra-*` repository so humans
(including **owners and admins**) cannot land DIY new stacks.

**EnvOps** (`issue-env-onboard.yml`) applies [`ruleset-workload.json`](ruleset-workload.json) automatically when creating a new env. Use this doc for manual / existing repos.

## Required ruleset: protect `main`

| Rule | Value |
| --- | --- |
| Target | Branch `main` |
| Restrict updates | Require pull request |
| Restrict deletions | Yes |
| Block force pushes | Yes |
| Require linear history | Recommended |
| Require PR | Yes — approvals as you prefer |
| Require status checks | **Yes — include `guard-new-stacks`** (from `tofu.yml`) plus plan jobs once named |
| **Bypass list** | **Empty** — do **not** allow repository admins to bypass |

Org-owned rulesets (applied to `infra-*`) are stronger than per-repo rules: a repo admin cannot turn them off.

```bash
gh api --method POST repos/OWNER/infra-ENV/rulesets \
  --input docs/ruleset-workload.json
```

## Why

CI alone fails DIY new-stack PRs (`gh-platform-actions/actions/security/guard-new-stacks`). Admins can still merge if they may bypass required checks. With **no bypass actors**, the only way to add `stacks/<new>/` is an IssueOps PR whose head branch is `issueops/<stack_id>` (check passes) then a normal merge.

Day-2 edits to **existing** stacks still work on any branch; `guard-new-stacks` allows them.

## Personal free accounts (WARN-only)

Private repos on a **free personal** GitHub plan cannot use repository rulesets or classic branch protection (API returns 403 / billing errors). EnvOps **warns and continues** if `ruleset-workload.json` cannot be applied.

| Control | Free personal private | Pro / org private | Public |
| --- | --- | --- | --- |
| Rulesets + required checks (`guard-new-stacks`) | WARN residual | Apply JSON | Apply JSON |
| Environment **required reviewers** (SoD apply gate) | WARN residual | Configure | Configure |

**Demo policy:** treat missing rulesets/reviewers as accepted residual risk; rely on `guard-new-stacks` CI + App-only `issueops/*` provenance. Production adopters: **Pro**, or host `infra-*` under an **org**.

## Checklist

- [ ] Ruleset on each workload `main` with required check `guard-new-stacks` (or documented WARN on free personal)
- [ ] Admin bypass disabled (repo and org) when rulesets exist
- [ ] Branch protection / ruleset blocks direct pushes to `main` when plan allows
- [ ] Control GitHub App can open PRs from `issueops/*` (contents + pull requests write)
- [ ] Environment required reviewers on apply Environments when plan allows

See also [Day-2 stack changes](../../_okf_knowledge/vault/playbooks/gh-platform-day2-stack-changes.md) (vault) and [DAY_OPERATIONS.md](DAY_OPERATIONS.md) §§3.4–3.5 / §10.
