# Day 38: tcpdump 抓包分析

> 📅 日期：2026-05-02
> 📖 学习主题：tcpdump 抓包分析 — 从原理到 SRE 实战
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 30 TCP 协议详解、Day 32 IP 协议、Day 37 nc/curl/wget

## 🎯 学习目标

- 理解 tcpdump 的工作原理（libpcap、AF_PACKET 套接字、内核抓包路径）
- 掌握 BPF（Berkeley Packet Filter）过滤语法，能构造复杂的抓包表达式
- 能解读 tcpdump 输出中的时间戳、TCP 标志、序列号等关键信息
- 掌握抓包文件管理（-w/-r）及与 Wireshark/tshark 的配合使用
- 能独立完成 SRE 生产环境中的网络故障排查

---

## 📖 核心知识点

### 1. tcpdump 原理与架构

#### 1.1 tcpdump 是什么

tcpdump 是 Linux 系统中最经典的**命令行抓包工具**，工作在数据链路层，能够捕获流经网卡的所有数据包。它是 SRE 排查网络问题的第一利器。

**核心特点**：

| 特性 | 说明 |
|------|------|
| 基于 libpcap | 使用 libpcap 库进行跨平台抓包 |
| 内核级抓包 | 通过 AF_PACKET 套接字在内核态捕获数据包 |
| BPF 过滤 | 在内核态过滤数据包，减少用户态拷贝开销 |
| 轻量高效 | 命令行工具，适合服务器环境 |
| 输出灵活 | 支持详细/精简/十六进制/ASCII 等多种输出格式 |

#### 1.2 抓包架构全景

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户空间 (User Space)                     │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────────────────────┐  │
│   │ tcpdump  │───→│ libpcap  │───→│ AF_PACKET 套接字          │  │
│   │ (CLI)    │    │ (库)     │    │ (内核↔用户态桥梁)         │  │
│   └──────────┘    └──────────┘    └─────────────┬────────────┘  │
│                                                  │              │
├──────────────────────────────────────────────────┼──────────────┤
│                        内核空间 (Kernel Space)    │              │
│                                                  ▼              │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    网卡驱动 (NIC Driver)                  │   │
│   │                         │                                │   │
│   │                         ▼                                │   │
│   │              ┌─────────────────────┐                     │   │
│   │              │  Ring Buffer        │  ← 数据包暂存区      │   │
│   │              │  (环形缓冲区)        │                     │   │
│   │              └─────────┬───────────┘                     │   │
│   │                        │                                 │   │
│   │                        ▼                                 │   │
│   │              ┌─────────────────────┐                     │   │
│   │              │  BPF 过滤器         │  ← 内核态过滤        │   │
│   │              │  (Berkeley Packet   │     只拷贝匹配的包   │   │
│   │              │   Filter)           │                     │   │
│   │              └─────────┬───────────┘                     │   │
│   │                        │                                 │   │
│   │            ┌───────────┼───────────┐                     │   │
│   │            ▼           ▼           ▼                     │   │
│   │     ┌──────────┐ ┌──────────┐ ┌──────────┐              │   │
│   │     │tcpdump   │ │内核协议栈│ │其他AF_PKT│              │   │
│   │     │的副本    │ │正常处理  │ │用户      │              │   │
│   │     └──────────┘ └──────────┘ └──────────┘              │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.3 libpcap 工作原理

libpcap（Packet Capture Library）是 tcpdump 的核心依赖库，提供了跨平台的抓包接口。

**工作流程**：

```
1. tcpdump 调用 pcap_open_live() 打开网络接口
       │
       ▼
2. libpcap 创建 AF_PACKET 原始套接字
       │
       ▼
3. 将 BPF 过滤器编译为字节码
       │
       ▼
4. 通过 setsockopt() 将 BPF 字节码注入内核
       │
       ▼
5. 内核 BPF 虚拟机对每个数据包执行过滤
       │
       ▼
6. 匹配的数据包从 Ring Buffer 拷贝到用户空间
       │
       ▼
7. tcpdump 格式化输出数据包信息
```

**关键系统调用**：

| 系统调用 | 作用 |
|----------|------|
| `socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL))` | 创建原始套接字，捕获所有协议 |
| `setsockopt(SO_ATTACH_FILTER)` | 将 BPF 过滤器附加到套接字 |
| `recvfrom()` / `read()` | 从套接字读取数据包 |
| `mmap()` | 内存映射 Ring Buffer，减少拷贝 |

#### 1.4 AF_PACKET 套接字

AF_PACKET 是 Linux 内核提供的原始套接字族，工作在数据链路层。

```bash
# 查看系统中的 AF_PACKET 套接字
sudo ss -f packet -a

# 查看 tcpdump 使用的文件描述符
sudo ls -la /proc/$(pgrep tcpdump)/fd/ 2>/dev/null

# 查看 Ring Buffer 大小
sudo ethtool -g eth0 2>/dev/null

# 调整 Ring Buffer（减少丢包）
sudo ethtool -G eth0 rx 4096 tx 4096
```

**AF_PACKET 的两种模式**：

| 模式 | 说明 | 性能 |
|------|------|------|
| SOCK_RAW | 收到完整的以太网帧（含 MAC 头） | tcpdump 默认使用 |
| SOCK_DGRAM | 去掉以太网头，从 IP 层开始 | 较少使用 |

#### 1.5 数据包在内核中的路径

```
网卡收到数据包
      │
      ▼
DMA 写入 Ring Buffer
      │
      ▼
硬中断 → 软中断 (NAPI)
      │
      ├──→ AF_PACKET 套接字 → tcpdump（抓包副本）
      │
      ├──→ Netfilter (iptables/nftables)
      │        │
      │        ▼
      │    PREROUTING → 路由判断 → INPUT/FORWARD/OUTPUT → POSTROUTING
      │
      └──→ 内核协议栈正常处理
               │
               ▼
           应用程序（通过 socket recv）
```

**SRE 关键点**：
- tcpdump 抓到的是 **AF_PACKET 层**的副本，不影响正常数据包处理
- 如果 Ring Buffer 满了，tcpdump 会丢包（显示 `dropped by kernel`）
- BPF 过滤在内核态执行，未匹配的包不会拷贝到用户态

#### 1.6 安装 tcpdump

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y tcpdump

# RHEL/CentOS/Rocky
sudo yum install -y tcpdump

# Alpine（容器环境常见）
apk add tcpdump

# Arch Linux
sudo pacman -S tcpdump

# 验证安装
tcpdump --version
# 输出示例：tcpdump version 4.99.4
#           libpcap version 1.10.4

# 检查 libpcap 版本
ldd $(which tcpdump) | grep pcap
```

---

### 2. tcpdump 命令详解

#### 2.1 基本命令格式

```bash
tcpdump [选项] [过滤表达式]
```

#### 2.2 常用选项速查表

| 选项 | 说明 | 示例 |
|------|------|------|
| `-i <interface>` | 指定网卡 | `tcpdump -i eth0` |
| `-i any` | 监听所有网卡 | `tcpdump -i any` |
| `-n` | 不解析主机名 | `tcpdump -n` |
| `-nn` | 不解析主机名和端口号 | `tcpdump -nn` |
| `-c <count>` | 捕获指定数量后退出 | `tcpdump -c 100` |
| `-w <file>` | 写入 pcap 文件 | `tcpdump -w capture.pcap` |
| `-r <file>` | 读取 pcap 文件 | `tcpdump -r capture.pcap` |
| `-s 0` | 捕获完整包（不截断） | `tcpdump -s 0` |
| `-s <len>` | 截断到指定长度 | `tcpdump -s 96` |
| `-v` / `-vv` / `-vvv` | 详细程度递增 | `tcpdump -vvv` |
| `-X` | 十六进制 + ASCII 输出 | `tcpdump -X` |
| `-A` | 仅 ASCII 输出（适合 HTTP） | `tcpdump -A` |
| `-e` | 显示链路层头（MAC 地址） | `tcpdump -e` |
| `-q` | 精简输出 | `tcpdump -q` |
| `-l` | 行缓冲（配合管道） | `tcpdump -l \| grep` |
| `-t` | 不显示时间戳 | `tcpdump -t` |
| `-tttt` | 显示详细日期时间 | `tcpdump -tttt` |
| `-G <seconds>` | 按时间轮转文件 | `tcpdump -G 300 -w %Y%m%d_%H%M%S.pcap` |
| `-W <count>` | 最大文件数 | `tcpdump -W 5` |
| `-C <MB>` | 按大小轮转文件 | `tcpdump -C 100 -w cap.pcap` |
| `--immediate-mode` | 立即模式（减少延迟） | `tcpdump --immediate-mode` |
| `-j <timestamp>` | 时间戳格式 | `tcpdump -j adapter` |
| `-Z <user>` | 降权运行 | `tcpdump -Z nobody` |

#### 2.3 输出格式详解

```bash
# 典型 TCP 输出
$ sudo tcpdump -i eth0 -nn -c 5
14:23:45.123456 IP 10.0.1.100.45678 > 10.0.1.50.80: Flags [S], seq 1234567, win 65535, options [mss 1460,sackOK,TS val 1234 ecr 0,nop,wscale 7], length 0
14:23:45.123789 IP 10.0.1.50.80 > 10.0.1.100.45678: Flags [S.], seq 9876543, ack 1234568, win 65535, options [mss 1460,sackOK,TS val 5678 ecr 1234,nop,wscale 7], length 0
14:23:45.123901 IP 10.0.1.100.45678 > 10.0.1.50.80: Flags [.], ack 1, win 512, length 0
14:23:45.124567 IP 10.0.1.100.45678 > 10.0.1.50.80: Flags [P.], seq 1:101, ack 1, win 512, length 100
14:23:45.125678 IP 10.0.1.50.80 > 10.0.1.100.45678: Flags [.], ack 101, win 512, length 0
```

**输出字段逐行解读**：

```
14:23:45.123456 IP 10.0.1.100.45678 > 10.0.1.50.80: Flags [S], seq 1234567, win 65535, options [...], length 0
│              │  │              │       │         │       │              │         │           │
│              │  │              │       │         │       │              │         │           └─ 数据长度
│              │  │              │       │         │       │              │         └─ TCP 选项
│              │  │              │       │         │       │              └─ 窗口大小
│              │  │              │       │         │       └─ 序列号
│              │  │              │       │         └─ TCP 标志
│              │  │              │       └─ 目标 IP.端口
│              │  │              └─ 源 IP.端口
│              │  └─ 协议 (IP)
│              └─ 时间戳
└─ 时间 (时:分:秒.微秒)
```

**TCP 标志位含义**：

| 标志 | tcpdump 显示 | 含义 |
|------|-------------|------|
| SYN | `[S]` | 同步序列号（建立连接） |
| SYN+ACK | `[S.]` | 确认同步（连接确认） |
| ACK | `[.]` | 确认 |
| FIN | `[F]` | 完成（关闭连接） |
| FIN+ACK | `[F.]` | 确认完成 |
| RST | `[R]` | 重置连接 |
| PSH | `[P]` | 推送数据 |
| PSH+ACK | `[P.]` | 推送数据并确认 |

#### 2.4 列出可用网卡

```bash
# 列出所有可用网卡
tcpdump -D
# 输出示例：
# 1.eth0 [Up, Running]
# 2.lo [Up, Running, Loopback]
# 3.docker0 [Up, Running]
# 4.any (Pseudo-device that captures on all interfaces) [Up, Running]
# 5.bluetooth-monitor (Bluetooth Linux Monitor) [none]
# 6.nflog (Linux netfilter log (NFLOG) interface) [none]
# 7.nfqueue (Linux netfilter queue (NFQUEUE) interface) [none]

# 查看网卡信息
ip -br link show
```

---

### 3. BPF 过滤语法详解

#### 3.1 BPF 原理

BPF（Berkeley Packet Filter）是一种在内核态执行的虚拟机，用于高效过滤数据包。

**BPF 的优势**：
- 在内核态过滤，减少用户态数据拷贝
- 编译为字节码，执行效率高
- 支持复杂的布尔逻辑表达式

**过滤器编译流程**：

```
BPF 表达式字符串
  "host 10.0.1.1 and port 80"
        │
        ▼
  pcap_compile() 编译
        │
        ▼
  BPF 字节码（指令数组）
        │
        ▼
  setsockopt(SO_ATTACH_FILTER) 注入内核
        │
        ▼
  内核 BPF 虚拟机执行
        │
        ▼
  匹配 → 拷贝到用户态
  不匹配 → 丢弃（不拷贝）
```

#### 3.2 BPF 原语（Primitives）

BPF 过滤表达式由**原语**和**组合运算符**构成。

**Type 原语（指定匹配对象）**：

| 原语 | 说明 | 示例 |
|------|------|------|
| `host` | 匹配主机 IP | `host 10.0.1.100` |
| `net` | 匹配网段 | `net 10.0.0.0/24` |
| `port` | 匹配端口 | `port 80` |
| `portrange` | 匹配端口范围 | `portrange 8000-9000` |
| `gateway` | 匹配网关 | `gateway 10.0.0.1` |

**Direction 原语（指定方向）**：

| 原语 | 说明 | 示例 |
|------|------|------|
| `src` | 源地址/端口 | `src host 10.0.1.100` |
| `dst` | 目标地址/端口 | `dst port 80` |
| `src or dst` | 源或目标（默认） | `src or dst port 80` |
| `src and dst` | 源且目标 | `src and dst host 10.0.1.100` |
| `inbound` | 入站 | `inbound` |
| `outbound` | 出站 | `outbound` |

**Protocol 原语（指定协议）**：

| 原语 | 说明 | 示例 |
|------|------|------|
| `tcp` | TCP 协议 | `tcp` |
| `udp` | UDP 协议 | `udp` |
| `icmp` | ICMP 协议 | `icmp` |
| `icmp6` | ICMPv6 协议 | `icmp6` |
| `arp` | ARP 协议 | `arp` |
| `rarp` | RARP 协议 | `rarp` |
| `ip` | IPv4 | `ip` |
| `ip6` | IPv6 | `ip6` |
| `ether` | 以太网帧 | `ether` |

#### 3.3 按主机过滤

```bash
# 抓取与特定 IP 相关的所有流量（双向）
sudo tcpdump -i eth0 host 192.168.1.100

# 只抓来源是某 IP 的包
sudo tcpdump -i eth0 src host 192.168.1.100

# 只抓目标是某 IP 的包
sudo tcpdump -i eth0 dst host 192.168.1.100

# 抓取与某 MAC 地址相关的流量
sudo tcpdump -i eth0 ether host aa:bb:cc:dd:ee:ff

# 按主机名过滤（不推荐，需要 DNS 解析）
sudo tcpdump -i eth0 host example.com
```

#### 3.4 按端口过滤

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

# 多个端口
sudo tcpdump -i eth0 port 80 or port 443
```

#### 3.5 按网络过滤

```bash
# 抓取整个子网的流量
sudo tcpdump -i eth0 net 192.168.1.0/24

# 更简洁的 CIDR 写法
sudo tcpdump -i eth0 net 10.0.0.0/8

# 排除某个网段
sudo tcpdump -i eth0 not net 172.16.0.0/12

# 精确匹配网段（使用 mask）
sudo tcpdump -i eth0 'net 10.0.0.0 mask 255.255.255.0'
```

#### 3.6 按协议过滤

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
sudo tcpdump -i eth0 tcp port 27017  # MongoDB
```

#### 3.7 逻辑运算符

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

# 组合使用
sudo tcpdump -i eth0 src net 10.0.0.0/8 and \( port 80 or port 443 \)

# 排除广播和本地回环
sudo tcpdump -i eth0 not broadcast and not net 127.0.0.0/8

# 复杂组合：内网到外网的 HTTP 流量
sudo tcpdump -i eth0 'src net 10.0.0.0/8 and dst not net 10.0.0.0/8 and tcp port 80'
```

#### 3.8 TCP 标志位过滤

这是排查 TCP 连接问题的高级技巧：

```bash
# 抓取所有 SYN 包（新建连接）
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0'

# 只抓纯 SYN 包（不含 ACK，即新建连接请求）
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0'

# 抓取 SYN+ACK 包（服务端确认）
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn|tcp-ack) == (tcp-syn|tcp-ack)'

# 抓取 FIN 包（关闭连接）
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-fin != 0'

# 抓取 RST 包（连接重置/拒绝）
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-rst != 0'

# 抓取 PSH 包（数据推送）
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-push != 0'

# SYN Flood 攻击特征（大量 SYN 无 ACK）
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0 and tcp[tcpflags] & (tcp-ack) == 0' -c 1000

# 标志位速查表
# tcp-syn    = 0x02
# tcp-ack    = 0x10
# tcp-fin    = 0x01
# tcp-rst    = 0x04
# tcp-push   = 0x08
# tcp-urg    = 0x20
```

**BPF 字节偏移计算**：

```
TCP 头部结构（简化）：
+--------+--------+---------+----------+
| 源端口 | 目端口 | 序列号  | 确认号   |
| 2字节  | 2字节  | 4字节   | 4字节    |
+--------+--------+---------+----------+
|偏移/保留| 标志位 | 窗口大小| ...      |
| 1字节  | 1字节  | 2字节   |          |
+--------+--------+---------+----------+

偏移 12 字节处是「数据偏移 + 保留 + 标志位」
tcp[12:1] 取出这个字节
& 0xf0 >> 4 得到数据偏移（TCP 头部长度）
tcp[13:1] 取出标志位字节
```

#### 3.9 数据包大小过滤

```bash
# 抓取大于 1000 字节的包
sudo tcpdump -i eth0 'greater 1000'

# 抓取小于 64 字节的包（可能是控制包）
sudo tcpdump -i eth0 'less 64'

# 结合协议
sudo tcpdump -i eth0 'tcp and greater 1000'
sudo tcpdump -i eth0 'udp and less 100'
```

#### 3.10 应用层协议过滤

```bash
# 抓取 HTTP GET 请求
sudo tcpdump -i eth0 -A -s 0 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)'
sudo tcpdump -i eth0 -A -s 0 'tcp port 80 and tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x47455420'
# 0x47455420 = "GET " 的十六进制

# 抓取 HTTP POST 请求
sudo tcpdump -i eth0 -A -s 0 'tcp port 80 and tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x504f5354'
# 0x504f5354 = "POST" 的十六进制

# 抓取 DNS 查询（UDP 53）
sudo tcpdump -i eth0 -nn port 53

# 抓取 DNS 查询请求（QR=0）
sudo tcpdump -i eth0 'udp port 53 and udp[10] & 0x80 = 0'

# 抓取 DNS 响应（QR=1）
sudo tcpdump -i eth0 'udp port 53 and udp[10] & 0x80 != 0'

# 抓取 HTTPS TLS ClientHello
sudo tcpdump -i eth0 -nn -s 0 'tcp port 443 and tcp[((tcp[12]&0xf0)>>2):1] = 0x16'
# 0x16 = TLS Handshake 类型
```

#### 3.11 BPF 过滤语法速查表

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
| TCP FIN | `'tcp[tcpflags] & tcp-fin != 0'` |
| 数据包大小 | `greater 100` / `less 64` |
| HTTP GET | `tcp[((tcp[12:1]&0xf0)>>2):4]=0x47455420` |
| DNS 查询 | `udp port 53 and udp[10]&0x80=0` |
| ARP 请求 | `arp` |
| ICMP echo | `icmp[0]=8` (请求) / `icmp[0]=0` (响应) |

---

### 4. 抓包文件管理

#### 4.1 保存抓包文件

```bash
# 保存到 pcap 文件
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/capture.pcap

# 限制包数量后保存
sudo tcpdump -i eth0 -nn -s 0 -c 10000 -w /tmp/capture.pcap

# 带过滤条件保存
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/http.pcap port 80

# 压缩保存（节省磁盘空间）
sudo tcpdump -i eth0 -nn -s 0 -w - port 80 | gzip > /tmp/capture.pcap.gz

# 按时间轮转（每 5 分钟一个文件，最多保留 12 个）
sudo tcpdump -i eth0 -nn -s 0 -G 300 -W 12 -w /tmp/capture_%Y%m%d_%H%M%S.pcap

# 按大小轮转（每个文件 100MB，最多保留 5 个）
sudo tcpdump -i eth0 -nn -s 0 -C 100 -W 5 -w /tmp/capture.pcap
```

#### 4.2 读取 pcap 文件

```bash
# 读取 pcap 文件
sudo tcpdump -r /tmp/capture.pcap

# 读取时应用过滤
sudo tcpdump -r /tmp/capture.pcap -nn 'host 10.0.1.100'
sudo tcpdump -r /tmp/capture.pcap -nn 'tcp[tcpflags] & tcp-rst != 0'

# 统计包数量
sudo tcpdump -r /tmp/capture.pcap -nn | wc -l

# 读取压缩文件
zcat /tmp/capture.pcap.gz | sudo tcpdump -r -
```

#### 4.3 与 Wireshark/tshark 配合

```bash
# tshark 是 Wireshark 的命令行版本，解析能力更强

# 统计 TCP 会话
tshark -r capture.pcap -q -z conv,tcp

# HTTP 请求统计
tshark -r capture.pcap -Y "http.request" -T fields \
  -e http.request.method -e http.request.uri -e ip.src | sort | uniq -c | sort -rn

# DNS 查询统计
tshark -r capture.pcap -Y "dns.qry.name" -T fields -e dns.qry.name | sort | uniq -c | sort -rn

# 分析 TCP 重传
tshark -r capture.pcap -Y "tcp.analysis.retransmission" -T fields \
  -e frame.number -e frame.time -e ip.src -e ip.dst -e tcp.seq

# 计算重传率
total=$(tshark -r capture.pcap -Y tcp -T fields -e frame.number 2>/dev/null | wc -l)
retrans=$(tshark -r capture.pcap -Y "tcp.analysis.retransmission" -T fields -e frame.number 2>/dev/null | wc -l)
echo "总TCP包: $total, 重传包: $retrans, 重传率: $(echo "scale=2; $retrans * 100 / $total" | bc)%"

# 统计 TLS 版本
tshark -r capture.pcap -Y "tls.handshake.type == 1" -T fields -e tls.handshake.version | sort | uniq -c

# 分析 TCP 时序图数据
tshark -r capture.pcap -Y tcp -T fields \
  -e frame.time_relative -e tcp.flags.str -e tcp.len -e tcp.seq | head -50
```

---

### 5. 高级用法

#### 5.1 抓取特定 TCP 连接的完整交互

```bash
# 步骤 1：先抓取目标 IP 的流量，找到目标端口
sudo tcpdump -i eth0 -nn host 10.0.1.50 -c 20

# 步骤 2：精确抓取该连接
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/conn.pcap \
  host 10.0.1.50 and port 8080

# 步骤 3：用 tshark 追踪流
tshark -r /tmp/conn.pcap -q -z follow,tcp,ascii,0
```

#### 5.2 抓取 HTTP 请求和响应

```bash
# 抓取 HTTP 流量并显示 ASCII 内容
sudo tcpdump -i eth0 -A -s 0 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)'

# 更简洁的方式
sudo tcpdump -i eth0 -A -s 0 port 80 | grep -A 5 "GET\|POST\|HTTP"

# 保存 HTTP 流量并用 tshark 解析
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/http.pcap port 80 &
sleep 30
kill %1

# 解析 HTTP 请求
tshark -r /tmp/http.pcap -Y "http.request" -T fields \
  -e http.request.method -e http.request.uri -e http.host -e http.user_agent

# 解析 HTTP 响应
tshark -r /tmp/http.pcap -Y "http.response" -T fields \
  -e http.response.code -e http.content_type -e http.content_length
```

#### 5.3 抓取 DNS 查询

```bash
# 抓取 DNS 流量
sudo tcpdump -i any -nn port 53

# 只抓 DNS 查询请求
sudo tcpdump -i any -nn 'udp port 53 and udp[10] & 0x80 = 0'

# 只抓 DNS 响应
sudo tcpdump -i any -nn 'udp port 53 and udp[10] & 0x80 != 0'

# 保存 DNS 流量并用 tshark 详细解析
sudo tcpdump -i any -nn -s 0 -w /tmp/dns.pcap port 53 &
dig google.com AAAA
dig example.com MX
kill %1

tshark -r /tmp/dns.pcap -Y "dns" -T fields \
  -e frame.time -e ip.src -e ip.dst -e dns.qry.name -e dns.a -e dns.resp.ttl
```

#### 5.4 抓取 TLS 握手

```bash
# 抓取 TLS 握手过程
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/tls.pcap 'tcp port 443' &
curl -s https://example.com > /dev/null
kill %1

# 用 tshark 解析 TLS 握手
tshark -r /tmp/tls.pcap -Y "tls.handshake" -T fields \
  -e frame.number -e ip.src -e ip.dst -e tls.handshake.type -e tls.handshake.version

# TLS 握手类型：
# 1 = ClientHello
# 2 = ServerHello
# 11 = Certificate
# 12 = ServerKeyExchange
# 14 = ServerHelloDone
# 16 = ClientKeyExchange
# 20 = ChangeCipherSpec
```

#### 5.5 监控网络质量

```bash
# 实时监控 TCP 重传
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0' -l | \
  awk '{print strftime("%H:%M:%S"), $0}'

# 监控 RST 包（连接异常）
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & tcp-rst != 0' -l

# 监控特定服务的连接建立速率
sudo tcpdump -i eth0 -nn 'dst port 80 and tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0' -l | \
  awk '{print strftime("%H:%M:%S"), $3}' | cut -d. -f1-4
```

---

### 6. 性能影响和安全考虑

#### 6.1 性能影响

| 影响因素 | 说明 | 缓解措施 |
|----------|------|----------|
| CPU 开销 | BPF 过滤在内核态执行，CPU 开销较小 | 使用精确的 BPF 过滤器 |
| 内存开销 | Ring Buffer + 用户态缓冲区 | 调整 Ring Buffer 大小 |
| 磁盘 I/O | -w 写文件时有磁盘写入 | 使用 -C/-G 轮转，监控磁盘空间 |
| 丢包 | Ring Buffer 满时丢包 | 增大 Ring Buffer，使用 -s 截断 |

```bash
# 查看 Ring Buffer 大小
sudo ethtool -g eth0

# 查看当前 Ring Buffer 使用情况
sudo ethtool -S eth0 | grep -i ring

# 增大 Ring Buffer（减少丢包）
sudo ethtool -G eth0 rx 4096

# 查看 tcpdump 统计信息（Ctrl+C 停止时显示）
# 输出示例：
# 12345 packets captured
# 12345 packets received by filter
# 0 packets dropped by kernel
# 0 packets dropped by interface
```

#### 6.2 生产环境抓包最佳实践

```bash
# DO: 使用 -c 限制包数量
sudo tcpdump -i eth0 -nn -c 10000 -w /tmp/limited.pcap

# DO: 使用 BPF 过滤减少捕获量
sudo tcpdump -i eth0 -nn -w /tmp/filtered.pcap host 10.0.1.50 and port 443

# DO: 使用 -s 截断（只抓头部，不抓 payload）
sudo tcpdump -i eth0 -nn -s 96 -w /tmp/headers.pcap

# DO: 使用 ring buffer 自动轮转
sudo tcpdump -i eth0 -nn -G 300 -W 5 -w /tmp/cap_%Y%m%d_%H%M%S.pcap

# DO: 使用压缩
sudo tcpdump -i eth0 -nn -s 0 -w - | gzip > /tmp/capture.pcap.gz

# DON'T: 不加限制地在生产环境抓包
# sudo tcpdump -i any -w /tmp/all.pcap  ← 磁盘可能爆满！

# DON'T: 不使用 -nn（DNS 解析会增加开销）
# sudo tcpdump -i eth0 host example.com  ← 会触发 DNS 查询！
```

#### 6.3 安全考虑

| 风险 | 说明 | 缓解措施 |
|------|------|----------|
| 权限泄露 | pcap 文件可能包含敏感数据 | 使用 `-Z` 降权，限制文件权限 |
| 数据暴露 | 抓包可能捕获密码、token | 只抓必要的流量，及时删除 pcap |
| 资源耗尽 | 无限抓包耗尽磁盘/CPU | 使用 -c/-C/-G 限制 |

```bash
# 以 nobody 用户运行（减少权限风险）
sudo tcpdump -i eth0 -Z nobody -w /tmp/capture.pcap

# 设置文件权限
sudo tcpdump -i eth0 -w /tmp/capture.pcap
sudo chmod 600 /tmp/capture.pcap

# 及时清理
rm -f /tmp/capture.pcap
```

---

### 7. SRE 实战案例

#### 7.1 案例一：连接超时 → TCP SYN 被丢弃 → 防火墙规则

**背景**：服务 A 调用服务 B 的 API，偶尔出现 `connection timed out` 错误，错误率约 5%。

**排查过程**：

```bash
# 步骤 1：确认连通性
ping -c 10 10.0.1.50
# 结果：正常，无丢包

# 步骤 2：测试端口连通性
nc -zv -w 5 10.0.1.50 8080
# 结果：有时成功，有时超时

# 步骤 3：tcpdump 抓包分析
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/timeout.pcap host 10.0.1.50 and port 8080

# 在另一个终端发起多次请求
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" --connect-timeout 5 http://10.0.1.50:8080/health
  sleep 1
done

# 步骤 4：分析抓包结果
sudo tcpdump -r /tmp/timeout.pcap -nn 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0'
# 输出：
# 14:23:45.123 IP 10.0.1.100.45678 > 10.0.1.50.8080: Flags [S], seq 1234567
# 14:23:46.124 IP 10.0.1.100.45678 > 10.0.1.50.8080: Flags [S], seq 1234567  ← 1秒后重传
# 14:23:48.125 IP 10.0.1.100.45678 > 10.0.1.50.8080: Flags [S], seq 1234567  ← 2秒后重传
# 14:23:45.456 IP 10.0.1.100.45679 > 10.0.1.50.8080: Flags [S], seq 2345678
# 14:23:45.457 IP 10.0.1.50.8080 > 10.0.1.100.45679: Flags [S.], seq 9876543  ← 有些连接成功

# 分析：
# - 有些 SYN 包没有收到 SYN+ACK（被丢弃）
# - 有些 SYN 包正常收到 SYN+ACK
# - 问题不是完全不通，而是间歇性丢弃

# 步骤 5：检查防火墙规则
sudo iptables -L -n -v | grep -i drop
# 发现有一条限速规则：
# 1234  60K  DROP  tcp  --  *  *  0.0.0.0/0  0.0.0.0/0  tcp dpt:8080 limit: above 100/sec

# 步骤 6：确认限速规则
sudo iptables -L INPUT -n -v --line-numbers | head -20
# 第 5 行：限制每秒最多 100 个新连接到 8080 端口
```

**根因**：防火墙对 8080 端口设置了连接速率限制（100/sec），高峰期超过限制的 SYN 包被 DROP。

**解决方案**：

```bash
# 方案 1：调整限速规则
sudo iptables -R INPUT 5 -p tcp --dport 8080 -m connlimit --connlimit-above 500 -j DROP
# 改用连接数限制而非速率限制

# 方案 2：提高速率限制
sudo iptables -R INPUT 5 -p tcp --dport 8080 -m limit --limit 500/sec --limit-burst 1000 -j ACCEPT

# 方案 3：白名单内网 IP
sudo iptables -I INPUT 4 -s 10.0.0.0/8 -p tcp --dport 8080 -j ACCEPT
```

#### 7.2 案例二：API 慢 → TCP 重传过多 → 网络质量差

**背景**：微服务 A 调用微服务 B 的 gRPC 接口，P99 延迟从 50ms 飙升到 5000ms。

**排查过程**：

```bash
# 步骤 1：curl 时间分解
curl -o /dev/null -s -w \
  "DNS: %{time_namelookup}s\nTCP: %{time_connect}s\nTLS: %{time_appconnect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" \
  http://10.0.1.50:8080/api/data
# 输出：
# DNS: 0.001s
# TCP: 0.003s
# TLS: 0.000s
# TTFB: 4.523s    ← 首字节时间异常！
# Total: 4.524s

# 步骤 2：mtr 查看网络质量
mtr -r -c 100 10.0.1.50
# 发现中间链路有 15% 丢包

# 步骤 3：tcpdump 抓包分析重传
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/slow_api.pcap host 10.0.1.50 and port 9090

# 发起请求
curl -s http://10.0.1.50:9090/api/data

# 步骤 4：分析重传
tshark -r /tmp/slow_api.pcap -Y "tcp.analysis.retransmission" -T fields \
  -e frame.time_relative -e ip.src -e ip.dst -e tcp.seq -e tcp.len
# 输出显示大量重传

# 步骤 5：计算重传率
total=$(tshark -r /tmp/slow_api.pcap -Y tcp -T fields -e frame.number 2>/dev/null | wc -l)
retrans=$(tshark -r /tmp/slow_api.pcap -Y "tcp.analysis.retransmission" -T fields -e frame.number 2>/dev/null | wc -l)
echo "总TCP包: $total, 重传包: $retrans"
echo "重传率: $(echo "scale=2; $retrans * 100 / $total" | bc)%"
# 重传率: 12.50%   ← 正常应 < 1%

# 步骤 6：检查网卡错误
ip -s link show eth0
# 发现 RX errors 和 CRC errors

# 步骤 7：检查 MTU
ip link show eth0 | grep mtu
ping -s 1472 -M do 10.0.1.50
```

**根因**：网络链路质量差（交换机端口 CRC 错误），导致大量 TCP 重传。

**解决方案**：

```bash
# 临时缓解：调整 TCP 参数
sudo sysctl -w net.ipv4.tcp_retries2=5
sudo sysctl -w net.ipv4.tcp_syn_retries=3

# 永久解决：联系网络团队更换交换机端口/线缆
```

#### 7.3 案例三：DNS 解析异常 → DNS 响应被劫持

**背景**：应用日志显示 `dial tcp: lookup api.example.com: no such host`，但 `dig` 命令能正常解析。

**排查过程**：

```bash
# 步骤 1：验证 DNS 解析
dig api.example.com @8.8.8.8
# 正常返回

dig api.example.com @10.0.0.2
# 返回 NXDOMAIN！使用公司 DNS 服务器时解析失败

# 步骤 2：tcpdump 抓取 DNS 流量
sudo tcpdump -i any -nn -s 0 -w /tmp/dns_issue.pcap port 53

# 发起查询
dig api.example.com @10.0.0.2

# 步骤 3：分析 DNS 流量
tshark -r /tmp/dns_issue.pcap -Y "dns" -T fields \
  -e frame.time -e ip.src -e ip.dst -e dns.qry.name -e dns.flags.rcode -e dns.a

# 发现：
# - 查询发到 10.0.0.2（公司 DNS）
# - 响应返回 NXDOMAIN（rcode=3）
# - 但 10.0.0.2 不是我们的 DNS 服务器！

# 步骤 4：检查 DNS 配置
cat /etc/resolv.conf
# nameserver 10.0.0.2    ← 被修改了！

# 步骤 5：检查 DHCP 配置
cat /etc/dhcp/dhclient.conf
# 发现 supersede domain-name-servers 10.0.0.2;  ← 被注入

# 步骤 6：检查是否有恶意进程
sudo lsof -i :53
sudo netstat -tulnp | grep :53
# 发现一个异常的 DNS 代理进程
```

**根因**：恶意软件修改了 DNS 配置，将 DNS 查询重定向到恶意 DNS 服务器，该服务器对某些域名返回 NXDOMAIN。

**解决方案**：

```bash
# 1. 恢复正确的 DNS 配置
sudo tee /etc/resolv.conf > /dev/null << 'EOF'
nameserver 10.0.0.1
nameserver 8.8.8.8
EOF

# 2. 清除恶意进程
sudo kill -9 <pid>

# 3. 加固 DNS 配置
sudo chattr +i /etc/resolv.conf  # 锁定文件防止修改

# 4. 使用 DNS over HTTPS（DoH）防止劫持
```

---

## 💻 实战练习

### 练习 1：基础抓包操作

**目标**：掌握 tcpdump 的基本用法

```bash
# 1. 启动一个 HTTP 服务
python3 -m http.server 8080 --bind 0.0.0.0 &
HTTP_PID=$!

# 2. 在另一个终端抓取 HTTP 流量
sudo tcpdump -i any -nn -A -s 0 -w /tmp/http_capture.pcap port 8080 &
TCPDUMP_PID=$!
sleep 1

# 3. 发起 HTTP 请求
curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/test.html

# 4. 停止抓包
sleep 2
kill $TCPDUMP_PID

# 5. 分析抓包结果
sudo tcpdump -r /tmp/http_capture.pcap -nn -A | grep -E "GET|POST|HTTP|Content-Type"

# 6. 用 tshark 解析 HTTP 请求
tshark -r /tmp/http_capture.pcap -Y "http.request" -T fields \
  -e http.request.method -e http.request.uri

# 7. 清理
kill $HTTP_PID
rm -f /tmp/http_capture.pcap
```

### 练习 2：DNS 查询分析

**目标**：观察 DNS 查询和响应的完整过程

```bash
# 1. 启动 DNS 抓包
sudo tcpdump -i any -nn -s 0 -w /tmp/dns_capture.pcap port 53 &
TCPDUMP_PID=$!

# 2. 发起不同类型的 DNS 查询
dig google.com A
dig google.com AAAA
dig google.com MX
dig google.com NS
dig -x 8.8.8.8  # 反向解析

# 3. 停止抓包
kill $TCPDUMP_PID

# 4. 分析 DNS 流量
sudo tcpdump -r /tmp/dns_capture.pcap -nn -v | head -50

# 5. 用 tshark 详细解析
tshark -r /tmp/dns_capture.pcap -Y "dns" -T fields \
  -e frame.number -e ip.src -e ip.dst -e dns.qry.name -e dns.a -e dns.resp.ttl

# 6. 统计 DNS 查询域名
tshark -r /tmp/dns_capture.pcap -Y "dns.flags.response == 0" -T fields \
  -e dns.qry.name 2>/dev/null | sort | uniq -c | sort -rn

# 7. 清理
rm -f /tmp/dns_capture.pcap
```

### 练习 3：TCP 连接状态分析

**目标**：使用 tcpdump 观察 TCP 三次握手和四次挥手

```bash
# 1. 抓取 TCP SYN/FIN/RST 包
sudo tcpdump -i any -nn 'tcp[tcpflags] & (tcp-syn|tcp-fin|tcp-rst) != 0' -c 50

# 2. 启动 HTTP 服务并抓包
python3 -m http.server 8081 --bind 127.0.0.1 &
HTTP_PID=$!

sudo tcpdump -i lo -nn -s 0 -w /tmp/tcp_states.pcap port 8081 &
TCPDUMP_PID=$!
sleep 1

# 3. 发起请求（观察三次握手 + 数据传输 + 四次挥手）
curl http://127.0.0.1:8081/

# 4. 停止抓包
sleep 1
kill $TCPDUMP_PID

# 5. 分析 TCP 状态
sudo tcpdump -r /tmp/tcp_states.pcap -nn 'tcp[tcpflags] & tcp-syn != 0'
# 应该看到 SYN 和 SYN+ACK

sudo tcpdump -r /tmp/tcp_states.pcap -nn 'tcp[tcpflags] & tcp-fin != 0'
# 应该看到 FIN 包

# 6. 完整时序分析
tshark -r /tmp/tcp_states.pcap -Y tcp -T fields \
  -e frame.time_relative -e ip.src -e ip.dst -e tcp.srcport -e tcp.dstport -e tcp.flags.str -e tcp.len

# 7. 清理
kill $HTTP_PID
rm -f /tmp/tcp_states.pcap
```

### 练习 4：高级 BPF 过滤实战

**目标**：构造复杂的 BPF 过滤器解决实际问题

```bash
# 场景 1：只抓取来自内网、目标为数据库端口、且是 TCP SYN 的包
sudo tcpdump -i any -nn \
  'src net 10.0.0.0/8 and dst port 3306 and tcp[tcpflags] & tcp-syn != 0'

# 场景 2：排除本地回环和 Docker 网桥流量
sudo tcpdump -i any -nn \
  'not net 127.0.0.0/8 and not net 172.17.0.0/16 and not net 172.18.0.0/16'

# 场景 3：抓取大于 1000 字节的 UDP 包
sudo tcpdump -i any -nn 'udp and greater 1000'

# 场景 4：抓取 ICMP echo request（ping 请求）
sudo tcpdump -i any -nn 'icmp[0] = 8'

# 场景 5：抓取 ICMP echo reply（ping 响应）
sudo tcpdump -i any -nn 'icmp[0] = 0'

# 场景 6：抓取所有 RST 包（连接异常重置）
sudo tcpdump -i any -nn 'tcp[tcpflags] & tcp-rst != 0' -c 20

# 场景 7：抓取特定子网间的流量
sudo tcpdump -i any -nn 'src net 10.0.1.0/24 and dst net 10.0.2.0/24'
```

---

## 🎯 面试题精选

### Q1：tcpdump 的工作原理是什么？

**参考答案**：

tcpdump 基于 libpcap 库工作，核心流程如下：

1. **创建套接字**：libpcap 调用 `socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL))` 创建原始套接字，工作在数据链路层
2. **注入 BPF 过滤器**：将用户指定的过滤表达式编译为 BPF 字节码，通过 `setsockopt(SO_ATTACH_FILTER)` 注入内核
3. **内核态过滤**：BPF 虚拟机在内核态对每个数据包执行过滤，只有匹配的包才会被拷贝到用户空间
4. **读取数据包**：通过 `recvfrom()` 或 `mmap()` 从 Ring Buffer 读取匹配的数据包
5. **格式化输出**：tcpdump 解析数据包头部，格式化输出

**关键点**：BPF 过滤在内核态执行，这是 tcpdump 高效的关键。如果没有 BPF 过滤，所有数据包都会拷贝到用户态，性能开销会很大。

### Q2：如何用 tcpdump 抓取 HTTPS 流量？能解密吗？

**参考答案**：

```bash
# 抓取 HTTPS 流量
sudo tcpdump -i eth0 -nn -s 0 -w https.pcap port 443

# 查看 TLS 握手过程
sudo tcpdump -i eth0 -nn -vv port 443

# 用 tshark 解析 TLS 版本和加密套件
tshark -r https.pcap -Y "tls.handshake.type == 2" -T fields \
  -e tls.handshake.version -e tls.handshake.ciphersuite
```

tcpdump 可以抓取 HTTPS 流量的**加密数据**，但**无法解密内容**，因为 TLS 使用端到端加密。

**解密 HTTPS 的方法**（需要提前准备）：
1. **SSLKEYLOGFILE**：在客户端设置环境变量，让浏览器导出 TLS 会话密钥，然后在 Wireshark 中导入
2. **中间人代理**：使用 mitmproxy、Charles 等工具作为中间人（需要安装 CA 证书）
3. **服务端抓包**：在服务端应用层记录日志（不依赖 tcpdump）

### Q3：BPF 过滤器的语法是什么？如何抓取特定 TCP 标志的包？

**参考答案**：

BPF 过滤器由**原语**和**运算符**组成：
- 原语：`host`、`net`、`port`、`tcp`、`udp`、`icmp` 等
- 方向：`src`、`dst`
- 运算符：`and`、`or`、`not`

抓取特定 TCP 标志：

```bash
# SYN 包（新建连接）
tcpdump 'tcp[tcpflags] & tcp-syn != 0'

# 纯 SYN（不含 ACK）
tcpdump 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0'

# RST 包（连接重置）
tcpdump 'tcp[tcpflags] & tcp-rst != 0'

# FIN 包（关闭连接）
tcpdump 'tcp[tcpflags] & tcp-fin != 0'
```

原理：TCP 标志位在 TCP 头部偏移 13 字节处，每个标志占 1 位。`tcp[tcpflags]` 读取该字节，然后用位运算检查特定位。

### Q4：tcpdump 和 Wireshark 有什么区别？各自适合什么场景？

**参考答案**：

| 维度 | tcpdump | Wireshark |
|------|---------|-----------|
| 界面 | 命令行 | GUI（也有 tshark 命令行） |
| 安装 | 轻量（~1MB） | 较重（~100MB+） |
| 适合环境 | 服务器、容器 | 桌面环境 |
| 实时分析 | 依赖 BPF 过滤语法 | 强大的显示过滤器 |
| 协议解析 | 基本 | 数千种协议深度解析 |
| 流追踪 | 不支持 | 一键 Follow Stream |
| 统计 | 有限 | 丰富的统计和图表 |

**SRE 使用场景**：
- **tcpdump**：服务器实时抓包、容器内抓包、脚本自动化、快速排查
- **Wireshark/tshark**：离线深度分析、TCP 时序图、协议解码、可视化

**最佳实践**：先用 tcpdump 在服务器上抓包保存为 pcap 文件，然后下载到本地用 Wireshark 深入分析。

### Q5：如何在生产环境安全地使用 tcpdump？

**参考答案**：

1. **限制包数量**：使用 `-c` 参数限制捕获数量
   ```bash
   sudo tcpdump -i eth0 -nn -c 10000 -w /tmp/cap.pcap
   ```

2. **使用 BPF 过滤**：只捕获需要的流量
   ```bash
   sudo tcpdump -i eth0 -nn host 10.0.1.50 and port 443
   ```

3. **限制文件大小**：使用 `-C` 或 `-G` 轮转
   ```bash
   sudo tcpdump -i eth0 -nn -G 300 -W 5 -w /tmp/cap_%H%M%S.pcap
   ```

4. **截断数据包**：使用 `-s 96` 只抓头部
   ```bash
   sudo tcpdump -i eth0 -nn -s 96 -w /tmp/headers.pcap
   ```

5. **降权运行**：使用 `-Z` 降低权限
   ```bash
   sudo tcpdump -i eth0 -Z nobody -w /tmp/cap.pcap
   ```

6. **监控磁盘空间**：确保有足够空间
   ```bash
   df -h /tmp
   ```

7. **及时清理**：分析完成后删除 pcap 文件

### Q6：如何用 tcpdump 排查 "Connection refused" 错误？

**参考答案**：

```bash
# 抓取与目标 IP 的流量
sudo tcpdump -i eth0 -nn host <目标IP> and port <目标端口>

# 典型输出（Connection refused）：
# 14:23:45.123 IP 10.0.1.100.45678 > 10.0.1.50.8080: Flags [S], seq 1234567
# 14:23:45.124 IP 10.0.1.50.8080 > 10.0.1.100.45678: Flags [R.], seq 0, ack 1234568
```

**解读**：
- 客户端发送 SYN（`[S]`）
- 服务器立即回复 RST+ACK（`[R.]`）
- RST 表示目标端口没有进程在监听

**排查步骤**：
1. 确认服务是否运行：`ss -tlnp | grep 8080`
2. 确认监听地址：是否绑定了 `0.0.0.0` 而非 `127.0.0.1`
3. 检查防火墙：`iptables -L -n | grep 8080`

### Q7：tcpdump 抓包时出现 "dropped by kernel" 是什么意思？如何解决？

**参考答案**：

`dropped by kernel` 表示内核 Ring Buffer 满了，数据包被丢弃。这是因为 tcpdump 读取数据包的速度跟不上网卡接收的速度。

**解决方案**：

1. **增大 Ring Buffer**：
   ```bash
   sudo ethtool -g eth0  # 查看最大值
   sudo ethtool -G eth0 rx 4096  # 增大
   ```

2. **使用 BPF 过滤**：减少需要拷贝的数据包数量

3. **截断数据包**：`-s 96` 只抓头部

4. **使用 `-B` 增大缓冲区**：
   ```bash
   sudo tcpdump -i eth0 -B 4096 -w /tmp/cap.pcap
   ```

5. **使用更快的存储**：SSD 比 HDD 写入更快

---

## 📚 深入阅读

### 官方文档

| 资源 | 链接 |
|------|------|
| tcpdump 官方手册 | https://www.tcpdump.org/manpages/tcpdump.1.html |
| tcpdump 官网 | https://www.tcpdump.org/ |
| BPF 过滤语法 | https://www.tcpdump.org/manpages/pcap-filter.7.html |
| libpcap 文档 | https://www.tcpdump.org/manpages/pcap.3pcap.html |

### Wireshark 资源

| 资源 | 链接 |
|------|------|
| Wireshark 用户指南 | https://www.wireshark.org/docs/wsug_html_chunked/ |
| Wireshark Display Filter | https://www.wireshark.org/docs/dfref/ |
| Wireshark Sample Captures | https://wiki.wireshark.org/SampleCaptures |

### 推荐书籍/博客

| 资源 | 说明 |
|------|------|
| 《Practical Packet Analysis》 | Chris Sanders 著，Wireshark 抓包分析经典 |
| 《The TCP/IP Guide》 | Charles Kozierok 著，TCP/IP 协议权威参考 |
| tcpdump 教程 (Daniel Miessler) | https://danielmiessler.com/p/tcpdump/ |
| BPF 语法在线参考 | https://biot.com/capstats/bpf.html |

---

## ✅ 自检清单

- [ ] 理解 tcpdump 的工作原理（libpcap → AF_PACKET → BPF）
- [ ] 知道 BPF 过滤器在内核态执行的优势
- [ ] 掌握 BPF 过滤语法（host/port/net/proto + 逻辑运算符）
- [ ] 能够使用 TCP 标志位过滤（SYN/FIN/RST）
- [ ] 能解读 tcpdump 输出中的时间戳、TCP 标志、序列号
- [ ] 掌握抓包文件管理（-w/-r/-C/-G）
- [ ] 能配合 tshark 进行高级分析（重传率、HTTP 统计、DNS 统计）
- [ ] 理解生产环境抓包的最佳实践和安全考虑
- [ ] 能够独立完成连接超时、API 慢、DNS 异常的排查
- [ ] 完成所有实战练习
