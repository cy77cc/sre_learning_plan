# Day 103: 搭建 K8s 生产级应用

> 📅 日期：2026-05-03
> 📖 学习主题：完整微服务部署、ConfigMap/Secret、Service/Ingress、HPA、PDB、资源配额、LimitRange、网络策略
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 93-102（K8s 全部基础知识、Helm）

## 🎯 学习目标

- 能够设计和部署完整的微服务架构
- 掌握 ConfigMap 和 Secret 的生产级使用
- 精通 Service 和 Ingress 的配置与优化
- 理解 PDB（PodDisruptionBudget）并能保障高可用
- 掌握 ResourceQuota 和 LimitRange 的资源管理
- 能够使用 NetworkPolicy 实现网络隔离
- 综合运用所有 K8s 知识搭建生产级应用

---

## 📖 核心知识点

### 1. 生产级应用架构设计

#### 1.1 微服务架构全景

```
┌─────────────────────────────────────────────────────────────────────┐
│                    生产级 K8s 应用架构                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Ingress Layer                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ TLS 终止     │  │ 路由规则      │  │ 限流/WAF     │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Service Layer                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │ Web Svc  │  │ API Svc  │  │ Auth Svc │  │ Cache Svc│   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Application Layer                         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │ Web App  │  │ API Srv  │  │ Auth Srv │  │ Worker   │   │   │
│  │  │ (React)  │  │ (Python) │  │ (Go)     │  │ (Python) │   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Data Layer                                │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │ MySQL    │  │ Redis    │  │ MongoDB  │  │ S3/OSS   │   │   │
│  │  │(StatefulSet)│(Deploy)  │  │(StatefulSet)│(External)│   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  横切关注点：                                                        │
│  - ConfigMap/Secret 管理配置与凭证                                   │
│  - HPA 自动扩缩容                                                   │
│  - PDB 保障高可用                                                   │
│  - ResourceQuota/LimitRange 资源管理                                │
│  - NetworkPolicy 网络隔离                                           │
│  - RBAC 权限控制                                                    │
│  - Monitoring & Logging                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 2. Namespace 与资源隔离

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    env: production
    managed-by: sre-team
---
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    env: staging
    managed-by: sre-team
```

---

### 3. ConfigMap — 配置管理

#### 3.1 ConfigMap 创建方式

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
  labels:
    app: my-app
# 方式 1：键值对
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
  DB_HOST: "mysql.production.svc.cluster.local"
  DB_PORT: "3306"
  DB_NAME: "myapp"
  CACHE_TTL: "300"
  MAX_CONNECTIONS: "100"

# 方式 2：文件内容
  nginx.conf: |
    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://api-server:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /healthz {
            return 200 'ok';
        }
    }

# 方式 3：多行配置文件
  application.yaml: |
    server:
      port: 8080
      timeout: 30s
    database:
      host: mysql.production.svc.cluster.local
      port: 3306
      pool:
        min: 5
        max: 20
    redis:
      host: redis.production.svc.cluster.local
      port: 6379
      db: 0
```

#### 3.2 ConfigMap 使用方式

```yaml
# 方式 1：环境变量（单个）
env:
  - name: APP_ENV
    valueFrom:
      configMapKeyRef:
        name: app-config
        key: APP_ENV

# 方式 2：环境变量（全部键值对）
envFrom:
  - configMapRef:
      name: app-config

# 方式 3：挂载为文件
volumeMounts:
  - name: config-volume
    mountPath: /app/config
    readOnly: true
volumes:
  - name: config-volume
    configMap:
      name: app-config
      items:
        - key: application.yaml
          path: application.yaml
        - key: nginx.conf
          path: nginx.conf
```

#### 3.3 ConfigMap 热更新

```yaml
# ConfigMap 挂载为文件时支持热更新（无需重启 Pod）
# 但使用 subPath 挂载时不支持热更新
# 环境变量方式也不支持热更新（需要重启 Pod）

# 推荐：使用 SHA256 注解触发滚动更新
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    metadata:
      annotations:
        # 当 ConfigMap 内容变化时，此注解会变化，触发 Pod 重建
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

---

### 4. Secret — 敏感信息管理

#### 4.1 Secret 类型

```yaml
# 类型 1：Opaque（通用 Secret）
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
  namespace: production
type: Opaque
data:
  # Base64 编码的值
  DB_PASSWORD: cGFzc3dvcmQxMjM=  # password123
  API_KEY: c2VjcmV0LWFwaS1rZXk=  # secret-api-key
stringData:
  # 明文字符串（K8s 自动编码）
  JWT_SECRET: "my-jwt-secret-key-2024"
  ENCRYPTION_KEY: "aes-256-encryption-key"

---
# 类型 2：TLS Secret
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
  namespace: production
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>

---
# 类型 3：Docker Registry Secret
apiVersion: v1
kind: Secret
metadata:
  name: registry-secret
  namespace: production
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: eyJhdXRocyI6eyJyZWdpc3RyeS5leGFtcGxlLmNvbSI6eyJ1c2VybmFtZSI6InVzZXIiLCJwYXNzd29yZCI6InBhc3MifX19
```

#### 4.2 Secret 使用方式

```yaml
# 环境变量方式
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: app-secret
        key: DB_PASSWORD

# 挂载为文件
volumeMounts:
  - name: secret-volume
    mountPath: /app/secrets
    readOnly: true
volumes:
  - name: secret-volume
    secret:
      secretName: app-secret
      defaultMode: 0400  # 只读权限
```

#### 4.3 Secret 管理最佳实践

```
生产环境 Secret 管理策略：

1. 不要将 Secret 提交到 Git 仓库
2. 使用外部 Secret 管理工具：
   - HashiCorp Vault
   - AWS Secrets Manager
   - Azure Key Vault
   - External Secrets Operator（K8s 原生）
3. 使用 Sealed Secrets 加密 Secret
4. 定期轮转 Secret
5. 使用 RBAC 限制 Secret 访问权限
```

```yaml
# External Secrets Operator 示例
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secret
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: app-secret
    creationPolicy: Owner
  data:
    - secretKey: DB_PASSWORD
      remoteRef:
        key: production/myapp/database
        property: password
    - secretKey: API_KEY
      remoteRef:
        key: production/myapp/api
        property: key
```

---

### 5. Deployment — 生产级部署配置

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: production
  labels:
    app: api-server
    version: v2.1.0
    tier: backend
spec:
  replicas: 3
  # 保留 5 个历史版本用于回滚
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: api-server
  strategy:
    type: RollingUpdate
    rollingUpdate:
      # 滚动更新策略
      maxSurge: 1        # 最多比期望多 1 个 Pod
      maxUnavailable: 0   # 更新时不允许不可用
  template:
    metadata:
      labels:
        app: api-server
        version: v2.1.0
        tier: backend
      annotations:
        # ConfigMap/Secret 变更时触发重建
        checksum/config: "abc123"
        checksum/secret: "def456"
        # Prometheus 监控注解
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      # 优雅终止时间
      terminationGracePeriodSeconds: 30
      # 服务账户
      serviceAccountName: api-server
      # 安全上下文
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      # 镜像拉取凭证
      imagePullSecrets:
        - name: registry-secret
      # 亲和性（跨节点高可用）
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values:
                      - api-server
              topologyKey: kubernetes.io/hostname
      # 拓扑分布（跨可用区）
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: api-server
      containers:
        - name: api-server
          image: my-registry.com/api-server:v2.1.0
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          # 环境变量
          env:
            - name: APP_ENV
              value: "production"
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secret
                  key: DB_PASSWORD
          envFrom:
            - configMapRef:
                name: app-config
          # 资源限制
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
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
            initialDelaySeconds: 0
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 0
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          # 安全上下文
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          # 卷挂载
          volumeMounts:
            - name: config
              mountPath: /app/config
              readOnly: true
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: config
          configMap:
            name: app-config
        - name: tmp
          emptyDir: {}
```

---

### 6. Service — 服务发现与负载均衡

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-server
  namespace: production
  labels:
    app: api-server
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
  selector:
    app: api-server
---
# Headless Service（用于 StatefulSet）
apiVersion: v1
kind: Service
metadata:
  name: mysql-headless
  namespace: production
spec:
  type: ClusterIP
  clusterIP: None  # Headless Service
  ports:
    - name: mysql
      port: 3306
      targetPort: 3306
  selector:
    app: mysql
```

---

### 7. Ingress — 入口流量管理

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: main-ingress
  namespace: production
  annotations:
    # Nginx Ingress 注解
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    # 限流
    nginx.ingress.kubernetes.io/limit-rps: "100"
    nginx.ingress.kubernetes.io/limit-connections: "50"
    # CORS
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://my-app.example.com"
    # 重写路径
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - my-app.example.com
      secretName: tls-secret
  rules:
    - host: my-app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-frontend
                port:
                  number: 80
          - path: /api(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: api-server
                port:
                  number: 80
          - path: /auth(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: auth-server
                port:
                  number: 80
```

---

### 8. PDB（PodDisruptionBudget）— 高可用保障

#### 8.1 PDB 概念

```
PDB（PodDisruptionBudget）定义了在自愿中断期间，
允许不可用的 Pod 最小数量或最大比例。

自愿中断（Voluntary Disruption）：
  - 节点维护（kubectl drain）
  - 集群升级
  - 节点缩容（Cluster Autoscaler）
  - 手动删除 Pod

非自愿中断（Non-voluntary Disruption）：
  - 节点故障
  - 磁盘故障
  - 网络分区
  - OOM Kill
```

#### 8.2 PDB 配置

```yaml
# pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: production
spec:
  # 方式 1：minAvailable（最少可用 Pod 数）
  minAvailable: 2  # 至少 2 个 Pod 可用
  # minAvailable: "50%"  # 至少 50% 的 Pod 可用

  # 方式 2：maxUnavailable（最多不可用 Pod 数）
  # maxUnavailable: 1  # 最多 1 个 Pod 不可用
  # maxUnavailable: "25%"  # 最多 25% 的 Pod 不可用

  # 注意：minAvailable 和 maxUnavailable 二选一
  selector:
    matchLabels:
      app: api-server

---
# 常见的 PDB 配置模式
# 1. 关键服务：至少 2 个副本可用
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: critical-service

---
# 2. 一般服务：最多 1 个不可用
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: standard-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: standard-service

---
# 3. 使用百分比
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: percentage-pdb
spec:
  minAvailable: "67%"
  selector:
    matchLabels:
      app: percentage-service
```

#### 8.3 PDB 与节点维护

```bash
# 节点维护前的正确流程：
# 1. 检查 PDB
kubectl get pdb -A

# 2. 标记节点为不可调度
kubectl cordon node-1

# 3. 驱逐节点上的 Pod（尊重 PDB）
kubectl drain node-1 --ignore-daemonsets --delete-emptydir-data

# 4. 执行维护...

# 5. 恢复节点
kubectl uncordon node-1
```

#### 8.4 SRE 实战：PDB 设计策略

```yaml
# 生产环境 PDB 设计原则：
# 1. 所有关键服务必须配置 PDB
# 2. PDB 配置与副本数协调
# 3. 不要将 minAvailable 设置为等于副本数

# 正确示例：3 副本服务，minAvailable=2
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: production
spec:
  minAvailable: 2  # 允许 1 个 Pod 中断
  selector:
    matchLabels:
      app: api-server

# 错误示例：3 副本服务，minAvailable=3
# 这会导致节点维护时无法驱逐任何 Pod
```

---

### 9. ResourceQuota — 资源配额

#### 9.1 ResourceQuota 配置

```yaml
# resourcequota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: production-quota
  namespace: production
spec:
  hard:
    # 计算资源限制
    requests.cpu: "20"        # 总 CPU 请求不超过 20 核
    requests.memory: "40Gi"   # 总内存请求不超过 40Gi
    limits.cpu: "40"          # 总 CPU 限制不超过 40 核
    limits.memory: "80Gi"     # 总内存限制不超过 80Gi

    # 对象数量限制
    pods: "50"                # 最多 50 个 Pod
    services: "20"            # 最多 20 个 Service
    secrets: "30"             # 最多 30 个 Secret
    configmaps: "30"          # 最多 30 个 ConfigMap
    persistentvolumeclaims: "10"  # 最多 10 个 PVC
    services.loadbalancers: "3"   # 最多 3 个 LoadBalancer
    services.nodeports: "5"       # 最多 5 个 NodePort

    # 存储限制
    requests.storage: "100Gi" # 总存储请求不超过 100Gi
```

#### 9.2 查看配额使用情况

```bash
# 查看配额
kubectl get resourcequota -n production
kubectl describe resourcequota production-quota -n production

# 输出示例：
# Name:                   production-quota
# Resource                Used   Hard
# --------                ----   ----
# limits.cpu              10     40
# limits.memory           20Gi   80Gi
# pods                    15     50
# requests.cpu            5      20
# requests.memory         10Gi   40Gi
```

---

### 10. LimitRange — 默认资源限制

```yaml
# limitrange.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: production-limitrange
  namespace: production
spec:
  limits:
    # 容器默认限制
    - type: Container
      default:
        cpu: "500m"
        memory: "512Mi"
      defaultRequest:
        cpu: "100m"
        memory: "128Mi"
      max:
        cpu: "4"
        memory: "8Gi"
      min:
        cpu: "50m"
        memory: "64Mi"
      maxLimitRequestRatio:
        cpu: "10"
        memory: "4"

    # Pod 默认限制
    - type: Pod
      max:
        cpu: "8"
        memory: "16Gi"

    # PVC 限制
    - type: PersistentVolumeClaim
      max:
        storage: "50Gi"
      min:
        storage: "1Gi"
```

---

### 11. NetworkPolicy — 网络策略

#### 11.1 网络策略概述

```
NetworkPolicy 控制 Pod 的入站（Ingress）和出站（Egress）流量

默认行为（无 NetworkPolicy）：
  - 所有 Pod 可以互相通信
  - 所有 Pod 可以访问外部网络

NetworkPolicy 启用后：
  - 未被任何 NetworkPolicy 选中的 Pod：保持默认行为
  - 被 NetworkPolicy 选中的 Pod：只允许策略中定义的流量
```

#### 11.2 默认拒绝策略

```yaml
# 默认拒绝所有入站流量
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}  # 选中所有 Pod
  policyTypes:
    - Ingress

---
# 默认拒绝所有出站流量
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}  # 选中所有 Pod
  policyTypes:
    - Egress
```

#### 11.3 允许特定流量

```yaml
# 允许 Ingress Controller 访问 Web 服务
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-to-web
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: web-frontend
  policyTypes:
    - Ingress
  ingress:
    - from:
        # 允许 Ingress Controller 的流量
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
          podSelector:
            matchLabels:
              app.kubernetes.io/name: ingress-nginx
      ports:
        - protocol: TCP
          port: 80

---
# 允许 API 服务访问数据库
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-mysql
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: mysql
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-server
      ports:
        - protocol: TCP
          port: 3306

---
# 允许 API 服务访问 Redis
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-redis
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: redis
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-server
      ports:
        - protocol: TCP
          port: 6379

---
# 允许 API 服务访问 DNS
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
    # 允许访问外部 HTTPS
    - to: []
      ports:
        - protocol: TCP
          port: 443
```

#### 11.4 完整的网络策略示例

```yaml
# 完整的微服务网络策略
# 1. 默认拒绝所有
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress

---
# 2. 允许 DNS 查询
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53

---
# 3. Web 前端：允许来自 Ingress 的入站，允许访问 API
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-frontend-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: web-frontend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 80
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: api-server
      ports:
        - protocol: TCP
          port: 8080

---
# 4. API 服务：允许来自 Web 的入站，允许访问 MySQL 和 Redis
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-server-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: web-frontend
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: mysql
      ports:
        - protocol: TCP
          port: 3306
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379

---
# 5. MySQL：只允许 API 访问
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mysql-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: mysql
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-server
      ports:
        - protocol: TCP
          port: 3306
  egress: []  # MySQL 不需要主动出站

---
# 6. Redis：只允许 API 和 Worker 访问
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: redis-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: redis
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-server
        - podSelector:
            matchLabels:
              app: worker
      ports:
        - protocol: TCP
          port: 6379
  egress: []
```

---

### 12. 完整的微服务部署清单

#### 12.1 部署顺序

```
部署顺序（考虑依赖关系）：

1. Namespace
2. ResourceQuota + LimitRange
3. Secret（数据库凭证等）
4. ConfigMap（应用配置）
5. NetworkPolicy（网络隔离）
6. PVC（持久化存储）
7. StatefulSet（MySQL、Redis）
8. Deployment（API、Web、Worker）
9. Service（服务发现）
10. Ingress（入口路由）
11. HPA（自动扩缩容）
12. PDB（高可用保障）
```

#### 12.2 一键部署脚本

```bash
#!/bin/bash
# deploy.sh - 生产环境部署脚本

set -euo pipefail

NAMESPACE="production"
APP_DIR="./k8s-manifests"

echo "=== Deploying to ${NAMESPACE} ==="

# 1. 创建命名空间
echo "1. Creating namespace..."
kubectl apply -f ${APP_DIR}/namespace.yaml

# 2. 资源配额与限制
echo "2. Applying resource quotas and limits..."
kubectl apply -f ${APP_DIR}/resourcequota.yaml
kubectl apply -f ${APP_DIR}/limitrange.yaml

# 3. 敏感信息
echo "3. Creating secrets..."
kubectl apply -f ${APP_DIR}/secrets.yaml

# 4. 配置信息
echo "4. Creating configmaps..."
kubectl apply -f ${APP_DIR}/configmap.yaml

# 5. 网络策略
echo "5. Applying network policies..."
kubectl apply -f ${APP_DIR}/networkpolicy.yaml

# 6. 持久化存储
echo "6. Creating PVCs..."
kubectl apply -f ${APP_DIR}/pvc.yaml

# 7. 数据库服务
echo "7. Deploying databases..."
kubectl apply -f ${APP_DIR}/mysql-statefulset.yaml
kubectl apply -f ${APP_DIR}/redis-deployment.yaml

# 等待数据库就绪
echo "Waiting for databases to be ready..."
kubectl rollout status statefulset/mysql -n ${NAMESPACE} --timeout=300s
kubectl rollout status deployment/redis -n ${NAMESPACE} --timeout=120s

# 8. 应用服务
echo "8. Deploying application services..."
kubectl apply -f ${APP_DIR}/api-deployment.yaml
kubectl apply -f ${APP_DIR}/web-deployment.yaml
kubectl apply -f ${APP_DIR}/worker-deployment.yaml

# 9. Service
echo "9. Creating services..."
kubectl apply -f ${APP_DIR}/services.yaml

# 10. Ingress
echo "10. Creating ingress..."
kubectl apply -f ${APP_DIR}/ingress.yaml

# 11. HPA
echo "11. Creating HPA..."
kubectl apply -f ${APP_DIR}/hpa.yaml

# 12. PDB
echo "12. Creating PDB..."
kubectl apply -f ${APP_DIR}/pdb.yaml

# 验证部署
echo "=== Verifying deployment ==="
kubectl get pods -n ${NAMESPACE}
kubectl get svc -n ${NAMESPACE}
kubectl get ingress -n ${NAMESPACE}
kubectl get hpa -n ${NAMESPACE}
kubectl get pdb -n ${NAMESPACE}

echo "=== Deployment complete ==="
```

---

## 💻 实战练习

### 练习 1：搭建完整的微服务应用

**目标**：部署一个包含前端、API、数据库的完整应用

```bash
# 创建项目目录
mkdir -p k8s-production/{manifests,scripts}

# 按照本章的 YAML 文件逐一创建并部署
kubectl apply -f manifests/namespace.yaml
kubectl apply -f manifests/configmap.yaml
kubectl apply -f manifests/secrets.yaml
kubectl apply -f manifests/mysql-statefulset.yaml
kubectl apply -f manifests/api-deployment.yaml
kubectl apply -f manifests/web-deployment.yaml
kubectl apply -f manifests/services.yaml
kubectl apply -f manifests/ingress.yaml

# 验证
kubectl get all -n production
```

### 练习 2：配置 NetworkPolicy 实现网络隔离

**目标**：为微服务配置网络策略，只允许必要的通信

```bash
# 部署网络策略
kubectl apply -f manifests/networkpolicy.yaml

# 测试：从 Web Pod 访问 API（应该成功）
kubectl exec -it deploy/web-frontend -n production -- curl http://api-server:8080/healthz

# 测试：从 Web Pod 直接访问 MySQL（应该被拒绝）
kubectl exec -it deploy/web-frontend -n production -- curl http://mysql:3306

# 测试：从 API Pod 访问 MySQL（应该成功）
kubectl exec -it deploy/api-server -n production -- curl http://mysql:3306
```

### 练习 3：故障排查 — Pod 无法启动

**场景**：新部署的 Pod 一直处于 CrashLoopBackOff 状态。

```bash
# 1. 查看 Pod 状态
kubectl get pods -n production | grep CrashLoop

# 2. 查看 Pod 事件
kubectl describe pod <pod-name> -n production

# 3. 查看容器日志
kubectl logs <pod-name> -n production --previous
kubectl logs <pod-name> -n production

# 4. 检查资源限制
kubectl get pod <pod-name> -n production -o jsonpath='{.spec.containers[0].resources}'

# 5. 检查 ConfigMap/Secret
kubectl get configmap -n production
kubectl get secret -n production

# 6. 进入容器调试
kubectl exec -it <pod-name> -n production -- /bin/sh

# 7. 常见原因：
#    - 镜像拉取失败（ImagePullBackOff）
#    - 启动命令错误
#    - 缺少环境变量或配置文件
#    - 资源不足（OOMKilled）
#    - 健康检查失败
```

---

## 🎯 面试题精选

### 1. PDB（PodDisruptionBudget）的作用是什么？

**答**：PDB 定义了在自愿中断（节点维护、集群升级、缩容）期间，允许不可用的 Pod 最小数量或最大比例。它确保关键服务在维护期间保持可用。例如 `minAvailable: 2` 表示至少 2 个 Pod 必须保持运行。

### 2. ResourceQuota 和 LimitRange 的区别？

**答**：
- **ResourceQuota**：限制整个 namespace 的资源使用总量（CPU、内存、对象数量）
- **LimitRange**：为 namespace 中的 Pod/Container 设置默认资源限制和范围约束
- ResourceQuota 是"总量控制"，LimitRange 是"个体约束"

### 3. NetworkPolicy 的默认行为是什么？

**答**：
- 没有 NetworkPolicy 时：所有 Pod 可以互相通信
- 创建了默认拒绝策略后：只有显式允许的流量才能通过
- NetworkPolicy 是 namespace 级别的
- 需要 CNI 插件支持（如 Calico、Cilium）

### 4. ConfigMap 的热更新机制？

**答**：
- 挂载为文件（volumeMount）：支持热更新，kubelet 会周期性检查 ConfigMap 变更
- 使用 subPath 挂载：不支持热更新
- 环境变量方式：不支持热更新，需要重启 Pod
- 推荐：使用 SHA256 注解触发滚动更新

### 5. 如何实现零停机部署？

**答**：
1. 使用 RollingUpdate 策略（maxUnavailable: 0）
2. 配置 PDB 确保最少可用 Pod 数
3. 配置 startupProbe 避免启动慢的 Pod 被杀
4. 配置 readinessProbe 确保流量只到就绪的 Pod
5. 使用 pre-upgrade Hook 执行数据库迁移

### 6. Secret 和 ConfigMap 的区别？

**答**：
- **ConfigMap**：存储非敏感配置数据，以明文存储
- **Secret**：存储敏感信息（密码、密钥），以 Base64 编码存储
- Secret 可以设置更严格的 RBAC 权限
- Secret 支持加密存储（需要配置加密提供程序）

### 7. 生产环境部署的关键配置有哪些？

**答**：
1. **资源限制**：requests 和 limits
2. **健康检查**：startup/liveness/readiness probe
3. **PDB**：保障高可用
4. **HPA**：自动扩缩容
5. **NetworkPolicy**：网络隔离
6. **SecurityContext**：安全加固
7. **Affinity**：跨节点/可用区分布
8. **ResourceQuota**：资源配额

### 8. 如何设计网络策略实现最小权限原则？

**答**：
1. 默认拒绝所有入站和出站流量
2. 只允许 DNS 查询（kube-dns）
3. 按服务间依赖关系逐步放开
4. 使用 label selector 精确控制
5. 定期审查和更新策略

### 9. Ingress 和 Service 的关系？

**答**：
- Service 提供集群内部的服务发现和负载均衡
- Ingress 提供集群外部的 HTTP/HTTPS 路由
- Ingress 通过 Service 将外部流量路由到 Pod
- Ingress 支持 TLS 终止、路径重写、限流等高级功能

### 10. 如何排查网络策略导致的连接问题？

**答**：
```bash
# 1. 查看 NetworkPolicy
kubectl get networkpolicy -n production

# 2. 临时删除 NetworkPolicy 测试
kubectl delete networkpolicy <policy-name> -n production

# 3. 使用 tcpdump 抓包
kubectl exec -it <pod-name> -n production -- tcpdump -i eth0

# 4. 检查 CNI 插件日志
kubectl logs -n kube-system -l k8s-app=calico-node
```

---

## 📚 深入阅读

- [Kubernetes 官方文档：配置最佳实践](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Kubernetes 官方文档：PodDisruptionBudget](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Kubernetes 官方文档：ResourceQuota](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
- [Kubernetes 官方文档：LimitRange](https://kubernetes.io/docs/concepts/policy/limit-range/)
- [Kubernetes 官方文档：NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Kubernetes 安全最佳实践](https://kubernetes.io/docs/concepts/security/overview/)
- [12 Factor App 与 Kubernetes](https://12factor.net/)

---

## ✅ 自检清单

- [ ] 能够设计完整的微服务架构
- [ ] 能够配置 ConfigMap 和 Secret 的多种使用方式
- [ ] 能够编写生产级的 Deployment 配置
- [ ] 能够配置 Service 和 Ingress 实现流量路由
- [ ] 能够使用 PDB 保障服务高可用
- [ ] 能够使用 ResourceQuota 和 LimitRange 管理资源
- [ ] 能够使用 NetworkPolicy 实现网络隔离
- [ ] 理解部署顺序和依赖关系
- [ ] 能够编写一键部署脚本
- [ ] 能够排查生产环境的常见故障
