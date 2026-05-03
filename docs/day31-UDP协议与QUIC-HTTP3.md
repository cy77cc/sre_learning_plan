# Day 31: UDP 协议、QUIC（HTTP/3）

> 📅 日期：2026-05-01
> 📖 学习主题：UDP 协议、QUIC（HTTP/3）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 30 TCP 协议详解

---

## 🎯 学习目标

完成 Day 31 的学习后，你应该掌握：
- 深入理解 UDP 协议的特点、适用场景和局限性
- 掌握 DNS 基于 UDP 的工作原理和 TCP 回退机制
- 理解 QUIC 协议的设计动机、核心特性（0-RTT、多路复用、连接迁移）
- 掌握 HTTP/3 与 HTTP/1.1、HTTP/2 的全面对比
- 能够在 SRE 实战中诊断 UDP 相关问题和部署 QUIC/HTTP/3

---

## 📖 核心知识点

### 1. UDP 协议详解

#### 1.1 UDP 概述

UDP（User Datagram Protocol，用户数据报协议）是传输层的核心协议之一。与 TCP 的复杂可靠不同，UDP 以简单和低延迟著称——它只做了传输层最基本的事情：复用/分用和差错校验。

```
UDP 的设计哲学：
→ "Do one thing and do it well"
→ 只负责端到端的数据传输
→ 不做连接管理、不做可靠传输、不做流量控制、不做拥塞控制
→ 把复杂性留给应用层，让应用自己决定需要什么

类比：
→ TCP = 挂号信（有回执、保证送达、有序）
→ UDP = 明信片（投出去就不管了、可能丢失、不保证顺序）
```

#### 1.2 UDP 头部格式

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          源端口 (16)           |        目的端口 (16)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           长度 (16)            |          校验和 (16)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           数据（Payload）                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

UDP 头部总计：8 字节（固定，无选项）
```

| 字段 | 大小 | 说明 | 与 TCP 对比 |
|------|------|------|-----------|
| 源端口 | 16 位 | 发送方端口（可选，可为 0） | TCP 也有 |
| 目的端口 | 16 位 | 接收方端口 | TCP 也有 |
| 长度 | 16 位 | UDP 头部 + 数据的总长度（最小 8） | TCP 没有（靠 IP 层） |
| 校验和 | 16 位 | IPv4 可选，IPv6 强制 | TCP 强制 |

**UDP 头部仅 8 字节 vs TCP 头部 20-60 字节**——这就是 UDP "轻量"的体现。

#### 1.3 UDP vs TCP 全面对比

| 特性 | TCP | UDP | SRE 视角差异 |
|------|-----|-----|-------------|
| 连接方式 | 面向连接（三次握手） | 无连接 | UDP 无连接建立延迟 |
| 可靠性 | 可靠（ACK + 重传 + 排序） | 不可靠（尽力而为） | UDP 丢包不重传 |
| 顺序保证 | 有序（序列号） | 无序 | UDP 包可能乱序到达 |
| 流量控制 | 滑动窗口 | 无 | UDP 可能打满带宽 |
| 拥塞控制 | 有（Cubic/BBR） | 无 | UDP 不会自动降速 |
| 头部大小 | 20-60 字节 | 8 字节 | UDP 开销更小 |
| 传输模式 | 字节流（无消息边界） | 数据报（有消息边界） | UDP 天然避免粘包 |
| 连接状态 | 有（11 种状态） | 无状态 | UDP 无 CLOSE_WAIT/TIME_WAIT |
| 资源消耗 | 高（内核维护连接状态） | 低 | UDP 可以支持更多并发 |
| 典型应用 | HTTP、SSH、FTP、数据库 | DNS、DHCP、NTP、视频流 | 各自适合不同场景 |

#### 1.4 UDP 适用场景分析

```
场景 1: DNS 查询
→ 请求/响应都很小（通常 < 512 字节）
→ 一问一答，无需维护连接状态
→ 延迟敏感（DNS 是所有网络请求的前置操作）
→ UDP 无连接开销 = 更快的查询

场景 2: 实时音视频（RTP/WebRTC）
→ 旧数据无价值（过期的音频帧不如丢弃）
→ 重传会引入不可接受的延迟
→ 应用层自己处理抖动缓冲（Jitter Buffer）
→ UDP 的"不可靠"反而是优势

场景 3: 在线游戏
→ 状态频繁更新（每秒 20-60 次）
→ 旧的状态更新比新的延迟到达更没意义
→ 低延迟比可靠性更重要
→ 应用层使用序列号自行处理乱序

场景 4: DHCP
→ 获取 IP 地址前还没有完整的网络栈
→ 无法使用 TCP（TCP 需要 IP 地址才能建立连接）
→ UDP 不需要预先的连接状态

场景 5: NTP 时间同步
→ 小数据包（48 字节）
→ 定期发送，偶尔丢失不影响
→ 对延迟极其敏感（要计算 RTT 来估算时间差）

场景 6: QUIC/HTTP3
→ 在 UDP 上重新实现可靠传输
→ 避免了 TCP 的队头阻塞问题
→ 用户态实现，可以快速迭代协议
```

#### 1.5 UDP 的风险与 SRE 关注点

```
风险 1: 无拥塞控制
┌─────────────────────────────────────────────────────────┐
│ → UDP 不会感知网络拥塞                                    │
│ → 大量 UDP 流量可能打满带宽                               │
│ → 影响同链路的 TCP 连接（TCP 会退让，UDP 不会）           │
│ → SRE 场景：监控流量突增导致业务 TCP 连接受影响           │
│                                                          │
│ 解决方案：                                               │
│ → 应用层实现拥塞控制（如 QUIC 的 BBR）                    │
│ → 网络设备对 UDP 做 QoS 限速                              │
│ → 使用 DSCP 标记区分 UDP 流量优先级                       │
└─────────────────────────────────────────────────────────┘

风险 2: UDP 反射/放大攻击
┌─────────────────────────────────────────────────────────┐
│ → 攻击者伪造源 IP 发送小请求                              │
│ → 服务器将大响应发送到被伪造的 IP（受害者）               │
│ → 放大倍数：DNS 28-54x, NTP 556x, Memcached 51000x     │
│                                                          │
│ 防御：                                                   │
│ → BCP38/BCP84 源地址验证（ISP 层面）                      │
│ → 限制 UDP 响应速率                                       │
│ → DNS 响应大小限制                                        │
│ → 关闭不必要的 UDP 服务（如 Memcached 对外暴露）          │
└─────────────────────────────────────────────────────────┘

风险 3: NAT/防火墙穿透困难
┌─────────────────────────────────────────────────────────┐
│ → UDP 无连接状态，NAT 需要维护映射表                      │
│ → NAT UDP 映射超时短（通常 30-180 秒）                    │
│ → 需要应用层 keepalive 保活                               │
│ → 防火墙可能默认只放行 TCP，不放行 UDP                    │
│                                                          │
│ SRE 场景：                                               │
│ → Kubernetes NetworkPolicy 忘记放行 UDP 53               │
│ → 云安全组只配了 TCP，没配 UDP                            │
└─────────────────────────────────────────────────────────┘
```

### 2. DNS 协议与 UDP/TCP

#### 2.1 DNS 协议概述

DNS 是互联网的基础设施，将域名映射为 IP 地址。它同时使用 UDP 和 TCP。

```
DNS 查询完整流程：

用户输入: www.example.com
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│ 1. 浏览器缓存检查                                          │
│    → 查找 DNS 缓存 → 命中？直接返回                        │
│ 2. 操作系统缓存（/etc/hosts + DNS Cache）                  │
│    → systemd-resolved / nscd 缓存                         │
│ 3. 本地 DNS 服务器（递归解析器）                            │
│    → 通常由 ISP 提供，或 8.8.8.8 / 1.1.1.1                │
│ 4. 递归查询过程：                                          │
│    → 本地 DNS → 根服务器(.) → 返回 .com TLD 地址           │
│    → 本地 DNS → .com TLD → 返回 example.com 权威 DNS      │
│    → 本地 DNS → 权威 DNS → 返回 www.example.com 的 A 记录  │
│ 5. 本地 DNS 缓存结果（TTL 内有效）                         │
│ 6. 返回给客户端并缓存                                      │
└───────────────────────────────────────────────────────────┘
```

#### 2.2 DNS 使用 UDP 还是 TCP？

```
标准查询 → UDP 53（默认）
→ 响应通常 < 512 字节
→ 无需建立连接，延迟更低
→ 一问一答模式，简单高效

切换到 TCP 53 的条件：
┌─────────────────────────────────────────────────────────┐
│ 条件 1: 响应超过 512 字节                                │
│   → 服务器设置 TC（Truncated）标志位                     │
│   → 客户端收到 TC=1 后改用 TCP 重新查询                  │
│   → EDNS0 扩展允许 UDP 响应最大 4096 字节               │
│                                                          │
│ 条件 2: 区域传输（AXFR/IXFR）                            │
│   → 主从 DNS 同步数据时使用                              │
│   → 数据量大，需要可靠传输                               │
│                                                          │
│ 条件 3: DNSSEC 验证                                      │
│   → DNSSEC 签名使响应变大                                │
│   → 可能超过 EDNS0 的 UDP 限制                           │
│                                                          │
│ 条件 4: 动态更新                                         │
│   → DNS 动态更新需要可靠性保证                           │
│                                                          │
│ 条件 5: 客户端显式请求 TCP                               │
│   → dig +tcp example.com                                │
└─────────────────────────────────────────────────────────┘

DNS 协议切换流程：
客户端 → DNS 服务器（UDP 53 查询）
                │
                ▼
DNS 服务器返回响应（TC=0 或 TC=1）
                │
    ┌───────────┴───────────┐
    │ TC=0（完整响应）        │ TC=1（响应被截断）
    │ 使用 UDP 结果           │ 客户端用 TCP 53 重新查询
    └───────────────────────┘
```

#### 2.3 DNS 查询命令详解

```bash
# 基础查询
dig example.com
# 关键输出：
# ;; ANSWER SECTION:
# example.com.    3600    IN    A    93.184.216.34
#                  ↑ TTL         ↑ 记录类型  ↑ IP

# 指定 DNS 服务器
dig @8.8.8.8 example.com
dig @1.1.1.1 example.com

# 指定记录类型
dig example.com A        # IPv4 地址
dig example.com AAAA     # IPv6 地址
dig example.com MX       # 邮件服务器
dig example.com NS       # 域名服务器
dig example.com TXT      # 文本记录（SPF/DKIM/验证）
dig example.com CNAME    # 别名
dig example.com SOA      # 起始授权

# 追踪完整解析链路（从根服务器开始）
dig +trace example.com
# 可以看到每一级的查询过程

# 强制使用 TCP
dig +tcp example.com

# 强制使用 UDP（默认）
dig +notcp example.com

# 查看查询耗时
dig example.com | grep "Query time"
# ;; Query time: 23 msec

# 反向解析（IP → 域名）
dig -x 93.184.216.34

# 查看 DNSSEC 签名
dig +dnssec example.com

# 简洁输出
host example.com
# example.com has address 93.184.216.34

# nslookup（较老但仍常用）
nslookup example.com
nslookup -type=MX example.com
```

#### 2.4 DNS 缓存与 TTL

```bash
# 查看本地 DNS 缓存统计（systemd-resolved）
resolvectl statistics
# 或
resolvectl query example.com
# 会显示是否命中缓存

# 清除本地 DNS 缓存
sudo systemctl restart systemd-resolved
# macOS: sudo killall -HUP mDNSResponder
# Windows: ipconfig /flushdns

# 查看 DNS 配置
cat /etc/resolv.conf
# nameserver 192.168.1.1
# nameserver 8.8.8.8
# options timeout:2 attempts:3

# TTL 策略建议：
# TTL=300 (5分钟): 适合频繁变更的记录（如 CDN）
# TTL=3600 (1小时): 适合一般服务
# TTL=86400 (24小时): 适合很少变更的记录
# TTL 过短 → DNS 查询频繁，增加延迟
# TTL 过长 → DNS 变更生效慢（故障切换慢）
```

#### 2.5 DNS 在 Kubernetes 中的特殊处理

```
Kubernetes DNS 架构：
┌─────────────────────────────────────────────────────────┐
│ Pod → CoreDNS (kube-dns) → 外部 DNS                      │
│                                                          │
│ Pod 内 /etc/resolv.conf:                                │
│ nameserver 10.96.0.10        ← CoreDNS ClusterIP       │
│ search default.svc.cluster.local svc.cluster.local ...  │
│ options ndots:5 timeout:2 attempts:2                    │
│                                                          │
│ ndots:5 的含义：                                         │
│ → 域名中 "." 数量 < 5 时，先搜索 search 域              │
│ → www.example → 搜索 www.example.default.svc...         │
│ → www.example.com → 直接查询（有 3 个点，< 5）           │
│ → 内部服务名不需要 FQDN                                  │
└─────────────────────────────────────────────────────────┘

Kubernetes DNS 常见问题：
1. NetworkPolicy 未放行 UDP 53 → DNS 超时
2. CoreDNS Pod 资源不足 → DNS 响应慢
3. ndots:5 导致大量无效搜索查询 → DNS 服务器压力大
4. DNS 缓存不足 → 频繁查询增加延迟
```

### 3. QUIC 协议深入

#### 3.1 为什么需要 QUIC？

```
TCP + TLS 的问题：

问题 1: 连接建立延迟高
┌─────────────────────────────────────────────────────────┐
│ 传统 HTTPS (TCP + TLS 1.3):                              │
│                                                          │
│ Client                          Server                  │
│   │  ──── TCP SYN ──────────→   │  ← 1 RTT              │
│   │  ←─── TCP SYN-ACK ──────   │                       │
│   │  ──── TCP ACK ───────────→  │                       │
│   │                              │                       │
│   │  ──── TLS ClientHello ──→   │  ← 1 RTT              │
│   │  ←─── TLS ServerHello ──   │                       │
│   │  ──── TLS Finished ─────→   │                       │
│   │                              │                       │
│   │  ──── 终于开始传数据 ────→  │                       │
│                                                          │
│ 总计: 2 RTT 才能开始传数据！                              │
│ 如果 RTT = 100ms → 200ms 后才能发第一个字节              │
└─────────────────────────────────────────────────────────┘

问题 2: TCP 层队头阻塞（Head-of-Line Blocking）
┌─────────────────────────────────────────────────────────┐
│ HTTP/2 的多路复用建立在 TCP 之上:                         │
│                                                          │
│ TCP 字节流: [S1_Pkt1][S2_Pkt1][S1_Pkt2*][S2_Pkt2]...  │
│                                       ↑ 这个包丢了       │
│                                                          │
│ → TCP 必须等 Pkt2 重传成功才能继续                       │
│ → Pkt2 之后的所有数据都不能交付                           │
│ → Stream 1 和 Stream 2 都被阻塞！                        │
│ → 一个丢包影响所有 HTTP 流                               │
└─────────────────────────────────────────────────────────┘

问题 3: 连接迁移困难
┌─────────────────────────────────────────────────────────┐
│ TCP 连接由四元组标识:                                    │
│ (源 IP, 源端口, 目的 IP, 目的端口)                       │
│                                                          │
│ 手机从 WiFi 切换到 4G:                                   │
│ → IP 地址变化 → 四元组变化 → 连接断开                    │
│ → 需要重新三次握手 + TLS 握手                            │
│ → 用户体验：页面卡顿/断连                                │
└─────────────────────────────────────────────────────────┘

问题 4: 协议僵化
┌─────────────────────────────────────────────────────────┐
│ TCP 在内核中实现，更新困难:                               │
│ → 部署新的 TCP 特性需要升级操作系统内核                  │
│ → 中间设备（NAT、防火墙）可能丢弃不理解的 TCP 选项       │
│ → TLS 1.3 的部署花了多年才普及                           │
│                                                          │
│ QUIC 在用户态实现:                                        │
│ → 应用程序自带 QUIC 实现，无需内核更新                    │
│ → 可以快速迭代协议特性                                    │
│ → 新版本部署 = 更新应用（如更新 Chrome）                  │
└─────────────────────────────────────────────────────────┘
```

#### 3.2 QUIC 协议栈

```
QUIC 协议栈对比 TCP+TLS+HTTP/2:

TCP+TLS+HTTP/2:                QUIC+HTTP/3:
┌──────────────────┐           ┌──────────────────┐
│    HTTP/2        │           │    HTTP/3        │
├──────────────────┤           ├──────────────────┤
│    TLS 1.2/1.3   │           │    QUIC          │
├──────────────────┤           │  ┌──────────────┐│
│    TCP           │           │  │ 可靠传输      ││
├──────────────────┤           │  │ 流量控制      ││
│    IP             │           │  │ TLS 1.3      ││
└──────────────────┘           │  │ 连接迁移      ││
 4 个独立层                    │  │ 多路复用      ││
 各层有冗余头部                 │  └──────────────┘│
 内核态实现                     ├──────────────────┤
                               │    UDP           │
                               ├──────────────────┤
                               │    IP             │
                               └──────────────────┘
                                传输+加密合并
                                减少头部开销
                                用户态实现
```

#### 3.3 QUIC 的核心特性

**特性 1: 0-RTT / 1-RTT 连接建立**

```
QUIC 首次连接（1 RTT）：
Client                              Server
  │                                    │
  │  Initial + Handshake               │
  │  (ClientHello + 早期数据)           │
  │ ─────────────────────────────────> │  1 RTT
  │                                    │
  │  Handshake + 1-RTT Keys            │
  │ <──────────────────────────────── │
  │                                    │
  │  开始传输应用数据                   │
  │ ─────────────────────────────────> │

QUIC 恢复连接（0 RTT）：
Client                              Server
  │                                    │
  │  0-RTT 数据                        │
  │  (加密的早期数据，使用缓存的密钥)    │
  │ ─────────────────────────────────> │  0 RTT！
  │                                    │  服务器可以直接处理
  │  1-RTT 数据                        │
  │ <──────────────────────────────── │
  │                                    │
  → 客户端发出第一个包就携带应用数据
  → 不需要等待服务器响应
  → 从用户角度看 = 0 延迟

对比 TCP+TLS 1.3:
→ 首次连接: TCP(1 RTT) + TLS(1 RTT) = 2 RTT
→ 恢复连接: TCP(1 RTT) + TLS(0 RTT) = 1 RTT
→ QUIC 首次: 1 RTT（省了 TCP 握手）
→ QUIC 恢复: 0 RTT（省了所有握手）

0-RTT 的安全风险:
→ 0-RTT 数据没有前向安全性（Forward Secrecy）
→ 可能被重放攻击（Replay Attack）
→ 服务器应该只对幂等请求使用 0-RTT 数据
→ GET 请求通常安全，POST 请求需要额外保护
```

**特性 2: 多路复用无队头阻塞**

```
TCP + HTTP/2 的队头阻塞：

TCP 是字节流，所有 HTTP 流共享同一个 TCP 连接:
┌─────────────────────────────────────────────────────────┐
│ TCP Stream: [S1_P1][S2_P1][S1_P2*][S3_P1][S2_P2]      │
│                                   ↑ 丢失               │
│                                                          │
│ → S1_P2 丢失 → TCP 等待重传                             │
│ → S1_P2 之后的所有包都不能交付给应用层                   │
│ → S2、S3 也被阻塞（虽然它们的数据已经到了）              │
│ → 一个丢包影响所有流                                     │
└─────────────────────────────────────────────────────────┘

QUIC 的流级独立可靠传输：

QUIC 在 UDP 之上为每个 Stream 独立实现可靠传输:
┌─────────────────────────────────────────────────────────┐
│ QUIC Stream 1: [Pkt1] [Pkt2*] [Pkt3]                   │
│                          ↑ 丢失，只影响 Stream 1         │
│ QUIC Stream 2: [Pkt1] [Pkt2] [Pkt3] [Pkt4]             │
│                       ↑ 不受影响，继续处理               │
│ QUIC Stream 3: [Pkt1] [Pkt2] [Pkt3]                    │
│                    ↑ 不受影响，继续处理                  │
│                                                          │
│ → 每个 Stream 有独立的序列号和流控                       │
│ → Stream 2 和 3 可以继续交付数据给应用层                 │
│ → 只有 Stream 1 等待重传                                 │
│ → 丢包影响范围从"所有流"缩小到"单个流"                  │
└─────────────────────────────────────────────────────────┘

HTTP/2 over TCP vs HTTP/3 over QUIC:
┌──────────────────────┬───────────────────────────────────┐
│ HTTP/2 (TCP)          │ HTTP/3 (QUIC)                      │
├──────────────────────┼───────────────────────────────────┤
│ 多流共享 TCP 连接     │ 每个流独立可靠传输                 │
│ TCP 层队头阻塞        │ 无 TCP 队头阻塞                    │
│ 一个丢包影响所有流    │ 丢包只影响单个流                   │
│ 流量控制：TCP + HTTP  │ 流量控制：QUIC 统一处理            │
└──────────────────────┴───────────────────────────────────┘
```

**特性 3: 连接迁移（Connection Migration）**

```
TCP 连接标识: 四元组 (源IP, 源端口, 目的IP, 目的端口)
→ 任何一个变化 → 连接断开 → 重新握手

QUIC 连接标识: Connection ID (CID)
→ CID 由客户端和服务器协商
→ CID 与 IP 地址无关
→ IP 变化 → CID 不变 → 连接保持

场景：手机从 WiFi 切换到 4G
┌─────────────────────────────────────────────────────────┐
│ TCP:                                                    │
│ WiFi: (192.168.1.100, 54321, 93.184.216.34, 443)       │
│   → WiFi 断开                                          │
│   → 连接断开                                           │
│ 4G: (10.0.0.50, 54321, 93.184.216.34, 443)             │
│   → 需要重新三次握手 + TLS 握手                         │
│   → 用户体验：页面卡顿 2-3 秒                           │
│                                                          │
│ QUIC:                                                    │
│ WiFi: CID=abc123                                       │
│   → WiFi 断开                                          │
│ 4G: CID=abc123 (不变！)                                │
│   → 客户端发送 PATH_CHALLENGE 探测新路径               │
│   → 服务器回复 PATH_RESPONSE 确认                      │
│   → 连接无缝继续                                       │
│   → 用户体验：几乎无感知                               │
└─────────────────────────────────────────────────────────┘
```

**特性 4: 内置 TLS 1.3**

```
QUIC 将 TLS 1.3 集成到协议中（不可分割）:

TCP + TLS:
→ TCP 是明文握手（三次握手）
→ TLS 在 TCP 之上加密（额外 RTT）
→ 两层独立，有冗余开销

QUIC:
→ 传输层握手和加密握手合并
→ 第一个 QUIC 包就是加密的
→ 所有 QUIC 数据包都经过加密（包括头部）
→ 没有明文传输的阶段

安全性提升:
→ TCP 头部明文 → 中间设备可以看到序列号、标志位
→ QUIC 头部加密 → 中间设备只能看到 UDP 头部
→ 保护了连接元数据（连接迁移不会泄露信息）
→ 更好的隐私保护
```

#### 3.4 QUIC vs TCP+TLS 全面对比

| 特性 | TCP + TLS 1.3 | QUIC (HTTP/3) | 优势方 |
|------|---------------|---------------|--------|
| 首次连接延迟 | 2 RTT | 1 RTT | QUIC |
| 恢复连接延迟 | 1 RTT | 0 RTT | QUIC |
| 队头阻塞 | 有（TCP 层） | 无（Stream 级独立） | QUIC |
| 加密范围 | TLS 层以上 | 所有 QUIC 数据（含头部） | QUIC |
| 连接迁移 | 不支持（四元组变化断连） | 原生支持（CID） | QUIC |
| 拥塞控制 | 内核态（升级困难） | 用户态（可自定义） | QUIC |
| 协议演进 | 内核升级周期长 | 应用更新即可 | QUIC |
| 成熟度 | 非常成熟 | 较新，仍在演进 | TCP |
| 中间件兼容 | 所有中间件支持 | 部分中间件不支持 UDP | TCP |
| CPU 开销 | 内核态优化成熟 | 用户态实现，开销略高 | TCP |
| 抓包分析 | 工具成熟 | 加密流量难以分析 | TCP |
| UDP 被阻断 | 不受影响 | 回退到 TCP/TLS | TCP |

#### 3.5 QUIC 的拥塞控制

```
QUIC 默认使用类似 TCP 的拥塞控制，但可以灵活替换:

Google QUIC 的拥塞控制:
→ 基于 TCP Cubic 的变体
→ 在用户态实现，可以快速迭代
→ 支持 Pacing（均匀发送，减少突发丢包）

BBR for QUIC:
→ Google 已将 BBR 移植到 QUIC
→ 比 Cubic 更适合高带宽长延迟场景
→ 可以通过应用层配置切换

QUIC 拥塞控制的优势:
→ 不需要修改内核就能部署新算法
→ 可以针对特定场景定制（如视频流、游戏）
→ A/B 测试更容易（只需更新客户端）
```

### 4. HTTP/3 vs HTTP/2 vs HTTP/1.1

#### 4.1 HTTP 版本演进

```
HTTP 版本演进时间线：

1991 ─── HTTP/0.9 ─── 只支持 GET，无头部，纯文本
  │
1996 ─── HTTP/1.0 ─── 引入状态码、头部、Content-Type
  │                    每个请求一个 TCP 连接
  │
1997 ─── HTTP/1.1 ─── 持久连接（Keep-Alive）
  │                    管线化（Pipelining，但有队头阻塞）
  │                    Host 头部（虚拟主机）
  │                    分块传输（Chunked）
  │
2015 ─── HTTP/2 ───── 二进制分帧
  │                    多路复用（Multiplexing）
  │                    头部压缩（HPACK）
  │                    服务器推送（Server Push）
  │                    流优先级
  │
2022 ─── HTTP/3 ───── 基于 QUIC（UDP）
                       0-RTT 连接建立
                       Stream 级独立（无队头阻塞）
                       头部压缩（QPACK）
                       连接迁移
```

#### 4.2 HTTP 版本全面对比

| 特性 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|------|----------|--------|--------|
| 传输层 | TCP | TCP | QUIC (UDP) |
| 连接方式 | 持久连接 | 单连接多路复用 | 单连接多路复用 |
| 数据格式 | 文本 | 二进制分帧 | 二进制分帧 |
| 多路复用 | 不支持（管线化有队头阻塞） | 支持（但 TCP 层有队头阻塞） | 支持（Stream 级独立） |
| 头部压缩 | 无 | HPACK | QPACK |
| 服务器推送 | 不支持 | 支持 | 支持（但实践中很少用） |
| 首次连接延迟 | TCP(1) + 请求(1) = 2 RTT | TCP(1) + TLS(1) + 请求(1) = 3 RTT | QUIC(1) + 请求(0) = 1 RTT |
| 恢复连接延迟 | 1 RTT（复用连接） | 1 RTT | 0 RTT |
| 队头阻塞 | 严重 | TCP 层有 | 无 |
| 连接迁移 | 不支持 | 不支持 | 支持 |
| 服务端实现 | 所有 Web 服务器 | 大多数 Web 服务器 | Nginx 1.25+, Envoy, Caddy |
| 客户端支持 | 所有浏览器 | 所有现代浏览器 | Chrome, Firefox, Safari, Edge |

#### 4.3 头部压缩对比

```
HTTP/1.1: 无头部压缩
→ 每个请求都发送完整的头部
→ Cookie 可能有几百字节
→ 典型头部：~800 字节/请求
→ 100 个请求 = 80KB 纯头部开销

HTTP/2 (HPACK):
→ 使用静态表 + 动态表 + 霍夫曼编码
→ 静态表：61 个常见头部名/值对
→ 动态表：连接内学习新的头部
→ 典型头部：压缩后 ~100 字节/请求
→ 压缩率：约 85-90%

HPACK 的队头阻塞问题：
→ 动态表的更新依赖于前面的包
→ 如果一个包丢失，后续包的头部解码会被阻塞
→ 这是 HTTP/2 over TCP 的队头阻塞来源之一

HTTP/3 (QPACK):
→ 类似 HPACK，但解耦了编码和确认
→ 使用单向流（Uni-directional Stream）传递动态表更新
→ 编码器和解码器独立工作
→ 即使数据流丢包，也不会阻塞其他流的头部解码
→ 解决了 HPACK 的队头阻塞问题
```

#### 4.4 HTTP/2 Server Push 的教训

```
HTTP/2 Server Push 的设计初衷：
→ 服务器主动推送客户端可能需要的资源
→ 例如：推送 CSS/JS 文件，无需等待 HTML 解析后请求
→ 目标：减少 1 个 RTT 的等待

实践中的问题：
→ 无法准确知道客户端是否已缓存 → 可能浪费带宽
→ 推送的资源与客户端请求竞争带宽 → 可能更慢
→ 实现复杂，服务器配置困难
→ 浏览器支持不一致

结果：
→ Chrome 在 2022 年移除了 Server Push 支持
→ HTTP/3 保留了 Server Push 但很少使用
→ 替代方案：103 Early Hints（更优雅的预加载）

经验教训：
→ 协议设计应该基于实际需求，而非理论优化
→ 过度优化可能适得其反
→ 向后兼容性很重要
```

### 5. QUIC/HTTP3 的 SRE 运维要点

#### 5.1 部署注意事项

```
1. 防火墙放行 UDP 443
   ┌─────────────────────────────────────────────────────┐
   │ → 很多防火墙默认只放行 TCP 443                       │
   │ → QUIC 使用 UDP 443，必须显式放行                    │
   │ → 如果 UDP 443 被阻断，客户端自动回退到 HTTP/2       │
   │ → 检查：nc -u -zv <host> 443                        │
   │ → 云安全组、iptables、企业防火墙都需要配置           │
   └─────────────────────────────────────────────────────┘

2. 负载均衡器支持
   ┌─────────────────────────────────────────────────────┐
   │ → 传统 L4 LB 只处理 TCP                              │
   │ → QUIC 需要 UDP 负载均衡                             │
   │ → 支持 QUIC 的 LB:                                   │
   │   - Envoy (原生支持)                                  │
   │   - Nginx 1.25+ (实验性支持)                         │
   │   - Caddy (原生支持)                                  │
   │   - Cloudflare (全球部署)                             │
   │   - AWS ALB (支持 HTTP/3)                             │
   └─────────────────────────────────────────────────────┘

3. TLS 证书
   ┌─────────────────────────────────────────────────────┐
   │ → QUIC 内置 TLS 1.3，必须有有效的 TLS 证书           │
   │ → 证书配置与 HTTPS 相同                              │
   │ → 建议使用 ECDSA 证书（比 RSA 更快）                 │
   └─────────────────────────────────────────────────────┘

4. 性能考量
   ┌─────────────────────────────────────────────────────┐
   │ → 高延迟网络（跨地域/移动网络）：QUIC 优势明显       │
   │ → 低延迟网络（局域网/同机房）：差异不大              │
   │ → CPU 开销：QUIC 用户态实现，比内核 TCP 略高         │
   │ → 内存开销：每个 QUIC 连接需要更多内存               │
   │ → 建议：先在非关键路径测试，逐步推广                 │
   └─────────────────────────────────────────────────────┘
```

#### 5.2 监控和排障

```
QUIC 流量监控的挑战：
→ QUIC 头部加密 → 中间设备无法看到传输层信息
→ 传统 TCP 监控工具（如 tcpdump）只能看到 UDP 封装
→ 需要专用工具或密钥导出

抓包分析方法：
1. 使用支持 QUIC 的 Wireshark（4.0+）
2. 设置 SSLKEYLOGFILE 环境变量导出密钥：
   export SSLKEYLOGFILE=/tmp/sslkeys.log
   curl --http3-only https://example.com
   wireshark -o "tls.keylog_file:/tmp/sslkeys.log" capture.pcap

3. tcpdump 捕获 UDP 443 流量：
   sudo tcpdump -i any 'udp port 443' -w /tmp/quic.pcap

关键监控指标：
→ QUIC 连接数
→ 0-RTT 连接比例
→ 连接迁移次数
→ Stream 级丢包率
→ 握手延迟（1-RTT vs 0-RTT）
→ 回退到 HTTP/2 的比例（说明 UDP 被阻断）
```

#### 5.3 Nginx 配置 HTTP/3

```nginx
# Nginx 1.25+ 支持 HTTP/3（实验性）

server {
    listen 443 ssl;           # TCP 443 (HTTP/2)
    listen 443 quic reuseport; # UDP 443 (HTTP/3)

    server_name example.com;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # 告知客户端支持 HTTP/3
    add_header Alt-Svc 'h3=":443"; ma=86400';

    # HTTP/3 需要 TLS 1.3
    ssl_protocols TLSv1.3;

    location / {
        root /var/www/html;
        index index.html;
    }
}

# 注意：
# 1. listen 443 quic 需要 Nginx 1.25+
# 2. reuseport 允许多个 worker 共享 UDP 端口
# 3. Alt-Svc 头部告知浏览器可以使用 HTTP/3
# 4. 浏览器首次访问仍使用 HTTP/2，后续自动升级
```

#### 5.4 curl 测试 HTTP/3

```bash
# 检查 curl 是否支持 HTTP/3
curl --version | grep -i quic
# 如果输出中有 HTTP3/QUIC → 支持
# 如果没有 → 需要编译支持 HTTP/3 的版本

# 使用 curl 测试 HTTP/3
curl --http3-only https://cloudflare.com -o /dev/null -w "
  HTTP版本: %{http_version}
  连接时间: %{time_connect}s
  TLS时间: %{time_appconnect}s
  首字节时间: %{time_starttransfer}s
  总时间: %{time_total}s
"

# 对比 HTTP/2
curl --http2 https://cloudflare.com -o /dev/null -w "
  HTTP版本: %{http_version}
  连接时间: %{time_connect}s
  TLS时间: %{time_appconnect}s
  首字节时间: %{time_starttransfer}s
  总时间: %{time_total}s
"

# 强制回退测试（模拟 UDP 被阻断）
# 使用 iptables 阻止 UDP 443，观察自动回退
sudo iptables -A OUTPUT -p udp --dport 443 -j DROP
curl --http3 https://cloudflare.com -v 2>&1 | grep -i "http\|quic\|fallback"
# 应该看到回退到 HTTP/2
sudo iptables -D OUTPUT -p udp --dport 443 -j DROP
```

### 6. UDP 在 SRE 中的其他应用

#### 6.1 NTP 时间同步

```
NTP（Network Time Protocol）基于 UDP 123 端口：

时间同步原理：
Client                          NTP Server
  │  NTP Request (T1) ────────>  │
  │  NTP Response (T2, T3) <─── │
  │  (T4 = 收到响应的时间)        │

延迟 = (T4 - T1) - (T3 - T2)
偏移 = ((T2 - T1) + (T3 - T4)) / 2

SRE 关注点：
→ 时间不同步会导致：
  - TLS 证书验证失败
  - 日志时间戳混乱
  - 分布式系统一致性问题
  - Kerberos 认证失败

→ 配置多个 NTP 服务器（至少 3 个）
→ 使用 chrony 替代 ntpd（更快收敛）
```

```bash
# 查看 NTP 同步状态
chronyc tracking
# System time: 0.000001234 seconds fast of NTP time

# 查看 NTP 源
chronyc sources -v

# 强制同步
chronyc makestep
```

#### 6.2 DHCP

```
DHCP（Dynamic Host Configuration Protocol）基于 UDP 67/68：

DHCP 四步交互（DORA）：
Client                          DHCP Server
  │  Discover (广播, UDP 68→67)  │
  │ ──────────────────────────> │
  │                              │
  │  Offer (单播/广播)           │
  │ <────────────────────────── │
  │                              │
  │  Request (广播)              │
  │ ──────────────────────────> │
  │                              │
  │  ACK                         │
  │ <────────────────────────── │

为什么用 UDP：
→ 客户端还没有 IP 地址（刚接入网络）
→ TCP 需要 IP 地址才能建立连接
→ UDP 不需要预先的连接状态
→ 广播方式发送（Discover 使用 255.255.255.255）
```

#### 6.3 Syslog

```
Syslog 基于 UDP 514（传统）或 TCP 514/TLS 6514（增强）：

UDP Syslog 的特点：
→ 发送即忘（Fire and Forget）
→ 不影响业务性能
→ 允许少量日志丢失

TCP Syslog 的特点：
→ 可靠传输，日志不丢失
→ 可以用 TLS 加密
→ 有连接开销

SRE 建议：
→ 关键日志（审计、安全）→ TCP/TLS
→ 一般日志（调试、监控）→ UDP
→ 大规模场景 → 使用 Fluentd/Filebeat 替代 Syslog
```

---

## 💻 实战练习

### 练习 1：UDP vs TCP 延迟对比测试

```bash
#!/bin/bash
# udp-vs-tcp-test.sh - UDP vs TCP 性能对比

echo "=== UDP vs TCP 延迟对比 ==="

# 启动 UDP 监听
nc -ul -p 8888 > /dev/null 2>&1 &
UDP_PID=$!

# 启动 TCP 监听
nc -l -p 9999 > /dev/null 2>&1 &
TCP_PID=$!

sleep 1

# UDP 测试（100 次）
echo ""
echo "--- UDP 测试（100 次发送）---"
UDP_START=$(date +%s%N)
for i in $(seq 1 100); do
    echo "test_$i" | nc -u -w 1 127.0.0.1 8888 2>/dev/null
done
UDP_END=$(date +%s%N)
UDP_TIME=$(( (UDP_END - UDP_START) / 1000000 ))
echo "UDP 总耗时: ${UDP_TIME}ms"
echo "UDP 平均: $((UDP_TIME / 100))ms/次"

# TCP 测试（100 次连接建立）
echo ""
echo "--- TCP 测试（100 次连接建立）---"
TCP_START=$(date +%s%N)
for i in $(seq 1 100); do
    echo "test_$i" | nc -w 1 127.0.0.1 9999 2>/dev/null
done
TCP_END=$(date +%s%N)
TCP_TIME=$(( (TCP_END - TCP_START) / 1000000 ))
echo "TCP 总耗时: ${TCP_TIME}ms"
echo "TCP 平均: $((TCP_TIME / 100))ms/次"

echo ""
echo "延迟差异: $((TCP_TIME - UDP_TIME))ms"
echo "TCP 比 UDP 慢: $((TCP_TIME * 100 / UDP_TIME - 100))%"

# 清理
kill $UDP_PID $TCP_PID 2>/dev/null
```

### 练习 2：DNS 查询与协议分析

```bash
# 1. 基础 DNS 查询
dig example.com

# 2. 对比 UDP 和 TCP 查询延迟
echo "=== UDP 查询 ==="
dig +notcp +time=2 example.com | grep "Query time"

echo "=== TCP 查询 ==="
dig +tcp +time=2 example.com | grep "Query time"

# 3. 追踪完整解析链
dig +trace example.com

# 4. 使用 tcpdump 观察 DNS 流量
sudo tcpdump -i any -n 'port 53' -c 10 &
TCPDUMP_PID=$!
sleep 1
dig example.com
sleep 2
kill $TCPDUMP_PID 2>/dev/null

# 5. 查看 DNS 响应是否被截断
dig +bufsize=512 example.com | grep -i "flags"
# 如果看到 tc 标志 → 响应被截断

# 6. 测试不同 DNS 服务器
for dns in 8.8.8.8 1.1.1.1 114.114.114.114; do
    echo -n "$dns: "
    dig @$dns +time=2 example.com | grep "Query time"
done
```

### 练习 3：模拟 DNS 查询超时（UDP 53 被阻断）

```bash
# 模拟 UDP 53 被丢弃的场景

# 1. 先确认当前 DNS 正常
echo "=== 测试 1: 正常 DNS 查询 ==="
dig +short example.com
# 应该返回 IP 地址

# 2. 丢弃 UDP 53 出站
sudo iptables -A OUTPUT -p udp --dport 53 -j DROP

# 3. 测试 UDP DNS 查询（应该超时）
echo "=== 测试 2: UDP DNS 查询（被阻断）==="
timeout 5 dig +notcp example.com 2>&1 | grep -E "timed out|no servers|connection"

# 4. 测试 TCP DNS 查询（应该成功）
echo "=== 测试 3: TCP DNS 查询（回退）==="
dig +tcp example.com | grep -E "Query time|SERVER"

# 5. 清除规则
sudo iptables -D OUTPUT -p udp --dport 53 -j DROP

# 6. 验证恢复正常
echo "=== 测试 4: 恢复正常 ==="
dig +short example.com
```

### 练习 4：HTTP/3 测试

```bash
# 1. 检查 curl 是否支持 HTTP/3
echo "=== 检查 HTTP/3 支持 ==="
curl --version 2>&1 | head -3

# 2. 测试支持 HTTP/3 的网站
echo "=== 测试 Cloudflare（支持 HTTP/3）==="
curl --http3-only -sI https://cloudflare.com 2>&1 | head -5

# 3. 查看 HTTP 响应中的 Alt-Svc 头部
echo "=== 检查 Alt-Svc 头部 ==="
curl -sI https://cloudflare.com | grep -i alt-svc
# 应该看到：alt-svc: h3=":443"; ma=86400

# 4. 使用 nmap 检查 UDP 443
echo "=== 检查 UDP 443 端口 ==="
sudo nmap -sU -p 443 cloudflare.com 2>/dev/null | grep -A2 "443"

# 5. 使用 openssl 查看 TLS 版本（QUIC 强制 TLS 1.3）
echo "=== TLS 版本检查 ==="
echo | openssl s_client -connect cloudflare.com:443 -brief 2>&1 | grep -i "protocol"
```

### 练习 5：UDP 端口监控

```bash
# 1. 查看所有 UDP 监听端口
echo "=== UDP 监听端口 ==="
ss -uln

# 2. 查看 UDP 连接统计
echo "=== UDP 连接统计 ==="
ss -uan | wc -l
echo "活跃 UDP 连接数: $(ss -uan | wc -l)"

# 3. 查看 DNS 相关的 UDP 连接
echo "=== DNS UDP 连接 ==="
ss -uan | grep :53

# 4. 查看 UDP 相关内核参数
echo "=== UDP 内核参数 ==="
sysctl -a 2>/dev/null | grep udp

# 5. 使用 nc 测试 UDP 端口可达性
echo "=== UDP 端口测试 ==="
echo "test" | nc -u -w 2 8.8.8.8 53 && echo "UDP 53 可达"
```

---

## 🔍 SRE 实战案例

### 案例 1：DNS 查询超时 — UDP 53 被 NetworkPolicy 丢弃

**场景**：生产环境部分 Pod 突然出现 DNS 解析超时，服务间通信失败。

**排查过程**：

```
Step 1: 确认 DNS 解析失败
$ kubectl exec -it pod/service-a-xxx -- nslookup service-b.default
;; connection timed out; no servers could be reached

Step 2: 区分 UDP 和 TCP
$ kubectl exec -it pod/service-a-xxx -- dig @10.96.0.10 +tcp service-b.default
;; Query time: 2 msec  ← TCP 正常

$ kubectl exec -it pod/service-a-xxx -- dig @10.96.0.10 +notcp service-b.default
;; connection timed out  ← UDP 超时

Step 3: 定位 NetworkPolicy
$ kubectl get networkpolicy -n default -o yaml
→ 发现只允许了 TCP 53，没有 UDP 53

Step 4: 修复
→ 添加 UDP 53 的 egress 规则
→ 应用后验证
```

**经验教训**：
- NetworkPolicy 必须同时允许 TCP 和 UDP 53
- DNS 默认使用 UDP，UDP 被阻断后会回退到 TCP（但有 5 秒超时延迟）
- 部署 NetworkPolicy 后必须测试 DNS 解析

### 案例 2：视频卡顿排查 — UDP 丢包和 Jitter

**场景**：公司内部视频会议系统频繁卡顿。

**排查过程**：

```
Step 1: 确认是网络问题
→ 多个用户同时反馈卡顿
→ 不同地点、不同设备都有问题
→ 排除客户端问题

Step 2: 检查网络质量
$ mtr -r -c 100 video-server.example.com
→ 发现中间链路丢包率 5%

Step 3: 分析 UDP 丢包
$ tcpdump -i eth0 'udp port 3478' -c 1000 -w /tmp/video.pcap
→ 用 Wireshark 分析
→ 发现约 5% 的 UDP 包丢失

Step 4: 检查 Jitter
→ 视频流使用 RTP over UDP
→ Jitter（抖动）> 30ms 会导致卡顿
→ 通过 Wireshark 的 RTP 分析工具确认 Jitter 过大

Step 5: 根因
→ 中间路由器拥塞导致 UDP 丢包
→ UDP 没有拥塞控制，大量 UDP 流量加剧拥塞

Step 6: 解决方案
→ 联系网络团队优化路由
→ 启用 QoS 为视频流量设置优先级
→ 视频客户端启用 FEC（前向纠错）补偿丢包
→ 配置 Jitter Buffer 吸收抖动
```

### 案例 3：QUIC 部署和监控

**场景**：公司决定为 API 服务启用 HTTP/3，需要设计部署和监控方案。

**部署步骤**：

```
1. 防火墙配置
   → 放行 UDP 443（所有节点：LB、应用服务器）
   → 云安全组添加 UDP 443 入站规则
   → iptables 添加 UDP 443 放行规则

2. 负载均衡器配置
   → Envoy: 配置 UDP listener
   → 或使用支持 QUIC 的云 LB（AWS ALB）

3. 应用服务器配置（Nginx 示例）
   → listen 443 quic reuseport
   → ssl_protocols TLSv1.3
   → add_header Alt-Svc 'h3=":443"; ma=86400'

4. 灰度发布
   → 先在 10% 的流量上启用
   → 监控指标无异常后逐步扩大

监控指标：
→ http3_connections_total: HTTP/3 连接数
→ http3_0rtt_ratio: 0-RTT 连接比例
→ http3_fallback_total: 回退到 HTTP/2 的次数
→ http3_stream_errors_total: Stream 级错误
→ quic_handshake_duration_seconds: 握手延迟
```

### 案例 4：UDP 反射攻击防护

**场景**：公司 DNS 服务器被用作反射攻击的放大器。

```
攻击原理：
攻击者 → 伪造受害者 IP → 发送 DNS 查询（小请求）
DNS 服务器 → 向受害者 IP 发送 DNS 响应（大响应）
→ 放大倍数 28-54 倍
→ 受害者被大量 DNS 响应淹没

防御措施：
1. 限制递归查询范围
   → 只允许内部 IP 发起递归查询
   → 外部 IP 只能查询本服务器权威的域名

2. 响应速率限制
   → 实施 DNS Response Rate Limiting (RRL)
   → 同一源 IP 的查询频率限制

3. 源地址验证（BCP38）
   → 在网络入口过滤伪造的源 IP
   → 确保出站流量的源 IP 是合法的

4. 监控告警
   → 监控 DNS 查询量突增
   → 监控出站 UDP 流量异常
```

---

## 🎯 面试题精选

### Q1: TCP 和 UDP 的区别是什么？各自适合什么场景？

**参考答案**：

```
核心区别：
TCP 面向连接、可靠、有序、有流量/拥塞控制，头部 20-60 字节。
UDP 无连接、不可靠、无序、无流量/拥塞控制，头部仅 8 字节。

TCP 适合：需要可靠传输的场景（HTTP、文件传输、数据库、邮件、SSH）
UDP 适合：延迟敏感或容忍丢包的场景（DNS、视频流、游戏、NTP、DHCP）

选择原则：
→ 要求数据完整不丢失 → TCP
→ 要求低延迟，可容忍丢包 → UDP
→ 请求-响应模式，数据量小 → UDP（如 DNS）
→ 大量数据传输 → TCP
→ 实时音视频 → UDP（应用层自己处理可靠性）
```

### Q2: QUIC 协议相比 TCP 有什么优势？

**参考答案**：

```
1. 更快的连接建立：首次 1 RTT vs TCP+TLS 的 2 RTT，恢复连接 0 RTT
2. 消除队头阻塞：Stream 级独立可靠传输，丢包只影响单个流
3. 连接迁移：基于 Connection ID 而非四元组，WiFi/4G 切换不断连
4. 内置加密：TLS 1.3 不可分割，所有数据（含头部）都加密
5. 用户态实现：协议迭代快，不需要升级内核
6. 灵活的拥塞控制：可以在应用层自定义和快速更新算法
```

### Q3: HTTP/3 解决了 HTTP/2 的什么问题？

**参考答案**：

```
HTTP/3 解决的核心问题是 TCP 层的队头阻塞：
→ HTTP/2 虽然支持多路复用，但底层 TCP 是字节流
→ 一个 TCP 包丢失会阻塞所有 HTTP 流
→ HTTP/3 基于 QUIC（UDP），每个流独立可靠传输
→ 丢包只影响单个流，其他流不受影响

其他改进：
→ 0-RTT 连接建立（HTTP/2 需要 TCP+TLS = 2 RTT）
→ 连接迁移支持（HTTP/2 连接在 IP 变化时断开）
→ QPACK 头部压缩解决 HPACK 的队头阻塞
```

### Q4: DNS 使用 UDP 还是 TCP？什么时候会切换？

**参考答案**：

```
DNS 默认使用 UDP 53（快速、无连接开销）。

切换到 TCP 53 的条件：
1. 响应超过 512 字节（或 EDNS0 的限制），TC 标志位被设置
2. 区域传输（AXFR/IXFR），需要传输大量数据
3. DNSSEC 查询，签名使响应变大
4. 动态更新，需要可靠性保证
5. 客户端显式使用 dig +tcp

UDP 被阻断时的回退：
→ DNS 客户端发 UDP 53 超时后（默认 5 秒）
→ 部分实现会自动回退到 TCP 53
→ 但回退延迟很长（5 秒超时 + TCP 握手）
→ SRE 场景：Kubernetes NetworkPolicy 忘记放行 UDP 53
```

### Q5: QUIC 的 0-RTT 有什么安全风险？

**参考答案**：

```
0-RTT 数据可能被重放攻击（Replay Attack）：
→ 攻击者截获客户端的 0-RTT 数据包
→ 将同样的数据包重新发送给服务器
→ 服务器无法区分是新请求还是重放
→ 如果 0-RTT 数据是非幂等操作（如扣款），会造成问题

防御措施：
1. 服务器只对幂等请求接受 0-RTT（如 GET）
2. 使用Strike Register 或时间窗口防止重放
3. 在应用层实现幂等性（幂等 Key）
4. 对敏感操作不使用 0-RTT
```

### Q6: 为什么视频流使用 UDP 而不是 TCP？

**参考答案**：

```
1. 延迟敏感：视频需要实时播放，TCP 重传引入的延迟（200ms+）不可接受
2. 旧数据无价值：过期的视频帧不如丢弃，用户感知不到少量丢包
3. TCP 重传风暴：网络抖动时 TCP 重传会加剧拥塞
4. 应用层自定义：视频协议（如 RTP）自己处理排序和抖动缓冲
5. Jitter Buffer：播放端用缓冲区吸收网络抖动，比 TCP 重传更高效
6. FEC 前向纠错：通过冗余数据恢复丢包，比等待重传更快
```

### Q7: QUIC 的连接迁移是如何实现的？

**参考答案**：

```
QUIC 使用 Connection ID（CID）标识连接，而非 TCP 的四元组：
→ CID 在连接建立时协商，与 IP 地址无关
→ IP 变化时（如 WiFi→4G），CID 不变，连接保持
→ 客户端通过 PATH_CHALLENGE 探测新路径
→ 服务器回复 PATH_RESPONSE 确认新路径
→ 后续数据通过新路径传输

对比 TCP：
→ TCP 连接由 (源IP, 源端口, 目的IP, 目的端口) 标识
→ IP 变化 → 四元组变化 → 连接断开
→ 需要重新三次握手 + TLS 握手

实际效果：
→ 手机从 WiFi 切换到 4G，TCP 连接断开 2-3 秒
→ QUIC 连接无缝继续，用户几乎无感知
```

### Q8: SRE 如何监控和排查 QUIC/HTTP/3 问题？

**参考答案**：

```
监控：
→ HTTP/3 连接数和比例
→ 0-RTT 连接比例（衡量缓存效果）
→ 回退到 HTTP/2 的比例（说明 UDP 被阻断）
→ Stream 级错误率
→ 握手延迟分布

排障工具：
→ tcpdump 抓取 UDP 443 流量
→ Wireshark 4.0+ 支持 QUIC 解析
→ 设置 SSLKEYLOGFILE 导出 TLS 密钥解密流量
→ curl --http3 测试 HTTP/3 连通性
→ nmap -sU -p 443 检查 UDP 端口状态

常见问题：
→ UDP 443 被防火墙阻断 → 检查安全组和 iptables
→ 负载均衡器不支持 UDP → 升级或更换 LB
→ 证书问题 → 确保 TLS 1.3 和有效证书
→ 性能不升反降 → 检查 CPU 开销，可能是用户态实现的开销
```

### Q9: HTTP Keep-Alive 和 QUIC 的多路复用有什么区别？

**参考答案**：

```
HTTP/1.1 Keep-Alive：
→ 复用 TCP 连接发送多个请求
→ 但必须串行处理（管线化有队头阻塞）
→ 浏览器通常对同一域名开 6-8 个 TCP 连接

HTTP/2 多路复用：
→ 单个 TCP 连接上并行发送多个请求/响应
→ 用 Stream ID 区分不同的请求
→ 但 TCP 层有队头阻塞

QUIC 多路复用：
→ 类似 HTTP/2，但基于 UDP
→ 每个 Stream 独立可靠传输
→ 没有 TCP 层队头阻塞
→ 真正的并行无干扰传输

关键区别：
→ HTTP/1.1: 串行（一个完成才能发下一个）
→ HTTP/2: 伪并行（TCP 丢包影响所有流）
→ HTTP/3: 真并行（丢包只影响单个流）
```

### Q10: 为什么 QUIC 选择基于 UDP 而不是直接修改 TCP？

**参考答案**：

```
1. TCP 在内核中实现，修改需要升级操作系统
→ 全球数十亿设备的内核升级周期以年计
→ UDP 是用户态可编程的，应用程序可以自带协议栈

2. 中间设备（NAT、防火墙）对 TCP 有深度包检测
→ 新的 TCP 选项可能被中间设备丢弃
→ UDP 相对"透明"，中间设备通常不深度解析

3. 部署速度
→ TCP 新特性需要 OS 厂商、云服务商、用户三方升级
→ QUIC 更新 = 更新应用（Chrome、curl 等）
→ 可以在几个月内覆盖数亿用户

4. 协议僵化（Protocol Ossification）
→ TCP 的设计已经固化在网络设备的固件中
→ 任何修改都可能被中间设备破坏
→ UDP 提供了一个"干净的画布"

5. 向后兼容
→ 如果 UDP 443 被阻断，自动回退到 TCP/TLS
→ 不会破坏现有基础设施
```

---

## 📚 深入阅读

### 官方文档与 RFC
- [RFC 768 - User Datagram Protocol](https://datatracker.ietf.org/doc/html/rfc768) — UDP 协议规范
- [RFC 9000 - QUIC: A UDP-Based Multiplexed and Secure Transport](https://datatracker.ietf.org/doc/html/rfc9000) — QUIC 核心规范
- [RFC 9114 - HTTP/3](https://datatracker.ietf.org/doc/html/rfc9114) — HTTP/3 规范
- [RFC 1035 - Domain Names](https://datatracker.ietf.org/doc/html/rfc1035) — DNS 协议规范
- [RFC 7858 - DNS over TLS](https://datatracker.ietf.org/doc/html/rfc7858) — DNS over TLS
- [RFC 8484 - DNS over HTTPS](https://datatracker.ietf.org/doc/html/rfc8484) — DNS over HTTPS

### 推荐资源
- [HTTP/3 Explained](https://http3-explained.haxx.se/) — curl 作者 Daniel Stenberg 的 HTTP/3 详解
- [QUIC Working Group](https://quicwg.org/) — QUIC 官方工作组
- [Cloudflare - What is QUIC?](https://www.cloudflare.com/learning/performance/what-is-quic/) — QUIC 入门
- [Google QUIC](https://www.chromium.org/quic/) — Google 的 QUIC 项目页面
- [QUIC-Go](https://github.com/quic-go/quic-go) — Go 语言的 QUIC 实现

### 视频资源
- [YouTube - QUIC Protocol Explained](https://www.youtube.com/watch?v=xhRRpD8j5hY) — 可视化讲解
- [Bilibili - HTTP/3 与 QUIC 详解](https://www.bilibili.com/video/BV1Xv4y1U7jG/) — 中文深度讲解
- [YouTube - HTTP/3 Deep Dive](https://www.youtube.com/watch?v=0WgOJrU3pQ8) — 深入技术分析

---

## ✅ 自检清单

### 理论检查点
- [ ] 理解 UDP 的特点：无连接、不可靠、轻量、有消息边界
- [ ] 能解释 UDP 和 TCP 的区别及各自的适用场景
- [ ] 理解 DNS 基于 UDP 的工作原理和 TCP 回退机制
- [ ] 理解 QUIC 的四大核心特性：0-RTT、多路复用、连接迁移、内置 TLS 1.3
- [ ] 能对比 HTTP/1.1、HTTP/2、HTTP/3 的区别
- [ ] 理解 QUIC 解决了 TCP 的哪些问题（队头阻塞、连接建立延迟、连接迁移）
- [ ] 理解 0-RTT 的安全风险（重放攻击）
- [ ] 理解 UDP 反射攻击的原理和防御

### 实操检查点
- [ ] 能使用 dig 命令进行 DNS 查询和排障
- [ ] 能使用 nc 测试 UDP 端口连通性
- [ ] 能使用 tcpdump 抓取 UDP/DNS 流量
- [ ] 能模拟 UDP 53 被阻断的场景并验证 TCP 回退
- [ ] 能配置 Nginx 支持 HTTP/3
- [ ] 能使用 curl 测试 HTTP/3
- [ ] 完成了全部 5 个实战练习和 4 个实战案例

---

*由 SRE 学习计划生成 | 2026-05-01*
