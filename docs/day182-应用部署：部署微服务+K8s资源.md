# Day 182: 部署微服务 + K8s 资源 — 微服务架构与 Kubernetes 编排

> 📅 日期：2026-05-05
> 📖 学习主题：微服务架构设计、Deployment/Service/Ingress、ConfigMap/Secret、HPA、PDB
> ⏰ 预计学习时间：6-8 小时
> 📋 前置知识：Day 90-104 (Kubernetes), Day 181 (Terraform 基础设施)

---

## 🎯 学习目标

完成 Day 182 的学习后，你应该能够：

1. 设计微服务架构并编写服务代码骨架
2. 创建 Dockerfile 构建容器镜像
3. 编写完整的 K8s Deployment、Service、Ingress 资源
4. 使用 ConfigMap 和 Secret 管理配置
5. 配置 HPA 实现自动扩缩容
6. 配置 PDB 保证高可用

---

## 📖 核心知识点

### 1. 微服务架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                     微服务架构总览                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Ingress (Nginx)                       │   │
│  │              api.sre-capstone.com                        │   │
│  └────────┬──────────────┬──────────────┬──────────────────┘   │
│           │              │              │                       │
│  ┌────────┴───────┐ ┌────┴────┐ ┌──────┴──────┐               │
│  │  /api/users    │ │/api/    │ │ /api/products│               │
│  │  User Service  │ │ orders  │ │Product Service│              │
│  │  (Go :8080)    │ │Order Svc│ │  (Python :8080)│             │
│  └────────┬───────┘ └────┬────┘ └──────┬──────┘               │
│           │              │              │                       │
│           └──────────────┼──────────────┘                       │
│                          │                                      │
│                 ┌────────┴────────┐                             │
│                 │   PostgreSQL    │                             │
│                 │     (RDS)       │                             │
│                 └────────┬────────┘                             │
│                          │                                      │
│                 ┌────────┴────────┐                             │
│                 │     Redis       │                             │
│                 │  (ElastiCache)  │                             │
│                 └─────────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 微服务代码实现

#### 2.1 User Service (Go)

```go
// services/user-service/main.go
package main

import (
    "context"
    "fmt"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
    "go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

// ============================================================
// 指标定义
// ============================================================
var (
    httpRequestsTotal = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total number of HTTP requests",
        },
        []string{"method", "path", "status"},
    )

    httpRequestDuration = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "HTTP request duration in seconds",
            Buckets: prometheus.DefBuckets,
        },
        []string{"method", "path"},
    )

    activeConnections = prometheus.NewGauge(
        prometheus.GaugeOpts{
            Name: "active_connections",
            Help: "Number of active connections",
        },
    )
)

func init() {
    prometheus.MustRegister(httpRequestsTotal)
    prometheus.MustRegister(httpRequestDuration)
    prometheus.MustRegister(activeConnections)
}

// ============================================================
// 模型定义
// ============================================================
type User struct {
    ID        string    `json:"id"`
    Username  string    `json:"username"`
    Email     string    `json:"email"`
    CreatedAt time.Time `json:"created_at"`
}

type HealthResponse struct {
    Status    string `json:"status"`
    Service   string `json:"service"`
    Version   string `json:"version"`
    Timestamp string `json:"timestamp"`
}

// ============================================================
// 模拟数据存储
// ============================================================
var users = map[string]User{
    "1": {ID: "1", Username: "alice", Email: "alice@example.com", CreatedAt: time.Now()},
    "2": {ID: "2", Username: "bob", Email: "bob@example.com", CreatedAt: time.Now()},
    "3": {ID: "3", Username: "charlie", Email: "charlie@example.com", CreatedAt: time.Now()},
}

// ============================================================
// 初始化 OpenTelemetry
// ============================================================
func initTracer() (*sdktrace.TracerProvider, error) {
    ctx := context.Background()

    exporter, err := otlptracegrpc.New(ctx,
        otlptracegrpc.WithInsecure(),
        otlptracegrpc.WithEndpoint(
            func() string {
                if ep := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"); ep != "" {
                    return ep
                }
                return "otel-collector:4317"
            }(),
        ),
    )
    if err != nil {
        return nil, fmt.Errorf("failed to create OTLP exporter: %w", err)
    }

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceNameKey.String("user-service"),
            semconv.ServiceVersionKey.String("1.0.0"),
            semconv.DeploymentEnvironmentKey.String(
                func() string {
                    if env := os.Getenv("ENVIRONMENT"); env != "" {
                        return env
                    }
                    return "dev"
                }(),
            ),
        )),
    )

    otel.SetTracerProvider(tp)
    return tp, nil
}

// ============================================================
// 中间件: 指标收集
// ============================================================
func metricsMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        start := time.Now()
        activeConnections.Inc()

        c.Next()

        activeConnections.Dec()
        duration := time.Since(start).Seconds()
        status := fmt.Sprintf("%d", c.Writer.Status())

        httpRequestsTotal.WithLabelValues(c.Request.Method, c.FullPath(), status).Observe(1)
        httpRequestDuration.WithLabelValues(c.Request.Method, c.FullPath()).Observe(duration)
    }
}

// ============================================================
// Handler: 健康检查
// ============================================================
func healthHandler(c *gin.Context) {
    c.JSON(http.StatusOK, HealthResponse{
        Status:    "healthy",
        Service:   "user-service",
        Version:   "1.0.0",
        Timestamp: time.Now().UTC().Format(time.RFC3339),
    })
}

func readyHandler(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{"status": "ready"})
}

// ============================================================
// Handler: 用户 CRUD
// ============================================================
func listUsers(c *gin.Context) {
    userList := make([]User, 0, len(users))
    for _, u := range users {
        userList = append(userList, u)
    }
    c.JSON(http.StatusOK, gin.H{"users": userList, "total": len(userList)})
}

func getUser(c *gin.Context) {
    id := c.Param("id")
    user, exists := users[id]
    if !exists {
        c.JSON(http.StatusNotFound, gin.H{"error": "user not found"})
        return
    }
    c.JSON(http.StatusOK, user)
}

func createUser(c *gin.Context) {
    var user User
    if err := c.ShouldBindJSON(&user); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    user.ID = fmt.Sprintf("%d", len(users)+1)
    user.CreatedAt = time.Now()
    users[user.ID] = user
    c.JSON(http.StatusCreated, user)
}

// ============================================================
// 主函数
// ============================================================
func main() {
    // 初始化 Tracer
    tp, err := initTracer()
    if err != nil {
        log.Printf("Warning: failed to init tracer: %v", err)
    } else {
        defer func() {
            _ = tp.Shutdown(context.Background())
        }()
    }

    // 设置 Gin
    r := gin.Default()

    // 中间件
    r.Use(metricsMiddleware())
    r.Use(otelgin.Middleware("user-service"))

    // 路由
    r.GET("/health", healthHandler)
    r.GET("/ready", readyHandler)
    r.GET("/metrics", gin.WrapH(promhttp.Handler()))

    api := r.Group("/api/v1")
    {
        api.GET("/users", listUsers)
        api.GET("/users/:id", getUser)
        api.POST("/users", createUser)
    }

    // 启动服务器
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }

    srv := &http.Server{
        Addr:    ":" + port,
        Handler: r,
    }

    go func() {
        log.Printf("User Service starting on port %s", port)
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("Server failed: %v", err)
        }
    }()

    // 优雅关闭
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    log.Println("Shutting down server...")
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    if err := srv.Shutdown(ctx); err != nil {
        log.Fatalf("Server forced to shutdown: %v", err)
    }
    log.Println("Server exited")
}
```

```go
// services/user-service/go.mod
module github.com/sre-capstone/user-service

go 1.22

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/prometheus/client_golang v1.19.0
    go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin v0.49.0
    go.opentelemetry.io/otel v1.24.0
    go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc v1.24.0
    go.opentelemetry.io/otel/sdk v1.24.0
)
```

#### 2.2 User Service Dockerfile

```dockerfile
# services/user-service/Dockerfile

# ============================================================
# 阶段 1: 构建
# ============================================================
FROM golang:1.22-alpine AS builder

WORKDIR /app

# 安装依赖
COPY go.mod go.sum ./
RUN go mod download

# 复制源码
COPY . .

# 编译
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-w -s" -o /user-service .

# ============================================================
# 阶段 2: 运行
# ============================================================
FROM alpine:3.19

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

# 从构建阶段复制二进制
COPY --from=builder /user-service .

# 创建非 root 用户
RUN addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:8080/health || exit 1

ENTRYPOINT ["./user-service"]
```

#### 2.3 Product Service (Python/FastAPI)

```python
# services/product-service/app/main.py
import os
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.responses import Response
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# ============================================================
# OpenTelemetry 初始化
# ============================================================
resource = Resource.create({
    "service.name": "product-service",
    "service.version": "1.0.0",
    "deployment.environment": os.getenv("ENVIRONMENT", "dev"),
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "otel-collector:4317"),
        insecure=True,
    )
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("product-service")

# ============================================================
# Prometheus 指标
# ============================================================
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Number of active requests",
)

# ============================================================
# 数据模型
# ============================================================
class Product(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    price: float
    stock: int = 0
    created_at: Optional[str] = None

# ============================================================
# 模拟数据
# ============================================================
products_db: dict[str, dict] = {
    "prod-1": {
        "id": "prod-1",
        "name": "Mechanical Keyboard",
        "description": "Cherry MX switches, RGB lighting",
        "price": 129.99,
        "stock": 50,
        "created_at": "2026-01-15T10:00:00Z",
    },
    "prod-2": {
        "id": "prod-2",
        "name": "Gaming Mouse",
        "description": "16000 DPI, ergonomic design",
        "price": 79.99,
        "stock": 100,
        "created_at": "2026-01-20T14:30:00Z",
    },
    "prod-3": {
        "id": "prod-3",
        "name": "USB-C Hub",
        "description": "7-in-1, 4K HDMI, 100W PD",
        "price": 49.99,
        "stock": 200,
        "created_at": "2026-02-01T09:15:00Z",
    },
}

# ============================================================
# FastAPI 应用
# ============================================================
app = FastAPI(
    title="Product Service",
    description="SRE Capstone - Product Service",
    version="1.0.0",
)

@app.middleware("http")
async def metrics_middleware(request, call_next):
    ACTIVE_REQUESTS.inc()
    start = time.time()

    response = await call_next(request)

    duration = time.time() - start
    ACTIVE_REQUESTS.dec()

    REQUEST_COUNT.labels(
        method=request.method,
        path=request.url.path,
        status=str(response.status_code),
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        path=request.url.path,
    ).observe(duration)

    return response

# ============================================================
# 路由
# ============================================================
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "product-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/ready")
async def ready():
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")

@app.get("/api/v1/products")
async def list_products():
    with tracer.start_as_current_span("list_products"):
        return {
            "products": list(products_db.values()),
            "total": len(products_db),
        }

@app.get("/api/v1/products/{product_id}")
async def get_product(product_id: str):
    with tracer.start_as_current_span("get_product") as span:
        span.set_attribute("product.id", product_id)

        product = products_db.get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

@app.post("/api/v1/products", status_code=201)
async def create_product(product: Product):
    with tracer.start_as_current_span("create_product"):
        product_id = f"prod-{uuid.uuid4().hex[:8]}"
        product_data = product.model_dump()
        product_data["id"] = product_id
        product_data["created_at"] = datetime.utcnow().isoformat()
        products_db[product_id] = product_data
        return product_data

@app.put("/api/v1/products/{product_id}/stock")
async def update_stock(product_id: str, quantity: int):
    with tracer.start_as_current_span("update_stock") as span:
        span.set_attribute("product.id", product_id)
        span.set_attribute("quantity", quantity)

        product = products_db.get(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        product["stock"] = quantity
        return product

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

```python
# services/product-service/requirements.txt
fastapi==0.110.0
uvicorn==0.29.0
pydantic==2.6.4
prometheus-client==0.20.0
opentelemetry-api==1.24.0
opentelemetry-sdk==1.24.0
opentelemetry-exporter-otlp-proto-grpc==1.24.0
httpx==0.27.0
```

#### 2.4 Product Service Dockerfile

```dockerfile
# services/product-service/Dockerfile

FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY app/ ./app/

# 创建非 root 用户
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 3. Kubernetes 资源定义

#### 3.1 Namespace

```yaml
# k8s/base/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: sre-capstone
  labels:
    app.kubernetes.io/part-of: sre-capstone
```

#### 3.2 User Service - Deployment

```yaml
# k8s/base/user-service/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: user-service
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/component: backend
    app.kubernetes.io/part-of: sre-capstone
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: user-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app.kubernetes.io/name: user-service
        app.kubernetes.io/version: "1.0.0"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: user-service
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
        - name: user-service
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/user-service:latest
          imagePullPolicy: Always
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          envFrom:
            - configMapRef:
                name: user-service-config
            - secretRef:
                name: user-service-secret
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 15
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 30
      terminationGracePeriodSeconds: 30
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: user-service
```

#### 3.3 User Service - Service

```yaml
# k8s/base/user-service/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: user-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: user-service
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
  selector:
    app.kubernetes.io/name: user-service
```

#### 3.4 User Service - Ingress

```yaml
# k8s/base/user-service/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: user-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: user-service
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.sre-capstone.com
      secretName: api-tls-secret
  rules:
    - host: api.sre-capstone.com
      http:
        paths:
          - path: /api/users(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: user-service
                port:
                  name: http
```

#### 3.5 User Service - ConfigMap

```yaml
# k8s/base/user-service/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: user-service-config
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: user-service
data:
  PORT: "8080"
  ENVIRONMENT: "dev"
  LOG_LEVEL: "info"
  LOG_FORMAT: "json"
  OTEL_EXPORTER_OTLP_ENDPOINT: "otel-collector.observability:4317"
  OTEL_SERVICE_NAME: "user-service"
  DB_HOST: "sre-capstone-dev.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com"
  DB_PORT: "5432"
  DB_NAME: "sre_capstone"
  DB_SSL_MODE: "require"
  REDIS_HOST: "sre-capstone-dev.xxxxxxxxxxxx.0001.use1.cache.amazonaws.com"
  REDIS_PORT: "6379"
```

#### 3.6 User Service - Secret

```yaml
# k8s/base/user-service/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: user-service-secret
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: user-service
type: Opaque
data:
  # base64 编码的值 (echo -n 'value' | base64)
  DB_USERNAME: ZGJhZG1pbg==        # dbadmin
  DB_PASSWORD: WW91clNlY3VyZVBhc3N3b3JkMTIzIQ==  # YourSecurePassword123!
  REDIS_PASSWORD: ""
```

#### 3.7 User Service - HPA

```yaml
# k8s/base/user-service/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: user-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: user-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user-service
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
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
```

#### 3.8 User Service - PDB

```yaml
# k8s/base/user-service/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: user-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: user-service
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: user-service
```

#### 3.9 User Service - ServiceAccount

```yaml
# k8s/base/user-service/serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: user-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: user-service
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/sre-capstone-dev-user-service
```

#### 3.10 Product Service Resources

```yaml
# k8s/base/product-service/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: product-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: product-service
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/component: backend
    app.kubernetes.io/part-of: sre-capstone
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: product-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app.kubernetes.io/name: product-service
        app.kubernetes.io/version: "1.0.0"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: product-service
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
        - name: product-service
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/product-service:latest
          imagePullPolicy: Always
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          envFrom:
            - configMapRef:
                name: product-service-config
          env:
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 15
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 30
      terminationGracePeriodSeconds: 30
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: product-service
```

```yaml
# k8s/base/product-service/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: product-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: product-service
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
  selector:
    app.kubernetes.io/name: product-service
```

```yaml
# k8s/base/product-service/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: product-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: product-service
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/rewrite-target: /$2
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - api.sre-capstone.com
      secretName: api-tls-secret
  rules:
    - host: api.sre-capstone.com
      http:
        paths:
          - path: /api/products(/|$)(.*)
            pathType: ImplementationSpecific
            backend:
              service:
                name: product-service
                port:
                  name: http
```

```yaml
# k8s/base/product-service/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: product-service-config
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: product-service
data:
  PORT: "8080"
  ENVIRONMENT: "dev"
  LOG_LEVEL: "info"
  OTEL_EXPORTER_OTLP_ENDPOINT: "otel-collector.observability:4317"
  OTEL_SERVICE_NAME: "product-service"
```

```yaml
# k8s/base/product-service/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: product-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-service
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
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 2
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Pods
          value: 1
          periodSeconds: 120
```

```yaml
# k8s/base/product-service/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: product-service
  namespace: sre-capstone
  labels:
    app.kubernetes.io/name: product-service
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: product-service
```

### 4. Kustomize 配置

```yaml
# k8s/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - namespace.yaml
  - user-service/deployment.yaml
  - user-service/service.yaml
  - user-service/ingress.yaml
  - user-service/configmap.yaml
  - user-service/secret.yaml
  - user-service/hpa.yaml
  - user-service/pdb.yaml
  - user-service/serviceaccount.yaml
  - product-service/deployment.yaml
  - product-service/service.yaml
  - product-service/ingress.yaml
  - product-service/configmap.yaml
  - product-service/hpa.yaml
  - product-service/pdb.yaml

commonLabels:
  app.kubernetes.io/managed-by: kustomize
```

```yaml
# k8s/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: sre-capstone

resources:
  - ../../base

patches:
  - target:
      kind: Deployment
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 1
  - target:
      kind: HorizontalPodAutoscaler
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: 1
      - op: replace
        path: /spec/maxReplicas
        value: 3

configMapGenerator:
  - name: user-service-config
    behavior: merge
    literals:
      - ENVIRONMENT=dev
      - LOG_LEVEL=debug

images:
  - name: 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/user-service
    newTag: dev-latest
  - name: 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/product-service
    newTag: dev-latest
```

```yaml
# k8s/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: sre-capstone

resources:
  - ../../base

patches:
  - target:
      kind: Deployment
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 3
  - target:
      kind: HorizontalPodAutoscaler
    patch: |-
      - op: replace
        path: /spec/minReplicas
        value: 3
      - op: replace
        path: /spec/maxReplicas
        value: 20

configMapGenerator:
  - name: user-service-config
    behavior: merge
    literals:
      - ENVIRONMENT=prod
      - LOG_LEVEL=warn

images:
  - name: 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/user-service
    newTag: v1.0.0
  - name: 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/product-service
    newTag: v1.0.0
```

### 5. Nginx Ingress Controller 安装

```bash
#!/usr/bin/env bash
# scripts/install-nginx-ingress.sh

set -euo pipefail

echo "=== 安装 Nginx Ingress Controller ==="

# 添加 Helm 仓库
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# 安装
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.nodeSelector."kubernetes\.io/os"=linux \
  --set controller.service.type=LoadBalancer \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"=nlb \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-cross-zone-load-balancing-enabled"=true \
  --set controller.metrics.enabled=true \
  --set controller.podAnnotations."prometheus\.io/scrape"=true \
  --set controller.podAnnotations."prometheus\.io/port"=10254

echo "=== 等待 Ingress Controller 就绪 ==="
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

echo "=== 获取 LoadBalancer 地址 ==="
kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
echo ""
```

---

## 💻 实战练习

### 练习 1：构建并推送微服务镜像

**目标**：构建 User Service 和 Product Service 的 Docker 镜像。

**步骤**：

```bash
# 1. 创建 ECR 仓库
aws ecr create-repository --repository-name sre-capstone/user-service --region us-east-1
aws ecr create-repository --repository-name sre-capstone/product-service --region us-east-1

# 2. 登录 ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# 3. 构建 User Service
cd services/user-service
docker build -t 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/user-service:v1.0.0 .
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/user-service:v1.0.0

# 4. 构建 Product Service
cd ../product-service
docker build -t 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/product-service:v1.0.0 .
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/sre-capstone/product-service:v1.0.0
```

**验证标准**：
- 镜像构建成功
- 镜像推送到 ECR
- 可以在 ECR 控制台看到镜像

### 练习 2：部署微服务到 K8s

**目标**：使用 Kustomize 部署微服务到 EKS 集群。

**步骤**：

```bash
# 1. 配置 kubectl
aws eks update-kubeconfig --name sre-capstone-dev-eks --region us-east-1

# 2. 安装 Nginx Ingress Controller
chmod +x scripts/install-nginx-ingress.sh
./scripts/install-nginx-ingress.sh

# 3. 部署应用 (Dev 环境)
kubectl apply -k k8s/overlays/dev/

# 4. 验证部署
kubectl get pods -n sre-capstone
kubectl get svc -n sre-capstone
kubectl get ingress -n sre-capstone

# 5. 测试服务
INGRESS_ADDR=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

curl http://${INGRESS_ADDR}/api/users -H "Host: api.sre-capstone.com"
curl http://${INGRESS_ADDR}/api/products -H "Host: api.sre-capstone.com"
```

**验证标准**：
- 所有 Pod 状态为 Running
- Service 和 Ingress 创建成功
- API 可以正常响应

### 练习 3：验证 HPA 自动扩缩容

**目标**：通过压力测试验证 HPA 自动扩缩容功能。

**步骤**：

```bash
# 1. 查看当前副本数
kubectl get hpa -n sre-capstone

# 2. 使用 hey 进行压力测试
# 安装 hey
go install github.com/rakyll/hey@latest

# 3. 获取服务地址
INGRESS_ADDR=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# 4. 发送大量请求
hey -z 5m -c 100 -q 500 \
  -H "Host: api.sre-capstone.com" \
  "http://${INGRESS_ADDR}/api/users"

# 5. 观察 HPA 扩容
watch kubectl get hpa -n sre-capstone
watch kubectl get pods -n sre-capstone

# 6. 停止压力测试后观察缩容 (需要等待 5 分钟 stabilization window)
```

**验证标准**：
- 负载增加时 Pod 数量自动增加
- 负载减少后 Pod 数量自动减少
- 扩缩容过程中服务不中断

---

## 🎯 面试题精选

### 问题 1：解释 K8s Deployment 的滚动更新策略

**参考答案**：

滚动更新通过 `maxUnavailable` 和 `maxSurge` 控制：
- `maxUnavailable`：更新过程中最多有多少 Pod 不可用
- `maxSurge`：更新过程中最多比期望数量多多少 Pod

例如 `maxUnavailable: 0, maxSurge: 1` 表示：
1. 先创建 1 个新 Pod
2. 新 Pod Ready 后，删除 1 个旧 Pod
3. 重复直到所有 Pod 更新完成

优势：零停机更新。

### 问题 2：HPA 的工作原理是什么？

**参考答案**：

HPA (Horizontal Pod Autoscaler) 工作流程：
1. Metrics Server 收集 Pod 指标
2. HPA Controller 定期查询指标 (默认 15 秒)
3. 计算期望副本数：`期望副本 = ceil(当前副本 * (当前指标 / 目标指标))`
4. 执行扩缩容

支持的指标类型：
- Resource: CPU、内存
- Pods: 自定义 Pod 指标
- Object: K8s 对象指标

### 问题 3：PDB 的作用是什么？如何配置？

**参考答案**：

PDB (Pod Disruption Budget) 限制自愿中断期间不可用的 Pod 数量。

自愿中断场景：
- Node 维护
- Cluster Autoscaler 缩容
- 手动删除 Pod

配置方式：
- `minAvailable`：最少可用 Pod 数
- `maxUnavailable`：最多不可用 Pod 数

建议：关键服务设置 `minAvailable: 1`，确保始终有可用实例。

### 问题 4：ConfigMap 和 Secret 的区别？

**参考答案**：

| 特性 | ConfigMap | Secret |
|------|-----------|--------|
| 数据 | 非敏感配置 | 敏感数据 |
| 编码 | 明文 | Base64 |
| 加密 | 否 | 可配置加密 |
| 挂载 | 文件/环境变量 | 文件/环境变量 |
| 大小限制 | 1MB | 1MB |

最佳实践：
- ConfigMap：数据库主机、端口、日志级别
- Secret：密码、API Key、TLS 证书
- 使用 External Secrets Operator 从 AWS Secrets Manager 同步

### 问题 5：如何实现零停机部署？

**参考答案**：

1. **Rolling Update**：逐步替换 Pod
2. **Readiness Probe**：确保新 Pod 就绪后才接收流量
3. **PDB**：保证最少可用实例
4. **Graceful Shutdown**：处理完当前请求后关闭
5. **Pre-stop Hook**：等待负载均衡器摘除
6. **Startup Probe**：慢启动应用保护

```yaml
lifecycle:
  preStop:
    exec:
      command: ["/bin/sh", "-c", "sleep 10"]
```

### 问题 6：如何调试 CrashLoopBackOff 状态的 Pod？

**参考答案**：

```bash
# 1. 查看 Pod 状态
kubectl describe pod <pod-name> -n <namespace>

# 2. 查看日志
kubectl logs <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous

# 3. 进入容器调试
kubectl exec -it <pod-name> -n <namespace> -- /bin/sh

# 4. 查看事件
kubectl get events -n <namespace> --sort-by=.metadata.creationTimestamp

# 5. 常见原因
# - 镜像拉取失败
# - 启动命令错误
# - 依赖服务不可用
# - 资源不足
# - 配置错误
```

### 问题 7：解释 K8s 中的资源请求和限制

**参考答案**：

- **Requests**：调度依据，保证分配的最小资源
- **Limits**：运行时上限，超过会被限制 (CPU) 或 OOMKilled (内存)

```yaml
resources:
  requests:
    cpu: 100m      # 保证 0.1 核
    memory: 128Mi  # 保证 128MB
  limits:
    cpu: 500m      # 最多 0.5 核
    memory: 512Mi  # 最多 512MB
```

最佳实践：
- 始终设置 requests 和 limits
- requests 用于调度，limits 用于保护
- CPU limits 会导致节流，memory limits 会导致 OOM

---

## 📚 深入阅读

### 官方文档
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Kubernetes PDB](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Kustomize Documentation](https://kustomize.io/)

### 推荐资源
- [12-Factor App](https://12factor.net/)
- [Kubernetes Best Practices](https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture)

---

## ✅ 自检清单

- [ ] 理解微服务架构设计原则
- [ ] 能编写多阶段 Dockerfile
- [ ] 能创建 K8s Deployment、Service、Ingress
- [ ] 理解 ConfigMap 和 Secret 的使用场景
- [ ] 能配置 HPA 实现自动扩缩容
- [ ] 理解 PDB 的作用和配置
- [ ] 能使用 Kustomize 管理多环境配置
- [ ] 理解滚动更新和零停机部署
- [ ] 完成 3 个实战练习
- [ ] 能回答相关面试题

---

*由 SRE 学习计划自动生成 | 2026-05-03*
