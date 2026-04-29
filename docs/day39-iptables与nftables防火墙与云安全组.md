# SRE 学习计划 — Day 39：iptables/nftables 防火墙 + 云安全组

---

## 📅 基本信息

| 项目 | 内容 |
|------|------|
| **天数** | Day 39 |
| **主题** | iptables/nftables 防火墙 + 云安全组 |
| **难度** | ⭐⭐⭐ 中级 |
| **预计时间** | 2-3 小时 |
| **前置知识** | Linux 网络基础、TCP/IP 协议、Day 38 tcpdump 基础 |

---

## 📖 目录

1. [iptables 基础](#1-iptables-基础)
2. [iptables 表与链结构](#2-iptables-表与链结构)
3. [nftables — iptables 的后继者](#3-nftables--iptables-的后继者)
4. [云安全组](#4-云安全组)
5. [SRE 实战案例：fail2ban + iptables 自动封禁](#5-sre-实战案例fail2ban--iptables-自动封禁)
6. [练习](#6-练习)
7. [扩展：端口转发 + fail2ban 安装配置](#7-扩展端口转发--fail2ban-安装配置)
8. [资源](#8-资源)

---

## 1. iptables 基础

### 1.1 什么是 iptables？

iptables 是 Linux 内核中 **netfilter** 框架的用户空间管理工具，用于配置 IPv4 数据包过滤规则。它是 Linux 系统上最经典的防火墙工具。

```
+----------------------------------------------+
|              用户空间 (User Space)             |
|                                              |
|   ┌─────────────────────────────────────┐     |
|   │        iptables (命令行工具)         │     |
|   └──────────────────┬──────────────────┘     |
|                      │                        |
|                      ▼                        |
|              netfilter API                    |
+----------------------------------------------+
|              内核空间 (Kernel Space)           |
|                                              |
|   ┌─────────────────────────────────────┐     |
|   │         netfilter 框架               │     |
|   │   ┌─────────┐ ┌───────┐ ┌────────┐  │     |
|   │   │  Filter  │ │  NAT  │ │ Mangle │  │     |
|   │   └─────────┘ └───────┘ └────────┘  │     |
|   └─────────────────────────────────────┘     |
|                      │                        |
|                      ▼                        |
|            IP 协议栈处理流程                    |
+----------------------------------------------+
```

### 1.2 安装与检查

```bash
# 检查 iptables 是否已安装
which iptables
iptables --version

# Debian/Ubuntu 安装
sudo apt-get update && sudo apt-get install -y iptables

# RHEL/CentOS/Rocky 安装
sudo yum install -y iptables iptables-services

# 查看当前规则
sudo iptables -L -n -v

# 查看规则（带行号）
sudo iptables -L -n -v --line-numbers
```

---

## 2. iptables 表与链结构

### 2.1 四表五链架构

**iptables 有四张表，每张表负责不同功能**：

| 表名 | 功能 | 常用场景 |
|------|------|----------|
| **filter** | 数据包过滤（默认表） | 允许/拒绝流量 |
| **nat** | 网络地址转换 | 端口转发、SNAT/MASQUERADE |
| **mangle** | 修改数据包内容 | 修改 TTL、TOS 标记 |
| **raw** | 连接追踪之前处理 | 禁用连接追踪（NOTRACK） |

**五条链定义数据包经过的不同阶段**：

| 链名 | 触发时机 | 可用表 |
|------|----------|--------|
| **PREROUTING** | 数据包到达后，路由判断前 | raw, mangle, nat |
| **INPUT** | 目标为本机的数据包 | mangle, filter |
| **FORWARD** | 经过本机转发的数据包 | mangle, filter |
| **OUTPUT** | 本机发出的数据包 | raw, mangle, nat, filter |
| **POSTROUTING** | 数据包离开前 | mangle, nat |

### 2.2 数据包流向图

```
                ┌─────────────────────────────────┐
                │        外部网络数据包            │
                └────────────────┬────────────────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │  PREROUTING   │  ← raw, mangle, nat
                         └───────┬───────┘
                                 │
                    ┌────────────┴────────────┐
                    │      路由决策            │
                    │  (目标IP 是本机吗？)      │
                    └──────┬──────────┬───────┘
                           │          │
                     是 → 本机    否 → 转发
                           │          │
                           ▼          ▼
                  ┌─────────────┐  ┌──────────┐
                  │   INPUT     │  │ FORWARD  │  ← mangle, filter
                  └──────┬──────┘  └────┬─────┘
                         │              │
                         ▼              ▼
                  ┌─────────────┐  ┌──────────┐
                  │  本地进程    │  │POSTROUTING│ ← mangle, nat
                  └──────┬──────┘  └────┬─────┘
                         │              │
                         ▼              │
                  ┌─────────────┐       │
                  │   OUTPUT    │       │  ← raw, mangle, nat, filter
                  └──────┬──────┘       │
                         │              │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │ POSTROUTING  │  ← mangle, nat
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │   发送到外部   │
                         └──────────────┘
```

### 2.3 基本命令语法

```bash
iptables [-t 表名] 操作 链名 [匹配条件] [-j 动作]
```

**常用操作**：

| 操作 | 参数 | 说明 |
|------|------|------|
| 查看 | `-L` | 列出规则 |
| 追加 | `-A` | 在链尾追加规则 |
| 插入 | `-I` | 在指定位置插入规则 |
| 删除 | `-D` | 删除规则 |
| 替换 | `-R` | 替换规则 |
| 清空 | `-F` | 清空链中所有规则 |
| 设置策略 | `-P` | 设置链的默认策略 |

**常用匹配条件**：

| 条件 | 参数 | 说明 |
|------|------|------|
| 源 IP | `-s <IP/CIDR>` | 匹配源地址 |
| 目标 IP | `-d <IP/CIDR>` | 匹配目标地址 |
| 协议 | `-p <协议>` | tcp, udp, icmp, all |
| 源端口 | `--sport <port>` | 匹配源端口 |
| 目标端口 | `--dport <port>` | 匹配目标端口 |
| 网卡入 | `-i <interface>` | 匹配进入的网卡 |
| 网卡出 | `-o <interface>` | 匹配发出的网卡 |
| 连接状态 | `-m state --state` | NEW, ESTABLISHED, RELATED, INVALID |
| 连接状态(新) | `-m conntrack --ctstate` | 推荐使用，替代 state |

**常用动作 (Target)**：

| 动作 | 参数 | 说明 |
|------|------|------|
| 接受 | `-j ACCEPT` | 允许数据包通过 |
| 拒绝 | `-j DROP` | 静默丢弃（不回复） |
| 拒绝并回复 | `-j REJECT` | 拒绝并返回错误信息 |
| 记录日志 | `-j LOG` | 记录到 syslog |
| 跳转 | `-j <自定义链>` | 跳转到自定义链 |
| 返回 | `-j RETURN` | 从自定义链返回 |

### 2.4 常用规则示例

```bash
# ===== 基本规则 =====

# 允许已建立的连接（重要！避免把自己锁在外面）
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# 允许本地回环
sudo iptables -A INPUT -i lo -j ACCEPT

# 允许 SSH（先放行，避免断连！）
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许特定 IP 访问
sudo iptables -A INPUT -s 192.168.1.100 -j ACCEPT

# 拒绝特定 IP
sudo iptables -A INPUT -s 10.99.99.99 -j DROP

# 允许 ICMP（ping）
sudo iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT

# 设置默认策略为 DROP（白名单模式）
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT  # 通常允许出站

# ===== 保存与恢复 =====

# Debian/Ubuntu 保存规则
sudo iptables-save > /etc/iptables/rules.v4

# RHEL/CentOS 保存规则
sudo service iptables save
# 或
sudo /usr/libexec/iptables/iptables.init save

# 恢复规则
sudo iptables-restore < /etc/iptables/rules.v4

# ===== 规则管理 =====

# 查看规则（带行号）
sudo iptables -L INPUT -n -v --line-numbers

# 按行号删除规则
sudo iptables -D INPUT 3

# 删除某条具体规则
sudo iptables -D INPUT -p tcp --dport 8080 -j ACCEPT

# 清空所有规则（谨慎使用！）
sudo iptables -F

# 插入规则到第一行（优先级最高）
sudo iptables -I INPUT 1 -p tcp --dport 22 -s 192.168.1.0/24 -j ACCEPT
```

### 2.5 iptables 规则示例输出解读

```bash
$ sudo iptables -L -n -v
Chain INPUT (policy DROP)
pkts bytes target     prot opt in     out     source               destination
 1.2M  800M ACCEPT     0    --  lo     *       0.0.0.0/0            0.0.0.0/0
 5.6M  3.2G ACCEPT     0    --  *      *       0.0.0.0/0            0.0.0.0/0            ctstate RELATED,ESTABLISHED
  10K  600K ACCEPT     6    --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:22
   5K  300K ACCEPT     6    --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:80
   2K  120K ACCEPT     6    --  *      *       0.0.0.0/0            0.0.0.0/0            tcp dpt:443
   1K   60K DROP       0    --  *      *       10.99.99.0/24        0.0.0.0/0
   500  30K LOG        0    --  *      *       0.0.0.0/0            0.0.0.0/0            LOG flags 0 level 4
```

**列解读**：

| 列名 | 含义 |
|------|------|
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

## 3. nftables — iptables 的后继者

### 3.1 iptables vs nftables 对比

| 特性 | iptables | nftables |
|------|----------|----------|
| **内核集成** | 多个独立模块 | 统一框架 |
| **规则语法** | 繁琐，多命令 | 简洁，声明式 |
| **性能** | 线性匹配，规则多时慢 | 更高效的集合匹配 |
| **原子操作** | ❌ 逐条加载 | ✅ 整表原子替换 |
| **规则数量上限** | 有限制 | 几乎无上限 |
| **IPv4/IPv6** | 分开管理（iptables/ip6tables） | 统一管理 |
| **集合/映射** | ❌ 不支持（需 ipset） | ✅ 原生支持 |
| **日志** | `-j LOG` | `log prefix "msg"` |
| **引入时间** | 1999 年 | 2014 年 (Linux 3.13+) |
| **默认使用** | CentOS 7, Ubuntu 18.04- | RHEL 8+, Debian 10+, Ubuntu 20.04+ |

### 3.2 nftables 架构

```
nftables 层次结构：
┌───────────────────────────────────┐
│           nftables                │
│  ┌─────────────────────────────┐  │
│  │         table (表)           │  │
│  │  ┌───────────────────────┐  │  │
│  │  │      chain (链)       │  │  │
│  │  │  ┌─────────────────┐  │  │  │
│  │  │  │   rule (规则)   │  │  │  │
│  │  │  │   rule (规则)   │  │  │  │
│  │  │  └─────────────────┘  │  │  │
│  │  └───────────────────────┘  │  │
│  └─────────────────────────────┘  │
└───────────────────────────────────┘

类型: filter, nat, route
族  : ip, ip6, inet, arp, bridge, netdev
```

### 3.3 nftables 基本命令

```bash
# 安装 nftables
sudo apt-get install -y nftables     # Debian/Ubuntu
sudo yum install -y nftables         # RHEL/CentOS 8+

# 启动并启用
sudo systemctl enable --now nftables

# 查看当前规则
sudo nft list ruleset

# 查看特定表
sudo nft list table inet filter

# ===== 创建表 =====
# 族: inet(双栈), ip(IPv4), ip6(IPv6), arp, bridge, netdev
sudo nft add table inet myfilter
sudo nft add table ip mynat

# ===== 创建链 =====
# 类型: filter, nat, route
# hook: prerouting, input, forward, output, postrouting
# priority: 数值，越小优先级越高 (filter=0, dstnat=-100, srcnat=100)
sudo nft add chain inet myfilter input { type filter hook input priority 0 \; policy drop \; }
sudo nft add chain inet myfilter forward { type filter hook forward priority 0 \; policy drop \; }
sudo nft add chain inet myfilter output { type filter hook output priority 0 \; policy accept \; }

# ===== 添加规则 =====
# 允许已建立的连接
sudo nft add rule inet myfilter input ct state established,related accept

# 允许回环
sudo nft add rule inet myfilter input iifname lo accept

# 允许 SSH
sudo nft add rule inet myfilter input tcp dport 22 accept

# 允许 HTTP/HTTPS
sudo nft add rule inet myfilter input tcp dport { 80, 443 } accept

# 允许 ICMP
sudo nft add rule inet myfilter input ip protocol icmp accept

# 使用集合（set）一次性匹配多个 IP
sudo nft add set inet myfilter allowlist { type ipv4_addr \; }
sudo nft add element inet myfilter allowlist { 192.168.1.100, 192.168.1.101, 10.0.0.50 }
sudo nft add rule inet myfilter input ip saddr @allowlist accept

# 动态集合（超时自动过期）
sudo nft add set inet myfilter banlist { type ipv4_addr \; flags timeout \; timeout 1h \; }
sudo nft add element inet myfilter banlist { 10.99.99.99 }
sudo nft add rule inet myfilter input ip saddr @banlist drop

# ===== 管理规则 =====
# 列出所有规则（含句柄）
sudo nft -a list ruleset

# 按句柄删除规则
sudo nft delete rule inet myfilter input handle 5

# 清空表
sudo nft flush table inet myfilter

# 删除表
sudo nft delete table inet myfilter

# ===== 保存与加载 =====
# 保存到文件
sudo nft list ruleset > /etc/nftables.conf

# 从文件加载
sudo nft -f /etc/nftables.conf

# 完全替换（原子操作）
sudo nft -f /etc/nftables.conf
```

### 3.4 nftables 配置文件示例

```bash
# /etc/nftables.conf
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
        tcp dport 9090 accept  # Prometheus
        tcp dport 9100 accept  # Node Exporter

        # 阻止危险端口
        tcp dport @blocked_ports drop

        # 记录并拒绝其他所有
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

---

## 4. 云安全组

### 4.1 云安全组 vs iptables 对比

| 特性 | iptables/nftables | 云安全组 (AWS/Aliyun/Tencent) |
|------|-------------------|-------------------------------|
| 运行位置 | 操作系统内核 | 虚拟化层/Hypervisor |
| 管理方式 | 命令行 | Web 控制台 / API / Terraform |
| 规则方向 | 入站+出站都需要配置 | 通常有状态（自动放行回包） |
| 性能影响 | 消耗 CPU | 几乎无影响（硬件加速） |
| 适用场景 | 主机级别精细控制 | 实例级别粗粒度控制 |
| 优先级 | 规则顺序匹配 | 按优先级或顺序匹配 |
| 日志 | 需额外配置 | 部分云厂商原生支持 |

### 4.2 AWS 安全组配置示例

```bash
# 使用 AWS CLI 创建安全组
aws ec2 create-security-group \
  --group-name sre-web-sg \
  --description "SRE Web Server Security Group" \
  --vpc-id vpc-12345678

# 添加入站规则
aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789 \
  --protocol tcp \
  --port 22 \
  --cidr 10.0.0.0/8

aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789 \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id sg-0123456789 \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# 查看安全组规则
aws ec2 describe-security-groups --group-ids sg-0123456789
```

### 4.3 阿里云安全组配置示例

```bash
# 使用阿里云 CLI 创建安全组
aliyun ecs CreateSecurityGroup \
  --RegionId cn-hangzhou \
  --VpcId vpc-uf6xxxxxxxx \
  --SecurityGroupName "sre-web-sg" \
  --Description "SRE Web Server Security Group"

# 添加入站规则
aliyun ecs AuthorizeSecurityGroup \
  --RegionId cn-hangzhou \
  --SecurityGroupId sg-uf6xxxxxxxx \
  --IpProtocol tcp \
  --PortRange 22/22 \
  --SourceCidrIp 10.0.0.0/8 \
  --Policy accept

aliyun ecs AuthorizeSecurityGroup \
  --RegionId cn-hangzhou \
  --SecurityGroupId sg-uf6xxxxxxxx \
  --IpProtocol tcp \
  --PortRange 80/80 \
  --SourceCidrIp 0.0.0.0/0 \
  --Policy accept

# 使用 Terraform 管理（推荐）
```

### 4.4 Terraform 安全组配置（多云通用）

```hcl
# main.tf
resource "aws_security_group" "sre_web" {
  name        = "sre-web-sg"
  description = "SRE Web Server Security Group"
  vpc_id      = var.vpc_id

  # SSH — 仅限内网
  ingress {
    description = "SSH from internal"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  # HTTP
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # 监控端口（Prometheus + Node Exporter）
  ingress {
    description = "Prometheus and Node Exporter"
    from_port   = 9090
    to_port     = 9100
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  # 出站 — 允许所有
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "sre-web-sg"
    Managed = "terraform"
  }
}
```

### 4.5 安全组最佳实践

| 原则 | 说明 |
|------|------|
| **最小权限** | 只开放必要端口，源 IP 尽量限制 |
| **分层防护** | 安全组（外层）+ iptables（内层）双重保护 |
| **命名规范** | 明确用途，如 `sre-web-sg`, `sre-db-sg` |
| **定期审计** | 检查是否有过宽的规则（如 0.0.0.0/0 + 22） |
| **标签管理** | 使用标签标记规则用途和负责人 |
| **IaC 管理** | 用 Terraform 等工具管理，避免手动变更 |

---

## 5. SRE 实战案例：fail2ban + iptables 自动封禁

### 5.1 问题描述

**背景**：一台面向公网的 Web 服务器持续遭到 SSH 暴力破解攻击。日志显示每分钟有数百次失败的登录尝试，来自全球各地的 IP。

**影响**：
- 系统负载升高（大量认证进程）
- 日志文件快速膨胀
- 安全风险增加

### 5.2 攻击现象

```bash
# 查看失败登录统计
sudo grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -20

# 输出示例：
#    1250 45.148.10.23
#     876 103.75.201.45
#     654 185.220.101.34
#     543 91.240.118.172
#     432 198.235.24.50
```

**攻击分析表**：

| IP | 尝试次数 | 来源地 | 时间跨度 |
|----|----------|--------|----------|
| 45.148.10.23 | 1250 | 俄罗斯 | 2小时内 |
| 103.75.201.45 | 876 | 印度 | 3小时内 |
| 185.220.101.34 | 654 | 德国（Tor 出口） | 1小时内 |

### 5.3 解决方案：fail2ban + iptables

#### 步骤 1：安装 fail2ban

```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y fail2ban

# RHEL/CentOS/Rocky
sudo yum install -y epel-release
sudo yum install -y fail2ban

# 检查版本
fail2ban-server --version
```

#### 步骤 2：配置 fail2ban

```bash
# 创建本地配置（不要直接修改 jail.conf）
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# 编辑配置
sudo nano /etc/fail2ban/jail.local
```

**关键配置项（jail.local）**：

```ini
[DEFAULT]
# 白名单 IP（不会被封禁）
ignoreip = 127.0.0.1/8 10.0.0.0/8 192.168.0.0/16

# 封禁时间（秒）—— 3600 = 1小时
bantime  = 3600

# 查找时间窗口（秒）
findtime = 600

# 在窗口内最大失败次数
maxretry = 5

# 使用哪种 ban 动作（后端）
backend = systemd

# 默认动作（使用 iptables）
action = iptables-multiport[name=default, port="ssh,http,https"]

# ===== SSH 防护 =====
[sshd]
enabled  = true
port     = ssh
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 3
bantime  = 7200    # SSH 封禁更久
findtime = 300     # 5分钟内

# ===== Nginx 登录防护 =====
[nginx-http-auth]
enabled  = true
port     = http,https
filter   = nginx-http-auth
logpath  = /var/log/nginx/error.log
maxretry = 3
bantime  = 3600

# ===== Nginx CC 攻击防护 =====
[nginx-cc]
enabled  = true
port     = http,https
filter   = nginx-cc
logpath  = /var/log/nginx/access.log
maxretry = 100
findtime = 60
bantime  = 1800
```

#### 步骤 3：创建自定义过滤器

```bash
# 创建 Nginx CC 攻击过滤器
sudo nano /etc/fail2ban/filter.d/nginx-cc.conf
```

```ini
# /etc/fail2ban/filter.d/nginx-cc.conf
[Definition]
# 匹配短时间内大量请求的 IP
failregex = ^<HOST> -.*"(GET|POST).*HTTP.*" (200|301|302) .*$
ignoreregex =
```

#### 步骤 4：启动与监控

```bash
# 启动 fail2ban
sudo systemctl enable --now fail2ban

# 查看状态
sudo fail2ban-client status

# 查看特定 jail 状态
sudo fail2ban-client status sshd

# 输出示例：
# Status for the jail: sshd
# |- Filter
# |  |- Currently failed: 5
# |  |- Total failed:     1250
# |  `- File list:        /var/log/auth.log
# `- Actions
#    |- Currently banned: 12
#    |- Total banned:     47
#    `- Banned IP list:   45.148.10.23 103.75.201.45 185.220.101.34 ...

# 查看 iptables 中的封禁规则
sudo iptables -L f2b-sshd -n -v

# 输出示例：
# Chain f2b-sshd (1 references)
# pkts bytes target     prot opt in     out     source               destination
#  12K  720K DROP       0    --  *      *       45.148.10.23         0.0.0.0/0
#   8K  480K DROP       0    --  *      *       103.75.201.45        0.0.0.0/0
# 9.8M  588M RETURN     0    --  *      *       0.0.0.0/0            0.0.0.0/0
```

#### 步骤 5：手动管理

```bash
# 手动封禁 IP
sudo fail2ban-client set sshd banip 45.148.10.23

# 手动解封 IP
sudo fail2ban-client set sshd unbanip 45.148.10.23

# 查看封禁的 IP
sudo fail2ban-client get sshd banip

# 重载配置
sudo fail2ban-client reload

# 查看日志
sudo tail -f /var/log/fail2ban.log

# 日志示例：
# 2024-01-15 10:30:45,123 fail2ban.actions        [1234]: NOTICE  [sshd] Ban 45.148.10.23
# 2024-01-15 11:30:45,456 fail2ban.actions        [1234]: NOTICE  [sshd] Unban 45.148.10.23
```

#### 步骤 6：效果验证

```bash
# 封禁前：持续看到失败登录
sudo tail -f /var/log/auth.log | grep "Failed password"

# 封禁后：被 ban 的 IP 无法建立连接
# 用 tcpdump 验证
sudo tcpdump -i any -nn host 45.148.10.23
# 应该看到 SYN 包但没有回应（DROP 规则生效）

# 检查 iptables 计数器（看到 DROP 计数增长说明规则在工作）
sudo iptables -L f2b-sshd -n -v --line-numbers
```

### 5.4 效果对比

| 指标 | 封禁前 | 封禁后 |
|------|--------|--------|
| SSH 失败登录/分钟 | ~500 | ~5（来自不同 IP 的试探） |
| 系统负载 | 3.5 | 0.3 |
| auth.log 增长 | 50MB/小时 | 1MB/小时 |
| 恶意 IP 数量 | 持续增加 | 自动封禁，动态清零 |

### 5.5 进阶：与云安全组联动

```bash
# 如果使用云服务器，fail2ban 可以通过 API 直接操作安全组
# 示例：使用自定义 action 调用阿里云 API

# /etc/fail2ban/action.d/aliyun-waf.conf
[Definition]
actionban = aliyun ecs AuthorizeSecurityGroup \
  --RegionId cn-hangzhou \
  --SecurityGroupId sg-xxx \
  --IpProtocol tcp \
  --PortRange 1/65535 \
  --SourceCidrIp <ip>/32 \
  --Policy drop

actionunban = aliyun ecs RevokeSecurityGroup \
  --RegionId cn-hangzhou \
  --SecurityGroupId sg-xxx \
  --IpProtocol tcp \
  --PortRange 1/65535 \
  --SourceCidrIp <ip>/32 \
  --Policy drop
```

---

## 6. 练习

### 练习 1：配置基本防火墙规则

```bash
# ===== 目标：搭建一个生产级基础防火墙 =====

# 1. 查看当前规则
sudo iptables -L -n -v --line-numbers

# 2. 清空现有规则（如果有重要规则请先备份）
sudo iptables-save > ~/iptables-backup-$(date +%Y%m%d).bak
sudo iptables -F
sudo iptables -X

# 3. 设置默认策略
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# 4. 允许回环
sudo iptables -A INPUT -i lo -j ACCEPT

# 5. 允许已建立的连接（关键！）
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# 6. 允许 SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 7. 允许 HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 8. 允许 ICMP（限速）
sudo iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s --limit-burst 4 -j ACCEPT

# 9. 添加日志（记录被拒绝的包）
sudo iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "iptables-drop: " --log-level 4

# 10. 查看最终规则
sudo iptables -L -n -v --line-numbers

# 11. 保存规则
sudo iptables-save > /etc/iptables/rules.v4

# 12. 验证：测试被拒绝的端口
curl -v --connect-timeout 3 http://127.0.0.1:8080  # 应该超时/拒绝
```

### 练习 2：使用 nftables 实现相同规则

```bash
# ===== 目标：用 nftables 实现练习 1 的防火墙 =====

# 1. 安装 nftables
sudo apt-get install -y nftables

# 2. 清空现有规则
sudo nft flush ruleset

# 3. 创建表和链
sudo nft add table inet firewall
sudo nft add chain inet firewall input '{ type filter hook input priority 0\; policy drop\; }'
sudo nft add chain inet firewall forward '{ type filter hook forward priority 0\; policy drop\; }'
sudo nft add chain inet firewall output '{ type filter hook output priority 0\; policy accept\; }'

# 4. 添加规则
sudo nft add rule inet firewall input iifname lo accept
sudo nft add rule inet firewall input ct state established,related accept
sudo nft add rule inet firewall input ct state invalid drop
sudo nft add rule inet firewall input tcp dport 22 accept
sudo nft add rule inet firewall input tcp dport { 80, 443 } accept
sudo nft add rule inet firewall input ip protocol icmp accept
sudo nft add rule inet firewall input limit rate 5/minute log prefix \"nft-drop: \"

# 5. 查看规则
sudo nft list ruleset

# 6. 保存
sudo nft list ruleset > /etc/nftables.conf
```

### 练习 3：模拟攻击并测试 fail2ban

```bash
# ===== 目标：在测试环境验证 fail2ban 的效果 =====

# 注意：只在测试/开发机器上操作！

# 1. 安装并配置 fail2ban（如上文）

# 2. 模拟 SSH 暴力破解（从另一台机器）
#    使用 hydra 或简单的循环
for i in $(seq 1 10); do
  ssh -o ConnectTimeout=2 -o PasswordAuthentication=yes fakeuser@$(hostname -I | awk '{print $1}') <<< "wrongpass" &
done

# 3. 在服务器上观察 fail2ban 反应
sudo tail -f /var/log/fail2ban.log

# 4. 验证 IP 被封禁
sudo fail2ban-client status sshd
sudo iptables -L f2b-sshd -n -v

# 5. 验证被封 IP 无法连接（从攻击机）
ssh user@server  # 应该连接超时

# 6. 解封并恢复
sudo fail2ban-client set sshd unbanip <攻击IP>
```

---

## 7. 扩展：端口转发 + fail2ban 安装配置

### 7.1 配置端口转发

**场景**：将外部 8080 端口转发到内部 80 端口，或转发到其他服务器。

#### 单服务器端口转发

```bash
# 1. 启用 IP 转发
sudo sysctl -w net.ipv4.ip_forward=1
# 永久生效
echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 2. 使用 iptables 配置 NAT 端口转发
# 将 8080 转发到 80
sudo iptables -t nat -A PREROUTING -p tcp --dport 8080 -j REDIRECT --to-port 80

# 3. 查看 NAT 规则
sudo iptables -t nat -L -n -v

# 4. 保存
sudo iptables-save > /etc/iptables/rules.v4
```

#### 跨服务器端口转发

```bash
# 场景：将本机 8080 转发到 10.0.1.50:80

# 1. 启用转发
sudo sysctl -w net.ipv4.ip_forward=1

# 2. DNAT：修改目标地址
sudo iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination 10.0.1.50:80

# 3. SNAT/MASQUERADE：修改源地址（让回包能正确返回）
sudo iptables -t nat -A POSTROUTING -p tcp -d 10.0.1.50 --dport 80 -j MASQUERADE

# 4. 允许 FORWARD
sudo iptables -A FORWARD -p tcp -d 10.0.1.50 --dport 80 -j ACCEPT
sudo iptables -A FORWARD -p tcp -s 10.0.1.50 --sport 80 -j ACCEPT

# 5. 查看完整规则
sudo iptables -t nat -L -n -v
sudo iptables -L FORWARD -n -v
```

#### nftables 端口转发

```bash
# nftables 实现端口转发（本机 8080 → 80）
sudo nft add table nat
sudo nft add chain nat prerouting '{ type nat hook prerouting priority -100\; }'
sudo nft add chain nat postrouting '{ type nat hook postrouting priority 100\; }'
sudo nft add rule nat prerouting tcp dport 8080 redirect to :80

# nftables 实现跨服务器转发（本机 8080 → 10.0.1.50:80）
sudo nft add rule nat prerouting tcp dport 8080 dnat to 10.0.1.50:80
sudo nft add rule nat postrouting ip daddr 10.0.1.50 tcp dport 80 masquerade
```

### 7.2 安装和配置 fail2ban（完整步骤）

```bash
# ===== 完整安装流程 =====

# 1. 安装
sudo apt-get update && sudo apt-get install -y fail2ban

# 2. 检查服务状态
sudo systemctl status fail2ban

# 3. 创建本地配置
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# 4. 编辑配置
sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[DEFAULT]
ignoreip = 127.0.0.1/8 10.0.0.0/8
bantime  = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200
findtime = 300
EOF

# 5. 重启服务
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban

# 6. 验证
sudo fail2ban-client status
sudo fail2ban-client status sshd

# 7. 测试
# 从另一台机器故意输错密码 3 次
# ssh fakeuser@server  # 输错密码

# 8. 观察
sudo tail -f /var/log/fail2ban.log

# 9. 管理
sudo fail2ban-client set sshd unbanip <your-ip>  # 如果误封了自己

# 10. 创建自定义 action（使用 iptables + nftables 双后端）
# 可以在 /etc/fail2ban/action.d/ 下创建自定义动作
```

### 7.3 fail2ban 配置检查清单

```bash
# 检查 fail2ban 是否正确加载
sudo fail2ban-client ping
# 应返回: pong

# 查看所有 jail
sudo fail2ban-client status

# 查看具体 jail 配置
sudo fail2ban-client get sshd maxretry
sudo fail2ban-client get sshd bantime
sudo fail2ban-client get sshd findtime
sudo fail2ban-client get sshd logpath

# 查看过滤规则匹配测试
sudo fail2ban-client get sshd failregex
sudo fail2ban-regex /var/log/auth.log /etc/fail2ban/filter.d/sshd.conf

# 查看 ban IP 列表
sudo fail2ban-client get sshd banip

# 检查 iptables 规则
sudo iptables -L -n -v | grep f2b
```

---

## 8. 资源

### 官方文档

| 资源 | 链接 |
|------|------|
| iptables 官方文档 | https://www.netfilter.org/documentation/ |
| iptables man page | https://linux.die.net/man/8/iptables |
| nftables 官方 wiki | https://wiki.nftables.org/ |
| nftables 手册 | https://manpages.debian.org/bookworm/nftables/nft.8.en.html |
| fail2ban 官方文档 | https://www.fail2ban.org/wiki/index.php/Main_Page |
| fail2ban GitHub | https://github.com/fail2ban/fail2ban |

### 云厂商文档

| 资源 | 链接 |
|------|------|
| AWS 安全组文档 | https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html |
| 阿里云安全组文档 | https://help.aliyun.com/zh/ecs/user-guide/security-group-overview |
| 腾讯云安全组文档 | https://cloud.tencent.com/document/product/213/18196 |

### 深入学习

| 资源 | 链接 |
|------|------|
| iptables 教程 (Frozentux) | https://www.frozentux.net/iptables-tutorial/ |
| nftables 迁移指南 | https://wiki.nftables.org/wiki-nftables/index.php/Moving_from_iptables_to_nftables |
| fail2ban 配置指南 | https://www.digitalocean.com/community/tutorials/how-fail2ban-works-to-protect-services-on-a-linux-server |
| Linux 防火墙权威指南 | https://www.netfilter.org/documentation/HOWTO/packet-filtering-HOWTO.html |
| 云安全最佳实践 | https://aws.amazon.com/architecture/security-identity-compliance/ |

### 工具

| 工具 | 链接 |
|------|------|
| iptables-save/restore | 系统自带 |
| iptables-persistent (Debian) | `apt install iptables-persistent` |
| firewalld (RHEL) | 基于 nftables 的前端工具 |
| ufw (Ubuntu) | `apt install ufw`，iptables 简化前端 |

---

## 📝 今日总结

**关键收获**：
1. **iptables 四表五链**是理解 Linux 防火墙的核心，数据包流向决定了规则匹配顺序
2. **白名单模式**（默认 DROP）比黑名单模式更安全，但务必先放行 SSH 和已建立连接
3. **nftables** 是 iptables 的现代化替代，语法更简洁、性能更好、支持集合和原子操作
4. **云安全组 + 主机防火墙** = 分层防御（纵深防御原则），两者缺一不可
5. **fail2ban** 是自动化的入侵防护工具，通过分析日志 + iptables 封禁实现动态防护
6. 端口转发需要 `ip_forward=1` + DNAT + SNAT 三步，缺一不可

**运维金句**：
> 「防火墙规则不是写完了就完了，要定期审计、定期清理。规则多了，就成了漏洞。」

**明日预告**：Day 40 — DNS 原理与排查（dig/nsd + CoreDNS 配置 + DNS 故障排查）

---

> 💡 **SRE 心法**：「安全不是产品，是过程。」防火墙规则只是起点，持续监控、定期审计、自动化响应才是真正的安全。
