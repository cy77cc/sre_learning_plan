# Day 137: Kubernetes 监控

> 阶段五：可观测性 | Week 19 | Day 2

## 今日学习目标
1. 理解 Kubernetes 监控体系架构与各组件职责
2. 掌握 kube-state-metrics 的部署与核心指标
3. 掌握 node-exporter 的部署与主机级指标采集
4. 理解 cAdvisor 容器指标采集机制
5. 掌握 kube-prometheus-stack Helm Chart 的安装与配置
6. 能够导入和定制 K8s 专用 Grafana 仪表盘
7. 掌握资源 Request/Limit 监控与 Pod 重启追踪
8. 了解 etcd/apiserver/scheduler/controller-manager 指标采集

## 核心知识点

### 1. Kubernetes 监控体系架构

#### 1.1 整体架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Kubernetes 监控体系架构                              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    数据采集层                                  │   │
│  │                                                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ kube-state-  │  │ node-exporter│  │   cAdvisor    │      │   │
│  │  │ metrics      │  │              │  │  (内置Kubelet)│      │   │
│  │  │              │  │              │  │              │      │   │
│  │  │ K8s 对象状态  │  │ 主机级指标   │  │ 容器级指标   │      │   │
│  │  │ - Deployment │  │ - CPU        │  │ - CPU Usage  │      │   │
│  │  │ - Pod        │  │ - Memory     │  │ - Mem Usage  │      │   │
│  │  │ - Service    │  │ - Disk       │  │ - Network    │      │   │
│  │  │ - Node       │  │ - Network    │  │ - Filesystem │      │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │   │
│  │         │                 │                 │                │   │
│  │         └─────────────────┼─────────────────┘                │   │
│  │                           │                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ kubelet      │  │ etcd         │  │ apiserver    │      │   │
│  │  │ metrics      │  │ metrics      │  │ metrics      │      │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │   │
│  └─────────┼─────────────────┼─────────────────┼───────────────┘   │
│            │                 │                 │                    │
│            └─────────────────┼─────────────────┘                    │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Prometheus Server                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │  TSDB 存储   │  │ PromQL 查询  │  │ Recording    │      │   │
│  │  │              │  │              │  │ Rules        │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                        │
│            ┌──────────────┼──────────────┐                         │
│            ▼              ▼              ▼                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │   Grafana    │ │  Alertmanager│ │  其他消费方   │               │
│  │  可视化      │ │  告警管理    │ │  (API/脚本)  │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 三大数据源对比

```
┌────────────────┬──────────────────┬──────────────────┬──────────────────┐
│ 特性            │ kube-state-metrics│ node-exporter   │ cAdvisor         │
├────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ 数据来源        │ K8s API Server   │ 主机 /proc /sys │ 容器运行时        │
│ 采集对象        │ K8s 对象状态     │ 主机系统         │ 容器              │
│ 部署方式        │ Deployment       │ DaemonSet        │ 内置 Kubelet      │
│ 默认端口        │ 8080 / 8081      │ 9100             │ 10250 (kubelet)   │
│ 指标前缀        │ kube_*           │ node_*           │ container_*       │
│ 典型指标        │ pod_status       │ cpu_seconds      │ cpu_usage_total   │
│                │ deployment_replicas│ memory_bytes    │ memory_working_set│
│ 更新频率        │ 持续 watch       │ 15s              │ 15s               │
│ 资源消耗        │ 低               │ 低               │ 低（内置）        │
└────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

### 2. kube-state-metrics

#### 2.1 概述与架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                  kube-state-metrics 架构                              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Kubernetes API Server                      │   │
│  │                                                             │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │   │
│  │  │  Pods   │ │ Deploy  │ │  Nodes  │ │Services │          │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │   │
│  └───────┼──────────┼──────────┼──────────┼──────────────────┘   │
│          │          │          │          │                        │
│          └──────────┼──────────┼──────────┘                        │
│                     │          │                                    │
│                     ▼          ▼                                    │
│          ┌─────────────────────────────┐                           │
│          │    kube-state-metrics       │                           │
│          │                             │                           │
│          │  - Watch K8s API 对象       │                           │
│          │  - 转换为 Prometheus 指标    │                           │
│          │  - 暴露 /metrics 端点       │                           │
│          │                             │                           │
│          │  端口: 8080 (metrics)       │                           │
│          │  端口: 8081 (telemetry)     │                           │
│          └──────────────┬──────────────┘                           │
│                         │                                          │
│                         ▼                                          │
│               ┌──────────────────┐                                 │
│               │    Prometheus    │                                  │
│               └──────────────────┘                                 │
│                                                                     │
│  核心特性：                                                          │
│  ├── 只读：只从 API Server 读取，不修改任何状态                      │
│  ├── 无状态：不存储数据，只转换格式                                  │
│  ├── 声明式：指标名称和标签遵循 K8s 命名规范                        │
│  ├── 自动发现：Watch 机制，实时感知对象变化                          │
│  └── 可扩展：支持自定义资源（CRD）指标                              │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.2 安装 kube-state-metrics

```bash
# 方式 1: 使用 Helm 安装（推荐）
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-state-metrics prometheus-community/kube-state-metrics \
  --namespace monitoring \
  --create-namespace \
  --set prometheusScrape=true \
  --set image.tag=v2.12.0 \
  --set resources.limits.cpu=200m \
  --set resources.limits.memory=256Mi \
  --set resources.requests.cpu=100m \
  --set resources.requests.memory=128Mi

# 方式 2: 使用 kubectl 安装
kubectl apply -f https://raw.githubusercontent.com/kubernetes/kube-state-metrics/main/examples/standard/deployment.yaml

# 方式 3: 使用 kube-prometheus-stack（包含在内）
# 见后续 kube-prometheus-stack 安装章节
```

```yaml
# 方式 4: 自定义 Helm values 安装
# values-kube-state-metrics.yaml
prometheusScrape: true

# 自定义指标标签
customLabels:
  team: sre
  environment: production

# 资源配置
resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

# 采集器配置
collectors:
  - certificatesigningrequests
  - configmaps
  - cronjobs
  - daemonsets
  - deployments
  - endpoints
  - horizontalpodautoscalers
  - ingresses
  - jobs
  - leases
  - limitranges
  - mutatingwebhookconfigurations
  - namespaces
  - networkpolicies
  - nodes
  - persistentvolumeclaims
  - persistentvolumes
  - poddisruptionbudgets
  - pods
  - replicasets
  - replicationcontrollers
  - resourcequotas
  - secrets
  - services
  - statefulsets
  - storageclasses
  - validatingwebhookconfigurations
  - volumeattachments

# 命名空间限制（只监控特定命名空间）
namespaces: ""
# 或者限制命名空间列表
# namespaces: "default,production,staging"

# RBAC 配置
rbac:
  create: true

# ServiceAccount
serviceAccount:
  create: true
  name: kube-state-metrics
```

#### 2.3 核心指标详解

```
┌─────────────────────────────────────────────────────────────────────┐
│                  kube-state-metrics 核心指标                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Pod 指标：                                                         │
│  ├── kube_pod_info                    Pod 基本信息                  │
│  ├── kube_pod_status_phase            Pod 阶段（Running/Pending等）│
│  ├── kube_pod_status_ready            Pod 就绪状态                 │
│  ├── kube_pod_status_running          Pod 运行中                   │
│  ├── kube_pod_container_status_terminated_reason  终止原因         │
│  ├── kube_pod_container_status_waiting_reason    等待原因          │
│  ├── kube_pod_container_status_restarts_total    重启次数          │
│  ├── kube_pod_container_resource_requests        资源请求          │
│  ├── kube_pod_container_resource_limits          资源限制          │
│  ├── kube_pod_created                 Pod 创建时间                 │
│  └── kube_pod_completion_time         Pod 完成时间                 │
│                                                                     │
│  Deployment 指标：                                                  │
│  ├── kube_deployment_spec_replicas     期望副本数                   │
│  ├── kube_deployment_status_replicas   当前副本数                   │
│  ├── kube_deployment_status_replicas_available  可用副本数          │
│  ├── kube_deployment_status_replicas_unavailable 不可用副本数      │
│  ├── kube_deployment_status_replicas_updated  已更新副本数          │
│  ├── kube_deployment_status_observed_generation 观察到的代数        │
│  └── kube_deployment_created           创建时间                     │
│                                                                     │
│  DaemonSet 指标：                                                   │
│  ├── kube_daemonset_status_desired_number_scheduled  期望调度数     │
│  ├── kube_daemonset_status_number_ready             就绪数          │
│  ├── kube_daemonset_status_number_unavailable       不可用数        │
│  ├── kube_daemonset_status_number_missed            错过数          │
│  └── kube_daemonset_status_updated_number_scheduled 已更新数        │
│                                                                     │
│  Node 指标：                                                        │
│  ├── kube_node_info                    节点信息                     │
│  ├── kube_node_status_condition        节点状态条件                 │
│  ├── kube_node_status_allocatable      可分配资源                   │
│  ├── kube_node_spec_unschedulable      是否不可调度                 │
│  ├── kube_node_role                    节点角色                     │
│  └── kube_node_created                 节点创建时间                 │
│                                                                     │
│  Job / CronJob 指标：                                               │
│  ├── kube_job_complete                 Job 完成状态                 │
│  ├── kube_job_failed                   Job 失败状态                 │
│  ├── kube_job_status_completion_time   完成时间                     │
│  ├── kube_cronjob_spec_schedule        调度计划                     │
│  ├── kube_cronjob_status_active        活跃任务数                   │
│  └── kube_cronjob_status_last_schedule_time  上次调度时间           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.4 常用 PromQL 查询

```promql
# ===== Pod 级别查询 =====

# 所有 Pod 的重启次数
kube_pod_container_status_restarts_total

# 最近 1 小时内重启过的 Pod
kube_pod_container_status_restarts_total
  - kube_pod_container_status_restarts_total offset 1h > 0

# 非 Running 状态的 Pod
kube_pod_status_phase{phase!="Running"} == 1

# 非 Ready 的 Pod
kube_pod_status_ready{condition="false"} == 1

# Pod 资源请求汇总（按命名空间）
sum(kube_pod_container_resource_requests{resource="cpu"}) by (namespace)
sum(kube_pod_container_resource_requests{resource="memory"}) by (namespace)

# Pod 资源限制汇总（按命名空间）
sum(kube_pod_container_resource_limits{resource="cpu"}) by (namespace)
sum(kube_pod_container_resource_limits{resource="memory"}) by (namespace)

# ===== Deployment 级别查询 =====

# Deployment 副本数不一致（期望 != 实际）
kube_deployment_spec_replicas
  != kube_deployment_status_replicas_available

# Deployment 不可用副本数 > 0
kube_deployment_status_replicas_unavailable > 0

# Deployment 滚动更新进度
kube_deployment_status_replicas_updated
  / kube_deployment_spec_replicas * 100

# ===== DaemonSet 级别查询 =====

# DaemonSet 未就绪节点数
kube_daemonset_status_desired_number_scheduled
  - kube_daemonset_status_number_ready

# DaemonSet 调度失败
kube_daemonset_status_desired_number_scheduled
  - kube_daemonset_status_number_scheduled > 0

# ===== Node 级别查询 =====

# 节点 NotReady
kube_node_status_condition{condition="Ready",status="true"} == 0

# 节点可分配资源
kube_node_status_allocatable{resource="cpu"}
kube_node_status_allocatable{resource="memory"}

# 节点角色
kube_node_role

# ===== Job / CronJob 查询 =====

# 失败的 Job
kube_job_failed > 0

# CronJob 上次调度时间距现在多久
time() - kube_cronjob_status_last_schedule_time
```

### 3. node-exporter

#### 3.1 部署架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                  node-exporter DaemonSet 部署                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Kubernetes Cluster                        │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │                    Node 1                             │   │   │
│  │  │  ┌──────────────────┐                               │   │   │
│  │  │  │  node-exporter   │  DaemonSet Pod (hostNetwork)  │   │   │
│  │  │  │  :9100/metrics   │                               │   │   │
│  │  │  │                  │                               │   │   │
│  │  │  │  采集:            │                               │   │   │
│  │  │  │  - /proc/stat    │  CPU 指标                     │   │   │
│  │  │  │  - /proc/meminfo │  内存指标                     │   │   │
│  │  │  │  - /proc/diskstats│ 磁盘指标                     │   │   │
│  │  │  │  - /proc/net/    │  网络指标                     │   │   │
│  │  │  │  - /sys/         │  系统指标                     │   │   │
│  │  │  └──────────────────┘                               │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │                    Node 2                             │   │   │
│  │  │  ┌──────────────────┐                               │   │   │
│  │  │  │  node-exporter   │                               │   │   │
│  │  │  │  :9100/metrics   │                               │   │   │
│  │  │  └──────────────────┘                               │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │                    Node N                             │   │   │
│  │  │  ┌──────────────────┐                               │   │   │
│  │  │  │  node-exporter   │                               │   │   │
│  │  │  │  :9100/metrics   │                               │   │   │
│  │  │  └──────────────────┘                               │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                        │
│                           ▼                                        │
│               ┌──────────────────┐                                 │
│               │    Prometheus    │                                  │
│               └──────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.2 DaemonSet 配置

```yaml
# node-exporter-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app.kubernetes.io/name: node-exporter
    app.kubernetes.io/version: v1.7.0
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: node-exporter
  template:
    metadata:
      labels:
        app.kubernetes.io/name: node-exporter
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9100"
    spec:
      hostNetwork: true
      hostPID: true
      tolerations:
        - operator: Exists
      containers:
        - name: node-exporter
          image: prom/node-exporter:v1.7.0
          args:
            - --path.procfs=/host/proc
            - --path.sysfs=/host/sys
            - --path.rootfs=/host/root
            - --collector.filesystem.mount-points-exclude=^/(dev|proc|sys|var/lib/docker/.+)($|/)
            - --collector.netclass.ignored-devices=^(veth.*)$
            - --collector.netdev.device-exclude=^(veth.*)$
          ports:
            - containerPort: 9100
              name: metrics
          resources:
            limits:
              cpu: 250m
              memory: 180Mi
            requests:
              cpu: 100m
              memory: 128Mi
          volumeMounts:
            - name: proc
              mountPath: /host/proc
              readOnly: true
            - name: sys
              mountPath: /host/sys
              readOnly: true
            - name: root
              mountPath: /host/root
              mountPropagation: HostToContainer
              readOnly: true
      volumes:
        - name: proc
          hostPath:
            path: /proc
        - name: sys
          hostPath:
            path: /sys
        - name: root
          hostPath:
            path: /
```

#### 3.3 node-exporter 核心指标

```
┌─────────────────────────────────────────────────────────────────────┐
│                  node-exporter 核心指标                               │
├──────────────┬──────────────────────────────────────────────────────┤
│ 类别          │ 核心指标                                            │
├──────────────┼──────────────────────────────────────────────────────┤
│ CPU          │ node_cpu_seconds_total (各模式CPU时间)               │
│              │ node_load1 / node_load5 / node_load15 (系统负载)     │
│              │ node_procs_running (运行中进程数)                    │
│              │ node_procs_blocked (阻塞进程数)                      │
├──────────────┼──────────────────────────────────────────────────────┤
│ 内存          │ node_memory_MemTotal_bytes (总内存)                 │
│              │ node_memory_MemAvailable_bytes (可用内存)            │
│              │ node_memory_Buffers_bytes (缓冲区)                   │
│              │ node_memory_Cached_bytes (缓存)                      │
│              │ node_memory_SwapTotal_bytes (交换分区总量)            │
│              │ node_memory_SwapFree_bytes (交换分区空闲)             │
├──────────────┼──────────────────────────────────────────────────────┤
│ 磁盘          │ node_disk_read_bytes_total (读取字节数)             │
│              │ node_disk_written_bytes_total (写入字节数)           │
│              │ node_disk_io_time_seconds_total (IO时间)             │
│              │ node_disk_read_time_seconds_total (读取时间)          │
│              │ node_disk_write_time_seconds_total (写入时间)         │
│              │ node_filesystem_size_bytes (文件系统总大小)           │
│              │ node_filesystem_avail_bytes (文件系统可用空间)        │
│              │ node_filesystem_files_free (可用 inode)              │
├──────────────┼──────────────────────────────────────────────────────┤
│ 网络          │ node_network_receive_bytes_total (接收字节数)       │
│              │ node_network_transmit_bytes_total (发送字节数)        │
│              │ node_network_receive_packets_total (接收包数)         │
│              │ node_network_transmit_packets_total (发送包数)        │
│              │ node_network_receive_errs_total (接收错误)            │
│              │ node_network_transmit_errs_total (发送错误)           │
│              │ node_network_up (网卡状态)                           │
├──────────────┼──────────────────────────────────────────────────────┤
│ 系统          │ node_boot_time_seconds (启动时间)                  │
│              │ node_time_seconds (当前时间)                         │
│              │ node_uname_info (系统信息)                           │
│              │ node_context_switches_total (上下文切换)              │
│              │ node_entropy_available_bits (可用熵)                 │
└──────────────┴──────────────────────────────────────────────────────┘
```

#### 3.4 常用 PromQL 查询

```promql
# ===== CPU 相关 =====

# CPU 使用率（排除 idle）
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# 各模式 CPU 使用率
avg by(mode) (rate(node_cpu_seconds_total[5m])) * 100

# 系统负载（1/5/15 分钟）
node_load1
node_load5
node_load15

# 负载与 CPU 核心数之比
node_load1 / count(node_cpu_seconds_total{mode="idle"}) by (instance)

# ===== 内存相关 =====

# 内存使用率
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100

# 可用内存（GB）
node_memory_MemAvailable_bytes / 1024 / 1024 / 1024

# Swap 使用率
(1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes) * 100

# ===== 磁盘相关 =====

# 磁盘使用率
(1 - node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100

# 磁盘 IO 使用率（百分比）
rate(node_disk_io_time_seconds_total[5m]) * 100

# 磁盘读写速率（MB/s）
rate(node_disk_read_bytes_total[5m]) / 1024 / 1024
rate(node_disk_written_bytes_total[5m]) / 1024 / 1024

# inode 使用率
(1 - node_filesystem_files_free / node_filesystem_files) * 100

# ===== 网络相关 =====

# 网络接收速率（Mbps）
rate(node_network_receive_bytes_total{device!="lo"}[5m]) * 8 / 1024 / 1024

# 网络发送速率（Mbps）
rate(node_network_transmit_bytes_total{device!="lo"}[5m]) * 8 / 1024 / 1024

# 网络错误率
rate(node_network_receive_errs_total[5m])
rate(node_network_transmit_errs_total[5m])
```

### 4. cAdvisor（容器级指标）

#### 4.1 cAdvisor 工作原理

```
┌─────────────────────────────────────────────────────────────────────┐
│                  cAdvisor 工作原理                                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Kubelet 节点                               │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │                    Kubelet                            │   │   │
│  │  │                                                     │   │   │
│  │  │  ┌───────────────────────────────────────────────┐ │   │   │
│  │  │  │              cAdvisor (内置)                   │ │   │   │
│  │  │  │                                               │ │   │   │
│  │  │  │  ┌────────────┐  ┌────────────┐              │ │   │   │
│  │  │  │  │ 容器运行时  │  │  /sys/fs/  │              │ │   │   │
│  │  │  │  │  接口       │  │  cgroup    │              │ │   │   │
│  │  │  │  └─────┬──────┘  └─────┬──────┘              │ │   │   │
│  │  │  │        │               │                      │ │   │   │
│  │  │  │        └───────┬───────┘                      │ │   │   │
│  │  │  │                │                              │ │   │   │
│  │  │  │                ▼                              │ │   │   │
│  │  │  │  ┌─────────────────────────────────────────┐ │ │   │   │
│  │  │  │  │          容器指标采集                    │ │ │   │   │
│  │  │  │  │                                         │ │ │   │   │
│  │  │  │  │  container_cpu_usage_seconds_total      │ │ │   │   │
│  │  │  │  │  container_memory_working_set_bytes     │ │ │   │   │
│  │  │  │  │  container_network_receive_bytes_total  │ │ │   │   │
│  │  │  │  │  container_fs_usage_bytes               │ │ │   │   │
│  │  │  │  │  container_fs_limit_bytes               │ │ │   │   │
│  │  │  │  │  container_oom_events_total             │ │ │   │   │
│  │  │  │  └─────────────────────────────────────────┘ │ │   │   │
│  │  │  └───────────────────────────────────────────────┘ │   │   │
│  │  │                                                     │   │   │
│  │  │  暴露端点: https://<node-ip>:10250/metrics/cadvisor │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                           │                                        │
│                           ▼                                        │
│               ┌──────────────────┐                                 │
│               │    Prometheus    │                                  │
│               └──────────────────┘                                 │
│                                                                     │
│  注意: cAdvisor 是 Kubelet 内置组件，无需单独部署                    │
│  指标通过 Kubelet 的 /metrics/cadvisor 端点暴露                    │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2 cAdvisor 核心指标

```yaml
# cAdvisor 指标分类
cpu:
  - container_cpu_usage_seconds_total      # CPU 使用总时间（秒）
  - container_cpu_cfs_periods_total        # CFS 调度周期总数
  - container_cpu_cfs_throttled_periods_total  # 被限制的周期数
  - container_cpu_cfs_throttled_seconds_total  # 被限制的时间

memory:
  - container_memory_working_set_bytes     # 工作集内存（包含不可回收）
  - container_memory_usage_bytes           # 内存使用量
  - container_memory_rss                   # RSS 内存
  - container_memory_cache                 # 缓存内存
  - container_memory_swap                  # Swap 使用量
  - container_oom_events_total             # OOM 事件数

network:
  - container_network_receive_bytes_total   # 接收字节数
  - container_network_transmit_bytes_total  # 发送字节数
  - container_network_receive_packets_total # 接收包数
  - container_network_transmit_packets_total# 发送包数
  - container_network_receive_errors_total  # 接收错误数
  - container_network_transmit_errors_total # 发送错误数

filesystem:
  - container_fs_usage_bytes               # 文件系统使用量
  - container_fs_limit_bytes               # 文件系统限制
  - container_fs_reads_total               # 读取次数
  - container_fs_writes_total              # 写入次数

process:
  container_processes                      # 进程数
  container_file_descriptors               # 文件描述符数
  container_sockets                        # Socket 数
```

#### 4.3 容器级别 PromQL 查询

```promql
# ===== 容器 CPU =====

# 容器 CPU 使用率（单核为 100%）
sum(rate(container_cpu_usage_seconds_total{image!="",container!=""}[5m])) by (pod, namespace)

# 容器 CPU 使用率（百分比，基于 limit）
sum(rate(container_cpu_usage_seconds_total{image!="",container!=""}[5m])) by (pod, namespace)
/ sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod, namespace) * 100

# 容器 CPU 被限制（Throttle）的百分比
rate(container_cpu_cfs_throttled_periods_total{image!="",container!=""}[5m])
/ rate(container_cpu_cfs_periods_total{image!="",container!=""}[5m]) * 100

# ===== 容器内存 =====

# 容器内存使用量（MB）
container_memory_working_set_bytes{image!="",container!=""} / 1024 / 1024

# 容器内存使用率（基于 limit）
container_memory_working_set_bytes{image!="",container!=""}
/ kube_pod_container_resource_limits{resource="memory"} * 100

# 容器 OOM Kill 事件
container_oom_events_total > 0

# ===== 容器网络 =====

# 容器网络接收速率（MB/s）
rate(container_network_receive_bytes_total{interface!="lo"}[5m]) / 1024 / 1024

# 容器网络发送速率（MB/s）
rate(container_network_transmit_bytes_total{interface!="lo"}[5m]) / 1024 / 1024

# ===== 容器文件系统 =====

# 容器文件系统使用量（GB）
container_fs_usage_bytes{image!="",container!=""} / 1024 / 1024 / 1024

# 容器文件系统使用率
container_fs_usage_bytes{image!="",container!=""}
/ container_fs_limit_bytes{image!="",container!=""} * 100
```

### 5. kube-prometheus-stack

#### 5.1 安装与配置

```bash
# 添加 Helm 仓库
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 创建命名空间
kubectl create namespace monitoring

# 下载默认 values 文件（用于自定义）
helm show values prometheus-community/kube-prometheus-stack > /tmp/kps-values.yaml

# 安装 kube-prometheus-stack
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.accessModes[0]=ReadWriteOnce \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
  --set grafana.adminPassword=admin123 \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=10Gi \
  --set alertmanager.alertmanagerSpec.retention=120h \
  --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.accessModes[0]=ReadWriteOnce \
  --set alertmanager.alertmanagerSpec.storage.volumeClaimTemplate.spec.resources.requests.storage=10Gi

# 检查安装状态
kubectl get pods -n monitoring
kubectl get svc -n monitoring
```

```yaml
# custom-values.yaml - 生产环境推荐配置
prometheus:
  prometheusSpec:
    # 数据保留时间
    retention: 30d
    retentionSize: "45GB"

    # 存储配置
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 100Gi

    # 资源配置
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: "2"
        memory: 4Gi

    # 采集间隔
    scrapeInterval: 30s
    evaluationInterval: 30s

    # 外部标签
    externalLabels:
      cluster: production
      environment: prod

    # 额外采集配置
    additionalScrapeConfigs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
          - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
            action: replace
            regex: ([^:]+)(?::\d+)?;(\d+)
            replacement: $1:$2
            target_label: __address__

    # ServiceMonitor 选择器
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    ruleSelectorNilUsesHelmValues: false

alertmanager:
  alertmanagerSpec:
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 200m
        memory: 512Mi
    storage:
      volumeClaimTemplate:
        spec:
          storageClassName: gp3
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 10Gi

  config:
    global:
      resolve_timeout: 5m
    route:
      group_by: ['alertname', 'namespace', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'default'
      routes:
        - match:
            severity: critical
          receiver: 'pagerduty'
          group_wait: 10s
          repeat_interval: 1h
        - match:
            severity: warning
          receiver: 'slack'
          repeat_interval: 4h
    receivers:
      - name: 'default'
        webhook_configs:
          - url: 'http://alertmanager-webhook:9095/webhook'
      - name: 'pagerduty'
        pagerduty_configs:
          - routing_key: '<pagerduty-key>'
            severity: 'critical'
      - name: 'slack'
        slack_configs:
          - api_url: '<slack-webhook-url>'
            channel: '#sre-alerts'
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

grafana:
  enabled: true
  adminPassword: admin123

  persistence:
    enabled: true
    size: 10Gi

  # 数据源自动配置
  sidecar:
    datasources:
      enabled: true
    dashboards:
      enabled: true

  # 额外数据源
  additionalDataSources:
    - name: Loki
      type: loki
      url: http://loki:3100
      access: proxy

  # Grafana 配置
  grafana.ini:
    server:
      root_url: https://grafana.example.com
    auth.anonymous:
      enabled: false
    security:
      admin_user: admin

kubeStateMetrics:
  enabled: true

nodeExporter:
  enabled: true

kubelet:
  enabled: true

kubeControllerManager:
  enabled: true

kubeScheduler:
  enabled: true

kubeEtcd:
  enabled: true

kubeProxy:
  enabled: true
```

#### 5.2 组件关系图

```
┌─────────────────────────────────────────────────────────────────────┐
│              kube-prometheus-stack 组件关系                           │
│                                                                     │
│  kube-prometheus-stack (Helm Chart)                                 │
│  ├── Prometheus Operator                                            │
│  │   ├── CRD 管理（Prometheus, ServiceMonitor, PodMonitor等）       │
│  │   ├── 自动配置 Prometheus Server                                 │
│  │   └── 自动管理 Alertmanager                                      │
│  │                                                                   │
│  ├── Prometheus Server                                              │
│  │   ├── 数据采集（Scrape）                                         │
│  │   ├── 规则评估（Rule Evaluation）                                │
│  │   └── 数据存储（TSDB）                                           │
│  │                                                                   │
│  │   预配置的 ServiceMonitor:                                        │
│  │   ├── kube-apiserver                                             │
│  │   ├── kube-controller-manager                                    │
│  │   ├── kube-scheduler                                             │
│  │   ├── kube-proxy                                                 │
│  │   ├── kubelet                                                    │
│  │   ├── kube-state-metrics                                         │
│  │   ├── node-exporter                                              │
│  │   ├── alertmanager                                               │
│  │   ├── prometheus                                                 │
│  │   └── grafana                                                    │
│  │                                                                   │
│  ├── Alertmanager                                                   │
│  │   ├── 告警路由（Routing）                                        │
│  │   ├── 告警分组（Grouping）                                       │
│  │   ├── 告警抑制（Inhibition）                                     │
│  │   ├── 告警静默（Silence）                                        │
│  │   └── 通知发送（Notification）                                   │
│  │                                                                   │
│  ├── Grafana                                                        │
│  │   ├── 预装 K8s 仪表盘                                            │
│  │   ├── 自动发现 ConfigMap 仪表盘                                  │
│  │   └── 自动配置 Prometheus 数据源                                  │
│  │                                                                   │
│  ├── kube-state-metrics                                             │
│  │   └── K8s 对象状态指标                                           │
│  │                                                                   │
│  ├── node-exporter                                                  │
│  │   └── 主机级指标（DaemonSet）                                    │
│  │                                                                   │
│  └── PrometheusRules (预配置告警规则)                               │
│      ├── K8s 资源告警                                               │
│      ├── 节点告警                                                   │
│      ├── etcd 告警                                                  │
│      └── 通用告警                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 6. K8s 专用 Grafana 仪表盘

#### 6.1 推荐仪表盘 ID

```
┌────────────────┬───────────────────────────────────────────────────┐
│ Dashboard ID   │ 描述                                              │
├────────────────┼───────────────────────────────────────────────────┤
│ 315            │ Kubernetes Cluster Monitoring (Prometheus)         │
│ 6417           │ Kubernetes Cluster (Prometheus)                    │
│ 13770          │ K8s Cluster Summary                                │
│ 15760          │ Kubernetes Views Global                            │
│ 15761          │ Kubernetes Views Namespaces                        │
│ 15762          │ Kubernetes Views Pods                              │
│ 15763          │ Kubernetes Views Nodes                             │
│ 13332          │ K8s Pod & Container Monitoring                    │
│ 5228          │ kube-state-metrics v2                              │
│ 17831          │ Kubernetes / Views / Global                        │
│ 15757          │ Node Exporter Full                                 │
│ 11074          │ Node Exporter (Simple)                             │
│ 12006          │ Kubernetes API Server                              │
│ 12007          │ Kubernetes Controller Manager                      │
│ 12008          │ Kubernetes Scheduler                               │
│ 12009          │ Kubernetes Kubelet                                 │
│ 3070           │ etcd Overview                                     │
└────────────────┴───────────────────────────────────────────────────┘
```

#### 6.2 导入仪表盘

```bash
# 方式 1: Grafana UI 导入
# 1. 打开 Grafana -> Dashboards -> Import
# 2. 输入 Dashboard ID（如 315）
# 3. 选择 Prometheus 数据源
# 4. 点击 Import

# 方式 2: 使用 Grafana API 导入
GRAFANA_URL="http://grafana.monitoring.svc:3000"
DASHBOARD_ID=315

# 下载仪表盘 JSON
curl -s "https://grafana.com/api/dashboards/${DASHBOARD_ID}/revisions/latest/download" \
  -o /tmp/dashboard.json

# 通过 API 导入
curl -X POST "${GRAFANA_URL}/api/dashboards/import" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
  -d "{
    \"dashboard\": $(cat /tmp/dashboard.json),
    \"overwrite\": true,
    \"inputs\": [
      {
        \"name\": \"DS_PROMETHEUS\",
        \"type\": \"datasource\",
        \"pluginId\": \"prometheus\",
        \"value\": \"Prometheus\"
      }
    ]
  }"
```

```yaml
# 方式 3: 使用 ConfigMap 自动导入（推荐 GitOps）
apiVersion: v1
kind: ConfigMap
metadata:
  name: k8s-cluster-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"  # Grafana sidecar 自动发现标签
data:
  k8s-cluster.json: |-
    {
      "dashboard": { ... },
      "overwrite": true
    }
```

### 7. 资源 Request/Limit 监控

#### 7.1 资源配额关系

```
┌─────────────────────────────────────────────────────────────────────┐
│                  K8s 资源配额层次                                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    ResourceQuota (命名空间级别)                │   │
│  │                                                             │   │
│  │  cpu: requests=8, limits=16                                 │   │
│  │  memory: requests=16Gi, limits=32Gi                         │   │
│  │  pods: 50                                                   │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │              LimitRange (默认值/范围)                 │   │   │
│  │  │                                                     │   │   │
│  │  │  default: cpu=200m, memory=256Mi  (默认 limit)      │   │   │
│  │  │  defaultRequest: cpu=100m, memory=128Mi  (默认 req) │   │   │
│  │  │  max: cpu=2, memory=4Gi                             │   │   │
│  │  │  min: cpu=50m, memory=64Mi                          │   │   │
│  │  │                                                     │   │   │
│  │  │  ┌─────────────────────────────────────────────┐   │   │   │
│  │  │  │              Pod 资源配置                    │   │   │   │
│  │  │  │                                             │   │   │   │
│  │  │  │  resources:                                 │   │   │   │
│  │  │  │    requests:  ← 调度依据                    │   │   │   │
│  │  │  │      cpu: "250m"   (0.25 核)                │   │   │   │
│  │  │  │      memory: "128Mi"                        │   │   │   │
│  │  │  │    limits:    ← 上限限制                    │   │   │   │
│  │  │  │      cpu: "500m"   (0.5 核)                 │   │   │   │
│  │  │  │      memory: "256Mi"                        │   │   │   │
│  │  │  │                                             │   │   │   │
│  │  │  │  Request ≤ Limit                            │   │   │   │
│  │  │  │  Request: K8s 调度器保证分配                │   │   │   │
│  │  │  │  Limit: 容器能使用的最大值                  │   │   │   │
│  │  │  │  - CPU 超 limit: 被限流（Throttle）         │   │   │   │
│  │  │  │  - Memory 超 limit: 被 OOM Kill            │   │   │   │
│  │  │  └─────────────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 7.2 资源监控 PromQL

```promql
# ===== 资源使用 vs Request/Limit =====

# CPU 使用量 vs Request
sum(rate(container_cpu_usage_seconds_total{container!="",pod!=""}[5m])) by (pod, namespace)
/ sum(kube_pod_container_resource_requests{resource="cpu"}) by (pod, namespace)

# CPU 使用量 vs Limit
sum(rate(container_cpu_usage_seconds_total{container!="",pod!=""}[5m])) by (pod, namespace)
/ sum(kube_pod_container_resource_limits{resource="cpu"}) by (pod, namespace)

# Memory 使用量 vs Request
sum(container_memory_working_set_bytes{container!="",pod!=""}) by (pod, namespace)
/ sum(kube_pod_container_resource_requests{resource="memory"}) by (pod, namespace)

# Memory 使用量 vs Limit
sum(container_memory_working_set_bytes{container!="",pod!=""}) by (pod, namespace)
/ sum(kube_pod_container_resource_limits{resource="memory"}) by (pod, namespace)

# ===== 节点级别资源使用 =====

# 节点 CPU 使用率（基于可分配资源）
sum(rate(container_cpu_usage_seconds_total{id="/"}[5m])) by (instance)
/ sum(kube_node_status_allocatable{resource="cpu"}) by (node)

# 节点 Memory 使用率
sum(container_memory_working_set_bytes{id="/"}) by (instance)
/ sum(kube_node_status_allocatable{resource="memory"}) by (node)

# 节点 Pod 数量
count(kube_pod_info) by (node)

# ===== 资源 Request 使用率（集群级别）=====

# 集群 CPU Request 分配率
sum(kube_pod_container_resource_requests{resource="cpu"})
/ sum(kube_node_status_allocatable{resource="cpu"}) * 100

# 集群 Memory Request 分配率
sum(kube_pod_container_resource_requests{resource="memory"})
/ sum(kube_node_status_allocatable{resource="memory"}) * 100

# ===== 无 Request/Limit 的 Pod =====

# 没有设置 CPU Request 的 Pod
kube_pod_container_resource_requests{resource="cpu"} == 0

# 没有设置 Memory Limit 的 Pod
kube_pod_container_resource_limits{resource="memory"} == 0
```

### 8. Pod 重启追踪

#### 8.1 重启原因分析

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Pod 重启原因分析                                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Container Status                           │   │
│  │                                                             │   │
│  │  ┌──────────────────┐  ┌──────────────────┐                │   │
│  │  │  Waiting         │  │  Running         │                │   │
│  │  │                  │  │                  │                │   │
│  │  │  Reason:         │  │  startedAt:      │                │   │
│  │  │  - CrashLoopBack │  │    2026-05-03... │                │   │
│  │  │  - ImagePullBack │  │                  │                │   │
│  │  │  - ContainerCreat│  │                  │                │   │
│  │  │  - PodInitializing│  │                  │                │   │
│  │  └──────────────────┘  └──────────────────┘                │   │
│  │                                                             │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │  Terminated                                           │  │   │
│  │  │                                                       │  │   │
│  │  │  Reason:               Exit Code:                     │  │   │
│  │  │  - OOMKilled           137 (内存溢出)                 │  │   │
│  │  │  - Error               1 (程序错误)                   │  │   │
│  │  │  - Completed           0 (正常完成)                   │  │   │
│  │  │  - DeadlineExceeded    - (超时)                       │  │   │
│  │  │  - ContainerStatusUnknown - (状态未知)                │  │   │
│  │  │                                                       │  │   │
│  │  │  restartCount: 5  ← 关键指标                          │  │   │
│  │  └──────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  常见重启模式：                                                      │
│  ├── restartCount 持续增加 → CrashLoopBackOff                       │
│  ├── restartCount 突然增加 → 代码/配置变更导致                      │
│  ├── OOMKilled → 内存 limit 过低或内存泄漏                         │
│  ├── ImagePullBackOff → 镜像拉取失败                                │
│  └── DeadlineExceeded → 启动探针超时                                │
└─────────────────────────────────────────────────────────────────────┘
```

#### 8.2 Pod 重启监控指标与告警

```yaml
# prometheus-rules-pod-restart.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pod-restart-alerts
  namespace: monitoring
spec:
  groups:
    - name: pod-restart
      rules:
        # 告警规则 1: Pod 频繁重启
        - alert: PodFrequentlyRestarting
          expr: |
            increase(kube_pod_container_status_restarts_total[1h]) > 5
          for: 5m
          labels:
            severity: warning
            team: sre
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} 频繁重启"
            description: |
              容器 {{ $labels.container }} 在过去 1 小时内重启了 {{ $value }} 次。
              请检查应用日志和资源限制。

        # 告警规则 2: Pod 重启次数激增
        - alert: PodRestartSpike
          expr: |
            (
              kube_pod_container_status_restarts_total
              - kube_pod_container_status_restarts_total offset 1h
            ) > 10
          for: 0m
          labels:
            severity: critical
            team: sre
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} 重启次数激增"
            description: |
              容器 {{ $labels.container }} 在过去 1 小时内重启了 {{ $value }} 次。
              这可能是严重问题的信号，请立即排查。

        # 告警规则 3: OOM Kill 导致重启
        - alert: PodOOMKilled
          expr: |
            kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
          for: 0m
          labels:
            severity: warning
            team: sre
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} 被 OOM Kill"
            description: |
              容器 {{ $labels.container }} 因内存溢出被终止。
              当前内存 limit: {{ with printf "kube_pod_container_resource_limits{resource='memory',pod='%s',namespace='%s',container='%s'}" $labels.pod $labels.namespace $labels.container | query }}{{ . | first | value | humanize1024 }}{{ end }}。
              建议增加内存 limit 或排查内存泄漏。

        # 告警规则 4: CrashLoopBackOff
        - alert: PodCrashLoopBackOff
          expr: |
            kube_pod_status_phase{phase="Running"} == 0
            and on(pod, namespace)
            kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"} == 1
          for: 5m
          labels:
            severity: critical
            team: sre
          annotations:
            summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} 处于 CrashLoopBackOff"
            description: |
              Pod 处于 CrashLoopBackOff 状态，请检查应用启动日志。

        # 告警规则 5: Deployment 副本不可用
        - alert: DeploymentReplicasUnavailable
          expr: |
            kube_deployment_status_replicas_unavailable > 0
          for: 10m
          labels:
            severity: warning
            team: sre
          annotations:
            summary: "Deployment {{ $labels.namespace }}/{{ $labels.deployment }} 有不可用副本"
            description: |
              当前 {{ $value }} 个副本不可用，期望副本数:
              {{ with printf "kube_deployment_spec_replicas{deployment='%s',namespace='%s'}" $labels.deployment $labels.namespace | query }}{{ . | first | value }}{{ end }}。
```

#### 8.3 SRE 场景：Pod 频繁重启排查

```
┌─────────────────────────────────────────────────────────────────────┐
│              SRE 场景: Pod 频繁重启排查流程                           │
│                                                                     │
│  时间线：                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 14:00  收到告警: PodFrequentlyRestarting                     │   │
│  │        Pod: production/api-server-xxx                        │   │
│  │        重启次数: 8 次/小时                                    │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Step 1: 查看监控指标                                         │   │
│  │                                                             │   │
│  │ Grafana Dashboard:                                          │   │
│  │ - restart_count 持续上升                                     │   │
│  │ - 终止原因: OOMKilled (exit code 137)                        │   │
│  │ - 内存使用接近 Limit                                        │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Step 2: 查看 Pod 事件和日志                                  │   │
│  │                                                             │   │
│  │ kubectl describe pod api-server-xxx -n production            │   │
│  │ Last State: Terminated                                      │   │
│  │   Reason: OOMKilled                                         │   │
│  │   Exit Code: 137                                            │   │
│  │   Memory Limit: 256Mi                                       │   │
│  │                                                             │   │
│  │ kubectl logs api-server-xxx -n production --previous         │   │
│  │ [OOM] 内存使用: 268MB / 256MB limit                         │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Step 3: 分析根因                                             │   │
│  │                                                             │   │
│  │ 内存使用趋势:                                                │   │
│  │ ┌────────────────────────────────────────────────┐          │   │
│  │ │ Memory   280 ─                              ╱│          │   │
│  │ │ (MiB)    260 ─                         ╱────╱ │          │   │
│  │ │          240 ─                   ╱────╱      │          │   │
│  │ │          220 ─             ╱────╱            │          │   │
│  │ │          200 ─       ╱────╱   ← OOM Kill     │          │   │
│  │ │          180 ─ ╱────╱         重启后恢复     │          │   │
│  │ │               └──────┬──────┬──────┬──────┐ │          │   │
│  │ │               14:00  14:15  14:30  14:45  │ │          │   │
│  │ └────────────────────────────────────────────┘ │          │   │
│  │                                                             │   │
│  │ 结论: 内存泄漏，使用量持续增长直到触发 OOM Kill             │   │
│  └────────────────────────────┬────────────────────────────────┘   │
│                               │                                     │
│                               ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Step 4: 修复                                                 │   │
│  │                                                             │   │
│  │ 短期: 增加内存 Limit (256Mi → 512Mi)                        │   │
│  │ 长期: 排查内存泄漏，修复代码                                 │   │
│  │ 预防: 设置内存使用告警（80% Limit）                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 9. etcd/apiserver/scheduler/controller-manager 指标

#### 9.1 Control Plane 组件指标

```
┌─────────────────────────────────────────────────────────────────────┐
│              K8s Control Plane 指标                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  kube-apiserver 指标:                                               │
│  ├── apiserver_request_total (请求总数)                             │
│  ├── apiserver_request_duration_seconds (请求延迟)                  │
│  ├── apiserver_request_count (请求计数)                             │
│  ├── apiserver_current_inflight_requests (当前并发请求)             │
│  ├── apiserver_audit_event_total (审计事件)                         │
│  └── apiserver_storage_objects (存储对象数)                         │
│                                                                     │
│  kube-controller-manager 指标:                                      │
│  ├── workqueue_adds_total (工作队列添加数)                          │
│  ├── workqueue_depth (工作队列深度)                                 │
│  ├── workqueue_queue_duration_seconds (队列等待时间)                │
│  ├── rest_client_requests_total (API 请求计数)                      │
│  ├── node_collector_evictions_total (节点驱逐数)                    │
│  └── pv_collector_bound_pv_count (绑定 PV 数)                      │
│                                                                     │
│  kube-scheduler 指标:                                               │
│  ├── scheduler_schedule_attempts_total (调度尝试数)                 │
│  ├── scheduler_e2e_scheduling_duration_seconds (端到端调度延迟)     │
│  ├── scheduler_pending_pods (待调度 Pod 数)                         │
│  ├── scheduler_framework_extension_point_duration (插件执行时间)     │
│  └── scheduler_preemption_attempts_total (抢占尝试数)               │
│                                                                     │
│  etcd 指标:                                                         │
│  ├── etcd_server_has_leader (是否有 Leader)                         │
│  ├── etcd_server_leader_changes_seen_total (Leader 变更次数)        │
│  ├── etcd_disk_wal_fsync_duration_seconds (WAL 同步延迟)            │
│  ├── etcd_disk_backend_commit_duration_seconds (提交延迟)           │
│  ├── etcd_network_peer_round_trip_time_seconds (网络 RTT)           │
│  ├── etcd_server_proposals_failed_total (提案失败数)                │
│  ├── etcd_server_proposals_applied_total (已应用提案数)             │
│  ├── etcd_debugging_mvcc_db_total_size_in_bytes (数据库大小)        │
│  └── etcd_server_slow_apply_total (慢应用数)                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 9.2 Control Plane 告警规则

```yaml
# prometheus-rules-control-plane.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: control-plane-alerts
  namespace: monitoring
spec:
  groups:
    - name: etcd
      rules:
        - alert: EtcdNoLeader
          expr: |
            etcd_server_has_leader == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "etcd 集群没有 Leader"
            description: "etcd 实例 {{ $labels.instance }} 没有 Leader，集群可能不可用。"

        - alert: EtcdHighFsyncDuration
          expr: |
            histogram_quantile(0.99, rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m])) > 0.5
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "etcd WAL 同步延迟过高"
            description: "P99 WAL 同步延迟: {{ $value }}s，建议检查磁盘性能。"

        - alert: EtcdHighCommitDuration
          expr: |
            histogram_quantile(0.99, rate(etcd_disk_backend_commit_duration_seconds_bucket[5m])) > 0.25
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "etcd 提交延迟过高"
            description: "P99 提交延迟: {{ $value }}s。"

    - name: apiserver
      rules:
        - alert: ApiserverHighRequestLatency
          expr: |
            histogram_quantile(0.99, rate(apiserver_request_duration_seconds_bucket{verb!~"WATCH|CONNECT"}[5m])) > 1
          for: 2m
          labels:
            severity: warning
          annotations:
            summary: "API Server 请求延迟过高"
            description: "P99 请求延迟: {{ $value }}s，verb: {{ $labels.verb }}。"

        - alert: ApiserverHighErrorRate
          expr: |
            sum(rate(apiserver_request_total{code=~"5.."}[5m])) by (verb)
            / sum(rate(apiserver_request_total[5m])) by (verb) > 0.01
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "API Server 错误率过高"
            description: "错误率: {{ $value | humanizePercentage }}，verb: {{ $labels.verb }}。"

    - name: scheduler
      rules:
        - alert: SchedulerHighSchedulingLatency
          expr: |
            histogram_quantile(0.99, rate(scheduler_e2e_scheduling_duration_seconds_bucket[5m])) > 10
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "调度器延迟过高"
            description: "P99 调度延迟: {{ $value }}s。"

        - alert: SchedulerPendingPods
          expr: |
            scheduler_pending_pods{queue="active"} > 100
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "调度器待处理 Pod 过多"
            description: "待调度 Pod 数: {{ $value }}，可能存在资源不足。"

    - name: controller-manager
      rules:
        - alert: ControllerManagerHighWorkqueueDepth
          expr: |
            workqueue_depth{job="kube-controller-manager"} > 100
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Controller Manager 工作队列过深"
            description: "队列深度: {{ $value }}，控制器可能跟不上。"
```

## 实战练习

### 练习 1: 部署 kube-prometheus-stack 并验证监控

**目标:** 使用 Helm 部署完整的 K8s 监控栈，验证所有组件正常采集数据。

```bash
# 步骤 1: 创建命名空间
kubectl create namespace monitoring

# 步骤 2: 添加 Helm 仓库
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 步骤 3: 创建自定义 values 文件
cat > /tmp/kps-values.yaml << 'EOF'
prometheus:
  prometheusSpec:
    retention: 7d
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
      limits:
        cpu: "1"
        memory: 1Gi

grafana:
  enabled: true
  adminPassword: admin123
  service:
    type: NodePort
    nodePort: 30300

kubeStateMetrics:
  enabled: true

nodeExporter:
  enabled: true

alertmanager:
  alertmanagerSpec:
    resources:
      requests:
        cpu: 50m
        memory: 128Mi
      limits:
        cpu: 100m
        memory: 256Mi
EOF

# 步骤 4: 安装
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values /tmp/kps-values.yaml

# 步骤 5: 验证安装
kubectl get pods -n monitoring
# 期望输出:
# NAME                                                     READY   STATUS
# kube-prometheus-stack-grafana-xxx                        3/3     Running
# kube-prometheus-stack-kube-state-metrics-xxx             1/1     Running
# kube-prometheus-stack-prometheus-node-exporter-xxx       1/1     Running
# kube-prometheus-stack-prometheus-operator-xxx            1/1     Running
# kube-prometheus-stack-alertmanager-0                     2/2     Running
# prometheus-kube-prometheus-stack-prometheus-0            2/2     Running

# 步骤 6: 验证数据采集
kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9090:9090 &
# 访问 http://localhost:9090/targets，确认所有 target 状态为 UP

# 步骤 7: 验证 Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80 &
# 访问 http://localhost:3000，导入 Dashboard ID 315
```

### 练习 2: 配置 Pod 重启监控与告警

**目标:** 创建自定义 PrometheusRule，监控 Pod 重启并通过 Alertmanager 发送告警。

```bash
# 步骤 1: 创建告警规则
cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pod-restart-custom
  namespace: monitoring
  labels:
    release: kube-prometheus-stack
spec:
  groups:
    - name: pod-restart-custom
      rules:
        - alert: PodFrequentRestart
          expr: increase(kube_pod_container_status_restarts_total[1h]) > 3
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "Pod {{ \$labels.pod }} 频繁重启"
            description: "容器 {{ \$labels.container }} 在 1 小时内重启 {{ \$value }} 次"

        - alert: PodOOMKilled
          expr: kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1
          for: 0m
          labels:
            severity: warning
          annotations:
            summary: "Pod {{ \$labels.pod }} 被 OOM Kill"
            description: "容器 {{ \$labels.container }} 因内存溢出被终止"
EOF

# 步骤 2: 验证规则已加载
kubectl get prometheusrule -n monitoring pod-restart-custom -o yaml

# 步骤 3: 创建一个会重启的测试 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: restart-test
  namespace: default
spec:
  containers:
    - name: crash
      image: busybox
      command: ["sh", "-c", "echo 'Starting...'; sleep 10; exit 1"]
      resources:
        limits:
          memory: 64Mi
        requests:
          memory: 32Mi
  restartPolicy: Always
EOF

# 步骤 4: 观察重启和告警
kubectl get pod restart-test -w
# 观察 restartCount 递增

# 步骤 5: 在 Prometheus 中查询告警状态
# 访问 http://localhost:9090/alerts，查看 PodFrequentRestart 告警状态
```

### 练习 3: 导入并定制 K8s Grafana 仪表盘

**目标:** 导入社区 K8s 仪表盘并添加自定义面板。

```bash
# 步骤 1: 访问 Grafana
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80 &
# 打开 http://localhost:3000

# 步骤 2: 导入社区仪表盘
# Dashboards -> Import -> 输入 ID: 315 -> Load
# 选择 Prometheus 数据源 -> Import

# 步骤 3: 导入 Node Exporter 仪表盘
# Dashboards -> Import -> 输入 ID: 1860 -> Load

# 步骤 4: 创建自定义仪表盘
# 添加以下 PromQL 查询的面板:

# Panel 1: Pod 重启次数 Top 10
# PromQL:
topk(10, increase(kube_pod_container_status_restarts_total[1h]))

# Panel 2: 集群 CPU Request 分配率
# PromQL:
sum(kube_pod_container_resource_requests{resource="cpu"})
/ sum(kube_node_status_allocatable{resource="cpu"}) * 100

# Panel 3: 集群 Memory Request 分配率
# PromQL:
sum(kube_pod_container_resource_requests{resource="memory"})
/ sum(kube_node_status_allocatable{resource="memory"}) * 100

# Panel 4: 非 Ready 状态的 Pod 数
# PromQL:
count(kube_pod_status_ready{condition="false"} == 1)

# Panel 5: 节点磁盘使用率 Top 10
# PromQL:
topk(10, (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)

# 步骤 5: 保存仪表盘
```

## 面试题精选

### 1. Kubernetes 监控中 kube-state-metrics 和 cAdvisor 有什么区别？

**参考答案：**

两者都是 K8s 监控的关键组件，但职责不同：

- **kube-state-metrics**: 监控 K8s 对象的声明状态（Declarative State）。它通过 Watch K8s API Server 获取 Deployment、Pod、Node 等对象的元数据和状态信息，转换为 Prometheus 指标。指标前缀为 `kube_*`。例如：Pod 是否 Running、Deployment 期望副本数等。

- **cAdvisor**: 监控容器的实际运行指标（Runtime Metrics）。它内置在 Kubelet 中，通过读取 cgroups 和容器运行时接口获取 CPU、内存、网络、文件系统等实时使用数据。指标前缀为 `container_*`。例如：容器 CPU 使用率、内存使用量等。

简单来说，kube-state-metrics 回答"期望状态是什么"，cAdvisor 回答"实际运行情况如何"。

### 2. 如何监控 Kubernetes 中的 Pod 重启问题？

**参考答案：**

监控 Pod 重启需要多维度结合：

1. **核心指标**：`kube_pod_container_status_restarts_total`（重启次数）、`kube_pod_container_status_last_terminated_reason`（上次终止原因）

2. **告警规则**：
   - 短时间内重启次数增加（如 1 小时内 > 5 次）
   - 出现 OOMKilled 终止原因
   - Pod 处于 CrashLoopBackOff 状态

3. **排查方法**：
   - `kubectl describe pod` 查看终止原因和事件
   - `kubectl logs --previous` 查看上次崩溃日志
   - 结合 cAdvisor 指标分析内存/CPU 使用趋势

4. **常见原因**：内存泄漏导致 OOM Kill、启动探针配置不当、依赖服务不可用、配置错误。

### 3. kube-prometheus-stack 包含哪些组件？各自的作用是什么？

**参考答案：**

kube-prometheus-stack 是一个完整的 K8s 监控解决方案 Helm Chart，包含：

- **Prometheus Operator**: 管理 Prometheus 和 Alertmanager 的生命周期，使用 CRD 简化配置
- **Prometheus Server**: 时序数据库，负责指标采集、存储和查询
- **Alertmanager**: 告警管理器，负责告警路由、分组、抑制和通知
- **Grafana**: 可视化平台，预装 K8s 相关仪表盘
- **kube-state-metrics**: K8s 对象状态指标导出器
- **node-exporter**: 主机级指标采集（DaemonSet 部署）
- **PrometheusRules**: 预配置的告警规则集

### 4. 如何计算 Kubernetes 集群的资源使用率？

**参考答案：**

集群资源使用率计算需要结合多个指标源：

```promql
# CPU 使用率（基于可分配资源）
# 分子: 所有容器实际 CPU 使用量
sum(rate(container_cpu_usage_seconds_total{id="/"}[5m]))
# 分母: 所有节点可分配 CPU
/ sum(kube_node_status_allocatable{resource="cpu"})

# CPU Request 分配率
sum(kube_pod_container_resource_requests{resource="cpu"})
/ sum(kube_node_status_allocatable{resource="cpu"})
```

关键区别：
- **使用率**：实际使用量 / 可分配量（来自 cAdvisor + kube-state-metrics）
- **分配率**：已 Request 量 / 可分配量（来自 kube-state-metrics）
- 使用率反映真实负载，分配率反映资源规划情况

### 5. node-exporter 为什么使用 DaemonSet 部署而不是 Deployment？

**参考答案：**

node-exporter 使用 DaemonSet 部署的核心原因是**每个节点都需要运行一个实例**来采集该节点的主机级指标。

DaemonSet 的优势：
1. **保证覆盖**：DaemonSet 确保每个节点（包括新加入的节点）都有一个 node-exporter 实例
2. **资源效率**：避免一个节点部署多个实例导致端口冲突和资源浪费
3. **自动调度**：新节点加入集群时自动调度
4. **容忍污点**：可以配置 tolerations 在 master 节点上运行

如果使用 Deployment，需要手动管理副本数与节点数的匹配，且新节点加入时不会自动部署。

### 6. etcd 监控中哪些指标最为关键？为什么？

**参考答案：**

etcd 最关键的监控指标：

1. **`etcd_server_has_leader`**：是否有 Leader，无 Leader 意味着集群不可用
2. **`etcd_server_leader_changes_seen_total`**：Leader 变更次数，频繁变更说明集群不稳定
3. **`etcd_disk_wal_fsync_duration_seconds`**：WAL 同步延迟，反映磁盘性能，延迟过高会导致写入超时
4. **`etcd_disk_backend_commit_duration_seconds`**：后端提交延迟，反映数据库写入性能
5. **`etcd_network_peer_round_trip_time_seconds`**：节点间网络 RTT，延迟过高会导致选举超时
6. **`etcd_server_proposals_failed_total`**：提案失败数，失败增加说明集群有问题

这些指标覆盖了 etcd 的三大核心依赖：磁盘性能、网络延迟和 Leader 稳定性。

### 7. 如何在 Grafana 中实现 K8s 多集群监控？

**参考答案：**

多集群监控方案：

1. **联邦方案（Federation）**：每个集群独立 Prometheus，全局 Prometheus 通过 federation 接口采集聚合指标
2. **Thanos/Mimir/Cortex**：使用长期存储方案，各集群 Prometheus 通过 Sidecar 或 Remote Write 上报数据到统一存储
3. **Remote Write**：各集群 Prometheus 通过 remote_write 将指标发送到中心 Prometheus

Grafana 配置：
- 配置多个 Prometheus 数据源（每个集群一个）
- 使用变量（`$cluster`）切换集群
- 仪表盘使用 `external_labels` 中的集群标签区分数据

```yaml
# Prometheus 配置 external_labels
prometheus:
  prometheusSpec:
    externalLabels:
      cluster: production-east
      environment: prod
```

### 8. 什么是 ServiceMonitor 和 PodMonitor？有什么区别？

**参考答案：**

两者都是 Prometheus Operator 的 CRD，用于定义 Prometheus 的采集目标：

- **ServiceMonitor**：基于 Kubernetes Service 定义采集目标。Prometheus 通过 Service 发现背后的 Pod，然后采集指标。适用于有 Service 暴露的应用。

- **PodMonitor**：直接基于 Pod 定义采集目标，不需要 Service。适用于没有 Service 但需要采集指标的 Pod（如批处理 Job）。

选择依据：如果有 Service，优先使用 ServiceMonitor；如果没有 Service 或不需要通过 Service 访问，使用 PodMonitor。

### 9. 如何优化 Prometheus 在大规模 K8s 集群中的性能？

**参考答案：**

大规模集群 Prometheus 优化策略：

1. **分片（Sharding）**：按命名空间或团队分片，使用多个 Prometheus 实例
2. **Recording Rules**：预计算复杂查询，减少实时计算
3. **指标裁剪**：使用 `metric_relabel_configs` 丢弃不需要的高基数指标
4. **采集间隔**：根据实际需求调整 scrapeInterval（如 30s 或 60s）
5. **存储优化**：使用 SSD、配置合理的 TSDB 参数
6. **长期存储**：使用 Thanos/Mimir/Cortex 实现长期存储和全局查询
7. **限制采集范围**：使用 namespace 限制 ServiceMonitor 的采集范围

### 10. 如何用 Prometheus 告警实现 SLO 驱动的告警？

**参考答案：**

SLO 驱动告警使用 Burn Rate（燃烧速率）和多窗口方法：

```promql
# 1 小时燃烧速率（5% 错误率 SLO）
(
  sum(rate(http_requests_total{code=~"5.."}[1h]))
  / sum(rate(http_requests_total[1h]))
) / (1 - 0.9995) > 14.4  # 14.4x 燃烧速率 = 2% 预算在 1 小时内消耗
```

多窗口方法：
- **长窗口（6h）+ 低倍数（1%）**：检测慢速燃烧
- **短窗口（1h）+ 高倍数（2%）**：检测快速燃烧
- **最短窗口（5m）+ 最高倍数（5%）**：检测突发问题

Grafana 内置支持 SLO 告警规则配置，可直接在 Alert Rules 中设置 Burn Rate 条件。

## 延伸阅读

- [kube-state-metrics 官方文档](https://github.com/kubernetes/kube-state-metrics)
- [Prometheus Operator 官方文档](https://prometheus-operator.dev/)
- [kube-prometheus-stack Helm Chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [node-exporter GitHub](https://github.com/prometheus/node_exporter)
- [Kubernetes 监控最佳实践](https://sysdig.com/blog/kubernetes-monitoring-prometheus/)
- [Google SRE Book - 监控分布式系统](https://sre.google/sre-book/practical-alerting/)
- [Prometheus 联邦与远程写入](https://prometheus.io/docs/prometheus/latest/federation/)
- [Thanos 长期存储方案](https://thanos.io/)

## 今日自检清单

- [ ] 能够部署 kube-state-metrics 并理解其核心指标
- [ ] 能够使用 DaemonSet 部署 node-exporter 并配置采集
- [ ] 理解 cAdvisor 的工作原理和容器级指标
- [ ] 能够使用 Helm 安装 kube-prometheus-stack 并自定义配置
- [ ] 能够从 grafana.com 导入 K8s 专用仪表盘
- [ ] 能够编写 PromQL 查询资源 Request/Limit 使用率
- [ ] 能够配置 Pod 重启监控告警规则
- [ ] 理解 etcd/apiserver/scheduler/controller-manager 的关键指标
- [ ] 能够排查 Pod OOM Kill 和 CrashLoopBackOff 问题
- [ ] 理解 ServiceMonitor 和 PodMonitor 的区别和使用场景
