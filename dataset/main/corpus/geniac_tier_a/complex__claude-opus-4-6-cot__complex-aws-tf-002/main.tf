###############################################################################
# variables.tf
###############################################################################
variable "region" {
  default = "us-east-1"
}

variable "cluster_name" {
  default = "zero-trust-platform"
}

variable "cluster_version" {
  default = "1.29"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "availability_zones" {
  default = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "siem_account_id" {
  description = "AWS Account ID of the centralized SIEM account"
  type        = string
  default     = "123456789012"
}

variable "tenants" {
  description = "List of tenant configurations"
  type = list(object({
    name              = string
    cpu_request_quota = string
    cpu_limit_quota   = string
    mem_request_quota = string
    mem_limit_quota   = string
    pod_quota         = string
    default_cpu_limit = string
    default_cpu_req   = string
    default_mem_limit = string
    default_mem_req   = string
  }))
  default = [
    {
      name              = "tenant-alpha"
      cpu_request_quota = "4"
      cpu_limit_quota   = "8"
      mem_request_quota = "8Gi"
      mem_limit_quota   = "16Gi"
      pod_quota         = "50"
      default_cpu_limit = "500m"
      default_cpu_req   = "100m"
      default_mem_limit = "512Mi"
      default_mem_req   = "128Mi"
    },
    {
      name              = "tenant-beta"
      cpu_request_quota = "2"
      cpu_limit_quota   = "4"
      mem_request_quota = "4Gi"
      mem_limit_quota   = "8Gi"
      pod_quota         = "30"
      default_cpu_limit = "250m"
      default_cpu_req   = "50m"
      default_mem_limit = "256Mi"
      default_mem_req   = "64Mi"
    },
    {
      name              = "tenant-gamma"
      cpu_request_quota = "6"
      cpu_limit_quota   = "12"
      mem_request_quota = "12Gi"
      mem_limit_quota   = "24Gi"
      pod_quota         = "80"
      default_cpu_limit = "1000m"
      default_cpu_req   = "200m"
      default_mem_limit = "1Gi"
      default_mem_req   = "256Mi"
    }
  ]
}

variable "cosign_public_key" {
  description = "Cosign/Sigstore public key for image verification"
  type        = string
  default     = "-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...\n-----END PUBLIC KEY-----"
}

variable "allowed_image_registries" {
  description = "Allowed container image registries"
  type        = list(string)
  default     = ["123456789012.dkr.ecr.us-east-1.amazonaws.com", "docker.io/library"]
}

###############################################################################
# providers.tf
###############################################################################
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
    kubectl = {
      source  = "alekc/kubectl"
      version = "~> 2.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = "zero-trust-platform"
      ManagedBy   = "terraform"
      Environment = "production"
    }
  }
}

provider "aws" {
  alias  = "siem"
  region = var.region
  assume_role {
    role_arn = "arn:aws:iam::${var.siem_account_id}:role/SIEMCrossAccountRole"
  }
}

provider "kubernetes" {
  host                   = aws_eks_cluster.main.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = aws_eks_cluster.main.endpoint
    cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
    }
  }
}

provider "kubectl" {
  host                   = aws_eks_cluster.main.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
  load_config_file       = false
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
  }
}

###############################################################################
# data.tf
###############################################################################
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

data "aws_iam_policy_document" "eks_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

###############################################################################
# vpc.tf
###############################################################################
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.cluster_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags = {
    Name = "${var.cluster_name}-igw"
  }
}

resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name                                        = "${var.cluster_name}-public-${var.availability_zones[count.index]}"
    "kubernetes.io/role/elb"                     = "1"
    "kubernetes.io/cluster/${var.cluster_name}"  = "shared"
  }
}

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name                                        = "${var.cluster_name}-private-${var.availability_zones[count.index]}"
    "kubernetes.io/role/internal-elb"            = "1"
    "kubernetes.io/cluster/${var.cluster_name}"  = "shared"
    "karpenter.sh/discovery"                     = var.cluster_name
  }
}

resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"
  tags = {
    Name = "${var.cluster_name}-nat-eip-${var.availability_zones[count.index]}"
  }
}

resource "aws_nat_gateway" "main" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.cluster_name}-nat-${var.availability_zones[count.index]}"
  }
  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = {
    Name = "${var.cluster_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }
  tags = {
    Name = "${var.cluster_name}-private-rt-${var.availability_zones[count.index]}"
  }
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

###############################################################################
# security_groups.tf
###############################################################################
resource "aws_security_group" "cluster" {
  name_prefix = "${var.cluster_name}-cluster-"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "${var.cluster_name}-cluster-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group" "node" {
  name_prefix = "${var.cluster_name}-node-"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name                                        = "${var.cluster_name}-node-sg"
    "karpenter.sh/discovery"                     = var.cluster_name
    "kubernetes.io/cluster/${var.cluster_name}"  = "owned"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Cluster SG rules
resource "aws_security_group_rule" "cluster_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.cluster.id
}

resource "aws_security_group_rule" "cluster_ingress_nodes" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.node.id
  security_group_id        = aws_security_group.cluster.id
}

# Node SG rules
resource "aws_security_group_rule" "node_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.node.id
}

resource "aws_security_group_rule" "node_ingress_self" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  self              = true
  security_group_id = aws_security_group.node.id
}

resource "aws_security_group_rule" "node_ingress_cluster" {
  type                     = "ingress"
  from_port                = 1025
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.cluster.id
  security_group_id        = aws_security_group.node.id
}

resource "aws_security_group_rule" "node_ingress_cluster_443" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.cluster.id
  security_group_id        = aws_security_group.node.id
}

###############################################################################
# eks.tf
###############################################################################
resource "aws_iam_role" "cluster" {
  name               = "${var.cluster_name}-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.eks_assume_role.json
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role_policy_attachment" "cluster_vpc_controller" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.cluster.name
}

resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${var.cluster_name}/cluster"
  retention_in_days = 90
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  version  = var.cluster_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
    security_group_ids      = [aws_security_group.cluster.id]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy,
    aws_iam_role_policy_attachment.cluster_vpc_controller,
    aws_cloudwatch_log_group.eks,
  ]
}

resource "aws_kms_key" "eks" {
  description             = "EKS Secret Encryption Key for ${var.cluster_name}"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.cluster_name}-eks-secrets"
  target_key_id = aws_kms_key.eks.key_id
}

###############################################################################
# oidc.tf - IRSA Foundation
###############################################################################
data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

locals {
  oidc_provider_arn = aws_iam_openid_connect_provider.eks.arn
  oidc_provider_url = replace(aws_iam_openid_connect_provider.eks.url, "https://", "")
}

###############################################################################
# eks_managed_nodegroup.tf - Initial bootstrap node group
###############################################################################
resource "aws_iam_role" "node" {
  name               = "${var.cluster_name}-node-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "node_worker" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_cni" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_ecr" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_ssm" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.node.name
}

resource "aws_eks_node_group" "system" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "system-nodes"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = aws_subnet.private[*].id

  scaling_config {
    desired_size = 3
    max_size     = 5
    min_size     = 2
  }

  instance_types = ["m6i.xlarge"]
  capacity_type  = "ON_DEMAND"

  labels = {
    "node-type" = "system"
  }

  taint {
    key    = "CriticalAddonsOnly"
    value  = "true"
    effect = "PREFER_NO_SCHEDULE"
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.node_worker,
    aws_iam_role_policy_attachment.node_cni,
    aws_iam_role_policy_attachment.node_ecr,
  ]
}

###############################################################################
# eks_addons.tf
###############################################################################
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "vpc-cni"
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.system]
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "coredns"
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.system]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "kube-proxy"
  resolve_conflicts_on_update = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.system]
}

###############################################################################
# karpenter.tf
###############################################################################
# Karpenter Controller IRSA
data "aws_iam_policy_document" "karpenter_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:karpenter:karpenter"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "karpenter_controller" {
  name               = "${var.cluster_name}-karpenter-controller"
  assume_role_policy = data.aws_iam_policy_document.karpenter_assume.json
}

resource "aws_iam_policy" "karpenter_controller" {
  name = "${var.cluster_name}-karpenter-controller"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "KarpenterEC2"
        Effect = "Allow"
        Action = [
          "ec2:CreateLaunchTemplate",
          "ec2:CreateFleet",
          "ec2:RunInstances",
          "ec2:CreateTags",
          "ec2:TerminateInstances",
          "ec2:DeleteLaunchTemplate",
          "ec2:DescribeLaunchTemplates",
          "ec2:DescribeInstances",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeSubnets",
          "ec2:DescribeInstanceTypes",
          "ec2:DescribeInstanceTypeOfferings",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeImages",
          "ec2:DescribeSpotPriceHistory",
        ]
        Resource = "*"
      },
      {
        Sid    = "KarpenterPassRole"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = aws_iam_role.node.arn
      },
      {
        Sid    = "KarpenterSSM"
        Effect = "Allow"
        Action = "ssm:GetParameter"
        Resource = "arn:${data.aws_partition.current.partition}:ssm:${var.region}::parameter/aws/service/*"
      },
      {
        Sid    = "KarpenterPricing"
        Effect = "Allow"
        Action = [
          "pricing:GetProducts",
        ]
        Resource = "*"
      },
      {
        Sid    = "KarpenterSQS"
        Effect = "Allow"
        Action = [
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ReceiveMessage",
        ]
        Resource = aws_sqs_queue.karpenter.arn
      },
      {
        Sid    = "KarpenterEKS"
        Effect = "Allow"
        Action = [
          "eks:DescribeCluster",
        ]
        Resource = aws_eks_cluster.main.arn
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "karpenter_controller" {
  role       = aws_iam_role.karpenter_controller.name
  policy_arn = aws_iam_policy.karpenter_controller.arn
}

# SQS Queue for Karpenter interruption handling
resource "aws_sqs_queue" "karpenter" {
  name                      = "${var.cluster_name}-karpenter"
  message_retention_seconds = 300
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue_policy" "karpenter" {
  queue_url = aws_sqs_queue.karpenter.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EC2InterruptionPolicy"
        Effect = "Allow"
        Principal = {
          Service = ["events.amazonaws.com", "sqs.amazonaws.com"]
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.karpenter.arn
      }
    ]
  })
}

# EventBridge rules for Karpenter
resource "aws_cloudwatch_event_rule" "karpenter_instance_state" {
  name = "${var.cluster_name}-karpenter-instance-state"
  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Instance State-change Notification"]
  })
}

resource "aws_cloudwatch_event_target" "karpenter_instance_state" {
  rule      = aws_cloudwatch_event_rule.karpenter_instance_state.name
  target_id = "KarpenterInterruptionQueueTarget"
  arn       = aws_sqs_queue.karpenter.arn
}

resource "aws_cloudwatch_event_rule" "karpenter_spot_interruption" {
  name = "${var.cluster_name}-karpenter-spot-interruption"
  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Spot Instance Interruption Warning"]
  })
}

resource "aws_cloudwatch_event_target" "karpenter_spot_interruption" {
  rule      = aws_cloudwatch_event_rule.karpenter_spot_interruption.name
  target_id = "KarpenterInterruptionQueueTarget"
  arn       = aws_sqs_queue.karpenter.arn
}

resource "aws_cloudwatch_event_rule" "karpenter_rebalance" {
  name = "${var.cluster_name}-karpenter-rebalance"
  event_pattern = jsonencode({
    source      = ["aws.ec2"]
    detail-type = ["EC2 Instance Rebalance Recommendation"]
  })
}

resource "aws_cloudwatch_event_target" "karpenter_rebalance" {
  rule      = aws_cloudwatch_event_rule.karpenter_rebalance.name
  target_id = "KarpenterInterruptionQueueTarget"
  arn       = aws_sqs_queue.karpenter.arn
}

# Instance profile for Karpenter-provisioned nodes
resource "aws_iam_instance_profile" "karpenter" {
  name = "${var.cluster_name}-karpenter-node"
  role = aws_iam_role.node.name
}

# Karpenter Helm release
resource "helm_release" "karpenter" {
  namespace        = "karpenter"
  create_namespace = true
  name             = "karpenter"
  repository       = "oci://public.ecr.aws/karpenter"
  chart            = "karpenter"
  version          = "0.35.0"
  wait             = true

  set {
    name  = "settings.clusterName"
    value = var.cluster_name
  }

  set {
    name  = "settings.clusterEndpoint"
    value = aws_eks_cluster.main.endpoint
  }

  set {
    name  = "settings.interruptionQueue"
    value = aws_sqs_queue.karpenter.name
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = aws_iam_role.karpenter_controller.arn
  }

  set {
    name  = "tolerations[0].key"
    value = "CriticalAddonsOnly"
  }

  set {
    name  = "tolerations[0].operator"
    value = "Exists"
  }

  set {
    name  = "nodeSelector.node-type"
    value = "system"
  }

  depends_on = [aws_eks_node_group.system]
}

# Karpenter NodePool - On-Demand (AZ-a, AZ-b)
resource "kubectl_manifest" "karpenter_nodeclass" {
  yaml_body = yamlencode({
    apiVersion = "karpenter.k8s.aws/v1beta1"
    kind       = "EC2NodeClass"
    metadata = {
      name = "default"
    }
    spec = {
      amiFamily = "AL2"
      role      = aws_iam_role.node.name
      subnetSelectorTerms = [{
        tags = {
          "karpenter.sh/discovery" = var.cluster_name
        }
      }]
      securityGroupSelectorTerms = [{
        tags = {
          "karpenter.sh/discovery" = var.cluster_name
        }
      }]
      blockDeviceMappings = [{
        deviceName = "/dev/xvda"
        ebs = {
          volumeSize          = "100Gi"
          volumeType          = "gp3"
          encrypted           = true
          deleteOnTermination = true
        }
      }]
      metadataOptions = {
        httpEndpoint            = "enabled"
        httpProtocolIPv6        = "disabled"
        httpPutResponseHopLimit = 2
        httpTokens              = "required"
      }
      tags = {
        "karpenter.sh/discovery" = var.cluster_name
      }
    }
  })

  depends_on = [helm_release.karpenter]
}

resource "kubectl_manifest" "karpenter_nodepool_ondemand" {
  yaml_body = yamlencode({
    apiVersion = "karpenter.sh/v1beta1"
    kind       = "NodePool"
    metadata = {
      name = "on-demand"
    }
    spec = {
      template = {
        metadata = {
          labels = {
            "capacity-type" = "on-demand"
            "node-pool"     = "on-demand"
          }
        }
        spec = {
          requirements = [
            {
              key      = "kubernetes.io/arch"
              operator = "In"
              values   = ["amd64"]
            },
            {
              key      = "karpenter.sh/capacity-type"
              operator = "In"
              values   = ["on-demand"]
            },
            {
              key      = "karpenter.k8s.aws/instance-category"
              operator = "In"
              values   = ["m", "c", "r"]
            },
            {
              key      = "karpenter.k8s.aws/instance-generation"
              operator = "Gte"
              values   = ["5"]
            },
            {
              key      = "topology.kubernetes.io/zone"
              operator = "In"
              values   = [var.availability_zones[0], var.availability_zones[1]]
            },
          ]
          nodeClassRef = {
            name = "default"
          }
        }
      }
      limits = {
        cpu    = "100"
        memory = "400Gi"
      }
      disruption = {
        consolidationPolicy = "WhenUnderutilized"
        expireAfter         = "720h"
      }
      weight = 50
    }
  })

  depends_on = [kubectl_manifest.karpenter_nodeclass]
}

resource "kubectl_manifest" "karpenter_nodepool_spot" {
  yaml_body = yamlencode({
    apiVersion = "karpenter.sh/v1beta1"
    kind       = "NodePool"
    metadata = {
      name = "spot"
    }
    spec = {
      template = {
        metadata = {
          labels = {
            "capacity-type" = "spot"
            "node-pool"     = "spot"
          }
        }
        spec = {
          requirements = [
            {
              key      = "kubernetes.io/arch"
              operator = "In"
              values   = ["amd64"]
            },
            {
              key      = "karpenter.sh/capacity-type"
              operator = "In"
              values   = ["spot"]
            },
            {
              key      = "karpenter.k8s.aws/instance-category"
              operator = "In"
              values   = ["m", "c", "r"]
            },
            {
              key      = "karpenter.k8s.aws/instance-generation"
              operator = "Gte"
              values   = ["5"]
            },
            {
              key      = "topology.kubernetes.io/zone"
              operator = "In"
              values   = [var.availability_zones[2]]
            },
          ]
          nodeClassRef = {
            name = "default"
          }
          taints = [{
            key    = "capacity-type"
            value  = "spot"
            effect = "NoSchedule"
          }]
        }
      }
      limits = {
        cpu    = "200"
        memory = "800Gi"
      }
      disruption = {
        consolidationPolicy = "WhenUnderutilized"
        expireAfter         = "168h"
      }
      weight = 100
    }
  })

  depends_on = [kubectl_manifest.karpenter_nodeclass]
}

###############################################################################
# istio.tf - Service Mesh with mTLS
###############################################################################
resource "kubernetes_namespace" "istio_system" {
  metadata {
    name = "istio-system"
    labels = {
      "istio-injection" = "disabled"
    }
  }
  depends_on = [aws_eks_node_group.system]
}

resource "helm_release" "istio_base" {
  name       = "istio-base"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "base"
  namespace  = kubernetes_namespace.istio_system.metadata[0].name
  version    = "1.21.0"
  wait       = true
}

resource "helm_release" "istiod" {
  name       = "istiod"
  repository = "https://istio-release.storage.googleapis.com/charts"
  chart      = "istiod"
  namespace  = kubernetes_namespace.istio_system.metadata[0].name
  version    = "1.21.0"
  wait       = true

  set {
    name  = "meshConfig.accessLogFile"
    value = "/dev/stdout"
  }

  set {
    name  = "meshConfig.accessLogEncoding"
    value = "JSON"
  }

  set {
    name  = "meshConfig.enableAutoMtls"
    value = "true"
  }

  set {
    name  = "meshConfig.outboundTrafficPolicy.mode"
    value = "REGISTRY_ONLY"
  }

  set {
    name  = "global.proxy.privileged"
    value = "false"
  }

  set {
    name  = "pilot.tolerations[0].key"
    value = "CriticalAddonsOnly"
  }

  set {
    name  = "pilot.tolerations[0].operator"
    value = "Exists"
  }

  depends_on = [helm_release.istio_base]
}

# Enforce STRICT mTLS cluster-wide
resource "kubectl_manifest" "istio_strict_mtls" {
  yaml_body = yamlencode({
    apiVersion = "security.istio.io/v1beta1"
    kind       = "PeerAuthentication"
    metadata = {
      name      = "default"
      namespace = "istio-system"
    }
    spec = {
      mtls = {
        mode = "STRICT"
      }
    }
  })

  depends_on = [helm_release.istiod]
}

# Authorization policy - deny all by default
resource "kubectl_manifest" "istio_deny_all" {
  yaml_body = yamlencode({
    apiVersion = "security.istio.io/v1beta1"
    kind       = "AuthorizationPolicy"
    metadata = {
      name      = "deny-all"
      namespace = "istio-system"
    }
    spec = {}
  })

  depends_on = [helm_release.istiod]
}

###############################################################################
# opa_gatekeeper.tf
###############################################################################
resource "helm_release" "gatekeeper" {
  name             = "gatekeeper"
  repository       = "https://open-policy-agent.github.io/gatekeeper/charts"
  chart            = "gatekeeper"
  namespace        = "gatekeeper-system"
  create_namespace = true
  version          = "3.15.0"
  wait             = true

  set {
    name  = "replicas"
    value = "3"
  }

  set {
    name  = "audit.replicas"
    value = "2"
  }

  set {
    name  = "tolerations[0].key"
    value = "CriticalAddonsOnly"
  }

  set {
    name  = "tolerations[0].operator"
    value = "Exists"
  }

  depends_on = [aws_eks_node_group.system]
}

# ConstraintTemplate: Deny Privileged Containers
resource "kubectl_manifest" "constraint_template_privileged" {
  yaml_body = <<-YAML
    apiVersion: templates.gatekeeper.sh/v1
    kind: ConstraintTemplate
    metadata:
      name: k8spspprivilegedcontainer
    spec:
      crd:
        spec:
          names:
            kind: K8sPSPPrivilegedContainer
          validation:
            openAPIV3Schema:
              type: object
              properties:
                exemptImages:
                  type: array
                  items:
                    type: string
      targets:
        - target: admission.k8s.gatekeeper.sh
          rego: |
            package k8spspprivileged

            violation[{"msg": msg, "details": {}}] {
              c := input_containers[_]
              c.securityContext.privileged == true
              not is_exempt(c)
              msg := sprintf("Privileged container is not allowed: %v, securityContext: %v", [c.name, c.securityContext])
            }

            input_containers[c] {
              c := input.review.object.spec.containers[_]
            }

            input_containers[c] {
              c := input.review.object.spec.initContainers[_]
            }

            input_containers[c] {
              c := input.review.object.spec.ephemeralContainers[_]
            }

            is_exempt(c) {
              exempt_images := object.get(input, ["parameters", "exemptImages"], [])
              img := c.image
              exemption := exempt_images[_]
              _matches_exemption(img, exemption)
            }

            _matches_exemption(img, exemption) {
              not endswith(exemption, "*")
              img == exemption
            }

            _matches_exemption(img, exemption) {
              endswith(exemption, "*")
              prefix := trim_suffix(exemption, "*")
              startswith(img, prefix)
            }
  YAML

  depends_on = [helm_release.gatekeeper]
}

# Constraint: Deny Privileged Containers
resource "kubectl_manifest" "constraint_privileged" {
  yaml_body = <<-YAML
    apiVersion: constraints.gatekeeper.sh/v1beta1
    kind: K8sPSPPrivilegedContainer
    metadata:
      name: deny-privileged-containers
    spec:
      enforcementAction: deny
      match:
        kinds:
          - apiGroups: [""]
            kinds: ["Pod"]
        excludedNamespaces:
          - kube-system
          - gatekeeper-system
          - istio-system
          - karpenter
      parameters:
        exemptImages:
          - "istio/proxyv2:*"
  YAML

  depends_on = [kubectl_manifest.constraint_template_privileged]
}

# ConstraintTemplate: Deny host namespace sharing
resource "kubectl_manifest" "constraint_template_host_namespace" {
  yaml_body = <<-YAML
    apiVersion: templates.gatekeeper.sh/v1
    kind: ConstraintTemplate
    metadata:
      name: k8spsphostnamespace
    spec:
      crd:
        spec:
          names:
            kind: K8sPSPHostNamespace
      targets:
        - target: admission.k8s.gatekeeper.sh
          rego: |
            package k8spsphostnamespace

            violation[{"msg": msg, "details": {}}] {
              input_share_hostnamespace(input.review.object)
              msg := sprintf("Sharing the host namespace is not allowed: %v", [input.review.object.metadata.name])
            }

            input_share_hostnamespace(o) {
              o.spec.hostPID == true
            }

            input_share_hostnamespace(o) {
              o.spec.hostIPC == true
            }

            input_share_hostnamespace(o) {
              o.spec.hostNetwork == true
            }
  YAML

  depends_on = [helm_release.gatekeeper]
}

resource "kubectl_manifest" "constraint_host_namespace" {
  yaml_body = <<-YAML
    apiVersion: constraints.gatekeeper.sh/v1beta1
    kind: K8sPSPHostNamespace
    metadata:
      name: deny-host-namespace
    spec:
      enforcementAction: deny
      match:
        kinds:
          - apiGroups: [""]
            kinds: ["Pod"]
        excludedNamespaces:
          - kube-system
          - gatekeeper-system
          - istio-system
          - karpenter
  YAML

  depends_on = [kubectl_manifest.constraint_template_host_namespace]
}

# ConstraintTemplate: Enforce Image Signing via Cosign/Sigstore
resource "kubectl_manifest" "constraint_template_image_signing" {
  yaml_body = <<-YAML
    apiVersion: templates.gatekeeper.sh/v1
    kind: ConstraintTemplate
    metadata:
      name: k8simagecosignsigned
    spec:
      crd:
        spec:
          names:
            kind: K8sImageCosignSigned
          validation:
            openAPIV3Schema:
              type: object
              properties:
                allowedRegistries:
                  type: array
                  items:
                    type: string
                  description: "List of allowed registries that require signed images"
                cosignPublicKey:
                  type: string
                  description: "Cosign public key for verification"
      targets:
        - target: admission.k8s.gatekeeper.sh
          rego: |
            package k8simagecosignsigned

            violation[{"msg": msg}] {
              container := input_containers[_]
              image := container.image
              not image_allowed(image)
              msg := sprintf("Container image '%v' is not from an allowed registry or is not signed. Allowed registries: %v", [image, input.parameters.allowedRegistries])
            }

            input_containers[c] {
              c := input.review.object.spec.containers[_]
            }

            input_containers[c] {
              c := input.review.object.spec.initContainers[_]
            }

            image_allowed(image) {
              allowed := input.parameters.allowedRegistries[_]
              startswith(image, allowed)
            }

            violation[{"msg": msg}] {
              container := input_containers[_]
              image := container.image
              not contains(image, "@sha256:")
              image_requires_digest(image)
              msg := sprintf("Container image '%v' must use a digest (sha256) reference for verified images", [image])
            }

            image_requires_digest(image) {
              allowed := input.parameters.allowedRegistries[_]
              startswith(image, allowed)
            }
  YAML

  depends_on = [helm_release.gatekeeper]
}

resource "kubectl_manifest" "constraint_image_signing" {
  yaml_body = yamlencode({
    apiVersion = "constraints.gatekeeper.sh/v1beta1"
    kind       = "K8sImageCosignSigned"
    metadata = {
      name = "require-signed-images"
    }
    spec = {
      enforcementAction = "deny"
      match = {
        kinds = [{
          apiGroups = [""]
          kinds     = ["Pod"]
        }]
        excludedNamespaces = [
          "kube-system",
          "gatekeeper-system",
          "istio-system",
          "karpenter",
          "cert-manager",
          "external-dns",
          "fluent-bit",
          "secrets-store-csi",
        ]
      }
      parameters = {
        allowedRegistries = var.allowed_image_registries
        cosignPublicKey   = var.cosign_public_key
      }
    }
  })

  depends_on = [kubectl_manifest.constraint_template_image_signing]
}

# ConstraintTemplate: Require non-root containers
resource "kubectl_manifest" "constraint_template_nonroot" {
  yaml_body = <<-YAML
    apiVersion: templates.gatekeeper.sh/v1
    kind: ConstraintTemplate
    metadata:
      name: k8spsprunasnonroot
    spec:
      crd:
        spec:
          names:
            kind: K8sPSPRunAsNonRoot
      targets:
        - target: admission.k8s.gatekeeper.sh
          rego: |
            package k8spsprunasnonroot

            violation[{"msg": msg}] {
              container := input_containers[_]
              not container.securityContext.runAsNonRoot == true
              not input.review.object.spec.securityContext.runAsNonRoot == true
              msg := sprintf("Container %v must set securityContext.runAsNonRoot to true", [container.name])
            }

            input_containers[c] {
              c := input.review.object.spec.containers[_]
            }

            input_containers[c] {
              c := input.review.object.spec.initContainers[_]
            }
  YAML

  depends_on = [helm_release.gatekeeper]
}

resource "kubectl_manifest" "constraint_nonroot" {
  yaml_body = <<-YAML
    apiVersion: constraints.gatekeeper.sh/v1beta1
    kind: K8sPSPRunAsNonRoot
    metadata:
      name: require-run-as-nonroot
    spec:
      enforcementAction: deny
      match:
        kinds:
          - apiGroups: [""]
            kinds: ["Pod"]
        excludedNamespaces:
          - kube-system
          - gatekeeper-system
          - istio-system
          - karpenter
  YAML

  depends_on = [kubectl_manifest.constraint_template_nonroot]
}

# ConstraintTemplate: Read-only root filesystem
resource "kubectl_manifest" "constraint_template_readonly_rootfs" {
  yaml_body = <<-YAML
    apiVersion: templates.gatekeeper.sh/v1
    kind: ConstraintTemplate
    metadata:
      name: k8spspreadonlyrootfilesystem
    spec:
      crd:
        spec:
          names:
            kind: K8sPSPReadOnlyRootFilesystem
      targets:
        - target: admission.k8s.gatekeeper.sh
          rego: |
            package k8spspreadonlyrootfilesystem

            violation[{"msg": msg}] {
              container := input_containers[_]
              not container.securityContext.readOnlyRootFilesystem == true
              msg := sprintf("Container %v must set readOnlyRootFilesystem to true", [container.name])
            }

            input_containers[c] {
              c := input.review.object.spec.containers[_]
            }

            input_containers[c] {
              c := input.review.object.spec.initContainers[_]
            }
  YAML

  depends_on = [helm_release.gatekeeper]
}

resource "kubectl_manifest" "constraint_readonly_rootfs" {
  yaml_body = <<-YAML
    apiVersion: constraints.gatekeeper.sh/v1beta1
    kind: K8sPSPReadOnlyRootFilesystem
    metadata:
      name: require-readonly-rootfs
    spec:
      enforcementAction: warn
      match:
        kinds:
          - apiGroups: [""]
            kinds: ["Pod"]
        excludedNamespaces:
          - kube-system
          - gatekeeper-system
          - istio-system
          - karpenter
  YAML

  depends_on = [kubectl_manifest.constraint_template_readonly_rootfs]
}

###############################################################################
# route53.tf - Private Hosted Zone + External DNS
###############################################################################
resource "aws_route53_zone" "private" {
  name = "internal.${var.cluster_name}.local"

  vpc {
    vpc_id = aws_vpc.main.id
  }

  tags = {
    Name = "${var.cluster_name}-private-zone"
  }
}

# External DNS IRSA
data "aws_iam_policy_document" "external_dns_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:external-dns:external-dns"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "external_dns" {
  name               = "${var.cluster_name}-external-dns"
  assume_role_policy = data.aws_iam_policy_document.external_dns_assume.json
}

resource "aws_iam_policy" "external_dns" {
  name = "${var.cluster_name}-external-dns"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "route53:ChangeResourceRecordSets",
        ]
        Resource = [
          "arn:${data.aws_partition.current.partition}:route53:::hostedzone/${aws_route53_zone.private.zone_id}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "route53:ListHostedZones",
          "route53:ListResourceRecordSets",
          "route53:ListTagsForResource",
        ]
        Resource = ["*"]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "external_dns" {
  role       = aws_iam_role.external_dns.name
  policy_arn = aws_iam_policy.external_dns.arn
}

resource "helm_release" "external_dns" {
  name             = "external-dns"
  repository       = "https://kubernetes-sigs.github.io/external-dns/"
  chart            = "external-dns"
  namespace        = "external-dns"
  create_namespace = true
  version          = "1.14.3"
  wait             = true

  set {
    name  = "provider"
    value = "aws"
  }

  set {
    name  = "aws.zoneType"
    value = "private"
  }

  set {
    name  = "domainFilters[0]"
    value = "internal.${var.cluster_name}.local"
  }

  set {
    name  = "policy"
    value = "sync"
  }

  set {
    name  = "registry"
    value = "txt"
  }

  set {
    name  = "txtOwnerId"
    value = var.cluster_name
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = aws_iam_role.external_dns.arn
  }

  set {
    name  = "sources[0]"
    value = "service"
  }

  set {
    name  = "sources[1]"
    value = "ingress"
  }

  set {
    name  = "tolerations[0].key"
    value = "CriticalAddonsOnly"
  }

  set {
    name  = "tolerations[0].operator"
    value = "Exists"
  }

  depends_on = [aws_eks_node_group.system]
}

###############################################################################
# secrets_store_csi.tf - AWS Secrets Manager CSI Driver
###############################################################################
data "aws_iam_policy_document" "secrets_csi_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:secrets-store-csi:secrets-store-csi-driver"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "secrets_csi" {
  name               = "${var.cluster_name}-secrets-csi"
  assume_role_policy = data.aws_iam_policy_document.secrets_csi_assume.json
}

resource "aws_iam_policy" "secrets_csi" {
  name = "${var.cluster_name}-secrets-csi"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
        ]
        Resource = "arn:${data.aws_partition.current.partition}:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.cluster_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
        ]
        Resource = "arn:${data.aws_partition.current.partition}:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter/${var.cluster_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
        ]
        Resource = aws_kms_key.eks.arn
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "secrets_csi" {
  role       = aws_iam_role.secrets_csi.name
  policy_arn = aws_iam_policy.secrets_csi.arn
}

resource "helm_release" "secrets_store_csi" {
  name             = "secrets-store-csi-driver"
  repository       = "https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts"
  chart            = "secrets-store-csi-driver"
  namespace        = "secrets-store-csi"
  create_namespace = true
  version          = "1.4.1"
  wait             = true

  set {
    name  = "syncSecret.enabled"
    value = "true"
  }

  set {
    name  = "enableSecretRotation"
    value = "true"
  }

  set {
    name  = "rotationPollInterval"
    value = "120s"
  }

  depends_on = [aws_eks_node_group.system]
}

resource "helm_release" "secrets_store_csi_aws" {
  name       = "secrets-store-csi-driver-provider-aws"
  repository = "https://aws.github.io/secrets-store-csi-driver-provider-aws"
  chart      = "secrets-store-csi-driver-provider-aws"
  namespace  = "secrets-store-csi"
  version    = "0.3.6"
  wait       = true

  depends_on = [helm_release.secrets_store_csi]
}

# Per-tenant IRSA for Secrets Manager access
resource "aws_iam_role" "tenant_secrets" {
  for_each = { for t in var.tenants : t.name => t }

  name = "${var.cluster_name}-${each.key}-secrets"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = local.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_provider_url}:sub" = "system:serviceaccount:${each.key}:${each.key}-sa"
          "${local.oidc_provider_url}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_policy" "tenant_secrets" {
  for_each = { for t in var.tenants : t.name => t }

  name = "${var.cluster_name}-${each.key}-secrets"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
        ]
        Resource = "arn:${data.aws_partition.current.partition}:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.cluster_name}/${each.key}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
        ]
        Resource = aws_kms_key.eks.arn
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "tenant_secrets" {
  for_each   = { for t in var.tenants : t.name => t }
  role       = aws_iam_role.tenant_secrets[each.key].name
  policy_arn = aws_iam_policy.tenant_secrets[each.key].arn
}

###############################################################################
# multi_tenant.tf - Namespaces, ResourceQuotas, LimitRanges, NetworkPolicies
###############################################################################
resource "kubernetes_namespace" "tenant" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name = each.key
    labels = {
      "tenant"                         = each.key
      "istio-injection"                = "enabled"
      "pod-security.kubernetes.io/enforce" = "restricted"
      "pod-security.kubernetes.io/audit"   = "restricted"
      "pod-security.kubernetes.io/warn"    = "restricted"
    }
    annotations = {
      "scheduler.alpha.kubernetes.io/defaultTolerations" = "[]"
    }
  }

  depends_on = [aws_eks_node_group.system]
}

resource "kubernetes_resource_quota" "tenant" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name      = "${each.key}-quota"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = each.value.cpu_request_quota
      "limits.cpu"      = each.value.cpu_limit_quota
      "requests.memory" = each.value.mem_request_quota
      "limits.memory"   = each.value.mem_limit_quota
      "pods"            = each.value.pod_quota
      "services"        = "20"
      "secrets"         = "50"
      "configmaps"      = "50"
      "persistentvolumeclaims" = "20"
      "services.loadbalancers" = "2"
      "services.nodeports"     = "0"
    }
  }
}

resource "kubernetes_limit_range" "tenant" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name      = "${each.key}-limits"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = each.value.default_cpu_limit
        memory = each.value.default_mem_limit
      }
      default_request = {
        cpu    = each.value.default_cpu_req
        memory = each.value.default_mem_req
      }
      max = {
        cpu    = "4"
        memory = "8Gi"
      }
      min = {
        cpu    = "10m"
        memory = "16Mi"
      }
    }
    limit {
      type = "Pod"
      max = {
        cpu    = "8"
        memory = "16Gi"
      }
    }
    limit {
      type = "PersistentVolumeClaim"
      max = {
        storage = "50Gi"
      }
      min = {
        storage = "1Gi"
      }
    }
  }
}

# Default deny all ingress/egress NetworkPolicy per tenant
resource "kubernetes_network_policy" "tenant_default_deny" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name      = "default-deny-all"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }
}

# Allow intra-tenant communication only
resource "kubernetes_network_policy" "tenant_allow_intra" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name      = "allow-intra-tenant"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]

    ingress {
      from {
        namespace_selector {
          match_labels = {
            tenant = each.key
          }
        }
      }
    }

    egress {
      to {
        namespace_selector {
          match_labels = {
            tenant = each.key
          }
        }
      }
    }
  }
}

# Allow DNS resolution
resource "kubernetes_network_policy" "tenant_allow_dns" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name      = "allow-dns"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      to {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = "kube-system"
          }
        }
      }
      ports {
        port     = "53"
        protocol = "UDP"
      }
      ports {
        port     = "53"
        protocol = "TCP"
      }
    }
  }
}

# Allow egress to Istio control plane
resource "kubernetes_network_policy" "tenant_allow_istio" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name      = "allow-istio-control-plane"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      to {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = "istio-system"
          }
        }
      }
      ports {
        port     = "15012"
        protocol = "TCP"
      }
      ports {
        port     = "15014"
        protocol = "TCP"
      }
    }
  }
}

# Allow Istio sidecar proxy traffic
resource "kubernetes_network_policy" "tenant_allow_istio_sidecar" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name      = "allow-istio-sidecar"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]

    ingress {
      ports {
        port     = "15006"
        protocol = "TCP"
      }
      ports {
        port     = "15001"
        protocol = "TCP"
      }
      ports {
        port     = "15090"
        protocol = "TCP"
      }
    }

    egress {
      ports {
        port     = "15006"
        protocol = "TCP"
      }
        ports {
        port     = "15001"
        protocol = "TCP"
      }
    }
  }
}

# Tenant service accounts with IRSA
resource "kubernetes_service_account" "tenant" {
  for_each = { for t in var.tenants : t.name => t }

  metadata {
    name      = "${each.key}-sa"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.tenant_secrets[each.key].arn
    }
    labels = {
      tenant = each.key
    }
  }
}

# Istio AuthorizationPolicy per tenant - allow only intra-tenant
resource "kubectl_manifest" "tenant_istio_authz" {
  for_each = { for t in var.tenants : t.name => t }

  yaml_body = yamlencode({
    apiVersion = "security.istio.io/v1beta1"
    kind       = "AuthorizationPolicy"
    metadata = {
      name      = "allow-intra-tenant"
      namespace = each.key
    }
    spec = {
      action = "ALLOW"
      rules = [{
        from = [{
          source = {
            namespaces = [each.key]
          }
        }]
      }]
    }
  })

  depends_on = [
    helm_release.istiod,
    kubernetes_namespace.tenant,
  ]
}

# SecretProviderClass per tenant
resource "kubectl_manifest" "tenant_secret_provider" {
  for_each = { for t in var.tenants : t.name => t }

  yaml_body = yamlencode({
    apiVersion = "secrets-store.csi.x-k8s.io/v1"
    kind       = "SecretProviderClass"
    metadata = {
      name      = "${each.key}-aws-secrets"
      namespace = each.key
    }
    spec = {
      provider = "aws"
      parameters = {
        objects = yamlencode([
          {
            objectName  = "${var.cluster_name}/${each.key}/app-secrets"
            objectType  = "secretsmanager"
            jmesPath = [
              {
                path        = "username"
                objectAlias = "db-username"
              },
              {
                path        = "password"
                objectAlias = "db-password"
              },
            ]
          }
        ])
      }
      secretObjects = [{
        secretName = "${each.key}-db-credentials"
        type       = "Opaque"
        data = [
          {
            objectName = "db-username"
            key        = "username"
          },
          {
            objectName = "db-password"
            key        = "password"
          },
        ]
      }]
    }
  })

  depends_on = [
    helm_release.secrets_store_csi_aws,
    kubernetes_namespace.tenant,
  ]
}

###############################################################################
# fluent_bit.tf - Logging to CloudWatch + Cross-Account SIEM
###############################################################################
# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/eks/${var.cluster_name}/application"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "dataplane" {
  name              = "/aws/eks/${var.cluster_name}/dataplane"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "host" {
  name              = "/aws/eks/${var.cluster_name}/host"
  retention_in_days = 14
}

# Fluent Bit IRSA
data "aws_iam_policy_document" "fluent_bit_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:fluent-bit:fluent-bit"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "fluent_bit" {
  name               = "${var.cluster_name}-fluent-bit"
  assume_role_policy = data.aws_iam_policy_document.fluent_bit_assume.json
}

resource "aws_iam_policy" "fluent_bit" {
  name = "${var.cluster_name}-fluent-bit"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:CreateLogGroup",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams",
          "logs:DescribeLogGroups",
          "logs:PutRetentionPolicy",
        ]
        Resource = [
          "arn:${data.aws_partition.current.partition}:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/eks/${var.cluster_name}/*",
          "arn:${data.aws_partition.current.partition}:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/eks/${var.cluster_name}/*:*",
        ]
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "fluent_bit" {
  role       = aws_iam_role.fluent_bit.name
  policy_arn = aws_iam_policy.fluent_bit.arn
}

resource "helm_release" "fluent_bit" {
  name             = "fluent-bit"
  repository       = "https://fluent.github.io/helm-charts"
  chart            = "fluent-bit"
  namespace        = "fluent-bit"
  create_namespace = true
  version          = "0.43.0"
  wait             = true

  values = [yamlencode({
    serviceAccount = {
      create = true
      name   = "fluent-bit"
      annotations = {
        "eks.amazonaws.com/role-arn" = aws_iam_role.fluent_bit.arn
      }
    }

    tolerations = [
      {
        operator = "Exists"
      }
    ]

    config = {
      service = <<-EOF
        [SERVICE]
            Daemon Off
            Flush 5
            Log_Level info
            Parsers_File /fluent-bit/etc/parsers.conf
            HTTP_Server On
            HTTP_Listen 0.0.0.0
            HTTP_Port 2020
            Health_Check On
            storage.path /var/fluent-bit/state/flb-storage/
            storage.sync normal
            storage.checksum off
            storage.backlog.mem_limit 5M
      EOF

      inputs = <<-EOF
        [INPUT]
            Name tail
            Tag kube.*
            Path /var/log/containers/*.log
            multiline.parser docker, cri
            DB /var/fluent-bit/state/flb_container.db
            Mem_Buf_Limit 50MB
            Skip_Long_Lines On
            Refresh_Interval 10
            Rotate_Wait 30
            storage.type filesystem
            Read_from_Head Off

        [INPUT]
            Name systemd
            Tag host.systemd.*
            Systemd_Filter _SYSTEMD_UNIT=kubelet.service
            Systemd_Filter _SYSTEMD_UNIT=containerd.service
            Read_From_Tail On
            DB /var/fluent-bit/state/systemd.db
      EOF

      filters = <<-EOF
        [FILTER]
            Name kubernetes
            Match kube.*
            Merge_Log On
            Keep_Log Off
            K8S-Logging.Parser On
            K8S-Logging.Exclude On
            Labels On
            Annotations Off
            Buffer_Size 0

        [FILTER]
            Name modify
            Match kube.*
            Add cluster ${var.cluster_name}
            Add region ${var.region}
            Add account_id ${data.aws_caller_identity.current.account_id}

        [FILTER]
            Name rewrite_tag
            Match kube.*
            Rule $kubernetes['namespace_name'] ^(tenant-.*)$ tenant.$1 false
            Emitter_Name re_emitted

        [FILTER]
            Name grep
            Match kube.*
            Exclude $kubernetes['namespace_name'] ^(kube-system|gatekeeper-system)$
      EOF

      outputs = <<-EOF
        [OUTPUT]
            Name cloudwatch_logs
            Match kube.*
            region ${var.region}
            log_group_name /aws/eks/${var.cluster_name}/application
            log_stream_prefix fluentbit-
            auto_create_group true
            log_key log
            extra_user_agent container-insights

        [OUTPUT]
            Name cloudwatch_logs
            Match tenant.*
            region ${var.region}
            log_group_name /aws/eks/${var.cluster_name}/application
            log_stream_prefix tenant-
            auto_create_group true
            log_key log

        [OUTPUT]
            Name cloudwatch_logs
            Match host.*
            region ${var.region}
            log_group_name /aws/eks/${var.cluster_name}/host
            log_stream_prefix host-
            auto_create_group true
      EOF
    }

    volumeMounts = [
      {
        name      = "var-log"
        mountPath = "/var/log"
        readOnly  = true
      },
      {
        name      = "var-lib-docker-containers"
        mountPath = "/var/lib/docker/containers"
        readOnly  = true
      },
      {
        name      = "flb-storage"
        mountPath = "/var/fluent-bit/state"
      },
      {
        name      = "run-log-journal"
        mountPath = "/run/log/journal"
        readOnly  = true
      },
    ]

    volumes = [
      {
        name = "var-log"
        hostPath = {
          path = "/var/log"
        }
      },
      {
        name = "var-lib-docker-containers"
        hostPath = {
          path = "/var/lib/docker/containers"
        }
      },
      {
        name = "flb-storage"
        hostPath = {
          path = "/var/fluent-bit/state"
        }
      },
      {
        name = "run-log-journal"
        hostPath = {
          path = "/run/log/journal"
        }
      },
    ]

    resources = {
      limits = {
        cpu    = "200m"
        memory = "256Mi"
      }
      requests = {
        cpu    = "50m"
        memory = "64Mi"
      }
    }
  })]

  depends_on = [aws_eks_node_group.system]
}

###############################################################################
# cross_account_siem.tf - CloudWatch Subscription Filters
###############################################################################
# Destination in SIEM account (cross-account Kinesis or CloudWatch destination)
resource "aws_cloudwatch_log_destination" "siem" {
  name       = "${var.cluster_name}-siem-destination"
  role_arn   = aws_iam_role.cloudwatch_to_siem.arn
  target_arn = aws_kinesis_stream.siem.arn
}

resource "aws_kinesis_stream" "siem" {
  name             = "${var.cluster_name}-siem-logs"
  shard_count      = 2
  retention_period = 48

  encryption_type = "KMS"
  kms_key_id      = "alias/aws/kinesis"

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    Name = "${var.cluster_name}-siem-logs"
  }
}

resource "aws_iam_role" "cloudwatch_to_siem" {
  name = "${var.cluster_name}-cw-to-siem"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "logs.${var.region}.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringLike = {
          "aws:SourceArn" = "arn:${data.aws_partition.current.partition}:logs:${var.region}:${data.aws_caller_identity.current.account_id}:*"
        }
      }
    }]
  })
}

resource "aws_iam_policy" "cloudwatch_to_kinesis" {
  name = "${var.cluster_name}-cw-to-kinesis"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords",
        ]
        Resource = aws_kinesis_stream.siem.arn
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cloudwatch_to_kinesis" {
  role       = aws_iam_role.cloudwatch_to_siem.name
  policy_arn = aws_iam_policy.cloudwatch_to_kinesis.arn
}

resource "aws_cloudwatch_log_destination_policy" "siem" {
  destination_name = aws_cloudwatch_log_destination.siem.name
  access_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowSIEMAccount"
      Effect = "Allow"
      Principal = {
        AWS = var.siem_account_id
      }
      Action   = "logs:PutSubscriptionFilter"
      Resource = aws_cloudwatch_log_destination.siem.arn
    }]
  })
}

# Subscription filters for each log group
resource "aws_cloudwatch_log_subscription_filter" "application_to_siem" {
  name            = "${var.cluster_name}-app-to-siem"
  log_group_name  = aws_cloudwatch_log_group.application.name
  filter_pattern  = ""
  destination_arn = aws_kinesis_stream.siem.arn
  role_arn        = aws_iam_role.cloudwatch_to_siem.arn

  depends_on = [aws_iam_role_policy_attachment.cloudwatch_to_kinesis]
}

resource "aws_cloudwatch_log_subscription_filter" "dataplane_to_siem" {
  name            = "${var.cluster_name}-dataplane-to-siem"
  log_group_name  = aws_cloudwatch_log_group.dataplane.name
  filter_pattern  = ""
  destination_arn = aws_kinesis_stream.siem.arn
  role_arn        = aws_iam_role.cloudwatch_to_siem.arn

  depends_on = [aws_iam_role_policy_attachment.cloudwatch_to_kinesis]
}

resource "aws_cloudwatch_log_subscription_filter" "eks_control_plane_to_siem" {
  name            = "${var.cluster_name}-controlplane-to-siem"
  log_group_name  = aws_cloudwatch_log_group.eks.name
  filter_pattern  = ""
  destination_arn = aws_kinesis_stream.siem.arn
  role_arn        = aws_iam_role.cloudwatch_to_siem.arn

  depends_on = [aws_iam_role_policy_attachment.cloudwatch_to_kinesis]
}

resource "aws_cloudwatch_log_subscription_filter" "host_to_siem" {
  name            = "${var.cluster_name}-host-to-siem"
  log_group_name  = aws_cloudwatch_log_group.host.name
  filter_pattern  = ""
  destination_arn = aws_kinesis_stream.siem.arn
  role_arn        = aws_iam_role.cloudwatch_to_siem.arn

  depends_on = [aws_iam_role_policy_attachment.cloudwatch_to_kinesis]
}

# Cross-account IAM policy for SIEM account to read from Kinesis
resource "aws_kinesis_stream_consumer" "siem" {
  name       = "siem-consumer"
  stream_arn = aws_kinesis_stream.siem.arn
}

###############################################################################
# outputs.tf
###############################################################################
output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "cluster_certificate_authority" {
  value     = aws_eks_cluster.main.certificate_authority[0].data
  sensitive = true
}

output "oidc_provider_arn" {
  value = local.oidc_provider_arn
}

output "oidc_provider_url" {
  value = local.oidc_provider_url
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "route53_private_zone_id" {
  value = aws_route53_zone.private.zone_id
}

output "route53_private_zone_name" {
  value = aws_route53_zone.private.name
}

output "karpenter_controller_role_arn" {
  value = aws_iam_role.karpenter_controller.arn
}

output "fluent_bit_role_arn" {
  value = aws_iam_role.fluent_bit.arn
}

output "external_dns_role_arn" {
  value = aws_iam_role.external_dns.arn
}

output "secrets_csi_role_arn" {
  value = aws_iam_role.secrets_csi.arn
}

output "tenant_namespaces" {
  value = [for t in var.tenants : t.name]
}

output "tenant_irsa_role_arns" {
  value = { for k, v in aws_iam_role.tenant_secrets : k => v.arn }
}

output "siem_kinesis_stream_arn" {
  value = aws_kinesis_stream.siem.arn
}

output "cloudwatch_log_groups" {
  value = {
    application   = aws_cloudwatch_log_group.application.name
    dataplane     = aws_cloudwatch_log_group.dataplane.name
    host          = aws_cloudwatch_log_group.host.name
    control_plane = aws_cloudwatch_log_group.eks.name
  }
}