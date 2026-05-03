# Day 29: OSI 七层模型与 TCP/IP 协议栈

> 📅 日期：2026-04-29
> 📖 学习主题：OSI 七层模型与 TCP/IP 协议栈
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 28 Linux 基础与 Shell 脚本综合能力评估

---

## 🎯 学习目标

完成 Day 29 的学习后，你应该掌握：
- 深入理解 OSI 七层模型每一层的职责、协议、设备和数据单元
- 掌握 TCP/IP 四层模型与 OSI 的映射关系，理解为什么实际使用 TCP/IP 模型
- 能够完整描述 HTTP 请求从应用层到物理层的封装与解封装过程
- 理解 MTU 对分片的影响，掌握 IP 分片、TCP MSS 协商和 Path MTU Discovery 机制
- 能够运用分层排查思路解决生产环境网络故障

---

## 📖 核心知识点

### 1. OSI 七层模型深入

#### 1.1 为什么需要网络分层？

在没有标准化分层模型之前，不同厂商的网络设备无法互通。分层设计的核心价值：

```
分层的优势：
┌─────────────────────────────────────────────────────────┐
│ 1. 标准化：每层有明确的接口定义，厂商可以独立实现        │
│ 2. 解耦合：修改某层的实现不影响其他层                    │
│ 3. 可调试：出问题时可以逐层排查，快速定位故障层          │
│ 4. 可复用：底层协议可以被多种上层协议复用                │
│ 5. 模块化：不同团队可以并行开发不同层的协议              │
└─────────────────────────────────────────────────────────┘

类比理解：
→ 物理层 = 公路（物理基础设施）
→ 数据链路层 = 交通规则（同一段路上的车辆如何行驶）
→ 网络层 = 导航系统（从 A 城市到 B 城市的路线规划）
→ 传输层 = 快递服务（保证包裹完整送达，有丢件重发机制）
→ 应用层 = 包裹内容（你真正要寄的东西）
```

#### 1.2 OSI 七层总览表

| 层级 | 名称 | 英文 | 数据单元 | 核心职责 | 典型协议 | 典型设备 | SRE 关注点 |
|------|------|------|----------|----------|----------|----------|-----------|
| L7 | 应用层 | Application | Data | 为应用提供网络服务接口 | HTTP, HTTPS, DNS, SSH, gRPC, SMTP, FTP | 应用服务器、WAF、API 网关 | 响应码、延迟、错误率 |
| L6 | 表示层 | Presentation | Data | 数据格式转换、加密、压缩 | TLS/SSL, JPEG, MPEG, gzip, Protocol Buffers | SSL 加速器、WAF | 证书过期、加密套件 |
| L5 | 会话层 | Session | Data | 会话管理、同步控制 | NetBIOS, RPC, SIP, PPTP, SOCKS | 代理服务器、会话控制器 | 会话超时、连接复用 |
| L4 | 传输层 | Transport | Segment/Datagram | 端到端传输、流量控制、差错控制 | TCP, UDP, SCTP, QUIC | 防火墙、负载均衡器、L4 LB | TCP 状态、重传、连接数 |
| L3 | 网络层 | Network | Packet | 逻辑寻址、路由选择、分组转发 | IP, ICMP, OSPF, BGP, ARP, IGMP | 路由器、三层交换机 | 路由、丢包、延迟、TTL |
| L2 | 数据链路层 | Data Link | Frame | 物理寻址、帧封装、差错检测 | Ethernet, PPP, VLAN(802.1Q), MPLS, STP, ARP | 交换机、网桥、网卡 | CRC 错误、丢帧、广播风暴 |
| L1 | 物理层 | Physical | Bit | 比特流的物理传输 | 以太网物理层、光纤、Wi-Fi(802.11)、RS-232 | 网线、光纤、中继器、集线器 | 链路状态、光衰、误码率 |

**记忆口诀（从下到上）**：**物数网传会表应**（物理层 -> 数据链路层 -> 网络层 -> 传输层 -> 会话层 -> 表示层 -> 应用层）。

#### 1.3 物理层（Layer 1）深入

物理层负责在物理介质上传输原始比特流，不关心数据的含义。

```
物理层核心要素：
┌─────────────────────────────────────────────────────────┐
│ 1. 机械特性：接口形状、引脚数量和排列                    │
│ 2. 电气特性：电压范围、阻抗、传输速率                    │
│ 3. 功能特性：每根引脚的功能定义                          │
│ 4. 过程特性：信号的时序关系                              │
└─────────────────────────────────────────────────────────┘

传输介质分类：
┌──────────────┬─────────────┬──────────────┬──────────────┐
│   介质类型    │   最大速率   │   最大距离    │   典型场景    │
├──────────────┼─────────────┼──────────────┼──────────────┤
│ Cat5e 网线   │ 1 Gbps      │ 100m         │ 办公室网络    │
│ Cat6a 网线   │ 10 Gbps     │ 100m         │ 数据中心      │
│ 单模光纤     │ 100+ Gbps   │ 80km+        │ 长距离传输    │
│ 多模光纤     │ 100 Gbps    │ 300-550m     │ 数据中心内部  │
│ Wi-Fi 6      │ 9.6 Gbps    │ 室内 ~50m    │ 无线接入      │
│ Wi-Fi 7      │ 46 Gbps     │ 室内 ~50m    │ 无线接入      │
└──────────────┴─────────────┴──────────────┴──────────────┘
```

**SRE 关注点**：
- 网卡状态：`ip link show` 检查 `state UP/DOWN`
- 光模块光衰：`ethtool -m eth0` 查看光功率（数据中心场景）
- 误码率：`ethtool -S eth0` 查看 CRC 错误、丢包计数
- 网线质量：物理层问题经常表现为间歇性丢包

#### 1.4 数据链路层（Layer 2）深入

数据链路层负责在相邻节点之间可靠地传输数据帧。

```
以太网帧结构（Ethernet II / DIX）：
┌─────────────┬─────────────┬────────┬──────────────────┬──────┐
│ 目的MAC(6B) │ 源MAC(6B)   │类型(2B)│    数据(46-1500B) │FCS(4B)│
└─────────────┴─────────────┴────────┴──────────────────┴──────┘
  ← 以太网头部 14 字节 →          ← 有效载荷 →         ← 校验 →

类型字段常见值：
- 0x0800 = IPv4
- 0x0806 = ARP
- 0x86DD = IPv6
- 0x8100 = VLAN (802.1Q)

最小帧长：64 字节（14 头部 + 46 数据 + 4 FCS）
最大帧长：1518 字节（14 头部 + 1500 数据 + 4 FCS）
VLAN 帧：1522 字节（增加 4 字节 VLAN Tag）

MAC 地址格式：
├── 厂商标识 (OUI) ──┤── 设备标识 ──┤
│   前 24 位          │   后 24 位   │
│   例如 00:1A:2B    │   3C:4D:5E   │

特殊 MAC 地址：
- FF:FF:FF:FF:FF:FF = 广播地址
- 01:00:5E:xx:xx:xx = 组播地址范围
- 00:00:00:00:00:00 = 无效地址
```

**交换机工作原理**：
```
MAC 地址学习过程：

1. 主机 A 发送帧（源 MAC=A，目的 MAC=B）
2. 交换机收到帧：
   a. 学习源 MAC → 记录 MAC=A 在端口 1
   b. 查找目的 MAC=B → 未找到
   c. 泛洪（Flooding）：从除端口 1 外的所有端口转发
3. 主机 B 收到帧，回复（源 MAC=B，目的 MAC=A）
4. 交换机收到回复：
   a. 学习源 MAC → 记录 MAC=B 在端口 2
   b. 查找目的 MAC=A → 找到在端口 1
   c. 单播转发：只从端口 1 转发

MAC 地址表（CAM Table）：
┌─────────────────┬──────────┬───────────┐
│ MAC 地址         │ 端口      │ 老化时间   │
├─────────────────┼──────────┼───────────┤
│ AA:BB:CC:DD:EE:01 │ Port 1  │ 300s      │
│ AA:BB:CC:DD:EE:02 │ Port 2  │ 300s      │
└─────────────────┴──────────┴───────────┘
```

**SRE 关注点**：
- ARP 表：`ip neigh show` 或 `arp -a`
- VLAN 配置：`ip -d link show` 查看 VLAN tag
- 广播风暴：`tcpdump -i eth0 broadcast` 检测异常广播
- STP 环路：交换机端口频繁 UP/DOWN 可能是 STP 收敛

#### 1.5 网络层（Layer 3）深入

网络层负责将数据包从源主机传送到目的主机，核心是路由选择。

```
IP 数据包头部（IPv4，20 字节固定 + 可变选项）：
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version|  IHL  |    DSCP   |ECN|         Total Length          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Identification        |Flags|     Fragment Offset      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Time to Live |    Protocol   |        Header Checksum         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Source Address                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Destination Address                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options (可选)      |       Padding         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

关键字段说明：
┌──────────────────┬────────┬────────────────────────────────────┐
│ 字段             │ 大小    │ 说明                               │
├──────────────────┼────────┼────────────────────────────────────┤
│ Version          │ 4 bit  │ IPv4=4, IPv6=6                     │
│ IHL              │ 4 bit  │ IP 头部长度（32 位字为单位）         │
│ Total Length     │ 16 bit │ 整个 IP 包大小（最大 65535 字节）    │
│ Identification   │ 16 bit │ 用于分片重组的标识                   │
│ Flags (DF/MF)    │ 3 bit  │ DF=不分片, MF=还有后续分片           │
│ Fragment Offset  │ 13 bit │ 分片在原始包中的偏移（8 字节为单位）  │
│ TTL              │ 8 bit  │ 生存时间（每经过一跳减 1）            │
│ Protocol         │ 8 bit  │ 上层协议（6=TCP, 17=UDP, 1=ICMP）    │
│ Source IP        │ 32 bit │ 源 IP 地址                          │
│ Destination IP   │ 32 bit │ 目的 IP 地址                        │
└──────────────────┴────────┴────────────────────────────────────┘
```

**路由选择过程**：
```
数据包转发决策流程：

1. 收到 IP 数据包
2. 检查目的 IP 是否是本机 → 是：交给上层协议处理
3. 不是本机 → 查路由表（Longest Prefix Match 最长前缀匹配）
4. 找到匹配路由 → 获取下一跳 IP 和出接口
5. 查 ARP 表获取下一跳的 MAC 地址
6. 封装以太网帧（目的 MAC = 下一跳 MAC）并转发
7. TTL 减 1，若 TTL=0 则丢弃并发送 ICMP Time Exceeded

路由表示例：
$ ip route show
default via 192.168.1.1 dev eth0
10.0.0.0/8 via 10.0.0.1 dev eth1
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100
172.16.0.0/16 via 172.16.0.1 dev eth2 metric 100
```

**ICMP 协议**：
```
ICMP 是网络层的辅助协议，用于报告错误和诊断：

常见 ICMP 类型：
┌──────┬──────────┬───────────────────────────────────────┐
│ 类型  │ 名称      │ 用途                                  │
├──────┼──────────┼───────────────────────────────────────┤
│ 0    │ Echo Reply     │ ping 回复                       │
│ 3    │ Dest Unreachable │ 目标不可达（细分 Code）        │
│  3/0 │ Network Unreachable │ 网络不可达                │
│  3/1 │ Host Unreachable   │ 主机不可达                 │
│  3/3 │ Port Unreachable   │ 端口不可达                 │
│  3/4 │ Fragmentation Needed │ 需要分片（PMTUD 核心）   │
│ 5    │ Redirect       │ 路由重定向                       │
│ 8    │ Echo Request   │ ping 请求                        │
│ 11   │ Time Exceeded  │ TTL 超时（traceroute 的原理）    │
│  11/0│ TTL Exceeded   │ TTL 在传输中为 0                │
│  11/1│ Fragment Reassembly Timeout │ 分片重组超时      │
└──────┴──────────┴───────────────────────────────────────┘
```

#### 1.6 传输层（Layer 4）深入

传输层提供端到端的通信服务，核心协议是 TCP 和 UDP。

```
端口号分类：
┌──────────────┬─────────────┬───────────────────────────────┐
│ 范围          │ 名称         │ 说明                          │
├──────────────┼─────────────┼───────────────────────────────┤
│ 0-1023       │ 知名端口     │ 系统服务，需要 root 权限       │
│ 1024-49151   │ 注册端口     │ 用户应用注册使用               │
│ 49152-65535  │ 动态/私有端口 │ 客户端临时端口（ephemeral）    │
└──────────────┴─────────────┴───────────────────────────────┘

常见知名端口：
┌───────┬──────────┬──────────┬──────────────────────────────┐
│ 端口   │ 服务      │ 协议     │ 说明                          │
├───────┼──────────┼──────────┼──────────────────────────────┤
│ 20/21 │ FTP       │ TCP      │ 文件传输（数据/控制）          │
│ 22    │ SSH       │ TCP      │ 安全远程登录                   │
│ 23    │ Telnet    │ TCP      │ 远程登录（不安全，已淘汰）     │
│ 25    │ SMTP      │ TCP      │ 邮件发送                       │
│ 53    │ DNS       │ UDP/TCP  │ 域名解析                       │
│ 80    │ HTTP      │ TCP      │ Web 服务                       │
│ 443   │ HTTPS     │ TCP      │ 加密 Web 服务                  │
│ 3306  │ MySQL     │ TCP      │ 数据库                         │
│ 5432  │ PostgreSQL│ TCP      │ 数据库                         │
│ 6379  │ Redis     │ TCP      │ 缓存/消息队列                  │
│ 8080  │ HTTP Alt  │ TCP      │ 备用 HTTP / 代理               │
│ 9090  │ Prometheus│ TCP      │ 监控系统                       │
└───────┴──────────┴──────────┴──────────────────────────────┘
```

**SRE 关注点**：
- TCP 连接状态：`ss -tan | awk 'NR>1{print $1}' | sort | uniq -c | sort -rn`
- 连接数监控：ESTABLISHED、TIME_WAIT、CLOSE_WAIT 数量
- 端口耗尽：`ss -tan state time-wait | wc -l`
- 重传率：`netstat -s | grep retransmit`

#### 1.7 会话层（Layer 5）深入

会话层管理通信会话的建立、维护和终止，提供对话控制和同步机制。

```
会话层的核心功能：

1. 会话建立（Session Establishment）
   → 身份验证
   → 协商会话参数（超时、窗口大小）
   → 分配会话标识符

2. 会话管理（Session Management）
   → 对话控制：全双工 / 半双工 / 单工
   → 同步点：在数据流中插入检查点
   → 活动管理：将长传输分解为多个活动

3. 会话终止（Session Termination）
   → 有序释放：双方协商后关闭
   → 异常终止：一方突然断开

SRE 视角的会话层：
- HTTP 会话：Cookie / Session ID
- RPC 会话：gRPC 的 Channel、Dubbo 的会话
- 数据库连接池：每个连接就是一个会话
- SSH 会话：保持长连接，超时断开
```

#### 1.8 表示层（Layer 6）深入

表示层负责数据的表示、加密和压缩，确保通信双方能理解彼此的数据格式。

```
表示层的核心功能：

1. 数据编码与转换
   ┌──────────────┬──────────────────────────────────────────┐
   │ 编码格式      │ 说明                                      │
   ├──────────────┼──────────────────────────────────────────┤
   │ ASCII        │ 7 位字符编码，128 个字符                   │
   │ UTF-8        │ 可变长度 Unicode 编码，1-4 字节            │
   │ JSON         │ 轻量级数据交换格式                         │
   │ XML          │ 可扩展标记语言                             │
   │ Protocol Buf │ Google 的二进制序列化格式                   │
   │ MessagePack  │ 类似 JSON 的二进制格式                     │
   └──────────────┴──────────────────────────────────────────┘

2. 数据加密
   → TLS/SSL：传输层加密（在实际实现中通常归入表示层）
   → 对称加密：AES-256-GCM（数据加密）
   → 非对称加密：RSA / ECDSA（密钥交换和签名）
   → 哈希：SHA-256（完整性校验）

3. 数据压缩
   → gzip / brotli / zstd（HTTP 响应压缩）
   → 图片压缩：JPEG（有损）、PNG（无损）、WebP
   → 视频压缩：H.264、H.265、AV1
```

**SRE 关注点**：
- TLS 证书过期：`openssl s_client -connect host:443 | openssl x509 -noout -dates`
- 加密套件安全：禁用弱加密（RC4、DES、MD5）
- 压缩效率：`curl -H "Accept-Encoding: br,gzip" -sI https://example.com`

#### 1.9 应用层（Layer 7）深入

应用层是最接近用户的一层，直接为应用程序提供网络通信服务。

```
应用层协议分类：

1. Web 协议
   → HTTP/1.1：文本协议，持久连接
   → HTTP/2：二进制分帧，多路复用，头部压缩
   → HTTP/3：基于 QUIC（UDP），0-RTT
   → WebSocket：全双工通信

2. 邮件协议
   → SMTP（25/587）：发送邮件
   → POP3（110/995）：接收邮件（下载模式）
   → IMAP（143/993）：接收邮件（在线模式）

3. 文件传输
   → FTP（20/21）：文件传输
   → SFTP（22）：安全文件传输（基于 SSH）
   → SCP（22）：安全复制

4. 域名解析
   → DNS（53）：域名到 IP 映射
   → mDNS（5353）：本地链路多播 DNS

5. 远程管理
   → SSH（22）：安全远程登录
   → RDP（3389）：远程桌面
   → VNC（5900）：远程桌面

6. 基础设施协议
   → DHCP（67/68）：自动分配 IP
   → NTP（123）：时间同步
   → SNMP（161/162）：网络设备监控
   → Syslog（514）：日志收集
```

### 2. TCP/IP 四层模型与 OSI 的映射

#### 2.1 两种模型的对比

```
┌─────────────────────────────────────────────────────────────┐
│                    OSI 七层模型                               │
├───────────────────────────┬─────────────────────────────────┤
│ L7 应用层                  │                                 │
│ L6 表示层                  │  ← TCP/IP 应用层                │
│ L5 会话层                  │    （合并了上三层）              │
├───────────────────────────┼─────────────────────────────────┤
│ L4 传输层                  │  ← TCP/IP 传输层                │
├───────────────────────────┼─────────────────────────────────┤
│ L3 网络层                  │  ← TCP/IP 网际层（Internet）    │
├───────────────────────────┼─────────────────────────────────┤
│ L2 数据链路层              │  ← TCP/IP 网络接口层            │
│ L1 物理层                  │    （合并了下两层）              │
└───────────────────────────┴─────────────────────────────────┘
```

| 对比维度 | OSI 七层模型 | TCP/IP 四层模型 |
|----------|-------------|----------------|
| 层数 | 7 层 | 4 层 |
| 设计理念 | 先有模型，后有协议 | 先有协议，后有模型 |
| 通用性 | 理论框架，通用性强 | 针对互联网，实用性强 |
| 应用层 | 分为应用层、表示层、会话层 | 合并为一个应用层 |
| 网络接口层 | 分为数据链路层和物理层 | 合并为一个网络接口层 |
| 实际使用 | 教学和理论分析 | 互联网实际协议栈 |

#### 2.2 为什么实际使用 TCP/IP 模型？

```
1. 历史原因
   → TCP/IP 协议族在 1970 年代由 DARPA 开发
   → OSI 模型在 1984 年才由 ISO 提出
   → TCP/IP 先入为主，已经成为事实标准

2. 实用性
   → OSI 模型过于理论化，会话层和表示层在实际协议中界限模糊
   → TCP/IP 模型更贴合实际实现
   → 大多数网络编程直接使用 Socket API（TCP/IP 模型的接口）

3. SRE 视角
   → 排障时通常只关注四层：
     - 应用层：HTTP 响应码、DNS 解析
     - 传输层：TCP 连接状态、端口可达性
     - 网络层：ping、traceroute、路由
     - 链路层：ARP、MAC、VLAN
```

#### 2.3 数据在各层的名称

```
发送端（自上而下）：          接收端（自下而上）：
Application Layer             Application Layer
    ↓ Data                    ↑ Data
Presentation Layer            Presentation Layer
    ↓ Data                    ↑ Data
Session Layer                 Session Layer
    ↓ Data                    ↑ Data
Transport Layer               Transport Layer
    ↓ Segment (TCP)           ↑ Segment (TCP)
    ↓ Datagram (UDP)          ↑ Datagram (UDP)
Network Layer                 Network Layer
    ↓ Packet                  ↑ Packet
Data Link Layer               Data Link Layer
    ↓ Frame                   ↑ Frame
Physical Layer                Physical Layer
    ↓ Bits                    ↑ Bits
    → 传输介质 →
```

### 3. 数据封装与解封装完整流程

#### 3.1 封装过程（以 HTTPS 请求为例）

当用户在浏览器输入 `https://www.example.com` 并回车：

```
Step 1: 应用层 — 生成 HTTP 请求
┌─────────────────────────────────────────────────────┐
│ GET / HTTP/1.1\r\n                                  │
│ Host: www.example.com\r\n                           │
│ User-Agent: Mozilla/5.0\r\n                         │
│ Accept: text/html\r\n                               │
│ Accept-Encoding: gzip, br\r\n                       │
│ Connection: keep-alive\r\n                          │
│ \r\n                                                │
└─────────────────────────────────────────────────────┘
数据大小：约 200 字节

Step 2: 表示层 — TLS 加密
┌─────────────────────────────────────────────────────┐
│ TLS 1.3 Record Header (5 bytes)                     │
│ Content Type: Application Data (0x17)               │
│ Encrypted Data: [加密后的 HTTP 请求]                  │
│ Authentication Tag: [完整性校验]                      │
└─────────────────────────────────────────────────────┘
加密后数据大小：约 250 字节（含 TLS 头部和认证标签）

Step 3: 传输层 — 添加 TCP 头部
┌───────────────┬─────────────────────────────────────┐
│ TCP Header    │         TLS 加密数据                 │
│ (20 字节)      │         (约 250 字节)                │
├───────────────┤                                     │
│ 源端口: 54321 │                                     │
│ 目的端口: 443 │                                     │
│ 序列号: 1000  │                                     │
│ 确认号: 0     │                                     │
│ Flags: SYN    │                                     │
│ 窗口: 65535   │                                     │
└───────────────┴─────────────────────────────────────┘
TCP 段大小：约 270 字节

Step 4: 网络层 — 添加 IP 头部
┌───────────────┬─────────────────────────────────────┐
│ IP Header     │         TCP Segment                  │
│ (20 字节)      │         (约 270 字节)                │
├───────────────┤                                     │
│ 版本: 4       │                                     │
│ 源IP: 192.168.1.100                               │
│ 目的IP: 93.184.216.34                              │
│ TTL: 64       │                                     │
│ 协议: 6 (TCP) │                                     │
└───────────────┴─────────────────────────────────────┘
IP 包大小：约 290 字节

Step 5: 数据链路层 — 添加以太网头部和尾部
┌───────────────┬───────────────┬─────────────────────┐
│ 以太网头部     │ IP Packet     │ FCS (4 字节)         │
│ (14 字节)      │ (290 字节)    │ 帧校验序列           │
├───────────────┤               │                     │
│ 目的MAC: 网关  │               │                     │
│ 源MAC: 本机    │               │                     │
│ 类型: 0x0800  │               │                     │
└───────────────┴───────────────┴─────────────────────┘
以太网帧大小：约 308 字节

Step 6: 物理层 — 转换为电信号
→ 将帧的二进制数据转换为电信号（或光信号）
→ 通过网线（或光纤）发送到网关
→ 比特率：1 Gbps = 每秒 10 亿个比特
```

#### 3.2 解封装过程（服务器接收端）

```
物理层：接收电信号 → 还原为比特流 → 交给数据链路层
    ↓
数据链路层：
  → 检查目的 MAC 地址是否匹配
  → 验证 FCS 校验（CRC32）
  → 去除以太网头部和尾部（14 + 4 = 18 字节）
  → 提取 IP Packet 交给网络层
    ↓
网络层：
  → 检查目的 IP 地址是否匹配
  → 检查 TTL（如果为 0 则丢弃）
  → 验证 IP 头部校验和
  → 如果有分片，等待重组
  → 去除 IP 头部（20 字节）
  → 根据 Protocol 字段（6=TCP）交给传输层
    ↓
传输层：
  → 根据目的端口（443）找到对应进程
  → 验证序列号，处理乱序和重传
  → 发送 ACK 确认
  → 去除 TCP 头部（20 字节）
  → 将数据交给应用层
    ↓
应用层：
  → TLS 解密
  → 解析 HTTP 请求
  → 处理请求并生成响应
```

#### 3.3 各层头部开销分析

```
HTTPS 请求的协议开销：

┌────────────────┬──────────┬──────────────────────────────┐
│ 层级            │ 开销      │ 说明                          │
├────────────────┼──────────┼──────────────────────────────┤
│ 以太网头部      │ 14 字节   │ 目的 MAC + 源 MAC + 类型      │
│ 以太网尾部      │ 4 字节    │ FCS 帧校验                    │
│ IP 头部         │ 20 字节   │ IPv4 固定头部                  │
│ TCP 头部        │ 20 字节   │ 无选项时的最小头部             │
│ TLS 记录头      │ 5 字节    │ TLS 1.3 记录层头部             │
├────────────────┼──────────┼──────────────────────────────┤
│ 总开销          │ 63 字节   │                              │
│ 有效载荷（MTU） │ 1500 字节 │ 以太网标准 MTU                │
│ 传输效率        │ 95.9%    │ 1437 / 1500                  │
└────────────────┴──────────┴──────────────────────────────┘

注意：实际效率取决于数据包大小。小包（如 ACK）效率很低：
→ ACK 包：有效载荷 0 字节，总大小 63 字节，效率 0%
→ 这就是为什么 TCP 存在延迟 ACK 和 Nagle 算法
```

### 4. MTU 对分片的影响

#### 4.1 MTU 基础概念

MTU（Maximum Transmission Unit，最大传输单元）是数据链路层所能传输的最大数据帧大小（不含链路层头部）。

```
MTU 与各层的关系：
┌───────────────────────────────────────────────────────────┐
│ 以太网帧 = 以太网头部(14) + IP 包 + FCS(4)                │
│ 最大帧长 = 1518 字节                                      │
│ MTU = 最大 IP 包大小 = 1500 字节                           │
│ MSS = 最大 TCP 数据大小 = MTU - IP 头部 - TCP 头部         │
│     = 1500 - 20 - 20 = 1460 字节                          │
└───────────────────────────────────────────────────────────┘

各类网络的 MTU：
┌──────────────────┬──────────┬──────────────────────────────┐
│ 网络类型          │ MTU       │ 说明                          │
├──────────────────┼──────────┼──────────────────────────────┤
│ 以太网            │ 1500      │ 最常见，数据中心/办公室标准    │
│ 巨型帧 (Jumbo)   │ 9000      │ 数据中心内部，减少分片         │
│ PPPoE            │ 1492      │ ADSL 拨号（8 字节 PPPoE 头）  │
│ GRE 隧道         │ 1476      │ 24 字节 GRE + 新 IP 头        │
│ IPsec 隧道       │ 1400      │ 约 100 字节额外开销           │
│ VXLAN            │ 1450      │ 50 字节 VXLAN 封装            │
│ WireGuard        │ 1440      │ 60 字节 WireGuard 头部        │
│ IPv6 最小 MTU    │ 1280      │ IPv6 强制要求的最小值          │
│ Wi-Fi            │ 2304      │ 802.11 最大帧大小             │
└──────────────────┴──────────┴──────────────────────────────┘
```

#### 4.2 IP 分片机制

当 IP 数据包大小超过链路层 MTU 时，需要进行分片：

```
原始数据包（4000 字节）超过 MTU（1500 字节），需要分片：

原始 IP 包：
┌──────────┬────────────────────────────────────────────┐
│ IP 头部  │              数据（3980 字节）               │
│ (20B)    │                                            │
└──────────┴────────────────────────────────────────────┘

分片后（每个分片都有独立的 IP 头部）：
┌──────────┬───────────────────┬──────┐
│ IP 头部  │ 数据 (1480 字节)   │ MF=1 │  Offset=0
│ (20B)    │                   │ DF=0 │
└──────────┴───────────────────┴──────┘
┌──────────┬───────────────────┬──────┐
│ IP 头部  │ 数据 (1480 字节)   │ MF=1 │  Offset=185 (1480/8)
│ (20B)    │                   │ DF=0 │
└──────────┴───────────────────┴──────┘
┌──────────┬─────────────────┬──────┐
│ IP 头部  │ 数据 (1020 字节) │ MF=0 │  Offset=370 (2960/8)
│ (20B)    │                 │ DF=0 │
└──────────┴─────────────────┴──────┘

关键标志位：
- DF (Don't Fragment) = 0：允许分片
- MF (More Fragments) = 1：还有后续分片
- Fragment Offset：分片数据在原始包中的偏移（以 8 字节为单位）

分片的问题：
1. 任何分片丢失 → 整个包需要重传
2. 分片重组在接收端完成，增加接收端负担
3. 中间路由器无法查看完整的传输层头部（无法做端口过滤）
4. 防火墙可能丢弃分片包（安全策略）
```

#### 4.3 TCP MSS 协商

TCP 在连接建立时通过 MSS（Maximum Segment Size）选项协商最大段大小，避免 IP 分片：

```
三次握手中的 MSS 协商：

客户端 → 服务器：SYN, MSS=1460
  → 告诉服务器："我最多能接收 1460 字节的 TCP 数据"

服务器 → 客户端：SYN-ACK, MSS=1400
  → 告诉客户端："我最多能接收 1400 字节的 TCP 数据"

双方取较小值：MSS = min(1460, 1400) = 1400 字节
→ 后续 TCP 数据段不会超过 1400 字节
→ 加上 TCP 头部(20) + IP 头部(20) = 1440 < 1500
→ 不会在以太网上触发 IP 分片

MSS 与 MTU 的关系：
MSS = MTU - IP 头部 - TCP 头部
    = 1500 - 20 - 20 = 1460 字节（标准以太网）

如果使用 VPN/隧道：
MSS = 1400 (IPsec) - 20 - 20 = 1360 字节
```

#### 4.4 Path MTU Discovery (PMTUD)

PMTUD 用于动态发现源到目的路径上的最小 MTU：

```
PMTUD 工作原理：

1. 发送端设置 DF=1（Don't Fragment），发送大包
2. 数据包到达路径上的某个路由器
3. 路由器发现包大小 > 出接口 MTU，且 DF=1
4. 路由器丢弃数据包
5. 路由器返回 ICMP "Fragmentation Needed"（Type 3, Code 4）
   → 消息中包含路由器的 MTU 值
6. 发送端收到 ICMP，减小发送包大小
7. 重复直到找到合适的 MTU

PMTUD 的"黑洞"问题：

场景：防火墙或中间设备丢弃了 ICMP 消息
→ 发送端收不到 "Fragmentation Needed"
→ 发送端不知道需要减小包大小
→ 大包持续被丢弃，但发送端不知道原因
→ 表现为：大文件传输失败，小包正常

解决方案：
1. 允许 ICMP "Fragmentation Needed" 通过防火墙
2. 在中间设备上配置 TCP MSS Clamping
   → iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN \
       -j TCPMSS --clamp-mss-to-pmtu
3. 使用 VPN/隧道时手动设置较小的 MSS
```

#### 4.5 分片与 MTU 的 SRE 排障

```bash
# 1. 测试路径 MTU（使用 ping 设置 DF 标志）
ping -M do -s 1472 www.example.com -c 2
# -M do: 设置 DF（Don't Fragment）标志
# -s 1472: payload 大小（1472 + 8 ICMP + 20 IP = 1500）
# 如果返回 "message too long, mtu=1500" → MTU 正常
# 如果超时 → MTU < 1500，逐步减小 -s 值

# 2. 二分法查找 MTU
ping -M do -s 1400 target -c 1  # 1428 < 1500，应通过
ping -M do -s 1450 target -c 1  # 1478 < 1500，应通过
ping -M do -s 1472 target -c 1  # 1500 = MTU，边界测试
ping -M do -s 1473 target -c 1  # 1501 > MTU，应失败

# 3. 查看网卡 MTU
ip link show eth0
# mtu 1500
ethtool eth0 | grep -i mtu

# 4. 查看路由的 MTU
ip route get 8.8.8.8
# 8.8.8.8 via 192.168.1.1 dev eth0 src 192.168.1.100 mtu 1500

# 5. 临时修改 MTU（用于测试）
sudo ip link set eth0 mtu 9000  # 启用巨型帧

# 6. 永久修改 MTU（Ubuntu/Debian）
# /etc/netplan/01-netcfg.yaml
# network:
#   ethernets:
#     eth0:
#       mtu: 9000

# 7. 用 tracepath 检测路径 MTU
tracepath www.example.com
# 输出中会显示每一跳的 PMTU

# 8. 抓包分析分片
sudo tcpdump -i eth0 'ip[6:2] & 0x3fff != 0' -n
# 过滤有分片偏移或 MF 标志的包
```

### 5. 各层典型协议和 SRE 关注点

```
SRE 日常工作中各层的排障重点：

┌──────────┬─────────────────────┬──────────────────────────────┐
│ 层级      │ SRE 常用工具         │ 关注指标                      │
├──────────┼─────────────────────┼──────────────────────────────┤
│ L7 应用层 │ curl, wget, ab      │ HTTP 码、延迟 P99、QPS        │
│          │ grpcurl, wrk        │ 错误率、吞吐量                 │
├──────────┼─────────────────────┼──────────────────────────────┤
│ L4 传输层 │ ss, netstat         │ TCP 状态分布、重传率           │
│          │ tcpdump, ngrep      │ 连接数、TIME_WAIT/CLOSE_WAIT  │
├──────────┼─────────────────────┼──────────────────────────────┤
│ L3 网络层 │ ping, traceroute    │ 延迟 RTT、丢包率、TTL         │
│          │ mtr, ip route       │ 路由可达性、ICMP 响应          │
├──────────┼─────────────────────┼──────────────────────────────┤
│ L2 链路层 │ ip neigh, arp       │ ARP 表、MAC 地址              │
│          │ ethtool, brctl      │ CRC 错误、丢帧、VLAN          │
├──────────┼─────────────────────┼──────────────────────────────┤
│ L1 物理层 │ ip link, ethtool    │ 链路状态、速率、双工模式       │
│          │ dmesg               │ 网卡错误、光模块光衰           │
└──────────┴─────────────────────┴──────────────────────────────┘
```

### 6. 网络排障的分层思路

#### 6.1 自下而上排查法（Bottom-Up）

```
最常用的排障方法，从物理层开始逐层向上：

L1 物理层排查：
├── 网线是否插好？指示灯是否亮？
├── ip link show → state UP/DOWN？
├── ethtool eth0 → Speed, Duplex 是否正常？
└── dmesg | grep eth0 → 有无网卡错误？

L2 链路层排查：
├── ip neigh show → 网关 ARP 是否正常？
├── arping -I eth0 网关IP → ARP 解析是否正常？
├── 是否有 VLAN 配置问题？
└── ethtool -S eth0 → CRC 错误、丢帧计数

L3 网络层排查：
├── ip addr show → IP 配置是否正确？
├── ip route show → 默认路由是否存在？
├── ping 网关 → 到网关是否可达？
├── ping 目标IP → 到目标是否可达？
├── traceroute 目标IP → 路径是否正常？
└── mtr 目标IP → 哪一跳丢包或延迟高？

L4 传输层排查：
├── ss -tlnp | grep 端口 → 服务是否在监听？
├── nc -zv 目标 端口 → TCP 端口是否可达？
├── tcpdump port 端口 → 是否有 SYN/SYN-ACK？
├── iptables -L -n → 防火墙是否放行？
└── ss -tan | awk '{print $1}' | sort | uniq -c → TCP 状态分布

L7 应用层排查：
├── curl -v http://目标:端口 → HTTP 响应码和内容
├── dig 目标域名 → DNS 解析是否正常？
├── journalctl -u 服务名 → 应用日志是否有错误？
└── systemctl status 服务名 → 服务运行状态
```

#### 6.2 自上而下排查法（Top-Down）

```
从应用层开始，适合应用层故障明确的场景：

L7 → 用户报告 "网站打不开"
├── curl 测试 → 返回什么错误？
│   ├── "Could not resolve host" → DNS 问题（L7 DNS）
│   ├── "Connection refused" → 端口未监听（L4）
│   ├── "Connection timed out" → 网络不通（L3/L4）
│   └── "SSL certificate problem" → TLS 问题（L6）
├── DNS 解析是否正常？→ dig 测试
├── TCP 连接是否正常？→ nc 测试
└── 逐步向下排查
```

#### 6.3 分治法（Divide and Conquer）

```
从中间层开始，快速缩小故障范围：

1. 先测 L3（ping）→ 通：网络层正常，问题在 L4-L7
                      不通：问题在 L1-L3
2. 如果 L3 通，测 L4（nc 端口）→ 通：问题在 L7
                                   不通：问题在 L4（防火墙/服务未启动）
3. 如果 L3 不通，查 L2（ARP）→ 正常：问题在 L3（路由）
                                 异常：问题在 L1-L2
```

---

## 💻 实战练习

### 练习 1：绘制 OSI 七层模型参考图

**任务**：在纸上或绘图工具中绘制 OSI 七层模型，标注每层的：
- 名称（中文 + 英文）
- 数据单元名称
- 至少 3 个典型协议
- 对应的网络设备
- SRE 排障命令

**参考模板**：

```
┌─────────────────────────────────────────────────────────────┐
│ L7 应用层 (Application)    │ 数据 (Data)                    │
│ 协议: HTTP, DNS, SSH, gRPC │ 设备: WAF, API 网关            │
│ 工具: curl, dig, wget      │ 关注: 响应码, 延迟, 错误率     │
├─────────────────────────────────────────────────────────────┤
│ L6 表示层 (Presentation)   │ 数据 (Data)                    │
│ 协议: TLS, gzip, Protobuf  │ 设备: SSL 加速器               │
│ 工具: openssl              │ 关注: 证书过期, 加密套件       │
├─────────────────────────────────────────────────────────────┤
│ L5 会话层 (Session)        │ 数据 (Data)                    │
│ 协议: RPC, SOCKS, NetBIOS  │ 设备: 代理服务器               │
│ 工具: ss                   │ 关注: 会话超时, 连接复用       │
├─────────────────────────────────────────────────────────────┤
│ L4 传输层 (Transport)      │ 段/数据报 (Segment/Datagram)   │
│ 协议: TCP, UDP, QUIC       │ 设备: 防火墙, L4 LB            │
│ 工具: ss, netstat, tcpdump │ 关注: TCP 状态, 重传, 连接数   │
├─────────────────────────────────────────────────────────────┤
│ L3 网络层 (Network)        │ 包 (Packet)                    │
│ 协议: IP, ICMP, OSPF, BGP  │ 设备: 路由器, 三层交换机       │
│ 工具: ping, traceroute, mtr│ 关注: 路由, 丢包, TTL          │
├─────────────────────────────────────────────────────────────┤
│ L2 数据链路层 (Data Link)  │ 帧 (Frame)                     │
│ 协议: Ethernet, VLAN, ARP  │ 设备: 交换机, 网桥             │
│ 工具: ip neigh, ethtool    │ 关注: ARP, CRC 错误, 广播风暴  │
├─────────────────────────────────────────────────────────────┤
│ L1 物理层 (Physical)       │ 比特 (Bit)                     │
│ 介质: 网线, 光纤, Wi-Fi    │ 设备: 集线器, 中继器           │
│ 工具: ip link, dmesg       │ 关注: 链路状态, 光衰, 误码率   │
└─────────────────────────────────────────────────────────────┘
```

### 练习 2：使用 tcpdump 观察数据包封装

```bash
# 安装 tcpdump
sudo apt-get install tcpdump -y

# 基础抓包：捕获 HTTP 流量
sudo tcpdump -i eth0 port 80 -n -v
# -i eth0: 指定网卡
# -n: 不解析域名
# -v: 显示详细信息（IP TTL、TOS、TCP 窗口等）

# 观察 TCP 三次握手（只看 SYN 和 SYN-ACK）
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0' -n
# 输出示例：
# 14:30:25.123 IP 192.168.1.100.54321 > 93.184.216.34.80: Flags [S], seq 1234567890, win 64240, options [mss 1460,sackOK,TS val 123 ecr 0,nop,wscale 7]
# 14:30:25.145 IP 93.184.216.34.80 > 192.168.1.100.54321: Flags [S.], seq 987654321, ack 1234567891, win 65535, options [mss 1460,sackOK,TS val 456 ecr 123,nop,wscale 7]
# 14:30:25.146 IP 192.168.1.100.54321 > 93.184.216.34.80: Flags [.], ack 987654322, win 512, options [nop,nop,TS val 123 ecr 456]

# 十六进制和 ASCII 显示（可以看到 HTTP 明文）
sudo tcpdump -i eth0 port 80 -n -X
# -X: 同时显示十六进制和 ASCII
# 可以看到 HTTP 请求头：GET / HTTP/1.1

# 保存到文件（用 Wireshark 分析）
sudo tcpdump -i eth0 -w /tmp/capture.pcap port 80
# 用 Wireshark 打开：wireshark /tmp/capture.pcap

# 观察 DNS 查询（UDP 53）
sudo tcpdump -i any -n 'port 53' -v
# 在另一个终端执行 dig example.com

# 观察 ICMP（ping）
sudo tcpdump -i any -n 'icmp' -v
# 在另一个终端执行 ping example.com
```

### 练习 3：MTU 路径发现测试

```bash
# 1. 查看本地网卡 MTU
ip link show | grep mtu
# 输出示例：mtu 1500

# 2. 测试 PMTUD（设置 DF 标志，逐步增大 payload）
# 标准以太网 MTU=1500，最大 payload = 1500 - 20(IP) - 8(ICMP) = 1472
ping -M do -s 1472 -c 2 www.baidu.com  # 应该通
ping -M do -s 1473 -c 2 www.baidu.com  # 应该不通（>1500）

# 3. 如果 1472 不通，逐步减小
ping -M do -s 1400 -c 2 www.baidu.com  # 1428 < 1500
ping -M do -s 1450 -c 2 www.baidu.com  # 1478 < 1500
ping -M do -s 1460 -c 2 www.baidu.com  # 1488 < 1500

# 4. 使用 tracepath 自动发现路径 MTU
tracepath www.baidu.com
# 输出中 PMTU 字段显示路径 MTU

# 5. 模拟 MTU 问题（使用网络命名空间）
sudo ip netns add test_ns
sudo ip link add veth0 type veth peer name veth1
sudo ip link set veth1 netns test_ns
sudo ip addr add 10.0.0.1/24 dev veth0
sudo ip link set veth0 up
sudo ip netns exec test_ns ip addr add 10.0.0.2/24 dev veth1
sudo ip netns exec test_ns ip link set veth1 up

# 设置较小的 MTU
sudo ip link set veth0 mtu 1000
sudo ip netns exec test_ns ip link set veth1 mtu 1000

# 测试分片
ping -M do -s 972 -c 2 10.0.0.2  # 972+28=1000，应该通
ping -M do -s 973 -c 2 10.0.0.2  # 973+28=1001，应该不通

# 清理
sudo ip netns del test_ns
sudo ip link del veth0 2>/dev/null
```

### 练习 4：逐层排障脚本

```bash
#!/bin/bash
# network-layer-diagnosis.sh - 网络分层排障脚本

TARGET=$1
PORT=${2:-80}

if [ -z "$TARGET" ]; then
    echo "用法: $0 <目标地址> [端口]"
    echo "示例: $0 api.example.com 443"
    exit 1
fi

echo "========================================="
echo "  网络分层排障工具"
echo "  目标: $TARGET:$PORT"
echo "========================================="
echo ""

# L1: 物理层检查
echo "[L1] 物理层检查"
echo "-----------------------------------------"
for iface in $(ip -br link show | awk '{print $1}' | grep -v lo); do
    state=$(ip -br link show "$iface" | awk '{print $2}')
    if [ "$state" = "UP" ]; then
        echo "  ✅ $iface: $state"
    else
        echo "  ❌ $iface: $state (链路异常)"
    fi
done
echo ""

# L2: 数据链路层检查
echo "[L2] 数据链路层检查"
echo "-----------------------------------------"
# 检查 ARP 表
GATEWAY=$(ip route | awk '/default/ {print $3}' | head -1)
if [ -n "$GATEWAY" ]; then
    GW_MAC=$(ip neigh show "$GATEWAY" | awk '{print $5}')
    if [ -n "$GW_MAC" ] && [ "$GW_MAC" != "FAILED" ]; then
        echo "  ✅ 网关 $GATEWAY 的 MAC: $GW_MAC"
    else
        echo "  ❌ 网关 $GATEWAY ARP 解析失败"
    fi
else
    echo "  ⚠️ 未找到默认网关"
fi
echo ""

# L3: 网络层检查
echo "[L3] 网络层检查"
echo "-----------------------------------------"
# IP 配置
echo "  本机 IP:"
ip -4 addr show | grep inet | grep -v 127.0.0.1 | awk '{print "    " $2}'
echo ""

# ping 测试
echo "  Ping 测试:"
if ping -c 3 -W 2 "$TARGET" &>/dev/null; then
    RTT=$(ping -c 3 -W 2 "$TARGET" 2>/dev/null | tail -1 | awk -F'/' '{print $5}')
    echo "    ✅ Ping 通 (平均 RTT: ${RTT}ms)"
else
    echo "    ❌ Ping 不通"
    echo "    → 检查路由: ip route get $TARGET"
    echo "    → 检查 DNS: dig $TARGET"
fi
echo ""

# L4: 传输层检查
echo "[L4] 传输层检查"
echo "-----------------------------------------"
# TCP 端口测试
if timeout 3 bash -c "echo > /dev/tcp/$TARGET/$PORT" 2>/dev/null; then
    echo "  ✅ TCP 端口 $PORT 可达"
else
    echo "  ❌ TCP 端口 $PORT 不可达"
    # 检查本地防火墙
    FW_RULES=$(iptables -L -n 2>/dev/null | grep -c "$PORT")
    if [ "$FW_RULES" -gt 0 ]; then
        echo "    ⚠️ 发现 $FW_RULES 条与端口 $PORT 相关的防火墙规则"
    fi
fi

# TCP 状态统计
echo ""
echo "  本机 TCP 连接状态:"
ss -tan 2>/dev/null | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn | head -5 | \
    while read count state; do
        echo "    $state: $count"
    done
echo ""

# L7: 应用层检查
echo "[L7] 应用层检查"
echo "-----------------------------------------"
# DNS 解析
RESOLVED_IP=$(dig +short "$TARGET" A 2>/dev/null | head -1)
if [ -n "$RESOLVED_IP" ]; then
    echo "  ✅ DNS 解析: $TARGET → $RESOLVED_IP"
else
    echo "  ❌ DNS 解析失败"
fi

# HTTP 测试
if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$TARGET:$PORT" --connect-timeout 5 --max-time 10 2>/dev/null)
    if [ -n "$HTTP_CODE" ] && [ "$HTTP_CODE" != "000" ]; then
        if [[ "$HTTP_CODE" =~ ^[23] ]]; then
            echo "  ✅ HTTP 响应码: $HTTP_CODE"
        else
            echo "  ⚠️ HTTP 响应码: $HTTP_CODE"
        fi
    else
        echo "  ❌ HTTP 请求失败（超时或连接错误）"
    fi
fi

echo ""
echo "========================================="
echo "  排障完成"
echo "========================================="
```

---

## 🎯 面试题精选

### Q1: OSI 七层模型和 TCP/IP 四层模型有什么区别？

**参考答案**：

```
核心区别：
1. 层数不同：OSI 7 层，TCP/IP 4 层
2. 设计理念：OSI 先有模型后有协议（理论驱动），TCP/IP 先有协议后有模型（实践驱动）
3. 上层合并：TCP/IP 将 OSI 的应用层+表示层+会话层合并为应用层
4. 下层合并：TCP/IP 将 OSI 的数据链路层+物理层合并为网络接口层
5. 实际使用：OSI 主要用于教学和理论分析，TCP/IP 是互联网的实际协议栈
6. 服务/接口/协议：OSI 明确定义了这三个概念，TCP/IP 没有严格区分
```

### Q2: 为什么需要网络分层？分层有什么好处和坏处？

**参考答案**：

```
好处：
1. 标准化：各层独立标准化，厂商可以独立实现
2. 解耦合：修改某层不影响其他层（如升级 Wi-Fi 不影响 TCP）
3. 可调试：逐层排查，快速定位故障
4. 可复用：IP 层可以同时承载 TCP 和 UDP
5. 模块化：不同团队并行开发

坏处：
1. 性能开销：每层都要添加头部，增加协议开销
2. 复杂性：完整的分层在某些场景下过于复杂
3. 层间耦合：某些功能跨层（如 TLS 在表示层还是应用层？）
4. 灵活性受限：严格的分层可能限制优化（如 TCP Fast Open 跨越了传输层和应用层）
```

### Q3: 数据从应用层到物理层经历了怎样的封装过程？

**参考答案**：

```
以 HTTP 请求为例：
1. 应用层：生成 HTTP 请求文本（GET / HTTP/1.1）
2. 表示层：TLS 加密（添加 TLS Record 头部）
3. 传输层：添加 TCP 头部（源端口、目的端口 443、序列号、标志位）
4. 网络层：添加 IP 头部（源 IP、目的 IP、TTL、协议号 6=TCP）
5. 数据链路层：添加以太网头部（源 MAC、目的 MAC=网关、类型 0x0800）和 FCS 尾部
6. 物理层：转换为电信号/光信号传输

每层只处理自己关心的信息：
- 路由器：只看 IP 头部（L3）
- 交换机：只看 MAC 地址（L2）
- 防火墙：可以看 L3/L4/L7
```

### Q4: 什么是 MTU？MTU 过大会导致什么问题？

**参考答案**：

```
MTU（最大传输单元）是数据链路层能传输的最大帧数据大小。

MTU 过大的影响：
1. 分片增加：超过路径 MTU 的包需要 IP 分片
2. 性能下降：分片和重组消耗 CPU，任一分片丢失需重传整个包
3. PMTUD 黑洞：如果 ICMP 被防火墙拦截，大包会被静默丢弃
4. 延迟增加：分片重组需要等待所有分片到达

SRE 场景：
- VPN/隧道场景需要关注 MTU（GRE、IPsec、VXLAN 都会减小有效 MTU）
- 数据中心使用巨型帧（9000）减少分片，但需要全链路支持
- Kubernetes 中 VXLAN 封装使 MTU 降至 1450
```

### Q5: TCP/IP 模型中，各层的数据单元分别叫什么？

**参考答案**：

```
应用层：数据（Data / Message）
传输层：段（Segment，TCP）/ 数据报（Datagram，UDP）
网络层：包（Packet / Datagram）
数据链路层：帧（Frame）
物理层：比特（Bit）

记忆方法：
- Segment = 段（TCP 把数据切成一段一段）
- Packet = 包（IP 把段打包，加上地址）
- Frame = 帧（链路层把包包成帧，加上 MAC）
- Bit = 比特（物理层把帧转成 0 和 1）
```

### Q6: ping 命令工作在哪一层？traceroute 呢？

**参考答案**：

```
ping：
- 使用 ICMP 协议，工作在网络层（L3）
- 发送 ICMP Echo Request，接收 Echo Reply
- 只测试网络层可达性，不测试传输层和应用层
- ping 通不代表服务可用（可能端口未监听或被防火墙拦截）

traceroute：
- 也工作在网络层（L3）
- 原理：发送 TTL 递增的 UDP 包（Linux）或 ICMP 包（Windows）
- TTL=1 的包在第一跳被丢弃，返回 ICMP Time Exceeded
- TTL=2 的包在第二跳被丢弃...
- 依次获取路径上每一跳的 IP 地址

mtr（My Traceroute）：
- 结合了 ping 和 traceroute
- 持续测试每一跳的延迟和丢包率
- 是网络排障最实用的工具
```

### Q7: 为什么说 ping 通不代表服务可用？

**参考答案**：

```
ping 只测试到 L3（网络层），而服务运行在 L4-L7：

1. ping 使用 ICMP，不使用 TCP/UDP
   → ICMP 可以通，但 TCP 端口可能未监听
   → "Connection refused" = 端口未监听

2. 防火墙可能放行 ICMP 但拦截 TCP
   → ping 通，但 telnet 端口超时

3. 服务进程可能崩溃但主机正常
   → ping 通（主机操作系统响应 ICMP）
   → 但服务已不再监听端口

4. 负载均衡器后面的服务可能部分不可用
   → ping LB 的 IP 通
   → 但后端部分实例不健康

正确的排障方法：ping（L3）→ nc（L4）→ curl（L7）
```

### Q8: 在 Kubernetes 中，Pod 的网络封装涉及哪些层？

**参考答案**：

```
Kubernetes Pod 网络（以 VXLAN 为例）：

1. Pod 内的容器发送 HTTP 请求（L7 应用层）
2. 添加 TCP 头部（L4 传输层）
3. 添加 IP 头部：源 IP = Pod IP，目的 IP = 目的 Pod IP（L3 网络层）
4. 封装为以太网帧（L2 数据链路层）
5. CNI 插件（如 Flannel VXLAN）进行二次封装：
   a. 添加 VXLAN 头部（UDP 8472）
   b. 添加外层 IP 头部（源 = 宿主机 IP，目的 = 目标宿主机 IP）
   c. 添加外层以太网头部
6. 通过物理网络传输

MTU 影响：
- 标准 MTU 1500
- VXLAN 封装开销 50 字节
- Pod 内有效 MTU = 1450
- 如果不调整 Pod 的 MTU，可能导致分片和性能下降
```

---

## 📚 深入阅读

### 官方文档与 RFC
- [RFC 1122 - Host Requirements](https://datatracker.ietf.org/doc/html/rfc1122) — TCP/IP 协议核心规范
- [RFC 791 - Internet Protocol (IPv4)](https://datatracker.ietf.org/doc/html/rfc791) — IPv4 协议规范
- [RFC 793 - Transmission Control Protocol](https://datatracker.ietf.org/doc/html/rfc793) — TCP 协议规范
- [RFC 894 - A Standard for the Transmission of IP Datagrams over Ethernet](https://datatracker.ietf.org/doc/html/rfc894) — 以太网上的 IP 传输

### 推荐书籍
- 《TCP/IP 详解 卷 1：协议》— W. Richard Stevens，网络协议的圣经
- 《计算机网络：自顶向下方法》— Kurose & Ross，适合入门
- 《图解 HTTP》— 前端/后端工程师的 HTTP 入门
- 《网络是怎样连接的》— 户根勤，从浏览器到服务器的完整链路

### 在线资源
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/) — 经典网络编程指南
- [Cloudflare Learning Center](https://www.cloudflare.com/learning/) — 通俗的网络知识教程
- [Brendan Gregg - Linux Network Performance](https://www.brendangregg.com/linuxperf.html) — Linux 网络性能分析

### 视频课程
- [Bilibili - 计算机网络微课堂](https://www.bilibili.com/video/BV1JV411t7ow/) — 系统讲解 OSI 和 TCP/IP
- [YouTube - Computer Networking Complete Course](https://www.youtube.com/watch?v=IPvYjXCsTg8) — 免费网络课程

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出 OSI 七层模型，标注每层的职责、协议、设备和数据单元
- [ ] 能解释 OSI 与 TCP/IP 模型的映射关系和各自的优缺点
- [ ] 能完整描述 HTTP 请求的封装和解封装过程
- [ ] 理解 MTU、MSS、分片机制和 PMTUD 的工作原理
- [ ] 理解各层在 SRE 排障中的作用和常用工具
- [ ] 能解释为什么 ping 通不代表服务可用

### 实操检查点
- [ ] 能使用 tcpdump 抓包并分析 TCP 三次握手
- [ ] 能使用 ping -M do 测试路径 MTU
- [ ] 能使用 tracepath/mtr 追踪路由路径
- [ ] 能使用 ip link/addr/route/neigh 查看网络配置
- [ ] 能编写分层排障脚本
- [ ] 完成了全部 4 个实战练习

---

*由 SRE 学习计划生成 | 2026-04-29*
