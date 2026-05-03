# Day 81: Docker 网络管理

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 网络管理
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 76 (Docker 简介与安装), Day 79 (Docker 容器管理), Day 29 (OSI 七层模型)

## 🎯 学习目标

- 深入理解 Docker 五种网络驱动（bridge/host/none/overlay/macvlan）的原理与适用场景
- 掌握自定义 bridge 网络的创建、管理与 DNS 解析机制
- 能配置端口映射并理解 iptables 底层规则
- 掌握容器互联与网络隔离策略
- 能排查生产环境中常见的 Docker 网络故障

---

## 📖 核心知识点

### 1. Docker 网络架构总览

Docker 网络基于 Linux 内核的 Network Namespace、veth pair、iptables/netfilter 等技术构建。每个容器拥有独立的网络栈，Docker 通过网络驱动控制容器之间以及容器与外部网络的通信。

```
┌─────────────────────────────────────────────────────────┐
│                     宿主机 (Host)                        │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │  Container A  │    │  Container B  │                  │
│  │  172.17.0.2   │    │  172.17.0.3   │                 │
│  │  eth0         │    │  eth0         │                  │
│  └──────┬───────┘    └──────┬───────┘                   │
│         │ veth pair          │ veth pair                 │
│  ┌──────┴───────┐    ┌──────┴───────┐                   │
│  │  vethXXXX    │    │  vethYYYY    │                    │
│  └──────┬───────┘    └──────┬───────┘                   │
│         │                    │                           │
│  ┌──────┴────────────────────┴───────┐                  │
│  │         docker0 (Bridge)          │                  │
│  │         172.17.0.1/16             │                  │
│  └──────────────┬────────────────────┘                  │
│                 │                                        │
│           ┌─────┴─────┐                                 │
│           │  iptables  │                                 │
│           │  NAT/MASQ  │                                 │
│           └─────┬─────┘                                 │
│                 │                                        │
│           ┌─────┴─────┐                                 │
│           │    eth0    │  (宿主机物理/虚拟网卡)           │
│           └───────────┘                                 │
└─────────────────────────────────────────────────────────┘
```

#### 核心技术栈

| 技术 | 作用 | Docker 中的应用 |
|------|------|-----------------|
| Network Namespace | 网络隔离 | 每个容器独立的网络栈 |
| veth pair | 虚拟以太网对 | 连接容器与网桥 |
| Linux Bridge | 二层交换 | docker0 默认网桥 |
| iptables/NAT | 地址转换与过滤 | 端口映射、出站 MASQUERADE |
| VXLAN | 隧道封装 | overlay 跨主机网络 |
| macvlan | MAC 地址虚拟化 | 容器直连物理网络 |

---

### 2. Bridge 网络详解

Bridge 是 Docker 的默认网络驱动。容器通过 veth pair 连接到 Linux Bridge，实现二层互通。

#### 2.1 默认 bridge vs 自定义 bridge

```
默认 bridge 网络:
┌─────────────────────────────────────────┐
│           docker0 (172.17.0.1/16)       │
│                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │  web    │  │   db    │  │  redis  │ │
│  │ 172.17  │  │ 172.17  │  │ 172.17  │ │
│  │  .0.2   │  │  .0.3   │  │  .0.4   │ │
│  └─────────┘  └─────────┘  └─────────┘ │
│                                         │
│  特点:                                   │
│  - 容器间可通信（通过 IP）                │
│  - 不支持 DNS 名称解析                   │
│  - 所有容器共享同一网络                   │
│  - 无网络隔离                            │
└─────────────────────────────────────────┘

自定义 bridge 网络:
┌─────────────────────┐  ┌─────────────────────┐
│  app-net            │  │  db-net             │
│  (172.20.0.0/16)    │  │  (172.21.0.0/16)    │
│                     │  │                     │
│  ┌─────┐ ┌──────┐  │  │  ┌─────┐ ┌──────┐  │
│  │web  │ │nginx │  │  │  │ db  │ │redis │  │
│  │.0.2 │ │.0.3  │  │  │  │.0.2 │ │.0.3  │  │
│  └─────┘ └──────┘  │  │  └─────┘ └──────┘  │
│                     │  │                     │
│  内置 DNS 服务器     │  │  内置 DNS 服务器     │
│  容器名→IP 解析     │  │  容器名→IP 解析     │
└─────────────────────┘  └─────────────────────┘
```

**关键区别:**

| 特性 | 默认 bridge | 自定义 bridge |
|------|------------|--------------|
| DNS 解析 | 不支持（需用 --link） | 内置 DNS 服务器 |
| 网络隔离 | 所有容器共享 | 按网络隔离 |
| 自动连接 | 新容器自动加入 | 需显式指定 |
| 配置灵活性 | 有限 | 支持子网、网关等 |
| 推荐程度 | 仅用于测试 | 生产环境推荐 |

#### 2.2 自定义 bridge 网络操作

```bash
# 创建自定义 bridge 网络
docker network create app-net

# 指定子网和网关
docker network create \
  --driver bridge \
  --subnet 172.20.0.0/16 \
  --gateway 172.20.0.1 \
  --ip-range 172.20.1.0/24 \
  --opt com.docker.network.bridge.name=br-app \
  --opt com.docker.network.bridge.enable_ip_masquerade=true \
  --opt com.docker.network.bridge.enable_icc=true \
  app-net

# 查看网络详情
docker network inspect app-net

# 将运行中的容器加入网络
docker network connect app-net my-container

# 将容器加入网络并指定 IP
docker network connect --ip 172.20.1.100 app-net my-container

# 断开网络
docker network disconnect app-net my-container

# 删除网络
docker network rm app-net

# 清理未使用的网络
docker network prune
```

#### 2.3 Bridge 网络底层机制

```bash
# 查看 Linux Bridge
brctl show
# 或
ip link show type bridge

# 查看 veth pair
ip link show type veth

# 查看容器的网络命名空间
ls /var/run/docker/netns/

# 进入容器的网络命名空间调试
pid=$(docker inspect -f '{{.State.Pid}}' my-container)
nsenter -t $pid -n ip addr show
nsenter -t $pid -n ip route show
nsenter -t $pid -n ss -tlnp

# 查看 iptables NAT 规则
iptables -t nat -L -n -v
iptables -L DOCKER -n -v
```

#### 2.4 Bridge 网络内部工作流程

```
容器 A (172.20.0.2) ping 容器 B (172.20.0.3):

1. 容器 A 的 ARP 请求:
   Container A → veth pair → docker0/br-app → veth pair → Container B

2. 数据包路径:
   Container A eth0
     → veth pair (vethA)
       → Bridge (br-app/docker0)
         → MAC 地址表查找
           → veth pair (vethB)
             → Container B eth0

3. 跨网络通信:
   Container A (app-net) → app-net bridge
     → iptables FORWARD chain
       → 拒绝 (不同 bridge 网络默认隔离)
```

---

### 3. Host 网络

Host 模式下容器与宿主机共享网络命名空间，容器直接使用宿主机的 IP 地址和端口。

```
Host 网络模式:

┌──────────────────────────────────────┐
│           宿主机网络栈                 │
│           eth0: 10.0.1.100           │
│                                      │
│  ┌──────────────┐ ┌──────────────┐  │
│  │ Container A   │ │ Container B   │ │
│  │ (无独立网络栈) │ │ (无独立网络栈) │ │
│  │ 直接使用       │ │ 直接使用       │ │
│  │ 10.0.1.100    │ │ 10.0.1.100    │ │
│  └──────────────┘ └──────────────┘  │
│                                      │
│  注意: 容器 A 和 B 不能使用相同端口    │
└──────────────────────────────────────┘
```

```bash
# 使用 host 网络
docker run -d --network host --name nginx-host nginx

# 验证: 容器直接监听宿主机端口
ss -tlnp | grep :80

# 优势: 性能最优，无 NAT 开销
# 劣势: 无网络隔离，端口冲突风险

# 适用场景:
# - 高性能网络应用（如负载均衡器）
# - 需要监听多个端口的服务
# - 对网络延迟敏感的应用
```

**Host 网络性能对比:**

| 指标 | bridge (NAT) | host |
|------|-------------|------|
| 网络延迟 | +0.1-0.5ms | 基准 |
| 吞吐量 | 约 90-95% | 100% |
| 端口管理 | 灵活映射 | 需协调 |
| 隔离性 | 好 | 无 |

---

### 4. None 网络

None 模式下容器没有外部网络连接，只有 loopback 接口。

```bash
# 创建无网络容器
docker run -d --network none --name isolated alpine sleep 3600

# 验证: 只有 lo 接口
docker exec isolated ip addr show
# 1: lo: <LOOPBACK,UP,LOWER_UP>
#     inet 127.0.0.1/8 scope host lo
# (无 eth0)

# 适用场景:
# - 安全敏感的计算任务
# - 仅需本地处理的批处理作业
# - 密码/密钥生成容器
# - 作为自定义网络的基础
```

---

### 5. Overlay 网络

Overlay 网络用于跨主机容器通信，基于 VXLAN 隧道封装技术。

#### 5.1 Overlay 网络架构

```
                    Overlay 网络 (VXLAN)
                    10.0.0.0/24

  Host A (10.0.1.10)            Host B (10.0.1.11)
  ┌────────────────────┐       ┌────────────────────┐
  │                    │       │                    │
  │  ┌──────────┐      │       │  ┌──────────┐      │
  │  │Container │      │       │  │Container │      │
  │  │10.0.0.2  │      │       │  │10.0.0.3  │      │
  │  └────┬─────┘      │       │  └────┬─────┘      │
  │       │            │       │       │            │
  │  ┌────┴─────┐      │       │  ┌────┴─────┐      │
  │  │ overlay  │      │       │  │ overlay  │      │
  │  │ endpoint │      │       │  │ endpoint │      │
  │  └────┬─────┘      │       │  └────┬─────┘      │
  │       │            │       │       │            │
  │  ┌────┴─────┐      │       │  ┌────┴─────┐      │
  │  │  VXLAN   │      │       │  │  VXLAN   │      │
  │  │  Tunnel  │      │       │  │  Tunnel  │      │
  │  └────┬─────┘      │       │  └────┬─────┘      │
  │       │            │       │       │            │
  │  ┌────┴─────┐      │       │  ┌────┴─────┐      │
  │  │  eth0    │──────┼───────┼──│  eth0    │      │
  │  │10.0.1.10 │      │       │  │10.0.1.11 │      │
  │  └──────────┘      │       │  └──────────┘      │
  └────────────────────┘       └────────────────────┘

  VXLAN 封装:
  ┌──────────┬──────────┬──────────┬──────────┐
  │ 外层 IP  │ 外层 UDP │ VXLAN    │ 原始     │
  │ Header   │ Header   │ Header   │ 以太帧   │
  │ (物理IP) │ (4789)   │ (VNI)    │ (容器IP) │
  └──────────┴──────────┴──────────┴──────────┘
```

#### 5.2 Overlay 网络操作

```bash
# 初始化 Swarm（Overlay 需要 Swarm 模式）
docker swarm init --advertise-addr 10.0.1.10

# 在其他节点加入 Swarm
docker swarm join --token <token> 10.0.1.10:2377

# 创建 Overlay 网络
docker network create \
  --driver overlay \
  --subnet 10.10.0.0/24 \
  --gateway 10.10.0.1 \
  --attachable \
  my-overlay

# 创建加密的 Overlay 网络
docker network create \
  --driver overlay \
  --opt encrypted \
  secure-overlay

# 部署服务到 Overlay 网络
docker service create \
  --name web \
  --network my-overlay \
  --replicas 3 \
  nginx

# 跨主机通信验证
# 在 Host A 上
docker exec web.1.<id> ping web.2.<id>  # 可能跨主机
```

#### 5.3 Overlay 网络与 Swarm 服务

```bash
# 创建 overlay 网络用于服务
docker network create -d overlay --attachable app-overlay

# 在 Host A 上运行独立容器
docker run -d --network app-overlay --name api api-server

# 在 Host B 上运行独立容器
docker run -d --network app-overlay --name web web-server

# 跨主机容器通过名称互通
docker exec web ping api  # 成功，通过 VXLAN 隧道

# 查看 VXLAN 端口
ss -ulnp | grep 4789
```

---

### 6. Macvlan 网络

Macvlan 允许容器拥有独立的 MAC 地址，直接接入物理网络。

#### 6.1 Macvlan 网络架构

```
Macvlan 网络模式:

物理交换机
    │
    ├── eth0 (宿主机物理接口)
    │     MAC: AA:BB:CC:DD:EE:01
    │     IP:  10.0.1.10
    │
    ├── eth0.10@eth0 (macvlan 子接口)
    │     ┌──────────────────────┐
    │     │ Container A          │
    │     │ MAC: AA:BB:CC:DD:EE:02│
    │     │ IP: 10.0.1.20        │
    │     └──────────────────────┘
    │
    └── eth0.10@eth0 (macvlan 子接口)
          ┌──────────────────────┐
          │ Container B          │
          │ MAC: AA:BB:CC:DD:EE:03│
          │ IP: 10.0.1.21        │
          └──────────────────────┘

注意: 宿主机与 macvlan 容器默认不能直接通信
解决方案: 创建 macvlan 子接口用于宿主机通信
```

#### 6.2 Macvlan 网络操作

```bash
# 创建 macvlan 网络
docker network create \
  --driver macvlan \
  --subnet 10.0.1.0/24 \
  --gateway 10.0.1.1 \
  -o parent=eth0 \
  my-macvlan

# 创建 macvlan 并指定 IP 范围
docker network create \
  --driver macvlan \
  --subnet 10.0.1.0/24 \
  --gateway 10.0.1.1 \
  --ip-range 10.0.1.200/25 \
  -o parent=eth0 \
  macvlan-net

# 运行容器使用 macvlan
docker run -d --network my-macvlan --name web1 nginx
docker run -d --network my-macvlan --name web2 nginx

# 验证容器有独立 MAC 和 IP
docker exec web1 ip addr show eth0

# 解决宿主机与 macvlan 容器通信问题
# 在宿主机上创建 macvlan 子接口
ip link add mac0 link eth0 type macvlan mode bridge
ip addr add 10.0.1.250/32 dev mac0
ip link set mac0 up
ip route add 10.0.1.200/25 dev mac0
```

#### 6.3 Macvlan 的两种模式

| 模式 | 说明 | 隔离性 |
|------|------|--------|
| bridge | 同一父接口下的容器互通 | 容器间互通 |
| 802.1q trunk | 基于 VLAN ID 隔离 | 按 VLAN 隔离 |

```bash
# 802.1q trunk 模式
docker network create \
  --driver macvlan \
  --subnet 10.0.10.0/24 \
  -o parent=eth0.10 \
  vlan10-net

docker network create \
  --driver macvlan \
  --subnet 10.0.20.0/24 \
  -o parent=eth0.20 \
  vlan20-net

# 不同 VLAN 的容器网络隔离
```

---

### 7. 端口映射深入

#### 7.1 端口映射的底层实现

```bash
# 端口映射本质是 iptables DNAT 规则
docker run -d -p 8080:80 --name web nginx

# 查看 iptables 规则
iptables -t nat -L DOCKER -n -v
# Chain DOCKER (2 references)
# target     prot opt in     out     source       destination
# DNAT       tcp  --  !docker0 *       0.0.0.0/0    0.0.0.0/0    tcp dpt:8080 to:172.17.0.2:80

# 查看 DOCKER-INGRESS 链（Swarm 模式）
iptables -t nat -L DOCKER-INGRESS -n -v

# 查看 Docker 维护的规则
iptables -t nat -S DOCKER
iptables -S DOCKER
```

#### 7.2 端口映射语法详解

```bash
# 基本语法
docker run -p [host_ip:]host_port:container_port[/protocol] image

# 映射到所有接口
docker run -p 8080:80 nginx
# 0.0.0.0:8080 → 容器:80

# 绑定特定 IP
docker run -p 127.0.0.1:8080:80 nginx
# 仅本地可访问

# 绑定特定网卡
docker run -p 10.0.1.10:8080:80 nginx

# 多端口映射
docker run -p 8080:80 -p 8443:443 nginx

# 映射 UDP 端口
docker run -p 5353:53/udp dns-server

# 同时映射 TCP 和 UDP
docker run -p 5353:53/tcp -p 5353:53/udp dns-server

# 随机端口映射
docker run -P nginx  # 映射 Dockerfile 中 EXPOSE 的端口
docker port <container>  # 查看映射

# 端口范围映射
docker run -p 3000-3005:3000-3005 app

# IPv6 映射
docker run -p "[::1]:8080:80" nginx
```

#### 7.3 端口映射与 iptables 的关系

```bash
# Docker 创建的 iptables 链
# 1. nat 表:
#    - PREROUTING → DOCKER
#    - OUTPUT → DOCKER
# 2. filter 表:
#    - FORWARD → DOCKER-USER → DOCKER-ISOLATION-STAGE-1/2 → DOCKER

# 自定义防火规规则（在 DOCKER-USER 链中）
iptables -I DOCKER-USER -i eth0 -p tcp --dport 8080 -j DROP
# 拒绝外部访问 8080 端口

# 允许特定 IP 访问
iptables -I DOCKER-USER -i eth0 -s 10.0.1.0/24 -p tcp --dport 8080 -j ACCEPT
iptables -I DOCKER-USER -i eth0 -p tcp --dport 8080 -j DROP

# 重要: DOCKER-USER 链在 DOCKER 链之前执行
# 自定义规则不会被 Docker 覆盖
```

---

### 8. DNS 解析机制

#### 8.1 Docker 内嵌 DNS 服务器

```
自定义网络 DNS 解析流程:

容器内请求解析 "db"
    │
    ▼
┌───────────────────────────┐
│  容器 /etc/resolv.conf    │
│  nameserver 127.0.0.11    │  ← Docker 内嵌 DNS
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│  Docker DNS (127.0.0.11)  │
│                           │
│  1. 查询同网络容器名       │
│     "db" → 172.20.0.3     │  ← 匹配成功
│                           │
│  2. 查询网络别名           │
│     "database" → 172.20.0.3│
│                           │
│  3. 查询服务发现           │
│     (Swarm 模式)          │
│                           │
│  4. 转发到上游 DNS         │
│     (宿主机 /etc/resolv.conf)│
└───────────────────────────┘
```

#### 8.2 DNS 操作

```bash
# 容器 DNS 解析测试
docker exec my-container nslookup db
docker exec my-container dig db
docker exec my-container getent hosts db

# 自定义 DNS 服务器
docker run -d --dns 8.8.8.8 --dns 114.114.114.114 nginx

# 自定义 DNS 搜索域
docker run -d --dns-search example.com nginx

# 完整 DNS 配置
docker run -d \
  --dns 8.8.8.8 \
  --dns-search example.com \
  --dns-opt ndots:5 \
  nginx

# 容器内查看 DNS 配置
docker exec my-container cat /etc/resolv.conf
# nameserver 127.0.0.11
# options ndots:0

# 查看 Docker DNS 日志
docker logs <dns-container> 2>&1 | grep -i dns
```

#### 8.3 网络别名 (Network Alias)

```bash
# 为容器设置网络别名
docker run -d --network app-net --name web --network-alias www nginx

# 同一网络中可用别名解析
docker exec other-container ping www  # 成功

# 多个容器使用同一别名实现简单的负载均衡
docker run -d --network app-net --name web1 --network-alias www nginx
docker run -d --network app-net --name web2 --network-alias www nginx

# DNS 轮询: 每次解析 www 可能返回不同 IP
docker exec client nslookup www
# Address 1: 172.20.0.2
# Address 2: 172.20.0.3
```

---

### 9. 网络隔离策略

#### 9.1 多网络隔离架构

```
生产环境网络隔离方案:

┌─────────────────────────────────────────────────────┐
│                     宿主机                            │
│                                                     │
│  ┌─────────────────── Frontend Net ──────────────┐  │
│  │  172.30.0.0/24                                │  │
│  │                                               │  │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────┐      │  │
│  │  │  nginx  │  │  cdn    │  │  waf     │      │  │
│  │  │  .0.2   │  │  .0.3   │  │  .0.4    │      │  │
│  │  └────┬────┘  └─────────┘  └──────────┘      │  │
│  └───────┼───────────────────────────────────────┘  │
│          │                                          │
│  ┌───────┼───────────── Backend Net ─────────────┐  │
│  │       │  172.31.0.0/24                        │  │
│  │  ┌────┴────┐  ┌─────────┐  ┌──────────┐      │  │
│  │  │   api   │  │  worker │  │  cache   │      │  │
│  │  │  .0.2   │  │  .0.3   │  │  .0.4    │      │  │
│  │  └────┬────┘  └─────────┘  └──────────┘      │  │
│  └───────┼───────────────────────────────────────┘  │
│          │                                          │
│  ┌───────┼────────────── DB Net ─────────────────┐  │
│  │       │  172.32.0.0/24                        │  │
│  │  ┌────┴────┐  ┌─────────┐                     │  │
│  │  │  mysql  │  │  redis  │                     │  │
│  │  │  .0.2   │  │  .0.3   │                     │  │
│  │  └─────────┘  └─────────┘                     │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

隔离规则:
- nginx 同时加入 Frontend 和 Backend 网络
- api 同时加入 Backend 和 DB 网络
- mysql 仅在 DB 网络
- Frontend 和 DB 网络完全隔离
```

#### 9.2 实现多网络隔离

```bash
# 创建三个隔离网络
docker network create frontend-net
docker network create backend-net
docker network create db-net

# 部署 nginx (双网卡: frontend + backend)
docker run -d --name nginx --network frontend-net nginx
docker network connect backend-net nginx

# 部署 api (双网卡: backend + db)
docker run -d --name api --network backend-net api-server
docker network connect db-net api

# 部署 mysql (仅 db 网络)
docker run -d --name mysql --network db-net mysql:8.0

# 验证隔离性
docker exec nginx ping api     # 成功 (同在 backend-net)
docker exec nginx ping mysql   # 失败 (不在同一网络)
docker exec api ping mysql     # 成功 (同在 db-net)
docker exec mysql ping nginx   # 失败 (不在同一网络)
```

#### 9.3 网络策略最佳实践

```bash
# 1. 禁用容器间 ICC (Inter-Container Communication)
docker network create \
  --driver bridge \
  --opt com.docker.network.bridge.enable_icc=false \
  restricted-net
# ICC=false 时，同一网络的容器也不能直接通信
# 但可以通过端口映射访问

# 2. 限制容器 IP 范围
docker network create \
  --subnet 172.50.0.0/24 \
  --ip-range 172.50.0.128/25 \
  limited-net
# 只有 172.50.0.128 - 172.50.0.255 可用

# 3. 使用 internal 网络（无出站访问）
docker network create --internal internal-only-net
# 容器间可通信，但无法访问外部网络

# 4. 组合使用
docker network create \
  --driver bridge \
  --internal \
  --opt com.docker.network.bridge.enable_icc=true \
  secure-internal
```

---

### 10. 生产环境网络故障排查

#### 10.1 常见问题诊断流程

```bash
# === 第一步: 检查容器网络状态 ===
docker inspect -f '{{json .NetworkSettings.Networks}}' <container> | jq

# === 第二步: 检查 DNS 解析 ===
docker exec <container> nslookup <target>
docker exec <container> cat /etc/resolv.conf

# === 第三步: 检查连通性 ===
docker exec <container> ping -c 3 <target>
docker exec <container> curl -v http://<target>:<port>

# === 第四步: 检查端口 ===
docker exec <container> ss -tlnp
docker port <container>

# === 第五步: 检查 iptables 规则 ===
iptables -t nat -L DOCKER -n -v
iptables -L DOCKER-USER -n -v
iptables -L FORWARD -n -v

# === 第六步: 抓包分析 ===
# 在容器内抓包
docker exec <container> tcpdump -i eth0 -nn -c 100

# 在宿主机 veth 接口抓包
# 先找到容器的 veth 接口
CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' <container>)
VETH=$(nsenter -t $CONTAINER_PID -n ip link show eth0 | grep -oP 'veth\w+')
tcpdump -i $VETH -nn -c 100

# 在 docker0 上抓包
tcpdump -i docker0 -nn -c 100
```

#### 10.2 生产故障案例: 容器间 DNS 解析失败

**故障现象:**
```
应用日志报错: "Could not resolve host: db-service"
```

**排查步骤:**

```bash
# 1. 确认容器网络
docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' app
# 输出: bridge
# 问题: 使用默认 bridge，不支持 DNS 名称解析

# 2. 检查目标容器是否在同一网络
docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' db-service
# 输出: bridge

# 3. 验证 DNS 解析
docker exec app nslookup db-service
# server can't find db-service: NXDOMAIN

# 根因: 默认 bridge 网络不支持容器名 DNS 解析

# 解决方案: 使用自定义网络
docker network create app-net
docker network connect app-net app
docker network connect app-net db-service

# 验证
docker exec app nslookup db-service
# Name: db-service  Address: 172.20.0.3
```

#### 10.3 生产故障案例: 端口映射不生效

**故障现象:**
```
curl http://host-ip:8080 连接超时
但 docker ps 显示端口已映射 0.0.0.0:8080->80/tcp
```

**排查步骤:**

```bash
# 1. 确认容器是否正常运行
docker ps | grep myapp
docker logs myapp

# 2. 确认容器内部端口是否监听
docker exec myapp ss -tlnp | grep :80
# 如果没有输出: 应用未监听 80 端口

# 3. 检查 iptables 规则
iptables -t nat -L DOCKER -n -v | grep 8080
# 确认 DNAT 规则存在

# 4. 检查防火墙
iptables -L INPUT -n -v | grep 8080
# 或检查 firewalld
firewall-cmd --list-all

# 5. 检查 DOCKER-USER 链
iptables -L DOCKER-USER -n -v
# 可能有 DROP 规则

# 6. 检查宿主机网络
ss -tlnp | grep 8080
# 确认宿主机上 8080 端口是否被占用
```

#### 10.4 生产故障案例: 跨主机 overlay 网络不通

**排查步骤:**

```bash
# 1. 检查 Swarm 节点状态
docker node ls
# 确认所有节点 Ready

# 2. 检查 overlay 网络
docker network ls | grep overlay
docker network inspect <overlay-net>

# 3. 检查 VXLAN 端口 (UDP 4789)
ss -ulnp | grep 4789
# 确认两个节点都在监听

# 4. 检查防火墙规则
iptables -L INPUT -n -v | grep 4789
# 或
ufw status | grep 4789

# 5. 测试底层网络连通
# 从 Host A 到 Host B
nc -zvu 10.0.1.11 4789

# 6. 检查加密 overlay 的 SPI
docker network inspect --format '{{.Options}}' <overlay-net>
```

---

### 11. 网络性能调优

#### 11.1 MTU 配置

```bash
# 查看当前 MTU
docker exec my-container ip link show eth0
# mtu 1500

# Overlay 网络需要额外 50 字节 VXLAN 头
# 建议物理网络 MTU >= 1550
# 或调整 overlay MTU
docker network create \
  --driver overlay \
  --opt com.docker.network.driver.mtu=1400 \
  my-overlay

# Bridge 网络 MTU
docker network create \
  --driver bridge \
  --opt com.docker.network.driver.mtu=1400 \
  my-bridge
```

#### 11.2 sysctl 调优

```bash
# 在宿主机上调整内核参数
# /etc/sysctl.d/99-docker-network.conf

# 允许 IP 转发
net.ipv4.ip_forward = 1

# 增大连接跟踪表
net.netfilter.nf_conntrack_max = 1048576
net.netfilter.nf_conntrack_tcp_timeout_established = 86400

# 增大 ARP 缓存
net.ipv4.neigh.default.gc_thresh1 = 4096
net.ipv4.neigh.default.gc_thresh2 = 8192
net.ipv4.neigh.default.gc_thresh3 = 16384

# 应用配置
sysctl -p /etc/sysctl.d/99-docker-network.conf
```

---

## 💻 实战练习

### 练习 1: 多网络隔离部署

**目标:** 部署一个三层架构（Web/App/DB），实现严格的网络隔离。

```bash
# 1. 创建网络
docker network create frontend
docker network create backend

# 2. 部署数据库 (仅 backend)
docker run -d --name mysql \
  --network backend \
  -e MYSQL_ROOT_PASSWORD=secret \
  -e MYSQL_DATABASE=myapp \
  mysql:8.0

# 等待 MySQL 启动
sleep 30

# 3. 部署应用 (backend + 前端接口)
docker run -d --name app \
  --network backend \
  -e DB_HOST=mysql \
  -e DB_PASSWORD=secret \
  python:3.11-slim \
  python -c "
import http.server, json, os
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'db': os.environ.get('DB_HOST')}).encode())
    def log_message(self, format, *args): pass
http.server.HTTPServer(('0.0.0.0', 5000), Handler).serve_forever()
"
docker network connect frontend app

# 4. 部署 Nginx (仅 frontend)
docker run -d --name nginx \
  --network frontend \
  -p 8080:80 \
  nginx

# 5. 验证隔离性
# Nginx 能访问 app
docker exec nginx curl -s http://app:5000
# Nginx 不能访问 mysql
docker exec nginx ping -c 1 mysql  # 应失败

# 6. 清理
docker rm -f nginx app mysql
docker network rm frontend backend
```

### 练习 2: Macvlan 网络配置

**目标:** 配置 macvlan 网络，使容器拥有独立 IP 并可从外部直接访问。

```bash
# 1. 创建 macvlan 网络（根据实际环境调整子网）
docker network create \
  --driver macvlan \
  --subnet 192.168.1.0/24 \
  --gateway 192.168.1.1 \
  -o parent=eth0 \
  my-macvlan

# 2. 运行容器
docker run -d --name macvlan-nginx \
  --network my-macvlan \
  --ip 192.168.1.200 \
  nginx

# 3. 验证独立 IP
docker exec macvlan-nginx ip addr show eth0

# 4. 从外部网络测试
# curl http://192.168.1.200

# 5. 解决宿主机到 macvlan 容器通信
# 在宿主机上创建 macvlan 子接口
sudo ip link add mac0 link eth0 type macvlan mode bridge
sudo ip addr add 192.168.1.250/32 dev mac0
sudo ip link set mac0 up
sudo ip route add 192.168.1.200/32 dev mac0

# 6. 从宿主机访问
curl http://192.168.1.200

# 7. 清理
docker rm -f macvlan-nginx
docker network rm my-macvlan
sudo ip link delete mac0
```

### 练习 3: 网络故障排查挑战

**目标:** 诊断并修复一个故意配置错误的多容器环境。

```bash
# 设置故障环境
docker network create app-net
docker run -d --name db --network app-net \
  -e MYSQL_ROOT_PASSWORD=secret mysql:8.0
docker run -d --name cache redis:7-alpine
docker run -d --name api --network app-net \
  -e DB_HOST=db -e CACHE_HOST=cache \
  python:3.11-slim sleep 3600

# === 挑战 1: API 无法连接 cache ===
# 提示: 检查网络
docker exec api ping cache  # 应该失败
# 你的任务: 找出原因并修复

# === 挑战 2: DNS 解析失败 ===
# 创建一个新的默认 bridge 容器
docker run -d --name worker alpine sleep 3600
docker exec worker ping api  # 应该失败
# 你的任务: 找出为什么无法解析，并修复

# === 挑战 3: 外部无法访问 API ===
docker run -d --name gateway -p 9090:80 nginx
# curl http://localhost:9090  # 应该可以访问
# 但 curl http://localhost:9090/api 无法代理到 api
# 你的任务: 配置正确的网络和 nginx 代理

# 清理
docker rm -f db cache api worker gateway
docker network rm app-net
```

**故障排查思考题:**

1. 为什么 `cache` 容器无法被 `api` 容器解析？
2. 如何让 `api` 容器同时访问 `db` 和 `cache`？
3. 默认 bridge 网络和自定义 bridge 网络的 DNS 行为有什么不同？
4. 如何查看容器的完整网络配置？
5. iptables 规则被意外清空后如何恢复 Docker 网络？

---

## 🎯 面试题精选

### 1. Docker 的 bridge 网络和 host 网络有什么区别？各自的适用场景是什么？

**参考答案:**

Bridge 网络为每个容器创建独立的网络命名空间，通过 veth pair 连接到 Linux Bridge，使用 NAT 实现外部访问。优点是网络隔离好、端口映射灵活；缺点是有少量性能开销。适用于大多数场景，尤其是需要端口映射和网络隔离的 Web 应用。

Host 网络让容器与宿主机共享网络命名空间，容器直接使用宿主机的 IP 和端口。优点是性能最优、无 NAT 开销；缺点是没有网络隔离、存在端口冲突风险。适用于对网络性能要求极高的场景，如高性能负载均衡器、网络监控工具等。

### 2. 为什么默认 bridge 网络不推荐用于生产环境？

**参考答案:**

默认 bridge 网络存在以下问题:
- 不支持 DNS 名称解析，容器间只能通过 IP 通信，IP 会随容器重建而变化
- 所有容器共享同一网络，无法实现网络隔离
- 不支持自动的服务发现
- 配置灵活性差，无法自定义子网、网关等参数

自定义 bridge 网络内置 DNS 服务器，支持容器名解析，支持网络隔离，是生产环境的推荐选择。

### 3. Docker 端口映射的底层实现原理是什么？

**参考答案:**

Docker 端口映射通过 iptables 的 DNAT（目标地址转换）规则实现。当执行 `docker run -p 8080:80` 时，Docker 在 nat 表的 DOCKER 链中添加规则，将宿主机 8080 端口的流量 DNAT 到容器的 80 端口。同时在 filter 表的 FORWARD 链中添加规则允许转发。

流量路径: 客户端 → 宿主机 eth0:8080 → iptables DNAT → 容器 veth → 容器 eth0:80

### 4. Overlay 网络如何实现跨主机通信？

**参考答案:**

Overlay 网络基于 VXLAN 技术。每个主机上运行 VXLAN 隧道端点（VTEP），当容器发送数据包到另一主机的容器时:
1. 源主机 VTEP 将原始以太网帧封装在 VXLAN 报文中
2. VXLAN 报文包含外层 UDP 头（目的端口 4789）和外层 IP 头
3. 通过物理网络传输到目标主机
4. 目标主机 VTEP 解封装，取出原始帧并交付给目标容器

Overlay 网络需要 Swarm 模式或 KV 存储（如 etcd）来同步网络状态。

### 5. 如何实现 Docker 容器间的网络隔离？

**参考答案:**

主要方法:
1. **多自定义网络:** 将不同服务放入不同网络，只在需要通信的服务间建立连接（多网卡）
2. **internal 网络:** `docker network create --internal` 创建无外部访问的隔离网络
3. **ICC 禁用:** `--opt com.docker.network.bridge.enable_icc=false` 禁止同网络容器直接通信
4. **DOCKER-USER 链:** 通过 iptables 规则精细控制流量
5. **macvlan + VLAN:** 基于 VLAN ID 实现物理层隔离

### 6. 容器无法解析其他容器名称，如何排查？

**参考答案:**

排查步骤:
1. 确认是否使用自定义网络（默认 bridge 不支持名称解析）
2. 确认两个容器是否在同一网络中
3. 检查 `/etc/resolv.conf` 是否指向 `127.0.0.11`
4. 确认目标容器正在运行
5. 尝试用 IP 直接通信排除网络层面问题
6. 检查 Docker daemon DNS 配置

### 7. Docker 的 DNS 解析机制是怎样的？

**参考答案:**

Docker 在每个容器内配置 DNS 服务器地址为 `127.0.0.11`，这是 Docker 内嵌的 DNS 服务器。解析流程:
1. 容器内应用请求解析域名
2. 请求发送到 `127.0.0.11`
3. Docker DNS 首先在自定义网络中查找匹配的容器名或网络别名
4. 找到则返回容器 IP
5. 未找到则转发到上游 DNS（宿主机 `/etc/resolv.conf` 或 `--dns` 指定的服务器）

Swarm 模式下还支持基于服务名的 DNS 解析和负载均衡。

### 8. 如何在不影响现有容器的情况下修改 Docker 的 iptables 规则？

**参考答案:**

使用 DOCKER-USER 链。Docker 不会修改 DOCKER-USER 链中的规则，且该链在 DOCKER 链之前执行。

```bash
# 拒绝外部访问容器的 8080 端口
iptables -I DOCKER-USER -i eth0 -p tcp --dport 8080 -j DROP

# 仅允许特定网段访问
iptables -I DOCKER-USER -i eth0 -s 10.0.0.0/8 -j ACCEPT
iptables -A DOCKER-USER -i eth0 -j DROP
```

### 9. macvlan 和 ipvlan 有什么区别？

**参考答案:**

Macvlan 为每个虚拟接口分配独立的 MAC 地址，对物理网络来说就像是独立的物理设备。缺点是某些云平台或交换机对 MAC 地址数量有限制。

Ipvlan 所有虚拟接口共享父接口的 MAC 地址，但有不同的 IP 地址。使用三层路由而非二层交换，不消耗 MAC 地址资源，适合 MAC 地址受限的环境。

### 10. 生产环境中 Docker 网络的最佳实践有哪些？

**参考答案:**

1. 始终使用自定义 bridge 网络替代默认 bridge
2. 按功能分层创建网络（frontend/backend/database）
3. 使用 internal 网络隔离无需外部访问的服务
4. 设置合理的 MTU（overlay 网络需考虑 VXLAN 开销）
5. 在 DOCKER-USER 链中配置防火墙规则
6. 监控 conntrack 表使用量
7. 避免在生产环境使用 host 网络（除非有特殊性能需求）
8. 为关键服务配置网络别名便于服务发现
9. 使用 overlay 加密选项保护跨主机通信
10. 定期清理未使用的网络

---

## 📚 深入阅读

- [Docker 官方网络文档](https://docs.docker.com/network/)
- [Bridge 网络驱动](https://docs.docker.com/network/bridge/)
- [Overlay 网络驱动](https://docs.docker.com/network/overlay/)
- [Macvlan 网络驱动](https://docs.docker.com/network/macvlan/)
- [Docker 网络与 iptables](https://docs.docker.com/network/iptables/)
- [Linux Bridge vs Open vSwitch](https://developers.redhat.com/blog/2017/06/28/what-is-a-linux-bridge)
- [VXLAN 协议详解](https://datatracker.ietf.org/doc/html/rfc7348)

---

## ✅ 自检清单

- [ ] 能区分五种网络驱动的适用场景
- [ ] 理解默认 bridge 和自定义 bridge 的 DNS 差异
- [ ] 能创建自定义网络并配置子网、网关
- [ ] 理解端口映射的 iptables DNAT 实现
- [ ] 能配置 macvlan 网络并解决宿主机通信问题
- [ ] 理解 overlay 网络的 VXLAN 封装机制
- [ ] 能实现多层网络隔离架构
- [ ] 掌握容器 DNS 解析机制和网络别名
- [ ] 能排查常见的网络故障（DNS 不通、端口不生效、跨主机不通）
- [ ] 知道如何在 DOCKER-USER 链中安全地添加防火墙规则
- [ ] 理解网络性能调优（MTU、conntrack、sysctl）
