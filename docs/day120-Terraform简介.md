# Day 120: Terraform 简介

> 📅 日期：2026-05-04
> 📖 学习主题：IaC 概念、Terraform vs CloudFormation/Pulumi、安装配置、Provider、状态文件、工作流
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 119（AWS 综合复习）

---

## 🎯 学习目标

- 理解 Infrastructure as Code（IaC）的核心理念与价值
- 掌握 Terraform 的架构设计与核心组件
- 能对比 Terraform、CloudFormation、Pulumi 的优劣
- 完成 Terraform 安装并配置第一个 Provider
- 理解状态文件（State File）的作用与管理策略
- 掌握 Terraform 标准工作流：init → plan → apply → destroy

---

## 📖 核心知识点

### 1. Infrastructure as Code（IaC）概念

#### 1.1 什么是 IaC

Infrastructure as Code 是用代码（而非手动操作）来定义、部署和管理基础设施的方法论。基础设施的配置以声明式或命令式的代码形式存储在版本控制系统中。

```
传统运维 vs IaC 对比：

┌─────────────────────────────────────────────────────────┐
│                    传统运维（ClickOps）                    │
├─────────────────────────────────────────────────────────┤
│ 1. 登录 AWS Console                                     │
│ 2. 手动点击创建 VPC                                      │
│ 3. 手动创建子网、路由表                                   │
│ 4. 手动创建 EC2 实例                                     │
│ 5. 手动配置安全组                                        │
│ 6. 重复以上步骤（生产/测试/开发）                          │
│                                                         │
│ 问题：                                                  │
│ - 不可重复（环境漂移）                                    │
│ - 不可审计（谁改了什么？）                                │
│ - 不可回滚（如何恢复？）                                  │
│ - 效率低（每次都要手动操作）                               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    IaC（Terraform）                       │
├─────────────────────────────────────────────────────────┤
│ 1. 编写 HCL 配置文件                                     │
│ 2. terraform plan → 预览变更                             │
│ 3. terraform apply → 自动创建所有资源                     │
│ 4. git commit → 版本控制                                 │
│ 5. 复用到其他环境 → terraform workspace                   │
│                                                         │
│ 优势：                                                  │
│ - 可重复（相同代码 = 相同环境）                            │
│ - 可审计（Git 历史记录所有变更）                           │
│ - 可回滚（git revert + terraform apply）                 │
│ - 高效（自动化一切）                                      │
└─────────────────────────────────────────────────────────┘
```

#### 1.2 IaC 的核心原则

| 原则 | 说明 | 实践 |
|------|------|------|
| 声明式 | 定义期望状态，而非执行步骤 | Terraform HCL 描述最终状态 |
| 版本控制 | 所有配置存储在 Git 中 | 每次变更必须提交 PR |
| 幂等性 | 多次执行结果相同 | plan → apply 可重复执行 |
| 自动化 | CI/CD 流水线驱动 | PR 触发 plan，merge 触发 apply |
| 模块化 | 可复用的组件 | Terraform Module 封装 |
| 最小权限 | 执行账号最小权限 | 专用 CI/CD IAM Role |

#### 1.3 IaC 工具分类

```
┌──────────────────────────────────────────────────────────┐
│                    IaC 工具分类                            │
├────────────────┬─────────────────────────────────────────┤
│   声明式       │   命令式                                │
│   (Declarative)│   (Imperative)                         │
│   - Terraform  │   - Pulumi (Python/Go/TS)              │
│   - CloudFormation                                      │
│   - Crossplane │   - AWS CDK                             │
├────────────────┴─────────────────────────────────────────┤
│                                                         │
│   多云工具              单云工具                          │
│   - Terraform           - CloudFormation (AWS)           │
│   - Pulumi              - Azure ARM/Bicep                │
│   - Crossplane          - Google Deployment Manager      │
│                                                         │
└──────────────────────────────────────────────────────────┘
```

### 2. Terraform 概述

#### 2.1 Terraform 是什么

Terraform 是 HashiCorp 开发的开源 IaC 工具，使用声明式配置语言（HCL）来定义和管理基础设施。它是目前业界最流行的多云 IaC 工具。

**核心特点：**
- **多云支持**：通过 Provider 支持 3000+ 云服务和平台
- **声明式语法**：HCL（HashiCorp Configuration Language）易读易写
- **执行计划**：apply 前先 plan，预览所有变更
- **资源图**：自动分析依赖关系，并行创建无依赖资源
- **状态管理**：跟踪真实基础设施与配置的映射关系

#### 2.2 Terraform 架构

```
┌───────────────────────────────────────────────────────────┐
│                    Terraform 架构                          │
│                                                           │
│  ┌─────────────┐                                          │
│  │  HCL 配置    │  ← 用户编写的 .tf 文件                  │
│  │  (.tf 文件)  │                                          │
│  └──────┬──────┘                                          │
│         │                                                 │
│  ┌──────▼──────┐                                          │
│  │  Core       │  ← Terraform 核心引擎                    │
│  │  Engine     │                                          │
│  │             │  1. 读取配置                              │
│  │  ┌───────┐  │  2. 构建资源图（Resource Graph）          │
│  │  │ Graph │  │  3. 对比状态文件（State Diff）            │
│  │  │  Walk │  │  4. 生成执行计划（Plan）                  │
│  │  └───────┘  │  5. 调用 Provider API 执行               │
│  └──────┬──────┘                                          │
│         │                                                 │
│  ┌──────┴──────────────────────────────────────┐          │
│  │              Provider Plugins                │          │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐   │          │
│  │  │ AWS  │  │Azure │  │ GCP  │  │K8s   │   │          │
│  │  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘   │          │
│  └─────┼─────────┼─────────┼─────────┼───────┘          │
│        ▼         ▼         ▼         ▼                   │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                 │
│  │ AWS  │  │Azure │  │ GCP  │  │K8s   │                 │
│  │ API  │  │ API  │  │ API  │  │ API  │                 │
│  └──────┘  └──────┘  └──────┘  └──────┘                 │
│                                                           │
│  ┌─────────────────────────────────────────┐             │
│  │       State File (terraform.tfstate)     │             │
│  │  - 资源 ID 与配置的映射关系              │             │
│  │  - 资源当前属性值与元数据                 │             │
│  │  - 资源之间的依赖关系                    │             │
│  │  - Provider 配置信息                     │             │
│  └─────────────────────────────────────────┘             │
└───────────────────────────────────────────────────────────┘
```

#### 2.3 Terraform 工作流

```
┌───────────────────────────────────────────────────────────┐
│                 Terraform 标准工作流                        │
│                                                           │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌────────┐ │
│  │  init   │───→│  plan   │───→│  apply  │───→│destroy │ │
│  └─────────┘    └─────────┘    └─────────┘    └────────┘ │
│       │              │              │              │      │
│  初始化项目     生成变更计划    执行变更计划    销毁资源    │
│  下载 Provider  预览将要       创建/修改/      删除所有    │
│  配置 Backend   创建/修改/     删除资源        管理的资源  │
│                 删除的资源                               │
│                                                           │
│  频率：每次     频率：每次     频率：每次     频率：       │
│  配置变更后     apply 前必做   确认 plan 后   仅开发/测试  │
└───────────────────────────────────────────────────────────┘
```

### 3. Terraform vs CloudFormation vs Pulumi

#### 3.1 详细对比

| 维度 | Terraform | CloudFormation | Pulumi |
|------|-----------|---------------|--------|
| **开发者** | HashiCorp | AWS | Pulumi Corp |
| **语言** | HCL | JSON/YAML | Python/Go/TS/Java/C# |
| **多云支持** | 是（3000+ Provider） | 仅 AWS | 是 |
| **状态管理** | 本地/远程 Backend | AWS 托管（Stack） | Pulumi Cloud/自托管 |
| **学习曲线** | 中等 | 低（AWS 用户） | 低（有编程经验） |
| **社区生态** | 最大 | AWS 官方 | 增长中 |
| **模块复用** | Module Registry | Nested Stack | Package Registry |
| **漂移检测** | plan 检测 | Drift Detection | preview 检测 |
| **执行计划** | terraform plan | Change Sets | pulumi preview |
| **许可证** | BSL 1.1 | Apache 2.0 | Apache 2.0 |
| **导入资源** | terraform import | aws cloudformation import | pulumi import |
| **测试框架** | terraform test | 无原生支持 | 原生单元测试 |
| **最佳场景** | 多云/IaC 标准 | 纯 AWS 环境 | 有编程背景的团队 |

#### 3.2 选型决策树

```
你需要管理多云环境吗？
    │
    ├── 是 ──→ 你的团队有编程经验吗？
    │             │
    │             ├── 是 ──→ Terraform 或 Pulumi
    │             └── 否 ──→ Terraform（HCL 更易上手）
    │
    └── 否 ──→ 仅使用 AWS？
                  │
                  ├── 是 ──→ CloudFormation 或 Terraform
                  │             │
                  │             ├── 需要跨云兼容 → Terraform
                  │             └── 仅 AWS → CloudFormation（更深度集成）
                  └── 否 ──→ Terraform
```

#### 3.3 Terraform 的优势与劣势

**优势：**
1. **多云统一管理**：一套工具管理 AWS、Azure、GCP、K8s 等
2. **庞大的社区**：Registry 上有数千个 Provider 和 Module
3. **执行计划**：apply 前看到所有变更，降低风险
4. **状态管理**：精确跟踪资源与配置的映射
5. **模块化**：可复用的 Module 系统
6. **HCL 语法**：专门为 IaC 设计，比 JSON/YAML 更易读

**劣势：**
1. **状态文件管理**：需要额外配置 remote backend
2. **HCL 学习成本**：新语言需要学习
3. **HashiCorp 许可证变更**：BSL 许可证限制商业竞品使用
4. **大规模管理**：数万资源时 plan/apply 速度变慢
5. **循环/条件**：HCL 的循环和条件表达式不如编程语言灵活

### 4. Terraform 安装与配置

#### 4.1 安装 Terraform

```bash
# 方法 1：使用包管理器（推荐）

# Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
  https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# macOS
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# 方法 2：直接下载二进制
TERRAFORM_VERSION="1.9.8"
curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
  -o terraform.zip
unzip terraform.zip
sudo mv terraform /usr/local/bin/
rm terraform.zip

# 验证安装
terraform version
# Terraform v1.9.8
# on linux_amd64
```

#### 4.2 安装 tfenv（Terraform 版本管理器）

```bash
# 安装 tfenv
git clone https://github.com/tfutils/tfenv.git ~/.tfenv
echo 'export PATH="$HOME/.tfenv/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 使用 tfenv
tfenv install 1.9.8
tfenv install 1.6.6
tfenv use 1.9.8
tfenv list
```

#### 4.3 配置 AWS Provider 认证

```bash
# 方法 1：环境变量（推荐用于 CI/CD）
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-east-1"

# 方法 2：AWS CLI 配置
aws configure
# 或使用 SSO
aws sso login --profile my-sso-profile

# 方法 3：在 Terraform 中配置（不推荐硬编码密钥）
# provider "aws" {
#   region     = "us-east-1"
#   access_key = "xxx"  # 永远不要这样做！
#   secret_key = "xxx"  # 永远不要这样做！
# }
```

### 5. Provider 详解

#### 5.1 Provider 是什么

Provider 是 Terraform 与外部 API 交互的插件。每个 Provider 负责管理特定云平台或服务的资源类型（Resource）和数据源（Data Source）。

```
┌─────────────────────────────────────────────────────────┐
│                   Provider 架构                          │
│                                                         │
│  Terraform Core                                         │
│       │                                                 │
│       │ gRPC 协议通信                                    │
│       │                                                 │
│  ┌────┴─────────────────────────────────────────┐       │
│  │              Provider Plugin                  │       │
│  │                                               │       │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐      │       │
│  │  │Resource │  │  Data   │  │Function │      │       │
│  │  │ Types   │  │ Sources │  │  Types  │      │       │
│  │  └─────────┘  └─────────┘  └─────────┘      │       │
│  │                                               │       │
│  │  API Client ←→ Cloud API                      │       │
│  └───────────────────────────────────────────────┘       │
│                                                         │
│  常用 Provider：                                         │
│  - hashicorp/aws         (AWS 云服务)                    │
│  - hashicorp/azurerm     (Azure 云服务)                  │
│  - hashicorp/google      (GCP 云服务)                    │
│  - hashicorp/kubernetes  (Kubernetes 集群)               │
│  - hashicorp/helm        (Helm Charts)                  │
│  - hashicorp/random      (随机值生成)                    │
│  - hashicorp/tls         (TLS 证书)                     │
│  - hashicorp/local       (本地文件操作)                   │
│  - grafana/grafana       (Grafana 监控)                  │
│  - datadog/datadog       (Datadog 监控)                  │
└─────────────────────────────────────────────────────────┘
```

#### 5.2 Provider 配置语法

```hcl
# versions.tf - 定义 Provider 版本约束
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # >= 5.0.0, < 6.0.0
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

# providers.tf - 配置 AWS Provider
provider "aws" {
  region = "us-east-1"

  # 使用命名 Profile（本地开发时）
  # profile = "my-profile"

  # 默认标签 — 所有资源都会自动添加这些标签
  default_tags {
    tags = {
      Environment = "production"
      ManagedBy   = "terraform"
      Project     = "sre-learning"
    }
  }

  # 假设角色（跨账户管理场景）
  # assume_role {
  #   role_arn = "arn:aws:iam::123456789012:role/TerraformRole"
  # }
}

# 多区域 Provider（使用别名）
provider "aws" {
  alias  = "us_west_2"
  region = "us-west-2"
}

# 使用别名 Provider 创建资源
resource "aws_s3_bucket" "replica" {
  provider = aws.us_west_2
  bucket   = "my-replica-bucket"
}
```

#### 5.3 Provider 版本约束语法

```hcl
# 版本约束操作符
# =  1.0.0    精确版本（仅此版本）
# != 1.0.0    排除此版本
# >  1.0.0    大于指定版本
# >= 1.0.0    大于等于指定版本
# <  2.0.0    小于指定版本
# <= 1.5.0    小于等于指定版本
# ~> 1.0      乐观约束（>= 1.0, < 2.0）—— 推荐
# ~> 1.5      乐观约束（>= 1.5, < 2.0）
# ~> 1.5.2    乐观约束（>= 1.5.2, < 1.6.0）

# 推荐用法：
version = "~> 5.0"   # 允许 5.x 的任何版本，不允许 6.0
version = ">= 1.9.0" # 允许 1.9.0 及以上任何版本
```

### 6. 状态文件（State File）深入解析

#### 6.1 状态文件的作用

状态文件是 Terraform 的核心概念。它维护了配置文件（.tf）与真实基础设施（云资源）之间的映射关系。

```
┌─────────────────────────────────────────────────────────┐
│                状态文件的核心作用                          │
│                                                         │
│  ┌──────────────┐        ┌──────────────┐               │
│  │  HCL 配置    │        │  真实基础设施  │               │
│  │  (.tf 文件)  │        │  (云资源)     │               │
│  │              │        │              │               │
│  │ resource "   │        │ EC2: i-abc   │               │
│  │  aws_instance│        │ VPC: vpc-xyz │               │
│  │  "web" {     │        │ SG: sg-123   │               │
│  │   ...        │        │ ...          │               │
│  │ }            │        │              │               │
│  └──────┬───────┘        └──────┬───────┘               │
│         │                       │                       │
│         │    ┌──────────────┐   │                       │
│         └───→│  State File  │←──┘                       │
│              │ (terraform.  │                           │
│              │  tfstate)    │                           │
│              │              │                           │
│              │ web → i-abc  │                           │
│              │ main → vpc-x │                           │
│              └──────────────┘                           │
│                                                         │
│  状态文件记录：                                          │
│  1. 资源地址 → 资源 ID 映射（aws_instance.web → i-xxx）  │
│  2. 资源的当前属性值（instance_type, ami 等）             │
│  3. 资源之间的依赖关系（depends_on）                     │
│  4. Provider 配置的元数据                                │
│  5. 输出值（outputs）                                   │
└─────────────────────────────────────────────────────────┘
```

#### 6.2 状态文件操作命令

```bash
# 查看状态
terraform state list                        # 列出所有资源
terraform state show aws_instance.web       # 查看资源详情

# 状态操作（谨慎使用！）
terraform state mv aws_instance.web aws_instance.app    # 重命名/移动资源
terraform state rm aws_instance.old                     # 从状态中移除（不删除真实资源）
terraform state pull                                    # 拉取远程状态到 stdout
terraform state push terraform.tfstate                  # 推送本地状态到远程

# 导入已有资源到状态
terraform import aws_instance.web i-1234567890abcdef0

# 刷新状态（从云平台读取最新状态）
terraform apply -refresh-only

# 强制重建资源
terraform apply -replace=aws_instance.web
```

#### 6.3 状态文件安全

**状态文件包含敏感信息！** 它可能包含数据库密码、API 密钥、证书私钥等。

**安全最佳实践：**

```hcl
# 1. 使用 remote backend（不要将状态存储在本地）
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true               # S3 服务端加密
    dynamodb_table = "terraform-lock"    # 状态锁表
  }
}

# 2. 敏感输出标记
output "db_password" {
  value     = aws_db_instance.main.password
  sensitive = true   # 不在 plan/apply 输出中明文显示
}

# 3. .gitignore 必须排除
# *.tfstate
# *.tfstate.backup
# *.tfstate.*.backup
# .terraform/
# .terraform.lock.hcl
# terraform.tfvars
# *.auto.tfvars
```

### 7. 第一个 Terraform 项目

#### 7.1 推荐的项目结构

```
my-first-terraform/
├── main.tf            # 主要资源定义
├── variables.tf       # 输入变量声明
├── outputs.tf         # 输出值定义
├── providers.tf       # Provider 配置
├── versions.tf        # Terraform 和 Provider 版本约束
├── terraform.tfvars   # 变量值（不提交到 Git）
├── data.tf            # 数据源定义（可选）
├── locals.tf          # 本地值定义（可选）
└── .gitignore         # Git 忽略规则
```

#### 7.2 完整示例：创建 EC2 实例

```hcl
# versions.tf
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

```hcl
# providers.tf
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = "sre-learning"
    }
  }
}
```

```hcl
# variables.tf
variable "aws_region" {
  description = "AWS 区域"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "环境名称"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "环境必须是 dev、staging 或 prod 之一。"
  }
}

variable "instance_type" {
  description = "EC2 实例类型"
  type        = string
  default     = "t3.micro"
}
```

```hcl
# main.tf

# 查找最新的 Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
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

# 创建安全组
resource "aws_security_group" "web" {
  name_prefix = "${var.environment}-web-"
  description = "Security group for web server"

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

  lifecycle {
    create_before_destroy = true
  }
}

# 创建 EC2 实例
resource "aws_instance" "web" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.web.id]

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd
    echo "<h1>Hello from Terraform!</h1>" > /var/www/html/index.html
  EOF

  tags = {
    Name = "${var.environment}-web-server"
  }
}
```

```hcl
# outputs.tf
output "instance_id" {
  description = "EC2 实例 ID"
  value       = aws_instance.web.id
}

output "public_ip" {
  description = "EC2 公有 IP 地址"
  value       = aws_instance.web.public_ip
}

output "ami_id" {
  description = "使用的 AMI ID"
  value       = data.aws_ami.amazon_linux.id
}
```

#### 7.3 执行 Terraform 工作流

```bash
# 1. 初始化（下载 Provider 插件、配置 Backend）
terraform init
# Initializing the backend...
# Initializing provider plugins...
# - Finding hashicorp/aws versions matching "~> 5.0"...
# - Installing hashicorp/aws v5.78.0...
# Terraform has been successfully initialized!

# 2. 格式化代码
terraform fmt -recursive

# 3. 验证配置语法
terraform validate
# Success! The configuration is valid.

# 4. 生成执行计划
terraform plan -out=tfplan
# Terraform will perform the following actions:
#   # aws_instance.web will be created
#   + resource "aws_instance" "web" {
#       + ami           = "ami-0abcdef1234567890"
#       + instance_type = "t3.micro"
#     }
#   # aws_security_group.web will be created
#   + resource "aws_security_group" "web" {
#       + name_prefix = "dev-web-"
#     }
# Plan: 2 to add, 0 to change, 0 to destroy.

# 5. 执行变更
terraform apply tfplan

# 6. 查看输出
terraform output
# instance_id = "i-0abcdef1234567890"
# public_ip   = "54.123.45.67"

# 7. 销毁资源（仅开发/测试环境！生产环境禁止！）
terraform destroy
```

### 8. Terraform CLI 常用命令速查

```bash
# ── 初始化 ──
terraform init                   # 初始化工作目录
terraform init -upgrade          # 升级 Provider 到最新兼容版本
terraform init -migrate-state    # 迁移状态到新的 backend
terraform init -reconfigure      # 重新配置 backend

# ── 格式化与验证 ──
terraform fmt                    # 格式化当前目录的 .tf 文件
terraform fmt -recursive         # 递归格式化子目录
terraform fmt -check             # 检查格式是否正确（CI 用）
terraform validate               # 验证配置语法

# ── 计划与应用 ──
terraform plan                   # 生成执行计划
terraform plan -out=tfplan       # 保存计划到文件
terraform plan -target=X         # 仅计划特定资源
terraform plan -destroy          # 计划销毁操作
terraform apply                  # 应用变更（交互确认）
terraform apply tfplan           # 应用已保存的计划
terraform apply -auto-approve    # 自动确认（CI/CD 用）
terraform apply -parallelism=20  # 调整并行度（默认 10）

# ── 状态管理 ──
terraform state list             # 列出状态中的所有资源
terraform state show <addr>      # 显示资源详细信息
terraform state mv <src> <dst>   # 移动/重命名资源
terraform state rm <addr>        # 从状态中移除资源
terraform import <addr> <id>     # 导入已有资源

# ── 工作空间 ──
terraform workspace list         # 列出所有工作空间
terraform workspace new <name>   # 创建新工作空间
terraform workspace select <n>   # 切换工作空间
terraform workspace delete <n>   # 删除工作空间

# ── 调试与输出 ──
terraform console                # 交互式控制台
terraform graph                  # 生成依赖关系图（DOT 格式）
terraform output                 # 显示所有输出值
terraform output -json           # JSON 格式输出

# ── 销毁 ──
terraform destroy                # 销毁所有管理的资源
terraform destroy -target=X      # 仅销毁特定资源
```

---

## 💻 实战练习

### 练习 1：安装 Terraform 并创建第一个资源

**目标：** 在本地安装 Terraform 并创建一个 S3 Bucket

```bash
# 1. 安装 Terraform（选择适合你系统的方式）
# 2. 创建项目目录
mkdir -p ~/terraform-lab/day120 && cd ~/terraform-lab/day120

# 3. 创建 main.tf
cat > main.tf << 'EOF'
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "lab" {
  bucket = "sre-lab-${random_id.bucket_suffix.hex}"
}

output "bucket_name" {
  value = aws_s3_bucket.lab.bucket
}
EOF

# 4. 执行完整工作流
terraform init
terraform plan
terraform apply -auto-approve

# 5. 验证
terraform state list
terraform output

# 6. 清理
terraform destroy -auto-approve
```

### 练习 2：状态文件操作

**目标：** 熟悉状态文件的查看和操作命令

```bash
# 1. 使用练习 1 的项目，重新创建资源
terraform apply -auto-approve

# 2. 查看状态文件原始内容
cat terraform.tfstate | jq '.resources[] | {type, name, instances}'

# 3. 使用 state 命令操作
terraform state list
terraform state show aws_s3_bucket.lab

# 4. 从状态中移除资源（不删除真实资源）
terraform state rm aws_s3_bucket.lab
terraform state list  # 应该为空

# 5. 重新导入资源
terraform import aws_s3_bucket.lab sre-lab-xxxxxxxx  # 替换为实际 bucket 名
terraform state list  # 应该重新显示资源

# 6. 清理
terraform destroy -auto-approve
```

### 练习 3：Provider 多区域配置

**目标：** 使用 Provider 别名在多个 AWS 区域创建资源

```hcl
# main.tf
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  alias  = "east"
  default_tags {
    tags = { ManagedBy = "terraform", Region = "us-east-1" }
  }
}

provider "aws" {
  region = "us-west-2"
  alias  = "west"
  default_tags {
    tags = { ManagedBy = "terraform", Region = "us-west-2" }
  }
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "east" {
  provider = aws.east
  bucket   = "sre-lab-east-${random_id.suffix.hex}"
}

resource "aws_s3_bucket" "west" {
  provider = aws.west
  bucket   = "sre-lab-west-${random_id.suffix.hex}"
}

output "east_bucket" { value = aws_s3_bucket.east.bucket }
output "west_bucket" { value = aws_s3_bucket.west.bucket }
```

---

## 🎯 面试题精选

### 1. 什么是 IaC？它解决了什么问题？

**参考答案：**
Infrastructure as Code（IaC）是用代码定义和管理基础设施的方法。它解决了：
- **环境不一致**：相同代码产生相同环境，消除"在我机器上能跑"的问题
- **手动操作风险**：自动化替代人工操作，减少人为错误
- **不可审计**：代码版本控制，所有变更可追溯
- **效率低下**：自动化部署，分钟级创建完整环境
- **不可重复**：代码可复用，快速创建新环境

### 2. Terraform 的状态文件是什么？为什么需要它？

**参考答案：**
状态文件（terraform.tfstate）是 Terraform 用来映射配置文件与真实基础设施之间关系的 JSON 文件。需要它的原因：
1. **资源映射**：记录 `aws_instance.web` 对应的真实资源 ID `i-xxx`
2. **变更检测**：对比配置和状态，确定需要创建/修改/删除的资源
3. **元数据存储**：记录资源的依赖关系、Provider 配置等
4. **性能优化**：避免每次都调用 API 查询所有资源

**生产环境最佳实践：** 使用 S3 + DynamoDB 作为 remote backend，启用加密和状态锁。

### 3. `terraform plan` 和 `terraform apply` 的区别是什么？

**参考答案：**
- `terraform plan` 是只读操作，生成执行计划显示将要进行的变更（创建/修改/删除），不实际修改基础设施
- `terraform apply` 执行 plan 中的变更，实际创建/修改/删除云资源
- **最佳实践**：总是先 plan 再 apply；CI/CD 中 plan 作为 PR 检查，apply 在 merge 后执行

### 4. 如何处理 Terraform 状态锁？

**参考答案：**
状态锁防止多人同时修改状态导致冲突。实现方式：
- **S3 backend**：使用 DynamoDB 表实现分布式锁
- **Terraform Cloud**：内置状态锁机制
- **手动解锁**：`terraform force-unlock <LOCK_ID>`（仅紧急情况使用）

```hcl
terraform {
  backend "s3" {
    bucket         = "terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
```

### 5. Provider 的版本约束 `~>` 是什么意思？

**参考答案：**
`~>` 是"乐观约束运算符"（Pessimistic Constraint Operator）：
- `~> 5.0` 等价于 `>= 5.0.0, < 6.0.0`（允许 minor 和 patch 更新）
- `~> 5.1` 等价于 `>= 5.1.0, < 6.0.0`
- `~> 5.1.2` 等价于 `>= 5.1.2, < 5.2.0`（仅允许 patch 更新）

**推荐：** 使用 `~> 5.0` 允许安全更新，避免大版本升级导致不兼容。

### 6. 如何导入已有的基础设施到 Terraform 管理？

**参考答案：**
```bash
# 步骤 1：编写匹配已有资源的 HCL 配置
# 步骤 2：导入到状态
terraform import aws_instance.existing i-1234567890abcdef0
# 步骤 3：运行 plan 检查差异，调整配置使其与实际资源匹配
terraform plan
```

Terraform 1.5+ 还支持 import block 语法：
```hcl
import {
  to = aws_instance.existing
  id = "i-1234567890abcdef0"
}
```

### 7. Terraform Cloud 和本地执行有什么区别？

**参考答案：**

| 维度 | 本地执行 | Terraform Cloud |
|------|---------|----------------|
| 状态存储 | 本地文件或自配 remote | 托管存储 |
| 状态锁 | 需自建 DynamoDB | 内置 |
| 执行环境 | 本地机器 | 远程执行器 |
| 协作 | 手动协调 | 内置协作功能 |
| 策略执行 | 需外部工具（tfsec/checkov） | Sentinel/OPA 集成 |
| 密钥管理 | 手动管理 | 内置变量管理 |
| 成本 | 免费 | 免费层 + 付费 |

### 8. 为什么不应该将状态文件提交到 Git？

**参考答案：**
1. **敏感信息泄露**：状态文件包含资源属性，可能含有密码、密钥等敏感数据
2. **并发冲突**：多人同时修改会导致状态覆盖和数据丢失
3. **文件大小**：大型基础设施的状态文件可能达到 MB 级别
4. **正确做法**：使用 remote backend（如 S3）存储状态，配合 DynamoDB 实现状态锁

---

## 📚 深入阅读

- [Terraform 官方文档](https://developer.hashicorp.com/terraform/docs)
- [Terraform Registry](https://registry.terraform.io/)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [Terraform Up & Running (Yevgeniy Brikman)](https://www.terraformupandrunning.com/)
- [AWS Provider 文档](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Language Guide](https://developer.hashicorp.com/terraform/language)

---

## ✅ 自检清单

- [ ] 理解 IaC 的核心理念与价值（声明式、版本控制、幂等性、自动化）
- [ ] 能对比 Terraform、CloudFormation、Pulumi 的优劣势和适用场景
- [ ] 成功安装 Terraform 并验证 `terraform version`
- [ ] 理解 Provider 的作用、版本约束语法和别名机制
- [ ] 理解状态文件的作用、安全要求和操作命令
- [ ] 掌握 terraform init / plan / apply / destroy 完整工作流
- [ ] 能创建包含 resource、data source、variable、output 的基本配置
- [ ] 理解 remote backend 的重要性（S3 + DynamoDB）
- [ ] 掌握 terraform state 常用操作（list、show、mv、rm、import）
- [ ] 知道 .gitignore 应该排除哪些 Terraform 文件
- [ ] 理解 Provider 别名的使用场景（多区域部署）
