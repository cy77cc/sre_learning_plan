# Day 46: Python 函数、日志模块与异常处理

> 📅 日期：2026-05-02
> 📖 学习主题：Python 函数、日志模块与异常处理
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

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

---

## 🏗️ 实战：带重试的 API 客户端

```python
#!/usr/bin/env python3
"""API client with retry, logging, and custom exceptions."""

import logging
import time
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API exception."""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass


def api_call(url, max_retries=3, timeout=5):
    """Make API call with retry and logging."""
    for attempt in range(max_retries):
        try:
            logger.info(f"Request {url} (attempt {attempt + 1})")
            resp = requests.get(url, timeout=timeout)

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            logger.info(f"Success: {resp.status_code}")
            return resp.json()

        except requests.Timeout:
            logger.error(f"Timeout on attempt {attempt + 1}")
        except requests.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise APIError(str(e))
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")

        if attempt < max_retries - 1:
            wait = 2 ** attempt
            logger.info(f"Retrying in {wait}s...")
            time.sleep(wait)

    raise APIError(f"Failed after {max_retries} attempts")


if __name__ == "__main__":
    data = api_call("https://api.example.com/data")
    print(data)
```

---

## 🧪 练习题

### 练习 1：日志轮转配置

配置 logging 模块，实现每天一个日志文件，保留 7 天。

<details>
<summary>答案</summary>

```python
import logging
from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler(
    "app.log", when="midnight", backupCount=7
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
))

logger = logging.getLogger()
logger.addHandler(handler)
```
</details>

---

## 🧪 练习题

### 练习 1：带超时的装饰器

编写一个装饰器，为函数添加超时控制。

<details>
<summary>答案</summary>

```python
import signal

def timeout(seconds):
    def decorator(func):
        def handler(signum, frame):
            raise TimeoutError(f"Function timed out after {seconds}s")
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wrapper
    return decorator

@timeout(5)
def slow_operation():
    time.sleep(10)
```
</details>

---

## 📚 扩展阅读

- [Python logging 文档](https://docs.python.org/3/library/logging.html)
- [PEP 3134 - Exception Chaining](https://peps.python.org/pep-3134/)
