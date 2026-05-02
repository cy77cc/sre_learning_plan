# Day 54: 实战项目 — 主机监控系统（Python 版）

> 📅 日期：2026-05-02
> 📖 学习主题：实战项目：主机监控系统（Python 版）
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 综合运用 Python 知识构建主机监控系统
- 实现指标采集、存储、告警
- 掌握 psutil 库的使用

---

## 📖 详细知识点

### 1. psutil 指标采集

```python
import psutil

# CPU
cpu_percent = psutil.cpu_percent(interval=1)
cpu_count = psutil.cpu_count()
cpu_freq = psutil.cpu_freq()

# 内存
mem = psutil.virtual_memory()
print(f"Total: {mem.total / 1e9:.1f}GB")
print(f"Used: {mem.percent}%")
print(f"Available: {mem.available / 1e9:.1f}GB")

# 磁盘
disk = psutil.disk_usage("/")
print(f"Total: {disk.total / 1e9:.1f}GB, Used: {disk.percent}%")

# 网络
net = psutil.net_io_counters()
print(f"Sent: {net.bytes_sent}, Recv: {net.bytes_recv}")

# 进程
for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
    print(proc.info)
```

### 2. 完整监控系统

```python
#!/usr/bin/env python3
"""Host monitoring system with SQLite storage."""

import psutil
import sqlite3
import time
from datetime import datetime


class Monitor:
    def __init__(self, db_path="metrics.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                network_sent INTEGER,
                network_recv INTEGER
            )
        """)
        self.conn.commit()

    def collect(self):
        net = psutil.net_io_counters()
        data = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "network_sent": net.bytes_sent,
            "network_recv": net.bytes_recv,
        }
        self.conn.execute(
            "INSERT INTO metrics (cpu_percent, memory_percent, disk_percent, network_sent, network_recv) "
            "VALUES (?, ?, ?, ?, ?)",
            (data["cpu_percent"], data["memory_percent"], data["disk_percent"],
             data["network_sent"], data["network_recv"])
        )
        self.conn.commit()
        return data

    def get_latest(self, limit=10):
        rows = self.conn.execute(
            "SELECT * FROM metrics ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return rows

    def check_thresholds(self, data):
        alerts = []
        if data["cpu_percent"] > 90:
            alerts.append(f"CPU usage: {data['cpu_percent']}%")
        if data["memory_percent"] > 85:
            alerts.append(f"Memory usage: {data['memory_percent']}%")
        if data["disk_percent"] > 90:
            alerts.append(f"Disk usage: {data['disk_percent']}%")
        return alerts

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    m = Monitor()
    try:
        while True:
            data = m.collect()
            alerts = m.check_thresholds(data)
            print(f"CPU: {data['cpu_percent']}%  MEM: {data['memory_percent']}%  DISK: {data['disk_percent']}%")
            if alerts:
                print(f"  ALERTS: {', '.join(alerts)}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        m.close()
```

---

## 📚 扩展阅读

- [psutil 文档](https://psutil.readthedocs.io/)
- [SQLite 文档](https://docs.python.org/3/library/sqlite3.html)
