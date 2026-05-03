# Day 121: Terraform 基础

> 📅 日期：2026-05-04
> 📖 学习主题：HCL 语法、资源/数据源/变量/输出、表达式、函数、provisioner、meta-arguments
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 120（Terraform 简介）

---

## 🎯 学习目标

- 掌握 HCL（HashiCorp Configuration Language）的完整语法
- 熟练使用 resource、data source、variable、output 四大核心构建块
- 掌握 Terraform 表达式和内置函数
- 理解 provisioner 的使用场景和最佳实践
- 掌握 meta-arguments（count、for_each、lifecycle、depends_on、provider）

---

## 📖 核心知识点

### 1. HCL 语法基础

#### 1.1 HCL 语法概览

HCL（HashiCorp Configuration Language）是 Terraform 的配置语言，结合了 JSON 的结构化和传统配置文件的可读性。

```
┌─────────────────────────────────────────────────────────┐
│                    HCL 语法元素                           │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Block     │  │ Argument    │  │ Expression  │     │
│  │   (块)      │  │  (参数)     │  │  (表达式)    │     │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤     │
│  │ resource    │  │ key = value │  │ var.x       │     │
│  │ variable    │  │             │  │ local.x     │     │
│  │ data        │  │             │  │ count.index │     │
│  │ output      │  │             │  │ for_each.key│     │
│  │ provider    │  │             │  │ element()   │     │
│  │ module      │  │             │  │ lookup()    │     │
│  │ locals      │  │             │  │ conditional │     │
│  │ terraform   │  │             │  │ splat [*]   │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Types      │  │  Comments   │  │  Heredoc    │     │
│  │  (类型)     │  │  (注释)     │  │  (多行字符串)│     │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤     │
│  │ string      │  │ # 单行      │  │ <<-EOF      │     │
│  │ number      │  │ // 单行     │  │   内容       │     │
│  │ bool        │  │ /* 多行 */  │  │ EOF         │     │
│  │ list        │  │             │  │             │     │
│  │ map         │  │             │  │             │     │
│  │ object      │  │             │  │             │     │
│  │ set         │  │             │  │             │     │
│  │ tuple       │  │             │  │             │     │
│  │ any         │  │             │  │             │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

#### 1.2 HCL 基本语法

```hcl
# ═══════════════════════════════════════════
# Block（块）语法
# ═══════════════════════════════════════════

# 块的基本结构：<block_type> "<block_label>" "<block_label>" { ... }
resource "aws_instance" "web" {       # 两个标签：类型 + 名称
  ami           = "ami-12345"         # Argument（参数）
  instance_type = "t3.micro"
}

# 不同类型的块
variable "region" {                   # 一个标签
  type    = string
  default = "us-east-1"
}

provider "aws" {                      # 一个标签
  region = var.region
}

data "aws_ami" "ubuntu" {             # 两个标签
  most_recent = true
  owners      = ["099720109477"]
}

module "vpc" {                        # 一个标签
  source = "./modules/vpc"
}

output "instance_ip" {                # 一个标签
  value = aws_instance.web.public_ip
}

locals {                              # 无标签
  env = "production"
}

# ═══════════════════════════════════════════
# Argument（参数）语法
# ═══════════════════════════════════════════

# 简单赋值
instance_type = "t3.micro"

# 复杂值
tags = {
  Name        = "web-server"
  Environment = "production"
}

# 列表
availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]

# ═══════════════════════════════════════════
# 注释
# ═══════════════════════════════════════════

# 这是单行注释（推荐）
// 这也是单行注释
/* 这是
   多行注释 */

# ═══════════════════════════════════════════
# Heredoc 多行字符串
# ═══════════════════════════════════════════

# 标准 Heredoc（保留缩进）
user_data = <<-EOF
  #!/bin/bash
  yum update -y
  yum install -y httpd
  systemctl start httpd
EOF

# JSON Heredoc
policy = jsonencode({
  Version = "2012-10-17"
  Statement = [
    {
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }
  ]
})
```

#### 1.3 数据类型详解

```hcl
# ═══════════════════════════════════════════
# 基本类型
# ═══════════════════════════════════════════

# string（字符串）
variable "name" {
  type    = string
  default = "hello-world"
}

# number（数字 — 整数和浮点数）
variable "count" {
  type    = number
  default = 3
}

# bool（布尔值）
variable "enabled" {
  type    = bool
  default = true
}

# ═══════════════════════════════════════════
# 复合类型
# ═══════════════════════════════════════════

# list（列表 — 有序集合）
variable "availability_zones" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# map（映射 — 键值对）
variable "tags" {
  type    = map(string)
  default = {
    Environment = "dev"
    Team        = "sre"
  }
}

# set（集合 — 无序无重复）
variable "allowed_ports" {
  type    = set(number)
  default = [80, 443, 8080]
}

# object（对象 — 结构化数据）
variable "server_config" {
  type = object({
    instance_type = string
    ami_id        = string
    disk_size     = number
    encrypted     = bool
    tags          = map(string)
  })
  default = {
    instance_type = "t3.micro"
    ami_id        = "ami-12345"
    disk_size     = 50
    encrypted     = true
    tags          = { Name = "default" }
  }
}

# tuple（元组 — 有序，元素类型可不同）
variable "mixed_list" {
  type    = tuple([string, number, bool])
  default = ["hello", 42, true]
}

# any（任意类型 — 不推荐过度使用）
variable "anything" {
  type    = any
  default = "flexible"
}
```

### 2. Resource（资源）

#### 2.1 资源语法

资源是 Terraform 配置的核心，每个 resource 块定义一个基础设施对象。

```hcl
# 基本语法
resource "<PROVIDER_TYPE>" "<LOCAL_NAME>" {
  # 参数
  argument1 = value1
  argument2 = value2

  # 嵌套块
  nested_block {
    nested_argument = value
  }

  # 生命周期规则
  lifecycle {
    create_before_destroy = true
  }
}
```

#### 2.2 完整的资源示例

```hcl
# ── EC2 实例 ──
resource "aws_instance" "web" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  key_name               = aws_key_pair.deployer.key_name
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
    encrypted   = true
  }

  ebs_block_device {
    device_name = "/dev/sdf"
    volume_size = 100
    volume_type = "gp3"
    encrypted   = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # IMDSv2
    http_put_response_hop_limit = 1
  }

  monitoring = true  # 详细监控

  user_data = base64encode(<<-EOF
    #!/bin/bash
    yum update -y
    yum install -y amazon-cloudwatch-agent
  EOF
  )

  tags = {
    Name        = "${var.environment}-web-server"
    Environment = var.environment
  }
}

# ── RDS 实例 ──
resource "aws_db_instance" "main" {
  identifier     = "${var.environment}-mysql"
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.r6g.large"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "appdb"
  username = "admin"
  password = var.db_password  # 从变量传入，不硬编码

  multi_az               = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  skip_final_snapshot       = false
  final_snapshot_identifier = "${var.environment}-mysql-final"
  deletion_protection       = var.environment == "prod" ? true : false

  performance_insights_enabled = true

  tags = {
    Name        = "${var.environment}-mysql"
    Environment = var.environment
  }
}
```

#### 2.3 资源地址（Resource Address）

```
资源地址格式：<RESOURCE_TYPE>.<LOCAL_NAME>[<INDEX/KEY>]

示例：
  aws_instance.web                    # 单个资源
  aws_instance.web[0]                 # count 创建的第一个
  aws_instance.web["us-east-1a"]      # for_each 创建的
  module.vpc.aws_subnet.public        # 模块内的资源
  module.vpc.aws_subnet.public[0]     # 模块内 count 创建的
```

### 3. Data Source（数据源）

#### 3.1 数据源的作用

数据源用于从已有基础设施或外部数据中查询信息，不创建任何资源。

```hcl
# ═══════════════════════════════════════════
# 查询最新 AMI
# ═══════════════════════════════════════════
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

# 使用数据源
resource "aws_instance" "web" {
  ami = data.aws_ami.amazon_linux.id  # 引用数据源
}

# ═══════════════════════════════════════════
# 查询当前 AWS 账户信息
# ═══════════════════════════════════════════
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# 使用
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
}

# ═══════════════════════════════════════════
# 查询 VPC 和子网
# ═══════════════════════════════════════════
data "aws_vpc" "existing" {
  filter {
    name   = "tag:Name"
    values = ["production-vpc"]
  }
}

data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.existing.id]
  }

  filter {
    name   = "tag:Tier"
    values = ["private"]
  }
}

# ═══════════════════════════════════════════
# 查询 Secrets Manager
# ═══════════════════════════════════════════
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "prod/database/password"
}

# ═══════════════════════════════════════════
# 查询 S3 对象
# ═══════════════════════════════════════════
data "aws_s3_object" "config" {
  bucket = "my-config-bucket"
  key    = "app/config.json"
}

# ═══════════════════════════════════════════
# 通用数据源
# ═══════════════════════════════════════════

# 读取本地文件
data "local_file" "script" {
  filename = "${path.module}/scripts/init.sh"
}

# 解析 JSON 文件
data "local_file" "config" {
  filename = "${path.module}/config.json"
}

locals {
  config = jsondecode(data.local_file.config.content)
}

# 生成 SSH 密钥
data "tls_public_key" "example" {
  private_key_pem = file("~/.ssh/id_rsa")
}
```

### 4. Variable（变量）

#### 4.1 变量声明与使用

```hcl
# ═══════════════════════════════════════════
# 变量声明
# ═══════════════════════════════════════════

variable "environment" {
  description = "部署环境名称"
  type        = string
  default     = "dev"

  # 验证规则
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "环境必须是 dev、staging 或 prod 之一。"
  }
}

variable "instance_count" {
  description = "EC2 实例数量"
  type        = number
  default     = 2

  validation {
    condition     = var.instance_count >= 1 && var.instance_count <= 10
    error_message = "实例数量必须在 1-10 之间。"
  }
}

variable "enable_monitoring" {
  description = "是否启用监控"
  type        = bool
  default     = true
}

variable "tags" {
  description = "资源标签"
  type        = map(string)
  default     = {}
}

variable "db_password" {
  description = "数据库密码"
  type        = string
  sensitive   = true  # 敏感值，不在输出中显示
  # 不设置 default，强制要求传入
}

# ═══════════════════════════════════════════
# 变量赋值方式（优先级从低到高）
# ═══════════════════════════════════════════

# 1. default 值（最低优先级）
# variable "x" { default = "default_value" }

# 2. terraform.tfvars 文件
# environment = "prod"
# instance_count = 3

# 3. *.auto.tfvars 文件（按文件名字母排序）
# auto.tfvars 内容：
# environment = "staging"

# 4. 环境变量
# export TF_VAR_environment="prod"

# 5. -var 命令行参数
# terraform apply -var="environment=prod"

# 6. -var-file 命令行参数
# terraform apply -var-file="prod.tfvars"

# 7. 交互式输入（无默认值且未赋值时）
# Terraform 会提示输入

# ═══════════════════════════════════════════
# 使用变量
# ═══════════════════════════════════════════

resource "aws_instance" "web" {
  count         = var.instance_count
  instance_type = "t3.micro"
  monitoring    = var.enable_monitoring

  tags = merge(var.tags, {
    Name        = "${var.environment}-web-${count.index + 1}"
    Environment = var.environment
  })
}
```

#### 4.2 Locals（本地值）

```hcl
locals {
  # 简单值
  environment = "production"
  region      = "us-east-1"

  # 计算值
  name_prefix = "${local.environment}-${local.region}"

  # 复杂映射
  instance_types = {
    dev     = "t3.micro"
    staging = "t3.small"
    prod    = "t3.medium"
  }

  # 合并标签
  common_tags = {
    Environment = local.environment
    ManagedBy   = "terraform"
    Project     = "sre-platform"
    CostCenter  = "engineering"
  }

  # 条件值
  is_prod = local.environment == "prod"

  # 动态计算
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

# 使用本地值
resource "aws_instance" "web" {
  instance_type = local.instance_types[var.environment]
  tags          = local.common_tags
}
```

### 5. Output（输出）

#### 5.1 输出语法

```hcl
# ── 基本输出 ──
output "instance_id" {
  description = "EC2 实例 ID"
  value       = aws_instance.web.id
}

# ── 敏感输出（不显示在 CLI 输出中）──
output "db_password" {
  description = "数据库密码"
  value       = aws_db_instance.main.password
  sensitive   = true
}

# ── 依赖条件输出（仅在条件满足时输出）──
output "public_ip" {
  description = "公有 IP（仅在有公网 IP 时）"
  value       = aws_instance.web.public_ip
  depends_on  = [aws_instance.web]  # 确保资源创建完成
}

# ── 复杂输出 ──
output "vpc_info" {
  description = "VPC 信息"
  value = {
    vpc_id     = aws_vpc.main.id
    cidr_block = aws_vpc.main.cidr_block
    subnet_ids = aws_subnet.private[*].id
  }
}

# ── 使用输出 ──
# terraform output                    # 显示所有输出
# terraform output instance_id        # 显示特定输出
# terraform output -json              # JSON 格式
# terraform output -raw instance_id   # 纯文本（无引号）
```

### 6. Expression（表达式）

#### 6.1 条件表达式

```hcl
# 三元运算符
resource "aws_instance" "web" {
  instance_type = var.environment == "prod" ? "t3.medium" : "t3.micro"
}

# 复杂条件
resource "aws_db_instance" "main" {
  deletion_protection = var.environment == "prod" ? true : false
  multi_az            = var.environment == "prod" ? true : false

  # 按环境选择实例类型
  instance_class = (
    var.environment == "prod" ? "db.r6g.large" :
    var.environment == "staging" ? "db.r6g.medium" :
    "db.t3.micro"
  )
}
```

#### 6.2 for 表达式

```hcl
# ── 列表转换 ──
locals {
  # 转换为大写
  upper_names = [for name in var.names : upper(name)]
  # ["ALICE", "BOB", "CHARLIE"]

  # 带条件过滤
  prod_servers = [for s in var.servers : s.name if s.environment == "prod"]

  # 转换为映射
  server_map = { for s in var.servers : s.name => s }
  # { "web-1" = { name = "web-1", type = "t3.micro" }, ... }
}

# ── 映射转换 ──
locals {
  # 转换值
  upper_tags = { for k, v in var.tags : k => upper(v) }

  # 过滤
  non_empty_tags = { for k, v in var.tags : k => v if v != "" }

  # 反转映射
  inverted = { for k, v in var.tags : v => k }
}
```

#### 6.3 Splat 表达式

```hcl
# Splat 表达式用于简化列表访问

# 等价写法
output "instance_ids" {
  value = aws_instance.web[*].id         # splat 表达式
  # 等价于
  # value = [for i in aws_instance.web : i.id]
}

# 嵌套 splat
output "eni_ids" {
  value = aws_instance.web[*].primary_network_interface_id
}
```

#### 6.4 动态块（Dynamic Block）

```hcl
# 当需要根据变量动态生成嵌套块时使用

variable "ingress_rules" {
  type = list(object({
    port        = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))
  default = [
    {
      port        = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTP"
    },
    {
      port        = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS"
    }
  ]
}

resource "aws_security_group" "web" {
  name_prefix = "web-"
  description = "Web server security group"

  dynamic "ingress" {
    for_each = var.ingress_rules
    content {
      description = ingress.value.description
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### 7. Function（函数）

#### 7.1 常用内置函数

```hcl
# ═══════════════════════════════════════════
# 字符串函数
# ═══════════════════════════════════════════

# 格式化
format("Hello, %s! You are %d years old.", "Alice", 30)
# "Hello, Alice! You are 30 years old."

format("%05d", 42)
# "00042"

# 替换
replace("hello-world", "-", "_")
# "hello_world"

# 分割
split(",", "a,b,c")
# ["a", "b", "c"]

# 连接
join(", ", ["a", "b", "c"])
# "a, b, c"

# 大小写
upper("hello")    # "HELLO"
lower("HELLO")    # "hello"
title("hello")    # "Hello"

# 去除空白
trimspace("  hello  ")   # "hello"
trim("!!hello!!", "!")   # "hello"

# 包含检查
contains(["a", "b", "c"], "b")   # true

# 子串
substr("hello world", 0, 5)   # "hello"

# 正则匹配
regex("^([a-z]+)-([0-9]+)$", "web-123")
# { "1" = "web", "2" = "123" }

# ═══════════════════════════════════════════
# 数字函数
# ═══════════════════════════════════════════

min(1, 2, 3)    # 1
max(1, 2, 3)    # 3
ceil(4.1)       # 5
floor(4.9)      # 4
abs(-5)         # 5
log(100, 10)    # 2.0
pow(2, 3)       # 8
parseint("FF", 16)  # 255

# ═══════════════════════════════════════════
# 集合函数
# ═══════════════════════════════════════════

length(["a", "b", "c"])       # 3
length("hello")                # 5

# 合并列表
concat(["a", "b"], ["c", "d"])   # ["a", "b", "c", "d"]

# 去重
distinct(["a", "b", "a", "c"])   # ["a", "b", "c"]

# 排序
sort(["c", "a", "b"])            # ["a", "b", "c"]

# 切片
slice(["a", "b", "c", "d"], 1, 3)   # ["b", "c"]

# 元素访问
element(["a", "b", "c"], 1)          # "b"
index(["a", "b", "c"], "b")          # 1

# 合并映射
merge({ a = 1, b = 2 }, { b = 3, c = 4 })   # { a = 1, b = 3, c = 4 }

# 查找
lookup({ a = "one", b = "two" }, "a", "default")   # "one"
lookup({ a = "one", b = "two" }, "c", "default")   # "default"

# 键值转换
keys({ a = 1, b = 2 })     # ["a", "b"]
values({ a = 1, b = 2 })   # [1, 2]

# 集合操作
setintersection(["a", "b", "c"], ["b", "c", "d"])   # ["b", "c"]
setunion(["a", "b"], ["b", "c"])                     # ["a", "b", "c"]
setsubtract(["a", "b", "c"], ["b"])                   # ["a", "c"]

# ═══════════════════════════════════════════
# 编码函数
# ═══════════════════════════════════════════

# JSON
jsonencode({ hello = "world" })          # '{"hello":"world"}'
jsondecode("{\"hello\":\"world\"}")       # { hello = "world" }

# YAML
yamlencode({ hello = "world" })          # "hello: world\n"

# Base64
base64encode("hello")                    # "aGVsbG8="
base64decode("aGVsbG8=")                 # "hello"

# URL
urlencode("hello world")                 # "hello%20world"

# CSV
csvdecode("a,b\n1,2\n3,4")              # [{a="1",b="2"}, {a="3",b="4"}]

# ═══════════════════════════════════════════
# 文件系统函数
# ═══════════════════════════════════════════

file("${path.module}/templates/init.sh")           # 读取文件内容
fileexists("${path.module}/config.json")            # 检查文件是否存在
templatefile("${path.module}/templates/init.tpl", { # 模板渲染
  hostname = "web-01"
  ip       = "10.0.1.10"
})
filebase64("${path.module}/files/cert.pem")        # Base64 编码读取

# 路径变量
path.module    # 当前模块路径
path.root      # 根模块路径
path.cwd       # 当前工作目录

# ═══════════════════════════════════════════
# 加密函数
# ═══════════════════════════════════════════

md5("hello")              # "5d41402abc4b2a76b9719d911017c592"
sha256("hello")           # "2cf24dba5fb0a30e26e83b2ac5b9e29e..."
sha512("hello")           # 更长的哈希值
bcrypt("password")        # bcrypt 哈希
uuid()                    # 生成 UUID
uuidv5("dns", "example.com")  # 基于名称的 UUID

# ═══════════════════════════════════════════
# 类型转换函数
# ═══════════════════════════════════════════

tostring(42)         # "42"
tonumber("42")       # 42
tobool("true")       # true
tolist(set)          # 转换为列表
tomap(object)        # 转换为映射
```

### 8. Provisioner（供应器）

#### 8.1 Provisioner 概述

Provisioner 用于在资源创建或销毁时执行额外操作。**应尽量避免使用**，优先考虑 user_data、cloud-init 等替代方案。

```
┌─────────────────────────────────────────────────────────┐
│              Provisioner 类型与使用场景                    │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │  local-exec     │  │  remote-exec    │               │
│  │  本地执行命令    │  │  远程执行命令    │               │
│  ├─────────────────┤  ├─────────────────┤               │
│  │ - 触发 CI/CD    │  │ - 安装软件      │               │
│  │ - 发送通知      │  │ - 配置服务      │               │
│  │ - 调用 API      │  │ - 执行脚本      │               │
│  └─────────────────┘  └─────────────────┘               │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐               │
│  │  file           │  │  替代方案       │               │
│  │  传输文件        │  │  优先使用       │               │
│  ├─────────────────┤  ├─────────────────┤               │
│  │ - 上传配置文件   │  │ - user_data     │               │
│  │ - 部署证书      │  │ - cloud-init    │               │
│  │ - 传输脚本      │  │ - Ansible       │               │
│  └─────────────────┘  │ - Packer        │               │
│                       └─────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

#### 8.2 Provisioner 语法

```hcl
# ── local-exec ──
resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"

  provisioner "local-exec" {
    command = "echo 'Instance ${self.id} created at ${self.public_ip}' >> instance_log.txt"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOF
      curl -X POST https://hooks.slack.com/services/xxx \
        -H 'Content-Type: application/json' \
        -d '{"text":"New instance: ${self.public_ip}"}'
    EOF
  }

  # 销毁时执行
  provisioner "local-exec" {
    when    = destroy
    command = "echo 'Instance ${self.id} is being destroyed' >> destroy_log.txt"
  }
}

# ── remote-exec ──
resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  key_name      = aws_key_pair.deployer.key_name

  connection {
    type        = "ssh"
    user        = "ec2-user"
    private_key = file("~/.ssh/id_rsa")
    host        = self.public_ip
    timeout     = "5m"
  }

  # 内联命令
  provisioner "remote-exec" {
    inline = [
      "sudo yum update -y",
      "sudo yum install -y httpd",
      "sudo systemctl start httpd",
      "sudo systemctl enable httpd",
    ]
  }

  # 执行远程脚本
  provisioner "remote-exec" {
    script = "${path.module}/scripts/setup.sh"
  }

  # 执行多个脚本
  provisioner "remote-exec" {
    scripts = [
      "${path.module}/scripts/install.sh",
      "${path.module}/scripts/configure.sh",
    ]
  }
}

# ── file ──
resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"

  connection {
    type        = "ssh"
    user        = "ec2-user"
    private_key = file("~/.ssh/id_rsa")
    host        = self.public_ip
  }

  # 传输文件
  provisioner "file" {
    source      = "${path.module}/files/app.conf"
    destination = "/etc/app/app.conf"
  }

  # 传输目录
  provisioner "file" {
    source      = "${path.module}/files/certs/"
    destination = "/etc/ssl/certs/app/"
  }

  # 使用 content 参数
  provisioner "file" {
    content     = templatefile("${path.module}/templates/nginx.conf.tpl", {
      server_name = var.domain_name
    })
    destination = "/etc/nginx/nginx.conf"
  }
}
```

#### 8.3 为什么应避免 Provisioner

```
Provisioner 的问题：
┌─────────────────────────────────────────────────────────┐
│ 1. 不在 Terraform 状态中跟踪                            │
│    - 执行失败时状态不确定                                │
│    - 无法 plan/preview                                   │
│                                                         │
│ 2. 不幂等                                               │
│    - 每次 apply 都会重新执行（如果触发重建）             │
│    - 无法保证相同结果                                    │
│                                                         │
│ 3. 破坏声明式模型                                        │
│    - Terraform 是声明式的，Provisioner 是命令式的        │
│    - 混合使用增加复杂度                                  │
│                                                         │
│ 4. 替代方案：                                            │
│    - user_data（EC2 启动时执行）                         │
│    - cloud-init（标准化实例初始化）                      │
│    - AMI（预构建镜像）                                   │
│    - Ansible/Salt（配置管理工具）                        │
│    - 容器镜像（不可变基础设施）                          │
└─────────────────────────────────────────────────────────┘
```

### 9. Meta-Arguments（元参数）

#### 9.1 count

```hcl
# count 用于创建多个相同资源

# 基本用法
resource "aws_instance" "web" {
  count = 3

  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"

  tags = {
    Name = "web-${count.index + 1}"  # web-1, web-2, web-3
  }
}

# 条件创建
resource "aws_instance" "monitoring" {
  count = var.enable_monitoring ? 1 : 0

  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  tags = { Name = "monitoring-server" }
}

# 引用 count 资源
output "instance_ids" {
  value = aws_instance.web[*].id   # 所有实例 ID 的列表
}

output "first_instance" {
  value = aws_instance.web[0].id   # 第一个实例 ID
}
```

**count 的陷阱：**

```hcl
# 问题：删除中间元素会导致后续资源重建
# 如果删除 index=1 的元素，原来的 index=2 会变成 index=1
# 从而触发不必要的资源变更

# 示例：
# 原始：web[0], web[1], web[2]
# 删除 web[1] 后：web[0], web[1](原 web[2]，会被重建)

# 解决方案：使用 for_each 替代 count
resource "aws_instance" "web" {
  for_each = toset(["web-1", "web-2", "web-3"])

  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"

  tags = {
    Name = each.key
  }
}
# 删除 web-2 不会影响 web-1 和 web-3
```

#### 9.2 for_each

```hcl
# for_each 使用 map 或 set 作为迭代源

# ── 使用 set ──
resource "aws_iam_user" "users" {
  for_each = toset(["alice", "bob", "charlie"])
  name     = each.key
  # each.value 与 each.key 相同（set 的特性）
}

# ── 使用 map ──
resource "aws_instance" "web" {
  for_each = {
    web-1 = { type = "t3.micro", az = "us-east-1a" }
    web-2 = { type = "t3.small", az = "us-east-1b" }
    web-3 = { type = "t3.micro", az = "us-east-1c" }
  }

  ami               = data.aws_ami.amazon_linux.id
  instance_type     = each.value.type
  availability_zone = each.value.az

  tags = {
    Name = each.key
  }
}

# ── 引用 for_each 资源 ──
output "web_instance_ids" {
  value = { for k, v in aws_instance.web : k => v.id }
}

# ── for_each 与 for 结合 ──
locals {
  users = {
    alice   = { role = "admin",  email = "alice@example.com" }
    bob     = { role = "viewer", email = "bob@example.com" }
    charlie = { role = "editor", email = "charlie@example.com" }
  }
}

resource "aws_iam_user" "users" {
  for_each = local.users
  name     = each.key
  tags = {
    Role  = each.value.role
    Email = each.value.email
  }
}
```

#### 9.3 lifecycle

```hcl
resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"

  lifecycle {
    # 先创建新资源，再销毁旧资源（零停机）
    create_before_destroy = true

    # 防止意外销毁（生产数据库必须设置！）
    prevent_destroy = true

    # 忽略某些属性的变更（避免不必要的更新）
    ignore_changes = [
      tags,                    # 忽略标签变更
      user_data,               # 忽略 user_data 变更
      ami,                     # 忽略 AMI 变更
    ]

    # 替换标记（当某些属性变更时强制重建）
    replace_triggered_by = [
      aws_security_group.web.id,
    ]

    # 前置条件
    precondition {
      condition     = data.aws_ami.amazon_linux.id != ""
      error_message = "AMI ID 不能为空。"
    }

    # 后置条件
    postcondition {
      condition     = self.public_ip != ""
      error_message = "实例必须有公有 IP。"
    }
  }
}
```

#### 9.4 depends_on

```hcl
# Terraform 通常能自动推断依赖关系
# 但在某些情况下需要显式指定

resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"

  # 显式依赖（当引用不通过参数传递时）
  depends_on = [
    aws_iam_role_policy_attachment.ec2_policy,
    aws_vpc_endpoint.s3,
  ]
}

# 典型使用场景：IAM 策略附件
resource "aws_iam_role" "ec2_role" {
  name = "ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_policy" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# 实例需要在策略附件之后创建
resource "aws_instance" "web" {
  ami                  = data.aws_ami.amazon_linux.id
  instance_type        = "t3.micro"
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  depends_on = [aws_iam_role_policy_attachment.ec2_policy]
}
```

#### 9.5 provider（元参数）

```hcl
# 使用别名 Provider
resource "aws_s3_bucket" "replica" {
  provider = aws.us_west_2   # 指定使用哪个 Provider
  bucket   = "my-replica-bucket"
}

# 在模块中指定 Provider
module "vpc_west" {
  source   = "./modules/vpc"
  providers = {
    aws = aws.us_west_2
  }
}
```

---

## 💻 实战练习

### 练习 1：变量与表达式

**目标：** 使用变量、locals、条件表达式创建一个可配置的 EC2 环境

```hcl
# variables.tf
variable "environment" {
  type    = string
  default = "dev"
}

variable "instance_count" {
  type    = number
  default = 1
}

variable "enable_monitoring" {
  type    = bool
  default = false
}

# locals.tf
locals {
  config = {
    dev = { type = "t3.micro",  count = 1, monitoring = false }
    staging = { type = "t3.small",  count = 2, monitoring = true }
    prod  = { type = "t3.medium", count = 3, monitoring = true }
  }

  current = local.config[var.environment]
}

# main.tf
resource "aws_instance" "web" {
  count         = local.current.count
  ami           = data.aws_ami.amazon_linux.id
  instance_type = local.current.type
  monitoring    = local.current.monitoring

  tags = {
    Name        = "${var.environment}-web-${count.index + 1}"
    Environment = var.environment
  }
}
```

### 练习 2：动态块与 for_each

**目标：** 使用 for_each 和 dynamic 创建灵活的安全组

```hcl
variable "security_rules" {
  type = map(object({
    type        = string
    port        = number
    protocol    = string
    cidr_blocks = list(string)
    description = string
  }))
  default = {
    http = {
      type        = "ingress"
      port        = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTP"
    }
    https = {
      type        = "ingress"
      port        = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS"
    }
    ssh = {
      type        = "ingress"
      port        = 22
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/8"]
      description = "SSH from internal"
    }
  }
}

resource "aws_security_group" "dynamic" {
  name_prefix = "dynamic-"
  description = "Security group with dynamic rules"

  dynamic "ingress" {
    for_each = { for k, v in var.security_rules : k => v if v.type == "ingress" }
    content {
      description = ingress.value.description
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = ingress.value.protocol
      cidr_blocks = ingress.value.cidr_blocks
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### 练习 3：函数综合运用

**目标：** 使用内置函数处理复杂数据转换

```hcl
# 练习：处理服务器列表数据
variable "servers" {
  type = list(object({
    name     = string
    env      = string
    type     = string
    ports    = list(number)
    tags     = map(string)
  }))
  default = [
    {
      name  = "web-1"
      env   = "prod"
      type  = "t3.micro"
      ports = [80, 443]
      tags  = { team = "frontend" }
    },
    {
      name  = "api-1"
      env   = "prod"
      type  = "t3.small"
      ports = [8080]
      tags  = { team = "backend" }
    },
    {
      name  = "db-1"
      env   = "dev"
      type  = "t3.micro"
      ports = [3306]
      tags  = { team = "data" }
    }
  ]
}

locals {
  # 1. 过滤出 prod 环境的服务器
  prod_servers = [for s in var.servers : s if s.env == "prod"]

  # 2. 创建名称到类型的映射
  server_type_map = { for s in var.servers : s.name => s.type }

  # 3. 获取所有不重复的端口
  all_ports = distinct(flatten([for s in var.servers : s.ports]))

  # 4. 按环境分组
  servers_by_env = { for s in var.servers : s.env => s... }

  # 5. 生成安全组规则（所有服务器的所有端口）
  sg_rules = flatten([
    for s in var.servers : [
      for port in s.ports : {
        name = "${s.name}-${port}"
        port = port
      }
    ]
  ])
}

# 验证（使用 terraform console 测试）
output "prod_servers" { value = local.prod_servers }
output "server_type_map" { value = local.server_type_map }
output "all_ports" { value = local.all_ports }
output "servers_by_env" { value = local.servers_by_env }
output "sg_rules" { value = local.sg_rules }
```

---

## 🎯 面试题精选

### 1. Terraform 中 `count` 和 `for_each` 的区别是什么？何时使用哪个？

**参考答案：**
- `count` 使用数字索引（0, 1, 2...），适用于创建多个相同资源
- `for_each` 使用 map/set 的键作为标识符，适用于需要唯一标识的资源
- `count` 的问题：删除中间元素会导致后续资源重建（索引偏移）
- `for_each` 的优势：删除某个元素不影响其他资源
- **推荐：** 优先使用 `for_each`，它更安全且资源标识更清晰

### 2. 解释 `lifecycle` 块的作用和常用参数

**参考答案：**
```hcl
lifecycle {
  create_before_destroy = true    # 先创建新资源再销毁旧资源
  prevent_destroy       = true    # 防止意外销毁（生产数据库）
  ignore_changes        = [tags]  # 忽略特定属性变更
  replace_triggered_by  = [sg.id] # 当依赖资源变更时强制替换
}
```
- `create_before_destroy`：保证零停机更新
- `prevent_destroy`：保护关键资源不被意外删除
- `ignore_changes`：避免不必要的更新（如外部修改的标签）

### 3. 为什么应该避免使用 Provisioner？

**参考答案：**
Provisioner 存在以下问题：
1. **不在状态中跟踪**：执行失败时状态不确定
2. **不幂等**：无法保证重复执行产生相同结果
3. **破坏声明式模型**：Terraform 是声明式的，Provisioner 是命令式的
4. **替代方案**：user_data（EC2）、cloud-init、AMI（预构建镜像）、Ansible

### 4. 如何在 Terraform 中处理敏感数据？

**参考答案：**
1. 变量标记 `sensitive = true`
2. 输出标记 `sensitive = true`
3. 使用 `terraform.tfvars` 文件（不提交到 Git）
4. 环境变量 `TF_VAR_xxx`
5. Secrets Manager / Vault 集成
6. state 文件使用 remote backend + 加密存储

### 5. `for` 表达式和 `dynamic` 块的区别是什么？

**参考答案：**
- `for` 表达式：用于数据转换，生成新的列表或映射值
- `dynamic` 块：用于动态生成嵌套配置块（如 ingress 规则）
- `for` 在 `locals`、`output`、参数中使用
- `dynamic` 在 resource 的嵌套块中使用

### 6. 解释 Terraform 的依赖推断机制

**参考答案：**
Terraform 通过引用关系自动推断依赖：
- 当 `resource A` 引用 `resource B` 的属性时，A 依赖 B
- 使用 `depends_on` 显式指定无法通过引用推断的依赖
- Terraform 构建有向无环图（DAG），并行执行无依赖的操作

### 7. `locals` 和 `variable` 的区别是什么？

**参考答案：**
| 维度 | variable | locals |
|------|----------|--------|
| 用途 | 接受外部输入 | 内部计算和复用 |
| 赋值 | tfvars/环境变量/命令行 | 在配置中定义 |
| 可见性 | 模块对外暴露 | 仅模块内部使用 |
| 默认值 | 可选 | 必须定义 |
| 敏感标记 | 支持 | 不支持 |

### 8. 如何在 Terraform 中实现条件资源创建？

**参考答案：**
```hcl
# 方法 1：count + 条件
resource "aws_instance" "monitoring" {
  count = var.enable_monitoring ? 1 : 0
  # ...
}

# 方法 2：for_each + 条件过滤
resource "aws_instance" "web" {
  for_each = { for k, v in var.servers : k => v if v.enabled }
  # ...
}
```

---

## 📚 深入阅读

- [Terraform Expressions](https://developer.hashicorp.com/terraform/language/expressions)
- [Terraform Functions](https://developer.hashicorp.com/terraform/language/functions)
- [Terraform Resources](https://developer.hashicorp.com/terraform/language/resources)
- [Terraform Data Sources](https://developer.hashicorp.com/terraform/language/data-sources)
- [Terraform Variables](https://developer.hashicorp.com/terraform/language/values/variables)
- [Terraform Provisioners](https://developer.hashicorp.com/terraform/language/resources/provisioners)

---

## ✅ 自检清单

- [ ] 掌握 HCL 基本语法（Block、Argument、Expression、Comment）
- [ ] 理解所有数据类型（string、number、bool、list、map、set、object、tuple）
- [ ] 熟练使用 resource 定义基础设施资源
- [ ] 熟练使用 data source 查询已有资源信息
- [ ] 掌握 variable 声明、验证和赋值方式（优先级）
- [ ] 理解 locals 的作用和使用场景
- [ ] 掌握 output 的声明和 sensitive 标记
- [ ] 熟练使用条件表达式、for 表达式、splat 表达式
- [ ] 掌握常用内置函数（字符串、集合、编码、文件系统）
- [ ] 理解 dynamic 块的使用场景
- [ ] 了解 Provisioner 的类型和限制，知道替代方案
- [ ] 掌握 meta-arguments：count、for_each、lifecycle、depends_on
- [ ] 理解 count 和 for_each 的区别及各自的陷阱
