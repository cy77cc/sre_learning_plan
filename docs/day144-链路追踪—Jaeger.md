# Day 144: 链路追踪 — Jaeger（分布式追踪原理、OpenTelemetry、Jaeger 架构、采样策略、与 Prometheus/Grafana 集成）

> 📅 日期：2026-05-09
> 📖 学习主题：分布式追踪原理、OpenTelemetry 标准、Jaeger 架构与部署、采样策略、与监控系统集成
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 133 (可观测性基础), Day 134 (Prometheus), Day 136 (Grafana)

## 🎯 学习目标

- 深入理解分布式追踪的核心原理
- 掌握 OpenTelemetry 的架构和语义约定
- 能够部署和配置 Jaeger 追踪系统
- 理解不同的采样策略及其适用场景
- 掌握 Jaeger 与 Prometheus/Grafana 的集成方式
- 能够在微服务架构中实施链路追踪

---

## 📖 核心知识点

### 1. 分布式追踪原理

#### 1.1 为什么需要分布式追踪

```
微服务架构中的请求链路：

用户请求 → API Gateway → User Service → Order Service → Payment Service
                │              │              │              │
                │              │              │              └── DB 查询
                │              │              └── Redis 缓存
                │              └── DB 查询
                └── 认证检查

问题：
  1. 一个请求经过多个服务，如何追踪完整链路？
  2. 哪个服务导致了延迟？
  3. 错误发生在哪个环节？
  4. 服务间的依赖关系是什么？

传统日志的局限：
  - 每个服务独立记录日志
  - 无法关联跨服务的日志
  - 难以定位性能瓶颈
  - 无法可视化请求路径
```

#### 1.2 核心概念

```
分布式追踪核心概念：

┌─────────────────────────────────────────────────────────────────┐
│                    追踪数据模型                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Trace（追踪）：一个完整请求的端到端路径                          │
│  ├── 由多个 Span 组成                                           │
│  ├── 有唯一的 Trace ID                                          │
│  └── 形成一棵 Span 树                                           │
│                                                                   │
│  Span（跨度）：一个操作单元                                      │
│  ├── 有唯一的 Span ID                                           │
│  ├── 有 Parent Span ID（除 Root Span）                          │
│  ├── 包含操作名、开始时间、结束时间                              │
│  ├── 包含 Tags（结构化数据）                                     │
│  ├── 包含 Logs（时间戳事件）                                     │
│  └── 有状态（OK, ERROR, UNSET）                                 │
│                                                                   │
│  Context Propagation（上下文传播）：                              │
│  ├── 将 Trace ID 和 Span ID 传播到下游服务                      │
│  ├── 通过 HTTP Header 传播（W3C Trace Context）                 │
│  └── 保证跨服务的链路关联                                        │
│                                                                   │
│  示例：                                                          │
│  Trace ID: abc123                                               │
│                                                                   │
│  Span A (Root) ────────────────────────────── 100ms             │
│    ├── Span B ──────────────── 50ms                              │
│    │     └── Span D ──── 20ms                                    │
│    └── Span C ──────────────── 60ms                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.3 上下文传播标准

```
W3C Trace Context 标准：

HTTP Header 格式：
  traceparent: 00-<trace-id>-<parent-span-id>-<trace-flags>
  
  示例：
  traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
  
  解析：
  - 00: 版本
  - 0af7651916cd43dd8448eb211c80319c: Trace ID (32 位)
  - b7ad6b7169203331: Parent Span ID (16 位)
  - 01: Trace Flags (01 = sampled)

  tracestate: vendor-specific-key=value
  
  示例：
  tracestate: congo=t61rcWkgMzE

传播流程：
  Service A → Service B → Service C
  │           │           │
  │  生成 Span│  创建子   │  创建子
  │  设置     │  Span     │  Span
  │  traceparent │  传播  │  传播
  │           │           │
  └───────────┴───────────┘
```

### 2. OpenTelemetry

#### 2.1 OpenTelemetry 架构

```
OpenTelemetry 架构：

┌─────────────────────────────────────────────────────────────────┐
│                    OpenTelemetry                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  应用层（SDK）                                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Traces API │ Metrics API │ Logs API                    │    │
│  │  追踪 API    │ 指标 API    │ 日志 API                    │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                    SDK 实现                               │    │
│  │  ├── TracerProvider: 创建 Tracer                         │    │
│  │  ├── MeterProvider: 创建 Meter                           │    │
│  │  ├── LoggerProvider: 创建 Logger                         │    │
│  │  ├── Resource: 服务元数据                                 │    │
│  │  ├── Sampler: 采样策略                                    │    │
│  │  └── SpanProcessor: Span 处理器                          │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                    Exporter（导出器）                      │    │
│  │  ├── OTLP Exporter (OpenTelemetry Protocol)              │    │
│  │  ├── Jaeger Exporter                                     │    │
│  │  ├── Zipkin Exporter                                     │    │
│  │  ├── Prometheus Exporter                                 │    │
│  │  └── Console Exporter (调试)                             │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │              OpenTelemetry Collector（可选）               │    │
│  │  ├── Receiver: 接收数据                                   │    │
│  │  ├── Processor: 处理数据                                  │    │
│  │  └── Exporter: 导出数据                                   │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    后端存储                                │    │
│  │  Jaeger │ Zipkin │ Prometheus │ Grafana Tempo │ ...     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 OpenTelemetry Collector 配置

```yaml
# otel-collector-config.yml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
  
  # 接收 Jaeger 格式
  jaeger:
    protocols:
      thrift_http:
        endpoint: 0.0.0.0:14268
      grpc:
        endpoint: 0.0.0.0:14250
  
  # 接收 Zipkin 格式
  zipkin:
    endpoint: 0.0.0.0:9411

processors:
  batch:
    timeout: 5s
    send_batch_size: 1024
  
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128
  
  # 添加资源属性
  resource:
    attributes:
      - key: environment
        value: production
        action: upsert
      - key: team
        value: sre
        action: insert
  
  # 尾部采样
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
      - name: errors-policy
        type: status_code
        status_code:
          status_codes: [ERROR]
      - name: slow-traces-policy
        type: latency
        latency:
          threshold_ms: 5000
      - name: probabilistic-policy
        type: probabilistic
        probabilistic:
          sampling_percentage: 10

exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true
  
  prometheus:
    endpoint: 0.0.0.0:8889
  
  logging:
    verbosity: basic

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  zpages:
    endpoint: 0.0.0.0:55679

service:
  extensions: [health_check, zpages]
  pipelines:
    traces:
      receivers: [otlp, jaeger, zipkin]
      processors: [memory_limiter, batch, tail_sampling]
      exporters: [otlp/jaeger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

### 3. Jaeger 架构

```
Jaeger 架构：

┌─────────────────────────────────────────────────────────────────┐
│                    Jaeger Architecture                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  应用层                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Service A│  │ Service B│  │ Service C│                      │
│  │ (OTel SDK)│  │ (OTel SDK)│  │ (OTel SDK)│                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │            │            │                                │
│       └────────────┴────────────┘                                │
│                    │                                              │
│                    ▼                                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              OpenTelemetry Collector                      │    │
│  │  Receiver → Processor → Exporter                        │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                    Jaeger Backend                         │    │
│  │                                                           │    │
│  │  ┌──────────────┐                                        │    │
│  │  │  jaeger-collector                                       │    │
│  │  │  接收、验证、处理追踪数据                               │    │
│  │  └──────┬───────┘                                        │    │
│  │         │                                                  │    │
│  │         ├──▶ Storage（存储后端）                          │    │
│  │         │    ├── Elasticsearch                            │    │
│  │         │    ├── Cassandra                                │    │
│  │         │    ├── Badger (嵌入式)                          │    │
│  │         │    └── Kafka (缓冲)                             │    │
│  │         │                                                  │    │
│  │  ┌──────┴───────┐                                        │    │
│  │  │  jaeger-query                                        │    │
│  │  │  查询 API + UI                                       │    │
│  │  └──────────────┘                                        │    │
│  │                                                           │    │
│  │  ┌──────────────┐                                        │    │
│  │  │  jaeger-agent                                        │    │
│  │  │  本地采集代理（可选）                                  │    │
│  │  └──────────────┘                                        │    │
│  │                                                           │    │
│  │  ┌──────────────┐                                        │    │
│  │  │  jaeger-ingester                                       │    │
│  │  │  从 Kafka 消费写入存储                                │    │
│  │  └──────────────┘                                        │    │
│  │                                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Jaeger 安装与配置

#### 4.1 Docker Compose 部署

```yaml
# docker-compose-jaeger.yml
version: '3.8'

services:
  jaeger:
    image: jaegertracing/all-in-one:1.52
    container_name: jaeger
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - SPAN_STORAGE_TYPE=elasticsearch
      - ES_SERVER_URLS=http://elasticsearch:9200
      - ES_INDEX_PREFIX=jaeger
      - ES_TAGS_AS_FIELDS_ALL=true
    ports:
      - "16686:16686"   # Jaeger UI
      - "14268:14268"   # Jaeger HTTP Thrift
      - "14250:14250"   # Jaeger gRPC
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
    networks:
      - jaeger-net

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: jaeger-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - jaeger-net

volumes:
  es-data:

networks:
  jaeger-net:
    driver: bridge
```

#### 4.2 Kubernetes 部署（Helm）

```bash
# 添加 Jaeger Helm 仓库
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update

# 安装 Jaeger
helm install jaeger jaegertracing/jaeger \
  --namespace observability \
  --create-namespace \
  --set storage.type=elasticsearch \
  --set storage.elasticsearch.host=elasticsearch-master \
  --set storage.elasticsearch.port=9200 \
  --set collector.replicas=3 \
  --set query.replicas=2 \
  --set agent.daemonset.enabled=true

# 或使用 OTel Collector 模式
helm install jaeger jaegertracing/jaeger \
  --namespace observability \
  --create-namespace \
  --set collector.replicas=3 \
  --set query.replicas=2 \
  --set storage.type=elasticsearch \
  --set storage.elasticsearch.host=elasticsearch-master \
  --set storage.elasticsearch.port=9200 \
  --set collector.service.type=ClusterIP \
  --set collector.service.grpc.port=4317 \
  --set collector.service.http.port=4318
```

### 5. 采样策略

```
采样策略对比：

┌──────────────────────────────────────────────────────────────────┐
│                    采样策略                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  1. 恒定采样（Constant Sampling）                                 │
│     ├── 全部采样：sample=true                                     │
│     ├── 全不采样：sample=false                                    │
│     └── 适用：开发环境、低流量                                    │
│                                                                    │
│  2. 概率采样（Probabilistic Sampling）                            │
│     ├── 按百分比随机采样                                          │
│     ├── 如：10% 采样率                                            │
│     └── 适用：生产环境、高流量                                    │
│                                                                    │
│  3. 速率限制采样（Rate Limiting Sampling）                        │
│     ├── 限制每秒采样数量                                          │
│     ├── 如：每秒最多 100 条                                       │
│     └── 适用：流量不均匀的场景                                    │
│                                                                    │
│  4. 自适应采样（Adaptive Sampling）                               │
│     ├── 根据流量自动调整采样率                                    │
│     ├── 保持恒定的采样数量                                        │
│     └── 适用：大规模生产环境                                      │
│                                                                    │
│  5. 尾部采样（Tail-based Sampling）                               │
│     ├── 先收集完整 Trace，再决定是否保留                          │
│     ├── 可以保留错误、慢请求等有价值的 Trace                      │
│     ├── 需要 Collector 支持                                       │
│     └── 适用：需要保留异常 Trace 的场景                           │
│                                                                    │
│  6. 头部采样（Head-based Sampling）                               │
│     ├── 在 Trace 开始时决定是否采样                               │
│     ├── 通过 traceparent header 传播                              │
│     ├── 简单高效                                                  │
│     └── 适用：一般场景                                            │
│                                                                    │
│  采样策略选择：                                                    │
│  ┌─────────────────┬────────────────────────────────────────┐   │
│  │ 场景            │ 推荐策略                                │   │
│  ├─────────────────┼────────────────────────────────────────┤   │
│  │ 开发环境        │ 全部采样                                │   │
│  │ 低流量生产      │ 全部采样或 50% 概率                     │   │
│  │ 高流量生产      │ 10% 概率 + 尾部采样保留错误             │   │
│  │ 超大规模        │ 1% 概率 + 自适应 + 尾部采样             │   │
│  └─────────────────┴────────────────────────────────────────┘   │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

```yaml
# Jaeger 采样配置
# 通过环境变量配置
environment:
  - SAMPLING_STRATEGIES_FILE=/etc/jaeger/sampling.json

# sampling.json
{
  "default_strategy": {
    "type": "probabilistic",
    "param": 0.1
  },
  "service_strategies": [
    {
      "service": "payment-service",
      "type": "probabilistic",
      "param": 0.5
    },
    {
      "service": "health-check",
      "type": "rateLimiting",
      "param": 10
    }
  ],
  "operation_strategies": [
    {
      "service": "api-gateway",
      "operation": "/health",
      "type": "probabilistic",
      "param": 0.01
    }
  ]
}
```

### 6. 与 Prometheus/Grafana 集成

```
三大支柱集成架构：

┌─────────────────────────────────────────────────────────────────┐
│                    可观测性集成                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  应用层                                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    OpenTelemetry SDK                      │    │
│  │  ├── Traces (追踪)                                       │    │
│  │  ├── Metrics (指标)                                      │    │
│  │  └── Logs (日志)                                         │    │
│  └──────┬──────────────────┬──────────────────┬─────────────┘    │
│         │                  │                  │                   │
│         ▼                  ▼                  ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ OTel Collector│  │ OTel Collector│  │ OTel Collector│           │
│  │ (Traces)     │  │ (Metrics)    │  │ (Logs)       │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                  │                   │
│         ▼                  ▼                  ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Jaeger     │  │  Prometheus  │  │    Loki      │           │
│  │   追踪存储    │  │  指标存储    │  │    日志存储    │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                  │                  │                   │
│         └──────────────────┴──────────────────┘                   │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                       Grafana                            │    │
│  │  ├── Metrics Dashboard (Prometheus)                      │    │
│  │  ├── Logs Explore (Loki)                                 │    │
│  │  ├── Traces Explore (Jaeger)                             │    │
│  │  └── Correlations (关联)                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 6.1 Grafana 中配置 Jaeger 数据源

```yaml
# Grafana 数据源配置
apiVersion: 1
datasources:
  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger-query:16686
    isDefault: false
    editable: true
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki
        filterByTraceID: true
        filterBySpanID: true
        tags: ['job']
      tracesToMetrics:
        datasourceUid: prometheus
        tags: ['job']
        queries:
          - name: Request rate
            query: sum(rate(traces_spanmetrics_calls_total{$$__tags}[5m]))
      nodeGraph:
        enabled: true
```

### 7. SRE 实战案例

#### 7.1 跨服务延迟排查

```
场景：用户反馈支付接口响应慢（> 5s），需要定位瓶颈

排查步骤：

1. 在 Jaeger UI 中搜索 payment-service 的慢 Trace
   - Service: payment-service
   - Min Duration: 5s
   - 时间范围：最近 1 小时

2. 查看 Trace 详情
   Trace ID: abc123
   Total Duration: 6.2s
   
   Span A: API Gateway → /api/pay (6.2s)
     Span B: payment-service → process_payment (5.8s)
       Span C: user-service → get_user_info (0.1s)
       Span D: order-service → get_order (0.2s)
       Span E: external-payment-gateway → charge (5.5s) ← 瓶颈
       Span F: database → insert_transaction (0.1s)

3. 根因：外部支付网关响应慢（5.5s）

4. 修复方案：
   - 设置外部调用超时（3s）
   - 实施断路器模式
   - 添加重试机制（指数退避）
   - 考虑异步支付
```

#### 7.2 错误链路追踪

```
场景：间歇性 500 错误，日志中看不到明显错误

排查步骤：

1. 在 Jaeger UI 中搜索错误 Trace
   - Service: order-service
   - Tags: error=true
   - 时间范围：最近 1 小时

2. 查看错误 Trace
   Trace ID: def456
   
   Span A: API Gateway → /api/orders (ERROR)
     Span B: order-service → create_order (ERROR)
       Span C: inventory-service → check_stock (OK)
       Span D: payment-service → charge (ERROR)
         Span E: database → update_balance (ERROR)
         → error.message: "deadlock detected"

3. 根因：数据库死锁导致支付失败

4. 修复方案：
   - 优化数据库事务顺序
   - 减少事务持有时间
   - 添加死锁重试机制
```

---

## 💻 实战练习

### 练习 1：部署 Jaeger + OTel Collector

```bash
# 步骤 1：创建配置文件
mkdir -p jaeger-lab
cd jaeger-lab

# 创建 docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  jaeger:
    image: jaegertracing/all-in-one:1.52
    environment:
      - COLLECTOR_OTLP_ENABLED=true
      - SPAN_STORAGE_TYPE=badger
      - BADGER_DIRECTORY_VALUE=/badger/data
      - BADGER_DIRECTORY_KEY=/badger/key
    ports:
      - "16686:16686"
      - "4317:4317"
      - "4318:4318"
    volumes:
      - badger-data:/badger

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.91.0
    command: ["--config=/etc/otel/config.yml"]
    volumes:
      - ./otel-config.yml:/etc/otel/config.yml
    ports:
      - "8888:8888"
      - "8889:8889"
    depends_on:
      - jaeger

volumes:
  badger-data:
EOF

# 创建 otel-config.yml
cat > otel-config.yml << 'EOF'
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s

exporters:
  otlp/jaeger:
    endpoint: jaeger:4317
    tls:
      insecure: true
  logging:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/jaeger, logging]
EOF

# 步骤 2：启动栈
docker-compose up -d

# 步骤 3：验证
curl -s "http://localhost:16686/api/services" | jq
# 应返回空列表（还没有追踪数据）
```

### 练习 2：使用 OpenTelemetry SDK 生成追踪数据

```python
# app.py - Python 示例
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
import time

# 配置资源
resource = Resource.create({
    "service.name": "demo-app",
    "service.version": "1.0.0",
    "environment": "lab"
})

# 配置 Provider
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="localhost:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# 获取 Tracer
tracer = trace.get_tracer("demo-tracer")

# 创建追踪
with tracer.start_as_current_span("main-operation") as span:
    span.set_attribute("http.method", "GET")
    span.set_attribute("http.url", "/api/test")
    
    # 子 Span 1
    with tracer.start_as_current_span("database-query") as db_span:
        db_span.set_attribute("db.system", "postgresql")
        db_span.set_attribute("db.statement", "SELECT * FROM users")
        time.sleep(0.1)  # 模拟查询
        db_span.add_event("query completed")
    
    # 子 Span 2
    with tracer.start_as_current_span("cache-lookup") as cache_span:
        cache_span.set_attribute("cache.system", "redis")
        time.sleep(0.05)  # 模拟缓存查询
    
    span.set_status(trace.StatusCode.OK)

print("Trace sent to Jaeger")
```

```bash
# 运行示例
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
python app.py

# 在 Jaeger UI 中查看追踪
open http://localhost:16686
# Service: demo-app → Find Traces
```

### 练习 3：采样策略配置

```bash
# 场景：配置差异化采样策略

# 步骤 1：创建采样配置
cat > sampling.json << 'EOF'
{
  "default_strategy": {
    "type": "probabilistic",
    "param": 0.1
  },
  "service_strategies": [
    {
      "service": "payment-service",
      "type": "probabilistic",
      "param": 0.5
    },
    {
      "service": "health-check",
      "type": "rateLimiting",
      "param": 5
    }
  ],
  "operation_strategies": [
    {
      "service": "api-gateway",
      "operation": "/health",
      "type": "probabilistic",
      "param": 0.01
    }
  ]
}
EOF

# 步骤 2：更新 docker-compose 使用采样配置
# 添加 volume 和环境变量

# 步骤 3：验证采样策略
curl -s "http://localhost:16686/api/services"
# 检查不同服务的 Trace 数量是否符合采样策略
```

---

## 🎯 面试题精选

### 1. 什么是分布式追踪？它解决了什么问题？

**答**：分布式追踪是一种用于跟踪请求在多个微服务间流转的技术。它解决了：
- 跨服务请求链路的可视化
- 定位性能瓶颈（哪个服务最慢）
- 错误传播路径追踪
- 服务依赖关系分析

### 2. Trace、Span、Context Propagation 分别是什么？

**答**：
- **Trace**：一个完整请求的端到端路径，由多个 Span 组成，有唯一的 Trace ID
- **Span**：一个操作单元，包含操作名、开始/结束时间、标签、日志等
- **Context Propagation**：将 Trace ID 和 Span ID 通过 HTTP Header 传播到下游服务，保证链路关联

### 3. 头部采样和尾部采样有什么区别？

**答**：
- **头部采样（Head-based）**：在 Trace 开始时决定是否采样，通过 Header 传播。简单高效，但可能丢失有价值的异常 Trace
- **尾部采样（Tail-based）**：先收集完整 Trace，再决定是否保留。可以保留错误、慢请求等有价值的 Trace，但需要 Collector 支持，延迟更高

### 4. OpenTelemetry 的三大信号是什么？

**答**：
- **Traces**：分布式追踪，记录请求的完整路径
- **Metrics**：指标数据，记录系统和应用的度量值
- **Logs**：日志数据，记录事件和错误信息

三者通过统一的 Resource 和 Context 关联。

### 5. Jaeger 的组件有哪些？各自的作用是什么？

**答**：
- **jaeger-agent**：本地采集代理，接收应用发送的追踪数据
- **jaeger-collector**：接收、验证、处理追踪数据，写入存储
- **jaeger-query**：提供查询 API 和 UI
- **jaeger-ingester**：从 Kafka 消费数据写入存储（可选）

### 6. 如何在微服务中实施链路追踪？

**答**：
1. 集成 OpenTelemetry SDK
2. 配置自动埋点（HTTP、数据库、消息队列）
3. 配置 Context Propagation（W3C Trace Context）
4. 部署 OTel Collector
5. 部署 Jaeger 后端
6. 在 Grafana 中配置数据源关联

### 7. 什么是 W3C Trace Context？

**答**：W3C Trace Context 是 W3C 标准化的分布式追踪上下文传播协议。通过 HTTP Header `traceparent` 和 `tracestate` 传播追踪信息，实现跨服务的链路关联。

格式：`traceparent: 00-<trace-id>-<parent-span-id>-<trace-flags>`

### 8. 如何优化 Jaeger 的存储性能？

**答**：
1. 使用 ES 作为存储后端（支持聚合查询）
2. 配置合理的索引策略（按天滚动）
3. 实施数据保留策略（自动清理旧数据）
4. 使用采样减少存储量
5. 配置 ES 的 ILM 管理 Jaeger 索引

### 9. 如何在 Grafana 中关联 Metrics、Logs、Traces？

**答**：
1. 使用相同的标签体系（job、namespace）
2. 配置 Traces to Logs（在 Jaeger 数据源中关联 Loki）
3. 配置 Traces to Metrics（在 Jaeger 数据源中关联 Prometheus）
4. 使用 Exemplar 将 Prometheus 指标链接到 Trace
5. 使用 Derived Fields 将日志中的 trace_id 链接到 Jaeger

### 10. 自动埋点和手动埋点有什么区别？

**答**：
- **自动埋点**：通过 SDK 自动拦截 HTTP 请求、数据库调用等，无需修改代码
- **手动埋点**：在代码中显式创建 Span，记录业务逻辑

最佳实践：自动埋点覆盖基础设施层，手动埋点覆盖关键业务逻辑。

---

## 📚 深入阅读

- [Jaeger 官方文档](https://www.jaegertracing.io/docs/)
- [OpenTelemetry 文档](https://opentelemetry.io/docs/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Grafana Tempo](https://grafana.com/docs/tempo/latest/)

---

## ✅ 自检清单

- [ ] 理解分布式追踪的核心概念（Trace、Span、Context Propagation）
- [ ] 掌握 OpenTelemetry 的架构和 SDK 使用
- [ ] 能够部署和配置 Jaeger
- [ ] 理解不同的采样策略及其适用场景
- [ ] 掌握 Jaeger 与 Prometheus/Grafana 的集成
- [ ] 能够使用追踪数据排查跨服务问题
- [ ] 理解 W3C Trace Context 标准
- [ ] 能够设计生产级的追踪架构
