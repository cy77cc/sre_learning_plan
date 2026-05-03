# Day 116: AWS 高可用架构

> 📅 日期：2026-05-03
> 📖 学习主题：AWS 高可用架构 — Well-Architected Framework、多可用区架构、Auto Scaling、ELB 故障转移、Route 53 健康检查、灾难恢复模式
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 105 (AWS 简介), Day 107 (VPC), Day 110 (EC2), Day 115 (AWS 安全)

## 🎯 学习目标

1. 理解 AWS Well-Architected Framework 的五大支柱
2. 掌握多可用区（Multi-AZ）架构设计原则
3. 能够配置 Auto Scaling Group 和 Launch Template
4. 掌握 ELB（ALB/NLB）跨可用区故障转移
5. 理解 Route 53 健康检查和故障转移路由策略
6. 掌握四种灾难恢复模式及其适用场景
7. 理解 RTO/RPO 概念及其在架构设计中的应用

---

## 📖 核心知识点

### 1. AWS Well-Architected Framework 五大支柱

AWS Well-Architected Framework 提供了一套构建云端架构的最佳实践，包含五大支柱：

```
┌──────────────────────────────────────────────────────────────┐
│           AWS Well-Architected Framework 五大支柱              │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │        ┌───────────────────────┐                    │    │
│  │        │      卓越运营          │                    │    │
│  │        │   Operational          │                    │    │
│  │        │   Excellence           │                    │    │
│  │        └───────────┬───────────┘                    │    │
│  │                    │                                 │    │
│  │  ┌─────────────────┼─────────────────┐              │    │
│  │  │                 │                 │              │    │
│  │  ▼                 ▼                 ▼              │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐        │    │
│  │  │  安全性    │ │  可靠性    │ │  性能效率  │        │    │
│  │  │ Security  │ │Reliability │ │Performance│        │    │
│  │  │           │ │            │ │ Efficiency│        │    │
│  │  └───────────┘ └───────────┘ └───────────┘        │    │
│  │                    │                                 │    │
│  │                    ▼                                 │    │
│  │            ┌───────────────┐                        │    │
│  │            │   成本优化     │                        │    │
│  │            │    Cost        │                        │    │
│  │            │  Optimization  │                        │    │
│  │            └───────────────┘                        │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 各支柱详解

```
┌──────────────────────────────────────────────────────────────┐
│  支柱 1：卓越运营（Operational Excellence）                     │
│                                                               │
│  核心原则：                                                    │
│  ├── 运营即代码（Operations as Code）                          │
│  │   ├── 使用 IaC（Terraform/CloudFormation）管理基础设施      │
│  │   ├── 使用 CI/CD 自动化部署流程                            │
│  │   └── 使用自动化测试验证变更                                │
│  ├── 注释文档（Make Frequent, Small, Reversible Changes）     │
│  │   ├── 小步快跑，频繁发布                                   │
│  │   ├── 可回滚的变更                                         │
│  │   └── 完整的变更日志                                       │
│  ├── 持续改进（Refine Operations Procedures Frequently）      │
│  │   ├── 定期演练故障恢复                                     │
│  │   ├── 从事故中学习（Post-incident review）                 │
│  │   └── 持续优化运维流程                                     │
│  └── 预测失败（Anticipate Failure）                            │
│      ├── 故障注入测试（Chaos Engineering）                    │
│      ├── 使用 GameDay 演练                                    │
│      └── 建立故障响应流程                                     │
│                                                               │
│  SRE 关键实践：                                                │
│  - SLI/SLO/SLA 体系                                          │
│  - 错误预算管理                                               │
│  - 自动化运维（AIOps）                                        │
│  - 事故管理流程                                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  支柱 2：安全性（Security）                                     │
│                                                               │
│  核心原则：                                                    │
│  ├── 实现强身份基础（Implement a Strong Identity Foundation）  │
│  │   ├── 集中身份管理（AWS SSO / IAM Identity Center）        │
│  │   ├── 最小权限原则                                         │
│  │   └── MFA 强制启用                                         │
│  ├── 使安全可追溯（Enable Traceability）                       │
│  │   ├── CloudTrail 审计日志                                  │
│  │   ├── VPC Flow Logs                                       │
│  │   └── 实时告警和自动响应                                   │
│  ├── 在所有层应用安全性（Apply Security at All Layers）        │
│  │   ├── 边缘层：WAF + Shield + CloudFront                   │
│  │   ├── 网络层：VPC + SG + NACL                             │
│  │   ├── 应用层：IAM + 加密                                  │
│  │   └── 数据层：KMS + 加密存储                               │
│  └── 自动化安全最佳实践（Automate Security Best Practices）    │
│      ├── Security Hub 统一安全视图                             │
│      ├── Config 合规检查                                      │
│      └── 自动修复                                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  支柱 3：可靠性（Reliability）                                  │
│                                                               │
│  核心原则：                                                    │
│  ├── 自动从故障中恢复（Automatically Recover from Failure）    │
│  │   ├── 健康检查 + 自动替换                                  │
│  │   ├── Auto Scaling 自动恢复容量                            │
│  │   └── Route 53 故障转移                                    │
│  ├── 横向扩展以满足需求（Scale Horizontally）                  │
│  │   ├── 无状态应用设计                                       │
│  │   ├── Auto Scaling Group                                   │
│  │   └── 负载均衡分散请求                                     │
│  ├── 停止猜测容量（Stop Guessing Capacity）                   │
│  │   ├── 使用 CloudWatch 监控指标                             │
│  │   ├── 基于指标的自动扩缩                                   │
│  │   └── 定期容量规划                                         │
│  └── 管理自动化中的变更（Manage Change in Automation）         │
│      ├── IaC 管理基础设施                                     │
│      ├── 自动化部署                                           │
│      └── 版本控制                                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  支柱 4：性能效率（Performance Efficiency）                     │
│                                                               │
│  核心原则：                                                    │
│  ├── 高效地使用计算资源（Democratize Advanced Technologies）   │
│  │   ├── 使用托管服务（RDS、ElastiCache、EKS）                │
│  │   ├── 无服务器架构（Lambda、Fargate）                      │
│  │   └── 减少运维负担                                         │
│  ├── 考虑全球部署（Go Global in Minutes）                     │
│  │   ├── 多区域部署                                           │
│  │   ├── CloudFront CDN                                      │
│  │   └── Route 53 地理路由                                    │
│  ├── 使用无服务器架构（Use Serverless Architectures）          │
│  │   ├── Lambda 按需执行                                      │
│  │   ├── DynamoDB 按需容量                                    │
│  │   └── Fargate 无服务器容器                                 │
│  └── 实验更频繁（Experiment More Often）                       │
│      ├── A/B 测试                                             │
│      ├── 蓝绿部署                                             │
│      └── 金丝雀发布                                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  支柱 5：成本优化（Cost Optimization）                          │
│                                                               │
│  核心原则：                                                    │
│  ├── 实施云财务管理（Implement Cloud Financial Management）    │
│  │   ├── 成本分配标签                                         │
│  │   ├── 预算告警                                             │
│  │   └── Cost Explorer 分析                                   │
│  ├── 采用消费模型（Adopt a Consumption Model）                │
│  │   ├── 按需付费 vs 预留实例                                 │
│  │   ├── Spot Instance 节省成本                               │
│  │   └── Auto Scaling 匹配需求                                │
│  ├── 衡量整体效率（Measure Overall Efficiency）                │
│  │   ├── 单位成本指标                                         │
│  │   ├── 资源利用率监控                                       │
│  │   └── 定期 Right Sizing                                    │
│  └── 停止为无差别繁重工作付费（Stop Spending on Undifferentiated Heavy Lifting）│
│      ├── 使用托管服务                                         │
│      ├── 自动化重复任务                                       │
│      └── 减少运维人力成本                                     │
└──────────────────────────────────────────────────────────────┘
```

### 2. 多可用区（Multi-AZ）架构设计

#### 可用区与区域概念

```
┌──────────────────────────────────────────────────────────────┐
│                    AWS 区域与可用区                             │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Region: us-east-1 (N. Virginia)                     │    │
│  │                                                     │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐│    │
│  │  │  AZ: us-east │  │  AZ: us-east │  │ AZ: us-east││    │
│  │  │    -1a       │  │    -1b       │  │   -1c      ││    │
│  │  │              │  │              │  │            ││    │
│  │  │  ┌────────┐  │  │  ┌────────┐  │  │ ┌────────┐ ││    │
│  │  │  │子网 A  │  │  │  │子网 B  │  │  │ │子网 C  │ ││    │
│  │  │  │10.0.1.0│  │  │  │10.0.2.0│  │  │ │10.0.3.0│ ││    │
│  │  │  └────────┘  │  │  └────────┘  │  │ └────────┘ ││    │
│  │  │              │  │              │  │            ││    │
│  │  │  独立的电力   │  │  独立的电力   │  │ 独立的电力  ││    │
│  │  │  独立的网络   │  │  独立的网络   │  │ 独立的网络  ││    │
│  │  │  独立的冷却   │  │  独立的冷却   │  │ 独立的冷却  ││    │
│  │  └──────────────┘  └──────────────┘  └────────────┘│    │
│  │                                                     │    │
│  │  AZ 之间通过低延迟链路连接（< 10ms）                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  关键特性：                                                    │
│  - 每个 AZ 至少 1 个数据中心                                  │
│  - AZ 之间物理隔离（独立电力、网络、冷却）                     │
│  - AZ 之间通过私有低延迟光纤连接                               │
│  - 同一区域不同 AZ 之间延迟通常 < 2ms                         │
└──────────────────────────────────────────────────────────────┘
```

#### Multi-AZ 架构模式

```
┌──────────────────────────────────────────────────────────────┐
│                    Multi-AZ 高可用架构                         │
│                                                               │
│                    ┌───────────────┐                          │
│                    │   Route 53    │                          │
│                    │  (DNS 解析)   │                          │
│                    └───────┬───────┘                          │
│                            │                                  │
│                    ┌───────▼───────┐                          │
│                    │      ALB      │                          │
│                    │  (跨 AZ 分发) │                          │
│                    └───────┬───────┘                          │
│                            │                                  │
│            ┌───────────────┼───────────────┐                  │
│            │               │               │                  │
│    ┌───────▼───────┐ ┌────▼────────┐ ┌────▼────────┐        │
│    │   AZ-1a       │ │   AZ-1b     │ │   AZ-1c     │        │
│    │               │ │             │ │             │        │
│    │ ┌───────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │        │
│    │ │  EC2      │ │ │ │  EC2    │ │ │ │  EC2    │ │        │
│    │ │  Instance │ │ │ │Instance │ │ │ │Instance │ │        │
│    │ │  (Web)    │ │ │ │ (Web)   │ │ │ │ (Web)   │ │        │
│    │ └───────────┘ │ │ └─────────┘ │ │ └─────────┘ │        │
│    │               │ │             │ │             │        │
│    │ ┌───────────┐ │ │ ┌─────────┐ │ │             │        │
│    │ │  RDS      │ │ │ │  RDS    │ │ │             │        │
│    │ │  Primary  │ │ │ │Standby  │ │ │             │        │
│    │ │  (主库)   │ │ │ │(备库)   │ │ │             │        │
│    │ └───────────┘ │ │ └─────────┘ │ │             │        │
│    └───────────────┘ └─────────────┘ └─────────────┘        │
│                                                               │
│  流量路径：                                                    │
│  1. 用户请求 → Route 53 DNS 解析                             │
│  2. DNS 解析到 ALB                                            │
│  3. ALB 跨 AZ 分发请求（基于轮询/最少连接）                   │
│  4. EC2 实例处理请求                                          │
│  5. RDS 自主故障转移（< 60 秒）                               │
└──────────────────────────────────────────────────────────────┘
```

#### Multi-AZ 配置示例

```bash
# 创建跨多个 AZ 的子网
# AZ-1a 子网
aws ec2 create-subnet \
  --vpc-id vpc-0123456789abcdef0 \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=Web-Subnet-AZ1a}]'

# AZ-1b 子网
aws ec2 create-subnet \
  --vpc-id vpc-0123456789abcdef0 \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=Web-Subnet-AZ1b}]'

# AZ-1c 子网
aws ec2 create-subnet \
  --vpc-id vpc-0123456789abcdef0 \
  --cidr-block 10.0.3.0/24 \
  --availability-zone us-east-1c \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=Web-Subnet-AZ1c}]'

# 创建 RDS Multi-AZ 实例
aws rds create-db-instance \
  --db-instance-identifier mydb-multi-az \
  --db-instance-class db.t3.medium \
  --engine mysql \
  --master-username admin \
  --master-user-password MySecurePass123! \
  --allocated-storage 100 \
  --multi-az \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:05:00-sun:06:00" \
  --storage-encrypted \
  --vpc-security-group-ids sg-0123456789abcdef0 \
  --db-subnet-group-name mydb-subnet-group

# 创建 RDS 子网组（包含多个 AZ）
aws rds create-db-subnet-group \
  --db-subnet-group-name mydb-subnet-group \
  --db-subnet-group-description "Multi-AZ subnet group" \
  --subnet-ids '["subnet-aaa111","subnet-bbb222","subnet-ccc333"]'
```

### 3. Auto Scaling Group（ASG）

#### ASG 架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Auto Scaling Group 架构                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  Launch Template                      │    │
│  │  ├── AMI ID（镜像）                                   │    │
│  │  ├── Instance Type（实例类型）                        │    │
│  │  ├── Key Pair（密钥对）                               │    │
│  │  ├── Security Group（安全组）                         │    │
│  │  ├── IAM Instance Profile（角色）                    │    │
│  │  ├── User Data（启动脚本）                            │    │
│  │  ├── Block Device Mapping（存储）                    │    │
│  │  └── Network Interface（网络配置）                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Auto Scaling Group                       │    │
│  │                                                     │    │
│  │  配置参数：                                          │    │
│  │  ├── Min Size（最小实例数）                          │    │
│  │  ├── Max Size（最大实例数）                          │    │
│  │  ├── Desired Capacity（期望容量）                    │    │
│  │  ├── VPC Zone Identifier（子网列表）                 │    │
│  │  ├── Health Check Type（健康检查类型）               │    │
│  │  │   ├── EC2（实例状态检查）                         │    │
│  │  │   └── ELB（负载均衡器健康检查）                   │    │
│  │  ├── Health Check Grace Period（宽限期）             │    │
│  │  └── Termination Policy（终止策略）                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│           ┌──────────────┼──────────────┐                    │
│           ▼              ▼              ▼                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  Scaling      │ │  Scaling     │ │  Scaling     │        │
│  │  Policy       │ │  Policy      │ │  Policy      │        │
│  │  (目标追踪)   │ │  (步进)      │ │  (简单)      │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

#### Launch Template 配置

```bash
# 创建 Launch Template
aws ec2 create-launch-template \
  --launch-template-name WebServer-LT-v1 \
  --version-description "Web server v1.0" \
  --launch-template-data '{
    "ImageId": "ami-0123456789abcdef0",
    "InstanceType": "t3.medium",
    "KeyName": "my-key-pair",
    "SecurityGroupIds": ["sg-0123456789abcdef0"],
    "IamInstanceProfile": {
      "Name": "EC2-S3-ReadOnly-Profile"
    },
    "BlockDeviceMappings": [
      {
        "DeviceName": "/dev/xvda",
        "Ebs": {
          "VolumeSize": 30,
          "VolumeType": "gp3",
          "Encrypted": true,
          "DeleteOnTermination": true
        }
      }
    ],
    "Monitoring": {
      "Enabled": true
    },
    "TagSpecifications": [
      {
        "ResourceType": "instance",
        "Tags": [
          {"Key": "Name", "Value": "WebServer-ASG"},
          {"Key": "Environment", "Value": "production"}
        ]
      }
    ],
    "UserData": "'$(echo '#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello from $(hostname -f)</h1>" > /var/www/html/index.html' | base64)'"
  }'

# 创建新版本
aws ec2 create-launch-template-version \
  --launch-template-name WebServer-LT-v1 \
  --source-version 1 \
  --launch-template-data '{
    "InstanceType": "t3.large"
  }'

# 设置默认版本
aws ec2 modify-launch-template \
  --launch-template-name WebServer-LT-v1 \
  --default-version 2
```

#### Auto Scaling Group 配置

```bash
# 创建 Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name WebServer-ASG \
  --launch-template "LaunchTemplateName=WebServer-LT-v1,Version=2" \
  --min-size 2 \
  --max-size 10 \
  --desired-capacity 4 \
  --vpc-zone-identifier "subnet-aaa111,subnet-bbb222,subnet-ccc333" \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --target-group-arns "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-tg/abc123" \
  --termination-policies "OldestInstance" "Default" \
  --tags '[
    {
      "Key": "Name",
      "Value": "WebServer-ASG",
      "PropagateAtLaunch": true
    },
    {
      "Key": "Environment",
      "Value": "production",
      "PropagateAtLaunch": true
    }
  ]'

# 创建目标追踪扩缩策略（推荐）
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name WebServer-ASG \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    },
    "TargetValue": 70.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

# 创建步进扩缩策略
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name WebServer-ASG \
  --policy-name cpu-step-scaling \
  --policy-type StepScaling \
  --adjustment-type ChangeInCapacity \
  --step-adjustments '[
    {
      "MetricIntervalLowerBound": 0,
      "MetricIntervalUpperBound": 20,
      "ScalingAdjustment": 2
    },
    {
      "MetricIntervalLowerBound": 20,
      "MetricIntervalUpperBound": 40,
      "ScalingAdjustment": 4
    },
    {
      "MetricIntervalLowerBound": 40,
      "ScalingAdjustment": 6
    }
  ]'

# 创建计划扩缩策略（定时扩缩）
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name WebServer-ASG \
  --scheduled-action-name scale-up-morning \
  --recurrence "0 8 * * 1-5" \
  --min-size 4 \
  --desired-capacity 6

aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name WebServer-ASG \
  --scheduled-action-name scale-down-night \
  --recurrence "0 22 * * 1-5" \
  --min-size 2 \
  --desired-capacity 2
```

#### 扩缩策略对比

| 策略类型 | 适用场景 | 扩缩速度 | 精确度 | 复杂度 |
|---------|---------|---------|-------|-------|
| 目标追踪（Target Tracking） | 通用场景 | 中等 | 高 | 低 |
| 步进扩缩（Step Scaling） | 分阶段扩缩 | 快 | 中等 | 中等 |
| 简单扩缩（Simple Scaling） | 简单场景 | 慢 | 低 | 低 |
| 计划扩缩（Scheduled Scaling） | 可预测负载 | 可控 | 高 | 低 |
| 预测扩缩（Predictive Scaling） | 周期性负载 | 快 | 高 | 高 |

### 4. ELB 跨可用区故障转移

#### ALB vs NLB 对比

```
┌──────────────────────────────────────────────────────────────┐
│                    ALB vs NLB 对比                             │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ALB（Application Load Balancer）                    │    │
│  │                                                     │    │
│  │  特性：                                              │    │
│  │  ├── Layer 7（HTTP/HTTPS）                           │    │
│  │  ├── 基于内容的路由（Path/Host/Header）              │    │
│  │  ├── WebSocket 支持                                 │    │
│  │  ├── HTTP/2 支持                                    │    │
│  │  ├── WAF 集成                                       │    │
│  │  ├── Lambda 函数作为目标                             │    │
│  │  └── 慢启动（Slow Start）                           │    │
│  │                                                     │    │
│  │  适用场景：                                          │    │
│  │  - Web 应用                                          │    │
│  │  - 微服务架构                                        │    │
│  │  - 需要内容路由的场景                                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  NLB（Network Load Balancer）                        │    │
│  │                                                     │    │
│  │  特性：                                              │    │
│  │  ├── Layer 4（TCP/UDP/TLS）                          │    │
│  │  ├── 超低延迟（百万级请求/秒）                       │    │
│  │  ├── 静态 IP 地址                                   │    │
│  │  ├── 源 IP 保留                                     │    │
│  │  ├── WebSocket 支持                                 │    │
│  │  └── TLS 卸载                                       │    │
│  │                                                     │    │
│  │  适用场景：                                          │    │
│  │  - 高性能 TCP/UDP 应用                               │    │
│  │  - 需要静态 IP 的场景                                │    │
│  │  - 游戏服务器                                        │    │
│  │  - IoT 应用                                          │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### ALB 跨 AZ 故障转移配置

```
┌──────────────────────────────────────────────────────────────┐
│                    ALB 跨 AZ 故障转移                          │
│                                                               │
│                    ┌───────────────┐                          │
│                    │      ALB      │                          │
│                    │               │                          │
│                    │  AZ-1a: NLB  │                          │
│                    │  AZ-1b: NLB  │                          │
│                    │  AZ-1c: NLB  │                          │
│                    └───────┬───────┘                          │
│                            │                                  │
│            ┌───────────────┼───────────────┐                  │
│            │               │               │                  │
│    ┌───────▼───────┐ ┌────▼────────┐ ┌────▼────────┐        │
│    │   AZ-1a       │ │   AZ-1b     │ │   AZ-1c     │        │
│    │               │ │             │ │             │        │
│    │ ┌───────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │        │
│    │ │  Target   │ │ │ │ Target  │ │ │ │ Target  │ │        │
│    │ │  Group    │ │ │ │ Group   │ │ │ │ Group   │ │        │
│    │ │  (健康)   │ │ │ │ (健康)  │ │ │ │ (不健康)│ │        │
│    │ └───────────┘ │ │ └─────────┘ │ │ └─────────┘ │        │
│    │               │ │             │ │             │        │
│    │  ✓ 流量分发   │ │  ✓ 流量分发  │ │  ✗ 流量跳过  │        │
│    └───────────────┘ └─────────────┘ └─────────────┘        │
│                                                               │
│  故障转移过程：                                                │
│  1. ALB 持续对目标进行健康检查（默认 30 秒间隔）               │
│  2. 连续 2 次健康检查失败 → 标记目标为不健康                   │
│  3. ALB 停止向不健康目标发送流量                               │
│  4. 当目标恢复健康后，自动重新加入                             │
│  5. 跨 AZ 流量自动重新分配                                     │
└──────────────────────────────────────────────────────────────┘
```

```bash
# 创建 ALB
aws elbv2 create-load-balancer \
  --name my-app-alb \
  --type application \
  --scheme internet-facing \
  --subnets subnet-aaa111 subnet-bbb222 subnet-ccc333 \
  --security-groups sg-0123456789abcdef0 \
  --tags 'Key=Environment,Value=production'

# 创建 Target Group
aws elbv2 create-target-group \
  --name my-app-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-0123456789abcdef0 \
  --health-check-protocol HTTP \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher 'HttpCode=200' \
  --target-type instance

# 创建监听器
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-app-alb/abc123 \
  --protocol HTTP \
  --port 80 \
  --default-actions '[
    {
      "Type": "forward",
      "TargetGroupArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/my-app-tg/def456"
    }
  ]'

# 配置跨 AZ 负载均衡属性
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-app-alb/abc123 \
  --attributes '[
    {
      "Key": "load_balancing.cross_zone.enabled",
      "Value": "true"
    },
    {
      "Key": "idle_timeout.timeout_seconds",
      "Value": "60"
    }
  ]'
```

### 5. Route 53 健康检查与故障转移路由

#### Route 53 路由策略

```
┌──────────────────────────────────────────────────────────────┐
│                    Route 53 路由策略                           │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  简单路由（Simple Routing）                           │    │
│  │  - 单个资源的标准 DNS 记录                            │    │
│  │  - 一个域名对应多个 IP（轮询）                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  故障转移路由（Failover Routing）                     │    │
│  │  ├── 主记录（Primary）→ 活跃资源                     │    │
│  │  ├── 辅助记录（Secondary）→ 备用资源                  │    │
│  │  └── 健康检查失败 → 自动切换到辅助                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  地理位置路由（Geolocation Routing）                  │    │
│  │  - 基于用户地理位置返回不同记录                       │    │
│  │  - 适用场景：内容本地化、合规要求                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  地理位置邻近路由（Geoproximity Routing）              │    │
│  │  - 基于地理位置 + 偏差值（Bias）                     │    │
│  │  - 需要 Route 53 Traffic Flow                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  加权路由（Weighted Routing）                         │    │
│  │  - 按权重分配流量（百分比）                           │    │
│  │  - 适用场景：A/B 测试、蓝绿部署                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  多值应答路由（Multivalue Answer Routing）            │    │
│  │  - 返回多个健康 IP 地址                               │    │
│  │  - 类似简单路由但支持健康检查                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  IP 基于路由（IP-based Routing）                      │    │
│  │  - 基于客户端 IP 地址路由                             │    │
│  │  - 适用场景：CIDR 范围路由                            │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 健康检查与故障转移配置

```bash
# 创建健康检查
aws route53 create-health-check \
  --caller-reference "my-health-check-$(date +%s)" \
  --health-check-config '{
    "FullyQualifiedDomainName": "app.example.com",
    "Port": 443,
    "Type": "HTTPS",
    "ResourcePath": "/health",
    "FailureThreshold": 3,
    "RequestInterval": 30,
    "EnableSNI": true,
    "SearchString": "OK"
  }'

# 创建故障转移主记录
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "primary",
          "Failover": "PRIMARY",
          "HealthCheckId": "health-check-id-123",
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "my-app-alb-123456.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'

# 创建故障转移辅助记录
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "secondary",
          "Failover": "SECONDARY",
          "AliasTarget": {
            "HostedZoneId": "Z268NLBHZEXAMPLE",
            "DNSName": "my-backup-alb-789012.us-west-2.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'

# 创建加权路由记录
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "v1",
          "Weight": 90,
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "my-app-v1-alb.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "v2",
          "Weight": 10,
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "my-app-v2-alb.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'
```

### 6. 灾难恢复模式

#### 四种灾难恢复模式对比

```
┌──────────────────────────────────────────────────────────────┐
│                    灾难恢复模式对比                             │
│                                                               │
│  RTO (Recovery Time Objective)：恢复时间目标                   │
│  RPO (Recovery Point Objective)：恢复点目标                    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  模式 1：备份与恢复（Backup & Restore）               │    │
│  │                                                     │    │
│  │  主区域                    灾难恢复区域              │    │
│  │  ┌─────────────┐          ┌─────────────┐          │    │
│  │  │  运行中的    │          │  S3 存储桶   │          │    │
│  │  │  应用和数据  │ ──备份──→│  (备份数据)  │          │    │
│  │  │             │          │             │          │    │
│  │  └─────────────┘          └─────────────┘          │    │
│  │                                                     │    │
│  │  RTO: 数小时         RPO: 取决于备份频率              │    │
│  │  成本: 低             复杂度: 低                      │    │
│  │  适用: 非关键系统、开发/测试环境                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  模式 2：引导光（Pilot Light）                        │    │
│  │                                                     │    │
│  │  主区域                    灾难恢复区域              │    │
│  │  ┌─────────────┐          ┌─────────────┐          │    │
│  │  │  运行中的    │          │  最小化运行  │          │    │
│  │  │  应用和数据  │ ──同步──→│  (数据库等)  │          │    │
│  │  │             │          │             │          │    │
│  │  │  ┌───────┐  │          │  ┌───────┐  │          │    │
│  │  │  │  App  │  │          │  │  DB   │  │          │    │
│  │  │  │  DB   │  │          │  │ (运行) │  │          │    │
│  │  │  └───────┘  │          │  └───────┘  │          │    │
│  │  └─────────────┘          └─────────────┘          │    │
│  │                                                     │    │
│  │  RTO: 10-15 分钟      RPO: 秒级（数据库同步）        │    │
│  │  成本: 中等            复杂度: 中等                   │    │
│  │  适用: 重要业务系统                                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  模式 3：温备（Warm Standby）                         │    │
│  │                                                     │    │
│  │  主区域                    灾难恢复区域              │    │
│  │  ┌─────────────┐          ┌─────────────┐          │    │
│  │  │  全量运行    │          │  缩减运行    │          │    │
│  │  │             │          │             │          │    │
│  │  │  ┌───────┐  │          │  ┌───────┐  │          │    │
│  │  │  │ App x │  │          │  │ App x │  │          │    │
│  │  │  │ 10    │  │ ──同步──→│  │ 1-2   │  │          │    │
│  │  │  │       │  │          │  │       │  │          │    │
│  │  │  │  DB   │  │          │  │  DB   │  │          │    │
│  │  │  │ (主)  │  │          │  │ (同步) │  │          │    │
│  │  │  └───────┘  │          │  └───────┘  │          │    │
│  │  └─────────────┘          └─────────────┘          │    │
│  │                                                     │    │
│  │  RTO: 几分钟          RPO: 秒级                     │    │
│  │  成本: 中高            复杂度: 中等                   │    │
│  │  适用: 核心业务系统                                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  模式 4：多活（Multi-Site Active/Active）             │    │
│  │                                                     │    │
│  │  主区域                    灾难恢复区域              │    │
│  │  ┌─────────────┐          ┌─────────────┐          │    │
│  │  │  全量运行    │          │  全量运行    │          │    │
│  │  │             │          │             │          │    │
│  │  │  ┌───────┐  │          │  ┌───────┐  │          │    │
│  │  │  │ App x │  │          │  │ App x │  │          │    │
│  │  │  │ 10    │  │ ←─同步──→│  │ 10    │  │          │    │
│  │  │  │       │  │          │  │       │  │          │    │
│  │  │  │  DB   │  │          │  │  DB   │  │          │    │
│  │  │  │ (主)  │  │          │  │ (主)  │  │          │    │
│  │  │  └───────┘  │          │  └───────┘  │          │    │
│  │  └─────────────┘          └─────────────┘          │    │
│  │                                                     │    │
│  │  RTO: 实时            RPO: 0（零数据丢失）           │    │
│  │  成本: 高              复杂度: 高                     │    │
│  │  适用: 关键任务系统、金融系统                         │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 灾难恢复模式详细对比

| 模式 | RTO | RPO | 成本 | 复杂度 | 数据复制 | 适用场景 |
|------|-----|-----|------|--------|---------|---------|
| 备份与恢复 | 数小时 | 数小时 | 低 | 低 | 定期备份 | 非关键系统 |
| 引导光 | 10-15 分钟 | 秒级 | 中等 | 中等 | 数据库同步 | 重要业务 |
| 温备 | 几分钟 | 秒级 | 中高 | 中等 | 实时同步 | 核心业务 |
| 多活 | 实时 | 0 | 高 | 高 | 双向同步 | 关键任务 |

### 7. RTO/RPO 概念详解

```
┌──────────────────────────────────────────────────────────────┐
│                    RTO/RPO 概念                                │
│                                                               │
│  时间轴：                                                     │
│  ────────────────────────────────────────────────────────    │
│       │                    │                    │             │
│       ▼                    ▼                    ▼             │
│    上次备份               故障发生             服务恢复         │
│       │                    │                    │             │
│       │◄──── RPO ─────────►│                    │             │
│       │   (可接受的数据      │                    │             │
│       │    丢失时间)         │                    │             │
│       │                    │                    │             │
│       │                    │◄──── RTO ─────────►│             │
│       │                    │   (可接受的          │             │
│       │                    │    恢复时间)         │             │
│       │                    │                    │             │
│  ────────────────────────────────────────────────────────    │
│                                                               │
│  RPO 示例：                                                    │
│  ├── 每小时备份 → RPO = 1 小时                                │
│  ├── 每日备份 → RPO = 24 小时                                 │
│  ├── 实时同步 → RPO = 0                                       │
│  └── 每 15 分钟备份 → RPO = 15 分钟                           │
│                                                               │
│  RTO 示例：                                                    │
│  ├── 手动恢复 → RTO = 数小时                                  │
│  ├── 自动故障转移 → RTO = 分钟级                              │
│  ├── 多活架构 → RTO = 秒级/实时                               │
│  └── 热备 → RTO = 分钟级                                      │
│                                                               │
│  设计原则：                                                    │
│  - RTO/RPO 越小，成本越高                                     │
│  - 需要根据业务需求平衡成本和可用性                             │
│  - 关键系统需要更小的 RTO/RPO                                  │
│  - 定期测试灾难恢复流程                                        │
└──────────────────────────────────────────────────────────────┘
```

### 8. SRE 实战案例：电商系统高可用设计

#### 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│              电商系统高可用架构                                  │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  用户请求                                              │    │
│  │    │                                                   │    │
│  │    ▼                                                   │    │
│  │  Route 53 (故障转移路由 + 健康检查)                     │    │
│  │    │                                                   │    │
│  │    ├── Primary: ALB (us-east-1)                       │    │
│  │    └── Secondary: ALB (us-west-2)                     │    │
│  │          │                                             │    │
│  │          ▼                                             │    │
│  │  ┌─────────────────────────────────────────────┐      │    │
│  │  │  ALB (跨 AZ 负载均衡)                         │      │    │
│  │  │  ├── WAF 规则防护                            │      │    │
│  │  │  ├── HTTPS 卸载                              │      │    │
│  │  │  └── 路径路由（/api, /static, /images）      │      │    │
│  │  └─────────────────────────────────────────────┘      │    │
│  │          │                                             │    │
│  │          ▼                                             │    │
│  │  ┌─────────────────────────────────────────────┐      │    │
│  │  │  Auto Scaling Group                          │      │    │
│  │  │  ├── Min: 2, Max: 20, Desired: 4            │      │    │
│  │  │  ├── 目标追踪: CPU 60%, 请求 1000/分钟       │      │    │
│  │  │  ├── 计划扩缩: 早 8 点扩, 晚 10 点缩         │      │    │
│  │  │  └── 跨 3 个 AZ 部署                         │      │    │
│  │  └─────────────────────────────────────────────┘      │    │
│  │          │                                             │    │
│  │    ┌─────┴─────┬─────────────────┐                    │    │
│  │    ▼           ▼                 ▼                    │    │
│  │  ┌────────┐ ┌────────┐    ┌────────────┐             │    │
│  │  │RDS     │ │Elasti- │    │ CloudFront │             │    │
│  │  │Multi-AZ│ │Cache   │    │ + S3       │             │    │
│  │  │MySQL   │ │Redis   │    │ (静态资源)  │             │    │
│  │  │        │ │集群     │    │            │             │    │
│  │  └────────┘ └────────┘    └────────────┘             │    │
│  │          │                                             │    │
│  │          ▼                                             │    │
│  │  ┌─────────────────────────────────────────────┐      │    │
│  │  │  监控与告警                                    │      │    │
│  │  │  ├── CloudWatch 指标监控                     │      │    │
│  │  │  ├── SNS 告警通知                            │      │    │
│  │  │  ├── X-Ray 分布式追踪                        │      │    │
│  │  │  └── CloudTrail 审计日志                     │      │    │
│  │  └─────────────────────────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  关键设计决策：                                                │
│  1. ALB 跨 AZ 部署，确保单 AZ 故障不影响服务                 │
│  2. ASG 最小 2 个实例，确保始终有冗余                         │
│  3. RDS Multi-AZ，自动故障转移 < 60 秒                       │
│  4. ElastiCache Redis 集群，读写分离 + 自动故障转移          │
│  5. CloudFront CDN，加速静态资源                              │
│  6. Route 53 故障转移路由，区域级灾难恢复                     │
└──────────────────────────────────────────────────────────────┘
```

#### 实施步骤

```bash
# 步骤 1：创建 VPC 和子网
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# 步骤 2：创建 ALB
aws elbv2 create-load-balancer \
  --name ecommerce-alb \
  --type application \
  --scheme internet-facing \
  --subnets subnet-az1 subnet-az2 subnet-az3

# 步骤 3：创建 Launch Template
aws ec2 create-launch-template \
  --launch-template-name ecommerce-web-lt \
  --launch-template-data '{
    "ImageId": "ami-0123456789abcdef0",
    "InstanceType": "t3.large",
    "SecurityGroupIds": ["sg-web-servers"],
    "IamInstanceProfile": {"Name": "EC2-App-Role"},
    "UserData": "'$(base64 -w0 user-data.sh)'"
  }'

# 步骤 4：创建 Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name ecommerce-asg \
  --launch-template "LaunchTemplateName=ecommerce-web-lt" \
  --min-size 2 \
  --max-size 20 \
  --desired-capacity 4 \
  --vpc-zone-identifier "subnet-az1,subnet-az2,subnet-az3" \
  --health-check-type ELB \
  --target-group-arns "arn:aws:elasticloadbalancing:...:targetgroup/ecommerce-tg/..."

# 步骤 5：创建 RDS Multi-AZ
aws rds create-db-instance \
  --db-instance-identifier ecommerce-db \
  --db-instance-class db.r5.large \
  --engine mysql \
  --multi-az \
  --allocated-storage 500 \
  --storage-encrypted \
  --backup-retention-period 7

# 步骤 6：创建 ElastiCache Redis 集群
aws elasticache create-replication-group \
  --replication-group-id ecommerce-redis \
  --replication-group-description "Ecommerce Redis cluster" \
  --num-cache-clusters 3 \
  --cache-node-type cache.r5.large \
  --engine redis \
  --automatic-failover-enabled \
  --multi-az-enabled

# 步骤 7：创建 Route 53 健康检查和故障转移
aws route53 create-health-check \
  --caller-reference "ecommerce-primary-$(date +%s)" \
  --health-check-config '{
    "FullyQualifiedDomainName": "ecommerce.example.com",
    "Port": 443,
    "Type": "HTTPS",
    "ResourcePath": "/health",
    "FailureThreshold": 3,
    "RequestInterval": 30
  }'
```

---

## 💻 实战练习

### 练习 1：基础操作 — 创建高可用 Web 应用

**目标**：使用 ALB + ASG + Multi-AZ 部署一个高可用 Web 应用

```bash
# 步骤 1：创建 VPC 和子网（至少 2 个 AZ）
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --query 'Vpc.VpcId' --output text)

# 创建 2 个公有子网（不同 AZ）
SUBNET1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --query 'Subnet.SubnetId' --output text)

SUBNET2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --query 'Subnet.SubnetId' --output text)

# 步骤 2：创建安全组
SG_ID=$(aws ec2 create-security-group \
  --group-name ha-web-sg \
  --description "HA Web Security Group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# 允许 HTTP 和 SSH
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

# 步骤 3：创建 Launch Template
aws ec2 create-launch-template \
  --launch-template-name ha-web-lt \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "t3.micro",
    "SecurityGroupIds": ["'$SG_ID'"],
    "UserData": "'$(echo '#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
echo "<h1>Hello from $(hostname -f)</h1>" > /var/www/html/index.html' | base64 -w0)'"
  }'

# 步骤 4：创建 ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name ha-web-alb \
  --type application \
  --scheme internet-facing \
  --subnets $SUBNET1 $SUBNET2 \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# 创建 Target Group
TG_ARN=$(aws elbv2 create-target-group \
  --name ha-web-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id $VPC_ID \
  --health-check-path / \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# 创建监听器
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions '[{"Type":"forward","TargetGroupArn":"'$TG_ARN'"}]'

# 步骤 5：创建 Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name ha-web-asg \
  --launch-template "LaunchTemplateName=ha-web-lt,Version=1" \
  --min-size 2 \
  --max-size 6 \
  --desired-capacity 2 \
  --vpc-zone-identifier "$SUBNET1,$SUBNET2" \
  --health-check-type ELB \
  --target-group-arns "$TG_ARN"

# 步骤 6：验证
aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' --output text

# 清理
aws autoscaling delete-auto-scaling-group \
  --auto-scaling-group-name ha-web-asg --force-delete
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN
aws elbv2 delete-target-group --target-group-arn $TG_ARN
```

### 练习 2：进阶场景 — 配置 Route 53 故障转移

**目标**：配置 Route 53 故障转移路由和健康检查

```bash
# 步骤 1：创建健康检查
HEALTH_CHECK_ID=$(aws route53 create-health-check \
  --caller-reference "lab-health-$(date +%s)" \
  --health-check-config '{
    "FullyQualifiedDomainName": "app.example.com",
    "Port": 443,
    "Type": "HTTPS",
    "ResourcePath": "/health",
    "FailureThreshold": 3,
    "RequestInterval": 30
  }' \
  --query 'HealthCheck.Id' --output text)

echo "Health Check ID: $HEALTH_CHECK_ID"

# 步骤 2：创建主记录（PRIMARY）
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "primary-us-east-1",
          "Failover": "PRIMARY",
          "HealthCheckId": "'$HEALTH_CHECK_ID'",
          "TTL": 60,
          "ResourceRecords": [{"Value": "1.2.3.4"}]
        }
      }
    ]
  }'

# 步骤 3：创建辅助记录（SECONDARY）
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890 \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "app.example.com",
          "Type": "A",
          "SetIdentifier": "secondary-us-west-2",
          "Failover": "SECONDARY",
          "TTL": 60,
          "ResourceRecords": [{"Value": "5.6.7.8"}]
        }
      }
    ]
  }'

# 步骤 4：验证健康检查状态
aws route53 get-health-check-status \
  --health-check-id $HEALTH_CHECK_ID

# 步骤 5：测试故障转移
# 模拟主区域故障（停止主区域服务），观察 DNS 是否自动切换

# 清理
aws route53 delete-health-check --health-check-id $HEALTH_CHECK_ID
```

### 练习 3：故障排查挑战 — ASG 扩缩问题

**场景**：ASG 没有按预期进行扩缩容，诊断并修复

```bash
# 步骤 1：检查 ASG 状态
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names my-asg \
  --query 'AutoScalingGroups[0].{
    MinSize: MinSize,
    MaxSize: MaxSize,
    DesiredCapacity: DesiredCapacity,
    Instances: Instances[*].{Id:InstanceId,Health:HealthStatus,AZ:AvailabilityZone}
  }'

# 步骤 2：检查扩缩活动历史
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name my-asg

# 步骤 3：检查 CloudWatch 指标
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=my-asg \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average

# 步骤 4：检查健康检查配置
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names my-asg \
  --query 'AutoScalingGroups[0].{
    HealthCheckType: HealthCheckType,
    HealthCheckGracePeriod: HealthCheckGracePeriod,
    TargetGroupARNs: TargetGroupARNs
  }'

# 步骤 5：检查实例健康状态
aws ec2 describe-instance-status \
  --instance-id i-0123456789abcdef0 \
  --query 'InstanceStatuses[0].{
    SystemStatus: SystemStatus.Status,
    InstanceStatus: InstanceStatus.Status
  }'

# 常见问题：
# 1. 健康检查宽限期太短 → 增加 HealthCheckGracePeriod
# 2. 健康检查路径错误 → 修正 Target Group 健康检查路径
# 3. IAM 权限不足 → 检查 ASG 的 Service Linked Role
# 4. 实例启动失败 → 检查 Launch Template 配置
# 5. 子网可用区不正确 → 更新 VPC Zone Identifier

# 挑战：编写脚本自动诊断 ASG 问题
# 提示：检查实例状态、扩缩活动、CloudWatch 指数
```

---

## 🎯 面试题精选

### Q1: 什么是 AWS Well-Architected Framework 的五大支柱？

**参考答案**：
AWS Well-Architected Framework 的五大支柱是：
1. **卓越运营（Operational Excellence）**：运行和监控系统以交付业务价值，并持续改进流程和程序。关键实践包括 IaC、CI/CD、自动化运维。
2. **安全性（Security）**：保护信息、系统和资产，同时通过风险评估和缓解策略交付业务价值。关键实践包括身份管理、数据加密、网络安全。
3. **可靠性（Reliability）**：确保工作负载在预期时间内正确、一致地执行其预期功能。关键实践包括自动恢复、横向扩展、容量管理。
4. **性能效率（Performance Efficiency）**：高效使用计算资源以满足系统要求，并在需求变化时维持该效率。关键实践包括使用托管服务、无服务器架构、全球部署。
5. **成本优化（Cost Optimization）**：避免不必要的成本，同时理解支出的去向和原因。关键实践包括消费模型、资源优化、自动化管理。

### Q2: Multi-AZ 和 Multi-Region 有什么区别？

**参考答案**：
- **Multi-AZ**：在同一区域内的多个可用区部署资源，用于实现高可用性。AZ 之间通过低延迟链路连接（< 2ms），适用于单区域内的故障容错。
- **Multi-Region**：在不同地理区域部署资源，用于实现灾难恢复和低延迟。区域之间通过互联网连接，延迟较高（100ms+），适用于区域级灾难恢复。

选择建议：
- 高可用需求 → Multi-AZ（RDS Multi-AZ、ALB 跨 AZ）
- 灾难恢复需求 → Multi-Region（Route 53 故障转移）
- 全球低延迟 → Multi-Region + CloudFront CDN

### Q3: Auto Scaling Group 的扩缩策略有哪些？

**参考答案**：
1. **目标追踪扩缩（Target Tracking）**：基于目标指标值自动扩缩，如 CPU 保持在 70%。最常用，配置简单。
2. **步进扩缩（Step Scaling）**：基于指标阈值分阶段扩缩，如 CPU > 60% 加 2 台，> 80% 加 4 台。
3. **简单扩缩（Simple Scaling）**：基于单一阈值扩缩，如 CPU > 70% 加 2 台。扩缩后有冷却期。
4. **计划扩缩（Scheduled Scaling）**：基于时间计划扩缩，如每天早 8 点扩到 6 台。
5. **预测扩缩（Predictive Scaling）**：基于历史数据预测未来需求，提前扩缩。

### Q4: 如何设计一个 RTO < 5 分钟、RPO < 1 分钟的架构？

**参考答案**：
对于 RTO < 5 分钟、RPO < 1 分钟的需求：
1. **数据库层**：使用 RDS Multi-AZ（自动故障转移 < 60 秒），或 Aurora Global Database（跨区域复制 < 1 秒）。
2. **应用层**：使用 ALB + ASG 跨 AZ 部署，最少 2 个实例，健康检查间隔 10 秒。
3. **缓存层**：ElastiCache Redis 集群，Multi-AZ 自动故障转移。
4. **DNS 层**：Route 53 健康检查，TTL 60 秒，故障转移路由。
5. **存储层**：S3 跨区域复制，或 EBS 快照定期备份。

这种架构的成本较高，需要根据业务重要性权衡。

### Q5: ALB 和 NLB 的选择标准是什么？

**参考答案**：
选择 ALB 的场景：
- HTTP/HTTPS 流量（Layer 7）
- 需要基于路径/主机的路由
- 需要 WebSocket 支持
- 需要 WAF 集成
- 需要 Lambda 作为目标

选择 NLB 的场景：
- TCP/UDP 流量（Layer 4）
- 需要超低延迟（百万级请求/秒）
- 需要静态 IP 地址
- 需要保留源 IP 地址
- 游戏服务器、IoT 应用

混合使用：NLB 作为入口，后面接 ALB 做内容路由。

### Q6: 什么是引导光（Pilot Light）灾难恢复模式？

**参考答案**：
引导光模式是一种灾难恢复策略，核心组件（如数据库）在灾难恢复区域持续运行，但应用层处于关闭状态。

工作流程：
1. 主区域运行完整应用栈
2. 数据库实时同步到灾难恢复区域
3. 应用层 AMI 和配置定期更新到灾难恢复区域
4. 故障发生时，启动灾难恢复区域的应用层
5. 修改 DNS 指向灾难恢复区域

优点：成本较低（只运行数据库），恢复时间较短（10-15 分钟）。
缺点：需要手动或脚本化启动应用层，恢复过程中有短暂服务中断。

### Q7: 如何实现零 RPO 的灾难恢复？

**参考答案**：
实现零 RPO（零数据丢失）需要：
1. **同步复制**：数据同时写入主区域和灾难恢复区域，确保两边数据一致。
2. **多活架构**：两个区域都运行完整应用栈，流量通过 Route 53 分发。
3. **分布式数据库**：使用支持多主复制的数据库（如 DynamoDB Global Tables、Aurora Global Database）。
4. **消息队列同步**：SQS/SNS 跨区域复制，确保消息不丢失。

挑战：
- 同步复制会增加写入延迟
- 多活架构需要处理数据冲突
- 成本较高（双倍资源）
- 需要复杂的故障检测和切换机制

### Q8: Route 53 健康检查的类型有哪些？

**参考答案**：
Route 53 支持以下健康检查类型：
1. **HTTP/HTTPS**：检查 HTTP 状态码（200-499）和响应体内容。
2. **TCP**：检查 TCP 连接是否成功建立。
3. **字符串匹配**：检查响应体是否包含指定字符串。
4. **CloudWatch 告警**：基于 CloudWatch 指标创建复合健康检查。
5. **计算（Calculated）**：组合多个健康检查的逻辑运算。

配置参数：
- 检查间隔：10 秒或 30 秒
- 失败阈值：1-10 次
- 健康检查器位置：全球多个 AWS 边缘站点

### Q9: Auto Scaling Group 的终止策略有哪些？

**参考答案**：
ASG 的终止策略（Termination Policies）：
1. **OldestInstance**：终止最旧的实例（默认）
2. **NewestInstance**：终止最新的实例
3. **OldestLaunchTemplate**：终止使用旧 Launch Template 的实例
4. **ClosestToNextInstanceHour**：终止最接近下一个计费小时的实例
5. **Default**：默认策略（平衡分布）
6. **AllocationStrategy**：基于分配策略终止

最佳实践：
- 生产环境使用 OldestInstance（确保使用最新配置）
- 使用保护机制（Instance Protection）防止关键实例被终止
- 配置终止钩子（Lifecycle Hook）执行清理操作

### Q10: 如何设计一个电商大促活动的高可用架构？

**参考答案**：
电商大促活动架构设计：
1. **前端层**：
   - CloudFront CDN 加速静态资源
   - WAF 防护恶意请求
   - Shield Advanced 防护 DDoS

2. **应用层**：
   - ALB 跨 AZ 负载均衡
   - ASG 提前扩容（预测扩缩）
   - 预热缓存（ElastiCache）

3. **数据层**：
   - RDS Multi-AZ + 读写分离
   - DynamoDB 按需容量
   - S3 存储静态资源

4. **监控层**：
   - CloudWatch 实时监控
   - SNS 告警通知
   - X-Ray 分布式追踪

5. **容灾层**：
   - Route 53 故障转移
   - 多区域部署关键服务
   - 限流降级策略

关键指标：
- ASG 扩缩速度：< 3 分钟
- 数据库连接池：预配置足够连接
- 缓存命中率：> 90%
- 错误率：< 0.1%

---

## 📚 延伸阅读

- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [Auto Scaling Group 用户指南](https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html)
- [Elastic Load Balancing 用户指南](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/what-is-load-balancing.html)
- [Route 53 开发者指南](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)
- [灾难恢复到 AWS 白皮书](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html)
- [AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html)

---

## ✅ 今日自检清单

- [ ] 能够解释 AWS Well-Architected Framework 的五大支柱
- [ ] 理解 Multi-AZ 架构设计原则和优势
- [ ] 能够创建 Launch Template 和 Auto Scaling Group
- [ ] 掌握不同扩缩策略的适用场景
- [ ] 能够配置 ALB/NLB 跨 AZ 负载均衡
- [ ] 理解 Route 53 故障转移路由和健康检查
- [ ] 能够描述四种灾难恢复模式及其差异
- [ ] 理解 RTO/RPO 概念及其在架构设计中的应用
- [ ] 能够设计一个高可用的电商系统架构
