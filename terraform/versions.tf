# -----------------------------------------------------------------------------
# Terraform and provider versions + remote state backend.
# -----------------------------------------------------------------------------
terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state stored in S3 (bucket created once by ./bootstrap).
  # The bucket name and region are NOT hardcoded here; pass them at init time:
  #   terraform init -backend-config=backend.hcl
  backend "s3" {
    key          = "product-app/dev/terraform.tfstate"
    encrypt      = true
    use_lockfile = true # Native S3 state locking (Terraform >= 1.10). No DynamoDB table needed.
  }
}
