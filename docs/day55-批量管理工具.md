# Day 55: 批量管理工具

> 📅 日期：2026-05-02
> 📖 学习主题：Paramiko/SSH 批量执行、并发控制、结果聚合、Playbook 风格、幂等操作
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 52 装饰器与高级技巧、Day 53 面向对象设计、Day 50 并发编程

## 🎯 学习目标

完成 Day 55 的学习后，你应该能够：
- 使用 Paramiko 实现 SSH 连接管理和远程命令执行
- 实现并发执行框架，支持并行和串行任务
- 构建结果聚合和报告生成功能
- 设计 Playbook 风格的任务定义语言
- 实现幂等操作，确保重复执行安全
- 构建一个类似 Ansible 核心功能的批量管理工具

---

## 📖 核心知识点

### 1. 系统架构设计

```
批量管理工具架构：

┌─────────────────────────────────────────────────────────────────┐
│                      BatchManager                                │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Inventory│    │  Task    │    │ Executor │    │ Reporter │  │
│  │  主机清单  │ →  │  任务定义 │ →  │  执行引擎 │ →  │  结果报告 │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ YAML/INI │    │ Playbook │    │ SSH Pool │    │ 聚合统计  │  │
│  │ 主机文件  │    │ 任务描述  │    │ 并发控制  │    │ 格式输出  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    安全与幂等                              │   │
│  │  SSH 密钥认证 → 幂等检查 → 变更检测 → 回滚支持             │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. SSH 连接管理

#### 2.1 Paramiko 基础与连接池

```python
import paramiko
import threading
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class HostInfo:
    """主机信息。"""
    hostname: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    key_file: Optional[str] = None
    sudo: bool = False
    sudo_password: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    @property
    def address(self):
        return f"{self.username}@{self.hostname}:{self.port}"


@dataclass
class CommandResult:
    """命令执行结果。"""
    host: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    success: bool = True
    error: Optional[str] = None

    def __str__(self):
        status = "OK" if self.success else "FAIL"
        return f"[{status}] {self.host}: exit={self.exit_code} ({self.duration:.1f}s)"


class SSHConnectionPool:
    """SSH 连接池。

    管理 SSH 连接的复用，避免频繁建立连接的开销。

    架构：
    ┌─────────────────────────────────────────┐
    │           SSHConnectionPool              │
    │  ┌─────────────────────────────────┐    │
    │  │  连接池 (按主机分组)              │    │
    │  │  host1: [conn1, conn2, ...]     │    │
    │  │  host2: [conn1, conn2, ...]     │    │
    │  └─────────────────────────────────┘    │
    │  - 连接复用                              │
    │  - 自动重连                              │
    │  - 线程安全                              │
    │  - 空闲连接回收                          │
    └─────────────────────────────────────────┘
    """

    def __init__(self, max_connections_per_host: int = 5):
        self._pools: Dict[str, list] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._max_per_host = max_connections_per_host
        self._global_lock = threading.Lock()

    def _get_lock(self, hostname: str) -> threading.Lock:
        if hostname not in self._locks:
            with self._global_lock:
                if hostname not in self._locks:
                    self._locks[hostname] = threading.Lock()
                    self._pools[hostname] = []
        return self._locks[hostname]

    @contextmanager
    def get_connection(self, host: HostInfo):
        """获取 SSH 连接（上下文管理器）。"""
        lock = self._get_lock(host.hostname)
        conn = None

        with lock:
            if self._pools[host.hostname]:
                conn = self._pools[host.hostname].pop()

        if conn is None:
            conn = self._create_connection(host)

        try:
            yield conn
        finally:
            # 验证连接是否仍然可用
            if conn.get_transport() and conn.get_transport().is_active():
                with lock:
                    if len(self._pools[host.hostname]) < self._max_per_host:
                        self._pools[host.hostname].append(conn)
                    else:
                        conn.close()
            else:
                conn.close()

    def _create_connection(self, host: HostInfo) -> paramiko.SSHClient:
        """创建新的 SSH 连接。"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": host.hostname,
            "port": host.port,
            "username": host.username,
            "timeout": 10,
        }

        if host.key_file:
            connect_kwargs["key_filename"] = host.key_file
        elif host.password:
            connect_kwargs["password"] = host.password

        client.connect(**connect_kwargs)
        logger.debug(f"SSH 连接建立: {host.address}")
        return client

    def close_all(self):
        """关闭所有连接。"""
        with self._global_lock:
            for hostname, pool in self._pools.items():
                for conn in pool:
                    try:
                        conn.close()
                    except Exception:
                        pass
                pool.clear()
```

#### 2.2 远程命令执行

```python
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RemoteExecutor:
    """远程命令执行器。"""

    def __init__(self, pool: SSHConnectionPool):
        self.pool = pool

    def execute(self, host: HostInfo, command: str,
                timeout: int = 30) -> CommandResult:
        """执行远程命令。"""
        start_time = time.time()

        try:
            with self.pool.get_connection(host) as conn:
                # 如果需要 sudo
                if host.sudo:
                    if host.sudo_password:
                        command = f"echo '{host.sudo_password}' | sudo -S {command}"
                    else:
                        command = f"sudo {command}"

                # 执行命令
                stdin, stdout, stderr = conn.exec_command(
                    command, timeout=timeout
                )

                exit_code = stdout.channel.recv_exit_status()
                stdout_str = stdout.read().decode('utf-8', errors='replace')
                stderr_str = stderr.read().decode('utf-8', errors='replace')

                duration = time.time() - start_time

                return CommandResult(
                    host=host.hostname,
                    command=command,
                    exit_code=exit_code,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    duration=duration,
                    success=(exit_code == 0)
                )

        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                host=host.hostname,
                command=command,
                exit_code=-1,
                stdout="",
                stderr="",
                duration=duration,
                success=False,
                error=str(e)
            )

    def upload_file(self, host: HostInfo, local_path: str,
                    remote_path: str) -> CommandResult:
        """上传文件到远程主机。"""
        start_time = time.time()
        try:
            with self.pool.get_connection(host) as conn:
                sftp = conn.open_sftp()
                sftp.put(local_path, remote_path)
                sftp.close()

                duration = time.time() - start_time
                return CommandResult(
                    host=host.hostname,
                    command=f"upload {local_path} -> {remote_path}",
                    exit_code=0,
                    stdout=f"文件上传成功: {local_path} -> {remote_path}",
                    stderr="",
                    duration=duration,
                    success=True
                )
        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                host=host.hostname,
                command=f"upload {local_path} -> {remote_path}",
                exit_code=-1,
                stdout="",
                stderr="",
                duration=duration,
                success=False,
                error=str(e)
            )

    def download_file(self, host: HostInfo, remote_path: str,
                      local_path: str) -> CommandResult:
        """从远程主机下载文件。"""
        start_time = time.time()
        try:
            with self.pool.get_connection(host) as conn:
                sftp = conn.open_sftp()
                sftp.get(remote_path, local_path)
                sftp.close()

                duration = time.time() - start_time
                return CommandResult(
                    host=host.hostname,
                    command=f"download {remote_path} -> {local_path}",
                    exit_code=0,
                    stdout=f"文件下载成功: {remote_path} -> {local_path}",
                    stderr="",
                    duration=duration,
                    success=True
                )
        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                host=host.hostname,
                command=f"download {remote_path} -> {local_path}",
                exit_code=-1,
                stdout="",
                stderr="",
                duration=duration,
                success=False,
                error=str(e)
            )
```

### 3. 主机清单（Inventory）

```python
import yaml
from typing import Dict, List, Optional
from pathlib import Path


class Inventory:
    """主机清单管理。

    支持 YAML 格式的主机定义，支持分组和变量继承。

    YAML 格式示例：
    ```yaml
    all:
      vars:
        username: root
        key_file: ~/.ssh/id_rsa

      children:
        webservers:
          hosts:
            - web01: {hostname: 10.0.1.10, port: 22}
            - web02: {hostname: 10.0.1.11}
          vars:
            http_port: 80

        dbservers:
          hosts:
            - db01: {hostname: 10.0.2.10}
            - db02: {hostname: 10.0.2.11}
          vars:
            db_port: 3306
    ```
    """

    def __init__(self):
        self._hosts: Dict[str, HostInfo] = {}
        self._groups: Dict[str, List[str]] = {}
        self._group_vars: Dict[str, Dict] = {}

    @classmethod
    def from_yaml(cls, filepath: str) -> 'Inventory':
        """从 YAML 文件加载。"""
        inv = cls()
        with open(filepath) as f:
            data = yaml.safe_load(f)

        all_vars = data.get("all", {}).get("vars", {})
        children = data.get("all", {}).get("children", {})

        for group_name, group_data in children.items():
            hosts = group_data.get("hosts", [])
            group_vars = {**all_vars, **group_data.get("vars", {})}

            inv._group_vars[group_name] = group_vars
            inv._groups[group_name] = []

            for host_entry in hosts:
                if isinstance(host_entry, str):
                    # 简单格式：只有主机名
                    host_info = HostInfo(hostname=host_entry, **group_vars)
                    inv._hosts[host_entry] = host_info
                    inv._groups[group_name].append(host_entry)
                elif isinstance(host_entry, dict):
                    # 详细格式：{name: {hostname: ..., port: ...}}
                    for name, props in host_entry.items():
                        merged = {**group_vars, **props}
                        host_info = HostInfo(
                            hostname=merged.get("hostname", name),
                            port=merged.get("port", 22),
                            username=merged.get("username", "root"),
                            password=merged.get("password"),
                            key_file=merged.get("key_file"),
                            sudo=merged.get("sudo", False),
                            tags=merged.get("tags", {}),
                        )
                        inv._hosts[name] = host_info
                        inv._groups[group_name].append(name)

        return inv

    @classmethod
    def from_simple(cls, hosts: List[str], **kwargs) -> 'Inventory':
        """从简单主机列表创建。"""
        inv = cls()
        for host in hosts:
            inv._hosts[host] = HostInfo(hostname=host, **kwargs)
        inv._groups["all"] = list(hosts)
        return inv

    def get_host(self, name: str) -> Optional[HostInfo]:
        return self._hosts.get(name)

    def get_hosts(self, group: str = None) -> List[HostInfo]:
        if group:
            names = self._groups.get(group, [])
            return [self._hosts[n] for n in names if n in self._hosts]
        return list(self._hosts.values())

    def get_groups(self) -> List[str]:
        return list(self._groups.keys())

    def filter_hosts(self, pattern: str = None,
                     tags: Dict[str, str] = None) -> List[HostInfo]:
        """按模式或标签过滤主机。"""
        hosts = list(self._hosts.values())

        if pattern:
            import fnmatch
            hosts = [h for h in hosts
                     if fnmatch.fnmatch(h.hostname, pattern)
                     or fnmatch.fnmatch(h.hostname.split('.')[0], pattern)]

        if tags:
            hosts = [h for h in hosts
                     if all(h.tags.get(k) == v for k, v in tags.items())]

        return hosts
```

### 4. 并发执行引擎

```python
import time
import logging
from typing import List, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """执行配置。"""
    max_workers: int = 10          # 最大并发数
    timeout: int = 30              # 单个任务超时（秒）
    serial: bool = False           # 是否串行执行
    fail_fast: bool = False        # 遇到失败是否立即停止
    retry_count: int = 0           # 失败重试次数
    retry_delay: float = 1.0       # 重试间隔


@dataclass
class ExecutionReport:
    """执行报告。"""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    duration: float = 0.0
    results: List[CommandResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (self.success / self.total * 100) if self.total else 0

    def summary(self) -> str:
        return (
            f"执行完成: 总计 {self.total}, "
            f"成功 {self.success}, 失败 {self.failed}, "
            f"跳过 {self.skipped}, "
            f"成功率 {self.success_rate:.1f}%, "
            f"耗时 {self.duration:.1f}s"
        )


class TaskExecutor:
    """任务执行引擎。

    支持并行和串行两种执行模式，支持失败快速停止和重试。

    执行流程：
    ┌─────────────────────────────────────────────────┐
    │                 TaskExecutor                     │
    │                                                  │
    │  1. 接收主机列表和命令                            │
    │  2. 根据配置选择执行模式                          │
    │     ├─ 并行模式: ThreadPoolExecutor              │
    │     └─ 串行模式: 逐个执行                        │
    │  3. 收集结果并生成报告                            │
    │  4. 失败重试（如果配置）                          │
    │  5. 返回 ExecutionReport                         │
    └─────────────────────────────────────────────────┘
    """

    def __init__(self, executor: RemoteExecutor,
                 config: ExecutionConfig = None):
        self.executor = executor
        self.config = config or ExecutionConfig()

    def run(self, hosts: List[HostInfo], command: str) -> ExecutionReport:
        """在多台主机上执行命令。"""
        report = ExecutionReport(total=len(hosts))
        start_time = time.time()

        if self.config.serial:
            self._run_serial(hosts, command, report)
        else:
            self._run_parallel(hosts, command, report)

        report.duration = time.time() - start_time
        return report

    def _run_parallel(self, hosts: List[HostInfo], command: str,
                      report: ExecutionReport):
        """并行执行。"""
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as pool:
            future_to_host = {}
            for host in hosts:
                future = pool.submit(
                    self._execute_with_retry, host, command
                )
                future_to_host[future] = host

            for future in as_completed(future_to_host, timeout=self.config.timeout * 3):
                host = future_to_host[future]
                try:
                    result = future.result(timeout=self.config.timeout)
                    report.results.append(result)

                    if result.success:
                        report.success += 1
                        logger.info(f"OK {host.hostname}: {result.stdout.strip()[:100]}")
                    else:
                        report.failed += 1
                        logger.error(f"FAIL {host.hostname}: {result.error or result.stderr}")

                    if self.config.fail_fast and not result.success:
                        # 取消剩余任务
                        for f in future_to_host:
                            f.cancel()
                        break

                except Exception as e:
                    report.failed += 1
                    report.results.append(CommandResult(
                        host=host.hostname,
                        command=command,
                        exit_code=-1,
                        stdout="",
                        stderr="",
                        duration=0,
                        success=False,
                        error=str(e)
                    ))

    def _run_serial(self, hosts: List[HostInfo], command: str,
                    report: ExecutionReport):
        """串行执行。"""
        for host in hosts:
            result = self._execute_with_retry(host, command)
            report.results.append(result)

            if result.success:
                report.success += 1
            else:
                report.failed += 1
                if self.config.fail_fast:
                    report.skipped = len(hosts) - report.success - report.failed
                    break

    def _execute_with_retry(self, host: HostInfo,
                            command: str) -> CommandResult:
        """带重试的执行。"""
        last_result = None
        for attempt in range(self.config.retry_count + 1):
            result = self.executor.execute(host, command, self.config.timeout)
            if result.success:
                return result
            last_result = result
            if attempt < self.config.retry_count:
                logger.warning(
                    f"{host.hostname} 第 {attempt + 1} 次失败，"
                    f"{self.config.retry_delay}s 后重试"
                )
                time.sleep(self.config.retry_delay)
        return last_result
```

### 5. Playbook 风格的任务定义

```python
import yaml
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum, auto


class TaskState(Enum):
    """任务状态。"""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    SKIPPED = auto()
    CHANGED = auto()


@dataclass
class Task:
    """Playbook 任务。

    类似 Ansible 的任务定义：
    ```yaml
    - name: 安装 Nginx
      apt:
        name: nginx
        state: present
      when: ansible_os_family == "Debian"
      tags: [web, nginx]
    ```
    """
    name: str
    module: str                    # 模块名（command, shell, apt, copy, etc）
    args: Dict[str, Any] = field(default_factory=dict)
    when: Optional[str] = None     # 条件表达式
    tags: List[str] = field(default_factory=list)
    ignore_errors: bool = False    # 忽略错误
    register: Optional[str] = None # 注册结果到变量
    changed_when: Optional[str] = None  # 判断是否"变更"的条件


@dataclass
class Play:
    """Playbook 中的一个 Play。

    定义一组主机和在这些主机上执行的任务。
    ```yaml
    - hosts: webservers
      become: true
      vars:
        http_port: 80
      tasks:
        - name: 安装 Nginx
          apt: name=nginx state=present
    ```
    """
    hosts: str                     # 目标主机组
    become: bool = False           # 是否 sudo
    vars: Dict[str, Any] = field(default_factory=dict)
    tasks: List[Task] = field(default_factory=list)
    serial: int = 0                # 滚动更新批次大小


class Playbook:
    """Playbook 解析器和执行器。

    支持 YAML 格式的任务定义，类似 Ansible 的 Playbook 语法。

    完整示例 (deploy_web.yaml):
    ```yaml
    - hosts: webservers
      become: true
      vars:
        app_version: "2.1.0"
        app_dir: /opt/myapp
      tasks:
        - name: 检查应用目录
          command: test -d {{ app_dir }}
          register: dir_check
          ignore_errors: true

        - name: 创建应用目录
          command: mkdir -p {{ app_dir }}
          when: dir_check.rc != 0

        - name: 停止旧版本
          systemd:
            name: myapp
            state: stopped
          ignore_errors: true

        - name: 部署新版本
          copy:
            src: ./dist/myapp-{{ app_version }}.tar.gz
            dest: /tmp/myapp.tar.gz

        - name: 解压部署
          command: tar xzf /tmp/myapp.tar.gz -C {{ app_dir }}

        - name: 启动新版本
          systemd:
            name: myapp
            state: started
            enabled: true

        - name: 健康检查
          command: curl -s http://localhost:8080/health
          register: health
          retries: 5
          delay: 3
    ```
    """

    @classmethod
    def from_yaml(cls, filepath: str) -> List[Play]:
        """从 YAML 文件解析 Playbook。"""
        with open(filepath) as f:
            data = yaml.safe_load(f)

        plays = []
        for play_data in data:
            tasks = []
            for task_data in play_data.get("tasks", []):
                # 解析模块参数（支持两种格式）
                module = task_data.get("module", "")
                args = {}

                # 格式 1: module: name=xxx state=xxx
                if "module" not in task_data:
                    for key, value in task_data.items():
                        if key in ("name", "when", "tags", "ignore_errors",
                                   "register", "changed_when"):
                            continue
                        module = key
                        if isinstance(value, str):
                            # 解析 key=value 格式
                            args = cls._parse_module_args(value)
                        elif isinstance(value, dict):
                            args = value
                        break

                task = Task(
                    name=task_data.get("name", "未命名任务"),
                    module=module,
                    args=args,
                    when=task_data.get("when"),
                    tags=task_data.get("tags", []),
                    ignore_errors=task_data.get("ignore_errors", False),
                    register=task_data.get("register"),
                )
                tasks.append(task)

            play = Play(
                hosts=play_data.get("hosts", "all"),
                become=play_data.get("become", False),
                vars=play_data.get("vars", {}),
                tasks=tasks,
                serial=play_data.get("serial", 0),
            )
            plays.append(play)

        return plays

    @staticmethod
    def _parse_module_args(args_str: str) -> Dict[str, str]:
        """解析模块参数字符串。

        将 "name=nginx state=present" 解析为
        {"name": "nginx", "state": "present"}
        """
        args = {}
        import shlex
        tokens = shlex.split(args_str)
        for token in tokens:
            if "=" in token:
                key, value = token.split("=", 1)
                args[key] = value
            else:
                # 位置参数
                args.setdefault("_positional", []).append(token)
        return args
```

### 6. 模块系统

```python
import os
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ModuleResult:
    """模块执行结果。"""

    def __init__(self, changed=False, msg="", rc=0, stdout="", stderr="",
                 failed=False, skipped=False):
        self.changed = changed
        self.msg = msg
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
        self.failed = failed
        self.skipped = skipped

    def to_dict(self):
        return {
            "changed": self.changed,
            "msg": self.msg,
            "rc": self.rc,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "failed": self.failed,
            "skipped": self.skipped,
        }


class Module(ABC):
    """模块基类。"""

    @abstractmethod
    def execute(self, host: HostInfo, args: Dict[str, Any],
                variables: Dict[str, Any]) -> ModuleResult:
        pass

    def _render_args(self, args: Dict[str, Any],
                     variables: Dict[str, Any]) -> Dict[str, Any]:
        """渲染参数中的变量引用。"""
        rendered = {}
        for key, value in args.items():
            if isinstance(value, str):
                # 替换 {{ variable }} 格式的变量
                import re
                def replace_var(match):
                    var_name = match.group(1).strip()
                    return str(variables.get(var_name, match.group(0)))
                value = re.sub(r'\{\{\s*(.+?)\s*\}\}', replace_var, value)
            rendered[key] = value
        return rendered


class CommandModule(Module):
    """command 模块 — 执行远程命令。

    这是最基础的模块，直接执行 shell 命令。
    幂等性：需要由用户通过 when 条件控制。
    """

    def __init__(self, executor: RemoteExecutor):
        self.executor = executor

    def execute(self, host, args, variables):
        args = self._render_args(args, variables)
        command = args.get("command") or args.get("_positional", [""])[0]
        if not command:
            return ModuleResult(failed=True, msg="未指定命令")

        result = self.executor.execute(host, command)
        return ModuleResult(
            changed=True,  # command 总是认为有变更
            msg=f"命令执行完成: exit={result.exit_code}",
            rc=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            failed=(result.exit_code != 0)
        )


class ShellModule(Module):
    """shell 模块 — 执行 shell 命令（支持管道等）。

    与 command 模块的区别：通过 /bin -sh -c 执行，
    支持管道、重定向等 shell 特性。
    """

    def __init__(self, executor: RemoteExecutor):
        self.executor = executor

    def execute(self, host, args, variables):
        args = self._render_args(args, variables)
        command = args.get("command") or args.get("_positional", [""])[0]
        if not command:
            return ModuleResult(failed=True, msg="未指定命令")

        result = self.executor.execute(host, f"/bin/sh -c '{command}'")
        return ModuleResult(
            changed=True,
            msg=f"Shell 命令执行完成: exit={result.exit_code}",
            rc=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            failed=(result.exit_code != 0)
        )


class CopyModule(Module):
    """copy 模块 — 复制文件到远程主机。

    幂等性：比较文件内容的 MD5，只在内容不同时才复制。
    """

    def __init__(self, executor: RemoteExecutor):
        self.executor = executor

    def execute(self, host, args, variables):
        args = self._render_args(args, variables)
        src = args.get("src") or args.get("_positional", [""])[0]
        dest = args.get("dest") or args.get("_positional", ["", ""])[1] \
            if len(args.get("_positional", [])) > 1 else None

        if not src or not dest:
            return ModuleResult(failed=True, msg="需要指定 src 和 dest")

        if not os.path.exists(src):
            return ModuleResult(failed=True, msg=f"源文件不存在: {src}")

        # 幂等检查：比较远程文件的 MD5
        import hashlib
        local_md5 = hashlib.md5(open(src, 'rb').read()).hexdigest()
        check_result = self.executor.execute(host, f"md5sum {dest} 2>/dev/null")

        if check_result.success:
            remote_md5 = check_result.stdout.split()[0] if check_result.stdout else ""
            if local_md5 == remote_md5:
                return ModuleResult(
                    changed=False,
                    msg=f"文件已存在且内容相同: {dest}"
                )

        # 上传文件
        upload_result = self.executor.upload_file(host, src, dest)
        if not upload_result.success:
            return ModuleResult(
                failed=True,
                msg=f"文件上传失败: {upload_result.error}"
            )

        return ModuleResult(
            changed=True,
            msg=f"文件已复制: {src} -> {dest}"
        )


class SystemdModule(Module):
    """systemd 模块 — 管理 systemd 服务。

    幂等性：检查服务当前状态，只在需要时才执行操作。
    """

    def __init__(self, executor: RemoteExecutor):
        self.executor = executor

    def execute(self, host, args, variables):
        args = self._render_args(args, variables)
        name = args.get("name")
        state = args.get("state")  # started, stopped, restarted, reloaded
        enabled = args.get("enabled")  # true, false

        if not name:
            return ModuleResult(failed=True, msg="需要指定服务名称")

        changed = False
        messages = []

        # 检查当前状态
        status_result = self.executor.execute(
            host, f"systemctl is-active {name} 2>/dev/null"
        )
        is_active = status_result.stdout.strip() == "active"

        # 处理状态变更
        if state:
            if state in ("started", "restarted") and not is_active:
                action = "restart" if state == "restarted" else "start"
                result = self.executor.execute(host, f"systemctl {action} {name}")
                if result.exit_code != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"服务 {action} 失败: {result.stderr}"
                    )
                changed = True
                messages.append(f"服务已 {action}")

            elif state == "stopped" and is_active:
                result = self.executor.execute(host, f"systemctl stop {name}")
                if result.exit_code != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"服务停止失败: {result.stderr}"
                    )
                changed = True
                messages.append("服务已停止")

            elif state == "reloaded":
                result = self.executor.execute(host, f"systemctl reload {name}")
                if result.exit_code != 0:
                    return ModuleResult(
                        failed=True,
                        msg=f"服务重载失败: {result.stderr}"
                    )
                changed = True
                messages.append("服务已重载")

        # 处理开机启动
        if enabled is not None:
            is_enabled_result = self.executor.execute(
                host, f"systemctl is-enabled {name} 2>/dev/null"
            )
            is_enabled = is_enabled_result.stdout.strip() == "enabled"

            if enabled and not is_enabled:
                self.executor.execute(host, f"systemctl enable {name}")
                changed = True
                messages.append("已设置开机启动")
            elif not enabled and is_enabled:
                self.executor.execute(host, f"systemctl disable {name}")
                changed = True
                messages.append("已取消开机启动")

        return ModuleResult(
            changed=changed,
            msg="; ".join(messages) if messages else "服务状态无需变更"
        )


class AptModule(Module):
    """apt 模块 — 管理 Debian/Ubuntu 软件包。

    幂等性：检查包是否已安装，只在需要时才执行安装/卸载。
    """

    def __init__(self, executor: RemoteExecutor):
        self.executor = executor

    def execute(self, host, args, variables):
        args = self._render_args(args, variables)
        name = args.get("name")
        state = args.get("state", "present")  # present, absent, latest

        if not name:
            return ModuleResult(failed=True, msg="需要指定包名")

        # 检查是否已安装
        check = self.executor.execute(host, f"dpkg -l {name} 2>/dev/null")
        is_installed = check.exit_code == 0 and f"ii  {name}" in check.stdout

        if state == "present" and is_installed:
            return ModuleResult(changed=False, msg=f"包 {name} 已安装")

        if state == "absent" and not is_installed:
            return ModuleResult(changed=False, msg=f"包 {name} 未安装")

        # 执行操作
        if state in ("present", "latest"):
            cmd = f"apt-get install -y {name}"
            if state == "latest":
                cmd = f"apt-get install -y --only-upgrade {name}"
        elif state == "absent":
            cmd = f"apt-get remove -y {name}"
        else:
            return ModuleResult(failed=True, msg=f"未知状态: {state}")

        result = self.executor.execute(host, cmd, timeout=120)
        return ModuleResult(
            changed=True,
            msg=f"包 {name} {state} 操作完成",
            rc=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            failed=(result.exit_code != 0)
        )


class ModuleRegistry:
    """模块注册表。"""

    def __init__(self, executor: RemoteExecutor):
        self._modules: Dict[str, Module] = {
            "command": CommandModule(executor),
            "shell": ShellModule(executor),
            "copy": CopyModule(executor),
            "systemd": SystemdModule(executor),
            "apt": AptModule(executor),
        }

    def register(self, name: str, module: Module):
        self._modules[name] = module

    def get(self, name: str) -> Optional[Module]:
        return self._modules.get(name)
```

### 7. Playbook 执行器

```python
import time
import logging
import re
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class PlaybookExecutor:
    """Playbook 执行器。

    执行流程：
    ┌─────────────────────────────────────────────────┐
    │              PlaybookExecutor                    │
    │                                                  │
    │  对每个 Play:                                     │
    │  1. 解析目标主机                                   │
    │  2. 合并变量（全局 + Play 级别）                    │
    │  3. 对每个 Task:                                  │
    │     a. 检查 when 条件                             │
    │     b. 获取对应模块                                │
    │     c. 在目标主机上执行                             │
    │     d. 记录结果（changed/failed/skipped）          │
    │     e. 如果 failed 且非 ignore_errors，停止        │
    │  4. 生成执行报告                                   │
    └─────────────────────────────────────────────────┘
    """

    def __init__(self, inventory: Inventory,
                 module_registry: ModuleRegistry):
        self.inventory = inventory
        self.registry = module_registry
        self._variables: Dict[str, Any] = {}

    def execute(self, plays: List[Play]) -> Dict[str, Any]:
        """执行 Playbook。"""
        overall_results = {
            "plays": [],
            "total_tasks": 0,
            "changed": 0,
            "failed": 0,
            "skipped": 0,
            "unreachable": 0,
        }

        for play in plays:
            play_result = self._execute_play(play)
            overall_results["plays"].append(play_result)
            overall_results["total_tasks"] += play_result["total_tasks"]
            overall_results["changed"] += play_result["changed"]
            overall_results["failed"] += play_result["failed"]
            overall_results["skipped"] += play_result["skipped"]

        return overall_results

    def _execute_play(self, play: Play) -> Dict[str, Any]:
        """执行单个 Play。"""
        hosts = self.inventory.get_hosts(play.hosts)
        if not hosts:
            logger.warning(f"未找到主机: {play.hosts}")
            return {"hosts": play.hosts, "total_tasks": 0, "changed": 0,
                    "failed": 0, "skipped": 0, "task_results": []}

        # 合并变量
        variables = {**self._variables, **play.vars}

        logger.info(f"执行 Play: {play.hosts} ({len(hosts)} 台主机, {len(play.tasks)} 个任务)")

        play_result = {
            "hosts": play.hosts,
            "total_tasks": len(play.tasks),
            "changed": 0,
            "failed": 0,
            "skipped": 0,
            "task_results": [],
        }

        for task in play.tasks:
            task_result = self._execute_task(task, hosts, variables, play.become)
            play_result["task_results"].append(task_result)

            if task_result["status"] == TaskState.CHANGED:
                play_result["changed"] += 1
            elif task_result["status"] == TaskState.FAILED:
                play_result["failed"] += 1
                if not task.ignore_errors:
                    logger.error(f"任务失败，停止执行: {task.name}")
                    break
            elif task_result["status"] == TaskState.SKIPPED:
                play_result["skipped"] += 1

            # 注册结果到变量
            if task.register:
                variables[task.register] = task_result

        return play_result

    def _execute_task(self, task: Task, hosts: List[HostInfo],
                      variables: Dict, become: bool) -> Dict:
        """执行单个任务。"""
        logger.info(f"  任务: {task.name}")

        # 检查 when 条件
        if task.when and not self._evaluate_condition(task.when, variables):
            logger.info(f"    跳过 (条件不满足): {task.when}")
            return {
                "task": task.name,
                "status": TaskState.SKIPPED,
                "host_results": {},
                "message": f"条件不满足: {task.when}"
            }

        # 获取模块
        module = self.registry.get(task.module)
        if not module:
            logger.error(f"    未知模块: {task.module}")
            return {
                "task": task.name,
                "status": TaskState.FAILED,
                "host_results": {},
                "message": f"未知模块: {task.module}"
            }

        # 在所有主机上执行
        host_results = {}
        changed_count = 0
        failed_count = 0

        for host in hosts:
            if become:
                host = HostInfo(
                    hostname=host.hostname,
                    port=host.port,
                    username=host.username,
                    password=host.password,
                    key_file=host.key_file,
                    sudo=True,
                )

            try:
                result = module.execute(host, task.args, variables)
                host_results[host.hostname] = result

                if result.changed:
                    changed_count += 1
                if result.failed:
                    failed_count += 1
                    logger.error(f"    FAIL {host.hostname}: {result.msg}")
                else:
                    logger.info(f"    OK {host.hostname}: {result.msg}")

            except Exception as e:
                failed_count += 1
                host_results[host.hostname] = ModuleResult(
                    failed=True, msg=str(e)
                )
                logger.error(f"    ERROR {host.hostname}: {e}")

        # 确定任务状态
        if failed_count > 0:
            status = TaskState.FAILED
        elif changed_count > 0:
            status = TaskState.CHANGED
        else:
            status = TaskState.SUCCESS

        return {
            "task": task.name,
            "status": status,
            "host_results": {k: v.to_dict() for k, v in host_results.items()},
            "changed": changed_count,
            "failed": failed_count,
        }

    def _evaluate_condition(self, condition: str,
                            variables: Dict) -> bool:
        """评估 when 条件。"""
        # 简单的条件评估
        # 支持: variable == value, variable != value, variable
        try:
            # 替换变量
            rendered = condition
            for key, value in variables.items():
                rendered = rendered.replace(key, repr(value))

            # 安全评估（只允许简单表达式）
            return eval(rendered, {"__builtins__": {}}, variables)
        except Exception as e:
            logger.warning(f"条件评估失败: {condition} -> {e}")
            return False
```

### 8. 结果报告

```python
import json
import time
from typing import Dict, List, Any
from datetime import datetime


class ReportGenerator:
    """执行报告生成器。"""

    @staticmethod
    def text_report(results: Dict[str, Any]) -> str:
        """生成文本报告。"""
        lines = []
        lines.append("=" * 60)
        lines.append("  批量管理工具执行报告")
        lines.append("=" * 60)
        lines.append(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        for play in results.get("plays", []):
            lines.append(f"  主机组: {play['hosts']}")
            lines.append(f"  任务数: {play['total_tasks']}")
            lines.append(f"  变更: {play['changed']}, 失败: {play['failed']}, "
                         f"跳过: {play['skipped']}")
            lines.append("")

            for task_result in play.get("task_results", []):
                status_icon = {
                    TaskState.SUCCESS: "[OK]",
                    TaskState.CHANGED: "[CHANGED]",
                    TaskState.FAILED: "[FAILED]",
                    TaskState.SKIPPED: "[SKIPPED]",
                }.get(task_result["status"], "[?]")

                lines.append(f"    {status_icon} {task_result['task']}")

                for host, result in task_result.get("host_results", {}).items():
                    icon = "OK" if not result.get("failed") else "FAIL"
                    msg = result.get("msg", "")[:80]
                    lines.append(f"          {host}: [{icon}] {msg}")

            lines.append("")

        lines.append("-" * 60)
        lines.append(f"  总计: {results['total_tasks']} 个任务, "
                     f"变更: {results['changed']}, "
                     f"失败: {results['failed']}, "
                     f"跳过: {results['skipped']}")
        lines.append("=" * 60)

        return "\n".join(lines)

    @staticmethod
    def json_report(results: Dict[str, Any]) -> str:
        """生成 JSON 报告。"""
        return json.dumps(results, indent=2, default=str)

    @staticmethod
    def html_report(results: Dict[str, Any]) -> str:
        """生成 HTML 报告。"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>批量管理执行报告</title>
            <style>
                body { font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px; }
                h1 { color: #0f3460; }
                .summary { background: #16213e; padding: 15px; border-radius: 8px; }
                .task { margin: 10px 0; padding: 10px; background: #16213e; border-radius: 4px; }
                .task.ok { border-left: 4px solid #2ecc71; }
                .task.changed { border-left: 4px solid #f39c12; }
                .task.failed { border-left: 4px solid #e74c3c; }
                .task.skipped { border-left: 4px solid #95a5a6; }
                .host { margin-left: 20px; font-size: 14px; }
            </style>
        </head>
        <body>
            <h1>批量管理执行报告</h1>
            <div class="summary">
                <p>总任务: {{ total }}, 变更: {{ changed }}, 失败: {{ failed }}, 跳过: {{ skipped }}</p>
            </div>
            {% for play in plays %}
            <h2>{{ play.hosts }}</h2>
            {% for task in play.task_results %}
            <div class="task {{ task.status.name|lower }}">
                <strong>{{ task.task }}</strong>
                {% for host, result in task.host_results.items() %}
                <div class="host">{{ host }}: {{ result.msg }}</div>
                {% endfor %}
            </div>
            {% endfor %}
            {% endfor %}
        </body>
        </html>
        """
        from jinja2 import Template
        template = Template(html)
        return template.render(
            total=results["total_tasks"],
            changed=results["changed"],
            failed=results["failed"],
            skipped=results["skipped"],
            plays=results["plays"]
        )
```

### 9. CLI 入口与完整使用示例

```python
#!/usr/bin/env python3
"""SRE 批量管理工具 — 类 Ansible 的核心功能。

使用方式：
    # 执行命令
    python batch_manager.py exec -f hosts.yaml -c "uptime" --parallel

    # 执行 Playbook
    python batch_manager.py playbook -f hosts.yaml -p deploy.yaml

    # 上传文件
    python batch_manager.py copy -f hosts.yaml --src ./app.tar.gz --dest /opt/

    # 查看主机信息
    python batch_manager.py info -f hosts.yaml
"""

import argparse
import sys
import logging
import yaml
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("batch-manager")


def cmd_exec(args):
    """执行远程命令。"""
    inventory = Inventory.from_yaml(args.inventory)
    hosts = inventory.get_hosts(args.group) if args.group else inventory.get_hosts()

    if args.pattern:
        import fnmatch
        hosts = [h for h in hosts if fnmatch.fnmatch(h.hostname, args.pattern)]

    if not hosts:
        logger.error("没有匹配的主机")
        sys.exit(1)

    logger.info(f"在 {len(hosts)} 台主机上执行: {args.command}")

    pool = SSHConnectionPool()
    executor = RemoteExecutor(pool)
    config = ExecutionConfig(
        max_workers=args.workers,
        timeout=args.timeout,
        serial=not args.parallel,
        fail_fast=args.fail_fast,
        retry_count=args.retries,
    )
    task_executor = TaskExecutor(executor, config)
    report = task_executor.run(hosts, args.command)

    # 输出结果
    for result in report.results:
        print(f"{result}")
        if result.stdout and args.verbose:
            print(f"  stdout: {result.stdout.strip()}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")

    print(f"\n{report.summary()}")
    pool.close_all()

    if report.failed > 0:
        sys.exit(1)


def cmd_playbook(args):
    """执行 Playbook。"""
    inventory = Inventory.from_yaml(args.inventory)
    pool = SSHConnectionPool()
    executor = RemoteExecutor(pool)
    module_registry = ModuleRegistry(executor)

    plays = Playbook.from_yaml(args.playbook)
    playbook_executor = PlaybookExecutor(inventory, module_registry)
    results = playbook_executor.execute(plays)

    # 生成报告
    report_gen = ReportGenerator()
    if args.output_format == "json":
        print(report_gen.json_report(results))
    elif args.output_format == "html":
        html = report_gen.html_report(results)
        output_path = args.output or "report.html"
        with open(output_path, "w") as f:
            f.write(html)
        print(f"HTML 报告已生成: {output_path}")
    else:
        print(report_gen.text_report(results))

    pool.close_all()

    if results["failed"] > 0:
        sys.exit(1)


def cmd_copy(args):
    """批量上传文件。"""
    inventory = Inventory.from_yaml(args.inventory)
    hosts = inventory.get_hosts(args.group) if args.group else inventory.get_hosts()

    pool = SSHConnectionPool()
    executor = RemoteExecutor(pool)
    config = ExecutionConfig(max_workers=args.workers, timeout=args.timeout)
    task_executor = TaskExecutor(executor, config)

    results = []
    for host in hosts:
        result = executor.upload_file(host, args.src, args.dest)
        results.append(result)
        print(f"{result}")

    success = sum(1 for r in results if r.success)
    print(f"\n上传完成: {success}/{len(results)} 成功")
    pool.close_all()


def cmd_info(args):
    """显示主机信息。"""
    inventory = Inventory.from_yaml(args.inventory)

    print(f"主机组: {', '.join(inventory.get_groups())}")
    print(f"主机总数: {len(inventory.get_hosts())}")
    print()

    for group in inventory.get_groups():
        hosts = inventory.get_hosts(group)
        print(f"[{group}] ({len(hosts)} 台)")
        for host in hosts:
            print(f"  {host.address}  tags={host.tags}")
        print()


def main():
    parser = argparse.ArgumentParser(description="SRE 批量管理工具")
    parser.add_argument("-f", "--inventory", required=True, help="主机清单文件")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # exec 子命令
    exec_parser = subparsers.add_parser("exec", help="执行远程命令")
    exec_parser.add_argument("-c", "--command", required=True, help="要执行的命令")
    exec_parser.add_argument("-g", "--group", help="目标主机组")
    exec_parser.add_argument("-p", "--pattern", help="主机名匹配模式")
    exec_parser.add_argument("-w", "--workers", type=int, default=10, help="并发数")
    exec_parser.add_argument("-t", "--timeout", type=int, default=30, help="超时时间")
    exec_parser.add_argument("--parallel", action="store_true", help="并行执行")
    exec_parser.add_argument("--fail-fast", action="store_true", help="失败快速停止")
    exec_parser.add_argument("--retries", type=int, default=0, help="重试次数")

    # playbook 子命令
    pb_parser = subparsers.add_parser("playbook", help="执行 Playbook")
    pb_parser.add_argument("-p", "--playbook", required=True, help="Playbook 文件")
    pb_parser.add_argument("-o", "--output", help="输出文件")
    pb_parser.add_argument("--output-format", choices=["text", "json", "html"],
                           default="text", help="输出格式")

    # copy 子命令
    copy_parser = subparsers.add_parser("copy", help="批量上传文件")
    copy_parser.add_argument("--src", required=True, help="本地文件路径")
    copy_parser.add_argument("--dest", required=True, help="远程目标路径")
    copy_parser.add_argument("-g", "--group", help="目标主机组")
    copy_parser.add_argument("-w", "--workers", type=int, default=10, help="并发数")
    copy_parser.add_argument("-t", "--timeout", type=int, default=60, help="超时时间")

    # info 子命令
    subparsers.add_parser("info", help="显示主机信息")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "exec": cmd_exec,
        "playbook": cmd_playbook,
        "copy": cmd_copy,
        "info": cmd_info,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
```

---

## 💻 实战练习

### 练习 1：实现一个服务健康检查工具

**要求**：
- 支持 TCP 端口检查
- 支持 HTTP 健康检查
- 支持自定义检查脚本
- 并行检查所有主机

<details>
<summary>参考答案</summary>

```python
import socket
import requests
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed


def check_tcp(host: str, port: int, timeout: int = 5) -> dict:
    """TCP 端口检查。"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return {
            "host": host,
            "check": f"tcp:{port}",
            "status": "ok" if result == 0 else "fail",
            "message": f"端口 {port} {'开放' if result == 0 else '关闭'}"
        }
    except Exception as e:
        return {"host": host, "check": f"tcp:{port}", "status": "fail",
                "message": str(e)}


def check_http(url: str, timeout: int = 5,
               expected_status: int = 200) -> dict:
    """HTTP 健康检查。"""
    try:
        resp = requests.get(url, timeout=timeout, verify=False)
        status = "ok" if resp.status_code == expected_status else "fail"
        return {
            "host": url,
            "check": "http",
            "status": status,
            "message": f"HTTP {resp.status_code}",
            "latency_ms": resp.elapsed.total_seconds() * 1000
        }
    except Exception as e:
        return {"host": url, "check": "http", "status": "fail",
                "message": str(e)}


def check_ssh(host: str, executor, command: str = "uptime") -> dict:
    """SSH 命令检查。"""
    result = executor.execute(HostInfo(hostname=host), command)
    return {
        "host": host,
        "check": "ssh",
        "status": "ok" if result.success else "fail",
        "message": result.stdout.strip()[:100] if result.success else result.error
    }


def batch_health_check(hosts: List[Dict], max_workers: int = 20) -> List[dict]:
    """批量健康检查。"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = []
        for host_cfg in hosts:
            check_type = host_cfg.get("type", "tcp")
            if check_type == "tcp":
                futures.append(pool.submit(
                    check_tcp, host_cfg["host"], host_cfg["port"]
                ))
            elif check_type == "http":
                futures.append(pool.submit(
                    check_http, host_cfg["url"]
                ))

        for future in as_completed(futures, timeout=30):
            results.append(future.result())

    return results
```
</details>

### 练习 2：实现配置文件分发工具

**要求**：
- 支持模板渲染（Jinja2 风格的变量替换）
- 支持分组差异化配置
- 配置变更前自动备份
- 支持回滚

<details>
<summary>参考答案</summary>

```python
import os
import re
import time
import hashlib
from typing import Dict


class ConfigDistributor:
    """配置文件分发器。"""

    def __init__(self, executor: RemoteExecutor):
        self.executor = executor

    def render_template(self, template: str, variables: Dict) -> str:
        """渲染模板。"""
        def replace_var(match):
            var_name = match.group(1).strip()
            return str(variables.get(var_name, match.group(0)))
        return re.sub(r'\{\{\s*(.+?)\s*\}\}', replace_var, template)

    def distribute(self, host: HostInfo, template_path: str,
                   remote_path: str, variables: Dict,
                   backup: bool = True) -> dict:
        """分发配置文件。"""
        # 读取模板
        with open(template_path) as f:
            template = f.read()

        # 渲染
        content = self.render_template(template, variables)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # 幂等检查
        check = self.executor.execute(host, f"md5sum {remote_path} 2>/dev/null")
        if check.success:
            remote_hash = check.stdout.split()[0]
            if remote_hash == content_hash:
                return {"changed": False, "msg": "配置文件无需更新"}

        # 备份
        if backup:
            backup_path = f"{remote_path}.bak.{int(time.time())}"
            self.executor.execute(host, f"cp {remote_path} {backup_path} 2>/dev/null")

        # 写入临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
            f.write(content)
            tmp_path = f.name

        try:
            # 上传
            result = self.executor.upload_file(host, tmp_path, remote_path)
            if not result.success:
                return {"changed": False, "msg": f"上传失败: {result.error}"}

            # 验证（可选的 reload 命令）
            return {"changed": True, "msg": f"配置已更新: {remote_path}"}
        finally:
            os.unlink(tmp_path)

    def rollback(self, host: HostInfo, remote_path: str) -> dict:
        """回滚到最近的备份。"""
        find = self.executor.execute(
            host, f"ls -t {remote_path}.bak.* 2>/dev/null | head -1"
        )
        if not find.success or not find.stdout.strip():
            return {"changed": False, "msg": "没有找到备份文件"}

        backup_path = find.stdout.strip()
        result = self.executor.execute(host, f"cp {backup_path} {remote_path}")
        return {
            "changed": result.success,
            "msg": f"已回滚到 {backup_path}" if result.success else "回滚失败"
        }
```
</details>

### 练习 3：实现滚动更新工具

**要求**：
- 支持配置批次大小
- 每批完成后自动健康检查
- 失败时自动回滚
- 支持暂停和恢复

<details>
<summary>参考答案</summary>

```python
import time
import logging
from typing import List, Callable

logger = logging.getLogger(__name__)


class RollingUpdater:
    """滚动更新器。"""

    def __init__(self, executor: RemoteExecutor, batch_size: int = 1):
        self.executor = executor
        self.batch_size = batch_size
        self._paused = False

    def update(self, hosts: List[HostInfo], deploy_func: Callable,
               health_check: Callable, rollback_func: Callable = None) -> dict:
        """执行滚动更新。

        参数：
        - hosts: 目标主机列表
        - deploy_func: 部署函数 (host) -> bool
        - health_check: 健康检查函数 (host) -> bool
        - rollback_func: 回滚函数 (host) -> None
        """
        results = {"success": [], "failed": [], "skipped": []}
        batches = [hosts[i:i+self.batch_size]
                   for i in range(0, len(hosts), self.batch_size)]

        for batch_idx, batch in enumerate(batches):
            logger.info(f"批次 {batch_idx + 1}/{len(batches)}: "
                       f"{[h.hostname for h in batch]}")

            # 等待暂停恢复
            while self._paused:
                time.sleep(1)

            batch_success = True
            for host in batch:
                try:
                    # 部署
                    logger.info(f"  部署 {host.hostname}...")
                    if not deploy_func(host):
                        raise Exception("部署函数返回失败")

                    # 健康检查
                    logger.info(f"  健康检查 {host.hostname}...")
                    if not health_check(host):
                        raise Exception("健康检查失败")

                    results["success"].append(host.hostname)
                    logger.info(f"  {host.hostname} 更新成功")

                except Exception as e:
                    logger.error(f"  {host.hostname} 更新失败: {e}")
                    results["failed"].append(host.hostname)
                    batch_success = False

                    # 回滚
                    if rollback_func:
                        logger.info(f"  回滚 {host.hostname}...")
                        try:
                            rollback_func(host)
                        except Exception as re:
                            logger.error(f"  回滚失败: {re}")

                    # 失败时停止后续批次
                    logger.error("批次失败，停止后续更新")
                    remaining = hosts[(batch_idx + 1) * self.batch_size:]
                    results["skipped"].extend([h.hostname for h in remaining])
                    return results

            # 批次间等待
            if batch_idx < len(batches) - 1:
                logger.info("批次完成，等待 10 秒...")
                time.sleep(10)

        return results

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
```
</details>

---

## 🎯 面试题精选

### 问题 1：Paramiko 连接池的作用是什么？如何实现？

**参考答案**：
连接池的作用：避免频繁建立 SSH 连接的开销（TCP 握手 + SSH 密钥交换），提升批量操作的性能。

实现要点：
1. 按主机分组管理连接
2. 使用线程锁保证线程安全
3. 使用上下文管理器自动归还连接
4. 归还前验证连接是否仍然活跃
5. 限制每台主机的最大连接数

### 问题 2：什么是幂等操作？在批量管理中为什么重要？

**参考答案**：
幂等操作是指执行一次和执行多次的结果相同。在批量管理中重要因为：
1. 网络中断可能导致操作重试
2. 需要安全地重复执行 Playbook
3. 调试时可以反复运行而不改变系统状态

实现方式：在执行前检查当前状态，只在需要时才执行变更。例如：安装软件前先检查是否已安装。

### 问题 3：如何实现类似 Ansible 的 when 条件判断？

**参考答案**：
实现方式：
1. 解析 when 表达式中的变量引用
2. 用当前变量值替换变量名
3. 使用安全的 eval 或 AST 解析器评估表达式
4. 返回 True/False 决定是否执行

安全注意事项：不应直接使用 eval，应使用受限的表达式解析器，防止代码注入。

### 问题 4：并发执行时如何控制失败快速停止（fail-fast）？

**参考答案**：
1. 使用 `concurrent.futures.as_completed` 监控任务完成情况
2. 一旦发现失败，调用 `Future.cancel()` 取消未开始的任务
3. 设置总超时时间
4. 对于串行模式，直接 break 循环

注意：已开始执行的任务无法取消，只能等待其完成或超时。

### 问题 5：Playbook 中的 register 关键字有什么作用？

**参考答案**：
register 将任务的执行结果注册到一个变量中，供后续任务引用。例如：
```yaml
- name: 检查文件是否存在
  command: test -f /etc/app.conf
  register: file_check

- name: 创建配置文件
  command: cp /etc/app.conf.default /etc/app.conf
  when: file_check.rc != 0
```

### 问题 6：如何实现滚动更新？需要注意什么？

**参考答案**：
滚动更新将更新过程分成多个批次，每批更新一小部分主机。关键点：
1. 配置批次大小（通常 1-2 台）
2. 每批完成后进行健康检查
3. 失败时停止并回滚已更新的主机
4. 批次间设置等待时间

注意事项：确保有负载均衡器将流量从更新中的主机移走。

### 问题 7：SSH 连接超时应该如何设置？

**参考答案**：
超时设置应分层：
1. **TCP 连接超时**：5-10 秒（检测主机不可达）
2. **SSH 认证超时**：10 秒（检测 SSH 服务问题）
3. **命令执行超时**：根据命令类型（简单命令 30 秒，安装软件 300 秒）
4. **总超时**：连接超时 + 执行超时 + 缓冲

建议使用指数退避重试，避免网络抖动导致误报。

### 问题 8：如何保证批量操作的安全性？

**参考答案**：
1. **Dry-run 模式**：预演执行，不实际变更
2. **确认机制**：执行前显示影响范围，要求确认
3. **回滚支持**：每个变更前备份，失败时自动回滚
4. **审计日志**：记录所有操作的详细日志
5. **权限控制**：限制可执行的命令和可操作的主机
6. **限速控制**：限制并发数，避免对目标主机造成压力

### 问题 9：Inventory 系统如何支持动态主机发现？

**参考答案**：
1. **静态文件**：YAML/INI 格式的主机清单
2. **脚本动态生成**：调用外部脚本获取主机列表
3. **云 API 集成**：从 AWS EC2、阿里云 ECS 等动态获取
4. **CMDB 集成**：从配置管理数据库查询
5. **DNS 服务发现**：通过 DNS SRV 记录发现主机

关键接口：`get_hosts()` 方法返回统一的 HostInfo 列表。

### 问题 10：如何测试批量管理工具？

**参考答案**：
1. **单元测试**：Mock SSH 连接，测试各模块逻辑
2. **集成测试**：使用 Docker 容器模拟多台主机
3. **Dry-run 测试**：验证 Playbook 解析和条件判断
4. **性能测试**：测试大规模主机（100+）的并发执行
5. **故障注入测试**：模拟网络中断、SSH 超时等异常

---

## 📚 深入阅读

### 官方文档
- [Paramiko 文档](https://docs.paramiko.org/)
- [Python concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html)
- [Ansible 官方文档](https://docs.ansible.com/)（参考设计思路）
- [fabric 文档](https://www.fabfile.org/)（Paramiko 的高级封装）

### 推荐书籍
- 《Python for DevOps》— Noah Gift（自动化和批量管理章节）
- 《Ansible: Up and Running》— Lorin Hochstein（Playbook 设计参考）
- 《Infrastructure as Code》— Kief Morris（基础设施自动化理念）

### 技术博客
- [Paramiko 最佳实践](https://docs.paramiko.org/en/stable/)
- [SSH 批量管理工具对比](https://github.com/ansible/ansible)
- [幂等性设计模式](https://restfulapi.net/idempotent-rest-apis/)

---

## ✅ 自检清单

### 理论检查
- [ ] 能解释 SSH 连接池的工作原理和优势
- [ ] 能解释幂等操作的概念和实现方式
- [ ] 能解释 Playbook 中各关键字的含义
- [ ] 能解释并发执行的 fail-fast 机制
- [ ] 能解释滚动更新的实现策略

### 实操检查
- [ ] 能使用 Paramiko 实现 SSH 连接和命令执行
- [ ] 能实现并发执行引擎（并行和串行）
- [ ] 能解析 YAML 格式的主机清单和 Playbook
- [ ] 能实现模块系统（command, copy, systemd, apt）
- [ ] 能生成文本、JSON、HTML 格式的执行报告

### 能力验证
- [ ] 能独立完成批量管理工具的开发
- [ ] 能编写 Playbook 实现自动化部署
- [ ] 能处理批量操作中的异常和回滚
