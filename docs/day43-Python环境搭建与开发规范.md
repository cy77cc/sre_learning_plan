# Day 43: Python 环境搭建与开发规范

> 📅 日期：2026-05-02
> 📖 学习主题：Python 环境搭建与开发规范
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 掌握 Python 虚拟环境（venv）的创建和使用
- 理解 pip 的依赖管理机制
- 掌握 PEP 8 编码规范
- 了解 Python 在 SRE 工作中的典型应用场景

---

## 📖 详细知识点

### 1. Python 环境管理

#### 1.1 为什么需要虚拟环境

系统只有一个 Python，但不同项目需要不同版本的包。虚拟环境为每个项目提供隔离的 Python 环境。

```bash
# 创建虚拟环境
python3 -m venv ~/envs/sre-tools

# 激活
source ~/envs/sre-tools/bin/activate

# 验证
which python3    # ~/envs/sre-tools/bin/python3
python3 --version

# 安装包
pip install requests boto3 prometheus-client

# 导出依赖
pip freeze > requirements.txt

# 从 requirements.txt 安装
pip install -r requirements.txt

# 退出虚拟环境
deactivate
```

#### 1.2 pip 依赖管理

```bash
# 查看已安装包
pip list

# 检查过期包
pip list --outdated

# 安装指定版本
pip install "requests>=2.28,<3.0"
pip install "django==4.2.0"

# 卸载包
pip uninstall requests

# 离线安装（生产环境无网络时）
pip download -d ./packages -r requirements.txt
pip install --no-index --find-links ./packages -r requirements.txt
```

### 2. PEP 8 编码规范

#### 2.1 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量/函数 | snake_case | `get_user_info` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES = 3` |
| 类 | PascalCase | `class HealthChecker` |
| 私有变量 | `_leading_underscore` | `_internal_state` |

#### 2.2 格式规范

```python
# 正确写法
def calculate_metrics(cpu, memory, disk):
    """Calculate system metrics.

    Args:
        cpu: CPU usage (0-100)
        memory: Memory usage (0-100)
        disk: Disk usage (0-100)

    Returns:
        dict with all metrics
    """
    return {
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
    }


class ServerMonitor:
    """Server health monitor."""

    MAX_RETRIES = 3  # 类常量用大写

    def __init__(self, host):
        self._host = host  # 私有变量用下划线前缀
        self._metrics = {}

    def check_health(self):
        """Check server health status."""
        pass


# 导入顺序：标准库 -> 第三方 -> 本地
import os
import sys

import requests
import boto3

from .utils import format_output
```

#### 2.3 自动格式化工具

```bash
# 安装
pip install black flake8 isort mypy

# 自动格式化代码
black script.py

# 排序 import
isort script.py

# 检查代码风格
flake8 script.py

# 类型检查
mypy script.py
```

### 3. SRE 中的 Python 应用

Python 在 SRE 中的典型应用：
1. 运维脚本（替代 Bash 处理复杂逻辑）
2. API 集成（调用 AWS、阿里云、K8s API）
3. 数据处理（日志分析、指标聚合）
4. 自动化工具（部署、备份、监控）
5. Web 服务（FastAPI/Flask 构建管理后台）

---

## 🏗️ 实战：搭建 Python SRE 工具项目

```bash
# 1. 创建项目结构
mkdir -p sre-tools/{src,tests,scripts}
cd sre-tools

# 2. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装开发工具
pip install black flake8 isort pytest requests

# 4. 创建配置文件 pyproject.toml
cat > pyproject.toml << 'EOF'
[tool.black]
line-length = 88
target-version = ['py39']

[tool.isort]
profile = "black"
EOF
```

```python
# src/health_check.py
#!/usr/bin/env python3
"""Server health check tool."""

import requests
import sys
from typing import Dict


def check_endpoint(url: str, timeout: int = 5) -> Dict:
    """Check an HTTP endpoint."""
    try:
        resp = requests.get(url, timeout=timeout)
        return {
            "url": url,
            "status": resp.status_code,
            "healthy": resp.status_code == 200,
        }
    except requests.RequestException as e:
        return {"url": url, "status": None, "healthy": False, "error": str(e)}


def main():
    endpoints = [
        "http://localhost:8080/health",
        "http://localhost:3306",
        "http://localhost:6379",
    ]

    all_healthy = True
    for url in endpoints:
        result = check_endpoint(url)
        status = "OK" if result["healthy"] else "FAIL"
        print(f"{status} {url} -> {result['status']}")
        if not result["healthy"]:
            all_healthy = False

    sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    main()
```

---

## 🧪 练习题

### 练习 1：依赖冲突解决

项目中同时需要 requests==2.28 和 boto3>=1.26，但 boto3 依赖 requests>=2.31。如何解决？

<details>
<summary>答案</summary>

使用 pip-tools 或 poetry 进行依赖解析，或者升级 requests 到兼容版本：
```bash
pip install "requests>=2.31" "boto3>=1.26"
# 或者用 poetry/pip-compile 自动解决版本冲突
```
</details>

---

## 🧪 练习题

### 练习 1：环境检测脚本

编写一个脚本，检查 Python 版本和依赖包是否满足要求。

<details>
<summary>答案</summary>

```python
import sys
import importlib

def check_env():
    # Python version
    v = sys.version_info
    if v < (3, 9):
        print(f"FAIL: need Python 3.9+, got {v.major}.{v.minor}")
        return False
    print(f"OK: Python {v.major}.{v.minor}")

    # Required packages
    for pkg in ["requests", "boto3", "pyyaml"]:
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, "__version__", "unknown")
            print(f"OK: {pkg} {ver}")
        except ImportError:
            print(f"FAIL: {pkg} not installed")
            return False
    return True

if __name__ == "__main__":
    sys.exit(0 if check_env() else 1)
```
</details>

---

## 📚 扩展阅读

- [PEP 8 官方文档](https://peps.python.org/pep-0008/)
- [Black 代码格式化工具](https://black.readthedocs.io/)
- [Python 虚拟环境指南](https://docs.python.org/3/library/venv.html)
