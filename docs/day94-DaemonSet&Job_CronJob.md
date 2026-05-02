# Day 94: DaemonSet & Job & CronJob

> 📅 日期：2026-05-03
> 📖 学习主题：DaemonSet & Job & CronJob
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解三种控制器的工作负载
- 能编写对应的 YAML

---

## 📖 工作负载类型

### 1. DaemonSet

```
在每个节点上运行一个 Pod 副本
适用：日志收集、监控代理

apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    metadata:
      labels:
        app: fluentd
    spec:
      containers:
        - name: fluentd
          image: fluentd:v1
```

### 2. Job

```
运行一次直到完成
适用：批处理、数据迁移

apiVersion: batch/v1
kind: Job
metadata:
  name: backup
spec:
  template:
    spec:
      containers:
        - name: backup
          image: backup-tool:v1
          args: ["--full"]
      restartPolicy: Never
```

### 3. CronJob

```
定时运行 Job
适用：定期备份、清理

apiVersion: batch/v1
kind: CronJob
metadata:
  name: cleanup
spec:
  schedule: "0 2 * * *"  # 每天凌晨 2 点
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: cleanup
              image: cleanup-tool:v1
          restartPolicy: OnFailure
```

---

## 📚 扩展阅读

- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
