# Day 46: 函数、日志模块与异常处理

> 📅 日期：2026-05-03
> 📖 学习主题：Python 函数高级特性、logging 模块架构、自定义异常、traceback、上下文管理器
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 43 Python 环境搭建, Day 44 数据类型, Day 45 系统命令与文件操作

## 🎯 学习目标

- 掌握 Python 函数的高级特性（装饰器、闭包、生成器、lambda）
- 深入理解 logging 模块的架构设计，能搭建生产级日志系统
- 掌握自定义异常体系和 traceback 处理，编写健壮的 SRE 工具
- 熟练使用上下文管理器（with 语句）管理资源生命周期

---

## 📖 核心知识点

### 1. 函数高级特性

#### 1.1 装饰器（Decorator）— SRE 最常用的模式

```
┌─────────────────────────────────────────────────────────────────┐
│                    装饰器工作原理                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  @decorator              等价于    def func(): ...              │
│  def func(): ...                  func = decorator(func)        │
│                                                                 │
│  装饰器本质：接受函数作为参数，返回新函数                        │
│                                                                 │
│  执行流程:                                                      │
│  1. 定义阶段: decorator(func) 被调用，返回 wrapper              │
│  2. 调用阶段: wrapper() 被调用，内部调用原函数                   │
│                                                                 │
│  SRE 用途:                                                      │
│    - 重试机制（网络请求失败自动重试）                           │
│    - 计时器（统计函数执行时间）                                 │
│    - 权限检查（操作前验证权限）                                 │
│    - 缓存（避免重复计算）                                       │
│    - 日志记录（记录函数调用）                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

```python
import time
import functools
import logging
from typing import Any, Callable, TypeVar, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ============================================
# 装饰器 1: 重试机制
# ============================================

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable[[F], F]:
    """
    重试装饰器 — SRE 网络请求必备

    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避系数（每次重试延迟翻倍）
        exceptions: 需要重试的异常类型

    Usage:
        @retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        def fetch_metrics():
            return requests.get("http://prometheus:9090/api/v1/query")
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for "
                            f"{func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for "
                            f"{func.__name__}: {e}"
                        )

            raise last_exception  # type: ignore

        return wrapper  # type: ignore
    return decorator


# ============================================
# 装饰器 2: 执行计时
# ============================================

def timer(func: F) -> F:
    """
    计时装饰器 — 统计函数执行时间

    SRE 用途：性能监控、慢查询检测
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.perf_counter() - start
            logger.info(f"{func.__name__} took {duration:.3f}s")
            # 超过阈值告警
            if duration > 10:
                logger.warning(
                    f"Slow function: {func.__name__} took {duration:.3f}s"
                )
    return wrapper  # type: ignore


# ============================================
# 装饰器 3: 缓存（简化版 LRU Cache）
# ============================================

def cached(ttl_seconds: int = 300) -> Callable[[F], F]:
    """
    带 TTL 的缓存装饰器

    SRE 用途：缓存不常变化的数据（服务列表、配置等）

    Args:
        ttl_seconds: 缓存过期时间（秒）
    """
    def decorator(func: F) -> F:
        cache: dict[str, tuple[Any, float]] = {}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            key = str(args) + str(sorted(kwargs.items()))
            now = time.time()

            # 检查缓存
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result

            # 缓存未命中，执行函数
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            logger.debug(f"Cache miss for {func.__name__}")
            return result

        # 添加清除缓存的方法
        wrapper.clear_cache = lambda: cache.clear()  # type: ignore
        return wrapper  # type: ignore
    return decorator


# ============================================
# 装饰器 4: 限流（Rate Limiter）
# ============================================

def rate_limit(calls_per_second: float = 1.0) -> Callable[[F], F]:
    """
    限流装饰器 — 控制函数调用频率

    SRE 用途：API 调用限流、防止被上游封禁
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_called[0] = time.time()
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


# ============================================
# 装饰器组合使用
# ============================================

@retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError, TimeoutError))
@timer
@cached(ttl_seconds=60)
def fetch_service_health(host: str, port: int = 8080) -> dict:
    """
    获取服务健康状态 — 组合了重试、计时、缓存三个装饰器

    执行顺序: retry → timer → cached → fetch_service_health
    """
    import requests
    url = f"http://{host}:{port}/health"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()
```

#### 1.2 闭包（Closure）

```python
from typing import Callable, Any


# ============================================
# 闭包基础 — 函数记住外部变量
# ============================================

def make_counter(start: int = 0) -> Callable[[], int]:
    """
    创建计数器闭包

    SRE 用途：创建独立的计数器实例（如每个服务的请求计数）
    """
    count = start

    def counter() -> int:
        nonlocal count  # 声明使用外部变量
        count += 1
        return count

    return counter


# 使用
request_counter = make_counter()
print(request_counter())  # 1
print(request_counter())  # 2
print(request_counter())  # 3

# 每个闭包实例独立
error_counter = make_counter()
print(error_counter())  # 1（不受 request_counter 影响）


# ============================================
# SRE 实战：带配置的告警函数工厂
# ============================================

def make_alert_func(
    webhook_url: str,
    channel: str = "#sre-alerts",
    severity: str = "WARNING",
) -> Callable[[str, str], bool]:
    """
    创建告警发送函数 — 闭包封装配置

    Args:
        webhook_url: Webhook URL
        channel: 告警频道
        severity: 默认严重级别

    Returns:
        告警发送函数
    """
    import requests

    def send_alert(message: str, override_severity: str = "") -> bool:
        """
        发送告警

        Args:
            message: 告警消息
            override_severity: 覆盖默认严重级别

        Returns:
            是否发送成功
        """
        effective_severity = override_severity or severity
        payload = {
            "channel": channel,
            "severity": effective_severity,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False

    return send_alert


# 使用
send_critical_alert = make_alert_func(
    webhook_url="https://hooks.slack.com/xxx",
    channel="#sre-critical",
    severity="CRITICAL",
)

send_warning_alert = make_alert_func(
    webhook_url="https://hooks.slack.com/xxx",
    channel="#sre-warnings",
    severity="WARNING",
)
```

#### 1.3 生成器（Generator）

```python
from typing import Generator, Iterator, Any, Optional
from pathlib import Path
import json


# ============================================
# 生成器基础 — 惰性求值
# ============================================

def fibonacci() -> Generator[int, None, None]:
    """
    斐波那契数列生成器

    生成器特点：
    1. 惰性求值 — 只在需要时计算下一个值
    2. 内存高效 — 不需要一次性存储所有值
    3. 可迭代 — 可以用 for 循环遍历
    """
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


# 使用
fib = fibonacci()
for _ in range(10):
    print(next(fib), end=" ")  # 0 1 1 2 3 5 8 13 21 34


# ============================================
# SRE 实战：流式读取大日志文件
# ============================================

def stream_log_file(
    path: Path,
    pattern: Optional[str] = None,
    tail: bool = False,
) -> Generator[str, None, None]:
    """
    流式读取日志文件 — 内存高效

    Args:
        path: 日志文件路径
        pattern: 过滤模式（可选）
        tail: 是否从末尾开始读取

    Yields:
        每一行日志
    """
    import re

    compiled_pattern = re.compile(pattern) if pattern else None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        if tail:
            # 移动到文件末尾附近
            f.seek(0, 2)  # 移到末尾
            file_size = f.tell()
            f.seek(max(0, file_size - 1024 * 1024))  # 最后 1MB

        for line in f:
            line = line.rstrip("\n")
            if compiled_pattern and not compiled_pattern.search(line):
                continue
            yield line


# 使用示例：流式分析错误日志
def analyze_errors(log_path: Path) -> dict:
    """分析日志中的错误"""
    error_count = 0
    errors_by_type: dict[str, int] = {}

    for line in stream_log_file(log_path, pattern=r"ERROR|CRITICAL"):
        error_count += 1
        # 提取错误类型
        if "ConnectionError" in line:
            errors_by_type["ConnectionError"] = errors_by_type.get("ConnectionError", 0) + 1
        elif "TimeoutError" in line:
            errors_by_type["TimeoutError"] = errors_by_type.get("TimeoutError", 0) + 1
        else:
            errors_by_type["Other"] = errors_by_type.get("Other", 0) + 1

    return {
        "total_errors": error_count,
        "by_type": errors_by_type,
    }


# ============================================
# 生成器管道 — 组合多个生成器
# ============================================

def read_lines(path: Path) -> Generator[str, None, None]:
    """读取文件行"""
    with open(path, "r") as f:
        for line in f:
            yield line.rstrip("\n")


def filter_lines(
    lines: Generator[str, None, None],
    pattern: str,
) -> Generator[str, None, None]:
    """过滤行"""
    import re
    compiled = re.compile(pattern)
    for line in lines:
        if compiled.search(line):
            yield line


def parse_log_lines(
    lines: Generator[str, None, None],
) -> Generator[dict, None, None]:
    """解析日志行"""
    import re
    pattern = re.compile(
        r'(?P<timestamp>\S+ \S+) '
        r'(?P<level>\w+) '
        r'(?P<message>.*)'
    )
    for line in lines:
        m = pattern.match(line)
        if m:
            yield m.groupdict()


def process_log_file(path: Path) -> Generator[dict, None, None]:
    """日志处理管道"""
    lines = read_lines(path)
    error_lines = filter_lines(lines, r"ERROR|CRITICAL")
    parsed = parse_log_lines(error_lines)
    yield from parsed


# 使用
for entry in process_log_file(Path("/var/log/app.log")):
    print(entry)
```

#### 1.4 Lambda 与高阶函数

```python
from typing import List, Dict, Any, Callable
from functools import reduce


# ============================================
# Lambda — 匿名函数
# ============================================

# 简单的 lambda
square = lambda x: x ** 2
add = lambda x, y: x + y

# SRE 场景：排序和过滤
servers = [
    {"name": "web-01", "cpu": 85.5, "memory": 72.3},
    {"name": "web-02", "cpu": 45.2, "memory": 88.1},
    {"name": "api-01", "cpu": 92.1, "memory": 65.4},
    {"name": "api-02", "cpu": 38.7, "memory": 55.2},
]

# 按 CPU 使用率排序
sorted_servers = sorted(servers, key=lambda s: s["cpu"], reverse=True)

# 过滤高负载服务器
high_cpu = list(filter(lambda s: s["cpu"] > 80, servers))
high_memory = list(filter(lambda s: s["memory"] > 80, servers))

# ============================================
# map / filter / reduce
# ============================================

# map — 转换每个元素
hostnames = list(map(lambda s: s["name"], servers))

# filter — 过滤元素
critical = list(filter(lambda s: s["cpu"] > 90 or s["memory"] > 90, servers))

# reduce — 累积计算
total_cpu = reduce(lambda acc, s: acc + s["cpu"], servers, 0)
avg_cpu = total_cpu / len(servers)


# ============================================
# SRE 实战：告警规则引擎
# ============================================

AlertRule = Callable[[Dict[str, Any]], Optional[str]]


def make_threshold_rule(
    metric: str,
    threshold: float,
    operator: str = ">",
    severity: str = "WARNING",
) -> AlertRule:
    """
    创建阈值告警规则

    Args:
        metric: 指标名称
        threshold: 阈值
        operator: 比较运算符 (>, <, >=, <=, ==)
        severity: 告警级别
    """
    operators = {
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
    }
    compare = operators[operator]

    def rule(data: Dict[str, Any]) -> Optional[str]:
        value = data.get(metric)
        if value is not None and compare(value, threshold):
            return f"[{severity}] {metric}={value} {operator} {threshold}"
        return None

    return rule


def evaluate_rules(
    data: Dict[str, Any],
    rules: List[AlertRule],
) -> List[str]:
    """评估所有告警规则"""
    alerts = []
    for rule in rules:
        alert = rule(data)
        if alert:
            alerts.append(alert)
    return alerts


# 定义告警规则
alert_rules = [
    make_threshold_rule("cpu_usage", 90, ">", "CRITICAL"),
    make_threshold_rule("memory_usage", 85, ">", "WARNING"),
    make_threshold_rule("disk_usage", 95, ">", "CRITICAL"),
    make_threshold_rule("error_rate", 0.05, ">", "WARNING"),
    make_threshold_rule("response_time_ms", 5000, ">", "CRITICAL"),
]

# 评估
metrics = {
    "cpu_usage": 92.5,
    "memory_usage": 78.3,
    "disk_usage": 45.2,
    "error_rate": 0.08,
    "response_time_ms": 2300,
}

alerts = evaluate_rules(metrics, alert_rules)
for alert in alerts:
    print(alert)
# [CRITICAL] cpu_usage=92.5 > 90
# [WARNING] error_rate=0.08 > 0.05
```

---

### 2. logging 模块 — 生产级日志系统

#### 2.1 logging 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python logging 模块架构                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Logger (日志器)                                                │
│    │  产生日志记录                                              │
│    │  层级命名: root > sre > sre.health > sre.health.check      │
│    │  级别: DEBUG < INFO < WARNING < ERROR < CRITICAL           │
│    ▼                                                            │
│  Filter (过滤器) — 可选                                         │
│    │  按条件过滤日志记录                                        │
│    ▼                                                            │
│  Handler (处理器)                                               │
│    │  将日志发送到目标                                          │
│    │  StreamHandler → 控制台                                    │
│    │  FileHandler → 文件                                        │
│    │  RotatingFileHandler → 轮转文件                            │
│    │  SyslogHandler → syslog                                    │
│    │  HTTPHandler → HTTP 端点                                   │
│    ▼                                                            │
│  Formatter (格式器)                                             │
│       定义日志输出格式                                          │
│       %(asctime)s %(levelname)s %(name)s %(message)s            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 Logger 层级设计

```python
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    app_name: str = "sre-toolkit",
    json_format: bool = False,
) -> logging.Logger:
    """
    设置生产级日志系统

    Args:
        log_level: 日志级别
        log_dir: 日志文件目录（None 则只输出到控制台）
        app_name: 应用名称
        json_format: 是否使用 JSON 格式

    Returns:
        根 Logger
    """
    # 获取根 Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 清除已有的 Handler（避免重复添加）
    root_logger.handlers.clear()

    # 创建 Formatter
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件 Handler（如果指定了日志目录）
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

        # 应用日志 — 轮转文件
        app_log_path = log_dir / f"{app_name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            app_log_path,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # 错误日志 — 只记录 ERROR 及以上
        error_log_path = log_dir / f"{app_name}.error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_path,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

    return root_logger


class JsonFormatter(logging.Formatter):
    """
    JSON 格式的日志格式器

    SRE 用途：结构化日志，便于 ELK/Loki 等日志系统解析
    """

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }

        # 添加异常信息
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # 添加额外字段
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)
```

#### 2.3 Logger 使用最佳实践

```python
import logging
from typing import Any


# ============================================
# 获取 Logger — 使用模块名
# ============================================

# 每个模块使用自己的 Logger
logger = logging.getLogger(__name__)
# __name__ 会是 "sre_toolkit.health.checker" 这样的层级名


# ============================================
# 日志级别使用规范
# ============================================

def process_request(request: dict) -> None:
    """演示各级别日志的使用场景"""

    # DEBUG — 开发调试信息，生产环境通常关闭
    logger.debug(f"Processing request: {request}")

    # INFO — 关键业务流程记录
    logger.info(f"Request received: {request.get('path')}")

    # WARNING — 异常但不影响核心功能
    if request.get("timeout", 5) > 30:
        logger.warning(f"Unusual timeout value: {request['timeout']}s")

    # ERROR — 错误，功能受影响
    try:
        result = call_external_api(request)
    except ConnectionError as e:
        logger.error(f"Failed to call external API: {e}", exc_info=True)

    # CRITICAL — 严重错误，系统可能不可用
    if not database_is_healthy():
        logger.critical("Database connection lost! Service degraded.")


# ============================================
# Logger 层级 — 控制不同模块的日志级别
# ============================================

def configure_module_loggers() -> None:
    """配置不同模块的日志级别"""

    # 第三方库 — 只记录 WARNING 及以上
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    # 业务模块 — 按需配置
    logging.getLogger("sre_toolkit.health").setLevel(logging.DEBUG)
    logging.getLogger("sre_toolkit.metrics").setLevel(logging.INFO)
    logging.getLogger("sre_toolkit.alerts").setLevel(logging.INFO)


# ============================================
# SRE 实战：带上下文的日志适配器
# ============================================

class ContextLogger(logging.LoggerAdapter):
    """
    带上下文的 Logger — 自动添加请求 ID、主机名等字段

    SRE 用途：分布式追踪、请求链路关联
    """

    def process(self, msg: str, kwargs: dict) -> tuple:
        # 将 extra 信息添加到日志记录
        extra = self.extra.copy()
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"]["extra_data"] = extra
        return msg, kwargs


# 使用示例
def handle_request(request_id: str, host: str) -> None:
    """处理请求 — 使用带上下文的 Logger"""
    logger = ContextLogger(
        logging.getLogger(__name__),
        {"request_id": request_id, "host": host},
    )

    logger.info("Request started")
    # 输出: 2026-05-03 10:00:00 INFO [sre_toolkit] Request started
    # JSON 中会包含: {"request_id": "abc-123", "host": "web-01"}

    try:
        # 处理逻辑
        logger.debug("Processing step 1")
        result = do_something()
        logger.info(f"Request completed: {result}")
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
```

#### 2.4 结构化日志 — structlog

```python
# structlog 是 Python 最流行的结构化日志库
# pip install structlog

import structlog
from typing import Any


def setup_structlog() -> None:
    """配置 structlog"""
    structlog.configure(
        processors=[
            # 添加时间戳
            structlog.processors.TimeStamper(fmt="iso"),
            # 添加日志级别
            structlog.processors.add_log_level,
            # 格式化堆栈信息
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # JSON 输出
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )


def demo_structlog() -> None:
    """structlog 使用示例"""
    log = structlog.get_logger()

    # 基础日志
    log.info("Server started", host="web-01", port=8080)

    # 绑定上下文 — 后续日志自动携带
    request_log = log.bind(request_id="abc-123", user_id="user-456")
    request_log.info("Request received", path="/api/health")
    request_log.info("Request completed", status=200, duration_ms=45)

    # 异常日志
    try:
        raise ValueError("Something went wrong")
    except ValueError:
        log.error("Operation failed", exc_info=True)


# SRE 实战：请求处理日志
def process_api_request(request_id: str, method: str, path: str) -> None:
    """处理 API 请求 — 带完整上下文的日志"""
    log = structlog.get_logger().bind(
        request_id=request_id,
        method=method,
        path=path,
    )

    log.info("Request started")

    # 认证
    log.debug("Authenticating request")
    user = authenticate_request(request_id)
    log = log.bind(user_id=user["id"])

    # 业务逻辑
    log.debug("Processing business logic")
    result = process_business_logic(user, path)

    # 响应
    log.info(
        "Request completed",
        status=200,
        response_size=len(str(result)),
    )
```

---

### 3. 异常处理

#### 3.1 异常体系

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python 异常层级                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BaseException                                                  │
│  ├── KeyboardInterrupt     (Ctrl+C)                            │
│  ├── SystemExit            (sys.exit())                        │
│  └── Exception             (所有用户异常的基类)                  │
│      ├── ValueError        (值错误)                            │
│      ├── TypeError         (类型错误)                          │
│      ├── KeyError          (字典键不存在)                       │
│      ├── IndexError        (列表索引越界)                       │
│      ├── AttributeError    (属性不存在)                         │
│      ├── OSError           (系统错误)                          │
│      │   ├── FileNotFoundError                                  │
│      │   ├── PermissionError                                    │
│      │   ├── ConnectionError                                    │
│      │   └── TimeoutError                                       │
│      ├── RuntimeError      (运行时错误)                         │
│      ├── IOError           (I/O 错误，别名 OSError)             │
│      └── 自定义异常...                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 自定义异常体系

```python
from typing import Optional, Any, Dict


# ============================================
# SRE 工具异常层级设计
# ============================================

class SREError(Exception):
    """
    SRE 工具基础异常类

    所有 SRE 工具的自定义异常都应该继承此类
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志或 API 响应）"""
        result = {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }
        if self.original_exception:
            result["original_error"] = {
                "type": self.original_exception.__class__.__name__,
                "message": str(self.original_exception),
            }
        return result


# 配置相关异常
class ConfigError(SREError):
    """配置错误基类"""
    pass


class ConfigNotFoundError(ConfigError):
    """配置文件不存在"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证失败"""
    pass


class ConfigParseError(ConfigError):
    """配置解析失败"""
    pass


# 连接相关异常
class ConnectionError(SREError):
    """连接错误基类"""
    pass


class ServiceUnavailableError(ConnectionError):
    """服务不可用"""
    pass


class AuthenticationError(ConnectionError):
    """认证失败"""
    pass


class TimeoutError(SREError):
    """超时错误"""
    pass


# 操作相关异常
class OperationError(SREError):
    """操作失败基类"""
    pass


class DeploymentError(OperationError):
    """部署失败"""
    pass


class RollbackError(OperationError):
    """回滚失败"""
    pass


class HealthCheckError(OperationError):
    """健康检查失败"""
    pass


# ============================================
# 使用示例
# ============================================

def deploy_service(service_name: str, version: str) -> None:
    """
    部署服务 — 使用自定义异常

    SRE 场景：自动化部署，异常时提供详细的错误信息
    """
    try:
        # 检查配置
        config = load_config(service_name)
    except FileNotFoundError as e:
        raise ConfigNotFoundError(
            f"Configuration not found for service: {service_name}",
            details={"service": service_name, "version": version},
            original_exception=e,
        )

    # 验证配置
    if "image" not in config:
        raise ConfigValidationError(
            f"Missing 'image' in configuration",
            details={"service": service_name, "config_keys": list(config.keys())},
        )

    # 执行部署
    try:
        update_deployment(service_name, config["image"], version)
    except Exception as e:
        raise DeploymentError(
            f"Failed to deploy {service_name}:{version}",
            details={
                "service": service_name,
                "version": version,
                "image": config["image"],
            },
            original_exception=e,
        )

    # 健康检查
    try:
        wait_for_healthy(service_name, timeout=120)
    except Exception as e:
        # 部署后健康检查失败，尝试回滚
        try:
            rollback(service_name)
        except Exception as rollback_e:
            raise RollbackError(
                f"Health check failed AND rollback failed for {service_name}",
                details={
                    "service": service_name,
                    "health_error": str(e),
                    "rollback_error": str(rollback_e),
                },
            )
        raise HealthCheckError(
            f"Service {service_name} failed health check after deployment, rolled back",
            details={"service": service_name, "error": str(e)},
            original_exception=e,
        )
```

#### 3.3 traceback 处理

```python
import traceback
import sys
import logging
from typing import Optional
from datetime import datetime


logger = logging.getLogger(__name__)


def get_traceback_str(exc: Exception) -> str:
    """
    获取异常的完整 traceback 字符串

    SRE 用途：记录到日志、发送到错误追踪系统
    """
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def log_exception(
    exc: Exception,
    context: Optional[dict] = None,
    level: int = logging.ERROR,
) -> None:
    """
    记录异常到日志 — 带上下文信息

    Args:
        exc: 异常对象
        context: 上下文信息
        level: 日志级别
    """
    extra_info = {
        "exception_type": exc.__class__.__name__,
        "exception_message": str(exc),
    }
    if context:
        extra_info["context"] = context

    logger.log(
        level,
        f"Exception occurred: {exc.__class__.__name__}: {exc}",
        exc_info=True,
        extra={"extra_data": extra_info},
    )


class ErrorReporter:
    """
    错误报告器 — 收集和报告异常

    SRE 用途：
    1. 聚合相同类型的错误
    2. 控制告警频率（避免告警风暴）
    3. 提供错误统计
    """

    def __init__(self, max_errors: int = 1000) -> None:
        self._errors: list[dict] = []
        self._max_errors = max_errors
        self._error_counts: dict[str, int] = {}

    def report(
        self,
        exc: Exception,
        context: Optional[dict] = None,
        severity: str = "ERROR",
    ) -> None:
        """报告一个错误"""
        error_key = f"{exc.__class__.__name__}:{str(exc)[:100]}"

        # 更新计数
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

        # 记录错误详情
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": get_traceback_str(exc),
            "context": context,
            "count": self._error_counts[error_key],
        }

        self._errors.append(error_entry)

        # 限制内存使用
        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors:]

        # 记录日志
        log_exception(exc, context)

    def get_summary(self) -> dict:
        """获取错误统计摘要"""
        return {
            "total_errors": len(self._errors),
            "unique_types": len(self._error_counts),
            "top_errors": sorted(
                self._error_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10],
            "recent_errors": self._errors[-5:],
        }

    def clear(self) -> None:
        """清空错误记录"""
        self._errors.clear()
        self._error_counts.clear()
```

---

### 4. 上下文管理器（Context Manager）

#### 4.1 上下文管理器原理

```
┌─────────────────────────────────────────────────────────────────┐
│                    上下文管理器工作原理                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  with expression as variable:                                   │
│      body                                                       │
│                                                                 │
│  等价于:                                                        │
│  manager = expression.__enter__()                               │
│  variable = manager                                             │
│  try:                                                           │
│      body                                                       │
│  except:                                                        │
│      expression.__exit__(exc_type, exc_val, exc_tb)             │
│      如果 __exit__ 返回 True，异常被吞掉                        │
│      如果 __exit__ 返回 False/None，异常继续传播                │
│  else:                                                          │
│      expression.__exit__(None, None, None)                      │
│                                                                 │
│  SRE 用途:                                                      │
│    - 文件操作（确保文件关闭）                                   │
│    - 数据库连接（确保连接释放）                                 │
│    - 锁管理（确保锁释放）                                       │
│    - 计时器（确保时间统计）                                     │
│    - 临时环境（确保环境恢复）                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

```python
import time
import logging
from typing import Optional, Any, Type
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================
# 类实现上下文管理器
# ============================================

class TimerContext:
    """
    计时上下文管理器 — 统计代码块执行时间

    SRE 用途：性能分析、慢操作检测
    """

    def __init__(self, name: str, log_level: int = logging.INFO) -> None:
        self._name = name
        self._log_level = log_level
        self._start: float = 0
        self._duration: float = 0

    def __enter__(self) -> "TimerContext":
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self._duration = time.perf_counter() - self._start
        logger.log(
            self._log_level,
            f"[Timer] {self._name}: {self._duration:.3f}s"
        )

    @property
    def duration(self) -> float:
        return self._duration


# 使用
with TimerContext("database_query") as t:
    time.sleep(0.5)  # 模拟数据库查询
print(f"Query took {t.duration:.3f}s")


# ============================================
# contextmanager 装饰器 — 更简洁的实现
# ============================================

@contextmanager
def timer(name: str):
    """
    计时上下文管理器（使用 contextmanager 装饰器）

    更简洁的实现方式
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        logger.info(f"[Timer] {name}: {duration:.3f}s")


@contextmanager
def error_handler(operation: str, reraise: bool = True):
    """
    错误处理上下文管理器

    SRE 用途：统一的错误处理和日志记录

    Args:
        operation: 操作名称（用于日志）
        reraise: 是否重新抛出异常
    """
    try:
        yield
    except Exception as e:
        logger.error(
            f"Operation '{operation}' failed: {e}",
            exc_info=True,
        )
        if reraise:
            raise


@contextmanager
def cd(path: Path):
    """
    临时切换工作目录

    SRE 用途：在特定目录下执行操作
    """
    import os
    old_cwd = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old_cwd)


@contextmanager
def env_override(**kwargs: str):
    """
    临时覆盖环境变量

    SRE 用途：在特定环境下执行操作
    """
    import os
    old_values = {}
    try:
        for key, value in kwargs.items():
            old_values[key] = os.environ.get(key)
            os.environ[key] = value
        yield
    finally:
        for key, old_value in old_values.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


@contextmanager
def suppress_and_log(
    *exceptions: Type[Exception],
    logger_name: str = __name__,
    level: int = logging.WARNING,
):
    """
    抑制异常并记录日志

    SRE 用途：非关键操作失败时记录日志但不中断流程
    """
    try:
        yield
    except exceptions as e:
        logging.getLogger(logger_name).log(
            level,
            f"Suppressed exception: {e}",
            exc_info=True,
        )


# ============================================
# SRE 实战：数据库连接上下文管理器
# ============================================

class DatabaseConnection:
    """
    数据库连接上下文管理器

    确保：
    1. 连接正确建立
    2. 事务正确提交/回滚
    3. 连接正确关闭
    """

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        self._connection = None

    def __enter__(self):
        logger.debug(f"Connecting to database...")
        # self._connection = create_connection(self._connection_string)
        self._connection = {"connected": True}  # 模拟
        return self._connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Database operation failed: {exc_val}")
            # self._connection.rollback()
        else:
            # self._connection.commit()
            pass

        # self._connection.close()
        logger.debug("Database connection closed")
        return False  # 不抑制异常


# 使用
with DatabaseConnection("postgresql://localhost/sre") as conn:
    # 执行数据库操作
    pass
```

#### 4.2 组合使用：日志 + 异常 + 上下文管理器

```python
import logging
import time
from typing import Optional, Any
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


@contextmanager
def sre_operation(
    operation_name: str,
    log_start: bool = True,
    log_end: bool = True,
    reraise: bool = True,
):
    """
    SRE 操作上下文管理器 — 统一日志、计时、异常处理

    Args:
        operation_name: 操作名称
        log_start: 是否记录开始日志
        log_end: 是否记录结束日志
        reraise: 是否重新抛出异常

    Usage:
        with sre_operation("deploy_service"):
            deploy("web-app", "v1.2.3")
    """
    if log_start:
        logger.info(f"Starting operation: {operation_name}")

    start = time.perf_counter()
    try:
        yield
        duration = time.perf_counter() - start
        if log_end:
            logger.info(
                f"Operation completed: {operation_name} "
                f"(took {duration:.3f}s)"
            )
    except Exception as e:
        duration = time.perf_counter() - start
        logger.error(
            f"Operation failed: {operation_name} "
            f"(took {duration:.3f}s): {e}",
            exc_info=True,
        )
        if reraise:
            raise


# 使用示例
def deploy_application(service: str, version: str) -> None:
    """部署应用 — 使用 sre_operation 上下文管理器"""

    with sre_operation(f"pull_image({service}:{version})"):
        pull_docker_image(service, version)

    with sre_operation(f"update_config({service})"):
        update_service_config(service, version)

    with sre_operation(f"rolling_update({service})"):
        perform_rolling_update(service)

    with sre_operation(f"health_check({service})"):
        wait_for_healthy(service, timeout=120)

    with sre_operation(f"smoke_test({service})"):
        run_smoke_tests(service)

    logger.info(f"Deployment completed: {service}:{version}")
```

---

## 💻 实战练习

### 练习 1：基础操作 — 编写重试装饰器

**目标**：编写一个支持指数退避的重试装饰器

```python
"""
练习：编写重试装饰器

要求：
1. 支持配置最大重试次数
2. 支持指数退避
3. 支持指定需要重试的异常类型
4. 支持配置退避上限
5. 记录重试日志
"""
import time
import functools
import logging
from typing import TypeVar, Callable, Any, Tuple

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """带指数退避的重试装饰器"""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        actual_delay = min(delay, max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} "
                            f"failed for {func.__name__}: {e}. "
                            f"Retrying in {actual_delay:.1f}s..."
                        )
                        time.sleep(actual_delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed "
                            f"for {func.__name__}: {e}"
                        )

            raise last_exception  # type: ignore

        return wrapper  # type: ignore
    return decorator


# 测试
@retry_with_backoff(
    max_retries=3,
    base_delay=0.5,
    retryable_exceptions=(ConnectionError, TimeoutError),
)
def fetch_data(url: str) -> dict:
    """模拟网络请求"""
    import random
    if random.random() < 0.7:  # 70% 概率失败
        raise ConnectionError(f"Connection failed: {url}")
    return {"status": "ok", "data": [1, 2, 3]}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        result = fetch_data("http://api.example.com/data")
        print(f"Result: {result}")
    except ConnectionError as e:
        print(f"Failed: {e}")
```

### 练习 2：进阶场景 — 生产级日志系统

**目标**：搭建一个完整的生产级日志系统

```python
"""
练习：生产级日志系统

要求：
1. 支持控制台和文件输出
2. 支持 JSON 格式（便于 ELK 解析）
3. 支持日志轮转（按大小和时间）
4. 支持不同模块不同日志级别
5. 支持请求 ID 关联
"""
import logging
import logging.handlers
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import contextmanager
import threading


class RequestIdFilter(logging.Filter):
    """请求 ID 过滤器 — 自动添加请求 ID 到日志记录"""

    _local = threading.local()

    @classmethod
    def set_request_id(cls, request_id: str) -> None:
        cls._local.request_id = request_id

    @classmethod
    def get_request_id(cls) -> str:
        return getattr(cls._local, "request_id", "no-request-id")

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = self.get_request_id()
        return True


class JsonFormatter(logging.Formatter):
    """JSON 格式器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }

        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_production_logging(
    app_name: str = "sre-app",
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
) -> None:
    """设置生产级日志"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.handlers.clear()

    # 请求 ID 过滤器
    request_filter = RequestIdFilter()

    # JSON 格式器
    json_formatter = JsonFormatter()

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.addFilter(request_filter)
    console.setFormatter(json_formatter)
    root_logger.addHandler(console)

    # 文件
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

        # 应用日志
        app_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{app_name}.log",
            maxBytes=100 * 1024 * 1024,
            backupCount=10,
        )
        app_handler.addFilter(request_filter)
        app_handler.setFormatter(json_formatter)
        root_logger.addHandler(app_handler)

        # 错误日志
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{app_name}.error.log",
            maxBytes=50 * 1024 * 1024,
            backupCount=5,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.addFilter(request_filter)
        error_handler.setFormatter(json_formatter)
        root_logger.addHandler(error_handler)


@contextmanager
def request_context(request_id: str):
    """请求上下文 — 自动设置和清除请求 ID"""
    RequestIdFilter.set_request_id(request_id)
    try:
        yield
    finally:
        RequestIdFilter.set_request_id("")


# 使用示例
if __name__ == "__main__":
    setup_production_logging(log_dir=Path("/tmp/sre-logs"))

    logger = logging.getLogger(__name__)

    with request_context("req-abc-123"):
        logger.info("Processing request")
        logger.debug("Step 1 complete")
        logger.info("Request completed")
```

### 练习 3：故障排查挑战 — 修复异常处理代码

**场景**：以下代码有多个异常处理问题，请找出并修复。

```python
# broken_exception.py — 故障排查练习
import json
import yaml

def load_config(path):
    try:
        with open(path) as f:
            if path.endswith('.yaml'):
                return yaml.load(f)  # 问题 1
            else:
                return json.load(f)
    except:  # 问题 2
        return {}

def process_data(data):
    try:
        result = data['key']  # 问题 3
        return result
    except KeyError:
        pass  # 问题 4

def connect_database(host, port):
    try:
        conn = create_connection(host, port)
        return conn
    except Exception as e:
        print(f"Error: {e}")  # 问题 5
        return None

def run_batch(items):
    results = []
    for item in items:
        try:
            result = process(item)
            results.append(result)
        except Exception:
            continue  # 问题 6
    return results
```

**预期发现的问题**：
1. `yaml.load(f)` 安全漏洞 — 应使用 `yaml.safe_load(f)`
2. 裸 `except` 捕获所有异常 — 应指定具体异常类型
3. 不检查键是否存在 — 应使用 `.get()` 或提前验证
4. 吞掉异常不记录 — 应该记录日志
5. 只打印不记录 — 应使用 logging 模块
6. 静默跳过失败项 — 应记录哪些项失败了

---

## 🎯 面试题精选

### 问题 1：Python 装饰器的执行顺序是怎样的？多个装饰器如何叠加？

**参考答案**：

装饰器从下往上应用，从上往下执行：

```python
@A
@B
@C
def func():
    pass

# 等价于
func = A(B(C(func)))
```

执行顺序：调用 `func()` 时，先执行 A 的 wrapper，再执行 B 的 wrapper，最后执行 C 的 wrapper，然后才是原函数。

SRE 场景中的装饰器叠加：
```python
@retry(max_attempts=3)  # 最外层：重试
@timer                   # 中间层：计时
@cached(ttl=60)          # 最内层：缓存
def fetch_data():
    pass
```

### 问题 2：logging 模块中 Logger、Handler、Formatter、Filter 各自的职责是什么？

**参考答案**：

| 组件 | 职责 | 数量关系 |
|------|------|---------|
| Logger | 产生日志记录 | 通常是单例（按模块名） |
| Handler | 将日志发送到目标 | 一个 Logger 可以有多个 Handler |
| Formatter | 定义输出格式 | 一个 Handler 一个 Formatter |
| Filter | 按条件过滤日志 | 可以挂载在 Logger 或 Handler 上 |

数据流：Logger → Filter → Handler → Formatter → 输出

### 问题 3：为什么 Python 推荐使用 `logging` 模块而不是 `print()`？

**参考答案**：

1. **级别控制**：logging 支持 DEBUG/INFO/WARNING/ERROR/CRITICAL 五个级别，可以按级别过滤
2. **输出目标**：logging 可以同时输出到控制台、文件、syslog、HTTP 端点
3. **格式化**：logging 支持统一的格式（时间戳、模块名、行号）
4. **线程安全**：logging 模块是线程安全的
5. **可配置**：可以通过配置文件动态调整
6. **异常记录**：logging 可以自动记录 traceback

### 问题 4：`finally` 块在什么情况下不会执行？

**参考答案**：

`finally` 块几乎总会执行，但以下情况不会：

1. `os._exit()` — 直接终止进程，不执行清理
2. `signal.SIGKILL` — 强制终止，无法捕获
3. Python 解释器崩溃
4. `finally` 块本身抛出异常（会覆盖原始异常）
5. 无限循环中没有 break

SRE 建议：使用 `atexit` 注册清理函数作为 `finally` 的补充。

### 问题 5：上下文管理器的 `__exit__` 方法返回 True 和 False 有什么区别？

**参考答案**：

- 返回 `False` 或 `None`：异常继续传播（推荐）
- 返回 `True`：异常被抑制（吞掉），程序继续执行

```python
class SuppressErrors:
    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, ValueError):
            return True  # 只抑制 ValueError
        return False  # 其他异常继续传播
```

SRE 建议：大多数情况下返回 `False`，只在明确需要抑制特定异常时返回 `True`。

### 问题 6：如何设计一个 SRE 工具的异常体系？

**参考答案**：

```python
# 基础异常
class SREError(Exception):
    pass

# 按功能域分组
class ConfigError(SREError): ...
class ConnectionError(SREError): ...
class OperationError(SREError): ...

# 具体异常
class ConfigNotFoundError(ConfigError): ...
class ServiceUnavailableError(ConnectionError): ...
class DeploymentError(OperationError): ...
```

设计原则：
1. 所有异常继承一个基础类
2. 按功能域分组
3. 异常消息包含足够的上下文
4. 提供 `to_dict()` 方法用于日志和 API 响应
5. 保留原始异常（`original_exception`）

### 问题 7：什么是异常链（Exception Chaining）？什么时候使用？

**参考答案**：

异常链通过 `raise ... from ...` 语法将原始异常附加到新异常：

```python
try:
    result = json.loads(text)
except json.JSONDecodeError as e:
    raise ConfigParseError(f"Invalid config") from e
```

使用场景：
1. 转换异常类型（底层异常 → 业务异常）
2. 添加上下文信息
3. 保留原始错误的 traceback

在 `__cause__` 属性中可以访问原始异常。

### 问题 8：structlog 和标准 logging 有什么区别？

**参考答案**：

| 特性 | 标准 logging | structlog |
|------|-------------|-----------|
| 输出格式 | 文本 | 结构化（JSON） |
| 上下文绑定 | 需要 LoggerAdapter | 原生支持 `.bind()` |
| 性能 | 一般 | 更好（惰性求值） |
| 可组合性 | 有限 | Processor 管道 |
| 学习曲线 | 低 | 中等 |

SRE 建议：
- 简单脚本用标准 logging
- 正式服务用 structlog（结构化日志便于 ELK 解析）
- 两者可以共存（structlog 可以输出到标准 logging）

---

## 📚 深入阅读

### 官方文档
- [logging — Logging facility for Python](https://docs.python.org/3/library/logging.html)
- [logging.config — Logging configuration](https://docs.python.org/3/library/logging.config.html)
- [contextlib — Utilities for with-statement contexts](https://docs.python.org/3/library/contextlib.html)
- [traceback — Print or retrieve a stack traceback](https://docs.python.org/3/library/traceback.html)
- [warnings — Warning control](https://docs.python.org/3/library/warnings.html)

### 推荐书籍
- 《Fluent Python》Luciano Ramalho — 第 7 章：函数装饰器和闭包
- 《Effective Python》Brett Slatkin — 第 2 章：函数
- 《Python Cookbook》David Beazley — 第 9 章：元编程

### 技术博客
- [Real Python — Python Decorators](https://realpython.com/primer-on-python-decorators/)
- [Real Python — Python Logging](https://realpython.com/python-logging/)
- [structlog 官方文档](https://www.structlog.org/)

---

## ✅ 自检清单

### 理论检查
- [ ] 理解装饰器的工作原理（闭包 + 函数作为参数）
- [ ] 理解 logging 模块的四个核心组件
- [ ] 知道 Python 异常体系的层级结构
- [ ] 理解上下文管理器的 `__enter__` 和 `__exit__` 协议
- [ ] 知道 `finally` 块的执行时机

### 实操检查
- [ ] 能编写自定义装饰器（重试、计时、缓存）
- [ ] 能搭建生产级日志系统（多 Handler、JSON 格式、轮转）
- [ ] 能设计和使用自定义异常体系
- [ ] 能使用 `contextmanager` 装饰器简化上下文管理器
- [ ] 能正确处理和记录异常 traceback

### 能力验证
- [ ] 能为 SRE 工具设计完整的日志和异常体系
- [ ] 能编写支持优雅关闭的服务
- [ ] 能使用 structlog 实现结构化日志
