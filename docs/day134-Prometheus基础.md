# Day 134: Prometheus 基础

> 📅 日期：2026-05-03
> 📖 学习主题：Prometheus 架构、安装配置、服务发现、指标类型、Exporter 生态
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 11 (系统监控命令), Day 88 (Docker 监控与日志), Day 133 (可观测性基础)

---

## 🎯 学习目标

- 理解 Prometheus 的整体架构和工作原理
- 掌握 Prometheus 的安装、配置和启动
- 理解 Prometheus 的拉取（Pull）模型与推送（Push）模型的区别
- 掌握四种指标类型（Counter、Gauge、Histogram、Summary）的特点和使用场景
- 熟悉 Prometheus 服务发现机制
- 了解主流 Exporter 生态系统

---

## 📖 核心知识点

### 1. Prometheus 架构概述

#### 1.1 发展历史

```
Prometheus 发展时间线：

  2012年  SoundCloud 内部开发（受 Google Borgmon 启发）
    │
  2015年  GitHub 开源发布
    │
  2016年  加入 CNCF（Cloud Native Computing Foundation）
    │     成为继 Kubernetes 之后的第二个 CNCF 项目
    │
  2018年  毕业项目，成为 CNCF 成熟项目
    │
  2020年  Prometheus 2.x 发布，采用 TSDB 存储引擎
    │
  2024年  Prometheus 3.0 发布，新 UI 和性能优化
    │
  2026年  云原生监控的事实标准
```

#### 1.2 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Prometheus 架构总览                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                    数据采集层                                 │  │
│   │                                                             │  │
│   │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │
│   │   │  Node    │  │  MySQL   │  │  Redis   │  │  App     │ │  │
│   │   │ Exporter │  │ Exporter │  │ Exporter │  │ /metrics │ │  │
│   │   └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘ │  │
│   │         │             │             │             │        │  │
│   └─────────┼─────────────┼─────────────┼─────────────┼────────┘  │
│             │             │             │             │            │
│             └─────────────┼─────────────┼─────────────┘            │
│                           │ Pull（拉取）                            │
│                           ▼                                        │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                    Prometheus Server                         │  │
│   │                                                             │  │
│   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │  │
│   │   │  Retrieval   │  │    TSDB      │  │   Rule       │    │  │
│   │   │  数据采集     │  │  时序数据库   │  │   Engine     │    │  │
│   │   │              │  │              │  │              │    │  │
│   │   │  HTTP 拉取   │  │  WAL 预写日志│  │  Recording   │    │  │
│   │   │  服务发现    │  │  Block 存储  │  │  Rules       │    │  │
│   │   │  指标解析    │  │  压缩合并    │  │  Alerting    │    │  │
│   │   │              │  │  标签索引    │  │  Rules       │    │  │
│   │   └──────────────┘  └──────────────┘  └──────────────┘    │  │
│   │                                                             │  │
│   │   ┌──────────────┐  ┌──────────────┐                      │  │
│   │   │   PromQL     │  │    HTTP      │                      │  │
│   │   │   查询引擎    │  │    API       │                      │  │
│   │   └──────────────┘  └──────────────┘                      │  │
│   │                                                             │  │
│   └───────────┬───────────────────────────────────┬─────────────┘  │
│               │                                   │                │
│               │                                   │ 告警            │
│               ▼                                   ▼                │
│   ┌──────────────────────┐            ┌──────────────────────┐    │
│   │      Grafana          │            │    Alertmanager      │    │
│   │      可视化           │            │      告警管理         │    │
│   │                      │            │                      │    │
│   │  - 仪表盘            │            │  - 路由              │    │
│   │  - 图表              │            │  - 分组              │    │
│   │  - 变量              │            │  - 抑制              │    │
│   │  - 告警              │            │  - 静默              │    │
│   └──────────────────────┘            │  - 通知              │    │
│                                       └──────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.3 核心组件

| 组件 | 功能 | 说明 |
|------|------|------|
| Prometheus Server | 核心服务 | 负责数据采集、存储、查询 |
| Retrieval | 数据采集 | 通过 HTTP 拉取指标数据 |
| TSDB | 时序数据库 | 高效存储时间序列数据 |
| PromQL | 查询语言 | 灵活的数据查询和聚合 |
| Rule Engine | 规则引擎 | Recording Rules 和 Alerting Rules |
| Alertmanager | 告警管理 | 告警路由、分组、抑制、通知 |
| Pushgateway | 推送网关 | 支持短期任务推送指标 |
| Service Discovery | 服务发现 | 自动发现监控目标 |

#### 1.4 Pull vs Push 模型

```
Pull 模型（Prometheus 采用）：
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Target 1 ──┐                                                │
│  Target 2 ──┤     Prometheus                                 │
│  Target 3 ──┼────▶  Server      定期拉取 /metrics 端点       │
│  Target 4 ──┤                                                │
│  Target N ──┘                                                │
│                                                              │
│  优点：                                                      │
│  ├── Server 控制采集频率                                     │
│  ├── 目标存活检测简单（HTTP 连通性）                         │
│  ├── 不需要服务端 SDK 复杂配置                              │
│  └── 易于水平扩展                                            │
│                                                              │
│  缺点：                                                      │
│  ├── 短生命周期任务可能错过采集                              │
│  ├── 需要目标暴露 HTTP 端点                                  │
│  └── 防火墙/网络策略可能阻碍拉取                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘

Push 模型（Pushgateway 辅助）：
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  短生命周期任务 ──▶ Pushgateway ──▶ Prometheus Server        │
│  (CronJob)         (推送端点)        (拉取 Pushgateway)      │
│                                                              │
│  适用场景：                                                  │
│  ├── 短生命周期任务（CronJob、Batch Job）                    │
│  ├── 无法暴露 HTTP 端点的服务                                │
│  └── 需要主动推送的场景                                      │
│                                                              │
│  注意：                                                      │
│  ├── 不适合大规模使用                                        │
│  ├── 推送的数据会一直保留直到被覆盖                          │
│  └── 应设置合理的 TTL                                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2. 安装与配置

#### 2.1 二进制安装

```bash
# 1. 下载 Prometheus
PROMETHEUS_VERSION="2.53.0"
wget https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz

# 2. 解压
tar xvfz prometheus-${PROMETHEUS_VERSION}.linux-amd64.tar.gz
cd prometheus-${PROMETHEUS_VERSION}.linux-amd64

# 3. 创建用户和目录
sudo useradd --no-create-home --shell /bin/false prometheus
sudo mkdir -p /etc/prometheus /var/lib/prometheus
sudo cp prometheus promtool /usr/local/bin/
sudo cp -r consoles console_libraries /etc/prometheus/
sudo chown -R prometheus:prometheus /etc/prometheus /var/lib/prometheus

# 4. 验证安装
prometheus --version
promtool --version
```

#### 2.2 Docker 安装

```bash
# Docker 运行
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /etc/prometheus:/etc/prometheus \
  -v /var/lib/prometheus:/prometheus \
  prom/prometheus:v2.53.0 \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --storage.tsdb.retention.time=15d \
  --web.enable-lifecycle

# Docker Compose
cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:v2.53.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
    restart: unless-stopped

volumes:
  prometheus_data:
EOF
```

#### 2.3 Systemd 服务管理

```ini
# /etc/systemd/system/prometheus.service
[Unit]
Description=Prometheus Monitoring System
Documentation=https://prometheus.io/docs/introduction/overview/
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=prometheus
Group=prometheus
ExecReload=/bin/kill -HUP $MAINPID
ExecStart=/usr/local/bin/prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/var/lib/prometheus \
  --storage.tsdb.retention.time=15d \
  --storage.tsdb.retention.size=10GB \
  --web.console.libraries=/etc/prometheus/console_libraries \
  --web.console.templates=/etc/prometheus/consoles \
  --web.enable-lifecycle \
  --web.enable-admin-api \
  --web.listen-address=0.0.0.0:9090 \
  --web.external-url=http://localhost:9090 \
  --log.level=info
SyslogIdentifier=prometheus
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
sudo systemctl status prometheus
```

#### 2.4 核心配置文件

```yaml
# /etc/prometheus/prometheus.yml

# 全局配置
global:
  # 采集间隔（默认 15s）
  scrape_interval: 15s

  # 评估规则间隔（默认 15s）
  evaluation_interval: 15s

  # 采集超时
  scrape_timeout: 10s

  # 外部标签（用于联邦和远程写入）
  external_labels:
    cluster: production
    region: us-east-1

# 告警配置
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'
      timeout: 10s

# 规则文件
rule_files:
  - '/etc/prometheus/rules/*.yml'

# 采集配置
scrape_configs:
  # Prometheus 自身监控
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter
  - job_name: 'node'
    static_configs:
      - targets:
          - 'node1:9100'
          - 'node2:9100'
          - 'node3:9100'
    relabel_configs:
      - source_labels: [__address__]
        regex: '(.+):(\d+)'
        target_label: instance
        replacement: '${1}'
```

#### 2.5 配置验证与热加载

```bash
# 配置验证
promtool check config /etc/prometheus/prometheus.yml

# 规则文件验证
promtool check rules /etc/prometheus/rules/*.yml

# 热加载配置（需要开启 --web.enable-lifecycle）
curl -X POST http://localhost:9090/-/reload

# 或发送 SIGHUP 信号
kill -HUP $(pgrep prometheus)

# 测试规则表达式
promtool test rules /etc/prometheus/tests/*.yml
```

### 3. 服务发现

#### 3.1 服务发现方式

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Prometheus 服务发现机制                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  静态配置（Static Config）：                                        │
│  └── 手动指定目标地址，适合小规模固定环境                           │
│                                                                     │
│  动态服务发现（Service Discovery）：                                │
│  ├── 基于文件（file_sd_configs）                                    │
│  │   └── 从 JSON/YAML 文件读取目标列表                             │
│  │                                                                  │
│  ├── 基于 DNS（dns_sd_configs）                                     │
│  │   └── 通过 DNS SRV 记录发现目标                                 │
│  │                                                                  │
│  ├── 基于 Kubernetes（kubernetes_sd_configs）                       │
│  │   ├── node        - K8s 节点                                    │
│  │   ├── pod         - Pod                                          │
│  │   ├── service     - Service                                      │
│  │   ├── endpoints   - Endpoints                                    │
│  │   └── ingress     - Ingress                                      │
│  │                                                                  │
│  ├── 基于云平台                                                      │
│  │   ├── ec2_sd_configs         - AWS EC2                           │
│  │   ├── azure_sd_configs       - Azure VM                          │
│  │   ├── gce_sd_configs         - GCP GCE                           │
│  │   └── openstack_sd_configs   - OpenStack                         │
│  │                                                                  │
│  ├── 基于配置管理                                                    │
│  │   ├── consul_sd_configs      - Consul                            │
│  │   ├── eureka_sd_configs      - Eureka                            │
│  │   └── serverset_sd_configs   - ZooKeeper Serverset               │
│  │                                                                  │
│  └── 基于 HTTP                                                      │
│      └── http_sd_configs        - 自定义 HTTP 端点                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.2 文件服务发现

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'file-sd'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.json'
          - '/etc/prometheus/targets/*.yml'
        refresh_interval: 5m
```

```json
// /etc/prometheus/targets/webservers.json
[
  {
    "targets": ["web1:9100", "web2:9100", "web3:9100"],
    "labels": {
      "env": "production",
      "role": "webserver",
      "team": "platform"
    }
  },
  {
    "targets": ["api1:9100", "api2:9100"],
    "labels": {
      "env": "production",
      "role": "api",
      "team": "backend"
    }
  }
]
```

#### 3.3 Kubernetes 服务发现

```yaml
# prometheus.yml - Kubernetes 服务发现配置
scrape_configs:
  # 1. 发现所有 Kubernetes 节点
  - job_name: 'kubernetes-nodes'
    kubernetes_sd_configs:
      - role: node
    relabel_configs:
      - action: labelmap
        regex: __meta_kubernetes_node_label_(.+)
      - source_labels: [__address__]
        regex: '(.+):(\d+)'
        target_label: __address__
        replacement: '${1}:9100'

  # 2. 发现所有带注解的 Pod
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: (.+)
        replacement: ${1}
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
```

#### 3.4 Relabeling 标签重写

```yaml
# Relabeling 配置示例
relabel_configs:
  # 1. 保留匹配的目标
  - source_labels: [__meta_kubernetes_pod_label_app]
    action: keep
    regex: my-app

  # 2. 丢弃匹配的目标
  - source_labels: [__meta_kubernetes_pod_phase]
    action: drop
    regex: (Succeeded|Failed)

  # 3. 替换标签值
  - source_labels: [__address__]
    regex: '(.+):(\d+)'
    target_label: instance
    replacement: '${1}'

  # 4. 映射标签
  - action: labelmap
    regex: __meta_kubernetes_pod_label_(.+)

  # 5. 哈希标签（用于一致性哈希分片）
  - source_labels: [__address__]
    modulus: 3
    target_label: __tmp_hash
    action: hashmod
  - source_labels: [__tmp_hash]
    regex: 0
    action: keep

  # 6. 设置固定标签
  - target_label: environment
    replacement: production
```

### 4. 指标类型

#### 4.1 指标类型总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Prometheus 指标类型                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │   Counter    │  │    Gauge     │                                │
│  │   计数器      │  │   仪表盘     │                                │
│  ├──────────────┤  ├──────────────┤                                │
│  │ 只增不减     │  │ 可增可减     │                                │
│  │ 单调递增     │  │ 瞬时值       │                                │
│  │              │  │              │                                │
│  │ 适用：       │  │ 适用：       │                                │
│  │ - 请求总数   │  │ - 当前温度   │                                │
│  │ - 错误总数   │  │ - 内存使用量 │                                │
│  │ - 处理字节数 │  │ - 队列长度   │                                │
│  │ - 任务完成数 │  │ - 并发连接数 │                                │
│  └──────────────┘  └──────────────┘                                │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │  Histogram   │  │   Summary    │                                │
│  │   直方图      │  │   摘要       │                                │
│  ├──────────────┤  ├──────────────┤                                │
│  │ 分桶统计     │  │ 客户端计算   │                                │
│  │ 可聚合       │  │ 不可聚合     │                                │
│  │              │  │              │                                │
│  │ 适用：       │  │ 适用：       │                                │
│  │ - 请求延迟   │  │ - 请求延迟   │                                │
│  │ - 响应大小   │  │ - 响应大小   │                                │
│  │ - 分布统计   │  │ - 精确分位数 │                                │
│  │              │  │              │                                │
│  │ 推荐：生产用 │  │ 推荐：少量用 │                                │
│  └──────────────┘  └──────────────┘                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2 Counter 计数器

Counter 是最简单的指标类型，表示单调递增的计数器。

```go
// Go 客户端示例
import "github.com/prometheus/client_golang/prometheus"

// 定义 Counter
var httpRequestsTotal = prometheus.NewCounterVec(
    prometheus.CounterOpts{
        Name: "http_requests_total",
        Help: "Total number of HTTP requests",
    },
    []string{"method", "endpoint", "status"},
)

// 注册指标
prometheus.MustRegister(httpRequestsTotal)

// 使用指标（只能递增）
httpRequestsTotal.WithLabelValues("GET", "/api/users", "200").Inc()
httpRequestsTotal.WithLabelValues("POST", "/api/users", "201").Add(1)
```

```
Counter 数据格式：

  # HELP http_requests_total Total number of HTTP requests
  # TYPE http_requests_total counter
  http_requests_total{method="GET",endpoint="/api/users",status="200"} 1234
  http_requests_total{method="POST",endpoint="/api/users",status="201"} 567

Counter 使用注意事项：

  ✅ 正确：使用 rate() 或 increase() 计算速率
     rate(http_requests_total[5m])        # 每秒速率
     increase(http_requests_total[1h])    # 1小时增量

  ❌ 错误：直接使用 Counter 值
     http_requests_total                  # 无意义，只显示绝对值

  ❌ 错误：手动减少 Counter 值
     Counter 只能递增，不能递减

  ⚠️ 注意：服务重启后 Counter 会重置为 0
     rate() 函数能自动处理 Counter 重置
```

#### 4.3 Gauge 仪表盘

Gauge 表示可以任意增减的数值。

```go
// Go 客户端示例
var cpuTemperature = prometheus.NewGauge(
    prometheus.GaugeOpts{
        Name: "cpu_temperature_celsius",
        Help: "Current CPU temperature",
    },
)

// 使用指标（可增可减）
cpuTemperature.Set(65.5)     // 设置值
cpuTemperature.Inc()         // 增加 1
cpuTemperature.Dec()         // 减少 1
cpuTemperature.Add(2.5)      // 增加指定值
cpuTemperature.Sub(1.2)      // 减少指定值
```

```
Gauge 数据格式：

  # HELP cpu_temperature_celsius Current CPU temperature
  # TYPE cpu_temperature_celsius gauge
  cpu_temperature_celsius 65.5

Gauge 常用操作：

  # 当前值
  node_memory_MemFree_bytes

  # 变化率
  deriv(node_memory_MemFree_bytes[5m])

  # 最大值（过去 1 小时）
  max_over_time(node_memory_MemFree_bytes[1h])

  # 最小值（过去 1 小时）
  min_over_time(node_memory_MemFree_bytes[1h])

  # 平均值（过去 1 小时）
  avg_over_time(node_memory_MemFree_bytes[1h])
```

#### 4.4 Histogram 直方图

Histogram 对观测值进行分桶统计，适合计算延迟分布。

```go
// Go 客户端示例
var httpDuration = prometheus.NewHistogramVec(
    prometheus.HistogramOpts{
        Name:    "http_request_duration_seconds",
        Help:    "HTTP request duration in seconds",
        Buckets: []float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10},
    },
    []string{"method", "endpoint"},
)

// 使用指标
timer := prometheus.NewTimer(httpDuration.WithLabelValues("GET", "/api/users"))
defer timer.ObserveDuration()
httpDuration.WithLabelValues("GET", "/api/users").Observe(0.15)
```

```
Histogram 数据格式：

  # HELP http_request_duration_seconds HTTP request duration in seconds
  # TYPE http_request_duration_seconds histogram
  http_request_duration_seconds_bucket{le="0.001"} 0
  http_request_duration_seconds_bucket{le="0.005"} 12
  http_request_duration_seconds_bucket{le="0.01"} 45
  http_request_duration_seconds_bucket{le="0.025"} 120
  http_request_duration_seconds_bucket{le="0.05"} 350
  http_request_duration_seconds_bucket{le="0.1"} 800
  http_request_duration_seconds_bucket{le="0.25"} 950
  http_request_duration_seconds_bucket{le="0.5"} 990
  http_request_duration_seconds_bucket{le="1"} 998
  http_request_duration_seconds_bucket{le="2.5"} 999
  http_request_duration_seconds_bucket{le="5"} 1000
  http_request_duration_seconds_bucket{le="+Inf"} 1000
  http_request_duration_seconds_sum 125.5
  http_request_duration_seconds_count 1000

Histogram 自动生成三个指标：
  *_bucket  - 各桶的累积计数
  *_sum     - 所有观测值的总和
  *_count   - 观测值的总数
```

```
Histogram 分位数计算：

  # P50（中位数）
  histogram_quantile(0.5, rate(http_request_duration_seconds_bucket[5m]))

  # P90
  histogram_quantile(0.9, rate(http_request_duration_seconds_bucket[5m]))

  # P99
  histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

  # 按标签分组的 P99
  histogram_quantile(0.99,
    sum by (le, method) (
      rate(http_request_duration_seconds_bucket[5m])
    )
  )

  # 平均延迟
  rate(http_request_duration_seconds_sum[5m])
  /
  rate(http_request_duration_seconds_count[5m])
```

#### 4.5 Summary 摘要

Summary 在客户端计算分位数，适合需要精确分位数的场景。

```
Summary 数据格式：

  # HELP http_request_duration_summary_seconds HTTP request duration in seconds
  # TYPE http_request_duration_summary_seconds summary
  http_request_duration_summary_seconds{quantile="0.5"} 0.08
  http_request_duration_summary_seconds{quantile="0.9"} 0.25
  http_request_duration_summary_seconds{quantile="0.99"} 0.85
  http_request_duration_summary_seconds_sum 125.5
  http_request_duration_summary_seconds_count 1000

Summary vs Histogram：

  ┌─────────────┬─────────────────┬─────────────────┐
  │ 特性         │ Histogram       │ Summary         │
  ├─────────────┼─────────────────┼─────────────────┤
  │ 分位数计算   │ 服务端（PromQL）│ 客户端          │
  │ 可聚合性     │ 可以跨实例聚合  │ 不能跨实例聚合  │
  │ 存储开销     │ 较高（多个桶）  │ 较低            │
  │ 精确度       │ 取决于桶划分    │ 可配置误差      │
  │ 推荐场景     │ 通用场景        │ 精确分位数      │
  └─────────────┴─────────────────┴─────────────────┘

  推荐：生产环境优先使用 Histogram
        只在需要精确分位数且无法接受桶误差时使用 Summary
```

#### 4.6 指标类型选择指南

```
指标类型选择决策树：

  你需要记录什么？
  │
  ├── 一个只会增加的数值？
  │   ├── 是 → Counter
  │   │   例子：请求总数、错误总数、字节总数
  │   │
  │   └── 否 ↓
  │
  ├── 一个可增可减的数值？
  │   ├── 是 → Gauge
  │   │   例子：温度、内存使用、队列长度
  │   │
  │   └── 否 ↓
  │
  ├── 需要统计分布/分位数？
  │   ├── 是 → Histogram（推荐）
  │   │   例子：请求延迟分布、响应大小分布
  │   │
  │   └── 否 ↓
  │
  └── 需要精确分位数且无法接受桶误差？
      ├── 是 → Summary
      │
      └── 否 → 重新考虑需求
```

### 5. Exporter 生态系统

#### 5.1 Exporter 概述

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Prometheus Exporter 生态系统                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  系统层：                                                          │
│  ├── node_exporter          - 主机指标（CPU/内存/磁盘/网络）       │
│  ├── process_exporter       - 进程指标                             │
│  └── collectd_exporter      - collectd 指标桥接                    │
│                                                                     │
│  数据库层：                                                        │
│  ├── mysqld_exporter        - MySQL 指标                           │
│  ├── postgres_exporter      - PostgreSQL 指标                      │
│  ├── mongodb_exporter       - MongoDB 指标                         │
│  ├── redis_exporter         - Redis 指标                           │
│  └── elasticsearch_exporter - Elasticsearch 指标                   │
│                                                                     │
│  中间件层：                                                        │
│  ├── nginx_exporter         - Nginx 指标                           │
│  ├── haproxy_exporter       - HAProxy 指标                         │
│  ├── rabbitmq_exporter      - RabbitMQ 指标                        │
│  ├── kafka_exporter         - Kafka 指标                           │
│  └── consul_exporter        - Consul 指标                          │
│                                                                     │
│  硬件层：                                                          │
│  ├── ipmi_exporter          - IPMI 硬件指标                        │
│  ├── snmp_exporter          - SNMP 设备指标                        │
│  ├── blackbox_exporter      - 黑盒探测（HTTP/TCP/ICMP/DNS）       │
│  └── smart_exporter         - 硬盘 SMART 指标                      │
│                                                                     │
│  云平台层：                                                        │
│  ├── cloudwatch_exporter    - AWS CloudWatch 指标                  │
│  ├── stackdriver_exporter   - GCP Stackdriver 指标                 │
│  └── azure_exporter         - Azure Monitor 指标                   │
│                                                                     │
│  应用层：                                                          │
│  ├── prometheus/client_golang  - Go 客户端库                       │
│  ├── prometheus/client_python  - Python 客户端库                   │
│  ├── prometheus/client_java    - Java 客户端库                     │
│  └── micrometer               - Java 应用指标（Spring Boot）       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.2 Node Exporter

Node Exporter 是最重要的 Exporter，用于采集主机指标。

```bash
# 安装 Node Exporter
NODE_EXPORTER_VERSION="1.8.1"
wget https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
tar xvfz node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
sudo cp node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/

# Systemd 服务
cat > /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter \
  --collector.cpu \
  --collector.meminfo \
  --collector.diskstats \
  --collector.filesystem \
  --collector.loadavg \
  --collector.netdev \
  --collector.netstat \
  --collector.sockstat \
  --collector.stat \
  --collector.time \
  --collector.uname \
  --collector.vmstat
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter
```

```
Node Exporter 核心指标：

  CPU 指标：
  ├── node_cpu_seconds_total           - CPU 时间（各模式）
  ├── node_load1 / node_load5 / node_load15  - 负载
  └── node_context_switches_total      - 上下文切换

  内存指标：
  ├── node_memory_MemTotal_bytes       - 总内存
  ├── node_memory_MemAvailable_bytes   - 可用内存
  ├── node_memory_Buffers_bytes        - 缓冲区
  ├── node_memory_Cached_bytes         - 缓存
  └── node_memory_SwapTotal_bytes      - Swap 总量

  磁盘指标：
  ├── node_disk_read_bytes_total       - 读取字节数
  ├── node_disk_written_bytes_total    - 写入字节数
  ├── node_disk_io_time_seconds_total  - IO 时间
  ├── node_filesystem_size_bytes       - 文件系统大小
  └── node_filesystem_avail_bytes      - 可用空间

  网络指标：
  ├── node_network_receive_bytes_total - 接收字节数
  ├── node_network_transmit_bytes_total- 发送字节数
  ├── node_network_receive_errs_total  - 接收错误
  └── node_tcp_curr_established        - 当前 TCP 连接数
```

#### 5.3 Blackbox Exporter

Blackbox Exporter 用于黑盒探测，支持 HTTP、TCP、ICMP、DNS 探测。

```yaml
# blackbox.yml 配置
modules:
  http_2xx:
    prober: http
    timeout: 10s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: [200, 301, 302]
      method: GET
      follow_redirects: true

  tcp_connect:
    prober: tcp
    timeout: 5s

  icmp:
    prober: icmp
    timeout: 5s

  dns:
    prober: dns
    dns:
      query_name: "example.com"
      query_type: "A"
```

```yaml
# prometheus.yml 中使用 Blackbox Exporter
scrape_configs:
  - job_name: 'blackbox-http'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - https://www.example.com
          - https://api.example.com/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

```
Blackbox Exporter 核心指标：

  probe_success           - 探测是否成功（1=成功，0=失败）
  probe_duration_seconds  - 探测耗时
  probe_http_status_code  - HTTP 状态码
  probe_dns_lookup_time_seconds - DNS 查询耗时
  probe_ssl_earliest_cert_expiry - SSL 证书最早过期时间
```

#### 5.4 MySQL Exporter

```bash
# 安装 MySQL Exporter
MYSQL_EXPORTER_VERSION="0.15.1"
wget https://github.com/prometheus/mysqld_exporter/releases/download/v${MYSQL_EXPORTER_VERSION}/mysqld_exporter-${MYSQL_EXPORTER_VERSION}.linux-amd64.tar.gz
tar xvfz mysqld_exporter-${MYSQL_EXPORTER_VERSION}.linux-amd64.tar.gz
sudo cp mysqld_exporter-${MYSQL_EXPORTER_VERSION}.linux-amd64/mysqld_exporter /usr/local/bin/

# 创建 MySQL 用户
mysql -e "
  CREATE USER 'exporter'@'localhost' IDENTIFIED BY 'password';
  GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'exporter'@'localhost';
  GRANT SELECT ON performance_schema.* TO 'exporter'@'localhost';
  FLUSH PRIVILEGES;
"
```

```
MySQL Exporter 核心指标：

  mysql_global_status_threads_connected    - 当前连接数
  mysql_global_status_threads_running      - 活跃线程数
  mysql_global_status_queries              - 查询总数
  mysql_global_status_slow_queries         - 慢查询数
  mysql_global_status_innodb_buffer_pool_reads - InnoDB 缓冲池读取
  mysql_slave_status_seconds_behind_master - 主从延迟秒数
  mysql_global_variables_max_connections   - 最大连接数
```

### 6. TSDB 存储原理

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Prometheus TSDB 存储架构                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   写入路径：                                                        │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐                  │
│   │  指标    │────▶│   WAL    │────▶│  Head    │                  │
│   │  采集    │     │ 预写日志 │     │  Block   │                  │
│   └──────────┘     └──────────┘     └──────────┘                  │
│                                       │                            │
│                                       │ 每 2 小时                  │
│                                       ▼                            │
│                                  ┌──────────┐                      │
│                                  │  持久化  │                      │
│                                  │  Block   │                      │
│                                  └──────────┘                      │
│                                       │                            │
│                                       │ 后台压缩                   │
│                                       ▼                            │
│                    ┌──────────────────────────────────┐            │
│                    │     合并后的 Block（大块）         │            │
│                    │  ┌────────┐ ┌────────┐ ┌──────┐ │            │
│                    │  │ Block1 │ │ Block2 │ │ ...  │ │            │
│                    │  │ 2h     │ │ 2h     │ │      │ │            │
│                    │  └────────┘ └────────┘ └──────┘ │            │
│                    └──────────────────────────────────┘            │
│                                                                     │
│   Block 结构：                                                      │
│   ├── chunks/    - 压缩后的时间序列数据                            │
│   ├── index      - 标签索引和时间序列索引                          │
│   ├── meta.json  - 块元数据（时间范围等）                          │
│   └── tombstones - 删除标记                                        │
│                                                                     │
│   压缩策略：                                                        │
│   ├── 垂直压缩：同一时间序列的连续数据点压缩存储                    │
│   ├── 水平压缩：不同时间序列的相同标签压缩存储                      │
│   └── 块合并：小块定期合并为大块，减少文件数量                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

```bash
# 存储配置参数
prometheus \
  --storage.tsdb.path=/var/lib/prometheus \
  --storage.tsdb.retention.time=15d \
  --storage.tsdb.retention.size=10GB \
  --storage.tsdb.wal-compression
```

### 7. 实战案例：完整的监控部署

```yaml
# docker-compose.yml - 完整的 Prometheus 监控栈
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.53.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/rules:/etc/prometheus/rules
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana:11.0.0
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:v1.8.1
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```

---

## 💻 实战练习

### 练习 1：安装 Prometheus 并配置基本采集

**目标**：完成 Prometheus 安装，配置 Node Exporter 采集

```bash
# 步骤 1：下载 Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.53.0/prometheus-2.53.0.linux-amd64.tar.gz
tar xvfz prometheus-2.53.0.linux-amd64.tar.gz

# 步骤 2：下载 Node Exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.8.1/node_exporter-1.8.1.linux-amd64.tar.gz
tar xvfz node_exporter-1.8.1.linux-amd64.tar.gz

# 步骤 3：启动 Node Exporter
./node_exporter-1.8.1.linux-amd64/node_exporter &

# 步骤 4：创建 Prometheus 配置
cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
EOF

# 步骤 5：启动 Prometheus
./prometheus-2.53.0.linux-amd64/prometheus --config.file=prometheus.yml

# 步骤 6：验证
# 访问 http://localhost:9090/targets 查看采集目标
# 查询 node_cpu_seconds_total 验证数据采集
```

### 练习 2：配置文件服务发现

**目标**：使用文件服务发现管理多个监控目标

```yaml
# 步骤 1：创建目标文件
# /etc/prometheus/targets/webservers.json
[
  {
    "targets": ["localhost:9100"],
    "labels": {
      "env": "development",
      "role": "webserver"
    }
  }
]

# 步骤 2：配置 Prometheus 使用文件服务发现
scrape_configs:
  - job_name: 'file-sd'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/*.json'
        refresh_interval: 30s

# 步骤 3：添加新目标
# 修改 webservers.json 添加新的目标地址
# 观察 Prometheus 自动发现新目标
```

### 练习 3：编写自定义 Exporter

**目标**：使用 Python 编写一个简单的自定义 Exporter

```python
#!/usr/bin/env python3
"""
自定义 Prometheus Exporter 示例
监控文件目录大小和文件数量
"""

import os
import time
from prometheus_client import start_http_server, Gauge, Counter

# 定义指标
DIR_SIZE = Gauge(
    'custom_directory_size_bytes',
    'Size of directory in bytes',
    ['path']
)

FILE_COUNT = Gauge(
    'custom_directory_file_count',
    'Number of files in directory',
    ['path']
)

SCRAPE_COUNT = Counter(
    'custom_scrape_total',
    'Total number of scrapes'
)

def get_directory_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_file_count(path):
    count = 0
    for dirpath, dirnames, filenames in os.walk(path):
        count += len(filenames)
    return count

def collect_metrics(paths):
    SCRAPE_COUNT.inc()
    for path in paths:
        if os.path.exists(path):
            DIR_SIZE.labels(path=path).set(get_directory_size(path))
            FILE_COUNT.labels(path=path).set(get_file_count(path))

def main():
    paths_to_monitor = ['/var/log', '/tmp', '/etc/prometheus']
    start_http_server(8000)
    print("Exporter started on port 8000")
    while True:
        collect_metrics(paths_to_monitor)
        time.sleep(15)

if __name__ == '__main__':
    main()
```

---

## 🎯 面试题精选

### 1. 为什么 Prometheus 采用拉取（Pull）模型而不是推送（Push）模型？

**参考答案**：Pull 模型让 Server 控制采集频率，简单的目标存活检测（HTTP 连通性），不需要客户端复杂配置，易于水平扩展。劣势是短生命周期任务可能错过采集（通过 Pushgateway 解决）。

### 2. Counter 和 Gauge 有什么区别？

**参考答案**：Counter 是单调递增的计数器，只能增加或重置为 0，适用于累计值（请求总数、错误总数），只能通过 `rate()` 计算速率。Gauge 是可任意增减的数值，反映当前状态（温度、内存使用量），可以直接读取。

### 3. Histogram 和 Summary 有什么区别？生产环境如何选择？

**参考答案**：Histogram 在服务端分桶存储，支持跨实例聚合，可通过 `histogram_quantile()` 计算任意分位数。Summary 在客户端计算分位数，精度可控但不支持跨实例聚合。生产环境推荐使用 Histogram。

### 4. Prometheus 的服务发现机制有哪些？

**参考答案**：静态配置、文件服务发现、DNS 服务发现、Kubernetes 服务发现、Consul 服务发现、云平台服务发现（EC2/Azure/GCE）。根据环境选择：容器化用 K8s SD，微服务用 Consul SD，云平台用原生 SD。

### 5. Prometheus 的存储原理是什么？

**参考答案**：使用 TSDB 存储引擎，WAL 预写日志保证持久性，数据按 2 小时分块存储，每个块包含 chunks（压缩数据）、index（索引）和 meta.json（元数据）。后台定期合并小块为大块，使用垂直压缩和水平压缩优化存储。

### 6. 如何处理高基数（High Cardinality）问题？

**参考答案**：避免使用高基数标签（用户ID、请求ID），使用 relabeling 过滤，设置指标限制参数，监控 `prometheus_tsdb_head_series` 序列数量，使用 Recording Rules 预聚合。

### 7. Recording Rules 和 Alerting Rules 有什么区别？

**参考答案**：Recording Rules 预计算并存储查询结果，加速常用查询。Alerting Rules 定义告警条件，触发后发送到 Alertmanager。两者都在 Rule Engine 中定期评估，都使用 PromQL 表达式。

---

## 📚 深入阅读

1. **Prometheus 官方文档** - https://prometheus.io/docs/
2. **Prometheus 最佳实践** - https://prometheus.io/docs/practices/
3. **Prometheus 存储原理** - https://prometheus.io/docs/prometheus/latest/storage/
4. **Prometheus Exporter 列表** - https://prometheus.io/docs/instrumenting/exporters/
5. **《Prometheus: Up & Running》** - O'Reilly 出版

---

## ✅ 自检清单

- [ ] 能够画出 Prometheus 的架构图并解释各组件功能
- [ ] 理解 Pull 模型的优势和适用场景
- [ ] 能够安装和配置 Prometheus Server
- [ ] 能够配置静态目标和文件服务发现
- [ ] 理解四种指标类型的特点和使用场景
- [ ] 能够为合适的场景选择正确的指标类型
- [ ] 了解主流 Exporter 的用途和配置
- [ ] 能够配置 Node Exporter 采集主机指标
- [ ] 理解 Prometheus TSDB 的存储原理
- [ ] 能够编写简单的自定义 Exporter
