# Day 75: 数据库综合评估

> 📅 日期：2026-05-03
> 📖 学习主题：MySQL + Redis 综合场景、故障排查、性能优化、架构设计
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 70 (MySQL 基础), Day 71 (MySQL 调优), Day 72 (MySQL 高可用), Day 73 (Redis 运维基础), Day 74 (Redis 高可用与集群)

---

## 🎯 学习目标

完成 Day 75 的学习后，你应该掌握：
- 能够设计 MySQL + Redis 联合架构，解决缓存一致性问题
- 掌握数据库故障排查的完整链路（现象 -> 诊断 -> 根因 -> 修复 -> 预防）
- 能够针对不同业务场景进行数据库性能优化
- 具备设计生产级数据库架构的能力
- 能够回答数据库相关的高级面试题

---

## 📖 核心知识点

### 1. MySQL + Redis 联合架构

#### 1.1 为什么需要 MySQL + Redis

```
┌─────────────────────────────────────────────────────────────────┐
│                MySQL 与 Redis 对比                              │
│                                                                 │
│  特性         │ MySQL            │ Redis                        │
│  ────────────┼──────────────────┼───────────────────────────── │
│  存储介质     │ 磁盘             │ 内存                          │
│  读延迟       │ 1-10ms           │ 0.1-1ms                      │
│  写延迟       │ 5-50ms           │ 0.1-1ms                      │
│  QPS          │ 5000-20000       │ 100000-500000                │
│  数据容量     │ TB 级            │ GB 级（受内存限制）            │
│  查询能力     │ SQL，复杂查询     │ Key-Value，简单查询           │
│  事务         │ ACID 完整支持     │ 有限支持（MULTI/EXEC）        │
│  持久化       │ 完善              │ RDB/AOF（可能丢数据）         │
│  扩展性       │ 分库分表          │ Cluster 分片                  │
│  适用场景     │ 核心业务数据       │ 缓存、会话、计数器            │
└─────────────────────────────────────────────────────────────────┘

结论：MySQL 存储核心数据，Redis 做缓存加速，两者互补。
```

#### 1.2 经典联合架构

```
┌─────────────────────────────────────────────────────────────────┐
│                MySQL + Redis 联合架构                            │
│                                                                 │
│  ┌──────────┐                                                   │
│  │  Client  │                                                   │
│  │  请求     │                                                   │
│  └────┬─────┘                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────┐    1. 先查缓存    ┌──────────┐                   │
│  │  应用层   │ ────────────────▶│  Redis   │                   │
│  │          │                   │  缓存     │                   │
│  │          │ ◀── 2a. 命中 ────│          │                   │
│  │          │                   └──────────┘                   │
│  │          │                                                   │
│  │          │    2b. 未命中     ┌──────────┐                   │
│  │          │ ────────────────▶│  MySQL   │                   │
│  │          │                   │  主库     │                   │
│  │          │ ◀── 3. 返回数据 ──│          │                   │
│  │          │                   └────┬─────┘                   │
│  │          │                        │ 同步复制                 │
│  │          │    4. 写入缓存    ┌────▼─────┐                   │
│  │          │ ────────────────▶│  MySQL   │                   │
│  └──────────┘                   │  从库     │                   │
│                                 └──────────┘                   │
│                                                                 │
│  读请求路径：Client → Redis (命中直接返回) → MySQL → 写回 Redis   │
│  写请求路径：Client → MySQL → 删除/更新 Redis                    │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.3 缓存一致性策略

缓存一致性是 MySQL + Redis 架构中最核心的问题。以下是四种主流方案的详细对比。

**方案一：Cache Aside Pattern（旁路缓存，最常用）**

```
读流程：
  1. 读 Redis → 命中则返回
  2. 未命中 → 读 MySQL
  3. 将结果写入 Redis（设置 TTL）
  4. 返回数据

写流程：
  1. 更新 MySQL
  2. 删除 Redis 缓存（而不是更新！）

为什么是「删除」而不是「更新」？
  - 避免并发写导致缓存脏数据
  - 删除后下次读时自动从 DB 加载最新数据
  - 更新缓存可能触发不必要的计算（缓存值需要复杂计算）
```

```python
# Cache Aside Pattern 实现示例

import redis
import json
import pymysql

r = redis.Redis(host='localhost', port=6379, db=0)
CACHE_TTL = 3600  # 1 小时

def get_user(user_id):
    """读取用户信息：先查缓存，未命中查数据库"""
    cache_key = f"user:{user_id}"

    # 1. 先查 Redis
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # 2. 缓存未命中，查 MySQL
    conn = pymysql.connect(host='localhost', user='root', password='pass', db='mydb')
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
    finally:
        conn.close()

    if user:
        # 3. 写入 Redis 缓存
        r.setex(cache_key, CACHE_TTL, json.dumps(user, default=str))

    return user

def update_user(user_id, data):
    """更新用户信息：先更新数据库，再删除缓存"""
    # 1. 更新 MySQL
    conn = pymysql.connect(host='localhost', user='root', password='pass', db='mydb')
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET name=%s, email=%s WHERE id=%s",
                (data['name'], data['email'], user_id)
            )
        conn.commit()
    finally:
        conn.close()

    # 2. 删除 Redis 缓存
    r.delete(f"user:{user_id}")
```

**方案二：延迟双删**

```
解决 Cache Aside 的并发问题：

  线程 A（写）              线程 B（读）
      │                        │
      │ 1. 更新 MySQL          │
      │                        │ 2. 读 Redis（旧数据）
      │                        │ 3. 缓存未命中，读 MySQL
      │                        │    （可能读到旧数据！）
      │ 4. 删除 Redis          │
      │                        │ 5. 写入旧数据到 Redis ← 问题！
      │
      │ 6. 延迟 500ms 再删一次  │
      │
      │ 7. 再次删除 Redis      │  ✅ 旧缓存被清除

延迟双删流程：
  1. 先删除 Redis 缓存
  2. 更新 MySQL
  3. 延迟一段时间（大于一次读请求的耗时）
  4. 再次删除 Redis 缓存
```

```python
import time
import threading

def update_user_delayed_double_delete(user_id, data):
    """延迟双删策略"""
    cache_key = f"user:{user_id}"

    # 1. 先删缓存
    r.delete(cache_key)

    # 2. 更新数据库
    conn = pymysql.connect(host='localhost', user='root', password='pass', db='mydb')
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET name=%s, email=%s WHERE id=%s",
                (data['name'], data['email'], user_id)
            )
        conn.commit()
    finally:
        conn.close()

    # 3. 延迟删除（异步执行，不阻塞当前请求）
    def delayed_delete():
        time.sleep(0.5)  # 延迟 500ms
        r.delete(cache_key)

    threading.Thread(target=delayed_delete).start()
```

**方案三：基于 Binlog 的异步更新（Canal + MQ）**

```
┌─────────────────────────────────────────────────────────────────┐
│           Binlog 异步更新缓存架构                                │
│                                                                 │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐         │
│  │ App    │───▶│ MySQL  │───▶│ Canal  │───▶│ Kafka  │         │
│  │        │    │        │    │        │    │        │         │
│  └────────┘    └────────┘    └────────┘    └───┬────┘         │
│                                                │               │
│                                           ┌────▼────┐          │
│                                           │ Consumer │          │
│                                           │ 更新缓存  │          │
│                                           └────┬────┘          │
│                                                │               │
│                                           ┌────▼────┐          │
│                                           │  Redis  │          │
│                                           │  缓存    │          │
│                                           └─────────┘          │
│                                                                 │
│  优点：                                                         │
│  - 应用层代码简单，只需操作 MySQL                                │
│  - 缓存更新与业务解耦                                           │
│  - 保证最终一致性                                               │
│  - 支持多级缓存更新                                             │
│                                                                 │
│  缺点：                                                         │
│  - 架构复杂，依赖 Canal + MQ                                    │
│  - 有延迟（秒级）                                               │
│  - 需要处理消息消费失败的情况                                    │
└─────────────────────────────────────────────────────────────────┘
```

```python
# Canal Consumer 示例（简化版）

from kafka import KafkaConsumer
import json
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
consumer = KafkaConsumer(
    'canal_db_mydb_users',
    bootstrap_servers=['kafka:9092'],
    group_id='redis-cache-updater',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

def process_binlog_event(event):
    """处理 binlog 事件，更新缓存"""
    table = event.get('table')
    event_type = event.get('type')  # INSERT, UPDATE, DELETE

    if table == 'users':
        if event_type in ('INSERT', 'UPDATE'):
            user_data = event.get('after')  # 更新后的数据
            user_id = user_data['id']
            r.setex(f"user:{user_id}", 3600, json.dumps(user_data, default=str))
        elif event_type == 'DELETE':
            user_id = event.get('before', {}).get('id')
            if user_id:
                r.delete(f"user:{user_id}")

for message in consumer:
    event = message.value
    try:
        process_binlog_event(event)
    except Exception as e:
        print(f"处理失败: {e}, offset: {message.offset}")
        # 失败重试或写入死信队列
```

**方案四：Read/Write Through（读写穿透）**

```
应用层通过缓存层统一读写，缓存层负责与数据库交互：

  写请求：App → Cache → DB
  读请求：App → Cache → (miss) → DB → Cache

  ┌────────┐    ┌─────────────────────┐    ┌────────┐
  │  App   │───▶│   Cache Layer       │───▶│  MySQL │
  │        │    │  (Redis + 读写逻辑)  │    │        │
  │        │◀───│                     │◀───│        │
  └────────┘    └─────────────────────┘    └────────┘

  优点：应用层代码简洁
  缺点：缓存层复杂度高，耦合严重
```

**缓存一致性策略对比：**

```
┌──────────────────────────────────────────────────────────────────┐
│                缓存一致性策略对比                                  │
│                                                                  │
│  策略              │ 一致性 │ 复杂度 │ 延迟   │ 适用场景          │
│  ─────────────────┼────────┼────────┼────────┼────────────────  │
│  Cache Aside       │ 最终   │ 低     │ 实时   │ 通用场景（推荐）  │
│  延迟双删          │ 最终   │ 中     │ 亚秒级 │ 写多读少          │
│  Binlog + MQ       │ 最终   │ 高     │ 秒级   │ 大规模、多级缓存  │
│  Read/Write Through│ 最终   │ 高     │ 实时   │ 统一数据访问层    │
│                                                                  │
│  SRE 推荐：Cache Aside + 合理 TTL，简单可靠。                     │
│  大规模场景用 Binlog + MQ 实现最终一致性。                        │
└──────────────────────────────────────────────────────────────────┘
```

#### 1.4 缓存三大问题

**缓存穿透（Cache Penetration）：**

```
问题：查询不存在的数据，缓存永远未命中，每次都打到数据库

  Client ──▶ Redis (miss) ──▶ MySQL (null) ──▶ 返回 null
  Client ──▶ Redis (miss) ──▶ MySQL (null) ──▶ 返回 null
  ... 重复，数据库压力持续增大

场景：恶意攻击（随机 ID 查询）、业务 bug（查询已删除的数据）

解决方案：

  1. 缓存空值
     查询结果为空时，也缓存一个空值（TTL 设短一点）
     SET user:999999 "" EX 60

  2. 布隆过滤器（Bloom Filter）
     ┌───────────────────────────────────────────────┐
     │  布隆过滤器：在缓存前增加一层过滤               │
     │                                               │
     │  Client ──▶ 布隆过滤器 ──▶ Redis ──▶ MySQL    │
     │              │                                │
     │              ├─ 不存在 → 直接返回 null         │
     │              └─ 可能存在 → 继续查询            │
     │                                               │
     │  特点：可能误判存在，不会误判不存在             │
     │  内存占用极小（1 亿数据约 100MB）              │
     └───────────────────────────────────────────────┘
```

```python
# 布隆过滤器实现（使用 Redis 的 RedisBloom 模块）
import redis

r = redis.Redis(host='localhost', port=6379)

# 创建布隆过滤器
r.execute_command('BF.RESERVE', 'user_filter', 0.001, 1000000)
# 0.001: 误判率 0.1%
# 1000000: 预期元素数量

# 添加元素
r.execute_command('BF.ADD', 'user_filter', 'user:1001')
r.execute_command('BF.ADD', 'user_filter', 'user:1002')

# 检查元素
exists = r.execute_command('BF.EXISTS', 'user_filter', 'user:1001')  # 1
not_exists = r.execute_command('BF.EXISTS', 'user_filter', 'user:99999')  # 0
```

**缓存击穿（Cache Breakdown）：**

```
问题：热点 Key 过期瞬间，大量并发请求直接打到数据库

  时间线：
  t0: hot:key 过期
  t1: 100 个并发请求同时查 Redis → miss
  t2: 100 个请求同时打到 MySQL → 数据库压力激增
  t3: 第 1 个请求返回，写入缓存
  t4: 其他 99 个请求也返回（重复写入）

解决方案：

  1. 互斥锁（Mutex Lock）
     ┌────────────────────────────────────────────────┐
     │  只允许一个请求去查数据库，其他请求等待          │
     │                                                │
     │  请求 1: Redis miss → 获取锁 → 查 DB → 写缓存  │
     │  请求 2: Redis miss → 获取锁失败 → 等待 → 重试  │
     │  请求 3: Redis miss → 获取锁失败 → 等待 → 重试  │
     │  ...                                           │
     │  请求 1 完成 → 释放锁 → 其他请求从缓存读取      │
     └────────────────────────────────────────────────┘
```

```python
import redis
import time

r = redis.Redis(host='localhost', port=6379)

def get_with_mutex(key, db_query_func, ttl=3600, lock_timeout=10):
    """带互斥锁的缓存读取"""
    # 1. 先查缓存
    value = r.get(key)
    if value:
        return value

    # 2. 尝试获取锁
    lock_key = f"lock:{key}"
    lock_acquired = r.set(lock_key, "1", nx=True, ex=lock_timeout)

    if lock_acquired:
        try:
            # 双重检查（其他请求可能已经写入缓存）
            value = r.get(key)
            if value:
                return value

            # 3. 查询数据库
            value = db_query_func()

            # 4. 写入缓存
            if value:
                r.setex(key, ttl, value)
            else:
                r.setex(key, 60, "")  # 缓存空值

            return value
        finally:
            # 5. 释放锁
            r.delete(lock_key)
    else:
        # 6. 未获取到锁，等待后重试
        time.sleep(0.1)
        return get_with_mutex(key, db_query_func, ttl, lock_timeout)
```

**缓存雪崩（Cache Avalanche）：**

```
问题：大量 Key 同时过期，或 Redis 宕机，请求全部打到数据库

  场景 1：大量 Key 同时过期
  ┌────────────────────────────────────────────────┐
  │  批量导入数据时设置了相同的 TTL                   │
  │  t0: 10000 个 Key 同时过期                      │
  │  t1: 10000 个请求同时打到 MySQL                 │
  └────────────────────────────────────────────────┘

  场景 2：Redis 宕机
  ┌────────────────────────────────────────────────┐
  │  Redis 故障，所有请求直接打到 MySQL              │
  └────────────────────────────────────────────────┘

解决方案：

  1. 随机 TTL（解决同时过期）
     ttl = base_ttl + random(0, 300)
     避免同一时间大量 Key 同时过期

  2. 多级缓存（解决 Redis 宕机）
     ┌────────────────────────────────────────────┐
     │  Client → 本地缓存 → Redis → MySQL         │
     │  即使 Redis 宕机，本地缓存仍能抵挡部分请求   │
     └────────────────────────────────────────────┘

  3. 熔断降级
     当数据库压力超过阈值时，触发熔断
     返回默认值或错误页面，保护数据库

  4. Redis 高可用
     使用 Sentinel 或 Cluster，避免单点故障
```

```python
import random

def set_with_random_ttl(key, value, base_ttl=3600, jitter=300):
    """设置随机 TTL，避免缓存雪崩"""
    ttl = base_ttl + random.randint(0, jitter)
    r.setex(key, ttl, value)
```

---

### 2. SRE 故障排查方法论

#### 2.1 故障排查五步法

```
┌─────────────────────────────────────────────────────────────────┐
│                数据库故障排查五步法                               │
│                                                                 │
│  1. 现象确认                                                    │
│     └─ 告警内容、影响范围、持续时间                              │
│     └─ 是 MySQL 问题还是 Redis 问题？                           │
│     └─ 是全量受影响还是部分受影响？                              │
│                                                                 │
│  2. 快速止损                                                    │
│     └─ 限流：保护数据库不被打垮                                 │
│     └─ 熔断：暂时切断问题链路                                   │
│     └─ 降级：返回默认值或缓存数据                               │
│     └─ 回滚：如果是变更引起，立即回滚                           │
│                                                                 │
│  3. 诊断定位                                                    │
│     └─ 查看监控指标（QPS、延迟、错误率）                        │
│     └─ 分析慢查询日志                                          │
│     └─ 检查系统资源（CPU、内存、磁盘、网络）                    │
│     └─ 检查连接数和线程状态                                    │
│                                                                 │
│  4. 根因分析                                                    │
│     └─ 是代码问题？配置问题？资源问题？还是外部依赖问题？        │
│     └─ 是偶发还是必现？                                        │
│     └─ 是否有最近的变更？                                      │
│                                                                 │
│  5. 修复与预防                                                  │
│     └─ 短期：修复当前问题                                      │
│     └─ 长期：优化代码、调整配置、增加监控                       │
│     └─ 复盘：编写 Post-Mortem 文档                             │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 MySQL 故障排查

**案例：MySQL 连接数耗尽**

```
故障现象：
  - 告警：MySQL Threads_connected 超过阈值
  - 应用报错：Too many connections
  - 影响范围：所有依赖 MySQL 的服务

排查过程：

  1. 查看当前连接数
     mysql> SHOW STATUS LIKE 'Threads_connected';
     └─ Threads_connected: 500（max_connections 也是 500）

  2. 查看连接来源
     mysql> SELECT user, host, db, command, time, state
            FROM information_schema.processlist
            ORDER BY time DESC LIMIT 20;
     └─ 发现大量 Sleep 连接，time > 300 秒

  3. 分析连接池配置
     └─ 应用端连接池 maxPoolSize=50，共 10 个实例
     └─ 理论最大连接 500，刚好等于 max_connections
     └─ 连接池未配置空闲连接回收

  4. 根因
     └─ 应用连接池未配置空闲连接超时回收
     └─ 每次发版重启时旧连接未正确关闭
     └─ 连接数逐渐累积直到耗尽

修复：
  1. 紧急：kill 空闲连接
     SELECT CONCAT('KILL ', id, ';')
     FROM information_schema.processlist
     WHERE command = 'Sleep' AND time > 300;

  2. 调整连接池配置
     maxPoolSize=30（降低单实例连接数）
     idleTimeout=60000（空闲 60 秒回收）
     maxLifetime=1800000（连接最大存活 30 分钟）

  3. 增加监控
     Threads_connected > 80% max_connections → 告警
```

**案例：MySQL 慢查询导致 CPU 飙升**

```
故障现象：
  - MySQL CPU 使用率 95%+
  - 应用接口 P99 延迟 > 5 秒
  - 慢查询日志大量新增

排查过程：

  1. 查看慢查询
     mysql> SELECT * FROM mysql.slow_log
            ORDER BY query_time DESC LIMIT 10;
     └─ 发现全表扫描: SELECT * FROM orders WHERE status='pending'

  2. 分析执行计划
     mysql> EXPLAIN SELECT * FROM orders WHERE status='pending';
     └─ type: ALL（全表扫描）
     └─ rows: 5000000
     └─ Extra: Using where

  3. 检查索引
     mysql> SHOW INDEX FROM orders;
     └─ status 字段没有索引！

  4. 根因
     └─ orders 表 500 万行，status 字段无索引
     └─ 每次查询扫描全表，CPU 和 I/O 压力大

修复：
  1. 添加索引
     CREATE INDEX idx_orders_status ON orders(status);

  2. 优化查询（避免 SELECT *）
     SELECT id, order_no, amount FROM orders WHERE status='pending';

  3. 监控
     慢查询数量 > 10/分钟 → 告警
```

#### 2.3 Redis 故障排查

**案例：Redis 延迟突增**

```
故障现象：
  - Redis P99 延迟从 1ms 飙升到 100ms+
  - 应用超时报错增多
  - Redis CPU 使用率正常（< 50%）

排查过程：

  1. 检查慢查询
     SLOWLOG GET 20
     └─ 发现 KEYS pattern:* 命令
     └─ KEYS 命令 O(N) 复杂度，阻塞主线程

  2. 检查持久化
     INFO persistence
     └─ rdb_last_bgsave_time_sec: 45
     └─ aof_rewrite_in_progress: 1
     └─ fork 耗时长，COW 导致内存压力

  3. 检查系统资源
     └─ iostat: 磁盘 I/O 利用率 98%
     └─ AOF everysec + BGSAVE 同时进行

  4. 检查大 Key
     redis-cli --bigkeys
     └─ 发现 Hash: cache:user:all 占 50MB

  5. 根因
     └─ 代码使用 KEYS 命令（生产禁用）
     └─ AOF 重写和 RDB 同时进行，磁盘 I/O 饱和
     └─ 大 Key 操作耗时

修复：
  1. 紧急：替换 KEYS 为 SCAN
  2. 调整持久化策略：错开 RDB 和 AOF 重写时间
  3. 拆分大 Key
  4. 增加延迟监控告警
```

---

### 3. 性能优化综合

#### 3.1 MySQL 性能优化清单

```
┌─────────────────────────────────────────────────────────────────┐
│                MySQL 性能优化清单                                │
│                                                                 │
│  ┌─ 查询优化 ──────────────────────────────────────────────┐   │
│  │  ✅ 使用 EXPLAIN 分析执行计划                            │   │
│  │  ✅ 避免 SELECT *，只查需要的列                          │   │
│  │  ✅ 合理使用索引（覆盖索引、联合索引）                   │   │
│  │  ✅ 避免在 WHERE 中对索引列使用函数                      │   │
│  │  ✅ 分页查询使用 id > offset 而非 LIMIT offset          │   │
│  │  ✅ 大事务拆分为小事务                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ 索引优化 ──────────────────────────────────────────────┐   │
│  │  ✅ 遵循最左前缀原则                                     │   │
│  │  ✅ 避免过多索引（影响写性能）                           │   │
│  │  ✅ 定期分析索引使用情况                                 │   │
│  │  ✅ 删除未使用的索引                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ 配置优化 ──────────────────────────────────────────────┐   │
│  │  ✅ innodb_buffer_pool_size: 物理内存的 60-80%           │   │
│  │  ✅ innodb_log_file_size: 1-2GB                         │   │
│  │  ✅ innodb_flush_log_at_trx_commit: 1（安全）或 2（性能）│   │
│  │  ✅ max_connections: 根据业务需要设置                    │   │
│  │  ✅ query_cache_type: OFF（MySQL 8.0 已移除）            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ 架构优化 ──────────────────────────────────────────────┐   │
│  │  ✅ 读写分离（主写从读）                                 │   │
│  │  ✅ 分库分表（大数据量场景）                             │   │
│  │  ✅ Redis 缓存热点数据                                   │   │
│  │  ✅ 连接池配置优化                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Redis 性能优化清单

```
┌─────────────────────────────────────────────────────────────────┐
│                Redis 性能优化清单                                │
│                                                                 │
│  ┌─ 命令优化 ──────────────────────────────────────────────┐   │
│  │  ✅ 使用 SCAN 替代 KEYS                                  │   │
│  │  ✅ 使用 Pipeline 批量操作                               │   │
│  │  ✅ 使用 MGET/MSET 批量读写                              │   │
│  │  ✅ 避免大 Key（Hash/Set 元素 < 5000）                   │   │
│  │  ✅ 使用 UNLINK 替代 DEL 删除大 Key                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ 内存优化 ──────────────────────────────────────────────┐   │
│  │  ✅ 设置 maxmemory 和淘汰策略                            │   │
│  │  ✅ 使用 Hash 存储对象（比多个 String 省内存）            │   │
│  │  ✅ 设置合理的 TTL，避免内存无限增长                      │   │
│  │  ✅ 定期运行 --bigkeys 检查大 Key                        │   │
│  │  ✅ 开启 activedefrag 碎片整理                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ 连接优化 ──────────────────────────────────────────────┐   │
│  │  ✅ 使用连接池，避免频繁创建/销毁连接                     │   │
│  │  ✅ 设置合理的连接超时和读写超时                          │   │
│  │  ✅ 监控 connected_clients 数量                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─ 架构优化 ──────────────────────────────────────────────┐   │
│  │  ✅ 热点数据使用本地缓存（Caffeine/Guava Cache）          │   │
│  │  ✅ 读写分离（从节点承担读请求）                          │   │
│  │  ✅ 数据分片（Redis Cluster）                            │   │
│  │  ✅ 避免单个 Key 成为热点                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.3 分页查询优化

```sql
-- 慢分页（OFFSET 越大越慢）
SELECT * FROM orders ORDER BY id LIMIT 10 OFFSET 1000000;
-- 扫描 1000010 行，丢弃前 1000000 行

-- 快分页（基于游标）
SELECT * FROM orders WHERE id > 1000000 ORDER BY id LIMIT 10;
-- 只扫描 10 行（需要 id 上有索引）

-- 延迟关联（另一种优化方式）
SELECT o.* FROM orders o
INNER JOIN (SELECT id FROM orders ORDER BY id LIMIT 10 OFFSET 1000000) t
ON o.id = t.id;
-- 子查询只扫描 id 列（覆盖索引），然后再关联取完整数据
```

---

### 4. 架构设计

#### 4.1 电商系统数据库架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                电商系统数据库架构                                 │
│                                                                 │
│  ┌──────────┐                                                   │
│  │  用户    │                                                   │
│  └────┬─────┘                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────┐                                                   │
│  │  Nginx   │  静态资源缓存、负载均衡                           │
│  └────┬─────┘                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────┐                                                   │
│  │ 应用集群  │  无状态，水平扩展                                │
│  │          │                                                   │
│  │ ┌──────┐ │  本地缓存（L1 Cache）                            │
│  │ │Caffeine│ │  热点数据 5 秒 TTL                              │
│  │ └──────┘ │                                                   │
│  └────┬─────┘                                                   │
│       │                                                         │
│       ├──────────────────┬─────────────────┐                   │
│       ▼                  ▼                 ▼                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐             │
│  │  Redis   │    │  MySQL   │    │ Elasticsearch │             │
│  │ Cluster  │    │  主从     │    │ 搜索引擎      │             │
│  │          │    │          │    │              │             │
│  │ - 会话   │    │ - 订单   │    │ - 商品搜索   │             │
│  │ - 缓存   │    │ - 用户   │    │ - 日志分析   │             │
│  │ - 限流   │    │ - 商品   │    │              │             │
│  │ - 分布式锁│    │ - 支付   │    │              │             │
│  └──────────┘    └──────────┘    └──────────────┘             │
│                                                                 │
│  数据流向：                                                      │
│  读请求 → 本地缓存 → Redis → MySQL                              │
│  写请求 → MySQL → 删除 Redis → 异步同步 ES                      │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.2 各场景数据存储选型

```
┌──────────────────────────────────────────────────────────────────┐
│                数据存储选型指南                                    │
│                                                                  │
│  场景              │ 存储方案                 │ 原因             │
│  ─────────────────┼─────────────────────────┼───────────────── │
│  用户 Session      │ Redis String/Hash       │ 读写快、自动过期  │
│  商品详情缓存       │ Redis Hash              │ 结构化、可部分更新│
│  接口限流          │ Redis String (INCR)     │ 原子操作、高性能  │
│  分布式锁          │ Redis String (SET NX)   │ 原子设置+过期     │
│  排行榜           │ Redis Sorted Set        │ 天然有序、高效    │
│  消息队列          │ Redis Stream / Kafka    │ Stream 轻量、Kafka可靠 │
│  搜索             │ Elasticsearch           │ 全文搜索、聚合    │
│  订单数据          │ MySQL                   │ 事务、复杂查询    │
│  用户数据          │ MySQL                   │ 关系型、强一致    │
│  支付流水          │ MySQL                   │ ACID、审计       │
│  日志             │ ELK / ClickHouse        │ 海量写入、分析    │
│  文件存储          │ S3 / MinIO              │ 对象存储、低成本  │
│  配置中心          │ etcd / Consul           │ 一致性、Watch     │
│  UV 统计          │ Redis HyperLogLog       │ 概率去重、极低内存│
│  布尔统计          │ Redis Bitmap            │ 极低内存占用      │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.3 容量规划

```
┌─────────────────────────────────────────────────────────────────┐
│                数据库容量规划                                    │
│                                                                 │
│  MySQL 容量规划：                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  数据量估算：                                            │   │
│  │  - 单行大小 × 日增量 × 保留天数 = 总数据量               │   │
│  │  - 例：500B × 100万/天 × 365天 = 182GB/年               │   │
│  │                                                         │   │
│  │  QPS 估算：                                              │   │
│  │  - 日活用户 × 人均请求数 / 86400 = 平均 QPS              │   │
│  │  - 峰值 QPS = 平均 QPS × 3-5 倍                         │   │
│  │  - 例：100万 × 50 / 86400 ≈ 579 QPS，峰值约 2000 QPS   │   │
│  │                                                         │   │
│  │  资源配置：                                              │   │
│  │  - CPU: 核心数 ≥ QPS / 5000                             │   │
│  │  - 内存: ≥ innodb_buffer_pool_size (数据量的 60-80%)     │   │
│  │  - 磁盘: SSD, IOPS ≥ 10000                             │   │
│  │  - 网络: ≥ QPS × 平均响应大小                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Redis 容量规划：                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  内存估算：                                              │   │
│  │  - Key 数量 × 单 Key 大小 × 1.2 (碎片系数) = 总内存     │   │
│  │  - 例：100万 × 1KB × 1.2 = 1.2GB                       │   │
│  │                                                         │   │
│  │  QPS 估算：                                              │   │
│  │  - 单实例：10万 QPS                                      │   │
│  │  - Cluster：N × 10万 QPS                                 │   │
│  │                                                         │   │
│  │  资源配置：                                              │   │
│  │  - 内存: ≥ 缓存数据量 × 2 (fork COW 预留)               │   │
│  │  - CPU: 4-8 核（单实例）                                 │   │
│  │  - 网络: 万兆网卡（大 Value 场景）                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

### 5. SRE 实战案例：完整故障排查链路

#### 案例：双十一大促数据库性能劣化

```
故障时间线：

  T-7 天: 容量评估，MySQL 和 Redis 资源充足
  T-1 天: 预热缓存，热门商品数据加载到 Redis
  T+0:    大促开始，流量瞬间涌入

  T+5min:
    - 告警：Redis 内存使用率 > 90%
    - 告警：MySQL CPU > 80%
    - 应用日志：大量 Redis OOM 错误

  T+8min:
    - 告警：MySQL 慢查询 > 100/分钟
    - 应用日志：MySQL 连接超时
    - 业务影响：下单成功率从 99.9% 降至 85%

排查过程：

  第一步：确认影响范围
    └─ 下单接口受影响，查询接口正常
    └─ Redis 和 MySQL 同时出现问题

  第二步：快速止损
    └─ 扩容 Redis 内存（maxmemory 8GB → 16GB）
    └─ 开启限流：下单接口 QPS 限制为 5000
    └─ 降级非核心功能：推荐、评价

  第三步：诊断定位
    └─ Redis: redis-cli --bigkeys
    │  └─ 发现 cart:user:* 占用 6GB（购物车数据）
    │  └─ 每个用户购物车平均 2MB，100 万用户 = 2TB
    │  └─ 但只有 3 万用户设置了 TTL，其他永久保存
    │
    └─ MySQL: SHOW PROCESSLIST
       └─ 大量查询: SELECT * FROM products WHERE id IN (...)
       └─ IN 子句包含 100+ 个 ID
       └─ 执行计划显示全表扫描

  第四步：根因分析
    └─ Redis 根因：
    │  └─ 购物车数据没有设置 TTL
    │  └─ 历史用户购物车数据累积
    │  └─ 大促前预热数据进一步加剧
    │
    └─ MySQL 根因：
       └─ 大量 IN 查询，优化器选择了全表扫描
       └─ 缺少合适的联合索引
       └─ 缓存未命中时直接打到数据库

  第五步：修复
    └─ 紧急：给所有 cart:user:* 设置 TTL (7 天)
    └─ 紧急：拆分 IN 查询为多个小查询
    └─ 紧急：添加 products 表的索引
    └─ 后续：
       └─ 购物车数据迁移到 MySQL，Redis 只缓存热门商品
       └─ 大促前自动扩容 Redis 和 MySQL
       └─ 增加购物车数据量监控

复盘总结：
  1. 容量评估只考虑了正常流量，未考虑大促场景
  2. 购物车数据缺少 TTL 策略
  3. 查询语句未经过 DBA 审核
  4. 缓存预热只预热了商品，未预热购物车
```

---

## 💻 实战练习

### 练习 1：MySQL + Redis 缓存一致性实践

**目标：** 实现 Cache Aside Pattern，验证缓存一致性。

```bash
# 启动 MySQL 和 Redis
docker run -d --name mysql-lab -p 3306:3306 \
    -e MYSQL_ROOT_PASSWORD=lab123 -e MYSQL_DATABASE=testdb \
    mysql:8.0

docker run -d --name redis-lab -p 6379:6379 redis:7-alpine

# 等待 MySQL 启动
sleep 15

# 创建测试表
docker exec -i mysql-lab mysql -uroot -plab123 testdb << 'SQL'
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(200) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO users (name, email) VALUES
('zhangsan', 'zhangsan@example.com'),
('lisi', 'lisi@example.com'),
('wangwu', 'wangwu@example.com');
SQL
```

```python
# cache_aside_demo.py
import redis
import json
import time
import pymysql

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
CACHE_TTL = 300  # 5 分钟

def get_db_conn():
    return pymysql.connect(
        host='localhost', port=3306, user='root', password='lab123',
        db='testdb', cursorclass=pymysql.cursors.DictCursor
    )

def get_user(user_id):
    """Cache Aside: 读"""
    cache_key = f"user:{user_id}"

    # 1. 查缓存
    cached = r.get(cache_key)
    if cached:
        print(f"[Cache Hit] user:{user_id}")
        return json.loads(cached)

    # 2. 缓存未命中，查数据库
    print(f"[Cache Miss] user:{user_id}, querying MySQL...")
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
    finally:
        conn.close()

    if user:
        # 3. 写入缓存
        r.setex(cache_key, CACHE_TTL, json.dumps(user, default=str))
        print(f"[Cache Set] user:{user_id}")

    return user

def update_user(user_id, name=None, email=None):
    """Cache Aside: 写"""
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            updates = []
            params = []
            if name:
                updates.append("name=%s")
                params.append(name)
            if email:
                updates.append("email=%s")
                params.append(email)
            params.append(user_id)
            cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id=%s", params)
        conn.commit()
        print(f"[DB Update] user:{user_id}")
    finally:
        conn.close()

    # 删除缓存（而不是更新）
    r.delete(f"user:{user_id}")
    print(f"[Cache Delete] user:{user_id}")

# 测试
if __name__ == "__main__":
    # 第一次读：缓存未命中
    user = get_user(1)
    print(f"Result: {user}\n")

    # 第二次读：缓存命中
    user = get_user(1)
    print(f"Result: {user}\n")

    # 更新用户
    update_user(1, name="zhangsan_updated")
    print()

    # 更新后读：缓存已删除，重新从 DB 加载
    user = get_user(1)
    print(f"Result: {user}\n")

    # 清理
    r.flushdb()
```

```bash
python3 cache_aside_demo.py

# 预期输出：
# [Cache Miss] user:1, querying MySQL...
# [Cache Set] user:1
# Result: {'id': 1, 'name': 'zhangsan', 'email': 'zhangsan@example.com', ...}
#
# [Cache Hit] user:1
# Result: {'id': 1, 'name': 'zhangsan', 'email': 'zhangsan@example.com', ...}
#
# [DB Update] user:1
# [Cache Delete] user:1
#
# [Cache Miss] user:1, querying MySQL...
# [Cache Set] user:1
# Result: {'id': 1, 'name': 'zhangsan_updated', 'email': 'zhangsan@example.com', ...}
```

### 练习 2：缓存穿透防护

**目标：** 使用布隆过滤器防护缓存穿透。

```bash
# 安装 RedisBloom 模块
docker run -d --name redis-bloom -p 6379:6379 \
    redis/redis-stack-server:latest
```

```python
# bloom_filter_demo.py
import redis
import json
import random
import time

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def setup():
    """初始化：创建布隆过滤器并加载有效用户 ID"""
    # 创建布隆过滤器（误判率 0.1%，预期 100 万元素）
    try:
        r.execute_command('BF.RESERVE', 'user_filter', 0.001, 1000000)
    except redis.ResponseError as e:
        if 'exists' not in str(e).lower():
            raise

    # 模拟数据库中的有效用户 ID
    valid_users = [f"user:{i}" for i in range(1, 10001)]

    # 批量添加到布隆过滤器
    pipe = r.pipeline()
    for user_id in valid_users:
        pipe.execute_command('BF.ADD', 'user_filter', user_id)
    pipe.execute()

    # 缓存部分用户数据到 Redis
    for i in range(1, 101):  # 缓存前 100 个
        r.setex(f"user:{i}", 300, json.dumps({
            "id": i, "name": f"user_{i}", "email": f"user_{i}@example.com"
        }))

    print(f"Setup complete: 10000 users in bloom filter, 100 in cache")

def get_user_with_bloom(user_id):
    """带布隆过滤器的查询"""
    cache_key = f"user:{user_id}"

    # 1. 先查布隆过滤器
    exists = r.execute_command('BF.EXISTS', 'user_filter', user_id)
    if not exists:
        print(f"[Bloom Filter] user:{user_id} definitely not exists, skip DB")
        return None

    # 2. 查 Redis 缓存
    cached = r.get(cache_key)
    if cached:
        print(f"[Cache Hit] user:{user_id}")
        return json.loads(cached)

    # 3. 查数据库（模拟）
    user_num = int(user_id.split(':')[1])
    if 1 <= user_num <= 10000:
        user = {"id": user_num, "name": f"user_{user_num}", "email": f"user_{user_num}@example.com"}
        r.setex(cache_key, 300, json.dumps(user))
        print(f"[DB Query + Cache Set] user:{user_id}")
        return user

    # 布隆过滤器误判的情况（概率极低）
    print(f"[Bloom Filter False Positive] user:{user_id}")
    return None

def get_user_without_bloom(user_id):
    """不带布隆过滤器的查询（对比）"""
    cache_key = f"user:{user_id}"

    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # 每次都查数据库（模拟穿透）
    user_num = int(user_id.split(':')[1]) if user_id.split(':')[1].isdigit() else 0
    print(f"[DB Query (穿透!)] user:{user_id}")
    return None

def benchmark():
    """性能对比测试"""
    # 测试 1000 个不存在的 ID
    fake_ids = [f"user:{random.randint(100000, 999999)}" for _ in range(1000)]

    # 不带布隆过滤器
    start = time.time()
    for fid in fake_ids:
        get_user_without_bloom(fid)
    time_without = time.time() - start

    # 带布隆过滤器
    start = time.time()
    for fid in fake_ids:
        get_user_with_bloom(fid)
    time_with = time.time() - start

    print(f"\n--- Benchmark Results ---")
    print(f"Without Bloom Filter: {time_without:.3f}s (1000 DB queries)")
    print(f"With Bloom Filter:    {time_with:.3f}s (0 DB queries)")
    print(f"Speedup: {time_without / time_with:.1f}x")

if __name__ == "__main__":
    setup()
    print("\n--- Test with valid user ---")
    get_user_with_bloom("user:50")

    print("\n--- Test with non-existent user ---")
    get_user_with_bloom("user:999999")

    print("\n--- Benchmark ---")
    benchmark()

    # 清理
    r.flushdb()
```

### 练习 3：数据库故障排查模拟

**目标：** 模拟并排查一个完整的数据库性能故障。

```bash
# 启动测试环境
docker run -d --name mysql-stress -p 3307:3306 \
    -e MYSQL_ROOT_PASSWORD=stress123 -e MYSQL_DATABASE=stressdb \
    mysql:8.0

docker run -d --name redis-stress -p 6380:6379 redis:7-alpine

sleep 15

# 创建测试表
docker exec -i mysql-stress mysql -uroot -pstress123 stressdb << 'SQL'
CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 插入 10 万条测试数据
DELIMITER //
CREATE PROCEDURE insert_orders()
BEGIN
    DECLARE i INT DEFAULT 0;
    WHILE i < 100000 DO
        INSERT INTO orders (user_id, product_id, amount, status)
        VALUES (
            FLOOR(RAND() * 10000),
            FLOOR(RAND() * 1000),
            ROUND(RAND() * 1000, 2),
            ELT(FLOOR(RAND() * 4) + 1, 'pending', 'paid', 'shipped', 'completed')
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;
CALL insert_orders();
SQL
```

```python
# stress_test.py
import pymysql
import redis
import time
import threading
import random

# 模拟故障场景 1: 全表扫描
def scenario_full_table_scan():
    """模拟全表扫描导致的性能问题"""
    conn = pymysql.connect(host='localhost', port=3307, user='root',
                          password='stress123', db='stressdb')
    try:
        with conn.cursor() as cur:
            # 故意不加索引的查询
            start = time.time()
            cur.execute("SELECT * FROM orders WHERE status = 'pending'")
            results = cur.fetchall()
            elapsed = time.time() - start
            print(f"[全表扫描] 查询 {len(results)} 条记录，耗时 {elapsed:.3f}s")

            # 查看执行计划
            cur.execute("EXPLAIN SELECT * FROM orders WHERE status = 'pending'")
            plan = cur.fetchall()
            print(f"[执行计划] type={plan[0][3]}, rows={plan[0][9]}")
    finally:
        conn.close()

# 模拟故障场景 2: 连接泄漏
def scenario_connection_leak():
    """模拟连接泄漏"""
    connections = []
    try:
        for i in range(50):
            conn = pymysql.connect(host='localhost', port=3307, user='root',
                                  password='stress123', db='stressdb')
            connections.append(conn)
            # 不关闭连接，模拟泄漏

        print(f"[连接泄漏] 创建了 {len(connections)} 个连接")

        # 查看 MySQL 连接数
        check_conn = pymysql.connect(host='localhost', port=3307, user='root',
                                    password='stress123', db='stressdb')
        with check_conn.cursor() as cur:
            cur.execute("SHOW STATUS LIKE 'Threads_connected'")
            result = cur.fetchone()
            print(f"[MySQL 状态] Threads_connected: {result[1]}")
        check_conn.close()
    finally:
        # 清理
        for conn in connections:
            try:
                conn.close()
            except:
                pass

# 模拟故障场景 3: 缓存穿透
def scenario_cache_penetration():
    """模拟缓存穿透"""
    r = redis.Redis(host='localhost', port=6380, db=0)
    conn = pymysql.connect(host='localhost', port=3307, user='root',
                          password='stress123', db='stressdb')

    db_query_count = 0

    def query_user(user_id):
        nonlocal db_query_count
        cache_key = f"user:{user_id}"

        # 不处理空值缓存，每次都穿透到 DB
        cached = r.get(cache_key)
        if cached:
            return cached

        # 穿透到数据库
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM orders WHERE user_id = %s LIMIT 1", (user_id,))
            result = cur.fetchone()
        db_query_count += 1

        if result:
            r.setex(cache_key, 300, str(result))
        return result

    # 查询大量不存在的用户
    start = time.time()
    for i in range(1000):
        query_user(random.randint(100000, 999999))
    elapsed = time.time() - start

    print(f"[缓存穿透] 查询 1000 次不存在的用户")
    print(f"  数据库查询次数: {db_query_count}")
    print(f"  总耗时: {elapsed:.3f}s")

    conn.close()
    r.flushdb()

# 运行所有场景
if __name__ == "__main__":
    print("=" * 60)
    print("场景 1: 全表扫描")
    print("=" * 60)
    scenario_full_table_scan()

    print("\n" + "=" * 60)
    print("场景 2: 连接泄漏")
    print("=" * 60)
    scenario_connection_leak()

    print("\n" + "=" * 60)
    print("场景 3: 缓存穿透")
    print("=" * 60)
    scenario_cache_penetration()

    print("\n" + "=" * 60)
    print("修复建议:")
    print("  1. 为 status 字段添加索引: CREATE INDEX idx_status ON orders(status)")
    print("  2. 配置连接池空闲回收: idleTimeout=60s")
    print("  3. 使用布隆过滤器 + 缓存空值防穿透")
    print("=" * 60)
```

```bash
# 运行故障模拟
pip install pymysql redis
python3 stress_test.py

# 手动修复：添加索引
docker exec -i mysql-stress mysql -uroot -pstress123 stressdb << 'SQL'
CREATE INDEX idx_orders_status ON orders(status);
EXPLAIN SELECT * FROM orders WHERE status = 'pending';
SQL
# 应该看到 type 从 ALL 变为 ref

# 清理
docker stop mysql-stress redis-stress
docker rm mysql-stress redis-stress
```

---

## 🎯 面试题精选

### 1. MySQL 和 Redis 如何保证数据一致性？

**参考答案：**
最常用的是 Cache Aside Pattern：读时先查缓存，未命中查数据库并写缓存；写时先更新数据库，再删除缓存。删除而非更新缓存可以避免并发写导致的脏数据。对于一致性要求更高的场景，可以使用延迟双删（先删缓存、更新 DB、延迟再删一次）或基于 Binlog 的异步更新（Canal + MQ）。最终方案都是接受最终一致性，配合合理 TTL 兜底。

### 2. 什么是缓存穿透、击穿、雪崩？分别怎么解决？

**参考答案：**
- **穿透：** 查询不存在的数据，缓存未命中直接打到数据库。解决：布隆过滤器 + 缓存空值
- **击穿：** 热点 Key 过期瞬间大量并发请求打到数据库。解决：互斥锁（只允许一个请求查 DB）+ 逻辑过期（不设物理 TTL）
- **雪崩：** 大量 Key 同时过期或 Redis 宕机。解决：随机 TTL + 多级缓存 + 熔断降级 + Redis 高可用

### 3. Redis 的持久化策略如何选择？

**参考答案：**
- 纯缓存场景：仅 RDB 即可，数据丢失可从数据库重建
- 数据安全要求高：AOF (everysec) + RDB
- 通用生产推荐：混合持久化（aof-use-rdb-preamble yes），兼具 RDB 的恢复速度和 AOF 的数据安全性
- 关键原则：永远设置 maxmemory，持久化只是兜底，高可用（主从 + Sentinel/Cluster）更重要

### 4. 如何设计一个高并发的商品详情页？

**参考答案：**
多级缓存架构：
1. **CDN：** 静态资源（图片、CSS、JS）
2. **Nginx 缓存：** 页面 HTML（5-10 秒 TTL）
3. **本地缓存（Caffeine）：** 热点商品数据（5 秒 TTL，容量有限）
4. **Redis 缓存：** 商品详情（5 分钟 TTL）
5. **MySQL：** 数据源

读路径：CDN → Nginx → 本地缓存 → Redis → MySQL
写路径：更新 MySQL → 删除 Redis → 通过 MQ 通知清除各级缓存

热点防护：本地缓存兜底 + 互斥锁防击穿 + 布隆过滤器防穿透

### 5. Redis Cluster 和 MySQL 分库分表有什么区别？

**参考答案：**
- **Redis Cluster：** 16384 个 hash slot 自动分片，客户端路由，运维相对简单，适合 Key-Value 场景
- **MySQL 分库分表：** 需要中间件（ShardingSphere、Vitess），分片键选择影响查询效率，跨分片查询复杂，支持复杂 SQL

选择标准：
- 数据模型简单、查询模式单一 → Redis Cluster
- 需要复杂查询、事务、JOIN → MySQL 分库分表
- 混合场景：Redis 做缓存 + MySQL 做持久存储

### 6. 如何排查 Redis 内存持续增长的问题？

**参考答案：**
排查步骤：
1. `INFO memory` 查看内存使用趋势
2. `redis-cli --bigkeys` 扫描大 Key
3. `redis-cli --memkeys` 按内存排序
4. `SCAN` 遍历检查 Key 的 TTL 设置
5. 检查是否有 Key 未设置过期时间
6. 检查 mem_fragmentation_ratio 是否过高

常见原因：
- 代码 bug 忘记设置 TTL
- 大 Key 不断增长（如 List 只 push 不 pop）
- 内存碎片率过高

### 7. 什么是热 Key 问题？如何解决？

**参考答案：**
热 Key 是指被频繁访问的 Key，会导致单个 Redis 节点或分片成为瓶颈。解决方案：
1. **本地缓存：** 在应用层缓存热 Key，减少 Redis 压力
2. **读写分离：** 热 Key 读取走从节点
3. **Key 分散：** 将热 Key 复制多份（product:1, product:2, ...），读取时随机选择
4. **监控告警：** 使用 `redis-cli --hotkeys` 发现热 Key

### 8. 如何保证分布式锁的可靠性？

**参考答案：**
Redis 分布式锁的关键要素：
1. **互斥性：** SET key value NX PX timeout（原子操作）
2. **唯一标识：** 使用 UUID 作为 value，防止误删别人的锁
3. **安全释放：** Lua 脚本保证「判断 + 删除」原子性
4. **超时自动释放：** 设置 PX 过期时间，防止死锁
5. **可重入性：** 使用 Hash 存储锁信息（field=线程ID, value=重入次数）
6. **续期机制：** 后台线程定期检查并延长锁的过期时间（看门狗机制）

对于更高可靠性要求，考虑 Redlock 算法（多节点锁）或 ZooKeeper 分布式锁。

### 9. MySQL 慢查询如何优化？

**参考答案：**
优化步骤：
1. **开启慢查询日志：** `slow_query_log=ON`, `long_query_time=1`
2. **分析慢查询：** `EXPLAIN` 查看执行计划
3. **常见优化：**
   - 添加合适的索引（覆盖索引、联合索引）
   - 避免 SELECT *，只查需要的列
   - 分页优化：用 `WHERE id > offset` 替代 `LIMIT offset`
   - 大查询拆分为小查询
   - 避免在 WHERE 中对索引列使用函数
4. **架构优化：** 读写分离、分库分表、缓存热点数据

### 10. 如何设计一个数据库监控告警体系？

**参考答案：**
监控层次：
1. **基础设施层：** CPU、内存、磁盘 I/O、网络（Node Exporter）
2. **数据库层：**
   - MySQL：QPS、TPS、慢查询数、连接数、缓冲池命中率、复制延迟（mysqld_exporter）
   - Redis：内存使用率、QPS、命中率、淘汰数、主从延迟（redis_exporter）
3. **应用层：** 接口延迟、错误率、QPS
4. **业务层：** 下单成功率、支付成功率

告警分级：
- P0（Critical）：服务不可用，立即响应
- P1（High）：性能严重下降，15 分钟内响应
- P2（Warning）：性能轻微下降，1 小时内响应
- P3（Info）：预警信息，工作时间处理

工具栈：Prometheus + Grafana + AlertManager

---

## 📚 深入阅读

### 官方文档
- [MySQL 8.0 Reference Manual](https://dev.mysql.com/doc/refman/8.0/en/) — MySQL 官方文档
- [Redis Documentation](https://redis.io/docs/) — Redis 官方文档
- [Redis Best Practices](https://redis.io/docs/operate/oss_and_stack/management/optimization/) — Redis 优化指南

### 推荐书籍
- 《高性能 MySQL》— Baron Schwartz 等，MySQL 优化圣经
- 《Redis 设计与实现》— 黄健宏，Redis 内部实现详解
- 《数据密集型应用系统设计》— Martin Kleppmann，分布式系统设计
- 《SRE: Google 运维解密》— Google SRE 团队，运维方法论

### 技术博客
- [MySQL Performance Blog](https://www.percona.com/blog/) — Percona 博客
- [Redis Blog](https://redis.io/blog/) — Redis 官方博客
- [美团技术团队](https://tech.meituan.com/) — 大量数据库实战文章
- [阿里云数据库内核月报](http://mysql.taobao.org/monthly/) — MySQL 内核分析

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 Cache Aside Pattern 的读写流程
- [ ] 能对比四种缓存一致性策略的优缺点
- [ ] 能说清缓存穿透、击穿、雪崩的区别和解决方案
- [ ] 能解释布隆过滤器的原理和适用场景
- [ ] 能设计 MySQL + Redis 联合架构
- [ ] 能制定数据库容量规划方案

### 实操检查点
- [ ] 能实现 Cache Aside Pattern 代码
- [ ] 能使用布隆过滤器防护缓存穿透
- [ ] 能通过 EXPLAIN 分析和优化慢查询
- [ ] 能使用 redis-cli --bigkeys 发现大 Key
- [ ] 能配置 Prometheus + Grafana 监控 MySQL 和 Redis

### 能力验证标准
- [ ] 能独立设计一个电商系统的数据库架构
- [ ] 能在 30 分钟内排查一个数据库性能故障
- [ ] 能根据业务场景选择合适的缓存策略
- [ ] 能制定完整的数据库监控告警方案
