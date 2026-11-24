# -----------------------------------------------------------------------------
# Values printed after "terraform apply" (and available via "terraform output").
# -----------------------------------------------------------------------------
output "alb_dns_name" {
  description = "Public DNS name of the load balancer"
  value       = aws_lb.app.dns_name
}

output "app_url" {
  description = "Base URL of the application"
  value       = local.https_enabled && var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.app.dns_name}"
}

output "swagger_url" {
  description = "Swagger UI"
  value       = "${local.https_enabled && var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.app.dns_name}"}/swagger-ui/index.html"
}

output "health_url" {
  description = "Actuator health endpoint"
  value       = "${local.https_enabled && var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_lb.app.dns_name}"}/actuator/health"
}

output "ecr_repository_url" {
  description = "Push the Docker image here"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  value = aws_ecs_service.app.name
}

output "cloudwatch_log_group" {
  description = "Application logs"
  value       = aws_cloudwatch_log_group.app.name
}

output "rds_endpoint" {
  description = "RDS endpoint (host:port). Private: only reachable from inside the VPC."
  value       = aws_db_instance.mysql.endpoint
}

output "db_secret_arn" {
  description = "Secrets Manager secret holding the DB username/password"
  value       = aws_secretsmanager_secret.db.arn
}
