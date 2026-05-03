# Day 87: Docker 网络进阶

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 网络高级配置、容器网络方案、网络性能调优
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 81 Docker 网络管理、Day 86 Docker 安全

---

## 🎯 学习目标

- 理解 Docker 网络底层原理（iptables、VXLAN）
- 掌握 macvlan 和 ipvlan 网络驱动配置
- 了解主流容器网络方案（Calico、Flannel、Cilium）的原理与区别
- 能够进行容器网络性能调优
- 掌握容器网络故障排查方法

---

## 📖 核心知识点

### 1. Docker 网络与 iptables

#### 1.1 Docker 网络 iptables 规则结构

Docker 依赖 iptables 实现网络隔离、端口映射和容器间通信控制。理解 iptables 规则是排查网络问题和加固安全的关键。

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker iptables 链结构                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   入站流量                                                   │
│   ─────────                                                  │
│   PREROUTING ──→ DOCKER 链 ──→ DNAT (端口映射)             │
│                                                             │
│   转发流量（容器出站/容器间）                                 │
│   ─────────                                                  │
│   FORWARD ──→ DOCKER-USER ──→ DOCKER-FORWARD               │
│                    │                │                        │
│                    │ (用户自定义)    ▼                        │
│                    │         DOCKER-ISOLATION-STAGE-1        │
│                    │         DOCKER-ISOLATION-STAGE-2        │
│                    ▼                                        │
│              优先级最高，                                    │
│              不被 Docker 覆盖                                │
│                                                             │
│   出站流量（容器 → 外部）                                    │
│   ─────────                                                  │
│   OUTPUT ──→ DOCKER-OUTPUT                                  │
│   POSTROUTING ──→ MASQUERADE (容器出站 SNAT)               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 查看 Docker 创建的 iptables 规则

```bash
# 查看 NAT 表规则（端口映射）
sudo iptables -t nat -L -n -v --line-numbers

# 输出示例：
# Chain DOCKER (2 references)
# num  target     prot opt source     destination
# 1    RETURN     all  --  0.0.0.0/0  0.0.0.0/0
# 2    DNAT       tcp  --  0.0.0.0/0  0.0.0.0/0  tcp dpt:8080 to:172.17.0.2:80

# 查看 FILTER 表规则
sudo iptables -L DOCKER-USER -n -v --line-numbers
sudo iptables -L DOCKER-FORWARD -n -v --line-numbers
sudo iptables -L DOCKER-ISOLATION-STAGE-1 -n -v
sudo iptables -L DOCKER-ISOLATION-STAGE-2 -n -v

# 查看完整的 DOCKER 链
sudo iptables -L DOCKER -n -v --line-numbers

# 实时监控 iptables 规则变化
sudo conntrack -E
```

#### 1.3 DOCKER-USER 链：自定义安全规则

`DOCKER-USER` 是 Docker 预留给用户的链，规则优先级最高且不会被 Docker 覆盖。这是实现自定义网络安全策略的最佳位置。

```bash
# 场景 1：只允许特定 IP 访问容器的 80 端口
sudo iptables -I DOCKER-USER -i eth0 -p tcp --dport 80 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -I DOCKER-USER -i eth0 -p tcp --dport 80 -j DROP

# 场景 2：阻止容器访问外部网络（仅允许访问 DNS）
sudo iptables -I DOCKER-USER -i docker0 -o eth0 -p udp --dport 53 -j ACCEPT
sudo iptables -I DOCKER-USER -i docker0 -o eth0 -p tcp --dport 53 -j ACCEPT
sudo iptables -I DOCKER-USER -i docker0 -o eth0 -j DROP

# 场景 3：阻止容器 A (172.17.0.2) 访问容器 B (172.17.0.3) 的 3306 端口
sudo iptables -I DOCKER-USER -s 172.17.0.2 -d 172.17.0.3 -p tcp --dport 3306 -j DROP

# 场景 4：限制容器的出站连接速率（防 DDoS）
sudo iptables -I DOCKER-USER -i docker0 -o eth0 -m conntrack --ctstate NEW \
  -m limit --limit 100/min --limit-burst 50 -j ACCEPT
sudo iptables -I DOCKER-USER -i docker0 -o eth0 -m conntrack --ctstate NEW -j DROP

# 保存 iptables 规则（重启后生效）
sudo apt-get install iptables-persistent
sudo netfilter-persistent save
# 或手动保存
sudo iptables-save > /etc/iptables/rules.v4
sudo ip6tables-save > /etc/iptables/rules.v6
```

#### 1.4 Docker 网络隔离机制

```
┌─────────────────────────────────────────────────────────────┐
│                Docker 网络隔离原理                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   网络 A (172.18.0.0/16)      网络 B (172.19.0.0/16)       │
│   ┌─────────────────┐        ┌─────────────────┐           │
│   │  容器1  容器2    │        │  容器3  容器4    │           │
│   │  .0.2    .0.3   │        │  .0.2    .0.3   │           │
│   └────────┬────────┘        └────────┬────────┘           │
│            │                          │                     │
│            ▼                          ▼                     │
│   ┌─────────────┐            ┌─────────────┐              │
│   │  br-abc123  │            │  br-def456  │              │
│   └─────────────┘            └─────────────┘              │
│                                                             │
│   DOCKER-ISOLATION-STAGE-1:                                │
│   - 如果入接口 != 出接口 → DROP                             │
│   - 网络 A 的流量无法到达网络 B                             │
│                                                             │
│   DOCKER-ISOLATION-STAGE-2:                                │
│   - 额外的隔离检查                                         │
│   - 确保不同 bridge 网络完全隔离                            │
│                                                             │
│   同一网络内的容器可以通信（除非 icc=false）                 │
│   不同网络的容器完全隔离                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

```bash
# 查看网络隔离规则
sudo iptables -L DOCKER-ISOLATION-STAGE-1 -n -v
# DROP all -- 172.18.0.0/16 172.19.0.0/16
# DROP all -- 172.19.0.0/16 172.18.0.0/16

# 验证隔离效果
# 网络 A 的容器
docker run --rm --network net-a alpine ping -c 2 172.19.0.2
# 不通

# 连接到两个网络的容器（作为网关）
docker network connect net-a gateway-container
docker network connect net-b gateway-container
# gateway-container 同时在两个网络中
```

#### 1.5 禁用 Docker 的 iptables 管理

```json
// /etc/docker/daemon.json
{
  "iptables": false
}
```

```bash
# 禁用后 Docker 不会创建任何 iptables 规则
# 需要手动配置全部网络规则

# 手动配置 NAT
sudo iptables -t nat -A POSTROUTING -s 172.17.0.0/16 ! -o docker0 -j MASQUERADE

# 手动配置转发
sudo iptables -A FORWARD -i docker0 -o eth0 -j ACCEPT
sudo iptables -A FORWARD -i eth0 -o docker0 -m state --state RELATED,ESTABLISHED -j ACCEPT
sudo iptables -A FORWARD -i docker0 -o docker0 -j ACCEPT

# 适用场景：
# - 使用自定义网络管理工具（如 Calico、Cilium）
# - 需要完全控制 iptables 规则
# - 多 Docker 实例共存
```

---

### 2. VXLAN 网络深度解析

#### 2.1 VXLAN 原理

VXLAN（Virtual Extensible LAN）是一种网络虚拟化技术，通过在三层网络上封装二层帧来构建跨物理网络的虚拟网络。Docker Overlay 网络和 Flannel VXLAN 模式都基于此技术。

```
┌─────────────────────────────────────────────────────────────┐
│                    VXLAN 封装结构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   原始以太帧                                                 │
│   ┌──────────────────────────────────────────────────────┐ │
│   │ Dst MAC │ Src MAC │ Type │         Payload           │ │
│   └──────────────────────────────────────────────────────┘ │
│                                                             │
│   VXLAN 封装后（增加 50 字节开销）                           │
│   ┌──────────────────────────────────────────────────────┐ │
│   │ Outer │ Outer │ UDP  │ VXLAN │ Inner │ Inner        │ │
│   │ Eth   │ IP    │ 8B   │ HDR   │ Eth   │ Payload      │ │
│   │ 14B   │ 20B   │      │ 8B    │ 14B   │              │ │
│   └──────────────────────────────────────────────────────┘ │
│                                                             │
│   VXLAN Header (8 字节)                                     │
│   ┌──────────────────────────────────────────────────────┐ │
│   │Flags|Rsvd(24b)│    VNI (24 bits)        │Rsvd(8b)   │ │
│   │ 8b  │         │  网络标识 0-16,777,215   │           │ │
│   └──────────────────────────────────────────────────────┘ │
│                                                             │
│   关键参数：                                                 │
│   - VNI：虚拟网络标识符，类似 VLAN ID 但范围更大              │
│   - UDP 目标端口：4789（默认）                               │
│   - MTU 开销：1500 - 50 = 1450（需调整 MTU 避免分片）       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2 Docker Overlay 网络（基于 VXLAN）

```bash
# 1. 初始化 Swarm（Overlay 网络需要 Swarm 模式）
docker swarm init --advertise-addr 192.168.1.10

# 2. 创建 Overlay 网络
docker network create \
  --driver overlay \
  --subnet 10.0.9.0/24 \
  --gateway 10.0.9.1 \
  --opt encrypted \
  my-overlay

# 3. 在 Overlay 网络上部署服务
docker service create \
  --name web \
  --network my-overlay \
  --replicas 3 \
  --publish published=8080,target=80 \
  nginx

# 4. 查看 VXLAN 配置
# 在 worker 节点上
ip link show type vxlan
ip -d link show vxlan0

# 5. 查看 VXLAN 转发数据库（FDB）
bridge fdb show dev vxlan0

# 6. 查看 VXLAN 收到的流量
sudo tcpdump -i eth0 port 4789 -nn
```

#### 2.3 Overlay 网络流量路径

```
┌─────────────────────────────────────────────────────────────┐
│                Overlay 网络数据包流向                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   容器 A (Node 1)                      容器 B (Node 2)      │
│   10.0.9.2                             10.0.9.3             │
│      │                                    ▲                 │
│      ▼                                    │                 │
│   ┌──────────┐                        ┌──────────┐         │
│   │ veth pair│                        │ veth pair│         │
│   └──────────┘                        └──────────┘         │
│      │                                    ▲                 │
│      ▼                                    │                 │
│   ┌──────────┐                        ┌──────────┐         │
│   │ overlay  │                        │ overlay  │         │
│   │ bridge   │                        │ bridge   │         │
│   └──────────┘                        └──────────┘         │
│      │                                    ▲                 │
│      ▼                                    │                 │
│   ┌──────────┐      VXLAN 封装     ┌──────────┐           │
│   │ vxlan0   │ ──────────────────→ │ vxlan0   │           │
│   └──────────┘   (UDP 4789)        └──────────┘           │
│      │                                    ▲                 │
│      ▼                                    │                 │
│   ┌──────────┐      物理网络        ┌──────────┐           │
│   │  eth0    │ ──────────────────→ │  eth0    │           │
│   │192.168.1.10                    │192.168.1.11          │
│   └──────────┘                      └──────────┘           │
│                                                             │
│   流量统计：                                                 │
│   - 原始数据包 + 50 字节 VXLAN 封装开销                     │
│   - MTU 需要设置为 1450（1500 - 50）                        │
│   - 加密模式下额外增加加密开销                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2.4 VXLAN 性能优化

```bash
# 1. 调整 MTU 避免分片
docker network create \
  --driver overlay \
  --opt com.docker.network.driver.mtu=1450 \
  optimized-overlay

# 全局 MTU 设置
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "mtu": 1450
}
EOF

# 2. 启用网卡硬件卸载（如果支持 VXLAN Offload）
# 检查网卡是否支持
ethtool -k eth0 | grep udp_tnl
# tx-udp_tnl-segmentation: on
# rx-udp_tnl-segmentation: on

# 启用卸载
ethtool -K eth0 tx-udp_tnl-segmentation on
ethtool -K eth0 rx-udp_tnl-segmentation on

# 3. 高性能替代方案：使用 host-gw（同子网时）
# Flannel host-gw 不做封装，直接路由，性能接近原生
# 但要求所有节点在同一子网

# 4. 使用 macvlan/ipvlan 替代（需要直接物理网络接入时）
```

---

### 3. macvlan 网络

#### 3.1 macvlan 原理

macvlan 允许在同一个物理接口上创建多个虚拟接口，每个接口拥有独立的 MAC 地址。容器直接出现在物理网络中，无需 NAT，性能接近原生。

```
┌─────────────────────────────────────────────────────────────┐
│                    macvlan 网络架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   容器 1              容器 2              容器 3             │
│   MAC: 02:42:ac:11:00:02                                    │
│   IP: 192.168.1.101  IP: 192.168.1.102  IP: 192.168.1.103  │
│      │                   │                   │              │
│      ▼                   ▼                   ▼              │
│   ┌────────────────────────────────────────────────────┐   │
│   │               macvlan (父接口 eth0)                │   │
│   │  macvlan0          macvlan1          macvlan2      │   │
│   └────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│                    ┌──────────┐                             │
│                    │  物理网卡 │                             │
│                    │   eth0   │                             │
│                    └──────────┘                             │
│                          │                                  │
│                          ▼                                  │
│                    ┌──────────┐                             │
│                    │   交换机  │                             │
│                    └──────────┘                             │
│                                                             │
│   特点：                                                     │
│   1. 每个容器拥有独立的 MAC + IP                             │
│   2. 容器直接出现在物理网络，类似物理机                       │
│   3. 无 NAT，无端口映射，性能接近原生                        │
│   4. 不需要 Docker 网桥                                     │
│   5. 需要物理网卡支持混杂模式                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 macvlan 模式对比

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| bridge | 同一父接口的容器可以直接通信（默认模式） | 最常用，推荐 |
| vepa | 容器间流量通过物理交换机返回（需要交换机支持 VEPA） | 需要流量经过物理设备审计 |
| private | 同一父接口的容器间完全隔离 | 安全隔离场景 |
| passthru | 只允许一个容器绑定到物理接口 | 单容器独占网卡 |

#### 3.3 macvlan 实战配置

```bash
# 1. 创建 macvlan 网络
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  -o macvlan_mode=bridge \
  my-macvlan

# 2. 运行容器
docker run -d --name web1 \
  --network my-macvlan \
  --ip 192.168.1.101 \
  nginx:alpine

docker run -d --name web2 \
  --network my-macvlan \
  --ip 192.168.1.102 \
  nginx:alpine

# 3. 验证容器网络
docker exec web1 ip addr show eth0
# eth0@if2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
#     link/ether 02:42:c0:a8:01:65
#     inet 192.168.1.101/24 brd 192.168.1.255 scope global eth0

# 4. 从物理网络的其他主机访问
curl http://192.168.1.101
curl http://192.168.1.102

# 5. 使用私有模式（容器间隔离）
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  -o macvlan_mode=private \
  my-macvlan-private
```

#### 3.4 macvlan 与宿主机通信问题及解决

macvlan 的一个已知限制是容器无法直接与宿主机通信。这是因为数据包从容器发出后通过 macvlan 子接口到达物理接口，但物理接口不会把数据包路由回自己的子接口。

```bash
# 问题演示
# 宿主机无法 ping 通 macvlan 容器
ping 192.168.1.101  # 从宿主机发起，不通

# 解决方案：创建 macvlan shim 接口
# 宿主机创建一个 macvlan 子接口用于与容器通信
sudo ip link add macvlan-shim link eth0 type macvlan mode bridge
sudo ip addr add 192.168.1.250/32 dev macvlan-shim
sudo ip link set macvlan-shim up

# 添加到容器的路由
sudo ip route add 192.168.1.101/32 dev macvlan-shim
sudo ip route add 192.168.1.102/32 dev macvlan-shim

# 验证通信
ping 192.168.1.101  # 现在通了

# 持久化配置
cat > /etc/network/if-up.d/macvlan-shim << 'SCRIPT'
#!/bin/bash
if [[ "$IFACE" == "eth0" ]]; then
    ip link add macvlan-shim link eth0 type macvlan mode bridge
    ip addr add 192.168.1.250/32 dev macvlan-shim
    ip link set macvlan-shim up
    ip route add 192.168.1.0/24 dev macvlan-shim
fi
SCRIPT
sudo chmod +x /etc/network/if-up.d/macvlan-shim
```

---

### 4. ipvlan 网络

#### 4.1 ipvlan vs macvlan

```
┌─────────────────────────────────────────────────────────────┐
│                ipvlan vs macvlan 对比                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   macvlan: 每个容器独立 MAC 地址                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  容器1(MAC-A)  容器2(MAC-B)  容器3(MAC-C)          │  │
│   │              ↓                                      │  │
│   │         物理交换机看到多个 MAC                        │  │
│   └─────────────────────────────────────────────────────┘  │
│   问题：MAC 地址数量可能受限，云环境可能拒绝                  │
│                                                             │
│   ipvlan: 共享父接口 MAC，每个容器独立 IP                    │
│   ┌─────────────────────────────────────────────────────┐  │
│   │  容器1(IP-1)   容器2(IP-2)   容器3(IP-3)           │  │
│   │         共享父接口 MAC（交换机只看到一个 MAC）        │  │
│   └─────────────────────────────────────────────────────┘  │
│   优点：云环境友好，不受 MAC 地址限制                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2 ipvlan L2 模式

```bash
# ipvlan L2 模式：类似 macvlan bridge 模式，工作在二层
docker network create -d ipvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  -o ipvlan_mode=l2 \
  my-ipvlan-l2

# 运行容器
docker run -d --name app1 \
  --network my-ipvlan-l2 \
  --ip 192.168.1.110 \
  nginx:alpine

docker run -d --name app2 \
  --network my-ipvlan-l2 \
  --ip 192.168.1.111 \
  nginx:alpine

# 容器间通信正常
docker exec app1 ping -c 3 192.168.1.111

# 与 macvlan bridge 类似，但共享 MAC
docker exec app1 ip link show eth0
# link/ether <父接口MAC>  -- 所有 ipvlan 容器使用相同的 MAC
```

#### 4.3 ipvlan L3 模式

```bash
# ipvlan L3 模式：工作在三层，通过路由通信
# 不依赖交换机的 MAC 学习，适合大规模部署
docker network create -d ipvlan \
  --subnet=10.10.0.0/24 \
  -o parent=eth0 \
  -o ipvlan_mode=l3 \
  my-ipvlan-l3

# 运行容器
docker run -d --name app3 \
  --network my-ipvlan-l3 \
  --ip 10.10.0.10 \
  nginx:alpine

# 注意：L3 模式下容器与宿主机同网段设备通信需要路由
# 宿主机添加路由
sudo ip route add 10.10.0.0/24 dev eth0

# 外部路由器需要配置回程路由
# 10.10.0.0/24 via 192.168.1.10 (宿主机 IP)

# L3 模式限制：不支持广播/多播，容器无法使用 DHCP
```

#### 4.4 ipvlan L3S 模式

```bash
# ipvlan L3S 模式：L3 + 支持 netfilter/iptables
docker network create -d ipvlan \
  --subnet=10.20.0.0/24 \
  -o parent=eth0 \
  -o ipvlan_mode=l3s \
  my-ipvlan-l3s

# L3S 相比 L3 的优势：
# - 支持 iptables 规则（可以做 SNAT/DNAT）
# - 支持 conntrack 连接跟踪
# - 与宿主机网络栈完全集成
# - 可以使用容器端口映射

# 验证 iptables 规则生效
docker run -d --name app4 \
  --network my-ipvlan-l3s \
  --ip 10.20.0.10 \
  -p 8080:80 \
  nginx:alpine
```

---

### 5. 容器网络方案深度对比

#### 5.1 总览

```
┌──────────────────────────────────────────────────────────────┐
│               主流容器网络方案对比                             │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ 特性         │ Flannel      │ Calico       │ Cilium         │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 数据平面     │ VXLAN/host-gw│ iptables/    │ eBPF           │
│              │              │ eBPF         │                │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 网络策略     │ 不支持       │ 支持(L3/L4)  │ 支持(L3-L7)    │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 路由模式     │ 封装为主     │ BGP 直接路由 │ 封装+直接路由  │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 性能         │ 中等         │ 高           │ 极高           │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 复杂度       │ 简单         │ 中等         │ 复杂           │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 加密         │ WireGuard    │ WireGuard/IPsec │ WireGuard/IPsec│
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 服务网格     │ 不支持       │ 不支持       │ 军edt/Istio集成│
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 可观测性     │ 基础         │ 中等         │ Hubble(强)     │
├──────────────┼──────────────┼──────────────┼────────────────┤
│ 适用场景     │ 小型/学习    │ 中大型生产   │ 高性能/云原生  │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

#### 5.2 Flannel 详解

Flannel 是最简单的 Kubernetes 网络方案，专注于提供 Pod 间网络连通性。

```bash
# 安装 Flannel
kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml

# 查看 Flannel Pod
kubectl get pods -n kube-flannel

# 查看 Flannel 配置
kubectl get configmap kube-flannel-cfg -n kube-flannel -o yaml

# 查看 Flannel 接口
ip link show flannel.1
ip addr show flannel.1

# 查看 Flannel 子网分配
ls /run/flannel/subnet.env
# FLANNEL_NETWORK=10.244.0.0/16
# FLANNEL_SUBNET=10.244.1.1/24
# FLANNEL_MTU=1450
# FLANNEL_IPMASQ=true
```

**Flannel 后端模式：**

| 后端 | 原理 | 性能 | 适用场景 |
|------|------|------|----------|
| VXLAN | UDP 封装 VXLAN 帧 | 中等 | 跨子网、通用场景 |
| host-gw | 直接路由到目标主机 | 高 | 同子网、追求性能 |
| WireGuard | 加密隧道 | 中等 | 需要加密通信 |

```bash
# 修改 Flannel 后端为 host-gw（同子网高性能）
kubectl edit configmap kube-flannel-cfg -n kube-flannel
# 修改 Backend 部分：
# Backend:
#   Type: host-gw
# 重启 Flannel Pod 生效
kubectl rollout restart daemonset kube-flannel -n kube-flannel
```

**Flannel VXLAN 流量路径：**

```
┌─────────────────────────────────────────────────────────────┐
│                Flannel VXLAN 数据包路径                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Pod A (Node 1: 10.244.1.5)      Pod B (Node 2: 10.244.2.8)│
│      │                                    ▲                 │
│      ▼                                    │                 │
│   ┌──────────┐                        ┌──────────┐         │
│   │ veth pair│                        │ veth pair│         │
│   └──────────┘                        └──────────┘         │
│      │                                    ▲                 │
│      ▼                                    │                 │
│   ┌──────────┐                        ┌──────────┐         │
│   │  cni0    │                        │  cni0    │         │
│   │ (bridge) │                        │ (bridge) │         │
│   └──────────┘                        └──────────┘         │
│      │                                    ▲                 │
│      ▼                                    │                 │
│   ┌──────────┐                        ┌──────────┐         │
│   │ flannel.1│                        │ flannel.1│         │
│   │ (VXLAN)  │ ─── UDP 4789 封装 ──→ │ (VXLAN)  │         │
│   └──────────┘                        └──────────┘         │
│      │                                    ▲                 │
│      ▼                                    │                 │
│   ┌──────────┐                        ┌──────────┐         │
│   │   eth0   │ ───── 物理网络 ─────→ │   eth0   │         │
│   │192.168.1.10                      │192.168.1.11        │
│   └──────────┘                        └──────────┘         │
│                                                             │
│   注意：每个节点分配一个 /24 子网                            │
│   Node 1: 10.244.1.0/24                                     │
│   Node 2: 10.244.2.0/24                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.3 Calico 详解

Calico 是生产环境最常用的 CNI 之一，支持 BGP 路由和丰富的网络策略。

```bash
# 安装 Calico（使用 Tigera Operator）
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.0/manifests/tigera-operator.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.0/manifests/custom-resources.yaml

# 查看 Calico 组件
kubectl get pods -n calico-system
kubectl get pods -n tigera-operator

# 安装 calicoctl 工具
curl -L https://github.com/projectcalico/calico/releases/latest/download/calicoctl-linux-amd64 -o /usr/local/bin/calicoctl
chmod +x /usr/local/bin/calicoctl

# 查看 Calico 节点
calicoctl get nodes

# 查看 IP 池
calicoctl get ippool -o wide
# NAME                  CIDR             SELECTOR
# default-ipv4-ippool   10.244.0.0/16    all()

# 查看 BGP 配置
calicoctl get bgpconfig default -o yaml

# 查看工作负载端点
calicoctl get workloadendpoints
```

**Calico 网络策略示例：**

```yaml
# 1. 默认拒绝所有入站流量
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default-deny-ingress
spec:
  selector: all()
  types:
    - Ingress

# 2. 允许 web 命名空间访问数据库的 3306 端口
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-web-to-db
  namespace: database
spec:
  selector: app == 'mysql'
  types:
    - Ingress
  ingress:
    - action: Allow
      protocol: TCP
      source:
        namespaceSelector: name == 'web'
        selector: app == 'web'
      destination:
        ports:
          - 3306

# 3. 全局允许 DNS 流量
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: allow-dns
spec:
  selector: all()
  order: 100
  egress:
    - action: Allow
      protocol: UDP
      destination:
        ports:
          - 53
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - 53
  types:
    - Egress
```

**Calico 数据平面模式：**

| 模式 | 原理 | 性能 | 适用场景 |
|------|------|------|----------|
| iptables | 传统 iptables 规则 | 中等 | 兼容性好 |
| eBPF | eBPF 程序直接处理 | 高 | 大规模/高吞吐 |
| VXLAN | 封装通信 | 中等 | 跨子网/云环境 |
| IPIP | IP-in-IP 封装 | 中高 | 跨子网（比 VXLAN 少 20 字节开销） |

#### 5.4 Cilium 详解

Cilium 是基于 eBPF 的新一代网络方案，提供 L3-L7 层的网络策略和强大的可观测性。

```bash
# 安装 Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin

# 安装 Cilium
cilium install --set kubeProxyReplacement=true

# 验证安装
cilium status

# 查看 Cilium 组件
kubectl get pods -n kube-system -l k8s-app=cilium
kubectl get pods -n kube-system -l name=cilium-operator

# 启用 Hubble 可观测性
cilium hubble enable --ui

# 查看流量
cilium hubble observe --namespace default

# 查看网络策略
kubectl get cnp --all-namespaces
```

**Cilium L7 网络策略示例：**

```yaml
# 只允许 web 访问 api 的 GET /api/v1/* 路径
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: api-l7-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: api
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: web
      toPorts:
        - ports:
            - port: "8080"
          rules:
            http:
              - method: GET
                path: "/api/v1/.*"
              - method: POST
                path: "/api/v1/orders"
```

**Cilium eBPF 架构：**

```
┌─────────────────────────────────────────────────────────────┐
│                    Cilium eBPF 数据平面                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────────────────────────────────────────────┐ │
│   │                    用户空间                            │ │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │ │
│   │  │ Cilium      │  │ Cilium      │  │ Hubble      │  │ │
│   │  │ Agent       │  │ Operator    │  │ Observer    │  │ │
│   │  │ (策略编译)  │  │ (IP池管理)  │  │ (流量可视)  │  │ │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  │ │
│   └──────────────────────────────────────────────────────┘ │
│                          │                                  │
│                          ▼                                  │
│   ┌──────────────────────────────────────────────────────┐ │
│   │                    内核空间                            │ │
│   │  ┌─────────────────────────────────────────────────┐ │ │
│   │  │              eBPF 程序                            │ │ │
│   │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐       │ │ │
│   │  │  │ TC Hook  │ │ XDP Hook │ │ Socket   │       │ │ │
│   │  │  │ 策略执行 │ │ 早期丢弃 │ │ 加速     │       │ │ │
│   │  │  │ (ingress/│ │ (DDoS    │ │ (sockops │       │ │ │
│   │  │  │  egress) │ │  防护)   │ │  /msg)   │       │ │ │
│   │  │  └──────────┘ └──────────┘ └──────────┘       │ │ │
│   │  └─────────────────────────────────────────────────┘ │ │
│   │                          │                            │ │
│   │                          ▼                            │ │
│   │  ┌─────────────────────────────────────────────────┐ │ │
│   │  │              eBPF Maps                           │ │ │
│   │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐  │ │ │
│   │  │  │ 策略规则   │ │ 连接跟踪   │ │ 负载均衡   │  │ │ │
│   │  │  │ (per-endpoint)│ (ctmap)    │ │ (svc map)  │  │ │ │
│   │  │  └────────────┘ └────────────┘ └────────────┘  │ │ │
│   │  └─────────────────────────────────────────────────┘ │ │
│   └──────────────────────────────────────────────────────┘ │
│                                                             │
│   优势：                                                     │
│   - 绕过 iptables，直接在内核数据路径中执行策略              │
│   - XDP 在网卡驱动层早期丢弃恶意流量                        │
│   - 连接跟踪和负载均衡在内核态完成，零拷贝                   │
│   - 支持 L7 层策略（HTTP/gRPC/Kafka）                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 6. 网络性能调优

#### 6.1 性能基准测试

```bash
# 1. 启动 iperf3 服务端
docker run -d --name iperf-server -p 5201:5201 networkstatic/iperf3 -s

# 2. 测试 bridge 网络性能
docker run --rm networkstatic/iperf3 -c 172.17.0.2 -t 30 -P 4
# -P 4：使用 4 个并行流

# 3. 测试 host 网络性能（作为基准）
docker run --rm --network host networkstatic/iperf3 -c 127.0.0.1 -t 30 -P 4

# 4. 测试 overlay 网络性能（跨主机）
# 在主机 2 上
docker run --rm networkstatic/iperf3 -c 192.168.1.10 -t 30 -P 4

# 5. 测试 macvlan 网络性能
docker run --rm --network my-macvlan networkstatic/iperf3 -c 192.168.1.101 -t 30 -P 4

# 6. 使用 netperf 进行延迟测试
docker run --rm networkstatic/netperf -H target_ip -t TCP_RR
# TCP_RR：请求-响应延迟测试
# TCP_STREAM：吞吐量测试

# 7. 结果对比记录
# | 网络模式 | 带宽 (Gbps) | 延迟 (us) | CPU 使用率 |
# |----------|-------------|-----------|-----------|
# | host     | 9.5         | 15        | 5%        |
# | bridge   | 8.2         | 45        | 12%       |
# | macvlan  | 9.3         | 18        | 6%        |
# | overlay  | 5.1         | 120       | 25%       |
# | flannel  | 4.8         | 135       | 28%       |
```

#### 6.2 MTU 优化

```bash
# VXLAN 封装增加 50 字节开销，需要相应调小 MTU
# 否则会导致分片，严重影响性能

# 1. 查看物理网络 MTU
ip link show eth0 | grep mtu
# mtu 1500

# 2. 计算各网络类型的 MTU
# 物理网络 MTU 1500:
#   VXLAN:   1500 - 50 = 1450
#   IPIP:    1500 - 20 = 1480
#   WireGuard: 1500 - 60 = 1440

# 3. 设置 Docker 全局 MTU
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "mtu": 1450
}
EOF
sudo systemctl restart docker

# 4. 设置特定网络的 MTU
docker network create \
  --driver overlay \
  --opt com.docker.network.driver.mtu=1450 \
  mtu-optimized

# 5. 验证 MTU 设置（不允许分片）
docker run --rm alpine ping -c 4 -M do -s 1422 8.8.8.8
# 1422 = 1450 - 28（IP + ICMP headers）
# 如果能 ping 通，说明 MTU 正确
```

#### 6.3 内核网络参数调优

```bash
# /etc/sysctl.d/99-docker-network.conf

# 1. 网络缓冲区优化（高吞吐场景）
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.ipv4.tcp_rmem = 4096 1048576 16777216
net.ipv4.tcp_wmem = 4096 1048576 16777216

# 2. TCP 优化
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_no_metrics_save = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15

# 3. 连接队列
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_max_syn_backlog = 65535

# 4. Conntrack 优化（容器环境特别重要）
net.netfilter.nf_conntrack_max = 1048576
net.netfilter.nf_conntrack_buckets = 262144
net.netfilter.nf_conntrack_tcp_timeout_established = 86400
net.netfilter.nf_conntrack_tcp_timeout_close_wait = 3600
net.netfilter.nf_conntrack_tcp_timeout_time_wait = 120

# 5. 端口范围
net.ipv4.ip_local_port_range = 1024 65535

# 应用配置
sudo sysctl -p /etc/sysctl.d/99-docker-network.conf
```

#### 6.4 中断亲和性与 RPS/RFS

```bash
# 网卡中断处理是网络性能的关键瓶颈

# 1. 查看网卡中断
cat /proc/interrupts | grep eth0

# 2. 安装 irqbalance（自动均衡中断到 CPU）
sudo apt-get install irqbalance
sudo systemctl enable --now irqbalance

# 3. 启用 RPS（Receive Packet Steering）
# 将接收队列的软中断分散到多个 CPU
echo "f" > /sys/class/net/eth0/queues/rx-0/rps_cpus
# "f" = 0x0f = CPU 0-3 参与处理

# 4. 启用 RFS（Receive Flow Steering）
echo 32768 > /sys/class/net/eth0/queues/rx-0/rps_flow_cnt
echo 32768 > /proc/sys/net/core/rps_sock_flow_entries

# 5. 启用 XPS（Transmit Packet Steering）
echo "f" > /sys/class/net/eth0/queues/tx-0/xps_cpus

# 6. 持久化配置
cat > /etc/udev/rules.d/99-network-optimize.rules << 'EOF'
ACTION=="add", SUBSYSTEM=="net", NAME=="eth0", RUN+="/bin/sh -c 'echo f > /sys/class/net/eth0/queues/rx-0/rps_cpus && echo f > /sys/class/net/eth0/queues/tx-0/xps_cpus'"
EOF
```

---

### 7. 网络故障排查工具箱

#### 7.1 系统化排查流程

```
┌─────────────────────────────────────────────────────────────┐
│              容器网络故障排查流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. 检查容器网络配置                                        │
│      docker inspect --format='{{json .NetworkSettings}}'     │
│      │                                                      │
│      ▼                                                      │
│   2. 检查网络命名空间                                        │
│      nsenter -t <PID> -n ip addr / ip route / ss            │
│      │                                                      │
│      ▼                                                      │
│   3. 检查连通性                                             │
│      ping / traceroute / curl                               │
│      │                                                      │
│      ▼                                                      │
│   4. 检查 DNS                                               │
│      nslookup / dig / cat /etc/resolv.conf                  │
│      │                                                      │
│      ▼                                                      │
│   5. 检查端口                                               │
│      ss -tlnp / netstat -tlnp                              │
│      │                                                      │
│      ▼                                                      │
│   6. 检查防火墙                                             │
│      iptables -L -n -v / iptables -t nat -L -n -v          │
│      │                                                      │
│      ▼                                                      │
│   7. 抓包分析                                               │
│      tcpdump / wireshark                                    │
│      │                                                      │
│      ▼                                                      │
│   8. 检查日志                                               │
│      journalctl -u docker / dmesg                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 7.2 常用排查命令详解

```bash
# === 1. 检查容器网络配置 ===
docker inspect --format='{{json .NetworkSettings.Networks}}' container_name | jq
docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' container_name

# === 2. 进入容器网络命名空间 ===
# 获取容器 PID
PID=$(docker inspect --format='{{.State.Pid}}' container_name)
# 进入网络命名空间
sudo nsenter -t $PID -n ip addr show
sudo nsenter -t $PID -n ip route show
sudo nsenter -t $PID -n ss -tlnp
sudo nsenter -t $PID -n cat /etc/resolv.conf

# === 3. 连通性测试 ===
docker exec container_name ping -c 3 target_ip
docker exec container_name traceroute target_ip
docker exec container_name curl -v http://target:port
docker exec container_name wget -O /dev/null http://target:port

# === 4. DNS 测试 ===
docker exec container_name nslookup service_name
docker exec container_name dig service_name +short
docker exec container_name cat /etc/resolv.conf

# === 5. 端口检查 ===
docker exec container_name ss -tlnp
docker exec container_name netstat -tlnp
# 从宿主机检查容器端口
ss -tlnp | grep :8080

# === 6. 防火墙规则 ===
sudo iptables -L DOCKER-USER -n -v --line-numbers
sudo iptables -L DOCKER-FORWARD -n -v
sudo iptables -t nat -L DOCKER -n -v

# === 7. 抓包分析 ===
# 在宿主机上抓 docker0 流量
sudo tcpdump -i docker0 -nn host 172.17.0.2

# 在容器内抓包（使用 netshoot 工具）
docker run --rm -it --network container:target_container \
  nicolaka/netshoot tcpdump -i eth0 -nn

# VXLAN 流量抓包
sudo tcpdump -i eth0 port 4789 -nn

# === 8. 流量监控 ===
docker stats --format "table {{.Name}}\t{{.NetIO}}"
# 实时查看网络流量
sudo iftop -i docker0
```

#### 7.3 常见问题与解决方案

```bash
# ============ 问题 1：容器无法访问外部网络 ============
# 原因：IP 转发未启用
sysctl net.ipv4.ip_forward
# 应该返回 1

# 修复
sudo sysctl -w net.ipv4.ip_forward=1
echo "net.ipv4.ip_forward = 1" | sudo tee -a /etc/sysctl.conf

# 检查 NAT 规则
sudo iptables -t nat -L POSTROUTING -n -v
# 确保有 MASQUERADE 规则

# ============ 问题 2：容器间无法通信 ============
# 原因 1：不同 Docker 网络
docker network ls
docker inspect --format='{{json .NetworkSettings.Networks}}' container1
docker inspect --format='{{json .NetworkSettings.Networks}}' container2
# 如果在不同网络，使用 docker network connect

# 原因 2：icc=false（容器间通信被禁用）
docker network inspect bridge | grep ICC

# 原因 3：iptables 规则阻止
sudo iptables -L DOCKER-USER -n -v

# ============ 问题 3：端口映射不生效 ============
# 检查端口映射
docker port container_name

# 检查 DNAT 规则
sudo iptables -t nat -L DOCKER -n -v

# 检查容器内服务是否监听正确端口
docker exec container_name ss -tlnp

# 检查防火墙是否阻止
sudo iptables -L INPUT -n -v
sudo ufw status

# ============ 问题 4：DNS 解析失败 ============
# 检查 resolv.conf
docker exec container_name cat /etc/resolv.conf

# 测试 DNS
docker exec container_name nslookup google.com

# 修改 Docker DNS
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
EOF
sudo systemctl restart docker

# ============ 问题 5：跨主机 Overlay 网络不通 ============
# 检查 VXLAN 端口（UDP 4789）
sudo ss -unlp | grep 4789

# 检查防火墙
sudo iptables -A INPUT -p udp --dport 4789 -j ACCEPT

# 检查 VXLAN 接口
ip link show type vxlan

# 抓包分析
sudo tcpdump -i eth0 port 4789 -nn
```

#### 7.4 网络监控脚本

```bash
#!/bin/bash
# docker-network-monitor.sh - Docker 网络状态监控

echo "==================== Docker 网络监控 ===================="
echo ""

echo "--- 1. 网络列表 ---"
docker network ls --format "table {{.Name}}\t{{.Driver}}\t{{.Scope}}\t{{.Internal}}"

echo ""
echo "--- 2. 容器网络状态 ---"
printf "%-25s %-20s %-18s %-15s\n" "CONTAINER" "NETWORK" "IP" "GATEWAY"
for container in $(docker ps -q 2>/dev/null); do
    name=$(docker inspect --format='{{.Name}}' $container | sed 's/\///')
    for net in $(docker inspect --format='{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' $container); do
        ip=$(docker inspect --format="{{(index .NetworkSettings.Networks \"$net\").IPAddress}}" $container)
        gw=$(docker inspect --format="{{(index .NetworkSettings.Networks \"$net\").Gateway}}" $container)
        printf "%-25s %-20s %-18s %-15s\n" "$name" "$net" "$ip" "$gw"
    done
done

echo ""
echo "--- 3. 网络流量统计 ---"
docker stats --no-stream --format "table {{.Name}}\t{{.NetIO}}" 2>/dev/null

echo ""
echo "--- 4. 端口映射 ---"
docker ps --format "table {{.Names}}\t{{.Ports}}" 2>/dev/null

echo ""
echo "--- 5. Conntrack 统计 ---"
if [ -f /proc/sys/net/netfilter/nf_conntrack_count ]; then
    count=$(cat /proc/sys/net/netfilter/nf_conntrack_count)
    max=$(cat /proc/sys/net/netfilter/nf_conntrack_max)
    pct=$((count * 100 / max))
    echo "当前连接: $count / $max ($pct%)"
    if [ $pct -gt 80 ]; then
        echo "[WARNING] Conntrack 使用率超过 80%!"
    fi
else
    echo "conntrack 模块未加载"
fi

echo ""
echo "--- 6. 网络接口错误统计 ---"
for iface in docker0 eth0; do
    if [ -d /sys/class/net/$iface ]; then
        rx_errors=$(cat /sys/class/net/$iface/statistics/rx_errors)
        tx_errors=$(cat /sys/class/net/$iface/statistics/tx_errors)
        rx_dropped=$(cat /sys/class/net/$iface/statistics/rx_dropped)
        tx_dropped=$(cat /sys/class/net/$iface/statistics/tx_dropped)
        echo "$iface: rx_errors=$rx_errors tx_errors=$tx_errors rx_dropped=$rx_dropped tx_dropped=$tx_dropped"
    fi
done
```

---

## 💻 实战练习

### 练习 1：配置 macvlan 网络

**目标：** 创建 macvlan 网络，使容器直接出现在物理网络中并可从外部访问。

```bash
# 1. 创建 macvlan 网络
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 \
  macvlan-net

# 2. 运行两个 nginx 容器
docker run -d --name web1 \
  --network macvlan-net \
  --ip 192.168.1.201 \
  nginx:alpine

docker run -d --name web2 \
  --network macvlan-net \
  --ip 192.168.1.202 \
  nginx:alpine

# 3. 验证容器 IP 和网络
docker exec web1 ip addr show eth0
docker exec web1 ip route show

# 4. 从其他主机测试访问
# 在另一台机器上
curl http://192.168.1.201
curl http://192.168.1.202

# 5. 解决宿主机与容器通信问题
sudo ip link add macvlan-shim link eth0 type macvlan mode bridge
sudo ip addr add 192.168.1.250/32 dev macvlan-shim
sudo ip link set macvlan-shim up
sudo ip route add 192.168.1.201/32 dev macvlan-shim
sudo ip route add 192.168.1.202/32 dev macvlan-shim

# 6. 验证宿主机到容器通信
ping -c 3 192.168.1.201
curl http://192.168.1.201

# 7. 验证容器间通信
docker exec web1 ping -c 3 192.168.1.202
```

### 练习 2：iptables 网络安全策略

**目标：** 使用 DOCKER-USER 链实现容器网络访问控制。

```bash
# 1. 启动测试容器
docker run -d --name app1 -p 8081:80 nginx:alpine
docker run -d --name app2 -p 8082:80 nginx:alpine
docker run -d --name db -e MYSQL_ROOT_PASSWORD=secret mysql:8.0

# 记录容器 IP
APP1_IP=$(docker inspect --format='{{.NetworkSettings.Networks.bridge.IPAddress}}' app1)
APP2_IP=$(docker inspect --format='{{.NetworkSettings.Networks.bridge.IPAddress}}' app2)
DB_IP=$(docker inspect --format='{{.NetworkSettings.Networks.bridge.IPAddress}}' db)
echo "app1=$APP1_IP app2=$APP2_IP db=$DB_IP"

# 2. 只允许 app1 访问数据库
sudo iptables -I DOCKER-USER -s $APP1_IP -d $DB_IP -p tcp --dport 3306 -j ACCEPT
sudo iptables -I DOCKER-USER -d $DB_IP -p tcp --dport 3306 -j DROP

# 3. 验证
# app1 应该能连接数据库
docker exec app1 sh -c "echo 'quit' | nc -w 3 $DB_IP 3306" && echo "app1: OK" || echo "app1: BLOCKED"

# app2 应该无法连接数据库
docker exec app2 sh -c "echo 'quit' | nc -w 3 $DB_IP 3306" && echo "app2: OK" || echo "app2: BLOCKED"

# 4. 限制外部只能访问 8081，不能访问 8082
sudo iptables -I DOCKER-USER -i eth0 -p tcp --dport 8082 -j DROP

# 5. 验证
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081  # 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8082  # 超时/拒绝

# 6. 查看规则
sudo iptables -L DOCKER-USER -n -v --line-numbers

# 7. 清理
sudo iptables -D DOCKER-USER -s $APP1_IP -d $DB_IP -p tcp --dport 3306 -j ACCEPT
sudo iptables -D DOCKER-USER -d $DB_IP -p tcp --dport 3306 -j DROP
sudo iptables -D DOCKER-USER -i eth0 -p tcp --dport 8082 -j DROP
docker rm -f app1 app2 db
```

### 练习 3：网络性能基准测试

**目标：** 对比不同网络模式的性能差异。

```bash
# 1. 启动 iperf3 服务端
docker run -d --name iperf-server -p 5201:5201 networkstatic/iperf3 -s

# 2. 测试 bridge 网络
echo "=== Bridge Network ==="
docker run --rm networkstatic/iperf3 -c $(docker inspect --format='{{.NetworkSettings.Networks.bridge.IPAddress}}' iperf-server) -t 10 -P 4

# 3. 测试 host 网络
echo "=== Host Network ==="
docker run --rm --network host networkstatic/iperf3 -c 127.0.0.1 -t 10 -P 4

# 4. 创建 macvlan 网络并测试
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  -o parent=eth0 \
  perf-macvlan

docker run -d --name iperf-macvlan \
  --network perf-macvlan \
  --ip 192.168.1.220 \
  networkstatic/iperf3 -s

echo "=== Macvlan Network ==="
# 需要从另一台主机测试，或使用 macvlan-shim
docker run --rm --network perf-macvlan networkstatic/iperf3 -c 192.168.1.220 -t 10 -P 4

# 5. 测试 MTU 影响
echo "=== MTU Test ==="
docker network create --opt com.docker.network.driver.mtu=1450 mtu-test-net
docker run -d --name iperf-mtu --network mtu-test-net networkstatic/iperf3 -s
docker run --rm --network mtu-test-net networkstatic/iperf3 -c $(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' iperf-mtu) -t 10

# 6. 延迟测试
echo "=== Latency Test (TCP_RR) ==="
docker run --rm networkstatic/netperf -H $(docker inspect --format='{{.NetworkSettings.Networks.bridge.IPAddress}}' iperf-server) -t TCP_RR

# 7. 清理
docker stop iperf-server iperf-macvlan iperf-mtu
docker rm iperf-server iperf-macvlan iperf-mtu
docker network rm perf-macvlan mtu-test-net

# 8. 记录结果
echo "=== Performance Summary ==="
# | Mode     | Bandwidth (Gbps) | Latency (us) |
# |----------|-----------------|--------------|
# | bridge   | ?               | ?            |
# | host     | ?               | ?            |
# | macvlan  | ?               | ?            |
```

---

## 🎯 面试题精选

### 1. Docker bridge 网络是如何实现的？

**参考答案：**

Docker bridge 网络基于 Linux 网桥（bridge）、veth pair 和 iptables 实现：

1. **docker0 网桥**：Docker 启动时自动创建的 Linux 网桥设备，默认子网 172.17.0.0/16
2. **veth pair**：每个容器创建一对虚拟以太网设备，一端在容器内（eth0），另一端连接到 docker0 网桥
3. **iptables NAT**：容器出站流量通过 MASQUERADE 转换为宿主机 IP
4. **iptables DNAT**：端口映射将宿主机端口转发到容器端口
5. **DOCKER-ISOLATION 链**：不同 bridge 网络之间的流量隔离

### 2. macvlan 和 ipvlan 有什么区别？

**参考答案：**

| 特性 | macvlan | ipvlan |
|------|---------|--------|
| MAC 地址 | 每个容器独立 MAC | 共享父接口 MAC |
| 交换机要求 | 需要混杂模式支持 | 不需要混杂模式 |
| 云环境兼容 | 可能受 MAC 限制 | 兼容性好 |
| 工作模式 | bridge/vepa/private/passthru | L2/L3/L3S |
| 性能 | 接近原生 | 接近原生 |

选择建议：云环境或大量容器场景用 ipvlan，传统数据中心用 macvlan。

### 3. VXLAN 的作用是什么？Docker 在哪里使用它？

**参考答案：**

VXLAN 通过在 UDP 数据包中封装二层帧实现跨三层网络的二层通信。核心参数 VNI（24 位）支持 16M 个虚拟网络。

Docker 使用 VXLAN 的场景：
- **Overlay 网络**：Swarm 訡式下跨主机容器通信
- **Flannel VXLAN 后端**：Kubernetes Pod 跨节点通信

封装开销 50 字节，需将 MTU 设置为 1450（假设物理 MTU 1500）避免分片。

### 4. 如何在 DOCKER-USER 链中实现网络安全策略？

**参考答案：**

```bash
# 只允许特定 IP 访问容器
sudo iptables -I DOCKER-USER -i eth0 -p tcp --dport 80 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -I DOCKER-USER -i eth0 -p tcp --dport 80 -j DROP

# 只允许特定容器访问数据库
sudo iptables -I DOCKER-USER -s 172.17.0.2 -d 172.17.0.3 -p tcp --dport 3306 -j ACCEPT
sudo iptables -I DOCKER-USER -d 172.17.0.3 -p tcp --dport 3306 -j DROP

# 限制出站速率
sudo iptables -I DOCKER-USER -i docker0 -o eth0 -m conntrack --ctstate NEW \
  -m limit --limit 100/min --limit-burst 50 -j ACCEPT
sudo iptables -I DOCKER-USER -i docker0 -o eth0 -m conntrack --ctstate NEW -j DROP
```

### 5. Calico、Flannel 和 Cilium 的核心区别是什么？

**参考答案：**

| 维度 | Flannel | Calico | Cilium |
|------|---------|--------|--------|
| 数据平面 | VXLAN/host-gw | iptables/eBPF | 纯 eBPF |
| 网络策略 | 不支持 | 支持 L3/L4 | 支持 L3-L7 |
| 性能 | 中等 | 高 | 极高 |
| 运维复杂度 | 低 | 中 | 高 |

选择建议：
- 学习/小型环境：Flannel
- 生产通用场景：Calico
- 高性能/深度可观测/服务网格：Cilium

### 6. 如何排查容器 DNS 解析失败？

**参考答案：**

排查步骤：
1. 检查 resolv.conf：`docker exec app cat /etc/resolv.conf`
2. 检查 Docker daemon DNS 配置：`/etc/docker/daemon.json`
3. 测试 DNS 解析：`docker exec app nslookup kubernetes.default`
4. 检查 kube-dns/coredns Pod 状态（K8s 环境）
5. 检查容器到 DNS 服务的网络连通性
6. 抓包分析 DNS 请求：`tcpdump -i any port 53`

常见原因：resolv.conf 配置错误、DNS 服务不可用、网络策略阻止 DNS 端口、conntrack 表满导致丢包。

### 7. 什么是 VXLAN 的 MTU 问题？如何解决？

**参考答案：**

VXLAN 封装增加 50 字节开销（14 以太网头 + 20 IP 头 + 8 UDP 头 + 8 VXLAN 头）。如果物理网络 MTU 为 1500，而 VXLAN 网络也设置 MTU 1500，数据包会因超大被分片，导致性能严重下降和丢包。

解决方法：
```bash
# 设置 VXLAN 网络 MTU = 物理 MTU - 50
docker network create --opt com.docker.network.driver.mtu=1450 overlay-net

# 全局设置
sudo tee /etc/docker/daemon.json << 'EOF'
{"mtu": 1450}
EOF
```

### 8. 如何优化容器环境的 conntrack 性能？

**参考答案：**

容器环境因大量短连接容易耗尽 conntrack 表。优化方法：

```bash
# 增大 conntrack 表
sysctl -w net.netfilter.nf_conntrack_max=1048576
sysctl -w net.netfilter.nf_conntrack_buckets=262144

# 缩短超时时间
sysctl -w net.netfilter.nf_conntrack_tcp_timeout_time_wait=30
sysctl -w net.netfilter.nf_conntrack_tcp_timeout_close_wait=30
sysctl -w net.netfilter.nf_conntrack_tcp_timeout_fin_wait=30

# 监控使用情况
conntrack -C  # 当前连接数
cat /proc/sys/net/netfilter/nf_conntrack_count
```

### 9. Docker 网络的 ICC 是什么？

**参考答案：**

ICC（Inter-Container Communication）控制同一 bridge 网络内容器之间的通信。

- `icc=true`（默认）：同一网络的容器可以互相通信
- `icc=false`：同一网络的容器无法直接通信，必须通过端口映射

禁用 ICC 的影响：
```json
// /etc/docker/daemon.json
{"icc": false}
```

设置 `icc=false` 后，容器间通信需要通过 `--link`（已废弃）或共享网络、端口映射等方式。这是增强安全性的措施，但会影响微服务架构中的服务发现。

### 10. 如何监控 Docker 网络流量？

**参考答案：**

```bash
# 1. docker stats 查看网络 I/O
docker stats --format "table {{.Name}}\t{{.NetIO}}"

# 2. 宿主机 iftop 实时监控
sudo iftop -i docker0

# 3. 抓包分析
sudo tcpdump -i docker0 -nn -w capture.pcap

# 4. 进入容器网络命名空间
PID=$(docker inspect --format='{{.State.Pid}}' app)
sudo nsenter -t $PID -n ss -s  # socket 统计

# 5. cAdvisor + Prometheus + Grafana（见 Day 88）
# 6. iptables 规则匹配计数
sudo iptables -L DOCKER-USER -n -v -x
```

---

## 📚 深入阅读

### 官方文档
- [Docker Networking Overview](https://docs.docker.com/network/)
- [Docker Overlay Networking](https://docs.docker.com/network/overlay/)
- [Flannel Documentation](https://github.com/flannel-io/flannel)
- [Calico Documentation](https://docs.tigera.io/calico/latest/about/)
- [Cilium Documentation](https://docs.cilium.io/)
- [Container Network Interface (CNI) Specification](https://github.com/containernetworking/cni/blob/main/SPEC.md)

### 技术文章
- [Understanding Docker Network Architecture](https://docs.docker.com/network/network-tutorial-standalone/)
- [VXLAN: Virtual Extensible LAN](https://datatracker.ietf.org/doc/html/rfc7348)
- [Cilium eBPF Datapath](https://docs.cilium.io/en/stable/architecture/)
- [Calico Data Path Performance](https://www.tigera.io/blog/calico-everything-you-wanted-to-know/)

### 工具资源
- [netshoot](https://github.com/nicolaka/netshoot) - 网络调试工具集
- [iperf3](https://github.com/esnet/iperf) - 网络性能测试
- [tcpdump](https://www.tcpdump.org/) - 网络抓包

---

## ✅ 自检清单

### 网络基础
- [ ] 理解 Docker bridge 网络的 iptables 规则结构
- [ ] 能够在 DOCKER-USER 链中添加自定义安全规则
- [ ] 理解 DOCKER-ISOLATION 链的隔离机制

### 高级网络
- [ ] 理解 VXLAN 封装原理和 MTU 调整
- [ ] 能够配置 macvlan 网络并解决宿主机通信问题
- [ ] 了解 ipvlan L2/L3/L3S 模式的区别和适用场景

### 容器网络方案
- [ ] 理解 Flannel 的 VXLAN/host-gw 后端区别
- [ ] 了解 Calico 的网络策略配置
- [ ] 了解 Cilium eBPF 架构的优势

### 性能优化
- [ ] 能够使用 iperf3 进行网络性能基准测试
- [ ] 掌握 MTU 优化方法
- [ ] 了解内核网络参数调优（缓冲区、conntrack、RPS/RFS）

### 故障排查
- [ ] 掌握容器网络排查的系统化流程
- [ ] 能够进入容器网络命名空间排查问题
- [ ] 能够使用 tcpdump 进行网络抓包分析
- [ ] 掌握常见网络问题的解决方案

---

**下一阶段：** Day 88 将学习 Docker 监控与日志管理，包括 cAdvisor、Prometheus 容器监控和日志驱动配置。
