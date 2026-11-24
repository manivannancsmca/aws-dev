# -----------------------------------------------------------------------------
# OPTIONAL: CPU based auto scaling for the ECS service (enable_autoscaling = true).
# Adds tasks when average CPU goes above the target, removes them when it drops.
# -----------------------------------------------------------------------------
resource "aws_appautoscaling_target" "ecs" {
  count = var.enable_autoscaling ? 1 : 0

  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  min_capacity       = var.autoscaling_min_capacity
  max_capacity       = var.autoscaling_max_capacity
}

resource "aws_appautoscaling_policy" "ecs_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${local.name_prefix}-cpu-target-tracking"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.ecs[0].service_namespace
  scalable_dimension = aws_appautoscaling_target.ecs[0].scalable_dimension
  resource_id        = aws_appautoscaling_target.ecs[0].resource_id

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.autoscaling_cpu_target
    scale_out_cooldown = 60
    scale_in_cooldown  = 300
  }
}
