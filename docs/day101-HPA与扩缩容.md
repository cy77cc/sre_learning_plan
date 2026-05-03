# Day 101: HPA 与扩缩容

> 📅 日期：2026-05-03
> 📖 学习主题：Horizontal Pod Autoscaler、Vertical Pod Autoscaler、Cluster Autoscaler、KEDA 事件驱动扩缩容
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 93-99（K8s 基础）、Day 100（调度器与亲和性）

## 🎯 学习目标

- 深入理解 HPA（Horizontal Pod Autoscaler）的工作原理与算法
- 掌握基于 CPU、Memory、Custom Metrics 的 HPA 配置
- 理解 VPA（Vertical Pod Autoscaler）的使用场景与限制
- 掌握 Cluster Autoscaler 的节点自动扩缩容
- 理解 KEDA 事件驱动扩缩容架构
- 能够设计生产级的扩缩容策略

---

## 📖 核心知识点

### 1. Kubernetes 扩缩容体系概览

```
┌─────────────────────────────────────────────────────────────────┐
│                Kubernetes 扩缩容体系                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐     │
│  │     HPA     │  │     VPA     │  │  Cluster Autoscaler │     │
│  │  水平扩缩容  │  │  垂直扩缩容  │  │    节点自动扩缩      │     │
│  │  (Pod 数量)  │  │  (资源限制)  │  │    (节点数量)        │     │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘     │
│         │                │                     │                │
│         v                v                     v                │
│  调整 Pod 副本数   调整 Pod CPU/       增减节点数量              │
│                    Memory 请求/限制                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    KEDA                                 │   │
│  │              事件驱动自动扩缩容                           │   │
│  │    (基于队列长度、消息数、自定义指标等)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. HPA（Horizontal Pod Autoscaler）

#### 2.1 HPA 工作原理

```
HPA 控制循环（默认 15 秒）：

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Metrics API │────>│ HPA Controller│────>│  Scale      │
│  (指标采集)   │     │  (计算期望副本)│     │  (调整副本数)│
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                     │
       v                    v                     v
  采集当前指标        对比目标值              更新 Deployment
  (CPU/Memory/        计算期望副本数           的 replicas
   Custom)            公式如下
```

**HPA 扩缩容公式**：

```
期望副本数 = ceil[当前副本数 × (当前指标值 / 目标指标值)]

示例：
  当前副本数: 4
  当前 CPU 利用率: 80%
  目标 CPU 利用率: 50%

  期望副本数 = ceil[4 × (80 / 50)] = ceil[6.4] = 7

缩容时需要满足稳定窗口（默认 5 分钟），避免抖动
```

#### 2.2 HPA 版本对比

| 特性 | autoscaling/v1 | autoscaling/v2 |
|------|---------------|----------------|
| 指标类型 | 仅 CPU | CPU/Memory/Custom/External |
| 多指标支持 | 不支持 | 支持 |
| 自定义指标 | 不支持 | 支持 |
| 扩缩容行为配置 | 不支持 | 支持 |
| 推荐使用 | 不推荐 | 推荐 |

#### 2.3 基于 CPU 的 HPA 配置

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70  # CPU 利用率目标 70%
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60  # 扩容稳定窗口 60 秒
      policies:
        - type: Pods
          value: 4  # 每次最多增加 4 个 Pod
          periodSeconds: 60
        - type: Percent
          value: 100  # 每次最多增加 100% 的 Pod
          periodSeconds: 60
      selectPolicy: Max  # 选择最大的扩容幅度
    scaleDown:
      stabilizationWindowSeconds: 300  # 缩容稳定窗口 5 分钟
      policies:
        - type: Pods
          value: 2  # 每次最多减少 2 个 Pod
          periodSeconds: 60
      selectPolicy: Min  # 选择最小的缩容幅度（保守策略）
```

#### 2.4 基于 Memory 的 HPA 配置

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-memory-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 15
  metrics:
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80  # 内存利用率目标 80%
```

#### 2.5 多指标 HPA 配置

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-multi-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 3
  maxReplicas: 30
  metrics:
    # 指标 1：CPU 利用率
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    # 指标 2：内存利用率
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    # 指标 3：自定义指标（请求数/秒）
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

**多指标的决策逻辑**：HPA 会分别计算每个指标的期望副本数，取最大值作为最终的期望副本数。例如：
- CPU 指标计算出需要 5 个副本
- Memory 指标计算出需要 8 个副本
- Custom 指标计算出需要 3 个副本
- 最终：取最大值 8 个副本

#### 2.6 基于自定义指标的 HPA

```yaml
# 前提：安装 Prometheus Adapter 或 Keda
# kubectl apply -f https://github.com/kubernetes-sigs/prometheus-adapter/releases/latest/download/prometheus-adapter.yaml

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-custom-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
    # 自定义指标：每秒请求数
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "500"
    # 自定义指标：请求延迟 P99
    - type: Pods
      pods:
        metric:
          name: http_request_duration_seconds_p99
        target:
          type: AverageValue
          averageValue: "500m"  # 500ms
```

#### 2.7 基于 External 指标的 HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: queue-processor-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: queue-processor
  minReplicas: 1
  maxReplicas: 50
  metrics:
    # 外部指标：SQS 队列长度
    - type: External
      external:
        metric:
          name: sqs_queue_messages_visible
          selector:
            matchLabels:
              queue: "task-queue"
        target:
          type: AverageValue
          averageValue: "10"  # 每个 Pod 处理 10 条消息
```

#### 2.8 HPA 扩缩容行为详解

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: detailed-behavior-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
  behavior:
    # 扩容行为
    scaleUp:
      # 種定窗口：在此窗口内只记录最大的推荐值
      stabilizationWindowSeconds: 60
      policies:
        # 策略 1：每 60 秒最多增加 4 个 Pod
        - type: Pods
          value: 4
          periodSeconds: 60
        # 策略 2：每 60 秒最多增加当前副本数的 100%
        - type: Percent
          value: 100
          periodSeconds: 60
      # Max: 选择最大的扩容幅度（快速扩容）
      # Min: 选择最小的扩容幅度（保守扩容）
      # Disabled: 禁用扩容
      selectPolicy: Max

    # 缩容行为
    scaleDown:
      # 稳定窗口：5 分钟内只记录最大的推荐值
      # 这意味着缩容会更保守，避免频繁抖动
      stabilizationWindowSeconds: 300
      policies:
        # 每 60 秒最多减少 1 个 Pod（保守缩容）
        - type: Pods
          value: 1
          periodSeconds: 60
      selectPolicy: Min  # 选择最小的缩容幅度
```

#### 2.9 HPA 的限制与注意事项

```
重要限制：

1. HPA 需要 Metrics Server 提供指标数据
   - 默认不安装，需要手动安装
   - kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

2. Pod 必须设置资源请求（requests）
   - HPA 计算的是 requests 的利用率，不是 limits
   - 未设置 requests 的 Pod 不会被 HPA 管理

3. HPA 与 VPA 不能同时管理同一资源
   - HPA 管理副本数，VPA 管理资源限制
   - 两者同时管理同一 Deployment 会导致冲突

4. 缩容有冷却时间
   - 默认稳定窗口 5 分钟
   - 避免指标抖动导致频繁扩缩容

5. HPA 不会驱逐正在运行的 Pod
   - 缩容时会选择最新的 Pod 进行删除
   - 通过 Deployment 的 rollingUpdate 策略执行
```

---

### 3. Metrics Server — HPA 的指标数据源

#### 3.1 Metrics Server 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Metrics Server                            │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  kubelet     │───>│  Metrics     │───>│  Metrics API │  │
│  │  (cAdvisor)  │    │  Aggregator  │    │  (metrics.   │  │
│  │  采集容器指标 │    │  聚合指标     │    │   k8s.io)    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                      │      │
│                                                      v      │
│                                              ┌──────────┐   │
│                                              │   HPA    │   │
│                                              │ Controller│  │
│                                              └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 安装 Metrics Server

```yaml
# metrics-server.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: metrics-server
  namespace: kube-system
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: metrics-server
  namespace: kube-system
spec:
  selector:
    matchLabels:
      k8s-app: metrics-server
  template:
    metadata:
      labels:
        k8s-app: metrics-server
    spec:
      serviceAccountName: metrics-server
      containers:
        - name: metrics-server
          image: registry.k8s.io/metrics-server/metrics-server:v0.6.4
          args:
            - --cert-dir=/tmp
            - --secure-port=4443
            - --kubelet-preferred-address-types=InternalIP,ExternalIP,Hostname
            - --kubelet-use-node-status-port
            - --metric-resolution=15s
            # 如果是自签名证书的环境，添加以下参数
            - --kubelet-insecure-tls
          ports:
            - name: https
              containerPort: 4443
              protocol: TCP
          resources:
            requests:
              cpu: 100m
              memory: 200Mi
            limits:
              cpu: 300m
              memory: 400Mi
```

```bash
# 安装 Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 或使用 Helm 安装
helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/
helm upgrade --install metrics-server metrics-server/metrics-server \
  --namespace kube-system \
  --set args="{--kubelet-insecure-tls}"

# 验证安装
kubectl get pods -n kube-system | grep metrics-server

# 查看节点指标
kubectl top nodes

# 查看 Pod 指标
kubectl top pods -n production

# 查看 Pod 的具体指标
kubectl top pods -n production --containers
```

---

### 4. VPA（Vertical Pod Autoscaler）

#### 4.1 VPA 工作原理

```
┌─────────────────────────────────────────────────────────────┐
│                    VPA 架构                                  │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  VPA         │    │  VPA         │    │  VPA         │  │
│  │  Recommender │    │  Updater     │    │  Admission   │  │
│  │  推荐资源     │    │  驱逐更新     │    │  Controller  │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                    │          │
│         v                   v                    v          │
│  分析历史指标          驱逐资源不合理的    修改 Pod 的        │
│  推荐最优资源          Pod（触发重建）    资源请求           │
│                                                             │
│  三种模式：                                                  │
│  - Off:      仅推荐，不自动调整                               │
│  - Initial:  仅在 Pod 创建时设置资源                           │
│  - Auto:     自动调整（会重启 Pod）                            │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2 VPA 配置示例

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: web-app-vpa
  namespace: production
spec:
  # 目标工作负载
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  # 更新策略
  updatePolicy:
    updateMode: "Auto"  # Off / Initial / Auto
  # 资源策略
  resourcePolicy:
    containerPolicies:
      - containerName: web
        minAllowed:
          cpu: "100m"
          memory: "128Mi"
        maxAllowed:
          cpu: "4"
          memory: "8Gi"
        controlledResources: ["cpu", "memory"]
        controlledValues: RequestsAndLimits  # RequestsOnly / RequestsAndLimits
```

#### 4.3 VPA 使用场景与限制

```
适用场景：
  ✓ 开发/测试环境的资源自动调整
  ✓ 不规则负载模式的工作负载
  ✓ 无法预估资源需求的新服务

限制与注意事项：
  ✗ VPA 会重启 Pod 来调整资源（影响可用性）
  ✗ 不能与 HPA 同时管理同一资源的 CPU/Memory
  ✗ 需要足够的历史数据才能做出准确推荐
  ✗ 生产环境建议使用 Off 模式仅获取推荐值
```

---

### 5. Cluster Autoscaler — 节点自动扩缩容

#### 5.1 Cluster Autoscaler 工作原理

```
┌─────────────────────────────────────────────────────────────┐
│                Cluster Autoscaler                            │
│                                                             │
│  扩容流程：                                                  │
│  1. 检测到 Pending Pod（因资源不足无法调度）                   │
│  2. 检查 Node Group 是否可以扩容                              │
│  3. 计算需要增加的节点数量                                    │
│  4. 调用云 API 创建新节点                                     │
│  5. 新节点加入集群，Pod 被调度                                 │
│                                                             │
│  缩容流程：                                                  │
│  1. 检测到低利用率节点（< 50% 请求资源）                      │
│  2. 检查节点上的 Pod 是否可以迁移到其他节点                    │
│  3. 检查 Pod 是否有 PDB 保护                                  │
│  4. 驱逐节点上的 Pod                                          │
│  5. 调用云 API 删除节点                                       │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 Cluster Autoscaler 部署

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
        - name: cluster-autoscaler
          image: registry.k8s.io/autoscaling/cluster-autoscaler:v1.28.0
          command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
            - --balance-similar-node-groups
            - --skip-nodes-with-system-pods=false
            # 扩缩容范围
            - --scale-down-utilization-threshold=0.5
            - --scale-down-delay-after-add=10m
            - --scale-down-delay-after-delete=1m
            - --scale-down-delay-after-failure=3m
            - --max-graceful-termination-sec=600
          resources:
            limits:
              cpu: 100m
              memory: 600Mi
            requests:
              cpu: 100m
              memory: 300Mi
```

#### 5.3 Cluster Autoscaler 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| scale-down-utilization-threshold | 节点利用率低于此值触发缩容 | 0.5 |
| scale-down-delay-after-add | 扩容后多久允许缩容 | 10m |
| scale-down-delay-after-delete | 缩容后多久允许再次缩容 | 0s |
| scale-down-unneeded-time | 节点空闲多久后缩容 | 10m |
| max-node-provision-time | 节点最大供应时间 | 15m |
| max-graceful-termination-sec | Pod 最大优雅终止时间 | 600s |
| expander | 节点组选择策略 | random |
| balance-similar-node-groups | 均衡相似节点组 | false |

#### 5.4 扩缩容流程图

```
扩容流程：

Pending Pod (Insufficient cpu)
    │
    ├── 1. Cluster Autoscaler 检测到 Pending Pod
    │
    ├── 2. 检查哪个 Node Group 可以满足
    │   ├── 评估每个 Node Group 的容量
    │   └── 选择最合适的 Node Group
    │
    ├── 3. 调用云 API 创建新节点
    │
    ├── 4. 等待节点就绪（最长 max-node-provision-time）
    │
    └── 5. Pod 被调度到新节点

缩容流程：

低利用率节点 (< 50%)
    │
    ├── 1. 检测节点利用率低于阈值
    │
    ├── 2. 检查节点上的 Pod 是否可以迁移
    │   ├── 检查是否有本地存储
    │   ├── 检查 PDB 约束
    │   └── 检查 Pod 中断预算
    │
    ├── 3. 标记节点为不可调度
    │
    ├── 4. 驱逐节点上的 Pod
    │
    ├── 5. 等待 Pod 优雅终止
    │
    └── 6. 删除节点
```

---

### 6. KEDA — 事件驱动自动扩缩容

#### 6.1 KEDA 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    KEDA 架构                                 │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  KEDA        │    │  Scaler      │    │  Metrics     │  │
│  │  Operator    │───>│  (200+       │───>│  Server      │  │
│  │  (核心控制器) │    │   Scaler)    │    │  (指标服务)   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                                       │          │
│         v                                       v          │
│  创建 ScaledObject                          HPA Controller  │
│  管理扩缩容策略                              基于外部指标    │
│                                             自动扩缩容       │
│                                                             │
│  支持的事件源：                                               │
│  - Apache Kafka    - RabbitMQ        - AWS SQS             │
│  - Redis           - PostgreSQL      - MySQL               │
│  - Prometheus      - AWS CloudWatch  - Azure Event Hub      │
│  - Cron            - HTTP            - 200+ 其他           │
└─────────────────────────────────────────────────────────────┘
```

#### 6.2 KEDA 安装

```bash
# 使用 Helm 安装 KEDA
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda \
  --namespace keda \
  --create-namespace

# 验证安装
kubectl get pods -n keda
```

#### 6.3 KEDA ScaledObject 配置

```yaml
# 基于 RabbitMQ 队列长度的扩缩容
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: rabbitmq-scaledobject
  namespace: production
spec:
  scaleTargetRef:
    name: queue-processor  # 目标 Deployment
  pollingInterval: 15  # 每 15 秒检查一次指标
  cooldownPeriod: 300  # 缩容冷却时间 5 分钟
  idleReplicaCount: 0  # 空闲时缩容到 0 个 Pod
  minReplicaCount: 1  # 最少 1 个 Pod
  maxReplicaCount: 50  # 最多 50 个 Pod
  triggers:
    - type: rabbitmq
      metadata:
        host: amqp://user:password@rabbitmq.production.svc:5672
        queueName: task-queue
        queueLength: "10"  # 每个 Pod 处理 10 条消息
      authenticationRef:
        name: rabbitmq-auth  # 引用 TriggerAuthentication

---
# TriggerAuthentication（存储认证信息）
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: rabbitmq-auth
  namespace: production
spec:
  secretTargetRef:
    - parameter: host
      name: rabbitmq-secret
      key: connection-string
```

#### 6.4 KEDA Cron Scaler

```yaml
# 定时扩缩容：工作时间扩容，非工作时间缩容
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaledobject
  namespace: production
spec:
  scaleTargetRef:
    name: web-app
  minReplicaCount: 2
  maxReplicaCount: 30
  idleReplicaCount: 2
  triggers:
    # 工作时间（9:00-18:00）扩容
    - type: cron
      metadata:
        timezone: Asia/Shanghai
        start: "0 9 * * *"  # 每天 9:00
        end: "0 18 * * *"   # 每天 18:00
        desiredReplicas: "10"
    # 高峰时间（11:00-14:00）进一步扩容
    - type: cron
      metadata:
        timezone: Asia/Shanghai
        start: "0 11 * * *"
        end: "0 14 * * *"
        desiredReplicas: "20"
```

#### 6.5 KEDA Prometheus Scaler

```yaml
# 基于 Prometheus 指标的扩缩容
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: prometheus-scaledobject
  namespace: production
spec:
  scaleTargetRef:
    name: api-server
  minReplicaCount: 2
  maxReplicaCount: 50
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        metricName: http_requests_per_second
        query: |
          sum(rate(http_requests_total{namespace="production", app="api-server"}[2m]))
        threshold: "1000"  # 每个 Pod 处理 1000 QPS
        activationThreshold: "100"  # 低于 100 QPS 时缩容到最小副本数
```

#### 6.6 KEDA 与 HPA 对比

| 特性 | HPA | KEDA |
|------|-----|------|
| 指标来源 | Metrics Server | 200+ 外部事件源 |
| 缩容到 0 | 不支持 | 支持（idleReplicaCount: 0） |
| 定时扩缩容 | 不支持 | 支持（Cron Scaler） |
| 队列驱动 | 不支持 | 原生支持 |
| 复杂度 | 低 | 中 |
| 适用场景 | 基于资源指标 | 事件驱动、队列驱动 |

---

### 7. 生产级扩缩容策略设计

#### 7.1 综合扩缩容方案

```
生产环境推荐的扩缩容架构：

┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Layer 1: HPA（Pod 水平扩缩容）                              │
│  ├── 基于 CPU/Memory 的基础扩缩容                            │
│  ├── 基于自定义指标（QPS、延迟）的精细扩缩容                   │
│  └── 配置合理的 behavior 策略                                │
│                                                             │
│  Layer 2: VPA（Pod 垂直扩缩容）                              │
│  ├── Off 模式：仅获取资源推荐                                 │
│  └── 定期审查并手动调整资源请求                               │
│                                                             │
│  Layer 3: Cluster Autoscaler（节点扩缩容）                    │
│  ├── 自动增减节点以满足 Pod 资源需求                          │
│  └── 配置合理的缩容阈值和延迟                                │
│                                                             │
│  Layer 4: KEDA（事件驱动扩缩容）                             │
│  ├── 队列驱动的异步任务处理                                   │
│  ├── 定时扩缩容策略                                          │
│  └── 支持缩容到 0                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 7.2 SRE 实战：Web 服务扩缩容方案

```yaml
# Web 服务的完整扩缩容配置
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 3
  maxReplicas: 50
  metrics:
    # CPU 利用率
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
    # 内存利用率
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 75
    # 自定义指标：QPS
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "500"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
        - type: Pods
          value: 10
          periodSeconds: 60
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
      selectPolicy: Min
```

#### 7.3 SRE 实战：异步任务处理扩缩容方案

```yaml
# 异步任务处理器的 KEDA 扩缩容配置
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: task-processor-keda
  namespace: production
spec:
  scaleTargetRef:
    name: task-processor
  pollingInterval: 10
  cooldownPeriod: 300
  idleReplicaCount: 0  # 无任务时缩容到 0
  minReplicaCount: 1
  maxReplicaCount: 100
  triggers:
    # SQS 队列长度
    - type: aws-sqs-queue
      metadata:
        queueURL: https://sqs.us-east-1.amazonaws.com/123456789/task-queue
        queueLength: "5"
        awsRegion: us-east-1
      authenticationRef:
        name: aws-credentials
    # 工作时间额外扩容
    - type: cron
      metadata:
        timezone: Asia/Shanghai
        start: "0 9 * * 1-5"  # 工作日 9:00
        end: "0 18 * * 1-5"   # 工作日 18:00
        desiredReplicas: "5"
```

#### 7.4 SRE 实战：扩缩容监控与告警

```yaml
# PrometheusRule：扩缩容监控告警
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: hpa-alerts
  namespace: monitoring
spec:
  groups:
    - name: hpa-alerts
      rules:
        # HPA 接近最大副本数
        - alert: HPAHighReplicas
          expr: |
            kube_horizontalpodautoscaler_status_current_replicas
            / kube_horizontalpodautoscaler_spec_max_replicas > 0.9
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "HPA {{ $labels.horizontalpodautoscaler }} 接近最大副本数"
            description: "当前副本数已达到最大副本数的 90%"

        # HPA 持续扩容
        - alert: HPAScalingUp
          expr: |
            increase(kube_horizontalpodautoscaler_status_current_replicas[30m]) > 5
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "HPA {{ $labels.horizontalpodautoscaler }} 持续扩容"
            description: "过去 30 分钟内副本数增加了 5 个以上"

        # HPA 无法扩容（资源不足）
        - alert: HPAUnableToScale
          expr: |
            kube_horizontalpodautoscaler_status_condition{condition="ScalingActive",status="false"} == 1
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "HPA {{ $labels.horizontalpodautoscaler }} 无法扩缩容"
            description: "HPA 控制器无法正常工作"
```

---

### 8. 扩缩容故障排查

#### 8.1 HPA 故障排查

```bash
# 1. 检查 HPA 状态
kubectl get hpa -n production
kubectl describe hpa web-app-hpa -n production

# 2. 常见问题：Metrics not available
# 原因：Metrics Server 未安装或未就绪
kubectl get pods -n kube-system | grep metrics-server
kubectl top nodes

# 3. 常见问题：Unable to compute metrics
# 原因：Pod 未设置资源请求
kubectl get deployment web-app -n production -o jsonpath='{.spec.template.spec.containers[0].resources}'

# 4. 常见问题：HPA 不扩容
# 检查当前指标值
kubectl get hpa web-app-hpa -n production -o yaml | grep -A 10 "currentMetrics"

# 5. 常见问题：HPA 频繁扩缩容
# 调整 stabilizationWindowSeconds
# 增加缩容的冷却时间

# 6. 查看 HPA 事件
kubectl get events -n production --field-selector involvedObject.name=web-app-hpa
```

#### 8.2 Cluster Autoscaler 故障排查

```bash
# 1. 查看 Cluster Autoscaler 日志
kubectl logs -n kube-system -l app=cluster-autoscaler --tail=100

# 2. 查看扩缩容状态
kubectl get configmap cluster-autoscaler-status -n kube-system -o yaml

# 3. 常见问题：节点未被缩容
# 检查节点上的 Pod 是否有本地存储
# 检查 Pod 的 PDB 约束
# 检查是否有 system Pod 在节点上

# 4. 常见问题：节点未被扩容
# 检查 Node Group 的最大节点数限制
# 检查云 API 权限
# 检查节点启动模板是否正确
```

---

## 💻 实战练习

### 练习 1：基础 HPA 配置

**目标**：为 Deployment 配置基于 CPU 的自动扩缩容

```bash
# 步骤 1：确保 Metrics Server 已安装
kubectl get pods -n kube-system | grep metrics-server

# 步骤 2：创建测试应用
kubectl create deployment php-apache --image=registry.k8s.io/hpa-example --port=80
kubectl set resources deployment php-apache --requests=cpu=100m

# 步骤 3：创建 HPA
kubectl autoscale deployment php-apache --cpu-percent=50 --min=1 --max=10

# 步骤 4：验证 HPA
kubectl get hpa php-apache

# 步骤 5：模拟负载
kubectl run -i --tty load-generator --rm --image=busybox:1.36 -- /bin/sh
# 在容器内执行：
# while true; do wget -q -O- http://php-apache.default.svc.cluster.local; done

# 步骤 6：观察扩缩容
kubectl get hpa php-apache --watch
kubectl get pods --watch
```

### 练习 2：多指标 HPA 与行为配置

**目标**：配置基于 CPU + Memory + 自定义指标的 HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: multi-metric-hpa
  namespace: default
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: php-apache
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
      selectPolicy: Min
```

### 练习 3：故障排查 — HPA 不工作

**场景**：HPA 创建后一直显示 `<unknown>` 指标，Pod 不扩缩容。

排查步骤：
```bash
# 1. 检查 HPA 状态
kubectl describe hpa <hpa-name>

# 2. 检查 Metrics Server
kubectl get pods -n kube-system | grep metrics-server
kubectl top nodes

# 3. 检查 Pod 资源请求
kubectl get deployment <name> -o jsonpath='{.spec.template.spec.containers[0].resources}'

# 4. 检查 HPA 事件
kubectl get events --field-selector involvedObject.name=<hpa-name>

# 5. 可能的原因：
#    - Metrics Server 未安装
#    - Pod 未设置 resources.requests
#    - Metrics Server 启动失败（证书问题）
#    - HPA 的 scaleTargetRef 配置错误
```

---

## 🎯 面试题精选

### 1. HPA 的扩缩容公式是什么？

**答**：`期望副本数 = ceil[当前副本数 × (当前指标值 / 目标指标值)]`

例如：当前 4 个副本，CPU 利用率 80%，目标 50%，则 `ceil[4 × (80/50)] = ceil[6.4] = 7` 个副本。

### 2. HPA 多指标时如何决策？

**答**：HPA 分别计算每个指标的期望副本数，取最大值作为最终期望副本数。这确保了所有指标都在目标范围内。

### 3. HPA 的 behavior 中 stabilizationWindowSeconds 的作用？

**答**：稳定窗口（stabilizationWindowSeconds）是缩容/扩容的防抖机制。在窗口时间内，HPA 只记录最大/最小的推荐值，避免指标抖动导致频繁扩缩容。扩容默认 0 秒，缩容默认 300 秒（5 分钟）。

### 4. HPA 和 VPA 能同时使用吗？

**答**：不能同时管理同一资源的 CPU/Memory。HPA 管理副本数（水平），VPA 管理资源限制（垂直）。如果同时使用，VPA 调整资源请求后会导致 HPA 的利用率计算基准变化，产生冲突。建议：使用 HPA 管理副本数，VPA 设置为 Off 模式仅提供资源推荐。

### 5. Cluster Autoscaler 什么时候会缩容节点？

**答**：节点满足以下条件才会被缩容：
- 节点利用率低于阈值（默认 50%）
- 节点上的所有 Pod 可以迁移到其他节点
- 没有 Pod 有本地存储（或设置了相关注解）
- Pod 的 PDB 允许中断
- 节点空闲时间超过阈值（默认 10 分钟）
- 不是刚扩容的节点（有延迟保护）

### 6. KEDA 相比 HPA 有什么优势？

**答**：
- 支持 200+ 外部事件源（SQS、Kafka、RabbitMQ 等）
- 可以缩容到 0 个 Pod（HPA 最少 1 个）
- 支持 Cron 定时扩缩容
- 支持复合触发器（多个条件组合）
- 适用于事件驱动和异步任务场景

### 7. 如何避免 HPA 的"抖动"（频繁扩缩容）？

**答**：
1. 增大 `stabilizationWindowSeconds`（特别是 scaleDown）
2. 设置保守的缩容策略（`selectPolicy: Min`）
3. 使用 `Pods` 类型而非 `Percent` 类型的策略
4. 合理设置 `periodSeconds`
5. 确保指标采集的稳定性（避免指标抖动）

### 8. Metrics Server 的作用是什么？如何排查其问题？

**答**：Metrics Server 通过 kubelet 的 cAdvisor 采集节点和容器的 CPU/Memory 指标，提供给 HPA 和 `kubectl top` 使用。

排查步骤：
```bash
kubectl get pods -n kube-system | grep metrics-server
kubectl logs -n kube-system -l k8s-app=metrics-server
kubectl top nodes
```
常见问题：证书问题（需添加 `--kubelet-insecure-tls`）、端口不通、资源不足。

### 9. HPA 的 selectPolicy 有哪几种？有什么区别？

**答**：
- `Max`：选择最大的扩缩容幅度（扩容时用，快速响应）
- `Min`：选择最小的扩缩容幅度（缩容时用，保守策略）
- `Disabled`：禁用该方向的扩缩容

### 10. 生产环境如何设计完整的扩缩容策略？

**答**：
1. **Layer 1 - HPA**：基于 CPU/Memory 和自定义指标的 Pod 水平扩缩容，配置合理的 behavior 策略
2. **Layer 2 - VPA**：Off 模式获取资源推荐，定期审查并手动调整
3. **Layer 3 - Cluster Autoscaler**：节点自动扩缩容，配合 HPA 使用
4. **Layer 4 - KEDA**：事件驱动场景（队列、定时任务），支持缩容到 0
5. **监控告警**：HPA 接近上限、持续扩容、无法扩容等场景的告警

---

## 📚 深入阅读

- [Kubernetes 官方文档：Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes 官方文档：HPA 行为配置](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior)
- [Kubernetes 官方文档：Metrics Server](https://github.com/kubernetes-sigs/metrics-server)
- [Kubernetes 官方文档：Vertical Pod Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- [Kubernetes 官方文档：Cluster Autoscaler](https://github.com/kubernetes/autoscaler/tree/master/cluster-autoscaler)
- [KEDA 官方文档](https://keda.sh/docs/)
- [Kubernetes HPA 最佳实践](https://learnk8s.io/horizontal-pod-autoscaler-best-practices)

---

## ✅ 自检清单

- [ ] 能够解释 HPA 的扩缩容公式和工作原理
- [ ] 能够配置基于 CPU/Memory 的 HPA
- [ ] 能够配置基于自定义指标的 HPA
- [ ] 能够配置 HPA 的 behavior 策略（稳定窗口、扩缩容策略）
- [ ] 能够安装和配置 Metrics Server
- [ ] 理解 VPA 的三种模式（Off/Initial/Auto）及使用场景
- [ ] 能够配置 Cluster Autoscaler 的扩缩容参数
- [ ] 能够使用 KEDA 配置事件驱动扩缩容
- [ ] 能够排查 HPA 不工作的常见原因
- [ ] 能够设计生产级的综合扩缩容策略
