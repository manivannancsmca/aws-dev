# -----------------------------------------------------------------------------
# ONE-TIME bootstrap: creates the S3 bucket that stores the Terraform state of
# the main configuration (../). This tiny config keeps its own state locally
# (terraform.tfstate in this folder) because the bucket cannot store its own state.
#
#   cd terraform/bootstrap
#   terraform init
#   terraform apply -var="state_bucket_name=product-app-tfstate-<your-account-id>"
#
# Jenkins (step 01) runs the same config but keeps this small state file in its
# persistent home folder instead of the build workspace, which is deleted after every build:
#   terraform init -backend-config="path=/var/jenkins_home/terraform-state/product-app/bootstrap.tfstate"
# -----------------------------------------------------------------------------
terraform {
  required_version = ">= 1.10"

  # Local state. Without -backend-config the file is ./terraform.tfstate (manual runs).
  backend "local" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "Region for the state bucket (use the same as the main configuration)."
  type        = string
  default     = "ap-south-1"
}

variable "state_bucket_name" {
  description = "Globally unique bucket name, e.g. product-app-tfstate-123456789012"
  type        = string
}

resource "aws_s3_bucket" "tfstate" {
  bucket = var.state_bucket_name

  lifecycle {
    prevent_destroy = true # losing the state bucket would orphan all infrastructure
  }
}

# Keep every version of the state file so a bad apply can be rolled back
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "state_bucket_name" {
  value = aws_s3_bucket.tfstate.bucket
}
