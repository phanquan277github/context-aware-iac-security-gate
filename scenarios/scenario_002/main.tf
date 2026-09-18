terraform {
  required_version = "= 1.16.2"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 5.100.0"
    }
  }
}

resource "aws_s3_bucket" "data_002" {
  bucket = "pilot-s3-context-002"
}

resource "aws_s3_bucket_acl" "data_002" {
  bucket = aws_s3_bucket.data_002.id
  acl    = "public-read"
}

resource "aws_security_group" "web_002" {
  name        = "pilot-web-002"
  description = "Pilot security group"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_policy" "access_002" {
  name = "pilot-policy-002"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [{
      Effect   = "Allow"
      Action   = "*"
      Resource = "*"
    }]
  })
}
