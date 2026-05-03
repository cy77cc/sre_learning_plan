# Day 49: 数据库交互

> 📅 日期：2026-05-03
> 📖 学习主题：Python 数据库交互（SQLite/MySQL/PostgreSQL, ORM vs 原生 SQL, 连接池, 事务, 迁移管理）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 46（Python 基础语法）, Day 47（Python 标准库）, Day 48（网络编程）

## 🎯 学习目标

- 掌握 Python DB-API 2.0 规范，理解数据库驱动的统一接口设计
- 能使用 SQLite、MySQL（pymysql）、PostgreSQL（psycopg2）进行 CRUD 操作
- 理解 ORM（SQLAlchemy）与原生 SQL 的取舍，能根据场景选择合适方案
- 掌握数据库连接池的原理与配置，避免连接泄漏
- 理解事务的 ACID 特性与隔离级别，能正确处理事务边界
- 能使用 Alembic 进行数据库迁移管理

---

## 📖 核心知识点

### 1. Python DB-API 2.0：统一的数据库接口

#### 1.1 为什么需要 DB-API？

Python 的数据库生态有一个重要的设计哲学：**用统一的接口访问不同的数据库**。这就是 PEP 249 定义的 DB-API 2.0 规范。

```
┌─────────────────────────────────────────────────────────────┐
│                    你的 SRE 工具代码                          │
├─────────────────────────────────────────────────────────────┤
│                    DB-API 2.0 接口层                         │
│  connect() → cursor → execute() → fetchall()/fetchone()    │
├──────────┬──────────────┬──────────────┬───────────────────┤
│ sqlite3  │ pymysql      │ psycopg2     │ cx_Oracle         │
│ (内置)    │ (MySQL)      │ (PostgreSQL) │ (Oracle)          │
├──────────┼──────────────┼──────────────┼───────────────────┤
│ SQLite   │ MySQL        │ PostgreSQL   │ Oracle            │
└──────────┴──────────────┴──────────────┴───────────────────┘
```

DB-API 2.0 定义了以下核心接口：

| 接口 | 作用 | SRE 场景 |
|------|------|----------|
| `connect()` | 创建数据库连接 | 初始化工具时连接数据库 |
| `connection.cursor()` | 创建游标 | 执行 SQL 语句 |
| `cursor.execute(sql, params)` | 执行 SQL | 查询配置、写入指标 |
| `cursor.fetchall()` | 获取所有结果 | 批量读取数据 |
| `cursor.fetchone()` | 获取单条结果 | 查询单个配置项 |
| `connection.commit()` | 提交事务 | 保存变更 |
| `connection.rollback()` | 回滚事务 | 出错时恢复 |
| `connection.close()` | 关闭连接 | 释放资源 |

#### 1.2 参数化查询：防止 SQL 注入

```python
#!/usr/bin/env python3
"""
DB-API 2.0 基础与参数化查询
SRE 场景：安全地查询和操作数据库

关键点：永远不要使用字符串拼接构造 SQL！
"""

import sqlite3


# ============================================================
# 错误示范：SQL 注入风险
# ============================================================
def get_user_unsafe(username: str):
    """这是错误的写法！存在 SQL 注入风险"""
    conn = sqlite3.connect("app.db")
    # 危险！如果 username = "'; DROP TABLE users; --"
    # 拼接后的 SQL: SELECT * FROM users WHERE name = ''; DROP TABLE users; --'
    cursor = conn.execute(f"SELECT * FROM users WHERE name = '{username}'")
    return cursor.fetchall()


# ============================================================
# 正确做法：参数化查询
# ============================================================
def get_user_safe(username: str):
    """安全的参数化查询"""
    conn = sqlite3.connect("app.db")
    # 使用 ? 占位符，驱动会自动处理转义
    cursor = conn.execute("SELECT * FROM users WHERE name = ?", (username,))
    return cursor.fetchall()


# ============================================================
# DB-API 2.0 完整示例：SRE 配置管理
# ============================================================
def demo_db_api():
    """
    使用 DB-API 2.0 操作 SQLite
    SRE 场景：管理服务配置、维护运维元数据
    """
    # connect() 返回 Connection 对象
    # SQLite 使用文件路径，其他数据库使用 DSN（Data Source Name）
    conn = sqlite3.connect(":memory:")  # 内存数据库用于演示
    conn.row_factory = sqlite3.Row  # 让查询结果像字典一样访问

    try:
        # 创建表
        conn.execute("""
            CREATE TABLE service_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL UNIQUE,
                environment TEXT NOT NULL DEFAULT 'production',
                replicas INTEGER NOT NULL DEFAULT 1,
                cpu_request TEXT NOT NULL DEFAULT '100m',
                memory_request TEXT NOT NULL DEFAULT '128Mi',
                enabled BOOLEAN NOT NULL DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 批量插入（使用 executemany）
        configs = [
            ("api-gateway", "production", 3, "500m", "512Mi", True),
            ("auth-service", "production", 2, "200m", "256Mi", True),
            ("notification", "staging", 1, "100m", "128Mi", True),
            ("batch-worker", "production", 1, "1000m", "2Gi", False),
        ]
        conn.executemany(
            "INSERT INTO service_config "
            "(service_name, environment, replicas, cpu_request, memory_request, enabled) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            configs,
        )
        conn.commit()

        # 查询：fetchall 返回所有结果
        cursor = conn.execute(
            "SELECT * FROM service_config WHERE environment = ? AND enabled = ?",
            ("production", True),
        )
        services = cursor.fetchall()
        print("=== Production Services ===")
        for svc in services:
            print(f"  {svc['service_name']}: {svc['replicas']} replicas, "
                  f"CPU={svc['cpu_request']}, Mem={svc['memory_request']}")

        # 查询：fetchone 返回单条结果
        cursor = conn.execute(
            "SELECT * FROM service_config WHERE service_name = ?",
            ("api-gateway",),
        )
        config = cursor.fetchone()
        if config:
            print(f"\napi-gateway config: replicas={config['replicas']}")

        # 更新
        conn.execute(
            "UPDATE service_config SET replicas = ? WHERE service_name = ?",
            (5, "api-gateway"),
        )
        conn.commit()
        print("\nUpdated api-gateway replicas to 5")

        # 删除
        conn.execute(
            "DELETE FROM service_config WHERE service_name = ?",
            ("batch-worker",),
        )
        conn.commit()
        print("Deleted batch-worker config")

        # 获取影响的行数
        cursor = conn.execute("SELECT changes()")
        print(f"Rows affected by last operation: {cursor.fetchone()[0]}")

    finally:
        # 永远要关闭连接
        conn.close()


if __name__ == "__main__":
    demo_db_api()
```

---

### 2. SQLite：SRE 工具的内置数据库

#### 2.1 为什么 SRE 需要 SQLite？

SQLite 是一个嵌入式数据库，不需要独立的数据库服务器。对于 SRE 工具来说，SQLite 是绝佳的选择：

```
┌────────────────────────────────────────────────────────────────┐
│                    SQLite vs 客户端-服务器数据库                   │
├─────────────────┬──────────────────┬───────────────────────────┤
│ 特性             │ SQLite           │ MySQL/PostgreSQL          │
├─────────────────┼──────────────────┼───────────────────────────┤
│ 部署方式         │ 嵌入式，零配置    │ 需要独立服务器              │
│ 数据存储         │ 单个文件          │ 服务器上的数据目录           │
│ 并发读           │ 支持              │ 支持                      │
│ 并发写           │ 串行(WAL模式下)   │ 支持                      │
│ 网络访问         │ 不支持            │ 支持                      │
│ 适用场景         │ 工具/脚本/测试    │ 生产应用                   │
│ SRE 推荐         │ 本地工具、缓存    │ 服务后端                   │
└─────────────────┴──────────────────┴───────────────────────────┘
```

#### 2.2 SQLite 高级用法

```python
#!/usr/bin/env python3
"""
SQLite 高级用法
SRE 场景：构建本地配置管理、指标缓存、离线数据存储
"""

import sqlite3
import json
import time
from contextlib import contextmanager
from datetime import datetime


@contextmanager
def get_db(db_path: str):
    """
    数据库连接的上下文管理器
    确保连接正确关闭，异常时自动回滚

    SRE 实践：使用 context manager 管理数据库连接生命周期
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # 启用 WAL 模式，提高并发读写性能
    # WAL = Write-Ahead Logging
    # 读操作不阻塞写操作，写操作不阻塞读操作
    conn.execute("PRAGMA journal_mode=WAL")
    # 设置忙等待超时（毫秒），避免 "database is locked" 错误
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class MetricsStore:
    """
    基于 SQLite 的监控指标存储
    SRE 场景：本地缓存监控数据，定期批量上报到 Prometheus/InfluxDB
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with get_db(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    tags TEXT DEFAULT '{}',
                    timestamp REAL NOT NULL,
                    reported BOOLEAN DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name_time
                ON metrics(metric_name, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_unreported
                ON metrics(reported) WHERE reported = 0
            """)

    def record(self, metric_name: str, value: float, tags: dict = None):
        """记录一条指标"""
        with get_db(self.db_path) as conn:
            conn.execute(
                "INSERT INTO metrics (metric_name, value, tags, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (metric_name, value, json.dumps(tags or {}), time.time()),
            )

    def get_unreported(self, limit: int = 1000) -> list[dict]:
        """获取未上报的指标"""
        with get_db(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM metrics WHERE reported = 0 "
                "ORDER BY timestamp LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_reported(self, ids: list[int]):
        """标记指标为已上报"""
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        with get_db(self.db_path) as conn:
            conn.execute(
                f"UPDATE metrics SET reported = 1 WHERE id IN ({placeholders})",
                ids,
            )

    def query(
        self,
        metric_name: str,
        start_time: float = None,
        end_time: float = None,
        aggregation: str = "avg",
    ) -> dict:
        """
        查询指标聚合值
        支持 avg, sum, min, max, count
        """
        valid_aggs = {"avg", "sum", "min", "max", "count"}
        if aggregation not in valid_aggs:
            raise ValueError(f"Invalid aggregation: {aggregation}")

        query = f"SELECT {aggregation}(value) as result FROM metrics WHERE metric_name = ?"
        params = [metric_name]

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        with get_db(self.db_path) as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return {
                "metric": metric_name,
                "aggregation": aggregation,
                "value": row["result"],
                "start_time": start_time,
                "end_time": end_time,
            }

    def cleanup(self, days: int = 7):
        """清理过期数据"""
        cutoff = time.time() - (days * 86400)
        with get_db(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM metrics WHERE timestamp < ?", (cutoff,)
            )
            return cursor.rowcount


class ConfigStore:
    """
    基于 SQLite 的配置管理
    SRE 场景：管理服务配置的版本历史、支持回滚
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with get_db(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    author TEXT NOT NULL,
                    comment TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_service
                ON config_history(service_name, version DESC)
            """)

    def update_config(
        self, service_name: str, config: dict, author: str, comment: str = ""
    ) -> int:
        """更新配置（创建新版本）"""
        with get_db(self.db_path) as conn:
            # 获取当前最新版本号
            cursor = conn.execute(
                "SELECT MAX(version) as max_ver FROM config_history "
                "WHERE service_name = ?",
                (service_name,),
            )
            row = cursor.fetchone()
            new_version = (row["max_ver"] or 0) + 1

            conn.execute(
                "INSERT INTO config_history "
                "(service_name, config_json, version, author, comment) "
                "VALUES (?, ?, ?, ?, ?)",
                (service_name, json.dumps(config, indent=2), new_version, author, comment),
            )
            return new_version

    def get_config(self, service_name: str, version: int = None) -> dict:
        """获取配置（默认获取最新版本）"""
        with get_db(self.db_path) as conn:
            if version:
                cursor = conn.execute(
                    "SELECT * FROM config_history "
                    "WHERE service_name = ? AND version = ?",
                    (service_name, version),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM config_history "
                    "WHERE service_name = ? ORDER BY version DESC LIMIT 1",
                    (service_name,),
                )
            row = cursor.fetchone()
            if row:
                return {
                    "service": row["service_name"],
                    "config": json.loads(row["config_json"]),
                    "version": row["version"],
                    "author": row["author"],
                    "comment": row["comment"],
                    "created_at": row["created_at"],
                }
            return None

    def get_history(self, service_name: str, limit: int = 10) -> list[dict]:
        """获取配置变更历史"""
        with get_db(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT version, author, comment, created_at FROM config_history "
                "WHERE service_name = ? ORDER BY version DESC LIMIT ?",
                (service_name, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def rollback(self, service_name: str, target_version: int, author: str) -> int:
        """回滚到指定版本（创建一个新版本，内容与目标版本相同）"""
        config = self.get_config(service_name, target_version)
        if not config:
            raise ValueError(f"Version {target_version} not found")
        return self.update_config(
            service_name,
            config["config"],
            author,
            f"Rollback to version {target_version}",
        )


def demo():
    """演示使用"""
    print("=== Metrics Store Demo ===")
    metrics = MetricsStore()
    metrics.record("cpu_usage", 75.5, {"host": "web-01"})
    metrics.record("cpu_usage", 82.3, {"host": "web-02"})
    metrics.record("memory_usage", 68.0, {"host": "web-01"})

    result = metrics.query("cpu_usage", aggregation="avg")
    print(f"Average CPU: {result['value']:.1f}%")

    unreported = metrics.get_unreported()
    print(f"Unreported metrics: {len(unreported)}")

    print("\n=== Config Store Demo ===")
    config = ConfigStore()
    config.update_config(
        "api-gateway",
        {"replicas": 3, "cpu": "500m", "memory": "512Mi"},
        "sre-engineer",
        "Initial deployment",
    )
    config.update_config(
        "api-gateway",
        {"replicas": 5, "cpu": "500m", "memory": "512Mi"},
        "sre-engineer",
        "Scale up for traffic surge",
    )

    current = config.get_config("api-gateway")
    print(f"Current config: {current['config']} (v{current['version']})")

    history = config.get_history("api-gateway")
    for h in history:
        print(f"  v{h['version']}: {h['comment']} by {h['author']}")


if __name__ == "__main__":
    demo()
```

---

### 3. MySQL 与 PostgreSQL

#### 3.1 MySQL 连接（pymysql）

```python
#!/usr/bin/env python3
"""
MySQL 连接与操作（使用 pymysql）
SRE 场景：查询业务数据库、执行运维数据迁移
"""

import pymysql
import pymysql.cursors
from contextlib import contextmanager


@contextmanager
def get_mysql_connection(
    host: str = "localhost",
    port: int = 3306,
    user: str = "root",
    password: str = "",
    database: str = "test",
    charset: str = "utf8mb4",
):
    """
    MySQL 连接的上下文管理器

    SRE 注意事项：
    1. 生产环境不要用 root，使用最小权限账号
    2. 连接信息不要硬编码，使用环境变量或密钥管理
    3. 设置合理的 connect_timeout 和 read_timeout
    """
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset=charset,
        cursorclass=pymysql.cursors.DictCursor,  # 返回字典格式
        connect_timeout=5,
        read_timeout=30,
        write_timeout=30,
        autocommit=False,  # 手动控制事务
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def demo_mysql():
    """MySQL 基础操作演示"""
    try:
        with get_mysql_connection(
            password="your_password",
            database="sre_db",
        ) as conn:
            with conn.cursor() as cursor:
                # 创建表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS incidents (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(500) NOT NULL,
                        severity ENUM('P0', 'P1', 'P2', 'P3') NOT NULL,
                        status ENUM('open', 'investigating', 'resolved') DEFAULT 'open',
                        assignee VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP NULL,
                        INDEX idx_severity (severity),
                        INDEX idx_status (status)
                    )
                """)

                # 插入故障记录
                cursor.execute(
                    "INSERT INTO incidents (title, severity, assignee) "
                    "VALUES (%s, %s, %s)",
                    ("API Gateway 502 errors", "P0", "sre-alice"),
                )
                incident_id = cursor.lastrowid
                print(f"Created incident #{incident_id}")

                # 查询未解决的 P0 故障
                cursor.execute(
                    "SELECT * FROM incidents "
                    "WHERE severity = %s AND status != %s "
                    "ORDER BY created_at DESC",
                    ("P0", "resolved"),
                )
                incidents = cursor.fetchall()
                print(f"Open P0 incidents: {len(incidents)}")

                # 更新故障状态
                cursor.execute(
                    "UPDATE incidents SET status = %s, resolved_at = NOW() "
                    "WHERE id = %s",
                    ("resolved", incident_id),
                )
                print(f"Resolved incident #{incident_id}")

    except pymysql.err.OperationalError as e:
        print(f"Connection failed: {e}")
        print("Make sure MySQL is running and credentials are correct")


if __name__ == "__main__":
    demo_mysql()
```

#### 3.2 PostgreSQL 连接（psycopg2）

```python
#!/usr/bin/env python3
"""
PostgreSQL 连接与操作（使用 psycopg2）
SRE 场景：查询业务数据库、执行复杂的数据分析

PostgreSQL vs MySQL 的 SRE 选择：
- PostgreSQL: 复杂查询、JSON 数据、GIS 数据、严格的数据完整性
- MySQL: 简单读写、高并发读、Web 应用
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager


@contextmanager
def get_pg_connection(
    host: str = "localhost",
    port: int = 5432,
    user: str = "postgres",
    password: str = "",
    database: str = "sre_db",
):
    """
    PostgreSQL 连接的上下文管理器

    psycopg2 的连接默认是 autocommit=False
    每个 SQL 语句都在一个隐式事务中
    """
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connect_timeout=5,
        options="-c statement_timeout=30000",  # SQL 超时 30 秒
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def demo_postgresql():
    """PostgreSQL 高级特性演示"""
    try:
        with get_pg_connection(password="your_password") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # PostgreSQL 的 JSON 支持（SRE 常用于存储配置和元数据）
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS service_registry (
                        id SERIAL PRIMARY KEY,
                        service_name VARCHAR(100) UNIQUE NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{}',
                        tags TEXT[] DEFAULT '{}',
                        health_check_url VARCHAR(500),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                # 插入服务注册信息（使用 JSONB）
                cur.execute(
                    """
                    INSERT INTO service_registry (service_name, metadata, tags, health_check_url)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (service_name) DO UPDATE SET
                        metadata = EXCLUDED.metadata,
                        tags = EXCLUDED.tags
                    """,
                    (
                        "api-gateway",
                        '{"version": "2.1.0", "team": "platform", "oncall": "sre-alice"}',
                        ["production", "critical", "public"],
                        "http://api-gateway:8080/healthz",
                    ),
                )

                # JSON 查询（PostgreSQL 的强大特性）
                cur.execute("""
                    SELECT service_name, metadata->>'version' as version,
                           metadata->>'team' as team
                    FROM service_registry
                    WHERE metadata->>'team' = %s
                    """,
                    ("platform",),
                )
                services = cur.fetchall()
                for svc in services:
                    print(f"  {svc['service_name']}: v{svc['version']} ({svc['team']})")

                # 数组查询
                cur.execute("""
                    SELECT service_name FROM service_registry
                    WHERE %s = ANY(tags)
                    """,
                    ("critical",),
                )
                critical_services = cur.fetchall()
                print(f"\nCritical services: {[s['service_name'] for s in critical_services]}")

    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    demo_postgresql()
```

---

### 4. 连接池：复用数据库连接

#### 4.1 为什么需要连接池？

```
没有连接池（每次操作新建连接）：

  请求 1 → [创建连接] → [执行SQL] → [关闭连接]
  请求 2 → [创建连接] → [执行SQL] → [关闭连接]
  请求 3 → [创建连接] → [执行SQL] → [关闭连接]
  ...

  问题：
  1. TCP 三次握手开销（每次 ~1ms）
  2. 数据库认证开销（MySQL 约 2-3ms）
  3. 连接资源浪费（文件描述符、内存）
  4. 高并发时连接数爆炸

有连接池：

  ┌─────────────────────────────────────────┐
  │              连接池 (pool_size=10)        │
  │  [conn1] [conn2] [conn3] ... [conn10]   │
  └────┬──────────┬──────────┬──────────────┘
       │          │          │
  请求 1      请求 2      请求 3
  (复用conn1) (复用conn2) (复用conn3)

  好处：
  1. 连接复用，减少握手和认证开销
  2. 控制最大连接数，保护数据库
  3. 自动管理连接生命周期
```

#### 4.2 SQLAlchemy 连接池

```python
#!/usr/bin/env python3
"""
SQLAlchemy 连接池配置
SRE 场景：生产级数据库连接管理
"""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool, NullPool, StaticPool


def create_db_engine(db_url: str, pool_type: str = "queue"):
    """
    创建带连接池的数据库引擎

    连接池类型选择：
    - QueuePool: 默认，适合大多数场景，支持多线程
    - NullPool: 不使用连接池，每次创建新连接，适合脚本
    - StaticPool: 固定单连接，适合测试

    SRE 场景：根据应用特性选择合适的连接池
    """
    if pool_type == "queue":
        engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=10,           # 常驻连接数
            max_overflow=20,        # 允许超出 pool_size 的临时连接数
            pool_timeout=30,        # 等待连接的超时时间（秒）
            pool_recycle=3600,      # 连接回收时间（秒），避免 MySQL 超时断开
            pool_pre_ping=True,     # 使用前 ping 检查连接是否存活
            echo=False,             # 不打印 SQL（生产环境关闭）
        )
    elif pool_type == "null":
        engine = create_engine(db_url, poolclass=NullPool)
    elif pool_type == "static":
        engine = create_engine(db_url, poolclass=StaticPool)
    else:
        raise ValueError(f"Unknown pool type: {pool_type}")

    return engine


def demo_connection_pool():
    """
    连接池使用演示
    使用 SQLite 演示（无需外部数据库）
    """
    engine = create_engine(
        "sqlite:///:memory:",
        pool_size=5,
        max_overflow=10,
        echo=False,
    )

    # 创建表
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE servers (
                id INTEGER PRIMARY KEY,
                hostname TEXT NOT NULL,
                ip TEXT NOT NULL,
                datacenter TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
        """))
        conn.commit()

    # 批量插入
    with engine.connect() as conn:
        servers = [
            {"hostname": "web-01", "ip": "10.0.1.1", "datacenter": "dc-east"},
            {"hostname": "web-02", "ip": "10.0.1.2", "datacenter": "dc-east"},
            {"hostname": "api-01", "ip": "10.0.2.1", "datacenter": "dc-west"},
        ]
        for server in servers:
            conn.execute(
                text("INSERT INTO servers (hostname, ip, datacenter) "
                     "VALUES (:hostname, :ip, :datacenter)"),
                server,
            )
        conn.commit()

    # 查询
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM servers WHERE datacenter = :dc"),
                              {"dc": "dc-east"})
        for row in result:
            print(f"  {row.hostname} ({row.ip}) - {row.datacenter}")

    # 查看连接池状态
    pool = engine.pool
    print(f"\nPool status:")
    print(f"  Size: {pool.size()}")
    print(f"  Checked out: {pool.checkedout()}")
    print(f"  Overflow: {pool.overflow()}")
    print(f"  Checked in: {pool.checkedin()}")

    engine.dispose()  # 关闭所有连接


if __name__ == "__main__":
    demo_connection_pool()
```

---

### 5. ORM vs 原生 SQL

#### 5.1 SQLAlchemy ORM

```python
#!/usr/bin/env python3
"""
SQLAlchemy ORM 使用
SRE 场景：结构化地管理运维数据模型

ORM 的优势：
1. 代码即文档：数据模型清晰定义在代码中
2. 防止 SQL 注入：参数化查询自动处理
3. 数据库无关：切换数据库不需要改代码
4. 迁移管理：配合 Alembic 自动管理 schema 变更

ORM 的劣势：
1. 性能开销：对象映射有额外开销
2. 复杂查询：不如原生 SQL 灵活
3. N+1 问题：容易产生隐式的额外查询

SRE 选择建议：
- CRUD 密集的操作 → ORM
- 复杂报表/分析 → 原生 SQL
- 简单脚本 → 原生 SQL
- 大型工具/平台 → ORM
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float
from sqlalchemy import DateTime, ForeignKey, func, text
from sqlalchemy.orm import (
    DeclarativeBase, Session, relationship, sessionmaker, Mapped, mapped_column
)
from datetime import datetime
from typing import Optional


class Base(DeclarativeBase):
    pass


class Server(Base):
    """服务器模型"""
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    hostname: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    datacenter: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="worker")
    cpu_cores: Mapped[int] = mapped_column(default=0)
    memory_gb: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # 关系
    metrics: Mapped[list["Metric"]] = relationship(back_populates="server")

    def __repr__(self):
        return f"<Server {self.hostname} ({self.ip_address})>"


class Metric(Base):
    """指标模型"""
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(default=func.now())

    server: Mapped["Server"] = relationship(back_populates="metrics")


def demo_orm():
    """ORM 完整演示"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        # 创建服务器
        servers = [
            Server(hostname="web-01", ip_address="10.0.1.1", datacenter="dc-east",
                   role="web", cpu_cores=8, memory_gb=32.0),
            Server(hostname="web-02", ip_address="10.0.1.2", datacenter="dc-east",
                   role="web", cpu_cores=8, memory_gb=32.0),
            Server(hostname="api-01", ip_address="10.0.2.1", datacenter="dc-west",
                   role="api", cpu_cores=16, memory_gb=64.0),
            Server(hostname="db-01", ip_address="10.0.3.1", datacenter="dc-east",
                   role="database", cpu_cores=32, memory_gb=128.0),
        ]
        session.add_all(servers)
        session.commit()

        # 查询所有 web 角色的服务器
        web_servers = session.query(Server).filter(Server.role == "web").all()
        print("Web servers:")
        for s in web_servers:
            print(f"  {s.hostname} ({s.ip_address}) - {s.cpu_cores} cores, {s.memory_gb}GB")

        # 复杂查询：按 datacenter 分组统计
        stats = (
            session.query(
                Server.datacenter,
                func.count(Server.id).label("count"),
                func.sum(Server.cpu_cores).label("total_cpu"),
                func.sum(Server.memory_gb).label("total_memory"),
            )
            .group_by(Server.datacenter)
            .all()
        )
        print("\nDatacenter stats:")
        for dc, count, cpu, mem in stats:
            print(f"  {dc}: {count} servers, {cpu} cores, {mem}GB RAM")

        # 添加指标数据
        metrics = [
            Metric(server_id=1, metric_name="cpu_usage", value=75.5),
            Metric(server_id=1, metric_name="memory_usage", value=68.0),
            Metric(server_id=2, metric_name="cpu_usage", value=82.3),
            Metric(server_id=2, metric_name="memory_usage", value=71.5),
        ]
        session.add_all(metrics)
        session.commit()

        # 联表查询：获取服务器及其指标
        results = (
            session.query(Server.hostname, Metric.metric_name, Metric.value)
            .join(Metric, Server.id == Metric.server_id)
            .filter(Metric.metric_name == "cpu_usage")
            .all()
        )
        print("\nCPU usage by server:")
        for hostname, metric, value in results:
            print(f"  {hostname}: {value}%")

        # 更新
        server = session.query(Server).filter(Server.hostname == "web-01").first()
        if server:
            server.status = "maintenance"
            session.commit()
            print(f"\nUpdated {server.hostname} status to {server.status}")

        # 使用原生 SQL（当 ORM 不够灵活时）
        result = session.execute(text("""
            SELECT datacenter, COUNT(*) as server_count,
                   AVG(cpu_cores) as avg_cpu
            FROM servers
            WHERE status = 'active'
            GROUP BY datacenter
            HAVING COUNT(*) > 1
        """))
        print("\nActive datacenters with >1 server (raw SQL):")
        for row in result:
            print(f"  {row.datacenter}: {row.server_count} servers, avg {row.avg_cpu:.0f} cores")


if __name__ == "__main__":
    demo_orm()
```

---

### 6. 事务管理

#### 6.1 ACID 与隔离级别

```
事务的 ACID 特性：
┌─────────────────────────────────────────────────────────────┐
│  A - Atomicity (原子性)                                      │
│      事务中的所有操作要么全部成功，要么全部回滚                  │
│      例：转账 = 扣款 + 入账，两步必须同时成功                   │
├─────────────────────────────────────────────────────────────┤
│  C - Consistency (一致性)                                     │
│      事务执行前后，数据库的完整性约束不变                        │
│      例：转账前后，两个账户的总金额不变                          │
├─────────────────────────────────────────────────────────────┤
│  I - Isolation (隔离性)                                      │
│      并发事务之间互不干扰                                      │
│      例：两个人同时修改同一行，结果是串行化的                     │
├─────────────────────────────────────────────────────────────┤
│  D - Durability (持久性)                                     │
│      事务提交后，数据永久保存                                   │
│      例：提交后即使数据库崩溃，数据也不会丢失                     │
└─────────────────────────────────────────────────────────────┘

SQL 隔离级别：
┌──────────────────┬──────────────┬──────────────┬───────────────┐
│ 隔离级别          │ 脏读         │ 不可重复读     │ 幻读          │
├──────────────────┼──────────────┼──────────────┼───────────────┤
│ READ UNCOMMITTED │ 可能          │ 可能          │ 可能          │
│ READ COMMITTED   │ 不会          │ 可能          │ 可能          │
│ REPEATABLE READ  │ 不会          │ 不会          │ 可能 (MySQL)  │
│ SERIALIZABLE     │ 不会          │ 不会          │ 不会          │
└──────────────────┴──────────────┴──────────────┴───────────────┘

SRE 选择建议：
- 大多数场景：READ COMMITTED（PostgreSQL 默认）
- 金融/支付：SERIALIZABLE 或 REPEATABLE READ
- 读多写少：READ COMMITTED + 合理的重试机制
```

#### 6.2 事务实践

```python
#!/usr/bin/env python3
"""
事务管理实践
SRE 场景：确保运维操作的原子性
"""

import sqlite3
from contextlib import contextmanager


@contextmanager
def transaction(conn: sqlite3.Connection):
    """
    事务上下文管理器
    自动提交或回滚
    """
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def deploy_service(conn: sqlite3.Connection, service_name: str, replicas: int):
    """
    部署服务：原子性地更新多个表

    SRE 场景：部署操作需要原子性
    - 更新部署记录
    - 更新服务注册
    - 记录审计日志

    如果任何一步失败，所有操作都应该回滚
    """
    with transaction(conn):
        # 1. 更新部署记录
        conn.execute(
            "UPDATE deployments SET status = 'completed', replicas = ? "
            "WHERE service_name = ? AND status = 'pending'",
            (replicas, service_name),
        )

        # 2. 更新服务注册
        conn.execute(
            "UPDATE service_registry SET desired_replicas = ?, "
            "last_deployed = CURRENT_TIMESTAMP WHERE service_name = ?",
            (replicas, service_name),
        )

        # 3. 记录审计日志
        conn.execute(
            "INSERT INTO audit_log (action, target, details) VALUES (?, ?, ?)",
            ("deploy", service_name, f"Scaled to {replicas} replicas"),
        )

        print(f"Deployed {service_name} with {replicas} replicas (atomic)")


def demo_transactions():
    """事务演示"""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE deployments (id INTEGER PRIMARY KEY, service_name TEXT, "
                 "status TEXT DEFAULT 'pending', replicas INTEGER)")
    conn.execute("CREATE TABLE service_registry (id INTEGER PRIMARY KEY, service_name TEXT, "
                 "desired_replicas INTEGER, last_deployed TIMESTAMP)")
    conn.execute("CREATE TABLE audit_log (id INTEGER PRIMARY KEY, action TEXT, "
                 "target TEXT, details TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

    # 插入测试数据
    conn.execute("INSERT INTO deployments (service_name, status, replicas) "
                 "VALUES ('api-gateway', 'pending', 3)")
    conn.execute("INSERT INTO service_registry (service_name, desired_replicas) "
                 "VALUES ('api-gateway', 3)")
    conn.commit()

    # 原子性部署
    deploy_service(conn, "api-gateway", 5)

    # 验证结果
    cursor = conn.execute("SELECT * FROM audit_log")
    for row in cursor.fetchall():
        print(f"Audit: {row[1]} {row[2]} - {row[3]}")

    conn.close()


if __name__ == "__main__":
    demo_transactions()
```

---

### 7. 数据库迁移管理（Alembic）

```python
#!/usr/bin/env python3
"""
Alembic 数据库迁移
SRE 场景：管理数据库 schema 变更，支持版本控制和回滚

为什么需要迁移管理？
1. 数据库 schema 需要版本控制（和代码一样）
2. 多环境（dev/staging/prod）需要一致的 schema
3. 需要支持回滚（出了问题能恢复）
4. 团队协作时需要同步 schema 变更

Alembic 工作流程：
1. 定义模型（SQLAlchemy ORM）
2. 生成迁移脚本：alembic revision --autogenerate
3. 应用迁移：alembic upgrade head
4. 回滚迁移：alembic downgrade -1
"""

# ============================================================
# Alembic 配置示例（实际使用时在 alembic.ini 和 env.py 中配置）
# ============================================================

# alembic.ini 示例配置
ALEMBIC_INI_TEMPLATE = """
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///sre_data.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""

# env.py 示例配置
ENV_PY_TEMPLATE = """
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入你的模型
from myapp.models import Base
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""

# 迁移脚本示例
MIGRATION_SCRIPT_TEMPLATE = """
\"\"\"Add service_config table

Revision ID: abc123
Revises:
Create Date: 2026-05-03 10:00:00.000000
\"\"\"

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    \"\"\"应用迁移\"\"\"
    op.create_table(
        'service_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('config_json', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_name', 'version'),
    )
    op.create_index('idx_config_service', 'service_config', ['service_name', 'version'])

def downgrade() -> None:
    \"\"\"回滚迁移\"\"\"
    op.drop_index('idx_config_service')
    op.drop_table('service_config')
"""


def print_alembic_workflow():
    """打印 Alembic 工作流程"""
    print("""
Alembic 数据库迁移工作流程：

1. 初始化 Alembic
   $ alembic init alembic

2. 配置数据库连接（alembic.ini 中的 sqlalchemy.url）

3. 定义模型（models.py）

4. 生成迁移脚本
   $ alembic revision --autogenerate -m "add service_config table"

5. 检查生成的迁移脚本（重要！自动检测可能有误）

6. 应用迁移
   $ alembic upgrade head        # 升级到最新版本
   $ alembic upgrade +1          # 升级一个版本

7. 回滚迁移
   $ alembic downgrade -1        # 回滚一个版本
   $ alembic downgrade base      # 回滚到初始状态

8. 查看迁移历史
   $ alembic history             # 查看所有迁移
   $ alembic current             # 查看当前版本

SRE 最佳实践：
- 迁移脚本必须经过 Code Review
- 在 staging 环境验证后再应用到 production
- 大表迁移要评估锁表时间
- 准备好回滚方案
- 迁移脚本要幂等（可重复执行）
    """)


if __name__ == "__main__":
    print_alembic_workflow()
```

---

### 8. SRE 实战案例

#### 8.1 故障排查：数据库连接泄漏

```
故障现象：
  服务运行一段时间后开始报 "too many connections" 错误
  数据库监控显示连接数持续增长，不释放

排查链路：
  1. 现象 → "too many connections"
  2. 诊断 → SHOW PROCESSLIST 查看连接状态
  3. 根因 → 代码中 try/except 块没有 finally 关闭连接
  4. 修复 → 使用 context manager 管理连接
  5. 预防 → 监控连接池使用率，设置连接上限

修复示例：
"""

# BAD: 连接泄漏
def query_broken(sql):
    conn = get_connection()
    try:
        cursor = conn.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error: {e}")
        return None
    # Bug: 没有 finally: conn.close()！
    # 如果发生异常，连接永远不会被关闭


# GOOD: 使用 context manager
def query_fixed(sql):
    with get_connection() as conn:
        try:
            cursor = conn.execute(sql)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error: {e}")
            return None


# BETTER: 使用连接池 + context manager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    "mysql+pymysql://user:pass@localhost/db",
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine)

def query_best(sql):
    with SessionLocal() as session:
        return session.execute(sql).fetchall()
```

#### 8.2 SRE 场景：配置数据库监控

```python
#!/usr/bin/env python3
"""
数据库监控脚本
SRE 场景：定期检查数据库健康状态，发现潜在问题
"""

import sqlite3
import time
import json
from datetime import datetime


def check_sqlite_health(db_path: str) -> dict:
    """
    SQLite 数据库健康检查

    检查项：
    1. 数据库文件大小
    2. WAL 文件大小
    3. 页面碎片化程度
    4. 查询性能
    """
    import os

    result = {
        "timestamp": datetime.now().isoformat(),
        "db_path": db_path,
        "status": "unknown",
        "checks": {},
    }

    # 检查文件大小
    try:
        db_size = os.path.getsize(db_path)
        wal_path = db_path + "-wal"
        wal_size = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0

        result["checks"]["db_size_mb"] = round(db_size / 1024 / 1024, 2)
        result["checks"]["wal_size_mb"] = round(wal_size / 1024 / 1024, 2)

        # WAL 文件过大可能是 checkpoint 问题
        if wal_size > 100 * 1024 * 1024:  # > 100MB
            result["checks"]["wal_warning"] = "WAL file is large, consider running PRAGMA wal_checkpoint"
    except OSError as e:
        result["checks"]["file_error"] = str(e)

    # 检查数据库完整性
    try:
        conn = sqlite3.connect(db_path)
        start = time.monotonic()
        cursor = conn.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        elapsed = (time.monotonic() - start) * 1000

        result["checks"]["integrity"] = integrity
        result["checks"]["integrity_check_ms"] = round(elapsed, 2)

        # 检查页面信息
        cursor = conn.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor = conn.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        cursor = conn.execute("PRAGMA freelist_count")
        freelist_count = cursor.fetchone()[0]

        result["checks"]["page_count"] = page_count
        result["checks"]["page_size"] = page_size
        result["checks"]["freelist_count"] = freelist_count
        result["checks"]["fragmentation_pct"] = round(
            freelist_count / page_count * 100, 2
        ) if page_count > 0 else 0

        # 查询性能测试
        start = time.monotonic()
        conn.execute("SELECT 1").fetchone()
        result["checks"]["query_latency_ms"] = round(
            (time.monotonic() - start) * 1000, 2
        )

        conn.close()
        result["status"] = "healthy" if integrity == "ok" else "unhealthy"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def main():
    # 创建测试数据库
    db_path = "/tmp/test_sre.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, data TEXT)")
    conn.executemany(
        "INSERT OR IGNORE INTO test (id, data) VALUES (?, ?)",
        [(i, f"data_{i}") for i in range(1000)],
    )
    conn.commit()
    conn.close()

    # 健康检查
    report = check_sqlite_health(db_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

---

## 💻 实战练习

### 练习 1：基础操作 -- 服务注册表

```python
#!/usr/bin/env python3
"""
练习 1：实现一个服务注册表
要求：
1. 使用 SQLite 存储服务信息
2. 支持注册、注销、查询、更新操作
3. 记录每次操作的审计日志
4. 使用事务保证原子性
"""

import sqlite3
import json
import time
from contextlib import contextmanager
from datetime import datetime


@contextmanager
def get_db(db_path: str = ":memory:"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class ServiceRegistry:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with get_db(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'active',
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    details TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_services_name ON services(name);
                CREATE INDEX IF NOT EXISTS idx_services_status ON services(status);
            """)

    def register(self, name: str, host: str, port: int, metadata: dict = None) -> dict:
        with get_db(self.db_path) as conn:
            conn.execute(
                "INSERT INTO services (name, host, port, metadata) VALUES (?, ?, ?, ?)",
                (name, host, port, json.dumps(metadata or {})),
            )
            conn.execute(
                "INSERT INTO audit_log (action, service_name, details) VALUES (?, ?, ?)",
                ("register", name, f"{host}:{port}"),
            )
            return {"name": name, "host": host, "port": port, "status": "active"}

    def deregister(self, name: str):
        with get_db(self.db_path) as conn:
            conn.execute("UPDATE services SET status = 'inactive' WHERE name = ?", (name,))
            conn.execute(
                "INSERT INTO audit_log (action, service_name) VALUES (?, ?)",
                ("deregister", name),
            )

    def heartbeat(self, name: str):
        with get_db(self.db_path) as conn:
            conn.execute(
                "UPDATE services SET last_heartbeat = CURRENT_TIMESTAMP WHERE name = ?",
                (name,),
            )

    def get_service(self, name: str) -> dict:
        with get_db(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM services WHERE name = ?", (name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_services(self, status: str = "active") -> list[dict]:
        with get_db(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM services WHERE status = ?", (status,))
            return [dict(row) for row in cursor.fetchall()]

    def get_audit_log(self, limit: int = 10) -> list[dict]:
        with get_db(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]


def main():
    registry = ServiceRegistry()

    # 注册服务
    registry.register("api-gateway", "10.0.1.1", 8080, {"version": "2.1.0", "team": "platform"})
    registry.register("auth-service", "10.0.1.2", 8081, {"version": "1.5.0", "team": "security"})
    registry.register("notification", "10.0.2.1", 8082, {"version": "3.0.0", "team": "platform"})

    # 列出所有活跃服务
    print("=== Active Services ===")
    for svc in registry.list_services():
        print(f"  {svc['name']}: {svc['host']}:{svc['port']} ({svc['status']})")

    # 注销一个服务
    registry.deregister("notification")
    print(f"\nAfter deregistering notification:")
    print(f"  Active: {len(registry.list_services())}")
    print(f"  Inactive: {len(registry.list_services('inactive'))}")

    # 审计日志
    print("\n=== Audit Log ===")
    for log in registry.get_audit_log():
        print(f"  [{log['action']}] {log['service_name']} - {log['details']}")


if __name__ == "__main__":
    main()
```

### 练习 2：进阶场景 -- 告警规则引擎

```python
#!/usr/bin/env python3
"""
练习 2：基于数据库的告警规则引擎
要求：
1. 定义告警规则（指标名、阈值、持续时间）
2. 评估指标是否触发告警
3. 记录告警历史
4. 支持告警静默（maintenance window）
"""

import sqlite3
import json
import time
from contextlib import contextmanager
from datetime import datetime, timedelta


@contextmanager
def get_db(db_path: str = ":memory:"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class AlertEngine:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with get_db(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    metric_name TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    duration_seconds INTEGER DEFAULT 0,
                    severity TEXT DEFAULT 'warning',
                    enabled BOOLEAN DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT DEFAULT 'firing',
                    fired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP NULL
                );
                CREATE TABLE IF NOT EXISTS silence_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    reason TEXT DEFAULT ''
                );
            """)

    def add_rule(
        self, name: str, metric_name: str, condition: str,
        threshold: float, duration: int = 0, severity: str = "warning"
    ):
        with get_db(self.db_path) as conn:
            conn.execute(
                "INSERT INTO alert_rules (name, metric_name, condition, threshold, "
                "duration_seconds, severity) VALUES (?, ?, ?, ?, ?, ?)",
                (name, metric_name, condition, threshold, duration, severity),
            )

    def evaluate(self, metric_name: str, value: float) -> list[dict]:
        """评估指标值，返回触发的告警"""
        alerts = []
        with get_db(self.db_path) as conn:
            rules = conn.execute(
                "SELECT * FROM alert_rules WHERE metric_name = ? AND enabled = 1",
                (metric_name,),
            ).fetchall()

            for rule in rules:
                # 检查是否在静默期
                silenced = conn.execute(
                    "SELECT COUNT(*) as cnt FROM silence_rules "
                    "WHERE rule_name = ? AND start_time <= ? AND end_time >= ?",
                    (rule["name"], datetime.now().isoformat(), datetime.now().isoformat()),
                ).fetchone()

                if silenced["cnt"] > 0:
                    continue

                # 评估条件
                triggered = False
                if rule["condition"] == ">" and value > rule["threshold"]:
                    triggered = True
                elif rule["condition"] == "<" and value < rule["threshold"]:
                    triggered = True
                elif rule["condition"] == ">=" and value >= rule["threshold"]:
                    triggered = True
                elif rule["condition"] == "<=" and value <= rule["threshold"]:
                    triggered = True

                if triggered:
                    conn.execute(
                        "INSERT INTO alert_history (rule_name, metric_value, threshold, severity) "
                        "VALUES (?, ?, ?, ?)",
                        (rule["name"], value, rule["threshold"], rule["severity"]),
                    )
                    alerts.append({
                        "rule": rule["name"],
                        "metric": metric_name,
                        "value": value,
                        "threshold": rule["threshold"],
                        "condition": rule["condition"],
                        "severity": rule["severity"],
                    })

        return alerts

    def get_active_alerts(self) -> list[dict]:
        with get_db(self.db_path) as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM alert_history WHERE status = 'firing' ORDER BY fired_at DESC"
            ).fetchall()]

    def add_silence(self, rule_name: str, duration_hours: int, reason: str = ""):
        with get_db(self.db_path) as conn:
            now = datetime.now()
            end = now + timedelta(hours=duration_hours)
            conn.execute(
                "INSERT INTO silence_rules (rule_name, start_time, end_time, reason) "
                "VALUES (?, ?, ?, ?)",
                (rule_name, now.isoformat(), end.isoformat(), reason),
            )


def main():
    engine = AlertEngine()

    # 添加告警规则
    engine.add_rule("high_cpu", "cpu_usage", ">", 80.0, severity="warning")
    engine.add_rule("critical_cpu", "cpu_usage", ">", 95.0, severity="critical")
    engine.add_rule("low_memory", "memory_available_gb", "<", 2.0, severity="warning")

    # 评估指标
    print("=== Evaluating CPU = 85% ===")
    alerts = engine.evaluate("cpu_usage", 85.0)
    for alert in alerts:
        print(f"  ALERT: {alert['rule']} - {alert['metric']}={alert['value']} "
              f"{alert['condition']} {alert['threshold']} ({alert['severity']})")

    print("\n=== Evaluating CPU = 97% ===")
    alerts = engine.evaluate("cpu_usage", 97.0)
    for alert in alerts:
        print(f"  ALERT: {alert['rule']} - {alert['metric']}={alert['value']} "
              f"{alert['condition']} {alert['threshold']} ({alert['severity']})")

    # 活跃告警
    print("\n=== Active Alerts ===")
    for alert in engine.get_active_alerts():
        print(f"  [{alert['severity']}] {alert['rule_name']}: "
              f"{alert['metric_value']} > {alert['threshold']}")


if __name__ == "__main__":
    main()
```

### 练习 3：故障排查挑战 -- 诊断慢查询

```python
#!/usr/bin/env python3
"""
练习 3：数据库慢查询诊断工具
挑战：找出代码中的性能问题并修复

症状：
  1. 查询操作随着数据量增加越来越慢
  2. 批量插入操作非常缓慢
  3. 某些查询返回重复数据
"""

import sqlite3
import time


def setup_test_db(conn):
    """创建测试数据"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            level TEXT NOT NULL,
            service TEXT NOT NULL,
            message TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            ts REAL NOT NULL
        );
    """)

    # 插入测试数据
    import random
    services = ["api", "web", "auth", "worker"]
    levels = ["INFO", "WARN", "ERROR", "DEBUG"]

    rows = []
    for i in range(10000):
        rows.append((
            time.time() - random.randint(0, 86400),
            random.choice(levels),
            random.choice(services),
            f"Log message {i}",
        ))
    conn.executemany("INSERT INTO logs (timestamp, level, service, message) VALUES (?, ?, ?, ?)", rows)

    rows = []
    for i in range(5000):
        rows.append((
            f"host-{random.randint(1, 10)}",
            random.choice(["cpu", "memory", "disk"]),
            random.uniform(0, 100),
            time.time() - random.randint(0, 3600),
        ))
    conn.executemany("INSERT INTO metrics (host, metric, value, ts) VALUES (?, ?, ?, ?)", rows)
    conn.commit()


# === 问题代码 ===

def find_errors_buggy(conn, service):
    """Bug 1: 没有索引，全表扫描"""
    cursor = conn.execute(
        f"SELECT * FROM logs WHERE service = '{service}' AND level = 'ERROR'"
    )
    return cursor.fetchall()


def get_latest_metrics_buggy(conn):
    """Bug 2: 子查询效率低"""
    cursor = conn.execute("""
        SELECT * FROM metrics WHERE ts = (
            SELECT MAX(ts) FROM metrics
        )
    """)
    return cursor.fetchall()


def batch_insert_buggy(conn, records):
    """Bug 3: 逐条插入，没有使用事务"""
    for record in records:
        conn.execute(
            "INSERT INTO metrics (host, metric, value, ts) VALUES (?, ?, ?, ?)",
            record,
        )
        conn.commit()  # 每条都 commit！


# === 修复后的代码 ===

def setup_indexes(conn):
    """创建索引"""
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_logs_service_level
        ON logs(service, level);
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp
        ON logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_metrics_host_metric_ts
        ON metrics(host, metric, ts DESC);
    """)
    conn.commit()


def find_errors_fixed(conn, service):
    """修复 1: 使用参数化查询 + 索引"""
    cursor = conn.execute(
        "SELECT * FROM logs WHERE service = ? AND level = 'ERROR'",
        (service,),
    )
    return cursor.fetchall()


def get_latest_metrics_fixed(conn):
    """修复 2: 使用窗口函数或 GROUP BY"""
    cursor = conn.execute("""
        SELECT m.* FROM metrics m
        INNER JOIN (
            SELECT host, metric, MAX(ts) as max_ts
            FROM metrics
            GROUP BY host, metric
        ) latest ON m.host = latest.host
        AND m.metric = latest.metric
        AND m.ts = latest.max_ts
    """)
    return cursor.fetchall()


def batch_insert_fixed(conn, records):
    """修复 3: 使用事务包裹批量插入"""
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.executemany(
            "INSERT INTO metrics (host, metric, value, ts) VALUES (?, ?, ?, ?)",
            records,
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def main():
    conn = sqlite3.connect(":memory:")
    setup_test_db(conn)

    # 测试查询性能（无索引）
    start = time.monotonic()
    find_errors_buggy(conn, "api")
    buggy_time = (time.monotonic() - start) * 1000

    # 创建索引
    setup_indexes(conn)

    # 测试查询性能（有索引）
    start = time.monotonic()
    find_errors_fixed(conn, "api")
    fixed_time = (time.monotonic() - start) * 1000

    print(f"Query without index: {buggy_time:.2f}ms")
    print(f"Query with index:    {fixed_time:.2f}ms")
    print(f"Speedup: {buggy_time / fixed_time:.1f}x")

    # 测试批量插入性能
    records = [(f"host-{i}", "cpu", 50.0, time.time()) for i in range(1000)]

    start = time.monotonic()
    conn2 = sqlite3.connect(":memory:")
    conn2.executescript("CREATE TABLE metrics (id INTEGER PRIMARY KEY, host TEXT, metric TEXT, value REAL, ts REAL)")
    batch_insert_buggy(conn2, records[:100])  # 只测试 100 条
    buggy_insert = (time.monotonic() - start) * 1000
    conn2.close()

    start = time.monotonic()
    conn3 = sqlite3.connect(":memory:")
    conn3.executescript("CREATE TABLE metrics (id INTEGER PRIMARY KEY, host TEXT, metric TEXT, value REAL, ts REAL)")
    batch_insert_fixed(conn3, records)
    fixed_insert = (time.monotonic() - start) * 1000
    conn3.close()

    print(f"\nBatch insert (100 rows, commit each): {buggy_insert:.2f}ms")
    print(f"Batch insert (1000 rows, single txn):  {fixed_insert:.2f}ms")

    conn.close()


if __name__ == "__main__":
    main()
```

---

## 🎯 面试题精选

### 题目 1：什么是 DB-API 2.0？它解决了什么问题？

**参考答案：**

DB-API 2.0 是 PEP 249 定义的 Python 数据库访问标准接口。它规定了所有数据库驱动必须实现的统一接口，包括 connect()、cursor、execute()、fetchone()/fetchall() 等方法。

它解决的核心问题是**数据库可移植性**：使用 DB-API 2.0 编写的代码可以在不同数据库之间切换，只需更改连接字符串和驱动导入。例如从 SQLite 切换到 PostgreSQL，代码逻辑基本不变。

### 题目 2：ORM 和原生 SQL 各自的优缺点？何时选择哪个？

**参考答案：**

| 维度 | ORM | 原生 SQL |
|------|-----|---------|
| 开发效率 | 高（自动映射） | 低（手写 SQL） |
| 性能 | 有开销（对象映射） | 最优 |
| 复杂查询 | 受限 | 完全灵活 |
| SQL 注入 | 自动防护 | 需手动防护 |
| 数据库迁移 | 自动生成 | 手动维护 |
| 学习曲线 | 需学 ORM API | 需学 SQL |

选择建议：
- **用 ORM**：CRUD 密集的应用、快速原型开发、团队 SQL 水平参差不齐
- **用原生 SQL**：复杂报表查询、性能敏感的核心路径、一次性数据脚本
- **混合使用**：大多数项目的最佳实践——ORM 做 CRUD，原生 SQL 做复杂查询

### 题目 3：什么是数据库连接池？为什么要使用它？

**参考答案：**

连接池是一组预先创建的数据库连接的缓存。当应用需要访问数据库时，从池中获取一个连接，使用后归还而不是关闭。

使用原因：
1. **性能**：避免每次请求都创建和销毁连接（TCP 握手 + 数据库认证约 5-10ms）
2. **资源控制**：限制最大连接数，防止打满数据库
3. **稳定性**：连接健康检查、自动重连
4. **并发控制**：当池满时，新请求排队等待而非创建新连接

关键参数：
- pool_size：常驻连接数（建议 5-20）
- max_overflow：允许的临时超出连接数
- pool_recycle：连接回收时间（避免数据库超时断开）
- pool_pre_ping：使用前检查连接存活

### 题目 4：解释数据库事务的隔离级别

**参考答案：**

隔离级别定义了并发事务之间的可见性规则：

- **READ UNCOMMITTED**：可以读到其他事务未提交的数据（脏读）
- **READ COMMITTED**：只能读到已提交的数据（PostgreSQL 默认）
- **REPEATABLE READ**：事务内多次读取结果一致（MySQL 默认）
- **SERIALIZABLE**：完全串行化，最安全但性能最差

SRE 实践建议：大多数场景使用 READ COMMITTED 即可。如果遇到"幻读"问题，先考虑用乐观锁（版本号）而非提高隔离级别。

### 题目 5：如何防止 SQL 注入？

**参考答案：**

防止 SQL 注入的核心原则：**永远不要将用户输入直接拼接到 SQL 字符串中**。

具体方法：
1. **参数化查询**：使用 `?` 或 `%s` 占位符
2. **ORM**：SQLAlchemy 等 ORM 自动处理参数转义
3. **输入验证**：在应用层验证输入格式
4. **最小权限**：数据库账号只授予必要的权限

```python
# 错误
cursor.execute(f"SELECT * FROM users WHERE name = '{username}'")

# 正确
cursor.execute("SELECT * FROM users WHERE name = ?", (username,))
```

### 题目 6：什么是 WAL（Write-Ahead Logging）？对 SQLite 有什么意义？

**参考答案：**

WAL 是一种日志机制：在修改数据之前，先将变更写入日志文件（WAL 文件）。这样读操作可以并发进行，不会被写操作阻塞。

对 SQLite 的意义：
- 默认的 journal 模式下，写操作会阻塞读操作
- WAL 模式下，读写可以并发，显著提升多线程场景的性能
- WAL 文件需要定期 checkpoint（合并到主数据库文件）

SRE 建议：使用 SQLite 的工具应默认启用 WAL 模式。

### 题目 7：SQLAlchemy 的 session 和 connection 有什么区别？

**参考答案：**

- **Connection**：底层的数据库连接，直接对应一个 TCP 连接到数据库
- **Session**：ORM 层的工作单元（Unit of Work），管理对象的生命周期、变更追踪、事务边界

Session 的关键特性：
1. **身份映射**：同一主键的对象在 Session 内是同一个 Python 对象
2. **延迟加载**：关联对象在访问时才真正查询
3. **变更追踪**：自动检测对象属性的修改
4. **事务管理**：Session.commit() 提交所有变更

SRE 建议：在 Web 应用中，每个请求使用一个 Session（scope）。在脚本中，使用 `with Session() as session:` 确保正确关闭。

### 题目 8：如何优化大批量数据插入的性能？

**参考答案：**

1. **使用事务包裹**：单个事务中插入所有数据，避免每条记录都 commit
2. **使用 executemany**：批量提交而不是逐条执行
3. **禁用索引**：插入前删除索引，插入后重建
4. **调整 SQLite 的 page_size 和 cache_size**
5. **使用 COPY 命令**（PostgreSQL）：比 INSERT 快 5-10 倍
6. **分批插入**：每 1000-10000 条一个事务，避免单个事务过大

```python
# 慢：逐条插入
for row in data:
    cursor.execute(sql, row)
    conn.commit()

# 快：批量插入
conn.execute("BEGIN")
cursor.executemany(sql, data)
conn.execute("COMMIT")
```

### 题目 9：什么是 Alembic？为什么需要数据库迁移工具？

**参考答案：**

Alembic 是 SQLAlchemy 作者开发的数据库迁移工具。它能自动检测模型变更并生成迁移脚本，支持升级和回滚。

为什么需要迁移工具：
1. **版本控制**：数据库 schema 变更有迹可循
2. **团队协作**：多人开发时同步 schema 变更
3. **环境一致性**：dev/staging/prod 使用相同的 schema
4. **安全回滚**：出问题时可以快速恢复
5. **自动化**：CI/CD 中自动执行迁移

SRE 最佳实践：
- 迁移脚本必须 Code Review
- 大表迁移评估锁表时间
- 先在 staging 验证
- 准备好回滚方案

### 题目 10：如何诊断和解决 "too many connections" 错误？

**参考答案：**

诊断步骤：
1. **查看数据库连接数**：`SHOW PROCESSLIST`（MySQL）或 `SELECT * FROM pg_stat_activity`（PostgreSQL）
2. **分析连接状态**：有多少是活跃查询？有多少是空闲？
3. **检查应用代码**：是否有连接泄漏（创建连接但不关闭）？
4. **检查连接池配置**：pool_size 和 max_overflow 是否合理？

解决方案：
1. **使用连接池**：控制最大连接数
2. **使用 context manager**：确保连接正确关闭
3. **设置 pool_recycle**：避免长时间空闲连接被数据库断开
4. **增加数据库最大连接数**：`max_connections`（临时方案）
5. **排查连接泄漏**：使用 `SHOW PROCESSLIST` 找出长时间空闲的连接

---

## 📚 深入阅读

### 官方文档

- [Python sqlite3 官方文档](https://docs.python.org/3/library/sqlite3.html)
- [Python DB-API 2.0 规范 (PEP 249)](https://peps.python.org/pep-0249/)
- [SQLAlchemy 官方文档](https://docs.sqlalchemy.org/)
- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [pymysql 文档](https://pymysql.readthedocs.io/)
- [psycopg2 文档](https://www.psycopg.org/docs/)

### 推荐书籍

- 《SQLAlchemy 权威指南》 -- Rick Copeland
- 《高性能 MySQL》 -- Baron Schwartz -- 第1-3章
- 《数据库系统内幕》 -- Alex Petrov -- 存储引擎与事务

### 技术博客

- [SQLite WAL 模式详解](https://www.sqlite.org/wal.html)
- [SQLAlchemy 连接池配置](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [PostgreSQL 与 MySQL 对比](https://www.postgresql.org/docs/current/compare.html)

---

## ✅ 自检清单

- [ ] 理解 DB-API 2.0 的核心接口（connect, cursor, execute, fetch）
- [ ] 能用参数化查询防止 SQL 注入
- [ ] 能使用 SQLite 构建本地工具的存储层
- [ ] 能使用 pymysql 连接 MySQL 并执行 CRUD 操作
- [ ] 能使用 psycopg2 连接 PostgreSQL 并使用 JSONB 等高级特性
- [ ] 理解 ORM 与原生 SQL 的取舍，能根据场景选择
- [ ] 能配置 SQLAlchemy 连接池（pool_size, max_overflow, pool_recycle）
- [ ] 理解事务的 ACID 特性和隔离级别
- [ ] 能使用 context manager 管理数据库连接生命周期
- [ ] 了解 Alembic 的基本使用流程
