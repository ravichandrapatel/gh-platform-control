#!/usr/bin/env bash
# FILE_NAME: open_workload_pr.sh
# DESCRIPTION: Commit rendered stack into workload repo and open a PR via gh.
# VERSION: 0.2.0
set -euo pipefail

RESOLVED_JSON="${1:?resolved json}"
STACK_SRC="${2:?stack source dir}"
TOKEN="${3:?github token}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

workload_repository="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["workload_repository"])' "${RESOLVED_JSON}")"
stack_path="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["stack_path"])' "${RESOLVED_JSON}")"
stack_id="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["stack_id"])' "${RESOLVED_JSON}")"
issue_number="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["issue_number"])' "${RESOLVED_JSON}")"
control_repo="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["control_repo"])' "${RESOLVED_JSON}")"
environment="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["environment"])' "${RESOLVED_JSON}")"
product="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product"])' "${RESOLVED_JSON}")"
owner="${workload_repository%%/*}"
base_branch="main"
branch="issueops/${stack_id}"

work="$(mktemp -d)"
cleanup() { rm -rf "${work}"; }
trap cleanup EXIT

export GH_TOKEN="${TOKEN}"
export GIT_TERMINAL_PROMPT=0

# Reuse an existing open PR for this head if present (REST; App tokens often lack GraphQL).
existing_pr="$(gh api "repos/${workload_repository}/pulls?state=open&head=${owner}:${branch}" --jq '.[0].html_url' 2>/dev/null || true)"
if [[ -n "${existing_pr}" && "${existing_pr}" != "null" ]]; then
  echo "PR_URL=${existing_pr}"
  echo "${existing_pr}" > "${ROOT}/.pr-url"
  echo "${branch}" > "${ROOT}/.pr-branch"
  echo "${workload_repository}" > "${ROOT}/.workload-repo"
  exit 0
fi

git clone --depth 1 "https://x-access-token:${TOKEN}@github.com/${workload_repository}.git" "${work}/repo"
cd "${work}/repo"

git config user.name "gh-platform-control[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git fetch origin "${base_branch}"
git checkout -B "${branch}" "origin/${base_branch}"

mkdir -p "${stack_path}"
cp -a "${STACK_SRC}/." "${stack_path}/"

git add "${stack_path}"
if git diff --cached --quiet; then
  # Branch may already have the stack from a prior failed PR-create attempt.
  if git ls-remote --exit-code origin "refs/heads/${branch}" >/dev/null 2>&1; then
    echo "WARN: no new commits; opening PR from existing remote branch ${branch}"
    git push -u origin "${branch}" || true
  else
    echo "ERROR: no changes to commit (stack may already exist on ${base_branch})" >&2
    exit 1
  fi
else
  git commit -m "$(cat <<EOF
feat(issueops): add ${stack_id}

Provision ${product} for ${environment} from ${control_repo}#${issue_number}.
EOF
)"
  git push -u origin "${branch}"
fi

# Prefer REST PR create — more reliable for GitHub App installation tokens.
title="feat(issueops): ${stack_id}"
body="$(cat <<EOF
## Summary
- Product: \`${product}\`
- Environment: \`${environment}\`
- Stack: \`${stack_path}\`
- Request: https://github.com/${control_repo}/issues/${issue_number}

## Test plan
- [ ] Review generated OpenTofu root
- [ ] Confirm CI plan (Checkov / Conftest / tofu plan) is green
- [ ] Merge to apply (prod requires Environment approval)
EOF
)"

if ! pr_url="$(gh api --method POST "repos/${workload_repository}/pulls" \
  -f title="${title}" \
  -f head="${branch}" \
  -f base="${base_branch}" \
  -f body="${body}" \
  --jq .html_url 2>/tmp/pr-create.err)"; then
  echo "ERROR: failed to open PR. Ensure the GitHub App has Pull requests: Read and write on ${workload_repository}." >&2
  echo "Branch pushed: https://github.com/${workload_repository}/compare/${base_branch}...${branch}?expand=1" >&2
  cat /tmp/pr-create.err >&2 || true
  exit 1
fi

echo "PR_URL=${pr_url}"
echo "${pr_url}" > "${ROOT}/.pr-url"
echo "${branch}" > "${ROOT}/.pr-branch"
echo "${workload_repository}" > "${ROOT}/.workload-repo"
