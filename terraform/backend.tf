# Remote state is intentionally NOT enabled for this take-home, because it
# would require a pre-existing S3 bucket + DynamoDB lock table (chicken-
# and-egg problem for `terraform plan` with no AWS account). In a real
# environment, uncomment and adapt this block, and create the bucket/table
# out-of-band (or via a small bootstrap Terraform config that itself uses
# local state).
#
# terraform {
#   backend "s3" {
#     bucket         = "your-org-terraform-state"
#     key            = "url-shortener/terraform.tfstate"   # override per env with -backend-config
#     region         = "us-east-1"
#     dynamodb_table = "terraform-state-locks"
#     encrypt        = true
#   }
# }
#
# Per-environment state isolation would be done with either:
#   - a distinct `key` per environment, passed via `-backend-config="key=url-shortener/prod/terraform.tfstate"`
#   - or separate workspaces (terraform workspace new prod)
# We'd use distinct keys per environment rather than workspaces, since
# workspaces make it easy to accidentally `apply` against the wrong
# environment from the same local state file list.
