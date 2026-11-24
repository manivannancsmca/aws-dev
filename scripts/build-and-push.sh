#!/usr/bin/env bash
# =============================================================================
# Builds the product-app Docker image and pushes it to the ECR repository
# created by Terraform. Works in Git Bash on Windows, macOS and Linux.
#
# Usage:  ./scripts/build-and-push.sh [tag]        (default tag: latest)
# Needs:  docker, aws CLI (logged in: AWS_PROFILE or env credentials), terraform
# =============================================================================
set -euo pipefail

TAG="${1:-latest}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/product-app"
TF_DIR="$ROOT_DIR/terraform"

echo ">> Reading ECR repository URL from Terraform outputs"
ECR_URL="$(terraform -chdir="$TF_DIR" output -raw ecr_repository_url)"
REGION="$(echo "$ECR_URL" | cut -d. -f4)"          # 123456789012.dkr.ecr.<region>.amazonaws.com/product-app
REGISTRY="$(echo "$ECR_URL" | cut -d/ -f1)"        # 123456789012.dkr.ecr.<region>.amazonaws.com
echo "   repository: $ECR_URL"
echo "   region:     $REGION"

echo ">> Building image (linux/amd64 to match the Fargate task definition)"
docker build --platform linux/amd64 -t "product-app:$TAG" "$APP_DIR"

echo ">> Logging in to ECR"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

echo ">> Tagging and pushing $ECR_URL:$TAG"
docker tag "product-app:$TAG" "$ECR_URL:$TAG"
docker push "$ECR_URL:$TAG"

echo ">> Done. Image available at $ECR_URL:$TAG"
echo "   Next: terraform -chdir=\"$TF_DIR\" apply -var=\"image_tag=$TAG\""
