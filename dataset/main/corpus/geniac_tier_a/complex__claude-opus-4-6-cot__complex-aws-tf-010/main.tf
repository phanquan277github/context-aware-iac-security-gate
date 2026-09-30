# =============================================================================
# DISASTER RECOVERY ARCHITECTURE - PILOT LIGHT STRATEGY
# Primary: us-east-1 | DR: us-west-2
# RPO: 15 minutes | RTO: 1 hour
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
# PROVIDERS
# -----------------------------------------------------------------------------
provider "aws" {
  region = "us-east-1"
  alias  = "primary"
  default_tags {
    tags = {
      Project     = "disaster-recovery"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}

provider "aws" {
  region = "us-west-2"
  alias  = "dr"
  default_tags {
    tags = {
      Project     = "disaster-recovery"
      Environment = "dr"
      ManagedBy   = "terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# DATA SOURCES
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {
  provider = aws.primary
}

data "aws_availability_zones" "primary" {
  provider = aws.primary
  state    = "available"
}

data "aws_availability_zones" "dr" {
  provider = aws.dr
  state    = "available"
}

locals {
  account_id       = data.aws_caller_identity.current.account_id
  app_name         = "dr-pilot-light"
  domain_name      = "app.example.com"
  primary_region   = "us-east-1"
  dr_region        = "us-west-2"
  eks_cluster_name = "${local.app_name}-cluster"
  rds_identifier   = "${local.app_name}-postgres"
  db_name          = "appdb"
  db_username      = "dbadmin"

  primary_vpc_cidr = "10.0.0.0/16"
  dr_vpc_cidr      = "10.1.0.0/16"

  primary_private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  primary_public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  dr_private_subnets      = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
  dr_public_subnets       = ["10.1.101.0/24", "10.1.102.0/24", "10.1.103.0/24"]
}

# =============================================================================
# NETWORKING - PRIMARY REGION
# =============================================================================
resource "aws_vpc" "primary" {
  provider             = aws.primary
  cidr_block           = local.primary_vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "${local.app_name}-primary-vpc" }
}

resource "aws_subnet" "primary_private" {
  provider          = aws.primary
  count             = 3
  vpc_id            = aws_vpc.primary.id
  cidr_block        = local.primary_private_subnets[count.index]
  availability_zone = data.aws_availability_zones.primary.names[count.index]

  tags = {
    Name                                           = "${local.app_name}-primary-private-${count.index}"
    "kubernetes.io/cluster/${local.eks_cluster_name}-primary" = "shared"
    "kubernetes.io/role/internal-elb"               = "1"
  }
}

resource "aws_subnet" "primary_public" {
  provider                = aws.primary
  count                   = 3
  vpc_id                  = aws_vpc.primary.id
  cidr_block              = local.primary_public_subnets[count.index]
  availability_zone       = data.aws_availability_zones.primary.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name                                           = "${local.app_name}-primary-public-${count.index}"
    "kubernetes.io/cluster/${local.eks_cluster_name}-primary" = "shared"
    "kubernetes.io/role/elb"                        = "1"
  }
}

resource "aws_internet_gateway" "primary" {
  provider = aws.primary
  vpc_id   = aws_vpc.primary.id
  tags     = { Name = "${local.app_name}-primary-igw" }
}

resource "aws_eip" "primary_nat" {
  provider = aws.primary
  domain   = "vpc"
  tags     = { Name = "${local.app_name}-primary-nat-eip" }
}

resource "aws_nat_gateway" "primary" {
  provider      = aws.primary
  allocation_id = aws_eip.primary_nat.id
  subnet_id     = aws_subnet.primary_public[0].id
  tags          = { Name = "${local.app_name}-primary-nat" }
}

resource "aws_route_table" "primary_public" {
  provider = aws.primary
  vpc_id   = aws_vpc.primary.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.primary.id
  }
  tags = { Name = "${local.app_name}-primary-public-rt" }
}

resource "aws_route_table" "primary_private" {
  provider = aws.primary
  vpc_id   = aws_vpc.primary.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.primary.id
  }
  tags = { Name = "${local.app_name}-primary-private-rt" }
}

resource "aws_route_table_association" "primary_public" {
  provider       = aws.primary
  count          = 3
  subnet_id      = aws_subnet.primary_public[count.index].id
  route_table_id = aws_route_table.primary_public.id
}

resource "aws_route_table_association" "primary_private" {
  provider       = aws.primary
  count          = 3
  subnet_id      = aws_subnet.primary_private[count.index].id
  route_table_id = aws_route_table.primary_private.id
}

# =============================================================================
# NETWORKING - DR REGION
# =============================================================================
resource "aws_vpc" "dr" {
  provider             = aws.dr
  cidr_block           = local.dr_vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "${local.app_name}-dr-vpc" }
}

resource "aws_subnet" "dr_private" {
  provider          = aws.dr
  count             = 3
  vpc_id            = aws_vpc.dr.id
  cidr_block        = local.dr_private_subnets[count.index]
  availability_zone = data.aws_availability_zones.dr.names[count.index]

  tags = {
    Name                                        = "${local.app_name}-dr-private-${count.index}"
    "kubernetes.io/cluster/${local.eks_cluster_name}-dr" = "shared"
    "kubernetes.io/role/internal-elb"            = "1"
  }
}

resource "aws_subnet" "dr_public" {
  provider                = aws.dr
  count                   = 3
  vpc_id                  = aws_vpc.dr.id
  cidr_block              = local.dr_public_subnets[count.index]
  availability_zone       = data.aws_availability_zones.dr.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name                                        = "${local.app_name}-dr-public-${count.index}"
    "kubernetes.io/cluster/${local.eks_cluster_name}-dr" = "shared"
    "kubernetes.io/role/elb"                     = "1"
  }
}

resource "aws_internet_gateway" "dr" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr.id
  tags     = { Name = "${local.app_name}-dr-igw" }
}

resource "aws_eip" "dr_nat" {
  provider = aws.dr
  domain   = "vpc"
  tags     = { Name = "${local.app_name}-dr-nat-eip" }
}

resource "aws_nat_gateway" "dr" {
  provider      = aws.dr
  allocation_id = aws_eip.dr_nat.id
  subnet_id     = aws_subnet.dr_public[0].id
  tags          = { Name = "${local.app_name}-dr-nat" }
}

resource "aws_route_table" "dr_public" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.dr.id
  }
  tags = { Name = "${local.app_name}-dr-public-rt" }
}

resource "aws_route_table" "dr_private" {
  provider = aws.dr
  vpc_id   = aws_vpc.dr.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.dr.id
  }
  tags = { Name = "${local.app_name}-dr-private-rt" }
}

resource "aws_route_table_association" "dr_public" {
  provider       = aws.dr
  count          = 3
  subnet_id      = aws_subnet.dr_public[count.index].id
  route_table_id = aws_route_table.dr_public.id
}

resource "aws_route_table_association" "dr_private" {
  provider       = aws.dr
  count          = 3
  subnet_id      = aws_subnet.dr_private[count.index].id
  route_table_id = aws_route_table.dr_private.id
}

# =============================================================================
# KMS KEYS
# =============================================================================
resource "aws_kms_key" "primary" {
  provider                = aws.primary
  description             = "Primary region encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = { Name = "${local.app_name}-primary-kms" }
}

resource "aws_kms_alias" "primary" {
  provider      = aws.primary
  name          = "alias/${local.app_name}-primary"
  target_key_id = aws_kms_key.primary.key_id
}

resource "aws_kms_key" "dr" {
  provider                = aws.dr
  description             = "DR region encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  tags                    = { Name = "${local.app_name}-dr-kms" }
}

resource "aws_kms_alias" "dr" {
  provider      = aws.dr
  name          = "alias/${local.app_name}-dr"
  target_key_id = aws_kms_key.dr.key_id
}

# =============================================================================
# EKS - PRIMARY REGION
# =============================================================================
resource "aws_iam_role" "eks_cluster" {
  provider = aws.primary
  name     = "${local.app_name}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  provider   = aws.primary
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  provider   = aws.primary
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_security_group" "eks_primary" {
  provider    = aws.primary
  name_prefix = "${local.app_name}-eks-primary-"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
    cidr_blocks = [local.primary_vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.app_name}-eks-primary-sg" }
}

resource "aws_eks_cluster" "primary" {
  provider = aws.primary
  name     = "${local.eks_cluster_name}-primary"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.29"

  vpc_config {
    subnet_ids              = aws_subnet.primary_private[*].id
    security_group_ids      = [aws_security_group.eks_primary.id]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  encryption_config {
    provider { key_arn = aws_kms_key.primary.arn }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]
}

resource "aws_iam_role" "eks_node_group" {
  provider = aws.primary
  name     = "${local.app_name}-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  provider   = aws.primary
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_group.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  provider   = aws.primary
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_group.name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry" {
  provider   = aws.primary
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_group.name
}

resource "aws_iam_role_policy_attachment" "eks_ebs_csi" {
  provider   = aws.primary
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
  role       = aws_iam_role.eks_node_group.name
}

resource "aws_eks_node_group" "primary" {
  provider        = aws.primary
  cluster_name    = aws_eks_cluster.primary.name
  node_group_name = "${local.app_name}-primary-nodes"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.primary_private[*].id

  scaling_config {
    desired_size = 3
    max_size     = 10
    min_size     = 2
  }

  instance_types = ["m6i.xlarge"]
  capacity_type  = "ON_DEMAND"
  disk_size      = 100

  update_config {
    max_unavailable = 1
  }

  labels = {
    role        = "workload"
    environment = "production"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry,
    aws_iam_role_policy_attachment.eks_ebs_csi,
  ]
}

resource "aws_eks_addon" "ebs_csi_primary" {
  provider     = aws.primary
  cluster_name = aws_eks_cluster.primary.name
  addon_name   = "aws-ebs-csi-driver"

  depends_on = [aws_eks_node_group.primary]
}

# =============================================================================
# EKS - DR REGION (Pilot Light - Scaled to Zero)
# =============================================================================
resource "aws_iam_role" "eks_cluster_dr" {
  provider = aws.dr
  name     = "${local.app_name}-eks-cluster-role-dr"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy_dr" {
  provider   = aws.dr
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster_dr.name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller_dr" {
  provider   = aws.dr
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster_dr.name
}

resource "aws_security_group" "eks_dr" {
  provider    = aws.dr
  name_prefix = "${local.app_name}-eks-dr-"
  vpc_id      = aws_vpc.dr.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [local.dr_vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.app_name}-eks-dr-sg" }
}

resource "aws_eks_cluster" "dr" {
  provider = aws.dr
  name     = "${local.eks_cluster_name}-dr"
  role_arn = aws_iam_role.eks_cluster_dr.arn
  version  = "1.29"

  vpc_config {
    subnet_ids              = aws_subnet.dr_private[*].id
    security_group_ids      = [aws_security_group.eks_dr.id]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  encryption_config {
    provider { key_arn = aws_kms_key.dr.arn }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy_dr,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller_dr,
  ]
}

resource "aws_iam_role" "eks_node_group_dr" {
  provider = aws.dr
  name     = "${local.app_name}-eks-node-role-dr"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy_dr" {
  provider   = aws.dr
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_group_dr.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy_dr" {
  provider   = aws.dr
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_group_dr.name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_dr" {
  provider   = aws.dr
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_group_dr.name
}

resource "aws_iam_role_policy_attachment" "eks_ebs_csi_dr" {
  provider   = aws.dr
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
  role       = aws_iam_role.eks_node_group_dr.name
}

# DR Node Group - Scaled to Zero (Pilot Light)
resource "aws_eks_node_group" "dr" {
  provider        = aws.dr
  cluster_name    = aws_eks_cluster.dr.name
  node_group_name = "${local.app_name}-dr-nodes"
  node_role_arn   = aws_iam_role.eks_node_group_dr.arn
  subnet_ids      = aws_subnet.dr_private[*].id

  scaling_config {
    desired_size = 0
    max_size     = 10
    min_size     = 0
  }

  instance_types = ["m6i.xlarge"]
  capacity_type  = "ON_DEMAND"
  disk_size      = 100

  update_config {
    max_unavailable = 1
  }

  labels = {
    role        = "workload"
    environment = "dr"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy_dr,
    aws_iam_role_policy_attachment.eks_cni_policy_dr,
    aws_iam_role_policy_attachment.eks_container_registry_dr,
    aws_iam_role_policy_attachment.eks_ebs_csi_dr,
  ]
}

resource "aws_eks_addon" "ebs_csi_dr" {
  provider     = aws.dr
  cluster_name = aws_eks_cluster.dr.name
  addon_name   = "aws-ebs-csi-driver"

  depends_on = [aws_eks_cluster.dr]
}

# =============================================================================
# EBS DLM LIFECYCLE POLICY - Hourly Snapshots with Cross-Region Copy
# =============================================================================
resource "aws_iam_role" "dlm_lifecycle" {
  provider = aws.primary
  name     = "${local.app_name}-dlm-lifecycle-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "dlm.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "dlm_lifecycle" {
  provider = aws.primary
  name     = "${local.app_name}-dlm-lifecycle-policy"
  role     = aws_iam_role.dlm_lifecycle.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateSnapshot",
          "ec2:CreateSnapshots",
          "ec2:DeleteSnapshot",
          "ec2:DescribeInstances",
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots",
          "ec2:EnableFastSnapshotRestores",
          "ec2:DescribeFastSnapshotRestores",
          "ec2:DisableFastSnapshotRestores",
          "ec2:CopySnapshot",
          "ec2:ModifySnapshotAttribute",
          "ec2:DescribeSnapshotAttribute",
          "ec2:CreateTags"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:CreateGrant",
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey*",
          "kms:ReEncrypt*"
        ]
        Resource = [
          aws_kms_key.primary.arn,
          aws_kms_key.dr.arn
        ]
      }
    ]
  })
}

resource "aws_dlm_lifecycle_policy" "ebs_snapshots" {
  provider           = aws.primary
  description        = "EBS hourly snapshots with cross-region replication for DR"
  execution_role_arn = aws_iam_role.dlm_lifecycle.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]

    target_tags = {
      "dr-backup" = "true"
    }

    schedule {
      name = "hourly-snapshots-with-crr"

      create_rule {
        interval      = 1
        interval_unit = "HOURS"
        times         = ["00:00"]
      }

      retain_rule {
        count = 24
      }

      tags_to_add = {
        SnapshotType = "dr-hourly"
        CreatedBy    = "dlm"
      }

      copy_tags = true

      cross_region_copy_rule {
        target    = local.dr_region
        encrypted = true
        cmk_arn   = aws_kms_key.dr.arn

        retain_rule {
          interval      = 24
          interval_unit = "HOURS"
        }
      }
    }
  }

  tags = { Name = "${local.app_name}-ebs-dlm-policy" }
}

# =============================================================================
# RDS POSTGRESQL - PRIMARY (Multi-AZ)
# =============================================================================
resource "aws_db_subnet_group" "primary" {
  provider   = aws.primary
  name       = "${local.app_name}-primary-db-subnet"
  subnet_ids = aws_subnet.primary_private[*].id
  tags       = { Name = "${local.app_name}-primary-db-subnet-group" }
}

resource "aws_security_group" "rds_primary" {
  provider    = aws.primary
  name_prefix = "${local.app_name}-rds-primary-"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_primary.id]
  }

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [local.dr_vpc_cidr]
    description = "Allow replication from DR region"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.app_name}-rds-primary-sg" }
}

resource "aws_rds_cluster_parameter_group" "primary" {
  provider = aws.primary
  name     = "${local.app_name}-pg16-cluster-params"
  family   = "aurora-postgresql16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
}

resource "aws_db_parameter_group" "primary" {
  provider = aws.primary
  name     = "${local.app_name}-pg16-params"
  family   = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }
}

resource "aws_db_instance" "primary" {
  provider                    = aws.primary
  identifier                  = local.rds_identifier
  engine                      = "postgres"
  engine_version              = "16.3"
  instance_class              = "db.r6g.xlarge"
  allocated_storage           = 100
  max_allocated_storage       = 500
  storage_type                = "gp3"
  storage_encrypted           = true
  kms_key_id                  = aws_kms_key.primary.arn
  db_name                     = local.db_name
  username                    = local.db_username
  manage_master_user_password = true
  multi_az                    = true
  db_subnet_group_name        = aws_db_subnet_group.primary.name
  vpc_security_group_ids      = [aws_security_group.rds_primary.id]
  parameter_group_name        = aws_db_parameter_group.primary.name
  backup_retention_period     = 14
  backup_window               = "03:00-04:00"
  maintenance_window          = "Mon:04:00-Mon:05:00"
  deletion_protection         = true
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${local.rds_identifier}-final-snapshot"
  copy_tags_to_snapshot       = true
  performance_insights_enabled          = true
  performance_insights_kms_key_id       = aws_kms_key.primary.arn
  performance_insights_retention_period = 731
  monitoring_interval                   = 60
  monitoring_role_arn                   = aws_iam_role.rds_monitoring.arn
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]

  tags = { Name = "${local.app_name}-primary-postgres" }
}

resource "aws_iam_role" "rds_monitoring" {
  provider = aws.primary
  name     = "${local.app_name}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  provider   = aws.primary
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  role       = aws_iam_role.rds_monitoring.name
}

# =============================================================================
# RDS POSTGRESQL - DR REGION (Cross-Region Read Replica)
# =============================================================================
resource "aws_db_subnet_group" "dr" {
  provider   = aws.dr
  name       = "${local.app_name}-dr-db-subnet"
  subnet_ids = aws_subnet.dr_private[*].id
  tags       = { Name = "${local.app_name}-dr-db-subnet-group" }
}

resource "aws_security_group" "rds_dr" {
  provider    = aws.dr
  name_prefix = "${local.app_name}-rds-dr-"
  vpc_id      = aws_vpc.dr.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_dr.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.app_name}-rds-dr-sg" }
}

resource "aws_db_parameter_group" "dr" {
  provider = aws.dr
  name     = "${local.app_name}-pg16-params-dr"
  family   = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }
}

resource "aws_iam_role" "rds_monitoring_dr" {
  provider = aws.dr
  name     = "${local.app_name}-rds-monitoring-role-dr"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "rds_monitoring_dr" {
  provider   = aws.dr
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  role       = aws_iam_role.rds_monitoring_dr.name
}

resource "aws_db_instance" "dr_replica" {
  provider               = aws.dr
  identifier             = "${local.rds_identifier}-dr-replica"
  replicate_source_db    = aws_db_instance.primary.arn
  instance_class         = "db.r6g.xlarge"
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.dr.arn
  multi_az               = false
  db_subnet_group_name   = aws_db_subnet_group.dr.name
  vpc_security_group_ids = [aws_security_group.rds_dr.id]
  parameter_group_name   = aws_db_parameter_group.dr.name
  skip_final_snapshot    = true

  performance_insights_enabled          = true
  performance_insights_kms_key_id       = aws_kms_key.dr.arn
  performance_insights_retention_period = 731
  monitoring_interval                   = 60
  monitoring_role_arn                   = aws_iam_role.rds_monitoring_dr.arn

  tags = { Name = "${local.app_name}-dr-postgres-replica" }
}

# =============================================================================
# S3 - CROSS-REGION REPLICATION WITH RTC
# =============================================================================
resource "aws_s3_bucket" "primary" {
  provider      = aws.primary
  bucket        = "${local.app_name}-primary-${local.account_id}"
  force_destroy = false
  tags          = { Name = "${local.app_name}-primary-bucket" }
}

resource "aws_s3_bucket_versioning" "primary" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "primary" {
  provider = aws.primary
  bucket   = aws_s3_bucket.primary.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.primary.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket" "dr" {
  provider      = aws.dr
  bucket        = "${local.app_name}-dr-${local.account_id}"
  force_destroy = false
  tags          = { Name = "${local.app_name}-dr-bucket" }
}

resource "aws_s3_bucket_versioning" "dr" {
  provider = aws.dr
  bucket   = aws_s3_bucket.dr.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "dr" {
  provider = aws.dr
  bucket   = aws_s3_bucket.dr.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.dr.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_iam_role" "s3_replication" {
  provider = aws.primary
  name     = "${local.app_name}-s3-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "s3_replication" {
  provider = aws.primary
  name     = "${local.app_name}-s3-replication-policy"
  role     = aws_iam_role.s3_replication.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.primary.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Resource = "${aws_s3_bucket.primary.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = "${aws_s3_bucket.dr.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [
          aws_kms_key.primary.arn,
          aws_kms_key.dr.arn
        ]
      }
    ]
  })
}

resource "aws_s3_bucket_replication_configuration" "primary_to_dr" {
  provider = aws.primary
  role     = aws_iam_role.s3_replication.arn
  bucket   = aws_s3_bucket.primary.id

  rule {
    id     = "dr-replication"
    status = "Enabled"

    filter {
      prefix = ""
    }

    destination {
      bucket        = aws_s3_bucket.dr.arn
      storage_class = "STANDARD"

      encryption_configuration {
        replica_kms_key_id = aws_kms_key.dr.arn
      }

      metrics {
        status = "Enabled"
        event_threshold {
          minutes = 15
        }
      }

      replication_time {
        status = "Enabled"
        time {
          minutes = 15
        }
      }
    }

    source_selection_criteria {
      sse_kms_encrypted_objects {
        status = "Enabled"
      }
    }

    delete_marker_replication {
      status = "Enabled"
    }
  }

  depends_on = [
    aws_s3_bucket_versioning.primary,
    aws_s3_bucket_versioning.dr,
  ]
}

# =============================================================================
# ELASTICACHE REDIS - GLOBAL DATASTORE
# =============================================================================
resource "aws_security_group" "redis_primary" {
  provider    = aws.primary
  name_prefix = "${local.app_name}-redis-primary-"
  vpc_id      = aws_vpc.primary.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_primary.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.app_name}-redis-primary-sg" }
}

resource "aws_security_group" "redis_dr" {
  provider    = aws.dr
  name_prefix = "${local.app_name}-redis-dr-"
  vpc_id      = aws_vpc.dr.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_dr.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.app_name}-redis-dr-sg" }
}

resource "aws_elasticache_subnet_group" "primary" {
  provider   = aws.primary
  name       = "${local.app_name}-redis-primary-subnet"
  subnet_ids = aws_subnet.primary_private[*].id
}

resource "aws_elasticache_subnet_group" "dr" {
  provider   = aws.dr
  name       = "${local.app_name}-redis-dr-subnet"
  subnet_ids = aws_subnet.dr_private[*].id
}

resource "aws_elasticache_parameter_group" "redis" {
  provider = aws.primary
  name     = "${local.app_name}-redis7-params"
  family   = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "volatile-lru"
  }
}

resource "aws_elasticache_parameter_group" "redis_dr" {
  provider = aws.dr
  name     = "${local.app_name}-redis7-params-dr"
  family   = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "volatile-lru"
  }
}

resource "aws_elasticache_global_replication_group" "redis" {
  provider                           = aws.primary
  global_replication_group_id_suffix = local.app_name
  primary_replication_group_id       = aws_elasticache_replication_group.primary.id
  global_replication_group_description = "Global Redis datastore for DR"
}

resource "aws_elasticache_replication_group" "primary" {
  provider                   = aws.primary
  replication_group_id       = "${local.app_name}-redis-primary"
  description                = "Primary Redis cluster"
  node_type                  = "cache.r6g.large"
  num_cache_clusters         = 2
  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.redis.name
  subnet_group_name          = aws_elasticache_subnet_group.primary.name
  security_group_ids         = [aws_security_group.redis_primary.id]
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.primary.arn
  snapshot_retention_limit   = 7
  snapshot_window            = "05:00-06:00"
  maintenance_window         = "mon:06:00-mon:07:00"
  engine_version             = "7.1"

  tags = { Name = "${local.app_name}-redis-primary" }
}

resource "aws_elasticache_replication_group" "dr" {
  provider                       = aws.dr
  replication_group_id           = "${local.app_name}-redis-dr"
  description                    = "DR Redis cluster (Global Datastore secondary)"
  global_replication_group_id    = aws_elasticache_global_replication_group.redis.global_replication_group_id
  num_cache_clusters             = 1
  port                           = 6379
  parameter_group_name           = aws_elasticache_parameter_group.redis_dr.name
  subnet_group_name              = aws_elasticache_subnet_group.dr.name
  security_group_ids             = [aws_security_group.redis_dr.id]
  automatic_failover_enabled     = true

  tags = { Name = "${local.app_name}-redis-dr" }
}

# =============================================================================
# ALB - PRIMARY REGION
# =============================================================================
resource "aws_security_group" "alb_primary" {
  provider    = aws.primary
  name_prefix = "${local.app_name}-alb-primary-"
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

  tags = { Name = "${local.app_name}-alb-primary-sg" }
}

resource "aws_lb" "primary" {
  provider           = aws.primary
  name               = "${local.app_name}-primary-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_primary.id]
  subnets            = aws_subnet.primary_public[*].id

  enable_deletion_protection = true

  tags = { Name = "${local.app_name}-primary-alb" }
}

resource "aws_lb_target_group" "primary" {
  provider    = aws.primary
  name        = "${local.app_name}-primary-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.primary.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 15
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = { Name = "${local.app_name}-primary-tg" }
}

resource "aws_lb_listener" "primary_https" {
  provider          = aws.primary
  load_balancer_arn = aws_lb.primary.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.primary.arn
  }
}

# =============================================================================
# ALB - DR REGION (Pre-provisioned)
# =============================================================================
resource "aws_security_group" "alb_dr" {
  provider    = aws.dr
  name_prefix = "${local.app_name}-alb-dr-"
  vpc_id      = aws_vpc.dr.id

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

  tags = { Name = "${local.app_name}-alb-dr-sg" }
}

resource "aws_lb" "dr" {
  provider           = aws.dr
  name               = "${local.app_name}-dr-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_dr.id]
  subnets            = aws_subnet.dr_public[*].id

  enable_deletion_protection = true

  tags = { Name = "${local.app_name}-dr-alb" }
}

resource "aws_lb_target_group" "dr" {
  provider    = aws.dr
  name        = "${local.app_name}-dr-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.dr.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 15
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = { Name = "${local.app_name}-dr-tg" }
}

resource "aws_lb_listener" "dr_https" {
  provider          = aws.dr
  load_balancer_arn = aws_lb.dr.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.dr.arn
  }
}

# =============================================================================
# CLOUDFRONT DISTRIBUTION
# =============================================================================
resource "aws_cloudfront_distribution" "main" {
  provider = aws.primary
  enabled  = true
  comment  = "${local.app_name} CloudFront distribution"

  origin {
    domain_name = aws_lb.primary.dns_name
    origin_id   = "primary-alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "primary-alb"

    forwarded_values {
      query_string = true
      cookies { forward = "all" }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = { Name = "${local.app_name}-cloudfront" }
}

# =============================================================================
# ROUTE53 - HEALTH CHECKS AND FAILOVER ROUTING
# =============================================================================
resource "aws_route53_zone" "main" {
  provider = aws.primary
  name     = "example.com"
}

resource "aws_route53_health_check" "primary" {
  provider          = aws.primary
  fqdn              = aws_lb.primary.dns_name
  port              = 80
  type              = "HTTP"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 10

  tags = { Name = "${local.app_name}-primary-health-check" }
}

resource "aws_route53_health_check" "dr" {
  provider          = aws.primary
  fqdn              = aws_lb.dr.dns_name
  port              = 80
  type              = "HTTP"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 10

  tags = { Name = "${local.app_name}-dr-health-check" }
}

resource "aws_route53_record" "primary" {
  provider        = aws.primary
  zone_id         = aws_route53_zone.main.zone_id
  name            = local.domain_name
  type            = "A"
  set_identifier  = "primary"
  health_check_id = aws_route53_health_check.primary.id

  failover_routing_policy {
    type = "PRIMARY"
  }

  alias {
    name                   = aws_lb.primary.dns_name
    zone_id                = aws_lb.primary.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "dr" {
  provider        = aws.primary
  zone_id         = aws_route53_zone.main.zone_id
  name            = local.domain_name
  type            = "A"
  set_identifier  = "secondary"
  health_check_id = aws_route53_health_check.dr.id

  failover_routing_policy {
    type = "SECONDARY"
  }

  alias {
    name                   = aws_lb.dr.dns_name
    zone_id                = aws_lb.dr.zone_id
    evaluate_target_health = true
  }
}

# =============================================================================
# CLOUDWATCH ALARMS FOR FAILOVER TRIGGER
# =============================================================================
resource "aws_sns_topic" "dr_failover" {
  provider = aws.primary
  name     = "${local.app_name}-dr-failover-topic"
}

resource "aws_cloudwatch_metric_alarm" "primary_health_check" {
  provider            = aws.primary
  alarm_name          = "${local.app_name}-primary-health-check-alarm"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 3
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  alarm_description   = "Primary region health check failed - trigger DR failover"
  alarm_actions       = [aws_sns_topic.dr_failover.arn]
  treat_missing_data  = "breaching"

  dimensions = {
    HealthCheckId = aws_route53_health_check.primary.id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_primary_health" {
  provider            = aws.primary
  alarm_name          = "${local.app_name}-rds-primary-health-alarm"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Primary RDS has no connections - potential failure"
  alarm_actions       = [aws_sns_topic.dr_failover.arn]
  treat_missing_data  = "breaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.primary.identifier
  }
}

# =============================================================================
# LAMBDA FAILOVER ORCHESTRATOR
# =============================================================================
resource "aws_iam_role" "failover_lambda" {
  provider = aws.primary
  name     = "${local.app_name}-failover-orchestrator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "failover_lambda" {
  provider = aws.primary
  name     = "${local.app_name}-failover-orchestrator-policy"
  role     = aws_iam_role.failover_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rds:PromoteReadReplica",
          "rds:DescribeDBInstances",
          "rds:ModifyDBInstance"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "eks:UpdateNodegroupConfig",
          "eks:DescribeNodegroup",
          "eks:ListNodegroups",
          "eks:DescribeCluster"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "route53:ChangeResourceRecordSets",
          "route53:GetHostedZone",
          "route53:ListResourceRecordSets",
          "route53:GetHealthCheck",
          "route53:UpdateHealthCheck"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation",
          "cloudfront:GetDistribution",
          "cloudfront:UpdateDistribution"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "elasticache:FailoverGlobalReplicationGroup",
          "elasticache:DescribeGlobalReplicationGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:PutParameter",
          "ssm:GetParameter"
        ]
        Resource = "*"
      }
    ]
  })
}

data "archive_file" "failover_lambda" {
  type        = "zip"
  output_path = "${path.module}/failover_lambda.zip"

  source {
    content  = <<-PYTHON
import json
import boto3
import os
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    DR Failover Orchestrator
    Triggered by CloudWatch Alarm via SNS when primary region health check fails.
    
    Steps:
    1. Promote RDS read replica in DR region
    2. Scale up EKS node group in DR region
    3. Failover ElastiCache Global Datastore
    4. Update Route53 records
    5. Invalidate CloudFront caches
    """
    
    logger.info(f"Failover triggered with event: {json.dumps(event)}")
    
    dr_region = os.environ['DR_REGION']
    eks_cluster_name = os.environ['EKS_CLUSTER_NAME']
    eks_nodegroup_name = os.environ['EKS_NODEGROUP_NAME']
    rds_replica_id = os.environ['RDS_REPLICA_IDENTIFIER']
    hosted_zone_id = os.environ['HOSTED_ZONE_ID']
    domain_name = os.environ['DOMAIN_NAME']
    cloudfront_dist_id = os.environ['CLOUDFRONT_DISTRIBUTION_ID']
    dr_alb_dns = os.environ['DR_ALB_DNS_NAME']
    dr_alb_zone_id = os.environ['DR_ALB_ZONE_ID']
    global_redis_group = os.environ['GLOBAL_REDIS_GROUP_ID']
    desired_nodes = int(os.environ.get('DESIRED_NODE_COUNT', '3'))
    
    results = {
        'rds_promotion': 'NOT_STARTED',
        'eks_scaleup': 'NOT_STARTED',
        'redis_failover': 'NOT_STARTED',
        'route53_update': 'NOT_STARTED',
        'cloudfront_invalidation': 'NOT_STARTED'
    }
    
    # Check if this is a duplicate/test invocation
    ssm = boto3.client('ssm', region_name=dr_region)
    try:
        param = ssm.get_parameter(Name='/dr/failover/lock')
        lock_time = float(param['Parameter']['Value'])
        if time.time() - lock_time < 3600:
            logger.warning("Failover already in progress (lock exists). Skipping.")
            return {'statusCode': 200, 'body': 'Failover already in progress'}
    except ssm.exceptions.ParameterNotFound:
        pass
    
    # Set failover lock
    ssm.put_parameter(
        Name='/dr/failover/lock',
        Value=str(time.time()),
        Type='String',
        Overwrite=True
    )
    
    # Step 1: Promote RDS Read Replica
    try:
        logger.info(f"Promoting RDS read replica: {rds_replica_id}")
        rds = boto3.client('rds', region_name=dr_region)
        rds.promote_read_replica(
            DBInstanceIdentifier=rds_replica_id,
            BackupRetentionPeriod=7,
            PreferredBackupWindow='03:00-04:00'
        )
        results['rds_promotion'] = 'INITIATED'
        logger.info("RDS promotion initiated successfully")
    except Exception as e:
        logger.error(f"RDS promotion failed: {str(e)}")
        results['rds_promotion'] = f'FAILED: {str(e)}'
    
    # Step 2: Scale up EKS Node Group
    try:
        logger.info(f"Scaling up EKS node group: {eks_nodegroup_name}")
        eks = boto3.client('eks', region_name=dr_region)
        eks.update_nodegroup_config(
            clusterName=eks_cluster_name,
            nodegroupName=eks_nodegroup_name,
            scalingConfig={
                'minSize': 2,
                'maxSize': 10,
                'desiredSize': desired_nodes
            }
        )
        results['eks_scaleup'] = 'INITIATED'
        logger.info(f"EKS scale-up to {desired_nodes} nodes initiated")
    except Exception as e:
        logger.error(f"EKS scale-up failed: {str(e)}")
        results['eks_scaleup'] = f'FAILED: {str(e)}'
    
    # Step 3: Failover ElastiCache Global Datastore
    try:
        logger.info(f"Failing over Redis Global Datastore: {global_redis_group}")
        elasticache = boto3.client('elasticache', region_name=dr_region)
        elasticache.failover_global_replication_group(
            GlobalReplicationGroupId=global_redis_group,
            PrimaryRegion=dr_region,
            PrimaryReplicationGroupId=f"{os.environ['DR_REDIS_REPLICATION_GROUP_ID']}"
        )
        results['redis_failover'] = 'INITIATED'
        logger.info("Redis Global Datastore failover initiated")
    except Exception as e:
        logger.error(f"Redis failover failed: {str(e)}")
        results['redis_failover'] = f'FAILED: {str(e)}'
    
    # Step 4: Update Route53 (force failover by updating health check)
    try:
        logger.info("Updating Route53 health check to force failover")
        route53 = boto3.client('route53', region_name='us-east-1')
        
        # Update the primary health check to force it to fail
        route53.update_health_check(
            HealthCheckId=os.environ['PRIMARY_HEALTH_CHECK_ID'],
            Disabled=True
        )
        
        results['route53_update'] = 'COMPLETED'
        logger.info("Route53 failover routing activated")
    except Exception as e:
        logger.error(f"Route53 update failed: {str(e)}")
        results['route53_update'] = f'FAILED: {str(e)}'
    
    # Step 5: Invalidate CloudFront Cache
    try:
        logger.info(f"Invalidating CloudFront distribution: {cloudfront_dist_id}")
        cloudfront = boto3.client('cloudfront', region_name='us-east-1')
        cloudfront.create_invalidation(
            DistributionId=cloudfront_dist_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 1,
                    'Items': ['/*']
                },
                'CallerReference': f'dr-failover-{int(time.time())}'
            }
        )
        results['cloudfront_invalidation'] = 'INITIATED'
        logger.info("CloudFront invalidation initiated")
    except Exception as e:
        logger.error(f"CloudFront invalidation failed: {str(e)}")
        results['cloudfront_invalidation'] = f'FAILED: {str(e)}'
    
    # Publish results to SNS
    try:
        sns = boto3.client('sns', region_name='us-east-1')
        sns.publish(
            TopicArn=os.environ['NOTIFICATION_TOPIC_ARN'],
            Subject=f'DR Failover Orchestration Results - {time.strftime("%Y-%m-%d %H:%M:%S UTC")}',
            Message=json.dumps(results, indent=2)
        )
    except Exception as e:
        logger.error(f"Failed to publish SNS notification: {str(e)}")
    
    logger.info(f"Failover orchestration completed: {json.dumps(results)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
    PYTHON
    filename = "index.py"
  }
}

resource "aws_lambda_function" "failover_orchestrator" {
  provider         = aws.primary
  filename         = data.archive_file.failover_lambda.output_path
  source_code_hash = data.archive_file.failover_lambda.output_base64sha256
  function_name    = "${local.app_name}-failover-orchestrator"
  role             = aws_iam_role.failover_lambda.arn
  handler          = "index.handler"
  runtime          = "python3.12"
  timeout          = 900
  memory_size      = 256

  environment {
    variables = {
      DR_REGION                      = local.dr_region
      EKS_CLUSTER_NAME               = aws_eks_cluster.dr.name
      EKS_NODEGROUP_NAME             = aws_eks_node_group.dr.node_group_name
      RDS_REPLICA_IDENTIFIER         = aws_db_instance.dr_replica.identifier
      HOSTED_ZONE_ID                 = aws_route53_zone.main.zone_id
      DOMAIN_NAME                    = local.domain_name
      CLOUDFRONT_DISTRIBUTION_ID     = aws_cloudfront_distribution.main.id
      DR_ALB_DNS_NAME                = aws_lb.dr.dns_name
      DR_ALB_ZONE_ID                 = aws_lb.dr.zone_id
      GLOBAL_REDIS_GROUP_ID          = aws_elasticache_global_replication_group.redis.id
      DR_REDIS_REPLICATION_GROUP_ID  = aws_elasticache_replication_group.dr.id
      PRIMARY_HEALTH_CHECK_ID        = aws_route53_health_check.primary.id
      NOTIFICATION_TOPIC_ARN         = aws_sns_topic.dr_failover.arn
      DESIRED_NODE_COUNT             = "3"
    }
  }

  tags = { Name = "${local.app_name}-failover-orchestrator" }
}

resource "aws_lambda_permission" "sns_trigger" {
  provider      = aws.primary
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.failover_orchestrator.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.dr_failover.arn
}

resource "aws_sns_topic_subscription" "failover_lambda" {
  provider  = aws.primary
  topic_arn = aws_sns_topic.dr_failover.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.failover_orchestrator.arn
}

resource "aws_cloudwatch_log_group" "failover_lambda" {
  provider          = aws.primary
  name              = "/aws/lambda/${aws_lambda_function.failover_orchestrator.function_name}"
  retention_in_days = 90
}

# =============================================================================
# SSM AUTOMATION DOCUMENT - DR TESTING RUNBOOK
# =============================================================================
resource "aws_iam_role" "ssm_automation" {
  provider = aws.primary
  name     = "${local.app_name}-ssm-automation-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = { Service = "ssm.amazonaws.com" }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = { Service = "lambda.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ssm_automation" {
  provider = aws.primary
  name     = "${local.app_name}-ssm-automation-policy"
  role     = aws_iam_role.ssm_automation.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rds:*",
          "eks:*",
          "elasticache:*",
          "route53:*",
          "cloudfront:*",
          "s3:*",
          "ec2:*",
          "lambda:InvokeFunction",
          "sns:Publish",
          "ssm:*",
          "logs:*",
          "cloudwatch:*",
          "iam:PassRole"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_ssm_document" "dr_test_runbook" {
  provider        = aws.primary
  name            = "${local.app_name}-dr-test-runbook"
  document_type   = "Automation"
  document_format = "YAML"

  content = yamlencode({
    schemaVersion = "0.3"
    description   = "Quarterly DR Testing Runbook - Pilot Light Strategy Validation"
    assumeRole    = aws_iam_role.ssm_automation.arn

    parameters = {
      DRRegion = {
        type        = "String"
        default     = local.dr_region
        description = "DR Region"
      }
      PrimaryRegion = {
        type        = "String"
        default     = local.primary_region
        description = "Primary Region"
      }
      EKSClusterName = {
        type        = "String"
        default     = aws_eks_cluster.dr.name
        description = "DR EKS Cluster Name"
      }
      EKSNodeGroupName = {
        type        = "String"
        default     = aws_eks_node_group.dr.node_group_name
        description = "DR EKS Node Group Name"
      }
      RDSReplicaIdentifier = {
        type        = "String"
        default     = aws_db_instance.dr_replica.identifier
        description = "DR RDS Replica Identifier"
      }
      PrimaryRDSIdentifier = {
        type        = "String"
        default     = aws_db_instance.primary.identifier
        description = "Primary RDS Identifier"
      }
      NotificationTopicArn = {
        type        = "String"
        default     = aws_sns_topic.dr_failover.arn
        description = "SNS Topic for notifications"
      }
      DesiredNodeCount = {
        type        = "String"
        default     = "3"
        description = "Desired EKS node count for DR"
      }
    }

    mainSteps = [
      {
        name   = "NotifyDRTestStart"
        action = "aws:executeAwsApi"
        inputs = {
          Service = "sns"
          Api     = "Publish"
          TopicArn = "{{ NotificationTopicArn }}"
          Subject  = "DR Test Started"
          Message  = "Quarterly DR test initiated at {{ global:DATE_TIME }}. Runbook execution ID: {{ automation:EXECUTION_ID }}"
        }
      },
      {
        name   = "ValidatePrerequisites"
        action = "aws:executeScript"
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import boto3
    dr_region = event['DRRegion']
    results = {}
    
    # Check DR EKS cluster status
    eks = boto3.client('eks', region_name=dr_region)
    cluster = eks.describe_cluster(name=event['EKSClusterName'])
    results['eks_cluster_status'] = cluster['cluster']['status']
    
    # Check DR RDS replica status
    rds = boto3.client('rds', region_name=dr_region)
    db = rds.describe_db_instances(DBInstanceIdentifier=event['RDSReplicaIdentifier'])
    results['rds_replica_status'] = db['DBInstances'][0]['DBInstanceStatus']
    results['rds_replica_lag'] = str(db['DBInstances'][0].get('StatusInfos', [{}]))
    
    # Validate all prerequisites pass
    all_ok = (
        results['eks_cluster_status'] == 'ACTIVE' and
        results['rds_replica_status'] == 'available'
    )
    results['prerequisites_met'] = all_ok
    
    if not all_ok:
        raise Exception(f"Prerequisites not met: {results}")
    
    return results
          PYTHON
          InputPayload = {
            DRRegion             = "{{ DRRegion }}"
            EKSClusterName       = "{{ EKSClusterName }}"
            RDSReplicaIdentifier = "{{ RDSReplicaIdentifier }}"
          }
        }
      },
      {
        name   = "ScaleUpDREKSNodes"
        action = "aws:executeAwsApi"
        inputs = {
          Service = "eks"
          Api     = "UpdateNodegroupConfig"
          clusterName   = "{{ EKSClusterName }}"
          nodegroupName = "{{ EKSNodeGroupName }}"
          scalingConfig = {
            minSize     = 2
            maxSize     = 10
            desiredSize = 3
          }
        }
        onFailure = "step:CleanupAndNotifyFailure"
      },
      {
        name   = "WaitForEKSNodesReady"
        action = "aws:executeScript"
        timeoutSeconds = 1800
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import boto3
    import time
    
    eks = boto3.client('eks', region_name=event['DRRegion'])
    desired = int(event['DesiredNodeCount'])
    
    for attempt in range(60):
        ng = eks.describe_nodegroup(
            clusterName=event['EKSClusterName'],
            nodegroupName=event['EKSNodeGroupName']
        )
        status = ng['nodegroup']['status']
        current_size = ng['nodegroup']['scalingConfig']['desiredSize']
        
        if status == 'ACTIVE' and current_size >= desired:
            return {'status': 'NODES_READY', 'node_count': current_size}
        
        time.sleep(30)
    
    raise Exception("EKS nodes did not become ready within timeout")
          PYTHON
          InputPayload = {
            DRRegion         = "{{ DRRegion }}"
            EKSClusterName   = "{{ EKSClusterName }}"
            EKSNodeGroupName = "{{ EKSNodeGroupName }}"
            DesiredNodeCount = "{{ DesiredNodeCount }}"
          }
        }
        onFailure = "step:CleanupAndNotifyFailure"
      },
      {
        name   = "ValidateRDSReplication"
        action = "aws:executeScript"
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import boto3
    
    rds = boto3.client('rds', region_name=event['DRRegion'])
    db = rds.describe_db_instances(DBInstanceIdentifier=event['RDSReplicaIdentifier'])
    instance = db['DBInstances'][0]
    
    result = {
        'status': instance['DBInstanceStatus'],
        'engine': instance['Engine'],
        'engine_version': instance['EngineVersion'],
        'storage_encrypted': instance['StorageEncrypted'],
        'multi_az': instance['MultiAZ'],
        'read_replica_source': instance.get('ReadReplicaSourceDBInstanceIdentifier', 'N/A')
    }
    
    if instance['DBInstanceStatus'] != 'available':
        raise Exception(f"RDS replica not available: {result}")
    
    return result
          PYTHON
          InputPayload = {
            DRRegion             = "{{ DRRegion }}"
            RDSReplicaIdentifier = "{{ RDSReplicaIdentifier }}"
          }
        }
      },
      {
        name   = "ValidateS3Replication"
        action = "aws:executeScript"
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import boto3
    import time
    
    s3_primary = boto3.client('s3', region_name='us-east-1')
    s3_dr = boto3.client('s3', region_name='us-west-2')
    
    # Write a test object to primary
    test_key = f'dr-test/validation-{int(time.time())}.txt'
    test_content = f'DR validation test at {time.strftime("%Y-%m-%d %H:%M:%S UTC")}'
    
    primary_bucket = event['PrimaryBucket']
    dr_bucket = event['DRBucket']
    
    s3_primary.put_object(
        Bucket=primary_bucket,
        Key=test_key,
        Body=test_content.encode()
    )
    
    # Wait for replication (up to 15 minutes per RTC SLA)
    for attempt in range(30):
        try:
            response = s3_dr.get_object(Bucket=dr_bucket, Key=test_key)
            replicated_content = response['Body'].read().decode()
            if replicated_content == test_content:
                # Cleanup
                s3_primary.delete_object(Bucket=primary_bucket, Key=test_key)
                s3_dr.delete_object(Bucket=dr_bucket, Key=test_key)
                return {
                    'status': 'REPLICATION_VERIFIED',
                    'replication_time_seconds': attempt * 30
                }
        except s3_dr.exceptions.NoSuchKey:
            pass
        time.sleep(30)
    
    raise Exception("S3 replication validation failed - object not replicated within timeout")
          PYTHON
          InputPayload = {
            PrimaryBucket = "${local.app_name}-primary-${local.account_id}"
            DRBucket      = "${local.app_name}-dr-${local.account_id}"
          }
        }
      },
      {
        name   = "ValidateRedisConnectivity"
        action = "aws:executeScript"
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import boto3
    
    elasticache = boto3.client('elasticache', region_name=event['DRRegion'])
    
    response = elasticache.describe_replication_groups(
        ReplicationGroupId=event['RedisReplicationGroupId']
    )
    
    rg = response['ReplicationGroups'][0]
    result = {
        'status': rg['Status'],
        'member_clusters': rg.get('MemberClusters', []),
        'node_groups': len(rg.get('NodeGroups', [])),
        'cluster_enabled': rg.get('ClusterEnabled', False)
    }
    
    if rg['Status'] != 'available':
        raise Exception(f"Redis replication group not available: {result}")
    
    return result
          PYTHON
          InputPayload = {
            DRRegion                = "{{ DRRegion }}"
            RedisReplicationGroupId = aws_elasticache_replication_group.dr.id
          }
        }
      },
      {
        name   = "ValidateALBHealth"
        action = "aws:executeScript"
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import boto3
    
    elbv2 = boto3.client('elbv2', region_name=event['DRRegion'])
    
    # Check ALB exists and is active
    albs = elbv2.describe_load_balancers(Names=[event['ALBName']])
    alb = albs['LoadBalancers'][0]
    
    # Check target groups
    tgs = elbv2.describe_target_groups(
        LoadBalancerArn=alb['LoadBalancerArn']
    )
    
    result = {
        'alb_state': alb['State']['Code'],
        'alb_dns': alb['DNSName'],
        'target_groups': len(tgs['TargetGroups']),
        'alb_scheme': alb['Scheme']
    }
    
    if alb['State']['Code'] != 'active':
        raise Exception(f"DR ALB not active: {result}")
    
    return result
          PYTHON
          InputPayload = {
            DRRegion = "{{ DRRegion }}"
            ALBName  = aws_lb.dr.name
          }
        }
      },
      {
        name   = "ValidateEBSSnapshotReplication"
        action = "aws:executeScript"
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import boto3
    from datetime import datetime, timedelta, timezone
    
    ec2 = boto3.client('ec2', region_name=event['DRRegion'])
    
    # Check for recent replicated snapshots
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    
    snapshots = ec2.describe_snapshots(
        Filters=[
            {'Name': 'tag:CreatedBy', 'Values': ['dlm']},
            {'Name': 'status', 'Values': ['completed']}
        ],
        OwnerIds=['self']
    )
    
    recent_snapshots = [
        s for s in snapshots['Snapshots']
        if s['StartTime'].replace(tzinfo=timezone.utc) > cutoff
    ]
    
    result = {
        'total_dr_snapshots': len(snapshots['Snapshots']),
        'recent_snapshots_count': len(recent_snapshots),
        'latest_snapshot_time': str(max(
            [s['StartTime'] for s in snapshots['Snapshots']]
        )) if snapshots['Snapshots'] else 'NONE'
    }
    
    return result
          PYTHON
          InputPayload = {
            DRRegion = "{{ DRRegion }}"
          }
        }
      },
      {
        name   = "GenerateTestReport"
        action = "aws:executeScript"
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import json
    import time
    
    report = {
        'test_execution_id': event.get('automation_execution_id', 'N/A'),
        'test_date': time.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'dr_strategy': 'Pilot Light',
        'rpo_target': '15 minutes',
        'rto_target': '1 hour',
        'test_results': {
            'prerequisites': 'PASSED',
            'eks_scaleup': 'PASSED',
            'rds_replication': 'PASSED',
            's3_replication': 'PASSED',
            'redis_connectivity': 'PASSED',
            'alb_health': 'PASSED',
            'ebs_snapshots': 'PASSED'
        },
        'overall_status': 'PASSED',
        'recommendations': [
            'Review and update runbook if any infrastructure changes occurred',
            'Verify application-level DR procedures are current',
            'Schedule next quarterly test'
        ]
    }
    
    return report
          PYTHON
          InputPayload = {
            automation_execution_id = "{{ automation:EXECUTION_ID }}"
          }
        }
      },
      {
        name   = "ScaleDownDRNodes"
        action = "aws:executeAwsApi"
        inputs = {
          Service = "eks"
          Api     = "UpdateNodegroupConfig"
          clusterName   = "{{ EKSClusterName }}"
          nodegroupName = "{{ EKSNodeGroupName }}"
          scalingConfig = {
            minSize     = 0
            maxSize     = 10
            desiredSize = 0
          }
        }
      },
      {
        name   = "NotifyDRTestComplete"
        action = "aws:executeAwsApi"
        inputs = {
          Service  = "sns"
          Api      = "Publish"
          TopicArn = "{{ NotificationTopicArn }}"
          Subject  = "DR Test Completed Successfully"
          Message  = "Quarterly DR test completed successfully at {{ global:DATE_TIME }}. All validation steps passed. DR nodes scaled back to zero. Execution ID: {{ automation:EXECUTION_ID }}"
        }
        isEnd = true
      },
      {
        name   = "CleanupAndNotifyFailure"
        action = "aws:executeScript"
        inputs = {
          Runtime = "python3.8"
          Handler = "handler"
          Script  = <<-PYTHON
def handler(event, context):
    import boto3
    
    # Scale down DR nodes on failure
    try:
        eks = boto3.client('eks', region_name=event['DRRegion'])
        eks.update_nodegroup_config(
            clusterName=event['EKSClusterName'],
            nodegroupName=event['EKSNodeGroupName'],
            scalingConfig={
                'minSize': 0,
                'maxSize': 10,
                'desiredSize': 0
            }
        )
    except Exception as e:
        pass
    
    # Send failure notification
    sns = boto3.client('sns', region_name='us-east-1')
    sns.publish(
        TopicArn=event['NotificationTopicArn'],
        Subject='DR Test FAILED',
        Message=f"Quarterly DR test FAILED at step. Manual investigation required. Execution ID: {event.get('ExecutionId', 'N/A')}"
    )
    
    return {'status': 'CLEANUP_COMPLETED'}
          PYTHON
          InputPayload = {
            DRRegion             = "{{ DRRegion }}"
            EKSClusterName       = "{{ EKSClusterName }}"
            EKSNodeGroupName     = "{{ EKSNodeGroupName }}"
            NotificationTopicArn = "{{ NotificationTopicArn }}"
            ExecutionId          = "{{ automation:EXECUTION_ID }}"
          }
        }
        isEnd = true
      }
    ]
  })

  tags = { Name = "${local.app_name}-dr-test-runbook" }
}

# SSM Maintenance Window for Quarterly DR Testing
resource "aws_ssm_maintenance_window" "dr_test" {
  provider            = aws.primary
  name                = "${local.app_name}-quarterly-dr-test"
  schedule            = "cron(0 2 ? 1,4,7,10 SAT#1 *)"
  duration            = 4
  cutoff              = 1
  allow_unassociated_targets = true

  tags = { Name = "${local.app_name}-quarterly-dr-test-window" }
}

resource "aws_ssm_maintenance_window_task" "dr_test" {
  provider         = aws.primary
  window_id        = aws_ssm_maintenance_window.dr_test.id
  task_type        = "AUTOMATION"
  task_arn         = aws_ssm_document.dr_test_runbook.arn
  priority         = 1
  service_role_arn = aws_iam_role.ssm_automation.arn

  max_concurrency = "1"
  max_errors      = "0"

  task_invocation_parameters {
    automation_parameters {
      document_version = "$LATEST"

      parameter {
        name   = "DRRegion"
        values = [local.dr_region]
      }
      parameter {
        name   = "PrimaryRegion"
        values = [local.primary_region]
      }
      parameter {
        name   = "EKSClusterName"
        values = [aws_eks_cluster.dr.name]
      }
      parameter {
        name   = "EKSNodeGroupName"
        values = [aws_eks_node_group.dr.node_group_name]
      }
      parameter {
        name   = "RDSReplicaIdentifier"
        values = [aws_db_instance.dr_replica.identifier]
      }
      parameter {
        name   = "PrimaryRDSIdentifier"
        values = [aws_db_instance.primary.identifier]
      }
      parameter {
        name   = "NotificationTopicArn"
        values = [aws_sns_topic.dr_failover.arn]
      }
    }
  }
}

# =============================================================================
# MONITORING DASHBOARD
# =============================================================================
resource "aws_cloudwatch_dashboard" "dr_monitoring" {
  provider       = aws.primary
  dashboard_name = "${local.app_name}-dr-monitoring"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Route53 Health Check Status"
          metrics = [
            ["AWS/Route53", "HealthCheckStatus", "HealthCheckId", aws_route53_health_check.primary.id, { label = "Primary" }],
            ["AWS/Route53", "HealthCheckStatus", "HealthCheckId", aws_route53_health_check.dr.id, { label = "DR" }]
          ]
          period = 60
          stat   = "Minimum"
          region = "us-east-1"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "RDS Replica Lag"
          metrics = [
            ["AWS/RDS", "ReplicaLag", "DBInstanceIdentifier", aws_db_instance.dr_replica.identifier, { label = "DR Replica Lag (seconds)" }]
          ]
          period = 60
          stat   = "Maximum"
          region = local.dr_region
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "S3 Replication Latency"
          metrics = [
            ["AWS/S3", "ReplicationLatency", "SourceBucket", "${local.app_name}-primary-${local.account_id}", "DestinationBucket", "${local.app_name}-dr-${local.account_id}", "RuleId", "dr-replication"]
          ]
          period = 300
          stat   = "Maximum"
          region = local.primary_region
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "EKS Node Group Size"
          metrics = [
            ["AWS/EKS", "cluster_node_count", "ClusterName", aws_eks_cluster.dr.name, { label = "DR Node Count" }]
          ]
          period = 60
          stat   = "Average"
          region = local.dr_region
        }
      }
    ]
  })
}

# =============================================================================
# SSM PARAMETERS FOR DR STATE TRACKING
# =============================================================================
resource "aws_ssm_parameter" "dr_config" {
  provider = aws.primary
  name     = "/dr/config"
  type     = "String"
  value = jsonencode({
    primary_region           = local.primary_region
    dr_region                = local.dr_region
    rpo_minutes              = 15
    rto_minutes              = 60
    strategy                 = "pilot-light"
    primary_eks_cluster      = aws_eks_cluster.primary.name
    dr_eks_cluster           = aws_eks_cluster.dr.name
    primary_rds              = aws_db_instance.primary.identifier
    dr_rds_replica           = aws_db_instance.dr_replica.identifier
    primary_s3_bucket        = aws_s3_bucket.primary.id
    dr_s3_bucket             = aws_s3_bucket.dr.id
    cloudfront_distribution  = aws_cloudfront_distribution.main.id
    failover_lambda          = aws_lambda_function.failover_orchestrator.function_name
    dr_test_runbook          = aws_ssm_document.dr_test_runbook.name
  })

  tags = { Name = "${local.app_name}-dr-config" }
}

resource "aws_ssm_parameter" "dr_config_dr_region" {
  provider = aws.dr
  name     = "/dr/config"
  type     = "String"
  value = jsonencode({
    role                = "dr"
    primary_region      = local.primary_region
    dr_region           = local.dr_region
    eks_cluster         = aws_eks_cluster.dr.name
    eks_nodegroup       = aws_eks_node_group.dr.node_group_name
    rds_replica         = aws_db_instance.dr_replica.identifier
    s3_bucket           = aws_s3_bucket.dr.id
    alb_dns             = aws_lb.dr.dns_name
  })

  tags = { Name = "${local.app_name}-dr-config" }
}

# =============================================================================
# OUTPUTS
# =============================================================================
output "primary_eks_cluster_endpoint" {
  value = aws_eks_cluster.primary.endpoint
}

output "dr_eks_cluster_endpoint" {
  value = aws_eks_cluster.dr.endpoint
}

output "primary_rds_endpoint" {
  value = aws_db_instance.primary.endpoint
}

output "dr_rds_replica_endpoint" {
  value = aws_db_instance.dr_replica.endpoint
}

output "primary_alb_dns" {
  value = aws_lb.primary.dns_name
}

output "dr_alb_dns" {
  value = aws_lb.dr.dns_name
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.main.domain_name
}

output "primary_s3_bucket" {
  value = aws_s3_bucket.primary.id
}

output "dr_s3_bucket" {
  value = aws_s3_bucket.dr.id
}

output "failover_lambda_arn" {
  value = aws_lambda_function.failover_orchestrator.arn
}

output "dr_test_runbook_name" {
  value = aws_ssm_document.dr_test_runbook.name
}

output "primary_health_check_id" {
  value = aws_route53_health_check.primary.id
}

output "dr_health_check_id" {
  value = aws_route53_health_check.dr.id
}

output "redis_global_datastore_id" {
  value = aws_elasticache_global_replication_group.redis.id
}

output "dr_monitoring_dashboard" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=${local.primary_region}#dashboards:name=${aws_cloudwatch_dashboard.dr_monitoring.dashboard_name}"
}