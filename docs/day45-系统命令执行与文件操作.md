# Day 45: 系统命令执行与文件操作

> 📅 日期：2026-05-03
> 📖 学习主题：subprocess / os / pathlib / shutil / 信号处理 / 临时文件 / 文件锁
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 43 Python 环境搭建, Day 44 数据类型与配置文件处理

## 🎯 学习目标

- 掌握 subprocess 模块执行系统命令，理解其安全模型和最佳实践
- 熟练使用 pathlib 替代 os.path 进行文件路径操作
- 掌握 shutil 进行文件/目录的高级操作
- 理解信号处理机制，能编写优雅关闭的 SRE 服务
- 掌握临时文件管理和文件锁，避免并发操作的竞态条件

---

## 📖 核心知识点

### 1. subprocess — 执行系统命令

#### 1.1 为什么需要 subprocess？

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python 执行系统命令的演进                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  os.system()        → 已废弃，无法捕获输出，安全风险             │
│  os.popen()         → 已废弃，管道处理有限                       │
│  commands模块       → Python 2 已移除                           │
│  subprocess         → 推荐方案，安全、灵活、功能完整             │
│                                                                 │
│  subprocess 的优势:                                             │
│    1. 安全：避免 shell 注入（不经过 shell 解析）                │
│    2. 灵活：分别控制 stdin/stdout/stderr                        │
│    3. 可靠：超时控制、返回码检查                                │
│    4. 并发：支持异步执行                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 subprocess.run() — 推荐的现代 API

```python
import subprocess
import shlex
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


# ============================================
# 基础用法
# ============================================

# 最简单的用法
result = subprocess.run(
    ["ls", "-la", "/var/log"],
    capture_output=True,  # 捕获 stdout 和 stderr
    text=True,            # 以字符串返回（而非 bytes）
    timeout=30,           # 超时时间（秒）
)
print(f"Return code: {result.returncode}")
print(f"Stdout:\n{result.stdout}")
print(f"Stderr:\n{result.stderr}")


# ============================================
# 安全执行 — 避免 shell 注入
# ============================================

# 正确：使用列表形式，不经过 shell 解析
hostname = "web-01"
result = subprocess.run(
    ["ping", "-c", "3", hostname],  # 每个参数独立传递
    capture_output=True,
    text=True,
)

# 危险：使用 shell=True，用户输入可能被注入
# 如果 hostname = "; rm -rf /"，则实际执行: ping -c 3 ; rm -rf /
# result = subprocess.run(
#     f"ping -c 3 {hostname}",  # 不要这样做!
#     shell=True,
# )


# ============================================
# 安全处理用户输入 — 使用 shlex.quote
# ============================================

def safe_execute(command: str, *args: str) -> subprocess.CompletedProcess:
    """
    安全执行命令 — 对用户输入进行转义

    Args:
        command: 命令名
        args: 命令参数

    Returns:
        CompletedProcess 对象
    """
    # 对每个参数进行 shell 转义
    safe_args = [shlex.quote(arg) for arg in args]
    cmd_list = [command] + list(args)  # 使用列表形式，不需要转义
    return subprocess.run(
        cmd_list,
        capture_output=True,
        text=True,
        timeout=30,
    )


# ============================================
# 检查返回码
# ============================================

def run_checked(command: List[str], timeout: int = 30) -> str:
    """
    执行命令并检查返回码

    Args:
        command: 命令列表
        timeout: 超时时间

    Returns:
        标准输出内容

    Raises:
        subprocess.CalledProcessError: 命令返回非零退出码
        subprocess.TimeoutExpired: 命令超时
    """
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,  # 非零退出码自动抛出异常
    )
    return result.stdout
```

#### 1.3 subprocess 高级用法

```python
import subprocess
import time
from typing import Generator, Optional, Tuple
from threading import Thread
import select


# ============================================
# 管道连接 — 命令串联
# ============================================

def pipe_commands(*commands: List[str]) -> str:
    """
    连接多个命令的管道

    等价于: cmd1 | cmd2 | cmd3

    Args:
        commands: 命令列表的列表

    Returns:
        最终命令的输出
    """
    processes = []
    for i, cmd in enumerate(commands):
        # 除了最后一个，都把 stdout 连接到下一个的 stdin
        stdin = processes[-1].stdout if processes else None
        p = subprocess.Popen(
            cmd,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        processes.append(p)

    # 等待所有进程完成
    stdout, stderr = processes[-1].communicate()

    # 检查所有进程的返回码
    for p in processes:
        p.wait()
        if p.returncode != 0:
            raise subprocess.CalledProcessError(
                p.returncode, p.args, stderr=stderr
            )

    return stdout


# 示例: ps aux | grep python | wc -l
count = pipe_commands(
    ["ps", "aux"],
    ["grep", "python"],
    ["wc", "-l"],
)
print(f"Python processes: {count.strip()}")


# ============================================
# 实时输出 — 流式处理长时间运行的命令
# ============================================

def run_with_live_output(
    command: List[str],
    timeout: Optional[int] = None,
) -> Generator[str, None, None]:
    """
    执行命令并实时产出每一行输出

    SRE 场景：执行长时间运行的部署脚本，实时显示进度

    Args:
        command: 命令列表
        timeout: 超时时间

    Yields:
        每一行输出
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
        text=True,
        bufsize=1,  # 行缓冲
    )

    start_time = time.time()

    try:
        while True:
            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                process.kill()
                raise subprocess.TimeoutExpired(command, timeout)

            line = process.stdout.readline()
            if line:
                yield line.rstrip("\n")
            elif process.poll() is not None:
                break
    finally:
        process.stdout.close()
        process.wait()


# 使用示例
for line in run_with_live_output(["ping", "-c", "5", "localhost"]):
    print(f"[{time.strftime('%H:%M:%S')}] {line}")


# ============================================
# 后台执行 — 异步运行命令
# ============================================

class BackgroundProcess:
    """
    后台进程管理器

    SRE 场景：启动后台服务、监控脚本等
    """

    def __init__(self, command: List[str]) -> None:
        self._command = command
        self._process: Optional[subprocess.Popen] = None
        self._output_lines: list[str] = []
        self._reader_thread: Optional[Thread] = None

    def start(self) -> None:
        """启动后台进程"""
        self._process = subprocess.Popen(
            self._command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        # 启动读取线程
        self._reader_thread = Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()

    def _read_output(self) -> None:
        """读取输出的后台线程"""
        for line in self._process.stdout:
            self._output_lines.append(line.rstrip("\n"))

    def is_running(self) -> bool:
        """检查进程是否还在运行"""
        return self._process is not None and self._process.poll() is None

    def get_output(self) -> list[str]:
        """获取已收集的输出"""
        return self._output_lines.copy()

    def stop(self, timeout: int = 10) -> int:
        """
        停止进程（先 SIGTERM，超时后 SIGKILL）

        Returns:
            进程退出码
        """
        if self._process is None:
            return -1

        import signal
        self._process.send_signal(signal.SIGTERM)
        try:
            return self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._process.kill()
            return self._process.wait()

    def wait(self, timeout: Optional[int] = None) -> int:
        """等待进程完成"""
        if self._process is None:
            return -1
        return self._process.wait(timeout=timeout)


# 使用示例
bg = BackgroundProcess(["python3", "-m", "http.server", "8080"])
bg.start()
print(f"Server running: {bg.is_running()}")
time.sleep(2)
output = bg.get_output()
exit_code = bg.stop()
print(f"Server stopped with code: {exit_code}")
```

#### 1.4 SRE 实战：服务器批量操作工具

```python
#!/usr/bin/env python3
"""
SRE 批量服务器操作工具

功能：
1. 批量执行命令
2. 批量文件分发
3. 批量健康检查
"""
import subprocess
import concurrent.futures
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CommandResult:
    """命令执行结果"""
    host: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration: float
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.returncode == 0 and self.error is None


@dataclass
class BatchExecutor:
    """
    批量命令执行器

    SRE 场景：在服务器集群上执行批量操作
    """

    hosts: List[str]
    max_workers: int = 10
    ssh_timeout: int = 30
    command_timeout: int = 60
    ssh_options: Dict[str, str] = field(default_factory=lambda: {
        "StrictHostKeyChecking": "no",
        "ConnectTimeout": "10",
    })

    def _build_ssh_command(self, host: str, command: str) -> List[str]:
        """构建 SSH 命令"""
        ssh_cmd = ["ssh"]
        for key, value in self.ssh_options.items():
            ssh_cmd.extend(["-o", f"{key}={value}"])
        ssh_cmd.extend([host, command])
        return ssh_cmd

    def execute(self, host: str, command: str) -> CommandResult:
        """
        在单台主机上执行命令

        Args:
            host: 主机名或 IP
            command: 要执行的命令

        Returns:
            CommandResult 对象
        """
        ssh_cmd = self._build_ssh_command(host, command)
        start_time = datetime.now()

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=self.command_timeout,
            )
            duration = (datetime.now() - start_time).total_seconds()

            return CommandResult(
                host=host,
                command=command,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
            )
        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            return CommandResult(
                host=host,
                command=command,
                returncode=-1,
                stdout="",
                stderr="",
                duration=duration,
                error=f"Command timed out after {self.command_timeout}s",
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return CommandResult(
                host=host,
                command=command,
                returncode=-1,
                stdout="",
                stderr="",
                duration=duration,
                error=str(e),
            )

    def execute_batch(
        self,
        command: str,
        hosts: Optional[List[str]] = None,
    ) -> List[CommandResult]:
        """
        在多台主机上并行执行命令

        Args:
            command: 要执行的命令
            hosts: 主机列表（默认使用 self.hosts）

        Returns:
            CommandResult 列表
        """
        target_hosts = hosts or self.hosts
        results: List[CommandResult] = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = {
                executor.submit(self.execute, host, command): host
                for host in target_hosts
            }

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)

        # 按主机名排序
        results.sort(key=lambda r: r.host)
        return results

    def health_check(self, port: int = 22) -> Dict[str, bool]:
        """
        批量 SSH 连通性检查

        Args:
            port: SSH 端口

        Returns:
            {host: is_reachable}
        """
        results = self.execute_batch(f"echo OK")
        return {r.host: r.success for r in results}

    def get_system_info(self) -> List[Dict[str, Any]]:
        """
        批量获取系统信息

        Returns:
            系统信息列表
        """
        command = (
            "uname -n && "
            "cat /etc/os-release | head -2 && "
            "free -h | grep Mem && "
            "df -h / | tail -1 && "
            "python3 --version 2>/dev/null || echo 'Python not found'"
        )

        results = self.execute_batch(command)
        system_info = []

        for r in results:
            if r.success:
                lines = r.stdout.strip().split("\n")
                system_info.append({
                    "host": r.host,
                    "hostname": lines[0] if lines else "unknown",
                    "os": lines[1] if len(lines) > 1 else "unknown",
                    "memory": lines[2] if len(lines) > 2 else "unknown",
                    "disk": lines[3] if len(lines) > 3 else "unknown",
                    "python": lines[4] if len(lines) > 4 else "unknown",
                })
            else:
                system_info.append({
                    "host": r.host,
                    "error": r.error or r.stderr,
                })

        return system_info


# 使用示例
if __name__ == "__main__":
    hosts = ["web-01", "web-02", "api-01", "api-02", "worker-01"]
    executor = BatchExecutor(hosts=hosts, max_workers=5)

    # 批量检查 Python 版本
    print("=== Python Version Check ===")
    results = executor.execute_batch("python3 --version")
    for r in results:
        status = "OK" if r.success else "FAIL"
        print(f"  [{status}] {r.host}: {r.stdout.strip() or r.error}")

    # 批量健康检查
    print("\n=== Health Check ===")
    health = executor.health_check()
    for host, is_ok in health.items():
        status = "UP" if is_ok else "DOWN"
        print(f"  [{status}] {host}")
```

---

### 2. pathlib — 现代文件路径操作

#### 2.1 为什么用 pathlib 替代 os.path？

```
┌─────────────────────────────────────────────────────────────────┐
│                    os.path vs pathlib 对比                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  os.path (旧风格):                                              │
│    import os.path                                               │
│    path = os.path.join("/var", "log", "app.log")               │
│    exists = os.path.exists(path)                                │
│    size = os.path.getsize(path)                                 │
│    name = os.path.basename(path)                                │
│    ext = os.path.splitext(path)[1]                              │
│    parent = os.path.dirname(path)                               │
│                                                                 │
│  pathlib (新风格):                                               │
│    from pathlib import Path                                     │
│    path = Path("/var/log/app.log")                              │
│    exists = path.exists()                                       │
│    size = path.stat().st_size                                   │
│    name = path.name                                             │
│    ext = path.suffix                                            │
│    parent = path.parent                                         │
│                                                                 │
│  pathlib 的优势:                                                │
│    1. 面向对象 — 方法挂载在 Path 对象上                         │
│    2. 跨平台 — 自动处理路径分隔符                               │
│    3. 可读性 — 链式调用更直观                                   │
│    4. 类型安全 — IDE 自动补全                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 pathlib 核心操作

```python
from pathlib import Path, PurePosixPath
from typing import List, Optional
import os
import glob


# ============================================
# 创建 Path 对象
# ============================================

# 绝对路径
log_dir = Path("/var/log")

# 相对路径（相对于当前工作目录）
config_file = Path("config/app.yaml")

# 家目录
home = Path.home()  # /home/user

# 当前目录
cwd = Path.cwd()

# 从多个部分拼接
app_log = Path("/var/log") / "myapp" / "app.log"  # /var/log/myapp/app.log

# 展开 ~ 和环境变量
expanded = Path("~/logs").expanduser()  # /home/user/logs


# ============================================
# 路径属性
# ============================================

path = Path("/var/log/nginx/access.log")

print(path.name)       # access.log (文件名)
print(path.stem)       # access (不含扩展名)
print(path.suffix)     # .log (扩展名)
print(path.suffixes)   # ['.log'] (所有扩展名)
print(path.parent)     # /var/log/nginx (父目录)
print(path.parents)    # [PosixPath('/var/log/nginx'), ...] (所有祖先)
print(path.parts)      # ('/', 'var', 'log', 'nginx', 'access.log')
print(path.anchor)     # / (根)


# ============================================
# 文件操作
# ============================================

# 检查存在性
path = Path("/var/log/nginx/access.log")
path.exists()          # 是否存在
path.is_file()         # 是否是文件
path.is_dir()          # 是否是目录
path.is_symlink()      # 是否是符号链接
path.is_absolute()     # 是否是绝对路径

# 文件信息
stat = path.stat()
stat.st_size           # 文件大小（字节）
stat.st_mtime          # 修改时间
stat.st_ctime          # 创建时间
stat.st_mode           # 权限模式

# 读写文件
content = path.read_text(encoding="utf-8")      # 读取文本
content = path.read_bytes()                       # 读取二进制
path.write_text("Hello, World!", encoding="utf-8")  # 写入文本
path.write_bytes(b"\x00\x01\x02")                # 写入二进制

# 目录操作
path.mkdir(parents=True, exist_ok=True)  # 创建目录（含父目录）
path.rmdir()                              # 删除空目录
path.unlink()                             # 删除文件
path.unlink(missing_ok=True)              # 删除文件，不存在也不报错

# 重命名/移动
path.rename("/var/log/nginx/old_access.log")

# 复制（需要 shutil）
import shutil
shutil.copy2(path, "/backup/access.log")


# ============================================
# 目录遍历
# ============================================

log_dir = Path("/var/log")

# 列出目录内容
for item in log_dir.iterdir():
    print(item.name, item.stat().st_size)

# 递归搜索 (glob)
for py_file in Path("/opt/app").rglob("*.py"):
    print(py_file)

# 模式匹配
for log_file in log_dir.glob("*.log"):
    print(log_file)

# 带过滤的遍历
for item in log_dir.iterdir():
    if item.is_file() and item.suffix == ".log":
        size_mb = item.stat().st_size / (1024 * 1024)
        if size_mb > 100:
            print(f"Large log: {item} ({size_mb:.1f} MB)")


# ============================================
# SRE 实战：日志目录管理
# ============================================

class LogManager:
    """
    日志目录管理器

    SRE 功能：
    1. 查找大日志文件
    2. 清理旧日志
    3. 统计日志目录使用情况
    """

    def __init__(self, log_dir: Path) -> None:
        self._log_dir = log_dir

    def find_large_logs(self, threshold_mb: float = 100) -> List[Path]:
        """查找超过阈值的日志文件"""
        threshold_bytes = threshold_mb * 1024 * 1024
        large_logs = []

        if not self._log_dir.exists():
            return large_logs

        for log_file in self._log_dir.rglob("*.log"):
            if log_file.is_file() and log_file.stat().st_size > threshold_bytes:
                large_logs.append(log_file)

        return sorted(large_logs, key=lambda p: p.stat().st_size, reverse=True)

    def cleanup_old_logs(self, days: int = 30, dry_run: bool = True) -> List[Path]:
        """
        清理超过指定天数的日志文件

        Args:
            days: 保留天数
            dry_run: 是否只预览不实际删除

        Returns:
            被删除（或预览将删除）的文件列表
        """
        import time
        cutoff_time = time.time() - (days * 86400)
        removed = []

        for log_file in self._log_dir.rglob("*"):
            if log_file.is_file() and log_file.stat().st_mtime < cutoff_time:
                removed.append(log_file)
                if not dry_run:
                    log_file.unlink()

        return removed

    def get_usage_stats(self) -> dict:
        """获取日志目录使用统计"""
        total_size = 0
        file_count = 0
        by_extension: dict = {}

        if not self._log_dir.exists():
            return {"total_size_mb": 0, "file_count": 0, "by_extension": {}}

        for item in self._log_dir.rglob("*"):
            if item.is_file():
                size = item.stat().st_size
                total_size += size
                file_count += 1
                ext = item.suffix or "(no ext)"
                by_extension[ext] = by_extension.get(ext, 0) + size

        return {
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "by_extension": {
                ext: round(size / (1024 * 1024), 2)
                for ext, size in sorted(by_extension.items(), key=lambda x: -x[1])
            },
        }
```

---

### 3. shutil — 高级文件操作

```python
import shutil
from pathlib import Path
from typing import Optional, Callable
import os


# ============================================
# 文件复制
# ============================================

# 复制文件（保留元数据）
shutil.copy2("/src/file.txt", "/dst/file.txt")

# 复制文件（不保留元数据）
shutil.copy("/src/file.txt", "/dst/file.txt")

# 复制文件到目录
shutil.copy2("/src/file.txt", "/dst/")  # → /dst/file.txt

# 复制目录树
shutil.copytree("/src/dir", "/dst/dir")

# 复制目录树（忽略特定文件）
shutil.copytree(
    "/src/dir",
    "/dst/dir",
    ignore=shutil.ignore_patterns("*.pyc", "__pycache__", ".git"),
)


# ============================================
# 文件移动
# ============================================

# 移动文件/目录
shutil.move("/src/file.txt", "/dst/file.txt")

# 移动目录
shutil.move("/src/dir", "/dst/dir")


# ============================================
# 目录删除
# ============================================

# 删除整个目录树（危险！）
shutil.rmtree("/tmp/old_dir")

# 安全删除（带 onerror 回调）
def on_rm_error(func, path, exc_info):
    """处理删除错误（如权限不足）"""
    import stat
    # 尝试修改权限后重试
    os.chmod(path, stat.S_IWRITE)
    func(path)

shutil.rmtree("/tmp/old_dir", onerror=on_rm_error)


# ============================================
# 磁盘使用情况
# ============================================

def get_disk_usage(path: str = "/") -> dict:
    """
    获取磁盘使用情况

    Args:
        path: 要检查的路径

    Returns:
        磁盘使用信息字典
    """
    usage = shutil.disk_usage(path)
    return {
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
        "used_percent": round(usage.used / usage.total * 100, 1),
    }


# ============================================
# SRE 实战：安全备份工具
# ============================================

class BackupManager:
    """
    安全备份管理器

    SRE 场景：配置文件备份、日志归档
    """

    def __init__(self, backup_dir: Path) -> None:
        self._backup_dir = backup_dir
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_file(
        self,
        source: Path,
        suffix: Optional[str] = None,
    ) -> Path:
        """
        备份单个文件

        Args:
            source: 源文件路径
            suffix: 备份文件后缀（默认使用时间戳）

        Returns:
            备份文件路径
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        from datetime import datetime
        timestamp = suffix or datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source.name}.{timestamp}"
        backup_path = self._backup_dir / backup_name

        shutil.copy2(source, backup_path)
        return backup_path

    def backup_directory(
        self,
        source: Path,
        exclude_patterns: Optional[list] = None,
    ) -> Path:
        """
        备份整个目录

        Args:
            source: 源目录路径
            exclude_patterns: 排除的文件模式

        Returns:
            备份目录路径
        """
        if not source.exists():
            raise FileNotFoundError(f"Source directory not found: {source}")

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source.name}.{timestamp}"
        backup_path = self._backup_dir / backup_name

        ignore_patterns = exclude_patterns or [
            "*.pyc", "__pycache__", ".git", ".venv", "node_modules",
        ]

        shutil.copytree(
            source,
            backup_path,
            ignore=shutil.ignore_patterns(*ignore_patterns),
        )
        return backup_path

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """清理超过保留天数的备份"""
        import time
        cutoff_time = time.time() - (keep_days * 86400)
        removed_count = 0

        for item in self._backup_dir.iterdir():
            if item.stat().st_mtime < cutoff_time:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                removed_count += 1

        return removed_count
```

---

### 4. os 模块 — 系统交互

```python
import os
import stat
from pathlib import Path
from typing import Dict, List, Optional


# ============================================
# 环境变量
# ============================================

# 获取环境变量
home = os.environ.get("HOME", "/root")
path = os.environ.get("PATH", "")
log_level = os.environ.get("LOG_LEVEL", "INFO")

# 设置环境变量（当前进程）
os.environ["APP_ENV"] = "production"

# 获取所有环境变量
all_env = dict(os.environ)

# SRE 场景：获取主机名和 IP
hostname = os.environ.get("HOSTNAME", os.uname().nodename)


# ============================================
# 进程信息
# ============================================

pid = os.getpid()          # 当前进程 PID
ppid = os.getppid()        # 父进程 PID
uid = os.getuid()          # 当前用户 UID
gid = os.getgid()          # 当前用户组 GID
uname = os.uname()         # 系统信息


# ============================================
# 文件权限操作
# ============================================

def set_secure_permissions(path: Path, is_dir: bool = False) -> None:
    """
    设置安全的文件权限

    SRE 最佳实践：
    - 配置文件: 600 (只有 owner 可读写)
    - 配置目录: 700 (只有 owner 可访问)
    - 日志文件: 640 (owner 可读写，group 可读)
    """
    if is_dir:
        os.chmod(path, stat.S_IRWXU)  # 700
    else:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 600


def check_file_permissions(path: Path) -> Dict[str, bool]:
    """检查文件权限是否安全"""
    if not path.exists():
        return {"exists": False}

    st = path.stat()
    mode = st.st_mode

    return {
        "exists": True,
        "owner_readable": bool(mode & stat.S_IRUSR),
        "owner_writable": bool(mode & stat.S_IWUSR),
        "owner_executable": bool(mode & stat.S_IXUSR),
        "group_readable": bool(mode & stat.S_IRGRP),
        "group_writable": bool(mode & stat.S_IWGRP),
        "world_readable": bool(mode & stat.S_IROTH),
        "world_writable": bool(mode & stat.S_IWOTH),
        "is_secure": not (mode & stat.S_IWOTH),  # 没有 world 可写
    }


# ============================================
# SRE 实战：系统信息采集
# ============================================

def collect_system_info() -> Dict[str, str]:
    """采集系统基本信息"""
    import platform

    info = {
        "hostname": os.uname().nodename,
        "os": platform.system(),
        "os_version": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "pid": str(os.getpid()),
        "uid": str(os.getuid()),
        "home": os.environ.get("HOME", "unknown"),
        "shell": os.environ.get("SHELL", "unknown"),
        "path": os.environ.get("PATH", "unknown"),
    }

    # 尝试获取更多系统信息
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["os_pretty_name"] = line.split("=", 1)[1].strip().strip('"')
                    break
    except (FileNotFoundError, PermissionError):
        pass

    return info
```

---

### 5. 信号处理 — 优雅关闭

#### 5.1 信号机制原理

```
┌─────────────────────────────────────────────────────────────────┐
│                    Linux 信号机制                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  信号是进程间通信 (IPC) 的一种方式                               │
│  用于通知进程发生了某个事件                                      │
│                                                                 │
│  常见信号:                                                      │
│  ┌──────────┬──────┬─────────────────────────────────┐          │
│  │ 信号名   │ 编号 │ 说明                            │          │
│  ├──────────┼──────┼─────────────────────────────────┤          │
│  │ SIGHUP   │  1   │ 终端挂起 / 配置重载             │          │
│  │ SIGINT   │  2   │ Ctrl+C 中断                    │          │
│  │ SIGQUIT  │  3   │ Ctrl+\ 退出并生成 core dump    │          │
│  │ SIGKILL  │  9   │ 强制终止（无法捕获）            │          │
│  │ SIGTERM  │ 15   │ 优雅终止（默认 kill 信号）      │          │
│  │ SIGUSR1  │ 10   │ 用户自定义信号 1               │          │
│  │ SIGUSR2  │ 12   │ 用户自定义信号 2               │          │
│  └──────────┴──────┴─────────────────────────────────┘          │
│                                                                 │
│  SRE 场景:                                                      │
│    SIGTERM → Kubernetes Pod 删除时发送                          │
│    SIGHUP  → Nginx 配置重载                                     │
│    SIGUSR1 → 日志轮转触发                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.2 Python 信号处理

```python
import signal
import sys
import time
import logging
from typing import Callable, Optional
from datetime import datetime


class GracefulShutdown:
    """
    优雅关闭管理器

    SRE 场景：处理 SIGTERM 信号，确保服务优雅关闭
    - 停止接收新请求
    - 等待正在处理的请求完成
    - 关闭数据库连接
    - 清理临时文件
    """

    def __init__(self) -> None:
        self._shutdown_requested = False
        self._shutdown_callbacks: list[Callable[[], None]] = []
        self._logger = logging.getLogger(__name__)

    def register_callback(self, callback: Callable[[], None]) -> None:
        """注册关闭回调函数"""
        self._shutdown_callbacks.append(callback)

    def request_shutdown(self, signum: int, frame: Optional[object]) -> None:
        """信号处理函数"""
        signal_name = signal.Signals(signum).name
        self._logger.info(f"Received {signal_name}, initiating graceful shutdown...")
        self._shutdown_requested = True

    def setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        # SIGTERM — Kubernetes 删除 Pod 时发送
        signal.signal(signal.SIGTERM, self.request_shutdown)
        # SIGINT — Ctrl+C
        signal.signal(signal.SIGINT, self.request_shutdown)
        # SIGHUP — 配置重载（通常用）
        signal.signal(signal.SIGHUP, self._handle_reload)

    def _handle_reload(self, signum: int, frame: Optional[object]) -> None:
        """处理 SIGHUP — 配置重载"""
        self._logger.info("Received SIGHUP, reloading configuration...")
        # 这里可以触发配置重新加载
        # reload_config()

    @property
    def should_shutdown(self) -> bool:
        """检查是否应该关闭"""
        return self._shutdown_requested

    def wait_for_shutdown(self, check_interval: float = 1.0) -> None:
        """等待关闭信号"""
        while not self._shutdown_requested:
            time.sleep(check_interval)

        self._execute_shutdown()

    def _execute_shutdown(self) -> None:
        """执行关闭回调"""
        self._logger.info("Executing shutdown callbacks...")
        for callback in self._shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                self._logger.error(f"Shutdown callback failed: {e}")
        self._logger.info("Shutdown complete")


# SRE 实战：带优雅关闭的监控服务
def run_monitoring_service() -> None:
    """运行监控服务，支持优雅关闭"""
    shutdown = GracefulShutdown()
    shutdown.setup_signal_handlers()

    # 注册关闭回调
    def cleanup_database():
        print("Closing database connections...")

    def cleanup_temp_files():
        print("Cleaning up temporary files...")

    def flush_metrics():
        print("Flushing metrics to storage...")

    shutdown.register_callback(cleanup_database)
    shutdown.register_callback(cleanup_temp_files)
    shutdown.register_callback(flush_metrics)

    print("Monitoring service started. Press Ctrl+C to stop.")

    # 主循环
    while not shutdown.should_shutdown:
        # 采集指标
        print(f"[{datetime.now()}] Collecting metrics...")
        time.sleep(5)

    print("Service stopped gracefully.")


# SIGHUP 配置重载示例
class ReloadableService:
    """支持 SIGHUP 配置重载的服务"""

    def __init__(self) -> None:
        self._config: dict = {}
        self._config_path = "/etc/myapp/config.yaml"

    def _reload_config(self, signum: int, frame: Optional[object]) -> None:
        """SIGHUP 处理函数 — 重新加载配置"""
        import yaml
        try:
            with open(self._config_path) as f:
                self._config = yaml.safe_load(f)
            print(f"Configuration reloaded from {self._config_path}")
        except Exception as e:
            print(f"Failed to reload config: {e}")

    def run(self) -> None:
        """运行服务"""
        signal.signal(signal.SIGHUP, self._reload_config)

        # 初始加载配置
        self._reload_config(None, None)

        # 主循环
        while True:
            # 使用 self._config 做业务逻辑
            time.sleep(1)
```

---

### 6. 临时文件管理

```python
import tempfile
import os
from pathlib import Path
from typing import Optional, Generator
from contextlib import contextmanager


# ============================================
# 临时文件/目录的基本用法
# ============================================

# 创建临时文件（自动删除）
with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=True) as f:
    f.write("log data\n")
    print(f"Temp file: {f.name}")
    # 退出 with 块后文件自动删除

# 创建临时文件（不自动删除）
with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
    temp_path = f.name
    f.write("log data\n")
# 需要手动删除
os.unlink(temp_path)

# 创建临时目录
with tempfile.TemporaryDirectory(prefix="sre-") as tmpdir:
    print(f"Temp dir: {tmpdir}")
    # 在临时目录中创建文件
    (Path(tmpdir) / "test.txt").write_text("hello")
    # 退出 with 块后目录及其内容自动删除


# ============================================
# SRE 实战：安全的临时文件操作
# ============================================

@contextmanager
def secure_temp_file(
    suffix: str = ".tmp",
    prefix: str = "sre-",
    mode: str = "w",
    dir: Optional[str] = None,
) -> Generator[Path, None, None]:
    """
    安全的临时文件上下文管理器

    确保：
    1. 文件权限为 600（只有 owner 可读写）
    2. 异常时自动清理
    3. 返回 Path 对象而非文件对象

    Args:
        suffix: 文件后缀
        prefix: 文件前缀
        mode: 打开模式
        dir: 临时文件目录

    Yields:
        临时文件的 Path 对象
    """
    import stat

    tmp_file = tempfile.NamedTemporaryFile(
        mode=mode,
        suffix=suffix,
        prefix=prefix,
        dir=dir,
        delete=False,
    )
    tmp_path = Path(tmp_file.name)

    try:
        # 设置安全权限
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 600
        tmp_file.close()
        yield tmp_path
    finally:
        # 确保清理
        if tmp_path.exists():
            tmp_path.unlink()


@contextmanager
def secure_temp_directory(
    prefix: str = "sre-",
    suffix: str = "",
    dir: Optional[str] = None,
) -> Generator[Path, None, None]:
    """
    安全的临时目录上下文管理器

    Yields:
        临时目录的 Path 对象
    """
    import stat

    tmp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=dir)
    tmp_path = Path(tmp_dir)

    try:
        # 设置安全权限
        os.chmod(tmp_path, stat.S_IRWXU)  # 700
        yield tmp_path
    finally:
        import shutil
        if tmp_path.exists():
            shutil.rmtree(tmp_path)


# SRE 场景：安全地生成临时配置文件
def generate_temp_config(config_data: dict) -> Path:
    """
    生成临时配置文件

    SRE 场景：运行时生成临时配置，程序退出后自动清理
    """
    import yaml

    with secure_temp_file(suffix=".yaml", prefix="sre-config-") as tmp_path:
        tmp_path.write_text(yaml.dump(config_data, default_flow_style=False))
        return tmp_path
```

---

### 7. 文件锁 — 并发安全

```python
import fcntl
import os
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager


# ============================================
# 文件锁基础
# ============================================

@contextmanager
def file_lock(
    lock_path: Path,
    timeout: float = 30.0,
    poll_interval: float = 0.1,
):
    """
    文件锁上下文管理器

    使用 fcntl.flock() 实现进程级文件锁

    Args:
        lock_path: 锁文件路径
        timeout: 等待超时时间（秒）
        poll_interval: 轮询间隔（秒）

    Yields:
        锁文件的文件描述符

    Raises:
        TimeoutError: 等待锁超时
    """
    lock_fd = None
    try:
        lock_fd = open(lock_path, "w")
        start_time = time.time()

        while True:
            try:
                # 非阻塞尝试获取锁
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (IOError, OSError):
                if time.time() - start_time > timeout:
                    raise TimeoutError(
                        f"Failed to acquire lock {lock_path} "
                        f"after {timeout}s"
                    )
                time.sleep(poll_interval)

        # 写入锁持有者信息
        lock_fd.write(f"{os.getpid()}\n")
        lock_fd.flush()

        yield lock_fd

    finally:
        if lock_fd is not None:
            # 释放锁
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            except (IOError, OSError):
                pass
            lock_fd.close()


# SRE 场景：防止多个实例同时执行同一任务
def run_exclusive_task(task_name: str) -> None:
    """
    确保同一任务只有一个实例在运行

    SRE 场景：定时任务、备份脚本、清理脚本
    """
    lock_path = Path(f"/tmp/sre-{task_name}.lock")

    try:
        with file_lock(lock_path, timeout=5.0):
            print(f"[{os.getpid()}] Running task: {task_name}")
            # 执行任务逻辑
            time.sleep(10)
            print(f"[{os.getpid()}] Task completed: {task_name}")
    except TimeoutError:
        print(f"[{os.getpid()}] Task {task_name} is already running, skipping")


# SRE 场景：安全地写入共享文件
def append_to_shared_log(log_path: Path, message: str) -> None:
    """
    安全地追加日志到共享文件

    使用文件锁确保多进程并发写入不会导致数据损坏
    """
    lock_path = log_path.with_suffix(".lock")

    with file_lock(lock_path):
        with open(log_path, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


# SRE 场景：PID 文件管理
class PidFile:
    """
    PID 文件管理器

    SRE 用途：
    1. 防止服务重复启动
    2. 记录进程 PID 用于发送信号
    """

    def __init__(self, pid_path: Path) -> None:
        self._pid_path = pid_path

    def __enter__(self) -> "PidFile":
        """获取 PID 文件锁并写入当前 PID"""
        self._lock_path = self._pid_path.with_suffix(".lock")
        self._lock_fd = open(self._lock_path, "w")

        try:
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            self._lock_fd.close()
            raise RuntimeError(
                f"Another instance is already running "
                f"(PID file: {self._pid_path})"
            )

        # 检查是否有旧的 PID 文件
        if self._pid_path.exists():
            old_pid = int(self._pid_path.read_text().strip())
            if self._is_process_running(old_pid):
                raise RuntimeError(
                    f"Process {old_pid} is already running"
                )

        # 写入当前 PID
        self._pid_path.write_text(f"{os.getpid()}\n")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """释放锁并删除 PID 文件"""
        try:
            self._pid_path.unlink(missing_ok=True)
        finally:
            fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
            self._lock_fd.close()

    @staticmethod
    def _is_process_running(pid: int) -> bool:
        """检查进程是否在运行"""
        try:
            os.kill(pid, 0)  # 发送信号 0，只检查进程是否存在
            return True
        except OSError:
            return False


# 使用示例
def run_daemon() -> None:
    """运行守护进程"""
    pid_file = PidFile(Path("/var/run/myapp.pid"))

    try:
        with pid_file:
            print(f"Daemon started with PID {os.getpid()}")
            # 主循环
            while True:
                time.sleep(1)
    except RuntimeError as e:
        print(f"Failed to start: {e}")
        sys.exit(1)
```

---

## 💻 实战练习

### 练习 1：基础操作 — 系统信息采集脚本

**目标**：编写一个采集服务器系统信息的脚本

```python
#!/usr/bin/env python3
"""
系统信息采集脚本

采集内容：
- 操作系统信息
- CPU 信息
- 内存使用
- 磁盘使用
- 网络接口
- Python 环境
"""
import subprocess
import platform
import os
import shutil
from pathlib import Path
from typing import Dict, Any


def get_os_info() -> Dict[str, str]:
    """获取操作系统信息"""
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "hostname": platform.node(),
    }

    # 读取 os-release
    os_release = Path("/etc/os-release")
    if os_release.exists():
        for line in os_release.read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                info[f"os_{key.lower()}"] = value.strip('"')

    return info


def get_cpu_info() -> Dict[str, Any]:
    """获取 CPU 信息"""
    info: Dict[str, Any] = {
        "count": os.cpu_count(),
        "load_avg": os.getloadavg(),
    }

    try:
        result = subprocess.run(
            ["lscpu"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower().replace(" ", "_")
                    info[f"cpu_{key}"] = value.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return info


def get_memory_info() -> Dict[str, Any]:
    """获取内存信息"""
    try:
        result = subprocess.run(
            ["free", "-b"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                return {
                    "total_bytes": int(parts[1]),
                    "used_bytes": int(parts[2]),
                    "free_bytes": int(parts[3]),
                    "total_gb": round(int(parts[1]) / (1024**3), 2),
                    "used_percent": round(int(parts[2]) / int(parts[1]) * 100, 1),
                }
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    return {}


def get_disk_info() -> Dict[str, Dict[str, Any]]:
    """获取磁盘信息"""
    disks = {}
    try:
        result = subprocess.run(
            ["df", "-B1"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 6:
                    mount = parts[5]
                    if mount.startswith(("/", "/home", "/var")):
                        disks[mount] = {
                            "total_bytes": int(parts[1]),
                            "used_bytes": int(parts[2]),
                            "available_bytes": int(parts[3]),
                            "used_percent": parts[4],
                            "filesystem": parts[0],
                        }
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass

    return disks


def get_python_info() -> Dict[str, str]:
    """获取 Python 环境信息"""
    return {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "executable": str(Path(sys.executable)),
        "venv": str(hasattr(sys, 'real_prefix') or
                    (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)),
    }


def main() -> None:
    import json
    import sys

    report = {
        "os": get_os_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "python": get_python_info(),
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

### 练习 2：进阶场景 — 日志轮转工具

**目标**：编写一个安全的日志轮转工具，支持文件锁和信号处理

```python
#!/usr/bin/env python3
"""
安全的日志轮转工具

功能：
1. 按大小或时间轮转日志
2. 使用文件锁确保并发安全
3. 支持 SIGHUP 信号触发轮转
4. 自动清理旧的轮转文件
"""
import os
import sys
import signal
import fcntl
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


class LogRotator:
    """安全的日志轮转器"""

    def __init__(
        self,
        log_path: Path,
        max_size_mb: float = 100,
        max_files: int = 10,
        compress: bool = True,
    ) -> None:
        self._log_path = log_path
        self._max_size_bytes = int(max_size_mb * 1024 * 1024)
        self._max_files = max_files
        self._compress = compress
        self._rotate_requested = False

        # 注册 SIGHUP 处理器
        signal.signal(signal.SIGHUP, self._handle_sighup)

    def _handle_sighup(self, signum: int, frame: Optional[object]) -> None:
        """SIGHUP 处理函数 — 触发日志轮转"""
        self._rotate_requested = True

    def _get_lock(self) -> Optional[int]:
        """获取文件锁"""
        lock_path = self._log_path.with_suffix(".lock")
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_fd
        except (IOError, OSError):
            os.close(lock_fd)
            return None

    def _release_lock(self, lock_fd: int) -> None:
        """释放文件锁"""
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        except (IOError, OSError):
            pass

    def _rotate(self) -> bool:
        """执行日志轮转"""
        if not self._log_path.exists():
            return False

        # 检查文件大小
        size = self._log_path.stat().st_size
        if size < self._max_size_bytes and not self._rotate_requested:
            return False

        # 获取锁
        lock_fd = self._get_lock()
        if lock_fd is None:
            return False

        try:
            # 生成轮转文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_path = self._log_path.with_suffix(f".{timestamp}.log")

            # 移动当前日志
            shutil.move(str(self._log_path), str(rotated_path))

            # 创建新的空日志文件
            self._log_path.touch()
            os.chmod(self._log_path, 0o640)

            # 压缩轮转文件
            if self._compress:
                import gzip
                gz_path = rotated_path.with_suffix(".log.gz")
                with open(rotated_path, "rb") as f_in:
                    with gzip.open(gz_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                rotated_path.unlink()
                print(f"Rotated and compressed: {gz_path}")
            else:
                print(f"Rotated: {rotated_path}")

            # 清理旧文件
            self._cleanup_old_files()

            self._rotate_requested = False
            return True

        finally:
            self._release_lock(lock_fd)

    def _cleanup_old_files(self) -> None:
        """清理旧的轮转文件"""
        pattern = self._log_path.stem + ".*"
        rotated_files = sorted(
            self._log_path.parent.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # 保留最新的 max_files 个文件
        for old_file in rotated_files[self._max_files:]:
            old_file.unlink()
            print(f"Cleaned up: {old_file}")

    def check_and_rotate(self) -> bool:
        """检查是否需要轮转，需要则执行"""
        return self._rotate()


# 使用示例
def main() -> None:
    log_path = Path("/var/log/myapp/app.log")
    rotator = LogRotator(log_path, max_size_mb=50, max_files=5)

    print(f"Monitoring {log_path} for rotation...")
    print(f"Send SIGHUP to force rotation: kill -HUP {os.getpid()}")

    while True:
        rotator.check_and_rotate()
        time.sleep(10)


if __name__ == "__main__":
    main()
```

### 练习 3：故障排查挑战 — 修复有问题的 subprocess 代码

**场景**：以下代码有安全和可靠性问题，请找出并修复。

```python
# broken_subprocess.py — 故障排查练习
import subprocess
import os

def run_command(cmd):
    result = subprocess.run(cmd, shell=True)  # 问题 1
    return result.stdout

def check_host(host):
    output = run_command(f"ping -c 1 {host}")  # 问题 2
    return "1 received" in output

def get_disk_usage():
    output = run_command("df -h")  # 问题 3
    return output

def cleanup_logs(days):
    cmd = f"find /var/log -name '*.log' -mtime +{days} -delete"  # 问题 4
    run_command(cmd)

def run_script(script_path):
    with open(script_path) as f:
        content = f.read()
    run_command(content)  # 问题 5
```

**预期发现的问题**：
1. `shell=True` 存在 shell 注入风险 — 应使用列表形式
2. 用户输入直接拼接到命令中 — 命令注入漏洞
3. 没有捕获输出（`capture_output=True`）— `result.stdout` 为 None
4. 没有检查返回码 — 删除失败时不知道
5. 直接执行文件内容 — 任意代码执行漏洞

---

## 🎯 面试题精选

### 问题 1：subprocess.run() 的 shell=True 和 shell=False 有什么区别？什么时候该用哪个？

**参考答案**：

| 特性 | shell=False (默认) | shell=True |
|------|-------------------|------------|
| 命令形式 | 列表 `["ls", "-la"]` | 字符串 `"ls -la"` |
| Shell 解析 | 不经过 shell | 通过 /bin/sh 执行 |
| 安全性 | 安全（无注入风险） | 危险（有注入风险） |
| 管道/重定向 | 不支持（需 Popen） | 支持 |
| 环境变量展开 | 不支持 | 支持 (`$HOME`) |

**使用建议**：
- 优先使用 `shell=False`（列表形式）
- 只在需要 shell 特性（管道、重定向、通配符）时用 `shell=True`
- 使用 `shell=True` 时，用 `shlex.quote()` 转义用户输入

### 问题 2：为什么推荐 pathlib 替代 os.path？

**参考答案**：

pathlib 的优势：
1. **面向对象**：方法挂载在 Path 对象上，而非模块函数
2. **可读性**：`Path("/var/log") / "app.log"` 比 `os.path.join("/var/log", "app.log")` 更直观
3. **链式调用**：`path.parent / "backup" / path.name`
4. **类型安全**：IDE 自动补全更好
5. **跨平台**：自动处理路径分隔符

SRE 建议：新代码使用 pathlib，旧代码逐步迁移。

### 问题 3：信号处理中，SIGTERM 和 SIGKILL 有什么区别？

**参考答案**：

| 特性 | SIGTERM (15) | SIGKILL (9) |
|------|-------------|-------------|
| 可捕获 | 是 | 否 |
| 默认行为 | 终止 | 强制终止 |
| 清理机会 | 有（可执行清理逻辑） | 无 |
| 使用场景 | 优雅关闭 | 强制终止僵尸进程 |

SRE 场景：
- Kubernetes 删除 Pod 时先发 SIGTERM，等待 gracePeriodSeconds，再发 SIGKILL
- 应用应该捕获 SIGTERM 执行清理（关闭连接、保存状态、刷新缓冲区）

### 问题 4：文件锁 flock 和 fcntl 有什么区别？

**参考答案**：

| 特性 | flock | fcntl |
|------|------|-------|
| 锁粒度 | 整个文件 | 文件记录区域 |
| 跨进程 | 是 | 是 |
| 继承性 | fork 后子进程继承锁 | fork 后子进程继承锁 |
| NFS 支持 | 不支持 | 支持 |
| 锁类型 | 共享锁、排他锁 | 共享锁、排他锁、建议锁 |

SRE 建议：
- 简单场景用 `flock`（如防止重复执行）
- 需要 NFS 支持或记录锁用 `fcntl`
- Python 中推荐用 `fcntl.flock()` 或第三方 `filelock` 库

### 问题 5：临时文件为什么需要设置权限？

**参考答案**：

默认创建的临时文件权限可能是 644 或 666（取决于 umask），其他用户可读。

安全风险：
- 临时配置文件可能包含密码、API Key
- 临时日志文件可能包含敏感信息
- 其他用户可以读取这些文件

最佳实践：
- 临时文件权限设为 600（只有 owner 可读写）
- 临时目录权限设为 700（只有 owner 可访问）
- 使用上下文管理器确保自动清理

### 问题 6：如何实现一个支持优雅关闭的 Python 守护进程？

**参考答案**：

```python
import signal
import sys
import os
import time
import logging

class Daemon:
    def __init__(self):
        self.running = True

    def handle_sigterm(self, signum, frame):
        logging.info("Received SIGTERM, shutting down...")
        self.running = False

    def handle_sighup(self, signum, frame):
        logging.info("Received SIGHUP, reloading config...")
        self.reload_config()

    def reload_config(self):
        # 重新加载配置
        pass

    def run(self):
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        signal.signal(signal.SIGHUP, self.handle_sighup)
        signal.signal(signal.SIGINT, self.handle_sigterm)

        # 写入 PID 文件
        with open("/var/run/myapp.pid", "w") as f:
            f.write(str(os.getpid()))

        try:
            while self.running:
                # 业务逻辑
                time.sleep(1)
        finally:
            # 清理
            os.unlink("/var/run/myapp.pid")
            logging.info("Daemon stopped")
```

### 问题 7：pathlib 的 Path 对象和字符串路径有什么区别？何时转换？

**参考答案**：

| 特性 | Path 对象 | 字符串路径 |
|------|----------|-----------|
| 类型 | `pathlib.Path` | `str` |
| 方法 | `.exists()`, `.read_text()` 等 | 无 |
| 拼接 | `/` 运算符 | `os.path.join()` |
| 传递给 subprocess | 需要 `str(path)` | 直接使用 |
| JSON 序列化 | 需要 `str(path)` | 直接使用 |

需要转换的场景：
- 传递给 subprocess（需要 str）
- JSON/YAML 序列化
- 与使用字符串的旧代码交互
- 正则表达式匹配路径

### 问题 8：为什么 os.system() 不推荐使用？

**参考答案**：

`os.system()` 的问题：
1. **无法捕获输出**：stdout/stderr 直接打印到终端
2. **无法获取返回码的详细信息**：只返回退出状态
3. **Shell 注入风险**：通过 shell 执行命令
4. **无法设置超时**：命令可能无限阻塞
5. **无法控制 stdin**：无法向命令发送输入

替代方案：使用 `subprocess.run()` 配合 `capture_output=True, text=True, timeout=30`。

---

## 📚 深入阅读

### 官方文档
- [subprocess — Subprocess management](https://docs.python.org/3/library/subprocess.html)
- [pathlib — Object-oriented filesystem paths](https://docs.python.org/3/library/pathlib.html)
- [shutil — High-level file operations](https://docs.python.org/3/library/shutil.html)
- [signal — Set handlers for asynchronous events](https://docs.python.org/3/library/signal.html)
- [tempfile — Generate temporary files and directories](https://docs.python.org/3/library/tempfile.html)
- [fcntl — The fcntl and ioctl system calls](https://docs.python.org/3/library/fcntl.html)

### 推荐书籍
- 《Python Cookbook》David Beazley — 第 5 章：文件与 I/O
- 《Effective Python》Brett Slatkin — 第 6 章：内置模块
- 《Linux System Programming》Robert Love — 第 5 章：进程管理

### 技术博客
- [Real Python — subprocess](https://realpython.com/python-subprocess/)
- [Real Python — pathlib](https://realpython.com/python-pathlib/)
- [Pymotw — signal](https://pymotw.com/3/signal/)

---

## ✅ 自检清单

### 理论检查
- [ ] 理解 subprocess 的安全模型（shell=True vs shell=False）
- [ ] 知道 pathlib 相比 os.path 的优势
- [ ] 理解 Linux 信号机制（SIGTERM, SIGHUP, SIGKILL）
- [ ] 知道文件锁的实现方式（flock vs fcntl）
- [ ] 理解临时文件的安全风险

### 实操检查
- [ ] 能用 subprocess 安全执行系统命令
- [ ] 能用 pathlib 进行文件路径操作
- [ ] 能用 shutil 进行文件复制/移动/删除
- [ ] 能编写信号处理函数实现优雅关闭
- [ ] 能用文件锁防止并发竞态条件

### 能力验证
- [ ] 能编写批量服务器操作工具（并行 SSH 执行）
- [ ] 能编写安全的日志轮转工具
- [ ] 能编写支持优雅关闭的守护进程
