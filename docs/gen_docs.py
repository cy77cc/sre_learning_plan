#!/usr/bin/env python3
"""批量生成 SRE 学习文档的辅助脚本。"""
import os
import sys

DOCS_DIR = "/root/sre_learning/docs"

def write_md(filename, content):
    path = os.path.join(DOCS_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    lines = content.count('\n') + 1
    print(f"  {lines:4d} {filename}")

def gen_header(day, title, hours="2-3"):
    return f"""# Day {day}: {title}

> 📅 日期：2026-05-02
> 📖 学习主题：{title}
> ⏰ 计划学习时间：{hours} 小时

---

## 🎯 学习目标

"""

def gen_footer(refs=None):
    s = """
---

## 🧪 练习题

"""
    if refs:
        s += "## 📚 扩展阅读\n\n"
        for r in refs:
            s += f"- {r}\n"
    return s

# ============ 批量生成 ============
files = {}

# Day 44
files["day44-数据类型与配置文件处理.md"] = gen_header(44, "Python 数据类型与配置文件处理") + """
- 掌握 Python 核心数据结构（list/dict/tuple/set）
- 能处理 JSON、YAML、INI、TOML 配置文件
- 理解数据结构在 SRE 工具中的应用

---

## 📖 详细知识点

### 1. 列表与字典

```python
# 列表推导式
servers = ["web01", "web02", "db01"]
active = [s for s in servers if s.startswith("web")]
# ['web01', 'web02']

# 字典操作
config = {"host": "0.0.0.0", "port": 8080}
config.get("timeout", 30)  # 安全访问
```

### 2. JSON 处理

```python
import json

# 读取
with open("config.json") as f:
    data = json.load(f)

# 写入
with open("output.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# 解析 API 响应
resp = requests.get("https://api.example.com/metrics")
metrics = resp.json()
```

### 3. YAML 处理

```python
# pip install pyyaml
import yaml

with open("docker-compose.yml") as f:
    config = yaml.safe_load(f)

# 写入
with open("output.yaml", "w") as f:
    yaml.dump(config, f, default_flow_style=False)
```

### 4. INI / TOML

```python
import configparser
config = configparser.ConfigParser()
config.read("app.ini")
db_host = config["database"]["host"]

# TOML (Python 3.11+)
import tomllib
with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
```

### 5. 实战：配置合并工具

```python
#!/usr/bin/env python3
"""Deep merge configuration files."""
import json
import sys

def deep_merge(base, override):
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

base = json.load(open(sys.argv[1]))
override = json.load(open(sys.argv[2]))
print(json.dumps(deep_merge(base, override), indent=2))
```
""" + gen_footer(["Python 数据结构文档", "JSON 规范 RFC 8259"])

# Day 46
files["day46-函数、日志模块与异常处理.md"] = gen_header(46, "Python 函数、日志模块与异常处理") + """
- 掌握 Python 函数的高级用法（装饰器、生成器、lambda）
- 熟练使用 logging 模块
- 掌握异常处理的 best practices

---

## 📖 详细知识点

### 1. 函数高级用法

```python
# 默认参数陷阱（不要用可变对象作默认值）
def add_item(item, items=None):  # 正确
    if items is None:
        items = []
    items.append(item)
    return items

# *args 和 **kwargs
def log_event(level, *args, **kwargs):
    msg = " ".join(str(a) for a in args)
    extra = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"[{level}] {msg} {extra}")

log_event("ERROR", "disk full", host="web01", disk="/dev/sda1")
```

### 2. 装饰器

```python
import time
import functools

def retry(max_attempts=3, delay=1):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry(max_attempts=3, delay=2)
def fetch_data(url):
    return requests.get(url).json()
```

### 3. 日志模块

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log"),
    ],
)

logger = logging.getLogger(__name__)
logger.info("Service started")
logger.warning("High memory usage: 85%")
logger.error("Connection failed", exc_info=True)
```

### 4. 异常处理

```python
# 正确做法
try:
    result = process_data(data)
except ValueError as e:
    logger.error(f"Invalid data: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error")
    raise
finally:
    cleanup()

# 自定义异常
class ServiceUnavailableError(Exception):
    def __init__(self, service, url):
        self.service = service
        self.url = url
        super().__init__(f"Service {service} at {url} is unavailable")
```
""" + gen_footer(["Python logging 文档", "PEP 3134 - Exception Chaining"])

# Day 47
files["day47-正则表达式与日志解析.md"] = gen_header(47, "Python 正则表达式与日志解析") + """
- 掌握 re 模块的常用方法
- 能用正则解析 Nginx/Apache 日志
- 理解贪婪与非贪婪匹配

---

## 📖 详细知识点

### 1. re 模块核心方法

```python
import re

# match - 从头匹配
re.match(r'\d+', '123abc')  # match '123'

# search - 任意位置
re.search(r'\d+', 'abc123')  # match '123'

# findall - 所有匹配
re.findall(r'\d+', 'a1b22c333')  # ['1', '22', '333']

# finditer - 迭代器
for m in re.finditer(r'\d+', 'a1b22c333'):
    print(m.group(), m.start(), m.end())

# sub - 替换
re.sub(r'\d+', 'NUM', 'a1b22c')  # 'aNUMbNUMc'

# split - 分割
re.split(r'[,\s]+', 'a,b  c,d')  # ['a', 'b', 'c', 'd']
```

### 2. 正则语法速查

| 模式 | 含义 | 示例 |
|------|------|------|
| `\d` | 数字 | `123` |
| `\w` | 单词字符 | `abc_123` |
| `\s` | 空白字符 | 空格、Tab |
| `.` | 任意字符 | |
| `*` | 0次或多次 | `ab*c` 匹配 ac/abc/abbc |
| `+` | 1次或多次 | `ab+c` 匹配 abc/abbc |
| `?` | 0次或1次 | `ab?c` 匹配 ac/abc |
| `{n,m}` | n到m次 | `\d{2,4}` |
| `^` | 行首 | `^ERROR` |
| `$` | 行尾 | `done$` |
| `()` | 分组 | `(\d+)-(\d+)` |
| `|` | 或 | `error\|warning` |
| `[]` | 字符集 | `[a-zA-Z0-9]` |

### 3. 解析 Nginx 日志

```python
import re
from datetime import datetime

LOG_PATTERN = re.compile(
    r'(?P<ip>\d+\.\d+\.\d+\.\d+) - - '
    r'\[(?P<time>[^\]]+)\] '
    r'"(?P<method>\w+) (?P<path>\S+) (?P<proto>\S+)" '
    r'(?P<status>\d+) (?P<size>\d+) '
    r'"(?P<referer>[^"]*)" '
    r'"(?P<ua>[^"]*)"'
)

def parse_nginx_log(filepath):
    results = []
    with open(filepath) as f:
        for line in f:
            m = LOG_PATTERN.match(line)
            if m:
                results.append(m.groupdict())
    return results

# 分析
logs = parse_nginx_log("/var/log/nginx/access.log")
from collections import Counter
status_counts = Counter(log["status"] for log in logs)
print(status_counts)
```
""" + gen_footer(["regex101.com 在线测试", "Python re 文档"])

# Day 48
files["day48-网络编程与HTTP客户端.md"] = gen_header(48, "Python 网络编程与 HTTP 客户端") + """
- 掌握 requests 库的高级用法
- 理解 socket 编程基础
- 能编写 HTTP 客户端与 REST API 交互

---

## 📖 详细知识点

### 1. requests 高级用法

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 会话（保持连接）
session = requests.Session()
session.headers.update({"User-Agent": "SRE-Tool/1.0"})

# 重试策略
retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

# 发送请求
resp = session.get("https://api.example.com/data", params={"page": 1})
resp.raise_for_status()  # 抛出 HTTP 错误
data = resp.json()

# 上传文件
with open("backup.tar.gz", "rb") as f:
    session.put("https://storage.example.com/file", data=f)

# 超时设置
resp = requests.get(url, timeout=(3.05, 30))  # (connect, read)
```

### 2. Socket 编程基础

```python
import socket

# TCP 客户端
def tcp_client(host, port, message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(message.encode())
        data = s.recv(1024)
        return data.decode()

# TCP 服务端
def tcp_server(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        conn, addr = s.accept()
        with conn:
            data = conn.recv(1024)
            conn.sendall(b"OK")

# UDP
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.sendto(b"hello", ("localhost", 9999))
    data, addr = s.recvfrom(1024)
```

### 3. 实战：API 健康检查

```python
#!/usr/bin/env python3
"""API health checker with retry and timeout."""
import requests
import sys
import time

def check_api(url, retries=3, timeout=5):
    session = requests.Session()
    for i in range(retries):
        try:
            start = time.time()
            resp = session.get(url, timeout=timeout)
            elapsed = time.time() - start
            print(f"OK {url} {resp.status_code} {elapsed:.3f}s")
            return True
        except requests.RequestException as e:
            print(f"FAIL {url} attempt {i+1}: {e}")
            if i < retries - 1:
                time.sleep(2 ** i)
    return False

urls = ["http://localhost:8080/health", "http://localhost:9090/metrics"]
all_ok = all(check_api(u) for u in urls)
sys.exit(0 if all_ok else 1)
```
""" + gen_footer(["requests 文档", "Python socket 文档"])

# Day 49
files["day49-数据库交互（SQLite）.md"] = gen_header(49, "Python 数据库交互（SQLite）") + """
- 掌握 sqlite3 模块的使用
- 理解 SQL 基础和参数化查询
- 能用 Python 操作 SQLite 进行数据管理

---

## 📖 详细知识点

### 1. SQLite 基础

```python
import sqlite3

# 连接（文件不存在会自动创建）
conn = sqlite3.connect("sre_data.db")
cursor = conn.cursor()

# 创建表
cursor.execute("""
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hostname TEXT NOT NULL UNIQUE,
    ip TEXT NOT NULL,
    cpu_cores INTEGER,
    memory_gb INTEGER,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# 插入
cursor.execute(
    "INSERT INTO servers (hostname, ip, cpu_cores, memory_gb) VALUES (?, ?, ?, ?)",
    ("web01", "10.0.1.10", 4, 16)
)
conn.commit()

# 批量插入
servers = [
    ("web02", "10.0.1.11", 8, 32),
    ("db01", "10.0.2.10", 16, 64),
]
cursor.executemany(
    "INSERT INTO servers (hostname, ip, cpu_cores, memory_gb) VALUES (?, ?, ?, ?)",
    servers
)
conn.commit()

# 查询
cursor.execute("SELECT * FROM servers WHERE status = ?", ("active",))
rows = cursor.fetchall()
for row in rows:
    print(row)

# 更新
cursor.execute("UPDATE servers SET memory_gb = ? WHERE hostname = ?", (64, "web01"))
conn.commit()

# 删除
cursor.execute("DELETE FROM servers WHERE status = ?", ("decommissioned",))
conn.commit()

conn.close()
```

### 2. 上下文管理器

```python
from contextlib import contextmanager

@contextmanager
def get_db(db_path="sre_data.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 字典式访问
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# 使用
with get_db() as db:
    cursor = db.execute("SELECT * FROM servers")
    for row in cursor:
        print(f"Host: {row['hostname']}, IP: {row['ip']}")
```

### 3. 实战：服务器资产管理系统

```python
#!/usr/bin/env python3
"""Simple server inventory system using SQLite."""
import sqlite3
import sys
from datetime import datetime

class Inventory:
    def __init__(self, db_path="inventory.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT UNIQUE NOT NULL,
                ip TEXT, env TEXT, role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def add(self, hostname, ip, env, role):
        self.conn.execute(
            "INSERT INTO servers (hostname, ip, env, role) VALUES (?, ?, ?, ?)",
            (hostname, ip, env, role)
        )
        self.conn.commit()

    def list_all(self, env=None):
        if env:
            rows = self.conn.execute(
                "SELECT * FROM servers WHERE env = ? ORDER BY hostname", (env,)
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM servers ORDER BY hostname").fetchall()
        for r in rows:
            print(f"  {r['hostname']:15s} {r['ip']:15s} {r['env']:8s} {r['role']}")

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    inv = Inventory()
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        inv.add(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        print(f"Added {sys.argv[2]}")
    else:
        print("All servers:")
        inv.list_all()
    inv.close()
```
""" + gen_footer(["sqlite3 文档", "SQL 教程"])

# Day 50
files["day50-并发编程.md"] = gen_header(50, "Python 并发编程") + """
- 理解 threading 和 multiprocessing 的区别
- 掌握 ThreadPoolExecutor 和 ProcessPoolExecutor
- 理解 GIL 对并发编程的影响
- 能在 SRE 工具中正确使用并发

---

## 📖 详细知识点

### 1. 线程 vs 进程

| 特性 | threading | multiprocessing |
|------|-----------|-----------------|
| 并发单位 | 线程 | 进程 |
| GIL 影响 | 受影响（CPU 密集无效） | 不受影响 |
| 内存共享 | 是 | 否（需要 IPC） |
| 适用场景 | I/O 密集 | CPU 密集 |
| 开销 | 小 | 大 |

### 2. ThreadPoolExecutor

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

def check_url(url):
    try:
        resp = requests.get(url, timeout=5)
        return url, resp.status_code, True
    except Exception as e:
        return url, None, False

urls = [
    "https://google.com",
    "https://github.com",
    "https://example.com",
]

# 并发检查
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(check_url, u): u for u in urls}
    for future in as_completed(futures):
        url, status, ok = future.result()
        print(f"{'OK' if ok else 'FAIL'} {url} {status}")
```

### 3. ProcessPoolExecutor

```python
from concurrent.futures import ProcessPoolExecutor
import hashlib

def compute_hash(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return filepath, h.hexdigest()

files = ["/var/log/syslog", "/etc/passwd", "/etc/hosts"]

with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(compute_hash, f) for f in files]
    for future in as_completed(futures):
        path, hash_val = future.result()
        print(f"{path}: {hash_val[:16]}...")
```

### 4. 实战：并发端口扫描

```python
#!/usr/bin/env python3
"""Concurrent port scanner."""
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

def scan_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        result = s.connect_ex((host, port))
        return port, result == 0

def scan(host, ports, max_workers=50):
    open_ports = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(scan_port, host, p): p for p in ports}
        for future in as_completed(futures):
            port, is_open = future.result()
            if is_open:
                open_ports.append(port)
    return sorted(open_ports)

if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    ports = range(1, 1025)
    print(f"Scanning {host}...")
    open_ports = scan(host, ports)
    print(f"Open ports: {open_ports}")
```
""" + gen_footer(["concurrent.futures 文档", "Python GIL 解释"])

# Day 51
files["day51-CLI工具开发.md"] = gen_header(51, "Python CLI 工具开发") + """
- 掌握 argparse 和 click 构建命令行工具
- 理解 CLI 工具的设计原则
- 能编写实用的 SRE CLI 工具

---

## 📖 详细知识点

### 1. argparse

```python
import argparse

parser = argparse.ArgumentParser(description="Server health checker")
parser.add_argument("host", help="Target host")
parser.add_argument("-p", "--ports", type=int, nargs="+", default=[80, 443], help="Ports to check")
parser.add_argument("-t", "--timeout", type=float, default=5.0, help="Connection timeout")
parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

args = parser.parse_args()
print(f"Checking {args.host} on ports {args.ports}")
```

### 2. click

```python
# pip install click
import click

@click.command()
@click.argument("host")
@click.option("-p", "--ports", multiple=True, default=[80, 443], help="Ports")
@click.option("-t", "--timeout", default=5.0, help="Timeout")
@click.option("-v", "--verbose", is_flag=True)
def check(host, ports, timeout, verbose):
    """Check server health on specified ports."""
    for port in ports:
        if verbose:
            click.echo(f"Checking {host}:{port}...")
        # check logic
        click.echo(f"{'OK' if True else 'FAIL'} {host}:{port}")

if __name__ == "__main__":
    check()
```

### 3. 实战：日志分析 CLI

```python
#!/usr/bin/env python3
"""Analyze log files from the command line."""
import argparse
import re
from collections import Counter

def analyze(filepath, pattern, top=10):
    counts = Counter()
    with open(filepath) as f:
        for line in f:
            m = re.search(pattern, line)
            if m:
                counts[m.group(1)] += 1
    return counts.most_common(top)

def main():
    parser = argparse.ArgumentParser(description="Log file analyzer")
    parser.add_argument("file", help="Log file path")
    parser.add_argument("-p", "--pattern", default=r'(\d+\.\d+\.\d+\.\d+)', help="Regex pattern")
    parser.add_argument("-n", "--top", type=int, default=10, help="Top N results")
    args = parser.parse_args()

    results = analyze(args.file, args.pattern, args.top)
    for item, count in results:
        print(f"{count:8d}  {item}")

if __name__ == "__main__":
    main()
```
""" + gen_footer(["argparse 文档", "click 文档"])

# Day 52
files["day52-装饰器与高级技巧.md"] = gen_header(52, "Python 装饰器与高级技巧") + """
- 理解装饰器的原理和编写方法
- 掌握上下文管理器、生成器、迭代器
- 能在 SRE 工具中应用高级 Python 特性

---

## 📖 详细知识点

### 1. 装饰器原理

```python
import functools
import time

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.3f}s")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(1)
    return "done"
```

### 2. 带参数的装饰器

```python
def retry(max_attempts=3, delay=1, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry(max_attempts=3, delay=2)
def fetch_api(url):
    return requests.get(url).json()
```

### 3. 生成器

```python
# 惰性求值，节省内存
def read_large_file(filepath):
    with open(filepath) as f:
        for line in f:
            yield line.strip()

# 使用
for line in read_large_file("/var/log/syslog"):
    if "ERROR" in line:
        process(line)

# 生成器表达式
total = sum(x*x for x in range(1000000))  # 不占用大量内存
```

### 4. 上下文管理器

```python
from contextlib import contextmanager

@contextmanager
def temp_dir():
    path = tempfile.mkdtemp()
    try:
        yield path
    finally:
        shutil.rmtree(path)

with temp_dir() as d:
    # 使用临时目录
    # 退出时自动清理
    pass
```
""" + gen_footer(["Python 装饰器教程", "生成器与迭代器文档"])

# Day 53
files["day53-面向对象设计（SRE工具架构）.md"] = gen_header(53, "Python 面向对象设计与 SRE 工具架构") + """
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
""" + gen_footer(["Python OOP 指南", "Design Patterns in Python"])

# Day 54
files["day54-实战项目：主机监控系统（Python版）.md"] = gen_header(54, "实战项目：主机监控系统（Python 版）") + """
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
import json
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
            "INSERT INTO metrics (cpu_percent, memory_percent, disk_percent, network_sent, network_recv) VALUES (?, ?, ?, ?, ?)",
            (data["cpu_percent"], data["memory_percent"], data["disk_percent"], data["network_sent"], data["network_recv"])
        )
        self.conn.commit()
        return data

    def get_latest(self, limit=10):
        rows = self.conn.execute(
            "SELECT * FROM metrics ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(zip(["id", "timestamp", "cpu", "mem", "disk", "net_sent", "net_recv"], r)) for r in rows]

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    m = Monitor()
    try:
        while True:
            data = m.collect()
            print(f"CPU: {data['cpu_percent']}%  MEM: {data['memory_percent']}%  DISK: {data['disk_percent']}%")
            time.sleep(5)
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        m.close()
```
""" + gen_footer(["psutil 文档", "SQLite 文档"])

# Day 55
files["day55-实战项目：批量管理工具.md"] = gen_header(55, "实战项目：批量服务器管理工具") + """
- 综合运用 Python 网络编程知识构建批量管理工具
- 实现 SSH 批量执行、文件批量分发
- 掌握并发执行和错误处理

---

## 📖 详细知识点

### 1. SSH 批量执行

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import paramiko

def ssh_exec(host, command, username="root", timeout=10):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=username, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        return host, exit_code, output, ""
    except Exception as e:
        return host, -1, "", str(e)
    finally:
        client.close()

# 批量执行
hosts = ["10.0.1.10", "10.0.1.11", "10.0.2.10"]
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(ssh_exec, h, "uptime"): h for h in hosts}
    for future in as_completed(futures):
        host, code, output, error = future.result()
        if error:
            print(f"FAIL {host}: {error}")
        else:
            print(f"OK {host}: {output.strip()}")
```

### 2. 文件批量分发

```python
def ssh_scp(host, local_path, remote_path, username="root"):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username)
    sftp = client.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    client.close()
```
""" + gen_footer(["paramiko 文档", "并发最佳实践"])

# Day 56
files["day56-理论测试：GIL、threadingvsmultiprocessing.md"] = gen_header(56, "理论测试：GIL、threading vs multiprocessing") + """
- 理解 GIL 的本质和影响
- 能正确选择 threading 或 multiprocessing
- 掌握并发编程的常见陷阱

---

## 📖 GIL 详解

### 1. 什么是 GIL

GIL（Global Interpreter Lock）是 CPython 中的一个互斥锁，确保同一时刻只有一个线程执行 Python 字节码。

```
为什么需要 GIL？
- CPython 的内存管理不是线程安全的
- GIL 简化了 C 扩展的实现
- 代价：多线程不能真正并行执行 CPU 密集型任务
```

### 2. GIL 的影响

```python
# CPU 密集型 - threading 无效（受 GIL 限制）
import threading
import time

def cpu_work():
    x = 0
    for i in range(10**7):
        x += i

# 串行
start = time.time()
cpu_work()
cpu_work()
print(f"Serial: {time.time()-start:.2f}s")

# 多线程（不会更快！）
start = time.time()
t1 = threading.Thread(target=cpu_work)
t2 = threading.Thread(target=cpu_work)
t1.start(); t2.start()
t1.join(); t2.join()
print(f"Thread: {time.time()-start:.2f}s")  # 差不多甚至更慢

# 多进程（会更快）
import multiprocessing
start = time.time()
p1 = multiprocessing.Process(target=cpu_work)
p2 = multiprocessing.Process(target=cpu_work)
p1.start(); p2.start()
p1.join(); p2.join()
print(f"Process: {time.time()-start:.2f}s")  # 快约 2 倍
```

### 3. 选择指南

| 场景 | 推荐 | 原因 |
|------|------|------|
| HTTP 请求 | ThreadPoolExecutor | I/O 密集，GIL 在等待时释放 |
| 文件读写 | ThreadPoolExecutor | I/O 密集 |
| 数据库查询 | ThreadPoolExecutor | I/O 密集 |
| 数据处理 | ProcessPoolExecutor | CPU 密集，绕过 GIL |
| 加密计算 | ProcessPoolExecutor | CPU 密集 |
| 图像处理 | ProcessPoolExecutor | CPU 密集 |

### 4. 绕过 GIL 的方法

1. 使用 multiprocessing（每个进程有自己的 GIL）
2. 使用 C 扩展（numpy、scipy 等在 C 层释放 GIL）
3. 使用其他 Python 实现（PyPy STM、Jython）
4. Python 3.13+ 的 free-threading 实验功能
""" + gen_footer(["GIL 官方 Wiki", "David Beazley - GIL 演讲"])

# 写入所有文件
for fname, content in files.items():
    write_md(fname, content)

print(f"\nDone: generated {len(files)} files")
