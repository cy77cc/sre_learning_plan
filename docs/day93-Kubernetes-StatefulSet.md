# Day 93: Kubernetes StatefulSet

> 📅 日期：2026-05-03
> 📖 学习主题：有状态应用管理、稳定网络标识、有序部署/扩缩/删除、持久存储、Headless Service
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 90 Kubernetes 架构, Day 91 Pod, Day 92 Deployment

---

## 🎯 学习目标

- 理解有状态应用与无状态应用的本质区别
- 掌握 StatefulSet 的三大特性（稳定网络标识、有序部署、持久存储）
- 理解 Headless Service 的工作原理
- 能使用 StatefulSet 部署 MySQL、Redis、ZooKeeper 等有状态应用
- 掌握 StatefulSet 的扩缩容和更新策略

---

## 📖 核心知识点

### 1. 有状态应用 vs 无状态应用

#### 1.1 核心区别

```
┌──────────────────────────────────────────────────────────────────┐
│              无状态应用 vs 有状态应用                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  无状态应用 (Stateless):                                         │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  特征:                                                   │     │
│  │  - 任何请求可以发送到任何副本                            │     │
│  │  - 副本之间完全等价，可互相替换                          │     │
│  │  - 不需要持久化存储                                      │     │
│  │  - 不依赖本地状态                                        │     │
│  │  - 扩缩容无顺序要求                                      │     │
│  │                                                          │     │
│  │  例子: Web 服务器、API 网关、无状态微服务                │     │
│  │  K8s 资源: Deployment                                    │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  有状态应用 (Stateful):                                          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  特征:                                                   │     │
│  │  - 每个实例有唯一标识                                    │     │
│  │  - 实例之间不是等价的（如主从关系）                      │     │
│  │  - 需要持久化存储（数据不能丢失）                        │     │
│  │  - 依赖本地状态（数据文件、配置等）                      │     │
│  │  - 扩缩容有顺序要求（如先启动主节点）                    │     │
│  │  - 需要稳定的网络标识（DNS 名称不变）                    │     │
│  │                                                          │     │
│  │  例子: MySQL、Redis、ZooKeeper、Elasticsearch、Kafka    │     │
│  │  K8s 资源: StatefulSet                                   │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  为什么 Deployment 不适合有状态应用？                             │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  Deployment 的 Pod:                                      │     │
│  │  - 名称是随机的 (web-app-7d4b8c9f6-xxxxx)              │     │
│  │  - 创建和删除没有顺序                                    │     │
│  │  - Pod 被调度到任意节点                                  │     │
│  │  - Volume 是临时的（Pod 重建后数据丢失）                │     │
│  │                                                          │     │
│  │  对于 MySQL 主从集群:                                    │     │
│  │  - 从节点需要知道主节点的地址                            │     │
│  │  - 每个节点需要自己的持久化数据                          │     │
│  │  - 启动顺序：先主后从                                    │     │
│  │  - 删除顺序：先从后主                                    │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 1.2 StatefulSet 三大核心特性

```
┌──────────────────────────────────────────────────────────────────┐
│                StatefulSet 三大特性                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  特性 1: 稳定的网络标识 (Stable Network Identity)               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  Pod 名称: <statefulset-name>-<ordinal>                 │     │
│  │  例: mysql-0, mysql-1, mysql-2                          │     │
│  │                                                          │     │
│  │  DNS 名称: <pod-name>.<headless-service>.ns.svc.cluster.local │
│  │  例: mysql-0.mysql.default.svc.cluster.local            │     │
│  │                                                          │     │
│  │  特点:                                                   │     │
│  │  - Pod 名称是确定性的（不是随机后缀）                    │     │
│  │  - Pod 重建后名称不变（DNS 可靠）                        │     │
│  │  - 每个 Pod 有独立的 DNS A 记录                          │     │
│  │  - 通过 Headless Service 实现                            │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  特性 2: 有序部署/扩缩/删除 (Ordered Deployment/Scaling)        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  创建顺序: 0 → 1 → 2 (前一个 Ready 后才创建下一个)     │     │
│  │  删除顺序: 2 → 1 → 0 (逆序删除)                        │     │
│  │  扩容顺序: 0 → 1 → 2 → ... (顺序创建新 Pod)           │     │
│  │  缩容顺序: N → N-1 → ... (逆序删除 Pod)                │     │
│  │                                                          │     │
│  │  好处:                                                   │     │
│  │  - 确保集群初始化顺序正确（如先启动主节点）              │     │
│  │  - 缩容时先删除从节点，保护数据完整性                    │     │
│  │  - 滚动更新时有序替换                                    │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  特性 3: 持久存储 (Stable Persistent Storage)                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  每个 Pod 有独立的 PVC，绑定到独立的 PV                  │     │
│  │  Pod 重建后自动挂载原来的 PVC（数据不丢失）              │     │
│  │                                                          │     │
│  │  mysql-0 ──> PVC data-mysql-0 ──> PV-0 (zone-a)        │     │
│  │  mysql-1 ──> PVC data-mysql-1 ──> PV-1 (zone-b)        │     │
│  │  mysql-2 ──> PVC data-mysql-2 ──> PV-2 (zone-c)        │     │
│  │                                                          │     │
│  │  即使 mysql-0 从 node-1 迁移到 node-2，                 │     │
│  │  它仍然挂载 PV-0 的数据                                  │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 2. Headless Service

#### 2.1 什么是 Headless Service

Headless Service 是一种特殊的 Service，ClusterIP 为 None，不进行负载均衡。每个 Pod 获得独立的 DNS A 记录。

```
┌──────────────────────────────────────────────────────────────────┐
│           普通 Service vs Headless Service                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  普通 Service (ClusterIP):                                       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  Service: mysql-service (ClusterIP: 10.96.0.100)        │     │
│  │  DNS: mysql-service → 10.96.0.100 (单个 IP)             │     │
│  │  流量: 10.96.0.100 → kube-proxy → 随机选择一个 Pod      │     │
│  │                                                          │     │
│  │  客户端只知道 Service IP，不知道具体 Pod IP              │     │
│  │  适合: 无状态应用（请求发给任意副本都行）                │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Headless Service (ClusterIP: None):                             │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  Service: mysql-headless (ClusterIP: None)              │     │
│  │  DNS 查询:                                               │     │
│  │    mysql-headless → [10.244.1.5, 10.244.2.8, 10.244.3.2]│    │
│  │    mysql-0.mysql-headless → 10.244.1.5                  │     │
│  │    mysql-1.mysql-headless → 10.244.2.8                  │     │
│  │    mysql-2.mysql-headless → 10.244.3.2                  │     │
│  │                                                          │     │
│  │  客户端可以直接访问每个 Pod 的独立 DNS 名称              │     │
│  │  适合: 有状态应用（需要知道具体是哪个实例）              │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```yaml
# headless-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql-headless
  labels:
    app: mysql
spec:
  clusterIP: None  # 关键：设为 None 表示 Headless
  selector:
    app: mysql
  ports:
  - port: 3306
    targetPort: 3306
    name: mysql
```

#### 2.2 StatefulSet 的 DNS 记录

```
┌──────────────────────────────────────────────────────────────────┐
│                StatefulSet DNS 记录体系                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  StatefulSet: mysql                                              │
│  Headless Service: mysql-headless                                │
│  Namespace: default                                              │
│                                                                  │
│  DNS 记录:                                                       │
│                                                                  │
│  A 记录 (每个 Pod):                                              │
│  mysql-0.mysql-headless.default.svc.cluster.local → 10.244.1.5  │
│  mysql-1.mysql-headless.default.svc.cluster.local → 10.244.2.8  │
│  mysql-2.mysql-headless.default.svc.cluster.local → 10.244.3.2  │
│                                                                  │
│  SRV 记录 (Headless Service):                                    │
│  _mysql._tcp.mysql-headless.default.svc.cluster.local            │
│  → mysql-0.mysql-headless.default.svc.cluster.local:3306        │
│  → mysql-1.mysql-headless.default.svc.cluster.local:3306        │
│  → mysql-2.mysql-headless.default.svc.cluster.local:3306        │
│                                                                  │
│  Pod 重建时:                                                     │
│  - Pod 名称不变: mysql-0                                        │
│  - DNS 记录更新: mysql-0.mysql-headless → 新 IP                 │
│  - PVC 不变: data-mysql-0 绑定到同一个 PV                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 3. StatefulSet 完整示例

#### 3.1 基础 StatefulSet

```yaml
# statefulset-basic.yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-headless
  labels:
    app: nginx
spec:
  clusterIP: None
  selector:
    app: nginx
  ports:
  - port: 80
    targetPort: 80
    name: web
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: nginx-headless  # 必须指定 Headless Service
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25-alpine
        ports:
        - containerPort: 80
          name: web
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "500m"
            memory: "256Mi"
        volumeMounts:
        - name: www-data
          mountPath: /usr/share/nginx/html
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
  # VolumeClaimTemplates: 每个 Pod 自动创建独立的 PVC
  volumeClaimTemplates:
  - metadata:
      name: www-data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: standard
      resources:
        requests:
          storage: 1Gi
```

```bash
# 创建 StatefulSet
kubectl apply -f statefulset-basic.yaml

# 观察 Pod 创建顺序（0 → 1 → 2）
kubectl get pods -l app=nginx -w

# 查看 Pod 名称（确定性名称，不是随机后缀）
kubectl get pods -l app=nginx
# NAME      READY   STATUS    AGE
# web-0     1/1     Running   2m
# web-1     1/1     Running   1m
# web-2     1/1     Running   30s

# 查看 PVC（每个 Pod 有独立的 PVC）
kubectl get pvc
# NAME              STATUS   VOLUME   CAPACITY   STORAGECLASS
# www-data-web-0    Bound    pv-xxx   1Gi        standard
# www-data-web-1    Bound    pv-xxx   1Gi        standard
# www-data-web-2    Bound    pv-xxx   1Gi        standard

# 测试 DNS 解析
kubectl run dns-test --image=busybox:1.36 -it --rm -- nslookup web-0.nginx-headless
kubectl run dns-test --image=busybox:1.36 -it --rm -- nslookup nginx-headless

# 测试缩容（删除顺序：2 → 1 → 0）
kubectl scale statefulset web --replicas=1
kubectl get pods -l app=nginx -w  # 观察 web-2 先被删除

# 注意：缩容不会自动删除 PVC（防止数据丢失）
kubectl get pvc
# 仍然有 3 个 PVC，即使只有 1 个 Pod
```

#### 3.2 StatefulSet 更新策略

```yaml
spec:
  updateStrategy:
    type: RollingUpdate     # RollingUpdate 或 OnDelete
    rollingUpdate:
      partition: 0          # 分区更新：只更新 ordinal >= partition 的 Pod
```

```
┌──────────────────────────────────────────────────────────────────┐
│                StatefulSet 更新策略                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  策略 1: RollingUpdate (默认)                                    │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  按逆序更新 Pod: N → N-1 → ... → 1 → 0                │     │
│  │                                                          │     │
│  │  partition 参数:                                         │     │
│  │  - partition: 0 (默认): 更新所有 Pod                    │     │
│  │  - partition: 3: 只更新 ordinal >= 3 的 Pod             │     │
│  │    (即 mysql-3, mysql-4, ...)                           │     │
│  │    ordinal < 3 的 Pod (mysql-0, mysql-1, mysql-2)       │     │
│  │    不会被更新                                            │     │
│  │                                                          │     │
│  │  用途: 金丝雀发布（先更新一部分 Pod 验证）               │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  策略 2: OnDelete                                               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                                                          │     │
│  │  只有手动删除 Pod 后才会创建新版本的 Pod                 │     │
│  │  不会自动更新                                            │     │
│  │                                                          │     │
│  │  用途: 需要完全控制更新时机的场景                        │     │
│  │                                                          │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```bash
# 分区更新（金丝雀发布）
# 假设有 5 个 Pod: mysql-0, mysql-1, mysql-2, mysql-3, mysql-4

# 1. 设置 partition=4，只更新 mysql-4
kubectl patch statefulset mysql -p '{"spec":{"updateStrategy":{"rollingUpdate":{"partition":4}}}}'

# 2. 更新镜像
kubectl set image statefulset/mysql mysql=mysql:8.0.35

# 3. 只有 mysql-4 会被更新
kubectl get pods -l app=mysql -w

# 4. 验证 mysql-4 正常后，设置 partition=0 更新所有 Pod
kubectl patch statefulset mysql -p '{"spec":{"updateStrategy":{"rollingUpdate":{"partition":0}}}}'

# 5. 观察剩余 Pod 按逆序更新: mysql-3 → mysql-2 → mysql-1 → mysql-0
```

---

### 4. 实战：部署 MySQL 主从集群

#### 4.1 架构设计

```
┌──────────────────────────────────────────────────────────────────┐
│                MySQL 主从集群架构                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   StatefulSet: mysql (replicas: 3)                               │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐    │
│   │                                                          │    │
│   │  mysql-0 (Master)                                        │    │
│   │  ├── 写操作 (Read-Write)                                │    │
│   │  ├── 数据目录: /var/lib/mysql                            │    │
│   │  ├── PVC: data-mysql-0 → PV-0                           │    │
│   │  └── DNS: mysql-0.mysql.default.svc.cluster.local       │    │
│   │                                                          │    │
│   │  mysql-1 (Slave)                                         │    │
│   │  ├── 只读 (Read-Only)                                   │    │
│   │  ├── 复制自 mysql-0                                     │    │
│   │  ├── PVC: data-mysql-1 → PV-1                           │    │
│   │  └── DNS: mysql-1.mysql.default.svc.cluster.local       │    │
│   │                                                          │    │
│   │  mysql-2 (Slave)                                         │    │
│   │  ├── 只读 (Read-Only)                                   │    │
│   │  ├── 复制自 mysql-0                                     │    │
│   │  ├── PVC: data-mysql-2 → PV-2                           │    │
│   │  └── DNS: mysql-2.mysql.default.svc.cluster.local       │    │
│   │                                                          │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
│   Service: mysql-read (Headless)                                 │
│   └── 所有 Pod 的读操作                                         │
│                                                                  │
│   Service: mysql-write (ClusterIP)                               │
│   └── 只指向 mysql-0 (Master)                                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 4.2 MySQL StatefulSet 完整配置

```yaml
# mysql-statefulset.yaml
# ConfigMap: MySQL 配置
apiVersion: v1
kind: ConfigMap
metadata:
  name: mysql-config
data:
  primary.cnf: |
    [mysqld]
    log-bin=mysql-bin
    server-id=1
    binlog-format=ROW
    gtid-mode=ON
    enforce-gtid-consistency=ON
    log-slave-updates=ON

  replica.cnf: |
    [mysqld]
    super-read-only
    server-id=2
    gtid-mode=ON
    enforce-gtid-consistency=ON
    log-slave-updates=ON
---
# Secret: MySQL Root 密码
apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
type: Opaque
data:
  MYSQL_ROOT_PASSWORD: cm9vdHBhc3N3b3Jk  # base64("rootpassword")
---
# Headless Service
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
# Write Service (只指向 Master)
apiVersion: v1
kind: Service
metadata:
  name: mysql-write
  labels:
    app: mysql
    role: primary
spec:
  selector:
    app: mysql
    statefulset.kubernetes.io/pod-name: mysql-0
  ports:
  - port: 3306
    targetPort: 3306
---
# Read Service (指向所有 Pod)
apiVersion: v1
kind: Service
metadata:
  name: mysql-read
  labels:
    app: mysql
    role: replica
spec:
  selector:
    app: mysql
  ports:
  - port: 3306
    targetPort: 3306
---
# StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      initContainers:
      # 初始化配置：根据 ordinal 决定是主还是从
      - name: init-mysql
        image: mysql:8.0
        command:
        - bash
        - -c
        - |
          set -ex
          # 从 Pod 名称中提取 ordinal
          ordinal=$(hostname | grep -o '\-[-]*[0-9]*$' | sed 's/-//')

          if [[ $ordinal -eq 0 ]]; then
            # mysql-0 作为 Primary
            cp /mnt/config-map/primary.cnf /mnt/conf.d/server.cnf
          else
            # 其他作为 Replica
            cp /mnt/config-map/replica.cnf /mnt/conf.d/server.cnf
            # 设置不同的 server-id
            sed -i "s/server-id=2/server-id=$((100 + $ordinal))/" /mnt/conf.d/server.cnf
          fi
        volumeMounts:
        - name: conf
          mountPath: /mnt/conf.d
        - name: config-map
          mountPath: /mnt/config-map

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
              key: MYSQL_ROOT_PASSWORD
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
        volumeMounts:
        - name: data
          mountPath: /var/lib/mysql
          subPath: mysql
        - name: conf
          mountPath: /etc/mysql/conf.d
        livenessProbe:
          exec:
            command: ["mysqladmin", "ping", "-uroot", "-p$(MYSQL_ROOT_PASSWORD)"]
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          exec:
            command: ["mysql", "-uroot", "-p$(MYSQL_ROOT_PASSWORD)", "-e", "SELECT 1"]
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3

      volumes:
      - name: conf
        emptyDir: {}
      - name: config-map
        configMap:
          name: mysql-config

  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: standard
      resources:
        requests:
          storage: 10Gi
```

```bash
# 部署 MySQL 集群
kubectl apply -f mysql-statefulset.yaml

# 观察 Pod 创建顺序
kubectl get pods -l app=mysql -w

# 验证主从状态
kubectl exec mysql-0 -- mysql -uroot -prootpassword -e "SHOW MASTER STATUS\G"
kubectl exec mysql-1 -- mysql -uroot -prootpassword -e "SHOW SLAVE STATUS\G"

# 测试写操作（通过 Write Service）
kubectl run mysql-client --image=mysql:8.0 -it --rm -- \
  mysql -h mysql-write -uroot -prootpassword -e "CREATE DATABASE test; USE test; CREATE TABLE t1(id INT); INSERT INTO t1 VALUES(1);"

# 测试读操作（通过 Read Service）
kubectl run mysql-client --image=mysql:8.0 -it --rm -- \
  mysql -h mysql-read -uroot -prootpassword -e "SELECT * FROM test.t1;"
```

---

### 5. 实战：部署 Redis Sentinel 集群

#### 5.1 架构设计

```
┌──────────────────────────────────────────────────────────────────┐
│                Redis Sentinel 集群架构                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   StatefulSet: redis (replicas: 3)                               │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐    │
│   │                                                          │    │
│   │  redis-0 (Master)                                        │    │
│   │  ├── 可读可写                                            │    │
│   │  ├── 数据目录: /data                                     │    │
│   │  └── PVC: data-redis-0                                   │    │
│   │                                                          │    │
│   │  redis-1 (Replica)                                       │    │
│   │  ├── 只读                                                │    │
│   │  ├── 复制自 redis-0                                      │    │
│   │  └── PVC: data-redis-1                                   │    │
│   │                                                          │    │
│   │  redis-2 (Replica)                                       │    │
│   │  ├── 只读                                                │    │
│   │  ├── 复制自 redis-0                                      │    │
│   │  └── PVC: data-redis-2                                   │    │
│   │                                                          │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
│   StatefulSet: redis-sentinel (replicas: 3)                      │
│   ┌────────────────────────────────────────────────────────┐    │
│   │                                                          │    │
│   │  sentinel-0, sentinel-1, sentinel-2                      │    │
│   │  ├── 监控 Redis 主从状态                                 │    │
│   │  ├── 自动故障转移 (Failover)                             │    │
│   │  └── 客户端通过 Sentinel 发现 Master                     │    │
│   │                                                          │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
│   自动故障转移流程:                                               │
│   1. Sentinel 检测到 redis-0 不可达                              │
│   2. Sentinel 投票选举新 Master (如 redis-1)                     │
│   3. redis-1 提升为 Master                                      │
│   4. redis-2 重新配置复制自 redis-1                              │
│   5. 客户端通过 Sentinel 获取新 Master 地址                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```yaml
# redis-statefulset.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
data:
  redis.conf: |
    appendonly yes
    appendfsync everysec
    save 900 1
    save 300 10
    save 60 10000
    maxmemory 256mb
    maxmemory-policy allkeys-lru

  sentinel.conf: |
    sentinel monitor mymaster redis-0.redis-headless 6379 2
    sentinel down-after-milliseconds mymaster 5000
    sentinel failover-timeout mymaster 60000
    sentinel parallel-syncs mymaster 1
---
apiVersion: v1
kind: Service
metadata:
  name: redis-headless
spec:
  clusterIP: None
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
spec:
  serviceName: redis-headless
  replicas: 3
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      initContainers:
      - name: init-redis
        image: redis:7.0
        command:
        - bash
        - -c
        - |
          set -ex
          ordinal=$(hostname | grep -o '\-[-]*[0-9]*$' | sed 's/-//')

          # 复制基础配置
          cp /mnt/config-map/redis.conf /data/redis.conf

          if [[ $ordinal -eq 0 ]]; then
            # redis-0 作为 Master，不需要 replicaof
            echo "# Master node" >> /data/redis.conf
          else
            # 其他节点作为 Replica
            echo "replicaof redis-0.redis-headless 6379" >> /data/redis.conf
            echo "replica-read-only yes" >> /data/redis.conf
          fi
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config-map
          mountPath: /mnt/config-map

      containers:
      - name: redis
        image: redis:7.0
        command: ["redis-server", "/data/redis.conf"]
        ports:
        - containerPort: 6379
          name: redis
        resources:
          requests:
            cpu: "100m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        volumeMounts:
        - name: data
          mountPath: /data
        livenessProbe:
          exec:
            command: ["redis-cli", "ping"]
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          exec:
            command: ["redis-cli", "ping"]
          initialDelaySeconds: 5
          periodSeconds: 5

      volumes:
      - name: config-map
        configMap:
          name: redis-config

  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: standard
      resources:
        requests:
          storage: 5Gi
```

```bash
# 部署 Redis 集群
kubectl apply -f redis-statefulset.yaml

# 验证主从状态
kubectl exec redis-0 -- redis-cli info replication | grep role
# role:master
kubectl exec redis-1 -- redis-cli info replication | grep role
# role:slave

# 测试数据同步
kubectl exec redis-0 -- redis-cli set test-key "hello"
kubectl exec redis-1 -- redis-cli get test-key
# 输出: "hello"

# 测试故障转移（删除 Master）
kubectl delete pod redis-0
# 观察 redis-1 或 redis-2 是否被提升为新 Master
kubectl exec redis-1 -- redis-cli info replication | grep role
```

---

### 6. 实战：部署 ZooKeeper 集群

#### 6.1 ZooKeeper StatefulSet

```yaml
# zookeeper-statefulset.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: zk-config
data:
  zoo.cfg: |
    tickTime=2000
    initLimit=10
    syncLimit=5
    dataDir=/data
    dataLogDir=/datalog
    clientPort=2181
    autopurge.snapRetainCount=3
    autopurge.purgeInterval=1
    server.1=zk-0.zk-headless:2888:3888
    server.2=zk-1.zk-headless:2888:3888
    server.3=zk-2.zk-headless:2888:3888
---
apiVersion: v1
kind: Service
metadata:
  name: zk-headless
spec:
  clusterIP: None
  selector:
    app: zk
  ports:
  - port: 2181
    targetPort: 2181
    name: client
  - port: 2888
    targetPort: 2888
    name: peer
  - port: 3888
    targetPort: 3888
    name: election
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: zk
spec:
  serviceName: zk-headless
  replicas: 3
  selector:
    matchLabels:
      app: zk
  template:
    metadata:
      labels:
        app: zk
    spec:
      initContainers:
      - name: init-zk
        image: zookeeper:3.9
        command:
        - bash
        - -c
        - |
          set -ex
          # 提取 ordinal
          ordinal=$(hostname | grep -o '\-[-]*[0-9]*$' | sed 's/-//')
          server_id=$((ordinal + 1))

          # 写入 myid 文件
          echo $server_id > /data/myid

          # 复制配置
          cp /mnt/config-map/zoo.cfg /data/zoo.cfg
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config-map
          mountPath: /mnt/config-map

      containers:
      - name: zk
        image: zookeeper:3.9
        ports:
        - containerPort: 2181
          name: client
        - containerPort: 2888
          name: peer
        - containerPort: 3888
          name: election
        env:
        - name: ZOO_DATA_DIR
          value: /data
        - name: ZOO_DATA_LOG_DIR
          value: /datalog
        resources:
          requests:
            cpu: "250m"
            memory: "512Mi"
          limits:
            cpu: "500m"
            memory: "1Gi"
        volumeMounts:
        - name: data
          mountPath: /data
        - name: datalog
          mountPath: /datalog
        livenessProbe:
          exec:
            command: ["zkServer.sh", "status"]
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command: ["zkCli.sh", "ls", "/"]
          initialDelaySeconds: 15
          periodSeconds: 10

      volumes:
      - name: config-map
        configMap:
          name: zk-config

  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: standard
      resources:
        requests:
          storage: 10Gi
  - metadata:
      name: datalog
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: standard
      resources:
        requests:
          storage: 10Gi
```

```bash
# 部署 ZooKeeper 集群
kubectl apply -f zookeeper-statefulset.yaml

# 验证集群状态
for i in 0 1 2; do
  echo "=== zk-$i ==="
  kubectl exec zk-$i -- zkServer.sh status
done

# 测试集群
kubectl exec -it zk-0 -- zkCli.sh
# 在 zkCli 中:
# create /test "hello"
# get /test
# quit

# 从其他节点验证数据同步
kubectl exec -it zk-1 -- zkCli.sh
# get /test
```

---

### 7. StatefulSet vs Deployment 对比

```
┌──────────────────────────────────────────────────────────────────┐
│                StatefulSet vs Deployment 对比                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  特性                  Deployment          StatefulSet            │
│  ─────────────         ──────────          ────────────          │
│  Pod 名称              随机后缀            确定性 (ordinal)       │
│  创建顺序              无序                有序 (0→1→2)          │
│  删除顺序              无序                逆序 (2→1→0)          │
│  扩缩容顺序            无序                有序                   │
│  更新顺序              无序                逆序 (N→0)            │
│  网络标识              不稳定              稳定 DNS               │
│  持久存储              无（需手动配置）    VolumeClaimTemplates   │
│  Headless Service      不需要              必须                   │
│  适用场景              无状态应用          有状态应用             │
│  典型应用              Web/API             DB/Cache/MQ            │
│                                                                  │
│  选择依据:                                                        │
│  - 应用实例之间是否等价？ → Deployment                           │
│  - 需要稳定网络标识？ → StatefulSet                              │
│  - 需要持久化存储且每个实例独立？ → StatefulSet                  │
│  - 扩缩容有顺序要求？ → StatefulSet                              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### 8. SRE 实战案例

#### 8.1 StatefulSet 扩缩容注意事项

```
┌──────────────────────────────────────────────────────────────────┐
│                StatefulSet 扩缩容注意事项                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  扩容:                                                           │
│  - 新 Pod 按顺序创建 (N, N+1, ...)                              │
│  - 新 Pod 需要初始化（可能需要加入集群、数据同步）               │
│  - 扩容不会自动触发数据重新分片                                  │
│                                                                  │
│  缩容:                                                           │
│  - Pod 按逆序删除 (N-1, N-2, ...)                               │
│  - PVC 不会自动删除（防止数据丢失）                              │
│  - 缩容后需要手动处理数据迁移/重新分片                           │
│                                                                  │
│  SRE 操作清单:                                                    │
│  1. 缩容前确认数据已迁移到其他节点                               │
│  2. 缩容后确认集群状态正常（如 Redis cluster nodes）            │
│  3. 确认不需要恢复后，手动删除多余的 PVC                        │
│  4. 记录操作日志                                                 │
│                                                                  │
│  命令:                                                            │
│  # 扩容                                                         │
│  kubectl scale statefulset mysql --replicas=5                   │
│                                                                  │
│  # 缩容                                                         │
│  kubectl scale statefulset mysql --replicas=3                   │
│                                                                  │
│  # 手动删除多余的 PVC（缩容后）                                  │
│  kubectl delete pvc data-mysql-4 data-mysql-3                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 8.2 StatefulSet 数据恢复

```bash
# 场景: mysql-0 的 PV 数据损坏，需要从备份恢复

# 1. 暂停 StatefulSet 更新
kubectl rollout pause statefulset/mysql

# 2. 删除损坏的 Pod（保留 PVC）
kubectl delete pod mysql-0

# 3. 从备份恢复数据到 PVC
# (具体步骤取决于备份方式：mysqldump, xtrabackup, etc.)

# 4. 恢复 StatefulSet
kubectl rollout resume statefulset/mysql

# 5. 验证数据完整性
kubectl exec mysql-0 -- mysql -uroot -prootpassword -e "CHECK TABLE test.t1"
```

---

## 💻 实战练习

### 练习 1：StatefulSet 基础操作

**目标：** 掌握 StatefulSet 的创建、扩缩容、更新

```bash
# 1. 创建一个简单的 StatefulSet
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: nginx-sts-headless
spec:
  clusterIP: None
  selector:
    app: nginx-sts
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nginx-sts
spec:
  serviceName: nginx-sts-headless
  replicas: 3
  selector:
    matchLabels:
      app: nginx-sts
  template:
    metadata:
      labels:
        app: nginx-sts
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
          storage: 100Mi
EOF

# 2. 观察有序创建
kubectl get pods -l app=nginx-sts -w
# 确认 0 → 1 → 2 的创建顺序

# 3. 查看 PVC
kubectl get pvc -l app=nginx-sts

# 4. 测试 DNS
kubectl run dns-test --image=busybox:1.36 -it --rm -- sh -c \
  "nslookup nginx-sts-0.nginx-sts-headless && nslookup nginx-sts-headless"

# 5. 写入数据
kubectl exec nginx-sts-0 -- sh -c 'echo "Hello from nginx-sts-0" > /usr/share/nginx/html/index.html'

# 6. 测试缩容（观察删除顺序 2 → 1 → 0）
kubectl scale statefulset nginx-sts --replicas=1
kubectl get pods -l app=nginx-sts -w

# 7. 确认 PVC 仍然存在
kubectl get pvc -l app=nginx-sts

# 8. 扩容回来
kubectl scale statefulset nginx-sts --replicas=3

# 9. 验证数据持久性
kubectl exec nginx-sts-0 -- cat /usr/share/nginx/html/index.html

# 10. 清理
kubectl delete statefulset nginx-sts
kubectl delete svc nginx-sts-headless
kubectl delete pvc -l app=nginx-sts
```

### 练习 2：Headless Service 与 DNS

**目标：** 深入理解 Headless Service 的 DNS 解析

```bash
# 1. 使用上面创建的 StatefulSet

# 2. 创建一个测试 Pod 进行 DNS 查询
kubectl run dns-debug --image=busybox:1.36 -it --rm -- sh

# 在 Pod 内执行:
# 查询 Headless Service（返回所有 Pod IP）
nslookup nginx-sts-headless

# 查询单个 Pod（返回该 Pod 的 IP）
nslookup nginx-sts-0.nginx-sts-headless
nslookup nginx-sts-1.nginx-sts-headless
nslookup nginx-sts-2.nginx-sts-headless

# 查询完整域名
nslookup nginx-sts-0.nginx-sts-headless.default.svc.cluster.local

# 3. 对比普通 Service 的 DNS
kubectl create svc clusterip nginx-normal --tcp=80:80
kubectl run dns-test2 --image=busybox:1.36 -it --rm -- sh
# nslookup nginx-normal  # 只返回一个 ClusterIP
```

### 练习 3：StatefulSet 更新策略

**目标：** 掌握分区更新（金丝雀发布）

```bash
# 1. 使用上面的 StatefulSet

# 2. 设置 partition=2，只更新 ordinal >= 2 的 Pod
kubectl patch statefulset nginx-sts -p '{"spec":{"updateStrategy":{"rollingUpdate":{"partition":2}}}}'

# 3. 更新镜像
kubectl set image statefulset/nginx-sts nginx=nginx:1.26-alpine

# 4. 观察只有 nginx-sts-2 被更新
kubectl get pods -l app=nginx-sts -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].image}{"\n"}{end}'

# 5. 验证 nginx-sts-0 和 nginx-sts-1 仍然是旧版本

# 6. 设置 partition=0 更新所有 Pod
kubectl patch statefulset nginx-sts -p '{"spec":{"updateStrategy":{"rollingUpdate":{"partition":0}}}}'

# 7. 观察剩余 Pod 按逆序更新
kubectl get pods -l app=nginx-sts -w

# 8. 清理
kubectl delete statefulset nginx-sts
kubectl delete svc nginx-sts-headless
kubectl delete pvc -l app=nginx-sts
```

---

## 🎯 面试题精选

### 1. StatefulSet 和 Deployment 有什么区别？什么场景下使用 StatefulSet？

**参考答案：**

| 特性 | Deployment | StatefulSet |
|------|-----------|-------------|
| Pod 名称 | 随机后缀 | 确定性 (ordinal) |
| 创建/删除顺序 | 无序 | 有序/逆序 |
| 网络标识 | 不稳定 | 稳定 DNS |
| 持久存储 | 不支持 | VolumeClaimTemplates |
| 适用场景 | 无状态应用 | 有状态应用 |

使用 StatefulSet 的场景：
- 数据库（MySQL、PostgreSQL、MongoDB）
- 缓存（Redis Cluster）
- 消息队列（Kafka、RabbitMQ）
- 分布式协调服务（ZooKeeper、etcd）
- 搜索引擎（Elasticsearch）

### 2. StatefulSet 的 Headless Service 是什么？为什么需要它？

**参考答案：**

Headless Service 是 ClusterIP 为 None 的 Service，不提供负载均衡，而是为每个 Pod 创建独立的 DNS A 记录。

需要的原因：
1. **稳定网络标识**：Pod 重建后 IP 会变，但 DNS 名称不变，其他 Pod 可以通过 DNS 名称访问
2. **直接访问 Pod**：有状态应用通常需要访问特定实例（如访问 Master 节点），不能通过负载均衡
3. **集群内部通信**：集群节点之间需要直接通信（如 ZooKeeper 的选举），不能经过代理

### 3. StatefulSet 缩容时 PVC 为什么不会自动删除？

**参考答案：**

StatefulSet 缩容时 PVC 不会自动删除，这是**有意设计**的，原因：
1. **数据安全**：有状态应用的数据是宝贵的，自动删除可能导致数据丢失
2. **扩容恢复**：如果扩容回来，Pod 可以自动挂载原来的 PVC，恢复数据
3. **手动决策**：数据删除应该是人工决策，不应该由控制器自动执行

SRE 最佳实践：
- 缩容前确认数据已迁移到其他节点
- 确认不需要恢复后，手动删除多余的 PVC
- 建立 PVC 清理的自动化流程

### 4. StatefulSet 的更新策略 partition 有什么用？

**参考答案：**

partition 参数用于实现**分区更新**，只更新 ordinal >= partition 的 Pod。

用法：
- `partition: 0`（默认）：更新所有 Pod
- `partition: N`：只更新 ordinal >= N 的 Pod

应用场景：
- **金丝雀发布**：设置 partition=N-1，只更新最后一个 Pod，验证无问题后再设置 partition=0 全量更新
- **灰度发布**：逐步减小 partition 值，分批更新 Pod
- **回滚**：增大 partition 值，只回滚部分 Pod

### 5. 如何在 StatefulSet 中实现 MySQL 主从复制？

**参考答案：**

实现步骤：
1. 使用 Init Container 根据 ordinal 决定角色（0 为主，其他为从）
2. 为不同角色生成不同的 MySQL 配置文件（Primary 配置 binlog，Replica 配置 replicaof）
3. 使用 Headless Service 提供稳定的 DNS 名称
4. 创建两个 Service：Write Service（指向主节点）和 Read Service（指向所有节点）
5. 使用 VolumeClaimTemplates 为每个 Pod 提供独立的持久存储

### 6. StatefulSet 的有序性保证在什么情况下会被打破？

**参考答案：**

有序性保证会在以下情况下被打破：
1. **节点故障**：如果运行 mysql-0 的节点宕机，K8s 可能先在其他节点创建 mysql-0，同时 mysql-1 仍在运行
2. **强制删除**：使用 `kubectl delete pod --force --grace-period=0` 强制删除
3. **网络分区**：Pod 与 API Server 失去连接，可能出现多个同名 Pod 的脑裂情况

应对措施：
- 使用 PodDisruptionBudget 保护关键 Pod
- 避免使用 force 删除
- 配置适当的 eviction 策略

### 7. 为什么 StatefulSet 需要单独的 Headless Service 和普通 Service？

**参考答案：**

两者各有用途：
- **Headless Service**：为 StatefulSet 提供稳定的 DNS 记录，让 Pod 之间可以通过 DNS 名称直接通信
- **普通 Service**：提供负载均衡，让外部客户端可以通过 Service IP 访问集群

例如 MySQL 场景：
- Headless Service：mysql-0.mysql-headless（主从复制使用）
- Write Service：mysql-write（应用写操作，指向 Master）
- Read Service：mysql-read（应用读操作，负载均衡到所有节点）

### 8. 如何处理 StatefulSet 的滚动更新失败？

**参考答案：**

StatefulSet 滚动更新失败时：
1. **查看更新状态**：`kubectl rollout status statefulset/<name>`
2. **查看失败 Pod**：`kubectl get pods -l app=<name>` 找到失败的 Pod
3. **查看原因**：`kubectl describe pod <pod-name>` 查看 Events
4. **暂停更新**：`kubectl rollout pause statefulset/<name>` 防止更多 Pod 更新
5. **修复或回滚**：
   - 如果是配置问题，修复后 `kubectl rollout resume statefulset/<name>`
   - 如果需要回滚，使用 partition 只回滚已更新的 Pod

### 9. StatefulSet 的 volumeClaimTemplates 和直接在 Pod 中定义 PVC 有什么区别？

**参考答案：**

| 特性 | volumeClaimTemplates | 直接定义 PVC |
|------|---------------------|-------------|
| PVC 创建 | 自动为每个 Pod 创建 | 需要手动创建 |
| PVC 命名 | `<name>-<sts-name>-<ordinal>` | 手动指定 |
| 绑定关系 | 自动绑定到对应 Pod | 需要手动关联 |
| 缩容行为 | 保留 PVC | PVC 不受影响 |
| 适用场景 | StatefulSet | Deployment 等 |

volumeClaimTemplates 的好处是自动化程度高，每个 Pod 自动获得独立的 PVC，无需手动管理。

### 10. 在生产环境中部署有状态应用（如数据库）到 K8s 是否推荐？

**参考答案：**

这取决于具体情况：

**推荐使用 K8s 的场景：**
- 团队熟悉 K8s 运维
- 需要统一的部署和管理流程
- 应用支持云原生架构（如 Operator）
- 使用成熟的 Operator（如 MySQL Operator、Redis Operator）

**不推荐的场景：**
- 超大规模数据库（TB 级别）
- 对性能要求极高（网络延迟敏感）
- 团队 K8s 经验不足
- 没有可靠的持久化存储方案

**SRE 建议：**
- 优先考虑云厂商托管数据库（RDS、Cloud SQL）
- 如果必须在 K8s 中运行，使用成熟的 Operator
- 确保有可靠的备份和恢复方案
- 使用专用节点和本地 SSD 存储

---

## 📚 深入阅读

- [Kubernetes 官方文档 - StatefulSet](https://kubernetes.io/zh-cn/docs/concepts/workloads/controllers/statefulset/)
- [Kubernetes 官方文档 - Headless Service](https://kubernetes.io/zh-cn/docs/concepts/services-networking/service/#headless-services)
- [MySQL on Kubernetes (官方示例)](https://kubernetes.io/docs/tasks/run-application/run-replicated-stateful-application/)
- [ZooKeeper on Kubernetes](https://kubernetes.io/docs/tutorials/stateful-application/zookeeper/)
- [Redis Operator for Kubernetes](https://github.com/spotahome/redis-operator)

---

## ✅ 自检清单

- [ ] 理解有状态应用与无状态应用的本质区别
- [ ] 掌握 StatefulSet 的三大特性（稳定网络标识、有序部署、持久存储）
- [ ] 理解 Headless Service 的工作原理和 DNS 记录体系
- [ ] 能使用 StatefulSet 部署 MySQL 主从集群
- [ ] 能使用 StatefulSet 部署 Redis 集群
- [ ] 理解 StatefulSet 的分区更新（partition）机制
- [ ] 掌握 StatefulSet 扩缩容的注意事项（特别是 PVC 不自动删除）
- [ ] 能排查 StatefulSet 的常见问题
- [ ] 理解 StatefulSet vs Deployment 的选择依据
- [ ] 了解生产环境部署有状态应用的注意事项
