# Day 52: 装饰器与高级技巧

> 📅 日期：2026-05-02
> 📖 学习主题：闭包、装饰器原理、常用装饰器模式、元类、描述符、元编程
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 48 Python 基础语法、Day 50 并发编程

## 🎯 学习目标

完成 Day 52 的学习后，你应该能够：
- 深入理解闭包的工作原理及其在装饰器中的核心作用
- 从零实现各类装饰器（带参数、类装饰器、装饰器堆叠）
- 掌握元类和描述符协议，理解 Python 对象模型的底层机制
- 在 SRE 工具中灵活运用装饰器实现日志、重试、缓存、限流等功能
- 理解元编程的原理，能编写自动生成代码的工具

---

## 📖 核心知识点

### 1. 闭包（Closure）— 装饰器的基石

#### 1.1 什么是闭包

闭包是指一个函数对象，它记住了自己被创建时的词法环境。简单说：**内部函数引用了外部函数的变量，即使外部函数已经执行完毕，这些变量依然存活**。

```
闭包的三个条件：
┌─────────────────────────────────────────────┐
│  1. 有嵌套函数（函数中有函数）                    │
│  2. 内部函数引用了外部函数的变量                   │
│  3. 外部函数返回了内部函数                        │
└─────────────────────────────────────────────┘
```

#### 1.2 闭包的内存模型

```python
def make_counter(start=0):
    """创建一个计数器闭包。"""
    count = start  # 这个变量被闭包"捕获"

    def counter():
        nonlocal count  # 声明使用外部变量
        count += 1
        return count

    return counter

# 即使 make_counter 已经返回，count 依然存在
c1 = make_counter()
c2 = make_counter(100)

print(c1())  # 1
print(c1())  # 2
print(c2())  # 101
print(c1())  # 3  — c1 和 c2 各自独立
```

内存状态示意：

```
调用 make_counter() 后的内存布局：

┌──────────────────────────────────────────────────┐
│ 全局作用域                                         │
│   c1 ──→ counter 函数对象                          │
│   c2 ──→ counter 函数对象（另一个）                  │
└──────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────┐
│ c1 的闭包环境     │    │ c2 的闭包环境     │
│  count = 0      │    │  count = 100    │
│  (每次调用+1)     │    │  (每次调用+1)     │
└─────────────────┘    └─────────────────┘
```

#### 1.3 闭包的常见陷阱 — 循环中的闭包

```python
# 错误示范：所有函数都引用同一个变量 i
def make_funcs_wrong():
    funcs = []
    for i in range(5):
        def func():
            return i  # 这里的 i 是延迟绑定的！
        funcs.append(func)
    return funcs

# 所有函数都返回 4（循环结束时 i 的值）
for f in make_funcs_wrong():
    print(f())  # 4, 4, 4, 4, 4

# 正确做法：用默认参数捕获当前值
def make_funcs_correct():
    funcs = []
    for i in range(5):
        def func(i=i):  # 默认参数在定义时求值
            return i
        funcs.append(func)
    return funcs

for f in make_funcs_correct():
    print(f())  # 0, 1, 2, 3, 4
```

#### 1.4 闭包在 SRE 中的应用

```python
def make_threshold_checker(metric_name, threshold, duration_seconds=60):
    """创建一个阈值检查器闭包。

    SRE 场景：当某个指标连续超过阈值一段时间后才触发告警，
    避免瞬时毛刺导致的误报。
    """
    history = []  # 被闭包捕获，持续记录历史数据

    def checker(current_value):
        now = time.time()
        history.append((now, current_value))

        # 清理过期数据
        cutoff = now - duration_seconds
        history[:] = [(t, v) for t, v in history if t >= cutoff]

        # 检查是否持续超标
        if len(history) < 2:
            return False
        all_exceeded = all(v > threshold for _, v in history)
        return all_exceeded

    return checker

# 使用
cpu_checker = make_threshold_checker("cpu", threshold=90, duration_seconds=30)
# 在监控循环中调用
# if cpu_checker(current_cpu):
#     send_alert("CPU 持续超过 90% 已达 30 秒")
```

---

### 2. 装饰器原理 — 从语法糖到底层机制

#### 2.1 装饰器的本质

装饰器的本质就是一个**接收函数作为参数并返回新函数的高阶函数**。`@decorator` 只是语法糖。

```python
# 这两种写法完全等价：

# 写法 1：使用 @ 语法
@timer
def slow_function():
    time.sleep(1)

# 写法 2：手动调用装饰器
def slow_function():
    time.sleep(1)
slow_function = timer(slow_function)
```

装饰器的执行流程：

```
Python 解释器执行 @decorator 时的步骤：

Step 1: 解释器定义 slow_function 函数对象
Step 2: 执行 timer(slow_function)  → 得到 wrapper 函数
Step 3: 将 slow_function 这个名字绑定到 wrapper

┌──────────────┐     传入      ┌──────────────┐     返回      ┌──────────────┐
│ slow_function │ ──────────→ │   timer()     │ ──────────→ │   wrapper     │
│ (原函数对象)   │             │ (装饰器函数)   │             │ (新函数对象)   │
└──────────────┘             └──────────────┘             └──────────────┘
                                                              ↑
                                                     slow_function 现在指向它
```

#### 2.2 functools.wraps 的必要性

```python
# 不使用 functools.wraps 的问题
def bad_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@bad_decorator
def example():
    """这是示例函数的文档字符串。"""
    pass

print(example.__name__)    # "wrapper" — 丢失了原函数名！
print(example.__doc__)     # None — 丢失了文档字符串！
print(example.__module__)  # 可能也不对

# 正确做法
import functools

def good_decorator(func):
    @functools.wraps(func)  # 复制原函数的元信息
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@good_decorator
def example():
    """这是示例函数的文档字符串。"""
    pass

print(example.__name__)    # "example" — 正确
print(example.__doc__)     # "这是示例函数的文档字符串。" — 正确
```

#### 2.3 带参数的装饰器 — 三层嵌套

```python
import functools
import logging

def log(level=logging.INFO, message=None):
    """带参数的日志装饰器。

    装饰器参数在最外层函数接收。
    这是一个"装饰器工厂"——调用它返回真正的装饰器。

    三层结构：
    ┌─────────────────────────────────────┐
    │ log(level, message)  ← 装饰器工厂    │  接收装饰器参数
    │   └─ decorator(func) ← 真正的装饰器  │  接收被装饰的函数
    │       └─ wrapper()   ← 包装函数      │  接收函数调用参数
    └─────────────────────────────────────┘
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = message or f"Calling {func.__name__}"
            logging.log(level, msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 使用
@log(level=logging.DEBUG, message="开始采集指标")
def collect_metrics():
    pass

# 等价于：collect_metrics = log(level=logging.DEBUG, message="开始采集指标")(collect_metrics)
```

#### 2.4 类装饰器

```python
import functools
import time

class Timer:
    """用类实现的计时装饰器。

    类装饰器通过 __init__ 接收函数，通过 __call__ 实现包装逻辑。
    相比函数装饰器，类装饰器更容易维护状态。
    """

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.total_time = 0.0
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        start = time.perf_counter()
        result = self.func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        self.total_time += elapsed
        self.call_count += 1
        return result

    def stats(self):
        avg = self.total_time / self.call_count if self.call_count else 0
        return {
            "total_time": round(self.total_time, 3),
            "call_count": self.call_count,
            "avg_time": round(avg, 3),
        }

@Timer
def slow_function():
    time.sleep(0.1)

slow_function()
slow_function()
print(slow_function.stats())
# {'total_time': 0.2, 'call_count': 2, 'avg_time': 0.1}
```

#### 2.5 装饰器堆叠的执行顺序

```python
@decorator_a
@decorator_b
@decorator_c
def func():
    pass

# 等价于：func = decorator_a(decorator_b(decorator_c(func)))
# 执行顺序：decorator_c 先包装 → decorator_b 再包装 → decorator_a 最外层
# 调用时：先进入 decorator_a → decorator_b → decorator_c → 原函数

# 实际例子
def bold(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return f"<b>{func(*args, **kwargs)}</b>"
    return wrapper

def italic(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return f"<i>{func(*args, **kwargs)}</i>"
    return wrapper

@bold
@italic
def greet(name):
    return f"Hello, {name}"

print(greet("SRE"))
# <b><i>Hello, SRE</i></b>
```

堆叠顺序示意：

```
调用 greet("SRE") 的执行流：

┌─────────────┐
│ bold.wrapper │ ← 最先进入
│  └──────────────────────┐
│  │ italic.wrapper       │ ← 第二层
│  │  └───────────────────┐│
│  │  │ greet("SRE")      ││ ← 原函数
│  │  │ → "Hello, SRE"    ││
│  │  └───────────────────┘│
│  │ → "<i>Hello, SRE</i>"│
│  └──────────────────────┘
│ → "<b><i>Hello, SRE</i></b>"
└─────────────┘
```

---

### 3. 常用装饰器模式 — SRE 必备

#### 3.1 重试装饰器（指数退避）

```python
import functools
import time
import random
import logging

logger = logging.getLogger(__name__)

def retry(max_attempts=3, base_delay=1.0, max_delay=60.0,
          exceptions=(Exception,), on_retry=None):
    """带指数退避和抖动的重试装饰器。

    SRE 场景：
    - 调用外部 API（如云厂商 API）时网络抖动
    - 数据库连接暂时不可用
    - 分布式系统中的暂时性故障

    指数退避公式：delay = min(base_delay * 2^attempt + jitter, max_delay)
    抖动（jitter）防止多客户端同时重试导致的"惊群效应"。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise

                    # 计算退避时间（指数退避 + 随机抖动）
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.5)
                    total_delay = delay + jitter

                    logger.warning(
                        f"{func.__name__} 第 {attempt + 1} 次重试，"
                        f"等待 {total_delay:.1f}s，错误: {e}"
                    )

                    if on_retry:
                        on_retry(func.__name__, attempt + 1, e)

                    time.sleep(total_delay)
            raise last_exception
        return wrapper
    return decorator

# 使用示例
@retry(max_attempts=3, base_delay=2.0, exceptions=(ConnectionError, TimeoutError))
def call_monitoring_api(endpoint):
    """调用监控系统 API，失败时自动重试。"""
    import requests
    resp = requests.get(endpoint, timeout=5)
    resp.raise_for_status()
    return resp.json()
```

#### 3.2 限流装饰器（令牌桶算法）

```python
import functools
import time
import threading

class RateLimiter:
    """令牌桶限流器。

    SRE 场景：
    - 限制告警发送频率，避免告警风暴
    - 控制 API 调用速率，防止触发上游限流
    - 批量操作时控制并发度

    令牌桶算法原理：
    ┌─────────────────────────────────────────┐
    │  桶以恒定速率填充令牌（rate 个/秒）         │
    │  每次请求消耗一个令牌                       │
    │  桶满时多余的令牌丢弃                       │
    │  桶空时请求被拒绝或等待                     │
    └─────────────────────────────────────────┘

    ┌─────┐
    │█████│ ← 桶（容量 = burst）
    │█████│    令牌以 rate 速度填充
    │█ ███│    请求到达时取走一个令牌
    └──┬──┘
       │ 请求通过
    ───┴───
    """

    def __init__(self, rate, burst=1):
        self.rate = rate          # 令牌填充速率（个/秒）
        self.burst = burst        # 桶容量
        self.tokens = burst       # 当前令牌数
        self.last_time = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_time
            # 补充令牌
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_time = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


def rate_limit(rate, burst=1):
    """限流装饰器。"""
    limiter = RateLimiter(rate, burst)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not limiter.acquire():
                raise RuntimeError(
                    f"Rate limit exceeded for {func.__name__} "
                    f"(rate={rate}/s, burst={burst})"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

# 使用：每秒最多发送 2 条告警，突发最多 5 条
@rate_limit(rate=2, burst=5)
def send_alert(message):
    print(f"ALERT: {message}")
```

#### 3.3 缓存装饰器（带 TTL）

```python
import functools
import time
import threading

def ttl_cache(maxsize=128, ttl=300):
    """带过期时间的缓存装饰器。

    SRE 场景：
    - DNS 查询缓存（避免频繁查询）
    - 配置信息缓存（定期刷新而非每次读取）
    - 主机信息缓存（避免重复 SSH 连接）

    与 functools.lru_cache 的区别：lru_cache 没有 TTL 过期机制。
    """
    def decorator(func):
        cache = {}
        cache_times = {}
        lock = threading.Lock()
        access_order = []  # LRU 顺序

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 构建缓存键
            key = (args, tuple(sorted(kwargs.items())))

            with lock:
                # 检查缓存是否存在且未过期
                if key in cache:
                    if time.monotonic() - cache_times[key] < ttl:
                        # 命中缓存，更新访问顺序
                        access_order.remove(key)
                        access_order.append(key)
                        return cache[key]
                    else:
                        # 缓存过期，删除
                        del cache[key]
                        del cache_times[key]

            # 缓存未命中，调用原函数
            result = func(*args, **kwargs)

            with lock:
                # 检查是否需要淘汰
                while len(cache) >= maxsize:
                    oldest_key = access_order.pop(0)
                    cache.pop(oldest_key, None)
                    cache_times.pop(oldest_key, None)

                cache[key] = result
                cache_times[key] = time.monotonic()
                access_order.append(key)

            return result

        wrapper.cache_clear = lambda: (cache.clear(), cache_times.clear(),
                                        access_order.clear())
        wrapper.cache_info = lambda: {
            "size": len(cache), "maxsize": maxsize, "ttl": ttl
        }
        return wrapper
    return decorator

# 使用：DNS 解析结果缓存 5 分钟
@ttl_cache(maxsize=256, ttl=300)
def resolve_hostname(hostname):
    import socket
    return socket.gethostbyname(hostname)
```

#### 3.4 单例装饰器

```python
import functools
import threading

def singleton(cls):
    """线程安全的单例装饰器。

    SRE 场景：
    - 全局配置管理器（只应有一个实例）
    - 日志收集器（避免重复初始化）
    - 数据库连接池（共享连接资源）
    """
    instances = {}
    lock = threading.Lock()

    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                # 双重检查锁定（Double-Checked Locking）
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance

@singleton
class ConfigManager:
    """全局配置管理器。"""
    def __init__(self, config_path="/etc/myapp/config.yaml"):
        import yaml
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

# 无论调用多少次，都返回同一个实例
config1 = ConfigManager()
config2 = ConfigManager()
assert config1 is config2
```

#### 3.5 权限检查装饰器

```python
import functools
import os
import logging

logger = logging.getLogger(__name__)

def require_root(func):
    """要求 root 权限的装饰器。

    SRE 场景：执行系统级操作前检查权限。
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if os.geteuid() != 0:
            raise PermissionError(
                f"{func.__name__} 需要 root 权限，当前 UID={os.geteuid()}"
            )
        return func(*args, **kwargs)
    return wrapper

def require_env(var_name):
    """要求环境变量存在的装饰器。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if var_name not in os.environ:
                raise EnvironmentError(
                    f"{func.__name__} 需要环境变量 {var_name}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

@require_root
def restart_service(service_name):
    """重启系统服务。"""
    os.system(f"systemctl restart {service_name}")

@require_env("SLACK_WEBHOOK_URL")
def send_slack_alert(message):
    """发送 Slack 告警。"""
    import requests
    webhook = os.environ["SLACK_WEBHOOK_URL"]
    requests.post(webhook, json={"text": message})
```

---

### 4. 元类（Metaclass）— Python 对象模型的顶层

#### 4.1 一切皆对象

在 Python 中，**类本身也是对象**。理解元类需要先理解这个层次关系：

```
Python 的类型层次：

┌─────────────────────────────────────────────────┐
│                   type (元类)                     │
│              所有类的"类"                          │
│                                                   │
│  ┌──────────────────────────────────────────┐    │
│  │              int, str, list ...           │    │
│  │              (内置类型)                    │    │
│  │                                          │    │
│  │  ┌───────────────────────────────────┐   │    │
│  │  │         自定义类                    │   │    │
│  │  │     class MyClass: ...             │   │    │
│  │  │                                    │   │    │
│  │  │  ┌────────────────────────────┐   │   │    │
│  │  │  │     实例对象                │   │   │    │
│  │  │  │  obj = MyClass()           │   │   │    │
│  │  │  └────────────────────────────┘   │   │    │
│  │  └───────────────────────────────────┘   │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘

关键关系：
- type(int) → <class 'type'>     — int 是 type 的实例
- type(type) → <class 'type'>    — type 是自己的实例
- isinstance(MyClass, type)      — 自定义类也是 type 的实例
```

验证这个关系：

```python
>>> type(42)
<class 'int'>
>>> type(int)
<class 'type'>
>>> type(type)
<class 'type'>

>>> class Foo: pass
>>> type(Foo)
<class 'type'>
>>> isinstance(Foo, type)
True
```

#### 4.2 class 语句的底层执行

```python
# 当你写：
class MyClass(BaseClass):
    x = 10
    def method(self):
        pass

# Python 实际执行的是：
MyClass = type('MyClass', (BaseClass,), {'x': 10, 'method': method})
#            ↑ 类名     ↑ 基类元组        ↑ 类属性字典
```

元类就是控制这个过程的机制。`type` 是默认的元类，你可以用自定义元类替换它。

#### 4.3 自定义元类

```python
class RegistryMeta(type):
    """自动注册子类的元类。

    SRE 场景：插件系统中，每定义一个新的监控采集器或告警通道，
    自动注册到全局注册表，无需手动维护。
    """

    _registry = {}

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        # 不注册基类本身
        if bases:
            # 用类名作为键注册
            mcs._registry[name] = cls
            # 也可以用类属性指定的名称注册
            plugin_name = namespace.get('plugin_name', name.lower())
            mcs._registry[plugin_name] = cls

        return cls

    @classmethod
    def get_registry(mcs):
        return dict(mcs._registry)

    @classmethod
    def get_plugin(mcs, name):
        return mcs._registry.get(name)


class Collector(metaclass=RegistryMeta):
    """采集器基类。"""
    plugin_name = "base"

    def collect(self):
        raise NotImplementedError


class CPUCollector(Collector):
    plugin_name = "cpu"

    def collect(self):
        import psutil
        return {"cpu_percent": psutil.cpu_percent(interval=1)}


class MemoryCollector(Collector):
    plugin_name = "memory"

    def collect(self):
        import psutil
        mem = psutil.virtual_memory()
        return {"memory_percent": mem.percent}


# 自动注册，无需手动维护列表
print(RegistryMeta.get_registry())
# {'Collector': <class 'Collector'>, 'base': ...,
#  'CPUCollector': ..., 'cpu': ...,
#  'MemoryCollector': ..., 'memory': ...}

# 通过名称获取插件
collector_cls = RegistryMeta.get_plugin("cpu")
collector = collector_cls()
print(collector.collect())
```

#### 4.4 `__init_subclass__` — 更简单的方案

```python
class Collector:
    """采集器基类（使用 __init_subclass__ 替代元类）。"""

    _registry = {}

    def __init_subclass__(cls, plugin_name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__.lower()
        Collector._registry[name] = cls

    def collect(self):
        raise NotImplementedError

class DiskCollector(Collector, plugin_name="disk"):
    def collect(self):
        import psutil
        return {"disk_percent": psutil.disk_usage("/").percent}

# __init_subclass__ 是 Python 3.6+ 的推荐方式，比元类更简洁
print(Collector._registry)
# {'disk': <class 'DiskCollector'>}
```

#### 4.5 元类 vs `__init_subclass__` 选择指南

```
┌────────────────────────────────────────────────────────────┐
│                   选择决策树                                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  需要拦截类的创建过程？                                       │
│  ├─ 否 → 不需要元类                                         │
│  └─ 是 → 需要修改 __new__ 或 __init__？                      │
│          ├─ 仅在子类创建时执行逻辑                             │
│          │   └─ 用 __init_subclass__（推荐）                  │
│          └─ 需要完全控制类的创建（修改基类、属性等）              │
│              └─ 用元类                                       │
│                                                            │
│  何时用元类：                                                │
│  - 需要修改类的属性或方法                                    │
│  - 需要自动添加方法到类                                      │
│  - 需要拦截属性访问                                          │
│  - ORM 框架（Django Models）                                │
│                                                            │
│  何时用 __init_subclass__：                                  │
│  - 仅需要在子类定义时执行注册或验证                            │
│  - 更简洁，不需要理解元类的复杂性                              │
│  - Python 3.6+ 推荐方式                                     │
└────────────────────────────────────────────────────────────┘
```

---

### 5. 描述符（Descriptor）— 属性访问的底层机制

#### 5.1 描述符协议

描述符是实现了特定方法的对象，这些方法在属性被访问时自动调用：

```python
class Descriptor:
    """描述符协议的三个方法。"""

    def __get__(self, obj, objtype=None):
        """属性被读取时调用。"""
        if obj is None:
            return self  # 通过类访问，返回描述符自身
        return self._value

    def __set__(self, obj, value):
        """属性被赋值时调用。"""
        self._value = value

    def __delete__(self, obj):
        """属性被删除时调用。"""
        del self._value
```

描述符的调用机制：

```
obj.attr 的查找顺序（简化版）：

1. 搜索 obj.__class__.__mro__ 中的类属性
2. 如果找到 data descriptor（同时有 __get__ 和 __set__），
   调用 descriptor.__get__(obj, type)
3. 否则搜索 obj.__dict__['attr']
4. 否则搜索类属性中的 non-data descriptor（只有 __get__），
   调用 descriptor.__get__(obj, type)
5. 否则抛出 AttributeError

data descriptor vs non-data descriptor：
┌────────────────────────────────────────────────────┐
│ data descriptor:     有 __get__ 和 __set__          │
│   优先级高于实例字典                                 │
│   例如：property                                   │
│                                                     │
│ non-data descriptor: 只有 __get__                    │
│   优先级低于实例字典                                 │
│   例如：函数（方法）                                 │
└────────────────────────────────────────────────────┘
```

#### 5.2 类型验证描述符

```python
class Validated:
    """带类型验证的描述符。

    SRE 场景：配置类中确保字段类型正确，避免运行时才发现配置错误。
    """

    def __init__(self, expected_type, default=None):
        self.expected_type = expected_type
        self.default = default
        self.name = None  # 在 __set_name__ 中自动设置

    def __set_name__(self, owner, name):
        """Python 3.6+ 自动调用，传入属性名。"""
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(
                f"{self.name} 必须是 {self.expected_type.__name__}，"
                f"得到 {type(value).__name__}"
            )
        obj.__dict__[self.name] = value


class ServerConfig:
    """服务器配置类，使用描述符自动验证类型。"""

    hostname = Validated(str)
    port = Validated(int, default=80)
    tags = Validated(list, default_factory=list)

    def __init__(self, hostname, port=80, tags=None):
        self.hostname = hostname  # 触发 __set__，自动验证类型
        self.port = port
        self.tags = tags or []

# 使用
config = ServerConfig("web01", port=8080)
print(config.hostname)  # "web01"

# 自动类型检查
try:
    config.port = "not_a_number"  # TypeError: port 必须是 int
except TypeError as e:
    print(e)
```

#### 5.3 描述符在 property 中的体现

```python
# property 本质上就是一个描述符
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def fahrenheit(self):
        """@property 就是一个 data descriptor。"""
        return self._celsius * 9 / 5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value):
        self._celsius = (value - 32) * 5 / 9

# 等价的手动描述符实现：
class Fahrenheit:
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj._celsius * 9 / 5 + 32

    def __set__(self, obj, value):
        obj._celsius = (value - 32) * 5 / 9

class TemperatureManual:
    fahrenheit = Fahrenheit()  # 描述符实例作为类属性

    def __init__(self, celsius):
        self._celsius = celsius
```

#### 5.4 描述符在 SRE 中的实际应用

```python
import psutil

class CachedMetric:
    """带缓存的系统指标描述符。

    SRE 场景：监控指标采集时，某些指标（如 CPU 频率）变化不频繁，
    可以缓存一段时间避免重复系统调用。
    """

    def __init__(self, func, ttl=5.0):
        self.func = func
        self.ttl = ttl
        self.cache_time = 0
        self.cached_value = None
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        now = time.monotonic()
        if now - self.cache_time >= self.ttl:
            self.cached_value = self.func(obj)
            self.cache_time = now

        return self.cached_value


class SystemMetrics:
    """系统指标采集器。"""

    @CachedMetric.__init__  # 不这样用，见下方正确写法
    def cpu_freq(self):
        return psutil.cpu_freq()

# 正确的描述符用法：
class CachedProperty:
    """简化的缓存属性描述符。"""

    def __init__(self, func, ttl=5.0):
        self.func = func
        self.ttl = ttl
        self.attr_name = None

    def __set_name__(self, owner, name):
        self.attr_name = f"_cached_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        cache = obj.__dict__.get(self.attr_name)
        now = time.monotonic()

        if cache is None or now - cache[0] >= self.ttl:
            value = self.func(obj)
            obj.__dict__[self.attr_name] = (now, value)
            return value

        return cache[1]


class SystemMetrics:
    """系统指标采集器，使用描述符缓存指标。"""

    @CachedProperty
    def cpu_freq(self):
        """CPU 频率（变化不频繁，缓存 10 秒）。"""
        freq = psutil.cpu_freq()
        return {"current": freq.current, "min": freq.min, "max": freq.max}

    @CachedProperty
    def disk_partitions(self):
        """磁盘分区信息（几乎不变，缓存 60 秒）。"""
        return [p.device for p in psutil.disk_partitions()]
```

---

### 6. 元编程（Metaprogramming）— 编写生成代码的代码

#### 6.1 动态创建类

```python
def make_data_class(class_name, fields):
    """动态创建数据类。

    SRE 场景：根据配置文件或 API 响应的 schema 动态生成数据模型。
    """
    # 构建 __init__ 方法
    def init(self, **kwargs):
        for field_name, field_type in fields.items():
            value = kwargs.get(field_name)
            if value is not None and not isinstance(value, field_type):
                raise TypeError(
                    f"{field_name} 必须是 {field_type.__name__}"
                )
            setattr(self, field_name, value)

    # 构建 __repr__ 方法
    def repr(self):
        attrs = ", ".join(
            f"{name}={getattr(self, name)!r}" for name in fields
        )
        return f"{class_name}({attrs})"

    # 构建类
    namespace = {
        '__init__': init,
        '__repr__': repr,
        '__annotations__': dict(fields),
    }

    return type(class_name, (object,), namespace)

# 动态创建告警事件类
AlertEvent = make_data_class("AlertEvent", {
    "hostname": str,
    "severity": str,
    "message": str,
    "timestamp": float,
})

event = AlertEvent(
    hostname="web01",
    severity="critical",
    message="CPU > 95%",
    timestamp=1234567890.0
)
print(event)  # AlertEvent(hostname='web01', severity='critical', ...)
```

#### 6.2 使用 `__init_subclass__` 实现插件自动发现

```python
import importlib
import pkgutil
import os

class PluginBase:
    """插件基类，自动发现并注册所有子类。"""

    _plugins = {}

    def __init_subclass__(cls, plugin_id=None, **kwargs):
        super().__init_subclass__(**kwargs)
        pid = plugin_id or cls.__name__
        PluginBase._plugins[pid] = cls

    @classmethod
    def load_plugins_from(cls, package_path):
        """从指定目录动态加载插件模块。"""
        for finder, name, ispkg in pkgutil.iter_modules([package_path]):
            importlib.import_module(name)

    @classmethod
    def get_plugin(cls, plugin_id):
        return cls._plugins.get(plugin_id)

    @classmethod
    def list_plugins(cls):
        return list(cls._plugins.keys())

    def execute(self, *args, **kwargs):
        raise NotImplementedError


# 定义插件
class CleanupTempPlugin(PluginBase, plugin_id="cleanup_temp"):
    def execute(self, days=7):
        import subprocess
        subprocess.run(["find", "/tmp", "-mtime", f"+{days}", "-delete"])


class RotateLogPlugin(PluginBase, plugin_id="rotate_logs"):
    def execute(self, log_dir="/var/log"):
        import subprocess
        subprocess.run(["logrotate", "-f", "/etc/logrotate.conf"])


# 使用
print(PluginBase.list_plugins())
# ['cleanup_temp', 'rotate_logs']

plugin = PluginBase.get_plugin("cleanup_temp")()
plugin.execute(days=3)
```

#### 6.3 使用 `__set_name__` 实现 ORM 风格的字段定义

```python
class Field:
    """ORM 风格的字段描述符。"""

    def __init__(self, field_type, required=True, default=None):
        self.field_type = field_type
        self.required = required
        self.default = default
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name
        # 在类上注册字段
        if not hasattr(owner, '_fields'):
            owner._fields = {}
        owner._fields[name] = self

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj, value):
        if value is not None and not isinstance(value, self.field_type):
            raise TypeError(
                f"{self.name} 期望 {self.field_type.__name__}，"
                f"得到 {type(value).__name__}"
            )
        obj.__dict__[self.name] = value

    def validate(self, obj):
        value = obj.__dict__.get(self.name)
        if self.required and value is None:
            raise ValueError(f"{self.name} 是必填字段")


class Model:
    """简单模型基类。"""

    def __init__(self, **kwargs):
        for name, field in self._fields.items():
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif field.required and field.default is None:
                raise ValueError(f"缺少必填字段: {name}")

    def validate(self):
        for field in self._fields.values():
            field.validate(self)

    def to_dict(self):
        return {name: getattr(self, name) for name in self._fields}


class AlertRule(Model):
    name = Field(str)
    metric = Field(str)
    threshold = Field(float)
    duration = Field(int, default=60)
    enabled = Field(bool, default=True)

# 使用
rule = AlertRule(
    name="high_cpu",
    metric="cpu_percent",
    threshold=90.0,
    duration=120
)
print(rule.to_dict())
# {'name': 'high_cpu', 'metric': 'cpu_percent', 'threshold': 90.0,
#  'duration': 120, 'enabled': True}
```

#### 6.4 `__getattr__` 和 `__getattribute__` 实现动态代理

```python
class MetricProxy:
    """指标代理对象，支持链式访问。

    SRE 场景：构建灵活的指标查询接口。

    Usage:
        metrics = MetricProxy()
        metrics.cpu.percent        → 查找 cpu_percent 指标
        metrics.memory.used_mb     → 查找 memory_used_mb 指标
        metrics.disk["/"].percent  → 查找 disk_/_percent 指标
    """

    def __init__(self, prefix="", collector=None):
        # 使用 object.__setattr__ 避免触发自定义 __setattr__
        object.__setattr__(self, '_prefix', prefix)
        object.__setattr__(self, '_collector', collector)

    def __getattr__(self, name):
        # 构建指标名
        new_prefix = f"{self._prefix}_{name}" if self._prefix else name
        return MetricProxy(prefix=new_prefix)

    def __getitem__(self, key):
        new_prefix = f"{self._prefix}_{key}" if self._prefix else key
        return MetricProxy(prefix=new_prefix)

    def __call__(self):
        # 当尝试"调用"时，实际查询指标
        metric_name = object.__getattribute__(self, '_prefix')
        collector = object.__getattribute__(self, '_collector')
        if collector:
            return collector.collect(metric_name)
        return metric_name

# 使用
proxy = MetricProxy()
print(proxy.cpu.percent())      # "cpu_percent"
print(proxy.memory.used_mb())   # "memory_used_mb"
print(proxy.disk["/"].free())   # "disk_/_free"
```

---

### 7. 综合实战：SRE 工具装饰器库

```python
#!/usr/bin/env python3
"""SRE 工具装饰器库 — 生产级实现。

包含 SRE 日常工作中最常用的装饰器：
- 日志记录
- 性能计时
- 自动重试
- 限流保护
- 缓存
- 权限检查
"""

import functools
import time
import logging
import threading
import random
from collections import deque
from typing import Any, Callable, Optional, Tuple, Type


# ──────────────────────────────────────────────
# 配置日志
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("sre.decorators")


# ──────────────────────────────────────────────
# 1. 日志装饰器
# ──────────────────────────────────────────────
def log_call(level=logging.INFO, include_args=False):
    """记录函数调用的装饰器。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            if include_args:
                logger.log(level, f"调用 {func_name}(args={args}, kwargs={kwargs})")
            else:
                logger.log(level, f"调用 {func_name}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{func_name} 完成")
                return result
            except Exception as e:
                logger.error(f"{func_name} 异常: {e}")
                raise
        return wrapper
    return decorator


# ──────────────────────────────────────────────
# 2. 计时装饰器
# ──────────────────────────────────────────────
class TimerStats:
    """全局计时统计收集器。"""
    _stats = {}
    _lock = threading.Lock()

    @classmethod
    def record(cls, func_name, elapsed):
        with cls._lock:
            if func_name not in cls._stats:
                cls._stats[func_name] = {
                    "count": 0, "total": 0.0,
                    "min": float('inf'), "max": 0.0
                }
            s = cls._stats[func_name]
            s["count"] += 1
            s["total"] += elapsed
            s["min"] = min(s["min"], elapsed)
            s["max"] = max(s["max"], elapsed)

    @classmethod
    def report(cls):
        with cls._lock:
            for name, s in sorted(cls._stats.items()):
                avg = s["total"] / s["count"] if s["count"] else 0
                print(f"  {name}: count={s['count']}, "
                      f"avg={avg:.3f}s, min={s['min']:.3f}s, max={s['max']:.3f}s")


def timer(func):
    """计时装饰器，自动记录到全局统计。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            TimerStats.record(func.__name__, elapsed)
    return wrapper


# ──────────────────────────────────────────────
# 3. 重试装饰器（指数退避 + 抖动）
# ──────────────────────────────────────────────
def retry(max_attempts=3, base_delay=1.0, max_delay=60.0,
          exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """重试装饰器。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts - 1:
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.5)
                    logger.warning(
                        f"{func.__name__} 第 {attempt + 1} 次重试，"
                        f"等待 {delay + jitter:.1f}s: {e}"
                    )
                    time.sleep(delay + jitter)
            raise last_exc
        return wrapper
    return decorator


# ──────────────────────────────────────────────
# 4. 限流装饰器
# ──────────────────────────────────────────────
def rate_limit(calls_per_second=1.0):
    """简单限流装饰器（滑动窗口）。"""
    min_interval = 1.0 / calls_per_second
    last_call = [0.0]  # 使用列表以便在闭包中修改
    lock = threading.Lock()

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                now = time.monotonic()
                wait = min_interval - (now - last_call[0])
                if wait > 0:
                    time.sleep(wait)
                last_call[0] = time.monotonic()
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ──────────────────────────────────────────────
# 使用示例
# ──────────────────────────────────────────────
if __name__ == "__main__":
    @log_call(level=logging.INFO)
    @timer
    @retry(max_attempts=3, exceptions=(ConnectionError,))
    @rate_limit(calls_per_second=2)
    def check_host(hostname):
        """检查主机健康状态。"""
        import random
        if random.random() < 0.3:
            raise ConnectionError(f"无法连接 {hostname}")
        time.sleep(0.1)
        return {"hostname": hostname, "status": "healthy"}

    # 执行多次调用
    for host in ["web01", "web02", "db01"]:
        try:
            result = check_host(host)
            logger.info(f"结果: {result}")
        except ConnectionError as e:
            logger.error(f"最终失败: {e}")

    # 打印统计
    print("\n性能统计：")
    TimerStats.report()
```

---

## 💻 实战练习

### 练习 1：实现一个缓存装饰器（带 TTL 和 LRU 淘汰）

**要求**：
- 支持设置缓存过期时间（TTL）
- 支持 LRU 淘汰策略
- 线程安全
- 提供 `cache_info()` 和 `cache_clear()` 方法

```python
# 你的代码框架
def ttl_lru_cache(maxsize=128, ttl=300):
    def decorator(func):
        # TODO: 实现缓存逻辑
        pass
    return decorator

# 测试
@ttl_lru_cache(maxsize=2, ttl=10)
def expensive_query(key):
    time.sleep(1)  # 模拟耗时操作
    return f"result_{key}"
```

<details>
<summary>参考答案</summary>

```python
import functools
import time
import threading
from collections import OrderedDict

def ttl_lru_cache(maxsize=128, ttl=300):
    def decorator(func):
        cache = OrderedDict()
        timestamps = {}
        lock = threading.Lock()
        hits = 0
        misses = 0

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal hits, misses
            key = (args, tuple(sorted(kwargs.items())))

            with lock:
                now = time.monotonic()
                if key in cache:
                    if now - timestamps[key] < ttl:
                        cache.move_to_end(key)
                        hits += 1
                        return cache[key]
                    else:
                        del cache[key]
                        del timestamps[key]

            result = func(*args, **kwargs)

            with lock:
                misses += 1
                cache[key] = result
                timestamps[key] = time.monotonic()
                while len(cache) > maxsize:
                    oldest_key, _ = cache.popitem(last=False)
                    timestamps.pop(oldest_key, None)

            return result

        def cache_info():
            return {"hits": hits, "misses": misses, "size": len(cache)}

        def cache_clear():
            cache.clear()
            timestamps.clear()

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper
    return decorator
```
</details>

### 练习 2：实现一个类装饰器，自动为方法添加输入验证

**要求**：
- 支持类型注解验证
- 支持自定义验证器
- 验证失败时抛出清晰的错误信息

```python
# 你的代码框架
class ValidateInput:
    def __init__(self, func):
        # TODO
        pass

    def __call__(self, *args, **kwargs):
        # TODO: 根据类型注解验证输入
        pass
```

<details>
<summary>参考答案</summary>

```python
import functools
import inspect

class ValidateInput:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.sig = inspect.signature(func)
        self.hints = func.__annotations__

    def __call__(self, *args, **kwargs):
        bound = self.sig.bind(*args, **kwargs)
        bound.apply_defaults()

        for name, value in bound.arguments.items():
            if name in self.hints:
                expected_type = self.hints[name]
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"参数 '{name}' 期望 {expected_type.__name__}，"
                        f"得到 {type(value).__name__}"
                    )
        return self.func(*args, **kwargs)

# 使用
@ValidateInput
def create_alert(name: str, threshold: float, enabled: bool = True):
    return {"name": name, "threshold": threshold, "enabled": enabled}

# 正常调用
print(create_alert("high_cpu", 90.0))

# 类型错误
try:
    create_alert("high_cpu", "not_a_number")
except TypeError as e:
    print(e)  # 参数 'threshold' 期望 float，得到 str
```
</details>

### 练习 3：实现一个插件系统（元类 + 描述符）

**要求**：
- 使用元类自动注册插件
- 使用描述符实现配置字段验证
- 支持通过配置文件启用/禁用插件

```python
# 你的代码框架
class PluginMeta(type):
    # TODO: 自动注册插件
    pass

class ConfigField:
    # TODO: 配置字段描述符
    pass

class Plugin(metaclass=PluginMeta):
    # TODO: 插件基类
    pass
```

<details>
<summary>参考答案</summary>

```python
import json

class PluginMeta(type):
    _registry = {}

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if bases:
            mcs._registry[name] = cls
        return cls

class ConfigField:
    def __init__(self, field_type, required=True, default=None):
        self.field_type = field_type
        self.required = required
        self.default = default

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj, value):
        if not isinstance(value, self.field_type):
            raise TypeError(f"{self.name}: 期望 {self.field_type.__name__}")
        obj.__dict__[self.name] = value

class Plugin(metaclass=PluginMeta):
    name = ConfigField(str)
    enabled = ConfigField(bool, default=True)

    def execute(self):
        raise NotImplementedError

class DiskCleanup(Plugin):
    name = "disk_cleanup"

    def __init__(self, days=7):
        self.days = days

    def execute(self):
        print(f"清理 {self.days} 天前的临时文件")

# 自动注册
print(PluginMeta._registry)
# {'DiskCleanup': <class 'DiskCleanup'>}
```
</details>

---

## 🎯 面试题精选

### 问题 1：什么是闭包？闭包和普通函数有什么区别？

**参考答案**：
闭包是一个函数对象，它记住了自己被创建时的词法环境中的变量。与普通函数的区别：
1. 闭包可以访问外部函数的局部变量，即使外部函数已返回
2. 闭包延长了外部变量的生命周期
3. 每个闭包实例都有自己独立的环境副本（或引用）
4. 常用于装饰器、回调函数、工厂函数等场景

### 问题 2：装饰器的执行时机是什么？@decorator 在哪一步生效？

**参考答案**：
装饰器在**模块加载时**（定义函数时）执行，而不是在调用函数时。当 Python 解释器遇到 `@decorator` 语法时：
1. 先定义被装饰的函数
2. 立即执行 `decorator(original_func)` 得到包装后的函数
3. 将原函数名绑定到包装后的函数

这意味着如果装饰器有副作用（如打印），会在导入时就执行。

### 问题 3：functools.wraps 的作用是什么？为什么必须使用它？

**参考答案**：
`functools.wraps` 将原函数的元信息（`__name__`、`__doc__`、`__module__`、`__annotations__` 等）复制到包装函数上。必须使用的原因：
1. 调试时看到正确的函数名而不是 "wrapper"
2. 文档字符串保持正确
3. 其他依赖函数元信息的工具（如 help()、Sphinx 文档）能正常工作
4. 序列化（pickle）依赖 `__name__` 和 `__qualname__`

### 问题 4：什么是元类？什么时候需要使用元类？

**参考答案**：
元类是"创建类的类"。`type` 是 Python 中最基础的元类。使用元类的场景：
1. **自动注册**：定义类时自动注册到全局注册表（插件系统）
2. **API 验证**：确保子类实现了特定方法
3. **ORM 框架**：Django 的 Model 用元类将类定义转换为数据库表
4. **单例模式**：控制类的实例化

大多数情况下，`__init_subclass__` 可以替代元类，更简单。

### 问题 5：描述符是什么？data descriptor 和 non-data descriptor 有什么区别？

**参考答案**：
描述符是实现了 `__get__`、`__set__`、`__delete__` 方法的对象。区别：
- **data descriptor**：同时实现了 `__get__` 和 `__set__`，优先级**高于**实例字典
- **non-data descriptor**：只实现了 `__get__`，优先级**低于**实例字典

`property` 是 data descriptor 的典型例子，而函数（方法）是 non-data descriptor。

### 问题 6：以下代码输出什么？为什么？

```python
def make_funcs():
    return [lambda: i for i in range(5)]

for f in make_funcs():
    print(f(), end=" ")
```

**参考答案**：
输出 `4 4 4 4 4`。因为 lambda 中的 `i` 是延迟绑定的，循环结束后 `i` 的值是 4，所有 lambda 共享同一个 `i`。修复方法：`lambda i=i: i`（默认参数在定义时求值）。

### 问题 7：元类和 `__init_subclass__` 应该如何选择？

**参考答案**：
优先使用 `__init_subclass__`（Python 3.6+），它更简单、更直观。只有在需要完全控制类的创建过程时（如修改基类、注入方法、拦截属性定义）才使用元类。Django、SQLAlchemy 等框架使用元类是因为它们需要在类定义时做大量转换工作。

### 问题 8：如何实现一个线程安全的单例？

**参考答案**：
常见方案有三种：
1. **装饰器 + 双重检查锁**：使用 `threading.Lock` 和双重 `if` 检查
2. **元类**：在元类的 `__call__` 中控制实例化
3. **模块级变量**：Python 模块本身就是单例的，将实例放在模块级别

推荐方案 1 或方案 3，因为最简单。方案 2 适用于需要跨继承体系的单例。

### 问题 9：解释以下代码的执行顺序

```python
@bold
@italic
def greet(name):
    return f"Hello, {name}"
```

**参考答案**：
等价于 `greet = bold(italic(greet))`。执行顺序：
1. 先定义 `greet` 函数
2. 执行 `italic(greet)` → 返回 italic 的 wrapper
3. 执行 `bold(italic_wrapper)` → 返回 bold 的 wrapper
4. `greet` 现在指向 bold 的 wrapper

调用时：进入 bold → 进入 italic → 执行原函数 → 返回 italic 结果 → 返回 bold 结果。

### 问题 10：装饰器和上下文管理器在 SRE 工具中各适合什么场景？

**参考答案**：
- **装饰器**：适合"围绕函数调用"的横切关注点（日志、重试、限流、权限检查、计时）。它的优势是声明式的，不侵入函数内部。
- **上下文管理器**：适合"资源管理"场景（数据库连接、临时文件、锁的获取释放、配置切换）。它的优势是明确的进入/退出语义，保证资源清理。

两者的共同点都是实现"关注点分离"，将通用逻辑从核心业务逻辑中抽离。

---

## 📚 深入阅读

### 官方文档
- [Python 装饰器指南](https://docs.python.org/3/glossary.html#term-decorator)
- [functools 模块](https://docs.python.org/3/library/functools.html)
- [描述符指南](https://docs.python.org/3/howto/descriptor.html)
- [Python 元类编程](https://docs.python.org/3/reference/datamodel.html#metaclasses)
- [contextlib 模块](https://docs.python.org/3/library/contextlib.html)
- [dataclasses 模块](https://docs.python.org/3/library/dataclasses.html)

### 推荐书籍
- 《Fluent Python》第二版 — Luciano Ramalho（第 9 章：装饰器与闭包，第 23 章：描述符与元类）
- 《Python Cookbook》第三版 — David Beazley（第 9 章：元编程）
- 《Python 源码剖析》— 陈儒（深入理解 Python 对象模型）

### 技术博客
- [Real Python: Primer on Python Decorators](https://realpython.com/primer-on-python-decorators/)
- [Real Python: Python Decorators 101](https://realpython.com/python-decorator/)
- [Descriptor HowTo Guide](https://docs.python.org/3/howto/descriptor.html)

---

## ✅ 自检清单

### 理论检查
- [ ] 能解释闭包的三个条件和内存模型
- [ ] 能解释装饰器的执行时机（定义时 vs 调用时）
- [ ] 能区分 data descriptor 和 non-data descriptor
- [ ] 能解释元类和 `__init_subclass__` 的区别及选择标准
- [ ] 能解释 `functools.wraps` 的必要性

### 实操检查
- [ ] 能从零实现带参数的三层嵌套装饰器
- [ ] 能实现带 TTL 和 LRU 的缓存装饰器
- [ ] 能使用元类实现自动注册的插件系统
- [ ] 能使用描述符实现类型验证
- [ ] 能在 SRE 工具中正确使用装饰器（重试、限流、日志）

### 能力验证
- [ ] 能为 SRE 工具设计完整的装饰器库
- [ ] 能在代码审查中发现装饰器的常见错误（忘记 wraps、闭包陷阱）
- [ ] 能解释装饰器堆叠的执行顺序
