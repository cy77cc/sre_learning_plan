# Day 67: 实战项目 — Prometheus Exporter

> 📅 日期：2026-05-02  
> 📖 学习主题：实战项目：Prometheus Exporter  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Prometheus Exporter 的工作原理
- 能用 Go 编写自定义 Exporter，暴露 /metrics 端点
- 理解 Prometheus 指标类型（Counter、Gauge、Histogram、Summary）
- 用 prometheus/client_golang 库注册和采集指标
- 将自定义 Exporter 集成到 Prometheus 的 scrape 配置中

---

## 📖 详细知识点

### 1. Exporter 原理

Prometheus 采用 **Pull 模型**：Prometheus Server 定期向目标 HTTP 端点拉取指标。Exporter 就是一个 HTTP 服务，响应 `/metrics` 请求，返回 Prometheus 文本格式：

```
# HELP http_requests_total Total HTTP requests received.
# TYPE http_requests_total counter
http_requests_total{method="GET",status="200"} 1024
http_requests_total{method="POST",status="201"} 56

# HELP memory_usage_bytes Current memory usage in bytes.
# TYPE memory_usage_bytes gauge
memory_usage_bytes 524288000
```

**关键格式规则**：
```
# HELP <指标名> 描述信息
# TYPE <指标名> <类型>
<指标名>{标签名="标签值"} 数值 [时间戳]
```

### 2. Prometheus 四种指标类型

| 类型 | 说明 | 适用场景 | 示例 |
|------|------|----------|------|
| **Counter** | 只增不减的计数器 | 请求数、错误数、总流量 | http_requests_total |
| **Gauge** | 可增可减的仪表盘 | CPU、内存、温度 | node_memory_used_bytes |
| **Histogram** | 分布统计（分桶） | 请求延迟、响应大小 | http_request_duration_seconds |
| **Summary** | 客户端分位统计 | 延迟的 P50/P90/P99 | api_latency_seconds |

### 3. 用 Go 编写 Node Exporter

#### 3.1 项目结构

```
node-exporter/
├── go.mod
├── main.go              # 主入口
├── collectors/
│   ├── collector.go     # Collector 接口
│   ├── cpu.go           # CPU 指标
│   ├── memory.go        # 内存指标
│   └── disk.go          # 磁盘指标
└── Dockerfile
```

#### 3.2 Collector 接口

```go
// collectors/collector.go
package collectors

import "github.com/prometheus/client_golang/prometheus"

// Collector 定义所有采集器必须实现的接口
type Collector interface {
    // Name 返回采集器名称
    Name() string
    // Describe 发送指标描述到 channel（用于 prometheus.Registry）
    Describe(ch chan<- *prometheus.Desc)
    // Collect 采集指标并发送到 channel
    Collect(ch chan<- prometheus.Metric)
}
```

#### 3.3 CPU 采集器

```go
// collectors/cpu.go
package collectors

import (
    "fmt"
    "os"
    "strconv"
    "strings"
    "time"

    "github.com/prometheus/client_golang/prometheus"
)

type CPUCollector struct {
    cpuDesc    *prometheus.Desc
    idleDesc   *prometheus.Desc
    iowaitDesc *prometheus.Desc
}

func NewCPUCollector() *CPUCollector {
    return &CPUCollector{
        cpuDesc: prometheus.NewDesc(
            "node_cpu_seconds_total",
            "Total CPU seconds per mode",
            []string{"mode"}, nil,
        ),
        idleDesc: prometheus.NewDesc(
            "node_cpu_idle_seconds",
            "CPU idle seconds",
            nil, nil,
        ),
        iowaitDesc: prometheus.NewDesc(
            "node_cpu_iowait_seconds",
            "CPU iowait seconds",
            nil, nil,
        ),
    }
}

func (c *CPUCollector) Name() string { return "cpu" }

func (c *CPUCollector) Describe(ch chan<- *prometheus.Desc) {
    ch <- c.cpuDesc
    ch <- c.idleDesc
    ch <- c.iowaitDesc
}

func (c *CPUCollector) Collect(ch chan<- prometheus.Metric) {
    stats := readCPUStats()
    ch <- prometheus.MustNewConstMetric(
        c.cpuDesc, prometheus.CounterValue, stats.user, "user",
    )
    ch <- prometheus.MustNewConstMetric(
        c.cpuDesc, prometheus.CounterValue, stats.system, "system",
    )
    ch <- prometheus.MustNewConstMetric(
        c.cpuDesc, prometheus.CounterValue, stats.idle, "idle",
    )
    ch <- prometheus.MustNewConstMetric(
        c.cpuDesc, prometheus.CounterValue, stats.iowait, "iowait",
    )
    ch <- prometheus.MustNewConstMetric(
        c.idleDesc, prometheus.GaugeValue, stats.idle,
    )
    ch <- prometheus.MustNewConstMetric(
        c.iowaitDesc, prometheus.GaugeValue, stats.iowait,
    )
}

type cpuStats struct {
    user, system, idle, iowait float64
}

func readCPUStats() cpuStats {
    data, _ := os.ReadFile("/proc/stat")
    for _, line := range strings.Split(string(data), "\n") {
        if strings.HasPrefix(line, "cpu ") {
            fields := strings.Fields(line)
            user, _ := strconv.ParseFloat(fields[1], 64)
            system, _ := strconv.ParseFloat(fields[3], 64)
            idle, _ := strconv.ParseFloat(fields[4], 64)
            iowait, _ := strconv.ParseFloat(fields[5], 64)
            // /proc/stat 的值是 USER_HZ 单位（通常是 1/100 秒）
            return cpuStats{
                user: user / 100.0,
                system: system / 100.0,
                idle: idle / 100.0,
                iowait: iowait / 100.0,
            }
        }
    }
    return cpuStats{}
}
```

#### 3.4 内存采集器

```go
// collectors/memory.go
package collectors

import (
    "os"
    "regexp"
    "strconv"
    "strings"

    "github.com/prometheus/client_golang/prometheus"
)

type MemoryCollector struct {
    totalDesc     *prometheus.Desc
    availableDesc *prometheus.Desc
    freeDesc      *prometheus.Desc
    buffersDesc   *prometheus.Desc
    cachedDesc    *prometheus.Desc
}

func NewMemoryCollector() *MemoryCollector {
    return &MemoryCollector{
        totalDesc: prometheus.NewDesc(
            "node_memory_total_bytes", "Total memory in bytes", nil, nil,
        ),
        availableDesc: prometheus.NewDesc(
            "node_memory_available_bytes", "Available memory in bytes", nil, nil,
        ),
        freeDesc: prometheus.NewDesc(
            "node_memory_free_bytes", "Free memory in bytes", nil, nil,
        ),
        buffersDesc: prometheus.NewDesc(
            "node_memory_buffers_bytes", "Buffer memory in bytes", nil, nil,
        ),
        cachedDesc: prometheus.NewDesc(
            "node_memory_cached_bytes", "Cached memory in bytes", nil, nil,
        ),
    }
}

func (c *MemoryCollector) Name() string { return "memory" }

func (c *MemoryCollector) Describe(ch chan<- *prometheus.Desc) {
    ch <- c.totalDesc
    ch <- c.availableDesc
    ch <- c.freeDesc
    ch <- c.buffersDesc
    ch <- c.cachedDesc
}

func (c *MemoryCollector) Collect(ch chan<- prometheus.Metric) {
    metrics := parseMemInfo()
    if v, ok := metrics["MemTotal"]; ok {
        ch <- prometheus.MustNewConstMetric(c.totalDesc, prometheus.GaugeValue, v)
    }
    if v, ok := metrics["MemAvailable"]; ok {
        ch <- prometheus.MustNewConstMetric(c.availableDesc, prometheus.GaugeValue, v)
    }
    if v, ok := metrics["MemFree"]; ok {
        ch <- prometheus.MustNewConstMetric(c.freeDesc, prometheus.GaugeValue, v)
    }
    if v, ok := metrics["Buffers"]; ok {
        ch <- prometheus.MustNewConstMetric(c.buffersDesc, prometheus.GaugeValue, v)
    }
    if v, ok := metrics["Cached"]; ok {
        ch <- prometheus.MustNewConstMetric(c.cachedDesc, prometheus.GaugeValue, v)
    }
}

func parseMemInfo() map[string]float64 {
    result := make(map[string]float64)
    data, _ := os.ReadFile("/proc/meminfo")
    re := regexp.MustCompile(`^(\w+):\s+(\d+)`)
    for _, line := range strings.Split(string(data), "\n") {
        matches := re.FindStringSubmatch(line)
        if len(matches) == 3 {
            value, _ := strconv.ParseFloat(matches[2], 64)
            // /proc/meminfo 的值单位是 kB，转为 bytes
            result[matches[1]] = value * 1024
        }
    }
    return result
}
```

#### 3.5 主程序

```go
// main.go
package main

import (
    "fmt"
    "log"
    "net/http"
    "os"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"

    "node-exporter/collectors"
)

func main() {
    // 创建自定义 Registry
    reg := prometheus.NewRegistry()

    // 注册 Go runtime 指标
    reg.MustRegister(prometheus.NewBuildInfoCollector())
    reg.MustRegister(prometheus.NewGoCollector())

    // 注册自定义采集器
    reg.MustRegister(collectors.NewCPUCollector())
    reg.MustRegister(collectors.NewMemoryCollector())
    reg.MustRegister(collectors.NewDiskCollector())

    // 健康检查
    http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("OK"))
    })

    // 暴露 /metrics 端点
    http.Handle("/metrics", promhttp.HandlerFor(reg, promhttp.HandlerOpts{
        EnableOpenMetrics: true,
    }))

    port := os.Getenv("PORT")
    if port == "" {
        port = "9100"
    }

    log.Printf("🚀 Node Exporter starting on :%s", port)
    log.Printf("📊 Metrics: http://localhost:%s/metrics", port)
    log.Printf("❤️  Health: http://localhost:%s/health", port)

    if err := http.ListenAndServe(":"+port, nil); err != nil {
        log.Fatalf("❌ Failed to start server: %v", err)
    }
}
```

#### 3.6 go.mod

```go
module node-exporter

go 1.22

require github.com/prometheus/client_golang v1.18.0
```

### 4. Prometheus 配置集成

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
        labels:
          instance: 'sre-server'

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 5. 验证

```bash
# 1. 运行 Exporter
cd node-exporter
go run main.go

# 2. 查看 /metrics 端点
curl http://localhost:9100/metrics

# 3. 预期输出
# TYPE node_cpu_seconds_total counter
# node_cpu_seconds_total{mode="user"} 1234.56
# node_cpu_seconds_total{mode="system"} 567.89
# node_cpu_seconds_total{mode="idle"} 8901.23
# TYPE node_memory_total_bytes gauge
# node_memory_total_bytes 8.388608e+09

# 4. 配置 Prometheus scrape 后，在 Grafana 查询
# node_cpu_seconds_total
# node_memory_available_bytes
```

### 6. SRE 实战案例

```
场景：需要监控一个没有暴露指标的遗留系统
方案：
1. 编写 Sidecar Exporter 进程，监控进程 PID、CPU、内存
2. 用 /proc/<pid>/stat 读取进程指标
3. 通过 /metrics 暴露给 Prometheus
4. 配置告警规则：进程 CPU > 90% 持续 5 分钟
```

---

## 💻 实战练习

### 练习 1：编写进程监控 Exporter

要求：
- 监控指定 PID 的进程
- 采集：CPU%、内存%、打开文件数、线程数
- 用 /proc/<pid>/ 目录下的文件
- 支持通过命令行参数 `--pid` 指定进程

### 练习 2：编写 HTTP 服务 Exporter

要求：
- 监控 Nginx 的 active connections、reading/writing/waiting
- 通过 Nginx stub_status 模块获取
- 暴露为 Prometheus 指标

### 练习 3：Docker 容器化

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /exporter

FROM alpine:3.19
COPY --from=builder /exporter /usr/local/bin/exporter
EXPOSE 9100
ENTRYPOINT ["/usr/local/bin/exporter"]
```

---

## 📚 推荐资源

- [Prometheus 官方文档](https://prometheus.io/docs/introduction/overview/)
- [Prometheus Go 客户端库](https://github.com/prometheus/client_golang)
- [Writing Exporters — 官方指南](https://prometheus.io/docs/instrumenting/writing_exporters/)
- [node_exporter 源码](https://github.com/prometheus/node_exporter) — 学习最佳实践

---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| 指标格式错误 | 确保 HELP 和 TYPE 注释在指标行之前 |
| 采集器未注册 | 用 reg.MustRegister 而不是 http.Handle |

### 延伸思考

- 如何避免 Exporter 成为 Prometheus 的单点故障？
- 大量指标时如何优化采集性能？

---

## ✅ 完成检查

- [ ] 理解 Prometheus 四种指标类型的区别和适用场景
- [ ] 能用 Go 编写自定义 Collector 并注册到 Registry
- [ ] 能从 /proc 读取系统指标并暴露为 Prometheus 格式
- [ ] 能配置 Prometheus scrape 自定义 Exporter
- [ ] 完成练习 1：进程监控 Exporter
- [ ] 完成练习 2：HTTP 服务 Exporter

---

*由 SRE 学习计划自动生成 | 2026-05-02*  
*Generated by Hermes Agent with review*
