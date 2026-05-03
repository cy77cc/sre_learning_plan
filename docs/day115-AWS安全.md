# Day 115: AWS 安全

> 📅 日期：2026-05-03
> 📖 学习主题：AWS 安全 — IAM 最佳实践、KMS 加密、Secrets Manager、WAF、Shield、GuardDuty、Security Hub、合规
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 105 (AWS 简介), Day 107 (VPC), Day 112 (CloudWatch)

## 🎯 学习目标

- 掌握 IAM 最佳实践与权限设计原则
- 理解 KMS 加密体系与密钥管理
- 能够使用 Secrets Manager 管理敏感信息
- 掌握 WAF 和 Shield 的 DDoS 防护策略
- 理解 GuardDuty 威胁检测与 Security Hub 安全中心
- 能够设计合规的 AWS 安全架构

---

## 📖 核心知识点

### 1. AWS 安全责任共担模型

```
┌──────────────────────────────────────────────────────────────┐
│              AWS 安全责任共担模型                               │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              客户负责（Security IN the Cloud）         │    │
│  │                                                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │   数据    │  │  应用     │  │  IAM     │          │    │
│  │  │   加密    │  │  安全     │  │  访问控制 │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │  操作系统  │  │  网络    │  │  客户端   │          │    │
│  │  │  补丁     │  │  配置    │  │  加密     │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              AWS 负责（Security OF the Cloud）        │    │
│  │                                                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │  全球     │  │  硬件     │  │  软件     │          │    │
│  │  │  基础设施  │  │  安全     │  │  安全     │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │  数据中心  │  │  网络    │  │  服务     │          │    │
│  │  │  物理安全  │  │  基础设施 │  │  可用性   │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 2. IAM 最佳实践

#### IAM 核心概念

```
┌──────────────────────────────────────────────────────────────┐
│                    IAM 核心组件                                │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Users     │  │   Groups    │  │   Roles     │          │
│  │   用户       │  │   用户组     │  │   角色       │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│                ┌──────────────────┐                          │
│                │   Policies       │                          │
│                │   策略文档         │                          │
│                │                  │                          │
│                │  ┌────────────┐  │                          │
│                │  │ JSON 文档  │  │                          │
│                │  │ 定义权限    │  │                          │
│                │  └────────────┘  │                          │
│                └──────────────────┘                          │
│                                                               │
│  策略类型：                                                    │
│  - 托管策略（AWS 托管 / 客户托管）                              │
│  - 内联策略（直接附加到用户/角色/组）                            │
│  - 权限边界（Permission Boundary）                             │
│  - SCP（Service Control Policy）                              │
│  - 资源策略（Resource Policy）                                 │
└──────────────────────────────────────────────────────────────┘
```

#### IAM 最佳实践详解

```
IAM 安全最佳实践（按优先级排序）：

1. 根账户安全（最高优先级）
   ├── 启用 MFA（硬件 MFA 最佳）
   ├── 不使用根账户进行日常操作
   ├── 删除根账户的访问密钥
   └── 使用 CloudWatch 告警监控根账户使用

2. 最小权限原则
   ├── 只授予完成任务所需的最小权限
   ├── 使用 AWS 托管策略作为起点
   ├── 逐步收紧权限
   └── 定期审查和清理未使用的权限

3. IAM 角色而非长期凭证
   ├── EC2 实例使用 Instance Profile
   ├── Lambda 使用执行角色
   ├── ECS 使用 Task Role
   ├── EKS 使用 IRSA
   └── 跨账户使用 AssumeRole

4. MFA（多因素认证）
   ├── 所有 IAM 用户启用 MFA
   ├── 根账户使用硬件 MFA
   ├── 特权操作要求 MFA
   └── 使用 Virtual MFA 或 U2F 安全密钥

5. 凭证管理
   ├── 定期轮换访问密钥（90 天）
   ├── 使用 Secrets Manager 存储密钥
   ├── 禁止在代码中硬编码凭证
   └── 使用 IAM Access Analyzer 检测未使用的访问

6. 条件键增强安全性
   ├── aws:SourceIp - 限制 IP 地址
   ├── aws:RequestedRegion - 限制区域
   ├── aws:MultiFactorAuthPresent - 要求 MFA
   ├── aws:CurrentTime - 限制访问时间
   └── aws:PrincipalOrgID - 限制组织
```

#### IAM Policy 详解

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
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        },
        "IpAddress": {
          "aws:SourceIp": "203.0.113.0/24"
        }
      }
    },
    {
      "Sid": "DenyDeleteOperations",
      "Effect": "Deny",
      "Action": [
        "s3:DeleteObject",
        "s3:DeleteBucket"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalTag/Team": "sre-admins"
        }
      }
    }
  ]
}
```

#### IAM 角色配置

```bash
# 创建 IAM 角色
aws iam create-role \
  --role-name EC2-S3-ReadOnly \
  --assume-role-policy-document '{
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
  }'

# 附加权限策略
aws iam attach-role-policy \
  --role-name EC2-S3-ReadOnly \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# 创建 Instance Profile
aws iam create-instance-profile \
  --instance-profile-name EC2-S3-ReadOnly-Profile

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-S3-ReadOnly-Profile \
  --role-name EC2-S3-ReadOnly

# 附加到 EC2 实例
aws ec2 associate-iam-instance-profile \
  --instance-id i-1234567890abcdef0 \
  --iam-instance-profile Name=EC2-S3-ReadOnly-Profile

# 创建权限边界
aws iam create-policy \
  --policy-name DeveloperBoundary \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:*",
          "ec2:*",
          "rds:*",
          "cloudwatch:*"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Deny",
        "Action": [
          "iam:*",
          "organizations:*",
          "account:*"
        ],
        "Resource": "*"
      }
    ]
  }'
```

#### IAM Access Analyzer

```bash
# 创建 Access Analyzer
aws accessanalyzer create-analyzer \
  --analyzer-name my-analyzer \
  --type ACCOUNT

# 获取分析结果
aws accessanalyzer list-findings \
  --analyzer-arn arn:aws:access-analyzer:us-east-1:123456789012:analyzer/my-analyzer

# 验证策略
aws accessanalyzer validate-policy \
  --policy-document file://policy.json \
  --policy-type IDENTITY_POLICY
```

### 3. KMS 加密

#### KMS 架构

```
┌──────────────────────────────────────────────────────────────┐
│                    KMS 加密架构                                │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    KMS 服务                           │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  Customer Master Key (CMK)                    │  │    │
│  │  │  ├── AWS 管理的 CMK（免费）                    │  │    │
│  │  │  ├── 客户管理的 CMK（收费）                    │  │    │
│  │  │  └── 自定义密钥存储（External Key Store）      │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │                                                     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  密钥操作                                      │  │    │
│  │  │  ├── Encrypt / Decrypt                       │  │    │
│  │  │  ├── GenerateDataKey                         │  │    │
│  │  │  ├── GenerateDataKeyPair                     │  │    │
│  │  │  └── ReEncrypt                               │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│           ┌──────────────┼──────────────┐                    │
│           ▼              ▼              ▼                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  S3 加密     │ │  EBS 加密    │ │  RDS 加密    │        │
│  │  (SSE-KMS)   │ │  (KMS)       │ │  (KMS)       │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                               │
│  信封加密（Envelope Encryption）：                             │
│  1. 生成数据密钥（Data Key）                                  │
│  2. 用数据密钥加密数据                                        │
│  3. 用 CMK 加密数据密钥                                       │
│  4. 存储加密后的数据密钥 + 加密后的数据                         │
└──────────────────────────────────────────────────────────────┘
```

#### KMS 操作

```bash
# 创建客户管理的 CMK
aws kms create-key \
  --description "My application encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --key-spec SYMMETRIC_DEFAULT \
  --tags TagKey=Environment,TagValue=production

# 创建别名
aws kms create-alias \
  --alias-name alias/my-app-key \
  --target-key-id 12345678-1234-1234-1234-123456789012

# 加密数据
aws kms encrypt \
  --key-id alias/my-app-key \
  --plaintext "My secret data" \
  --output text \
  --query CiphertextBlob

# 解密数据
aws kms decrypt \
  --ciphertext-blob fileb://encrypted-file \
  --output text \
  --query Plaintext

# 生成数据密钥
aws kms generate-data-key \
  --key-id alias/my-app-key \
  --key-spec AES_256

# 启用密钥轮换
aws kms enable-key-rotation \
  --key-id 12345678-1234-1234-1234-123456789012

# 查看密钥轮换状态
aws kms get-key-rotation-status \
  --key-id 12345678-1234-1234-1234-123456789012

# 禁用密钥
aws kms disable-key \
  --key-id 12345678-1234-1234-1234-123456789012

# 计划删除密钥（等待期 7-30 天）
aws kms schedule-key-deletion \
  --key-id 12345678-1234-1234-1234-123456789012 \
  --pending-window-in-days 30
```

#### S3 加密选项

```
S3 加密选项对比：

┌─────────────────────────────────────────────────────────────┐
│  SSE-S3（S3 管理的密钥）                                      │
│  - AES-256 加密                                             │
│  - S3 自动管理密钥                                          │
│  - 免费                                                     │
│  - 无法审计密钥使用                                          │
│  - 设置：x-amz-server-side-encryption: AES256               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SSE-KMS（KMS 管理的密钥）                                    │
│  - 使用 KMS CMK 加密                                        │
│  - 可审计密钥使用（CloudTrail）                              │
│  - 可控制密钥策略                                           │
│  - KMS API 调用收费                                         │
│  - 设置：x-amz-server-side-encryption: aws:kms              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  SSE-C（客户提供密钥）                                        │
│  - 客户提供加密密钥                                          │
│  - S3 不存储密钥                                            │
│  - 每次请求需要提供密钥                                      │
│  - 适用于混合云场景                                          │
│  - 设置：x-amz-server-side-encryption-customer-algorithm    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  客户端加密（Client-Side Encryption）                        │
│  - 数据在客户端加密后上传                                    │
│  - 使用 AWS SDK 或客户端加密库                               │
│  - 完全由客户控制                                           │
└─────────────────────────────────────────────────────────────┘
```

```bash
# 启用 S3 默认加密（SSE-KMS）
aws s3api put-bucket-encryption \
  --bucket my-bucket \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "aws:kms",
          "KMSMasterKeyID": "alias/my-app-key"
        },
        "BucketKeyEnabled": true
      }
    ]
  }'

# 创建 Bucket Policy 强制加密
aws s3api put-bucket-policy \
  --bucket my-bucket \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "DenyUnencryptedUploads",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::my-bucket/*",
        "Condition": {
          "StringNotEquals": {
            "s3:x-amz-server-side-encryption": "aws:kms"
          }
        }
      }
    ]
  }'
```

### 4. Secrets Manager

#### Secrets Manager 架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Secrets Manager 架构                        │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Secrets Manager                                     │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  Secret (密钥)                                 │  │    │
│  │  │  ├── 密文数据（JSON）                          │  │    │
│  │  │  ├── 版本管理（自动轮换）                      │  │    │
│  │  │  ├── 访问控制（IAM + Resource Policy）         │  │    │
│  │  │  └── 审计日志（CloudTrail）                    │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│           ┌──────────────┼──────────────┐                    │
│           ▼              ▼              ▼                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  应用获取     │ │  RDS 自动    │ │  Redshift    │        │
│  │  数据库凭证   │ │  轮换密码    │ │  自动轮换     │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                               │
│  自动轮换流程：                                                │
│  1. Secrets Manager 触发 Lambda                              │
│  2. Lambda 生成新密码                                        │
│  3. Lambda 更新数据库密码                                    │
│  4. Lambda 更新 Secret                                       │
│  5. 应用获取最新版本的 Secret                                 │
└──────────────────────────────────────────────────────────────┘
```

#### Secrets Manager 操作

```bash
# 创建 Secret
aws secretsmanager create-secret \
  --name prod/myapp/database \
  --description "Production database credentials" \
  --secret-string '{
    "username": "admin",
    "password": "MySecurePassword123!",
    "engine": "mysql",
    "host": "mydb.cluster-xxx.us-east-1.rds.amazonaws.com",
    "port": 3306,
    "dbname": "myapp"
  }'

# 获取 Secret
aws secretsmanager get-secret-value \
  --secret-id prod/myapp/database \
  --query 'SecretString' --output text | jq .

# 更新 Secret
aws secretsmanager update-secret \
  --secret-id prod/myapp/database \
  --secret-string '{
    "username": "admin",
    "password": "NewSecurePassword456!",
    "engine": "mysql",
    "host": "mydb.cluster-xxx.us-east-1.rds.amazonaws.com",
    "port": 3306,
    "dbname": "myapp"
  }'

# 列出所有 Secret
aws secretsmanager list-secrets

# 删除 Secret（带恢复期）
aws secretsmanager delete-secret \
  --secret-id prod/myapp/database \
  --recovery-window-in-days 30

# 强制删除（无恢复期）
aws secretsmanager delete-secret \
  --secret-id prod/myapp/database \
  --force-delete-without-recovery

# 启用自动轮换
aws secretsmanager rotate-secret \
  --secret-id prod/myapp/database \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRDSMySQLRotationSingleUser \
  --rotation-rules '{"AutomaticallyAfterDays": 30}'

# 创建资源策略
aws secretsmanager put-resource-policy \
  --secret-id prod/myapp/database \
  --resource-policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::123456789012:role/my-app-role"
        },
        "Action": "secretsmanager:GetSecretValue",
        "Resource": "*"
      }
    ]
  }'
```

#### 使用 SDK 获取 Secret

```python
import boto3
import json

def get_secret(secret_name, region='us-east-1'):
    """从 Secrets Manager 获取密钥"""
    client = boto3.client('secretsmanager', region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        raise

# 使用示例
db_credentials = get_secret('prod/myapp/database')
connection = mysql.connect(
    host=db_credentials['host'],
    user=db_credentials['username'],
    password=db_credentials['password'],
    database=db_credentials['dbname']
)
```

### 5. WAF（Web Application Firewall）

#### WAF 架构

```
┌──────────────────────────────────────────────────────────────┐
│                    WAF 架构                                    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    WAF Web ACL                       │    │
│  │                                                     │    │
│  │  规则组（Rule Groups）：                              │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  AWS Managed Rules                           │  │    │
│  │  │  - Core Rule Set (CRS)                       │  │    │
│  │  │  - Known Bad Inputs                          │  │    │
│  │  │  - SQL Injection                             │  │    │
│  │  │  - Linux/Windows OS Protection               │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │  自定义规则                                    │  │    │
│  │  │  - IP 白名单/黑名单                           │  │    │
│  │  │  - 地理位置限制                               │  │    │
│  │  │  - 速率限制                                  │  │    │
│  │  │  - 字符串匹配                                │  │    │
│  │  │  - 正则表达式                                │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│           ┌──────────────┼──────────────┐                    │
│           ▼              ▼              ▼                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  ALB         │  │  API Gateway │  │  CloudFront  │        │
│  │  负载均衡器   │  │  API 网关    │  │  CDN         │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

#### WAF 配置

```bash
# 创建 Web ACL
aws wafv2 create-web-acl \
  --name my-web-acl \
  --scope REGIONAL \
  --default-action '{"Allow":{}}' \
  --rules '[
    {
      "Name": "AWSManagedRulesCommonRuleSet",
      "Priority": 1,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": {"None":{}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "AWSManagedRulesCommonRuleSet"
      }
    },
    {
      "Name": "RateLimitRule",
      "Priority": 2,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "Action": {"Block":{}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimitRule"
      }
    },
    {
      "Name": "GeoBlockRule",
      "Priority": 3,
      "Statement": {
        "GeoMatchStatement": {
          "CountryCodes": ["CN", "RU"]
        }
      },
      "Action": {"Block":{}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "GeoBlockRule"
      }
    }
  ]' \
  --visibility-config '{
    "SampledRequestsEnabled": true,
    "CloudWatchMetricsEnabled": true,
    "MetricName": "my-web-acl"
  }'

# 关联 ALB
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789012:regional/webacl/my-web-acl/abc123 \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/abc123

# 关联 API Gateway
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789012:regional/webacl/my-web-acl/abc123 \
  --resource-arn arn:aws:apigateway:us-east-1::/restapis/my-api/stages/prod

# 查看 WAF 日志
aws wafv2 get-logging-configuration \
  --resource-arn arn:aws:wafv2:us-east-1:123456789012:regional/webacl/my-web-acl/abc123
```

### 6. Shield（DDoS 防护）

#### Shield Standard vs Shield Advanced

| 特性 | Shield Standard | Shield Advanced |
|------|----------------|-----------------|
| 费用 | 免费 | $3,000/月 + 数据传输费 |
| 防护层 | Layer 3/4 | Layer 3/4/7 |
| 自动防护 | 是 | 是 |
| DDoS 响应团队 | 否 | 是（24/7） |
| 费用保护 | 否 | 是（DDoS 期间） |
| 详细报告 | 否 | 是 |
| WAF 集成 | 否 | 是 |
| 适用场景 | 基础防护 | 高安全需求 |

#### Shield 配置

```bash
# 启用 Shield Advanced
aws shield create-protection \
  --name my-alb-protection \
  --resource-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/abc123

# 创建 Shield 响应团队联系人
aws shield create-emergency-contact-contents \
  --emergency-contact-list '[
    {
      "EmailAddress": "sre@example.com",
      "PhoneNumber": "+1-555-123-4567",
      "ContactNotes": "SRE Team primary contact"
    }
  ]'

# 创建 Shield 保护组
aws shield create-protection-group \
  --protection-group-id my-protection-group \
  --aggregation MAX \
  --pattern ALL \
  --resource-type ELASTIC_LOAD_BALANCING

# 查看 DDoS 事件
aws shield describe-attacks \
  --resource-arns arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/abc123 \
  --start-time FromInclusion=2026-01-01T00:00:00Z \
  --end-time ToExclusion=2026-05-03T00:00:00Z
```

### 7. GuardDuty（威胁检测）

#### GuardDuty 概述

```
┌──────────────────────────────────────────────────────────────┐
│                    GuardDuty 威胁检测                         │
│                                                               │
│  数据源：                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  VPC     │  │  Cloud   │  │  DNS     │  │  EBS     │    │
│  │  Flow    │  │  Trail   │  │  Logs    │  │  Volume  │    │
│  │  Logs    │  │  Logs    │  │          │  │  数据    │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │            │
│       └─────────────┴─────────────┴─────────────┘            │
│                          │                                    │
│                    ┌─────▼─────┐                              │
│                    │ GuardDuty │                              │
│                    │  ML 引擎  │                              │
│                    └─────┬─────┘                              │
│                          │                                    │
│           ┌──────────────┼──────────────┐                    │
│           ▼              ▼              ▼                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  威胁发现     │ │  安全中心    │ │  EventBridge │        │
│  │  (Findings)  │ │  (Security   │ │  自动响应     │        │
│  │              │ │   Hub)       │ │              │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                               │
│  检测类型：                                                    │
│  - 未授权访问（UnauthorizedAccess）                           │
│  - 异常行为（Behavior）                                       │
│  - 恶意软件（Trojan）                                         │
│  - 加密货币挖矿（CryptoCurrency）                             │
│  - IAM 威胁（IAMUser）                                       │
└──────────────────────────────────────────────────────────────┘
```

#### GuardDuty 配置

```bash
# 启用 GuardDuty
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES

# 获取 Detector ID
DETECTOR_ID=$(aws guardduty list-detectors --query 'DetectorIds[0]' --output text)

# 列出发现
aws guardduty list-findings \
  --detector-id "$DETECTOR_ID" \
  --finding-criteria '{
    "Criterion": {
      "severity": {
        "Gte": 4
      }
    }
  }'

# 获取发现详情
aws guardduty get-findings \
  --detector-id "$DETECTOR_ID" \
  --finding-ids "finding-id-1" "finding-id-2"

# 创建 IP 白名单
aws guardduty create-ip-set \
  --detector-id "$DETECTOR_ID" \
  --name trusted-ips \
  --format TXT \
  --location s3://my-bucket/trusted-ips.txt \
  --activate

# 创建威胁情报集
aws guardduty create-threat-intel-set \
  --detector-id "$DETECTOR_ID" \
  --name threat-ips \
  --format TXT \
  --location s3://my-bucket/threat-ips.txt \
  --activate
```

### 8. Security Hub（安全中心）

#### Security Hub 概述

```
┌──────────────────────────────────────────────────────────────┐
│                    Security Hub 架构                           │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    Security Hub                       │    │
│  │                                                     │    │
│  │  安全标准：                                          │    │
│  │  ├── AWS Foundational Security Best Practices       │    │
│  │  ├── CIS AWS Foundations Benchmark                  │    │
│  │  ├── PCI DSS                                        │    │
│  │  └── NIST 800-53                                    │    │
│  │                                                     │    │
│  │  集成服务：                                          │    │
│  │  ├── GuardDuty（威胁检测）                           │    │
│  │  ├── Inspector（漏洞扫描）                           │    │
│  │  ├── Macie（数据分类）                               │    │
│  │  ├── IAM Access Analyzer                            │    │
│  │  ├── Firewall Manager                               │    │
│  │  └── 第三方安全工具                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│           ┌──────────────┼──────────────┐                    │
│           ▼              ▼              ▼                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  自动修复     │ │  安全评分    │ │  合规报告    │        │
│  │  (EventBridge)│ │  (Dashboard) │ │  (Export)    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

#### Security Hub 配置

```bash
# 启用 Security Hub
aws securityhub enable-security-hub \
  --enable-default-standards

# 启用安全标准
aws securityhub batch-enable-standards \
  --standards-subscription-requests '[
    {
      "StandardsArn": "arn:aws:securityhub:::standards/aws-foundational-security-best-practices/v/1.0.0"
    },
    {
      "StandardsArn": "arn:aws:securityhub:us-east-1::standards/cis-aws-foundations-benchmark/v/1.2.0"
    }
  ]'

# 获取安全发现
aws securityhub get-findings \
  --filters '{
    "SeverityLabel": [
      {
        "Value": "CRITICAL",
        "Comparison": "EQUALS"
      }
    ],
    "WorkflowStatus": [
      {
        "Value": "NEW",
        "Comparison": "EQUALS"
      }
    ]
  }' \
  --max-items 100

# 获取合规状态
aws securityhub get-enabled-standards

# 创建自定义洞察（Insight）
aws securityhub create-insight \
  --name "Critical Findings" \
  --filters '{
    "SeverityLabel": [
      {
        "Value": "CRITICAL",
        "Comparison": "EQUALS"
      }
    ]
  }' \
  --group-by-resource-type
```

### 9. 合规框架

#### AWS 合规服务

```
┌──────────────────────────────────────────────────────────────┐
│                    AWS 合规服务                                │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AWS Config                                          │    │
│  │  - 资源配置记录                                      │    │
│  │  - 配置规则（合规检查）                               │    │
│  │  - 资源变更历史                                      │    │
│  │  - 自动修复                                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AWS Audit Manager                                   │    │
│  │  - 自动收集审计证据                                   │    │
│  │  - 支持多种合规框架                                   │    │
│  │  - 生成审计报告                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AWS Artifact                                        │    │
│  │  - 合规报告下载                                       │    │
│  │  - 合同管理                                          │    │
│  │  - SOC, ISO, PCI DSS 报告                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  常见合规框架：                                                │
│  - SOC 1/2/3                                                │
│  - ISO 27001/27017/27018                                    │
│  - PCI DSS                                                  │
│  - HIPAA                                                    │
│  - GDPR                                                     │
│  - FedRAMP                                                  │
└──────────────────────────────────────────────────────────────┘
```

#### AWS Config 配置

```bash
# 启用 AWS Config
aws configservice put-configuration-recorder \
  --configuration-recorder '{
    "name": "default",
    "roleARN": "arn:aws:iam::123456789012:role/aws-config-role",
    "recordingGroup": {
      "allSupported": true,
      "includeGlobalResourceTypes": true
    }
  }'

aws configservice put-delivery-channel \
  --delivery-channel '{
    "name": "default",
    "s3BucketName": "my-config-bucket",
    "configSnapshotDeliveryProperties": {
      "deliveryFrequency": "TwentyFour_Hours"
    }
  }'

aws configservice start-configuration-recorder \
  --configuration-recorder-name default

# 创建合规规则
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-ssl-only",
    "Description": "S3 bucket policy should require SSL",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_SSL_REQUESTS_ONLY"
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::S3::Bucket"]
    }
  }'

# 评估合规状态
aws configservice describe-compliance-by-config-rule \
  --config-rule-names s3-bucket-ssl-only

# 获取不合规资源
aws configservice get-compliance-details-by-config-rule \
  --config-rule-name s3-bucket-ssl-only \
  --compliance-types NON_COMPLIANT
```

### 10. SRE 实战案例

#### 场景：多层安全架构

```
┌──────────────────────────────────────────────────────────────┐
│              多层安全架构                                       │
│                                                               │
│  边缘层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Route 53 → CloudFront + WAF + Shield Advanced       │    │
│  │  - DDoS 防护                                          │    │
│  │  - Web 应用防火墙                                      │    │
│  │  - 地理位置限制                                        │    │
│  │  - 速率限制                                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  网络层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  VPC                                                  │    │
│  │  ├── Security Groups（最小权限）                      │    │
│  │  ├── NACLs（子网级防护）                              │    │
│  │  ├── VPC Flow Logs（流量审计）                        │    │
│  │  └── Private Subnets（无公网访问）                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  应用层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  IAM                                                │    │
│  │  ├── 最小权限策略                                    │    │
│  │  ├── MFA 强制                                        │    │
│  │  ├── IRSA (EKS)                                      │    │
│  │  └── 条件键（IP, MFA, Region）                      │    │
│  │                                                     │    │
│  │  数据加密                                            │    │
│  │  ├── 传输中：TLS 1.2+                               │    │
│  │  ├── 静态：KMS (SSE-KMS)                            │    │
│  │  └── 密钥管理：自动轮换                              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  监控层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  GuardDuty（威胁检测）                                │    │
│  │  Security Hub（安全中心）                             │    │
│  │  CloudTrail（API 审计）                               │    │
│  │  CloudWatch（告警）                                   │    │
│  │  Config（合规检查）                                    │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 故障排查：安全事件响应

```
安全事件响应流程：

1. 检测阶段
   - GuardDuty 发现异常：UnauthorizedAccess:EC2/MaliciousIPCaller
   - Security Hub 显示 CRITICAL 发现
   - CloudWatch 告警触发

2. 分析阶段
   - 查看 CloudTrail 日志：谁在什么时间做了什么
   - 查看 VPC Flow Logs：网络流量分析
   - 查看 GuardDuty 发现详情

3. 遏制阶段
   - 隔离受感染实例：修改 Security Group
   - 撤销 IAM 凭证：删除访问密钥
   - 阻止恶意 IP：更新 WAF 规则

4. 修复阶段
   - 清理恶意软件
   - 修补漏洞
   - 更新安全配置

5. 恢复阶段
   - 恢复服务
   - 验证安全
   - 监控异常

6. 总结阶段
   - 编写事件报告
   - 更新安全策略
   - 改进监控告警
```

---

## 💻 实战练习

### 练习 1：基础操作 — IAM 安全配置

**目标**：创建安全的 IAM 配置，包括角色、策略和 MFA

```bash
# 步骤 1：创建 IAM 角色
aws iam create-role \
  --role-name SRE-Lab-Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "ec2.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# 步骤 2：创建最小权限策略
aws iam create-policy \
  --policy-name SRE-Lab-Policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:ListBucket",
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource": "*",
        "Condition": {
          "StringEquals": {
            "aws:RequestedRegion": "us-east-1"
          }
        }
      }
    ]
  }'

# 步骤 3：附加策略到角色
aws iam attach-role-policy \
  --role-name SRE-Lab-Role \
  --policy-arn arn:aws:iam::123456789012:policy/SRE-Lab-Policy

# 步骤 4：验证角色配置
aws iam get-role --role-name SRE-Lab-Role
aws iam list-attached-role-policies --role-name SRE-Lab-Role

# 清理
aws iam detach-role-policy \
  --role-name SRE-Lab-Role \
  --policy-arn arn:aws:iam::123456789012:policy/SRE-Lab-Policy
aws iam delete-policy --policy-arn arn:aws:iam::123456789012:policy/SRE-Lab-Policy
aws iam delete-role --role-name SRE-Lab-Role
```

### 练习 2：进阶场景 — Secrets Manager 和 KMS

**目标**：创建和管理密钥，配置自动轮换

```bash
# 步骤 1：创建 KMS 密钥
KEY_ID=$(aws kms create-key \
  --description "SRE Lab encryption key" \
  --query 'KeyMetadata.KeyId' --output text)

# 步骤 2：创建别名
aws kms create-alias \
  --alias-name alias/sre-lab-key \
  --target-key-id "$KEY_ID"

# 步骤 3：使用 KMS 加密
ENCRYPTED=$(aws kms encrypt \
  --key-id alias/sre-lab-key \
  --plaintext "My secret data" \
  --query 'CiphertextBlob' --output text)

echo "$ENCRYPTED"

# 步骤 4：解密
aws kms decrypt \
  --ciphertext-blob "fileb://<(echo $ENCRYPTED | base64 -d)" \
  --query 'Plaintext' --output text

# 步骤 5：创建 Secret
aws secretsmanager create-secret \
  --name sre-lab/test-secret \
  --secret-string '{"username":"admin","password":"SecurePass123!"}'

# 步骤 6：获取 Secret
aws secretsmanager get-secret-value \
  --secret-id sre-lab/test-secret \
  --query 'SecretString' --output text

# 清理
aws secretsmanager delete-secret \
  --secret-id sre-lab/test-secret \
  --force-delete-without-recovery
aws kms schedule-key-deletion \
  --key-id "$KEY_ID" \
  --pending-window-in-days 7
```

### 练习 3：故障排查挑战 — 安全事件分析

**场景**：GuardDuty 检测到异常活动，分析并响应

```bash
# 步骤 1：启用 GuardDuty
DETECTOR_ID=$(aws guardduty create-detector \
  --enable \
  --query 'DetectorId' --output text)

echo "Detector ID: $DETECTOR_ID"

# 步骤 2：等待并查看发现（可能需要几分钟）
aws guardduty list-findings \
  --detector-id "$DETECTOR_ID"

# 步骤 3：创建 IP 白名单
cat <<EOF > trusted-ips.txt
203.0.113.0/24
198.51.100.0/24
EOF

aws s3 cp trusted-ips.txt s3://sre-lab-security/trusted-ips.txt

aws guardduty create-ip-set \
  --detector-id "$DETECTOR_ID" \
  --name trusted-ips \
  --format TXT \
  --location s3://sre-lab-security/trusted-ips.txt \
  --activate

# 步骤 4：验证配置
aws guardduty list-ip-sets --detector-id "$DETECTOR_ID"

# 挑战：编写脚本自动处理 GuardDuty 发现
# 提示：使用 EventBridge 触发 Lambda 自动响应

# 清理
aws guardduty delete-detector --detector-id "$DETECTOR_ID"
```

---

## 🎯 面试题精选

### Q1: IAM 最佳实践有哪些？

**答案**：
1. 根账户启用 MFA，不用于日常操作
2. 最小权限原则，定期审查权限
3. 使用角色而非长期凭证
4. 所有用户启用 MFA
5. 定期轮换访问密钥
6. 使用条件键增强安全性
7. 使用 IAM Access Analyzer 检测未使用的权限

### Q2: SSE-S3、SSE-KMS 和 SSE-C 有什么区别？

**答案**：
| 特性 | SSE-S3 | SSE-KMS | SSE-C |
|------|--------|---------|-------|
| 密钥管理 | S3 管理 | KMS 管理 | 客户提供 |
| 审计能力 | 无 | CloudTrail | 无 |
| 费用 | 免费 | KMS 收费 | 免费 |
| 密钥轮换 | 自动 | 可配置 | 手动 |
| 适用场景 | 一般加密 | 需要审计 | 混合云 |

### Q3: WAF 的规则优先级如何设计？

**答案**：
1. **高优先级**：速率限制（防 DDoS）
2. **中优先级**：AWS 托管规则组（SQL 注入、XSS）
3. **低优先级**：自定义规则（IP 黑名单、地理位置）
4. 最后：默认允许或拒绝

### Q4: GuardDuty 如何检测威胁？

**答案**：
GuardDuty 通过以下数据源进行 ML 分析：
- VPC Flow Logs（网络流量模式）
- CloudTrail Logs（API 调用模式）
- DNS Logs（域名解析模式）
- EBS Volume 数据（恶意软件扫描）
- Kubernetes 审计日志
- S3 数据事件

### Q5: Security Hub 的作用是什么？

**答案**：
Security Hub 是 AWS 的安全中心服务：
- 聚合多个安全服务的发现（GuardDuty、Inspector、Macie 等）
- 执行安全标准评估（AWS 最佳实践、CIS、PCI DSS）
- 提供安全评分和合规状态
- 支持自动修复（通过 EventBridge）
- 生成合规报告

### Q6: 如何设计一个合规的 AWS 架构？

**答案**：
1. 启用 CloudTrail 记录所有 API 调用
2. 启用 AWS Config 记录资源配置
3. 使用 Security Hub 执行合规检查
4. 使用 KMS 加密所有敏感数据
5. 使用 VPC 和安全组隔离网络
6. 使用 IAM 最佳实践控制访问
7. 定期生成合规报告

### Q7: KMS 的信封加密是什么？

**答案**：
信封加密是一种高效的数据加密方式：
1. 生成数据密钥（Data Key）
2. 用数据密钥加密数据（性能好）
3. 用 CMK 加密数据密钥（安全性高）
4. 存储加密后的数据密钥 + 加密后的数据
优势：避免每次都调用 KMS API，降低成本和延迟

---

## 📚 深入阅读

- [AWS 安全最佳实践](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [KMS 开发者指南](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html)
- [Secrets Manager 用户指南](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [WAF 开发者指南](https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html)
- [GuardDuty 用户指南](https://docs.aws.amazon.com/guardduty/latest/ug/what-is-guardduty.html)
- [Security Hub 用户指南](https://docs.aws.amazon.com/securityhub/latest/userguide/what-is-securityhub.html)

---

## ✅ 自检清单

- [ ] 能够设计最小权限的 IAM 策略
- [ ] 理解 KMS 加密体系和信封加密
- [ ] 能够使用 Secrets Manager 管理敏感信息
- [ ] 能够配置 WAF 规则防护 Web 应用
- [ ] 理解 Shield Standard 和 Advanced 的区别
- [ ] 能够启用 GuardDuty 并分析威胁发现
- [ ] 能够使用 Security Hub 进行安全评估
- [ ] 能够设计合规的 AWS 安全架构
