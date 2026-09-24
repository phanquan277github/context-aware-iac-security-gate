terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.5"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "random_pet" "suffix" {
  length = 2
}

locals {
  # Naming convention for all resources
  name_prefix   = "secure-example"
  name_suffix   = random_pet.suffix.id
  resource_name = "${local.name_prefix}-${local.name_suffix}"

  # Common tags for resource tagging and tracking
  common_tags = {
    Terraform   = "true"
    Environment = "production"
    Project     = "secure-s3-example"
  }
}

################################################################################
# KMS Keys for Encryption at Rest
# A best practice is to use a dedicated KMS CMK for each major resource/service.
################################################################################

resource "aws_kms_key" "s3_access_logs_key" {
  description             = "KMS CMK for encrypting S3 access log bucket"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = local.common_tags
}

resource "aws_kms_key" "s3_main_key" {
  description             = "KMS CMK for encrypting the main S3 bucket"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = local.common_tags
}

################################################################################
# S3 Bucket for Storing Access Logs
# This bucket must also be secure and is the target for the main bucket's logs.
################################################################################

resource "aws_s3_bucket" "access_logs" {
  bucket = "${local.resource_name}-access-logs"
  tags   = local.common_tags
}

resource "aws_s3_bucket_acl" "access_logs_acl" {
  bucket = aws_s3_bucket.access_logs.id
  acl    = "log-delivery-write"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_access_logs_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket                  = aws_s3_bucket.access_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "access_logs_enforce_tls" {
  bucket = aws_s3_bucket.access_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSSLRequestsOnly"
        Action    = "s3:*"
        Effect    = "Deny"
        Resource = [
          aws_s3_bucket.access_logs.arn,
          "${aws_s3_bucket.access_logs.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
        Principal = "*"
      },
    ]
  })
}

################################################################################
# Primary S3 Bucket with all Security Controls
################################################################################

resource "aws_s3_bucket" "main" {
  bucket = local.resource_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket                  = aws_s3_bucket.main.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.s3_main_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_logging" "main" {
  bucket = aws_s3_bucket.main.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "log/"
}

resource "aws_s3_bucket_policy" "main_enforce_tls" {
  bucket = aws_s3_bucket.main.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSSLRequestsOnly"
        Action    = "s3:*"
        Effect    = "Deny"
        Resource = [
          aws_s3_bucket.main.arn,
          "${aws_s3_bucket.main.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
        Principal = "*"
      },
    ]
  })
}

resource "aws_s3_bucket_object_lock_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  object_lock_enabled = "Enabled"

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 7
    }
  }
  depends_on = [aws_s3_bucket_versioning.main]
}
