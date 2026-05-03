# Day 145: APM 集成（应用性能监控、自动埋点、手动埋点、采样策略、服务地图、错误追踪、性能分析）

> 📅 日期：2026-05-10
> 📖 学习主题：APM 核心概念、自动/手动埋点、采样策略、服务地图、错误追踪、性能分析
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 144 (Jaeger 链路追踪), Day 134 (Prometheus), Day 136 (Grafana)

## 🎯 学习目标

- 深入理解 APM（Application Performance Monitoring）的核心概念
- 掌握自动埋点和手动埋点的实现方式
- 理解不同采样策略的实现与配置
- 能够使用服务地图分析服务依赖关系
- 掌握错误追踪和性能分析的方法
- 能够在生产环境中实施 APM 监控

---

## 📖 核心知识点

### 1. APM 概述

```
APM（Application Performance Monitoring）应用性能监控：

┌─────────────────────────────────────────────────────────────────┐
│                    APM 核心能力                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. 性能监控                                                      │
│     ├── 响应时间（Latency）                                      │
│     ├── 吞吐量（Throughput）                                     │
│     ├── 错误率（Error Rate）                                     │
│     └── 饱和度（Saturation）                                     │
│                                                                   │
│  2. 分布式追踪                                                    │
│     ├── 请求链路可视化                                           │
│     ├── 跨服务延迟分析                                           │
│     └── 错误传播追踪                                             │
│                                                                   │
│  3. 服务地图                                                      │
│     ├── 服务依赖关系                                             │
│     ├── 调用频率和延迟                                           │
│     └── 错误率热力图                                             │
│                                                                   │
│  4. 错误追踪                                                      │
│     ├── 异常捕获和聚合                                           │
│     ├── 错误上下文信息                                           │
│     └── 错误趋势分析                                             │
│                                                                   │
│  5. 性能分析                                                      │
│     ├── 代码级性能分析（Profiling）                              │
│     ├── 数据库查询分析                                           │
│     ├── 外部调用分析                                             │
│     └── 资源使用分析                                             │
│                                                                   │
│  APM 工具对比：                                                   │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐ │
│  │ 工具         │ 类型         │ 优势         │ 劣势         │ │
│  ├──────────────┼──────────────┼──────────────┼──────────────┤ │
│  │ Elastic APM  │ 开源         │ ELK 集成     │ 资源消耗大   │ │
│  │ Jaeger       │ 开源(CNCF)   │ K8s 生态     │ 功能有限     │ │
│  │ Grafana Tempo│ 开源         │ 低成本       │ 功能简单     │ │
│  │ Datadog APM  │ 商业         │ 功能全面     │ 成本高       │ │
│  │ New Relic    │ 商业         │ 易用         │ 成本高       │ │
│  └──────────────┴──────────────┴──────────────┴──────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. 自动埋点（Auto-Instrumentation）

#### 2.1 自动埋点原理

```
自动埋点工作原理：

┌─────────────────────────────────────────────────────────────────┐
│                    自动埋点机制                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. 字节码注入（Java/Go/.NET）                                   │
│     ├── 在类加载时注入追踪代码                                   │
│     ├── 拦截方法调用                                             │
│     └── 无需修改业务代码                                         │
│                                                                   │
│  2. Monkey Patching（Python/Node.js）                            │
│     ├── 替换标准库函数                                           │
│     ├── 拦截 HTTP 请求/响应                                      │
│     └── 自动创建 Span                                            │
│                                                                   │
│  3. HTTP Header 解析                                             │
│     ├── 解析 traceparent header                                  │
│     ├── 提取 Trace ID 和 Span ID                                │
│     └── 创建子 Span                                              │
│                                                                   │
│  自动埋点覆盖范围：                                               │
│  ├── HTTP 客户端（requests, urllib, axios）                      │
│  ├── HTTP 服务器（Flask, Django, Express）                       │
│  ├── 数据库（MySQL, PostgreSQL, Redis, MongoDB）                 │
│  ├── 消息队列（Kafka, RabbitMQ, SQS）                            │
│  ├── RPC 框架（gRPC, Thrift）                                    │
│  └── 模板引擎（Jinja2, EJS）                                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 Python 自动埋点

```python
# Python 自动埋点配置

# 安装依赖
# pip install opentelemetry-distro opentelemetry-exporter-otlp
# opentelemetry-bootstrap -a install  # 安装所有自动埋点包

# app.py
from flask import Flask
import requests
import psycopg2

app = Flask(__name__)

@app.route('/api/users/<user_id>')
def get_user(user_id):
    # 自动埋点会创建以下 Span：
    # 1. HTTP Server Span (Flask)
    # 2. DB Span (PostgreSQL)
    # 3. HTTP Client Span (requests)
    
    conn = psycopg2.connect("postgresql://localhost/mydb")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id))
    user = cursor.fetchone()
    
    # 调用外部服务
    response = requests.get(f"http://order-service/api/orders?user_id={user_id}")
    
    return {"user": user, "orders": response.json()}

if __name__ == '__main__':
    app.run(port=5000)
```

```bash
# 启动自动埋点
# 方式 1：使用 opentelemetry-instrument 命令
opentelemetry-instrument \
  --service_name my-flask-app \
  --exporter_otlp_endpoint http://localhost:4317 \
  --exporter_otlp_protocol grpc \
  python app.py

# 方式 2：使用环境变量
export OTEL_SERVICE_NAME=my-flask-app
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_TRACES_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_PYTHON_FLASK_EXCLUDED_URLS="healthcheck,metrics"
python app.py

# 方式 3：代码方式
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

# 配置 Provider
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="localhost:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# 自动埋点
FlaskInstrumentor().instrument()
RequestsInstrumentor().instrument()
Psycopg2Instrumentor().instrument()
```

#### 2.3 Java 自动埋点

```bash
# Java 自动埋点（使用 Java Agent）

# 下载 OpenTelemetry Java Agent
curl -L -O https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar

# 启动应用
java -javaagent:opentelemetry-javaagent.jar \
  -Dotel.service.name=my-java-app \
  -Dotel.exporter.otlp.endpoint=http://localhost:4317 \
  -Dotel.exporter.otlp.protocol=grpc \
  -Dotel.traces.sampler=parentbased_traceidratio \
  -Dotel.traces.sampler.arg=0.1 \
  -jar my-app.jar

# 环境变量方式
export OTEL_SERVICE_NAME=my-java-app
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_TRACES_SAMPLER=parentbased_traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1
java -javaagent:opentelemetry-javaagent.jar -jar my-app.jar
```

#### 2.4 Node.js 自动埋点

```javascript
// tracing.js - 初始化自动埋点
'use strict';

const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-grpc');
const { PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');

const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'my-node-app',
    [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
  }),
  traceExporter: new OTLPTraceExporter({
    url: 'http://localhost:4317',
  }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: 'http://localhost:4317',
    }),
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
```

```bash
# 启动应用
node -r ./tracing.js app.js
```

### 3. 手动埋点（Manual Instrumentation）

#### 3.1 手动埋点场景

```
何时需要手动埋点：

┌─────────────────────────────────────────────────────────────────┐
│                    手动埋点场景                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. 业务逻辑追踪                                                  │
│     ├── 订单创建流程                                             │
│     ├── 支付处理流程                                             │
│     └── 用户注册流程                                             │
│                                                                   │
│  2. 自定义组件                                                    │
│     ├── 内部 RPC 框架                                           │
│     ├── 自定义缓存层                                             │
│     └── 私有协议客户端                                           │
│                                                                   │
│  3. 关键业务指标                                                  │
│     ├── 订单金额                                                 │
│     ├── 用户 ID                                                  │
│     └── 业务状态                                                 │
│                                                                   │
│  4. 错误上下文                                                    │
│     ├── 捕获业务异常                                             │
│     ├── 记录错误原因                                             │
│     └── 添加调试信息                                             │
│                                                                   │
│  5. 性能关键路径                                                  │
│     ├── 算法执行时间                                             │
│     ├── 数据处理时间                                             │
│     └── 第三方 API 调用时间                                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 Python 手动埋点

```python
from opentelemetry import trace
from opentelemetry.trace import StatusCode

tracer = trace.get_tracer("order-service")

def create_order(user_id, items):
    with tracer.start_as_current_span("create_order") as span:
        # 添加业务标签
        span.set_attribute("user_id", user_id)
        span.set_attribute("item_count", len(items))
        span.set_attribute("order_type", "standard")
        
        try:
            # 验证库存
            with tracer.start_as_current_span("validate_inventory") as inv_span:
                inv_span.set_attribute("items", str(items))
                validate_inventory(items)
                inv_span.add_event("inventory_validated")
            
            # 计算价格
            with tracer.start_as_current_span("calculate_price") as price_span:
                total = calculate_price(items)
                price_span.set_attribute("total_amount", total)
                price_span.set_attribute("currency", "CNY")
            
            # 创建支付
            with tracer.start_as_current_span("create_payment") as pay_span:
                payment_id = process_payment(user_id, total)
                pay_span.set_attribute("payment_id", payment_id)
                pay_span.set_attribute("payment_method", "alipay")
            
            # 记录成功事件
            span.add_event("order_created", {
                "order_id": order_id,
                "total_amount": total
            })
            
            span.set_status(StatusCode.OK)
            return order_id
            
        except InsufficientInventoryError as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            span.set_attribute("error.type", "inventory_error")
            raise
        except PaymentError as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.record_exception(e)
            span.set_attribute("error.type", "payment_error")
            raise
```

#### 3.3 Go 手动埋点

```go
package main

import (
    "context"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/codes"
    "go.opentelemetry.io/otel/trace"
)

var tracer = otel.Tracer("order-service")

func CreateOrder(ctx context.Context, userID string, items []Item) (string, error) {
    ctx, span := tracer.Start(ctx, "create_order",
        trace.WithAttributes(
            attribute.String("user_id", userID),
            attribute.Int("item_count", len(items)),
        ),
    )
    defer span.End()

    // 验证库存
    if err := validateInventory(ctx, items); err != nil {
        span.SetStatus(codes.Error, "inventory validation failed")
        span.RecordError(err)
        return "", err
    }

    // 计算价格
    total := calculatePrice(ctx, items)
    span.SetAttributes(
        attribute.Float64("total_amount", total),
        attribute.String("currency", "CNY"),
    )

    // 创建支付
    paymentID, err := processPayment(ctx, userID, total)
    if err != nil {
        span.SetStatus(codes.Error, "payment failed")
        span.RecordError(err)
        return "", err
    }

    span.AddEvent("order_created", trace.WithAttributes(
        attribute.String("payment_id", paymentID),
    ))

    return paymentID, nil
}
```

### 4. 服务地图（Service Map）

```
服务地图可视化：

┌─────────────────────────────────────────────────────────────────┐
│                    服务地图                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│                    ┌──────────────┐                              │
│                    │  API Gateway │                              │
│                    │  RPS: 1000   │                              │
│                    │  P99: 50ms   │                              │
│                    └──────┬───────┘                              │
│                           │                                      │
│           ┌───────────────┼───────────────┐                     │
│           │               │               │                      │
│           ▼               ▼               ▼                      │
│    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│    │ User Service │ │Order Service │ │Payment Svc   │          │
│    │ RPS: 500     │ │ RPS: 300     │ │ RPS: 200     │          │
│    │ P99: 30ms    │ │ P99: 100ms   │ │ P99: 200ms   │          │
│    │ Err: 0.1%    │ │ Err: 0.5%    │ │ Err: 1.0%    │          │
│    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘          │
│           │               │               │                      │
│           ▼               ▼               ▼                      │
│    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│    │  PostgreSQL  │ │    Redis     │ │  3rd Party   │          │
│    │  RPS: 500    │ │  RPS: 1000   │ │  RPS: 200    │          │
│    │  P99: 10ms   │ │  P99: 5ms    │ │  P99: 500ms  │          │
│    └──────────────┘ └──────────────┘ └──────────────┘          │
│                                                                   │
│  图例：                                                          │
│  ──── 正常连接（错误率 < 1%）                                    │
│  ---- 警告连接（错误率 1-5%）                                    │
│  ···· 异常连接（错误率 > 5%）                                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 5. 错误追踪（Error Tracking）

```
错误追踪的核心能力：

┌─────────────────────────────────────────────────────────────────┐
│                    错误追踪                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. 错误聚合                                                      │
│     ├── 按错误类型聚合                                           │
│     ├── 按服务聚合                                               │
│     ├── 按时间聚合                                               │
│     └── 按影响用户聚合                                           │
│                                                                   │
│  2. 错误上下文                                                    │
│     ├── 请求参数                                                 │
│     ├── 用户信息                                                 │
│     ├── 环境信息                                                 │
│     └── 调用栈                                                   │
│                                                                   │
│  3. 错误趋势                                                      │
│     ├── 错误数量趋势                                             │
│     ├── 错误率趋势                                               │
│     └── 新增错误检测                                             │
│                                                                   │
│  4. 错误关联                                                      │
│     ├── 关联到 Trace                                             │
│     ├── 关联到日志                                               │
│     └── 关联到指标                                               │
│                                                                   │
│  错误追踪配置示例：                                               │
│                                                                   │
│  # Python 错误追踪                                                │
│  try:                                                            │
│      result = process_order(order)                               │
│  except Exception as e:                                          │
│      span.record_exception(e)                                    │
│      span.set_status(StatusCode.ERROR, str(e))                   │
│      # 发送到错误追踪系统                                        │
│      capture_exception(e, context={                              │
│          "order_id": order_id,                                   │
│          "user_id": user_id,                                     │
│          "items": items                                          │
│      })                                                          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 6. 性能分析（Profiling）

```
持续性能分析（Continuous Profiling）：

┌─────────────────────────────────────────────────────────────────┐
│                    性能分析                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. CPU Profiling                                                 │
│     ├── 火焰图（Flame Graph）                                    │
│     ├── 热点函数识别                                             │
│     └── CPU 使用率分析                                           │
│                                                                   │
│  2. Memory Profiling                                              │
│     ├── 内存分配分析                                             │
│     ├── 内存泄漏检测                                             │
│     └── GC 压力分析                                              │
│                                                                   │
│  3. Goroutine/Thread Profiling                                    │
│     ├── 协程/线程数量                                            │
│     ├── 阻塞分析                                                 │
│     └── 死锁检测                                                 │
│                                                                   │
│  4. 工具推荐：                                                    │
│     ├── Pyroscope（持续性能分析）                                │
│     ├── Grafana Pyroscope                                        │
│     ├── pprof（Go）                                              │
│     ├── async-profiler（Java）                                   │
│     └── py-spy（Python）                                         │
│                                                                   │
│  火焰图示例：                                                     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Flame Graph                            │    │
│  │                                                           │    │
│  │  ┌─────────────────────────────────────┐                │    │
│  │  │            main (100%)              │                │    │
│  │  ├──────────┬──────────┬───────────────┤                │    │
│  │  │ process  │  query  │   render      │                │    │
│  │  │ (40%)    │ (35%)   │   (25%)       │                │    │
│  │  ├──────────┼──────────┼───────────────┤                │    │
│  │  │ validate │  db     │   template    │                │    │
│  │  │ (20%)    │ (25%)   │   (15%)       │                │    │
│  │  │ calculate│  cache  │   serialize   │                │    │
│  │  │ (20%)    │ (10%)   │   (10%)       │                │    │
│  │  └──────────┴──────────┴───────────────┘                │    │
│  │                                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 7. Elastic APM 集成

#### 7.1 Elastic APM 架构

```
Elastic APM 架构：

┌─────────────────────────────────────────────────────────────────┐
│                    Elastic APM                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  应用层                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ APM Agent│  │ APM Agent│  │ APM Agent│                      │
│  │ (Java)   │  │ (Python) │  │ (Node.js)│                      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
│       │            │            │                                │
│       └────────────┴────────────┘                                │
│                    │                                              │
│                    ▼                                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    APM Server                             │    │
│  │  ├── 接收追踪数据                                        │    │
│  │  ├── 处理和转换                                          │    │
│  │  └── 写入 Elasticsearch                                  │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Elasticsearch                          │    │
│  │  ├── apm-*-span-* (Span 数据)                           │    │
│  │  ├── apm-*-transaction-* (Transaction 数据)              │    │
│  │  ├── apm-*-metric-* (指标数据)                           │    │
│  │  └── apm-*-error-* (错误数据)                            │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Kibana                                 │    │
│  │  ├── APM UI: 服务地图、追踪查看、错误分析                │    │
│  │  ├── 服务指标: 响应时间、吞吐量、错误率                  │    │
│  │  └── 依赖分析: 服务间调用关系                            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 7.2 Elastic APM Python Agent

```python
# 安装
# pip install elastic-apm

# Flask 应用
from flask import Flask
import elasticapm
from elasticapm.contrib.flask import ElasticAPM

app = Flask(__name__)

# 配置 APM
app.config['ELASTIC_APM'] = {
    'SERVICE_NAME': 'my-flask-app',
    'SECRET_TOKEN': '',
    'SERVER_URL': 'http://localhost:8200',
    'ENVIRONMENT': 'production',
    'CAPTURE_BODY': 'all',
    'TRANSACTION_SAMPLE_RATE': 0.1,
}

apm = ElasticAPM(app)

@app.route('/api/users/<user_id>')
def get_user(user_id):
    # 自动追踪 HTTP 请求
    
    # 手动追踪自定义操作
    with elasticapm.capture_span('validate_user', 'validation'):
        validate_user(user_id)
    
    # 追踪数据库查询
    with elasticapm.capture_span('db_query', 'db', 'postgresql'):
        user = db.query(User).get(user_id)
    
    # 记录自定义指标
    elasticapm.set_custom_context({'user_id': user_id})
    
    return user

@app.errorhandler(Exception)
def handle_error(e):
    # 自动捕获异常
    elasticapm.capture_exception()
    return str(e), 500
```

### 8. Grafana APM 集成

```
Grafana 全栈 APM 方案：

┌─────────────────────────────────────────────────────────────────┐
│                    Grafana APM Stack                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  应用 → OTel SDK → OTel Collector                                │
│                        │                                          │
│          ┌─────────────┼─────────────┐                          │
│          ▼             ▼             ▼                           │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│    │  Tempo   │  │Prometheus│  │   Loki   │                    │
│    │  追踪    │  │  指标    │  │  日志    │                    │
│    └────┬─────┘  └────┬─────┘  └────┬─────┘                    │
│         │             │             │                            │
│         └─────────────┼─────────────┘                           │
│                       │                                          │
│                       ▼                                          │
│    ┌─────────────────────────────────────────────────────────┐ │
│    │                      Grafana                             │ │
│    │  ├── Explore: Traces (Tempo)                            │ │
│    │  ├── Explore: Logs (Loki)                               │ │
│    │  ├── Explore: Metrics (Prometheus)                      │ │
│    │  ├── Service Map (Tempo)                                │ │
│    │  ├── Exemplar Links (Prometheus → Tempo)                │ │
│    │  └── Trace to Logs (Tempo → Loki)                       │ │
│    └─────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Grafana Tempo 特点：                                            │
│  ├── 只索引 Trace ID（低成本）                                   │
│  ├── 使用对象存储（S3/GCS）                                      │
│  ├── 支持 TraceQL 查询语言                                       │
│  └── 与 Prometheus/Loki 深度集成                                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 9. SRE 实战案例

#### 9.1 性能瓶颈定位

```
场景：API 响应时间从 200ms 升到 2s，需要定位瓶颈

排查步骤：

1. 查看 APM 服务概览
   → 发现 payment-service 的 P99 延迟从 300ms 升到 3s

2. 查看慢 Trace
   → 找到一个 3.5s 的 Trace
   
   Trace 分解：
   API Gateway: 50ms
   payment-service: 3.2s
     ├── validate_request: 10ms
     ├── check_fraud: 50ms
     ├── charge_payment: 3.1s  ← 瓶颈
     │     ├── call_stripe_api: 3.0s  ← 外部 API 慢
     │     └── update_database: 100ms
     └── send_notification: 20ms

3. 根因：第三方支付 API（Stripe）响应慢

4. 修复方案：
   - 设置 Stripe API 超时（2s）
   - 实施断路器（50% 错误率时断路）
   - 添加异步支付确认
   - 监控 Stripe API 的响应时间
```

#### 9.2 内存泄漏检测

```
场景：Java 服务内存持续增长，最终 OOM

排查步骤：

1. 查看 APM 指标
   → 发现 heap 使用率持续增长
   → 每小时增长约 100MB

2. 查看 Profiling 数据
   → 火焰图显示 HashMap.put 占用 40% CPU

3. 分析代码
   → 发现缓存未设置过期时间
   → 缓存对象不断累积

4. 修复：
   - 使用 Caffeine 缓存替代 HashMap
   - 设置最大容量和过期时间
   - 监控缓存命中率
```

---

## 💻 实战练习

### 练习 1：部署 Elastic APM

```bash
# 步骤 1：使用 Docker 部署 APM Server
docker run -d --name apm-server \
  -p 8200:8200 \
  -e ELASTICSEARCH_HOSTS=http://elasticsearch:9200 \
  docker.elastic.co/apm/apm-server:8.11.0

# 步骤 2：配置 Python 应用
pip install elastic-apm[flask]

# 步骤 3：修改 Flask 应用
# 添加 APM 配置（参考前面的示例）

# 步骤 4：验证
curl http://localhost:8200/
# 应返回 APM Server 信息
```

### 练习 2：OpenTelemetry 全栈集成

```bash
# 目标：部署 OTel + Jaeger + Prometheus + Grafana 全栈

# 步骤 1：创建 docker-compose.yml
# 包含：OTel Collector、Jaeger、Prometheus、Grafana

# 步骤 2：配置 OTel Collector
# 接收 OTLP 数据
# 导出到 Jaeger（Traces）和 Prometheus（Metrics）

# 步骤 3：部署示例应用
# 使用自动埋点

# 步骤 4：在 Grafana 中配置数据源
# 添加 Jaeger、Prometheus 数据源
# 配置 Exemplar 关联

# 步骤 5：验证
# 在 Grafana Explore 中查看 Traces 和 Metrics
```

### 练习 3：服务地图分析

```bash
# 场景：分析微服务依赖关系

# 步骤 1：部署多个微服务
# user-service、order-service、payment-service

# 步骤 2：生成流量
# 使用 curl 或 hey 生成请求

# 步骤 3：在 Jaeger/Grafana 中查看服务地图
# 分析服务间的调用关系
# 识别高延迟和高错误率的服务

# 步骤 4：优化建议
# 根据服务地图提出优化建议
```

---

## 🎯 面试题精选

### 1. 什么是 APM？它的核心能力有哪些？

**答**：APM（Application Performance Monitoring）是应用性能监控，核心能力包括：
- 性能监控（响应时间、吞吐量、错误率）
- 分布式追踪（请求链路可视化）
- 服务地图（服务依赖关系）
- 错误追踪（异常捕获和聚合）
- 性能分析（代码级 Profiling）

### 2. 自动埋点和手动埋点有什么区别？什么时候用哪个？

**答**：
- **自动埋点**：通过 SDK 自动拦截 HTTP、数据库等调用，无需修改代码，覆盖基础设施层
- **手动埋点**：在代码中显式创建 Span，记录业务逻辑和关键指标

最佳实践：自动埋点覆盖基础设施层（HTTP、DB、Cache），手动埋点覆盖关键业务逻辑（订单创建、支付处理）。

### 3. 如何设计合理的采样策略？

**答**：
- **开发环境**：100% 采样（全量采集）
- **低流量生产**：50-100% 采样
- **高流量生产**：10% 概率采样 + 尾部采样保留错误
- **超大规模**：1% 概率采样 + 自适应采样 + 尾部采样

关键：确保错误和慢请求被采样到。

### 4. 什么是火焰图？如何使用它定位性能瓶颈？

**答**：火焰图是一种可视化 CPU 使用的图表，横轴表示采样比例，纵轴表示调用栈深度。使用方法：
1. 找到最宽的函数（占用 CPU 最多）
2. 从下往上看调用链路
3. 优化热点函数

### 5. 如何在 Grafana 中实现全栈可观测性？

**答**：
1. 使用 OpenTelemetry SDK 采集 Traces、Metrics、Logs
2. 部署 OTel Collector 处理和路由数据
3. 使用 Tempo 存储 Traces，Prometheus 存储 Metrics，Loki 存储 Logs
4. 在 Grafana 中配置数据源关联（Exemplar、Trace to Logs）
5. 创建统一的 Dashboard 展示三大支柱数据

### 6. 什么是尾部采样？它解决了什么问题？

**答**：尾部采样（Tail-based Sampling）是在 Trace 完成后再决定是否保留。它解决了头部采样可能丢失有价值的异常 Trace 的问题。通过 OTel Collector 的 tail_sampling processor 实现，可以配置保留错误、慢请求等策略。

### 7. 如何使用 APM 排查跨服务性能问题？

**答**：
1. 在 APM 中搜索慢 Trace（设置最小持续时间）
2. 查看 Trace 详情，分析各 Span 的耗时
3. 找到最慢的 Span（瓶颈）
4. 分析瓶颈原因（外部调用、数据库查询、计算密集）
5. 针对性优化（超时设置、断路器、缓存、异步处理）

### 8. 什么是持续性能分析（Continuous Profiling）？

**答**：持续性能分析是在生产环境中持续收集应用的 CPU、内存、协程等 Profiling 数据。通过火焰图等可视化方式定位性能瓶颈。工具包括 Pyroscope、Grafana Pyroscope、pprof 等。

### 9. 如何监控第三方 API 的性能？

**答**：
1. 使用自动埋点拦截 HTTP 客户端调用
2. 记录响应时间、状态码、错误信息
3. 设置超时和断路器
4. 在 APM 中创建专门的 Dashboard
5. 配置告警（响应时间 > 阈值、错误率 > 阈值）

### 10. Elastic APM 和 Grafana Tempo 有什么区别？

**答**：
- **Elastic APM**：功能全面，包括服务地图、错误追踪、Profiling，与 ELK 深度集成，但资源消耗大
- **Grafana Tempo**：轻量级追踪存储，只索引 Trace ID，成本低，与 Prometheus/Loki 深度集成，但功能相对简单

---

## 📚 深入阅读

- [OpenTelemetry 文档](https://opentelemetry.io/docs/)
- [Elastic APM 文档](https://www.elastic.co/guide/en/apm/guide/current/index.html)
- [Grafana Tempo 文档](https://grafana.com/docs/tempo/latest/)
- [Pyroscope 文档](https://pyroscope.io/docs/)

---

## ✅ 自检清单

- [ ] 理解 APM 的核心能力和价值
- [ ] 掌握自动埋点的配置和使用
- [ ] 掌握手动埋点的最佳实践
- [ ] 理解不同采样策略的适用场景
- [ ] 能够使用服务地图分析依赖关系
- [ ] 掌握错误追踪和性能分析方法
- [ ] 能够在生产环境中实施 APM
- [ ] 理解 Elastic APM 和 Grafana Tempo 的区别
