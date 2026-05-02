# Day 90: Kubernetes 简介与架构

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes 简介与架构
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Kubernetes 的核心概念和架构
- 掌握 Master/Node 组件的作用
- 理解 Pod、Service、Deployment 的关系

---

## 📖 K8s 架构

### 1. 为什么需要 K8s

```
Docker 的问题：
- 如何调度容器到多台机器？
- 如何自动扩缩容？
- 如何做服务发现？
- 如何做滚动更新？

Kubernetes 解决：
- 容器编排（调度、部署、管理）
- 自动扩缩容（HPA）
- 服务发现和负载均衡
- 滚动更新和回滚
- 自我修复（自愈）
```

### 2. K8s 架构

```
Master 节点（控制平面）：
  ├── API Server（所有交互的入口）
  ├── etcd（键值存储，集群状态）
  ├── Scheduler（调度 Pod 到节点）
  └── Controller Manager（维护期望状态）

Node 节点（工作节点）：
  ├── kubelet（与 Master 通信，管理容器）
  ├── kube-proxy（网络代理，服务发现）
  └── Container Runtime（Docker/containerd）
```

### 3. 核心概念

| 概念 | 说明 |
|------|------|
| Pod | 最小部署单元，包含一个或多个容器 |
| Service | 稳定的网络端点，暴露 Pod |
| Deployment | 管理 Pod 的副本和更新 |
| Namespace | 逻辑隔离 |
| ConfigMap | 配置管理 |
| Secret | 敏感信息管理 |
| Volume | 持久化存储 |

### 4. 安装 minikube

```bash
# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 启动
minikube start --driver=docker

# 安装 kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 验证
kubectl cluster-info
kubectl get nodes
```

---

## 📚 扩展阅读

- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [K8s 架构详解](https://kubernetes.io/docs/concepts/overview/components/)
