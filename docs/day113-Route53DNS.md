# Day 113: Route 53 DNS

> 📅 日期：2026-05-03
> 📖 学习主题：Route 53 DNS — 托管区域、记录类型、路由策略、健康检查、故障转移、加权路由、延迟路由、DNSSEC
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 105 (AWS 简介), Day 107 (VPC), Day 110 (ELB)

## 🎯 学习目标

- 掌握 Route 53 托管区域（Hosted Zone）的创建与管理
- 理解 DNS 记录类型（A, AAAA, CNAME, MX, TXT, SRV, Alias）的区别与用途
- 熟练配置各种路由策略（Simple, Weighted, Latency, Failover, Geolocation, Geoproximity, Multivalue）
- 能够设计和配置健康检查与故障转移方案
- 理解 DNSSEC 的原理与实现
- 能够设计多区域、高可用的 DNS 架构

---

## 📖 核心知识点

### 1. Route 53 概述

Route 53 是 AWS 的 DNS 服务，名称来源于 DNS 默认端口 53。它提供 DNS 解析、域名注册、健康检查三大核心功能。

```
┌──────────────────────────────────────────────────────────────────┐
│                    Route 53 核心功能                               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    DNS 解析服务                               │ │
│  │  - 托管区域（Hosted Zone）                                    │ │
│  │  - DNS 记录（A, AAAA, CNAME, MX, TXT, Alias）               │ │
│  │  - 路由策略（Simple, Weighted, Latency, Failover...）        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   域名注册        │  │   健康检查        │  │   DNSSEC       │ │
│  │   - 购买域名      │  │   - HTTP/HTTPS   │  │   - 域名签名    │ │
│  │   - 自动续费      │  │   - TCP          │  │   - 防篡改      │ │
│  │   - 隐私保护      │  │   - 关联告警      │  │   - 链式信任    │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### DNS 解析流程

```
┌──────────────────────────────────────────────────────────────┐
│                    DNS 解析流程                                │
│                                                               │
│  1. 用户浏览器请求 www.example.com                            │
│     │                                                        │
│     ▼                                                        │
│  2. 递归解析器（ISP DNS）                                     │
│     │  - 检查本地缓存                                         │
│     │  - 缓存过期则开始递归查询                                │
│     ▼                                                        │
│  3. 根域名服务器（.）                                         │
│     │  - 返回 .com 权威服务器地址                              │
│     ▼                                                        │
│  4. 顶级域名服务器（.com）                                     │
│     │  - 返回 example.com 权威服务器地址                       │
│     ▼                                                        │
│  5. Route 53 权威 DNS                                        │
│     │  - 返回 www.example.com 的 IP 地址                      │
│     │  - 根据路由策略选择最优结果                              │
│     ▼                                                        │
│  6. 用户浏览器连接到目标 IP                                    │
└──────────────────────────────────────────────────────────────┘
```

#### Route 53 全球基础设施

```
Route 53 全球 Anycast 网络：

  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ 北美     │  │ 欧洲     │  │ 亚太     │  │ 南美     │
  │ 20+ 边缘 │  │ 15+ 边缘 │  │ 10+ 边缘 │  │ 5+ 边缘  │
  │ 站点     │  │ 站点     │  │ 站点     │  │ 站点     │
  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
       │             │             │             │
       └─────────────┴─────────────┴─────────────┘
                          │
                   ┌──────▼──────┐
                   │ Route 53    │
                   │ 权威 DNS    │
                   │ (多 AZ)     │
                   └─────────────┘

- 全球 50+ 边缘站点
- Anycast 路由自动选择最近的边缘站点
- 100% 可用性 SLA
- DNS 查询延迟 < 50ms
```

### 2. 托管区域（Hosted Zone）

#### 公有托管区域 vs 私有托管区域

| 特性 | 公有托管区域 | 私有托管区域 |
|------|------------|------------|
| 用途 | 公网 DNS 解析 | VPC 内部 DNS 解析 |
| 可见性 | 全球互联网 | 仅关联的 VPC |
| 典型场景 | 网站域名 | 内部服务发现 |
| 费用 | $0.50/月/区域 | $0.50/月/区域 |
| DNS 查询 | $0.40/百万次 | $0.40/百万次 |

#### 托管区域管理

```bash
# 创建公有托管区域
aws route53 create-hosted-zone \
  --name example.com \
  --caller-reference $(date +%s) \
  --hosted-zone-config Comment="Production website"

# 创建私有托管区域
aws route53 create-hosted-zone \
  --name internal.example.com \
  --caller-reference $(date +%s) \
  --hosted-zone-config Comment="Internal services",PrivateZone=true \
  --vpc VPCRegion=us-east-1,VPCId=vpc-12345678

# 列出所有托管区域
aws route53 list-hosted-zones

# 获取托管区域详情
aws route53 get-hosted-zone --id Z1234567890ABC

# 为私有托管区域关联额外 VPC
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id Z1234567890ABC \
  --vpc VPCRegion=us-west-2,VPCId=vpc-87654321

# 删除托管区域（需要先删除所有记录，除 NS 和 SOA）
aws route53 delete-hosted-zone --id Z1234567890ABC
```

#### 子域委派（Subdomain Delegation）

```
子域委派示例：

example.com（父域）
  ├── Route 53 托管区域 Z111111111
  │   ├── A    → 1.2.3.4
  │   ├── NS   → ns-1.awsdns-01.com.
  │   │          ns-2.awsdns-02.net.
  │   │          ns-3.awsdns-03.org.
  │   │          ns-4.awsdns-04.co.uk.
  │   └── NS (dev) → ns-5.awsdns-05.com.    ← 子域委派
  │                    ns-6.awsdns-06.net.
  │
  └── dev.example.com（子域）
      ├── Route 53 托管区域 Z222222222
      ├── A    → 5.6.7.8
      └── CNAME → api.dev.example.com

配置子域委派：
1. 在父域创建 NS 记录指向子域的 DNS 服务器
2. 创建子域的独立托管区域
3. 在子域托管区域中配置记录
```

### 3. DNS 记录类型

#### 记录类型详解

| 记录类型 | 说明 | 示例 | 用途 |
|----------|------|------|------|
| A | IPv4 地址 | `1.2.3.4` | 将域名映射到 IPv4 |
| AAAA | IPv6 地址 | `2001:db8::1` | 将域名映射到 IPv6 |
| CNAME | 规范名称 | `www.example.com → example.com` | 域名别名 |
| MX | 邮件交换 | `10 mail.example.com` | 邮件路由 |
| TXT | 文本记录 | `"v=spf1 include:amazonses.com ~all"` | SPF/DKIM/验证 |
| SRV | 服务记录 | `10 5 5060 sip.example.com` | 服务发现 |
| NS | 名称服务器 | `ns-1.awsdns-01.com.` | 域名服务器 |
| SOA | 起始授权 | | 域名管理信息 |
| CAA | 证书授权 | | 限制 SSL 证书签发 |

#### Alias 记录 vs CNAME 记录

```
Alias 记录 vs CNAME 记录：

┌─────────────────────────────────────────────────────────────┐
│                    CNAME 记录                                │
│                                                              │
│  www.example.com ──CNAME──> example.com                     │
│                                                              │
│  特点：                                                      │
│  - 只能用于非根域名（不能用于 example.com）                    │
│  - 需要两次 DNS 查询                                         │
│  - 可能产生额外费用                                           │
│  - 不支持在 zone apex 使用                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Alias 记录                                │
│                                                              │
│  example.com ──Alias──> my-alb-123456.us-east-1.elb.amazonaws.com
│                                                              │
│  特点：                                                      │
│  - 可以用于根域名（zone apex）                                │
│  - 单次 DNS 查询，更快                                        │
│  - 不额外收费                                                │
│  - 只能指向 AWS 资源                                         │
│  - 自动跟随目标 IP 变化                                       │
└─────────────────────────────────────────────────────────────┘
```

#### Alias 记录支持的 AWS 资源

| 资源类型 | 说明 |
|----------|------|
| ALB/NLB/CLB | 负载均衡器 |
| CloudFront Distribution | CDN 分发 |
| S3 Website Endpoint | S3 静态网站 |
| API Gateway | API 网关 |
| Elastic Beanstalk | Beanstalk 环境 |
| Global Accelerator | 全球加速器 |
| VPC Interface Endpoint | VPC 端点 |
| Route 53 记录（同区域） | 其他 Route 53 记录 |
| Amazon S3 Bucket | S3 存储桶 |

#### 记录管理

```bash
# 创建 A 记录
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "www.example.com",
          "Type": "A",
          "TTL": 300,
          "ResourceRecords": [
            {"Value": "1.2.3.4"}
          ]
        }
      }
    ]
  }'

# 创建 Alias 记录（指向 ALB）
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "example.com",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "Z35SXDOTRQ7X7K",
            "DNSName": "my-alb-123456.us-east-1.elb.amazonaws.com",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'

# 创建 CNAME 记录
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [
            {"Value": "my-api.us-east-1.elb.amazonaws.com"}
          ]
        }
      }
    ]
  }'

# 创建 MX 记录（邮件）
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "example.com",
          "Type": "MX",
          "TTL": 3600,
          "ResourceRecords": [
            {"Value": "10 inbound-smtp.us-east-1.amazonaws.com"}
          ]
        }
      }
    ]
  }'

# 创建 TXT 记录（SPF）
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "example.com",
          "Type": "TXT",
          "TTL": 3600,
          "ResourceRecords": [
            {"Value": "\"v=spf1 include:amazonses.com ~all\""}
          ]
        }
      }
    ]
  }'

# 更新记录
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "www.example.com",
          "Type": "A",
          "TTL": 300,
          "ResourceRecords": [
            {"Value": "5.6.7.8"}
          ]
        }
      }
    ]
  }'

# 删除记录
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "DELETE",
        "ResourceRecordSet": {
          "Name": "www.example.com",
          "Type": "A",
          "TTL": 300,
          "ResourceRecords": [
            {"Value": "1.2.3.4"}
          ]
        }
      }
    ]
  }'

# 列出托管区域中的所有记录
aws route53 list-resource-record-sets \
  --hosted-zone-id Z1234567890ABC
```

### 4. 路由策略（Routing Policies）

#### 路由策略总览

```
┌──────────────────────────────────────────────────────────────┐
│                    Route 53 路由策略                           │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Simple    │  │  Weighted   │  │  Latency    │          │
│  │   简单路由   │  │  加权路由    │  │  延迟路由    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Failover   │  │ Geolocation │  │ Geoproximity│          │
│  │  故障转移    │  │  地理位置    │  │  地理临近    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐                             │
│  │ Multivalue  │  │  IP-based   │                             │
│  │  多值路由    │  │  IP 路由     │                             │
│  └─────────────┘  └─────────────┘                             │
└──────────────────────────────────────────────────────────────┘
```

#### 1. Simple Routing（简单路由）

```
简单路由：一个域名对应一个或多个值

  www.example.com ──> 1.2.3.4
                  ──> 5.6.7.8
                  ──> 9.10.11.12

  客户端随机选择一个 IP

适用场景：
  - 单资源（如单个 EC2 实例）
  - 多个等价资源（轮询）

限制：
  - 不支持健康检查关联
  - 不支持条件路由
```

```bash
# 简单路由：单个 A 记录
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "simple.example.com",
          "Type": "A",
          "TTL": 300,
          "ResourceRecords": [
            {"Value": "1.2.3.4"},
            {"Value": "5.6.7.8"}
          ]
        }
      }
    ]
  }'
```

#### 2. Weighted Routing（加权路由）

```
加权路由：按权重比例分配流量

  api.example.com
       │
       ├── Weight=70% ──> us-east-1 (主区域)
       │                   IP: 1.2.3.4
       │                   Health Check: HC-East
       │
       ├── Weight=20% ──> us-west-2 (次区域)
       │                   IP: 5.6.7.8
       │                   Health Check: HC-West
       │
       └── Weight=10% ──> eu-west-1 (灰度区域)
                           IP: 9.10.11.12
                           Health Check: HC-EU

  流量分配：70% → us-east-1, 20% → us-west-2, 10% → eu-west-1

适用场景：
  - 流量分配（A/B 测试）
  - 金丝雀发布
  - 区域间流量调配
```

```bash
# 加权路由：70/20/10 分配
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "us-east-1",
          "Weight": 70,
          "TTL": 60,
          "ResourceRecords": [{"Value": "1.2.3.4"}],
          "HealthCheckId": "a]1234567-1234-1234-1234-123456789012"
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "us-west-2",
          "Weight": 20,
          "TTL": 60,
          "ResourceRecords": [{"Value": "5.6.7.8"}],
          "HealthCheckId": "b1234567-1234-1234-1234-123456789012"
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "eu-west-1",
          "Weight": 10,
          "TTL": 60,
          "ResourceRecords": [{"Value": "9.10.11.12"}],
          "HealthCheckId": "c1234567-1234-1234-1234-123456789012"
        }
      }
    ]
  }'
```

#### 3. Latency Routing（延迟路由）

```
延迟路由：将用户路由到延迟最低的区域

  api.example.com
       │
       ├── Latency: us-east-1 ──> 1.2.3.4
       │   (北美用户延迟最低)       延迟: 20ms
       │
       ├── Latency: us-west-2 ──> 5.6.7.8
       │   (西海岸用户延迟最低)     延迟: 35ms
       │
       └── Latency: eu-west-1 ──> 9.10.11.12
           (欧洲用户延迟最低)       延迟: 15ms

  Route 53 根据历史延迟数据自动选择最优区域

适用场景：
  - 多区域部署
  - 全球用户访问优化
  - 性敏感应用
```

```bash
# 延迟路由：多区域部署
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "us-east-1",
          "Region": "us-east-1",
          "TTL": 60,
          "ResourceRecords": [{"Value": "1.2.3.4"}],
          "HealthCheckId": "d1234567-1234-1234-1234-123456789012"
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "eu-west-1",
          "Region": "eu-west-1",
          "TTL": 60,
          "ResourceRecords": [{"Value": "9.10.11.12"}],
          "HealthCheckId": "e1234567-1234-1234-1234-123456789012"
        }
      }
    ]
  }'
```

#### 4. Failover Routing（故障转移路由）

```
故障转移路由：主备切换

  api.example.com
       │
       ├── Primary (主) ──> us-east-1
       │    IP: 1.2.3.4
       │    Health Check: HC-Primary
       │    状态: HEALTHY
       │
       └── Secondary (备) ──> us-west-2
            IP: 5.6.7.8
            Health Check: HC-Secondary
            状态: UNHEALTHY (不健康时不返回)

  正常情况：用户 → Primary (us-east-1)
  主站故障：用户 → Secondary (us-west-2)

适用场景：
  - 主备架构
  - 灾难恢复
  - 蓝绿部署
```

```bash
# 创建主健康检查
PRIMARY_HC=$(aws route53 create-health-check \
  --caller-reference "primary-$(date +%s)" \
  --health-check-config '{
    "IPAddress": "1.2.3.4",
    "Port": 80,
    "Type": "HTTP",
    "ResourcePath": "/health",
    "RequestInterval": 10,
    "FailureThreshold": 3,
    "EnableSNI": false
  }' \
  --query 'HealthCheck.Id' --output text)

# 创建备健康检查
SECONDARY_HC=$(aws route53 create-health-check \
  --caller-reference "secondary-$(date +%s)" \
  --health-check-config '{
    "IPAddress": "5.6.7.8",
    "Port": 80,
    "Type": "HTTP",
    "ResourcePath": "/health",
    "RequestInterval": 10,
    "FailureThreshold": 3,
    "EnableSNI": false
  }' \
  --query 'HealthCheck.Id' --output text)

# 故障转移路由
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch "{
    \"Changes\": [
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"api.example.com\",
          \"Type\": \"A\",
          \"SetIdentifier\": \"primary\",
          \"Failover\": \"PRIMARY\",
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"1.2.3.4\"}],
          \"HealthCheckId\": \"$PRIMARY_HC\"
        }
      },
      {
        \"Action\": \"CREATE\",
        \"ResourceRecordSet\": {
          \"Name\": \"api.example.com\",
          \"Type\": \"A\",
          \"SetIdentifier\": \"secondary\",
          \"Failover\": \"SECONDARY\",
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"5.6.7.8\"}],
          \"HealthCheckId\": \"$SECONDARY_HC\"
        }
      }
    ]
  }"
```

#### 5. Geolocation Routing（地理位置路由）

```
地理位置路由：基于用户地理位置返回不同结果

  api.example.com
       │
       ├── Continent: NA (北美) ──> us-east-1
       │    IP: 1.2.3.4
       │
       ├── Country: DE (德国) ──> eu-central-1
       │    IP: 5.6.7.8
       │
       ├── Country: JP (日本) ──> ap-northeast-1
       │    IP: 9.10.11.12
       │
       └── Default (默认) ──> us-east-1
            IP: 1.2.3.4

  匹配优先级：精确匹配 > 国家 > 大洲 > 默认

适用场景：
  - 内容本地化
  - 法规合规（数据主权）
  - 语言定向
```

```bash
# 地理位置路由
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "north-america",
          "GeoLocation": {"ContinentCode": "NA"},
          "TTL": 300,
          "ResourceRecords": [{"Value": "1.2.3.4"}]
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "germany",
          "GeoLocation": {"CountryCode": "DE"},
          "TTL": 300,
          "ResourceRecords": [{"Value": "5.6.7.8"}]
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "default",
          "GeoLocation": {"CountryCode": "*"},
          "TTL": 300,
          "ResourceRecords": [{"Value": "1.2.3.4"}]
        }
      }
    ]
  }'
```

#### 6. Multivalue Answer Routing（多值路由）

```
多值路由：返回多个健康记录，客户端随机选择

  api.example.com
       │
       ├── 1.2.3.4 (Health Check: ✅) ──> 返回
       ├── 5.6.7.8 (Health Check: ✅) ──> 返回
       ├── 9.10.11.12 (Health Check: ❌) ──> 不返回
       └── 13.14.15.16 (Health Check: ✅) ──> 返回

  返回最多 8 个健康记录
  客户端随机选择一个

适用场景：
  - 简单的负载均衡
  - 替代 ELB 的场景
  - 提高可用性
```

### 5. 健康检查（Health Checks）

#### 健康检查类型

```
┌──────────────────────────────────────────────────────────────┐
│                    Route 53 健康检查类型                        │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  1. 基于端点的健康检查                                 │    │
│  │     - HTTP/HTTPS：检查 HTTP 状态码                     │    │
│  │     - TCP：检查端口连通性                              │    │
│  │     - 字符串匹配：检查响应体内容                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  2. 基于 CloudWatch 的健康检查                        │    │
│  │     - 关联 CloudWatch 告警                            │    │
│  │     - 基于自定义指标判断健康状态                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  3. 计算型健康检查（Calculated）                       │    │
│  │     - 组合多个健康检查的状态                           │    │
│  │     - AND/OR/NOT 逻辑组合                             │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 健康检查配置

```bash
# HTTP 健康检查
aws route53 create-health-check \
  --caller-reference "http-check-$(date +%s)" \
  --health-check-config '{
    "IPAddress": "1.2.3.4",
    "Port": 80,
    "Type": "HTTP",
    "ResourcePath": "/health",
    "RequestInterval": 10,
    "FailureThreshold": 3,
    "EnableSNI": false
  }'

# HTTPS 健康检查
aws route53 create-health-check \
  --caller-reference "https-check-$(date +%s)" \
  --health-check-config '{
    "FullyQualifiedDomainName": "api.example.com",
    "Port": 443,
    "Type": "HTTPS",
    "ResourcePath": "/health",
    "RequestInterval": 10,
    "FailureThreshold": 3,
    "EnableSNI": true
  }'

# TCP 健康检查
aws route53 create-health-check \
  --caller-reference "tcp-check-$(date +%s)" \
  --health-check-config '{
    "IPAddress": "1.2.3.4",
    "Port": 3306,
    "Type": "TCP",
    "RequestInterval": 10,
    "FailureThreshold": 3
  }'

# 字符串匹配健康检查
aws route53 create-health-check \
  --caller-reference "string-check-$(date +%s)" \
  --health-check-config '{
    "FullyQualifiedDomainName": "api.example.com",
    "Port": 80,
    "Type": "HTTP_STR_MATCH",
    "ResourcePath": "/health",
    "SearchString": "\"status\":\"healthy\"",
    "RequestInterval": 30,
    "FailureThreshold": 3
  }'

# 基于 CloudWatch 的健康检查
aws route53 create-health-check \
  --caller-reference "cw-check-$(date +%s)" \
  --health-check-config '{
    "Type": "CLOUDWATCH_METRIC",
    "AlarmIdentifier": {
      "Name": "high-cpu-alarm",
      "Region": "us-east-1"
    },
    "InsufficientDataHealthStatus": "Unhealthy"
  }'

# 计算型健康检查
aws route53 create-health-check \
  --caller-reference "calc-check-$(date +%s)" \
  --health-check-config '{
    "Type": "CALCULATED",
    "HealthThreshold": 2,
    "ChildHealthChecks": [
      "a1234567-1234-1234-1234-123456789012",
      "b1234567-1234-1234-1234-123456789012",
      "c1234567-1234-1234-1234-123456789012"
    ],
    "Inverted": false
  }'

# 查询健康检查状态
aws route53 get-health-check-status \
  --health-check-id a1234567-1234-1234-1234-123456789012

# 列出所有健康检查
aws route53 list-health-checks

# 删除健康检查
aws route53 delete-health-check \
  --health-check-id a1234567-1234-1234-1234-123456789012
```

#### 健康检查参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `RequestInterval` | 检查间隔 | 30 秒（标准）/ 10 秒（快速） |
| `FailureThreshold` | 连续失败次数 | 3 |
| `MeasureLatency` | 测量延迟 | false |
| `Inverted` | 反转结果 | false |
| `EnableSNI` | 启用 SNI | false |
| `InsufficientDataHealthStatus` | 数据不足时状态 | LastKnownStatus |

### 6. DNSSEC（DNS Security Extensions）

#### DNSSEC 原理

```
┌──────────────────────────────────────────────────────────────┐
│                    DNSSEC 链式信任模型                         │
│                                                               │
│  根域名（.）                                                  │
│  ├── DS 记录：存储 .com 的公钥摘要                             │
│  └── RRSIG：根域名的签名                                      │
│       │                                                      │
│       ▼                                                      │
│  .com 顶级域名                                                │
│  ├── DNSKEY：公钥                                            │
│  ├── DS 记录：存储 example.com 的公钥摘要                     │
│  └── RRSIG：.com 的签名                                      │
│       │                                                      │
│       ▼                                                      │
│  example.com                                                  │
│  ├── DNSKEY：公钥                                            │
│  ├── RRSIG：example.com 的签名                                │
│  └── NSEC/NSEC3：记录不存在的证明                             │
│                                                               │
│  验证流程：                                                    │
│  1. 从根域名获取 .com 的 DS 记录                              │
│  2. 从 .com 获取 DNSKEY 并验证 DS                             │
│  3. 从 example.com 获取 DNSKEY 并验证 DS                      │
│  4. 验证 example.com 的 A 记录 RRSIG                         │
│  5. 如果所有验证通过，返回结果                                  │
└──────────────────────────────────────────────────────────────┘
```

#### DNSSEC 配置

```bash
# 注意：Route 53 的 DNSSEC 配置需要通过 AWS 控制台或 API
# 步骤概述：

# 1. 为托管区域启用 DNSSEC
# AWS 控制台操作：Route 53 → 托管区域 → 启用 DNSSEC

# 2. 创建 KMS 密钥用于签名
aws kms create-key \
  --description "Route 53 DNSSEC signing key" \
  --key-usage SIGN_VERIFY \
  --key-spec ECC_NIST_P256 \
  --key-policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "Allow Route 53 DNSSEC Service",
        "Effect": "Allow",
        "Principal": {
          "Service": "route53.amazonaws.com"
        },
        "Action": [
          "kms:Sign",
          "kms:Verify"
        ],
        "Resource": "*"
      }
    ]
  }'

# 3. 创建密钥签名密钥（KSK）
# 需要通过 Route 53 API 或控制台操作

# 4. 获取 DS 记录并添加到域名注册商
# DS 记录需要添加到父域（如 .com）的注册商处

# 5. 验证 DNSSEC 配置
dig +dnssec example.com
dig +dnssec +short DNSKEY example.com
```

### 7. SRE 实战案例

#### 场景 1：多区域高可用 DNS 架构

```
┌──────────────────────────────────────────────────────────────┐
│              多区域高可用 DNS 架构                              │
│                                                               │
│  用户请求                                                     │
│     │                                                        │
│     ▼                                                        │
│  Route 53 (Latency + Failover)                               │
│     │                                                        │
│     ├── us-east-1 (主)                                       │
│     │   ├── ALB ──> ECS Service (3 tasks)                   │
│     │   ├── RDS Multi-AZ                                    │
│     │   └── ElastiCache Redis                               │
│     │                                                        │
│     ├── us-west-2 (灾备)                                     │
│     │   ├── ALB ──> ECS Service (2 tasks)                   │
│     │   ├── RDS Read Replica (可提升为主)                    │
│     │   └── ElastiCache Redis                               │
│     │                                                        │
│     └── eu-west-1 (欧洲)                                     │
│         ├── ALB ──> ECS Service (2 tasks)                   │
│         ├── RDS Read Replica                                 │
│         └── ElastiCache Redis                               │
│                                                               │
│  DNS 配置：                                                    │
│  - Latency 路由：自动选择延迟最低的区域                        │
│  - Failover 路由：主区域故障时切换到灾备区域                   │
│  - 健康检查：每 10 秒检查一次，3 次失败触发切换                │
└──────────────────────────────────────────────────────────────┘
```

#### 场景 2：金丝雀发布 DNS 配置

```bash
# 金丝雀发布：5% 流量到新版本

# v1（当前版本）- 95% 流量
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1234567890ABC \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "v1-production",
          "Weight": 95,
          "TTL": 60,
          "ResourceRecords": [{"Value": "1.2.3.4"}],
          "HealthCheckId": "hc-v1"
        }
      },
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.example.com",
          "Type": "A",
          "SetIdentifier": "v2-canary",
          "Weight": 5,
          "TTL": 60,
          "ResourceRecords": [{"Value": "5.6.7.8"}],
          "HealthCheckId": "hc-v2"
        }
      }
    ]
  }'

# 逐步增加新版本流量：20%
# ... Weight=80, Weight=20

# 全量切换：100%
# ... Weight=0, Weight=100
```

#### 场景 3：故障排查 — DNS 解析问题

```
常见 DNS 问题排查：

1. DNS 解析不生效
   - 检查 TTL：等待 TTL 过期
   - 检查 NS 记录：域名注册商的 NS 是否指向 Route 53
   - 检查记录类型：A vs CNAME vs Alias
   - 工具：dig, nslookup, whois

2. DNS 解析延迟高
   - 检查 TTL 设置：过短的 TTL 增加查询次数
   - 检查 Route 53 边缘站点覆盖
   - 使用 Alias 记录替代 CNAME

3. 故障转移不生效
   - 检查健康检查状态
   - 检查健康检查的端口和路径
   - 检查防火墙是否允许 Route 53 探针 IP
   - Route 53 健康检查 IP 范围：https://ip-ranges.amazonaws.com/ip-ranges.json

4. 调试命令：
   dig +trace example.com
   dig @ns-1.awsdns-01.com. example.com
   nslookup -type=SOA example.com
   whois example.com
```

---

## 💻 实战练习

### 练习 1：基础操作 — 创建托管区域和记录

**目标**：创建托管区域、添加各种类型的 DNS 记录

```bash
# 步骤 1：创建托管区域
aws route53 create-hosted-zone \
  --name sre-lab.example.com \
  --caller-reference "lab-$(date +%s)" \
  --hosted-zone-config Comment="SRE Lab Environment"

# 步骤 2：记录 Hosted Zone ID
ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name sre-lab.example.com \
  --query 'HostedZones[0].Id' --output text)

# 步骤 3：添加 A 记录
aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "web.sre-lab.example.com",
          "Type": "A",
          "TTL": 300,
          "ResourceRecords": [{"Value": "1.2.3.4"}]
        }
      }
    ]
  }'

# 步骤 4：添加 CNAME 记录
aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "api.sre-lab.example.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "web.sre-lab.example.com"}]
        }
      }
    ]
  }'

# 步骤 5：列出所有记录
aws route53 list-resource-record-sets \
  --hosted-zone-id "$ZONE_ID"

# 清理
aws route53 delete-hosted-zone --id "$ZONE_ID"
```

### 练习 2：进阶场景 — 加权路由与健康检查

**目标**：配置加权路由和健康检查，实现流量分配

```bash
# 步骤 1：创建健康检查
HC_ID=$(aws route53 create-health-check \
  --caller-reference "lab-hc-$(date +%s)" \
  --health-check-config '{
    "FullyQualifiedDomainName": "example.com",
    "Port": 80,
    "Type": "HTTP",
    "ResourcePath": "/",
    "RequestInterval": 30,
    "FailureThreshold": 3
  }' \
  --query 'HealthCheck.Id' --output text)

echo "Health Check ID: $HC_ID"

# 步骤 2：查看健康检查状态（需要等待几分钟）
aws route53 get-health-check-status --health-check-id "$HC_ID"

# 步骤 3：创建加权路由记录（模拟）
aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch '{
    "Changes": [
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "weighted.sre-lab.example.com",
          "Type": "A",
          "SetIdentifier": "version-1",
          "Weight": 80,
          "TTL": 60,
          "ResourceRecords": [{"Value": "1.2.3.4"}]
        }
      },
      {
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "weighted.sre-lab.example.com",
          "Type": "A",
          "SetIdentifier": "version-2",
          "Weight": 20,
          "TTL": 60,
          "ResourceRecords": [{"Value": "5.6.7.8"}]
        }
      }
    ]
  }'

# 清理
aws route53 delete-health-check --health-check-id "$HC_ID"
```

### 练习 3：故障排查挑战 — DNS 解析问题定位

**场景**：用户报告网站无法访问，使用 DNS 工具排查

```bash
# 步骤 1：检查域名解析
dig +trace example.com

# 步骤 2：检查 NS 记录
dig NS example.com

# 步骤 3：检查 A 记录
dig A example.com

# 步骤 4：检查 CNAME 记录
dig CNAME api.example.com

# 步骤 5：使用不同 DNS 服务器查询
dig @8.8.8.8 example.com
dig @1.1.1.1 example.com

# 步骤 6：检查 Route 53 托管区域
aws route53 list-hosted-zones-by-name \
  --dns-name example.com

# 步骤 7：检查健康检查状态
aws route53 list-health-checks

# 挑战：编写脚本自动检测 DNS 解析问题
# 提示：检查 TTL、记录类型、健康检查状态、响应时间
```

---

## 🎯 面试题精选

### Q1: Route 53 Alias 记录和 CNAME 记录有什么区别？

**答案**：
| 特性 | Alias 记录 | CNAME 记录 |
|------|-----------|-----------|
| Zone apex 支持 | 支持（如 example.com） | 不支持 |
| DNS 查询次数 | 1 次 | 2 次 |
| 费用 | 免费 | 按查询收费 |
| 目标 | 仅 AWS 资源 | 任意域名 |
| 自动更新 | 是 | 否 |
| 适用场景 | AWS 资源映射 | 通用域名别名 |

### Q2: 如何设计一个跨区域的高可用 DNS 架构？

**答案**：
1. 使用 Latency Routing 将用户路由到延迟最低的区域
2. 为每个区域配置 Failover Routing，主区域故障时切换到灾备区域
3. 为每个记录配置健康检查，每 10 秒检查一次
4. 使用短 TTL（60 秒）确保快速切换
5. 配置 CloudWatch 告警监控健康检查状态

### Q3: Route 53 的路由策略有哪些？各自的适用场景是什么？

**答案**：
- **Simple**：单资源或等价资源，不支持健康检查
- **Weighted**：流量分配（A/B 测试、金丝雀发布）
- **Latency**：多区域部署，自动选择延迟最低的区域
- **Failover**：主备架构，主站故障时切换到备站
- **Geolocation**：基于用户地理位置（内容本地化、法规合规）
- **Geoproximity**：基于地理位置 + 偏移值（流量工程）
- **Multivalue**：返回多个健康记录，客户端随机选择

### Q4: Route 53 健康检查的故障转移时间是多少？

**答案**：
- 标准健康检查：30 秒间隔 × 3 次失败 = 最少 90 秒
- 快速健康检查：10 秒间隔 × 3 次失败 = 最少 30 秒
- 但还需要加上 DNS TTL 时间
- 建议：使用短 TTL（60 秒）+ 快速健康检查，总故障转移时间约 90 秒

### Q5: DNSSEC 如何保护 DNS 安全？

**答案**：
DNSSEC 通过数字签名验证 DNS 响应的完整性和真实性：
- 每个 DNS 区域使用私钥对记录签名（RRSIG）
- 公钥通过 DNSKEY 记录发布
- 父域通过 DS 记录存储子域公钥的摘要
- 形成从根域名到目标域名的信任链
- 防止 DNS 缓存投毒和中间人攻击

### Q6: 如何使用 Route 53 实现金丝雀发布？

**答案**：
使用加权路由策略：
1. 部署新版本到独立的端点
2. 创建两个加权记录：v1（95%）和 v2（5%）
3. 为两个版本分别配置健康检查
4. 监控新版本的关键指标（错误率、延迟）
5. 逐步增加新版本的权重：5% → 20% → 50% → 100%
6. 如果出现问题，立即降低权重或回滚到 0%

### Q7: Route 53 私有托管区域的用途是什么？

**答案**：
私有托管区域用于 VPC 内部的 DNS 解析：
- 允许在 VPC 内使用自定义域名（如 `db.internal.example.com`）
- 不暴露到公网，增强安全性
- 支持跨 VPC 共享（通过 VPC 关联）
- 典型场景：内部服务发现、数据库连接字符串、微服务通信

### Q8: 如何排查 Route 53 DNS 解析不生效的问题？

**答案**：
1. 检查 NS 记录：域名注册商的 NS 是否指向 Route 53
2. 检查记录是否存在：`aws route53 list-resource-record-sets`
3. 检查 TTL：等待 TTL 过期后再测试
4. 检查健康检查状态：不健康的记录不会返回
5. 使用不同 DNS 服务器测试：`dig @8.8.8.8 example.com`
6. 检查防火墙：确保 Route 53 健康检查 IP 未被阻止
7. 使用 `dig +trace` 追踪完整解析路径

---

## 📚 深入阅读

- [Route 53 官方文档](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)
- [Route 53 路由策略](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html)
- [Route 53 健康检查](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/welcome-health-checks.html)
- [DNSSEC 配置指南](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-configuring-dnssec.html)
- [Route 53 最佳实践](https://aws.amazon.com/blogs/architecture/disaster-recovery-dr-architecture-on-aws-part-iii-dns-and-dns-failback/)

---

## ✅ 自检清单

- [ ] 能够创建和管理公有/私有托管区域
- [ ] 理解 DNS 记录类型（A, AAAA, CNAME, MX, TXT, Alias）的区别
- [ ] 能够配置各种路由策略（Simple, Weighted, Latency, Failover, Geolocation）
- [ ] 能够创建和管理健康检查（HTTP, HTTPS, TCP, CloudWatch）
- [ ] 能够设计多区域高可用 DNS 架构
- [ ] 理解 DNSSEC 的原理和配置方式
- [ ] 能够使用 dig/nslookup 排查 DNS 解析问题
- [ ] 能够使用加权路由实现金丝雀发布
