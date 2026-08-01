#!/usr/bin/env bash
# FILE_NAME: bootstrap-labels.sh
# DESCRIPTION: Create IssueOps labels on the control repository.
# VERSION: 0.1.0
set -euo pipefail

REPO="${1:-${GITHUB_REPOSITORY:-}}"
if [[ -z "${REPO}" ]]; then
  echo "Usage: $0 OWNER/gh-platform-control" >&2
  exit 1
fi

create() {
  local name="$1" color="$2" desc="$3"
  gh label create "${name}" --repo "${REPO}" --color "${color}" --description "${desc}" --force >/dev/null
  echo "OK label ${name}"
}

create "issueops" "0E8A16" "IssueOps intake"
create "product:s3-bucket" "1D76DB" "Product: S3 bucket"
create "status:pending-validation" "FBCA04" "Awaiting control validation"
create "status:validation-failed" "D93F0B" "Catalog/schema validation failed"
create "status:config-error" "B60205" "Missing App/secrets/pins/config"
create "status:provision-failed" "E99695" "PR/deployment step failed"
create "status:pr-open" "0075CA" "Workload PR opened"
create "status:plan-ok" "0E8A16" "Workload plan succeeded"
create "status:plan-failed" "D93F0B" "Workload plan failed"
create "status:applied" "0E8A16" "Apply succeeded"
create "status:apply-failed" "D93F0B" "Apply failed"

echo "OK: IssueOps labels ready on ${REPO}"
