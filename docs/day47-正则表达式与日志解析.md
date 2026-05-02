# Day 47: Python 正则表达式与日志解析

> 📅 日期：2026-05-02
> 📖 学习主题：Python 正则表达式与日志解析
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

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
| `*` | 0次或多次 | `ab*c` |
| `+` | 1次或多次 | `ab+c` |
| `?` | 0次或1次 | `ab?c` |
| `{n,m}` | n到m次 | `\d{2,4}` |
| `^` | 行首 | `^ERROR` |
| `$` | 行尾 | `done$` |
| `()` | 分组 | `(\d+)-(\d+)` |
| `\|` | 或 | `error\|warning` |
| `[]` | 字符集 | `[a-zA-Z0-9]` |

### 3. 解析 Nginx 日志

```python
import re
from collections import Counter

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
status_counts = Counter(log["status"] for log in logs)
print(status_counts)

# Top IPs
ip_counts = Counter(log["ip"] for log in logs)
for ip, count in ip_counts.most_common(10):
    print(f"{ip}: {count} requests")
```

### 4. 贪婪 vs 非贪婪

```python
# 贪婪（默认）
re.findall(r'<.*>', '<b>bold</b> <i>italic</i>')
# ['<b>bold</b> <i>italic</i>']  ← 匹配了整个字符串

# 非贪婪（加 ?）
re.findall(r'<.*?>', '<b>bold</b> <i>italic</i>')
# ['<b>', '</b>', '<i>', '</i>']  ← 每个标签单独匹配
```

---

## 🏗️ 实战：日志分析工具

```python
#!/usr/bin/env python3
"""Analyze log files and generate reports."""

import re
import argparse
from collections import Counter
from datetime import datetime


def analyze_access_log(filepath, top_n=10):
    """Analyze Nginx/Apache access log."""
    pattern = re.compile(
        r'(\d+\.\d+\.\d+\.\d+).*?"(\w+) (\S+).*?" (\d{3})'
    )

    ips = Counter()
    paths = Counter()
    status_codes = Counter()

    with open(filepath) as f:
        for line in f:
            m = pattern.search(line)
            if m:
                ips[m.group(1)] += 1
                paths[m.group(3)] += 1
                status_codes[m.group(4)] += 1

    print(f"=== Log Analysis: {filepath} ===\n")

    print(f"Total requests: {sum(ips.values())}\n")

    print("Top IPs:")
    for ip, count in ips.most_common(top_n):
        print(f"  {ip:20s} {count}")

    print("\nTop Paths:")
    for path, count in paths.most_common(top_n):
        print(f"  {path:40s} {count}")

    print("\nStatus Codes:")
    for code, count in sorted(status_codes.items()):
        print(f"  {code}: {count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Log file path")
    parser.add_argument("-n", "--top", type=int, default=10)
    args = parser.parse_args()
    analyze_access_log(args.file, args.top)
```

---

## 🧪 练习题

### 练习 1：提取错误日志

从 syslog 中提取所有包含 "error" 或 "fail" 的行，并提取时间戳和进程名。

<details>
<summary>答案</summary>

```python
import re

pattern = re.compile(
    r'(?P<time>\w+\s+\d+\s+\d+:\d+:\d+)\s+'
    r'(?P<host>\S+)\s+'
    r'(?P<process>\S+?)(?:\[\d+\])?:\s*'
    r'.*?(?:error|fail)',
    re.IGNORECASE
)

with open("/var/log/syslog") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            print(f"{m['time']} {m['process']}: {line.strip()}")
```
</details>

---

## 🧪 练习题

### 练习 1：手机号提取

从文本中提取所有中国手机号（11 位数字，1 开头）。

<details>
<summary>答案</summary>

```python
import re
pattern = re.compile(r'1[3-9]\d{9}')
phones = pattern.findall(text)
```
</details>

---

## 📚 扩展阅读

- [regex101.com 在线测试](https://regex101.com/)
- [Python re 文档](https://docs.python.org/3/library/re.html)
