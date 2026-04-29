# SRE 学习计划 — Day 38：tcpdump 抓包分析

---

## 📅 基本信息

| 项目 | 内容 |
|------|------|
| **天数** | Day 38 |
| **主题** | tcpdump 抓包分析 |
| **难度** | ⭐⭐⭐ 中级 |
| **预计时间** | 2-3 小时 |
| **前置知识** | TCP/IP 协议基础、网络层与传输层概念 |

---

## 📖 目录

1. [tcpdump 概述](#1-tcpdump-概述)
2. [BPF 过滤语法](#2-bpf-过滤语法)
3. [Wireshark 基础](#3-wireshark-基础)
4. [SRE 实战案例：TCP 重传分析](#4-sre-实战案例tcp-重传分析)
5. [练习](#5-练习)
6. [进阶技巧](#6-进阶技巧)
7. [资源](#7-资源)

---

## 1. tcpdump 概述

### 1.1 什么是 tcpdump？

tcpdump 是 Linux 系统中最经典的**命令行抓包工具**，基于 libpcap 库，直接在数据链路层捕获数据包。它是 SRE 排查网络问题的利器。

```
+-------------------+     +-------------------+     +-------------------+
|   应用层 (HTTP)    |     |   应用层 (HTTP)    |     |   应用层 (HTTP)    |
+-------------------+     +-------------------+     +-------------------+
|   传输层 (TCP)     |     |   传输层 (TCP)     |     |   传输层 (TCP)     |
+-------------------+     +-------------------+     +-------------------+
|   网络层 (IP)      |     |   网络层 (IP)      |     |   网络层 (IP)      |
+-------------------+     +-------------------+     +-------------------+
| 数据链路层 (Ethernet)| ←tcpdump抓包点→ | 数据链路层 (Ethernet)|     | 数据链路层 (Ethernet)|
+-------------------+     +-------------------+     +-------------------+
```

### 1.2 安装 tcpdump

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y tcpdump

# RHEL/CentOS/Rocky
sudo yum install -y tcpdump

# Alpine (容器常见)
apk add tcpdump

# 验证安装
tcpdump --version
```

### 1.3 基本命令格式

```bash
tcpdump [选项] [过滤表达式]
```

**常用选项速查表**：

| 选项 | 说明 | 示例 |
|------|------|------|
| `-i <interface>` | 指定网卡 | `tcpdump -i eth0` |
| `-n` | 不解析主机名（IP 显示） | `tcpdump -n` |
| `-nn` | 不解析主机名和端口号 | `tcpdump -nn` |
| `-c <count>` | 捕获指定数量后退出 | `tcpdump -c 10` |
| `-w <file>` | 写入 pcap 文件 | `tcpdump -w capture.pcap` |
| `-r <file>` | 读取 pcap 文件 | `tcpdump -r capture.pcap` |
| `-s 0` | 捕获完整数据包（不截断） | `tcpdump -s 0` |
| `-v` / `-vv` / `-vvv` | 详细程度递增 | `tcpdump -vvv` |
| `-X` | 同时显示十六进制和 ASCII | `tcpdump -X` |
| `-A` | 以 ASCII 显示（适合 HTTP） | `tcpdump -A` |
| `-q` | 精简输出 | `tcpdump -q` |
| `-l` | 行缓冲（配合管道使用） | `tcpdump -l` |
| `--immediate-mode` | 立即模式，减少延迟 | `tcpdump --immediate-mode` |

### 1.4 快速入门示例

```bash
# 捕获 eth0 上所有流量（Ctrl+C 停止）
sudo tcpdump -i eth0

# 只抓 10 个包，显示 IP 和端口号
sudo tcpdump -i eth0 -nn -c 10

# 抓取流量保存到文件，后续用 Wireshark 分析
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/capture.pcap

# 读取已保存的 pcap 文件
sudo tcpdump -r /tmp/capture.pcap -nn
```

---

## 2. BPF 过滤语法

### 2.1 BPF 基础

tcpdump 使用 **BPF (Berkeley Packet Filter)** 语法过滤数据包。理解 BPF 是高效抓包的核心。

**核心关键字分类**：

| 类别 | 关键字 | 说明 |
|------|--------|------|
| **Type** | `host`, `net`, `port`, `portrange` | 过滤主机、网络、端口 |
| **Dir** | `src`, `dst`, `src or dst` | 过滤方向 |
| **Proto** | `tcp`, `udp`, `icmp`, `arp`, `ip`, `ip6` | 过滤协议 |

### 2.2 按主机过滤

```bash
# 抓取与特定 IP 相关的所有流量（双向）
sudo tcpdump -i eth0 host 192.168.1.100

# 只抓来源是某 IP 的包
sudo tcpdump -i eth0 src host 192.168.1.100

# 只抓目标是某 IP 的包
sudo tcpdump -i eth0 dst host 192.168.1.100

# 按主机名过滤（需要 DNS 解析，建议用 -n 禁用）
sudo tcpdump -i eth0 host example.com

# 抓取与某 MAC 地址相关的流量
sudo tcpdump -i eth0 ether host aa:bb:cc:dd:ee:ff
```

### 2.3 按端口过滤

```bash
# 抓取特定端口的流量
sudo tcpdump -i eth0 port 80

# 源端口或目标端口
sudo tcpdump -i eth0 src port 443
sudo tcpdump -i eth0 dst port 8080

# 端口范围
sudo tcpdump -i eth0 portrange 8000-9000

# 排除某个端口
sudo tcpdump -i eth0 port not 22

# 多个端口（使用 or）
sudo tcpdump -i eth0 port 80 or port 443
```

### 2.4 按网络过滤

```bash
# 抓取整个子网的流量
sudo tcpdump -i eth0 net 192.168.1.0/24

# 更简洁的 CIDR 写法
sudo tcpdump -i eth0 net 10.0.0.0/8

# 排除某个网段
sudo tcpdump -i eth0 not net 172.16.0.0/12
```

### 2.5 按协议过滤

```bash
# TCP 流量
sudo tcpdump -i eth0 tcp

# UDP 流量
sudo tcpdump -i eth0 udp

# ICMP（ping 使用）
sudo tcpdump -i eth0 icmp

# ARP
sudo tcpdump -i eth0 arp

# IPv6
sudo tcpdump -i eth0 ip6

# 特定协议的端口组合
sudo tcpdump -i eth0 tcp port 3306   # MySQL
sudo tcpdump -i eth0 tcp port 6379   # Redis
sudo tcpdump -i eth0 tcp port 5432   # PostgreSQL
```

### 2.6 逻辑运算符

| 运算符 | 写法 | 说明 |
|--------|------|------|
| **与** | `and` / `&&` | 同时满足 |
| **或** | `or` / `\|\|` | 满足任一 |
| **非** | `not` / `!` | 排除 |

```bash
# and：抓取来自 192.168.1.100 且目标端口为 80 的包
sudo tcpdump -i eth0 src host 192.168.1.100 and dst port 80

# or：抓取 80 或 443 端口的流量
sudo tcpdump -i eth0 port 80 or port 443

# not：排除 SSH 流量
sudo tcpdump -i eth0 not port 22

# 组合使用：抓取来自某网段的 HTTP 或 HTTPS
sudo tcpdump -i eth0 src net 10.0.0.0/8 and \( port 80 or port 443 \)

# 排除广播和特定网段
sudo tcpdump -i eth0 not broadcast and not net 127.0.0.0/8

# 抓取 TCP 且不是 80 端口的流量
sudo tcpdump -i eth0 tcp and not port 80
```

### 2.7 TCP 标志位过滤（高级）

```bash
# TCP 标志位过滤 - 排查连接问题的利器
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0'        # SYN 包（新建连接）
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0'  # 纯 SYN
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-fin != 0'        # FIN 包（关闭连接）
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-rst != 0'        # RST 包（重置连接）
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-ack != 0'        # ACK 包

# 抓取 SYN 洪水攻击特征（大量 SYN 无 ACK）
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0 and tcp[tcpflags] & (tcp-ack) == 0'
```

### 2.8 BPF 过滤语法速查表

| 过滤需求 | BPF 表达式 |
|----------|-----------|
| 指定 IP | `host 10.0.0.1` |
| 排除 IP | `not host 10.0.0.1` |
| 指定网段 | `net 10.0.0.0/24` |
| 指定端口 | `port 80` |
| 端口范围 | `portrange 1024-65535` |
| 指定协议 | `tcp` / `udp` / `icmp` |
| 源方向 | `src host 10.0.0.1` |
| 目标方向 | `dst host 10.0.0.1` |
| 组合条件 | `host 10.0.0.1 and port 80` |
| TCP SYN | `'tcp[tcpflags] & tcp-syn != 0'` |
| TCP RST | `'tcp[tcpflags] & tcp-rst != 0'` |
| 数据包大小 | `greater 100` / `less 64` |

---

## 3. Wireshark 基础

### 3.1 Wireshark vs tcpdump 对比

| 特性 | tcpdump | Wireshark |
|------|---------|-----------|
| 界面 | 命令行 | GUI |
| 安装 | 轻量，服务器友好 | 较重，适合桌面 |
| 实时分析 | 有限（依赖过滤语法） | 强大的显示过滤器 |
| 协议解析 | 基本 | 数千种协议深度解析 |
| Follow Stream | ❌ | ✅ 一键追踪完整会话 |
| 统计功能 | 有限 | 丰富的统计和图表 |
| 适合场景 | 服务器实时抓包、脚本自动化 | 离线深度分析、可视化 |

### 3.2 安装 Wireshark

```bash
# Debian/Ubuntu
sudo apt-get install -y wireshark

# macOS (Homebrew)
brew install --cask wireshark

# Windows
# 访问 https://www.wireshark.org/download.html 下载安装包
```

### 3.3 Wireshark 显示过滤器

Wireshark 的显示过滤器比 tcpdump 的 BPF 更灵活（在已捕获的数据上过滤）：

| 过滤器 | 说明 |
|--------|------|
| `ip.addr == 192.168.1.100` | 过滤特定 IP |
| `tcp.port == 80` | 过滤 TCP 端口 |
| `http.request.method == "GET"` | 过滤 HTTP GET 请求 |
| `http.response.code == 200` | 过滤 HTTP 200 响应 |
| `dns.qry.name == "example.com"` | 过滤特定 DNS 查询 |
| `tcp.flags.syn == 1` | 过滤 SYN 包 |
| `tcp.flags.reset == 1` | 过滤 RST 包 |
| `tcp.analysis.retransmission` | 过滤 TCP 重传 |
| `frame.len > 1000` | 过滤大包 |
| `tcp.stream eq 0` | 过滤特定 TCP 流 |

### 3.4 Follow Stream（追踪流）

这是 Wireshark 最实用的功能之一：

1. 右键点击任意 TCP/UDP/HTTP 数据包
2. 选择 **Follow → TCP Stream**（或 UDP/HTTP Stream）
3. Wireshark 会自动重组完整会话，以可读形式展示

**使用场景**：
- 查看完整的 HTTP 请求/响应
- 检查数据库查询内容
- 分析 API 调用 payload
- 排查协议交互问题

### 3.5 Wireshark 统计功能

| 菜单项 | 功能 | SRE 用途 |
|--------|------|----------|
| **Statistics → Protocol Hierarchy** | 协议层级统计 | 了解流量组成 |
| **Statistics → Conversations** | 会话统计 | 找出流量最大的主机对 |
| **Statistics → Endpoints** | 端点统计 | 分析单主机流量 |
| **Statistics → I/O Graphs** | I/O 图表 | 可视化流量趋势 |
| **Statistics → TCP Stream Graphs → Time-Sequence (Stevens)** | TCP 时序图 | 分析 TCP 窗口和重传 |
| **Statistics → TCP Stream Graphs → Round Trip Time** | RTT 图表 | 延迟分析 |
| **Statistics → DNS** | DNS 统计 | 分析 DNS 查询模式 |
| **Analyze → Expert Info** | 专家信息 | 自动检测异常（重传、零窗口等） |

---

## 4. SRE 实战案例：TCP 重传分析

### 4.1 问题描述

**背景**：生产环境中，某微服务 A 调用微服务 B 的 gRPC 接口时，P99 延迟从 50ms 飙升到 5000ms，大量请求超时。

**症状**：
- 应用日志中出现 `context deadline exceeded`
- 监控系统显示服务 B 的 CPU 和内存正常
- 网络延迟监控显示间歇性 spikes

### 4.2 排查步骤

#### 步骤 1：确认问题范围

```bash
# 在服务 A 上测试到服务 B 的基础网络连通性
ping -c 10 10.0.1.50

# 使用 curl 测试 HTTP 端点延迟
curl -o /dev/null -s -w "time_namelookup: %{time_namelookup}\ntime_connect: %{time_connect}\ntime_starttransfer: %{time_starttransfer}\ntime_total: %{time_total}\n" http://10.0.1.50:8080/health

# 使用 mtr 查看路由路径和质量
mtr -r -c 100 10.0.1.50
```

#### 步骤 2：tcpdump 抓包分析

```bash
# 在服务 A 上抓取与服务 B 之间的流量
sudo tcpdump -i any -nn -s 0 -w /tmp/grpc_issue.pcap host 10.0.1.50 and port 9090

# 让流量跑 30 秒
sleep 30

# 停止抓包后分析
```

#### 步骤 3：分析重传

```bash
# 方法 1：用 tcpdump 直接查看重传包
sudo tcpdump -r /tmp/grpc_issue.pcap -nn 'tcp[tcpflags] & tcp-rst != 0'

# 方法 2：统计重传数量
sudo tcpdump -r /tmp/grpc_issue.pcap -nn | grep -c 'retransmit'

# 方法 3：提取 TCP 重传的详细时间线
sudo tcpdump -r /tmp/grpc_issue.pcap -nn -vv \
  'src host 10.0.1.100 and dst host 10.0.1.50 and tcp' | head -50

# 方法 4：用 tshark（Wireshark 命令行版）分析重传
tshark -r /tmp/grpc_issue.pcap -Y "tcp.analysis.retransmission" -T fields \
  -e frame.number -e frame.time -e ip.src -e ip.dst -e tcp.seq -e tcp.len

# 方法 5：计算重传率
total=$(tshark -r /tmp/grpc_issue.pcap -Y tcp -T fields -e frame.number 2>/dev/null | wc -l)
retrans=$(tshark -r /tmp/grpc_issue.pcap -Y "tcp.analysis.retransmission" -T fields -e frame.number 2>/dev/null | wc -l)
echo "总TCP包: $total"
echo "重传包: $retrans"
echo "重传率: $(echo "scale=2; $retrans * 100 / $total" | bc)%"
```

#### 步骤 4：用 Wireshark 深入分析

```bash
# 将 pcap 文件下载到本地用 Wireshark 打开
wireshark /tmp/grpc_issue.pcap &

# 在 Wireshark 中执行以下操作：
# 1. 应用过滤器: tcp.analysis.retransmission
# 2. 查看 Expert Info（Analyze → Expert Info）
# 3. 查看 TCP Stream Graph（Statistics → TCP Stream Graphs）
# 4. Follow TCP Stream 查看完整交互
```

### 4.3 分析结果与根因

**发现**：
```
分析结果显示：
- TCP 重传率高达 15%（正常应 < 1%）
- 大量 Duplicate ACK
- RTT 从 1ms 波动到 2000ms
- 没有 RST 包，说明不是连接被拒绝
```

**根因定位**：
| 可能原因 | 排除方法 | 结论 |
|----------|----------|------|
| 对端服务过载 | 检查服务 B CPU/内存/队列 | ❌ 排除（资源正常） |
| 网络拥塞 | mtr 查看丢包、tcpdump 看重传模式 | ✅ 确认（中间链路拥塞） |
| MTU 不匹配 | `ping -s 1472 -M do 10.0.1.50` 测试 | ❌ 排除（分片正常） |
| 网卡/交换机故障 | 检查端口错误计数 | ✅ 辅助因素（CRC 错误） |

```bash
# 检查网卡错误
ip -s link show eth0

# 检查 MTU
ip link show eth0 | grep mtu

# MTU 测试（测试不同大小的包是否能通过）
ping -s 1472 -M do 10.0.1.50   # 1500 - 28(IP+ICMP头) = 1472
ping -s 8972 -M do 10.0.1.50   # Jumbo frame 测试
```

### 4.4 解决方案

```bash
# 方案 1：切换网络路径（如果有多条路由）
ip route add 10.0.1.0/24 via 10.0.0.2 dev eth1

# 方案 2：调整 TCP 参数（临时缓解）
sudo sysctl -w net.ipv4.tcp_retries2=5      # 减少重试次数（默认15）
sudo sysctl -w net.ipv4.tcp_syn_retries=3    # SYN 重试减少

# 方案 3：联系网络团队修复交换机端口
# 方案 4：启用 ECN（显式拥塞通知）
sudo sysctl -w net.ipv4.tcp_ecn=1
```

---

## 5. 练习

### 练习 1：抓取 HTTP 流量

**目标**：抓取并分析 HTTP 请求和响应

```bash
# 1. 在终端 1 中启动一个简单的 HTTP 服务
python3 -m http.server 8080 --bind 0.0.0.0

# 2. 在终端 2 中启动抓包
sudo tcpdump -i any -nn -A -s 0 -w /tmp/http_capture.pcap port 8080

# 3. 在终端 3 中发起 HTTP 请求
curl http://127.0.0.1:8080/

# 4. 停止抓包（Ctrl+C），然后分析
sudo tcpdump -r /tmp/http_capture.pcap -nn -A

# 5. 只查看 HTTP 请求内容
sudo tcpdump -r /tmp/http_capture.pcap -nn -A 'tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x47455420'
# (0x47455420 = "GET " 的十六进制)

# 6. 清理
pkill -f "python3 -m http.server"
rm /tmp/http_capture.pcap
```

### 练习 2：抓取 DNS 查询

**目标**：观察 DNS 查询和响应的完整过程

```bash
# 1. 启动 DNS 抓包（DNS 使用 UDP 53 端口）
sudo tcpdump -i any -nn -s 0 -w /tmp/dns_capture.pcap port 53 &
TCPDUMP_PID=$!

# 2. 发起 DNS 查询
dig google.com A
dig baidu.com AAAA
dig example.com MX

# 3. 停止抓包
kill $TCPDUMP_PID

# 4. 分析 DNS 流量
sudo tcpdump -r /tmp/dns_capture.pcap -nn -v

# 5. 使用 tshark 详细解析 DNS 响应
tshark -r /tmp/dns_capture.pcap -Y "dns" -T fields \
  -e frame.number \
  -e ip.src \
  -e ip.dst \
  -e dns.qry.name \
  -e dns.a \
  -e dns.resp.ttl

# 6. 统计 DNS 查询的域名
tshark -r /tmp/dns_capture.pcap -Y "dns.flags.response == 0" -T fields \
  -e dns.qry.name 2>/dev/null | sort | uniq -c | sort -rn

# 7. 清理
rm /tmp/dns_capture.pcap
```

### 练习 3：综合场景 — 模拟延迟并抓包分析

```bash
# 1. 使用 tc 模拟网络延迟
sudo tc qdisc add dev lo root netem delay 100ms

# 2. 抓包验证延迟
sudo tcpdump -i lo -nn -w /tmp/latency_test.pcap port 8080 &
TCPDUMP_PID=$!

# 3. 发起请求
python3 -m http.server 8080 --bind 127.0.0.1 &
HTTP_PID=$!
sleep 1
curl -o /dev/null -w "Total time: %{time_total}s\n" http://127.0.0.1:8080/

# 4. 停止
kill $TCPDUMP_PID $HTTP_PID

# 5. 分析 TCP 时序
tshark -r /tmp/latency_test.pcap -Y tcp -T fields \
  -e frame.time_relative -e tcp.flags.str -e tcp.len 2>/dev/null

# 6. 清理网络规则
sudo tc qdisc del dev lo root
rm /tmp/latency_test.pcap
```

### 练习 4：BPF 过滤实战

```bash
# 综合练习：构造复杂的 BPF 过滤器
# 场景：只抓取来自内网、目标为数据库端口、且是 TCP SYN 的包

sudo tcpdump -i any -nn \
  'src net 10.0.0.0/8 and dst port 3306 and tcp[tcpflags] & tcp-syn != 0'

# 场景：排除本地回环和 Docker 网桥流量
sudo tcpdump -i any -nn \
  'not net 127.0.0.0/8 and not net 172.17.0.0/16'

# 场景：抓取大于 1000 字节的 UDP 包
sudo tcpdump -i any -nn 'udp and greater 1000'
```

---

## 6. 进阶技巧

### 6.1 生产环境抓包最佳实践

```bash
# ✅ DO: 使用 -c 限制包数量，避免磁盘写满
sudo tcpdump -i eth0 -nn -c 10000 -w /tmp/limited.pcap

# ✅ DO: 使用 BPF 过滤减少捕获量
sudo tcpdump -i eth0 -nn -w /tmp/filtered.pcap host 10.0.1.50 and port 443

# ✅ DO: 压缩 pcap 文件
sudo tcpdump -i eth0 -nn -w - | gzip > /tmp/capture.pcap.gz

# ❌ DON'T: 不加限制地在生产环境抓包
sudo tcpdump -i any -w /tmp/unlimited.pcap  # 磁盘可能爆满！

# ✅ DO: 使用 ring buffer 自动轮转
sudo tcpdump -i eth0 -nn -G 300 -W 5 -w /tmp/capture_%Y%m%d_%H%M%S.pcap
# -G 300: 每 300 秒切换文件
# -W 5:  最多保留 5 个文件，自动覆盖最旧的
```

### 6.2 与 tshark 配合

```bash
# tshark 是 Wireshark 的命令行版本，解析能力更强

# 统计 TCP 会话
tshark -r capture.pcap -q -z conv,tcp

# HTTP 请求统计
tshark -r capture.pcap -Y "http.request" -T fields \
  -e http.request.method -e http.request.uri -e ip.src | sort | uniq -c | sort -rn

# DNS 查询统计
tshark -r capture.pcap -Y "dns.qry.name" -T fields -e dns.qry.name | sort | uniq -c | sort -rn
```

### 6.3 常见问题排查命令速查

| 问题 | tcpdump 命令 |
|------|-------------|
| 连接被拒绝 | `tcpdump -i any 'tcp[tcpflags] & tcp-rst != 0'` |
| 连接超时 | `tcpdump -i any 'host <目标IP>'` 看是否有 SYN-ACK |
| DNS 解析慢 | `tcpdump -i any port 53` |
| HTTP 慢响应 | `tcpdump -i any -A port 80` |
| TLS 握手失败 | `tcpdump -i any port 443` 看 ClientHello/ServerHello |
| 大量连接建立 | `tcpdump -i any 'tcp[tcpflags] & tcp-syn != 0'` |
| 数据包分片 | `tcpdump -i any 'ip[6:2] & 0x1fff != 0'` |

---

## 7. 资源

### 官方文档

| 资源 | 链接 |
|------|------|
| tcpdump 官方手册 | https://www.tcpdump.org/manpages/tcpdump.1.html |
| tcpdump 官网 | https://www.tcpdump.org/ |
| Wireshark 用户指南 | https://www.wireshark.org/docs/wsug_html_chunked/ |
| Wireshark 下载 | https://www.wireshark.org/download.html |
| Wireshark Display Filter Reference | https://www.wireshark.org/docs/dfref/ |

### 深入学习

| 资源 | 链接 |
|------|------|
| BPF 过滤语法详细文档 | https://www.tcpdump.org/manpages/pcap-filter.7.html |
| TCP 重传分析指南 | https://wiki.wireshark.org/TCP_Analysis |
| Wireshark 专家信息说明 | https://wiki.wireshark.org/Expert |
| 网络排错方法论 | https://github.com/leandromoreira/digital-ocean-networking-tutorial |
| tc 网络模拟工具 | https://man7.org/linux/man-pages/man8/tc.8.html |

### 在线练习

| 资源 | 链接 |
|------|------|
| Wireshark 官方 Sample Captures | https://wiki.wireshark.org/SampleCaptures |
| tcpdump 教程 (Daniel Miessler) | https://danielmiessler.com/p/tcpdump/ |
| BPF 语法在线参考 | https://biot.com/capstats/bpf.html |

---

## 📝 今日总结

**关键收获**：
1. tcpdump 是 SRE 网络排查的核心工具，必须熟练使用 BPF 过滤语法
2. BPF 的核心：`type (host/net/port)` + `dir (src/dst)` + `proto (tcp/udp/icmp)` + `逻辑运算符`
3. tcpdump 负责「抓」，Wireshark 负责「析」，两者配合效率最高
4. TCP 重传是网络问题的常见指标，重传率 > 1% 就需要关注
5. 生产环境抓包必须有限制：`-c` 限数量、BPF 过滤、ring buffer 轮转

**明日预告**：Day 39 — iptables/nftables 防火墙 + 云安全组

---

> 💡 **SRE 心法**：「网络问题的答案都在数据包里。」学会看包，你就掌握了解决一半网络问题的能力。
