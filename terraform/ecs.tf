# -----------------------------------------------------------------------------
# ECS cluster + Fargate task definition.
# The task definition is the "recipe" for one container: image, CPU/memory,
# environment variables, secrets, logging and health check.
# -----------------------------------------------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled" # enable later for detailed CPU/memory dashboards (extra CloudWatch cost)
  }
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${local.name_prefix}-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc" # each task gets its own network interface and private IP
  cpu                      = var.container_cpu
  memory                   = var.container_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64" # must match the architecture the image was built for
  }

  container_definitions = jsonencode([
    {
      name      = var.project_name
      image     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
      essential = true

      portMappings = [{
        containerPort = var.app_port
        protocol      = "tcp"
      }]

      # Plain (non-secret) configuration. Same variable names as docker-compose.yml.
      environment = [
        { name = "SPRING_PROFILES_ACTIVE", value = "aws" },
        { name = "DB_HOST", value = aws_db_instance.mysql.address },
        { name = "DB_PORT", value = tostring(aws_db_instance.mysql.port) },
        { name = "DB_NAME", value = var.db_name }
      ]

      # Secret configuration: ECS reads the JSON keys from Secrets Manager at task start.
      # Format: <secret ARN>:<json key>:<version stage>:<version id>  (last two left empty = current version)
      secrets = [
        { name = "DB_USERNAME", valueFrom = "${aws_secretsmanager_secret.db.arn}:username::" },
        { name = "DB_PASSWORD", valueFrom = "${aws_secretsmanager_secret.db.arn}:password::" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      # Container-level health check (the ALB performs its own as well)
      healthCheck = {
        command     = ["CMD-SHELL", "wget -qO- http://localhost:${var.app_port}/actuator/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 90 # give the JVM + Flyway time to start before counting failures
      }
    }
  ])
}
