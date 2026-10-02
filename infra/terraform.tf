terraform {
  # Remote state in S3 (+ DynamoDB for locking) - needed so GitHub Actions
  # runners (which start fresh every run, with no memory between runs) can
  # read/write the same state as local machines. Bucket and table were
  # created once, out-of-band, before this block existed (see memory /
  # session notes - a classic bootstrapping problem: you can't store the
  # state of "create the state bucket" inside that same bucket).
  backend "s3" {
    bucket         = "agentcore-cx-agent-tfstate-504736193889"
    key            = "agentcore-cx-agent/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "agentcore-cx-agent-tflock"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.27"
    }
  }
}
