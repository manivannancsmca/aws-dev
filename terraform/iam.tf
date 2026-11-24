# -----------------------------------------------------------------------------
# IAM roles for ECS (least privilege).
#   execution role = used by the ECS agent BEFORE the container starts:
#                    pull image from ECR, write logs, read the DB secret
#   task role      = used by the application code at runtime (nothing needed today)
# -----------------------------------------------------------------------------
locals {
  ecs_tasks_assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${local.name_prefix}-ecs-task-execution-role"
  assume_role_policy = local.ecs_tasks_assume_role_policy
}

# AWS managed policy: ecr:GetAuthorizationToken, ecr:BatchGetImage, logs:CreateLogStream, logs:PutLogEvents ...
resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Extra permission: read ONLY our database secret (needed to inject DB_USERNAME / DB_PASSWORD)
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "read-db-credentials-secret"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.db.arn]
    }]
  })
}

# The application itself calls no AWS APIs, so this role has no policies.
# Add policies here later if the app needs S3, SQS, etc.
resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-ecs-task-role"
  assume_role_policy = local.ecs_tasks_assume_role_policy
}
