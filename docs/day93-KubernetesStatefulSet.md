# Day 93: Kubernetes StatefulSet

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes StatefulSet
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 StatefulSet 与 Deployment 的区别
- 能部署有状态应用（数据库）

---

## 📖 StatefulSet

### 1. 有状态 vs 无状态

| 特性 | Deployment | StatefulSet |
|------|-----------|-------------|
| Pod 名称 | 随机 | 有序（app-0, app-1） |
| 存储 | 共享 PVC | 独立 PVC per Pod |
| 网络 | 共享 Service IP | 独立 Headless Service |
| 部署顺序 | 并行 | 有序（0→1→2） |
| 适用场景 | Web 服务 | 数据库、消息队列 |

### 2. StatefulSet YAML

```yaml
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
      containers:
        - name: mysql
          image: mysql:8.0
          volumeMounts:
            - name: data
              mountPath: /var/lib/mysql
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

### 3. Headless Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None  # Headless
  selector:
    app: mysql
  ports:
    - port: 3306
```

---

## 📚 扩展阅读

- [StatefulSet 文档](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
