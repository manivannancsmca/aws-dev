# -----------------------------------------------------------------------------
# OPTIONAL: HTTPS certificate from AWS Certificate Manager (ACM), validated
# automatically through DNS records in Route 53. Everything in this file is
# created only when domain_name AND route53_zone_id are set (and no
# certificate_arn is given). See locals.tf.
# -----------------------------------------------------------------------------
resource "aws_acm_certificate" "app" {
  count = local.create_certificate ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# ACM asks us to prove domain ownership by creating a CNAME record; Terraform does that for us
resource "aws_route53_record" "cert_validation" {
  for_each = local.create_certificate ? {
    for dvo in aws_acm_certificate.app[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  zone_id         = var.route53_zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

# Waits until ACM has seen the DNS record and issued the certificate
resource "aws_acm_certificate_validation" "app" {
  count = local.create_certificate ? 1 : 0

  certificate_arn         = aws_acm_certificate.app[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# DNS alias so https://<domain_name> points at the load balancer
resource "aws_route53_record" "app" {
  count = local.create_certificate ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}
