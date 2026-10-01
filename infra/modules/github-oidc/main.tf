# One-time trust relationship: tells AWS to accept identity tokens issued
# by GitHub Actions, instead of requiring a stored access key/secret.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    "ab9d0263244dd0326eb67015705a667e79cfe998",
  ]
}

# The role GitHub Actions will assume. The trust policy below is the real
# security boundary: it only trusts tokens whose "sub" claim proves the
# request came from a workflow run on the main branch of this exact repo -
# nothing else can ever assume this role, even with the role's ARN in hand.
resource "aws_iam_role" "github_actions_cd" {
  name = "github-actions-cx-agent-cd"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = var.github_repo_sub
          }
        }
      }
    ]
  })
}

# Narrow permissions: push images to exactly this ECR repo, and redeploy
# exactly this Agent Runtime. Not admin access, not access to anything else
# in the account.
resource "aws_iam_role_policy" "github_actions_cd" {
  name = "github-actions-cx-agent-cd-policy"
  role = aws_iam_role.github_actions_cd.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ECRAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:BatchGetImage",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
        ]
        Resource = var.ecr_repository_arn
      },
      {
        Sid    = "AgentRuntimeRedeploy"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:UpdateAgentRuntime",
          "bedrock-agentcore:GetAgentRuntime",
        ]
        Resource = var.agent_runtime_arn
      },
      {
        Sid      = "PassExecutionRole"
        Effect   = "Allow"
        Action   = "iam:PassRole"
        Resource = var.agent_execution_role_arn
      },
    ]
  })
}


resource "aws_iam_role" "github_actions_terraform" {
  name = "github-actions-cx-agent-terraform"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = var.github_repo_sub
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "terraform_managed_policies" {
  for_each = toset([
    "arn:aws:iam::aws:policy/IAMFullAccess",
    "arn:aws:iam::aws:policy/AmazonCognitoPowerUser",
    "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    "arn:aws:iam::aws:policy/AmazonOpenSearchServiceFullAccess",
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    "arn:aws:iam::aws:policy/SecretsManagerReadWrite",
    "arn:aws:iam::aws:policy/AWSLambda_FullAccess",
    "arn:aws:iam::aws:policy/AmazonSQSFullAccess",
    "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess",
  ])
  role       = aws_iam_role.github_actions_terraform.name
  policy_arn = each.value
}

# Terraform's own state needs read/write access to the S3 state bucket +
# DynamoDB lock table - not covered by the FullAccess policies above in a
# resource-scoped way, so grant them explicitly.
resource "aws_iam_role_policy" "terraform_state_access" {
  name = "github-actions-cx-agent-terraform-state"
  role = aws_iam_role.github_actions_terraform.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "StateBucket"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::agentcore-cx-agent-tfstate-504736193889",
          "arn:aws:s3:::agentcore-cx-agent-tfstate-504736193889/*",
        ]
      },
      {
        Sid      = "StateLock"
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
        Resource = "arn:aws:dynamodb:us-west-2:504736193889:table/agentcore-cx-agent-tflock"
      },
    ]
  })
}
