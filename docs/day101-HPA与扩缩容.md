# Day 101: HPA 与扩缩容

> 📅 日期：2026-05-03
> 📖 学习主题：K8s HPA 与扩缩容
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Horizontal Pod Autoscaler
- 能配置基于 CPU/内存的自动扩缩容

---

## 📖 HPA

### 1. 工作原理

```
Metrics Server → 收集指标
  ↓
HPA Controller → 对比当前指标与目标值
  ↓
调整 Deployment 的 replicas
```

### 2. 配置 HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### 3. 常用命令

```bash
kubectl autoscale deployment myapp --cpu-percent=70 --min=2 --max=10
kubectl get hpa
kubectl describe hpa myapp-hpa
```

### 4. VPA 与 Cluster Autoscaler

- VPA（Vertical Pod Autoscaler）：调整资源请求/限制
- Cluster Autoscaler：自动增加/减少节点

---

## 📚 扩展阅读

- [HPA 文档](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
