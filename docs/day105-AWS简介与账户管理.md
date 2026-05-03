# Day 105: AWS 简介与账户管理

> 📅 日期：2026-05-04
> 📖 学习主题：AWS 全球基础设施、IAM 用户/组/角色/策略、账户安全 MFA、CLI 配置、Organizations
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 104（K8s 综合评估）

## 🎯 学习目标

- 理解 AWS 全球基础设施（Region / AZ / Edge Location）的架构与选型原则
- 掌握 IAM 四大核心组件（User / Group / Role / Policy）的原理与最佳实践
- 能够配置 AWS CLI v2 并完成账户安全加固（MFA、密码策略、访问密钥轮换）
- 理解 AWS Organizations 的多账户管理模式与 SCP 策略
- 掌握 SRE 场景下的 IAM 故障排查方法

---

## 📖 核心知识点

### 1. AWS 全球基础设施

#### 1.1 Region（区域）

AWS Region 是全球范围内独立的地理区域，每个 Region 由多个可用区组成。

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS 全球基础设施                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  us-east-1   │  │  eu-west-1   │  │ ap-northeast-1│         │
│  │  (N. Virginia)│  │  (Ireland)   │  │  (Tokyo)     │         │
│  │              │  │              │  │              │          │
│  │  ┌───┐┌───┐ │  │  ┌───┐┌───┐ │  │  ┌───┐┌───┐ │          │
│  │  │AZ ││AZ │ │  │  │AZ ││AZ │ │  │  │AZ ││AZ │ │          │
│  │  │ a ││ b │ │  │  │ a ││ b │ │  │  │ a ││ b │ │          │
│  │  └───┘└───┘ │  │  └───┘└───┘ │  │  └───┘└───┘ │          │
│  │  ┌───┐      │  │  ┌───┐      │  │  ┌───┐      │          │
│  │  │ c │      │  │  │ c │      │  │  │ c │      │          │
│  │  └───┘      │  │  └───┘      │  │  └───┘      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Edge Locations (400+ 全球节点)                       │       │
│  │  CloudFront / Route 53 / Global Accelerator          │       │
│  └─────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

**Region 选择原则：**

| 因素 | 说明 | SRE 关注点 |
|------|------|-----------|
| 延迟 | 用户就近访问 | 用 CloudWatch 测量延迟 |
| 合规 | 数据主权法规 | GDPR 要求数据留在欧盟 |
| 服务可用 | 并非所有 Region 都有全部服务 | 新服务通常先在 us-east-1 上线 |
| 成本 | 不同 Region 定价不同 | us-east-1 通常最便宜 |
| 容灾 | 跨 Region 部署 | 至少选择两个 Region 做灾备 |

```bash
# 列出所有可用 Region
aws ec2 describe-regions --output table

# 查看当前 Region
aws configure get region

# 列出某个 Region 的所有可用区
aws ec2 describe-availability-zones \
  --region us-east-1 \
  --query "AvailabilityZones[*].[ZoneName,State]" \
  --output table
```

#### 1.2 Availability Zone（可用区）

每个 AZ 是 Region 内一个或多个独立的数据中心，具有：
- 独立的电力、网络、冷却系统
- 低延迟的私有光纤互联（通常 < 10ms）
- 故障隔离能力

```
Region: us-east-1
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│  │  AZ: a      │   │  AZ: b      │   │  AZ: c      │  │
│  │             │   │             │   │             │  │
│  │ ┌─────────┐ │   │ ┌─────────┐ │   │ ┌─────────┐ │  │
│  │ │DC 1     │ │   │ │DC 1     │ │   │ │DC 1     │ │  │
│  │ │┌───┐┌──┐│ │   │ │┌───┐┌──┐│ │   │ │┌───┐┌──┐│ │  │
│  │ ││EC2││S3││ │   │ ││EC2││RDS││ │   │ ││EC2││S3││ │  │
│  │ │└───┘└──┘│ │   │ │└───┘└──┘│ │   │ │└───┘└──┘│ │  │
│  │ └─────────┘ │   │ └─────────┘ │   │ └─────────┘ │  │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘  │
│         │                 │                 │          │
│         └─────────────────┼─────────────────┘          │
│                    私有光纤互联                          │
│                   (冗余、低延迟)                         │
└─────────────────────────────────────────────────────────┘
```

#### 1.3 Edge Location（边缘节点）

- 全球 400+ 个边缘节点
- 服务于 CloudFront（CDN）、Route 53（DNS）、Global Accelerator
- 比 Region 更靠近终端用户
- 不直接运行 EC2 等计算服务

---

### 2. IAM（Identity and Access Management）

IAM 是 AWS 安全的基石，负责 **认证（Authentication）** 和 **授权（Authorization）**。

#### 2.1 IAM 四大核心组件

```
┌─────────────────────────────────────────────────────────────────┐
│                        IAM 架构                                  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    IAM Policy (策略)                        │ │
│  │  JSON 文档，定义 Allow/Deny 权限                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │ │
│  │  │AWS 托管策略  │  │ 客户托管策略 │  │ 内联策略     │       │ │
│  │  │(AWS managed) │  │(Customer    │  │(Inline)     │       │ │
│  │  │             │  │ managed)    │  │             │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  IAM User    │  │  IAM Group   │  │  IAM Role    │         │
│  │              │  │              │  │              │         │
│  │  - 长期凭证  │  │  - 用户容器  │  │  - 临时凭证  │         │
│  │  - Access Key│  │  - 策略继承  │  │  - STS Token │         │
│  │  - 密码      │  │              │  │  - 信任策略  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  应用场景：                                                      │
│  User: 个人开发者/管理员        Group: 团队权限管理               │
│  Role: EC2实例角色/跨账户访问/联合身份                           │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 IAM Policy 详解

策略是 JSON 文档，定义了允许或拒绝的操作。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowS3ReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::my-app-bucket",
        "arn:aws:s3:::my-app-bucket/*"
      ],
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "203.0.113.0/24"
        }
      }
    }
  ]
}
```

**Policy 评估逻辑：**

```
请求进入
    │
    ▼
┌──────────────┐     ┌──────────────┐
│ 是否有显式   │─Yes─▶│  Effect 是   │
│ Deny？       │      │  Deny？      │
└──────┬───────┘      └──────┬───────┘
       │No                   │Yes
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│ 是否有显式   │      │   拒绝请求    │
│ Allow？      │      │  (最终结果)   │
└──────┬───────┘      └──────────────┘
       │Yes
       ▼
┌──────────────┐
│ Condition    │
│ 满足？       │
└──────┬───────┘
       │Yes
       ▼
  ┌──────────┐
  │ 允许请求  │
  └──────────┘
```

**关键规则：**
- 显式 Deny 优先于所有 Allow（这是最重要的规则）
- 没有显式 Allow 则默认 Deny
- 多个策略取并集时，Deny 仍然优先

#### 2.3 IAM User 操作

```bash
# 创建用户
aws iam create-user --user-name sre-dev-01

# 创建登录配置文件（控制台登录）
aws iam create-login-profile \
  --user-name sre-dev-01 \
  --password 'Str0ng!P@ssw0rd#2026' \
  --password-reset-required

# 创建访问密钥（CLI/API 访问）
aws iam create-access-key --user-name sre-dev-01
# 输出包含 AccessKeyId 和 SecretAccessKey，只显示一次

# 为用户附加策略
aws iam attach-user-policy \
  --user-name sre-dev-01 \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# 为用户添加内联策略
aws iam put-user-policy \
  --user-name sre-dev-01 \
  --policy-name S3ReadOnlyMyBucket \
  --policy-document file://s3-readonly-policy.json

# 列出用户
aws iam list-users --output table

# 删除用户前需要先清理
# 1. 删除访问密钥
aws iam list-access-keys --user-name sre-dev-01
aws iam delete-access-key --user-name sre-dev-01 --access-key-id AKIA...

# 2. 分离策略
aws iam list-attached-user-policies --user-name sre-dev-01
aws iam detach-user-policy --user-name sre-dev-01 --policy-arn arn:...

# 3. 删除用户
aws iam delete-user --user-name sre-dev-01
```

#### 2.4 IAM Group 操作

```bash
# 创建组
aws iam create-group --group-name SRE-Team

# 为组附加策略
aws iam attach-group-policy \
  --group-name SRE-Team \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# 将用户加入组
aws iam add-user-to-group \
  --user-name sre-dev-01 \
  --group-name SRE-Team

# 列出组成员
aws iam get-group --group-name SRE-Team

# 列出组的策略
aws iam list-attached-group-policies --group-name SRE-Team

# 常见组结构
# SRE-ReadOnly    → 只读权限（监控、排查）
# SRE-Developer   → 开发权限（EC2、S3、RDS 有限操作）
# SRE-Admin       → 管理权限（IAM、VPC、全服务管理）
# SRE-Break-Glass → 紧急权限（需要 MFA + 审批流程）
```

#### 2.5 IAM Role

Role 是一组临时凭证，通过 STS（Security Token Service）获取。

**典型使用场景：**

```
┌─────────────────────────────────────────────────────────────┐
│                    IAM Role 使用场景                          │
│                                                             │
│  1. EC2 实例角色                                             │
│     ┌─────┐    AssumeRole    ┌─────────┐                    │
│     │ EC2 │ ──────────────▶  │ S3/RDS  │                    │
│     └─────┘   临时凭证       └─────────┘                    │
│                                                             │
│  2. 跨账户访问                                               │
│     ┌───────────┐  AssumeRole  ┌───────────┐               │
│     │ Account A │ ────────────▶│ Account B │               │
│     │  (SRE)    │  临时凭证    │ (Prod)    │               │
│     └───────────┘              └───────────┘               │
│                                                             │
│  3. 联合身份                                               │
│     ┌──────────┐  SAML/OIDC   ┌───────────┐               │
│     │ 公司AD   │ ────────────▶│ AWS IAM   │               │
│     │ /Okta    │  联合登录     │  Role     │               │
│     └──────────┘              └───────────┘               │
└─────────────────────────────────────────────────────────────┘
```

```bash
# 创建信任策略文件
cat > /tmp/ec2-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# 创建角色
aws iam create-role \
  --role-name SRE-EC2-Role \
  --assume-role-policy-document file:///tmp/ec2-trust-policy.json

# 附加策略
aws iam attach-role-policy \
  --role-name SRE-EC2-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# 创建实例配置文件（EC2 使用角色必须通过实例配置文件）
aws iam create-instance-profile \
  --instance-profile-name SRE-EC2-Profile

aws iam add-role-to-instance-profile \
  --instance-profile-name SRE-EC2-Profile \
  --role-name SRE-EC2-Role

# 将实例配置文件附加到 EC2 实例
aws ec2 associate-iam-instance-profile \
  --instance-id i-0123456789abcdef0 \
  --iam-instance-profile Name=SRE-EC2-Profile

# 从 EC2 实例内部获取临时凭证
# EC2 实例不需要配置 Access Key，直接通过元数据服务获取
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/SRE-EC2-Role
```

#### 2.6 IAM Role — 跨账户访问

```bash
# === Account A (111111111111) — 生产账户 ===
# 创建角色，信任 Account B

cat > /tmp/cross-account-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::222222222222:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "SRE-Cross-Account-2026"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name CrossAccount-SRE-ReadOnly \
  --assume-role-policy-document file:///tmp/cross-account-trust.json

aws iam attach-role-policy \
  --role-name CrossAccount-SRE-ReadOnly \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# === Account B (222222222222) — SRE 账户 ===
# SRE 用户通过 STS AssumeRole 切换到生产账户

aws sts assume-role \
  --role-arn arn:aws:iam::111111111111:role/CrossAccount-SRE-ReadOnly \
  --role-session-name sre-session \
  --external-id SRE-Cross-Account-2026

# 输出临时凭证，配置为 profile
# ~/.aws/config
# [profile prod-readonly]
# role_arn = arn:aws:iam::111111111111:role/CrossAccount-SRE-ReadOnly
# source_profile = sre-default
# external_id = SRE-Cross-Account-2026

aws s3 ls --profile prod-readonly
```

---

### 3. 账户安全加固

#### 3.1 密码策略

```bash
# 设置密码策略
aws iam update-account-password-policy \
  --minimum-password-length 14 \
  --require-symbols \
  --require-numbers \
  --require-uppercase-characters \
  --require-lowercase-characters \
  --allow-users-to-change-password \
  --max-password-age 90 \
  --password-reuse-prevention 12 \
  --hard-expiry

# 查看密码策略
aws iam get-account-password-policy
```

#### 3.2 MFA（Multi-Factor Authentication）

```bash
# 列出用户的 MFA 设备
aws iam list-mfa-devices --user-name sre-dev-01

# 生成虚拟 MFA 设备
aws iam create-virtual-mfa-device \
  --virtual-mfa-device-name sre-dev-01-mfa \
  --outfile /tmp/mfa-seed.b64 \
  --bootstrap-method Base32StringSeed

# 启用 MFA（需要两个连续的 OTP 码）
aws iam enable-mfa-device \
  --user-name sre-dev-01 \
  --serial-number arn:aws:iam::123456789012:mfa/sre-dev-01-mfa \
  --authentication-code1 123456 \
  --authentication-code2 789012

# 强制所有用户使用 MFA 的策略
cat > /tmp/require-mfa.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowViewAccountInfo",
      "Effect": "Allow",
      "Action": [
        "iam:GetAccountPasswordPolicy",
        "iam:GetAccountSummary",
        "iam:ListVirtualMFADevices"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowManageOwnPasswords",
      "Effect": "Allow",
      "Action": [
        "iam:ChangePassword",
        "iam:GetUser"
      ],
      "Resource": "arn:aws:iam::*:user/${aws:username}"
    },
    {
      "Sid": "AllowManageOwnMFA",
      "Effect": "Allow",
      "Action": [
        "iam:CreateVirtualMFADevice",
        "iam:DeleteVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:ListMFADevices",
        "iam:ResyncMFADevice"
      ],
      "Resource": [
        "arn:aws:iam::*:mfa/${aws:username}",
        "arn:aws:iam::*:user/${aws:username}"
      ]
    },
    {
      "Sid": "DenyAllExceptListedIfNoMFA",
      "Effect": "Deny",
      "NotAction": [
        "iam:CreateVirtualMFADevice",
        "iam:EnableMFADevice",
        "iam:GetUser",
        "iam:ListMFADevices",
        "iam:ListVirtualMFADevices",
        "iam:ResyncMFADevice",
        "sts:GetSessionToken"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
EOF
```

#### 3.3 访问密钥轮换

```bash
# 列出账户中所有用户的访问密钥状态
aws iam generate-credential-report
aws iam get-credential-report --query "Content" --output text | base64 -d

# 检查过期的访问密钥
aws iam list-users --query "Users[*].UserName" --output text | while read user; do
  echo "=== $user ==="
  aws iam list-access-keys --user-name "$user" \
    --query "AccessKeyMetadata[*].[AccessKeyId,Status,CreateDate]" \
    --output table
done

# 轮换访问密钥
# 1. 创建新密钥
aws iam create-access-key --user-name sre-dev-01

# 2. 更新应用使用新密钥

# 3. 使旧密钥失效
aws iam update-access-key \
  --user-name sre-dev-01 \
  --access-key-id AKIAOLDKEY123 \
  --status Inactive

# 4. 验证新密钥工作正常后删除旧密钥
aws iam delete-access-key \
  --user-name sre-dev-01 \
  --access-key-id AKIAOLDKEY123
```

---

### 4. AWS CLI 配置

#### 4.1 安装与配置

```bash
# 安装 AWS CLI v2 (Linux)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 验证安装
aws --version
# aws-cli/2.x.x Python/3.x.x Linux/x.x.x exe/x86_64

# 配置默认凭证
aws configure
# AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
# AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# Default region name [None]: us-east-1
# Default output format [None]: json

# 配置多个 Profile
aws configure --profile sre-dev
aws configure --profile sre-prod

# 查看配置
aws configure list
aws configure list --profile sre-prod
```

#### 4.2 多 Profile 配置文件

```ini
# ~/.aws/config
[default]
region = us-east-1
output = json

[profile sre-dev]
region = us-east-1
output = json
source_profile = default

[profile sre-prod]
region = us-east-1
output = json
role_arn = arn:aws:iam::111111111111:role/SRE-Prod-ReadOnly
source_profile = default
external_id = SRE-Cross-Account-2026
mfa_serial = arn:aws:iam::123456789012:mfa/sre-admin

[profile sre-prod-admin]
region = us-east-1
output = json
role_arn = arn:aws:iam::111111111111:role/SRE-Prod-Admin
source_profile = default
external_id = SRE-Admin-2026
mfa_serial = arn:aws:iam::123456789012:mfa/sre-admin
```

```bash
# 使用 Profile
aws s3 ls --profile sre-prod

# 设置环境变量（临时）
export AWS_PROFILE=sre-prod
aws s3 ls

# 使用 AWS_ACCESS_KEY_ID 环境变量（优先级高于配置文件）
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

#### 4.3 凭证优先级

```
优先级从高到低：
1. 命令行参数 (--profile, --region)
2. 环境变量 (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
3. CLI credentials file (~/.aws/credentials)
4. CLI config file (~/.aws/config)
5. EC2 实例元数据 / ECS 任务角色
```

---

### 5. AWS Organizations

#### 5.1 组织架构

```
┌─────────────────────────────────────────────────────────────────┐
│                   AWS Organizations                              │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Management Account (管理账户)                              │ │
│  │  - 账单聚合                                                 │ │
│  │  - SCP 策略管理                                             │ │
│  │  - 不运行工作负载                                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                           │                                     │
│         ┌─────────────────┼─────────────────┐                  │
│         ▼                 ▼                 ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │  OU: Sandbox│  │  OU: Prod   │  │  OU: Shared │           │
│  │             │  │             │  │  Services   │           │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │           │
│  │ │Account  │ │  │ │Account  │ │  │ │Account  │ │           │
│  │ │Dev-01   │ │  │ │Prod-01  │ │  │ │Logging  │ │           │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │           │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │           │
│  │ │Account  │ │  │ │Account  │ │  │ │Account  │ │           │
│  │ │Dev-02   │ │  │ │Prod-02  │ │  │ │Security │ │           │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.2 SCP（Service Control Policy）

SCP 定义组织中账户的最大权限边界。SCP 不能授予权限，只能限制权限。

```bash
# 创建组织
aws organizations create-organization \
  --feature-set ALL

# 创建 OU
aws organizations create-organizational-unit \
  --parent-id r-xxxx \
  --name "Production"

# 创建 SCP 策略
cat > /tmp/scp-deny-region.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "a4b:*",
        "budgets:*",
        "ce:*",
        "chime:*",
        "cloudfront:*",
        "cur:*",
        "globalaccelerator:*",
        "health:*",
        "iam:*",
        "importexport:*",
        "organizations:*",
        "route53:*",
        "route53domains:*",
        "s3:GetBucketLocation",
        "s3:ListAllMyBuckets",
        "sts:*",
        "support:*",
        "trustedadvisor:*",
        "waf:*",
        "wafv2:*",
        "wellarchitected:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "us-east-1",
            "us-west-2",
            "eu-west-1"
          ]
        }
      }
    }
  ]
}
EOF

aws organizations create-policy \
  --name "Deny-Non-Approved-Regions" \
  --type SERVICE_CONTROL_POLICY \
  --description "只允许使用 us-east-1, us-west-2, eu-west-1" \
  --content file:///tmp/scp-deny-region.json

# 将 SCP 附加到 OU
aws organizations attach-policy \
  --policy-id p-xxxxxxxx \
  --target-id ou-xxxx-xxxxxxxx
```

#### 5.3 常用 SCP 策略

```json
// 禁止停用 CloudTrail
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ProtectCloudTrail",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail"
      ],
      "Resource": "*"
    }
  ]
}
```

```json
// 禁止离开组织
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PreventLeavingOrg",
      "Effect": "Deny",
      "Action": [
        "organizations:LeaveOrganization"
      ],
      "Resource": "*"
    }
  ]
}
```

---

### 6. IAM 最佳实践（SRE 视角）

```
┌─────────────────────────────────────────────────────────────────┐
│                 IAM 最佳实践清单                                  │
│                                                                 │
│  1. 根账户                                                       │
│     ✓ 启用 MFA                                                   │
│     ✓ 不要创建访问密钥                                            │
│     ✓ 仅用于账户级别的操作（计费、组织管理）                        │
│                                                                 │
│  2. 用户管理                                                     │
│     ✓ 每人一个 IAM 用户（不要共享凭证）                           │
│     ✓ 通过 Group 分配权限（不要直接附加策略给用户）                │
│     ✓ 定期审查和清理不活跃用户                                    │
│     ✓ 访问密钥定期轮换（90 天）                                   │
│                                                                 │
│  3. 权限管理                                                     │
│     ✓ 最小权限原则                                               │
│     ✓ 使用 AWS 托管策略开始，然后细化                             │
│     ✓ 使用条件键增加安全性（IP、MFA、时间）                       │
│     ✓ 定期使用 IAM Access Analyzer 审查                          │
│                                                                 │
│  4. 角色使用                                                     │
│     ✓ EC2 使用实例角色（不要在实例上放 Access Key）               │
│     ✓ 跨账户使用 AssumeRole + ExternalId                         │
│     ✓ 使用 Permission Boundary 限制角色最大权限                   │
│                                                                 │
│  5. 审计                                                         │
│     ✓ 启用 CloudTrail 记录所有 API 调用                          │
│     ✓ 启用 IAM Access Analyzer                                  │
│     ✓ 定期生成凭据报告                                           │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 使用 IAM Access Analyzer
aws accessanalyzer create-analyzer \
  --analyzer-name sre-analyzer \
  --type ACCOUNT

# 列出发现的外部访问
aws accessanalyzer list-findings \
  --analyzer-name sre-analyzer \
  --status ACTIVE

# 使用 IAM Credential Report
aws iam generate-credential-report
aws iam get-credential-report --query "Content" --output text | base64 -d

# 使用 IAM Last Accessed 数据
aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::123456789012:role/SRE-EC2-Role

aws iam get-service-last-accessed-details \
  --job-id xxxxxxxx
```

---

### 7. SRE 实战案例

#### 案例 1：EC2 实例无法访问 S3 — IAM 角色排查

**故障现象：** EC2 实例上运行的应用突然无法访问 S3 Bucket，返回 `AccessDenied` 错误。

**排查流程：**

```bash
# 1. 确认 EC2 实例是否有角色
aws ec2 describe-iam-instance-profile-associations \
  --filters "Name=instance-id,Values=i-0123456789abcdef0"

# 2. 检查角色信任策略
aws iam get-role --role-name SRE-EC2-Role \
  --query "Role.AssumeRolePolicyDocument"

# 3. 检查附加的策略
aws iam list-attached-role-policies --role-name SRE-EC2-Role
aws iam list-role-policies --role-name SRE-EC2-Role

# 4. 模拟策略评估
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/SRE-EC2-Role \
  --action-names s3:GetObject s3:PutObject \
  --resource-arns arn:aws:s3:::my-app-bucket/*

# 5. 检查 S3 Bucket Policy 是否拒绝了角色
aws s3api get-bucket-policy --bucket my-app-bucket

# 6. 检查 VPC Endpoint 策略（如果有）
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=vpc-xxxxx" \
  --query "VpcEndpoints[*].PolicyDocument"
```

**常见原因：**
- 角色被意外修改或分离
- S3 Bucket Policy 添加了显式 Deny
- VPC Endpoint 策略限制了访问
- SCP 限制了操作

#### 案例 2：跨账户 SSO 登录失败

**故障现象：** SRE 团队通过 SSO 登录生产账户时，提示 `Access Denied`。

```bash
# 1. 检查 SSO 配置
aws sso-admin list-instances

# 2. 检查 Permission Set
aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxxx

# 3. 检查账户分配
aws sso-admin list-accounts-for-provisioned-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxxx \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-xxxxx/ps-xxxxx

# 4. 检查用户/组分配
aws sso-admin list-account-assignments \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxxx \
  --account-id 111111111111 \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-xxxxx/ps-xxxxx

# 5. 检查 SCP 是否阻止
aws organizations list-policies-for-target \
  --target-id 111111111111 \
  --filter SERVICE_CONTROL_POLICY
```

#### 案例 3：CI/CD Pipeline 权限不足

**故障现象：** GitHub Actions Pipeline 部署时报告 `User: arn:aws:iam::xxx:user/ci-bot is not authorized to perform: iam:PassRole`。

```bash
# 1. 检查 ci-bot 用户的策略
aws iam list-attached-user-policies --user-name ci-bot
aws iam list-user-policies --user-name ci-bot

# 2. 检查 iam:PassRole 的条件
# iam:PassRole 通常需要指定特定的角色 ARN
# 策略应类似：
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::123456789012:role/EC2-App-Role",
  "Condition": {
    "StringEquals": {
      "iam:PassedToService": "ec2.amazonaws.com"
    }
  }
}

# 3. 建议：使用 OIDC 而非长期 Access Key
# 配置 GitHub Actions OIDC Provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# 创建信任 OIDC 的角色
cat > /tmp/github-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:*"
        }
      }
    }
  ]
}
EOF
```

---

## 💻 实战练习

### 练习 1：基础操作 — 创建 IAM 用户和组

**目标：** 创建一个 SRE 团户结构，包含用户、组和策略。

```bash
# 步骤 1: 创建组
aws iam create-group --group-name SRE-Team

# 步骤 2: 为组附加只读策略
aws iam attach-group-policy \
  --group-name SRE-Team \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# 步骤 3: 创建用户
aws iam create-user --user-name sre-student-01

# 步骤 4: 创建登录配置
aws iam create-login-profile \
  --user-name sre-student-01 \
  --password 'Exercise!Pass2026' \
  --password-reset-required

# 步骤 5: 创建访问密钥
aws iam create-access-key --user-name sre-student-01

# 步骤 6: 将用户加入组
aws iam add-user-to-group \
  --user-name sre-student-01 \
  --group-name SRE-Team

# 步骤 7: 验证
aws iam list-attached-group-policies --group-name SRE-Team
aws iam get-group --group-name SRE-Team

# 步骤 8: 清理
aws iam remove-user-from-group --user-name sre-student-01 --group-name SRE-Team
aws iam delete-access-key --user-name sre-student-01 --access-key-id <key-id>
aws iam delete-login-profile --user-name sre-student-01
aws iam delete-user --user-name sre-student-01
```

### 练习 2：进阶场景 — 配置 EC2 实例角色

**目标：** 创建一个 EC2 实例角色，允许实例读取特定 S3 Bucket。

```bash
# 步骤 1: 创建信任策略
cat > /tmp/ec2-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# 步骤 2: 创建角色
aws iam create-role \
  --role-name S3-Read-EC2-Role \
  --assume-role-policy-document file:///tmp/ec2-trust.json

# 步骤 3: 创建自定义策略
cat > /tmp/s3-read-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::exercise-bucket",
        "arn:aws:s3:::exercise-bucket/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name S3-Read-EC2-Role \
  --policy-name S3ReadOnly \
  --policy-document file:///tmp/s3-read-policy.json

# 步骤 4: 创建实例配置文件
aws iam create-instance-profile --instance-profile-name S3-Read-Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name S3-Read-Profile \
  --role-name S3-Read-EC2-Role

# 步骤 5: 启动 EC2 并附加角色
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t3.micro \
  --iam-instance-profile Name=S3-Read-Profile \
  --key-name my-key

# 步骤 6: 验证（SSH 到实例后）
# aws s3 ls s3://exercise-bucket  # 应该成功
# aws ec2 describe-instances      # 应该失败（没有 EC2 权限）
```

### 练习 3：故障排查挑战 — 策略评估调试

**场景：** 一个 IAM 用户被附加了以下策略，但无法删除 S3 对象。找出原因。

```json
// 策略 A（用户直接附加）
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::team-bucket/*"
    }
  ]
}

// 策略 B（通过组附加）
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": [
        "s3:DeleteObject",
        "s3:DeleteBucket"
      ],
      "Resource": "*"
    }
  ]
}
```

```bash
# 排查步骤
# 1. 列出用户所有策略
aws iam list-attached-user-policies --user-name problem-user
aws iam list-groups-for-user --user-name problem-user

# 2. 检查组策略
aws iam list-attached-group-policies --group-name SRE-Team

# 3. 使用策略模拟器
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:user/problem-user \
  --action-names s3:DeleteObject \
  --resource-arns arn:aws:s3:::team-bucket/test.txt

# 答案：策略 B 中的显式 Deny 优先于策略 A 的 Allow
# 评估逻辑：显式 Deny > 显式 Allow > 隐式 Deny
# 解决方案：从组中移除 Deny 策略，或使用 Condition 限制范围
```

---

## 🎯 面试题精选

### 题目 1：IAM Policy 的评估逻辑是什么？

**答：** IAM 策略评估遵循以下优先级：
1. 默认所有请求都被隐式拒绝
2. 检查是否有任何适用的显式 Deny — 如果有，立即拒绝
3. 检查是否有任何适用的显式 Allow — 如果有，允许
4. 如果既没有显式 Deny 也没有显式 Allow，则隐式拒绝

关键点：显式 Deny 永远优先于 Allow，这是安全设计的核心。

### 题目 2：IAM User、Group、Role 的区别？

**答：**
- **User**：代表一个人或应用，拥有长期凭证（Access Key + 密码）
- **Group**：User 的容器，便于批量管理权限，Group 不能嵌套
- **Role**：一组临时凭证（通过 STS 获取），有信任策略定义谁可以使用

关键区别：User 的凭证是长期的，Role 的凭证是临时的（默认 1 小时，最长 12 小时）。

### 题目 3：什么是 Permission Boundary？与 SCP 的区别？

**答：**
- **Permission Boundary**：IAM 实体（User/Role）的最大权限边界，附加在单个 User/Role 上
- **SCP**：组织中账户的最大权限边界，附加在账户/OU 上

两者都不能授予权限，只能限制权限。区别在于作用范围：
- Permission Boundary → 单个 IAM 实体
- SCP → 整个账户或 OU

### 题目 4：如何安全地让 EC2 访问 S3？

**答：** 使用 IAM 实例角色（Instance Profile）：
1. 创建 Role，信任策略允许 `ec2.amazonaws.com`
2. 附加 S3 访问策略到 Role
3. 创建 Instance Profile 并关联 Role
4. 启动 EC2 时指定 Instance Profile

绝对不要在 EC2 上放置 Access Key，因为：
- 密钥可能泄露（日志、代码、快照）
- 无法自动轮换
- 违反最小权限原则

### 题目 5：跨账户访问有哪些方式？

**答：**
1. **AssumeRole + ExternalId**：最常见，通过 STS 获取临时凭证
2. **Cross-account Bucket Policy**：S3 直接授权给另一个账户的 User/Role
3. **VPC Peering + Private Link**：网络层面的跨账户访问
4. **AWS Organizations + SCP**：组织内的集中管理
5. **AWS RAM（Resource Access Manager）**：共享资源（子网、Route 53 Resolver 等）

### 题目 6：如何实现零信任的安全模型？

**答：**
1. 最小权限原则：每个实体只获得完成任务所需的最小权限
2. 强制 MFA：所有用户必须启用 MFA
3. 临时凭证：使用 Role 而非长期 Access Key
4. 条件限制：使用 Condition 锁定 IP、时间、MFA 状态
5. 审计日志：CloudTrail 记录所有 API 调用
6. 定期审查：IAM Access Analyzer + Credential Report
7. SCP 边界：组织层面限制最大权限

### 题目 7：aws:PrincipalOrgId 条件键的作用？

**答：** 用于限制只有同一 AWS 组织内的账户才能访问资源。常用于 S3 Bucket Policy：

```json
{
  "Condition": {
    "StringEquals": {
      "aws:PrincipalOrgId": "o-xxxxxxxxxx"
    }
  }
}
```

比列出所有账户 ID 更好维护，新账户加入组织后自动获得权限。

### 题目 8：IAM 的 Limit 和 Quota 有哪些需要注意？

**答：**
- 每个账户最多 5000 个 IAM User
- 每个 User 最多属于 10 个 Group
- 每个 User 最多附加 10 个 Managed Policy
- 每个 Role 最多附加 10 个 Managed Policy
- 每个 Policy 最多 6144 字符（内联策略）
- Managed Policy 最大 6144 字符（默认版本），所有版本共 10 个

### 题目 9：什么是 Session Policy？与 Resource-based Policy 的区别？

**答：**
- **Session Policy**：通过 `AssumeRole` 时传入的策略，进一步限制 Role 的权限（两者取交集）
- **Resource-based Policy**：附加在资源上的策略（如 S3 Bucket Policy），可以跨账户直接授权

关键区别：Resource-based Policy 可以同时包含 Allow 和对其他账户的授权，而 Session Policy 只能进一步限制。

---

## 📚 深入阅读

- [AWS IAM 官方文档](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html)
- [AWS IAM 最佳实践](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Organizations 官方文档](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html)
- [AWS CLI v2 配置](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
- [AWS Security Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/IAMBestPracticesAndUseCases.html)
- [IAM Policy Evaluation Logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

---

## ✅ 自检清单

- [ ] 能够解释 AWS Region / AZ / Edge Location 的区别和选型原则
- [ ] 能够创建和管理 IAM User、Group、Role、Policy
- [ ] 能够编写自定义 IAM Policy（JSON 格式）
- [ ] 能够配置跨账户访问（AssumeRole + ExternalId）
- [ ] 能够配置 AWS CLI v2 多 Profile
- [ ] 能够设置账户安全加固（MFA、密码策略、密钥轮换）
- [ ] 能够理解 SCP 的作用和评估逻辑
- [ ] 能够排查 IAM 相关的 AccessDenied 错误
- [ ] 能够使用 IAM Access Analyzer 和 Credential Report
- [ ] 能够解释 Policy 评估逻辑（Deny > Allow > Implicit Deny）
