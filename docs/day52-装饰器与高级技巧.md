# Day 52: Python 装饰器与高级技巧

> 📅 日期：2026-05-02
> 📖 学习主题：Python 装饰器与高级技巧
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

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

### 5. LRU 缓存

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def dns_lookup(hostname):
    """Cache DNS lookups to avoid repeated queries."""
    import socket
    return socket.gethostbyname(hostname)

# 查看缓存统计
dns_lookup.cache_info()
# CacheInfo(hits=42, misses=10, maxsize=128, currsize=10)
```

---

## 🏗️ 实战：带缓存和重试的 API 客户端

```python
#!/usr/bin/env python3
"""API client with caching, retry, and timing."""

import time
import functools
import requests
from functools import lru_cache


def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__}: {elapsed:.3f}s")
        return result
    return wrapper


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


class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    @timer
    @retry(max_attempts=3)
    def get(self, endpoint, cache=True):
        url = f"{self.base_url}/{endpoint}"
        resp = self.session.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()


client = APIClient("https://api.example.com")
data = client.get("users/1")
```

---

## 🧪 练习题

### 练习 1：编写一个限流装饰器

限制函数每分钟最多调用 N 次。

<details>
<summary>答案</summary>

```python
import time
from collections import deque

def rate_limit(max_calls, period=60):
    def decorator(func):
        calls = deque()
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            while calls and calls[0] < now - period:
                calls.popleft()
            if len(calls) >= max_calls:
                raise Exception("Rate limit exceeded")
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=5, period=60)
def api_call():
    pass
```
</details>

---

## 📚 扩展阅读

- [Python 装饰器教程](https://realpython.com/primer-on-python-decorators/)
- [生成器与迭代器文档](https://docs.python.org/3/howto/functional.html#generators)
- [contextlib 文档](https://docs.python.org/3/library/contextlib.html)
