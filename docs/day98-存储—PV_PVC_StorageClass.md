# Day 98: 存储 — PV/PVC/StorageClass

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes 存储 — PV/PVC/StorageClass
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 K8s 存储抽象层
- 掌握 PV、PVC、StorageClass 的关系

---

## 📖 存储架构

### 1. 三层抽象

```
StorageClass（存储类）
  ↓ 动态供应
PersistentVolume（PV，持久卷）
  ↓ 绑定
PersistentVolumeClaim（PVC，持久卷声明）
  ↓ 挂载
Pod
```

### 2. PVC

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
```

### 3. PV

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /data/mysql
```

### 4. StorageClass

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
```

### 5. 访问模式

| 模式 | 说明 |
|------|------|
| RWO | 单节点读写 |
| ROX | 多节点只读 |
| RWX | 多节点读写 |

---

## 📚 扩展阅读

- [K8s 存储文档](https://kubernetes.io/docs/concepts/storage/)
