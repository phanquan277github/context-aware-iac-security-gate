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

# ============================================================
# 1. Public S3 exposure
# ============================================================

resource "aws_s3_bucket" "public_data_009" {
  bucket = "pilot-public-data-009"
}

resource "aws_s3_bucket_public_access_block" "public_data_009" {
  bucket = aws_s3_bucket.public_data_009.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "public_data_009" {
  bucket = aws_s3_bucket.public_data_009.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "PublicRead"
        Effect = "Allow"

        Principal = "*"

        Action = [
          "s3:GetObject"
        ]

        Resource = "${aws_s3_bucket.public_data_009.arn}/*"
      }
    ]
  })
}

# ============================================================
# 2. IAM privilege escalation
# ============================================================

resource "aws_iam_user" "escalation_target_009" {
  name = "pilot-escalation-user-009"
}

resource "aws_iam_user_policy" "privilege_escalation_009" {
  name = "pilot-privilege-escalation-009"
  user = aws_iam_user.escalation_target_009.name

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

# ============================================================
# 3. Open administrative network access
# ============================================================

resource "aws_security_group" "admin_009" {
  name        = "pilot-admin-009"
  description = "Pilot administrative access"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
