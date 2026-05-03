# Day 91: Kubernetes Pod

> 📅 日期：2026-05-03
> 📖 学习主题：Pod 生命周期、init 容器、sidecar 模式、资源管理与 QoS、健康检查、优雅终止
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 90 Kubernetes 简介与架构

---

## 🎯 学习目标

- 深入理解 Pod 的设计哲学和内部机制
- 掌握 Pod 生命周期各阶段和状态转换
- 熟练使用 init 容器和 sidecar 容器模式
- 理解资源请求/限制与 QoS 类别的关系
- 掌握三种健康检查探针的配置与最佳实践
- 理解 Pod 优雅终止流程和 PreStop Hook

---

## 📖 核心知识点

### 1. Pod 概述

#### 1.1 什么是 Pod

Pod 是 Kubernetes 中**最小的可部署单元**，是一组**共享网络和存储**的容器集合。Pod 不是容器的简单堆叠，而是一个逻辑上的"主机"，内部容器共享同一个 Network Namespace。

**为什么需要 Pod 而不是直接调度容器？**

```
┌──────────────────────────────────────────────────────────────────┐
│                    为什么需要 Pod？                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  问题 1: 紧耦合容器如何协同工作？                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  场景: Web 服务器 + 日志收集器                           │     │
│  │                                                          │     │
│  │  如果分开部署:                                           │     │
│  │  - 日志收集器如何访问 Web 服务器的日志文件？              │     │
│  │  - 如何确保它们调度到同一台机器？                         │     │
│  │  - 如何共享网络栈？                                      │     │
│  │                                                          │     │
│  │  Pod 解决方案:                                           │     │
│  │  - 共享 Volume: 两个容器访问同一个日志目录                │     │
│  │  - 共享网络: localhost 通信，无需服务发现                 │     │
│  │  - 同调度: 两个容器始终在同一节点                         │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  问题 2: 如何管理容器的生命周期？                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Pod 提供统一的生命周期管理:                              │     │
│  │  - Pod 创建时，所有容器一起创建                           │     │
│  │  - Pod 删除时，所有容器一起销毁                           │     │
│  │  - Pod 重启策略应用于整个 Pod（不是单个容器）             │     │
│  │  - Pod 状态聚合所有容器的状态                             │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 1.2 Pod 内部结构

```
┌──────────────────────────────────────────────────────────────────┐
│                    Pod 内部结构                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────────── Pod ────────────────────────────────┐   │
│   │                                                          │   │
│   │   Network Namespace (共享网络)                           │   │
│   │   ├── Pod IP: 10.244.1.5                                │   │
│   │   ├── 共享端口空间 (localhost 通信)                      │   │
│   │   └── 共享主机名                                        │   │
│   │                                                          │   │
│   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │   │
│   │   │  Container A  │  │  Container B  │  │ Init Ctr 1  │ │   │
│   │   │  (主容器)     │  │  (sidecar)   │  │ (初始化)     │ │   │
│   │   │              │  │              │  │              │ │   │
│   │   │  nginx:1.25  │  │  fluentd:v1  │  │  busybox     │ │   │
│   │   │  port: 80    │  │  日志收集     │  │  等待依赖    │ │   │
│   │   └──────────────┘  └──────────────┘  └──────────────┘ │   │
│   │                                                          │   │
│   │   Shared Volumes (共享存储)                              │   │
│   │   ├── /var/log/nginx (Container A 写, Container B 读)   │   │
│   │   └── /etc/config (ConfigMap 挂载)                      │   │
│   │                                                          │   │
│   │   Shared IPC Namespace                                   │   │
│   │   └── 共享内存、信号量                                   │   │
│   │                                                          │   │
│   └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Pod 资源对象示例：**

```yaml
# pod-basic.yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-app
  namespace: default
  labels:                         # 标签：用于选择和过滤
    app: web
    version: v1
    environment: production
  annotations:                    # 注解：存储非标识性元数据
    description: "Web application pod"
    owner: "sre-team"
spec:
  restartPolicy: Always           # 重启策略：Always/OnFailure/Never
  terminationGracePeriodSeconds: 30  # 优雅终止等待时间
  containers:
  - name: web
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
      name: http
      protocol: TCP
    env:                          # 环境变量
    - name: ENV
      value: "production"
    - name: DB_HOST               # 从 Secret 读取
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: host
    resources:                    # 资源请求和限制
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"
    volumeMounts:
    - name: config-volume
      mountPath: /etc/nginx/conf.d
    - name: log-volume
      mountPath: /var/log/nginx
  volumes:
  - name: config-volume
    configMap:
      name: nginx-config
  - name: log-volume
    emptyDir: {}
```

---

### 2. Pod 生命周期

#### 2.1 Pod 阶段（Phase）

```
┌──────────────────────────────────────────────────────────────────┐
│                    Pod 生命周期状态转换                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌───────────┐                                                  │
│   │           │                                                  │
│   │  Pending  │ <─── 创建请求已接受，等待调度或拉取镜像           │
│   │           │                                                  │
│   └─────┬─────┘                                                  │
│         │                                                        │
│         │ 调度成功 + 所有容器创建完成                              │
│         ▼                                                        │
│   ┌───────────┐                                                  │
│   │           │                                                  │
│   │  Running  │ <─── 至少一个容器正在运行                         │
│   │           │                                                  │
│   └─────┬─────┘                                                  │
│         │                                                        │
│    ┌────┼────────────────┐                                       │
│    │    │                │                                       │
│    ▼    ▼                ▼                                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                          │
│  │ Succeeded│  │ Failed  │  │Unknown  │                          │
│  │ (正常)  │  │ (失败)  │  │ (未知)  │                          │
│  └─────────┘  └─────────┘  └─────────┘                          │
│                                                                  │
│  Phase 说明:                                                     │
│  - Pending: 已被系统接受，但容器尚未全部就绪                      │
│    (等待调度、拉取镜像、创建容器)                                 │
│  - Running: 至少一个容器处于运行状态                              │
│  - Succeeded: 所有容器正常退出（退出码 0），不会再重启            │
│  - Failed: 至少一个容器异常退出（非 0 退出码）                    │
│  - Unknown: 无法获取 Pod 状态（通常是节点通信问题）               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 2.2 Pod 容器状态（Container State）

```
┌──────────────────────────────────────────────────────────────────┐
│                    容器状态                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Waiting      容器未开始运行，正在等待条件满足                    │
│  │           (拉取镜像、执行 init 容器)                          │
│  │           Reason: ImagePullBackOff, CrashLoopBackOff,         │
│  │                   ContainerCreating, PodInitializing          │
│  │                                                               │
│  Running      容器正在执行                                        │
│  │           StartedAt: 容器启动时间                             │
│  │                                                               │
│  Terminated   容器已结束运行                                      │
│              ExitCode: 退出码 (0=成功, 非0=失败)                 │
│              Reason: Completed, OOMKilled, Error                 │
│              StartedAt: 启动时间                                 │
│              FinishedAt: 结束时间                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 2.3 重启策略（Restart Policy）

```yaml
spec:
  restartPolicy: Always  # 默认值
```

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| Always | 容器退出后总是重启（默认） | Web 服务器、长期运行服务 |
| OnFailure | 仅在非 0 退出码时重启 | Job、批处理任务 |
| Never | 容器退出后不重启 | 调试、一次性任务 |

**SRE 注意：** restartPolicy 是 Pod 级别的，不是容器级别的。所有容器共享同一个重启策略。重启间隔采用指数退避：10s, 20s, 40s, ... 最大 300s（5 分钟）。成功运行 10 分钟后重置退避计时器。

```bash
# 查看 Pod 重启次数
kubectl get pod <pod-name> -o jsonpath='{.status.containerStatuses[0].restartCount}'

# 查看容器退出原因
kubectl describe pod <pod-name> | grep -A 5 "Last State"

# 查看容器退出码含义
# 0: 正常退出
# 1: 应用错误
# 137: OOMKilled (SIGKILL) 或被外部 kill
# 139: SIGSEGV (段错误)
# 143: SIGTERM (优雅终止)
```

---

### 3. Init 容器

#### 3.1 概念与原理

Init 容器是在主容器启动**之前**运行的容器，用于执行初始化任务。它们按顺序执行，每个必须成功完成后下一个才会开始。

```
┌──────────────────────────────────────────────────────────────────┐
│                    Init 容器执行流程                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Pod 启动                                                       │
│      │                                                           │
│      ▼                                                           │
│   ┌──────────────┐                                               │
│   │ Init Ctr 1   │  等待 MySQL 服务就绪                          │
│   │ (等待依赖)   │  直到 MySQL 可连接才退出                      │
│   └──────┬───────┘                                               │
│          │ 退出码 0                                               │
│          ▼                                                        │
│   ┌──────────────┐                                               │
│   │ Init Ctr 2   │  下载配置文件                                  │
│   │ (准备数据)   │  从 S3/ConfigMap 获取配置                     │
│   └──────┬───────┘                                               │
│          │ 退出码 0                                               │
│          ▼                                                        │
│   ┌──────────────┐                                               │
│   │ Init Ctr 3   │  数据库迁移                                    │
│   │ (初始化)     │  执行 schema migration                        │
│   └──────┬───────┘                                               │
│          │ 退出码 0                                               │
│          ▼                                                        │
│   ┌──────────────┐  ┌──────────────┐                             │
│   │ Container A  │  │ Container B  │  所有主容器并行启动          │
│   │ (web)        │  │ (sidecar)    │                              │
│   └──────────────┘  └──────────────┘                             │
│                                                                  │
│   关键特性：                                                      │
│   - 按顺序执行，前一个成功后才启动下一个                          │
│   - 如果 init 容器失败，Pod 会重启（遵循 restartPolicy）         │
│   - Init 容器不支持 readinessProbe                               │
│   - Init 容器不支持 lifecycle.preStop                            │
│   - Pod 重启时，所有 init 容器会重新执行                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.2 Init 容器实际应用

```yaml
# pod-with-init.yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-with-init
  labels:
    app: web
spec:
  initContainers:
  # 场景 1: 等待依赖服务就绪
  - name: wait-for-db
    image: busybox:1.36
    command: ['sh', '-c', 'until nc -z mysql-service 3306; do echo waiting for mysql; sleep 2; done']
    resources:
      requests:
        cpu: "50m"
        memory: "32Mi"
      limits:
        cpu: "100m"
        memory: "64Mi"

  # 场景 2: 从外部系统下载配置
  - name: download-config
    image: busybox:1.36
    command: ['sh', '-c', 'wget -O /shared/config.json https://config-server/app-config.json']
    volumeMounts:
    - name: shared-config
      mountPath: /shared
    resources:
      requests:
        cpu: "50m"
        memory: "32Mi"
      limits:
        cpu: "100m"
        memory: "64Mi"

  # 场景 3: 设置文件权限
  - name: fix-permissions
    image: busybox:1.36
    command: ['sh', '-c', 'chown -R 1000:1000 /app-data && chmod -R 755 /app-data']
    volumeMounts:
    - name: app-data
      mountPath: /app-data
    securityContext:
      runAsUser: 0  # 需要 root 权限修改文件权限
    resources:
      requests:
        cpu: "50m"
        memory: "32Mi"
      limits:
        cpu: "100m"
        memory: "64Mi"

  containers:
  - name: web
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
    volumeMounts:
    - name: shared-config
      mountPath: /etc/nginx/conf.d
    - name: app-data
      mountPath: /usr/share/nginx/html
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"

  volumes:
  - name: shared-config
    emptyDir: {}
  - name: app-data
    emptyDir: {}
```

```bash
# 查看 init 容器状态
kubectl get pod web-with-init -o jsonpath='{.status.initContainerStatuses[*].state}'

# 查看 init 容器日志
kubectl logs web-with-init -c wait-for-db
kubectl logs web-with-init -c download-config

# 排查 init 容器失败
kubectl describe pod web-with-init
# 关注 Events 和 Init Containers 部分
```

---

### 4. Sidecar 容器模式

#### 4.1 概念与设计

Sidecar（边车）模式是在 Pod 中添加辅助容器来增强主容器的功能。Sidecar 容器与主容器共享网络和存储，但执行不同的职责。

```
┌──────────────────────────────────────────────────────────────────┐
│                    Sidecar 模式架构                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────── Pod: web-app ────────────────────────────┐  │
│   │                                                           │  │
│   │   Shared Network Namespace                                │  │
│   │   (localhost 通信, 共享端口空间)                           │  │
│   │                                                           │  │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│   │   │  主容器      │  │  Sidecar 1  │  │  Sidecar 2  │     │  │
│   │   │  nginx:1.25  │  │  fluentd    │  │  envoy      │     │  │
│   │   │             │  │  日志收集    │  │  Service    │     │  │
│   │   │  业务逻辑    │  │             │  │  Mesh 代理  │     │  │
│   │   │             │  │  读取日志    │  │             │     │  │
│   │   │             │  │  转发到 ES   │  │  流量管理   │     │  │
│   │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │  │
│   │          │                │                │             │  │
│   │          └────────┬───────┴────────┬───────┘             │  │
│   │                   │                │                     │  │
│   │          ┌────────▼────────────────▼────────┐            │  │
│   │          │      Shared Volumes               │            │  │
│   │          │      /var/log/nginx               │            │  │
│   │          │      (主容器写, sidecar 读)       │            │  │
│   │          └───────────────────────────────────┘            │  │
│   │                                                           │  │
│   └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│   Sidecar 常见用途：                                              │
│   1. 日志收集 (Fluentd/Filebeat/Fluent Bit)                     │
│   2. Service Mesh 代理 (Envoy/Istio Proxy)                     │
│   3. 配置更新 (ConfigMap Reload)                                │
│   4. 安全代理 (Vault Agent)                                     │
│   5. 数据库代理 (Cloud SQL Proxy)                               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.2 Sidecar 完整示例

```yaml
# pod-with-sidecar.yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-with-sidecar
  labels:
    app: web
spec:
  containers:
  # 主容器: Web 应用
  - name: web
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
    volumeMounts:
    - name: nginx-config
      mountPath: /etc/nginx/conf.d
    - name: shared-logs
      mountPath: /var/log/nginx
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"

  # Sidecar 容器: 日志收集
  - name: log-collector
    image: fluent/fluent-bit:2.2
    volumeMounts:
    - name: shared-logs
      mountPath: /var/log/nginx
      readOnly: true
    - name: fluentbit-config
      mountPath: /fluent-bit/etc/
    resources:
      requests:
        cpu: "50m"
        memory: "64Mi"
      limits:
        cpu: "200m"
        memory: "128Mi"

  # Sidecar 容器: 配置热更新
  - name: config-reloader
    image: jimmidyson/configmap-reload:v0.12.0
    args:
    - --volume-dir=/config
    - --webhook-url=http://localhost:8080/reload
    volumeMounts:
    - name: nginx-config
      mountPath: /config
      readOnly: true
    resources:
      requests:
        cpu: "10m"
        memory: "16Mi"
      limits:
        cpu: "50m"
        memory: "32Mi"

  volumes:
  - name: nginx-config
    configMap:
      name: nginx-config
  - name: shared-logs
    emptyDir: {}
  - name: fluentbit-config
    configMap:
      name: fluentbit-config
```

**K8s 1.28+ 原生 Sidecar 支持（KEP-753）：**

```yaml
# 使用原生 sidecar 特性（K8s 1.28+ alpha, 1.29+ beta）
spec:
  initContainers:
  - name: istio-proxy
    image: istio/proxyv2:1.20.0
    restartPolicy: Always   # 关键：标记为 sidecar
    args: ["proxy", "sidecar"]
    # 使用 initContainers + restartPolicy=Always 实现原生 sidecar
    # 好处：确保 sidecar 在主容器之前启动，在主容器之后终止
```

---

### 5. 资源管理与 QoS

#### 5.1 资源请求与限制

```
┌──────────────────────────────────────────────────────────────────┐
│                    资源管理模型                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   requests（请求）: 容器需要的最小资源量                          │
│   ├── 用于调度：Scheduler 根据 requests 选择节点                 │
│   ├── 保证供给：节点上保证容器能获得 requests 指定的资源          │
│   └── 不会 OOM：只要不超过 requests，不会被驱逐                  │
│                                                                  │
│   limits（限制）: 容器能使用的最大资源量                          │
│   ├── CPU limit: 超过时被限流（throttle），不会被杀死             │
│   ├── Memory limit: 超过时被 OOMKilled 杀死                      │
│   └── 硬性上限：容器永远无法使用超过 limits 的资源               │
│                                                                  │
│   资源单位：                                                      │
│   ├── CPU: 1 = 1 核, 100m = 0.1 核 (millicore)                 │
│   │         最小单位: 1m (千分之一核)                            │
│   └── Memory: 128Mi = 128 Mebibyte                              │
│              1Gi  = 1 Gibibyte                                  │
│              支持: Ki, Mi, Gi, Ti, K, M, G, T                  │
│                                                                  │
│   调度公式:                                                       │
│   节点可分配 >= 所有 Pod 的 requests 之和                        │
│   节点实际使用可以超过 requests（只要不超过 limits）              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```yaml
# resource-example.yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: app
    image: nginx:1.25-alpine
    resources:
      requests:
        cpu: "250m"       # 调度时保证 0.25 核
        memory: "128Mi"   # 调度时保证 128Mi
      limits:
        cpu: "500m"       # 最多使用 0.5 核（超过被限流）
        memory: "256Mi"   # 最多使用 256Mi（超过被 OOMKilled）
```

**SRE 最佳实践：**

```
┌──────────────────────────────────────────────────────────────────┐
│                    资源配置最佳实践                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 必须设置 requests（否则调度器无法做出合理决策）               │
│                                                                  │
│  2. 推荐设置 limits（防止容器失控占用资源）                      │
│                                                                  │
│  3. CPU limits 可以不设（允许突发），但 memory limits 必须设置   │
│                                                                  │
│  4. requests:limits 比例建议：                                   │
│     - CPU: requests = 50%-100% of limits                        │
│     - Memory: requests = 80%-100% of limits                     │
│                                                                  │
│  5. 使用 LimitRange 设置命名空间默认值：                         │
│     防止忘记设置资源的 Pod 占用过多资源                          │
│                                                                  │
│  6. 使用 ResourceQuota 限制命名空间总资源                        │
│                                                                  │
│  7. 使用 VPA (Vertical Pod Autoscaler) 自动调整资源请求          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.2 QoS 类别

Kubernetes 根据 requests 和 limits 的配置自动将 Pod 分为三个 QoS（Quality of Service）类别，用于资源不足时的驱逐优先级。

```
┌──────────────────────────────────────────────────────────────────┐
│                    QoS 类别                                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Guaranteed (保证级) — 最高优先级，最后被驱逐                     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  条件: 所有容器的 requests == limits                    │     │
│  │                                                          │     │
│  │  containers:                                             │     │
│  │  - name: app                                            │     │
│  │    resources:                                           │     │
│  │      requests: { cpu: "500m", memory: "256Mi" }        │     │
│  │      limits:   { cpu: "500m", memory: "256Mi" }        │     │
│  │                                                          │     │
│  │  特点: 资源完全保证，适合关键服务                         │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Burstable (突发级) — 中等优先级                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  条件: 至少一个容器设置了 requests 或 limits，           │     │
│  │        但 requests != limits                            │     │
│  │                                                          │     │
│  │  containers:                                             │     │
│  │  - name: app                                            │     │
│  │    resources:                                           │     │
│  │      requests: { cpu: "200m", memory: "128Mi" }        │     │
│  │      limits:   { cpu: "500m", memory: "256Mi" }        │     │
│  │                                                          │     │
│  │  特点: 保证 requests，允许突发到 limits                  │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  BestEffort (尽力级) — 最低优先级，最先被驱逐                    │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  条件: 没有设置任何 requests 或 limits                  │     │
│  │                                                          │     │
│  │  containers:                                             │     │
│  │  - name: app                                            │     │
│  │    image: nginx                                         │     │
│  │    # 没有 resources 字段                                │     │
│  │                                                          │     │
│  │  特点: 不保证任何资源，内存压力时最先被杀                 │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  驱逐顺序 (节点内存不足时):                                      │
│  BestEffort → Burstable (超过 requests 的) → Guaranteed         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```bash
# 查看 Pod 的 QoS 类别
kubectl get pod <pod-name> -o jsonpath='{.status.qosClass}'

# 查看所有 Pod 的 QoS 类别
kubectl get pods -o custom-columns=\
  NAME:.metadata.name,\
  QOS:.status.qosClass,\
  CPU_REQ:.spec.containers[*].resources.requests.cpu,\
  CPU_LIM:.spec.containers[*].resources.limits.cpu

# 查看节点已分配资源
kubectl describe node <node-name> | grep -A 15 "Allocated resources"
```

#### 5.3 LimitRange 与 ResourceQuota

```yaml
# limitrange.yaml — 命名空间级别的资源默认值和限制
apiVersion: v1
kind: LimitRange
metadata:
  name: default-limits
  namespace: my-app
spec:
  limits:
  - default:           # 默认 limits
      cpu: "500m"
      memory: "256Mi"
    defaultRequest:    # 默认 requests
      cpu: "100m"
      memory: "128Mi"
    max:               # 单容器最大值
      cpu: "2"
      memory: "2Gi"
    min:               # 单容器最小值
      cpu: "50m"
      memory: "64Mi"
    maxLimitRequestRatio:  # limits/requests 最大比率
      cpu: "4"
      memory: "2"
    type: Container
```

```yaml
# resourcequota.yaml — 命名空间级别的总资源限制
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-quota
  namespace: my-app
spec:
  hard:
    requests.cpu: "10"           # 总 CPU 请求上限 10 核
    requests.memory: "20Gi"      # 总内存请求上限 20Gi
    limits.cpu: "20"             # 总 CPU 限制上限 20 核
    limits.memory: "40Gi"        # 总内存限制上限 40Gi
    pods: "50"                   # 最多 50 个 Pod
    services: "10"               # 最多 10 个 Service
    persistentvolumeclaims: "20" # 最多 20 个 PVC
    configmaps: "20"             # 最多 20 个 ConfigMap
    secrets: "20"                # 最多 20 个 Secret
```

```bash
# 查看命名空间的资源配额使用情况
kubectl get resourcequota -n my-app
kubectl describe resourcequota team-quota -n my-app

# 输出示例:
# Name:                   team-quota
# Resource                Used   Hard
# --------                ----   ----
# limits.cpu              2      20
# limits.memory           1Gi    40Gi
# pods                    5      50
# requests.cpu            1      10
# requests.memory         512Mi  20Gi
```

---

### 6. Pod 调度

#### 6.1 nodeSelector — 简单节点选择

```yaml
spec:
  nodeSelector:
    disktype: ssd
    kubernetes.io/os: linux
  containers:
  - name: app
    image: nginx
```

```bash
# 给节点打标签
kubectl label nodes node-01 disktype=ssd
kubectl label nodes node-02 disktype=hdd

# 查看节点标签
kubectl get nodes --show-labels
kubectl get node node-01 --show-labels | grep disktype
```

#### 6.2 Node Affinity — 高级节点亲和性

```yaml
# node-affinity.yaml
apiVersion: v1
kind: Pod
metadata:
  name: affinity-demo
spec:
  affinity:
    nodeAffinity:
      # 硬性要求：必须满足
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: kubernetes.io/os
            operator: In
            values: ["linux"]
          - key: topology.kubernetes.io/zone
            operator: In
            values: ["us-east-1a", "us-east-1b"]

      # 软性偏好：尽量满足
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 80
        preference:
          matchExpressions:
          - key: disktype
            operator: In
            values: ["ssd"]
      - weight: 20
        preference:
          matchExpressions:
          - key: node-role
            operator: In
            values: ["compute"]
  containers:
  - name: app
    image: nginx
```

**操作符说明：**

| 操作符 | 说明 | 示例 |
|--------|------|------|
| In | 标签值在列表中 | values: ["ssd", "nvme"] |
| NotIn | 标签值不在列表中 | values: ["hdd"] |
| Exists | 标签存在（不检查值） | key: "gpu" |
| DoesNotExist | 标签不存在 | key: "gpu" |
| Gt | 标签值大于（数值比较） | values: ["3"] |
| Lt | 标签值小于（数值比较） | values: ["5"] |

#### 6.3 Taint 与 Toleration — 污点与容忍

```bash
# 给节点设置污点
kubectl taint nodes node-01 dedicated=gpu:NoSchedule
# 含义：不容忍此污点的 Pod 不能调度到 node-01

# 查看节点污点
kubectl describe node node-01 | grep Taints

# 移除污点
kubectl taint nodes node-01 dedicated=gpu:NoSchedule-
```

```yaml
# toleration.yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-app
spec:
  tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "gpu"
    effect: "NoSchedule"
  containers:
  - name: app
    image: nvidia/cuda:12.0-base
```

**污点效果（Effect）：**

| Effect | 说明 |
|--------|------|
| NoSchedule | 不容忍的 Pod 不能调度到此节点（已有 Pod 不受影响） |
| PreferNoSchedule | 尽量不调度到此节点（软性） |
| NoExecute | 不容忍的 Pod 会被驱逐（已有 Pod 也受影响） |

**内置污点：**

```bash
# 节点不可用时自动添加的污点
node.kubernetes.io/not-ready           # 节点未就绪
node.kubernetes.io/unreachable         # 节点不可达
node.kubernetes.io/memory-pressure     # 内存压力
node.kubernetes.io/disk-pressure       # 磁盘压力
node.kubernetes.io/pid-pressure        # PID 压力
node.kubernetes.io/network-unavailable # 网络不可用
```

---

### 7. 健康检查（Probes）

#### 7.1 三种探针

```
┌──────────────────────────────────────────────────────────────────┐
│                    Kubernetes 健康检查探针                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Startup Probe (启动探针) — K8s 1.18+                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  目的: 检查容器是否已成功启动                            │     │
│  │  时机: 容器启动时执行，成功后不再执行                    │     │
│  │  失败: 超过 failureThreshold 后杀死容器                  │     │
│  │  场景: 启动时间长的应用（Java/Spring Boot）              │     │
│  │  特点: 启动期间 liveness/readiness 探针被禁用            │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Liveness Probe (存活探针)                                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  目的: 检查容器是否还在正常运行                          │     │
│  │  时机: 容器整个生命周期持续执行                          │     │
│  │  失败: 失败后重启容器（遵循 restartPolicy）              │     │
│  │  场景: 检测死锁、死循环等不可恢复故障                    │     │
│  │  注意: 失败会导致 Pod 重启！谨慎设置                     │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Readiness Probe (就绪探针)                                      │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  目的: 检查容器是否准备好接收流量                        │     │
│  │  时机: 容器整个生命周期持续执行                          │     │
│  │  失败: 从 Service 的 Endpoints 中移除（不接收流量）      │     │
│  │  场景: 预热缓存、建立数据库连接池                        │     │
│  │  特点: 不会重启容器，只是停止接收流量                    │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**探针执行流程：**

```
┌──────────────────────────────────────────────────────────────────┐
│                    探针执行时序                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  时间线 ──────────────────────────────────────────────────────>  │
│                                                                  │
│  容器启动                                                        │
│  │                                                               │
│  ├── Startup Probe 开始执行                                      │
│  │   ├── initialDelaySeconds: 0 (默认)                          │
│  │   ├── periodSeconds: 10 (默认)                               │
│  │   ├── failureThreshold: 3 (默认)                             │
│  │   ├── 失败 → 重启容器                                        │
│  │   └── 成功 → 停止，Liveness/Readiness 开始                   │
│  │                                                               │
│  ├── Liveness Probe 开始执行                                     │
│  │   ├── periodSeconds: 10 (默认)                               │
│  │   ├── failureThreshold: 3 (默认)                             │
│  │   ├── 连续失败 3 次 → 重启容器                               │
│  │   └── 成功 → 继续监控                                        │
│  │                                                               │
│  ├── Readiness Probe 开始执行                                    │
│  │   ├── periodSeconds: 10 (默认)                               │
│  │   ├── failureThreshold: 3 (默认)                             │
│  │   ├── 连续失败 3 次 → 从 Endpoints 移除                      │
│  │   ├── 成功 → 加回 Endpoints                                  │
│  │   └── 持续监控整个容器生命周期                               │
│  │                                                               │
│  └── 容器终止                                                    │
│      └── 探针停止执行                                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 7.2 探针探测方式

```yaml
# probe-types.yaml
apiVersion: v1
kind: Pod
metadata:
  name: probe-demo
spec:
  containers:
  - name: app
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80

    # 方式 1: HTTP GET 探针
    # 向容器发送 HTTP GET 请求，2xx/3xx 表示成功
    livenessProbe:
      httpGet:
        path: /healthz
        port: 80
        httpHeaders:
        - name: X-Custom-Header
          value: "health-check"
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3

    # 方式 2: TCP Socket 探针
    # 尝试建立 TCP 连接，连接成功表示健康
    readinessProbe:
      tcpSocket:
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 10
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3

    # 方式 3: Exec 探针
    # 在容器内执行命令，退出码 0 表示成功
    startupProbe:
      exec:
        command:
        - cat
        - /tmp/healthy
      initialDelaySeconds: 0
      periodSeconds: 10
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 30  # 允许 300 秒启动时间 (30 * 10s)

    # 方式 4: gRPC 探针 (K8s 1.27+ GA)
    # livenessProbe:
    #   grpc:
    #     port: 50051
```

**探针参数详解：**

| 参数 | 说明 | 默认值 | 建议值 |
|------|------|--------|--------|
| initialDelaySeconds | 容器启动后等待多久开始探测 | 0 | 根据应用启动时间设置 |
| periodSeconds | 探测间隔 | 10 | 10-30 |
| timeoutSeconds | 探测超时时间 | 1 | 3-5 |
| successThreshold | 连续成功几次算健康 | 1 | 1（liveness 必须为 1） |
| failureThreshold | 连续失败几次算不健康 | 3 | 3-5 |

#### 7.3 健康检查最佳实践

```yaml
# best-practice-probes.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:1.25-alpine
        ports:
        - containerPort: 80

        # Startup: 给慢启动应用足够时间
        # failureThreshold=30, periodSeconds=10 => 最多等 300 秒
        startupProbe:
          httpGet:
            path: /healthz
            port: 80
          failureThreshold: 30
          periodSeconds: 10

        # Liveness: 检测不可恢复的故障
        # 只检查核心功能，不要太严格
        livenessProbe:
          httpGet:
            path: /healthz
            port: 80
          periodSeconds: 15
          timeoutSeconds: 5
          failureThreshold: 3

        # Readiness: 检测是否准备好接收流量
        # 可以检查依赖服务（数据库、缓存等）
        readinessProbe:
          httpGet:
            path: /ready
            port: 80
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
          successThreshold: 1

        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
```

**SRE 健康检查设计原则：**

```
┌──────────────────────────────────────────────────────────────────┐
│                    健康检查设计原则                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Startup Probe:                                                  │
│  ✓ 对于启动慢的应用（Java/Spring），必须配置 startupProbe        │
│  ✓ failureThreshold * periodSeconds >= 预期启动时间              │
│  ✗ 不要在 startupProbe 中检查外部依赖                            │
│                                                                  │
│  Liveness Probe:                                                 │
│  ✓ 只检查应用自身是否存活（不检查外部依赖）                      │
│  ✓ 轻量级检查（不要调用数据库或外部 API）                        │
│  ✓ 检测死锁、内存泄漏等不可恢复故障                              │
│  ✗ 不要过于敏感（避免误杀健康容器）                              │
│  ✗ 不要在 liveness 中检查下游服务                                │
│                                                                  │
│  Readiness Probe:                                                │
│  ✓ 可以检查外部依赖（数据库、缓存、消息队列）                    │
│  ✓ 在应用预热完成前返回失败（如缓存加载中）                      │
│  ✓ 在无法处理请求时返回失败（如队列满）                          │
│  ✗ 不要返回永远失败（否则永远无法接收流量）                      │
│                                                                  │
│  /healthz vs /ready 端点设计：                                   │
│  /healthz: 应用进程存活，核心功能正常                            │
│  /ready:   应用可以处理请求，依赖服务可用                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 8. 优雅终止

#### 8.1 Pod 终止流程

```
┌──────────────────────────────────────────────────────────────────┐
│                    Pod 优雅终止流程                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ① kubectl delete pod <name>                                    │
│     │                                                            │
│     ▼                                                            │
│  ② API Server 更新 Pod 的 deletionTimestamp                      │
│     │                                                            │
│     ▼                                                            │
│  ③ kubelet 检测到 deletionTimestamp                              │
│     │                                                            │
│     ├──> ④ 执行 PreStop Hook（如果配置了）                       │
│     │        │                                                   │
│     │        ▼                                                   │
│     │    PreStop Hook 完成或超时                                  │
│     │                                                            │
│     ├──> ⑤ 向容器主进程发送 SIGTERM 信号                         │
│     │        │                                                   │
│     │        ├── 容器优雅关闭：                                  │
│     │        │   - 停止接收新请求                                │
│     │        │   - 处理完正在处理的请求                          │
│     │        │   - 关闭数据库连接                                │
│     │        │   - 刷新缓冲区                                    │
│     │        │   - 退出进程                                      │
│     │        │                                                   │
│     │        └── 容器忽略 SIGTERM → 继续等待                     │
│     │                                                            │
│     ├──> ⑥ 等待 terminationGracePeriodSeconds（默认 30s）       │
│     │                                                            │
│     └──> ⑦ 超时后发送 SIGKILL 强制杀死容器                       │
│            │                                                      │
│            ▼                                                      │
│     ⑧ Pod 从 API Server 删除                                     │
│                                                                  │
│   时间线:                                                         │
│   ├── 0s:   设置 deletionTimestamp                               │
│   ├── 0-30s: PreStop Hook + SIGTERM + 容器优雅关闭               │
│   └── 30s:  SIGKILL 强制终止                                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 8.2 PreStop Hook 配置

```yaml
# graceful-termination.yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-graceful
  labels:
    app: web
spec:
  terminationGracePeriodSeconds: 60  # 延长到 60 秒
  containers:
  - name: web
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
    lifecycle:
      preStop:
        # 方式 1: 执行命令
        exec:
          command:
          - /bin/sh
          - -c
          - |
            # 从 Service Endpoints 中摘除
            sleep 5
            # 停止接收新连接
            nginx -s quit
            # 等待现有连接完成
            sleep 10

        # 方式 2: HTTP 请求
        # httpGet:
        #   path: /shutdown
        #   port: 8080

    # 优雅终止配合的探针配置
    readinessProbe:
      httpGet:
        path: /ready
        port: 80
      periodSeconds: 5
```

**SRE 优雅终止最佳实践：**

```
┌──────────────────────────────────────────────────────────────────┐
│                    优雅终止最佳实践                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PreStop Hook 中先 sleep 一段时间                             │
│     原因: kube-proxy 更新 iptables 规则有延迟                    │
│     建议: sleep 5-15s，等待 Endpoints 更新完成                   │
│                                                                  │
│  2. 应用必须处理 SIGTERM 信号                                    │
│     - Go: 使用 signal.NotifyContext                              │
│     - Java: Runtime.addShutdownHook()                            │
│     - Node.js: process.on('SIGTERM', handler)                   │
│     - Python: signal.signal(signal.SIGTERM, handler)            │
│                                                                  │
│  3. terminationGracePeriodSeconds 要足够长                       │
│     - 大于 PreStop Hook 时间 + 优雅关闭时间                      │
│     - 建议: 30-120 秒（根据应用特性调整）                        │
│                                                                  │
│  4. 配合 PDB (PodDisruptionBudget) 使用                          │
│     - 确保滚动更新时始终有足够数量的 Pod 提供服务                │
│                                                                  │
│  5. 不要在 PreStop Hook 中做清理依赖的操作                       │
│     - 清理数据库连接、临时文件等应该在应用内部完成               │
│     - PreStop Hook 主要用于协调 shutdown 流程                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 9. SRE 实战案例

#### 9.1 Pod 启动失败排查

```
┌──────────────────────────────────────────────────────────────────┐
│                    Pod 启动失败排查决策树                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  kubectl get pod 显示:                                           │
│                                                                  │
│  ImagePullBackOff / ErrImagePull                                 │
│  ├── 检查镜像名称是否正确                                        │
│  ├── 检查镜像仓库是否可访问                                      │
│  ├── 检查 imagePullSecrets 是否配置                              │
│  └── 检查节点网络是否能访问镜像仓库                              │
│                                                                  │
│  CrashLoopBackOff                                                │
│  ├── kubectl logs <pod> 查看容器日志                             │
│  ├── kubectl logs <pod> --previous 查看上一次崩溃日志            │
│  ├── 检查 OOMKilled: describe pod 看 Last State                 │
│  ├── 检查启动命令是否正确                                        │
│  └── 检查配置文件/环境变量是否正确                               │
│                                                                  │
│  Pending                                                         │
│  ├── kubectl describe pod 查看 Events                            │
│  ├── FailedScheduling: 资源不足/污点不匹配                      │
│  ├── PVC Pending: PV 不存在或绑定失败                           │
│  └── 检查 nodeSelector/affinity 是否有匹配节点                  │
│                                                                  │
│  ContainerCreating (长时间)                                      │
│  ├── 检查 Volume 挂载是否正常                                    │
│  ├── 检查 ConfigMap/Secret 是否存在                              │
│  ├── 检查节点磁盘空间是否充足                                    │
│  └── 检查 CNI 插件是否正常                                       │
│                                                                  │
│  Init:Error / Init:CrashLoopBackOff                              │
│  ├── kubectl logs <pod> -c <init-container-name>                │
│  ├── 检查 init 容器逻辑是否正确                                  │
│  └── 检查 init 容器依赖的服务是否可用                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 9.2 OOMKilled 排查与处理

```bash
# 场景: Pod 频繁重启，状态显示 OOMKilled
# 排查步骤：

# 1. 确认 OOMKilled
kubectl describe pod <pod-name> | grep -A 5 "Last State"
# 输出: Reason: OOMKilled, Exit Code: 137

# 2. 查看容器实际内存使用
kubectl top pod <pod-name>
kubectl top pod <pod-name> --containers

# 3. 查看节点内存压力
kubectl describe node <node-name> | grep -A 5 "Conditions"
# 关注 MemoryPressure 条件

# 4. 查看 kubelet 驱逐日志
journalctl -u kubelet | grep -i evict

# 5. 解决方案:
# 方案 A: 增加 memory limits
# 方案 B: 优化应用内存使用
# 方案 C: 检查是否存在内存泄漏
# 方案 D: 使用 VPA 自动调整资源

# 6. 使用 VPA 推荐值
kubectl describe vpa <vpa-name> | grep "Lower Bound\|Target\|Upper Bound"
```

#### 9.3 Pod 网络问题排查

```bash
# 场景: Pod 之间无法通信
# 排查步骤：

# 1. 检查 Pod 网络状态
kubectl get pod <pod-name> -o jsonpath='{.status.podIP}'

# 2. 从 Pod 内部测试连通性
kubectl exec -it <pod-name> -- ping <target-pod-ip>
kubectl exec -it <pod-name> -- nslookup kubernetes.default
kubectl exec -it <pod-name> -- curl http://<service-name>:<port>

# 3. 检查 Service 和 Endpoints
kubectl get svc <service-name>
kubectl get endpoints <service-name>
# 如果 Endpoints 为空，说明没有就绪的 Pod 匹配 Service selector

# 4. 检查 NetworkPolicy
kubectl get networkpolicy -A
# NetworkPolicy 可能阻止了 Pod 间通信

# 5. 检查 CNI 插件
kubectl get pods -n kube-system | grep calico  # 或 flannel/weave
```

---

## 💻 实战练习

### 练习 1：Pod 基础操作

**目标：** 掌握 Pod 的创建、查看、调试

```bash
# 1. 创建一个带资源限制的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: practice-pod
  labels:
    app: practice
    env: dev
spec:
  containers:
  - name: nginx
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "200m"
        memory: "256Mi"
    livenessProbe:
      httpGet:
        path: /
        port: 80
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /
        port: 80
      periodSeconds: 5
EOF

# 2. 查看 Pod 详细信息
kubectl get pod practice-pod -o wide
kubectl describe pod practice-pod
kubectl get pod practice-pod -o yaml

# 3. 查看 Pod 日志
kubectl logs practice-pod
kubectl logs practice-pod --previous  # 查看上一次的日志

# 4. 进入容器调试
kubectl exec -it practice-pod -- /bin/sh
# 在容器内: curl localhost:80, cat /etc/os-release

# 5. 端口转发
kubectl port-forward practice-pod 8080:80
# 浏览器访问 http://localhost:8080

# 6. 查看 Pod 的 QoS 类别
kubectl get pod practice-pod -o jsonpath='{.status.qosClass}'

# 7. 清理
kubectl delete pod practice-pod
```

### 练习 2：Init 容器与 Sidecar

**目标：** 掌握 init 容器和 sidecar 模式的实际应用

```bash
# 1. 创建带 init 容器的 Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: init-demo
spec:
  initContainers:
  - name: init-service
    image: busybox:1.36
    command: ['sh', '-c', 'echo "Init container started" > /work-dir/index.html && echo "Init done"']
    volumeMounts:
    - name: workdir
      mountPath: /work-dir
  containers:
  - name: web
    image: nginx:1.25-alpine
    volumeMounts:
    - name: workdir
      mountPath: /usr/share/nginx/html
    ports:
    - containerPort: 80
  volumes:
  - name: workdir
    emptyDir: {}
EOF

# 2. 观察 init 容器执行
kubectl get pod init-demo -w  # watch 模式
kubectl logs init-demo -c init-service  # 查看 init 容器日志

# 3. 验证 init 容器的效果
kubectl exec -it init-demo -- cat /usr/share/nginx/html/index.html
kubectl port-forward init-demo 8081:80
curl http://localhost:8081

# 4. 创建带 sidecar 的 Pod（日志收集模拟）
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: sidecar-demo
spec:
  containers:
  - name: web
    image: nginx:1.25-alpine
    volumeMounts:
    - name: shared-logs
      mountPath: /var/log/nginx
    ports:
    - containerPort: 80
  - name: log-watcher
    image: busybox:1.36
    command: ['sh', '-c', 'tail -f /var/log/nginx/access.log']
    volumeMounts:
    - name: shared-logs
      mountPath: /var/log/nginx
      readOnly: true
  volumes:
  - name: shared-logs
    emptyDir: {}
EOF

# 5. 生成日志并观察 sidecar 收集
kubectl port-forward sidecar-demo 8082:80
curl http://localhost:8082
kubectl logs sidecar-demo -c log-watcher

# 6. 清理
kubectl delete pod init-demo sidecar-demo
```

### 练习 3：健康检查与优雅终止

**目标：** 配置和测试健康检查探针，理解优雅终止流程

```bash
# 1. 创建一个会延迟启动的应用
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: probe-practice
spec:
  terminationGracePeriodSeconds: 60
  containers:
  - name: app
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
    startupProbe:
      httpGet:
        path: /
        port: 80
      failureThreshold: 30
      periodSeconds: 10
    livenessProbe:
      httpGet:
        path: /
        port: 80
      periodSeconds: 15
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /
        port: 80
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 3
    lifecycle:
      preStop:
        exec:
          command:
          - /bin/sh
          - -c
          - "echo 'Shutting down...' && sleep 5 && nginx -s quit"
EOF

# 2. 观察探针执行
kubectl describe pod probe-practice | grep -A 10 "Conditions"
kubectl get events --field-selector involvedObject.name=probe-practice

# 3. 测试 Readiness Probe
# 修改 nginx 配置使 / 返回 500
kubectl exec probe-practice -- sh -c 'echo "server { listen 80; location / { return 500; } }" > /etc/nginx/conf.d/default.conf && nginx -s reload'
# 观察 Pod 状态变化
kubectl get pod probe-practice -w
# Readiness Probe 失败后，Pod Ready 状态变为 0/1

# 4. 恢复健康
kubectl exec probe-practice -- sh -c 'echo "server { listen 80; location / { return 200; } }" > /etc/nginx/conf.d/default.conf && nginx -s reload'

# 5. 测试优雅终止
kubectl delete pod probe-practice
# 在另一个终端观察:
kubectl get pod probe-practice -w
# 注意观察 Terminating 状态持续的时间

# 6. 清理
kubectl delete pod probe-practice --force --grace-period=0
```

---

## 🎯 面试题精选

### 1. Pod 为什么是 Kubernetes 的最小调度单位，而不是容器？

**参考答案：**

Pod 是最小调度单位的原因：
1. **共享网络**：Pod 内容器共享 Network Namespace，可通过 localhost 通信，避免了容器间的服务发现和端口映射问题
2. **共享存储**：Pod 内容器可通过 Volume 共享数据，实现数据交换（如日志收集场景）
3. **共同调度**：紧密耦合的容器需要在同一节点运行，Pod 作为一个整体被调度
4. **生命周期管理**：Pod 提供统一的生命周期管理，所有容器同生共死
5. **资源隔离与共享的平衡**：Pod 是资源分配的最小单位，内部容器共享资源但互相隔离

如果直接调度容器，将难以表达"这些容器需要在一起运行"的需求。

### 2. Init 容器和普通容器有什么区别？

**参考答案：**

| 特性 | Init 容器 | 普通容器 |
|------|----------|---------|
| 执行顺序 | 按顺序串行执行 | 并行执行 |
| 执行时机 | 主容器启动之前 | 与 Pod 生命周期相同 |
| 重启策略 | 失败后 Pod 重启，重新执行所有 init 容器 | 遵循 Pod 的 restartPolicy |
| 就绪探针 | 不支持 | 支持 |
| PreStop Hook | 不支持 | 支持 |
| 用途 | 初始化、等待依赖、数据准备 | 运行业务逻辑 |

### 3. 三种 QoS 类别有什么区别？在什么情况下会被驱逐？

**参考答案：**

- **Guaranteed**：所有容器的 requests == limits。最后被驱逐，适合关键服务
- **Burstable**：至少一个容器设置了 requests 或 limits，但不相等。中等优先级
- **BestEffort**：没有设置任何 requests 或 limits。最先被驱逐

驱逐顺序：节点内存不足时，kubelet 按 BestEffort → Burstable → Guaranteed 的顺序驱逐 Pod。同类别内，超过 requests 的 Pod 优先被驱逐。

SRE 建议：生产环境的关键服务必须配置为 Guaranteed，避免在资源紧张时被误杀。

### 4. Liveness Probe 和 Readiness Probe 有什么区别？使用不当会有什么问题？

**参考答案：**

| 特性 | Liveness Probe | Readiness Probe |
|------|---------------|-----------------|
| 目的 | 检测容器是否存活 | 检测容器是否准备好接收流量 |
| 失败后果 | 重启容器 | 从 Service Endpoints 移除 |
| 影响范围 | 容器重启 | 不接收流量，但容器继续运行 |
| 检查内容 | 应用核心功能 | 应用 + 外部依赖 |

使用不当的问题：
- **Liveness 过于严格**：频繁重启容器（如检查数据库连接，数据库短暂不可用就重启）
- **Liveness 过于宽松**：容器已经不健康但不重启（如死锁检测不到）
- **Readiness 检查外部依赖**：依赖服务短暂不可用时，所有 Pod 同时从 Endpoints 移除，导致服务完全不可用
- **没有配置 Startup Probe**：启动慢的应用被 Liveness Probe 误杀

### 5. Pod 的优雅终止流程是怎样的？为什么需要 PreStop Hook？

**参考答案：**

优雅终止流程：
1. 用户删除 Pod（kubectl delete）
2. API Server 设置 Pod 的 deletionTimestamp
3. kubelet 检测到后执行 PreStop Hook
4. 向容器主进程发送 SIGTERM 信号
5. 等待 terminationGracePeriodSeconds（默认 30s）
6. 超时后发送 SIGKILL 强制杀死

需要 PreStop Hook 的原因：
- kube-proxy 更新 iptables/IPVS 规则有延迟，可能在 Pod 收到 SIGTERM 后仍有流量路由到该 Pod
- 在 PreStop 中 sleep 5-15s，等待 Endpoints 更新完成，确保不会有新流量到达
- 应用可以在此期间完成清理工作（关闭连接、刷新缓冲区等）

### 6. 什么是 Sidecar 模式？列举常见用途。

**参考答案：**

Sidecar 模式是在 Pod 中添加辅助容器来增强主容器功能。主容器和 Sidecar 共享网络和存储，但职责不同。

常见用途：
1. **日志收集**：Fluentd/Filebeat 容器读取主容器的日志文件并转发到日志系统
2. **Service Mesh 代理**：Envoy/Istio Proxy 拦截主容器的网络流量，实现服务网格功能
3. **配置热更新**：ConfigMap Reload 容器监听配置变化并通知主容器重新加载
4. **安全代理**：Vault Agent 从 HashiCorp Vault 获取密钥并注入到主容器
5. **数据库代理**：Cloud SQL Proxy 提供到云数据库的安全连接

### 7. 如何设置资源请求和限制？requests 和 limits 的最佳实践是什么？

**参考答案：**

```yaml
resources:
  requests:
    cpu: "250m"      # 调度保证
    memory: "128Mi"
  limits:
    cpu: "500m"      # 硬性上限
    memory: "256Mi"
```

最佳实践：
1. **必须设置 requests**：调度器依赖 requests 做出调度决策
2. **必须设置 memory limits**：防止容器 OOM 影响节点
3. **CPU limits 可选**：允许 CPU 突发，但设置 limits 可防止单个容器独占 CPU
4. **requests:limits 比例**：CPU 建议 50%-100%，Memory 建议 80%-100%
5. **使用 LimitRange 设置默认值**：防止遗忘
6. **使用 ResourceQuota 限制总量**：防止命名空间超分配

### 8. 如何排查 Pod 处于 CrashLoopBackOff 状态？

**参考答案：**

排查步骤：
```bash
# 1. 查看当前日志
kubectl logs <pod-name>

# 2. 查看上一次崩溃的日志
kubectl logs <pod-name> --previous

# 3. 查看详细信息（退出码、重启次数）
kubectl describe pod <pod-name>

# 4. 常见退出码：
# 0: 正常退出（可能是启动命令配置错误）
# 1: 应用错误
# 137: OOMKilled 或被外部 kill -9
# 139: SIGSEGV (段错误)
# 143: SIGTERM (收到终止信号)

# 5. 如果是 OOMKilled，增加 memory limits
# 6. 如果是应用错误，修复代码或配置
# 7. 如果启动命令错误，检查 command 和 args
```

### 9. Startup Probe 的作用是什么？什么场景下必须使用？

**参考答案：**

Startup Probe 用于检查容器是否已成功启动。在 Startup Probe 成功之前，Liveness Probe 和 Readiness Probe 会被禁用。

必须使用的场景：
1. **Java/Spring Boot 应用**：启动时间可能需要 30-120 秒，如果只用 Liveness Probe（默认 failureThreshold=3, periodSeconds=10），容器可能在启动完成前就被重启
2. **需要加载大量数据的应用**：启动时需要加载缓存、预热连接池
3. **初始化复杂的微服务**：需要注册到服务发现、建立各种连接

配置建议：`failureThreshold * periodSeconds >= 预期最大启动时间`

### 10. Kubernetes 如何决定驱逐哪些 Pod？

**参考答案：**

Kubernetes 通过 kubelet 的 eviction 机制驱逐 Pod：

驱逐触发条件：
- `memory.available` < 阈值（默认 200Mi）
- `nodefs.available` < 阈值（默认 10%）
- `imagefs.available` < 阈值（默认 15%）
- `pid.available` < 阈值（默认 1000）

驱逐优先级（从先到后）：
1. BestEffort Pod 中超过 requests 的
2. Burstable Pod 中超过 requests 的
3. 所有 BestEffort Pod
4. Burstable Pod 中使用量接近 requests 的
5. Guaranteed Pod（最后被驱逐）

```bash
# 查看 kubelet 驱逐阈值
kubectl describe node <node-name> | grep -A 10 "Conditions"

# 查看驱逐事件
kubectl get events --field-selector reason=Evicted
```

---

## 📚 深入阅读

- [Kubernetes 官方文档 - Pod](https://kubernetes.io/zh-cn/docs/concepts/workloads/pods/)
- [Kubernetes 官方文档 - Pod 生命周期](https://kubernetes.io/zh-cn/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes 官方文档 - Init 容器](https://kubernetes.io/zh-cn/docs/concepts/workloads/pods/init-containers/)
- [Kubernetes 官方文档 - 资源管理](https://kubernetes.io/zh-cn/docs/concepts/configuration/manage-resources-containers/)
- [Kubernetes 官方文档 - 配置 Liveness, Readiness 和 Startup 探针](https://kubernetes.io/zh-cn/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Kubernetes 官方文档 - 优雅终止](https://kubernetes.io/zh-cn/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination)

---

## ✅ 自检清单

- [ ] 理解 Pod 的设计哲学（为什么是最小调度单位）
- [ ] 掌握 Pod 生命周期的 5 个阶段（Pending/Running/Succeeded/Failed/Unknown）
- [ ] 理解 restartPolicy 的三种策略及其行为
- [ ] 能编写 Init 容器配置，理解其执行顺序和失败处理
- [ ] 理解 Sidecar 模式及其常见应用场景
- [ ] 掌握 requests/limits 的配置和 QoS 类别的判断
- [ ] 理解三种 QoS 类别的驱逐优先级
- [ ] 能配置 Startup/Liveness/Readiness 三种探针
- [ ] 理解每种探针的适用场景和配置不当的后果
- [ ] 掌握 Pod 优雅终止流程和 PreStop Hook 的使用
- [ ] 能排查常见的 Pod 问题（ImagePullBackOff、CrashLoopBackOff、OOMKilled）
