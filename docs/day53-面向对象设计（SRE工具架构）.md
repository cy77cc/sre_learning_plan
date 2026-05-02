# Day 53: Python 面向对象设计与 SRE 工具架构

> 📅 日期：2026-05-02
> 📖 学习主题：Python 面向对象设计与 SRE 工具架构
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 OOP 四大原则在 SRE 工具中的应用
- 掌握类、继承、组合、抽象类
- 能设计可扩展的运维工具架构

---

## 📖 详细知识点

### 1. 类与对象

```python
class Server:
    def __init__(self, hostname, ip, role):
        self.hostname = hostname
        self.ip = ip
        self.role = role
        self._metrics = {}

    @property
    def address(self):
        return f"{self.hostname} ({self.ip})"

    def check_health(self):
        raise NotImplementedError

    def __repr__(self):
        return f"Server({self.hostname}, {self.ip})"
```

### 2. 继承与组合

```python
# 继承
class WebServer(Server):
    def __init__(self, hostname, ip, port=80):
        super().__init__(hostname, ip, "web")
        self.port = port

    def check_health(self):
        resp = requests.get(f"http://{self.ip}:{self.port}/health")
        return resp.status_code == 200

# 组合（优于继承）
class HealthChecker:
    def __init__(self, server, checker):
        self.server = server
        self.checker = checker

    def run(self):
        return self.checker.check(self.server)
```

### 3. 抽象基类

```python
from abc import ABC, abstractmethod

class Monitor(ABC):
    @abstractmethod
    def collect(self):
        pass

    @abstractmethod
    def alert(self):
        pass

class CPUMonitor(Monitor):
    def collect(self):
        return psutil.cpu_percent()

    def alert(self):
        if self.collect() > 90:
            send_alert("CPU usage > 90%")
```

### 4. 数据类（Python 3.7+）

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class ServerConfig:
    hostname: str
    ip: str
    ports: List[int] = field(default_factory=lambda: [80, 443])
    tags: List[str] = field(default_factory=list)

    @property
    def address(self):
        return f"{self.hostname}:{self.ports[0]}"

config = ServerConfig("web01", "10.0.1.10")
```

---

## 🏗️ 实战：可插拔监控系统

```python
#!/usr/bin/env python3
"""Pluggable monitoring system using OOP."""

from abc import ABC, abstractmethod
from typing import Dict, List
import psutil


class MetricCollector(ABC):
    @abstractmethod
    def collect(self) -> Dict[str, float]:
        pass


class CPUCollector(MetricCollector):
    def collect(self):
        return {"cpu_percent": psutil.cpu_percent(interval=1)}


class MemoryCollector(MetricCollector):
    def collect(self):
        mem = psutil.virtual_memory()
        return {
            "memory_percent": mem.percent,
            "memory_available_mb": mem.available / 1024 / 1024,
        }


class DiskCollector(MetricCollector):
    def collect(self):
        disk = psutil.disk_usage("/")
        return {
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / 1024**3,
        }


class Monitor:
    def __init__(self):
        self.collectors: List[MetricCollector] = []

    def register(self, collector: MetricCollector):
        self.collectors.append(collector)

    def run(self) -> Dict:
        metrics = {}
        for collector in self.collectors:
            metrics.update(collector.collect())
        return metrics


if __name__ == "__main__":
    monitor = Monitor()
    monitor.register(CPUCollector())
    monitor.register(MemoryCollector())
    monitor.register(DiskCollector())

    metrics = monitor.run()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
```

---

## 🧪 练习题

### 练习 1：设计一个告警系统

设计一个支持多种告警渠道（邮件、Slack、Webhook）的告警系统。

<details>
<summary>答案</summary>

```python
from abc import ABC, abstractmethod

class Notifier(ABC):
    @abstractmethod
    def send(self, message: str):
        pass

class EmailNotifier(Notifier):
    def send(self, message):
        # send email
        pass

class SlackNotifier(Notifier):
    def send(self, message):
        # send to Slack
        pass

class AlertManager:
    def __init__(self):
        self.notifiers = []

    def add_notifier(self, notifier: Notifier):
        self.notifiers.append(notifier)

    def alert(self, message):
        for n in self.notifiers:
            n.send(message)
```
</details>

---

## 📚 扩展阅读

- [Python OOP 指南](https://docs.python.org/3/tutorial/classes.html)
- [Design Patterns in Python](https://refactoring.guru/design-patterns/python)
