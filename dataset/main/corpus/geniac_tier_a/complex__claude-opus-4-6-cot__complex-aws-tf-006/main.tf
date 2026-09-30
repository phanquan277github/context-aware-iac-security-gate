# =============================================================================
# Multi-Region Active-Active Web Application Infrastructure
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# -----------------------------------------------------------------------------
# Providers
# -----------------------------------------------------------------------------
provider "aws" {
  region = "us-east-1"
  alias  = "primary"
}

provider "aws" {
  region = "eu-west-1"
  alias  = "secondary"
}

# For CloudFront WAF and ACM (must be us-east-1)
provider "aws" {
  region = "us-east-1"
  alias  = "cloudfront_waf"
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
variable "domain_name" {
  description = "Primary domain name"
  type        = string
  default     = "example.com"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "multiregion-app"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "db_master_username" {
  description = "Aurora master username"
  type        = string
  default     = "appadmin"
  sensitive   = true
}

variable "db_master_password" {
  description = "Aurora master password"
  type        = string
  sensitive   = true
}

variable "route53_zone_id" {
  description = "Existing Route53 hosted zone ID"
  type        = string
}

locals {
  primary_region   = "us-east-1"
  secondary_region = "eu-west-1"

  primary_azs   = ["us-east-1a", "us-east-1b", "us-east-1c"]
  secondary_azs = ["eu-west-1a", "eu-west-1b", "eu-west-1c"]

  primary_vpc_cidr   = "10.0.0.0/16"
  secondary_vpc_cidr = "10.1.0.0/16"

  common_tags = {
    Application = var.app_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# =============================================================================
# DATA SOURCES
# =============================================================================
data "aws_route53_zone" "main" {
  provider = aws.primary
  zone_id  = var.route53_zone_id
}

data "aws_caller_identity" "current" {
  provider = aws.primary
}

data "aws_ami" "amazon_linux_primary" {
  provider    = aws.primary
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_ami" "amazon_linux_secondary" {
  provider    = aws.secondary
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# =============================================================================
# KMS KEYS
# =============================================================================
resource "aws_kms_key" "primary" {
  provider                = aws.primary
  description             = "${var.app_name} encryption key - primary"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = local.common_tags
}

resource "aws_kms_alias" "primary" {
  provider      = aws.primary
  name          = "alias/${var.app_name}-primary"
  target_key_id = aws_kms_key.primary.key_id
}

resource "aws_kms_key" "secondary" {
  provider                = aws.secondary
  description             = "${var.app_name} encryption key - secondary"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = local.common_tags
}

resource "aws_kms_alias" "secondary" {
  provider      = aws.secondary
  name          = "alias/${var.app_name}-secondary"
  target_key_id = aws_kms_key.secondary.key_id
}

# =============================================================================
# VPC - PRIMARY REGION
# =============================================================================
resource "aws_vpc" "primary" {
  provider             = aws.primary
  cidr_block           = local.primary_vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpc-primary"
  })
}

resource "aws_subnet" "primary_public" {
  provider          = aws.primary
  count             = length(local.primary_azs)
  vpc_id            = aws_vpc.primary.id
  cidr_block        = cidrsubnet(local.primary_vpc_cidr, 4, count.index)
  availability_zone = local.primary_azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-public-${local.primary_azs[count.index]}"
    Tier = "public"
  })
}

resource "aws_subnet" "primary_private" {
  provider          = aws.primary
  count             = length(local.primary_azs)
  vpc_id            = aws_vpc.primary.id
  cidr_block        = cidrsubnet(local.primary_vpc_cidr, 4, count.index + 3)
  availability_zone = local.primary_azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-private-${local.primary_azs[count.index]}"
    Tier = "private"
  })
}

resource "aws_subnet" "primary_database" {
  provider          = aws.primary
  count             = length(local.primary_azs)
  vpc_id            = aws_vpc.primary.id
  cidr_block        = cidrsubnet(local.primary_vpc_cidr, 4, count.index + 6)
  availability_zone = local.primary_azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-database-${local.primary_azs[count.index]}"
    Tier = "database"
  })
}

resource "aws_internet_gateway" "primary" {
  provider = aws.primary
  vpc_id   = aws_vpc.primary.id

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-igw-primary"
  })
}

resource "aws_eip" "primary_nat" {
  provider = aws.primary
  count    = length(local.primary_azs)
  domain   = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-nat-eip-primary-${count.index}"
  })
}

resource "aws_nat_gateway" "primary" {
  provider      = aws.primary
  count         = length(local.primary_azs)
  allocation_id = aws_eip.primary_nat[count.index].id
  subnet_id     = aws_subnet.primary_public[count.index].id

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-nat-primary-${count.index}"
  })

  depends_on = [aws_internet_gateway.primary]
}

resource "aws_route_table" "primary_public" {
  provider = aws.primary
  vpc_id   = aws_vpc.primary.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.primary.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-rt-public-primary"
  })
}

resource "aws_route_table_association" "primary_public" {
  provider       = aws.primary
  count          = length(local.primary_azs)
  subnet_id      = aws_subnet.primary_public[count.index].id
  route_table_id = aws_route_table.primary_public.id
}

resource "aws_route_table" "primary_private" {
  provider = aws.primary
  count    = length(local.primary_azs)
  vpc_id   = aws_vpc.primary.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.primary[count.index].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-rt-private-primary-${count.index}"
  })
}

resource "aws_route_table_association" "primary_private" {
  provider       = aws.primary
  count          = length(local.primary_azs)
  subnet_id      = aws_subnet.primary_private[count.index].id
  route_table_id = aws_route_table.primary_private[count.index].id
}

resource "aws_route_table_association" "primary_database" {
  provider       = aws.primary
  count          = length(local.primary_azs)
  subnet_id      = aws_subnet.primary_database[count.index].id
  route_table_id = aws_route_table.primary_private[count.index].id
}

# =============================================================================
# VPC - SECONDARY REGION
# =============================================================================
resource "aws_vpc" "secondary" {
  provider             = aws.secondary
  cidr_block           = local.secondary_vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpc-secondary"
  })
}

resource "aws_subnet" "secondary_public" {
  provider          = aws.secondary
  count             = length(local.secondary_azs)
  vpc_id            = aws_vpc.secondary.id
  cidr_block        = cidrsubnet(local.secondary_vpc_cidr, 4, count.index)
  availability_zone = local.secondary_azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-public-${local.secondary_azs[count.index]}"
    Tier = "public"
  })
}

resource "aws_subnet" "secondary_private" {
  provider          = aws.secondary
  count             = length(local.secondary_azs)
  vpc_id            = aws_vpc.secondary.id
  cidr_block        = cidrsubnet(local.secondary_vpc_cidr, 4, count.index + 3)
  availability_zone = local.secondary_azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-private-${local.secondary_azs[count.index]}"
    Tier = "private"
  })
}

resource "aws_subnet" "secondary_database" {
  provider          = aws.secondary
  count             = length(local.secondary_azs)
  vpc_id            = aws_vpc.secondary.id
  cidr_block        = cidrsubnet(local.secondary_vpc_cidr, 4, count.index + 6)
  availability_zone = local.secondary_azs[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-database-${local.secondary_azs[count.index]}"
    Tier = "database"
  })
}

resource "aws_internet_gateway" "secondary" {
  provider = aws.secondary
  vpc_id   = aws_vpc.secondary.id

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-igw-secondary"
  })
}

resource "aws_eip" "secondary_nat" {
  provider = aws.secondary
  count    = length(local.secondary_azs)
  domain   = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-nat-eip-secondary-${count.index}"
  })
}

resource "aws_nat_gateway" "secondary" {
  provider      = aws.secondary
  count         = length(local.secondary_azs)
  allocation_id = aws_eip.secondary_nat[count.index].id
  subnet_id     = aws_subnet.secondary_public[count.index].id

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-nat-secondary-${count.index}"
  })

  depends_on = [aws_internet_gateway.secondary]
}

resource "aws_route_table" "secondary_public" {
  provider = aws.secondary
  vpc_id   = aws_vpc.secondary.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.secondary.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-rt-public-secondary"
  })
}

resource "aws_route_table_association" "secondary_public" {
  provider       = aws.secondary
  count          = length(local.secondary_azs)
  subnet_id      = aws_subnet.secondary_public[count.index].id
  route_table_id = aws_route_table.secondary_public.id
}

resource "aws_route_table" "secondary_private" {
  provider = aws.secondary
  count    = length(local.secondary_azs)
  vpc_id   = aws_vpc.secondary.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.secondary[count.index].id
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-rt-private-secondary-${count.index}"
  })
}

resource "aws_route_table_association" "secondary_private" {
  provider       = aws.secondary
  count          = length(local.secondary_azs)
  subnet_id      = aws_subnet.secondary_private[count.index].id
  route_table_id = aws_route_table.secondary_private[count.index].id
}

resource "aws_route_table_association" "secondary_database" {
  provider       = aws.secondary
  count          = length(local.secondary_azs)
  subnet_id      = aws_subnet.secondary_database[count.index].id
  route_table_id = aws_route_table.secondary_private[count.index].id
}

# =============================================================================
# SSM VPC ENDPOINTS - PRIMARY
# =============================================================================
resource "aws_security_group" "primary_vpc_endpoints" {
  provider    = aws.primary
  name_prefix = "${var.app_name}-vpce-primary-"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [local.primary_vpc_cidr]
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpce-sg-primary"
  })
}

resource "aws_vpc_endpoint" "primary_ssm" {
  provider            = aws.primary
  vpc_id              = aws_vpc.primary.id
  service_name        = "com.amazonaws.${local.primary_region}.ssm"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.primary_private[*].id
  security_group_ids  = [aws_security_group.primary_vpc_endpoints.id]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpce-ssm-primary"
  })
}

resource "aws_vpc_endpoint" "primary_ssmmessages" {
  provider            = aws.primary
  vpc_id              = aws_vpc.primary.id
  service_name        = "com.amazonaws.${local.primary_region}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.primary_private[*].id
  security_group_ids  = [aws_security_group.primary_vpc_endpoints.id]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpce-ssmmessages-primary"
  })
}

resource "aws_vpc_endpoint" "primary_ec2messages" {
  provider            = aws.primary
  vpc_id              = aws_vpc.primary.id
  service_name        = "com.amazonaws.${local.primary_region}.ec2messages"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.primary_private[*].id
  security_group_ids  = [aws_security_group.primary_vpc_endpoints.id]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpce-ec2messages-primary"
  })
}

# =============================================================================
# SSM VPC ENDPOINTS - SECONDARY
# =============================================================================
resource "aws_security_group" "secondary_vpc_endpoints" {
  provider    = aws.secondary
  name_prefix = "${var.app_name}-vpce-secondary-"
  vpc_id      = aws_vpc.secondary.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [local.secondary_vpc_cidr]
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpce-sg-secondary"
  })
}

resource "aws_vpc_endpoint" "secondary_ssm" {
  provider            = aws.secondary
  vpc_id              = aws_vpc.secondary.id
  service_name        = "com.amazonaws.${local.secondary_region}.ssm"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.secondary_private[*].id
  security_group_ids  = [aws_security_group.secondary_vpc_endpoints.id]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpce-ssm-secondary"
  })
}

resource "aws_vpc_endpoint" "secondary_ssmmessages" {
  provider            = aws.secondary
  vpc_id              = aws_vpc.secondary.id
  service_name        = "com.amazonaws.${local.secondary_region}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.secondary_private[*].id
  security_group_ids  = [aws_security_group.secondary_vpc_endpoints.id]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpce-ssmmessages-secondary"
  })
}

resource "aws_vpc_endpoint" "secondary_ec2messages" {
  provider            = aws.secondary
  vpc_id              = aws_vpc.secondary.id
  service_name        = "com.amazonaws.${local.secondary_region}.ec2messages"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.secondary_private[*].id
  security_group_ids  = [aws_security_group.secondary_vpc_endpoints.id]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-vpce-ec2messages-secondary"
  })
}

# =============================================================================
# IAM ROLE FOR EC2 INSTANCES (SSM)
# =============================================================================
resource "aws_iam_role" "ec2_ssm" {
  provider = aws.primary
  name     = "${var.app_name}-ec2-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ssm_managed" {
  provider   = aws.primary
  role       = aws_iam_role.ec2_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  provider   = aws.primary
  role       = aws_iam_role.ec2_ssm.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "ec2_ssm" {
  provider = aws.primary
  name     = "${var.app_name}-ec2-ssm-profile"
  role     = aws_iam_role.ec2_ssm.name

  tags = local.common_tags
}

# =============================================================================
# ACM CERTIFICATES
# =============================================================================

# CloudFront certificate (must be us-east-1)
resource "aws_acm_certificate" "cloudfront" {
  provider          = aws.primary
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = [
    "*.${var.domain_name}"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-cert-cloudfront"
  })
}

resource "aws_route53_record" "cloudfront_cert_validation" {
  provider = aws.primary
  for_each = {
    for dvo in aws_acm_certificate.cloudfront.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "cloudfront" {
  provider                = aws.primary
  certificate_arn         = aws_acm_certificate.cloudfront.arn
  validation_record_fqdns = [for record in aws_route53_record.cloudfront_cert_validation : record.fqdn]
}

# Primary ALB certificate
resource "aws_acm_certificate" "primary_alb" {
  provider          = aws.primary
  domain_name       = "alb-primary.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-cert-alb-primary"
  })
}

resource "aws_route53_record" "primary_alb_cert_validation" {
  provider = aws.primary
  for_each = {
    for dvo in aws_acm_certificate.primary_alb.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "primary_alb" {
  provider                = aws.primary
  certificate_arn         = aws_acm_certificate.primary_alb.arn
  validation_record_fqdns = [for record in aws_route53_record.primary_alb_cert_validation : record.fqdn]
}

# Secondary ALB certificate
resource "aws_acm_certificate" "secondary_alb" {
  provider          = aws.secondary
  domain_name       = "alb-secondary.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-cert-alb-secondary"
  })
}

resource "aws_route53_record" "secondary_alb_cert_validation" {
  provider = aws.primary
  for_each = {
    for dvo in aws_acm_certificate.secondary_alb.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "secondary_alb" {
  provider                = aws.secondary
  certificate_arn         = aws_acm_certificate.secondary_alb.arn
  validation_record_fqdns = [for record in aws_route53_record.secondary_alb_cert_validation : record.fqdn]
}

# =============================================================================
# SECURITY GROUPS - PRIMARY
# =============================================================================
resource "aws_security_group" "primary_alb" {
  provider    = aws.primary
  name_prefix = "${var.app_name}-alb-primary-"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-alb-sg-primary"
  })
}

resource "aws_security_group" "primary_app" {
  provider    = aws.primary
  name_prefix = "${var.app_name}-app-primary-"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.primary_alb.id]
  }

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.primary_vpc_endpoints.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-app-sg-primary"
  })
}

resource "aws_security_group" "primary_db" {
  provider    = aws.primary
  name_prefix = "${var.app_name}-db-primary-"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.primary_app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-db-sg-primary"
  })
}

# =============================================================================
# SECURITY GROUPS - SECONDARY
# =============================================================================
resource "aws_security_group" "secondary_alb" {
  provider    = aws.secondary
  name_prefix = "${var.app_name}-alb-secondary-"
  vpc_id      = aws_vpc.secondary.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-alb-sg-secondary"
  })
}

resource "aws_security_group" "secondary_app" {
  provider    = aws.secondary
  name_prefix = "${var.app_name}-app-secondary-"
  vpc_id      = aws_vpc.secondary.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.secondary_alb.id]
  }

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.secondary_vpc_endpoints.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-app-sg-secondary"
  })
}

resource "aws_security_group" "secondary_db" {
  provider    = aws.secondary
  name_prefix = "${var.app_name}-db-secondary-"
  vpc_id      = aws_vpc.secondary.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.secondary_app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-db-sg-secondary"
  })
}

# =============================================================================
# ALB - PRIMARY
# =============================================================================
resource "aws_lb" "primary" {
  provider           = aws.primary
  name               = "${var.app_name}-alb-primary"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.primary_alb.id]
  subnets            = aws_subnet.primary_public[*].id

  enable_deletion_protection = true
  drop_invalid_header_fields = true

  access_logs {
    bucket  = aws_s3_bucket.primary_alb_logs.id
    prefix  = "alb-logs"
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-alb-primary"
  })
}

resource "aws_s3_bucket" "primary_alb_logs" {
  provider      = aws.primary
  bucket_prefix = "${var.app_name}-alb-logs-primary-"
  force_destroy = true

  tags = local.common_tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "primary_alb_logs" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary_alb_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "primary_alb_logs" {
  provider                = aws.primary
  bucket                  = aws_s3_bucket.primary_alb_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_elb_service_account" "primary" {
  provider = aws.primary
}

resource "aws_s3_bucket_policy" "primary_alb_logs" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary_alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = data.aws_elb_service_account.primary.arn
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.primary_alb_logs.arn}/alb-logs/*"
      }
    ]
  })
}

resource "aws_lb_target_group" "primary" {
  provider = aws.primary
  name     = "${var.app_name}-tg-primary"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.primary.id

  health_check {
    enabled             = true
    healthy_threshold   = 3
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-tg-primary"
  })
}

resource "aws_lb_listener" "primary_https" {
  provider          = aws.primary
  load_balancer_arn = aws_lb.primary.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.primary_alb.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.primary.arn
  }
}

resource "aws_lb_listener" "primary_http_redirect" {
  provider          = aws.primary
  load_balancer_arn = aws_lb.primary.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# =============================================================================
# ALB - SECONDARY
# =============================================================================
resource "aws_lb" "secondary" {
  provider           = aws.secondary
  name               = "${var.app_name}-alb-secondary"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.secondary_alb.id]
  subnets            = aws_subnet.secondary_public[*].id

  enable_deletion_protection = true
  drop_invalid_header_fields = true

  access_logs {
    bucket  = aws_s3_bucket.secondary_alb_logs.id
    prefix  = "alb-logs"
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-alb-secondary"
  })
}

resource "aws_s3_bucket" "secondary_alb_logs" {
  provider      = aws.secondary
  bucket_prefix = "${var.app_name}-alb-logs-secondary-"
  force_destroy = true

  tags = local.common_tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "secondary_alb_logs" {
  provider = aws.secondary
  bucket   = aws_s3_bucket.secondary_alb_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "secondary_alb_logs" {
  provider                = aws.secondary
  bucket                  = aws_s3_bucket.secondary_alb_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_elb_service_account" "secondary" {
  provider = aws.secondary
}

resource "aws_s3_bucket_policy" "secondary_alb_logs" {
  provider = aws.secondary
  bucket   = aws_s3_bucket.secondary_alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = data.aws_elb_service_account.secondary.arn
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.secondary_alb_logs.arn}/alb-logs/*"
      }
    ]
  })
}

resource "aws_lb_target_group" "secondary" {
  provider = aws.secondary
  name     = "${var.app_name}-tg-secondary"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.secondary.id

  health_check {
    enabled             = true
    healthy_threshold   = 3
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-tg-secondary"
  })
}

resource "aws_lb_listener" "secondary_https" {
  provider          = aws.secondary
  load_balancer_arn = aws_lb.secondary.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.secondary_alb.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.secondary.arn
  }
}

resource "aws_lb_listener" "secondary_http_redirect" {
  provider          = aws.secondary
  load_balancer_arn = aws_lb.secondary.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# =============================================================================
# LAUNCH TEMPLATES & ASG - PRIMARY
# =============================================================================
resource "aws_launch_template" "primary" {
  provider    = aws.primary
  name_prefix = "${var.app_name}-lt-primary-"
  image_id    = data.aws_ami.amazon_linux_primary.id

  iam_instance_profile {
    arn = aws_iam_instance_profile.ec2_ssm.arn
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 30
      volume_type           = "gp3"
      encrypted             = true
      kms_key_id            = aws_kms_key.primary.arn
      delete_on_termination = true
    }
  }

  network_interfaces {
    associate_public_ip_address = false
    security_groups             = [aws_security_group.primary_app.id]
  }

  monitoring {
    enabled = true
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y amazon-ssm-agent
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
    # Install and start web application
    yum install -y httpd
    systemctl enable httpd
    systemctl start httpd
    echo "OK" > /var/www/html/health
    REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
    echo "<h1>Hello from $REGION</h1>" > /var/www/html/index.html
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "${var.app_name}-instance-primary"
    })
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(local.common_tags, {
      Name = "${var.app_name}-volume-primary"
    })
  }

  tags = local.common_tags
}

resource "aws_autoscaling_group" "primary" {
  provider            = aws.primary
  name_prefix         = "${var.app_name}-asg-primary-"
  vpc_zone_identifier = aws_subnet.primary_private[*].id
  target_group_arns   = [aws_lb_target_group.primary.arn]
  min_size            = 2
  max_size            = 10
  desired_capacity    = 3
  health_check_type   = "ELB"

  health_check_grace_period = 300

  mixed_instances_policy {
    instances_distribution {
      on_demand_base_capacity                  = 1
      on_demand_percentage_above_base_capacity = 25
      spot_allocation_strategy                 = "capacity-optimized"
    }

    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.primary.id
        version            = "$Latest"
      }

      override {
        instance_type     = "t3.large"
        weighted_capacity = "1"
      }

      override {
        instance_type     = "t3a.large"
        weighted_capacity = "1"
      }

      override {
        instance_type     = "m5.large"
        weighted_capacity = "1"
      }

      override {
        instance_type     = "m5a.large"
        weighted_capacity = "1"
      }
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.app_name}-asg-primary"
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = local.common_tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}

resource "aws_autoscaling_policy" "primary_target_tracking" {
  provider               = aws.primary
  name                   = "${var.app_name}-target-tracking-primary"
  autoscaling_group_name = aws_autoscaling_group.primary.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.primary.arn_suffix}/${aws_lb_target_group.primary.arn_suffix}"
    }
    target_value = 1000
  }
}

# =============================================================================
# LAUNCH TEMPLATES & ASG - SECONDARY
# =============================================================================
resource "aws_launch_template" "secondary" {
  provider    = aws.secondary
  name_prefix = "${var.app_name}-lt-secondary-"
  image_id    = data.aws_ami.amazon_linux_secondary.id

  iam_instance_profile {
    arn = aws_iam_instance_profile.ec2_ssm.arn
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 30
      volume_type           = "gp3"
      encrypted             = true
      kms_key_id            = aws_kms_key.secondary.arn
      delete_on_termination = true
    }
  }

  network_interfaces {
    associate_public_ip_address = false
    security_groups             = [aws_security_group.secondary_app.id]
  }

  monitoring {
    enabled = true
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y amazon-ssm-agent
    systemctl enable amazon-ssm-agent
    systemctl start amazon-ssm-agent
    yum install -y httpd
    systemctl enable httpd
    systemctl start httpd
    echo "OK" > /var/www/html/health
    REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
    echo "<h1>Hello from $REGION</h1>" > /var/www/html/index.html
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "${var.app_name}-instance-secondary"
    })
  }

  tag_specifications {
    resource_type = "volume"
    tags = merge(local.common_tags, {
      Name = "${var.app_name}-volume-secondary"
    })
  }

  tags = local.common_tags
}

resource "aws_autoscaling_group" "secondary" {
  provider            = aws.secondary
  name_prefix         = "${var.app_name}-asg-secondary-"
  vpc_zone_identifier = aws_subnet.secondary_private[*].id
  target_group_arns   = [aws_lb_target_group.secondary.arn]
  min_size            = 2
  max_size            = 10
  desired_capacity    = 3
  health_check_type   = "ELB"

  health_check_grace_period = 300

  mixed_instances_policy {
    instances_distribution {
      on_demand_base_capacity                  = 1
      on_demand_percentage_above_base_capacity = 25
      spot_allocation_strategy                 = "capacity-optimized"
    }

    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.secondary.id
        version            = "$Latest"
      }

      override {
        instance_type     = "t3.large"
        weighted_capacity = "1"
      }

      override {
        instance_type     = "t3a.large"
        weighted_capacity = "1"
      }

      override {
        instance_type     = "m5.large"
        weighted_capacity = "1"
      }

      override {
        instance_type     = "m5a.large"
        weighted_capacity = "1"
      }
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.app_name}-asg-secondary"
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = local.common_tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}

resource "aws_autoscaling_policy" "secondary_target_tracking" {
  provider               = aws.secondary
  name                   = "${var.app_name}-target-tracking-secondary"
  autoscaling_group_name = aws_autoscaling_group.secondary.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.secondary.arn_suffix}/${aws_lb_target_group.secondary.arn_suffix}"
    }
    target_value = 1000
  }
}

# =============================================================================
# S3 STATIC ASSETS BUCKETS
# =============================================================================
resource "aws_s3_bucket" "static_assets_primary" {
  provider      = aws.primary
  bucket_prefix = "${var.app_name}-static-primary-"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-static-primary"
  })
}

resource "aws_s3_bucket_versioning" "static_assets_primary" {
  provider = aws.primary
  bucket   = aws_s3_bucket.static_assets_primary.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "static_assets_primary" {
  provider = aws.primary
  bucket   = aws_s3_bucket.static_assets_primary.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "static_assets_primary" {
  provider                = aws.primary
  bucket                  = aws_s3_bucket.static_assets_primary.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "static_assets_primary" {
  provider = aws.primary
  bucket   = aws_s3_bucket.static_assets_primary.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.static_assets_primary.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.primary.arn
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket" "static_assets_secondary" {
  provider      = aws.secondary
  bucket_prefix = "${var.app_name}-static-secondary-"
  force_destroy = true

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-static-secondary"
  })
}

resource "aws_s3_bucket_versioning" "static_assets_secondary" {
  provider = aws.secondary
  bucket   = aws_s3_bucket.static_assets_secondary.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "static_assets_secondary" {
  provider = aws.secondary
  bucket   = aws_s3_bucket.static_assets_secondary.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "static_assets_secondary" {
  provider                = aws.secondary
  bucket                  = aws_s3_bucket.static_assets_secondary.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "static_assets_secondary" {
  provider = aws.secondary
  bucket   = aws_s3_bucket.static_assets_secondary.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.static_assets_secondary.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.secondary.arn
          }
        }
      }
    ]
  })
}

# =============================================================================
# WAFv2 - CLOUDFRONT (must be us-east-1)
# =============================================================================
resource "aws_wafv2_web_acl" "cloudfront" {
  provider    = aws.cloudfront_waf
  name        = "${var.app_name}-waf-cloudfront"
  description = "WAF for CloudFront distributions"
  scope       = "CLOUDFRONT"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesBotControlRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesBotControlRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesBotControlRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "RateLimitRule"
    priority = 4

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRuleMetric"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "CloudFrontWAFMetric"
    sampled_requests_enabled   = true
  }

  tags = local.common_tags
}

# =============================================================================
# WAFv2 - ALB PRIMARY (REGIONAL)
# =============================================================================
resource "aws_wafv2_web_acl" "alb_primary" {
  provider    = aws.primary
  name        = "${var.app_name}-waf-alb-primary"
  description = "WAF for primary ALB"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "PrimaryALBCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "PrimaryALBSQLiRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesBotControlRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesBotControlRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "PrimaryALBBotControlMetric"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "PrimaryALBWAFMetric"
    sampled_requests_enabled   = true
  }

  tags = local.common_tags
}

resource "aws_wafv2_web_acl_association" "alb_primary" {
  provider     = aws.primary
  resource_arn = aws_lb.primary.arn
  web_acl_arn  = aws_wafv2_web_acl.alb_primary.arn
}

# =============================================================================
# WAFv2 - ALB SECONDARY (REGIONAL)
# =============================================================================
resource "aws_wafv2_web_acl" "alb_secondary" {
  provider    = aws.secondary
  name        = "${var.app_name}-waf-alb-secondary"
  description = "WAF for secondary ALB"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SecondaryALBCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SecondaryALBSQLiRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesBotControlRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesBotControlRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SecondaryALBBotControlMetric"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "SecondaryALBWAFMetric"
    sampled_requests_enabled   = true
  }

  tags = local.common_tags
}

resource "aws_wafv2_web_acl_association" "alb_secondary" {
  provider     = aws.secondary
  resource_arn = aws_lb.secondary.arn
  web_acl_arn  = aws_wafv2_web_acl.alb_secondary.arn
}

# =============================================================================
# CLOUDFRONT - ORIGIN ACCESS CONTROL
# =============================================================================
resource "aws_cloudfront_origin_access_control" "primary" {
  provider                          = aws.primary
  name                              = "${var.app_name}-oac-primary"
  description                       = "OAC for primary S3 static assets"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "secondary" {
  provider                          = aws.primary
  name                              = "${var.app_name}-oac-secondary"
  description                       = "OAC for secondary S3 static assets"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# =============================================================================
# CLOUDFRONT DISTRIBUTIONS
# =============================================================================
resource "aws_cloudfront_distribution" "primary" {
  provider        = aws.primary
  enabled         = true
  is_ipv6_enabled = true
  comment         = "${var.app_name} primary distribution"
  web_acl_id      = aws_wafv2_web_acl.cloudfront.arn

  aliases = ["primary.${var.domain_name}"]

  # ALB Origin
  origin {
    domain_name = aws_lb.primary.dns_name
    origin_id   = "alb-primary"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # S3 Static Assets Origin with OAC
  origin {
    domain_name              = aws_s3_bucket.static_assets_primary.bucket_regional_domain_name
    origin_id                = "s3-static-primary"
    origin_access_control_id = aws_cloudfront_origin_access_control.primary.id
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "alb-primary"

    forwarded_values {
      query_string = true
      headers      = ["Host", "Origin", "Authorization"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }

  ordered_cache_behavior {
    path_pattern     = "/static/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-static-primary"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.cloudfront.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-cf-primary"
  })
}

resource "aws_cloudfront_distribution" "secondary" {
  provider        = aws.primary
  enabled         = true
  is_ipv6_enabled = true
  comment         = "${var.app_name} secondary distribution"
  web_acl_id      = aws_wafv2_web_acl.cloudfront.arn

  aliases = ["secondary.${var.domain_name}"]

  # ALB Origin
  origin {
    domain_name = aws_lb.secondary.dns_name
    origin_id   = "alb-secondary"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # S3 Static Assets Origin with OAC
  origin {
    domain_name              = aws_s3_bucket.static_assets_secondary.bucket_regional_domain_name
    origin_id                = "s3-static-secondary"
    origin_access_control_id = aws_cloudfront_origin_access_control.secondary.id
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "alb-secondary"

    forwarded_values {
      query_string = true
      headers      = ["Host", "Origin", "Authorization"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }

  ordered_cache_behavior {
    path_pattern     = "/static/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-static-secondary"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.cloudfront.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-cf-secondary"
  })
}

# =============================================================================
# ROUTE53 HEALTH CHECKS & LATENCY-BASED ROUTING
# =============================================================================
resource "aws_route53_health_check" "primary" {
  provider          = aws.primary
  fqdn              = "primary.${var.domain_name}"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-hc-primary"
  })
}

resource "aws_route53_health_check" "secondary" {
  provider          = aws.primary
  fqdn              = "secondary.${var.domain_name}"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 30

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-hc-secondary"
  })
}

# CloudFront CNAME records
resource "aws_route53_record" "primary_cf" {
  provider = aws.primary
  zone_id  = data.aws_route53_zone.main.zone_id
  name     = "primary.${var.domain_name}"
  type     = "A"

  alias {
    name                   = aws_cloudfront_distribution.primary.domain_name
    zone_id                = aws_cloudfront_distribution.primary.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "secondary_cf" {
  provider = aws.primary
  zone_id  = data.aws_route53_zone.main.zone_id
  name     = "secondary.${var.domain_name}"
  type     = "A"

  alias {
    name                   = aws_cloudfront_distribution.secondary.domain_name
    zone_id                = aws_cloudfront_distribution.secondary.hosted_zone_id
    evaluate_target_health = false
  }
}

# ALB DNS records
resource "aws_route53_record" "primary_alb" {
  provider = aws.primary
  zone_id  = data.aws_route53_zone.main.zone_id
  name     = "alb-primary.${var.domain_name}"
  type     = "A"

  alias {
    name                   = aws_lb.primary.dns_name
    zone_id                = aws_lb.primary.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "secondary_alb" {
  provider = aws.primary
  zone_id  = data.aws_route53_zone.main.zone_id
  name     = "alb-secondary.${var.domain_name}"
  type     = "A"

  alias {
    name                   = aws_lb.secondary.dns_name
    zone_id                = aws_lb.secondary.zone_id
    evaluate_target_health = true
  }
}

# Latency-based routing for the main domain
resource "aws_route53_record" "app_primary" {
  provider       = aws.primary
  zone_id        = data.aws_route53_zone.main.zone_id
  name           = "app.${var.domain_name}"
  type           = "A"
  set_identifier = "primary"

  alias {
    name                   = aws_cloudfront_distribution.primary.domain_name
    zone_id                = aws_cloudfront_distribution.primary.hosted_zone_id
    evaluate_target_health = true
  }

  latency_routing_policy {
    region = local.primary_region
  }

  health_check_id = aws_route53_health_check.primary.id
}

resource "aws_route53_record" "app_secondary" {
  provider       = aws.primary
  zone_id        = data.aws_route53_zone.main.zone_id
  name           = "app.${var.domain_name}"
  type           = "A"
  set_identifier = "secondary"

  alias {
    name                   = aws_cloudfront_distribution.secondary.domain_name
    zone_id                = aws_cloudfront_distribution.secondary.hosted_zone_id
    evaluate_target_health = true
  }

  latency_routing_policy {
    region = local.secondary_region
  }

  health_check_id = aws_route53_health_check.secondary.id
}

# =============================================================================
# SHIELD ADVANCED
# =============================================================================
resource "aws_shield_protection" "primary_alb" {
  provider     = aws.primary
  name         = "${var.app_name}-shield-alb-primary"
  resource_arn = aws_lb.primary.arn

  tags = local.common_tags
}

resource "aws_shield_protection" "secondary_alb" {
  provider     = aws.secondary
  name         = "${var.app_name}-shield-alb-secondary"
  resource_arn = aws_lb.secondary.arn

  tags = local.common_tags
}

resource "aws_shield_protection" "cloudfront_primary" {
  provider     = aws.primary
  name         = "${var.app_name}-shield-cf-primary"
  resource_arn = aws_cloudfront_distribution.primary.arn

  tags = local.common_tags
}

resource "aws_shield_protection" "cloudfront_secondary" {
  provider     = aws.primary
  name         = "${var.app_name}-shield-cf-secondary"
  resource_arn = aws_cloudfront_distribution.secondary.arn

  tags = local.common_tags
}

resource "aws_shield_protection" "route53" {
  provider     = aws.primary
  name         = "${var.app_name}-shield-route53"
  resource_arn = "arn:aws:route53:::hostedzone/${data.aws_route53_zone.main.zone_id}"

  tags = local.common_tags
}

# Shield Advanced subscription (account-level)
resource "aws_shield_subscription" "main" {
  provider   = aws.primary
  auto_renew = "ENABLED"
}

# DRT access role
resource "aws_iam_role" "drt_access" {
  provider = aws.primary
  name     = "${var.app_name}-shield-drt-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "drt.shield.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "drt_access" {
  provider   = aws.primary
  role       = aws_iam_role.drt_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSShieldDRTAccessPolicy"
}

resource "aws_shield_drt_access_role_arn_association" "main" {
  provider = aws.primary
  role_arn = aws_iam_role.drt_access.arn

  depends_on = [aws_shield_subscription.main]
}

resource "aws_shield_proactive_engagement" "main" {
  provider = aws.primary
  enabled  = true

  emergency_contact {
    email_address = "security@${var.domain_name}"
    phone_number  = "+15555555555"
    contact_notes = "Primary security contact for DDoS response"
  }

  depends_on = [aws_shield_drt_access_role_arn_association.main]
}

# =============================================================================
# AURORA GLOBAL DATABASE
# =============================================================================
resource "aws_rds_global_cluster" "main" {
  provider                  = aws.primary
  global_cluster_identifier = "${var.app_name}-global-db"
  engine                    = "aurora-mysql"
  engine_version            = "8.0.mysql_aurora.3.04.1"
  database_name             = replace(var.app_name, "-", "_")
  storage_encrypted         = true
  deletion_protection       = true
}

# Primary Aurora Cluster
resource "aws_db_subnet_group" "primary" {
  provider   = aws.primary
  name       = "${var.app_name}-db-subnet-primary"
  subnet_ids = aws_subnet.primary_database[*].id

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-db-subnet-primary"
  })
}

resource "aws_rds_cluster" "primary" {
  provider                    = aws.primary
  cluster_identifier          = "${var.app_name}-aurora-primary"
  global_cluster_identifier   = aws_rds_global_cluster.main.id
  engine                      = aws_rds_global_cluster.main.engine
  engine_version              = aws_rds_global_cluster.main.engine_version
  database_name               = replace(var.app_name, "-", "_")
  master_username             = var.db_master_username
  master_password             = var.db_master_password
  db_subnet_group_name        = aws_db_subnet_group.primary.name
  vpc_security_group_ids      = [aws_security_group.primary_db.id]
  storage_encrypted           = true
  kms_key_id                  = aws_kms_key.primary.arn
  backup_retention_period     = 35
  preferred_backup_window     = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  deletion_protection         = true
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${var.app_name}-aurora-primary-final"
  enabled_cloudwatch_logs_exports = ["audit", "error", "general", "slowquery"]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-aurora-primary"
  })

  lifecycle {
    ignore_changes = [engine_version]
  }
}

resource "aws_rds_cluster_instance" "primary" {
  provider                  = aws.primary
  count                     = 2
  identifier                = "${var.app_name}-aurora-primary-${count.index}"
  cluster_identifier        = aws_rds_cluster.primary.id
  instance_class            = "db.r6g.large"
  engine                    = aws_rds_global_cluster.main.engine
  engine_version            = aws_rds_global_cluster.main.engine_version
  db_subnet_group_name      = aws_db_subnet_group.primary.name
  publicly_accessible       = false
  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.primary.arn

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-aurora-primary-${count.index}"
  })
}

# Secondary Aurora Cluster
resource "aws_db_subnet_group" "secondary" {
  provider   = aws.secondary
  name       = "${var.app_name}-db-subnet-secondary"
  subnet_ids = aws_subnet.secondary_database[*].id

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-db-subnet-secondary"
  })
}

resource "aws_rds_cluster" "secondary" {
  provider                    = aws.secondary
  cluster_identifier          = "${var.app_name}-aurora-secondary"
  global_cluster_identifier   = aws_rds_global_cluster.main.id
  engine                      = aws_rds_global_cluster.main.engine
  engine_version              = aws_rds_global_cluster.main.engine_version
  db_subnet_group_name        = aws_db_subnet_group.secondary.name
  vpc_security_group_ids      = [aws_security_group.secondary_db.id]
  storage_encrypted           = true
  kms_key_id                  = aws_kms_key.secondary.arn
  backup_retention_period     = 35
  preferred_backup_window     = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  deletion_protection         = true
  skip_final_snapshot         = true
  enable_global_write_forwarding = true
  enabled_cloudwatch_logs_exports = ["audit", "error", "general", "slowquery"]

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-aurora-secondary"
  })

  depends_on = [aws_rds_cluster_instance.primary]

  lifecycle {
    ignore_changes = [
      engine_version,
      master_username,
      master_password,
      replication_source_identifier,
    ]
  }
}

resource "aws_rds_cluster_instance" "secondary" {
  provider                  = aws.secondary
  count                     = 2
  identifier                = "${var.app_name}-aurora-secondary-${count.index}"
  cluster_identifier        = aws_rds_cluster.secondary.id
  instance_class            = "db.r6g.large"
  engine                    = aws_rds_global_cluster.main.engine
  engine_version            = aws_rds_global_cluster.main.engine_version
  db_subnet_group_name      = aws_db_subnet_group.secondary.name
  publicly_accessible       = false
  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.secondary.arn

  tags = merge(local.common_tags, {
    Name = "${var.app_name}-aurora-secondary-${count.index}"
  })
}

# =============================================================================
# SSM SESSION MANAGER CONFIGURATION
# =============================================================================
resource "aws_ssm_document" "session_manager_prefs" {
  provider        = aws.primary
  name            = "SSM-SessionManagerRunShell"
  document_type   = "Session"
  document_format = "JSON"

  content = jsonencode({
    schemaVersion = "1.0"
    description   = "Session Manager preferences"
    sessionType   = "Standard_Stream"
    inputs = {
      s3BucketName                = ""
      s3KeyPrefix                 = ""
      s3EncryptionEnabled         = true
      cloudWatchLogGroupName      = aws_cloudwatch_log_group.ssm_sessions.name
      cloudWatchEncryptionEnabled = true
      idleSessionTimeout          = "20"
      maxSessionDuration          = "60"
      kmsKeyId                    = aws_kms_key.primary.key_id
      runAsEnabled                = false
      shellProfile = {
        linux   = "exec /bin/bash"
        windows = ""
      }
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "ssm_sessions" {
  provider          = aws.primary
  name              = "/aws/ssm/${var.app_name}/sessions"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.primary.arn

  tags = local.common_tags
}

resource "aws_ssm_document" "session_manager_prefs_secondary" {
  provider        = aws.secondary
  name            = "SSM-SessionManagerRunShell"
  document_type   = "Session"
  document_format = "JSON"

  content = jsonencode({
    schemaVersion = "1.0"
    description   = "Session Manager preferences"
    sessionType   = "Standard_Stream"
    inputs = {
      s3BucketName                = ""
      s3KeyPrefix                 = ""
      s3EncryptionEnabled         = true
      cloudWatchLogGroupName      = aws_cloudwatch_log_group.ssm_sessions_secondary.name
      cloudWatchEncryptionEnabled = true
      idleSessionTimeout          = "20"
      maxSessionDuration          = "60"
      kmsKeyId                    = aws_kms_key.secondary.key_id
      runAsEnabled                = false
      shellProfile = {
        linux   = "exec /bin/bash"
        windows = ""
      }
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "ssm_sessions_secondary" {
  provider          = aws.secondary
  name              = "/aws/ssm/${var.app_name}/sessions"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.secondary.arn

  tags = local.common_tags
}

# =============================================================================
# CLOUDWATCH ALARMS
# =============================================================================
resource "aws_cloudwatch_metric_alarm" "primary_asg_cpu" {
  provider            = aws.primary
  alarm_name          = "${var.app_name}-primary-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "High CPU utilization on primary ASG"

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.primary.name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "secondary_asg_cpu" {
  provider            = aws.secondary
  alarm_name          = "${var.app_name}-secondary-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "High CPU utilization on secondary ASG"

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.secondary.name
  }

  tags = local.common_tags
}

# =============================================================================
# OUTPUTS
# =============================================================================
output "app_url" {
  description = "Application URL with latency-based routing"
  value       = "https://app.${var.domain_name}"
}

output "primary_cloudfront_domain" {
  description = "Primary CloudFront distribution domain"
  value       = aws_cloudfront_distribution.primary.domain_name
}

output "secondary_cloudfront_domain" {
  description = "Secondary CloudFront distribution domain"
  value       = aws_cloudfront_distribution.secondary.domain_name
}

output "primary_alb_dns" {
  description = "Primary ALB DNS name"
  value       = aws_lb.primary.dns_name
}

output "secondary_alb_dns" {
  description = "Secondary ALB DNS name"
  value       = aws_lb.secondary.dns_name
}

output "aurora_primary_endpoint" {
  description = "Aurora primary cluster endpoint"
  value       = aws_rds_cluster.primary.endpoint
}

output "aurora_primary_reader_endpoint" {
  description = "Aurora primary cluster reader endpoint"
  value       = aws_rds_cluster.primary.reader_endpoint
}

output "aurora_secondary_endpoint" {
  description = "Aurora secondary cluster endpoint (write forwarding enabled)"
  value       = aws_rds_cluster.secondary.endpoint
}

output "aurora_secondary_reader_endpoint" {
  description = "Aurora secondary cluster reader endpoint"
  value       = aws_rds_cluster.secondary.reader_endpoint
}

output "global_cluster_identifier" {
  description = "Aurora Global Database identifier"
  value       = aws_rds_global_cluster.main.global_cluster_identifier
}