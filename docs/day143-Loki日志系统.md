# Day 143: Loki 日志系统（架构、LogQL、Promtail、与 Prometheus 集成、标签设计、保留策略、vs ELK 对比）

> 📅 日期：2026-05-08
> 📖 学习主题：Grafana Loki 架构设计、LogQL 查询语言、Promtail 采集、标签策略、与 ELK 对比
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 134 (Prometheus 基础), Day 136 (Grafana 可视化), Day 140 (Elasticsearch)

## 🎯 学习目标

- 深入理解 Loki 的架构设计与核心理念
- 掌握 LogQL 查询语言的语法和高级用法
- 能够配置 Promtail 采集日志
- 理解 Loki 的标签设计策略
- 掌握 Loki 的存储与保留策略配置
- 能够对比 Loki 和 ELK 并做出选型决策

---

## 📖 核心知识点

### 1. Loki 概述与设计理念

```
Loki 的核心理念："Like Prometheus, but for logs"

┌─────────────────────────────────────────────────────────────────┐
│                    Loki 设计哲学                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  传统日志系统（ELK）：                                            │
│  ├── 全文索引 → 存储成本高                                        │
│  ├── 索引构建 → 写入延迟大                                        │
│  └── 独立体系 → 与指标/链路分离                                   │
│                                                                   │
│  Loki 的创新：                                                    │
│  ├── 只索引标签（Label）→ 存储成本低                              │
│  ├── 不索引日志内容 → 写入速度快                                  │
│  ├── 使用标签查询 → 与 Prometheus 一致                            │
│  ├── 对象存储 → 成本低、可扩展                                    │
│  └── 与 Grafana 深度集成 → 统一可观测                             │
│                                                                   │
│  核心原则：                                                       │
│  1. 标签即索引（Labels are the index）                            │
│  2. 日志内容不索引，查询时过滤                                    │
│  3. 与 Prometheus 共享标签体系                                    │
│  4. 对象存储友好（S3、GCS、MinIO）                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Loki 架构

```
Loki 微服务架构：

┌─────────────────────────────────────────────────────────────────┐
│                    Loki 架构                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  数据采集层                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Promtail │  │Fluent Bit│  │  Vector  │  │ OTel     │       │
│  │  (官方)   │  │  (CNCF)  │  │(Datadog) │  │Collector │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │            │            │            │                   │
│       └────────────┴────────────┴────────────┘                   │
│                        │                                          │
│                        ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Loki (API Gateway)                     │    │
│  │  接收日志、路由到对应组件                                  │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                              │                                    │
│        ┌─────────────────────┼─────────────────────┐            │
│        ▼                     ▼                     ▼            │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐          │
│  │Distributor│        │ Ingester │        │ Querier  │          │
│  │  分发器    │───────▶│  写入器   │        │  查询器   │          │
│  │          │        │          │        │          │          │
│  │ 验证标签  │        │ 压缩日志  │        │ 执行 LogQL│          │
│  │ 路由到环  │        │ 构建块    │        │ 聚合结果  │          │
│  └──────────┘        └────┬─────┘        └────┬─────┘          │
│                            │                    │                 │
│                            ▼                    ▼                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Storage Layer                          │    │
│  │                                                           │    │
│  │  ┌─────────────┐    ┌─────────────┐                     │    │
│  │  │  Index Store │    │  Chunk Store│                     │    │
│  │  │  (标签索引)   │    │  (日志块)    │                     │    │
│  │  │             │    │             │                     │    │
│  │  │  - BoltDB   │    │  - S3       │                     │    │
│  │  │  - TSDB     │    │  - GCS      │                     │    │
│  │  │  - Cassandra│    │  - Azure    │                     │    │
│  │  │  - DynamoDB │    │  - Cassandra│                     │    │
│  │  └─────────────┘    └─────────────┘                     │    │
│  │                                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  组件职责：                                                       │
│  ├── Distributor：接收日志流，验证标签，路由到 Ingester           │
│  ├── Ingester：压缩日志为块，写入存储                             │
│  ├── Querier：执行 LogQL 查询，从存储读取日志                    │
│  ├── Query Frontend（可选）：查询缓存、拆分查询                  │
│  └── Compactor（可选）：压缩索引、清理过期数据                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3. 安装与配置

#### 3.1 Docker Compose 部署

```yaml
# docker-compose-loki.yml
version: '3.8'

services:
  loki:
    image: grafana/loki:2.9.0
    container_name: loki
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yml:/etc/loki/local-config.yaml
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - loki-net

  promtail:
    image: grafana/promtail:2.9.0
    container_name: promtail
    volumes:
      - ./promtail-config.yml:/etc/promtail/config.yml
      - /var/log:/var/log
      - promtail-positions:/positions
    command: -config.file=/etc/promtail/config.yml
    networks:
      - loki-net

  grafana:
    image: grafana/grafana:10.2.0
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - loki-net

volumes:
  loki-data:
  promtail-positions:
  grafana-data:

networks:
  loki-net:
    driver: bridge
```

#### 3.2 Loki 配置文件

```yaml
# loki-config.yml - 单节点模式
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: info

common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

ingester:
  chunk_idle_period: 5m
  chunk_retain_period: 30s
  max_chunk_age: 2h
  wal:
    enabled: true
    dir: /loki/wal
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1

schema_config:
  configs:
    - from: "2024-01-01"
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

storage_config:
  filesystem:
    directory: /loki/chunks

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h    # 7 天
  max_query_length: 721h              # 30 天
  max_query_series: 10000
  max_query_parallelism: 32
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
  per_stream_rate_limit: 5MB
  per_stream_rate_limit_burst: 15MB
  max_entries_limit_per_query: 5000

compactor:
  working_directory: /loki/compactor
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150

analytics:
  reporting_enabled: false
```

#### 3.3 生产级 Loki 配置（S3 存储）

```yaml
# loki-config-prod.yml - 生产环境
auth_enabled: true

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: warn

distributor:
  ring:
    kvstore:
      store: consul
      consul:
        host: consul:8500

ingester:
  chunk_idle_period: 30m
  chunk_retain_period: 1m
  max_chunk_age: 2h
  wal:
    enabled: true
    dir: /loki/wal
    flush_on_shutdown: true
  lifecycler:
    ring:
      kvstore:
        store: consul
      replication_factor: 3

schema_config:
  configs:
    - from: "2024-01-01"
      store: tsdb
      object_store: s3
      schema: v13
      index:
        prefix: loki_index_
        period: 24h

storage_config:
  aws:
    s3: s3://us-east-1/loki-chunks
    s3forcepathstyle: true
    bucketnames: loki-chunks
    region: us-east-1
    access_key_id: ${AWS_ACCESS_KEY_ID}
    secret_access_key: ${AWS_SECRET_ACCESS_KEY}
  tsdb_shipper:
    active_index_directory: /loki/tsdb-index
    cache_location: /loki/tsdb-cache
    shared_store: s3

limits_config:
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  max_query_length: 721h
  ingestion_rate_mb: 20
  ingestion_burst_size_mb: 40
  per_stream_rate_limit: 10MB
  per_stream_rate_limit_burst: 30MB

compactor:
  working_directory: /loki/compactor
  shared_store: s3
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 256
```

### 4. LogQL 查询语言

#### 4.1 LogQL 基础语法

```
LogQL 查询语法：

┌─────────────────────────────────────────────────────────────────┐
│                    LogQL 查询结构                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  查询 = Log Stream Selector + Log Pipeline                       │
│                                                                   │
│  Log Stream Selector（日志流选择器）：                            │
│  ├── 选择哪些日志流                                              │
│  ├── 使用标签过滤                                                │
│  └── 类似 Prometheus 的标签选择器                                │
│                                                                   │
│  Log Pipeline（日志管道）：                                       │
│  ├── 对日志内容进行过滤                                          │
│  ├── 解析、提取字段                                              │
│  └── 可选，不加则返回原始日志                                    │
│                                                                   │
│  示例：                                                          │
│  {app="nginx", env="prod"} |= "error" | logfmt | status >= 500 │
│  ├── Log Stream Selector ──┘    │       │       │              │
│  ├── Line Filter ────────────────┘       │       │              │
│  ├── Parser ─────────────────────────────┘       │              │
│  └── Label Filter ───────────────────────────────┘              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 4.2 Log Stream Selector

```bash
# 精确匹配
{app="nginx"}
{app="nginx", env="production"}

# 正则匹配
{app=~"nginx|apache"}
{app=~"web-.*"}
{env!~"dev|staging"}

# 不等于
{app!="nginx"}

# 组合
{app="nginx", env="production", host=~"web-0[1-3]"}
```

#### 4.3 Line Filter（行过滤器）

```bash
# 包含
{app="nginx"} |= "error"
{app="nginx"} |= "timeout" |= "connection"

# 不包含
{app="nginx"} != "healthcheck"
{app="nginx"} != "GET /health"

# 正则匹配
{app="nginx"} |~ "status=[45]\\d{2}"
{app="nginx"} |~ "error|exception|panic"

# 正则不匹配
{app="nginx"} !~ "healthcheck|ready"

# 组合过滤
{app="nginx"} |= "error" != "healthcheck" |~ "status=5\\d{2}"
```

#### 4.4 Parser（解析器）

```bash
# JSON 解析
{app="nginx"} | json
{app="nginx"} | json | status >= 500

# Logfmt 解析
{app="payment"} | logfmt
{app="payment"} | logfmt | duration > 1s

# Pattern 解析（自定义模式）
{app="nginx"} | pattern `<ip> - - [<ts>] "<method> <path> <_>" <status> <size>`
{app="nginx"} | pattern `<ip> - - [<ts>] "<method> <path> <_>" <status> <size>` | status >= 500

# Regexp 解析
{app="nginx"} | regexp `(?P<ip>\\S+) .* "(?P<method>\\S+) (?P<path>\\S+)"`

# Unpack 解析（嵌套 JSON）
{app="nginx"} | unpack

# Label Format（重命名标签）
{app="nginx"} | json | label_format status_code="status"
```

#### 4.5 Label Filter（标签过滤器）

```bash
# 数值比较
{app="nginx"} | json | status >= 500
{app="nginx"} | json | bytes > 1024
{app="nginx"} | json | response_time < 0.1

# 字符串比较
{app="nginx"} | json | method = "POST"
{app="nginx"} | json | method != "GET"
{app="nginx"} | json | path =~ "/api/.*"
{app="nginx"} | json | path !~ "/health"

# Duration 比较
{app="nginx"} | logfmt | duration > 1s
{app="nginx"} | logfmt | duration > 500ms

# Bytes 比较
{app="nginx"} | logfmt | size > 10MB
```

#### 4.6 聚合查询

```bash
# 计数
count_over_time({app="nginx"} |= "error" [5m])
count_over_time({app="nginx"} |= "error" [1h]) by (host)

# 速率
rate({app="nginx"} |= "error" [5m])
rate({app="nginx"}[5m])

# 每秒速率
rate({app="nginx"} |= "error" [1m]) by (host)

# 聚合
sum(count_over_time({app="nginx"} |= "error" [5m]))
sum(rate({app="nginx"}[5m])) by (host)
avg(rate({app="nginx"}[5m])) by (host)
max(count_over_time({app="nginx"}[5m])) by (host)
min(count_over_time({app="nginx"}[5m])) by (host)

# Top K
topk(5, sum(rate({app="nginx"}[5m])) by (host))

# Bottom K
bottomk(5, sum(rate({app="nginx"}[5m])) by (host))

# 排序
sort_desc(sum(rate({app="nginx"}[5m])) by (host))
```

#### 4.7 解析后的数值查询

```bash
# 从 JSON 日志中提取数值并计算
# 示例日志：{"status": 500, "response_time": 1.5, "service": "payment"}

# 统计错误率
sum(rate({app="payment"} | json | status >= 500 [5m]))
/
sum(rate({app="payment"} | json [5m]))

# 统计 P99 延迟
quantile_over_time(0.99, {app="payment"} | json | unwrap response_time [5m])

# 统计平均响应时间
avg_over_time({app="payment"} | json | unwrap response_time [5m]) by (service)

# 统计最大响应时间
max_over_time({app="payment"} | json | unwrap response_time [5m]) by (endpoint)
```

### 5. Promtail 配置

#### 5.1 Promtail 架构

```
Promtail 工作流程：

┌──────────────────────────────────────────────────────────────┐
│                      Promtail                                  │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │  Target   │  │  Target   │  │  Target   │                   │
│  │  发现     │  │  发现     │  │  发现     │                   │
│  │ (文件)    │  │ (K8s)    │  │ (journal)│                   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                   │
│       │            │            │                             │
│       └────────────┴────────────┘                             │
│                    │                                           │
│                    ▼                                           │
│  ┌────────────────────────────────────┐                      │
│  │          Pipeline Stage            │                      │
│  │  ├── 正则匹配提取字段               │                      │
│  │  ├── JSON 解析                     │                      │
│  │  ├── 日志级别提取                  │                      │
│  │  └── 标签添加                      │                      │
│  └──────────────────┬─────────────────┘                      │
│                     │                                          │
│                     ▼                                          │
│  ┌────────────────────────────────────┐                      │
│  │          Positions File             │                      │
│  │  记录每个文件的读取位置              │                      │
│  └──────────────────┬─────────────────┘                      │
│                     │                                          │
│                     ▼                                          │
│  ┌────────────────────────────────────┐                      │
│  │          Loki Push API              │                      │
│  │  POST /loki/api/v1/push             │                      │
│  └────────────────────────────────────┘                      │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2 Promtail 配置文件

```yaml
# promtail-config.yml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /positions/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push
    # 如果需要认证
    # basic_auth:
    #   username: promtail
    #   password: ${LOKI_PASSWORD}
    # 批量发送
    batchwait: 1s
    batchsize: 1048576  # 1MB
    timeout: 10s

scrape_configs:
  # ========== 系统日志 ==========
  - job_name: system
    static_configs:
      - targets:
          - localhost
        labels:
          job: syslog
          host: ${HOSTNAME}
          __path__: /var/log/syslog

  # ========== Nginx 日志 ==========
  - job_name: nginx
    static_configs:
      - targets:
          - localhost
        labels:
          job: nginx
          __path__: /var/log/nginx/*.log
    pipeline_stages:
      # 解析 Nginx 日志
      - regex:
          expression: '^(?P<remote_addr>\\S+) - (?P<remote_user>\\S+) \\[(?P<time_local>.+)\\] "(?P<method>\\S+) (?P<request>\\S+) (?P<protocol>\\S+)" (?P<status>\\d+) (?P<body_bytes_sent>\\d+)'
      - labels:
          method:
          status:
      - timestamp:
          source: time_local
          format: "02/Jan/2006:15:04:05 -0700"

  # ========== 应用 JSON 日志 ==========
  - job_name: app
    static_configs:
      - targets:
          - localhost
        labels:
          job: app
          __path__: /var/log/app/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            service: service
            trace_id: trace_id
            message: message
      - labels:
          level:
          service:
      - timestamp:
          source: time
          format: "2006-01-02T15:04:05.000Z"

  # ========== Kubernetes Pod 日志 ==========
  - job_name: kubernetes
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
      - source_labels: [__meta_kubernetes_pod_node_name]
        target_label: node
    pipeline_stages:
      - cri: {}
      - json:
          expressions:
            level: level
            msg: message
      - labels:
          level:
      - output:
          source: msg

  # ========== Journal 日志 ==========
  - job_name: journal
    journal:
      json: false
      max_age: 12h
      path: /var/log/journal
      labels:
        job: systemd
    relabel_configs:
      - source_labels: ['__journal__systemd_unit']
        target_label: 'unit'
```

### 6. 标签设计策略

```
Loki 标签设计最佳实践：

┌──────────────────────────────────────────────────────────────────┐
│                    标签设计原则                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ✅ 推荐做法：                                                    │
│  ├── 使用低基数标签（< 100 个唯一值）                             │
│  ├── 使用有意义的业务标签                                        │
│  ├── 与 Prometheus 标签保持一致                                  │
│  ├── 使用静态标签（job, namespace, app）                         │
│  └── 在 pipeline 中提取动态标签                                  │
│                                                                    │
│  ❌ 避免做法：                                                    │
│  ├── 高基数标签（user_id, request_id, session_id）               │
│  ├── 频繁变化的标签                                              │
│  ├── 日志内容作为标签                                            │
│  └── 过多标签（影响查询性能）                                    │
│                                                                    │
│  推荐标签：                                                       │
│  ├── job: 日志来源（nginx, app, system）                         │
│  ├── namespace: K8s 命名空间                                     │
│  ├── app: 应用名称                                               │
│  ├── environment: 环境（prod, staging, dev）                     │
│  ├── host: 主机名                                                │
│  ├── level: 日志级别（info, warn, error）                        │
│  └── service: 服务名称                                           │
│                                                                    │
│  高基数字段 → 使用 LogQL 过滤，不作为标签                        │
│  ├── user_id: {app="payment"} | json | user_id="12345"          │
│  ├── request_id: {app="nginx"} | json | request_id="abc"        │
│  └── ip: {app="nginx"} | json | remote_addr="1.2.3.4"           │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### 7. 存储与保留策略

```
Loki 存储架构：

┌──────────────────────────────────────────────────────────────┐
│                    Loki 存储分层                                │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  热存储（近期数据）                                            │
│  ├── Ingester 内存 + WAL                                      │
│  ├── 块大小：目标 1MB，最大 5MB                                │
│  ├── 刷新间隔：1 小时                                          │
│  └── 存储：本地磁盘 / SSD                                     │
│                                                                │
│  温存储（天级数据）                                            │
│  ├── TSDB 索引                                                │
│  ├── 日志块存储                                                │
│  └── 存储：S3 / GCS / MinIO                                   │
│                                                                │
│  冷存储（月级数据）                                            │
│  ├── 压缩后的日志块                                            │
│  ├── 仅保留索引                                                │
│  └── 存储：S3 Glacier / 低成本存储                             │
│                                                                │
│  保留策略配置：                                                │
│  ├── chunk_retain_period: 30s （Ingester 保留块的时间）       │
│  ├── max_chunk_age: 2h （块的最大年龄）                       │
│  ├── reject_old_samples_max_age: 168h （拒绝旧样本）          │
│  └── retention_period: 744h （全局保留期，31 天）             │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

```yaml
# 保留策略配置
limits_config:
  # 全局保留期
  retention_period: 744h  # 31 天

  # 每租户保留期（通过运行时配置覆盖）
  per_tenant_override_config: /etc/loki/overrides.yaml

# overrides.yaml - 每租户保留策略
overrides:
  "tenant-1":
    retention_period: 168h    # 7 天
  "tenant-2":
    retention_period: 2160h   # 90 天

# Compactor 配置
compactor:
  working_directory: /loki/compactor
  shared_store: s3
  compaction_interval: 10m
  retention_enabled: true
  retention_delete_delay: 2h
  retention_delete_worker_count: 150
```

### 8. Loki vs ELK 对比

```
Loki vs ELK 全面对比：

┌─────────────────┬──────────────────────┬──────────────────────┐
│ 特性            │ Loki                 │ ELK                  │
├─────────────────┼──────────────────────┼──────────────────────┤
│ 索引策略        │ 只索引标签           │ 全文索引             │
│ 存储成本        │ 低（对象存储）       │ 高（SSD + 内存）     │
│ 写入性能        │ 高                   │ 中（需要构建索引）   │
│ 查询性能        │ 中（流式过滤）       │ 高（倒排索引）       │
│ 全文搜索        │ 不支持               │ 支持                 │
│ 标签查询        │ 原生支持             │ 需要 keyword 字段    │
│ 正则查询        │ 支持（慢）           │ 支持                 │
│ 聚合分析        │ 有限                 │ 强大                 │
│ 可视化          │ Grafana              │ Kibana               │
│ 生态集成        │ Prometheus/Grafana   │ Elastic Stack        │
│ K8s 支持        │ 原生                 │ 需要额外配置         │
│ 运维复杂度      │ 低                   │ 高                   │
│ 社区活跃度      │ 高（Grafana Labs）   │ 高（Elastic）        │
│ 适用场景        │ K8s/云原生           │ 传统企业             │
│ 学习曲线        │ 低                   │ 中高                 │
└─────────────────┴──────────────────────┴──────────────────────┘

选型建议：

选择 Loki：
  ✓ K8s / 云原生环境
  ✓ 已使用 Prometheus + Grafana
  ✓ 日志量大，存储成本敏感
  ✓ 主要需求是日志搜索和告警
  ✓ 不需要复杂的日志分析

选择 ELK：
  ✓ 需要全文搜索能力
  ✓ 需要复杂的日志分析（聚合、统计）
  ✓ 有专业的 ELK 运维团队
  ✓ 需要机器学习异常检测
  ✓ 传统企业环境

混合架构：
  ✓ Loki 用于实时日志搜索和告警
  ✓ ELK 用于深度日志分析和审计
  ✓ 共享采集层（Filebeat → Kafka → 分发）
```

### 9. SRE 实战案例

#### 9.1 Loki 查询性能优化

```
问题：LogQL 查询超时，返回 "query timed out"

原因分析：
1. 标签选择器太宽泛 → 扫描数据量大
2. 没有时间范围限制 → 全量扫描
3. 正则匹配过多 → CPU 密集

优化方案：

1. 缩小标签范围
   # 不推荐
   {job="app"}
   
   # 推荐
   {job="app", namespace="production", level="error"}

2. 添加时间范围
   {job="app"} |= "error"  # 最近 1 小时（Grafana 默认）
   
3. 使用行过滤器缩小范围
   {job="app"} |= "error" != "healthcheck"

4. 避免高基数聚合
   # 不推荐（高基数）
   sum(rate({job="app"} | json [5m])) by (user_id)
   
   # 推荐（低基数）
   sum(rate({job="app"} | json [5m])) by (service)

5. 使用 Query Frontend 缓存
   query_range:
     results_cache:
       cache:
         embedded_cache:
           enabled: true
           max_size_mb: 256
```

#### 9.2 日志丢失排查

```
问题：Loki 中部分日志缺失

排查步骤：

1. 检查 Promtail 状态
   curl -s "localhost:9080/targets"
   → 查看 targets 是否正常

2. 检查 Promtail 位置文件
   cat /positions/positions.yaml
   → 确认文件读取位置是否正确

3. 检查 Loki 接收状态
   curl -s "localhost:3100/metrics" | grep loki_ingester_samples_received_total
   → 确认是否收到日志

4. 检查 Loki 错误日志
   docker logs loki 2>&1 | grep -i error
   → 查看是否有 rate limit 或其他错误

5. 检查标签基数
   curl -s "localhost:3100/loki/api/v1/label/job/values"
   → 确认标签是否正常

6. 常见原因：
   - Promtail 权限不足（无法读取日志文件）
   - Loki rate limit（ingestion_rate_mb 限制）
   - WAL 损坏（Ingester 异常重启）
   - 标签基数过高（内存溢出）
```

---

## 💻 实战练习

### 练习 1：部署 Loki + Promtail + Grafana

```bash
# 步骤 1：创建配置文件
mkdir -p loki-stack
cd loki-stack

# 创建 loki-config.yml（使用前面的单节点配置）
# 创建 promtail-config.yml（使用前面的配置）
# 创建 docker-compose.yml（使用前面的模板）

# 步骤 2：启动栈
docker-compose up -d

# 步骤 3：验证 Loki
curl -s "localhost:3100/ready"
# 应返回 "ready"

# 步骤 4：验证 Promtail
curl -s "localhost:9080/targets"
# 应显示已配置的 targets

# 步骤 5：配置 Grafana 数据源
# 访问 localhost:3000
# 添加 Loki 数据源：http://loki:3100

# 步骤 6：查询日志
# 在 Grafana Explore 中执行：
{job="syslog"}
{job="syslog"} |= "error"
```

### 练习 2：LogQL 查询练习

```bash
# 场景：分析 Nginx 访问日志

# 查询 1：查看所有 Nginx 日志
{job="nginx"}

# 查询 2：过滤错误请求
{job="nginx"} | json | status >= 500

# 查询 3：统计每分钟错误数
sum(count_over_time({job="nginx"} | json | status >= 500 [1m]))

# 查询 4：按状态码统计
sum(count_over_time({job="nginx"} | json [5m])) by (status)

# 查询 5：统计 P99 延迟
quantile_over_time(0.99, {job="nginx"} | json | unwrap response_time [5m])

# 查询 6：查找慢请求
{job="nginx"} | json | response_time > 5

# 查询 7：统计每秒请求速率
sum(rate({job="nginx"}[5m])) by (method)
```

### 练习 3：标签设计与保留策略

```bash
# 场景：为微服务设计标签策略

# 步骤 1：确定核心标签
# job: 服务名称（payment, order, user）
# namespace: K8s 命名空间
# environment: 环境（prod, staging）
# level: 日志级别

# 步骤 2：配置 Promtail pipeline
# 从 JSON 日志中提取 level 和 service 作为标签

# 步骤 3：配置保留策略
# 生产环境：保留 30 天
# 开发环境：保留 7 天

# 步骤 4：验证标签
curl -s "localhost:3100/loki/api/v1/label/job/values"
curl -s "localhost:3100/loki/api/v1/label/level/values"
```

---

## 🎯 面试题精选

### 1. Loki 和 ELK 在索引策略上有什么区别？

**答**：
- **ELK**：对日志内容进行全文索引（倒排索引），支持复杂的全文搜索和聚合，但存储成本高
- **Loki**：只索引标签（Label），不索引日志内容，查询时通过标签快速定位日志流，然后流式过滤。存储成本低，但全文搜索能力弱

### 2. LogQL 的 Log Stream Selector 和 Log Pipeline 分别是什么？

**答**：
- **Log Stream Selector**：选择日志流，使用标签过滤，类似 Prometheus 的标签选择器
- **Log Pipeline**：对日志内容进行处理，包括行过滤（`|=`、`|~`）、解析（`| json`、`| logfmt`）、标签过滤（`| status >= 500`）

### 3. Loki 的标签设计有什么原则？

**答**：
- 使用低基数标签（< 100 个唯一值）
- 避免高基数标签（如 user_id、request_id）
- 使用有意义的业务标签
- 与 Prometheus 标签保持一致
- 高基数字段使用 LogQL 过滤而非标签

### 4. Promtail 的 Positions 文件有什么作用？

**答**：Positions 文件记录了每个日志文件的读取偏移量，用于断点续传。当 Promtail 重启时，从 Positions 文件恢复读取位置，避免重复采集或丢失日志。

### 5. Loki 的存储架构有什么特点？

**答**：
- **Index Store**：存储标签索引，支持 BoltDB、TSDB、Cassandra、DynamoDB
- **Chunk Store**：存储日志块，支持 S3、GCS、Azure Blob、Cassandra
- 日志在 Ingester 中压缩为块后写入 Chunk Store
- 对象存储友好，成本低、可扩展

### 6. 如何优化 Loki 的查询性能？

**答**：
1. 缩小标签选择器范围
2. 添加时间范围限制
3. 使用行过滤器缩小范围
4. 避免高基数聚合
5. 使用 Query Frontend 缓存
6. 合理设置 `max_query_length` 和 `max_query_series`

### 7. Loki 的 Compactor 组件有什么作用？

**答**：Compactor 负责：
- **索引压缩**：合并小的索引文件，提高查询效率
- **数据清理**：根据保留策略删除过期数据
- **标记删除**：标记需要删除的数据块

### 8. 什么场景下选择 Loki 而不是 ELK？

**答**：
- K8s / 云原生环境
- 已使用 Prometheus + Grafana 生态
- 日志量大，存储成本敏感
- 主要需求是日志搜索和告警
- 不需要复杂的全文搜索和日志分析

### 9. Loki 的 Ingestion Rate Limit 是什么？如何配置？

**答**：Ingestion Rate Limit 限制每个租户的日志写入速率，防止某个租户占用过多资源。

```yaml
limits_config:
  ingestion_rate_mb: 10       # 每秒 10MB
  ingestion_burst_size_mb: 20 # 突发 20MB
  per_stream_rate_limit: 5MB  # 每条流每秒 5MB
```

### 10. 如何在 Grafana 中关联 Metrics 和 Logs？

**答**：
1. 使用相同的标签体系（如 job、namespace）
2. 在 Grafana Dashboard 中同时展示 Prometheus 指标和 Loki 日志
3. 使用 Derived Fields 将日志中的 trace_id 链接到 Jaeger
4. 使用 Exemplar 将 Prometheus 指标链接到 Loki 日志

---

## 📚 深入阅读

- [Loki 官方文档](https://grafana.com/docs/loki/latest/)
- [LogQL 查询语言](https://grafana.com/docs/loki/latest/logql/)
- [Promtail 配置](https://grafana.com/docs/loki/latest/clients/promtail/)
- [Loki 最佳实践](https://grafana.com/docs/loki/latest/best-practices/)

---

## ✅ 自检清单

- [ ] 理解 Loki 的架构设计和核心组件
- [ ] 掌握 LogQL 的基础语法和高级用法
- [ ] 能够配置 Promtail 采集日志
- [ ] 理解标签设计的最佳实践
- [ ] 掌握存储和保留策略的配置
- [ ] 能够对比 Loki 和 ELK 并做出选型决策
- [ ] 能够优化 Loki 的查询性能
- [ ] 理解 Loki 与 Prometheus/Grafana 的集成方式
