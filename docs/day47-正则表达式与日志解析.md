# Day 47: 正则表达式与日志解析

> 📅 日期：2026-05-03
> 📖 学习主题：Python re 模块、正则表达式编译优化、分组捕获、日志格式化解析、多行日志处理
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 43-46 Python 基础系列

## 🎯 学习目标

- 深入掌握 Python re 模块的核心方法和高级特性
- 理解正则表达式编译优化的原理和最佳实践
- 熟练使用分组捕获和命名分组解析复杂日志格式
- 能解析 Nginx/Apache/syslog/K8s 等 SRE 常见日志格式
- 掌握多行日志处理和日志聚合分析技术

---

## 📖 核心知识点

### 1. re 模块核心方法

#### 1.1 正则表达式引擎原理

```
┌─────────────────────────────────────────────────────────────────┐
│                    正则表达式匹配引擎                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Python re 模块使用回溯式 (backtracking) NFA 引擎               │
│                                                                 │
│  匹配过程:                                                      │
│  1. 编译阶段: 正则表达式 → 内部状态机 (pattern object)          │
│  2. 匹配阶段: 从左到右尝试匹配，失败时回溯                      │
│                                                                 │
│  回溯示例:                                                      │
│  模式: a.*b                                                    │
│  字符串: "axxbyb"                                               │
│                                                                 │
│  步骤 1: a 匹配 a ✅                                            │
│  步骤 2: .* 贪婪匹配 "xxbyb" ✅                                 │
│  步骤 3: b 匹配失败 (已到末尾) ❌                               │
│  步骤 4: .* 回溯，释放 "b" → 匹配 "xxb"                        │
│  步骤 5: b 匹配 b ✅                                            │
│  匹配成功: "axxb"                                               │
│                                                                 │
│  性能注意:                                                      │
│  - 贪婪量词 (.*  .+) 会导致大量回溯                            │
│  - 非贪婪量词 (.*? .+?) 回溯更少                               │
│  - 固定字符串前缀可以加速匹配                                   │
│  - 编译后的 pattern 对象可以复用，避免重复编译                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 核心方法对比

```python
import re
from typing import List, Optional, Match


# ============================================
# re.search — 搜索第一个匹配
# ============================================

def search_example() -> None:
    """search: 在字符串任意位置搜索第一个匹配"""
    text = "Error: connection timeout at 10.0.0.1:8080"

    # 搜索 IP 地址
    match = re.search(r'\d+\.\d+\.\d+\.\d+', text)
    if match:
        print(f"Found IP: {match.group()}")  # 10.0.0.1
        print(f"Position: {match.start()}-{match.end()}")  # 29-37

    # 搜索端口
    match = re.search(r':(\d+)', text)
    if match:
        print(f"Full match: {match.group()}")    # :8080
        print(f"Group 1: {match.group(1)}")      # 8080


# ============================================
# re.match — 从头匹配
# ============================================

def match_example() -> None:
    """match: 只从字符串开头匹配"""
    text = "2026-05-03 ERROR Connection failed"

    # match 只从开头匹配
    m = re.match(r'(\d{4}-\d{2}-\d{2})\s+(\w+)', text)
    if m:
        print(f"Date: {m.group(1)}")   # 2026-05-03
        print(f"Level: {m.group(2)}")  # ERROR

    # match 不会匹配中间的内容
    m = re.match(r'ERROR', text)
    print(m)  # None（因为开头是日期，不是 ERROR）


# ============================================
# re.findall — 查找所有匹配
# ============================================

def findall_example() -> None:
    """findall: 返回所有匹配的列表"""
    text = "10.0.0.1:8080, 10.0.0.2:3306, 10.0.0.3:6379"

    # 无分组 — 返回匹配字符串列表
    ips = re.findall(r'\d+\.\d+\.\d+\.\d+', text)
    print(ips)  # ['10.0.0.1', '10.0.0.2', '10.0.0.3']

    # 有分组 — 返回分组内容的元组列表
    pairs = re.findall(r'(\d+\.\d+\.\d+\.\d+):(\d+)', text)
    print(pairs)  # [('10.0.0.1', '8080'), ('10.0.0.2', '3306'), ('10.0.0.3', '6379')]

    # 多个分组 — 返回元组列表
    for ip, port in pairs:
        print(f"  {ip}:{port}")


# ============================================
# re.finditer — 返回迭代器
# ============================================

def finditer_example() -> None:
    """finditer: 返回 Match 对象的迭代器（内存高效）"""
    text = "Error at 10.0.0.1, Warning at 10.0.0.2, Error at 10.0.0.3"

    # finditer 适合处理大文本
    for m in re.finditer(r'(\w+)\s+at\s+(\d+\.\d+\.\d+\.\d+)', text):
        print(f"[{m.start():3d}] {m.group(1)}: {m.group(2)}")


# ============================================
# re.sub — 替换
# ============================================

def sub_example() -> None:
    """sub: 替换匹配的内容"""
    text = "Password: secret123, API Key: sk-abc456"

    # 脱敏处理
    masked = re.sub(
        r'(Password|API Key):\s*\S+',
        lambda m: f"{m.group(1)}: ***",
        text,
    )
    print(masked)  # Password: ***, API Key: ***

    # 使用反向引用
    log = "2026-05-03T10:00:00 ERROR Connection failed"
    reformatted = re.sub(
        r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\s+(\w+)',
        r'[\1 \2] \3',
        log,
    )
    print(reformatted)  # [2026-05-03 10:00:00] ERROR


# ============================================
# re.split — 分割
# ============================================

def split_example() -> None:
    """split: 按模式分割字符串"""
    text = "web-01,web-02;api-01|api-02 worker-01"

    # 按多种分隔符分割
    hosts = re.split(r'[,;|\s]+', text)
    print(hosts)  # ['web-01', 'web-02', 'api-01', 'api-02', 'worker-01']

    # 保留分隔符（使用捕获组）
    parts = re.split(r'([,;|])', text)
    print(parts)  # ['web-01', ',', 'web-02', ';', 'api-01', '|', ...]
```

---

### 2. 编译优化

#### 2.1 为什么需要编译？

```
┌─────────────────────────────────────────────────────────────────┐
│                    正则表达式编译优化                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  每次调用 re.search() 等函数时:                                  │
│  1. 解析正则表达式字符串                                        │
│  2. 编译为内部状态机                                            │
│  3. 执行匹配                                                    │
│                                                                 │
│  如果同一个正则表达式使用多次:                                   │
│  re.search(pattern, text1)  → 编译 + 匹配                      │
│  re.search(pattern, text2)  → 编译 + 匹配 (重复编译!)           │
│  re.search(pattern, text3)  → 编译 + 匹配 (重复编译!)           │
│                                                                 │
│  使用 re.compile():                                             │
│  compiled = re.compile(pattern)  → 编译一次                     │
│  compiled.search(text1)          → 只匹配                      │
│  compiled.search(text2)          → 只匹配                      │
│  compiled.search(text3)          → 只匹配                      │
│                                                                 │
│  性能提升: 10-50% (取决于使用频率)                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 编译最佳实践

```python
import re
from typing import Pattern


# ============================================
# 模块级编译 — 最佳实践
# ============================================

# 在模块级别编译正则表达式（只编译一次）
LOG_PATTERN: Pattern = re.compile(
    r'(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)'
    r'\s+'
    r'(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)'
    r'\s+'
    r'\[(?P<logger>[^\]]+)\]'
    r'\s+'
    r'(?P<message>.*)'
)

IP_PATTERN: Pattern = re.compile(
    r'\b(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
)

NGINX_ACCESS_PATTERN: Pattern = re.compile(
    r'(?P<remote_addr>\S+)\s+'
    r'-\s+'  # remote user (通常为 -)
    r'(?P<remote_user>\S+)\s+'
    r'\[(?P<time_local>[^\]]+)\]\s+'
    r'"(?P<request>[^"]*)"\s+'
    r'(?P<status>\d{3})\s+'
    r'(?P<body_bytes_sent>\d+)\s+'
    r'"(?P<http_referer>[^"]*)"\s+'
    r'"(?P<http_user_agent>[^"]*)"'
    r'(?:\s+"(?P<http_x_forwarded_for>[^"]*)")?'
)


# ============================================
# 编译标志 — 增强匹配能力
# ============================================

# IGNORECASE — 不区分大小写
case_insensitive = re.compile(r'error|warning|critical', re.IGNORECASE)

# MULTILINE — ^ 和 $ 匹配每行的开头和结尾
multiline = re.compile(r'^ERROR.*$', re.MULTILINE)

# DOTALL — . 匹配包括换行符在内的所有字符
dotall = re.compile(r'<script>.*?</script>', re.DOTALL)

# VERBOSE — 允许使用注释和空白（提高复杂正则的可读性）
nginx_log_pattern = re.compile(r"""
    (?P<ip>\d+\.\d+\.\d+\.\d+)   # 客户端 IP
    \s+                            # 空白
    \S+                            # remote user
    \s+                            # 空白
    \S+                            # auth user
    \s+                            # 空白
    \[(?P<time>[^\]]+)\]           # 时间戳
    \s+                            # 空白
    "(?P<method>\w+)               # HTTP 方法
    \s+                            # 空白
    (?P<path>\S+)                  # 请求路径
    \s+                            # 空白
    (?P<protocol>[^"]*)"           # 协议版本
    \s+                            # 空白
    (?P<status>\d{3})              # 状态码
    \s+                            # 空白
    (?P<bytes>\d+)                 # 响应大小
""", re.VERBOSE)

# 组合多个标志
combined = re.compile(r'^error.*$', re.IGNORECASE | re.MULTILINE | re.DOTALL)
```

#### 2.3 SRE 实战：日志解析器类

```python
import re
from typing import Pattern, Dict, List, Optional, Any, Generator
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    """解析后的日志条目"""
    timestamp: Optional[datetime] = None
    level: str = ""
    logger_name: str = ""
    message: str = ""
    raw: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


class LogParser:
    """
    通用日志解析器

    支持多种日志格式：
    - Python 标准日志格式
    - Nginx 访问日志
    - syslog 格式
    - JSON 日志
    """

    # 预编译的常用模式
    PYTHON_LOG: Pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d+)?)'
        r'\s+'
        r'(?P<level>\w+)'
        r'\s+'
        r'(?P<logger>\S+)'
        r'\s+'
        r'(?P<message>.*)'
    )

    NGINX_ACCESS: Pattern = re.compile(
        r'(?P<remote_addr>\S+)\s+'
        r'\S+\s+\S+\s+'
        r'\[(?P<time_local>[^\]]+)\]\s+'
        r'"(?P<request>[^"]*)"\s+'
        r'(?P<status>\d{3})\s+'
        r'(?P<body_bytes>\d+)\s+'
        r'"(?P<referer>[^"]*)"\s+'
        r'"(?P<user_agent>[^"]*)"'
    )

    SYSLOG: Pattern = re.compile(
        r'(?P<timestamp>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<hostname>\S+)\s+'
        r'(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?:\s+'
        r'(?P<message>.*)'
    )

    def __init__(self, format_type: str = "python") -> None:
        """
        初始化解析器

        Args:
            format_type: 日志格式类型 (python/nginx/syslog)
        """
        self._format_type = format_type
        self._pattern = self._get_pattern(format_type)

    def _get_pattern(self, format_type: str) -> Pattern:
        """获取对应格式的正则模式"""
        patterns = {
            "python": self.PYTHON_LOG,
            "nginx": self.NGINX_ACCESS,
            "syslog": self.SYSLOG,
        }
        if format_type not in patterns:
            raise ValueError(f"Unsupported format: {format_type}")
        return patterns[format_type]

    def parse_line(self, line: str) -> Optional[LogEntry]:
        """
        解析单行日志

        Args:
            line: 日志行

        Returns:
            LogEntry 对象，解析失败返回 None
        """
        match = self._pattern.match(line.strip())
        if not match:
            return LogEntry(raw=line, message=line)

        groups = match.groupdict()

        if self._format_type == "python":
            return LogEntry(
                timestamp=self._parse_timestamp(groups.get("timestamp", "")),
                level=groups.get("level", ""),
                logger_name=groups.get("logger", ""),
                message=groups.get("message", ""),
                raw=line,
            )
        elif self._format_type == "nginx":
            return LogEntry(
                timestamp=self._parse_nginx_time(groups.get("time_local", "")),
                level="INFO",
                message=groups.get("request", ""),
                raw=line,
                extra={
                    "remote_addr": groups.get("remote_addr", ""),
                    "status": int(groups.get("status", 0)),
                    "body_bytes": int(groups.get("body_bytes", 0)),
                    "referer": groups.get("referer", ""),
                    "user_agent": groups.get("user_agent", ""),
                },
            )
        elif self._format_type == "syslog":
            return LogEntry(
                timestamp=self._parse_syslog_time(groups.get("timestamp", "")),
                level="INFO",
                logger_name=groups.get("process", ""),
                message=groups.get("message", ""),
                raw=line,
                extra={
                    "hostname": groups.get("hostname", ""),
                    "pid": groups.get("pid", ""),
                },
            )

        return LogEntry(raw=line, message=line)

    def parse_file(
        self,
        path: Path,
        filter_level: Optional[str] = None,
    ) -> Generator[LogEntry, None, None]:
        """
        流式解析日志文件

        Args:
            path: 日志文件路径
            filter_level: 过滤的日志级别（可选）

        Yields:
            LogEntry 对象
        """
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                entry = self.parse_line(line)
                if entry is None:
                    continue
                if filter_level and entry.level != filter_level:
                    continue
                yield entry

    @staticmethod
    def _parse_timestamp(ts_str: str) -> Optional[datetime]:
        """解析 Python 日志时间戳"""
        for fmt in (
            "%Y-%m-%d %H:%M:%S,%f",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_nginx_time(time_str: str) -> Optional[datetime]:
        """解析 Nginx 时间格式"""
        try:
            return datetime.strptime(time_str, "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            return None

    @staticmethod
    def _parse_syslog_time(time_str: str) -> Optional[datetime]:
        """解析 syslog 时间格式"""
        try:
            # syslog 格式: "May  3 10:00:00"
            current_year = datetime.now().year
            dt = datetime.strptime(f"{current_year} {time_str}", "%Y %b %d %H:%M:%S")
            return dt
        except ValueError:
            return None
```

---

### 3. 分组捕获

#### 3.1 基础分组

```python
import re
from typing import List, Tuple, Optional, Dict


# ============================================
# 普通分组 — 用 () 包裹
# ============================================

text = "2026-05-03 10:30:45 ERROR [api-server] Connection timeout to db:5432"

# 提取时间、级别、消息
m = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(\w+)\s+\[([^\]]+)\]\s+(.*)', text)
if m:
    date = m.group(1)       # 2026-05-03
    time_str = m.group(2)   # 10:30:45
    level = m.group(3)      # ERROR
    logger = m.group(4)     # api-server
    message = m.group(5)    # Connection timeout to db:5432
    all_groups = m.groups()  # ('2026-05-03', '10:30:45', 'ERROR', 'api-server', '...')


# ============================================
# 命名分组 — 用 (?P<name>...) 语法
# ============================================

PATTERN = re.compile(
    r'(?P<date>\d{4}-\d{2}-\d{2})\s+'
    r'(?P<time>\d{2}:\d{2}:\d{2})\s+'
    r'(?P<level>\w+)\s+'
    r'\[(?P<logger>[^\]]+)\]\s+'
    r'(?P<message>.*)'
)

m = PATTERN.search(text)
if m:
    # 通过名称访问
    print(m.group("date"))     # 2026-05-03
    print(m.group("level"))    # ERROR

    # 获取所有命名分组
    print(m.groupdict())
    # {'date': '2026-05-03', 'time': '10:30:45', 'level': 'ERROR', ...}


# ============================================
# 非捕获分组 — 用 (?:...) 语法
# ============================================

# 匹配 HTTP 或 HTTPS URL，但不捕获协议部分
url_pattern = re.compile(r'https?://(?P<host>[^/]+)(?P<path>/\S*)?')

m = url_pattern.search("Visit https://api.example.com/v1/users for details")
if m:
    print(m.group("host"))  # api.example.com
    print(m.group("path"))  # /v1/users
    # 注意：没有 group(1) 对应 https://


# ============================================
# 反向引用 — 引用之前捕获的分组
# ============================================

# 匹配重复的单词
duplicate_pattern = re.compile(r'\b(\w+)\s+\1\b')
text = "the the quick brown fox jumped over the the lazy dog"
matches = duplicate_pattern.findall(text)
print(matches)  # ['the', 'the']

# 匹配 HTML 标签对
tag_pattern = re.compile(r'<(?P<tag>\w+)>.*?</(?P=tag)>')
html = "<div>Hello</div><span>World</span>"
matches = tag_pattern.findall(html)
print(matches)  # ['div', 'span']
```

#### 3.2 高级分组技巧

```python
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


# ============================================
# 前向断言和后向断言
# ============================================

# 前向肯定断言 (?=...) — 匹配后面跟着特定内容的位置
# 提取后面跟着 GB 的数字
text = "Disk usage: 85GB, Memory: 16GB, Swap: 4GB"
sizes = re.findall(r'(\d+)(?=GB)', text)
print(sizes)  # ['85', '16', '4']

# 前向否定断言 (?!...) — 匹配后面不跟着特定内容的位置
# 提取非 localhost 的 IP
text = "Connect to 10.0.0.1 or 192.168.1.1 or 127.0.0.1"
ips = re.findall(r'\d+\.\d+\.\d+\.\d+(?!.*localhost)', text)

# 后向肯定断言 (?<=...) — 匹配前面有特定内容的位置
# 提取冒号后面的值
text = "host: web-01, port: 8080, timeout: 30"
values = re.findall(r'(?<=:\s)\S+', text)
print(values)  # ['web-01', '8080', '30']

# 后向否定断言 (?<!...) — 匹配前面没有特定内容的位置
# 提取非注释行的内容
lines = [
    "# This is a comment",
    "server_name = example.com",
    "# Another comment",
    "listen = 8080",
]
non_comment = [line for line in lines if re.search(r'(?<!#.*)=\s*\S+', line)]


# ============================================
# SRE 实战：Nginx 配置解析器
# ============================================

@dataclass
class NginxLocation:
    """Nginx location 配置"""
    path: str
    modifier: str  # =, ~, ~*, ^~, 或空
    directives: Dict[str, str]
    proxy_pass: Optional[str] = None


class NginxConfigParser:
    """
    Nginx 配置解析器 — 使用正则表达式

    SRE 用途：自动化分析 Nginx 配置，发现潜在问题
    """

    # 预编译正则
    LOCATION_PATTERN = re.compile(
        r'location\s+'
        r'(?P<modifier>[=~*^]+)?\s*'
        r'(?P<path>\S+)\s*\{',
        re.VERBOSE,
    )

    DIRECTIVE_PATTERN = re.compile(
        r'(?P<key>\w[\w_]*)\s+(?P<value>[^;]+);',
    )

    UPSTREAM_PATTERN = re.compile(
        r'upstream\s+(?P<name>\w+)\s*\{(?P<body>[^}]+)\}',
        re.DOTALL,
    )

    SERVER_BLOCK_PATTERN = re.compile(
        r'server\s*\{(?P<body>(?:[^{}]|{[^{}]*})*)\}',
        re.DOTALL,
    )

    def parse_locations(self, config_text: str) -> List[NginxLocation]:
        """解析所有 location 块"""
        locations = []

        for match in self.LOCATION_PATTERN.finditer(config_text):
            path = match.group("path")
            modifier = match.group("modifier") or ""

            # 提取 location 块内的指令
            start = match.end()
            brace_count = 1
            pos = start
            while pos < len(config_text) and brace_count > 0:
                if config_text[pos] == '{':
                    brace_count += 1
                elif config_text[pos] == '}':
                    brace_count -= 1
                pos += 1

            block_body = config_text[start:pos - 1]

            directives = {}
            proxy_pass = None
            for dm in self.DIRECTIVE_PATTERN.finditer(block_body):
                key = dm.group("key")
                value = dm.group("value").strip()
                directives[key] = value
                if key == "proxy_pass":
                    proxy_pass = value

            locations.append(NginxLocation(
                path=path,
                modifier=modifier,
                directives=directives,
                proxy_pass=proxy_pass,
            ))

        return locations

    def parse_upstreams(self, config_text: str) -> Dict[str, List[str]]:
        """解析 upstream 块"""
        upstreams = {}

        for match in self.UPSTREAM_PATTERN.finditer(config_text):
            name = match.group("name")
            body = match.group("body")

            servers = re.findall(r'server\s+([^;]+);', body)
            upstreams[name] = [s.strip() for s in servers]

        return upstreams

    def find_security_issues(self, config_text: str) -> List[str]:
        """检查 Nginx 配置的安全问题"""
        issues = []

        # 检查 server_tokens
        if 'server_tokens off' not in config_text:
            issues.append("WARNING: server_tokens not disabled (information leakage)")

        # 检查 X-Frame-Options
        if 'X-Frame-Options' not in config_text:
            issues.append("WARNING: X-Frame-Options header not set (clickjacking risk)")

        # 检查 X-Content-Type-Options
        if 'X-Content-Type-Options' not in config_text:
            issues.append("WARNING: X-Content-Type-Options not set (MIME sniffing risk)")

        # 检查 SSL 配置
        if 'ssl_protocols' in config_text:
            if re.search(r'SSLv[23]', config_text):
                issues.append("CRITICAL: SSLv2/SSLv3 enabled (POODLE vulnerability)")

        # 检查 default_server
        if 'listen 80;' in config_text and 'default_server' not in config_text:
            issues.append("WARNING: No default_server defined (host header attack)")

        return issues
```

---

### 4. 日志格式化解析

#### 4.1 常见日志格式

```
┌─────────────────────────────────────────────────────────────────┐
│                    SRE 常见日志格式                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Python 标准日志                                             │
│  2026-05-03 10:30:45,123 ERROR [sre_toolkit.health] Connection  │
│  格式: %(asctime)s %(levelname)s [%(name)s] %(message)s         │
│                                                                 │
│  2. Nginx 访问日志 (Combined)                                   │
│  10.0.0.1 - - [03/May/2026:10:30:45 +0000] "GET /api/health    │
│  HTTP/1.1" 200 1234 "-" "curl/7.68.0"                          │
│                                                                 │
│  3. Nginx 错误日志                                              │
│  2026/05/03 10:30:45 [error] 1234#0: *5678 connect() failed    │
│  (111: Connection refused)                                      │
│                                                                 │
│  4. syslog (RFC 3164)                                           │
│  May  3 10:30:45 web-01 nginx: 10.0.0.1 - GET / HTTP/1.1 200   │
│                                                                 │
│  5. JSON 结构化日志                                             │
│  {"timestamp":"2026-05-03T10:30:45Z","level":"ERROR",...}       │
│                                                                 │
│  6. Kubernetes 日志                                             │
│  2026-05-03T10:30:45.123Z stdout F Error connecting to db      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.2 多种日志格式解析

```python
import re
import json
from typing import Dict, List, Optional, Any, Generator, Pattern
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from collections import Counter, defaultdict


@dataclass
class ParsedLog:
    """解析后的通用日志结构"""
    timestamp: Optional[datetime] = None
    level: str = "INFO"
    source: str = ""
    message: str = ""
    raw: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)


class MultiFormatLogParser:
    """
    多格式日志解析器

    自动检测日志格式并解析
    """

    # 格式检测模式
    FORMAT_DETECTORS: Dict[str, Pattern] = {
        "json": re.compile(r'^\s*\{'),
        "nginx_access": re.compile(r'^\d+\.\d+\.\d+\.\d+\s'),
        "nginx_error": re.compile(r'^\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}'),
        "python": re.compile(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'),
        "syslog": re.compile(r'^\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}'),
        "k8s": re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z'),
    }

    # 各格式的解析模式
    PYTHON_PATTERN: Pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:[,\.]\d+)?)'
        r'\s+(?P<level>\w+)'
        r'\s+\[(?P<source>[^\]]+)\]'
        r'\s+(?P<message>.*)'
    )

    NGINX_ACCESS_PATTERN: Pattern = re.compile(
        r'(?P<remote_addr>\S+)\s+'
        r'(?P<remote_user>\S+)\s+'
        r'(?P<auth_user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<request>[^"]*)"\s+'
        r'(?P<status>\d{3})\s+'
        r'(?P<body_bytes>\d+)\s+'
        r'"(?P<referer>[^"]*)"\s+'
        r'"(?P<user_agent>[^"]*)"'
    )

    NGINX_ERROR_PATTERN: Pattern = re.compile(
        r'(?P<timestamp>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})'
        r'\s+\[(?P<level>\w+)\]'
        r'\s+(?P<pid>\d+)#(?P<tid>\d+)'
        r':\s+\*(?P<cid>\d+)'
        r'\s+(?P<message>.*)'
    )

    SYSLOG_PATTERN: Pattern = re.compile(
        r'(?P<timestamp>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2})'
        r'\s+(?P<hostname>\S+)'
        r'\s+(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?:'
        r'\s+(?P<message>.*)'
    )

    K8S_PATTERN: Pattern = re.compile(
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)'
        r'\s+(?P<stream>stdout|stderr)'
        r'\s+(?P<tag>F|P)'
        r'\s+(?P<message>.*)'
    )

    def detect_format(self, line: str) -> str:
        """自动检测日志格式"""
        for fmt, pattern in self.FORMAT_DETECTORS.items():
            if pattern.match(line):
                return fmt
        return "unknown"

    def parse_line(self, line: str, format_type: Optional[str] = None) -> ParsedLog:
        """
        解析单行日志

        Args:
            line: 日志行
            format_type: 格式类型（None 则自动检测）

        Returns:
            ParsedLog 对象
        """
        line = line.rstrip()
        if not format_type:
            format_type = self.detect_format(line)

        if format_type == "json":
            return self._parse_json(line)
        elif format_type == "nginx_access":
            return self._parse_nginx_access(line)
        elif format_type == "nginx_error":
            return self._parse_nginx_error(line)
        elif format_type == "python":
            return self._parse_python(line)
        elif format_type == "syslog":
            return self._parse_syslog(line)
        elif format_type == "k8s":
            return self._parse_k8s(line)
        else:
            return ParsedLog(message=line, raw=line)

    def _parse_json(self, line: str) -> ParsedLog:
        """解析 JSON 日志"""
        try:
            data = json.loads(line)
            return ParsedLog(
                timestamp=self._parse_iso_timestamp(data.get("timestamp", "")),
                level=data.get("level", data.get("severity", "INFO")).upper(),
                source=data.get("logger", data.get("service", "")),
                message=data.get("message", data.get("msg", "")),
                raw=line,
                fields={k: v for k, v in data.items()
                       if k not in ("timestamp", "level", "severity", "logger", "message", "msg")},
            )
        except json.JSONDecodeError:
            return ParsedLog(message=line, raw=line)

    def _parse_nginx_access(self, line: str) -> ParsedLog:
        """解析 Nginx 访问日志"""
        m = self.NGINX_ACCESS_PATTERN.match(line)
        if not m:
            return ParsedLog(message=line, raw=line)

        g = m.groupdict()
        status = int(g.get("status", 0))

        # 根据状态码确定级别
        if status >= 500:
            level = "ERROR"
        elif status >= 400:
            level = "WARNING"
        else:
            level = "INFO"

        return ParsedLog(
            timestamp=self._parse_nginx_time(g.get("timestamp", "")),
            level=level,
            source="nginx",
            message=f"{g.get('request', '')} → {status}",
            raw=line,
            fields={
                "remote_addr": g.get("remote_addr", ""),
                "request": g.get("request", ""),
                "status": status,
                "body_bytes": int(g.get("body_bytes", 0)),
                "referer": g.get("referer", ""),
                "user_agent": g.get("user_agent", ""),
            },
        )

    def _parse_nginx_error(self, line: str) -> ParsedLog:
        """解析 Nginx 错误日志"""
        m = self.NGINX_ERROR_PATTERN.match(line)
        if not m:
            return ParsedLog(message=line, raw=line)

        g = m.groupdict()
        level_map = {"emerg": "CRITICAL", "alert": "CRITICAL", "crit": "CRITICAL",
                     "error": "ERROR", "warn": "WARNING", "notice": "INFO", "info": "INFO", "debug": "DEBUG"}

        return ParsedLog(
            timestamp=self._parse_nginx_time(g.get("timestamp", "")),
            level=level_map.get(g.get("level", ""), "INFO"),
            source="nginx",
            message=g.get("message", ""),
            raw=line,
            fields={
                "pid": g.get("pid", ""),
                "connection_id": g.get("cid", ""),
            },
        )

    def _parse_python(self, line: str) -> ParsedLog:
        """解析 Python 标准日志"""
        m = self.PYTHON_PATTERN.match(line)
        if not m:
            return ParsedLog(message=line, raw=line)

        g = m.groupdict()
        return ParsedLog(
            timestamp=self._parse_python_time(g.get("timestamp", "")),
            level=g.get("level", "INFO"),
            source=g.get("source", ""),
            message=g.get("message", ""),
            raw=line,
        )

    def _parse_syslog(self, line: str) -> ParsedLog:
        """解析 syslog 日志"""
        m = self.SYSLOG_PATTERN.match(line)
        if not m:
            return ParsedLog(message=line, raw=line)

        g = m.groupdict()
        return ParsedLog(
            timestamp=self._parse_syslog_time(g.get("timestamp", "")),
            level="INFO",
            source=g.get("process", ""),
            message=g.get("message", ""),
            raw=line,
            fields={
                "hostname": g.get("hostname", ""),
                "pid": g.get("pid", ""),
            },
        )

    def _parse_k8s(self, line: str) -> ParsedLog:
        """解析 Kubernetes 日志"""
        m = self.K8S_PATTERN.match(line)
        if not m:
            return ParsedLog(message=line, raw=line)

        g = m.groupdict()
        stream = g.get("stream", "stdout")
        level = "ERROR" if stream == "stderr" else "INFO"

        return ParsedLog(
            timestamp=self._parse_iso_timestamp(g.get("timestamp", "")),
            level=level,
            source="k8s",
            message=g.get("message", ""),
            raw=line,
            fields={
                "stream": stream,
                "tag": g.get("tag", ""),
            },
        )

    @staticmethod
    def _parse_iso_timestamp(ts: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_nginx_time(ts: str) -> Optional[datetime]:
        try:
            return datetime.strptime(ts, "%d/%b/%Y:%H:%M:%S %z")
        except ValueError:
            return None

    @staticmethod
    def _parse_python_time(ts: str) -> Optional[datetime]:
        for fmt in ("%Y-%m-%d %H:%M:%S,%f", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_syslog_time(ts: str) -> Optional[datetime]:
        try:
            year = datetime.now().year
            return datetime.strptime(f"{year} {ts}", "%Y %b %d %H:%M:%S")
        except ValueError:
            return None
```

---

### 5. 多行日志处理

#### 5.1 多行日志的挑战

```
┌─────────────────────────────────────────────────────────────────┐
│                    多行日志示例                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Python traceback (多行):                                       │
│  2026-05-03 10:30:45 ERROR [api] Request failed                │
│  Traceback (most recent call last):                            │
│    File "/app/handler.py", line 42, in process                 │
│      result = db.query(sql)                                     │
│    File "/app/db.py", line 15, in query                        │
│      raise ConnectionError("timeout")                          │
│  ConnectionError: timeout                                       │
│                                                                 │
│  Java stack trace (多行):                                       │
│  2026-05-03 10:30:45 ERROR com.example.App - Error occurred   │
│  java.lang.NullPointerException                                │
│      at com.example.App.process(App.java:42)                   │
│      at com.example.App.main(App.java:10)                      │
│                                                                 │
│  问题：每行一个日志条目的假设不成立                             │
│  需要将多行合并为一个完整的日志条目                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.2 多行日志合并

```python
import re
from typing import Generator, List, Optional, Pattern
from pathlib import Path


class MultilineLogProcessor:
    """
    多行日志处理器

    将跨多行的日志条目（如 Python traceback）合并为单条记录

    SRE 用途：
    - Python 应用的 traceback 日志
    - Java 应用的 stack trace 日志
    - 自定义多行日志格式
    """

    # 新日志行的起始模式
    LOG_START_PATTERNS: List[Pattern] = [
        # Python 标准日志
        re.compile(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'),
        # Nginx 访问日志
        re.compile(r'^\d+\.\d+\.\d+\.\d+\s'),
        # syslog
        re.compile(r'^\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}'),
        # ISO 时间戳
        re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'),
        # JSON 日志
        re.compile(r'^\s*\{'),
    ]

    def __init__(
        self,
        start_patterns: Optional[List[Pattern]] = None,
        max_lines_per_entry: int = 100,
    ) -> None:
        """
        初始化多行日志处理器

        Args:
            start_patterns: 日志行起始模式列表
            max_lines_per_entry: 每个日志条目的最大行数（防止无限合并）
        """
        self._start_patterns = start_patterns or self.LOG_START_PATTERNS
        self._max_lines = max_lines_per_entry

    def _is_log_start(self, line: str) -> bool:
        """判断是否是新日志条目的开始"""
        return any(p.match(line) for p in self._start_patterns)

    def process_file(self, path: Path) -> Generator[str, None, None]:
        """
        处理多行日志文件，合并多行条目

        Args:
            path: 日志文件路径

        Yields:
            合并后的日志条目（每条用换行符连接多行）
        """
        current_entry_lines: List[str] = []

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")

                if self._is_log_start(line):
                    # 新条目开始，输出之前的条目
                    if current_entry_lines:
                        yield "\n".join(current_entry_lines)
                    current_entry_lines = [line]
                else:
                    # 当前行是上一条目的延续
                    if current_entry_lines:
                        if len(current_entry_lines) < self._max_lines:
                            current_entry_lines.append(line)
                    else:
                        # 没有前一条目，作为独立行
                        current_entry_lines = [line]

            # 输出最后一条
            if current_entry_lines:
                yield "\n".join(current_entry_lines)

    def process_file_with_context(
        self,
        path: Path,
        context_lines: int = 5,
    ) -> Generator[dict, None, None]:
        """
        处理日志文件，为每条错误日志附带上下文

        Args:
            path: 日志文件路径
            context_lines: 错误日志前后的上下文行数

        Yields:
            包含日志内容和上下文的字典
        """
        all_lines: List[str] = []
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = [line.rstrip("\n") for line in f]

        # 找到所有错误行的索引
        error_indices = [
            i for i, line in enumerate(all_lines)
            if re.search(r'\b(ERROR|CRITICAL|Exception|Traceback)\b', line)
        ]

        for idx in error_indices:
            start = max(0, idx - context_lines)
            end = min(len(all_lines), idx + context_lines + 1)

            yield {
                "error_line": all_lines[idx],
                "line_number": idx + 1,
                "context_before": all_lines[start:idx],
                "context_after": all_lines[idx + 1:end],
                "full_context": all_lines[start:end],
            }


# SRE 实战：traceback 提取器
class TracebackExtractor:
    """
    从日志中提取 Python traceback

    SRE 用途：
    - 错误聚合（相同 traceback 归为一类）
    - 根因分析（提取最终异常类型和消息）
    """

    TRACEBACK_START: Pattern = re.compile(r'^Traceback \(most recent call last\):')
    EXCEPTION_LINE: Pattern = re.compile(r'^(\w+(?:\.\w+)*)\s*:\s*(.*)')

    def extract_tracebacks(self, text: str) -> List[dict]:
        """
        从文本中提取所有 traceback

        Args:
            text: 包含 traceback 的文本

        Returns:
            traceback 信息列表
        """
        tracebacks = []
        lines = text.split("\n")
        i = 0

        while i < len(lines):
            if self.TRACEBACK_START.match(lines[i]):
                tb_lines = [lines[i]]
                i += 1

                # 收集 traceback 的所有行
                while i < len(lines):
                    line = lines[i]
                    # traceback 结束于异常行（非空格开头，非 File/Traceback）
                    if (line and not line.startswith(" ") and
                        not line.startswith("File") and
                        not self.TRACEBACK_START.match(line)):
                        tb_lines.append(line)
                        break
                    tb_lines.append(line)
                    i += 1

                # 解析异常信息
                exception_match = self.EXCEPTION_LINE.match(tb_lines[-1])
                exception_type = exception_match.group(1) if exception_match else "Unknown"
                exception_msg = exception_match.group(2) if exception_match else ""

                # 提取文件和行号
                file_matches = re.findall(r'File "([^"]+)", line (\d+)', "\n".join(tb_lines))
                last_file = file_matches[-1] if file_matches else ("unknown", "0")

                tracebacks.append({
                    "full_traceback": "\n".join(tb_lines),
                    "exception_type": exception_type,
                    "exception_message": exception_msg,
                    "last_file": last_file[0],
                    "last_line": int(last_file[1]),
                    "hash": self._hash_traceback(tb_lines),
                })

            i += 1

        return tracebacks

    def _hash_traceback(self, tb_lines: List[str]) -> str:
        """
        计算 traceback 的哈希值 — 用于错误聚合

        去除变量值，只保留结构
        """
        import hashlib

        # 提取文件名和行号（忽略具体变量值）
        structure = []
        for line in tb_lines:
            file_match = re.search(r'File "([^"]+)", line (\d+)', line)
            if file_match:
                structure.append(f"{file_match.group(1)}:{file_match.group(2)}")
            elif re.match(r'^\w+(?:\.\w+)*:', line):
                structure.append(line.split(":")[0])

        hash_input = "\n".join(structure)
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]


# 使用示例
if __name__ == "__main__":
    sample_log = """
2026-05-03 10:30:45 ERROR [api] Request failed
Traceback (most recent call last):
  File "/app/handler.py", line 42, in process
    result = db.query(sql)
  File "/app/db.py", line 15, in query
    raise ConnectionError("timeout to database:5432")
ConnectionError: timeout to database:5432
2026-05-03 10:30:46 INFO [api] Retrying...
2026-05-03 10:30:50 ERROR [api] Request failed again
Traceback (most recent call last):
  File "/app/handler.py", line 42, in process
    result = db.query(sql)
  File "/app/db.py", line 15, in query
    raise ConnectionError("timeout to database:5432")
ConnectionError: timeout to database:5432
"""

    extractor = TracebackExtractor()
    tracebacks = extractor.extract_tracebacks(sample_log)

    for tb in tracebacks:
        print(f"Exception: {tb['exception_type']}: {tb['exception_message']}")
        print(f"Location:  {tb['last_file']}:{tb['last_line']}")
        print(f"Hash:      {tb['hash']}")
        print("---")
```

---

### 6. SRE 实战：日志分析工具

```python
#!/usr/bin/env python3
"""
SRE 日志分析工具

功能：
1. 解析多种日志格式
2. 统计错误分布
3. 发现异常模式
4. 生成分析报告
"""
import re
import json
import argparse
from typing import Dict, List, Any, Counter as CounterType
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class LogAnalysisReport:
    """日志分析报告"""
    file_path: str
    total_lines: int = 0
    parsed_lines: int = 0
    parse_errors: int = 0
    time_range: Dict[str, str] = field(default_factory=dict)
    level_distribution: Dict[str, int] = field(default_factory=dict)
    top_errors: List[Dict[str, Any]] = field(default_factory=list)
    error_rate_over_time: Dict[str, float] = field(default_factory=dict)
    slow_requests: List[Dict[str, Any]] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)


class LogAnalyzer:
    """
    日志分析器

    SRE 用途：
    - 故障排查：快速定位错误原因
    - 性能分析：发现慢请求
    - 趋势分析：错误率变化趋势
    - 容量规划：请求量分布
    """

    def __init__(self, parser: MultiFormatLogParser) -> None:
        self._parser = parser
        self._entries: List[ParsedLog] = []

    def load_file(self, path: Path, max_lines: int = 0) -> int:
        """
        加载日志文件

        Args:
            path: 日志文件路径
            max_lines: 最大加载行数（0 表示全部）

        Returns:
            成功解析的行数
        """
        count = 0
        for entry in self._parser.parse_file(path):
            self._entries.append(entry)
            count += 1
            if max_lines > 0 and count >= max_lines:
                break
        return count

    def analyze(self) -> LogAnalysisReport:
        """生成分析报告"""
        report = LogAnalysisReport(
            file_path="",
            total_lines=len(self._entries),
            parsed_lines=sum(1 for e in self._entries if e.timestamp),
        )

        if not self._entries:
            return report

        # 时间范围
        timestamps = [e.timestamp for e in self._entries if e.timestamp]
        if timestamps:
            report.time_range = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat(),
            }

        # 级别分布
        level_counter: CounterType[str] = Counter()
        for entry in self._entries:
            level_counter[entry.level] += 1
        report.level_distribution = dict(level_counter)

        # Top 错误
        error_messages: CounterType[str] = Counter()
        for entry in self._entries:
            if entry.level in ("ERROR", "CRITICAL"):
                # 截取消息前 100 字符作为 key
                key = entry.message[:100]
                error_messages[key] += 1
        report.top_errors = [
            {"message": msg, "count": count}
            for msg, count in error_messages.most_common(10)
        ]

        # 错误率趋势（按小时）
        hourly_total: Dict[str, int] = defaultdict(int)
        hourly_errors: Dict[str, int] = defaultdict(int)
        for entry in self._entries:
            if entry.timestamp:
                hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
                hourly_total[hour_key] += 1
                if entry.level in ("ERROR", "CRITICAL"):
                    hourly_errors[hour_key] += 1

        for hour in sorted(hourly_total.keys()):
            total = hourly_total[hour]
            errors = hourly_errors.get(hour, 0)
            report.error_rate_over_time[hour] = round(errors / total * 100, 2) if total > 0 else 0

        # 异常检测
        report.anomalies = self._detect_anomalies()

        return report

    def _detect_anomalies(self) -> List[str]:
        """检测异常模式"""
        anomalies = []

        # 检测错误突发
        timestamps = [e.timestamp for e in self._entries
                     if e.timestamp and e.level in ("ERROR", "CRITICAL")]
        if len(timestamps) >= 10:
            # 检查是否有短时间内大量错误
            for i in range(len(timestamps) - 9):
                window_start = timestamps[i]
                window_end = timestamps[i + 9]
                if (window_end - window_start).total_seconds() < 60:
                    anomalies.append(
                        f"Error burst: 10 errors in "
                        f"{(window_end - window_start).total_seconds():.0f}s "
                        f"starting at {window_start.isoformat()}"
                    )
                    break

        # 检测错误率突增
        error_rates = list(self._detect_rate_spikes())
        if error_rates:
            anomalies.extend(error_rates)

        return anomalies

    def _detect_rate_spikes(self):
        """检测错误率突增"""
        hourly_total: Dict[str, int] = defaultdict(int)
        hourly_errors: Dict[str, int] = defaultdict(int)

        for entry in self._entries:
            if entry.timestamp:
                hour_key = entry.timestamp.strftime("%Y-%m-%d %H:00")
                hourly_total[hour_key] += 1
                if entry.level in ("ERROR", "CRITICAL"):
                    hourly_errors[hour_key] += 1

        rates = []
        for hour in sorted(hourly_total.keys()):
            total = hourly_total[hour]
            errors = hourly_errors.get(hour, 0)
            rate = errors / total * 100 if total > 0 else 0
            rates.append((hour, rate))

        # 检测突增（当前小时比前一个小时高 3 倍以上）
        for i in range(1, len(rates)):
            if rates[i - 1][1] > 0 and rates[i][1] > rates[i - 1][1] * 3:
                yield (
                    f"Error rate spike: {rates[i][0]} "
                    f"({rates[i][1]:.1f}% vs {rates[i-1][1]:.1f}%)"
                )


def main() -> None:
    """命令行入口"""
    arg_parser = argparse.ArgumentParser(description="SRE Log Analyzer")
    arg_parser.add_argument("file", help="Log file path")
    arg_parser.add_argument(
        "--format",
        choices=["auto", "python", "nginx", "syslog", "json", "k8s"],
        default="auto",
        help="Log format",
    )
    arg_parser.add_argument("--max-lines", type=int, default=0, help="Max lines to parse")
    arg_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = arg_parser.parse_args()

    log_parser = MultiFormatLogParser()
    analyzer = LogAnalyzer(log_parser)

    print(f"Loading {args.file}...")
    loaded = analyzer.load_file(Path(args.file), args.max_lines)
    print(f"Loaded {loaded} entries")

    print("Analyzing...")
    report = analyzer.analyze()

    if args.json:
        print(json.dumps(report.__dict__, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"\n{'='*60}")
        print(f"Log Analysis Report")
        print(f"{'='*60}")
        print(f"Total entries: {report.total_lines}")
        print(f"Parsed entries: {report.parsed_lines}")
        if report.time_range:
            print(f"Time range: {report.time_range['start']} - {report.time_range['end']}")

        print(f"\nLevel Distribution:")
        for level, count in sorted(report.level_distribution.items()):
            pct = count / report.total_lines * 100 if report.total_lines > 0 else 0
            print(f"  {level:10s}: {count:6d} ({pct:.1f}%)")

        if report.top_errors:
            print(f"\nTop Errors:")
            for err in report.top_errors[:5]:
                print(f"  [{err['count']:4d}] {err['message']}")

        if report.anomalies:
            print(f"\nAnomalies Detected:")
            for anomaly in report.anomalies:
                print(f"  - {anomaly}")


if __name__ == "__main__":
    main()
```

---

## 💻 实战练习

### 练习 1：基础操作 — Nginx 日志解析

**目标**：解析 Nginx 访问日志并生成统计报告

```python
#!/usr/bin/env python3
"""
Nginx 日志分析练习

要求：
1. 解析 Nginx Combined 格式日志
2. 统计状态码分布
3. 统计 Top 10 IP 和 URL
4. 计算平均响应大小
5. 发现异常请求（4xx/5xx）
"""
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any


NGINX_PATTERN = re.compile(
    r'(?P<ip>\S+)\s+'
    r'\S+\s+\S+\s+'
    r'\[(?P<time>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<path>\S+)\s+\S+"\s+'
    r'(?P<status>\d{3})\s+'
    r'(?P<bytes>\d+)\s+'
    r'"[^"]*"\s+'
    r'"(?P<ua>[^"]*)"'
)


def analyze_nginx_log(path: Path) -> Dict[str, Any]:
    """分析 Nginx 日志"""
    status_counter: Counter = Counter()
    ip_counter: Counter = Counter()
    path_counter: Counter = Counter()
    method_counter: Counter = Counter()
    total_bytes = 0
    total_requests = 0
    errors: List[Dict[str, str]] = []

    with open(path, "r") as f:
        for line_num, line in enumerate(f, 1):
            m = NGINX_PATTERN.match(line)
            if not m:
                continue

            total_requests += 1
            g = m.groupdict()

            status = g["status"]
            status_counter[status] += 1
            ip_counter[g["ip"]] += 1
            path_counter[g["path"]] += 1
            method_counter[g["method"]] += 1
            total_bytes += int(g["bytes"])

            if status.startswith(("4", "5")):
                errors.append({
                    "line": line_num,
                    "ip": g["ip"],
                    "method": g["method"],
                    "path": g["path"],
                    "status": status,
                })

    return {
        "total_requests": total_requests,
        "total_bytes": total_bytes,
        "avg_bytes": total_bytes / total_requests if total_requests else 0,
        "status_distribution": dict(status_counter.most_common()),
        "top_ips": dict(ip_counter.most_common(10)),
        "top_paths": dict(path_counter.most_common(10)),
        "method_distribution": dict(method_counter.most_common()),
        "error_count": len(errors),
        "recent_errors": errors[-10:],
    }


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2:
        print("Usage: python nginx_analyzer.py <access.log>")
        sys.exit(1)

    report = analyze_nginx_log(Path(sys.argv[1]))
    print(json.dumps(report, indent=2))
```

### 练习 2：进阶场景 — 错误聚合与根因分析

**目标**：从大量日志中聚合相同类型的错误，找到根因

```python
"""
练习：错误聚合与根因分析

要求：
1. 提取所有 ERROR/CRITICAL 日志
2. 按错误类型聚合（相同 traceback 哈希）
3. 统计每种错误的出现次数和首次/末次出现时间
4. 识别错误突发时段
5. 生成可读的分析报告
"""
import re
import hashlib
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class ErrorGroup:
    """错误分组"""
    exception_type: str
    exception_message: str
    traceback_hash: str
    count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    occurrences: List[datetime] = field(default_factory=list)
    sample_traceback: str = ""


class ErrorAggregator:
    """错误聚合器"""

    def __init__(self) -> None:
        self._groups: Dict[str, ErrorGroup] = {}

    def add_error(
        self,
        timestamp: datetime,
        exception_type: str,
        exception_message: str,
        traceback: str,
    ) -> None:
        """添加一个错误"""
        # 计算 traceback 哈希（用于聚合）
        tb_hash = self._hash_traceback(traceback)

        if tb_hash not in self._groups:
            self._groups[tb_hash] = ErrorGroup(
                exception_type=exception_type,
                exception_message=exception_message,
                traceback_hash=tb_hash,
                first_seen=timestamp,
                sample_traceback=traceback,
            )

        group = self._groups[tb_hash]
        group.count += 1
        group.last_seen = timestamp
        group.occurrences.append(timestamp)

    def _hash_traceback(self, traceback: str) -> str:
        """计算 traceback 的结构哈希"""
        # 提取文件名和行号
        structure = re.findall(r'File "([^"]+)", line (\d+)', traceback)
        hash_input = "|".join(f"{f}:{l}" for f, l in structure)
        if not hash_input:
            hash_input = traceback[:200]
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def get_report(self) -> List[Dict[str, Any]]:
        """生成聚合报告"""
        report = []
        for group in sorted(
            self._groups.values(),
            key=lambda g: g.count,
            reverse=True,
        ):
            report.append({
                "exception_type": group.exception_type,
                "exception_message": group.exception_message,
                "count": group.count,
                "first_seen": group.first_seen.isoformat(),
                "last_seen": group.last_seen.isoformat(),
                "traceback_hash": group.traceback_hash,
                "sample": group.sample_traceback[:500],
            })
        return report
```

### 练习 3：故障排查挑战 — 修复正则表达式

**场景**：以下正则表达式有性能或正确性问题，请找出并修复。

```python
# broken_regex.py — 故障排查练习
import re

# 问题 1: 灾难性回溯
pattern1 = re.compile(r'(a+)+b')
# 测试: pattern1.search("a" * 30)  # 会非常慢!

# 问题 2: 贪婪匹配导致错误结果
pattern2 = re.compile(r'<div>.*</div>')
text2 = "<div>first</div> <div>second</div>"
result2 = pattern2.findall(text2)
# 期望: ['<div>first</div>', '<div>second</div>']
# 实际: ['<div>first</div> <div>second</div>']

# 问题 3: 未转义特殊字符
pattern3 = re.compile(r'C:\Users\admin')
# 匹配失败，因为 \U 和 \a 是特殊序列

# 问题 4: 忘记编译
for line in open("/var/log/syslog"):
    if re.search(r'error|warning|critical', line, re.IGNORECASE):
        pass  # 每次循环都重新编译!

# 问题 5: 分组捕获错误
pattern5 = re.compile(r'(\d+)-(\d+)')
text5 = "port-range: 8000-9000"
m = pattern5.search(text5)
if m:
    start = m.group(1)  # 正确
    end = m.group(3)    # 错误! 只有 2 个分组
```

**预期发现的问题**：
1. `(a+)+b` 灾难性回溯 — 应改为 `(?:a)+b` 或 `a+b`
2. `.*` 贪婪匹配 — 应改为 `.*?` 非贪婪
3. 反斜杠未转义 — 应使用 `r'C:\\Users\\admin'` 或 `re.escape()`
4. 循环中重复编译 — 应在循环外 `compiled = re.compile()`
5. `group(3)` 索引错误 — 只有 2 个分组，应为 `group(2)`

---

## 🎯 面试题精选

### 问题 1：正则表达式中 `.*` 和 `.*?` 有什么区别？

**参考答案**：

- `.*` 是贪婪匹配：尽可能多地匹配字符
- `.*?` 是非贪婪匹配：尽可能少地匹配字符

```python
text = "<b>bold</b> <i>italic</i>"

re.findall(r'<.*>', text)    # ['<b>bold</b> <i>italic</i>']
re.findall(r'<.*?>', text)   # ['<b>', '</b>', '<i>', '</i>']
```

SRE 场景：解析日志时通常使用非贪婪匹配，避免匹配到跨越多行的内容。

### 问题 2：为什么要在模块级别编译正则表达式？

**参考答案**：

每次调用 `re.search()` 等函数时，Python 都会：
1. 解析正则表达式字符串
2. 编译为内部状态机
3. 执行匹配

使用 `re.compile()` 可以将步骤 1 和 2 只执行一次，后续调用只执行步骤 3。

性能提升取决于使用频率：
- 低频使用（几次）：几乎无差别
- 中频使用（几百次）：提升 10-30%
- 高频使用（几万次）：提升 30-50%

### 问题 3：什么是灾难性回溯（Catastrophic Backtracking）？如何避免？

**参考答案**：

灾难性回溯发生在正则表达式有嵌套量词时：

```python
# 危险模式
re.search(r'(a+)+b', 'a' * 30)  # 可能需要几小时

# 原因：(a+)+ 中，内层 a+ 和外层 + 的组合导致指数级回溯
# 'aaa' 可以被拆分为: (a)(a)(a), (aa)(a), (a)(aa), (aaa) 等
```

避免方法：
1. 避免嵌套量词：`(a+)+` → `a+`
2. 使用原子组（Python 不原生支持，但可以用 `re` 的 `(?=...)` 技巧）
3. 使用更具体的模式：`.` → `[^>]`
4. 设置匹配超时（第三方库 `regex` 支持）

### 问题 4：如何用正则表达式解析多种日志格式？

**参考答案**：

```python
class MultiFormatParser:
    def __init__(self):
        self.formats = {
            "json": re.compile(r'^\s*\{'),
            "nginx": re.compile(r'^\d+\.\d+\.\d+\.\d+\s'),
            "python": re.compile(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'),
        }
        self.parsers = {
            "json": self._parse_json,
            "nginx": self._parse_nginx,
            "python": self._parse_python,
        }

    def parse(self, line):
        for fmt, pattern in self.formats.items():
            if pattern.match(line):
                return self.parsers[fmt](line)
        return self._parse_unknown(line)
```

### 问题 5：正则表达式中的前向断言和后向断言是什么？

**参考答案**：

断言（Assertion）匹配一个位置而非字符：

| 断言类型 | 语法 | 含义 |
|---------|------|------|
| 前向肯定 | `(?=...)` | 后面跟着... |
| 前向否定 | `(?!...)` | 后面不跟着... |
| 后向肯定 | `(?<=...)` | 前面有... |
| 后向否定 | `(?<!...)` | 前面没有... |

SRE 应用：
```python
# 提取单位前面的数字
re.findall(r'\d+(?=GB)', '16GB RAM, 512GB SSD')  # ['16', '512']

# 提取冒号后面的值
re.findall(r'(?<=:\s)\S+', 'host: web-01, port: 8080')  # ['web-01', '8080']
```

### 问题 6：如何处理多行日志（如 Python traceback）？

**参考答案**：

多行日志的核心问题是确定日志条目的边界：

```python
class MultilineProcessor:
    # 识别日志行起始的模式
    START_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}')

    def process(self, lines):
        current = []
        for line in lines:
            if self.START_PATTERN.match(line):
                if current:
                    yield "\n".join(current)
                current = [line]
            else:
                if current:
                    current.append(line)
        if current:
            yield "\n".join(current)
```

关键点：
1. 定义日志行起始模式
2. 非起始行归入前一条日志
3. 设置最大行数限制（防止无限合并）

### 问题 7：如何用正则表达式做日志脱敏？

**参考答案**：

```python
import re

def mask_sensitive_data(log_line: str) -> str:
    """日志脱敏"""
    # IP 地址（保留网段）
    log_line = re.sub(
        r'(\d{1,3}\.\d{1,3}\.)\d{1,3}\.\d{1,3}',
        r'\1***.***',
        log_line,
    )

    # 邮箱
    log_line = re.sub(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        '***@***.***',
        log_line,
    )

    # 密码/密钥
    log_line = re.sub(
        r'(password|secret|key|token)\s*[=:]\s*\S+',
        r'\1=***',
        log_line,
        flags=re.IGNORECASE,
    )

    # 手机号
    log_line = re.sub(
        r'1[3-9]\d{9}',
        '1**********',
        log_line,
    )

    return log_line
```

### 问题 8：re.DOTALL、re.MULTILINE、re.IGNORECASE 各自的作用是什么？

**参考答案**：

| 标志 | 缩写 | 作用 |
|------|------|------|
| `re.IGNORECASE` | `re.I` | 不区分大小写 |
| `re.MULTILINE` | `re.M` | `^` 和 `$` 匹配每行的开头和结尾 |
| `re.DOTALL` | `re.S` | `.` 匹配包括 `\n` 在内的所有字符 |
| `re.VERBOSE` | `re.X` | 允许使用注释和空白 |

```python
# DOTALL: . 匹配换行符
re.findall(r'<div>.*?</div>', text, re.DOTALL)

# MULTILINE: ^ 匹配每行开头
re.findall(r'^ERROR.*$', text, re.MULTILINE)

# VERBOSE: 允许注释
re.compile(r"""
    \d{4}-\d{2}-\d{2}  # 日期
    \s+                  # 空白
    \d{2}:\d{2}:\d{2}   # 时间
""", re.VERBOSE)
```

---

## 📚 深入阅读

### 官方文档
- [re — Regular expression operations](https://docs.python.org/3/library/re.html)
- [Regular Expression HOWTO](https://docs.python.org/3/howto/regex.html)

### 在线工具
- [regex101](https://regex101.com/) — 正则表达式在线测试和调试
- [regexr](https://regexr.com/) — 正则表达式学习和测试
- [Debuggex](https://www.debuggex.com/) — 正则表达式可视化

### 推荐书籍
- 《Mastering Regular Expressions》Jeffrey Friedl — 正则表达式权威指南
- 《Python Cookbook》David Beazley — 第 2 章：字符串和文本
- 《Effective Python》Brett Slatkin — 第 5 章：字符串

### 技术博客
- [Real Python — Regular Expressions](https://realpython.com/regex-python/)
- [Regular-Expressions.info](https://www.regular-expressions.info/) — 正则表达式教程
- [Google RE2](https://github.com/google/re2) — 线性时间正则引擎

---

## ✅ 自检清单

### 理论检查
- [ ] 理解正则表达式引擎的回溯机制
- [ ] 知道贪婪匹配和非贪婪匹配的区别
- [ ] 理解编译优化的原理和收益
- [ ] 知道前向断言和后向断言的用法
- [ ] 理解灾难性回溯的成因和避免方法

### 实操检查
- [ ] 能用 re 模块的 search/match/findall/sub/split 方法
- [ ] 能编写和使用命名分组正则表达式
- [ ] 能解析 Nginx/Apache/syslog 等常见日志格式
- [ ] 能处理多行日志（如 Python traceback）
- [ ] 能用正则表达式做日志脱敏

### 能力验证
- [ ] 能编写通用的多格式日志解析器
- [ ] 能实现错误聚合和根因分析
- [ ] 能编写日志分析工具生成统计报告
