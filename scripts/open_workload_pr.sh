#!/usr/bin/env bash
# FILE_NAME: open_workload_pr.sh
# DESCRIPTION: Commit rendered stack into workload repo and open a PR via gh.
# VERSION: 0.1.0
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

branch="issueops/${stack_id}"
work="$(mktemp -d)"
cleanup() { rm -rf "${work}"; }
trap cleanup EXIT

export GH_TOKEN="${TOKEN}"
export GIT_TERMINAL_PROMPT=0

git clone --depth 1 "https://x-access-token:${TOKEN}@github.com/${workload_repository}.git" "${work}/repo"
cd "${work}/repo"

git config user.name "gh-platform-control"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

git checkout -b "${branch}"

mkdir -p "${stack_path}"
cp -a "${STACK_SRC}/." "${stack_path}/"

git add "${stack_path}"
if git diff --cached --quiet; then
  echo "ERROR: no changes to commit (stack may already exist)" >&2
  exit 1
fi

git commit -m "$(cat <<EOF
feat(issueops): add ${stack_id}

Provision ${product} for ${environment} from ${control_repo}#${issue_number}.
EOF
)"

git push -u origin "${branch}"

pr_url="$(gh pr create \
  --repo "${workload_repository}" \
  --title "feat(issueops): ${stack_id}" \
  --body "$(cat <<EOF
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
)")"

echo "PR_URL=${pr_url}"
echo "${pr_url}" > "${ROOT}/.pr-url"
echo "${branch}" > "${ROOT}/.pr-branch"
echo "${workload_repository}" > "${ROOT}/.workload-repo"
