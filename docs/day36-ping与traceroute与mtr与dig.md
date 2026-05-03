# Day 36: 网络诊断工具 — ping / traceroute / mtr / dig

> 📅 日期：2026-04-30
> 📖 学习主题：网络诊断工具深度解析与 SRE 实战
> ⏰ 计划学习时间：2-3 小时

## 🎯 学习目标

- [ ] 掌握 ping、traceroute、mtr、dig 四大网络诊断工具的核心用法和参数
- [ ] 理解 ICMP 协议原理、TTL 机制和路由追踪原理
- [ ] 通过 SRE 实战案例：使用 mtr 发现 80% 丢包并确认运营商问题
- [ ] 完成练习：用 mtr 分析到多个云厂商的网络质量
- [ ] 扩展：使用 fping 批量 ping 生成延迟报告

---

## 📖 详细知识点

### 1. ping — 基础连通性检测

#### 1.1 ICMP 协议原理

ping 使用 ICMP (Internet Control Message Protocol) Echo Request/Echo Reply 消息来检测网络连通性。

```
┌──────────────┐                    ┌──────────────┐
│   Client     │                    │   Server     │
│              │  ICMP Echo Request │              │
│              │ ──────────────────>│              │
│              │                    │              │
│              │ ICMP Echo Reply    │              │
│              │ <──────────────────│              │
└──────────────┘                    └──────────────┘
```

**ICMP 消息类型：**

| 类型 (Type) | 代码 (Code) | 含义 | 常见场景 |
|------------|------------|------|---------|
| 0 | 0 | Echo Reply | ping 正常响应 |
| 3 | 0-15 | Destination Unreachable | 目标不可达 |
| 3 | 0 | Network Unreachable | 网络不可达 |
| 3 | 1 | Host Unreachable | 主机不可达 |
| 3 | 3 | Port Unreachable | 端口不可达 (UDP) |
| 3 | 4 | Fragmentation Needed | 需要分片但设置了 DF |
| 8 | 0 | Echo Request | ping 发出的请求 |
| 11 | 0 | TTL Expired | traceroute 利用此机制 |
| 11 | 1 | TTL Expired in Transit | 路由环路检测 |

#### 1.2 ping 常用命令

```bash
# 基础用法 — 发送 4 个 ICMP 包
ping -c 4 www.example.com

# 指定间隔时间 (秒)
ping -c 10 -i 0.5 www.example.com

# 指定包大小
ping -c 4 -s 1472 www.example.com   # MTU 测试 (1500 - 28 = 1472)

# Flood ping (快速发送，SRE 压力测试用)
ping -f -c 1000 www.example.com

# 显示时间戳
ping -c 4 -D www.example.com

# 设置 TTL
ping -c 4 -t 64 www.example.com

# 只发送不接收 (单向测试)
ping -c 4 -q www.example.com
```

#### 1.3 ping 输出解读

```
PING www.example.com (93.184.216.34) 56(84) bytes of data.
64 bytes from 93.184.216.34: icmp_seq=1 ttl=56 time=45.2 ms
64 bytes from 93.184.216.34: icmp_seq=2 ttl=56 time=44.8 ms
64 bytes from 93.184.216.34: icmp_seq=3 ttl=56 time=46.1 ms
64 bytes from 93.184.216.34: icmp_seq=4 ttl=56 time=45.5 ms

--- www.example.com ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3005ms
rtt min/avg/max/mdev = 44.812/45.392/46.132/0.487 ms
```

**关键字段说明：**

| 字段 | 含义 | 正常范围 | 异常表现 |
|------|------|---------|---------|
| ttl | Time To Live，每经过一跳减 1 | 64/128/255 初始值 | 异常低表示路由过长 |
| time | 往返延迟 (RTT) | < 50ms (同城) | > 200ms 可能存在拥塞 |
| packet loss | 丢包率 | 0% | > 1% 需关注，> 5% 严重 |
| mdev | 延迟抖动 (标准差) | < 5ms | > 20ms 网络不稳定 |

**TTL 与操作系统推断：**

| 初始 TTL | 常见操作系统 | 推断方法 |
|---------|------------|---------|
| 64 | Linux / macOS / BSD | 收到 TTL ≤ 64 |
| 128 | Windows | 收到 TTL ≤ 128 |
| 255 | 网络设备 (路由器/交换机) | 收到 TTL ≤ 255 |

#### 1.4 MTU 路径发现 (Path MTU Discovery)

MTU (Maximum Transmission Unit) 是网络链路能够传输的最大数据包大小。以太网默认 MTU 为 1500 字节。

```
MTU 路径发现原理:

发送 DF (Don't Fragment) 标志的包，逐渐增大包大小:
  1400 bytes → 通过 ✅
  1450 bytes → 通过 ✅
  1472 bytes → 通过 ✅
  1473 bytes → 返回 ICMP "Fragmentation Needed" ❌
  
路径 MTU = 1472 + 28 (IP+ICMP 头) = 1500
```

```bash
# 使用 ping 进行 MTU 发现
# -M do: 设置 DF 标志 (Don't Fragment)
# -s: 设置包大小 (不包含 IP/ICMP 头部的 28 字节)

# 标准以太网 MTU 测试 (1500 - 28 = 1472)
ping -c 4 -M do -s 1472 www.example.com
# 成功: 1500 就是路径 MTU

# 如果失败，逐步减小
ping -c 4 -M do -s 1400 www.example.com
ping -c 4 -M do -s 1450 www.example.com
ping -c 4 -M do -s 1470 www.example.com

# 二分法快速定位 MTU
mtu_test() {
    local host="$1"
    local low=0
    local high=9000  # 支持巨型帧的网络
    
    while [ $((high - low)) -gt 1 ]; do
        local mid=$(( (low + high) / 2 ))
        if ping -c 1 -W 2 -M do -s "$mid" "$host" &>/dev/null; then
            low=$mid
        else
            high=$mid
        fi
    done
    
    echo "路径 MTU: $((low + 28)) 字节 (数据包大小: $low)"
}

mtu_test www.example.com
```

**MTU 问题排查场景：**

| 现象 | 可能原因 | 排查方法 |
|------|---------|---------|
| 小包通大包不通 | MTU 不匹配 | ping -M do -s 测试 |
| SSH 能连但传文件卡住 | MTU 问题导致大包丢弃 | 降低 MTU 或调整 MSS |
| 网页加载卡住 | TCP MSS > 路径 MTU | 抓包检查 MSS 协商 |
| VPN 连接后部分网站不通 | VPN 封装降低了有效 MTU | 调整 VPN MTU |

#### 1.5 ping 高级用法

```bash
# 指定源地址 (多网卡场景)
ping -c 4 -I 192.168.1.100 www.example.com

# 记录路由 (类似 traceroute)
ping -c 4 -R www.example.com

# 设置 QoS/DSCP 标记
ping -c 4 -Q 0x10 www.example.com  # 低延迟标记

# 指定网卡
ping -c 4 -I eth0 www.example.com

# 计算统计信息后退出
ping -c 100 -q www.example.com

# 带时间戳的 ping (用于长期监控)
ping -c 60 -D www.example.com > ping_log.txt

# 使用 IPv6
ping6 -c 4 www.example.com
ping -6 -c 4 www.example.com
```

### 2. traceroute — 路径追踪

#### 2.1 工作原理

traceroute 利用 IP 数据包的 TTL (Time To Live) 字段和 ICMP Time Exceeded 消息来追踪数据包经过的每一跳路由器。

```
发送过程:
  TTL=1 → 第1跳路由器收到后 TTL=0 → 返回 ICMP Time Exceeded
  TTL=2 → 第2跳路由器收到后 TTL=0 → 返回 ICMP Time Exceeded
  TTL=3 → 第3跳路由器收到后 TTL=0 → 返回 ICMP Time Exceeded
  ...
  TTL=N → 到达目标 → 返回 ICMP Echo Reply 或端口不可达
```

#### 2.2 traceroute 常用命令

```bash
# 基础用法
traceroute www.example.com

# 使用 ICMP (需要 root)
sudo traceroute -I www.example.com

# 使用 TCP SYN (绕过 ICMP 防火墙)
traceroute -T -p 443 www.example.com

# 设置最大跳数和超时
traceroute -m 30 -w 3 www.example.com

# 指定源地址 (多网卡场景)
traceroute -s 192.168.1.100 www.example.com

# 不解析域名 (加快速度)
traceroute -n www.example.com

# 设置发送包数量
traceroute -q 5 www.example.com
```

#### 2.3 traceroute 的三种探测模式

| 模式 | 命令 | 协议 | 特点 | 使用场景 |
|------|------|------|------|---------|
| UDP (默认) | `traceroute host` | UDP (端口 33434+) | 高端口递增，可能被防火墙拦截 | Linux 默认模式 |
| ICMP | `traceroute -I host` | ICMP Echo | 需要 root 权限 | 目标禁 UDP 时使用 |
| TCP | `traceroute -T -p 443 host` | TCP SYN | 绕过大多数防火墙 | 最佳兼容性 |

```bash
# UDP 模式 (默认)
traceroute www.example.com

# ICMP 模式 (需要 root)
sudo traceroute -I www.example.com

# TCP 模式 (绕过 UDP 防火墙)
traceroute -T -p 443 www.example.com

# TCP 模式连接特定端口
traceroute -T -p 8080 api.example.com

# 对比三种模式的结果
echo "=== UDP ===" && traceroute -n -m 15 www.example.com
echo "=== ICMP ===" && sudo traceroute -I -n -m 15 www.example.com
echo "=== TCP ===" && traceroute -T -n -m 15 -p 443 www.example.com
```

**为什么某些跳显示 `* * *`？**

```
原因 1: 路由器配置了 ICMP 速率限制
  → 不影响数据转发，只是不回复探测包
  → 后续跳正常则无需担心

原因 2: 防火墙丢弃了探测包
  → 尝试使用 TCP 模式 (-T)
  → 或指定常用端口 (-p 80/443)

原因 3: 真实丢包
  → 后续跳也显示 * * * 则可能是真实故障
  → 使用 mtr 进行长时间测试确认
```

#### 2.4 traceroute 输出解读

```
traceroute to www.example.com (93.184.216.34), 30 hops max, 60 byte packets
 1  192.168.1.1 (192.168.1.1)  2.345 ms  2.123 ms  2.456 ms
 2  10.0.0.1 (10.0.0.1)  5.678 ms  5.432 ms  5.891 ms
 3  100.64.0.1 (100.64.0.1)  8.901 ms  8.765 ms  9.012 ms
 4  * * *                    ← 路由器禁用了 ICMP 回复 (正常现象)
 5  202.96.128.86 (202.96.128.86)  15.234 ms  14.987 ms  15.567 ms
 6  93.184.216.34 (93.184.216.34)  45.678 ms  45.234 ms  46.012 ms
```

**每行三列延迟的含义：** 每个 TTL 发送 3 个探测包，三列分别是三个包的 RTT。

| 现象 | 可能原因 | SRE 判断 |
|------|---------|---------|
| 某跳延迟突增 | 拥塞或低优先级处理 | 结合后续跳判断 |
| 某跳全是 `*` | 禁 ICMP 或丢包 | 看下一跳是否可达 |
| 所有跳都 `*` | 完全不通 | 检查防火墙/路由 |
| 延迟逐渐增加后突降 | 正常 (地理距离) | 关注异常跳 |
| 出现环路 (IP 重复) | 路由环路 | 紧急故障 |

### 3. mtr — 增强型网络诊断

#### 3.1 mtr 简介

mtr (My TraceRoute) 结合了 ping 和 traceroute 的功能，提供持续的网络质量监控，是 SRE 排查网络问题的首选工具。

#### 3.2 mtr 常用命令

```bash
# 交互式模式 (默认)
mtr www.example.com

# 报告模式 (适合脚本和日志)
mtr -r -c 100 www.example.com

# 宽格式输出 (显示完整域名)
mtr -r -c 100 --no-dns www.example.com

# CSV 格式 (方便后续处理)
mtr -r -c 100 --csv www.example.com

# JSON 格式
mtr -r -c 100 --json www.example.com

# 仅显示最后结果 (不显示过程)
mtr -r -c 100 -n www.example.com

# 使用 TCP 模式 (绕过 ICMP 限制)
mtr -T -p 443 -r -c 100 www.example.com

# 设置包大小
mtr -r -c 100 -s 1024 www.example.com
```

#### 3.3 mtr 输出解读

```
Host                   Loss%   Snt   Last   Avg  Best  Wrst StDev
 1. 192.168.1.1         0.0%   100    2.3   2.5   1.8   5.6   0.8
 2. 10.0.0.1            0.0%   100    5.6   5.8   4.9   8.2   0.6
 3. 100.64.0.1          0.0%   100    8.9   9.1   7.8  12.3   0.9
 4. 202.96.128.86       0.0%   100   15.2  15.5  13.8  18.9   1.1
 5. 93.184.216.34       0.0%   100   45.6  45.9  43.2  49.8   1.3
```

**各列含义：**

| 列名 | 含义 | 说明 |
|------|------|------|
| Host | 节点 IP 或域名 | `-n` 参数仅显示 IP |
| Loss% | 丢包率 | > 1% 需关注，> 5% 严重 |
| Snt | 已发送包数 | 测试的样本量 |
| Last | 最后一次延迟 | 当前网络状态 |
| Avg | 平均延迟 | 整体网络质量 |
| Best | 最佳延迟 | 理想状态 |
| Wrst | 最差延迟 | 网络抖动上限 |
| StDev | 标准差 | 值越大表示网络越不稳定 |

#### 3.4 mtr 丢包分析要点

**关键原则：逐跳分析，不能孤立看某一跳的丢包。**

| 场景 | 丢包表现 | 原因判断 |
|------|---------|---------|
| 中间某跳丢包，后续正常 | 仅该跳丢包 | 该路由器限速 ICMP，**非真实丢包** |
| 从某跳开始全部丢包 | 该跳及后续全部丢包 | 该跳之后**真实丢包** |
| 最后一跳高丢包 | 仅终点丢包 | 可能是目标限速 ICMP 或真实丢包 |
| 全程高丢包 | 所有跳都丢包 | 本机网络或出口问题 |

#### 3.5 mtr 高级用法与长期监测

```bash
# 长时间监测 (适合间歇性问题)
# 运行 1 小时，每秒一个包
mtr -r -c 3600 -i 1 www.example.com > mtr_1h_report.txt

# 后台运行，定期输出报告
nohup mtr -r -c 3600 -i 1 --json www.example.com > mtr_report.json &

# TCP 模式 (绕过 ICMP 限制)
mtr -T -p 443 -r -c 100 www.example.com

# UDP 模式
mtr -u -r -c 100 www.example.com

# 指定源地址
mtr -a 192.168.1.100 -r -c 100 www.example.com

# 设置包大小
mtr -s 1500 -r -c 100 www.example.com  # 测试 MTU

# 并行 DNS 解析
mtr -b -r -c 100 www.example.com

# 输出为 XML 格式
mtr -r -c 100 --xml www.example.com
```

**mtr 自动化监控脚本：**

```bash
#!/bin/bash
# mtr_monitor.sh - 网络质量持续监控
# 用法: ./mtr_monitor.sh <目标> [间隔秒数] [次数]

TARGET="${1:?用法: $0 <目标> [间隔秒数] [次数]}"
INTERVAL="${2:-60}"   # 默认每 60 秒测试一次
COUNT="${3:-10}"      # 默认每次发 10 个包
LOG_DIR="./mtr_logs"
mkdir -p "$LOG_DIR"

echo "开始监控 $TARGET，每 ${INTERVAL}s 测试一次"
echo "日志目录: $LOG_DIR"
echo "按 Ctrl+C 停止"

while true; do
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    REPORT_FILE="$LOG_DIR/mtr_${TIMESTAMP}.txt"
    
    # 执行 mtr 测试
    mtr -r -c "$COUNT" -n "$TARGET" > "$REPORT_FILE" 2>/dev/null
    
    # 提取最后一跳的指标
    LAST_LINE=$(tail -1 "$REPORT_FILE")
    LOSS=$(echo "$LAST_LINE" | awk '{print $3}' | tr -d '%')
    AVG=$(echo "$LAST_LINE" | awk '{print $5}')
    
    # 判断是否异常
    if [ -n "$LOSS" ] && [ "$LOSS" -gt 5 ] 2>/dev/null; then
        echo "[$(date)] ⚠️ 警告: $TARGET 丢包 ${LOSS}%，平均延迟 ${AVG}ms"
        # 可以在这里发送告警通知
    else
        echo "[$(date)] ✅ 正常: $TARGET 丢包 ${LOSS}%，平均延迟 ${AVG}ms"
    fi
    
    sleep "$INTERVAL"
done
```

#### 3.6 mtr vs traceroute vs ping 对比

| 特性 | ping | traceroute | mtr |
|------|------|-----------|-----|
| 功能 | 连通性检测 | 路径追踪 | 路径 + 连通性 |
| 持续监控 | 需要脚本 | 单次执行 | 内置支持 |
| 丢包统计 | 仅终点 | 每跳 3 个包 | 每跳持续统计 |
| 延迟统计 | avg/min/max | 每跳 3 次 | avg/best/wrst/stdev |
| 输出格式 | 文本 | 文本 | text/csv/json/xml |
| SRE 推荐场景 | 快速检测 | 路径分析 | **网络质量诊断首选** |

### 4. dig — DNS 诊断

#### 4.1 dig 常用命令

```bash
# 基础查询
dig www.example.com

# 简洁输出
dig +short www.example.com

# 指定 DNS 服务器
dig @8.8.8.8 www.example.com
dig @1.1.1.1 www.example.com
dig @114.114.114.114 www.example.com

# 查询特定记录类型
dig A www.example.com        # A 记录 (IPv4)
dig AAAA www.example.com     # AAAA 记录 (IPv6)
dig MX example.com           # MX 记录
dig NS example.com           # NS 记录
dig TXT example.com          # TXT 记录
dig SOA example.com          # SOA 记录
dig CNAME www.example.com    # CNAME 记录

# 跟踪完整解析链
dig +trace www.example.com

# 显示所有信息
dig +noall +answer +authority +additional www.example.com

# 查询反向 DNS (PTR)
dig -x 93.184.216.34

# 批量查询
dig -f domains.txt +short

# 设置超时和重试
dig +time=2 +tries=1 www.example.com
```

#### 4.2 dig 输出解读

```
; <<>> DiG 9.18.1 <<>> www.example.com
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 12345
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 512

;; QUESTION SECTION:
;www.example.com.               IN      A

;; ANSWER SECTION:
www.example.com.        86400   IN      A       93.184.216.34

;; Query time: 15 msec
;; SERVER: 8.8.8.8#53(8.8.8.8) (UDP)
;; WHEN: Mon Apr 29 14:00:00 UTC 2026
;; MSG SIZE  rcvd: 59
```

**关键字段：**

| 字段 | 含义 | 正常值 |
|------|------|-------|
| status | 查询状态 | NOERROR |
| flags | 响应标志 | qr (响应) rd (递归) ra (递归可用) |
| ANSWER SECTION | 回答记录 | 至少 1 条 |
| Query time | 查询耗时 | < 50ms |
| SERVER | 使用的 DNS 服务器 | 配置的 DNS |

#### 4.3 dig +trace 详解

`dig +trace` 模拟完整的递归查询过程，从根服务器开始逐级查询：

```bash
dig +trace www.example.com
```

**输出解读：**

```
; <<>> DiG 9.18.1 <<>> +trace www.example.com
;; global options: +cmd

# 第 1 步: 查询根服务器 (.)
.                       518400  IN      NS      a.root-servers.net.
.                       518400  IN      NS      b.root-servers.net.
...
;; Received 239 bytes from 8.8.8.8#53(8.8.8.8) in 5 ms

# 第 2 步: 查询 .com TLD 服务器
com.                    172800  IN      NS      a.gtld-servers.net.
com.                    172800  IN      NS      b.gtld-servers.net.
...
;; Received 1170 bytes from 198.41.0.4#53(a.root-servers.net) in 45 ms

# 第 3 步: 查询 example.com 权威服务器
example.com.            172800  IN      NS      a.iana-servers.net.
example.com.            172800  IN      NS      b.iana-servers.net.
...
;; Received 248 bytes from 192.5.6.30#53(a.gtld-servers.net) in 38 ms

# 第 4 步: 从权威服务器获取最终结果
www.example.com.        86400   IN      A       93.184.216.34
;; Received 59 bytes from 199.43.135.53#53(a.iana-servers.net) in 82 ms
```

**trace 排查场景：**

```bash
# 场景 1: DNS 解析慢
# 观察每步的 Query time，定位慢在哪个层级
dig +trace +stats www.example.com 2>&1 | grep "Query time"

# 场景 2: DNS 记录不一致
# 对比 trace 结果和实际解析结果
dig +trace www.example.com | tail -5
dig @8.8.8.8 www.example.com +short

# 场景 3: 权威服务器配置问题
# 直接查询权威服务器
dig @a.iana-servers.net www.example.com +short
```

#### 4.4 dig DNSSEC 验证

```bash
# 查询 DNSSEC 记录
dig +dnssec www.example.com

# 查看 RRSIG (签名记录)
dig +dnssec +short www.example.com

# 查看 DS 记录 (委托签名)
dig DS example.com

# 查看 DNSKEY (公钥)
dig DNSKEY example.com

# 验证 DNSSEC 链
dig +trace +dnssec www.example.com

# 检查 DNSSEC 验证状态
dig +cd +short www.example.com   # 跳过验证 (CD = Checking Disabled)
dig +short www.example.com       # 正常验证
```

**DNSSEC 验证链：**

```
Root DNS (.)
  │ DS 记录 → .com 的 DS 记录
  ▼
.com TLD
  │ DS 记录 → example.com 的 DS 记录
  ▼
example.com 权威服务器
  │ RRSIG 记录 → 对 A/AAAA 等记录的签名
  ▼
www.example.com (最终结果)
```

#### 4.5 nslookup vs dig 对比

| 特性 | nslookup | dig |
|------|---------|-----|
| 输出格式 | 简洁 | 详细 (RFC 格式) |
| DNSSEC 支持 | 不支持 | 支持 (+dnssec) |
| 批量查询 | 不支持 | 支持 (-f 文件) |
| 跟踪解析链 | 不支持 | 支持 (+trace) |
| 脚本友好 | 一般 | 优秀 (+short) |
| 记录类型查询 | 支持 | 支持 |
| 指定 DNS 服务器 | 支持 | 支持 (@server) |
| SRE 推荐 | 一般 | **首选** |

```bash
# nslookup 基础用法
nslookup www.example.com
nslookup -type=MX example.com
nslookup www.example.com 8.8.8.8

# dig 等效命令
dig +short www.example.com
dig MX example.com +short
dig @8.8.8.8 www.example.com +short

# dig 独有功能
dig +trace www.example.com      # nslookup 无法做到
dig +dnssec www.example.com     # nslookup 无法做到
dig -f domains.txt +short       # 批量查询
```

### 5. 网络诊断方法论

#### 5.1 自下而上排查法 (Bottom-Up Approach)

```
OSI 模型自下而上排查:

Layer 7 (应用层):   HTTP 响应是否正常? ← curl/wget
Layer 6 (表示层):   TLS 证书是否有效?  ← openssl
Layer 5 (会话层):   连接是否建立?      ← nc/ss
Layer 4 (传输层):   TCP/UDP 端口是否通? ← nc/telnet
Layer 3 (网络层):   IP 路由是否正确?   ← ping/traceroute/mtr
Layer 2 (数据链路): MAC 地址是否正确?  ← arp/ip neigh
Layer 1 (物理层):   网线是否插好?      ← ethtool/ip link
```

```bash
# 自下而上排查脚本
check_bottom_up() {
    local target="$1"
    echo "=== 自下而上排查: $target ==="
    
    # Layer 1-2: 物理/数据链路层
    echo "[L1/L2] 网卡状态:"
    ip link show | grep -E "state (UP|DOWN)"
    
    # Layer 3: 网络层 (ping)
    echo "[L3] Ping 测试:"
    ping -c 3 -W 2 "$target" &>/dev/null && echo "  ✅ 通" || echo "  ❌ 不通"
    
    # Layer 4: 传输层 (端口)
    echo "[L4] TCP 端口测试:"
    nc -z -w 3 "$target" 80 &>/dev/null && echo "  ✅ 80 端口通" || echo "  ❌ 80 端口不通"
    nc -z -w 3 "$target" 443 &>/dev/null && echo "  ✅ 443 端口通" || echo "  ❌ 443 端口不通"
    
    # Layer 7: 应用层 (HTTP)
    echo "[L7] HTTP 测试:"
    local code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "https://$target")
    echo "  HTTP 状态码: $code"
}
```

#### 5.2 二分法定位 (Binary Search)

```
二分法定位网络问题:

客户端 ←→ [中间点 A] ←→ [中间点 B] ←→ 服务端

步骤 1: ping 客户端 → 服务端 (不通)
步骤 2: ping 客户端 → 中间点 B (通)
步骤 3: ping 中间点 B → 服务端 (不通)
步骤 4: 问题在 B → 服务端之间

继续二分:
步骤 5: ping 中间点 C → 服务端 (通)
步骤 6: 问题在 B → C 之间
```

```bash
# 二分法定位脚本
binary_search_network() {
    local hops=("192.168.1.1" "10.0.0.1" "172.16.0.1" "203.0.113.1" "93.184.216.34")
    local names=("网关" "接入层" "汇聚层" "核心层" "目标服务器")
    
    echo "=== 二分法定位网络问题 ==="
    
    local left=0
    local right=$(( ${#hops[@]} - 1 ))
    
    while [ $left -lt $right ]; do
        local mid=$(( (left + right) / 2 ))
        echo "测试 ${names[$mid]} (${hops[$mid]})..."
        
        if ping -c 1 -W 2 "${hops[$mid]}" &>/dev/null; then
            echo "  ✅ 可达，问题在 ${names[$mid]} 之后"
            left=$((mid + 1))
        else
            echo "  ❌ 不可达，问题在 ${names[$mid]} 之前或该节点"
            right=$mid
        fi
    done
    
    echo "问题定位: ${names[$left]} (${hops[$left]})"
}
```

---

## 🎯 面试题精选

### 面试题 1：ping 和 traceroute 的原理区别是什么？

**参考答案：**

| 方面 | ping | traceroute |
|------|------|-----------|
| 协议 | ICMP Echo Request/Reply | UDP/ICMP + ICMP Time Exceeded |
| 目的 | 检测端到端连通性 | 追踪每一跳路径 |
| TTL | 使用默认 TTL (64/128) | 从 1 开始递增 |
| 结果 | 终点的延迟和丢包 | 每一跳的延迟和可达性 |
| 使用场景 | 快速检测服务是否可达 | 定位网络瓶颈在哪个节点 |

traceroute 的核心原理：利用 TTL 递减机制，当 TTL=0 时路由器返回 ICMP Time Exceeded 消息，从而获取每一跳路由器的 IP 和延迟。

### 面试题 2：如何排查网络丢包？

**参考答案：**

排查步骤：
1. **确认丢包范围**：`ping` 测试基本连通性，观察丢包率
2. **定位丢包位置**：`mtr -r -c 100 目标`，逐跳分析丢包
3. **判断丢包类型**：
   - 中间丢后面好 → 该路由器限速 ICMP，非真实丢包
   - 中间丢后面也丢 → 真实丢包，该跳是故障点
   - 全部丢 → 本地网络问题
4. **验证**：从不同网络（不同运营商、不同地区）测试
5. **处理**：联系运营商/网络团队、切换备用线路

### 面试题 3：mtr 输出中，中间某跳丢包但后续正常，是为什么？

**参考答案：**

这是最常见的 mtr 误判。原因是中间路由器配置了 ICMP 速率限制（ICMP Rate Limiting），对 ICMP Time Exceeded 消息进行了限速，但数据包实际正常转发。

判断规则：**看最后一跳的丢包率**。如果最后一跳 0% 丢包，即使中间有跳显示丢包，网络也是正常的。

只有当某一跳开始丢包，且后续所有跳（包括终点）都显示相同或更高丢包率时，才是真实丢包。

### 面试题 4：dig +trace 的输出中，每一步代表什么？

**参考答案：**

`dig +trace` 模拟递归解析器的完整查询过程：
1. **根服务器查询**：获取 .com TLD 服务器的 NS 记录
2. **TLD 服务器查询**：获取 example.com 权威服务器的 NS 记录
3. **权威服务器查询**：获取最终的 A/AAAA 记录

每一步的 `Received ... bytes from ... in ... ms` 显示了从哪个服务器收到了多少字节的响应，以及耗时多少毫秒。通过观察每步的耗时，可以定位 DNS 解析慢的原因。

### 面试题 5：如何用命令行验证 DNS 记录是否生效？

**参考答案：**

```bash
# 1. 对比多个 DNS 服务器的结果
dig @8.8.8.8 www.example.com +short
dig @1.1.1.1 www.example.com +short
dig @223.5.5.5 www.example.com +short

# 2. 追踪完整解析链
dig +trace www.example.com

# 3. 查询特定记录类型
dig MX example.com +short
dig TXT example.com +short

# 4. 检查 TTL
dig www.example.com | grep -A1 "ANSWER SECTION"

# 5. 检查 DNSSEC
dig +dnssec www.example.com
```

### 面试题 6：ping 的 TTL 字段有什么用？如何通过 TTL 推断操作系统？

**参考答案：**

TTL (Time To Live) 是 IP 数据包的生存时间，每经过一个路由器减 1。当 TTL=0 时，路由器丢弃数据包并返回 ICMP Time Exceeded 消息。TTL 的作用是防止数据包在网络中无限循环。

通过收到的 TTL 值可以推断对方的操作系统：
- TTL ≤ 64：Linux/macOS/BSD（初始 TTL 通常是 64）
- TTL ≤ 128：Windows（初始 TTL 通常是 128）
- TTL ≤ 255：网络设备如路由器/交换机（初始 TTL 通常是 255）

实际推断方法：如果收到 TTL=52，那么初始 TTL 很可能是 64（64-52=12 跳）。

### 面试题 7：fping 和 ping 有什么区别？

**参考答案：**

| 特性 | ping | fping |
|------|------|-------|
| 目标数量 | 单个 | 多个 (并行) |
| 输出格式 | 逐行显示 | 汇总统计 |
| 脚本友好 | 一般 | 优秀 (CSV/退出码) |
| 性能 | 逐个测试 | 并行测试 |
| 使用场景 | 单目标连通性 | 批量主机存活扫描、网络质量对比 |

fping 特别适合 SRE 场景：
- 批量检查服务器存活状态
- 多节点网络质量对比
- 自动化网络监控脚本

---

## 🛠️ SRE 实战案例

### 案例 1：mtr 发现 80% 丢包 → 确认运营商问题

#### 背景

某 SRE 值班人员收到告警：用户反馈华东地区访问 API 服务大量超时。

#### 排查过程

**Step 1：确认服务状态**

```bash
# 检查服务端状态
systemctl status nginx
systemctl status app-service
curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/health
# 输出: 200 ✅ 服务正常
```

**Step 2：从用户所在地测试**

```bash
# 用户在上海，从上海节点测试
mtr -r -c 200 -n 203.0.113.50
```

**mtr 输出结果：**

```
Start: 2026-04-29T14:30:00+0800
HOST: sh-monitor-01                Loss%   Snt   Last   Avg  Best  Wrst StDev
  1. 10.0.1.1                       0.0%   200    1.2   1.3   0.8   3.2   0.4
  2. 100.64.0.1                     0.0%   200    3.5   3.6   2.9   6.1   0.5
  3. 112.64.245.1                   0.0%   200    5.8   6.0   4.9   9.8   0.7
  4. 112.64.244.89                  0.0%   200    8.2   8.5   7.1  12.3   0.9
  5. 202.96.209.5                   0.0%   200   12.1  12.5  10.8  16.2   1.1
  6. 202.96.209.125                 0.0%   200   15.3  15.8  13.9  19.7   1.2
  7. 101.95.88.1                    0.0%   200   18.5  19.0  16.8  23.4   1.3
  8. 202.97.33.1                    0.0%   200   22.1  22.6  20.1  27.8   1.5
  9. 202.97.50.45                  80.0%   200   45.2  46.8  42.1  52.3   2.8  ← 丢包起点!
 10. 180.163.100.1                 80.0%   200   48.5  50.1  45.3  56.7   3.0
 11. 180.163.100.50                80.0%   200   52.1  53.8  48.9  59.2   3.1
 12. 203.0.113.50                  80.0%   200   55.3  56.9  52.1  63.4   3.2
```

#### 分析

1. **第 9 跳 (202.97.50.45) 开始出现 80% 丢包**
2. **后续所有跳 (10-12) 同样 80% 丢包**
3. **延迟从 22ms 跳到 46ms**，增加了约 24ms
4. **IP 段 202.97.x.x 属于中国电信骨干网**

#### 判断逻辑

```
判断规则:
  IF (第 N 跳丢包) AND (第 N+1 到终点 同样丢包)
  THEN → 第 N 跳是真实故障点
  
  IF (第 N 跳丢包) AND (第 N+1 到终点 无丢包)
  THEN → 第 N 跳限速 ICMP，非真实故障
```

#### 结论与处理

| 项目 | 内容 |
|------|------|
| **故障类型** | 运营商网络拥塞/故障 |
| **影响范围** | 华东电信用户 |
| **影响程度** | 80% 丢包，严重 |
| **处理措施** | 1. 联系电信报障<br>2. 临时切换流量到联通/移动线路<br>3. CDN 调度到正常区域 |

**验证是否运营商问题：**

```bash
# 从不同运营商网络测试
# 联通节点测试
ssh user@unicom-node "mtr -r -c 100 -n 203.0.113.50"

# 移动节点测试
ssh user@mobile-node "mtr -r -c 100 -n 203.0.113.50"

# 如果联通/移动正常，确认是电信问题
```

### 案例 2：traceroute 发现路由环路

```bash
# 路由环路表现
traceroute -n example.com

 1  192.168.1.1    2.3 ms  2.1 ms  2.4 ms
 2  10.0.0.1       5.6 ms  5.4 ms  5.8 ms
 3  172.16.0.1     8.9 ms  8.7 ms  9.1 ms
 4  10.0.0.1       12.3 ms  12.1 ms  12.5 ms  ← 回到第 2 跳!
 5  172.16.0.1     15.6 ms  15.3 ms  15.8 ms  ← 回到第 3 跳!
 6  10.0.0.1       18.9 ms  18.7 ms  19.1 ms  ← 环路再次出现
 ...
```

**处理：** 联系网络团队检查 BGP 路由配置，确认是否存在路由黑洞或错误的路由策略。

---

## 🛠️ 实战练习

### 练习 1：用 mtr 分析到多个云厂商的网络质量

```bash
#!/bin/bash
# cloud_network_test.sh - 多云厂商网络质量对比测试
# 用法: ./cloud_network_test.sh

set -euo pipefail

TARGETS=(
    "阿里云:100.100.100.200"        # 阿里云内网元数据
    "腾讯云:169.254.0.23"           # 腾讯云内网元数据
    "AWS:dns.google"                # AWS 常用 DNS
    "Google:8.8.8.8"               # Google DNS
    "Cloudflare:1.1.1.1"           # Cloudflare DNS
)

RESULTS_DIR="./mtr_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "=========================================="
echo "  多云厂商网络质量对比测试"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

for entry in "${TARGETS[@]}"; do
    IFS=':' read -r name target <<< "$entry"
    echo ""
    echo ">>> 测试: $name ($target)"
    echo "------------------------------------------"
    
    mtr -r -c 50 -n --no-dns "$target" > "$RESULTS_DIR/${name}.txt" 2>/dev/null
    
    # 提取关键指标
    if [ -f "$RESULTS_DIR/${name}.txt" ]; then
        LAST_LINE=$(tail -1 "$RESULTS_DIR/${name}.txt")
        LOSS=$(echo "$LAST_LINE" | awk '{print $3}')
        AVG=$(echo "$LAST_LINE" | awk '{print $5}')
        WRST=$(echo "$LAST_LINE" | awk '{print $7}')
        echo "  丢包率: $LOSS"
        echo "  平均延迟: $AVG ms"
        echo "  最差延迟: $WRST ms"
    else
        echo "  ❌ 测试失败"
    fi
done

echo ""
echo "=========================================="
echo "  测试完成，结果保存在: $RESULTS_DIR/"
echo "=========================================="
```

### 练习 2：用 fping 批量 ping 生成延迟报告

```bash
#!/bin/bash
# fping_report.sh - 批量 ping 延迟报告
# 前提: apt install fping

set -euo pipefail

# 目标列表
TARGETS=(
    "8.8.8.8"          # Google DNS
    "1.1.1.1"          # Cloudflare DNS
    "114.114.114.114"  # 114 DNS
    "223.5.5.5"        # 阿里 DNS
    "119.29.29.29"     # 腾讯 DNS
)

REPORT_FILE="fping_report_$(date +%Y%m%d_%H%M%S).csv"

echo "=========================================="
echo "  批量网络延迟报告"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# CSV 表头
echo "Target,Status,Avg(ms),Min(ms),Max(ms),Loss(%),Sent,Received" > "$REPORT_FILE"

for target in "${TARGETS[@]}"; do
    echo ""
    echo ">>> 测试: $target"
    echo "------------------------------------------"
    
    # fping 输出格式
    RESULT=$(fping -c 20 -e "$target" 2>&1 || true)
    
    # 解析结果
    if echo "$RESULT" | grep -q "unreachable\|timeout\|100% loss"; then
        echo "  ❌ $target - 不可达"
        echo "$target,UNREACHABLE,N/A,N/A,N/A,100%,20,0" >> "$REPORT_FILE"
    else
        # 提取统计信息
        STATS=$(echo "$RESULT" | grep -oP '[\d.]+/(.*)')
        echo "  ✅ $result - $STATS"
        
        AVG=$(echo "$RESULT" | grep -oP 'avg = \K[\d.]+')
        MIN=$(echo "$RESULT" | grep -oP 'min = \K[\d.]+')
        MAX=$(echo "$RESULT" | grep -oP 'max = \K[\d.]+')
        SENT=$(echo "$RESULT" | grep -oP '\K\d+(?=/)')
        RECV=$(echo "$RESULT" | grep -oP '\d+/[0-9]+ ' | head -1 | cut -d'/' -f2)
        
        echo "$target,OK,$AVG,$MIN,$MAX,0%,$SENT,$RECV" >> "$REPORT_FILE"
    fi
done

echo ""
echo "=========================================="
echo "  报告已保存: $REPORT_FILE"
echo "=========================================="

# 显示汇总表格
echo ""
echo "=== 延迟汇总 ==="
column -s',' -t < "$REPORT_FILE"
```

**安装 fping：**

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y fping

# RHEL/CentOS
sudo yum install -y fping

# 快速使用
fping -c 10 8.8.8.8 1.1.1.1 114.114.114.114
```

### 练习 3：综合网络诊断脚本

```bash
#!/bin/bash
# comprehensive_net_check.sh - 综合网络诊断
# 用法: ./comprehensive_net_check.sh <目标IP或域名>

TARGET="${1:?用法: $0 <目标>}"

echo "╔══════════════════════════════════════════╗"
echo "║        综合网络诊断报告                    ║"
echo "║  目标: $TARGET"
echo "║  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "╚══════════════════════════════════════════╝"

# 1. DNS 诊断
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 [1/5] DNS 诊断"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo ">>> 本地 DNS:"
dig +short "$TARGET" 2>/dev/null || echo "无法解析"

echo ""
echo ">>> 公共 DNS 对比:"
echo "  Google (8.8.8.8):     $(dig @8.8.8.8 +short "$TARGET" 2>/dev/null || echo '超时')"
echo "  Cloudflare (1.1.1.1): $(dig @1.1.1.1 +short "$TARGET" 2>/dev/null || echo '超时')"
echo "  阿里 (223.5.5.5):     $(dig @223.5.5.5 +short "$TARGET" 2>/dev/null || echo '超时')"

# 2. ping 测试
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 [2/5] Ping 测试 (10 次)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
ping -c 10 -W 2 "$TARGET" 2>/dev/null | tail -3

# 3. TCP 端口连通性
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 [3/5] TCP 端口连通性"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
for port in 80 443 8080 22; do
    if nc -z -w 3 "$TARGET" "$port" 2>/dev/null; then
        echo "  ✅ 端口 $port: 可达"
    else
        echo "  ❌ 端口 $port: 不可达"
    fi
done

# 4. traceroute (前 15 跳)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 [4/5] 路由追踪 (前 15 跳)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
traceroute -n -m 15 -w 2 "$TARGET" 2>/dev/null | head -20

# 5. mtr 快速测试
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 [5/5] MTR 快速测试 (20 个包)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if command -v mtr &>/dev/null; then
    mtr -r -c 20 -n "$TARGET" 2>/dev/null | tail -15
else
    echo "  mtr 未安装，跳过"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 诊断完成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 📚 最新优质资源

### 官方文档
- [mtr 官方 GitHub](https://github.com/traviscross/mtr) - mtr 源码和文档
- [iputils ping 文档](https://github.com/iputils/iputils) - Linux ping 实现
- [traceroute 官方](https://github.com/iputils/iputils) - traceroute 实现
- [BIND dig 文档](https://bind9.readthedocs.io/) - dig 工具文档
- [ICMP RFC 792](https://datatracker.ietf.org/doc/html/rfc792) - ICMP 协议规范

### 教程与文章
- [Understanding mtr Output](https://kb.nmsu.edu/page.php?id=28190) - mtr 输出解读指南
- [Traceroute vs MTR vs Ping](https://www.cloudflare.com/learning/network-layer/ping-vs-traceroute-vs-mtr/) - Cloudflare 对比分析
- [DNS Troubleshooting Guide](https://developers.google.com/speed/public-dns/docs/using) - Google DNS 排查指南
- [Packet Life Network Troubleshooting](https://packetlife.net/blog/) - 网络排障实战博客

### 工具
- [fping](http://fping.org/) - 批量 ping 工具
- [hping3](http://www.hping.org/) - 高级 ping 工具 (TCP/UDP/ICMP)
- [nping](https://nmap.org/nping/) - Nmap 系列网络探测工具
- [SmokePing](https://oss.oetiker.ch/smokeping/) - 持续网络延迟监控
- [pingplotter](https://www.pingplotter.com/) - 可视化网络诊断工具

### SRE 相关
- [Google SRE - Network Diagnostics](https://sre.google/sre-book/network-diagnostics/) - SRE 网络诊断章节
- [Network Troubleshooting for SREs](https://www.oreilly.com/library/view/learning-sre/9781492076070/ch04.html) - O'Reilly 学习 SRE 第4章
- [AWS Network Troubleshooting Guide](https://docs.aws.amazon.com/vpc/latest/troubleshooting/what-is-vpc-troubleshooting.html) - AWS 网络排查指南

---

## 📝 笔记

### 今日总结

1. **ping** 是最基础的网络连通性检测工具，通过 ICMP Echo Request/Reply 检测目标是否可达。关注 RTT、丢包率和抖动三个核心指标。

2. **traceroute** 利用 TTL 递减和 ICMP Time Exceeded 机制追踪数据包路径。每跳发送 3 个包，通过延迟变化定位网络瓶颈。

3. **mtr** 是 SRE 排查网络问题的首选工具，结合了 ping 和 traceroute 的优势。关键在于**逐跳分析丢包**，区分真实丢包和 ICMP 限速。

4. **dig** 是 DNS 诊断的瑞士军刀，支持多种记录类型查询、指定 DNS 服务器、跟踪完整解析链等功能。

### 核心记忆点

```
mtr 丢包判断口诀:
  中间丢，后面好 → 限速，正常
  中间丢，后面糟 → 故障，报修
  全部丢 → 本地网络问题
  最后丢 → 目标或终点限速
```

### 问题记录

- [ ] mtr 的 TCP 模式 (-T) 和 UDP 模式在实际排查中的差异
- [ ] 如何通过 BGP Looking Glass 跨运营商验证路由
- [ ] eBPF 在网络诊断中的应用 (xcap, trace-cmd)

### 延伸思考

- 如何自动化持续监控网络质量？→ SmokePing + Grafana
- 多地域网络质量监控方案？→ 全球探测节点 + 集中分析
- SD-WAN 如何影响传统网络诊断工具？→ 可能需要新的检测策略

---

## ✅ 完成检查

- [x] 掌握了 ping 的核心用法和 ICMP 协议原理
- [x] 理解了 traceroute 的 TTL 工作机制
- [x] 熟练使用 mtr 进行网络质量分析
- [x] 掌握了 dig 的各种 DNS 查询方法
- [x] 完成了 SRE 实战案例：80% 丢包 → 运营商问题
- [x] 完成了练习：多云厂商网络质量对比
- [x] 完成了扩展：fping 批量延迟报告

### 自我评估

| 技能 | 掌握程度 | 验证方式 |
|------|---------|---------|
| ping 排查 | ⭐⭐⭐⭐ | 能通过 ping 判断网络质量 |
| traceroute 分析 | ⭐⭐⭐⭐ | 能识别路由异常 |
| mtr 实战 | ⭐⭐⭐⭐⭐ | 能独立分析丢包原因 |
| dig DNS 诊断 | ⭐⭐⭐⭐ | 能排查 DNS 问题 |
| 脚本编写 | ⭐⭐⭐⭐ | 能编写自动化诊断脚本 |

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 ICMP Echo Request/Reply 的工作原理
- [ ] 能说明 TTL 机制以及 traceroute 如何利用它
- [ ] 能区分 mtr 输出中的真实丢包和 ICMP 限速
- [ ] 能解释 DNS 递归查询和迭代查询的区别
- [ ] 能说明 DNSSEC 的验证链（Root → TLD → 权威）
- [ ] 能解释 ping 的 MTU 路径发现原理

### 实操检查点
- [ ] 能用 `ping -M do -s` 测试路径 MTU
- [ ] 能用 `traceroute -T -p 443` 绕过 ICMP 防火墙
- [ ] 能用 `mtr -r -c 100` 生成网络质量报告
- [ ] 能用 `dig +trace` 追踪完整 DNS 解析链
- [ ] 能用 `dig +dnssec` 验证 DNSSEC 签名
- [ ] 能用 fping 批量测试多目标延迟
- [ ] 能编写自动化网络诊断脚本
- [ ] 能用 mtr 实现持续网络质量监控

### 故障排查能力检查
- [ ] 能通过 mtr 报告定位运营商丢包问题
- [ ] 能通过 dig 对比不同 DNS 服务器的结果
- [ ] 能通过 traceroute 发现路由环路
- [ ] 能用二分法定位网络故障节点
- [ ] 能区分客户端、运营商、服务端的网络问题

---

> 📌 **明日预告**：Day 37 将深入学习 nc、curl、wget 的高级用法，包括 curl 时间分解、nc 端口测试实战、健康检查脚本编写等。
