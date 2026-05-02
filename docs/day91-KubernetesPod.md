# Day 91: Kubernetes Pod

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes Pod
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Pod 的概念和生命周期
- 能编写 Pod YAML
- 掌握 Pod 的调试方法

---

## 📖 Pod 详解

### 1. 什么是 Pod

```
Pod 是 K8s 最小的部署单元：
- 一个 Pod 可以包含一个或多个容器
- Pod 内的容器共享网络和存储
- Pod 是调度的基本单位（不是容器）
```

### 2. Pod YAML

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: myapp
  labels:
    app: myapp
spec:
  containers:
    - name: app
      image: myapp:v1
      ports:
        - containerPort: 8080
      resources:
        requests:
          memory: "128Mi"
          cpu: "250m"
        limits:
          memory: "256Mi"
          cpu: "500m"
      livenessProbe:
        httpGet:
          path: /health
          port: 8080
        initialDelaySeconds: 5
        periodSeconds: 10
      readinessProbe:
        httpGet:
          path: /ready
          port: 8080
        initialDelaySeconds: 3
```

### 3. Pod 生命周期

```
Pending → Running → Succeeded/Failed
  │          │
  │          └─ 容器可能重启（restartPolicy）
  │
  └─ 等待调度（资源不足、镜像拉取中）

重启策略：
  Always（默认）— 总是重启
  OnFailure — 失败时重启
  Never — 从不重启
```

### 4. 常用命令

```bash
kubectl apply -f pod.yaml
kubectl get pods
kubectl describe pod myapp
kubectl logs myapp
kubectl exec -it myapp -- /bin/bash
kubectl delete pod myapp
kubectl port-forward myapp 8080:8080
```

---

## 📚 扩展阅读

- [Pod 文档](https://kubernetes.io/docs/concepts/workloads/pods/)
