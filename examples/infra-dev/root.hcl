# FILE_NAME: root.hcl
# DESCRIPTION: Terragrunt root — remote state + provider generate for thin stack wrappers.
# VERSION: 0.1.0
# Place at the workload repo root (sibling of stacks/). IssueOps TG products include this file.

locals {
  # Mirror placeholders from config/environment.yaml / control environments.yaml.
  aws_region   = "us-east-1"
  aws_account  = "REPLACE_ACCOUNT_ID"
  environment  = "dev"
  state_bucket = "tfstate-${local.aws_account}-${local.environment}"
}

remote_state {
  backend = "s3"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
  config = {
    bucket       = local.state_bucket
    key          = "${path_relative_to_include()}/terraform.tfstate"
    region       = local.aws_region
    encrypt      = true
    use_lockfile = true
  }
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 5.0" }
  }
}

provider "aws" {
  region = "${local.aws_region}"
}
EOF
}
