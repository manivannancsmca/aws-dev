# -----------------------------------------------------------------------------
# ECR repository that stores the product-app Docker image.
# -----------------------------------------------------------------------------
resource "aws_ecr_repository" "app" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE" # allows re-pushing "latest"; use IMMUTABLE + git-SHA tags in production

  # Lets "terraform destroy" delete the repository even if it still contains images
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true # free vulnerability scan of every pushed image
  }
}

# Keep only the 10 most recent images to avoid paying for old ones
resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
