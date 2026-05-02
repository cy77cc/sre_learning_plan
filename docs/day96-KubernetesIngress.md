# Day 96: Kubernetes Ingress

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes Ingress
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Ingress 的作用
- 能配置基于域名的路由

---

## 📖 Ingress

### 1. 什么是 Ingress

```
Ingress 管理外部访问到集群内服务：
- 基于域名的路由
- TLS 终止
- 负载均衡
- 需要 Ingress Controller（如 Nginx、Traefik）
```

### 2. Ingress YAML

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp
                port:
                  number: 80
```

### 3. TLS

```yaml
spec:
  tls:
    - hosts:
        - myapp.example.com
      secretName: myapp-tls
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp
                port:
                  number: 80
```

### 4. 安装 Nginx Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

---

## 📚 扩展阅读

- [Ingress 文档](https://kubernetes.io/docs/concepts/services-networking/ingress/)
