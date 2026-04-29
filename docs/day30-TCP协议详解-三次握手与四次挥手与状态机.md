# Day 30: TCP 协议详解 — 三次握手、四次挥手、状态机

> 📅 日期：2026-04-30
> 📖 学习主题：TCP 协议详解 — 三次握手、四次挥手、状态机
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 30 的学习后，你应该掌握：
- 理解 TCP 三次握手和四次挥手的完整过程
- 掌握 TCP 11 种连接状态及其转换关系
- 理解 TIME_WAIT 和 CLOSE_WAIT 的成因与调优方法
- 理解 TCP 拥塞控制算法和 KeepAlive 机制
- 能够在生产环境中诊断 TCP 连接状态异常问题

---

## 📖 详细知识点

### 1. TCP 协议基础

#### 1.1 TCP 的核心特性

TCP（Transmission Control Protocol，传输控制协议）是互联网最核心的协议之一，位于 TCP/IP 模型的传输层。

| 特性 | 说明 | SRE 关注点 |
|------|------|-----------|
| 面向连接 | 通信前需建立连接（三次握手） | 连接建立延迟、SYN Flood 攻击 |
| 可靠传输 | 确认机制（ACK）、重传机制 | 网络丢包率、重传率 |
| 字节流 | 无消息边界，按字节流传输 | 粘包/拆包问题（应用层处理） |
| 全双工 | 双方可同时收发数据 | 连接状态管理 |
| 流量控制 | 滑动窗口机制 | 窗口大小、接收缓冲区 |
| 拥塞控制 | 慢启动、拥塞避免等 | 网络拥塞时吞吐量下降 |

#### 1.2 TCP 头部格式

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          源端口 (16)           |        目的端口 (16)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        序列号 (32)                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        确认号 (32)                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| 数据偏移 |  保留  | 控制位 (6) |          窗口大小 (16)         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          校验和 (16)           |       紧急指针 (16)            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    选项 + 填充（可变长度）                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           数据（Payload）                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**SRE 关键字段**：

| 字段 | 大小 | 说明 |
|------|------|------|
| 源/目的端口 | 各 16 位 | 标识应用进程 |
| 序列号 (Seq) | 32 位 | 标识数据字节的顺序 |
| 确认号 (Ack) | 32 位 | 期望收到的下一个字节序号 |
| 控制位 (Flags) | 6 位 | SYN, ACK, FIN, RST, PSH, URG |
| 窗口大小 | 16 位 | 接收方还能接收的字节数 |
| 数据偏移 | 4 位 | TCP 头部长度（32 位字为单位） |

**6 个控制标志位**：

| 标志位 | 全称 | 含义 | 常见场景 |
|--------|------|------|----------|
| SYN | Synchronize | 同步序列号，建立连接 | 三次握手 |
| ACK | Acknowledge | 确认号有效 | 几乎所有包 |
| FIN | Finish | 发送方数据发送完毕 | 四次挥手 |
| RST | Reset | 连接异常，强制重置 | 端口未监听、连接异常 |
| PSH | Push | 通知接收方立即交付数据 | 减少缓冲延迟 |
| URG | Urgent | 紧急指针有效 | 较少使用 |

### 2. 三次握手（Three-Way Handshake）

#### 2.1 完整过程

```
客户端 (Client)                    服务器 (Server)
     │                                  │
     │       ① SYN=1, Seq=x             │
     │ ───────────────────────────────> │
     │                                  │
     │    ② SYN=1, ACK=1, Seq=y         │
     │       Ack=x+1                    │
     │ <─────────────────────────────── │
     │                                  │
     │       ③ ACK=1, Seq=x+1           │
     │       Ack=y+1                    │
     │ ───────────────────────────────> │
     │                                  │
     │        连接建立，开始传输数据      │
     ▼                                  ▼
```

**详细说明**：

| 步骤 | 方向 | 标志位 | Seq | Ack | 说明 | 内核状态变化 |
|------|------|--------|-----|-----|------|-------------|
| ① | C→S | SYN=1 | x | - | 客户端发起连接 | 客户端: CLOSED → SYN_SENT |
| ② | S→C | SYN=1, ACK=1 | y | x+1 | 服务器确认+响应 | 服务器: LISTEN → SYN_RECV |
| ③ | C→S | ACK=1 | x+1 | y+1 | 客户端确认 | 客户端: SYN_SENT → ESTABLISHED<br>服务器: SYN_RECV → ESTABLISHED |

#### 2.2 为什么需要三次？两次不够吗？

**两次握手的问题**：

```
场景：客户端发出的 SYN 在网络中滞留了很久
时间线：
T1: 客户端发送 SYN (seq=100) → 网络延迟
T2: 客户端超时重传 SYN (seq=101) → 连接正常建立并完成通信
T3: 连接关闭
T4: 滞留的旧 SYN (seq=100) 到达服务器

如果只有两次握手：
→ 服务器收到旧 SYN，回复 SYN+ACK → 连接建立
→ 但客户端并没有发起新连接，不会发送 ACK
→ 服务器维护了一个无效连接，浪费资源

三次握手的作用：
→ 服务器回复 SYN+ACK 后进入 SYN_RECV 状态
→ 客户端收到后不发 ACK（因为不是它发起的）
→ 服务器超时后自动关闭连接
→ 避免了历史连接引起的资源浪费
```

#### 2.3 三次握手中的 Seq/Ack 变化示例

```
客户端初始 Seq = 1000
服务器初始 Seq = 5000

① C→S: SYN=1, Seq=1000
② S→C: SYN=1, ACK=1, Seq=5000, Ack=1001   (1000+1)
③ C→S: ACK=1, Seq=1001, Ack=5001           (5000+1)

连接建立后发送数据：
④ C→S: ACK=1, Seq=1001, Ack=5001, Data[100字节]
⑤ S→C: ACK=1, Seq=5001, Ack=1101           (1001+100)
```

**注意**：SYN 和 FIN 各消耗一个序列号，纯 ACK 不消耗序列号。

### 3. 四次挥手（Four-Way Wavehand）

#### 3.1 完整过程

```
主动关闭方 (Client)               被动关闭方 (Server)
     │                                  │
     │   ① FIN=1, Seq=u                 │
     │ ───────────────────────────────> │
     │                                  │
     │   ② ACK=1, Seq=v, Ack=u+1        │
     │ <─────────────────────────────── │
     │                                  │
     │  ← 此时服务器可能还有数据要发送 →  │
     │  ← Client 进入 TIME_WAIT 等待 →  │
     │                                  │
     │   ③ FIN=1, ACK=1, Seq=w          │
     │       Ack=u+1                    │
     │ <─────────────────────────────── │
     │                                  │
     │   ④ ACK=1, Seq=u+1, Ack=w+1      │
     │ ───────────────────────────────> │
     │                                  │
     │  ← 等待 2MSL 后关闭 →            │
     ▼                                  ▼
```

**详细说明**：

| 步骤 | 方向 | 标志位 | 说明 | 状态变化 |
|------|------|--------|------|----------|
| ① | C→S | FIN=1 | 客户端发送完毕，请求关闭 | Client: ESTABLISHED → FIN_WAIT_1 |
| ② | S→C | ACK=1 | 服务器确认收到 FIN | Server: ESTABLISHED → CLOSE_WAIT<br>Client: FIN_WAIT_1 → FIN_WAIT_2 |
| ③ | S→C | FIN=1 | 服务器也发送完毕，请求关闭 | Server: CLOSE_WAIT → LAST_ACK |
| ④ | C→S | ACK=1 | 客户端确认收到 FIN | Server: LAST_ACK → CLOSED<br>Client: FIN_WAIT_2 → TIME_WAIT |

#### 3.2 为什么挥手需要四次？

因为 TCP 是全双工的，每一方向都需要独立关闭。

- 客户端发 FIN 只表示"我不再发送数据"，但仍可以接收数据
- 服务器收到 FIN 后，可能还有未发送完的数据
- 所以服务器先回复 ACK（第 ② 步），等数据发送完毕后再发 FIN（第 ③ 步）
- 如果服务器没有剩余数据，② 和 ③ 可能合并为一个包（此时看起来像三次）

#### 3.3 TIME_WAIT 详解

**为什么需要 TIME_WAIT？**

```
1. 确保最后一个 ACK 能到达服务器
   - 如果第 ④ 步的 ACK 丢失，服务器会重传 FIN（第 ③ 步）
   - 客户端在 TIME_WAIT 状态下可以重传 ACK
   - 如果客户端直接关闭，就无法回应重传的 FIN

2. 让旧连接的数据包在网络中消散
   - 防止旧连接的延迟数据包被新连接误接收
   - MSL (Maximum Segment Lifetime) = 数据包在网络中的最大存活时间
   - 2MSL = 一个来回的最大时间
   - Linux 默认 MSL = 60 秒 → 2MSL = 120 秒
   - Linux 实际 TIME_WAIT 超时 = 60 秒（内核优化）
```

**TIME_WAIT 过多导致的问题**：

```
问题 1：端口耗尽
- TIME_WAIT 占用本地端口（ephemeral port 范围：32768-60999）
- 最大约 28000 个连接
- 大量短连接场景下，端口耗尽 → 新连接失败

问题 2：内存占用
- 每个 TIME_WAIT 连接占用约 1KB 内核内存
- 10 万个 TIME_WAIT → 约 100MB 内核内存

检查命令：
ss -tan state time-wait | wc -l
cat /proc/sys/net/ipv4/tcp_max_tw_buckets
```

**TIME_WAIT 调优方案**：

```bash
# 1. 调整 TIME_WAIT 桶大小（默认 16384）
# /etc/sysctl.conf
net.ipv4.tcp_max_tw_buckets = 262144

# 2. 启用 TIME_WAIT 快速回收（谨慎使用）
net.ipv4.tcp_tw_recycle = 0  # 已废弃，NAT 环境下有问题

# 3. 启用 TIME_WAIT 重用（推荐）
net.ipv4.tcp_tw_reuse = 1    # 允许 TIME_WAIT socket 用于新的出站连接
                              # 前提：新连接的 Seq 号足够大

# 4. 调整 MSL（影响 TIME_WAIT 持续时间）
net.ipv4.tcp_fin_timeout = 60  # 默认 60 秒

# 5. 扩大 ephemeral port 范围
net.ipv4.ip_local_port_range = 1024 65535

# 应用配置
sudo sysctl -p
```

**注意**：`tcp_tw_recycle` 在 Linux 4.12+ 已被移除，因为它在 NAT 环境下会导致连接问题。推荐做法是使用 `tcp_tw_reuse` 或优化应用层连接管理（连接池）。

### 4. TCP 11 种连接状态

#### 4.1 状态总览

| 状态 | 全称 | 说明 | 持续时间 | 哪端会出现 |
|------|------|------|----------|-----------|
| LISTEN | 监听 | 服务器等待连接请求 | 持续 | 服务器 |
| SYN_SENT | 已发送 SYN | 客户端已发 SYN，等待回应 | 短暂（秒级） | 客户端 |
| SYN_RECV | 已收到 SYN | 服务器收到 SYN，已发回应 | 短暂 | 服务器 |
| ESTABLISHED | 已建立 | 连接已建立，正常传输数据 | 长 | 两端 |
| FIN_WAIT_1 | 等待 FIN 1 | 己方已发 FIN，等待对方 ACK | 短暂 | 主动关闭方 |
| FIN_WAIT_2 | 等待 FIN 2 | 已收到对方 ACK，等待对方 FIN | 可长可短 | 主动关闭方 |
| CLOSE_WAIT | 等待关闭 | 已收到对方 FIN，等待己方关闭 | **可长（问题）** | 被动关闭方 |
| CLOSING | 同时关闭 | 双方同时发 FIN | 短暂 | 两端 |
| LAST_ACK | 最后确认 | 己方已发 FIN，等待对方最终 ACK | 短暂 | 被动关闭方 |
| TIME_WAIT | 等待 2MSL | 已发最终 ACK，等待 2MSL | 60-120 秒 | 主动关闭方 |
| CLOSED | 已关闭 | 连接完全关闭 | - | 两端 |

#### 4.2 TCP 状态转换图（简化版）

```
                    ┌──────────┐
                    │  CLOSED  │
                    └────┬─────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
    │  LISTEN   │  │ SYN_SENT  │  │ SYN_RECV  │
    │ (服务器)  │  │ (客户端)  │  │ (服务器)  │
    └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
          │ 收到 SYN      │ 收到 SYN-ACK  │ 收到 ACK
          │ 发送 SYN-ACK   │              │
          └──────┬────────┘              │
                 │                       │
          ┌──────▼───────────────────────▼──────┐
          │           ESTABLISHED                │
          │         （数据传输中）                │
          └──┬──────────────────────┬────────────┘
             │ 发送 FIN             │ 收到 FIN
             │（主动关闭方）        │（被动关闭方）
      ┌──────▼──────┐       ┌──────▼──────┐
      │ FIN_WAIT_1  │       │ CLOSE_WAIT  │ ← ⚠️ SRE 重点
      └──────┬──────┘       └──────┬──────┘
             │ 收到 ACK            │ 应用程序 close()
             │                     │ 发送 FIN
      ┌──────▼──────┐       ┌──────▼──────┐
      │ FIN_WAIT_2  │       │ LAST_ACK    │
      └──────┬──────┘       └──────┬──────┘
             │ 收到 FIN            │ 收到 ACK
             │                     │
      ┌──────▼──────┐       ┌──────▼──────┐
      │ TIME_WAIT   │       │  CLOSED     │
      │ (等 2MSL)   │       └─────────────┘
      └──────┬──────┘
             │ 超时
      ┌──────▼──────┐
      │  CLOSED     │
      └─────────────┘
```

#### 4.3 用 ss 命令查看 TCP 状态

```bash
# 查看所有 TCP 连接状态
ss -tan

# 按状态统计连接数
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn
# 输出示例：
#   1500 ESTAB      ← 正常连接
#    230 LISTEN     ← 监听端口
#    156 TIME-WAIT  ← 等待关闭
#     45 CLOSE-WAIT ← ⚠️ 可能有问题
#      8 FIN-WAIT-2 ← 等待对方关闭

# 查看指定状态的连接
ss -tan state established
ss -tan state time-wait
ss -tan state close-wait

# 查看 CLOSE-WAIT 连接的详细信息（进程 + 端口）
ss -tanp state close-wait
# 输出包含进程名和 PID，直接定位问题应用

# 查看连接数的详细分布（按端口）
ss -tan state close-wait | awk '{print $4}' | cut -d: -f2 | sort | uniq -c | sort -rn
# 可以找出哪个端口对应的 close-wait 最多
```

### 5. CLOSE_WAIT 成因与排查

#### 5.1 CLOSE_WAIT 的本质

```
CLOSE_WAIT 的含义：
- 对端已经发送了 FIN（表示它不再发送数据）
- 本地内核已经回复了 ACK
- 但本地应用程序还没有调用 close() 关闭 socket
- 内核在等待应用程序关闭 socket → CLOSE_WAIT

这不是内核的问题，是应用程序的 bug！
```

#### 5.2 CLOSE_WAIT 过多导致的问题

```
问题链：
CLOSE_WAIT 过多
  → 每个连接占用一个文件描述符（FD）
  → FD 数量达到 ulimit -n 限制（通常 1024 或 65535）
  → 新连接无法创建（"Too many open files"）
  → 服务拒绝新的请求
  → 如果进程不断尝试分配内存处理这些连接
  → 可能触发 OOM Killer
```

#### 5.3 常见成因

| 场景 | 原因 | 解决方案 |
|------|------|----------|
| 异常未处理 | 捕获异常后未关闭连接 | 确保 finally/defer 中 close |
| 连接池泄露 | 从连接池获取连接后未归还 | 使用 try-with-resources / defer |
| 死锁/阻塞 | 线程阻塞在处理逻辑中，无法执行 close | 设置超时，修复死锁 |
| 逻辑错误 | 忘记在某个分支中关闭连接 | 代码审查，添加连接监控 |
| 异步回调 | 异步操作中丢失了 socket 引用 | 正确管理异步生命周期 |

### 6. TCP 拥塞控制

#### 6.1 拥塞控制算法

| 算法 | 年份 | 特点 | 适用场景 |
|------|------|------|----------|
| Reno | 1990 | 慢启动 + 拥塞避免 + 快重传 + 快恢复 | 经典算法，已逐渐淘汰 |
| Cubic | 2008 | 基于窗口大小而非 RTT 的增长函数 | Linux 默认（2.6.19+） |
| BBR | 2016 | 基于带宽和 RTT 建模，主动探测 | Google 推荐，高吞吐场景 |
| NewReno | 1996 | Reno 的改进版 | 历史意义 |

#### 6.2 Cubic 算法的四个阶段

```
拥塞窗口 (cwnd) 变化：

cwnd ↑
  │
  │          ┌── 慢启动（指数增长）
  │         ╱
  │        ╱
  │       ╱ ← 到达 ssthresh
  │      ╱
  │     ╱  ──── 拥塞避免（线性增长）
  │    ╱
  │   ╱   ← 丢包事件
  │  ╱╲   ──── 拥塞窗口减半
  │ ╱  ╲
  │╱    ╲  ──── Cubic 凹函数增长
  │      ╲        （快速恢复丢失的带宽）
  │       ╲
  │        ╲──── 接近上次最大值后进入凸函数
  │         ╲      （探索更大带宽）
  │          ╲
  └────────────────────→ 时间

关键参数：
- cwnd (congestion window): 拥塞窗口，发送方允许发送的最大数据量
- ssthresh (slow start threshold): 慢启动阈值
- rwnd (receive window): 接收窗口，接收方能接收的最大数据量
- 实际发送窗口 = min(cwnd, rwnd)
```

#### 6.3 查看和调整拥塞控制算法

```bash
# 查看当前系统支持的拥塞控制算法
sysctl net.ipv4.tcp_available_congestion_control
# 输出示例：reno cubic bbr

# 查看当前使用的算法
sysctl net.ipv4.tcp_congestion_control
# 输出示例：cubic

# 切换到 BBR（推荐用于高吞吐场景）
echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
sudo sysctl -p

# 验证 BBR 是否生效
sysctl net.ipv4.tcp_congestion_control
lsmod | grep tcp_bbr

# 查看每个连接的拥塞控制信息
ss -tanpi | head -20
# 输出中包含 cwnd（拥塞窗口）等信息
```

### 7. TCP KeepAlive 机制

#### 7.1 KeepAlive 的作用

```
问题：TCP 连接建立后，如果一端宕机或网络中断，另一端无法感知。
KeepAlive 的作用：定期发送探测包，确认连接是否存活。

注意：TCP KeepAlive 不同于应用层心跳！
- TCP KeepAlive 由内核管理，对应用透明
- 应用层心跳由应用程序自己实现
- 两者可以共存，各有用途
```

#### 7.2 KeepAlive 参数

```bash
# 查看当前 KeepAlive 参数
sysctl net.ipv4.tcp_keepalive_time     # 默认 7200 秒（2小时）
sysctl net.ipv4.tcp_keepalive_intvl    # 默认 75 秒
sysctl net.ipv4.tcp_keepalive_probes   # 默认 9 次

# 实际超时时间 = tcp_keepalive_time + tcp_keepalive_probes × tcp_keepalive_intvl
# = 7200 + 9 × 75 = 7875 秒 ≈ 2.2 小时

# 调整为更激进的设置（按需）
echo "net.ipv4.tcp_keepalive_time=600" >> /etc/sysctl.conf     # 10 分钟无数据开始探测
echo "net.ipv4.tcp_keepalive_intvl=30" >> /etc/sysctl.conf     # 每 30 秒探测一次
echo "net.ipv4.tcp_keepalive_probes=5" >> /etc/sysctl.conf     # 探测 5 次无回应则断开
sudo sysctl -p

# 总超时 = 600 + 5 × 30 = 750 秒 = 12.5 分钟
```

#### 7.3 KeepAlive 数据包示例

```
正常连接：无数据交换时静默

KeepAlive 探测：
Client                          Server
  │                                │
  │    ACK, Seq=100 (0 字节)       │  ← 探测包（窗口大小为 1）
  │ ────────────────────────────> │
  │                                │
  │    ACK, Seq=500, Ack=101       │  ← 正常回应
  │ <──────────────────────────── │

如果 Server 宕机：
Client                          Server (宕机)
  │                                │
  │    探测包 (无回应)              │
  │ ────────────────────────────> ✗
  │                                │
  │    探测包 (无回应)              │
  │ ────────────────────────────> ✗
  │       ... (5 次)               │
  │                                │
  │    内核关闭连接                 │
  │    应用层收到 read() = 0 或错误 │
```

### 8. 其他重要 TCP 机制

#### 8.1 滑动窗口与流量控制

```
发送方                                    接收方
┌────────────┐                      ┌────────────┐
│  已发送    │  ──── 数据流 ────→   │  已接收    │
│  未确认    │                      │  缓冲区    │
└────────────┘                      └────────────┘
      │                                   │
      │ ←──── 窗口大小 (rwnd) ──────→    │

窗口通告：接收方在每个 ACK 中告知发送方还能接收多少数据
发送窗口 = min(拥塞窗口 cwnd, 接收窗口 rwnd)
```

#### 8.2 Nagle 算法与 TCP_NODELAY

```
Nagle 算法：
- 目的：减少小数据包数量，提高网络效率
- 规则：如果有未确认的数据，缓存后续小数据直到 ACK 到达

副作用：可能引入延迟（40ms - 200ms）

禁用方法（应用程序层面）：
setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, 1)

SRE 场景：
- RPC 框架通常禁用 Nagle 以降低延迟
- 文件传输场景保持 Nagle 启用以提高吞吐
```

#### 8.3 TCP Fast Open (TFO)

```
传统握手：3 次握手 + 数据传输
TFO 握手：在 SYN 包中携带数据，减少 1 个 RTT

前提：客户端和服务器都支持 TFO，且之前已建立过连接

查看状态：
sysctl net.ipv4.tcp_fastopen
# 0=关闭, 1=作为客户端启用, 2=作为服务器启用, 3=两者都启用
```

---

## 🛠️ 实战练习

### 练习 1：用 ss 命令查看 TCP 状态统计

```bash
# 查看所有 TCP 连接及其状态
ss -tan

# 输出示例：
# State      Recv-Q Send-Q Local Address:Port    Peer Address:Port
# LISTEN     0      128    0.0.0.0:22            0.0.0.0:*
# ESTAB      0      0      192.168.1.100:22      192.168.1.50:54321
# TIME-WAIT  0      0      192.168.1.100:8080    10.0.0.5:12345

# 按状态统计数量
ss -tan | awk 'NR>1 {count[$1]++} END {for (s in count) printf "%-12s %d\n", s, count[s]}'
# 输出：
# ESTAB        156
# LISTEN       12
# TIME-WAIT    89
# CLOSE-WAIT   23

# 只统计数量（一行命令）
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn

# 查看 CLOSE-WAIT 的进程信息
ss -tanp state close-wait | head -20

# 查看 ESTABLISHED 连接数
ss -tan state established | wc -l

# 监控 TCP 状态变化（每秒刷新）
watch -n 1 'ss -tan | awk "NR>1 {print \$1}" | sort | uniq -c | sort -rn'
```

### 练习 2：用 sysctl 查看和调整 TCP 内核参数

```bash
# 查看所有 TCP 相关的内核参数
sysctl -a | grep tcp_

# 关键参数速查
echo "=== 连接相关 ==="
sysctl net.ipv4.tcp_max_syn_backlog      # SYN 队列大小
sysctl net.core.somaxconn                # 监听队列上限
sysctl net.ipv4.tcp_max_tw_buckets       # TIME_WAIT 最大数量

echo "=== 超时相关 ==="
sysctl net.ipv4.tcp_fin_timeout          # FIN_WAIT_2 超时
sysctl net.ipv4.tcp_keepalive_time       # KeepAlive 空闲时间
sysctl net.ipv4.tcp_keepalive_intvl      # KeepAlive 探测间隔
sysctl net.ipv4.tcp_keepalive_probes     # KeepAlive 探测次数

echo "=== 窗口相关 ==="
sysctl net.ipv4.tcp_rmem                 # 接收缓冲区 (min default max)
sysctl net.ipv4.tcp_wmem                 # 发送缓冲区 (min default max)
sysctl net.ipv4.tcp_window_scaling       # 窗口缩放

echo "=== 拥塞控制 ==="
sysctl net.ipv4.tcp_congestion_control   # 当前算法
sysctl net.ipv4.tcp_available_congestion_control  # 可用算法

echo "=== 端口相关 ==="
sysctl net.ipv4.ip_local_port_range      # 本地端口范围
sysctl net.ipv4.tcp_tw_reuse             # TIME_WAIT 重用
```

### 练习 3：模拟和观察 TCP 状态

```bash
# 在一个终端启动 HTTP 服务器
python3 -m http.server 8888 &

# 在另一个终端建立连接
curl http://localhost:8888/ &

# 快速查看连接状态
ss -tan | grep 8888
# 应该能看到 ESTAB 状态

# 停止服务器，观察状态变化
kill %1
ss -tan | grep 8888
# 可能看到 TIME-WAIT 或 CLOSE-WAIT

# 使用 nc 测试
nc -l -p 9999 &    # 监听 9999 端口
nc localhost 9999  # 建立连接

# 查看状态
ss -tan | grep 9999

# 关闭 nc 连接（Ctrl+C）
# 观察 TIME-WAIT 状态

# 清理
kill %1 %2 2>/dev/null
```

### 练习 4：诊断 CLOSE-WAIT 问题脚本

```bash
#!/bin/bash
# diagnose-close-wait.sh - 诊断 CLOSE_WAIT 问题

echo "=== CLOSE_WAIT 诊断 ==="
echo ""

# 统计 CLOSE_WAIT 数量
CLOSE_WAIT_COUNT=$(ss -tan state close-wait | wc -l)
echo "CLOSE_WAIT 连接数: $CLOSE_WAIT_COUNT"

if [ "$CLOSE_WAIT_COUNT" -gt 100 ]; then
    echo "⚠️ 警告: CLOSE_WAIT 数量过多!"
    echo ""
    echo "按进程统计:"
    ss -tanp state close-wait 2>/dev/null | \
        grep -oP 'users:\(\("\K[^"]+' | sort | uniq -c | sort -rn | head -10
    echo ""
    echo "按本地端口统计:"
    ss -tan state close-wait | awk 'NR>1 {print $4}' | \
        rev | cut -d: -f1 | rev | sort | uniq -c | sort -rn | head -10
else
    echo "✅ CLOSE_WAIT 数量正常"
fi

echo ""
echo "=== 文件描述符使用 ==="
# 查看系统级 FD 限制
echo "系统最大打开文件数: $(cat /proc/sys/fs/file-max)"
echo "当前已打开文件数: $(cat /proc/sys/fs/file-nr | awk '{print $1}')"
echo ""
echo "进程级 FD 使用 Top 10:"
ls /proc/*/fd 2>/dev/null | cut -d/ -f3 | \
    while read pid; do
        count=$(ls /proc/$pid/fd 2>/dev/null | wc -l)
        name=$(cat /proc/$pid/comm 2>/dev/null)
        [ -n "$name" ] && echo "$count $name (PID: $pid)"
    done | sort -rn | head -10

echo ""
echo "=== 诊断完成 ==="
```

---

## 🔍 SRE 实战案例：大量 CLOSE_WAIT 导致 OOM

### 场景描述

生产环境的 API 网关在高峰时段突然出现大量 502 错误，随后服务器被 OOM Killer 终止进程。

### 排查过程

```
时间线：
14:00  监控告警：API 网关 502 错误率飙升
14:02  SSH 登录服务器，发现服务已重启
14:05  检查系统日志，发现 OOM Killer 记录

dmesg | grep -i "oom-killer" | tail -5
# [14:03:22] Out of memory: Killed process 12345 (api-gateway)

14:10  重启服务后，问题暂时恢复

深入排查：
```

#### Step 1：检查 TCP 连接状态

```bash
# 查看 TCP 状态分布
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn
# 输出：
#   8500 CLOSE-WAIT    ← 🔴 异常！
#    230 ESTAB
#    156 TIME-WAIT
#     12 LISTEN

# 查看 CLOSE-WAIT 的进程
ss -tanp state close-wait | head -20
# 输出显示都是 api-gateway 进程（PID 12345）
```

#### Step 2：检查文件描述符

```bash
# 查看进程 FD 数量
ls /proc/12345/fd | wc -l
# 输出：8523  ← 接近 ulimit 限制

# 查看 ulimit 配置
cat /proc/12345/limits | grep "open files"
# 输出：Max open files            10000

# FD 使用率：8523/10000 = 85% ← 即将耗尽
```

#### Step 3：检查应用代码

```bash
# 查看应用日志
journalctl -u api-gateway --since "2 hours ago" | grep -i "error\|warn\|exception" | tail -20
# 发现大量 "connection reset by peer" 错误

# 查看代码（伪代码）
# 问题代码：
def handle_request(conn):
    try:
        data = conn.recv(4096)
        response = process(data)
        conn.sendall(response)
        # ❌ 缺少 conn.close() ！
    except Exception as e:
        log.error(f"Error: {e}")
        # ❌ 异常分支也没有关闭连接！

# 正确代码：
def handle_request(conn):
    try:
        data = conn.recv(4096)
        response = process(data)
        conn.sendall(response)
    except Exception as e:
        log.error(f"Error: {e}")
    finally:
        conn.close()  # ✅ 确保总是关闭
```

#### Step 4：根因分析

```
根因链条：
上游负载均衡器健康检查超时
  → 主动关闭了到 API 网关的连接（发送 FIN）
  → API 网关收到 FIN，内核回复 ACK
  → 但应用代码异常分支没有调用 close()
  → 连接停留在 CLOSE_WAIT 状态
  → 每个 CLOSE_WAIT 占用 1 个 FD
  → 连接持续累积，FD 耗尽
  → 新连接无法创建 → 502 错误
  → 进程持续分配内存 → OOM

修复方案：
1. 代码修复：确保所有代码路径都正确关闭连接
2. 连接超时：设置 socket 超时，避免无限等待
3. FD 限制：适当提高 ulimit，但治标不治本
4. 监控告警：添加 CLOSE_WAIT 数量告警阈值
```

#### Step 5：修复与预防

```python
# 修复后的代码（Python 示例）
import socket
import contextlib

def handle_request(conn):
    # 方法 1：使用 contextlib
    with contextlib.closing(conn):
        try:
            conn.settimeout(30)  # 设置超时
            data = conn.recv(4096)
            response = process(data)
            conn.sendall(response)
        except socket.timeout:
            log.warning("Connection timeout")
        except ConnectionResetError:
            log.warning("Connection reset by peer")
        except Exception as e:
            log.error(f"Unexpected error: {e}")

    # conn 在 with 块结束时自动关闭

# 方法 2：使用 try-finally
def handle_request_v2(conn):
    try:
        conn.settimeout(30)
        data = conn.recv(4096)
        response = process(data)
        conn.sendall(response)
    except Exception as e:
        log.error(f"Error: {e}")
    finally:
        try:
            conn.close()
        except:
            pass  # 忽略关闭时的异常
```

```bash
# 系统层面配置
# /etc/security/limits.conf
* soft nofile 65535
* hard nofile 65535

# /etc/sysctl.conf
net.ipv4.tcp_fin_timeout = 30          # 减少 FIN_WAIT_2 超时
net.ipv4.tcp_keepalive_time = 600      # 10 分钟无数据开始探测
net.ipv4.tcp_keepalive_intvl = 30      # 每 30 秒探测
net.ipv4.tcp_keepalive_probes = 5      # 5 次无回应断开
net.core.somaxconn = 4096              # 增大监听队列

sudo sysctl -p
```

#### Step 6：添加监控告警

```bash
# Prometheus 监控项
# tcp_connection_state{state="close_wait"}  ← 设置告警阈值

# 告警规则（Prometheus YAML）
groups:
  - name: tcp-alerts
    rules:
      - alert: HighCloseWait
        expr: sum(tcp_connection_state{state="close_wait"}) > 500
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "高 CLOSE_WAIT 连接数 ({{ $value }})"
          description: "可能存在连接泄露"

      - alert: CriticalCloseWait
        expr: sum(tcp_connection_state{state="close_wait"}) > 5000
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "大量 CLOSE_WAIT 连接 ({{ $value }})"
          description: "服务可能即将不可用"
```

### 经验总结

```
CLOSE_WAIT 是被动关闭方的状态
→ 对端已经关闭连接，本地还在等待应用程序关闭
→ 这不是内核的问题，是应用程序的 bug
→ 必须在代码中确保所有路径都正确 close()
→ Java 使用 try-with-resources
→ Python 使用 with / try-finally
→ Go 使用 defer conn.Close()

SRE 监控要点：
1. CLOSE_WAIT 数量监控 → 超过阈值告警
2. FD 使用率监控 → 超过 80% 告警
3. TCP 连接总数监控 → 异常增长告警
4. 应用层健康检查 → 快速发现连接问题
```

---

## 📚 最新优质资源

### 官方文档
- [RFC 793 - TCP Protocol Specification](https://datatracker.ietf.org/doc/html/rfc793) — TCP 协议原始规范
- [RFC 7323 - TCP Extensions for High Performance](https://datatracker.ietf.org/doc/html/rfc7323) — TCP 高性能扩展（窗口缩放、时间戳）
- [Linux TCP Documentation](https://www.kernel.org/doc/html/latest/networking/tcp.html) — Linux 内核 TCP 文档

### 推荐教程
- [TCP State Diagram](https://en.wikipedia.org/wiki/Transmission_Control_Protocol#Protocol_operation) — Wikipedia TCP 状态图
- [TCP 连接状态详解](https://www.cnblogs.com/f-ck-need-u/p/7503419.html) — 中文技术博客
- [Brendan Gregg - TCP Observability](https://www.brendangregg.com/blog/2017-03-08/tcp-observability.html) — 可观测性专家的博客

### 视频课程
- [Bilibili - TCP 三次握手四次挥手动画演示](https://www.bilibili.com/video/BV1gx411D7mP/) — 直观理解握手挥手过程
- [YouTube - TCP Congestion Control Explained](https://www.youtube.com/watch?v=U9HfN-3o36g) — 拥塞控制算法详解
- [Bilibili - TCP 状态机深入理解](https://www.bilibili.com/video/BV1KE411C7Bm/) — 状态转换完整讲解

### SRE 相关资源
- [Google BBR 拥塞控制](https://github.com/google/bbr) — Google 开源的 BBR 算法实现
- [Linux TCP Tuning Guide](https://github.com/leandromoreira/linux-network-performance-parameters) — 网络性能调优参数指南
- [Etsy's TCP Monitoring](https://codeascraft.com/) — Etsy 工程博客中的 TCP 监控实践

---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）
- 三次握手防止历史连接建立，四次挥手是因为全双工需要独立关闭
- TIME_WAIT 是主动关闭方的正常状态，过多时可通过 tw_reuse 和扩大端口范围优化
- CLOSE_WAIT 是被动关闭方的状态，表示应用程序未调用 close()，本质是代码 bug
- TCP 拥塞控制算法从 Cubic 向 BBR 演进，BBR 更适合高带宽场景
- KeepAlive 默认 2 小时太长，生产环境建议调整为 10-30 分钟
- TCP 状态监控是 SRE 的基本功，`ss` 命令比 `netstat` 更高效

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| TIME_WAIT 过多导致端口耗尽 | 启用 tcp_tw_reuse，扩大 ip_local_port_range |
| CLOSE_WAIT 累积 | 检查应用代码，确保所有路径都 close() |
| SYN Flood 攻击 | 启用 tcp_syncookies，增大 tcp_max_syn_backlog |
| BBR 不生效 | 确认内核版本 ≥ 4.9，设置 default_qdisc=fq |
| ss 命令输出太多 | 使用 awk/grep 过滤，或指定 state 参数 |

### 延伸思考

- 思考 1：在 Kubernetes 中，Pod 间的 TCP 连接经过哪些网络组件？Service 的 iptables/ipvs 模式如何影响 TCP 状态？
- 思考 2：为什么 HTTP/1.1 引入 Keep-Alive（持久连接）？它如何影响 TCP 连接的建立次数？
- 思考 3：如何区分正常的 TIME_WAIT 和异常的 CLOSE_WAIT？监控告警的阈值应该如何设置？

---

## ✅ 完成检查

- [ ] 理解 TCP 三次握手和四次挥手的完整过程
- [ ] 掌握 TCP 11 种连接状态及转换关系
- [ ] 理解 TIME_WAIT 的成因和调优方法
- [ ] 理解 CLOSE_WAIT 的成因（应用未 close）
- [ ] 理解 TCP 拥塞控制算法（Cubic、BBR）
- [ ] 理解 TCP KeepAlive 机制和参数调优
- [ ] 完成 ss 命令状态统计练习
- [ ] 完成 sysctl 参数查看和调整练习
- [ ] 理解 SRE 实战案例中的 CLOSE_WAIT → OOM 链路
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记

---

*由 SRE 学习计划自动生成 | 2026-04-30*
