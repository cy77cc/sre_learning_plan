# Day 94: Kubernetes DaemonSet 与 Job/CronJob

> 📅 日期：2026-05-03
> 📖 学习主题：DaemonSet 生命周期、节点守护进程、Job 并行/完成策略、CronJob 调度、批处理任务
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 90 Kubernetes 架构, Day 91 Pod, Day 92 Deployment

---

## 🎯 学习目标

- 掌握 DaemonSet 的设计原理和使用场景
- 理解 DaemonSet 与 Deployment 的区别
- 掌握 Job 的并行执行和完成策略
- 掌握 CronJob 的调度配置和历史限制
- 能使用 DaemonSet 部署日志收集、监控、网络插件
- 能使用 Job/CronJob 执行批处理和定时任务

---

## 📖 核心知识点

### 1. DaemonSet 概述

#### 1.1 什么是 DaemonSet

DaemonSet 是 Kubernetes 中用于确保**每个（或指定）节点上运行一个 Pod 副本**的工作负载资源。它类似于 Linux 系统中的 systemd 服务，是节点级别的守护进程。

```
┌──────────────────────────────────────────────────────────────────┐
│                    DaemonSet 工作原理                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   DaemonSet: log-agent (确保每个节点运行一个日志收集 Agent)       │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  Node 1                                                 │    │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐     │    │
│   │  │  Pod A   │  │  Pod B   │  │  log-agent-xxxx  │     │    │
│   │  │ (业务)   │  │ (业务)   │  │  (DaemonSet Pod) │     │    │
│   │  └──────────┘  └──────────┘  └──────────────────┘     │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  Node 2                                                 │    │
│   │  ┌──────────┐  ┌──────────────────┐                    │    │
│   │  │  Pod C   │  │  log-agent-yyyy  │                    │    │
│   │  │ (业务)   │  │  (DaemonSet Pod) │                    │    │
│   │  └──────────┘  └──────────────────┘                    │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  Node 3                                                 │    │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐     │    │
│   │  │  Pod D   │  │  Pod E   │  │  log-agent-zzzz  │     │    │
│   │  │ (业务)   │  │ (业务)   │  │  (DaemonSet Pod) │     │    │
│   │  └──────────┘  └──────────┘  └──────────────────┘     │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
│   DaemonSet 特性:                                                │
│   - 新节点加入集群时，自动在新节点上创建 Pod                     │
│   - 节点被移除时，自动清理对应的 Pod                             │
│   - DaemonSet 的 Pod 由 DaemonSet Controller 直接创建，         │
│     不通过 ReplicaSet                                            │
│   - 删除 DaemonSet 会删除所有它创建的 Pod                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 1.2 DaemonSet vs Deployment

```
┌──────────────────────────────────────────────────────────────────┐
│                DaemonSet vs Deployment 对比                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  特性              Deployment            DaemonSet                │
│  ─────────────     ──────────            ──────────              │
│  Pod 副本数        用户指定 (replicas)   由节点数量决定           │
│  Pod 分布          调度器决定            每个节点一个             │
│  控制器            ReplicaSet            直接管理 Pod             │
│  适用场景          无状态应用            节点级守护进程           │
│  典型应用          Web 服务器            日志/监控/网络           │
│  更新策略          RollingUpdate         RollingUpdate/OnDelete   │
│  扩缩容            手动/HPA              自动随节点增减           │
│                                                                  │
│  选择依据:                                                        │
│  - 需要每个节点运行一个？ → DaemonSet                            │
│  - 需要固定副本数？ → Deployment                                 │
│  - 节点级操作（日志/监控/网络）？ → DaemonSet                    │
│  - 应用级服务（Web/API）？ → Deployment                          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 1.3 DaemonSet 使用场景

| 场景 | 典型组件 | 说明 |
|------|---------|------|
| 日志收集 | Fluentd, Filebeat, Fluent Bit | 每个节点收集该节点上所有容器的日志 |
| 节点监控 | Node Exporter, cAdvisor | 每个节点暴露该节点的系统指标 |
| 网络插件 | Calico, Cilium, Flannel | 每个节点运行网络代理 |
| 存储插件 | Ceph, GlusterFS | 每个节点运行存储守护进程 |
| 安全代理 | Falco, Sysdig Agent | 每个节点运行安全检测 |
| Ingress Controller | Nginx Ingress, Traefik | 在指定节点运行入口控制器 |
| GPU 设备插件 | NVIDIA Device Plugin | 在有 GPU 的节点运行设备插件 |

---

### 2. DaemonSet 详解

#### 2.1 DaemonSet YAML 完整解析

```yaml
# daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: log-agent
  namespace: kube-system
  labels:
    app: log-agent
spec:
  # 选择器（必须匹配 Pod 模板的标签）
  selector:
    matchLabels:
      app: log-agent

  # 更新策略
  updateStrategy:
    type: RollingUpdate       # RollingUpdate 或 OnDelete
    rollingUpdate:
      maxUnavailable: 1       # 更新时最多不可用的 Pod 数
      # 注意：DaemonSet 不支持 maxSurge

  # 修订历史限制
  revisionHistoryLimit: 10

  # Pod 模板
  template:
    metadata:
      labels:
        app: log-agent
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9100"
    spec:
      # 容忍所有污点（确保在所有节点运行，包括 Master）
      tolerations:
      - operator: Exists      # 容忍所有污点

      # 安全上下文
      securityContext:
        runAsUser: 0          # 日志收集通常需要 root 权限

      # 使用主机网络（可选，某些场景需要）
      # hostNetwork: true

      # 使用主机 PID（可选，监控场景需要）
      # hostPID: true

      containers:
      - name: log-agent
        image: fluent/fluent-bit:2.2
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "200m"
            memory: "256Mi"

        # 挂载主机日志目录
        volumeMounts:
        - name: varlog
          mountPath: /var/log
          readOnly: true
        - name: containers
          mountPath: /var/lib/docker/containers
          readOnly: true
        - name: config
          mountPath: /fluent-bit/etc/

        # 健康检查
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 2020
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/metrics
            port: 2020
          initialDelaySeconds: 5
          periodSeconds: 10

      # 终止宽限期
      terminationGracePeriodSeconds: 30

      volumes:
      - name: varlog
        hostPath:
          path: /var/log
          type: Directory
      - name: containers
        hostPath:
          path: /var/lib/docker/containers
          type: DirectoryOrCreate
      - name: config
        configMap:
          name: log-agent-config
```

#### 2.2 DaemonSet 节点选择

```yaml
# 方式 1: nodeSelector（简单匹配）
spec:
  template:
    spec:
      nodeSelector:
        kubernetes.io/os: linux
        node-role.kubernetes.io/worker: ""

# 方式 2: nodeAffinity（高级匹配）
spec:
  template:
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/os
                operator: In
                values: ["linux"]
              - key: node-type
                operator: NotIn
                values: ["spot"]  # 不在 Spot 节点上运行
```

**只在特定节点运行 DaemonSet：**

```
┌──────────────────────────────────────────────────────────────────┐
│                DaemonSet 节点选择策略                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 1: 在所有节点运行（包括 Master）                           │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  tolerations:                                          │     │
│  │  - operator: Exists    # 容忍所有污点                   │     │
│  │                                                          │     │
│  │  用途: 日志收集、监控 Agent                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  场景 2: 只在 Worker 节点运行（默认行为）                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  不设置 tolerations（默认不容忍 Master 污点）           │     │
│  │                                                          │     │
│  │  Master 节点有污点:                                      │     │
│  │  node-role.kubernetes.io/control-plane:NoSchedule       │     │
│  │                                                          │     │
│  │  用途: 大部分 DaemonSet                                  │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  场景 3: 只在有 GPU 的节点运行                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  nodeSelector:                                         │     │
│  │    accelerator: nvidia-tesla-p100                      │     │
│  │                                                          │     │
│  │  用途: GPU 设备插件                                      │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  场景 4: 只在特定可用区运行                                     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  affinity:                                             │     │
│  │    nodeAffinity:                                       │     │
│  │      requiredDuringSchedulingIgnoredDuringExecution:   │     │
│  │        nodeSelectorTerms:                              │     │
│  │        - matchExpressions:                             │     │
│  │          - key: topology.kubernetes.io/zone            │     │
│  │            operator: In                                │     │
│  │            values: ["us-east-1a", "us-east-1b"]       │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 2.3 DaemonSet 更新策略

```
┌──────────────────────────────────────────────────────────────────┐
│                DaemonSet 更新策略                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  策略 1: RollingUpdate (推荐)                                    │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  maxUnavailable: 1                                      │     │
│  │                                                          │     │
│  │  更新过程:                                               │     │
│  │  1. 更新 maxUnavailable 个 Pod                          │     │
│  │  2. 等待新 Pod 就绪                                      │     │
│  │  3. 继续更新下一批                                       │     │
│  │                                                          │     │
│  │  注意: DaemonSet 不支持 maxSurge                        │     │
│  │  原因: 每个节点只能运行一个 Pod，不能创建额外 Pod        │     │
│  │                                                          │     │
│  │  maxUnavailable 可以是绝对数或百分比:                    │     │
│  │  - maxUnavailable: 1    (默认，一次更新 1 个)           │     │
│  │  - maxUnavailable: 25%  (一次更新 25% 的节点)           │     │
│  │  - maxUnavailable: 100% (一次更新所有，等同 Recreate)   │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  策略 2: OnDelete                                               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  只有手动删除 Pod 后才创建新版本 Pod                     │     │
│  │  不会自动更新                                            │     │
│  │                                                          │     │
│  │  用途: 需要完全控制更新时机                              │     │
│  │  例如: 网络插件更新，需要逐个节点手动操作                │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```bash
# DaemonSet 更新操作
# 方式 1: 修改 YAML 后 apply
kubectl apply -f daemonset.yaml

# 方式 2: 直接更新镜像
kubectl set image daemonset/log-agent log-agent=fluent/fluent-bit:2.3 -n kube-system

# 查看更新状态
kubectl rollout status daemonset/log-agent -n kube-system

# 查看更新历史
kubectl rollout history daemonset/log-agent -n kube-system

# 回滚
kubectl rollout undo daemonset/log-agent -n kube-system

# 暂停/恢复更新
kubectl rollout pause daemonset/log-agent -n kube-system
kubectl rollout resume daemonset/log-agent -n kube-system
```

---

### 3. 实战：DaemonSet 部署场景

#### 3.1 Node Exporter（Prometheus 节点监控）

```yaml
# node-exporter-daemonset.yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
  namespace: monitoring
  labels:
    app: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: node-exporter
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9100"
        prometheus.io/path: "/metrics"
    spec:
      hostNetwork: true         # 使用主机网络
      hostPID: true             # 使用主机 PID 命名空间
      tolerations:
      - operator: Exists        # 容忍所有污点（包括 Master）
      containers:
      - name: node-exporter
        image: prom/node-exporter:v1.7.0
        args:
        - --path.procfs=/host/proc
        - --path.sysfs=/host/sys
        - --path.rootfs=/host/root
        - --collector.filesystem.mount-points-exclude=^/(dev|proc|sys|var/lib/docker/.+|var/lib/kubelet/.+)($|/)
        ports:
        - containerPort: 9100
          name: metrics
          hostPort: 9100        # 使用主机端口
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "200m"
            memory: "256Mi"
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
        livenessProbe:
          httpGet:
            path: /
            port: 9100
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /
            port: 9100
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: proc
        hostPath:
          path: /proc
          type: Directory
      - name: sys
        hostPath:
          path: /sys
          type: Directory
      - name: root
        hostPath:
          path: /
          type: Directory
```

#### 3.2 Fluent Bit（日志收集）

```yaml
# fluentbit-daemonset.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentbit-config
  namespace: logging
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off
        Parsers_File  parsers.conf

    [INPUT]
        Name              tail
        Tag               kube.*
        Path              /var/log/containers/*.log
        Parser            cri
        DB                /var/log/flb_kube.db
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [FILTER]
        Name                kubernetes
        Match               kube.*
        Kube_URL            https://kubernetes.default.svc:443
        Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
        Kube_Tag_Prefix     kube.var.log.containers.
        Merge_Log           On
        Merge_Log_Key       log_processed
        K8S-Logging.Parser  On
        K8S-Logging.Exclude Off

    [OUTPUT]
        Name            es
        Match           kube.*
        Host            elasticsearch.logging.svc.cluster.local
        Port            9200
        Index           k8s-logs
        Type            _doc
        Logstash_Format On
        Logstash_Prefix k8s
        Retry_Limit     False

  parsers.conf: |
    [PARSER]
        Name        cri
        Format      regex
        Regex       ^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<log>.*)$
        Time_Key    time
        Time_Format %Y-%m-%dT%H:%M:%S.%L%z
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: logging
  labels:
    app: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 25%
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      serviceAccountName: fluent-bit
      tolerations:
      - operator: Exists
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:2.2
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "200m"
            memory: "256Mi"
        volumeMounts:
        - name: config
          mountPath: /fluent-bit/etc/
        - name: varlog
          mountPath: /var/log
          readOnly: true
        - name: containers
          mountPath: /var/lib/docker/containers
          readOnly: true
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 2020
          initialDelaySeconds: 10
          periodSeconds: 30
      volumes:
      - name: config
        configMap:
          name: fluentbit-config
      - name: varlog
        hostPath:
          path: /var/log
          type: Directory
      - name: containers
        hostPath:
          path: /var/lib/docker/containers
          type: DirectoryOrCreate
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: fluent-bit
  namespace: logging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: fluent-bit
rules:
- apiGroups: [""]
  resources: ["pods", "namespaces"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: fluent-bit
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: fluent-bit
subjects:
- kind: ServiceAccount
  name: fluent-bit
  namespace: logging
```

---

### 4. Job 概述

#### 4.1 什么是 Job

Job 是 Kubernetes 中用于运行**一次性任务**的工作负载资源。它创建一个或多个 Pod，确保指定数量的 Pod 成功完成任务后终止。

```
┌──────────────────────────────────────────────────────────────────┐
│                    Job 工作原理                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Job: db-migration                                               │
│  completions: 1, parallelism: 1                                  │
│                                                                  │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                 │
│  │  创建    │────>│  运行    │────>│  完成    │                 │
│  │  Pod     │     │  任务    │     │  退出 0  │                 │
│  └──────────┘     └──────────┘     └──────────┘                 │
│                                        │                         │
│                                        ▼                         │
│                                  Job 状态: Complete              │
│                                                                  │
│  Job 特性:                                                       │
│  - 创建 Pod 执行任务                                             │
│  - Pod 成功完成（退出码 0）后，Job 记录成功                     │
│  - Pod 失败时，根据 restartPolicy 和 backoffLimit 重试           │
│  - Job 完成后 Pod 不会自动删除（由 TTL 控制）                   │
│                                                                  │
│  Job vs Deployment:                                              │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Deployment: 持续运行的服务，Pod 永远不退出              │     │
│  │  Job: 一次性任务，Pod 完成后退出                        │     │
│  │                                                          │     │
│  │  Deployment: restartPolicy=Always (默认)                │     │
│  │  Job: restartPolicy=OnFailure 或 Never                  │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.2 Job 完整示例

```yaml
# job-basic.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: hello-job
spec:
  # 任务完成数：成功运行 1 个 Pod 即可
  completions: 1

  # 并行度：同时运行 1 个 Pod
  parallelism: 1

  # 失败重试次数：最多重试 3 次
  backoffLimit: 3

  # 超时时间：600 秒后自动终止
  activeDeadlineSeconds: 600

  # TTL：Job 完成后 1 小时自动清理
  ttlSecondsAfterFinished: 3600

  template:
    metadata:
      labels:
        job: hello
    spec:
      # Job 的 Pod 必须设置 restartPolicy 为 OnFailure 或 Never
      restartPolicy: Never
      containers:
      - name: hello
        image: busybox:1.36
        command: ["sh", "-c", "echo 'Hello from Job!' && sleep 10 && echo 'Done!'"]
        resources:
          requests:
            cpu: "50m"
            memory: "32Mi"
          limits:
            cpu: "100m"
            memory: "64Mi"
```

```bash
# 创建 Job
kubectl apply -f job-basic.yaml

# 查看 Job 状态
kubectl get jobs
kubectl describe job hello-job

# 查看 Job 的 Pod
kubectl get pods -l job=hello

# 查看 Pod 日志
kubectl logs -l job=hello

# 等待 Job 完成
kubectl wait --for=condition=complete --timeout=120s job/hello-job

# 删除 Job
kubectl delete job hello-job
```

---

### 5. Job 并行执行

#### 5.1 并行 Job 模式

```
┌──────────────────────────────────────────────────────────────────┐
│                    Job 并行执行模式                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  模式 1: 非并行 Job                                              │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  completions: 1, parallelism: 1 (默认)                 │     │
│  │  只运行一个 Pod，成功后 Job 完成                        │     │
│  │  适用: 数据库迁移、一次性初始化                         │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  模式 2: 带完成数的并行 Job (Work Queue)                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  completions: 10, parallelism: 3                       │     │
│  │                                                          │     │
│  │  Pod-1 (task-1) ──完成──> Pod-4 (task-4) ──完成──>     │     │
│  │  Pod-2 (task-2) ──完成──> Pod-5 (task-5) ──完成──>     │     │
│  │  Pod-3 (task-3) ──完成──> Pod-6 (task-6) ──> ...       │     │
│  │                                                          │     │
│  │  特点:                                                   │     │
│  │  - 需要成功完成 10 个 Pod                                │     │
│  │  - 同时运行 3 个 Pod                                     │     │
│  │  - 每个 Pod 完成后自动创建新的                           │     │
│  │  - 适用于处理 10 个独立任务                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  模式 3: 无完成数的并行 Job (Work Queue with no completions)    │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  parallelism: 5 (不设置 completions)                    │     │
│  │                                                          │     │
│  │  Pod-1 ──完成──> Job 完成（一个成功即可）               │     │
│  │  Pod-2 ──完成──>                                       │     │
│  │  Pod-3 ──完成──>                                       │     │
│  │  Pod-4 ──完成──>                                       │     │
│  │  Pod-5 ──完成──>                                       │     │
│  │                                                          │     │
│  │  特点:                                                   │     │
│  │  - 所有 Pod 并行运行                                    │     │
│  │  - 任意一个成功 Job 就完成                              │     │
│  │  - 适用于竞争性任务                                     │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 5.2 并行 Job 示例

```yaml
# job-parallel.yaml — 并行处理 10 个任务
apiVersion: batch/v1
kind: Job
metadata:
  name: parallel-job
spec:
  completions: 10       # 需要完成 10 个任务
  parallelism: 3        # 同时运行 3 个 Pod
  backoffLimit: 5       # 最多重试 5 次
  completionMode: Indexed  # 索引模式（K8s 1.21+）
  template:
    metadata:
      labels:
        job: parallel
    spec:
      restartPolicy: OnFailure
      containers:
      - name: worker
        image: busybox:1.36
        command:
        - sh
        - -c
        - |
          # JOB_COMPLETION_INDEX 环境变量是 Pod 的索引（0-9）
          echo "Processing task $JOB_COMPLETION_INDEX"
          sleep $((JOB_COMPLETION_INDEX * 5 + 10))
          echo "Task $JOB_COMPLETION_INDEX completed"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: "100m"
            memory: "64Mi"
```

```bash
# 创建并行 Job
kubectl apply -f job-parallel.yaml

# 观察 Pod 创建和完成过程
kubectl get pods -l job=parallel -w

# 查看各任务的日志
kubectl logs parallel-job-0
kubectl logs parallel-job-1
# ...

# 查看 Job 完成进度
kubectl describe job parallel-job
# 关注: Succeeded: 3/10, Active: 3
```

#### 5.3 Work Queue 模式（Redis）

```yaml
# job-workqueue.yaml — 从 Redis 队列消费任务
apiVersion: batch/v1
kind: Job
metadata:
  name: worker-job
spec:
  parallelism: 5       # 5 个 Worker 并行消费
  # 不设置 completions，当队列为空时 Worker 自动退出
  template:
    metadata:
      labels:
        job: worker
    spec:
      restartPolicy: OnFailure
      containers:
      - name: worker
        image: python:3.12-slim
        command:
        - python
        - -c
        - |
          import redis
          import time
          import sys
          import os

          r = redis.Redis(host='redis-service', port=6379, decode_responses=True)

          while True:
              # 从队列中取任务（阻塞 5 秒）
              task = r.brpop('task_queue', timeout=5)
              if task is None:
                  print("Queue empty, exiting")
                  sys.exit(0)

              task_data = task[1]
              print(f"Processing: {task_data}")
              time.sleep(2)  # 模拟处理
              print(f"Completed: {task_data}")
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
```

---

### 6. CronJob 概述

#### 6.1 什么是 CronJob

CronJob 是 Kubernetes 中用于**定时执行任务**的工作负载资源，类似于 Linux 的 crontab。它按照指定的时间调度创建 Job 对象。

```
┌──────────────────────────────────────────────────────────────────┐
│                    CronJob 工作原理                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CronJob: backup-job                                             │
│  schedule: "0 2 * * *"  (每天凌晨 2 点)                         │
│                                                                  │
│  时间线:                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  00:00  01:00  02:00  03:00  04:00  ...  02:00 (第二天)  │   │
│  │                           │                        │      │   │
│  │                           ▼                        ▼      │   │
│  │                      创建 Job-1              创建 Job-2    │   │
│  │                           │                        │      │   │
│  │                           ▼                        ▼      │   │
│  │                      Pod 运行备份            Pod 运行备份  │   │
│  │                           │                        │      │   │
│  │                           ▼                        ▼      │   │
│  │                      Job 完成                Job 完成      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  CronJob 控制的资源链:                                            │
│  CronJob → Job → Pod                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 6.2 CronJob 完整示例

```yaml
# cronjob-basic.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
spec:
  # Cron 表达式：每天凌晨 2 点执行
  schedule: "0 2 * * *"

  # 时区（K8s 1.27+ GA）
  timeZone: "Asia/Shanghai"

  # 并发策略：
  # Allow: 允许并发执行（默认）
  # Forbid: 如果上一个还没完成，跳过本次
  # Replace: 取消正在运行的，启动新的
  concurrencyPolicy: Forbid

  # 是否暂停调度
  suspend: false

  # 历史限制
  successfulJobsHistoryLimit: 3    # 保留最近 3 个成功 Job
  failedJobsHistoryLimit: 5        # 保留最近 5 个失败 Job

  # 启动截止时间：如果错过了调度时间 100 秒，则跳过
  startingDeadlineSeconds: 100

  # Job 模板
  jobTemplate:
    spec:
      backoffLimit: 2               # 最多重试 2 次
      activeDeadlineSeconds: 3600   # 最多运行 1 小时
      ttlSecondsAfterFinished: 86400  # 完成后 24 小时自动清理
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: backup
            image: mysql:8.0
            command:
            - /bin/sh
            - -c
            - |
              echo "Starting backup at $(date)"
              mysqldump -h mysql-service -u root -p$MYSQL_ROOT_PASSWORD \
                --all-databases --single-transaction \
                > /backup/db-backup-$(date +%Y%m%d%H%M%S).sql
              echo "Backup completed at $(date)"
            env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-secret
                  key: MYSQL_ROOT_PASSWORD
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
            resources:
              requests:
                cpu: "250m"
                memory: "256Mi"
              limits:
                cpu: "500m"
                memory: "512Mi"
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

```bash
# 创建 CronJob
kubectl apply -f cronjob-basic.yaml

# 查看 CronJob 状态
kubectl get cronjob
kubectl describe cronjob database-backup

# 查看 CronJob 创建的 Job
kubectl get jobs -l cronjob=database-backup

# 手动触发一次 CronJob（不需要等到调度时间）
kubectl create job manual-backup --from=cronjob/database-backup

# 暂停 CronJob
kubectl patch cronjob database-backup -p '{"spec":{"suspend":true}}'

# 恢复 CronJob
kubectl patch cronjob database-backup -p '{"spec":{"suspend":false}}'

# 查看 CronJob 事件
kubectl get events --field-selector involvedObject.name=database-backup
```

#### 6.3 Cron 表达式详解

```
┌──────────────────────────────────────────────────────────────────┐
│                    Cron 表达式格式                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  格式: ┌───────────── 分钟 (0-59)                               │
│        │ ┌───────────── 小时 (0-23)                              │
│        │ │ ┌───────────── 日 (1-31)                              │
│        │ │ │ ┌───────────── 月 (1-12)                            │
│        │ │ │ │ ┌───────────── 周几 (0-6, 0=周日)                │
│        │ │ │ │ │                                                  │
│        * * * * *                                                  │
│                                                                  │
│  常用示例:                                                        │
│  ───────────────────────────────────────────────────────────     │
│  "0 * * * *"          每小时整点                                 │
│  "0 2 * * *"          每天凌晨 2 点                              │
│  "0 2 * * 1"          每周一凌晨 2 点                            │
│  "0 2 1 * *"          每月 1 号凌晨 2 点                         │
│  "*/5 * * * *"        每 5 分钟                                  │
│  "0 9-17 * * 1-5"     工作日 9 点到 17 点每小时                  │
│  "0 2 * * 0"          每周日凌晨 2 点                            │
│  "30 2 1,15 * *"      每月 1 号和 15 号凌晨 2:30                 │
│                                                                  │
│  特殊字符:                                                        │
│  *     任意值                                                    │
│  ,     列表 (1,3,5)                                              │
│  -     范围 (1-5)                                                │
│  /     步长 (*/5)                                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 7. CronJob 高级配置

#### 7.1 并发策略详解

```
┌──────────────────────────────────────────────────────────────────┐
│                CronJob 并发策略                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Allow (默认): 允许并发执行                                      │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  时间: 02:00  02:05  02:10                              │     │
│  │          │       │       │                              │     │
│  │          ▼       ▼       ▼                              │     │
│  │       Job-1   Job-2   Job-3                             │     │
│  │      (运行中) (运行中) (运行中)                          │     │
│  │                                                          │     │
│  │  问题: 可能导致资源竞争                                  │     │
│  │  适用: 任务之间无依赖，可以并行                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Forbid: 禁止并发执行                                           │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  时间: 02:00  02:05  02:10                              │     │
│  │          │       │       │                              │     │
│  │          ▼       跳过    ▼                              │     │
│  │       Job-1    (上一个  Job-2                           │     │
│  │      (运行中)   还在)  (运行中)                          │     │
│  │                                                          │     │
│  │  适用: 任务有冲突（如写同一个文件）                      │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Replace: 替换正在运行的 Job                                    │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  时间: 02:00  02:05  02:10                              │     │
│  │          │       │       │                              │     │
│  │          ▼       ▼       ▼                              │     │
│  │       Job-1   Job-1   Job-2                             │     │
│  │      (运行中) (被终止) (运行中)                          │     │
│  │                                                          │     │
│  │  适用: 始终使用最新数据执行                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 7.2 常见 CronJob 场景

```yaml
# 场景 1: 每日数据库备份
apiVersion: batch/v1
kind: CronJob
metadata:
  name: daily-db-backup
spec:
  schedule: "0 2 * * *"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: backup
            image: mysql:8.0
            command: ["sh", "-c", "mysqldump ... > /backup/db-$(date +%F).sql"]
---
# 场景 2: 每小时清理临时文件
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cleanup-temp
spec:
  schedule: "0 * * * *"
  concurrencyPolicy: Allow
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: cleanup
            image: busybox:1.36
            command: ["sh", "-c", "find /tmp -type f -mtime +1 -delete && echo 'Cleanup done'"]
          volumes:
          - name: tmp
            hostPath:
              path: /tmp
---
# 场景 3: 每周生成报告
apiVersion: batch/v1
kind: CronJob
metadata:
  name: weekly-report
spec:
  schedule: "0 8 * * 1"  # 每周一早上 8 点
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: report
            image: python:3.12-slim
            command:
            - python
            - -c
            - |
              import datetime
              print(f"Generating report for week {datetime.date.today().isocalendar()[1]}")
              # 生成报告逻辑...
```

---

### 8. Job/CronJob 最佳实践

```
┌──────────────────────────────────────────────────────────────────┐
│                Job/CronJob 最佳实践                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Job 最佳实践:                                                    │
│  1. 始终设置 backoffLimit（防止无限重试）                        │
│  2. 始终设置 activeDeadlineSeconds（防止任务挂起）              │
│  3. 使用 ttlSecondsAfterFinished 自动清理已完成的 Job           │
│  4. 优先使用 restartPolicy=OnFailure（避免创建多个 Pod）        │
│  5. 使用 completionMode=Indexed 处理独立子任务                  │
│  6. 并行度不要超过队列中的任务数                                │
│                                                                  │
│  CronJob 最佳实践:                                               │
│  1. 设置合理的 concurrencyPolicy（通常用 Forbid）               │
│  2. 设置 startingDeadlineSeconds（处理 Controller Manager 故障）│
│  3. 限制 successfulJobsHistoryLimit 和 failedJobsHistoryLimit   │
│  4. 使用 timeZone 指定时区（避免 UTC 混淆）                     │
│  5. 任务逻辑应该是幂等的（可重复执行不产生副作用）              │
│  6. 监控失败的 Job（设置告警）                                  │
│                                                                  │
│  常见问题:                                                        │
│  - CronJob 不执行: 检查 suspend 字段、schedule 格式             │
│  - Job 一直 Pending: 检查资源配额、节点资源                     │
│  - Job 一直失败: 检查镜像、命令、环境变量                       │
│  - 多个 Job 并发: 检查 concurrencyPolicy 设置                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 9. SRE 实战案例

#### 9.1 定时备份自动化

```yaml
# 完整的备份方案：CronJob + PVC + S3 上传
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etcd-backup
  namespace: kube-system
spec:
  schedule: "0 */6 * * *"  # 每 6 小时
  timeZone: "Asia/Shanghai"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 4
  failedJobsHistoryLimit: 3
  startingDeadlineSeconds: 300
  jobTemplate:
    spec:
      backoffLimit: 1
      activeDeadlineSeconds: 600
      ttlSecondsAfterFinished: 172800  # 48 小时后清理
      template:
        spec:
          nodeSelector:
            node-role.kubernetes.io/control-plane: ""
          tolerations:
          - key: node-role.kubernetes.io/control-plane
            effect: NoSchedule
          restartPolicy: OnFailure
          containers:
          - name: etcd-backup
            image: bitnami/etcd:3.5
            command:
            - /bin/sh
            - -c
            - |
              set -e
              BACKUP_FILE="/backup/etcd-$(date +%Y%m%d-%H%M%S).db"

              # 备份 etcd
              etcdctl snapshot save $BACKUP_FILE \
                --endpoints=https://127.0.0.1:2379 \
                --cacert=/etc/kubernetes/pki/etcd/ca.crt \
                --cert=/etc/kubernetes/pki/etcd/server.crt \
                --key=/etc/kubernetes/pki/etcd/server.key

              # 验证备份
              etcdctl snapshot status $BACKUP_FILE --write-out=table

              # 上传到 S3（需要安装 aws cli）
              # aws s3 cp $BACKUP_FILE s3://k8s-backups/etcd/

              echo "Backup completed: $BACKUP_FILE"
            volumeMounts:
            - name: etcd-certs
              mountPath: /etc/kubernetes/pki/etcd
              readOnly: true
            - name: backup-storage
              mountPath: /backup
            resources:
              requests:
                cpu: "100m"
                memory: "128Mi"
              limits:
                cpu: "500m"
                memory: "256Mi"
          volumes:
          - name: etcd-certs
            hostPath:
              path: /etc/kubernetes/pki/etcd
              type: Directory
          - name: backup-storage
            persistentVolumeClaim:
              claimName: etcd-backup-pvc
```

#### 9.2 批量数据处理

```yaml
# 使用索引 Job 并行处理数据分片
apiVersion: batch/v1
kind: Job
metadata:
  name: data-processor
spec:
  completions: 100          # 100 个数据分片
  parallelism: 10           # 10 个并发 Worker
  completionMode: Indexed
  backoffLimit: 15
  activeDeadlineSeconds: 7200  # 2 小时超时
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: processor
        image: python:3.12-slim
        command:
        - python
        - -c
        - |
          import os
          import time

          index = int(os.environ['JOB_COMPLETION_INDEX'])
          print(f"Processing shard {index}/100")

          # 模拟数据处理
          time.sleep(30)
          print(f"Shard {index} completed")
        resources:
          requests:
            cpu: "500m"
            memory: "256Mi"
          limits:
            cpu: "1"
            memory: "512Mi"
```

---

## 💻 实战练习

### 练习 1：DaemonSet 操作

**目标：** 掌握 DaemonSet 的创建和管理

```bash
# 1. 创建一个简单的 DaemonSet
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: practice-ds
  labels:
    app: practice-ds
spec:
  selector:
    matchLabels:
      app: practice-ds
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: practice-ds
    spec:
      containers:
      - name: pause
        image: registry.k8s.io/pause:3.9
        resources:
          requests:
            cpu: "10m"
            memory: "16Mi"
          limits:
            cpu: "50m"
            memory: "32Mi"
EOF

# 2. 查看 DaemonSet 和 Pod
kubectl get daemonset practice-ds
kubectl get pods -l app=practice-ds -o wide
# 确认每个节点（除了可能的 Master）都有一个 Pod

# 3. 查看 Pod 分布
kubectl get pods -l app=practice-ds -o custom-columns=\
  NAME:.metadata.name,NODE:.spec.nodeName,STATUS:.status.phase

# 4. 测试 DaemonSet 更新
kubectl set image daemonset/practice-ds pause=registry.k8s.io/pause:3.9 --record
kubectl rollout status daemonset/practice-ds

# 5. 查看更新历史
kubectl rollout history daemonset/practice-ds

# 6. 清理
kubectl delete daemonset practice-ds
```

### 练习 2：Job 操作

**目标：** 掌握 Job 的创建、并行执行和完成策略

```bash
# 1. 创建一个简单的 Job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: practice-job
spec:
  backoffLimit: 3
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: hello
        image: busybox:1.36
        command: ["sh", "-c", "echo 'Starting job...' && sleep 5 && echo 'Job done!'"]
        resources:
          requests:
            cpu: "50m"
            memory: "32Mi"
EOF

# 2. 查看 Job 状态
kubectl get jobs
kubectl describe job practice-job

# 3. 查看 Pod 日志
kubectl logs -l job-name=practice-job

# 4. 等待 Job 完成
kubectl wait --for=condition=complete --timeout=120s job/practice-job

# 5. 创建并行 Job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: parallel-practice
spec:
  completions: 6
  parallelism: 3
  backoffLimit: 5
  completionMode: Indexed
  template:
    spec:
      restartPolicy: OnFailure
      containers:
      - name: worker
        image: busybox:1.36
        command:
        - sh
        - -c
        - |
          INDEX=\$JOB_COMPLETION_INDEX
          echo "Task \$INDEX started"
          sleep \$((INDEX * 5 + 5))
          echo "Task \$INDEX completed"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: "50m"
            memory: "32Mi"
EOF

# 6. 观察并行执行过程
kubectl get pods -l job-name=parallel-practice -w
kubectl logs -l job-name=parallel-practice --all-containers

# 7. 查看最终状态
kubectl describe job parallel-practice

# 8. 清理
kubectl delete job practice-job parallel-practice
```

### 练习 3：CronJob 操作

**目标：** 掌握 CronJob 的创建和管理

```bash
# 1. 创建一个 CronJob
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: practice-cronjob
spec:
  schedule: "*/2 * * * *"  # 每 2 分钟执行一次
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  startingDeadlineSeconds: 60
  jobTemplate:
    spec:
      backoffLimit: 1
      activeDeadlineSeconds: 60
      ttlSecondsAfterFinished: 300
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: hello
            image: busybox:1.36
            command: ["sh", "-c", "echo 'CronJob executed at $(date)' && sleep 5"]
            resources:
              requests:
                cpu: "50m"
                memory: "32Mi"
EOF

# 2. 查看 CronJob 状态
kubectl get cronjob
kubectl describe cronjob practice-cronjob

# 3. 等待 2 分钟，观察 Job 被创建
kubectl get jobs -w

# 4. 查看 Job 的 Pod 日志
kubectl logs -l job-name=<job-name>

# 5. 手动触发一次
kubectl create job manual-trigger --from=cronjob/practice-cronjob

# 6. 查看手动触发的 Job
kubectl get job manual-trigger
kubectl logs job/manual-trigger

# 7. 暂停 CronJob
kubectl patch cronjob practice-cronjob -p '{"spec":{"suspend":true}}'

# 8. 恢复 CronJob
kubectl patch cronjob practice-cronjob -p '{"spec":{"suspend":false}}'

# 9. 清理
kubectl delete cronjob practice-cronjob
kubectl delete job manual-trigger
```

---

## 🎯 面试题精选

### 1. DaemonSet 和 Deployment 有什么区别？什么场景使用 DaemonSet？

**参考答案：**

| 特性 | Deployment | DaemonSet |
|------|-----------|-----------|
| Pod 副本数 | 用户指定 | 由节点数量决定 |
| Pod 分布 | 调度器决定 | 每个节点一个 |
| 控制器 | ReplicaSet | 直接管理 Pod |
| 适用场景 | 无状态应用 | 节点级守护进程 |

使用 DaemonSet 的场景：
- 日志收集（Fluentd/Filebeat）：每个节点需要收集该节点的日志
- 节点监控（Node Exporter）：每个节点需要暴露该节点的指标
- 网络插件（Calico/Cilium）：每个节点需要运行网络代理
- 存储守护进程（Ceph）：每个节点需要运行存储客户端

### 2. DaemonSet 如何确保只在特定节点上运行 Pod？

**参考答案：**

三种方式：
1. **nodeSelector**：简单标签匹配
   ```yaml
   nodeSelector:
     node-type: worker
   ```

2. **nodeAffinity**：高级匹配，支持 In/NotIn/Gt/Lt 等操作符
   ```yaml
   affinity:
     nodeAffinity:
       requiredDuringSchedulingIgnoredDuringExecution:
         nodeSelectorTerms:
         - matchExpressions:
           - key: node-type
             operator: In
             values: ["worker"]
   ```

3. **Taint/Toleration**：通过设置/容忍污点控制
   - 默认 DaemonSet 不会调度到有 NoSchedule 污点的节点（如 Master）
   - 添加 tolerations 可以在 Master 节点上运行

### 3. Job 的 backoffLimit 和 activeDeadlineSeconds 分别是什么？

**参考答案：**

- **backoffLimit**：Job 失败后的最大重试次数。默认为 6。每次失败后等待时间指数递增（10s, 20s, 40s...）。超过此限制后 Job 标记为 Failed。

- **activeDeadlineSeconds**：Job 的最大运行时间（秒）。超过后 Job 被终止，所有运行中的 Pod 被删除。优先级高于 backoffLimit。

SRE 建议：两者都应设置，防止任务无限重试或挂起。

### 4. CronJob 的三种并发策略有什么区别？

**参考答案：**

| 策略 | 行为 | 适用场景 |
|------|------|---------|
| Allow | 允许并发执行（默认） | 任务之间无依赖 |
| Forbid | 上一个未完成则跳过本次 | 任务有冲突（如写同一文件） |
| Replace | 终止正在运行的，启动新的 | 始终使用最新数据 |

Forbid 是最安全的选择，防止资源竞争和数据冲突。

### 5. 如何实现 Job 的并行处理？

**参考答案：**

两种模式：
1. **带 completions 的并行**：设置 completions 和 parallelism，Job 创建 completions 个 Pod，parallelism 个并行运行。每个 Pod 处理一个任务，通过 JOB_COMPLETION_INDEX 区分。

2. **无 completions 的并行**：只设置 parallelism，所有 Pod 并行运行，任意一个成功 Job 就完成。适用于竞争性任务。

```yaml
# 模式 1: 处理 100 个任务，10 个并行
spec:
  completions: 100
  parallelism: 10
  completionMode: Indexed
```

### 6. DaemonSet 的更新策略 RollingUpdate 有什么限制？

**参考答案：**

DaemonSet 的 RollingUpdate 与 Deployment 不同：
- **不支持 maxSurge**：因为每个节点只能运行一个 Pod，不能创建额外 Pod
- **只支持 maxUnavailable**：控制更新时最多有多少个 Pod 不可用
- **更新顺序不确定**：不像 StatefulSet 有固定顺序

maxUnavailable 可以是：
- 绝对数：`maxUnavailable: 1`（默认，一次更新一个节点）
- 百分比：`maxUnavailable: 25%`（一次更新 25% 的节点）

### 7. CronJob 的 startingDeadlineSeconds 有什么作用？

**参考答案：**

startingDeadlineSeconds 指定如果错过了调度时间，Job 是否仍然应该启动的截止时间（秒）。

作用：
- 如果 CronJob Controller 由于某种原因（如 Controller Manager 安装/重启）错过了调度时间，startingDeadlineSeconds 决定是否仍然创建 Job
- 如果当前时间 - 预期调度时间 > startingDeadlineSeconds，则跳过本次调度
- 如果不设置，默认为 0，表示不启动错过的 Job

建议：设置为 100-300 秒，应对 Controller Manager 短暂不可用的情况。

### 8. 如何清理已完成的 Job？

**参考答案：**

三种方式：
1. **ttlSecondsAfterFinished**（推荐）：Job 完成后自动清理
   ```yaml
   spec:
     ttlSecondsAfterFinished: 3600  # 完成后 1 小时清理
   ```

2. **CronJob 的 history limit**：限制保留的历史 Job 数量
   ```yaml
   spec:
     successfulJobsHistoryLimit: 3
     failedJobsHistoryLimit: 1
   ```

3. **手动清理**：
   ```bash
   kubectl delete job <job-name>
   kubectl delete jobs --all  # 删除所有 Job
   ```

### 9. DaemonSet Pod 如何访问主机资源？

**参考答案：**

```yaml
spec:
  template:
    spec:
      hostNetwork: true     # 使用主机网络栈
      hostPID: true         # 使用主机 PID 命名空间
      hostIPC: true         # 使用主机 IPC 命名空间
      containers:
      - name: agent
        securityContext:
          privileged: true  # 特权模式（访问所有设备）
        volumeMounts:
        - name: host-fs
          mountPath: /host
          mountPropagation: Bidirectional
      volumes:
      - name: host-fs
        hostPath:
          path: /
          type: Directory
```

注意：这些设置有安全风险，应遵循最小权限原则。

### 10. Job 失败后如何排查？

**参考答案：**

```bash
# 1. 查看 Job 状态
kubectl describe job <job-name>
# 关注 Conditions 和 Events

# 2. 查看失败的 Pod
kubectl get pods -l job-name=<job-name> --field-selector=status.phase=Failed

# 3. 查看 Pod 日志
kubectl logs <failed-pod-name>
kubectl logs <failed-pod-name> --previous  # 上一次的日志

# 4. 常见失败原因:
# - 镜像拉取失败: ImagePullBackOff
# - 命令执行失败: 非 0 退出码
# - 资源不足: Pod Pending
# - 超时: activeDeadlineSeconds 超时
# - OOM: 内存不足

# 5. 修复后重新运行
kubectl delete job <job-name>
kubectl apply -f job.yaml  # 修改后的配置
```

---

## 📚 深入阅读

- [Kubernetes 官方文档 - DaemonSet](https://kubernetes.io/zh-cn/docs/concepts/workloads/controllers/daemonset/)
- [Kubernetes 官方文档 - Job](https://kubernetes.io/zh-cn/docs/concepts/workloads/controllers/job/)
- [Kubernetes 官方文档 - CronJob](https://kubernetes.io/zh-cn/docs/concepts/workloads/controllers/cron-jobs/)
- [Kubernetes 官方文档 - 使用 CronJob 运行自动化任务](https://kubernetes.io/zh-cn/docs/tasks/job/automated-tasks-with-cron-jobs/)

---

## ✅ 自检清单

- [ ] 理解 DaemonSet 的设计目的和使用场景
- [ ] 掌握 DaemonSet 与 Deployment 的区别
- [ ] 理解 DaemonSet 的节点选择策略（nodeSelector/Affinity/Toleration）
- [ ] 掌握 DaemonSet 的更新策略（RollingUpdate/OnDelete）
- [ ] 能使用 DaemonSet 部署日志收集和监控 Agent
- [ ] 理解 Job 的工作原理和三种并行模式
- [ ] 掌握 Job 的 backoffLimit、activeDeadlineSeconds、ttlSecondsAfterFinished
- [ ] 理解 CronJob 的调度机制和三种并发策略
- [ ] 掌握 Cron 表达式的编写
- [ ] 能使用 Job/CronJob 执行批处理和定时任务
- [ ] 能排查 Job/CronJob 的常见问题
