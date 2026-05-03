# Day 43: Python 环境搭建与开发规范

> 📅 日期：2026-05-03
> 📖 学习主题：Python 环境管理、开发规范与代码质量工具链
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 36-42 网络基础

## 🎯 学习目标

- 掌握 pyenv 多版本 Python 管理，能在生产环境中快速切换和隔离 Python 版本
- 理解 virtualenv / venv / Poetry 的适用场景与底层机制
- 熟练运用 PEP 8 规范和类型提示编写高质量 SRE 脚本
- 掌握 flake8 / mypy / black / isort / pre-commit 等代码质量工具的配置与集成
- 能搭建完整的 Python 项目脚手架，适用于 SRE 自动化工具开发

---

## 📖 核心知识点

### 1. Python 版本管理 — pyenv

#### 1.1 为什么 SRE 需要多版本 Python？

在 SRE 日常工作中，你会面对多种 Python 版本需求：

```
┌─────────────────────────────────────────────────────────────────┐
│                    SRE 的 Python 版本困境                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  系统自带 Python (CentOS 7)     → Python 2.7 / 3.6             │
│  监控 Agent (Prometheus exporter) → Python 3.8+                 │
│  自动化脚本 (Ansible playbook)   → Python 3.9+                  │
│  新项目 (FastAPI 微服务)         → Python 3.11+                 │
│  遗留运维脚本                    → Python 2.7 (不能动!)          │
│                                                                 │
│  问题：系统 Python 不能随便升级，会影响 yum/dnf 等系统工具        │
│  解决：pyenv 在用户空间管理多个 Python 版本                       │
└─────────────────────────────────────────────────────────────────┘
```

**关键原则：永远不要动系统自带的 Python！**

CentOS/RHEL 系统的 `yum` / `dnf` 依赖系统 Python，直接升级或替换会导致包管理器崩溃。pyenv 通过在用户目录（`~/.pyenv`）下编译安装 Python，完全隔离于系统环境。

#### 1.2 pyenv 工作原理

```
┌─────────────────────────────────────────────────────────────────┐
│                    pyenv 版本解析流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  用户执行: python script.py                                     │
│       │                                                         │
│       ▼                                                         │
│  Shell 检查 PATH                                                │
│       │                                                         │
│       ▼                                                         │
│  ~/.pyenv/shims/python  ← pyenv 注入的 shim 脚本                │
│       │                                                         │
│       ▼                                                         │
│  pyenv 版本解析 (按优先级):                                      │
│    1. PYENV_VERSION 环境变量                                     │
│    2. .python-version 文件 (当前目录向上搜索)                     │
│    3. ~/.pyenv/version 全局默认                                  │
│       │                                                         │
│       ▼                                                         │
│  ~/.pyenv/versions/3.11.7/bin/python  ← 实际执行的 Python        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

pyenv 的核心设计是 **shim 层**：它在 PATH 最前面插入 `~/.pyenv/shims/`，里面是一组代理脚本（python, pip, python3 等），这些 shim 会根据版本解析规则转发到对应版本的真正二进制文件。

#### 1.3 pyenv 安装与配置

```bash
# ============================================
# 1. 安装编译依赖 (CentOS/RHEL)
# ============================================
sudo yum groupinstall -y "Development Tools"
sudo yum install -y \
    gcc make patch gdbm-devel openssl-devel libffi-devel \
    sqlite-devel readline-devel zlib-devel bzip2-devel \
    xz-devel tk-devel

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev \
    libxmlsec1-dev libffi-dev liblzma-dev

# ============================================
# 2. 安装 pyenv (推荐用官方安装脚本)
# ============================================
curl https://pyenv.run | bash

# ============================================
# 3. 配置 Shell 环境 (添加到 ~/.bashrc 或 ~/.zshrc)
# ============================================
cat >> ~/.bashrc << 'EOF'
# pyenv 配置
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
EOF

source ~/.bashrc

# ============================================
# 4. 安装 Python 版本
# ============================================
# 查看可安装版本
pyenv install --list | grep -E "^  3\.(8|9|10|11|12)\." | tail -20

# 安装常用版本（SRE 推荐）
pyenv install 3.9.18    # 兼容 CentOS 7 遗留脚本
pyenv install 3.10.13   # 中间版本
pyenv install 3.11.7    # 生产推荐版本
pyenv install 3.12.1    # 最新稳定版

# ============================================
# 5. 设置版本
# ============================================
# 全局默认
pyenv global 3.11.7

# 当前目录 (会创建 .python-version 文件)
pyenv local 3.12.1

# 当前 Shell 会话
pyenv shell 3.10.13

# ============================================
# 6. 验证
# ============================================
pyenv versions        # 列出已安装版本
python --version      # 验证当前版本
which python          # 应该指向 ~/.pyenv/shims/python
```

#### 1.4 pyenv 常用命令速查

| 命令 | 作用 | SRE 场景 |
|------|------|---------|
| `pyenv install --list` | 列出所有可安装版本 | 确认可用版本 |
| `pyenv install 3.x.y` | 安装指定版本 | 部署新环境 |
| `pyenv versions` | 列出已安装版本 | 环境审计 |
| `pyenv version` | 显示当前激活版本 | 故障排查 |
| `pyenv global 3.x.y` | 设置全局默认版本 | 服务器初始化 |
| `pyenv local 3.x.y` | 设置目录级版本 | 项目隔离 |
| `pyenv shell 3.x.y` | 设置当前 Shell 版本 | 临时测试 |
| `pyenv uninstall 3.x.y` | 卸载版本 | 清理磁盘空间 |
| `pyenv rehash` | 重建 shim 脚本 | 安装新包后 |

#### 1.5 SRE 实战：批量服务器 Python 版本审计

```python
#!/usr/bin/env python3
"""
SRE 场景：检查服务器集群的 Python 版本一致性
用于确保所有服务器的 Python 环境符合基线要求
"""
import subprocess
import json
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PythonVersionInfo:
    """Python 版本信息"""
    host: str
    version: Optional[str]
    path: Optional[str]
    pyenv_installed: bool
    error: Optional[str] = None


def check_python_version(host: str, timeout: int = 10) -> PythonVersionInfo:
    """
    检查远程主机的 Python 版本信息

    Args:
        host: 主机名或 IP
        timeout: SSH 超时时间（秒）

    Returns:
        PythonVersionInfo: 版本信息对象
    """
    try:
        # 获取 Python 版本
        result = subprocess.run(
            ["ssh", "-o", f"ConnectTimeout={timeout}", host,
             "python3 --version 2>/dev/null && which python3"],
            capture_output=True, text=True, timeout=timeout + 5
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            version = lines[0] if lines else None
            path = lines[1] if len(lines) > 1 else None
        else:
            version = None
            path = None

        # 检查 pyenv 是否安装
        pyenv_result = subprocess.run(
            ["ssh", "-o", f"ConnectTimeout={timeout}", host,
             "command -v pyenv >/dev/null 2>&1 && echo yes || echo no"],
            capture_output=True, text=True, timeout=timeout + 5
        )
        pyenv_installed = pyenv_result.stdout.strip() == "yes"

        return PythonVersionInfo(
            host=host,
            version=version,
            path=path,
            pyenv_installed=pyenv_installed
        )
    except subprocess.TimeoutExpired:
        return PythonVersionInfo(
            host=host, version=None, path=None,
            pyenv_installed=False, error="SSH 连接超时"
        )
    except Exception as e:
        return PythonVersionInfo(
            host=host, version=None, path=None,
            pyenv_installed=False, error=str(e)
        )


def audit_cluster(hosts: List[str], baseline: str = "Python 3.11.7") -> Dict:
    """
    审计集群 Python 版本一致性

    Args:
        hosts: 主机列表
        baseline: 基线版本

    Returns:
        审计结果字典
    """
    results = []
    compliant = 0
    non_compliant = 0
    unreachable = 0

    for host in hosts:
        info = check_python_version(host)
        results.append(info)

        if info.error:
            unreachable += 1
        elif info.version and baseline in info.version:
            compliant += 1
        else:
            non_compliant += 1

    return {
        "baseline": baseline,
        "total_hosts": len(hosts),
        "compliant": compliant,
        "non_compliant": non_compliant,
        "unreachable": unreachable,
        "details": [
            {
                "host": r.host,
                "version": r.version,
                "path": r.path,
                "pyenv": r.pyenv_installed,
                "error": r.error,
                "status": "OK" if (r.version and baseline in r.version)
                         else ("ERROR" if r.error else "MISMATCH")
            }
            for r in results
        ]
    }


if __name__ == "__main__":
    # 示例用法
    test_hosts = ["web-01", "web-02", "api-01", "api-02", "worker-01"]
    report = audit_cluster(test_hosts)
    print(json.dumps(report, indent=2, ensure_ascii=False))
```

---

### 2. 虚拟环境管理

#### 2.1 为什么需要虚拟环境？

```
┌─────────────────────────────────────────────────────────────────┐
│                    依赖冲突问题                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  项目 A 需要: requests==2.28.0                                  │
│  项目 B 需要: requests==2.31.0                                  │
│                                                                 │
│  如果都装在系统 Python 中:                                       │
│    pip install requests==2.28.0  → 装好了                       │
│    pip install requests==2.31.0  → 覆盖了! 项目 A 可能崩溃       │
│                                                                 │
│  虚拟环境解决方案:                                               │
│    项目 A: .venv-A/ → requests==2.28.0                         │
│    项目 B: .venv-B/ → requests==2.31.0                         │
│    互不干扰 ✅                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 venv vs virtualenv vs Poetry 对比

| 特性 | venv (标准库) | virtualenv | Poetry |
|------|--------------|------------|--------|
| 安装 | 内置，无需安装 | `pip install virtualenv` | 独立安装 |
| 速度 | 较快 | 更快（有缓存） | 依赖解析较慢 |
| Python 版本管理 | 不支持 | 支持指定解释器 | 集成 pyenv |
| 依赖锁定 | 不支持（需 pip-tools） | 不支持 | 内置 poetry.lock |
| 构建系统 | 不支持 | 不支持 | 内置 pyproject.toml |
| SRE 推荐场景 | 简单脚本 | 需要多 Python 版本 | 正式项目/CLI 工具 |

#### 2.3 venv 标准库用法

```bash
# ============================================
# 创建虚拟环境
# ============================================
# 在项目目录下创建
python3 -m venv .venv

# 指定 Python 版本
python3.11 -m venv .venv

# 不包含系统包（完全隔离）
python3 -m venv --without-pip .venv  # 不推荐，通常需要 pip

# ============================================
# 激活/停用
# ============================================
# Linux/macOS
source .venv/bin/activate

# 停用
deactivate

# ============================================
# 验证环境
# ============================================
which python    # 应该指向 .venv/bin/python
python --version
pip list        # 应该只有基础包

# ============================================
# 依赖管理
# ============================================
# 安装依赖
pip install requests prometheus-client

# 导出依赖列表
pip freeze > requirements.txt

# 从文件安装
pip install -r requirements.txt
```

#### 2.4 venv 底层机制

```
┌─────────────────────────────────────────────────────────────────┐
│                    venv 目录结构                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  .venv/                                                         │
│  ├── bin/ (Linux/macOS) 或 Scripts/ (Windows)                   │
│  │   ├── activate          ← Shell 激活脚本 (修改 PATH)         │
│  │   ├── activate.csh      ← csh 激活脚本                      │
│  │   ├── activate.fish     ← fish 激活脚本                      │
│  │   ├── python            ← 指向系统 Python 的符号链接          │
│  │   ├── python3           ← 同上                              │
│  │   ├── pip               ← 虚拟环境专属 pip                   │
│  │   └── pip3              ← 同上                              │
│  ├── include/               ← C 头文件（编译扩展用）             │
│  ├── lib/                   ← site-packages 所在目录            │
│  │   └── python3.11/                                              │
│  │       └── site-packages/ ← 所有安装的包都在这里               │
│  └── pyvenv.cfg             ← 虚拟环境配置文件                   │
│                                                                 │
│  pyvenv.cfg 内容:                                               │
│  home = /home/user/.pyenv/versions/3.11.7/bin                   │
│  include-system-site-packages = false                           │
│  version = 3.11.7                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**激活脚本的核心作用**：修改 `PATH` 环境变量，将 `.venv/bin/` 放在最前面，使得 `python` 和 `pip` 命令优先指向虚拟环境内的版本。

#### 2.5 Poetry 现代化依赖管理

```bash
# ============================================
# 安装 Poetry
# ============================================
curl -sSL https://install.python-poetry.org | python3 -

# 验证安装
poetry --version

# 配置：在项目目录内创建虚拟环境
poetry config virtualenvs.in-project true

# ============================================
# 初始化项目
# ============================================
mkdir sre-toolkit && cd sre-toolkit
poetry init

# 或者从头创建项目
poetry new sre-toolkit

# ============================================
# 依赖管理
# ============================================
# 添加依赖
poetry add requests
poetry add prometheus-client
poetry add pyyaml

# 添加开发依赖
poetry add --group dev pytest mypy flake8 black

# 安装所有依赖
poetry install

# 更新依赖
poetry update

# 查看依赖树
poetry show --tree

# 导出 requirements.txt（给不使用 Poetry 的环境）
poetry export -f requirements.txt --output requirements.txt
```

**pyproject.toml 示例（SRE 工具项目）：**

```toml
[tool.poetry]
name = "sre-toolkit"
version = "0.1.0"
description = "SRE 自动化运维工具集"
authors = ["SRE Team <sre@example.com>"]
readme = "README.md"
packages = [{include = "sre_toolkit"}]

[tool.poetry.dependencies]
python = "^3.9"
requests = "^2.31.0"
pyyaml = "^6.0.1"
prometheus-client = "^0.19.0"
click = "^8.1.7"
structlog = "^23.2.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-cov = "^4.1.0"
mypy = "^1.7.0"
flake8 = "^6.1.0"
black = "^23.11.0"
isort = "^5.12.0"
pre-commit = "^3.6.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 88

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

#### 2.6 pip 离线部署（生产环境无网络场景）

```bash
# ============================================
# 在有网络的机器上下载依赖包
# ============================================
mkdir -p /tmp/offline-packages

# 下载 requirements.txt 中的所有包及其依赖
pip download \
    -d /tmp/offline-packages \
    -r requirements.txt \
    --platform manylinux2014_x86_64 \
    --python-version 3.11 \
    --only-binary=:all:

# 打包传输到目标机器
tar czf sre-deps.tar.gz -C /tmp/offline-packages .
scp sre-deps.tar.gz target-server:/tmp/

# ============================================
# 在无网络的目标机器上安装
# ============================================
tar xzf /tmp/sre-deps.tar.gz -C /tmp/offline-packages
pip install \
    --no-index \
    --find-links /tmp/offline-packages \
    -r requirements.txt
```

#### 2.7 SRE 实战：虚拟环境自动化部署脚本

```bash
#!/bin/bash
# deploy_venv.sh — SRE 自动化部署虚拟环境
# 用途：在目标服务器上创建标准化 Python 环境

set -euo pipefail

# 配置
PYTHON_VERSION="3.11.7"
VENV_DIR="/opt/sre-tools/.venv"
REQUIREMENTS_FILE="/opt/sre-tools/requirements.txt"
LOG_FILE="/var/log/sre-venv-deploy.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

check_prerequisites() {
    log "检查前置条件..."

    # 检查 pyenv
    if ! command -v pyenv &>/dev/null; then
        log "ERROR: pyenv 未安装"
        exit 1
    fi

    # 检查目标 Python 版本
    if ! pyenv versions --bare | grep -q "^${PYTHON_VERSION}$"; then
        log "安装 Python ${PYTHON_VERSION}..."
        pyenv install "$PYTHON_VERSION"
    fi

    log "前置条件检查通过"
}

create_venv() {
    log "创建虚拟环境: ${VENV_DIR}"

    # 如果已存在，备份后重建
    if [ -d "$VENV_DIR" ]; then
        BACKUP="${VENV_DIR}.bak.$(date +%s)"
        log "备份现有环境到: ${BACKUP}"
        mv "$VENV_DIR" "$BACKUP"
    fi

    # 使用指定版本创建虚拟环境
    PYENV_VERSION="$PYTHON_VERSION" python3 -m venv "$VENV_DIR"

    # 升级 pip
    "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel

    log "虚拟环境创建完成"
}

install_dependencies() {
    log "安装依赖..."

    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        log "ERROR: 依赖文件不存在: ${REQUIREMENTS_FILE}"
        exit 1
    fi

    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE" \
        --no-cache-dir \
        --timeout 120

    log "依赖安装完成"
}

verify() {
    log "验证环境..."

    # 验证 Python 版本
    ACTUAL_VERSION=$("$VENV_DIR/bin/python" --version)
    log "Python 版本: ${ACTUAL_VERSION}"

    # 验证关键包
    for pkg in requests pyyaml prometheus_client; do
        if "$VENV_DIR/bin/python" -c "import $pkg" 2>/dev/null; then
            log "  OK: ${pkg}"
        else
            log "  FAIL: ${pkg} 导入失败"
            return 1
        fi
    done

    log "环境验证通过"
}

main() {
    log "========== 开始部署 SRE Python 环境 =========="
    check_prerequisites
    create_venv
    install_dependencies
    verify
    log "========== 部署完成 =========="
}

main "$@"
```

---

### 3. PEP 8 编码规范

#### 3.1 为什么 SRE 脚本也需要遵守 PEP 8？

SRE 脚本往往需要多人维护。凌晨 3 点被 PagerDuty 叫醒后，你需要在 5 分钟内读懂一段脚本来定位问题。规范的代码风格能显著降低认知负担。

```
┌─────────────────────────────────────────────────────────────────┐
│                    PEP 8 核心规则速查                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  缩进        4 个空格，不用 Tab                                  │
│  行宽        79 字符（代码），72 字符（文档字符串/注释）           │
│  命名        snake_case (变量/函数), PascalCase (类),            │
│              UPPER_SNAKE (常量)                                  │
│  空行        顶层函数/类之间: 2 个空行                           │
│              类内方法之间: 1 个空行                               │
│  导入        每行一个导入，分组排列                               │
│  空格        运算符两侧、逗号后、冒号后（非切片）                 │
│  注释        与代码保持同步，解释 why 而非 what                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 命名规范详解

```python
# ============================================
# 变量命名 — snake_case
# ============================================
# 正确
host_name = "web-01"
retry_count = 3
is_healthy = True
max_timeout = 30
cpu_usage_percent = 85.5

# 错误
hostName = "web-01"       # 驼峰命名，不符合 Python 惯例
HostName = "web-01"       # 大驼峰，应该是类名
MAX_TIMEOUT = 30          # 全大写，应该是常量
x = 30                    # 无意义的变量名

# ============================================
# 常量命名 — UPPER_SNAKE_CASE
# ============================================
DEFAULT_TIMEOUT = 30
MAX_RETRY_COUNT = 5
HEALTH_CHECK_INTERVAL = 10
PROMETHEUS_PORT = 9090

# ============================================
# 函数命名 — snake_case，动词开头
# ============================================
def check_health(host: str) -> bool: ...
def get_cpu_usage(hostname: str) -> float: ...
def send_alert(message: str, severity: str) -> None: ...
def is_port_open(host: str, port: int) -> bool: ...

# 避免
def health(host): ...       # 缺少动词
def checkHost(host): ...    # 驼峰命名

# ============================================
# 类命名 — PascalCase
# ============================================
class HealthChecker: ...
class MetricsCollector: ...
class ServiceDiscovery: ...
class AlertManager: ...

# ============================================
# 模块/包命名 — snake_case (全小写)
# ============================================
# 文件名: health_checker.py, metrics_collector.py
# 包名:   sre_toolkit/health/, sre_toolkit/metrics/
```

#### 3.3 导入规范

```python
# ============================================
# 导入顺序 (PEP 8 + isort 标准)
# ============================================

# 1. 标准库导入
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 2. 相关第三方库导入
import requests
import yaml
from prometheus_client import Counter, Gauge, start_http_server

# 3. 本地应用/库导入
from sre_toolkit.health import HealthChecker
from sre_toolkit.metrics import MetricsCollector
from sre_toolkit.utils.config import load_config

# ============================================
# 导入最佳实践
# ============================================

# 每行一个导入
import json
import os
import sys

# 使用 from 导入具体名称
from pathlib import Path
from typing import Dict, List

# 避免通配符导入 (污染命名空间)
# from os import *   # 不要这样做

# 给长模块名起别名 (约定俗成)
import numpy as np
import pandas as pd
import prometheus_client as prom
```

#### 3.4 代码格式化示例

```python
# ============================================
# 正确的格式
# ============================================

def check_service_health(
    host: str,
    port: int = 8080,
    timeout: float = 5.0,
    retries: int = 3,
    path: str = "/health",
) -> Dict[str, any]:
    """
    检查服务健康状态。

    Args:
        host: 目标主机名或 IP
        port: 服务端口号
        timeout: 请求超时时间（秒）
        retries: 重试次数
        path: 健康检查路径

    Returns:
        包含健康状态的字典

    Raises:
        ConnectionError: 无法连接到目标服务
    """
    url = f"http://{host}:{port}{path}"

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            return {
                "host": host,
                "port": port,
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "attempt": attempt,
            }
        except requests.RequestException as e:
            if attempt == retries:
                return {
                    "host": host,
                    "port": port,
                    "status": "unreachable",
                    "error": str(e),
                    "attempt": attempt,
                }
            time.sleep(1 * attempt)  # 指数退避

    return {"host": host, "status": "unknown"}
```

---

### 4. 类型提示（Type Hints）

#### 4.1 为什么 SRE 脚本需要类型提示？

```python
# ============================================
# 没有类型提示 — 调用者需要读源码才能理解参数
# ============================================
def process_alert(data, config, threshold):
    # data 是什么？dict? list? str?
    # config 是什么？路径？配置对象？
    # threshold 是什么？int? float? 百分比？
    ...

# ============================================
# 有类型提示 — 一目了然
# ============================================
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AlertConfig:
    """告警配置"""
    webhook_url: str
    channels: List[str]
    severity_levels: Dict[str, int]


@dataclass
class AlertData:
    """告警数据"""
    alertname: str
    severity: str
    instance: str
    description: str
    timestamp: float
    labels: Dict[str, str]
    annotations: Dict[str, str]


def process_alert(
    data: AlertData,
    config: AlertConfig,
    threshold: float = 0.8,
) -> Optional[str]:
    """
    处理告警，决定是否发送通知。

    Args:
        data: 告警数据对象
        config: 告警配置
        threshold: 告警阈值（0.0-1.0），超过此值才发送

    Returns:
        发送结果消息，或 None 表示未达到阈值
    """
    severity_level = config.severity_levels.get(data.severity, 0)
    max_level = max(config.severity_levels.values())

    if severity_level / max_level < threshold:
        return None

    message = f"[{data.severity}] {data.alertname}: {data.description}"
    return f"Alert sent: {message}"
```

#### 4.2 常用类型提示语法

```python
from typing import (
    Any, Dict, List, Optional, Tuple, Union,
    Callable, Iterator, Generator, TypeVar, Generic,
    Protocol, Literal
)
from collections.abc import Sequence, Mapping

# ============================================
# 基础类型
# ============================================
host: str = "web-01"
port: int = 8080
timeout: float = 5.0
is_healthy: bool = True

# ============================================
# 容器类型
# ============================================
hosts: List[str] = ["web-01", "web-02"]
ports: Dict[str, int] = {"http": 80, "https": 443}
tags: Tuple[str, ...] = ("production", "us-east-1")
unique_ips: set[str] = {"10.0.0.1", "10.0.0.2"}  # Python 3.9+

# ============================================
# Optional — 可能为 None
# ============================================
def get_host_ip(hostname: str) -> Optional[str]:
    """解析主机名，失败返回 None"""
    import socket
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None

# ============================================
# Union — 多种类型
# ============================================
def parse_config(source: Union[str, Path, dict]) -> dict:
    """从文件路径或字典加载配置"""
    if isinstance(source, dict):
        return source
    path = Path(source) if isinstance(source, str) else source
    return yaml.safe_load(path.read_text())

# Python 3.10+ 可以用 | 语法
def parse_config_v2(source: str | Path | dict) -> dict: ...

# ============================================
# Callable — 函数类型
# ============================================
HealthCheckFunc = Callable[[str, int], bool]

def run_checks(
    hosts: List[str],
    check_fn: HealthCheckFunc,
) -> Dict[str, bool]:
    """对每个主机执行健康检查"""
    return {host: check_fn(host, 8080) for host in hosts}

# ============================================
# Literal — 字面量类型
# ============================================
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

def set_log_level(level: LogLevel) -> None:
    logging.getLogger().setLevel(level)

# ============================================
# Protocol — 结构化子类型
# ============================================
class SupportsHealthCheck(Protocol):
    """支持健康检查的协议"""
    def check(self) -> bool: ...
    @property
    def name(self) -> str: ...

class HTTPHealthCheck:
    def __init__(self, url: str):
        self._url = url
        self.name = f"HTTP({url})"

    def check(self) -> bool:
        try:
            return requests.get(self._url, timeout=5).status_code == 200
        except Exception:
            return False

class TCPHealthCheck:
    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port
        self.name = f"TCP({host}:{port})"

    def check(self) -> bool:
        import socket
        try:
            with socket.create_connection((self._host, self._port), timeout=5):
                return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False

def run_health_check(checker: SupportsHealthCheck) -> None:
    """只要实现了 check() 和 name，就能传入"""
    status = "PASS" if checker.check() else "FAIL"
    print(f"[{status}] {checker.name}")
```

#### 4.3 dataclass — SRE 数据模型

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class ServerInfo:
    """服务器信息 — SRE CMDB 数据模型"""
    hostname: str
    ip_address: str
    environment: str  # production, staging, development
    region: str
    cpu_cores: int
    memory_gb: float
    disk_gb: float
    os_version: str
    python_version: str
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    services: List[str] = field(default_factory=list)
    is_monitored: bool = True

    def __post_init__(self) -> None:
        """初始化后验证"""
        if self.environment not in ("production", "staging", "development"):
            raise ValueError(f"Invalid environment: {self.environment}")
        if self.cpu_cores <= 0:
            raise ValueError(f"Invalid cpu_cores: {self.cpu_cores}")

    @property
    def full_name(self) -> str:
        return f"{self.hostname}.{self.environment}.{self.region}"

    def add_service(self, service_name: str) -> None:
        """添加服务"""
        if service_name not in self.services:
            self.services.append(service_name)

    def is_production(self) -> bool:
        return self.environment == "production"


# 使用示例
server = ServerInfo(
    hostname="web-01",
    ip_address="10.0.1.100",
    environment="production",
    region="us-east-1",
    cpu_cores=8,
    memory_gb=32.0,
    disk_gb=500.0,
    os_version="Ubuntu 22.04",
    python_version="3.11.7",
    tags={"team": "platform", "cost-center": "infra"},
    services=["nginx", "python-api"],
)

print(server.full_name)        # web-01.production.us-east-1
print(server.is_production())  # True
```

---

### 5. 代码质量工具链

#### 5.1 工具链全景图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python 代码质量工具链                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  编辑器/IDE                                                    │
│    │                                                           │
│    ▼                                                           │
│  black (格式化) ──→ isort (导入排序) ──→ 写入文件               │
│    │                                                           │
│    ▼                                                           │
│  flake8 (Lint) ──→ 发现代码风格和潜在问题                      │
│    │                                                           │
│    ▼                                                           │
│  mypy (类型检查) ──→ 静态类型分析                               │
│    │                                                           │
│    ▼                                                           │
│  pytest (测试) ──→ 运行单元测试 + 覆盖率                       │
│    │                                                           │
│    ▼                                                           │
│  pre-commit (Git Hook) ──→ 提交前自动检查                      │
│    │                                                           │
│    ▼                                                           │
│  CI/CD Pipeline ──→ 最终质量门禁                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.2 flake8 — Lint 工具

```bash
# 安装
pip install flake8

# 基础使用
flake8 script.py

# 指定最大行宽
flake8 --max-line-length=88 script.py

# 忽略特定规则
flake8 --ignore=E501,W503 script.py

# 排除目录
flake8 --exclude=.venv,__pycache__,migrations
```

**flake8 配置文件 (.flake8)：**

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude =
    .git,
    .venv,
    __pycache__,
    build,
    dist,
    *.egg-info,
    migrations
per-file-ignores =
    __init__.py:F401
    tests/*:E501
```

**常见错误代码：**

| 代码 | 含义 | 修复方法 |
|------|------|---------|
| E111 | 缩进不是 4 的倍数 | 用 4 空格缩进 |
| E302 | 期望 2 个空行 | 在顶层定义间加空行 |
| E501 | 行太长 (>79 字符) | 拆分或用括号换行 |
| W291 | 行尾有空格 | 删除尾部空格 |
| W292 | 文件末尾无换行符 | 添加换行符 |
| F401 | 导入了但未使用 | 删除或使用 |
| F811 | 重复定义 | 检查变量名冲突 |

#### 5.3 mypy — 静态类型检查

```bash
# 安装
pip install mypy

# 基础使用
mypy script.py

# 严格模式
mypy --strict script.py

# 指定 Python 版本
mypy --python-version 3.9 script.py
```

**mypy 配置文件 (mypy.ini)：**

```ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
show_error_codes = True

# 对第三方库宽松处理
[mypy-requests.*]
ignore_missing_imports = True

[mypy-yaml.*]
ignore_missing_imports = True
```

```python
# mypy 检查示例
from typing import List, Optional

# 正确
def get_hosts(environment: str) -> List[str]:
    if environment == "production":
        return ["web-01", "web-02"]
    return ["staging-01"]

# mypy 报错: Missing return statement
def get_port(service: str) -> int:
    if service == "http":
        return 80
    # 缺少 else 分支的 return

# mypy 报错: Incompatible return type
def get_timeout() -> float:
    return "5.0"  # 返回了 str，声明了 float
```

#### 5.4 black — 自动格式化

```bash
# 安装
pip install black

# 格式化单个文件
black script.py

# 格式化目录
black src/

# 检查模式（不修改，只报告）
black --check src/

# 差异模式（显示会做的修改）
black --diff src/

# 指定行宽
black --line-length 88 src/
```

#### 5.5 isort — 导入排序

```bash
# 安装
pip install isort

# 排序
isort script.py

# 检查模式
isort --check-only --diff script.py

# 配合 black 使用
isort --profile black script.py
```

#### 5.6 pre-commit — Git Hook 自动化

```yaml
# .pre-commit-config.yaml
repos:
  # 代码格式化
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  # 导入排序
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  # Lint 检查
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203"]

  # 类型检查
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]

  # 通用检查
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: check-merge-conflict
      - id: debug-statements

  # 安全检查
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
        additional_dependencies: ["bandit[toml]"]
```

```bash
# 安装 pre-commit
pip install pre-commit

# 安装 Git hooks
pre-commit install

# 手动运行所有检查
pre-commit run --all-files

# 跳过某个 hook (紧急情况)
SKIP=mypy git commit -m "hotfix: urgent fix"

# 更新 hooks 版本
pre-commit autoupdate
```

---

### 6. SRE 实战：项目脚手架

#### 6.1 标准 SRE 工具项目结构

```
sre-toolkit/
├── .git/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── .pre-commit-config.yaml     # pre-commit 配置
├── .flake8                     # flake8 配置
├── mypy.ini                    # mypy 配置
├── pyproject.toml              # 项目配置 + Poetry
├── poetry.lock                 # 依赖锁定
├── README.md
├── Makefile                    # 常用命令快捷方式
├── Dockerfile                  # 容器化
├── src/
│   └── sre_toolkit/
│       ├── __init__.py
│       ├── __main__.py         # CLI 入口
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── health.py       # 健康检查命令
│       │   ├── deploy.py       # 部署命令
│       │   └── monitor.py      # 监控命令
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py       # 配置管理
│       │   ├── logging.py      # 日志配置
│       │   └── exceptions.py   # 自定义异常
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── cpu.py          # CPU 指标采集
│       │   ├── memory.py       # 内存指标采集
│       │   └── disk.py         # 磁盘指标采集
│       └── utils/
│           ├── __init__.py
│           ├── http.py         # HTTP 工具
│           └── retry.py        # 重试装饰器
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures
│   ├── test_health.py
│   ├── test_collectors/
│   │   ├── test_cpu.py
│   │   └── test_memory.py
│   └── test_utils/
│       └── test_retry.py
├── config/
│   ├── default.yaml            # 默认配置
│   ├── production.yaml         # 生产环境配置
│   └── staging.yaml            # 预发布环境配置
└── scripts/
    ├── setup.sh                # 环境初始化
    └── deploy.sh               # 部署脚本
```

#### 6.2 Makefile — 常用命令集合

```makefile
# Makefile — SRE 工具项目常用命令

.PHONY: help install lint format typecheck test coverage clean

help:  ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装依赖
	poetry install

lint:  ## 运行 lint 检查
	poetry run flake8 src/ tests/
	poetry run isort --check-only --diff src/ tests/
	poetry run black --check src/ tests/

format:  ## 自动格式化代码
	poetry run isort --profile black src/ tests/
	poetry run black src/ tests/

typecheck:  ## 运行类型检查
	poetry run mypy src/

test:  ## 运行测试
	poetry run pytest tests/ -v

coverage:  ## 运行测试并生成覆盖率报告
	poetry run pytest tests/ -v --cov=sre_toolkit --cov-report=html --cov-report=term

pre-commit:  ## 运行 pre-commit 检查
	poetry run pre-commit run --all-files

clean:  ## 清理临时文件
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .mypy_cache .pytest_cache htmlcov .coverage

docker-build:  ## 构建 Docker 镜像
	docker build -t sre-toolkit:latest .
```

#### 6.3 CI/CD 配置 (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run lint
        run: make lint

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run mypy
        run: make typecheck

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Run tests
        run: make coverage
```

---

## 💻 实战练习

### 练习 1：基础操作 — 搭建 Python 开发环境

**目标**：在本地搭建完整的 Python SRE 开发环境

**步骤**：

```bash
# 1. 安装 pyenv（如果未安装）
curl https://pyenv.run | bash

# 2. 配置 Shell
# 将以下内容添加到 ~/.bashrc 或 ~/.zshrc:
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# 3. 安装 Python 3.11.7
pyenv install 3.11.7
pyenv global 3.11.7

# 4. 创建项目
mkdir sre-practice && cd sre-practice

# 5. 用 Poetry 初始化
poetry init --name sre-practice --description "SRE Practice Project"

# 6. 添加依赖
poetry add requests pyyaml prometheus-client
poetry add --group dev pytest mypy flake8 black isort

# 7. 创建项目结构
mkdir -p src/sre_practice tests config

# 8. 配置 pre-commit
poetry add --group dev pre-commit
poetry run pre-commit install
```

**验证标准**：
- [ ] `pyenv versions` 显示 3.11.7
- [ ] `poetry install` 成功完成
- [ ] `poetry run python --version` 显示 3.11.7
- [ ] `poetry run pytest --version` 可用
- [ ] `poetry run mypy --version` 可用

### 练习 2：进阶场景 — 编写类型安全的配置加载器

**目标**：编写一个带完整类型提示的 YAML 配置加载器

```python
"""
练习：编写类型安全的 SRE 配置加载器

要求：
1. 使用 dataclass 定义配置结构
2. 完整的类型提示
3. 验证逻辑（__post_init__）
4. 支持环境变量覆盖
5. 通过 mypy --strict 检查
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import os
import yaml


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str
    port: int = 5432
    username: str = "sre"
    password: str = ""
    database: str = "sre_db"
    pool_size: int = 10

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Invalid port: {self.port}")
        if self.pool_size < 1:
            raise ValueError(f"Invalid pool_size: {self.pool_size}")


@dataclass
class AlertConfig:
    """告警配置"""
    enabled: bool = True
    webhook_url: str = ""
    channels: List[str] = field(default_factory=list)
    severity_threshold: str = "WARNING"

    def __post_init__(self) -> None:
        valid_severities = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.severity_threshold not in valid_severities:
            raise ValueError(
                f"Invalid severity: {self.severity_threshold}. "
                f"Must be one of {valid_severities}"
            )


@dataclass
class AppConfig:
    """应用主配置"""
    app_name: str = "sre-toolkit"
    environment: str = "development"
    log_level: str = "INFO"
    database: DatabaseConfig = field(
        default_factory=lambda: DatabaseConfig(host="localhost")
    )
    alerts: AlertConfig = field(default_factory=AlertConfig)
    extra: Dict[str, str] = field(default_factory=dict)


def load_config(
    config_path: Path,
    environment: Optional[str] = None,
) -> AppConfig:
    """
    加载配置文件，支持环境变量覆盖。

    Args:
        config_path: 配置文件路径
        environment: 环境名称，用于加载环境特定配置

    Returns:
        AppConfig: 应用配置对象
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw_config: dict = yaml.safe_load(f) or {}

    # 读取环境特定配置
    if environment:
        env_config_path = config_path.parent / f"{environment}.yaml"
        if env_config_path.exists():
            with open(env_config_path, "r", encoding="utf-8") as f:
                env_config: dict = yaml.safe_load(f) or {}
            raw_config = deep_merge(raw_config, env_config)

    # 环境变量覆盖
    raw_config = apply_env_overrides(raw_config)

    return build_config(raw_config)


def deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def apply_env_overrides(config: dict) -> dict:
    """从环境变量覆盖配置"""
    env_mappings = {
        "SRE_APP_NAME": ("app_name",),
        "SRE_ENVIRONMENT": ("environment",),
        "SRE_LOG_LEVEL": ("log_level",),
        "SRE_DB_HOST": ("database", "host"),
        "SRE_DB_PORT": ("database", "port"),
        "SRE_DB_PASSWORD": ("database", "password"),
        "SRE_ALERT_WEBHOOK": ("alerts", "webhook_url"),
    }

    for env_var, path in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None:
            d = config
            for key in path[:-1]:
                d = d.setdefault(key, {})
            if path[-1] == "port":
                value = int(value)
            d[path[-1]] = value

    return config


def build_config(raw: dict) -> AppConfig:
    """从字典构建配置对象"""
    db_raw = raw.get("database", {})
    database = DatabaseConfig(
        host=db_raw.get("host", "localhost"),
        port=db_raw.get("port", 5432),
        username=db_raw.get("username", "sre"),
        password=db_raw.get("password", ""),
        database=db_raw.get("database", "sre_db"),
        pool_size=db_raw.get("pool_size", 10),
    )

    alert_raw = raw.get("alerts", {})
    alerts = AlertConfig(
        enabled=alert_raw.get("enabled", True),
        webhook_url=alert_raw.get("webhook_url", ""),
        channels=alert_raw.get("channels", []),
        severity_threshold=alert_raw.get("severity_threshold", "WARNING"),
    )

    return AppConfig(
        app_name=raw.get("app_name", "sre-toolkit"),
        environment=raw.get("environment", "development"),
        log_level=raw.get("log_level", "INFO"),
        database=database,
        alerts=alerts,
    )


if __name__ == "__main__":
    config = AppConfig(
        app_name="my-sre-tool",
        environment="production",
        database=DatabaseConfig(
            host="db.prod.internal",
            port=5432,
            username="sre",
            password="secret",
            database="monitoring",
        ),
        alerts=AlertConfig(
            webhook_url="https://hooks.slack.com/xxx",
            channels=["#sre-alerts", "#oncall"],
            severity_threshold="ERROR",
        ),
    )
    print(f"App: {config.app_name}")
    print(f"DB:  {config.database.host}:{config.database.port}")
    print(f"Alert channels: {config.alerts.channels}")
```

### 练习 3：故障排查挑战 — 修复有问题的 SRE 脚本

**场景**：以下脚本有多个 PEP 8 违规和类型问题，请用 flake8 和 mypy 找出并修复所有问题。

```python
# broken_script.py — 故障排查练习
import json,os,sys
import requests
from typing import *

def check_server(host,port=80,timeout=5):
    try:
        r=requests.get(f"http://{host}:{port}/health",timeout=timeout)
        if r.status_code==200:
            return {'status':'healthy','latency':r.elapsed.total_seconds()}
        else:
            return {'status':'unhealthy','code':r.status_code}
    except Exception as e:
        return {'status':'error','message':str(e)}

def check_multiple(hosts,ports=[80,443],timeout=5):
    results={}
    for host in hosts:
        for port in ports:
            key=f"{host}:{port}"
            results[key]=check_server(host,port,timeout)
    return results

def main():
    servers=['web-01','web-02','api-01']
    results=check_multiple(servers)
    for name,result in results.items():
        print(f"{name}: {result['status']}")
    json.dump(results,open('results.json','w'),indent=2)

if __name__=='__main__':
    main()
```

**修复指引**：

```bash
# 1. 用 flake8 检查
flake8 broken_script.py

# 2. 用 mypy 检查
mypy broken_script.py

# 3. 用 black 自动格式化
black broken_script.py

# 4. 用 isort 排序导入
isort --profile black broken_script.py

# 5. 手动修复 mypy 报告的类型问题
```

**预期发现的问题**：
- E401: 一行多个导入 (`import json,os,sys`)
- E231: 逗号后缺少空格
- E225: 运算符两侧缺少空格
- E501: 行太长
- E302: 顶层定义间缺少空行
- F401: 未使用的导入 (`sys`)
- F403: 通配符导入 (`from typing import *`)
- 可变默认参数 (`ports=[80,443]`) — 应使用 `ports=None`
- 未关闭的文件句柄 (`open('results.json','w')`)

---

## 🎯 面试题精选

### 问题 1：pyenv 的 shim 机制是什么？为什么需要它？

**参考答案**：

pyenv 使用 shim 脚本来拦截 Python 相关命令。shim 是位于 `~/.pyenv/shims/` 目录下的轻量级代理脚本，它们在 PATH 中的优先级最高。

工作流程：
1. 用户执行 `python` 命令
2. Shell 在 PATH 中找到 `~/.pyenv/shims/python`
3. shim 脚本调用 pyenv 的版本解析逻辑
4. 解析优先级：`PYENV_VERSION` 环境变量 > `.python-version` 文件 > `~/.pyenv/version` 全局设置
5. shim 将命令转发到对应版本的实际 Python 二进制文件

需要 shim 机制的原因：直接修改 PATH 只能指向一个 Python 版本，无法实现目录级别的版本切换。shim 层让版本选择是动态的，同一台机器上不同项目可以使用不同 Python 版本。

### 问题 2：venv 创建的虚拟环境中，pip 安装的包为什么不会影响系统 Python？

**参考答案**：

venv 通过以下机制实现隔离：

1. **独立的 site-packages 目录**：每个虚拟环境有自己的 `.venv/lib/pythonX.Y/site-packages/`，pip 安装的包只放在这个目录中。

2. **PATH 优先级**：激活虚拟环境后，`.venv/bin/` 被放在 PATH 最前面，`python` 和 `pip` 命令优先指向虚拟环境内的版本。

3. **pyvenv.cfg 配置**：虚拟环境中的 Python 解释器读取 `pyvenv.cfg` 文件，其中 `include-system-site-packages = false`（默认）确保不加载系统包。

4. **sys.prefix 被修改**：虚拟环境中的 Python 将 `sys.prefix` 指向 `.venv/`，pip 根据这个路径决定安装位置。

### 问题 3：Poetry 的 poetry.lock 文件有什么作用？为什么不能删除？

**参考答案**：

`poetry.lock` 是依赖锁定文件，记录了所有依赖（包括间接依赖）的精确版本和哈希值。

作用：
1. **确定性构建**：确保所有环境（开发、测试、生产）安装完全相同的依赖版本
2. **可复现性**：即使上游发布了新版本，`poetry install` 也会安装锁定的版本
3. **安全性**：哈希校验防止供应链攻击（包被篡改）

删除后果：
- 下次 `poetry install` 会重新解析所有依赖
- 可能安装到不同版本，导致"在我机器上能运行"的问题
- 间接依赖版本变化可能引入不兼容

最佳实践：将 `poetry.lock` 提交到版本控制系统。

### 问题 4：PEP 8 中为什么建议行宽 79 字符？现代开发还需要遵守吗？

**参考答案**：

PEP 8 的 79 字符限制源于历史原因：
- 早期终端宽度为 80 字符
- 便于在终端中并排查看两个文件（diff 工具）
- 强制开发者拆分复杂表达式，提高可读性

现代实践：
- PEP 8 本身允许团队约定更宽的行宽（如 99 或 120）
- Black 默认使用 88 字符（折中方案）
- Google Python Style Guide 使用 80 字符
- 很多团队使用 120 字符

SRE 场景建议：
- 终端操作频繁的 SRE 脚本建议保持 79-88 字符
- 工具类代码可以放宽到 120 字符
- 关键是团队统一，不要混用

### 问题 5：Type Hint 在运行时有性能影响吗？

**参考答案**：

**性能影响**：
- Type Hint 在运行时几乎零开销。Python 解释器默认不执行类型检查，类型注解只存储在 `__annotations__` 字典中
- 使用 `from __future__ import annotations`（Python 3.7+）可以将注解变为惰性求值字符串，进一步减少开销
- 只有使用 mypy 等工具进行静态检查时才会真正分析类型

**SRE 最佳实践**：
- 所有公开函数必须有类型提示
- 配置文件加载、API 交互等边界处必须有类型提示
- CI 中集成 mypy 检查

### 问题 6：pre-commit hook 和 CI 检查有什么区别？为什么两者都需要？

**参考答案**：

| 维度 | pre-commit | CI 检查 |
|------|-----------|---------|
| 执行时机 | `git commit` 时 | push 后/PR 创建时 |
| 执行环境 | 开发者本地 | CI 服务器 |
| 检查范围 | 本次提交的变更 | 整个项目 |
| 反馈速度 | 即时（秒级） | 延迟（分钟级） |
| 可绕过 | `--no-verify` 或 `SKIP=hook` | 不能绕过（受保护分支） |

两者都需要的原因：
- pre-commit 提供即时反馈，减少 CI 失败次数，节省 CI 资源
- CI 是最终防线，确保所有代码都经过检查
- CI 可以做 pre-commit 做不到的事：跨平台测试、集成测试、覆盖率报告

### 问题 7：如何在 SRE 脚本中正确处理 secrets（密码、API Key）？

**参考答案**：

```python
import os
from pathlib import Path
from typing import Optional


def get_secret(name: str, default: Optional[str] = None) -> str:
    """
    获取 secret，优先级：环境变量 > Secret 文件 > 默认值
    """
    # 1. 环境变量
    value = os.environ.get(name)
    if value:
        return value

    # 2. Kubernetes Secret 挂载文件
    secret_file = Path(f"/var/run/secrets/{name}")
    if secret_file.exists():
        return secret_file.read_text().strip()

    # 3. 默认值
    if default is not None:
        return default

    raise ValueError(f"Secret not found: {name}")


def mask_secret(value: str, visible: int = 4) -> str:
    """脱敏显示"""
    if len(value) <= visible:
        return "***"
    return value[:visible] + "***"
```

SRE 最佳实践：
1. 永远不要硬编码 secrets
2. 使用环境变量或 Secret Manager（如 HashiCorp Vault、AWS Secrets Manager）
3. 日志中脱敏
4. 使用 `python-dotenv` 加载 `.env` 文件（不要提交到 Git）

### 问题 8：Python 项目中 __init__.py 文件的作用是什么？什么时候可以省略？

**参考答案**：

`__init__.py` 的作用：
1. **标识包**：告诉 Python 这个目录是一个 Python 包（Python 3.3 之前必须有）
2. **控制导入**：定义 `__all__` 列表控制 `from package import *` 的行为
3. **便捷导入**：在 `__init__.py` 中导入子模块，允许 `from package import Class` 而非 `from package.module import Class`

可以省略的情况（Python 3.3+ 命名空间包）：
- 单纯的目录组织，不需要包级别的初始化逻辑
- 使用 `src` layout 的现代项目

SRE 建议：始终添加 `__init__.py`，即使是空文件。这样可以避免导入歧义，也便于工具（mypy、pytest）正确识别包结构。

---

## 📚 深入阅读

### 官方文档
- [Python 官方文档 — venv](https://docs.python.org/3/library/venv.html)
- [Python 官方文档 — typing](https://docs.python.org/3/library/typing.html)
- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 484 — Type Hints](https://peps.python.org/pep-0484/)
- [PEP 526 — Variable Annotations](https://peps.python.org/pep-0526/)

### 工具文档
- [pyenv 官方文档](https://github.com/pyenv/pyenv#readme)
- [Poetry 官方文档](https://python-poetry.org/docs/)
- [mypy 官方文档](https://mypy.readthedocs.io/)
- [Black 官方文档](https://black.readthedocs.io/)
- [pre-commit 官方文档](https://pre-commit.com/)

### 推荐书籍
- 《Fluent Python》Luciano Ramalho — 第 2 章：数据结构
- 《Effective Python》Brett Slatkin — 第 2 章：函数
- 《Python Cookbook》David Beazley — 第 14 章：模块与包

### 技术博客
- [Real Python — Python Virtual Environments](https://realpython.com/python-virtual-environments-a-primer/)
- [Real Python — Python Type Checking](https://realpython.com/python-type-checking/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

## ✅ 自检清单

### 理论检查
- [ ] 能解释 pyenv shim 机制的工作原理
- [ ] 理解 venv 的隔离原理（site-packages、PATH、pyvenv.cfg）
- [ ] 知道 PEP 8 的核心规则（缩进、行宽、命名、导入）
- [ ] 理解 Type Hint 的运行时行为（零开销、静态检查）
- [ ] 知道 Poetry 相比 pip + requirements.txt 的优势

### 实操检查
- [ ] 能用 pyenv 安装和切换 Python 版本
- [ ] 能用 venv 或 Poetry 创建和管理虚拟环境
- [ ] 能配置 flake8 + mypy + black + isort 工具链
- [ ] 能配置 pre-commit 实现提交前自动检查
- [ ] 能编写带完整类型提示的 Python 模块

### 能力验证
- [ ] 能从零搭建一个 SRE 工具项目（含 pyproject.toml、CI、pre-commit）
- [ ] 能通过 mypy --strict 检查自己编写的代码
- [ ] 能为团队制定 Python 开发规范并配置自动化检查
