output "github_actions_role_arn" {
  description = "ARN GitHub Actions will use to authenticate to AWS via OIDC"
  value       = aws_iam_role.github_actions_cd.arn
}

output "github_actions_terraform_role_arn" {
  description = "ARN GitHub Actions will use for Terraform plan/apply via OIDC"
  value       = aws_iam_role.github_actions_terraform.arn
}
