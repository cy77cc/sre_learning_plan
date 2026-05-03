# Day 56: Python SRE 综合评估

> 📅 日期：2026-05-02
> 📖 学习主题：综合项目、代码审查、性能优化、测试覆盖
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 48-55 全部 Python 课程

## 🎯 学习目标

完成 Day 56 的学习后，你应该能够：
- 独立完成一个完整的 SRE 工具项目（从需求到部署）
- 运用代码审查标准发现和修复常见问题
- 掌握 Python 性能优化的核心技术
- 编写高质量的测试用例，达到 80% 以上的覆盖率
- 综合运用前 5 天学到的所有知识

---

## 📖 核心知识点

### 1. 综合项目：SRE 工具箱

```
SRE 工具箱架构：

┌─────────────────────────────────────────────────────────────────┐
│                      SRE Toolbox                                 │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  监控模块  │  │  告警模块  │  │  执行模块  │  │  报告模块  │       │
│  │ Monitor  │  │ Alerter  │  │ Executor │  │ Reporter │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │             │
│       └──────────────┼──────────────┼──────────────┘             │
│                      │              │                             │
│                      ▼              ▼                             │
│              ┌──────────────┐ ┌──────────────┐                  │
│              │  存储层       │ │  配置层       │                  │
│              │ SQLite/Redis │ │  YAML/ENV    │                  │
│              └──────────────┘ └──────────────┘                  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    CLI 接口层                              │   │
│  │  python toolbox.py monitor --config config.yaml          │   │
│  │  python toolbox.py exec -f hosts.yaml -c "uptime"        │   │
│  │  python toolbox.py alert --list                          │   │
│  │  python toolbox.py report --format html                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.1 项目结构

```
sre-toolbox/
├── pyproject.toml          # 项目配置和依赖
├── README.md
├── config/
│   ├── default.yaml        # 默认配置
│   └── production.yaml     # 生产环境配置
├── src/
│   └── sre_toolbox/
│       ├── __init__.py
│       ├── cli.py          # CLI 入口
│       ├── config.py       # 配置管理
│       ├── monitor/
│       │   ├── __init__.py
│       │   ├── collector.py    # 指标采集
│       │   ├── store.py        # 指标存储
│       │   └── delta.py        # 差分计算
│       ├── alert/
│       │   ├── __init__.py
│       │   ├── engine.py       # 告警引擎
│       │   ├── rules.py        # 规则定义
│       │   └── notifiers.py    # 通知渠道
│       ├── executor/
│       │   ├── __init__.py
│       │   ├── ssh.py          # SSH 执行器
│       │   ├── pool.py         # 连接池
│       │   ├── inventory.py    # 主机清单
│       │   └── playbook.py     # Playbook 引擎
│       ├── report/
│       │   ├── __init__.py
│       │   └── generator.py    # 报告生成
│       └── utils/
│           ├── __init__.py
│           ├── decorators.py   # 通用装饰器
│           └── logging.py      # 日志配置
├── tests/
│   ├── conftest.py
│   ├── test_monitor/
│   ├── test_alert/
│   ├── test_executor/
│   └── test_utils/
└── systemd/
    └── sre-toolbox.service
```

#### 1.2 核心实现

```python
#!/usr/bin/env python3
"""SRE 工具箱 — 主入口。

整合监控、告警、批量执行、报告等功能的统一 CLI 工具。
"""

import argparse
import sys
import logging
import os
from pathlib import Path


def setup_logging(level="INFO", log_file=None):
    """配置日志。"""
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers
    )


# ──────────────────────────────────────────────
# 配置管理
# ──────────────────────────────────────────────
import yaml
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """应用配置。"""
    monitor: Dict[str, Any] = field(default_factory=dict)
    database: Dict[str, Any] = field(default_factory=dict)
    web: Dict[str, Any] = field(default_factory=dict)
    alert_rules: list = field(default_factory=list)
    inventory: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: str) -> 'AppConfig':
        """加载配置文件。"""
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return cls(
            monitor=data.get("monitor", {}),
            database=data.get("database", {}),
            web=data.get("web", {}),
            alert_rules=data.get("alert_rules", []),
            inventory=data.get("inventory", {}),
        )


# ──────────────────────────────────────────────
# CLI 命令实现
# ──────────────────────────────────────────────

def cmd_monitor(args, config: AppConfig):
    """启动监控。"""
    from sre_toolbox.monitor.collector import collect_all
    from sre_toolbox.monitor.store import MetricsStore, MemoryCache
    from sre_toolbox.alert.engine import AlertEngine, AlertRule, Severity

    db_path = config.database.get("path", "metrics.db")
    store = MetricsStore(db_path)
    cache = MemoryCache()

    # 初始化告警引擎
    engine = AlertEngine()
    for rule_cfg in config.alert_rules:
        severity_map = {"info": Severity.INFO, "warning": Severity.WARNING,
                        "critical": Severity.CRITICAL}
        engine.add_rule(AlertRule(
            name=rule_cfg["name"],
            metric=rule_cfg["metric"],
            operator=rule_cfg["operator"],
            threshold=rule_cfg["threshold"],
            severity=severity_map.get(rule_cfg.get("severity", "warning"),
                                       Severity.WARNING),
            duration=rule_cfg.get("duration", 0),
            message=rule_cfg.get("message", ""),
        ))

    interval = config.monitor.get("collect_interval", 10)
    print(f"监控启动 (间隔 {interval}s, 数据库 {db_path})")

    import time
    import signal

    running = True
    def stop(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while running:
        metrics = collect_all()
        cache.put_batch(metrics)
        store.save_batch(metrics)

        alerts = engine.evaluate(metrics)
        for alert in alerts:
            print(f"ALERT [{alert.severity.value}]: {alert.message}")

        cpu = metrics.get("cpu_percent", 0)
        mem = metrics.get("mem_percent", 0)
        disk = metrics.get("disk_root_percent", 0)
        print(f"CPU: {cpu}%  MEM: {mem}%  DISK: {disk}%")

        time.sleep(interval)

    print("监控已停止")


def cmd_exec(args, config: AppConfig):
    """执行远程命令。"""
    from sre_toolbox.executor.inventory import Inventory
    from sre_toolbox.executor.pool import SSHConnectionPool
    from sre_toolbox.executor.ssh import RemoteExecutor, TaskExecutor, ExecutionConfig

    inventory = Inventory.from_yaml(args.inventory)
    hosts = inventory.get_hosts(args.group) if args.group else inventory.get_hosts()

    if not hosts:
        print("没有匹配的主机")
        sys.exit(1)

    print(f"在 {len(hosts)} 台主机上执行: {args.command}")

    pool = SSHConnectionPool()
    executor = RemoteExecutor(pool)
    config_exec = ExecutionConfig(
        max_workers=args.workers,
        timeout=args.timeout,
        serial=not args.parallel,
    )

    task_executor = TaskExecutor(executor, config_exec)
    report = task_executor.run(hosts, args.command)

    for result in report.results:
        print(f"{result}")
        if result.stdout and args.verbose:
            print(f"  {result.stdout.strip()}")

    print(f"\n{report.summary()}")
    pool.close_all()

    if report.failed > 0:
        sys.exit(1)


def cmd_alert(args, config: AppConfig):
    """告警管理。"""
    from sre_toolbox.monitor.store import MetricsStore
    from sre_toolbox.alert.engine import AlertEngine, AlertRule, Severity

    db_path = config.database.get("path", "metrics.db")
    store = MetricsStore(db_path)

    if args.list:
        # 列出当前告警
        alerts = store.get_active_alerts()
        if not alerts:
            print("当前没有活跃告警")
        else:
            for alert in alerts:
                print(f"[{alert['severity']}] {alert['rule_name']}: "
                      f"{alert['message']} (值: {alert['value']})")
    elif args.add_rule:
        print(f"添加规则: {args.add_rule}")
        # 实际实现：解析并添加规则
    else:
        print("使用 --list 查看告警，--add-rule 添加规则")


def cmd_report(args, config: AppConfig):
    """生成报告。"""
    from sre_toolbox.monitor.store import MetricsStore
    from sre_toolbox.report.generator import ReportGenerator
    import time

    db_path = config.database.get("path", "metrics.db")
    store = MetricsStore(db_path)

    # 获取所有指标的最新值
    metrics = store.get_all_latest()

    report_data = {
        "timestamp": time.time(),
        "metrics": metrics,
        "metric_count": len(metrics),
    }

    gen = ReportGenerator()
    if args.format == "json":
        import json
        print(json.dumps(report_data, indent=2, default=str))
    elif args.format == "html":
        output = args.output or "report.html"
        with open(output, "w") as f:
            f.write(gen.html_report(report_data))
        print(f"报告已生成: {output}")
    else:
        print(gen.text_report(report_data))


def main():
    parser = argparse.ArgumentParser(
        description="SRE 工具箱 — 一站式运维工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s monitor -c config.yaml          启动监控
  %(prog)s exec -f hosts.yaml -c uptime    执行远程命令
  %(prog)s alert --list                    查看告警
  %(prog)s report --format html            生成报告
        """
    )
    parser.add_argument("-c", "--config", default="config.yaml",
                        help="配置文件路径")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--log-file", help="日志文件路径")

    subparsers = parser.add_subparsers(dest="subcommand")

    # monitor
    mon_parser = subparsers.add_parser("monitor", help="启动监控")

    # exec
    exec_parser = subparsers.add_parser("exec", help="执行远程命令")
    exec_parser.add_argument("-f", "--inventory", required=True,
                             help="主机清单文件")
    exec_parser.add_argument("-c", "--command", required=True,
                             help="要执行的命令")
    exec_parser.add_argument("-g", "--group", help="目标主机组")
    exec_parser.add_argument("-w", "--workers", type=int, default=10,
                             help="并发数")
    exec_parser.add_argument("-t", "--timeout", type=int, default=30,
                             help="超时时间")
    exec_parser.add_argument("--parallel", action="store_true",
                             help="并行执行")
    exec_parser.add_argument("-v", "--verbose", action="store_true",
                             help="详细输出")

    # alert
    alert_parser = subparsers.add_parser("alert", help="告警管理")
    alert_parser.add_argument("--list", action="store_true",
                              help="列出活跃告警")
    alert_parser.add_argument("--add-rule", help="添加告警规则")

    # report
    report_parser = subparsers.add_parser("report", help="生成报告")
    report_parser.add_argument("--format", choices=["text", "json", "html"],
                               default="text", help="输出格式")
    report_parser.add_argument("-o", "--output", help="输出文件")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.log_level, args.log_file)

    # 加载配置
    if os.path.exists(args.config):
        config = AppConfig.load(args.config)
    else:
        config = AppConfig()

    commands = {
        "monitor": cmd_monitor,
        "exec": cmd_exec,
        "alert": cmd_alert,
        "report": cmd_report,
    }
    commands[args.subcommand](args, config)


if __name__ == "__main__":
    main()
```

---

### 2. 代码审查标准

#### 2.1 常见问题清单

```python
"""
SRE 工具代码审查检查清单。

审查维度：
1. 正确性 — 逻辑是否正确，边界条件是否处理
2. 安全性 — 是否有注入、泄露、权限问题
3. 可靠性 — 异常处理、重试、超时是否完善
4. 性能   — 是否有性能瓶颈、资源泄漏
5. 可维护性 — 代码是否清晰、可读、可测试
"""

# ──────────────────────────────────────────────
# 1. 正确性问题示例
# ──────────────────────────────────────────────

# 错误：未处理边界条件
def bad_percent(used, total):
    return used / total * 100  # total 为 0 时 ZeroDivisionError

# 正确：处理边界条件
def good_percent(used, total):
    if total <= 0:
        return 0.0
    return round(used / total * 100, 2)


# 错误：浮点数比较
def bad_compare(a, b):
    return a == b  # 0.1 + 0.2 != 0.3

# 正确：使用容差比较
def good_compare(a, b, tolerance=1e-9):
    return abs(a - b) < tolerance


# 错误：未验证输入
def bad_parse_config(data):
    return data["monitor"]["interval"]  # KeyError 如果键不存在

# 正确：安全访问
def good_parse_config(data):
    return data.get("monitor", {}).get("interval", 10)


# ──────────────────────────────────────────────
# 2. 安全性问题示例
# ──────────────────────────────────────────────

# 错误：SQL 注入
def bad_query(conn, metric_name):
    sql = f"SELECT * FROM metrics WHERE name = '{metric_name}'"
    return conn.execute(sql)

# 正确：参数化查询
def good_query(conn, metric_name):
    sql = "SELECT * FROM metrics WHERE name = ?"
    return conn.execute(sql, (metric_name,))


# 错误：命令注入
def bad_exec(host, user_input):
    os.system(f"ping -c 1 {user_input}")  # user_input 可以是 "; rm -rf /"

# 正确：使用参数化调用
def good_exec(host, user_input):
    import subprocess
    subprocess.run(["ping", "-c", "1", user_input], timeout=10)


# 错误：硬编码密钥
BAD_API_KEY = "sk-1234567890abcdef"

# 正确：从环境变量读取
import os
GOOD_API_KEY = os.environ.get("API_KEY")


# 错误：不安全的 pickle 反序列化
import pickle
def bad_load(data):
    return pickle.loads(data)  # 可以执行任意代码

# 正确：使用 JSON
import json
def good_load(data):
    return json.loads(data)


# ──────────────────────────────────────────────
# 3. 可靠性问题示例
# ──────────────────────────────────────────────

# 错误：未设置超时
import requests
def bad_request(url):
    return requests.get(url)  # 可能永远挂起

# 正确：设置超时
def good_request(url, timeout=10):
    return requests.get(url, timeout=timeout)


# 错误：未处理异常
def bad_process(data):
    result = data["key"]["nested"]["value"]
    return result * 2

# 正确：显式异常处理
def good_process(data):
    try:
        result = data["key"]["nested"]["value"]
        return result * 2
    except (KeyError, TypeError) as e:
        logger.error(f"数据处理失败: {e}")
        return None


# 错误：资源未关闭
def bad_read_file(path):
    f = open(path)
    data = f.read()
    return data  # 文件未关闭

# 正确：使用上下文管理器
def good_read_file(path):
    with open(path) as f:
        return f.read()


# ──────────────────────────────────────────────
# 4. 性能问题示例
# ──────────────────────────────────────────────

# 错误：循环中重复创建对象
def bad_process(hosts):
    results = []
    for host in hosts:
        client = SSHClient()  # 每次都新建连接
        client.connect(host)
        results.append(client.exec_command("uptime"))
        client.close()
    return results

# 正确：复用连接
def good_process(hosts, pool):
    results = []
    for host in hosts:
        with pool.get_connection(host) as conn:
            results.append(conn.exec_command("uptime"))
    return results


# 错误：不必要的列表转换
def bad_sum(filepath):
    total = 0
    lines = list(open(filepath))  # 全部读入内存
    for line in lines:
        total += float(line.strip())
    return total

# 正确：惰性迭代
def good_sum(filepath):
    total = 0
    with open(filepath) as f:
        for line in f:  # 逐行读取
            total += float(line.strip())
    return total


# ──────────────────────────────────────────────
# 5. 可维护性问题示例
# ──────────────────────────────────────────────

# 错误：魔法数字
def bad_check(value):
    if value > 90:  # 90 是什么？
        return "critical"
    elif value > 70:  # 70 是什么？
        return "warning"
    return "ok"

# 正确：使用常量
CPU_CRITICAL_THRESHOLD = 90
CPU_WARNING_THRESHOLD = 70

def good_check(value):
    if value > CPU_CRITICAL_THRESHOLD:
        return "critical"
    elif value > CPU_WARNING_THRESHOLD:
        return "warning"
    return "ok"


# 错误：过长的函数（超过 50 行）
def bad_do_everything(config, hosts, command):
    # ... 100 行代码 ...
    pass

# 正确：拆分为小函数
def good_do_everything(config, hosts, command):
    inventory = parse_inventory(hosts)
    connection = create_connection(config)
    results = execute_on_hosts(connection, inventory, command)
    report = generate_report(results)
    return report
```

#### 2.2 自动化代码审查脚本

```python
#!/usr/bin/env python3
"""SRE 工具代码审查脚本。

自动检查 Python 代码的常见问题。
"""

import ast
import os
import sys
import re
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum, auto


class Severity(Enum):
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()


@dataclass
class Issue:
    file: str
    line: int
    severity: Severity
    category: str
    message: str

    def __str__(self):
        return f"{self.file}:{self.line} [{self.severity.name}] {self.category}: {self.message}"


class CodeReviewer:
    """代码审查器。"""

    def __init__(self):
        self.issues: List[Issue] = []

    def review_file(self, filepath: str):
        """审查单个文件。"""
        with open(filepath) as f:
            content = f.read()
            lines = content.splitlines()

        # 文本检查
        self._check_text(filepath, lines)

        # AST 检查
        try:
            tree = ast.parse(content)
            self._check_ast(filepath, tree)
        except SyntaxError as e:
            self.issues.append(Issue(
                filepath, e.lineno or 0, Severity.CRITICAL,
                "syntax", f"语法错误: {e.msg}"
            ))

    def _check_text(self, filepath: str, lines: List[str]):
        """基于文本的检查。"""
        for i, line in enumerate(lines, 1):
            # 硬编码密钥
            if re.search(r'(api_key|password|secret|token)\s*=\s*["\'][^"\']+["\']',
                         line, re.IGNORECASE):
                if 'os.environ' not in line and 'getenv' not in line:
                    self.issues.append(Issue(
                        filepath, i, Severity.CRITICAL,
                        "security", "疑似硬编码密钥或密码"
                    ))

            # SQL 注入
            if re.search(r'f["\'].*SELECT.*{.*}.*["\']', line):
                self.issues.append(Issue(
                    filepath, i, Severity.CRITICAL,
                    "security", "疑似 SQL 注入（使用 f-string 构建 SQL）"
                ))

            # 命令注入
            if re.search(r'os\.system\(f["\']', line):
                self.issues.append(Issue(
                    filepath, i, Severity.HIGH,
                    "security", "使用 os.system 执行命令，存在注入风险"
                ))

            # 不安全的 pickle
            if 'pickle.loads' in line or 'pickle.load' in line:
                self.issues.append(Issue(
                    filepath, i, Severity.HIGH,
                    "security", "使用 pickle 反序列化，存在任意代码执行风险"
                ))

            # 未设置超时
            if re.search(r'requests\.(get|post|put|delete)\([^)]*\)', line):
                if 'timeout' not in line:
                    self.issues.append(Issue(
                        filepath, i, Severity.MEDIUM,
                        "reliability", "HTTP 请求未设置超时"
                    ))

            # print 语句（应使用 logging）
            if re.match(r'^\s*print\(', line):
                self.issues.append(Issue(
                    filepath, i, Severity.LOW,
                    "style", "使用 print 而非 logging"
                ))

    def _check_ast(self, filepath: str, tree: ast.AST):
        """基于 AST 的检查。"""
        for node in ast.walk(tree):
            # 函数过长
            if isinstance(node, ast.FunctionDef):
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    length = node.end_lineno - node.lineno
                    if length > 50:
                        self.issues.append(Issue(
                            filepath, node.lineno, Severity.MEDIUM,
                            "style", f"函数 {node.name} 过长 ({length} 行，建议 < 50)"
                        ))

                # 缺少文档字符串
                if not (node.body and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)):
                    if not node.name.startswith('_'):
                        self.issues.append(Issue(
                            filepath, node.lineno, Severity.LOW,
                            "style", f"函数 {node.name} 缺少文档字符串"
                        ))

            # 文件过长
            if isinstance(node, ast.Module):
                if hasattr(node, 'end_lineno') and node.end_lineno > 800:
                    self.issues.append(Issue(
                        filepath, 1, Severity.MEDIUM,
                        "style", f"文件过长 ({node.end_lineno} 行，建议 < 800)"
                    ))

    def report(self) -> str:
        """生成审查报告。"""
        if not self.issues:
            return "代码审查通过，未发现问题。"

        lines = ["代码审查报告", "=" * 40, ""]

        by_severity = {}
        for issue in self.issues:
            by_severity.setdefault(issue.severity, []).append(issue)

        for severity in [Severity.CRITICAL, Severity.HIGH,
                         Severity.MEDIUM, Severity.LOW]:
            issues = by_severity.get(severity, [])
            if issues:
                lines.append(f"\n{severity.name} ({len(issues)} 个问题):")
                lines.append("-" * 30)
                for issue in issues:
                    lines.append(f"  {issue}")

        # 统计
        lines.append(f"\n总计: {len(self.issues)} 个问题")
        critical = len(by_severity.get(Severity.CRITICAL, []))
        high = len(by_severity.get(Severity.HIGH, []))
        if critical or high:
            lines.append("存在 CRITICAL 或 HIGH 级别问题，建议修复后再提交。")

        return "\n".join(lines)


def main():
    """命令行入口。"""
    if len(sys.argv) < 2:
        print("用法: python review.py <file_or_directory>")
        sys.exit(1)

    reviewer = CodeReviewer()
    target = sys.argv[1]

    if os.path.isfile(target):
        reviewer.review_file(target)
    elif os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', '.venv')]
            for f in files:
                if f.endswith('.py'):
                    reviewer.review_file(os.path.join(root, f))

    print(reviewer.report())

    # 如果有严重问题，返回非零退出码
    critical = sum(1 for i in reviewer.issues
                   if i.severity in (Severity.CRITICAL, Severity.HIGH))
    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
```

---

### 3. 性能优化

#### 3.1 性能分析工具

```python
#!/usr/bin/env python3
"""Python 性能分析工具集。

包含：
1. cProfile — 函数级性能分析
2. line_profiler — 行级性能分析
3. memory_profiler — 内存分析
4. 自定义计时装饰器
"""

import time
import functools
import cProfile
import pstats
import io
from typing import Callable
from contextlib import contextmanager


# ──────────────────────────────────────────────
# 1. 计时装饰器
# ──────────────────────────────────────────────
def benchmark(func: Callable = None, *, iterations: int = 1):
    """性能基准测试装饰器。

    使用方式：
        @benchmark(iterations=1000)
        def fast_function():
            pass

        @benchmark
        def slow_function():
            pass
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            times = []
            result = None
            for _ in range(iterations):
                start = time.perf_counter_ns()
                result = f(*args, **kwargs)
                elapsed = time.perf_counter_ns() - start
                times.append(elapsed)

            avg_ns = sum(times) / len(times)
            min_ns = min(times)
            max_ns = max(times)

            print(f"\n{'=' * 50}")
            print(f"Benchmark: {f.__name__}")
            print(f"  Iterations: {iterations}")
            print(f"  Average:   {avg_ns / 1e6:.3f} ms")
            print(f"  Min:       {min_ns / 1e6:.3f} ms")
            print(f"  Max:       {max_ns / 1e6:.3f} ms")
            print(f"  Total:     {sum(times) / 1e6:.3f} ms")
            print(f"{'=' * 50}")

            return result
        return wrapper

    if func is None:
        return decorator
    return decorator(func)


# ──────────────────────────────────────────────
# 2. 上下文管理器计时
# ──────────────────────────────────────────────
@contextmanager
def timer(label: str = "Operation"):
    """计时上下文管理器。"""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed:.3f}s")


# ──────────────────────────────────────────────
# 3. cProfile 分析
# ──────────────────────────────────────────────
def profile_function(func: Callable, *args, top_n: int = 20, **kwargs):
    """使用 cProfile 分析函数。"""
    profiler = cProfile.Profile()
    profiler.enable()

    result = func(*args, **kwargs)

    profiler.disable()

    # 输出统计
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(top_n)

    print(f"\ncProfile 结果 ({func.__name__}):")
    print(stream.getvalue())

    return result


# ──────────────────────────────────────────────
# 4. 常见性能优化技巧
# ──────────────────────────────────────────────

# 技巧 1：使用集合进行成员检查
# 慢: O(n)
def bad_membership_check(item, items_list):
    return item in items_list

# 快: O(1)
def good_membership_check(item, items_set):
    return item in items_set


# 技巧 2：使用 join 进行字符串拼接
# 慢: 每次创建新字符串对象
def bad_string_concat(strings):
    result = ""
    for s in strings:
        result += s
    return result

# 快: 一次性拼接
def good_string_concat(strings):
    return "".join(strings)


# 技巧 3：使用生成器节省内存
# 慢: 创建完整列表
def bad_large_list():
    return [x * x for x in range(1000000)]

# 快: 惰性求值
def good_large_generator():
    return (x * x for x in range(1000000))


# 技巧 4：使用局部变量
# 慢: 每次访问对象属性
class BadCounter:
    def __init__(self):
        self.count = 0
        self.items = []

    def process(self, data):
        for item in data:
            self.count += 1  # 属性查找开销
            self.items.append(item)  # 属性查找 + 方法查找

# 快: 使用局部变量缓存
class GoodCounter:
    def __init__(self):
        self.count = 0
        self.items = []

    def process(self, data):
        count = self.count  # 缓存到局部变量
        items = self.items
        append = items.append  # 缓存方法引用

        for item in data:
            count += 1
            append(item)

        self.count = count  # 写回


# 技巧 5：使用 __slots__ 减少内存
# 默认: 每个实例都有 __dict__
class DefaultPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

# 优化: 使用 __slots__
class SlottedPoint:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y


# 技巧 6：使用 lru_cache 缓存
from functools import lru_cache

# 无缓存: 每次都计算
def fib_no_cache(n):
    if n < 2:
        return n
    return fib_no_cache(n - 1) + fib_no_cache(n - 2)

# 有缓存: 自动缓存结果
@lru_cache(maxsize=128)
def fib_cached(n):
    if n < 2:
        return n
    return fib_cached(n - 1) + fib_cached(n - 2)
```

#### 3.2 内存优化

```python
"""
Python 内存优化技巧。

SRE 场景：监控系统需要长时间运行，内存泄漏会导致 OOM。
"""

import sys
import gc
from typing import Dict, List


# ──────────────────────────────────────────────
# 1. 内存使用分析
# ──────────────────────────────────────────────
def get_object_size(obj, seen=None) -> int:
    """递归计算对象的内存占用。"""
    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)

    size = sys.getsizeof(obj)

    if isinstance(obj, dict):
        size += sum(get_object_size(k, seen) + get_object_size(v, seen)
                    for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        size += sum(get_object_size(i, seen) for i in obj)
    elif hasattr(obj, '__dict__'):
        size += get_object_size(obj.__dict__, seen)

    return size


# ──────────────────────────────────────────────
# 2. 常见内存泄漏场景
# ──────────────────────────────────────────────

# 泄漏 1：无限增长的缓存
class LeakyCache:
    """永远不会清理的缓存 — 内存泄漏。"""
    def __init__(self):
        self._cache = {}

    def get(self, key):
        return self._cache.get(key)

    def put(self, key, value):
        self._cache[key] = value  # 只增不减


class FixedCache:
    """带最大大小的缓存。"""
    def __init__(self, maxsize=1000):
        self._cache = {}
        self._maxsize = maxsize
        self._access_order = []

    def put(self, key, value):
        if len(self._cache) >= self._maxsize:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = value
        self._access_order.append(key)


# 泄漏 2：循环引用
class LeakyNode:
    """循环引用导致无法被垃圾回收。"""
    def __init__(self, value):
        self.value = value
        self.parent = None
        self.children = []

    def add_child(self, child):
        self.children.append(child)
        child.parent = self  # 循环引用


# 修复：使用 weakref
import weakref

class FixedNode:
    """使用 weakref 打破循环引用。"""
    def __init__(self, value):
        self.value = value
        self._parent = None
        self.children = []

    @property
    def parent(self):
        if self._parent is not None:
            return self._parent()
        return None

    @parent.setter
    def parent(self, node):
        self._parent = weakref.ref(node) if node else None

    def add_child(self, child):
        self.children.append(child)
        child.parent = self


# 泄漏 3：全局变量积累
class MetricsCollector:
    """错误示范：将所有历史数据存在内存中。"""
    _history = []  # 全局变量，只增不减

    def collect(self, metric):
        self._history.append(metric)  # 无限增长


class FixedMetricsCollector:
    """正确做法：限制历史数据量。"""
    def __init__(self, max_history=10000):
        self._history = []
        self._max_history = max_history

    def collect(self, metric):
        self._history.append(metric)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]


# ──────────────────────────────────────────────
# 3. 大数据处理优化
# ──────────────────────────────────────────────

def process_large_file_bad(filepath: str):
    """错误示范：一次性读入全部数据。"""
    with open(filepath) as f:
        lines = f.readlines()  # 全部读入内存
    return [process_line(line) for line in lines]


def process_large_file_good(filepath: str):
    """正确做法：逐行处理。"""
    results = []
    with open(filepath) as f:
        for line in f:  # 逐行读取
            results.append(process_line(line))
    return results


def process_large_file_best(filepath: str):
    """最优做法：生成器，惰性处理。"""
    with open(filepath) as f:
        for line in f:
            yield process_line(line)


# ──────────────────────────────────────────────
# 4. 内存监控装饰器
# ──────────────────────────────────────────────
import tracemalloc
import functools


def memory_profile(func):
    """内存分析装饰器。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()

        result = func(*args, **kwargs)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"\n内存分析: {func.__name__}")
        print(f"  当前: {current / 1024:.1f} KB")
        print(f"  峰值: {peak / 1024:.1f} KB")

        return result
    return wrapper


# 辅助函数
def process_line(line):
    return line.strip().upper()
```

---

### 4. 测试覆盖

#### 4.1 测试框架与最佳实践

```python
"""
SRE 工具测试最佳实践。

测试金字塔：
┌─────────────────────────────────────────────┐
│              E2E 测试 (10%)                  │
│         真实环境的端到端测试                   │
├─────────────────────────────────────────────┤
│          集成测试 (20%)                       │
│      组件间的交互测试                         │
├─────────────────────────────────────────────┤
│         单元测试 (70%)                        │
│     单个函数/类的测试                         │
└─────────────────────────────────────────────┘
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, List


# ──────────────────────────────────────────────
# 测试夹具（Fixtures）
# ──────────────────────────────────────────────

@pytest.fixture
def sample_metrics():
    """提供测试用的指标数据。"""
    return {
        "cpu_percent": 75.5,
        "memory_percent": 60.2,
        "disk_root_percent": 45.0,
        "load_1min": 2.5,
    }


@pytest.fixture
def mock_psutil():
    """Mock psutil 模块。"""
    with patch('psutil.cpu_percent', return_value=75.5), \
         patch('psutil.virtual_memory') as mock_mem, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.cpu_count', return_value=4):

        mock_mem.return_value = MagicMock(
            total=8 * 1024**3,
            available=3 * 1024**3,
            percent=62.5
        )
        mock_disk.return_value = MagicMock(
            total=100 * 1024**3,
            used=50 * 1024**3,
            free=50 * 1024**3,
            percent=50.0
        )
        yield


@pytest.fixture
def temp_db(tmp_path):
    """提供临时数据库。"""
    db_path = str(tmp_path / "test_metrics.db")
    return db_path


# ──────────────────────────────────────────────
# 单元测试
# ──────────────────────────────────────────────

class TestMetricCollector:
    """指标采集器测试。"""

    def test_collect_cpu(self, mock_psutil):
        """测试 CPU 指标采集。"""
        from sre_toolbox.monitor.collector import collect_cpu
        result = collect_cpu()
        assert "cpu_percent" in result
        assert 0 <= result["cpu_percent"] <= 100

    def test_collect_memory(self, mock_psutil):
        """测试内存指标采集。"""
        from sre_toolbox.monitor.collector import collect_memory
        result = collect_memory()
        assert "mem_percent" in result
        assert 0 <= result["mem_percent"] <= 100
        assert "mem_total_gb" in result
        assert result["mem_total_gb"] > 0

    def test_collect_disk(self, mock_psutil):
        """测试磁盘指标采集。"""
        from sre_toolbox.monitor.collector import collect_disk
        result = collect_disk()
        assert any("disk_" in k and "_percent" in k for k in result.keys())


class TestDeltaCalculator:
    """差分计算器测试。"""

    def test_first_call_returns_none(self):
        """首次调用应返回 None。"""
        from sre_toolbox.monitor.delta import DeltaCalculator
        calc = DeltaCalculator()
        result = calc.calculate("test_metric", 100.0)
        assert result is None

    def test_calculate_rate(self):
        """测试速率计算。"""
        from sre_toolbox.monitor.delta import DeltaCalculator
        calc = DeltaCalculator()
        calc.calculate("bytes_sent", 1000)
        time.sleep(0.1)
        result = calc.calculate("bytes_sent", 2000)
        assert result is not None
        assert result > 0  # 应该是正数

    def test_calculate_rates_batch(self, sample_metrics):
        """测试批量差分计算。"""
        from sre_toolbox.monitor.delta import DeltaCalculator
        calc = DeltaCalculator()

        # 第一次调用
        calc.calculate_rates(sample_metrics)
        time.sleep(0.1)

        # 第二次调用
        result = calc.calculate_rates(sample_metrics)
        # 差值为 0，所以速率应该接近 0
        assert isinstance(result, dict)


class TestAlertEngine:
    """告警引擎测试。"""

    def test_alert_triggered_when_threshold_exceeded(self, sample_metrics):
        """测试超过阈值时触发告警。"""
        from sre_toolbox.alert.engine import AlertEngine, AlertRule, Severity
        engine = AlertEngine()
        engine.add_rule(AlertRule(
            name="cpu_high",
            metric="cpu_percent",
            operator=">",
            threshold=70,
            severity=Severity.WARNING,
        ))

        alerts = engine.evaluate(sample_metrics)
        assert len(alerts) == 1
        assert alerts[0].rule_name == "cpu_high"

    def test_no_alert_when_below_threshold(self, sample_metrics):
        """测试低于阈值时不触发告警。"""
        from sre_toolbox.alert.engine import AlertEngine, AlertRule, Severity
        engine = AlertEngine()
        engine.add_rule(AlertRule(
            name="cpu_high",
            metric="cpu_percent",
            operator=">",
            threshold=90,  # 高于 75.5
            severity=Severity.WARNING,
        ))

        alerts = engine.evaluate(sample_metrics)
        assert len(alerts) == 0

    def test_alert_cooldown(self, sample_metrics):
        """测试告警冷却期。"""
        from sre_toolbox.alert.engine import AlertEngine, AlertRule, Severity
        engine = AlertEngine()
        engine.add_rule(AlertRule(
            name="cpu_high",
            metric="cpu_percent",
            operator=">",
            threshold=70,
            severity=Severity.WARNING,
            cooldown=60,  # 60 秒冷却
        ))

        # 第一次触发
        alerts1 = engine.evaluate(sample_metrics)
        assert len(alerts1) == 1

        # 第二次不应触发（冷却期内）
        alerts2 = engine.evaluate(sample_metrics)
        assert len(alerts2) == 0

    def test_alert_recovery(self, sample_metrics):
        """测试告警恢复。"""
        from sre_toolbox.alert.engine import AlertEngine, AlertRule, Severity
        engine = AlertEngine()
        engine.add_rule(AlertRule(
            name="cpu_high",
            metric="cpu_percent",
            operator=">",
            threshold=70,
            severity=Severity.WARNING,
            cooldown=0,
        ))

        # 触发告警
        engine.evaluate(sample_metrics)
        assert len(engine.get_active_alerts()) == 1

        # 指标恢复
        low_metrics = {"cpu_percent": 30.0}
        engine.evaluate(low_metrics)
        assert len(engine.get_active_alerts()) == 0


class TestMetricsStore:
    """指标存储测试。"""

    def test_save_and_query(self, temp_db):
        """测试保存和查询。"""
        from sre_toolbox.monitor.store import MetricsStore
        store = MetricsStore(temp_db)

        store.save("cpu_percent", 75.5, timestamp=1000.0)
        store.save("cpu_percent", 80.0, timestamp=2000.0)

        results = store.query("cpu_percent", 0, 3000)
        assert len(results) == 2
        assert results[0][1] == 75.5  # (timestamp, value)

    def test_batch_save(self, temp_db):
        """测试批量保存。"""
        from sre_toolbox.monitor.store import MetricsStore
        store = MetricsStore(temp_db)

        metrics = {"cpu_percent": 75.5, "mem_percent": 60.0}
        store.save_batch(metrics, timestamp=1000.0)

        assert store.get_latest("cpu_percent") is not None
        assert store.get_latest("mem_percent") is not None

    def test_aggregate(self, temp_db):
        """测试聚合查询。"""
        from sre_toolbox.monitor.store import MetricsStore
        store = MetricsStore(temp_db)

        for i in range(10):
            store.save("test_metric", float(i), timestamp=float(i))

        avg = store.aggregate("test_metric", 0, 10, "avg")
        assert avg is not None
        assert abs(avg - 4.5) < 0.001

    def test_cleanup(self, temp_db):
        """测试数据清理。"""
        from sre_toolbox.monitor.store import MetricsStore
        store = MetricsStore(temp_db, retention_days=0)  # 立即过期

        store.save("old_metric", 1.0, timestamp=1.0)
        store.save("new_metric", 2.0, timestamp=time.time())

        deleted = store.cleanup()
        assert deleted >= 1


class TestMemoryCache:
    """内存缓存测试。"""

    def test_put_and_get(self):
        """测试存取。"""
        from sre_toolbox.monitor.store import MemoryCache
        cache = MemoryCache(max_points=100)

        cache.put("test", 42.0, timestamp=1000.0)
        result = cache.get_latest("test")
        assert result is not None
        assert result[1] == 42.0

    def test_max_points_limit(self):
        """测试最大点数限制。"""
        from sre_toolbox.monitor.store import MemoryCache
        cache = MemoryCache(max_points=5)

        for i in range(10):
            cache.put("test", float(i), timestamp=float(i))

        data = cache.get("test")
        assert len(data) <= 5

    def test_aggregate(self):
        """测试聚合。"""
        from sre_toolbox.monitor.store import MemoryCache
        cache = MemoryCache()

        now = time.time()
        for i in range(10):
            cache.put("test", float(i), timestamp=now - 60 + i)

        avg = cache.aggregate("test", window_seconds=120, func="avg")
        assert avg is not None


# ──────────────────────────────────────────────
# 集成测试
# ──────────────────────────────────────────────

class TestMonitorIntegration:
    """监控系统集成测试。"""

    def test_collect_store_alert_flow(self, temp_db, mock_psutil):
        """测试采集→存储→告警的完整流程。"""
        from sre_toolbox.monitor.collector import collect_all
        from sre_toolbox.monitor.store import MetricsStore
        from sre_toolbox.alert.engine import AlertEngine, AlertRule, Severity

        store = MetricsStore(temp_db)
        engine = AlertEngine()
        engine.add_rule(AlertRule(
            name="cpu_high",
            metric="cpu_percent",
            operator=">",
            threshold=50,  # 低于 mock 的 75.5
            severity=Severity.WARNING,
        ))

        # 采集
        metrics = collect_all()

        # 存储
        store.save_batch(metrics)

        # 告警
        alerts = engine.evaluate(metrics)

        # 验证
        assert store.get_latest("cpu_percent") is not None
        assert len(alerts) > 0


# ──────────────────────────────────────────────
# pytest 配置
# ──────────────────────────────────────────────

# conftest.py
"""
import pytest

@pytest.fixture(autouse=True)
def setup_test_env(tmp_path):
    # 每个测试使用独立的临时目录
    os.chdir(tmp_path)
    yield
"""

# pytest.ini
"""
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --cov=sre_toolbox --cov-report=term-missing
"""
```

#### 4.2 测试运行与覆盖率

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_monitor/test_collector.py

# 运行并显示覆盖率
pytest --cov=sre_toolbox --cov-report=term-missing

# 生成 HTML 覆盖率报告
pytest --cov=sre_toolbox --cov-report=html

# 运行并生成 JUnit XML 报告（用于 CI）
pytest --junitxml=test-results.xml

# 运行并显示最慢的 10 个测试
pytest --durations=10

# 运行标记为 slow 的测试
pytest -m slow

# 并行运行测试（需要 pytest-xdist）
pytest -n auto
```

---

## 💻 实战练习

### 练习 1：实现一个完整的 CLI 工具

**要求**：
- 支持子命令（monitor, exec, report）
- 支持配置文件
- 支持日志级别配置
- 编写测试用例

<details>
<summary>参考答案</summary>

```python
#!/usr/bin/env python3
"""SRE CLI 工具 — 完整实现。"""

import argparse
import sys
import os
import logging
from pathlib import Path


def setup_logging(level="INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s [%(levelname)s] %(message)s'
    )


def cmd_health(args):
    """系统健康检查。"""
    import psutil
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    print(f"CPU:    {cpu}%")
    print(f"Memory: {mem.percent}% ({mem.available / 1e9:.1f}GB free)")
    print(f"Disk:   {disk.percent}% ({disk.free / 1e9:.1f}GB free)")

    if cpu > 90:
        print("WARNING: CPU 使用率过高")
    if mem.percent > 85:
        print("WARNING: 内存使用率过高")
    if disk.percent > 90:
        print("WARNING: 磁盘使用率过高")


def cmd_tail(args):
    """实时跟踪日志。"""
    import time
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"文件不存在: {filepath}")
        sys.exit(1)

    with open(filepath) as f:
        f.seek(0, 2)  # 移到文件末尾
        while True:
            line = f.readline()
            if line:
                if args.grep and args.grep not in line:
                    continue
                print(line, end="")
            else:
                time.sleep(0.1)


def cmd_port_check(args):
    """端口检查。"""
    import socket
    for host_port in args.targets:
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            port = int(port)
        else:
            host = host_port
            port = args.port

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(args.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            status = "OPEN" if result == 0 else "CLOSED"
            print(f"{host}:{port} — {status}")
        except Exception as e:
            print(f"{host}:{port} — ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="SRE CLI 工具")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    subparsers = parser.add_subparsers(dest="command")

    # health
    subparsers.add_parser("health", help="系统健康检查")

    # tail
    tail_parser = subparsers.add_parser("tail", help="跟踪日志")
    tail_parser.add_argument("file", help="日志文件路径")
    tail_parser.add_argument("--grep", help="过滤关键词")

    # port-check
    port_parser = subparsers.add_parser("port-check", help="端口检查")
    port_parser.add_argument("targets", nargs="+", help="目标 (host:port)")
    port_parser.add_argument("-p", "--port", type=int, default=80, help="默认端口")
    port_parser.add_argument("-t", "--timeout", type=int, default=3, help="超时")

    args = parser.parse_args()
    setup_logging(args.log_level)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"health": cmd_health, "tail": cmd_tail,
     "port-check": cmd_port_check}[args.command](args)


if __name__ == "__main__":
    main()
```
</details>

### 练习 2：为 SRE 工具编写完整的测试套件

**要求**：
- 单元测试覆盖率 > 80%
- 包含正常路径和异常路径
- 使用 mock 隔离外部依赖
- 使用 fixture 管理测试数据

<details>
<summary>参考答案</summary>

```python
"""SRE 工具测试套件。"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time


# ──────────────────────────────────────────────
# Fixture
# ──────────────────────────────────────────────

@pytest.fixture
def alert_engine():
    from sre_toolbox.alert.engine import AlertEngine
    return AlertEngine()


@pytest.fixture
def sample_rule():
    from sre_toolbox.alert.engine import AlertRule, Severity
    return AlertRule(
        name="test_rule",
        metric="cpu_percent",
        operator=">",
        threshold=80,
        severity=Severity.WARNING,
        cooldown=0,
    )


@pytest.fixture
def metrics_store(tmp_path):
    from sre_toolbox.monitor.store import MetricsStore
    return MetricsStore(str(tmp_path / "test.db"))


# ──────────────────────────────────────────────
# 测试
# ──────────────────────────────────────────────

class TestAlertEngine:
    def test_add_rule(self, alert_engine, sample_rule):
        alert_engine.add_rule(sample_rule)
        assert len(alert_engine.get_rules()) == 1

    def test_remove_rule(self, alert_engine, sample_rule):
        alert_engine.add_rule(sample_rule)
        alert_engine.remove_rule("test_rule")
        assert len(alert_engine.get_rules()) == 0

    def test_evaluate_triggers_alert(self, alert_engine, sample_rule):
        alert_engine.add_rule(sample_rule)
        alerts = alert_engine.evaluate({"cpu_percent": 90})
        assert len(alerts) == 1
        assert alerts[0].rule_name == "test_rule"

    def test_evaluate_no_alert(self, alert_engine, sample_rule):
        alert_engine.add_rule(sample_rule)
        alerts = alert_engine.evaluate({"cpu_percent": 50})
        assert len(alerts) == 0

    def test_missing_metric(self, alert_engine, sample_rule):
        alert_engine.add_rule(sample_rule)
        alerts = alert_engine.evaluate({"other_metric": 90})
        assert len(alerts) == 0

    def test_disabled_rule(self, alert_engine):
        from sre_toolbox.alert.engine import AlertRule, Severity
        rule = AlertRule(
            name="disabled", metric="cpu", operator=">",
            threshold=50, severity=Severity.WARNING, enabled=False
        )
        alert_engine.add_rule(rule)
        alerts = alert_engine.evaluate({"cpu": 90})
        assert len(alerts) == 0


class TestMetricsStore:
    def test_save_and_retrieve(self, metrics_store):
        metrics_store.save("test", 42.0, timestamp=1000.0)
        result = metrics_store.get_latest("test")
        assert result is not None
        assert result[1] == 42.0

    def test_query_empty(self, metrics_store):
        result = metrics_store.query("nonexistent", 0, 1000)
        assert result == []

    def test_batch_save(self, metrics_store):
        metrics = {"a": 1.0, "b": 2.0, "c": 3.0}
        metrics_store.save_batch(metrics, timestamp=1000.0)
        for name in metrics:
            assert metrics_store.get_latest(name) is not None

    def test_aggregate_avg(self, metrics_store):
        for i in range(5):
            metrics_store.save("test", float(i), timestamp=float(i))
        avg = metrics_store.aggregate("test", 0, 5, "avg")
        assert abs(avg - 2.0) < 0.001

    def test_aggregate_max(self, metrics_store):
        for i in range(5):
            metrics_store.save("test", float(i), timestamp=float(i))
        max_val = metrics_store.aggregate("test", 0, 5, "max")
        assert max_val == 4.0

    def test_cleanup(self, metrics_store):
        metrics_store.save("old", 1.0, timestamp=1.0)
        metrics_store.save("new", 2.0, timestamp=time.time())
        # retention_days=0 means everything is expired
        store = metrics_store
        store.retention_days = 0
        deleted = store.cleanup()
        assert deleted >= 1
```
</details>

### 练习 3：性能优化实战

**要求**：
- 找出给定代码的性能瓶颈
- 使用 cProfile 分析
- 实施优化并验证效果

```python
# 待优化的代码
def process_logs_slow(log_lines: list) -> dict:
    """处理日志行，统计各级别的数量。"""
    result = {}
    for line in log_lines:
        parts = line.split(" ")
        if len(parts) >= 3:
            level = parts[2]
            if level in result:
                result[level] = result[level] + 1
            else:
                result[level] = 1
    return result

# 测试数据
import random
levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
test_lines = [f"2024-01-01 12:00:{i:02d} {random.choice(levels)} message {i}"
              for i in range(100000)]
```

<details>
<summary>参考答案</summary>

```python
from collections import Counter
import time


# 优化版本 1：使用 Counter
def process_logs_fast(log_lines: list) -> dict:
    """使用 Counter 统计。"""
    levels = (line.split(" ")[2] for line in log_lines if len(line.split(" ")) >= 3)
    return dict(Counter(levels))


# 优化版本 2：预分配 + 局部变量
def process_logs_faster(log_lines: list) -> dict:
    """预分配结果 + 局部变量优化。"""
    result = {}
    result_get = result.get
    for line in log_lines:
        parts = line.split(" ")
        if len(parts) >= 3:
            level = parts[2]
            result[level] = result_get(level, 0) + 1
    return result


# 性能对比
def benchmark_comparison():
    import random
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    test_lines = [f"2024-01-01 12:00:{i:02d} {random.choice(levels)} msg {i}"
                  for i in range(100000)]

    for func in [process_logs_slow, process_logs_fast, process_logs_faster]:
        start = time.perf_counter()
        result = func(test_lines)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__}: {elapsed:.3f}s — {result}")

# 预期结果：
# process_logs_slow:    ~0.15s
# process_logs_fast:    ~0.08s (Counter 优化)
# process_logs_faster:  ~0.06s (局部变量优化)
```
</details>

---

## 🎯 面试题精选

### 问题 1：如何保证 SRE 工具的代码质量？

**参考答案**：
1. **代码审查**：每次提交都经过审查，使用自动化工具辅助
2. **测试覆盖**：单元测试 > 80%，关键路径 100%
3. **类型注解**：使用 mypy 进行静态类型检查
4. **代码风格**：使用 black、flake8 统一风格
5. **CI/CD**：自动化测试、lint、构建
6. **文档**：函数文档字符串、使用示例

### 问题 2：Python 性能优化有哪些常用手段？

**参考答案**：
1. **算法优化**：选择合适的数据结构（集合 vs 列表查重）
2. **缓存**：使用 lru_cache、functools.cache 缓存计算结果
3. **生成器**：用生成器替代列表，节省内存
4. **局部变量**：将频繁访问的属性/方法缓存为局部变量
5. **并行处理**：I/O 密集用 threading，CPU 密集用 multiprocessing
6. **C 扩展**：关键路径使用 numpy、cython 等
7. **profiling**：先用 cProfile 定位瓶颈，再针对性优化

### 问题 3：什么是测试金字塔？如何在 SRE 工具中应用？

**参考答案**：
测试金字塔从下到上：
- **单元测试（70%）**：测试单个函数/类，速度快，隔离好
- **集成测试（20%）**：测试组件间的交互，如采集→存储→告警
- **E2E 测试（10%）**：在真实环境中测试完整流程

SRE 工具中：Mock SSH 连接做单元测试，用 Docker 容器做集成测试，在测试环境做 E2E 测试。

### 问题 4：如何发现和修复 Python 内存泄漏？

**参考答案**：
1. **检测**：使用 `tracemalloc`、`memory_profiler` 跟踪内存增长
2. **常见原因**：
   - 无限增长的缓存/列表
   - 循环引用（使用 weakref 解决）
   - 全局变量积累
   - 未关闭的资源（文件、连接）
3. **预防**：限制缓存大小、使用上下文管理器、定期清理

### 问题 5：代码审查应该关注哪些方面？

**参考答案**：
- **正确性**：边界条件、异常处理、逻辑正确
- **安全性**：注入、硬编码密钥、不安全的反序列化
- **可靠性**：超时设置、重试机制、资源清理
- **性能**：N+1 查询、不必要的循环、大文件一次性读取
- **可维护性**：函数长度、命名清晰度、文档

### 问题 6：如何设计一个可测试的 SRE 工具？

**参考答案**：
1. **依赖注入**：通过构造函数传入依赖，而非内部创建
2. **接口抽象**：依赖抽象接口，而非具体实现
3. **Mock 友好**：避免直接调用系统 API，通过可替换的组件调用
4. **配置外部化**：配置从文件/环境变量读取，而非硬编码
5. **无状态设计**：函数尽量无副作用，类尽量不可变

### 问题 7：pytest 的 fixture 有什么作用？与 unittest 的 setUp/tearDown 有什么区别？

**参考答案**：
fixture 的优势：
1. **更灵活**：可以按名称自动注入，不需要继承
2. **作用域控制**：function/class/module/session 级别
3. **参数化**：支持参数化 fixture
4. **自动清理**：yield 之后的代码自动执行清理
5. **组合**：fixture 可以依赖其他 fixture

### 问题 8：什么是 Mock？什么时候应该使用 Mock？

**参考答案**：
Mock 是模拟对象，替代真实依赖进行测试。应该使用 Mock 的场景：
1. 外部服务（SSH、HTTP API、数据库）
2. 系统调用（文件系统、网络、进程）
3. 时间依赖（time.time、time.sleep）
4. 随机数（random）
5. 价格昂贵的操作

不应该 Mock 的场景：纯函数、数据结构操作。

### 问题 9：如何实现 SRE 工具的持续集成？

**参考答案**：
1. **代码检查**：black（格式）、flake8（风格）、mypy（类型）
2. **单元测试**：pytest + 覆盖率报告
3. **安全扫描**：bandit（安全问题）、safety（依赖漏洞）
4. **构建打包**：构建 Docker 镜像或 Python 包
5. **部署测试**：在测试环境验证
6. **性能基准**：关键路径的性能回归测试

### 问题 10：如何评估 SRE 工具的生产就绪度？

**参考答案**：
1. **可靠性**：异常处理完善、重试机制、优雅降级
2. **可观测性**：日志、指标、告警、链路追踪
3. **性能**：满足 SLO 要求、资源消耗合理
4. **安全性**：无硬编码密钥、输入验证、最小权限
5. **可维护性**：代码清晰、测试充分、文档完整
6. **可部署性**：支持 systemd、Docker、配置管理
7. **可扩展性**：插件架构、配置驱动

---

## 📚 深入阅读

### 官方文档
- [pytest 文档](https://docs.pytest.org/)
- [unittest.mock 文档](https://docs.python.org/3/library/unittest.mock.html)
- [cProfile 文档](https://docs.python.org/3/library/profile.html)
- [tracemalloc 文档](https://docs.python.org/3/library/tracemalloc.html)

### 推荐书籍
- 《Python Testing with pytest》— Brian Okken
- 《High Performance Python》— Micha Gorelick
- 《Clean Code in Python》— Mariano Anaya
- 《Effective Python》— Brett Slatkin

### 技术博客
- [Real Python: Testing in Python](https://realpython.com/python-testing/)
- [Real Python: Python Performance](https://realpython.com/python-performance/)
- [Python 官方性能指南](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)

---

## ✅ 自检清单

### 理论检查
- [ ] 能解释测试金字塔及其在 SRE 工具中的应用
- [ ] 能解释 Python 内存管理和常见泄漏原因
- [ ] 能解释 cProfile 的使用方法和输出解读
- [ ] 能解释代码审查的核心关注点
- [ ] 能解释 pytest fixture 的作用域和使用方式

### 实操检查
- [ ] 能独立完成一个 SRE CLI 工具的开发
- [ ] 能编写覆盖率 > 80% 的测试用例
- [ ] 能使用 cProfile 定位性能瓶颈
- [ ] 能发现和修复常见代码问题
- [ ] 能进行 Python 内存优化

### 能力验证
- [ ] 能从零构建一个完整的 SRE 工具项目
- [ ] 能通过代码审查发现 CRITICAL 和 HIGH 级别问题
- [ ] 能将 Python 工具的性能提升 50% 以上
- [ ] 能为 SRE 工具建立完整的 CI/CD 流程
