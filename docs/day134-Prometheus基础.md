# Day 134: Prometheus 基础

> 📅 日期：2026-05-05
> 📖 学习主题：Prometheus 基础
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Prometheus 的架构和数据模型
- 掌握四种指标类型（Counter, Gauge, Histogram, Summary）的使用场景
- 能安装、配置 Prometheus 并编写基础 PromQL 查询
- 理解 Exporter 的工作原理

---

## 📖 Prometheus 架构

### 1. 为什么选择 Prometheus？

```
传统监控系统（Nagios, Zabbix）：
  - 基于推送（Push）
  - 配置复杂
  - 不适合动态环境（容器、K8s）

Prometheus：
  - 基于拉取（Pull）— 主动去 Target 抓取数据
  - 时间序列数据库（TSDB）
  - 服务发现（自动发现 K8s Pod、EC2 实例）
  - PromQL 强大的查询语言
  - 云原生生态标准（CNCF 毕业项目）
```

### 2. 架构图

```
┌─────────────┐     Pull      ┌──────────────────┐
│  Prometheus │ ◄──────────── │  Targets         │
│  (TSDB +    │               │  (Node Exporter) │
│   PromQL +  │               │  (App Metrics)   │
│   Alerting) │               │  (Kubelet)       │
└──────┬──────┘               └──────────────────┘
       │
       ├──► Grafana (可视化)
       │
       ├──► Alertmanager (告警路由、去重、静默)
       │         ├──► PagerDuty
       │         ├──► Slack
       │         └──► Email
       │
       └──► Prometheus Federator (跨集群聚合)
```

### 3. Pull vs Push 的争议

```
Pull 的优势：
  ✅ 服务端控制抓取频率，不会被突发流量压垮
  ✅ Target 下线后自动停止抓取（不会出现僵尸数据）
  ✅ 更容易调试（curl http://target:9100/metrics 即可看到数据）

Push 的场景：
  - 短期任务（Batch Job, CronJob）— 还没等 Prometheus 来拉就挂了
  - 防火墙限制（Prometheus 无法访问 Target）
  解决方案：Pushgateway（但不推荐滥用）
```

---

## 📖 数据模型

### 1. 时间序列

Prometheus 存储的所有数据都是**时间序列**：
```
{__name__="http_requests_total", method="POST", handler="/api/users", status="200", instance="10.0.1.10:8080", job="api"}
```

- **指标名（__name__）**：描述测量什么（如 http_requests_total）
- **标签（Labels）**：维度信息（method, handler, status 等）
- **值（Value）**：浮点数 + 时间戳

### 2. 命名规范

```
✅ 正确：
  http_requests_total        ← Counter 以 _total 结尾
  node_memory_usage_bytes    ← Gauge 带单位
  http_request_duration_seconds  ← Histogram/Summary 带单位
  go_goroutines              ← 内置指标以 go_ 开头

❌ 错误：
  httpRequests               ← 不要用驼峰
  request_count              ← 不要用 count，用 total
  cpu                        ← 缺少单位
```

---

## 📖 四种指标类型

### 1. Counter（计数器）

**特点：只增不减，重启后归零。**

```
适用场景：
  - 请求总数
  - 错误总数
  - 字节数

典型指标：
  http_requests_total
  http_errors_total
  node_network_receive_bytes_total
```

```promql
# 总请求数
http_requests_total

# 每秒请求数（rate 自动处理 Counter 重置）
rate(http_requests_total[5m])

# 过去 1 小时增加的总量
increase(http_requests_total[1h])

# 错误率
rate(http_errors_total[5m]) / rate(http_requests_total[5m])
```

### 2. Gauge（仪表盘）

**特点：可增可减，反映当前状态。**

```
适用场景：
  - CPU 使用率
  - 内存使用量
  - 当前连接数
  - 队列长度

典型指标：
  node_cpu_usage_percent
  go_goroutines
  rabbitmq_queue_messages
```

```promql
# 当前值
node_memory_usage_bytes

# 5 分钟前 vs 现在的差值
node_memory_usage_bytes - node_memory_usage_bytes offset 5m

# 预测 2 小时后（基于线性趋势）
predict_linear(node_disk_free_bytes[1h], 2*3600)
```

### 3. Histogram（直方图）

**特点：将观测值分桶（Bucket），可计算分位数。**

```
适用场景：
  - 请求延迟分布
  - 响应大小分布
  - 批处理耗时

典型指标：
  http_request_duration_seconds_bucket
  http_response_size_bytes_bucket
```

**内部结构**：
```promql
http_request_duration_seconds_bucket{le="0.05"}   # <= 50ms 的请求数
http_request_duration_seconds_bucket{le="0.1"}    # <= 100ms 的请求数
http_request_duration_seconds_bucket{le="0.5"}    # <= 500ms 的请求数
http_request_duration_seconds_bucket{le="+Inf"}   # 总请求数

http_request_duration_seconds_sum                # 所有请求的总耗时
http_request_duration_seconds_count              # 总请求数
```

```promql
# 计算 P99 延迟
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# 计算平均延迟
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# 95% 的请求是否在 200ms 以内？
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) < 0.2
```

### 4. Summary（摘要）

**特点：客户端直接计算分位数，更精确但无法聚合。**

```
适用场景：
  - 需要精确分位数（如 P99）
  - 不需要跨实例聚合

与 Histogram 的区别：
  - Histogram：服务端分桶，可聚合，分位数是估算值
  - Summary：客户端计算分位数，不可聚合，分位数精确
```

```promql
# Summary 自带分位数值
rpc_duration_seconds{quantile="0.5"}   # P50
rpc_duration_seconds{quantile="0.9"}   # P90
rpc_duration_seconds{quantile="0.99"}  # P99
```

**SRE 建议**：优先使用 Histogram，除非你需要精确的分位数且不需要聚合。

---

## 🏗️ 安装与配置

### 1. Docker 安装

```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /etc/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v prometheus_data:/prometheus \
  prom/prometheus:latest
```

### 2. prometheus.yml 配置详解

```yaml
# 全局配置
global:
  scrape_interval: 15s        # 默认抓取间隔
  evaluation_interval: 15s    # 规则评估间隔
  scrape_timeout: 10s         # 抓取超时

# 外部标签（联邦集群时使用）
external_labels:
  cluster: 'production'
  region: 'us-east-1'

# 告警规则文件
rule_files:
  - "rules/*.yml"

# Alertmanager 配置
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

# 抓取配置
scrape_configs:
  # Prometheus 自身
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter（服务器指标）
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
        labels:
          env: 'production'

  # 应用指标
  - job_name: 'api'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['api-server:8080']

  # K8s 服务发现
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

### 3. Exporter 列表

| Exporter | 端口 | 用途 |
|----------|------|------|
| Node Exporter | 9100 | 服务器 CPU/内存/磁盘/网络 |
| cAdvisor | 8080 | Docker 容器指标 |
| Blackbox Exporter | 9115 | HTTP/TCP/DNS 探测 |
| SNMP Exporter | 9116 | 网络设备监控 |
| MySQL Exporter | 9104 | MySQL 指标 |
| Redis Exporter | 9121 | Redis 指标 |

---

## 🧪 练习题

### 练习 1：PromQL 查询

写出以下查询的 PromQL：
1. 过去 5 分钟的平均 QPS（按 job 分组）
2. P95 延迟 > 500ms 的服务
3. 磁盘使用率 > 85% 的节点

<details>
<summary>答案</summary>

```promql
# 1. 平均 QPS（按 job 分组）
sum(rate(http_requests_total[5m])) by (job)

# 2. P95 延迟 > 500ms 的服务
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5

# 3. 磁盘使用率 > 85%
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100 > 85
```
</details>

### 练习 2：指标类型选择

以下场景应该使用哪种指标类型？

1. 系统启动时间
2. API 请求总次数
3. HTTP 响应延迟分布
4. 当前活跃连接数
5. 任务队列长度

<details>
<summary>答案</summary>

1. **Gauge**（可增可减，反映当前状态）
2. **Counter**（只增不减）
3. **Histogram**（需要分布统计）
4. **Gauge**（可增可减）
5. **Gauge**（可增可减）
</details>

### 练习 3：编写告警规则

编写一个告警规则，当服务错误率超过 5% 持续 10 分钟时触发告警。

<details>
<summary>答案</summary>

```yaml
groups:
  - name: api-alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_errors_total[5m])) by (service)
          /
          sum(rate(http_requests_total[5m])) by (service)
          > 0.05
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }} for more than 10 minutes."
```
</details>

---

## 📖 深入：Relabeling（重标签）

### 什么是 Relabeling？

在抓取指标之前，动态修改 Target 的标签。这是 Prometheus 最强大的功能之一。

### 两种 Relabeling

```yaml
scrape_configs:
  - job_name: 'api'
    # metric_relabel_configs: 抓取后修改指标标签
    # relabel_configs: 抓取前修改 Target 标签
    relabel_configs:
      # 只抓取带有 prometheus.io/scrape=true 注解的 Pod
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true

      # 从 Pod 名称中提取环境信息
      - source_labels: [__meta_kubernetes_pod_name]
        regex: '(.*)-(prod|staging|dev)-(.*)'
        target_label: environment
        replacement: '$2'

      # 重命名标签
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
```

### 常用 Action

| Action | 说明 |
|--------|------|
| replace | 替换标签值 |
| keep | 保留匹配的 Target |
| drop | 丢弃匹配的 Target |
| labelmap | 从元标签映射 |
| labeldrop | 删除匹配的标签 |
| labelkeep | 保留匹配的标签 |

---

## 📖 深入：Recording Rules

### 为什么需要 Recording Rules？

```
问题：
  - 复杂查询（如 rate() + sum() by()）每次都要重新计算
  - Dashboard 加载慢
  - 告警规则重复计算相同表达式

解决：
  - 预先计算结果，存储为新指标
  - 提高查询性能
  - 简化 PromQL
```

### 编写 Recording Rules

```yaml
# rules/recording_rules.yml
groups:
  - name: api_recording_rules
    interval: 30s
    rules:
      # 预计算每秒请求数
      - record: job:http_requests:rate5m
        expr: sum(rate(http_requests_total[5m])) by (job)

      # 预计算错误率
      - record: job:http_error_rate:ratio5m
        expr: |
          sum(rate(http_errors_total[5m])) by (job)
          /
          sum(rate(http_requests_total[5m])) by (job)

      # 预计算 P99 延迟
      - record: job:http_request_duration_seconds:p99
        expr: |
          histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (job, le))
```

使用预计算指标：
```promql
# 原来（每次都要计算）
sum(rate(http_requests_total[5m])) by (job)

# 现在（直接查询预计算结果）
job:http_requests:rate5m
```

---

## 📖 深入：Prometheus 存储与性能

### TSDB 存储结构

```
/data/
└── prometheus/
    ├── 01BKGV7JBM69T2G1BGBGM6KB12  ← Block（2小时数据）
    │   ├── meta.json
    │   ├── chunks/                 ← 实际数据
    │   └── index                   ← 索引
    ├── 01BKGTZQ1SYQJIM4EB5742XV8Y  ← Block
    ├── wal/                        ← Write-Ahead Log（未刷盘数据）
    └── queries.active              ← 活跃查询
```

### 性能调优

```yaml
# prometheus.yml
global:
  scrape_interval: 15s    # 不要太频繁，15s 是合理默认值

storage:
  tsdb:
    max-block-duration: 2h     # 每个 block 的时长
    min-block-duration: 2h
    retention.time: 15d        # 数据保留时间
    retention.size: 50GB       # 或按大小限制

# 资源建议：
# - 100k 时间序列：2 CPU, 4GB RAM
# - 1M 时间序列：4 CPU, 16GB RAM
# - 10M 时间序列：8 CPU, 32GB RAM
```

---

## 🏗️ 实战：监控一个 Go 应用

### 1. 应用代码添加指标

```go
package main

import (
    "net/http"
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
    httpRequests = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total HTTP requests",
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
)

func init() {
    prometheus.MustRegister(httpRequests, httpRequestDuration)
}

func handler(w http.ResponseWriter, r *http.Request) {
    start := time.Now()

    // 业务逻辑
    w.Write([]byte("Hello!"))

    duration := time.Since(start).Seconds()
    httpRequests.WithLabelValues(r.Method, r.URL.Path, "200").Inc()
    httpRequestDuration.WithLabelValues(r.Method, r.URL.Path).Observe(duration)
}

func main() {
    http.HandleFunc("/", handler)
    http.Handle("/metrics", promhttp.Handler())
    http.ListenAndServe(":8080", nil)
}
```

### 2. Prometheus 配置

```yaml
scrape_configs:
  - job_name: 'my-go-app'
    static_configs:
      - targets: ['localhost:8080']
```

### 3. Grafana Dashboard

导入 Dashboard ID: `10263`（Go 应用模板）或自定义：
- QPS 面板
- P99/P95/P50 延迟面板
- 错误率面板
- Goroutine 数量面板

---

## 📚 扩展阅读

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [PromQL 完整参考](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Prometheus 监控实战](https://github.com/burningalchemist/monitoring-prometheus)
- [Relabeling 详解](https://www.robustperception.io/relabelling-can-discard-targets-metrics-and-more)
