# Day 32: IP 协议 — 地址分类、子网掩码、CIDR、NAT

> 📅 日期：2026-05-02
> 📖 学习主题：IP 协议 — 地址分类、子网掩码、CIDR、NAT、ICMP、ARP
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 29（OSI 七层模型）、Day 30（TCP 协议）

---

## 🎯 学习目标

完成 Day 32 的学习后，你应该掌握：
- 深入理解 IPv4 报文结构，能逐字段解释首部含义
- 掌握 IP 地址分类（A/B/C/D/E 类）及私有地址段
- 熟练进行子网划分计算（CIDR、VLSM）
- 理解 NAT 四种类型及其在云环境中的应用
- 掌握 ICMP 协议原理（ping/traceroute）
- 理解 ARP 协议工作过程及安全风险
- 了解 IPv6 基础和过渡技术
- 能够排查 NAT 带宽瓶颈和子网划分问题

---

## 📖 核心知识点

### 1. IPv4 报文结构深入解析

#### 1.1 IPv4 首部结构图

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version|  IHL  |    DSCP   |ECN|          Total Length         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Identification        |Flags|      Fragment Offset    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Time to Live |    Protocol   |         Header Checksum       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Source Address                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Destination Address                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options (可选)              |    Padding    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

#### 1.2 首部字段详解

| 字段 | 长度 | 说明 | SRE 关注点 |
|------|------|------|-----------|
| Version | 4 bits | IP 版本号，IPv4 = 4 | 抓包时验证版本 |
| IHL | 4 bits | 首部长度（32-bit 字为单位），最小 5（20 字节） | 有 Options 时变大 |
| DSCP | 6 bits | 差分服务代码点（QoS 优先级） | 流量整形、优先级标记 |
| ECN | 2 bits | 显式拥塞通知 | 拥塞控制协同 |
| Total Length | 16 bits | 数据包总长度（字节），最大 65535 | MTU 相关问题 |
| Identification | 16 bits | 标识符，用于分片重组 | 分片追踪 |
| Flags | 3 bits | DF（不分片）、MF（更多分片） | MTU 路径发现 |
| Fragment Offset | 13 bits | 分片偏移（以 8 字节为单位） | 分片攻击检测 |
| TTL | 8 bits | 生存时间，每经过一跳减 1 | 防环、traceroute 原理 |
| Protocol | 8 bits | 上层协议号 | 识别流量类型 |
| Header Checksum | 16 bits | 首部校验和 | 数据完整性 |
| Source Address | 32 bits | 源 IP 地址 | 溯源、过滤 |
| Destination Address | 32 bits | 目标 IP 地址 | 路由决策 |

#### 1.3 关键字段深入分析

**TTL（Time To Live）**

```
TTL 的工作原理：
┌────────┐    TTL=64    ┌────────┐    TTL=63    ┌────────┐
│ 源主机  │───────────▶│ 路由器A │───────────▶│ 路由器B │
│        │             │ TTL-1=63│             │ TTL-1=62│
└────────┘             └────────┘             └────────┘

如果 TTL 减到 0：
┌────────┐
│ 路由器  │  TTL=0 → 丢弃数据包
│        │  → 返回 ICMP Time Exceeded（Type 11, Code 0）
└────────┘  → 这就是 traceroute 的原理！
```

**常见 TTL 初始值：**

| 操作系统 | 默认 TTL | 说明 |
|---------|---------|------|
| Linux | 64 | 大多数 Linux 发行版 |
| Windows | 128 | Windows 系列 |
| macOS | 64 | 基于 BSD |
| Cisco IOS | 255 | 网络设备 |

```bash
# 通过 TTL 猜测远端操作系统
ping -c 1 8.8.8.8
# TTL=117 → 可能是 Windows（128-11跳）
# TTL=53  → 可能是 Linux（64-11跳）

# 查看/修改本机默认 TTL
sysctl net.ipv4.ip_default_ttl
sysctl -w net.ipv4.ip_default_ttl=128
```

**协议号（Protocol）**

| 协议号 | 协议 | 说明 |
|--------|------|------|
| 1 | ICMP | Internet 控制消息协议 |
| 2 | IGMP | Internet 组管理协议 |
| 6 | TCP | 传输控制协议 |
| 17 | UDP | 用户数据报协议 |
| 41 | IPv6-in-IPv4 | 6in4 隧道 |
| 47 | GRE | 通用路由封装 |
| 50 | ESP | IPSec 封装安全载荷 |
| 51 | AH | IPSec 认证头 |
| 89 | OSPF | 开放最短路径优先 |
| 132 | SCTP | 流控制传输协议 |

```bash
# 使用 tcpdump 按协议号过滤
tcpdump -i eth0 'ip proto 1'      # ICMP
tcpdump -i eth0 'ip proto 6'      # TCP
tcpdump -i eth0 'ip proto 17'     # UDP
tcpdump -i eth0 'ip proto 47'     # GRE
```

**标志位（Flags）与分片**

```
Flags（3 bits）：
  Bit 0: 保留（必须为 0）
  Bit 1: DF（Don't Fragment）= 1 表示不允许分片
  Bit 2: MF（More Fragments）= 1 表示后面还有分片

分片示例：
原始数据包 3000 字节，MTU = 1500

分片 1: [IP Header 20B] [Data 1480B]  Offset=0,  DF=0, MF=1
分片 2: [IP Header 20B] [Data 1480B]  Offset=185, DF=0, MF=1
分片 3: [IP Header 20B] [Data 40B]    Offset=370, DF=0, MF=0

接收端根据 Identification + Source IP + Destination IP + Protocol 识别同一数据包的分片
```

```bash
# 查看分片统计
cat /proc/net/snmp | grep -A 1 Ip:
# Ip: Forwarding DefaultTTL ... ReasmReqds ReasmOKs ReasmFails
# ReasmReqds: 收到的需要重组的数据包数
# ReasmOKs: 成功重组的数据包数
# ReasmFails: 重组失败的数据包数

# 查看分片攻击防护
sysctl net.ipv4.ipfrag_high_thresh      # 分片缓存上限
sysctl net.ipv4.ipfrag_low_thresh        # 分片缓存下限
sysctl net.ipv4.ipfrag_time              # 分片超时时间
```

---

### 2. IPv4 地址分类

#### 2.1 五类地址详解

```
A 类地址（0xxxxxxx）:
  范围: 0.0.0.0 ~ 127.255.255.255
  网络位: 8 位 | 主机位: 24 位
  网络数: 126（去掉 0 和 127）
  每网络主机数: 2^24 - 2 = 16,777,214
  用途: 大型组织、国家级网络

B 类地址（10xxxxxx）:
  范围: 128.0.0.0 ~ 191.255.255.255
  网络位: 16 位 | 主机位: 16 位
  网络数: 16,384
  每网络主机数: 2^16 - 2 = 65,534
  用途: 大学、中型企业

C 类地址（110xxxxx）:
  范围: 192.0.0.0 ~ 223.255.255.255
  网络位: 24 位 | 主机位: 8 位
  网络数: 2,097,152
  每网络主机数: 2^8 - 2 = 254
  用途: 小型企业、ISP

D 类地址（1110xxxx）:
  范围: 224.0.0.0 ~ 239.255.255.255
  用途: 组播（Multicast）

E 类地址（1111xxxx）:
  范围: 240.0.0.0 ~ 255.255.255.255
  用途: 实验保留
```

**快速判断脚本：**

```bash
#!/bin/bash
# classify_ip.sh - 判断 IP 地址类别和类型
ip=$1
first_octet=$(echo "$ip" | cut -d. -f1)

# 判断类别
if [ "$first_octet" -ge 1 ] && [ "$first_octet" -le 126 ]; then
    class="A"
elif [ "$first_octet" -ge 128 ] && [ "$first_octet" -le 191 ]; then
    class="B"
elif [ "$first_octet" -ge 192 ] && [ "$first_octet" -le 223 ]; then
    class="C"
elif [ "$first_octet" -ge 224 ] && [ "$first_octet" -le 239 ]; then
    class="D（组播）"
elif [ "$first_octet" -ge 240 ]; then
    class="E（保留）"
fi

# 判断是否私有地址
second_octet=$(echo "$ip" | cut -d. -f2)
if [ "$first_octet" -eq 10 ]; then
    type="私有地址（RFC 1918）"
elif [ "$first_octet" -eq 172 ] && [ "$second_octet" -ge 16 ] && [ "$second_octet" -le 31 ]; then
    type="私有地址（RFC 1918）"
elif [ "$first_octet" -eq 192 ] && [ "$second_octet" -eq 168 ]; then
    type="私有地址（RFC 1918）"
elif [ "$first_octet" -eq 127 ]; then
    type="回环地址"
elif [ "$first_octet" -eq 169 ] && [ "$second_octet" -eq 254 ]; then
    type="APIPA（自动私有 IP）"
elif [ "$first_octet" -eq 100 ] && [ "$second_octet" -ge 64 ] && [ "$second_octet" -le 127 ]; then
    type="CGN（运营商级 NAT，RFC 6598）"
else
    type="公网地址"
fi

echo "IP: $ip"
echo "类别: $class 类"
echo "类型: $type"

# 测试：
# ./classify_ip.sh 10.0.0.1      → A 类, 私有地址
# ./classify_ip.sh 172.16.0.1    → B 类, 私有地址
# ./classify_ip.sh 192.168.1.1   → C 类, 私有地址
# ./classify_ip.sh 8.8.8.8       → A 类, 公网地址
# ./classify_ip.sh 224.0.0.1     → D 类（组播）
```

#### 2.2 特殊地址详解

| 地址/地址段 | 名称 | 用途 | SRE 场景 |
|------------|------|------|---------|
| 0.0.0.0/8 | 本网络 | 表示"任意地址"或"本机" | 监听地址 `0.0.0.0:80` |
| 10.0.0.0/8 | A 类私有 | 大型内部网络 | 云厂商 VPC 默认 |
| 100.64.0.0/10 | CGN | 运营商级 NAT | 双重 NAT 场景 |
| 127.0.0.0/8 | 回环 | 本地测试 | `localhost`、健康检查 |
| 169.254.0.0/16 | APIPA | DHCP 失败时自动分配 | 故障排查信号 |
| 172.16.0.0/12 | B 类私有 | 中型内部网络 | Docker 默认网桥 |
| 192.168.0.0/16 | C 类私有 | 小型内部网络 | 家庭路由器 |
| 224.0.0.0/4 | 组播 | 一对多通信 | 服务发现、直播 |
| 255.255.255.255 | 有限广播 | 本网段广播 | DHCP 发现 |

```bash
# 查看本机所有 IP 地址
ip addr show | grep "inet "
# 输出示例：
# inet 127.0.0.1/8 scope host lo
# inet 10.0.2.15/24 brd 10.0.2.255 scope global eth0
# inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
# inet 10.244.1.0/24 scope global cni0

# 判断是否为私有地址
is_private_ip() {
    local ip=$1
    local o1 o2
    o1=$(echo "$ip" | cut -d. -f1)
    o2=$(echo "$ip" | cut -d. -f2)

    if [ "$o1" -eq 10 ]; then
        return 0
    elif [ "$o1" -eq 172 ] && [ "$o2" -ge 16 ] && [ "$o2" -le 31 ]; then
        return 0
    elif [ "$o1" -eq 192 ] && [ "$o2" -eq 168 ]; then
        return 0
    fi
    return 1
}
```

---

### 3. 子网掩码与子网划分

#### 3.1 子网掩码原理

子网掩码用于区分 IP 地址中的**网络部分**和**主机部分**：

```
IP 地址:    192.168.1.100 = 11000000.10101000.00000001.01100100
子网掩码:   255.255.255.0 = 11111111.11111111.11111111.00000000
                            ────────────────────────────────────
                            │←── 网络位 ──→│←── 主机位 ──→│

网络地址 = IP AND Mask:     192.168.1.0   = 11000000.10101000.00000001.00000000
广播地址 = Network OR ~Mask: 192.168.1.255 = 11000000.10101000.00000001.11111111
```

#### 3.2 CIDR 表示法

CIDR（Classless Inter-Domain Routing）打破了传统 A/B/C 类的固定划分：

```
格式: IP地址/前缀长度
示例: 192.168.1.0/24

/24 表示前 24 位是网络位，后 8 位是主机位
等价于子网掩码 255.255.255.0
```

**常用 CIDR 对照表：**

| CIDR | 子网掩码 | 二进制 | 可用主机数 | 适用场景 |
|------|---------|--------|-----------|---------|
| /8 | 255.0.0.0 | 11111111.00000000... | 16,777,214 | A 类网络 |
| /16 | 255.255.0.0 | 11111111.11111111... | 65,534 | B 类网络 |
| /24 | 255.255.255.0 | 11111111.11111111.11111111.00000000 | 254 | 小型网络 |
| /25 | 255.255.255.128 | ...11111111.10000000 | 126 | 半子网 |
| /26 | 255.255.255.192 | ...11111111.11000000 | 62 | 部门子网 |
| /27 | 255.255.255.224 | ...11111111.11100000 | 30 | 小型部门 |
| /28 | 255.255.255.240 | ...11111111.11110000 | 14 | VLAN |
| /29 | 255.255.255.248 | ...11111111.11111000 | 6 | 点对点 |
| /30 | 255.255.255.252 | ...11111111.11111100 | 2 | 路由器互联 |
| /32 | 255.255.255.255 | ...11111111.11111111 | 1 | 主机路由 |

#### 3.3 子网划分计算

**计算公式：**
- 网络地址 = IP AND 子网掩码
- 广播地址 = 网络地址 OR（NOT 子网掩码）
- 第一个可用 IP = 网络地址 + 1
- 最后一个可用 IP = 广播地址 - 1
- 可用主机数 = 2^(32-前缀长度) - 2

**示例：192.168.1.100/26**

```
IP:      192.168.1.100 = 11000000.10101000.00000001.01100100
掩码:    255.255.255.192 = 11111111.11111111.11111111.11000000
网络地址: 192.168.1.64  = 11000000.10101000.00000001.01000000
广播地址: 192.168.1.127 = 11000000.10101000.00000001.01111111
可用范围: 192.168.1.65 ~ 192.168.1.126
可用主机: 62 台
```

```bash
# 使用 ipcalc 工具快速计算
ipcalc 192.168.1.100/26

# 输出：
# Address:   192.168.1.100
# Netmask:   255.255.255.192 = 26
# Network:   192.168.1.64/26
# HostMin:   192.168.1.65
# HostMax:   192.168.1.126
# Broadcast: 192.168.1.127
# Hosts/Net: 62

# 批量计算子网
for i in 0 32 64 96 128 160 192 224; do
    echo "=== 192.168.10.$i/27 ==="
    ipcalc 192.168.10.$i/27 | grep -E "Network|HostMin|HostMax|Broadcast|Hosts"
done
```

#### 3.4 VLSM（可变长子网掩码）

VLSM 允许在同一网络中使用不同长度的子网掩码，最大化 IP 地址利用率：

**场景：为公司各部门分配 10.0.0.0/16**

| 部门 | 需要主机数 | 分配网段 | CIDR | 可用主机 |
|------|-----------|---------|------|---------|
| 研发部 | 200 | 10.0.1.0/24 | /24 | 254 |
| 测试部 | 100 | 10.0.2.0/25 | /25 | 126 |
| 运维部 | 50 | 10.0.2.128/26 | /26 | 62 |
| 管理网 | 10 | 10.0.2.192/28 | /28 | 14 |
| 点对点链路 | 2 | 10.0.2.208/30 | /30 | 2 |
| 服务器区 | 500 | 10.0.3.0/23 | /23 | 510 |

```bash
# 自动化 VLSM 计算脚本
#!/bin/bash
# vlsm_calc.sh - VLSM 子网计算器

calculate_subnet() {
    local network=$1
    local prefix=$2
    local hosts_needed=$3
    local name=$4

    # 计算需要的主机位
    local host_bits=1
    while [ $((2**host_bits - 2)) -lt "$hosts_needed" ]; do
        ((host_bits++))
    done

    local new_prefix=$((32 - host_bits))
    local available_hosts=$((2**host_bits - 2))

    echo "$name: 需要 $hosts_needed 台, 分配 /$new_prefix, 可用 $available_hosts 台"
}

# 使用示例
calculate_subnet "10.0.0.0" 16 200 "研发部"
calculate_subnet "10.0.0.0" 16 100 "测试部"
calculate_subnet "10.0.0.0" 16 50  "运维部"
calculate_subnet "10.0.0.0" 16 10  "管理网"
calculate_subnet "10.0.0.0" 16 2   "点对点"
```

#### 3.5 超网（Supernetting）与路由聚合

将多个连续子网合并为更大的网段，减少路由表条目：

```
聚合前（4 条路由）：
  192.168.0.0/24
  192.168.1.0/24
  192.168.2.0/24
  192.168.3.0/24

聚合后（1 条路由）：
  192.168.0.0/22

计算过程：
  192.168.0.0 = 11000000.10101000.00000000.00000000
  192.168.1.0 = 11000000.10101000.00000001.00000000
  192.168.2.0 = 11000000.10101000.00000010.00000000
  192.168.3.0 = 11000000.10101000.00000011.00000000
  ───────────────────────────────────────────────────
  公共前缀:   11000000.10101000.000000（22 位）
  聚合结果:   192.168.0.0/22
```

---

### 4. NAT（网络地址转换）深入

#### 4.1 NAT 工作原理

```
        内部网络（私有IP）              NAT 网关               互联网
   ┌─────────────────────┐    ┌──────────────────┐    ┌───────────────┐
   │ PC1: 192.168.1.10   │    │ 内网口: .1.1     │    │               │
   │ 端口: 12345         │───▶│ 公网IP: 203.0.113.5│──▶│ 8.8.8.8:80    │
   │                     │    │ NAT表:             │    │               │
   │ 发送: 192.168.1.10  │    │ 内:192.168.1.10:  │    │ 源IP:203.0.113.5│
   │       :12345 →      │    │     12345         │    │ 源端口:54321   │
   │       8.8.8.8:80    │    │ 外:203.0.113.5:   │    │               │
   │                     │    │     54321         │    │ 回复:          │
   │ 接收: 8.8.8.8:80 → │◀───│                   │◀───│ 8.8.8.8:80 →  │
   │       192.168.1.10  │    │                   │    │ 203.0.113.5:  │
   │       :12345        │    │                   │    │ 54321         │
   └─────────────────────┘    └──────────────────┘    └───────────────┘
```

#### 4.2 NAT 四种类型

| 类型 | 全称 | 方向 | 修改字段 | 典型场景 |
|------|------|------|---------|---------|
| SNAT | Source NAT | 内→外 | 源 IP | 内网访问互联网 |
| DNAT | Destination NAT | 外→内 | 目标 IP+端口 | 端口映射、发布服务 |
| PAT | Port Address Translation | 内→外 | 源 IP+端口 | 家庭路由器、云 NAT |
| Full NAT | 完全 NAT | 双向 | 源和目标 | 负载均衡器（LVS） |

**SNAT vs MASQUERADE：**

```bash
# SNAT：出口 IP 固定（适合有固定公网 IP 的服务器）
iptables -t nat -A POSTROUTING -s 192.168.1.0/24 -o eth0 \
    -j SNAT --to-source 203.0.113.5

# MASQUERADE：出口 IP 动态（适合 DHCP/PPPoE 拨号）
iptables -t nat -A POSTROUTING -s 192.168.1.0/24 -o eth0 \
    -j MASQUERADE

# 性能差异：SNAT 比 MASQUERADE 快，因为不需要每次查找接口 IP
# 生产环境建议使用 SNAT
```

**DNAT 端口映射：**

```bash
# 将公网 80 端口映射到内网服务器
iptables -t nat -A PREROUTING -d 203.0.113.5 -p tcp --dport 80 \
    -j DNAT --to-destination 192.168.1.10:80

# 将公网 8080 映射到内网 80 端口（端口转换）
iptables -t nat -A PREROUTING -d 203.0.113.5 -p tcp --dport 8080 \
    -j DNAT --to-destination 192.168.1.10:80

# 一对多端口映射（端口范围）
iptables -t nat -A PREROUTING -d 203.0.113.5 -p tcp --dport 10000:20000 \
    -j DNAT --to-destination 192.168.1.10

# 查看 NAT 规则
iptables -t nat -L -n -v --line-numbers

# 查看连接跟踪表
conntrack -L
conntrack -L -s 192.168.1.10   # 按源 IP 过滤
conntrack -C                    # 当前连接数
```

#### 4.3 NAT 穿透问题

NAT 穿透（NAT Traversal）是 P2P 通信的主要挑战：

```
问题场景：
  PC-A (192.168.1.10) ←→ NAT-A ←→ Internet ←→ NAT-B ←→ PC-B (10.0.0.10)

  PC-A 想直接连接 PC-B，但：
  1. PC-A 不知道 PC-B 的公网 IP 和端口
  2. NAT-B 不允许未经请求的外部连接进入
  3. 即使知道公网 IP，NAT 映射可能已过期
```

**NAT 类型与穿透难度：**

| NAT 类型 | 描述 | 穿透难度 |
|---------|------|---------|
| Full Cone | 一旦映射建立，任何外部主机都可访问 | 容易 |
| Restricted Cone | 只有曾经通信过的外部 IP 可访问 | 中等 |
| Port Restricted Cone | 只有曾经通信过的外部 IP+端口 可访问 | 较难 |
| Symmetric | 每个目标的映射都不同 | 最难 |

**穿透方案：**

```bash
# 方案 1：STUN/TURN 服务器（WebRTC 使用）
# STUN: 发现自己的公网 IP 和端口
# TURN: 中继服务器转发流量

# 方案 2：端口映射（UPnP/NAT-PMP）
# 路由器自动配置端口映射

# 方案 3：打洞（Hole Punching）
# 双方同时向对方发送数据包，建立 NAT 映射

# 方案 4：中继服务器（最可靠但有延迟）
# 所有流量通过公网中继服务器转发
```

#### 4.4 Linux iptables NAT 完整配置

```bash
#!/bin/bash
# nat_gateway.sh - 配置 Linux 作为 NAT 网关

# 1. 开启 IP 转发
echo 1 > /proc/sys/net/ipv4/ip_forward
# 永久生效
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# 2. 配置 SNAT（内网访问外网）
iptables -t nat -A POSTROUTING -s 192.168.1.0/24 -o eth0 -j SNAT --to-source 203.0.113.5

# 3. 配置 DNAT（外网访问内网服务）
iptables -t nat -A PREROUTING -d 203.0.113.5 -p tcp --dport 80 \
    -j DNAT --to-destination 192.168.1.10:80
iptables -t nat -A PREROUTING -d 203.0.113.5 -p tcp --dport 443 \
    -j DNAT --to-destination 192.168.1.10:443

# 4. 配置 FORWARD 链（允许转发）
iptables -A FORWARD -i eth1 -o eth0 -s 192.168.1.0/24 -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -d 192.168.1.0/24 \
    -m state --state ESTABLISHED,RELATED -j ACCEPT

# 5. 查看配置
echo "=== NAT 表 ==="
iptables -t nat -L -n -v

echo "=== FORWARD 链 ==="
iptables -L FORWARD -n -v

echo "=== 连接跟踪 ==="
conntrack -C
```

---

### 5. ICMP 协议

#### 5.1 ICMP 报文结构

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Type      |     Code      |          Checksum             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Message Body (可变长度)                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

#### 5.2 ICMP 报文类型

| Type | Code | 名称 | 用途 |
|------|------|------|------|
| 0 | 0 | Echo Reply | ping 回复 |
| 3 | 0 | Network Unreachable | 网络不可达 |
| 3 | 1 | Host Unreachable | 主机不可达 |
| 3 | 3 | Port Unreachable | 端口不可达 |
| 3 | 4 | Fragmentation Needed | 需要分片（Path MTU） |
| 8 | 0 | Echo Request | ping 请求 |
| 11 | 0 | TTL Expired in Transit | TTL 超时（traceroute） |
| 11 | 1 | Fragment Reassembly Timeout | 分片重组超时 |
| 12 | 0 | Parameter Problem | 参数错误 |

#### 5.3 ping 的工作原理

```
ping 工作流程：

主机 A                                  主机 B
  │                                        │
  │──── ICMP Echo Request (Type 8) ──────▶│
  │     Seq=1, Data="abcdefghijklmnop"     │
  │                                        │
  │◀──── ICMP Echo Reply (Type 0) ────────│
  │     Seq=1, Data="abcdefghijklmnop"     │
  │                                        │
  │     计算 RTT = 收到时间 - 发送时间       │
```

```bash
# ping 常用选项
ping -c 5 8.8.8.8           # 发送 5 个包
ping -i 0.2 8.8.8.8         # 间隔 0.2 秒
ping -s 1472 8.8.8.8        # 指定数据大小
ping -W 2 8.8.8.8           # 超时 2 秒
ping -t 10 8.8.8.8          # 设置 TTL
ping -f 8.8.8.8             # flood ping（需要 root）
ping -I eth0 8.8.8.8        # 指定出口接口
ping -M do -s 1472 8.8.8.8  # Path MTU 发现

# IPv6 ping
ping6 2001:4860:4860::8888
ping -6 2001:4860:4860::8888
```

#### 5.4 traceroute 原理

```
traceroute 工作原理：

第 1 跳（TTL=1）：
  主机 ──[TTL=1]──▶ 路由器A ── TTL=0，丢弃
                    路由器A ──[ICMP Type 11]──▶ 主机
  主机记录路由器A的IP和RTT

第 2 跳（TTL=2）：
  主机 ──[TTL=2]──▶ 路由器A ──[TTL=1]──▶ 路由器B ── TTL=0，丢弃
                                            路由器B ──[ICMP Type 11]──▶ 主机
  主机记录路由器B的IP和RTT

... 重复直到到达目标主机
```

```bash
# traceroute 常用选项
traceroute 8.8.8.8              # 默认使用 UDP
traceroute -I 8.8.8.8           # 使用 ICMP（与 Windows tracert 一致）
traceroute -T 8.8.8.8           # 使用 TCP（穿越防火墙）
traceroute -n 8.8.8.8           # 不解析域名（更快）
traceroute -p 443 8.8.8.8       # 指定端口（TCP/UDP 模式）
traceroute -w 2 8.8.8.8         # 超时 2 秒
traceroute -q 1 8.8.8.8         # 每跳只发 1 个包

# mtr：结合 ping + traceroute
mtr -n -c 100 -r 8.8.8.8       # 发送 100 个包，报告模式
mtr -n -u 8.8.8.8              # 使用 UDP
mtr -n -T 8.8.8.8              # 使用 TCP
```

---

### 6. ARP 协议

#### 6.1 ARP 工作原理

```
ARP（Address Resolution Protocol）：IP 地址 → MAC 地址

场景：主机 A (192.168.1.10) 要发送数据给主机 B (192.168.1.20)

步骤 1：A 检查 ARP 缓存
  ┌─────────────────────────────┐
  │ ARP 缓存表                   │
  │ 192.168.1.1 → aa:bb:cc:dd:ee:01 │  ← 路由器
  │ 192.168.1.20 → ???            │  ← 没有 B 的记录
  └─────────────────────────────┘

步骤 2：A 发送 ARP 广播请求
  ┌────────────────────────────────────────┐
  │ ARP Request（广播）                     │
  │ Source MAC: aa:bb:cc:dd:ee:10          │
  │ Source IP:  192.168.1.10               │
  │ Target MAC: ff:ff:ff:ff:ff:ff（广播）   │
  │ Target IP:  192.168.1.20               │
  │ "谁是 192.168.1.20？请告诉 192.168.1.10"│
  └────────────────────────────────────────┘

步骤 3：B 回复 ARP 应答（单播）
  ┌────────────────────────────────────────┐
  │ ARP Reply（单播）                       │
  │ Source MAC: aa:bb:cc:dd:ee:20          │
  │ Source IP:  192.168.1.20               │
  │ Target MAC: aa:bb:cc:dd:ee:10          │
  │ Target IP:  192.168.1.10               │
  │ "我是 192.168.1.20，我的 MAC 是 aa:bb:cc:dd:ee:20"│
  └────────────────────────────────────────┘

步骤 4：A 更新 ARP 缓存，开始通信
```

#### 6.2 ARP 命令

```bash
# 查看 ARP 缓存
arp -n
ip neigh show

# 输出示例：
# 192.168.1.1 dev eth0 lladdr aa:bb:cc:dd:ee:01 REACHABLE
# 192.168.1.20 dev eth0 lladdr aa:bb:cc:dd:ee:20 STALE

# ARP 状态说明：
# REACHABLE: 活跃，可达
# STALE: 过期但仍可用，下次使用时会重新验证
# DELAY: 等待确认中
# INCOMPLETE: ARP 请求已发送，等待回复
# FAILED: ARP 解析失败

# 添加静态 ARP 条目
ip neigh add 192.168.1.100 lladdr aa:bb:cc:dd:ee:64 dev eth0 nud permanent

# 删除 ARP 条目
ip neigh del 192.168.1.100 dev eth0

# 清除所有 ARP 缓存
ip neigh flush all

# 发送免费 ARP（Gratuitous ARP）
arping -U -c 3 -I eth0 192.168.1.100
```

#### 6.3 免费 ARP（Gratuitous ARP）

免费 ARP 是主机主动发送的 ARP 请求，目标 IP 是自己的 IP：

```
免费 ARP 的用途：
1. IP 地址冲突检测：开机时发送，检测是否有其他主机使用相同 IP
2. 更新其他主机的 ARP 缓存：IP 地址变更后通知其他主机
3. 高可用切换：VIP 漂移后，新主机发送免费 ARP 更新交换机 MAC 表
```

```bash
# 发送免费 ARP（用于 VIP 漂移后的 ARP 更新）
# -U: 无故 ARP（Unsolicited ARP）
# -c 3: 发送 3 个
# -I eth0: 指定接口
arping -U -c 3 -I eth0 192.168.1.100

# 在 keepalived 中自动发送免费 ARP
# vrrp_instance VI_1 {
#     ...
#     advert_int 1
#     garp_master_refresh 5    # 每 5 秒发送一次免费 ARP
#     garp_master_repeat 3     # 每次发送 3 个
# }
```

#### 6.4 ARP 欺骗与防护

```
ARP 欺骗（ARP Spoofing）：

攻击者发送伪造的 ARP 回复，将自己的 MAC 地址与网关 IP 绑定：

正常情况：
  网关 (192.168.1.1) MAC = aa:bb:cc:dd:ee:01

攻击者发送：
  "192.168.1.1 的 MAC 是 aa:bb:cc:dd:ee:99（攻击者 MAC）"

受害者更新 ARP 缓存后：
  所有发往网关的流量 → 发送给攻击者 → 中间人攻击！
```

**ARP 欺骗防护：**

```bash
# 1. 静态 ARP 绑定（简单但维护成本高）
ip neigh add 192.168.1.1 lladdr aa:bb:cc:dd:ee:01 dev eth0 nud permanent

# 2. 使用 arpwatch 监控 ARP 变化
apt install arpwatch
systemctl enable arpwatch

# 3. 交换机端启用 DAI（Dynamic ARP Inspection）

# 4. 使用 802.1X 认证

# 5. 监控 ARP 表变化脚本
#!/bin/bash
# monitor_arp.sh
KNOWN_MACS=(
    "192.168.1.1:aa:bb:cc:dd:ee:01"
    "192.168.1.10:aa:bb:cc:dd:ee:10"
)

while true; do
    for entry in "${KNOWN_MACS[@]}"; do
        ip=$(echo "$entry" | cut -d: -f1-3)
        expected_mac=$(echo "$entry" | cut -d: -f4-)
        actual_mac=$(ip neigh show "$ip" | awk '{print $5}')
        if [ "$actual_mac" != "$expected_mac" ]; then
            echo "ALERT: ARP spoofing detected! $ip expected=$expected_mac actual=$actual_mac"
            # 发送告警...
        fi
    done
    sleep 10
done
```

---

### 7. IPv6 基础

#### 7.1 IPv6 地址格式

```
完整格式：2001:0db8:0000:0000:0000:0000:0000:0001
压缩格式：2001:db8::1

压缩规则：
1. 每段前导零可省略：0db8 → db8
2. 连续的全零段可用 :: 代替（只能使用一次）
3. 示例：
   fe80:0000:0000:0000:0000:0000:0000:0001 → fe80::1
   2001:0db8:0000:0000:0000:0000:0000:0001 → 2001:db8::1
   ff02:0000:0000:0000:0000:0000:0000:0001 → ff02::1
```

#### 7.2 IPv6 vs IPv4 对比

| 特性 | IPv4 | IPv6 |
|------|------|------|
| 地址长度 | 32 位（4 字节） | 128 位（16 字节） |
| 地址数量 | ~43 亿 | ~3.4×10^38 |
| 表示法 | 点分十进制 | 冒号十六进制 |
| 子网掩码 | 点分十进制或 CIDR | 仅 CIDR（/64 为主） |
| 广播 | 支持（255.255.255.255） | 不支持（使用组播） |
| NAT | 广泛使用 | 不需要（地址充足） |
| 分片 | 路由器和发送端 | 仅发送端 |
| 校验和 | 有（首部） | 无（依赖上层） |
| DHCP | 需要 | 可选（SLAAC） |
| IPSec | 可选 | 内置支持 |

#### 7.3 IPv6 地址类型

| 类型 | 前缀 | 说明 | IPv4 等价 |
|------|------|------|----------|
| 全球单播 | 2000::/3 | 公网可路由 | 公网 IP |
| 链路本地 | fe80::/10 | 仅在本地链路 | 169.254.0.0/16 |
| 唯一本地 | fc00::/7 | 内部网络 | 10.0.0.0/8 等 |
| 回环 | ::1/128 | 本地测试 | 127.0.0.1 |
| 未指定 | ::/128 | 表示"无地址" | 0.0.0.0 |
| 组播 | ff00::/8 | 一对多通信 | 224.0.0.0/4 |

#### 7.4 IPv6 过渡技术

```
过渡技术分类：

1. 双栈（Dual Stack）
   ┌─────────────────────────────────┐
   │ 主机同时运行 IPv4 和 IPv6 协议栈  │
   │ IPv4 地址: 10.0.0.1             │
   │ IPv6 地址: 2001:db8::1          │
   │ 两个协议独立工作                  │
   └─────────────────────────────────┘

2. 隧道（Tunneling）
   ┌──────────────────────────────────────────────┐
   │ IPv6 数据包封装在 IPv4 数据包中传输              │
   │ [IPv4 Header][IPv6 Header][IPv6 Data]          │
   │ 适用于 IPv6 孤岛穿越 IPv4 网络                   │
   └──────────────────────────────────────────────┘
   隧道类型：
   - 6to4: 自动隧道，使用 2002::/16 前缀
   - 6in4: 手动隧道（GRE、SIT）
   - Teredo: 穿越 NAT 的 IPv6 隧道

3. 翻译（Translation）
   ┌──────────────────────────────────────────────┐
   │ NAT64/DNS64: IPv6 客户端访问 IPv4 服务器        │
   │ 464XLAT: IPv4 应用在 IPv6 网络上运行             │
   └──────────────────────────────────────────────┘
```

```bash
# 查看本机 IPv6 地址
ip -6 addr show

# 测试 IPv6 连通性
ping6 -c 3 2001:4860:4860::8888

# 查看 IPv6 路由
ip -6 route show

# 检查 IPv6 配置
sysctl net.ipv6.conf.all.disable_ipv6
sysctl net.ipv6.conf.default.autoconf

# 禁用/启用 IPv6
sysctl -w net.ipv6.conf.all.disable_ipv6=1  # 禁用
sysctl -w net.ipv6.conf.all.disable_ipv6=0  # 启用
```

---

## 💻 实战练习

### 练习 1：子网划分计算

```bash
# 题目 1：计算以下 IP 的网络地址、广播地址、可用主机范围
# 172.16.35.120/20

# 解答：
ipcalc 172.16.35.120/20
# Network:   172.16.32.0/20
# HostMin:   172.16.32.1
# HostMax:   172.16.47.254
# Broadcast: 172.16.47.255
# Hosts/Net: 4094

# 题目 2：将 192.168.10.0/24 划分为至少 6 个子网，每个至少 25 台主机
# 答案：使用 /27（每子网 30 台主机，可划分 8 个子网）

# 题目 3：VLSM - 为以下需求分配 10.0.0.0/16
# 研发部 200 台、测试部 100 台、运维部 50 台、管理 10 台、点对点 2 台

# 编写脚本自动计算
#!/bin/bash
echo "=== VLSM 子网分配 ==="
echo "原网络: 10.0.0.0/16"
echo ""
echo "部门        | 需要主机 | 分配网段         | CIDR | 可用主机"
echo "------------|----------|-----------------|------|--------"
echo "研发部      | 200      | 10.0.1.0/24     | /24  | 254"
echo "测试部      | 100      | 10.0.2.0/25     | /25  | 126"
echo "运维部      | 50       | 10.0.2.128/26   | /26  | 62"
echo "管理网      | 10       | 10.0.2.192/28   | /28  | 14"
echo "点对点      | 2        | 10.0.2.208/30   | /30  | 2"
```

### 练习 2：NAT 配置实验

```bash
# 实验环境：使用 network namespace 模拟 NAT 场景

# 1. 创建拓扑
# 内网主机 (ns-internal) → NAT 网关 (ns-nat) → 外网 (ns-external)

# 创建 namespace
ip netns add ns-internal
ip netns add ns-nat
ip netns add ns-external

# 创建 veth pair
ip link add veth-int type veth peer name veth-nat-int
ip link add veth-ext type veth peer name veth-nat-ext

# 分配到 namespace
ip link set veth-int netns ns-internal
ip link set veth-nat-int netns ns-nat
ip link set veth-nat-ext netns ns-nat
ip link set veth-ext netns ns-external

# 配置 IP
ip netns exec ns-internal ip addr add 192.168.1.10/24 dev veth-int
ip netns exec ns-internal ip link set veth-int up
ip netns exec ns-internal ip link set lo up
ip netns exec ns-internal ip route add default via 192.168.1.1

ip netns exec ns-nat ip addr add 192.168.1.1/24 dev veth-nat-int
ip netns exec ns-nat ip addr add 10.0.0.1/24 dev veth-nat-ext
ip netns exec ns-nat ip link set veth-nat-int up
ip netns exec ns-nat ip link set veth-nat-ext up
ip netns exec ns-nat ip link set lo up

ip netns exec ns-external ip addr add 10.0.0.10/24 dev veth-ext
ip netns exec ns-external ip link set veth-ext up
ip netns exec ns-external ip link set lo up

# 2. 在 NAT 网关上配置 SNAT
ip netns exec ns-nat sysctl -w net.ipv4.ip_forward=1
ip netns exec ns-nat iptables -t nat -A POSTROUTING -s 192.168.1.0/24 \
    -o veth-nat-ext -j SNAT --to-source 10.0.0.1

# 3. 测试连通性
ip netns exec ns-internal ping -c 3 10.0.0.10

# 4. 在 ns-external 上抓包观察
ip netns exec ns-external tcpdump -i veth-ext -n icmp
# 应该看到源 IP 是 10.0.0.1 而不是 192.168.1.10

# 5. 清理
ip netns delete ns-internal
ip netns delete ns-nat
ip netns delete ns-external
```

### 练习 3：故障排查挑战

```bash
# 场景：某服务器无法访问外网，但能 ping 通同网段其他服务器

# 排查步骤：
# 1. 检查 IP 配置
ip addr show
ip route show

# 2. 检查默认网关
ip route show default
ping -c 1 <网关IP>

# 3. 检查 DNS
cat /etc/resolv.conf
nslookup example.com

# 4. 检查防火墙
iptables -L -n
iptables -t nat -L -n

# 5. 检查 ARP
ip neigh show
arp -n

# 6. 抓包分析
tcpdump -i eth0 -n host 8.8.8.8
# 观察是否有 ICMP Echo Request 发出
# 观察是否有 ICMP Echo Reply 返回
# 观察是否有 ICMP 不可达消息

# 常见原因：
# - 默认网关配置错误
# - 防火墙规则阻止出站
# - NAT 规则缺失
# - 路由表错误
# - MTU 问题（需要分片但 DF 标志置位）
```

---

## 🏥 SRE 实战案例

### 案例 1：云服务器 NAT 网关带宽瓶颈

**场景：**
- 3 台 Web 服务器 + 2 台 API 服务器通过 NAT 网关访问公网
- NAT 网关带宽 5 Mbps
- API 服务器频繁超时

**排查过程：**

```bash
# 1. 检查 NAT 连接数
conntrack -C
conntrack -L | wc -l

# 2. 分析连接分布
conntrack -L | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn
# 输出：
# 5000 10.0.2.10    ← API 服务器 1
# 3000 10.0.2.11    ← API 服务器 2
# 2000 10.0.1.10    ← Web 服务器 1

# 3. 检查带宽
iftop -i eth0
sar -n DEV 1 10

# 4. 检查 TIME_WAIT 堆积
ss -s | grep -i wait
netstat -ant | grep TIME_WAIT | wc -l
```

**解决方案：**
```bash
# 短期：升级 NAT 网关带宽
# 中期：优化连接池，减少短连接
# 长期：使用 VPC Endpoint 访问云服务

# 内核参数优化
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.tcp_fin_timeout=15
sysctl -w net.ipv4.tcp_max_syn_backlog=65535
```

### 案例 2：子网划分不当导致 IP 冲突

**场景：**
- 两个部门各自创建了 192.168.1.0/24 网段
- 合并网络后出现 IP 地址冲突
- 部分服务器间歇性无法访问

**排查过程：**

```bash
# 1. 检查 ARP 表是否有重复 MAC
arp -n | sort -k3 | uniq -d -f2

# 2. 使用 arping 检测 IP 冲突
arping -c 3 -I eth0 192.168.1.100
# 如果收到多个不同 MAC 的回复，说明有冲突

# 3. 检查交换机 MAC 地址表
# 在交换机上执行：
# show mac address-table | include 192.168.1.100

# 4. 抓包分析
tcpdump -i eth0 -n arp
# 观察同一 IP 是否有多个 MAC 回复
```

**解决方案：**
```bash
# 1. 重新规划子网
# 部门 A: 192.168.1.0/24
# 部门 B: 192.168.2.0/24

# 2. 使用 DHCP 保留地址避免冲突

# 3. 部署 IPAM（IP Address Management）系统

# 4. 配置 ARP 检测
# 交换机启用 DAI（Dynamic ARP Inspection）
```

### 案例 3：IPv6 迁移方案设计

**场景：**
- 公司现有纯 IPv4 网络
- 需要逐步迁移到 IPv6

**迁移方案：**

```bash
# Phase 1: 评估与准备
# - 盘点所有网络设备 IPv6 支持情况
# - 测试关键应用 IPv6 兼容性
# - 申请 IPv6 地址段

# Phase 2: 双栈部署
# - 核心交换机启用双栈
# - DNS 服务器添加 AAAA 记录
# - 负载均衡器配置 IPv6 虚拟 IP

# Phase 3: 逐步迁移
# - 新服务优先使用 IPv6
# - 旧服务逐步改造
# - 监控 IPv6 流量占比

# Phase 4: 验证与优化
# - 测试 IPv6-only 场景
# - 优化 IPv6 路由
# - 文档更新

# 检查 IPv6 部署状态
ip -6 addr show
ip -6 route show
dig -6 example.com AAAA
curl -6 https://example.com
```

---

## 🎯 面试题精选（10 道）

### 题目 1：子网划分计算

**题目**：给定 IP 地址 10.1.2.73/26，求网络地址、广播地址、可用 IP 范围。

**答案**：
```
/26 表示前缀长度 26 位，子网掩码 255.255.255.192
73 的二进制: 01001001
掩码最后字节: 11000000（192）
73 AND 192 = 64

网络地址: 10.1.2.64
广播地址: 10.1.2.127
可用范围: 10.1.2.65 ~ 10.1.2.126
可用主机: 62 台
```

### 题目 2：NAT 的四种类型

**题目**：请解释 SNAT、DNAT、PAT 和 Full NAT 的区别。

**答案**：
| 类型 | 方向 | 修改内容 | 场景 |
|------|------|---------|------|
| SNAT | 内→外 | 源 IP | 内网访问互联网 |
| DNAT | 外→内 | 目标 IP+端口 | 端口映射 |
| PAT | 内→外 | 源 IP+端口 | 多对一（家庭路由器） |
| Full NAT | 双向 | 源+目标 | 负载均衡（LVS） |

### 题目 3：IPv6 的优势

**题目**：IPv6 相比 IPv4 有哪些主要优势？

**答案**：
1. 地址空间：128 位 vs 32 位，约 3.4×10^38 个地址
2. 简化首部：去除校验和，路由器处理更快
3. 无需 NAT：地址充足，端到端通信
4. 内置 IPSec：安全性更好
5. 自动配置：SLAAC 无需 DHCP
6. 更好的组播支持
7. 流标签：支持 QoS

### 题目 4：ARP 工作原理

**题目**：描述 ARP 的完整工作过程。

**答案**：
1. 主机 A 要发送数据给主机 B，先检查 ARP 缓存
2. 如果缓存中没有 B 的 MAC，发送 ARP 广播请求
3. 广播内容："谁是 192.168.1.20？请告诉 192.168.1.10"
4. 主机 B 收到后，单播回复自己的 MAC 地址
5. 主机 A 收到回复，更新 ARP 缓存，开始通信

### 题目 5：traceroute 原理

**题目**：traceroute 是如何发现路径上每一跳路由器的？

**答案**：
traceroute 利用 TTL 递增的特性：
1. 发送 TTL=1 的数据包，第一跳路由器 TTL 减为 0，返回 ICMP Time Exceeded
2. 发送 TTL=2 的数据包，第二跳路由器返回 ICMP Time Exceeded
3. 依次递增 TTL，直到目标主机返回 ICMP Port Unreachable 或 Echo Reply
4. 记录每次返回的路由器 IP 和 RTT

### 题目 6：CIDR 和子网划分

**题目**：192.168.1.0/24 能划分成多少个 /28 子网？每个子网有多少可用主机？

**答案**：
```
/24 到 /28 差 4 位
可划分子网数: 2^4 = 16 个
每个子网可用主机: 2^(32-28) - 2 = 2^4 - 2 = 14 台
```

### 题目 7：TTL 的作用

**题目**：IP 数据包的 TTL 字段有什么作用？为什么需要它？

**答案**：
TTL（Time To Live）防止数据包在网络中无限循环：
1. 每经过一个路由器，TTL 减 1
2. 当 TTL 减到 0 时，路由器丢弃数据包并返回 ICMP Time Exceeded
3. 如果没有 TTL，路由环路会导致数据包永远在网络中传输
4. traceroute 利用 TTL 递增来发现路径

### 题目 8：NAT 穿透

**题目**：什么是 NAT 穿透？为什么 P2P 应用需要 NAT 穿透？

**答案**：
NAT 穿透是指让位于 NAT 后面的主机能够直接通信的技术：
1. NAT 隐藏了内网主机的真实 IP，外部无法主动连接
2. P2P 应用需要双方直接通信，必须穿透 NAT
3. 常用方案：STUN/TURN、端口映射（UPnP）、打洞（Hole Punching）
4. Symmetric NAT 最难穿透，通常需要 TURN 中继

### 题目 9：ARP 欺骗

**题目**：什么是 ARP 欺骗？如何防护？

**答案**：
ARP 欺骗是攻击者发送伪造 ARP 回复，将自己的 MAC 与网关 IP 绑定：
1. 攻击后果：中间人攻击、流量劫持
2. 防护措施：
   - 静态 ARP 绑定
   - 交换机启用 DAI
   - 使用 802.1X 认证
   - 部署 ARP 监控工具（arpwatch）

### 题目 10：IPv4 私有地址段

**题目**：RFC 1918 定义了哪些私有地址段？为什么需要私有地址？

**答案**：
```
私有地址段：
- 10.0.0.0/8（A 类，约 1677 万地址）
- 172.16.0.0/12（B 类，约 104 万地址）
- 192.168.0.0/16（C 类，约 6.5 万地址）

需要私有地址的原因：
1. IPv4 地址不足，需要复用
2. 内部网络不需要公网路由
3. 通过 NAT 转换后访问互联网
4. 提高安全性（内网地址不暴露）
```

---

## 📚 深入阅读

### RFC 文档
- [RFC 791 - Internet Protocol](https://datatracker.ietf.org/doc/html/rfc791)
- [RFC 1918 - Address Allocation for Private Internets](https://datatracker.ietf.org/doc/html/rfc1918)
- [RFC 4632 - Classless Inter-Domain Routing (CIDR)](https://datatracker.ietf.org/doc/html/rfc4632)
- [RFC 826 - ARP](https://datatracker.ietf.org/doc/html/rfc826)
- [RFC 792 - ICMP](https://datatracker.ietf.org/doc/html/rfc792)
- [RFC 4291 - IPv6 Addressing Architecture](https://datatracker.ietf.org/doc/html/rfc4291)
- [RFC 3022 - Traditional NAT](https://datatracker.ietf.org/doc/html/rfc3022)

### 推荐书籍
- 《TCP/IP 详解 卷一：协议》- W. Richard Stevens
- 《计算机网络：自顶向下方法》- James Kurose
- 《图解 TCP/IP》- 竹下隆史

### 实用工具
| 工具 | 用途 |
|------|------|
| `ipcalc` | IP 地址计算 |
| `ip` | 网络配置（iproute2） |
| `conntrack` | 连接跟踪 |
| `arping` | ARP 测试 |
| `nmap` | 网络扫描 |
| `tcpdump` | 抓包分析 |

### 在线练习
- [subnet-calculator.com](https://www.subnet-calculator.com/)
- [ipv6test.google.com](https://ipv6test.google.com/)

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出 IPv4 首部结构并解释每个字段
- [ ] 能快速判断 IP 地址属于哪一类（A/B/C/D/E）
- [ ] 理解私有地址段（10/172.16/192.168）和特殊地址
- [ ] 掌握子网掩码计算和 CIDR 表示法
- [ ] 理解 NAT 四种类型及工作原理
- [ ] 知道 ICMP 报文类型和 ping/traceroute 原理
- [ ] 理解 ARP 工作过程和 ARP 欺骗防护
- [ ] 了解 IPv6 地址格式和过渡技术

### 实操检查点
- [ ] 能使用 ipcalc 计算子网
- [ ] 能使用 ip 命令查看和配置 IP 地址
- [ ] 能使用 iptables 配置 SNAT/DNAT
- [ ] 能使用 conntrack 查看 NAT 连接表
- [ ] 能使用 arp 和 ip neigh 查看 ARP 表
- [ ] 能使用 ping 和 traceroute 排查网络问题
- [ ] 能完成 VLSM 子网划分
- [ ] 能使用 network namespace 模拟网络拓扑

---

> 💡 **SRE 思考题**：如果你的 VPC 内有 500 台服务器需要通过 NAT 网关访问公网，每台平均产生 100 个并发连接，NAT 网关的连接跟踪表需要多大？带宽应该如何规划？
>
> **提示**：连接跟踪表大小 = 500 × 100 = 50,000 条目。带宽需要根据每连接的平均带宽和并发连接数计算。
