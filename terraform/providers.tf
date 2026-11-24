# -----------------------------------------------------------------------------
# AWS provider. Credentials are NEVER written here: Terraform reads them from
# the environment (AWS_PROFILE, AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, or an
# assumed role), exactly like the AWS CLI does.
# -----------------------------------------------------------------------------
provider "aws" {
  region = var.aws_region

  # Every resource gets these tags automatically (useful for cost reports and cleanup)
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
