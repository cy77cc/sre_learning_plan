# Day 122: Terraform 进阶

> 📅 日期：2026-05-04
> 📖 学习主题：模块开发、状态管理 remote backend、导入与移动、workspace、模块注册、terraform test
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 120（Terraform 简介）、Day 121（Terraform 基础）

---

## 🎯 学习目标

- 掌握 Terraform 模块的设计、开发和发布
- 理解 remote backend 的配置和状态管理最佳实践
- 掌握资源导入（import）和移动（moved block）的使用
- 熟练使用 workspace 管理多环境
- 了解 Terraform Registry 模块发布流程
- 掌握 terraform test 编写基础设施测试

---

## 📖 核心知识点

### 1. 模块开发（Module Development）

#### 1.1 模块是什么

模块是 Terraform 代码组织和复用的基本单位。一个模块就是一组 `.tf` 文件的集合，通过 `module` 块调用。

```
┌─────────────────────────────────────────────────────────┐
│                    模块架构                               │
│                                                         │
│  Root Module（根模块）                                   │
│  ┌──────────────────────────────────────────────┐       │
│  │  main.tf                                    │       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │       │
│  │  │ module  │  │ module  │  │ resource│     │       │
│  │  │ "vpc"   │  │ "eks"   │  │ "s3"    │     │       │
│  │  └────┬────┘  └────┬────┘  └─────────┘     │       │
│  └───────┼────────────┼────────────────────────┘       │
│          │            │                                 │
│  ┌───────▼────┐ ┌─────▼──────┐                         │
│  │ VPC Module │ │ EKS Module │  ← 子模块               │
│  │            │ │            │                          │
│  │ main.tf    │ │ main.tf    │                          │
│  │ variables.tf│ │ variables.tf│                        │
│  │ outputs.tf │ │ outputs.tf │                          │
│  └────────────┘ └────────────┘                          │
│                                                         │
│  来源：                                                 │
│  - 本地路径（./modules/vpc）                            │
│  - Terraform Registry（terraform-aws-modules/vpc/aws）  │
│  - Git 仓库（git::https://github.com/xxx//modules/vpc） │
│  - S3 存储桶（s3::https://bucket.s3.amazonaws.com/xxx） │
└─────────────────────────────────────────────────────────┘
```

#### 1.2 模块结构规范

```
modules/
└── vpc/
    ├── main.tf           # 主要资源定义
    ├── variables.tf      # 输入变量声明
    ├── outputs.tf        # 输出值定义
    ├── versions.tf       # Provider 版本约束
    ├── locals.tf         # 本地值
    ├── data.tf           # 数据源
    ├── README.md         # 模块文档
    └── examples/         # 使用示例
        └── complete/
            ├── main.tf
            └── outputs.tf
```

#### 1.3 模块开发实战：VPC 模块

```hcl
# ═══════════════════════════════════════════
# modules/vpc/variables.tf
# ═══════════════════════════════════════════

variable "name" {
  description = "VPC 名称前缀"
  type        = string
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
  description = "可用区列表"
  type        = list(string)
}

variable "private_subnets" {
  description = "私有子网 CIDR 列表"
  type        = list(string)
  default     = []
}

variable "public_subnets" {
  description = "公有子网 CIDR 列表"
  type        = list(string)
  default     = []
}

variable "database_subnets" {
  description = "数据库子网 CIDR 列表"
  type        = list(string)
  default     = []
}

variable "enable_nat_gateway" {
  description = "是否创建 NAT Gateway"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "是否使用单个 NAT Gateway（节省成本）"
  type        = bool
  default     = false
}

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

variable "tags" {
  description = "资源标签"
  type        = map(string)
  default     = {}
}
```

```hcl
# ═══════════════════════════════════════════
# modules/vpc/main.tf
# ═══════════════════════════════════════════

locals {
  # 计算子网数量
  max_subnet_length = max(
    length(var.private_subnets),
    length(var.public_subnets),
    length(var.database_subnets),
  )

  # NAT Gateway 数量
  nat_gateway_count = var.enable_nat_gateway ? (
    var.single_nat_gateway ? 1 : local.max_subnet_length
  ) : 0

  # 公共标签
  tags = merge(var.tags, {
    Module = "vpc"
  })
}

# ── VPC ──
resource "aws_vpc" "this" {
  cidr_block           = var.cidr
  enable_dns_hostnames = var.enable_dns_hostnames
  enable_dns_support   = var.enable_dns_support

  tags = merge(local.tags, {
    Name = "${var.name}-vpc"
  })
}

# ── Internet Gateway ──
resource "aws_internet_gateway" "this" {
  count  = length(var.public_subnets) > 0 ? 1 : 0
  vpc_id = aws_vpc.this.id

  tags = merge(local.tags, {
    Name = "${var.name}-igw"
  })
}

# ── 公有子网 ──
resource "aws_subnet" "public" {
  count = length(var.public_subnets)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnets[count.index]
  availability_zone       = var.azs[count.index % length(var.azs)]
  map_public_ip_on_launch = true

  tags = merge(local.tags, {
    Name = "${var.name}-public-${var.azs[count.index % length(var.azs)]}"
    Tier = "public"
  })
}

# ── 私有子网 ──
resource "aws_subnet" "private" {
  count = length(var.private_subnets)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnets[count.index]
  availability_zone = var.azs[count.index % length(var.azs)]

  tags = merge(local.tags, {
    Name = "${var.name}-private-${var.azs[count.index % length(var.azs)]}"
    Tier = "private"
  })
}

# ── 数据库子网 ──
resource "aws_subnet" "database" {
  count = length(var.database_subnets)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.database_subnets[count.index]
  availability_zone = var.azs[count.index % length(var.azs)]

  tags = merge(local.tags, {
    Name = "${var.name}-database-${var.azs[count.index % length(var.azs)]}"
    Tier = "database"
  })
}

# ── 数据库子网组 ──
resource "aws_db_subnet_group" "database" {
  count = length(var.database_subnets) > 0 ? 1 : 0

  name        = "${var.name}-database"
  description = "Database subnet group for ${var.name}"
  subnet_ids  = aws_subnet.database[*].id

  tags = merge(local.tags, {
    Name = "${var.name}-database-subnet-group"
  })
}

# ── NAT Gateway（EIP + NAT）──
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

# ── 公有路由表 ──
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

# ── 私有路由表 ──
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

# ── 数据库路由表 ──
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

# ── VPC Flow Logs ──
resource "aws_flow_log" "this" {
  count = 1

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
  count             = 1
  name              = "/aws/vpc-flow-log/${var.name}"
  retention_in_days = 30

  tags = local.tags
}

resource "aws_iam_role" "flow_log" {
  count = 1
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
  count = 1
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
```

```hcl
# ═══════════════════════════════════════════
# modules/vpc/outputs.tf
# ═══════════════════════════════════════════

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "vpc_cidr" {
  description = "VPC CIDR 块"
  value       = aws_vpc.this.cidr_block
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
  value       = try(aws_db_subnet_group.database[0].name, null)
}

output "nat_gateway_ips" {
  description = "NAT Gateway 公有 IP"
  value       = aws_eip.nat[*].public_ip
}

output "public_route_table_ids" {
  description = "公有路由表 ID 列表"
  value       = aws_route_table.public[*].id
}

output "private_route_table_ids" {
  description = "私有路由表 ID 列表"
  value       = aws_route_table.private[*].id
}
```

```hcl
# ═══════════════════════════════════════════
# modules/vpc/versions.tf
# ═══════════════════════════════════════════

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
  }
}
```

#### 1.4 调用模块

```hcl
# ── 本地模块 ──
module "vpc" {
  source = "./modules/vpc"

  name               = "production"
  cidr               = "10.0.0.0/16"
  azs                = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnets     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnets    = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  database_subnets   = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = false

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# ── Registry 模块 ──
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "my-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {
    Terraform   = "true"
    Environment = "prod"
  }
}

# ── Git 模块 ──
module "vpc" {
  source = "git::https://github.com/myorg/terraform-modules.git//modules/vpc?ref=v1.2.0"
}

# ── 使用模块输出 ──
resource "aws_instance" "web" {
  subnet_id = module.vpc.private_subnet_ids[0]
}
```

#### 1.5 模块设计最佳实践

```
┌─────────────────────────────────────────────────────────┐
│                模块设计最佳实践                            │
│                                                         │
│  1. 单一职责                                             │
│     - 一个模块只做一件事（VPC、EKS、RDS）                │
│     - 不要把所有资源放在一个大模块中                      │
│                                                         │
│  2. 接口清晰                                             │
│     - variables.tf 定义清晰的输入                        │
│     - outputs.tf 暴露必要的输出                          │
│     - 使用 validation 验证输入                           │
│                                                         │
│  3. 合理默认值                                           │
│     - 为常用参数提供合理默认值                           │
│     - 敏感参数不设默认值（强制传入）                      │
│                                                         │
│  4. 版本管理                                             │
│     - 使用语义化版本号                                   │
│     - Git tag 标记发布版本                               │
│     - versions.tf 约束 Provider 版本                     │
│                                                         │
│  5. 文档与示例                                           │
│     - README.md 说明用途和参数                           │
│     - examples/ 目录提供使用示例                         │
│                                                         │
│  6. 不要硬编码                                           │
│     - 区域、账号 ID、CIDR 等都应参数化                   │
│     - 使用 variables 传入所有可变值                      │
└─────────────────────────────────────────────────────────┘
```

### 2. Remote Backend 状态管理

#### 2.1 为什么需要 Remote Backend

```
┌─────────────────────────────────────────────────────────┐
│           本地状态 vs Remote 状态                         │
│                                                         │
│  本地状态的问题：                                        │
│  ┌─────────────────────────────────────────────┐        │
│  │ 1. 单点故障（磁盘损坏 = 状态丢失）           │        │
│  │ 2. 无法协作（多人无法共享）                   │        │
│  │ 3. 无状态锁（并发修改冲突）                   │        │
│  │ 4. 安全风险（敏感信息在本地）                 │        │
│  │ 5. 无审计（谁改了状态？）                     │        │
│  └─────────────────────────────────────────────┘        │
│                                                         │
│  Remote Backend 解决方案：                               │
│  ┌─────────────────────────────────────────────┐        │
│  │ 1. 高可用存储（S3 跨 AZ 复制）               │        │
│  │ 2. 团队共享（所有人访问同一状态）             │        │
│  │ 3. 状态锁（DynamoDB 防止并发）               │        │
│  │ 4. 加密存储（S3 SSE 加密）                   │        │
│  │ 5. 版本历史（S3 版本控制）                   │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

#### 2.2 S3 Backend 配置

```hcl
# ═══════════════════════════════════════════
# 先创建 S3 Bucket 和 DynamoDB 表（一次性）
# ═══════════════════════════════════════════

# bootstrap/main.tf
resource "aws_s3_bucket" "terraform_state" {
  bucket = "my-terraform-state-${data.aws_caller_identity.current.account_id}"

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name        = "Terraform State"
    ManagedBy   = "terraform-bootstrap"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_dynamodb_table" "terraform_lock" {
  name         = "terraform-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name      = "Terraform State Lock"
    ManagedBy = "terraform-bootstrap"
  }
}
```

```hcl
# ═══════════════════════════════════════════
# 使用 Remote Backend
# ═══════════════════════════════════════════

terraform {
  backend "s3" {
    bucket         = "my-terraform-state-123456789012"
    key            = "production/vpc/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"

    # 可选：使用 KMS 加密
    # kms_key_id = "arn:aws:kms:us-east-1:123456789012:key/xxx"
  }
}
```

#### 2.3 Backend 迁移

```bash
# 从本地状态迁移到 S3
# 1. 配置新的 backend
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

# 2. 执行迁移
terraform init -migrate-state
# Terraform 会检测到 backend 变更
# 提示是否将现有状态迁移到新 backend
# 输入 yes 确认

# 3. 验证
terraform state list
```

#### 2.4 Remote State Data Source

```hcl
# 跨项目共享状态数据
data "terraform_remote_state" "vpc" {
  backend = "s3"

  config = {
    bucket = "my-terraform-state"
    key    = "production/vpc/terraform.tfstate"
    region = "us-east-1"
  }
}

# 使用远程状态输出
resource "aws_instance" "web" {
  subnet_id = data.terraform_remote_state.vpc.outputs.private_subnet_ids[0]
}
```

### 3. 资源导入（Import）

#### 3.1 传统 import 命令

```bash
# 将已有资源导入到 Terraform 管理
terraform import aws_instance.web i-1234567890abcdef0
terraform import aws_s3_bucket.my_bucket my-bucket-name
terraform import aws_vpc.main vpc-12345678
terraform import 'aws_instance.web[0]' i-xxx
terraform import 'module.vpc.aws_subnet.public[0]' subnet-xxx
```

#### 3.2 Import Block（Terraform 1.5+）

```hcl
# 使用 import block 声明式导入
import {
  to = aws_instance.web
  id = "i-1234567890abcdef0"
}

import {
  to = aws_s3_bucket.my_bucket
  id = "my-bucket-name"
}

import {
  to = aws_vpc.main
  id = "vpc-12345678"
}

# 配合 plan 使用
# terraform plan -generate-config-out=generated.tf
# 这会生成导入资源的配置代码
```

#### 3.3 导入工作流

```
导入已有资源的完整流程：

┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 1. 编写配置   │───→│ 2. 导入资源   │───→│ 3. 对比差异   │
│ 手动或生成    │    │ terraform    │    │ terraform    │
│              │    │ import       │    │ plan         │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                    ┌──────────┴──────────┐
                                    │                     │
                              ┌─────▼─────┐         ┌─────▼─────┐
                              │ 无差异     │         │ 有差异     │
                              │ 完成！     │         │ 调整配置   │
                              └───────────┘         │ 匹配实际   │
                                                    └───────────┘
```

### 4. Moved Block（资源移动）

#### 4.1 Moved Block 语法

```hcl
# Terraform 1.1+ 支持 moved block
# 用于重命名或移动资源，无需删除重建

# ── 重命名资源 ──
moved {
  from = aws_instance.web
  to   = aws_instance.application
}

# ── 移动到模块 ──
moved {
  from = aws_instance.web
  to   = module.ec2.aws_instance.web
}

# ── 移动 count 资源到 for_each ──
moved {
  from = aws_instance.web[0]
  to   = aws_instance.web["web-1"]
}

moved {
  from = aws_instance.web[1]
  to   = aws_instance.web["web-2"]
}

# ── 在模块之间移动 ──
moved {
  from = module.old_name
  to   = module.new_name
}

# ── 重命名模块 ──
moved {
  from = module.vpc
  to   = module.network
}
```

#### 4.2 与 state mv 的对比

```bash
# state mv 命令（旧方式，命令式）
terraform state mv aws_instance.web aws_instance.application
terraform state mv aws_instance.web[0] 'aws_instance.web["web-1"]'

# moved block（新方式，声明式）— 推荐
# moved {
#   from = aws_instance.web
#   to   = aws_instance.application
# }
```

| 维度 | state mv | moved block |
|------|----------|-------------|
| 方式 | 命令式 | 声明式 |
| 版本控制 | 不在 Git 中 | 在 Git 中可追溯 |
| 可审查 | 不可 | 可以 PR 审查 |
| 安全性 | 直接操作状态 | plan 预览后执行 |
| 推荐度 | 仅紧急情况 | 推荐使用 |

### 5. Workspace（工作空间）

#### 5.1 Workspace 概述

Workspace 用于在同一配置中管理多个环境的状态。每个 workspace 有独立的状态文件。

```
┌─────────────────────────────────────────────────────────┐
│                    Workspace 架构                         │
│                                                         │
│  同一套 .tf 配置文件                                     │
│  ┌─────────────────────────────────────────────┐        │
│  │  main.tf                                    │        │
│  │  variables.tf                               │        │
│  │  outputs.tf                                 │        │
│  └─────────────────────────────────────────────┘        │
│                     │                                   │
│         ┌───────────┼───────────┐                       │
│         │           │           │                       │
│  ┌──────▼──────┐ ┌──▼────────┐ ┌▼──────────┐           │
│  │   dev       │ │  staging  │ │  prod     │           │
│  │ workspace   │ │ workspace │ │ workspace │           │
│  │             │ │           │ │           │           │
│  │ terraform   │ │ terraform │ │ terraform │           │
│  │ .tfstate    │ │ .tfstate  │ │ .tfstate  │           │
│  │             │ │           │ │           │           │
│  │ VPC: vpc-1  │ │ VPC: vpc-2│ │ VPC: vpc-3│          │
│  │ EC2: i-1    │ │ EC2: i-2  │ │ EC2: i-3  │          │
│  └─────────────┘ └───────────┘ └───────────┘           │
└─────────────────────────────────────────────────────────┘
```

#### 5.2 Workspace 命令

```bash
# 列出所有 workspace
terraform workspace list
#   default
# * dev
#   staging
#   prod

# 创建新 workspace
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod

# 切换 workspace
terraform workspace select prod

# 显示当前 workspace
terraform workspace show

# 删除 workspace（必须先切换到其他 workspace）
terraform workspace select default
terraform workspace delete dev
```

#### 5.3 在配置中使用 Workspace

```hcl
# 根据 workspace 使用不同配置
locals {
  env_config = {
    dev = {
      instance_type = "t3.micro"
      instance_count = 1
      db_instance_class = "db.t3.micro"
    }
    staging = {
      instance_type = "t3.small"
      instance_count = 2
      db_instance_class = "db.t3.small"
    }
    prod = {
      instance_type = "t3.medium"
      instance_count = 3
      db_instance_class = "db.r6g.large"
    }
  }

  # 使用当前 workspace 名称
  current_env    = terraform.workspace
  current_config = local.env_config[local.current_env]
}

resource "aws_instance" "web" {
  count         = local.current_config.instance_count
  instance_type = local.current_config.instance_type

  tags = {
    Name        = "${local.current_env}-web-${count.index + 1}"
    Environment = local.current_env
    Workspace   = terraform.workspace
  }
}
```

#### 5.4 Workspace vs 目录隔离

```
┌─────────────────────────────────────────────────────────┐
│           Workspace vs 目录隔离 对比                      │
│                                                         │
│  Workspace 方式：                                        │
│  project/                                               │
│  ├── main.tf                                            │
│  ├── variables.tf                                       │
│  └── outputs.tf                                         │
│  状态：dev.tfstate, staging.tfstate, prod.tfstate        │
│                                                         │
│  目录隔离方式（推荐）：                                   │
│  project/                                               │
│  ├── modules/                                           │
│  │   └── vpc/                                           │
│  ├── environments/                                      │
│  │   ├── dev/                                           │
│  │   │   ├── main.tf                                    │
│  │   │   ├── terraform.tfvars                           │
│  │   │   └── backend.tf                                 │
│  │   ├── staging/                                       │
│  │   │   ├── main.tf                                    │
│  │   │   ├── terraform.tfvars                           │
│  │   │   └── backend.tf                                 │
│  │   └── prod/                                          │
│  │       ├── main.tf                                    │
│  │       ├── terraform.tfvars                           │
│  │       └── backend.tf                                 │
│                                                         │
│  推荐目录隔离，因为：                                     │
│  - 每个环境独立的 tfvars（不同的配置）                   │
│  - 每个环境独立的 backend（不同的状态 key）              │
│  - 更清晰的 Git 历史                                    │
│  - 避免 workspace 切换错误                              │
└─────────────────────────────────────────────────────────┘
```

### 6. Terraform Test

#### 6.1 测试框架概述

Terraform 1.6+ 引入了原生测试框架 `terraform test`。

```hcl
# ═══════════════════════════════════════════
# tests/vpc_test.tftest.hcl
# ═══════════════════════════════════════════

# 测试运行变量
variables {
  name               = "test"
  cidr               = "10.0.0.0/16"
  azs                = ["us-east-1a", "us-east-1b"]
  public_subnets     = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets    = ["10.0.11.0/24", "10.0.12.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = true
  tags = {
    Environment = "test"
  }
}

# 测试用例 1：验证 VPC CIDR
run "verify_vpc_cidr" {
  command = plan

  assert {
    condition     = module.vpc.vpc_cidr == "10.0.0.0/16"
    error_message = "VPC CIDR 应该是 10.0.0.0/16"
  }
}

# 测试用例 2：验证子网数量
run "verify_subnet_count" {
  command = plan

  assert {
    condition     = length(module.vpc.public_subnet_ids) == 2
    error_message = "应该创建 2 个公有子网"
  }

  assert {
    condition     = length(module.vpc.private_subnet_ids) == 2
    error_message = "应该创建 2 个私有子网"
  }
}

# 测试用例 3：验证 NAT Gateway 数量
run "verify_nat_gateway" {
  command = plan

  assert {
    condition     = length(module.vpc.nat_gateway_ips) == 1
    error_message = "single_nat_gateway=true 时应该只有 1 个 NAT Gateway"
  }
}

# 测试用例 4：验证标签
run "verify_tags" {
  command = plan

  assert {
    condition     = module.vpc.vpc_tags["Environment"] == "test"
    error_message = "VPC 应该有 Environment=test 标签"
  }
}

# 测试用例 5：实际创建资源（需要 AWS 凭证）
run "apply_and_verify" {
  command = apply

  assert {
    condition     = module.vpc.vpc_id != ""
    error_message = "VPC 应该成功创建"
  }

  assert {
    condition     = can(regex("^vpc-", module.vpc.vpc_id))
    error_message = "VPC ID 应该以 vpc- 开头"
  }
}
```

#### 6.2 运行测试

```bash
# 运行所有测试
terraform test

# 运行特定测试文件
terraform test -filter=tests/vpc_test.tftest.hcl

# 详细输出
terraform test -verbose

# 只运行 plan 测试（不需要 AWS 凭证）
terraform test -filter=tests/vpc_test.tftest.hcl
```

### 7. 模块发布到 Terraform Registry

#### 7.1 发布要求

```
模块发布到 Registry 的要求：

1. 仓库命名规范
   - GitHub: terraform-<PROVIDER>-<NAME>
   - 例如: terraform-aws-vpc

2. 目录结构
   - 根目录必须有 main.tf, variables.tf, outputs.tf
   - 必须有 README.md

3. 版本标签
   - 使用语义化版本: v1.0.0, v1.1.0, v2.0.0
   - Git tag 标记

4. 文档
   - 使用 terraform-docs 生成文档
   - 包含使用示例

5. GPG 签名（推荐）
   - 用 GPG key 签名 tag
```

#### 7.2 使用 terraform-docs 生成文档

```bash
# 安装 terraform-docs
brew install terraform-docs

# 生成 Markdown 文档
terraform-docs markdown table ./modules/vpc > ./modules/vpc/README.md

# 配置文件 .terraform-docs.yml
# formatter: markdown table
# output:
#   file: README.md
#   mode: replace
# sections:
#   show:
#     - requirements
#     - providers
#     - inputs
#     - outputs
```

---

## 💻 实战练习

### 练习 1：开发一个 S3 模块

**目标：** 创建一个可复用的 S3 Bucket 模块

```hcl
# modules/s3-bucket/variables.tf
variable "bucket_name" {
  description = "Bucket 名称"
  type        = string
}

variable "versioning" {
  description = "是否启用版本控制"
  type        = bool
  default     = true
}

variable "encryption" {
  description = "是否启用加密"
  type        = bool
  default     = true
}

variable "block_public_access" {
  description = "是否阻止公开访问"
  type        = bool
  default     = true
}

variable "lifecycle_rules" {
  description = "生命周期规则"
  type = list(object({
    id                            = string
    enabled                       = bool
    prefix                        = string
    transition_days               = number
    transition_storage_class      = string
    noncurrent_expiration_days    = number
  }))
  default = []
}

variable "tags" {
  description = "资源标签"
  type        = map(string)
  default     = {}
}

# modules/s3-bucket/main.tf
resource "aws_s3_bucket" "this" {
  bucket = var.bucket_name
  tags   = var.tags
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = var.versioning ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  count  = var.encryption ? 1 : 0
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  count  = var.block_public_access ? 1 : 0
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  count  = length(var.lifecycle_rules) > 0 ? 1 : 0
  bucket = aws_s3_bucket.this.id

  dynamic "rule" {
    for_each = var.lifecycle_rules
    content {
      id     = rule.value.id
      status = rule.value.enabled ? "Enabled" : "Disabled"

      filter {
        prefix = rule.value.prefix
      }

      transition {
        days          = rule.value.transition_days
        storage_class = rule.value.transition_storage_class
      }

      noncurrent_version_expiration {
        noncurrent_days = rule.value.noncurrent_expiration_days
      }
    }
  }
}

# modules/s3-bucket/outputs.tf
output "bucket_id" {
  value = aws_s3_bucket.this.id
}

output "bucket_arn" {
  value = aws_s3_bucket.this.arn
}

output "bucket_domain_name" {
  value = aws_s3_bucket.this.bucket_domain_name
}
```

### 练习 2：配置 Remote Backend

**目标：** 创建 S3 Backend 基础设施并迁移本地状态

```hcl
# bootstrap/main.tf
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
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "terraform_state" {
  bucket = "terraform-state-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket                  = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_lock" {
  name         = "terraform-lock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute { name = "LockID"; type = "S" }
}

output "state_bucket" { value = aws_s3_bucket.terraform_state.id }
output "lock_table"   { value = aws_dynamodb_table.terraform_lock.name }
```

### 练习 3：Workspace 多环境管理

**目标：** 使用 workspace 管理 dev/staging/prod 环境

```bash
# 1. 创建 workspace
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod

# 2. 切换到 dev 并应用
terraform workspace select dev
terraform plan -var-file=dev.tfvars
terraform apply -var-file=dev.tfvars

# 3. 切换到 prod 并应用
terraform workspace select prod
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars

# 4. 验证各环境状态独立
terraform workspace select dev
terraform state list
# 只显示 dev 的资源

terraform workspace select prod
terraform state list
# 只显示 prod 的资源
```

---

## 🎯 面试题精选

### 1. 如何设计一个可复用的 Terraform 模块？

**参考答案：**
1. **单一职责**：一个模块只管理一类资源（如 VPC、RDS）
2. **清晰接口**：variables.tf 定义输入，outputs.tf 暴露输出
3. **合理默认值**：常用参数有默认值，敏感参数强制传入
4. **版本管理**：使用语义化版本号和 Git tag
5. **文档完善**：README.md 说明用途和参数，examples/ 提供示例
6. **不硬编码**：区域、CIDR、账号等都参数化

### 2. Remote Backend 的作用是什么？为什么生产环境必须使用？

**参考答案：**
Remote Backend 解决了本地状态的多个问题：
- **高可用**：S3 跨 AZ 复制，避免单点故障
- **团队协作**：多人共享同一状态文件
- **状态锁**：DynamoDB 防止并发修改冲突
- **安全加密**：S3 KMS 加密保护敏感信息
- **版本历史**：S3 版本控制可回滚状态

### 3. `moved` block 和 `terraform state mv` 的区别是什么？

**参考答案：**
- `state mv` 是命令式操作，直接修改状态文件，不在版本控制中
- `moved` block 是声明式方式，写在 .tf 文件中，可提交到 Git，可 PR 审查
- `moved` block 在 plan 时预览，更安全
- **推荐**：使用 `moved` block，仅在紧急情况使用 `state mv`

### 4. Workspace 和目录隔离哪种方式更好？

**参考答案：**
**推荐目录隔离**，原因：
- 每个环境独立的 tfvars 文件（不同配置）
- 每个环境独立的 backend 配置（不同状态 key）
- 更清晰的 Git 历史和变更追踪
- 避免 workspace 切换错误导致在错误环境执行

Workspace 适合：开发/测试快速切换，共享相同配置的小项目。

### 5. 如何将已有基础设施迁移到 Terraform 管理？

**参考答案：**
1. 编写与已有资源匹配的 HCL 配置
2. 使用 `terraform import` 或 `import` block 导入资源
3. 运行 `terraform plan` 检查差异
4. 调整配置使其与实际资源完全匹配
5. 使用 `-generate-config-out` 自动生成配置（1.5+）

### 6. terraform test 的作用是什么？

**参考答案：**
`terraform test` 是 Terraform 1.6+ 的原生测试框架，用于：
- 验证模块输出是否符合预期
- 测试不同参数组合的效果
- 在 CI/CD 中自动验证基础设施变更
- 支持 plan 级别测试（无需实际创建资源）和 apply 级别测试

### 7. 如何管理跨项目的 Terraform 状态依赖？

**参考答案：**
使用 `terraform_remote_state` 数据源：
```hcl
data "terraform_remote_state" "vpc" {
  backend = "s3"
  config = {
    bucket = "terraform-state"
    key    = "prod/vpc/terraform.tfstate"
    region = "us-east-1"
  }
}
```
或者使用 SSM Parameter Store、Consul 等共享数据。

### 8. 模块版本管理的最佳实践是什么？

**参考答案：**
1. 使用语义化版本号（MAJOR.MINOR.PATCH）
2. Git tag 标记每个发布版本
3. 调用方使用 `~>` 约束版本（如 `~> 1.0`）
4. Breaking change 升 MAJOR 版本号
5. 使用 terraform-docs 自动生成文档
6. CI/CD 自动运行 terraform test

---

## 📚 深入阅读

- [Terraform Modules](https://developer.hashicorp.com/terraform/language/modules)
- [Terraform Backends](https://developer.hashicorp.com/terraform/language/backend)
- [Terraform Import](https://developer.hashicorp.com/terraform/language/import)
- [Terraform Test](https://developer.hashicorp.com/terraform/language/tests)
- [Terraform Registry Publishing](https://developer.hashicorp.com/terraform/registry/modules/publish)
- [terraform-aws-modules](https://github.com/terraform-aws-modules)

---

## ✅ 自检清单

- [ ] 掌握模块的结构规范（main.tf、variables.tf、outputs.tf、versions.tf）
- [ ] 能开发一个完整的 VPC 模块
- [ ] 理解 Remote Backend 的重要性和配置方法
- [ ] 掌握 S3 + DynamoDB Backend 的完整配置
- [ ] 理解 backend 迁移流程（terraform init -migrate-state）
- [ ] 掌握 terraform import 和 import block 的使用
- [ ] 理解 moved block 的作用和使用场景
- [ ] 掌握 workspace 的创建、切换和使用
- [ ] 了解 workspace 和目录隔离的优劣对比
- [ ] 能编写 terraform test 测试用例
- [ ] 了解模块发布到 Registry 的要求和流程
- [ ] 理解 terraform_remote_state 跨项目数据共享
