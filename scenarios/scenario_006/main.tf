terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_iam_user" "escalation_target_006" {
  name = "pilot-escalation-user-006"
}

resource "aws_iam_user_policy" "privilege_escalation_006" {
  name = "pilot-privilege-escalation-006"
  user = aws_iam_user.escalation_target_006.name

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect   = "Allow"
        Action   = ["iam:AttachUserPolicy"]
        Resource = "*"
      }
    ]
  })
}
