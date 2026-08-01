# GitHub Rulesets — gh-platform-control

Apply **after** the GitHub remote exists (Settings → Rules → Rulesets, or `gh api`).

## Required ruleset: protect `main`

| Rule | Value |
| --- | --- |
| Target | Branch `main` |
| Restrict creations | Yes (admins may bypass only for break-glass) |
| Restrict updates | Yes — require pull request |
| Restrict deletions | Yes |
| Block force pushes | Yes |
| Require linear history | Yes |
| Require PR | Yes — ≥1 approval, dismiss stale reviews, require conversation resolution |
| Require status checks | Yes — add CI job names once workflows are green |
| Require signed commits | Optional (enable when org GPG/SSH signing is standard) |
| Lock branch | No (use restrictions above) |

## Optional ruleset: block dangerous refs

- Deny pushes matching `refs/heads/main` from non-PR contexts (covered by restrict updates).
- Tag ruleset: allow create annotated tags matching `v*`; deny update/delete of tags.

## Apply via gh (example)

```bash
# Run from a machine authenticated to the org that owns gh-platform-control
gh api --method POST repos/{owner}/gh-platform-control/rulesets \
  --input docs/ruleset-main.json
```

See [ruleset-main.json](ruleset-main.json) for a starting payload. Replace `{owner}` and adjust `required_status_checks` after first CI run.
