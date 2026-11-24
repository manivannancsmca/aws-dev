# -----------------------------------------------------------------------------
# CloudWatch log group. The ECS task sends container stdout/stderr here
# through the "awslogs" log driver (see ecs.tf).
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = var.log_retention_days
}
