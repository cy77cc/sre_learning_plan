# Day 31: UDP 协议、QUIC（HTTP/3）

> 📅 日期：2026-05-01
> 📖 学习主题：UDP 协议、QUIC（HTTP/3）
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 31 的学习后，你应该掌握：
- 理解 UDP 协议的核心特性、适用场景和局限性
- 掌握 DNS 协议基于 UDP 的工作原理及 TCP 回退机制
- 理解 QUIC 协议的设计动机、核心特性和相对于 TCP+TLS 的优势
- 掌握 HTTP/3 与 HTTP/1.1、HTTP/2 的区别
- 能够在 SRE 实战中诊断 UDP 相关问题
- 能够使用 netcat 等工具进行 UDP 测试

---

## 📖 详细知识点

### 1. UDP 协议详解

#### 1.1 UDP 概述

UDP（User Datagram Protocol，用户数据报协议）是传输层的另一种核心协议，与 TCP 并列。相比 TCP 的复杂和可靠，UDP 以简单和低延迟著称。

| 特性 | TCP | UDP | SRE 关注差异 |
|------|-----|-----|-------------|
| 连接方式 | 面向连接（三次握手） | 无连接 | UDP 无需握手，延迟更低 |
| 可靠性 | 可靠（ACK + 重传） | 不可靠（不保证到达） | UDP 丢包不重传 |
| 顺序保证 | 有序 | 无序 | UDP 包可能乱序到达 |
| 流量控制 | 滑动窗口 | 无 | UDP 可能打满带宽 |
| 拥塞控制 | 有 | 无 | UDP 不会自动降速 |
| 头部大小 | 20-60 字节 | 8 字节 | UDP 开销更小 |
| 传输模式 | 字节流 | 数据报（有消息边界） | UDP 天然避免粘包 |
| 典型应用 | HTTP、SSH、FTP | DNS、DHCP、NTP、视频流 | 各自适合不同场景 |

#### 1.2 UDP 头部格式

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          源端口 (16)           |        目的端口 (16)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           长度 (16)           |          校验和 (16)            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           数据（Payload）                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

UDP 头部总计：8 字节（固定）
```

**UDP 头部字段说明**：

| 字段 | 大小 | 说明 |
|------|------|------|
| 源端口 | 16 位 | 发送方端口（可选，可为 0） |
| 目的端口 | 16 位 | 接收方端口 |
| 长度 | 16 位 | UDP 头部 + 数据的总长度（最小 8 字节） |
| 校验和 | 16 位 | 可选（IPv4 中），IPv6 强制要求 |

#### 1.3 UDP 的适用场景

| 场景 | 原因 | 典型协议 |
|------|------|----------|
| DNS 查询 | 请求/响应小，延迟敏感 | DNS (UDP 53) |
| 实时音视频 | 容忍少量丢包，不能容忍延迟 | RTP, WebRTC |
| 游戏 | 状态频繁更新，旧数据无价值 | 游戏自定义协议 |
| DHCP | 获取 IP 前没有 TCP 连接 | DHCP (UDP 67/68) |
| NTP 时间同步 | 定时发送小数据包 | NTP (UDP 123) |
| SNMP 监控 | 轮询式小数据包 | SNMP (UDP 161/162) |
| Syslog 日志 | 允许少量日志丢失 | Syslog (UDP 514) |
| QUIC/HTTP3 | 在 UDP 上实现可靠传输 | QUIC (UDP 443) |

#### 1.4 UDP 的局限性与风险

```
风险 1：无拥塞控制
→ UDP 不会感知网络拥塞
→ 大量 UDP 流量可能打满带宽
→ 影响同链路的其他 TCP 连接
→ SRE 场景：UDP 监控流量突增导致网络拥塞

风险 2：无可靠性保证
→ 数据包可能丢失、重复、乱序
→ 应用层需要自行处理
→ DNS 等简单场景没问题，复杂场景需要额外机制

风险 3：容易被滥用
→ UDP 反射攻击（DNS amplification、NTP amplification）
→ 攻击者伪造源 IP 发送小请求，获得大响应
→ 放大倍数可达 50-100 倍
→ SRE 防护：BCP38（源地址验证）、rate limiting

风险 4：防火墙/NAT 穿透
→ UDP 无连接状态，NAT 需要特殊处理
→ NAT 映射超时短（通常 30-180 秒）
→ 需要 keepalive 保活
```

### 2. DNS 协议与 UDP/TCP

#### 2.1 DNS 协议概述

DNS（Domain Name System，域名系统）是互联网的基础设施，负责将人类可读的域名转换为机器可用的 IP 地址。

```
DNS 查询完整流程：
用户输入: www.example.com

1. 浏览器缓存检查 → 无
2. 操作系统缓存检查 (DNS Cache) → 无
3. 向本地 DNS 服务器（通常由 ISP 或 DHCP 分配）发送查询
   → UDP 53 端口
   → 本地 DNS 检查缓存 → 无
4. 本地 DNS 向根服务器查询（13 组根服务器）
   → 返回 .com TLD 服务器地址
5. 本地 DNS 向 .com TLD 服务器查询
   → 返回 example.com 的权威 DNS 服务器地址
6. 本地 DNS 向权威 DNS 服务器查询
   → 返回 www.example.com 的 A 记录 (93.184.216.34)
7. 本地 DNS 缓存结果，返回给客户端
8. 客户端缓存结果

后续相同域名查询直接使用缓存（TTL 内有效）
```

#### 2.2 DNS 使用 UDP 还是 TCP？

| 场景 | 传输协议 | 原因 |
|------|----------|------|
| 标准查询/响应 | UDP 53 | 响应通常 < 512 字节，UDP 更快 |
| 响应超过 512 字节 | TCP 53 | 使用 EDNS0 扩展后 UDP 可更大，但超大响应用 TCP |
| 区域传输（AXFR/IXFR） | TCP 53 | 传输大量 DNS 记录，需要可靠传输 |
| DNSSEC 验证 | UDP/TCP 53 | DNSSEC 签名使响应变大，可能触发 TCP |
| 动态更新 | TCP 53 | 需要可靠性保证 |

```
DNS 协议切换机制：

客户端 → 本地 DNS（UDP 53）
    ↓
本地 DNS 收到响应，检查 TC（Truncated）标志位
    ↓
TC=1：响应被截断（超过 UDP 限制）
    → 客户端改用 TCP 53 重新查询
    ↓
TC=0：响应完整
    → 使用 UDP 返回的结果
```

#### 2.3 DNS 记录类型

| 记录类型 | 说明 | 示例 |
|----------|------|------|
| A | IPv4 地址 | example.com → 93.184.216.34 |
| AAAA | IPv6 地址 | example.com → 2606:2800:220:1:248:1893:25c8:1946 |
| CNAME | 别名 | www.example.com → example.com |
| MX | 邮件服务器 | example.com → mail.example.com (优先级 10) |
| NS | 域名服务器 | example.com → ns1.example.com |
| TXT | 文本记录 | SPF、DKIM、域名验证 |
| SRV | 服务定位 | _sip._tcp.example.com → 服务器地址 |
| SOA | 起始授权 | 区域管理信息 |
| PTR | 反向解析 | IP → 域名 |

#### 2.4 DNS 查询命令

```bash
# 基础查询
dig example.com
# 输出关键信息：
# ;; QUESTION SECTION:
# ;example.com.                   IN      A
#
# ;; ANSWER SECTION:
# example.com.            3600    IN      A       93.184.216.34
#                         ↑ TTL（秒）    ↑ 记录类型  ↑ IP 地址

# 指定记录类型
dig example.com AAAA          # IPv6 地址
dig example.com MX            # 邮件服务器
dig example.com TXT           # 文本记录
dig example.com NS            # 域名服务器

# 指定 DNS 服务器
dig @8.8.8.8 example.com      # 使用 Google DNS
dig @1.1.1.1 example.com      # 使用 Cloudflare DNS

# 追踪完整解析链路
dig +trace example.com
# 从根服务器开始，逐级查询

# 查看查询使用的协议和耗时
dig +time=5 example.com
# ;; Query time: 23 msec
# ;; SERVER: 192.168.1.1#53(192.168.1.1)

# 使用 nslookup（较老，但某些环境仍需要）
nslookup example.com

# 使用 host（简洁输出）
host example.com
```

#### 2.5 DNS 缓存与 TTL

```bash
# 查看本地 DNS 缓存（systemd-resolved）
resolvectl statistics
# 或
sudo systemd-resolve --statistics

# 清除本地 DNS 缓存
sudo systemctl restart systemd-resolved
# macOS: sudo killall -HUP mDNSResponder

# 查看 /etc/resolv.conf 中的 DNS 配置
cat /etc/resolv.conf
# nameserver 192.168.1.1
# nameserver 8.8.8.8

# DNS 缓存生命周期
# TTL = Time To Live（生存时间）
# TTL=300 → 缓存 5 分钟
# TTL=86400 → 缓存 24 小时
# TTL=0 → 不缓存
```

### 3. QUIC 协议详解

#### 3.1 为什么需要 QUIC？

**TCP + TLS 的问题**：

```
传统 HTTPS（TCP + TLS）的连接建立过程：

客户端                              服务器
  │                                    │
  │  ──── TCP 三次握手 (1 RTT) ────→   │
  │  SYN →                            │
  │       ← SYN-ACK                   │
  │  ACK →                            │
  │                                    │
  │  ──── TLS 握手 (1-2 RTT) ────→    │
  │  ClientHello →                    │
  │       ← ServerHello + Cert        │
  │  Finished →                       │
  │       ← Finished                  │
  │                                    │
  │  ──── 终于开始传输数据 ────→       │

总延迟：2-3 个 RTT 才能开始传输数据！

如果使用 TLS 1.3 + TCP：
→ 最快也需要 1 RTT（TLS 1.3 优化后）
→ 加上 TCP 三次握手 = 2 RTT

如果使用 0-RTT 恢复：
→ TLS 1.3 支持 0-RTT 恢复
→ 但 TCP 三次握手仍然存在 = 1 RTT

此外还有队头阻塞（Head-of-Line Blocking）问题：
→ TCP 是字节流，一个包丢失会影响后续所有数据
→ HTTP/2 的多路复用建立在 TCP 之上
→ 一个流丢包 → 所有流都被阻塞
```

#### 3.2 QUIC 的核心设计

```
QUIC = Quick UDP Internet Connections
设计目标：
1. 减少连接建立延迟
2. 消除队头阻塞
3. 改善连接迁移
4. 内置加密（TLS 1.3 不可分割）

QUIC 在 UDP 上实现了可靠传输 + 加密：

┌──────────────────────────────────────────┐
│            HTTP/3                        │  ← 应用层
├──────────────────────────────────────────┤
│            QUIC                          │  ← 传输层（用户态）
│  • 可靠传输（基于 UDP）                   │
│  • 多路复用（Streams）                    │
│  • 内置 TLS 1.3 加密                     │
│  • 连接迁移（Connection ID）              │
├──────────────────────────────────────────┤
│            UDP                           │  ← 不可靠传输
├──────────────────────────────────────────┤
│            IP                            │  ← 网络层
└──────────────────────────────────────────┘
```

#### 3.3 QUIC vs TCP+TLS 对比

| 特性 | TCP + TLS 1.3 | QUIC (HTTP/3) | 优势 |
|------|---------------|---------------|------|
| 首次连接 | 2 RTT（TCP 1 + TLS 1） | 1 RTT | 减少 50% |
| 连接恢复 | 1 RTT（TCP + TLS 0-RTT） | 0 RTT | 减少 100% |
| 队头阻塞 | 有（TCP 层） | 无（Stream 级） | 多路复用更彻底 |
| 加密 | TLS 在 TCP 之上 | TLS 内置在 QUIC 中 | 更安全，更少 RTT |
| 连接迁移 | 不自然（基于四元组） | 原生支持（Connection ID） | 网络切换不断连 |
| 拥塞控制 | 内核态（Cubic/BBR） | 用户态（可自定义） | 灵活部署新算法 |
| 部署难度 | 中间件可能干扰 | UDP 443 可能被阻断 | 需要防火墙放行 |
| 中间件可见性 | 中间件可看到 TCP 层 | 中间件只能看到 UDP 封装 | 隐私更好，但排障更难 |

#### 3.4 QUIC 连接建立过程

```
客户端                              服务器
  │                                    │
  │  Initial + Handshake (1 RTT)      │
  │  (包含 ClientHello + 早期数据)     │
  │ ─────────────────────────────────> │
  │                                    │
  │  Handshake + 1-RTT Keys           │
  │ <──────────────────────────────── │
  │                                    │
  │  开始传输应用数据                  │
  │ ─────────────────────────────────> │
  │ <──────────────────────────────── │

对比 TCP+TLS：
TCP 三次握手 (1 RTT) + TLS 1.3 (1 RTT) = 2 RTT
QUIC 首次连接 = 1 RTT（合并了传输层和加密层握手）

QUIC 0-RTT（连接恢复）：
→ 客户端缓存了上次连接的会话信息
→ 在第一个包中就携带加密的早期数据
→ 服务器验证后直接处理，无需等待
→ 从客户端角度看 = 0 RTT
→ ⚠️ 注意：0-RTT 数据可能被重放攻击，需谨慎使用
```

#### 3.5 QUIC 的多路复用与队头阻塞

```
TCP + HTTP/2 的队头阻塞：

TCP Stream: [Stream1_Pkt1] [Stream2_Pkt1] [Stream1_Pkt2*] [Stream2_Pkt2] [Stream1_Pkt3]
                                                                 ↑ 这个包丢失
→ TCP 需要等待 Pkt2 重传成功
→ Pkt2 之后的所有包都不能交付
→ Stream1 和 Stream2 都被阻塞！

QUIC (HTTP/3) 的多路复用：

QUIC Stream 1: [Pkt1] [Pkt2*] [Pkt3]
                              ↑ 这个包丢失，只影响 Stream 1
QUIC Stream 2: [Pkt1] [Pkt2] [Pkt3] [Pkt4]  ← 不受影响，正常处理
QUIC Stream 3: [Pkt1] [Pkt2] [Pkt3]           ← 不受影响，正常处理

→ 每个 Stream 独立可靠传输
→ Stream 2 和 3 可以继续处理
→ 只有 Stream 1 被阻塞
```

#### 3.6 QUIC 连接迁移

```
场景：手机从 WiFi 切换到 4G

TCP：
- 连接由四元组标识：(源IP, 源端口, 目的IP, 目的端口)
- IP 地址变化 → 四元组变化 → 连接断开
- 需要重新建立连接

QUIC：
- 连接由 Connection ID（CID）标识，与 IP 无关
- IP 地址变化 → CID 不变 → 连接保持
- 只需更新 NAT 映射，无需重新握手

实现：
- 客户端发送 PATH_CHALLENGE 探测新路径
- 服务器回复 PATH_RESPONSE 确认
- 后续数据通过新路径传输
```

#### 3.7 QUIC 的 SRE 运维要点

```
部署注意事项：
1. 防火墙必须放行 UDP 443
   → 很多防火墙默认只放行 TCP 443
   → QUIC 会被阻止 → 回退到 HTTP/2

2. 负载均衡器需要支持 QUIC
   → 传统 LB 只处理 TCP
   → 需要支持 UDP 的 LB（如 Envoy、Nginx 1.25+）

3. 监控工具需要更新
   → tcpdump/ Wireshark 需要更新到支持 QUIC 的版本
   → 加密的 QUIC 流量无法直接解析
   → 需要导出密钥文件（SSLKEYLOGFILE）

4. 性能对比
   → 高延迟网络：QUIC 优势明显
   → 局域网/低延迟网络：差异不大
   → CPU 开销：QUIC 在用户态实现，CPU 开销略高
```

### 4. HTTP/3 与 HTTP 演进

#### 4.1 HTTP 版本对比

| 版本 | 传输层 | 年份 | 核心特性 | 性能瓶颈 |
|------|--------|------|----------|----------|
| HTTP/0.9 | TCP | 1991 | 仅 GET，无头部 | 功能极其有限 |
| HTTP/1.0 | TCP | 1996 | 方法、状态码、头部 | 每个请求一个新连接 |
| HTTP/1.1 | TCP | 1997 | 持久连接、管线化 | 队头阻塞、连接数限制 |
| HTTP/2 | TCP | 2015 | 多路复用、头部压缩、Server Push | TCP 层队头阻塞 |
| HTTP/3 | QUIC (UDP) | 2022 | 0-RTT、Stream 级独立、连接迁移 | UDP 可能被阻断 |

#### 4.2 头部压缩对比

| 特性 | HTTP/1.1 | HTTP/2 (HPACK) | HTTP/3 (QPACK) |
|------|----------|----------------|----------------|
| 压缩方式 | 无（Gzip 压缩 body） | 动态表 + 霍夫曼编码 | 动态表 + 无阻塞编码 |
| 典型头部大小 | ~800 字节 | ~100 字节 | ~100 字节 |
| 队头阻塞 | N/A | 有（动态表依赖） | 无（解耦编码和确认） |

### 5. UDP 与 TCP 延迟对比

#### 5.1 延迟构成分析

```
TCP 连接延迟：
┌─────────────────────────────────────────────┐
│ TCP 三次握手:     1 RTT                     │
│ TLS 1.2 握手:     2 RTT                     │
│ TLS 1.3 握手:     1 RTT                     │
│ 首次数据传输:     额外延迟                   │
│ 总计 (TLS 1.3):   2 RTT                     │
└─────────────────────────────────────────────┘

UDP 连接延迟（无连接）：
┌─────────────────────────────────────────────┐
│ 无握手:           0 RTT                     │
│ QUIC 首次连接:    1 RTT                     │
│ QUIC 0-RTT:       0 RTT                     │
│ DNS 查询 (UDP):   ~1 RTT                    │
└─────────────────────────────────────────────┘

实际延迟 = RTT + 处理时间 + 排队时间
```

#### 5.2 延迟测试方法

```bash
# 测试 RTT（ping 是最简单的方式）
ping -c 10 google.com
# PING google.com (142.250.4.100): 56 data bytes
# 64 bytes from 142.250.4.100: icmp_seq=0 ttl=117 time=23.456 ms
# --- google.com ping statistics ---
# 10 packets transmitted, 10 packets received, 0.0% packet loss
# round-trip min/avg/max/stddev = 22.1/23.5/25.8/1.2 ms

# 测试 TCP 连接建立时间
time (echo > /dev/tcp/google.com/443) 2>&1
# 或使用 nmap
nmap -p 443 --script ssl-enum-ciphers google.com

# 测试 DNS 查询延迟（UDP）
dig +time=1 google.com | grep "Query time"
# ;; Query time: 23 msec

# 使用 hping3 测试 TCP 握手延迟
sudo hping3 -S -p 443 -c 10 google.com
# 查看 RTT 统计
```

---

## 🛠️ 实战练习

### 练习 1：用 netcat 发送 UDP 数据包，对比 TCP 延迟

```bash
# 安装 netcat
sudo apt-get install ncat -y  # 或 netcat-openbsd

# --- UDP 测试 ---

# 终端 1：启动 UDP 服务器
nc -ul -p 8888
# -u: UDP 模式
# -l: 监听
# -p 8888: 端口

# 终端 2：发送 UDP 数据包
nc -u -w 1 127.0.0.1 8888
# 输入消息，回车发送
# -w 1: 超时 1 秒
# 注意：UDP 不需要建立连接，发送即完成

# 性能对比测试脚本
#!/bin/bash
# udp-vs-tcp-latency.sh

echo "=== UDP vs TCP 延迟对比 ==="

# UDP 延迟测试（100 次）
echo ""
echo "--- UDP 延迟测试（100 次往返）---"
UDP_START=$(date +%s%N)
for i in $(seq 1 100); do
    echo "ping_$i" | nc -u -w 1 127.0.0.1 8888 > /dev/null 2>&1
done
UDP_END=$(date +%s%N)
UDP_TIME=$(( (UDP_END - UDP_START) / 1000000 ))
echo "UDP 100 次总耗时: ${UDP_TIME}ms"
echo "UDP 平均延迟: $(( UDP_TIME / 100 ))ms"

# TCP 延迟测试（100 次连接建立）
echo ""
echo "--- TCP 延迟测试（100 次连接建立）---"
TCP_START=$(date +%s%N)
for i in $(seq 1 100); do
    echo "ping_$i" | nc -w 1 127.0.0.1 9999 > /dev/null 2>&1
done
TCP_END=$(date +%s%N)
TCP_TIME=$(( (TCP_END - TCP_START) / 1000000 ))
echo "TCP 100 次总耗时: ${TCP_TIME}ms"
echo "TCP 平均延迟: $(( TCP_TIME / 100 ))ms"

echo ""
echo "=== 测试完成 ==="
```

### 练习 2：DNS 查询与协议分析

```bash
# 查看 DNS 查询使用的协议
dig +tcp google.com | grep "Query time"
# 强制使用 TCP 查询

dig +notcp google.com | grep "Query time"
# 强制使用 UDP 查询

# 使用 tcpdump 观察 DNS 查询过程
sudo tcpdump -i any -n 'port 53' -v
# 在另一个终端执行：
dig google.com
# 观察 tcpdump 输出中的 UDP 53 流量

# 观察 DNS 查询类型
dig google.com A       # A 记录
dig google.com AAAA    # AAAA 记录
dig google.com MX      # MX 记录
dig google.com ANY     # 所有记录（部分服务器已禁用）

# 查看 DNS 响应是否被截断
dig +bufsize=512 google.com
# 如果响应超过 512 字节，会设置 TC 标志
# 客户端需要改用 TCP 查询

# 查看 DNS 缓存状态（systemd-resolved）
resolvectl query google.com
# 会显示缓存命中情况
```

### 练习 3：模拟 DNS 查询超时场景

```bash
# 模拟 UDP 53 被丢弃的场景
# 使用 iptables 丢弃 UDP 53 出站包

# 先记录当前规则
sudo iptables -L -n

# 添加规则：丢弃 UDP 53 出站
sudo iptables -A OUTPUT -p udp --dport 53 -j DROP

# 测试 DNS 查询
dig google.com
# 应该超时（UDP 被丢弃）
# ;; connection timed out; no servers could be reached

# 测试 TCP 53 查询（应该成功）
dig +tcp google.com
# 应该正常返回结果

# 清除规则
sudo iptables -D OUTPUT -p udp --dport 53 -j DROP

# 验证规则已清除
dig google.com
# 应该恢复正常
```

### 练习 4：使用 curl 测试 HTTP/3

```bash
# 检查 curl 是否支持 HTTP/3
curl --version | grep -i quic
# 如果没有 quic/HTTP3 字样，需要安装支持 HTTP/3 的版本

# 安装支持 HTTP/3 的 curl（Ubuntu）
sudo apt-get install curl -y
# 注意：多数发行版的 curl 不支持 HTTP/3
# 需要自行编译：https://github.com/curl/curl/blob/master/docs/HTTP3.md

# 使用 curl 测试 HTTP/3
curl --http3-only https://cloudflare.com -o /dev/null -w "HTTP 版本: %{http_version}\n"
# 如果支持 HTTP/3，输出：HTTP 版本: 3

# 强制使用 HTTP/2
curl --http2 https://cloudflare.com -o /dev/null -w "HTTP 版本: %{http_version}\n"

# 使用 ngtcp2 工具测试 QUIC
# https://github.com/ngtcp2/ngtcp2
sudo apt-get install quiche -y  # Cloudflare 的 QUIC 实现

# 使用 quic-go 的客户端测试
go install github.com/quic-go/quic-go/http3/example/client@latest

# 使用 Wireshark 分析 QUIC 流量
sudo tcpdump -i any -w /tmp/quic.pcap 'udp port 443'
# 用 Wireshark 打开，设置 SSLKEYLOGFILE 环境变量解密
```

### 练习 5：UDP 监听与端口检查

```bash
# 查看 UDP 监听端口
ss -uln
# -u: UDP
# -l: 监听
# -n: 不解析名称

# 查看所有 UDP 连接（包括已建立的）
ss -uan

# 查看指定 UDP 端口的连接
ss -uan | grep :53

# 使用 nc 创建 UDP 监听器
nc -ul -p 9999

# 使用 nc 发送 UDP 数据包
echo "Hello UDP" | nc -u -w 1 127.0.0.1 9999

# 使用 nmap 扫描 UDP 端口
sudo nmap -sU -p 53,123,161,514 192.168.1.1
# -sU: UDP 扫描
# 注意：UDP 扫描比 TCP 扫描慢得多

# 查看 UDP 相关的内核参数
sysctl -a | grep udp_
# net.ipv4.udp_mem          # UDP 内存限制
# net.ipv4.udp_rmem_min     # 最小接收缓冲区
# net.ipv4.udp_wmem_min     # 最小发送缓冲区
```

---

## 🔍 SRE 实战案例：DNS 查询超时 → UDP 53 被丢弃 → TCP 53 回退

### 场景描述

生产环境中，部分 Pod 突然出现 DNS 解析超时，导致服务间通信失败，引发级联故障。

### 排查过程

```
告警信息：
- 服务 A 调用服务 B 超时率飙升（> 50%）
- 服务 A 日志中出现 "dial tcp: lookup service-b.default: i/o timeout"
- 其他服务正常，只有服务 A 受影响

时间线：
09:00  告警触发
09:02  进入服务 A 的 Pod 排查
09:05  确认 DNS 解析失败
09:10  定位根因
```

#### Step 1：确认 DNS 解析失败

```bash
# 在 Pod 内测试 DNS
nslookup service-b.default
# Server:    10.96.0.10
# Address:   10.96.0.10#53
# ** server can't find service-b.default: NXDOMAIN
# 或者超时：;; connection timed out; no servers could be reached

# 使用 dig 查看详细信息
dig @10.96.0.10 service-b.default.svc.cluster.local
# ;; connection timed out; no servers could be reached

# 直接 ping IP 确认网络可达
ping 10.96.0.10
# 64 bytes from 10.96.0.10: icmp_seq=1 ttl=64 time=0.5 ms
# ✅ CoreDNS 可达
```

#### Step 2：分析 DNS 协议层面

```bash
# 检查 DNS 查询使用的协议
dig @10.96.0.10 +tcp service-b.default.svc.cluster.local
# ;; Query time: 2 msec
# ;; SERVER: 10.96.0.10#53(TCP)
# ✅ TCP 53 正常！

dig @10.96.0.10 +notcp service-b.default.svc.cluster.local
# ;; connection timed out; no servers could be reached
# ❌ UDP 53 超时！

# 结论：UDP 53 被丢弃，但 TCP 53 正常
```

#### Step 3：定位根因

```bash
# 检查 iptables 规则
iptables -L -n -v | grep 53
# 发现一条规则：
# DROP  udp  --  *      *       10.244.0.0/16        10.96.0.10           udp dpt:53

# 这条规则是谁加的？
# 检查 kube-proxy 日志
journalctl -u kube-proxy --since "1 hour ago" | grep -i "iptables\|53"

# 检查网络策略（NetworkPolicy）
kubectl get networkpolicy -A
# 发现某条 NetworkPolicy 只允许 TCP 流量到 CoreDNS
# 但没有允许 UDP 流量！
```

```yaml
# 问题 NetworkPolicy（不完整）
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: service-a
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
        - podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: TCP    # ❌ 只允许了 TCP！
          port: 53
        # 缺少 UDP 53 的规则
```

#### Step 4：修复方案

```yaml
# 修复后的 NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: service-a
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
        - podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: TCP    # ✅ 同时允许 TCP
          port: 53
        - protocol: UDP    # ✅ 允许 UDP
          port: 53
```

```bash
# 应用修复
kubectl apply -f networkpolicy-allow-dns.yaml

# 验证修复
kubectl exec -it pod/service-a-xxx -- dig @10.96.0.10 service-b.default.svc.cluster.local
# 应该恢复正常
```

#### Step 5：根因分析与经验总结

```
根因链条：
开发团队添加了 NetworkPolicy 限制出站流量
  → 只允许了 TCP 53 到 CoreDNS
  → 忘记允许 UDP 53
  → DNS 客户端默认使用 UDP 53 查询
  → UDP 53 被 NetworkPolicy 丢弃
  → DNS 查询超时（默认超时 5 秒）
  → 服务调用失败
  → 部分 DNS 客户端在 UDP 超时后会回退到 TCP 53
  → 但回退延迟很长（5 秒超时 + TCP 握手 + TCP 查询）
  → 用户体验：DNS 解析很慢（5 秒+）

为什么 DNS 默认使用 UDP？
1. DNS 响应通常很小（< 512 字节）
2. UDP 无连接开销，延迟更低
3. 减少 DNS 服务器负载
4. 历史原因：DNS 设计于 1987 年，UDP 更高效

什么时候回退到 TCP？
1. 响应超过 512 字节（TC 标志设置）
2. 区域传输（AXFR）
3. 部分客户端在 UDP 超时后自动回退
4. 显式使用 dig +tcp 命令

经验教训：
1. NetworkPolicy 必须同时允许 TCP 和 UDP 53
2. DNS 超时时间较长（默认 5 秒），对延迟敏感的服务影响大
3. 添加 NetworkPolicy 后应进行全面测试（UDP + TCP）
4. 可以设置 DNS 超时时间：/etc/resolv.conf 中 options timeout:1 attempts:2
```

#### Step 6：预防措施

```bash
# 1. 添加监控告警
# 监控 DNS 查询失败率
# CoreDNS 指标：coredns_dns_request_duration_seconds
# 关注超时查询比例

# 2. 添加 DNS 查询延迟告警
# Prometheus 规则
- alert: HighDNSLatency
  expr: histogram_quantile(0.99, rate(coredns_dns_request_duration_seconds_bucket[5m])) > 1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "DNS 查询延迟过高 (P99 > 1s)"

# 3. 优化 DNS 配置
# /etc/resolv.conf
options timeout:1    # 每次查询超时 1 秒（默认 5 秒）
options attempts:2   # 重试 2 次（默认 2 次）
options ndots:5      # 小于 5 个点先搜索本地域

# 4. 使用本地 DNS 缓存
# 在 Pod 中运行 dnsmasq 或 nscd
# 减少对外部 DNS 的查询次数

# 5. 定期测试 DNS 连通性
# 作为健康检查的一部分
dig @10.96.0.10 kubernetes.default.svc.cluster.local
# 失败时触发告警
```

---

## 📚 最新优质资源

### 官方文档
- [RFC 768 - User Datagram Protocol (UDP)](https://datatracker.ietf.org/doc/html/rfc768) — UDP 协议原始规范
- [RFC 9000 - QUIC: A UDP-Based Multiplexed and Secure Transport](https://datatracker.ietf.org/doc/html/rfc9000) — QUIC 协议核心规范
- [RFC 9114 - HTTP/3](https://datatracker.ietf.org/doc/html/rfc9114) — HTTP/3 规范
- [RFC 1035 - Domain Names Implementation](https://datatracker.ietf.org/doc/html/rfc1035) — DNS 协议规范

### 推荐教程
- [Cloudflare - What is UDP?](https://www.cloudflare.com/learning/ddos/glossary/user-datagram-protocol-udp/) — UDP 入门教程
- [Cloudflare - What is QUIC?](https://www.cloudflare.com/learning/performance/what-is-quic/) — QUIC 详细讲解
- [QUIC Working Group](https://quicwg.org/) — QUIC 官方工作组
- [HTTP/3 Explained](https://http3-explained.haxx.se/) — Daniel Stenberg（curl 作者）的 HTTP/3 详解

### 视频课程
- [Bilibili - DNS 原理与排障实战](https://www.bilibili.com/video/BV1qW411u7ax/) — 深入理解 DNS
- [YouTube - QUIC Protocol Explained](https://www.youtube.com/watch?v=xhRRpD8j5hY) — QUIC 协议可视化讲解
- [Bilibili - HTTP/3 与 QUIC 协议详解](https://www.bilibili.com/video/BV1Xv4y1U7jG/) — 中文深度讲解

### SRE 相关资源
- [CoreDNS 官方文档](https://coredns.io/) — Kubernetes DNS 服务
- [QUIC-Go 实现](https://github.com/quic-go/quic-go) — Go 语言的 QUIC 实现
- [Cloudflare Blog - QUIC](https://blog.cloudflare.com/tag/quic/) — Cloudflare 的 QUIC 实践
- [HTTP/3 vs HTTP/2 Performance](https://blog.cloudflare.com/http-3-vs-http-2/) — 性能对比分析

---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）
- UDP 是无连接的、不可靠的传输协议，但正是这种"简单"带来了低延迟优势
- DNS 是 UDP 最经典的应用场景，小请求小响应 + 延迟敏感 = UDP 完美匹配
- 当 UDP 53 被阻断时，DNS 可以回退到 TCP 53，但回退延迟很长（5 秒+）
- QUIC 在 UDP 之上重新实现了可靠传输，解决了 TCP 的队头阻塞和连接迁移问题
- HTTP/3 = QUIC 上的 HTTP，首次连接 1 RTT，恢复连接 0 RTT
- QUIC 的加密是内置的（TLS 1.3），不像 TCP 需要额外加 TLS 层
- NetworkPolicy 忘记放行 UDP 53 是 Kubernetes 中的常见坑

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| curl 不支持 HTTP/3 | 编译支持 QUIC 的 curl 版本，或使用 quiche/ngtcp2 |
| QUIC 流量无法抓包分析 | 设置 SSLKEYLOGFILE 环境变量，Wireshark 导入密钥解密 |
| UDP 扫描速度极慢 | 使用 masscan 替代 nmap，或仅扫描已知端口 |
| DNS 查询慢但 TCP 53 正常 | 检查防火墙/NetworkPolicy 是否放行了 UDP 53 |
| CoreDNS 日志中出现 SERVFAIL | 检查上游 DNS 配置和后端 Pod 状态 |

### 延伸思考

- 思考 1：QUIC 将传输层从内核移到用户态，这对性能和可维护性有什么影响？
- 思考 2：在 Kubernetes 中，CoreDNS 同时处理 TCP 和 UDP 53，两者的性能特征有什么不同？
- 思考 3：如果所有流量都迁移到 HTTP/3（QUIC），传统的 TCP 监控工具如何适应？

---

## ✅ 完成检查

- [ ] 理解 UDP 协议的核心特性和适用场景
- [ ] 掌握 DNS 协议基于 UDP 的工作原理
- 理解 DNS 的 TCP 回退机制（UDP 超时/截断 → TCP 53）
- [ ] 理解 QUIC 协议的设计动机和核心特性
- [ ] 理解 HTTP/3 与 HTTP/1.1、HTTP/2 的区别
- [ ] 理解 QUIC 的多路复用如何解决队头阻塞
- [ ] 完成 netcat UDP 测试练习
- [ ] 完成 DNS 查询与协议分析练习
- [ ] 完成 HTTP/3 测试练习
- [ ] 理解 SRE 实战案例中的 DNS 超时 → UDP 被丢弃 → TCP 回退链路
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记

---

*由 SRE 学习计划自动生成 | 2026-05-01*
