terraform {
  # Using LOCAL state (stored as a file on this EC2 instance) instead of
  # an S3 backend, since this is one person working alone, not a team
  # that needs shared, remote state.

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.18"
    }
  }
}
