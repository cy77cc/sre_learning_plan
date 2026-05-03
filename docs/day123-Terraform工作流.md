# Day 123: Terraform 工作流

> 📅 日期：2026-05-04
> 📖 学习主题：plan/apply/destroy 深入、CI/CD 集成、代码审查、策略检查（tfsec/checkov）、drift 检测
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 120-122（Terraform 全部基础课程）

---

## 🎯 学习目标

- 深入理解 plan/apply/destroy 的底层机制和高级用法
- 掌握 Terraform CI/CD 集成的最佳实践（plan on PR, apply on merge）
- 能配置策略检查工具（tfsec、checkov、OPA）
- 掌握基础设施漂移检测和处理方法
- 理解 Terraform 代码审查的要点和规范

---

## 📖 核心知识点

### 1. Plan/Apply/Destroy 深入解析

#### 1.1 Terraform 执行流程

```
┌───────────────────────────────────────────────────────────────┐
│                  Terraform Apply 内部流程                      │
│                                                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │  1. 读取  │──→│  2. 构建  │──→│  3. 对比  │──→│  4. 执行  │  │
│  │  配置     │   │  资源图   │   │  状态    │   │  变更    │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘  │
│       │              │              │              │          │
│  读取所有 .tf   构建 DAG      对比配置、      按依赖顺序     │
│  文件和模块    (有向无环图)   状态和实际      并行执行操作   │
│  解析 HCL      分析依赖关系   基础设施的差异                 │
│                                                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │  5. 锁定  │──→│  6. 计划  │──→│  7. 确认  │──→│  8. 更新  │  │
│  │  状态     │   │  生成     │   │  执行    │   │  状态    │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘  │
│       │              │              │              │          │
│  DynamoDB       生成变更计划    用户确认或     将新状态写入  │
│  获取状态锁     显示将要执行    auto-approve   远程 Backend  │
│                 的操作列表                     释放状态锁    │
└───────────────────────────────────────────────────────────────┘
```

#### 1.2 Plan 高级用法

```bash
# ── 目标资源限制 ──
# 仅计划特定资源（调试时有用）
terraform plan -target=aws_instance.web
terraform plan -target=module.vpc

# ── 变量覆盖 ──
terraform plan -var="environment=prod"
terraform plan -var-file="prod.tfvars"

# ── 保存计划到文件 ──
terraform plan -out=tfplan.binary
# 二进制格式，包含完整执行计划

# ── 销毁计划 ──
terraform plan -destroy
# 预览将要销毁的资源

# ── 刷新状态 ──
terraform plan -refresh-only
# 仅从云平台刷新状态，不生成变更计划

# ── 详细输出 ──
terraform plan -json | jq .
# JSON 格式输出，适合 CI/CD 解析

# ── 并行度 ──
terraform plan -parallelism=20
# 增加并行操作数（默认 10）
```

#### 1.3 Plan 输出解读

```bash
# Plan 输出的符号含义：
# +   创建（Create）
# -   删除（Destroy）
# ~   修改（Update，原地修改）
# -/+ 替换（Replace，先删后建）
# <=  读取（Read，data source）
#     无符号 = 无变更

# 示例输出解读：
# aws_instance.web must be replaced
# -/+ resource "aws_instance" "web" {
#       ~ ami           = "ami-old" -> "ami-new"  # 强制替换
#         instance_type = "t3.micro"               # 无变更
#       ~ tags          = {                         # 原地修改
#           ~ Name = "old-name" -> "new-name"
#         }
#     }

# Plan: 1 to add, 1 to change, 1 to destroy.
# 总结：1个创建，1个修改，1个删除
```

#### 1.4 Apply 高级用法

```bash
# ── 自动确认（CI/CD 用）──
terraform apply -auto-approve

# ── 应用已保存的计划 ──
terraform apply tfplan.binary
# 注意：使用保存的计划时不需要 -auto-approve

# ── 目标资源 ──
terraform apply -target=aws_instance.web

# ── 销毁 ──
terraform apply -destroy
# 等价于 terraform destroy

# ── 刷新并应用 ──
terraform apply -refresh-only
# 仅刷新状态，不执行变更

# ── 并行度 ──
terraform apply -parallelism=20
```

#### 1.5 Destroy 注意事项

```bash
# 生产环境禁止使用 terraform destroy！

# 安全措施：
# 1. 使用 prevent_destroy 生命周期规则
resource "aws_db_instance" "main" {
  lifecycle {
    prevent_destroy = true  # 防止意外删除
  }
}

# 2. 使用 -target 精确销毁
terraform destroy -target=aws_instance.temporary

# 3. 使用 deletion_protection（AWS 资源级别）
resource "aws_dynamodb_table" "main" {
  deletion_protection_enabled = true
}
```

### 2. CI/CD 集成

#### 2.1 最佳实践：Plan on PR, Apply on Merge

```
┌───────────────────────────────────────────────────────────┐
│              Terraform CI/CD 最佳实践                      │
│                                                           │
│  开发者提交 PR                                             │
│       │                                                   │
│       ▼                                                   │
│  ┌─────────────────────────────────────────┐              │
│  │  CI Pipeline（自动触发）                 │              │
│  │                                         │              │
│  │  1. terraform fmt -check                │              │
│  │  2. terraform validate                  │              │
│  │  3. terraform plan -out=tfplan          │              │
│  │  4. tfsec / checkov 安全扫描            │              │
│  │  5. 将 plan 结果评论到 PR               │              │
│  │  6. 人工审查 plan 输出                  │              │
│  │                                         │              │
│  └─────────────────────────────────────────┘              │
│       │                                                   │
│       ▼                                                   │
│  人工 Review & Approve                                     │
│       │                                                   │
│       ▼                                                   │
│  Merge to main                                             │
│       │                                                   │
│       ▼                                                   │
│  ┌─────────────────────────────────────────┐              │
│  │  CD Pipeline（自动触发）                 │              │
│  │                                         │              │
│  │  1. terraform plan -out=tfplan          │              │
│  │  2. terraform apply tfplan              │              │
│  │  3. 通知（Slack/Teams）                 │              │
│  │                                         │              │
│  └─────────────────────────────────────────┘              │
└───────────────────────────────────────────────────────────┘
```

#### 2.2 GitHub Actions 配置

```yaml
# .github/workflows/terraform-plan.yml
name: "Terraform Plan"

on:
  pull_request:
    branches: [main]
    paths:
      - "**.tf"
      - "**.tfvars"

permissions:
  contents: read
  pull-requests: write

env:
  TF_VERSION: "1.9.8"
  AWS_REGION: "us-east-1"

jobs:
  plan:
    name: "Terraform Plan"
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Terraform Format Check
        id: fmt
        run: terraform fmt -check -recursive
        continue-on-error: true

      - name: Terraform Init
        id: init
        run: terraform init -backend=true

      - name: Terraform Validate
        id: validate
        run: terraform validate

      - name: Terraform Plan
        id: plan
        run: terraform plan -no-color -out=tfplan
        continue-on-error: true

      - name: Comment PR with Plan
        uses: actions/github-script@v7
        if: github.event_name == 'pull_request'
        with:
          script: |
            const { owner, repo } = context.repo;
            const issue_number = context.issue.number;
            const plan = `${{ steps.plan.outputs.stdout }}`;
            const fmt = `${{ steps.fmt.outcome }}`;
            const validate = `${{ steps.validate.outcome }}`;
            const planOutcome = `${{ steps.plan.outcome }}`;

            let body = `## Terraform Plan Results\n\n`;
            body += `| Step | Status |\n|------|--------|\n`;
            body += `| Format | ${fmt === 'success' ? '✅' : '❌'} |\n`;
            body += `| Validate | ${validate === 'success' ? '✅' : '❌'} |\n`;
            body += `| Plan | ${planOutcome === 'success' ? '✅' : '❌'} |\n\n`;
            body += `\`\`\`hcl\n${plan}\n\`\`\``;

            await github.rest.issues.createComment({
              owner, repo, issue_number, body
            });

      - name: Fail on Plan Error
        if: steps.plan.outcome == 'failure'
        run: exit 1
```

```yaml
# .github/workflows/terraform-apply.yml
name: "Terraform Apply"

on:
  push:
    branches: [main]
    paths:
      - "**.tf"
      - "**.tfvars"

permissions:
  contents: read
  id-token: write

env:
  TF_VERSION: "1.9.8"
  AWS_REGION: "us-east-1"

jobs:
  apply:
    name: "Terraform Apply"
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Terraform Init
        run: terraform init -backend=true

      - name: Terraform Apply
        run: terraform apply -auto-approve

      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1.25.0
        with:
          payload: |
            {
              "text": "Terraform Apply ${{ job.status }}: ${{ github.repository }}@${{ github.sha }}"
            }
```

#### 2.3 GitLab CI 配置

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - plan
  - apply
  - destroy

variables:
  TF_VERSION: "1.9.8"
  TF_ROOT: "${CI_PROJECT_DIR}"

.terraform-base:
  image: hashicorp/terraform:${TF_VERSION}
  before_script:
    - cd ${TF_ROOT}
    - terraform init -backend=true

fmt-check:
  extends: .terraform-base
  stage: validate
  script:
    - terraform fmt -check -recursive
  rules:
    - changes:
        - "**.tf"

validate:
  extends: .terraform-base
  stage: validate
  script:
    - terraform validate
  rules:
    - changes:
        - "**.tf"

plan:
  extends: .terraform-base
  stage: plan
  script:
    - terraform plan -out=tfplan -no-color 2>&1 | tee plan.txt
  artifacts:
    paths:
      - tfplan
      - plan.txt
    expire_in: 1 week
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "**.tf"

apply:
  extends: .terraform-base
  stage: apply
  script:
    - terraform apply -auto-approve
  dependencies:
    - plan
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      changes:
        - "**.tf"
  when: manual  # 手动确认
  environment:
    name: production
```

### 3. 策略检查（Policy as Code）

#### 3.1 tfsec — 安全扫描

```bash
# 安装 tfsec
brew install tfsec
# 或
go install github.com/aquasecurity/tfsec/cmd/tfsec@latest

# 运行扫描
tfsec .

# 输出格式
tfsec . --format json
tfsec . --format html --out tfsec-report.html
tfsec . --format junit --out tfsec-report.xml

# 排除特定规则
tfsec . --exclude aws-s3-enable-bucket-logging

# 仅显示高危和严重问题
tfsec . --minimum-severity HIGH

# CI/CD 集成
tfsec . --soft-fail  # 不阻断 CI（仅报告）
tfsec . --hard-fail  # 阻断 CI（有问题就失败）
```

**常见 tfsec 规则：**

```
┌─────────────────────────────────────────────────────────┐
│                 tfsec 常见规则                             │
├──────────────────────────────┬────────────────────────────┤
│ 规则 ID                     │ 说明                       │
├──────────────────────────────┼────────────────────────────┤
│ aws-s3-enable-bucket-logging│ S3 应启用访问日志           │
│ aws-s3-enable-versioning    │ S3 应启用版本控制           │
│ aws-s3-no-public-access     │ S3 不应允许公开访问         │
│ aws-s3-specify-public-access│ S3 应配置公开访问阻止       │
│ aws-ec2-enable-at-rest-encrypt│ EBS 应加密               │
│ aws-ec2-no-public-ingress   │ EC2 不应开放公网入站        │
│ aws-rds-encryption-enabled  │ RDS 应启用加密              │
│ aws-rds-multi-az            │ RDS 应启用多 AZ            │
│ aws-vpc-no-public-ingress   │ VPC 不应有公开入站规则      │
│ aws-iam-no-policy-wildcards │ IAM 不应使用通配符策略      │
│ aws-ecr-enforce-immutable   │ ECR 应启用不可变标签        │
│ aws-eks-enable-control-logging│ EKS 应启用控制平面日志    │
└──────────────────────────────┴────────────────────────────┘
```

**在代码中忽略特定规则：**

```hcl
# 忽略特定资源的特定规则
resource "aws_s3_bucket" "public_website" {
  bucket = "public-website"

  # tfsec:ignore:aws-s3-no-public-access-bucket
  # 公开网站需要公开访问
}

# 或使用注释
# tfsec:ignore:aws-s3-no-public-access-bucket
resource "aws_s3_bucket" "public_website" {
  bucket = "public-website"
}
```

#### 3.2 Checkov — 策略检查

```bash
# 安装 checkov
pip install checkov

# 运行扫描
checkov -d .

# 指定框架
checkov -d . --framework terraform

# 输出格式
checkov -d . --output json
checkov -d . --output junitxml --output-file checkov-results.xml

# 跳过特定检查
checkov -d . --skip-check CKV_AWS_18

# 仅运行特定检查
checkov -d . --check CKV_AWS_18,CKV_AWS_19

# CI/CD 集成
checkov -d . --soft-fail  # 不阻断 CI
checkov -d . --hard-fail  # 有问题就失败
```

**在代码中跳过 Checkov 检查：**

```hcl
# 跳过整个资源的所有检查
# checkov:skip=CKV_AWS_18:Public website requires public access
resource "aws_s3_bucket" "public" {
  bucket = "public-website"
}

# 跳过特定行的检查
resource "aws_s3_bucket" "example" {
  bucket = "example"
  # checkov:skip=CKV_AWS_14:Versioning not needed for temp bucket
}
```

#### 3.3 OPA（Open Policy Agent）

```hcl
# 使用 terraform test 或 Sentinel 进行 OPA 策略检查

# policies/enforce_tags.rego
package terraform.tags

required_tags := ["Environment", "Team", "ManagedBy"]

deny[msg] {
    resource := input.resource_changes[_]
    resource.change.actions[_] == "create"

    tags := object.get(resource.change.after, "tags", {})
    missing := required_tags[_]
    not tags[missing]

    msg := sprintf(
        "%s '%s' 缺少必需标签 '%s'",
        [resource.type, resource.name, missing]
    )
}

deny[msg] {
    resource := input.resource_changes[_]
    resource.type == "aws_s3_bucket"
    resource.change.actions[_] == "create"

    not resource.change.after.server_side_encryption_configuration

    msg := sprintf(
        "S3 Bucket '%s' 未配置服务端加密",
        [resource.name]
    )
}
```

```bash
# 使用 conftest 运行 OPA 策略
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
conftest test tfplan.json -p policies/
```

### 4. Drift Detection（漂移检测）

#### 4.1 什么是漂移

```
┌─────────────────────────────────────────────────────────┐
│                    基础设施漂移                           │
│                                                         │
│  ┌──────────────┐        ┌──────────────┐               │
│  │  Terraform   │        │  真实基础设施  │               │
│  │  配置/状态   │        │  (云资源)     │               │
│  │              │        │              │               │
│  │ instance_type│  ≠     │ instance_type│               │
│  │ = t3.micro   │        │ = t3.large   │               │
│  │              │        │              │               │
│  │ tags:        │  ≠     │ tags:        │               │
│  │  Name=web    │        │  Name=web    │               │
│  │              │        │  Team=ops    │  ← 被手动修改  │
│  └──────────────┘        └──────────────┘               │
│                                                         │
│  漂移原因：                                              │
│  1. 手动在 Console 修改了资源                            │
│  2. 其他自动化工具修改了资源                             │
│  3. AWS 自动修改（如安全组规则）                         │
│  4. 另一个 Terraform 项目修改了共享资源                  │
│                                                         │
│  漂移风险：                                              │
│  1. 配置不一致（下次 apply 可能意外变更）                │
│  2. 安全漏洞（手动添加了不安全的规则）                   │
│  3. 成本增加（手动扩容了实例）                           │
│  4. 合规问题（不符合组织策略）                           │
└─────────────────────────────────────────────────────────┘
```

#### 4.2 漂移检测方法

```bash
# ── 方法 1：terraform plan -refresh-only ──
terraform plan -refresh-only
# 从云平台读取最新状态，对比 Terraform 状态文件
# 不生成变更计划，仅报告差异

# ── 方法 2：terraform plan ──
terraform plan
# 如果有漂移，plan 会显示将要执行的变更来纠正漂移

# ── 方法 3：定期自动化检测 ──
# 在 CI/CD 中定期运行 plan -refresh-only
# 将结果发送到 Slack/邮件通知
```

#### 4.3 漂移处理策略

```
┌─────────────────────────────────────────────────────────┐
│                 漂移处理策略                               │
│                                                         │
│  发现漂移                                                │
│      │                                                  │
│      ├── 期望的变更（需要保留）                          │
│      │     │                                            │
│      │     └── 更新 Terraform 配置匹配实际状态           │
│      │         terraform apply                          │
│      │                                                  │
│      └── 非期望的变更（需要纠正）                        │
│            │                                            │
│            ├── 纠正漂移                                  │
│            │   terraform apply（恢复到配置定义的状态）   │
│            │                                            │
│            └── 防止再次漂移                              │
│                - IAM 权限限制手动修改                    │
│                - 监控告警检测手动变更                    │
│                - 定期运行 drift detection                │
└─────────────────────────────────────────────────────────┘
```

#### 4.4 自动化漂移检测

```yaml
# .github/workflows/drift-detection.yml
name: "Drift Detection"

on:
  schedule:
    - cron: "0 8 * * 1-5"  # 每天早上 8 点（工作日）
  workflow_dispatch:

jobs:
  drift:
    name: "Check Drift"
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.9.8"

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Terraform Init
        run: terraform init

      - name: Check Drift
        id: drift
        run: |
          terraform plan -refresh-only -detailed-exitcode 2>&1 | tee drift.txt
          echo "exit_code=${PIPESTATUS[0]}" >> $GITHUB_OUTPUT
        continue-on-error: true

      - name: Notify on Drift
        if: steps.drift.outputs.exit_code == '2'
        uses: slackapi/slack-github-action@v1.25.0
        with:
          payload: |
            {
              "text": ":warning: *Infrastructure Drift Detected*\n\n```${{ steps.drift.outputs.stdout }}```"
            }
```

### 5. 代码审查要点

#### 5.1 Terraform 代码审查清单

```
┌─────────────────────────────────────────────────────────┐
│              Terraform 代码审查清单                       │
│                                                         │
│  安全性：                                                │
│  □ 无硬编码密码/密钥/Token                              │
│  □ 敏感变量标记 sensitive = true                         │
│  □ S3 Bucket 启用加密和公开访问阻止                     │
│  □ Security Group 不开放 0.0.0.0/0 的 SSH/RDP          │
│  □ RDS 启用加密和 Multi-AZ                              │
│  □ IAM 策略遵循最小权限原则                              │
│  □ tfsec/checkov 扫描无高危问题                         │
│                                                         │
│  可靠性：                                                │
│  □ 生产资源设置 prevent_destroy                          │
│  □ 关键资源设置 create_before_destroy                    │
│  □ 使用 Multi-AZ 部署                                   │
│  □ Auto Scaling 配置合理                                │
│  □ 备份策略已配置                                       │
│                                                         │
│  可维护性：                                              │
│  □ 代码格式化（terraform fmt）                           │
│  □ 语法验证通过（terraform validate）                    │
│  □ 变量有 description 和 validation                     │
│  □ 输出有 description                                   │
│  □ 使用 locals 减少重复                                 │
│  □ 使用模块封装可复用逻辑                                │
│  □ 使用 for_each 而非 count                             │
│                                                         │
│  状态管理：                                              │
│  □ 使用 Remote Backend                                  │
│  □ 状态锁已配置（DynamoDB）                             │
│  □ 状态文件加密存储                                     │
│  □ .gitignore 排除状态文件                              │
│                                                         │
│  命名规范：                                              │
│  □ 资源命名使用 snake_case                              │
│  □ 变量命名使用 snake_case                              │
│  □ 标签包含 Environment、ManagedBy、Name                │
│  □ 使用一致的命名前缀                                   │
└─────────────────────────────────────────────────────────┘
```

#### 5.2 Plan 输出审查要点

```
审查 plan 输出时关注：

1. 资源变更数量
   - 是否有意外的大量删除？
   - 是否有意外的资源替换（-/+）？

2. 替换操作（-/+）
   - 替换是否必要？
   - 是否会导致数据丢失？
   - 是否有 create_before_destroy？

3. 安全相关变更
   - Security Group 规则变更
   - IAM 策略变更
   - 加密配置变更
   - 网络 ACL 变更

4. 数据库变更
   - RDS 实例变更可能导致停机
   - 参数组变更可能需要重启
   - 存储扩展是否需要维护窗口？

5. 成本影响
   - 实例类型变更
   - 新增 NAT Gateway
   - 新增 RDS 实例
```

### 6. Terraform 项目规范

#### 6.1 目录结构规范

```
terraform-infra/
├── modules/                    # 可复用模块
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── versions.tf
│   ├── eks/
│   │   └── ...
│   └── rds/
│       └── ...
├── environments/               # 环境配置
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── backend.tf
│   │   ├── providers.tf
│   │   ├── terraform.tfvars
│   │   └── versions.tf
│   ├── staging/
│   │   └── ...
│   └── prod/
│       └── ...
├── .github/
│   └── workflows/
│       ├── terraform-plan.yml
│       ├── terraform-apply.yml
│       └── drift-detection.yml
├── .gitignore
├── .terraform-docs.yml
├── .tfsec.yml
└── README.md
```

#### 6.2 .gitignore 配置

```gitignore
# Terraform
*.tfstate
*.tfstate.backup
*.tfstate.*.backup
.terraform/
.terraform.lock.hcl
crash.log
crash.*.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json
.terraformrc
terraform.rc

# 敏感文件
*.tfvars
!example.tfvars
*.auto.tfvars
secrets/
.env

# 计划文件
tfplan
tfplan.binary
*.tfplan

# IDE
.terraform/
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

---

## 💻 实战练习

### 练习 1：配置 GitHub Actions CI/CD

**目标：** 为 Terraform 项目配置完整的 CI/CD 流水线

```yaml
# 完整的 GitHub Actions 配置
# .github/workflows/terraform.yml
name: Terraform

on:
  pull_request:
    branches: [main]
    paths: ["**.tf"]
  push:
    branches: [main]
    paths: ["**.tf"]

env:
  TF_VERSION: "1.9.8"

jobs:
  terraform:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Terraform Fmt Check
        run: terraform fmt -check

      - name: Terraform Init
        run: terraform init

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Plan
        if: github.event_name == 'pull_request'
        run: terraform plan -no-color -out=tfplan
        continue-on-error: true

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve
```

### 练习 2：配置 tfsec 和 checkov

**目标：** 在项目中配置安全扫描工具

```yaml
# .tfsec.yml
minimum_severity: MEDIUM
exclude:
  - aws-s3-enable-bucket-logging  # 日志桶不需要自己的日志

---
# .checkov.yml
framework:
  - terraform
skip-check:
  - CKV_AWS_18  # S3 access logging
output:
  - json
  - junitxml
```

### 练习 3：编写漂移检测脚本

**目标：** 创建一个自动化漂移检测和通知脚本

```bash
#!/bin/bash
# scripts/drift-detection.sh

set -euo pipefail

ENVIRONMENT="${1:-dev}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

echo "=== Drift Detection: ${ENVIRONMENT} ==="

cd "environments/${ENVIRONMENT}"

# 初始化
terraform init -backend=true -input=false

# 检测漂移
DRIFT_OUTPUT=$(terraform plan -refresh-only -detailed-exitcode -no-color 2>&1) || true
EXIT_CODE=$?

case $EXIT_CODE in
  0)
    echo "No drift detected."
    ;;
  1)
    echo "Error during drift detection."
    echo "$DRIFT_OUTPUT"
    exit 1
    ;;
  2)
    echo "Drift detected!"
    echo "$DRIFT_OUTPUT"

    # 发送 Slack 通知
    if [ -n "$SLACK_WEBHOOK" ]; then
      curl -s -X POST "$SLACK_WEBHOOK" \
        -H 'Content-type: application/json' \
        -d "{
          \"text\": \":warning: Infrastructure drift detected in ${ENVIRONMENT}\n\`\`\`${DRIFT_OUTPUT}\`\`\`\"
        }"
    fi
    exit 2
    ;;
esac
```

---

## 🎯 面试题精选

### 1. 解释 Terraform 的 plan → apply 工作流及其安全性

**参考答案：**
- `plan` 是只读操作，生成执行计划，显示所有将要执行的变更（创建/修改/删除）
- `apply` 执行 plan 中的变更
- **安全性**：plan 在 apply 之前执行，用户可以审查所有变更再确认
- **CI/CD 最佳实践**：plan 在 PR 时自动运行供审查，apply 在 merge 后执行
- 保存 plan 到文件（`-out=tfplan`），apply 时使用保存的计划，确保执行的是审查过的变更

### 2. 什么是基础设施漂移？如何检测和处理？

**参考答案：**
漂移是指实际基础设施与 Terraform 状态/配置不一致。原因包括手动修改、其他工具修改等。

检测方法：
- `terraform plan -refresh-only` 定期检测
- CI/CD 定时任务自动扫描

处理策略：
1. 如果是期望的变更 → 更新 Terraform 配置匹配实际
2. 如果是非期望的变更 → `terraform apply` 恢复到配置状态
3. 预防措施：限制 IAM 权限、监控告警、定期检测

### 3. 如何在 CI/CD 中安全地运行 Terraform？

**参考答案：**
1. **Plan on PR**：PR 时自动运行 plan，结果评论到 PR 供审查
2. **Apply on Merge**：merge 到 main 后自动 apply
3. **使用 OIDC**：通过 GitHub OIDC 获取 AWS 临时凭证，不存储长期密钥
4. **环境审批**：生产环境 apply 需要人工审批
5. **状态锁**：使用 DynamoDB 防止并发执行
6. **计划文件**：保存 plan 到文件，apply 使用保存的计划

### 4. tfsec 和 checkov 的区别是什么？

**参考答案：**
两者都是 IaC 安全扫描工具：
- **tfsec**：专注于安全规则，规则由 Aqua Security 维护，轻量级
- **checkov**：更全面，支持安全和合规检查，规则更多，支持多框架
- **推荐**：两者都用，互补覆盖。tfsec 偏安全，checkov 偏合规

### 5. 如何防止生产资源被意外删除？

**参考答案：**
1. **Terraform 层面**：`lifecycle { prevent_destroy = true }`
2. **AWS 资源层面**：`deletion_protection = true`（RDS、ELB 等）
3. **IAM 层面**：限制 Delete 权限，使用 SCP
4. **CI/CD 层面**：生产环境 apply 需要人工审批
5. **S3 状态保护**：状态文件启用版本控制，可回滚

### 6. 如何处理 Terraform 执行超时或卡住？

**参考答案：**
1. 检查状态锁：`terraform force-unlock <LOCK_ID>`
2. 增加超时：资源级别配置 `timeouts` 块
3. 增加并行度：`-parallelism=20`
4. 分阶段执行：使用 `-target` 分批创建资源
5. 检查 API 限流：AWS API 限流可能导致超时

### 7. Terraform 代码审查应该关注哪些方面？

**参考答案：**
1. **安全性**：无硬编码密码、敏感数据标记、SG 规则、IAM 权限
2. **可靠性**：prevent_destroy、Multi-AZ、备份策略
3. **可维护性**：格式化、命名规范、模块化、文档
4. **成本**：实例类型选择、NAT Gateway 数量、存储类型
5. **Plan 审查**：关注替换操作、意外删除、安全相关变更

### 8. 如何实现 Terraform 的蓝绿部署？

**参考答案：**
```hcl
# 使用 workspace 或独立目录
# 蓝环境
module "blue" {
  source     = "./modules/app"
  env_suffix = "blue"
  # ...
}

# 绿环境
module "green" {
  source     = "./modules/app"
  env_suffix = "green"
  # ...
}

# ALB Target Group 权重切换
resource "aws_lb_listener_rule" "traffic_split" {
  # 通过修改权重实现蓝绿切换
}
```

---

## 📚 深入阅读

- [Terraform Workflows](https://developer.hashicorp.com/terraform/cli/workflow)
- [GitHub Actions for Terraform](https://github.com/hashicorp/setup-terraform)
- [tfsec Documentation](https://aquasecurity.github.io/tfsec/)
- [Checkov Documentation](https://www.checkov.io/)
- [OPA for Terraform](https://www.openpolicyagent.org/docs/latest/terraform/)
- [Terraform Cloud](https://cloud.hashicorp.com/products/terraform)

---

## ✅ 自检清单

- [ ] 理解 plan/apply/destroy 的内部执行流程
- [ ] 掌握 plan 的高级用法（-target、-var、-out、-refresh-only）
- [ ] 能解读 plan 输出中的符号（+、-、~、-/+）
- [ ] 掌握 GitHub Actions / GitLab CI 的 Terraform CI/CD 配置
- [ ] 理解 "Plan on PR, Apply on Merge" 的最佳实践
- [ ] 能配置 tfsec 进行安全扫描
- [ ] 能配置 checkov 进行合规检查
- [ ] 理解基础设施漂移的概念、检测和处理方法
- [ ] 掌握代码审查清单（安全、可靠性、可维护性）
- [ ] 了解 OPA 策略检查的基本用法
- [ ] 能配置 .gitignore 排除所有敏感文件
- [ ] 理解 CI/CD 中使用 OIDC 获取临时凭证
