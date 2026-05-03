# Day 119: AWS 知识掌握（综合复习）

> 📅 日期：2026-05-03
> 📖 学习主题：AWS 综合复习 — 架构设计、成本优化、故障排查、最佳实践总结
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 105-118（AWS 全部课程）

---

## 🎯 学习目标

- 掌握 AWS Well-Architected Framework 六大支柱的核心原则
- 能独立设计高可用、可扩展、安全的多 AZ 架构
- 掌握 AWS 成本优化的系统性方法
- 能进行 AWS 环境的故障排查与根因分析
- 整合 Day 105-118 所有知识点形成完整的 AWS 知识体系

---

## 📖 核心知识点

### 1. AWS Well-Architected Framework 六大支柱

```
┌─────────────────────────────────────────────────────────────┐
│                AWS Well-Architected Framework                │
├──────────┬──────────┬──────────┬──────────┬────────┬────────┤
│ 卓越运营 │ 安全性   │ 可靠性   │ 性能效率 │ 成本优化│ 可持续性│
│Operational│Security │Reliability│Performance│Cost    │Sustain-│
│Excellence│         │          │Efficiency │Optimi- │ability │
│          │         │          │          │zation  │        │
├──────────┼──────────┼──────────┼──────────┼────────┼────────┤
│ IaC      │ IAM      │ 多 AZ    │ 选型     │ 预留实例│ 绿色计算│
│ 自动化   │ 加密     │ 自动恢复 │ 缓存     │ Savings│ 资源优化│
│ 监控     │ 网络安全 │ 故障隔离 │ CDN      │ Plans  │        │
│ 变更管理 │ 日志审计 │ 备份     │ 无服务器 │ Spot   │        │
└──────────┴──────────┴──────────┴──────────┴────────┴────────┘
```

#### 1.1 卓越运营（Operational Excellence）

**核心原则：**
- **IaC（Infrastructure as Code）**：所有基础设施通过代码管理（CloudFormation / Terraform）
- **自动化运维**：CI/CD 流水线、自动扩缩容、自动修复
- **可观测性**：CloudWatch 指标 + 日志 + X-Ray 追踪
- **变更管理**：蓝绿部署、金丝雀发布、滚动更新

**SRE 实践要点：**

```yaml
# 运维自动化检查清单
Operational_Checklist:
  Infrastructure:
    - 所有资源通过 IaC 创建
    - 版本控制所有配置
    - 自动化部署流水线
  Monitoring:
    - 关键指标告警（CPU > 80%, 内存 > 85%）
    - 日志集中收集与分析
    - 分布式追踪覆盖核心链路
  Incident_Response:
    - Runbook 文档化
    - 自动化故障恢复
    - 事后复盘（Post-mortem）流程
```

#### 1.2 安全性（Security）

**安全架构分层：**

```
┌─────────────────────────────────────┐
│           应用安全层                 │
│  WAF / Shield / Cognito / Secrets   │
├─────────────────────────────────────┤
│           数据安全层                 │
│  KMS 加密 / S3 加密 / RDS 加密      │
├─────────────────────────────────────┤
│           计算安全层                 │
│  Security Groups / IAM Roles        │
├─────────────────────────────────────┤
│           网络安全层                 │
│  VPC / NACL / Private Subnet        │
├─────────────────────────────────────┤
│           账户安全层                 │
│  Organizations / SCP / MFA / CloudTrail│
└─────────────────────────────────────┘
```

**IAM 最佳实践：**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceMFALogin",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

**安全检查要点：**
- 根账户启用 MFA 并禁用 Access Key
- 所有 IAM 用户强制 MFA
- 最小权限原则（Least Privilege）
- Security Group 不开放 0.0.0.0/0 的 SSH/RDP
- S3 Bucket 默认加密、禁止公开访问
- 所有 API 调用通过 CloudTrail 审计

#### 1.3 可靠性（Reliability）

**高可用架构模式：**

```
                    ┌─────────────┐
                    │  Route 53   │
                    │ (DNS 健康检查)│
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ CloudFront  │
                    │   (CDN)     │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │     ALB     │
                    │ (多 AZ 部署) │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐┌─────┴─────┐┌─────┴─────┐
        │  AZ-1a    ││  AZ-1b    ││  AZ-1c    │
        │ ┌───────┐ ││ ┌───────┐ ││ ┌───────┐ │
        │ │  EC2  │ ││ │  EC2  │ ││ │  EC2  │ │
        │ └───────┘ ││ └───────┘ ││ └───────┘ │
        │ ┌───────┐ ││ ┌───────┐ ││ ┌───────┐ │
        │ │ RDS   │ ││ │ RDS   │ ││ │ RDS   │ │
        │ │(主)   │ ││ │(备)   │ ││ │(只读) │ │
        │ └───────┘ ││ └───────┘ ││ └───────┘ │
        └───────────┘└───────────┘└───────────┘
```

**可靠性设计原则：**

| 策略 | 实现方式 | RTO/RPO |
|------|---------|---------|
| 多 AZ 部署 | ALB + Auto Scaling 跨 AZ | RTO: 秒级 |
| 数据库高可用 | RDS Multi-AZ | RTO: 60-120s |
| 灾难恢复 | 跨区域复制（S3/RDS） | RTO: 分钟-小时 |
| 自动恢复 | EC2 Auto Recovery | RTO: 3-5 分钟 |
| 备份策略 | AWS Backup 定期备份 | RPO: 取决于策略 |

#### 1.4 性能效率（Performance Efficiency）

**性能优化矩阵：**

```
┌─────────────┬──────────────────────────────────────────┐
│   层级      │          优化策略                         │
├─────────────┼──────────────────────────────────────────┤
│ 计算        │ 实例选型（计算/内存/存储优化型）           │
│             │ Auto Scaling 动态扩缩                    │
│             │ Lambda 事件驱动（免运维）                 │
├─────────────┼──────────────────────────────────────────┤
│ 存储        │ EBS gp3/io2（IOPS 密集型）               │
│             │ S3 智能分层（Lifecycle Policy）            │
│             │ EFS（共享文件系统）                       │
├─────────────┼──────────────────────────────────────────┤
│ 数据库      │ ElastiCache（Redis/Memcached 缓存）       │
│             │ DynamoDB（Serverless NoSQL）              │
│             │ Aurora（MySQL/PG 兼容，自动扩缩）         │
├─────────────┼──────────────────────────────────────────┤
│ 网络        │ CloudFront（全球 CDN）                    │
│             │ Global Accelerator（TCP/UDP 加速）        │
│             │ VPC Endpoint（减少 NAT 开销）             │
├─────────────┼──────────────────────────────────────────┤
│ 内容分发    │ S3 + CloudFront 静态资源                  │
│             │ API Gateway + Lambda API                  │
└─────────────┴──────────────────────────────────────────┘
```

#### 1.5 成本优化（Cost Optimization）

**成本优化策略：**

```
┌──────────────────────────────────────────────────────────────┐
│                    成本优化策略全景                            │
├────────────────┬─────────────────────────────────────────────┤
│ Right Sizing   │ CloudWatch 指标分析 → 调整实例规格           │
│                │ Compute Optimizer 推荐                       │
├────────────────┼─────────────────────────────────────────────┤
│ 购买策略       │ Reserved Instances (1yr/3yr) → 稳定负载      │
│                │ Savings Plans → 灵活承诺                     │
│                │ Spot Instances → 容错/批处理                 │
├────────────────┼─────────────────────────────────────────────┤
│ 架构优化       │ Serverless（Lambda/DynamoDB）→ 按需付费      │
│                │ 容器化（ECS/EKS）→ 提高资源利用率            │
│                │ S3 智能分层 → 降低存储成本                   │
├────────────────┼─────────────────────────────────────────────┤
│ 资源管理       │ 标签策略 → 成本分配                          │
│                │ 自动关闭非生产环境                           │
│                │ 删除未使用的资源（EBS/Snapshot/EIP）         │
├────────────────┼─────────────────────────────────────────────┤
│ 监控与治理     │ AWS Cost Explorer → 成本分析                 │
│                │ Budgets → 预算告警                           │
│                │ Trusted Advisor → 优化建议                   │
└────────────────┴─────────────────────────────────────────────┘
```

**成本分析脚本：**

```bash
#!/bin/bash
# cost-analysis.sh - AWS 成本分析脚本

echo "=== 本月成本概览 ==="
aws ce get-cost-and-usage \
    --time-period Start=$(date -d "-1 month" +%Y-%m-01),End=$(date +%Y-%m-01) \
    --granularity MONTHLY \
    --metrics "UnblendedCost" \
    --group-by Type=DIMENSION,Key=SERVICE \
    --query 'ResultsByTime[*].Groups[*].[Keys[0],Metrics.UnblendedAmount]' \
    --output table

echo "=== 未使用的 EBS 卷 ==="
aws ec2 describe-volumes \
    --filters Name=status,Values=available \
    --query 'Volumes[*].[VolumeId,Size,CreateTime,VolumeType]' \
    --output table

echo "=== 未关联的 Elastic IP ==="
aws ec2 describe-addresses \
    --query 'Addresses[?AssociationId==null].[PublicIp,AllocationId]' \
    --output table

echo "=== 过期的 Snapshots（超过 30 天）==="
aws ec2 describe-snapshots \
    --owner-ids self \
    --query "snapshots[?StartTime<='$(date -d '-30 days' -u +%Y-%m-%dT%H:%M:%SZ)'].[SnapshotId,StartTime,VolumeSize]" \
    --output table
```

#### 1.6 可持续性（Sustainability）

- 选择高效实例类型（Graviton ARM 处理器）
- 使用 Serverless 减少闲置资源
- S3 智能分层减少存储冗余
- 选择绿色能源区域

### 2. 故障排查方法论

#### 2.1 故障排查流程

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1.发现    │───→│ 2.定位   │───→│ 3.修复   │───→│ 4.复盘   │
│ 监控告警  │    │ 日志分析  │    │ 快速恢复  │    │ 根因分析  │
│ 用户反馈  │    │ 指标异常  │    │ 变更回滚  │    │ 改进措施  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

#### 2.2 常见故障排查场景

**场景 1：EC2 实例无法访问**

```bash
# 排查步骤
# 1. 检查实例状态
aws ec2 describe-instance-status --instance-ids i-xxx

# 2. 检查 Security Group
aws ec2 describe-security-groups --group-ids sg-xxx

# 3. 检查 NACL
aws ec2 describe-network-acls --filters "Name=association.subnet-id,Values=subnet-xxx"

# 4. 检查路由表
aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=subnet-xxx"

# 5. 检查系统日志
aws ec2 get-console-output --instance-id i-xxx --output text

# 6. 检查 CPU Credits（T 系列实例）
aws cloudwatch get-metric-statistics \
    --namespace AWS/EC2 \
    --metric-name CPUCreditBalance \
    --dimensions Name=InstanceId,Value=i-xxx \
    --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average
```

**场景 2：RDS 连接问题**

```bash
# 1. 检查 RDS 状态
aws rds describe-db-instances --db-instance-identifier mydb \
    --query 'DBInstances[*].[DBInstanceStatus,Endpoint.Address,Endpoint.Port]'

# 2. 检查安全组规则
aws ec2 describe-security-groups --group-ids sg-xxx \
    --query 'SecurityGroups[*].IpPermissions'

# 3. 检查参数组
aws rds describe-db-parameters --db-parameter-group-name my-param-group \
    --query 'Parameters[?ParameterName==`max_connections`]'
```

**场景 3：S3 访问被拒绝**

```bash
# 1. 检查 Bucket Policy
aws s3api get-bucket-policy --bucket my-bucket

# 2. 检查 Block Public Access 设置
aws s3api get-public-access-block --bucket my-bucket

# 3. 检查 Bucket ACL
aws s3api get-bucket-acl --bucket my-bucket

# 4. 检查 IAM 策略
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::123456789012:role/MyRole \
    --action-names s3:GetObject \
    --resource-arns arn:aws:s3:::my-bucket/*
```

**场景 4：ALB 502/503/504 错误**

```bash
# 1. 检查 Target Group 健康状态
aws elbv2 describe-target-health --target-group-arn arn:aws:...

# 2. 检查 ALB 访问日志
aws s3 ls s3://alb-logs-bucket/AWSLogs/123456789012/elasticloadbalancing/

# 3. 检查后端实例响应时间
aws cloudwatch get-metric-statistics \
    --namespace AWS/ApplicationELB \
    --metric-name TargetResponseTime \
    --dimensions Name=LoadBalancer,Value=app/my-alb/xxx \
    --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 60 \
    --statistics Average Maximum

# 4. 检查连接耗尽
aws cloudwatch get-metric-statistics \
    --namespace AWS/ApplicationELB \
    --metric-name ActiveConnectionCount \
    --dimensions Name=LoadBalancer,Value=app/my-alb/xxx \
    --start-time $(date -u -d '-1 hour' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 60 \
    --statistics Sum
```

### 3. 架构设计综合案例

#### 3.1 三层 Web 应用架构

```
用户请求流向：

[用户] → [Route53] → [CloudFront] → [WAF] → [ALB]
                                                    │
                                    ┌───────────────┼───────────────┐
                                    │               │               │
                              [EC2/Web层]     [EC2/Web层]     [EC2/Web层]
                              (AZ-1a)        (AZ-1b)        (AZ-1c)
                                    │               │               │
                                    └───────────────┼───────────────┘
                                                    │
                                              [ElastiCache]
                                              (Redis 集群)
                                                    │
                                    ┌───────────────┼───────────────┐
                                    │               │               │
                              [RDS 主]        [RDS 只读]      [RDS 只读]
                              (AZ-1a)        (AZ-1b)        (AZ-1c)
```

**核心组件选型：**

| 组件 | 选型 | 配置要点 |
|------|------|---------|
| DNS | Route 53 | 健康检查 + 故障转移路由策略 |
| CDN | CloudFront | 缓存静态资源，压缩开启 |
| WAF | AWS WAF | SQL注入/XSS防护，速率限制 |
| 负载均衡 | ALB | 跨 AZ，健康检查路径 /health |
| Web 服务器 | EC2 (Auto Scaling) | t3.medium，最小2/最大10 |
| 缓存 | ElastiCache Redis | r6g.large，Multi-AZ |
| 数据库 | RDS Aurora MySQL | db.r6g.large，Multi-AZ + 只读副本 |
| 存储 | S3 | 静态资源，版本控制，跨区域复制 |

#### 3.2 Serverless 微服务架构

```
[客户端] → [API Gateway] → [Lambda 函数组]
                                │
                    ┌───────────┼───────────┐
                    │           │           │
              [用户服务]  [订单服务]  [支付服务]
                    │           │           │
              [DynamoDB]  [DynamoDB]  [SQS Queue]
                                         │
                                    [支付处理 Lambda]
                                         │
                                    [DynamoDB]
```

### 4. 高可用架构设计模式

#### 4.1 主动-主动多区域架构

```
┌───────────────────────────────────────────────────────────────┐
│                   主动-主动多区域架构                           │
│                                                               │
│  ┌────── Region A (us-east-1) ──────┐                        │
│  │                                  │                        │
│  │  Route53 (加权路由 50%)           │                        │
│  │       │                          │                        │
│  │  CloudFront + ALB                │                        │
│  │       │                          │                        │
│  │  ┌────┴────┐ ┌────────┐         │                        │
│  │  │ EC2/ECS │ │ElastiCa │         │                        │
│  │  │ Cluster │ │ che     │         │                        │
│  │  └────┬────┘ └────────┘         │                        │
│  │       │                          │                        │
│  │  Aurora Global (主写)             │                        │
│  └──────────────────────────────────┘                        │
│           │ Aurora Global Database 跨区域复制                 │
│  ┌────────▼─────────────────────────┐                        │
│  │  Region B (us-west-2)            │                        │
│  │                                  │                        │
│  │  Route53 (加权路由 50%)           │                        │
│  │       │                          │                        │
│  │  CloudFront + ALB                │                        │
│  │       │                          │                        │
│  │  ┌────┴────┐ ┌────────┐         │                        │
│  │  │ EC2/ECS │ │ElastiCa │         │                        │
│  │  │ Cluster │ │ che     │         │                        │
│  │  └────┬────┘ └────────┘         │                        │
│  │       │                          │                        │
│  │  Aurora Global (只读/故障转移)    │                        │
│  └──────────────────────────────────┘                        │
└───────────────────────────────────────────────────────────────┘
```

**适用场景：** RPO = 0, RTO < 1 分钟，全球用户分布

#### 4.2 灾难恢复模式对比

| 模式 | RPO | RTO | 成本 | 适用场景 |
|------|-----|-----|------|---------|
| 备份恢复 | 小时级 | 小时级 | 低 | 非关键应用 |
| Pilot Light | 分钟级 | 15-60 分钟 | 中 | 一般业务系统 |
| Warm Standby | 秒级 | 分钟级 | 中高 | 重要业务系统 |
| 多区域主动 | 0 | 秒级 | 高 | 核心业务系统 |

#### 4.3 数据库高可用设计

```
┌─────────────────────────────────────────────────────────┐
│               Aurora 高可用架构                           │
│                                                         │
│  ┌─── AZ-1a ───┐  ┌─── AZ-1b ───┐  ┌─── AZ-1c ───┐   │
│  │              │  │              │  │              │   │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │   │
│  │  │Writer  │  │  │  │Reader  │  │  │  │Reader  │  │   │
│  │  │实例    │  │  │  │实例    │  │  │  │实例    │  │   │
│  │  └────────┘  │  │  └────────┘  │  │  └────────┘  │   │
│  │              │  │              │  │              │   │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │   │
│  │  │存储节点│  │  │  │存储节点│  │  │  │存储节点│  │   │
│  │  │(6副本) │  │  │  │(6副本) │  │  │  │(6副本) │  │   │
│  │  └────────┘  │  │  └────────┘  │  │  └────────┘  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                         │
│  特点：                                                  │
│  - 存储跨 3 AZ 自动复制（6 副本）                        │
│  - 自动故障转移 < 30 秒                                  │
│  - 最多 15 个只读副本                                    │
│  - 存储自动扩展到 128 TB                                 │
└─────────────────────────────────────────────────────────┘
```

### 5. 成本优化实战详解

#### 5.1 购买策略决策矩阵

```
┌─────────────────────────────────────────────────────────┐
│              AWS 购买策略决策矩阵                         │
│                                                         │
│  工作负载特性：                                          │
│  ┌─────────────┬──────────────┬──────────────┐          │
│  │ 稳定性/时长 │ 推荐策略      │ 节省比例     │          │
│  ├─────────────┼──────────────┼──────────────┤          │
│  │ 7x24 稳定  │ Reserved 3yr │ 最高 72%     │          │
│  │ 全年稳定    │ Reserved 1yr │ 最高 40%     │          │
│  │ 承诺用量    │ Savings Plan │ 最高 66%     │          │
│  │ 容错/批处理 │ Spot Instance│ 最高 90%     │          │
│  │ 临时/测试   │ On-Demand    │ 0%（灵活）   │          │
│  └─────────────┴──────────────┴──────────────┘          │
│                                                         │
│  Savings Plans 类型：                                    │
│  ┌────────────────┬─────────────────────────────────┐   │
│  │ Compute SP     │ 跨 EC2/Fargate/Lambda 灵活使用  │   │
│  │ EC2 Instance SP│ 限定实例系列，折扣更大           │   │
│  │ SageMaker SP   │ 专用于 SageMaker 实例           │   │
│  └────────────────┴─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

#### 5.2 存储成本优化

```bash
#!/bin/bash
# storage-optimization.sh - 存储成本分析与优化脚本

echo "=== S3 存储分析 ==="
aws s3api list-buckets --query 'Buckets[*].Name' --output text | tr '\t' '\n' | while read bucket; do
    size=$(aws s3 ls "s3://${bucket}" --recursive --summarize 2>/dev/null | tail -1 | awk '{print $3}')
    count=$(aws s3 ls "s3://${bucket}" --recursive --summarize 2>/dev/null | tail -2 | head -1 | awk '{print $2}')
    echo "Bucket: ${bucket}, Objects: ${count}, Size: ${size} bytes"
done

echo ""
echo "=== EBS 卷分析 ==="
echo "未挂载的 EBS 卷："
aws ec2 describe-volumes \
    --filters Name=status,Values=available \
    --query 'Volumes[*].[VolumeId,Size,VolumeType,CreateTime]' \
    --output table

echo ""
echo "gp2 卷（可升级到 gp3）："
aws ec2 describe-volumes \
    --filters Name=volume-type,Values=gp2 \
    --query 'Volumes[*].[VolumeId,Size,State,Attachments[0].InstanceId]' \
    --output table

echo ""
echo "=== Snapshot 清理建议 ==="
echo "超过 90 天的快照："
aws ec2 describe-snapshots --owner-ids self \
    --query "snapshots[?StartTime<='$(date -d '-90 days' -u +%Y-%m-%dT%H:%M:%SZ)'].[SnapshotId,StartTime,VolumeSize,Description]" \
    --output table
```

#### 5.3 S3 生命周期策略

```json
{
  "Rules": [
    {
      "ID": "OptimizeStorage",
      "Status": "Enabled",
      "Filter": { "Prefix": "" },
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        },
        {
          "Days": 365,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "NoncurrentVersionTransitions": [
        {
          "NoncurrentDays": 30,
          "StorageClass": "STANDARD_IA"
        }
      ],
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
```

### 6. AWS 服务速查表

#### 4.1 计算服务

| 服务 | 场景 | 计费模式 |
|------|------|---------|
| EC2 | 通用计算，完全控制 | 按需/预留/Spot |
| Lambda | 事件驱动，短时任务 | 按调用次数和时长 |
| ECS | 容器编排（AWS 深度集成） | 按 EC2 或 Fargate |
| EKS | Kubernetes 托管 | 按 EC2 + 控制平面费用 |
| Fargate | Serverless 容器 | 按 vCPU 和内存 |

#### 4.2 存储服务

| 服务 | 场景 | 特点 |
|------|------|------|
| S3 | 对象存储，静态资源 | 11个9持久性，智能分层 |
| EBS | 块存储，数据库 | gp3/io2，快照备份 |
| EFS | NFS 共享文件系统 | 弹性扩展，多 AZ |
| FSx | 高性能文件系统 | Windows/Lustre |

#### 4.3 数据库服务

| 服务 | 场景 | 特点 |
|------|------|------|
| RDS | 关系型数据库 | Multi-AZ，自动备份 |
| Aurora | MySQL/PG 兼容 | 5x 性能，自动扩缩 |
| DynamoDB | NoSQL | 毫秒延迟，Serverless |
| ElastiCache | 内存缓存 | Redis/Memcached |
| Redshift | 数据仓库 | 列存储，大规模分析 |

#### 4.4 网络服务

| 服务 | 场景 | 关键配置 |
|------|------|---------|
| VPC | 网络隔离 | CIDR规划，子网划分 |
| ALB/NLB | 负载均衡 | 健康检查，路由规则 |
| CloudFront | CDN | 缓存策略，源站配置 |
| Route 53 | DNS | 路由策略，健康检查 |
| Transit Gateway | 多 VPC 互联 | 路由表，附件管理 |

---

## 💻 实战练习

### 练习 1：架构设计

**场景：** 设计一个高可用电商网站架构

**要求：**
- 支持日均 PV 100 万
- 数据库读写分离
- 静态资源 CDN 加速
- 自动扩缩容
- 成本可控

**设计输出：**
```
1. 绘制架构图（ASCII art）
2. 列出所有 AWS 服务及规格
3. 估算月度成本
4. 制定容灾方案
```

### 练习 2：成本优化分析

**场景：** 分析以下环境并提出优化建议

```bash
# 当前环境清单
- 20 台 m5.xlarge EC2（CPU 平均使用率 15%）
- 5 个 RDS db.r5.2xlarge（连接数平均 50）
- 2TB S3 Standard 存储（大部分数据超过 90 天未访问）
- 10 个 EBS gp2 卷（500GB each，3 个未挂载）
- NAT Gateway 流量费 $500/月
```

**任务：**
1. 计算当前月度成本
2. 提出至少 5 项优化建议
3. 预估优化后成本
4. 制定实施计划

### 练习 3：故障排查挑战

**场景：** 生产环境突然出现以下告警

```
[CRITICAL] ALB 5xx Error Rate > 5%
[CRITICAL] EC2 CPU Utilization > 90%
[WARNING]  RDS Connection Count > 80% of max
[WARNING]  ElastiCache Memory Usage > 85%
```

**任务：**
1. 按优先级排序处理这些告警
2. 制定排查步骤
3. 列出可能的根因
4. 制定短期修复和长期改进方案

---

## 🎯 面试题精选

### 1. 解释 AWS Well-Architected Framework 的六大支柱

**参考答案：**
AWS Well-Architected Framework 包含六大支柱：
1. **卓越运营**：通过 IaC、自动化、监控实现高效运维
2. **安全性**：身份认证、检测控制、基础设施保护、数据保护、事件响应
3. **可靠性**：从故障中恢复、满足动态计算需求、管理网络和配额限制
4. **性能效率**：高效使用计算资源满足系统需求，并随需求变化维护效率
5. **成本优化**：避免不必要的成本，理解支出驱动因素
6. **可持续性**：减少碳足迹，高效利用资源

### 2. 如何设计一个 99.99% 可用的 Web 应用？

**参考答案：**
- **多 AZ 部署**：ALB 跨 AZ，EC2 Auto Scaling 分布在 3 个 AZ
- **数据库高可用**：RDS Multi-AZ + 只读副本
- **缓存层**：ElastiCache Redis 集群模式（Multi-AZ）
- **CDN**：CloudFront 缓存静态资源，减少源站压力
- **DNS 故障转移**：Route 53 健康检查 + 故障转移策略
- **自动恢复**：EC2 Auto Recovery，RDS 自动故障转移
- **监控告警**：CloudWatch + SNS 快速发现故障
- **99.99% SLA = 年停机 52.6 分钟**

### 3. EC2、ECS、EKS、Lambda 如何选型？

**参考答案：**

| 需求 | 选型 | 理由 |
|------|------|------|
| 完全控制 OS | EC2 | 需要自定义内核/驱动 |
| 容器化应用 | ECS | AWS 深度集成，简单易用 |
| K8s 生态 | EKS | 多云兼容，社区丰富 |
| 事件驱动 | Lambda | 免运维，按需付费 |
| 混合场景 | EKS + Fargate | K8s + Serverless 容器 |

### 4. 如何排查 EC2 实例 SSH 无法连接的问题？

**参考答案：**
1. **检查实例状态**：`aws ec2 describe-instance-status` 确认实例运行中
2. **检查 Security Group**：确认入站规则允许 22 端口，源 IP 正确
3. **检查 NACL**：确认子网 ACL 允许 22 端口双向流量
4. **检查路由表**：确认子网有正确的路由（IGW 或 NAT）
5. **检查密钥对**：确认使用正确的 .pem 文件，权限 400
6. **检查系统日志**：`aws ec2 get-console-output` 查看启动错误
7. **使用 Session Manager**：替代 SSH，无需开放 22 端口

### 5. 解释 AWS 的 Shared Responsibility Model

**参考答案：**
- **AWS 负责（Security OF the Cloud）**：物理安全、硬件、网络基础设施、虚拟化层
- **客户负责（Security IN the Cloud）**：数据加密、IAM 配置、OS 补丁、网络配置、应用安全
- **不同服务责任不同**：EC2 客户管理更多（OS/应用），Lambda 客户管理更少（仅代码和数据）

### 6. 如何优化 AWS 成本？

**参考答案：**
1. **Right Sizing**：使用 Compute Optimizer 分析，降配闲置实例
2. **购买策略**：稳定负载用 Reserved/Savings Plans，容错任务用 Spot
3. **存储优化**：S3 智能分层，删除未使用的 EBS/Snapshot
4. **架构优化**：Serverless 替代长期运行实例，容器化提高利用率
5. **标签治理**：强制标签策略，按团队/项目分配成本
6. **自动化**：非生产环境定时开关，Auto Scaling 动态调整

### 7. Aurora 与标准 RDS 的区别是什么？

**参考答案：**
- **存储架构**：Aurora 使用分布式存储，自动扩展到 128TB，数据跨 3 AZ 6 副本
- **性能**：Aurora MySQL 是标准 MySQL 的 5 倍，Aurora PG 是标准 PG 的 3 倍
- **可用性**：Aurora 支持最多 15 个只读副本，延迟 < 10ms
- **故障转移**：Aurora 故障转移 < 30 秒（标准 RDS 60-120 秒）
- **成本**：Aurora 实例价格高 20%，但存储价格低，总体 TCO 可能更低
- **Serverless**：Aurora Serverless v2 自动扩缩，适合间歇性负载

### 8. VPC 设计的最佳实践是什么？

**参考答案：**
- **CIDR 规划**：预留足够空间，使用 /16 或更大，避免与其他 VPC/本地网络重叠
- **子网划分**：每个 AZ 至少 3 个子网（公有/私有/数据库），公有子网放 NAT/LB
- **公有子网最小化**：仅放置负载均衡器和 NAT Gateway
- **NAT Gateway**：每个 AZ 一个 NAT Gateway（高可用），或用 NAT Instance 节省成本
- **VPC Endpoint**：S3/DynamoDB 使用 Gateway Endpoint，其他服务使用 Interface Endpoint
- **流量日志**：启用 VPC Flow Logs 分析网络流量

---

## 📚 深入阅读

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Well-Architected Labs](https://wellarchitectedlabs.com/)
- [AWS Cost Optimization](https://aws.amazon.com/aws-cost-management/)
- [AWS Architecture Center](https://aws.amazon.com/architecture/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [AWS re:Invent Sessions](https://reinvent.awsevents.com/)

---

## ✅ 自检清单

- [ ] 能解释 AWS Well-Architected Framework 六大支柱
- [ ] 能设计多 AZ 高可用架构
- [ ] 能制定成本优化策略（Reserved/Spot/Savings Plans）
- [ ] 能排查常见的 AWS 网络/计算/存储故障
- [ ] 理解 Shared Responsibility Model
- [ ] 掌握 AWS 服务选型（EC2 vs ECS vs EKS vs Lambda）
- [ ] 能使用 AWS CLI 进行日常运维操作
- [ ] 掌握 IAM 最佳实践（最小权限、MFA、角色）
- [ ] 理解 VPC 网络设计（子网/路由/NACL/SG）
- [ ] 能分析 CloudWatch 指标和日志进行故障定位
- [ ] 掌握 RDS 高可用和备份恢复策略
- [ ] 理解 S3 存储类别和生命周期策略
