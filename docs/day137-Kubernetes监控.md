# Day 137: Kubernetes 监控

> 📅 日期：2026-05-04
> 📖 学习主题：Kubernetes 监控
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 K8s 监控指标
- 掌握 kube-state-metrics

---

## 📖 K8s 监控

### 指标来源

```
kubelet — 容器资源使用
kube-state-metrics — K8s 对象状态
cAdvisor — 容器指标
Node Exporter — 节点指标
```

### 关键指标

```
节点：CPU、内存、磁盘、网络
Pod：CPU、内存、重启次数
Deployment：可用副本数
```

---

## 📚 扩展阅读

- [K8s 监控最佳实践](https://kubernetes.io/docs/tasks/debug/debug-cluster/)
