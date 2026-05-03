# Day 181: Terraform 创建 VPC + EKS — 完整基础设施代码

> 📅 日期：2026-05-04
> 📖 学习主题：Terraform 模块化设计、VPC 网络架构、EKS 集群部署、多环境配置、远程状态管理
> ⏰ 预计学习时间：6-8 小时
> 📋 前置知识：Day 120-129 (Terraform), Day 105-119 (AWS), Day 180 (项目规划)

---

## 🎯 学习目标

完成 Day 181 的学习后，你应该能够：

1. 编写模块化的 Terraform 代码
2. 设计生产级 VPC 网络架构
3. 部署 EKS 集群及节点组
4. 配置多环境 (dev/staging/prod) 隔离
5. 管理 Terraform 远程状态
6. 理解基础设施安全最佳实践

---

## 📖 核心知识点

### 1. 项目结构概览

```
infrastructure/terraform/
├── modules/                    # 可复用模块
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── eks/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── rds/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── elasticache/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/               # 环境配置
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── staging/
│   │   └── ...
│   └── prod/
│       └── ...
└── versions.tf                 # Provider 版本约束
```

### 2. VPC 模块

#### 2.1 variables.tf

```hcl
# infrastructure/terraform/modules/vpc/variables.tf

variable "project_name" {
  description = "项目名称，用于资源命名"
  type        = string
}

variable "environment" {
  description = "环境名称: dev, staging, prod"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR 地址段"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "可用区列表"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnet_cidrs" {
  description = "私有子网 CIDR 列表"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
}

variable "public_subnet_cidrs" {
  description = "公有子网 CIDR 列表"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "database_subnet_cidrs" {
  description = "数据库子网 CIDR 列表"
  type        = list(string)
  default     = ["10.0.20.0/24", "10.0.21.0/24", "10.0.22.0/24"]
}

variable "enable_nat_gateway" {
  description = "是否启用 NAT Gateway"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "是否使用单个 NAT Gateway (节省成本)"
  type        = bool
  default     = false
}

variable "enable_vpn_gateway" {
  description = "是否启用 VPN Gateway"
  type        = bool
  default     = false
}

variable "enable_flow_logs" {
  description = "是否启用 VPC Flow Logs"
  type        = bool
  default     = true
}

variable "tags" {
  description = "通用标签"
  type        = map(string)
  default     = {}
}
```

#### 2.2 main.tf

```hcl
# infrastructure/terraform/modules/vpc/main.tf

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ============================================================
# VPC
# ============================================================
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

# ============================================================
# Internet Gateway
# ============================================================
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-igw"
  })
}

# ============================================================
# 公有子网
# ============================================================
resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name                                           = "${local.name_prefix}-public-${var.availability_zones[count.index]}"
    "kubernetes.io/role/elb"                       = "1"
    "kubernetes.io/cluster/${local.name_prefix}-eks" = "shared"
  })
}

# ============================================================
# 私有子网
# ============================================================
resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(local.common_tags, {
    Name                                           = "${local.name_prefix}-private-${var.availability_zones[count.index]}"
    "kubernetes.io/role/internal-elb"              = "1"
    "kubernetes.io/cluster/${local.name_prefix}-eks" = "shared"
  })
}

# ============================================================
# 数据库子网
# ============================================================
resource "aws_subnet" "database" {
  count = length(var.database_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.database_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-${var.availability_zones[count.index]}"
  })
}

# ============================================================
# 数据库子网组 (RDS 使用)
# ============================================================
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet-group"
  subnet_ids = aws_subnet.database[*].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })
}

# ============================================================
# Elastic IP (NAT Gateway 使用)
# ============================================================
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.availability_zones)) : 0
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-eip-${count.index}"
  })

  depends_on = [aws_internet_gateway.main]
}

# ============================================================
# NAT Gateway
# ============================================================
resource "aws_nat_gateway" "main" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.availability_zones)) : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-${count.index}"
  })

  depends_on = [aws_internet_gateway.main]
}

# ============================================================
# 公有路由表
# ============================================================
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = length(var.public_subnet_cidrs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ============================================================
# 私有路由表
# ============================================================
resource "aws_route_table" "private" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.availability_zones)) : 1

  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-private-rt-${count.index}"
  })
}

resource "aws_route" "private_nat" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.availability_zones)) : 0

  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[var.single_nat_gateway ? 0 : count.index].id
}

resource "aws_route_table_association" "private" {
  count = length(var.private_subnet_cidrs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[var.single_nat_gateway ? 0 : count.index].id
}

# ============================================================
# 数据库路由表 (使用私有路由表)
# ============================================================
resource "aws_route_table_association" "database" {
  count = length(var.database_subnet_cidrs)

  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.private[var.single_nat_gateway ? 0 : count.index].id
}

# ============================================================
# VPC Flow Logs
# ============================================================
resource "aws_flow_log" "main" {
  count = var.enable_flow_logs ? 1 : 0

  iam_role_arn    = aws_iam_role.flow_log[0].arn
  log_destination = aws_cloudwatch_log_group.flow_log[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-flow-log"
  })
}

resource "aws_cloudwatch_log_group" "flow_log" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/aws/vpc-flow-log/${local.name_prefix}"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_iam_role" "flow_log" {
  count = var.enable_flow_logs ? 1 : 0

  name = "${local.name_prefix}-vpc-flow-log-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "flow_log" {
  count = var.enable_flow_logs ? 1 : 0

  name = "${local.name_prefix}-vpc-flow-log-policy"
  role = aws_iam_role.flow_log[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# ============================================================
# 安全组: ALB
# ============================================================
resource "aws_security_group" "alb" {
  name_prefix = "${local.name_prefix}-alb-"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
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

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}
```

#### 2.3 outputs.tf

```hcl
# infrastructure/terraform/modules/vpc/outputs.tf

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "公有子网 ID 列表"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "私有子网 ID 列表"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "数据库子网 ID 列表"
  value       = aws_subnet.database[*].id
}

output "database_subnet_group_name" {
  description = "数据库子网组名称"
  value       = aws_db_subnet_group.main.name
}

output "nat_gateway_ips" {
  description = "NAT Gateway 公网 IP"
  value       = aws_eip.nat[*].public_ip
}

output "alb_security_group_id" {
  description = "ALB 安全组 ID"
  value       = aws_security_group.alb.id
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.main.id
}

output "private_route_table_ids" {
  description = "私有路由表 ID 列表"
  value       = aws_route_table.private[*].id
}
```

### 3. EKS 模块

#### 3.1 variables.tf

```hcl
# infrastructure/terraform/modules/eks/variables.tf

variable "project_name" {
  description = "项目名称"
  type        = string
}

variable "environment" {
  description = "环境名称"
  type        = string
}

variable "cluster_version" {
  description = "EKS 集群版本"
  type        = string
  default     = "1.29"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "私有子网 ID 列表"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "公有子网 ID 列表"
  type        = list(string)
}

variable "node_instance_types" {
  description = "节点实例类型"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_min_size" {
  description = "节点最小数量"
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "节点最大数量"
  type        = number
  default     = 10
}

variable "node_desired_size" {
  description = "节点期望数量"
  type        = number
  default     = 3
}

variable "node_disk_size" {
  description = "节点磁盘大小 (GB)"
  type        = number
  default     = 50
}

variable "enable_cluster_autoscaler" {
  description = "是否启用 Cluster Autoscaler"
  type        = bool
  default     = true
}

variable "tags" {
  description = "通用标签"
  type        = map(string)
  default     = {}
}
```

#### 3.2 main.tf

```hcl
# infrastructure/terraform/modules/eks/main.tf

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# ============================================================
# EKS Cluster IAM Role
# ============================================================
resource "aws_iam_role" "eks_cluster" {
  name = "${local.name_prefix}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster.name
}

# ============================================================
# EKS Cluster Security Group
# ============================================================
resource "aws_security_group" "eks_cluster" {
  name_prefix = "${local.name_prefix}-eks-cluster-"
  description = "EKS Cluster security group"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow worker nodes to communicate with cluster API"
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

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-eks-cluster-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ============================================================
# EKS Cluster
# ============================================================
resource "aws_eks_cluster" "main" {
  name     = "${local.name_prefix}-eks"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.cluster_version

  vpc_config {
    subnet_ids              = concat(var.private_subnet_ids, var.public_subnet_ids)
    security_group_ids      = [aws_security_group.eks_cluster.id]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  enabled_cluster_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  tags = local.common_tags

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]
}

# ============================================================
# EKS Node Group IAM Role
# ============================================================
resource "aws_iam_role" "eks_nodes" {
  name = "${local.name_prefix}-eks-node-role"

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

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_ssm_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
  role       = aws_iam_role.eks_nodes.name
}

# ============================================================
# EKS Node Group
# ============================================================
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name_prefix}-node-group"
  node_role_arn   = aws_iam_role.eks_nodes.arn
  subnet_ids      = var.private_subnet_ids

  instance_types = var.node_instance_types
  disk_size      = var.node_disk_size
  capacity_type  = "ON_DEMAND"

  scaling_config {
    min_size     = var.node_min_size
    max_size     = var.node_max_size
    desired_size = var.node_desired_size
  }

  update_config {
    max_unavailable = 1
  }

  labels = {
    Environment = var.environment
    NodeGroup   = "main"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-node-group"
  })

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry,
    aws_iam_role_policy_attachment.eks_ssm_policy,
  ]

  lifecycle {
    ignore_changes = [scaling_config[0].desired_size]
  }
}

# ============================================================
# OIDC Provider (用于 IRSA)
# ============================================================
data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = local.common_tags
}

# ============================================================
# Cluster Autoscaler IAM Role (IRSA)
# ============================================================
data "aws_caller_identity" "current" {}

resource "aws_iam_role" "cluster_autoscaler" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  name  = "${local.name_prefix}-cluster-autoscaler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.eks.arn
        }
        Condition = {
          StringEquals = {
            "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:sub" = "system:serviceaccount:kube-system:cluster-autoscaler"
            "${replace(aws_eks_cluster.main.identity[0].oidc[0].issuer, "https://", "")}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "cluster_autoscaler" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  name  = "${local.name_prefix}-cluster-autoscaler-policy"
  role  = aws_iam_role.cluster_autoscaler[0].id

  policy = jsonencode({
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
      }
    ]
  })
}

# ============================================================
# EKS Addons
# ============================================================
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"

  resolve_conflicts_on_update = "OVERWRITE"
  tags                        = local.common_tags
}

resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "coredns"

  resolve_conflicts_on_update = "OVERWRITE"
  tags                        = local.common_tags

  depends_on = [aws_eks_node_group.main]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "kube-proxy"

  resolve_conflicts_on_update = "OVERWRITE"
  tags                        = local.common_tags
}
```

#### 3.3 outputs.tf

```hcl
# infrastructure/terraform/modules/eks/outputs.tf

output "cluster_name" {
  description = "EKS 集群名称"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "EKS 集群 API 端点"
  value       = aws_eks_cluster.main.endpoint
}

output "cluster_certificate_authority" {
  description = "EKS 集群 CA 证书"
  value       = aws_eks_cluster.main.certificate_authority[0].data
}

output "cluster_arn" {
  description = "EKS 集群 ARN"
  value       = aws_eks_cluster.main.arn
}

output "cluster_security_group_id" {
  description = "EKS 集群安全组 ID"
  value       = aws_security_group.eks_cluster.id
}

output "oidc_provider_arn" {
  description = "OIDC Provider ARN (用于 IRSA)"
  value       = aws_iam_openid_connect_provider.eks.arn
}

output "oidc_provider_url" {
  description = "OIDC Provider URL"
  value       = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

output "node_group_arn" {
  description = "Node Group ARN"
  value       = aws_eks_node_group.main.arn
}

output "node_role_arn" {
  description = "节点 IAM Role ARN"
  value       = aws_iam_role.eks_nodes.arn
}

output "cluster_autoscaler_role_arn" {
  description = "Cluster Autoscaler IAM Role ARN"
  value       = var.enable_cluster_autoscaler ? aws_iam_role.cluster_autoscaler[0].arn : ""
}
```

### 4. 环境配置

#### 4.1 Dev 环境

```hcl
# infrastructure/terraform/environments/dev/main.tf

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

# ============================================================
# VPC
# ============================================================
module "vpc" {
  source = "../../modules/vpc"

  project_name  = var.project_name
  environment   = "dev"
  vpc_cidr      = "10.0.0.0/16"

  availability_zones    = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnet_cidrs   = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs  = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
  database_subnet_cidrs = ["10.0.20.0/24", "10.0.21.0/24", "10.0.22.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true   # Dev 环境使用单个 NAT 节省成本
  enable_flow_logs   = true

  tags = {
    CostCenter = "engineering"
  }
}

# ============================================================
# EKS
# ============================================================
module "eks" {
  source = "../../modules/eks"

  project_name = var.project_name
  environment  = "dev"

  cluster_version      = "1.29"
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  public_subnet_ids    = module.vpc.public_subnet_ids

  node_instance_types = ["t3.medium"]
  node_min_size       = 2
  node_max_size       = 5
  node_desired_size   = 2
  node_disk_size      = 50

  enable_cluster_autoscaler = true

  tags = {
    CostCenter = "engineering"
  }
}

# ============================================================
# RDS PostgreSQL
# ============================================================
module "rds" {
  source = "../../modules/rds"

  project_name = var.project_name
  environment  = "dev"

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.database_subnet_ids
  subnet_group_name  = module.vpc.database_subnet_group_name

  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  max_allocated_storage = 100

  db_name  = "sre_capstone"
  db_user  = "dbadmin"
  db_password = var.db_password

  multi_az            = false  # Dev 不需要多 AZ
  backup_retention    = 7
  deletion_protection = false  # Dev 可以删除

  tags = {
    CostCenter = "engineering"
  }
}

# ============================================================
# ElastiCache Redis
# ============================================================
module "elasticache" {
  source = "../../modules/elasticache"

  project_name = var.project_name
  environment  = "dev"

  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnet_ids

  node_type           = "cache.t3.micro"
  num_cache_nodes     = 1
  engine_version      = "7.0"

  tags = {
    CostCenter = "engineering"
  }
}
```

```hcl
# infrastructure/terraform/environments/dev/variables.tf

variable "aws_region" {
  description = "AWS 区域"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "项目名称"
  type        = string
  default     = "sre-capstone"
}

variable "db_password" {
  description = "数据库密码"
  type        = string
  sensitive   = true
}
```

```hcl
# infrastructure/terraform/environments/dev/terraform.tfvars

aws_region   = "us-east-1"
project_name = "sre-capstone"

# db_password 通过环境变量或 secrets 管理器提供
# export TF_VAR_db_password="your-secure-password"
```

```hcl
# infrastructure/terraform/environments/dev/backend.tf

terraform {
  backend "s3" {
    bucket         = "sre-capstone-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "sre-capstone-terraform-lock"
    encrypt        = true
  }
}
```

#### 4.2 Prod 环境

```hcl
# infrastructure/terraform/environments/prod/main.tf

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

# ============================================================
# VPC (生产环境配置)
# ============================================================
module "vpc" {
  source = "../../modules/vpc"

  project_name  = var.project_name
  environment   = "prod"
  vpc_cidr      = "10.1.0.0/16"

  availability_zones    = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnet_cidrs   = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24"]
  private_subnet_cidrs  = ["10.1.10.0/24", "10.1.11.0/24", "10.1.12.0/24"]
  database_subnet_cidrs = ["10.1.20.0/24", "10.1.21.0/24", "10.1.22.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = false  # 生产环境每个 AZ 一个 NAT
  enable_flow_logs   = true

  tags = {
    CostCenter = "production"
  }
}

# ============================================================
# EKS (生产环境配置)
# ============================================================
module "eks" {
  source = "../../modules/eks"

  project_name = var.project_name
  environment  = "prod"

  cluster_version      = "1.29"
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  public_subnet_ids    = module.vpc.public_subnet_ids

  node_instance_types = ["t3.large", "t3.xlarge"]
  node_min_size       = 3
  node_max_size       = 20
  node_desired_size   = 5
  node_disk_size      = 100

  enable_cluster_autoscaler = true

  tags = {
    CostCenter = "production"
  }
}

# ============================================================
# RDS (生产环境配置)
# ============================================================
module "rds" {
  source = "../../modules/rds"

  project_name = var.project_name
  environment  = "prod"

  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.database_subnet_ids
  subnet_group_name  = module.vpc.database_subnet_group_name

  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.r6g.large"
  allocated_storage    = 100
  max_allocated_storage = 500

  db_name  = "sre_capstone"
  db_user  = "dbadmin"
  db_password = var.db_password

  multi_az            = true   # 生产环境多 AZ
  backup_retention    = 30
  deletion_protection = true   # 生产环境启用删除保护

  tags = {
    CostCenter = "production"
  }
}

# ============================================================
# ElastiCache (生产环境配置)
# ============================================================
module "elasticache" {
  source = "../../modules/elasticache"

  project_name = var.project_name
  environment  = "prod"

  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnet_ids

  node_type           = "cache.r6g.large"
  num_cache_nodes     = 2
  engine_version      = "7.0"

  tags = {
    CostCenter = "production"
  }
}
```

```hcl
# infrastructure/terraform/environments/prod/backend.tf

terraform {
  backend "s3" {
    bucket         = "sre-capstone-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "sre-capstone-terraform-lock"
    encrypt        = true
  }
}
```

### 5. 远程状态管理

```bash
#!/usr/bin/env bash
# scripts/setup-terraform-backend.sh
# 创建 Terraform 远程状态存储

set -euo pipefail

BUCKET_NAME="sre-capstone-terraform-state"
DYNAMODB_TABLE="sre-capstone-terraform-lock"
REGION="us-east-1"

echo "=== 创建 S3 Bucket ==="
aws s3api create-bucket \
  --bucket "${BUCKET_NAME}" \
  --region "${REGION}" \
  --create-bucket-configuration LocationConstraint="${REGION}" 2>/dev/null || true

# 启用版本控制
aws s3api put-bucket-versioning \
  --bucket "${BUCKET_NAME}" \
  --versioning-configuration Status=Enabled

# 启用加密
aws s3api put-bucket-encryption \
  --bucket "${BUCKET_NAME}" \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "aws:kms"
        }
      }
    ]
  }'

# 阻止公开访问
aws s3api put-public-access-block \
  --bucket "${BUCKET_NAME}" \
  --public-access-block-configuration \
    BlockPublicAcls=true,\
    IgnorePublicAcls=true,\
    BlockPublicPolicy=true,\
    RestrictPublicBuckets=true

echo "=== 创建 DynamoDB 表 ==="
aws dynamodb create-table \
  --table-name "${DYNAMODB_TABLE}" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "${REGION}" 2>/dev/null || echo "表已存在"

echo "=== Terraform 远程状态后端创建完成 ==="
echo "S3 Bucket: ${BUCKET_NAME}"
echo "DynamoDB Table: ${DYNAMODB_TABLE}"
echo "Region: ${REGION}"
```

### 6. 部署脚本

```bash
#!/usr/bin/env bash
# scripts/deploy-infra.sh
# 部署基础设施

set -euo pipefail

ENVIRONMENT=${1:-dev}
ACTION=${2:-plan}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TF_DIR="${PROJECT_ROOT}/infrastructure/terraform/environments/${ENVIRONMENT}"

if [[ ! -d "${TF_DIR}" ]]; then
    echo "错误: 环境目录不存在: ${TF_DIR}"
    exit 1
fi

cd "${TF_DIR}"

echo "=== 环境: ${ENVIRONMENT} ==="
echo "=== 操作: ${ACTION} ==="

# 检查必要的环境变量
if [[ -z "${TF_VAR_db_password:-}" ]]; then
    echo "警告: TF_VAR_db_password 未设置"
    echo "请设置: export TF_VAR_db_password='your-secure-password'"
fi

case "${ACTION}" in
    init)
        terraform init -upgrade
        ;;
    plan)
        terraform init -upgrade
        terraform plan -out=tfplan
        ;;
    apply)
        terraform init -upgrade
        if [[ -f tfplan ]]; then
            terraform apply tfplan
        else
            terraform apply
        fi
        ;;
    destroy)
        terraform init -upgrade
        terraform destroy
        ;;
    output)
        terraform output
        ;;
    *)
        echo "用法: $0 <environment> <init|plan|apply|destroy|output>"
        exit 1
        ;;
esac
```

---

## 💻 实战练习

### 练习 1：部署 Dev 环境 VPC

**目标**：使用 Terraform 创建 Dev 环境的 VPC。

**步骤**：

```bash
# 1. 先创建远程状态后端
chmod +x scripts/setup-terraform-backend.sh
./scripts/setup-terraform-backend.sh

# 2. 设置数据库密码
export TF_VAR_db_password="YourSecurePassword123!"

# 3. 初始化 Terraform
cd infrastructure/terraform/environments/dev
terraform init

# 4. 查看执行计划
terraform plan

# 5. 应用 (仅 VPC 部分)
terraform apply -target=module.vpc

# 6. 验证 VPC 创建
aws ec2 describe-vpcs --filters "Name=tag:Project,Values=sre-capstone" \
  --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# 7. 验证子网
aws ec2 describe-subnets --filters "Name=tag:Project,Values=sre-capstone" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

**验证标准**：
- VPC 创建成功，CIDR 为 10.0.0.0/16
- 9 个子网创建成功 (3 公有 + 3 私有 + 3 数据库)
- NAT Gateway 创建成功
- 路由表关联正确

### 练习 2：部署 EKS 集群

**目标**：在 VPC 基础上部署 EKS 集群。

**步骤**：

```bash
# 1. 部署 EKS
cd infrastructure/terraform/environments/dev
terraform apply -target=module.eks

# 2. 配置 kubectl
aws eks update-kubeconfig \
  --name sre-capstone-dev-eks \
  --region us-east-1

# 3. 验证集群
kubectl get nodes
kubectl cluster-info

# 4. 验证组件
kubectl get pods -n kube-system
```

**验证标准**：
- EKS 集群状态为 ACTIVE
- kubectl 可以连接集群
- 节点状态为 Ready
- CoreDNS、kube-proxy、vpc-cni 组件正常

### 练习 3：对比多环境配置差异

**目标**：理解 Dev 和 Prod 环境配置的差异。

**步骤**：

```bash
# 1. 对比 VPC 配置
diff \
  <(cd infrastructure/terraform/environments/dev && terraform plan -target=module.vpc 2>&1) \
  <(cd infrastructure/terraform/environments/prod && terraform plan -target=module.vpc 2>&1)

# 2. 列出关键差异
echo "=== Dev vs Prod 关键差异 ==="
echo "Dev NAT:  single_nat_gateway = true"
echo "Prod NAT: single_nat_gateway = false"
echo ""
echo "Dev EKS Nodes:  t3.medium x2-5"
echo "Prod EKS Nodes: t3.large/xlarge x3-20"
echo ""
echo "Dev RDS:  db.t3.micro, multi_az=false"
echo "Prod RDS: db.r6g.large, multi_az=true"
```

**验证标准**：
- 理解各环境的配置差异
- 能解释每个差异的原因
- 理解成本与可靠性的权衡

---

## 🎯 面试题精选

### 问题 1：Terraform state 为什么需要远程存储？

**参考答案**：

远程状态存储的必要性：
1. **团队协作**：多人需要访问同一状态
2. **安全性**：状态文件可能包含敏感信息
3. **状态锁**：防止并发操作导致状态冲突
4. **版本控制**：S3 版本控制可回滚状态
5. **备份**：远程存储更可靠

最佳实践：S3 + DynamoDB Lock，启用加密和版本控制。

### 问题 2：解释 Terraform 中的 dependency 解析

**参考答案**：

Terraform 通过两种方式解析依赖：
1. **隐式依赖**：通过引用其他资源的输出自动推断
2. **显式依赖**：使用 `depends_on` 手动声明

```
# 隐式依赖 (推荐)
module "eks" {
  vpc_id = module.vpc.vpc_id  # 自动依赖 module.vpc
}

# 显式依赖 (必要时使用)
resource "null_resource" "example" {
  depends_on = [module.eks]
}
```

### 问题 3：为什么 EKS 节点要放在私有子网？

**参考答案**：

安全性考虑：
1. **减少攻击面**：节点不直接暴露在公网
2. **NAT Gateway**：节点通过 NAT 访问外网 (拉取镜像等)
3. **ALB 入口**：流量通过 ALB 转发到私有节点
4. **安全组控制**：精细控制入站和出站流量

### 问题 4：解释 IRSA (IAM Roles for Service Accounts) 的工作原理

**参考答案**：

IRSA 允许 K8s Pod 使用 AWS IAM 角色：

1. EKS 集群启用 OIDC Provider
2. 创建 IAM Role，信任策略指向 OIDC Provider
3. K8s ServiceAccount 注解 `eks.amazonaws.com/role-arn`
4. Pod 使用该 ServiceAccount 时，自动获取临时凭证
5. SDK 自动使用这些凭证访问 AWS 服务

优势：最小权限原则，每个服务独立 IAM 角色。

### 问题 5：Terraform workspace 和环境目录哪种多环境方案更好？

**参考答案**：

| 方案 | Workspace | 环境目录 |
|------|-----------|---------|
| 隔离性 | 弱 (共享代码) | 强 (独立代码) |
| 灵活性 | 低 | 高 |
| 代码重复 | 少 | 多 (可用模块减少) |
| 适用场景 | 简单环境 | 复杂环境 |

本项目选择环境目录方案，因为：
- 不同环境配置差异大
- 需要独立的状态管理
- 安全性要求高
- 使用模块减少代码重复

### 问题 6：如何实现 Terraform 代码的测试？

**参考答案**：

1. **terraform validate**：语法验证
2. **terraform plan**：变更预览
3. **tflint**：最佳实践检查
4. **checkov**：安全合规扫描
5. **terratest**：集成测试 (Go)
6. **Sentinel**：策略即代码

### 问题 7：NAT Gateway 高可用设计

**参考答案**：

```
生产环境: 每个 AZ 一个 NAT Gateway
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  AZ-1a      │  │  AZ-1b      │  │  AZ-1c      │
│  NAT GW-1   │  │  NAT GW-2   │  │  NAT GW-3   │
│  └→ EIP-1   │  │  └→ EIP-2   │  │  └→ EIP-3   │
└─────────────┘  └─────────────┘  └─────────────┘

开发环境: 单个 NAT Gateway (节省成本)
┌─────────────┐
│  AZ-1a      │
│  NAT GW-1   │
│  └→ EIP-1   │
└─────────────┘
```

---

## 📚 深入阅读

### 官方文档
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS EKS Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/)
- [Terraform Module Documentation](https://developer.hashicorp.com/terraform/language/modules)
- [AWS VPC Documentation](https://docs.aws.amazon.com/vpc/latest/userguide/)

### 推荐模块
- [terraform-aws-modules/vpc](https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws)
- [terraform-aws-modules/eks](https://registry.terraform.io/modules/terraform-aws-modules/eks/aws)

---

## ✅ 自检清单

- [ ] 理解 Terraform 模块化设计原则
- [ ] 能解释 VPC 网络架构设计
- [ ] 理解公有/私有/数据库子网的用途
- [ ] 能部署 EKS 集群及节点组
- [ ] 理解 IRSA 的工作原理
- [ ] 能配置多环境隔离
- [ ] 理解远程状态管理的必要性
- [ ] 能执行 terraform plan/apply/destroy
- [ ] 完成 3 个实战练习
- [ ] 能回答相关面试题

---

*由 SRE 学习计划自动生成 | 2026-05-03*
