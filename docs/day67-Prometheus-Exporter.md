# Day 67: Prometheus Exporter

> 📅 日期：2026-05-03
> 📖 学习主题：Prometheus 客户端库、指标类型、自定义 Exporter、Pushgateway 与完整 SRE 监控实现
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 62 并发编程、Day 63 标准库与网络编程、Day 65 Context 与超时控制

## 🎯 学习目标

完成 Day 67 的学习后，你应该能够：
1. 理解 Prometheus Pull 模型和指标暴露机制
2. 熟练使用 Counter、Gauge、Histogram、Summary 四种指标类型
3. 实现自定义 Collector 和注册机制
4. 编写完整的自定义 Exporter（HTTP 服务 + 指标采集 + /metrics 端点）
5. 使用 Pushgateway 处理批处理任务的指标推送
6. 将 Exporter 集成到 Prometheus 的 scrape 配置中

---

## 📖 核心知识点

### 1. Prometheus 监控体系概述

#### 1.1 Prometheus 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Prometheus 监控架构                           │
│                                                                   │
│  ┌──────────────┐     Pull (HTTP GET)      ┌──────────────────┐ │
│  │  Prometheus   │ ───────────────────────→ │  Exporter A      │ │
│  │  Server       │     /metrics              │  (Node Exporter) │ │
│  │               │                           └──────────────────┘ │
│  │  ┌──────────┐ │     Pull (HTTP GET)      ┌──────────────────┐ │
│  │  │  TSDB    │ │ ───────────────────────→ │  Exporter B      │ │
│  │  │ (存储)   │ │     /metrics              │  (自定义 Exporter)│ │
│  │  └──────────┘ │                           └──────────────────┘ │
│  │               │     Pull (HTTP GET)      ┌──────────────────┐ │
│  │  ┌──────────┐ │ ───────────────────────→ │  Exporter C      │ │
│  │  │ PromQL   │ │     /metrics              │  (应用内置指标)  │ │
│  │  │ (查询)   │ │                           └──────────────────┘ │
│  │  └──────────┘ │                                                  │
│  └───────┬───────┘                                                  │
│          │                                                          │
│          ▼                                                          │
│  ┌──────────────┐     Push                  ┌──────────────────┐ │
│  │  Alertmanager │ ←───────────────────── │  Pushgateway     │ │
│  │  (告警)       │                           │  (批处理任务)    │ │
│  └──────────────┘                           └──────────────────┘ │
│          │                                                          │
│          ▼                                                          │
│  ┌──────────────┐     查询                  ┌──────────────────┐ │
│  │  Grafana     │ ←───────────────────── │  用户            │ │
│  │  (可视化)    │                           └──────────────────┘ │
│  └──────────────┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.2 Pull vs Push 模型

| 特性 | Pull (Scrape) | Push (Pushgateway) |
|------|---------------|-------------------|
| 方向 | Prometheus 主动拉取 | 应用主动推送 |
| 适用场景 | 长期运行的服务 | 短生命周期任务（CronJob） |
| 服务发现 | 支持（Consul、DNS、K8s） | 不需要 |
| 健康检查 | 天然支持（scrape 失败=宕机） | 需要额外实现 |
| 推荐程度 | **首选** | 特定场景使用 |

#### 1.3 指标文本格式

```
# HELP http_requests_total Total number of HTTP requests.
# TYPE http_requests_total counter
http_requests_total{method="GET", handler="/api/users", status="200"} 1027
http_requests_total{method="POST", handler="/api/users", status="201"} 3

# HELP http_request_duration_seconds HTTP request duration in seconds.
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{handler="/api/users",le="0.005"} 0
http_request_duration_seconds_bucket{handler="/api/users",le="0.01"} 5
http_request_duration_seconds_bucket{handler="/api/users",le="0.025"} 12
http_request_duration_seconds_bucket{handler="/api/users",le="0.05"} 25
http_request_duration_seconds_bucket{handler="/api/users",le="0.1"} 48
http_request_duration_seconds_bucket{handler="/api/users",le="0.25"} 95
http_request_duration_seconds_bucket{handler="/api/users",le="0.5"} 100
http_request_duration_seconds_bucket{handler="/api/users",le="1"} 102
http_request_duration_seconds_bucket{handler="/api/users",le="+Inf"} 103
http_request_duration_seconds_sum 18.42
http_request_duration_seconds_count 103

# HELP go_goroutines Number of goroutines that currently exist.
# TYPE go_goroutines gauge
go_goroutines 42
```

---

### 2. Prometheus 客户端库（Go）

#### 2.1 安装

```bash
go get github.com/prometheus/client_golang/prometheus
go get github.com/prometheus/client_golang/prometheus/promhttp
```

#### 2.2 四种指标类型详解

##### Counter（计数器）

Counter 是只增不减的计数器，重启时归零。适用于累计值统计。

```go
package main

import (
    "net/http"
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

// 定义 Counter
var httpRequestsTotal = prometheus.NewCounterVec(
    prometheus.CounterOpts{
        Namespace: "sre",           // 命名空间
        Subsystem: "http",          // 子系统
        Name:      "requests_total", // 指标名
        Help:      "Total number of HTTP requests", // 帮助信息
    },
    []string{"method", "handler", "status"}, // 标签
)

func init() {
    // 注册指标
    prometheus.MustRegister(httpRequestsTotal)
}

// 使用 Counter
func recordRequest(method, handler, status string) {
    httpRequestsTotal.With(prometheus.Labels{
        "method":  method,
        "handler": handler,
        "status":  status,
    }).Inc() // 增加 1
}

func recordRequestN(method, handler, status string, n float64) {
    httpRequestsTotal.With(prometheus.Labels{
        "method":  method,
        "handler": handler,
        "status":  status,
    }).Add(n) // 增加 n
}

func main() {
    http.Handle("/metrics", promhttp.Handler())
    http.ListenAndServe(":9090", nil)
}
```

**Counter 最佳实践：**
```go
// 好：使用标签区分维度
var requests = prometheus.NewCounterVec(
    prometheus.CounterOpts{Name: "http_requests_total"},
    []string{"method", "status"},
)

// 坏：为每个端点创建独立 Counter
var getRequests = prometheus.NewCounter(...)
var postRequests = prometheus.NewCounter(...)
```

##### Gauge（仪表盘）

Gauge 是可增可减的值，反映当前状态。

```go
var (
    // 当前活跃连接数
    activeConnections = prometheus.NewGauge(
        prometheus.GaugeOpts{
            Namespace: "sre",
            Name:      "active_connections",
            Help:      "Number of active connections",
        },
    )

    // 带标签的 Gauge
    cpuUsage = prometheus.NewGaugeVec(
        prometheus.GaugeOpts{
            Namespace: "sre",
            Name:      "cpu_usage_percent",
            Help:      "CPU usage percentage",
        },
        []string{"core"},
    )

    // 内存使用
    memoryUsage = prometheus.NewGaugeVec(
        prometheus.GaugeOpts{
            Namespace: "sre",
            Name:      "memory_usage_bytes",
            Help:      "Memory usage in bytes",
        },
        []string{"type"}, // type: used, free, cached, buffers
    )
)

func init() {
    prometheus.MustRegister(activeConnections, cpuUsage, memoryUsage)
}

func updateMetrics() {
    activeConnections.Inc()           // 增加 1
    activeConnections.Dec()           // 减少 1
    activeConnections.Set(42)         // 设置为 42
    activeConnections.Add(5)          // 增加 5
    activeConnections.Sub(3)          // 减少 3

    cpuUsage.WithLabelValues("0").Set(75.5)
    cpuUsage.WithLabelValues("1").Set(82.3)

    memoryUsage.WithLabelValues("used").Set(4 * 1024 * 1024 * 1024)
    memoryUsage.WithLabelValues("free").Set(2 * 1024 * 1024 * 1024)
}
```

##### Histogram（直方图）

Histogram 对观测值进行分桶统计，自动计算分位数（服务端）。

```go
var (
    // 请求延迟分布
    requestDuration = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{
            Namespace: "sre",
            Name:      "http_request_duration_seconds",
            Help:      "HTTP request duration in seconds",
            Buckets:   []float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10},
        },
        []string{"method", "handler"},
    )

    // 响应大小分布
    responseSize = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{
            Namespace: "sre",
            Name:      "http_response_size_bytes",
            Help:      "HTTP response size in bytes",
            Buckets:   prometheus.ExponentialBuckets(100, 2, 10), // 100, 200, 400, ..., 51200
        },
        []string{"method", "handler"},
    )
)

func init() {
    prometheus.MustRegister(requestDuration, responseSize)
}

// 使用 Histogram 记录延迟
func recordDuration(method, handler string, duration time.Duration) {
    requestDuration.WithLabelValues(method, handler).Observe(duration.Seconds())
}

// 使用计时器模式
func middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        timer := prometheus.NewTimer(requestDuration.WithLabelValues(r.Method, r.URL.Path))
        defer timer.ObserveDuration() // 自动记录耗时

        next.ServeHTTP(w, r)

        // 记录响应大小
        // responseSize.WithLabelValues(r.Method, r.URL.Path).Observe(float64(written))
    })
}
```

**Histogram 自动产生的指标：**
```
# 以下指标由 Histogram 自动生成：
sre_http_request_duration_seconds_bucket{le="0.001"} 0
sre_http_request_duration_seconds_bucket{le="0.005"} 5
sre_http_request_duration_seconds_bucket{le="0.01"} 12
...
sre_http_request_duration_seconds_bucket{le="+Inf"} 100
sre_http_request_duration_seconds_sum 25.5
sre_http_request_duration_seconds_count 100
```

##### Summary（摘要）

Summary 在客户端计算分位数，直接暴露 P50、P90、P99 等值。

```go
var (
    apiLatency = prometheus.NewSummaryVec(
        prometheus.SummaryOpts{
            Namespace:  "sre",
            Name:       "api_latency_seconds",
            Help:       "API latency in seconds",
            Objectives: map[float64]float64{
                0.5:  0.05,  // P50，误差 5%
                0.9:  0.01,  // P90，误差 1%
                0.99: 0.001, // P99，误差 0.1%
            },
            MaxAge:     10 * time.Minute, // 滑动窗口
            AgeBuckets: 5,                // 窗口分桶数
            BufCap:     500,              // 缓冲区大小
        },
        []string{"endpoint"},
    )
)

func init() {
    prometheus.MustRegister(apiLatency)
}

func recordLatency(endpoint string, duration time.Duration) {
    apiLatency.WithLabelValues(endpoint).Observe(duration.Seconds())
}
```

**Summary 产生的指标：**
```
sre_api_latency_seconds{endpoint="/api/users",quantile="0.5"} 0.025
sre_api_latency_seconds{endpoint="/api/users",quantile="0.9"} 0.085
sre_api_latency_seconds{endpoint="/api/users",quantile="0.99"} 0.250
sre_api_latency_seconds_sum{endpoint="/api/users"} 45.2
sre_api_latency_seconds_count{endpoint="/api/users"} 1000
```

##### Histogram vs Summary 对比

| 特性 | Histogram | Summary |
|------|-----------|---------|
| 分位数计算 | 服务端（PromQL） | 客户端（Go 代码） |
| 可聚合 | 是（多实例可合并） | 否（分位数不可合并） |
| 精度 | 取决于桶划分 | 可配置误差 |
| 额外指标 | _bucket, _sum, _count | _sum, _count |
| 推荐场景 | **大多数场景** | 需要精确客户端分位数 |

**SRE 建议：** 优先使用 Histogram，除非你明确需要客户端分位数且不需要跨实例聚合。

---

### 3. 注册机制与 Registry

#### 3.1 默认注册器

```go
package main

import (
    "github.com/prometheus/client_golang/prometheus"
)

// 使用默认注册器（MustRegister）
var myCounter = prometheus.NewCounter(
    prometheus.CounterOpts{
        Name: "my_counter",
        Help: "A simple counter",
    },
)

func init() {
    // 注册到默认注册器
    prometheus.MustRegister(myCounter)

    // 也可以使用 Register（返回 error）
    if err := prometheus.Register(myCounter); err != nil {
        // 处理重复注册等错误
        if are, ok := err.(prometheus.AlreadyRegisteredError); ok {
            // 指标已注册，使用已有的
            myCounter = are.ExistingCollector.(prometheus.Counter)
        }
    }
}
```

#### 3.2 自定义注册器

```go
package main

import (
    "net/http"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

// 自定义注册器
var registry = prometheus.NewRegistry()

// 注册标准指标（Go runtime、进程信息）
func init() {
    // 注册 Go 运行时指标
    registry.MustRegister(prometheus.NewGoCollector())
    // 注册进程指标
    registry.MustRegister(prometheus.NewProcessCollector(prometheus.ProcessCollectorOpts{}))
}

func setupMetrics() {
    // 在自定义注册器中注册指标
    myCounter := prometheus.NewCounter(
        prometheus.CounterOpts{
            Name: "my_custom_counter",
            Help: "Custom counter in custom registry",
        },
    )
    registry.MustRegister(myCounter)
}

func main() {
    setupMetrics()

    // 使用自定义注册器的 Handler
    handler := promhttp.HandlerFor(registry, promhttp.HandlerOpts{
        EnableOpenMetrics: true,
    })

    http.Handle("/metrics", handler)
    http.ListenAndServe(":9090", nil)
}
```

#### 3.3 不使用注册器（直接输出）

```go
package main

import (
    "fmt"
    "net/http"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/common/expfmt"
)

func customMetricsHandler(w http.ResponseWriter, r *http.Request) {
    // 收集所有指标
    mfs, err := prometheus.DefaultGatherer.Gather()
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    // 输出为文本格式
    w.Header().Set("Content-Type", string(expfmt.FmtText))
    for _, mf := range mfs {
        expfmt.MetricFamilyToText(w, mf)
    }
}
```

---

### 4. 自定义 Collector

#### 4.1 Collector 接口

```go
// Collector 接口定义
type Collector interface {
    // Describe 发送指标描述符到 channel
    Describe(chan<- *Desc)
    // Collect 发送指标数据到 channel
    Collect(chan<- Metric)
}
```

#### 4.2 实现自定义 Collector

当需要从外部系统获取指标数据时，使用自定义 Collector：

```go
package main

import (
    "sync"

    "github.com/prometheus/client_golang/prometheus"
)

// SystemCollector 自定义系统指标收集器
type SystemCollector struct {
    cpuUsage    *prometheus.Desc
    memoryTotal *prometheus.Desc
    memoryUsed  *prometheus.Desc
    diskTotal   *prometheus.Desc
    diskUsed    *prometheus.Desc
    mu          sync.RWMutex
}

// NewSystemCollector 创建系统指标收集器
func NewSystemCollector() *SystemCollector {
    return &SystemCollector{
        cpuUsage: prometheus.NewDesc(
            "system_cpu_usage_percent",
            "Current CPU usage percentage",
            []string{"core"},
            nil,
        ),
        memoryTotal: prometheus.NewDesc(
            "system_memory_total_bytes",
            "Total system memory in bytes",
            nil,
            nil,
        ),
        memoryUsed: prometheus.NewDesc(
            "system_memory_used_bytes",
            "Used system memory in bytes",
            nil,
            nil,
        ),
        diskTotal: prometheus.NewDesc(
            "system_disk_total_bytes",
            "Total disk space in bytes",
            []string{"mountpoint"},
            nil,
        ),
        diskUsed: prometheus.NewDesc(
            "system_disk_used_bytes",
            "Used disk space in bytes",
            []string{"mountpoint"},
            nil,
        ),
    }
}

// Describe 实现 Collector 接口
func (c *SystemCollector) Describe(ch chan<- *prometheus.Desc) {
    ch <- c.cpuUsage
    ch <- c.memoryTotal
    ch <- c.memoryUsed
    ch <- c.diskTotal
    ch <- c.diskUsed
}

// Collect 实现 Collector 接口，采集实际数据
func (c *SystemCollector) Collect(ch chan<- prometheus.Metric) {
    // 采集 CPU 使用率
    cpuData := collectCPUUsage()
    for core, usage := range cpuData {
        ch <- prometheus.MustNewConstMetric(
            c.cpuUsage,
            prometheus.GaugeValue,
            usage,
            core,
        )
    }

    // 采集内存信息
    memTotal, memUsed := collectMemoryInfo()
    ch <- prometheus.MustNewConstMetric(c.memoryTotal, prometheus.GaugeValue, float64(memTotal))
    ch <- prometheus.MustNewConstMetric(c.memoryUsed, prometheus.GaugeValue, float64(memUsed))

    // 采集磁盘信息
    diskData := collectDiskInfo()
    for mp, info := range diskData {
        ch <- prometheus.MustNewConstMetric(c.diskTotal, prometheus.GaugeValue, float64(info.total), mp)
        ch <- prometheus.MustNewConstMetric(c.diskUsed, prometheus.GaugeValue, float64(info.used), mp)
    }
}

// 采集函数（简化实现）
func collectCPUUsage() map[string]float64 {
    // 实际实现应读取 /proc/stat
    return map[string]float64{
        "0": 45.2,
        "1": 32.8,
    }
}

func collectMemoryInfo() (total, used uint64) {
    // 实际实现应读取 /proc/meminfo
    return 8 * 1024 * 1024 * 1024, 5 * 1024 * 1024 * 1024
}

type DiskInfo struct {
    total uint64
    used  uint64
}

func collectDiskInfo() map[string]DiskInfo {
    // 实际实现应使用 syscall.Statfs
    return map[string]DiskInfo{
        "/":     {100 * 1024 * 1024 * 1024, 60 * 1024 * 1024 * 1024},
        "/data": {500 * 1024 * 1024 * 1024, 200 * 1024 * 1024 * 1024},
    }
}

func main() {
    collector := NewSystemCollector()
    prometheus.MustRegister(collector)

    // ... 启动 HTTP 服务器
}
```

---

### 5. 完整 Exporter 实现：SRE 服务健康检查 Exporter

#### 5.1 项目结构

```
sre-health-exporter/
├── main.go              # 入口
├── collector.go         # 自定义 Collector
├── checker.go           # 健康检查逻辑
├── config.go            # 配置
├── go.mod
├── go.sum
└── config.yaml          # 配置文件
```

#### 5.2 配置文件 (config.yaml)

```yaml
# 监控目标配置
targets:
  - name: "web-api"
    url: "http://web-api:8080/health"
    timeout: 5s
    interval: 30s

  - name: "database"
    type: "tcp"
    address: "db-master:3306"
    timeout: 3s

  - name: "redis"
    type: "tcp"
    address: "redis:6379"
    timeout: 2s

  - name: "external-api"
    url: "https://api.external.com/health"
    timeout: 10s

server:
  port: 9100
  path: /metrics
```

#### 5.3 完整实现代码

```go
// main.go
package main

import (
    "context"
    "flag"
    "fmt"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
    "gopkg.in/yaml.v3"
)

func main() {
    configFile := flag.String("config", "config.yaml", "配置文件路径")
    port := flag.Int("port", 9100, "HTTP 服务端口")
    flag.Parse()

    // 加载配置
    cfg, err := loadConfig(*configFile)
    if err != nil {
        log.Fatalf("加载配置失败: %v", err)
    }

    // 创建注册器
    registry := prometheus.NewRegistry()

    // 注册标准指标
    registry.MustRegister(prometheus.NewGoCollector())
    registry.MustRegister(prometheus.NewProcessCollector(prometheus.ProcessCollectorOpts{}))

    // 创建自定义 Collector
    collector := NewHealthCollector(cfg.Targets)
    registry.MustRegister(collector)

    // 启动后台健康检查
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()
    go collector.StartPeriodicCheck(ctx)

    // HTTP 路由
    mux := http.NewServeMux()
    mux.Handle("/metrics", promhttp.HandlerFor(registry, promhttp.HandlerOpts{
        EnableOpenMetrics: true,
    }))
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("OK"))
    })

    server := &http.Server{
        Addr:         fmt.Sprintf(":%d", *port),
        Handler:      mux,
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
    }

    // 优雅关闭
    go func() {
        sigCh := make(chan os.Signal, 1)
        signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
        <-sigCh
        log.Println("收到关闭信号...")
        cancel()
        ctx, _ := context.WithTimeout(context.Background(), 5*time.Second)
        server.Shutdown(ctx)
    }()

    log.Printf("Exporter 启动在 :%d/metrics", *port)
    if err := server.ListenAndServe(); err != http.ErrServerClosed {
        log.Fatalf("服务器异常: %v", err)
    }
}
```

```go
// config.go
package main

import (
    "os"
    "time"

    "gopkg.in/yaml.v3"
)

type Config struct {
    Targets []TargetConfig `yaml:"targets"`
    Server  ServerConfig   `yaml:"server"`
}

type TargetConfig struct {
    Name     string        `yaml:"name"`
    URL      string        `yaml:"url"`
    Type     string        `yaml:"type"` // http, tcp
    Address  string        `yaml:"address"`
    Timeout  time.Duration `yaml:"timeout"`
    Interval time.Duration `yaml:"interval"`
}

type ServerConfig struct {
    Port int    `yaml:"port"`
    Path string `yaml:"path"`
}

func loadConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }

    cfg := &Config{}
    if err := yaml.Unmarshal(data, cfg); err != nil {
        return nil, err
    }

    // 设置默认值
    for i := range cfg.Targets {
        if cfg.Targets[i].Timeout == 0 {
            cfg.Targets[i].Timeout = 5 * time.Second
        }
        if cfg.Targets[i].Interval == 0 {
            cfg.Targets[i].Interval = 30 * time.Second
        }
        if cfg.Targets[i].Type == "" {
            cfg.Targets[i].Type = "http"
        }
    }

    return cfg, nil
}
```

```go
// checker.go
package main

import (
    "context"
    "fmt"
    "net"
    "net/http"
    "time"
)

// CheckResult 健康检查结果
type CheckResult struct {
    Target   string
    Status   float64 // 1 = UP, 0 = DOWN
    Latency  float64 // 秒
    Error    string
    CheckedAt time.Time
}

// HealthChecker 健康检查器
type HealthChecker struct {
    httpClient *http.Client
}

func NewHealthChecker() *HealthChecker {
    return &HealthChecker{
        httpClient: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

// CheckHTTP 检查 HTTP 端点
func (c *HealthChecker) CheckHTTP(ctx context.Context, name, url string, timeout time.Duration) CheckResult {
    start := time.Now()
    result := CheckResult{
        Target:    name,
        CheckedAt: start,
    }

    reqCtx, cancel := context.WithTimeout(ctx, timeout)
    defer cancel()

    req, err := http.NewRequestWithContext(reqCtx, "GET", url, nil)
    if err != nil {
        result.Status = 0
        result.Error = fmt.Sprintf("创建请求失败: %v", err)
        result.Latency = time.Since(start).Seconds()
        return result
    }

    resp, err := c.httpClient.Do(req)
    if err != nil {
        result.Status = 0
        result.Error = err.Error()
        result.Latency = time.Since(start).Seconds()
        return result
    }
    defer resp.Body.Close()

    result.Latency = time.Since(start).Seconds()

    if resp.StatusCode >= 200 && resp.StatusCode < 300 {
        result.Status = 1
    } else {
        result.Status = 0
        result.Error = fmt.Sprintf("HTTP %d", resp.StatusCode)
    }

    return result
}

// CheckTCP 检查 TCP 端口
func (c *HealthChecker) CheckTCP(ctx context.Context, name, address string, timeout time.Duration) CheckResult {
    start := time.Now()
    result := CheckResult{
        Target:    name,
        CheckedAt: start,
    }

    var d net.Dialer
    connCtx, cancel := context.WithTimeout(ctx, timeout)
    defer cancel()

    conn, err := d.DialContext(connCtx, "tcp", address)
    if err != nil {
        result.Status = 0
        result.Error = err.Error()
        result.Latency = time.Since(start).Seconds()
        return result
    }
    conn.Close()

    result.Status = 1
    result.Latency = time.Since(start).Seconds()
    return result
}

// Check 根据配置类型选择检查方式
func (c *HealthChecker) Check(ctx context.Context, cfg TargetConfig) CheckResult {
    switch cfg.Type {
    case "tcp":
        return c.CheckTCP(ctx, cfg.Name, cfg.Address, cfg.Timeout)
    default:
        return c.CheckHTTP(ctx, cfg.Name, cfg.URL, cfg.Timeout)
    }
}
```

```go
// collector.go
package main

import (
    "context"
    "log"
    "sync"
    "time"

    "github.com/prometheus/client_golang/prometheus"
)

// HealthCollector 健康检查指标收集器
type HealthCollector struct {
    targets []TargetConfig
    checker *HealthChecker

    // 指标描述符
    targetUp     *prometheus.Desc
    targetLatency *prometheus.Desc

    // 缓存结果
    mu      sync.RWMutex
    results map[string]CheckResult
}

// NewHealthCollector 创建健康检查收集器
func NewHealthCollector(targets []TargetConfig) *HealthCollector {
    return &HealthCollector{
        targets: targets,
        checker: NewHealthChecker(),
        results: make(map[string]CheckResult),
        targetUp: prometheus.NewDesc(
            "sre_health_target_up",
            "Whether the target is up (1) or down (0)",
            []string{"target"},
            nil,
        ),
        targetLatency: prometheus.NewDesc(
            "sre_health_target_latency_seconds",
            "Latency of the health check in seconds",
            []string{"target"},
            nil,
        ),
    }
}

// Describe 实现 Collector 接口
func (c *HealthCollector) Describe(ch chan<- *prometheus.Desc) {
    ch <- c.targetUp
    ch <- c.targetLatency
}

// Collect 实现 Collector 接口
func (c *HealthCollector) Collect(ch chan<- prometheus.Metric) {
    c.mu.RLock()
    defer c.mu.RUnlock()

    for _, result := range c.results {
        ch <- prometheus.MustNewConstMetric(
            c.targetUp,
            prometheus.GaugeValue,
            result.Status,
            result.Target,
        )
        ch <- prometheus.MustNewConstMetric(
            c.targetLatency,
            prometheus.GaugeValue,
            result.Latency,
            result.Target,
        )
    }
}

// StartPeriodicCheck 启动定期健康检查
func (c *HealthCollector) StartPeriodicCheck(ctx context.Context) {
    // 首次立即检查
    c.checkAll(ctx)

    // 定期检查
    ticker := time.NewTicker(15 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            log.Println("停止定期健康检查")
            return
        case <-ticker.C:
            c.checkAll(ctx)
        }
    }
}

// checkAll 并发检查所有目标
func (c *HealthCollector) checkAll(ctx context.Context) {
    var wg sync.WaitGroup

    for _, target := range c.targets {
        wg.Add(1)
        go func(cfg TargetConfig) {
            defer wg.Done()
            result := c.checker.Check(ctx, cfg)

            c.mu.Lock()
            c.results[cfg.Name] = result
            c.mu.Unlock()

            if result.Status == 0 {
                log.Printf("[WARN] 目标 %s 不可达: %s", cfg.Name, result.Error)
            }
        }(target)
    }

    wg.Wait()
}
```

#### 5.4 运行与测试

```bash
# 构建
go build -o sre-health-exporter .

# 运行
./sre-health-exporter -config config.yaml -port 9100

# 测试指标端点
curl http://localhost:9100/metrics

# 输出示例：
# HELP sre_health_target_up Whether the target is up (1) or down (0)
# TYPE sre_health_target_up gauge
sre_health_target_up{target="web-api"} 1
sre_health_target_up{target="database"} 1
sre_health_target_up{target="redis"} 0
# HELP sre_health_target_latency_seconds Latency of the health check in seconds
# TYPE sre_health_target_latency_seconds gauge
sre_health_target_latency_seconds{target="web-api"} 0.025
sre_health_target_latency_seconds{target="database"} 0.003
sre_health_target_latency_seconds{target="redis"} 0
```

---

### 6. Pushgateway

#### 6.1 适用场景

Pushgateway 用于短生命周期任务（CronJob、批处理）的指标推送：

```
┌──────────────┐    Push metrics    ┌──────────────┐    Scrape    ┌──────────────┐
│  CronJob /   │ ────────────────→ │  Pushgateway │ ←─────────── │  Prometheus  │
│  Batch Job   │    HTTP POST      │              │   HTTP GET   │  Server      │
└──────────────┘                   └──────────────┘              └──────────────┘
```

#### 6.2 使用 Pushgateway

```go
package main

import (
    "fmt"
    "time"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/push"
)

func main() {
    // 定义指标
    jobDuration := prometheus.NewHistogram(prometheus.HistogramOpts{
        Name:    "batch_job_duration_seconds",
        Help:    "Duration of batch job",
        Buckets: []float64{1, 5, 10, 30, 60, 120, 300},
    })

    jobSuccess := prometheus.NewCounter(prometheus.CounterOpts{
        Name: "batch_job_success_total",
        Help: "Total successful batch jobs",
    })

    jobErrors := prometheus.NewCounter(prometheus.CounterOpts{
        Name: "batch_job_errors_total",
        Help: "Total failed batch jobs",
    })

    // 执行任务
    start := time.Now()
    err := runBatchJob()
    duration := time.Since(start)

    // 记录指标
    jobDuration.Observe(duration.Seconds())
    if err != nil {
        jobErrors.Inc()
    } else {
        jobSuccess.Inc()
    }

    // 推送到 Pushgateway
    err = push.New("http://pushgateway:9091", "my_batch_job").
        Collector(jobDuration).
        Collector(jobSuccess).
        Collector(jobErrors).
        Grouping("job_id", fmt.Sprintf("%d", time.Now().Unix())).
        Push()

    if err != nil {
        fmt.Printf("推送到 Pushgateway 失败: %v\n", err)
    } else {
        fmt.Println("指标已推送到 Pushgateway")
    }
}

func runBatchJob() error {
    // 模拟批处理任务
    time.Sleep(5 * time.Second)
    return nil
}
```

#### 6.3 推送后清理旧指标

```go
// 任务完成后删除指标（避免过期数据）
err = push.New("http://pushgateway:9091", "my_batch_job").
    Grouping("job_id", jobID).
    Delete()

// 删除该 job 的所有指标
err = push.New("http://pushgateway:9091", "my_batch_job").
    Delete()
```

---

### 7. Prometheus Scrape 配置

#### 7.1 静态配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Prometheus 自身
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  # 自定义 Exporter
  - job_name: "sre-health-exporter"
    scrape_interval: 10s
    static_configs:
      - targets: ["exporter-host:9100"]
    # 指标重标签
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: "go_.*"
        action: drop  # 丢弃 go_ 开头的指标

  # Node Exporter
  - job_name: "node"
    static_configs:
      - targets: ["node1:9100", "node2:9100"]

  # 应用内置指标
  - job_name: "my-app"
    metrics_path: "/api/metrics"
    scheme: "https"
    tls_config:
      insecure_skip_verify: true
    static_configs:
      - targets: ["app1:8080", "app2:8080"]
```

#### 7.2 服务发现配置

```yaml
# 基于 Consul 的服务发现
scrape_configs:
  - job_name: "consul-services"
    consul_sd_configs:
      - server: "consul:8500"
        tags:
          - "prometheus"
    relabel_configs:
      - source_labels: [__meta_consul_service]
        target_label: service
      - source_labels: [__meta_consul_node]
        target_label: node

# 基于 Kubernetes 的服务发现
scrape_configs:
  - job_name: "kubernetes-pods"
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
```

---

### 8. 常用 PromQL 查询

#### 8.1 Counter 查询

```promql
# 请求速率（每秒请求数）
rate(http_requests_total[5m])

# 按方法和状态码分组的请求速率
sum by (method, status) (rate(http_requests_total[5m]))

# 错误率
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# 5 分钟内请求总数增量
increase(http_requests_total[5m])
```

#### 8.2 Gauge 查询

```promql
# CPU 使用率
system_cpu_usage_percent

# 内存使用率
system_memory_used_bytes / system_memory_total_bytes * 100

# 磁盘使用率
system_disk_used_bytes / system_disk_total_bytes * 100
```

#### 8.3 Histogram 查询

```promql
# P99 延迟
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, handler))

# P95 延迟
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# 平均延迟
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

---

## 💻 实战练习

### 练习 1：实现 Redis Exporter

```go
// 任务：实现一个 Exporter，采集 Redis INFO 命令的指标
// 指标包括：
// - redis_up: Redis 是否可达
// - redis_connected_clients: 连接数
// - redis_used_memory_bytes: 内存使用
// - redis_commands_processed_total: 命令处理总数
// - redis_keyspace_hits_total: 命中总数
// - redis_keyspace_misses_total: 未命中总数

package main

import (
    "context"
    "strings"

    "github.com/prometheus/client_golang/prometheus"
)

type RedisCollector struct {
    addr string

    up               *prometheus.Desc
    connectedClients *prometheus.Desc
    usedMemory       *prometheus.Desc
    commandsProcessed *prometheus.Desc
    keyspaceHits     *prometheus.Desc
    keyspaceMisses   *prometheus.Desc
}

func NewRedisCollector(addr string) *RedisCollector {
    return &RedisCollector{
        addr: addr,
        up: prometheus.NewDesc(
            "redis_up",
            "Whether Redis is reachable",
            nil, nil,
        ),
        connectedClients: prometheus.NewDesc(
            "redis_connected_clients",
            "Number of connected clients",
            nil, nil,
        ),
        // ... 其他指标定义
    }
}

func (c *RedisCollector) Describe(ch chan<- *prometheus.Desc) {
    // 实现
}

func (c *RedisCollector) Collect(ch chan<- prometheus.Metric) {
    // 连接 Redis，执行 INFO 命令
    // 解析结果并输出指标
}
```

### 练习 2：实现应用内嵌指标

```go
// 任务：在 HTTP 服务中嵌入 Prometheus 指标
// 1. 请求数（按方法、路径、状态码）
// 2. 请求延迟（Histogram）
// 3. 请求体大小（Histogram）
// 4. 响应体大小（Histogram）
// 5. 活跃请求数（Gauge）
// 6. 错误数（按类型）

package main

import (
    "net/http"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

// 任务：实现 MetricsMiddleware
func MetricsMiddleware(next http.Handler) http.Handler {
    // 实现中间件
    return nil
}
```

### 练习 3：编写完整的 Exporter 测试

```go
package main

import (
    "testing"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/stretchr/testify/assert"
)

// 任务：为 HealthCollector 编写测试
func TestHealthCollector_Describe(t *testing.T) {
    // 验证 Describe 输出正确的描述符
}

func TestHealthCollector_Collect(t *testing.T) {
    // 验证 Collect 输出正确的指标
}

func TestHealthCollector_CheckAll(t *testing.T) {
    // 验证定期检查功能
}
```

---

## 🎯 面试题精选

### 1. Prometheus 的四种指标类型分别是什么？适用场景？

**参考答案：**
- **Counter**：只增不减的计数器，适用于请求总数、错误总数等累计值
- **Gauge**：可增可减的值，适用于温度、内存使用、活跃连接数等当前值
- **Histogram**：分桶统计，适用于延迟分布、响应大小分布，支持服务端计算分位数
- **Summary**：客户端分位数统计，适用于需要精确客户端分位数的场景

### 2. Histogram 和 Summary 的区别？

**参考答案：**
- Histogram 在服务端计算分位数，Summary 在客户端计算
- Histogram 可以跨实例聚合（多个实例的 bucket 可以相加），Summary 的分位数不可聚合
- Histogram 需要预先定义桶边界，Summary 可以配置误差
- 推荐使用 Histogram，除非明确需要客户端分位数

### 3. 什么是 Exporter？如何编写自定义 Exporter？

**参考答案：**
Exporter 是一个 HTTP 服务，暴露 `/metrics` 端点返回 Prometheus 文本格式的指标。编写步骤：
1. 使用 `prometheus/client_golang` 库
2. 定义指标（Counter、Gauge、Histogram、Summary）
3. 注册指标到 Registry
4. 实现 `/metrics` HTTP Handler
5. 可选：实现 Collector 接口从外部系统采集数据

### 4. Pushgateway 的使用场景和注意事项？

**参考答案：**
- 适用于短生命周期任务（CronJob、批处理）
- 任务完成后应删除旧指标，避免过期数据
- 不适用于长期运行的服务（应使用 Pull 模式）
- Pushgateway 单点故障问题：需要高可用部署
- 指标在 Pushgateway 重启后保留（如果配置了持久化）

### 5. 如何避免指标爆炸（Cardinality Explosion）？

**参考答案：**
- 避免使用高基数标签（如用户 ID、请求 ID）
- 使用 `metric_relabel_configs` 丢弃不需要的指标
- 设置 `max_samples_per_query` 限制查询样本数
- 使用 `metric_relabel_configs` 合并低频标签值
- 监控 `prometheus_tsdb_head_series` 指标，设置告警阈值

### 6. `rate()` 和 `increase()` 的区别？

**参考答案：**
- `rate()` 计算每秒的平均速率，适用于 Counter
- `increase()` 计算时间窗口内的总增量
- `rate()` = `increase()` / 时间窗口秒数
- `irate()` 使用最后两个数据点计算瞬时速率，更敏感

### 7. 如何实现优雅关闭（Graceful Shutdown）中的指标采集？

**参考答案：**
- 在 `main` 中捕获 SIGINT/SIGTERM 信号
- 先停止接受新请求
- 等待现有请求完成
- 最后一次采集指标并推送（如果使用 Pushgateway）
- 关闭 HTTP 服务器

### 8. 如何监控 Exporter 本身？

**参考答案：**
- 注册 Go 运行时指标（`prometheus.NewGoCollector()`）
- 注册进程指标（`prometheus.NewProcessCollector()`）
- 监控 Exporter 的 `/metrics` 端点可用性
- 监控 Exporter 的延迟和错误率
- 使用 Prometheus 的 `up` 指标检测 Exporter 是否可达

### 9. 指标命名最佳实践？

**参考答案：**
- 使用 `<namespace>_<subsystem>_<name>_<unit>` 格式
- Counter 以 `_total` 结尾
- 使用标准单位后缀：`_seconds`、`_bytes`、`_total`
- 使用 snake_case 命名
- Help 字段清晰描述指标含义

### 10. 如何在 Kubernetes 中部署 Exporter？

**参考答案：**
- 使用 Deployment 部署 Exporter Pod
- 添加 Prometheus 注解：`prometheus.io/scrape: "true"`
- 配置 Service 和 ServiceMonitor（如果使用 Prometheus Operator）
- 使用 ConfigMap 挂载配置文件
- 设置资源限制（CPU、内存）
- 配置健康检查（livenessProbe、readinessProbe）

---

## 📚 深入阅读

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Prometheus 客户端库（Go）](https://pkg.go.dev/github.com/prometheus/client_golang)
- [PromQL 官方文档](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Prometheus 最佳实践](https://prometheus.io/docs/practices/instrumentation/)
- [Prometheus Exporter 模式](https://prometheus.io/docs/instrumenting/writing_exporters/)
- [Pushgateway 文档](https://github.com/prometheus/pushgateway)
- [Grafana Dashboard 设计](https://grafana.com/docs/grafana/latest/dashboards/)

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出 Prometheus 架构图，说明 Pull 模型工作原理
- [ ] 能解释四种指标类型的区别和适用场景
- [ ] 能说明 Histogram 和 Summary 的优劣对比
- [ ] 能解释 Collector 接口的作用和实现方式

### 实操检查点
- [ ] 能使用 Counter/Gauge/Histogram/Summary 定义和注册指标
- [ ] 能实现自定义 Collector 从外部系统采集数据
- [ ] 能编写完整的 Exporter 并暴露 /metrics 端点
- [ ] 能配置 Prometheus 的 scrape 配置

### 能力验证标准
- [ ] 能独立编写生产级 Exporter（配置、指标、健康检查、优雅关闭）
- [ ] 能使用 Pushgateway 推送批处理任务指标
- [ ] 能编写基本的 PromQL 查询
