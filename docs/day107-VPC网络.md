# Day 107: VPC 网络

> 📅 日期：2026-05-06
> 📖 学习主题：VPC 子网、路由表、Internet Gateway、NAT Gateway、NACL vs 安全组、VPC Peering、VPC Endpoint、Flow Logs
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 105（AWS 简介与账户管理）、Day 106（EC2 基础）

## 🎯 学习目标

- 理解 VPC 的网络架构与 CIDR 规划
- 掌握子网、路由表、Internet Gateway、NAT Gateway 的配置
- 能够区分 NACL 和安全组的使用场景
- 掌握 VPC Peering 和 VPC Endpoint 的原理与配置
- 能够使用 VPC Flow Logs 排查网络故障

---

## 📖 核心知识点

### 1. VPC 架构总览

VPC（Virtual Private Cloud）是 AWS 中的虚拟网络，是你在云中所有资源的网络基础。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VPC (10.0.0.0/16)                            │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  可用区 A (us-east-1a)                                        │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐            │ │
│  │  │ Public Subnet       │  │ Private Subnet      │            │ │
│  │  │ 10.0.1.0/24         │  │ 10.0.10.0/24        │            │ │
│  │  │                     │  │                     │            │ │
│  │  │ ┌─────┐ ┌─────┐    │  │ ┌─────┐ ┌─────┐    │            │ │
│  │  │ │ALB  │ │ NAT │    │  │ │App  │ │ App │    │            │ │
│  │  │ │     │ │ GW  │    │  │ │Srv  │ │ Srv │    │            │ │
│  │  │ └─────┘ └─────┘    │  │ └─────┘ └─────┘    │            │ │
│  │  └─────────────────────┘  └─────────────────────┘            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  可用区 B (us-east-1b)                                        │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐            │ │
│  │  │ Public Subnet       │  │ Private Subnet      │            │ │
│  │  │ 10.0.2.0/24         │  │ 10.0.20.0/24        │            │ │
│  │  │                     │  │                     │            │ │
│  │  │ ┌─────┐ ┌─────┐    │  │ ┌─────┐ ┌─────┐    │            │ │
│  │  │ │ALB  │ │ NAT │    │  │ │App  │ │ DB  │    │            │ │
│  │  │ │     │ │ GW  │    │  │ │Srv  │ │     │    │            │ │
│  │  │ └─────┘ └─────┘    │  │ └─────┘ └─────┘    │            │ │
│  │  └─────────────────────┘  └─────────────────────┘            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  路由逻辑                                                      │ │
│  │                                                                │ │
│  │  Public Subnet → Route Table:                                  │ │
│  │    10.0.0.0/16 → local (VPC 内部通信)                         │ │
│  │    0.0.0.0/0   → igw-xxxx (Internet Gateway)                  │ │
│  │                                                                │ │
│  │  Private Subnet → Route Table:                                 │ │
│  │    10.0.0.0/16 → local                                        │ │
│  │    0.0.0.0/0   → nat-xxxx (NAT Gateway，仅出站)              │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. CIDR 规划

```bash
# 创建 VPC
aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=sre-prod-vpc}]'

# 启用 DNS 主机名（必须，否则 EC2 无法解析公共 DNS）
aws ec2 modify-vpc-attribute \
  --vpc-id vpc-0123456789abcdef0 \
  --enable-dns-hostnames '{"Value": true}'

aws ec2 modify-vpc-attribute \
  --vpc-id vpc-0123456789abcdef0 \
  --enable-dns-support '{"Value": true}'
```

**CIDR 规划建议：**

| 用途 | CIDR | 可用 IP 数 | 说明 |
|------|------|-----------|------|
| VPC | 10.0.0.0/16 | 65,536 | 整个 VPC |
| Public Subnet A | 10.0.1.0/24 | 251 | ALB, NAT GW, Bastion |
| Public Subnet B | 10.0.2.0/24 | 251 | ALB, NAT GW |
| Private Subnet A | 10.0.10.0/24 | 251 | 应用服务器 |
| Private Subnet B | 10.0.20.0/24 | 251 | 应用服务器 |
| Data Subnet A | 10.0.100.0/24 | 251 | 数据库 |
| Data Subnet B | 10.0.101.0/24 | 251 | 数据库 |

**注意：** 每个子网 AWS 保留 5 个 IP（前 4 个 + 最后 1 个），所以 /24 子网实际可用 251 个 IP。

---

### 3. 子网（Subnet）

```bash
# 创建公有子网
aws ec2 create-subnet \
  --vpc-id vpc-0123456789abcdef0 \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=public-1a}]'

# 设置自动分配公有 IP（公有子网需要）
aws ec2 modify-subnet-attribute \
  --subnet-id subnet-0123456789abcdef0 \
  --map-public-ip-on-launch

# 创建私有子网
aws ec2 create-subnet \
  --vpc-id vpc-0123456789abcdef0 \
  --cidr-block 10.0.10.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=private-1a}]'

# 列出子网
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=vpc-0123456789abcdef0" \
  --query "Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,MapPublicIpOnLaunch,Tags[?Key=='Name'].Value|[0]]" \
  --output table
```

---

### 4. Internet Gateway（IGW）

Internet Gateway 是 VPC 连接互联网的网关，只用于公有子网。

```bash
# 创建 Internet Gateway
aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=sre-igw}]'

# 附加到 VPC
aws ec2 attach-internet-gateway \
  --internet-gateway-id igw-0123456789abcdef0 \
  --vpc-id vpc-0123456789abcdef0

# 创建公有子网的路由表
aws ec2 create-route-table \
  --vpc-id vpc-0123456789abcdef0 \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=public-rt}]'

# 添加默认路由到 IGW
aws ec2 create-route \
  --route-table-id rtb-0123456789abcdef0 \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id igw-0123456789abcdef0

# 关联子网
aws ec2 associate-route-table \
  --route-table-id rtb-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0
```

---

### 5. NAT Gateway

NAT Gateway 允许私有子网中的实例访问互联网（仅出站），同时阻止互联网主动访问。

```
┌─────────────────────────────────────────────────────────────────┐
│                    NAT Gateway 流量路径                          │
│                                                                 │
│  私有子网实例                公有子网              互联网        │
│  ┌─────────┐               ┌─────────┐          ┌─────────┐   │
│  │ App Srv │ ──出站请求──▶ │  NAT    │ ────────▶│ Internet│   │
│  │ 10.0.10.5│              │  GW     │          │         │   │
│  └─────────┘               │ EIP:    │          └─────────┘   │
│       ▲                    │ 1.2.3.4 │               │        │
│       │                    └─────────┘               │        │
│       │                         ▲                    │        │
│       └─────响应（源NAT回）─────┘◀──────响应─────────┘        │
│                                                                 │
│  关键点：                                                        │
│  - NAT GW 必须在公有子网                                        │
│  - 需要弹性 IP                                                  │
│  - 按小时 + 数据量收费                                          │
│  - 单个 NAT GW 带宽最高 45 Gbps                                │
│  - 生产环境每个 AZ 部署一个（避免单点）                          │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 分配弹性 IP（NAT Gateway 需要）
aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=nat-eip-1a}]'

# 创建 NAT Gateway（在公有子网）
aws ec2 create-nat-gateway \
  --subnet-id subnet-public-1a \
  --allocation-id eipalloc-0123456789abcdef0 \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=nat-gw-1a}]'

# 等待 NAT Gateway 可用
aws ec2 wait nat-gateway-available \
  --nat-gateway-ids nat-0123456789abcdef0

# 创建私有子网路由表
aws ec2 create-route-table \
  --vpc-id vpc-0123456789abcdef0 \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=private-rt-1a}]'

# 添加默认路由到 NAT Gateway
aws ec2 create-route \
  --route-table-id rtb-private-1a \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id nat-0123456789abcdef0

# 关联私有子网
aws ec2 associate-route-table \
  --route-table-id rtb-private-1a \
  --subnet-id subnet-private-1a
```

---

### 6. NACL vs 安全组

```
┌─────────────────────────────────────────────────────────────────┐
│                    NACL vs 安全组 详细对比                       │
│                                                                 │
│  特性              NACL                    安全组                │
│  ───────────────────────────────────────────────────────────    │
│  作用范围          子网级别                实例级别              │
│  状态              无状态                  有状态                │
│  规则类型          Allow + Deny            仅 Allow             │
│  规则评估          按编号顺序，第一条匹配  所有规则合并评估      │
│  返回流量          需要显式允许规则        自动允许              │
│  默认行为          允许所有                拒绝所有              │
│  应用对象          子网内所有实例          指定的实例            │
│                                                                 │
│  典型使用场景：                                                  │
│  NACL: 阻止已知恶意 IP、子网级访问控制                          │
│  安全组: 应用级访问控制（推荐主要使用）                          │
│                                                                 │
│  最佳实践：                                                      │
│  1. 优先使用安全组（更灵活，有状态）                            │
│  2. NACL 作为第二层防御（无状态，更严格）                       │
│  3. 两者配合使用                                                │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# NACL 操作
# 创建 NACL
aws ec2 create-network-acl \
  --vpc-id vpc-0123456789abcdef0 \
  --tag-specifications 'ResourceType=network-acl,Tags=[{Key=Name,Value=sre-nacl}]'

# 添加入站规则 — 允许 HTTP
aws ec2 create-network-acl-entry \
  --network-acl-id acl-0123456789abcdef0 \
  --rule-number 100 \
  --protocol tcp \
  --port-range From=80,To=80 \
  --cidr-block 0.0.0.0/0 \
  --rule-action allow \
  --ingress

# 添加入站规则 — 允许 HTTPS
aws ec2 create-network-acl-entry \
  --network-acl-id acl-0123456789abcdef0 \
  --rule-number 110 \
  --protocol tcp \
  --port-range From=443,To=443 \
  --cidr-block 0.0.0.0/0 \
  --rule-action allow \
  --ingress

# 添加入站规则 — 允许临时端口（返回流量需要）
aws ec2 create-network-acl-entry \
  --network-acl-id acl-0123456789abcdef0 \
  --rule-number 120 \
  --protocol tcp \
  --port-range From=1024,To=65535 \
  --cidr-block 0.0.0.0/0 \
  --rule-action allow \
  --ingress

# 添加入站规则 — 拒绝特定 IP
aws ec2 create-network-acl-entry \
  --network-acl-id acl-0123456789abcdef0 \
  --rule-number 50 \
  --protocol -1 \
  --cidr-block 203.0.113.0/24 \
  --rule-action deny \
  --ingress

# 删除 NACL 规则
aws ec2 delete-network-acl-entry \
  --network-acl-id acl-0123456789abcdef0 \
  --rule-number 50 \
  --ingress
```

---

### 7. VPC Peering

VPC Peering 连接两个 VPC，使它们可以通过私有 IP 通信。

```
┌─────────────────────────────────────────────────────────────────┐
│                    VPC Peering 架构                              │
│                                                                 │
│  VPC A (10.0.0.0/16)          VPC B (172.16.0.0/16)            │
│  ┌─────────────────┐          ┌─────────────────┐              │
│  │                 │          │                 │              │
│  │ ┌─────┐        │          │        ┌─────┐ │              │
│  │ │ EC2 │        │          │        │ RDS │ │              │
│  │ │10.0.│        │          │        │172.16│ │              │
│  │ │1.10 │────────┼──Peer───▶┼────────│.0.20│ │              │
│  │ └─────┘        │          │        └─────┘ │              │
│  │                 │          │                 │              │
│  │ Route:         │          │ Route:          │              │
│  │ 172.16.0.0/16  │          │ 10.0.0.0/16     │              │
│  │ → pcx-xxxx     │          │ → pcx-xxxx      │              │
│  └─────────────────┘          └─────────────────┘              │
│                                                                 │
│  限制：                                                         │
│  - CIDR 不能重叠                                               │
│  - 不支持传递路由（A↔B, B↔C 不等于 A↔C）                      │
│  - 跨账户/跨 Region 都支持                                     │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建 VPC Peering（同账户）
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-vpc-a-id \
  --peer-vpc-id vpc-vpc-b-id \
  --tag-specifications 'ResourceType=vpc-peering-connection,Tags=[{Key=Name,Value=a-to-b-peering}]'

# 接受 Peering（对端账户/Region 需要接受）
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id pcx-0123456789abcdef0

# 在 VPC A 的路由表中添加到 VPC B 的路由
aws ec2 create-route \
  --route-table-id rtb-vpc-a \
  --destination-cidr-block 172.16.0.0/16 \
  --vpc-peering-connection-id pcx-0123456789abcdef0

# 在 VPC B 的路由表中添加到 VPC A 的路由
aws ec2 create-route \
  --route-table-id rtb-vpc-b \
  --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id pcx-0123456789abcdef0

# 查看 Peering 连接
aws ec2 describe-vpc-peering-connections \
  --query "VpcPeeringConnections[*].[VpcPeeringConnectionId,Status.Code,RequesterVpcInfo.VpcId,AccepterVpcInfo.VpcId]" \
  --output table

# 跨账户 Peering
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-local \
  --peer-vpc-id vpc-remote \
  --peer-owner-id 222222222222 \
  --peer-region us-west-2
```

---

### 8. VPC Endpoint

VPC Endpoint 允许私有子网中的实例访问 AWS 服务，无需经过互联网。

```
┌─────────────────────────────────────────────────────────────────┐
│                    VPC Endpoint 类型                             │
│                                                                 │
│  Gateway Endpoint              Interface Endpoint               │
│  ┌───────────────────┐        ┌───────────────────┐            │
│  │ S3, DynamoDB      │        │ 大多数 AWS 服务    │            │
│  │ 免费               │        │ 按小时 + 数据收费  │            │
│  │ 路由表条目         │        │ ENI (弹性网络接口) │            │
│  │ 仅同 Region        │        │ 支持跨 Region      │            │
│  └───────────────────┘        └───────────────────┘            │
│                                                                 │
│  流量路径对比：                                                  │
│  无 Endpoint:  私有子网 → NAT GW → 互联网 → S3                 │
│  有 Endpoint:  私有子网 → VPC Endpoint → S3 (私有网络)          │
│                                                                 │
│  优势：                                                          │
│  1. 更安全（流量不离开 AWS 网络）                               │
│  2. 更低延迟                                                    │
│  3. 更低成本（避免 NAT Gateway 数据费）                         │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建 Gateway Endpoint（S3）
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-private-1a rtb-private-1b \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [
          "arn:aws:s3:::my-app-bucket",
          "arn:aws:s3:::my-app-bucket/*"
        ]
      }
    ]
  }'

# 创建 Interface Endpoint（ECR）
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0123456789abcdef0 \
  --service-name com.amazonaws.us-east-1.ecr.api \
  --vpc-endpoint-type Interface \
  --subnet-ids subnet-private-1a subnet-private-1b \
  --security-group-ids sg-endpoint-sg \
  --private-dns-enabled

# 列出 VPC Endpoints
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=vpc-0123456789abcdef0" \
  --query "VpcEndpoints[*].[VpcEndpointId,ServiceName,VpcEndpointType,State]" \
  --output table

# 删除 VPC Endpoint
aws ec2 delete-vpc-endpoints \
  --vpc-endpoint-ids vpce-0123456789abcdef0
```

---

### 9. VPC Flow Logs

VPC Flow Logs 记录 VPC 中网络接口的入站和出站流量，用于网络故障排查和安全审计。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Flow Log 记录格式                             │
│                                                                 │
│  字段顺序：                                                      │
│  version account-id interface-id srcaddr dstaddr                │
│  srcport dstport protocol packets bytes                         │
│  start end action log-status                                    │
│                                                                 │
│  示例记录：                                                      │
│  2 123456789012 eni-0123456789 10.0.1.10 10.0.10.20            │
│  49761 3306 6 20 1234 1620000000 1620000060 ACCEPT OK          │
│                                                                 │
│  action: ACCEPT 或 REJECT                                       │
│  log-status: OK, NODATA, SKIPDATA                               │
│                                                                 │
│  Flow Log 目标：                                                │
│  - CloudWatch Logs（实时分析）                                  │
│  - S3（长期存储，成本低）                                       │
│  - Kinesis Firehose（流式处理）                                 │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建 Flow Log（发送到 CloudWatch Logs）
# 先创建 IAM Role
cat > /tmp/flowlog-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "vpc-flow-logs.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name VPCFlowLogsRole \
  --assume-role-policy-document file:///tmp/flowlog-trust.json

cat > /tmp/flowlog-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name VPCFlowLogsRole \
  --policy-name FlowLogsPolicy \
  --policy-document file:///tmp/flowlog-policy.json

# 创建 Flow Log
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-0123456789abcdef0 \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /vpc/flowlogs \
  --deliver-logs-permission-arn arn:aws:iam::123456789012:role/VPCFlowLogsRole \
  --tag-specifications 'ResourceType=vpc-flow-log,Tags=[{Key=Name,Value=sre-vpc-flowlog}]'

# 创建 Flow Log（发送到 S3，更便宜）
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-0123456789abcdef0 \
  --traffic-type ALL \
  --log-destination-type s3 \
  --log-destination arn:aws:s3:::sre-flowlog-bucket/vpc-flowlogs/ \
  --max-aggregation-interval 60 \
  --tag-specifications 'ResourceType=vpc-flow-log,Tags=[{Key=Name,Value=sre-vpc-flowlog-s3}]'

# 查询 Flow Logs（CloudWatch Logs Insights）
aws logs start-query \
  --log-group-name /vpc/flowlogs \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --end-time $(date +%s)000 \
  --query-string '
    fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, action
    | filter action = "REJECT"
    | stats count(*) as rejectCount by srcAddr, dstAddr, dstPort
    | sort rejectCount desc
    | limit 20
  '
```

---

### 10. SRE 实战案例

#### 案例 1：私有子网中的实例无法访问互联网

**故障现象：** 私有子网中的 EC2 实例无法 yum update，返回 `Could not resolve host`。

```bash
# 1. 检查路由表
aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values=subnet-private-1a" \
  --query "RouteTables[*].Routes[*].[DestinationCidrBlock,GatewayId,NatGatewayId]" \
  --output table

# 2. 检查 NAT Gateway 状态
aws ec2 describe-nat-gateways \
  --filter "Name=subnet-id,Values=subnet-public-1a" "Name=state,Values=available" \
  --query "NatGateways[*].[NatGatewayId,State,VpcId]"

# 3. 检查公有子网路由（NAT GW 所在子网）
aws ec2 describe-route-tables \
  --filters "Name=association.subnet-id,Values=subnet-public-1a" \
  --query "RouteTables[*].Routes[*].[DestinationCidrBlock,GatewayId]"

# 4. 检查 NAT GW 的 EIP 是否正常
aws ec2 describe-nat-gateways \
  --nat-gateway-ids nat-xxxxx \
  --query "NatGateways[0].NatGatewayAddresses"

# 5. 检查 NACL（NAT GW 所在子网需要允许出站 443）
aws ec2 describe-network-acls \
  --filters "Name=association.subnet-id,Values=subnet-public-1a" \
  --query "NetworkAcls[*].Entries"

# 根因：公有子网的 NACL 没有允许 NAT GW 返回流量的临时端口规则
# 解决方案：添加 NACL 入站规则，允许 1024-65535 端口
```

#### 案例 2：VPC Peering 连接后无法通信

```bash
# 1. 检查 Peering 状态
aws ec2 describe-vpc-peering-connections \
  --vpc-peering-connection-ids pcx-xxxxx \
  --query "VpcPeeringConnections[0].Status"

# 2. 检查双方路由表
# VPC A
aws ec2 describe-route-tables \
  --filters "Name=route.vpc-peering-connection-id,Values=pcx-xxxxx"
# VPC B
aws ec2 describe-route-tables \
  --filters "Name=route.vpc-peering-connection-id,Values=pcx-xxxxx" \
  --region us-west-2

# 3. 检查安全组（是否允许对端 CIDR）
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx \
  --query "SecurityGroups[*].IpPermissions"

# 4. 检查 CIDR 是否重叠
# VPC A: 10.0.0.0/16
# VPC B: 10.0.0.0/16  ← 重叠！
# 重叠的 CIDR 不能 Peering

# 根因：安全组只允许了本 VPC 的 CIDR，没有添加对端 VPC 的 CIDR
```

#### 案例 3：Flow Logs 发现异常流量

```bash
# 查询被拒绝的流量
aws logs start-query \
  --log-group-name /vpc/flowlogs \
  --start-time $(date -d '24 hours ago' +%s)000 \
  --end-time $(date +%s)000 \
  --query-string '
    fields @timestamp, srcAddr, dstAddr, dstPort, action
    | filter action = "REJECT"
    | stats count(*) as attempts by srcAddr, dstPort
    | sort attempts desc
    | limit 10
  '

# 结果发现大量来自 203.0.113.50 的 22 端口连接尝试
# 处理方案：在 NACL 中永久阻止该 IP
aws ec2 create-network-acl-entry \
  --network-acl-id acl-xxxxx \
  --rule-number 10 \
  --protocol tcp \
  --port-range From=22,To=22 \
  --cidr-block 203.0.113.50/32 \
  --rule-action deny \
  --ingress
```

---

## 💻 实战练习

### 练习 1：基础操作 — 创建完整的 VPC 架构

```bash
# 步骤 1: 创建 VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.10.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=exercise-vpc}]' \
  --query "Vpc.VpcId" --output text)

aws ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-hostnames '{"Value":true}'
aws ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-support '{"Value":true}'

# 步骤 2: 创建 Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=exercise-igw}]' \
  --query "InternetGateway.InternetGatewayId" --output text)
aws ec2 attach-internet-gateway --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID"

# 步骤 3: 创建公有子网
PUB_SUBNET=$(aws ec2 create-subnet \
  --vpc-id "$VPC_ID" \
  --cidr-block 10.10.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=exercise-public}]' \
  --query "Subnet.SubnetId" --output text)
aws ec2 modify-subnet-attribute --subnet-id "$PUB_SUBNET" --map-public-ip-on-launch

# 步骤 4: 创建私有子网
PRIV_SUBNET=$(aws ec2 create-subnet \
  --vpc-id "$VPC_ID" \
  --cidr-block 10.10.10.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=exercise-private}]' \
  --query "Subnet.SubnetId" --output text)

# 步骤 5: 创建公有路由表
PUB_RT=$(aws ec2 create-route-table \
  --vpc-id "$VPC_ID" \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=exercise-public-rt}]' \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-route --route-table-id "$PUB_RT" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW_ID"
aws ec2 associate-route-table --route-table-id "$PUB_RT" --subnet-id "$PUB_SUBNET"

# 步骤 6: 验证
aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --query "Vpcs[0].CidrBlock"
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,MapPublicIpOnLaunch]" --output table
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "RouteTables[*].[RouteTableId,Routes[*].[DestinationCidrBlock,GatewayId]]" --output table
```

### 练习 2：进阶场景 — 配置 NAT Gateway

```bash
# 步骤 1: 创建 NAT Gateway
EIP_ALLOC=$(aws ec2 allocate-address --domain vpc --query "AllocationId" --output text)
NAT_GW=$(aws ec2 create-nat-gateway \
  --subnet-id "$PUB_SUBNET" \
  --allocation-id "$EIP_ALLOC" \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=exercise-nat}]' \
  --query "NatGateway.NatGatewayId" --output text)

echo "Waiting for NAT Gateway..."
aws ec2 wait nat-gateway-available --nat-gateway-ids "$NAT_GW"

# 步骤 2: 创建私有路由表
PRIV_RT=$(aws ec2 create-route-table \
  --vpc-id "$VPC_ID" \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=exercise-private-rt}]' \
  --query "RouteTable.RouteTableId" --output text)
aws ec2 create-route --route-table-id "$PRIV_RT" --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$NAT_GW"
aws ec2 associate-route-table --route-table-id "$PRIV_RT" --subnet-id "$PRIV_SUBNET"

# 步骤 3: 验证路由
aws ec2 describe-route-tables --route-table-ids "$PRIV_RT" \
  --query "RouteTables[0].Routes[*].[DestinationCidrBlock,NatGatewayId]"
```

### 练习 3：故障排查挑战 — VPC Endpoint 排查

**场景：** 私有子网中的实例无法访问 S3，已经配置了 VPC Endpoint。

```bash
# 排查步骤
# 1. 检查 VPC Endpoint 是否存在
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=service-name,Values=*s3*" \
  --query "VpcEndpoints[*].[VpcEndpointId,State,RouteTableIds]"

# 2. 检查 Endpoint 策略
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-xxxxx \
  --query "VpcEndpoints[0].PolicyDocument"

# 3. 检查路由表是否关联了 Endpoint
aws ec2 describe-route-tables \
  --filters "Name=route.gateway-id,Values=vpce-xxxxx" \
  --query "RouteTables[*].RouteTableId"

# 4. 检查 S3 Bucket Policy 是否拒绝了 VPC Endpoint
aws s3api get-bucket-policy --bucket my-bucket

# 答案：VPC Endpoint 策略中只允许了特定 Bucket，但应用访问的是另一个 Bucket
# 或者：S3 Bucket Policy 中有 Deny VPC Endpoint 的条件
```

---

## 🎯 面试题精选

### 题目 1：公有子网和私有子网的区别？

**答：**
- **公有子网**：路由表中有指向 Internet Gateway 的 0.0.0.0/0 路由，实例可以分配公有 IP，互联网可以直接访问
- **私有子网**：路由表中没有 IGW 路由（或通过 NAT Gateway 出站），实例没有公有 IP，互联网不能直接访问

关键区别不在于 IP 地址范围，而在于路由表配置。

### 题目 2：NAT Gateway 和 NAT Instance 的区别？

**答：**
- **NAT Gateway**：AWS 托管，高可用（单 AZ 内），最高 45 Gbps，自动扩展，无需管理，按小时+数据收费
- **NAT Instance**：用户管理的 EC2 实例，需要手动管理高可用，带宽取决于实例类型，可以使用 Spot 实例降低成本

生产环境推荐 NAT Gateway，开发环境可考虑 NAT Instance 节约成本。

### 题目 3：VPC Peering 的限制有哪些？

**答：**
1. CIDR 不能重叠
2. 不支持传递路由（A↔B, B↔C 不等于 A↔C）
3. 同一 VPC 只能有一个 Peering 到同一对端 VPC
4. 不支持组播/广播
5. 跨 Region Peering 有延迟

如果需要传递路由，使用 Transit Gateway。

### 题目 4：什么是 Transit Gateway？

**答：** Transit Gateway 是中心化的网络枢纽，可以连接多个 VPC 和本地网络。优势：
- 支持传递路由
- 简化网络拓扑（Hub-Spoke 模型）
- 支持路由隔离（通过路由表）
- 支持跨 Region 对等连接
- 适用于大规模多 VPC 架构

### 题目 5：NACL 规则的评估顺序是什么？

**答：** NACL 规则按编号从小到大评估，第一条匹配的规则生效。默认 NACL 允许所有入站和出站流量。

最佳实践：使用 100 的倍数作为规则编号（100, 200, 300），方便后续插入规则。

### 题目 6：VPC Endpoint 的两种类型有什么区别？

**答：**
- **Gateway Endpoint**：仅支持 S3 和 DynamoDB，免费，通过路由表实现，不创建 ENI
- **Interface Endpoint**：支持大多数 AWS 服务，按小时+数据收费，创建 ENI，支持跨 Region

生产环境建议为 S3 和 DynamoDB 配置 Gateway Endpoint，其他服务按需配置 Interface Endpoint。

### 题目 7：如何实现 VPC 与本地数据中心的连接？

**答：**
1. **VPN 连接**：通过 Internet Gateway 建立 IPsec VPN，快速但依赖互联网
2. **Direct Connect**：专线连接，低延迟高带宽，但需要物理线路
3. **Site-to-Site VPN**：通过 Virtual Private Gateway 建立
4. **Transit Gateway**：集中管理多个 VPN/DX 连接

### 题目 8：VPC 中默认有多少个路由表？可以创建多少个？

**答：**
- 每个 VPC 自动创建 1 个主路由表（Main Route Table）
- 最多可以创建 200 个路由表（默认限制，可申请提高）
- 每个子网必须关联一个路由表，未显式关联的子网使用主路由表
- 每个路由表最多 50 条路由（可申请提高到 200）

---

## 📚 深入阅读

- [VPC 官方文档](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)
- [VPC 网络设计最佳实践](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-best-practices.html)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
- [Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)
- [VPC Endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)

---

## ✅ 自检清单

- [ ] 能够设计 VPC 的 CIDR 规划方案
- [ ] 能够创建公有子网和私有子网
- [ ] 能够配置 Internet Gateway 和路由表
- [ ] 能够部署 NAT Gateway 并配置私有子网路由
- [ ] 能够区分 NACL 和安全组的使用场景
- [ ] 能够配置 VPC Peering 并添加路由
- [ ] 能够创建 Gateway Endpoint 和 Interface Endpoint
- [ ] 能够配置 VPC Flow Logs 并查询日志
- [ ] 能够使用 Flow Logs 排查网络故障
- [ ] 理解 Transit Gateway 的适用场景
