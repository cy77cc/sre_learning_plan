# Day 106: EC2 基础

> 📅 日期：2026-05-05
> 📖 学习主题：实例类型、AMI、安全组、密钥对、用户数据、EBS 卷类型、弹性 IP、费用优化
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 105（AWS 简介与账户管理）

## 🎯 学习目标

- 理解 EC2 实例类型族的分类与选型策略
- 掌握 AMI、安全组、密钥对的管理
- 理解 EBS 卷类型与性能特征，能够根据场景选择合适的存储
- 掌握 User Data 实现实例初始化自动化
- 理解费用优化策略（Spot、Reserved、Savings Plans）

---

## 📖 核心知识点

### 1. EC2 实例类型

EC2（Elastic Compute Cloud）提供按需的虚拟计算资源。实例类型决定了 CPU、内存、存储和网络能力。

#### 1.1 实例类型族

```
┌─────────────────────────────────────────────────────────────────┐
│                    EC2 实例类型族                                │
│                                                                 │
│  通用型 (General Purpose)                                       │
│  ├── T 系列 (t3, t3a, t4g) — 突发性能，适合开发/测试            │
│  ├── M 系列 (m6i, m7g)   — 均衡，适合 Web 应用/微服务          │
│  └── Mac 系列 (mac1, mac2) — macOS 环境                        │
│                                                                 │
│  计算优化型 (Compute Optimized)                                 │
│  ├── C 系列 (c6i, c7g)   — 高性能计算，批处理                  │
│  └── Hpc 系列             — HPC 工作负载                        │
│                                                                 │
│  内存优化型 (Memory Optimized)                                  │
│  ├── R 系列 (r6i, r7g)   — 内存数据库，缓存                    │
│  ├── X 系列 (x2idn)      — 大内存 SAP/HANA                    │
│  └── z 系列              — 高频数据库                          │
│                                                                 │
│  存储优化型 (Storage Optimized)                                 │
│  ├── I 系列 (i4i)        — 高 IOPS 数据库（NVMe）              │
│  ├── D 系列 (d3)         — 大容量顺序读写（HDD）               │
│  └── Im/Is 系列          — 密集存储                            │
│                                                                 │
│  加速计算型 (Accelerated Computing)                             │
│  ├── P 系列 (p4d, p5)    — ML 训练（GPU）                      │
│  ├── G 系列 (g5, g6)     — 图形/ML 推理（GPU）                 │
│  ├── Inf 系列 (inf2)     — ML 推理（AWS Inferentia）           │
│  └── Trn 系列 (trn1)     — ML 训练（AWS Trainium）             │
│                                                                 │
│  ARM 架构（Graviton）                                          │
│  ├── t4g, m7g, c7g, r7g  — 性价比高 20-40%                    │
│  └── 适合大多数 Linux 工作负载                                  │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 列出所有实例类型
aws ec2 describe-instance-types \
  --filters "Name=instance-type,Values=t3.*" \
  --query "InstanceTypes[*].[InstanceType,VCpuInfo.DefaultVCpus,MemoryInfo.SizeInMiB]" \
  --output table

# 查看特定实例类型的详细信息
aws ec2 describe-instance-types \
  --instance-types t3.medium \
  --query "InstanceTypes[0].{CPU:VCpuInfo.DefaultVCpus,Memory:MemoryInfo.SizeInMiB,Network:NetworkInfo.NetworkPerformance}"

# 查看可用区中可用的实例类型
aws ec2 describe-instance-type-offerings \
  --location-type availability-zone \
  --filters "Name=instance-type,Values=m6i.large" \
  --region us-east-1 \
  --output table
```

#### 1.2 SRE 场景选型指南

| 场景 | 推荐类型 | 原因 |
|------|---------|------|
| Web 应用 / API 服务 | m6i / m7g | 均衡的 CPU/内存 |
| 内存数据库（Redis/Memcached） | r6i / r7g | 高内存比 |
| CI/CD Runner | c6i / c7g | 计算密集 |
| 日志处理（Elasticsearch） | r6i + i4i | 内存 + 高 IOPS |
| 数据分析 | r6i / x2idn | 大内存 |
| ML 推理 | inf2 / g5 | 加速计算 |
| 开发测试环境 | t3 / t4g | 突发性能，低成本 |

---

### 2. AMI（Amazon Machine Image）

AMI 是 EC2 实例的模板，包含操作系统、应用软件和配置。

#### 2.1 AMI 类型

```
┌─────────────────────────────────────────────────────────────────┐
│                    AMI 类型                                      │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ AWS 官方 AMI │  │ Marketplace │  │ 自定义 AMI  │            │
│  │             │  │ AMI         │  │             │            │
│  │ Amazon      │  │ 第三方      │  │ 从实例创建   │            │
│  │ Linux 2023  │  │ 付费/免费   │  │ 从快照创建   │            │
│  │ Ubuntu      │  │ 安全扫描   │  │ 从 EBS 创建  │            │
│  │ RHEL        │  │ 合规认证   │  │             │            │
│  │ Windows     │  │             │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  AMI 存储在 S3（不可直接访问），通过 EBS 快照管理               │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 查找 AMI
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*" "Name=architecture,Values=x86_64" \
  --query "sort_by(Images, &CreationDate)[-5:].[ImageId,Name,CreationDate]" \
  --output table

# 查找最新 Amazon Linux 2023 AMI
aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" \
            "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text

# 创建自定义 AMI（从运行中的实例）
aws ec2 create-image \
  --instance-id i-0123456789abcdef0 \
  --name "sre-app-v2.1-$(date +%Y%m%d)" \
  --description "SRE App v2.1 with monitoring agent" \
  --no-reboot

# 列出自定义 AMI
aws ec2 describe-images \
  --owners self \
  --query "Images[*].[ImageId,Name,CreationDate,State]" \
  --output table

# 复制 AMI 到另一个 Region（灾备）
aws ec2 copy-image \
  --source-region us-east-1 \
  --source-image-id ami-0123456789abcdef0 \
  --name "sre-app-v2.1-eu-west" \
  --region eu-west-1

# 共享 AMI 给另一个账户
aws ec2 modify-image-attribute \
  --image-id ami-0123456789abcdef0 \
  --launch-permission "Add=[{UserId=222222222222}]"
```

#### 2.2 AMI 生命周期管理

```bash
#!/bin/bash
# cleanup-amis.sh — 保留最近 5 个 AMI，删除更旧的

KEEP=5
APP_NAME="sre-app"

AMIS=$(aws ec2 describe-images \
  --owners self \
  --filters "Name=name,Values=${APP_NAME}-*" \
  --query "sort_by(Images, &CreationDate)[].{Id:ImageId,Name:Name,Date:CreationDate}" \
  --output json)

COUNT=$(echo "$AMIS" | jq length)

if [ "$COUNT" -gt "$KEEP" ]; then
  DELETE_COUNT=$((COUNT - KEEP))
  echo "Found $COUNT AMIs, deleting $DELETE_COUNT oldest..."

  echo "$AMIS" | jq -r ".[0:$DELETE_COUNT][].Id" | while read ami_id; do
    echo "Deregistering AMI: $ami_id"
    aws ec2 deregister-image --image-id "$ami_id"

    SNAPSHOTS=$(aws ec2 describe-snapshots \
      --owner-ids self \
      --filters "Name=description,Values=*${ami_id}*" \
      --query "Snapshots[*].SnapshotId" \
      --output text)

    for snap in $SNAPSHOTS; do
      echo "Deleting snapshot: $snap"
      aws ec2 delete-snapshot --snapshot-id "$snap"
    done
  done
else
  echo "Only $COUNT AMIs found, nothing to delete."
fi
```

---

### 3. 安全组（Security Group）

安全组是 EC2 实例的虚拟防火墙，控制入站和出站流量。

#### 3.1 安全组 vs NACL

```
┌─────────────────────────────────────────────────────────────────┐
│              安全组 vs NACL 对比                                 │
│                                                                 │
│  安全组 (Security Group)           NACL (Network ACL)           │
│  ┌─────────────────────┐          ┌─────────────────────┐      │
│  │ 实例级别            │          │ 子网级别            │      │
│  │ 有状态              │          │ 无状态              │      │
│  │ 只支持 Allow        │          │ 支持 Allow 和 Deny  │      │
│  │ 所有规则同时评估    │          │ 规则按编号顺序评估  │      │
│  │ 返回流量自动允许    │          │ 需要显式允许返回流量│      │
│  │                    │          │                    │      │
│  │ 评估流程：          │          │ 评估流程：          │      │
│  │ 所有规则 → 合并    │          │ 按编号 → 第一条匹配│      │
│  │ → 有 Allow 即通过  │          │ → 执行并停止       │      │
│  └─────────────────────┘          └─────────────────────┘      │
│                                                                 │
│  最佳实践：两者配合使用，NACL 做粗粒度，安全组做细粒度          │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 安全组操作

```bash
# 创建安全组
aws ec2 create-security-group \
  --group-name sre-web-sg \
  --description "Security group for SRE web servers" \
  --vpc-id vpc-0123456789abcdef0

# 添加入站规则 — 允许 HTTP
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

# 添加入站规则 — 允许 HTTPS
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# 添加入站规则 — 允许 SSH（仅限跳板机安全组）
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 22 \
  --source-group sg-bastion01234567890

# 添加入站规则 — 允许来自另一个安全组的流量
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 8080 \
  --source-group sg-alb01234567890

# 使用 JSON 格式批量添加规则
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --ip-permissions '[
    {
      "IpProtocol": "tcp",
      "FromPort": 80,
      "ToPort": 80,
      "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTP from anywhere"}]
    },
    {
      "IpProtocol": "tcp",
      "FromPort": 443,
      "ToPort": 443,
      "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "HTTPS from anywhere"}]
    }
  ]'

# 查看安全组规则
aws ec2 describe-security-groups \
  --group-ids sg-0123456789abcdef0 \
  --query "SecurityGroups[*].IpPermissions" \
  --output json

# 删除安全组规则
aws ec2 revoke-security-group-ingress \
  --group-id sg-0123456789abcdef0 \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0

# 查找引用了特定安全组的资源
aws ec2 describe-network-interfaces \
  --filters "Name=group-id,Values=sg-0123456789abcdef0" \
  --query "NetworkInterfaces[*].[NetworkInterfaceId,Attachment.InstanceId,Status]"
```

---

### 4. 密钥对（Key Pair）

密钥对用于安全地 SSH 连接到 EC2 实例。

```bash
# 创建密钥对（密钥只在创建时显示一次）
aws ec2 create-key-pair \
  --key-name sre-key-2026 \
  --key-type ed25519 \
  --query "KeyMaterial" \
  --output text > ~/.ssh/sre-key-2026.pem

# 设置权限（必须是 400 或 600）
chmod 400 ~/.ssh/sre-key-2026.pem

# 列出密钥对
aws ec2 describe-key-pairs \
  --query "KeyPairs[*].[KeyName,KeyPairId,CreateTime]" \
  --output table

# 获取密钥对指纹（验证密钥）
aws ec2 describe-key-pairs \
  --key-names sre-key-2026 \
  --include-public-key \
  --query "KeyPairs[0].PublicKey"

# 删除密钥对
aws ec2 delete-key-pair --key-name sre-key-2026

# SSH 连接
ssh -i ~/.ssh/sre-key-2026.pem ec2-user@<public-ip>

# 使用 SSM Session Manager（推荐，无需开放 22 端口）
aws ssm start-session --target i-0123456789abcdef0
```

---

### 5. 用户数据（User Data）

User Data 是实例启动时自动执行的脚本，常用于初始化配置。

#### 5.1 基础用法

```bash
# 启动实例时传入 User Data
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t3.micro \
  --key-name sre-key-2026 \
  --security-group-ids sg-0123456789abcdef0 \
  --user-data file://userdata.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=sre-web-01}]'
```

```bash
#!/bin/bash
# userdata.sh — 完整的实例初始化脚本
set -euo pipefail

# 日志记录
exec > >(tee /var/log/user-data.log) 2>&1
echo "=== User Data Script Started at $(date) ==="

# 系统更新
dnf update -y

# 安装基础工具
dnf install -y \
  amazon-cloudwatch-agent \
  awscli \
  htop \
  curl \
  jq

# 安装 Docker
dnf install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# 配置 CloudWatch Agent
cat > /opt/aws/amazon-cloudwatch-agent/etc/config.json << 'EOF'
{
  "metrics": {
    "metrics_collected": {
      "mem": { "measurement": ["mem_used_percent"] },
      "disk": { "measurement": ["used_percent"], "resources": ["*"] }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "/ec2/sre-web",
            "log_stream_name": "{instance_id}/messages"
          }
        ]
      }
    }
  }
}
EOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json

# 从 S3 获取应用配置
aws s3 cp s3://sre-config-bucket/app-config.json /opt/app/config.json

# 部署应用
docker pull sre-registry.example.com/web-app:v2.1
docker run -d \
  --name web-app \
  --restart unless-stopped \
  -p 8080:8080 \
  -v /opt/app/config.json:/app/config.json \
  sre-registry.example.com/web-app:v2.1

echo "=== User Data Script Completed at $(date) ==="
```

#### 5.2 cloud-init 详解

```yaml
#cloud-config
# 使用 cloud-init 格式（更结构化）
# 注意：cloud-config 和 bash 脚本不能混用

# 主机名
hostname: sre-web-01

# 包管理
package_update: true
packages:
  - amazon-cloudwatch-agent
  - htop
  - curl
  - jq

# 写入文件
write_files:
  - path: /opt/app/config.json
    permissions: '0644'
    owner: root:root
    content: |
      {
        "environment": "production",
        "log_level": "info"
      }
  - path: /etc/sysctl.d/99-sre.conf
    content: |
      net.core.somaxconn = 65535
      net.ipv4.tcp_max_syn_backlog = 65535

# 运行命令
runcmd:
  - systemctl enable amazon-cloudwatch-agent
  - systemctl start amazon-cloudwatch-agent
  - sysctl --system
  - echo "Instance initialized" > /var/log/cloud-init-done
```

#### 5.3 查看 User Data 执行日志

```bash
# 从实例内部查看
cat /var/log/cloud-init-output.log
cat /var/log/user-data.log

# 从实例元数据获取 User Data
curl http://169.254.169.254/latest/user-data

# 检查 cloud-init 状态
cloud-init status
cloud-init status --wait  # 等待完成
```

---

### 6. 实例存储 vs EBS

#### 6.1 实例存储（Instance Store）

实例存储是直接附加在物理主机上的本地磁盘。

```
┌─────────────────────────────────────────────────────────────────┐
│              实例存储 vs EBS                                     │
│                                                                 │
│  实例存储 (Instance Store)          EBS (Elastic Block Store)    │
│  ┌─────────────────────┐          ┌─────────────────────┐      │
│  │ 物理主机本地磁盘    │          │ 网络附加存储        │      │
│  │ NVMe SSD            │          │ 独立于实例生命周期  │      │
│  │ 最高 3.3M IOPS      │          │ 可独立挂载/卸载     │      │
│  │ 实例停止=数据丢失   │          │ 支持快照备份        │      │
│  │ 无额外费用          │          │ 可跨 AZ 迁移        │      │
│  │ 不支持快照          │          │ 按容量+IOPS 收费    │      │
│  │                     │          │                     │      │
│  │ 适用：临时缓存      │          │ 适用：数据库/文件系统│      │
│  │ 临时文件/交换分区   │          │ 持久化数据          │      │
│  └─────────────────────┘          └─────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.2 EBS 卷类型详解

| 卷类型 | 用途 | 最大 IOPS | 最大吞吐 | 价格 |
|--------|------|-----------|----------|------|
| gp3 | 通用 SSD | 16,000 | 1,000 MB/s | 最低 |
| gp2 | 通用 SSD（旧） | 16,000 | 250 MB/s | 中等 |
| io2 Block Express | 高性能 SSD | 256,000 | 4,000 MB/s | 最高 |
| io2 | 高性能 SSD | 64,000 | 1,000 MB/s | 高 |
| st1 | 吞吐优化 HDD | 500 | 500 MB/s | 低 |
| sc1 | 冷存储 HDD | 250 | 250 MB/s | 最低 |

```bash
# 创建 EBS 卷
aws ec2 create-volume \
  --availability-zone us-east-1a \
  --size 100 \
  --volume-type gp3 \
  --iops 3000 \
  --throughput 125 \
  --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=app-data-vol}]'

# 挂载 EBS 卷到实例
aws ec2 attach-volume \
  --volume-id vol-0123456789abcdef0 \
  --instance-id i-0123456789abcdef0 \
  --device /dev/xvdf

# 在实例内部格式化和挂载
sudo mkfs -t xfs /dev/xvdf
sudo mkdir /data
sudo mount /dev/xvdf /data
echo '/dev/xvdf /data xfs defaults,nofail 0 2' | sudo tee -a /etc/fstab

# 创建 EBS 快照
aws ec2 create-snapshot \
  --volume-id vol-0123456789abcdef0 \
  --description "Daily backup $(date +%Y%m%d)" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=Name,Value=daily-backup}]'

# 修改 EBS 卷属性（在线扩容）
aws ec2 modify-volume \
  --volume-id vol-0123456789abcdef0 \
  --size 200 \
  --volume-type gp3 \
  --iops 6000

# 查看卷修改状态
aws ec2 describe-volumes-modifications \
  --volume-id vol-0123456789abcdef0

# 列出实例的所有卷
aws ec2 describe-volumes \
  --filters "Name=attachment.instance-id,Values=i-0123456789abcdef0" \
  --query "Volumes[*].[VolumeId,Size,VolumeType,State]" \
  --output table
```

#### 6.3 EBS 快照管理

```bash
#!/bin/bash
# ebs-snapshot-lifecycle.sh — 自动快照和清理

VOLUME_ID="vol-0123456789abcdef0"
RETENTION_DAYS=7

# 创建快照
SNAPSHOT_ID=$(aws ec2 create-snapshot \
  --volume-id "$VOLUME_ID" \
  --description "Automated backup $(date +%Y-%m-%d_%H:%M)" \
  --tag-specifications "ResourceType=snapshot,Tags=[{Key=Name,Value=auto-backup},{Key=VolumeId,Value=$VOLUME_ID}]" \
  --query "SnapshotId" \
  --output text)

echo "Created snapshot: $SNAPSHOT_ID"

# 等待快照完成
aws ec2 wait snapshot-completed --snapshot-ids "$SNAPSHOT_ID"

# 清理过期快照
CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%dT%H:%M:%S)

aws ec2 describe-snapshots \
  --owner-ids self \
  --filters "Name=tag:VolumeId,Values=$VOLUME_ID" \
  --query "Snapshots[?StartTime<='$CUTOFF_DATE'].[SnapshotId]" \
  --output text | while read snap_id; do
  echo "Deleting expired snapshot: $snap_id"
  aws ec2 delete-snapshot --snapshot-id "$snap_id"
done
```

---

### 7. 弹性 IP（Elastic IP）

弹性 IP 是静态的公有 IPv4 地址，可以动态地重新映射到不同实例。

```bash
# 分配弹性 IP
aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=web-eip}]'

# 关联到实例
aws ec2 associate-address \
  --instance-id i-0123456789abcdef0 \
  --allocation-id eipalloc-0123456789abcdef0

# 解除关联
aws ec2 disassociate-address \
  --association-id eipassoc-0123456789abcdef0

# 释放弹性 IP（不使用的 EIP 会产生费用）
aws ec2 release-address \
  --allocation-id eipalloc-0123456789abcdef0

# 查找未使用的弹性 IP
aws ec2 describe-addresses \
  --query "Addresses[?AssociationId==null].[PublicIp,AllocationId]" \
  --output table
```

**EIP 费用注意：** 分配了 EIP 但未关联到运行中的实例，按小时收费。SRE 应定期审计未使用的 EIP。

---

### 8. 费用优化策略

#### 8.1 购买选项对比

```
┌─────────────────────────────────────────────────────────────────┐
│                    EC2 费用优化策略                              │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ On-Demand    │  │ Reserved     │  │ Spot         │         │
│  │ 按需实例     │  │ 预留实例     │  │ 竞价实例     │         │
│  │              │  │              │  │              │         │
│  │ 无承诺       │  │ 1年或3年     │  │ 最高节省     │         │
│  │ 按秒计费     │  │ 节省最多72%  │  │ 90%          │         │
│  │ 随时启停     │  │ 可预付/无预付│  │ 可被回收     │         │
│  │              │  │              │  │ 2分钟通知    │         │
│  │ 适用：       │  │ 适用：       │  │ 适用：       │         │
│  │ 临时/开发    │  │ 稳定工作负载 │  │ 容错/批处理  │         │
│  │ 短期项目     │  │ 生产数据库   │  │ CI/CD       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Savings Plans（推荐）                                 │      │
│  │ - Compute SP: 跨 EC2/Fargate/Lambda 的统一折扣      │      │
│  │ - EC2 SP: 特定实例族的折扣                           │      │
│  │ - Machine Learning SP: SageMaker 等                  │      │
│  │ - 灵活度高于 Reserved Instance                       │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

#### 8.2 Spot 实例

```bash
# 查看 Spot 价格历史
aws ec2 describe-spot-price-history \
  --instance-types m6i.large \
  --product-descriptions "Linux/UNIX" \
  --start-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --query "SpotPriceHistory[*].[AvailabilityZone,SpotPrice]" \
  --output table

# 请求 Spot 实例
aws ec2 request-spot-instances \
  --spot-price "0.05" \
  --instance-count 1 \
  --type "one-time" \
  --launch-specification '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "m6i.large",
    "KeyName": "sre-key-2026",
    "SecurityGroupIds": ["sg-0123456789abcdef0"]
  }'

# 使用 Spot Fleet（推荐，更灵活）
aws ec2 create-spot-fleet \
  --spot-fleet-request-config '{
    "IamFleetRole": "arn:aws:iam::123456789012:role/aws-ec2-spot-fleet-tagging-role",
    "TargetCapacity": 3,
    "TerminateInstancesWithExpiration": true,
    "LaunchTemplateConfigs": [
      {
        "LaunchTemplateSpecification": {
          "LaunchTemplateId": "lt-0123456789abcdef0",
          "Version": "1"
        },
        "Overrides": [
          {"InstanceType": "m6i.large", "AvailabilityZone": "us-east-1a"},
          {"InstanceType": "m6i.large", "AvailabilityZone": "us-east-1b"},
          {"InstanceType": "m5.large", "AvailabilityZone": "us-east-1a"}
        ]
      }
    ],
    "AllocationStrategy": "capacityOptimized"
  }'
```

#### 8.3 Reserved Instance

```bash
# 查看预留实例推荐
aws ec2 get-reservations-purchase-recommendation \
  --service-code AmazonEC2 \
  --term-years ONE_YEAR \
  --payment-option NO_UPFRONT \
  --lookback-period-in-days SIXTY_DAYS

# 查看现有预留实例
aws ec2 describe-reserved-instances \
  --query "ReservedInstances[*].[ReservedInstancesId,InstanceType,InstanceCount,End,State]" \
  --output table
```

#### 8.4 成本分析

```bash
# 获取月度成本
aws ce get-cost-and-usage \
  --time-period Start=2026-04-01,End=2026-04-30 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query "ResultsByTime[*].Groups[*].[Keys[0],Metrics.UnblendedCost.Amount]" \
  --output table

# 获取 EC2 按实例类型的成本
aws ce get-cost-and-usage \
  --time-period Start=2026-04-01,End=2026-04-30 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Elastic Compute Cloud - Compute"]}}' \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE \
  --query "ResultsByTime[*].Groups[*].[Keys[0],Metrics.UnblendedCost.Amount]" \
  --output table
```

---

### 9. 实例生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                    EC2 实例生命周期                              │
│                                                                 │
│  ┌─────────┐   Launch   ┌─────────┐                            │
│  │ Pending │ ──────────▶│ Running │                            │
│  └─────────┘            └────┬────┘                            │
│                              │                                  │
│                    ┌─────────┼─────────┐                        │
│                    │         │         │                        │
│                    ▼         ▼         ▼                        │
│              ┌─────────┐ ┌────────┐ ┌──────────┐              │
│              │ Stop    │ │ Reboot │ │ Terminate│              │
│              │ (保留   │ │ (保持  │ │ (删除    │              │
│              │  EBS)   │ │  运行) │ │  所有)   │              │
│              └────┬────┘ └────────┘ └──────────┘              │
│                   │                                            │
│                   ▼                                            │
│              ┌─────────┐                                       │
│              │Stopped  │                                       │
│              │(EBS保留)│                                       │
│              └────┬────┘                                       │
│                   │                                            │
│                   ▼                                            │
│              ┌─────────┐                                       │
│              │ Start   │ ─────▶ Running                        │
│              └─────────┘                                       │
│                                                                 │
│  注意：                                                          │
│  - Stop 后实例存储数据丢失                                      │
│  - Stop 后公有 IP 会释放（EIP 保留）                            │
│  - Terminate 后 EBS 默认删除（可设 DeleteOnTermination=false）  │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 启动实例
aws ec2 run-instances \
  --image-id ami-0abcdef1234567890 \
  --instance-type t3.medium \
  --key-name sre-key-2026 \
  --security-group-ids sg-0123456789abcdef0 \
  --subnet-id subnet-0123456789abcdef0 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=sre-web-01}]'

# 停止实例（保留 EBS）
aws ec2 stop-instances --instance-ids i-0123456789abcdef0

# 启动已停止的实例
aws ec2 start-instances --instance-ids i-0123456789abcdef0

# 重启实例
aws ec2 reboot-instances --instance-ids i-0123456789abcdef0

# 终止实例
aws ec2 terminate-instances --instance-ids i-0123456789abcdef0

# 查看实例状态
aws ec2 describe-instance-status \
  --instance-ids i-0123456789abcdef0 \
  --query "InstanceStatuses[*].[InstanceStatus.Status,SystemStatus.Status]"

# 启用终止保护
aws ec2 modify-instance-attribute \
  --instance-id i-0123456789abcdef0 \
  --disable-api-termination

# 查看实例元数据
curl http://169.254.169.254/latest/meta-data/
curl http://169.254.169.254/latest/meta-data/instance-id
curl http://169.254.169.254/latest/meta-data/instance-type
curl http://169.254.169.254/latest/meta-data/public-ipv4
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

---

### 10. SRE 实战案例

#### 案例 1：EC2 实例启动后应用无法访问

**故障现象：** 新启动的 EC2 实例上应用无法访问，安全组和 NACL 都已配置。

```bash
# 1. 检查实例状态
aws ec2 describe-instance-status \
  --instance-ids i-0123456789abcdef0

# 2. 检查 User Data 执行日志（通过 SSM）
aws ssm start-session --target i-0123456789abcdef0
cat /var/log/cloud-init-output.log | tail -50

# 3. 检查应用进程
systemctl status my-app
docker ps

# 4. 检查端口监听
ss -tlnp | grep 8080

# 5. 检查实例元数据服务
curl -s http://169.254.169.254/latest/meta-data/instance-id

# 根因：User Data 脚本中 Docker 拉取镜像超时，应用未启动
# 解决方案：增加 User Data 超时重试逻辑
```

#### 案例 2：EBS 卷空间不足导致数据库崩溃

```bash
# 1. 检查磁盘使用率
df -h /data

# 2. 查找大文件
du -sh /data/* | sort -rh | head -10

# 3. 清理日志
find /data/logs -name "*.log" -mtime +7 -delete

# 4. 在线扩容 EBS 卷
aws ec2 modify-volume \
  --volume-id vol-0123456789abcdef0 \
  --size 200

# 5. 在实例内扩展文件系统
# 对于 XFS:
sudo xfs_growfs /data
# 对于 ext4:
sudo resize2fs /dev/xvdf

# 6. 设置 CloudWatch 告警监控磁盘使用率
aws cloudwatch put-metric-alarm \
  --alarm-name "EBS-DiskUsage-High" \
  --metric-name "used_percent" \
  --namespace "CWAgent" \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:sre-alerts"
```

#### 案例 3：Spot 实例被回收

```bash
# 1. 检查 Spot 实例中断通知（2分钟前通知）
curl -s http://169.254.169.254/latest/meta-data/spot/instance-action

# 2. 检查 Spot Fleet 状态
aws ec2 describe-spot-fleet-requests \
  --spot-fleet-request-ids sfr-xxxxx

# 3. 查看 Spot 中断历史
aws ec2 describe-spot-instance-requests \
  --filters "Name=state,Values=closed" \
  --query "SpotInstanceRequests[*].[SpotInstanceRequestId,Status.Code,CreateTime]"

# 4. 实现优雅关闭脚本
cat > /etc/spot-interruption-handler.sh << 'EOF'
#!/bin/bash
while true; do
  ACTION=$(curl -s -o /dev/null -w "%{http_code}" http://169.254.169.254/latest/meta-data/spot/instance-action)
  if [ "$ACTION" -eq 200 ]; then
    echo "Spot interruption detected, gracefully shutting down..."
    aws elbv2 deregister-targets \
      --target-group-arn arn:aws:... \
      --targets Id=i-$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
    sleep 30
    systemctl stop my-app
    exit 0
  fi
  sleep 5
done
EOF
chmod +x /etc/spot-interruption-handler.sh
```

---

## 💻 实战练习

### 练习 1：基础操作 — 启动和管理 EC2 实例

```bash
# 步骤 1: 创建安全组
SG_ID=$(aws ec2 create-security-group \
  --group-name sre-exercise-sg \
  --description "Exercise security group" \
  --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

# 步骤 2: 创建密钥对
aws ec2 create-key-pair \
  --key-name sre-exercise-key \
  --key-type ed25519 \
  --query "KeyMaterial" --output text > ~/.ssh/sre-exercise-key.pem
chmod 400 ~/.ssh/sre-exercise-key.pem

# 步骤 3: 获取最新 Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" \
  --output text)

# 步骤 4: 启动实例
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type t3.micro \
  --key-name sre-exercise-key \
  --security-group-ids "$SG_ID" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=sre-exercise}]' \
  --query "Instances[0].InstanceId" --output text)

# 步骤 5: 等待实例运行
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

# 步骤 6: 获取公有 IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query "Reservations[0].Instances[0].PublicIpAddress" --output text)

echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"

# 步骤 7: SSH 连接测试
ssh -i ~/.ssh/sre-exercise-key.pem -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" \
  "cat /etc/os-release && uname -r"

# 步骤 8: 清理
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID"
aws ec2 wait instance-terminated --instance-ids "$INSTANCE_ID"
aws ec2 delete-key-pair --key-name sre-exercise-key
aws ec2 delete-security-group --group-id "$SG_ID"
rm ~/.ssh/sre-exercise-key.pem
```

### 练习 2：进阶场景 — 使用 User Data 自动化部署

```bash
# 步骤 1: 创建 User Data 脚本
cat > /tmp/userdata.sh << 'USERDATA'
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/userdata.log) 2>&1

echo "=== Starting initialization ==="
dnf install -y nginx

cat > /usr/share/nginx/html/index.html << 'HTML'
<!DOCTYPE html>
<html>
<head><title>SRE Exercise</title></head>
<body>
<h1>Hello from EC2 User Data!</h1>
<p>Instance ID: <span id="instance-id">loading...</span></p>
<p>Availability Zone: <span id="az">loading...</span></p>
<script>
fetch('http://169.254.169.254/latest/meta-data/instance-id')
  .then(r => r.text()).then(d => document.getElementById('instance-id').textContent = d);
fetch('http://169.254.169.254/latest/meta-data/placement/availability-zone')
  .then(r => r.text()).then(d => document.getElementById('az').textContent = d);
</script>
</body>
</html>
HTML

systemctl enable nginx
systemctl start nginx
echo "=== Initialization complete ==="
USERDATA

# 步骤 2: 启动实例
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text)

aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type t3.micro \
  --key-name sre-exercise-key \
  --security-group-ids "$SG_ID" \
  --user-data file:///tmp/userdata.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=sre-userdata-test}]'
```

### 练习 3：故障排查挑战 — EBS 卷挂载问题

**场景：** 将一个 EBS 卷从实例 A 分离后挂载到实例 B，但实例 B 看不到设备。

```bash
# 排查步骤
# 1. 检查卷状态
aws ec2 describe-volumes --volume-ids vol-xxxxx \
  --query "Volumes[0].{State:State,Attachments:Attachments}"

# 2. 确认卷已完全分离
aws ec2 wait volume-available --volume-ids vol-xxxxx

# 3. 确认实例和卷在同一 AZ
aws ec2 describe-volumes --volume-ids vol-xxxxx \
  --query "Volumes[0].AvailabilityZone"
aws ec2 describe-instances --instance-ids i-yyyyy \
  --query "Reservations[0].Instances[0].Placement.AvailabilityZone"

# 4. 检查设备名是否冲突
aws ec2 describe-instances --instance-ids i-yyyyy \
  --query "Reservations[0].Instances[0].BlockDeviceMappings"

# 5. 在实例内检查
lsblk
dmesg | grep -i "xvdf\|nvme"

# 答案：常见原因是卷未完全分离就开始附加，或设备名冲突
```

---

## 🎯 面试题精选

### 题目 1：EC2 实例停止和终止的区别？

**答：**
- **Stop**：实例停止运行，EBS 根卷保留，实例存储数据丢失，公有 IP 释放（EIP 保留），不收取计算费用但收取 EBS 存储费用
- **Terminate**：实例删除，默认删除 EBS 根卷（可设 DeleteOnTermination=false 保留），释放所有资源

### 题目 2：gp2 和 gp3 的区别？为什么推荐 gp3？

**答：**
- gp2：IOPS 与容量挂钩（每 GB 3 IOPS，最低 100，最高 16000），吞吐最高 250 MB/s
- gp3：IOPS 和吞吐独立配置（基准 3000 IOPS / 125 MB/s，可额外购买），价格低 20%

推荐 gp3 的原因：成本更低，性能与容量解耦，更灵活的性能配置。

### 题目 3：什么是 Nitro Enclave？

**答：** Nitro Enclave 是 AWS 提供的隔离计算环境，用于处理高度敏感数据。特点：无持久存储、无网络访问、无管理员访问，通过加密通道与父实例通信，适用于密钥管理、PII 处理等场景。

### 题目 4：Spot 实例被中断时如何保证应用可用性？

**答：**
1. 使用多种实例类型和 AZ（增加容量池）
2. 实现检查点机制（定期保存状态到 S3）
3. 监听 2 分钟中断通知，优雅关闭
4. 使用 Spot Fleet 管理多实例
5. 关键服务使用 On-Demand + Spot 混合
6. 使用 ALB + 健康检查自动剔除中断实例

### 题目 5：EBS 快照是增量的还是全量的？

**答：** EBS 快照是增量的。第一个快照是全量的，后续快照只保存自上次快照以来变化的块。删除任何一个快照不影响其他快照。

### 题目 6：如何实现 EC2 实例的零停机维护？

**答：** 使用 Auto Scaling Group + ALB，创建新的 Launch Template 版本，执行 Instance Refresh（逐步替换实例）。或者手动创建新实例 -> 注册到 ALB -> 验证健康 -> 注销旧实例。

### 题目 7：Placement Group 的类型和使用场景？

**答：**
- **Cluster**：同一 AZ 的低延迟网络，适合 HPC
- **Spread**：不同硬件，最多 7 个实例/AZ，适合关键应用
- **Partition**：逻辑分区，每个分区在不同硬件，适合 HDFS/HBase

### 题目 8：如何从实例存储的实例中恢复数据？

**答：** 实例存储的数据无法直接恢复。预防措施：不要在实例存储上保存唯一数据，使用 RAID 1 镜像到 EBS，定期同步到 S3，使用 EBS 作为主存储。

---

## 📚 深入阅读

- [EC2 实例类型](https://aws.amazon.com/ec2/instance-types/)
- [EBS 卷类型](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-volume-types.html)
- [EC2 Spot 实例](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html)
- [EC2 最佳实践](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/best-practices-for-EC2.html)
- [Savings Plans](https://aws.amazon.com/savingsplans/)

---

## ✅ 自检清单

- [ ] 能够根据工作负载选择合适的实例类型
- [ ] 能够创建和管理自定义 AMI
- [ ] 能够配置安全组规则（允许/拒绝入站和出站）
- [ ] 能够创建密钥对并安全地 SSH 连接
- [ ] 能够编写 User Data 脚本自动化实例初始化
- [ ] 能够区分 EBS 卷类型并根据场景选择
- [ ] 能够在线扩容 EBS 卷
- [ ] 能够管理弹性 IP
- [ ] 理解 Spot / Reserved / On-Demand 的成本差异
- [ ] 能够实现 Spot 实例的优雅中断处理
- [ ] 能够排查 EC2 常见故障（启动失败、网络不通、磁盘满）
