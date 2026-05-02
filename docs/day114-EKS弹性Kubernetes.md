# Day 114: EKS 弹性 Kubernetes

> 📅 日期：2026-05-04
> 📖 学习主题：EKS 弹性 Kubernetes
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 EKS 架构
- 能创建 EKS 集群

---

## 📖 EKS

### 创建集群

```bash
eksctl create cluster \
    --name my-cluster \
    --region us-east-1 \
    --nodegroup-name standard-workers \
    --node-type t3.medium \
    --nodes 3 \
    --nodes-min 2 \
    --nodes-max 5
```

### 特性

- 托管控制平面
- 自动升级
- 集成 AWS IAM
- Fargate 支持

---

## 📚 扩展阅读

- [EKS 文档](https://docs.aws.amazon.com/eks/)
