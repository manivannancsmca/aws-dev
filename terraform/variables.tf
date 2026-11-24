# -----------------------------------------------------------------------------
# Input variables. Every value has a sensible default for a small dev/demo
# deployment; override them in terraform.tfvars (see terraform.tfvars.example).
# -----------------------------------------------------------------------------

# ---------- General ----------
variable "project_name" {
  description = "Short name used as a prefix for all resources."
  type        = string
  default     = "product-app"
}

variable "environment" {
  description = "Environment name (dev, staging, prod). Part of every resource name."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "ap-south-1"
}

# ---------- Networking ----------
variable "vpc_cidr" {
  description = "CIDR block of the dedicated VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Exactly two AZs in aws_region. Subnets are spread across them."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Provide exactly two availability zones."
  }
}

variable "public_subnet_cidrs" {
  description = "Public subnets (ALB + NAT Gateway), one per AZ."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]
}

variable "private_app_subnet_cidrs" {
  description = "Private subnets for ECS tasks, one per AZ."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "private_db_subnet_cidrs" {
  description = "Private subnets for RDS, one per AZ (no internet route at all)."
  type        = list(string)
  default     = ["10.0.20.0/24", "10.0.21.0/24"]
}

# ---------- Application / ECS ----------
variable "app_port" {
  description = "Port the Spring Boot container listens on."
  type        = number
  default     = 8080
}

variable "image_tag" {
  description = "Tag of the image in ECR to run (e.g. latest or a git SHA)."
  type        = string
  default     = "latest"
}

variable "container_cpu" {
  description = "Fargate CPU units for the task (256 = 0.25 vCPU, 512 = 0.5 vCPU, 1024 = 1 vCPU)."
  type        = number
  default     = 512
}

variable "container_memory" {
  description = "Fargate memory (MiB) for the task. Must be a valid combination with container_cpu."
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Number of ECS tasks to run."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "How long CloudWatch keeps application logs."
  type        = number
  default     = 7
}

# ---------- Auto scaling (optional) ----------
variable "enable_autoscaling" {
  description = "Enable CPU based target-tracking auto scaling for the ECS service."
  type        = bool
  default     = false
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks when auto scaling is enabled."
  type        = number
  default     = 1
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks when auto scaling is enabled."
  type        = number
  default     = 4
}

variable "autoscaling_cpu_target" {
  description = "Average CPU utilisation (%) the auto scaler tries to maintain."
  type        = number
  default     = 60
}

# ---------- Database (RDS MySQL) ----------
variable "db_name" {
  description = "Initial database (schema) name created in RDS."
  type        = string
  default     = "productdb"
}

variable "db_username" {
  description = "Master username for RDS. The password is generated and stored in Secrets Manager."
  type        = string
  default     = "product_user"
}

variable "db_engine_version" {
  description = "MySQL engine version. Major-only (8.4) lets RDS pick the latest minor version."
  type        = string
  default     = "8.4"
}

variable "db_instance_class" {
  description = "RDS instance size. db.t4g.micro is the cheapest Graviton option; db.t3.micro is the x86 equivalent."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "Storage size in GiB."
  type        = number
  default     = 20
}

variable "db_multi_az" {
  description = "Run a synchronous standby in a second AZ (roughly doubles the RDS cost)."
  type        = bool
  default     = false
}

variable "db_backup_retention_days" {
  description = "Automated backup retention (0 disables backups; 1-35)."
  type        = number
  default     = 1
}

variable "db_skip_final_snapshot" {
  description = "Skip the final snapshot on destroy. Set to false for anything that holds real data."
  type        = bool
  default     = true
}

variable "db_deletion_protection" {
  description = "Prevent accidental deletion of the database. Enable for production."
  type        = bool
  default     = false
}

variable "secret_recovery_window_days" {
  description = "Days before a deleted secret is really gone. 0 = immediate (lets you destroy/re-apply quickly in dev)."
  type        = number
  default     = 0
}

# ---------- HTTPS (optional) ----------
variable "certificate_arn" {
  description = "ARN of an existing validated ACM certificate (same region). Leave empty to let Terraform create one or to use HTTP only."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Public DNS name for the app (e.g. products.example.com). Requires route53_zone_id."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route 53 hosted zone ID that owns domain_name. Used for ACM DNS validation and the ALB alias record."
  type        = string
  default     = ""
}
