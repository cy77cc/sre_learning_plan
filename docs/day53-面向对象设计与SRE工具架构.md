# Day 53: 面向对象设计与 SRE 工具架构

> 📅 日期：2026-05-02
> 📖 学习主题：SOLID 原则、设计模式在 SRE 中的应用、插件架构、配置驱动
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 52 装饰器与高级技巧、Day 48 Python 基础语法

## 🎯 学习目标

完成 Day 53 的学习后，你应该能够：
- 深入理解 SOLID 原则并在 SRE 工具设计中应用
- 掌握策略模式、观察者模式、工厂模式等在 SRE 场景中的实际应用
- 设计可扩展的插件架构，支持动态加载和热插拔
- 实现配置驱动的运维工具，支持 YAML/JSON 配置
- 运用组合优于继承、依赖倒置等设计原则构建健壮的 SRE 工具

---

## 📖 核心知识点

### 1. SOLID 原则在 SRE 工具中的应用

SOLID 原则不是学术理论，而是解决 SRE 工具维护难题的实用指南。

#### 1.1 单一职责原则（SRP）

```
原则：一个类只有一个引起它变化的原因。

SRE 反面案例 — 一个类做了太多事：
┌─────────────────────────────────────────────┐
│              BadMonitor                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐   │
│  │ 采集指标 │ │ 存储数据 │ │ 发送告警    │   │
│  │ collect  │ │  store  │ │  alert      │   │
│  └─────────┘ └─────────┘ └─────────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐   │
│  │ 生成报告 │ │ 管理配置 │ │ HTTP 接口   │   │
│  │ report  │ │ config  │ │  api        │   │
│  └─────────┘ └─────────┘ └─────────────┘   │
│  修改任何功能都要改这个类 → 高风险             │
└─────────────────────────────────────────────┘

正确做法 — 每个类只负责一件事：
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ MetricCollect │  │ MetricStore  │  │ AlertManager │
│   采集指标    │  │   存储指标    │  │   告警管理    │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                  │
        └────────────────┼──────────────────┘
                         ▼
              ┌──────────────────┐
              │ MonitoringSystem │
              │    组合协调       │
              └──────────────────┘
```

```python
# 违反 SRP — 一个类做了太多事
class BadMonitor:
    def collect_metrics(self): ...
    def store_to_database(self): ...
    def send_alert(self): ...
    def generate_report(self): ...
    def load_config(self): ...
    def start_http_server(self): ...

# 遵循 SRP — 每个类只负责一件事
class MetricCollector:
    """只负责采集指标。"""
    def collect(self) -> dict: ...

class MetricStore:
    """只负责存储指标。"""
    def save(self, metrics: dict) -> None: ...
    def query(self, metric_name: str, start: float, end: float) -> list: ...

class AlertManager:
    """只负责告警判断和通知。"""
    def evaluate(self, metrics: dict) -> list: ...
    def notify(self, alerts: list) -> None: ...

class ReportGenerator:
    """只负责生成报告。"""
    def generate(self, metrics: list) -> str: ...
```

#### 1.2 开闭原则（OCP）

```
原则：对扩展开放，对修改关闭。

SRE 场景：新增告警渠道时，不应该修改已有代码。

┌─────────────────────────────────────────────┐
│              AlertManager                    │
│                                              │
│  def notify(self, message):                  │
│      if channel == "email":      ← 违反 OCP  │
│          send_email(message)                 │
│      elif channel == "slack":   ← 每次加渠道  │
│          send_slack(message)    ← 都要改这里  │
│      elif channel == "webhook":              │
│          send_webhook(message)               │
└─────────────────────────────────────────────┘

正确做法：
┌─────────────────────────────────────────────┐
│          Notifier (接口/抽象类)               │
│          + send(message): ...                │
│                  ▲                            │
│     ┌────────────┼────────────┐              │
│     │            │            │              │
│ EmailNotifier SlackNotifier WebhookNotifier  │
│                                              │
│ AlertManager 持有 Notifier 列表              │
│ 新增渠道只需添加新类，无需修改 AlertManager    │
└─────────────────────────────────────────────┘
```

```python
from abc import ABC, abstractmethod
from typing import List
import logging

logger = logging.getLogger(__name__)


class Notifier(ABC):
    """通知渠道接口。"""

    @abstractmethod
    def send(self, message: str, severity: str = "warning") -> bool:
        """发送通知，返回是否成功。"""
        pass


class EmailNotifier(Notifier):
    def __init__(self, smtp_host, recipients):
        self.smtp_host = smtp_host
        self.recipients = recipients

    def send(self, message, severity="warning"):
        logger.info(f"发送邮件到 {self.recipients}: {message}")
        # 实际发送逻辑
        return True


class SlackNotifier(Notifier):
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send(self, message, severity="warning"):
        import requests
        color = {"critical": "#FF0000", "warning": "#FFA500", "info": "#00FF00"}
        payload = {
            "attachments": [{
                "color": color.get(severity, "#FFA500"),
                "text": message
            }]
        }
        resp = requests.post(self.webhook_url, json=payload, timeout=5)
        return resp.status_code == 200


class WebhookNotifier(Notifier):
    def __init__(self, url, headers=None):
        self.url = url
        self.headers = headers or {}

    def send(self, message, severity="warning"):
        import requests
        payload = {"message": message, "severity": severity}
        resp = requests.post(self.url, json=payload, headers=self.headers, timeout=5)
        return resp.status_code == 200


class AlertManager:
    """告警管理器 — 新增渠道无需修改此类。"""

    def __init__(self):
        self.notifiers: List[Notifier] = []
        self.rules = []

    def add_notifier(self, notifier: Notifier):
        self.notifiers.append(notifier)

    def add_rule(self, rule):
        self.rules.append(rule)

    def evaluate(self, metrics: dict):
        """评估所有规则，触发告警。"""
        for rule in self.rules:
            if rule.should_alert(metrics):
                message = rule.format_message(metrics)
                severity = rule.severity
                for notifier in self.notifiers:
                    try:
                        notifier.send(message, severity)
                    except Exception as e:
                        logger.error(f"通知发送失败: {e}")
```

#### 1.3 里氏替换原则（LSP）

```
原则：子类必须能替换父类而不影响程序正确性。

SRE 场景：所有存储后端都应该能互相替换。

违反 LSP 的例子：
class MetricsStore:
    def save(self, metrics):
        # 保存到 SQLite
        self.conn.execute("INSERT ...", metrics)

class RedisStore(MetricsStore):
    def save(self, metrics):
        # 如果 RedisStore 不支持某些查询方法
        # 替换后程序就崩溃了
        raise NotImplementedError("Redis 不支持复杂查询")
```

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime


class MetricsStore(ABC):
    """指标存储抽象基类 — 定义所有存储后端必须支持的操作。"""

    @abstractmethod
    def save(self, metric_name: str, value: float,
             timestamp: Optional[float] = None) -> None:
        """保存一条指标数据。"""
        pass

    @abstractmethod
    def query(self, metric_name: str, start: float, end: float) -> List[Dict]:
        """查询指标数据。"""
        pass

    @abstractmethod
    def get_latest(self, metric_name: str) -> Optional[Dict]:
        """获取最新一条数据。"""
        pass


class SQLiteStore(MetricsStore):
    """SQLite 存储后端。"""

    def __init__(self, db_path="metrics.db"):
        import sqlite3
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_name_ts ON metrics(name, timestamp)"
        )
        self.conn.commit()

    def save(self, metric_name, value, timestamp=None):
        ts = timestamp or datetime.now().timestamp()
        self.conn.execute(
            "INSERT INTO metrics (name, value, timestamp) VALUES (?, ?, ?)",
            (metric_name, value, ts)
        )
        self.conn.commit()

    def query(self, metric_name, start, end):
        rows = self.conn.execute(
            "SELECT name, value, timestamp FROM metrics "
            "WHERE name = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp",
            (metric_name, start, end)
        ).fetchall()
        return [{"name": r[0], "value": r[1], "timestamp": r[2]} for r in rows]

    def get_latest(self, metric_name):
        row = self.conn.execute(
            "SELECT name, value, timestamp FROM metrics "
            "WHERE name = ? ORDER BY timestamp DESC LIMIT 1",
            (metric_name,)
        ).fetchone()
        if row:
            return {"name": row[0], "value": row[1], "timestamp": row[2]}
        return None


class InMemoryStore(MetricsStore):
    """内存存储后端（用于测试和临时场景）。"""

    def __init__(self):
        self._data = {}  # {metric_name: [(timestamp, value), ...]}

    def save(self, metric_name, value, timestamp=None):
        ts = timestamp or datetime.now().timestamp()
        self._data.setdefault(metric_name, []).append((ts, value))

    def query(self, metric_name, start, end):
        entries = self._data.get(metric_name, [])
        return [
            {"name": metric_name, "value": v, "timestamp": t}
            for t, v in entries if start <= t <= end
        ]

    def get_latest(self, metric_name):
        entries = self._data.get(metric_name, [])
        if entries:
            t, v = entries[-1]
            return {"name": metric_name, "value": v, "timestamp": t}
        return None


# 使用：任何 MetricsStore 的子类都能互相替换
def save_and_check(store: MetricsStore, name: str, value: float):
    """这个函数不关心具体存储实现。"""
    store.save(name, value)
    latest = store.get_latest(name)
    print(f"{name} 最新值: {latest['value']}")

# 可以传入任何子类
save_and_check(InMemoryStore(), "cpu_percent", 85.5)
save_and_check(SQLiteStore("/tmp/test.db"), "cpu_percent", 85.5)
```

#### 1.4 接口隔离原则（ISP）

```
原则：不应该强迫客户端依赖它不使用的接口。

SRE 场景：不同的监控组件只需要不同的能力。

违反 ISP：
┌─────────────────────────────────────────────────┐
│              MonitorInterface                    │
│  + collect_metrics()                             │
│  + store_metrics()                               │
│  + send_alert()                                  │
│  + generate_report()                             │
│  + start_http_server()                           │
│  + load_config()                                 │
└─────────────────────────────────────────────────┘
    ▲
    │  所有组件都必须实现所有方法（很多是空实现）
    │
    ├── SimpleCollector 只需要 collect_metrics
    ├── AlertSender 只需要 send_alert
    └── ReportService 只需要 generate_report
```

```python
from abc import ABC, abstractmethod
from typing import Dict, List


# 拆分为细粒度的接口
class Collector(ABC):
    @abstractmethod
    def collect(self) -> Dict[str, float]:
        pass


class Store(ABC):
    @abstractmethod
    def save(self, metrics: Dict[str, float]) -> None:
        pass

    @abstractmethod
    def query(self, name: str, start: float, end: float) -> List[Dict]:
        pass


class Alerter(ABC):
    @abstractmethod
    def evaluate(self, metrics: Dict[str, float]) -> List[str]:
        pass

    @abstractmethod
    def notify(self, alerts: List[str]) -> None:
        pass


class Reporter(ABC):
    @abstractmethod
    def generate(self, metrics: List[Dict]) -> str:
        pass


# 每个组件只实现自己需要的接口
class CPUMonitor(Collector):
    """只需要实现 Collector 接口。"""
    def collect(self):
        import psutil
        return {"cpu_percent": psutil.cpu_percent(interval=1)}


class DiskAlerter(Alerter):
    """只需要实现 Alerter 接口。"""
    def __init__(self, threshold=90):
        self.threshold = threshold

    def evaluate(self, metrics):
        alerts = []
        for name, value in metrics.items():
            if "disk" in name and value > self.threshold:
                alerts.append(f"磁盘告警: {name}={value}%")
        return alerts

    def notify(self, alerts):
        for alert in alerts:
            print(f"ALERT: {alert}")
```

#### 1.5 依赖倒置原则（DIP）

```
原则：高层模块不应依赖低层模块，两者都应依赖抽象。

SRE 场景：监控系统的核心逻辑不应依赖具体的数据存储或通知方式。

违反 DIP：
┌──────────────────┐     依赖      ┌──────────────┐
│ MonitoringSystem  │ ──────────→ │  SQLiteStore  │
│  (高层模块)       │             │  (低层模块)    │
└──────────────────┘             └──────────────┘
    换成 Redis 要改 MonitoringSystem 的代码

遵循 DIP：
┌──────────────────┐     依赖      ┌──────────────┐
│ MonitoringSystem  │ ──────────→ │ MetricsStore  │
│  (高层模块)       │             │  (抽象接口)    │
└──────────────────┘             └──────────────┘
                                       ▲
                          ┌────────────┼────────────┐
                          │            │            │
                    SQLiteStore  RedisStore  InMemoryStore
                    (低层模块依赖抽象)
```

```python
from abc import ABC, abstractmethod
from typing import List, Dict


# 抽象层
class MetricsStore(ABC):
    @abstractmethod
    def save(self, name: str, value: float): ...

    @abstractmethod
    def query(self, name: str, start: float, end: float) -> List[Dict]: ...


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, message: str): ...


# 高层模块依赖抽象
class MonitoringSystem:
    """监控系统核心 — 不依赖任何具体实现。"""

    def __init__(self, store: MetricsStore, channels: List[NotificationChannel]):
        self.store = store
        self.channels = channels
        self.rules = []

    def add_rule(self, metric_name, threshold, direction="above"):
        self.rules.append({
            "metric": metric_name,
            "threshold": threshold,
            "direction": direction
        })

    def process_metrics(self, metrics: Dict[str, float]):
        """处理一批指标：存储 + 检查告警。"""
        # 存储
        for name, value in metrics.items():
            self.store.save(name, value)

        # 检查告警
        alerts = self._evaluate_rules(metrics)
        if alerts:
            self._send_notifications(alerts)

    def _evaluate_rules(self, metrics):
        alerts = []
        for rule in self.rules:
            name = rule["metric"]
            if name in metrics:
                value = metrics[name]
                if rule["direction"] == "above" and value > rule["threshold"]:
                    alerts.append(f"{name}={value} 超过阈值 {rule['threshold']}")
                elif rule["direction"] == "below" and value < rule["threshold"]:
                    alerts.append(f"{name}={value} 低于阈值 {rule['threshold']}")
        return alerts

    def _send_notifications(self, alerts):
        for alert in alerts:
            for channel in self.channels:
                try:
                    channel.send(alert)
                except Exception as e:
                    print(f"通知失败: {e}")


# 依赖注入：通过构造函数传入具体实现
system = MonitoringSystem(
    store=SQLiteStore("/tmp/monitor.db"),
    channels=[SlackNotifier("https://hooks.slack.com/xxx")]
)

# 测试时可以注入 mock
test_system = MonitoringSystem(
    store=InMemoryStore(),
    channels=[PrintNotifier()]  # 只是打印，不真正发送
)
```

---

### 2. 设计模式在 SRE 中的应用

#### 2.1 策略模式 — 可切换的采集策略

```python
from abc import ABC, abstractmethod
from typing import Dict
import psutil


class CollectStrategy(ABC):
    """采集策略接口。"""

    @abstractmethod
    def collect(self) -> Dict[str, float]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class FastCollectStrategy(CollectStrategy):
    """快速采集策略 — 只采集核心指标，不阻塞。"""

    @property
    def name(self):
        return "fast"

    def collect(self):
        return {
            "cpu_percent": psutil.cpu_percent(interval=0),
            "memory_percent": psutil.virtual_memory().percent,
        }


class DetailedCollectStrategy(CollectStrategy):
    """详细采集策略 — 采集所有指标，可能较慢。"""

    @property
    def name(self):
        return "detailed"

    def collect(self):
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()
        cpu_freq = psutil.cpu_freq()

        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_freq_current": cpu_freq.current if cpu_freq else 0,
            "memory_total_gb": mem.total / (1024 ** 3),
            "memory_available_gb": mem.available / (1024 ** 3),
            "memory_percent": mem.percent,
            "disk_total_gb": disk.total / (1024 ** 3),
            "disk_free_gb": disk.free / (1024 ** 3),
            "disk_percent": disk.percent,
            "net_bytes_sent": net.bytes_sent,
            "net_bytes_recv": net.bytes_recv,
        }


class ProcessCollectStrategy(CollectStrategy):
    """进程采集策略 — 采集进程级指标。"""

    @property
    def name(self):
        return "process"

    def collect(self):
        top_cpu = []
        top_mem = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                top_cpu.append((info["pid"], info["name"], info["cpu_percent"] or 0))
                top_mem.append((info["pid"], info["name"], info["memory_percent"] or 0))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        top_cpu.sort(key=lambda x: x[2], reverse=True)
        top_mem.sort(key=lambda x: x[2], reverse=True)

        result = {}
        for pid, name, cpu in top_cpu[:5]:
            result[f"top_cpu_{name}_{pid}"] = cpu
        for pid, name, mem in top_mem[:5]:
            result[f"top_mem_{name}_{pid}"] = mem
        return result


class MetricCollector:
    """可切换采集策略的指标采集器。"""

    def __init__(self, strategy: CollectStrategy):
        self._strategy = strategy

    @property
    def strategy(self):
        return self._strategy

    @strategy.setter
    def strategy(self, strategy: CollectStrategy):
        self._strategy = strategy

    def collect(self):
        return self._strategy.collect()


# 使用
collector = MetricCollector(FastCollectStrategy())
print(collector.collect())  # 快速采集

collector.strategy = DetailedCollectStrategy()
print(collector.collect())  # 切换为详细采集
```

#### 2.2 观察者模式 — 事件驱动的告警系统

```python
from typing import Callable, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricEvent:
    """指标事件。"""
    name: str
    value: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    source: str = "localhost"
    labels: Dict[str, str] = field(default_factory=dict)


class EventBus:
    """事件总线 — 实现观察者模式。

    SRE 场景：
    - 指标采集后发布事件，多个消费者（存储、告警、仪表盘）独立订阅
    - 解耦事件的生产者和消费者
    - 支持异步处理

    架构：
    ┌──────────┐    publish     ┌──────────┐    notify    ┌──────────────┐
    │ Collector │ ──────────→  │ EventBus │ ──────────→ │ AlertManager │
    └──────────┘               └──────────┘              ├──────────────┤
                               subscribe    └───────────→│ MetricStore  │
                                                          ├──────────────┤
                                                          └───────────→│ Dashboard  │
                                                                       └──────────────┘
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件。"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅。"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    def publish(self, event_type: str, data: Any):
        """发布事件，通知所有订阅者。"""
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"事件处理器 {handler.__name__} 异常: {e}")

    def publish_metric(self, event: MetricEvent):
        """发布指标事件。"""
        self.publish("metric", event)
        # 同时按指标名发布
        self.publish(f"metric.{event.name}", event)


# 使用
bus = EventBus()

# 订阅者 1：存储
def store_metric(event: MetricEvent):
    print(f"[Store] {event.name}={event.value}")

# 订阅者 2：告警
def check_alert(event: MetricEvent):
    thresholds = {"cpu_percent": 90, "memory_percent": 85}
    if event.name in thresholds and event.value > thresholds[event.name]:
        print(f"[Alert] {event.name}={event.value} 超过阈值 {thresholds[event.name]}")

# 订阅者 3：日志
def log_metric(event: MetricEvent):
    logger.info(f"[Log] {event.name}={event.value} @ {event.source}")

# 注册订阅者
bus.subscribe("metric", store_metric)
bus.subscribe("metric", check_alert)
bus.subscribe("metric", log_metric)
bus.subscribe("metric.cpu_percent", lambda e: print(f"[CPU专用] {e.value}%"))

# 发布事件
bus.publish_metric(MetricEvent("cpu_percent", 95.2))
bus.publish_metric(MetricEvent("memory_percent", 60.0))
```

#### 2.3 工厂模式 — 动态创建采集器和存储后端

```python
from typing import Dict, Type
import json
import yaml


class CollectorFactory:
    """采集器工厂 — 根据配置动态创建采集器。

    SRE 场景：不同环境（开发、测试、生产）需要不同的采集器配置，
    通过配置文件驱动，无需修改代码。
    """

    _registry: Dict[str, Type] = {}

    @classmethod
    def register(cls, name: str):
        """注册装饰器。"""
        def decorator(klass):
            cls._registry[name] = klass
            return klass
        return decorator

    @classmethod
    def create(cls, name: str, **kwargs):
        """创建采集器实例。"""
        if name not in cls._registry:
            raise ValueError(f"未知采集器: {name}，可用: {list(cls._registry.keys())}")
        return cls._registry[name](**kwargs)

    @classmethod
    def from_config(cls, config: dict):
        """从配置字典创建采集器。"""
        collectors = []
        for item in config.get("collectors", []):
            name = item.pop("type")
            collectors.append(cls.create(name, **item))
        return collectors


@CollectorFactory.register("cpu")
class CPUCollector:
    def __init__(self, interval=1):
        self.interval = interval

    def collect(self):
        import psutil
        return {"cpu_percent": psutil.cpu_percent(interval=self.interval)}


@CollectorFactory.register("memory")
class MemoryCollector:
    def __init__(self, **kwargs):
        pass

    def collect(self):
        import psutil
        mem = psutil.virtual_memory()
        return {"memory_percent": mem.percent}


@CollectorFactory.register("disk")
class DiskCollector:
    def __init__(self, mount_point="/", **kwargs):
        self.mount_point = mount_point

    def collect(self):
        import psutil
        disk = psutil.disk_usage(self.mount_point)
        return {f"disk_{self.mount_point}_percent": disk.percent}


# 从配置文件创建
config = {
    "collectors": [
        {"type": "cpu", "interval": 2},
        {"type": "memory"},
        {"type": "disk", "mount_point": "/"},
        {"type": "disk", "mount_point": "/data"},
    ]
}

collectors = CollectorFactory.from_config(config)
for c in collectors:
    print(f"{type(c).__name__}: {c.collect()}")
```

#### 2.4 责任链模式 — 多级告警处理

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class Alert:
    """告警数据。"""
    name: str
    severity: str  # critical, warning, info
    message: str
    value: float
    threshold: float
    timestamp: float = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class AlertHandler(ABC):
    """告警处理器基类（责任链模式）。"""

    def __init__(self):
        self._next: Optional[AlertHandler] = None

    def set_next(self, handler: 'AlertHandler') -> 'AlertHandler':
        self._next = handler
        return handler

    def handle(self, alert: Alert):
        result = self.process(alert)
        if result and self._next:
            self._next.handle(alert)
        elif not result:
            print(f"  [{self.__class__.__name__}] 告警被拦截: {alert.name}")

    @abstractmethod
    def process(self, alert: Alert) -> bool:
        """处理告警，返回 True 继续传递，返回 False 拦截。"""
        pass


class DeduplicationHandler(AlertHandler):
    """去重处理器 — 相同告警在冷却期内不重复发送。"""

    def __init__(self, cooldown_seconds=300):
        super().__init__()
        self.cooldown = cooldown_seconds
        self.recent_alerts = {}  # {alert_name: last_send_time}

    def process(self, alert):
        now = time.time()
        last_time = self.recent_alerts.get(alert.name, 0)
        if now - last_time < self.cooldown:
            return False  # 拦截：冷却期内
        self.recent_alerts[alert.name] = now
        return True  # 继续传递


class SeverityFilter(AlertHandler):
    """严重级别过滤器 — 只处理指定级别以上的告警。"""

    def __init__(self, min_severity="warning"):
        super().__init__()
        self.severity_order = {"info": 0, "warning": 1, "critical": 2}
        self.min_level = self.severity_order.get(min_severity, 1)

    def process(self, alert):
        alert_level = self.severity_order.get(alert.severity, 0)
        return alert_level >= self.min_level


class RateLimitHandler(AlertHandler):
    """限流处理器 — 每秒最多处理 N 条告警。"""

    def __init__(self, max_per_second=10):
        super().__init__()
        self.max_per_second = max_per_second
        self.window = []

    def process(self, alert):
        now = time.time()
        self.window = [t for t in self.window if now - t < 1.0]
        if len(self.window) >= self.max_per_second:
            return False
        self.window.append(now)
        return True


class NotificationHandler(AlertHandler):
    """最终通知处理器 — 实际发送告警。"""

    def process(self, alert):
        print(f"  [通知] {alert.severity.upper()}: {alert.name} — {alert.message}")
        return True


# 构建责任链
chain = DeduplicationHandler(cooldown_seconds=60)
chain.set_next(SeverityFilter(min_severity="warning")) \
     .set_next(RateLimitHandler(max_per_second=5)) \
     .set_next(NotificationHandler())

# 测试
alerts = [
    Alert("high_cpu", "critical", "CPU 95%", 95, 90),
    Alert("high_cpu", "critical", "CPU 95%", 95, 90),  # 被去重拦截
    Alert("low_disk", "info", "磁盘 50%", 50, 90),     # 被级别过滤拦截
    Alert("high_mem", "warning", "内存 88%", 88, 85),
]

for alert in alerts:
    print(f"\n处理: {alert.name}")
    chain.handle(alert)
```

#### 2.5 状态模式 — 服务健康检查

```python
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional
import time


class ServiceState(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()
    UNKNOWN = auto()


class HealthState(ABC):
    """健康状态基类。"""

    @abstractmethod
    def check(self, context: 'ServiceHealthCheck') -> ServiceState:
        pass

    @abstractmethod
    def on_enter(self, context: 'ServiceHealthCheck'):
        pass


class HealthyState(HealthState):
    def check(self, context):
        if context.consecutive_failures >= 1:
            return ServiceState.DEGRADED
        return ServiceState.HEALTHY

    def on_enter(self, context):
        print(f"  [{context.name}] 状态: 健康")
        context.recovery_time = None


class DegradedState(HealthState):
    def check(self, context):
        if context.consecutive_failures >= 3:
            return ServiceState.UNHEALTHY
        if context.consecutive_failures == 0:
            return ServiceState.HEALTHY
        return ServiceState.DEGRADED

    def on_enter(self, context):
        print(f"  [{context.name}] 状态: 降级 (连续失败 {context.consecutive_failures} 次)")


class UnhealthyState(HealthState):
    def check(self, context):
        if context.consecutive_successes >= 3:
            return ServiceState.HEALTHY
        return ServiceState.UNHEALTHY

    def on_enter(self, context):
        if not context.recovery_time:
            context.recovery_time = time.time()
        print(f"  [{context.name}] 状态: 不健康")


class ServiceHealthCheck:
    """带状态机的健康检查器。"""

    _states = {
        ServiceState.HEALTHY: HealthyState(),
        ServiceState.DEGRADED: DegradedState(),
        ServiceState.UNHEALTHY: UnhealthyState(),
    }

    def __init__(self, name, check_func, **kwargs):
        self.name = name
        self.check_func = check_func
        self.current_state = ServiceState.UNKNOWN
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.recovery_time = None

    def check(self):
        try:
            result = self.check_func()
            if result:
                self.consecutive_failures = 0
                self.consecutive_successes += 1
            else:
                self.consecutive_successes = 0
                self.consecutive_failures += 1
        except Exception:
            self.consecutive_successes = 0
            self.consecutive_failures += 1

        # 状态转换
        state_handler = self._states.get(self.current_state)
        if state_handler:
            new_state = state_handler.check(self)
        else:
            new_state = ServiceState.HEALTHY if self.consecutive_failures == 0 \
                else ServiceState.UNHEALTHY

        if new_state != self.current_state:
            self.current_state = new_state
            self._states[new_state].on_enter(self)

        return self.current_state


# 使用
def check_http():
    import random
    return random.random() > 0.3  # 70% 成功率

service = ServiceHealthCheck("web-api", check_http)
for i in range(10):
    state = service.check()
    time.sleep(0.1)
```

---

### 3. 插件架构设计

#### 3.1 完整的插件系统

```python
#!/usr/bin/env python3
"""SRE 工具插件系统 — 支持动态加载和热插拔。

架构：
┌─────────────────────────────────────────────────────────┐
│                    PluginManager                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │                  Plugin Registry                    │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │  │
│  │  │ cpu  │ │ disk │ │ net  │ │ proc │  ...          │  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘              │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Plugin Loader                         │  │
│  │  - 从文件加载                                      │  │
│  │  - 从目录扫描                                      │  │
│  │  - 热重载                                          │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Plugin Lifecycle                       │  │
│  │  init → configure → start → execute → stop         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
"""

import importlib
import importlib.util
import os
import sys
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto

logger = logging.getLogger(__name__)


class PluginState(Enum):
    LOADED = auto()
    CONFIGURED = auto()
    RUNNING = auto()
    STOPPED = auto()
    ERROR = auto()


@dataclass
class PluginInfo:
    """插件元信息。"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    """插件基类 — 所有插件必须继承此类。"""

    @abstractmethod
    def info(self) -> PluginInfo:
        """返回插件元信息。"""
        pass

    @abstractmethod
    def configure(self, config: dict) -> None:
        """配置插件。"""
        pass

    @abstractmethod
    def start(self) -> None:
        """启动插件。"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止插件。"""
        pass

    def health_check(self) -> bool:
        """健康检查，默认返回 True。"""
        return True


class CollectorPlugin(Plugin):
    """采集器插件基类。"""

    @abstractmethod
    def collect(self) -> Dict[str, float]:
        """采集指标。"""
        pass


class NotifierPlugin(Plugin):
    """通知插件基类。"""

    @abstractmethod
    def send(self, message: str, severity: str) -> bool:
        """发送通知。"""
        pass


class PluginManager:
    """插件管理器。"""

    def __init__(self, plugin_dirs: List[str] = None):
        self._plugins: Dict[str, Plugin] = {}
        self._states: Dict[str, PluginState] = {}
        self._plugin_dirs = plugin_dirs or []

    def register(self, plugin: Plugin):
        """手动注册插件。"""
        info = plugin.info()
        if info.name in self._plugins:
            raise ValueError(f"插件 {info.name} 已注册")

        # 检查依赖
        for dep in info.dependencies:
            if dep not in self._plugins:
                raise ValueError(f"插件 {info.name} 依赖未满足: {dep}")

        self._plugins[info.name] = plugin
        self._states[info.name] = PluginState.LOADED
        logger.info(f"注册插件: {info.name} v{info.version}")

    def load_from_directory(self, directory: str):
        """从目录扫描并加载插件。"""
        plugin_dir = Path(directory)
        if not plugin_dir.exists():
            logger.warning(f"插件目录不存在: {directory}")
            return

        for py_file in plugin_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                self._load_plugin_file(py_file)
            except Exception as e:
                logger.error(f"加载插件 {py_file} 失败: {e}")

    def _load_plugin_file(self, filepath: Path):
        """从单个文件加载插件。"""
        module_name = filepath.stem
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 查找 Plugin 子类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and issubclass(attr, Plugin)
                    and attr is not Plugin and attr is not CollectorPlugin
                    and attr is not NotifierPlugin):
                instance = attr()
                self.register(instance)

    def configure_plugin(self, name: str, config: dict):
        """配置插件。"""
        plugin = self._get_plugin(name)
        plugin.configure(config)
        self._states[name] = PluginState.CONFIGURED
        logger.info(f"配置插件: {name}")

    def start_plugin(self, name: str):
        """启动插件。"""
        plugin = self._get_plugin(name)
        plugin.start()
        self._states[name] = PluginState.RUNNING
        logger.info(f"启动插件: {name}")

    def stop_plugin(self, name: str):
        """停止插件。"""
        plugin = self._get_plugin(name)
        plugin.stop()
        self._states[name] = PluginState.STOPPED
        logger.info(f"停止插件: {name}")

    def start_all(self):
        """启动所有已配置的插件。"""
        for name, state in self._states.items():
            if state == PluginState.CONFIGURED:
                self.start_plugin(name)

    def stop_all(self):
        """停止所有运行中的插件。"""
        for name, state in self._states.items():
            if state == PluginState.RUNNING:
                self.stop_plugin(name)

    def get_collectors(self) -> List[CollectorPlugin]:
        """获取所有采集器插件。"""
        return [p for p in self._plugins.values() if isinstance(p, CollectorPlugin)]

    def get_notifiers(self) -> List[NotifierPlugin]:
        """获取所有通知插件。"""
        return [p for p in self._plugins.values() if isinstance(p, NotifierPlugin)]

    def status(self) -> Dict[str, str]:
        """获取所有插件状态。"""
        return {name: state.name for name, state in self._states.items()}

    def _get_plugin(self, name: str) -> Plugin:
        if name not in self._plugins:
            raise KeyError(f"插件不存在: {name}")
        return self._plugins[name]


# ──────────────────────────────────────────────
# 示例插件实现
# ──────────────────────────────────────────────

class CPUMonitorPlugin(CollectorPlugin):
    """CPU 监控插件。"""

    def __init__(self):
        self._interval = 1
        self._running = False

    def info(self):
        return PluginInfo(
            name="cpu_monitor",
            version="1.0.0",
            description="CPU 指标采集插件",
            author="SRE Team"
        )

    def configure(self, config):
        self._interval = config.get("interval", 1)

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def collect(self):
        import psutil
        return {
            "cpu_percent": psutil.cpu_percent(interval=self._interval),
            "cpu_count": psutil.cpu_count(),
        }


class MemoryMonitorPlugin(CollectorPlugin):
    """内存监控插件。"""

    def __init__(self):
        self._running = False

    def info(self):
        return PluginInfo(
            name="memory_monitor",
            version="1.0.0",
            description="内存指标采集插件",
            author="SRE Team"
        )

    def configure(self, config):
        pass

    def start(self):
        self._running = True

    def stop(self):
        self._running = False

    def collect(self):
        import psutil
        mem = psutil.virtual_memory()
        return {
            "memory_percent": mem.percent,
            "memory_available_gb": round(mem.available / (1024 ** 3), 2),
        }


class LogNotifierPlugin(NotifierPlugin):
    """日志通知插件。"""

    def __init__(self):
        self._logger = logging.getLogger("notifier.log")

    def info(self):
        return PluginInfo(
            name="log_notifier",
            version="1.0.0",
            description="日志通知插件",
            author="SRE Team"
        )

    def configure(self, config):
        level = config.get("level", "INFO")
        self._logger.setLevel(getattr(logging, level))

    def start(self):
        pass

    def stop(self):
        pass

    def send(self, message, severity):
        self._logger.log(
            getattr(logging, severity.upper(), logging.INFO),
            message
        )
        return True


# ──────────────────────────────────────────────
# 使用示例
# ──────────────────────────────────────────────

if __name__ == "__main__":
    manager = PluginManager()

    # 注册插件
    manager.register(CPUMonitorPlugin())
    manager.register(MemoryMonitorPlugin())
    manager.register(LogNotifierPlugin())

    # 配置
    manager.configure_plugin("cpu_monitor", {"interval": 2})
    manager.configure_plugin("log_notifier", {"level": "DEBUG"})

    # 启动
    manager.start_all()

    # 采集
    for collector in manager.get_collectors():
        metrics = collector.collect()
        print(f"{collector.info().name}: {metrics}")

    # 发送通知
    for notifier in manager.get_notifiers():
        notifier.send("测试告警消息", "warning")

    # 查看状态
    print(f"\n插件状态: {manager.status()}")

    # 停止
    manager.stop_all()
```

---

### 4. 配置驱动的运维工具

#### 4.1 YAML 配置驱动的监控系统

```python
#!/usr/bin/env python3
"""配置驱动的监控系统。

通过 YAML 配置文件定义：
- 采集哪些指标
- 告警规则
- 通知渠道
- 采集间隔

无需修改代码即可调整监控策略。
"""

import yaml
import time
import logging
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CollectorConfig:
    """采集器配置。"""
    name: str
    type: str
    interval: int = 60
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """告警规则。"""
    name: str
    metric: str
    condition: str  # "above", "below", "equal"
    threshold: float
    duration: int = 0  # 持续时间（秒）
    severity: str = "warning"
    message: str = ""

    def evaluate(self, value: float) -> bool:
        if self.condition == "above":
            return value > self.threshold
        elif self.condition == "below":
            return value < self.threshold
        elif self.condition == "equal":
            return abs(value - self.threshold) < 0.001
        return False


@dataclass
class NotificationConfig:
    """通知配置。"""
    type: str  # "email", "slack", "webhook", "log"
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


class ConfigDrivenMonitor:
    """配置驱动的监控系统。"""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.collectors = []
        self.rules = []
        self.notifiers = []
        self._history = {}  # {metric_name: [(timestamp, value), ...]}

        self._init_from_config()

    def _load_config(self) -> dict:
        """加载 YAML 配置文件。"""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        logger.info(f"加载配置: {self.config_path}")
        return config

    def _init_from_config(self):
        """从配置初始化组件。"""
        # 初始化采集器
        for coll_cfg in self.config.get("collectors", []):
            cfg = CollectorConfig(**coll_cfg)
            if cfg.enabled:
                self.collectors.append(cfg)
                logger.info(f"启用采集器: {cfg.name} (间隔 {cfg.interval}s)")

        # 初始化告警规则
        for rule_cfg in self.config.get("alert_rules", []):
            rule = AlertRule(**rule_cfg)
            self.rules.append(rule)
            logger.info(f"加载规则: {rule.name} ({rule.metric} {rule.condition} {rule.threshold})")

        # 初始化通知渠道
        for notif_cfg in self.config.get("notifications", []):
            cfg = NotificationConfig(**notif_cfg)
            if cfg.enabled:
                self.notifiers.append(cfg)
                logger.info(f"启用通知: {cfg.type}")

    def collect_all(self) -> Dict[str, float]:
        """执行所有采集器。"""
        metrics = {}
        for cfg in self.collectors:
            try:
                result = self._execute_collector(cfg)
                metrics.update(result)
            except Exception as e:
                logger.error(f"采集器 {cfg.name} 失败: {e}")
        return metrics

    def _execute_collector(self, cfg: CollectorConfig) -> Dict[str, float]:
        """执行单个采集器。"""
        import psutil

        if cfg.type == "cpu":
            return {"cpu_percent": psutil.cpu_percent(interval=cfg.params.get("interval", 1))}
        elif cfg.type == "memory":
            mem = psutil.virtual_memory()
            return {"memory_percent": mem.percent}
        elif cfg.type == "disk":
            mount = cfg.params.get("mount_point", "/")
            disk = psutil.disk_usage(mount)
            return {f"disk_{mount}_percent": disk.percent}
        elif cfg.type == "network":
            net = psutil.net_io_counters()
            return {"net_bytes_sent": net.bytes_sent, "net_bytes_recv": net.bytes_recv}
        else:
            logger.warning(f"未知采集器类型: {cfg.type}")
            return {}

    def check_alerts(self, metrics: Dict[str, float]) -> List[AlertRule]:
        """检查告警规则。"""
        triggered = []
        now = time.time()

        for rule in self.rules:
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]

            # 记录历史
            if rule.metric not in self._history:
                self._history[rule.metric] = []
            self._history[rule.metric].append((now, value))

            # 清理过期历史
            if rule.duration > 0:
                cutoff = now - rule.duration
                self._history[rule.metric] = [
                    (t, v) for t, v in self._history[rule.metric] if t >= cutoff
                ]

            # 检查条件
            if rule.duration > 0:
                # 需要持续超标
                history = self._history[rule.metric]
                if len(history) >= 2 and all(rule.evaluate(v) for _, v in history):
                    triggered.append(rule)
            else:
                if rule.evaluate(value):
                    triggered.append(rule)

        return triggered

    def send_notifications(self, alerts: List[AlertRule], metrics: Dict[str, float]):
        """发送通知。"""
        for alert in alerts:
            message = alert.message or f"{alert.metric} 触发告警: {alert.condition} {alert.threshold}"
            value = metrics.get(alert.metric, 0)
            full_message = f"[{alert.severity.upper()}] {alert.name}: {message} (当前值: {value})"

            for notif_cfg in self.notifiers:
                try:
                    self._send_notification(notif_cfg, full_message, alert.severity)
                except Exception as e:
                    logger.error(f"通知发送失败 ({notif_cfg.type}): {e}")

    def _send_notification(self, cfg: NotificationConfig, message: str, severity: str):
        if cfg.type == "log":
            logger.log(
                getattr(logging, severity.upper(), logging.INFO),
                message
            )
        elif cfg.type == "webhook":
            import requests
            url = cfg.params.get("url")
            if url:
                requests.post(url, json={"message": message, "severity": severity}, timeout=5)
        # 其他通知类型...

    def run_once(self):
        """执行一次采集和检查。"""
        metrics = self.collect_all()
        alerts = self.check_alerts(metrics)
        if alerts:
            self.send_notifications(alerts, metrics)
        return metrics, alerts

    def run(self, global_interval: int = 10):
        """持续运行。"""
        logger.info("监控系统启动")
        try:
            while True:
                metrics, alerts = self.run_once()
                print(f"指标: {metrics}")
                if alerts:
                    print(f"告警: {[a.name for a in alerts]}")
                time.sleep(global_interval)
        except KeyboardInterrupt:
            logger.info("监控系统停止")


# 示例配置文件 (monitor_config.yaml):
SAMPLE_CONFIG = """
# 采集器配置
collectors:
  - name: cpu
    type: cpu
    interval: 10
    enabled: true
    params:
      interval: 1

  - name: memory
    type: memory
    interval: 30
    enabled: true

  - name: disk_root
    type: disk
    interval: 60
    enabled: true
    params:
      mount_point: /

  - name: disk_data
    type: disk
    interval: 60
    enabled: true
    params:
      mount_point: /data

# 告警规则
alert_rules:
  - name: cpu_high
    metric: cpu_percent
    condition: above
    threshold: 90
    duration: 30
    severity: critical
    message: "CPU 使用率持续过高"

  - name: memory_high
    metric: memory_percent
    condition: above
    threshold: 85
    severity: warning
    message: "内存使用率过高"

  - name: disk_high
    metric: disk_/_percent
    condition: above
    threshold: 90
    severity: critical
    message: "根分区使用率过高"

# 通知渠道
notifications:
  - type: log
    enabled: true
    params:
      level: WARNING

  - type: webhook
    enabled: false
    params:
      url: https://hooks.slack.com/xxx
"""

if __name__ == "__main__":
    import tempfile
    import os

    # 写入示例配置
    config_file = os.path.join(tempfile.gettempdir(), "monitor_config.yaml")
    with open(config_file, "w") as f:
        f.write(SAMPLE_CONFIG)

    # 运行
    monitor = ConfigDrivenMonitor(config_file)
    for _ in range(3):
        metrics, alerts = monitor.run_once()
        print(f"采集: {metrics}")
        print(f"告警: {[r.name for r in alerts]}")
        time.sleep(2)
```

---

## 💻 实战练习

### 练习 1：设计一个可插拔的日志收集器

**要求**：
- 支持多种日志源（文件、journald、syslog）
- 支持多种输出目标（Elasticsearch、文件、stdout）
- 使用 SOLID 原则设计
- 通过配置文件驱动

```python
# 你的代码框架
from abc import ABC, abstractmethod

class LogSource(ABC):
    @abstractmethod
    def read(self) -> list: ...

class LogOutput(ABC):
    @abstractmethod
    def write(self, entries: list) -> None: ...

class LogCollector:
    def __init__(self, source: LogSource, output: LogOutput):
        # TODO
        pass
```

<details>
<summary>参考答案</summary>

```python
from abc import ABC, abstractmethod
from typing import List, Dict
import json
import time


class LogEntry:
    def __init__(self, timestamp, level, message, source="", **extra):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.source = source
        self.extra = extra

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            **self.extra
        }


class LogSource(ABC):
    @abstractmethod
    def read(self) -> List[LogEntry]:
        pass


class FileLogSource(LogSource):
    def __init__(self, filepath, seek_to_end=False):
        self.filepath = filepath
        self._position = 0
        if seek_to_end:
            try:
                with open(filepath) as f:
                    f.seek(0, 2)
                    self._position = f.tell()
            except FileNotFoundError:
                pass

    def read(self) -> List[LogEntry]:
        entries = []
        try:
            with open(self.filepath) as f:
                f.seek(self._position)
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(LogEntry(
                            timestamp=time.time(),
                            level="INFO",
                            message=line,
                            source=self.filepath
                        ))
                self._position = f.tell()
        except FileNotFoundError:
            pass
        return entries


class StdoutLogSource(LogSource):
    """从 stdout 读取（用于测试）。"""
    def __init__(self):
        self._lines = []

    def add_line(self, line):
        self._lines.append(line)

    def read(self) -> List[LogEntry]:
        entries = [LogEntry(time.time(), "INFO", line, "stdin") for line in self._lines]
        self._lines.clear()
        return entries


class LogOutput(ABC):
    @abstractmethod
    def write(self, entries: List[LogEntry]) -> None:
        pass


class JsonFileOutput(LogOutput):
    def __init__(self, filepath):
        self.filepath = filepath

    def write(self, entries):
        with open(self.filepath, "a") as f:
            for entry in entries:
                f.write(json.dumps(entry.to_dict()) + "\n")


class StdoutOutput(LogOutput):
    def write(self, entries):
        for entry in entries:
            print(f"[{entry.level}] {entry.source}: {entry.message}")


class LogCollector:
    def __init__(self, source: LogSource, output: LogOutput, filters=None):
        self.source = source
        self.output = output
        self.filters = filters or []

    def add_filter(self, filter_func):
        self.filters.append(filter_func)

    def collect_once(self):
        entries = self.source.read()
        for f in self.filters:
            entries = [e for e in entries if f(e)]
        if entries:
            self.output.write(entries)
        return len(entries)

    def run(self, interval=5):
        while True:
            count = self.collect_once()
            if count:
                print(f"处理 {count} 条日志")
            time.sleep(interval)

# 使用
source = FileLogSource("/var/log/syslog", seek_to_end=True)
output = StdoutOutput()
collector = LogCollector(source, output)
collector.add_filter(lambda e: "error" in e.message.lower())
```
</details>

### 练习 2：实现一个配置驱动的定时任务调度器

**要求**：
- 通过 YAML 配置定义任务
- 支持 cron 表达式
- 支持任务依赖
- 任务失败重试

<details>
<summary>参考答案</summary>

```python
import yaml
import time
import logging
from typing import Dict, List, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class TaskConfig:
    name: str
    command: str
    schedule: str = ""  # cron 表达式或 interval
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 0
    timeout: int = 300
    enabled: bool = True


class Task:
    def __init__(self, config: TaskConfig, func: Callable):
        self.config = config
        self.func = func
        self.last_run = 0
        self.run_count = 0
        self.fail_count = 0

    def should_run(self, now: float) -> bool:
        if not self.config.enabled:
            return False
        if self.config.schedule.startswith("every "):
            seconds = int(self.config.schedule.split()[1])
            return now - self.last_run >= seconds
        return False

    def execute(self):
        for attempt in range(self.config.retry_count + 1):
            try:
                result = self.func()
                self.run_count += 1
                self.last_run = time.time()
                return result
            except Exception as e:
                logger.error(f"任务 {self.config.name} 失败 (尝试 {attempt+1}): {e}")
                if attempt < self.config.retry_count:
                    time.sleep(2 ** attempt)
                else:
                    self.fail_count += 1
                    raise


class Scheduler:
    def __init__(self, config_path: str):
        self.tasks: Dict[str, Task] = {}
        self._load_config(config_path)

    def _load_config(self, path):
        with open(path) as f:
            config = yaml.safe_load(f)

        task_registry = {
            "cleanup_temp": lambda: logger.info("清理临时文件"),
            "check_disk": lambda: logger.info("检查磁盘"),
            "backup_db": lambda: logger.info("备份数据库"),
        }

        for task_cfg in config.get("tasks", []):
            tc = TaskConfig(**task_cfg)
            func = task_registry.get(tc.command, lambda: logger.info(f"执行 {tc.command}"))
            self.tasks[tc.name] = Task(tc, func)

    def run(self, interval=1):
        while True:
            now = time.time()
            for name, task in self.tasks.items():
                if task.should_run(now):
                    # 检查依赖
                    deps_met = all(
                        self.tasks[dep].last_run > task.last_run
                        for dep in task.config.depends_on
                        if dep in self.tasks
                    )
                    if deps_met:
                        task.execute()
            time.sleep(interval)
```
</details>

### 练习 3：设计一个告警规则引擎

**要求**：
- 支持复杂的条件表达式（AND、OR、NOT）
- 支持时间窗口聚合（avg、max、min、count）
- 支持告警抑制和静默

<details>
<summary>参考答案</summary>

```python
import time
from typing import Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum, auto


class Aggregation(Enum):
    AVG = auto()
    MAX = auto()
    MIN = auto()
    COUNT = auto()
    LAST = auto()


@dataclass
class MetricWindow:
    """时间窗口内的指标数据。"""
    values: List[tuple] = field(default_factory=list)  # [(timestamp, value)]

    def add(self, value: float, timestamp: float = None):
        ts = timestamp or time.time()
        self.values.append((ts, value))

    def aggregate(self, func: Aggregation, window_seconds: float) -> float:
        now = time.time()
        cutoff = now - window_seconds
        recent = [v for t, v in self.values if t >= cutoff]
        if not recent:
            raise ValueError("窗口内无数据")

        if func == Aggregation.AVG:
            return sum(recent) / len(recent)
        elif func == Aggregation.MAX:
            return max(recent)
        elif func == Aggregation.MIN:
            return min(recent)
        elif func == Aggregation.COUNT:
            return len(recent)
        elif func == Aggregation.LAST:
            return recent[-1]


@dataclass
class RuleCondition:
    metric: str
    aggregation: Aggregation = Aggregation.LAST
    window_seconds: float = 0
    operator: str = ">"  # >, <, >=, <=, ==, !=
    threshold: float = 0

    def evaluate(self, metrics: Dict[str, MetricWindow]) -> bool:
        if self.metric not in metrics:
            return False
        window = metrics[self.metric]
        try:
            value = window.aggregate(self.aggregation, self.window_seconds or 60)
        except ValueError:
            return False

        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: abs(a - b) < 0.001,
            "!=": lambda a, b: abs(a - b) >= 0.001,
        }
        return ops[self.operator](value, self.threshold)


@dataclass
class AlertRule:
    name: str
    conditions: List[RuleCondition]
    logic: str = "AND"  # AND or OR
    severity: str = "warning"
    message: str = ""
    suppressed_until: float = 0

    def evaluate(self, metrics: Dict[str, MetricWindow]) -> bool:
        if time.time() < self.suppressed_until:
            return False

        results = [c.evaluate(metrics) for c in self.conditions]
        if self.logic == "AND":
            return all(results)
        return any(results)

    def suppress(self, duration_seconds: float):
        self.suppressed_until = time.time() + duration_seconds


class RuleEngine:
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.metrics: Dict[str, MetricWindow] = {}

    def add_rule(self, rule: AlertRule):
        self.rules.append(rule)

    def record(self, metric_name: str, value: float):
        if metric_name not in self.metrics:
            self.metrics[metric_name] = MetricWindow()
        self.metrics[metric_name].add(value)

    def evaluate_all(self) -> List[AlertRule]:
        triggered = []
        for rule in self.rules:
            if rule.evaluate(self.metrics):
                triggered.append(rule)
        return triggered
```
</details>

---

## 🎯 面试题精选

### 问题 1：什么是 SOLID 原则？请用 SRE 工具的例子解释。

**参考答案**：
- **S（单一职责）**：采集器只负责采集，存储器只负责存储，告警器只负责告警
- **O（开闭原则）**：新增告警渠道只需添加新类，不修改 AlertManager
- **L（里氏替换）**：SQLiteStore 和 InMemoryStore 可以互相替换
- **I（接口隔离）**：采集器不需要实现通知接口
- **D（依赖倒置）**：监控系统依赖 MetricsStore 抽象，不依赖具体实现

### 问题 2：组合优于继承，为什么？在 SRE 工具中如何体现？

**参考答案**：
继承的问题：紧耦合、脆弱基类问题、继承层次过深难以理解。组合的优势：
1. 灵活替换：可以在运行时更换组件
2. 更好的测试：可以单独 mock 每个组件
3. 避免菱形继承问题

SRE 示例：`MonitoringSystem` 通过组合 `MetricCollector` + `MetricStore` + `AlertManager` 构建，而不是继承一个大而全的基类。

### 问题 3：设计模式在 SRE 工具中有哪些实际应用？

**参考答案**：
- **策略模式**：可切换的采集策略（快速/详细）
- **观察者模式**：事件驱动的告警系统，指标发布后多个消费者独立处理
- **工厂模式**：根据配置动态创建采集器和存储后端
- **责任链模式**：多级告警处理（去重 → 级别过滤 → 限流 → 通知）
- **状态模式**：服务健康检查状态机（健康 → 降级 → 不健康）
- **装饰器模式**：为函数添加日志、重试、缓存等横切关注点

### 问题 4：什么是依赖注入？如何在 Python 中实现？

**参考答案**：
依赖注入是指对象的依赖由外部传入，而不是在内部创建。Python 实现方式：
1. **构造函数注入**：通过 `__init__` 参数传入依赖（最常用）
2. **属性注入**：通过 setter 方法设置依赖
3. **方法注入**：通过方法参数传入依赖

Python 没有像 Java/Spring 那样的 DI 容器，通常手动注入或使用 `injector` 库。

### 问题 5：如何设计一个可扩展的插件系统？

**参考答案**：
关键设计要素：
1. **插件接口**：定义清晰的抽象基类（Plugin）
2. **注册机制**：使用元类或 `__init_subclass__` 自动注册
3. **发现机制**：支持从目录扫描加载插件
4. **生命周期管理**：init → configure → start → stop
5. **依赖管理**：检查插件间的依赖关系
6. **配置驱动**：通过配置文件启用/禁用和配置插件

### 问题 6：观察者模式和发布-订阅模式有什么区别？

**参考答案**：
- **观察者模式**：主题直接维护观察者列表，直接通知（紧耦合）
- **发布-订阅模式**：通过事件总线（中间层）解耦，发布者和订阅者互不知道对方

在 SRE 中，发布-订阅更适合，因为指标采集器不需要知道谁在消费数据。

### 问题 7：什么是开闭原则的"对扩展开放，对修改关闭"？

**参考答案**：
"对扩展开放"意味着可以通过添加新代码来扩展系统行为。"对修改关闭"意味着扩展时不需要修改已有代码。

实现方式：依赖抽象（接口/基类），新增实现类即可扩展。例如新增一个 Slack 通知渠道，只需实现 `Notifier` 接口，注册到 `AlertManager`，无需修改 `AlertManager` 的代码。

### 问题 8：责任链模式在 SRE 中有哪些应用场景？

**参考答案**：
1. **告警处理链**：去重 → 级别过滤 → 限流 → 聚合 → 通知
2. **日志处理链**：解析 → 过滤 → 转换 → 输出
3. **请求处理链**：认证 → 限流 → 路由 → 处理
4. **故障诊断链**：网络检查 → DNS 检查 → 端口检查 → 服务检查

### 问题 9：如何在 Python 中实现配置热重载？

**参考答案**：
1. **文件监控**：使用 `watchdog` 库监控配置文件变化
2. **信号触发**：发送 SIGHUP 信号触发重载
3. **定时轮询**：定期检查配置文件的修改时间
4. **API 触发**：通过 HTTP API 触发重载

关键点：重载时要注意线程安全，使用锁保护配置的读写。

### 问题 10：数据类（dataclass）和普通类有什么区别？什么时候用哪个？

**参考答案**：
`dataclass` 自动生成 `__init__`、`__repr__`、`__eq__` 等方法，适合数据容器。普通类适合有复杂行为的对象。

SRE 中的使用场景：
- **dataclass**：配置对象、数据传输对象、指标数据结构
- **普通类**：有复杂逻辑的管理器、采集器、处理器

---

## 📚 深入阅读

### 官方文档
- [Python 类文档](https://docs.python.org/3/tutorial/classes.html)
- [abc 模块](https://docs.python.org/3/library/abc.html)
- [dataclasses 模块](https://docs.python.org/3/library/dataclasses.html)
- [importlib 模块](https://docs.python.org/3/library/importlib.html)

### 推荐书籍
- 《设计模式：可复用面向对象软件的基础》— GoF（经典设计模式）
- 《Clean Architecture》— Robert C. Martin（SOLID 原则的深入讲解）
- 《Fluent Python》第二版 — Luciano Ramalho（Python 对象模型）
- 《Python 设计模式》— Chetan Giridhar

### 技术博客
- [Refactoring Guru: Design Patterns](https://refactoring.guru/design-patterns/python)
- [Real Python: OOP in Python 3](https://realpython.com/python3-object-oriented-programming/)
- [Python Design Patterns](https://python-patterns.guide/)

---

## ✅ 自检清单

### 理论检查
- [ ] 能解释 SOLID 原则并举出 SRE 工具的例子
- [ ] 能区分策略模式、观察者模式、工厂模式的应用场景
- [ ] 能解释"组合优于继承"的原因
- [ ] 能解释依赖注入和依赖倒置的关系
- [ ] 能解释插件架构的核心设计要素

### 实操检查
- [ ] 能使用策略模式设计可切换的采集器
- [ ] 能实现一个完整的插件系统（注册、加载、生命周期）
- [ ] 能设计配置驱动的监控系统
- [ ] 能实现责任链模式的告警处理链
- [ ] 能使用 dataclass 和 ABC 设计清晰的接口

### 能力验证
- [ ] 能为 SRE 工具选择合适的设计模式
- [ ] 能在代码审查中识别 SOLID 违规
- [ ] 能设计可扩展、可测试的 SRE 工具架构
