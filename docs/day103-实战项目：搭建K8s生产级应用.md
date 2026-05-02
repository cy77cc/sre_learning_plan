# Day 103: 实战项目 — 搭建 K8s 生产级应用

> 📅 日期：2026-05-03
> 📖 学习主题：实战项目：搭建 K8s 生产级应用
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 综合运用 K8s 知识部署完整应用
- 掌握生产环境最佳实践

---

## 🏗️ 项目：部署微服务应用

### 架构

```
Ingress (Nginx)
  → Service (web-frontend)
    → Deployment (React App)
  → Service (api-backend)
    → Deployment (Python API)
      → Service (MySQL)
        → StatefulSet + PVC
      → Service (Redis)
        → Deployment + PVC
```

### 部署

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f mysql-statefulset.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f web-deployment.yaml
kubectl apply -f services.yaml
kubectl apply -f ingress.yaml
```

### 验证

```bash
kubectl get all -n myapp
kubectl get ingress -n myapp
curl -H "Host: myapp.example.com" http://<ingress-ip>
```

---

## 📚 扩展阅读

- [K8s 最佳实践](https://kubernetes.io/docs/concepts/configuration/overview/)
