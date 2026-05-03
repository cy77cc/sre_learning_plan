# Day 33: 路由基础 — 路由表、默认网关、静态路由

> 📅 日期：2026-05-02
> 📖 学习主题：路由基础 — 路由表、默认网关、静态路由、策略路由、虚拟网络
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 32（IP 协议）

---

## 🎯 学习目标

完成 Day 33 的学习后，你应该掌握：
- 深入理解路由表结构和最长前缀匹配原则
- 熟练使用 ip route 命令管理路由表
- 掌握静态路由和默认网关配置
- 理解策略路由（ip rule + ip route table）
- 掌握 Linux 作为路由器的配置方法
- 理解网络命名空间和虚拟网络设备
- 了解 VxLAN/GRE 隧道基础
- 能够排查容器网络路由问题

---

## 📖 核心知识点

### 1. 路由原理深入

#### 1.1 路由决策流程

```
数据包到达网络接口
    │
    ▼
┌─────────────────────────────────────────┐
│ 1. 检查目标 IP 是否是本机地址            │
│    → 是：接收处理                        │
│    → 否：继续路由决策                    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 2. 检查是否开启 IP 转发                  │
│    net.ipv4.ip_forward                   │
│    → 未开启：丢弃                        │
│    → 开启：继续路由查找                  │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 3. 查询路由表                            │
│    ┌───────────────────────────────┐    │
│    │ 精确主机路由 (/32)             │ ←──│── 最高优先级
│    │ 特定网络路由                   │    │
│    │ 默认路由 (0.0.0.0/0)          │ ←──│── 最低优先级
│    └───────────────────────────────┘    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 4. 最长前缀匹配                         │
│    多条匹配时选择前缀最长的路由           │
│    前缀相同时选择 metric 最小的路由       │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 5. 确定下一跳和出口接口                  │
│    → 如果有 via：发送给下一跳路由器      │
│    → 如果无 via：直接发送到目标          │
└──────────────────┬──────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│ 6. ARP 解析下一跳 MAC 地址              │
│    → 查找 ARP 缓存                      │
│    → 发送 ARP 请求（如果需要）           │
│    → 封装以太网帧发送                    │
└─────────────────────────────────────────┘
```

#### 1.2 最长前缀匹配（Longest Prefix Match）

```
场景：目标 IP = 192.168.1.50

路由表：
  A: 192.168.0.0/16   via 10.0.0.1    ← 匹配前 16 位
  B: 192.168.1.0/24   via 10.0.0.2    ← 匹配前 24 位
  C: 192.168.1.0/28   via 10.0.0.3    ← 匹配前 28 位
  D: 192.168.1.48/30  via 10.0.0.4    ← 匹配前 30 位

匹配分析：
  192.168.1.50 二进制: 11000000.10101000.00000001.00110010

  A (192.168.0.0/16):   11000000.10101000.───────────────────── 匹配 ✓
  B (192.168.1.0/24):   11000000.10101000.00000001.──────────── 匹配 ✓
  C (192.168.1.0/28):   11000000.10101000.00000001.0011─────── 匹配 ✓
  D (192.168.1.48/30):  11000000.10101000.00000001.001100───── 匹配 ✓

  选择 D（/30 是最长前缀，最精确）
```

```bash
# 验证路由查找
ip route get 192.168.1.50
# 输出: 192.168.1.50 via 10.0.0.4 dev eth0 src 10.0.0.100

# 添加多条不同前缀长度的路由
ip route add 192.168.0.0/16 via 10.0.0.1 dev eth0
ip route add 192.168.1.0/24 via 10.0.0.2 dev eth0
ip route add 192.168.1.0/28 via 10.0.0.3 dev eth0

# 测试路由选择
ip route get 192.168.1.50  # 应该走 10.0.0.2（/24 匹配）
ip route get 192.168.1.10  # 应该走 10.0.0.3（/28 匹配）
ip route get 192.168.2.10  # 应该走 10.0.0.1（/16 匹配）
```

#### 1.3 路由表条目详解

```bash
$ ip route show
default via 10.0.2.2 dev eth0 proto dhcp metric 100
10.0.2.0/24 dev eth0 proto kernel scope link src 10.0.2.15 metric 100
172.17.0.0/16 dev docker0 proto kernel scope link src 172.17.0.1 linkdown
192.168.56.0/24 dev eth1 proto kernel scope link src 192.168.56.10 metric 101
10.10.0.0/16 via 192.168.56.1 dev eth1 metric 200
```

**字段解释：**

| 字段 | 含义 | 可选值 |
|------|------|--------|
| `default` | 默认路由（0.0.0.0/0） | 特殊目标 |
| `via` | 下一跳路由器 IP | IP 地址 |
| `dev` | 出口网络接口 | eth0, eth1, docker0... |
| `proto` | 路由来源 | kernel（直连）, static, dhcp, bird |
| `scope` | 作用域 | link（链路本地）, host, global |
| `src` | 源地址（出站时使用） | 本机 IP |
| `metric` | 路由优先级 | 数值越小越优先 |
| `linkdown` | 接口状态 | 接口未启用 |

**路由类型：**

| 类型 | 来源 | 特点 |
|------|------|------|
| 直连路由 | `proto kernel` | 接口配置 IP 后自动生成 |
| 静态路由 | `proto static` | 管理员手动添加 |
| DHCP 路由 | `proto dhcp` | DHCP 服务器分配 |
| 动态路由 | `proto bird/ospf/bgp` | 路由协议学习 |

---

### 2. Linux 路由表管理

#### 2.1 ip route 命令详解

```bash
# =============================================
# 查看路由
# =============================================

# 查看主路由表
ip route show
ip r                    # 简写

# 只看默认路由
ip route show default
ip r | grep default

# 查看特定网段的路由
ip route show 10.0.0.0/8

# 查看特定接口的路由
ip route show dev eth0

# 查看带统计信息的路由
ip -s route show

# 验证特定目标的路由选择
ip route get 8.8.8.8
# 8.8.8.8 via 10.0.2.2 dev eth0 src 10.0.2.15 uid 0
#     cache

# 查看 IPv6 路由
ip -6 route show
ip -6 r

# =============================================
# 添加路由
# =============================================

# 添加静态路由（通过下一跳）
ip route add 10.10.0.0/16 via 192.168.1.1 dev eth0

# 添加静态路由（直接发送，点对点链路）
ip route add 172.16.0.0/24 dev ppp0

# 添加主机路由（/32）
ip route add 10.0.0.5/32 via 192.168.1.1

# 添加带 metric 的路由
ip route add 10.20.0.0/16 via 192.168.1.2 dev eth0 metric 50

# 添加默认路由
ip route add default via 192.168.1.1 dev eth0

# 添加带源地址的路由
ip route add 10.30.0.0/16 via 192.168.1.3 dev eth0 src 192.168.1.100

# =============================================
# 修改路由
# =============================================

# 替换路由（存在则替换，不存在则添加）
ip route replace 10.10.0.0/16 via 192.168.1.3 dev eth0

# 修改默认路由
ip route change default via 192.168.1.2 dev eth0 metric 50

# =============================================
# 删除路由
# =============================================

# 删除特定路由
ip route del 10.10.0.0/16

# 删除默认路由
ip route del default

# 删除特定接口的所有路由
ip route flush dev eth0

# =============================================
# 特殊路由类型
# =============================================

# 黑洞路由（静默丢弃）
ip route add blackhole 10.99.0.0/16
# 发往 10.99.x.x 的数据包被丢弃，不返回 ICMP

# 不可达路由（返回 ICMP 不可达）
ip route add unreachable 10.88.0.0/16
# 发往 10.88.x.x 的数据包被丢弃，返回 ICMP 不可达

# 禁止路由（返回 ICMP 禁止）
ip route add prohibit 10.77.0.0/16
# 发往 10.77.x.x 的数据包被丢弃，返回 ICMP 禁止

# =============================================
# 路由缓存管理
# =============================================

# 查看路由缓存
ip route show cache

# 清除路由缓存（Linux 3.6+ 已移除路由缓存）
# ip route flush cache  # 已废弃
```

#### 2.2 传统 route 命令

```bash
# 查看路由表
route -n
netstat -rn

# 输出示例：
# Kernel IP routing table
# Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
# 0.0.0.0         10.0.2.2        0.0.0.0         UG    100    0        0 eth0
# 10.0.2.0        0.0.0.0         255.255.255.0   U     100    0        0 eth0
# 172.17.0.0      0.0.0.0         255.255.0.0     U     0      0        0 docker0

# Flags 说明：
# U: 路由启用（Up）
# G: 网关路由（Gateway）
# H: 主机路由（Host）
# D: 动态路由（Dynamic）
# M: 修改过的路由（Modified）

# 添加路由
route add -net 10.10.0.0/16 gw 192.168.1.1 dev eth0
route add -host 10.0.0.5 gw 192.168.1.1
route add default gw 192.168.1.1

# 删除路由
route del -net 10.10.0.0/16
route del default gw 192.168.1.1
```

---

### 3. 默认网关

#### 3.1 默认网关的作用

```
默认网关（Default Gateway）是路由表中的 0.0.0.0/0 路由：

本机 IP: 192.168.1.100/24
默认网关: 192.168.1.1

流量走向：
  目标 192.168.1.50  → 匹配 192.168.1.0/24 → 直连发送
  目标 10.0.0.5      → 无匹配路由 → 使用默认网关 → 发给 192.168.1.1
  目标 8.8.8.8       → 无匹配路由 → 使用默认网关 → 发给 192.168.1.1
```

#### 3.2 多默认网关

```bash
# 场景：服务器有两块网卡，配置双默认网关

# eth0: 连接互联网（优先）
ip route add default via 10.0.0.1 dev eth0 metric 100

# eth1: 连接内网（备用）
ip route add default via 192.168.1.1 dev eth1 metric 200

# 查看默认路由
ip route show default
# default via 10.0.0.1 dev eth0 metric 100
# default via 192.168.1.1 dev eth1 metric 200

# metric 小的优先使用
# 当 eth0 故障时，自动切换到 eth1（需要配合监控脚本）
```

#### 3.3 永久配置默认网关

```bash
# Debian/Ubuntu: /etc/network/interfaces
# auto eth0
# iface eth0 inet static
#     address 192.168.1.100/24
#     gateway 192.168.1.1

# Netplan (Ubuntu 18.04+): /etc/netplan/01-netcfg.yaml
# network:
#   version: 2
#   ethernets:
#     eth0:
#       addresses: [192.168.1.100/24]
#       routes:
#         - to: default
#           via: 192.168.1.1
#           metric: 100

# RHEL/CentOS: /etc/sysconfig/network-scripts/ifcfg-eth0
# GATEWAY=192.168.1.1

# systemd-networkd: /etc/systemd/network/10-eth0.network
# [Network]
# Address=192.168.1.100/24
# Gateway=192.168.1.1
```

---

### 4. 静态路由 vs 动态路由

#### 4.1 静态路由

```bash
# 静态路由配置示例
# 场景：公司有两个子网通过路由器连接

# 网络拓扑：
# 192.168.1.0/24 ←→ Router A (192.168.1.1, 10.0.0.1) ←→ Router B (10.0.0.2, 192.168.2.1) ←→ 192.168.2.0/24

# 在 Router A 上添加到 192.168.2.0/24 的路由
ip route add 192.168.2.0/24 via 10.0.0.2 dev eth1

# 在 Router B 上添加到 192.168.1.0/24 的路由
ip route add 192.168.1.0/24 via 10.0.0.1 dev eth1

# 验证
ip route get 192.168.2.100
ping -c 3 192.168.2.100
```

#### 4.2 动态路由协议简介

| 协议 | 类型 | 算法 | 适用规模 | 特点 |
|------|------|------|---------|------|
| RIP | 距离矢量 | Bellman-Ford | 小型网络 | 最大 15 跳，简单 |
| OSPF | 链路状态 | Dijkstra | 大型企业 | 快速收敛，支持分层 |
| BGP | 路径矢量 | 策略路由 | 互联网 | AS 间路由，策略灵活 |
| IS-IS | 链路状态 | Dijkstra | ISP | 类似 OSPF，扩展性好 |
| EIGRP | 混合型 | DUAL | Cisco 网络 | 快速收敛，Cisco 专有 |

```
RIP（Routing Information Protocol）：
  - 最大跳数 15（16 表示不可达）
  - 每 30 秒广播整个路由表
  - 适合小型网络（<15 跳）

OSPF（Open Shortest Path First）：
  - 使用 Dijkstra 算法计算最短路径
  - 支持区域（Area）分层设计
  - 快速收敛（触发更新）
  - 适合大型企业网络

BGP（Border Gateway Protocol）：
  - 互联网骨干网协议
  - AS（自治系统）间路由
  - 基于策略的路由选择
  - 互联网上约有 10 万+ BGP 路由
```

---

### 5. 策略路由（Policy Routing）

#### 5.1 策略路由概念

```
传统路由：只根据目标 IP 选择路由
策略路由：根据源 IP、目标 IP、端口、协议等多维度选择路由

场景：服务器有两块网卡
  eth0: 10.0.0.100/24 → 连接互联网（ISP-A）
  eth1: 192.168.1.100/24 → 连接内网

需求：
  - 从 10.0.0.0/24 来的流量走 eth0
  - 从 192.168.1.0/24 来的流量走 eth1
```

#### 5.2 ip rule 命令

```bash
# =============================================
# 查看策略路由规则
# =============================================
ip rule show
# 输出示例：
# 0:	from all lookup local
# 32766:	from all lookup main
# 32767:	from all lookup default

# 规则优先级：数字越小越优先
# local 表：本机地址路由（最高优先级）
# main 表：主路由表（我们通常配置的路由）
# default 表：默认路由表

# =============================================
# 添加策略路由规则
# =============================================

# 创建自定义路由表
echo "100 isp1" >> /etc/iproute2/rt_tables
echo "200 isp2" >> /etc/iproute2/rt_tables

# 为 10.0.0.0/24 网段创建独立路由表
ip rule add from 10.0.0.0/24 table isp1

# 为 192.168.1.0/24 网段创建独立路由表
ip rule add from 192.168.1.0/24 table isp2

# 配置各路由表的默认路由
ip route add default via 10.0.0.1 dev eth0 table isp1
ip route add default via 192.168.1.1 dev eth1 table isp2

# 添加必要的路由到各表
ip route add 10.0.0.0/24 dev eth0 table isp1
ip route add 192.168.1.0/24 dev eth1 table isp2

# 查看规则
ip rule show
# 0:	from all lookup local
# 32764:	from 192.168.1.0/24 lookup isp2
# 32765:	from 10.0.0.0/24 lookup isp1
# 32766:	from all lookup main
# 32767:	from all lookup default

# 查看自定义路由表
ip route show table isp1
ip route show table isp2
```

#### 5.3 策略路由高级场景

```bash
# =============================================
# 场景 1：基于目标端口的路由
# =============================================
# 所有 HTTP 流量走 eth0，其他走默认路由

# 使用 iptables 给特定流量打标记
iptables -t mangle -A PREROUTING -p tcp --dport 80 -j MARK --set-mark 1
iptables -t mangle -A PREROUTING -p tcp --dport 443 -j MARK --set-mark 1

# 根据标记选择路由表
ip rule add fwmark 1 table isp1
ip route add default via 10.0.0.1 dev eth0 table isp1

# =============================================
# 场景 2：负载均衡（ECMP）
# =============================================
# 同一目标有多条等价路由

ip route add default \
    nexthop via 10.0.0.1 dev eth0 weight 1 \
    nexthop via 192.168.1.1 dev eth1 weight 1

# 查看 ECMP 路由
ip route show default
# default
#         nexthop via 10.0.0.1 dev eth0 weight 1
#         nexthop via 192.168.1.1 dev eth1 weight 1

# =============================================
# 场景 3：基于 TOS 的路由
# =============================================
# 低延迟流量走高速链路

ip rule add tos 0x10 table isp1  # 低延迟
ip route add default via 10.0.0.1 dev eth0 table isp1

# =============================================
# 场景 4：故障转移
# =============================================
# 主链路故障时自动切换到备用链路

# 主路由（metric 小）
ip route add default via 10.0.0.1 dev eth0 metric 100

# 备用路由（metric 大）
ip route add default via 192.168.1.1 dev eth1 metric 200

# 配合健康检查脚本
#!/bin/bash
while true; do
    if ! ping -c 1 -W 2 10.0.0.1 > /dev/null 2>&1; then
        echo "主链路故障，切换到备用"
        ip route del default via 10.0.0.1
        ip route change default via 192.168.1.1 dev eth1 metric 100
    fi
    sleep 10
done
```

---

### 6. Linux 作为路由器

#### 6.1 开启 IP 转发

```bash
# 临时开启
echo 1 > /proc/sys/net/ipv4/ip_forward
sysctl -w net.ipv4.ip_forward=1

# 永久开启
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# 验证
sysctl net.ipv4.ip_forward
cat /proc/sys/net/ipv4/ip_forward
```

#### 6.2 配置 NAT 路由器

```bash
#!/bin/bash
# setup_nat_router.sh - 配置 Linux 作为 NAT 路由器

# 网络拓扑：
# 内网 (192.168.1.0/24) ←→ eth0: 192.168.1.1 ←→ [Linux Router] ←→ eth1: 10.0.0.100 ←→ 互联网

# 1. 开启 IP 转发
sysctl -w net.ipv4.ip_forward=1

# 2. 配置 SNAT（内网访问外网）
iptables -t nat -A POSTROUTING -s 192.168.1.0/24 -o eth1 -j MASQUERADE

# 3. 配置 FORWARD 链
iptables -A FORWARD -i eth0 -o eth1 -s 192.168.1.0/24 -j ACCEPT
iptables -A FORWARD -i eth1 -o eth0 -m state --state ESTABLISHED,RELATED -j ACCEPT

# 4. 配置 DNAT（外网访问内网服务）
iptables -t nat -A PREROUTING -i eth1 -p tcp --dport 80 \
    -j DNAT --to-destination 192.168.1.10:80
iptables -t nat -A PREROUTING -i eth1 -p tcp --dport 443 \
    -j DNAT --to-destination 192.168.1.10:443

# 5. 允许转发 DNAT 流量
iptables -A FORWARD -i eth1 -o eth0 -d 192.168.1.10 -p tcp --dport 80 -j ACCEPT
iptables -A FORWARD -i eth1 -o eth0 -d 192.168.1.10 -p tcp --dport 443 -j ACCEPT

# 6. 配置内网客户端默认网关
# 在内网客户端上：
# ip route add default via 192.168.1.1

# 7. 配置 DNS（可选）
# 安装 dnsmasq 作为 DNS 转发器
# apt install dnsmasq
# echo "server=8.8.8.8" >> /etc/dnsmasq.conf
# systemctl restart dnsmasq

echo "NAT 路由器配置完成"
echo "内网客户端请将默认网关设置为 192.168.1.1"
```

---

### 7. 网络命名空间和虚拟网络设备

#### 7.1 网络命名空间（Network Namespace）

```bash
# 网络命名空间提供完全隔离的网络环境
# 每个命名空间有独立的：
# - 网络接口
# - 路由表
# - iptables 规则
# - /proc/net 目录

# =============================================
# 创建和管理命名空间
# =============================================

# 创建命名空间
ip netns add ns1
ip netns add ns2

# 查看命名空间
ip netns list

# 在命名空间中执行命令
ip netns exec ns1 ip addr show
ip netns exec ns1 ip route show
ip netns exec ns1 ping 127.0.0.1

# 进入命名空间（交互式）
ip netns exec ns1 bash
# 在命名空间中操作后 exit 退出

# 删除命名空间
ip netns delete ns1
```

#### 7.2 veth pair（虚拟以太网对）

```
veth pair 是一对虚拟网卡，数据从一端进入，从另一端出来：

┌─────────────────┐                    ┌─────────────────┐
│   Namespace 1   │                    │   Namespace 2   │
│                 │                    │                 │
│   veth-a        │◄──────────────────►│   veth-b        │
│   192.168.1.10  │   数据包双向传输    │   192.168.2.10  │
│                 │                    │                 │
└─────────────────┘                    └─────────────────┘

数据包流向：
  veth-a 发送 → veth-b 接收
  veth-b 发送 → veth-a 接收
```

```bash
# 创建 veth pair
ip link add veth-a type veth peer name veth-b

# 将 veth 分配到命名空间
ip link set veth-a netns ns1
ip link set veth-b netns ns2

# 配置 IP
ip netns exec ns1 ip addr add 192.168.1.10/24 dev veth-a
ip netns exec ns1 ip link set veth-a up
ip netns exec ns1 ip link set lo up

ip netns exec ns2 ip addr add 192.168.2.10/24 dev veth-b
ip netns exec ns2 ip link set veth-b up
ip netns exec ns2 ip link set lo up

# 配置路由实现互通
ip netns exec ns1 ip route add 192.168.2.0/24 via 192.168.1.1 dev veth-a
ip netns exec ns2 ip route add 192.168.1.0/24 via 192.168.2.1 dev veth-b

# 测试连通性
ip netns exec ns1 ping -c 3 192.168.2.10
```

#### 7.3 Linux Bridge（网桥）

```bash
# 网桥工作在数据链路层（L2），连接多个网络接口

# 创建网桥
ip link add br0 type bridge
ip link set br0 up

# 将接口加入网桥
ip link set eth1 master br0
ip link set veth-a master br0

# 配置网桥 IP
ip addr add 192.168.1.1/24 dev br0

# 查看网桥信息
bridge link show
brctl show  # 传统命令

# 网桥在容器网络中的应用：
# Docker 默认使用 docker0 网桥
# K8s 的 CNI 插件可能使用网桥
```

#### 7.4 完整实验：三个命名空间互通

```bash
#!/bin/bash
# three_ns_network.sh - 搭建三命名空间互通网络

# 拓扑：
# ns1 (10.0.1.10) ←→ ns-router (10.0.1.1, 10.0.2.1) ←→ ns2 (10.0.2.10)

# 1. 创建命名空间
ip netns add ns1
ip netns add ns-router
ip netns add ns2

# 2. 创建 veth pair
ip link add veth-ns1 type veth peer name veth-router1
ip link add veth-ns2 type veth peer name veth-router2

# 3. 分配到命名空间
ip link set veth-ns1 netns ns1
ip link set veth-router1 netns ns-router
ip link set veth-ns2 netns ns2
ip link set veth-router2 netns ns-router

# 4. 配置 IP
ip netns exec ns1 ip addr add 10.0.1.10/24 dev veth-ns1
ip netns exec ns1 ip link set veth-ns1 up
ip netns exec ns1 ip link set lo up
ip netns exec ns1 ip route add default via 10.0.1.1

ip netns exec ns-router ip addr add 10.0.1.1/24 dev veth-router1
ip netns exec ns-router ip addr add 10.0.2.1/24 dev veth-router2
ip netns exec ns-router ip link set veth-router1 up
ip netns exec ns-router ip link set veth-router2 up
ip netns exec ns-router ip link set lo up

ip netns exec ns2 ip addr add 10.0.2.10/24 dev veth-ns2
ip netns exec ns2 ip link set veth-ns2 up
ip netns exec ns2 ip link set lo up
ip netns exec ns2 ip route add default via 10.0.2.1

# 5. 开启路由转发
ip netns exec ns-router sysctl -w net.ipv4.ip_forward=1

# 6. 测试连通性
echo "=== ns1 → ns2 ==="
ip netns exec ns1 ping -c 3 10.0.2.10

echo "=== ns2 → ns1 ==="
ip netns exec ns2 ping -c 3 10.0.1.10

echo "=== 路由追踪 ==="
ip netns exec ns1 traceroute -n 10.0.2.10

# 7. 查看路由表
echo "=== ns1 路由表 ==="
ip netns exec ns1 ip route show

echo "=== ns-router 路由表 ==="
ip netns exec ns-router ip route show

echo "=== ns2 路由表 ==="
ip netns exec ns2 ip route show

# 8. 清理
# ip netns delete ns1
# ip netns delete ns-router
# ip netns delete ns2
```

---

### 8. VxLAN 和 GRE 隧道

#### 8.1 GRE 隧道

```
GRE（Generic Routing Encapsulation）：
- 封装任意协议的数据包在 IP 包中
- 常用于 VPN 和站点互联

封装格式：
┌───────────────────────────────────────────────┐
│ [Outer IP Header][GRE Header][Inner IP Packet]│
│  20 bytes         4 bytes     Original packet  │
└───────────────────────────────────────────────┘
```

```bash
# 创建 GRE 隧道
# 站点 A: 10.0.0.1 (公网)
# 站点 B: 10.0.0.2 (公网)
# 隧道内网: 172.16.0.0/24

# 站点 A 配置
ip tunnel add gre1 mode gre remote 10.0.0.2 local 10.0.0.1 ttl 255
ip link set gre1 up
ip addr add 172.16.0.1/24 dev gre1
ip route add 192.168.2.0/24 via 172.16.0.2 dev gre1

# 站点 B 配置
ip tunnel add gre1 mode gre remote 10.0.0.1 local 10.0.0.2 ttl 255
ip link set gre1 up
ip addr add 172.16.0.2/24 dev gre1
ip route add 192.168.1.0/24 via 172.16.0.1 dev gre1

# 查看隧道
ip tunnel show
# gre1: gre/ip remote 10.0.0.2 local 10.0.0.1 ttl 255

# 测试
ping -c 3 172.16.0.2
```

#### 8.2 VxLAN 隧道

```
VxLAN（Virtual Extensible LAN）：
- 在三层网络上构建二层网络
- 使用 UDP 4789 端口
- 支持 16M 个 VNI（VXLAN Network Identifier）
- K8s Flannel 使用 VxLAN 作为后端

封装格式：
┌─────────────────────────────────────────────────────────────┐
│ [Outer Eth][Outer IP][UDP 4789][VxLAN Header][Inner Eth][Data]│
│  14 bytes  20 bytes  8 bytes   8 bytes       14 bytes  ...   │
└─────────────────────────────────────────────────────────────┘
```

```bash
# 创建 VxLAN 接口
# 假设：
# Host A: 10.0.0.1
# Host B: 10.0.0.2
# VNI: 100
# VxLAN 子网: 172.16.0.0/24

# Host A 配置
ip link add vxlan100 type vxlan id 100 remote 10.0.0.2 dstport 4789 dev eth0
ip link set vxlan100 up
ip addr add 172.16.0.1/24 dev vxlan100

# Host B 配置
ip link add vxlan100 type vxlan id 100 remote 10.0.0.1 dstport 4789 dev eth0
ip link set vxlan100 up
ip addr add 172.16.0.2/24 dev vxlan100

# 测试
ping -c 3 172.16.0.2

# 查看 VxLAN 接口
ip -d link show vxlan100

# VxLAN 在 K8s 中的应用：
# Flannel 使用 VxLAN 实现 Pod 跨节点通信
# 每个节点创建 flannel.1 接口
# Pod 流量通过 VxLAN 隧道封装传输
```

---

## 💻 实战练习

### 练习 1：路由表查看与分析

```bash
# 1. 查看完整路由表
ip route show

# 2. 只看默认路由
ip route show default

# 3. 查看特定网段的路由
ip route show 10.0.0.0/8

# 4. 查看特定接口的路由
ip route show dev eth0

# 5. 验证特定目标的路由选择
ip route get 8.8.8.8
ip route get 192.168.1.50
ip route get 10.0.0.1

# 6. 查看带统计信息的路由
ip -s route show

# 练习：分析你的路由表，回答以下问题
# - 默认网关是什么？
# - 有哪些直连网段？
# - 有没有静态路由？
# - Docker/容器网络使用的网段是什么？
```

### 练习 2：路由配置实验

```bash
# 实验环境：使用 network namespace

# 1. 创建拓扑
# ns-client (10.0.1.100) → ns-router (10.0.1.1, 10.0.2.1) → ns-server (10.0.2.100)

ip netns add ns-client
ip netns add ns-router
ip netns add ns-server

ip link add veth-c type veth peer name veth-r1
ip link add veth-s type veth peer name veth-r2

ip link set veth-c netns ns-client
ip link set veth-r1 netns ns-router
ip link set veth-s netns ns-server
ip link set veth-r2 netns ns-router

ip netns exec ns-client ip addr add 10.0.1.100/24 dev veth-c
ip netns exec ns-client ip link set veth-c up
ip netns exec ns-client ip link set lo up
ip netns exec ns-client ip route add default via 10.0.1.1

ip netns exec ns-router ip addr add 10.0.1.1/24 dev veth-r1
ip netns exec ns-router ip addr add 10.0.2.1/24 dev veth-r2
ip netns exec ns-router ip link set veth-r1 up
ip netns exec ns-router ip link set veth-r2 up
ip netns exec ns-router ip link set lo up
ip netns exec ns-router sysctl -w net.ipv4.ip_forward=1

ip netns exec ns-server ip addr add 10.0.2.100/24 dev veth-s
ip netns exec ns-server ip link set veth-s up
ip netns exec ns-server ip link set lo up
ip netns exec ns-server ip route add default via 10.0.2.1

# 2. 测试连通性
ip netns exec ns-client ping -c 3 10.0.2.100

# 3. 查看路由表
ip netns exec ns-client ip route show
ip netns exec ns-router ip route show
ip netns exec ns-server ip route show

# 4. 路由追踪
ip netns exec ns-client traceroute -n 10.0.2.100

# 5. 抓包分析
ip netns exec ns-router tcpdump -i veth-r1 -n icmp &
ip netns exec ns-client ping -c 1 10.0.2.100

# 6. 清理
ip netns delete ns-client
ip netns delete ns-router
ip netns delete ns-server
```

### 练习 3：策略路由实验

```bash
# 场景：服务器有两块网卡，需要根据源 IP 选择不同出口

# 1. 创建实验环境
ip netns add ns-client1
ip netns add ns-client2
ip netns add ns-router

# 创建 veth pair
ip link add veth-c1 type veth peer name veth-r1
ip link add veth-c2 type veth peer name veth-r2

# 分配到命名空间
ip link set veth-c1 netns ns-client1
ip link set veth-r1 netns ns-router
ip link set veth-c2 netns ns-client2
ip link set veth-r2 netns ns-router

# 配置 IP
ip netns exec ns-client1 ip addr add 10.0.1.100/24 dev veth-c1
ip netns exec ns-client1 ip link set veth-c1 up
ip netns exec ns-client1 ip link set lo up
ip netns exec ns-client1 ip route add default via 10.0.1.1

ip netns exec ns-client2 ip addr add 10.0.2.100/24 dev veth-c2
ip netns exec ns-client2 ip link set veth-c2 up
ip netns exec ns-client2 ip link set lo up
ip netns exec ns-client2 ip route add default via 10.0.2.1

ip netns exec ns-router ip addr add 10.0.1.1/24 dev veth-r1
ip netns exec ns-router ip addr add 10.0.2.1/24 dev veth-r2
ip netns exec ns-router ip link set veth-r1 up
ip netns exec ns-router ip link set veth-r2 up
ip netns exec ns-router ip link set lo up
ip netns exec ns-router sysctl -w net.ipv4.ip_forward=1

# 2. 配置策略路由
ip netns exec ns-router bash -c '
    echo "100 table1" >> /etc/iproute2/rt_tables
    echo "200 table2" >> /etc/iproute2/rt_tables
'

ip netns exec ns-router ip rule add from 10.0.1.0/24 table table1
ip netns exec ns-router ip rule add from 10.0.2.0/24 table table2
ip netns exec ns-router ip route add 10.0.1.0/24 dev veth-r1 table table1
ip netns exec ns-router ip route add 10.0.2.0/24 dev veth-r2 table table2

# 3. 测试
ip netns exec ns-client1 ping -c 3 10.0.2.100

# 4. 清理
ip netns delete ns-client1
ip netns delete ns-client2
ip netns delete ns-router
```

---

## 🏥 SRE 实战案例

### 案例 1：容器网络不通 — ip route show 排查

**场景：**
K8s 集群中，Node A 上的 Pod 无法访问 Node B 上的 Pod。

**环境信息：**
- Node A: 10.0.1.10，Pod 网段 10.244.1.0/24
- Node B: 10.0.1.11，Pod 网段 10.244.2.0/24
- CNI: Flannel (VxLAN)

**排查过程：**

```bash
# 1. 检查 Node A 的路由表
$ ip route show
default via 10.0.1.1 dev eth0
10.0.1.0/24 dev eth0 proto kernel scope link src 10.0.1.10
10.244.1.0/24 dev cni0 proto kernel scope link src 10.244.1.1
# ⚠️ 缺少到 10.244.2.0/24 的路由！

# 2. 对比 Node B 的路由表
$ ssh 10.0.1.11 ip route show
default via 10.0.1.1 dev eth0
10.0.1.0/24 dev eth0 proto kernel scope link src 10.0.1.11
10.244.2.0/24 dev cni0 proto kernel scope link src 10.244.2.1
10.244.1.0/24 via 10.244.1.0 dev flannel.1 onlink
# ✅ Node B 有到 10.244.1.0/24 的路由

# 3. 检查 Flannel 状态
$ systemctl status flanneld
# 发现 flanneld 服务在 Node A 上崩溃

# 4. 检查 flannel.1 接口
$ ip addr show flannel.1
# 接口不存在！

# 5. 检查 Flannel 日志
$ journalctl -u flanneld --since "1 hour ago" -n 50
# 错误：failed to add route: network is unreachable
```

**根因：** Flannel 服务崩溃，导致 VxLAN 接口未创建，路由表不完整。

**解决方案：**

```bash
# 1. 重启 Flannel
systemctl restart flanneld

# 2. 验证接口创建
ip addr show flannel.1

# 3. 验证路由表
ip route show | grep 10.244

# 4. 测试连通性
ping -c 3 10.244.2.5

# 5. 预防措施
# 配置 systemd 自动重启
# [Service]
# Restart=always
# RestartSec=5

# 6. 监控脚本
#!/bin/bash
EXPECTED_ROUTES=("10.244.1.0/24" "10.244.2.0/24" "10.244.3.0/24")
for route in "${EXPECTED_ROUTES[@]}"; do
    if ! ip route show | grep -q "$route"; then
        echo "CRITICAL: Missing route for $route"
        # 发送告警
    fi
done
```

### 案例 2：双网卡策略路由配置

**场景：**
服务器有两块网卡：
- eth0: 10.0.0.100/24（生产网段）
- eth1: 192.168.1.100/24（管理网段）

需求：从哪个网卡进来的流量，响应时从同一个网卡返回。

**配置：**

```bash
#!/bin/bash
# dual_nic_policy_routing.sh

# 1. 创建路由表
echo "100 prod" >> /etc/iproute2/rt_tables
echo "200 mgmt" >> /etc/iproute2/rt_tables

# 2. 配置策略路由规则
ip rule add from 10.0.0.100 table prod
ip rule add from 192.168.1.100 table mgmt

# 3. 配置各路由表
ip route add 10.0.0.0/24 dev eth0 table prod
ip route add default via 10.0.0.1 dev eth0 table prod

ip route add 192.168.1.0/24 dev eth1 table mgmt
ip route add default via 192.168.1.1 dev eth1 table mgmt

# 4. 主路由表保持默认
ip route add default via 10.0.0.1 dev eth0

# 5. 验证
echo "=== 策略规则 ==="
ip rule show

echo "=== prod 路由表 ==="
ip route show table prod

echo "=== mgmt 路由表 ==="
ip route show table mgmt

# 6. 测试
# 从 10.0.0.0/24 网段访问
ping -c 3 -I 10.0.0.100 10.0.0.1

# 从 192.168.1.0/24 网段访问
ping -c 3 -I 192.168.1.100 192.168.1.1
```

### 案例 3：K8s 网络模型中的路由

**场景：**
理解 K8s 网络模型如何使用路由实现 Pod 间通信。

**K8s 网络模型要求：**
1. 每个 Pod 有唯一 IP
2. 所有 Pod 可以直接通信（不需 NAT）
3. 节点可以与 Pod 通信

**典型路由配置（Flannel）：**

```bash
# Node 1 (10.0.1.10) 路由表
$ ip route show
default via 10.0.1.1 dev eth0
10.0.1.0/24 dev eth0 proto kernel scope link src 10.0.1.10
10.244.1.0/24 dev cni0 proto kernel scope link src 10.244.1.1
10.244.2.0/24 via 10.244.2.0 dev flannel.1 onlink
10.244.3.0/24 via 10.244.3.0 dev flannel.1 onlink

# Node 2 (10.0.1.11) 路由表
$ ip route show
default via 10.0.1.1 dev eth0
10.0.1.0/24 dev eth0 proto kernel scope link src 10.0.1.11
10.244.1.0/24 via 10.244.1.0 dev flannel.1 onlink
10.244.2.0/24 dev cni0 proto kernel scope link src 10.244.2.1
10.244.3.0/24 via 10.244.3.0 dev flannel.1 onlink

# 流量走向：
# Pod-A (10.244.1.5) → Pod-B (10.244.2.5)
# 1. Pod-A 发送到默认网关 (10.244.1.1, cni0)
# 2. Node 1 查找路由: 10.244.2.0/24 via 10.244.2.0 dev flannel.1
# 3. 数据包通过 VxLAN 隧道封装发送到 Node 2
# 4. Node 2 解封装，查找路由: 10.244.2.0/24 dev cni0
# 5. 数据包到达 Pod-B
```

---

## 🎯 面试题精选（10 道）

### 题目 1：路由查找过程

**题目**：描述 Linux 内核查找路由的完整过程。

**答案**：
1. 收到数据包，提取目标 IP
2. 查询路由缓存（如有）
3. 按优先级查询路由表：
   - local 表（本机地址）
   - main 表（主路由表）
   - 自定义表（策略路由）
4. 执行最长前缀匹配
5. 多条匹配时选择 metric 最小的
6. 确定下一跳和出口接口
7. ARP 解析下一跳 MAC
8. 封装发送

### 题目 2：最长前缀匹配

**题目**：路由表中有 192.168.0.0/16 和 192.168.1.0/24，目标 IP 192.168.1.50 会匹配哪条？

**答案**：
匹配 192.168.1.0/24，因为 /24 比 /16 前缀更长，更精确。

### 题目 3：Linux 如何做路由器

**题目**：如何让 Linux 服务器充当路由器？

**答案**：
1. 开启 IP 转发：`sysctl -w net.ipv4.ip_forward=1`
2. 配置多个网络接口连接不同网段
3. 添加静态路由或配置动态路由协议
4. 配置 iptables 规则（如需 NAT）
5. 永久生效：写入 /etc/sysctl.conf

### 题目 4：静态路由 vs 动态路由

**题目**：静态路由和动态路由各有什么优缺点？

**答案**：
| 特性 | 静态路由 | 动态路由 |
|------|---------|---------|
| 配置 | 手动 | 自动学习 |
| 维护成本 | 高 | 低 |
| 适应性 | 不自动适应变化 | 自动适应 |
| 资源消耗 | 极低 | 较高 |
| 安全性 | 高 | 需额外安全机制 |
| 适用规模 | 小型网络 | 中大型网络 |

### 题目 5：策略路由

**题目**：什么是策略路由？与传统路由有什么区别？

**答案**：
策略路由根据源 IP、端口、协议等多维度选择路由，而传统路由只根据目标 IP。策略路由使用 `ip rule` 和多路由表实现。

### 题目 6：metric 的作用

**题目**：路由表中的 metric 字段有什么作用？

**答案**：
metric 表示路由的"开销"或"优先级"，数值越小越优先。当多条路由匹配同一目标时，选择 metric 最小的。常用于主备路由切换。

### 题目 7：默认网关

**题目**：什么是默认网关？没有默认网关会怎样？

**答案**：
默认网关是 0.0.0.0/0 路由，匹配所有未明确路由的目标。没有默认网关时，只能访问直连网段，无法访问其他网络。

### 题目 8：黑洞路由

**题目**：什么是黑洞路由？有什么用途？

**答案**：
黑洞路由（blackhole）静默丢弃匹配的数据包，不返回 ICMP 消息。用途：安全防护、流量过滤、防止路由环路。

### 题目 9：VxLAN 原理

**题目**：简述 VxLAN 的工作原理和用途。

**答案**：
VxLAN 在三层网络上构建二层网络，使用 UDP 4789 端口封装以太网帧。支持 16M 个 VNI。主要用于：K8s Pod 跨节点通信、数据中心网络虚拟化。

### 题目 10：网络命名空间

**题目**：什么是网络命名空间？在容器中如何使用？

**答案**：
网络命名空间提供完全隔离的网络环境，包括独立的接口、路由表、iptables。Docker 和 K8s 使用命名空间隔离容器网络。每个容器有自己的网络命名空间。

---

## 📚 深入阅读

### 参考文档
- [Linux ip-route man page](https://man7.org/linux/man-pages/man8/ip-route.8.html)
- [Linux ip-rule man page](https://man7.org/linux/man-pages/man8/ip-rule.8.html)
- [Linux ip-netns man page](https://man7.org/linux/man-pages/man8/ip-netns.8.html)
- [RFC 1812 - IPv4 Router Requirements](https://datatracker.ietf.org/doc/html/rfc1812)

### 推荐书籍
- 《TCP/IP 详解 卷一：协议》- W. Richard Stevens
- 《Linux 网络架构》- Terry Ogletree
- 《Kubernetes 网络》- James Strong

### 实用工具
| 工具 | 用途 |
|------|------|
| `ip route` | 路由管理 |
| `ip rule` | 策略路由规则 |
| `ip netns` | 网络命名空间 |
| `traceroute` | 路径追踪 |
| `mtr` | 持续路径追踪 |
| `tcpdump` | 抓包分析 |
| `bridge` | 网桥管理 |

---

## ✅ 自检清单

### 理论检查点
- [ ] 理解路由决策流程和最长前缀匹配
- [ ] 能解释路由表中每个字段的含义
- [ ] 理解静态路由和动态路由的区别
- [ ] 掌握策略路由的概念和配置方法
- [ ] 理解 Linux 如何作为路由器工作
- [ ] 了解网络命名空间和 veth pair
- [ ] 了解 VxLAN 和 GRE 隧道基础

### 实操检查点
- [ ] 能使用 ip route 查看、添加、删除路由
- [ ] 能使用 ip route get 验证路由选择
- [ ] 能配置策略路由（ip rule + ip route table）
- [ ] 能使用 ip netns 创建隔离网络环境
- [ ] 能搭建三命名空间互通网络
- [ ] 能排查容器网络路由问题
- [ ] 能配置 Linux NAT 路由器

---

> 💡 **SRE 思考题**：如果一台服务器有 3 块网卡（eth0 连接互联网、eth1 连接内网、eth2 连接管理网），如何确保不同来源的流量从正确的网卡返回？
>
> **提示**：使用策略路由，为每个网段创建独立的路由表，通过 ip rule 根据源地址选择路由表。
