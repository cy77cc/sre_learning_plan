# Day 72: MySQL 高可用与备份

> 📅 日期：2026-05-03
> 📖 学习主题：主从复制原理、GTID、半同步复制、MHA/Orchestrator、InnoDB Cluster、备份恢复、PITR、监控指标
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 70（MySQL 基础与架构）, Day 71（MySQL 性能调优）

## 🎯 学习目标

完成 Day 72 的学习后，你应该能够：
1. 画出 MySQL 主从复制的完整流程图，解释 binlog dump、I/O thread、SQL thread 的协作
2. 配置并验证基于 GTID 的主从复制，理解 GTID 相比传统复制的优势
3. 理解半同步复制的原理和 `rpl_semi_sync_master_wait_point` 的区别
4. 掌握 mysqldump 和 xtrabackup 的使用场景和操作流程
5. 实现基于 binlog 的时间点恢复 (PITR)
6. 设计 MySQL 高可用架构方案，区分 MHA、Orchestrator、InnoDB Cluster 的适用场景
7. 建立 MySQL 监控指标体系，区分 DBA 和 SRE 的职责边界

---

## 📖 核心知识点

### 1. 主从复制原理

#### 1.1 复制架构总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                    MySQL 主从复制架构                                  │
│                                                                      │
│   ┌─────────────────────┐                                           │
│   │    Master (主库)     │                                           │
│   │                     │                                           │
│   │  ┌───────────────┐  │    binlog events                         │
│   │  │   Binlog      │  │ ──────────────────────┐                  │
│   │  │  (binlog.0001) │  │                       │                  │
│   │  └───────────────┘  │                       │                  │
│   │                     │    ┌───────────────────┼───────────────┐  │
│   │  ┌───────────────┐  │    │   Binlog Dump    │               │  │
│   │  │  写入线程     │  │    │   Thread         │               │  │
│   │  │  (执行SQL)    │  │    │   (Master端)     │               │  │
│   │  └───────────────┘  │    │   读取binlog     │               │  │
│   └─────────────────────┘    │   发送给Slave    │               │  │
│                              └────────┬──────────┘               │  │
│                                       │                           │  │
│   ┌──────────────────────────────────┼───────────────────────────┤  │
│   │    Slave (从库)                  │                           │  │
│   │                                  ▼                           │  │
│   │  ┌───────────────────────────────────────┐                  │  │
│   │  │  I/O Thread (从库IO线程)               │                  │  │
│   │  │  接收 binlog events                    │                  │  │
│   │  │  写入本地 Relay Log                     │                  │  │
│   │  └───────────────────┬───────────────────┘                  │  │
│   │                      ▼                                      │  │
│   │  ┌───────────────────────────────────────┐                  │  │
│   │  │  Relay Log (中继日志)                   │                  │  │
│   │  │  (relay-log.000001)                    │                  │  │
│   │  └───────────────────┬───────────────────┘                  │  │
│   │                      ▼                                      │  │
│   │  ┌───────────────────────────────────────┐                  │  │
│   │  │  SQL Thread (从库SQL线程)              │                  │  │
│   │  │  读取 Relay Log                         │                  │  │
│   │  │  重放 SQL 语句                          │                  │  │
│   │  └───────────────────┬───────────────────┘                  │  │
│   │                      ▼                                      │  │
│   │  ┌───────────────────────────────────────┐                  │  │
│   │  │  Slave 数据库                          │                  │  │
│   │  │  (与 Master 数据一致)                   │                  │  │
│   │  └───────────────────────────────────────┘                  │  │
│   └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

#### 1.2 复制流程详解

```
完整复制流程：

1. Master 执行写操作
   → 记录到 binlog（按事务提交顺序）

2. Slave 的 I/O Thread
   → 连接 Master 的 Binlog Dump Thread
   → 请求从指定位置（binlog 文件名 + 偏移量 或 GTID）开始的 binlog
   → 接收 binlog events
   → 写入本地 Relay Log

3. Slave 的 SQL Thread
   → 读取 Relay Log
   → 按顺序重放 events
   → 在 Slave 上执行相同的变更

时间线：
  Master:  [T1: INSERT] → [T2: UPDATE] → [T3: DELETE]
                ↓              ↓              ↓
  Binlog:  [event1]      [event2]      [event3]
                ↓              ↓              ↓
  Relay:   [event1]      [event2]      [event3]
                ↓              ↓              ↓
  Slave:   [重放 T1]     [重放 T2]     [重放 T3]

延迟来源：
  -  网络传输延迟（binlog 从 Master 到 Slave）
  -  SQL Thread 单线程重放（MySQL 5.6 前的瓶颈）
  -  大事务执行时间（如一次性 UPDATE 100 万行）
```

#### 1.3 传统复制 vs GTID 复制

```
传统复制（基于 binlog position）：
  -  CHANGE MASTER TO MASTER_LOG_FILE='binlog.000003', MASTER_LOG_POS=154;
  -  优点：简单直观
  -  缺点：
     a. 主从切换时需要手动计算新 Master 的 binlog position
     b. 故障转移复杂，容易出错
     c. 无法自动跳过已执行的事务

GTID 复制（Global Transaction Identifier）：
  -  每个事务有全局唯一标识：server_uuid:transaction_id
  -  例如：3e11fa47-71ca-11e1-9e33-c80aa9429562:23
  -  优点：
     a. 主从切换时 Slave 自动找到正确位置
     b. 故障转移简单可靠
     c. 可以自动跳过已执行的事务
     d. 便于搭建复杂的复制拓扑
  -  缺点：
     a. 不支持 CREATE TABLE ... SELECT（MySQL 8.0 前）
     b. 不支持事务和非事务混合引擎
```

---

### 2. 主从复制配置

#### 2.1 GTID 主从复制配置

```ini
# Master 配置 (my.cnf)
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog_format = ROW
binlog_row_image = FULL
sync_binlog = 1

# GTID 配置
gtid_mode = ON
enforce_gtid_consistency = ON

# 半同步复制（可选）
# plugin-load = "rpl_semi_sync_master=semisync_master.so"
# rpl_semi_sync_master_enabled = 1
# rpl_semi_sync_master_timeout = 1000

# 从库写入 relay log 的安全配置
innodb_flush_log_at_trx_commit = 1
```

```ini
# Slave 配置 (my.cnf)
[mysqld]
server-id = 2                          # 每个实例必须不同
log-bin = mysql-bin
binlog_format = ROW
relay-log = relay-bin
log_slave_updates = ON                 # 从库也记录 binlog（级联复制需要）
read_only = ON                         # 从库只读
super_read_only = ON                   # 超级用户也只读（推荐）

# GTID 配置
gtid_mode = ON
enforce_gtid_consistency = ON

# 并行复制（MySQL 5.7+）
slave_parallel_type = LOGICAL_CLOCK
slave_parallel_workers = 8
slave_preserve_commit_order = ON
```

```sql
-- 在 Master 上创建复制用户
CREATE USER 'repl'@'%' IDENTIFIED BY 'StrongPassword123!';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;

-- 在 Slave 上配置主从关系
CHANGE MASTER TO
    MASTER_HOST='10.0.1.1',
    MASTER_PORT=3306,
    MASTER_USER='repl',
    MASTER_PASSWORD='StrongPassword123!',
    MASTER_AUTO_POSITION=1;   -- GTID 模式

-- 启动复制
START SLAVE;

-- 查看复制状态
SHOW SLAVE STATUS\G
```

#### 2.2 关键状态指标

```sql
SHOW SLAVE STATUS\G

-- 重点关注以下字段：
-- Slave_IO_Running: Yes          ← I/O 线程是否运行
-- Slave_SQL_Running: Yes         ← SQL 线程是否运行
-- Seconds_Behind_Master: 0       ← 复制延迟（秒），0 表示无延迟
-- Retrieved_Gtid_Set             ← 已接收的 GTID 集合
-- Executed_Gtid_Set              ← 已执行的 GTID 集合
-- Last_IO_Error                  ← 最近的 I/O 错误
-- Last_SQL_Error                 ← 最近的 SQL 错误
-- Relay_Log_Space                ← Relay Log 占用空间

-- 复制延迟详细分析（MySQL 8.0）
SELECT
    CHANNEL_NAME,
    SERVICE_STATE AS io_state,
    RECEIVED_TRANSACTION_SET
FROM performance_schema.replication_connection_status;

SELECT
    CHANNEL_NAME,
    SERVICE_STATE AS sql_state,
    LAST_APPLIED_TRANSACTION_END_APPLY_TIMESTAMP
FROM performance_schema.replication_applier_status_by_worker;
```

---

### 3. 半同步复制

#### 3.1 异步复制 vs 半同步复制

```
异步复制（默认）：
  Master: COMMIT → 写 binlog → 返回客户端成功
  Slave:  异步接收 binlog → 异步重放

  风险：Master 崩溃时，可能有已提交的事务未同步到 Slave
        导致切换后数据丢失

  时间线：
  Master: [写入] → [binlog] → [返回成功] →→→ [Slave 接收] → [Slave 重放]
                                              ↑ 可能还没收到

半同步复制：
  Master: COMMIT → 写 binlog → 等待 Slave 确认收到 → 返回客户端成功
  Slave:  接收 binlog → 确认收到 → 异步重放

  保证：Master 返回成功时，至少有一个 Slave 已收到 binlog
  注意：只保证 Slave 收到，不保证 Slave 已重放（应用）

  时间线：
  Master: [写入] → [binlog] → [等Slave确认] → [返回成功]
  Slave:                   [接收] → [确认收到] → [重放]
```

#### 3.2 半同步复制配置

```sql
-- 安装半同步插件（Master）
INSTALL PLUGIN rpl_semi_sync_master SONAME 'semisync_master.so';
SET GLOBAL rpl_semi_sync_master_enabled = 1;
SET GLOBAL rpl_semi_sync_master_timeout = 1000;  -- 超时 1 秒降级为异步

-- 安装半同步插件（Slave）
INSTALL PLUGIN rpl_semi_sync_slave SONAME 'semisync_slave.so';
SET GLOBAL rpl_semi_sync_slave_enabled = 1;

-- 重启 Slave 的 I/O 线程使配置生效
STOP SLAVE IO_THREAD;
START SLAVE IO_THREAD;

-- 查看半同步状态
SHOW STATUS LIKE 'Rpl_semi_sync%';

-- 关键指标：
-- Rpl_semi_sync_master_status: ON              → 半同步是否启用
-- Rpl_semi_sync_master_clients: 1              → 半同步 Slave 数量
-- Rpl_semi_sync_master_no_tx: 0                → 降级为异步的事务数
-- Rpl_semi_sync_master_yes_tx: 1000            → 半同步成功的事务数
-- Rpl_semi_sync_master_net_avg_wait_time: 500  → 平均等待时间（微秒）
```

#### 3.3 wait_point 的区别

```sql
-- MySQL 5.7 引入 rpl_semi_sync_master_wait_point

-- AFTER_SYNC（默认，MySQL 5.7+）
-- 流程：写 binlog → 等 Slave 确认 → 存储引擎 COMMIT
-- 优点：主从数据完全一致，不会出现幻读
-- 场景：推荐使用

-- AFTER_COMMIT（MySQL 5.6）
-- 流程：写 binlog → 存储引擎 COMMIT → 等 Slave 确认 → 返回客户端
-- 缺点：Master 已提交但 Slave 未确认时，其他客户端可能看到已提交数据
--       而 Slave 还没有这些数据 → 不一致窗口

-- 设置
SET GLOBAL rpl_semi_sync_master_wait_point = 'AFTER_SYNC';
```

---

### 4. MHA 与 Orchestrator

#### 4.1 MHA (Master High Availability)

```
MHA 架构：
  ┌──────────────┐
  │  MHA Manager  │  ← 监控 Master 状态
  │  (管理节点)   │     故障检测 + 自动切换
  └──────┬───────┘
         │ 监控心跳
    ┌────┼────────────────────┐
    │    │                    │
    ▼    ▼                    ▼
┌────────┐ ┌────────┐ ┌────────┐
│Master  │ │Slave 1 │ │Slave 2 │
│(主库)  │ │(从库)  │ │(从库)  │
└────────┘ └────────┘ └────────┘

MHA 故障切换流程：
  1. Manager 检测到 Master 不可用（连续 N 次心跳失败）
  2. 确认 Master 真的宕机（SSH 检查、MySQL ping）
  3. 从所有 Slave 中选出数据最新的作为新 Master
  4. 将其他 Slave 切换到新 Master
  5. 应用差异的 relay log（补齐未同步的数据）
  6. VIP 漂移到新 Master
  7. 通知应用层

优势：
  -  保证数据一致性（尽可能补齐差异数据）
  -  自动故障转移（30 秒内完成）
  -  支持在线切换（计划内维护）

劣势：
  -  需要 SSH 互通
  -  Manager 单点（可以部署多个）
  -  社区维护减少（2018 年后更新缓慢）
```

#### 4.2 Orchestrator

```
Orchestrator 架构：
  ┌──────────────────────────────┐
  │     Orchestrator 集群         │
  │  (3 节点，Raft 一致性)       │
  │  ┌─────┐ ┌─────┐ ┌─────┐   │
  │  │ O1  │ │ O2  │ │ O3  │   │
  │  │Lead │ │Foll │ │Foll │   │
  │  └─────┘ └─────┘ └─────┘   │
  └──────────┬───────────────────┘
             │ 管理/监控
    ┌────────┼────────┬────────────┐
    │        │        │            │
    ▼        ▼        ▼            ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│Master │ │Slave 1│ │Slave 2│ │Slave 3│
│       │ │       │ │       │ │       │
└───────┘ └───────┘ └───────┘ └───────┘

Orchestrator 优势：
  -  支持复杂的复制拓扑（树形、环形）
  -  Web UI 可视化拓扑管理
  -  自动发现和修复复制拓扑变化
  -  支持多种故障转移策略
  -  社区活跃，持续更新
  -  不需要 SSH 互通

Orchestrator 故障转移流程：
  1. 检测 Master 故障（通过代理查询或心跳）
  2. 确认故障（多次检测，避免误判）
  3. 选择最佳候选 Master（数据最新、延迟最小）
  4. 提升候选为新 Master
  5. 重新配置其他 Slave 指向新 Master
  6. 通过 hook 脚本更新 VIP/DNS/ProxySQL
```

#### 4.3 自动化切换脚本示例

```bash
#!/bin/bash
# Orchestrator 故障切换 hook 脚本
# 在 Orchestrator 的 PostFailoverProcesses 中配置

EVENT_TYPE=$1      # failure, recovery, etc.
SUCCESSOR_HOST=$2  # 新 Master 的 host
DEAD_MASTER=$3     # 旧 Master 的 host

LOG_FILE="/var/log/orchestrator/failover.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$EVENT_TYPE] $*" >> "$LOG_FILE"
}

log "开始故障切换: 旧 Master=$DEAD_MASTER, 新 Master=$SUCCESSOR_HOST"

# 1. 更新 ProxySQL 后端配置
mysql -h 127.0.0.1 -P 6032 -u admin -padmin_pass -e "
    UPDATE mysql_servers
    SET hostname = '$SUCCESSOR_HOST'
    WHERE hostgroup_id = 10 AND hostname = '$DEAD_MASTER';
    LOAD MYSQL SERVERS TO RUNTIME;
"
log "ProxySQL 配置已更新"

# 2. 更新 DNS 记录（如果使用 DNS 方式）
# nsupdate -k /etc/bind/rndc.key <<EOF
# update delete master.db.internal A
# update add master.db.internal 60 A $(dig +short $SUCCESSOR_HOST)
# send
# EOF

# 3. 发送告警通知
curl -X POST "https://hooks.slack.com/services/xxx" \
    -H 'Content-type: application/json' \
    -d "{\"text\": \"[MySQL Failover] Master: $DEAD_MASTER -> $SUCCESSOR_HOST, Event: $EVENT_TYPE\"}"

log "故障切换完成"
```

---

### 5. InnoDB Cluster

#### 5.1 架构概述

```
InnoDB Cluster 是 MySQL 官方的高可用解决方案，基于：
  -  Group Replication (组复制) — 数据同步
  -  MySQL Shell — 管理工具
  -  MySQL Router — 透明路由

┌──────────────────────────────────────────────────────────────┐
│                    InnoDB Cluster 架构                        │
│                                                              │
│   ┌─────────────────────────────────────────────┐           │
│   │           Group Replication                  │           │
│   │                                             │           │
│   │   ┌─────────┐ ┌─────────┐ ┌─────────┐     │           │
│   │   │ Node 1  │ │ Node 2  │ │ Node 3  │     │           │
│   │   │(Primary)│ │(Second.)│ │(Second.)│     │           │
│   │   │  RW     │ │  RO     │ │  RO     │     │           │
│   │   └────┬────┘ └────┬────┘ └────┬────┘     │           │
│   │        └───────────┼───────────┘           │           │
│   │          Paxos 协议（多数派一致性）        │           │
│   └─────────────────────────────────────────────┘           │
│                         │                                    │
│   ┌─────────────────────┼───────────────────────┐           │
│   │           MySQL Router                       │           │
│   │                                             │           │
│   │   Port 6446 (RW) → Primary Node            │           │
│   │   Port 6447 (RO) → Secondary Nodes         │           │
│   └─────────────────────┬───────────────────────┘           │
│                         │                                    │
│   ┌─────────────────────┼───────────────────────┐           │
│   │           应用程序                           │           │
│   │   连接 localhost:6446 (写)                  │           │
│   │   连接 localhost:6447 (读)                  │           │
│   └─────────────────────────────────────────────┘           │
└──────────────────────────────────────────────────────────────┘

Group Replication 特性：
  -  单主模式（推荐）：只有一个节点可写，自动选主
  -  多主模式：所有节点都可写（冲突检测，性能受限）
  -  基于 Paxos 协议，需要至少 3 个节点（容忍 1 个故障）
  -  自动故障检测和切换（秒级）
```

#### 5.2 InnoDB Cluster 快速搭建

```sql
-- 使用 MySQL Shell 搭建

-- Step 1: 配置三个 MySQL 实例（每个实例 server-id 不同）
-- 每个实例的 my.cnf 都需要：
-- [mysqld]
-- server-id = X
-- gtid_mode = ON
-- enforce_gtid_consistency = ON
-- binlog_checksum = NONE
-- log_bin = mysql-bin
-- binlog_format = ROW
-- master_info_repository = TABLE
-- relay_log_info_repository = TABLE
-- transaction_write_set_extraction = XXHASH64

-- Step 2: 使用 MySQL Shell 检查实例配置
-- mysqlsh root@node1:3306
-- dba.checkInstanceConfiguration()
-- 对每个节点执行

-- Step 3: 创建 Cluster
-- mysqlsh root@node1:3306
-- var cluster = dba.createCluster('myCluster')

-- Step 4: 添加节点
-- cluster.addInstance('root@node2:3306')
-- cluster.addInstance('root@node3:3306')

-- Step 5: 查看集群状态
-- cluster.status()
-- 输出示例：
-- {
--     "clusterName": "myCluster",
--     "status": "OK",
--     "topology": {
--         "node1:3306": {"status": "ONLINE", "role": "PRIMARY"},
--         "node2:3306": {"status": "ONLINE", "role": "SECONDARY"},
--         "node3:3306": {"status": "ONLINE", "role": "SECONDARY"}
--     }
-- }
```

```bash
# Step 6: 配置 MySQL Router
mysqlrouter --bootstrap root@node1:3306 --directory /etc/mysqlrouter
systemctl start mysqlrouter

# 验证路由
mysql -h 127.0.0.1 -P 6446 -u root -e "SELECT @@hostname;"  # RW → Primary
mysql -h 127.0.0.1 -P 6447 -u root -e "SELECT @@hostname;"  # RO → Secondary
```

---

### 6. 备份策略与工具

#### 6.1 备份分类

```
┌──────────────────────────────────────────────────────────────────┐
│                    MySQL 备份分类                                  │
├────────────────┬─────────────────────────────────────────────────┤
│ 按方式分       │                                                 │
├────────────────┼─────────────────────────────────────────────────┤
│ 逻辑备份       │ mysqldump, mydumper, mysqlpump                  │
│                │ 备份 SQL 语句或 CSV                             │
│                │ 优点：跨版本恢复，可选择性恢复                  │
│                │ 缺点：备份/恢复慢，文件大                       │
├────────────────┼─────────────────────────────────────────────────┤
│ 物理备份       │ xtrabackup (Percona), mysqlbackup (Oracle)     │
│                │ 直接复制数据文件                                │
│                │ 优点：备份/恢复快，对业务影响小                 │
│                │ 缺点：不能跨版本，需要相同 OS 和 MySQL 版本    │
├────────────────┼─────────────────────────────────────────────────┤
│ 按范围分       │                                                 │
├────────────────┼─────────────────────────────────────────────────┤
│ 全量备份       │ 完整数据库备份                                  │
│ 增量备份       │ 自上次备份以来的变更                            │
│ 差异备份       │ 自上次全量备份以来的变更                        │
├────────────────┼─────────────────────────────────────────────────┤
│ 按是否锁表分   │                                                 │
├────────────────┼─────────────────────────────────────────────────┤
│ 热备           │ 不锁表，不影响读写（xtrabackup）               │
│ 温备           │ 只读，不写入（mysqldump --single-transaction） │
│ 冷备           │ 停止 MySQL 后复制数据文件                       │
└────────────────┴─────────────────────────────────────────────────┘
```

#### 6.2 mysqldump 备份

```bash
# 全库备份
mysqldump -u root -p \
    --all-databases \
    --single-transaction \       # InnoDB 热备（使用 MVCC 一致性快照）
    --routines \                 # 包含存储过程和函数
    --triggers \                 # 包含触发器
    --events \                   # 包含事件
    --set-gtid-purged=ON \      # GTID 环境下保留 GTID 信息
    --master-data=2 \           # 记录 binlog position（注释形式）
    --flush-logs \              # 刷新 binlog（便于增量恢复）
    --hex-blob \                # 二进制数据使用十六进制
    --result-file=/backup/full_$(date +%Y%m%d_%H%M%S).sql

# 单库备份
mysqldump -u root -p \
    --single-transaction \
    --set-gtid-purged=OFF \
    sre_lab > /backup/sre_lab_$(date +%Y%m%d).sql

# 单表备份
mysqldump -u root -p \
    --single-transaction \
    --set-gtid-purged=OFF \
    sre_lab orders users > /backup/tables_$(date +%Y%m%d).sql

# 只备份表结构
mysqldump -u root -p --no-data sre_lab > /backup/schema.sql

# 只备份数据
mysqldump -u root -p --no-create-info sre_lab > /backup/data.sql

# 压缩备份
mysqldump -u root -p --all-databases --single-transaction | \
    gzip > /backup/full_$(date +%Y%m%d).sql.gz

# 恢复
mysql -u root -p < /backup/full_20260503.sql
gunzip < /backup/full_20260503.sql.gz | mysql -u root -p
```

#### 6.3 xtrabackup 备份（推荐生产使用）

```bash
# 安装 Percona XtraBackup
# apt install percona-xtrabackup-80  或
# yum install percona-xtrabackup-80

# ============================================================
# 全量备份
# ============================================================
xtrabackup --backup \
    --target-dir=/backup/full \
    --user=root \
    --password=StrongPassword

# 备份完成后，准备备份（apply log）
xtrabackup --prepare --target-dir=/backup/full

# 恢复
systemctl stop mysql
rm -rf /var/lib/mysql/*
xtrabackup --copy-back --target-dir=/backup/full
chown -R mysql:mysql /var/lib/mysql
systemctl start mysql

# ============================================================
# 增量备份
# ============================================================
# 第一次：全量备份
xtrabackup --backup \
    --target-dir=/backup/full \
    --user=root --password=StrongPassword

# 第二次：增量备份（基于全量）
xtrabackup --backup \
    --target-dir=/backup/inc1 \
    --incremental-basedir=/backup/full \
    --user=root --password=StrongPassword

# 第三次：增量备份（基于上次增量）
xtrabackup --backup \
    --target-dir=/backup/inc2 \
    --incremental-basedir=/backup/inc1 \
    --user=root --password=StrongPassword

# 增量恢复：先准备全量，再合并增量
# Step 1: 准备全量备份（不回滚未提交事务）
xtrabackup --prepare --apply-log-only --target-dir=/backup/full

# Step 2: 合并第一个增量
xtrabackup --prepare --apply-log-only \
    --target-dir=/backup/full \
    --incremental-dir=/backup/inc1

# Step 3: 合并第二个增量（最后一次不加 --apply-log-only）
xtrabackup --prepare \
    --target-dir=/backup/full \
    --incremental-dir=/backup/inc2

# Step 4: 恢复
systemctl stop mysql
rm -rf /var/lib/mysql/*
xtrabackup --copy-back --target-dir=/backup/full
chown -R mysql:mysql /var/lib/mysql
systemctl start mysql
```

#### 6.4 备份脚本（SRE 生产级）

```bash
#!/bin/bash
# MySQL 自动备份脚本 — 生产级
# 用途：每日全量备份 + 增量备份 + 保留策略 + 备份验证

set -euo pipefail

# ============================================================
# 配置
# ============================================================
BACKUP_DIR="/backup/mysql"
RETENTION_DAYS=7                 # 保留最近 7 天的备份
MYSQL_USER="backup_user"
MYSQL_PASS="${MYSQL_BACKUP_PASS}"  # 从环境变量读取
MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
LOG_FILE="/var/log/mysql/backup.log"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

TODAY=$(date +%Y%m%d)
FULL_DIR="${BACKUP_DIR}/full/${TODAY}"
INCR_DIR="${BACKUP_DIR}/incr"
WEEKDAY=$(date +%u)  # 1=周一, 7=周日

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

notify() {
    local msg="$1"
    log "$msg"
    if [[ -n "$SLACK_WEBHOOK" ]]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-type: application/json' \
            -d "{\"text\": \"$msg\"}" > /dev/null 2>&1 || true
    fi
}

# ============================================================
# 备份函数
# ============================================================
do_full_backup() {
    log "开始全量备份: ${FULL_DIR}"
    mkdir -p "${FULL_DIR}"

    xtrabackup --backup \
        --target-dir="${FULL_DIR}" \
        --user="${MYSQL_USER}" \
        --password="${MYSQL_PASS}" \
        --host="${MYSQL_HOST}" \
        --port="${MYSQL_PORT}" \
        --compress \
        --compress-threads=4 \
        2>>"$LOG_FILE"

    # 记录备份元数据
    echo "${TODAY}" > "${BACKUP_DIR}/latest_full"

    local size
    size=$(du -sh "${FULL_DIR}" | cut -f1)
    log "全量备份完成，大小: ${size}"
}

do_incr_backup() {
    local latest_full
    latest_full=$(cat "${BACKUP_DIR}/latest_full" 2>/dev/null || echo "")
    if [[ -z "$latest_full" ]]; then
        log "没有找到全量备份，执行全量备份"
        do_full_backup
        return
    fi

    local base_dir="${BACKUP_DIR}/full/${latest_full}"
    local incr_target="${INCR_DIR}/${TODAY}"

    # 查找最近的备份目录（全量或增量）
    local latest_incr
    latest_incr=$(ls -d "${INCR_DIR}"/${latest_full}* 2>/dev/null | tail -1 || echo "")
    local basedir_to_use="${base_dir}"
    if [[ -n "$latest_incr" ]]; then
        basedir_to_use="${latest_incr}"
    fi

    log "开始增量备份: ${incr_target} (基于: ${basedir_to_use})"
    mkdir -p "${incr_target}"

    xtrabackup --backup \
        --target-dir="${incr_target}" \
        --incremental-basedir="${basedir_to_use}" \
        --user="${MYSQL_USER}" \
        --password="${MYSQL_PASS}" \
        --host="${MYSQL_HOST}" \
        --port="${MYSQL_PORT}" \
        --compress \
        2>>"$LOG_FILE"

    local size
    size=$(du -sh "${incr_target}" | cut -f1)
    log "增量备份完成，大小: ${size}"
}

cleanup_old_backups() {
    log "清理 ${RETENTION_DAYS} 天前的备份"
    find "${BACKUP_DIR}/full" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true
    find "${INCR_DIR}" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} \; 2>/dev/null || true
    log "清理完成"
}

# ============================================================
# 主流程
# ============================================================
main() {
    log "===== MySQL 备份开始 ====="

    mkdir -p "${BACKUP_DIR}/full" "${INCR_DIR}"

    if [[ "$WEEKDAY" == "7" ]]; then
        # 周日：全量备份
        do_full_backup
    else
        # 周一到周六：增量备份
        do_incr_backup
    fi

    cleanup_old_backups

    notify "[MySQL Backup] 备份完成 (日期: ${TODAY}, 类型: $([ "$WEEKDAY" == "7" ] && echo "全量" || echo "增量"))"
    log "===== MySQL 备份结束 ====="
}

main "$@"
```

---

### 7. 时间点恢复 (PITR)

#### 7.1 PITR 原理

```
PITR (Point-in-Time Recovery) 原理：
  1. 恢复最近的全量备份
  2. 应用全量备份后的增量备份（如有）
  3. 重放 binlog 到指定时间点或 GTID

  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
  │ 全量备份 │ → │ 增量备份 │ → │ binlog   │ → │ 恢复到   │
  │ (周日)   │   │ (周一~六)│   │ 重放     │   │ 时间点 T │
  └──────────┘   └──────────┘   └──────────┘   └──────────┘

场景：
  -  误删数据（DROP TABLE, DELETE without WHERE）
  -  误更新数据（UPDATE SET wrong_value）
  -  安全审计（查看某个时间点的数据状态）
```

#### 7.2 PITR 操作步骤

```bash
# 场景：2026-05-03 14:30:00 有人误删了 orders 表的数据
# 需要恢复到 2026-05-03 14:29:59 的状态

# ============================================================
# Step 1: 找到全量备份和 binlog
# ============================================================
# 全量备份时间：2026-05-03 02:00:00
# binlog 文件列表
ls -la /var/log/mysql/binlog.*
# binlog.000001 (全量备份时刷新)
# binlog.000002 (包含 02:00 到 14:30 之间的所有变更)
# binlog.000003 (14:30 之后)

# ============================================================
# Step 2: 在临时实例上恢复全量备份
# ============================================================
# 准备临时 MySQL 实例
docker run -d --name mysql-recovery \
    -e MYSQL_ROOT_PASSWORD=temppass \
    -v /backup/full/20260503:/backup \
    -p 3307:3306 \
    mysql:8.0

# 恢复全量备份到临时实例
docker exec mysql-recovery bash -c "
    xtrabackup --prepare --target-dir=/backup
"
docker exec mysql-recovery bash -c "
    # 停止 MySQL，替换数据目录
    mysqladmin -u root -ptemppass shutdown
    rm -rf /var/lib/mysql/*
    xtrabackup --copy-back --target-dir=/backup
    chown -R mysql:mysql /var/lib/mysql
"

# 启动临时实例
docker start mysql-recovery

# ============================================================
# Step 3: 重放 binlog 到指定时间点
# ============================================================
# 从主库复制 binlog 文件
scp master:/var/log/mysql/binlog.000002 /tmp/
scp master:/var/log/mysql/binlog.000003 /tmp/

# 解析 binlog 找到误操作的位置
mysqlbinlog --base64-output=DECODE-ROWS -v \
    --start-datetime="2026-05-03 14:00:00" \
    --stop-datetime="2026-05-03 14:35:00" \
    /tmp/binlog.000002 | grep -A5 -B5 "DELETE FROM orders"

# 找到误操作的精确位置，比如 binlog.000003 position 1234

# 方案 A：按时间点恢复（不包含误操作）
mysqlbinlog \
    --start-datetime="2026-05-03 02:00:00" \
    --stop-datetime="2026-05-03 14:29:59" \
    /tmp/binlog.000002 /tmp/binlog.000003 | \
    mysql -h 127.0.0.1 -P 3307 -u root -ptemppass

# 方案 B：按位置恢复（更精确）
mysqlbinlog \
    --start-position=154 \
    --stop-position=1234 \
    /tmp/binlog.000002 /tmp/binlog.000003 | \
    mysql -h 127.0.0.1 -P 3307 -u root -ptemppass

# 方案 C：按 GTID 恢复（最精确）
mysqlbinlog \
    --exclude-gtids="3e11fa47-71ca-11e1-9e33-c80aa9429562:100" \
    /tmp/binlog.000002 /tmp/binlog.000003 | \
    mysql -h 127.0.0.1 -P 3307 -u root -ptemppass

# ============================================================
# Step 4: 验证恢复结果
# ============================================================
mysql -h 127.0.0.1 -P 3307 -u root -ptemppass -e "
    SELECT COUNT(*) FROM sre_lab.orders;
    SELECT * FROM sre_lab.orders ORDER BY id DESC LIMIT 10;
"

# ============================================================
# Step 5: 导出恢复的数据，导入到生产库
# ============================================================
mysqldump -h 127.0.0.1 -P 3307 -u root -ptemppass \
    --single-transaction sre_lab orders > /tmp/recovered_orders.sql

mysql -u root -p sre_lab < /tmp/recovered_orders.sql

# 清理临时实例
docker stop mysql-recovery && docker rm mysql-recovery
```

---

### 8. 高可用架构方案对比

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MySQL 高可用方案对比                                      │
├──────────────┬────────────┬────────────┬────────────┬──────────────────────┤
│ 方案         │ 数据一致性 │ 切换时间   │ 复杂度     │ 适用场景             │
├──────────────┼────────────┼────────────┼────────────┼──────────────────────┤
│ 主从手动切换 │ 可能丢失   │ 分钟级     │ 低         │ 不重要业务           │
│              │ 数据       │            │            │                      │
├──────────────┼────────────┼────────────┼────────────┼──────────────────────┤
│ 半同步复制   │ 基本一致   │ 需手动     │ 中         │ 一般业务             │
│ + MHA        │            │ 或脚本     │            │                      │
│              │            │ 30 秒      │            │                      │
├──────────────┼────────────┼────────────┼────────────┼──────────────────────┤
│ Orchestrator │ 基本一致   │ 10-30 秒   │ 中         │ 中大型业务           │
│ + ProxySQL   │            │ 自动       │            │ 复杂拓扑             │
├──────────────┼────────────┼────────────┼────────────┼──────────────────────┤
│ InnoDB       │ 强一致     │ 秒级       │ 中高       │ 核心业务             │
│ Cluster      │ (Paxos)    │ 自动       │            │ 要求数据零丢失       │
├──────────────┼────────────┼────────────┼────────────┼──────────────────────┤
│ MySQL Group  │ 强一致     │ 秒级       │ 高         │ 金融级业务           │
│ Replication  │ (Paxos)    │ 自动       │            │ 要求 RPO=0           │
│ (多主模式)   │            │            │            │                      │
├──────────────┼────────────┼────────────┼────────────┼──────────────────────┤
│ Galera       │ 强一致     │ 秒级       │ 高         │ 需要多主写入         │
│ Cluster      │            │ 自动       │            │ Percona XtraDB       │
└──────────────┴────────────┴────────────┴────────────┴──────────────────────┘

SRE 选型建议：
  -  非核心业务/开发环境：主从复制 + 手动切换
  -  一般生产业务：Orchestrator + ProxySQL（成熟、社区活跃）
  -  核心业务/金融：InnoDB Cluster（官方支持、强一致）
  -  要求 RPO=0：半同步复制 + 自动切换
```

---

### 9. MySQL 监控指标体系

#### 9.1 SRE 视角的监控分层

```
┌──────────────────────────────────────────────────────────────────┐
│                 MySQL 监控分层 (SRE 视角)                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: 业务指标 (SRE 最关心)                                 │
│  ├── 查询响应时间 (P50/P95/P99)                                │
│  ├── QPS / TPS (每秒查询/事务数)                               │
│  ├── 连接数使用率                                               │
│  ├── 慢查询数量和比例                                           │
│  └── 错误率 (连接失败、超时)                                    │
│                                                                  │
│  Layer 2: 复制健康 (SRE 关键)                                   │
│  ├── 复制延迟 (Seconds_Behind_Master)                          │
│  ├── 复制线程状态 (IO/SQL Thread)                              │
│  ├── GTID 执行状态                                              │
│  └── 半同步降级次数                                             │
│                                                                  │
│  Layer 3: 存储引擎指标                                          │
│  ├── Buffer Pool 命中率                                        │
│  ├── 脏页比例                                                   │
│  ├── redo log 写入速率                                          │
│  ├── 行锁等待时间                                               │
│  └── 死锁次数                                                   │
│                                                                  │
│  Layer 4: 系统资源 (SRE 基础)                                   │
│  ├── CPU 使用率                                                 │
│  ├── 内存使用 (Buffer Pool + OS)                               │
│  ├── 磁盘 I/O (IOPS, 延迟, 使用率)                            │
│  └── 网络流量                                                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 9.2 Prometheus + mysqld_exporter 监控配置

```yaml
# prometheus.yml — MySQL 监控配置
scrape_configs:
  - job_name: 'mysql'
    static_configs:
      - targets:
        - 'mysql-master:9104'
        - 'mysql-slave1:9104'
        - 'mysql-slave2:9104'
    scrape_interval: 15s
    scrape_timeout: 10s
```

```bash
# 安装 mysqld_exporter
# 下载：https://github.com/prometheus/mysqld_exporter/releases

# 创建监控用户
mysql -u root -p -e "
CREATE USER 'exporter'@'localhost' IDENTIFIED BY 'ExporterPass123!';
GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'localhost';
FLUSH PRIVILEGES;
"

# 配置
cat > /etc/.mysqld_exporter.cnf << 'EOF'
[client]
user=exporter
password=ExporterPass123!
host=127.0.0.1
port=3306
EOF

# 启动 mysqld_exporter
mysqld_exporter \
    --config.my-cnf=/etc/.mysqld_exporter.cnf \
    --collect.global_status \
    --collect.global_variables \
    --collect.slave_status \
    --collect.info_schema.innodb_metrics \
    --collect.info_schema.processlist \
    --collect.info_schema.query_response_time \
    --web.listen-address=:9104
```

#### 9.3 关键告警规则

```yaml
# mysql_alerts.yml — Prometheus 告警规则
groups:
  - name: mysql_alerts
    rules:
      # === 业务层告警 ===
      - alert: MySQLDown
        expr: mysql_up == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "MySQL 实例 {{ $labels.instance }} 不可用"

      - alert: MySQLHighSlowQueries
        expr: rate(mysql_global_status_slow_queries[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "慢查询率过高: {{ $value }}/s"

      - alert: MySQLConnectionsHigh
        expr: >
          mysql_global_status_threads_connected /
          mysql_global_variables_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "连接使用率超过 80%: {{ $value | humanizePercentage }}"

      # === 复制告警 ===
      - alert: MySQLReplicationLag
        expr: mysql_slave_status_seconds_behind_master > 30
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "复制延迟: {{ $value }} 秒"

      - alert: MySQLReplicationLagCritical
        expr: mysql_slave_status_seconds_behind_master > 300
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "复制延迟严重: {{ $value }} 秒"

      - alert: MySQLReplicationNotRunning
        expr: >
          mysql_slave_status_slave_io_running != 1 or
          mysql_slave_status_slave_sql_running != 1
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "复制线程停止运行"

      # === 存储引擎告警 ===
      - alert: MySQLBufferPoolHitRateLow
        expr: >
          1 - (
            rate(mysql_global_status_innodb_buffer_pool_reads[5m]) /
            rate(mysql_global_status_innodb_buffer_pool_read_requests[5m])
          ) < 0.99
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Buffer Pool 命中率低于 99%: {{ $value | humanizePercentage }}"

      - alert: MySQLInnoDBRowLockWaits
        expr: rate(mysql_global_status_innodb_row_lock_waits[5m]) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "行锁等待次数过多: {{ $value }}/s"

      # === 系统资源告警 ===
      - alert: MySQLDiskUsageHigh
        expr: >
          (node_filesystem_size_bytes{mountpoint="/var/lib/mysql"} -
           node_filesystem_avail_bytes{mountpoint="/var/lib/mysql"}) /
          node_filesystem_size_bytes{mountpoint="/var/lib/mysql"} > 0.85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "MySQL 数据目录磁盘使用率超过 85%"
```

#### 9.4 DBA vs SRE 职责边界

```
┌──────────────────────────────────────────────────────────────────┐
│              DBA vs SRE 职责边界                                  │
├─────────────────────────────┬────────────────────────────────────┤
│         DBA 职责            │          SRE 职责                  │
├─────────────────────────────┼────────────────────────────────────┤
│ 数据库架构设计              │ 可用性架构设计（HA、DR）           │
│ SQL 优化和索引设计          │ 性能监控和告警体系                 │
│ 数据建模和范式化            │ 容量规划和扩展策略                 │
│ 存储过程/触发器开发         │ 自动化运维工具开发                 │
│ 数据迁移和版本升级          │ 备份验证和恢复演练                 │
│ 数据安全和审计              │ 故障响应和 RCA                    │
│ 专用的性能调优              │ SLI/SLO 定义和监控                │
│ 数据库权限管理              │ 变更管理和风险评估                 │
│ 表结构变更 (DDL)            │ 自动化部署和配置管理               │
│ 慢查询分析和优化建议        │ 告警规则和值班流程                 │
├─────────────────────────────┼────────────────────────────────────┤
│  交集区域（协作区）：                                              │
│  - 备份策略制定和执行                                            │
│  - 高可用方案选型和实施                                          │
│  - 性能瓶颈定位和解决                                            │
│  - 容量评估和扩容                                                │
│  - 故障应急和恢复                                                │
└──────────────────────────────────────────────────────────────────┘
```

---

### 10. SRE 实战案例

#### 10.1 案例：主从延迟导致数据不一致

**现象：**
- 用户在主库下单成功后，立即查询订单状态显示"未找到"
- 读写分离架构，写走主库，读走从库
- 从库延迟持续增长，从 1 秒增长到 30 秒

**诊断过程：**

```sql
-- Step 1: 检查复制状态
SHOW SLAVE STATUS\G
-- Seconds_Behind_Master: 30
-- Slave_IO_Running: Yes
-- Slave_SQL_Running: Yes

-- Step 2: 检查是否有大事务
-- 在主库上查看
SHOW FULL PROCESSLIST;
-- 发现一个 UPDATE 正在执行：UPDATE orders SET status=2 WHERE ...（已执行 45 秒）

-- Step 3: 检查从库的 relay log 处理情况
SHOW SLAVE STATUS\G
-- Relay_Log_Space: 5GB  ← relay log 堆积严重
-- 确认是大事务导致 SQL Thread 单线程重放成为瓶颈
```

**根因：** 一个批量 UPDATE 操作（更新 100 万行）在主库上执行了 45 秒，由于从库 SQL Thread 是单线程重放，导致复制延迟持续增长。

**修复：**

```sql
-- 紧急修复：开启并行复制
SET GLOBAL slave_parallel_type = 'LOGICAL_CLOCK';
SET GLOBAL slave_parallel_workers = 8;
STOP SLAVE SQL_THREAD;
START SLAVE SQL_THREAD;

-- 验证延迟是否下降
SHOW SLAVE STATUS\G

-- 应用层临时方案：关键读走主库
-- 在代码中添加逻辑：
-- 写操作后的第一次读 → 走主库
-- 其他读 → 走从库
```

**长期预防：**
1. 开启并行复制（`slave_parallel_workers=8`）
2. 限制大事务的执行，分批处理（每批 1000 行）
3. 监控复制延迟，超过 5 秒告警
4. 应用层实现写后读一致性（sticky read）

#### 10.2 案例：误删数据的紧急恢复

**现象：**
- 15:30 开发人员误执行 `DELETE FROM users WHERE 1=1`
- 删除了用户表的全部数据（200 万行）
- 用户投诉无法登录

**紧急恢复流程：**

```bash
# Step 1: 立即停止应用写入（避免新数据与恢复冲突）
# 通知开发停止服务或切到维护模式

# Step 2: 确认误操作的时间点和位置
mysqlbinlog --base64-output=DECODE-ROWS -v \
    --start-datetime="2026-05-03 15:25:00" \
    --stop-datetime="2026-05-03 15:35:00" \
    /var/log/mysql/binlog.000005 | grep -B10 "DELETE FROM users"

# 找到：# at 54321
# 确认误操作 GTID：3e11fa47:12345

# Step 3: 使用 xtrabackup 全量备份 + binlog 恢复
# 恢复全量备份到临时实例（同 7.2 节步骤）

# Step 4: 重放 binlog 到误操作前
mysqlbinlog \
    --stop-position=54320 \
    /var/log/mysql/binlog.000004 /var/log/mysql/binlog.000005 | \
    mysql -h 127.0.0.1 -P 3307 -u root -ptemppass

# Step 5: 验证恢复数据
mysql -h 127.0.0.1 -P 3307 -u root -ptemppass -e "
    SELECT COUNT(*) FROM sre_lab.users;  -- 应该有 200 万行
"

# Step 6: 将恢复的数据导出并导入到生产库
mysqldump -h 127.0.0.1 -P 3307 -u root -ptemppass \
    --single-transaction --no-create-info sre_lab users > /tmp/users_data.sql

# 在生产库上导入
mysql -u root -p sre_lab < /tmp/users_data.sql

# Step 7: 恢复应用服务，验证业务正常
```

**事后改进：**
1. 配置 `sql_safe_updates=ON`，防止没有 WHERE 条件的 DELETE/UPDATE
2. 应用层使用不同权限：读写账号和只读账号分离
3. 关键表启用触发器记录删除日志
4. 建立备份恢复演练制度，每月执行一次 PITR 演练

---

## 💻 实战练习

### 练习 1：搭建 GTID 主从复制

```bash
# 准备两个 MySQL 实例（使用 Docker）
# Master
docker run -d --name mysql-master \
    -e MYSQL_ROOT_PASSWORD=master_pass \
    -p 3306:3306 \
    -v /tmp/master.cnf:/etc/mysql/conf.d/custom.cnf \
    mysql:8.0

# Slave
docker run -d --name mysql-slave \
    -e MYSQL_ROOT_PASSWORD=slave_pass \
    -p 3307:3306 \
    -v /tmp/slave.cnf:/etc/mysql/conf.d/custom.cnf \
    mysql:8.0
```

```ini
# /tmp/master.cnf
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog_format = ROW
gtid_mode = ON
enforce_gtid_consistency = ON
sync_binlog = 1
innodb_flush_log_at_trx_commit = 1
```

```ini
# /tmp/slave.cnf
[mysqld]
server-id = 2
log-bin = mysql-bin
relay-log = relay-bin
log_slave_updates = ON
read_only = ON
gtid_mode = ON
enforce_gtid_consistency = ON
```

```sql
-- 在 Master 上创建复制用户
docker exec mysql-master mysql -u root -pmaster_pass -e "
CREATE USER 'repl'@'%' IDENTIFIED BY 'ReplPass123!';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';
FLUSH PRIVILEGES;
"

-- 在 Slave 上配置复制
docker exec mysql-slave mysql -u root -pslave_pass -e "
CHANGE MASTER TO
    MASTER_HOST='mysql-master',
    MASTER_PORT=3306,
    MASTER_USER='repl',
    MASTER_PASSWORD='ReplPass123!',
    MASTER_AUTO_POSITION=1;
START SLAVE;
"

-- 验证复制状态
docker exec mysql-slave mysql -u root -pslave_pass -e "SHOW SLAVE STATUS\G"

-- 测试复制
docker exec mysql-master mysql -u root -pmaster_pass -e "
CREATE DATABASE sre_test;
USE sre_test;
CREATE TABLE test (id INT PRIMARY KEY AUTO_INCREMENT, val VARCHAR(50));
INSERT INTO test (val) VALUES ('hello'), ('world');
"

-- 在 Slave 上验证
docker exec mysql-slave mysql -u root -pslave_pass -e "
SELECT * FROM sre_test.test;
"
```

### 练习 2：mysqldump 备份与恢复

```bash
# 准备测试数据
docker exec mysql-master mysql -u root -pmaster_pass -e "
USE sre_test;
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50),
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO users (name, email) VALUES
    ('Alice', 'alice@example.com'),
    ('Bob', 'bob@example.com'),
    ('Carol', 'carol@example.com');
"

# 全量备份
docker exec mysql-master mysqldump -u root -pmaster_pass \
    --single-transaction \
    --set-gtid-purged=OFF \
    sre_test > /tmp/sre_test_backup.sql

# 模拟数据丢失
docker exec mysql-master mysql -u root -pmaster_pass -e "
DELETE FROM sre_test.users WHERE id = 2;
"

# 验证数据丢失
docker exec mysql-master mysql -u root -pmaster_pass -e "SELECT * FROM sre_test.users;"

# 恢复备份
docker exec -i mysql-master mysql -u root -pmaster_pass sre_test < /tmp/sre_test_backup.sql

# 验证恢复结果
docker exec mysql-master mysql -u root -pmaster_pass -e "SELECT * FROM sre_test.users;"
-- Bob 应该回来了
```

### 练习 3：PITR 恢复演练

```bash
# 准备：确保 binlog 开启
docker exec mysql-master mysql -u root -pmaster_pass -e "
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
"

# 记录当前时间
T1=$(date '+%Y-%m-%d %H:%M:%S')
echo "T1 (恢复目标时间点): $T1"

# 插入正常数据
docker exec mysql-master mysql -u root -pmaster_pass -e "
INSERT INTO sre_test.users (name, email) VALUES ('Dave', 'dave@example.com');
INSERT INTO sre_test.users (name, email) VALUES ('Eve', 'eve@example.com');
"

sleep 2

# 模拟误操作
T2=$(date '+%Y-%m-%d %H:%M:%S')
echo "T2 (误操作时间点): $T2"

docker exec mysql-master mysql -u root -pmaster_pass -e "
DELETE FROM sre_test.users;
"

# 验证数据已被删除
docker exec mysql-master mysql -u root -pmaster_pass -e "SELECT * FROM sre_test.users;"

# 使用 binlog 进行 PITR 恢复
# 找到 binlog 文件
docker exec mysql-master mysql -u root -pmaster_pass -e "SHOW BINARY LOGS;"

# 解析 binlog 找到误操作位置
docker exec mysql-master mysqlbinlog \
    --base64-output=DECODE-ROWS -v \
    --start-datetime="$T1" \
    --stop-datetime="$T2" \
    /var/lib/mysql/binlog.000001 2>/dev/null | tail -20

# 恢复到误操作前
docker exec mysql-master mysqlbinlog \
    --start-datetime="$T1" \
    --stop-datetime="$T2" \
    /var/lib/mysql/binlog.000001 | \
    docker exec -i mysql-master mysql -u root -pmaster_pass

# 验证恢复结果
docker exec mysql-master mysql -u root -pmaster_pass -e "SELECT * FROM sre_test.users;"
```

---

## 🎯 面试题精选

### 1. MySQL 主从复制的原理是什么？

**参考答案：**
MySQL 复制基于 binlog，分为三个步骤：
1. **Master** 将数据变更记录到 binlog
2. **Slave 的 I/O Thread** 连接 Master 的 Binlog Dump Thread，接收 binlog events 并写入本地 Relay Log
3. **Slave 的 SQL Thread** 读取 Relay Log，重放 SQL 语句

关键点：binlog 是复制的基础，复制是异步的（默认），可能存在延迟。

### 2. GTID 复制相比传统复制有什么优势？

**参考答案：**
1. **简化故障转移**：自动找到正确的复制位置，无需手动计算 binlog position
2. **自动跳过重复事务**：通过 GTID 集合判断事务是否已执行
3. **方便搭建复杂拓扑**：级联复制、多源复制更容易管理
4. **数据一致性保障**：可以在切换时验证主从数据是否一致
5. **与 Orchestrator 等工具集成更好**

### 3. 半同步复制是如何工作的？和异步复制有什么区别？

**参考答案：**
- **异步复制**：Master 提交后不等 Slave 确认，直接返回成功。风险是 Master 崩溃时可能丢失数据
- **半同步复制**：Master 提交后等待至少一个 Slave 确认收到 binlog 才返回成功。保证了至少一个 Slave 有最新数据
- **AFTER_SYNC vs AFTER_COMMIT**：AFTER_SYNC（MySQL 5.7 默认）在存储引擎提交前等待 Slave 确认，避免了不一致窗口

### 4. mysqldump 和 xtrabackup 的区别？各自适用什么场景？

**参考答案：**

| 对比项 | mysqldump | xtrabackup |
|--------|-----------|------------|
| 备份方式 | 逻辑备份（SQL 语句） | 物理备份（数据文件） |
| 备份速度 | 慢（大库需要小时级） | 快（并行压缩） |
| 恢复速度 | 慢（执行 SQL） | 快（直接复制文件） |
| 锁影响 | 需要 FTWRL | 不锁表（热备） |
| 选择性恢复 | 可选择单表 | 需要额外操作 |
| 增量备份 | 不支持（需配合 binlog） | 支持（增量页级别） |

**SRE 选择建议**：生产环境使用 xtrabackup，开发/测试环境可用 mysqldump

### 5. 如何实现 MySQL 的时间点恢复 (PITR)？

**参考答案：**
1. 恢复最近的全量备份（mysqldump 或 xtrabackup）
2. 使用 `mysqlbinlog` 工具重放 binlog 到指定时间点
3. 可以按时间（`--stop-datetime`）或按位置（`--stop-position`）或按 GTID（`--exclude-gtids`）精确恢复
4. 关键前提：binlog 必须保留足够长时间（`expire_logs_days` 配置合理）

### 6. MHA、Orchestrator、InnoDB Cluster 分别适用于什么场景？

**参考答案：**
- **MHA**：传统方案，基于 binlog position 补齐数据。适合对一致性要求不那么高的场景。社区维护减少
- **Orchestrator**：功能最全面，支持复杂拓扑，Web UI 管理。适合中大型企业。社区活跃
- **InnoDB Cluster**：MySQL 官方方案，基于 Group Replication（Paxos 协议），强一致性。适合核心业务和金融场景

### 7. 如何监控 MySQL 的复制健康状态？

**参考答案：**
1. **核心指标**：`Seconds_Behind_Master`（延迟）、`Slave_IO_Running`、`Slave_SQL_Running`
2. **高级指标**：`Relay_Log_Space`（堆积）、GTID 差距、并行复制 Worker 状态
3. **监控工具**：mysqld_exporter + Prometheus + Grafana
4. **告警策略**：延迟 >5s 告警、>30s 严重、复制线程停止立即告警
5. **定期验证**：对比主从数据一致性（pt-table-checksum）

### 8. 备份策略如何设计？保留多久？如何验证备份有效性？

**参考答案：**
- **策略**：每日全量 + binlog 增量。核心业务每 6 小时全量
- **保留**：本地保留 7 天，异地/对象存储保留 30 天
- **验证**：
  1. 每周自动恢复到临时实例
  2. 执行数据完整性检查（表行数、校验和）
  3. 记录恢复耗时，评估是否满足 RTO
  4. 每月进行一次完整的恢复演练

### 9. 什么是 RPO 和 RTO？如何根据业务确定？

**参考答案：**
- **RPO (Recovery Point Objective)**：允许丢失多长时间的数据
  - RPO=0：不允许丢失数据（需要同步复制 + 本地备份）
  - RPO=1h：允许丢失 1 小时数据（每小时备份）
- **RTO (Recovery Time Objective)**：允许多长时间恢复服务
  - RTO=0：秒级切换（需要自动故障转移）
  - RTO=4h：允许 4 小时恢复（可以手动恢复）

不同业务的 RPO/RTO：
| 业务级别 | RPO | RTO | 方案 |
|---------|-----|-----|------|
| 金融核心 | 0 | <1min | InnoDB Cluster + 同步复制 |
| 电商交易 | <1min | <5min | 半同步 + Orchestrator |
| 一般业务 | <1h | <1h | 异步复制 + 定时备份 |
| 日志分析 | <24h | <4h | 每日备份即可 |

### 10. 如何处理主从复制中断？

**参考答案：**

排查步骤：
1. `SHOW SLAVE STATUS\G` 查看 `Last_IO_Error` 和 `Last_SQL_Error`
2. 常见原因和处理：
   - **主键冲突**：跳过冲突事务（`SET GLOBAL sql_slave_skip_counter=1`）或使用 GTID 跳过
   - **表不存在**：在从库创建缺失的表
   - **网络中断**：检查网络连通性，修复后 `START SLAVE`
   - **数据不一致**：使用 `pt-table-sync` 修复数据差异
3. 长期方案：使用 GTID 复制自动处理、监控告警及时发现

---

## 📚 深入阅读

### 官方文档
- MySQL 8.0 Replication: https://dev.mysql.com/doc/refman/8.0/en/replication.html
- MySQL 8.0 Group Replication: https://dev.mysql.com/doc/refman/8.0/en/group-replication.html
- MySQL 8.0 InnoDB Cluster: https://dev.mysql.com/doc/refman/8.0/en/mysql-innodb-cluster.html
- MySQL 8.0 Backup and Recovery: https://dev.mysql.com/doc/refman/8.0/en/backup-and-recovery.html
- Percona XtraBackup: https://docs.percona.com/percona-xtrabackup/8.0/

### 推荐书籍
- 《MySQL 技术内幕：InnoDB 存储引擎》— 姜承尧
- 《高性能 MySQL（第 4 版）》— 复制与备份章节
- 《MySQL 管理之道》— 贺春旸

### 工具
- Orchestrator: https://github.com/openark/orchestrator
- Percona Toolkit: https://www.percona.com/software/database-tools/percona-toolkit
- pt-table-checksum: 主从数据一致性检查
- pt-table-sync: 主从数据修复
- gh-ost: 在线 DDL 工具

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出主从复制的完整流程（binlog dump → I/O thread → relay log → SQL thread）
- [ ] 能解释 GTID 复制的优势和工作原理
- [ ] 能解释半同步复制和异步复制的区别及 AFTER_SYNC 的优势
- [ ] 能对比 MHA、Orchestrator、InnoDB Cluster 的适用场景
- [ ] 能解释 PITR 的原理和操作步骤
- [ ] 能区分 mysqldump 和 xtrabackup 的优缺点
- [ ] 能说出 DBA 和 SRE 在数据库运维中的职责边界

### 实操检查点
- [ ] 能独立搭建基于 GTID 的主从复制环境
- [ ] 能使用 mysqldump 和 xtrabackup 进行全量和增量备份
- [ ] 能使用 binlog 执行时间点恢复 (PITR)
- [ ] 能配置 mysqld_exporter + Prometheus 监控 MySQL
- [ ] 能编写和部署 MySQL 告警规则
- [ ] 能编写自动备份脚本

### 能力验证标准
- [ ] 独立完成一次完整的 PITR 恢复演练（从备份恢复到指定时间点）
- [ ] 搭建一个包含自动监控和告警的 MySQL 高可用环境
- [ ] 能为一个新业务制定完整的 MySQL 备份策略和高可用方案
