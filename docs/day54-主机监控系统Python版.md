# Day 54: 主机监控系统 Python 版

> 📅 日期：2026-05-02
> 📖 学习主题：psutil 指标采集、指标存储、告警规则引擎、Web 仪表盘、systemd 集成
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 52 装饰器与高级技巧、Day 53 面向对象设计、Day 50 并发编程

## 🎯 学习目标

完成 Day 54 的学习后，你应该能够：
- 使用 psutil 采集完整的主机指标（CPU、内存、磁盘、网络、进程）
- 实现带 TTL 和自动清理的指标存储层
- 构建支持复合条件的告警规则引擎
- 开发实时 Web 仪表盘展示指标和告警
- 编写 systemd 服务文件，将监控系统部署为系统服务
- 理解主机监控系统的完整数据流：采集 → 存储 → 告警 → 展示

---

## 📖 核心知识点

### 1. 系统架构设计

```
完整的主机监控系统数据流：

┌─────────────────────────────────────────────────────────────────┐
│                        主机监控系统                               │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  采集层   │ →  │  存储层   │ →  │  告警层   │ →  │  展示层   │  │
│  │ Collector │    │  Store   │    │  Alerter │    │Dashboard │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  psutil  │    │  SQLite  │    │ 规则引擎  │    │ Flask/   │  │
│  │  系统调用 │    │  内存缓存 │    │ 告警渠道  │    │ HTTP API │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    systemd 服务管理                        │   │
│  │  开机自启 → 进程守护 → 日志管理 → 优雅停止                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. psutil 指标采集详解

#### 2.1 psutil 核心 API

```python
import psutil
import time
from typing import Dict, List, Any


def collect_cpu() -> Dict[str, float]:
    """CPU 指标采集。

    返回指标：
    - cpu_percent: 总体 CPU 使用率
    - cpu_user: 用户态 CPU 时间占比
    - cpu_system: 内核态 CPU 时间占比
    - cpu_iowait: I/O 等待时间占比
    - cpu_count_logical: 逻辑 CPU 数
    - cpu_count_physical: 物理 CPU 数
    - cpu_freq_mhz: 当前 CPU 频率
    """
    cpu_times_percent = psutil.cpu_times_percent(interval=1)
    cpu_freq = psutil.cpu_freq()

    return {
        "cpu_percent": psutil.cpu_percent(interval=0),
        "cpu_user": cpu_times_percent.user,
        "cpu_system": cpu_times_percent.system,
        "cpu_iowait": cpu_times_percent.iowait if hasattr(cpu_times_percent, 'iowait') else 0,
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "cpu_freq_mhz": cpu_freq.current if cpu_freq else 0,
    }


def collect_memory() -> Dict[str, float]:
    """内存指标采集。

    返回指标：
    - mem_total_gb: 总内存
    - mem_available_gb: 可用内存
    - mem_used_gb: 已用内存
    - mem_percent: 使用率
    - swap_total_gb: 交换区总量
    - swap_used_gb: 交换区已用
    - swap_percent: 交换区使用率
    """
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "mem_total_gb": round(mem.total / (1024 ** 3), 2),
        "mem_available_gb": round(mem.available / (1024 ** 3), 2),
        "mem_used_gb": round(mem.used / (1024 ** 3), 2),
        "mem_percent": mem.percent,
        "swap_total_gb": round(swap.total / (1024 ** 3), 2),
        "swap_used_gb": round(swap.used / (1024 ** 3), 2),
        "swap_percent": swap.percent,
    }


def collect_disk() -> Dict[str, float]:
    """磁盘指标采集。

    返回每个挂载点的使用情况和 I/O 计数器。
    """
    metrics = {}

    # 分区使用情况
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            prefix = f"disk_{part.mountpoint.replace('/', '_').strip('_') or 'root'}"
            metrics[f"{prefix}_total_gb"] = round(usage.total / (1024 ** 3), 2)
            metrics[f"{prefix}_used_gb"] = round(usage.used / (1024 ** 3), 2)
            metrics[f"{prefix}_free_gb"] = round(usage.free / (1024 ** 3), 2)
            metrics[f"{prefix}_percent"] = usage.percent
        except PermissionError:
            pass

    # I/O 计数器
    io = psutil.disk_io_counters()
    if io:
        metrics["disk_read_bytes"] = io.read_bytes
        metrics["disk_write_bytes"] = io.write_bytes
        metrics["disk_read_count"] = io.read_count
        metrics["disk_write_count"] = io.write_count

    return metrics


def collect_network() -> Dict[str, float]:
    """网络指标采集。

    返回指标：
    - net_bytes_sent: 发送字节数
    - net_bytes_recv: 接收字节数
    - net_packets_sent: 发送包数
    - net_packets_recv: 接收包数
    - net_errin: 接收错误数
    - net_errout: 发送错误数
    - net_dropin: 接收丢包数
    - net_dropout: 发送丢包数
    """
    io = psutil.net_io_counters()
    return {
        "net_bytes_sent": io.bytes_sent,
        "net_bytes_recv": io.bytes_recv,
        "net_packets_sent": io.packets_sent,
        "net_packets_recv": io.packets_recv,
        "net_errin": io.errin,
        "net_errout": io.errout,
        "net_dropin": io.dropin,
        "net_dropout": io.dropout,
    }


def collect_load() -> Dict[str, float]:
    """系统负载指标。

    返回 1 分钟、5 分钟、15 分钟的平均负载。
    """
    load1, load5, load15 = psutil.getloadavg()
    cpu_count = psutil.cpu_count(logical=True)
    return {
        "load_1min": load1,
        "load_5min": load5,
        "load_15min": load15,
        "load_1min_per_cpu": round(load1 / cpu_count, 2) if cpu_count else 0,
    }


def collect_processes(top_n: int = 10) -> Dict[str, Any]:
    """进程指标采集。

    返回 CPU 和内存占用最高的进程。
    """
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 按 CPU 排序
    top_cpu = sorted(procs, key=lambda p: p.get("cpu_percent", 0) or 0, reverse=True)[:top_n]
    # 按内存排序
    top_mem = sorted(procs, key=lambda p: p.get("memory_percent", 0) or 0, reverse=True)[:top_n]

    return {
        "process_count": len(procs),
        "top_cpu": top_cpu,
        "top_mem": top_mem,
    }


def collect_all() -> Dict[str, Any]:
    """采集所有指标。"""
    metrics = {}
    metrics.update(collect_cpu())
    metrics.update(collect_memory())
    metrics.update(collect_disk())
    metrics.update(collect_network())
    metrics.update(collect_load())
    metrics["_timestamp"] = time.time()
    metrics["_processes"] = collect_processes()
    return metrics
```

#### 2.2 差分指标计算

```python
import time
from typing import Dict, Optional


class DeltaCalculator:
    """差分指标计算器。

    某些指标（如磁盘 I/O、网络流量）是累计值，
    需要计算两次采集之间的差值得到速率。

    SRE 场景：
    - 网络流量速率（bytes/s）
    - 磁盘 I/O 速率（bytes/s）
    - 磁盘 IOPS（operations/s）
    """

    def __init__(self):
        self._previous: Dict[str, tuple] = {}  # {name: (timestamp, value)}

    def calculate(self, name: str, value: float) -> Optional[float]:
        """计算差分值。返回 None 如果没有前一次数据。"""
        now = time.time()

        if name in self._previous:
            prev_time, prev_value = self._previous[name]
            dt = now - prev_time
            if dt > 0:
                delta = (value - prev_value) / dt
                self._previous[name] = (now, value)
                return round(delta, 2)

        self._previous[name] = (now, value)
        return None

    def calculate_rates(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """批量计算差分指标。"""
        rate_metrics = {}
        delta_fields = [
            "net_bytes_sent", "net_bytes_recv",
            "disk_read_bytes", "disk_write_bytes",
            "disk_read_count", "disk_write_count",
        ]
        for field in delta_fields:
            if field in metrics:
                rate = self.calculate(field, metrics[field])
                if rate is not None:
                    rate_metrics[f"{field}_per_sec"] = rate
        return rate_metrics
```

---

### 3. 指标存储层

#### 3.1 SQLite 存储实现

```python
import sqlite3
import time
import threading
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta


class MetricsStore:
    """SQLite 指标存储。

    特性：
    - 自动建表和索引
    - 批量写入优化
    - 数据自动过期清理
    - 线程安全

    存储架构：
    ┌─────────────────────────────────────────────┐
    │               metrics 表                     │
    │  id | name | value | timestamp | labels_json │
    ├─────────────────────────────────────────────┤
    │  1  | cpu  | 85.2  | 1714723200| {}         │
    │  2  | mem  | 72.1  | 1714723200| {}         │
    │  ...                                        │
    └─────────────────────────────────────────────┘
    索引: idx_name_ts (name, timestamp)
    """

    def __init__(self, db_path: str = "metrics.db",
                 retention_days: int = 7):
        self.db_path = db_path
        self.retention_days = retention_days
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接。"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10
            )
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self):
        """初始化数据库表和索引。"""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp REAL NOT NULL,
                labels_json TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_name_ts
                ON metrics(name, timestamp);

            CREATE INDEX IF NOT EXISTS idx_timestamp
                ON metrics(timestamp);

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp REAL NOT NULL,
                resolved INTEGER DEFAULT 0,
                resolved_at REAL
            );

            CREATE INDEX IF NOT EXISTS idx_alerts_ts
                ON alerts(timestamp);

            CREATE INDEX IF NOT EXISTS idx_alerts_resolved
                ON alerts(resolved);
        """)
        conn.commit()

    def save(self, name: str, value: float,
             timestamp: Optional[float] = None,
             labels: Optional[Dict] = None) -> None:
        """保存单条指标。"""
        import json
        ts = timestamp or time.time()
        labels_json = json.dumps(labels or {})
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO metrics (name, value, timestamp, labels_json) "
            "VALUES (?, ?, ?, ?)",
            (name, value, ts, labels_json)
        )
        conn.commit()

    def save_batch(self, metrics: Dict[str, float],
                   timestamp: Optional[float] = None) -> None:
        """批量保存指标（性能优化）。"""
        import json
        ts = timestamp or time.time()
        rows = [
            (name, value, ts, '{}')
            for name, value in metrics.items()
            if isinstance(value, (int, float)) and not name.startswith('_')
        ]
        conn = self._get_conn()
        conn.executemany(
            "INSERT INTO metrics (name, value, timestamp, labels_json) "
            "VALUES (?, ?, ?, ?)",
            rows
        )
        conn.commit()

    def query(self, name: str, start: float, end: float,
              limit: int = 1000) -> List[Tuple]:
        """查询指标数据。"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT timestamp, value FROM metrics "
            "WHERE name = ? AND timestamp BETWEEN ? AND ? "
            "ORDER BY timestamp ASC LIMIT ?",
            (name, start, end, limit)
        ).fetchall()
        return rows

    def get_latest(self, name: str) -> Optional[Tuple]:
        """获取最新一条数据。"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT timestamp, value FROM metrics "
            "WHERE name = ? ORDER BY timestamp DESC LIMIT 1",
            (name,)
        ).fetchone()
        return row

    def get_all_latest(self) -> Dict[str, float]:
        """获取所有指标的最新值。"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT name, value, timestamp FROM metrics "
            "WHERE id IN (SELECT MAX(id) FROM metrics GROUP BY name)"
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def aggregate(self, name: str, start: float, end: float,
                  func: str = "avg") -> Optional[float]:
        """聚合查询（avg, max, min, count）。"""
        conn = self._get_conn()
        agg_funcs = {
            "avg": "AVG(value)",
            "max": "MAX(value)",
            "min": "MIN(value)",
            "count": "COUNT(*)",
            "sum": "SUM(value)",
        }
        sql_func = agg_funcs.get(func, "AVG(value)")
        row = conn.execute(
            f"SELECT {sql_func} FROM metrics "
            "WHERE name = ? AND timestamp BETWEEN ? AND ?",
            (name, start, end)
        ).fetchone()
        return row[0] if row else None

    def save_alert(self, rule_name: str, metric_name: str,
                   value: float, threshold: float,
                   severity: str, message: str) -> int:
        """保存告警记录。"""
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO alerts (rule_name, metric_name, value, threshold, "
            "severity, message, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rule_name, metric_name, value, threshold, severity,
             message, time.time())
        )
        conn.commit()
        return cursor.lastrowid

    def get_active_alerts(self) -> List[Dict]:
        """获取未解决的告警。"""
        import json
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, rule_name, metric_name, value, threshold, "
            "severity, message, timestamp FROM alerts "
            "WHERE resolved = 0 ORDER BY timestamp DESC"
        ).fetchall()
        return [
            {
                "id": r[0], "rule_name": r[1], "metric_name": r[2],
                "value": r[3], "threshold": r[4], "severity": r[5],
                "message": r[6], "timestamp": r[7]
            }
            for r in rows
        ]

    def cleanup(self) -> int:
        """清理过期数据。"""
        cutoff = time.time() - (self.retention_days * 86400)
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM metrics WHERE timestamp < ?", (cutoff,)
        )
        conn.commit()
        deleted = cursor.rowcount
        if deleted:
            # 回收空间
            conn.execute("VACUUM")
        return deleted

    def get_metric_names(self) -> List[str]:
        """获取所有指标名称。"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT DISTINCT name FROM metrics ORDER BY name"
        ).fetchall()
        return [row[0] for row in rows]
```

#### 3.2 内存缓存层

```python
import time
import threading
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class MemoryCache:
    """内存指标缓存。

    用于存储最近 N 分钟的指标数据，支持快速查询，
    避免频繁查询 SQLite。

    架构：
    ┌─────────────────────────────────────────┐
    │           MemoryCache                    │
    │  ┌─────────────────────────────────┐    │
    │  │ cpu_percent: [v1, v2, v3, ...]  │    │
    │  │ mem_percent: [v1, v2, v3, ...]  │    │
    │  │ disk_percent: [v1, v2, v3, ...] │    │
    │  └─────────────────────────────────┘    │
    │  每个指标保留最近 max_points 个数据点      │
    │  自动淘汰最旧的数据                       │
    └─────────────────────────────────────────┘
    """

    def __init__(self, max_points: int = 360):
        self.max_points = max_points  # 默认保留 6 小时（每分钟一个点）
        self._data: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        self._lock = threading.Lock()

    def put(self, name: str, value: float, timestamp: Optional[float] = None):
        """添加数据点。"""
        ts = timestamp or time.time()
        with self._lock:
            self._data[name].append((ts, value))
            # 超过最大点数，淘汰最旧的
            if len(self._data[name]) > self.max_points:
                self._data[name] = self._data[name][-self.max_points:]

    def put_batch(self, metrics: Dict[str, float], timestamp: Optional[float] = None):
        """批量添加数据点。"""
        ts = timestamp or time.time()
        for name, value in metrics.items():
            if isinstance(value, (int, float)) and not name.startswith('_'):
                self.put(name, value, ts)

    def get(self, name: str, last_n: Optional[int] = None) -> List[Tuple[float, float]]:
        """获取数据点。"""
        with self._lock:
            data = self._data.get(name, [])
            if last_n:
                return data[-last_n:]
            return list(data)

    def get_latest(self, name: str) -> Optional[Tuple[float, float]]:
        """获取最新数据点。"""
        with self._lock:
            data = self._data.get(name, [])
            return data[-1] if data else None

    def get_all_latest(self) -> Dict[str, float]:
        """获取所有指标的最新值。"""
        result = {}
        with self._lock:
            for name, points in self._data.items():
                if points:
                    result[name] = points[-1][1]
        return result

    def aggregate(self, name: str, window_seconds: float,
                  func: str = "avg") -> Optional[float]:
        """在时间窗口内聚合。"""
        cutoff = time.time() - window_seconds
        with self._lock:
            data = self._data.get(name, [])
            recent = [v for t, v in data if t >= cutoff]

        if not recent:
            return None

        if func == "avg":
            return sum(recent) / len(recent)
        elif func == "max":
            return max(recent)
        elif func == "min":
            return min(recent)
        elif func == "count":
            return len(recent)
        return recent[-1]
```

---

### 4. 告警规则引擎

```python
import time
import logging
import threading
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum, auto

logger = logging.getLogger(__name__)


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ConditionOp(Enum):
    GT = ">"       # 大于
    LT = "<"       # 小于
    GTE = ">="     # 大于等于
    LTE = "<="     # 小于等于
    EQ = "=="      # 等于
    NEQ = "!="     # 不等于


@dataclass
class AlertRule:
    """告警规则。

    属性：
    - name: 规则名称
    - metric: 监控的指标名
    - operator: 比较运算符
    - threshold: 阈值
    - severity: 告警级别
    - duration: 持续时间（秒），0 表示立即触发
    - cooldown: 告警冷却时间（秒），避免重复告警
    - message: 告警消息模板
    """
    name: str
    metric: str
    operator: str
    threshold: float
    severity: Severity = Severity.WARNING
    duration: int = 0
    cooldown: int = 300
    message: str = ""
    enabled: bool = True

    def evaluate(self, value: float) -> bool:
        """评估条件。"""
        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: abs(a - b) < 0.001,
            "!=": lambda a, b: abs(a - b) >= 0.001,
        }
        op_func = ops.get(self.operator)
        if not op_func:
            logger.error(f"未知运算符: {self.operator}")
            return False
        return op_func(value, self.threshold)


@dataclass
class Alert:
    """告警实例。"""
    rule_name: str
    metric_name: str
    value: float
    threshold: float
    severity: Severity
    message: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False


class AlertEngine:
    """告警引擎。

    职责：
    1. 管理告警规则
    2. 评估指标是否触发告警
    3. 处理告警冷却和去重
    4. 通知告警渠道

    架构：
    ┌──────────────────────────────────────────────────┐
    │                   AlertEngine                     │
    │                                                   │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
    │  │ Rule     │  │ History  │  │ Notifier │       │
    │  │ Registry │  │ Tracker  │  │ Registry │       │
    │  └──────────┘  └──────────┘  └──────────┘       │
    │       │              │              │             │
    │       ▼              ▼              ▼             │
    │  存储规则列表    记录触发历史    管理通知渠道      │
    │  规则启用/禁用   冷却期检查      多渠道分发        │
    └──────────────────────────────────────────────────┘
    """

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._history: Dict[str, float] = {}  # {rule_name: last_alert_time}
        self._state: Dict[str, List[Tuple[float, float]]] = {}  # 持续时间追踪
        self._notifiers: List[Callable] = []
        self._lock = threading.Lock()
        self._active_alerts: Dict[str, Alert] = {}

    def add_rule(self, rule: AlertRule):
        """添加告警规则。"""
        with self._lock:
            self._rules[rule.name] = rule
        logger.info(f"添加规则: {rule.name} ({rule.metric} {rule.operator} {rule.threshold})")

    def remove_rule(self, name: str):
        """移除告警规则。"""
        with self._lock:
            self._rules.pop(name, None)

    def add_notifier(self, notifier: Callable):
        """添加通知渠道。"""
        self._notifiers.append(notifier)

    def evaluate(self, metrics: Dict[str, float]) -> List[Alert]:
        """评估所有规则，返回触发的告警。"""
        triggered = []
        now = time.time()

        with self._lock:
            rules = list(self._rules.values())

        for rule in rules:
            if not rule.enabled:
                continue
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]

            if not rule.evaluate(value):
                # 条件不满足，清除状态
                self._state.pop(rule.name, None)
                # 如果之前有活跃告警，标记为已解决
                if rule.name in self._active_alerts:
                    self._active_alerts[rule.name].resolved = True
                    del self._active_alerts[rule.name]
                continue

            # 条件满足，记录状态
            if rule.name not in self._state:
                self._state[rule.name] = []
            self._state[rule.name].append((now, value))

            # 检查持续时间
            state_entries = self._state[rule.name]
            if rule.duration > 0:
                # 清理过期数据
                cutoff = now - rule.duration
                state_entries[:] = [(t, v) for t, v in state_entries if t >= cutoff]
                if len(state_entries) < 2:
                    continue  # 数据不足，不触发

            # 检查冷却期
            last_alert_time = self._history.get(rule.name, 0)
            if now - last_alert_time < rule.cooldown:
                continue  # 冷却期内，不重复告警

            # 触发告警
            message = rule.message or f"{rule.metric} {rule.operator} {rule.threshold}"
            alert = Alert(
                rule_name=rule.name,
                metric_name=rule.metric,
                value=value,
                threshold=rule.threshold,
                severity=rule.severity,
                message=f"{message} (当前值: {value:.2f})",
            )
            triggered.append(alert)
            self._history[rule.name] = now
            self._active_alerts[rule.name] = alert

        # 发送通知
        if triggered:
            self._notify(triggered)

        return triggered

    def _notify(self, alerts: List[Alert]):
        """发送告警通知。"""
        for notifier in self._notifiers:
            for alert in alerts:
                try:
                    notifier(alert)
                except Exception as e:
                    logger.error(f"通知发送失败: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """获取当前活跃的告警。"""
        with self._lock:
            return list(self._active_alerts.values())

    def get_rules(self) -> List[AlertRule]:
        """获取所有规则。"""
        with self._lock:
            return list(self._rules.values())


# 通知渠道实现
def log_notifier(alert: Alert):
    """日志通知。"""
    level_map = {
        Severity.INFO: logging.INFO,
        Severity.WARNING: logging.WARNING,
        Severity.CRITICAL: logging.CRITICAL,
    }
    level = level_map.get(alert.severity, logging.WARNING)
    logger.log(level, f"[{alert.severity.value.upper()}] {alert.message}")


def webhook_notifier(url: str) -> Callable:
    """Webhook 通知工厂。"""
    def notifier(alert: Alert):
        import requests
        payload = {
            "rule": alert.rule_name,
            "metric": alert.metric_name,
            "value": alert.value,
            "threshold": alert.threshold,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp,
        }
        requests.post(url, json=payload, timeout=5)
    return notifier
```

---

### 5. Web 仪表盘

```python
#!/usr/bin/env python3
"""监控系统 Web 仪表盘。

使用 Flask 提供 HTTP API 和简单前端。

API 端点：
- GET /api/metrics          — 获取所有最新指标
- GET /api/metrics/<name>   — 获取指定指标的历史数据
- GET /api/alerts           — 获取活跃告警
- GET /api/rules            — 获取告警规则
- GET /                     — 仪表盘页面
"""

import json
import time
import logging
from typing import Dict
from datetime import datetime

# Flask 会在运行时导入，这里先定义接口
logger = logging.getLogger(__name__)


def create_app(store, cache, alert_engine, collector):
    """创建 Flask 应用。

    参数：
    - store: MetricsStore 实例
    - cache: MemoryCache 实例
    - alert_engine: AlertEngine 实例
    - collector: 指标采集器
    """
    from flask import Flask, jsonify, request, render_template_string

    app = Flask(__name__)

    # ──────────────────────────────────────────
    # HTML 模板（内嵌，无需外部文件）
    # ──────────────────────────────────────────
    DASHBOARD_HTML = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SRE 主机监控</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px; }
            h1 { color: #0f3460; border-bottom: 2px solid #0f3460; padding-bottom: 10px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }
            .card { background: #16213e; border-radius: 8px; padding: 15px; border-left: 4px solid #0f3460; }
            .card.critical { border-left-color: #e74c3c; }
            .card.warning { border-left-color: #f39c12; }
            .card.healthy { border-left-color: #2ecc71; }
            .metric-name { font-size: 14px; color: #888; }
            .metric-value { font-size: 28px; font-weight: bold; }
            .metric-unit { font-size: 14px; color: #888; }
            .alert { background: #2c1a1a; border-left-color: #e74c3c; margin: 5px 0; }
            .alert.warning { background: #2c2a1a; border-left-color: #f39c12; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #333; }
            th { color: #0f3460; }
            .section { margin-top: 30px; }
            .section h2 { color: #e94560; }
            .timestamp { font-size: 12px; color: #666; }
        </style>
    </head>
    <body>
        <h1>SRE 主机监控仪表盘</h1>
        <p class="timestamp">最后更新: {{ timestamp }}</p>

        <div class="section">
            <h2>核心指标</h2>
            <div class="grid">
                {% for name, value in metrics.items() %}
                {% if not name.startswith('_') %}
                <div class="card {{ 'critical' if value > 90 else ('warning' if value > 70 else 'healthy') }}">
                    <div class="metric-name">{{ name }}</div>
                    <div class="metric-value">
                        {{ "%.2f"|format(value) if value is number else value }}
                    </div>
                </div>
                {% endif %}
                {% endfor %}
            </div>
        </div>

        {% if alerts %}
        <div class="section">
            <h2>活跃告警 ({{ alerts|length }})</h2>
            {% for alert in alerts %}
            <div class="card alert {{ alert.severity.value }}">
                <strong>[{{ alert.severity.value|upper }}]</strong>
                {{ alert.message }}
                <span class="timestamp">
                    {{ alert.timestamp|timestamp_format }}
                </span>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="section">
            <h2>告警规则</h2>
            <table>
                <tr><th>规则</th><th>指标</th><th>条件</th><th>级别</th><th>状态</th></tr>
                {% for rule in rules %}
                <tr>
                    <td>{{ rule.name }}</td>
                    <td>{{ rule.metric }}</td>
                    <td>{{ rule.operator }} {{ rule.threshold }}</td>
                    <td>{{ rule.severity.value }}</td>
                    <td>{{ '启用' if rule.enabled else '禁用' }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """

    # 自定义 Jinja2 过滤器：时间戳格式化
    @app.template_filter('timestamp_format')
    def timestamp_format(ts):
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    # ──────────────────────────────────────────
    # 页面路由
    # ──────────────────────────────────────────
    @app.route("/")
    def dashboard():
        metrics = cache.get_all_latest()
        alerts = alert_engine.get_active_alerts()
        rules = alert_engine.get_rules()
        return render_template_string(
            DASHBOARD_HTML,
            metrics=metrics,
            alerts=alerts,
            rules=rules,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    # ──────────────────────────────────────────
    # API 路由
    # ──────────────────────────────────────────
    @app.route("/api/metrics")
    def api_metrics():
        """获取所有最新指标。"""
        metrics = cache.get_all_latest()
        return jsonify({
            "status": "ok",
            "timestamp": time.time(),
            "metrics": metrics
        })

    @app.route("/api/metrics/<name>")
    def api_metric_history(name):
        """获取指定指标的历史数据。"""
        minutes = request.args.get("minutes", 60, type=int)
        start = time.time() - (minutes * 60)
        end = time.time()

        # 先从缓存查
        data = cache.get(name)
        if not data:
            # 从数据库查
            data = store.query(name, start, end)

        return jsonify({
            "status": "ok",
            "metric": name,
            "data": [{"timestamp": t, "value": v} for t, v in data]
        })

    @app.route("/api/alerts")
    def api_alerts():
        """获取活跃告警。"""
        alerts = alert_engine.get_active_alerts()
        return jsonify({
            "status": "ok",
            "alerts": [
                {
                    "rule_name": a.rule_name,
                    "metric": a.metric_name,
                    "value": a.value,
                    "threshold": a.threshold,
                    "severity": a.severity.value,
                    "message": a.message,
                    "timestamp": a.timestamp,
                }
                for a in alerts
            ]
        })

    @app.route("/api/rules")
    def api_rules():
        """获取告警规则。"""
        rules = alert_engine.get_rules()
        return jsonify({
            "status": "ok",
            "rules": [
                {
                    "name": r.name,
                    "metric": r.metric,
                    "operator": r.operator,
                    "threshold": r.threshold,
                    "severity": r.severity.value,
                    "enabled": r.enabled,
                }
                for r in rules
            ]
        })

    @app.route("/api/health")
    def api_health():
        """健康检查端点。"""
        return jsonify({"status": "ok", "timestamp": time.time()})

    return app
```

---

### 6. 完整的监控系统主程序

```python
#!/usr/bin/env python3
"""SRE 主机监控系统 — 完整实现。

功能：
1. 多维度指标采集（CPU、内存、磁盘、网络、负载、进程）
2. SQLite + 内存双层存储
3. 灵活的告警规则引擎
4. Web 仪表盘和 REST API
5. systemd 服务集成

使用方式：
    # 直接运行
    python monitor.py --config config.yaml

    # 作为 systemd 服务
    sudo systemctl start sre-monitor

配置文件示例 (config.yaml):
    monitor:
      collect_interval: 10       # 采集间隔（秒）
      store_interval: 60         # 存储间隔（秒）
      cleanup_interval: 3600     # 清理间隔（秒）
      retention_days: 7          # 数据保留天数

    database:
      path: /var/lib/sre-monitor/metrics.db

    web:
      enabled: true
      host: 0.0.0.0
      port: 8080

    alert_rules:
      - name: cpu_high
        metric: cpu_percent
        operator: ">"
        threshold: 90
        duration: 30
        severity: critical
        message: "CPU 使用率持续过高"

      - name: memory_high
        metric: mem_percent
        operator: ">"
        threshold: 85
        severity: warning
        message: "内存使用率过高"

      - name: disk_high
        metric: disk_root_percent
        operator: ">"
        threshold: 90
        severity: critical
        message: "根分区使用率过高"

      - name: swap_usage
        metric: swap_percent
        operator: ">"
        threshold: 50
        severity: warning
        message: "交换区使用率过高"
"""

import os
import sys
import time
import signal
import logging
import argparse
import threading
from pathlib import Path

# 将当前目录加入路径
sys.path.insert(0, str(Path(__file__).parent))


# ──────────────────────────────────────────────
# 日志配置
# ──────────────────────────────────────────────
def setup_logging(log_level="INFO", log_file=None):
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )


logger = logging.getLogger("sre-monitor")


# ──────────────────────────────────────────────
# 配置加载
# ──────────────────────────────────────────────
def load_config(config_path: str) -> dict:
    """加载 YAML 配置文件。"""
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config


# ──────────────────────────────────────────────
# 默认配置
# ──────────────────────────────────────────────
DEFAULT_CONFIG = {
    "monitor": {
        "collect_interval": 10,
        "store_interval": 60,
        "cleanup_interval": 3600,
        "retention_days": 7,
    },
    "database": {
        "path": "metrics.db",
    },
    "web": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8080,
    },
    "alert_rules": [
        {
            "name": "cpu_high",
            "metric": "cpu_percent",
            "operator": ">",
            "threshold": 90,
            "duration": 30,
            "severity": "critical",
            "message": "CPU 使用率持续过高",
        },
        {
            "name": "memory_high",
            "metric": "mem_percent",
            "operator": ">",
            "threshold": 85,
            "severity": "warning",
            "message": "内存使用率过高",
        },
        {
            "name": "disk_high",
            "metric": "disk_root_percent",
            "operator": ">",
            "threshold": 90,
            "severity": "critical",
            "message": "根分区使用率过高",
        },
    ],
}


# ──────────────────────────────────────────────
# 监控系统主类
# ──────────────────────────────────────────────
class MonitorSystem:
    """主机监控系统。"""

    def __init__(self, config: dict):
        self.config = config
        self._running = False
        self._threads = []

        # 初始化组件
        monitor_cfg = config.get("monitor", {})
        db_cfg = config.get("database", {})
        web_cfg = config.get("web", {})

        # 存储层
        from day54_store import MetricsStore, MemoryCache
        self.store = MetricsStore(
            db_path=db_cfg.get("path", "metrics.db"),
            retention_days=monitor_cfg.get("retention_days", 7)
        )
        self.cache = MemoryCache(max_points=360)

        # 差分计算器
        from day54_delta import DeltaCalculator
        self.delta_calc = DeltaCalculator()

        # 告警引擎
        from day54_alert import AlertEngine, AlertRule, Severity, log_notifier
        self.alert_engine = AlertEngine()
        self.alert_engine.add_notifier(log_notifier)

        # 加载告警规则
        for rule_cfg in config.get("alert_rules", []):
            severity_map = {
                "info": Severity.INFO,
                "warning": Severity.WARNING,
                "critical": Severity.CRITICAL,
            }
            rule = AlertRule(
                name=rule_cfg["name"],
                metric=rule_cfg["metric"],
                operator=rule_cfg["operator"],
                threshold=rule_cfg["threshold"],
                severity=severity_map.get(rule_cfg.get("severity", "warning"), Severity.WARNING),
                duration=rule_cfg.get("duration", 0),
                cooldown=rule_cfg.get("cooldown", 300),
                message=rule_cfg.get("message", ""),
            )
            self.alert_engine.add_rule(rule)

        # Web 仪表盘
        self.web_cfg = web_cfg

        logger.info("监控系统初始化完成")

    def start(self):
        """启动监控系统。"""
        self._running = True
        monitor_cfg = self.config.get("monitor", {})

        # 启动采集线程
        collect_thread = threading.Thread(
            target=self._collect_loop,
            args=(monitor_cfg.get("collect_interval", 10),),
            daemon=True,
            name="collector"
        )
        collect_thread.start()
        self._threads.append(collect_thread)

        # 启动存储线程
        store_thread = threading.Thread(
            target=self._store_loop,
            args=(monitor_cfg.get("store_interval", 60),),
            daemon=True,
            name="store"
        )
        store_thread.start()
        self._threads.append(store_thread)

        # 启动清理线程
        cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            args=(monitor_cfg.get("cleanup_interval", 3600),),
            daemon=True,
            name="cleanup"
        )
        cleanup_thread.start()
        self._threads.append(cleanup_thread)

        # 启动 Web 仪表盘
        if self.web_cfg.get("enabled", True):
            web_thread = threading.Thread(
                target=self._run_web,
                daemon=True,
                name="web"
            )
            web_thread.start()
            self._threads.append(web_thread)

        logger.info("监控系统已启动")

        # 注册信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # 主线程等待
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止监控系统。"""
        logger.info("正在停止监控系统...")
        self._running = False
        for t in self._threads:
            t.join(timeout=5)
        logger.info("监控系统已停止")

    def _signal_handler(self, signum, frame):
        """信号处理。"""
        logger.info(f"收到信号 {signum}，准备停止")
        self._running = False

    def _collect_loop(self, interval: int):
        """指标采集循环。"""
        from day54_collect import collect_all
        logger.info(f"采集线程启动 (间隔 {interval}s)")

        while self._running:
            try:
                metrics = collect_all()

                # 存入缓存
                self.cache.put_batch(metrics)

                # 计算差分指标
                rate_metrics = self.delta_calc.calculate_rates(metrics)
                if rate_metrics:
                    self.cache.put_batch(rate_metrics)

                # 评估告警
                all_metrics = {**metrics, **rate_metrics}
                alerts = self.alert_engine.evaluate(all_metrics)
                if alerts:
                    for alert in alerts:
                        logger.warning(f"告警触发: {alert.message}")

                # 打印状态
                cpu = metrics.get("cpu_percent", 0)
                mem = metrics.get("mem_percent", 0)
                disk = metrics.get("disk_root_percent", 0)
                logger.debug(f"CPU: {cpu}%  MEM: {mem}%  DISK: {disk}%")

            except Exception as e:
                logger.error(f"采集异常: {e}", exc_info=True)

            time.sleep(interval)

    def _store_loop(self, interval: int):
        """定时存储循环。"""
        logger.info(f"存储线程启动 (间隔 {interval}s)")

        while self._running:
            try:
                metrics = self.cache.get_all_latest()
                if metrics:
                    self.store.save_batch(metrics)
                    logger.debug(f"存储 {len(metrics)} 条指标")
            except Exception as e:
                logger.error(f"存储异常: {e}", exc_info=True)

            time.sleep(interval)

    def _cleanup_loop(self, interval: int):
        """数据清理循环。"""
        logger.info(f"清理线程启动 (间隔 {interval}s)")

        while self._running:
            try:
                deleted = self.store.cleanup()
                if deleted:
                    logger.info(f"清理 {deleted} 条过期数据")
            except Exception as e:
                logger.error(f"清理异常: {e}", exc_info=True)

            time.sleep(interval)

    def _run_web(self):
        """启动 Web 仪表盘。"""
        try:
            from day54_web import create_app
            app = create_app(
                store=self.store,
                cache=self.cache,
                alert_engine=self.alert_engine,
                collector=None
            )
            host = self.web_cfg.get("host", "0.0.0.0")
            port = self.web_cfg.get("port", 8080)
            logger.info(f"Web 仪表盘启动: http://{host}:{port}")
            app.run(host=host, port=port, debug=False, use_reloader=False)
        except ImportError:
            logger.warning("Flask 未安装，Web 仪表盘未启动")
        except Exception as e:
            logger.error(f"Web 仪表盘异常: {e}", exc_info=True)


# ──────────────────────────────────────────────
# 命令行入口
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SRE 主机监控系统")
    parser.add_argument(
        "-c", "--config",
        default="/etc/sre-monitor/config.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别"
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="日志文件路径"
    )
    args = parser.parse_args()

    # 初始化日志
    setup_logging(args.log_level, args.log_file)

    # 加载配置
    if os.path.exists(args.config):
        config = load_config(args.config)
    else:
        logger.warning(f"配置文件不存在: {args.config}，使用默认配置")
        config = DEFAULT_CONFIG

    # 启动监控系统
    monitor = MonitorSystem(config)
    monitor.start()


if __name__ == "__main__":
    main()
```

---

### 7. systemd 服务集成

#### 7.1 systemd 服务文件

```ini
# /etc/systemd/system/sre-monitor.service
# SRE 主机监控系统 systemd 服务单元

[Unit]
Description=SRE Host Monitor Service
Documentation=https://github.com/your-org/sre-monitor
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=sre-monitor
Group=sre-monitor

# 启动命令
ExecStart=/usr/bin/python3 /opt/sre-monitor/monitor.py \
    --config /etc/sre-monitor/config.yaml \
    --log-level INFO \
    --log-file /var/log/sre-monitor/monitor.log

# 停止命令（优雅停止）
ExecStop=/bin/kill -SIGTERM $MAINPID

# 重启策略
Restart=on-failure
RestartSec=10
StartLimitBurst=3
StartLimitIntervalSec=60

# 资源限制
LimitNOFILE=65536
MemoryMax=512M
CPUQuota=50%

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/sre-monitor /var/log/sre-monitor
PrivateTmp=true

# 环境变量
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

#### 7.2 安装脚本

```bash
#!/bin/bash
# install.sh — SRE 监控系统安装脚本

set -e

# 配置
INSTALL_DIR="/opt/sre-monitor"
CONFIG_DIR="/etc/sre-monitor"
DATA_DIR="/var/lib/sre-monitor"
LOG_DIR="/var/log/sre-monitor"
SERVICE_USER="sre-monitor"

echo "=== SRE 监控系统安装 ==="

# 1. 创建用户
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
    echo "创建用户: $SERVICE_USER"
fi

# 2. 创建目录
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR" "$LOG_DIR"
echo "创建目录完成"

# 3. 复制文件
cp monitor.py collect.py store.py cache.py delta.py alert.py web.py "$INSTALL_DIR/"
echo "复制程序文件完成"

# 4. 创建默认配置
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cat > "$CONFIG_DIR/config.yaml" << 'EOF'
monitor:
  collect_interval: 10
  store_interval: 60
  cleanup_interval: 3600
  retention_days: 7

database:
  path: /var/lib/sre-monitor/metrics.db

web:
  enabled: true
  host: 0.0.0.0
  port: 8080

alert_rules:
  - name: cpu_high
    metric: cpu_percent
    operator: ">"
    threshold: 90
    duration: 30
    severity: critical
    message: "CPU 使用率持续过高"

  - name: memory_high
    metric: mem_percent
    operator: ">"
    threshold: 85
    severity: warning
    message: "内存使用率过高"

  - name: disk_high
    metric: disk_root_percent
    operator: ">"
    threshold: 90
    severity: critical
    message: "根分区使用率过高"
EOF
    echo "创建默认配置文件"
fi

# 5. 安装依赖
pip3 install psutil flask pyyaml
echo "安装 Python 依赖完成"

# 6. 设置权限
chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR" "$LOG_DIR"
chmod 755 "$INSTALL_DIR"/*.py
echo "设置权限完成"

# 7. 安装 systemd 服务
cp sre-monitor.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable sre-monitor
echo "安装 systemd 服务完成"

# 8. 启动服务
systemctl start sre-monitor
echo "=== 安装完成 ==="
echo "查看状态: systemctl status sre-monitor"
echo "查看日志: journalctl -u sre-monitor -f"
echo "Web 仪表盘: http://localhost:8080"
```

#### 7.3 日志轮转配置

```
# /etc/logrotate.d/sre-monitor
/var/log/sre-monitor/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 sre-monitor sre-monitor
    postrotate
        systemctl reload sre-monitor 2>/dev/null || true
    endscript
}
```

---

## 💻 实战练习

### 练习 1：添加进程监控指标

**要求**：
- 采集每个进程的 CPU 和内存使用
- 找出占用资源最高的 5 个进程
- 当某个进程不存在时触发告警

<details>
<summary>参考答案</summary>

```python
import psutil
from typing import Dict, List


def collect_process_metrics(watch_processes: List[str] = None) -> Dict:
    """采集进程指标。"""
    metrics = {}
    procs = []

    for proc in psutil.process_iter(["pid", "name", "cpu_percent",
                                      "memory_percent", "status"]):
        try:
            info = proc.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 进程总数
    metrics["process_count"] = len(procs)

    # Top 5 CPU
    top_cpu = sorted(procs, key=lambda p: p.get("cpu_percent", 0) or 0,
                     reverse=True)[:5]
    for i, p in enumerate(top_cpu):
        metrics[f"top_cpu_{i}_name"] = p["name"]
        metrics[f"top_cpu_{i}_percent"] = p.get("cpu_percent", 0) or 0

    # Top 5 内存
    top_mem = sorted(procs, key=lambda p: p.get("memory_percent", 0) or 0,
                     reverse=True)[:5]
    for i, p in enumerate(top_mem):
        metrics[f"top_mem_{i}_name"] = p["name"]
        metrics[f"top_mem_{i}_percent"] = p.get("memory_percent", 0) or 0

    # 监控特定进程是否存在
    if watch_processes:
        running_names = {p["name"] for p in procs}
        for name in watch_processes:
            metrics[f"proc_{name}_running"] = 1.0 if name in running_names else 0.0

    return metrics


# 告警规则
def check_critical_processes(engine, required_processes):
    """检查关键进程是否在运行。"""
    from alert import AlertRule, Severity
    for proc_name in required_processes:
        engine.add_rule(AlertRule(
            name=f"proc_{proc_name}_down",
            metric=f"proc_{proc_name}_running",
            operator="<",
            threshold=0.5,
            severity=Severity.CRITICAL,
            cooldown=60,
            message=f"关键进程 {proc_name} 未运行"
        ))
```
</details>

### 练习 2：实现指标导出功能

**要求**：
- 支持导出为 CSV 格式
- 支持导出为 Prometheus 格式
- 支持按时间范围导出

<details>
<summary>参考答案</summary>

```python
import time
from typing import List, Dict
from datetime import datetime


def export_csv(store, metric_names: List[str],
               start: float, end: float, output_path: str):
    """导出指标为 CSV 格式。"""
    import csv

    # 收集所有指标数据
    all_data = {}
    for name in metric_names:
        rows = store.query(name, start, end)
        for ts, value in rows:
            if ts not in all_data:
                all_data[ts] = {"timestamp": ts}
            all_data[ts][name] = value

    # 排序并写入
    sorted_rows = sorted(all_data.values(), key=lambda r: r["timestamp"])
    if not sorted_rows:
        return

    fieldnames = ["timestamp"] + metric_names
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted_rows:
            row["timestamp"] = datetime.fromtimestamp(row["timestamp"]).isoformat()
            writer.writerow(row)


def export_prometheus(store, cache) -> str:
    """导出 Prometheus 格式的指标。"""
    lines = []
    metrics = cache.get_all_latest()

    for name, value in metrics.items():
        if isinstance(value, (int, float)) and not name.startswith('_'):
            # Prometheus 指标名只允许 [a-zA-Z0-9_]
            prom_name = name.replace(".", "_").replace("-", "_")
            lines.append(f"# TYPE {prom_name} gauge")
            lines.append(f"# HELP {prom_name} {name} metric")
            lines.append(f"{prom_name} {value}")

    return "\n".join(lines)


def export_json(store, metric_names: List[str],
                start: float, end: float) -> Dict:
    """导出为 JSON 格式。"""
    result = {}
    for name in metric_names:
        rows = store.query(name, start, end)
        result[name] = [
            {"timestamp": ts, "value": value}
            for ts, value in rows
        ]
    return result
```
</details>

### 练习 3：实现告警通知渠道

**要求**：
- 实现邮件通知（使用 smtplib）
- 实现企业微信/钉钉 Webhook 通知
- 支持告警聚合（相同类型告警合并发送）

<details>
<summary>参考答案</summary>

```python
import time
import json
import logging
import smtplib
from email.mime.text import MIMEText
from typing import List, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class EmailNotifier:
    """邮件通知。"""

    def __init__(self, smtp_host, smtp_port, username, password, recipients):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipients = recipients

    def send(self, alert):
        subject = f"[{alert.severity.value.upper()}] {alert.rule_name}"
        body = f"""
告警规则: {alert.rule_name}
监控指标: {alert.metric_name}
当前值: {alert.value}
阈值: {alert.threshold}
级别: {alert.severity.value}
消息: {alert.message}
时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.timestamp))}
        """

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = ", ".join(self.recipients)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.username, self.recipients, msg.as_string())
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False


class DingTalkNotifier:
    """钉钉 Webhook 通知。"""

    def __init__(self, webhook_url, at_mobiles=None):
        self.webhook_url = webhook_url
        self.at_mobiles = at_mobiles or []

    def send(self, alert):
        import requests
        severity_emoji = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🟢",
        }
        emoji = severity_emoji.get(alert.severity.value, "⚪")

        text = (
            f"### {emoji} SRE 告警通知\n"
            f"- **规则**: {alert.rule_name}\n"
            f"- **指标**: {alert.metric_name}\n"
            f"- **当前值**: {alert.value}\n"
            f"- **阈值**: {alert.threshold}\n"
            f"- **级别**: {alert.severity.value}\n"
            f"- **消息**: {alert.message}\n"
        )

        payload = {
            "msgtype": "markdown",
            "markdown": {"title": f"SRE告警: {alert.rule_name}", "text": text},
            "at": {"atMobiles": self.at_mobiles, "isAtAll": False},
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"钉钉通知失败: {e}")
            return False


class AlertAggregator:
    """告警聚合器 — 相同类型告警合并发送。"""

    def __init__(self, notifier, aggregate_window=300):
        self.notifier = notifier
        self.window = aggregate_window
        self.buffer: Dict[str, List] = defaultdict(list)
        self.last_send: Dict[str, float] = {}

    def send(self, alert):
        key = f"{alert.rule_name}:{alert.severity.value}"
        self.buffer[key].append(alert)

        now = time.time()
        if now - self.last_send.get(key, 0) >= self.window:
            alerts = self.buffer.pop(key, [])
            if alerts:
                # 合并发送
                merged = self._merge_alerts(alerts)
                self.notifier.send(merged)
                self.last_send[key] = now

    def _merge_alerts(self, alerts):
        """合并多条告警为一条。"""
        from dataclasses import dataclass
        @dataclass
        class MergedAlert:
            rule_name: str
            metric_name: str
            value: float
            threshold: float
            severity: object
            message: str
            timestamp: float

        first = alerts[0]
        messages = [a.message for a in alerts]
        return MergedAlert(
            rule_name=first.rule_name,
            metric_name=first.metric_name,
            value=alerts[-1].value,
            threshold=first.threshold,
            severity=first.severity,
            message=f"在过去 {self.window} 秒内触发 {len(alerts)} 次:\n" +
                    "\n".join(messages[:5]),
            timestamp=alerts[-1].timestamp,
        )
```
</details>

---

## 🎯 面试题精选

### 问题 1：psutil 采集指标时，cpu_percent(interval=1) 和 cpu_percent(interval=0) 有什么区别？

**参考答案**：
- `interval=1`：阻塞 1 秒，返回这 1 秒内的平均 CPU 使用率。首次调用总是返回有意义的值。
- `interval=0`：不阻塞，返回自上次调用以来的 CPU 使用率。首次调用返回 0.0（因为没有上次调用的基准）。

在高频采集场景中，应使用 `interval=0` 并确保首次调用后等待足够时间，避免阻塞采集线程。

### 问题 2：为什么使用 SQLite 的 WAL 模式？

**参考答案**：
WAL（Write-Ahead Logging）模式的优势：
1. **读写并发**：读操作不阻塞写操作，写操作不阻塞读操作
2. **更好的性能**：写入不需要等待读取完成
3. **崩溃恢复**：更可靠的崩溃恢复机制

设置方法：`PRAGMA journal_mode=WAL`。在监控系统中，采集线程频繁写入，Web 线程频繁读取，WAL 模式能显著提升并发性能。

### 问题 3：如何避免监控系统本身成为被监控主机的性能瓶颈？

**参考答案**：
1. **采集间隔合理**：核心指标 10-30 秒，非核心指标 60 秒以上
2. **批量写入**：积累多条数据后批量写入数据库，减少 I/O
3. **内存缓存**：热数据放内存，冷数据放 SQLite
4. **异步采集**：使用独立线程，不阻塞主程序
5. **资源限制**：通过 systemd 的 `CPUQuota` 和 `MemoryMax` 限制资源使用
6. **差分计算**：避免每次采集都做全量计算

### 问题 4：如何实现告警的冷却期（cooldown）？

**参考答案**：
冷却期是指同一告警触发后，在指定时间内不重复发送。实现方式：
1. 记录每个规则上次触发的时间戳
2. 触发前检查当前时间与上次触发时间的差值
3. 差值小于冷却期则跳过

需要注意：冷却期应区分告警级别，critical 级别的冷却期可以短一些。

### 问题 5：systemd 服务文件中 `Restart=on-failure` 和 `Restart=always` 有什么区别？

**参考答案**：
- `on-failure`：只在非正常退出时重启（退出码非 0 或被信号杀死）
- `always`：总是重启，包括正常退出（退出码 0）

SRE 监控系统应使用 `on-failure`，因为正常停止（如 `systemctl stop`）不应该触发重启。

### 问题 6：如何设计一个高可用的主机监控系统？

**参考答案**：
1. **本地缓存**：网络中断时数据暂存本地
2. **断点续传**：恢复连接后补传缺失数据
3. **多通道告警**：主通道失败时切换备用通道
4. **自监控**：监控系统自身的健康状态
5. **数据压缩**：减少存储和传输开销
6. **集群方案**：多节点互为备份

### 问题 7：指标存储如何处理数据量增长？

**参考答案**：
1. **数据过期**：自动删除 N 天前的数据（retention policy）
2. **数据聚合**：将旧数据按小时/天聚合，减少数据点
3. **分区存储**：按时间分区，便于清理和查询
4. **压缩**：使用列式存储或压缩算法
5. **迁移到时序数据库**：数据量大时考虑 InfluxDB、Prometheus

### 问题 8：如何测试监控系统？

**参考答案**：
1. **单元测试**：测试每个组件（采集器、存储、告警引擎）
2. **集成测试**：测试组件间的交互
3. **Mock 测试**：模拟 psutil 返回值，测试边界条件
4. **性能测试**：验证高频采集下的资源消耗
5. **故障注入**：模拟磁盘满、网络断等异常场景

### 问题 9：内存缓存和 SQLite 各自适合什么场景？

**参考答案**：
- **内存缓存**：最近几分钟的热数据、Web 仪表盘实时展示、告警评估
- **SQLite**：历史数据持久化、长期趋势分析、数据导出

两者的协作：采集数据先写内存缓存，定时批量刷入 SQLite。查询时先查缓存，缓存未命中再查 SQLite。

### 问题 10：如何处理 psutil 采集时的权限问题？

**参考答案**：
某些 psutil 操作需要 root 权限（如查看其他用户的进程信息）。处理方式：
1. **优雅降级**：捕获 `AccessDenied` 异常，跳过无权限的指标
2. **配置控制**：通过配置文件控制是否采集需要特权的指标
3. **最小权限**：只给监控用户必要的权限（如 `CAP_SYS_PTRACE`）
4. **文档说明**：明确标注哪些指标需要什么权限

---

## 📚 深入阅读

### 官方文档
- [psutil 文档](https://psutil.readthedocs.io/en/latest/)
- [SQLite 文档](https://www.sqlite.org/docs.html)
- [Flask 文档](https://flask.palletsprojects.com/)
- [systemd.service 文档](https://www.freedesktop.org/software/systemd/man/systemd.service.html)

### 推荐书籍
- 《Site Reliability Engineering》— Google SRE 团队（监控章节）
- 《Monitoring with Prometheus》— James Turnbull
- 《Python for DevOps》— Noah Gift（监控和自动化章节）

### 技术博客
- [psutil 高级用法](https://psutil.readthedocs.io/en/latest/#recipes)
- [SQLite 性能优化](https://www.sqlite.org/faq.html#q19)
- [Prometheus 数据模型](https://prometheus.io/docs/concepts/data_model/)

---

## ✅ 自检清单

### 理论检查
- [ ] 能解释 psutil 各类指标的含义和采集方式
- [ ] 能解释 SQLite WAL 模式的优势
- [ ] 能解释告警冷却期和去重的实现原理
- [ ] 能解释内存缓存和持久化存储的协作方式
- [ ] 能解释 systemd 服务文件各字段的含义

### 实操检查
- [ ] 能使用 psutil 采集完整的主机指标
- [ ] 能实现 SQLite 指标存储（包括批量写入和聚合查询）
- [ ] 能实现告警规则引擎（支持持续时间、冷却期）
- [ ] 能开发 Web 仪表盘展示指标和告警
- [ ] 能编写 systemd 服务文件并部署监控系统

### 能力验证
- [ ] 能独立完成主机监控系统的完整开发
- [ ] 能处理监控系统中的常见问题（权限、性能、数据量）
- [ ] 能将监控系统部署为生产级 systemd 服务
