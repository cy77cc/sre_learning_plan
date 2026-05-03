# Day 96: Kubernetes Ingress

> 📅 日期：2026-05-03
> 📖 学习主题：Kubernetes Ingress（Ingress Controller, 路由规则, TLS, 重写, 限流, 灰度发布, Gateway API）
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 95 Kubernetes Service, Day 92 Deployment

## 🎯 学习目标

完成 Day 96 的学习后，你应该能够：

1. 理解 Ingress 的架构和工作原理
2. 掌握 Nginx Ingress Controller 和 Traefik 的配置
3. 能够配置 TLS 终止、路径重写、限流等高级功能
4. 实现基于 Ingress 的灰度发布/金丝雀发布
5. 了解 Gateway API 的设计理念和迁移路径

---

## 📖 核心知识点

### 1. Ingress 概念与架构

#### 1.1 为什么需要 Ingress

```
没有 Ingress 时的暴露方式：

方案 1：NodePort
  每个 Service 分配一个节点端口（30000-32767）
  → 端口资源有限
  → 无法基于域名/路径路由
  → 每个 Service 需要一个外部 LB

方案 2：LoadBalancer
  每个 Service 创建一个云厂商 LB
  → 成本高（每个 LB 每月 $15-50）
  → 10 个 Service = 10 个 LB

方案 3：Ingress（推荐）
  一个 Ingress Controller（一个 LB）
  → 基于域名/路径路由到不同 Service
  → 集中管理 TLS、限流、认证
  → 成本最低
```

#### 1.2 Ingress 架构图

```
                        互联网
                          │
                          ▼
              ┌───────────────────────┐
              │   云厂商 LoadBalancer  │ ← 一个外部 IP
              │   (或 NodePort)       │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Ingress Controller  │ ← Nginx/Traefik/HAProxy
              │   (Pod 运行)          │
              └───────────┬───────────┘
                          │
           ┌──────────────┼──────────────┐
           │              │              │
           ▼              ▼              ▼
    ┌────────────┐ ┌────────────┐ ┌────────────┐
    │ Service A  │ │ Service B  │ │ Service C  │
    │ app1.com   │ │ app2.com   │ │ app1.com/  │
    │            │ │            │ │   api      │
    └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
          │              │              │
     ┌────┼────┐    ┌────┼────┐    ┌────┼────┐
     ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼
    Pod  Pod  Pod  Pod  Pod  Pod  Pod  Pod  Pod
```

#### 1.3 Ingress 资源 vs Ingress Controller

```
Ingress 资源（声明式配置）：
  → 定义路由规则（域名、路径、后端 Service）
  → 只是 Kubernetes API 对象
  → 本身不做任何事情

Ingress Controller（实际执行者）：
  → 监听 Ingress 资源变化
  → 生成代理配置（nginx.conf / traefik.toml）
  → 处理实际的流量转发
  → 需要单独安装（不是 K8s 内置组件）
```

---

### 2. Ingress Controller 对比

#### 2.1 主流 Ingress Controller

| 特性 | Nginx Ingress | Traefik | HAProxy | Envoy (Contour) |
|------|---------------|---------|---------|-----------------|
| 社区活跃度 | 最高 | 高 | 中 | 高 |
| 配置方式 | 注解为主 | CRD + 注解 | CRD + 注解 | CRD |
| 热更新 | reload | 动态 | 动态 | 动态 |
| 性能 | 高 | 高 | 最高 | 高 |
| 学习曲线 | 低 | 中 | 中 | 高 |
| 自动服务发现 | 否 | 是 | 否 | 否 |
| Dashboard | 否 | 是 | 否 | 否 |
| 适用场景 | 通用 | 微服务 | 高性能 | 服务网格 |

#### 2.2 Nginx Ingress Controller 安装

```bash
# 方式 1：使用 Helm（推荐）
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.service.type=LoadBalancer \
  --set controller.metrics.enabled=true \
  --set controller.podAnnotations."prometheus\.io/scrape"="true" \
  --set controller.podAnnotations."prometheus\.io/port"="10254"

# 方式 2：使用 YAML
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.5/deploy/static/provider/cloud/deploy.yaml

# 验证安装
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

#### 2.3 Traefik 安装

```bash
# 使用 Helm
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  --set replicas=2 \
  --set service.type=LoadBalancer \
  --set dashboard.enabled=true \
  --set metrics.prometheus.enabled=true

# 验证
kubectl get pods -n traefik
kubectl get svc -n traefik
```

---

### 3. Ingress 路由规则

#### 3.1 基于域名的路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-host-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
    # 域名 1 → Service A
    - host: app1.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app1-service
                port:
                  number: 80
    # 域名 2 → Service B
    - host: app2.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app2-service
                port:
                  number: 80
```

#### 3.2 基于路径的路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-routing
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          # 前端
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
          # API 服务
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8080
          # 静态资源
          - path: /static
            pathType: Prefix
            backend:
              service:
                name: static-service
                port:
                  number: 80
```

#### 3.3 pathType 详解

| pathType | 匹配规则 | 示例 |
|----------|----------|------|
| Prefix | 前缀匹配（按 / 分割） | `/api` 匹配 `/api`、`/api/v1`、`/api/users` |
| Exact | 精确匹配 | `/api` 只匹配 `/api`，不匹配 `/api/` |
| ImplementationSpecific | 由 Ingress Controller 决定 | 取决于具体实现 |

```yaml
# pathType 匹配示例
rules:
  - host: example.com
    http:
      paths:
        - path: /api        # Prefix: /api, /api/v1, /api/users 都匹配
          pathType: Prefix
          backend:
            service:
              name: api
              port:
                number: 80
        - path: /api/health  # Exact: 只匹配 /api/health
          pathType: Exact
          backend:
            service:
              name: health
              port:
                number: 80
```

---

### 4. TLS/HTTPS 配置

#### 4.1 基本 TLS 配置

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    # 强制 HTTPS 重定向
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    # HSTS 头
    nginx.ingress.kubernetes.io/hsts: "true"
    nginx.ingress.kubernetes.io/hsts-max-age: "31536000"
    nginx.ingress.kubernetes.io/hsts-include-subdomains: "true"
spec:
  tls:
    - hosts:
        - secure.example.com
        - www.secure.example.com
      secretName: example-tls    # 包含 tls.crt 和 tls.key 的 Secret
  rules:
    - host: secure.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: secure-app
                port:
                  number: 80
```

#### 4.2 创建 TLS Secret

```bash
# 方式 1：从证书文件创建
kubectl create secret tls example-tls \
  --cert=tls.crt \
  --key=tls.key

# 方式 2：YAML 方式
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: example-tls
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
EOF

# 方式 3：使用 cert-manager 自动管理证书
```

#### 4.3 cert-manager 自动证书管理

```yaml
# 安装 cert-manager
# kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml

# ClusterIssuer 配置（Let's Encrypt）
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
---
# 使用 cert-manager 的 Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: auto-tls-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"   # 自动申请证书
spec:
  tls:
    - hosts:
        - secure.example.com
      secretName: secure-example-tls    # cert-manager 自动创建
  rules:
    - host: secure.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: secure-app
                port:
                  number: 80
```

---

### 5. 路径重写

#### 5.1 Nginx Ingress 重写

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rewrite-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    # 重写目标路径
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    # 使用正则捕获组
    nginx.ingress.kubernetes.io/use-regex: "true"
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          # /api/v1/anything → /anything
          - path: /api/v1(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: api-v1
                port:
                  number: 80
          # /api/v2/anything → /anything
          - path: /api/v2(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: api-v2
                port:
                  number: 80
```

#### 5.2 添加/修改请求头

```yaml
annotations:
  # 添加请求头
  nginx.ingress.kubernetes.io/configuration-snippet: |
    more_set_headers "X-Custom-Header: my-value";
    more_set_headers "X-Request-Id: $request_id";
  # 传递真实 IP
  nginx.ingress.kubernetes.io/use-forwarded-headers: "true"
  nginx.ingress.kubernetes.io/proxy-set-headers: "ingress-nginx/custom-headers"
---
# 自定义头的 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-headers
  namespace: ingress-nginx
data:
  X-Real-IP: "$remote_addr"
  X-Forwarded-For: "$proxy_add_x_forwarded_for"
```

---

### 6. 限流配置

#### 6.1 Nginx Ingress 限流

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rate-limit-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    # 每秒每 IP 允许的请求数
    nginx.ingress.kubernetes.io/limit-rps: "10"
    # 每分钟每 IP 允许的请求数
    nginx.ingress.kubernetes.io/limit-rpm: "100"
    # 每小时每 IP 允许的请求数
    nginx.ingress.kubernetes.io/limit-rph: "1000"
    # 并发连接数限制
    nginx.ingress.kubernetes.io/limit-connections: "5"
    # 限流后的状态码
    nginx.ingress.kubernetes.io/limit-burst-multiplier: "3"
    # 限流白名单
    nginx.ingress.kubernetes.io/limit-whitelist: "10.0.0.0/8,172.16.0.0/12"
spec:
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
```

#### 6.2 限流策略详解

```
┌─────────────────────────────────────────────────────────┐
│                    限流策略层次                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  全局限流（Ingress 级别）                                │
│    │                                                    │
│    ├── limit-rps: 每秒请求数                            │
│    ├── limit-rpm: 每分钟请求数                           │
│    ├── limit-rph: 每小时请求数                           │
│    └── limit-connections: 并发连接数                     │
│                                                         │
│  突发控制                                               │
│    └── limit-burst-multiplier: 突发倍数                  │
│        实际突发 = limit-rps × burst-multiplier           │
│        例：limit-rps=10, burst=3 → 突发允许 30 请求     │
│                                                         │
│  白名单                                                │
│    └── limit-whitelist: 不受限流的 IP 段                │
│                                                         │
│  应用级限流（更精细）                                    │
│    └── 使用 Lua 插件或外部限流服务                      │
└─────────────────────────────────────────────────────────┘
```

---

### 7. 灰度发布/金丝雀发布

#### 7.1 基于 Nginx Ingress 注解的灰度

```yaml
# 稳定版 Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-stable
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-stable
                port:
                  number: 80
---
# 金丝雀版 Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: myapp-canary
  annotations:
    kubernetes.io/ingress.class: "nginx"
    # 启用金丝雀
    nginx.ingress.kubernetes.io/canary: "true"
    # 流量权重（10% 流量到金丝雀）
    nginx.ingress.kubernetes.io/canary-weight: "10"
    # 基于 Header 的金丝雀（优先级高于 weight）
    # nginx.ingress.kubernetes.io/canary-by-header: "X-Canary"
    # nginx.ingress.kubernetes.io/canary-by-header-value: "true"
    # 基于 Cookie 的金丝雀
    # nginx.ingress.kubernetes.io/canary-by-cookie: "canary"
    # nginx.ingress.kubernetes.io/canary-by-cookie-value: "always"
spec:
  rules:
    - host: myapp.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: myapp-canary
                port:
                  number: 80
```

#### 7.2 灰度发布策略对比

| 策略 | 实现方式 | 精确度 | 适用场景 |
|------|----------|--------|----------|
| 权重分流 | canary-weight | 百分比 | 渐进式发布 |
| Header 标记 | canary-by-header | 精确 | 内部测试 |
| Cookie 标记 | canary-by-cookie | 精确 | 用户选择加入 |
| IP 白名单 | canary-by-header-value | 精确 | 特定用户 |

#### 7.3 金丝雀发布完整流程

```
┌─ 金丝雀发布流程 ────────────────────────────────────────┐
│                                                         │
│  1. 部署稳定版 v1                                       │
│     kubectl apply -f deployment-v1.yaml                 │
│     kubectl apply -f service-v1.yaml                    │
│     kubectl apply -f ingress-stable.yaml                │
│                                                         │
│  2. 部署金丝雀版 v2（少量副本）                         │
│     kubectl apply -f deployment-v2.yaml                 │
│     kubectl apply -f service-v2.yaml                    │
│     kubectl apply -f ingress-canary.yaml (weight=10)    │
│                                                         │
│  3. 监控指标                                            │
│     - 错误率是否上升？                                  │
│     - 延迟是否增加？                                    │
│     - 业务指标是否正常？                                │
│                                                         │
│  4. 逐步增加流量                                        │
│     weight=10 → 30 → 50 → 80 → 100                    │
│                                                         │
│  5. 完全切换或回滚                                      │
│     成功：更新 stable 到 v2，删除 canary ingress        │
│     失败：删除 canary ingress，流量回到 v1              │
└─────────────────────────────────────────────────────────┘
```

---

### 8. Nginx Ingress 高级配置

#### 8.1 超时配置

```yaml
annotations:
  # 代理超时（秒）
  nginx.ingress.kubernetes.io/proxy-connect-timeout: "10"
  nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
  nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
  # 上传大小限制
  nginx.ingress.kubernetes.io/proxy-body-size: "50m"
  # 重试配置
  nginx.ingress.kubernetes.io/proxy-next-upstream: "error timeout http_502 http_503"
  nginx.ingress.kubernetes.io/proxy-next-upstream-tries: "3"
```

#### 8.2 CORS 配置

```yaml
annotations:
  nginx.ingress.kubernetes.io/enable-cors: "true"
  nginx.ingress.kubernetes.io/cors-allow-origin: "https://frontend.example.com,https://admin.example.com"
  nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
  nginx.ingress.kubernetes.io/cors-allow-headers: "Authorization, Content-Type, X-Request-ID"
  nginx.ingress.kubernetes.io/cors-expose-headers: "X-Request-ID"
  nginx.ingress.kubernetes.io/cors-max-age: "3600"
  nginx.ingress.kubernetes.io/cors-allow-credentials: "true"
```

#### 8.3 认证配置（Basic Auth）

```bash
# 创建密码文件
htpasswd -c auth admin
htpasswd auth user1

# 创建 Secret
kubectl create secret generic basic-auth --from-file=auth
```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: auth-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: basic-auth
    nginx.ingress.kubernetes.io/auth-realm: "Authentication Required"
spec:
  rules:
    - host: admin.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: admin-service
                port:
                  number: 80
```

#### 8.4 自定义 Nginx 配置

```yaml
# 全局配置（ConfigMap）
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-ingress-controller
  namespace: ingress-nginx
data:
  worker-processes: "auto"
  keep-alive: "75"
  upstream-keepalive-connections: "256"
  use-gzip: "true"
  gzip-level: "5"
  gzip-types: "application/json application/javascript text/css text/plain"
  log-format-upstream: '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" $request_length $request_time [$proxy_upstream_name] [$proxy_alternative_upstream_name] $upstream_addr $upstream_response_length $upstream_response_time $upstream_status $req_id'
  # 安全头
  hide-headers: "X-Powered-By,Server"
  ssl-protocols: "TLSv1.2 TLSv1.3"
  ssl-ciphers: "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256"
```

---

### 9. Traefik 特性

#### 9.1 Traefik IngressRoute（CRD）

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: myapp-route
  namespace: default
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`myapp.example.com`)
      kind: Rule
      services:
        - name: myapp-service
          port: 80
      middlewares:
        - name: rate-limit
        - name: compress
  tls:
    secretName: myapp-tls
---
# 中间件：限流
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: rate-limit
spec:
  rateLimit:
    average: 100
    burst: 50
    period: 1s
---
# 中间件：压缩
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: compress
spec:
  compress: {}
```

#### 9.2 Traefik 自动服务发现

```yaml
# Traefik 自动发现带有特定标签的 Service
apiVersion: v1
kind: Service
metadata:
  name: myapp
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.rule: "Host(`myapp.example.com`)"
    traefik.ingress.kubernetes.io/router.tls.certresolver: letsencrypt
spec:
  selector:
    app: myapp
  ports:
    - port: 80
      targetPort: 8080
```

---

### 10. Gateway API（下一代 Ingress）

#### 10.1 Gateway API 概述

```
Gateway API 是 Kubernetes SIG-Network 官方推出的
下一代服务网络 API，旨在替代 Ingress。

核心优势：
  1. 角色分离：基础设施提供者、集群运维、应用开发者
  2. 更强的表达力：Header 匹配、权重路由、请求镜像
  3. 可扩展性：自定义策略附件
  4. 跨命名空间引用
```

#### 10.2 Gateway API 核心资源

```
┌─────────────────────────────────────────────────────────┐
│                  Gateway API 资源层次                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  GatewayClass（基础设施提供者管理）                      │
│    │                                                    │
│    ├── Gateway（集群运维管理）                           │
│    │     │                                              │
│    │     ├── HTTPRoute（应用开发者管理）                 │
│    │     ├── TLSRoute                                  │
│    │     ├── TCPRoute                                  │
│    │     └── GRPCRoute                                 │
│    │                                                    │
│    └── ReferenceGrant（跨命名空间授权）                  │
└─────────────────────────────────────────────────────────┘
```

#### 10.3 Gateway API 示例

```yaml
# GatewayClass（通常由基础设施提供者创建）
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: nginx
spec:
  controllerName: gateway.nginx.org/nginx-gateway-controller
---
# Gateway（集群运维创建）
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: production-gateway
  namespace: infra
spec:
  gatewayClassName: nginx
  listeners:
    - name: http
      protocol: HTTP
      port: 80
    - name: https
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - name: wildcard-tls
      allowedRoutes:
        namespaces:
          from: Selector
          selector:
            matchLabels:
              gateway-access: "true"
---
# HTTPRoute（应用开发者创建）
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: myapp-route
  namespace: myapp
spec:
  parentRefs:
    - name: production-gateway
      namespace: infra
      sectionName: https
  hostnames:
    - "myapp.example.com"
  rules:
    # 规则 1：API 路由
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: api-service
          port: 8080
          weight: 90       # 权重路由
        - name: api-service-canary
          port: 8080
          weight: 10
    # 规则 2：Header 匹配
    - matches:
        - headers:
            - name: x-debug
              value: "true"
      backendRefs:
        - name: debug-service
          port: 8080
    # 规则 3：默认路由
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: frontend-service
          port: 80
```

#### 10.4 Ingress vs Gateway API 对比

| 特性 | Ingress | Gateway API |
|------|---------|-------------|
| 角色分离 | 不支持 | 原生支持 |
| Header 匹配 | 依赖注解 | 原生支持 |
| 权重路由 | 依赖注解 | 原生支持 |
| 跨命名空间 | 不支持 | ReferenceGrant |
| 协议支持 | HTTP/HTTPS | HTTP/TLS/TCP/gRPC |
| 可扩展性 | 注解（字符串） | Policy Attachment |
| 标准化程度 | 低（注解不统一） | 高（统一 API） |

---

## 💻 实战练习

### 练习 1：基础 Ingress 配置

**目标**：配置基于域名和路径的路由

```bash
# 1. 安装 Nginx Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.5/deploy/static/provider/cloud/deploy.yaml

# 2. 创建后端应用
kubectl create deployment app1 --image=nginx --replicas=2
kubectl expose deployment app1 --port=80

kubectl create deployment app2 --image=httpd --replicas=2
kubectl expose deployment app2 --port=80

# 3. 创建基于域名的 Ingress
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-host
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
    - host: app1.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app1
                port:
                  number: 80
    - host: app2.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app2
                port:
                  number: 80
EOF

# 4. 验证 Ingress
kubectl get ingress
kubectl describe ingress multi-host

# 5. 测试路由（需要配置 hosts 或使用 curl -H）
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -H "Host: app1.local" http://${INGRESS_IP}
curl -H "Host: app2.local" http://${INGRESS_IP}
```

### 练习 2：TLS + cert-manager 自动证书

**目标**：配置 HTTPS 并使用 cert-manager 自动管理证书

```bash
# 1. 安装 cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.3/cert-manager.yaml

# 2. 等待 cert-manager 就绪
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager -n cert-manager --timeout=120s

# 3. 创建 ClusterIssuer（使用 staging 环境测试）
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: test@example.com
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
      - http01:
          ingress:
            class: nginx
EOF

# 4. 创建带 TLS 的 Ingress
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-demo
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-staging"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
    - hosts:
        - demo.example.com
      secretName: demo-tls
  rules:
    - host: demo.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app1
                port:
                  number: 80
EOF

# 5. 查看证书状态
kubectl get certificate
kubectl describe certificate demo-tls
kubectl get certificaterequest
```

### 练习 3：金丝雀发布实践

**目标**：实现基于权重的金丝雀发布

```bash
# 1. 部署稳定版
kubectl create deployment app-stable --image=nginx:1.24 --replicas=3
kubectl expose deployment app-stable --port=80

# 2. 给稳定版 Pod 添加版本标识
kubectl exec deploy/app-stable -- sh -c 'echo "v1-stable" > /usr/share/nginx/html/index.html'

# 3. 部署金丝雀版
kubectl create deployment app-canary --image=nginx:1.25 --replicas=1
kubectl expose deployment app-canary --port=80

# 4. 给金丝雀版添加版本标识
kubectl exec deploy/app-canary -- sh -c 'echo "v2-canary" > /usr/share/nginx/html/index.html'

# 5. 创建稳定版 Ingress
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-stable-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
spec:
  rules:
    - host: canary-demo.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-stable
                port:
                  number: 80
EOF

# 6. 创建金丝雀 Ingress（20% 流量）
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-canary-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "20"
spec:
  rules:
    - host: canary-demo.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: app-canary
                port:
                  number: 80
EOF

# 7. 测试流量分配
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
for i in $(seq 1 20); do
  curl -s -H "Host: canary-demo.local" http://${INGRESS_IP}
done | sort | uniq -c

# 预期：约 80% v1-stable，约 20% v2-canary
```

---

## 🎯 面试题精选

### 题目 1：Ingress 和 Service LoadBalancer 有什么区别？

**参考答案**：

- **Service LoadBalancer**：每个 Service 创建一个外部负载均衡器，分配一个外部 IP。适合单个服务暴露。成本高（每个 LB 一个公网 IP + 费用）。
- **Ingress**：一个 Ingress Controller（一个 LB）通过域名/路径路由到多个 Service。适合多服务统一入口。成本低，功能丰富（TLS、限流、重写等）。

### 题目 2：Ingress Controller 是如何工作的？

**参考答案**：

1. Ingress Controller 作为 Pod 运行，暴露为 LoadBalancer 或 NodePort Service
2. 监听 Kubernetes API 中 Ingress 资源的变化
3. 根据 Ingress 规则生成代理配置（如 nginx.conf）
4. 热加载配置（nginx reload 或动态 API）
5. 接收外部流量，根据域名/路径匹配规则，转发到对应后端 Service

### 题目 3：如何实现 Ingress 的金丝雀发布？

**参考答案**：

使用 Nginx Ingress 的金丝雀注解：

1. 创建稳定版 Ingress（指向 stable Service）
2. 创建金丝雀 Ingress（添加 `canary: "true"` 注解）
3. 通过 `canary-weight` 设置流量比例
4. 或通过 `canary-by-header` / `canary-by-cookie` 实现精确控制
5. 逐步增加权重，验证后切换或回滚

### 题目 4：cert-manager 的工作原理是什么？

**参考答案**：

1. 用户在 Ingress 上添加 `cert-manager.io/cluster-issuer` 注解
2. cert-manager 检测到注解，创建 Certificate 资源
3. 创建 CertificateRequest 和 Order 资源
4. 与 ACME 服务器（如 Let's Encrypt）交互
5. 通过 HTTP-01 或 DNS-01 挑战验证域名所有权
6. 获取证书，存储到 Kubernetes Secret
7. 定期自动续期

### 题目 5：Gateway API 相比 Ingress 有什么优势？

**参考答案**：

1. **角色分离**：GatewayClass（基础设施）、Gateway（运维）、HTTPRoute（开发者）
2. **更强的表达力**：原生支持 Header 匹配、权重路由、请求镜像
3. **跨命名空间**：通过 ReferenceGrant 实现安全的跨命名空间引用
4. **协议支持**：HTTP、TLS、TCP、gRPC 统一 API
5. **可扩展性**：Policy Attachment 机制，比注解更规范

### 题目 6：Nginx Ingress 如何配置限流？

**参考答案**：

通过注解配置：
- `limit-rps`：每秒每 IP 请求数限制
- `limit-rpm`：每分钟每 IP 请求数限制
- `limit-connections`：并发连接数限制
- `limit-whitelist`：限流白名单 IP
- `limit-burst-multiplier`：突发倍数

限流使用 nginx 的 `limit_req_zone` 和 `limit_conn_zone` 模块实现。

### 题目 7：Ingress 的 pathType 有哪几种？有什么区别？

**参考答案**：

1. **Prefix**：前缀匹配，按 `/` 分割。`/api` 匹配 `/api`、`/api/v1`、`/api/users`。
2. **Exact**：精确匹配。`/api` 只匹配 `/api`，不匹配 `/api/` 或 `/api/v1`。
3. **ImplementationSpecific**：匹配规则由 Ingress Controller 实现决定。

### 题目 8：如何排查 Ingress 404 问题？

**参考答案**：

1. 检查 Ingress 是否创建：`kubectl get ingress`
2. 检查 Ingress 详情：`kubectl describe ingress` 查看事件
3. 检查后端 Service 是否存在：`kubectl get svc`
4. 检查 Endpoints：`kubectl get endpoints`
5. 检查 Ingress Controller 日志：`kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx`
6. 检查域名解析：确认 DNS 解析到 Ingress Controller 的 IP
7. 检查 Host 头：curl 时必须包含正确的 Host 头

### 题目 9：Traefik 和 Nginx Ingress 的主要区别是什么？

**参考答案**：

| 特性 | Nginx Ingress | Traefik |
|------|---------------|---------|
| 配置方式 | 注解为主 | CRD + 注解 |
| 热更新 | reload（短暂中断） | 动态（无中断） |
| 自动发现 | 否 | 是（通过标签） |
| Dashboard | 否 | 内置 Web UI |
| 中间件 | 注解 | CRD Middleware |
| 学习曲线 | 低 | 中 |

### 题目 10：Ingress Controller 的高可用如何实现？

**参考答案**：

1. **多副本部署**：`replicaCount: 2+`
2. **Pod 反亲和性**：确保副本分布在不同节点
3. **PodDisruptionBudget**：确保滚动更新时至少有 N 个副本
4. **健康检查**：配置 Liveness 和 Readiness Probe
5. **资源限制**：设置 requests 和 limits
6. **HPA**：根据负载自动扩缩容

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: ingress-nginx-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: ingress-nginx
```

---

## 📚 深入阅读

- [Kubernetes Ingress 官方文档](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Nginx Ingress Controller 文档](https://kubernetes.github.io/ingress-nginx/)
- [Traefik 文档](https://doc.traefik.io/traefik/)
- [cert-manager 文档](https://cert-manager.io/docs/)
- [Gateway API 文档](https://gateway-api.sigs.k8s.io/)
- [Gateway API 迁移指南](https://gateway-api.sigs.k8s.io/guides/migrating-from-ingress/)

---

## ✅ 自检清单

- [ ] 能够解释 Ingress 的架构和工作原理
- [ ] 能够配置基于域名和路径的路由规则
- [ ] 能够配置 TLS 终止和 cert-manager 自动证书
- [ ] 能够配置路径重写、限流、CORS 等高级功能
- [ ] 能够实现基于权重/头部/ Cookie 的金丝雀发布
- [ ] 理解 Nginx Ingress 和 Traefik 的区别
- [ ] 了解 Gateway API 的设计理念和核心资源
- [ ] 能够排查 Ingress 相关的常见问题
- [ ] 知道如何实现 Ingress Controller 的高可用
