# Day 92: Kubernetes Deployment

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes Deployment
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Deployment 的作用
- 掌握滚动更新和回滚
- 能编写 Deployment YAML

---

## 📖 Deployment

### 1. 什么是 Deployment

```
Deployment 管理 Pod 的副本：
- 定义期望的副本数（replicas）
- 自动维护副本数
- 支持滚动更新
- 支持回滚
```

### 2. Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: app
          image: myapp:v1
          ports:
            - containerPort: 8080
```

### 3. 滚动更新

```bash
# 更新镜像
kubectl set image deployment/myapp app=myapp:v2

# 查看更新状态
kubectl rollout status deployment/myapp

# 查看历史
kubectl rollout history deployment/myapp

# 回滚
kubectl rollout undo deployment/myapp
kubectl rollout undo deployment/myapp --to-revision=2
```

### 4. 扩缩容

```bash
kubectl scale deployment/myapp --replicas=5
```

---

## 📚 扩展阅读

- [Deployment 文档](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
