# Day 74: Redis 高可用与集群

> 📅 日期：2026-05-03
> 📖 学习主题：主从复制、Sentinel 哨兵、Redis Cluster、数据分片、故障转移、扩容缩容、监控指标
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 73 (Redis 运维基础)

---

## 🎯 学习目标

完成 Day 74 的学习后，你应该掌握：
- 理解 Redis 主从复制的原理（全量同步与增量同步）
- 能够部署和配置 Redis Sentinel 高可用方案
- 掌握 Redis Cluster 的数据分片原理（hash slot）和故障转移机制
- 能够完成 Redis Cluster 的扩容和缩容操作
- 熟悉 Redis 核心监控指标和告警策略

---

## 📖 核心知识点

### 1. Redis 高可用架构全景

```
┌─────────────────────────────────────────────────────────────────┐
│                    Redis 高可用架构对比                          │
│                                                                 │
│  方案            │ 数据分片 │ 自动故障转移 │ 复杂度 │ 适用规模    │
│  ────────────────┼──────────┼──────────────┼────────┼────────── │
│  主从复制         │ 不支持   │ 不支持       │ 低     │ 小规模     │
│  Sentinel 哨兵    │ 不支持   │ 支持         │ 中     │ 中规模     │
│  Redis Cluster   │ 支持     │ 支持         │ 高     │ 大规模     │
│  代理层(Twemproxy)│ 支持     │ 不支持       │ 中     │ 中大规模   │
└─────────────────────────────────────────────────────────────────┘

SRE 选型建议：
  - 数据量 < 16GB, QPS < 10万 → Sentinel
  - 数据量 > 16GB, QPS > 10万 → Redis Cluster
  - 需要跨数据中心 → Redis Enterprise 或 自建代理层
```

---

### 2. 主从复制（Replication）

主从复制是 Redis 高可用的基础。从节点复制主节点数据，提供读扩展和数据冗余。

#### 2.1 主从复制架构

```
┌───────────────────────────────────────────────────────────┐
│                    主从复制架构                             │
│                                                           │
│              ┌──────────────┐                             │
│              │   Master     │                             │
│              │   :6379      │                             │
│              │   读 + 写     │                             │
│              └──────┬───────┘                             │
│                     │                                     │
│         ┌───────────┼───────────┐                         │
│         │           │           │                         │
│   ┌─────▼─────┐ ┌──▼──────┐ ┌──▼──────┐                 │
│   │  Slave 1  │ │ Slave 2 │ │ Slave 3 │                 │
│   │  :6379    │ │ :6379   │ │ :6379   │                 │
│   │  只读      │ │ 只读    │ │ 只读     │                 │
│   └───────────┘ └─────────┘ └─────────┘                 │
│                                                           │
│   写请求 ──▶ Master                                       │
│   读请求 ──▶ Slave（可配置读写分离）                        │
└───────────────────────────────────────────────────────────┘
```

#### 2.2 全量同步（Full Sync）

```
全量同步流程（首次连接或复制偏移量不匹配时触发）：

  Slave                              Master
    │                                   │
    │  1. SLAVEOF / REPLICAOF           │
    │  ──────────────────────────────▶  │
    │                                   │
    │  2. MASTER runid + offset 检查     │
    │  ◀──────────────────────────────  │
    │     (返回 FULLRESYNC)             │
    │                                   │
    │  3. BGSAVE                        │
    │     Master fork 子进程生成 RDB     │
    │                                   │
    │  4. RDB 文件传输                   │
    │  ◀──────────────────────────────  │
    │                                   │
    │  5. Slave 加载 RDB               │
    │     (期间 Master 新写入缓存在      │
    │      repl_backlog_buffer)         │
    │                                   │
    │  6. 发送缓冲区中的增量命令          │
    │  ◀──────────────────────────────  │
    │                                   │
    │  7. 同步完成，进入增量同步          │
    │                                   │
```

**全量同步的开销：**
- Master：fork() 子进程 + RDB 传输（COW 内存翻倍风险）
- Slave：清空旧数据 + 加载 RDB（阻塞期间无法服务）
- 网络：RDB 文件传输占用带宽

#### 2.3 增量同步（Partial Sync）

```
增量同步流程（断线重连时优先尝试）：

  Slave                              Master
    │                                   │
    │  1. 断线重连                       │
    │  ──────────────────────────────▶  │
    │     PSYNC runid offset            │
    │                                   │
    │  2. 检查 repl_backlog_buffer      │
    │     offset 是否还在缓冲区内        │
    │                                   │
    │  情况 A: offset 在缓冲区内         │
    │  ◀── CONTINUE + 增量数据 ───────  │  ✅ 增量同步
    │                                   │
    │  情况 B: offset 已不在缓冲区       │
    │  ◀── FULLRESYNC ───────────────  │  ❌ 降级为全量同步
    │                                   │

repl_backlog_buffer 大小配置：
  repl-backlog-size 256mb    # 越大，断线后增量同步成功率越高
  repl-backlog-ttl 3600      # 没有 Slave 时保留缓冲区的时间（秒）
```

#### 2.4 主从配置

```bash
# Master 配置（redis.conf）
bind 0.0.0.0
port 6379
requirepass "strong_password"
masterauth "strong_password"           # 从节点连接密码

# Slave 配置（redis.conf）
replicaof 10.0.1.10 6379              # 指向 Master
masterauth "strong_password"           # Master 密码
replica-read-only yes                  # 从节点只读（推荐）
replica-serve-stale-data yes           # 同步期间是否响应读请求
```

```redis
-- 动态设置主从关系（运行时）
REPLICAOF 10.0.1.10 6379
CONFIG SET masterauth "strong_password"

-- 取消主从关系
REPLICAOF NO ONE

-- 查看复制状态
INFO replication

# role:slave
# master_host:10.0.1.10
# master_port:6379
# master_link_status:up
# master_last_io_seconds_ago:1
# slave_repl_offset:123456789
# slave_read_only:1
```

#### 2.5 主从复制的注意事项

```
┌─────────────────────────────────────────────────────────────┐
│              主从复制注意事项                                 │
│                                                             │
│  1. 数据延迟                                                 │
│     └─ 异步复制，Slave 数据可能落后 Master                    │
│     └─ 监控 master_repl_offset - slave_repl_offset          │
│                                                             │
│  2. 数据丢失                                                 │
│     └─ Master 宕机时，未同步到 Slave 的数据会丢失             │
│     └─ Master 写入成功 → 返回客户端 → 还未同步 → Master 宕机  │
│     └─ 解决：WAIT 命令同步等待确认                            │
│                                                             │
│  3. 复制风暴                                                 │
│     └─ 多个 Slave 同时向 Master 全量同步                     │
│     └─ 解决：Slave 从 Slave 复制（级联复制）                  │
│     └─ Master → Slave1 → Slave2, Slave3                    │
│                                                             │
│  4. 从节点数量                                               │
│     └─ 单个 Master 建议不超过 10 个 Slave                    │
│     └─ 更多从节点用级联复制                                  │
└─────────────────────────────────────────────────────────────┘
```

---

### 3. Redis Sentinel（哨兵）

Sentinel 是 Redis 的高可用方案，自动监控、故障转移和通知。

#### 3.1 Sentinel 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sentinel 高可用架构                            │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Sentinel 1  │  │  Sentinel 2  │  │  Sentinel 3  │          │
│  │  :26379      │  │  :26379      │  │  :26379      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         │    gossip 协议互相通信             │                   │
│         │    ──────────────────────────────▶│                   │
│         │                                   │                   │
│         └───────────────┬───────────────────┘                   │
│                         │ 监控                                   │
│         ┌───────────────┼───────────────┐                       │
│         │               │               │                       │
│   ┌─────▼──────┐  ┌────▼──────┐  ┌─────▼──────┐               │
│   │  Master    │  │  Slave 1  │  │  Slave 2   │               │
│   │  :6379     │──│  :6379    │──│  :6379     │               │
│   │  (当前主)   │  │  (从)     │  │  (从)      │               │
│   └────────────┘  └───────────┘  └────────────┘               │
│                                                                 │
│   故障转移后：                                                   │
│   Slave 1 提升为新 Master，Slave 2 指向新 Master                 │
│   Sentinel 通知客户端新 Master 地址                              │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Sentinel 工作原理

**主观下线（SDOWN）与客观下线（ODOWN）：**

```
故障检测流程：

  Sentinel 1                Master                Sentinel 2
      │                        │                       │
      │  PING ────────────────▶│                       │
      │                        │                       │
      │  (超时未响应)           │                       │
      │                        │                       │
      │  标记 Master SDOWN     │                       │
      │  (主观下线)             │                       │
      │                        │                       │
      │  询问其他 Sentinel      │                       │
      │  ─────────────────────────────────────────────▶│
      │                        │        PING ──────────│
      │                        │◀── (也超时) ──────────│
      │                        │                       │
      │                        │    标记 Master SDOWN   │
      │                        │                       │
      │  ◀─── SDOWN 确认 ──────────────────────────────│
      │                        │                       │
      │  达到 quorum 数量       │                       │
      │  Master 标记 ODOWN     │                       │
      │  (客观下线)             │                       │
      │                        │                       │
      │  开始故障转移选举       │                       │
```

**Leader 选举（Raft 算法）：**

```
Sentinel Leader 选举：

  1. 发现 Master ODOWN 后，Sentinel 们开始选举 Leader
  2. 每个 Sentinel 向其他 Sentinel 发送投票请求
  3. 每个 Sentinel 只投一票（先到先得）
  4. 获得多数票的 Sentinel 成为 Leader
  5. Leader 负责执行故障转移

  Sentinel 1 ──投票请求──▶ Sentinel 2  (Sentinel 2 投给 1)
  Sentinel 1 ──投票请求──▶ Sentinel 3  (Sentinel 3 投给 1)
  Sentinel 2 ──投票请求──▶ Sentinel 1  (已投给 1，拒绝)
  Sentinel 2 ──投票请求──▶ Sentinel 3  (已投给 1，拒绝)

  结果：Sentinel 1 获得 2 票，成为 Leader
```

**故障转移流程：**

```
故障转移完整流程：

  Leader Sentinel
      │
      ├─ 1. 选择新 Master（优先级 → offset → runid）
      │     优先级：slave-priority 值最小的
      │     offset：复制偏移量最大的（数据最新）
      │     runid：最小的（兜底）
      │
      ├─ 2. 对选中的 Slave 执行 REPLICAOF NO ONE
      │     （提升为 Master）
      │
      ├─ 3. 对其他 Slave 执行 REPLICAOF 新MasterIP 新MasterPort
      │     （指向新 Master）
      │
      ├─ 4. 更新 Sentinel 自身的配置
      │     （记录新 Master 地址）
      │
      └─ 5. 通知客户端
            （Pub/Sub 发布新 Master 地址）
```

#### 3.3 Sentinel 部署配置

```bash
# sentinel.conf（三个 Sentinel 节点配置相同）

# 监控 Master
sentinel monitor mymaster 10.0.1.10 6379 2
# mymaster: Master 名称
# 10.0.1.10 6379: Master 地址
# 2: quorum（至少 2 个 Sentinel 同意才判定 ODOWN）

# Master 密码
sentinel auth-pass mymaster strong_password

# 故障检测超时
sentinel down-after-milliseconds mymaster 5000
# 5 秒无响应标记 SDOWN

# 故障转移超时
sentinel failover-timeout mymaster 60000
# 故障转移超过 60 秒视为失败

# 同步 Slave 数量
sentinel parallel-syncs mymaster 1
# 故障转移后，每次同步 1 个 Slave（避免全部阻塞）

# 日志
sentinel announce-ip 10.0.1.11       # 容器/NAT 环境需要
sentinel announce-port 26379
```

```bash
# 启动 Sentinel
redis-sentinel /etc/redis/sentinel.conf
# 或
redis-server /etc/redis/sentinel.conf --sentinel

# 完整部署示例（3 节点）
# 节点 1: 10.0.1.11 (Sentinel + Slave)
# 节点 2: 10.0.1.12 (Sentinel + Slave)
# 节点 3: 10.0.1.10 (Sentinel + Master)
```

#### 3.4 Sentinel 操作命令

```redis
-- 连接 Sentinel
redis-cli -p 26379

-- 查看 Master 信息
SENTINEL master mymaster

-- 查看所有 Slave
SENTINEL replicas mymaster

-- 查看所有 Sentinel
SENTINEL sentinels mymaster

-- 获取 Master 地址
SENTINEL get-master-addr-by-name mymaster

-- 模拟故障转移（手动触发）
SENTINEL failover mymaster

-- 重置 Sentinel 配置
SENTINEL reset mymaster

-- 检查 Master 是否可达
SENTINEL is-master-down-by-addr mymaster 10.0.1.10 6379
```

#### 3.5 Sentinel 客户端连接

```python
# Python: 使用 redis-py 连接 Sentinel
from redis.sentinel import Sentinel

sentinel = Sentinel([
    ('10.0.1.11', 26379),
    ('10.0.1.12', 26379),
    ('10.0.1.13', 26379),
], socket_timeout=0.5)

# 获取 Master（自动故障转移）
master = sentinel.master_for('mymaster', password='strong_password')
master.set('key', 'value')

# 获取 Slave（读请求）
slave = sentinel.slave_for('mymaster', password='strong_password')
value = slave.get('key')
```

```go
// Go: 使用 go-redis 连接 Sentinel
import "github.com/redis/go-redis/v9"

rdb := redis.NewFailoverClient(&redis.FailoverOptions{
    MasterName:    "mymaster",
    SentinelAddrs: []string{"10.0.1.11:26379", "10.0.1.12:26379", "10.0.1.13:26379"},
    Password:      "strong_password",
    SentinelPassword: "sentinel_password",
})
```

---

### 4. Redis Cluster（分片集群）

Redis Cluster 是 Redis 官方的分布式方案，支持数据分片和自动故障转移。

#### 4.1 Cluster 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Redis Cluster 架构                            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Master A   │  │  Master B   │  │  Master C   │            │
│  │  Slot 0-5460│  │Slot 5461-   │  │Slot 10923-  │            │
│  │             │  │    10922    │  │    16383    │            │
│  │  10.0.1.10  │  │  10.0.1.11  │  │  10.0.1.12  │            │
│  │  :7000      │  │  :7000      │  │  :7000      │            │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│         │                │                │                     │
│         │ Gossip 协议     │                │                     │
│         │ ───────────────▶│                │                     │
│         │                │────────────────│                     │
│         │                │                │                     │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐            │
│  │  Slave A'   │  │  Slave B'   │  │  Slave C'   │            │
│  │  10.0.1.13  │  │  10.0.1.14  │  │  10.0.1.15  │            │
│  │  :7000      │  │  :7000      │  │  :7000      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  16384 个 Hash Slot 分布在 3 个 Master 上                        │
│  每个 Master 有一个 Slave 作为备份                               │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.2 数据分片：Hash Slot 原理

```
Hash Slot 分片机制：

  Key ──▶ CRC16(key) ──▶ CRC16(key) % 16384 ──▶ Slot 编号

  例子：
    CRC16("user:1001") % 16384 = 5649   → Master B
    CRC16("order:2001") % 16384 = 12038  → Master C
    CRC16("product:3001") % 16384 = 1023 → Master A

  ┌──────────────────────────────────────────────────────┐
  │  Slot 分配：                                          │
  │  Master A: [0, 5460]       → 5461 个 slot (33.3%)    │
  │  Master B: [5461, 10922]   → 5462 个 slot (33.3%)    │
  │  Master C: [10923, 16383]  → 5461 个 slot (33.3%)    │
  │  总计: 16384 个 slot                                  │
  └──────────────────────────────────────────────────────┘
```

**Hash Tag —— 强制相关 Key 在同一节点：**

```
Hash Tag 规则：
  Key 中 {} 内的部分用于计算 hash slot

  例子：
    {user:1001}:profile   ──▶ CRC16("user:1001") % 16384 = 5649
    {user:1001}:orders    ──▶ CRC16("user:1001") % 16384 = 5649
    {user:1001}:sessions  ──▶ CRC16("user:1001") % 16384 = 5649

  三个 Key 都在同一个 slot，可以使用 MGET、事务、Lua 脚本

  ⚠️ 但是可能导致数据倾斜！
  如果某个 Hash Tag 下数据量很大，对应的节点会成为热点。
```

#### 4.3 Cluster 节点通信：Gossip 协议

```
Gossip 协议通信机制：

  ┌─────────┐           ┌─────────┐           ┌─────────┐
  │ Node A  │◀─────────▶│ Node B  │◀─────────▶│ Node C  │
  └─────────┘           └─────────┘           └─────────┘

  每个节点定期（每秒）随机选择几个节点发送消息：

  消息类型：
  ┌──────────────┬──────────────────────────────────┐
  │ MEET          │ 新节点加入集群                    │
  │ PING          │ 心跳检测（附带节点状态信息）       │
  │ PONG          │ PING 的响应                      │
  │ FAIL          │ 广播节点故障信息                  │
  └──────────────┴──────────────────────────────────┘

  集群状态传播：
  1. Node A 发现 Node B 不可达
  2. Node A 将 Node B 标记为 PFAIL（疑似下线）
  3. 其他节点也标记 PFAIL
  4. 超过半数 Master 标记 PFAIL → FAIL（确认下线）
  5. 广播 FAIL 消息，开始故障转移
```

#### 4.4 Cluster 故障转移

```
Cluster 故障转移流程：

  Master B 宕机
       │
       ▼
  Slave B' 检测到 Master B 失联
  (超过 cluster-node-timeout)
       │
       ▼
  Slave B' 向所有 Master 发起投票
  (要求成为新 Master)
       │
       ▼
  Master A, Master C 投票
  (每个 Master 只投一票，多数票通过)
       │
       ▼
  Slave B' 提升为新 Master
  接管 Master B 的所有 slot
       │
       ▼
  集群恢复正常
  (如果原 Master B 恢复，自动降级为 Slave)
```

#### 4.5 Cluster 部署

```bash
# 准备 6 个节点配置（3 主 3 从）
for port in 7001 7002 7003 7004 7005 7006; do
    mkdir -p /tmp/redis-cluster/$port
    cat > /tmp/redis-cluster/$port/redis.conf << EOF
port $port
cluster-enabled yes
cluster-config-file nodes-$port.conf
cluster-node-timeout 5000
appendonly yes
appendfilename "appendonly-$port.aof"
dbfilename dump-$port.rdb
dir /tmp/redis-cluster/$port
bind 0.0.0.0
protected-mode no
EOF
done

# 启动 6 个节点
for port in 7001 7002 7003 7004 7005 7006; do
    redis-server /tmp/redis-cluster/$port/redis.conf --daemonize yes
done

# 创建集群（Redis 5.0+）
redis-cli --cluster create \
    127.0.0.1:7001 127.0.0.1:7002 127.0.0.1:7003 \
    127.0.0.1:7004 127.0.0.1:7005 127.0.0.1:7006 \
    --cluster-replicas 1

# --cluster-replicas 1: 每个 Master 有 1 个 Slave
# 自动分配 slot 和主从关系

# 验证集群状态
redis-cli -p 7001 CLUSTER INFO
redis-cli -p 7001 CLUSTER NODES
```

**集群操作命令：**

```redis
-- 查看集群信息
CLUSTER INFO

-- 查看集群节点
CLUSTER NODES

-- 查看 Key 所在 slot
CLUSTER KEYSLOT user:1001

-- 查看 slot 分配
CLUSTER SLOTS

-- 集群健康检查
redis-cli --cluster check 127.0.0.1:7001
```

#### 4.6 Cluster 扩容缩容

**添加节点（扩容）：**

```bash
# 1. 启动新节点
redis-server /tmp/redis-cluster/7007/redis.conf --daemonize yes

# 2. 将新节点加入集群
redis-cli --cluster add-node 127.0.0.1:7007 127.0.0.1:7001
# 7007: 新节点
# 7001: 集群中已有节点

# 3. 重新分配 slot（从现有节点迁移 slot 到新节点）
redis-cli --cluster reshard 127.0.0.1:7001
# 交互式选择迁移多少 slot、从哪个节点迁移

# 4. 添加 Slave（可选）
redis-server /tmp/redis-cluster/7008/redis.conf --daemonize yes
redis-cli --cluster add-node 127.0.0.1:7008 127.0.0.1:7001 \
    --cluster-slave --cluster-master-id <master-7007-node-id>

# 5. 验证
redis-cli --cluster check 127.0.0.1:7001
```

**删除节点（缩容）：**

```bash
# 1. 先迁移 slot 到其他节点
redis-cli --cluster reshard 127.0.0.1:7001
# 将要删除节点的 slot 全部迁出

# 2. 删除 Slave 节点
redis-cli --cluster del-node 127.0.0.1:7001 <slave-node-id>

# 3. 删除 Master 节点（确保 slot 已全部迁出）
redis-cli --cluster del-node 127.0.0.1:7001 <master-node-id>

# 4. 验证
redis-cli --cluster check 127.0.0.1:7001
```

**Slot 迁移原理：**

```
Slot 迁移过程（以 slot 100 从 A 迁移到 B 为例）：

  1. CLUSTER SETSLOT 100 MIGRATING <B-node-id>
     └─ A 标记 slot 100 为 MIGRATING 状态
     └─ 新请求如果 key 在 A 上，正常处理
     └─ 新请求如果 key 不在 A 上，返回 MOVED

  2. CLUSTER SETSLOT 100 IMPORTING <A-node-id>
     └─ B 标记 slot 100 为 IMPORTING 状态
     └─ 收到 slot 100 的请求，返回 ASK 重定向到 A

  3. CLUSTER GETKEYSINSLOT 100 100
     └─ 获取 slot 100 中的 key 列表

  4. MIGRATE <B-ip> <B-port> <key> 0 5000
     └─ 逐个迁移 key 到 B（原子操作）

  5. CLUSTER SETSLOT 100 NODE <B-node-id>
     └─ 所有节点更新 slot 100 的归属为 B
```

---

### 5. Redis Cluster 客户端路由

```
客户端路由协议：

  Client                  Node A                Node B
    │                        │                     │
    │  GET user:1001         │                     │
    │  (CRC16=5649 → B)     │                     │
    │  ─────────────────────▶│                     │
    │                        │                     │
    │  MOVED 5649 10.0.1.11:7000                   │
    │  ◀─────────────────────│                     │
    │                        │                     │
    │  GET user:1001         │                     │
    │  ───────────────────────────────────────────▶│
    │                        │                     │
    │  "zhangsan"            │                     │
    │  ◀───────────────────────────────────────────│
    │                        │                     │
    │  (Client 缓存 slot 映射)                      │
    │  后续 user:1001 直接访问 Node B                │

  MOVED: 永久重定向，Client 更新本地 slot 映射
  ASK:   临时重定向（slot 迁移中），Client 不更新映射
```

```python
# Python: redis-py 自动处理 Cluster 路由
from redis.cluster import RedisCluster

rc = RedisCluster(
    startup_nodes=[
        {"host": "10.0.1.10", "port": 7000},
        {"host": "10.0.1.11", "port": 7000},
        {"host": "10.0.1.12", "port": 7000},
    ],
    decode_responses=True,
    require_full_coverage=True,
)

# 自动路由到正确的节点
rc.set("user:1001", "zhangsan")
value = rc.get("user:1001")
```

---

### 6. Redis 监控指标

#### 6.1 核心监控指标

```
┌─────────────────────────────────────────────────────────────────┐
│                    Redis 核心监控指标                            │
│                                                                 │
│  类别          │ 指标                    │ 告警阈值             │
│  ─────────────┼────────────────────────┼───────────────────── │
│  内存          │ used_memory            │ > 80% maxmemory     │
│               │ mem_fragmentation_ratio │ > 1.5 或 < 1.0      │
│               │ evicted_keys           │ > 0                 │
│  ─────────────┼────────────────────────┼───────────────────── │
│  性能          │ instantaneous_ops_per_sec │ 业务基线的 2 倍    │
│               │ latency_percentiles    │ p99 > 5ms           │
│               │ blocked_clients        │ > 0                 │
│  ─────────────┼────────────────────────┼───────────────────── │
│  连接          │ connected_clients      │ > maxclients * 0.8  │
│               │ rejected_connections    │ > 0                 │
│  ─────────────┼────────────────────────┼───────────────────── │
│  持久化        │ rdb_last_bgsave_status │ != "ok"             │
│               │ aof_last_bgrewrite_status │ != "ok"           │
│               │ aof_last_write_status  │ != "ok"             │
│  ─────────────┼────────────────────────┼───────────────────── │
│  主从          │ master_link_status     │ != "up"             │
│               │ master_last_io_seconds_ago │ > 10             │
│               │ slave_repl_offset      │ 差值过大             │
│  ─────────────┼────────────────────────┼───────────────────── │
│  Cluster       │ cluster_state          │ != "ok"             │
│               │ cluster_slots_ok       │ != 16384            │
│               │ cluster_slots_pfail    │ > 0                 │
│               │ cluster_slots_fail     │ > 0                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.2 监控命令详解

```redis
-- 综合信息
INFO all                          -- 所有信息
INFO memory                       -- 内存信息
INFO stats                        -- 统计信息
INFO replication                  -- 复制信息
INFO clients                      -- 客户端信息
INFO keyspace                     -- 数据库键空间信息
INFO persistence                  -- 持久化信息
INFO cpu                          -- CPU 信息
INFO cluster                      -- 集群信息

-- 实时监控
MONITOR                           -- 实时打印所有命令（调试用，生产慎用！）
redis-cli --latency               -- 延迟测试
redis-cli --latency-history       -- 延迟历史
redis-cli --latency-dist          -- 延迟分布图
redis-cli --stat                  -- 实时统计

-- 慢查询日志
CONFIG SET slowlog-log-slower-than 10000  -- 超过 10ms 记录
CONFIG SET slowlog-max-len 128            -- 最多记录 128 条
SLOWLOG GET 10                            -- 查看最近 10 条慢查询
SLOWLOG LEN                               -- 慢查询日志条数
SLOWLOG RESET                             -- 清空慢查询日志
```

#### 6.3 Prometheus + Grafana 监控方案

```yaml
# docker-compose.yml: Redis + Redis Exporter + Prometheus + Grafana
version: "3.8"
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --requirepass "password"

  redis-exporter:
    image: oliver006/redis_exporter:latest
    ports: ["9121:9121"]
    environment:
      REDIS_ADDR: "redis://redis:6379"
      REDIS_PASSWORD: "password"

  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "admin"
```

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

#### 6.4 关键告警规则（Prometheus AlertManager）

```yaml
# redis-alerts.yml
groups:
  - name: redis-alerts
    rules:
      # Redis 实例宕机
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis 实例 {{ $labels.instance }} 已宕机"

      # 内存使用率过高
      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis 内存使用率超过 80%: {{ $value | humanizePercentage }}"

      # 内存碎片率异常
      - alert: RedisMemoryFragmentation
        expr: redis_mem_fragmentation_ratio > 1.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Redis 内存碎片率过高: {{ $value }}"

      # 连接数过多
      - alert: RedisConnectionsHigh
        expr: redis_connected_clients > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis 连接数过高: {{ $value }}"

      # 淘汰 Key
      - alert: RedisEvictions
        expr: rate(redis_evicted_keys_total[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis 正在淘汰 Key，可能内存不足"

      # 主从断开
      - alert: RedisReplicationBroken
        expr: redis_master_link_status == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis 主从复制断开"

      # 慢查询过多
      - alert: RedisSlowQueries
        expr: rate(redis_slowlog_total[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis 慢查询过多: {{ $value }}/s"

      # Cluster 状态异常
      - alert: RedisClusterStateNotOk
        expr: redis_cluster_state == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis Cluster 状态异常"
```

---

### 7. SRE 实战案例

#### 案例 1：Sentinel 故障转移导致数据不一致

```
故障现象：
  - Sentinel 完成故障转移，新 Master 提升成功
  - 但客户端读到的数据是旧的（缺失最近 5 秒的数据）

排查过程：
  1. 检查旧 Master 的复制状态
     └─ INFO replication
     └─ master_repl_offset: 1000000
     └─ slave_repl_offset: 999900（差 100 字节）

  2. 分析
     └─ 异步复制导致 Slave 数据落后
     └─ 故障转移时有 5 秒的数据未同步

根因：
  Redis 异步复制是天然的。Master 写入成功后返回客户端，
  但数据还未同步到 Slave。Master 宕机后这部分数据丢失。

修复与预防：
  1. 使用 WAIT 命令同步等待确认
     SET key value
     WAIT 1 5000              -- 等待至少 1 个 Slave 确认，超时 5 秒

  2. 对关键数据使用 AOF always 模式
  3. 监控 master_repl_offset 差值
  4. 接受最终一致性，业务层做幂等处理
```

#### 案例 2：Redis Cluster 数据倾斜

```
故障现象：
  - Cluster 中某个节点内存使用率 95%，其他节点 50%
  - 该节点频繁触发内存淘汰
  - 业务部分 Key 操作变慢

排查过程：
  1. redis-cli --cluster check 127.0.0.1:7001
     └─ Slot 分配均匀，每个节点 5461 个 slot

  2. 检查各节点 Key 数量
     redis-cli -p 7001 DBSIZE    → 100万
     redis-cli -p 7002 DBSIZE    → 100万
     redis-cli -p 7003 DBSIZE    → 500万   ← 异常！

  3. 分析大 Key
     redis-cli -p 7003 --bigkeys
     └─ 发现 Hash: {cache}:user:all 占 4GB

  4. 根因
     └─ 使用了 Hash Tag {cache}
     └─ 所有以 {cache} 开头的 Key 都在同一个 slot
     └─ 导致该 slot 所在节点数据量暴增

修复：
  1. 拆分大 Key
     {cache}:user:all → {cache}:user:part1, {cache}:user:part2, ...
     使用 Hash Tag 的不同前缀分散到不同 slot

  2. 或去掉 Hash Tag，让 Key 自然分散

  3. 监控各节点内存和 Key 数量的均衡度
```

#### 案例 3：Cluster 节点故障导致部分请求失败

```
故障现象：
  - Cluster 中一个 Master 宕机
  - 故障转移期间（约 15 秒），部分请求返回 CLUSTERDOWN 错误
  - 故障转移完成后恢复正常

排查过程：
  1. 检查 cluster-node-timeout 配置
     └─ cluster-node-timeout 15000（15 秒）

  2. 分析故障转移耗时
     └─ 检测下线：15 秒
     └─ 投票选举：1-2 秒
     └─ Slot 迁移：1-2 秒
     └─ 总计：约 18 秒

根因：
  cluster-node-timeout 设置过长，导致故障检测慢。
  期间 Cluster 状态为 fail，拒绝所有请求。

修复：
  1. 缩短 cluster-node-timeout
     cluster-node-timeout 5000      # 5 秒

  2. 客户端增加重试逻辑
     └─ 捕获 CLUSTERDOWN 错误
     └─ 指数退避重试

  3. 客户端开启 read-from-replica
     └─ Master 不可用时从 Slave 读取（数据可能旧）
```

---

## 💻 实战练习

### 练习 1：搭建主从复制

**目标：** 手动配置 Redis 主从复制，验证数据同步。

```bash
# 启动 Master
docker run -d --name redis-master -p 6380:6379 redis:7-alpine \
    redis-server --requirepass "master123"

# 启动 Slave 1
docker run -d --name redis-slave1 -p 6381:6379 redis:7-alpine \
    redis-server --replicaof redis-master 6379 --masterauth "master123"

# 启动 Slave 2
docker run -d --name redis-slave2 -p 6382:6379 redis:7-alpine \
    redis-server --replicaof redis-master 6379 --masterauth "master123"

# 验证主从关系
redis-cli -p 6380 -a master123 INFO replication
# 应显示 role:master, connected_slaves:2

redis-cli -p 6381 -a master123 INFO replication
# 应显示 role:slave, master_link_status:up

# 测试数据同步
redis-cli -p 6380 -a master123 SET test:key "hello"
redis-cli -p 6381 -a master123 GET test:key
# 应返回 "hello"

# 测试 Slave 只读
redis-cli -p 6381 -a master123 SET test:fail "should not work"
# 应返回 READONLY 错误

# 测试 Slave 晋升为 Master
docker stop redis-master
docker exec -it redis-slave1 redis-cli -a master123 REPLICAOF NO ONE
redis-cli -p 6381 -a master123 INFO replication
# 应显示 role:master

# 清理
docker stop redis-master redis-slave1 redis-slave2
docker rm redis-master redis-slave1 redis-slave2
```

### 练习 2：部署 Redis Sentinel

**目标：** 搭建 3 Sentinel + 1 Master + 2 Slave 高可用架构，模拟故障转移。

```bash
# 创建网络
docker network create redis-net

# 启动 Master
docker run -d --name redis-master --network redis-net \
    -p 6380:6379 redis:7-alpine redis-server --requirepass "sentinel123"

# 启动 Slave
docker run -d --name redis-slave1 --network redis-net \
    -p 6381:6379 redis:7-alpine \
    redis-server --replicaof redis-master 6379 --masterauth "sentinel123"

docker run -d --name redis-slave2 --network redis-net \
    -p 6382:6379 redis:7-alpine \
    redis-server --replicaof redis-master 6379 --masterauth "sentinel123"

# 创建 Sentinel 配置
for i in 1 2 3; do
    cat > /tmp/sentinel-$i.conf << EOF
port 26379
sentinel monitor mymaster redis-master 6379 2
sentinel auth-pass mymaster sentinel123
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 10000
sentinel parallel-syncs mymaster 1
EOF
done

# 启动 Sentinel（在真实环境中应分布在不同机器）
docker run -d --name sentinel1 --network redis-net \
    -p 26379:26379 redis:7-alpine \
    redis-sentinel /etc/redis/sentinel.conf
docker cp /tmp/sentinel-1.conf sentinel1:/etc/redis/sentinel.conf
docker restart sentinel1

docker run -d --name sentinel2 --network redis-net \
    -p 26380:26379 redis:7-alpine \
    redis-sentinel /etc/redis/sentinel.conf
docker cp /tmp/sentinel-2.conf sentinel2:/etc/redis/sentinel.conf
docker restart sentinel2

docker run -d --name sentinel3 --network redis-net \
    -p 26381:26379 redis:7-alpine \
    redis-sentinel /etc/redis/sentinel.conf
docker cp /tmp/sentinel-3.conf sentinel3:/etc/redis/sentinel.conf
docker restart sentinel3

# 查看 Sentinel 状态
redis-cli -p 26379 SENTINEL master mymaster
redis-cli -p 26379 SENTINEL replicas mymaster

# 模拟 Master 故障
docker stop redis-master

# 等待故障转移（约 10 秒）
sleep 12

# 查看新 Master
redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster

# 恢复旧 Master（自动变为 Slave）
docker start redis-master
sleep 5
redis-cli -p 6380 -a sentinel123 INFO replication
# 应显示 role:slave

# 清理
docker stop redis-master redis-slave1 redis-slave2 sentinel1 sentinel2 sentinel3
docker rm redis-master redis-slave1 redis-slave2 sentinel1 sentinel2 sentinel3
docker network rm redis-net
rm /tmp/sentinel-*.conf
```

### 练习 3：Redis Cluster 搭建与扩容

**目标：** 搭建 3 主 3 从的 Redis Cluster，验证数据分片，并完成扩容操作。

```bash
# 清理旧数据
rm -rf /tmp/redis-cluster
mkdir -p /tmp/redis-cluster

# 创建 6 个节点配置
for port in 7001 7002 7003 7004 7005 7006; do
    mkdir -p /tmp/redis-cluster/$port
    cat > /tmp/redis-cluster/$port/redis.conf << EOF
port $port
cluster-enabled yes
cluster-config-file nodes-$port.conf
cluster-node-timeout 5000
appendonly yes
dbfilename dump-$port.rdb
dir /tmp/redis-cluster/$port
bind 127.0.0.1
protected-mode no
EOF
done

# 启动 6 个节点
for port in 7001 7002 7003 7004 7005 7006; do
    redis-server /tmp/redis-cluster/$port/redis.conf --daemonize yes
done

# 创建集群
redis-cli --cluster create \
    127.0.0.1:7001 127.0.0.1:7002 127.0.0.1:7003 \
    127.0.0.1:7004 127.0.0.1:7005 127.0.0.1:7006 \
    --cluster-replicas 1 --cluster-yes

# 验证集群
redis-cli -p 7001 CLUSTER INFO
redis-cli -p 7001 CLUSTER NODES

# 测试数据分片
for i in $(seq 1 100); do
    redis-cli -c -p 7001 SET "test:key:$i" "value:$i"
done

# 查看 Key 分布
for port in 7001 7002 7003; do
    echo "Node $port:"
    redis-cli -p $port DBSIZE
done

# 扩容：添加新节点
mkdir -p /tmp/redis-cluster/7007
cat > /tmp/redis-cluster/7007/redis.conf << EOF
port 7007
cluster-enabled yes
cluster-config-file nodes-7007.conf
cluster-node-timeout 5000
appendonly yes
dbfilename dump-7007.rdb
dir /tmp/redis-cluster/7007
bind 127.0.0.1
protected-mode no
EOF

redis-server /tmp/redis-cluster/7007/redis.conf --daemonize yes

# 加入集群
redis-cli --cluster add-node 127.0.0.1:7007 127.0.0.1:7001

# 重新分配 slot（迁移 4096 个 slot 到新节点）
redis-cli --cluster reshard 127.0.0.1:7001 \
    --cluster-from all \
    --cluster-to $(redis-cli -p 7007 CLUSTER MYID) \
    --cluster-slots 4096 \
    --cluster-yes

# 验证扩容
redis-cli --cluster check 127.0.0.1:7001

# 清理
for port in 7001 7002 7003 7004 7005 7006 7007; do
    redis-cli -p $port SHUTDOWN NOSAVE 2>/dev/null
done
rm -rf /tmp/redis-cluster
```

---

## 🎯 面试题精选

### 1. Redis 主从复制的原理是什么？全量同步和增量同步有什么区别？

**参考答案：**
主从复制分为全量同步和增量同步。首次连接时触发全量同步：Master 执行 BGSAVE 生成 RDB 文件，发送给 Slave，同时将期间的新写入缓存在 repl_backlog_buffer 中，RDB 传输完成后发送缓冲区中的增量数据。断线重连时优先尝试增量同步：Slave 发送 PSYNC offset，如果 offset 还在 repl_backlog_buffer 中，Master 只发送增量数据；否则降级为全量同步。

### 2. Sentinel 是如何检测 Master 故障的？SDOWN 和 ODOWN 有什么区别？

**参考答案：**
每个 Sentinel 定期向 Master 发送 PING，如果在 down-after-milliseconds 时间内没有收到有效回复，该 Sentinel 将 Master 标记为 SDOWN（主观下线）。然后 Sentinel 询问其他 Sentinel 对该 Master 的状态判断，如果超过 quorum 个 Sentinel 都认为 Master 下线，则标记为 ODOWN（客观下线），触发故障转移。

### 3. Redis Cluster 的数据分片原理是什么？为什么是 16384 个 slot？

**参考答案：**
Redis Cluster 使用 CRC16(key) % 16384 将 Key 映射到 16384 个 hash slot，每个 Master 负责一部分 slot。选择 16384 的原因是：slot 信息需要通过心跳包在节点间传播，16384 个 slot 的状态信息约占 2KB（16384 / 8 = 2048 bytes），在可接受的网络开销内。如果 slot 数量更多，心跳包会过大，影响 Gossip 协议效率。

### 4. 如何保证 Redis 缓存和 MySQL 数据的一致性？

**参考答案：**
常见方案：
1. **Cache Aside Pattern：** 读时先查缓存，未命中查数据库并写缓存；写时先更新数据库，再删除缓存
2. **延迟双删：** 先删缓存，再更新数据库，延迟一段时间再删一次缓存
3. **消息队列异步更新：** 数据库变更通过 binlog + Canal 发送到消息队列，消费者更新缓存
4. **设置合理 TTL：** 兜底方案，即使数据不一致也能在 TTL 后自动恢复

推荐方案：Cache Aside Pattern + 合理 TTL，简单可靠。

### 5. Redis Cluster 故障转移期间，客户端请求会怎样？

**参考答案：**
在 cluster-node-timeout 时间内（默认 15 秒），集群检测到节点下线。期间该节点负责的 slot 请求会返回 CLUSTERDOWN 错误。故障转移完成后（通常 15-20 秒），Slave 提升为新 Master，接管 slot，请求恢复正常。客户端需要实现重试机制处理 CLUSTERDOWN 错误。

### 6. 主从复制中的复制风暴是什么？如何解决？

**参考答案：**
复制风暴是指多个 Slave 同时向 Master 发起全量同步，导致 Master 的 CPU 和网络压力飙升。常见于 Master 重启后所有 Slave 同时重连。解决方案：
1. 级联复制：Master → Slave1 → Slave2, Slave3
2. 错开 Slave 的重连时间
3. 增大 repl_backlog_size，提高增量同步成功率

### 7. Redis Sentinel 和 Redis Cluster 如何选择？

**参考答案：**
- **Sentinel：** 适合数据量小于单机内存（通常 < 16GB）、不需要数据分片的场景。优点是简单、运维成本低。
- **Cluster：** 适合数据量超过单机内存、需要水平扩展的场景。支持数据分片和自动故障转移，但运维复杂度高。
- 选择标准：数据量、QPS、运维能力。大多数中小规模场景 Sentinel 足够。

### 8. 如何监控 Redis 主从复制延迟？

**参考答案：**
监控 master_repl_offset 和 slave_repl_offset 的差值。使用 INFO replication 命令获取这两个值。差值持续增大说明复制延迟严重。在 Prometheus 中可以用 `redis_master_repl_offset - redis_slave_repl_offset` 计算延迟。告警阈值建议设置为差值 > 1MB 或 master_last_io_seconds_ago > 10。

### 9. Redis Cluster 中为什么建议使用 Hash Tag？有什么风险？

**参考答案：**
Hash Tag 可以将相关 Key 强制分配到同一个 slot，使得 MGET、事务、Lua 脚本等需要 Key 在同一节点的操作成为可能。例如 `{user:1001}:profile` 和 `{user:1001}:orders` 都会分配到同一个 slot。风险是可能导致数据倾斜，如果某个 Hash Tag 下数据量特别大，对应节点会成为热点。使用时需要评估数据分布。

### 10. 如何实现 Redis 的跨数据中心高可用？

**参考答案：**
Redis 原生不支持跨数据中心同步。常见方案：
1. **Redis Enterprise Active-Active：** 商业方案，支持多主多活
2. **CRDTs（Conflict-free Replicated Data Types）：** 无冲突复制数据类型
3. **代理层方案：** 如 Twemproxy、Codis，在代理层做路由和同步
4. **异步复制 + 业务层冲突解决：** 接受最终一致性

---

## 📚 深入阅读

### 官方文档
- [Redis 复制](https://redis.io/docs/operate/oss_and_stack/management/replication/) — 主从复制官方文档
- [Redis Sentinel](https://redis.io/docs/operate/oss_and_stack/management/sentinel/) — Sentinel 官方文档
- [Redis Cluster](https://redis.io/docs/operate/oss_and_stack/management/scaling/) — Cluster 官方文档
- [Redis Cluster 规范](https://redis.io/docs/reference/cluster-spec/) — Cluster 协议规范

### 推荐书籍
- 《Redis 设计与实现》— 黄健宏，第 16-18 章：复制、Sentinel、Cluster
- 《Redis 深度历险》— 钱文品，集群相关章节
- 《Redis 开发与运维》— 付磊、张益军，高可用与集群运维章节

### 技术博客
- [Redis Cluster Tutorial](https://redis.io/docs/operate/oss_and_stack/management/scaling/) — 官方集群教程
- [Redis Sentinel Documentation](https://redis.io/docs/operate/oss_and_stack/management/sentinel/) — 官方 Sentinel 文档
- [Redis Monitoring](https://redis.io/docs/operate/oss_and_stack/management/optimization/monitoring/) — 官方监控指南

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释主从复制的全量同步和增量同步流程
- [ ] 能说明 Sentinel 的 SDOWN/ODOWN 检测机制
- [ ] 能解释 Redis Cluster 的 Hash Slot 分片原理
- [ ] 能说明 Cluster 故障转移的投票选举过程
- [ ] 能解释 Hash Tag 的作用和风险
- [ ] 能对比 Sentinel 和 Cluster 的适用场景

### 实操检查点
- [ ] 能独立搭建 Redis 主从复制
- [ ] 能部署 Redis Sentinel 并模拟故障转移
- [ ] 能搭建 Redis Cluster 并验证数据分片
- [ ] 能完成 Cluster 的扩容和缩容操作
- [ ] 能配置 Prometheus + Grafana 监控 Redis

### 能力验证标准
- [ ] 能在 15 分钟内搭建一个 Sentinel 高可用架构
- [ ] 能根据业务需求选择合适的高可用方案
- [ ] 能独立排查主从复制延迟问题
- [ ] 能设计并实施 Redis 监控告警方案
