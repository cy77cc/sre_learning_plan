# Day 30: TCP 协议详解 — 三次握手、四次挥手、状态机

> 📅 日期：2026-04-30
> 📖 学习主题：TCP 协议详解 — 三次握手、四次挥手、状态机
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 29 OSI 七层模型与 TCP/IP 协议栈

---

## 🎯 学习目标

完成 Day 30 的学习后，你应该掌握：
- 深入理解 TCP 报文结构中每个关键字段的含义和作用
- 掌握三次握手和四次挥手的完整过程，理解为什么是三次/四次
- 熟悉 TCP 11 种状态机的含义和转换条件
- 理解 TCP 拥塞控制（慢启动、拥塞避免、快重传、快恢复、BBR）
- 理解 TCP 流量控制（滑动窗口、窗口缩放）
- 掌握 TCP KeepAlive、Nagle 算法、TCP_NODELAY 等机制
- 能够在生产环境中诊断和解决 TCP 相关问题（CLOSE_WAIT、TIME_WAIT、重传）

---

## 📖 核心知识点

### 1. TCP 报文结构深入

#### 1.1 TCP 头部格式

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          源端口 (16)           |        目的端口 (16)           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        序列号 Sequence Number (32)              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    确认号 Acknowledgment Number (32)            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| 数据偏移(4) | 保留(3) |C|E|U|A|P|R|S|F|     窗口大小 (16)      |
|             |         |W|R|C|S|S|Y|I|                         |
|             |         |R|G|K|H|T|N|N|                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          校验和 (16)           |       紧急指针 (16)            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    选项 + 填充（可变长度）                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           数据（Payload）                       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

#### 1.2 关键字段详解

| 字段 | 大小 | 说明 | SRE 关注点 |
|------|------|------|-----------|
| 源端口 | 16 位 | 发送方端口号（0-65535） | 高并发时 ephemeral port 可能耗尽 |
| 目的端口 | 16 位 | 接收方端口号 | 确认服务监听端口是否正确 |
| 序列号 (Seq) | 32 位 | 本报文段数据第一个字节的序号 | 用于乱序重排和重传检测 |
| 确认号 (Ack) | 32 位 | 期望收到的下一个字节序号 | 确认对方已收到多少数据 |
| 数据偏移 | 4 位 | TCP 头部长度（32 位字为单位） | 最小 5（20 字节），最大 15（60 字节） |
| 控制位 (Flags) | 9 位 | CWR,ECE,URG,ACK,PSH,RST,SYN,FIN | 标志连接状态和控制信息 |
| 窗口大小 | 16 位 | 接收方还能接收的字节数 | 流量控制的核心，最大 65535 |
| 校验和 | 16 位 | 头部 + 数据 + 伪头部的校验 | 如果校验失败，包会被静默丢弃 |
| 紧急指针 | 16 位 | 紧急数据的末尾偏移 | URG=1 时有效，实际很少使用 |

#### 1.3 TCP 标志位详解

| 标志位 | 全称 | 位 | 含义 | 常见场景 | SRE 排查 |
|--------|------|-----|------|----------|----------|
| CWR | Congestion Window Reduced | 8 | 拥塞窗口已减小 | 拥塞控制响应 | 一般不需要关注 |
| ECE | ECN-Echo | 7 | ECN 回显，通知拥塞 | 显式拥塞通知 | 高级拥塞控制 |
| URG | Urgent | 6 | 紧急指针有效 | 紧急数据传输 | 极少使用 |
| ACK | Acknowledge | 5 | 确认号字段有效 | 几乎所有包（除 SYN） | ACK 丢失可能导致重传 |
| PSH | Push | 4 | 推送，立即交付数据 | 实时应用、交互式终端 | 减少缓冲延迟 |
| RST | Reset | 3 | 重置连接 | 端口未监听、连接异常 | 大量 RST 说明有问题 |
| SYN | Synchronize | 2 | 同步序列号 | 连接建立（握手） | SYN Flood 攻击 |
| FIN | Finish | 1 | 发送方数据完毕 | 连接关闭（挥手） | FIN_WAIT/CLOSE_WAIT |

#### 1.4 TCP 选项字段

```
常见的 TCP 选项：

1. MSS（Maximum Segment Size）- Kind 2, 长度 4 字节
   → 通告最大段大小，通常在 SYN 包中携带
   → MSS = MTU - IP 头部 - TCP 头部 = 1500 - 20 - 20 = 1460

2. Window Scale - Kind 3, 长度 3 字节
   → 窗口缩放因子（0-14）
   → 实际窗口 = 窗口大小 << 缩放因子
   → 只在 SYN/SYN-ACK 中协商

3. SACK Permitted - Kind 4, 长度 2 字节
   → 表示支持选择性确认
   → 只在 SYN 包中携带

4. SACK - Kind 5, 长度可变
   → 选择性确认，告知发送方哪些数据块已收到
   → 避免重传已收到的数据

5. Timestamps - Kind 8, 长度 10 字节
   → 用于精确计算 RTT
   → 防止序列号回绕（PAWS）

查看 TCP 选项：
tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0' -n -v
# 在 SYN 包的 options 中可以看到 mss, sackOK, wscale, timestamp
```

### 2. 三次握手（Three-Way Handshake）

#### 2.1 完整过程

```
客户端 (Client)                              服务器 (Server)
     │                                            │
     │  CLOSED                                    │  LISTEN
     │                                            │
     │  ① SYN=1, Seq=x                           │
     │  (客户端选择初始序列号 x)                    │
     │ ─────────────────────────────────────────> │
     │                                            │
     │  SYN_SENT                                  │  SYN_RECV
     │                                            │
     │  ② SYN=1, ACK=1, Seq=y, Ack=x+1           │
     │  (服务器选择初始序列号 y，确认 x+1)         │
     │ <───────────────────────────────────────── │
     │                                            │
     │  ESTABLISHED                               │
     │                                            │
     │  ③ ACK=1, Seq=x+1, Ack=y+1                │
     │  (确认 y+1，可以携带数据)                   │
     │ ─────────────────────────────────────────> │
     │                                            │
     │  ESTABLISHED                               │  ESTABLISHED
     │                                            │
     │  ← 开始双向数据传输 →                       │
```

**详细步骤分析**：

| 步骤 | 方向 | 标志位 | Seq | Ack | 数据量 | 内核状态变化 |
|------|------|--------|-----|-----|--------|-------------|
| ① SYN | C→S | SYN=1 | x | - | 0 | C: CLOSED→SYN_SENT; S: 收到后 LISTEN→SYN_RECV |
| ② SYN-ACK | S→C | SYN=1, ACK=1 | y | x+1 | 0 | S: 发送后保持 SYN_RECV |
| ③ ACK | C→S | ACK=1 | x+1 | y+1 | 0+ | C: SYN_SENT→ESTABLISHED; S: 收到后 SYN_RECV→ESTABLISHED |

**注意**：SYN 消耗一个序列号，纯 ACK 不消耗序列号。所以①后期望的 Ack 是 x+1，②后期望的 Ack 是 y+1。

#### 2.2 为什么是三次而不是两次？

```
两次握手的问题 —— 历史连接场景：

时间线：
T1: 客户端发送 SYN (seq=100)，但因网络延迟没有及时到达
T2: 客户端超时，重传 SYN (seq=200)，正常建立连接
T3: 客户端和服务器正常通信，然后关闭连接
T4: 之前滞留的 SYN (seq=100) 终于到达服务器

如果是两次握手：
  服务器收到旧 SYN (seq=100)
  → 服务器回复 SYN-ACK，连接直接建立
  → 服务器进入 ESTABLISHED 状态，开始等待数据
  → 但客户端并没有发起这个连接（它已经关闭了之前的连接）
  → 服务器维护了一个永远不会有数据的空闲连接
  → 浪费服务器资源（内存、文件描述符）

三次握手如何解决：
  服务器收到旧 SYN (seq=100)
  → 服务器回复 SYN-ACK，进入 SYN_RECV 状态
  → 客户端收到这个意外的 SYN-ACK，发现不是自己发起的连接
  → 客户端发送 RST（重置）拒绝这个连接
  → 服务器收到 RST，关闭连接
  → 避免了无效连接占用服务器资源

核心原因：三次握手让客户端有机会在第三步"否决"连接建立
```

#### 2.3 为什么不是四次？

```
三次握手已经足够完成两个目标：
1. 同步双方的初始序列号（ISN）
2. 确认双方的收发能力

① SYN：客户端告诉服务器自己的初始序列号
② SYN-ACK：服务器告诉客户端自己的初始序列号 + 确认收到了客户端的序列号
③ ACK：客户端确认收到了服务器的序列号

如果把第②步拆成两步（先 ACK 再 SYN），就变成了四次握手：
②a 服务器回复 ACK：确认收到客户端的 SYN
②b 服务器发送 SYN：同步自己的序列号
→ 这两步可以合并为一个 SYN-ACK 包
→ 所以三次就够了，不需要四次
```

#### 2.4 SYN Flood 攻击与防御

```
SYN Flood 攻击原理：

攻击者                          服务器
  │                                │
  │  SYN (伪造源 IP)               │
  │ ────────────────────────────> │
  │                                │  → 分配资源，放入 SYN 队列
  │  SYN (伪造另一个源 IP)         │  → 发送 SYN-ACK，等待 ACK
  │ ────────────────────────────> │
  │                                │  → 再分配资源...
  │  ... (每秒数万个 SYN)          │
  │                                │
  │                                │  SYN 队列溢出！
  │                                │  合法的 SYN 无法被处理
  │                                │  → 服务拒绝（DoS）

攻击特点：
1. 攻击者不完成三次握手（不发 ACK）
2. 使用伪造的源 IP 地址
3. SYN-ACK 发往伪造的 IP，永远收不到 ACK
4. 服务器的 SYN 队列（半连接队列）被耗尽

防御方法：

1. SYN Cookies（最有效）
   → 不在 SYN_RECV 时分配资源
   → 将连接信息编码到 SYN-ACK 的序列号中
   → 收到 ACK 时验证序列号，再分配资源
   → 启用：sysctl -w net.ipv4.tcp_syncookies=1

2. 增大 SYN 队列
   → sysctl -w net.ipv4.tcp_max_syn_backlog=65535
   → 增大半连接队列容量

3. 减少 SYN_RECV 超时
   → sysctl -w net.ipv4.tcp_synack_retries=2
   → 默认 5 次重试（约 63 秒），减少到 2 次（约 7 秒）

4. SYN Proxy（防火墙层面）
   → 防火墙代理三次握手
   → 验证连接合法性后再转发给服务器
   → 适用于：云服务商、CDN（如 Cloudflare）

5. 限制 SYN 速率
   → iptables -A INPUT -p tcp --syn -m limit --limit 100/s -j ACCEPT
   → iptables -A INPUT -p tcp --syn -j DROP
```

#### 2.5 三次握手的异常场景

```
异常 1：SYN-ACK 丢失
Client                         Server
  │  SYN ──────────────────>  │
  │                           │  → SYN_RECV
  │  SYN-ACK ─ ─ ─ ─ ─ ✗     │  ← 丢失！
  │                           │
  │  (客户端超时重传 SYN)      │
  │  SYN ──────────────────>  │
  │                           │  → 重新 SYN_RECV
  │  SYN-ACK ─────────────>   │
  │  ACK ──────────────────>  │
  │  ESTABLISHED              │  ESTABLISHED

异常 2：第三个 ACK 丢失
Client                         Server
  │  SYN ──────────────────>  │
  │  SYN-ACK <──────────────  │
  │  ACK ─ ─ ─ ─ ─ ─ ─ ✗     │  ← 丢失！
  │  ESTABLISHED              │  → 仍在 SYN_RECV
  │                           │
  │  (服务器超时重传 SYN-ACK)  │
  │  SYN-ACK <──────────────  │
  │  ACK ──────────────────>  │
  │  ESTABLISHED              │  ESTABLISHED

异常 3：客户端收到 SYN-ACK 后发送 RST
→ 当客户端没有发起连接却收到 SYN-ACK
→ 可能是历史连接的延迟包，或 IP 地址冲突
→ 客户端发送 RST 拒绝连接
```

### 3. 四次挥手（Four-Way Wavehand）

#### 3.1 完整过程

```
主动关闭方 (Client)                      被动关闭方 (Server)
     │                                        │
     │  ESTABLISHED                           │  ESTABLISHED
     │                                        │
     │  ① FIN=1, Seq=u                        │
     │  (我不再发送数据了)                      │
     │ ─────────────────────────────────────> │
     │                                        │
     │  FIN_WAIT_1                            │  → 收到 FIN
     │                                        │
     │  ② ACK=1, Seq=v, Ack=u+1               │
     │  (知道了，我可能还有数据要发)            │
     │ <───────────────────────────────────── │
     │                                        │
     │  FIN_WAIT_2                            │  CLOSE_WAIT
     │                                        │  → 应用程序处理剩余数据
     │                                        │  → 应用程序调用 close()
     │                                        │
     │  ③ FIN=1, ACK=1, Seq=w, Ack=u+1        │
     │  (我也不再发送数据了)                    │
     │ <───────────────────────────────────── │
     │                                        │
     │  → 收到 FIN                            │  LAST_ACK
     │                                        │
     │  ④ ACK=1, Seq=u+1, Ack=w+1             │
     │  (知道了，再见)                          │
     │ ─────────────────────────────────────> │
     │                                        │
     │  TIME_WAIT                             │  → 收到 ACK
     │  (等待 2MSL)                           │  CLOSED
     │                                        │
     │  (2MSL 超时)                           │
     │  CLOSED                                │
```

#### 3.2 为什么是四次而不是三次？

```
TCP 是全双工的，每个方向需要独立关闭：

1. 客户端发送 FIN：表示"我不再发送数据"
   → 但这只关闭了 客户端→服务器 方向
   → 客户端仍然可以接收数据

2. 服务器收到 FIN 后，可能还有数据要发送
   → 所以先回复 ACK（第②步），表示"知道了"
   → 继续发送剩余数据
   → 数据发送完毕后，发送 FIN（第③步）

3. 如果服务器没有剩余数据
   → 第②步（ACK）和第③步（FIN）可能合并为一个包
   → 此时看起来像"三次挥手"
   → 但这只是特殊情况，不是规范要求

为什么不能像握手一样合并？
→ 握手时服务器收到 SYN 后可以立即回复 SYN-ACK
→ 挥手时服务器收到 FIN 后不能立即关闭（可能还有数据要发）
→ ACK 和 FIN 的发送时机不同，通常无法合并
```

#### 3.3 TIME_WAIT 详解

```
TIME_WAIT 状态的含义：
→ 主动关闭方在发送最后一个 ACK 后进入 TIME_WAIT
→ 等待 2MSL（Maximum Segment Lifetime）后才关闭
→ Linux 默认 MSL = 60 秒，所以 2MSL = 120 秒
→ 实际 Linux 内核的 TIME_WAIT 超时约为 60 秒

TIME_WAIT 存在的两个原因：

1. 确保最后一个 ACK 能到达服务器
   ┌──────────────────────────────────────────────────┐
   │ 如果第④步的 ACK 丢失：                            │
   │ → 服务器收不到 ACK                                │
   │ → 服务器超时重传 FIN（第③步）                      │
   │ → 客户端在 TIME_WAIT 状态下可以重传 ACK            │
   │ → 如果客户端直接 CLOSED，无法回应重传的 FIN         │
   │ → 服务器会一直重传直到放弃，连接异常关闭            │
   └──────────────────────────────────────────────────┘

2. 让旧连接的延迟数据包在网络中消散
   ┌──────────────────────────────────────────────────┐
   │ 场景：同一个 (源IP, 源端口, 目的IP, 目的端口) 四元组│
   │ 旧连接的延迟数据包可能在新连接建立后才到达           │
   │ → TIME_WAIT 等待 2MSL 确保旧包已消亡               │
   │ → 防止旧数据被新连接误收                            │
   │ → MSL = 数据包在网络中的最大存活时间                │
   │ → 2MSL = 一个来回的最大时间                         │
   └──────────────────────────────────────────────────┘
```

**TIME_WAIT 过多的问题和解决方案**：

```
问题 1：端口耗尽
→ TIME_WAIT 连接占用本地端口（ephemeral port: 32768-60999）
→ 约 28000 个端口可用
→ 大量短连接场景下，端口耗尽 → 新连接失败

问题 2：内核内存占用
→ 每个 TIME_WAIT 连接约占 1KB 内核内存
→ 10 万个 TIME_WAIT ≈ 100MB

检查命令：
ss -tan state time-wait | wc -l
cat /proc/sys/net/ipv4/tcp_max_tw_buckets

解决方案（按优先级排序）：

1. 使用长连接（连接池）— 根本解决
   → 避免频繁创建和关闭短连接
   → HTTP Keep-Alive、gRPC 连接池

2. 启用 tcp_tw_reuse — 推荐
   → net.ipv4.tcp_tw_reuse = 1
   → 允许 TIME_WAIT socket 用于新的出站连接
   → 前提：新连接的序列号大于旧连接的最后序列号（基于时间戳）

3. 扩大 ephemeral port 范围
   → net.ipv4.ip_local_port_range = 1024 65535
   → 从 ~28000 扩大到 ~64000 个端口

4. 增大 tcp_max_tw_buckets
   → net.ipv4.tcp_max_tw_buckets = 262144
   → 允许更多 TIME_WAIT 连接存在

5. 调整 tcp_fin_timeout
   → net.ipv4.tcp_fin_timeout = 30
   → 减少 FIN_WAIT_2 的超时时间（间接影响）

注意：
→ tcp_tw_recycle 在 Linux 4.12+ 已移除！
→ 在 NAT 环境下会导致来自不同客户端的连接被拒绝
→ 不要使用 tcp_tw_recycle
```

#### 3.4 CLOSE_WAIT 详解

```
CLOSE_WAIT 的含义：
→ 被动关闭方收到对方的 FIN 后，内核自动回复 ACK
→ 但应用程序没有调用 close() 来关闭 socket
→ 连接停留在 CLOSE_WAIT 状态

CLOSE_WAIT 的本质：
→ 这不是内核的问题，是应用程序的 Bug！
→ 内核已经知道对方关闭了连接
→ 但应用程序没有处理这个事件（没有 close socket）

常见成因：
┌─────────────────────┬──────────────────────────────────────┐
│ 成因                  │ 说明                                  │
├─────────────────────┼──────────────────────────────────────┤
│ 异常处理遗漏          │ catch 块中没有 close()                │
│ 连接池泄露            │ 从连接池获取后未归还                   │
│ 死锁/阻塞            │ 线程阻塞在某个操作，无法执行 close()   │
│ 异步回调丢失          │ 异步操作中丢失了 socket 引用           │
│ 代码逻辑错误          │ 某个分支路径没有 close()               │
│ 资源泄露              │ 未使用 try-with-resources / defer     │
└─────────────────────┴──────────────────────────────────────┘

CLOSE_WAIT 的危害链：
CLOSE_WAIT 过多
  → 每个连接占用一个文件描述符（FD）
  → FD 达到 ulimit -n 限制
  → "Too many open files" 错误
  → 新连接无法创建
  → 服务不可用
```

#### 3.5 四次挥手的其他状态

```
FIN_WAIT_2 状态：
→ 主动关闭方收到 ACK 后进入
→ 等待对方发送 FIN
→ 如果对方长时间不发 FIN → FIN_WAIT_2 泄露
→ tcp_fin_timeout 控制 FIN_WAIT_2 的最大持续时间（默认 60 秒）

CLOSING 状态（同时关闭）：
→ 双方同时发送 FIN
→ 双方都进入 CLOSING 状态
→ 收到对方的 FIN 后发送 ACK
→ 进入 TIME_WAIT

Client A                      Client B
  │  FIN ──────────────────>  │
  │  FIN <─────────────────  │  (同时发送 FIN)
  │  ACK ──────────────────>  │
  │  ACK <─────────────────  │
  │  TIME_WAIT               │  TIME_WAIT

LAST_ACK 状态：
→ 被动关闭方发送 FIN 后进入
→ 等待对方的最终 ACK
→ 收到 ACK 后进入 CLOSED
```

### 4. TCP 11 种状态机详解

#### 4.1 状态总览

| 状态 | 方向 | 含义 | 持续时间 | 常见问题 |
|------|------|------|----------|----------|
| CLOSED | - | 连接不存在（初始/最终状态） | - | - |
| LISTEN | 服务器 | 等待客户端的连接请求 | 持续 | 端口未监听导致 Connection Refused |
| SYN_SENT | 客户端 | 已发送 SYN，等待 SYN-ACK | 短暂（秒级） | 超时说明网络不通或服务未启动 |
| SYN_RECV | 服务器 | 已收到 SYN，已发 SYN-ACK，等待 ACK | 短暂 | 过多可能是 SYN Flood 攻击 |
| ESTABLISHED | 双方 | 连接已建立，可以双向传输数据 | 长 | 正常状态 |
| FIN_WAIT_1 | 主动关闭方 | 已发送 FIN，等待 ACK | 短暂 | 长时间存在说明 FIN 丢失或对方不回 ACK |
| FIN_WAIT_2 | 主动关闭方 | 已收到 ACK，等待对方 FIN | 中等 | 长时间存在可能是对方不调用 close() |
| CLOSE_WAIT | 被动关闭方 | 已收到对方 FIN，等待己方 close() | 可长 | 过多 = 应用 Bug（未 close socket） |
| CLOSING | 双方 | 双方同时发送 FIN | 短暂 | 罕见，同时关闭场景 |
| LAST_ACK | 被动关闭方 | 已发送 FIN，等待最终 ACK | 短暂 | ACK 丢失会导致重传 FIN |
| TIME_WAIT | 主动关闭方 | 已发送最终 ACK，等待 2MSL | 60 秒 | 过多导致端口耗尽 |

#### 4.2 完整状态转换图

```
                              ┌──────────┐
                              │  CLOSED  │
                              └────┬─────┘
                                   │
                    ┌──────────────┼──────────────────┐
                    │ 被动打开       │ 主动打开           │ 主动打开
                    │ (listen)      │ (connect)         │ 收到 SYN
              ┌─────▼─────┐  ┌─────▼─────┐       ┌─────▼─────┐
              │  LISTEN   │  │ SYN_SENT  │       │ SYN_RECV  │
              │           │  │           │       │           │
              └─────┬─────┘  └─────┬─────┘       └─────┬─────┘
                    │ 收到 SYN      │ 收到 SYN-ACK       │ 收到 ACK
                    │ 发 SYN-ACK    │ 发 ACK             │
                    └───────┬───────┘                    │
                            │                            │
                     ┌──────▼────────────────────────────▼──────┐
                     │               ESTABLISHED                 │
                     │            （数据双向传输中）               │
                     └──┬──────────────┬──────────────┬─────────┘
                        │ 主动关闭      │ 收到 FIN      │ 同时关闭
                        │ 发送 FIN      │ 发送 ACK      │ 发送 FIN
                 ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
                 │ FIN_WAIT_1  │ │ CLOSE_WAIT  │ │  CLOSING    │
                 └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                        │ 收到 ACK      │ 应用 close()   │ 收到 ACK
                        │              │ 发送 FIN       │
                 ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
                 │ FIN_WAIT_2  │ │ LAST_ACK    │ │ TIME_WAIT   │
                 └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                        │ 收到 FIN      │ 收到 ACK       │ 2MSL 超时
                        │ 发送 ACK      │               │
                 ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
                 │ TIME_WAIT   │ │  CLOSED     │ │  CLOSED     │
                 └──────┬──────┘ └─────────────┘ └─────────────┘
                        │ 2MSL 超时
                 ┌──────▼──────┐
                 │  CLOSED     │
                 └─────────────┘
```

#### 4.3 用 ss 命令监控 TCP 状态

```bash
# 查看所有 TCP 连接状态
ss -tan

# 按状态统计连接数
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn
# 输出示例：
#   1500 ESTAB
#    230 LISTEN
#    156 TIME-WAIT
#     45 CLOSE-WAIT   ← ⚠️ 需要关注
#      8 FIN-WAIT-2

# 查看指定状态的连接详情
ss -tanp state close-wait
# -p 显示进程信息（PID 和进程名）

# 查看 CLOSE_WAIT 的进程分布
ss -tanp state close-wait | awk 'NR>1 {print $NF}' | sort | uniq -c | sort -rn

# 查看 TIME_WAIT 的目标端口分布
ss -tan state time-wait | awk 'NR>1 {print $4}' | rev | cut -d: -f1 | rev | sort | uniq -c | sort -rn

# 实时监控 TCP 状态变化（每 2 秒刷新）
watch -n 2 'ss -tan | awk "NR>1 {print \$1}" | sort | uniq -c | sort -rn'

# 查看 Recv-Q 和 Send-Q（判断是否有请求积压）
ss -tln
# Recv-Q: 接收队列中等待 accept 的连接数
# Send-Q: 监听队列的最大长度
# 如果 Recv-Q 接近 Send-Q，说明 accept 太慢
```

### 5. TCP 拥塞控制

#### 5.1 拥塞控制概述

```
为什么需要拥塞控制？
→ 如果发送方不控制发送速率，可能导致网络拥塞
→ 拥塞 → 丢包 → 重传 → 更多数据 → 更严重拥塞 → 拥塞崩溃（Congestion Collapse）
→ 拥塞控制的目的是探测网络容量，避免拥塞

拥塞控制的核心变量：
→ cwnd (Congestion Window): 拥塞窗口，发送方维护
→ rwnd (Receive Window): 接收窗口，接收方通告
→ ssthresh (Slow Start Threshold): 慢启动阈值
→ 实际发送窗口 = min(cwnd, rwnd)
```

#### 5.2 经典拥塞控制算法（Reno/Cubic）

```
四个阶段：

1. 慢启动（Slow Start）
   → cwnd 从 1 MSS 开始
   → 每收到一个 ACK，cwnd += 1 MSS（指数增长）
   → 每个 RTT，cwnd 翻倍
   → 直到 cwnd >= ssthresh

2. 拥塞避免（Congestion Avoidance）
   → cwnd >= ssthresh 后进入
   → 每个 RTT，cwnd += 1 MSS（线性增长）
   → 缓慢探测更大带宽
   → 直到检测到丢包

3. 快重传（Fast Retransmit）
   → 收到 3 个重复 ACK → 立即重传丢失的包
   → 不等待超时（超时通常需要 RTO ≈ 200ms+）
   → 3 个重复 ACK 说明网络只是轻微丢包

4. 快恢复（Fast Recovery）
   → ssthresh = cwnd / 2
   → cwnd = ssthresh + 3 MSS
   → 直接进入拥塞避免阶段（而非慢启动）

cwnd 变化示意：
cwnd ↑
  │        慢启动（指数增长）
  │       ╱
  │      ╱
  │     ╱ ← ssthresh
  │    ╱  ─────── 拥塞避免（线性增长）
  │   ╱
  │  ╱  ← 丢包事件（3 个重复 ACK）
  │ ╱ ╲
  │╱   ╲────── 拥塞避免（cwnd = ssthresh）
  │     ╲
  │      ╲ ← 又一次丢包
  │       ╲
  └────────────────→ 时间
```

#### 5.3 Cubic 算法（Linux 默认）

```
Cubic（2008 年）是 Linux 2.6.19+ 的默认算法：

与 Reno 的区别：
→ Reno 基于 AIMD（加法增乘法减），恢复速度慢
→ Cubic 基于三次函数（W(t) = C(t-K)^3 + Wmax），恢复更快

Cubic 的三个阶段：
1. 慢启动（与 Reno 相同）
2. 凹函数增长：快速恢复到上次丢包前的窗口大小
3. 凸函数增长：超过上次最大值后缓慢探测更大窗口

Cubic 的优势：
→ 在高带宽长延迟网络（BDP 大）中表现更好
→ 更公平：多个 Cubic 流共享带宽时更均衡
→ 恢复快：丢包后能快速恢复到之前的发送速率
```

#### 5.4 BBR 算法（Google 推荐）

```
BBR（Bottleneck Bandwidth and Round-trip propagation time）：
→ Google 2016 年提出，2017 年合入 Linux 4.9 内核
→ 不同于基于丢包的 Cubic，BBR 基于带宽和 RTT 建模

BBR 的核心思想：
→ 估计瓶颈链路的带宽（BtlBw）和最小 RTT（RTprop）
→ 发送速率 = BtlBw × RTprop
→ 主动探测，而非被动等待丢包

BBR 的两个阶段：
1. Startup：类似慢启动，快速找到瓶颈带宽
2. Drain：排空队列中的数据
3. ProbeBW：周期性探测更大带宽（每 8 个 RTT）
4. ProbeRTT：周期性测量最小 RTT（每 10 秒）

BBR vs Cubic：
┌────────────────┬───────────────┬──────────────────┐
│ 特性            │ Cubic          │ BBR               │
├────────────────┼───────────────┼──────────────────┤
│ 拥塞信号        │ 丢包           │ 带宽和 RTT 估计    │
│ 恢复速度        │ 较快           │ 更快              │
│ 高带宽利用率    │ 中等           │ 高                │
│ 公平性          │ 较好           │ 需要改进          │
│ 适用场景        │ 通用           │ 高带宽长延迟       │
│ 部署风险        │ 低             │ 中（需要测试）     │
└────────────────┴───────────────┴──────────────────┘
```

#### 5.5 查看和调整拥塞控制算法

```bash
# 查看当前支持的算法
sysctl net.ipv4.tcp_available_congestion_control
# 输出：reno cubic bbr

# 查看当前使用的算法
sysctl net.ipv4.tcp_congestion_control
# 输出：cubic

# 切换到 BBR
echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
sudo sysctl -p

# 验证 BBR 生效
sysctl net.ipv4.tcp_congestion_control
# 输出：bbr
lsmod | grep tcp_bbr
# 输出：tcp_bbr  20480  1

# 为特定连接指定算法（应用程序层面）
# 使用 setsockopt(TCP_CONGESTION, "bbr")
# 或通过 ip route:
ip route add default via 192.168.1.1 dev eth0 congctl bbr

# 查看连接的拥塞控制信息
ss -tanpi | grep ESTAB | head -5
# 输出中包含 cwnd（拥塞窗口）等信息
```

### 6. TCP 流量控制

#### 6.1 滑动窗口机制

```
滑动窗口的四个区域：

发送方视角：
┌─────────────────────────────────────────────────────────┐
│  已发送并确认  │ 已发送未确认  │  可以发送    │  不能发送   │
│  (Acked)      │ (Sent)       │  (Usable)    │ (Not Usable)│
│               │              │              │             │
│  ◄────────────┼──────────────┼──────────────┼─────────────►
│               │              │              │             │
│               │ ◄── 发送窗口 (cwnd) ──►     │             │
│               │    ◄── 有效窗口 (min(cwnd,rwnd)) ──►     │
└─────────────────────────────────────────────────────────┘

窗口滑动过程：
1. 发送数据 → "已发送未确认" 区域向右扩展
2. 收到 ACK → "已发送并确认" 区域向右扩展（窗口右移）
3. 接收方通告新窗口大小 → "可以发送" 区域调整

窗口大小为 0 的情况：
→ 接收方缓冲区满，通告窗口大小为 0
→ 发送方停止发送数据
→ 发送方定期发送"窗口探测"包（Window Probe）
→ 直到接收方通告非零窗口
```

#### 6.2 窗口缩放（Window Scale）

```
问题：TCP 头部的窗口大小字段只有 16 位，最大 65535 字节
→ 对于高带宽长延迟网络（BDP 大），64KB 窗口太小
→ 例如：100 Mbps × 100 ms = 1.25 MB，需要远大于 64KB 的窗口

Window Scale 选项（RFC 7323）：
→ 在 SYN/SYN-ACK 中协商缩放因子（0-14）
→ 实际窗口 = 窗口大小字段 << 缩放因子
→ 最大窗口 = 65535 × 2^14 = 1,073,725,440 字节 ≈ 1 GB

协商过程：
Client SYN:  Window Scale = 7 (2^7 = 128)
Server SYN-ACK: Window Scale = 8 (2^8 = 256)
→ 后续通信中，Client 发送的窗口大小 × 128
→ Server 发送的窗口大小 × 256

查看窗口缩放：
sysctl net.ipv4.tcp_window_scaling
# 1 = 启用（默认）

# 查看连接的窗口信息
ss -tanpi | grep ESTAB | head -5
```

#### 6.3 TCP 缓冲区调优

```bash
# 接收缓冲区（min, default, max）
sysctl net.ipv4.tcp_rmem
# 默认：4096 131072 6291456
# → 最小 4KB，默认 128KB，最大 6MB

# 发送缓冲区（min, default, max）
sysctl net.ipv4.tcp_wmem
# 默认：4096 16384 4194304
# → 最小 4KB，默认 16KB，最大 4MB

# 全局网络缓冲区
sysctl net.core.rmem_max         # 接收缓冲区最大值
sysctl net.core.wmem_max         # 发送缓冲区最大值
sysctl net.core.rmem_default     # 接收缓冲区默认值
sysctl net.core.wmem_default     # 发送缓冲区默认值
sysctl net.core.optmem_max       # 辅助缓冲区最大值

# 高带宽长延迟网络的调优建议
# BDP = 带宽 × RTT
# 例如：1 Gbps × 50 ms = 6.25 MB
echo "net.ipv4.tcp_rmem = 4096 87380 16777216" >> /etc/sysctl.conf
echo "net.ipv4.tcp_wmem = 4096 87380 16777216" >> /etc/sysctl.conf
echo "net.core.rmem_max = 16777216" >> /etc/sysctl.conf
echo "net.core.wmem_max = 16777216" >> /etc/sysctl.conf
sudo sysctl -p
```

### 7. TCP KeepAlive 机制

#### 7.1 KeepAlive 工作原理

```
问题场景：
→ TCP 连接建立后，如果一端宕机或网络中断
→ 另一端无法感知连接已断开
→ 连接一直存在，占用资源
→ 直到尝试发送数据时才发现连接已死

TCP KeepAlive 的作用：
→ 定期发送探测包（空 ACK，序列号 = 已发送序列号 - 1）
→ 确认连接是否仍然存活
→ 如果对端无响应，经过多次探测后关闭连接

探测过程：
Client                          Server (存活)
  │  ACK (KeepAlive) ────────>  │
  │  ACK (正常响应) <────────── │
  │  (连接正常，继续等待)        │

Client                          Server (宕机)
  │  ACK (KeepAlive) ────────>  ✗
  │  (等待 intvl 秒)            │
  │  ACK (KeepAlive) ────────>  ✗
  │  (等待 intvl 秒)            │
  │  ... (重复 probes 次)       │
  │  连接关闭                    │
```

#### 7.2 KeepAlive 参数

```bash
# 查看当前 KeepAlive 参数
sysctl net.ipv4.tcp_keepalive_time     # 默认 7200 秒（2 小时）
sysctl net.ipv4.tcp_keepalive_intvl    # 默认 75 秒
sysctl net.ipv4.tcp_keepalive_probes   # 默认 9 次

# 计算实际超时时间
# 超时 = tcp_keepalive_time + tcp_keepalive_probes × tcp_keepalive_intvl
# = 7200 + 9 × 75 = 7875 秒 ≈ 2.2 小时

# 生产环境建议调优
echo "net.ipv4.tcp_keepalive_time=600" >> /etc/sysctl.conf    # 10 分钟
echo "net.ipv4.tcp_keepalive_intvl=30" >> /etc/sysctl.conf    # 30 秒间隔
echo "net.ipv4.tcp_keepalive_probes=5" >> /etc/sysctl.conf    # 5 次探测
sudo sysctl -p
# 超时 = 600 + 5 × 30 = 750 秒 = 12.5 分钟
```

#### 7.3 TCP KeepAlive vs HTTP Keep-Alive

```
┌──────────────────┬────────────────────┬────────────────────────┐
│ 特性              │ TCP KeepAlive       │ HTTP Keep-Alive         │
├──────────────────┼────────────────────┼────────────────────────┤
│ 层级              │ 传输层（L4）        │ 应用层（L7）            │
│ 作用              │ 检测连接存活        │ 复用 TCP 连接            │
│ 实现              │ 内核自动            │ HTTP 头部控制            │
│ 默认行为          │ 默认关闭（需配置）  │ HTTP/1.1 默认开启        │
│ 探测包            │ 空 ACK             │ 无（靠请求复用）         │
│ 对应用的影响      │ 应用无感知          │ 应用可以控制             │
│ 超时检测          │ 可以检测死连接      │ 不检测连接存活           │
│ 典型配置          │ 600s / 30s / 5次   │ Keep-Alive: timeout=5   │
└──────────────────┴────────────────────┴────────────────────────┘

两者可以共存，互不干扰：
→ TCP KeepAlive 在内核层面检测死连接
→ HTTP Keep-Alive 在应用层面复用连接
→ 建议：两者都启用
```

### 8. Nagle 算法和 TCP_NODELAY

#### 8.1 Nagle 算法

```
Nagle 算法的目的：减少网络中小数据包的数量

规则：
1. 如果有未确认的数据在传输中，缓存后续小数据直到 ACK 到达
2. 如果累积数据达到 MSS 大小，立即发送
3. 如果没有未确认的数据，立即发送第一个小包

效果：
→ 将多个小写入合并为一个大包
→ 减少网络中小包的数量
→ 提高网络效率

副作用：引入延迟
→ 小数据包需要等待前面数据的 ACK 才能发送
→ 在低延迟场景（如游戏、SSH）中，40ms-200ms 的延迟不可接受

应用场景：
┌─────────────────┬──────────────┬──────────────────────────┐
│ 场景              │ Nagle 算法    │ 原因                      │
├─────────────────┼──────────────┼──────────────────────────┤
│ 文件传输          │ 启用          │ 吞吐量优先，延迟不敏感     │
│ HTTP 请求体       │ 启用          │ 大块数据，小包合并有益     │
│ RPC / gRPC       │ 禁用          │ 延迟敏感，小请求快速发送   │
│ 游戏             │ 禁用          │ 实时性要求极高             │
│ SSH              │ 禁用          │ 交互式终端，击键需要即时回显│
│ 数据库查询        │ 禁用          │ 查询小，结果需要快速返回   │
└─────────────────┴──────────────┴──────────────────────────┘
```

#### 8.2 TCP_NODELAY 和 TCP_CORK

```bash
# 禁用 Nagle 算法（应用程序层面）
setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &opt, sizeof(opt))
# 效果：数据立即发送，不等待 ACK

# TCP_CORK（Linux 特有）：
setsockopt(fd, IPPROTO_TCP, TCP_CORK, &opt, sizeof(opt))
# 效果：累积数据直到达到 MSS 或 200ms 超时
# 比 Nagle 更激进的合并策略
# 适合：sendfile() 场景，先发头部再发文件内容

# 查看连接是否启用了 TCP_NODELAY
ss -tanpi | grep ESTAB | head -5
# 输出中会显示 tcp_nodelay 标志

# RPC 框架的典型配置：
# gRPC: 默认启用 TCP_NODELAY
# Thrift: 默认启用 TCP_NODELAY
# HTTP/2: 默认启用 TCP_NODELAY
```

### 9. TCP Fast Open (TFO)

```
传统 TCP 连接：
→ 三次握手（1 RTT）→ 数据传输（1 RTT）= 至少 2 RTT

TCP Fast Open：
→ 首次连接：正常三次握手，服务器生成 Cookie
→ 后续连接：在 SYN 包中携带数据 + Cookie
→ 服务器验证 Cookie 后直接处理数据
→ 省去了 1 个 RTT 的等待时间

Client                              Server
  │  SYN + Cookie + Data ───────>  │
  │  (首次连接需要正常握手获取 Cookie)
  │                                │  验证 Cookie
  │  SYN-ACK + Data <──────────── │  直接处理数据
  │  ACK + Data ─────────────────> │
  │                                │
  → 总共 1 RTT 就完成了连接建立和数据传输

启用 TFO：
sysctl net.ipv4.tcp_fastopen
# 0 = 关闭
# 1 = 作为客户端启用
# 2 = 作为服务器启用
# 3 = 客户端和服务器都启用
echo "net.ipv4.tcp_fastopen=3" >> /etc/sysctl.conf
```

### 10. TCP 重传机制

```
TCP 重传的两种触发方式：

1. 超时重传（RTO, Retransmission Timeout）
   → 发送数据后启动定时器
   → RTO 动态计算（基于 RTT 测量）
   → 如果 RTO 内没收到 ACK → 重传
   → RTO 通常 200ms-数秒
   → 问题：等待时间长，影响延迟

2. 快重传（Fast Retransmit）
   → 收到 3 个重复 ACK → 立即重传
   → 不等待超时
   → 3 个重复 ACK 说明后续数据已到达，只是中间丢了
   → 通常在几十毫秒内触发

SACK（选择性确认）：
→ 接收方在 ACK 中携带已收到的不连续数据块
→ 发送方只重传缺失的数据块
→ 避免重传已收到的数据
→ 例如：收到 [1-1000] 和 [3001-5000]，缺 [1001-3000]
→ SACK: [1-1000, 3001-5000]，发送方只重传 [1001-3000]

RTO 计算（RFC 6298）：
SRTT = (1 - α) × SRTT + α × RTT_sample    (α = 1/8)
RTTVAR = (1 - β) × RTTVAR + β × |SRTT - RTT_sample| (β = 1/4)
RTO = SRTT + max(G, 4 × RTTVAR)
其中 G 是时钟粒度

首次 RTO：1 秒（未测量 RTT 前的保守值）
最小 RTO：200 ms（Linux 默认）
最大 RTO：120 秒（Linux 默认）

查看重传统计：
netstat -s | grep -i retransmit
# TcpExtTCPSlowStartRetransTCPSynRetrans
# TcpExtTCPLostRetransmit

# 或使用 ss 查看重传信息
ss -tanpi | grep ESTAB | head -5
# 输出中包含 retrans 相关信息
```

---

## 💻 实战练习

### 练习 1：用 ss 命令监控 TCP 状态

```bash
# 查看所有 TCP 连接状态统计
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn

# 查看监听端口和队列
ss -tln
# Recv-Q: 等待 accept 的连接数
# Send-Q: 监听队列最大长度

# 查看 CLOSE_WAIT 的详细信息
ss -tanp state close-wait

# 查看 TIME_WAIT 的数量
ss -tan state time-wait | wc -l

# 监控 TCP 状态实时变化
watch -n 1 'ss -tan | awk "NR>1 {print \$1}" | sort | uniq -c | sort -rn'

# 查看连接的详细信息（包括窗口大小、拥塞窗口等）
ss -tanpi state established | head -20
```

### 练习 2：用 tcpdump 观察三次握手和四次挥手

```bash
# 终端 1：启动 HTTP 服务器
python3 -m http.server 8888 &

# 终端 2：抓包
sudo tcpdump -i lo port 8888 -n -v

# 终端 3：发送请求
curl http://localhost:8888/

# 观察 tcpdump 输出：
# 1. SYN:       Flags [S], seq ...
# 2. SYN-ACK:   Flags [S.], seq ..., ack ...
# 3. ACK:       Flags [.], ack ...
# 4. HTTP GET:  Flags [P.], seq ..., ack ... (PSH+ACK)
# 5. HTTP 200:  Flags [P.], seq ..., ack ...
# 6. FIN-ACK:   Flags [F.], seq ..., ack ...
# 7. ACK:       Flags [.], ack ...

# 清理
kill %1
```

### 练习 3：查看和调整 TCP 内核参数

```bash
# 查看所有 TCP 相关参数
sysctl -a | grep tcp_ | sort

# 关键参数分类查看
echo "=== 连接队列 ==="
sysctl net.core.somaxconn
sysctl net.ipv4.tcp_max_syn_backlog

echo "=== TIME_WAIT ==="
sysctl net.ipv4.tcp_max_tw_buckets
sysctl net.ipv4.tcp_tw_reuse
sysctl net.ipv4.tcp_fin_timeout

echo "=== KeepAlive ==="
sysctl net.ipv4.tcp_keepalive_time
sysctl net.ipv4.tcp_keepalive_intvl
sysctl net.ipv4.tcp_keepalive_probes

echo "=== 缓冲区 ==="
sysctl net.ipv4.tcp_rmem
sysctl net.ipv4.tcp_wmem

echo "=== 拥塞控制 ==="
sysctl net.ipv4.tcp_congestion_control
sysctl net.ipv4.tcp_available_congestion_control

echo "=== 端口范围 ==="
sysctl net.ipv4.ip_local_port_range
```

### 练习 4：诊断 CLOSE_WAIT 问题脚本

```bash
#!/bin/bash
# diagnose-tcp-states.sh - TCP 状态诊断脚本

echo "========================================="
echo "  TCP 连接状态诊断"
echo "========================================="
echo ""

# TCP 状态统计
echo "[1] TCP 状态分布:"
echo "-----------------------------------------"
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn | \
    while read count state; do
        case "$state" in
            CLOSE-WAIT)
                if [ "$count" -gt 100 ]; then
                    echo "  🔴 $state: $count (异常！可能存在连接泄露)"
                else
                    echo "  $state: $count"
                fi
                ;;
            TIME-WAIT)
                if [ "$count" -gt 10000 ]; then
                    echo "  🟡 $state: $count (过多，检查短连接场景)"
                else
                    echo "  $state: $count"
                fi
                ;;
            *)
                echo "  $state: $count"
                ;;
        esac
    done

echo ""
echo "[2] CLOSE_WAIT 详情:"
echo "-----------------------------------------"
CW_COUNT=$(ss -tan state close-wait | wc -l)
if [ "$CW_COUNT" -gt 0 ]; then
    echo "  CLOSE_WAIT 连接的进程分布:"
    ss -tanp state close-wait 2>/dev/null | \
        grep -oP 'users:\(\("\K[^"]+' | sort | uniq -c | sort -rn | head -5
else
    echo "  无 CLOSE_WAIT 连接"
fi

echo ""
echo "[3] 监听队列状态:"
echo "-----------------------------------------"
ss -tln | awk 'NR>1 {
    if ($2 > $3 * 0.8) {
        printf "  ⚠️ %s: Recv-Q=%s/%s (队列接近满！)\n", $4, $2, $3
    } else {
        printf "  ✅ %s: Recv-Q=%s/%s\n", $4, $2, $3
    }
}'

echo ""
echo "[4] 文件描述符使用:"
echo "-----------------------------------------"
FILE_NR=$(cat /proc/sys/fs/file-nr | awk '{print $1}')
FILE_MAX=$(cat /proc/sys/fs/file-max)
USAGE=$((FILE_NR * 100 / FILE_MAX))
echo "  已用/最大: $FILE_NR / $FILE_MAX ($USAGE%)"
if [ "$USAGE" -gt 80 ]; then
    echo "  🔴 FD 使用率超过 80%，可能存在泄露"
fi

echo ""
echo "[5] KeepAlive 配置:"
echo "-----------------------------------------"
echo "  tcp_keepalive_time:  $(sysctl -n net.ipv4.tcp_keepalive_time) 秒"
echo "  tcp_keepalive_intvl: $(sysctl -n net.ipv4.tcp_keepalive_intvl) 秒"
echo "  tcp_keepalive_probes: $(sysctl -n net.ipv4.tcp_keepalive_probes) 次"
TOTAL=$(( $(sysctl -n net.ipv4.tcp_keepalive_time) + $(sysctl -n net.ipv4.tcp_keepalive_probes) * $(sysctl -n net.ipv4.tcp_keepalive_intvl) ))
echo "  总超时: $TOTAL 秒 ($((TOTAL / 60)) 分钟)"

echo ""
echo "========================================="
echo "  诊断完成"
echo "========================================="
```

---

## 🔍 SRE 实战案例

### 案例 1：大量 CLOSE_WAIT 导致文件描述符耗尽

**场景**：API 网关在高峰时段出现 502 错误，随后被 OOM Killer 终止。

**排查过程**：

```
Step 1: 检查 TCP 状态
$ ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn
  8500 CLOSE-WAIT    ← 🔴 异常！
   230 ESTAB
   156 TIME-WAIT
    12 LISTEN

Step 2: 定位进程
$ ss -tanp state close-wait | head -5
→ 都是 api-gateway 进程

Step 3: 检查 FD
$ ls /proc/<pid>/fd | wc -l
8523 / 10000 = 85%  → 即将耗尽

Step 4: 根因分析
→ 上游负载均衡器健康检查超时，关闭连接（发送 FIN）
→ API 网关收到 FIN，内核回复 ACK
→ 但应用代码异常分支没有调用 close()
→ 连接停留 CLOSE_WAIT

Step 5: 修复
→ 代码修复：所有路径确保 close()
→ 监控告警：CLOSE_WAIT > 500 触发告警
→ FD 监控：使用率 > 80% 触发告警
```

### 案例 2：TIME_WAIT 过多导致端口耗尽

**场景**：微服务 A 调用微服务 B，间歇性出现 "Cannot assign requested address"。

**排查过程**：

```
Step 1: 检查 TIME_WAIT 数量
$ ss -tan state time-wait | wc -l
27800  ← 接近 ephemeral port 上限（32768-60999 ≈ 28000）

Step 2: 分析原因
→ 微服务 A 使用短连接调用 B（每次请求新建连接）
→ 高并发下快速创建和关闭连接
→ TIME_WAIT 积累导致端口耗尽

Step 3: 解决方案
1. 启用长连接（连接池）
   → 使用 HTTP Keep-Alive 或 gRPC 连接池
   → 从根本上减少连接创建和关闭

2. 启用 tcp_tw_reuse
   → net.ipv4.tcp_tw_reuse = 1
   → 允许 TIME_WAIT 端口被复用

3. 扩大端口范围
   → net.ipv4.ip_local_port_range = 1024 65535
```

### 案例 3：TCP 重传导致延迟飙升

**场景**：用户反馈 API 响应延迟从 10ms 飙升到 500ms+。

**排查过程**：

```
Step 1: 检查网络质量
$ mtr -r -c 100 api-server
→ 发现第 5 跳丢包率 15%

Step 2: 检查 TCP 重传
$ netstat -s | grep retransmit
TcpExtTCPSlowStartRetrans: 12345
→ 大量重传

Step 3: 分析原因
→ 中间网络设备（第 5 跳路由器）拥塞
→ 丢包触发 TCP 重传
→ 重传等待时间（RTO ≈ 200ms+）导致延迟飙升

Step 4: 解决方案
1. 联系网络团队修复拥塞的路由器
2. 启用 BBR 拥塞控制（对丢包更鲁棒）
3. 启用 SACK 减少不必要的重传
```

### 案例 4：用 ss 分析 TCP 连接问题

```bash
# 综合分析脚本
#!/bin/bash
echo "=== TCP 连接综合分析 ==="

# 1. 总体状态
echo "连接状态分布:"
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn

# 2. 每个服务的连接数
echo ""
echo "按本地端口统计 ESTABLISHED 连接:"
ss -tan state established | awk 'NR>1 {print $4}' | \
    rev | cut -d: -f1 | rev | sort | uniq -c | sort -rn | head -10

# 3. 每个远程 IP 的连接数
echo ""
echo "按远程 IP 统计连接数:"
ss -tan state established | awk 'NR>1 {print $5}' | \
    cut -d: -f1 | sort | uniq -c | sort -rn | head -10

# 4. Recv-Q 积压（说明 accept 慢）
echo ""
echo "Recv-Q 积压（> 0 说明有问题）:"
ss -tln | awk 'NR>1 && $2 > 0 {print "  " $4 " Recv-Q=" $2 " Send-Q=" $3}'

# 5. 长连接检测
echo ""
echo "长时间无活动的连接（可能需要清理）:"
ss -tanp state established | awk 'NR>1 {print}' | \
    while read line; do
        timer=$(echo "$line" | grep -oP 'timer:\(\w+,\K[0-9]+')
        if [ -n "$timer" ] && [ "$timer" -gt 3600 ]; then
            echo "  $line"
        fi
    done | head -10
```

---

## 🎯 面试题精选

### Q1: 为什么 TCP 握手是三次而不是两次？

**参考答案**：两次握手的问题在于无法防止历史连接。如果客户端发送的 SYN 在网络中滞留，服务器收到后直接建立连接，但客户端并没有发起新连接，导致服务器维护无效连接浪费资源。三次握手让客户端有机会在第三步"否决"连接建立。同时三次握手也是双方同步初始序列号（ISN）的最少次数。

### Q2: 为什么 TCP 挥手需要四次而不是三次？

**参考答案**：TCP 是全双工的，每个方向需要独立关闭。客户端发送 FIN 只表示"我不再发送数据"，但仍然可以接收。服务器收到 FIN 后可能还有数据要发送，所以先回复 ACK，等数据发送完毕后再发 FIN。如果服务器没有剩余数据，ACK 和 FIN 可以合并为一个包（看起来像三次），但这只是特殊情况。

### Q3: TIME_WAIT 状态的作用是什么？如何处理 TIME_WAIT 过多？

**参考答案**：TIME_WAIT 存在两个原因：1) 确保最后一个 ACK 能到达服务器（如果丢失可以重传 ACK）；2) 让旧连接的延迟数据包在网络中消散（防止被新连接误收）。TIME_WAIT 过多的解决方案：1) 使用长连接/连接池（根本解决）；2) 启用 tcp_tw_reuse；3) 扩大 ephemeral port 范围；4) 注意不要使用已废弃的 tcp_tw_recycle。

### Q4: CLOSE_WAIT 状态是怎么产生的？如何排查？

**参考答案**：CLOSE_WAIT 是被动关闭方在收到对方 FIN 后的状态，表示应用程序没有调用 close() 关闭 socket。这是应用层 Bug，不是内核问题。排查方法：1) `ss -tanp state close-wait` 查看进程；2) 检查应用代码中是否有连接泄露（异常分支没有 close）；3) 监控 FD 使用率。常见成因：异常处理遗漏、连接池泄露、死锁/阻塞。

### Q5: TCP 的慢启动和拥塞避免有什么区别？

**参考答案**：慢启动阶段 cwnd 从 1 MSS 开始，每收到一个 ACK 增加 1 MSS（指数增长），每 RTT 翻倍。当 cwnd 达到 ssthresh 后进入拥塞避免阶段，每 RTT 只增加 1 MSS（线性增长）。慢启动快速探测可用带宽，拥塞避免缓慢逼近网络容量。丢包后 ssthresh 设为 cwnd/2，重新开始慢启动（或快恢复）。

### Q6: BBR 和 Cubic 拥塞控制算法有什么区别？

**参考答案**：Cubic 基于丢包信号，使用三次函数控制窗口增长，丢包后窗口减半再通过凹函数快速恢复。BBR 基于带宽和 RTT 估计，主动探测瓶颈带宽（BtlBw）和最小延迟（RTprop），发送速率 = BtlBw × RTprop。BBR 在高带宽长延迟网络中表现更好，不依赖丢包作为拥塞信号，但在低延迟网络中可能不公平。

### Q7: Nagle 算法和 TCP_NODELAY 是什么关系？

**参考答案**：Nagle 算法在发送方缓存小数据包，等待前面数据的 ACK 到达后再发送，以减少网络中小包数量。TCP_NODELAY 是一个 socket 选项，设置后禁用 Nagle 算法，数据立即发送。RPC 框架、游戏、SSH 等延迟敏感场景通常禁用 Nagle（设置 TCP_NODELAY），文件传输等吞吐量优先场景保持启用。

### Q8: 如何用 ss 命令排查 TCP 连接问题？

**参考答案**：
- `ss -tan | awk 'NR>1{print $1}' | sort | uniq -c | sort -rn` 查看状态分布
- `ss -tanp state close-wait` 查看 CLOSE_WAIT 的进程
- `ss -tln` 查看监听端口和队列积压
- `ss -tanpi` 查看连接的详细信息（窗口、拥塞控制等）
- `ss -tan state time-wait | wc -l` 统计 TIME_WAIT 数量
- Recv-Q 接近 Send-Q 说明 accept 太慢，可能是应用阻塞

### Q9: SYN Flood 攻击的原理和防御方法？

**参考答案**：攻击者发送大量伪造源 IP 的 SYN 包，服务器为每个 SYN 分配资源并回复 SYN-ACK，但永远收不到 ACK（因为源 IP 是伪造的），导致 SYN 队列耗尽，合法连接无法建立。防御方法：1) 启用 SYN Cookies（最有效，不分配资源）；2) 增大 tcp_max_syn_backlog；3) 减少 SYN_RECV 超时；4) 防火墙层面限速。

### Q10: TCP KeepAlive 和应用层心跳有什么区别？

**参考答案**：TCP KeepAlive 由内核管理，发送空 ACK 探测包，对应用透明，默认 2 小时空闲后才开始探测（太长），主要用于检测死连接。应用层心跳由应用程序自己实现，可以自定义间隔和内容，通常 10-30 秒一次，除了检测连接存活还可以交换状态信息。两者可以共存，建议生产环境同时使用。

---

## 📚 深入阅读

### 官方文档与 RFC
- [RFC 793 - TCP Protocol Specification](https://datatracker.ietf.org/doc/html/rfc793) — TCP 协议原始规范
- [RFC 7323 - TCP Extensions for High Performance](https://datatracker.ietf.org/doc/html/rfc7323) — 窗口缩放、时间戳
- [RFC 6298 - Computing TCP's Retransmission Timer](https://datatracker.ietf.org/doc/html/rfc6298) — RTO 计算
- [RFC 2018 - TCP Selective Acknowledgment Options](https://datatracker.ietf.org/doc/html/rfc2018) — SACK
- [RFC 7413 - TCP Fast Open](https://datatracker.ietf.org/doc/html/rfc7413) — TFO

### 推荐资源
- [Linux TCP Documentation](https://www.kernel.org/doc/html/latest/networking/tcp.html) — Linux 内核 TCP 文档
- [Brendan Gregg - TCP Observability](https://www.brendangregg.com/blog/2017-03-08/tcp-observability.html) — TCP 可观测性
- [Google BBR](https://github.com/google/bbr) — BBR 拥塞控制算法实现
- [Linux Network Performance Parameters](https://github.com/leandromoreira/linux-network-performance-parameters) — 网络性能调优指南

### 视频资源
- [Bilibili - TCP 三次握手四次挥手动画](https://www.bilibili.com/video/BV1gx411D7mP/) — 直观理解
- [YouTube - TCP Congestion Control](https://www.youtube.com/watch?v=U9HfN-3o36g) — 拥塞控制详解

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出 TCP 头部结构，说明每个关键字段的含义
- [ ] 能完整描述三次握手的过程，解释为什么不是两次/四次
- [ ] 能完整描述四次挥手的过程，解释 TIME_WAIT 和 CLOSE_WAIT 的成因
- [ ] 能画出 TCP 11 种状态的转换图
- [ ] 理解慢启动、拥塞避免、快重传、快恢复的工作原理
- [ ] 理解 BBR 与 Cubic 的区别
- [ ] 理解滑动窗口、窗口缩放和 Nagle 算法
- [ ] 理解 TCP KeepAlive 与 HTTP Keep-Alive 的区别

### 实操检查点
- [ ] 能用 ss 命令查看和统计 TCP 连接状态
- [ ] 能用 tcpdump 观察三次握手和四次挥手
- [ ] 能查看和调整 TCP 内核参数（sysctl）
- [ ] 能诊断 CLOSE_WAIT 和 TIME_WAIT 问题
- [ ] 能配置 BBR 拥塞控制算法
- [ ] 完成了全部 4 个实战练习和 4 个实战案例

---

*由 SRE 学习计划生成 | 2026-04-30*
