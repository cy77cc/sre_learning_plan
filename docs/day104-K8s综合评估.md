# Day 104: K8s 综合评估 — 部署完整应用 + 理论测试

> 📅 日期：2026-05-03
> 📖 学习主题：综合项目验证、故障注入、恢复演练、理论测试、实战场景
> ⏰ 预计学习时间：6-8 小时
> 📋 前置知识：Day 93-103（K8s 全部知识）

## 🎯 学习目标

- 综合验证 Day 93-103 的所有 K8s 知识
- 能够独立完成生产级应用的部署与验证
- 掌握故障注入与恢复演练方法
- 通过 20 道理论测试题检验学习成果
- 通过 5 个实战场景提升问题解决能力

---

## 📖 核心知识点

### 1. 综合项目架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SRE Shop — 电商微服务应用                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Ingress (nginx)                                            │   │
│  │  ├── shop.example.com/       → Web Frontend                 │   │
│  │  ├── shop.example.com/api    → API Server                   │   │
│  │  └── shop.example.com/admin  → Admin Panel                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Application Layer                                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │ Web      │  │ API      │  │ Admin    │  │ Worker   │   │   │
│  │  │ Frontend │  │ Server   │  │ Panel    │  │ (Async)  │   │   │
│  │  │ (React)  │  │ (Python) │  │ (React)  │  │ (Python) │   │   │
│  │  │ 3 replicas│ │ 3 replicas│ │ 2 replicas│ │ 2 replicas│   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Data Layer                                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │   │
│  │  │ MySQL    │  │ Redis    │  │ RabbitMQ │                 │   │
│  │  │ 3 replicas│ │ 3 replicas│ │ 1 replica│                 │   │
│  │  │(StatefulSet)│(Deploy)  │  │(StatefulSet)│              │   │
│  │  └──────────┘  └──────────┘  └──────────┘                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  横切关注点：                                                        │
│  ✓ ConfigMap/Secret   ✓ HPA         ✓ PDB                          │
│  ✓ ResourceQuota      ✓ LimitRange  ✓ NetworkPolicy                │
│  ✓ RBAC               ✓ Monitoring  ✓ Logging                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 2. 完整部署配置

#### 2.1 Namespace 与资源管理

```yaml
# 01-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sre-shop
  labels:
    env: production
    team: sre
    app: sre-shop

---
# 02-resourcequota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: sre-shop-quota
  namespace: sre-shop
spec:
  hard:
    requests.cpu: "16"
    requests.memory: "32Gi"
    limits.cpu: "32"
    limits.memory: "64Gi"
    pods: "40"
    services: "15"
    secrets: "20"
    configmaps: "20"
    persistentvolumeclaims: "10"

---
# 03-limitrange.yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: sre-shop-limitrange
  namespace: sre-shop
spec:
  limits:
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
```

#### 2.2 Secret 与 ConfigMap

```yaml
# 04-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: sre-shop
type: Opaque
stringData:
  MYSQL_ROOT_PASSWORD: "RootP@ssw0rd2024!"
  MYSQL_DATABASE: "sre_shop"
  MYSQL_USER: "app_user"
  MYSQL_PASSWORD: "AppP@ssw0rd2024!"
  DATABASE_URL: "mysql://app_user:AppP@ssw0rd2024!@mysql.sre-shop.svc.cluster.local:3306/sre_shop"

---
apiVersion: v1
kind: Secret
metadata:
  name: redis-secret
  namespace: sre-shop
type: Opaque
stringData:
  REDIS_PASSWORD: "RedisP@ssw0rd2024!"
  REDIS_URL: "redis://:RedisP@ssw0rd2024!@redis.sre-shop.svc.cluster.local:6379/0"

---
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
  namespace: sre-shop
type: Opaque
stringData:
  JWT_SECRET: "jwt-secret-key-2024-production"
  ENCRYPTION_KEY: "aes-256-encryption-key-2024"

---
# 05-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: sre-shop
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
  LOG_FORMAT: "json"
  DB_HOST: "mysql.sre-shop.svc.cluster.local"
  DB_PORT: "3306"
  DB_NAME: "sre_shop"
  REDIS_HOST: "redis.sre-shop.svc.cluster.local"
  REDIS_PORT: "6379"
  RABBITMQ_HOST: "rabbitmq.sre-shop.svc.cluster.local"
  RABBITMQ_PORT: "5672"
  CACHE_TTL: "300"
  SESSION_TIMEOUT: "3600"
  MAX_CONNECTIONS: "100"
  WORKER_CONCURRENCY: "10"
```

#### 2.3 数据库服务（StatefulSet）

```yaml
# 06-mysql.yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
  namespace: sre-shop
spec:
  type: ClusterIP
  clusterIP: None
  ports:
    - name: mysql
      port: 3306
      targetPort: 3306
  selector:
    app: mysql

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: sre-shop
spec:
  serviceName: mysql
  replicas: 1
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
          env:
            - name: MYSQL_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: MYSQL_ROOT_PASSWORD
            - name: MYSQL_DATABASE
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: MYSQL_DATABASE
            - name: MYSQL_USER
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: MYSQL_USER
            - name: MYSQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: MYSQL_PASSWORD
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          volumeMounts:
            - name: mysql-data
              mountPath: /var/lib/mysql
          livenessProbe:
            exec:
              command:
                - mysqladmin
                - ping
                - -h
                - localhost
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
                - mysql
                - -h
                - localhost
                - -u
                - root
                - -p$(MYSQL_ROOT_PASSWORD)
                - -e
                - "SELECT 1"
            initialDelaySeconds: 10
            periodSeconds: 5
  volumeClaimTemplates:
    - metadata:
        name: mysql-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
```

```yaml
# 07-redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: sre-shop
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command: ["redis-server"]
          args:
            - "--requirepass"
            - "$(REDIS_PASSWORD)"
            - "--maxmemory"
            - "256mb"
            - "--maxmemory-policy"
            - "allkeys-lru"
          ports:
            - containerPort: 6379
          env:
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: redis-secret
                  key: REDIS_PASSWORD
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            exec:
              command:
                - redis-cli
                - -a
                - $(REDIS_PASSWORD)
                - ping
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            exec:
              command:
                - redis-cli
                - -a
                - $(REDIS_PASSWORD)
                - ping
            initialDelaySeconds: 5
            periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: sre-shop
spec:
  type: ClusterIP
  ports:
    - port: 6379
      targetPort: 6379
  selector:
    app: redis
```

#### 2.4 应用服务（Deployment）

```yaml
# 08-api-server.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: sre-shop
spec:
  replicas: 3
  revisionHistoryLimit: 5
  selector:
    matchLabels:
      app: api-server
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: api-server
        tier: backend
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      terminationGracePeriodSeconds: 30
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
      containers:
        - name: api-server
          image: sre-registry.example.com/api-server:v2.1.0
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: MYSQL_PASSWORD
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: redis-secret
                  key: REDIS_PASSWORD
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: app-secret
                  key: JWT_SECRET
          envFrom:
            - configMapRef:
                name: app-config
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
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
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: api-server
  namespace: sre-shop
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
  selector:
    app: api-server
```

```yaml
# 09-web-frontend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: sre-shop
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
        tier: frontend
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values:
                      - web-frontend
              topologyKey: kubernetes.io/hostname
      containers:
        - name: web
          image: sre-registry.example.com/web-frontend:v2.1.0
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

---
apiVersion: v1
kind: Service
metadata:
  name: web-frontend
  namespace: sre-shop
spec:
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 80
  selector:
    app: web-frontend
```

```yaml
# 10-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker
  namespace: sre-shop
spec:
  replicas: 2
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
        tier: backend
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: worker
          image: sre-registry.example.com/worker:v2.1.0
          command: ["python", "worker.py"]
          envFrom:
            - configMapRef:
                name: app-config
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: MYSQL_PASSWORD
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: redis-secret
                  key: REDIS_PASSWORD
          resources:
            requests:
              cpu: "200m"
              memory: "256Mi"
            limits:
              cpu: "1"
              memory: "1Gi"
          livenessProbe:
            exec:
              command: ["python", "healthcheck.py"]
            initialDelaySeconds: 30
            periodSeconds: 15
```

#### 2.5 Ingress 配置

```yaml
# 11-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: sre-shop-ingress
  namespace: sre-shop
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "20m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    nginx.ingress.kubernetes.io/limit-rps: "100"
    nginx.ingress.kubernetes.io/limit-connections: "50"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - shop.example.com
      secretName: shop-tls
  rules:
    - host: shop.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-server
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-frontend
                port:
                  number: 80
```

#### 2.6 HPA 配置

```yaml
# 12-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-server-hpa
  namespace: sre-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-server
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 75
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
        - type: Pods
          value: 1
          periodSeconds: 60
      selectPolicy: Min

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-frontend-hpa
  namespace: sre-shop
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-frontend
  minReplicas: 3
  maxReplicas: 15
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Pods
          value: 5
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
      selectPolicy: Min
```

#### 2.7 PDB 配置

```yaml
# 13-pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: sre-shop
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: api-server

---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-frontend-pdb
  namespace: sre-shop
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-frontend
```

#### 2.8 NetworkPolicy 配置

```yaml
# 14-networkpolicy.yaml
# 默认拒绝所有
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: sre-shop
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress

---
# 允许 DNS
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: sre-shop
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
# Ingress → Web Frontend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-to-web
  namespace: sre-shop
spec:
  podSelector:
    matchLabels:
      app: web-frontend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
      ports:
        - protocol: TCP
          port: 80

---
# Ingress → API Server
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-ingress-to-api
  namespace: sre-shop
spec:
  podSelector:
    matchLabels:
      app: api-server
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
        - podSelector:
            matchLabels:
              app: web-frontend
      ports:
        - protocol: TCP
          port: 8080

---
# API → MySQL
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-mysql
  namespace: sre-shop
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
        - podSelector:
            matchLabels:
              app: worker
      ports:
        - protocol: TCP
          port: 3306

---
# API → Redis
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-redis
  namespace: sre-shop
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
        - podSelector:
            matchLabels:
              app: worker
      ports:
        - protocol: TCP
          port: 6379
```

---

### 3. 部署验证

#### 3.1 部署脚本

```bash
#!/bin/bash
# deploy-sre-shop.sh
set -euo pipefail

NAMESPACE="sre-shop"
MANIFESTS_DIR="./manifests"

echo "========================================="
echo "  SRE Shop Production Deployment"
echo "========================================="

# 1. 基础设施
echo "[1/12] Creating namespace and resource quotas..."
kubectl apply -f ${MANIFESTS_DIR}/01-namespace.yaml
kubectl apply -f ${MANIFESTS_DIR}/02-resourcequota.yaml
kubectl apply -f ${MANIFESTS_DIR}/03-limitrange.yaml

# 2. 配置与凭证
echo "[2/12] Creating secrets and configmaps..."
kubectl apply -f ${MANIFESTS_DIR}/04-secrets.yaml
kubectl apply -f ${MANIFESTS_DIR}/05-configmap.yaml

# 3. 网络策略
echo "[3/12] Applying network policies..."
kubectl apply -f ${MANIFESTS_DIR}/14-networkpolicy.yaml

# 4. 数据库
echo "[4/12] Deploying MySQL..."
kubectl apply -f ${MANIFESTS_DIR}/06-mysql.yaml
echo "  Waiting for MySQL to be ready..."
kubectl rollout status statefulset/mysql -n ${NAMESPACE} --timeout=300s

echo "[5/12] Deploying Redis..."
kubectl apply -f ${MANIFESTS_DIR}/07-redis.yaml
kubectl rollout status deployment/redis -n ${NAMESPACE} --timeout=120s

# 5. 应用服务
echo "[6/12] Deploying API Server..."
kubectl apply -f ${MANIFESTS_DIR}/08-api-server.yaml
kubectl rollout status deployment/api-server -n ${NAMESPACE} --timeout=300s

echo "[7/12] Deploying Web Frontend..."
kubectl apply -f ${MANIFESTS_DIR}/09-web-frontend.yaml
kubectl rollout status deployment/web-frontend -n ${NAMESPACE} --timeout=180s

echo "[8/12] Deploying Worker..."
kubectl apply -f ${MANIFESTS_DIR}/10-worker.yaml
kubectl rollout status deployment/worker -n ${NAMESPACE} --timeout=180s

# 6. 路由与入口
echo "[9/12] Creating Ingress..."
kubectl apply -f ${MANIFESTS_DIR}/11-ingress.yaml

# 7. 自动扩缩容
echo "[10/12] Creating HPA..."
kubectl apply -f ${MANIFESTS_DIR}/12-hpa.yaml

# 8. 高可用保障
echo "[11/12] Creating PDB..."
kubectl apply -f ${MANIFESTS_DIR}/13-pdb.yaml

# 9. 验证
echo "[12/12] Verifying deployment..."
echo ""
echo "=== Pods ==="
kubectl get pods -n ${NAMESPACE} -o wide
echo ""
echo "=== Services ==="
kubectl get svc -n ${NAMESPACE}
echo ""
echo "=== Ingress ==="
kubectl get ingress -n ${NAMESPACE}
echo ""
echo "=== HPA ==="
kubectl get hpa -n ${NAMESPACE}
echo ""
echo "=== PDB ==="
kubectl get pdb -n ${NAMESPACE}
echo ""
echo "=== Resource Quota ==="
kubectl describe resourcequota -n ${NAMESPACE}
echo ""
echo "========================================="
echo "  Deployment Complete!"
echo "========================================="
```

#### 3.2 验证检查清单

```bash
# 验证脚本
#!/bin/bash
# verify.sh
set -euo pipefail

NAMESPACE="sre-shop"
ERRORS=0

echo "=== Verification Checklist ==="

# 1. 检查所有 Pod 是否 Running
echo -n "1. All pods running: "
NOT_RUNNING=$(kubectl get pods -n ${NAMESPACE} --no-headers | grep -v "Running\|Completed" | wc -l)
if [ "$NOT_RUNNING" -eq 0 ]; then
    echo "PASS"
else
    echo "FAIL ($NOT_RUNNING pods not running)"
    kubectl get pods -n ${NAMESPACE} | grep -v "Running\|Completed"
    ERRORS=$((ERRORS+1))
fi

# 2. 检查所有 Deployment 副本数
echo -n "2. All deployments at desired replicas: "
NOT_READY=$(kubectl get deployments -n ${NAMESPACE} --no-headers | awk '{if ($2 != $3) print $1}')
if [ -z "$NOT_READY" ]; then
    echo "PASS"
else
    echo "FAIL (Not ready: $NOT_READY)"
    ERRORS=$((ERRORS+1))
fi

# 3. 检查 HPA 状态
echo -n "3. HPA active: "
HPA_INACTIVE=$(kubectl get hpa -n ${NAMESPACE} --no-headers | grep -v "Active" | wc -l)
if [ "$HPA_INACTIVE" -eq 0 ]; then
    echo "PASS"
else
    echo "FAIL"
    ERRORS=$((ERRORS+1))
fi

# 4. 检查 PDB 状态
echo -n "4. PDB allowed disruptions > 0: "
PDB_OK=$(kubectl get pdb -n ${NAMESPACE} --no-headers | awk '{if ($4 > 0) print $1}' | wc -l)
PDB_TOTAL=$(kubectl get pdb -n ${NAMESPACE} --no-headers | wc -l)
if [ "$PDB_OK" -eq "$PDB_TOTAL" ]; then
    echo "PASS"
else
    echo "FAIL"
    ERRORS=$((ERRORS+1))
fi

# 5. 检查 Ingress
echo -n "5. Ingress configured: "
INGRESS=$(kubectl get ingress -n ${NAMESPACE} --no-headers | wc -l)
if [ "$INGRESS" -gt 0 ]; then
    echo "PASS"
else
    echo "FAIL"
    ERRORS=$((ERRORS+1))
fi

# 6. 检查 NetworkPolicy
echo -n "6. NetworkPolicy applied: "
NP=$(kubectl get networkpolicy -n ${NAMESPACE} --no-headers | wc -l)
if [ "$NP" -gt 0 ]; then
    echo "PASS ($NP policies)"
else
    echo "FAIL"
    ERRORS=$((ERRORS+1))
fi

# 7. 检查资源配额
echo -n "7. ResourceQuota configured: "
QUOTA=$(kubectl get resourcequota -n ${NAMESPACE} --no-headers | wc -l)
if [ "$QUOTA" -gt 0 ]; then
    echo "PASS"
else
    echo "FAIL"
    ERRORS=$((ERRORS+1))
fi

echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo "=== All checks passed! ==="
else
    echo "=== $ERRORS check(s) failed! ==="
    exit 1
fi
```

---

### 4. 故障注入与恢复演练

#### 4.1 故障注入场景

```bash
# 场景 1：Pod 被意外删除
echo "=== Scenario 1: Pod Deletion ==="
kubectl delete pod -l app=api-server -n sre-shop --grace-period=0 --force
# 预期：Deployment 自动重建 Pod
sleep 30
kubectl get pods -n sre-shop -l app=api-server

# 场景 2：节点故障模拟
echo "=== Scenario 2: Node Failure Simulation ==="
# 标记节点为不可调度
kubectl cordon <node-name>
# 驱逐节点上的 Pod
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data --force
# 预期：Pod 被调度到其他节点
sleep 60
kubectl get pods -n sre-shop -o wide

# 场景 3：ConfigMap 变更
echo "=== Scenario 3: ConfigMap Update ==="
kubectl edit configmap app-config -n sre-shop
# 修改 LOG_LEVEL 为 debug
# 预期：ConfigMap 更新，但 Pod 需要重启才能生效

# 场景 4：资源不足
echo "=== Scenario 4: Resource Exhaustion ==="
# 创建一个消耗大量资源的 Pod
kubectl run stress --image=progrium/stress -- \
  --cpu 4 --io 2 --vm 2 --vm-bytes 128M -t 600
# 预期：HPA 触发扩容，或者新 Pod 无法调度

# 场景 5：数据库连接失败
echo "=== Scenario 5: Database Connection Failure ==="
# 模拟 MySQL Pod 故障
kubectl delete pod mysql-0 -n sre-shop
# 预期：API Server 的 readinessProbe 失败，流量不再路由到它
# StatefulSet 自动重建 MySQL Pod
```

#### 4.2 恢复演练

```bash
# 恢复演练 1：回滚部署
echo "=== Recovery 1: Rollback Deployment ==="
kubectl rollout history deployment/api-server -n sre-shop
kubectl rollout undo deployment/api-server -n sre-shop
kubectl rollout status deployment/api-server -n sre-shop

# 恢复演练 2：从 PDB 保护中恢复
echo "=== Recovery 2: PDB Protected Maintenance ==="
kubectl uncordon <node-name>
kubectl get pods -n sre-shop -o wide

# 恢复演练 3：紧急扩容
echo "=== Recovery 3: Emergency Scaling ==="
kubectl scale deployment api-server -n sre-shop --replicas=10
kubectl get hpa api-server-hpa -n sre-shop

# 恢复演练 4：修复配置错误
echo "=== Recovery 4: Fix Configuration ==="
kubectl apply -f ${MANIFESTS_DIR}/05-configmap.yaml
kubectl rollout restart deployment/api-server -n sre-shop
kubectl rollout status deployment/api-server -n sre-shop
```

---

### 5. 理论测试（20 道题）

#### 题目 1：Pod 的 restartPolicy 有哪些？

<details>
<summary>查看答案</summary>

三种：
- `Always`（默认）：容器总是重启
- `OnFailure`：仅在容器退出码非 0 时重启
- `Never`：从不重启

</details>

#### 题目 2：Service 有哪四种类型？

<details>
<summary>查看答案</summary>

- `ClusterIP`（默认）：集群内部 IP，仅集群内可访问
- `NodePort`：在每个节点上开放一个端口
- `LoadBalancer`：使用云提供商的负载均衡器
- `ExternalName`：将 Service 映射到外部域名

</details>

#### 题目 3：Deployment 的滚动更新策略参数有哪些？

<details>
<summary>查看答案</summary>

- `maxSurge`：更新过程中最多比期望副本数多出的 Pod 数量（可以是绝对数或百分比）
- `maxUnavailable`：更新过程中最多不可用的 Pod 数量

两者配合控制更新速度和可用性。`maxUnavailable: 0` 配合 `maxSurge: 1` 实现零停机更新。

</details>

#### 题目 4：HPA 的扩缩容公式是什么？

<details>
<summary>查看答案</summary>

```
期望副本数 = ceil[当前副本数 × (当前指标值 / 目标指标值)]
```

多指标时，分别计算每个指标的期望副本数，取最大值。缩容有稳定窗口（默认 300 秒）防抖。

</details>

#### 题目 5：PDB 的 minAvailable 和 maxUnavailable 有什么区别？

<details>
<summary>查看答案</summary>

- `minAvailable`：最少可用 Pod 数（可以是绝对数或百分比）
- `maxUnavailable`：最多不可用 Pod 数（可以是绝对数或百分比）

两者二选一。例如 3 副本服务：`minAvailable: 2` 等价于 `maxUnavailable: 1`。

</details>

#### 题目 6：nodeAffinity 的 required 和 preferred 有什么区别？

<details>
<summary>查看答案</summary>

- `requiredDuringSchedulingIgnoredDuringExecution`：硬性约束，不满足则不调度
- `preferredDuringSchedulingIgnoredDuringExecution`：软性偏好，通过 weight 设置优先级

`IgnoredDuringExecution` 表示节点标签变更后，已运行的 Pod 不会被驱逐。

</details>

#### 题目 7：Taint 的三种 Effect 有什么区别？

<details>
<summary>查看答案</summary>

- `NoSchedule`：不允许新 Pod 调度，已运行的不受影响
- `PreferNoSchedule`：尽量不调度（软性排斥）
- `NoExecute`：不允许新 Pod + 驱逐已运行的不容忍 Pod

</details>

#### 题目 8：ConfigMap 和 Secret 的区别？

<details>
<summary>查看答案</summary>

- ConfigMap 存储非敏感配置，明文存储
- Secret 存储敏感信息，Base64 编码存储
- Secret 可以设置更严格的 RBAC 权限
- Secret 支持加密存储（需配置加密提供程序）

</details>

#### 题目 9：什么是 TopologySpreadConstraints？与 podAntiAffinity 的区别？

<details>
<summary>查看答案</summary>

TopologySpreadConstraints 控制 Pod 在拓扑域间的均匀分布，支持 maxSkew（最大偏差）。

区别：
- podAntiAffinity 是二元决策（是/否），不控制均匀分布
- TopologySpreadConstraints 支持 maxSkew，更精细
- TopologySpreadConstraints 支持 whenUnsatisfiable（DoNotSchedule/ScheduleAnyway）

</details>

#### 题目 10：ResourceQuota 和 LimitRange 的区别？

<details>
<summary>查看答案</summary>

- ResourceQuota：限制整个 namespace 的资源总量（CPU、内存、对象数量）
- LimitRange：为 namespace 中的 Pod/Container 设置默认资源限制和范围

ResourceQuota 是"总量控制"，LimitRange 是"个体约束"。

</details>

#### 题目 11：NetworkPolicy 的默认行为是什么？

<details>
<summary>查看答案</summary>

- 没有 NetworkPolicy 时：所有 Pod 可以互相通信
- 创建默认拒绝策略后：只有显式允许的流量才能通过
- NetworkPolicy 是 namespace 级别的
- 需要 CNI 插件支持（Calico、Cilium 等）

</details>

#### 题目 12：Helm values 文件的优先级顺序？

<details>
<summary>查看答案</summary>

从高到低：
1. `--set` 命令行参数
2. `--set-file` / `--set-string`
3. `-f` / `--values` 文件（后添加的优先级更高）
4. Chart 中的 `values.yaml`（默认值）

</details>

#### 题目 13：如何实现零停机部署？

<details>
<summary>查看答案</summary>

1. RollingUpdate 策略（maxUnavailable: 0）
2. PDB 确保最少可用 Pod 数
3. startupProbe 避免启动慢的 Pod 被杀
4. readinessProbe 确保流量只到就绪的 Pod
5. pre-upgrade Hook 执行数据库迁移

</details>

#### 题目 14：Cluster Autoscaler 什么时候会缩容节点？

<details>
<summary>查看答案</summary>

条件：
- 节点利用率低于阈值（默认 50%）
- 节点上的 Pod 可以迁移到其他节点
- 没有本地存储的 Pod（或有相关注解）
- Pod 的 PDB 允许中断
- 节点空闲超过阈值（默认 10 分钟）

</details>

#### 题目 15：KEDA 相比 HPA 的优势？

<details>
<summary>查看答案</summary>

- 支持 200+ 外部事件源
- 可以缩容到 0 个 Pod
- 支持 Cron 定时扩缩容
- 支持复合触发器
- 适用于事件驱动和异步任务场景

</details>

#### 题目 16：Helm Hook 有哪些类型？常见使用场景？

<details>
<summary>查看答案</summary>

类型：pre-install、post-install、pre-upgrade、post-upgrade、pre-rollback、post-rollback、pre-delete、post-delete、test

场景：
- pre-install/pre-upgrade：数据库迁移
- post-install：初始化数据
- test：健康检查

</details>

#### 题目 17：什么是 PriorityClass？preemptionPolicy 的作用？

<details>
<summary>查看答案</summary>

PriorityClass 定义 Pod 的优先级。高优先级 Pod 可以抢占低优先级 Pod。

`preemptionPolicy`：
- `PreemptLowerPriority`（默认）：可以抢占
- `Never`：不抢占，但可以被抢占

</details>

#### 题目 18：如何排查 Pod 处于 Pending 状态？

<details>
<summary>查看答案</summary>

```bash
kubectl describe pod <pod-name> | grep -A 20 "Events:"
```

常见原因：
- 资源不足（Insufficient cpu/memory）
- nodeSelector/nodeAffinity 不匹配
- Taint 不被容忍
- PVC 未绑定

</details>

#### 题目 19：Ingress 和 Service 的关系？

<details>
<summary>查看答案</summary>

- Service 提供集群内部的服务发现和负载均衡
- Ingress 提供集群外部的 HTTP/HTTPS 路由
- Ingress 通过 Service 将外部流量路由到 Pod
- Ingress 支持 TLS 终止、路径重写、限流等

</details>

#### 题目 20：生产环境部署的关键配置清单？

<details>
<summary>查看答案</summary>

1. 资源限制（requests/limits）
2. 健康检查（startup/liveness/readiness probe）
3. PDB（高可用保障）
4. HPA（自动扩缩容）
5. NetworkPolicy（网络隔离）
6. SecurityContext（安全加固）
7. Affinity（跨节点/可用区分布）
8. ResourceQuota（资源配额）
9. LimitRange（默认限制）
10. ConfigMap/Secret（配置管理）

</details>

---

### 6. 实战场景（5 个）

#### 场景 1：流量突增导致服务不可用

**描述**：某电商应用在大促期间流量突增 10 倍，API Server 响应超时，Pod 频繁 OOMKilled。

**排查与解决**：
```bash
# 1. 检查 HPA 状态
kubectl get hpa -n sre-shop
# 检查是否触发扩容

# 2. 检查资源使用
kubectl top pods -n sre-shop
# 检查 CPU/Memory 使用率

# 3. 检查 Pod 事件
kubectl get events -n sre-shop | grep OOMKilled

# 4. 紧急扩容
kubectl scale deployment api-server -n sre-shop --replicas=10

# 5. 调整资源限制
kubectl set resources deployment api-server -n sre-shop \
  --limits=cpu=2,memory=2Gi \
  --requests=cpu=1,memory=1Gi

# 6. 调整 HPA 配置
kubectl patch hpa api-server-hpa -n sre-shop \
  --patch '{"spec":{"maxReplicas":50}}'
```

#### 场景 2：节点维护导致服务中断

**描述**：需要对节点进行内核升级，但要求服务不中断。

**操作步骤**：
```bash
# 1. 检查 PDB
kubectl get pdb -n sre-shop

# 2. 标记节点不可调度
kubectl cordon node-3

# 3. 优雅驱逐 Pod（尊重 PDB）
kubectl drain node-3 \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --grace-period=60 \
  --timeout=300s

# 4. 执行维护
ssh node-3 "apt-get update && apt-get upgrade -y && reboot"

# 5. 等待节点恢复
kubectl wait --for=condition=Ready node/node-3 --timeout=600s

# 6. 恢复调度
kubectl uncordon node-3

# 7. 验证 Pod 分布
kubectl get pods -n sre-shop -o wide
```

#### 场景 3：数据库迁移导致 API 错误

**描述**：数据库 Schema 变更后，API Server 无法连接数据库。

**排查与解决**：
```bash
# 1. 检查 API Server 日志
kubectl logs -l app=api-server -n sre-shop --tail=100

# 2. 检查 MySQL 状态
kubectl exec -it mysql-0 -n sre-shop -- mysql -u root -p -e "SHOW DATABASES;"

# 3. 回滚 API Server 到兼容版本
kubectl rollout undo deployment/api-server -n sre-shop

# 4. 或者：重新执行迁移
kubectl apply -f ${MANIFESTS_DIR}/job-migrate.yaml

# 5. 验证
kubectl logs job/migrate -n sre-shop
```

#### 场景 4：网络策略阻断了服务通信

**描述**：部署新的 NetworkPolicy 后，API Server 无法访问 Redis。

**排查与解决**：
```bash
# 1. 检查 NetworkPolicy
kubectl get networkpolicy -n sre-shop

# 2. 临时删除 NetworkPolicy 测试
kubectl delete networkpolicy allow-api-to-redis -n sre-shop

# 3. 测试连通性
kubectl exec -it deploy/api-server -n sre-shop -- \
  redis-cli -h redis.sre-shop.svc.cluster.local -p 6379 ping

# 4. 修复 NetworkPolicy
cat << 'EOF' | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-redis
  namespace: sre-shop
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
        - podSelector:
            matchLabels:
              app: worker
      ports:
        - protocol: TCP
          port: 6379
EOF

# 5. 验证
kubectl exec -it deploy/api-server -n sre-shop -- \
  redis-cli -h redis.sre-shop.svc.cluster.local -p 6379 ping
```

#### 场景 5：Helm 部署失败需要回滚

**描述**：使用 Helm 升级应用后，新版本的 Pod 一直 CrashLoopBackOff。

**排查与解决**：
```bash
# 1. 查看 Release 状态
helm status sre-shop -n sre-shop

# 2. 查看历史版本
helm history sre-shop -n sre-shop

# 3. 查看失败的 Pod
kubectl get pods -n sre-shop | grep CrashLoop
kubectl logs <pod-name> -n sre-shop --previous

# 4. 对比版本差异
helm diff revision sre-shop 5 6 -n sre-shop

# 5. 回滚到上一个成功版本
helm rollback sre-shop 5 -n sre-shop

# 6. 验证回滚
kubectl rollout status deployment/api-server -n sre-shop
helm status sre-shop -n sre-shop

# 7. 根因分析
helm get values sre-shop -n sre-shop --revision 6
# 找出导致问题的配置变更
```

---

## 📚 深入阅读

- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [Kubernetes 最佳实践](https://learnk8s.io/)
- [Helm 官方文档](https://helm.sh/docs/)
- [CNCF 技术雷达](https://radar.cncf.io/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/overview/)
- [Production Kubernetes Book](https://www.oreilly.com/library/view/production-kubernetes/9781492092292/)

---

## ✅ 自检清单

- [ ] 能够独立设计和部署完整的微服务架构
- [ ] 能够配置 ConfigMap/Secret 管理应用配置
- [ ] 能够编写生产级的 Deployment（健康检查、资源限制、安全上下文）
- [ ] 能够配置 Service 和 Ingress 实现流量路由
- [ ] 能够使用 HPA 实现自动扩缩容
- [ ] 能够使用 PDB 保障服务高可用
- [ ] 能够使用 ResourceQuota 和 LimitRange 管理资源
- [ ] 能够使用 NetworkPolicy 实现网络隔离
- [ ] 能够使用 Helm 管理应用部署和回滚
- [ ] 能够进行故障注入和恢复演练
- [ ] 通过 20 道理论测试题
- [ ] 完成 5 个实战场景
