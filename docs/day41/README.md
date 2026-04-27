# Day 41: Socket 编程基础

> 📅 日期：2026-04-27  
> 📖 学习主题：Socket 编程基础  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 41 的学习后，你应该掌握：
- 理解 Socket 编程基础 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. Socket 编程概述

#### 1.1 什么是 Socket

Socket（套接字）是操作系统提供的**网络通信端点抽象**，是进程间网络通信的基础。可以理解为网络通信的"插座"——一端插着客户端，一端插着服务端，数据通过它们流动。

```
客户端 Socket                    服务端 Socket
   │                                │
   ├── connect() ───────────────────►│
   │         SYN                    │
   │◄───────────────────────────────┤
   │         SYN+ACK                │
   │                                │
   ├── ACK ─────────────────────────►│
   │                                │
   ├── send(data) ─────────────────►│
   │                                ├── recv(data)
   │◄───────────────────────────────┤
   │         response               │
   │                                │
   └── close() ────────────────────►│
```

#### 1.2 Socket 的类型

| 类型 | 常量 | 协议 | 特点 | SRE 场景 |
|------|------|------|------|----------|
| 流式 Socket | `SOCK_STREAM` | TCP | 可靠、有序、面向连接 | Web 服务、数据库连接 |
| 数据报 Socket | `SOCK_DGRAM` | UDP | 无连接、不可靠、低延迟 | DNS 查询、监控指标上报 |
| 原始 Socket | `SOCK_RAW` | Raw IP | 直接操作 IP 层 | 抓包工具、网络诊断 |

#### 1.3 Socket 地址族

| 地址族 | 常量 | 说明 | 示例 |
|--------|------|------|------|
| IPv4 | `AF_INET` | 最常用的地址族 | `('192.168.1.1', 8080)` |
| IPv6 | `AF_INET6` | 下一代 IP 协议 | `('::1', 8080)` |
| Unix 域 | `AF_UNIX` | 本地进程间通信 | `/var/run/app.sock` |

---

### 2. TCP Socket 编程（面向连接）

#### 2.1 服务端 Socket 生命周期

```
socket() → bind() → listen() → accept() → recv()/send() → close()
```

```python
# === TCP 服务端 ===
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 避免 Address already in use

server.bind(('0.0.0.0', 9999))  # 监听所有网卡
server.listen(5)                # 最多 5 个连接排队
print("Server listening on port 9999...")

while True:
    client_socket, client_addr = server.accept()
    print(f"Connection from {client_addr}")

    data = client_socket.recv(4096)  # 接收最多 4096 字节
    print(f"Received: {data.decode()}")

    client_socket.sendall(b"Hello from server!")
    client_socket.close()
```

#### 2.2 客户端 Socket

```python
# === TCP 客户端 ===
import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 9999))

client.sendall(b"Hello from client!")
response = client.recv(4096)
print(f"Server replied: {response.decode()}")

client.close()
```

#### 2.3 关键 API 详解

| 方法 | 说明 | 参数/返回值 |
|------|------|-------------|
| `socket(family, type)` | 创建 socket | 返回 socket 对象 |
| `bind((host, port))` | 绑定地址和端口 | 无返回值 |
| `listen(backlog)` | 开始监听 | backlog=等待队列长度 |
| `accept()` | 接受连接 | 返回 `(client_socket, address)` |
| `connect((host, port))` | 连接服务端 | 无返回值 |
| `recv(bufsize)` | 接收数据 | 返回 bytes |
| `send(data)` | 发送数据 | 返回发送字节数 |
| `sendall(data)` | 发送全部数据 | 确保所有数据发出 |
| `close()` | 关闭连接 | 无返回值 |
| `settimeout(seconds)` | 设置超时 | 避免永久阻塞 |

---

### 3. UDP Socket 编程（无连接）

```python
# === UDP 服务端 ===
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(('0.0.0.0', 9998))

while True:
    data, client_addr = server.recvfrom(4096)
    print(f"From {client_addr}: {data.decode()}")
    server.sendto(b"ACK", client_addr)

# === UDP 客户端 ===
import socket

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.sendto(b"Hello UDP!", ('127.0.0.1', 9998))
data, server = client.recvfrom(4096)
print(f"Server: {data.decode()}")
client.close()
```

**TCP vs UDP 对比**：

| 特性 | TCP (SOCK_STREAM) | UDP (SOCK_DGRAM) |
|------|-------------------|-------------------|
| 连接 | 需要三次握手 | 无需连接 |
| 可靠性 | 保证送达、有序 | 不保证送达、可能乱序 |
| 速度 | 较慢（握手+确认） | 快（直接发送） |
| 流量控制 | 滑动窗口 | 无 |
| 适用场景 | HTTP、SSH、数据库 | DNS、监控、视频流 |

---

### 4. SRE 实战：Socket 编程应用场景

#### 4.1 健康检查探针

```python
#!/usr/bin/env python3
# SRE 健康检查工具 — 检测服务端口连通性
import socket
import sys
from datetime import datetime

def check_port(host, port, timeout=3.0):
    # 检测端口是否可达
    start = datetime.now()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        elapsed = (datetime.now() - start).total_seconds() * 1000
        sock.close()
        return {"host": host, "port": port, "status": "UP", "latency_ms": "%.1f" % elapsed}
    except socket.timeout:
        return {"host": host, "port": port, "status": "TIMEOUT", "latency_ms": ">3000"}
    except ConnectionRefusedError:
        return {"host": host, "port": port, "status": "REFUSED", "latency_ms": "-"}
    except Exception as e:
        return {"host": host, "port": port, "status": "ERROR", "latency_ms": "-", "error": str(e)}

# 检查一组关键服务
services = [
    ("127.0.0.1", 80),    # Nginx
    ("127.0.0.1", 443),   # HTTPS
    ("127.0.0.1", 3306),  # MySQL
    ("127.0.0.1", 6379),  # Redis
    ("127.0.0.1", 8080),  # App Server
]

for host, port in services:
    result = check_port(host, port)
    status_icon = "OK" if result["status"] == "UP" else "FAIL"
    print("%s %s:%s - %s (%sms)" % (
        status_icon, result['host'], result['port'],
        result['status'], result['latency_ms']))
```

#### 4.2 简易 HTTP 客户端（原始 Socket）

```python
import socket

def http_get(host, port, path="/"):
    # 用原始 Socket 发送 HTTP GET 请求
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((host, port))

    request = "GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n" % (path, host)
    sock.sendall(request.encode())

    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

    sock.close()
    return response.decode()

# 使用示例
resp = http_get("example.com", 80, "/")
print(resp[:500])  # 打印前 500 字符
```

#### 4.3 Unix Domain Socket — 进程间通信

```python
import socket
import os

SOCK_PATH = "/tmp/sre_app.sock"

# 服务端
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
if os.path.exists(SOCK_PATH):
    os.unlink(SOCK_PATH)
server.bind(SOCK_PATH)
server.listen(1)
conn, _ = server.accept()
data = conn.recv(1024)
conn.sendall(b"ACK from Unix socket")
conn.close()

# 客户端（同一台机器上更快，无需网络栈）
client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client.connect(SOCK_PATH)
client.sendall(b"Hello via Unix socket")
print(client.recv(1024).decode())
client.close()
```

**Unix Domain Socket vs TCP localhost**：
- Unix Domain Socket 不需要经过 TCP/IP 协议栈
- 性能比 TCP localhost 高 **2-5 倍**
- 适合微服务间本地通信（如 Nginx → uWSGI）

---

### 5. Socket 选项与调优

#### 5.1 常用 Socket 选项

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 地址复用 — 避免 TIME_WAIT 导致的 "Address already in use"
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 发送/接收缓冲区大小
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

# TCP Keepalive — 检测死连接
sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)    # 空闲 60 秒后开始探测
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)   # 每 10 秒探测一次
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)      # 最多探测 6 次

# 禁用 Nagle 算法 — 降低延迟（适合实时应用）
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
```

#### 5.2 TIME_WAIT 问题

```bash
# 查看 TIME_WAIT 连接数量
ss -tan state time-wait | wc -l

# 查看连接状态分布
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn

# 内核调优（/etc/sysctl.conf）
# net.ipv4.tcp_tw_reuse = 1     # 允许重用 TIME_WAIT 连接
# net.ipv4.tcp_max_tw_buckets = 262144  # TIME_WAIT 桶大小
# net.ipv4.tcp_fin_timeout = 30 # FIN-WAIT-2 超时
```

---

### 6. 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `Address already in use` | 端口被占用或 TIME_WAIT | 设置 `SO_REUSEADDR`，或换端口 |
| `Connection refused` | 目标端口没有监听 | 检查服务是否启动、防火墙规则 |
| `Connection timed out` | 网络不通或防火墙拦截 | `ping` 测试，检查 `iptables`/安全组 |
| `Broken pipe` | 对端已关闭连接 | 检查连接状态，处理异常 |
| 中文乱码 | 编码不一致 | 统一使用 UTF-8，`data.decode('utf-8')` |
| 接收数据不完整 | TCP 是流协议，一次 recv 不等于一次 send | 循环 recv 直到收到完整消息 |

---

### 7. 扩展阅读

- **Python 官方文档**: `socket` module — https://docs.python.org/3/library/socket.html
- **Beej's Guide to Network Programming**: 经典网络编程教程 — https://beej.us/guide/bgnet/
- **`selectors` 模块**: Python 多路复用 I/O（适合高并发服务端）
- **`asyncio`**: Python 异步网络编程（现代推荐方案）


---

## 💻 实战练习

### 练习 1：网络故障排查脚本

**场景**：用户报告"网站访问慢"，系统化排查。

```bash
#!/bin/bash
TARGET="example.com"
echo "=== 网络排查: $TARGET ==="

# 1. DNS
echo "DNS: $(dig +short $TARGET A 2>/dev/null || echo 'FAILED')"

# 2. 连通性
ping -c 3 -W 2 $TARGET 2>&1 | tail -1

# 3. 路由
traceroute -m 15 -w 2 $TARGET 2>/dev/null | head -10

# 4. 端口
for port in 80 443; do
    timeout 2 bash -c "echo > /dev/tcp/$TARGET/$port" 2>/dev/null && \
        echo "端口 $port: OK" || echo "端口 $port: FAIL"
done

# 5. HTTP
curl -s -o /dev/null -w "HTTP: %{{http_code}}, Time: %{{time_total}}s\n" "http://$TARGET"

# 6. TCP 状态
ss -tan | awk 'NR>1 {{print $1}}' | sort | uniq -c | sort -rn
```

### 练习 2：抓包分析

```bash
# 抓取 HTTP 流量
sudo tcpdump -i any -n port 80 -A 2>/dev/null | head -50

# 保存到文件用 Wireshark 分析
sudo tcpdump -i any -n port 443 -w /tmp/capture.pcap

# 分析 TCP 握手
sudo tcpdump -i any -n 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0' -c 10
```


---

## 📚 最新优质资源

### 官方文档
- [Ubuntu 22.04 LTS 官方文档](https://ubuntu.com/documentation)
- [Linux FHS 标准 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/)
- [Bash 官方手册](https://www.gnu.org/software/bash/manual/)

### 推荐教程
- [MIT The Missing Semester](https://missing.csail.mit.edu/) - 工程师必学但学校不教的技能
- [Linux Journey](https://linuxjourney.com/) - 免费的 Linux 学习路径
- [Ryan's Tutorials - Linux](https://ryanstutorials.net/linuxtutorial/) - 入门到进阶
- [Linux Command Library](https://linuxcommand.org/) - 命令行入门

### 视频课程
- [Bilibili: 鸟哥的Linux私房菜（基础篇）](https://www.bilibili.com/video/BV1Vt411X7y6/)
- [YouTube: NetworkChuck - Linux Basics](https://www.youtube.com/playlist?list=PLI9KFC2-DCX-6LVEU2c2XBGWckzVqKS6j)
- [YouTube: DevOps Journey - Linux for DevOps](https://www.youtube.com/playlist?list=PL2_OBreMn7FqZkvLWn1Br7W1v5E5XKJyI)

### 实战练习平台
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) - 史上最好的 Linux 入门练习
- [KodeKloud Engineer](https://kodekloud.com) - 交互式 K8s 和 DevOps 练习
- [Play with Docker](https://play.docker.com/) - 免费 Docker 练习环境
- [Learn Linux TV](https://www.learnlinux.tv/) - 视频 + 实战

### SRE 相关资源
- [Google SRE Books](https://sre.google/sre-book/table-of-contents/)
- [Linux Performance](http://www.brendangregg.com/linuxperf.html) - Brendan Gregg
- [Ops School](http://www.ops-school.org/) - 运维工程师学习路径


---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| 问题描述 | 如何解决 |

### 延伸思考

- 思考 1：...
- 思考 2：...

---

## ✅ 完成检查

- [ ] 理解核心概念（能用自己的话解释）
- [ ] 完成所有基础命令练习
- [ ] 完成实战场景练习
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记
- [ ] 理解了命令背后的原理

---

*由 SRE 学习计划自动生成 | 2026-04-27 09:06:31*  
*Generated by Hermes Agent with review*
