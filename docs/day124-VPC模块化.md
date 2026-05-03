# Day 124: VPC 模块化

> 📅 日期：2026-05-04
> 📖 学习主题：可复用 VPC 模块、子网/路由/NAT 参数化、多环境支持、最佳实践
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 107（VPC 网络）、Day 120-123（Terraform 全部课程）

---

## 🎯 学习目标

- 设计并开发一个生产级可复用 VPC 模块
- 掌握子网、路由表、NAT Gateway 的参数化设计
- 实现多环境（dev/staging/prod）的差异化配置
- 理解 VPC 设计的最佳实践（CIDR 规划、高可用、安全）
- 掌握 VPC Flow Logs、VPC Endpoint 等高级功能

---

## 📖 核心知识点

### 1. VPC 架构设计

#### 1.1 生产级 VPC 架构

```
┌───────────────────────────────────────────────────────────────┐
│                    生产级 VPC 架构                              │
│                                                               │
│  VPC: 10.0.0.0/16                                             │
│  ┌───────────────────────────────────────────────────────────┐│
│  │                                                           ││
│  │  ┌─── AZ-1a ──────────┐  ┌─── AZ-1b ──────────┐         ││
│  │  │                    │  │                    │         ││
│  │  │  Public Subnet     │  │  Public Subnet     │         ││
│  │  │  10.0.1.0/24       │  │  10.0.2.0/24       │         ││
│  │  │  ┌──────┐ ┌──────┐ │  │  ┌──────┐         │         ││
│  │  │  │ NAT  │ │ ALB  │ │  │  │ NAT  │ ┌──────┐│         ││
│  │  │  │  GW  │ │      │ │  │  │  GW  │ │ ALB  ││         ││
│  │  │  └──────┘ └──────┘ │  │  └──────┘ └──────┘│         ││
│  │  │                    │  │                    │         ││
│  │  │  Private Subnet    │  │  Private Subnet    │         ││
│  │  │  10.0.11.0/24      │  │  10.0.12.0/24      │         ││
│  │  │  ┌──────┐ ┌──────┐ │  │  ┌──────┐ ┌──────┐│         ││
│  │  │  │ EC2  │ │ EC2  │ │  │  │ EC2  │ │ EC2  ││         ││
│  │  │  └──────┘ └──────┘ │  │  └──────┘ └──────┘│         ││
│  │  │                    │  │                    │         ││
│  │  │  Database Subnet   │  │  Database Subnet   │         ││
│  │  │  10.0.21.0/24      │  │  10.0.22.0/24      │         ││
│  │  │  ┌──────┐ ┌──────┐ │  │  ┌──────┐ ┌──────┐│         ││
│  │  │  │ RDS  │ │ RDS  │ │  │  │ RDS  │ │ Redis││         ││
│  │  │  │ 主   │ │ 只读 │ │  │  │ 只读 │ │      ││         ││
│  │  │  └──────┘ └──────┘ │  │  └──────┘ └──────┘│         ││
│  │  └────────────────────┘  └────────────────────┘         ││
│  │                                                           ││
│  │  ┌─── AZ-1c ──────────┐  ┌─────────────────────┐        ││
│  │  │                    │  │  VPC Endpoints       │        ││
│  │  │  Public Subnet     │  │  ┌──────┐ ┌──────┐  │        ││
│  │  │  10.0.3.0/24       │  │  │  S3  │ │ ECR  │  │        ││
│  │  │  ┌──────┐          │  │  │ GW   │ │ IF   │  │        ││
│  │  │  │ ALB  │          │  │  └──────┘ └──────┘  │        ││
│  │  │  └──────┘          │  └─────────────────────┘        ││
│  │  │                    │                                  ││
│  │  │  Private Subnet    │                                  ││
│  │  │  10.0.13.0/24      │                                  ││
│  │  │  ┌──────┐          │                                  ││
│  │  │  │ EC2  │          │                                  ││
│  │  │  └──────┘          │                                  ││
│  │  │                    │                                  ││
│  │  │  Database Subnet   │                                  ││
│  │  │  10.0.23.0/24      │                                  ││
│  │  │  ┌──────┐          │                                  ││
│  │  │  │ RDS  │          │                                  ││
│  │  │  │ 只读 │          │                                  ││
│  │  │  └──────┘          │                                  ││
│  │  └────────────────────┘                                  ││
│  │                                                           ││
│  └───────────────────────────────────────────────────────────┘│
│                                                               │
│  Internet ←→ IGW ←→ Public Subnets ←→ NAT GW ←→ Private     │
│                                       ←→ Private Subnets     │
└───────────────────────────────────────────────────────────────┘
```

#### 1.2 CIDR 规划最佳实践

```
┌─────────────────────────────────────────────────────────┐
│                    CIDR 规划策略                          │
│                                                         │
│  VPC CIDR: 10.0.0.0/16（65536 个 IP）                   │
│                                                         │
│  子网划分规则：                                          │
│  1. 每个 AZ 的子网使用 /24（256 个 IP）                  │
│  2. 公有/私有/数据库子网分别使用不同的第二段              │
│  3. 预留空间用于未来扩展                                 │
│                                                         │
│  子网命名规则：                                          │
│  10.0.XX.0/24                                          │
│       │                                                 │
│       ├── XX = 1-9: 公有子网                            │
│       │   10.0.1.0/24  (AZ-1a)                         │
│       │   10.0.2.0/24  (AZ-1b)                         │
│       │   10.0.3.0/24  (AZ-1c)                         │
│       │                                                 │
│       ├── XX = 11-19: 私有子网                          │
│       │   10.0.11.0/24 (AZ-1a)                         │
│       │   10.0.12.0/24 (AZ-1b)                         │
│       │   10.0.13.0/24 (AZ-1c)                         │
│       │                                                 │
│       ├── XX = 21-29: 数据库子网                        │
│       │   10.0.21.0/24 (AZ-1a)                         │
│       │   10.0.22.0/24 (AZ-1b)                         │
│       │   10.0.23.0/24 (AZ-1c)                         │
│       │                                                 │
│       └── XX = 31-39: 预留（未来扩展）                  │
│           10.0.31.0/24                                  │
│           10.0.32.0/24                                  │
│                                                         │
│  多 VPC 规划：                                          │
│  10.0.0.0/16  - 生产 VPC                               │
│  10.1.0.0/16  - 预发布 VPC                             │
│  10.2.0.0/16  - 开发 VPC                               │
│  10.100.0.0/16 - 共享服务 VPC                          │
└─────────────────────────────────────────────────────────┘
```

### 2. VPC 模块开发

#### 2.1 模块变量定义

```hcl
# modules/vpc/variables.tf

# ── 基础配置 ──
variable "name" {
  description = "VPC 名称前缀，用于资源命名和标签"
  type        = string

  validation {
    condition     = length(var.name) > 0 && length(var.name) <= 32
    error_message = "名称长度必须在 1-32 个字符之间。"
  }

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.name))
    error_message = "名称只能包含小写字母、数字和连字符。"
  }
}

variable "cidr" {
  description = "VPC CIDR 块"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.cidr, 0))
    error_message = "必须是有效的 CIDR 块。"
  }
}

variable "azs" {
  description = "可用区列表（至少 2 个，推荐 3 个）"
  type        = list(string)

  validation {
    condition     = length(var.azs) >= 2
    error_message = "至少需要 2 个可用区以确保高可用。"
  }
}

# ── 子网配置 ──
variable "public_subnets" {
  description = "公有子网 CIDR 列表（与 azs 数量一致）"
  type        = list(string)
  default     = []
}

variable "private_subnets" {
  description = "私有子网 CIDR 列表（与 azs 数量一致）"
  type        = list(string)
  default     = []
}

variable "database_subnets" {
  description = "数据库子网 CIDR 列表（与 azs 数量一致）"
  type        = list(string)
  default     = []
}

variable "elasticache_subnets" {
  description = "ElastiCache 子网 CIDR 列表"
  type        = list(string)
  default     = []
}

variable "intra_subnets" {
  description = "内部子网 CIDR 列表（无路由到互联网）"
  type        = list(string)
  default     = []
}

# ── NAT Gateway 配置 ──
variable "enable_nat_gateway" {
  description = "是否创建 NAT Gateway"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "是否使用单个 NAT Gateway（节省成本，不推荐生产环境）"
  type        = bool
  default     = false
}

variable "one_nat_gateway_per_az" {
  description = "每个 AZ 使用独立的 NAT Gateway（最高可用性）"
  type        = bool
  default     = false
}

# ── DNS 配置 ──
variable "enable_dns_hostnames" {
  description = "是否启用 DNS 主机名"
  type        = bool
  default     = true
}

variable "enable_dns_support" {
  description = "是否启用 DNS 支持"
  type        = bool
  default     = true
}

# ── VPC Endpoint 配置 ──
variable "enable_s3_endpoint" {
  description = "是否创建 S3 Gateway Endpoint"
  type        = bool
  default     = true
}

variable "enable_dynamodb_endpoint" {
  description = "是否创建 DynamoDB Gateway Endpoint"
  type        = bool
  default     = true
}

variable "enable_ecr_api_endpoint" {
  description = "是否创建 ECR API Interface Endpoint"
  type        = bool
  default     = false
}

variable "enable_ecr_dkr_endpoint" {
  description = "是否创建 ECR Docker Interface Endpoint"
  type        = bool
  default     = false
}

# ── Flow Logs 配置 ──
variable "enable_flow_log" {
  description = "是否启用 VPC Flow Logs"
  type        = bool
  default     = true
}

variable "flow_log_retention_days" {
  description = "Flow Logs 保留天数"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.flow_log_retention_days)
    error_message = "保留天数必须是 CloudWatch Logs 支持的值。"
  }
}

# ── 标签 ──
variable "tags" {
  description = "所有资源的通用标签"
  type        = map(string)
  default     = {}
}

variable "public_subnet_tags" {
  description = "公有子网的额外标签"
  type        = map(string)
  default     = {}
}

variable "private_subnet_tags" {
  description = "私有子网的额外标签"
  type        = map(string)
  default     = {}
}

variable "database_subnet_tags" {
  description = "数据库子网的额外标签"
  type        = map(string)
  default     = {}
}
```

#### 2.2 模块主配置

```hcl
# modules/vpc/main.tf

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
  }
}

locals {
  # 计算子网数量
  max_subnet_length = max(
    length(var.public_subnets),
    length(var.private_subnets),
    length(var.database_subnets),
    length(var.elasticache_subnets),
    length(var.intra_subnets),
  )

  # NAT Gateway 数量计算
  nat_gateway_count = var.enable_nat_gateway ? (
    var.one_nat_gateway_per_az ? length(var.azs) : (
      var.single_nat_gateway ? 1 : local.max_subnet_length
    )
  ) : 0

  # 通用标签
  tags = merge(var.tags, {
    Module    = "vpc"
    ManagedBy = "terraform"
  })
}

# ═══════════════════════════════════════════════════════════
# VPC
# ═══════════════════════════════════════════════════════════

resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_hostnames = var.enable_dns_hostnames
  enable_dns_support   = var.enable_dns_support

  tags = merge(local.tags, {
    Name = "${var.name}-vpc"
  })
}

# ═══════════════════════════════════════════════════════════
# Internet Gateway
# ═══════════════════════════════════════════════════════════

resource "aws_internet_gateway" "this" {
  count  = length(var.public_subnets) > 0 ? 1 : 0
  vpc_id = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${var.name}-igw"
  })
}

# ═══════════════════════════════════════════════════════════
# 公有子网
# ═══════════════════════════════════════════════════════════

resource "aws_subnet" "public" {
  count = length(var.public_subnets)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnets[count.index]
  availability_zone       = var.azs[count.index % length(var.azs)]
  map_public_ip_on_launch = true

  tags = merge(local.tags, var.public_subnet_tags, {
    Name = "${var.name}-public-${var.azs[count.index % length(var.azs)]}"
    Tier = "public"
  })
}

# ═══════════════════════════════════════════════════════════
# 私有子网
# ═══════════════════════════════════════════════════════════

resource "aws_subnet" "private" {
  count = length(var.private_subnets)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnets[count.index]
  availability_zone = var.azs[count.index % length(var.azs)]

  tags = merge(local.tags, var.private_subnet_tags, {
    Name = "${var.name}-private-${var.azs[count.index % length(var.azs)]}"
    Tier = "private"
  })
}

# ═══════════════════════════════════════════════════════════
# 数据库子网
# ═══════════════════════════════════════════════════════════

resource "aws_subnet" "database" {
  count = length(var.database_subnets)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.database_subnets[count.index]
  availability_zone = var.azs[count.index % length(var.azs)]

  tags = merge(local.tags, var.database_subnet_tags, {
    Name = "${var.name}-database-${var.azs[count.index % length(var.azs)]}"
    Tier = "database"
  })
}

resource "aws_db_subnet_group" "database" {
  count = length(var.database_subnets) > 0 ? 1 : 0

  name        = "${var.name}-database"
  description = "Database subnet group for ${var.name}"
  subnet_ids  = aws_subnet.database[*].id

  tags = merge(local.tags, {
    Name = "${var.name}-database-subnet-group"
  })
}

# ═══════════════════════════════════════════════════════════
# ElastiCache 子网
# ═══════════════════════════════════════════════════════════

resource "aws_subnet" "elasticache" {
  count = length(var.elasticache_subnets)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.elasticache_subnets[count.index]
  availability_zone = var.azs[count.index % length(var.azs)]

  tags = merge(local.tags, {
    Name = "${var.name}-elasticache-${var.azs[count.index % length(var.azs)]}"
    Tier = "elasticache"
  })
}

resource "aws_elasticache_subnet_group" "this" {
  count = length(var.elasticache_subnets) > 0 ? 1 : 0

  name        = "${var.name}-elasticache"
  description = "ElastiCache subnet group for ${var.name}"
  subnet_ids  = aws_subnet.elasticache[*].id

  tags = local.tags
}

# ═══════════════════════════════════════════════════════════
# 内部子网（无互联网路由）
# ═══════════════════════════════════════════════════════════

resource "aws_subnet" "intra" {
  count = length(var.intra_subnets)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.intra_subnets[count.index]
  availability_zone = var.azs[count.index % length(var.azs)]

  tags = merge(local.tags, {
    Name = "${var.name}-intra-${var.azs[count.index % length(var.azs)]}"
    Tier = "intra"
  })
}

# ═══════════════════════════════════════════════════════════
# NAT Gateway
# ═══════════════════════════════════════════════════════════

resource "aws_eip" "nat" {
  count  = local.nat_gateway_count
  domain = "vpc"

  tags = merge(local.tags, {
    Name = "${var.name}-nat-eip-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  count = local.nat_gateway_count

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index % length(aws_subnet.public)].id

  tags = merge(local.tags, {
    Name = "${var.name}-nat-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.this]
}

# ═══════════════════════════════════════════════════════════
# 公有路由表
# ═══════════════════════════════════════════════════════════

resource "aws_route_table" "public" {
  count  = length(var.public_subnets) > 0 ? 1 : 0
  vpc_id = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${var.name}-public-rt"
  })
}

resource "aws_route" "public_internet" {
  count                  = length(var.public_subnets) > 0 ? 1 : 0
  route_table_id         = aws_route_table.public[0].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this[0].id
}

resource "aws_route_table_association" "public" {
  count          = length(var.public_subnets)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

# ═══════════════════════════════════════════════════════════
# 私有路由表
# ═══════════════════════════════════════════════════════════

resource "aws_route_table" "private" {
  count  = length(var.private_subnets) > 0 ? local.nat_gateway_count : 0
  vpc_id = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${var.name}-private-rt-${count.index + 1}"
  })
}

resource "aws_route" "private_nat" {
  count                  = local.nat_gateway_count
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[count.index % local.nat_gateway_count].id
}

resource "aws_route_table_association" "private" {
  count          = length(var.private_subnets)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[var.single_nat_gateway ? 0 : count.index % local.nat_gateway_count].id
}

# ═══════════════════════════════════════════════════════════
# 数据库路由表（无互联网路由）
# ═══════════════════════════════════════════════════════════

resource "aws_route_table" "database" {
  count  = length(var.database_subnets) > 0 ? 1 : 0
  vpc_id = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${var.name}-database-rt"
  })
}

resource "aws_route_table_association" "database" {
  count          = length(var.database_subnets)
  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database[0].id
}

# ═══════════════════════════════════════════════════════════
# VPC Endpoints
# ═══════════════════════════════════════════════════════════

# S3 Gateway Endpoint
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_s3_endpoint ? 1 : 0

  vpc_id       = aws_vpc.this.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"

  route_table_ids = concat(
    aws_route_table.private[*].id,
    aws_route_table.database[*].id,
  )

  tags = merge(local.tags, {
    Name = "${var.name}-s3-endpoint"
  })
}

# DynamoDB Gateway Endpoint
resource "aws_vpc_endpoint" "dynamodb" {
  count = var.enable_dynamodb_endpoint ? 1 : 0

  vpc_id       = aws_vpc.this.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.dynamodb"
  vpc_endpoint_type = "Gateway"

  route_table_ids = concat(
    aws_route_table.private[*].id,
    aws_route_table.database[*].id,
  )

  tags = merge(local.tags, {
    Name = "${var.name}-dynamodb-endpoint"
  })
}

# ECR API Interface Endpoint
resource "aws_vpc_endpoint" "ecr_api" {
  count = var.enable_ecr_api_endpoint ? 1 : 0

  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ecr.api"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint[0].id]

  tags = merge(local.tags, {
    Name = "${var.name}-ecr-api-endpoint"
  })
}

# ECR Docker Interface Endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  count = var.enable_ecr_dkr_endpoint ? 1 : 0

  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint[0].id]

  tags = merge(local.tags, {
    Name = "${var.name}-ecr-dkr-endpoint"
  })
}

# VPC Endpoint 安全组
resource "aws_security_group" "vpc_endpoint" {
  count = (var.enable_ecr_api_endpoint || var.enable_ecr_dkr_endpoint) ? 1 : 0

  name_prefix = "${var.name}-vpc-endpoint-"
  description = "Security group for VPC Interface Endpoints"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${var.name}-vpc-endpoint-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ═══════════════════════════════════════════════════════════
# VPC Flow Logs
# ═══════════════════════════════════════════════════════════

resource "aws_flow_log" "this" {
  count = var.enable_flow_log ? 1 : 0

  vpc_id               = aws_vpc.this.id
  traffic_type         = "ALL"
  log_destination_type = "cloud-watch-logs"
  log_destination      = aws_cloudwatch_log_group.flow_log[0].arn
  iam_role_arn         = aws_iam_role.flow_log[0].arn

  tags = merge(local.tags, {
    Name = "${var.name}-flow-log"
  })
}

resource "aws_cloudwatch_log_group" "flow_log" {
  count             = var.enable_flow_log ? 1 : 0
  name              = "/aws/vpc-flow-log/${var.name}"
  retention_in_days = var.flow_log_retention_days

  tags = local.tags
}

resource "aws_iam_role" "flow_log" {
  count = var.enable_flow_log ? 1 : 0
  name  = "${var.name}-vpc-flow-log"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
    }]
  })

  tags = local.tags
}

resource "aws_iam_role_policy" "flow_log" {
  count = var.enable_flow_log ? 1 : 0
  name  = "${var.name}-vpc-flow-log"
  role  = aws_iam_role.flow_log[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

# ═══════════════════════════════════════════════════════════
# 默认安全组（限制所有流量）
# ═══════════════════════════════════════════════════════════

resource "aws_default_security_group" "this" {
  vpc_id = aws_vpc.this.id

  # 不添加任何规则 = 禁止所有流量
  tags = merge(local.tags, {
    Name = "${var.name}-default-sg-restricted"
  })
}

# ═══════════════════════════════════════════════════════════
# 数据源
# ═══════════════════════════════════════════════════════════

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
```

#### 2.3 模块输出

```hcl
# modules/vpc/outputs.tf

# ── VPC ──
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "VPC CIDR 块"
  value       = aws_vpc.this.cidr_block
}

output "vpc_arn" {
  description = "VPC ARN"
  value       = aws_vpc.this.arn
}

# ── 子网 ──
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

output "elasticache_subnet_ids" {
  description = "ElastiCache 子网 ID 列表"
  value       = aws_subnet.elasticache[*].id
}

output "intra_subnet_ids" {
  description = "内部子网 ID 列表"
  value       = aws_subnet.intra[*].id
}

# ── 子网组 ──
output "database_subnet_group_name" {
  description = "数据库子网组名称"
  value       = try(aws_db_subnet_group.database[0].name, null)
}

output "elasticache_subnet_group_name" {
  description = "ElastiCache 子网组名称"
  value       = try(aws_elasticache_subnet_group.this[0].name, null)
}

# ── 路由表 ──
output "public_route_table_ids" {
  description = "公有路由表 ID 列表"
  value       = aws_route_table.public[*].id
}

output "private_route_table_ids" {
  description = "私有路由表 ID 列表"
  value       = aws_route_table.private[*].id
}

output "database_route_table_ids" {
  description = "数据库路由表 ID 列表"
  value       = aws_route_table.database[*].id
}

# ── NAT Gateway ──
output "nat_gateway_ips" {
  description = "NAT Gateway 公有 IP 列表"
  value       = aws_eip.nat[*].public_ip
}

output "nat_gateway_ids" {
  description = "NAT Gateway ID 列表"
  value       = aws_nat_gateway.this[*].id
}

# ── Internet Gateway ──
output "igw_id" {
  description = "Internet Gateway ID"
  value       = try(aws_internet_gateway.this[0].id, null)
}

# ── VPC Endpoints ──
output "s3_endpoint_id" {
  description = "S3 VPC Endpoint ID"
  value       = try(aws_vpc_endpoint.s3[0].id, null)
}

output "dynamodb_endpoint_id" {
  description = "DynamoDB VPC Endpoint ID"
  value       = try(aws_vpc_endpoint.dynamodb[0].id, null)
}

# ── Flow Logs ──
output "flow_log_id" {
  description = "VPC Flow Log ID"
  value       = try(aws_flow_log.this[0].id, null)
}

output "flow_log_cloudwatch_log_group" {
  description = "Flow Log CloudWatch Log Group 名称"
  value       = try(aws_cloudwatch_log_group.flow_log[0].name, null)
}

# ── 安全组 ──
output "vpc_endpoint_security_group_id" {
  description = "VPC Endpoint 安全组 ID"
  value       = try(aws_security_group.vpc_endpoint[0].id, null)
}

# ── AZ 映射 ──
output "azs" {
  description = "使用的可用区列表"
  value       = var.azs
}
```

### 3. 多环境配置

#### 3.1 目录结构

```
environments/
├── dev/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── backend.tf
│   ├── providers.tf
│   └── terraform.tfvars
├── staging/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── backend.tf
│   ├── providers.tf
│   └── terraform.tfvars
└── prod/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── backend.tf
    ├── providers.tf
    └── terraform.tfvars
```

#### 3.2 开发环境配置

```hcl
# environments/dev/terraform.tfvars
name               = "dev"
cidr               = "10.2.0.0/16"
azs                = ["us-east-1a", "us-east-1b"]
public_subnets     = ["10.2.1.0/24", "10.2.2.0/24"]
private_subnets    = ["10.2.11.0/24", "10.2.12.0/24"]
database_subnets   = ["10.2.21.0/24", "10.2.22.0/24"]

# 开发环境：节省成本
enable_nat_gateway = true
single_nat_gateway = true  # 单个 NAT Gateway

# VPC Endpoints
enable_s3_endpoint       = true
enable_dynamodb_endpoint = true
enable_ecr_api_endpoint  = false
enable_ecr_dkr_endpoint  = false

# Flow Logs
enable_flow_log        = false  # 开发环境可关闭
flow_log_retention_days = 7

tags = {
  Environment = "dev"
  CostCenter  = "engineering"
  Team        = "sre"
}

private_subnet_tags = {
  "kubernetes.io/role/internal-elb" = "1"
}

public_subnet_tags = {
  "kubernetes.io/role/elb" = "1"
}
```

#### 3.3 生产环境配置

```hcl
# environments/prod/terraform.tfvars
name               = "prod"
cidr               = "10.0.0.0/16"
azs                = ["us-east-1a", "us-east-1b", "us-east-1c"]
public_subnets     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
private_subnets    = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
database_subnets   = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
elasticache_subnets = ["10.0.31.0/24", "10.0.32.0/24", "10.0.33.0/24"]

# 生产环境：高可用
enable_nat_gateway     = true
single_nat_gateway     = false  # 每个子网一个 NAT
one_nat_gateway_per_az = false

# VPC Endpoints
enable_s3_endpoint       = true
enable_dynamodb_endpoint = true
enable_ecr_api_endpoint  = true
enable_ecr_dkr_endpoint  = true

# Flow Logs
enable_flow_log        = true
flow_log_retention_days = 90

tags = {
  Environment = "prod"
  CostCenter  = "engineering"
  Team        = "sre"
  Compliance  = "pci-dss"
}

private_subnet_tags = {
  "kubernetes.io/role/internal-elb" = "1"
}

public_subnet_tags = {
  "kubernetes.io/role/elb" = "1"
}
```

#### 3.4 环境调用模块

```hcl
# environments/prod/main.tf

module "vpc" {
  source = "../../modules/vpc"

  name               = var.name
  cidr               = var.cidr
  azs                = var.azs
  public_subnets     = var.public_subnets
  private_subnets    = var.private_subnets
  database_subnets   = var.database_subnets
  elasticache_subnets = var.elasticache_subnets

  enable_nat_gateway     = var.enable_nat_gateway
  single_nat_gateway     = var.single_nat_gateway
  one_nat_gateway_per_az = var.one_nat_gateway_per_az

  enable_s3_endpoint       = var.enable_s3_endpoint
  enable_dynamodb_endpoint = var.enable_dynamodb_endpoint
  enable_ecr_api_endpoint  = var.enable_ecr_api_endpoint
  enable_ecr_dkr_endpoint  = var.enable_ecr_dkr_endpoint

  enable_flow_log        = var.enable_flow_log
  flow_log_retention_days = var.flow_log_retention_days

  tags              = var.tags
  public_subnet_tags  = var.public_subnet_tags
  private_subnet_tags = var.private_subnet_tags
}

# environments/prod/backend.tf
terraform {
  backend "s3" {
    bucket         = "terraform-state-123456789012"
    key            = "prod/vpc/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

# environments/prod/providers.tf
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Environment = "prod"
      ManagedBy   = "terraform"
      Project     = "platform"
    }
  }
}

# environments/prod/outputs.tf
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "database_subnet_ids" {
  value = module.vpc.database_subnet_ids
}
```

### 4. VPC 设计最佳实践

```
┌─────────────────────────────────────────────────────────┐
│              VPC 设计最佳实践总结                          │
│                                                         │
│  网络设计：                                              │
│  1. 使用 /16 VPC CIDR，预留扩展空间                     │
│  2. 每个子网使用 /24（256 个 IP）                        │
│  3. 至少 2 个 AZ，推荐 3 个 AZ                          │
│  4. 公有子网仅放 LB 和 NAT GW                          │
│  5. 应用和数据库放在私有子网                             │
│                                                         │
│  NAT Gateway：                                          │
│  1. 生产环境每个 AZ 一个 NAT GW（高可用）               │
│  2. 开发环境可使用单个 NAT GW（节省成本）               │
│  3. 监控 NAT GW 的数据处理量和连接数                    │
│                                                         │
│  安全：                                                  │
│  1. 限制默认安全组（不放行任何流量）                     │
│  2. 启用 VPC Flow Logs                                  │
│  3. 使用 VPC Endpoint 减少公网暴露                      │
│  4. NACL 作为额外的网络层防护                            │
│                                                         │
│  成本优化：                                              │
│  1. 使用 VPC Endpoint 替代 NAT GW 流量                  │
│  2. 开发环境使用单个 NAT GW                             │
│  3. Flow Logs 保留期根据合规要求调整                     │
│  4. 使用 Gateway Endpoint（免费）而非 Interface Endpoint│
│                                                         │
│  EKS 集成：                                             │
│  1. 子网添加 kubernetes.io/role/elb 标签                │
│  2. 私有子网添加 kubernetes.io/role/internal-elb 标签   │
│  3. 预留足够的 IP 给 Pod（VPC CNI 每个 Pod 一个 IP）    │
│  4. 考虑使用自定义网络（PREFIX_DELEGATION）             │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 实战练习

### 练习 1：开发完整 VPC 模块

**目标：** 从零开发上述 VPC 模块并验证

```bash
# 1. 创建模块目录结构
mkdir -p modules/vpc

# 2. 创建所有模块文件（variables.tf, main.tf, outputs.tf, versions.tf）

# 3. 创建开发环境
mkdir -p environments/dev

# 4. 初始化和验证
cd environments/dev
terraform init
terraform validate
terraform plan

# 5. 应用
terraform apply -auto-approve

# 6. 验证
terraform output
aws ec2 describe-vpcs --vpc-ids $(terraform output -raw vpc_id)

# 7. 清理
terraform destroy -auto-approve
```

### 练习 2：多环境部署

**目标：** 使用模块部署 dev 和 prod 两个环境

```bash
# 1. 创建 dev 和 prod 环境配置
# 2. 部署 dev 环境
cd environments/dev
terraform init && terraform apply -auto-approve

# 3. 部署 prod 环境
cd environments/prod
terraform init && terraform apply -auto-approve

# 4. 对比两个环境
echo "=== Dev VPC ==="
cd ../dev && terraform output
echo "=== Prod VPC ==="
cd ../prod && terraform output
```

### 练习 3：VPC Endpoint 验证

**目标：** 验证 VPC Endpoint 是否正确工作

```bash
# 1. 创建带 VPC Endpoint 的 VPC
# 2. 在私有子网创建 EC2 实例
# 3. 验证 S3 访问（通过 Endpoint，不经过 NAT）
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=vpc-xxx"

# 4. 在 EC2 上测试
# curl https://s3.us-east-1.amazonaws.com  # 应该通过 Endpoint
# 检查路由表是否包含 S3 Endpoint 的路由
```

---

## 🎯 面试题精选

### 1. 如何设计一个生产级 VPC？

**参考答案：**
- 使用 /16 CIDR 预留扩展空间
- 至少 3 个 AZ 部署
- 公有/私有/数据库三层子网
- 每个 AZ 一个 NAT Gateway（高可用）
- 启用 VPC Flow Logs
- 使用 VPC Endpoint 减少公网暴露
- 限制默认安全组
- 子网 CIDR 使用 /24，预留足够 IP

### 2. NAT Gateway 的三种配置策略是什么？

**参考答案：**
1. **单个 NAT Gateway**：所有 AZ 共享一个（最便宜，有单点故障）
2. **每子网一个 NAT Gateway**：按子网数量创建（中等成本）
3. **每 AZ 一个 NAT Gateway**：`one_nat_gateway_per_az = true`（最高可用性，最贵）

**推荐：** 生产环境使用每 AZ 一个或每子网一个；开发/测试使用单个。

### 3. VPC Gateway Endpoint 和 Interface Endpoint 的区别是什么？

**参考答案：**
| 维度 | Gateway Endpoint | Interface Endpoint |
|------|-----------------|-------------------|
| 支持服务 | S3、DynamoDB | 大多数 AWS 服务 |
| 费用 | 免费 | 按小时和数据量收费 |
| 实现方式 | 路由表条目 | ENI（弹性网络接口） |
| DNS | 前缀列表 | 私有 DNS |
| 跨区域 | 不支持 | 支持 |

### 4. 为什么私有子网需要 NAT Gateway？

**参考答案：**
私有子网没有直接通往 Internet Gateway 的路由。NAT Gateway 允许私有子网中的实例访问互联网（如拉取 Docker 镜像、更新软件包），同时阻止互联网主动连接私有实例。NAT Gateway 部署在公有子网中，私有子网通过路由表将出站流量指向 NAT Gateway。

### 5. VPC Flow Logs 的作用是什么？

**参考答案：**
VPC Flow Logs 记录 VPC 中网络接口的入站和出站流量信息，包括：
- 源/目标 IP 和端口
- 协议
- 接受/拒绝状态
- 数据包和字节数

用途：安全审计、网络故障排查、合规要求、流量分析。

### 6. 如何为 EKS 准备 VPC 子网？

**参考答案：**
1. 为子网添加 EKS 所需标签：
   - 公有子网：`kubernetes.io/role/elb = "1"`
   - 私有子网：`kubernetes.io/role/internal-elb = "1"`
2. 确保每个子网有足够的 IP（每个 Pod 一个 IP）
3. 使用 VPC CNI 的 PREFIX_DELEGATION 模式扩展 IP 空间
4. 考虑使用独立子网给 Pod 使用

### 7. 如何降低 VPC 的 NAT Gateway 成本？

**参考答案：**
1. 使用 VPC Endpoint 替代 NAT Gateway 流量（S3、DynamoDB 免费）
2. 使用 Gateway Endpoint 访问 S3 和 DynamoDB
3. 开发环境使用单个 NAT Gateway
4. 监控 NAT Gateway 数据处理量，优化应用流量
5. 使用 NAT Instance 替代（小规模场景）

### 8. 默认安全组为什么应该限制所有流量？

**参考答案：**
AWS 默认安全组允许同组内所有流量互通。如果没有明确使用自定义安全组，资源会被分配到默认安全组，导致意外的网络访问。限制默认安全组（不添加任何规则）是一种防御性措施，强制所有资源必须显式使用自定义安全组。

---

## 📚 深入阅读

- [AWS VPC 文档](https://docs.aws.amazon.com/vpc/latest/userguide/)
- [terraform-aws-modules/vpc](https://github.com/terraform-aws-modules/terraform-aws-vpc)
- [VPC CIDR 规划](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Subnets.html)
- [VPC Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)

---

## ✅ 自检清单

- [ ] 理解生产级 VPC 的架构设计（三层子网、多 AZ）
- [ ] 掌握 CIDR 规划最佳实践（/16 VPC、/24 子网）
- [ ] 能开发一个完整的可复用 VPC 模块
- [ ] 掌握子网、路由表、NAT Gateway 的参数化设计
- [ ] 实现了多环境差异化配置（dev/staging/prod）
- [ ] 理解 VPC Gateway Endpoint 和 Interface Endpoint 的区别
- [ ] 配置了 VPC Flow Logs 和 CloudWatch 日志
- [ ] 理解 NAT Gateway 的三种配置策略和成本影响
- [ ] 掌握 EKS 子网标签配置
- [ ] 理解默认安全组的安全加固
