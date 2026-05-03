# Day 125: EKS 基础设施

> 📅 日期：2026-05-04
> 📖 学习主题：Terraform 管理 EKS 集群、节点组、IRSA、Add-ons、完整集群部署
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 114（EKS 弹性 Kubernetes）、Day 120-124（Terraform 全部课程）

---

## 🎯 学习目标

- 掌握使用 Terraform 管理 EKS 集群的完整流程
- 理解托管节点组（Managed Node Group）和 Fargate Profile 的配置
- 掌握 IRSA（IAM Roles for Service Accounts）的实现
- 了解 EKS Add-ons 的管理方式
- 能独立完成从 VPC 到 EKS 集群的完整基础设施部署

---

## 📖 核心知识点

### 1. EKS 架构概览

```
┌───────────────────────────────────────────────────────────────┐
│                    EKS 完整架构                                │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    VPC: 10.0.0.0/16                     │  │
│  │                                                         │  │
│  │  ┌─── Public Subnets ──┐  ┌─── Private Subnets ──────┐ │  │
│  │  │                     │  │                           │ │  │
│  │  │  ┌──────┐ ┌──────┐  │  │  ┌─────────────────────┐ │ │  │
│  │  │  │ ALB  │ │ NAT  │  │  │  │   EKS Control Plane │ │ │  │
│  │  │  │      │ │  GW  │  │  │  │   (AWS Managed)     │ │ │  │
│  │  │  └──────┘ └──────┘  │  │  └─────────────────────┘ │ │  │
│  │  │                     │  │                           │ │  │
│  │  │                     │  │  ┌─────────────────────┐ │ │  │
│  │  │                     │  │  │  Managed Node Group │ │ │  │
│  │  │                     │  │  │  ┌─────┐ ┌─────┐   │ │ │  │
│  │  │                     │  │  │  │EC2  │ │EC2  │   │ │ │  │
│  │  │                     │  │  │  │Pod  │ │Pod  │   │ │ │  │
│  │  │                     │  │  │  └─────┘ └─────┘   │ │ │  │
│  │  │                     │  │  └─────────────────────┘ │ │  │
│  │  │                     │  │                           │ │  │
│  │  │                     │  │  ┌─────────────────────┐ │ │  │
│  │  │                     │  │  │  Fargate Profile    │ │ │  │
│  │  │                     │  │  │  ┌─────┐ ┌─────┐   │ │ │  │
│  │  │                     │  │  │  │Pod  │ │Pod  │   │ │ │  │
│  │  │                     │  │  │  │(无EC2)│(无EC2)│   │ │ │  │
│  │  │                     │  │  │  └─────┘ └─────┘   │ │ │  │
│  │  │                     │  │  └─────────────────────┘ │ │  │
│  │  │                     │  │                           │ │  │
│  │  │                     │  │  ┌─────────────────────┐ │ │  │
│  │  │                     │  │  │   Database Subnets  │ │ │  │
│  │  │                     │  │  │   ┌─────┐ ┌─────┐  │ │ │  │
│  │  │                     │  │  │   │ RDS │ │Redis│  │ │ │  │
│  │  │                     │  │  │   └─────┘ └─────┘  │ │ │  │
│  │  │                     │  │  └─────────────────────┘ │ │  │
│  │  └─────────────────────┘  └─────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐ │
│  │  IRSA     │  │  Add-ons  │  │  EBS CSI   │  │  VPC CNI  │ │
│  │  Pod IAM  │  │  CoreDNS  │  │  Driver    │  │  Plugin   │ │
│  │  Roles    │  │  kube-proxy│  │           │  │           │ │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### 2. EKS 集群 Terraform 模块

#### 2.1 使用官方 EKS 模块

```hcl
# modules/eks/variables.tf

variable "cluster_name" {
  description = "EKS 集群名称"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]*$", var.cluster_name))
    error_message = "集群名称必须以字母开头，只能包含字母、数字和连字符。"
  }
}

variable "cluster_version" {
  description = "Kubernetes 版本"
  type        = string
  default     = "1.29"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "私有子网 ID 列表（节点部署位置）"
  type        = list(string)
}

variable "control_plane_subnet_ids" {
  description = "控制平面子网 ID 列表（可选，默认使用 private_subnet_ids）"
  type        = list(string)
  default     = []
}

# ── 节点组配置 ──
variable "node_groups" {
  description = "托管节点组配置"
  type = map(object({
    instance_types = list(string)
    capacity_type  = string     # ON_DEMAND 或 SPOT
    min_size       = number
    max_size       = number
    desired_size   = number
    disk_size      = number
    labels         = map(string)
    taints = list(object({
      key    = string
      value  = string
      effect = string
    }))
  }))
  default = {
    general = {
      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
      min_size       = 2
      max_size       = 10
      desired_size   = 3
      disk_size      = 50
      labels         = { role = "general" }
      taints         = []
    }
  }
}

# ── Fargate 配置 ──
variable "fargate_profiles" {
  description = "Fargate Profile 配置"
  type = map(object({
    namespace = string
    labels    = map(string)
  }))
  default = {}
}

# ── IRSA 配置 ──
variable "enable_irsa" {
  description = "是否启用 IRSA"
  type        = bool
  default     = true
}

# ── Add-ons 配置 ──
variable "cluster_addons" {
  description = "EKS Add-ons 配置"
  type = map(object({
    most_recent              = bool
    service_account_role_arn = string
  }))
  default = {
    coredns = {
      most_recent              = true
      service_account_role_arn = null
    }
    kube-proxy = {
      most_recent              = true
      service_account_role_arn = null
    }
    vpc-cni = {
      most_recent              = true
      service_account_role_arn = null
    }
    aws-ebs-csi-driver = {
      most_recent              = true
      service_account_role_arn = null
    }
  }
}

# ── 标签 ──
variable "tags" {
  description = "资源标签"
  type        = map(string)
  default     = {}
}
```

#### 2.2 EKS 集群主配置

```hcl
# modules/eks/main.tf

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = ">= 4.0"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

locals {
  cluster_subnet_ids = length(var.control_plane_subnet_ids) > 0 ? var.control_plane_subnet_ids : var.private_subnet_ids

  tags = merge(var.tags, {
    Module    = "eks"
    ManagedBy = "terraform"
  })
}

# ═══════════════════════════════════════════════════════════
# EKS 集群 IAM 角色
# ═══════════════════════════════════════════════════════════

resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role_policy_attachment" "cluster_vpc_controller" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.cluster.name
}

# ═══════════════════════════════════════════════════════════
# EKS 集群安全组
# ═══════════════════════════════════════════════════════════

resource "aws_security_group" "cluster" {
  name_prefix = "${var.cluster_name}-cluster-"
  description = "EKS cluster security group"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow worker nodes to communicate with control plane"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${var.cluster_name}-cluster-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ═══════════════════════════════════════════════════════════
# EKS 集群
# ═══════════════════════════════════════════════════════════

resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  version  = var.cluster_version
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids              = local.cluster_subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true  # 生产环境建议设为 false
    security_group_ids      = [aws_security_group.cluster.id]
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler",
  ]

  # 加密配置（可选）
  # encryption_config {
  #   resources = ["secrets"]
  #   provider {
  #     key_arn = aws_kms_key.eks.arn
  #   }
  # }

  tags = local.tags

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy,
    aws_iam_role_policy_attachment.cluster_vpc_controller,
  ]
}

# ═══════════════════════════════════════════════════════════
# OIDC Provider（IRSA 需要）
# ═══════════════════════════════════════════════════════════

data "tls_certificate" "cluster" {
  count = var.enable_irsa ? 1 : 0
  url   = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "cluster" {
  count = var.enable_irsa ? 1 : 0

  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.cluster[0].certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.this.identity[0].oidc[0].issuer

  tags = local.tags
}

# ═══════════════════════════════════════════════════════════
# 节点组 IAM 角色
# ═══════════════════════════════════════════════════════════

resource "aws_iam_role" "node_group" {
  name = "${var.cluster_name}-node-group-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "node_group_worker" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_cni" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_ecr" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_ssm" {
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.node_group.name
}

# ═══════════════════════════════════════════════════════════
# 托管节点组
# ═══════════════════════════════════════════════════════════

resource "aws_eks_node_group" "this" {
  for_each = var.node_groups

  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-${each.key}"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = var.private_subnet_ids

  instance_types = each.value.instance_types
  capacity_type  = each.value.capacity_type
  disk_size      = each.value.disk_size

  scaling_config {
    min_size     = each.value.min_size
    max_size     = each.value.max_size
    desired_size = each.value.desired_size
  }

  update_config {
    max_unavailable_percentage = 33
  }

  labels = each.value.labels

  dynamic "taint" {
    for_each = each.value.taints
    content {
      key    = taint.value.key
      value  = taint.value.value
      effect = taint.value.effect
    }
  }

  tags = merge(local.tags, {
    Name     = "${var.cluster_name}-${each.key}"
    NodeRole = each.key
  })

  depends_on = [
    aws_iam_role_policy_attachment.node_group_worker,
    aws_iam_role_policy_attachment.node_group_cni,
    aws_iam_role_policy_attachment.node_group_ecr,
    aws_iam_role_policy_attachment.node_group_ssm,
  ]

  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

# ═══════════════════════════════════════════════════════════
# Fargate Profile
# ═══════════════════════════════════════════════════════════

resource "aws_iam_role" "fargate" {
  count = length(var.fargate_profiles) > 0 ? 1 : 0
  name  = "${var.cluster_name}-fargate-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks-fargate-pods.amazonaws.com"
      }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "fargate_policy" {
  count      = length(var.fargate_profiles) > 0 ? 1 : 0
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy"
  role       = aws_iam_role.fargate[0].name
}

resource "aws_eks_fargate_profile" "this" {
  for_each = var.fargate_profiles

  cluster_name           = aws_eks_cluster.this.name
  fargate_profile_name   = "${var.cluster_name}-${each.key}"
  pod_execution_role_arn = aws_iam_role.fargate[0].arn
  subnet_ids             = var.private_subnet_ids

  selector {
    namespace = each.value.namespace
    labels    = each.value.labels
  }

  tags = merge(local.tags, {
    Name = "${var.cluster_name}-${each.key}"
  })

  depends_on = [
    aws_iam_role_policy_attachment.fargate_policy,
  ]
}

# ═══════════════════════════════════════════════════════════
# EKS Add-ons
# ═══════════════════════════════════════════════════════════

resource "aws_eks_addon" "this" {
  for_each = var.cluster_addons

  cluster_name                = aws_eks_cluster.this.name
  addon_name                  = each.key
  most_recent                 = each.value.most_recent
  service_account_role_arn    = each.value.service_account_role_arn
  resolve_conflicts_on_create = "OVERWRITE"
  resolve_conflicts_on_update = "OVERWRITE"

  tags = local.tags

  depends_on = [
    aws_eks_node_group.this,
  ]
}
```

#### 2.3 EKS 模块输出

```hcl
# modules/eks/outputs.tf

output "cluster_name" {
  description = "EKS 集群名称"
  value       = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  description = "EKS 集群 API 端点"
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_version" {
  description = "EKS 集群版本"
  value       = aws_eks_cluster.this.version
}

output "cluster_arn" {
  description = "EKS 集群 ARN"
  value       = aws_eks_cluster.this.arn
}

output "cluster_certificate_authority" {
  description = "集群 CA 证书（Base64）"
  value       = aws_eks_cluster.this.certificate_authority[0].data
}

output "cluster_security_group_id" {
  description = "集群安全组 ID"
  value       = aws_security_group.cluster.id
}

output "oidc_provider_arn" {
  description = "OIDC Provider ARN（IRSA 用）"
  value       = try(aws_iam_openid_connect_provider.cluster[0].arn, null)
}

output "oidc_provider_url" {
  description = "OIDC Provider URL（IRSA 用）"
  value       = try(aws_iam_openid_connect_provider.cluster[0].url, null)
}

output "oidc_provider_id" {
  description = "OIDC Provider ID（去掉 https:// 前缀）"
  value       = try(replace(aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", ""), null)
}

output "node_group_role_arn" {
  description = "节点组 IAM 角色 ARN"
  value       = aws_iam_role.node_group.arn
}

output "node_group_role_name" {
  description = "节点组 IAM 角色名称"
  value       = aws_iam_role.node_group.name
}
```

### 3. IRSA（IAM Roles for Service Accounts）

#### 3.1 IRSA 原理

```
┌─────────────────────────────────────────────────────────┐
│                    IRSA 工作原理                          │
│                                                         │
│  1. EKS 集群配置 OIDC Provider                          │
│     ┌─────────────────────────────────────────┐         │
│     │  OIDC Issuer:                           │         │
│     │  https://oidc.eks.us-east-1.amazonaws.com│        │
│     │  /id/XXXXXX                             │         │
│     └─────────────────────────────────────────┘         │
│                                                         │
│  2. Kubernetes Service Account 关联 IAM Role            │
│     ┌─────────────────────────────────────────┐         │
│     │  apiVersion: v1                         │         │
│     │  kind: ServiceAccount                   │         │
│     │  metadata:                              │         │
│     │    name: my-app                         │         │
│     │    annotations:                         │         │
│     │      eks.amazonaws.com/role-arn:        │         │
│     │        arn:aws:iam::123:role/my-app     │         │
│     └─────────────────────────────────────────┘         │
│                                                         │
│  3. Pod 请求 STS 临时凭证                               │
│     ┌─────────────────────────────────────────┐         │
│     │  Pod → ServiceAccount → Token           │         │
│     │  → STS AssumeRoleWithWebIdentity        │         │
│     │  → IAM Role → AWS API                   │         │
│     └─────────────────────────────────────────┘         │
│                                                         │
│  优势：                                                  │
│  - 每个 Pod 独立的 IAM 角色                              │
│  - 无需在节点上配置长期凭证                              │
│  - 最小权限原则                                          │
│  - 可审计（CloudTrail 记录每次调用）                     │
└─────────────────────────────────────────────────────────┘
```

#### 3.2 IRSA 模块

```hcl
# modules/irsa/main.tf

variable "cluster_name" {
  description = "EKS 集群名称"
  type        = string
}

variable "cluster_oidc_provider_arn" {
  description = "OIDC Provider ARN"
  type        = string
}

variable "cluster_oidc_provider_id" {
  description = "OIDC Provider ID（去掉 https:// 前缀）"
  type        = string
}

variable "namespace" {
  description = "Kubernetes 命名空间"
  type        = string
  default     = "default"
}

variable "service_account_name" {
  description = "Kubernetes Service Account 名称"
  type        = string
}

variable "role_name" {
  description = "IAM Role 名称"
  type        = string
}

variable "policy_arns" {
  description = "附加的 IAM 策略 ARN 列表"
  type        = list(string)
  default     = []
}

variable "inline_policies" {
  description = "内联策略（name -> policy_json）"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "资源标签"
  type        = map(string)
  default     = {}
}

# ── IAM Role ──
resource "aws_iam_role" "this" {
  name = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = var.cluster_oidc_provider_arn
      }
      Condition = {
        StringEquals = {
          "${var.cluster_oidc_provider_id}:aud" = "sts.amazonaws.com"
          "${var.cluster_oidc_provider_id}:sub" = "system:serviceaccount:${var.namespace}:${var.service_account_name}"
        }
      }
    }]
  })

  tags = var.tags
}

# ── 附加策略 ──
resource "aws_iam_role_policy_attachment" "this" {
  for_each = toset(var.policy_arns)

  role       = aws_iam_role.this.name
  policy_arn = each.value
}

# ── 内联策略 ──
resource "aws_iam_role_policy" "this" {
  for_each = var.inline_policies

  name   = each.key
  role   = aws_iam_role.this.id
  policy = each.value
}

output "role_arn" {
  description = "IAM Role ARN（用于 ServiceAccount 注解）"
  value       = aws_iam_role.this.arn
}

output "role_name" {
  description = "IAM Role 名称"
  value       = aws_iam_role.this.name
}
```

#### 3.3 使用 IRSA 模块

```hcl
# ── 为 AWS Load Balancer Controller 创建 IRSA ──
module "irsa_lb_controller" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "kube-system"
  service_account_name       = "aws-load-balancer-controller"
  role_name                  = "${var.cluster_name}-lb-controller"

  policy_arns = [
    aws_iam_policy.lb_controller.arn,
  ]

  tags = local.tags
}

resource "aws_iam_policy" "lb_controller" {
  name        = "${var.cluster_name}-lb-controller"
  description = "IAM policy for AWS Load Balancer Controller"
  policy      = file("${path.module}/policies/lb-controller-policy.json")
}

# ── 为 Cluster Autoscaler 创建 IRSA ──
module "irsa_cluster_autoscaler" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "kube-system"
  service_account_name       = "cluster-autoscaler"
  role_name                  = "${var.cluster_name}-cluster-autoscaler"

  inline_policies = {
    cluster-autoscaler = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = [
            "autoscaling:DescribeAutoScalingGroups",
            "autoscaling:DescribeAutoScalingInstances",
            "autoscaling:DescribeLaunchConfigurations",
            "autoscaling:DescribeScalingActivities",
            "autoscaling:DescribeTags",
            "ec2:DescribeInstanceTypes",
            "ec2:DescribeLaunchTemplateVersions",
          ]
          Effect   = "Allow"
          Resource = "*"
        },
        {
          Action = [
            "autoscaling:SetDesiredCapacity",
            "autoscaling:TerminateInstanceInAutoScalingGroup",
            "ec2:DescribeImages",
            "ec2:GetInstanceTypesFromInstanceRequirements",
            "eks:DescribeNodegroup",
          ]
          Effect   = "Allow"
          Resource = "*"
        },
      ]
    })
  }

  tags = local.tags
}

# ── 为 External Secrets 创建 IRSA ──
module "irsa_external_secrets" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "external-secrets"
  service_account_name       = "external-secrets"
  role_name                  = "${var.cluster_name}-external-secrets"

  inline_policies = {
    secrets-manager = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret",
            "secretsmanager:ListSecretVersionIds",
          ]
          Effect   = "Allow"
          Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:*"
        },
        {
          Action = [
            "ssm:GetParameter",
            "ssm:GetParameters",
            "ssm:GetParametersByPath",
          ]
          Effect   = "Allow"
          Resource = "arn:aws:ssm:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:parameter/*"
        },
      ]
    })
  }

  tags = local.tags
}
```

### 4. EKS Add-ons 管理

#### 4.1 Add-on 配置

```hcl
# ── 常用 Add-ons ──
variable "cluster_addons" {
  default = {
    coredns = {
      most_recent              = true
      service_account_role_arn = null
    }
    kube-proxy = {
      most_recent              = true
      service_account_role_arn = null
    }
    vpc-cni = {
      most_recent              = true
      service_account_role_arn = null
    }
    aws-ebs-csi-driver = {
      most_recent              = true
      service_account_role_arn = null  # 可配置 IRSA
    }
  }
}

# ── VPC CNI 配置 ──
# 使用 PREFIX_DELEGATION 扩展 IP 空间
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = module.eks.cluster_name
  addon_name                  = "vpc-cni"
  most_recent                 = true
  resolve_conflicts_on_update = "OVERWRITE"

  configuration_values = jsonencode({
    env = {
      ENABLE_PREFIX_DELEGATION = "true"
      WARM_PREFIX_TARGET       = "1"
    }
  })
}

# ── CoreDNS 配置 ──
resource "aws_eks_addon" "coredns" {
  cluster_name                = module.eks.cluster_name
  addon_name                  = "coredns"
  most_recent                 = true
  resolve_conflicts_on_update = "OVERWRITE"

  configuration_values = jsonencode({
    computeType = "Fargate"
  })

  depends_on = [aws_eks_fargate_profile.kube_system]
}
```

### 5. 完整 EKS 部署示例

#### 5.1 生产环境完整配置

```hcl
# environments/prod/eks.tf

# ── EKS 集群 ──
module "eks" {
  source = "../../modules/eks"

  cluster_name    = "production"
  cluster_version = "1.29"

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  node_groups = {
    # 通用工作负载
    general = {
      instance_types = ["m6i.xlarge", "m6i.2xlarge"]
      capacity_type  = "ON_DEMAND"
      min_size       = 3
      max_size       = 20
      desired_size   = 5
      disk_size      = 100
      labels = {
        role     = "general"
        workload = "web"
      }
      taints = []
    }

    # 内存优化型工作负载
    memory = {
      instance_types = ["r6i.xlarge"]
      capacity_type  = "ON_DEMAND"
      min_size       = 0
      max_size       = 10
      desired_size   = 2
      disk_size      = 100
      labels = {
        role     = "memory-optimized"
        workload = "cache"
      }
      taints = [{
        key    = "workload"
        value  = "cache"
        effect = "NO_SCHEDULE"
      }]
    }

    # Spot 实例（容错工作负载）
    spot = {
      instance_types = ["m6i.xlarge", "m5.xlarge", "m5a.xlarge"]
      capacity_type  = "SPOT"
      min_size       = 0
      max_size       = 20
      desired_size   = 3
      disk_size      = 100
      labels = {
        role     = "spot"
        workload = "batch"
      }
      taints = [{
        key    = "spot"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  cluster_addons = {
    coredns = {
      most_recent              = true
      service_account_role_arn = null
    }
    kube-proxy = {
      most_recent              = true
      service_account_role_arn = null
    }
    vpc-cni = {
      most_recent              = true
      service_account_role_arn = module.irsa_vpc_cni.role_arn
    }
    aws-ebs-csi-driver = {
      most_recent              = true
      service_account_role_arn = module.irsa_ebs_csi.role_arn
    }
  }

  enable_irsa = true

  tags = {
    Environment = "prod"
    Team        = "platform"
  }
}

# ── IRSA for VPC CNI ──
module "irsa_vpc_cni" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "kube-system"
  service_account_name       = "aws-node"
  role_name                  = "prod-vpc-cni"

  policy_arns = [
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
  ]
}

# ── IRSA for EBS CSI Driver ──
module "irsa_ebs_csi" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "kube-system"
  service_account_name       = "ebs-csi-controller-sa"
  role_name                  = "prod-ebs-csi"

  policy_arns = [
    "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy",
  ]
}

# ── IRSA for AWS Load Balancer Controller ──
module "irsa_lb_controller" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "kube-system"
  service_account_name       = "aws-load-balancer-controller"
  role_name                  = "prod-lb-controller"

  policy_arns = [
    aws_iam_policy.lb_controller.arn,
  ]
}

# ── IRSA for Cluster Autoscaler ──
module "irsa_cluster_autoscaler" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "kube-system"
  service_account_name       = "cluster-autoscaler"
  role_name                  = "prod-cluster-autoscaler"

  inline_policies = {
    autoscaler = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = [
            "autoscaling:DescribeAutoScalingGroups",
            "autoscaling:DescribeAutoScalingInstances",
            "autoscaling:DescribeLaunchConfigurations",
            "autoscaling:DescribeTags",
            "ec2:DescribeInstanceTypes",
            "ec2:DescribeLaunchTemplateVersions",
            "eks:DescribeNodegroup",
          ]
          Effect   = "Allow"
          Resource = "*"
        },
        {
          Action = [
            "autoscaling:SetDesiredCapacity",
            "autoscaling:TerminateInstanceInAutoScalingGroup",
          ]
          Effect   = "Allow"
          Resource = "*"
          Condition = {
            StringEquals = {
              "autoscaling:ResourceTag/k8s.io/cluster-autoscaler/enabled" = "true"
            }
          }
        },
      ]
    })
  }
}

# ── IRSA for External Secrets ──
module "irsa_external_secrets" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "external-secrets"
  service_account_name       = "external-secrets"
  role_name                  = "prod-external-secrets"

  inline_policies = {
    secrets = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret",
          ]
          Effect   = "Allow"
          Resource = "arn:aws:secretsmanager:us-east-1:*:secret:prod/*"
        },
        {
          Action = [
            "ssm:GetParameter",
            "ssm:GetParameters",
            "ssm:GetParametersByPath",
          ]
          Effect   = "Allow"
          Resource = "arn:aws:ssm:us-east-1:*:parameter/prod/*"
        },
      ]
    })
  }
}

# ── Helm Charts（Kubernetes 资源）──
provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# AWS Load Balancer Controller（通过 Helm 安装）
resource "helm_release" "lb_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  version    = "1.7.2"
  namespace  = "kube-system"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.create"
    value = "true"
  }

  set {
    name  = "serviceAccount.name"
    value = "aws-load-balancer-controller"
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.irsa_lb_controller.role_arn
  }

  depends_on = [module.eks]
}

# Cluster Autoscaler（通过 Helm 安装）
resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  version    = "9.37.0"
  namespace  = "kube-system"

  set {
    name  = "autoDiscovery.clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "awsRegion"
    value = "us-east-1"
  }

  set {
    name  = "rbac.serviceAccount.create"
    value = "true"
  }

  set {
    name  = "rbac.serviceAccount.name"
    value = "cluster-autoscaler"
  }

  set {
    name  = "rbac.serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.irsa_cluster_autoscaler.role_arn
  }

  depends_on = [module.eks]
}

# Metrics Server（通过 Helm 安装）
resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  version    = "3.12.1"
  namespace  = "kube-system"

  depends_on = [module.eks]
}
```

#### 5.2 kubectl 配置

```bash
# 配置 kubectl 连接 EKS 集群
aws eks update-kubeconfig --name production --region us-east-1

# 验证集群连接
kubectl get nodes
kubectl get pods -A
kubectl cluster-info
```

---

## 💻 实战练习

### 练习 1：部署最小 EKS 集群

**目标：** 使用 Terraform 部署一个最小可用的 EKS 集群

```hcl
# minimal-eks/main.tf
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "minimal-eks"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "minimal-eks"
  cluster_version = "1.29"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    default = {
      instance_types = ["t3.medium"]
      min_size       = 1
      max_size       = 3
      desired_size   = 2
    }
  }
}
```

### 练习 2：配置 IRSA

**目标：** 为应用配置 IRSA，允许 Pod 访问 S3

```hcl
# 1. 创建 IRSA
module "irsa_s3_reader" {
  source = "./modules/irsa"

  cluster_name               = module.eks.cluster_name
  cluster_oidc_provider_arn  = module.eks.oidc_provider_arn
  cluster_oidc_provider_id   = module.eks.oidc_provider_id
  namespace                  = "default"
  service_account_name       = "s3-reader"
  role_name                  = "eks-s3-reader"

  inline_policies = {
    s3-read = jsonencode({
      Version = "2012-10-17"
      Statement = [{
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Effect   = "Allow"
        Resource = ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"]
      }]
    })
  }
}

# 2. 验证（在 Kubernetes 中）
# kubectl create serviceaccount s3-reader
# kubectl annotate serviceaccount s3-reader eks.amazonaws.com/role-arn=arn:aws:iam::123:role/eks-s3-reader
```

### 练习 3：完整 EKS 部署

**目标：** 部署包含 VPC、EKS、IRSA、Helm Charts 的完整环境

```bash
# 1. 创建所有 Terraform 文件
# 2. 初始化
terraform init

# 3. 计划
terraform plan -out=tfplan

# 4. 应用（EKS 创建需要 15-20 分钟）
terraform apply tfplan

# 5. 配置 kubectl
aws eks update-kubeconfig --name production --region us-east-1

# 6. 验证
kubectl get nodes
kubectl get pods -A
kubectl get serviceaccounts -A

# 7. 测试 IRSA
kubectl run test-pod --image=amazon/aws-cli --rm -it \
  --overrides='{"spec":{"serviceAccountName":"s3-reader"}}' \
  -- aws s3 ls s3://my-bucket
```

---

## 🎯 面试题精选

### 1. EKS 控制平面和数据平面的职责分别是什么？

**参考答案：**
- **控制平面（AWS 托管）**：API Server、etcd、Scheduler、Controller Manager，由 AWS 管理和升级
- **数据平面（用户管理）**：Worker Node、kubelet、kube-proxy、容器运行时
- AWS 负责控制平面的可用性和安全性，用户负责节点配置、Pod 调度和应用部署

### 2. IRSA 是什么？为什么需要它？

**参考答案：**
IRSA（IAM Roles for Service Accounts）允许 Kubernetes Pod 使用 AWS IAM 角色。它通过 OIDC Provider 实现：
- 每个 ServiceAccount 可以关联一个 IAM Role
- Pod 通过 Web Identity Token 获取 AWS 临时凭证
- 替代了在节点上配置长期凭证的方式
- 实现了 Pod 级别的最小权限原则

### 3. Managed Node Group 和 Fargate 的区别是什么？

**参考答案：**
| 维度 | Managed Node Group | Fargate |
|------|-------------------|---------|
| 计算资源 | EC2 实例 | 无服务器 |
| 控制粒度 | 可自定义实例类型、AMI | 不可自定义 |
| 成本模式 | 按实例计费 | 按 Pod 资源计费 |
| 适用场景 | 长期运行、稳定负载 | 突发、间歇性负载 |
| 启动速度 | 分钟级 | 秒级 |
| GPU 支持 | 支持 | 不支持 |
| DaemonSet | 支持 | 不支持 |

### 4. 如何为 EKS 节点选择合适的实例类型？

**参考答案：**
- **通用型**（m 系列）：Web 服务器、API 服务
- **计算优化型**（c 系列）：CI/CD、批处理
- **内存优化型**（r 系列）：缓存、数据库
- **GPU 型**（p/g 系列）：机器学习、推理
- 使用混合实例类型 + Spot 实例降低成本
- 考虑 Graviton（ARM）实例获得更好性价比

### 5. EKS Add-ons 的作用是什么？

**参考答案：**
EKS Add-ons 是 AWS 管理的集群组件：
- **CoreDNS**：集群内 DNS 解析
- **kube-proxy**：网络代理和负载均衡
- **VPC CNI**：Pod 网络（每个 Pod 一个 VPC IP）
- **EBS CSI Driver**：持久化存储

优势：AWS 管理版本升级、安全补丁，与 EKS 版本兼容性有保证。

### 6. 如何实现 EKS 集群的高可用？

**参考答案：**
1. **多 AZ 部署**：节点分布在 3 个 AZ
2. **托管节点组**：Auto Scaling 自动修复
3. **Pod 反亲和性**：Pod 分散到不同节点
4. **PodDisruptionBudget**：确保滚动更新时有足够可用 Pod
5. **控制平面**：AWS 自动管理多 AZ 高可用
6. **Cluster Autoscaler**：根据负载自动扩缩节点

### 7. VPC CNI 的 PREFIX_DELEGATION 模式是什么？

**参考答案：**
PREFIX_DELEGATION 允许每个 ENI 分配一个 /28 前缀（16 个 IP），而非单个 IP。这大幅增加了每个节点可用的 Pod IP 数量：
- 默认模式：每个 ENI 的 IP 数 = 实例支持的 ENI 数 * 每个 ENI 的 IP 数
- PREFIX_DELEGATION：每个 ENI 的 IP 数 * 16
- 适用于需要大量 IP 的场景（如大规模集群或 IPv4 地址紧张）

### 8. 如何安全地管理 EKS 集群的访问权限？

**参考答案：**
1. **aws-auth ConfigMap**：映射 IAM 角色到 Kubernetes RBAC
2. **IRSA**：Pod 级别的 AWS 权限
3. **Kubernetes RBAC**：命名空间级别的权限控制
4. **Private Endpoint**：禁用公网访问，仅通过 VPC 内部访问
5. **审计日志**：启用 EKS 控制平面日志
6. **OPA/Gatekeeper**：策略执行

---

## 📚 深入阅读

- [AWS EKS 文档](https://docs.aws.amazon.com/eks/latest/userguide/)
- [terraform-aws-modules/eks](https://github.com/terraform-aws-modules/terraform-aws-eks)
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [IRSA 文档](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EKS Add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [VPC CNI Plugin](https://github.com/aws/amazon-vpc-cni-k8s)

---

## ✅ 自检清单

- [ ] 理解 EKS 架构（控制平面、数据平面、网络）
- [ ] 能使用 Terraform 部署完整的 EKS 集群
- [ ] 掌握托管节点组的配置（实例类型、扩缩容、标签、Taint）
- [ ] 理解 IRSA 的原理和配置方法
- [ ] 能为不同组件配置 IRSA（LB Controller、Autoscaler、External Secrets）
- [ ] 掌握 EKS Add-ons 的管理方式
- [ ] 理解 VPC CNI 的 PREFIX_DELEGATION 模式
- [ ] 能通过 Helm 安装 Kubernetes 组件
- [ ] 掌握 kubectl 配置和集群验证
- [ ] 理解 Managed Node Group 和 Fargate 的区别和适用场景
- [ ] 掌握 EKS 集群的安全最佳实践
- [ ] 能完成从 VPC 到 EKS 的端到端部署
