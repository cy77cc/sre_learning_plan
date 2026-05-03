# Day 51: CLI 工具开发

> 📅 日期：2026-05-03
> 📖 学习主题：Python CLI 工具开发（argparse/click/typer, rich 美化输出, 交互式提示, 打包分发, entry_points）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 46（Python 基础语法）, Day 47（Python 标准库）, Day 48（网络编程）

## 🎯 学习目标

- 掌握 argparse、click、typer 三种 CLI 框架的核心用法与适用场景
- 能使用 rich 库美化终端输出（表格、进度条、语法高亮、面板）
- 能实现交互式提示、确认对话框、密码输入等用户交互
- 掌握 Python 包的打包分发流程（pyproject.toml、setuptools、entry_points）
- 能独立开发一个生产级的 SRE CLI 工具

---

## 📖 核心知识点

### 1. 为什么 SRE 需要 CLI 工具？

```
┌─────────────────────────────────────────────────────────────────┐
│                    SRE 工具链中的 CLI                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  日常运维                    故障排查                   自动化    │
│  ┌────────────┐            ┌────────────┐           ┌────────┐ │
│  │ kubectl    │            │ tcpdump    │           │ Ansible│ │
│  │ docker     │            │ strace     │           │ Terra- │ │
│  │ systemctl  │            │ journalctl │           │ form   │ │
│  └──────┬─────┘            └──────┬─────┘           └───┬────┘ │
│         │                         │                     │      │
│         └─────────────┬───────────┘─────────────────────┘      │
│                       ▼                                        │
│              ┌─────────────────┐                               │
│              │   自定义 CLI 工具  │                               │
│              │  (Python + click) │                               │
│              └─────────────────┘                               │
│                                                                 │
│  SRE 为什么需要自定义 CLI？                                       │
│  1. 封装复杂的多步骤操作为简单命令                                │
│  2. 标准化团队的操作流程                                         │
│  3. 集成多个系统（K8s + 监控 + 日志）                            │
│  4. 提供统一的操作入口                                           │
│  5. 减少人为操作失误                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. argparse：标准库的 CLI 框架

#### 2.1 基础用法

```python
#!/usr/bin/env python3
"""
argparse 详解：Python 标准库的 CLI 框架
SRE 场景：快速编写简单的运维脚本

argparse 的优势：
- 标准库，无需安装
- 自动生成帮助信息和用法说明
- 支持位置参数、可选参数、子命令
- 自动类型转换和验证
"""

import argparse
import sys


def create_simple_parser():
    """
    基础 argparse 用法
    SRE 场景：简单的服务检查脚本
    """
    parser = argparse.ArgumentParser(
        description="SRE Service Health Checker",
        epilog="Example: %(prog)s --host web-01 --port 8080",
    )

    # 位置参数（必须提供）
    parser.add_argument(
        "service",
        help="Service name to check",
    )

    # 可选参数（带 -- 前缀）
    parser.add_argument(
        "-H", "--host",
        default="localhost",
        help="Host to connect to (default: localhost)",
    )

    parser.add_argument(
        "-p", "--port",
        type=int,
        default=8080,
        help="Port number (default: 8080)",
    )

    # 布尔标志
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    # 互斥参数组
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    output_group.add_argument(
        "--csv",
        action="store_true",
        help="Output in CSV format",
    )

    # 带默认值的选择参数
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Connection timeout in seconds (default: 5.0)",
    )

    # 必选的可选参数（听起来矛盾，但很有用）
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "staging", "production"],
        help="Target environment",
    )

    return parser


def demo_argparse():
    """argparse 演示"""
    parser = create_simple_parser()

    # 解析命令行参数
    # 在实际使用中用 sys.argv[1:]
    # 这里用列表模拟
    args = parser.parse_args(["api-service", "--host", "10.0.1.1", "--env", "production", "-v"])

    print(f"Service: {args.service}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Verbose: {args.verbose}")
    print(f"Timeout: {args.timeout}")
    print(f"Environment: {args.env}")


# ============================================================
# 子命令：类似 git 的命令结构
# ============================================================

def create_subcommand_parser():
    """
    子命令解析器
    SRE 场景：构建多功能的运维工具（类似 kubectl）
    """
    parser = argparse.ArgumentParser(
        description="SRE Operations Tool",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True,
    )

    # 子命令: check
    check_parser = subparsers.add_parser(
        "check",
        help="Check service health",
        aliases=["c"],
    )
    check_parser.add_argument("service", help="Service name")
    check_parser.add_argument("-n", "--namespace", default="default")
    check_parser.add_argument("--timeout", type=float, default=5.0)

    # 子命令: deploy
    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy a service",
        aliases=["d"],
    )
    deploy_parser.add_argument("service", help="Service name")
    deploy_parser.add_argument("--replicas", type=int, default=3)
    deploy_parser.add_argument("--image", required=True, help="Container image")
    deploy_parser.add_argument("--dry-run", action="store_true")

    # 子命令: logs
    logs_parser = subparsers.add_parser(
        "logs",
        help="View service logs",
        aliases=["l"],
    )
    logs_parser.add_argument("service", help="Service name")
    logs_parser.add_argument("-f", "--follow", action="store_true")
    logs_parser.add_argument("--tail", type=int, default=100)
    logs_parser.add_argument("--since", default="1h", help="Time duration (e.g., 1h, 30m)")

    # 子命令: scale
    scale_parser = subparsers.add_parser(
        "scale",
        help="Scale a service",
        aliases=["s"],
    )
    scale_parser.add_argument("service", help="Service name")
    scale_parser.add_argument("--replicas", type=int, required=True)

    return parser


def demo_subcommands():
    """子命令演示"""
    parser = create_subcommand_parser()

    # 模拟命令行
    args = parser.parse_args(["check", "api-gateway", "-n", "production"])
    print(f"Command: {args.command}")
    print(f"Service: {args.service}")
    print(f"Namespace: {args.namespace}")

    print()

    args = parser.parse_args(["deploy", "auth-service", "--image", "auth:v2.1.0", "--replicas", "5"])
    print(f"Command: {args.command}")
    print(f"Service: {args.service}")
    print(f"Image: {args.image}")
    print(f"Replicas: {args.replicas}")


if __name__ == "__main__":
    print("=== 基础 argparse ===")
    demo_argparse()
    print("\n=== 子命令 ===")
    demo_subcommands()
```

#### 2.2 argparse 高级技巧

```python
#!/usr/bin/env python3
"""
argparse 高级用法
SRE 场景：构建复杂的运维工具
"""

import argparse
import json
import os


class ConfigAction(argparse.Action):
    """
    自定义 Action：从配置文件加载参数
    SRE 场景：支持配置文件 + 命令行参数的组合
    """
    def __call__(self, parser, namespace, values, option_string=None):
        with open(values) as f:
            config = json.load(f)
        for key, value in config.items():
            setattr(namespace, key, value)


def int_range(min_val, max_val):
    """
    自定义类型：限制整数范围
    SRE 场景：验证端口号、副本数等参数
    """
    def validator(value):
        ivalue = int(value)
        if ivalue < min_val or ivalue > max_val:
            raise argparse.ArgumentTypeError(
                f"{value} is not in range [{min_val}, {max_val}]"
            )
        return ivalue
    validator.__name__ = f"int[{min_val}-{max_val}]"
    return validator


def env_var(value):
    """
    自定义类型：支持环境变量展开
    SRE 场景：从环境变量读取敏感配置
    """
    if value.startswith("$"):
        env_name = value[1:]
        env_value = os.environ.get(env_name)
        if env_value is None:
            raise argparse.ArgumentTypeError(
                f"Environment variable {env_name} is not set"
            )
        return env_value
    return value


def create_advanced_parser():
    """高级 argparse 配置"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
SRE Operations Tool v2.0

A comprehensive tool for managing production services.
Supports health checks, deployments, and monitoring.

Examples:
  sre-tool check api-gateway --env production
  sre-tool deploy api-gateway --image v2.1.0 --replicas 5
  sre-tool scale api-gateway --replicas 10
        """,
    )

    # 从配置文件加载参数
    parser.add_argument(
        "--config",
        action=ConfigAction,
        help="Load config from JSON file",
    )

    # 支持环境变量展开
    parser.add_argument(
        "--token",
        type=env_var,
        default="$SRE_TOOL_TOKEN",
        help="API token (supports $ENV_VAR syntax)",
    )

    # 端口号验证
    parser.add_argument(
        "--port",
        type=int_range(1, 65535),
        default=8080,
        help="Port number (1-65535)",
    )

    # 全局选项
    parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v, -vv, -vvv)",
    )

    parser.add_argument(
        "--output", "-o",
        choices=["text", "json", "yaml", "table"],
        default="text",
        help="Output format",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )

    return parser


if __name__ == "__main__":
    parser = create_advanced_parser()
    # 显示帮助信息
    parser.print_help()
```

---

### 3. click：Python 最流行的 CLI 框架

#### 3.1 click 核心概念

```
┌─────────────────────────────────────────────────────────────────┐
│                    click 核心概念                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  装饰器驱动的 CLI 框架                                            │
│                                                                 │
│  @click.group()          → 定义命令组（类似 git）                  │
│  @group.command()        → 定义子命令                             │
│  @click.option()         → 定义可选参数                           │
│  @click.argument()       → 定义位置参数                           │
│  @click.pass_context     → 传递上下文对象                          │
│  @click.confirmation_prompt → 确认提示                            │
│                                                                 │
│  click vs argparse:                                              │
│  ┌──────────────┬──────────────┬──────────────────┐             │
│  │ 特性          │ argparse     │ click            │             │
│  ├──────────────┼──────────────┼──────────────────┤             │
│  │ 定义方式      │ 命令式        │ 装饰器式          │             │
│  │ 子命令        │ 手动配置      │ group 自动组织    │             │
│  │ 自动补全      │ 需手动实现    │ 内置支持          │             │
│  │ 彩色输出      │ 无            │ 内置              │             │
│  │ 进度条        │ 无            │ 内置              │             │
│  │ 提示输入      │ 无            │ 内置              │             │
│  │ 类型验证      │ 基础          │ 丰富              │             │
│  │ 依赖         │ 标准库        │ pip install click │             │
│  └──────────────┴──────────────┴──────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 click 实战

```python
#!/usr/bin/env python3
"""
click 框架详解
SRE 场景：构建专业的运维 CLI 工具

安装: pip install click
"""

import click
import json
import sys
import os
from pathlib import Path


# ============================================================
# 基础命令
# ============================================================

@click.command()
@click.argument("name")
@click.option("--greeting", "-g", default="Hello", help="Greeting word")
@click.option("--count", "-c", default=1, type=click.IntRange(1, 100), help="Repeat count")
@click.option("--uppercase", "-u", is_flag=True, help="Uppercase output")
def greet(name, greeting, count, uppercase):
    """Simple greeting command."""
    for _ in range(count):
        msg = f"{greeting}, {name}!"
        if uppercase:
            msg = msg.upper()
        click.echo(msg)


# ============================================================
# 命令组（类似 kubectl 的结构）
# ============================================================

@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--config", "-c", type=click.Path(), default="~/.sre-tool.json",
              help="Config file path")
@click.pass_context
def cli(ctx, verbose, config):
    """
    SRE Operations Tool

    A comprehensive CLI for managing production services.
    """
    # 确保 ctx.obj 存在
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    # 加载配置文件
    config_path = Path(config).expanduser()
    if config_path.exists():
        with open(config_path) as f:
            ctx.obj["config"] = json.load(f)
    else:
        ctx.obj["config"] = {}


# ============================================================
# 子命令: check
# ============================================================

@cli.command()
@click.argument("services", nargs=-1, required=True)
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
@click.option("--timeout", "-t", default=5.0, help="Check timeout in seconds")
@click.option("--output", "-o", type=click.Choice(["text", "json", "table"]), default="text")
@click.pass_context
def check(ctx, services, namespace, timeout, output):
    """Check service health status."""
    verbose = ctx.obj.get("verbose", False)
    results = []

    with click.progressbar(
        services,
        label="Checking services",
        show_eta=True,
    ) as bar:
        for service in bar:
            if verbose:
                click.echo(f"\n  Checking {service}...", err=True)

            # 模拟健康检查
            import time
            time.sleep(0.5)
            result = {
                "service": service,
                "namespace": namespace,
                "status": "healthy",
                "latency_ms": 42.5,
            }
            results.append(result)

    # 输出结果
    if output == "json":
        click.echo(json.dumps(results, indent=2))
    elif output == "table":
        click.echo(f"{'Service':<20} {'Namespace':<12} {'Status':<10} {'Latency':<10}")
        click.echo("-" * 55)
        for r in results:
            click.echo(f"{r['service']:<20} {r['namespace']:<12} {r['status']:<10} {r['latency_ms']:<10}")
    else:
        for r in results:
            status_color = "green" if r["status"] == "healthy" else "red"
            click.secho(f"  {r['service']}: {r['status']}", fg=status_color)


# ============================================================
# 子命令: deploy
# ============================================================

@cli.command()
@click.argument("service")
@click.option("--image", "-i", required=True, help="Container image (e.g., app:v2.1.0)")
@click.option("--replicas", "-r", type=click.IntRange(1, 100), default=3, help="Number of replicas")
@click.option("--namespace", "-n", default="default")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def deploy(ctx, service, image, replicas, namespace, dry_run, force):
    """Deploy a service to Kubernetes."""
    verbose = ctx.obj.get("verbose", False)

    # 显示部署信息
    click.echo(f"Deploying {service}:")
    click.echo(f"  Image:    {image}")
    click.echo(f"  Replicas: {replicas}")
    click.echo(f"  Namespace: {namespace}")

    if dry_run:
        click.secho("\n[DRY RUN] No changes will be made.", fg="yellow")
        return

    # 确认提示（除非 --force）
    if not force:
        click.confirm(
            f"\nDo you want to deploy {service} with {replicas} replicas?",
            abort=True,
        )

    # 模拟部署过程
    with click.progressbar(
        length=100,
        label="Deploying",
        show_eta=True,
    ) as bar:
        for i in range(100):
            import time
            time.sleep(0.05)
            bar.update(1)

    click.secho(f"\nSuccessfully deployed {service}!", fg="green")


# ============================================================
# 子命令: logs
# ============================================================

@cli.command()
@click.argument("service")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--tail", "-t", type=int, default=100, help="Number of lines to show")
@click.option("--since", "-s", default="1h", help="Show logs since (e.g., 1h, 30m, 2d)")
@click.option("--grep", "-g", help="Filter logs by pattern")
@click.option("--level", "-l", type=click.Choice(["DEBUG", "INFO", "WARN", "ERROR"]),
              help="Filter by log level")
@click.pass_context
def logs(ctx, service, follow, tail, since, grep, level):
    """View service logs."""
    click.echo(f"Logs for {service} (last {tail} lines, since {since}):")

    # 模拟日志输出
    import random
    levels = ["INFO", "WARN", "ERROR", "DEBUG"]
    for i in range(min(tail, 20)):
        log_level = random.choice(levels)
        if level and log_level != level:
            continue
        line = f"[2026-05-03 10:{i:02d}:00] [{log_level}] {service}: Request processed {i}"
        if grep and grep not in line:
            continue
        if log_level == "ERROR":
            click.secho(line, fg="red")
        elif log_level == "WARN":
            click.secho(line, fg="yellow")
        else:
            click.echo(line)


# ============================================================
# 子命令: scale
# ============================================================

@cli.command()
@click.argument("service")
@click.option("--replicas", "-r", type=click.IntRange(0, 100), required=True,
              help="Target number of replicas (0 to stop)")
@click.option("--namespace", "-n", default="default")
@click.confirmation_prompt(prompt="Are you sure you want to scale?")
@click.pass_context
def scale(ctx, service, replicas, namespace):
    """Scale a service deployment."""
    if replicas == 0:
        click.secho(f"WARNING: This will stop {service}!", fg="red", bold=True)

    click.echo(f"Scaling {service} to {replicas} replicas in {namespace}...")

    # 模拟扩缩容
    import time
    with click.progressbar(range(replicas), label="Scaling") as bar:
        for _ in bar:
            time.sleep(0.3)

    click.secho(f"Scaled {service} to {replicas} replicas", fg="green")


# ============================================================
# 子命令: config
# ============================================================

@cli.group()
def config():
    """Manage tool configuration."""
    pass


@config.command("show")
@click.pass_context
def config_show(ctx):
    """Show current configuration."""
    cfg = ctx.obj.get("config", {})
    if cfg:
        click.echo(json.dumps(cfg, indent=2))
    else:
        click.echo("No configuration found")


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx, key, value):
    """Set a configuration value."""
    config_path = Path("~/.sre-tool.json").expanduser()
    cfg = {}
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)

    cfg[key] = value
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)

    click.echo(f"Set {key} = {value}")


if __name__ == "__main__":
    cli()
```

---

### 4. typer：基于类型注解的 CLI 框架

#### 4.1 typer 核心优势

```python
#!/usr/bin/env python3
"""
typer 框架详解
SRE 场景：用最简洁的代码构建 CLI 工具

安装: pip install typer[all]

typer 的核心优势：
1. 基于 Python 类型注定义参数
2. 自动生成帮助信息
3. 自动补全支持
4. 内置 rich 集成
"""

import typer
from typing import Optional, List
from enum import Enum
from pathlib import Path
import json

app = typer.Typer(
    name="sre-tool",
    help="SRE Operations Tool - Manage production services",
    add_completion=False,
)


# ============================================================
# 枚举类型：自动生成选项列表
# ============================================================

class Environment(str, Enum):
    dev = "dev"
    staging = "staging"
    production = "production"


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    table = "table"


# ============================================================
# 基础命令：类型注解即参数定义
# ============================================================

@app.command()
def check(
    services: List[str] = typer.Argument(..., help="Service names to check"),
    namespace: str = typer.Option("default", "-n", "--namespace", help="K8s namespace"),
    timeout: float = typer.Option(5.0, "-t", "--timeout", help="Timeout in seconds"),
    output: OutputFormat = typer.Option(OutputFormat.text, "-o", "--output"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Check service health status."""
    results = []
    for service in services:
        # 模拟健康检查
        import time
        time.sleep(0.3)
        result = {
            "service": service,
            "namespace": namespace,
            "status": "healthy",
            "latency_ms": 42.5,
        }
        results.append(result)

        if verbose:
            typer.echo(f"  Checked {service}: {result['status']}")

    if output == OutputFormat.json:
        typer.echo(json.dumps(results, indent=2))
    else:
        for r in results:
            status = r["status"]
            color = typer.colors.GREEN if status == "healthy" else typer.colors.RED
            typer.secho(f"  {r['service']}: {status}", fg=color)


@app.command()
def deploy(
    service: str = typer.Argument(..., help="Service name"),
    image: str = typer.Option(..., "-i", "--image", help="Container image"),
    replicas: int = typer.Option(3, "-r", "--replicas", min=1, max=100),
    env: Environment = typer.Option(Environment.staging, "-e", "--env"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Deploy a service."""
    typer.echo(f"Deploying {service}:")
    typer.echo(f"  Image:    {image}")
    typer.echo(f"  Replicas: {replicas}")
    typer.echo(f"  Env:      {env.value}")

    if dry_run:
        typer.secho("[DRY RUN] No changes will be made.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    if not force:
        confirm = typer.confirm(f"Deploy {service} to {env.value}?")
        if not confirm:
            raise typer.Abort()

    # 模拟部署
    with typer.progressbar(range(100), label="Deploying") as progress:
        for _ in progress:
            import time
            time.sleep(0.02)

    typer.secho(f"Deployed {service} successfully!", fg=typer.colors.GREEN)


@app.command()
def scale(
    service: str = typer.Argument(..., help="Service name"),
    replicas: int = typer.Option(..., "-r", "--replicas", min=0, max=100),
    namespace: str = typer.Option("default", "-n", "--namespace"),
):
    """Scale a service."""
    if replicas == 0:
        typer.secho(f"WARNING: This will stop {service}!", fg=typer.colors.RED, bold=True)
        if not typer.confirm("Are you sure?"):
            raise typer.Abort()

    typer.echo(f"Scaling {service} to {replicas} replicas...")
    typer.secho(f"Scaled {service} to {replicas} replicas", fg=typer.colors.GREEN)


# ============================================================
# 子命令组
# ============================================================

config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    format: OutputFormat = typer.Option(OutputFormat.text, "-o", "--output"),
):
    """Show current configuration."""
    config = {"api_url": "https://api.example.com", "timeout": 30}
    if format == OutputFormat.json:
        typer.echo(json.dumps(config, indent=2))
    else:
        for key, value in config.items():
            typer.echo(f"  {key}: {value}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
):
    """Set a configuration value."""
    typer.echo(f"Set {key} = {value}")


# ============================================================
# 回调：全局选项
# ============================================================

@app.callback()
def main(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    config: Optional[Path] = typer.Option(None, "-c", "--config", help="Config file"),
):
    """
    SRE Operations Tool

    Manage production services from the command line.
    """
    if verbose:
        typer.echo("Verbose mode enabled")
    if config:
        typer.echo(f"Using config: {config}")


if __name__ == "__main__":
    app()
```

---

### 5. rich：美化终端输出

#### 5.1 rich 核心功能

```python
#!/usr/bin/env python3
"""
rich 库详解：美化终端输出
SRE 场景：让 CLI 工具的输出更专业、更易读

安装: pip install rich

rich 的核心功能：
1. 彩色文本和样式
2. 表格
3. 进度条
4. 面板和布局
5. 语法高亮
6. Markdown 渲染
7. 树形结构
8. Live 实时更新
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.tree import Tree
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.style import Style
from rich import box
import time
import json

console = Console()


# ============================================================
# 基础输出
# ============================================================

def demo_basic_output():
    """基础彩色输出"""
    console.print("\n[bold]=== 基础输出 ===[/bold]")

    # 彩色文本
    console.print("[red]ERROR[/red]: Service is down")
    console.print("[yellow]WARNING[/yellow]: High CPU usage")
    console.print("[green]OK[/green]: All services healthy")
    console.print("[blue]INFO[/blue]: Deployment started")

    # 样式组合
    console.print("[bold red]CRITICAL[/bold red]: Database connection lost")
    console.print("[dim]Debug: connecting to 10.0.1.1:5432[/dim]")

    # 内联样式
    console.print("Service", style="bold cyan", end="")
    console.print(" is ", end="")
    console.print("healthy", style="bold green")


# ============================================================
# 表格
# ============================================================

def demo_table():
    """表格输出"""
    console.print("\n[bold]=== 表格 ===[/bold]")

    table = Table(
        title="Service Health Status",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Replicas", justify="right")
    table.add_column("CPU %", justify="right")
    table.add_column("Memory %", justify="right")
    table.add_column("Uptime", justify="right")

    # 添加数据行
    services = [
        ("api-gateway", "healthy", "3/3", "45%", "62%", "15d 3h"),
        ("auth-service", "healthy", "2/2", "38%", "55%", "15d 3h"),
        ("notification", "degraded", "1/3", "92%", "88%", "2d 1h"),
        ("batch-worker", "stopped", "0/1", "0%", "0%", "N/A"),
        ("redis", "healthy", "1/1", "12%", "45%", "30d 12h"),
    ]

    for name, status, replicas, cpu, mem, uptime in services:
        if status == "healthy":
            status_text = Text(status, style="bold green")
        elif status == "degraded":
            status_text = Text(status, style="bold yellow")
        else:
            status_text = Text(status, style="bold red")

        table.add_row(name, status_text, replicas, cpu, mem, uptime)

    console.print(table)


# ============================================================
# 面板
# ============================================================

def demo_panel():
    """面板输出"""
    console.print("\n[bold]=== 面板 ===[/bold]")

    # 简单面板
    console.print(Panel("All systems operational", title="Status", border_style="green"))

    # 复杂面板
    health_data = """
[green]api-gateway[/green]: 3/3 replicas ready
[green]auth-service[/green]: 2/2 replicas ready
[yellow]notification[/yellow]: 1/3 replicas ready (degraded)
[red]batch-worker[/red]: 0/1 replicas (stopped)
    """
    console.print(Panel(
        health_data.strip(),
        title="[bold]Service Health[/bold]",
        border_style="blue",
        padding=(1, 2),
    ))

    # JSON 面板
    config = {"api_url": "https://api.example.com", "timeout": 30, "retries": 3}
    json_str = json.dumps(config, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Configuration", border_style="cyan"))


# ============================================================
# 进度条
# ============================================================

def demo_progress():
    """进度条"""
    console.print("\n[bold]=== 进度条 ===[/bold]")

    # 简单进度条
    with Progress() as progress:
        task = progress.add_task("[cyan]Downloading...", total=100)
        while not progress.finished:
            progress.update(task, advance=1)
            time.sleep(0.02)

    # 自定义进度条
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[green]Deploying service...", total=50)
        for i in range(50):
            progress.update(task, advance=1)
            time.sleep(0.05)

    # 多任务进度条
    with Progress() as progress:
        task1 = progress.add_task("[red]Downloading packages...", total=20)
        task2 = progress.add_task("[green]Installing...", total=30)
        task3 = progress.add_task("[blue]Configuring...", total=10)

        while not progress.finished:
            if not progress.tasks[0].finished:
                progress.update(task1, advance=0.5)
            if not progress.tasks[1].finished:
                progress.update(task2, advance=0.3)
            if not progress.tasks[2].finished:
                progress.update(task3, advance=0.1)
            time.sleep(0.05)


# ============================================================
# 树形结构
# ============================================================

def demo_tree():
    """树形结构"""
    console.print("\n[bold]=== 树形结构 ===[/bold]")

    tree = Tree("[bold]Production Cluster[/bold]")
    dc_east = tree.add("[cyan]dc-east[/cyan]")
    dc_east.add("[green]web-01[/green] (10.0.1.1)")
    dc_east.add("[green]web-02[/green] (10.0.1.2)")
    dc_east.add("[yellow]api-01[/yellow] (10.0.1.3) - degraded")

    dc_west = tree.add("[cyan]dc-west[/cyan]")
    dc_west.add("[green]web-03[/green] (10.0.2.1)")
    dc_west.add("[red]db-01[/red] (10.0.2.2) - down")

    console.print(tree)


# ============================================================
# Markdown 渲染
# ============================================================

def demo_markdown():
    """Markdown 渲染"""
    console.print("\n[bold]=== Markdown ===[/bold]")

    md = """
# Incident Report

## Summary
The **api-gateway** service experienced a *502 error spike* at 14:30 UTC.

## Timeline
- 14:30 - Error rate exceeds 5%
- 14:35 - On-call engineer notified
- 14:45 - Root cause identified: database connection pool exhausted
- 15:00 - Fix deployed, error rate returns to normal

## Action Items
1. Increase connection pool size
2. Add connection pool monitoring
3. Update runbook
    """
    console.print(Markdown(md))


# ============================================================
# 实时更新
# ============================================================

def demo_live():
    """实时更新显示"""
    console.print("\n[bold]=== 实时更新 ===[/bold]")

    def generate_table(data):
        """生成实时更新的表格"""
        table = Table(box=box.SIMPLE)
        table.add_column("Service", style="cyan")
        table.add_column("Status")
        table.add_column("Requests/s", justify="right")

        for name, status, rps in data:
            color = "green" if status == "healthy" else "red"
            table.add_row(name, f"[{color}]{status}[/{color}]", str(rps))

        return table

    # 模拟实时数据
    data = [
        ("api-gateway", "healthy", 1250),
        ("auth-service", "healthy", 340),
        ("notification", "healthy", 85),
    ]

    with Live(generate_table(data), refresh_per_second=4) as live:
        for i in range(10):
            time.sleep(0.5)
            # 更新数据
            data[0] = ("api-gateway", "healthy", 1250 + i * 50)
            data[2] = ("notification", "healthy" if i % 3 != 0 else "degraded", 85 + i * 10)
            live.update(generate_table(data))


def main():
    """运行所有演示"""
    demo_basic_output()
    demo_table()
    demo_panel()
    demo_progress()
    demo_tree()
    demo_markdown()
    demo_live()


if __name__ == "__main__":
    main()
```

---

### 6. 交互式提示

```python
#!/usr/bin/env python3
"""
交互式 CLI 工具
SRE 场景：需要用户输入的运维工具
"""

import click
import getpass
from typing import Optional


# ============================================================
# click 的交互功能
# ============================================================

@click.group()
def cli():
    """Interactive SRE Tool."""
    pass


@cli.command()
@click.option("--name", prompt="Your name", help="Your name")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True,
              help="Password")
@click.option("--email", prompt="Email address", help="Email")
def register(name, password, email):
    """Register a new user with interactive prompts."""
    click.echo(f"Registered: {name} <{email}>")


@cli.command()
@click.option("--service", prompt="Service name", help="Service to restart")
@click.option("--replicas", prompt="Number of replicas", type=int, default=3)
@click.confirmation_prompt(prompt="Are you sure you want to restart?")
def restart(service, replicas):
    """Restart a service with confirmation."""
    click.echo(f"Restarting {service} with {replicas} replicas...")


@cli.command()
def choose_env():
    """Choose environment interactively."""
    env = click.prompt(
        "Select environment",
        type=click.Choice(["dev", "staging", "production"], case_sensitive=False),
        default="staging",
    )
    click.echo(f"Selected: {env}")


@cli.command()
@click.option("--verbose", "-v", count=True, help="Verbosity level")
def debug(verbose):
    """Debug command with verbosity levels."""
    levels = {0: "quiet", 1: "normal", 2: "verbose", 3: "debug"}
    level = levels.get(verbose, "debug")
    click.echo(f"Verbosity: {level} ({verbose})")


# ============================================================
# 使用 getpass 获取密码（不回显）
# ============================================================

@cli.command()
def login():
    """Login with password (no echo)."""
    username = click.prompt("Username")
    password = getpass.getpass("Password: ")
    click.echo(f"Logged in as {username}")


# ============================================================
# 选择列表
# ============================================================

@cli.command()
def select_service():
    """Select a service from a list."""
    services = ["api-gateway", "auth-service", "notification", "batch-worker"]

    click.echo("Available services:")
    for i, svc in enumerate(services, 1):
        click.echo(f"  {i}. {svc}")

    choice = click.prompt(
        "Select service number",
        type=click.IntRange(1, len(services)),
        default=1,
    )
    selected = services[choice - 1]
    click.echo(f"Selected: {selected}")


# ============================================================
# 多选
# ============================================================

@cli.command()
def multi_select():
    """Select multiple options."""
    options = {
        "h": "Health check",
        "l": "View logs",
        "r": "Restart",
        "s": "Scale",
    }

    click.echo("Available actions:")
    for key, desc in options.items():
        click.echo(f"  {key}: {desc}")

    choices = click.prompt(
        "Select actions (comma-separated)",
        default="h,l",
    )
    selected = [c.strip() for c in choices.split(",")]
    for choice in selected:
        if choice in options:
            click.echo(f"  -> {options[choice]}")
        else:
            click.secho(f"  -> Invalid: {choice}", fg="red")


if __name__ == "__main__":
    cli()
```

---

### 7. 打包分发

#### 7.1 pyproject.toml 配置

```python
#!/usr/bin/env python3
"""
Python 包打包分发
SRE 场景：将 CLI 工具打包为可安装的 Python 包
"""

# ============================================================
# pyproject.toml 示例
# ============================================================

PYPROJECT_TOML = """
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "sre-tool"
version = "1.0.0"
description = "SRE Operations Tool"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "SRE Team", email = "sre@example.com"},
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: System :: Systems Administration",
]
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "httpx>=0.24",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1",
]

[project.scripts]
sre-tool = "sre_tool.cli:main"
sre = "sre_tool.cli:main"

[project.urls]
Homepage = "https://github.com/example/sre-tool"
Documentation = "https://sre-tool.readthedocs.io"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.pytest.ini_options]
testpaths = ["tests"]
"""


# ============================================================
# 包目录结构
# ============================================================

PACKAGE_STRUCTURE = """
sre-tool/
├── pyproject.toml          # 项目配置（替代 setup.py）
├── README.md
├── LICENSE
├── src/
│   └── sre_tool/
│       ├── __init__.py     # 包初始化，版本信息
│       ├── cli.py          # CLI 入口点
│       ├── commands/       # 子命令模块
│       │   ├── __init__.py
│       │   ├── check.py    # 健康检查命令
│       │   ├── deploy.py   # 部署命令
│       │   ├── logs.py     # 日志命令
│       │   └── scale.py    # 扩缩容命令
│       ├── config.py       # 配置管理
│       ├── api/            # API 客户端
│       │   ├── __init__.py
│       │   ├── k8s.py      # Kubernetes API
│       │   └── prometheus.py
│       └── utils/          # 工具函数
│           ├── __init__.py
│           ├── output.py   # 输出格式化
│           └── validators.py
├── tests/
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_check.py
│   └── test_deploy.py
└── docs/
    └── usage.md
"""


# ============================================================
# 入口点代码
# ============================================================

CLI_ENTRY_POINT = '''#!/usr/bin/env python3
"""
SRE Tool CLI Entry Point

This module defines the main CLI application using click.
When installed via pip, the `sre-tool` command will execute this.
"""

import click
import sys
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="sre-tool")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--config", "-c", type=click.Path(), help="Config file path")
@click.pass_context
def main(ctx, verbose, config):
    """SRE Operations Tool - Manage production services."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")


@main.command()
@click.argument("services", nargs=-1, required=True)
@click.pass_context
def check(ctx, services):
    """Check service health."""
    for service in services:
        console.print(f"Checking {service}... [green]OK[/green]")


@main.command()
@click.argument("service")
@click.option("--image", "-i", required=True)
@click.option("--replicas", "-r", type=int, default=3)
@click.pass_context
def deploy(ctx, service, image, replicas):
    """Deploy a service."""
    console.print(f"Deploying {service} with {image} ({replicas} replicas)")


if __name__ == "__main__":
    main()
'''


def print_packaging_guide():
    """打印打包分发指南"""
    print("""
Python 包打包分发指南：

1. 创建项目结构
   mkdir -p sre-tool/src/sre_tool
   mkdir -p sre-tool/tests

2. 编写 pyproject.toml（见上方示例）

3. 安装开发模式
   cd sre-tool
   pip install -e ".[dev]"

4. 构建分发包
   pip install build
   python -m build
   # 生成 dist/sre_tool-1.0.0.tar.gz 和 dist/sre_tool-1.0.0-py3-none-any.whl

5. 上传到 PyPI（或内部仓库）
   pip install twine
   twine upload dist/*

6. 安装
   pip install sre-tool
   # 或从内部仓库
   pip install sre-tool --index-url https://pypi.example.com

entry_points 的作用：
- 在 [project.scripts] 中定义命令名和入口函数
- pip install 时自动生成可执行脚本
- 用户可以直接在命令行运行 sre-tool

SRE 最佳实践：
- 使用 pyproject.toml（而非 setup.py）
- 固定依赖版本范围（避免破坏性更新）
- 添加 --version 选项
- 支持 --config 指定配置文件
- 使用 rich 美化输出
- 编写单元测试
    """)


if __name__ == "__main__":
    print_packaging_guide()
```

---

### 8. SRE 实战：完整的 CLI 工具

```python
#!/usr/bin/env python3
"""
SRE 实战：完整的服务管理 CLI 工具
整合 click + rich + typer 的最佳实践
"""

import click
import json
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum

console = Console()


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    name: str
    namespace: str
    status: ServiceStatus
    replicas: str
    cpu_percent: float
    memory_percent: float
    uptime: str


def load_config(config_path: Optional[str] = None) -> dict:
    """加载配置文件"""
    path = Path(config_path or "~/.sre-tool.json").expanduser()
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"api_url": "https://kubernetes.default.svc"}


@click.group()
@click.version_option(version="1.0.0", prog_name="sre-tool")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--config", "-c", type=click.Path(), help="Config file")
@click.option("--output", "-o", type=click.Choice(["text", "json", "table"]),
              default="text", help="Output format")
@click.pass_context
def cli(ctx, verbose, config, output):
    """SRE Operations Tool"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["output"] = output
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.argument("services", nargs=-1)
@click.option("--namespace", "-n", default="default")
@click.option("--watch", "-w", is_flag=True, help="Watch mode (refresh every 5s)")
@click.pass_context
def status(ctx, services, namespace, watch):
    """Show service status."""
    # 模拟获取服务状态
    all_services = [
        ServiceInfo("api-gateway", namespace, ServiceStatus.HEALTHY, "3/3", 45.2, 62.1, "15d 3h"),
        ServiceInfo("auth-service", namespace, ServiceStatus.HEALTHY, "2/2", 38.5, 55.0, "15d 3h"),
        ServiceInfo("notification", namespace, ServiceStatus.DEGRADED, "1/3", 92.0, 88.5, "2d 1h"),
        ServiceInfo("batch-worker", namespace, ServiceStatus.UNHEALTHY, "0/1", 0.0, 0.0, "N/A"),
    ]

    if services:
        filtered = [s for s in all_services if s.name in services]
    else:
        filtered = all_services

    output = ctx.obj["output"]

    if output == "json":
        data = [
            {
                "name": s.name,
                "status": s.status.value,
                "replicas": s.replicas,
                "cpu": s.cpu_percent,
                "memory": s.memory_percent,
            }
            for s in filtered
        ]
        console.print_json(json.dumps(data))
        return

    # 表格输出
    table = Table(title=f"Service Status ({namespace})", box=box.ROUNDED)
    table.add_column("Service", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Replicas", justify="center")
    table.add_column("CPU %", justify="right")
    table.add_column("Memory %", justify="right")
    table.add_column("Uptime", justify="right")

    for s in filtered:
        if s.status == ServiceStatus.HEALTHY:
            status_text = f"[green]{s.status.value}[/green]"
        elif s.status == ServiceStatus.DEGRADED:
            status_text = f"[yellow]{s.status.value}[/yellow]"
        else:
            status_text = f"[red]{s.status.value}[/red]"

        table.add_row(
            s.name,
            status_text,
            s.replicas,
            f"{s.cpu_percent:.1f}%",
            f"{s.memory_percent:.1f}%",
            s.uptime,
        )

    console.print(table)

    # 摘要
    healthy = sum(1 for s in filtered if s.status == ServiceStatus.HEALTHY)
    total = len(filtered)
    console.print(f"\nTotal: {total}, Healthy: {healthy}, Issues: {total - healthy}")


@cli.command()
@click.argument("service")
@click.option("--image", "-i", required=True)
@click.option("--replicas", "-r", type=int, default=3)
@click.option("--env", "-e", type=click.Choice(["dev", "staging", "production"]),
              default="staging")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def deploy(ctx, service, image, replicas, env, dry_run):
    """Deploy a service."""
    console.print(f"\n[bold]Deploying {service}[/bold]")
    console.print(f"  Image:     {image}")
    console.print(f"  Replicas:  {replicas}")
    console.print(f"  Env:       {env}")

    if dry_run:
        console.print("\n[yellow][DRY RUN] No changes will be made[/yellow]")
        return

    if not click.confirm(f"\nDeploy to {env}?"):
        raise click.Abort()

    with Progress() as progress:
        task = progress.add_task(f"[cyan]Deploying to {env}...", total=100)
        for _ in range(100):
            progress.update(task, advance=1)
            time.sleep(0.03)

    console.print(f"\n[green]Deployed {service} successfully![/green]")


@cli.command()
@click.argument("service")
@click.option("--follow", "-f", is_flag=True)
@click.option("--tail", "-t", type=int, default=50)
@click.option("--level", "-l", type=click.Choice(["DEBUG", "INFO", "WARN", "ERROR"]))
@click.pass_context
def logs(ctx, service, follow, tail, level):
    """View service logs."""
    import random
    console.print(f"[bold]Logs for {service}[/bold] (last {tail} lines)\n")

    levels = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
    for i in range(min(tail, 30)):
        log_level = random.choice(levels)
        if level and log_level != level:
            continue
        line = f"[2026-05-03 10:{i:02d}:00] [{log_level}] Request {i} processed"
        if log_level == "ERROR":
            console.print(f"[red]{line}[/red]")
        elif log_level == "WARN":
            console.print(f"[yellow]{line}[/yellow]")
        else:
            console.print(line)


@cli.command()
@click.argument("service")
@click.option("--replicas", "-r", type=int, required=True)
@click.pass_context
def scale(ctx, service, replicas):
    """Scale a service."""
    if replicas == 0:
        console.print(f"[red bold]WARNING: This will stop {service}![/red bold]")
        if not click.confirm("Are you sure?"):
            raise click.Abort()

    console.print(f"Scaling {service} to {replicas} replicas...")
    console.print(f"[green]Scaled {service} to {replicas} replicas[/green]")


@cli.command()
@click.argument("query")
@click.option("--duration", "-d", default="1h", help="Time range")
@click.pass_context
def metrics(ctx, query, duration):
    """Query Prometheus metrics."""
    console.print(f"[bold]Query:[/bold] {query}")
    console.print(f"[bold]Range:[/bold] {duration}")

    # 模拟查询结果
    table = Table(box=box.SIMPLE)
    table.add_column("Time", style="dim")
    table.add_column("Value", justify="right")

    import random
    for i in range(10):
        table.add_row(f"10:{i:02d}:00", f"{random.uniform(10, 100):.2f}")

    console.print(table)


if __name__ == "__main__":
    cli()
```

---

## 💻 实战练习

### 练习 1：基础操作 -- 日志分析 CLI

```python
#!/usr/bin/env python3
"""
练习 1：日志分析 CLI 工具
要求：
1. 使用 click 构建 CLI
2. 支持解析 Nginx/Apache 日志
3. 输出统计信息（IP 排名、状态码分布、请求路径排名）
4. 支持 JSON 和表格两种输出格式
5. 使用 rich 美化输出
"""

import click
import re
import json
from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path

console = Console()

# Nginx 日志格式正则
NGINX_PATTERN = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d+) (?P<size>\d+)'
)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Log Analyzer - Analyze web server logs."""
    pass


@cli.command()
@click.argument("logfile", type=click.Path(exists=True))
@click.option("--top", "-t", type=int, default=10, help="Number of top entries to show")
@click.option("--format", "-f", "output_format", type=click.Choice(["text", "json"]),
              default="text")
def analyze(logfile, top, output_format):
    """Analyze a log file."""
    ips = Counter()
    statuses = Counter()
    paths = Counter()
    methods = Counter()
    total_lines = 0
    total_bytes = 0

    with open(logfile) as f:
        for line in f:
            match = NGINX_PATTERN.match(line)
            if match:
                total_lines += 1
                data = match.groupdict()
                ips[data["ip"]] += 1
                statuses[data["status"]] += 1
                paths[data["path"]] += 1
                methods[data["method"]] += 1
                total_bytes += int(data["size"])

    if output_format == "json":
        result = {
            "total_lines": total_lines,
            "total_bytes": total_bytes,
            "top_ips": ips.most_common(top),
            "status_codes": dict(statuses),
            "top_paths": paths.most_common(top),
            "methods": dict(methods),
        }
        console.print_json(json.dumps(result, indent=2))
        return

    # 表格输出
    console.print(Panel(f"[bold]Log Analysis: {logfile}[/bold]", border_style="cyan"))
    console.print(f"Total lines: {total_lines}, Total bytes: {total_bytes:,}\n")

    # IP 排名
    table = Table(title=f"Top {top} IPs", box=box.ROUNDED)
    table.add_column("IP", style="cyan")
    table.add_column("Requests", justify="right")
    table.add_column("Percentage", justify="right")
    for ip, count in ips.most_common(top):
        pct = count / total_lines * 100 if total_lines else 0
        table.add_row(ip, str(count), f"{pct:.1f}%")
    console.print(table)

    # 状态码分布
    table = Table(title="Status Codes", box=box.ROUNDED)
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Percentage", justify="right")
    for status, count in sorted(statuses.items()):
        pct = count / total_lines * 100 if total_lines else 0
        color = "green" if status.startswith("2") else "red" if status.startswith("5") else "yellow"
        table.add_row(f"[{color}]{status}[/{color}]", str(count), f"{pct:.1f}%")
    console.print(table)

    # 请求路径排名
    table = Table(title=f"Top {top} Paths", box=box.ROUNDED)
    table.add_column("Path", style="cyan")
    table.add_column("Requests", justify="right")
    for path, count in paths.most_common(top):
        table.add_row(path, str(count))
    console.print(table)


@cli.command()
@click.argument("logfile", type=click.Path(exists=True))
@click.option("--status", "-s", help="Filter by status code")
@click.option("--ip", "-i", help="Filter by IP")
@click.option("--path", "-p", help="Filter by path pattern")
def filter(logfile, status, ip, path):
    """Filter log entries."""
    with open(logfile) as f:
        for line in f:
            match = NGINX_PATTERN.match(line)
            if not match:
                continue
            data = match.groupdict()

            if status and not data["status"].startswith(status):
                continue
            if ip and data["ip"] != ip:
                continue
            if path and path not in data["path"]:
                continue

            if data["status"].startswith("5"):
                console.print(f"[red]{line.strip()}[/red]")
            elif data["status"].startswith("4"):
                console.print(f"[yellow]{line.strip()}[/yellow]")
            else:
                console.print(line.strip())


@cli.command()
@click.argument("logfile", type=click.Path(exists=True))
@click.option("--interval", "-i", type=int, default=60, help="Interval in seconds")
def timeline(logfile, interval):
    """Show request timeline."""
    from collections import defaultdict

    buckets = defaultdict(int)
    with open(logfile) as f:
        for line in f:
            match = NGINX_PATTERN.match(line)
            if match:
                time_str = match.group("time")
                # 简化处理：按分钟分桶
                minute = time_str.split(":")[1]
                buckets[minute] += 1

    table = Table(title="Request Timeline", box=box.ROUNDED)
    table.add_column("Minute", style="cyan")
    table.add_column("Requests", justify="right")
    table.add_column("Bar")

    max_count = max(buckets.values()) if buckets else 1
    for minute, count in sorted(buckets.items()):
        bar_len = int(count / max_count * 40)
        bar = "█" * bar_len
        table.add_row(f":{minute}", str(count), f"[green]{bar}[/green]")

    console.print(table)


if __name__ == "__main__":
    cli()
```

### 练习 2：进阶场景 -- 服务配置管理工具

```python
#!/usr/bin/env python3
"""
练习 2：服务配置管理 CLI
要求：
1. 使用 click 子命令组
2. 支持配置的 CRUD 操作
3. 支持配置版本历史和回滚
4. 使用 rich 表格展示
5. 支持 JSON 导入导出
"""

import click
import json
import sqlite3
from datetime import datetime
from rich.console import Console
from rich.table import Table
from pathlib import Path

console = Console()

# 简单的配置存储
CONFIG_DB = Path("~/.sre-config.db").expanduser()


def get_db():
    conn = sqlite3.connect(str(CONFIG_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            version INTEGER NOT NULL,
            author TEXT DEFAULT 'unknown',
            comment TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Service Configuration Manager."""
    pass


@cli.command()
@click.argument("service")
@click.argument("key")
@click.argument("value")
@click.option("--author", "-a", default="sre")
@click.option("--comment", "-c", default="")
def set(service, key, value, author, comment):
    """Set a configuration value."""
    conn = get_db()
    # 获取当前版本
    row = conn.execute(
        "SELECT MAX(version) as v FROM configs WHERE service = ? AND key = ?",
        (service, key),
    ).fetchone()
    new_version = (row["v"] or 0) + 1

    conn.execute(
        "INSERT INTO configs (service, key, value, version, author, comment) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (service, key, value, new_version, author, comment),
    )
    conn.commit()
    conn.close()
    console.print(f"[green]Set {service}.{key} = {value} (v{new_version})[/green]")


@cli.command()
@click.argument("service")
@click.option("--version", "-v", type=int, help="Specific version")
def get(service, version):
    """Get configuration for a service."""
    conn = get_db()
    if version:
        rows = conn.execute(
            "SELECT * FROM configs WHERE service = ? AND version = ?",
            (service, version),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM configs WHERE service = ? AND version = "
            "(SELECT MAX(version) FROM configs WHERE service = ?)",
            (service, service),
        ).fetchall()
    conn.close()

    if not rows:
        console.print(f"[yellow]No config found for {service}[/yellow]")
        return

    table = Table(title=f"Config: {service}", box=box.ROUNDED)
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_column("Version", justify="right")
    table.add_column("Author")
    table.add_column("Updated At")

    for row in rows:
        table.add_row(row["key"], row["value"], str(row["version"]),
                      row["author"], row["created_at"])
    console.print(table)


@cli.command()
@click.argument("service")
def history(service):
    """Show configuration change history."""
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT version, author, comment, created_at FROM configs "
        "WHERE service = ? ORDER BY version DESC LIMIT 20",
        (service,),
    ).fetchall()
    conn.close()

    table = Table(title=f"History: {service}", box=box.ROUNDED)
    table.add_column("Version", justify="right", style="cyan")
    table.add_column("Author")
    table.add_column("Comment")
    table.add_column("Date")

    for row in rows:
        table.add_row(str(row["version"]), row["author"], row["comment"], row["created_at"])
    console.print(table)


@cli.command()
@click.argument("service")
@click.argument("version", type=int)
@click.option("--author", "-a", default="sre")
def rollback(service, version, author):
    """Rollback to a specific version."""
    conn = get_db()
    rows = conn.execute(
        "SELECT key, value FROM configs WHERE service = ? AND version = ?",
        (service, version),
    ).fetchall()

    if not rows:
        console.print(f"[red]Version {version} not found[/red]")
        return

    # 获取当前最大版本
    max_ver = conn.execute(
        "SELECT MAX(version) as v FROM configs WHERE service = ?",
        (service,),
    ).fetchone()["v"]
    new_version = max_ver + 1

    for row in rows:
        conn.execute(
            "INSERT INTO configs (service, key, value, version, author, comment) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (service, row["key"], row["value"], new_version, author,
             f"Rollback to v{version}"),
        )
    conn.commit()
    conn.close()
    console.print(f"[green]Rolled back {service} to v{version} (new version: {new_version})[/green]")


@cli.command()
@click.argument("service")
@click.argument("output_file", type=click.Path())
def export(service, output_file):
    """Export config to JSON file."""
    conn = get_db()
    rows = conn.execute(
        "SELECT key, value FROM configs WHERE service = ? AND version = "
        "(SELECT MAX(version) FROM configs WHERE service = ?)",
        (service, service),
    ).fetchall()
    conn.close()

    config = {row["key"]: row["value"] for row in rows}
    with open(output_file, "w") as f:
        json.dump(config, f, indent=2)
    console.print(f"[green]Exported {len(config)} keys to {output_file}[/green]")


@cli.command()
@click.argument("service")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--author", "-a", default="sre")
def import_config(service, input_file, author):
    """Import config from JSON file."""
    with open(input_file) as f:
        config = json.load(f)

    conn = get_db()
    max_ver = conn.execute(
        "SELECT MAX(version) as v FROM configs WHERE service = ?",
        (service,),
    ).fetchone()["v"] or 0
    new_version = max_ver + 1

    for key, value in config.items():
        conn.execute(
            "INSERT INTO configs (service, key, value, version, author, comment) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (service, key, str(value), new_version, author, f"Imported from {input_file}"),
        )
    conn.commit()
    conn.close()
    console.print(f"[green]Imported {len(config)} keys for {service} (v{new_version})[/green]")


if __name__ == "__main__":
    cli()
```

### 练习 3：故障排查挑战 -- 改进 CLI 工具的用户体验

```python
#!/usr/bin/env python3
"""
练习 3：CLI 工具用户体验改进
挑战：以下 CLI 工具存在多个 UX 问题，请找出并修复

问题：
1. 没有进度反馈，用户不知道正在做什么
2. 错误信息不友好
3. 没有 --dry-run 选项
4. 没有确认提示（危险操作）
5. 输出格式单一
"""

# === 问题代码 ===

import sys
import json


def deploy_broken(args):
    """UX 很差的部署命令"""
    service = args[0]
    image = args[1]
    # 没有参数验证
    # 没有进度显示
    # 没有确认
    # 直接执行
    print(f"Deploying {service}...")
    # ... 部署逻辑 ...
    print("Done")


# === 修复后的代码 ===

import click
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

console = Console()


@click.command()
@click.argument("service")
@click.option("--image", "-i", required=True, help="Container image")
@click.option("--replicas", "-r", type=click.IntRange(1, 100), default=3)
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text")
def deploy_fixed(service, image, replicas, dry_run, force, output):
    """Deploy a service (improved UX)."""

    # 1. 显示部署计划
    plan = {
        "service": service,
        "image": image,
        "replicas": replicas,
    }

    if output == "json":
        console.print_json(json.dumps(plan))
    else:
        console.print(f"\n[bold]Deployment Plan[/bold]")
        console.print(f"  Service:  {service}")
        console.print(f"  Image:    {image}")
        console.print(f"  Replicas: {replicas}")

    # 2. dry-run 模式
    if dry_run:
        console.print("\n[yellow][DRY RUN] No changes will be made[/yellow]")
        return

    # 3. 确认提示
    if not force:
        if not click.confirm(f"\nDeploy {service} to production?"):
            console.print("[yellow]Aborted[/yellow]")
            raise click.Abort()

    # 4. 进度反馈
    with Progress() as progress:
        task = progress.add_task(f"[cyan]Deploying {service}...", total=100)
        for _ in range(100):
            progress.update(task, advance=1)
            import time
            time.sleep(0.02)

    # 5. 结果反馈
    console.print(f"\n[green]Successfully deployed {service}[/green]")
    console.print(f"  Image: {image}")
    console.print(f"  Replicas: {replicas}")


if __name__ == "__main__":
    deploy_fixed()
```

---

## 🎯 面试题精选

### 题目 1：argparse、click、typer 三个 CLI 框架如何选择？

**参考答案：**

| 维度 | argparse | click | typer |
|------|----------|-------|-------|
| 依赖 | 标准库 | 需安装 | 需安装 |
| 学习曲线 | 中等 | 低 | 最低 |
| 代码量 | 较多 | 中等 | 最少 |
| 子命令 | 手动配置 | group 装饰器 | 自动推导 |
| 类型验证 | 基础 | 丰富 | 最丰富（类型注解） |
| 彩色输出 | 无 | 内置 | 内置（rich） |
| 自动补全 | 需手动 | 内置 | 内置 |

选择建议：
- **简单脚本**：argparse（无需安装依赖）
- **专业工具**：click（功能全面，社区活跃）
- **快速开发**：typer（代码最少，类型安全）
- **新项目推荐**：typer + rich（开发效率最高）

### 题目 2：如何在 CLI 工具中实现 --dry-run 模式？

**参考答案：**

dry-run 模式让用户预览操作而不实际执行。实现方式：

1. 添加 `--dry-run` 选项：`@click.option("--dry-run", is_flag=True)`
2. 在执行逻辑前检查：`if dry_run: 显示计划并退出`
3. 用不同颜色标记 dry-run 输出：`click.secho("[DRY RUN]", fg="yellow")`

SRE 场景：部署、扩缩容、配置变更等危险操作都应该支持 dry-run。

### 题目 3：如何实现 CLI 工具的配置文件支持？

**参考答案：**

支持配置文件的层级覆盖机制：

1. **默认值**：代码中的默认参数
2. **配置文件**：`~/.tool.json` 或 `~/.config/tool/config.yaml`
3. **环境变量**：`TOOL_API_URL` 等
4. **命令行参数**：`--api-url`

优先级：命令行 > 环境变量 > 配置文件 > 默认值

实现方式：
```python
@click.option("--api-url",
              default=os.environ.get("TOOL_API_URL", config.get("api_url", "http://localhost")))
```

### 题目 4：entry_points 是什么？为什么需要它？

**参考答案：**

entry_points 是 Python 包的元数据，定义了包安装后可以执行的命令。

```toml
[project.scripts]
sre-tool = "sre_tool.cli:main"
```

这告诉 pip：安装这个包后，创建一个名为 `sre-tool` 的可执行文件，执行时调用 `sre_tool.cli` 模块的 `main` 函数。

好处：
1. 用户安装后可以直接运行 `sre-tool`，不需要知道 Python 模块路径
2. 自动处理 Python 路径和依赖
3. 支持 `pip install` 和 `pipx install`
4. 跨平台（自动生成 .exe 等）

### 题目 5：如何为 CLI 工具编写测试？

**参考答案：**

click 提供了内置的测试工具：

```python
from click.testing import CliRunner
from my_tool import cli

def test_check_command():
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "api-gateway", "--namespace", "default"])
    assert result.exit_code == 0
    assert "api-gateway" in result.output

def test_deploy_dry_run():
    runner = CliRunner()
    result = runner.invoke(cli, ["deploy", "api", "-i", "v1.0", "--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN" in result.output
```

测试要点：
1. 测试正常流程（exit_code == 0）
2. 测试错误输入（exit_code != 0）
3. 测试 --help 输出
4. 测试 --dry-run 模式
5. 使用 mock 隔离外部依赖

### 题目 6：如何处理 CLI 工具中的敏感信息（密码、Token）？

**参考答案：**

1. **环境变量**：`$SRE_TOOL_TOKEN`，不硬编码在代码中
2. **隐藏输入**：`@click.option("--password", prompt=True, hide_input=True)`
3. **配置文件权限**：配置文件设置 `chmod 600`
4. **密钥管理器**：集成 HashiCorp Vault、AWS Secrets Manager
5. **不记录日志**：敏感参数不输出到日志

```python
# 错误
click.echo(f"Token: {token}")  # 可能泄露到日志

# 正确
click.echo(f"Token: {'*' * len(token)}")  # 脱敏显示
```

### 题目 7：如何实现 CLI 工具的自动补全？

**参考答案：**

click 支持 shell 自动补全：

```bash
# Bash
eval "$(_SRE_TOOL_COMPLETE=bash_source sre-tool)"

# Zsh
eval "$(_SRE_TOOL_COMPLETE=zsh_source sre-tool)"

# Fish
eval (env _SRE_TOOL_COMPLETE=fish_source sre-tool)
```

可以添加到 `~/.bashrc` 或 `~/.zshrc` 中。

typer 内置支持自动补全，无需额外配置。

### 题目 8：如何用 pipx 分发 CLI 工具？

**参考答案：**

pipx 是专门用于安装 Python CLI 工具的工具，它为每个工具创建独立的虚拟环境，避免依赖冲突。

```bash
# 安装 pipx
pip install pipx

# 用 pipx 安装 CLI 工具
pipx install sre-tool

# 从 Git 仓库安装
pipx install git+https://github.com/example/sre-tool.git

# 升级
pipx upgrade sre-tool
```

SRE 推荐：将内部 CLI 工具发布到私有 PyPI 仓库，团队成员用 `pipx install sre-tool --index-url https://pypi.example.com` 安装。

### 题目 9：click 的 Context 对象有什么作用？

**参考答案：**

click.Context 是一个在命令执行期间传递的上下文对象，用于：

1. **传递共享数据**：`ctx.obj["verbose"]` 在子命令间共享标志
2. **获取父命令信息**：`ctx.parent` 访问父命令的上下文
3. **控制程序行为**：`ctx.exit()` 提前退出，`ctx.abort()` 中止操作
4. **访问配置**：存储全局配置

```python
@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config()

@cli.command()
@click.pass_context
def check(ctx):
    config = ctx.obj["config"]
    # 使用配置
```

### 题目 10：如何让 CLI 工具支持管道操作（stdin/stdout）？

**参考答案：**

支持管道是 Unix 哲学的核心。Python 实现：

```python
import sys

@click.command()
@click.argument("input_file", type=click.File("r"), default="-")
def process(input_file):
    """Process input from file or stdin."""
    for line in input_file:
        # 处理每一行
        result = line.strip().upper()
        click.echo(result)  # 输出到 stdout

# 使用方式：
# cat data.txt | sre-tool process
# sre-tool process data.txt
# sre-tool process < data.txt > output.txt
```

关键点：
1. `type=click.File("r")` 支持文件路径和 `-`（表示 stdin）
2. 输出到 stdout 以便管道下游使用
3. 日志和进度信息输出到 stderr：`click.echo("...", err=True)`

---

## 📚 深入阅读

### 官方文档

- [Python argparse 官方文档](https://docs.python.org/3/library/argparse.html)
- [click 官方文档](https://click.palletsprojects.com/)
- [typer 官方文档](https://typer.tiangolo.com/)
- [rich 官方文档](https://rich.readthedocs.io/)
- [Python packaging 官方指南](https://packaging.python.org/)

### 推荐书籍

- 《Building CLI Applications in Python》 -- Jodie Burchell
- 《Python Cookbook》 -- David Beazley -- 第14章

### 技术博客

- [Real Python: Python Command-Line Interfaces](https://realpython.com/python-command-line-interfaces/)
- [click vs argparse vs typer comparison](https://click.palletsprojects.com/en/8.x/why/)
- [Rich Documentation](https://rich.readthedocs.io/en/latest/)

---

## ✅ 自检清单

- [ ] 能用 argparse 构建带子命令的 CLI 工具
- [ ] 能用 click 构建专业的 CLI 工具（group + command）
- [ ] 能用 typer 基于类型注解快速构建 CLI
- [ ] 能用 rich 美化输出（表格、进度条、面板、树形结构）
- [ ] 能实现交互式提示（确认、密码、选择列表）
- [ ] 能实现 --dry-run、--force、--verbose 等标准选项
- [ ] 理解 pyproject.toml 的结构和 entry_points 的作用
- [ ] 能将 CLI 工具打包为可安装的 Python 包
- [ ] 能为 CLI 工具编写测试（click.testing.CliRunner）
- [ ] 能设计用户友好的 CLI 接口（帮助信息、错误提示、进度反馈）
