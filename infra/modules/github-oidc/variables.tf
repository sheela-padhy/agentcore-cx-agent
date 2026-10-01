variable "github_repo" {
  description = "GitHub repo allowed to assume this role, as owner/name (e.g. sheela-padhy/agentcore-cx-agent)"
  type        = string
}

variable "github_repo_sub" {
  description = <<-EOT
    The exact "sub" claim GitHub's OIDC token presents for a push to main on
    this repo. GitHub embeds immutable numeric IDs alongside the owner/repo
    names (format: repo:OWNER@OWNER_ID/REPO@REPO_ID:ref:refs/heads/main) to
    prevent impersonation via renaming - find the real value by temporarily
    adding a step that decodes and prints the token's claims.
  EOT
  type        = string
}

variable "ecr_repository_arn" {
  description = "ARN of the ECR repository GitHub Actions is allowed to push to"
  type        = string
}

variable "agent_runtime_arn" {
  description = "ARN of the Agent Runtime GitHub Actions is allowed to redeploy"
  type        = string
}

variable "agent_execution_role_arn" {
  description = "ARN of the role the Agent Runtime itself runs as (needed for iam:PassRole during redeploy)"
  type        = string
}
