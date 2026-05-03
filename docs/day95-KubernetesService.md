# Day 95: Kubernetes Service

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes Service（ClusterIP/NodePort/LoadBalancer/ExternalName, Endpoints, kube-proxy 三种模式, 会话保持, Headless Service）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 91 Kubernetes Pod, Day 92 Deployment, Day 93 命名空间与标签

## 🎯 学习目标

完成 Day 95 的学习后，你应该能够：

1. 深入理解 Kubernetes Service 的四种类型及其适用场景
2. 掌握 kube-proxy 三种工作模式（iptables/IPVS/eBPF）的原理与区别
3. 能够配置 Headless Service 和会话保持（Session Affinity）
4. 理解 Endpoints 机制并排查服务发现问题
5. 在生产环境中正确选择和配置 Service 类型

---

## 📖 核心知识点

### 1. Service 概念与原理

#### 1.1 为什么需要 Service

Pod 是临时的、可替换的。每次 Pod 重建，IP 地址都会变化。Service 为一组 Pod 提供稳定的访问入口：

```
┌─────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                    │
│                                                         │
│  Client Pod                                             │
│     │                                                   │
│     │  请求 myapp:80                                    │
│     ▼                                                   │
│  ┌──────────────────────┐                               │
│  │   Service: myapp     │   ← 稳定的虚拟 IP (VIP)       │
│  │   ClusterIP: 10.96.x │                               │
│  │   Port: 80           │                               │
│  └──────────┬───────────┘                               │
│             │                                           │
│     ┌───────┼───────┐                                   │
│     ▼       ▼       ▼                                   │
│  ┌─────┐ ┌─────┐ ┌─────┐                               │
│  │Pod 1│ │Pod 2│ │Pod 3│   ← IP 会变，但 Service 不变  │
│  │:8080│ │:8080│ │:8080│                                │
│  └─────┘ └─────┘ └─────┘                               │
└─────────────────────────────────────────────────────────┘
```

#### 1.2 Service 的核心组件

```
Service 资源
    │
    ├── spec.selector     ──→  标签选择器，匹配后端 Pod
    ├── spec.ports[]      ──→  端口映射（port → targetPort）
    ├── spec.type         ──→  Service 类型
    └── status.loadBalancer  └─→  LoadBalancer 类型的外部 IP

自动创建的资源：
    Endpoints (或 EndpointSlice)
        └── 记录匹配到的所有 Pod IP:Port
```

#### 1.3 Service 四种类型对比

| 特性 | ClusterIP | NodePort | LoadBalancer | ExternalName |
|------|-----------|----------|--------------|--------------|
| 默认类型 | 是 | 否 | 否 | 否 |
| 集群内访问 | 可以 | 可以 | 可以 | 可以 |
| 节点端口暴露 | 否 | 是 (30000-32767) | 是 | 否 |
| 外部 LB | 否 | 否 | 是 | 否 |
| DNS 映射 | A 记录 | A 记录 | A 记录 | CNAME 记录 |
| 典型用途 | 内部服务通信 | 开发/测试 | 生产外部访问 | 外部服务别名 |
| 性能开销 | 低 | 中 | 中 | 极低 |

---

### 2. ClusterIP（默认类型）

#### 2.1 基本配置

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-service
  namespace: default
spec:
  type: ClusterIP          # 默认值，可省略
  selector:
    app: myapp
    version: v1
  ports:
    - name: http            # 端口名称（多端口时必须指定）
      protocol: TCP
      port: 80              # Service 端口（客户端访问的端口）
      targetPort: 8080      # Pod 端口（容器监听的端口）
    - name: https
      protocol: TCP
      port: 443
      targetPort: 8443
```

#### 2.2 DNS 解析规则

```
完整 DNS 格式：<service-name>.<namespace>.svc.cluster.local

示例（同 namespace）：
  myapp-service  →  10.96.0.100

示例（跨 namespace）：
  myapp-service.default.svc.cluster.local  →  10.96.0.100
  myapp-service.default                     →  10.96.0.100

无头 Service：
  myapp-headless.default.svc.cluster.local  →  Pod IP 列表
```

#### 2.3 源码视角：ClusterIP 的工作流程

```
1. kube-apiserver 收到 Service 创建请求
2. 分配 ClusterIP（从 --service-cluster-ip-range 指定的 CIDR 中）
3. 将 Service 信息写入 etcd
4. kube-proxy watch 到 Service 变更
5. kube-proxy 在每个节点上配置转发规则（iptables/IPVS）
6. Endpoints Controller 创建 Endpoints 对象（记录 Pod IP）
7. 客户端请求 ClusterIP → 内核转发 → Pod
```

---

### 3. NodePort

#### 3.1 配置示例

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-nodeport
spec:
  type: NodePort
  selector:
    app: myapp
  ports:
    - name: http
      port: 80               # 集群内部端口
      targetPort: 8080       # Pod 端口
      nodePort: 30080        # 节点端口（可选，不指定则自动分配）
    - name: https
      port: 443
      targetPort: 8443
      nodePort: 30443
  externalTrafficPolicy: Cluster  # 或 Local
```

#### 3.2 externalTrafficPolicy 详解

```
┌─ externalTrafficPolicy: Cluster（默认）─────────────────┐
│                                                         │
│  外部请求 → 任意节点 → iptables 转发到其他节点的 Pod     │
│                                                         │
│  优点：流量均匀分布                                      │
│  缺点：多一跳网络延迟；丢失源 IP                         │
└─────────────────────────────────────────────────────────┘

┌─ externalTrafficPolicy: Local ──────────────────────────┐
│                                                         │
│  外部请求 → 有 Pod 的节点 → 直接转发到本节点 Pod         │
│  外部请求 → 无 Pod 的节点 → 连接被拒绝                   │
│                                                         │
│  优点：保留源 IP；减少一跳延迟                           │
│  缺点：流量分布不均匀                                    │
└─────────────────────────────────────────────────────────┘
```

#### 3.3 SRE 注意事项

```bash
# 查看 NodePort 分配情况
kubectl get svc myapp-nodeport -o jsonpath='{.spec.ports[*].nodePort}'

# 确认节点防火墙规则（云厂商安全组需放行 30000-32767）
# AWS Security Group / GCP Firewall Rules / Azure NSG

# 端口范围配置（kube-apiserver 启动参数）
--service-node-port-range=30000-32767
```

---

### 4. LoadBalancer

#### 4.1 基本配置

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-lb
  annotations:
    # AWS 特定注解
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"  # 或 "clb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    # GCP 特定注解
    # cloud.google.com/load-balancer-type: "Internal"  # 内部 LB
spec:
  type: LoadBalancer
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
      protocol: TCP
  loadBalancerSourceRanges:    # 限制访问源 IP
    - 10.0.0.0/8
    - 172.16.0.0/12
  externalTrafficPolicy: Local  # 保留源 IP
```

#### 4.2 各云厂商 LB 类型对照

| 云厂商 | 注解 | 类型 | 说明 |
|--------|------|------|------|
| AWS | `aws-load-balancer-type: "nlb"` | NLB | 网络负载均衡，高性能 |
| AWS | `aws-load-balancer-type: "clb"` | CLB | 经典负载均衡 |
| GCP | `load-balancer-type: "Internal"` | 内部 LB | 仅内网可访问 |
| Azure | `load-balancer-internal: "true"` | 内部 LB | 仅 VNet 可访问 |
| 阿里云 | `service.beta.kubernetes.io/alibaba-cloud-loadbalancer-spec` | SLB 规格 | slb.s1.small 等 |

#### 4.3 MetalLB（裸金属集群）

在非云环境（裸金属）中，LoadBalancer 类型默认无法使用。MetalLB 填补了这个空白：

```yaml
# MetalLB 地址池配置
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: default-pool
  namespace: metallb-system
spec:
  addresses:
    - 192.168.1.240-192.168.1.250
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: default
  namespace: metallb-system
spec:
  ipAddressPools:
    - default-pool
```

---

### 5. ExternalName

#### 5.1 基本配置

```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-db
  namespace: production
spec:
  type: ExternalName
  externalName: db.prod.example.com   # 外部服务的 CNAME 目标
```

#### 5.2 使用场景

```
场景：应用代码中写死了服务名 "external-db"
  → 需要将其映射到外部数据库 RDS 地址

Pod 内解析 external-db.production.svc.cluster.local
  → DNS 返回 CNAME → db.prod.example.com
  → 最终解析到 RDS 的 IP 地址

优势：
  1. 应用代码无需修改
  2. 可以通过修改 ExternalName 切换后端
  3. 跨集群服务发现
```

#### 5.3 注意事项

```yaml
# ExternalName 不能与 selector 同时使用
# ExternalName 不支持端口映射（需要配合端口使用 Endpoints）

# 如果需要端口映射，手动创建 Endpoints：
apiVersion: v1
kind: Endpoints
metadata:
  name: external-db
subsets:
  - addresses:
      - ip: 203.0.113.10
    ports:
      - port: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: external-db
spec:
  ports:
    - port: 5432
  # 注意：没有 selector
```

---

### 6. Endpoints 与 EndpointSlice

#### 6.1 Endpoints 对象

```bash
# 查看 Service 关联的 Endpoints
kubectl get endpoints myapp-service

# 输出示例
# NAME           ENDPOINTS                                AGE
# myapp-service  10.244.1.5:8080,10.244.2.8:8080,10.244.3.3:8080  5m

# 详细查看
kubectl get endpoints myapp-service -o yaml
```

```yaml
# Endpoints YAML（由 Endpoints Controller 自动维护）
apiVersion: v1
kind: Endpoints
metadata:
  name: myapp-service      # 与 Service 同名
subsets:
  - addresses:             # 就绪 Pod 的 IP 列表
      - ip: 10.244.1.5
        nodeName: node-1
        targetRef:
          kind: Pod
          name: myapp-pod-1
          namespace: default
      - ip: 10.244.2.8
        nodeName: node-2
      - ip: 10.244.3.3
        nodeName: node-3
    notReadyAddresses: []  # 未就绪 Pod（Readiness Probe 失败）
    ports:
      - name: http
        port: 8080
        protocol: TCP
```

#### 6.2 EndpointSlice（Kubernetes 1.21+默认）

```
Endpoints 的问题：
  - 单个 Endpoints 对象包含所有 Pod IP
  - 大规模集群中（数千 Pod），每次变更都要全量更新
  - 导致 kube-proxy 和 etcd 的压力剧增

EndpointSlice 的改进：
  - 分片存储（每个 Slice 最多 100 个 Endpoint）
  - 支持增量更新
  - 支持拓扑感知路由（Topology Aware Routing）
```

```bash
# 查看 EndpointSlice
kubectl get endpointslice -l kubernetes.io/service-name=myapp-service

# 输出示例
# NAME                        ADDRESSTYPE   PORTS   ENDPOINTS                AGE
# myapp-service-abc12         IPv4          8080    10.244.1.5,10.244.2.8   5m
```

#### 6.3 手动管理 Endpoints（无 Selector 的 Service）

```yaml
# 场景：访问集群外部的数据库
apiVersion: v1
kind: Service
metadata:
  name: external-postgres
spec:
  ports:
    - port: 5432
      targetPort: 5432
  # 没有 selector，需要手动创建 Endpoints
---
apiVersion: v1
kind: Endpoints
metadata:
  name: external-postgres    # 必须与 Service 同名
subsets:
  - addresses:
      - ip: 10.0.1.100       # 外部数据库主节点
      - ip: 10.0.1.101       # 外部数据库只读副本
    ports:
      - port: 5432
        protocol: TCP
```

---

### 7. kube-proxy 三种模式（高频面试题）

#### 7.1 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                     kube-apiserver                          │
│                         │                                   │
│                   watch Service/Endpoints                   │
│                         │                                   │
│              ┌──────────┼──────────┐                        │
│              ▼          ▼          ▼                        │
│         ┌─────────┐ ┌─────────┐ ┌─────────┐                │
│         │ iptables│ │  IPVS   │ │  eBPF   │                │
│         │  模式   │ │  模式   │ │  模式   │                │
│         └─────────┘ └─────────┘ └─────────┘                │
│              │          │          │                        │
│              ▼          ▼          ▼                        │
│         内核 Netfilter  内核 IPVS   内核 eBPF              │
│              │          │          │                        │
│              └──────────┼──────────┘                        │
│                         ▼                                   │
│                    后端 Pod                                  │
└─────────────────────────────────────────────────────────────┘
```

#### 7.2 iptables 模式（默认）

**原理**：

```
kube-proxy 监听 Service 和 Endpoints 变化
  → 生成 iptables 规则
  → 写入 nat 表的 KUBE-SERVICES 链

请求流程：
  Pod 访问 ClusterIP:Port
    → PREROUTING 链
    → KUBE-SERVICES 链（匹配目标 IP:Port）
    → KUBE-SVC-XXXX 链（Service 级别）
    → KUBE-SEP-XXXX 链（Endpoint 级别，DNAT 到具体 Pod）
    → 数据包目标 IP 被修改为 Pod IP
    → 路由到 Pod
```

**iptables 规则示例**：

```bash
# 查看 kube-proxy 生成的 iptables 规则
iptables -t nat -L KUBE-SERVICES -n --line-numbers

# 规则结构示例：
# Chain KUBE-SERVICES (1 references)
# target     prot  source    destination
# KUBE-SVC-xxx  tcp  --  0.0.0.0/0  10.96.0.100  /* default/myapp:http */ tcp dpt:80

# 负载均衡实现：
# - 概率匹配（probability 模块）
# - 2 个 Pod：各 50% 概率
# - 3 个 Pod：各 33.3% 概率
# - 通过 KUBE-SEP-xxx 链 DNAT 到具体 Pod IP
```

**iptables 模式的优缺点**：

```
优点：
  + 实现简单，成熟稳定
  + 内核原生支持，无需额外组件
  + 适合中小规模集群（Service 数 < 1000）

缺点：
  - 规则线性匹配，O(n) 复杂度
  - Service/Endpoints 变更时全量刷新规则
  - 大规模集群中规则数量爆炸（N Service × M Pod）
  - 1000 Service × 10 Pod = ~20000 条规则
  - 规则更新期间可能导致短暂连接中断
  - 不支持高级负载均衡算法（仅随机/概率）
```

#### 7.3 IPVS 模式

**原理**：

```
IPVS（IP Virtual Server）是 Linux 内核的四层负载均衡模块
  → 基于 Netfilter 的钩子函数
  → 使用哈希表存储规则，O(1) 查找
  → 支持多种负载均衡算法

kube-proxy 使用 IPVS 模式：
  → 监听 Service/Endpoints 变更
  → 通过 netlink 接口操作 IPVS 规则
  → 创建虚拟服务器（Virtual Server）和真实服务器（Real Server）
```

**IPVS 负载均衡算法**：

| 算法 | 缩写 | 说明 | 适用场景 |
|------|------|------|----------|
| Round Robin | rr | 轮询（默认） | 通用场景 |
| Least Connection | lc | 最少连接数 | 长连接服务 |
| Destination Hashing | dh | 目标地址哈希 | 缓存亲和性 |
| Source Hashing | sh | 源地址哈希 | 会话保持 |
| Shortest Expected Delay | sed | 最短预期延迟 | 低延迟要求 |
| Never Queue | nq | 从不排队 | 高性能要求 |

**启用 IPVS 模式**：

```yaml
# kube-proxy ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: kube-proxy
  namespace: kube-system
data:
  config.conf: |
    mode: "ipvs"
    ipvs:
      scheduler: "rr"           # 负载均衡算法
      syncPeriod: "30s"         # 规则同步周期
      minSyncPeriod: "2s"       # 最小同步间隔
      strictARP: true           # MetalLB 需要
    iptables:
      masqueradeAll: false
      syncPeriod: "30s"
```

```bash
# 确认 IPVS 模式已启用
kubectl logs -n kube-system kube-proxy-xxxxx | grep "Using ipvs"

# 查看 IPVS 规则
ipvsadm -Ln
ipvsadm -Ln -t 10.96.0.100:80    # 查看特定 Service

# 输出示例：
# TCP  10.96.0.100:80 rr
#   -> 10.244.1.5:8080     Masq    1      0
#   -> 10.244.2.8:8080     Masq    1      0
#   -> 10.244.3.3:8080     Masq    1      0
```

**IPVS 模式的优缺点**：

```
优点：
  + O(1) 哈希表查找，性能远优于 iptables
  + 支持多种负载均衡算法
  + 规则增量更新，不需要全量刷新
  + 适合大规模集群（Service 数 > 1000）
  + 支持连接重用（connection reuse）

缺点：
  - 需要加载 ip_vs 内核模块
  - 配置相对复杂
  - 调试需要使用 ipvsadm 工具
  - 与某些 CNI 插件可能有兼容性问题
```

#### 7.4 eBPF 模式（Cilium）

**原理**：

```
eBPF（extended Berkeley Packet Filter）
  → 在内核中运行沙盒程序
  → 可以挂载到网络栈的各个钩子点
  → 绕过 iptables/IPVS，直接在 XDP 层处理

Cilium eBPF kube-proxy 替代方案：
  → 在 TC（Traffic Control）和 XDP 层拦截流量
  → 直接在内核中完成 Service 到 Pod 的映射
  → 支持 socket-level 负载均衡（sock_ops）
```

**eBPF 模式的优缺点**：

```
优点：
  + 性能最优（内核态直接处理）
  + 支持高级功能（L7 负载均衡、网络策略）
  + 无需 iptables/IPVS
  + 可观测性强（BPF maps 可查询）
  + 支持 Maglev 一致性哈希

缺点：
  - 需要较新的内核版本（>= 4.19.57）
  - 依赖 Cilium CNI
  - 排查问题需要了解 eBPF
  - 生态相对较新
```

#### 7.5 三种模式对比总结（面试重点）

| 特性 | iptables | IPVS | eBPF (Cilium) |
|------|----------|------|---------------|
| 查找复杂度 | O(n) | O(1) | O(1) |
| 最大 Service 数 | ~5000 | ~10000+ | ~50000+ |
| 负载均衡算法 | 概率随机 | rr/lc/dh/sh/sed/nq | Maglev/随机 |
| 规则更新 | 全量刷新 | 增量更新 | 增量更新 |
| 内核要求 | 通用 | ip_vs 模块 | >= 4.19.57 |
| 调试工具 | iptables -L | ipvsadm | bpftool/cilium |
| 源 IP 保留 | 需要配置 | 支持 | 原生支持 |
| 适用规模 | 小中型 | 大型 | 超大型 |
| 部署复杂度 | 低 | 中 | 高 |
| 生产成熟度 | 最成熟 | 成熟 | 快速成熟中 |

---

### 8. 会话保持（Session Affinity）

#### 8.1 ClusterIP 会话保持

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-session
spec:
  type: ClusterIP
  selector:
    app: myapp
  sessionAffinity: ClientIP      # 基于客户端 IP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800      # 会话超时时间（默认 10800s = 3h）
  ports:
    - port: 80
      targetPort: 8080
```

#### 8.2 会话保持的工作原理

```
┌─ iptables 模式下的会话保持 ─────────────────────────────┐
│                                                         │
│  kube-proxy 生成 iptables 规则时：                       │
│  - 不再使用 probability 模块                            │
│  - 改用 recent 模块记录客户端 IP                         │
│  - 同一客户端 IP 的请求总是转发到同一 Pod                │
│                                                         │
│  缺点：                                                 │
│  - Endpoints 变更时会话可能中断                          │
│  - Pod 扩缩容时会话会重新分配                            │
└─────────────────────────────────────────────────────────┘

┌─ IPVS 模式下的会话保持 ─────────────────────────────────┐
│                                                         │
│  使用 sh（Source Hashing）算法：                         │
│  - 基于源 IP 哈希选择后端                               │
│  - 会话超时由 IPVS 的 persistence_timeout 控制          │
│                                                         │
│  配置：                                                 │
│  ipvsadm -Ln -t 10.96.0.100:80 -p 10800               │
└─────────────────────────────────────────────────────────┘
```

#### 8.3 高级会话保持：使用 Envoy/Istio

```yaml
# Istio DestinationRule 实现更精细的会话保持
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: myapp-session
spec:
  host: myapp-service
  trafficPolicy:
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"     # 基于 HTTP Header
        # httpCookie:                    # 或基于 Cookie
        #   name: session-id
        #   ttl: 3600s
        # useSourceIp: true             # 或基于源 IP
```

---

### 9. Headless Service

#### 9.1 什么是 Headless Service

```
Headless Service = clusterIP: None 的 Service

特点：
  - 不分配 ClusterIP
  - DNS 解析直接返回所有 Pod IP 列表
  - 客户端可以直接连接到特定 Pod
  - 适合有状态应用（StatefulSet）
```

#### 9.2 配置示例

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-headless
spec:
  clusterIP: None           # 关键字段：设为 None
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
```

#### 9.3 DNS 解析行为对比

```bash
# 普通 Service DNS 解析
nslookup myapp-service.default.svc.cluster.local
# 返回：
# Name:    myapp-service.default.svc.cluster.local
# Address: 10.96.0.100        ← 单个 ClusterIP

# Headless Service DNS 解析
nslookup myapp-headless.default.svc.cluster.local
# 返回：
# Name:    myapp-headless.default.svc.cluster.local
# Address: 10.244.1.5         ← Pod 1 IP
# Address: 10.244.2.8         ← Pod 2 IP
# Address: 10.244.3.3         ← Pod 3 IP

# StatefulSet Pod 的 DNS（带序号）
nslookup myapp-headless-0.myapp-headless.default.svc.cluster.local
# 返回：
# Name:    myapp-headless-0.myapp-headless.default.svc.cluster.local
# Address: 10.244.1.5         ← 特定 Pod 的 IP
```

#### 9.4 Headless Service 的典型用途

```
1. StatefulSet（有状态应用）
   - MySQL 主从集群：客户端需要连接到特定实例
   - Redis Cluster：节点间需要直接通信
   - Kafka：Broker 需要固定标识

2. 服务发现
   - 客户端自行实现负载均衡
   - gRPC 客户端端负载均衡

3. 批处理任务
   - 需要发现所有 Worker 节点
```

#### 9.5 StatefulSet + Headless Service 完整示例

```yaml
# Headless Service（提供 DNS）
apiVersion: v1
kind: Service
metadata:
  name: mysql
  labels:
    app: mysql
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
    - port: 3306
      targetPort: 3306
      name: mysql
---
# StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: "mysql"        # 必须与 Headless Service 名称匹配
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
        - name: mysql
          image: mysql:8.0
          ports:
            - containerPort: 3306
              name: mysql
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: root-password
          volumeMounts:
            - name: mysql-data
              mountPath: /var/lib/mysql
  volumeClaimTemplates:
    - metadata:
        name: mysql-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: "standard"
        resources:
          requests:
            storage: 20Gi
```

---

### 10. Service 高级配置

#### 10.1 多端口 Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp-multiport
spec:
  selector:
    app: myapp
  ports:
    - name: http
      port: 80
      targetPort: 8080
    - name: https
      port: 443
      targetPort: 8443
    - name: metrics
      port: 9090
      targetPort: 9090
```

#### 10.2 Service 与 Pod 端口映射

```yaml
# 方式 1：直接指定端口号
ports:
  - port: 80
    targetPort: 8080

# 方式 2：引用 Pod 端口名称
ports:
  - port: 80
    targetPort: http     # Pod 中定义的端口名称

# 方式 3：port == targetPort（省略 targetPort）
ports:
  - port: 8080           # Service 和 Pod 都使用 8080
```

#### 10.3 External IPs

```yaml
# 在已有节点 IP 上暴露 Service（不需要 NodePort）
apiVersion: v1
kind: Service
metadata:
  name: myapp-external
spec:
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
  externalIPs:
    - 203.0.113.10    # 节点的外部 IP
    - 203.0.113.11    # 另一个节点的外部 IP
```

---

## 💻 实战练习

### 练习 1：基础 Service 操作

**目标**：创建不同类型的 Service 并验证服务发现

```bash
# 1. 创建一个 Deployment
kubectl create deployment nginx-demo --image=nginx:1.25 --replicas=3

# 2. 创建 ClusterIP Service
kubectl expose deployment nginx-demo --port=80 --target-port=80 --type=ClusterIP

# 3. 验证 Service 和 Endpoints
kubectl get svc nginx-demo
kubectl get endpoints nginx-demo

# 4. 在集群内测试 DNS 解析
kubectl run test-pod --image=busybox:1.36 --rm -it --restart=Never -- nslookup nginx-demo

# 5. 测试负载均衡（多次请求观察变化）
kubectl run test-pod --image=busybox:1.36 --rm -it --restart=Never -- \
  sh -c "for i in \$(seq 1 10); do wget -qO- nginx-demo 2>/dev/null | grep 'Server Address' || echo 'Request \$i'; done"

# 6. 创建 NodePort Service
kubectl delete svc nginx-demo
kubectl expose deployment nginx-demo --port=80 --target-port=80 --type=NodePort

# 7. 查看分配的 NodePort
kubectl get svc nginx-demo -o jsonpath='{.spec.ports[0].nodePort}'

# 8. 通过 NodePort 访问
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[0].address}')
NODE_PORT=$(kubectl get svc nginx-demo -o jsonpath='{.spec.ports[0].nodePort}')
curl http://${NODE_IP}:${NODE_PORT}
```

### 练习 2：Headless Service 与 StatefulSet

**目标**：理解 Headless Service 的 DNS 解析行为

```bash
# 1. 创建 Headless Service
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: nginx-headless
spec:
  clusterIP: None
  selector:
    app: nginx-stateful
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: "nginx-headless"
  replicas: 3
  selector:
    matchLabels:
      app: nginx-stateful
  template:
    metadata:
      labels:
        app: nginx-stateful
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
          ports:
            - containerPort: 80
          volumeMounts:
            - name: www
              mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
    - metadata:
        name: www
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 1Gi
EOF

# 2. 等待 Pod 就绪
kubectl wait --for=condition=ready pod -l app=nginx-stateful --timeout=120s

# 3. 测试 Headless Service DNS（返回所有 Pod IP）
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- \
  nslookup nginx-headless

# 4. 测试 StatefulSet Pod 的 DNS（单个 Pod）
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- \
  nslookup web-0.nginx-headless

# 5. 验证每个 Pod 有独立的存储
for i in 0 1 2; do
  kubectl exec web-$i -- sh -c "echo 'Hello from web-$i' > /usr/share/nginx/html/index.html"
done

# 6. 验证可以通过特定 Pod DNS 访问
kubectl run curl-test --image=curlimages/curl:8.5.0 --rm -it --restart=Never -- \
  sh -c "curl -s web-0.nginx-headless; echo; curl -s web-1.nginx-headless; echo; curl -s web-2.nginx-headless"
```

### 练习 3：故障排查挑战

**目标**：排查常见的 Service 发现问题

```bash
# 场景 1：Service 无 Endpoints
# 创建一个错误的 Service（selector 与 Pod 标签不匹配）
kubectl create deployment myapp --image=nginx --replicas=2
kubectl expose deployment myapp --port=80

# 故意修改 Pod 标签使其不匹配
kubectl label pod -l app=myapp app=wrong-label --overwrite

# 排查步骤：
kubectl get endpoints myapp                        # 检查 Endpoints 是否为空
kubectl get pods --show-labels | grep myapp        # 检查 Pod 标签
kubectl describe svc myapp                         # 检查 selector

# 修复：
kubectl label pod -l app=wrong-label app=myapp --overwrite

# 场景 2：Pod 未就绪导致 Endpoints 为空
# 创建一个 Readiness Probe 失败的 Deployment
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: failing-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: failing
  template:
    metadata:
      labels:
        app: failing
    spec:
      containers:
        - name: app
          image: nginx
          readinessProbe:
            httpGet:
              path: /healthz
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: failing-app
spec:
  selector:
    app: failing
  ports:
    - port: 80
      targetPort: 80
EOF

# 排查步骤：
kubectl get pods -l app=failing                    # 检查 Pod 状态
kubectl describe pod -l app=failing | grep -A5 "Readiness"  # 检查 Readiness
kubectl get endpoints failing-app                  # 确认 Endpoints 为空

# 场景 3：kube-proxy 模式排查
kubectl get configmap kube-proxy -n kube-system -o yaml | grep mode
kubectl logs -n kube-system -l k8s-app=kube-proxy | grep -i "mode\|using"

# 如果使用 iptables 模式
iptables -t nat -L KUBE-SERVICES | head -20

# 如果使用 IPVS 模式
ipvsadm -Ln | head -20
```

---

## 🎯 面试题精选

### 题目 1：Kubernetes Service 的四种类型分别是什么？各有什么特点？

**参考答案**：

1. **ClusterIP**：默认类型，分配集群内部虚拟 IP，仅集群内可访问。通过 kube-proxy 实现负载均衡。
2. **NodePort**：在 ClusterIP 基础上，在每个节点上开放一个端口（30000-32767），外部可通过 `<NodeIP>:<NodePort>` 访问。
3. **LoadBalancer**：在 NodePort 基础上，自动创建云厂商的负载均衡器，分配外部 IP。适合生产环境。
4. **ExternalName**：将 Service 映射到外部 DNS 名称（CNAME），不分配 ClusterIP。用于引用外部服务。

### 题目 2：kube-proxy 的 iptables 模式和 IPVS 模式有什么区别？

**参考答案**：

| 维度 | iptables | IPVS |
|------|----------|------|
| 查找复杂度 | O(n) 线性匹配 | O(1) 哈希表 |
| 规则更新 | 全量刷新 | 增量更新 |
| 负载均衡算法 | 概率随机 | 支持 rr/lc/dh/sh 等 |
| 最大规模 | ~5000 Service | ~10000+ Service |
| 性能 | 规则多时下降 | 稳定高性能 |

IPVS 适合大规模集群，iptables 适合中小规模集群。

### 题目 3：Headless Service 和普通 Service 有什么区别？

**参考答案**：

- **普通 Service**：分配 ClusterIP，DNS 解析返回 ClusterIP，kube-proxy 负责负载均衡。
- **Headless Service**：`clusterIP: None`，不分配 ClusterIP，DNS 解析直接返回所有 Pod IP 列表。

Headless Service 适用于：
- StatefulSet：需要稳定的网络标识
- 客户端负载均衡：客户端自行选择后端
- 服务发现：需要知道所有 Pod 地址

### 题目 4：什么是 externalTrafficPolicy？Local 和 Cluster 有什么区别？

**参考答案**：

`externalTrafficPolicy` 控制外部流量的转发策略：

- **Cluster（默认）**：流量可以转发到任意节点上的 Pod，可能多一跳网络延迟，丢失源 IP，但流量分布均匀。
- **Local**：流量只转发到本节点上的 Pod，保留源 IP，减少延迟，但流量分布不均匀（如果某节点没有 Pod，流量会被丢弃）。

### 题目 5：如何排查 Service 无法访问的问题？

**参考答案**：

排查步骤：
1. **检查 Service**：`kubectl get svc <name>` 确认 Service 存在
2. **检查 Endpoints**：`kubectl get endpoints <name>` 确认有后端 Pod
3. **检查 Pod 状态**：Pod 必须处于 Running 且通过 Readiness Probe
4. **检查标签匹配**：Service selector 必须与 Pod labels 匹配
5. **检查端口**：Service port 和 targetPort 必须正确
6. **检查 kube-proxy**：确认 kube-proxy 正常运行
7. **检查 DNS**：`nslookup <service-name>` 确认 DNS 解析正常
8. **检查网络策略**：NetworkPolicy 可能阻止了流量

### 题目 6：Service 的 sessionAffinity 有哪几种？如何实现？

**参考答案**：

Kubernetes 原生支持两种 sessionAffinity：
- **None**（默认）：不启用会话保持
- **ClientIP**：基于客户端 IP 的会话保持，同一客户端 IP 的请求总是转发到同一 Pod

实现原理：
- iptables 模式：使用 recent 模块记录客户端 IP
- IPVS 模式：使用 sh（Source Hashing）算法

更高级的会话保持（基于 Cookie/Header）需要使用服务网格（如 Istio）或 Ingress Controller。

### 题目 7：Endpoints 和 EndpointSlice 有什么区别？

**参考答案**：

- **Endpoints**：传统的端点对象，所有 Pod IP 存储在单个对象中。大规模集群中，每次变更都需要全量更新，对 etcd 和 kube-proxy 压力大。
- **EndpointSlice**（Kubernetes 1.21+默认）：将端点分片存储（每个 Slice 最多 100 个 Endpoint），支持增量更新，性能更好。还支持拓扑感知路由。

### 题目 8：kube-proxy 的三种工作模式是什么？

**参考答案**：

1. **iptables 模式**（默认）：使用 iptables 规则实现 Service 到 Pod 的映射。规则线性匹配 O(n)，适合中小规模集群。
2. **IPVS 模式**：使用 Linux 内核 IPVS 模块，哈希表查找 O(1)，支持多种负载均衡算法，适合大规模集群。
3. **eBPF 模式**（Cilium）：使用 eBPF 程序在内核网络栈中直接处理，性能最优，支持高级功能，但需要较新内核。

### 题目 9：LoadBalancer 类型的 Service 在非云环境中如何使用？

**参考答案**：

在裸金属/非云环境中，LoadBalancer 类型默认无法使用（没有云厂商 LB 集成）。解决方案：

1. **MetalLB**：最流行的开源方案，支持 L2 模式和 BGP 模式
2. **kube-vip**：轻量级方案，支持 ARP 和 BGP
3. **云厂商 LB Controller**：如 AWS Load Balancer Controller

MetalLB 配置：定义 IPAddressPool 和 L2Advertisement/BGPAdvertisement，为 Service 分配外部 IP。

### 题目 10：如何实现 Service 的金丝雀发布/流量分割？

**参考答案**：

Kubernetes 原生 Service 不支持流量分割。实现方式：

1. **多 Deployment + 同一 Service**：通过控制副本数实现流量比例（不精确）
2. **Istio VirtualService**：精确控制流量权重
3. **Nginx Ingress 注解**：`nginx.ingress.kubernetes.io/canary-weight`
4. **Argo Rollouts**：支持渐进式交付

---

## 📚 深入阅读

- [Kubernetes Service 官方文档](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [kube-proxy IPVS 模式](https://kubernetes.io/docs/reference/networking/virtual-ips/)
- [Cilium kube-proxy 替代](https://docs.cilium.io/en/stable/network/kubernetes/kubeproxy-free/)
- [MetalLB 文档](https://metallb.universe.tf/)
- [Kubernetes 网络模型](https://kubernetes.io/docs/concepts/cluster-administration/networking/)

---

## ✅ 自检清单

- [ ] 能够解释 Service 四种类型的区别和适用场景
- [ ] 理解 kube-proxy 三种模式的工作原理和优缺点
- [ ] 能够配置 Headless Service 并解释其 DNS 解析行为
- [ ] 能够配置 sessionAffinity 并理解其实现原理
- [ ] 能够排查 Service 发现问题（无 Endpoints、DNS 故障等）
- [ ] 理解 Endpoints 和 EndpointSlice 的区别
- [ ] 能够在裸金属集群中部署 MetalLB
- [ ] 知道 externalTrafficPolicy 的区别和使用场景
- [ ] 能够回答面试中关于 Service 和 kube-proxy 的高频问题
