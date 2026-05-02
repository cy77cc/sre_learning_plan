# Day 55: 实战项目 — 批量服务器管理工具

> 📅 日期：2026-05-02
> 📖 学习主题：实战项目：批量服务器管理工具
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 综合运用 Python 网络编程知识构建批量管理工具
- 实现 SSH 批量执行、文件批量分发
- 掌握并发执行和错误处理

---

## 📖 详细知识点

### 1. SSH 批量执行

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import paramiko


def ssh_exec(host, command, username="root", timeout=10):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=username, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        return host, exit_code, output, ""
    except Exception as e:
        return host, -1, "", str(e)
    finally:
        client.close()


# 批量执行
hosts = ["10.0.1.10", "10.0.1.11", "10.0.2.10"]
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(ssh_exec, h, "uptime"): h for h in hosts}
    for future in as_completed(futures):
        host, code, output, error = future.result()
        if error:
            print(f"FAIL {host}: {error}")
        else:
            print(f"OK {host}: {output.strip()}")
```

### 2. 文件批量分发

```python
def ssh_scp(host, local_path, remote_path, username="root"):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username)
    sftp = client.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    client.close()
```

### 3. 实战：批量管理 CLI

```python
#!/usr/bin/env python3
"""Batch server management tool."""

import argparse
import paramiko
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_on_host(host, command, username, timeout):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=username, timeout=timeout)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode()
        error = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        return host, exit_code, output, error
    except Exception as e:
        return host, -1, "", str(e)
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Batch server management")
    parser.add_argument("command", help="Command to execute")
    parser.add_argument("-f", "--hosts-file", required=True, help="Hosts file (one per line)")
    parser.add_argument("-u", "--username", default="root")
    parser.add_argument("-t", "--timeout", type=int, default=10)
    parser.add_argument("-w", "--workers", type=int, default=10)
    args = parser.parse_args()

    with open(args.hosts_file) as f:
        hosts = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Executing on {len(hosts)} hosts: {args.command}\n")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_on_host, h, args.command, args.username, args.timeout): h
            for h in hosts
        }
        for future in as_completed(futures):
            host, code, output, error = future.result()
            if error:
                print(f"FAIL {host}: {error}")
            else:
                print(f"OK {host} (exit={code}):\n{output}")


if __name__ == "__main__":
    main()
```

---

## 📚 扩展阅读

- [paramiko 文档](https://docs.paramiko.org/)
- [并发最佳实践](https://docs.python.org/3/library/concurrent.futures.html)
