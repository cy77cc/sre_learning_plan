# Day 132: Terraform + Ansible 综合实践

> 📅 日期：2026-05-10
> 📖 学习主题：Terraform 创建基础设施、Ansible 配置应用、完整工作流、最佳实践
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 131（自动化部署），Day 120（Terraform 简介）

## 🎯 学习目标

- 理解 Terraform + Ansible 的分工与协作模式
- 掌握 Terraform 创建基础设施并输出 Inventory
- 掌握 Ansible 读取 Terraform 输出并配置服务器
- 能构建完整的 IaC 工作流（基础设施 + 配置管理 + 应用部署）

---

## 📖 核心知识点

### 1. Terraform + Ansible 协作模式

#### 1.1 分工与职责

```
┌─────────────────────────────────────────────────────────────────┐
│                Terraform + Ansible 分工                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Terraform 负责                        │   │
│  │                                                         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │  VPC     │  │  EC2     │  │  RDS     │              │   │
│  │  │  子网    │  │  实例    │  │  数据库  │              │   │
│  │  │  路由表  │  │  安全组  │  │  参数组  │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │  ELB     │  │  S3      │  │  IAM     │              │   │
│  │  │  负载    │  │  存储    │  │  角色    │              │   │
│  │  │  均衡器  │  │  桶      │  │  策略    │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  │                                                         │   │
│  │  特点：声明式、有状态、幂等、管理生命周期               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          │ 输出 IP、主机名、连接信息            │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Ansible 负责                          │   │
│  │                                                         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │  安装    │  │  配置    │  │  部署    │              │   │
│  │  │  软件包  │  │  服务    │  │  应用    │              │   │
│  │  │  Nginx   │  │  SSH     │  │  代码    │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │  安全    │  │  监控    │  │  备份    │              │   │
│  │  │  加固    │  │  Agent   │  │  策略    │              │   │
│  │  │  防火墙  │  │  Exporter│  │  Cron    │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  │                                                         │   │
│  │  特点：命令式、无状态、SSH 连接、配置管理               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  对比总结：                                                      │
│  ┌────────────────┬────────────────┬────────────────┐          │
│  │     维度       │   Terraform    │    Ansible     │          │
│  ├────────────────┼────────────────┼────────────────┤          │
│  │     类型       │   基础设施     │   配置管理     │          │
│  │     语言       │   HCL          │   YAML         │          │
│  │     状态       │   有状态       │   无状态       │          │
│  │     连接       │   API          │   SSH          │          │
│  │     幂等       │   内置         │   内置         │          │
│  │     适用       │   创建资源     │   配置服务器   │          │
│  │     回滚       │   state 管理   │   重新部署     │          │
│  └────────────────┴────────────────┴────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 集成方式

```
┌─────────────────────────────────────────────────────────────────┐
│                Terraform + Ansible 集成方式                       │
│                                                                 │
│  方式 1：Terraform 输出 → Ansible Inventory                     │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│  │Terraform │────→│ 输出文件 │────→│ Ansible  │               │
│  │ 创建资源 │     │ (JSON)   │     │ 动态     │               │
│  └──────────┘     └──────────┘     │ Inventory│               │
│                                     └──────────┘               │
│                                                                 │
│  方式 2：Terraform null_resource + local-exec                    │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│  │Terraform │────→│local-exec│────→│ Ansible  │               │
│  │ 创建资源 │     │ provisioner│    │ Playbook │               │
│  └──────────┘     └──────────┘     └──────────┘               │
│                                                                 │
│  方式 3：terraform-inventory（第三方工具）                       │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│  │Terraform │────→│ tfstate  │────→│terraform-│               │
│  │ 创建资源 │     │ 文件     │     │inventory │               │
│  └──────────┘     └──────────┘     └──────────┘               │
│                                                                 │
│  推荐：方式 1（最灵活、最可控）                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Terraform 创建基础设施

#### 2.1 项目结构

```
terraform-ansible-project/
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   ├── providers.tf
│   ├── network.tf
│   ├── compute.tf
│   ├── database.tf
│   └── ansible_inventory.tf
├── ansible/
│   ├── ansible.cfg
│   ├── inventory/
│   │   └── generated/
│   │       └── hosts.yml
│   ├── playbooks/
│   │   ├── site.yml
│   │   ├── webservers.yml
│   │   └── dbservers.yml
│   └── roles/
│       ├── common/
│       ├── nginx/
│       ├── app/
│       └── postgresql/
├── Makefile
└── README.md
```

#### 2.2 Terraform 配置

```hcl
# terraform/versions.tf
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
```

```hcl
# terraform/variables.tf
variable "project_name" {
  description = "项目名称"
  type        = string
  default     = "sre-platform"
}

variable "environment" {
  description = "环境名称"
  type        = string
  default     = "production"

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "环境必须是 dev、staging 或 production。"
  }
}

variable "aws_region" {
  description = "AWS 区域"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.0.0.0/16"
}

variable "web_instance_type" {
  description = "Web 服务器实例类型"
  type        = string
  default     = "t3.medium"
}

variable "web_instance_count" {
  description = "Web 服务器数量"
  type        = number
  default     = 2
}

variable "db_instance_class" {
  description = "数据库实例类型"
  type        = string
  default     = "db.t3.medium"
}

variable "db_name" {
  description = "数据库名称"
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "数据库用户名"
  type        = string
  default     = "appuser"
}

variable "db_password" {
  description = "数据库密码"
  type        = string
  sensitive   = true
}

variable "ssh_key_name" {
  description = "SSH 密钥对名称"
  type        = string
}

variable "ansible_ssh_private_key_file" {
  description = "Ansible SSH 私钥文件路径"
  type        = string
  default     = "~/.ssh/ansible.pem"
}
```

```hcl
# terraform/providers.tf
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

```hcl
# terraform/network.tf
# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-${var.environment}-igw"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-${var.environment}-public-${count.index + 1}"
    Tier = "public"
  }
}

# Private Subnets
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-${var.environment}-private-${count.index + 1}"
    Tier = "private"
  }
}

# Route Table for Public Subnets
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
  tags = {
    Name = "${var.project_name}-${var.environment}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name = "${var.project_name}-${var.environment}-nat"
  }

  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-private-rt"
  }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}
```

```hcl
# terraform/compute.tf
# Security Group for Web Servers
resource "aws_security_group" "web" {
  name_prefix = "${var.project_name}-${var.environment}-web-"
  description = "Security group for web servers"
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

  ingress {
    description = "SSH from bastion"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
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

  tags = {
    Name = "${var.project_name}-${var.environment}-web-sg"
  }
}

# AMI Data Source
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

# Web Server Instances
resource "aws_instance" "web" {
  count                  = var.web_instance_count
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.web_instance_type
  key_name               = var.ssh_key_name
  vpc_security_group_ids = [aws_security_group.web.id]
  subnet_id              = aws_subnet.public[count.index].id

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-web-${count.index + 1}"
    Role = "webserver"
    Tier = "public"
  }
}
```

```hcl
# terraform/database.tf
# Security Group for Database
resource "aws_security_group" "db" {
  name_prefix = "${var.project_name}-${var.environment}-db-"
  description = "Security group for database"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from web servers"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
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

  tags = {
    Name = "${var.project_name}-${var.environment}-db-sg"
  }
}

# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-${var.environment}-db-subnet"
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}-db"

  engine         = "postgres"
  engine_version = "16.3"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  multi_az            = true
  skip_final_snapshot = false
  final_snapshot_identifier = "${var.project_name}-${var.environment}-db-final"

  tags = {
    Name = "${var.project_name}-${var.environment}-db"
    Role = "database"
  }
}
```

#### 2.3 Terraform 输出 Ansible Inventory

```hcl
# terraform/outputs.tf
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "web_server_ips" {
  description = "Web 服务器公网 IP 列表"
  value       = aws_instance.web[*].public_ip
}

output "web_server_private_ips" {
  description = "Web 服务器私有 IP 列表"
  value       = aws_instance.web[*].private_ip
}

output "web_server_ids" {
  description = "Web 服务器实例 ID 列表"
  value       = aws_instance.web[*].id
}

output "db_endpoint" {
  description = "数据库连接端点"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "db_address" {
  description = "数据库地址"
  value       = aws_db_instance.main.address
}

output "db_port" {
  description = "数据库端口"
  value       = aws_db_instance.main.port
}
```

```hcl
# terraform/ansible_inventory.tf
# 生成 Ansible Inventory 文件
resource "local_file" "ansible_inventory" {
  filename = "${path.module}/../ansible/inventory/generated/hosts.yml"
  content  = <<-EOF
    ---
    all:
      vars:
        ansible_user: ec2-user
        ansible_ssh_private_key_file: ${var.ansible_ssh_private_key_file}
        ansible_ssh_common_args: '-o StrictHostKeyChecking=no'
        project_name: ${var.project_name}
        environment: ${var.environment}
        app_env: ${var.environment}

      children:
        webservers:
          hosts:
    %{for idx, instance in aws_instance.web~}
            web${idx + 1}:
              ansible_host: ${instance.public_ip}
              private_ip: ${instance.private_ip}
              instance_id: ${instance.id}
              availability_zone: ${instance.availability_zone}
    %{endfor~}
          vars:
            app_port: 8080
            nginx_port: 80

        dbservers:
          hosts:
            db-primary:
              ansible_host: ${aws_db_instance.main.address}
              db_endpoint: ${aws_db_instance.main.endpoint}
              db_port: ${aws_db_instance.main.port}
              db_name: ${var.db_name}
              db_username: ${var.db_username}
          vars:
            db_engine: postgres
            db_version: "${aws_db_instance.main.engine_version}"

        production:
          children:
            webservers:
            dbservers:
  EOF
}
```

### 3. Ansible 配置应用

#### 3.1 Ansible 项目配置

```ini
# ansible/ansible.cfg
[defaults]
inventory = ./inventory/generated/hosts.yml
remote_user = ec2-user
host_key_checking = False
timeout = 30
log_path = ./ansible.log
forks = 20
retry_files_enabled = True
retry_files_save_path = ./retry
gathering = smart
fact_caching = jsonfile
fact_caching_connection = /tmp/ansible_facts_cache
fact_caching_timeout = 86400
stdout_callback = yaml
display_skipped_hosts = False
roles_path = ./roles

[privilege_escalation]
become = True
become_method = sudo
become_user = root
become_ask_pass = False

[ssh_connection]
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o StrictHostKeyChecking=no
pipelining = True
retries = 3
```

#### 3.2 主 Playbook

```yaml
# ansible/playbooks/site.yml
---
# 主入口 Playbook — 完整服务器配置

- name: Configure web servers
  import_playbook: webservers.yml

- name: Configure database
  import_playbook: dbservers.yml
```

```yaml
# ansible/playbooks/webservers.yml
---
- name: Configure web servers
  hosts: webservers
  become: yes
  gather_facts: yes
  serial: "50%"

  vars:
    app_name: mywebapp
    app_port: 8080
    deploy_user: deploy
    deploy_group: deploy
    app_dir: /opt/{{ app_name }}

  pre_tasks:
    - name: Wait for SSH to be ready
      wait_for_connection:
        timeout: 300
      tags: [always]

    - name: Verify connectivity
      ping:
      tags: [always]

    - name: Display server info
      debug:
        msg: |
          Host: {{ inventory_hostname }}
          IP: {{ ansible_default_ipv4.address | default(ansible_host) }}
          OS: {{ ansible_distribution }} {{ ansible_distribution_version }}
          CPU: {{ ansible_processor_vcpus }}
          RAM: {{ ansible_memtotal_mb }} MB
      tags: [always]

  roles:
    - role: common
      tags: [common]

    - role: nginx
      vars:
        nginx_port: 80
        nginx_server_name: "{{ app_domain | default('_') }}"
      tags: [nginx]

    - role: app
      vars:
        app_version: "{{ app_version | default('latest') }}"
      tags: [app]

  post_tasks:
    - name: Verify all services are running
      service:
        name: "{{ item }}"
        state: started
      loop:
        - nginx
        - "{{ app_name }}"
      tags: [verify]

    - name: Health check
      uri:
        url: "http://localhost:{{ app_port }}/health"
        method: GET
        status_code: 200
      register: health
      retries: 5
      delay: 10
      until: health.status == 200
      tags: [verify]

    - name: Display deployment summary
      debug:
        msg: |
          Deployment complete!
          Host: {{ inventory_hostname }}
          Version: {{ app_version | default('latest') }}
          Status: Healthy
      tags: [verify]
```

```yaml
# ansible/playbooks/dbservers.yml
---
- name: Configure database connection
  hosts: webservers
  become: yes
  gather_facts: yes

  vars:
    app_name: mywebapp
    app_dir: /opt/{{ app_name }}

  tasks:
    - name: Deploy database connection config
      template:
        src: templates/db.conf.j2
        dest: "{{ app_dir }}/config/db.conf"
        owner: deploy
        group: deploy
        mode: "0640"
      notify: Restart application

    - name: Test database connectivity
      shell: |
        PGPASSWORD="{{ db_password }}" psql -h {{ hostvars['db-primary']['db_endpoint'] }} \
          -U {{ hostvars['db-primary']['db_username'] }} \
          -d {{ hostvars['db-primary']['db_name'] }} \
          -c "SELECT 1"
      register: db_test
      changed_when: false
      failed_when: false

    - name: Display database connectivity result
      debug:
        msg: "Database connectivity: {{ 'OK' if db_test.rc == 0 else 'FAILED' }}"

  handlers:
    - name: Restart application
      service:
        name: "{{ app_name }}"
        state: restarted
```

### 4. 完整工作流

#### 4.1 Makefile

```makefile
# Makefile
.PHONY: init plan apply destroy ansible-deploy ansible-configure help

# 变量
ENV ?= production
TF_DIR = terraform
ANSIBLE_DIR = ansible

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Terraform 命令 ──
tf-init: ## 初始化 Terraform
	cd $(TF_DIR) && terraform init

tf-plan: ## 生成 Terraform 执行计划
	cd $(TF_DIR) && terraform plan -out=tfplan

tf-apply: ## 应用 Terraform 变更
	cd $(TF_DIR) && terraform apply tfplan

tf-destroy: ## 销毁 Terraform 资源（危险！）
	cd $(TF_DIR) && terraform destroy

tf-output: ## 显示 Terraform 输出
	cd $(TF_DIR) && terraform output

tf-inventory: ## 生成 Ansible Inventory
	cd $(TF_DIR) && terraform apply -target=local_file.ansible_inventory -auto-approve

# ── Ansible 命令 ──
ansible-lint: ## 运行 Ansible Lint
	cd $(ANSIBLE_DIR) && ansible-lint playbooks/

ansible-syntax: ## 检查 Ansible 语法
	cd $(ANSIBLE_DIR) && ansible-playbook playbooks/site.yml --syntax-check

ansible-ping: ## 测试 Ansible 连接
	cd $(ANSIBLE_DIR) && ansible all -m ping

ansible-configure: ## 配置服务器（安装软件、配置服务）
	cd $(ANSIBLE_DIR) && ansible-playbook playbooks/site.yml --tags "common,nginx"

ansible-deploy: ## 部署应用
	cd $(ANSIBLE_DIR) && ansible-playbook playbooks/site.yml \
		-e "app_version=$(VERSION)"

ansible-rollback: ## 回滚应用
	cd $(ANSIBLE_DIR) && ansible-playbook playbooks/rollback.yml

# ── 完整工作流 ──
infra-create: tf-init tf-plan tf-apply tf-inventory ## 创建基础设施并生成 Inventory

infra-configure: ansible-configure ## 配置基础设施

infra-deploy: ansible-deploy ## 部署应用

full-deploy: infra-create infra-configure infra-deploy ## 完整部署（创建+配置+部署）

full-destroy: tf-destroy ## 销毁所有资源（危险！）
```

#### 4.2 完整工作流图

```
┌─────────────────────────────────────────────────────────────────┐
│                Terraform + Ansible 完整工作流                     │
│                                                                 │
│  阶段 1：基础设施创建（Terraform）                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │ tf-init │→ │tf-plan  │→ │tf-apply │→ │ 输出    │          │
│  └─────────┘  └─────────┘  └─────────┘  │Inventory│          │
│                                          └────┬────┘          │
│                                               │                │
│  阶段 2：服务器配置（Ansible）                 │                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐       │                │
│  │ common  │→ │  nginx  │→ │   app   │←──────┘                │
│  │ Role    │  │  Role   │  │  Role   │                         │
│  └─────────┘  └─────────┘  └─────────┘                         │
│       │            │            │                               │
│  阶段 3：应用部署（Ansible）                    │                │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                       │
│  │ Clone   │→ │Install  │→ │Restart  │                        │
│  │ Code    │  │Deps     │  │Service  │                        │
│  └─────────┘  └─────────┘  └─────────┘                        │
│                                                                 │
│  阶段 4：验证（Ansible）                                        │
│  ┌─────────┐  ┌─────────┐                                     │
│  │ Health  │→ │ Notify  │                                     │
│  │ Check   │  │ Slack   │                                     │
│  └─────────┘  └─────────┘                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5. 最佳实践

#### 5.1 项目组织最佳实践

```
┌─────────────────────────────────────────────────────────────────┐
│                    IaC 项目最佳实践                               │
│                                                                 │
│  1. 分离 Terraform 和 Ansible 代码                              │
│     terraform/     ← 基础设施代码                               │
│     ansible/       ← 配置管理代码                               │
│                                                                 │
│  2. 使用 Remote State                                           │
│     S3 + DynamoDB（AWS）                                        │
│     状态文件不提交到 Git                                         │
│                                                                 │
│  3. Vault 加密敏感数据                                          │
│     密码、API Key、证书等                                        │
│     使用 ansible-vault 加密                                     │
│                                                                 │
│  4. 环境隔离                                                    │
│     每个环境独立的 Terraform workspace                          │
│     每个环境独立的 Inventory 目录                                │
│                                                                 │
│  5. 版本控制                                                    │
│     Terraform Provider 版本锁定                                 │
│     Ansible Role 版本锁定                                       │
│     requirements.yml 管理依赖                                   │
│                                                                 │
│  6. CI/CD 集成                                                  │
│     PR 触发 terraform plan + ansible-lint                       │
│     Merge 触发 terraform apply + ansible-playbook               │
│                                                                 │
│  7. 测试                                                        │
│     terraform validate + terraform test                         │
│     ansible-lint + ansible-playbook --syntax-check              │
│     Molecule 测试 Role                                          │
│                                                                 │
│  8. 文档                                                        │
│     README.md 说明项目结构和使用方法                            │
│     变量文档（terraform-docs）                                   │
│     架构图（draw.io / mermaid）                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.2 安全最佳实践

```yaml
# 安全检查清单
security_best_practices:
  terraform:
    - "使用 remote backend 存储状态"
    - "启用状态文件加密"
    - "使用 DynamoDB 状态锁"
    - "IAM 角色最小权限原则"
    - "敏感输出标记 sensitive = true"
    - "不将 .tfstate 提交到 Git"
    - "使用 terraform-docs 自动生成文档"

  ansible:
    - "使用 Vault 加密敏感变量"
    - "使用 SSH 密钥认证，禁用密码"
    - "no_log: true 防止敏感信息泄露"
    - "使用 become 提权，不用 root 直连"
    - "定期轮换 SSH 密钥和 Vault 密码"
    - "使用 ansible-lint 检查代码质量"

  general:
    - "所有代码提交到 Git"
    - "使用 PR 审查机制"
    - "CI/CD 中使用最小权限账号"
    - "定期审计 IAM 权限"
    - "监控和告警异常操作"
```

#### 5.3 Terraform + Ansible 集成的替代方案

```hcl
# 方案 2：使用 null_resource + local-exec 调用 Ansible
resource "null_resource" "ansible_provisioner" {
  # 当实例创建或变更时触发
  triggers = {
    instance_ids = join(",", aws_instance.web[*].id)
  }

  # 等待 SSH 可用
  provisioner "remote-exec" {
    inline = ["echo 'SSH is ready'"]

    connection {
      type        = "ssh"
      user        = "ec2-user"
      private_key = file(var.ansible_ssh_private_key_file)
      host        = aws_instance.web[0].public_ip
    }
  }

  # 执行 Ansible Playbook
  provisioner "local-exec" {
    command = <<-EOT
      cd ../ansible && \
      ansible-playbook playbooks/site.yml \
        -i inventory/generated/hosts.yml \
        --tags "common,nginx" \
        -e "app_version=latest"
    EOT

    environment = {
      ANSIBLE_HOST_KEY_CHECKING = "False"
    }
  }
}
```

```bash
# 方案 3：使用 terraform-inventory 动态读取 tfstate
# 安装
pip install terraform-inventory

# 使用
ansible -i terraform-inventory \
  -m ping \
  all

ansible-playbook -i terraform-inventory \
  playbooks/site.yml
```

### 6. 故障排查

```
┌─────────────────────────────────────────────────────────────────┐
│                常见问题排查                                       │
│                                                                 │
│  问题 1：Terraform 创建资源后 Ansible 连接超时                   │
│  原因：SSH 服务未就绪 / 安全组未开放 22 端口                     │
│  解决：                                                         │
│  - 使用 wait_for_connection 模块等待 SSH 就绪                   │
│  - 检查安全组规则                                               │
│  - 确认 SSH 密钥路径正确                                        │
│                                                                 │
│  问题 2：Ansible Inventory 未更新                                │
│  原因：Terraform 输出未重新生成 Inventory 文件                   │
│  解决：                                                         │
│  - 运行 terraform apply -target=local_file.ansible_inventory    │
│  - 或运行 make tf-inventory                                     │
│                                                                 │
│  问题 3：Ansible 找不到变量                                      │
│  原因：变量定义在 Terraform 输出中，未传递到 Ansible             │
│  解决：                                                         │
│  - 在 Inventory 的 group_vars 中定义                            │
│  - 使用 -e 参数传递                                            │
│  - 使用 hostvars 引用其他主机的变量                             │
│                                                                 │
│  问题 4：数据库连接失败                                          │
│  原因：安全组未开放 / 密码错误 / 网络不通                       │
│  解决：                                                         │
│  - 检查 RDS 安全组是否允许 Web 服务器的 5432 端口               │
│  - 确认 Vault 中的密码正确                                      │
│  - 使用 psql 测试连接                                           │
│                                                                 │
│  问题 5：Terraform 和 Ansible 状态不一致                         │
│  原因：手动修改了基础设施或配置                                  │
│  解决：                                                         │
│  - 运行 terraform plan 检测漂移                                 │
│  - 运行 ansible-playbook --check 检查配置                       │
│  - 使用 terraform import 导入手动创建的资源                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💻 实战练习

### 练习 1：创建完整基础设施

**目标：** 使用 Terraform 创建 VPC + EC2 + RDS 并输出 Ansible Inventory

```bash
# 1. 创建项目目录
mkdir -p iac-project/{terraform,ansible}

# 2. 编写 Terraform 配置
# 3. 运行 terraform init && terraform plan
# 4. 运行 terraform apply
# 5. 验证 Inventory 文件生成
cat ansible/inventory/generated/hosts.yml
```

### 练习 2：Ansible 配置服务器

**目标：** 使用 Ansible 配置 Terraform 创建的服务器

```bash
# 1. 测试连接
cd ansible
ansible all -m ping

# 2. 运行配置 Playbook
ansible-playbook playbooks/site.yml

# 3. 验证服务状态
ansible all -m shell -a "systemctl status nginx"
```

### 练习 3：完整端到端部署

**目标：** 构建完整的 IaC 工作流

```bash
# 使用 Makefile
make full-deploy ENV=production VERSION=v1.0.0

# 或手动执行
make tf-init
make tf-plan
make tf-apply
make ansible-configure
make ansible-deploy VERSION=v1.0.0
```

---

## 🎯 面试题精选

### 1. Terraform 和 Ansible 各自的职责是什么？为什么需要两者配合使用？

**参考答案：**
- **Terraform**：负责基础设施的创建和管理（VPC、EC2、RDS、ELB 等），使用声明式 HCL 语法，有状态管理。
- **Ansible**：负责服务器的配置和应用部署（安装软件、配置服务、部署代码），使用 YAML 语法，无状态。

两者配合是因为：
1. Terraform 擅长创建云资源，但不擅长配置管理
2. Ansible 擅长配置管理，但不擅长创建云资源
3. 各自发挥优势，覆盖完整的基础设施生命周期

### 2. 如何实现 Terraform 输出到 Ansible Inventory 的自动转换？

**参考答案：**
三种方式：
1. **local_file 资源**：在 Terraform 中使用 `local_file` 资源生成 YAML/INI 格式的 Inventory 文件
2. **terraform-inventory**：第三方工具，直接读取 tfstate 文件作为动态 Inventory
3. **null_resource + local-exec**：在 Terraform 中通过 local-exec 调用脚本生成 Inventory

推荐使用方式 1（local_file），因为：
- 生成的是静态文件，可以在 Git 中追踪
- 不依赖第三方工具
- 可以自定义输出格式

### 3. 如何处理 Terraform 和 Ansible 之间的变量传递？

**参考答案：**
1. **通过 Inventory**：Terraform 输出写入 Inventory 文件的 group_vars/host_vars
2. **通过 -e 参数**：Ansible 命令行传递变量
3. **通过文件**：Terraform 输出到 JSON 文件，Ansible 使用 `include_vars` 读取
4. **通过模板**：Terraform 使用 `templatefile` 生成 Ansible 的变量文件

### 4. 在 CI/CD 中如何编排 Terraform 和 Ansible 的执行顺序？

**参考答案：**
```
CI Pipeline:
1. terraform validate + terraform plan (PR 检查)
2. ansible-lint + ansible-playbook --syntax-check (PR 检查)
3. terraform apply (merge 后)
4. terraform output → 生成 Inventory
5. ansible-playbook (配置服务器)
6. ansible-playbook (部署应用)
7. 健康检查 + 通知
```

### 5. 如何实现基础设施和配置的漂移检测？

**参考答案：**
- **基础设施漂移**：`terraform plan` 检测实际资源与配置的差异
- **配置漂移**：`ansible-playbook --check --diff` 检测实际配置与期望配置的差异
- **自动化**：定期运行检测脚本，发现漂移发送告警
- **修复**：`terraform apply` 修复基础设施漂移，`ansible-playbook` 修复配置漂移

### 6. 如何管理多个环境（dev/staging/production）的基础设施和配置？

**参考答案：**
**Terraform：**
- 使用 workspace 隔离环境状态
- 使用变量文件（terraform.tfvars）定义环境特定值
- 使用目录结构分离环境（environments/dev/、environments/staging/）

**Ansible：**
- 使用独立的 Inventory 目录（inventory/production/、inventory/staging/）
- 使用 group_vars 定义环境变量
- 使用 Vault 加密不同环境的敏感数据

### 7. Terraform 的 provisioner（如 local-exec）和 Ansible 有什么区别？什么时候用哪个？

**参考答案：**
- **Terraform provisioner**：在资源创建/销毁时执行，适合一次性操作（如初始化脚本）
- **Ansible**：独立的配置管理工具，适合持续的配置管理和应用部署

**推荐：** 尽量避免使用 provisioner，改用 Ansible 作为独立的配置管理步骤。provisioner 的问题：
- 不可重复执行
- 错误处理困难
- 与 Terraform 状态耦合

---

## 📚 深入阅读

- [Terraform + Ansible Integration](https://developer.hashicorp.com/terraform/tutorials/provision/ansible)
- [Ansible Dynamic Inventory with Terraform](https://docs.ansible.com/ansible/latest/inventory_guide/)
- [Infrastructure as Code Best Practices](https://www.terraform-best-practices.com/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/sample_setup.html)

---

## ✅ 自检清单

- [ ] 理解 Terraform 和 Ansible 的分工与协作模式
- [ ] 掌握 Terraform 创建基础设施并输出 Inventory 的方法
- [ ] 掌握 Ansible 读取 Terraform 输出并配置服务器的流程
- [ ] 能构建完整的 IaC 工作流（Makefile 编排）
- [ ] 理解三种集成方式的优缺点（local_file、terraform-inventory、null_resource）
- [ ] 掌握多环境管理策略
- [ ] 理解安全最佳实践（Vault、Remote State、最小权限）
- [ ] 能排查常见的集成问题
- [ ] 掌握 CI/CD 集成的方法
- [ ] 能独立完成从零到部署的完整流程
