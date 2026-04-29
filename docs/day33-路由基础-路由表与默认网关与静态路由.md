# Day 33: 路由基础 — 路由表、默认网关与静态路由

> 📅 日期：2026-04-29  
> 📖 学习主题：路由基础 — 路由表、默认网关、静态路由  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 33 的学习后，你应该掌握：
- 理解路由表的结构和工作原理
- 掌握默认网关的概念与配置方法
- 理解静态路由的配置与应用场景
- 能够使用 `ip route` 命令查看、分析和修改路由表
- 理解路由优先级（metric）和最长前缀匹配原则
- 在容器网络不通的场景下，通过路由表排查问题
- 完成路由表查看/分析/修改的动手练习
- 搭建两个 Linux namespace 并配置跨路由通信

---

## 📖 详细知识点

### 1. 路由概述

#### 1.1 什么是路由

路由（Routing）是网络设备（路由器、主机）根据数据包的目标 IP 地址，决定将数据包从哪个接口发送出去的决策过程。

```
数据包到达设备
    │
    ▼
┌────────────────────┐
│   目标 IP 地址     │
│   ↓ 查询路由表      │
│   匹配最佳路由条目  │
│   ↓               │
│   确定出口接口     │
│   确定下一跳地址    │
└────────────────────┘
    │
    ▼
数据包从出口发出
```

#### 1.2 路由决策三要素

| 要素 | 说明 | 示例 |
|------|------|------|
| 目标网络 | 数据包要到达的网络 | 10.0.0.0/8 |
| 下一跳（Next Hop） | 数据包要发送到的下一个设备 IP | 10.0.0.1 |
| 出口接口 | 数据包离开本机的网络接口 | eth0 |

#### 1.3 路由的类型

| 类型 | 来源 | 特点 | 适用场景 |
|------|------|------|---------|
| 直连路由 | 接口配置 IP 后自动生成 | 优先级最高，无需配置 | 直连网段 |
| 静态路由 | 管理员手动配置 | 稳定但维护成本高 | 小型网络、固定路径 |
| 默认路由 | 手动配置的 0.0.0.0/0 | 匹配所有目标 | 出口网关 |
| 动态路由 | 路由协议自动学习 | 自适应拓扑变化 | 大型网络 |

**动态路由协议（了解即可）：**

| 协议 | 类型 | 说明 |
|------|------|------|
| RIP | 距离矢量 | 简单，最大跳数 15 |
| OSPF | 链路状态 | 大型企业常用 |
| BGP | 路径矢量 | 互联网骨干网 |

---

### 2. 路由表详解

#### 2.1 查看路由表

```bash
# 现代方式（推荐）
ip route show
# 或简写
ip r

# 传统方式
route -n
netstat -rn

# 查看 IPv6 路由
ip -6 route show
```

#### 2.2 路由表条目解读

```bash
$ ip route show
default via 10.0.2.2 dev eth0 proto dhcp metric 100
10.0.2.0/24 dev eth0 proto kernel scope link src 10.0.2.15 metric 100
172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1
192.168.1.0/24 via 10.0.2.254 dev eth0 metric 200
```

**逐条解读：**

| 条目 | 含义 |
|------|------|
| `default via 10.0.2.2 dev eth0 proto dhcp metric 100` | 默认路由：所有未匹配的流量通过 eth0 发送到 10.0.2.2 |
| `10.0.2.0/24 dev eth0 proto kernel scope link src 10.0.2.15 metric 100` | 直连路由：10.0.2.0/24 网段直接从 eth0 发送，源 IP 为 10.0.2.15 |
| `172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1` | Docker 网桥路由：Docker 容器网络 |
| `192.168.1.0/24 via 10.0.2.254 dev eth0 metric 200` | 静态路由：访问 192.168.1.0/24 需通过 10.0.2.254 |

#### 2.3 路由表关键字段

| 字段 | 含义 | 说明 |
|------|------|------|
| `via` | 下一跳地址 | 数据包要发送到的下一个路由器 |
| `dev` | 出口接口 | 数据包离开的网络接口 |
| `proto` | 路由来源 | `kernel`=内核直连, `static`=手动, `dhcp`=DHCP, `bird`=BIRD 路由守护进程 |
| `scope` | 作用域 | `link`=链路本地, `global`=全局, `host`=主机 |
| `src` | 源地址 | 该路由使用的源 IP |
| `metric` | 优先级 | 数值越小优先级越高 |

---

### 3. 路由匹配原则

#### 3.1 最长前缀匹配（Longest Prefix Match）

路由器选择路由时，使用**最长前缀匹配**原则：匹配网络前缀最长的路由条目。

```
目标 IP：192.168.1.50

路由表中有：
  A: 192.168.0.0/16  via 10.0.0.1
  B: 192.168.1.0/24  via 10.0.0.2
  C: 192.168.1.0/28  via 10.0.0.3

匹配结果：选择 C（/28 是最长前缀，最精确）
```

| 路由条目 | 匹配位 | 是否匹配 |
|---------|--------|---------|
| 192.168.0.0/16 | 前 16 位 | ✅ 匹配 |
| 192.168.1.0/24 | 前 24 位 | ✅ 匹配 |
| 192.168.1.0/28 | 前 28 位 | ✅ 匹配 ← **选中（最长）** |

#### 3.2 优先级（Metric）

当存在多条到同一目标的路由时，选择 metric 值最小的：

```bash
ip route show
# default via 10.0.0.1 dev eth0 metric 100    ← 选中（metric 小）
# default via 10.0.1.1 dev eth1 metric 200
```

#### 3.3 路由选择流程

```
收到数据包，目标 IP = X
    │
    ▼
┌─────────────────────────────────┐
│ 1. 检查是否有 exact host 路由    │  (目标 IP = 路由前缀/32)
│    → 有则使用该路由              │
└──────────────┬──────────────────┘
               │ 无
               ▼
┌─────────────────────────────────┐
│ 2. 执行最长前缀匹配               │  (匹配网络前缀最长的条目)
│    → 找到最精确的网络路由         │
└──────────────┬──────────────────┘
               │ 无匹配
               ▼
┌─────────────────────────────────┐
│ 3. 使用默认路由（0.0.0.0/0）     │  (如果有配置)
└──────────────┬──────────────────┘
               │ 无默认路由
               ▼
        ❌ 丢弃，返回 ICMP 不可达
```

---

### 4. 默认网关

#### 4.1 什么是默认网关

默认网关（Default Gateway）是一条特殊路由 `0.0.0.0/0`，当路由表中没有任何更具体的路由匹配目标 IP 时，数据包将发送到默认网关。

```
本机 (192.168.1.100)
    │
    │ 目标：8.8.8.8（不在任何已配置的网络中）
    ▼
┌─────────────┐
│ 路由表查询   │ → 无匹配的具体路由
│             │ → 使用默认路由
└──────┬──────┘
       │
       ▼
  默认网关: 192.168.1.1
       │
       ▼
  互联网...
```

#### 4.2 配置默认网关

```bash
# 查看当前默认网关
ip route show default
# 或
route -n | grep '^0.0.0.0'

# 添加默认网关
ip route add default via 192.168.1.1 dev eth0

# 删除默认网关
ip route del default via 192.168.1.1

# 添加带 metric 的默认网关
ip route add default via 192.168.1.1 dev eth0 metric 100

# 添加 IPv6 默认网关
ip -6 route add default via 2001:db8::1 dev eth0
```

#### 4.3 多默认网关与策略路由

当有多条默认路由时（多网卡场景）：

```bash
# 查看多个默认路由
ip route show default
# default via 10.0.0.1 dev eth0 metric 100    ← 优先使用
# default via 192.168.1.1 dev eth1 metric 200  ← 备用

# 使用策略路由（根据源 IP 选择不同网关）
# 场景：服务器有两块网卡，不同来源的流量走不同出口
ip rule add from 10.0.0.0/8 table 100
ip route add default via 10.0.0.1 dev eth0 table 100

ip rule add from 192.168.1.0/24 table 200
ip route add default via 192.168.1.1 dev eth1 table 200

# 查看策略路由规则
ip rule show
```

---

### 5. 静态路由

#### 5.1 什么是静态路由

静态路由由管理员手动配置，不会随网络拓扑变化自动调整。适合网络结构简单、路径固定的场景。

#### 5.2 添加静态路由

```bash
# 基本语法
ip route add <目标网络>/<前缀> via <下一跳> dev <接口> [metric <值>]

# 示例 1：通过下一跳到达远程网络
ip route add 10.10.0.0/16 via 192.168.1.1 dev eth0
# 含义：要到 10.10.x.x 的流量，通过 eth0 发给 192.168.1.1

# 示例 2：通过接口直接发送（点对点链路）
ip route add 172.16.0.0/24 dev ppp0
# 含义：172.16.0.x 的流量直接从 ppp0 发出

# 示例 3：主机路由（/32）
ip route add 10.0.0.5/32 via 192.168.1.1
# 含义：只针对 10.0.0.5 这一台主机的路由

# 示例 4：带 metric 的路由
ip route add 10.20.0.0/16 via 192.168.1.2 dev eth0 metric 50

# 删除静态路由
ip route del 10.10.0.0/16
ip route del 10.10.0.0/16 via 192.168.1.1

# 替换路由（先删后加）
ip route replace 10.10.0.0/16 via 192.168.1.3 dev eth0
```

#### 5.3 永久静态路由

```bash
# Debian/Ubuntu: /etc/network/interfaces
# 在接口配置中添加：
# iface eth0 inet static
#     address 192.168.1.100/24
#     gateway 192.168.1.1
#     up ip route add 10.10.0.0/16 via 192.168.1.1

# 或使用 /etc/network/interfaces.d/
# 或使用 /etc/sysconfig/network-scripts/route-eth0 (RHEL/CentOS):
# 10.10.0.0/16 via 192.168.1.1

# Netplan (Ubuntu 18.04+):
# /etc/netplan/01-netcfg.yaml
# network:
#   version: 2
#   ethernets:
#     eth0:
#       addresses: [192.168.1.100/24]
#       routes:
#         - to: 10.10.0.0/16
#           via: 192.168.1.1
#       nameservers:
#         addresses: [8.8.8.8]

# 应用 Netplan
netplan apply
```

#### 5.4 静态路由 vs 动态路由

| 特性 | 静态路由 | 动态路由 |
|------|---------|---------|
| 配置方式 | 手动 | 协议自动学习 |
| 维护成本 | 高（每条都要配） | 低 |
| 适应性 | 不自动适应拓扑变化 | 自动适应 |
| 资源消耗 | 极低 | 较高（CPU/内存/带宽） |
| 安全性 | 高（不会被欺骗） | 需额外安全机制 |
| 适用规模 | 小型网络 | 中大型网络 |

---

### 6. 路由调试与故障排查

#### 6.1 常用调试命令

```bash
# 追踪数据包路径
traceroute 8.8.8.8
mtr 8.8.8.8              # 更强大，结合 ping + traceroute
tracepath 8.8.8.8        # 无需 root 权限

# 查看 ARP 表（IP → MAC 映射）
ip neigh show
arp -n

# 查看数据包计数（检查路由是否生效）
ip -s route show

# 持续跟踪路由变化
watch -n 1 'ip route show'

# 检查数据包走向（模拟路由查找）
ip route get 8.8.8.8
# 输出示例：
# 8.8.8.8 via 10.0.2.2 dev eth0 src 10.0.2.15 uid 0
#     cache

# 查看特定路由的详细信息
ip route show 10.0.0.0/8
```

#### 6.2 路由表完整示例与分析

```bash
$ ip route show
default via 10.0.2.2 dev eth0 proto dhcp metric 100
10.0.2.0/24 dev eth0 proto kernel scope link src 10.0.2.15 metric 100
172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 linkdown
192.168.56.0/24 dev eth1 proto kernel scope link src 192.168.56.10 metric 101
10.10.0.0/16 via 192.168.56.1 dev eth1 metric 200
```

| 流量目标 | 匹配的路由 | 出口 | 下一跳 |
|---------|-----------|------|--------|
| 10.0.2.50 | `10.0.2.0/24` | eth0 | 直连 |
| 192.168.56.20 | `192.168.56.0/24` | eth1 | 直连 |
| 10.10.5.100 | `10.10.0.0/16` | eth1 | 192.168.56.1 |
| 8.8.8.8 | `default` | eth0 | 10.0.2.2 |
| 172.17.0.5 | `172.17.0.0/16` | docker0 | 直连（linkdown） |

---

## 🏥 SRE 实战案例：容器网络不通 → ip route show 发现 Pod 路由缺失

### 场景描述

某 Kubernetes 集群中，Node A 上的 Pod 无法访问 Node B 上的 Pod。

**环境信息：**
- Node A：`10.0.1.10`，运行 Pod `10.244.1.0/24` 网段
- Node B：`10.0.1.11`，运行 Pod `10.244.2.0/24` 网段
- 使用 Flannel 作为 CNI 网络插件

**故障现象：**
```bash
# 在 Node A 上 ping Node B 上的 Pod
$ ping 10.244.2.5
connect: Network is unreachable
```

### 排查过程

```bash
# 步骤 1：检查 Node A 的路由表
$ ip route show
default via 10.0.1.1 dev eth0 proto dhcp metric 100
10.0.1.0/24 dev eth0 proto kernel scope link src 10.0.1.10 metric 100
10.244.1.0/24 dev cni0 proto kernel scope link src 10.244.1.1
# ⚠️ 注意：缺少 10.244.2.0/24 的路由！

# 步骤 2：对比正常的 Node B 的路由表
$ ssh 10.0.1.11 ip route show
default via 10.0.1.1 dev eth0 proto dhcp metric 100
10.0.1.0/24 dev eth0 proto kernel scope link src 10.0.1.11 metric 100
10.244.2.0/24 dev cni0 proto kernel scope link src 10.244.2.1
10.244.1.0/24 via 10.244.1.0 dev flannel.1 onlink
# ✅ Node B 有 10.244.1.0/24 的路由

# 步骤 3：检查 Flannel 状态
$ systemctl status flanneld
# 发现 flanneld 服务在 Node A 上已崩溃

# 步骤 4：检查 Flannel 日志
$ journalctl -u flanneld --since "1 hour ago" -n 50
# 发现错误：
# "failed to add route 10.244.2.0/24 via 10.244.2.0: invalid argument"

# 步骤 5：检查 flannel.1 接口
$ ip addr show flannel.1
# 接口不存在！
```

### 根因分析

| 问题 | 详情 |
|------|------|
| Flannel 崩溃 | flanneld 进程异常退出 |
| 路由缺失 | 因 Flannel 崩溃，Node A 的路由表中缺少到其他 Pod 网段的路由 |
| 隧道接口丢失 | flannel.1 VxLAN 接口未创建 |

### 解决方案

```bash
# 1. 重启 Flannel 服务
systemctl restart flanneld

# 2. 验证服务状态
systemctl status flanneld
# 确认 Active: active (running)

# 3. 验证 flannel.1 接口
ip addr show flannel.1
# 应显示类似：
# 4: flannel.1: <BROADCAST,MULTICAST,UP,LOWER_UP>
#     inet 10.244.1.0 peer 10.244.2.0/32 scope global flannel.1

# 4. 验证路由表恢复
ip route show
# 应包含：
# 10.244.2.0/24 via 10.244.2.0 dev flannel.1 onlink

# 5. 测试连通性
ping -c 3 10.244.2.5
# 应正常响应

# 6. 使用 ip route get 验证路由查找
ip route get 10.244.2.5
# 输出：
# 10.244.2.5 via 10.244.2.0 dev flannel.1 src 10.244.1.1 uid 0
```

### 预防措施

```bash
# 1. 监控 Flannel 服务
# Prometheus + node_exporter 监控 systemd 单元状态

# 2. 路由监控脚本
#!/bin/bash
# /usr/local/bin/check-pod-routes.sh
EXPECTED_SUBNETS=("10.244.1.0/24" "10.244.2.0/24" "10.244.3.0/24")
for subnet in "${EXPECTED_SUBNETS[@]}"; do
    if ! ip route show | grep -q "$subnet"; then
        echo "CRITICAL: Missing route for $subnet"
        # 发送告警...
    fi
done

# 3. 配置 systemd 自动重启
# /etc/systemd/system/flanneld.service.d/override.conf
# [Service]
# Restart=always
# RestartSec=5
```

### 经验总结

```
✅ 容器网络不通时，第一步检查路由表：ip route show
✅ 使用 ip route get <目标IP> 验证具体数据包的走向
✅ CNI 插件（Flannel/Calico）故障常表现为路由缺失
✅ 定期检查路由表完整性，纳入监控
✅ flannel.1 / cali* 等虚拟接口的状态直接影响 Pod 通信
```

---

## 📝 练习：查看/分析/修改路由表

### 练习 1：查看路由表

```bash
# 1. 查看完整路由表
ip route show

# 2. 只看默认路由
ip route show default

# 3. 查看特定网段的路由
ip route show 10.0.0.0/8

# 4. 查看特定接口的路由
ip route show dev eth0

# 5. 查看带统计信息的路由
ip -s route show

# 6. 验证特定目标 IP 的路由选择
ip route get 8.8.8.8
ip route get 192.168.1.50

# 记录你的输出并分析每条路由的含义
```

### 练习 2：分析路由表

**给定的路由表：**

```
default via 10.0.0.1 dev eth0 proto dhcp metric 100
10.0.0.0/24 dev eth0 proto kernel scope link src 10.0.0.50 metric 100
10.0.0.0/16 dev eth1 proto static metric 200
172.16.0.0/12 dev docker0 proto kernel scope link src 172.16.0.1
192.168.100.0/24 via 10.0.0.254 dev eth0 metric 150
```

**问题：**

| 序号 | 问题 | 答案 |
|------|------|------|
| 1 | 目标 `8.8.8.8` 的出口和下一跳？ | eth0, 10.0.0.1（走默认路由） |
| 2 | 目标 `10.0.0.100` 的出口？ | eth0（直连，最长前缀 /24 优先于 /16） |
| 3 | 目标 `10.1.5.50` 的出口？ | eth1（匹配 10.0.0.0/16） |
| 4 | 目标 `172.16.5.10` 的出口？ | docker0（匹配 172.16.0.0/12） |
| 5 | 目标 `192.168.100.5` 的出口和下一跳？ | eth0, 10.0.0.254 |
| 6 | 哪条路由优先级最高？ | `10.0.0.0/24`（metric 100 且前缀最长） |
| 7 | 如果有两条默认路由 metric 分别为 100 和 200，走哪条？ | metric 100 的那条 |

### 练习 3：修改路由表

```bash
# 场景 1：添加一条静态路由
# 要求：访问 10.10.0.0/16 的流量通过 eth0 发送到 10.0.0.254
sudo ip route add 10.10.0.0/16 via 10.0.0.254 dev eth0

# 验证
ip route show 10.10.0.0/16
ip route get 10.10.5.1

# 场景 2：添加一条主机路由
# 要求：访问 192.168.1.100 的流量通过 eth1 发送
sudo ip route add 192.168.1.100/32 dev eth1

# 场景 3：添加备用默认网关
# 要求：添加 eth1 作为第二默认网关
sudo ip route add default via 192.168.1.1 dev eth1 metric 200

# 场景 4：修改路由 metric
# 要求：将默认路由 metric 改为 50
sudo ip route change default via 10.0.0.1 dev eth0 metric 50

# 场景 5：删除路由
# 要求：删除之前添加的静态路由
sudo ip route del 10.10.0.0/16 via 10.0.0.254 dev eth0

# 场景 6：添加黑洞路由（丢弃特定流量）
# 要求：丢弃发往 10.99.0.0/16 的所有流量
sudo ip route add blackhole 10.99.0.0/16
# 验证
ping 10.99.1.1
# 应显示：connect: No route to host

# 场景 7：添加不可达路由
sudo ip route add unreachable 10.88.0.0/16
# 区别：blackhole 静默丢弃，unreachable 返回 ICMP 不可达
```

### 练习 4：路由追踪

```bash
# 1. 追踪到外部地址的路径
traceroute -n 8.8.8.8

# 2. 使用 mtr 进行持续追踪
mtr -n -c 10 8.8.8.8

# 3. 追踪 IPv6 路径
traceroute -6 -n 2001:4860:4860::8888

# 4. 使用 ping 验证路径中的每一跳
# 假设 traceroute 显示：
#  1  10.0.0.1   1ms
#  2  203.0.113.1  10ms
#  3  8.8.8.8  15ms
ping -c 3 10.0.0.1
ping -c 3 203.0.113.1

# 5. 检查每一跳的 DNS 反向解析
traceroute 8.8.8.8  # 不加 -n 进行 DNS 解析
```

---

## 🚀 扩展实践：搭建两个 namespace 配置跨路由

### 实验目标

创建两个 Linux network namespace，模拟两个不同网段，通过 veth pair 连接，并配置静态路由实现互通。

### 拓扑图

```
┌─────────────────┐     veth pair      ┌─────────────────┐
│   ns-internal   │◄──────────────────►│    ns-dmz       │
│                 │   veth-a ↔ veth-b  │                 │
│ 172.16.1.10/24  │                    │ 172.16.2.10/24  │
└─────────────────┘                    └─────────────────┘
         │                                    │
         │ 需要配置路由才能互相通信              │
         └────────────────┬───────────────────┘
                          │
                  当前：互相 ping 不通
                  目标：互相 ping 通
```

### 实验步骤

```bash
# =============================================
# 步骤 1：创建两个 network namespace
# =============================================
sudo ip netns add ns-internal
sudo ip netns add ns-dmz

# 验证创建
ip netns list
# 输出：ns-dmz, ns-internal

# =============================================
# 步骤 2：创建 veth pair（虚拟以太网对）
# =============================================
# veth 是一对虚拟网卡，数据从一端进入，从另一端出来
sudo ip link add veth-a type veth peer name veth-b

# 查看创建的 veth pair
ip link show | grep veth

# =============================================
# 步骤 3：将 veth 分配到各自的 namespace
# =============================================
sudo ip link set veth-a netns ns-internal
sudo ip link set veth-b netns ns-dmz

# 验证分配
sudo ip netns exec ns-internal ip link show
sudo ip netns exec ns-dmz ip link show

# =============================================
# 步骤 4：配置 IP 地址
# =============================================
# ns-internal: 172.16.1.10/24
sudo ip netns exec ns-internal ip addr add 172.16.1.10/24 dev veth-a
sudo ip netns exec ns-internal ip link set veth-a up
sudo ip netns exec ns-internal ip link set lo up

# ns-dmz: 172.16.2.10/24
sudo ip netns exec ns-dmz ip addr add 172.16.2.10/24 dev veth-b
sudo ip netns exec ns-dmz ip link set veth-b up
sudo ip netns exec ns-dmz ip link set lo up

# =============================================
# 步骤 5：测试连通性（此时应该不通）
# =============================================
sudo ip netns exec ns-internal ping -c 1 172.16.2.10
# ❌ 不通！因为两个 namespace 在不同的 /24 网段

# 查看 ns-internal 的路由表
sudo ip netns exec ns-internal ip route show
# 只有 172.16.1.0/24 的直连路由，没有到 172.16.2.0/24 的路由

# =============================================
# 步骤 6：配置路由实现互通
# =============================================
# 方案 A：添加静态路由（推荐，模拟真实场景）

# 在 ns-internal 中添加到 ns-dmz 网段的路由
# 下一跳为 veth-b 的 IP
sudo ip netns exec ns-dmz ip addr add 172.16.1.1/32 dev veth-b
sudo ip netns exec ns-internal ip route add 172.16.2.0/24 via 172.16.1.1 dev veth-a

# 在 ns-dmz 中添加到 ns-internal 网段的路由
sudo ip netns exec ns-internal ip addr add 172.16.2.1/32 dev veth-a
sudo ip netns exec ns-dmz ip route add 172.16.1.0/24 via 172.16.2.1 dev veth-b

# 方案 B：使用同一个 /23 子网（简化方案）
# 将两个接口都配置为 172.16.0.0/23 网段
# sudo ip netns exec ns-internal ip addr add 172.16.1.10/23 dev veth-a
# sudo ip netns exec ns-dmz ip addr add 172.16.2.10/23 dev veth-b

# =============================================
# 步骤 7：验证连通性
# =============================================
# ns-internal ping ns-dmz
sudo ip netns exec ns-internal ping -c 3 172.16.2.10
# ✅ PING 172.16.2.10 (172.16.2.10) 56(84) bytes of data.
# ✅ 64 bytes from 172.16.2.10: icmp_seq=1 ttl=64 time=0.050 ms

# ns-dmz ping ns-internal
sudo ip netns exec ns-dmz ping -c 3 172.16.1.10
# ✅ PING 172.16.1.10 (172.16.1.10) 56(84) bytes of data.
# ✅ 64 bytes from 172.16.1.10: icmp_seq=1 ttl=64 time=0.045 ms

# =============================================
# 步骤 8：查看各自的路由表
# =============================================
echo "=== ns-internal 路由表 ==="
sudo ip netns exec ns-internal ip route show
# 172.16.1.0/24 dev veth-a proto kernel scope link src 172.16.1.10
# 172.16.2.0/24 via 172.16.1.1 dev veth-a

echo "=== ns-dmz 路由表 ==="
sudo ip netns exec ns-dmz ip route show
# 172.16.2.0/24 dev veth-b proto kernel scope link src 172.16.2.10
# 172.16.1.0/24 via 172.16.2.1 dev veth-b

# =============================================
# 步骤 9：添加第三 namespace 模拟三节点网络
# =============================================
# 创建 ns-office
sudo ip netns add ns-office
sudo ip link add veth-c type veth peer name veth-d
sudo ip link set veth-c netns ns-internal
sudo ip link set veth-d netns ns-office

sudo ip netns exec ns-internal ip addr add 172.16.3.10/24 dev veth-c
sudo ip netns exec ns-internal ip link set veth-c up
sudo ip netns exec ns-office ip addr add 172.16.3.20/24 dev veth-d
sudo ip netns exec ns-office ip link set veth-d up
sudo ip netns exec ns-office ip link set lo up

# 配置 ns-office 到 ns-dmz 的路由（经过 ns-internal）
# 注意：这需要 ns-internal 开启 IP 转发
sudo ip netns exec ns-internal sysctl -w net.ipv4.ip_forward=1

# ns-office 添加默认路由走 ns-internal
sudo ip netns exec ns-office ip route add 172.16.2.0/24 via 172.16.3.10 dev veth-d

# ns-dmz 添加路由到 ns-office（经过 ns-internal）
sudo ip netns exec ns-dmz ip route add 172.16.3.0/24 via 172.16.1.10 dev veth-b

# 测试：ns-office → ns-dmz
sudo ip netns exec ns-office ping -c 2 172.16.2.10
# ✅ 应能 ping 通

# =============================================
# 步骤 10：清理实验环境
# =============================================
sudo ip netns delete ns-internal
sudo ip netns delete ns-dmz
sudo ip netns delete ns-office
```

### 实验验证清单

| 检查项 | 命令 | 预期结果 |
|--------|------|---------|
| namespace 创建 | `ip netns list` | 显示 ns-internal 和 ns-dmz |
| veth 分配 | `ip netns exec ns-internal ip link show` | 显示 veth-a |
| IP 配置 | `ip netns exec ns-internal ip addr show` | 显示 172.16.1.10/24 |
| 接口 UP | `ip netns exec ns-internal ip link show veth-a` | 状态为 UP |
| 路由配置 | `ip netns exec ns-internal ip route show` | 有到 172.16.2.0/24 的路由 |
| 双向 ping | `ip netns exec ns-internal ping 172.16.2.10` | 响应正常 |
| IP 转发 | `ip netns exec ns-internal sysctl net.ipv4.ip_forward` | 值为 1 |

---

## 📚 扩展阅读与资源

### 参考文档
- [Linux ip-route man page](https://man7.org/linux/man-pages/man8/ip-route.8.html)
- [Linux ip-netns man page](https://man7.org/linux/man-pages/man8/ip-netns.8.html)
- [RFC 1812 - IPv4 Router Requirements](https://datatracker.ietf.org/doc/html/rfc1812)
- [策略路由 Linux 文档](https://www.policyrouting.org/)

### 实用工具
- `ip route` — 路由管理（iproute2 套件）
- `traceroute` / `mtr` — 路径追踪
- `ip netns` — network namespace 管理
- `tcpdump` — 抓包验证路由正确性

### 深入学习
- 路由协议 OSPF/BGP（Day 44+ 内容）
- Linux 策略路由（ip rule + ip route table）
- BGP 在数据中心的应用（BGP unnumbered）

---

## 📝 总结

| 知识点 | 关键要点 |
|--------|---------|
| 路由表 | 数据包转发的决策表，通过 `ip route show` 查看 |
| 最长前缀匹配 | 路由选择的核心原则，前缀越长越优先 |
| 默认网关 | 0.0.0.0/0 路由，所有未匹配流量的出口 |
| 静态路由 | 手动配置，`ip route add` 添加，适合固定路径 |
| Metric | 路由优先级，数值越小越优先 |
| 容器网络 | CNI 插件通过路由表实现 Pod 间通信 |
| Network Namespace | Linux 网络隔离机制，可模拟多主机网络 |

---

> 💡 **SRE 思考题**：如果一台服务器有 3 块网卡（eth0 连接互联网、eth1 连接内网、eth2 连接管理网），如何确保不同来源的流量从正确的网卡返回？（提示：策略路由）
