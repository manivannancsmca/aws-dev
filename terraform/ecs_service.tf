# -----------------------------------------------------------------------------
# ECS service: keeps desired_count copies of the task running, registers them
# with the load balancer, and replaces unhealthy tasks automatically.
# -----------------------------------------------------------------------------
resource "aws_ecs_service" "app" {
  name            = "${local.name_prefix}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private_app[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false # private subnets; outbound traffic goes through the NAT Gateway
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = var.project_name
    container_port   = var.app_port
  }

  # Do not kill a freshly started task before Spring Boot + Flyway have finished starting
  health_check_grace_period_seconds = 120

  # If a new deployment keeps failing, stop it and roll back to the previous task definition
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # The listener must exist before the service tries to register targets
  depends_on = [aws_lb_listener.http]
}
