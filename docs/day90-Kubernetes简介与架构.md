# Day 90: Kubernetes 简介与架构

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes 架构、Master/Node 组件、核心组件原理、集群安装方式
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 80-89 Docker 全部内容

---

## 🎯 学习目标

- 理解 Kubernetes 的设计哲学和核心概念
- 掌握 Master 节点四大组件（etcd、API Server、Scheduler、Controller Manager）的职责与协作
- 掌握 Node 节点组件（kubelet、kube-proxy、Container Runtime）的工作原理
- 能使用 kubeadm 搭建生产级 K8s 集群
- 理解声明式 API 与控制循环（Reconciliation Loop）的核心机制

---

## 📖 核心知识点

### 1. Kubernetes 概述

#### 1.1 什么是 Kubernetes

Kubernetes（K8s）是 Google 基于内部 Borg 系统开源的**容器编排平台**，用于自动化部署、扩展和管理容器化应用。它不是一个传统的部署工具，而是一个**分布式系统操作系统**，管理跨多个主机的容器化工作负载。

**核心价值：**

| 特性 | 说明 | SRE 意义 |
|------|------|----------|
| 自动化部署 | 声明式 API，期望状态管理 | 减少人工操作失误 |
| 自我修复 | 自动重启、替换、杀死不响应的容器 | 提高系统可用性 |
| 水平扩展 | 基于 CPU/内存/自定义指标自动扩缩 | 应对流量波动 |
| 服务发现与负载均衡 | 内置 DNS 和负载分配 | 简化网络管理 |
| 存储编排 | 自动挂载本地/云存储 | 有状态应用支持 |
| 密钥与配置管理 | Secret/ConfigMap | 安全管理敏感信息 |

#### 1.2 Kubernetes 核心设计哲学

```
┌──────────────────────────────────────────────────────────────────┐
│                    Kubernetes 设计哲学                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 声明式（Declarative）                                        │
│     "告诉系统想要什么状态，而不是怎么做"                            │
│     ┌─────────────┐      ┌─────────────┐                        │
│     │  YAML 文件   │ ───> │  K8s 控制器  │                        │
│     │ (期望状态)   │      │ (达成状态)   │                        │
│     └─────────────┘      └─────────────┘                        │
│                                                                  │
│  2. 控制循环（Reconciliation Loop）                               │
│     ┌──────────┐    观察当前状态    ┌──────────┐                  │
│     │          │ <──────────────── │          │                  │
│     │  控制器   │                   │  实际状态 │                  │
│     │          │ ────────────────> │          │                  │
│     └──────────┘    执行动作        └──────────┘                  │
│          │                                                       │
│          ▼                                                       │
│     比较 (期望状态 vs 实际状态) -> 不一致则执行动作                  │
│                                                                  │
│  3. 水平扩展优于垂直扩展                                          │
│     - 无状态应用 -> 多副本横向扩展                                 │
│     - 容器轻量级 -> 快速启停                                       │
│                                                                  │
│  4. 松耦合微服务                                                  │
│     - Pod 为最小调度单元                                          │
│     - Service 解耦网络                                            │
│     - ConfigMap/Secret 解耦配置                                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**控制循环是 Kubernetes 最核心的机制**。每个控制器都在不断地执行以下循环：

1. **Observe**（观察）：从 API Server 获取资源的当前状态
2. **Diff**（比较）：将当前状态与期望状态进行比较
3. **Act**（执行）：执行必要的操作使当前状态趋近期望状态

这个循环确保了系统具有**自愈能力**——无论发生什么故障（节点宕机、容器崩溃、网络中断），控制器都会持续尝试将系统恢复到期望状态。

**SRE 深入理解 — 控制循环的具体实例：**

```
┌──────────────────────────────────────────────────────────────────┐
│              Deployment Controller 控制循环实例                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  用户声明: replicas: 3                                           │
│                                                                  │
│  循环 1: 观察到 0 个 Pod → 创建 3 个 Pod                         │
│  循环 2: 观察到 3 个 Pod → 一致，无需操作                         │
│  循环 3: 观察到 2 个 Pod（1 个崩溃） → 创建 1 个新 Pod           │
│  循环 4: 观察到 3 个 Pod → 一致，无需操作                         │
│  循环 5: 观察到 4 个 Pod（手动多创建了） → 删除 1 个多余 Pod     │
│                                                                  │
│  关键：控制器永远不会停止循环，它持续监控并修正偏差                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 1.3 Kubernetes 与 Docker 的关系

```
┌──────────────────────────────────────────────────────────────────┐
│                    容器技术栈                                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                  Kubernetes (编排层)                       │  │
│   │    Pod / Deployment / Service / ConfigMap / ...           │  │
│   └──────────────────────────────┬───────────────────────────┘  │
│                                  │                               │
│   ┌──────────────────────────────▼───────────────────────────┐  │
│   │              Container Runtime Interface (CRI)            │  │
│   └──────────────────────────────┬───────────────────────────┘  │
│                                  │                               │
│          ┌───────────────────────┼───────────────────────┐      │
│          ▼                       ▼                       ▼      │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│   │  containerd  │     │    CRI-O     │     │  Docker Engine│   │
│   │  (推荐)      │     │  (Red Hat)   │     │  (已废弃 CRI) │   │
│   └──────┬───────┘     └──────┬───────┘     └──────┬───────┘   │
│          │                    │                     │           │
│          ▼                    ▼                     ▼           │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              Linux Kernel (namespaces, cgroups)           │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   注意：K8s 1.24 移除了 dockershim，containerd 成为默认运行时     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**关键点：**
- Kubernetes 不直接管理 Docker，而是通过 CRI（Container Runtime Interface）与容器运行时交互
- containerd 是当前生产环境推荐的容器运行时
- Docker 构建的镜像仍然可以在 K8s 中运行（OCI 标准兼容）

---

### 2. Kubernetes 整体架构

#### 2.1 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Kubernetes 集群架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────── Master 节点 ────────────────────────────────────┐    │
│   │                                                                     │    │
│   │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────┐ │    │
│   │  │  API Server │  │    etcd     │  │  Scheduler   │  │Controller│ │    │
│   │  │  (集群入口)  │  │ (数据存储)  │  │  (调度器)    │  │ Manager  │ │    │
│   │  │  :6443      │  │  :2379      │  │              │  │(控制器)  │ │    │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └────┬─────┘ │    │
│   │         │                │                │               │        │    │
│   │         └────────┬───────┴────────┬───────┘               │        │    │
│   │                  │                │                       │        │    │
│   │                  ▼                ▼                       │        │    │
│   │           ┌──────────────────────────┐                    │        │    │
│   │           │    所有组件通过 API       │ <──────────────────┘        │    │
│   │           │    Server 通信           │                             │    │
│   │           └──────────────────────────┘                             │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                           API 请求 │ kubelet 通信                            │
│                                    ▼                                        │
│   ┌─────────────────── Worker Node 1 ──────────────────────────────────┐    │
│   │                                                                     │    │
│   │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │    │
│   │  │   kubelet    │  │  kube-proxy  │  │  Container Runtime     │   │    │
│   │  │ (节点代理)   │  │ (网络代理)   │  │  (containerd/CRI-O)   │   │    │
│   │  │  :10250      │  │              │  │                        │   │    │
│   │  └──────┬───────┘  └──────┬───────┘  └────────────┬───────────┘   │    │
│   │         │                 │                        │               │    │
│   │         ▼                 ▼                        ▼               │    │
│   │  ┌────────────────────────────────────────────────────────────┐   │    │
│   │  │                    Pod 1          Pod 2          Pod 3    │   │    │
│   │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │    │
│   │  │  │ Container A │  │ Container C │  │ Container E │       │   │    │
│   │  │  │ Container B │  │ Container D │  │             │       │   │    │
│   │  │  └─────────────┘  └─────────────┘  └─────────────┘       │   │    │
│   │  └────────────────────────────────────────────────────────────┘   │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   ┌─────────────────── Worker Node 2 ──────────────────────────────────┐    │
│   │  (结构同上，运行不同的 Pod)                                          │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.2 组件通信流程

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Kubernetes 请求流转                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  用户创建 Deployment:                                                │
│                                                                      │
│  ① kubectl apply -f deployment.yaml                                 │
│       │                                                              │
│       ▼                                                              │
│  ② API Server (认证 -> 授权 -> 准入控制 -> 持久化到 etcd)             │
│       │                                                              │
│       ├──> ③ Controller Manager 检测到新 Deployment                   │
│       │         │                                                    │
│       │         ▼                                                    │
│       │    ④ Deployment Controller 创建 ReplicaSet                   │
│       │         │                                                    │
│       │         ▼                                                    │
│       │    ⑤ ReplicaSet Controller 创建 Pod（标记为 Pending）         │
│       │                                                              │
│       ├──> ⑥ Scheduler 检测到未调度的 Pod                             │
│       │         │                                                    │
│       │         ▼                                                    │
│       │    ⑦ Scheduler 选择最优节点，写入 Pod.spec.nodeName           │
│       │                                                              │
│       ├──> ⑧ 目标节点的 kubelet 检测到分配给自己的 Pod                 │
│       │         │                                                    │
│       │         ▼                                                    │
│       │    ⑨ kubelet 调用 containerd 创建容器                        │
│       │         │                                                    │
│       │         ▼                                                    │
│       │    ⑩ kubelet 持续汇报 Pod 状态给 API Server                   │
│       │                                                              │
│       └──> ⑪ kube-proxy 更新 iptables/IPVS 规则实现 Service 路由     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**SRE 关键理解：** 整个流程是**异步的**和**事件驱动的**。kubectl apply 只是将期望状态写入 etcd，后续所有组件各自通过 watch API Server 检测变化并采取行动。理解这个流程对排查问题至关重要——当 Pod 没有运行时，你需要按这个链路逐个检查每个环节。

---

### 3. Master 节点组件详解

#### 3.1 etcd — 集群的"大脑"

etcd 是一个高可用的分布式键值存储系统，是 Kubernetes 集群的**唯一数据存储后端**。所有集群状态（Pod、Service、ConfigMap、Secret 等）都存储在 etcd 中。

**架构特点：**

```
┌─────────────────────────────────────────────────────────────────┐
│                    etcd 集群架构                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    Raft 协议     ┌──────────┐                    │
│   │  etcd-1  │ <──────────────> │  etcd-2  │                    │
│   │ (Leader) │                  │(Follower) │                    │
│   └────┬─────┘                  └─────┬─────┘                   │
│        │                              │                         │
│        │         Raft 协议            │                         │
│        │    ┌──────────────────┐      │                         │
│        └───>│     etcd-3       │<─────┘                         │
│             │   (Follower)     │                                │
│             └──────────────────┘                                │
│                                                                 │
│   Raft 一致性算法：                                              │
│   - Leader 选举：集群启动或 Leader 故障时选举新 Leader             │
│   - 日志复制：Leader 将写操作复制到多数节点后才返回成功             │
│   - 安全性：已提交的日志不会被覆盖                                │
│   - 需要 (n/2)+1 节点存活才能正常工作（3 节点容忍 1 故障）        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**关键特性：**

| 特性 | 说明 |
|------|------|
| 一致性 | 基于 Raft 协议，强一致性保证 |
| 高可用 | 建议 3 或 5 节点（奇数），容忍 (n-1)/2 故障 |
| 性能 | 读操作可从任意节点，写操作必须经过 Leader |
| 数据模型 | 分层键值存储，支持前缀查询和 watch |
| 安全性 | 支持 TLS 加密和 RBAC 访问控制 |

**etcd 常用运维命令：**

```bash
# 查看集群健康状态
etcdctl endpoint health --cluster

# 查看集群成员
etcdctl member list --write-out=table

# 备份 etcd 数据（SRE 必备操作）
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-$(date +%Y%m%d).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# 验证备份
etcdctl snapshot status /backup/etcd-20260503.db --write-out=table

# 查看 etcd 数据库大小
etcdctl endpoint status --write-out=table

# 查看某个 key 的内容
etcdctl get /registry/pods/default/ --prefix --keys-only
```

**SRE 实战 — etcd 故障排查：**

```bash
# 场景：集群无法创建新资源，kubectl 报错 "connection refused"
# 排查步骤：

# 1. 检查 etcd Pod 状态
kubectl get pods -n kube-system -l component=etcd

# 2. 检查 etcd 日志
kubectl logs -n kube-system etcd-master-01

# 3. 检查 etcd 磁盘空间（etcd 默认 2GB 空间限制）
etcdctl endpoint status --write-out=table
# 如果 DB SIZE 接近 2GB，需要执行碎片整理

# 4. 碎片整理（在线操作，不中断服务）
etcdctl defrag --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# 5. 清理历史版本（压缩）
etcdctl compact $(etcdctl endpoint status --write-out=json | jq '.[0].Status.header.revision')
```

#### 3.2 API Server — 集群的"网关"

API Server（kube-apiserver）是 Kubernetes 控制平面的**前端**，所有组件之间的通信都通过它进行。它是唯一直接与 etcd 交互的组件。

**请求处理流程：**

```
┌──────────────────────────────────────────────────────────────────┐
│                   API Server 请求处理流程                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   客户端请求 (kubectl / kubelet / Controller Manager)             │
│         │                                                        │
│         ▼                                                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  1. 认证 (Authentication)                                │   │
│   │     - X.509 客户端证书                                   │   │
│   │     - Bearer Token (ServiceAccount)                      │   │
│   │     - OpenID Connect (OIDC)                              │   │
│   │     - Webhook Token 认证                                 │   │
│   └──────────────────────────┬──────────────────────────────┘   │
│                              ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  2. 授权 (Authorization)                                 │   │
│   │     - RBAC (Role-Based Access Control) — 推荐             │   │
│   │     - ABAC (Attribute-Based)                             │   │
│   │     - Webhook                                            │   │
│   │     - Node 授权模式                                      │   │
│   └──────────────────────────┬──────────────────────────────┘   │
│                              ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  3. 准入控制 (Admission Control)                         │   │
│   │     Mutating Admission Webhooks ──> 修改请求              │   │
│   │           │                                               │   │
│   │           ▼                                               │   │
│   │     Validating Admission Webhooks ──> 校验请求            │   │
│   │     内置控制器: NamespaceLifecycle, ResourceQuota, ...    │   │
│   └──────────────────────────┬──────────────────────────────┘   │
│                              ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  4. 持久化到 etcd                                        │   │
│   └──────────────────────────┬──────────────────────────────┘   │
│                              ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  5. 返回响应给客户端                                      │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**API Server 核心特性：**

- **无状态**：API Server 本身不存储数据，所有状态在 etcd 中
- **Watch 机制**：其他组件通过 Watch API 监听资源变化，避免轮询
- **聚合层**：支持通过 Aggregated API 扩展自定义资源
- **审计日志**：记录所有 API 请求，安全合规必备

```bash
# 查看 API Server 配置
kubectl get pod -n kube-system kube-apiserver-master -o yaml

# 常用启动参数
# --etcd-servers=https://127.0.0.1:2379
# --authorization-mode=Node,RBAC
# --enable-admission-plugins=NamespaceLifecycle,NodeRestriction,ResourceQuota
# --audit-log-path=/var/log/kubernetes/audit.log
# --audit-log-maxage=30
# --audit-log-maxbackup=10
# --audit-log-maxsize=100

# 测试 API Server 健康
kubectl get --raw /healthz
kubectl get --raw /readyz

# 查看 API 资源列表
kubectl api-resources
kubectl api-versions

# 查看集群信息
kubectl cluster-info
kubectl cluster-info dump
```

#### 3.3 Scheduler — 集群的"调度员"

Scheduler（kube-scheduler）负责将未调度的 Pod 分配到合适的 Node 上运行。调度过程分为两个阶段：**过滤（Filtering）** 和 **打分（Scoring）**。

**调度流程：**

```
┌──────────────────────────────────────────────────────────────────┐
│                   Kubernetes 调度流程                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐    │
│   │                  待调度 Pod 列表                         │    │
│   └───────────────────────┬────────────────────────────────┘    │
│                           ▼                                      │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  阶段 1: 过滤 (Filtering / Predicate)                   │    │
│   │                                                          │    │
│   │  排除不满足条件的节点：                                    │    │
│   │  - 资源是否充足？ (CPU/Memory requests)                   │    │
│   │  - 端口是否冲突？                                         │    │
│   │  - nodeSelector/nodeAffinity 是否匹配？                  │    │
│   │  - 污点容忍 (Taint/Toleration) 是否满足？                │    │
│   │  - Pod 拓扑分布约束是否满足？                             │    │
│   │                                                          │    │
│   │  所有 Node: [N1, N2, N3, N4, N5]                        │    │
│   │  过滤后:    [N2, N4, N5]                                 │    │
│   └───────────────────────┬────────────────────────────────┘    │
│                           ▼                                      │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  阶段 2: 打分 (Scoring / Priority)                      │    │
│   │                                                          │    │
│   │  对候选节点评分：                                         │    │
│   │  - LeastRequested: 资源空闲最多的节点得分高               │    │
│   │  - BalancedResourceAllocation: CPU/Memory 使用均衡       │    │
│   │  - ImageLocality: 节点已有镜像得分高                      │    │
│   │  - SelectorSpread: 同 Service 的 Pod 分散到不同节点      │    │
│   │  - NodeAffinity: 满足亲和性规则得分高                     │    │
│   │                                                          │    │
│   │  N2: 80分, N4: 60分, N5: 75分                            │    │
│   └───────────────────────┬────────────────────────────────┘    │
│                           ▼                                      │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  阶段 3: 绑定 (Binding)                                  │    │
│   │                                                          │    │
│   │  选择得分最高的节点 N2，将 Pod 绑定到 N2                  │    │
│   │  写入 Pod.spec.nodeName = "node-02"                     │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```bash
# 查看 Pod 调度结果
kubectl get pod <pod-name> -o wide

# 查看调度失败的原因
kubectl describe pod <pod-name>
# 重点关注 Events 部分的 FailedScheduling 事件

# 查看节点资源使用情况（判断是否有足够资源调度）
kubectl describe node <node-name>
# 关注 Allocatable vs Allocated 资源

# 模拟调度（Dry Run）
kubectl create deployment nginx --image=nginx --dry-run=server -o yaml
```

#### 3.4 Controller Manager — 集群的"执行者"

Controller Manager 是多个控制器的集合，每个控制器负责一种资源类型的控制循环。它是 Kubernetes **声明式模型**的核心实现。

**主要控制器：**

```
┌──────────────────────────────────────────────────────────────────┐
│                   Controller Manager 内置控制器                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ Deployment Controller│ ── 管理 Deployment                     │
│  │  - 创建 ReplicaSet   │    确保指定数量的 Pod 副本运行          │
│  │  - 滚动更新          │                                        │
│  │  - 回滚              │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ ReplicaSet Controller│ ── 管理 ReplicaSet                     │
│  │  - 维护 Pod 副本数   │    确保指定数量的 Pod 副本运行          │
│  │  - 创建/删除 Pod     │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ StatefulSet Controller│ ── 管理有状态应用                     │
│  │  - 有序部署/扩缩     │                                        │
│  │  - 稳定的网络标识    │                                        │
│  │  - 持久存储          │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ DaemonSet Controller │ ── 管理节点守护进程                    │
│  │  - 每个节点运行一个  │                                        │
│  │  - 日志/监控/网络    │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ Node Controller      │ ── 管理节点生命周期                    │
│  │  - 节点状态监控      │                                        │
│  │  - Pod 驱逐          │    节点 NotReady 超过 5min 驱逐 Pod    │
│  │  - CIDR 分配         │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ Service Controller   │ ── 管理 LoadBalancer 类型 Service      │
│  │  - 云 LB 创建/删除   │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
│  ┌─────────────────────┐                                        │
│  │ Endpoint Controller  │ ── 维护 Endpoint 对象                  │
│  │  - 跟踪 Pod IP       │    Service 到 Pod 的映射               │
│  │  - 更新 endpoints    │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```bash
# 查看 Controller Manager 日志
kubectl logs -n kube-system kube-controller-manager-master

# 关键启动参数
# --controllers=*,bootstrapsigner,tokencleaner
# --node-monitor-period=5s
# --node-monitor-grace-period=40s
# --pod-eviction-timeout=5m0s
```

---

### 4. Worker Node 组件详解

#### 4.1 kubelet — 节点的"管家"

kubelet 是运行在每个 Worker Node 上的代理，负责管理节点上的 Pod 和容器。

```
┌──────────────────────────────────────────────────────────────────┐
│                    kubelet 职责                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                     kubelet                              │     │
│  ├────────────────────────────────────────────────────────┤     │
│  │                                                          │     │
│  │  1. Pod 管理                                             │     │
│  │     - 通过 Watch API 监听分配给本节点的 Pod               │     │
│  │     - 调用 CRI 创建/停止容器                              │     │
│  │     - 挂载 Volume                                       │     │
│  │     - 下载 Secret                                       │     │
│  │                                                          │     │
│  │  2. 健康检查                                             │     │
│  │     - 执行 Liveness Probe（存活探针）                    │     │
│  │     - 执行 Readiness Probe（就绪探针）                   │     │
│  │     - 执行 Startup Probe（启动探针）                     │     │
│  │                                                          │     │
│  │  3. 资源监控                                             │     │
│  │     - 采集节点和容器资源使用指标                          │     │
│  │     - 上报给 API Server / Metrics Server                 │     │
│  │                                                          │     │
│  │  4. 状态汇报                                             │     │
│  │     - 定期汇报节点状态（Node Heartbeat，默认 10s）       │     │
│  │     - 汇报 Pod 状态变更                                  │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  kubelet 与 CRI 交互：                                           │
│                                                                  │
│  kubelet ──gRPC──> CRI ──> containerd ──> runc ──> 容器         │
│                      │                                           │
│                      ├── Image Service (镜像管理)                │
│                      └── Runtime Service (容器生命周期)           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```bash
# kubelet 端口 10250
# 查看 kubelet 状态
systemctl status kubelet

# 查看 kubelet 日志
journalctl -u kubelet -f

# kubelet 配置文件
cat /var/lib/kubelet/config.yaml

# 关键配置参数
# cgroupDriver: systemd          # 推荐使用 systemd 作为 cgroup 驱动
# containerRuntimeEndpoint       # CRI 端点
# clusterDNS: [10.96.0.10]      # CoreDNS 地址
# clusterDomain: cluster.local   # 集群域名
# maxPods: 110                   # 每节点最大 Pod 数
# evictionHard:                  # 硬性驱逐阈值
#   memory.available: "200Mi"
#   nodefs.available: "10%"
#   imagefs.available: "15%"
```

#### 4.2 kube-proxy — 网络代理

kube-proxy 负责实现 Kubernetes Service 的网络代理功能，维护节点上的网络规则，将访问 Service 的流量转发到后端 Pod。

```
┌──────────────────────────────────────────────────────────────────┐
│                    kube-proxy 代理模式                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  模式 1: iptables (默认)                                         │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Service VIP ──> iptables DNAT 规则 ──> Pod IP         │     │
│  │                                                          │     │
│  │  优点：成熟稳定，内核原生                                 │     │
│  │  缺点：Service 数量多时规则链长，性能下降                 │     │
│  │  适用：Service 数量 < 1000                               │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  模式 2: IPVS (推荐大规模集群)                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Service VIP ──> IPVS 哈希表 ──> Pod IP                │     │
│  │                                                          │     │
│  │  优点：高性能哈希查找，支持多种负载均衡算法               │     │
│  │  缺点：需要内核支持 IPVS 模块                            │     │
│  │  算法：rr(轮询), lc(最少连接), sh(源哈希), dh(目标哈希)  │     │
│  │  适用：Service 数量 > 1000                               │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  模式 3: nftables (K8s 1.29+ 实验性)                             │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  基于 nftables 替代 iptables，性能更好                   │     │
│  │  未来可能成为默认模式                                    │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  流量转发策略：                                                    │
│  - ClusterIP: 集群内部访问                                       │
│  - NodePort: 通过节点端口暴露                                    │
│  - LoadBalancer: 云厂商负载均衡器                                │
│  - ExternalName: CNAME 映射                                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```bash
# 查看 kube-proxy 模式
kubectl get configmap -n kube-system kube-proxy -o yaml | grep mode

# 查看 iptables 规则（iptables 模式）
iptables -t nat -L KUBE-SERVICES -n

# 查看 IPVS 规则（IPVS 模式）
ipvsadm -Ln

# 查看 kube-proxy 日志
kubectl logs -n kube-system -l k8s-app=kube-proxy
```

---

### 5. 集群安装方式

#### 5.1 kubeadm — 生产级安装

kubeadm 是 Kubernetes 官方提供的集群引导工具，适合**生产环境**和**学习深入理解 K8s 组件**。

**系统要求：**

| 资源 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 磁盘 | 20 GB | 50 GB SSD |
| 系统 | Ubuntu 20.04+, CentOS 7+, RHEL 7+ | Ubuntu 22.04 LTS |
| 网络 | 节点间互通 | 独立子网 |

**安装步骤：**

```bash
# ============ 所有节点执行 ============

# 1. 系统准备
# 关闭 swap（K8s 要求）
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# 加载内核模块
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

# 设置内核参数
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system

# 2. 安装 containerd
sudo apt-get update
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
# 修改 SystemdCgroup = true
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd

# 3. 安装 kubeadm、kubelet、kubectl
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key \
  | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' \
  | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl

# ============ Master 节点执行 ============

# 4. 初始化 Master
sudo kubeadm init \
  --pod-network-cidr=10.244.0.0/16 \
  --service-cidr=10.96.0.0/12 \
  --apiserver-advertise-address=<master-ip>

# 5. 配置 kubectl
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

# 6. 安装网络插件（Calico）
kubectl apply -f https://docs.projectcalico.org/manifests/calico.yaml

# ============ Worker 节点执行 ============

# 7. 加入集群（使用 kubeadm init 输出的 join 命令）
sudo kubeadm join <master-ip>:6443 --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>

# ============ 验证 ============

# 8. 检查集群状态
kubectl get nodes
kubectl get pods -n kube-system
kubectl cluster-info
```

**kubeadm 证书管理：**

```bash
# 查看证书过期时间
kubeadm certs check-expiration

# 续期证书
kubeadm certs renew all

# 证书默认位置
# /etc/kubernetes/pki/apiserver.crt
# /etc/kubernetes/pki/apiserver.key
# /etc/kubernetes/pki/ca.crt
# /etc/kubernetes/pki/ca.key
```

#### 5.2 k3s — 轻量级安装

k3s 是 Rancher 开发的轻量级 Kubernetes 发行版，适合**边缘计算**、**IoT**、**CI/CD** 和**开发环境**。

```
┌──────────────────────────────────────────────────────────────────┐
│                    k3s vs kubeadm 对比                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  特性              k3s                 kubeadm                   │
│  ─────────────     ─────────────       ─────────────             │
│  二进制大小        < 100MB             ~1GB (全组件)              │
│  内存需求          512MB+              2GB+                      │
│  安装时间          < 1 分钟            10-30 分钟                │
│  默认存储          SQLite (可换 etcd)  etcd                      │
│  默认网络          flannel             需自选 (Calico/Cilium)    │
│  默认 Ingress      Traefik             无 (需自装)               │
│  运行时            containerd          containerd                │
│  多节点支持        是                  是                        │
│  生产就绪          边缘/轻量场景       通用生产环境               │
│  CNCF 认证         是                  是                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```bash
# k3s 安装 — Master 节点
curl -sfL https://get.k3s.io | sh -s - server \
  --disable traefik \
  --write-kubeconfig-mode 644

# 获取 join token
sudo cat /var/lib/rancher/k3s/server/node-token

# k3s 安装 — Worker 节点
curl -sfL https://get.k3s.io | K3S_URL=https://<master-ip>:6443 \
  K3S_TOKEN=<node-token> sh -s - agent

# k3s 使用 kubectl
k3s kubectl get nodes
# 或配置 kubeconfig
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl get nodes

# k3s 卸载
/usr/local/bin/k3s-uninstall.sh   # server
/usr/local/bin/k3s-agent-uninstall.sh  # agent
```

#### 5.3 minikube — 本地开发

minikube 是 Kubernetes 官方提供的本地开发工具，在单机上运行一个单节点集群。

```bash
# 安装 minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 启动集群（推荐使用 Docker 驱动）
minikube start --driver=docker --cpus=4 --memory=4096

# 启用插件
minikube addons enable metrics-server
minikube addons enable ingress
minikube addons enable dashboard

# 查看集群状态
minikube status
kubectl get nodes

# 访问服务
minikube service <service-name> --url

# 停止/删除
minikube stop
minikube delete
```

---

### 6. Kubernetes API 对象概览

```
┌──────────────────────────────────────────────────────────────────┐
│                    Kubernetes 核心 API 对象                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  工作负载 (Workloads)                                            │
│  ├── Pod                  最小调度单元                            │
│  ├── ReplicaSet           维持 Pod 副本数                         │
│  ├── Deployment           声明式管理无状态应用                    │
│  ├── StatefulSet          管理有状态应用                          │
│  ├── DaemonSet            每节点运行一个 Pod                      │
│  ├── Job                  一次性任务                              │
│  └── CronJob              定时任务                                │
│                                                                  │
│  服务发现与负载均衡                                               │
│  ├── Service              稳定的网络端点                          │
│  └── Ingress              HTTP/HTTPS 路由                        │
│                                                                  │
│  配置与存储                                                      │
│  ├── ConfigMap             非敏感配置                             │
│  ├── Secret               敏感配置                                │
│  ├── PersistentVolume      持久存储卷                             │
│  └── PersistentVolumeClaim 存储卷声明                             │
│                                                                  │
│  集群资源                                                        │
│  ├── Namespace             资源隔离                               │
│  ├── Node                  工作节点                               │
│  ├── ServiceAccount        Pod 身份                               │
│  ├── Role / ClusterRole    RBAC 角色                              │
│  └── ResourceQuota         资源配额                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 7. SRE 实战案例

#### 7.1 生产故障排查完整链路

```
┌──────────────────────────────────────────────────────────────────┐
│              SRE 故障排查决策树                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  问题：应用访问超时                                               │
│                                                                  │
│  Step 1: 检查 Pod 状态                                           │
│    ├── Pod Running? ──> Step 2                                   │
│    ├── Pod Pending? ──> 检查调度                                 │
│    │     ├── FailedScheduling: 资源不足                          │
│    │     ├── FailedScheduling: 污点/亲和性不匹配                 │
│    │     └── FailedScheduling: PVC 绑定失败                      │
│    ├── Pod CrashLoopBackOff? ──> 检查日志                        │
│    │     ├── OOMKilled: 增加内存限制                             │
│    │     ├── 启动失败: 检查镜像/配置                             │
│    │     └── 健康检查失败: 调整探针参数                          │
│    └── Pod ImagePullBackOff? ──> 检查镜像                       │
│          ├── 镜像名称错误                                        │
│          ├── 镜像仓库认证失败                                    │
│          └── 网络不通                                            │
│                                                                  │
│  Step 2: 检查 Service/Endpoints                                 │
│    ├── Endpoints 为空? ──> Pod 未就绪 (Readiness Probe 失败)     │
│    ├── Endpoints 正常? ──> 检查 kube-proxy                       │
│    └── Service 类型正确? ──> ClusterIP/NodePort/LB               │
│                                                                  │
│  Step 3: 检查网络                                                │
│    ├── DNS 解析正常? ──> nslookup kubernetes.default             │
│    ├── Pod 间通信正常? ──> 从 Pod 内 curl 其他服务               │
│    └── 外部访问正常? ──> 检查 Ingress/LB 配置                    │
│                                                                  │
│  Step 4: 检查节点                                                │
│    ├── 节点 Ready? ──> kubectl get nodes                        │
│    ├── 资源充足? ──> kubectl top nodes                          │
│    └── kubelet 正常? ──> systemctl status kubelet               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 7.2 API Server 性能优化

```yaml
# API Server 审计日志配置
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # 不记录只读的健康检查请求
  - level: None
    nonResourceURLs:
      - /healthz*
      - /readyz*
      - /livez*

  # 不记录 kube-system 命名空间的只读请求
  - level: None
    resources:
      - group: ""
        resources: ["configmaps", "endpoints"]
    namespaces: ["kube-system"]

  # 记录所有写操作
  - level: Metadata
    verbs: ["create", "update", "patch", "delete"]

  # 其他请求只记录元数据
  - level: Metadata
```

---

## 💻 实战练习

### 练习 1：使用 kubeadm 搭建集群

**目标：** 搭建一个 1 Master + 2 Worker 的 K8s 集群

```bash
# 步骤 1: 准备 3 台虚拟机（或使用 multipass 快速创建）
multipass launch --name k8s-master --cpus 2 --mem 4G --disk 20G
multipass launch --name k8s-worker1 --cpus 2 --mem 4G --disk 20G
multipass launch --name k8s-worker2 --cpus 2 --mem 4G --disk 20G

# 步骤 2: 在所有节点上安装 containerd 和 kubeadm（参考 5.1 节）

# 步骤 3: 初始化 Master 并安装网络插件

# 步骤 4: Worker 节点加入集群

# 步骤 5: 验证集群
kubectl get nodes
kubectl get pods -n kube-system
kubectl run test --image=nginx
kubectl get pod test -o wide  # 确认 Pod 调度到某个 Worker 节点
kubectl delete pod test
```

### 练习 2：探索集群组件

**目标：** 理解各组件之间的协作关系

```bash
# 任务 1: 查看所有系统组件
kubectl get pods -n kube-system -o wide
# 记录每个组件运行在哪个节点

# 任务 2: 创建一个 Pod 并观察调度过程
kubectl run nginx --image=nginx --dry-run=client -o yaml > pod.yaml
# 编辑 pod.yaml 添加资源限制
kubectl apply -f pod.yaml
kubectl describe pod nginx  # 观察 Events 部分

# 任务 3: 查看 API Server 的资源操作日志
kubectl get events --sort-by='.lastTimestamp'
kubectl get events --field-selector involvedObject.name=nginx

# 任务 4: 查看节点资源分配
kubectl describe node <node-name> | grep -A 10 "Allocated resources"
```

### 练习 3：故障排查挑战

**目标：** 排查预设的集群问题

```bash
# 场景 1: Pod 一直处于 Pending 状态
# 创建一个资源需求极大的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: hungry-pod
spec:
  containers:
  - name: hungry
    image: nginx
    resources:
      requests:
        cpu: "100"
        memory: "100Gi"
EOF
kubectl describe pod hungry-pod  # 分析 Pending 原因
# 修复：调整资源请求或添加更多节点

# 场景 2: Node 状态为 NotReady
# 模拟 kubelet 故障
sudo systemctl stop kubelet
kubectl get nodes  # 观察节点状态变化
kubectl describe node <node-name>  # 查看 Conditions
# 恢复：sudo systemctl start kubelet
# 观察 Pod 驱逐过程（默认 5 分钟后开始驱逐）

# 场景 3: API Server 无法访问
# 检查 API Server Pod 状态
kubectl get pods -n kube-system -l component=kube-apiserver
# 检查 API Server 日志
kubectl logs -n kube-system kube-apiserver-$(hostname)
# 检查证书是否过期
kubeadm certs check-expiration
```

---

## 🎯 面试题精选

### 1. Kubernetes 的核心组件有哪些？各自的作用是什么？

**参考答案：**

Master 节点组件：
- **etcd**：分布式键值存储，保存集群所有状态数据
- **API Server**：集群入口，所有组件通过它通信，处理认证、授权、准入控制
- **Scheduler**：将未调度的 Pod 分配到合适的 Node，经过过滤和打分两个阶段
- **Controller Manager**：运行各种控制器，执行控制循环确保实际状态匹配期望状态

Worker 节点组件：
- **kubelet**：节点代理，管理 Pod 生命周期，执行健康检查，汇报节点状态
- **kube-proxy**：实现 Service 网络代理，维护 iptables/IPVS 规则
- **Container Runtime**：容器运行时（containerd/CRI-O），负责容器的创建和管理

### 2. 什么是控制循环（Reconciliation Loop）？为什么它是 Kubernetes 的核心？

**参考答案：**

控制循环是 Kubernetes 的核心设计模式，持续执行"观察-比较-执行"的循环：
1. **Observe**：控制器通过 Watch API 监听资源的实际状态
2. **Diff**：将实际状态与用户在 YAML 中声明的期望状态比较
3. **Act**：如果两者不一致，执行操作使实际状态趋近期望状态

它是核心的原因：
- 实现了**自愈能力**：Pod 崩溃会自动重启，节点宕机会自动迁移
- 实现了**声明式管理**：用户只需描述期望状态，系统自动达成
- 实现了**最终一致性**：即使暂时不一致，系统也会持续尝试达到期望状态

### 3. etcd 集群应该部署几个节点？为什么？

**参考答案：**

推荐 **3 或 5 个节点**（必须是奇数）。

原因：etcd 使用 Raft 一致性算法，需要 (n/2)+1 个节点形成多数派才能正常工作。
- 3 节点：容忍 1 个节点故障
- 5 节点：容忍 2 个节点故障
- 不推荐偶数节点：4 节点也只能容忍 1 个故障（和 3 节点一样），但增加了网络开销

### 4. kubelet 和 API Server 之间是如何通信的？

**参考答案：**

kubelet 通过以下方式与 API Server 交互：
- **Watch 机制**：kubelet Watch API Server 上分配给自己节点的 Pod 变化
- **汇报状态**：kubelet 定期（默认 10s）向 API Server 发送心跳（Node Heartbeat），汇报节点状态
- **双向认证**：使用 X.509 证书进行 TLS 双向认证，端口 10250
- **Pod 状态同步**：当 Pod 状态变化时（容器启动、健康检查失败等），kubelet 更新 API Server 中的 Pod status

注意：kubelet 不通过 Controller Manager 通信，而是直接与 API Server 交互。

### 5. kubeadm、k3s、minikube 分别适合什么场景？

**参考答案：**

| 工具 | 适用场景 | 特点 |
|------|---------|------|
| kubeadm | 生产环境、学习组件 | 官方工具，完整组件，需要手动配置网络和存储 |
| k3s | 边缘计算、IoT、轻量级生产 | 单二进制 <100MB，内置 SQLite，安装简单 |
| minikube | 本地开发、学习 | 单节点，支持多种驱动（Docker/VM），内置插件 |

选择建议：
- 学习 K8s 架构：kubeadm（理解每个组件）
- 快速原型开发：minikube（一键启动）
- 边缘/轻量生产：k3s（资源占用少）
- 生产环境：kubeadm 或云厂商托管服务（EKS/GKE/AKS）

### 6. API Server 的准入控制（Admission Control）是什么？有哪些类型？

**参考答案：**

准入控制是 API Server 处理请求的第三道关卡（认证 -> 授权 -> 准入控制），在对象持久化到 etcd 之前对请求进行拦截和修改。

两种类型：
- **Mutating Admission Webhooks**：可以修改请求对象（如自动注入 sidecar 容器、添加标签）
- **Validating Admission Webhooks**：只能接受或拒绝请求（如校验镜像来源、资源限制）

执行顺序：先执行 Mutating，再执行 Validating。

常用内置准入控制器：
- `NamespaceLifecycle`：防止在不存在的 Namespace 中创建资源
- `ResourceQuota`：强制执行资源配额
- `NodeRestriction`：限制 kubelet 只能修改自己的 Node 和 Pod
- `LimitRanger`：强制执行默认资源限制

### 7. kube-proxy 的三种模式有什么区别？

**参考答案：**

| 模式 | 实现方式 | 性能 | 适用规模 | 状态 |
|------|---------|------|---------|------|
| iptables | Linux iptables 规则 | O(n) 线性查找 | <1000 Service | 默认 |
| IPVS | Linux IPVS 内核模块 | O(1) 哈希查找 | >1000 Service | 推荐大规模 |
| nftables | nftables 规则 | 比 iptables 更好 | 任意规模 | 1.29+ 实验性 |

iptables 模式的主要问题是：Service 数量增多时，规则链变长，每次规则更新需要全量刷新，性能下降明显。IPVS 使用哈希表实现 O(1) 查找，且支持多种负载均衡算法。

### 8. 为什么 Kubernetes 要求关闭 swap？

**参考答案：**

Kubernetes 要求关闭 swap 的原因：
1. **调度准确性**：kubelet 通过监控内存使用率来决定是否驱逐 Pod。如果启用了 swap，实际可用内存变得不可预测，导致调度决策不准确。
2. **性能保证**：swap 使用磁盘作为虚拟内存，性能远低于物理内存。对于延迟敏感的容器化应用，swap 会导致严重的性能抖动。
3. **QoS 保障**：Kubernetes 的 QoS（服务质量）机制依赖于精确的内存管理。swap 会破坏 Guaranteed、Burstable、BestEffort 三级 QoS 的语义。

### 9. 如何备份和恢复 etcd？

**参考答案：**

```bash
# 备份
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# 恢复
# 1. 停止 API Server
# 2. 恢复快照
ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd-snapshot.db \
  --data-dir=/var/lib/etcd-restore
# 3. 修改 etcd 配置指向新数据目录
# 4. 重启 etcd 和 API Server
```

SRE 最佳实践：将 etcd 备份自动化，每日备份并存储到远程位置（S3/GCS），定期测试恢复流程。

### 10. 如何判断 Kubernetes 集群是否健康？

**参考答案：**

```bash
# 1. 检查节点状态
kubectl get nodes  # 所有节点应为 Ready

# 2. 检查系统组件
kubectl get pods -n kube-system  # 所有 Pod 应为 Running

# 3. 检查组件健康端点
kubectl get --raw /healthz
kubectl get --raw /readyz
kubectl get --raw /livez

# 4. 检查 etcd 健康
etcdctl endpoint health --cluster

# 5. 检查证书过期
kubeadm certs check-expiration

# 6. 检查事件
kubectl get events -A --sort-by='.lastTimestamp' | tail -20

# 7. 检查资源使用
kubectl top nodes
kubectl top pods -A
```

---

## 📚 深入阅读

- [Kubernetes 官方文档 - 概念](https://kubernetes.io/zh-cn/docs/concepts/)
- [Kubernetes 官方文档 - 组件](https://kubernetes.io/zh-cn/docs/concepts/overview/components/)
- [etcd 官方文档](https://etcd.io/docs/)
- [Kubernetes 官方文档 - 使用 kubeadm 创建集群](https://kubernetes.io/zh-cn/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/)
- [k3s 官方文档](https://docs.k3s.io/)
- [CNCF Kubernetes 认证管理员 (CKA) 考试大纲](https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/)

---

## ✅ 自检清单

- [ ] 能画出 Kubernetes 整体架构图并解释每个组件的职责
- [ ] 理解控制循环（Reconciliation Loop）的工作原理和重要性
- [ ] 知道 etcd 使用 Raft 一致性算法，了解其容错能力
- [ ] 理解 API Server 的请求处理流程（认证 -> 授权 -> 准入控制 -> 持久化）
- [ ] 理解 Scheduler 的两阶段调度（过滤 -> 打分）
- [ ] 知道 kubelet 的主要职责（Pod 管理、健康检查、状态汇报）
- [ ] 了解 kube-proxy 的 iptables 和 IPVS 模式的区别
- [ ] 能使用 kubeadm 搭建一个可用的 K8s 集群
- [ ] 了解 k3s 和 minikube 的适用场景
- [ ] 能通过 kubectl 命令检查集群健康状态
