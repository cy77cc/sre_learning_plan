# Day 109: RDS 数据库

> 📅 日期：2026-05-08
> 📖 学习主题：RDS 引擎选择、多可用区、读副本、自动备份、参数组、安全、Performance Insights、Aurora
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 105（AWS 简介与账户管理）、Day 107（VPC 网络）

## 🎯 学习目标

- 理解 RDS 支持的数据库引擎及其适用场景
- 掌握多可用区部署和读副本的配置与区别
- 能够配置自动备份、参数组和安全组
- 掌握 Performance Insights 进行数据库性能分析
- 理解 Aurora 与标准 RDS 的区别和优势

---

## 📖 核心知识点

### 1. RDS 引擎选择

```
┌─────────────────────────────────────────────────────────────────┐
│                    RDS 支持的引擎                                │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ MySQL       │  │ PostgreSQL  │  │ MariaDB     │            │
│  │             │  │             │  │             │            │
│  │ 最流行      │  │ 功能丰富    │  │ MySQL 兼容  │            │
│  │ 简单易用    │  │ JSON/扩展   │  │ 开源        │            │
│  │ 版本 5.7/8  │  │ 版本 12~16  │  │ 版本 10.x   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Oracle      │  │ SQL Server  │  │ Aurora      │            │
│  │             │  │             │  │ (推荐)       │            │
│  │ 企业级      │  │ Windows 生态│  │ MySQL/PG兼容│            │
│  │ 按License  │  │ 按License  │  │ 5x 性能提升 │            │
│  │ BYOL/按需  │  │ Express 免费│  │ 自动扩展    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  选型建议：                                                      │
│  - 新项目首选 Aurora（MySQL/PG 兼容）                           │
│  - 已有 MySQL 迁移 → RDS MySQL 或 Aurora MySQL                  │
│  - 需要高级功能 → PostgreSQL 或 Aurora PostgreSQL                │
│  - Oracle/SQL Server 依赖 → 对应 RDS 引擎                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 创建 RDS 实例

```bash
# 创建 RDS MySQL 实例
aws rds create-db-instance \
  --db-instance-identifier sre-app-db \
  --db-instance-class db.t3.medium \
  --engine mysql \
  --engine-version 8.0.35 \
  --master-username admin \
  --master-user-password 'Str0ng!DB@Pass2026' \
  --allocated-storage 100 \
  --max-allocated-storage 500 \
  --storage-type gp3 \
  --storage-encrypted \
  --db-subnet-group-name sre-db-subnet-group \
  --vpc-security-group-ids sg-db-sg \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:30-sun:05:30" \
  --multi-az \
  --auto-minor-version-upgrade \
  --deletion-protection \
  --enable-performance-insights \
  --performance-insights-retention-period 731 \
  --tags Key=Environment,Value=production Key=Team,Value=sre

# 查看实例状态
aws rds describe-db-instances \
  --db-instance-identifier sre-app-db \
  --query "DBInstances[0].{Status:DBInstanceStatus,Endpoint:Endpoint.Address,Port:Endpoint.Port}"

# 连接数据库（从 EC2 实例）
mysql -h sre-app-db.xxxx.us-east-1.rds.amazonaws.com -u admin -p

# 修改实例（增加存储）
aws rds modify-db-instance \
  --db-instance-identifier sre-app-db \
  --allocated-storage 200 \
  --apply-immediately

# 创建只读副本
aws rds create-db-instance-read-replica \
  --db-instance-identifier sre-app-db-read-1 \
  --source-db-instance-identifier sre-app-db \
  --db-instance-class db.t3.medium \
  --availability-zone us-east-1b

# 删除实例（创建最终快照）
aws rds delete-db-instance \
  --db-instance-identifier sre-app-db \
  --final-db-snapshot-identifier sre-app-db-final-$(date +%Y%m%d) \
  --delete-automated-backups
```

---

### 3. 多可用区（Multi-AZ）

```
┌─────────────────────────────────────────────────────────────────┐
│                    RDS Multi-AZ 架构                             │
│                                                                 │
│  us-east-1a                         us-east-1b                  │
│  ┌─────────────────┐               ┌─────────────────┐         │
│  │ 主实例 (Primary)│    同步复制    │ 备用实例 (Standby)│        │
│  │                 │ ─────────────▶│                 │         │
│  │ ┌─────────────┐ │               │ ┌─────────────┐ │         │
│  │ │ MySQL 8.0   │ │               │ │ MySQL 8.0   │ │         │
│  │ │             │ │               │ │ (热备)       │ │         │
│  │ └─────────────┘ │               │ └─────────────┘ │         │
│  │                 │               │                 │         │
│  │ EBS Volume      │               │ EBS Volume      │         │
│  └────────┬────────┘               └─────────────────┘         │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐                                            │
│  │ DNS Endpoint    │                                            │
│  │ sre-app-db.xxx  │                                            │
│  │ .rds.amazonaws  │                                            │
│  │ .com            │                                            │
│  └─────────────────┘                                            │
│                                                                 │
│  故障切换过程（自动，60-120 秒）：                               │
│  1. 主实例不可用                                                │
│  2. DNS 自动切换到备用实例                                      │
│  3. 备用实例提升为主实例                                        │
│  4. 应用重连（需要处理连接中断）                                │
│                                                                 │
│  注意：                                                          │
│  - 同步复制，零数据丢失                                         │
│  - 备用实例不处理读请求                                         │
│  - DNS 切换，应用需要重连                                       │
│  - 费用约为单实例的 2 倍                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4. 读副本（Read Replica）

```
┌─────────────────────────────────────────────────────────────────┐
│                    RDS Read Replica 架构                         │
│                                                                 │
│  us-east-1a                         us-east-1b                  │
│  ┌─────────────────┐               ┌─────────────────┐         │
│  │ 主实例 (Primary)│    异步复制    │ 读副本 1        │         │
│  │                 │ ─────────────▶│                 │         │
│  │ 写入 + 读取     │               │ 仅读取           │         │
│  └────────┬────────┘               └─────────────────┘         │
│           │                                                     │
│           │               us-east-1c                            │
│           │               ┌─────────────────┐                   │
│           │  异步复制     │ 读副本 2        │                   │
│           ├──────────────▶│                 │                   │
│           │               │ 仅读取           │                   │
│           │               └─────────────────┘                   │
│           │                                                     │
│           │               eu-west-1a (跨 Region)                │
│           │               ┌─────────────────┐                   │
│           │  异步复制     │ 读副本 3        │                   │
│           └──────────────▶│                 │                   │
│                           │ 仅读取           │                   │
│                           └─────────────────┘                   │
│                                                                 │
│  读副本 vs Multi-AZ：                                           │
│  ┌────────────────┬────────────────┬────────────────┐          │
│  │ 特性           │ Multi-AZ       │ Read Replica   │          │
│  ├────────────────┼────────────────┼────────────────┤          │
│  │ 复制方式       │ 同步           │ 异步           │          │
│  │ 用途           │ 高可用         │ 读扩展         │          │
│  │ 读请求         │ 不处理         │ 处理           │          │
│  │ 跨 Region     │ 不支持         │ 支持           │          │
│  │ 自动故障切换   │ 是             │ 手动提升       │          │
│  │ 数据延迟       │ 零             │ 秒级           │          │
│  └────────────────┴────────────────┴────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建读副本
aws rds create-db-instance-read-replica \
  --db-instance-identifier sre-app-db-read-1 \
  --source-db-instance-identifier sre-app-db \
  --db-instance-class db.r6g.large \
  --availability-zone us-east-1b

# 跨 Region 读副本
aws rds create-db-instance-read-replica \
  --db-instance-identifier sre-app-db-eu-read \
  --source-db-instance-identifier sre-app-db \
  --source-region us-east-1 \
  --region eu-west-1

# 手动提升读副本为独立实例（断开与主实例的关系）
aws rds promote-read-replica \
  --db-instance-identifier sre-app-db-read-1

# 监控复制延迟
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=sre-app-db-read-1 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average Maximum
```

---

### 5. 自动备份与恢复

```bash
# 查看自动备份
aws rds describe-db-automated-backups \
  --db-instance-identifier sre-app-db \
  --query "DBAutomatedBackups[*].[DBBackupResourceArn,RestorableTime,BackupRetentionPeriod]"

# 手动创建快照
aws rds create-db-snapshot \
  --db-instance-identifier sre-app-db \
  --db-snapshot-identifier sre-app-db-manual-$(date +%Y%m%d)

# 从快照恢复（创建新实例）
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier sre-app-db-restored \
  --db-snapshot-identifier sre-app-db-manual-20260508 \
  --db-instance-class db.t3.medium \
  --multi-az

# 恢复到指定时间点（PITR）
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier sre-app-db \
  --target-db-instance-identifier sre-app-db-pitr \
  --restore-time "2026-05-08T10:30:00Z" \
  --db-instance-class db.t3.medium

# 复制快照到另一个 Region（灾备）
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:123456789012:snapshot:sre-app-db-manual-20260508 \
  --target-db-snapshot-identifier sre-app-db-manual-20260508-eu \
  --region eu-west-1

# 共享快照给另一个账户
aws rds modify-db-snapshot-attribute \
  --db-snapshot-identifier sre-app-db-manual-20260508 \
  --attribute-name restore \
  --values-to-add '{"222222222222"}'
```

---

### 6. 参数组

参数组控制数据库引擎的配置参数。

```bash
# 创建参数组
aws rds create-db-parameter-group \
  --db-parameter-group-family mysql8.0 \
  --db-parameter-group-name sre-mysql8-custom \
  --description "SRE MySQL 8.0 custom parameters"

# 修改参数
aws rds modify-db-parameter-group \
  --db-parameter-group-name sre-mysql8-custom \
  --parameters \
    "ParameterName=slow_query_log,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=long_query_time,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=log_output,ParameterValue=FILE,ApplyMethod=immediate" \
    "ParameterName=max_connections,ParameterValue=500,ApplyMethod=immediate" \
    "ParameterName=innodb_buffer_pool_size,ParameterValue='{DBInstanceClassMemory*3/4}',ApplyMethod=pending-reboot"

# 应用参数组到实例
aws rds modify-db-instance \
  --db-instance-identifier sre-app-db \
  --db-parameter-group-name sre-mysql8-custom \
  --apply-immediately

# 查看参数
aws rds describe-db-parameters \
  --db-parameter-group-name sre-mysql8-custom \
  --query "Parameters[?ParameterName=='slow_query_log']"

# 查看引擎默认参数
aws rds describe-engine-default-parameters \
  --db-parameter-group-family mysql8.0 \
  --query "EngineDefaults.Parameters[?IsModifiable==\`true\`].[ParameterName,Description]" \
  --output table
```

**常用 MySQL 参数优化：**

| 参数 | 默认值 | 推荐值 | 说明 |
|------|--------|--------|------|
| slow_query_log | 0 | 1 | 启用慢查询日志 |
| long_query_time | 10 | 1 | 慢查询阈值（秒） |
| max_connections | 151 | 500-1000 | 最大连接数 |
| innodb_buffer_pool_size | 128M | 实例内存 75% | InnoDB 缓冲池 |
| innodb_log_file_size | 48M | 256M | 重做日志大小 |
| innodb_flush_log_at_trx_commit | 1 | 1（生产）/ 2（性能） | 事务提交刷盘策略 |
| character_set_server | latin1 | utf8mb4 | 字符集 |

---

### 7. 安全配置

```
┌─────────────────────────────────────────────────────────────────┐
│                    RDS 安全模型                                  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  网络层                                                     │ │
│  │  - VPC 私有子网部署                                         │ │
│  │  - 安全组限制访问来源                                       │ │
│  │  - NACL 子网级控制                                          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  认证层                                                     │ │
│  │  - 主用户名/密码                                            │ │
│  │  - IAM 数据库认证（MySQL/PG）                              │ │
│  │  - Kerberos 认证（MySQL）                                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  加密层                                                     │ │
│  │  - 静态加密（KMS）                                          │ │
│  │  - 传输加密（SSL/TLS）                                      │ │
│  │  - 自定义 KMS Key                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  审计层                                                     │ │
│  │  - CloudTrail API 审计                                      │ │
│  │  - 数据库原生日志                                           │ │
│  │  - Performance Insights                                     │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建数据库子网组
aws rds create-db-subnet-group \
  --db-subnet-group-name sre-db-subnet-group \
  --db-subnet-group-description "SRE DB subnet group" \
  --subnet-ids subnet-private-1a subnet-private-1b

# 创建数据库安全组
aws ec2 create-security-group \
  --group-name sre-db-sg \
  --description "RDS security group" \
  --vpc-id vpc-0123456789abcdef0

# 只允许应用安全组访问 3306 端口
aws ec2 authorize-security-group-ingress \
  --group-id sg-db-sg \
  --protocol tcp \
  --port 3306 \
  --source-group sg-app-sg

# 启用 IAM 数据库认证
aws rds modify-db-instance \
  --db-instance-identifier sre-app-db \
  --enable-iam-database-authentication \
  --apply-immediately

# 创建数据库用户（使用 IAM 认证）
# 在 MySQL 中执行：
# CREATE USER 'app_user' IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';
# GRANT SELECT, INSERT, UPDATE ON mydb.* TO 'app_user';

# 使用 IAM Token 连接
RDS_HOST="sre-app-db.xxxx.us-east-1.rds.amazonaws.com"
TOKEN=$(aws rds generate-db-auth-token \
  --hostname "$RDS_HOST" \
  --port 3306 \
  --username app_user)

mysql --host="$RDS_HOST" --user=app_user --password="$TOKEN" --ssl-mode=REQUIRED

# 强制 SSL 连接
# 在参数组中设置：
# require_secure_transport = ON
```

---

### 8. Performance Insights

Performance Insights 帮助分析数据库负载和性能瓶颈。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Performance Insights                          │
│                                                                 │
│  Database Load (DB Load)                                        │
│  ▲                                                              │
│  │     ┌───┐                                                   │
│  │     │CPU│  ┌──────┐                                         │
│  │     │   │  │Wait  │  ┌───┐                                  │
│  │ ┌───│   │  │Event │  │CPU│                                  │
│  │ │CPU│   │  │      │  │   │                                  │
│  │ │   │   │  │      │  │   │                                  │
│  └─┴───┴───┴──┴──────┴──┴───┴──────────────────────▶ Time     │
│                                                                 │
│  Top SQL Queries：                                              │
│  1. SELECT * FROM orders WHERE...    (45% DB Load)             │
│  2. INSERT INTO logs VALUES...       (23% DB Load)             │
│  3. UPDATE users SET last_login...   (12% DB Load)             │
│                                                                 │
│  Wait Events：                                                  │
│  1. CPU (40%)                                                   │
│  2. io/innodb/innodb_data_file (25%)                           │
│  3. synch/mutex/innodb/buf_dblwr (15%)                         │
│                                                                 │
│  关键指标：                                                      │
│  - DB Load: 数据库当前负载（vCPU 数）                          │
│  - DB Load by Wait: 按等待事件分类的负载                       │
│  - Top SQL: 消耗最多资源的查询                                  │
│  - Top Hosts/Users: 消耗最多资源的来源                         │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 启用 Performance Insights
aws rds modify-db-instance \
  --db-instance-identifier sre-app-db \
  --enable-performance-insights \
  --performance-insights-retention-period 731 \
  --performance-insights-kms-key-id alias/rds-pi-key \
  --apply-immediately

# 查询 Performance Insights 数据（通过 CLI）
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier db-xxxxx \
  --metric-queries '[
    {
      "Metric": "db.load.avg",
      "GroupBy": {"Group": "db.sql", "Dimensions": ["db.sql.id"], "Limit": 10}
    }
  ]' \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period-in-seconds 300

# 查看等待事件
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier db-xxxxx \
  --metric-queries '[
    {
      "Metric": "db.load.avg",
      "GroupBy": {"Group": "db.wait_event", "Dimensions": ["db.wait_event.name"], "Limit": 10}
    }
  ]' \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period-in-seconds 300
```

---

### 9. Aurora

Aurora 是 AWS 自研的云原生数据库，兼容 MySQL 和 PostgreSQL。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Aurora 架构                                   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Aurora Cluster                                            │ │
│  │                                                            │ │
│  │  ┌──────────────────────────────────────────────────────┐ │ │
│  │  │  共享存储层（6 副本，跨 3 AZ）                        │ │ │
│  │  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │ │ │
│  │  │  │ AZ-a│ │ AZ-a│ │ AZ-b│ │ AZ-b│ │ AZ-c│ │ AZ-c│  │ │ │
│  │  │  │  S  │ │  S  │ │  S  │ │  S  │ │  S  │ │  S  │  │ │ │
│  │  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘  │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │                                                            │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │ │
│  │  │ Writer      │  │ Reader 1    │  │ Reader 2    │       │ │
│  │  │ (Primary)   │  │ (Replica)   │  │ (Replica)   │       │ │
│  │  │ us-east-1a  │  │ us-east-1b  │  │ us-east-1c  │       │ │
│  │  │             │  │             │  │             │       │ │
│  │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │       │ │
│  │  │ │ DB      │ │  │ │ DB      │ │  │ │ DB      │ │       │ │
│  │  │ │ Engine  │ │  │ │ Engine  │ │  │ │ Engine  │ │       │ │
│  │  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │       │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │ │
│  │                                                            │ │
│  │  Endpoint:                                                  │ │
│  │  Cluster Endpoint (Writer): sre-cluster.cluster-xxx.rds    │ │
│  │  Reader Endpoint:           sre-cluster.cluster-ro-xxx.rds │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Aurora vs RDS MySQL：                                           │
│  ┌────────────────┬────────────────┬────────────────┐          │
│  │ 特性           │ RDS MySQL      │ Aurora MySQL   │          │
│  ├────────────────┼────────────────┼────────────────┤          │
│  │ 性能           │ 基准           │ 5x 提升        │          │
│  │ 存储扩展       │ 手动           │ 自动 (128TB)   │          │
│  │ 复制延迟       │ 秒级           │ 毫秒级         │          │
│  │ 故障切换       │ 60-120 秒      │ < 30 秒        │          │
│  │ 读副本         │ 最多 15 个     │ 最多 15 个     │          │
│  │ 存储费用       │ 按预分配       │ 按实际使用     │          │
│  │ Serverless     │ 不支持         │ 支持 (v2)      │          │
│  └────────────────┴────────────────┴────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

```bash
# 创建 Aurora MySQL 集群
aws rds create-db-cluster \
  --db-cluster-identifier sre-aurora-cluster \
  --engine aurora-mysql \
  --engine-version 8.0.mysql_aurora.3.07.0 \
  --master-username admin \
  --master-user-password 'Str0ng!DB@Pass2026' \
  --db-subnet-group-name sre-db-subnet-group \
  --vpc-security-group-ids sg-db-sg \
  --storage-encrypted \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00"

# 创建 Writer 实例
aws rds create-db-instance \
  --db-instance-identifier sre-aurora-writer \
  --db-cluster-identifier sre-aurora-cluster \
  --db-instance-class db.r6g.large \
  --engine aurora-mysql

# 创建 Reader 实例
aws rds create-db-instance \
  --db-instance-identifier sre-aurora-reader-1 \
  --db-cluster-identifier sre-aurora-cluster \
  --db-instance-class db.r6g.large \
  --engine aurora-mysql \
  --availability-zone us-east-1b

# 查看集群端点
aws rds describe-db-clusters \
  --db-cluster-identifier sre-aurora-cluster \
  --query "DBClusters[0].{Endpoint:Endpoint,ReaderEndpoint:ReaderEndpoint}"

# Aurora Serverless v2
aws rds create-db-cluster \
  --db-cluster-identifier sre-aurora-serverless \
  --engine aurora-mysql \
  --engine-version 8.0.mysql_aurora.3.07.0 \
  --master-username admin \
  --master-user-password 'Str0ng!DB@Pass2026' \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16

aws rds create-db-instance \
  --db-instance-identifier sre-aurora-serverless-writer \
  --db-cluster-identifier sre-aurora-serverless \
  --db-instance-class db.serverless \
  --engine aurora-mysql
```

---

### 10. SRE 实战案例

#### 案例 1：RDS 存储空间不足

```bash
# 1. 检查存储使用
aws rds describe-db-instances \
  --db-instance-identifier sre-app-db \
  --query "DBInstances[0].{Allocated:AllocatedStorage,Free:FreeStorageSpace,Max:MaxAllocatedStorage}"

# 2. 检查 CloudWatch 指标
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=sre-app-db \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Minimum

# 3. 检查哪些表占用空间最多
# 连接到数据库执行：
# SELECT table_schema, table_name, 
#   ROUND(data_length/1024/1024, 2) AS data_mb,
#   ROUND(index_length/1024/1024, 2) AS index_mb
# FROM information_schema.tables
# ORDER BY data_length DESC LIMIT 20;

# 4. 清理过期数据
# DELETE FROM logs WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

# 5. 启用自动扩展存储
aws rds modify-db-instance \
  --db-instance-identifier sre-app-db \
  --max-allocated-storage 500 \
  --apply-immediately

# 6. 设置告警
aws cloudwatch put-metric-alarm \
  --alarm-name "RDS-LowStorage" \
  --metric-name FreeStorageSpace \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 5368709120 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=DBInstanceIdentifier,Value=sre-app-db \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:sre-alerts"
```

#### 案例 2：数据库连接数过高

```bash
# 1. 检查连接数
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=sre-app-db \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Average Maximum

# 2. 检查当前连接（MySQL）
# SHOW PROCESSLIST;
# SELECT user, host, db, command, time, state 
# FROM information_schema.processlist 
# ORDER BY time DESC;

# 3. 查找连接泄漏
# SELECT user, COUNT(*) as connections 
# FROM information_schema.processlist 
# GROUP BY user ORDER BY connections DESC;

# 4. 设置连接限制
# 在参数组中：
# max_connections = 500
# wait_timeout = 300
# interactive_timeout = 300

# 5. 推荐：使用 RDS Proxy 管理连接池
aws rds create-db-proxy \
  --db-proxy-name sre-app-proxy \
  --engine-family MYSQL \
  --auth '[{"AuthScheme":"SECRETS","IAMAuth":"DISABLED","SecretArn":"arn:aws:secretsmanager:..."}]' \
  --role-arn arn:aws:iam::123456789012:role/RDSProxyRole \
  --vpc-subnet-ids subnet-private-1a subnet-private-1b \
  --vpc-security-group-ids sg-proxy-sg
```

#### 案例 3：Aurora 故障切换后应用无法连接

```bash
# 1. 检查集群状态
aws rds describe-db-clusters \
  --db-cluster-identifier sre-aurora-cluster \
  --query "DBClusters[0].Status"

# 2. 检查实例状态
aws rds describe-db-instances \
  --filters "Name=db-cluster-id,Values=sre-aurora-cluster" \
  --query "DBInstances[*].[DBInstanceIdentifier,DBInstanceStatus,AvailabilityZone]"

# 3. 验证 DNS 解析
nslookup sre-aurora-cluster.cluster-xxx.us-east-1.rds.amazonaws.com

# 4. 检查应用连接配置
# 确保使用 Cluster Endpoint（不是实例 Endpoint）
# 确保连接字符串配置了重试逻辑

# 根因：应用硬编码了 Writer 实例的 Endpoint，故障切换后 Endpoint 变化
# 解决方案：使用 Cluster Endpoint（自动指向当前 Writer）
```

---

## 💻 实战练习

### 练习 1：基础操作 — 创建 RDS 实例

```bash
# 步骤 1: 创建子网组
aws rds create-db-subnet-group \
  --db-subnet-group-name exercise-db-subnet \
  --db-subnet-group-description "Exercise" \
  --subnet-ids subnet-priv-1a subnet-priv-1b

# 步骤 2: 创建安全组
SG_ID=$(aws ec2 create-security-group \
  --group-name exercise-db-sg \
  --description "Exercise DB" \
  --vpc-id vpc-xxxx \
  --query "GroupId" --output text)

# 步骤 3: 创建 RDS 实例
aws rds create-db-instance \
  --db-instance-identifier exercise-db \
  --db-instance-class db.t3.micro \
  --engine mysql \
  --engine-version 8.0.35 \
  --master-username admin \
  --master-user-password 'ExercisePass2026!' \
  --allocated-storage 20 \
  --db-subnet-group-name exercise-db-subnet \
  --vpc-security-group-ids "$SG_ID" \
  --backup-retention-period 1 \
  --no-multi-az \
  --no-deletion-protection

# 步骤 4: 等待可用
aws rds wait db-instance-available --db-instance-identifier exercise-db

# 步骤 5: 获取端点
aws rds describe-db-instances \
  --db-instance-identifier exercise-db \
  --query "DBInstances[0].Endpoint.Address" --output text

# 步骤 6: 清理
aws rds delete-db-instance \
  --db-instance-identifier exercise-db \
  --skip-final-snapshot \
  --delete-automated-backups
```

### 练习 2：进阶场景 — 配置只读副本

```bash
# 步骤 1: 创建只读副本
aws rds create-db-instance-read-replica \
  --db-instance-identifier exercise-db-read \
  --source-db-instance-identifier exercise-db

# 步骤 2: 等待可用
aws rds wait db-instance-available --db-instance-identifier exercise-db-read

# 步骤 3: 监控复制延迟
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=exercise-db-read \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average

# 步骤 4: 在主实例写入数据，从副本读取验证
```

### 练习 3：故障排查挑战 — 慢查询排查

**场景：** RDS CPU 使用率持续 90%+，应用响应缓慢。

```bash
# 排查步骤
# 1. 检查 CPU 使用率
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=sre-app-db \
  --start-time $(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average Maximum

# 2. 使用 Performance Insights 查找 Top SQL
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier db-xxxxx \
  --metric-queries '[{"Metric":"db.load.avg","GroupBy":{"Group":"db.sql","Dimensions":["db.sql.id"],"Limit":5}}]' \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period-in-seconds 300

# 3. 检查慢查询日志
# 在 MySQL 中：
# SHOW VARIABLES LIKE 'slow_query_log';
# SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;

# 4. 分析执行计划
# EXPLAIN SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending';

# 答案：缺少索引导致全表扫描
# 解决方案：ALTER TABLE orders ADD INDEX idx_customer_status (customer_id, status);
```

---

## 🎯 面试题精选

### 题目 1：Multi-AZ 和 Read Replica 的区别？

**答：**
- **Multi-AZ**：同步复制，用于高可用，备用实例不处理读请求，自动故障切换，零数据丢失
- **Read Replica**：异步复制，用于读扩展，可以处理读请求，手动提升为主实例，秒级延迟

### 题目 2：Aurora 的存储架构有什么特别？

**答：** Aurora 存储层是分布式、自愈的 SSD 存储：
- 数据自动跨 3 个 AZ 复制 6 副本
- 存储自动扩展，最大 128 TB
- 只写入变更的页面（redo log），减少 I/O
- 存储层独立于计算层，支持快速故障切换

### 题目 3：RDS 自动备份保留多长时间？

**答：** 默认 1 天，可配置 1-35 天。设置为 0 禁用自动备份（不推荐）。自动备份在备份窗口期间进行，支持 PITR（时间点恢复）。

### 题目 4：如何实现 RDS 的零停机存储扩展？

**答：** RDS 支持在线存储扩展（无需停机）：
1. 使用 `modify-db-instance` 增加 `allocated-storage`
2. 设置 `max-allocated-storage` 启用自动扩展
3. 存储扩展操作不中断数据库服务
4. 但不能缩小存储（需要创建新实例迁移数据）

### 题目 5：RDS Proxy 的作用是什么？

**答：** RDS Proxy 是一个托管的数据库代理：
- 连接池管理（减少数据库连接数）
- 自动故障切换（无需应用重连）
- IAM 认证支持
- 提高可用性和可扩展性
- 适用于 Serverless 和 Lambda 场景

### 题目 6：如何监控 RDS 的性能？

**答：**
1. **CloudWatch 指标**：CPU、内存、存储、连接数、IOPS
2. **Performance Insights**：Top SQL、等待事件、负载分析
3. **Enhanced Monitoring**：OS 级别指标（进程、线程）
4. **慢查询日志**：识别慢查询
5. **事件通知**：维护、故障切换等事件

### 题目 7：Aurora Serverless v2 的适用场景？

**答：**
- 访问模式不可预测的工作负载
- 开发和测试环境（可以缩容到 0.5 ACU）
- 多租户应用（每个租户一个数据库）
- 不需要持续运行的后台任务

### 题目 8：RDS 的维护窗口是什么？

**答：** 维护窗口是 AWS 执行系统维护（如操作系统补丁、数据库引擎升级）的时间段。在此期间实例可能重启。建议设置在低流量时段。Auto Minor Version Upgrade 会自动在维护窗口内应用小版本升级。

---

## 📚 深入阅读

- [RDS 官方文档](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html)
- [Aurora 官方文档](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html)
- [Performance Insights](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html)
- [RDS 最佳实践](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [RDS Proxy](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html)

---

## ✅ 自检清单

- [ ] 能够根据需求选择合适的 RDS 引擎
- [ ] 能够创建和管理 RDS 实例
- [ ] 理解 Multi-AZ 和 Read Replica 的区别和配置
- [ ] 能够配置自动备份和 PITR 恢复
- [ ] 能够创建和修改参数组
- [ ] 能够配置 RDS 安全（安全组、加密、IAM 认证）
- [ ] 能够使用 Performance Insights 分析性能
- [ ] 理解 Aurora 的架构优势
- [ ] 能够排查 RDS 常见故障（连接、存储、性能）
- [ ] 能够配置 RDS 事件通知和 CloudWatch 告警
