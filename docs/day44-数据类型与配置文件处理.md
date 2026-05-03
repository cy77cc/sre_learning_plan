# Day 44: Python 数据类型与配置文件处理

> 📅 日期：2026-05-03
> 📖 学习主题：Python 数据类型深入与配置文件处理（JSON/YAML/TOML/INI/Pydantic）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 43 Python 环境搭建与开发规范

## 🎯 学习目标

- 深入掌握 Python 核心数据类型（list/dict/set/tuple）的内部机制与性能特征
- 熟练处理 JSON/YAML/TOML/INI 四种 SRE 常用配置文件格式
- 掌握 Pydantic 数据验证框架，编写类型安全的配置管理代码
- 能实现多环境配置合并、环境变量覆盖、配置热加载等 SRE 核心功能

---

## 📖 核心知识点

### 1. Python 数据类型深入

#### 1.1 列表（list）— 有序可变序列

**底层实现**：list 使用动态数组（C 语言的 `PyObject**`）实现，内存连续分配。

```
┌─────────────────────────────────────────────────────────────────┐
│                    list 内存布局                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  list 对象头 (PyObject_VAR_HEAD)                                │
│  ├── ob_refcnt    (引用计数)                                    │
│  ├── ob_type      (类型指针 → list)                             │
│  ├── ob_size      (当前元素数量)                                │
│  ├── allocated    (已分配的容量)                                 │
│  └── ob_item      (指向数组的指针)                               │
│            │                                                    │
│            ▼                                                    │
│       ┌────┬────┬────┬────┬────┬────┬────┬────┐                │
│       │ p0 │ p1 │ p2 │ p3 │ p4 │NULL│NULL│NULL│                │
│       └────┴────┴────┴────┴────┴────┴────┴────┘                │
│        ↑                                  ↑                     │
│      ob_item                          allocated=8               │
│                                       ob_size=5                 │
│                                                                 │
│  扩容策略: new_allocated = (newsize >> 3) + (newsize < 9 ? 3 : 6) + newsize │
│  即每次扩容约 12.5%，避免频繁 realloc                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**时间复杂度：**

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| `list[i]` | O(1) | 数组索引，直接计算偏移 |
| `list.append(x)` | O(1) 均摊 | 尾部追加，偶尔触发扩容 |
| `list.insert(i, x)` | O(n) | 需要移动 i 之后的所有元素 |
| `list.pop()` | O(1) | 尾部弹出 |
| `list.pop(0)` | O(n) | 头部弹出，需要移动所有元素 |
| `x in list` | O(n) | 线性扫描 |
| `list.sort()` | O(n log n) | Timsort 算法 |

**SRE 实战：高效的列表操作**

```python
from typing import List, Any
from collections import deque
import time


def benchmark_list_operations() -> None:
    """对比 list 和 deque 在不同场景下的性能"""
    n = 100000

    # 场景 1: 尾部追加 — list 和 deque 都很快
    start = time.perf_counter()
    lst: List[int] = []
    for i in range(n):
        lst.append(i)
    list_append_time = time.perf_counter() - start

    start = time.perf_counter()
    dq: deque[int] = deque()
    for i in range(n):
        dq.append(i)
    deque_append_time = time.perf_counter() - start

    print(f"尾部追加 {n} 次:")
    print(f"  list:  {list_append_time:.4f}s")
    print(f"  deque: {deque_append_time:.4f}s")

    # 场景 2: 头部插入 — deque 远快于 list
    start = time.perf_counter()
    lst2: List[int] = []
    for i in range(10000):
        lst2.insert(0, i)
    list_insert_time = time.perf_counter() - start

    start = time.perf_counter()
    dq2: deque[int] = deque()
    for i in range(10000):
        dq2.appendleft(i)
    deque_insert_time = time.perf_counter() - start

    print(f"\n头部插入 10000 次:")
    print(f"  list:  {list_insert_time:.4f}s")
    print(f"  deque: {deque_insert_time:.4f}s")


# SRE 场景：用 deque 实现固定大小的日志缓冲区
from collections import deque
from typing import NamedTuple
from datetime import datetime


class LogEntry(NamedTuple):
    timestamp: datetime
    level: str
    message: str
    source: str


class LogRingBuffer:
    """
    环形日志缓冲区 — 保留最近 N 条日志
    SRE 用途：内存中保留最近的错误日志，用于故障排查
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._buffer: deque[LogEntry] = deque(maxlen=maxsize)
        self._maxsize = maxsize

    def push(self, entry: LogEntry) -> None:
        """添加日志条目，超过 maxsize 自动丢弃最旧的"""
        self._buffer.append(entry)

    def get_recent(self, n: int = 10) -> List[LogEntry]:
        """获取最近 n 条日志"""
        return list(self._buffer)[-n:]

    def get_by_level(self, level: str) -> List[LogEntry]:
        """按级别过滤日志"""
        return [e for e in self._buffer if e.level == level]

    def get_errors(self) -> List[LogEntry]:
        """获取所有 ERROR 和 CRITICAL 级别日志"""
        return [
            e for e in self._buffer
            if e.level in ("ERROR", "CRITICAL")
        ]

    def clear(self) -> None:
        """清空缓冲区"""
        self._buffer.clear()

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def is_full(self) -> bool:
        return len(self._buffer) == self._maxsize


# 使用示例
log_buffer = LogRingBuffer(maxsize=5000)
log_buffer.push(LogEntry(
    timestamp=datetime.now(),
    level="ERROR",
    message="Connection refused to database:5432",
    source="api-server"
))
```

#### 1.2 字典（dict）— 哈希表实现

**底层实现**：Python 3.6+ 使用紧凑哈希表，保持插入顺序。

```
┌─────────────────────────────────────────────────────────────────┐
│                    dict 内存布局 (Python 3.6+)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  紧凑哈希表结构:                                                │
│                                                                 │
│  indices (稀疏数组):                                            │
│  ┌────┬────┬────┬────┬────┬────┬────┬────┐                     │
│  │ -1 │  0 │ -1 │  2 │  1 │ -1 │ -1 │ -1 │                     │
│  └────┴────┴────┴────┴────┴────┴────┴────┘                     │
│   hash%8                                                      │
│                                                                 │
│  entries (紧凑数组，按插入顺序):                                 │
│  ┌─────────────────────────────────────────┐                   │
│  │ [0] hash=1234, key="host", value="web01"│                   │
│  │ [1] hash=5678, key="port", value=8080   │                   │
│  │ [2] hash=9012, key="timeout", value=30  │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
│  优势: 内存节省约 20-25%，且保持插入顺序                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**时间复杂度：**

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| `d[key]` | O(1) 均摊 | 哈希查找 |
| `d[key] = value` | O(1) 均摊 | 哈希插入 |
| `key in d` | O(1) 均摊 | 哈希查找 |
| `del d[key]` | O(1) 均摊 | 哈希删除 |
| `d.keys()` | O(1) | 返回视图对象 |

**SRE 实战：字典高级操作**

```python
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict, Counter, OrderedDict
import json


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典 — SRE 配置管理核心函数

    用途：将默认配置与环境特定配置合并

    Args:
        base: 基础配置
        override: 覆盖配置（优先级更高）

    Returns:
        合并后的配置字典
    """
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def flatten_dict(
    d: Dict[str, Any],
    parent_key: str = "",
    sep: str = ".",
) -> Dict[str, Any]:
    """
    将嵌套字典展平为单层 — 用于环境变量映射

    示例:
        {"database": {"host": "localhost", "port": 5432}}
        → {"database.host": "localhost", "database.port": 5432}
    """
    items: List[tuple[str, Any]] = []
    for key, value in d.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep).items())
        else:
            items.append((new_key, value))
    return dict(items)


def unflatten_dict(
    d: Dict[str, Any],
    sep: str = ".",
) -> Dict[str, Any]:
    """
    将展平的字典还原为嵌套结构 — 环境变量还原配置

    示例:
        {"database.host": "localhost", "database.port": 5432}
        → {"database": {"host": "localhost", "port": 5432}}
    """
    result: Dict[str, Any] = {}
    for key, value in d.items():
        parts = key.split(sep)
        current = result
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return result


def dict_diff(
    d1: Dict[str, Any],
    d2: Dict[str, Any],
) -> Dict[str, Any]:
    """
    计算两个字典的差异 — 用于配置变更检测

    Returns:
        差异字典，包含 added, removed, changed 三个键
    """
    added = {k: d2[k] for k in d2 if k not in d1}
    removed = {k: d1[k] for k in d1 if k not in d2}
    changed = {
        k: {"old": d1[k], "new": d2[k]}
        for k in d1 if k in d2 and d1[k] != d2[k]
    }
    return {"added": added, "removed": removed, "changed": changed}


# SRE 场景：统计 HTTP 状态码分布
def analyze_status_codes(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    分析 HTTP 日志中的状态码分布

    Args:
        logs: 日志记录列表，每条包含 "status" 字段

    Returns:
        包含统计信息的字典
    """
    status_counter = Counter(log.get("status", 0) for log in logs)
    total = sum(status_counter.values())

    # 按类别分组
    categories: Dict[str, int] = defaultdict(int)
    for status, count in status_counter.items():
        if 200 <= status < 300:
            categories["2xx_success"] += count
        elif 300 <= status < 400:
            categories["3xx_redirect"] += count
        elif 400 <= status < 500:
            categories["4xx_client_error"] += count
        elif 500 <= status < 600:
            categories["5xx_server_error"] += count
        else:
            categories["other"] += count

    return {
        "total_requests": total,
        "unique_status_codes": len(status_counter),
        "distribution": dict(status_counter.most_common()),
        "categories": dict(categories),
        "error_rate": (
            round((categories["4xx_client_error"] + categories["5xx_server_error"]) / total * 100, 2)
            if total > 0 else 0
        ),
    }


# Python 3.9+ 字典合并运算符
defaults = {"timeout": 30, "retries": 3, "log_level": "INFO"}
overrides = {"timeout": 60, "log_level": "DEBUG"}
config = defaults | overrides  # {'timeout': 60, 'retries': 3, 'log_level': 'DEBUG'}
```

#### 1.3 集合（set）— 哈希集合

```python
from typing import Set, FrozenSet, List, Dict, Any


# SRE 场景 1: 服务器差异比较
def compare_server_sets(
    expected: Set[str],
    actual: Set[str],
) -> Dict[str, Set[str]]:
    """
    比较期望的服务器集合与实际的服务器集合

    用途：CMDB 一致性检查，发现遗漏或多出的服务器
    """
    return {
        "missing": expected - actual,      # 应该有但没有的
        "extra": actual - expected,        # 不应该有但有的
        "common": expected & actual,       # 两边都有的
        "all": expected | actual,          # 所有服务器
    }


# SRE 场景 2: 服务依赖分析
def find_circular_dependencies(
    dependencies: Dict[str, Set[str]],
) -> List[tuple[str, str]]:
    """
    检测服务间的循环依赖

    Args:
        dependencies: 服务依赖图，{"service_a": {"service_b", "service_c"}}

    Returns:
        循环依赖对列表
    """
    circular: List[tuple[str, str]] = []
    for service, deps in dependencies.items():
        for dep in deps:
            if dep in dependencies and service in dependencies[dep]:
                # 避免重复 (A→B, B→A 只记录一次)
                pair = tuple(sorted([service, dep]))
                if pair not in circular:
                    circular.append(pair)
    return circular


# SRE 场景 3: 端口冲突检测
def detect_port_conflicts(
    services: Dict[str, Set[int]],
) -> Dict[int, Set[str]]:
    """
    检测多个服务使用相同端口的冲突

    Args:
        services: {"service_name": {port1, port2, ...}}

    Returns:
        {port: {conflicting_services}}
    """
    port_to_services: Dict[int, Set[str]] = {}
    for service, ports in services.items():
        for port in ports:
            port_to_services.setdefault(port, set()).add(service)

    # 只返回有冲突的端口
    return {
        port: svcs
        for port, svcs in port_to_services.items()
        if len(svcs) > 1
    }


# frozenset — 不可变集合，可以作为字典的键
SERVICE_LABELS = {
    frozenset({"env:prod", "region:us-east", "team:platform"}): "platform-us",
    frozenset({"env:prod", "region:eu-west", "team:platform"}): "platform-eu",
    frozenset({"env:staging", "region:us-east", "team:backend"}): "backend-staging",
}
```

#### 1.4 元组（tuple）— 不可变序列

```python
from typing import NamedTuple, Tuple, Dict, Any
from datetime import datetime


# NamedTuple — 带字段名的元组，比 dataclass 更轻量
class HealthCheckResult(NamedTuple):
    """健康检查结果 — 使用 NamedTuple 保证不可变"""
    host: str
    port: int
    is_healthy: bool
    response_time_ms: float
    status_code: int
    error: str = ""


class MetricPoint(NamedTuple):
    """Prometheus 风格的指标数据点"""
    name: str
    value: float
    timestamp: float
    labels: Tuple[Tuple[str, str], ...]  # 不可变的标签对


# 使用示例
result = HealthCheckResult(
    host="web-01",
    port=8080,
    is_healthy=True,
    response_time_ms=45.2,
    status_code=200,
)

# 元组解包
host, port, is_healthy, response_time, status, error = result
print(f"{host}:{port} → {status} ({response_time}ms)")

# 作为字典键（因为不可变）
cache: Dict[Tuple[str, int], HealthCheckResult] = {}
cache[(result.host, result.port)] = result


# SRE 场景：用元组表示不可变的配置快照
def create_config_snapshot(config: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
    """
    创建配置的不可变快照 — 用于配置变更检测

    将 dict 转换为 tuple of tuples，可以哈希、比较
    """
    def _convert(obj: Any) -> Any:
        if isinstance(obj, dict):
            return tuple(sorted((k, _convert(v)) for k, v in obj.items()))
        elif isinstance(obj, list):
            return tuple(_convert(item) for item in obj)
        return obj

    return tuple(sorted((k, _convert(v)) for k, v in config.items()))
```

---

### 2. 配置文件处理

#### 2.1 JSON — 最通用的数据交换格式

```
┌─────────────────────────────────────────────────────────────────┐
│                    JSON 特性                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  优点:                                                         │
│    - 所有编程语言都支持                                        │
│    - 结构清晰，人类可读                                        │
│    - 原生支持嵌套结构                                          │
│    - API 响应的标准格式                                        │
│                                                                 │
│  缺点:                                                         │
│    - 不支持注释                                                │
│    - 不支持尾逗号                                              │
│    - 没有日期类型（需用字符串）                                │
│    - 数字精度问题（大整数）                                    │
│                                                                 │
│  SRE 用途:                                                     │
│    - API 交互（Kubernetes, AWS, Prometheus）                   │
│    - 日志格式（结构化日志）                                    │
│    - 配置文件（简单场景）                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

```python
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
import uuid


# ============================================
# 基础用法
# ============================================

# 读取 JSON 文件
def load_json(path: Path) -> Any:
    """安全加载 JSON 文件"""
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: line {e.lineno} col {e.colno}")


# 写入 JSON 文件
def save_json(data: Any, path: Path, indent: int = 2) -> None:
    """保存数据到 JSON 文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data, f,
            indent=indent,
            ensure_ascii=False,  # 保留中文
            default=str,         # 处理不可序列化的类型
        )


# ============================================
# 自定义 JSON 编解码器 — 处理特殊类型
# ============================================

class SREJsonEncoder(json.JSONEncoder):
    """
    SRE 专用 JSON 编码器
    支持 datetime, date, Decimal, uuid, set, Path 等类型
    """

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, set):
            return sorted(list(obj))
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        return super().default(obj)


def dumps(obj: Any, **kwargs: Any) -> str:
    """使用 SRE 编码器序列化"""
    return json.dumps(obj, cls=SREJsonEncoder, ensure_ascii=False, **kwargs)


def loads(s: str, **kwargs: Any) -> Any:
    """反序列化 JSON 字符串"""
    return json.loads(s, **kwargs)


# ============================================
# JSON Lines (JSONL) — SRE 日志常用格式
# ============================================

def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """
    读取 JSON Lines 文件

    每行一个 JSON 对象，适合流式处理大文件
    SRE 场景：结构化日志文件
    """
    results: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: invalid JSON at line {line_num}: {e}")
    return results


def stream_jsonl(path: Path):
    """
    流式读取 JSON Lines 文件（生成器）

    适合处理大文件，不会一次性加载到内存
    """
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: invalid JSON at line {line_num}: {e}")


# SRE 实战：解析 Kubernetes API 响应
def parse_k8s_pod_list(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    解析 Kubernetes Pod 列表 API 响应

    API: GET /api/v1/pods
    """
    pods = []
    for item in response.get("items", []):
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        status = item.get("status", {})

        pods.append({
            "name": metadata.get("name"),
            "namespace": metadata.get("namespace"),
            "node": spec.get("nodeName"),
            "phase": status.get("phase"),
            "pod_ip": status.get("podIP"),
            "start_time": status.get("startTime"),
            "containers": [
                {
                    "name": c.get("name"),
                    "image": c.get("image"),
                    "ready": any(
                        cs.get("name") == c.get("name") and cs.get("ready")
                        for cs in status.get("containerStatuses", [])
                    ),
                }
                for c in spec.get("containers", [])
            ],
        })
    return pods
```

#### 2.2 YAML — SRE 配置文件首选

```
┌─────────────────────────────────────────────────────────────────┐
│                    YAML vs JSON 对比                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  特性          YAML                    JSON                     │
│  ─────────────────────────────────────────────────────────────  │
│  注释          支持 (#)                不支持                    │
│  可读性        更高（无引号/括号）      一般                      │
│  数据类型      丰富（日期、二进制）     基础类型                  │
│  锚点/引用     支持 (&anchor, *alias)  不支持                    │
│  多文档        支持 (---)              不支持                    │
│  文件大小      更小                    更大                      │
│  解析速度      较慢                    较快                      │
│  安全性        需要 safe_load          相对安全                  │
│                                                                 │
│  SRE 选择建议:                                                  │
│    - 配置文件 → YAML (Docker Compose, K8s, Ansible)             │
│    - API 交互 → JSON (标准化、跨语言)                           │
│    - 简单配置 → JSON (不需要注释时)                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

```python
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime


# ============================================
# 安全加载 — 必须使用 safe_load!
# ============================================

def load_yaml(path: Path) -> Any:
    """
    安全加载 YAML 文件

    重要：永远使用 safe_load，不要使用 yaml.load!
    yaml.load 可以执行任意 Python 代码（安全漏洞）
    """
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(data: Any, path: Path) -> None:
    """保存数据到 YAML 文件"""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f,
            default_flow_style=False,  # 使用块状格式
            allow_unicode=True,         # 支持中文
            sort_keys=False,            # 保持原始键顺序
            width=120,                  # 行宽
        )


# ============================================
# 多文档 YAML — K8s manifest 常用
# ============================================

def load_all_yaml(path: Path) -> List[Any]:
    """
    加载多文档 YAML 文件

    SRE 场景：一个文件包含多个 K8s 资源定义
    用 --- 分隔多个文档
    """
    with open(path, "r", encoding="utf-8") as f:
        return list(yaml.safe_load_all(f))


def save_all_yaml(documents: List[Any], path: Path) -> None:
    """保存多个文档到 YAML 文件"""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump_all(
            documents, f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )


# ============================================
# YAML 锚点和引用 — 配置复用
# ============================================

# YAML 文件示例 (docker-compose 风格):
"""
# common-env.yaml
x-common-env: &common-env
  LOG_LEVEL: info
  REDIS_HOST: redis.internal
  DB_HOST: postgres.internal

services:
  api:
    environment:
      <<: *common-env
      SERVICE_NAME: api-server
      PORT: "8080"

  worker:
    environment:
      <<: *common-env
      SERVICE_NAME: background-worker
      CONCURRENCY: "4"
"""


# ============================================
# YAML 自定义标签 — 处理特殊类型
# ============================================

def datetime_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> datetime:
    """处理 YAML 中的 datetime 标签"""
    value = loader.construct_scalar(node)
    return datetime.fromisoformat(str(value))


# 注册自定义标签
yaml.SafeLoader.add_constructor(
    "!datetime",
    datetime_constructor,
)


# ============================================
# SRE 实战：配置合并引擎
# ============================================

class ConfigMerger:
    """
    SRE 配置合并引擎

    支持：
    1. 基础配置 + 环境配置 合并
    2. YAML 锚点/引用
    3. 环境变量覆盖
    4. 配置验证
    """

    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir
        self._base_config: Dict[str, Any] = {}
        self._env_config: Dict[str, Any] = {}

    def load(self, environment: str) -> Dict[str, Any]:
        """
        加载并合并配置

        Args:
            environment: 环境名称 (dev/staging/prod)

        Returns:
            合并后的配置字典
        """
        # 加载基础配置
        base_path = self._config_dir / "default.yaml"
        self._base_config = load_yaml(base_path) or {}

        # 加载环境配置
        env_path = self._config_dir / f"{environment}.yaml"
        if env_path.exists():
            self._env_config = load_yaml(env_path) or {}
        else:
            self._env_config = {}

        # 合并
        merged = deep_merge_yaml(self._base_config, self._env_config)

        # 环境变量覆盖
        merged = self._apply_env_overrides(merged)

        return merged

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """从环境变量覆盖配置"""
        import os

        # 映射: 环境变量名 -> 配置路径
        mappings = {
            "APP_LOG_LEVEL": ("app", "log_level"),
            "APP_PORT": ("app", "port"),
            "DB_HOST": ("database", "host"),
            "DB_PORT": ("database", "port"),
            "DB_PASSWORD": ("database", "password"),
            "REDIS_HOST": ("redis", "host"),
            "REDIS_PORT": ("redis", "port"),
        }

        for env_var, path in mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                d = config
                for key in path[:-1]:
                    d = d.setdefault(key, {})
                # 类型转换
                if path[-1] in ("port",):
                    value = int(value)
                d[path[-1]] = value

        return config


def deep_merge_yaml(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """深度合并 YAML 配置"""
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge_yaml(result[key], value)
        else:
            result[key] = value
    return result
```

#### 2.3 TOML — Python 生态新标准

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOML 特性                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  优点:                                                         │
│    - 语义明确，类型丰富（日期、时间、表、数组）                 │
│    - 支持注释                                                    │
│    - 层次结构清晰（section 嵌套）                               │
│    - Python 3.11+ 内置 tomllib 模块                             │
│                                                                 │
│  缺点:                                                         │
│    - 深层嵌套时可读性下降                                       │
│    - 不如 YAML 灵活                                             │
│                                                                 │
│  SRE 用途:                                                     │
│    - pyproject.toml (Python 项目标准配置)                       │
│    - 简单的应用配置                                            │
│    - Cargo.toml (Rust), go.mod 的设计理念                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

```python
import sys
from typing import Any, Dict
from pathlib import Path

# Python 3.11+ 内置 tomllib (只读)
if sys.version_info >= (3, 11):
    import tomllib

    def load_toml(path: Path) -> Dict[str, Any]:
        """加载 TOML 文件 (Python 3.11+)"""
        if not path.exists():
            raise FileNotFoundError(f"TOML file not found: {path}")
        with open(path, "rb") as f:
            return tomllib.load(f)

else:
    # Python 3.10 及以下使用 tomli 库
    # pip install tomli
    import tomli  # type: ignore[import-untyped]

    def load_toml(path: Path) -> Dict[str, Any]:
        """加载 TOML 文件 (Python 3.10-)"""
        if not path.exists():
            raise FileNotFoundError(f"TOML file not found: {path}")
        with open(path, "rb") as f:
            return tomli.load(f)


# 写入 TOML 需要第三方库 tomli_w
# pip install tomli_w
try:
    import tomli_w

    def save_toml(data: Dict[str, Any], path: Path) -> None:
        """保存数据到 TOML 文件"""
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
except ImportError:
    def save_toml(data: Dict[str, Any], path: Path) -> None:
        raise ImportError("tomli_w not installed: pip install tomli_w")


# SRE 场景：读取 pyproject.toml 中的项目信息
def get_project_info(project_dir: Path) -> Dict[str, Any]:
    """读取项目的基本信息"""
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return {"error": "pyproject.toml not found"}

    config = load_toml(pyproject_path)

    poetry = config.get("tool", {}).get("poetry", {})
    return {
        "name": poetry.get("name", "unknown"),
        "version": poetry.get("version", "unknown"),
        "description": poetry.get("description", ""),
        "python_requires": poetry.get("dependencies", {}).get("python", "unknown"),
        "dependencies": list(poetry.get("dependencies", {}).keys()),
        "dev_dependencies": list(poetry.get("group", {}).get("dev", {}).get("dependencies", {}).keys()),
    }
```

#### 2.4 INI — 传统配置格式

```python
import configparser
from typing import Any, Dict, List, Optional
from pathlib import Path


def load_ini(path: Path) -> configparser.ConfigParser:
    """加载 INI 配置文件"""
    config = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation(),  # 支持 ${section:key} 引用
    )
    config.read(path, encoding="utf-8")
    return config


def ini_to_dict(config: configparser.ConfigParser) -> Dict[str, Dict[str, str]]:
    """将 ConfigParser 转换为嵌套字典"""
    result: Dict[str, Dict[str, str]] = {}
    for section in config.sections():
        result[section] = dict(config.items(section))
    return result


# SRE 场景：解析 supervisord 配置
"""
# /etc/supervisord.conf 示例
[program:api-server]
command=/opt/app/venv/bin/python -m app.main
directory=/opt/app
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/api-server.err.log
stdout_logfile=/var/log/supervisor/api-server.out.log
environment=APP_ENV="production",LOG_LEVEL="info"

[program:celery-worker]
command=/opt/app/venv/bin/celery -A app.worker worker
directory=/opt/app
autostart=true
autorestart=true
numprocs=4
process_name=%(program_name)s_%(process_num)02d
"""

def get_supervisor_programs(config_path: Path) -> List[Dict[str, str]]:
    """获取 supervisord 中所有 program 配置"""
    config = load_ini(config_path)
    programs = []
    for section in config.sections():
        if section.startswith("program:"):
            name = section.split(":", 1)[1]
            programs.append({
                "name": name,
                "command": config.get(section, "command", fallback=""),
                "directory": config.get(section, "directory", fallback=""),
                "autostart": config.get(section, "autostart", fallback="true"),
                "autorestart": config.get(section, "autorestart", fallback="true"),
            })
    return programs
```

---

### 3. Pydantic 数据验证

#### 3.1 为什么需要 Pydantic？

```
┌─────────────────────────────────────────────────────────────────┐
│                    配置验证的痛点                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  问题 1: 类型错误                                               │
│    config["port"] = "8080"   # 字符串，应该 int                │
│    → 连接时才发现错误，已来不及                                 │
│                                                                 │
│  问题 2: 缺少必填字段                                           │
│    config 没有 "database_host" 键                               │
│    → 运行时 KeyError 崩溃                                       │
│                                                                 │
│  问题 3: 值范围错误                                             │
│    config["port"] = 99999   # 超出有效端口范围                  │
│    → 绑定失败，错误信息不明确                                   │
│                                                                 │
│  问题 4: 嵌套配置验证                                           │
│    配置层层嵌套，手动验证代码冗长且易错                         │
│                                                                 │
│  Pydantic 解决方案:                                             │
│    - 声明式定义数据模型                                        │
│    - 自动类型转换和验证                                        │
│    - 详细的错误信息                                            │
│    - 与 JSON Schema 集成                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Pydantic 基础用法

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path
import re


class Environment(str, Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseModel):
    """数据库配置模型"""
    host: str = Field(
        default="localhost",
        description="数据库主机地址",
        examples=["db.prod.internal", "10.0.1.100"],
    )
    port: int = Field(
        default=5432,
        ge=1,
        le=65535,
        description="数据库端口",
    )
    username: str = Field(
        default="sre",
        min_length=1,
        description="数据库用户名",
    )
    password: str = Field(
        default="",
        description="数据库密码（建议从环境变量读取）",
    )
    database: str = Field(
        default="sre_db",
        min_length=1,
        description="数据库名称",
    )
    pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="连接池大小",
    )
    ssl_mode: str = Field(
        default="prefer",
        description="SSL 模式",
    )

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """验证主机地址格式"""
        # 允许 IP 地址或主机名
        ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        hostname_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$"
        if not (re.match(ip_pattern, v) or re.match(hostname_pattern, v)):
            raise ValueError(f"Invalid host: {v}")
        return v

    @field_validator("ssl_mode")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        valid_modes = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
        if v not in valid_modes:
            raise ValueError(f"Invalid ssl_mode: {v}. Must be one of {valid_modes}")
        return v


class RedisConfig(BaseModel):
    """Redis 配置模型"""
    host: str = "localhost"
    port: int = Field(default=6379, ge=1, le=65535)
    db: int = Field(default=0, ge=0, le=15)
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: float = Field(default=5.0, gt=0)


class AlertConfig(BaseModel):
    """告警配置模型"""
    enabled: bool = True
    webhook_url: Optional[str] = None
    channels: List[str] = Field(default_factory=list)
    severity_threshold: LogLevel = LogLevel.WARNING
    rate_limit_per_minute: int = Field(default=10, ge=1)
    cooldown_seconds: int = Field(default=300, ge=0)

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError(f"Invalid webhook URL: {v}")
        return v


class AppConfig(BaseModel):
    """应用主配置模型"""
    app_name: str = Field(
        default="sre-toolkit",
        min_length=1,
        max_length=64,
    )
    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    debug: bool = False

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)

    extra_tags: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_production_config(self) -> "AppConfig":
        """生产环境的额外验证"""
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                raise ValueError("debug cannot be True in production")
            if self.database.password == "":
                raise ValueError("database password is required in production")
            if self.alerts.enabled and not self.alerts.webhook_url:
                raise ValueError("webhook_url is required when alerts are enabled in production")
        return self
```

#### 3.3 Pydantic 配置加载实战

```python
import os
import yaml
import json
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import ValidationError


def load_app_config(
    config_path: Path,
    environment: Optional[str] = None,
) -> AppConfig:
    """
    加载并验证应用配置

    优先级: 环境变量 > 环境配置文件 > 基础配置文件

    Args:
        config_path: 基础配置文件路径
        environment: 环境名称

    Returns:
        验证后的 AppConfig 对象

    Raises:
        ValidationError: 配置验证失败
        FileNotFoundError: 配置文件不存在
    """
    # 加载基础配置
    raw_config = _load_config_file(config_path)

    # 加载环境配置
    if environment:
        env_config_path = config_path.parent / f"{environment}.yaml"
        if env_config_path.exists():
            env_config = _load_config_file(env_config_path)
            raw_config = _deep_merge(raw_config, env_config)

    # 环境变量覆盖
    raw_config = _apply_env_overrides(raw_config)

    # Pydantic 验证
    try:
        return AppConfig(**raw_config)
    except ValidationError as e:
        # 提供友好的错误信息
        errors = []
        for error in e.errors():
            loc = " → ".join(str(l) for l in error["loc"])
            errors.append(f"  [{loc}] {error['msg']} (type: {error['type']})")
        raise ValueError(
            f"Configuration validation failed:\n" + "\n".join(errors)
        ) from e


def _load_config_file(path: Path) -> Dict[str, Any]:
    """根据扩展名加载配置文件"""
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    elif suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    elif suffix == ".toml":
        return load_toml(path)
    else:
        raise ValueError(f"Unsupported config format: {suffix}")


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """深度合并两个字典"""
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """从环境变量覆盖配置"""
    env_mappings = {
        "APP_NAME": ("app_name",),
        "APP_ENV": ("environment",),
        "APP_LOG_LEVEL": ("log_level",),
        "APP_DEBUG": ("debug",),
        "DB_HOST": ("database", "host"),
        "DB_PORT": ("database", "port"),
        "DB_PASSWORD": ("database", "password"),
        "DB_NAME": ("database", "database"),
        "DB_POOL_SIZE": ("database", "pool_size"),
        "REDIS_HOST": ("redis", "host"),
        "REDIS_PORT": ("redis", "port"),
        "REDIS_PASSWORD": ("redis", "password"),
        "ALERT_WEBHOOK": ("alerts", "webhook_url"),
        "ALERT_ENABLED": ("alerts", "enabled"),
    }

    for env_var, path in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None:
            d = config
            for key in path[:-1]:
                d = d.setdefault(key, {})
            # 类型转换
            if path[-1] in ("port", "pool_size"):
                value = int(value)
            elif path[-1] in ("debug", "enabled"):
                value = value.lower() in ("true", "1", "yes")
            d[path[-1]] = value

    return config
```

#### 3.4 Pydantic 配置热加载

```python
import time
import hashlib
from pathlib import Path
from typing import Optional, Callable, Any
from threading import Thread, Event


class ConfigWatcher:
    """
    配置文件热加载器

    监控配置文件变化，自动重新加载并通知回调函数

    SRE 场景：
    - 运行时修改配置不需要重启服务
    - 动态调整日志级别、告警阈值等
    """

    def __init__(
        self,
        config_path: Path,
        environment: Optional[str] = None,
        reload_interval: float = 5.0,
        on_reload: Optional[Callable[[AppConfig], None]] = None,
    ) -> None:
        self._config_path = config_path
        self._environment = environment
        self._reload_interval = reload_interval
        self._on_reload = on_reload
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._current_config: Optional[AppConfig] = None
        self._last_hash: str = ""

    def start(self) -> AppConfig:
        """启动配置监控，返回初始配置"""
        self._current_config = load_app_config(
            self._config_path, self._environment
        )
        self._last_hash = self._compute_config_hash()
        self._thread = Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        return self._current_config

    def stop(self) -> None:
        """停止配置监控"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._reload_interval + 1)

    @property
    def config(self) -> Optional[AppConfig]:
        """获取当前配置"""
        return self._current_config

    def _compute_config_hash(self) -> str:
        """计算配置文件的哈希值"""
        if not self._config_path.exists():
            return ""
        content = self._config_path.read_bytes()
        return hashlib.md5(content).hexdigest()

    def _watch_loop(self) -> None:
        """监控循环"""
        while not self._stop_event.is_set():
            self._stop_event.wait(self._reload_interval)
            if self._stop_event.is_set():
                break

            current_hash = self._compute_config_hash()
            if current_hash != self._last_hash:
                try:
                    new_config = load_app_config(
                        self._config_path, self._environment
                    )
                    self._current_config = new_config
                    self._last_hash = current_hash
                    if self._on_reload:
                        self._on_reload(new_config)
                    print(f"[ConfigWatcher] Config reloaded at {time.strftime('%H:%M:%S')}")
                except Exception as e:
                    print(f"[ConfigWatcher] Reload failed: {e}")


# 使用示例
def on_config_change(new_config: AppConfig) -> None:
    """配置变更回调"""
    print(f"Log level changed to: {new_config.log_level.value}")
    # 动态更新日志级别
    import logging
    logging.getLogger().setLevel(new_config.log_level.value)


if __name__ == "__main__":
    watcher = ConfigWatcher(
        config_path=Path("config/default.yaml"),
        environment="production",
        reload_interval=10.0,
        on_reload=on_config_change,
    )
    config = watcher.start()
    print(f"App: {config.app_name}, Env: {config.environment.value}")

    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
```

---

## 💻 实战练习

### 练习 1：基础操作 — 配置格式转换器

**目标**：编写一个配置格式转换工具，支持 JSON/YAML/TOML/INI 互相转换

```python
#!/usr/bin/env python3
"""
配置格式转换工具

用法:
    python config_converter.py input.yaml output.json
    python config_converter.py input.json output.toml
"""
import sys
import json
import yaml
import configparser
from pathlib import Path
from typing import Any, Dict


def load_config(path: Path) -> Any:
    """根据扩展名加载配置"""
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        with open(path, "r") as f:
            return yaml.safe_load(f)
    elif suffix == ".json":
        with open(path, "r") as f:
            return json.load(f)
    elif suffix == ".toml":
        import tomllib
        with open(path, "rb") as f:
            return tomllib.load(f)
    elif suffix == ".ini":
        config = configparser.ConfigParser()
        config.read(path)
        return {s: dict(config.items(s)) for s in config.sections()}
    else:
        raise ValueError(f"Unsupported format: {suffix}")


def save_config(data: Any, path: Path) -> None:
    """根据扩展名保存配置"""
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    elif suffix == ".json":
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    elif suffix == ".toml":
        import tomli_w
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
    elif suffix == ".ini":
        config = configparser.ConfigParser()
        for section, values in data.items():
            if isinstance(values, dict):
                config[section] = {str(k): str(v) for k, v in values.items()}
        with open(path, "w") as f:
            config.write(f)
    else:
        raise ValueError(f"Unsupported format: {suffix}")


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python config_converter.py <input> <output>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    data = load_config(input_path)
    save_config(data, output_path)
    print(f"Converted: {input_path} → {output_path}")


if __name__ == "__main__":
    main()
```

### 练习 2：进阶场景 — Pydantic 配置模型

**目标**：为一个 SRE 监控系统定义完整的 Pydantic 配置模型

```python
"""
练习：定义 SRE 监控系统的 Pydantic 配置模型

要求：
1. 支持 Prometheus、Grafana、AlertManager 三个组件的配置
2. 每个组件有独立的连接配置（host, port, timeout）
3. 支持环境变量覆盖
4. 生产环境有额外的验证规则
5. 能生成 JSON Schema 用于文档
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from enum import Enum
from pathlib import Path
import yaml
import json


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PrometheusConfig(BaseModel):
    """Prometheus 配置"""
    host: str = "localhost"
    port: int = Field(default=9090, ge=1, le=65535)
    scheme: str = Field(default="http")
    scrape_interval: str = "15s"
    evaluation_interval: str = "15s"
    retention_days: int = Field(default=15, ge=1, le=365)
    external_labels: Dict[str, str] = Field(default_factory=dict)

    @field_validator("scheme")
    @classmethod
    def validate_scheme(cls, v: str) -> str:
        if v not in ("http", "https"):
            raise ValueError(f"Invalid scheme: {v}")
        return v

    @property
    def base_url(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"


class GrafanaConfig(BaseModel):
    """Grafana 配置"""
    host: str = "localhost"
    port: int = Field(default=3000, ge=1, le=65535)
    admin_user: str = "admin"
    admin_password: str = ""
    org_name: str = "SRE"
    allow_embedding: bool = False

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class AlertRoute(BaseModel):
    """告警路由配置"""
    match: Dict[str, str] = Field(..., description="标签匹配规则")
    receiver: str = Field(..., description="接收者名称")
    group_wait: str = "30s"
    group_interval: str = "5m"
    repeat_interval: str = "4h"


class AlertManagerConfig(BaseModel):
    """AlertManager 配置"""
    host: str = "localhost"
    port: int = Field(default=9093, ge=1, le=65535)
    routes: List[AlertRoute] = Field(default_factory=list)
    receivers: List[str] = Field(default_factory=list)
    resolve_timeout: str = "5m"


class MonitoringConfig(BaseModel):
    """监控系统主配置"""
    prometheus: PrometheusConfig = Field(default_factory=PrometheusConfig)
    grafana: GrafanaConfig = Field(default_factory=GrafanaConfig)
    alertmanager: AlertManagerConfig = Field(default_factory=AlertManagerConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "MonitoringConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_json_schema(self) -> str:
        return json.dumps(self.model_json_schema(), indent=2, ensure_ascii=False)


# 测试
if __name__ == "__main__":
    config = MonitoringConfig(
        prometheus=PrometheusConfig(
            host="prometheus.prod.internal",
            retention_days=30,
            external_labels={"cluster": "prod-us-east"},
        ),
        grafana=GrafanaConfig(
            host="grafana.prod.internal",
            admin_password="secret",
        ),
        alertmanager=AlertManagerConfig(
            host="alertmanager.prod.internal",
            routes=[
                AlertRoute(
                    match={"severity": "critical"},
                    receiver="pagerduty",
                ),
                AlertRoute(
                    match={"severity": "warning"},
                    receiver="slack",
                ),
            ],
        ),
    )
    print(config.prometheus.base_url)  # http://prometheus.prod.internal:9090
    print(config.to_json_schema()[:200])
```

### 练习 3：故障排查挑战 — 配置问题诊断

**场景**：以下配置加载代码有多个问题，请找出并修复。

```python
# broken_config.py — 配置加载有问题
import yaml
import json

def load_config(path):
    with open(path) as f:
        if path.endswith('.yaml'):
            return yaml.load(f)  # 问题 1: 安全问题
        elif path.endswith('.json'):
            return json.load(f)

def merge_config(base, override):
    for key, value in override.items():
        if key in base:
            base[key] = value  # 问题 2: 不支持深度合并
    return base  # 问题 3: 修改了原始 base

def get_config_value(config, key_path):
    keys = key_path.split('.')
    value = config
    for key in keys:
        value = value[key]  # 问题 4: 没有处理 KeyError
    return value

def save_config(config, path):
    with open(path, 'w') as f:
        yaml.dump(config, f)  # 问题 5: 没有 ensure_ascii
```

**预期发现的问题**：
1. `yaml.load(f)` 应使用 `yaml.safe_load(f)` — 任意代码执行漏洞
2. 合并不支持嵌套字典 — 浅合并导致子配置丢失
3. 修改了原始 base 字典 — 应该创建副本
4. 没有处理键不存在的情况 — 应该用 `.get()` 或 try/except
5. YAML 输出不支持中文 — 应加 `allow_unicode=True`

---

## 🎯 面试题精选

### 问题 1：Python 的 list 和 deque 有什么区别？各适合什么场景？

**参考答案**：

| 特性 | list | deque |
|------|------|-------|
| 底层实现 | 动态数组 | 双向链表 |
| 尾部追加 | O(1) 均摊 | O(1) |
| 头部插入 | O(n) | O(1) |
| 随机访问 | O(1) | O(n) |
| 内存布局 | 连续 | 分散 |

SRE 场景选择：
- 需要随机访问（按索引取元素）→ list
- 需要频繁头部操作（FIFO 队列）→ deque
- 固定大小的缓冲区（日志环形缓冲）→ deque(maxlen=N)
- 需要排序、切片 → list

### 问题 2：Python dict 的插入顺序保证是什么时候引入的？

**参考答案**：

- Python 3.6：CPython 实现层面保证插入顺序（紧凑哈希表的副作用）
- Python 3.7：语言规范层面保证插入顺序（所有实现必须遵守）

这意味着 `dict` 不再需要 `OrderedDict`（除非需要 `move_to_end()` 等方法）。

SRE 影响：配置文件加载后，键的顺序会被保留。这对于需要按顺序处理配置项的场景很重要。

### 问题 3：yaml.load() 和 yaml.safe_load() 有什么区别？为什么必须用 safe_load？

**参考答案**：

`yaml.load()` 可以执行任意 Python 代码，因为 YAML 规范支持标签（tag）来指定数据类型：

```yaml
# 恶意 YAML — 可以执行任意命令
!!python/object/apply:os.system ['rm -rf /']
```

`yaml.safe_load()` 只加载基础 YAML 类型（字符串、数字、列表、字典、布尔、None），不允许执行 Python 代码。

**安全建议**：永远使用 `yaml.safe_load()`，除非你完全信任输入来源且确实需要加载自定义类型。

### 问题 4：Pydantic 的 field_validator 和 model_validator 有什么区别？

**参考答案**：

- `field_validator`：验证单个字段，可以在字段值上做格式检查、范围检查、正则匹配等
- `model_validator`：验证整个模型，可以检查多个字段之间的关系

```python
# field_validator — 单字段验证
@field_validator("port")
@classmethod
def validate_port(cls, v):
    if not 1 <= v <= 65535:
        raise ValueError("Port must be 1-65535")
    return v

# model_validator — 跨字段验证
@model_validator(mode="after")
def validate_production(self):
    if self.environment == "production" and self.debug:
        raise ValueError("Cannot enable debug in production")
    return self
```

### 问题 5：如何实现配置热加载（不重启服务更新配置）？

**参考答案**：

有三种常见方案：

1. **文件监控**：使用 watchdog 库或轮询检测配置文件变化
2. **信号触发**：发送 SIGHUP 信号触发重新加载
3. **API 触发**：暴露 HTTP API 端点触发重新加载

推荐方案：文件监控 + 回调通知

```python
# 核心思路
class ConfigWatcher:
    def __init__(self, path, callback):
        self.path = path
        self.callback = callback
        self.last_hash = ""

    def watch(self):
        while True:
            current_hash = md5(self.path.read_bytes())
            if current_hash != self.last_hash:
                new_config = load_config(self.path)
                self.callback(new_config)
                self.last_hash = current_hash
            sleep(5)
```

### 问题 6：JSON、YAML、TOML、INI 四种配置格式各适合什么场景？

**参考答案**：

| 格式 | 适合场景 | 不适合场景 |
|------|---------|-----------|
| JSON | API 交互、结构化日志 | 需要注释的配置文件 |
| YAML | K8s/Docker Compose/Ansible | 简单的键值配置 |
| TOML | Python 项目配置 (pyproject.toml) | 深层嵌套的复杂配置 |
| INI | 传统应用配置 (supervisord) | 需要复杂数据类型的配置 |

SRE 建议：
- 新项目优先用 YAML（可读性好、支持注释）
- Python 项目用 TOML（pyproject.toml 标准）
- API 响应用 JSON（标准化）
- 遗留系统用 INI（兼容性）

### 问题 7：如何处理配置中的敏感信息（密码、API Key）？

**参考答案**：

```python
# 方案 1: 环境变量
db_password = os.environ.get("DB_PASSWORD")

# 方方案 2: Secret 文件 (Kubernetes Secret)
secret_path = Path("/var/run/secrets/db-password")
db_password = secret_path.read_text().strip() if secret_path.exists() else None

# 方案 3: 加密配置文件
from cryptography.fernet import Fernet
key = os.environ.get("CONFIG_ENCRYPTION_KEY")
fernet = Fernet(key.encode())
encrypted_value = fernet.decrypt(config["db_password_encrypted"].encode()).decode()

# 方案 4: Secret Manager (HashiCorp Vault, AWS Secrets Manager)
import hvac
client = hvac.Client(url="http://vault:8200")
secret = client.secrets.kv.v2.read_secret_version(path="database")
db_password = secret["data"]["data"]["password"]
```

**最佳实践**：
1. 永远不要将敏感信息提交到 Git
2. 使用 `.gitignore` 排除 `.env` 文件
3. 配置文件中用占位符（如 `${DB_PASSWORD}`），运行时从环境变量替换
4. 使用 Secret Manager 管理生产环境的敏感信息

### 问题 8：Python 的 `__slots__` 有什么作用？在 SRE 中有什么应用场景？

**参考答案**：

`__slots__` 限制实例只能拥有指定的属性，优点：
1. **内存节省**：不需要 `__dict__`，每个实例节省约 100 字节
2. **属性保护**：防止意外添加新属性
3. **访问速度**：属性访问略快

```python
class MetricPoint:
    __slots__ = ("name", "value", "timestamp", "labels")

    def __init__(self, name, value, timestamp, labels):
        self.name = name
        self.value = value
        self.timestamp = timestamp
        self.labels = labels
```

SRE 场景：
- 需要创建大量小对象时（如每秒处理数万个指标数据点）
- 内存敏感的监控 Agent
- 需要防止属性名拼写错误的场景

---

## 📚 深入阅读

### 官方文档
- [Python 数据结构文档](https://docs.python.org/3/tutorial/datastructures.html)
- [JSON 规范 RFC 8259](https://datatracker.ietf.org/doc/html/rfc8259)
- [YAML 规范](https://yaml.org/spec/1.2.2/)
- [TOML 规范](https://toml.io/en/v1.0.0)
- [Pydantic 官方文档](https://docs.pydantic.dev/)

### 推荐书籍
- 《Fluent Python》Luciano Ramalho — 第 2 章：数据结构
- 《Python Cookbook》David Beazley — 第 1 章：数据结构与算法
- 《Effective Python》Brett Slatkin — 第 4 章：列表与字典

### 技术博客
- [Real Python — Python Dict](https://realpython.com/python-dicts/)
- [Real Python — JSON in Python](https://realpython.com/python-json/)
- [Real Python — YAML in Python](https://realpython.com/python-yaml/)

---

## ✅ 自检清单

### 理论检查
- [ ] 理解 list/dict/set/tuple 的底层实现和时间复杂度
- [ ] 知道 JSON/YAML/TOML/INI 各自的优缺点和适用场景
- [ ] 理解 Pydantic 的验证流程（field_validator vs model_validator）
- [ ] 知道 `yaml.load()` 的安全风险
- [ ] 理解配置合并的深度合并 vs 浅合并

### 实操检查
- [ ] 能用 json/yaml/tomllib 读写配置文件
- [ ] 能编写 Pydantic 模型进行配置验证
- [ ] 能实现多环境配置合并和环境变量覆盖
- [ ] 能编写 JSON Lines 流式解析器处理大文件
- [ ] 能实现配置文件热加载机制

### 能力验证
- [ ] 能为一个 SRE 项目设计完整的配置管理方案
- [ ] 能编写配置格式转换工具
- [ ] 能用 Pydantic 生成 JSON Schema 用于 API 文档
