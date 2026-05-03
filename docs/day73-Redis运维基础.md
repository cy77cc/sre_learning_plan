# Day 73: Redis 运维基础

> 📅 日期：2026-05-03
> 📖 学习主题：Redis 架构、数据结构、持久化、内存管理、事务与脚本
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 70 (MySQL 基础与架构), Day 71 (MySQL 性能调优)

---

## 🎯 学习目标

完成 Day 73 的学习后，你应该掌握：
- 理解 Redis 的单线程模型以及为什么单线程还能如此之快
- 掌握 Redis 五种基本数据结构及三种扩展数据结构的底层实现
- 能够根据业务场景选择合适的持久化策略（RDB / AOF / 混合）
- 熟练配置内存管理策略和淘汰策略
- 掌握事务、Lua 脚本和 Pipeline 的使用场景与限制

---

## 📖 核心知识点

### 1. Redis 架构与核心原理

#### 1.1 Redis 是什么

Redis（Remote Dictionary Server）是一个开源的、基于内存的键值存储数据库。它支持多种数据结构，广泛用于缓存、会话管理、消息队列、分布式锁等 SRE 核心场景。

```
┌─────────────────────────────────────────────────────┐
│                    Redis 架构总览                     │
│                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  Client  │───▶│  Network     │───▶│  单线程    │  │
│  │  请求     │    │  I/O 多路复用 │    │  事件循环  │  │
│  └──────────┘    └──────────────┘    └─────┬─────┘  │
│                                            │        │
│                    ┌───────────────────────┼────┐   │
│                    │       内存数据库       │    │   │
│                    │  ┌─────┐ ┌─────┐ ┌───┴─┐  │   │
│                    │  │String│ │Hash │ │List │  │   │
│                    │  └─────┘ └─────┘ └─────┘  │   │
│                    │  ┌─────┐ ┌─────┐ ┌─────┐  │   │
│                    │  │ Set  │ │ZSet │ │More │  │   │
│                    │  └─────┘ └─────┘ └─────┘  │   │
│                    └───────────────────────────┘   │
│                            │                        │
│                    ┌───────┴───────┐                │
│                    │   持久化层     │                │
│                    │  RDB  |  AOF  │                │
│                    └───────────────┘                │
└─────────────────────────────────────────────────────┘
```

#### 1.2 Redis 单线程模型 —— 为什么这么快？

这是 Redis 面试最高频的问题之一。Redis 的核心处理逻辑确实是单线程的（Redis 6.0 之后网络 I/O 使用多线程，但命令执行仍是单线程）。

**单线程快的四大原因：**

```
┌─────────────────────────────────────────────────────────┐
│              Redis 单线程快的原因                         │
│                                                         │
│  1. 纯内存操作                                            │
│     ┌──────┐    0.001ms    ┌──────┐                     │
│     │ 内存  │──────────────▶│ 结果  │                     │
│     └──────┘               └──────┘                     │
│     数据全部在内存中，读写操作不受磁盘 I/O 限制              │
│                                                         │
│  2. I/O 多路复用 (epoll/kqueue)                           │
│     ┌──────────┐                                        │
│     │  Client 1 │──┐                                    │
│     ├──────────┤  │    ┌─────────┐    ┌──────────────┐  │
│     │  Client 2 │──┼───▶│  epoll  │───▶│ 单线程依次处理 │  │
│     ├──────────┤  │    └─────────┘    └──────────────┘  │
│     │  Client N │──┘                                    │
│     └──────────┘  一个线程同时监听多个 socket 连接         │
│                                                         │
│  3. 高效数据结构                                          │
│     SDS (动态字符串)、ziplist、quicklist、skiplist、       │
│     intset、hashtable —— 每种结构都针对场景深度优化         │
│                                                         │
│  4. 避免上下文切换                                        │
│     单线程不需要加锁，没有线程切换开销，没有死锁问题         │
└─────────────────────────────────────────────────────────┘
```

**对比多线程模型：**

| 特性 | Redis 单线程 | Memcached 多线程 |
|------|-------------|-----------------|
| CPU 利用率 | 单核，通常够用 | 多核并行 |
| 锁开销 | 无 | 需要加锁 |
| 上下文切换 | 无 | 有开销 |
| 复杂度 | 低 | 高 |
| 瓶颈 | 网络 / 内存 | CPU |

> **SRE 注意：** Redis 的瓶颈通常不在 CPU，而在网络带宽和内存大小。如果你发现 Redis CPU 飙升，通常是以下原因：使用了 KEYS 命令、大 Key 操作、Lua 脚本执行过久。

#### 1.3 Redis 6.0+ 多线程 I/O

```
Redis 6.0 之后的线程模型：

┌─────────────────────────────────────────────────┐
│                                                 │
│  I/O 线程组（多线程）                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ I/O 线程1│ │ I/O 线程2│ │ I/O 线程N│           │
│  │ 读请求   │ │ 读请求   │ │ 读请求   │           │
│  │ 写响应   │ │ 写响应   │ │ 写响应   │           │
│  └────┬────┘ └────┬────┘ └────┬────┘           │
│       │           │           │                 │
│       └───────────┼───────────┘                 │
│                   ▼                             │
│           ┌──────────────┐                      │
│           │  主线程       │  ◀── 命令执行仍然是   │
│           │  命令执行     │      单线程！         │
│           └──────────────┘                      │
│                                                 │
└─────────────────────────────────────────────────┘

配置 io-threads：
# redis.conf
io-threads 4           # I/O 线程数（建议 CPU 核心数的一半）
io-threads-do-reads yes # 开启读多线程
```

---

### 2. Redis 数据结构详解

#### 2.1 五种基本数据结构

##### String（字符串）

String 是 Redis 最基本的数据类型，底层实现为 SDS（Simple Dynamic String）。

```
SDS 结构：
┌──────────────────────────────┐
│  struct sdshdr {             │
│      int len;    // 已用长度  │
│      int free;   // 剩余空间  │
│      char buf[]; // 字节数组  │
│  }                           │
└──────────────────────────────┘

与 C 字符串对比：
┌──────────────┬──────────────┬──────────────────┐
│    特性       │   C 字符串    │     SDS          │
├──────────────┼──────────────┼──────────────────┤
│ 获取长度      │ O(n) 遍历    │ O(1) 直接读 len  │
│ 缓冲区溢出    │ 可能发生     │ 不会，自动扩容    │
│ 二进制安全    │ 不支持       │ 支持             │
│ 空间预分配    │ 无           │ 有               │
│ 惰性释放      │ 无           │ 有               │
└──────────────┴──────────────┴──────────────────┘
```

```redis
-- 基础操作
SET user:1001:name "zhangsan"
GET user:1001:name
SETNX lock:order:12345 "holder-uuid"    -- 分布式锁
SETEX session:abc 3600 "user_data"       -- 带过期时间
MSET k1 "v1" k2 "v2" k3 "v3"           -- 批量设置
MGET k1 k2 k3                           -- 批量获取

-- 计数器场景（SRE 常用）
INCR metrics:requests:total              -- 请求计数
INCRBY metrics:bytes:sent 1024           -- 增量计数
INCRBYFLOAT price:item:1001 0.50         -- 浮点数增量

-- 位图操作（轻量级布尔统计）
SETBIT login:2026-05-03 1001 1           -- 用户 1001 今日登录
GETBIT login:2026-05-03 1001             -- 查询登录状态
BITCOUNT login:2026-05-03                -- 今日登录用户数
```

> **SRE 场景：** 用 String 做接口限流计数器。例如 `INCR ratelimit:api:/v1/users:192.168.1.1`，配合 `EXPIRE` 设置时间窗口。

##### Hash（哈希）

Hash 底层使用 ziplist（小数据量）或 hashtable（大数据量）。

```
Hash 底层转换：
  小数据量 (默认)          大数据量
  ┌─────────────┐         ┌─────────────┐
  │   ziplist    │  ──▶    │  hashtable   │
  │  连续内存     │ 超过阈值  │  哈希表       │
  │  节省内存     │         │  O(1) 查找    │
  └─────────────┘         └─────────────┘

转换阈值（可配置）：
  hash-max-ziplist-entries 128    # 字段数超过 128 转换
  hash-max-ziplist-value 64       # 字段值超过 64 字节转换
```

```redis
-- 对象存储（比多个 String 更省内存）
HSET user:1001 name "zhangsan" email "zs@example.com" age 28
HGET user:1001 name
HGETALL user:1001
HINCRBY user:1001 age 1

-- SRE 场景：服务器指标存储
HMSET server:web-01 cpu_usage 85.2 mem_usage 72.1 disk_usage 45.0 load_5m 2.3
HINCRBY server:web-01 restart_count 1
HSET server:web-01 last_check "2026-05-03T10:30:00Z"
```

> **SRE 场景：** 用 Hash 存储用户 Session 信息，每个 Session 一个 Key，字段存不同属性。比用多个 String Key 更紧凑。

##### List（列表）

List 底层使用 quicklist（ziplist + 双向链表的混合体）。

```
quicklist 结构：
┌──────────┐    ┌──────────┐    ┌──────────┐
│ node 1   │◀──▶│ node 2   │◀──▶│ node 3   │
│ [ziplist] │    │ [ziplist] │    │ [ziplist] │
│ a, b, c   │    │ d, e, f   │    │ g, h     │
└──────────┘    └──────────┘    └──────────┘

每个 node 是一个双向链表节点，
内部存储一个 ziplist，兼顾链表的灵活性和 ziplist 的内存效率。
```

```redis
-- 消息队列
LPUSH queue:emails '{"to":"user@example.com","subject":"Welcome"}'
RPOP queue:emails
BRPOP queue:emails 30              -- 阻塞弹出，超时 30 秒

-- 最新列表（保留最近 N 条）
LPUSH recent:logs "2026-05-03 ERROR: disk full on web-01"
LTRIM recent:logs 0 999            -- 只保留最近 1000 条

-- SRE 场景：任务队列
LPUSH tasks:deploy '{"service":"user-api","version":"v2.1.0","env":"prod"}'
BRPOP tasks:deploy 0               -- worker 阻塞等待任务
```

> **SRE 注意：** List 做消息队列没有 ACK 机制。如果需要可靠消息传递，考虑使用 Stream（Redis 5.0+）。

##### Set（集合）

Set 底层使用 intset（纯整数集合）或 hashtable。

```
intset 结构（纯整数时使用）：
┌──────────────────────────────┐
│  encoding: INT32_ENCONDING   │
│  length: 5                   │
│  contents: [1, 2, 3, 10, 99] │  ◀── 有序、不重复
└──────────────────────────────┘

当包含非整数元素时，自动转换为 hashtable。
```

```redis
-- 标签系统
SADD article:1001:tags "redis" "database" "nosql"
SADD article:1002:tags "redis" "cache" "performance"
SINTER article:1001:tags article:1002:tags    -- 交集：共同标签
SDIFF article:1001:tags article:1002:tags     -- 差集

-- SRE 场景：在线用户统计
SADD online:users "user:1001" "user:1002" "user:1003"
SCARD online:users                           -- 在线人数
SISMEMBER online:users "user:1001"           -- 是否在线
SREM online:users "user:1001"                -- 用户下线
```

##### Sorted Set（有序集合）

Sorted Set 底层使用 ziplist 或 skiplist + hashtable。

```
skiplist（跳表）结构：
Level 3:  1 ─────────────────────────────────▶ 9
Level 2:  1 ────────────▶ 5 ─────────────────▶ 9
Level 1:  1 ──▶ 3 ──▶ 5 ──▶ 7 ──▶ 9
Level 0:  1  2  3  4  5  6  7  8  9

跳表 vs 红黑树：
┌──────────────┬───────────┬───────────┐
│    特性       │  跳表      │  红黑树    │
├──────────────┼───────────┼───────────┤
│ 查找时间      │ O(logN)   │ O(logN)   │
│ 实现复杂度    │ 简单       │ 复杂      │
│ 范围查询      │ 高效       │ 较差      │
│ 内存占用      │ 较多       │ 较少      │
│ 并发友好      │ 较好       │ 较差      │
└──────────────┴───────────┴───────────┘
Redis 选择跳表的原因：实现简单、范围查询高效、ZREVRANGE 等命令容易实现。
```

```redis
-- 排行榜
ZADD leaderboard 1500 "player:A" 1200 "player:B" 1800 "player:C"
ZREVRANGE leaderboard 0 2 WITHSCORES         -- Top 3
ZRANK leaderboard "player:A"                  -- 排名
ZINCRBY leaderboard 100 "player:A"            -- 加分

-- SRE 场景：延迟队列
ZADD delay:queue 1683100200 '{"task":"cleanup","retry":0}'
ZADD delay:queue 1683100500 '{"task":"notify","retry":1}'
ZRANGEBYSCORE delay:queue 0 1683100300        -- 取出到期任务
ZREM delay:queue '{"task":"cleanup","retry":0}' -- 处理后删除
```

#### 2.2 扩展数据结构

| 数据结构 | 底层实现 | 典型场景 | 命令示例 |
|---------|---------|---------|---------|
| Bitmap | String 的位操作 | 用户签到、在线状态、布隆过滤器 | `SETBIT`, `BITCOUNT`, `BITOP` |
| HyperLogLog | 概率算法 | UV 统计（误差 0.81%） | `PFADD`, `PFCOUNT`, `PFMERGE` |
| Stream | Radix Tree + Listpack | 消息队列（Redis 5.0+） | `XADD`, `XREAD`, `XGROUP` |

```redis
-- HyperLogLog：统计每日独立访客
PFADD uv:2026-05-03 "user1" "user2" "user3" "user1"  -- 去重
PFCOUNT uv:2026-05-03                                  -- 返回 3
PFMERGE uv:2026-05 uv:2026-05-01 uv:2026-05-02 uv:2026-05-03
PFCOUNT uv:2026-05                                     -- 月度 UV

-- Stream：可靠消息队列
XADD orders * service "payment" amount 99.99 user_id 1001
XLEN orders
XREAD COUNT 10 STREAMS orders 0                       -- 读取前 10 条
XGROUP CREATE orders workers 0                         -- 创建消费者组
XREADGROUP GROUP workers consumer1 COUNT 1 STREAMS orders >
XACK orders workers "1683100200000-0"                  -- 确认消费
```

---

### 3. Redis 持久化：RDB vs AOF

持久化是 Redis 运维中最重要的决策之一。选择不当会导致数据丢失或性能下降。

#### 3.1 RDB（Redis Database Snapshot）

RDB 通过 fork 子进程生成内存快照，写入 `.rdb` 文件。

```
RDB 持久化流程：

  主进程                    子进程
    │                        │
    │  fork() ──────────────▶│
    │                        │
    │  继续处理请求            │
    │  (Copy-on-Write)       │
    │                        │  遍历内存数据
    │                        │  写入 temp.rdb
    │                        │
    │                        │  rename temp.rdb dump.rdb
    │                        │
    │◀─── 子进程退出 ─────────│
    │                        │
```

**Copy-on-Write (COW) 机制：**

```
fork 时：
  父进程内存页 ─────────┐
                        ├──▶  共享物理内存页
  子进程内存页 ─────────┘

写入时（父进程有新写入）：
  父进程 ──▶ 复制一份新页 ──▶ 写入新数据（不影响子进程）
  子进程 ──▶ 仍然指向旧页 ──▶ 照常快照

风险：如果 fork 后大量写入，会导致内存翻倍！
```

**RDB 配置：**

```bash
# redis.conf
# 自动触发条件（满足任一即触发 BGSAVE）
save 900 1       # 900 秒内至少 1 个 key 变化
save 300 10      # 300 秒内至少 10 个 key 变化
save 60 10000    # 60 秒内至少 10000 个 key 变化

# 关闭自动 RDB
# save ""

dbfilename dump.rdb          # RDB 文件名
dir /var/lib/redis            # RDB 保存目录
rdbcompression yes            # LZF 压缩
rdbchecksum yes               # CRC64 校验
stop-writes-on-bgsave-error yes  # BGSAVE 出错时停止写入
```

**手动触发：**

```redis
SAVE          -- 同步保存（阻塞主线程，生产禁用！）
BGSAVE        -- 后台异步保存（推荐）
LASTSAVE      -- 查看最后一次成功 RDB 的时间戳
```

**RDB 优缺点：**

| 优点 | 缺点 |
|------|------|
| 文件紧凑，适合备份和灾难恢复 | 可能丢失最后一次快照后的数据 |
| 恢复速度快（直接加载二进制） | fork 时内存翻倍风险 |
| 对性能影响小（子进程处理） | 大数据量时 fork 耗时 |
| 适合全量备份 | 不适合实时持久化 |

#### 3.2 AOF（Append Only File）

AOF 以日志追加的方式记录每一个写操作。

```
AOF 持久化流程：

  客户端写命令
       │
       ▼
  ┌──────────┐
  │ 命令追加  │  ──▶  aof_buf (内存缓冲区)
  └──────────┘
       │
       ▼  (根据 fsync 策略)
  ┌──────────┐
  │ 文件写入  │  ──▶  OS page cache
  └──────────┘
       │
       ▼  (fsync)
  ┌──────────┐
  │ 磁盘同步  │  ──▶  appendonly.aof
  └──────────┘
```

**fsync 策略对比：**

```
┌────────────────┬──────────────┬──────────────┬──────────────┐
│    策略         │  always      │  everysec    │  no          │
├────────────────┼──────────────┼──────────────┼──────────────┤
│ 写入方式        │ 每条命令fsync │ 每秒fsync    │ 由 OS 决定   │
│ 数据安全性      │ 最高          │ 最多丢 1 秒  │ 可能丢 30 秒 │
│ 性能影响        │ 最差          │ 推荐         │ 最好         │
│ 磁盘 I/O       │ 极高          │ 低           │ 最低         │
│ 推荐场景        │ 金融级        │ 通用生产     │ 可容忍丢失   │
└────────────────┴──────────────┴──────────────┴──────────────┘
```

**AOF 配置：**

```bash
# redis.conf
appendonly yes                      # 开启 AOF
appendfilename "appendonly.aof"     # AOF 文件名
appendfsync everysec                # 推荐：每秒同步一次

# AOF 重写配置
auto-aof-rewrite-percentage 100     # AOF 文件增长 100% 时触发重写
auto-aof-rewrite-min-size 64mb      # AOF 文件最小 64MB 才触发重写
aof-use-rdb-preamble yes            # 混合持久化（Redis 4.0+）
```

**AOF 重写流程：**

```
AOF 重写（压缩 AOF 文件）：

  主进程                         子进程
    │                             │
    │  fork() ───────────────────▶│
    │                             │
    │  继续处理请求                 │  遍历数据库
    │  写命令追加到旧 AOF           │  生成最小命令集写入新 AOF
    │  同时追加到 AOF 重写缓冲区     │
    │                             │
    │                             │  完成重写
    │◀─── 信号通知 ───────────────│
    │                             │
    │  将重写缓冲区内容追加到新 AOF   │
    │  原子替换旧 AOF 文件          │
    │                             │
```

```redis
-- 手动触发 AOF 重写
BGREWRITEAOF

-- 查看 AOF 状态
INFO persistence
```

#### 3.3 混合持久化（Redis 4.0+ 推荐）

```
混合持久化 = RDB 快照 + AOF 增量日志

AOF 重写时的文件结构：
┌─────────────────────────────────┐
│  RDB 二进制数据（全量快照）       │  ◀── 恢复速度快
├─────────────────────────────────┤
│  AOF 增量命令（重写后的增量）     │  ◀── 数据完整性高
└─────────────────────────────────┘

重启时：先加载 RDB 部分，再回放 AOF 部分
兼具 RDB 的恢复速度和 AOF 的数据安全性
```

**持久化策略选择指南：**

```
┌─────────────────────────────────────────────────┐
│           持久化策略选择决策树                     │
│                                                 │
│  数据丢失可接受？                                 │
│  ├─ 是 ──▶ 仅 RDB（快照备份即可）                │
│  └─ 否 ──▶ 数据丢失容忍度？                      │
│            ├─ < 1 秒 ──▶ AOF (always)           │
│            │            性能差，适合金融场景       │
│            ├─ ≤ 1 秒 ──▶ 混合持久化（推荐）       │
│            │            AOF (everysec) + RDB     │
│            └─ > 1 秒 ──▶ AOF (everysec)         │
│                                                 │
│  SRE 推荐：混合持久化 + 定期 RDB 备份到远程存储    │
└─────────────────────────────────────────────────┘
```

---

### 4. 内存管理

#### 4.1 内存分配

Redis 使用 jemalloc 作为默认内存分配器（也可选 libc、tcmalloc）。

```redis
-- 查看内存使用详情
INFO memory

# used_memory:1073741824           -- Redis 分配器分配的内存
# used_memory_human:1.00G
# used_memory_rss:1207959552       -- 操作系统看到的 RSS 内存
# used_memory_rss_human:1.12G
# used_memory_peak:2147483648      -- 内存使用峰值
# mem_fragmentation_ratio:1.13     -- 内存碎片率
# mem_allocator:jemalloc-5.3.0     -- 内存分配器

-- 内存碎片率解读：
-- < 1.0: 使用了 swap，性能严重下降，需立即处理
-- 1.0 - 1.5: 正常范围
-- > 1.5: 碎片严重，考虑重启或开启碎片整理
```

**内存碎片整理（Redis 4.0+）：**

```bash
# redis.conf
activedefrag yes                     -- 开启主动碎片整理
active-defrag-ignore-bytes 100mb     -- 碎片超过 100MB 才整理
active-defrag-threshold-lower 10     -- 碎片率超过 10% 开始整理
active-defrag-threshold-upper 100    -- 碎片率超过 100% 全力整理
active-defrag-cycle-min 1            -- 最小 CPU 占用百分比
active-defrag-cycle-max 25           -- 最大 CPU 占用百分比
```

#### 4.2 内存淘汰策略（Eviction Policy）

当 Redis 内存达到 `maxmemory` 限制时，根据淘汰策略决定如何处理新写入。

```
┌─────────────────────────────────────────────────────────────┐
│                  Redis 淘汰策略全景                           │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐                         │
│  │  noeviction  │    │  volatile-* │  只淘汰有过期时间的 key   │
│  │  不淘汰       │    │             │                         │
│  │  写入报错     │    ├─────────────┤                         │
│  └─────────────┘    │ volatile-lru │  LRU 淘汰有过期的 key   │
│                      │ volatile-lfu │  LFU 淘汰有过期的 key   │
│  ┌─────────────┐    │ volatile-ttl │  淘汰最快过期的 key     │
│  │ allkeys-*   │    │ volatile-random │ 随机淘汰有过期的 key  │
│  │ 淘汰所有 key │    └─────────────┘                         │
│  ├─────────────┤                                             │
│  │ allkeys-lru │  ◀── 最常用：全局 LRU 淘汰                  │
│  │ allkeys-lfu │  ◀── 热点数据友好：淘汰访问最少的             │
│  │ allkeys-random │ 随机淘汰                                 │
│  └─────────────┘                                             │
└─────────────────────────────────────────────────────────────┘
```

**策略详解与对比：**

| 策略 | 淘汰范围 | 淘汰算法 | 适用场景 |
|------|---------|---------|---------|
| `noeviction` | 不淘汰 | N/A | 数据不能丢失，宁可报错 |
| `allkeys-lru` | 所有 key | 最近最少使用 | **通用缓存（推荐）** |
| `allkeys-lfu` | 所有 key | 最不经常使用 | 热点数据明显的场景 |
| `volatile-lru` | 有过期时间的 key | LRU | 混合存储（缓存+持久） |
| `volatile-lfu` | 有过期时间的 key | LFU | 混合存储且有热点 |
| `volatile-ttl` | 有过期时间的 key | TTL | 希望优先淘汰快过期的 |
| `volatile-random` | 有过期时间的 key | 随机 | 无明确偏好 |
| `allkeys-random` | 所有 key | 随机 | 极少使用 |

```redis
-- 配置淘汰策略
CONFIG SET maxmemory 4gb
CONFIG SET maxmemory-policy allkeys-lru

-- 查看当前配置
CONFIG GET maxmemory
CONFIG GET maxmemory-policy
```

> **SRE 最佳实践：**
> - 纯缓存场景：使用 `allkeys-lru` 或 `allkeys-lfu`
> - 缓存 + 持久数据混合：使用 `volatile-lru`，持久数据不设过期时间
> - 永远设置 `maxmemory`，否则 Redis 会吃光所有内存直到被 OOM Killer 杀掉

#### 4.3 大 Key 问题

大 Key 是 Redis 运维中最常见的性能杀手之一。

```
大 Key 的危害：
┌──────────────────────────────────────────────┐
│ 1. 阻塞主线程：一次 DEL 一个 100MB 的 Key     │
│    会阻塞其他请求数秒                          │
│ 2. 网络拥塞：一次 GET 一个 10MB 的 Value       │
│    占用大量带宽                                │
│ 3. 内存不均：Cluster 模式下数据倾斜            │
│ 4. 持久化卡顿：fork 时 COW 内存翻倍            │
└──────────────────────────────────────────────┘
```

**大 Key 检测与处理：**

```bash
# 检测大 Key（生产环境在从节点执行）
redis-cli --bigkeys

# 更精确的内存分析
redis-cli --memkeys

# 使用 MEMORY USAGE 查看单个 Key 的内存占用
redis-cli MEMORY USAGE user:profile:1001

# 使用 SCAN 遍历（不要用 KEYS！）
redis-cli --scan --pattern "user:*" | while read key; do
    type=$(redis-cli TYPE "$key" | awk '{print $NF}')
    echo "$key ($type): $(redis-cli MEMORY USAGE "$key") bytes"
done
```

**大 Key 删除（安全方式）：**

```redis
-- 危险！直接删除大 Key 会阻塞主线程
DEL big:key

-- 安全：异步删除（Redis 4.0+）
UNLINK big:key                -- 后台异步删除

-- 对于 Hash/Set/ZSet：分批删除
HSCAN big:hash 0 COUNT 100    -- 分批扫描
HDEL big:hash field1 field2   -- 分批删除

-- 或者用 Lua 脚本分批删除
EVAL "
    local keys = redis.call('HKEYS', KEYS[1])
    for i=1, #keys, 100 do
        redis.call('HDEL', KEYS[1], unpack(keys, i, math.min(i+99, #keys)))
    end
    return #keys
" 1 big:hash
```

---

### 5. 事务与 Lua 脚本

#### 5.1 Redis 事务

Redis 事务通过 MULTI / EXEC 实现，但与关系型数据库事务有本质区别。

```
Redis 事务流程：

  MULTI          -- 开始事务
    │
    ▼
  SET k1 v1      -- 命令入队（不执行）
  SET k2 v2      -- 命令入队
  INCR counter   -- 命令入队
    │
    ▼
  EXEC           -- 执行所有入队命令
    │
    ▼
  返回所有命令结果
```

```redis
-- 基本事务
MULTI
SET account:A 900
SET account:B 1100
EXEC

-- 事务 + WATCH（乐观锁）
WATCH account:A              -- 监视 key
val = GET account:A          -- 读取当前值
MULTI                        -- 开始事务
SET account:A val-100        -- 修改
EXEC                         -- 如果 account:A 被其他客户端修改，EXEC 返回 nil

-- DISCARD 取消事务
MULTI
SET k1 v1
DISCARD                      -- 取消事务，所有命令不执行
```

**Redis 事务的局限性：**

```
┌─────────────────────────────────────────────────────────┐
│              Redis 事务 vs 关系型事务                    │
│                                                         │
│  特性         │ Redis 事务      │ MySQL 事务             │
│ ─────────────┼────────────────┼─────────────────────── │
│  原子性       │ 部分支持         │ 完全支持（回滚）        │
│  一致性       │ 不保证           │ 完全支持               │
│  隔离性       │ 单线程天然隔离    │ MVCC / 锁             │
│  持久性       │ 取决于持久化配置  │ redo log / binlog     │
│  错误处理     │ 语法错误全部回滚  │ 完整回滚               │
│              │ 运行时错误不影响  │                       │
│              │ 其他命令         │                       │
└─────────────────────────────────────────────────────────┘

Redis 事务不能回滚！
如果 EXEC 前某个命令有语法错误，所有命令都不会执行。
但如果是运行时错误（如对 String 执行 LPUSH），
只有该命令失败，其他命令照常执行。
```

#### 5.2 Lua 脚本

Lua 脚本是 Redis 实现原子操作的利器，比事务更强大。

```
Lua 脚本执行流程：

  ┌──────────┐     EVAL / EVALSHA      ┌───────────┐
  │  Client   │ ──────────────────────▶ │  Redis    │
  │           │                         │  Lua 引擎 │
  │           │ ◀────────────────────── │  (原子)   │
  └──────────┘     执行结果              └───────────┘

  整个脚本在 Redis 内原子执行，
  执行期间不会有其他命令插入（单线程保证）。
```

```redis
-- 基本 Lua 脚本
EVAL "return redis.call('SET', KEYS[1], ARGV[1])" 1 mykey myvalue

-- KEYS[1] = 第一个 key 参数
-- ARGV[1] = 第一个 value 参数
-- 数字 1 表示有几个 key 参数

-- 原子性 CAS（Compare-And-Set）
EVAL "
    local current = redis.call('GET', KEYS[1])
    if current == ARGV[1] then
        redis.call('SET', KEYS[1], ARGV[2])
        return 1
    end
    return 0
" 1 mykey old_value new_value

-- 原子性限流器
EVAL "
    local key = KEYS[1]
    local limit = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local current = redis.call('INCR', key)
    if current == 1 then
        redis.call('EXPIRE', key, window)
    end
    if current > limit then
        return 0
    end
    return 1
" 1 ratelimit:api:192.168.1.1 100 60

-- 分布式锁（安全获取 + 释放）
-- 加锁
EVAL "
    if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'PX', ARGV[2]) then
        return 1
    end
    return 0
" 1 lock:order:12345 "uuid-holder-xxx" 30000

-- 释放锁（只能释放自己持有的锁）
EVAL "
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        return redis.call('DEL', KEYS[1])
    end
    return 0
" 1 lock:order:12345 "uuid-holder-xxx"
```

**EVALSHA —— 避免重复传输脚本：**

```redis
-- 第一次：加载脚本并执行
SCRIPT LOAD "return redis.call('SET', KEYS[1], ARGV[1])"
-- 返回 SHA1: "a1b2c3d4..."

-- 后续：用 SHA1 执行（更高效）
EVALSHA "a1b2c3d4..." 1 mykey myvalue

-- 检查脚本是否已缓存
SCRIPT EXISTS "a1b2c3d4..."

-- 清空脚本缓存
SCRIPT FLUSH
```

> **SRE 注意事项：**
> - Lua 脚本执行期间阻塞所有其他命令，脚本不能太长（建议 < 5ms）
> - 不要在 Lua 脚本中使用不确定性的命令（如 RANDOMKEY、TIME）
> - Redis Cluster 中 Lua 脚本操作的所有 Key 必须在同一个节点（使用 hash tag: `{tag}key1`, `{tag}key2`）

---

### 6. Pipeline（管道）

Pipeline 允许客户端一次发送多个命令，减少网络往返次数。

```
没有 Pipeline（N 次往返）：

  Client              Redis
    │── SET k1 v1 ─────▶│
    │◀── OK ─────────────│
    │── SET k2 v2 ─────▶│
    │◀── OK ─────────────│
    │── SET k3 v3 ─────▶│
    │◀── OK ─────────────│
    ... 重复 N 次 ...

使用 Pipeline（1 次往返）：

  Client              Redis
    │── SET k1 v1 ──┐   │
    │── SET k2 v2 ──┼──▶│
    │── SET k3 v3 ──┘   │
    │◀── OK ────────┐   │
    │◀── OK ────────┼───│
    │◀── OK ────────┘   │
```

**Pipeline 性能对比：**

```bash
# 普通方式：逐条执行
redis-cli SET key1 value1
redis-cli SET key2 value2
# ... 10000 次，每次约 0.1ms 网络延迟
# 总耗时：10000 * 0.1ms = 1000ms

# Pipeline 方式：批量执行
echo -e "SET key1 value1\nSET key2 value2\n..." | redis-cli --pipe
# 总耗时：约 10-50ms
```

**各语言客户端 Pipeline 示例：**

```python
# Python (redis-py)
import redis

r = redis.Redis(host='localhost', port=6379)
pipe = r.pipeline(transaction=False)  # 非事务 Pipeline

for i in range(10000):
    pipe.set(f'key:{i}', f'value:{i}')

results = pipe.execute()  # 一次性发送所有命令
```

```go
// Go (go-redis)
pipe := rdb.Pipeline()

for i := 0; i < 10000; i++ {
    pipe.Set(ctx, fmt.Sprintf("key:%d", i), fmt.Sprintf("value:%d", i), 0)
}

cmds, err := pipe.Exec(ctx)  // 一次性发送
```

```java
// Java (Jedis)
jedis jedis = new Jedis("localhost", 6379);
Pipeline pipe = jedis.pipelined();

for (int i = 0; i < 10000; i++) {
    pipe.set("key:" + i, "value:" + i);
}

pipe.sync();  // 一次性发送
```

> **SRE 实践建议：**
> - Pipeline 批量大小建议 100-500 条命令，避免一次发送太多导致阻塞
> - Pipeline 不是原子操作，命令之间可能插入其他客户端的命令
> - 批量写入大量数据时，结合 SCAN + Pipeline 避免阻塞

---

### 7. SRE 实战案例

#### 案例 1：Redis 内存突增导致服务不可用

```
故障现象：
  - 告警：Redis used_memory 超过 maxmemory
  - 业务表现：写入操作频繁报错 "OOM command not allowed"
  - 影响范围：所有依赖 Redis 的服务

排查过程：
  1. redis-cli INFO memory
     └─ used_memory: 8GB, maxmemory: 8GB
     └─ used_memory_peak: 12GB
     └─ mem_fragmentation_ratio: 1.02

  2. redis-cli --bigkeys
     └─ 发现 Hash: user:session:* 平均每个 5MB
     └─ 总计约 2000 个 session 占用 10GB

  3. redis-cli --scan --pattern "user:session:*" | wc -l
     └─ 2000+ 个 session key

  4. TTL 检查
     └─ redis-cli TTL user:session:abc123
     └─ 返回 -1（没有过期时间！）

根因：
  代码 bug：创建 session 时忘记设置 TTL
  session 不断累积，最终撑爆内存

修复：
  1. 紧急：批量给现有 session 设置过期时间
     EVAL "
       local keys = redis.call('SCAN', ARGV[1], 'MATCH', 'user:session:*', 'COUNT', 100)
       for _, k in ipairs(keys[2]) do
         redis.call('EXPIRE', k, 3600)
       end
       return keys[1]
     " 0

  2. 修复代码：所有 session 创建时必须设置 TTL
     SETEX session:{id} 3600 "{data}"

  3. 增加监控告警
     - used_memory > 80% maxmemory → Warning
     - used_memory > 90% maxmemory → Critical

预防：
  - Code Review 检查所有 Redis SET 操作是否有 TTL
  - 定期运行 redis-cli --bigkeys 监控大 Key
  - 设置合理的 maxmemory-policy
```

#### 案例 2：AOF 重写导致 Redis 卡顿

```
故障现象：
  - Redis 响应延迟从 1ms 飙升到 500ms+
  - 监控：AOF rewrite 持续时间超过 30 秒
  - 业务：API 超时率上升

排查过程：
  1. redis-cli INFO persistence
     └─ aof_rewrite_in_progress: 1
     └─ aof_current_size: 15GB
     └─ aof_base_size: 5GB

  2. 检查系统资源
     └─ top: redis 进程 CPU 80%
     └─ iostat: 磁盘 I/O 利用率 95%
     └─ free: 内存使用 90%

  3. 分析
     └─ AOF 文件 15GB，重写需要遍历所有数据
     └─ fork 子进程时 COW 导致内存翻倍
     └─ 磁盘 I/O 成为瓶颈

根因：
  - AOF 文件过大（15GB），重写耗时
  - 重写频率配置不当，小文件频繁重写变大文件
  - 磁盘性能不足

修复：
  1. 调整 AOF 重写参数
     auto-aof-rewrite-percentage 200    # 增长 200% 才重写
     auto-aof-rewrite-min-size 512mb    # 最小 512MB

  2. 切换到混合持久化
     aof-use-rdb-preamble yes

  3. 升级磁盘（HDD → SSD）

预防：
  - 监控 AOF 文件大小和重写耗时
  - 在业务低峰期手动触发 BGREWRITEAOF
  - 考虑关闭 AOF，仅使用 RDB + 从节点
```

#### 案例 3：热点 Key 导致单节点过载

```
故障现象：
  - Redis Cluster 某个节点 CPU 100%，其他节点正常
  - 该节点处理了 80% 的请求
  - 业务：商品详情页超时

排查过程：
  1. redis-cli --stat
     └─ node-3: 50000 ops/s，其他节点: 5000 ops/s

  2. redis-cli --hotkeys（需开启 LFU）
     └─ product:detail:12345 每秒被访问 30000+ 次

  3. redis-cli DEBUG OBJECT product:detail:12345
     └─ serializedlength: 50KB

根因：
  - 热门商品 Key 集中在一个节点
  - 没有做本地缓存，所有请求穿透到 Redis

修复：
  1. 应用层本地缓存（Caffeine/Guava Cache）
     └─ 热点 Key 缓存 5 秒，减少 Redis 压力

  2. 读写分离
     └─ 热点读取走从节点

  3. Key 分散
     └─ product:detail:12345:{random_suffix}
     └─ 读取时随机选择一个（数据冗余）

预防：
  - 对热点数据建立本地缓存策略
  - 监控 Redis 各节点的 ops/s 是否均衡
  - 使用 MONITOR（短暂）或 redis-faina 分析热点命令
```

---

## 💻 实战练习

### 练习 1：Redis 数据结构操作

**目标：** 熟练使用 Redis 五种基本数据结构完成 SRE 场景操作。

```bash
# 启动 Redis
docker run -d --name redis-lab -p 6379:6379 redis:7-alpine

# 连接
docker exec -it redis-lab redis-cli
```

```redis
-- 1. String：接口限流计数器
SET ratelimit:api:/v1/users:192.168.1.1 0
INCR ratelimit:api:/v1/users:192.168.1.1
EXPIRE ratelimit:api:/v1/users:192.168.1.1 60
TTL ratelimit:api:/v1/users:192.168.1.1

-- 2. Hash：服务器监控指标
HMSET server:web-01 cpu 85.2 mem 72.1 disk 45.0 uptime 86400 status "healthy"
HINCRBY server:web-01 alert_count 1
HGETALL server:web-01

-- 3. List：日志缓冲队列
LPUSH logs:app "2026-05-03T10:00:01 ERROR: Connection refused to db-01"
LPUSH logs:app "2026-05-03T10:00:02 WARN: High memory usage on web-02"
LPUSH logs:app "2026-05-03T10:00:03 INFO: Health check passed for all services"
LRANGE logs:app 0 -1
LTRIM logs:app 0 99

-- 4. Set：在线服务注册
SADD services:healthy "user-api" "order-api" "payment-api"
SADD services:degraded "notification-api"
SUNION services:healthy services:degraded
SCARD services:healthy

-- 5. Sorted Set：告警优先级队列
ZADD alerts:queue 1 "low:disk-warning:web-01" 5 "high:oom-killer:db-01" 10 "critical:service-down:payment-api"
ZREVRANGE alerts:queue 0 -1 WITHSCORES
ZPOPMAX alerts:queue
```

### 练习 2：持久化配置与验证

**目标：** 配置 RDB 和 AOF 持久化，验证数据持久化效果。

```bash
# 创建带持久化配置的 Redis
mkdir -p /tmp/redis-data

cat > /tmp/redis-persistence.conf << 'EOF'
port 6379
dir /data
dbfilename dump.rdb
save 60 5

appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
aof-use-rdb-preamble yes
EOF

docker run -d --name redis-persist \
  -p 6380:6379 \
  -v /tmp/redis-data:/data \
  -v /tmp/redis-persistence.conf:/usr/local/etc/redis/redis.conf \
  redis:7-alpine redis-server /usr/local/etc/redis/redis.conf

# 写入测试数据
for i in $(seq 1 1000); do
  redis-cli -p 6380 SET "test:key:$i" "value:$i"
done

# 查看 RDB 文件
ls -la /tmp/redis-data/dump.rdb

# 查看 AOF 文件
ls -la /tmp/redis-data/appendonly.aof

# 手动触发 RDB
redis-cli -p 6380 BGSAVE
sleep 2
ls -la /tmp/redis-data/dump.rdb

# 验证数据恢复
docker stop redis-persist
docker rm redis-persist
docker run -d --name redis-persist \
  -p 6380:6379 \
  -v /tmp/redis-data:/data \
  -v /tmp/redis-persistence.conf:/usr/local/etc/redis/redis.conf \
  redis:7-alpine redis-server /usr/local/etc/redis/redis.conf

redis-cli -p 6380 DBSIZE
redis-cli -p 6380 GET test:key:500
# 应该返回 "value:500"

# 清理
docker stop redis-persist && docker rm redis-persist
rm -rf /tmp/redis-data /tmp/redis-persistence.conf
```

### 练习 3：Lua 脚本实现分布式锁

**目标：** 用 Lua 脚本实现一个安全的分布式锁，包含加锁、解锁和续期。

```bash
# 启动 Redis
docker run -d --name redis-lock -p 6379:6379 redis:7-alpine
```

```redis
-- 1. 安全加锁（SET NX PX + 唯一标识）
-- 参数：KEYS[1]=锁名, ARGV[1]=持有者UUID, ARGV[2]=过期时间ms
SET lock:order:12345 "uuid-abc-123" NX PX 30000
-- 返回 OK 表示加锁成功，nil 表示已被占用

-- 2. 安全解锁（Lua 脚本保证原子性）
-- 只有持有者才能释放锁
EVAL "
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        redis.call('DEL', KEYS[1])
        return 1
    end
    return 0
" 1 lock:order:12345 "uuid-abc-123"

-- 3. 锁续期（Lua 脚本原子性延长过期时间）
EVAL "
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        redis.call('PEXPIRE', KEYS[1], ARGV[2])
        return 1
    end
    return 0
" 1 lock:order:12345 "uuid-abc-123" 30000

-- 4. 验证锁的互斥性
-- 终端 1：加锁
SET lock:resource "holder-1" NX PX 30000

-- 终端 2：尝试加锁（失败）
SET lock:resource "holder-2" NX PX 30000
-- 返回 nil

-- 终端 2：尝试释放别人的锁（失败）
EVAL "
    if redis.call('GET', KEYS[1]) == ARGV[1] then
        redis.call('DEL', KEYS[1])
        return 1
    end
    return 0
" 1 lock:resource "holder-2"
-- 返回 0

-- 清理
docker stop redis-lock && docker rm redis-lock
```

---

## 🎯 面试题精选

### 1. Redis 为什么这么快？

**参考答案：**
Redis 快主要有四个原因：
1. **纯内存操作：** 数据存储在内存中，读写操作纳秒级，不受磁盘 I/O 限制
2. **I/O 多路复用：** 使用 epoll/kqueue 实现单线程同时处理大量连接，避免多线程的锁竞争和上下文切换
3. **高效数据结构：** SDS、ziplist、skiplist、intset 等针对不同场景深度优化的数据结构
4. **单线程模型：** 没有线程切换开销，没有锁竞争，没有死锁问题

### 2. Redis 的持久化方式有哪些？如何选择？

**参考答案：**
- **RDB：** 定时快照，文件小、恢复快，但可能丢失最后几分钟数据
- **AOF：** 追加写命令日志，数据安全性高，但文件大、恢复慢
- **混合持久化（推荐）：** AOF 重写时使用 RDB 格式存储全量数据 + AOF 增量命令

选择建议：
- 纯缓存场景：仅 RDB
- 数据安全要求高：AOF (everysec) + RDB
- 通用生产环境：混合持久化

### 3. Redis 事务和 MySQL 事务有什么区别？

**参考答案：**
Redis 事务不支持回滚。MULTI/EXEC 只保证命令按顺序执行，不被其他命令打断。如果某个命令有运行时错误，其他命令仍然会执行。MySQL 事务支持完整的 ACID 特性，包括回滚。Redis 也没有隔离级别的概念，因为单线程天然串行化。

### 4. 什么是缓存穿透、缓存击穿、缓存雪崩？如何解决？

**参考答案：**
- **缓存穿透：** 查询不存在的数据，缓存未命中直接打到数据库。解决：布隆过滤器、缓存空值
- **缓存击穿：** 热点 Key 过期瞬间大量请求打到数据库。解决：互斥锁、永不过期 + 异步更新
- **缓存雪崩：** 大量 Key 同时过期或 Redis 宕机。解决：随机 TTL、集群高可用、本地缓存兜底

### 5. Redis 的内存淘汰策略有哪些？生产环境如何选择？

**参考答案：**
八种策略分为两大类：`volatile-*`（只淘汰有过期时间的 Key）和 `allkeys-*`（淘汰所有 Key）。
- 纯缓存场景推荐 `allkeys-lru`（最近最少使用）
- 有热点数据推荐 `allkeys-lfu`（最不经常使用）
- 混合存储（缓存+持久数据）推荐 `volatile-lru`
- 永远不要使用 `noeviction`（除非你能接受写入失败）

### 6. 如何发现和处理 Redis 大 Key？

**参考答案：**
发现方法：
- `redis-cli --bigkeys`：扫描大 Key（在从节点执行）
- `redis-cli --memkeys`：按内存占用排序
- `MEMORY USAGE key`：查看单个 Key 的内存
- `SCAN` 遍历 + `MEMORY USAGE`：自定义脚本

处理方法：
- 使用 `UNLINK`（异步删除）替代 `DEL`
- Hash/Set/ZSet 用 HSCAN/SSCAN/ZSCAN 分批删除
- 业务层拆分大 Key

### 7. Redis Pipeline 和事务有什么区别？

**参考答案：**
- **Pipeline：** 批量发送命令，减少网络往返，但不是原子操作，命令之间可能插入其他客户端的命令
- **事务（MULTI/EXEC）：** 保证命令按顺序原子执行，不会被其他命令打断
- **Pipeline + 事务：** 可以结合使用，在事务中批量发送命令

### 8. Lua 脚本在 Redis 中的作用是什么？有什么限制？

**参考答案：**
Lua 脚本可以实现复杂的原子操作，例如分布式锁的安全释放、原子性 CAS 操作、限流器等。限制包括：
- 执行期间阻塞所有其他命令，脚本必须短小（< 5ms）
- 不能使用不确定性命令（RANDOMKEY、TIME 等）
- Cluster 模式下所有操作的 Key 必须在同一个节点（使用 hash tag）
- 脚本大小限制 1GB

### 9. Redis 单线程模型的瓶颈在哪里？什么时候需要多实例？

**参考答案：**
Redis 的瓶颈通常不在 CPU，而在：
1. **内存容量：** 单实例内存有限，数据量大时需要分片
2. **网络带宽：** 大 Value 或高 QPS 时网卡成为瓶颈
3. **持久化：** fork 子进程和磁盘 I/O 影响性能

当单实例 QPS 超过 10 万或内存超过物理机限制时，考虑使用 Redis Cluster 分片。

### 10. 解释 Redis 的 Copy-on-Write 机制及其风险。

**参考答案：**
Redis 在执行 RDB 或 AOF 重写时，通过 fork() 创建子进程。fork 后父子进程共享内存页，只有当父进程有写操作时才会复制对应的内存页（COW）。

风险：如果 fork 后有大量写操作，会导致大量内存页被复制，内存使用量可能翻倍。在内存使用率接近 100% 时，fork 可能失败。建议：
- 预留 50% 内存给 fork 操作
- 在内存使用率低时触发持久化
- 监控 `used_memory` 和 `used_memory_rss` 的差值

---

## 📚 深入阅读

### 官方文档
- [Redis 官方文档](https://redis.io/docs/) — 最权威的参考
- [Redis 数据类型](https://redis.io/docs/data-types/) — 各数据类型详细说明
- [Redis 持久化](https://redis.io/docs/operate/oss_and_stack/management/persistence/) — RDB/AOF 配置详解
- [Redis 内存优化](https://redis.io/docs/operate/oss_and_stack/management/optimization/memory-optimization/) — 内存优化最佳实践
- [Redis Lua 脚本](https://redis.io/docs/interact/programmability/eval-intro/) — Lua 脚本使用指南

### 推荐书籍
- 《Redis 设计与实现》— 黄健宏，深入理解 Redis 内部实现
- 《Redis 深度历险：核心原理与应用实践》— 钱文品，实战导向
- 《Redis 开发与运维》— 付磊、张益军，运维视角全面覆盖

### 技术博客
- [Redis 命令参考](https://redis.io/commands/) — 所有命令的详细文档
- [Redis University](https://university.redis.com/) — 官方免费课程
- [Redis Labs 博客](https://redis.io/blog/) — 最新特性和最佳实践

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 Redis 单线程为什么快（四个原因）
- [ ] 能说出五种基本数据结构的底层实现
- [ ] 能对比 RDB、AOF、混合持久化的优缺点
- [ ] 能解释 Copy-on-Write 机制及其风险
- [ ] 能说出八种内存淘汰策略及适用场景
- [ ] 能解释 Redis 事务与 MySQL 事务的区别
- [ ] 能说明 Lua 脚本的优势和限制

### 实操检查点
- [ ] 能独立安装和配置 Redis
- [ ] 能配置 RDB 和 AOF 持久化
- [ ] 能使用 redis-cli --bigkeys 发现大 Key
- [ ] 能编写 Lua 脚本实现分布式锁
- [ ] 能使用 Pipeline 批量操作 Redis
- [ ] 能配置内存淘汰策略

### 能力验证标准
- [ ] 能在 5 分钟内解释清楚 Redis 快的原因
- [ ] 能根据业务场景选择合适的持久化策略
- [ ] 能独立排查 Redis 内存问题
- [ ] 能设计并实现一个简单的分布式锁方案
