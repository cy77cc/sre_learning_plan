# Day 44: Python 数据类型与配置文件处理

> 📅 日期：2026-05-02
> 📖 学习主题：Python 数据类型与配置文件处理
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 Python 核心数据结构（list/dict/tuple/set）
- 能处理 JSON、YAML、INI、TOML 配置文件
- 理解数据结构在 SRE 工具中的实际应用场景

---

## 📖 详细知识点

### 1. 列表与字典

```python
# 列表推导式
servers = ["web01", "web02", "db01"]
active = [s for s in servers if s.startswith("web")]
# ['web01', 'web02']

# 嵌套列表展平
nested = [[1, 2], [3, 4], [5]]
flat = [x for row in nested for x in row]

# 字典操作
config = {"host": "0.0.0.0", "port": 8080}
config.get("timeout", 30)  # 安全访问

# 字典推导式
squared = {x: x**2 for x in range(5)}

# Python 3.9+ 字典合并
defaults = {"timeout": 30, "retries": 3}
overrides = {"timeout": 60}
config = defaults | overrides  # {'timeout': 60, 'retries': 3}
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

# JSON 验证
try:
    data = json.loads(raw_text)
except json.JSONDecodeError as e:
    print(f"Invalid JSON at line {e.lineno}")
```

### 3. YAML 处理

```python
# pip install pyyaml
import yaml

# 安全加载
with open("docker-compose.yml") as f:
    config = yaml.safe_load(f)

# 写入
with open("output.yaml", "w") as f:
    yaml.dump(config, f, default_flow_style=False)

# 多文档 YAML
with open("k8s-manifests.yaml") as f:
    docs = list(yaml.safe_load_all(f))
```

### 4. INI / TOML

```python
import configparser
config = configparser.ConfigParser()
config.read("app.ini")
db_host = config["database"]["host"]

# TOML (Python 3.11+ 内置)
import tomllib
with open("pyproject.toml", "rb") as f:
    data = tomllib.load(f)
```

---

## 🏗️ 实战：配置合并工具

```python
#!/usr/bin/env python3
"""Deep merge configuration files."""
import json
import sys


def deep_merge(base, override):
    """Recursively merge two dicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def main():
    if len(sys.argv) < 3:
        print("Usage: merge.py base.json override.json")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        base = json.load(f)
    with open(sys.argv[2]) as f:
        override = json.load(f)

    merged = deep_merge(base, override)
    print(json.dumps(merged, indent=2))


if __name__ == "__main__":
    main()
```

---

## 🧪 练习题

### 练习 1：日志统计

从 JSON 格式的日志文件中统计每个状态码的出现次数。

<details>
<summary>答案</summary>

```python
import json
from collections import Counter

with open("access.json") as f:
    logs = json.load(f)

counts = Counter(entry["status"] for entry in logs)
for status, count in counts.most_common():
    print(f"{status}: {count}")
```
</details>

---

## 🧪 练习题

### 练习 1：配置验证器

编写一个 YAML 配置验证器，检查必填字段是否存在且类型正确。

<details>
<summary>答案</summary>

```python
import yaml
import sys

def validate(config, schema):
    errors = []
    for key, expected in schema.items():
        if key not in config:
            errors.append(f"Missing: {key}")
        elif not isinstance(config[key], expected):
            errors.append(f"Wrong type: {key}")
    return errors

schema = {
    "server": dict,
    "database": dict,
    "log_level": str,
    "max_connections": int,
}

with open("config.yaml") as f:
    config = yaml.safe_load(f)

errors = validate(config, schema)
if errors:
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("Configuration valid")
```
</details>

---

## 📚 扩展阅读

- [Python 数据结构文档](https://docs.python.org/3/tutorial/datastructures.html)
- [JSON 规范 RFC 8259](https://datatracker.ietf.org/doc/html/rfc8259)
