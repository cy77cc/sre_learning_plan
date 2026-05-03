# Day 71: MySQL 性能调优

> 📅 日期：2026-05-03
> 📖 学习主题：慢查询分析、EXPLAIN 执行计划、索引优化、查询优化、配置调优、连接池、读写分离、分库分表
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 70（MySQL 基础与架构）

## 🎯 学习目标

完成 Day 71 的学习后，你应该能够：
1. 使用慢查询日志和 `pt-query-digest` 定位性能瓶颈 SQL
2. 熟练解读 `EXPLAIN` 执行计划的每一列含义，判断查询是否需要优化
3. 掌握索引优化的核心策略（覆盖索引、索引下推、前缀索引等）
4. 理解 MySQL 关键配置参数的调优方法（Buffer Pool、Redo Log、连接数等）
5. 设计并实施读写分离架构，理解分库分表的适用场景与方案选型
6. 以 SRE 视角建立 MySQL 性能监控体系

---

## 📖 核心知识点

### 1. 慢查询分析

#### 1.1 慢查询日志配置

```sql
-- 查看慢查询日志状态
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- 开启慢查询日志（生产环境建议常开）
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;              -- 超过 1 秒记录
SET GLOBAL log_queries_not_using_indexes = ON; -- 记录未使用索引的查询
SET GLOBAL min_examined_row_limit = 100;     -- 扫描超过 100 行才记录

-- 永久配置 (my.cnf)
-- [mysqld]
-- slow_query_log = ON
-- slow_query_log_file = /var/log/mysql/slow.log
-- long_query_time = 1
-- log_queries_not_using_indexes = ON
-- min_examined_row_limit = 100
```

#### 1.2 慢查询日志分析工具

```bash
# mysqldumpslow — MySQL 自带的慢查询分析工具
# 按执行时间排序，显示前 10 条
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

# 按查询次数排序
mysqldumpslow -s c -t 10 /var/log/mysql/slow.log

# 按返回行数排序
mysqldumpslow -s r -t 10 /var/log/mysql/slow.log

# 参数说明：
# -s: 排序方式 (t=时间, c=次数, l=锁时间, r=行数, at=平均时间)
# -t: 返回前 N 条
# -g: 正则过滤
```

```bash
# pt-query-digest — Percona Toolkit 的专业慢查询分析工具
# 安装
# apt install percona-toolkit  或
# yum install percona-toolkit

# 分析慢查询日志
pt-query-digest /var/log/mysql/slow.log > slow_report.txt

# 分析最近 1 小时的慢查询
pt-query-digest --since '1h' /var/log/mysql/slow.log

# 分析 binlog
mysqlbinlog binlog.000001 | pt-query-digest --type binlog

# 输出示例（简化）：
# Rank  Query ID           Response time  Calls  R/Call  V/M
# ==== ================== ============== ====== ======= =====
#    1  0xABCDEF1234567890  1500.0000 35.2%    500  3.0000  0.12
#    2  0x1234567890ABCDEF   800.0000 18.8%   1000  0.8000  0.05
#
# Query 1: SELECT * FROM orders WHERE user_id = '...'
# → 全表扫描，需要添加索引
```

#### 1.3 Performance Schema 查询分析

```sql
-- 查看最耗时的 SQL（MySQL 8.0）
SELECT
    DIGEST_TEXT AS query,
    COUNT_STAR AS exec_count,
    ROUND(SUM_TIMER_WAIT / 1e12, 2) AS total_time_s,
    ROUND(AVG_TIMER_WAIT / 1e12, 4) AS avg_time_s,
    SUM_ROWS_EXAMINED AS rows_examined,
    SUM_ROWS_SENT AS rows_sent,
    FIRST_SEEN,
    LAST_SEEN
FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 10;

-- 查看全表扫描的 SQL
SELECT
    DIGEST_TEXT AS query,
    COUNT_STAR AS exec_count,
    SUM_ROWS_EXAMINED AS rows_examined,
    SUM_ROWS_SENT AS rows_sent,
    SUM_NO_INDEX_USED AS no_index_count
FROM performance_schema.events_statements_summary_by_digest
WHERE SUM_NO_INDEX_USED > 0
ORDER BY SUM_ROWS_EXAMINED DESC
LIMIT 10;

-- 查看临时表使用情况
SELECT
    DIGEST_TEXT AS query,
    SUM_CREATED_TMP_TABLES AS tmp_tables,
    SUM_CREATED_TMP_DISK_TABLES AS tmp_disk_tables
FROM performance_schema.events_statements_summary_by_digest
WHERE SUM_CREATED_TMP_DISK_TABLES > 0
ORDER BY SUM_CREATED_TMP_DISK_TABLES DESC
LIMIT 10;
```

---

### 2. EXPLAIN 执行计划详解

#### 2.1 EXPLAIN 输出各列含义

```sql
EXPLAIN SELECT * FROM orders
WHERE user_id = 12345 AND status = 'paid'
ORDER BY create_time DESC LIMIT 20;
```

```
┌─────┬───────┬──────┬───────┬──────┬──────┬──────┬──────┬──────┬────────────────┐
│ id  │select │table │ type  │possib│ key  │key_  │ ref  │ rows │ Extra          │
│     │_type  │      │       │le_   │      │len   │      │      │                │
│     │       │      │       │keys  │      │      │      │      │                │
├─────┼───────┼──────┼───────┼──────┼──────┼──────┼──────┼──────┼────────────────┤
│  1  │ SIMPLE│orders│ ref   │idx_  │idx_  │  8   │const │  15  │ Using where;   │
│     │       │      │       │user_ │user_ │      │,const│      │ Using index    │
│     │       │      │       │stat..│stat..│      │      │      │ condition;     │
│     │       │      │       │      │      │      │      │      │ Using filesort │
└─────┴───────┴──────┴───────┴──────┴──────┴──────┴──────┴──────┴────────────────┘
```

#### 2.2 type 列（访问类型）— 从好到差

```
┌──────────────┬───────────────────────────────────────────────────────┬───────────┐
│ type 值      │ 含义                                                  │ 性能评级  │
├──────────────┼───────────────────────────────────────────────────────┼───────────┤
│ system       │ 表只有一行（系统表）                                  │ 最好      │
│ const        │ 主键或唯一索引等值查询，最多返回一行                  │ 极好      │
│ eq_ref       │ 连接查询中，驱动表每行在被驱动表中用主键/唯一索引    │ 很好      │
│ ref          │ 非唯一索引等值查询                                    │ 好        │
│ fulltext     │ 全文索引                                              │ 特殊      │
│ ref_or_null  │ 类似 ref，但额外搜索 NULL 值                          │ 一般      │
│ index_merge  │ 使用多个索引的合并                                    │ 一般      │
│ unique_subq  │ IN 子查询使用唯一索引                                 │ 一般      │
│ index_subq   │ IN 子查询使用普通索引                                 │ 一般      │
│ range        │ 索引范围查询（BETWEEN, >, <, IN）                     │ 可接受    │
│ index        │ 全索引扫描（遍历整棵索引树）                          │ 差        │
│ ALL          │ 全表扫描                                              │ 最差      │
└──────────────┴───────────────────────────────────────────────────────┴───────────┘

优化目标：至少达到 range 级别，最好 ref 或更优
```

#### 2.3 key 列与 Extra 列详解

```
key 列：
  -  实际使用的索引名称
  -  NULL 表示没有使用索引
  -  可以用 FORCE INDEX/USE INDEX/IGNORE INDEX 干预

rows 列：
  -  预估需要扫描的行数（不是精确值）
  -  越小越好，超过 1 万行需要关注

Extra 列常见值：

  ✅ Using index          → 覆盖索引，无需回表
  ✅ Using where          → Server 层过滤，不影响性能
  ✅ Using index condition→ 索引下推 (ICP)，减少回表次数
  ⚠️ Using temporary      → 使用临时表，需关注
  ⚠️ Using filesort       → 额外排序操作，需关注
  ❌ Using join buffer     → 连接没有使用索引
  ❌ Select tables optimized away → 聚合函数直接在索引上完成
```

#### 2.4 EXPLAIN 实战分析

```sql
-- 场景 1: 全表扫描 → 需要加索引
EXPLAIN SELECT * FROM orders WHERE user_id = 12345;
-- type=ALL, key=NULL, rows=5000000  ❌

-- 修复：添加索引
ALTER TABLE orders ADD INDEX idx_user_id (user_id);
EXPLAIN SELECT * FROM orders WHERE user_id = 12345;
-- type=ref, key=idx_user_id, rows=15  ✅

-- 场景 2: 索引失效 — 隐式类型转换
-- phone 是 VARCHAR 类型
EXPLAIN SELECT * FROM users WHERE phone = 13800138000;
-- type=ALL  ❌  数字与字符串比较，索引失效
EXPLAIN SELECT * FROM users WHERE phone = '13800138000';
-- type=ref  ✅

-- 场景 3: 索引失效 — 函数操作
EXPLAIN SELECT * FROM orders WHERE YEAR(create_time) = 2025;
-- type=ALL  ❌
EXPLAIN SELECT * FROM orders
WHERE create_time >= '2025-01-01' AND create_time < '2026-01-01';
-- type=range  ✅

-- 场景 4: 索引下推 (ICP) — MySQL 5.6+
-- 联合索引 (user_id, status, create_time)
EXPLAIN SELECT * FROM orders
WHERE user_id = 12345 AND status LIKE '%paid%';
-- Extra: Using index condition  ✅  ICP 在引擎层过滤 status

-- 场景 5: 排序优化
-- Using filesort → 没有利用索引排序
EXPLAIN SELECT * FROM orders
WHERE user_id = 12345 ORDER BY create_time DESC;
-- 如果索引是 (user_id)，Extra 中会有 Using filesort

-- 如果索引是 (user_id, create_time)
ALTER TABLE orders ADD INDEX idx_user_time (user_id, create_time);
EXPLAIN SELECT * FROM orders
WHERE user_id = 12345 ORDER BY create_time DESC;
-- Extra: Using index condition  ✅  利用索引排序，无 filesort

-- 场景 6: 分页优化
-- 深分页问题
EXPLAIN SELECT * FROM orders ORDER BY id LIMIT 1000000, 20;
-- rows=1000020  ❌  扫描 100 万行只取 20 行

-- 优化方案：延迟关联
EXPLAIN SELECT o.* FROM orders o
INNER JOIN (SELECT id FROM orders ORDER BY id LIMIT 1000000, 20) t
ON o.id = t.id;
-- 子查询使用覆盖索引，只回表 20 次  ✅
```

---

### 3. 索引优化策略

#### 3.1 索引设计原则

```
┌──────────────────────────────────────────────────────────────────┐
│                  索引设计核心原则                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 选择性高的列优先                                             │
│     选择性 = 不重复的值 / 总行数                                 │
│     user_id (选择性 0.9) > status (选择性 0.001)                │
│                                                                  │
│  2. 联合索引的列顺序：等值查询在前，范围查询在后                 │
│     WHERE a=1 AND b>10 → INDEX(a, b)                           │
│     不是 INDEX(b, a)                                             │
│                                                                  │
│  3. 覆盖索引优先                                                 │
│     SELECT a, b FROM t WHERE a=1 → INDEX(a, b)                  │
│                                                                  │
│  4. 避免冗余索引                                                 │
│     INDEX(a, b) 已经覆盖 INDEX(a)，不需要单独建 INDEX(a)        │
│                                                                  │
│  5. 避免过多索引                                                 │
│     每个索引都会增加写入开销（INSERT/UPDATE/DELETE）              │
│     单表索引建议不超过 5-6 个                                    │
│                                                                  │
│  6. 前缀索引处理长字符串                                         │
│     INDEX(email(20)) 代替 INDEX(email)                          │
│     注意：前缀索引不能用于 ORDER BY 和覆盖索引                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.2 联合索引与最左前缀详解

```sql
-- 联合索引 (a, b, c) 的使用规则

-- ✅ 完整使用三列
WHERE a=1 AND b=2 AND c=3

-- ✅ 使用前两列
WHERE a=1 AND b=2

-- ✅ 只使用第一列
WHERE a=1

-- ✅ 范围查询后的列不走索引
WHERE a=1 AND b>10 AND c=3  → 使用 (a, b)，c 不走索引

-- ⚠️ MySQL 8.0 的 Index Skip Scan
-- 在某些情况下，即使不满足最左前缀也能使用索引
-- 例如：INDEX(status, user_id)
-- WHERE user_id = 12345  → 可能使用 Index Skip Scan

-- 验证索引使用情况
SHOW INDEX FROM orders;
ANALYZE TABLE orders;  -- 更新索引统计信息
```

#### 3.3 索引下推 (ICP)

```
Index Condition Pushdown (ICP) — MySQL 5.6 引入

没有 ICP（MySQL 5.5 及以前）：
  存储引擎层：通过索引找到 user_id=12345 的所有记录 → 回表取完整数据
  Server 层：过滤 status='paid' 的记录

  假设 user_id=12345 有 1000 条记录，只有 10 条 status='paid'
  → 回表 1000 次，Server 层过滤后只返回 10 条

有 ICP（MySQL 5.6+）：
  存储引擎层：通过索引找到 user_id=12345 的记录
             在索引层直接过滤 status='paid'（因为联合索引包含 status）
             只对满足条件的 10 条记录回表

  → 回表 10 次，减少 99% 的回表操作

  EXPLAIN Extra 中显示：Using index condition
```

#### 3.4 索引失效场景总结

```sql
-- ❌ 对索引列使用函数
WHERE YEAR(create_time) = 2025
WHERE DATE_FORMAT(create_time, '%Y-%m') = '2025-01'

-- ❌ 对索引列做运算
WHERE id + 1 = 100
WHERE id = 100 - 1  -- ✅ 右边运算不影响

-- ❌ 隐式类型转换
WHERE phone = 13800138000  -- phone 是 VARCHAR

-- ❌ LIKE 左模糊
WHERE name LIKE '%abc'  -- ❌
WHERE name LIKE 'abc%'  -- ✅

-- ❌ OR 条件中有非索引列
WHERE indexed_col = 1 OR non_indexed_col = 2  -- ❌
-- 解决：给 non_indexed_col 也加索引，或用 UNION

-- ❌ 使用 != 或 NOT IN（通常）
WHERE status != 1  -- 可能不走索引（取决于数据分布）
WHERE status NOT IN (1, 2, 3)

-- ❌ IS NULL / IS NOT NULL（取决于数据分布和 MySQL 版本）
WHERE deleted_at IS NOT NULL

-- ✅ MySQL 8.0 改进了对 NOT NULL 列的 IS NULL 优化
```

---

### 4. 查询优化技巧

#### 4.1 JOIN 优化

```sql
-- 驱动表与被驱动表的选择
-- 小表驱动大表（优化器通常自动选择）

-- EXPLAIN 查看 JOIN 执行计划
EXPLAIN SELECT o.*, u.name
FROM orders o
JOIN users u ON o.user_id = u.id
WHERE o.status = 1;

-- 确保 JOIN 列有索引
-- 被驱动表的关联列必须有索引
ALTER TABLE orders ADD INDEX idx_user_id (user_id);

-- 避免在 JOIN 条件上使用函数
-- ❌
SELECT * FROM orders o JOIN users u ON CAST(o.user_id AS CHAR) = u.id;
-- ✅
SELECT * FROM orders o JOIN users u ON o.user_id = u.id;

-- 避免大量 JOIN
-- MySQL 建议单次查询 JOIN 不超过 5-6 个表
-- 超过时考虑拆分查询或反范式化
```

#### 4.2 子查询优化

```sql
-- ❌ 相关子查询（每行执行一次）
SELECT * FROM orders o
WHERE EXISTS (SELECT 1 FROM users u WHERE u.id = o.user_id AND u.status = 1);

-- ✅ 改写为 JOIN
SELECT o.* FROM orders o
JOIN users u ON o.user_id = u.id AND u.status = 1;

-- ❌ IN 子查询（大结果集）
SELECT * FROM orders
WHERE user_id IN (SELECT id FROM users WHERE age > 25);

-- ✅ 改写为 JOIN（MySQL 8.0 优化器通常会自动转换）
SELECT o.* FROM orders o
JOIN users u ON o.user_id = u.id
WHERE u.age > 25;

-- ❌ 在 SELECT 列表中使用子查询
SELECT o.*,
    (SELECT name FROM users u WHERE u.id = o.user_id) AS user_name
FROM orders o;

-- ✅ 改写为 JOIN
SELECT o.*, u.name AS user_name
FROM orders o
JOIN users u ON o.user_id = u.id;
```

#### 4.3 分页查询优化

```sql
-- ❌ 深分页问题
SELECT * FROM orders ORDER BY id LIMIT 1000000, 20;
-- 扫描 1000020 行，丢弃前 100 万行

-- ✅ 方案 1：延迟关联（Deferred Join）
SELECT o.* FROM orders o
INNER JOIN (
    SELECT id FROM orders ORDER BY id LIMIT 1000000, 20
) t ON o.id = t.id;
-- 子查询走覆盖索引，只需回表 20 次

-- ✅ 方案 2：游标分页（记住上次最大 ID）
SELECT * FROM orders WHERE id > 1000000 ORDER BY id LIMIT 20;
-- 直接定位，无需扫描前面的行

-- ✅ 方案 3：业务限制
-- 不允许用户直接跳到第 50000 页
-- 只允许"上一页"和"下一页"

-- ✅ 方案 4：Elasticsearch 搜索场景
-- 对于搜索类分页，使用 ES 的 search_after
```

#### 4.4 COUNT 优化

```sql
-- COUNT(*) vs COUNT(1) vs COUNT(col)
-- COUNT(*) = COUNT(1)：统计所有行（包括 NULL）
-- COUNT(col)：统计 col 不为 NULL 的行

-- InnoDB 中 COUNT(*) 的实现
-- 没有存储行数，必须遍历（聚簇索引或最小的二级索引）
-- MyISAM 直接存储行数，COUNT(*) 极快

-- 优化方案：
-- 1. 使用近似值
EXPLAIN SELECT * FROM orders;  -- rows 列是近似值

-- 2. 维护计数表
CREATE TABLE table_counts (
    table_name VARCHAR(64) PRIMARY KEY,
    row_count BIGINT NOT NULL DEFAULT 0
);

-- 使用触发器维护（写入性能影响）
-- 或者定期更新

-- 3. 缓存计数
-- 使用 Redis 缓存 COUNT 结果
-- 定期与数据库同步

-- 4. 小表直接 COUNT，大表用近似值或缓存
```

#### 4.5 UPDATE/DELETE 优化

```sql
-- ❌ 大事务：一次更新大量行
UPDATE orders SET status = 2 WHERE status = 1 AND create_time < '2025-01-01';
-- 可能更新 100 万行，长时间持锁

-- ✅ 分批更新
DELIMITER //
CREATE PROCEDURE batch_update_orders()
BEGIN
    DECLARE affected INT DEFAULT 1;
    WHILE affected > 0 DO
        UPDATE orders SET status = 2
        WHERE status = 1 AND create_time < '2025-01-01'
        LIMIT 1000;
        SET affected = ROW_COUNT();
        -- 短暂释放锁，让其他事务有机会执行
        SELECT SLEEP(0.1);
    END WHILE;
END //
DELIMITER ;

-- ✅ 使用 pt-archiver 进行大批量数据清理
-- pt-archiver --source h=localhost,D=sre_lab,t=old_orders \
--   --purge --where "create_time < '2024-01-01'" --limit 1000 --sleep 0.5
```

---

### 5. MySQL 配置调优

#### 5.1 关键配置参数

```ini
[mysqld]
# ============================================================
# InnoDB Buffer Pool — 最重要的参数
# ============================================================
# 建议：物理内存的 60-80%
# 16GB 内存的服务器 → innodb_buffer_pool_size = 10G
innodb_buffer_pool_size = 10G

# 多实例减少锁竞争（>=1GB 时建议 8-16）
innodb_buffer_pool_instances = 8

# 预热：重启后自动加载热数据到 Buffer Pool
innodb_buffer_pool_dump_at_shutdown = ON
innodb_buffer_pool_load_at_startup = ON

# ============================================================
# Redo Log
# ============================================================
# 较大的 redo log 减少刷盘频率，但崩溃恢复时间更长
# 写入密集型场景建议 1-4GB
innodb_log_file_size = 1G
innodb_log_files_in_group = 2
innodb_log_buffer_size = 64M

# 刷盘策略（0/1/2）
# 0: 每秒刷盘（可能丢失 1 秒数据）
# 1: 每次提交都刷盘（最安全，性能最差）—— 默认值
# 2: 每次提交写入 OS 缓存，每秒 fsync
innodb_flush_log_at_trx_commit = 1

# ============================================================
# IO 配置
# ============================================================
# 使用 O_DIRECT 避免双重缓存（InnoDB Buffer Pool + OS Page Cache）
innodb_flush_method = O_DIRECT

# IO 容量（SSD 建议 2000-10000）
innodb_io_capacity = 2000
innodb_io_capacity_max = 4000

# 读写 IO 线程数
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# ============================================================
# 连接与线程
# ============================================================
# 最大连接数
max_connections = 500

# 线程缓存
thread_cache_size = 64

# ============================================================
# 表与缓存
# ============================================================
# 表定义缓存
table_definition_cache = 2000

# 表文件句柄缓存
table_open_cache = 4000

# 临时表大小
tmp_table_size = 64M
max_heap_table_size = 64M

# ============================================================
# 排序与连接缓冲
# ============================================================
sort_buffer_size = 4M
join_buffer_size = 4M
read_buffer_size = 2M
read_rnd_buffer_size = 4M

# ============================================================
# Binlog
# ============================================================
log_bin = mysql-bin
binlog_format = ROW
binlog_row_image = FULL
sync_binlog = 1               # 与 innodb_flush_log_at_trx_commit=1 配合保证数据安全
expire_logs_days = 7
max_binlog_size = 256M

# ============================================================
# 慢查询
# ============================================================
slow_query_log = ON
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
log_queries_not_using_indexes = ON
```

#### 5.2 配置调优方法论

```
┌──────────────────────────────────────────────────────────────┐
│                MySQL 配置调优流程                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Step 1: 建立基线                                             │
│  - 记录当前 QPS、TPS、响应时间、连接数                       │
│  - SHOW GLOBAL STATUS; 记录关键指标                          │
│                                                              │
│  Step 2: 监控识别瓶颈                                         │
│  - Buffer Pool 命中率 (<99% → 增大 buffer_pool_size)        │
│  - 慢查询比例 (>1% → 优化 SQL)                               │
│  - 连接使用率 (>80% → 增大 max_connections)                  │
│  - 临时表落盘率 (→ 增大 tmp_table_size)                      │
│                                                              │
│  Step 3: 单参数调整                                           │
│  - 每次只调整一个参数                                        │
│  - 观察 24-48 小时                                           │
│  - 有回退方案                                                │
│                                                              │
│  Step 4: 验证效果                                             │
│  - 对比调整前后的性能指标                                    │
│  - 无改善则回退                                              │
│                                                              │
│  Step 5: 持续优化                                             │
│  - 定期 review 配置                                          │
│  - 随业务增长调整                                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 5.3 关键状态指标监控

```sql
-- Buffer Pool 命中率（目标 >99%）
SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read%';
-- 命中率 = 1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)

-- 连接使用率
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';
-- 使用率 = Threads_connected / max_connections

-- QPS 和 TPS
SHOW GLOBAL STATUS LIKE 'Questions';
SHOW GLOBAL STATUS LIKE 'Com_commit';
SHOW GLOBAL STATUS LIKE 'Com_rollback';

-- 临时表使用
SHOW GLOBAL STATUS LIKE 'Created_tmp%';
-- Created_tmp_disk_tables / Created_tmp_tables < 25% 为正常

-- 线程缓存命中率
SHOW GLOBAL STATUS LIKE 'Threads_created';
SHOW VARIABLES LIKE 'thread_cache_size';

-- 表锁竞争
SHOW GLOBAL STATUS LIKE 'Table_locks_waited';
-- Table_locks_waited 应该很低

-- InnoDB 行锁等待
SHOW GLOBAL STATUS LIKE 'Innodb_row_lock%';
-- Innodb_row_lock_time_avg 平均锁等待时间
```

---

### 6. 连接池

#### 6.1 为什么需要连接池

```
没有连接池：
  每次请求 → 创建 TCP 连接 → 认证 → 执行 SQL → 关闭连接
  问题：
  - TCP 三次握手开销
  - MySQL 认证开销（密码验证、权限加载）
  - 频繁创建/销毁线程
  - max_connections 限制

有连接池：
  启动时 → 创建 N 个连接 → 放入池中
  请求时 → 从池中取连接 → 执行 SQL → 归还连接
  优势：
  - 连接复用，减少创建开销
  - 控制并发数，保护数据库
  - 统一管理连接生命周期
```

#### 6.2 ProxySQL 连接池配置

```sql
-- ProxySQL 是 MySQL 中间件，提供连接池、读写分离、查询缓存等功能

-- 安装 ProxySQL 后配置
-- 添加 MySQL 后端服务器
INSERT INTO mysql_servers (hostgroup_id, hostname, port, weight)
VALUES
(10, '10.0.1.1', 3306, 1000),  -- 写组 (hostgroup 10)
(20, '10.0.1.2', 3306, 500),   -- 读组 (hostgroup 20)
(20, '10.0.1.3', 3306, 500);   -- 读组 (hostgroup 20)

-- 配置读写分离规则
INSERT INTO mysql_query_rules (rule_id, active, match_pattern, destination_hostgroup)
VALUES
(1, 1, '^SELECT.*FOR UPDATE', 10),  -- SELECT FOR UPDATE → 写组
(2, 1, '^SELECT', 20);              -- 普通 SELECT → 读组

-- 配置连接池参数
SET mysql-max_connections = 2048;
SET mysql-default_max_latency_ms = 1000;

-- 加载配置
LOAD MYSQL SERVERS TO RUNTIME;
LOAD MYSQL QUERY RULES TO RUNTIME;
SAVE MYSQL SERVERS TO DISK;
SAVE MYSQL QUERY RULES TO DISK;
```

#### 6.3 应用层连接池配置

```python
# Python — SQLAlchemy 连接池配置
from sqlalchemy import create_engine

engine = create_engine(
    'mysql+pymysql://user:pass@localhost:3306/mydb',
    pool_size=20,           # 连接池大小
    max_overflow=10,        # 超出 pool_size 后最多再创建的连接数
    pool_timeout=30,        # 从池中获取连接的超时时间
    pool_recycle=3600,      # 连接回收时间（避免 MySQL 的 wait_timeout 断开）
    pool_pre_ping=True,     # 使用前检测连接是否有效
)
```

```go
// Go — database/sql 连接池配置
import (
    "database/sql"
    "time"
)

db, err := sql.Open("mysql", "user:pass@tcp(localhost:3306)/mydb")
db.SetMaxOpenConns(100)               // 最大打开连接数
db.SetMaxIdleConns(25)                // 最大空闲连接数
db.SetConnMaxLifetime(30 * time.Minute) // 连接最大存活时间
db.SetConnMaxIdleTime(5 * time.Minute)  // 空闲连接最大存活时间
```

---

### 7. 读写分离

#### 7.1 读写分离架构

```
┌──────────┐     ┌──────────────────┐     ┌──────────────────────┐
│          │     │                  │     │    Master (写)        │
│  应用    │ ──→ │  代理/中间件     │ ──→ │  处理 INSERT/UPDATE   │
│  服务器  │     │  ProxySQL/       │     │  DELETE/SELECT FOR    │
│          │     │  MySQL Router    │     │  UPDATE               │
│          │     │                  │     └──────────┬───────────┘
│          │     │  读写分离规则：  │                │
│          │     │  SELECT → Slave  │     ┌──────────┴───────────┐
│          │     │  写操作 → Master │     │    复制 (Replication) │
│          │     │                  │     └──┬────────────────┬──┘
│          │     └──────────────────┘        │                │
│          │                                 ▼                ▼
│          │                    ┌────────────────┐  ┌────────────────┐
│          │                    │  Slave 1 (读)  │  │  Slave 2 (读)  │
│          │                    │  处理 SELECT   │  │  处理 SELECT   │
└──────────┘                    └────────────────┘  └────────────────┘
```

#### 7.2 读写分离注意事项

```
1. 主从延迟问题
   -  写入 Master 后立即从 Slave 读，可能读到旧数据
   -  解决方案：
      a. 关键读走 Master（写后读一致性）
      b. 使用半同步复制减少延迟
      c. 监控 Seconds_Behind_Master，超过阈值时切换读到 Master

2. 事务内的一致性
   -  同一事务中的所有操作必须在同一连接上
   -  不能事务内一半走 Master，一半走 Slave

3. 连接路由策略
   -  基于 SQL 类型：SELECT 走 Slave
   -  基于事务：事务内所有操作走 Master
   -  基于 Hint：/*master*/ 强制走 Master
```

---

### 8. 分库分表

#### 8.1 什么时候需要分库分表

```
触发条件：
  -  单表行数超过 2000 万或数据量超过 10GB
  -  单库写入 QPS 超过 5000
  -  单实例磁盘空间不足
  -  单实例 CPU/IO 已经成为瓶颈

不建议过早分库分表：
  -  优先优化 SQL 和索引
  -  优先读写分离
  -  优先缓存（Redis）
  -  分库分表带来的复杂性远超预期
```

#### 8.2 分库分表方案

```
垂直拆分：
  ┌──────────────────────────────────────────────┐
  │ 垂直分库：按业务拆分                          │
  │                                              │
  │  用户库(user_db): users, user_profiles       │
  │  订单库(order_db): orders, order_items       │
  │  商品库(product_db): products, categories    │
  │                                              │
  │  优点：业务解耦，独立扩缩容                   │
  │  缺点：跨库 JOIN 需要应用层处理              │
  ├──────────────────────────────────────────────┤
  │ 垂直分表：按列拆分                            │
  │                                              │
  │  users 表 → users (热数据) + user_details (冷数据) │
  │                                              │
  │  优点：减少单行数据量，提高缓存效率           │
  │  缺点：需要 JOIN 查询完整数据                 │
  └──────────────────────────────────────────────┘

水平拆分：
  ┌──────────────────────────────────────────────┐
  │ 水平分表：同一数据库内拆分                    │
  │                                              │
  │  orders → orders_0, orders_1, ..., orders_15 │
  │  路由规则：order_id % 16                      │
  │                                              │
  ├──────────────────────────────────────────────┤
  │ 水平分库分表：跨数据库实例拆分                │
  │                                              │
  │  order_db_0: orders_0 ~ orders_3             │
  │  order_db_1: orders_4 ~ orders_7             │
  │  order_db_2: orders_8 ~ orders_11            │
  │  order_db_3: orders_12 ~ orders_15           │
  │  路由规则：order_id % 4 → db, (order_id/4) % 4 → table │
  │                                              │
  │  优点：突破单库/单表瓶颈                      │
  │  缺点：分布式事务、跨库查询、数据迁移复杂     │
  └──────────────────────────────────────────────┘
```

#### 8.3 分片键选择

```sql
-- 分片键选择原则
-- 1. 查询频率最高的字段
-- 2. 数据分布均匀（高基数）
-- 3. 避免跨分片查询

-- 常见分片策略
-- 按用户 ID 分片（电商场景）
-- user_id % 16 → 确保同一用户的数据在同一分片

-- 按时间分片（日志场景）
-- 按月分表：logs_202501, logs_202502, ...

-- 按哈希分片（通用）
-- CRC32(sharding_key) % shard_count

-- 分片中间件选型
-- ShardingSphere (Java 生态，功能全面)
-- Vitess (YouTube 开源，K8s 原生)
-- ProxySQL (轻量级，主要做读写分离)
-- MySQL Router (官方，配合 InnoDB Cluster)
```

---

### 9. SRE 实战案例

#### 9.1 案例：慢查询导致数据库 CPU 100%

**现象：**
- 某电商平台大促期间，MySQL CPU 使用率飙到 100%
- 大量请求超时，用户无法下单
- `SHOW PROCESSLIST` 显示 200+ 个活跃查询

**诊断过程：**

```sql
-- Step 1: 查看当前运行的查询
SHOW FULL PROCESSLIST;
-- 发现大量类似查询：
-- SELECT * FROM products WHERE category_id = 5 AND price > 100 ORDER BY sales_count DESC;

-- Step 2: EXPLAIN 分析
EXPLAIN SELECT * FROM products WHERE category_id = 5 AND price > 100 ORDER BY sales_count DESC;
-- type=ALL, rows=2000000, Extra=Using where; Using filesort
-- 全表扫描 + 文件排序！

-- Step 3: 检查索引
SHOW INDEX FROM products;
-- 只有 PRIMARY KEY，没有 category_id 和 price 的索引

-- Step 4: 分析慢查询日志
-- pt-query-digest 显示该 SQL 平均执行 3.5 秒，每秒执行 500+ 次
```

**根因：** products 表 200 万行数据，查询没有索引，每秒 500+ 次全表扫描 + 文件排序。

**紧急修复：**

```sql
-- 1. 添加索引（在线 DDL，MySQL 5.6+）
ALTER TABLE products ADD INDEX idx_category_price_sales (category_id, price, sales_count),
    ALGORITHM=INPLACE, LOCK=NONE;

-- 2. 验证
EXPLAIN SELECT * FROM products WHERE category_id = 5 AND price > 100 ORDER BY sales_count DESC;
-- type=range, key=idx_category_price_sales, rows=500, Extra=Using index condition ✅
```

**长期预防：**
1. 新功能上线前必须经过 SQL 审核（使用 SQL Review 工具）
2. 慢查询日志实时监控，告警阈值 1 秒
3. 定期 `pt-query-digest` 分析 Top 10 慢查询
4. 建立索引设计规范

---

## 💻 实战练习

### 练习 1：EXPLAIN 深度分析

```sql
USE sre_lab;

-- 创建测试表和数据
CREATE TABLE products (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    category_id INT NOT NULL,
    brand_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    status TINYINT NOT NULL DEFAULT 1,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category_id),
    INDEX idx_brand (brand_id),
    INDEX idx_status_time (status, create_time)
) ENGINE=InnoDB;

-- 插入测试数据（使用存储过程）
DELIMITER //
CREATE PROCEDURE gen_products(IN num INT)
BEGIN
    DECLARE i INT DEFAULT 0;
    WHILE i < num DO
        INSERT INTO products (category_id, brand_id, name, price, stock, status, create_time)
        VALUES (
            FLOOR(1 + RAND() * 50),
            FLOOR(1 + RAND() * 200),
            CONCAT('Product_', i),
            ROUND(10 + RAND() * 9990, 2),
            FLOOR(RAND() * 1000),
            IF(RAND() > 0.3, 1, 0),
            DATE_ADD('2024-01-01', INTERVAL FLOOR(RAND() * 730) DAY)
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL gen_products(500000);
ANALYZE TABLE products;

-- 练习：分析以下查询的执行计划
-- 1. 全表扫描
EXPLAIN SELECT * FROM products WHERE name LIKE '%Phone%';

-- 2. 索引范围查询
EXPLAIN SELECT * FROM products WHERE category_id BETWEEN 10 AND 20;

-- 3. 联合索引使用
EXPLAIN SELECT * FROM products WHERE status = 1 AND create_time > '2025-06-01';

-- 4. 排序优化
EXPLAIN SELECT * FROM products WHERE category_id = 5 ORDER BY price DESC LIMIT 20;

-- 5. 分页优化
EXPLAIN SELECT * FROM products ORDER BY id LIMIT 400000, 20;
-- 对比延迟关联方案
EXPLAIN SELECT p.* FROM products p
INNER JOIN (SELECT id FROM products ORDER BY id LIMIT 400000, 20) t ON p.id = t.id;

-- 6. COUNT 查询
EXPLAIN SELECT COUNT(*) FROM products WHERE category_id = 5;

-- 7. 子查询 vs JOIN
EXPLAIN SELECT * FROM products
WHERE category_id IN (SELECT id FROM categories WHERE status = 1);
EXPLAIN SELECT p.* FROM products p JOIN categories c ON p.category_id = c.id WHERE c.status = 1;
```

### 练习 2：慢查询优化实战

```sql
-- 场景：电商订单查询系统
USE sre_lab;

CREATE TABLE order_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id)
) ENGINE=InnoDB;

DELIMITER //
CREATE PROCEDURE gen_order_items(IN num INT)
BEGIN
    DECLARE i INT DEFAULT 0;
    WHILE i < num DO
        INSERT INTO order_items (order_id, product_id, quantity, unit_price, create_time)
        VALUES (
            FLOOR(1 + RAND() * 100000),
            FLOOR(1 + RAND() * 10000),
            FLOOR(1 + RAND() * 5),
            ROUND(10 + RAND() * 990, 2),
            DATE_ADD('2024-01-01', INTERVAL FLOOR(RAND() * 730) DAY)
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL gen_order_items(2000000);
ANALYZE TABLE order_items;

-- 优化以下查询（先 EXPLAIN，再优化）
-- 查询 1：统计每个订单的总金额
EXPLAIN SELECT order_id, SUM(quantity * unit_price) AS total
FROM order_items GROUP BY order_id;

-- 查询 2：查询特定产品在特定时间段的销售情况
EXPLAIN SELECT * FROM order_items
WHERE product_id = 1234 AND create_time BETWEEN '2025-01-01' AND '2025-06-30';

-- 查询 3：查询金额最高的 100 个订单项
EXPLAIN SELECT * FROM order_items
ORDER BY quantity * unit_price DESC LIMIT 100;
```

### 练习 3：配置调优模拟

```bash
# 查看当前 MySQL 配置
mysql -u root -e "SHOW VARIABLES LIKE 'innodb_buffer_pool_size';"
mysql -u root -e "SHOW VARIABLES LIKE 'max_connections';"
mysql -u root -e "SHOW VARIABLES LIKE 'innodb_flush_log_at_trx_commit';"

# 查看关键状态指标
mysql -u root -e "
SHOW GLOBAL STATUS WHERE Variable_name IN (
    'Innodb_buffer_pool_read_requests',
    'Innodb_buffer_pool_reads',
    'Threads_connected',
    'Threads_created',
    'Created_tmp_disk_tables',
    'Created_tmp_tables',
    'Slow_queries',
    'Questions',
    'Com_commit',
    'Com_rollback',
    'Innodb_row_lock_waits',
    'Innodb_row_lock_time_avg',
    'Table_locks_waited'
);
"

# 计算 Buffer Pool 命中率
# 命中率 = 1 - (Innodb_buffer_pool_reads / Innodb_buffer_pool_read_requests)
# 目标 > 99%

# 计算临时表落盘率
# 落盘率 = Created_tmp_disk_tables / Created_tmp_tables
# 目标 < 25%
```

---

## 🎯 面试题精选

### 1. 如何优化一个慢查询？你的排查思路是什么？

**参考答案：**

排查流程：
1. **定位慢查询**：开启慢查询日志，使用 `pt-query-digest` 分析 Top N 慢查询
2. **EXPLAIN 分析**：查看执行计划，重点关注 type、key、rows、Extra
3. **判断根因**：
   - type=ALL → 全表扫描 → 添加索引
   - Extra=Using filesort → 排序无法用索引 → 调整索引或 SQL
   - Extra=Using temporary → 使用临时表 → 优化 GROUP BY/ORDER BY
   - rows 很大 → 扫描行数过多 → 优化 WHERE 条件
4. **优化手段**：添加索引、改写 SQL、分页优化、反范式化
5. **验证效果**：EXPLAIN 确认执行计划改善，监控实际响应时间

### 2. EXPLAIN 中的 type 列有哪些值？分别代表什么？

**参考答案：** 从好到差：system > const > eq_ref > ref > range > index > ALL
- const：主键或唯一索引等值查询
- eq_ref：JOIN 时主键/唯一索引关联
- ref：普通索引等值查询
- range：索引范围扫描
- index：全索引扫描
- ALL：全表扫描（最差，需要优化）

### 3. 什么是覆盖索引？什么是索引下推？

**参考答案：**
- **覆盖索引**：查询所需的列都在索引中，不需要回表读取数据行。EXPLAIN 中显示 `Using index`
- **索引下推 (ICP)**：MySQL 5.6 引入，在存储引擎层就对索引列进行过滤，减少回表次数。EXPLAIN 中显示 `Using index condition`

### 4. innodb_flush_log_at_trx_commit 设置为 0、1、2 有什么区别？

**参考答案：**
- **1**（默认）：每次提交都 fsync 到磁盘，最安全，性能最差
- **0**：每秒将 log buffer 写入 OS 缓存并 fsync，可能丢失 1 秒数据
- **2**：每次提交写入 OS 缓存，每秒 fsync 到磁盘，折中方案
- 生产环境建议：金融场景用 1，一般业务可考虑 2

### 5. 分库分表的时机？什么时候不应该分库分表？

**参考答案：**

应该分库分表：
- 单表超过 2000 万行或 10GB
- 单库写入 QPS 超过 5000
- 单实例磁盘/CPU/IO 成为瓶颈

不应该过早分库分表：
- 先优化 SQL 和索引（可能 90% 的问题在这里解决）
- 先读写分离
- 先加缓存（Redis）
- 分库分表会带来分布式事务、跨库查询、全局 ID、数据迁移等复杂性

### 6. 如何处理 MySQL 的深分页问题？

**参考答案：**
1. **延迟关联**：先用覆盖索引查出 ID，再 JOIN 取完整数据
2. **游标分页**：记住上一页最后一条的 ID，用 `WHERE id > last_id LIMIT 20`
3. **业务限制**：不允许跳页，只能上一页/下一页
4. **搜索引擎**：搜索场景用 Elasticsearch 的 `search_after`

### 7. Buffer Pool 命中率低怎么办？

**参考答案：**
1. 增大 `innodb_buffer_pool_size`（物理内存 60-80%）
2. 检查是否有大表全表扫描挤出热点数据
3. 使用 `innodb_buffer_pool_dump_at_shutdown` 保持热点数据
4. 优化 SQL 减少不必要的全表扫描
5. 监控 `SHOW ENGINE INNODB STATUS` 中的 Buffer Pool 统计

### 8. 如何设计一个支持千万级数据的 MySQL 表？

**参考答案：**
1. 合理设计主键（自增 INT/BIGINT，避免 UUID）
2. 精心设计索引（覆盖高频查询，避免冗余）
3. 合适的字符集和字段类型（避免过度使用 VARCHAR(255)）
4. 冷热数据分离（历史数据归档）
5. 读写分离减轻主库压力
6. 必要时分库分表
7. 定期 `OPTIMIZE TABLE` 回收碎片空间

---

## 📚 深入阅读

### 官方文档
- MySQL 8.0 EXPLAIN Output Format: https://dev.mysql.com/doc/refman/8.0/en/explain-output.html
- MySQL 8.0 InnoDB Buffer Pool: https://dev.mysql.com/doc/refman/8.0/en/innodb-buffer-pool.html
- MySQL 8.0 Optimization: https://dev.mysql.com/doc/refman/8.0/en/optimization.html

### 推荐书籍
- 《高性能 MySQL（第 4 版）》— 性能优化的圣经
- 《MySQL 实战 45 讲》— 丁奇（极客时间课程，实战性强）
- 《数据库索引设计与优化》— Tapio Lahdenmaki

### 工具
- Percona Toolkit: https://www.percona.com/software/database-tools/percona-toolkit
- pt-query-digest: 慢查询分析利器
- pt-online-schema-change: 在线 DDL 工具
- gh-ost: GitHub 开源的在线 DDL 工具

---

## ✅ 自检清单

### 理论检查点
- [ ] 能说出 EXPLAIN 每一列的含义和优化方向
- [ ] 能解释覆盖索引、索引下推、最左前缀的区别
- [ ] 能说出 innodb_flush_log_at_trx_commit 三种设置的区别
- [ ] 能解释读写分离的原理和主从延迟的解决方案
- [ ] 能说出分库分表的垂直拆分和水平拆分的区别

### 实操检查点
- [ ] 能使用 `pt-query-digest` 分析慢查询日志并给出优化建议
- [ ] 能通过 EXPLAIN 分析判断查询是否需要优化
- [ ] 能设计合理的联合索引并验证其效果
- [ ] 能根据业务场景调整 MySQL 关键配置参数
- [ ] 能使用分页优化技术解决深分页问题

### 能力验证标准
- [ ] 独立优化一个 P99 > 1s 的慢查询，使其降到 50ms 以内
- [ ] 为一个新业务表设计完整的索引方案
- [ ] 搭建并验证读写分离架构
