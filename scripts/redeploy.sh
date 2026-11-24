#!/usr/bin/env bash
# =============================================================================
# Forces the ECS service to pull the image again and start new tasks.
# Use after pushing a new image with the SAME tag (e.g. "latest").
# If you pushed a NEW tag, run "terraform apply -var=image_tag=<tag>" instead.
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/terraform"

CLUSTER="$(terraform -chdir="$TF_DIR" output -raw ecs_cluster_name)"
SERVICE="$(terraform -chdir="$TF_DIR" output -raw ecs_service_name)"

echo ">> Forcing new deployment of $SERVICE on $CLUSTER"
aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --force-new-deployment --query 'service.deployments[0].{status:status,rollout:rolloutState}' --output table

echo ">> Waiting until the service is stable (can take 2-4 minutes)..."
aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE"
echo ">> Deployment finished. Health: $(terraform -chdir="$TF_DIR" output -raw health_url)"
