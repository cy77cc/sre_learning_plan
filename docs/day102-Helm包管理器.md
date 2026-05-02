# Day 102: Helm 包管理器

> 📅 日期：2026-05-03
> 📖 学习主题：K8s Helm 包管理器
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Helm 的作用
- 能安装和管理 Helm Chart

---

## 📖 Helm

### 1. 什么是 Helm

```
Helm = K8s 的包管理器
Chart = 一组 K8s 资源模板
Release = Chart 的运行实例
```

### 2. 安装 Helm

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 3. 常用命令

```bash
# 添加仓库
helm repo add stable https://charts.helm.sh/stable
helm repo update

# 安装
helm install my-release stable/nginx

# 查看
helm list
helm status my-release

# 升级
helm upgrade my-release stable/nginx --set replicaCount=3

# 回滚
helm rollback my-release 1

# 卸载
helm uninstall my-release
```

### 4. 创建自定义 Chart

```bash
helm create myapp
# 生成：
# myapp/
# ├── Chart.yaml
# ├── values.yaml
# ├── charts/
# └── templates/
#     ├── deployment.yaml
#     ├── service.yaml
#     └── ingress.yaml
```

---

## 📚 扩展阅读

- [Helm 文档](https://helm.sh/docs/)
- [Artifact Hub](https://artifacthub.io/)
