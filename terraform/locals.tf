# -----------------------------------------------------------------------------
# Values computed from variables and reused across files.
# -----------------------------------------------------------------------------
locals {
  # Prefix for every resource name, e.g. "product-app-dev"
  name_prefix = "${var.project_name}-${var.environment}"

  # HTTPS handling (see acm.tf and alb.tf):
  #  - certificate_arn given           -> use that existing ACM certificate
  #  - domain_name + route53_zone_id   -> Terraform requests and validates a certificate
  #  - neither                         -> HTTP only (fine for a first demo)
  create_certificate = var.certificate_arn == "" && var.domain_name != "" && var.route53_zone_id != ""
  https_enabled      = var.certificate_arn != "" || local.create_certificate
  certificate_arn    = var.certificate_arn != "" ? var.certificate_arn : one(aws_acm_certificate_validation.app[*].certificate_arn)
}
