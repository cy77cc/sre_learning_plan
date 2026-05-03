# Day 39: iptables/nftables 防火墙 + 云安全组

> 📅 日期：2026-05-02
> 📖 学习主题：iptables/nftables 防火墙 + 云安全组 + fail2ban
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 30 TCP 协议、Day 32 IP 协议、Day 38 tcpdump

## 🎯 学习目标

- 理解 Linux 防火墙架构（Netfilter 框架、Hook 点、表/链/规则）
- 掌握 iptables 四表五链的完整概念和常用规则配置
- 理解 NAT（SNAT/DNAT/MASQUERADE）和连接追踪（conntrack）
- 掌握 nftables 的语法和从 iptables 迁移的策略
- 能配置云安全组和 fail2ban 实现自动化安全防护

---

## 📖 核心知识点

### 1. Linux 防火墙架构 — Netfilter 框架

#### 1.1 Netfilter 是什么

Netfilter 是 Linux 内核中的数据包过滤框架，工作在内核网络协议栈的多个关键位置。iptables 和 nftables 都是 Netfilter 的用户空间管理工具。

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户空间 (User Space)                       │
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│   │   iptables   │    │   nftables   │    │     firewalld        │  │
│   │   (传统工具)  │    │   (新工具)   │    │   (高级前端)         │  │
│   └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│          │                   │                       │              │
├──────────┼───────────────────┼───────────────────────┼──────────────┤
│          │    内核空间        │                       │              │
│          ▼                   ▼                       ▼              │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    Netfilter 框架                            │   │
│   │                                                             │   │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │   │
│   │   │  raw    │  │ mangle  │  │  nat    │  │ filter  │      │   │
│   │   │ (表)    │  │ (表)    │  │ (表)    │  │ (表)    │      │   │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘      │   │
│   │                                                             │   │
│   │   ┌──────────────────────────────────────────────────────┐  │   │
│   │   │              5 个 Hook 点                            │  │   │
│   │   │  NF_INET_PRE_ROUTING                                │  │   │
│   │   │  NF_INET_LOCAL_IN                                   │  │   │
│   │   │  NF_INET_FORWARD                                    │  │   │
│   │   │  NF_INET_LOCAL_OUT                                  │  │   │
│   │   │  NF_INET_POST_ROUTING                               │  │   │
│   │   └──────────────────────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│                     IP 协议栈正常处理                                 │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 Netfilter 的 5 个 Hook 点

Netfilter 在内核网络协议栈中定义了 5 个 Hook 点（挂载点），数据包经过这些点时会触发注册的回调函数：

| Hook 点 | 内核常量 | 触发时机 |
|---------|----------|----------|
| PREROUTING | NF_INET_PRE_ROUTING | 数据包到达后，路由判断前 |
| INPUT | NF_INET_LOCAL_IN | 目标为本机的数据包，路由判断后 |
| FORWARD | NF_INET_FORWARD | 经过本机转发的数据包 |
| OUTPUT | NF_INET_LOCAL_OUT | 本机产生的数据包 |
| POSTROUTING | NF_INET_POST_ROUTING | 数据包离开前，路由判断后 |

#### 1.3 数据包完整流经路径

```
                        ┌──────────────────────────┐
                        │      外部网络数据包       │
                        └─────────────┬────────────┘
                                      │
                                      ▼
                            ┌───────────────────┐
                            │    PREROUTING     │  raw → mangle → nat (DNAT)
                            └─────────┬─────────┘
                                      │
                            ┌─────────┴─────────┐
                            │    路由决策        │
                            │  目标IP是本机？    │
                            └───┬───────────┬───┘
                                │           │
                          是 → INPUT    否 → FORWARD
                                │           │
                          mangle → filter   mangle → filter
                                │           │
                                ▼           ▼
                          ┌──────────┐  ┌──────────────┐
                          │ 本地进程 │  │ POSTROUTING  │
                          └────┬─────┘  │ mangle → nat │
                               │        │   (SNAT/MASQ) │
                               ▼        └───────┬──────┘
                          ┌──────────┐          │
                          │  OUTPUT  │          ▼
                          │ raw→mangle│    ┌──────────┐
                          │ →nat→filter│   │ 发送到   │
                          └────┬─────┘   │ 外部网络  │
                               │         └──────────┘
                               ▼
                        ┌──────────────┐
                        │ POSTROUTING  │  mangle → nat (SNAT/MASQUERADE)
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   发送到      │
                        │   外部网络    │
                        └──────────────┘
```

**SRE 关键理解**：
- PREROUTING 是数据包进入后的第一个检查点
- 路由决策决定数据包走 INPUT（本机处理）还是 FORWARD（转发）
- POSTROUTING 是数据包离开前的最后一个检查点
- DNAT 在 PREROUTING 阶段执行（修改目标地址）
- SNAT/MASQUERADE 在 POSTROUTING 阶段执行（修改源地址）

---

### 2. iptables 深入

#### 2.1 四表详解

iptables 有四张表，每张表负责不同的功能，优先级从高到低为：raw → mangle → nat → filter

| 表名 | 优先级 | 功能 | 内核模块 |
|------|--------|------|----------|
| **raw** | 最高 | 连接追踪之前处理，可跳过 conntrack | iptable_raw |
| **mangle** | 高 | 修改数据包头部（TTL、TOS、MARK） | iptable_mangle |
| **nat** | 中 | 网络地址转换（SNAT、DNAT、MASQUERADE） | iptable_nat |
| **filter** | 低 | 数据包过滤（默认表） | iptable_filter |

**raw 表**：

```bash
# raw 表用于在连接追踪之前处理数据包
# 主要用途：跳过连接追踪（NOTRACK），提高性能

# 对特定流量禁用连接追踪（适合高并发场景）
sudo iptables -t raw -A PREROUTING -p tcp --dport 80 -j NOTRACK
sudo iptables -t raw -A OUTPUT -p tcp --sport 80 -j NOTRACK
```

**mangle 表**：

```bash
# mangle 表用于修改数据包的头部字段

# 修改 TTL（隐藏跳数）
sudo iptables -t mangle -A PREROUTING -i eth0 -j TTL --ttl-set 64

# 设置 DSCP 标记（QoS）
sudo iptables -t mangle -A FORWARD -p tcp --dport 443 -j DSCP --set-dscp 46

# MARK 标记（配合策略路由）
sudo iptables -t mangle -A PREROUTING -s 10.0.1.0/24 -j MARK --set-mark 1
```

**nat 表**：

```bash
# nat 表用于网络地址转换

# DNAT：将外部 8080 端口转发到内部 10.0.1.50:80
sudo iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination 10.0.1.50:80

# SNAT：将内网流量的源地址改为公网 IP
sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o eth0 -j SNAT --to-source 203.0.113.1

# MASQUERADE：动态 SNAT（适用于动态 IP，如拨号上网）
sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o eth0 -j MASQUERADE

# 本机端口重定向
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
```

**filter 表**（默认表）：

```bash
# filter 表用于数据包过滤，是最常用的表

# 允许 HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 拒绝其他所有入站
sudo iptables -P INPUT DROP
```

#### 2.2 五链详解

| 链名 | 触发时机 | 可用表 | 常见用途 |
|------|----------|--------|----------|
| **PREROUTING** | 数据包到达后，路由判断前 | raw, mangle, nat | DNAT、端口转发、标记 |
| **INPUT** | 目标为本机的数据包 | mangle, filter | 入站过滤 |
| **FORWARD** | 经过本机转发的数据包 | mangle, filter | 转发过滤 |
| **OUTPUT** | 本机产生的数据包 | raw, mangle, nat, filter | 出站过滤 |
| **POSTROUTING** | 数据包离开前 | mangle, nat | SNAT、MASQUERADE |

#### 2.3 规则匹配详解

**基本语法**：

```bash
iptables [-t 表名] 操作 链名 [匹配条件] [-j 动作]
```

**常用操作**：

| 操作 | 参数 | 说明 |
|------|------|------|
| 追加 | `-A` | 在链尾追加规则 |
| 插入 | `-I [位置]` | 在指定位置插入规则（默认第 1 行） |
| 删除 | `-D` | 删除规则（按内容或行号） |
| 替换 | `-R` | 替换指定位置的规则 |
| 清空 | `-F` | 清空链中所有规则 |
| 列出 | `-L` | 列出规则 |
| 设置策略 | `-P` | 设置链的默认策略 |
| 新建链 | `-N` | 创建自定义链 |
| 删除链 | `-X` | 删除自定义链 |

**匹配条件详解**：

| 条件 | 参数 | 说明 | 示例 |
|------|------|------|------|
| 源 IP | `-s` | 匹配源地址 | `-s 10.0.1.100` |
| 目标 IP | `-d` | 匹配目标地址 | `-d 10.0.1.50` |
| 协议 | `-p` | 匹配协议 | `-p tcp` / `-p udp` / `-p icmp` |
| 源端口 | `--sport` | 匹配源端口 | `--sport 12345` |
| 目标端口 | `--dport` | 匹配目标端口 | `--dport 80` |
| 多端口 | `--dports` | 匹配多个端口 | `-m multiport --dports 80,443` |
| 入站网卡 | `-i` | 匹配进入的网卡 | `-i eth0` |
| 出站网卡 | `-o` | 匹配发出的网卡 | `-o eth0` |
| 连接状态 | `-m conntrack --ctstate` | 匹配连接状态 | `ESTABLISHED,RELATED` |
| 速率限制 | `-m limit` | 限速 | `--limit 100/sec` |
| 连接数限制 | `-m connlimit` | 限制并发连接 | `--connlimit-above 50` |
| 字符串匹配 | `-m string` | 匹配数据包内容 | `--string "GET" --algo bm` |
| 时间匹配 | `-m time` | 按时间匹配 | `--timestart 08:00 --timestop 18:00` |
| IP 范围 | `-m iprange` | 匹配 IP 范围 | `--src-range 10.0.1.1-10.0.1.100` |
| TTL | `-m ttl` | 匹配 TTL 值 | `--ttl-eq 64` |
| MAC 地址 | `-m mac` | 匹配 MAC 地址 | `--mac-source aa:bb:cc:dd:ee:ff` |

**动作（Target）详解**：

| 动作 | 参数 | 说明 |
|------|------|------|
| 接受 | `-j ACCEPT` | 允许数据包通过 |
| 丢弃 | `-j DROP` | 静默丢弃（不回复） |
| 拒绝 | `-j REJECT` | 拒绝并返回错误信息 |
| 记录日志 | `-j LOG` | 记录到 syslog |
| 跳转 | `-j <自定义链>` | 跳转到自定义链 |
| 返回 | `-j RETURN` | 从自定义链返回主链 |
| SNAT | `-j SNAT` | 源地址转换 |
| DNAT | `-j DNAT` | 目标地址转换 |
| MASQUERADE | `-j MASQUERADE` | 动态源地址转换 |
| REDIRECT | `-j REDIRECT` | 端口重定向 |
| MARK | `-j MARK` | 设置标记 |

#### 2.4 连接追踪（conntrack）

conntrack 是 Netfilter 的连接追踪模块，是状态防火墙和 NAT 的基础。

```bash
# 查看连接追踪表
sudo conntrack -L

# 查看连接追踪统计
sudo conntrack -S

# 查看最大连接追踪数
sudo sysctl net.netfilter.nf_conntrack_max

# 调整最大连接追踪数（高并发场景）
sudo sysctl -w net.netfilter.nf_conntrack_max=1000000

# 查看当前连接追踪数量
sudo cat /proc/sys/net/netfilter/nf_conntrack_count

# 查看连接追踪超时时间
sudo sysctl net.netfilter.nf_conntrack_tcp_timeout_established
sudo sysctl net.netfilter.nf_conntrack_tcp_timeout_time_wait

# 调整超时（减少 TIME_WAIT 占用）
sudo sysctl -w net.netfilter.nf_conntrack_tcp_timeout_time_wait=30

# 清空连接追踪表（谨慎使用）
sudo conntrack -F
```

**连接状态说明**：

| 状态 | 说明 | 示例 |
|------|------|------|
| NEW | 新建连接 | SYN 包 |
| ESTABLISHED | 已建立的连接 | 数据传输中 |
| RELATED | 相关连接 | FTP 数据连接、ICMP 错误 |
| INVALID | 无效数据包 | 无法识别的包 |
| UNTRACKED | 未追踪 | 被 NOTRACK 标记的包 |

```bash
# 基于状态的防火墙规则（推荐）
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -m conntrack --ctstate INVALID -j DROP
sudo iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -j ACCEPT
```

#### 2.5 NAT 配置详解

**SNAT（源地址转换）**：

```bash
# 场景：内网服务器访问外网时，将源地址改为公网 IP
# 前提：启用 IP 转发
sudo sysctl -w net.ipv4.ip_forward=1

# SNAT（固定公网 IP）
sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o eth0 -j SNAT --to-source 203.0.113.1

# MASQUERADE（动态公网 IP，如 DHCP/拨号）
sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o eth0 -j MASQUERADE
```

**DNAT（目标地址转换）**：

```bash
# 场景：将外部请求转发到内部服务器
# 端口转发：外部 8080 → 内部 10.0.1.50:80
sudo iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination 10.0.1.50:80

# 同时需要允许 FORWARD
sudo iptables -A FORWARD -p tcp -d 10.0.1.50 --dport 80 -j ACCEPT

# 完整的端口转发配置
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination 10.0.1.50:80
sudo iptables -t nat -A POSTROUTING -p tcp -d 10.0.1.50 --dport 80 -j MASQUERADE
sudo iptables -A FORWARD -p tcp -d 10.0.1.50 --dport 80 -j ACCEPT
sudo iptables -A FORWARD -p tcp -s 10.0.1.50 --sport 80 -j ACCEPT
```

#### 2.6 常用规则示例

```bash
# ===== 基础安全规则 =====

# 允许已建立的连接（重要！避免把自己锁在外面）
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# 允许本地回环
sudo iptables -A INPUT -i lo -j ACCEPT

# 允许 SSH（先放行，避免断连！）
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许 ICMP（限速防 Ping Flood）
sudo iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s --limit-burst 4 -j ACCEPT

# 拒绝特定 IP 段
sudo iptables -A INPUT -s 10.99.99.0/24 -j DROP

# 限速：限制 SSH 连接速率（防暴力破解）
sudo iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set --name SSH
sudo iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP

# 记录被拒绝的包
sudo iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "iptables-drop: " --log-level 4

# 设置默认策略
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# ===== 高级规则 =====

# 防 SYN Flood
sudo iptables -A INPUT -p tcp --syn -m limit --limit 1/s --limit-burst 3 -j ACCEPT
sudo iptables -A INPUT -p tcp --syn -j DROP

# 防端口扫描
sudo iptables -A INPUT -p tcp --tcp-flags ALL NONE -j DROP
sudo iptables -A INPUT -p tcp --tcp-flags ALL ALL -j DROP
sudo iptables -A INPUT -p tcp --tcp-flags ALL FIN,URG,PSH -j DROP
sudo iptables -A INPUT -p tcp --tcp-flags ALL SYN,RST,ACK,FIN,URG -j DROP

# 限制并发连接数
sudo iptables -A INPUT -p tcp --dport 80 -m connlimit --connlimit-above 50 -j REJECT
```

#### 2.7 规则保存与恢复

```bash
# ===== Debian/Ubuntu =====
# 安装持久化工具
sudo apt-get install -y iptables-persistent

# 保存规则
sudo iptables-save > /etc/iptables/rules.v4
sudo ip6tables-save > /etc/iptables/rules.v6

# 恢复规则
sudo iptables-restore < /etc/iptables/rules.v4

# 开机自动加载
sudo systemctl enable netfilter-persistent

# ===== RHEL/CentOS/Rocky =====
# 保存规则
sudo service iptables save
# 或
sudo iptables-save > /etc/sysconfig/iptables

# 恢复规则
sudo iptables-restore < /etc/sysconfig/iptables

# 开机自动加载
sudo systemctl enable iptables
```

#### 2.8 iptables 规则输出解读

```bash
$ sudo iptables -L INPUT -n -v --line-numbers
Chain INPUT (policy DROP)
num   pkts bytes target     prot opt in     out     source               destination
1     1.2M  800M ACCEPT     0    --  lo     *       0.0.0.0/0            0.0.0.0/0
2     5.6M  3.2G ACCEPT     0    --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate RELATED,ESTABLISHED
3      10K  600K ACCEPT     6    --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:22
4       5K  300K ACCEPT     6    --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:80
5       2K  120K ACCEPT     6    --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:443
6       1K   60K DROP       0    --  *      *       10.99.99.0/24        0.0.0.0/0
7       500  30K LOG        0    --  *      *       0.0.0.0/0            0.0.0.0/0            LOG flags 0 level 4 prefix "iptables-drop: "
```

| 列名 | 含义 |
|------|------|
| num | 规则行号（用于插入/删除） |
| pkts | 匹配的包数量 |
| bytes | 匹配的字节数 |
| target | 动作（ACCEPT/DROP/REJECT/LOG） |
| prot | 协议（0=all, 6=tcp, 17=udp, 1=icmp） |
| opt | 选项 |
| in | 入站网卡（* = 任意） |
| out | 出站网卡（* = 任意） |
| source | 源地址 |
| destination | 目标地址 |

---

### 3. nftables — iptables 的继任者

#### 3.1 为什么需要 nftables

iptables 存在的问题：
- **性能差**：规则线性匹配，规则多时性能下降
- **语法繁琐**：IPv4 和 IPv6 需要分别管理
- **不支持原子操作**：逐条加载规则，可能出现中间状态
- **需要 ipset**：集合功能需要额外模块

nftables 的改进：
- **统一框架**：替代 iptables、ip6tables、arptables、ebtables
- **更好的性能**：支持集合（set）和映射（map），匹配效率更高
- **原子操作**：整表替换，避免中间状态
- **更简洁的语法**：声明式配置

#### 3.2 nftables vs iptables 对比

| 特性 | iptables | nftables |
|------|----------|----------|
| 内核集成 | 多个独立模块 | 统一框架（nf_tables） |
| 规则语法 | 繁琐，多命令 | 简洁，声明式 |
| 性能 | 线性匹配 | 集合匹配（O(1)） |
| 原子操作 | 逐条加载 | 整表原子替换 |
| IPv4/IPv6 | 分开管理 | 统一管理（inet 族） |
| 集合/映射 | 需要 ipset | 原生支持 |
| 日志 | `-j LOG` | `log prefix "msg"` |
| 引入时间 | 1999 年 | 2014 年（Linux 3.13+） |
| 默认使用 | CentOS 7, Ubuntu 18.04 | RHEL 8+, Debian 10+, Ubuntu 20.04+ |

#### 3.3 nftables 架构

```
nftables 层次结构：
┌───────────────────────────────────┐
│           nftables                │
│  ┌─────────────────────────────┐  │
│  │    table (表)               │  │
│  │    族: ip/ip6/inet/arp/...  │  │
│  │  ┌───────────────────────┐  │  │
│  │  │    chain (链)         │  │  │
│  │  │    类型: filter/nat   │  │  │
│  │  │    hook: input/output │  │  │
│  │  │  ┌─────────────────┐  │  │  │
│  │  │  │   rule (规则)   │  │  │  │
│  │  │  │   rule (规则)   │  │  │  │
│  │  │  └─────────────────┘  │  │  │
│  │  └───────────────────────┘  │  │
│  └─────────────────────────────┘  │
└───────────────────────────────────┘

族(family):
  ip      - 仅 IPv4
  ip6     - 仅 IPv6
  inet    - IPv4 + IPv6（推荐）
  arp     - ARP
  bridge  - 桥接
  netdev  - 网络设备

表类型(type):
  filter  - 过滤（默认）
  nat     - 地址转换
  route   - 路由
```

#### 3.4 nftables 基本命令

```bash
# 安装 nftables
sudo apt-get install -y nftables     # Debian/Ubuntu
sudo yum install -y nftables         # RHEL/CentOS 8+

# 启动并启用
sudo systemctl enable --now nftables

# ===== 查看规则 =====
sudo nft list ruleset                 # 查看所有规则
sudo nft list table inet filter       # 查看特定表
sudo nft -a list ruleset              # 查看所有规则（含句柄）

# ===== 创建表 =====
sudo nft add table inet myfilter      # 创建 inet 族的表

# ===== 创建链 =====
# 语法：nft add chain <族> <表> <链名> { type <类型> hook <钩子> priority <优先级> \; policy <策略> \; }
sudo nft add chain inet myfilter input \
  { type filter hook input priority 0 \; policy drop \; }
sudo nft add chain inet myfilter forward \
  { type filter hook forward priority 0 \; policy drop \; }
sudo nft add chain inet myfilter output \
  { type filter hook output priority 0 \; policy accept \; }

# ===== 添加规则 =====
# 允许回环
sudo nft add rule inet myfilter input iifname lo accept

# 允许已建立的连接
sudo nft add rule inet myfilter input ct state established,related accept

# 丢弃无效连接
sudo nft add rule inet myfilter input ct state invalid drop

# 允许 SSH
sudo nft add rule inet myfilter input tcp dport 22 accept

# 允许 HTTP/HTTPS（多端口）
sudo nft add rule inet myfilter input tcp dport { 80, 443 } accept

# 允许 ICMP
sudo nft add rule inet myfilter input ip protocol icmp accept

# 使用集合（set）
sudo nft add set inet myfilter allowlist { type ipv4_addr \; }
sudo nft add element inet myfilter allowlist { 192.168.1.100, 192.168.1.101, 10.0.0.50 }
sudo nft add rule inet myfilter input ip saddr @allowlist accept

# 动态集合（超时自动过期）
sudo nft add set inet myfilter banlist { type ipv4_addr \; flags timeout \; timeout 1h \; }
sudo nft add element inet myfilter banlist { 10.99.99.99 timeout 30m }
sudo nft add rule inet myfilter input ip saddr @banlist drop

# ===== 管理规则 =====
# 按句柄删除规则
sudo nft -a list inet myfilter input    # 查看句柄
sudo nft delete rule inet myfilter input handle 5

# 清空表
sudo nft flush table inet myfilter

# 删除表
sudo nft delete table inet myfilter

# ===== 保存与加载 =====
sudo nft list ruleset > /etc/nftables.conf    # 保存
sudo nft -f /etc/nftables.conf                 # 加载
```

#### 3.5 nftables 配置文件示例

```bash
#!/usr/sbin/nft -f

# 清空现有规则
flush ruleset

table inet filter {
    # 定义集合
    set allowed_ips {
        type ipv4_addr
        elements = { 192.168.1.100, 10.0.0.50 }
    }

    set blocked_ports {
        type inet_service
        elements = { 23, 135, 139, 445 }
    }

    chain input {
        type filter hook input priority 0; policy drop;

        # 允许回环
        iifname "lo" accept

        # 允许已建立的连接
        ct state established,related accept

        # 丢弃无效连接
        ct state invalid drop

        # 允许 ICMP
        ip protocol icmp accept

        # 允许 SSH（限制来源）
        ip saddr @allowed_ips tcp dport 22 accept

        # 允许 HTTP/HTTPS
        tcp dport { 80, 443 } accept

        # 允许监控端口
        tcp dport { 9090, 9100, 9115 } accept  # Prometheus

        # 阻止危险端口
        tcp dport @blocked_ports drop

        # 限速防暴力破解
        tcp dport 22 ct state new limit rate 3/minute accept

        # 记录并拒绝其他
        log prefix "[nftables-input-drop] " level info
        counter drop
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}
```

#### 3.6 从 iptables 迁移到 nftables

```bash
# 方法 1：使用 iptables-translate 工具
# 将 iptables 规则转换为 nftables 规则
sudo iptables-translate -A INPUT -p tcp --dport 80 -j ACCEPT
# 输出：nft add rule ip filter INPUT tcp dport 80 counter accept

# 批量转换
sudo iptables-save | iptables-restore-translate > /tmp/nftables-ruleset.conf

# 方法 2：手动重写（推荐，可以优化规则结构）

# 方法 3：使用 nftables 兼容层
# nftables 提供了 iptables 兼容层，可以在过渡期使用
sudo update-alternatives --set iptables /usr/sbin/iptables-nft
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-nft
```

---

### 4. firewalld — 高级防火墙前端

#### 4.1 firewalld 简介

firewalld 是 CentOS/RHEL/Fedora 的默认防火墙管理工具，底层使用 nftables（RHEL 8+）或 iptables（RHEL 7）。

```bash
# 检查 firewalld 状态
sudo systemctl status firewalld

# 启动/停止
sudo systemctl start firewalld
sudo systemctl stop firewalld

# 查看默认区域
sudo firewall-cmd --get-default-zone

# 查看所有区域
sudo firewall-cmd --get-zones

# 查看区域详情
sudo firewall-cmd --zone=public --list-all

# 添加服务
sudo firewall-cmd --zone=public --add-service=http --permanent
sudo firewall-cmd --zone=public --add-service=https --permanent

# 添加端口
sudo firewall-cmd --zone=public --add-port=8080/tcp --permanent

# 删除规则
sudo firewall-cmd --zone=public --remove-service=http --permanent

# 重新加载
sudo firewall-cmd --reload

# 添加富规则（Rich Rule）
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="10.0.0.0/8" port port="22" protocol="tcp" accept'

# 端口转发
sudo firewall-cmd --permanent --add-forward-port=port=8080:proto=tcp:toport=80
sudo firewall-cmd --permanent --add-forward-port=port=8080:proto=tcp:toaddr=10.0.1.50:toport=80
```

#### 4.2 firewalld 区域

| 区域 | 默认行为 | 适用场景 |
|------|----------|----------|
| drop | 丢弃所有入站 | 最严格 |
| block | 拒绝所有入站（返回错误） | 严格 |
| public | 仅允许选择的服务 | 公网服务器（默认） |
| external | 伪装（MASQUERADE） | 外部网络 |
| internal | 信任大部分 | 内部网络 |
| trusted | 允许所有 | 完全信任 |

---

### 5. 云安全组

#### 5.1 云安全组 vs iptables

| 特性 | iptables/nftables | 云安全组 |
|------|-------------------|----------|
| 运行位置 | 操作系统内核 | 虚拟化层/Hypervisor |
| 管理方式 | 命令行 | Web 控制台 / API / Terraform |
| 规则方向 | 入站+出站都需要配置 | 通常有状态（自动放行回包） |
| 性能影响 | 消耗 CPU | 几乎无影响（硬件加速） |
| 适用场景 | 主机级别精细控制 | 实例级别粗粒度控制 |
| 日志 | 需额外配置 | 部分云厂商原生支持 |

#### 5.2 AWS 安全组配置

```bash
# 创建安全组
aws ec2 create-security-group \
  --group-name sre-web-sg \
  --description "SRE Web Server Security Group" \
  --vpc-id vpc-12345678

# 添加入站规则
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789 \
  --protocol tcp --port 22 --cidr 10.0.0.0/8

aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789 \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789 \
  --protocol tcp --port 443 --cidr 0.0.0.0/0

# 查看安全组规则
aws ec2 describe-security-groups --group-ids sg-0123456789
```

#### 5.3 Terraform 安全组配置（多云通用）

```hcl
resource "aws_security_group" "sre_web" {
  name        = "sre-web-sg"
  description = "SRE Web Server Security Group"
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH from internal"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "sre-web-sg" }
}
```

#### 5.4 安全组最佳实践

| 原则 | 说明 |
|------|------|
| 最小权限 | 只开放必要端口，源 IP 尽量限制 |
| 分层防护 | 安全组（外层）+ iptables（内层）双重保护 |
| 命名规范 | 明确用途，如 `sre-web-sg`, `sre-db-sg` |
| 定期审计 | 检查是否有过宽的规则（如 0.0.0.0/0 + 22） |
| IaC 管理 | 用 Terraform 等工具管理，避免手动变更 |

---

### 6. fail2ban 自动封禁

#### 6.1 fail2ban 原理

fail2ban 通过分析日志文件，检测暴力破解等恶意行为，自动在防火墙中封禁恶意 IP。

```
日志文件 ──→ fail2ban 监控 ──→ 正则匹配 ──→ 计数器 ──→ 超过阈值？
                                                        │
                                              是 ←──────┘
                                               │
                                               ▼
                                     执行封禁动作（iptables/nftables）
                                               │
                                               ▼
                                     定时解封（bantime 到期）
```

#### 6.2 安装和配置

```bash
# 安装
sudo apt-get update && sudo apt-get install -y fail2ban  # Debian/Ubuntu
sudo yum install -y epel-release && sudo yum install -y fail2ban  # RHEL/CentOS

# 创建本地配置
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

**关键配置（jail.local）**：

```ini
[DEFAULT]
# 白名单 IP
ignoreip = 127.0.0.1/8 10.0.0.0/8 192.168.0.0/16

# 封禁时间（秒）
bantime  = 3600

# 查找时间窗口（秒）
findtime = 600

# 最大失败次数
maxretry = 5

# 后端
backend = systemd

# 默认动作
action = iptables-multiport[name=default, port="ssh,http,https"]

# SSH 防护
[sshd]
enabled  = true
port     = ssh
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 3
bantime  = 7200
findtime = 300

# Nginx 登录防护
[nginx-http-auth]
enabled  = true
port     = http,https
filter   = nginx-http-auth
logpath  = /var/log/nginx/error.log
maxretry = 3
bantime  = 3600

# Nginx CC 攻击防护
[nginx-cc]
enabled  = true
port     = http,https
filter   = nginx-cc
logpath  = /var/log/nginx/access.log
maxretry = 100
findtime = 60
bantime  = 1800
```

#### 6.3 管理和监控

```bash
# 启动
sudo systemctl enable --now fail2ban

# 查看状态
sudo fail2ban-client status

# 查看特定 jail
sudo fail2ban-client status sshd

# 手动封禁/解封
sudo fail2ban-client set sshd banip 45.148.10.23
sudo fail2ban-client set sshd unbanip 45.148.10.23

# 查看封禁 IP
sudo fail2ban-client get sshd banip

# 重载配置
sudo fail2ban-client reload

# 查看日志
sudo tail -f /var/log/fail2ban.log
```

---

### 7. SRE 实战案例

#### 7.1 案例一：fail2ban 自动封禁暴力破解

**背景**：公网服务器持续遭到 SSH 暴力破解，每分钟数百次失败登录。

```bash
# 查看攻击情况
sudo grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -20

# 安装并配置 fail2ban
sudo apt-get install -y fail2ban
sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[DEFAULT]
ignoreip = 127.0.0.1/8 10.0.0.0/8
bantime = 7200
findtime = 300
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
EOF

sudo systemctl enable --now fail2ban

# 验证效果
sudo fail2ban-client status sshd
# Currently banned: 12
# Total banned: 47
```

#### 7.2 案例二：端口转发配置

**场景**：将外部 8080 端口转发到内部服务器 10.0.1.50:80

```bash
# 启用 IP 转发
sudo sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf

# iptables 端口转发
sudo iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination 10.0.1.50:80
sudo iptables -t nat -A POSTROUTING -p tcp -d 10.0.1.50 --dport 80 -j MASQUERADE
sudo iptables -A FORWARD -p tcp -d 10.0.1.50 --dport 80 -j ACCEPT
sudo iptables -A FORWARD -p tcp -s 10.0.1.50 --sport 80 -j ACCEPT

# 验证
curl -v http://localhost:8080
sudo iptables -t nat -L -n -v
```

#### 7.3 案例三：容器网络与 iptables

**背景**：Docker/Kubernetes 与 iptables 的关系

```bash
# Docker 创建的 iptables 链
sudo iptables -L -n -v | grep -i docker
# DOCKER - 用户定义网络
# DOCKER-ISOLATION-STAGE-1 - 网络隔离
# DOCKER-ISOLATION-STAGE-2 - 网络隔离

# 查看 Docker 的 NAT 规则
sudo iptables -t nat -L -n -v | grep -i docker

# K8s 创建的 iptables 链（kube-proxy）
sudo iptables -L -n -v | grep -i kube
# KUBE-SERVICES - 服务规则
# KUBE-EXTERNAL-SERVICES - 外部服务
# KUBE-FIREWALL - 防火墙规则

# 注意事项：
# 1. 不要直接修改 Docker/K8s 创建的链
# 2. 使用 Docker/K8s 的 API 管理网络规则
# 3. 重启 Docker/K8s 会重建 iptables 规则
# 4. 使用 `iptables -F` 可能导致容器网络中断
```

---

## 💻 实战练习

### 练习 1：配置基本防火墙

```bash
# 备份现有规则
sudo iptables-save > ~/iptables-backup-$(date +%Y%m%d).bak

# 清空规则
sudo iptables -F
sudo iptables -X

# 设置默认策略
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# 添加规则
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT

# 查看规则
sudo iptables -L -n -v --line-numbers

# 保存
sudo iptables-save > /etc/iptables/rules.v4
```

### 练习 2：nftables 实现相同规则

```bash
sudo nft flush ruleset

sudo nft add table inet firewall
sudo nft add chain inet firewall input '{ type filter hook input priority 0\; policy drop\; }'
sudo nft add chain inet firewall forward '{ type filter hook forward priority 0\; policy drop\; }'
sudo nft add chain inet firewall output '{ type filter hook output priority 0\; policy accept\; }'

sudo nft add rule inet firewall input iifname lo accept
sudo nft add rule inet firewall input ct state established,related accept
sudo nft add rule inet firewall input ct state invalid drop
sudo nft add rule inet firewall input tcp dport 22 accept
sudo nft add rule inet firewall input tcp dport { 80, 443 } accept
sudo nft add rule inet firewall input ip protocol icmp accept

sudo nft list ruleset
sudo nft list ruleset > /etc/nftables.conf
```

### 练习 3：NAT 配置

```bash
# 场景：搭建一个简单的 NAT 网关
# eth0 = 外网，eth1 = 内网 (10.0.0.0/24)

# 启用转发
sudo sysctl -w net.ipv4.ip_forward=1

# SNAT（内网访问外网）
sudo iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o eth0 -j MASQUERADE

# DNAT（外部访问内部 Web 服务器）
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j DNAT --to-destination 10.0.0.100:80
sudo iptables -A FORWARD -p tcp -d 10.0.0.100 --dport 80 -j ACCEPT

# 查看 NAT 规则
sudo iptables -t nat -L -n -v
```

---

## 🎯 面试题精选

### Q1：iptables 的四表五链是什么？数据包是如何流经这些链的？

**参考答案**：

**四表**（优先级从高到低）：
- raw：连接追踪之前处理
- mangle：修改数据包头部
- nat：网络地址转换
- filter：数据包过滤（默认）

**五链**：
- PREROUTING：数据包到达后，路由判断前
- INPUT：目标为本机
- FORWARD：经过本机转发
- OUTPUT：本机产生
- POSTROUTING：数据包离开前

**数据包流向**：
- 入站：PREROUTING → 路由判断 → INPUT → 本地进程
- 转发：PREROUTING → 路由判断 → FORWARD → POSTROUTING
- 出站：本地进程 → OUTPUT → POSTROUTING

### Q2：SNAT 和 DNAT 的区别是什么？

**参考答案**：

- **SNAT（Source NAT）**：修改数据包的**源地址**，用于内网服务器访问外网时隐藏内网 IP。在 POSTROUTING 链执行。
- **DNAT（Destination NAT）**：修改数据包的**目标地址**，用于将外部请求转发到内部服务器。在 PREROUTING 链执行。

```
SNAT：内网 10.0.1.100 → 外网时源地址改为 203.0.113.1
DNAT：外部访问 203.0.113.1:8080 → 转发到 10.0.1.50:80
```

### Q3：nftables 相比 iptables 有什么优势？

**参考答案**：

1. **统一框架**：替代 iptables/ip6tables/arptables/ebtables
2. **更好的性能**：支持集合（set），匹配效率 O(1)
3. **原子操作**：整表替换，避免中间状态
4. **更简洁的语法**：声明式配置
5. **原生 IPv4/IPv6 双栈**：使用 inet 族统一管理
6. **动态集合**：支持超时自动过期

### Q4：什么是 conntrack？为什么它可能导致性能问题？

**参考答案**：

conntrack（连接追踪）是 Netfilter 的模块，用于追踪每个连接的状态（NEW、ESTABLISHED、RELATED 等）。它是状态防火墙和 NAT 的基础。

**性能问题**：
- 每个连接都需要在 conntrack 表中创建条目
- 高并发时 conntrack 表可能满（默认 65536）
- conntrack 表满后新连接被丢弃

**解决方案**：
```bash
# 增大 conntrack 表
sudo sysctl -w net.netfilter.nf_conntrack_max=1000000

# 对高流量服务禁用 conntrack
sudo iptables -t raw -A PREROUTING -p tcp --dport 80 -j NOTRACK
```

### Q5：如何防止 SSH 暴力破解？

**参考答案**：

```bash
# 方法 1：iptables 限速
sudo iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW \
  -m recent --set --name SSH
sudo iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW \
  -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP

# 方法 2：fail2ban
sudo apt-get install -y fail2ban
# 配置 jail.local，maxretry=3, bantime=7200

# 方法 3：密钥认证 + 禁用密码登录
# /etc/ssh/sshd_config:
# PasswordAuthentication no
# PermitRootLogin no

# 方法 4：修改 SSH 端口
# /etc/ssh/sshd_config:
# Port 2222
```

---

## 📚 深入阅读

| 资源 | 链接 |
|------|------|
| iptables 官方文档 | https://www.netfilter.org/documentation/ |
| nftables 官方 wiki | https://wiki.nftables.org/ |
| fail2ban 官方文档 | https://www.fail2ban.org/wiki/index.php/Main_Page |
| AWS 安全组文档 | https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html |
| 阿里云安全组文档 | https://help.aliyun.com/zh/ecs/user-guide/security-group-overview |
| nftables 迁移指南 | https://wiki.nftables.org/wiki-nftables/index.php/Moving_from_iptables_to_nftables |

---

## ✅ 自检清单

- [ ] 理解 Netfilter 框架和 5 个 Hook 点
- [ ] 掌握 iptables 四表五链的概念和数据包流向
- [ ] 能配置基本的 iptables 防火墙规则
- [ ] 理解 NAT（SNAT/DNAT/MASQUERADE）的工作原理
- [ ] 理解 conntrack 连接追踪及其性能影响
- [ ] 掌握 nftables 的基本语法和配置
- [ ] 能配置云安全组（AWS/阿里云）
- [ ] 能配置 fail2ban 自动封禁暴力破解
- [ ] 理解容器网络与 iptables 的关系
- [ ] 完成所有实战练习
