# Day 70: MySQL 基础与架构

> 📅 日期：2026-05-03
> 📖 学习主题：MySQL 架构体系、存储引擎、事务与锁机制、索引原理、日志系统
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 49（数据库交互）, Day 43-56（Python SRE 工具开发）

## 🎯 学习目标

完成 Day 70 的学习后，你应该能够：
1. 画出 MySQL 逻辑架构图，解释连接层、SQL 层、存储引擎层的职责与协作关系
2. 对比 InnoDB 与 MyISAM 的核心差异，说明为什么生产环境必须使用 InnoDB
3. 深入解释事务 ACID 特性的实现原理（undo log、redo log、锁、MVCC）
4. 手绘 B+ Tree 索引结构，解释聚簇索引与二级索引的区别和回表查询
5. 理解 binlog、redo log、undo log 三种日志的作用、写入时机和协作关系
6. 能够针对 SRE 场景进行基础的 SQL 优化和索引设计

---

## 📖 核心知识点

### 1. MySQL 逻辑架构

#### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        客户端连接层                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │  JDBC    │ │ pymysql  │ │ mysql CLI│ │  Go      │  ...         │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘              │
│       └────────────┼────────────┼────────────┘                     │
│                    ▼                                                │
│            ┌──────────────┐                                        │
│            │   连接管理器   │  管理客户端连接、线程分配、认证       │
│            │ (Connection   │                                        │
│            │  Pool)        │                                        │
│            └──────┬───────┘                                        │
├───────────────────┼────────────────────────────────────────────────┤
│                   ▼           SQL 层                                │
│  ┌────────────────────────────────────────────┐                    │
│  │              SQL 接口 (SQL Interface)        │                    │
│  │  接收 SQL 语句，返回结果集                   │                    │
│  └────────────────────┬───────────────────────┘                    │
│                       ▼                                             │
│  ┌────────────────────────────────────────────┐                    │
│  │            解析器 (Parser)                   │                    │
│  │  词法分析 → 语法分析 → 语法树               │                    │
│  └────────────────────┬───────────────────────┘                    │
│                       ▼                                             │
│  ┌────────────────────────────────────────────┐                    │
│  │          预处理器 (Preprocessor)             │                    │
│  │  检查表/列是否存在，权限验证，展开 *         │                    │
│  └────────────────────┬───────────────────────┘                    │
│                       ▼                                             │
│  ┌────────────────────────────────────────────┐                    │
│  │         优化器 (Optimizer)                   │                    │
│  │  选择最优执行计划：索引选择、JOIN 顺序、     │                    │
│  │  子查询转换、成本估算                        │                    │
│  └────────────────────┬───────────────────────┘                    │
│                       ▼                                             │
│  ┌────────────────────────────────────────────┐                    │
│  │         执行器 (Executor)                    │                    │
│  │  调用存储引擎接口，获取数据，返回结果       │                    │
│  └────────────────────┬───────────────────────┘                    │
├──────────────────────┼─────────────────────────────────────────────┤
│                      ▼          存储引擎层                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ InnoDB  │  │ MyISAM   │  │ Memory   │  │ NDB      │  ...      │
│  │(默认)   │  │          │  │          │  │ Cluster  │           │
│  └─────────┘  └──────────┘  └──────────┘  └──────────┘           │
│       │                                                            │
│       ▼                                                            │
│  ┌────────────────────────────────────────────┐                    │
│  │          文件系统 (磁盘/SSD)                 │                    │
│  │  .frm (表结构) .ibd (InnoDB 数据) .MYD/.MYI│                    │
│  └────────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 各层职责详解

| 层次 | 组件 | 职责 | SRE 关注点 |
|------|------|------|-----------|
| 连接层 | 连接管理器 | TCP 连接管理、身份认证、线程复用 | `max_connections`、连接泄漏排查 |
| SQL 层 | SQL 接口 | 接收并解析客户端 SQL 请求 | 慢查询日志 |
| SQL 层 | 解析器 | 词法/语法分析，生成解析树 | SQL 语法错误排查 |
| SQL 层 | 优化器 | 基于成本的执行计划选择 | `EXPLAIN` 分析、索引优化 |
| SQL 层 | 执行器 | 执行计划、调用引擎接口 | 锁等待、全表扫描 |
| 引擎层 | InnoDB | 事务、行锁、外键、MVCC | 核心引擎，重点掌握 |
| 引擎层 | MyISAM | 全文索引、表锁 | 仅用于只读/分析场景 |

#### 1.3 一条 SQL 的完整执行流程

```sql
SELECT * FROM users WHERE id = 100;
```

```
1. 客户端发送 SQL 到 MySQL Server
2. 连接器：验证用户名密码，检查权限
3. 查询缓存（MySQL 8.0 已移除）：检查是否有缓存结果
4. 解析器：词法分析（识别 SELECT、*、FROM、users、WHERE、id、=、100）
          语法分析（检查 SQL 是否合法，生成解析树）
5. 预处理器：检查 users 表是否存在，id 列是否存在，权限是否足够
6. 优化器：决定使用主键索引（PRIMARY），选择执行计划
7. 执行器：调用 InnoDB 引擎的读接口
8. 存储引擎：通过 B+ Tree 在聚簇索引中定位 id=100 的记录
9. 返回结果集给客户端
```

---

### 2. 存储引擎：InnoDB vs MyISAM

#### 2.1 核心对比

```
┌─────────────────────────────────────────────────────────────────┐
│                    InnoDB vs MyISAM 对比                         │
├─────────────────┬─────────────────────┬─────────────────────────┤
│ 特性            │ InnoDB              │ MyISAM                  │
├─────────────────┼─────────────────────┼─────────────────────────┤
│ 事务支持        │ ✅ 支持 ACID        │ ❌ 不支持               │
│ 行级锁          │ ✅ 支持             │ ❌ 仅表锁               │
│ 外键            │ ✅ 支持             │ ❌ 不支持               │
│ MVCC            │ ✅ 支持             │ ❌ 不支持               │
│ 崩溃恢复        │ ✅ redo log 保证    │ ❌ 无崩溃恢复能力       │
│ 全文索引        │ ✅ (5.6+)           │ ✅ 支持                 │
│ 聚簇索引        │ ✅ 数据按主键存储   │ ❌ 非聚簇               │
│ 存储文件        │ .frm + .ibd         │ .frm + .MYD + .MYI     │
│ 适用场景        │ OLTP，读写混合      │ 只读/分析，全文搜索     │
│ 计数查询        │ 需遍历 (COUNT=慢)   │ 存储行数 (COUNT=快)    │
└─────────────────┴─────────────────────┴─────────────────────────┘
```

#### 2.2 InnoDB 架构详解

```
┌─────────────────────────────────────────────────────────────┐
│                      InnoDB 内存结构                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Buffer Pool (缓冲池)                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │   │
│  │  │ 数据页   │ │ 索引页   │ │ 自适应   │            │   │
│  │  │ (Data    │ │ (Index   │ │ 哈希索引 │            │   │
│  │  │  Page)   │ │  Page)   │ │ (AHI)    │            │   │
│  │  └──────────┘ └──────────┘ └──────────┘            │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐            │   │
│  │  │ Change   │ │ 锁信息   │ │ 数据字典 │            │   │
│  │  │ Buffer   │ │          │ │ 缓存     │            │   │
│  │  └──────────┘ └──────────┘ └──────────┘            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Redo Log     │  │ Undo Log     │  │ 额外内存     │     │
│  │ Buffer       │  │ Buffer       │  │ Pool         │     │
│  │ (重做日志    │  │ (回滚日志    │  │              │     │
│  │  缓冲区)     │  │  缓冲区)     │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────────────────────────┤
│                      InnoDB 磁盘结构                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           System Tablespace (ibdata1)                │   │
│  │  数据字典、Change Buffer、Undo Log（MySQL 8.0 前）   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ File-Per-    │  │ Redo Log     │  │ Undo         │     │
│  │ Table Space  │  │ (ib_logfile  │  │ Tablespace   │     │
│  │ (.ibd 文件)  │  │  0/1)        │  │ (undo_001)   │     │
│  │ 数据+索引    │  │ WAL 机制     │  │ 事务回滚     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │ Doublewrite  │  │ Temporary    │                       │
│  │ Buffer       │  │ Tablespace   │                       │
│  │ (防页断裂)   │  │ (临时表)     │                       │
│  └──────────────┘  └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

**Buffer Pool 工作原理：**

```
读取数据时：
  1. 先在 Buffer Pool 中查找（Page Cache）
  2. 命中 → 直接从内存返回（逻辑读）
  3. 未命中 → 从磁盘读取到 Buffer Pool（物理读），再返回

修改数据时：
  1. 先修改 Buffer Pool 中的页（脏页，Dirty Page）
  2. 记录 redo log（WAL 机制）
  3. 脏页由后台线程异步刷盘（Checkpoint）

关键参数：
  innodb_buffer_pool_size    # Buffer Pool 大小，建议物理内存的 60-80%
  innodb_buffer_pool_instances  # 多实例减少锁竞争（>=1GB 时建议 8-16）
```

#### 2.3 查看和切换存储引擎

```sql
-- 查看支持的存储引擎
SHOW ENGINES;

-- 查看默认存储引擎
SELECT @@default_storage_engine;

-- 查看某张表的存储引擎
SHOW TABLE STATUS LIKE 'users'\G

-- 创建表时指定引擎
CREATE TABLE orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    amount DECIMAL(10,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 修改已有表的引擎（会锁表，生产慎用）
ALTER TABLE orders ENGINE=InnoDB;
```

---

### 3. 事务 ACID 特性与实现原理

#### 3.1 ACID 四大特性

```
┌─────────────────────────────────────────────────────────────┐
│                    事务 ACID 特性                            │
├───────────┬─────────────────────────────┬───────────────────┤
│ 特性      │ 含义                        │ 实现机制          │
├───────────┼─────────────────────────────┼───────────────────┤
│ A         │ Atomicity 原子性            │ undo log          │
│ (原子性)  │ 事务要么全部成功，要么全部  │ 回滚到事务开始前  │
│           │ 回滚                        │ 的状态            │
├───────────┼─────────────────────────────┼───────────────────┤
│ C         │ Consistency 一致性          │ 由 AID 共同保证   │
│ (一致性)  │ 事务前后数据满足完整性约束  │ 应用层+数据库约束 │
├───────────┼─────────────────────────────┼───────────────────┤
│ I         │ Isolation 隔离性            │ MVCC + 锁         │
│ (隔离性)  │ 并发事务互不干扰            │ Read View         │
├───────────┼─────────────────────────────┼───────────────────┤
│ D         │ Durability 持久性           │ redo log          │
│ (持久性)  │ 提交后的数据永久保存        │ WAL + Doublewrite │
└───────────┴─────────────────────────────┴───────────────────┘
```

#### 3.2 事务隔离级别

```sql
-- 查看当前隔离级别
SELECT @@transaction_isolation;

-- 设置隔离级别
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;
```

```
┌────────────────────┬───────────────┬───────────────┬───────────────┐
│ 隔离级别           │ 脏读          │ 不可重复读    │ 幻读          │
├────────────────────┼───────────────┼───────────────┼───────────────┤
│ READ UNCOMMITTED   │ 可能          │ 可能          │ 可能          │
│ (读未提交)         │               │               │               │
├────────────────────┼───────────────┼───────────────┼───────────────┤
│ READ COMMITTED     │ 不会          │ 可能          │ 可能          │
│ (读已提交) - Oracle│               │               │               │
├────────────────────┼───────────────┼───────────────┼───────────────┤
│ REPEATABLE READ    │ 不会          │ 不会          │ InnoDB 通过   │
│ (可重复读) - 默认  │               │               │ Gap Lock 解决 │
├────────────────────┼───────────────┼───────────────┼───────────────┤
│ SERIALIZABLE       │ 不会          │ 不会          │ 不会          │
│ (串行化)           │               │               │               │
└────────────────────┴───────────────┴───────────────┴───────────────┘
```

#### 3.3 MVCC 多版本并发控制

MVCC 是 InnoDB 实现高并发的核心机制，通过保存数据的多个版本来实现非锁定读。

```
每行数据隐含两个字段：
  trx_id     : 最后修改该行的事务 ID
  roll_pointer: 指向 undo log 中该行的上一个版本

Read View（读视图）结构：
  m_ids        : 创建 Read View 时活跃的事务 ID 列表
  min_trx_id   : m_ids 中的最小值
  max_trx_id   : 系统下一个要分配的事务 ID
  creator_trx_id: 创建该 Read View 的事务 ID

可见性判断规则：
  1. trx_id == creator_trx_id → 自己修改的，可见
  2. trx_id < min_trx_id     → 事务已提交，可见
  3. trx_id >= max_trx_id    → 事务在 Read View 之后开始，不可见
  4. trx_id in m_ids         → 事务还未提交，不可见
  5. trx_id not in m_ids     → 事务已提交，可见

  不可见时 → 沿 roll_pointer 找到上一个版本，重复判断
```

```
示例：两个并发事务
  事务 A (id=100)  事务 B (id=101)

  时间线：
  T1: 事务 A 开始，创建 Read View
  T2: 事务 B 修改 id=1 的 name 为 'B'
  T3: 事务 A 查询 id=1

  事务 A 的 Read View:
    m_ids = [100, 101]     -- A 和 B 都是活跃事务
    min_trx_id = 100
    max_trx_id = 102
    creator_trx_id = 100

  行数据 trx_id = 101
    判断: 101 in m_ids → 不可见
    沿 roll_pointer 找到上一个版本 (trx_id=90, 假设已提交)
    判断: 90 < min_trx_id(100) → 可见
    结果: 事务 A 看到的是事务 B 修改前的数据
```

---

### 4. 锁机制

#### 4.1 锁分类

```
按粒度分：
  ┌──────────────────────────────────────────────────────┐
  │ 表锁 (Table Lock)                                    │
  │  -  LOCK TABLES t READ/WRITE                        │
  │  -  开销小，加锁快，粒度大，并发低                    │
  │  -  MyISAM 只支持表锁                                │
  │  -  InnoDB 的意向锁也是表级锁                        │
  ├──────────────────────────────────────────────────────┤
  │ 行锁 (Row Lock) - InnoDB 独有                       │
  │  -  开销大，加锁慢，粒度小，并发高                    │
  │  -  基于索引实现，无索引则退化为表锁                  │
  ├──────────────────────────────────────────────────────┤
  │ 页锁 (Page Lock) - BDB 引擎（已废弃）               │
  └──────────────────────────────────────────────────────┘

按类型分：
  ┌──────────────────────────────────────────────────────┐
  │ 共享锁 (S Lock, Shared Lock)                         │
  │  -  SELECT ... LOCK IN SHARE MODE                   │
  │  -  多个事务可同时持有                               │
  │  -  读读不互斥                                       │
  ├──────────────────────────────────────────────────────┤
  │ 排他锁 (X Lock, Exclusive Lock)                      │
  │  -  SELECT ... FOR UPDATE                           │
  │  -  INSERT / UPDATE / DELETE 自动加 X 锁            │
  │  -  与任何锁互斥                                     │
  ├──────────────────────────────────────────────────────┤
  │ 意向锁 (Intention Lock) - InnoDB 表级锁             │
  │  -  IS (Intention Shared): 事务打算给行加 S 锁      │
  │  -  IX (Intention Exclusive): 事务打算给行加 X 锁   │
  │  -  用于快速判断表中是否有行锁                       │
  └──────────────────────────────────────────────────────┘
```

#### 4.2 InnoDB 行锁算法

```
┌──────────────────────────────────────────────────────────────────┐
│                  InnoDB 行锁三种算法                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Record Lock (记录锁)                                           │
│  -  锁定索引记录本身                                             │
│  -  SELECT * FROM t WHERE id=1 FOR UPDATE                      │
│  -  锁住 id=1 这一条记录                                        │
│                                                                  │
│  Gap Lock (间隙锁)                                               │
│  -  锁定索引记录之间的间隙，不包含记录本身                       │
│  -  防止其他事务在间隙中插入新记录（防止幻读）                   │
│  -  只在 REPEATABLE READ 及以上隔离级别生效                      │
│                                                                  │
│  Next-Key Lock (临键锁) = Record Lock + Gap Lock                │
│  -  InnoDB 默认行锁算法                                          │
│  -  锁定记录本身 + 记录前面的间隙                                │
│  -  左开右闭区间：(gap, record]                                 │
│                                                                  │
│  示例：索引值为 10, 20, 30                                       │
│  Next-Key Lock 可能的锁定范围：                                  │
│    (-∞, 10], (10, 20], (20, 30], (30, +∞)                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.3 死锁排查与处理

```sql
-- 查看当前锁等待
SELECT * FROM information_schema.INNODB_LOCK_WAITS;

-- MySQL 8.0 查看锁信息
SELECT * FROM performance_schema.data_locks;
SELECT * FROM performance_schema.data_lock_waits;

-- 查看最近一次死锁信息
SHOW ENGINE INNODB STATUS\G
-- 找到 LATEST DETECTED DEADLOCK 部分

-- 设置锁等待超时（默认 50 秒）
SET SESSION innodb_lock_wait_timeout = 10;

-- 查看当前运行的事务
SELECT * FROM information_schema.INNODB_TRX;

-- 杀掉阻塞事务
KILL <thread_id>;
```

**死锁示例与分析：**

```sql
-- 会话 A
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;  -- 锁住 id=1
-- 等待...
UPDATE accounts SET balance = balance + 100 WHERE id = 2;  -- 等待 id=2 的锁

-- 会话 B
BEGIN;
UPDATE accounts SET balance = balance - 50 WHERE id = 2;   -- 锁住 id=2
UPDATE accounts SET balance = balance + 50 WHERE id = 1;   -- 等待 id=1 的锁 → 死锁！

-- InnoDB 自动检测死锁，回滚持有 undo log 最少的事务
-- 应用收到错误：ERROR 1213 (40001): Deadlock found when trying to get lock
```

**SRE 预防死锁的最佳实践：**
1. 以固定顺序访问表和行（如按 id 升序）
2. 事务尽量短小，减少锁持有时间
3. 使用合适的索引，避免锁升级为表锁
4. 设置合理的 `innodb_lock_wait_timeout`
5. 监控死锁指标，配置告警

---

### 5. 索引原理：B+ Tree

#### 5.1 B+ Tree 结构

```
InnoDB 使用 B+ Tree 作为索引数据结构。

B+ Tree 的特点：
  1. 所有数据都存储在叶子节点（非叶子节点只存储索引键）
  2. 叶子节点通过双向链表连接（支持范围查询）
  3. 每个节点包含多个键值对（高扇出，低树高）
  4. 树高通常为 3-4 层，可存储数亿条数据

┌──────────────────────────────────────────────────────────────────┐
│                        B+ Tree 索引结构                           │
│                                                                  │
│  Level 2 (根节点):         [       50 | 100        ]            │
│                            /          |           \              │
│  Level 1 (非叶子节点):  [20|35]    [65|80]    [120|150]         │
│                        /  |  \    /  |  \     /  |  \           │
│  Level 0 (叶子节点): [10|15] [20|30] [35|45] [50|60] [65|75]   │
│    ←→ 双向链表 ←→    [80|90] [100|110] [120|135] [150|200]     │
│                      ←→ 叶子节点通过双向链表连接 ←→              │
│                                                                  │
│  查找 id=65 的路径：                                             │
│    根节点: 65 > 50 且 65 < 100 → 走中间指针                     │
│    非叶子: 65 >= 65 且 65 < 80 → 走左边指针                     │
│    叶子节点: 找到 id=65 的完整行数据                             │
│    总共 3 次磁盘 I/O（如果根节点常驻内存则 2 次）               │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.2 聚簇索引 vs 二级索引

```
聚簇索引 (Clustered Index):
  -  数据行本身存储在 B+ Tree 的叶子节点中
  -  每张表只能有一个聚簇索引
  -  InnoDB 选择主键作为聚簇索引
  -  如果没有主键，选择第一个 UNIQUE NOT NULL 索引
  -  如果都没有，InnoDB 自动生成隐藏的 ROW_ID

二级索引 (Secondary Index):
  -  叶子节点存储的是主键值（不是数据行的物理地址）
  -  通过二级索引查找数据需要"回表"
  -  先在二级索引中找到主键值
  -  再通过主键值在聚簇索引中找到完整行数据

┌──────────────────────────────────────────────────────────────┐
│  聚簇索引 (PRIMARY KEY on id)                                │
│  叶子节点: [id=1, name=Alice, age=25, email=alice@... ]      │
│           [id=2, name=Bob,   age=30, email=bob@...   ]      │
│           [id=3, name=Carol, age=28, email=carol@... ]      │
├──────────────────────────────────────────────────────────────┤
│  二级索引 (INDEX on name)                                    │
│  叶子节点: [name=Alice → id=1]                               │
│           [name=Bob   → id=2]                               │
│           [name=Carol → id=3]                               │
└──────────────────────────────────────────────────────────────┘

回表查询过程：
  SELECT * FROM users WHERE name = 'Bob';

  1. 在二级索引 (name) 中找到 name='Bob'，得到 id=2
  2. 用 id=2 去聚簇索引中查找完整行数据
  3. 返回完整数据行

覆盖索引 (Covering Index):
  SELECT id, name FROM users WHERE name = 'Bob';

  -  二级索引叶子节点已经包含 id 和 name
  -  无需回表，直接返回（Using index）
```

#### 5.3 索引设计原则

```sql
-- 1. 最左前缀原则
-- 联合索引 (a, b, c) 可以匹配以下查询：
SELECT * FROM t WHERE a = 1;                    -- ✅ 使用索引
SELECT * FROM t WHERE a = 1 AND b = 2;         -- ✅ 使用索引
SELECT * FROM t WHERE a = 1 AND b = 2 AND c=3; -- ✅ 使用索引
SELECT * FROM t WHERE b = 2;                    -- ❌ 不使用索引
SELECT * FROM t WHERE b = 2 AND c = 3;         -- ❌ 不使用索引
SELECT * FROM t WHERE a = 1 AND c = 3;         -- ⚠️ 只用到 a

-- 2. 范围查询右边的列不走索引
SELECT * FROM t WHERE a = 1 AND b > 10 AND c = 3;  -- 只用 (a, b)

-- 3. 索引列不参与函数运算
SELECT * FROM t WHERE YEAR(create_time) = 2026;     -- ❌ 不走索引
SELECT * FROM t WHERE create_time >= '2026-01-01'
  AND create_time < '2027-01-01';                    -- ✅ 走索引

-- 4. 类型转换导致索引失效
-- phone 是 varchar 类型
SELECT * FROM users WHERE phone = 13800138000;       -- ❌ 隐式转换
SELECT * FROM users WHERE phone = '13800138000';     -- ✅

-- 5. 覆盖索引减少回表
-- 推荐：SELECT id, name FROM users WHERE name = 'Bob';
-- 联合索引 (name, id) 可以覆盖查询
```

---

### 6. 日志系统：binlog / redo log / undo log

#### 6.1 三种日志对比

```
┌──────────────┬────────────────────┬────────────────────┬────────────────────┐
│ 特性         │ redo log           │ undo log           │ binlog             │
├──────────────┼────────────────────┼────────────────────┼────────────────────┤
│ 所属层       │ InnoDB 引擎层      │ InnoDB 引擎层      │ MySQL Server 层    │
│ 记录内容     │ 物理日志           │ 逻辑日志           │ 逻辑日志           │
│              │ "某页偏移量写入    │ "执行 INSERT 前    │ "执行了 INSERT     │
│              │  了什么数据"       │  记录为空，DELETE   │  语句" 或行变更    │
│              │                    │  前记录为..."      │                    │
│ 写入方式     │ 循环写             │ 追加写             │ 追加写             │
│              │ ib_logfile0/1      │ undo tablespace    │ binlog.000001      │
│ 用途         │ 崩溃恢复 (CR)      │ 事务回滚           │ 主从复制           │
│              │ 保证持久性 (D)     │ MVCC 多版本读      │ 数据恢复 (PITR)   │
│ 生命周期     │ Checkpoint 后可    │ 事务提交且无       │ 保留策略内         │
│              │ 被覆盖             │ MVCC 引用后清理    │ (expire_logs_days) │
└──────────────┴────────────────────┴────────────────────┴────────────────────┘
```

#### 6.2 Redo Log 与 WAL 机制

```
WAL (Write-Ahead Logging): 先写日志，再写磁盘

为什么需要 redo log？
  -  修改数据时，先修改 Buffer Pool 中的内存页（脏页）
  -  脏页不会立即刷盘（随机 I/O 太慢）
  -  如果此时 MySQL 崩溃，内存中的修改会丢失
  -  redo log 记录了"做了什么修改"
  -  重启后，通过 redo log 恢复未刷盘的脏页数据

redo log 写入流程：
  1. 事务执行 UPDATE 语句
  2. InnoDB 将修改写入 redo log buffer（内存）
  3. 事务提交时，将 redo log buffer 刷入磁盘（fsync）
  4. 后台线程择机将脏页刷入磁盘（Checkpoint）

  redo log 文件：ib_logfile0, ib_logfile1（循环写入）

  ┌─────────┐     ┌─────────┐
  │logfile0 │ ──→ │logfile1 │ ──→ 回到 logfile0
  └─────────┘     └─────────┘
  write pos: 当前写入位置
  checkpoint: 已经刷盘的位置
  中间的空间: 可以写入新日志

  如果 write pos 追上 checkpoint，必须停下来做 Checkpoint
```

```sql
-- 查看 redo log 配置
SHOW VARIABLES LIKE 'innodb_log%';

-- redo log 大小（默认 48MB * 2 = 96MB）
-- 生产建议：根据写入量设置为 1-4GB
-- innodb_log_file_size = 1G
-- innodb_log_files_in_group = 2

-- 查看 redo log 写入状态
SHOW GLOBAL STATUS LIKE 'Innodb_os_log%';
```

#### 6.3 Binlog 详解

```sql
-- 查看 binlog 配置
SHOW VARIABLES LIKE 'log_bin%';
SHOW VARIABLES LIKE 'binlog_format%';

-- 三种格式
-- STATEMENT: 记录 SQL 语句本身（主从可能不一致）
-- ROW: 记录行变更前后的数据（推荐，数据一致性好）
-- MIXED: 自动选择 STATEMENT 或 ROW

-- 推荐配置
SET GLOBAL binlog_format = 'ROW';
SET GLOBAL binlog_row_image = 'FULL';

-- 查看 binlog 文件列表
SHOW BINARY LOGS;

-- 查看 binlog 事件
SHOW BINLOG EVENTS IN 'binlog.000001' LIMIT 10;

-- 使用 mysqlbinlog 工具解析
-- mysqlbinlog --base64-output=DECODE-ROWS -v binlog.000001
```

#### 6.4 两阶段提交 (2PC)

```
为了保证 redo log 和 binlog 的一致性，InnoDB 使用两阶段提交：

写入过程：
  1. InnoDB 写入 redo log（prepare 状态）
  2. MySQL Server 写入 binlog
  3. InnoDB 将 redo log 标记为 commit 状态

崩溃恢复时的判断：
  -  redo log 有 prepare，binlog 有对应记录 → 提交事务
  -  redo log 有 prepare，binlog 无对应记录 → 回滚事务
  -  redo log 有 commit → 事务已完成，无需处理

时间线：
  ┌──────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ 写入  │ →  │ redo log │ →  │ 写入     │ →  │ redo log │
  │ 数据  │    │ prepare  │    │ binlog   │    │ commit   │
  └──────┘    └──────────┘    └──────────┘    └──────────┘
                  ↑ 阶段 1 ↑      ↑ 阶段 2 ↑
```

---

### 7. SRE 实战案例

#### 7.1 案例：生产环境 InnoDB Buffer Pool 不足导致性能下降

**现象：**
- 某电商数据库（16GB 内存）响应时间从 5ms 飙升到 500ms
- CPU 使用率不高（30%），但 I/O await 很高
- 业务侧反馈：订单查询超时，用户投诉增多

**诊断过程：**

```sql
-- Step 1: 检查 Buffer Pool 命中率
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read%';
-- Innodb_buffer_pool_read_requests = 10000000 (逻辑读)
-- Innodb_buffer_pool_reads = 500000 (物理读)
-- 命中率 = 1 - (500000/10000000) = 95%  ← 低于 99%，需要关注

-- Step 2: 查看 Buffer Pool 使用情况
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
-- innodb_buffer_pool_size = 1G  ← 只分配了 1GB！

-- Step 3: 查看数据库大小
SELECT
    table_schema AS db,
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
FROM information_schema.tables
GROUP BY table_schema
ORDER BY size_mb DESC;
-- 业务库: 12GB  ← 数据库比 Buffer Pool 大 12 倍！

-- Step 4: 检查脏页刷盘情况
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_pages_dirty%';
-- 脏页比例较高，刷盘压力大
```

**根因：** Buffer Pool 只分配了 1GB，而数据库大小 12GB，导致大量物理读和频繁的脏页刷盘。

**修复：**

```sql
-- 在线调整 Buffer Pool 大小（MySQL 5.7+ 支持在线调整）
SET GLOBAL innodb_buffer_pool_size = 10 * 1024 * 1024 * 1024;  -- 10GB

-- 验证调整
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';

-- 永久配置（写入 my.cnf）
-- [mysqld]
-- innodb_buffer_pool_size = 10G
-- innodb_buffer_pool_instances = 8
```

**预防措施：**
1. 新实例部署时，Buffer Pool 设为物理内存的 60-80%
2. 监控 `Innodb_buffer_pool_read_requests` 和 `Innodb_buffer_pool_reads`，计算命中率
3. 命中率低于 99% 时告警
4. 定期检查数据库增长趋势，提前扩容

#### 7.2 案例：索引缺失导致全表扫描

**现象：**
- 某订单查询接口 P99 延迟从 20ms 升到 2s
- 慢查询日志中出现大量全表扫描

**诊断过程：**

```sql
-- Step 1: 开启慢查询日志
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;
SET GLOBAL log_queries_not_using_indexes = ON;

-- Step 2: 查看慢查询
-- 分析慢查询日志
-- mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

-- Step 3: EXPLAIN 分析
EXPLAIN SELECT * FROM orders
WHERE user_id = 12345 AND status = 'paid'
ORDER BY create_time DESC LIMIT 20;

-- 结果显示 type=ALL, rows=5000000 → 全表扫描！
-- key=NULL → 没有使用任何索引

-- Step 4: 检查现有索引
SHOW INDEX FROM orders;
-- 只有 PRIMARY KEY，没有 user_id 和 status 的索引
```

**修复：**

```sql
-- 添加合适的联合索引
ALTER TABLE orders ADD INDEX idx_user_status_time (user_id, status, create_time);

-- 验证
EXPLAIN SELECT * FROM orders
WHERE user_id = 12345 AND status = 'paid'
ORDER BY create_time DESC LIMIT 20;
-- type=ref, key=idx_user_status_time, rows=15  ← 优化效果显著
```

**预防措施：**
1. 新表上线前，必须经过 DBA/SRE 审查索引设计
2. 慢查询日志持续监控，配置告警
3. 定期使用 `pt-query-digest` 分析慢查询
4. 建立索引变更的变更管理流程

---

## 💻 实战练习

### 练习 1：存储引擎与事务基础

```bash
# 1. 创建测试数据库和表
mysql -u root -e "
CREATE DATABASE IF NOT EXISTS sre_lab;
USE sre_lab;

-- InnoDB 表
CREATE TABLE accounts_innodb (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    balance DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- MyISAM 表
CREATE TABLE logs_myisam (
    id INT PRIMARY KEY AUTO_INCREMENT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=MyISAM;

-- 插入测试数据
INSERT INTO accounts_innodb (name, balance) VALUES
('Alice', 10000.00), ('Bob', 5000.00), ('Carol', 8000.00);
"
```

```sql
-- 2. 体验事务的 ACID 特性
USE sre_lab;

-- 开启事务
START TRANSACTION;

-- 转账：Alice 向 Bob 转 2000
UPDATE accounts_innodb SET balance = balance - 2000 WHERE name = 'Alice';
UPDATE accounts_innodb SET balance = balance + 2000 WHERE name = 'Bob';

-- 查看当前事务中的数据
SELECT * FROM accounts_innodb;

-- 另开一个 mysql 会话查看（RR 隔离级别下看不到未提交的变更）
-- SELECT * FROM accounts_innodb;  -- 在另一个终端执行

-- 提交事务
COMMIT;

-- 验证结果
SELECT * FROM accounts_innodb;

-- 3. 体验事务回滚
START TRANSACTION;
DELETE FROM accounts_innodb WHERE name = 'Carol';
SELECT * FROM accounts_innodb;  -- Carol 消失了
ROLLBACK;
SELECT * FROM accounts_innodb;  -- Carol 又回来了！
```

### 练习 2：索引操作与 EXPLAIN 分析

```bash
# 1. 创建带大量数据的测试表
mysql -u root -e "
USE sre_lab;

CREATE TABLE big_orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    order_no VARCHAR(32) NOT NULL,
    status TINYINT NOT NULL DEFAULT 0,
    amount DECIMAL(10,2) NOT NULL,
    create_time DATETIME NOT NULL,
    update_time DATETIME NOT NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB;

-- 插入 100 万条测试数据（使用存储过程）
DELIMITER //
CREATE PROCEDURE generate_orders(IN num INT)
BEGIN
    DECLARE i INT DEFAULT 0;
    START TRANSACTION;
    WHILE i < num DO
        INSERT INTO big_orders (user_id, order_no, status, amount, create_time, update_time)
        VALUES (
            FLOOR(1 + RAND() * 10000),
            CONCAT('ORD', LPAD(i, 10, '0')),
            FLOOR(RAND() * 4),
            ROUND(RAND() * 10000, 2),
            DATE_ADD('2024-01-01', INTERVAL FLOOR(RAND() * 730) DAY),
            NOW()
        );
        SET i = i + 1;
        IF i % 10000 = 0 THEN
            COMMIT;
            START TRANSACTION;
        END IF;
    END WHILE;
    COMMIT;
END //
DELIMITER ;

CALL generate_orders(1000000);
"
```

```sql
-- 2. EXPLAIN 分析不同查询
USE sre_lab;

-- 全表扫描
EXPLAIN SELECT * FROM big_orders WHERE user_id = 5000;

-- 添加联合索引
ALTER TABLE big_orders ADD INDEX idx_user_status_time (user_id, status, create_time);

-- 使用联合索引
EXPLAIN SELECT * FROM big_orders
WHERE user_id = 5000 AND status = 1
ORDER BY create_time DESC LIMIT 20;

-- 覆盖索引示例
EXPLAIN SELECT user_id, status, create_time FROM big_orders
WHERE user_id = 5000 AND status = 1;

-- 索引失效的场景
EXPLAIN SELECT * FROM big_orders WHERE YEAR(create_time) = 2025;  -- 函数导致失效
EXPLAIN SELECT * FROM big_orders WHERE create_time >= '2025-01-01'
  AND create_time < '2026-01-01';  -- 走索引
```

### 练习 3：锁与死锁排查

```bash
# 准备测试表
mysql -u root -e "
USE sre_lab;
CREATE TABLE lock_test (
    id INT PRIMARY KEY,
    name VARCHAR(50),
    value INT,
    INDEX idx_name (name)
) ENGINE=InnoDB;

INSERT INTO lock_test VALUES (1, 'a', 10), (2, 'b', 20), (3, 'c', 30),
    (5, 'e', 50), (10, 'j', 100);
"
```

```sql
-- 练习 1: 观察行锁
-- 会话 A:
USE sre_lab;
SET autocommit = 0;
UPDATE lock_test SET value = 100 WHERE id = 1;

-- 会话 B（另一个终端）:
USE sre_lab;
SET autocommit = 0;
UPDATE lock_test SET value = 200 WHERE id = 2;  -- 成功，不同行不阻塞
UPDATE lock_test SET value = 300 WHERE id = 1;  -- 阻塞！等待会话 A 的锁

-- 查看锁信息
SELECT * FROM performance_schema.data_locks;
SELECT * FROM performance_schema.data_lock_waits;

-- 练习 2: 观察间隙锁 (Gap Lock)
-- 会话 A:
SET autocommit = 0;
SELECT * FROM lock_test WHERE id = 7 FOR UPDATE;
-- 虽然 id=7 不存在，但 Gap Lock 锁住了 (5, 10) 的间隙

-- 会话 B:
SET autocommit = 0;
INSERT INTO lock_test VALUES (8, 'h', 80);  -- 阻塞！被 Gap Lock 挡住
INSERT INTO lock_test VALUES (11, 'k', 110);  -- 成功，不在间隙内

-- 练习 3: 产生死锁并分析
-- 会话 A:
SET autocommit = 0;
UPDATE lock_test SET value = value + 1 WHERE id = 1;

-- 会话 B:
SET autocommit = 0;
UPDATE lock_test SET value = value + 1 WHERE id = 2;

-- 会话 A:
UPDATE lock_test SET value = value + 1 WHERE id = 2;  -- 等待 B

-- 会话 B:
UPDATE lock_test SET value = value + 1 WHERE id = 1;  -- 死锁！

-- 查看死锁信息
SHOW ENGINE INNODB STATUS\G
-- 找到 LATEST DETECTED DEADLOCK 段落分析
```

---

## 🎯 面试题精选

### 1. 为什么 InnoDB 使用 B+ Tree 而不是 B Tree 或 Hash？

**参考答案：**

| 数据结构 | 对比 |
|---------|------|
| Hash | 等值查询 O(1)，但不支持范围查询、排序、最左前缀 |
| B Tree | 数据存在所有节点，导致每个节点存储的键更少，树更高，I/O 更多 |
| B+ Tree | 数据只在叶子节点，非叶子节点可以存更多索引键 → 树更矮 → I/O 更少；叶子节点双向链表 → 支持范围查询和排序 |

**核心原因：**
1. **磁盘 I/O 最小化**：B+ Tree 的非叶子节点不存数据，扇出度高，3 层树可索引约 2000 万行数据
2. **范围查询高效**：叶子节点双向链表，找到起始点后顺序扫描即可
3. **查询稳定**：所有查询都要走到叶子节点，查询时间稳定为 O(log N)

### 2. 聚簇索引和二级索引的区别？什么是回表？如何避免？

**参考答案：**
- **聚簇索引**：叶子节点存储完整行数据，每张表只有一个（通常为主键）
- **二级索引**：叶子节点存储主键值，可以有多个
- **回表**：通过二级索引找到主键后，再回到聚簇索引查找完整数据
- **避免回表**：使用覆盖索引，查询的列都在索引中，无需回表

### 3. redo log 和 binlog 有什么区别？为什么需要两阶段提交？

**参考答案：**
- **redo log**：InnoDB 引擎层，物理日志，循环写，用于崩溃恢复
- **binlog**：Server 层，逻辑日志，追加写，用于主从复制和 PITR
- **两阶段提交**：保证 redo log 和 binlog 的一致性。如果先写 redo log 再写 binlog，崩溃时可能导致主从数据不一致；两阶段提交通过 prepare 和 commit 两个状态，确保两者要么都成功，要么都失败

### 4. MVCC 是如何实现的？RC 和 RR 隔离级别下有什么区别？

**参考答案：**
- MVCC 通过 undo log 版本链 + Read View 实现非锁定读
- **RC**：每次 SELECT 都创建新的 Read View（能看到其他事务已提交的最新数据）
- **RR**：只在事务第一次 SELECT 时创建 Read View（整个事务期间看到的数据一致）

### 5. InnoDB 的行锁是锁行还是锁索引？

**参考答案：** 锁索引。InnoDB 的行锁是加在索引记录上的：
- 如果有索引，锁住索引记录
- 如果没有索引，InnoDB 会创建隐藏的聚簇索引，但实际效果是锁住所有行（类似表锁）
- 这就是为什么没有索引的 WHERE 条件会导致锁升级

### 6. 如何排查 MySQL 的死锁问题？

**参考答案：**
1. `SHOW ENGINE INNODB STATUS\G` 查看 LATEST DETECTED DEADLOCK
2. 查看 `performance_schema.data_locks` 和 `data_lock_waits`
3. 分析死锁日志中的事务持有的锁和等待的锁
4. 优化方案：固定访问顺序、缩短事务、添加索引、调整隔离级别

### 7. 一个 MySQL 表最多能存多少数据？

**参考答案：**
- 理论上限：64TB（表空间限制）
- 实际建议：单表不超过 2000 万行或 10GB
- 超过后建议分库分表
- InnoDB 页大小 16KB，一个页最少存 2 行，每行最大约 8KB

### 8. 为什么 MySQL 8.0 移除了查询缓存？

**参考答案：**
1. 查询缓存的失效粒度是表级别，任何表的写操作都会导致该表所有缓存失效
2. 在高并发写入场景下，缓存命中率极低，反而增加了维护缓存的开销
3. 查询缓存存在全局锁竞争，影响并发性能
4. 推荐使用应用层缓存（Redis）或 ProxySQL 等中间件实现查询缓存

---

## 📚 深入阅读

### 官方文档
- MySQL 8.0 Reference Manual - InnoDB Storage Engine: https://dev.mysql.com/doc/refman/8.0/en/innodb-storage-engine.html
- MySQL 8.0 Reference Manual - InnoDB Architecture: https://dev.mysql.com/doc/refman/8.0/en/innodb-architecture.html
- MySQL 8.0 Reference Manual - Transaction Isolation Levels: https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-isolation-levels.html

### 推荐书籍
- 《MySQL 技术内幕：InnoDB 存储引擎》— 姜承尧（InnoDB 原理最权威的中文书）
- 《高性能 MySQL（第 4 版）》— Silvia Botros & Jeremy Tinley
- 《MySQL 是怎样运行的》— 小孩子（适合入门理解原理）

### 技术博客
- MySQL Internals Manual: https://dev.mysql.com/doc/internals/en/
- Jeremy Cole 的 InnoDB 系列博客（深入源码分析）
- Percona Blog: https://www.percona.com/blog/

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出 MySQL 三层逻辑架构图并解释各层职责
- [ ] 能对比 InnoDB 与 MyISAM 的 5 个核心差异
- [ ] 能解释事务 ACID 特性各自由什么机制保证
- [ ] 能画出 B+ Tree 结构并解释聚簇索引和二级索引的区别
- [ ] 能解释 redo log、undo log、binlog 各自的作用和写入时机
- [ ] 能解释 MVCC 的工作原理和 Read View 的可见性判断
- [ ] 能说出 InnoDB 三种行锁算法（Record Lock、Gap Lock、Next-Key Lock）

### 实操检查点
- [ ] 能使用 `EXPLAIN` 分析 SQL 执行计划
- [ ] 能创建合适的索引并验证索引是否生效
- [ ] 能通过 `SHOW ENGINE INNODB STATUS` 排查死锁
- [ ] 能使用事务进行数据操作并验证隔离级别效果
- [ ] 能查看和分析 binlog 内容

### 能力验证标准
- [ ] 独立完成一个表的索引设计（覆盖等值查询、范围查询、排序）
- [ ] 排查一个死锁场景并给出优化建议
- [ ] 能向团队成员解释为什么生产环境必须使用 InnoDB
