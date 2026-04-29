# Day 29: OSI 七层模型与 TCP/IP 协议栈

> 📅 日期：2026-04-29
> 📖 学习主题：OSI 七层模型与 TCP/IP 协议栈
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 29 的学习后，你应该掌握：
- 理解 OSI 七层模型的核心概念和每层职责
- 掌握 TCP/IP 四层模型与 OSI 七层模型的对应关系
- 理解数据封装与解封装过程，以及 MTU 对分片的影响
- 能够识别典型协议所在的层级及对应的网络设备
- 能够在 SRE 实战中运用网络分层模型进行故障排查

---

## 📖 详细知识点

### 1. OSI 七层模型概述

#### 1.1 什么是 OSI 模型？

OSI（Open Systems Interconnection）七层模型是国际标准化组织（ISO）于 1984 年提出的网络通信参考模型。它将复杂的网络通信过程抽象为七个层次，每层都有明确的职责和接口定义。

**核心理念**：每一层只与相邻层交互，对上层提供服务，使用下层的功能。这种分层设计使得不同厂商的设备可以互操作，也便于故障定位。

#### 1.2 七层详解

| 层级 | 名称 | 英文 | 核心职责 | 典型协议 | 典型设备 | 数据单位 |
|------|------|------|----------|----------|----------|----------|
| 第 7 层 | 应用层 | Application | 为应用程序提供网络服务接口 | HTTP, HTTPS, DNS, FTP, SMTP, SSH, gRPC | 应用服务器、网关 | 数据（Data） |
| 第 6 层 | 表示层 | Presentation | 数据格式转换、加密解密、压缩解压缩 | SSL/TLS, JPEG, MPEG, ASCII, UTF-8 | 网关 | 数据（Data） |
| 第 5 层 | 会话层 | Session | 建立、管理、终止会话，同步控制 | NetBIOS, RPC, SIP, PPTP | 网关 | 数据（Data） |
| 第 4 层 | 传输层 | Transport | 端到端传输，流量控制，差错控制 | TCP, UDP, SCTP | 防火墙、负载均衡器 | 段（Segment）/ 数据报（Datagram） |
| 第 3 层 | 网络层 | Network | 逻辑寻址、路由选择、分组转发 | IP, ICMP, OSPF, BGP, ARP（部分） | 路由器、三层交换机 | 包（Packet） |
| 第 2 层 | 数据链路层 | Data Link | 物理寻址（MAC）、帧封装、差错检测 | Ethernet, PPP, VLAN, MPLS, ARP | 交换机、网桥、网卡 | 帧（Frame） |
| 第 1 层 | 物理层 | Physical | 比特流的物理传输，电气/光/无线信号 | 以太网物理层、光纤、Wi-Fi 物理层、RS-232 | 网线、光纤、中继器、集线器 | 比特（Bit） |

**记忆口诀**：从下到上 —— **物数网传会表应**（物理层→数据链路层→网络层→传输层→会话层→表示层→应用层）。

#### 1.3 各层详细说明

**应用层（Layer 7）**
- 最接近用户的一层，直接为应用程序提供网络通信服务
- HTTP/HTTPS：Web 服务，SRE 日常监控的重点
- DNS：域名解析，网络故障排查的第一步
- 注意：HTTP 是无状态协议，基于请求-响应模式

**表示层（Layer 6）**
- 负责数据的表示、加密和压缩
- TLS/SSL 加密在表示层完成（实际实现中常与应用层结合）
- 数据编码：JSON、XML、Protocol Buffers 等

**会话层（Layer 5）**
- 管理通信会话的建立、维护和终止
- 对话控制：全双工/半双工模式
- 同步点：在长传输中插入检查点，断点续传的基础

**传输层（Layer 4）**
- **TCP**：面向连接，可靠传输，流量控制，拥塞控制
- **UDP**：无连接，不可靠但低延迟
- 端口号：标识同一主机上的不同应用（0-65535，0-1023 为知名端口）
- SRE 关注重点：连接状态、TIME_WAIT、CLOSE_WAIT 等

**网络层（Layer 3）**
- IP 地址：逻辑寻址，IPv4（32 位）和 IPv6（128 位）
- 路由选择：决定数据包的传输路径
- ICMP：网络诊断协议（ping、traceroute 的基础）
- MTU（Maximum Transmission Unit）：最大传输单元

**数据链路层（Layer 2）**
- MAC 地址：物理寻址，全球唯一（48 位）
- 帧封装：添加头部（源/目的 MAC）和尾部（FCS 校验）
- 交换机基于 MAC 地址表转发帧

**物理层（Layer 1）**
- 比特流的物理传输媒介
- 电信号、光信号、无线电波
- 网线类别（Cat5e、Cat6）、光纤类型

### 2. TCP/IP 协议栈

#### 2.1 TCP/IP 四层模型

实际互联网使用的是 TCP/IP 模型，而非严格的 OSI 模型。两者对应关系如下：

| TCP/IP 四层模型 | OSI 七层模型 | 说明 |
|-----------------|-------------|------|
| 应用层（Application） | 应用层 + 表示层 + 会话层 | TCP/IP 将上三层合并 |
| 传输层（Transport） | 传输层 | 对应一致 |
| 网际层（Internet） | 网络层 | 对应一致 |
| 网络接口层（Network Interface） | 数据链路层 + 物理层 | TCP/IP 将下两层合并 |

```
┌─────────────────────────────────────────┐
│          OSI 七层模型                    │
├─────────────┬───────────────────────────┤
│  应用层     │  HTTP, DNS, SSH, FTP      │
│  表示层     │  TLS, JSON, 加密          │  ← TCP/IP 应用层
│  会话层     │  会话管理, 同步           │
├─────────────┼───────────────────────────┤
│  传输层     │  TCP, UDP                 │  ← TCP/IP 传输层
├─────────────┼───────────────────────────┤
│  网络层     │  IP, ICMP, ARP, BGP       │  ← TCP/IP 网际层
├─────────────┼───────────────────────────┤
│  数据链路层 │  Ethernet, WiFi, VLAN     │  ← TCP/IP 网络接口层
│  物理层     │  网线, 光纤, 无线         │
└─────────────┴───────────────────────────┘
```

#### 2.2 为什么 TCP/IP 模型更实用？

- OSI 模型过于理论化，TCP/IP 模型是实践中形成的
- TCP/IP 模型更关注端到端通信
- 互联网协议族（Internet Protocol Suite）基于 TCP/IP 模型构建
- SRE 日常工作中排查故障，往往在 TCP/IP 模型的各层之间切换

### 3. 数据封装与解封装过程

#### 3.1 封装过程（发送端：自上而下）

当浏览器访问 `https://www.example.com` 时，数据封装过程如下：

```
应用层：    HTTP Request → 添加 HTTP 头部
            ↓
表示层：    数据加密（TLS） → 添加安全头部
            ↓
会话层：    建立会话 → 添加会话标识
            ↓
传输层：    添加 TCP 头部（源端口 54321，目的端口 443） → TCP Segment
            ↓
网络层：    添加 IP 头部（源 IP 192.168.1.100，目的 IP 93.184.216.34） → IP Packet
            ↓
数据链路层：添加以太网头部（源 MAC + 目的 MAC）和尾部（FCS）→ Ethernet Frame
            ↓
物理层：    转换为电信号/光信号 → Bits 在介质中传输
```

#### 3.2 解封装过程（接收端：自下而上）

```
物理层：    接收电信号 → 还原为比特流
            ↓
数据链路层：检查目的 MAC → 去除以太网头部和尾部 → 提取 IP Packet
            ↓
网络层：    检查目的 IP → 去除 IP 头部 → 提取 TCP Segment
            ↓
传输层：    检查目的端口 → 去除 TCP 头部 → 提取应用数据
            ↓
会话层：    管理会话状态
            ↓
表示层：    解密数据
            ↓
应用层：    解析 HTTP 请求 → 生成响应
```

#### 3.3 封装头部大小示例

```
以太网帧结构：
┌─────────────┬─────────────┬────────┬──────────────┬──────┐
│ 目的MAC(6)  │ 源MAC(6)    │ 类型(2)│ 数据(≤1500)  │ FCS(4)│
└─────────────┴─────────────┴────────┴──────────────┴──────┘
  以太网头部 = 14 字节        MTU=1500 字节    帧校验

IP 头部（IPv4）：20 字节（固定） + 选项（可变）
TCP 头部：20 字节（固定） + 选项（可变）

总开销 = 以太网头部(14) + IP 头部(20) + TCP 头部(20) + FCS(4) = 58 字节
有效载荷最大 = 1500 字节
传输效率 = 1500 / (1500 + 58) ≈ 96.3%
```

### 4. MTU 与分片

#### 4.1 MTU 基础概念

MTU（Maximum Transmission Unit，最大传输单元）是数据链路层所能传输的最大数据帧大小。

| 网络类型 | 典型 MTU | 说明 |
|----------|----------|------|
| 以太网（Ethernet） | 1500 字节 | 最常见 |
| 巨型帧（Jumbo Frame） | 9000 字节 | 数据中心内部 |
| PPPoE | 1492 字节 | ADSL 拨号 |
| IPv6 最小 MTU | 1280 字节 | IPv6 强制最小值 |
| GRE 隧道 | 1476 字节 | 24 字节 GRE 头部开销 |
| VXLAN | 1450 字节 | 50 字节 VXLAN 封装开销 |
| ICMP（ping 默认） | 64 字节（含 IP 头部） | ping 的 payload 通常 56 字节 |

#### 4.2 分片机制

当 IP 数据包大小超过路径 MTU 时：

```
原始数据包（4000 字节）超过 MTU（1500 字节）：

原始数据包：
┌──────────┬─────────────────────────────────────┐
│ IP 头部  │              数据                    │
│ (20B)    │            (3980B)                  │
└──────────┴─────────────────────────────────────┘

分片后：
分片1：┌──────────┬────────────────┬───────┐
       │ IP 头部  │   数据(1480B)  │ DF=0  │  MF=1, Offset=0
       └──────────┴────────────────┴───────┘
分片2：┌──────────┬────────────────┬───────┐
       │ IP 头部  │   数据(1480B)  │ DF=0  │  MF=1, Offset=185
       └──────────┴────────────────┴───────┘
分片3：┌──────────┬────────────┬───────┐
       │ IP 头部  │ 数据(1020B)│ DF=0  │  MF=0, Offset=370
       └──────────┴────────────┴───────┘

注意：每个分片都有独立的 IP 头部，接收端需要重组。
```

**关键标志位**：
- **DF（Don't Fragment）**：设置后不允许分片。若超过 MTU 则返回 ICMP Type 3 Code 4（Fragmentation needed）
- **MF（More Fragments）**：1 表示还有后续分片，0 表示最后一个分片

#### 4.3 PMTUD（Path MTU Discovery）

路径 MTU 发现机制用于确定源到目的路径上的最小 MTU：

```
1. 发送端设置 DF=1，发送大包
2. 若路径上某路由器 MTU 较小，无法转发
3. 路由器丢弃数据包，返回 ICMP "Fragmentation needed"
4. 发送端根据 ICMP 中的 MTU 值调整发送大小
5. 重复直到找到合适的 MTU

注意：ICMP 被防火墙拦截会导致 PMTUD 失败 → "黑洞"问题
```

**SRE 排查 MTU 问题的命令**：
```bash
# 测试路径 MTU（Linux）
ping -M do -s 1472 www.example.com
# -M do: 设置 DF 标志
# -s 1472: payload 大小（1472 + 8 ICMP + 20 IP = 1500）
# 若通：MTU ≥ 1500；若不通：逐步减小 -s 值测试

# 测试特定 MTU
ping -M do -s 1400 www.example.com  # 1400+28 = 1428 < 1500，应通过

# 查看网卡 MTU
ip link show eth0
# 输出示例：mtu 1500

# 临时修改 MTU
sudo ip link set eth0 mtu 9000

# 永久修改（Ubuntu/Debian）
# /etc/network/interfaces 中添加：
# auto eth0
# iface eth0 inet dhcp
#     mtu 9000
```

### 5. 典型协议在各层的分布

| 协议 | 层级 | 端口 | 传输协议 | SRE 排查命令 |
|------|------|------|----------|-------------|
| HTTP | 7 | 80 | TCP | `curl -v`, `tcpdump port 80` |
| HTTPS | 7 | 443 | TCP | `openssl s_client`, `curl -vk` |
| DNS | 7 | 53 | UDP/TCP | `dig`, `nslookup`, `tcpdump port 53` |
| SSH | 7 | 22 | TCP | `ssh -v`, `tcpdump port 22` |
| TCP | 4 | - | - | `ss -tan`, `netstat -tan` |
| UDP | 4 | - | - | `ss -uan`, `netstat -uan` |
| IP | 3 | - | - | `ip route`, `traceroute` |
| ICMP | 3 | - | - | `ping`, `traceroute` |
| ARP | 2/3 | - | - | `arp -a`, `ip neigh` |

---

## 🛠️ 实战练习

### 练习 1：画出 OSI 七层模型

**任务**：在纸上或绘图工具中画出 OSI 七层模型，并标注以下内容：
- 每层的名称（中文 + 英文）
- 每层的典型协议（至少 3 个）
- HTTP 请求从浏览器发出到服务器响应，经过的每一层
- 每层的数据单位名称

**参考标注**：

```
┌─────────────────────────────────────────────────────────┐
│  L7 应用层 (Application)                                │
│  协议: HTTP, HTTPS, DNS, SSH                            │
│  ← HTTP 请求/响应从这里开始                             │
├─────────────────────────────────────────────────────────┤
│  L6 表示层 (Presentation)                               │
│  协议: TLS/SSL, gzip, JSON                              │
│  ← HTTPS 加密在此层                                     │
├─────────────────────────────────────────────────────────┤
│  L5 会话层 (Session)                                    │
│  协议: 会话管理                                         │
│  ← 维持 HTTP 会话状态                                   │
├─────────────────────────────────────────────────────────┤
│  L4 传输层 (Transport)                                  │
│  协议: TCP (端口 443), UDP                              │
│  ← 添加 TCP 头部（源端口→目的端口 443）                 │
├─────────────────────────────────────────────────────────┤
│  L3 网络层 (Network)                                    │
│  协议: IP, ICMP                                         │
│  ← 添加 IP 头部（源 IP→目的 IP）                        │
├─────────────────────────────────────────────────────────┤
│  L2 数据链路层 (Data Link)                              │
│  协议: Ethernet, WiFi                                   │
│  ← 添加 MAC 头部（源 MAC→网关 MAC）                     │
├─────────────────────────────────────────────────────────┤
│  L1 物理层 (Physical)                                   │
│  介质: 网线、光纤、无线电波                              │
│  ← 转换为电信号/光信号传输                              │
└─────────────────────────────────────────────────────────┘
```

### 练习 2：使用 tcpdump 观察数据包封装

**目标**：用 tcpdump 观察 TCP 数据包的封装信息

```bash
# 安装 tcpdump（如未安装）
sudo apt-get install tcpdump -y

# 捕获 eth0 网卡上端口 80 的流量
sudo tcpdump -i eth0 port 80 -n -v
# -i eth0: 指定网卡
# port 80: 过滤 HTTP 流量
# -n: 不解析域名和端口名
# -v: 显示详细信息（包含 IP TTL、TOS 等）

# 更详细的输出（包含链路层头部）
sudo tcpdump -i eth0 port 443 -n -vv -X
# -vv: 更详细
# -X: 同时显示十六进制和 ASCII

# 捕获特定主机的流量
sudo tcpdump -i any host 10.0.0.5 -n

# 捕获并保存到文件（后续用 Wireshark 分析）
sudo tcpdump -i eth0 -w /tmp/capture.pcap port 80
# 用 Wireshark 打开：wireshark /tmp/capture.pcap

# 观察 TCP 三次握手
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0' -n
# 会看到 SYN, SYN-ACK, ACK 三个包

# 输出示例：
# 14:30:25.123456 IP 192.168.1.100.54321 > 93.184.216.34.80: Flags [S], seq 1234567890, win 64240
#   ↑ IP 头部           源:端口              目的:端口         SYN标志  序列号       窗口大小
```

### 练习 3：使用 ping 测试 MTU 路径发现

```bash
# 测试默认 ping（64 字节，包含 56 字节 payload + 8 字节 ICMP）
ping -c 4 www.baidu.com

# 测试 PMTUD（设置 DF 标志）
ping -M do -s 1472 www.baidu.com -c 2
# 如果返回 "message too long" 或超时，说明 MTU < 1500

# 逐步减小测试
ping -M do -s 1400 www.baidu.com -c 2  # 1400+28 = 1428
ping -M do -s 1000 www.baidu.com -c 2  # 1000+28 = 1028

# 查看系统默认 MTU
ip link show | grep mtu
# 输出：mtu 1500 qdisc ...

# 查看路由表的 MTU 信息
ip route show
# 输出示例中的 mtu 字段
```

### 练习 4：追踪数据包经过的网络设备

```bash
# 追踪到目标的路由路径
traceroute www.baidu.com
# 或使用 mtr（更直观）
sudo apt-get install mtr -y
mtr www.baidu.com

# mtr 输出示例：
# Host                    Loss%   Snt   Last   Avg  Best  Wrst StDev
# 192.168.1.1             0.0%    10    1.2   1.5   1.0   2.1  0.3
# 10.0.0.1                0.0%    10    5.1   5.3   4.8   6.2  0.4
# ...
# 每跳代表一个路由器（L3 设备）

# 查看本地 ARP 表（L2 设备映射）
ip neigh show
# 输出：IP 地址 → MAC 地址的映射

# 查看路由表（L3 路由信息）
ip route show
# 输出：目标网络 → 下一跳 → 接口
```

---

## 🔍 SRE 实战案例：网站打不开的网络排查

### 场景描述

用户报告：公司内部服务 `http://api.internal.company.com` 无法访问。

### 排查步骤（从下到上逐层排查）

```
Step 1: 物理层检查（Layer 1）
┌─────────────────────────────────────────────┐
│ # 检查网卡状态                               │
│ ip link show eth0                           │
│ # 输出：state UP → 物理连接正常              │
│ # 输出：state DOWN → 网线松动/网卡禁用       │
│                                             │
│ # 检查网线指示灯                             │
│ # 服务器机房：观察网卡 LED 是否亮灯          │
│                                             │
│ ✅ 结果：网卡 state UP，物理层正常            │
└─────────────────────────────────────────────┘
         ↓
Step 2: 数据链路层检查（Layer 2）
┌─────────────────────────────────────────────┐
│ # 检查 MAC 地址和 ARP                        │
│ ip neigh show                               │
│ # 网关的 MAC 地址是否正常？                  │
│                                             │
│ # 检查 VLAN 配置                             │
│ ip -d link show eth0                        │
│ # 确认 VLAN ID 是否正确                      │
│                                             │
│ ✅ 结果：ARP 正常，VLAN 配置正确             │
└─────────────────────────────────────────────┘
         ↓
Step 3: 网络层检查（Layer 3）
┌─────────────────────────────────────────────┐
│ # 检查 IP 配置                               │
│ ip addr show eth0                           │
│ # IP 地址、子网掩码是否正确？                │
│                                             │
│ # ping 网关                                  │
│ ping -c 3 192.168.1.1                       │
│ ✅ 结果：ping 网关通                         │
│                                             │
│ # ping 目标服务器                            │
│ ping -c 3 api.internal.company.com          │
│ ✅ 结果：ping 通！说明网络层（IP 层）没问题  │
│ ❗ 关键发现：网络层可达，但应用不可用        │
└─────────────────────────────────────────────┘
         ↓
Step 4: 传输层检查（Layer 4）
┌─────────────────────────────────────────────┐
│ # 使用 telnet 测试 TCP 端口                  │
│ telnet api.internal.company.com 8080        │
│ # 或                                         │
│ nc -zv api.internal.company.com 8080        │
│ # 或使用 bash 内置                           │
│ echo > /dev/tcp/api.internal.company.com/8080│
│                                             │
│ ❌ 结果：Connection refused / 超时          │
│                                             │
│ # 检查本地防火墙                             │
│ sudo iptables -L -n                         │
│ sudo iptables -L -n | grep 8080             │
│ # 发现：OUTPUT 链有一条规则 DROP 8080 端口  │
│                                             │
│ 🔍 定位：防火墙规则阻止了对 8080 端口的访问  │
└─────────────────────────────────────────────┘
         ↓
Step 5: 应用层检查（Layer 7）
┌─────────────────────────────────────────────┐
│ # 在防火墙放行后测试                         │
│ curl -v http://api.internal.company.com:8080│
│ # 检查 HTTP 响应码                           │
│                                             │
│ # 检查服务进程                               │
│ ps aux | grep api                           │
│ systemctl status api-service                │
│                                             │
│ # 查看应用日志                               │
│ journalctl -u api-service --since "1 hour ago"│
│                                             │
│ ✅ 结果：服务正常响应 200 OK                 │
└─────────────────────────────────────────────┘
```

### 排查总结

```
网络分层排查思路：
L1 物理层  → 网线/网卡/指示灯    → 通
L2 链路层  → MAC/ARP/VLAN       → 通
L3 网络层  → ping 通             → 通 ✅（网络可达）
L4 传输层  → telnet/nc 端口不通  → ❌ 不通！
L7 应用层  → 端口不通无法到达    → 未到达

根因：防火墙规则 DROP 了 8080 端口
解决：sudo iptables -D OUTPUT -p tcp --dport 8080 -j DROP
验证：nc -zv api.internal.company.com 8080 → 通
```

### 快速排查脚本

```bash
#!/bin/bash
# sre-network-check.sh - 快速网络分层排查脚本

TARGET=$1
PORT=${2:-80}

echo "=== SRE 网络分层快速排查 ==="
echo "目标: $TARGET:$PORT"
echo ""

# L3: ping 测试
echo "[L3] Ping 测试..."
if ping -c 2 -W 2 "$TARGET" &>/dev/null; then
    echo "  ✅ Ping 通（网络层正常）"
else
    echo "  ❌ Ping 不通（网络层故障）"
    echo "  → 检查路由: ip route show"
    echo "  → 检查 DNS: dig $TARGET"
    exit 1
fi

# L4: TCP 端口测试
echo "[L4] TCP 端口测试..."
if timeout 3 bash -c "echo > /dev/tcp/$TARGET/$PORT" 2>/dev/null; then
    echo "  ✅ 端口 $PORT 可达（传输层正常）"
else
    echo "  ❌ 端口 $PORT 不可达"
    echo "  → 检查防火墙: iptables -L -n"
    echo "  → 检查服务: ss -tlnp | grep $PORT"
fi

# L7: HTTP 测试
echo "[L7] HTTP 测试..."
if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$TARGET:$PORT" --connect-timeout 3 2>/dev/null)
    if [[ "$HTTP_CODE" =~ ^[23] ]]; then
        echo "  ✅ HTTP 响应码: $HTTP_CODE（应用层正常）"
    else
        echo "  ⚠️ HTTP 响应码: $HTTP_CODE"
    fi
fi

echo ""
echo "=== 排查完成 ==="
```

使用方式：
```bash
chmod +x sre-network-check.sh
./sre-network-check.sh api.internal.company.com 8080
```

---

## 📚 最新优质资源

### 官方文档
- [RFC 1122 - Host Requirements (TCP/IP)](https://datatracker.ietf.org/doc/html/rfc1122) — TCP/IP 协议核心规范
- [RFC 791 - Internet Protocol (IPv4)](https://datatracker.ietf.org/doc/html/rfc791) — IPv4 协议规范
- [RFC 793 - Transmission Control Protocol](https://datatracker.ietf.org/doc/html/rfc793) — TCP 协议规范

### 推荐教程
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/) — 经典网络编程指南
- [TCP/IP Illustrated Vol.1](https://en.wikipedia.org/wiki/TCP/IP_Illustrated) — W. Richard Stevens 经典著作
- [Cloudflare Learning Center - Networking](https://www.cloudflare.com/learning/) — 通俗的网络知识教程

### 视频课程
- [Bilibili - 计算机网络微课堂](https://www.bilibili.com/video/BV1JV411t7ow/) — 华为课程，系统讲解 OSI 和 TCP/IP
- [YouTube - NetworkChuck CCNA 系列](https://www.youtube.com/playlist?list=PLIhvC56v63IJVXv0GJcl9vO5Z6znCVb1P) — 实操性强的网络入门
- [Bilibili - TCP/IP 协议栈详解](https://www.bilibili.com/video/BV1PW411d7Xm/) — 深入理解网络协议

### SRE 相关资源
- [Google SRE Book - Chapter 23: Network](https://sre.google/sre-book/networking/) — Google SRE 视角的网络知识
- [Linux Network Troubleshooting Guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_networking/troubleshooting-network-problems_configuring-and-managing-networking) — Red Hat 官方网络排障指南
- [tcpdump 官方文档](https://www.tcpdump.org/) — 数据包分析工具

---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）
- OSI 七层模型是理论框架，TCP/IP 四层模型是实际实现，理解两者的映射关系很重要
- 网络故障排查应该遵循从下到上（或从上到下）的逐层排查原则
- ping 通不代表服务可用——ping 只测试到 L3（ICMP），而服务通常运行在 L7（HTTP/gRPC 等）
- MTU 问题经常被忽视，特别是在使用隧道（VXLAN、GRE、IPsec）的场景下
- tcpdump 是 SRE 排查网络问题的瑞士军刀，需要熟练掌握

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| tcpdump 权限不足 | 使用 `sudo` 或将用户加入 `wireshark` 组 |
| ping 不通但业务正常 | 目标服务器禁用了 ICMP 响应（正常安全策略） |
| 分片导致性能下降 | 启用 PMTUD 或使用巨型帧（数据中心内） |
| iptables 规则太多难以排查 | 使用 `iptables -L -n --line-numbers` 按序号查看 |

### 延伸思考

- 思考 1：在微服务架构中，服务间通信经过多少层网络？Sidecar 代理（如 Envoy）在网络模型中属于哪一层？
- 思考 2：Kubernetes 中 Pod 间的网络通信与宿主机上的容器网络有何不同？CNI 插件如何处理网络分层？
- 思考 3：为什么现代数据中心倾向于使用 9000 字节的巨型帧？有什么风险和限制？

---

## ✅ 完成检查

- [ ] 理解 OSI 七层模型的核心概念和每层职责
- [ ] 掌握 TCP/IP 四层模型与 OSI 的对应关系
- [ ] 理解数据封装与解封装过程
- [ ] 理解 MTU 和分片机制
- [ ] 完成 tcpdump 抓包练习
- [ ] 完成 MTU 路径发现测试
- [ ] 理解 SRE 实战案例中的逐层排查思路
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记

---

*由 SRE 学习计划自动生成 | 2026-04-29*
