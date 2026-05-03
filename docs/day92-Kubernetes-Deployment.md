# Day 92: Kubernetes Deployment

> 📅 日期：2026-05-03
> 📖 学习主题：声明式管理、滚动更新、回滚、扩缩容、ReplicaSet、金丝雀/蓝绿部署
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 90 Kubernetes 架构, Day 91 Kubernetes Pod

---

## 🎯 学习目标

- 深入理解 Deployment 的声明式管理模型和控制循环
- 掌握滚动更新策略的配置与调优
- 熟练使用回滚机制处理发布故障
- 掌握手动和自动扩缩容方法
- 理解 ReplicaSet 的工作原理及其与 Deployment 的关系
- 掌握金丝雀部署和蓝绿部署的实现方式

---

## 📖 核心知识点

### 1. Deployment 概述

#### 1.1 什么是 Deployment

Deployment 是 Kubernetes 中最常用的工作负载资源，用于**声明式管理无状态应用**。它通过管理 ReplicaSet 来管理 Pod，提供**滚动更新**、**回滚**、**扩缩容**等能力。

**核心设计思想：声明式管理**

```
┌──────────────────────────────────────────────────────────────────┐
│                    声明式 vs 命令式                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  命令式 (Imperative):                                            │
│  "做 X，然后做 Y，然后做 Z"                                      │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  kubectl run nginx --image=nginx:1.24                   │     │
│  │  kubectl scale deployment nginx --replicas=3            │     │
│  │  kubectl set image deployment nginx nginx=nginx:1.25    │     │
│  │                                                          │     │
│  │  问题:                                                   │     │
│  │  - 操作顺序敏感                                          │     │
│  │  - 难以审计和追踪                                        │     │
│  │  - 无法版本控制                                          │     │
│  │  - 不适合 GitOps                                        │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  声明式 (Declarative):                                           │
│  "我想要状态 X"                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  kubectl apply -f deployment.yaml                       │     │
│  │                                                          │     │
│  │  YAML 文件描述了期望的最终状态:                           │     │
│  │  - 3 个 nginx:1.25 副本                                  │     │
│  │  - 每个副本 256Mi 内存                                   │     │
│  │  - 滚动更新策略                                          │     │
│  │                                                          │     │
│  │  优势:                                                   │     │
│  │  - K8s 自动计算需要执行的操作                             │     │
│  │  - 可存储在 Git 中，版本控制                              │     │
│  │  - 支持 GitOps 工作流                                    │     │
│  │  - 幂等：多次 apply 结果相同                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 1.2 Deployment 与 ReplicaSet 的关系

```
┌──────────────────────────────────────────────────────────────────┐
│                Deployment → ReplicaSet → Pod 控制链               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  Deployment: web-app                                      │  │
│   │  replicas: 3, image: nginx:1.25                          │  │
│   │  revision: 2                                              │  │
│   └────────────────────────┬─────────────────────────────────┘  │
│                            │ 管理                                 │
│                            ▼                                     │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  ReplicaSet: web-app-7d4b8c9f6 (当前版本)                 │  │
│   │  replicas: 3, template: nginx:1.25                       │  │
│   │  revision: 2                                              │  │
│   └────────────────────────┬─────────────────────────────────┘  │
│                            │ 管理                                 │
│                  ┌─────────┼─────────┐                           │
│                  ▼         ▼         ▼                           │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│   │  Pod-1   │ │  Pod-2   │ │  Pod-3   │                        │
│   │ nginx:1.25│ │ nginx:1.25│ │ nginx:1.25│                     │
│   └──────────┘ └──────────┘ └──────────┘                        │
│                                                                  │
│   旧版本 ReplicaSet (保留用于回滚):                               │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  ReplicaSet: web-app-5d8f7b6a4 (旧版本)                   │  │
│   │  replicas: 0, template: nginx:1.24                       │  │
│   │  revision: 1                                              │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│   控制链: Deployment → ReplicaSet → Pod                          │
│   - Deployment 管理 ReplicaSet（通过 revision 控制版本）         │
│   - ReplicaSet 管理 Pod（通过 replicas 控制副本数）              │
│   - Deployment 不直接管理 Pod                                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 1.3 Deployment YAML 完整解析

```yaml
# deployment-full.yaml
apiVersion: apps/v1              # API 版本
kind: Deployment                 # 资源类型
metadata:
  name: web-app                  # Deployment 名称
  namespace: production          # 命名空间
  labels:                        # Deployment 自身的标签
    app: web
    team: platform
  annotations:
    kubernetes.io/change-cause: "Initial deployment v1.25"  # 变更原因（记录在 revision 中）
spec:
  # ============ 副本数 ============
  replicas: 3                    # 期望的 Pod 副本数

  # ============ 选择器 ============
  selector:
    matchLabels:                 # 必须与 template.metadata.labels 匹配
      app: web                   # 选择器一旦设置不可更改

  # ============ 更新策略 ============
  strategy:
    type: RollingUpdate          # 更新策略：RollingUpdate 或 Recreate
    rollingUpdate:
      maxUnavailable: 1          # 更新过程中最多不可用的 Pod 数
      maxSurge: 1                # 更新过程中最多超出期望副本数的 Pod 数

  # ============ 修订历史限制 ============
  revisionHistoryLimit: 10       # 保留的旧 ReplicaSet 数量（默认 10）

  # ============ 进度截止时间 ============
  progressDeadlineSeconds: 600   # 更新进度超时时间（默认 600s）

  # ============ 最小就绪时间 ============
  minReadySeconds: 10            # Pod 就绪后等待多久才认为可用

  # ============ Pod 模板 ============
  template:
    metadata:
      labels:                    # Pod 的标签，必须匹配 selector
        app: web
        version: v1.25
        team: platform
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      # 服务账号
      serviceAccountName: web-app

      # 安全上下文
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000

      # 亲和性
      affinity:
        podAntiAffinity:         # Pod 反亲和：分散到不同节点
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values: ["web"]
              topologyKey: kubernetes.io/hostname

      # 容器定义
      containers:
      - name: web
        image: nginx:1.25-alpine
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 80
          name: http
          protocol: TCP
        - containerPort: 8080
          name: metrics
          protocol: TCP

        # 环境变量
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password

        # 资源配置
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"

        # 健康检查
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 15
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3

        # 优雅终止
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10 && nginx -s quit"]

        # 存储挂载
        volumeMounts:
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
        - name: tls-certs
          mountPath: /etc/nginx/ssl
          readOnly: true

      # 终止宽限期
      terminationGracePeriodSeconds: 60

      # 卷定义
      volumes:
      - name: config
        configMap:
          name: nginx-config
      - name: tls-certs
        secret:
          secretName: tls-certs
```

---

### 2. 滚动更新（Rolling Update）

#### 2.1 滚动更新原理

```
┌──────────────────────────────────────────────────────────────────┐
│                    滚动更新过程（maxSurge=1, maxUnavailable=1）   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  初始状态: 3 个 v1 副本                                          │
│  ┌─────┐ ┌─────┐ ┌─────┐                                        │
│  │ v1  │ │ v1  │ │ v1  │                                        │
│  │ Pod1│ │ Pod2│ │ Pod3│                                        │
│  └─────┘ └─────┘ └─────┘                                        │
│  期望: 3, 可用: 3, 不可用: 0                                     │
│                                                                  │
│  Step 1: 创建 1 个 v2 Pod（maxSurge=1，允许超出 1 个）          │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                                │
│  │ v1  │ │ v1  │ │ v1  │ │ v2  │  (新创建，等待就绪)            │
│  │ Pod1│ │ Pod2│ │ Pod3│ │ Pod4│                                 │
│  └─────┘ └─────┘ └─────┘ └─────┘                                │
│  期望: 3, 可用: 3, 不可用: 0, 总数: 4                           │
│                                                                  │
│  Step 2: v2 Pod 就绪后，删除 1 个 v1 Pod（maxUnavailable=1）    │
│  ┌─────┐ ┌─────┐ ┌─────┐                                        │
│  │ v1  │ │ v1  │ │ v2  │                                        │
│  │ Pod1│ │ Pod2│ │ Pod4│  (Pod3 已删除)                          │
│  └─────┘ └─────┘ └─────┘                                        │
│  期望: 3, 可用: 3, 不可用: 0                                     │
│                                                                  │
│  Step 3: 继续创建 1 个 v2 Pod                                    │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                                │
│  │ v1  │ │ v1  │ │ v2  │ │ v2  │                                │
│  │ Pod1│ │ Pod2│ │ Pod4│ │ Pod5│                                 │
│  └─────┘ └─────┘ └─────┘ └─────┘                                │
│                                                                  │
│  Step 4: v2 Pod5 就绪后，删除 1 个 v1 Pod                       │
│  ┌─────┐ ┌─────┐ ┌─────┐                                        │
│  │ v1  │ │ v2  │ │ v2  │                                        │
│  │ Pod1│ │ Pod4│ │ Pod5│                                         │
│  └─────┘ └─────┘ └─────┘                                        │
│                                                                  │
│  Step 5: 继续...                                                │
│  ┌─────┐ ┌─────┐ ┌─────┐                                        │
│  │ v2  │ │ v2  │ │ v2  │                                        │
│  │ Pod4│ │ Pod5│ │ Pod6│  (最终状态)                            │
│  └─────┘ └─────┘ └─────┘                                        │
│  期望: 3, 可用: 3, 不可用: 0                                     │
│                                                                  │
│  关键点:                                                          │
│  - 整个过程中可用 Pod 数始终 >= replicas - maxUnavailable        │
│  - 总 Pod 数始终 <= replicas + maxSurge                          │
│  - 新 Pod 必须通过 Readiness Probe 后才会删除旧 Pod              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 2.2 更新策略参数调优

```yaml
# 不同场景的策略配置
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 25%    # 可以是绝对数或百分比
      maxSurge: 25%          # 可以是绝对数或百分比
```

**策略参数对比：**

| 场景 | maxUnavailable | maxSurge | 特点 |
|------|---------------|----------|------|
| 零停机发布 | 0 | 1 | 始终保持所有旧 Pod 运行，先创建新 Pod |
| 快速发布 | 1 | 1 | 平衡速度和可用性 |
| 大规模快速 | 25% | 25% | 默认策略，适合大部分场景 |
| 资源紧张 | 1 | 0 | 不创建额外 Pod，先删旧再建新 |
| 完全替换 | 100% | 100% | 一次替换所有 Pod（类似 Recreate） |

```bash
# 执行滚动更新
# 方式 1: 修改 YAML 后 apply
kubectl apply -f deployment.yaml

# 方式 2: 直接更新镜像
kubectl set image deployment/web-app web=nginx:1.26-alpine --record

# 方式 3: 编辑 Deployment
kubectl edit deployment web-app

# 查看更新状态
kubectl rollout status deployment/web-app

# 查看更新历史
kubectl rollout history deployment/web-app

# 暂停更新（用于多个字段同时修改）
kubectl rollout pause deployment/web-app
# ... 多次修改 ...
kubectl rollout resume deployment/web-app

# 查看更新过程中的 ReplicaSet
kubectl get rs -l app=web
```

#### 2.3 Recreate 策略

```yaml
# 策略对比
spec:
  strategy:
    type: Recreate  # 先删除所有旧 Pod，再创建新 Pod
```

```
┌──────────────────────────────────────────────────────────────────┐
│           RollingUpdate vs Recreate                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RollingUpdate (滚动更新):                                       │
│  ┌─────┐ ┌─────┐ ┌─────┐     ┌─────┐ ┌─────┐ ┌─────┐          │
│  │ v1  │ │ v1  │ │ v1  │ ──> │ v2  │ │ v2  │ │ v2  │          │
│  └─────┘ └─────┘ └─────┘     └─────┘ └─────┘ └─────┘          │
│  逐步替换，过程中始终有 Pod 提供服务                             │
│  适用: 大部分无状态 Web 应用                                     │
│                                                                  │
│  Recreate (重建):                                                │
│  ┌─────┐ ┌─────┐ ┌─────┐     ┌─────┐ ┌─────┐ ┌─────┐          │
│  │ v1  │ │ v1  │ │ v1  │ ──> │     │ │     │ │     │          │
│  └─────┘ └─────┘ └─────┘     └─────┘ └─────┘ └─────┘          │
│         全部删除                  全部创建 v2                     │
│  ┌─────┐ ┌─────┐ ┌─────┐                                        │
│  │ v2  │ │ v2  │ │ v2  │                                        │
│  └─────┘ └─────┘ └─────┘                                        │
│  有停机时间，但保证同一时间只有一个版本运行                       │
│  适用: 不支持多版本并行的应用（如数据库 schema 变更）             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 3. 回滚（Rollback）

#### 3.1 版本控制机制

```
┌──────────────────────────────────────────────────────────────────┐
│                    Deployment 版本控制                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Deployment: web-app                                             │
│  │                                                               │
│  ├── Revision 1 (nginx:1.24)                                    │
│  │   └── ReplicaSet: web-app-5d8f7b6a4 (replicas: 0)           │
│  │       (旧版本，保留用于回滚)                                  │
│  │                                                               │
│  ├── Revision 2 (nginx:1.25)                                    │
│  │   └── ReplicaSet: web-app-7d4b8c9f6 (replicas: 3)           │
│  │       (当前版本)                                              │
│  │                                                               │
│  └── Revision 3 (nginx:1.26) — 如果发生过回滚，当前版本          │
│      └── ReplicaSet: web-app-9e8d7c6b5 (replicas: 3)           │
│                                                                  │
│  revisionHistoryLimit: 10  # 默认保留 10 个历史版本              │
│  设为 0 禁用历史记录（节省资源但无法回滚）                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.2 回滚操作

```bash
# 查看更新历史
kubectl rollout history deployment/web-app
# 输出:
# REVISION  CHANGE-CAUSE
# 1         Initial deployment v1.24
# 2         Update to nginx 1.25
# 3         Update to nginx 1.26

# 查看特定版本的详情
kubectl rollout history deployment/web-app --revision=2

# 回滚到上一个版本
kubectl rollout undo deployment/web-app

# 回滚到指定版本
kubectl rollout undo deployment/web-app --to-revision=2

# 查看回滚状态
kubectl rollout status deployment/web-app

# 回滚后查看新的 ReplicaSet
kubectl get rs -l app=web
```

**SRE 回滚最佳实践：**

```
┌──────────────────────────────────────────────────────────────────┐
│                    SRE 回滚最佳实践                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 发布前: 确保 revisionHistoryLimit 足够大（至少 5-10）        │
│                                                                  │
│  2. 发布时: 使用 --record 记录变更原因                           │
│     kubectl set image deployment/web web=nginx:1.26 --record     │
│     或在 annotations 中添加 kubernetes.io/change-cause           │
│                                                                  │
│  3. 发布后: 监控关键指标（错误率、延迟、CPU/内存）               │
│     - 如果指标异常，立即执行回滚                                 │
│     - 不要等所有 Pod 更新完成再回滚                              │
│                                                                  │
│  4. 回滚验证:                                                    │
│     - 确认回滚到正确的版本                                       │
│     - 验证应用功能恢复正常                                       │
│     - 检查日志是否有异常                                         │
│                                                                  │
│  5. 注意事项:                                                    │
│     - 回滚只回滚 Pod 模板（image/配置），不回滚其他字段          │
│     - 回滚实际上是一次新的更新（创建新 revision）                │
│     - 如果旧版本的 ReplicaSet 已被清理，无法回滚                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 4. 扩缩容（Scaling）

#### 4.1 手动扩缩容

```bash
# 方式 1: kubectl scale
kubectl scale deployment/web-app --replicas=5

# 方式 2: kubectl edit
kubectl edit deployment/web-app
# 修改 spec.replicas: 5

# 方式 3: kubectl patch
kubectl patch deployment web-app -p '{"spec":{"replicas":5}}'

# 方式 4: 修改 YAML 后 apply
# 编辑 deployment.yaml 中的 replicas: 5
kubectl apply -f deployment.yaml

# 查看扩缩容状态
kubectl get deployment web-app
kubectl get rs -l app=web
kubectl get pods -l app=web
```

#### 4.2 自动扩缩容（HPA）

```yaml
# hpa.yaml
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
  maxReplicas: 10
  metrics:
  # 基于 CPU 使用率
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # 目标 CPU 使用率 70%

  # 基于内存使用率
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

  # 基于自定义指标（需要 Prometheus Adapter）
  # - type: Pods
  #   pods:
  #     metric:
  #       name: http_requests_per_second
  #     target:
  #       type: AverageValue
  #       averageValue: "1000"

  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60    # 扩容稳定窗口
      policies:
      - type: Percent
        value: 100                       # 每次最多扩容 100%
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300   # 缩容稳定窗口（5分钟）
      policies:
      - type: Percent
        value: 10                        # 每次最多缩容 10%
        periodSeconds: 60
```

```bash
# 创建 HPA
kubectl apply -f hpa.yaml

# 或使用命令行创建
kubectl autoscale deployment web-app --cpu-percent=70 --min=2 --max=10

# 查看 HPA 状态
kubectl get hpa
kubectl describe hpa web-app-hpa

# 查看 HPA 事件（扩缩容原因）
kubectl get events --field-selector involvedObject.name=web-app-hpa

# 查看指标
kubectl top pods -l app=web
```

**HPA 工作原理：**

```
┌──────────────────────────────────────────────────────────────────┐
│                    HPA 工作流程                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│   │  HPA         │────>│  Metrics     │────>│  Pod 指标     │   │
│   │  Controller  │     │  Server      │     │  (CPU/Memory) │   │
│   └──────┬───────┘     └──────────────┘     └──────────────┘   │
│          │                                                       │
│          │ 计算期望副本数:                                        │
│          │ desiredReplicas = ceil(currentReplicas *              │
│          │                     currentMetricValue / desiredMetricValue) │
│          │                                                       │
│          │ 例: 3 * (85% / 70%) = ceil(3.64) = 4                │
│          │                                                       │
│          ▼                                                       │
│   ┌──────────────┐                                               │
│   │  更新        │                                               │
│   │  Deployment  │                                               │
│   │  replicas: 4 │                                               │
│   └──────────────┘                                               │
│                                                                  │
│   前置条件:                                                       │
│   - 安装 Metrics Server（minikube addons enable metrics-server）│
│   - Pod 必须设置 resources.requests（HPA 基于 requests 计算）   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 5. ReplicaSet 深入理解

#### 5.1 ReplicaSet 控制循环

```
┌──────────────────────────────────────────────────────────────────┐
│                ReplicaSet 控制循环                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ReplicaSet spec:                                                │
│    replicas: 3                                                   │
│    selector: { app: web }                                       │
│                                                                  │
│  控制循环:                                                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  1. 列出所有匹配 selector 的 Pod                        │     │
│  │     kubectl get pods -l app=web                         │     │
│  │     结果: [pod-1, pod-2]  (只有 2 个)                   │     │
│  │                                                          │     │
│  │  2. 比较: 期望 3 vs 实际 2 → 差 1                      │     │
│  │                                                          │     │
│  │  3. 执行: 创建 1 个新 Pod                               │     │
│  │                                                          │     │
│  │  4. 等待下一次循环（默认 ~1 秒）                        │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  持续循环:                                                        │
│  - 监听 Pod 创建/删除事件                                        │
│  - Pod 被删除 → 发现实例不足 → 创建新 Pod                       │
│  - 手动创建匹配 selector 的 Pod → 发现实例过多 → 删除多余 Pod   │
│  - Pod 状态变更 → 更新 ReplicaSet status                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.2 ReplicaSet 与 Deployment 的协作

```bash
# 查看 Deployment 管理的 ReplicaSet
kubectl get rs -l app=web
# 输出:
# NAME               DESIRED   CURRENT   READY   AGE
# web-app-5d8f7b6    0         0         0       2d   (旧版本)
# web-app-7d4b8c9    3         3         3       1h   (当前版本)

# 查看 ReplicaSet 的详细信息
kubectl describe rs web-app-7d4b8c9

# 注意: 不要手动修改 Deployment 管理的 ReplicaSet
# Deployment Controller 会覆盖你的修改

# 查看 Pod 的 OwnerReference（确认归属关系）
kubectl get pod web-app-7d4b8c9-xxxxx -o jsonpath='{.metadata.ownerReferences}'
```

---

### 6. 金丝雀部署与蓝绿部署

#### 6.1 金丝雀部署（Canary Deployment）

金丝雀部署是将新版本逐步推送给一小部分用户，验证无问题后再全量发布。

```
┌──────────────────────────────────────────────────────────────────┐
│                    金丝雀部署                                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  阶段 1: 全量运行 v1                                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Service (selector: app=web)                              │   │
│  │    ├── Pod v1 (33%)                                       │   │
│  │    ├── Pod v1 (33%)                                       │   │
│  │    └── Pod v1 (33%)                                       │   │
│  │  流量分配: v1 = 100%                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  阶段 2: 金丝雀发布（10% 流量到 v2）                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Deployment v1: replicas=3                                │   │
│  │  Deployment v2 (canary): replicas=1                       │   │
│  │  Service (selector: app=web) — 同时匹配 v1 和 v2         │   │
│  │    ├── Pod v1                                             │   │
│  │    ├── Pod v1                                             │   │
│  │    ├── Pod v1                                             │   │
│  │    └── Pod v2 (canary)                                    │   │
│  │  流量分配: v1 = 75%, v2 = 25% (4 个 Pod 等权分配)        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  阶段 3: 金丝雀验证通过，全量发布 v2                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Deployment v1: replicas=0                                │   │
│  │  Deployment v2: replicas=4                                │   │
│  │    ├── Pod v2                                             │   │
│  │    ├── Pod v2                                             │   │
│  │    ├── Pod v2                                             │   │
│  │    └── Pod v2                                             │   │
│  │  流量分配: v2 = 100%                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**金丝雀部署实现：**

```yaml
# canary-deployment.yaml
# 主 Deployment (稳定版)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app-stable
  labels:
    app: web
    track: stable
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
      track: stable
  template:
    metadata:
      labels:
        app: web
        track: stable
        version: v1.25
    spec:
      containers:
      - name: web
        image: nginx:1.25-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
---
# 金丝雀 Deployment (新版本)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app-canary
  labels:
    app: web
    track: canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web
      track: canary
  template:
    metadata:
      labels:
        app: web
        track: canary
        version: v1.26
    spec:
      containers:
      - name: web
        image: nginx:1.26-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
---
# Service 同时匹配 stable 和 canary
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web  # 匹配所有 track
  ports:
  - port: 80
    targetPort: 80
```

**金丝雀部署的流量控制（使用 Ingress 注解）：**

```yaml
# 使用 Nginx Ingress 实现金丝雀流量分配
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"  # 10% 流量到 canary
spec:
  ingressClassName: nginx
  rules:
  - host: web.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-app-canary
            port:
              number: 80
```

#### 6.2 蓝绿部署（Blue-Green Deployment）

蓝绿部署同时维护两个完整环境，通过切换流量实现零停机部署。

```
┌──────────────────────────────────────────────────────────────────┐
│                    蓝绿部署                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  阶段 1: 蓝色环境（当前版本）提供服务                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Service (selector: app=web, version=blue)               │   │
│  │         │                                                │   │
│  │         ├── Pod v1 (blue)                                │   │
│  │         ├── Pod v1 (blue)                                │   │
│  │         └── Pod v1 (blue)                                │   │
│  │                                                          │   │
│  │  Deployment green (replicas=3, 不接收流量)               │   │
│  │         ├── Pod v2 (green)                               │   │
│  │         ├── Pod v2 (green)                               │   │
│  │         └── Pod v2 (green)                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  阶段 2: 切换 Service selector 到绿色环境                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Service (selector: app=web, version=green)  ← 切换！    │   │
│  │         │                                                │   │
│  │         ├── Pod v2 (green)                               │   │
│  │         ├── Pod v2 (green)                               │   │
│  │         └── Pod v2 (green)                               │   │
│  │                                                          │   │
│  │  Deployment blue (replicas=3, 不接收流量，待回滚)        │   │
│  │         ├── Pod v1 (blue)                                │   │
│  │         ├── Pod v1 (blue)                                │   │
│  │         └── Pod v1 (blue)                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  优势: 切换瞬间完成，真正的零停机                                │
│  劣势: 需要双倍资源，同一时间只有一个版本提供服务                │
│  回滚: 只需将 Service selector 切回旧版本                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```yaml
# blue-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app-blue
  labels:
    app: web
    version: blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
      version: blue
  template:
    metadata:
      labels:
        app: web
        version: blue
    spec:
      containers:
      - name: web
        image: nginx:1.25-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
---
# green-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app-green
  labels:
    app: web
    version: green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
      version: green
  template:
    metadata:
      labels:
        app: web
        version: green
    spec:
      containers:
      - name: web
        image: nginx:1.26-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
---
# service.yaml — 切换 selector 实现蓝绿切换
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web
    version: blue  # 切换为 green 即可实现蓝绿部署
  ports:
  - port: 80
    targetPort: 80
```

```bash
# 蓝绿切换操作
# 1. 部署绿色版本
kubectl apply -f green-deployment.yaml

# 2. 验证绿色版本
kubectl get pods -l app=web,version=green
# 等待所有 Pod 就绪

# 3. 切换流量（一行命令实现零停机）
kubectl patch service web-app -p '{"spec":{"selector":{"version":"green"}}}'

# 4. 验证切换
kubectl describe svc web-app
kubectl get endpoints web-app

# 5. 回滚（如果需要）
kubectl patch service web-app -p '{"spec":{"selector":{"version":"blue"}}}'

# 6. 确认无问题后清理旧版本
kubectl scale deployment web-app-blue --replicas=0
# 或完全删除
kubectl delete deployment web-app-blue
```

**部署策略对比：**

| 策略 | 停机时间 | 资源消耗 | 回滚速度 | 复杂度 | 适用场景 |
|------|---------|---------|---------|--------|---------|
| RollingUpdate | 无 | 低 | 慢 | 低 | 大部分无状态应用 |
| Recreate | 有 | 低 | 慢 | 低 | 不支持多版本并行的应用 |
| Blue-Green | 无 | 双倍 | 快（秒级） | 中 | 关键服务、需要快速回滚 |
| Canary | 无 | 低+少量 | 快 | 高 | 高风险变更、需要逐步验证 |

---

### 7. Deployment 高级配置

#### 7.1 PodDisruptionBudget (PDB)

```yaml
# pdb.yaml — 确保滚动更新和节点维护时始终保持最少可用 Pod 数
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
spec:
  minAvailable: 2  # 至少保持 2 个 Pod 可用
  # 或使用 maxUnavailable
  # maxUnavailable: 1
  selector:
    matchLabels:
      app: web
```

```bash
# 查看 PDB 状态
kubectl get pdb web-app-pdb
kubectl describe pdb web-app-pdb
```

#### 7.2 Pod 亲和性与反亲和性

```yaml
spec:
  template:
    spec:
      affinity:
        # Pod 反亲和：分散到不同节点（高可用）
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values: ["web"]
            topologyKey: kubernetes.io/hostname

        # 或分散到不同可用区
        # podAntiAffinity:
        #   preferredDuringSchedulingIgnoredDuringExecution:
        #   - weight: 100
        #     podAffinityTerm:
        #       labelSelector:
        #         matchExpressions:
        #         - key: app
        #           operator: In
        #           values: ["web"]
        #       topologyKey: topology.kubernetes.io/zone
```

---

### 8. SRE 实战案例

#### 8.1 发布故障快速回滚

```
┌──────────────────────────────────────────────────────────────────┐
│                    发布故障回滚流程                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景: 发布新版本后，错误率从 0.1% 飙升到 5%                     │
│                                                                  │
│  Step 1: 确认问题                                                │
│  ├── 监控告警: 错误率 > 1%                                       │
│  ├── kubectl rollout status: 查看更新进度                        │
│  └── kubectl get pods: 查看新 Pod 状态                           │
│                                                                  │
│  Step 2: 决策 - 回滚                                             │
│  ├── kubectl rollout undo deployment/web-app                     │
│  └── kubectl rollout status deployment/web-app                   │
│                                                                  │
│  Step 3: 验证恢复                                                │
│  ├── 监控: 错误率回落到 0.1%                                     │
│  ├── kubectl get pods: 确认 Pod 全部 Running                     │
│  └── 功能验证: 核心业务流程正常                                  │
│                                                                  │
│  Step 4: 复盘                                                    │
│  ├── 查看回滚后的 revision: kubectl rollout history              │
│  ├── 分析新版本失败原因                                          │
│  ├── 修复后重新发布                                              │
│  └── 更新发布检查清单                                            │
│                                                                  │
│  时间线:                                                          │
│  T+0s:  告警触发                                                 │
│  T+30s: 确认问题，执行回滚                                       │
│  T+60s: 回滚完成，新 Pod 开始启动                                │
│  T+120s: 新 Pod 就绪，流量切换完成                               │
│  T+180s: 监控确认恢复正常                                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 8.2 Deployment 更新卡住排查

```bash
# 场景: kubectl rollout status 长时间不完成

# 1. 查看更新状态
kubectl rollout status deployment/web-app
# 输出: Waiting for rollout to finish: 2 out of 3 new replicas have been updated...

# 2. 查看 ReplicaSet 状态
kubectl get rs -l app=web -o wide
# 查看 DESIRED 和 READY 的差异

# 3. 查看新 Pod 状态
kubectl get pods -l app=web --sort-by=.metadata.creationTimestamp
# 查看新 Pod 是否处于 CrashLoopBackOff 或 Pending

# 4. 查看事件
kubectl get events --sort-by=.lastTimestamp | tail -20

# 5. 常见原因:
# - 新版本镜像拉取失败 → ImagePullBackOff
# - 新版本启动失败 → CrashLoopBackOff
# - 资源不足 → Pending (FailedScheduling)
# - Readiness Probe 配置不当 → Pod 不就绪
# - minReadySeconds 设置过长

# 6. 处理方式:
# 方案 A: 修复问题后继续
# 方案 B: 回滚到上一个版本
kubectl rollout undo deployment/web-app
```

---

## 💻 实战练习

### 练习 1：Deployment 基础操作

**目标：** 掌握 Deployment 的创建、更新、回滚

```bash
# 1. 创建 Deployment
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: practice-deploy
  labels:
    app: practice
spec:
  replicas: 3
  selector:
    matchLabels:
      app: practice
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    metadata:
      labels:
        app: practice
    spec:
      containers:
      - name: nginx
        image: nginx:1.24-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "100m"
            memory: "128Mi"
EOF

# 2. 查看 Deployment 和 ReplicaSet
kubectl get deployment practice-deploy
kubectl get rs -l app=practice
kubectl get pods -l app=practice

# 3. 执行滚动更新
kubectl set image deployment/practice-deploy nginx=nginx:1.25-alpine --record

# 4. 观察更新过程
kubectl rollout status deployment/practice-deploy
kubectl get rs -l app=practice -w  # watch 模式

# 5. 查看更新历史
kubectl rollout history deployment/practice-deploy

# 6. 回滚到上一个版本
kubectl rollout undo deployment/practice-deploy

# 7. 验证回滚
kubectl get rs -l app=practice
kubectl rollout history deployment/practice-deploy

# 8. 清理
kubectl delete deployment practice-deploy
```

### 练习 2：蓝绿部署实践

**目标：** 实现蓝绿部署并练习快速切换

```bash
# 1. 部署蓝色版本（当前版本）
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bg-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bg-demo
      version: blue
  template:
    metadata:
      labels:
        app: bg-demo
        version: blue
    spec:
      containers:
      - name: nginx
        image: nginx:1.24-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
EOF

# 2. 创建 Service 指向蓝色版本
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: bg-service
spec:
  selector:
    app: bg-demo
    version: blue
  ports:
  - port: 80
    targetPort: 80
EOF

# 3. 验证蓝色版本
kubectl get pods -l app=bg-demo,version=blue
kubectl port-forward svc/bg-service 8081:80 &
curl http://localhost:8081

# 4. 部署绿色版本（新版本）
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bg-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bg-demo
      version: green
  template:
    metadata:
      labels:
        app: bg-demo
        version: green
    spec:
      containers:
      - name: nginx
        image: nginx:1.25-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
EOF

# 5. 等待绿色版本就绪
kubectl rollout status deployment/bg-green

# 6. 切换流量到绿色版本
kubectl patch service bg-service -p '{"spec":{"selector":{"version":"green"}}}'

# 7. 验证切换
kubectl port-forward svc/bg-service 8082:80 &
curl http://localhost:8082  # 应该返回 nginx 1.25 的响应

# 8. 回滚到蓝色版本
kubectl patch service bg-service -p '{"spec":{"selector":{"version":"blue"}}}'

# 9. 清理
kubectl delete deployment bg-blue bg-green
kubectl delete service bg-service
```

### 练习 3：故障排查挑战

**目标：** 排查 Deployment 更新过程中的常见问题

```bash
# 场景 1: 更新卡住 - 新版本 Pod 无法启动
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: broken-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: broken
  template:
    metadata:
      labels:
        app: broken
    spec:
      containers:
      - name: app
        image: nginx:1.24-alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
EOF

# 执行一个会失败的更新
kubectl set image deployment/broken-deploy app=nginx:not-exist-tag --record

# 排查:
kubectl rollout status deployment/broken-deploy
kubectl get rs -l app=broken
kubectl get pods -l app=broken | grep ImagePullBackOff
kubectl describe pod <failed-pod-name>

# 修复: 回滚
kubectl rollout undo deployment/broken-deploy

# 场景 2: 扩缩容失败 - 资源不足
kubectl scale deployment/broken-deploy --replicas=100
kubectl get pods -l app=broken | grep Pending
kubectl describe pod <pending-pod-name> | grep Events

# 修复: 调整到合理副本数
kubectl scale deployment/broken-deploy --replicas=3

# 清理
kubectl delete deployment broken-deploy
```

---

## 🎯 面试题精选

### 1. Deployment 的滚动更新是如何工作的？maxSurge 和 maxUnavailable 是什么意思？

**参考答案：**

滚动更新通过逐步替换旧版本 Pod 实现零停机更新：
1. 创建 maxSurge 个新版本 Pod（允许超出期望副本数）
2. 等待新 Pod 通过 Readiness Probe
3. 删除 maxUnavailable 个旧版本 Pod
4. 重复直到所有 Pod 都更新完成

- **maxSurge**：更新过程中允许超出 replicas 的最大 Pod 数。值越大，更新越快，但需要更多资源
- **maxUnavailable**：更新过程中允许不可用的最大 Pod 数。值越大，更新越快，但可用性越低

默认值都是 25%。如果设 maxSurge=0, maxUnavailable=1，则先删旧 Pod 再建新 Pod（资源紧张时使用）。

### 2. Deployment 回滚是如何实现的？有什么限制？

**参考答案：**

回滚实现：
- Deployment 保留旧版本的 ReplicaSet（由 revisionHistoryLimit 控制）
- 回滚时将旧 ReplicaSet 的 Pod 模板复制到新 revision
- 实际上是一次新的滚动更新

限制：
- 只回滚 Pod 模板（image、环境变量等），不回滚 replicas、strategy 等字段
- 回滚后会创建新的 revision（不是回到旧的 revision 号）
- 如果旧 ReplicaSet 已被清理（revisionHistoryLimit 过小），无法回滚
- 建议 revisionHistoryLimit 设为 5-10

### 3. 什么是金丝雀部署？如何在 Kubernetes 中实现？

**参考答案：**

金丝雀部署是将新版本推送给一小部分用户进行验证，确认无问题后再全量发布。

实现方式：
1. **基于副本数比例**：创建两个 Deployment（stable 和 canary），通过 replicas 比例控制流量分配。例如 stable=9, canary=1 表示约 10% 流量到新版本
2. **基于 Ingress 注解**：使用 Nginx Ingress 的 canary-weight 注解精确控制流量比例
3. **基于 Service Mesh**：使用 Istio VirtualService 实现更精细的流量控制（基于 header、cookie 等）

### 4. 蓝绿部署和滚动更新有什么区别？各自的优缺点？

**参考答案：**

| 特性 | 蓝绿部署 | 滚动更新 |
|------|---------|---------|
| 停机时间 | 无（瞬间切换） | 无（逐步替换） |
| 资源消耗 | 双倍 | 额外 maxSurge 个 |
| 回滚速度 | 秒级（切换 Service） | 分钟级（重新部署） |
| 复杂度 | 中 | 低 |
| 风险 | 切换后全量暴露 | 逐步暴露 |
| 适用场景 | 关键服务、需要快速回滚 | 大部分无状态应用 |

### 5. ReplicaSet 和 Deployment 是什么关系？为什么不直接使用 ReplicaSet？

**参考答案：**

Deployment 管理 ReplicaSet，ReplicaSet 管理 Pod。

不直接使用 ReplicaSet 的原因：
- ReplicaSet 只能维持 Pod 副本数，不支持滚动更新
- ReplicaSet 没有版本历史，无法回滚
- ReplicaSet 没有更新策略（RollingUpdate/Recreate）
- Deployment 提供了声明式更新、回滚、扩缩容等高级功能

实际使用中，总是使用 Deployment 而不是直接使用 ReplicaSet。

### 6. 如何实现零停机部署？需要哪些配置？

**参考答案：**

零停机部署需要以下配置：
1. **滚动更新策略**：maxUnavailable=0, maxSurge>=1（先创建新 Pod 再删除旧 Pod）
2. **Readiness Probe**：确保新 Pod 完全就绪后才接收流量
3. **PreStop Hook**：在 Pod 终止前 sleep 一段时间，等待 Endpoints 更新
4. **优雅终止**：应用处理 SIGTERM 信号，完成正在处理的请求
5. **PDB (PodDisruptionBudget)**：确保节点维护时也有足够 Pod 提供服务

```yaml
# 完整配置示例
spec:
  strategy:
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    spec:
      containers:
      - name: app
        readinessProbe: ...
        lifecycle:
          preStop:
            exec:
              command: ["sh", "-c", "sleep 15"]
      terminationGracePeriodSeconds: 60
---
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
```

### 7. progressDeadlineSeconds 和 minReadySeconds 分别是什么作用？

**参考答案：**

- **progressDeadlineSeconds**（默认 600s）：Deployment 更新的最大等待时间。如果在此时间内更新没有取得进展（新 Pod 没有 Ready），Deployment 会被标记为 Progressing=False。注意：这不会自动回滚，只是设置状态条件。

- **minReadySeconds**（默认 0）：Pod Ready 后等待多久才被认为是 Available。在此期间如果 Pod 出问题，不算更新成功。用于确保新版本在真实负载下运行一段时间后仍然稳定。

### 8. HPA 是如何计算扩缩容的？

**参考答案：**

HPA 计算公式：
```
desiredReplicas = ceil[currentReplicas * (currentMetricValue / desiredMetricValue)]
```

例如：当前 3 个副本，CPU 使用率 85%，目标 70%：
```
desiredReplicas = ceil(3 * 85/70) = ceil(3.64) = 4
```

关键机制：
- 默认每 15 秒检查一次指标
- 使用 5 分钟窗口的平均值避免抖动
- scaleUp 快速（默认不限制），scaleDown 慢（默认 5 分钟稳定窗口）
- 至少需要 Metrics Server 提供 Pod 指标
- Pod 必须设置 resources.requests

### 9. 什么是 PodDisruptionBudget？什么场景下需要使用？

**参考答案：**

PDB 限制了在自愿中断（voluntary disruption）期间可以同时不可用的 Pod 数量。

自愿中断包括：
- 节点维护（kubectl drain）
- 集群自动缩容
- Deployment 更新

PDB 配置：
- `minAvailable`：至少保持 N 个 Pod 可用
- `maxUnavailable`：最多允许 N 个 Pod 不可用

使用场景：
- 关键服务（如 API 网关）需要保证最小可用副本数
- 有状态服务（如数据库）需要保证最小集群节点数
- 需要安全执行节点维护操作

### 10. 如何实现基于自定义指标的 HPA？

**参考答案：**

步骤：
1. 安装 Prometheus 和 Prometheus Adapter
2. 应用暴露自定义指标（如 http_requests_total）
3. 配置 Prometheus Adapter 将指标转换为 K8s 自定义指标 API
4. 创建 HPA 引用自定义指标

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

---

## 📚 深入阅读

- [Kubernetes 官方文档 - Deployment](https://kubernetes.io/zh-cn/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes 官方文档 - ReplicaSet](https://kubernetes.io/zh-cn/docs/concepts/workloads/controllers/replicaset/)
- [Kubernetes 官方文档 - HPA](https://kubernetes.io/zh-cn/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes 官方文档 - PDB](https://kubernetes.io/zh-cn/docs/tasks/run-application/configure-pdb/)
- [Argo Rollouts - 渐进式交付](https://argoproj.github.io/rollouts/)

---

## ✅ 自检清单

- [ ] 理解 Deployment 的声明式管理模型
- [ ] 掌握 Deployment → ReplicaSet → Pod 的控制链
- [ ] 理解滚动更新的原理（maxSurge、maxUnavailable）
- [ ] 能执行回滚操作并理解其限制
- [ ] 掌握手动扩缩容和 HPA 自动扩缩容
- [ ] 理解 HPA 的计算公式和工作流程
- [ ] 能实现金丝雀部署（基于副本比例或 Ingress 注解）
- [ ] 能实现蓝绿部署（基于 Service selector 切换）
- [ ] 理解 PDB 的作用和配置
- [ ] 能排查 Deployment 更新卡住的问题
