# Day 42: 网络基础综合评估

> 📅 日期：2026-05-02
> 📖 学习主题：网络基础综合评估 — 回顾、测试、实战
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 29-41 所有网络相关知识

## 🎯 学习目标

- 综合回顾 Day 29-41 的核心知识点
- 通过理论测试检验对网络协议的理解
- 通过实操测试检验网络故障排查能力
- 明确下一步学习路线图

---

## 📖 知识回顾表

### Day 29-41 核心知识点速查

| Day | 主题 | 核心知识点 | SRE 关键技能 |
|-----|------|-----------|-------------|
| 29 | OSI 模型与 TCP/IP | 七层模型、封装与解封装 | 理解数据包从应用到物理的完整路径 |
| 30 | TCP 协议详解 | 三次握手、四次挥手、状态机 | 排查 TIME_WAIT/CLOSE_WAIT、理解重传 |
| 31 | UDP 与 QUIC/HTTP3 | UDP 特点、QUIC 原理 | 理解实时通信、HTTP/3 优势 |
| 32 | IP 协议与子网划分 | IP 地址分类、CIDR、NAT | 子网计算、NAT 配置 |
| 33 | 路由基础 | 路由表、默认网关、静态路由 | 路由排查、策略路由 |
| 34 | DNS 协议 | 记录类型、解析链、TTL | DNS 故障排查、记录配置 |
| 35 | 从 URL 到页面 | 完整请求链路 | 理解全链路性能分析 |
| 36 | ping/traceroute/mtr/dig | 网络诊断工具 | 网络连通性和路径排查 |
| 37 | nc/curl/wget | 高级网络工具 | HTTP 调试、时间分解、健康检查 |
| 38 | tcpdump 抓包分析 | BPF 过滤、抓包分析 | 生产环境抓包、重传分析 |
| 39 | iptables/nftables | 防火墙、NAT、fail2ban | 安全防护、端口转发、自动封禁 |
| 40 | HTTP/HTTPS 深入 | 状态码、TLS 握手、缓存 | 502/504 排查、证书管理 |
| 41 | Socket/Nginx/HAProxy | I/O 模型、负载均衡 | 反向代理配置、性能调优 |

### 网络分层与 SRE 工具对照

```
┌─────────────────────────────────────────────────────────────────┐
│  应用层 (7)    HTTP, DNS, SMTP, gRPC                            │
│  工具: curl, wget, dig, nc                                      │
│  SRE: API 调试、DNS 排查、健康检查                              │
├─────────────────────────────────────────────────────────────────┤
│  表示层 (6)    TLS/SSL, JSON, gzip                              │
│  工具: openssl, curl -v                                         │
│  SRE: 证书管理、TLS 握手排查                                    │
├─────────────────────────────────────────────────────────────────┤
│  会话层 (5)    NetBIOS, RPC                                     │
│  SRE: 连接管理                                                  │
├─────────────────────────────────────────────────────────────────┤
│  传输层 (4)    TCP, UDP                                         │
│  工具: ss, netstat, tcpdump                                     │
│  SRE: 连接状态排查、重传分析、端口检查                          │
├─────────────────────────────────────────────────────────────────┤
│  网络层 (3)    IP, ICMP, ARP                                    │
│  工具: ping, traceroute, mtr, ip route                          │
│  SRE: 路由排查、子网划分、连通性测试                            │
├─────────────────────────────────────────────────────────────────┤
│  数据链路层(2)  Ethernet, WiFi                                  │
│  工具: ip link, ethtool, arp                                    │
│  SRE: 网卡状态、MAC 地址、MTU                                   │
├─────────────────────────────────────────────────────────────────┤
│  物理层 (1)    光纤、电缆、无线电                               │
│  SRE: 网线、交换机端口、物理连接                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 理论测试（20 道题）

### Part 1: TCP 协议（5 题）

**Q1：请画出 TCP 三次握手的完整过程，包括每个包的标志位和序列号。**

<details>
<summary>参考答案</summary>

```
客户端                                服务器
  │                                     │
  │  SYN, seq=x                         │
  │ ───────────────────────────────────→│  第 1 次握手
  │                                     │
  │  SYN+ACK, seq=y, ack=x+1           │
  │ ←───────────────────────────────────│  第 2 次握手
  │                                     │
  │  ACK, seq=x+1, ack=y+1             │
  │ ───────────────────────────────────→│  第 3 次握手
  │                                     │
  │  ←── 数据传输开始 ──→                │
```

- 第 1 次：客户端发送 SYN（seq=x），进入 SYN_SENT 状态
- 第 2 次：服务器回复 SYN+ACK（seq=y, ack=x+1），进入 SYN_RCVD 状态
- 第 3 次：客户端发送 ACK（ack=y+1），双方进入 ESTABLISHED 状态

</details>

**Q2：TIME_WAIT 状态的作用是什么？为什么需要等待 2MSL？**

<details>
<summary>参考答案</summary>

TIME_WAIT 的作用：
1. **确保最后一个 ACK 到达**：如果服务器没收到最后的 ACK，会重传 FIN，客户端需要 TIME_WAIT 来处理
2. **防止旧连接的数据包干扰新连接**：等待 2MSL 确保网络中属于该连接的所有数据包都已消失

2MSL（Maximum Segment Lifetime）= 2 * 2 分钟 = 4 分钟（Linux 默认 60 秒）

调优：
```bash
# 允许 TIME_WAIT 状态的 socket 被快速回收
sudo sysctl -w net.ipv4.tcp_tw_reuse=1

# 减少 TIME_WAIT 超时
sudo sysctl -w net.netfilter.nf_conntrack_tcp_timeout_time_wait=30
```

</details>

**Q3：CLOSE_WAIT 状态大量堆积说明什么问题？如何排查？**

<details>
<summary>参考答案</summary>

CLOSE_WAIT 大量堆积说明**应用程序没有正确关闭连接**（没有调用 close()）。

排查步骤：
```bash
# 1. 查看 CLOSE_WAIT 数量
ss -t state close-wait | wc -l

# 2. 查看哪些进程有 CLOSE_WAIT
ss -t state close-wait -p

# 3. 检查应用代码
# 通常是连接泄漏：创建了连接但没有在 finally 中关闭
```

常见原因：
- 代码 Bug：没有关闭连接
- 连接池配置不当
- 上游服务异常导致连接未正常关闭

</details>

**Q4：TCP 重传机制是怎样的？重传率多少算正常？**

<details>
<summary>参考答案</summary>

TCP 重传机制：
1. **超时重传**：发送数据后启动定时器，超时未收到 ACK 则重传
2. **快速重传**：收到 3 个重复 ACK 立即重传（不等超时）
3. **SACK（选择性确认）**：只重传丢失的数据段

重传率标准：
- < 1%：正常
- 1%-5%：需要关注
- \> 5%：有问题，需要排查

排查：
```bash
# 使用 tcpdump 分析重传
tshark -r capture.pcap -Y "tcp.analysis.retransmission" | wc -l

# 使用 ss 查看重传统计
ss -s
```

</details>

**Q5：TCP 的滑动窗口和拥塞控制有什么区别？**

<details>
<summary>参考答案</summary>

- **滑动窗口（流量控制）**：接收方通过窗口大小告诉发送方自己还能接收多少数据，防止接收方缓冲区溢出。是**端到端**的控制。

- **拥塞控制**：发送方根据网络状况调整发送速率，防止网络拥塞。是**全局**的控制。

拥塞控制算法：
- 慢启动（Slow Start）：指数增长
- 拥塞避免（Congestion Avoidance）：线性增长
- 快速重传（Fast Retransmit）：3 个重复 ACK
- 快速恢复（Fast Recovery）：从快速重传恢复

</details>

### Part 2: IP 与子网（3 题）

**Q6：请计算 192.168.1.0/26 可以容纳多少台主机？该子网的广播地址是什么？**

<details>
<summary>参考答案</summary>

/26 表示网络位 26 位，主机位 32-26=6 位。

- 可用主机数：2^6 - 2 = 62 台（去掉网络地址和广播地址）
- 子网掩码：255.255.255.192
- 网络地址：192.168.1.0
- 广播地址：192.168.1.63
- 可用 IP 范围：192.168.1.1 - 192.168.1.62

</details>

**Q7：10.0.1.100/24 和 10.0.2.100/24 能直接通信吗？需要什么？**

<details>
<summary>参考答案</summary>

不能直接通信。它们在不同的子网：
- 10.0.1.100/24 的网络地址是 10.0.1.0
- 10.0.2.100/24 的网络地址是 10.0.2.0

需要**路由器**转发。需要：
1. 两个子网都配置默认网关
2. 路由器连接两个子网
3. 路由器启用 IP 转发

</details>

**Q8：SNAT 和 DNAT 分别在什么时候使用？**

<details>
<summary>参考答案</summary>

- **SNAT（Source NAT）**：内网服务器访问外网时，将源地址改为公网 IP。在 POSTROUTING 链执行。
  - 场景：内网服务器访问互联网

- **DNAT（Destination NAT）**：外部请求转发到内部服务器。在 PREROUTING 链执行。
  - 场景：端口转发、负载均衡器

</details>

### Part 3: DNS（3 题）

**Q9：DNS 递归查询和迭代查询的区别是什么？**

<details>
<summary>参考答案</summary>

- **递归查询**：客户端向本地 DNS 服务器查询，本地 DNS 服务器负责完成整个查询过程，最终返回结果给客户端。

- **迭代查询**：本地 DNS 服务器向根/顶级/权威 DNS 服务器逐步查询，每次得到一个"去问下一个"的指引。

通常：
- 客户端 → 本地 DNS：递归查询
- 本地 DNS → 根/顶级/权威：迭代查询

</details>

**Q10：DNS 的 A、AAAA、CNAME、MX、NS、TXT 记录分别是什么？**

<details>
<summary>参考答案</summary>

| 记录类型 | 说明 | 示例 |
|----------|------|------|
| A | IPv4 地址 | example.com → 93.184.216.34 |
| AAAA | IPv6 地址 | example.com → 2606:2800:220:1:... |
| CNAME | 别名 | www.example.com → example.com |
| MX | 邮件服务器 | example.com → mail.example.com (优先级 10) |
| NS | 域名服务器 | example.com → ns1.example.com |
| TXT | 文本记录 | 用于 SPF、DKIM、域名验证 |
| SRV | 服务记录 | _sip._tcp.example.com → sipserver.example.com |
| PTR | 反向解析 | 34.216.184.93 → example.com |

</details>

**Q11：DNS 缓存中毒是什么？如何防范？**

<details>
<summary>参考答案</summary>

DNS 缓存中毒（DNS Cache Poisoning）：攻击者伪造 DNS 响应，将域名解析到恶意 IP。

攻击原理：
1. 攻击者发送大量 DNS 查询
2. 在权威服务器响应之前，伪造响应
3. 如果伪造响应先到达，DNS 服务器会缓存错误结果

防范措施：
- **DNSSEC**：对 DNS 响应进行数字签名
- **DNS over HTTPS (DoH)**：加密 DNS 查询
- **DNS over TLS (DoT)**：加密 DNS 传输
- **随机化查询 ID**：增加伪造难度
- **限制递归查询**：只允许内部网络递归

</details>

### Part 4: HTTP/HTTPS（4 题）

**Q12：HTTP/1.1 和 HTTP/2 的主要区别是什么？**

<details>
<summary>参考答案</summary>

| 特性 | HTTP/1.1 | HTTP/2 |
|------|----------|--------|
| 传输格式 | 文本 | 二进制分帧 |
| 多路复用 | 不支持（有队头阻塞） | 支持 |
| 头部压缩 | 无 | HPACK |
| 服务器推送 | 不支持 | 支持 |
| 连接管理 | Keep-Alive | 单连接多路复用 |

</details>

**Q13：HTTPS 的 TLS 握手过程是怎样的？**

<details>
<summary>参考答案</summary>

1. ClientHello：客户端发送支持的 TLS 版本、加密套件、随机数
2. ServerHello：服务器选择版本和套件，发送随机数
3. Certificate：服务器发送证书链
4. ServerKeyExchange：发送 ECDH 公钥（ECDHE 模式）
5. ClientKeyExchange：客户端发送 ECDH 公钥
6. 双方计算共享密钥
7. ChangeCipherSpec + Finished：切换到加密通信

TLS 1.3 优化为 1-RTT，且 Certificate 之后的消息全部加密。

</details>

**Q14：强缓存和协商缓存的区别是什么？**

<details>
<summary>参考答案</summary>

- **强缓存**：不需要向服务器请求，直接使用本地缓存
  - 头部：`Cache-Control: max-age=xxx`、`Expires`
  - 状态码：200 (from cache)

- **协商缓存**：需要向服务器验证资源是否过期
  - 头部：`ETag`/`If-None-Match`、`Last-Modified`/`If-Modified-Since`
  - 状态码：304 Not Modified（未修改）、200（已修改）

流程：先检查强缓存 → 命中直接用 → 未命中检查协商缓存 → 命中返回 304 → 未命中返回 200

</details>

**Q15：502 和 504 错误分别是什么原因？**

<details>
<summary>参考答案</summary>

- **502 Bad Gateway**：网关/代理从上游收到**无效响应**
  - 原因：上游服务崩溃、返回不完整响应
  - 排查：检查上游服务状态

- **504 Gateway Timeout**：网关/代理等待上游响应**超时**
  - 原因：上游处理太慢
  - 排查：检查上游性能、调整超时配置

</details>

### Part 5: 防火墙与负载均衡（5 题）

**Q16：iptables 的四表五链是什么？**

<details>
<summary>参考答案</summary>

四表（优先级从高到低）：raw → mangle → nat → filter
五链：PREROUTING、INPUT、FORWARD、OUTPUT、POSTROUTING

数据包流向：
- 入站：PREROUTING → INPUT → 本地进程
- 转发：PREROUTING → FORWARD → POSTROUTING
- 出站：本地进程 → OUTPUT → POSTROUTING

</details>

**Q17：nftables 相比 iptables 有什么优势？**

<details>
<summary>参考答案</summary>

1. 统一框架：替代 iptables/ip6tables/arptables/ebtables
2. 更好性能：支持集合（set），O(1) 匹配
3. 原子操作：整表替换
4. 更简洁语法：声明式配置
5. 原生 IPv4/IPv6 双栈
6. 动态集合：支持超时自动过期

</details>

**Q18：四层和七层负载均衡的区别是什么？**

<details>
<summary>参考答案</summary>

- **四层**：传输层（TCP/UDP），根据 IP+端口转发，性能高，支持任何协议
- **七层**：应用层（HTTP），根据 URL/Header/Cookie 路由，功能强大

选择：
- 数据库、Redis：四层
- Web 应用、API：七层
- 需要内容路由：七层

</details>

**Q19：Nginx 和 HAProxy 应该如何选择？**

<details>
<summary>参考答案</summary>

- **Nginx**：Web 服务器 + 反向代理，能同时处理静态文件和代理
- **HAProxy**：专业负载均衡器，ACL 更灵活，内置统计页面

选择：
- 需要 Web 服务器 + 反向代理：Nginx
- 需要专业负载均衡（特别是四层）：HAProxy
- 需要统计页面：HAProxy
- 已有 Nginx：Nginx

</details>

**Q20：如何防止 SSH 暴力破解？**

<details>
<summary>参考答案</summary>

1. **fail2ban**：自动封禁暴力破解 IP
2. **iptables 限速**：限制 SSH 连接速率
3. **密钥认证**：禁用密码登录
4. **修改端口**：使用非标准端口
5. **安全组限制**：只允许特定 IP 访问 SSH
6. **Port Knocking**：先敲门再开放端口

```bash
# fail2ban 配置
[sshd]
enabled = true
maxretry = 3
bantime = 7200
findtime = 300
```

</details>

---

## 💻 实操测试（5 个场景）

### 场景 1：tcpdump 抓包分析 TCP 连接问题

**任务**：使用 tcpdump 抓包分析以下场景，并写出排查步骤。

**场景描述**：用户报告访问 `http://10.0.1.50:8080/api/data` 偶尔超时，错误率约 10%。

**你需要**：
1. 写出 tcpdump 命令抓取相关流量
2. 如何判断是 SYN 被丢弃还是响应超时
3. 如何计算重传率
4. 可能的根因和解决方案

<details>
<summary>参考答案</summary>

```bash
# 1. 抓取相关流量
sudo tcpdump -i eth0 -nn -s 0 -w /tmp/timeout.pcap host 10.0.1.50 and port 8080

# 2. 分析 SYN 包
sudo tcpdump -r /tmp/timeout.pcap -nn 'tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0'
# 如果看到 SYN 重传（1秒、2秒、4秒...），说明 SYN 被丢弃
# 如果看到 SYN+ACK 正常返回，但数据传输慢，说明是响应超时

# 3. 计算重传率
total=$(tshark -r /tmp/timeout.pcap -Y tcp -T fields -e frame.number 2>/dev/null | wc -l)
retrans=$(tshark -r /tmp/timeout.pcap -Y "tcp.analysis.retransmission" -T fields -e frame.number 2>/dev/null | wc -l)
echo "重传率: $(echo "scale=2; $retrans * 100 / $total" | bc)%"

# 4. 可能根因
# - SYN 被丢弃 → 防火墙限速规则
# - 响应超时 → 上游服务处理慢
# - 重传率高 → 网络质量差
```

</details>

### 场景 2：用 curl 时间分解分析 API 延迟

**任务**：分析一个 API 的延迟瓶颈。

**场景描述**：`https://api.example.com/users` 响应时间 3 秒，需要找出瓶颈在哪里。

**你需要**：
1. 使用 curl 时间分解获取各阶段耗时
2. 分析哪个阶段是瓶颈
3. 针对性优化建议

<details>
<summary>参考答案</summary>

```bash
# 1. curl 时间分解
curl -o /dev/null -s -w \
  "DNS:       %{time_namelookup}s\n\
   TCP:       %{time_connect}s\n\
   TLS:       %{time_appconnect}s\n\
   TTFB:      %{time_starttransfer}s\n\
   Total:     %{time_total}s\n" \
  https://api.example.com/users

# 2. 分析
# DNS: 0.01s → 正常
# TCP: 0.05s → 正常（TCP 连接 = 0.04s）
# TLS: 0.15s → 正常（TLS 握手 = 0.10s）
# TTFB: 2.8s → 异常！首字节时间太长
# Total: 3.0s → 瓶颈在 TTFB

# 3. 优化建议
# TTFB 长 = 服务器处理慢
# - 检查数据库查询
# - 检查是否有 N+1 查询
# - 增加缓存
# - 检查上游服务依赖
```

</details>

### 场景 3：配置 iptables 防火墙规则

**任务**：为一台公网 Web 服务器配置基本防火墙。

**要求**：
- 只允许 SSH(22)、HTTP(80)、HTTPS(443) 入站
- 允许已建立的连接
- 允许本地回环
- 允许 ICMP（限速）
- 记录被拒绝的包
- 默认策略为 DROP

<details>
<summary>参考答案</summary>

```bash
# 备份现有规则
sudo iptables-save > ~/iptables-backup.bak

# 清空规则
sudo iptables -F
sudo iptables -X

# 设置默认策略
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# 允许本地回环
sudo iptables -A INPUT -i lo -j ACCEPT

# 允许已建立的连接
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# 允许 SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许 ICMP（限速）
sudo iptables -A INPUT -p icmp --icmp-type echo-request \
  -m limit --limit 1/s --limit-burst 4 -j ACCEPT

# 记录被拒绝的包
sudo iptables -A INPUT -m limit --limit 5/min \
  -j LOG --log-prefix "iptables-drop: " --log-level 4

# 查看规则
sudo iptables -L -n -v --line-numbers

# 保存
sudo iptables-save > /etc/iptables/rules.v4
```

</details>

### 场景 4：排查 DNS 解析异常

**任务**：用户报告 `dig example.com` 返回错误结果。

**你需要**：
1. 使用 dig 从不同 DNS 服务器查询
2. 对比结果找出问题
3. 检查本地 DNS 配置
4. 排查是否有 DNS 劫持

<details>
<summary>参考答案</summary>

```bash
# 1. 从不同 DNS 服务器查询
dig example.com @8.8.8.8          # Google DNS
dig example.com @1.1.1.1          # Cloudflare DNS
dig example.com @$(cat /etc/resolv.conf | grep nameserver | head -1 | awk '{print $2}')  # 本地 DNS

# 2. 对比结果
# 如果 8.8.8.8 和 1.1.1.1 返回正确，但本地 DNS 返回错误 → 本地 DNS 有问题

# 3. 检查本地 DNS 配置
cat /etc/resolv.conf
# 检查是否有异常的 nameserver

# 4. 检查是否有 DNS 劫持
# tcpdump 抓取 DNS 流量
sudo tcpdump -i any -nn port 53
# 观察 DNS 查询是否发到了预期的 DNS 服务器

# 5. 检查是否有恶意进程修改 DNS 配置
sudo lsof -i :53
sudo netstat -tulnp | grep :53

# 6. 修复
# 恢复正确的 DNS 配置
# 锁定 /etc/resolv.conf（chattr +i）
```

</details>

### 场景 5：编写网络诊断脚本

**任务**：编写一个综合网络诊断脚本，自动检查网络连通性、DNS、端口、HTTP 等。

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# network-diag.sh - 综合网络诊断脚本

set -e

TARGET=${1:-"example.com"}
TARGET_IP=$(dig +short $TARGET | head -1)

echo "=========================================="
echo "  网络诊断报告: $TARGET ($TARGET_IP)"
echo "  时间: $(date)"
echo "=========================================="

# 1. DNS 解析检查
echo ""
echo "=== DNS 解析检查 ==="
echo "A 记录:"
dig +short $TARGET A
echo "AAAA 记录:"
dig +short $TARGET AAAA
echo "NS 记录:"
dig +short $TARGET NS

# 2. 连通性检查
echo ""
echo "=== 连通性检查 ==="
if ping -c 3 -W 2 $TARGET_IP > /dev/null 2>&1; then
    echo "PING: OK"
    ping -c 3 -W 2 $TARGET_IP | tail -1
else
    echo "PING: FAIL"
fi

# 3. 路由检查
echo ""
echo "=== 路由检查 ==="
traceroute -m 15 -w 2 $TARGET_IP 2>/dev/null | head -20 || echo "traceroute 不可用"

# 4. 端口检查
echo ""
echo "=== 端口检查 ==="
for port in 80 443 22; do
    if nc -zv -w 3 $TARGET_IP $port 2>&1 | grep -q "succeeded"; then
        echo "端口 $port: OPEN"
    else
        echo "端口 $port: CLOSED"
    fi
done

# 5. HTTP 检查
echo ""
echo "=== HTTP 检查 ==="
if command -v curl > /dev/null 2>&1; then
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 http://$TARGET 2>/dev/null)
    echo "HTTP 状态码: $http_code"

    if [ "$http_code" != "000" ]; then
        echo "时间分解:"
        curl -o /dev/null -s -w \
          "  DNS:     %{time_namelookup}s\n\
           TCP:     %{time_connect}s\n\
           TTFB:    %{time_starttransfer}s\n\
           Total:   %{time_total}s\n" \
          --connect-timeout 5 http://$TARGET 2>/dev/null
    fi
fi

# 6. HTTPS 检查
echo ""
echo "=== HTTPS 证书检查 ==="
if command -v openssl > /dev/null 2>&1; then
    cert_info=$(echo | openssl s_client -connect $TARGET:443 -servername $TARGET 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
    if [ -n "$cert_info" ]; then
        echo "$cert_info"
        # 计算剩余天数
        expire_date=$(echo "$cert_info" | grep notAfter | cut -d= -f2)
        expire_ts=$(date -d "$expire_date" +%s 2>/dev/null)
        now_ts=$(date +%s)
        if [ -n "$expire_ts" ]; then
            days_left=$(( (expire_ts - now_ts) / 86400 ))
            echo "  剩余天数: $days_left"
            if [ $days_left -lt 30 ]; then
                echo "  ⚠️ 证书即将过期！"
            fi
        fi
    else
        echo "无法获取证书信息"
    fi
fi

# 7. 系统网络信息
echo ""
echo "=== 系统网络信息 ==="
echo "默认网关:"
ip route | grep default
echo "DNS 配置:"
cat /etc/resolv.conf | grep nameserver
echo "网络接口:"
ip -br addr show

echo ""
echo "=========================================="
echo "  诊断完成"
echo "=========================================="
```

</details>

---

## 📊 能力评估标准

### 评分标准

| 等级 | 理论测试 | 实操测试 | 说明 |
|------|----------|----------|------|
| **优秀** | 18-20 题正确 | 5 个场景全部完成 | 可以独立处理复杂网络问题 |
| **良好** | 14-17 题正确 | 4 个场景完成 | 可以处理大部分网络问题 |
| **及格** | 10-13 题正确 | 3 个场景完成 | 基础扎实，需要更多实践 |
| **需加强** | < 10 题正确 | < 3 个场景完成 | 需要复习相关知识点 |

### 自评清单

**理论知识**：
- [ ] 理解 OSI 七层模型和 TCP/IP 四层模型
- [ ] 掌握 TCP 三次握手、四次挥手、状态机
- [ ] 理解 IP 地址分类、子网划分、CIDR
- [ ] 掌握 DNS 解析链和记录类型
- [ ] 理解 HTTP/HTTPS 协议和 TLS 握手
- [ ] 掌握 iptables 四表五链
- [ ] 理解负载均衡算法和选择

**实操能力**：
- [ ] 能使用 ping/traceroute/mtr/dig 排查网络问题
- [ ] 能使用 tcpdump 抓包分析
- [ ] 能使用 curl 时间分解分析延迟
- [ ] 能配置 iptables/nftables 防火墙
- [ ] 能配置 Nginx/HAProxy 负载均衡
- [ ] 能排查 DNS 解析异常
- [ ] 能编写网络诊断脚本

---

## 🗺️ 下一步学习路线图

### 短期（1-2 周）

```
网络基础（已完成）
    │
    ▼
Day 43-49: Python 编程基础
    │
    ├── Day 43: Python 环境搭建与开发规范
    ├── Day 44: 数据类型与配置文件处理
    ├── Day 45: 系统命令执行与文件操作
    ├── Day 46: 函数、日志模块与异常处理
    ├── Day 47: 正则表达式与日志解析
    ├── Day 48: 网络编程与 HTTP 客户端
    └── Day 49: 数据库交互（SQLite）
```

### 中期（1-2 月）

```
Python 编程
    │
    ▼
自动化运维工具
    │
    ├── Ansible 基础与进阶
    ├── Terraform 基础设施即代码
    ├── CI/CD 流水线（GitLab CI/GitHub Actions）
    └── 容器技术（Docker 深入）
```

### 长期（3-6 月）

```
自动化运维
    │
    ▼
云原生与可观测性
    │
    ├── Kubernetes 集群管理
    ├── Prometheus + Grafana 监控
    ├── ELK/Loki 日志系统
    ├── 分布式追踪（Jaeger/Zipkin）
    └── 混沌工程（Chaos Monkey）
```

### 网络知识进阶

```
网络基础（已完成）
    │
    ├── VPN 技术（WireGuard、OpenVPN）
    ├── SDN（软件定义网络）
    ├── Service Mesh（Istio）
    ├── 网络性能调优（TCP 参数优化）
    └── 容器网络（Calico、Flannel、Cilium）
```

---

## 📝 学习笔记模板

```
日期: ___________
今日学习内容: ___________

关键收获:
1. ___________
2. ___________
3. ___________

遇到的问题:
1. ___________
   解决方案: ___________

需要复习的内容:
1. ___________

明天的计划:
1. ___________
```

---

## ✅ 自检清单

- [ ] 完成理论测试（20 题）
- [ ] 完成实操测试（5 个场景）
- [ ] 评估自己的能力等级
- [ ] 制定下一步学习计划
- [ ] 整理学习笔记
- [ ] 标记需要复习的知识点

---

> 💡 **SRE 心法**：「网络是所有系统的基础。网络问题排查能力是 SRE 的核心竞争力。」掌握了网络基础，你就具备了解决大部分基础设施问题的基础能力。
