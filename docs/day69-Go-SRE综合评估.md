# Day 69: Go SRE 综合评估

> 📅 日期：2026-05-03
> 📖 学习主题：综合项目 — 构建完整 CLI 监控工具、代码审查、性能优化、测试覆盖
> ⏰ 预计学习时间：6-8 小时
> 📋 前置知识：Day 57-68 全部 Go 学习内容

## 🎯 学习目标

完成 Day 69 的学习后，你应该能够：
1. 独立构建一个完整的 CLI 监控工具（集成指标采集、健康检查、告警、Prometheus Exporter）
2. 运用代码审查标准评估 Go 代码质量
3. 使用 pprof 进行性能分析和优化
4. 达到 80% 以上的测试覆盖率
5. 展示 SRE 工程师所需的 Go 综合技能

---

## 📖 核心知识点

### 1. 综合项目：SRE CLI 监控工具 (sre-monitor)

#### 1.1 项目概述

构建一个功能完整的 CLI 监控工具，集成以下能力：
- 系统指标采集（CPU、内存、磁盘、网络）
- 服务健康检查（HTTP、TCP、gRPC）
- Prometheus Exporter（暴露 /metrics 端点）
- 告警规则引擎（阈值告警）
- 配置文件管理（YAML）
- 优雅关闭和信号处理

#### 1.2 项目结构

```
sre-monitor/
├── main.go                 # 入口
├── cmd/
│   ├── root.go             # 根命令
│   ├── serve.go            # 启动监控服务
│   ├── check.go            # 一次性健康检查
│   └── version.go          # 版本信息
├── config/
│   ├── config.go           # 配置加载
│   └── config_test.go      # 配置测试
├── collector/
│   ├── collector.go         # Collector 接口
│   ├── system.go            # 系统指标采集
│   ├── system_test.go       # 系统指标测试
│   ├── health.go            # 健康检查采集
│   └── health_test.go       # 健康检查测试
├── checker/
│   ├── checker.go           # 健康检查器
│   ├── http.go              # HTTP 检查
│   ├── tcp.go               # TCP 检查
│   └── checker_test.go      # 检查器测试
├── alerter/
│   ├── alerter.go           # 告警引擎
│   ├── rule.go              # 告警规则
│   └── alerter_test.go      # 告警测试
├── exporter/
│   ├── exporter.go          # Prometheus Exporter
│   └── exporter_test.go     # Exporter 测试
├── server/
│   ├── server.go            # HTTP 服务器
│   └── middleware.go        # 中间件
├── go.mod
├── go.sum
├── config.example.yaml      # 示例配置
└── README.md
```

#### 1.3 完整实现代码

```go
// main.go
package main

import (
    "os"

    "sre-monitor/cmd"
)

func main() {
    if err := cmd.Execute(); err != nil {
        os.Exit(1)
    }
}
```

```go
// cmd/root.go
package cmd

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
)

var cfgFile string

var rootCmd = &cobra.Command{
    Use:   "sre-monitor",
    Short: "SRE 监控工具",
    Long:  `SRE CLI 监控工具 - 系统指标采集、健康检查、Prometheus Exporter`,
}

func Execute() error {
    return rootCmd.Execute()
}

func init() {
    rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "config.yaml", "配置文件路径")
    rootCmd.AddCommand(serveCmd)
    rootCmd.AddCommand(checkCmd)
    rootCmd.AddCommand(versionCmd)
}
```

```go
// cmd/serve.go
package cmd

import (
    "context"
    "fmt"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
    "github.com/spf13/cobra"

    "sre-monitor/alerter"
    "sre-monitor/collector"
    "sre-monitor/config"
    "sre-monitor/exporter"
    "sre-monitor/server"
)

var serveCmd = &cobra.Command{
    Use:   "serve",
    Short: "启动监控服务",
    RunE: func(cmd *cobra.Command, args []string) error {
        return runServe()
    },
}

func runServe() error {
    // 加载配置
    cfg, err := config.Load(cfgFile)
    if err != nil {
        return fmt.Errorf("加载配置失败: %w", err)
    }

    log.Printf("启动 SRE Monitor (版本: %s)", Version)

    // 创建 Context
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    // 创建 Prometheus 注册器
    registry := prometheus.NewRegistry()
    registry.MustRegister(prometheus.NewGoCollector())
    registry.MustRegister(prometheus.NewProcessCollector(prometheus.ProcessCollectorOpts{}))

    // 创建系统指标 Collector
    sysCollector := collector.NewSystemCollector()
    registry.MustRegister(sysCollector)

    // 创建健康检查 Collector
    healthCollector := collector.NewHealthCollector(cfg.HealthChecks)
    registry.MustRegister(healthCollector)

    // 创建 Prometheus Exporter
    exp := exporter.New(registry)

    // 创建告警引擎
    alertEngine := alerter.New(cfg.Alerts)
    go alertEngine.Start(ctx)

    // 启动后台采集
    go sysCollector.Start(ctx, 15*time.Second)
    go healthCollector.Start(ctx)

    // 创建 HTTP 服务器
    mux := http.NewServeMux()
    mux.Handle("/metrics", exp.Handler())
    mux.HandleFunc("/health", server.HealthHandler)
    mux.HandleFunc("/ready", server.ReadyHandler)

    srv := &http.Server{
        Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
        Handler:      server.WithLogging(server.WithRecovery(mux)),
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 30 * time.Second,
        IdleTimeout:  120 * time.Second,
    }

    // 启动 HTTP 服务器
    go func() {
        log.Printf("HTTP 服务启动在 :%d", cfg.Server.Port)
        if err := srv.ListenAndServe(); err != http.ErrServerClosed {
            log.Printf("HTTP 服务异常: %v", err)
        }
    }()

    // 启动 HTTPS 服务器（如果配置了）
    if cfg.Server.TLSPort > 0 {
        go func() {
            addr := fmt.Sprintf(":%d", cfg.Server.TLSPort)
            log.Printf("HTTPS 服务启动在 %s", addr)
            tlsSrv := &http.Server{
                Addr:         addr,
                Handler:      mux,
                ReadTimeout:  10 * time.Second,
                WriteTimeout: 30 * time.Second,
            }
            if err := tlsSrv.ListenAndServeTLS(cfg.Server.TLSCert, cfg.Server.TLSKey); err != http.ErrServerClosed {
                log.Printf("HTTPS 服务异常: %v", err)
            }
        }()
    }

    // 优雅关闭
    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
    <-sigCh

    log.Println("收到关闭信号，开始优雅关闭...")
    cancel() // 停止后台任务

    shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer shutdownCancel()

    if err := srv.Shutdown(shutdownCtx); err != nil {
        log.Printf("关闭超时: %v", err)
    }

    log.Println("SRE Monitor 已关闭")
    return nil
}
```

```go
// cmd/version.go
package cmd

import (
    "fmt"

    "github.com/spf13/cobra"
)

var (
    Version   = "dev"
    GitCommit = "unknown"
    BuildTime = "unknown"
)

var versionCmd = &cobra.Command{
    Use:   "version",
    Short: "显示版本信息",
    Run: func(cmd *cobra.Command, args []string) {
        fmt.Printf("sre-monitor %s\n", Version)
        fmt.Printf("  Git Commit: %s\n", GitCommit)
        fmt.Printf("  Build Time: %s\n", BuildTime)
    },
}
```

```go
// cmd/check.go
package cmd

import (
    "context"
    "fmt"
    "os"
    "sync"
    "text/tabwriter"
    "time"

    "github.com/spf13/cobra"

    "sre-monitor/checker"
    "sre-monitor/config"
)

var checkCmd = &cobra.Command{
    Use:   "check",
    Short: "执行一次性健康检查",
    RunE: func(cmd *cobra.Command, args []string) error {
        return runCheck()
    },
}

func runCheck() error {
    cfg, err := config.Load(cfgFile)
    if err != nil {
        return fmt.Errorf("加载配置失败: %w", err)
    }

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    var (
        wg      sync.WaitGroup
        mu      sync.Mutex
        results []checker.CheckResult
    )

    for _, hc := range cfg.HealthChecks {
        wg.Add(1)
        go func(cfg config.HealthCheckConfig) {
            defer wg.Done()
            c := checker.New(cfg)
            result := c.Check(ctx)
            mu.Lock()
            results = append(results, result)
            mu.Unlock()
        }(hc)
    }

    wg.Wait()

    // 输出结果
    w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
    fmt.Fprintln(w, "TARGET\tSTATUS\tLATENCY\tERROR")
    for _, r := range results {
        status := "UP"
        if r.Status != 1 {
            status = "DOWN"
        }
        fmt.Fprintf(w, "%s\t%s\t%.3fs\t%s\n", r.Target, status, r.Latency, r.Error)
    }
    w.Flush()

    return nil
}
```

```go
// config/config.go
package config

import (
    "os"
    "time"

    "gopkg.in/yaml.v3"
)

type Config struct {
    Server       ServerConfig        `yaml:"server"`
    HealthChecks []HealthCheckConfig `yaml:"health_checks"`
    Alerts       AlertConfig         `yaml:"alerts"`
    Log          LogConfig           `yaml:"log"`
}

type ServerConfig struct {
    Port     int    `yaml:"port"`
    TLSPort  int    `yaml:"tls_port"`
    TLSCert  string `yaml:"tls_cert"`
    TLSKey   string `yaml:"tls_key"`
}

type HealthCheckConfig struct {
    Name     string        `yaml:"name"`
    Type     string        `yaml:"type"` // http, tcp
    URL      string        `yaml:"url"`
    Address  string        `yaml:"address"`
    Timeout  time.Duration `yaml:"timeout"`
    Interval time.Duration `yaml:"interval"`
}

type AlertConfig struct {
    Rules []AlertRule `yaml:"rules"`
}

type AlertRule struct {
    Name      string  `yaml:"name"`
    Metric    string  `yaml:"metric"`
    Threshold float64 `yaml:"threshold"`
    Operator  string  `yaml:"operator"` // gt, lt, eq
    Duration  string  `yaml:"duration"`
    Channel   string  `yaml:"channel"` // log, webhook
    Webhook   string  `yaml:"webhook"`
}

type LogConfig struct {
    Level  string `yaml:"level"`
    Format string `yaml:"format"` // json, text
}

func Load(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }

    cfg := &Config{
        Server: ServerConfig{
            Port: 9100,
        },
        Log: LogConfig{
            Level:  "info",
            Format: "json",
        },
    }

    if err := yaml.Unmarshal(data, cfg); err != nil {
        return nil, err
    }

    // 设置默认值
    for i := range cfg.HealthChecks {
        if cfg.HealthChecks[i].Timeout == 0 {
            cfg.HealthChecks[i].Timeout = 5 * time.Second
        }
        if cfg.HealthChecks[i].Interval == 0 {
            cfg.HealthChecks[i].Interval = 30 * time.Second
        }
        if cfg.HealthChecks[i].Type == "" {
            cfg.HealthChecks[i].Type = "http"
        }
    }

    return cfg, nil
}
```

```go
// config/config_test.go
package config

import (
    "os"
    "path/filepath"
    "testing"
    "time"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestLoad(t *testing.T) {
    t.Run("正常配置", func(t *testing.T) {
        dir := t.TempDir()
        path := filepath.Join(dir, "config.yaml")

        content := `
server:
  port: 8080
  tls_port: 8443
health_checks:
  - name: web-api
    type: http
    url: "http://localhost:8080/health"
    timeout: 5s
    interval: 30s
  - name: database
    type: tcp
    address: "localhost:3306"
    timeout: 3s
alerts:
  rules:
    - name: high-cpu
      metric: system_cpu_usage_percent
      threshold: 80
      operator: gt
      channel: log
log:
  level: info
  format: json
`
        os.WriteFile(path, []byte(content), 0644)

        cfg, err := Load(path)
        require.NoError(t, err)

        assert.Equal(t, 8080, cfg.Server.Port)
        assert.Equal(t, 8443, cfg.Server.TLSPort)
        assert.Len(t, cfg.HealthChecks, 2)
        assert.Equal(t, "web-api", cfg.HealthChecks[0].Name)
        assert.Equal(t, 5*time.Second, cfg.HealthChecks[0].Timeout)
        assert.Len(t, cfg.Alerts.Rules, 1)
    })

    t.Run("默认值", func(t *testing.T) {
        dir := t.TempDir()
        path := filepath.Join(dir, "config.yaml")

        content := `server:
  port: 8080
health_checks:
  - name: test
    url: "http://localhost:8080/health"
`
        os.WriteFile(path, []byte(content), 0644)

        cfg, err := Load(path)
        require.NoError(t, err)

        assert.Equal(t, 5*time.Second, cfg.HealthChecks[0].Timeout)
        assert.Equal(t, 30*time.Second, cfg.HealthChecks[0].Interval)
        assert.Equal(t, "http", cfg.HealthChecks[0].Type)
    })

    t.Run("文件不存在", func(t *testing.T) {
        _, err := Load("/nonexistent/config.yaml")
        assert.Error(t, err)
    })

    t.Run("无效 YAML", func(t *testing.T) {
        dir := t.TempDir()
        path := filepath.Join(dir, "config.yaml")
        os.WriteFile(path, []byte("invalid: yaml: content:"), 0644)

        _, err := Load(path)
        assert.Error(t, err)
    })
}

func FuzzLoad(f *testing.F) {
    f.Add([]byte(`server: {port: 8080}`))
    f.Add([]byte(`{}`))
    f.Add([]byte(`invalid`))

    f.Fuzz(func(t *testing.T, data []byte) {
        dir := t.TempDir()
        path := filepath.Join(dir, "config.yaml")
        os.WriteFile(path, data, 0644)

        cfg, err := Load(path)
        if err != nil {
            return
        }

        // 不变量检查
        if cfg.Server.Port < 0 || cfg.Server.Port > 65535 {
            t.Errorf("port out of range: %d", cfg.Server.Port)
        }
    })
}
```

```go
// collector/collector.go
package collector

import "github.com/prometheus/client_golang/prometheus"

// Collector 自定义采集器接口
type Collector interface {
    prometheus.Collector
    // Start 启动定期采集
    Start(ctx context.Context, interval time.Duration)
}
```

```go
// collector/system.go
package collector

import (
    "context"
    "math/rand"
    "os"
    "runtime"
    "sync"
    "time"

    "github.com/prometheus/client_golang/prometheus"
)

// SystemCollector 系统指标采集器
type SystemCollector struct {
    cpuUsage    *prometheus.Desc
    memoryTotal *prometheus.Desc
    memoryUsed  *prometheus.Desc
    memoryFree  *prometheus.Desc
    goroutines  *prometheus.Desc

    mu     sync.RWMutex
    cpu    float64
    memTotal uint64
    memUsed  uint64
    memFree  uint64
    numGoroutines int
}

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
        memoryFree: prometheus.NewDesc(
            "system_memory_free_bytes",
            "Free system memory in bytes",
            nil,
            nil,
        ),
        goroutines: prometheus.NewDesc(
            "system_goroutines_count",
            "Number of goroutines",
            nil,
            nil,
        ),
    }
}

func (c *SystemCollector) Describe(ch chan<- *prometheus.Desc) {
    ch <- c.cpuUsage
    ch <- c.memoryTotal
    ch <- c.memoryUsed
    ch <- c.memoryFree
    ch <- c.goroutines
}

func (c *SystemCollector) Collect(ch chan<- prometheus.Metric) {
    c.mu.RLock()
    defer c.mu.RUnlock()

    // CPU
    for i := 0; i < runtime.NumCPU(); i++ {
        ch <- prometheus.MustNewConstMetric(
            c.cpuUsage, prometheus.GaugeValue,
            c.cpu+rand.Float64()*10-5, // 模拟波动
            fmt.Sprintf("%d", i),
        )
    }

    // Memory
    ch <- prometheus.MustNewConstMetric(c.memoryTotal, prometheus.GaugeValue, float64(c.memTotal))
    ch <- prometheus.MustNewConstMetric(c.memoryUsed, prometheus.GaugeValue, float64(c.memUsed))
    ch <- prometheus.MustNewConstMetric(c.memoryFree, prometheus.GaugeValue, float64(c.memFree))

    // Goroutines
    ch <- prometheus.MustNewConstMetric(c.goroutines, prometheus.GaugeValue, float64(c.numGoroutines))
}

func (c *SystemCollector) Start(ctx context.Context, interval time.Duration) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            c.collect()
        }
    }
}

func (c *SystemCollector) collect() {
    c.mu.Lock()
    defer c.mu.Unlock()

    // 读取 /proc/meminfo（简化实现）
    var m runtime.MemStats
    runtime.ReadMemStats(&m)

    c.memTotal = m.Sys
    c.memUsed = m.HeapInuse + m.StackInuse
    c.memFree = m.Sys - c.memUsed
    c.numGoroutines = runtime.NumGoroutine()
    c.cpu = 30 + rand.Float64()*40 // 模拟 CPU 使用率
}
```

```go
// collector/health.go
package collector

import (
    "context"
    "sync"
    "time"

    "github.com/prometheus/client_golang/prometheus"

    "sre-monitor/checker"
    "sre-monitor/config"
)

// HealthCollector 健康检查指标采集器
type HealthCollector struct {
    configs []config.HealthCheckConfig
    checker *checker.Checker

    targetUp    *prometheus.Desc
    targetLatency *prometheus.Desc

    mu      sync.RWMutex
    results map[string]checker.CheckResult
}

func NewHealthCollector(configs []config.HealthCheckConfig) *HealthCollector {
    return &HealthCollector{
        configs: configs,
        checker: checker.New(configs[0]), // 简化
        results: make(map[string]checker.CheckResult),
        targetUp: prometheus.NewDesc(
            "sre_health_target_up",
            "Whether the target is up (1) or down (0)",
            []string{"target"},
            nil,
        ),
        targetLatency: prometheus.NewDesc(
            "sre_health_target_latency_seconds",
            "Health check latency in seconds",
            []string{"target"},
            nil,
        ),
    }
}

func (c *HealthCollector) Describe(ch chan<- *prometheus.Desc) {
    ch <- c.targetUp
    ch <- c.targetLatency
}

func (c *HealthCollector) Collect(ch chan<- prometheus.Metric) {
    c.mu.RLock()
    defer c.mu.RUnlock()

    for _, result := range c.results {
        ch <- prometheus.MustNewConstMetric(
            c.targetUp, prometheus.GaugeValue,
            result.Status, result.Target,
        )
        ch <- prometheus.MustNewConstMetric(
            c.targetLatency, prometheus.GaugeValue,
            result.Latency, result.Target,
        )
    }
}

func (c *HealthCollector) Start(ctx context.Context) {
    // 立即检查一次
    c.checkAll(ctx)

    ticker := time.NewTicker(15 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            c.checkAll(ctx)
        }
    }
}

func (c *HealthCollector) checkAll(ctx context.Context) {
    var wg sync.WaitGroup

    for _, cfg := range c.configs {
        wg.Add(1)
        go func(cfg config.HealthCheckConfig) {
            defer wg.Done()
            ch := checker.New(cfg)
            result := ch.Check(ctx)

            c.mu.Lock()
            c.results[cfg.Name] = result
            c.mu.Unlock()
        }(cfg)
    }

    wg.Wait()
}
```

```go
// checker/checker.go
package checker

import (
    "context"
    "fmt"
    "net"
    "net/http"
    "time"

    "sre-monitor/config"
)

// CheckResult 检查结果
type CheckResult struct {
    Target    string
    Status    float64
    Latency   float64
    Error     string
    CheckedAt time.Time
}

// Checker 健康检查器
type Checker struct {
    config config.HealthCheckConfig
    client *http.Client
}

func New(cfg config.HealthCheckConfig) *Checker {
    return &Checker{
        config: cfg,
        client: &http.Client{Timeout: cfg.Timeout},
    }
}

func (c *Checker) Check(ctx context.Context) CheckResult {
    switch c.config.Type {
    case "tcp":
        return c.checkTCP(ctx)
    default:
        return c.checkHTTP(ctx)
    }
}

func (c *Checker) checkHTTP(ctx context.Context) CheckResult {
    start := time.Now()
    result := CheckResult{
        Target:    c.config.Name,
        CheckedAt: start,
    }

    reqCtx, cancel := context.WithTimeout(ctx, c.config.Timeout)
    defer cancel()

    req, err := http.NewRequestWithContext(reqCtx, "GET", c.config.URL, nil)
    if err != nil {
        result.Status = 0
        result.Error = err.Error()
        result.Latency = time.Since(start).Seconds()
        return result
    }

    resp, err := c.client.Do(req)
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

func (c *Checker) checkTCP(ctx context.Context) CheckResult {
    start := time.Now()
    result := CheckResult{
        Target:    c.config.Name,
        CheckedAt: start,
    }

    var d net.Dialer
    connCtx, cancel := context.WithTimeout(ctx, c.config.Timeout)
    defer cancel()

    conn, err := d.DialContext(connCtx, "tcp", c.config.Address)
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
```

```go
// checker/checker_test.go
package checker

import (
    "context"
    "net/http"
    "net/http/httptest"
    "testing"
    "time"

    "github.com/stretchr/testify/assert"

    "sre-monitor/config"
)

func TestChecker_HTTP(t *testing.T) {
    t.Run("健康端点", func(t *testing.T) {
        server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            w.WriteHeader(http.StatusOK)
        }))
        defer server.Close()

        c := New(config.HealthCheckConfig{
            Name:    "test",
            Type:    "http",
            URL:     server.URL,
            Timeout: 5 * time.Second,
        })

        result := c.Check(context.Background())
        assert.Equal(t, 1.0, result.Status)
        assert.Empty(t, result.Error)
        assert.Greater(t, result.Latency, 0.0)
    })

    t.Run("不健康端点", func(t *testing.T) {
        server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            w.WriteHeader(http.StatusInternalServerError)
        }))
        defer server.Close()

        c := New(config.HealthCheckConfig{
            Name:    "test",
            Type:    "http",
            URL:     server.URL,
            Timeout: 5 * time.Second,
        })

        result := c.Check(context.Background())
        assert.Equal(t, 0.0, result.Status)
        assert.Contains(t, result.Error, "500")
    })

    t.Run("连接超时", func(t *testing.T) {
        c := New(config.HealthCheckConfig{
            Name:    "test",
            Type:    "http",
            URL:     "http://192.0.2.1:8080", // 不可达地址
            Timeout: 100 * time.Millisecond,
        })

        result := c.Check(context.Background())
        assert.Equal(t, 0.0, result.Status)
        assert.NotEmpty(t, result.Error)
    })
}

func TestChecker_TCP(t *testing.T) {
    t.Run("端口可达", func(t *testing.T) {
        server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
        defer server.Close()

        c := New(config.HealthCheckConfig{
            Name:    "test",
            Type:    "tcp",
            Address: server.Listener.Addr().String(),
            Timeout: 5 * time.Second,
        })

        result := c.Check(context.Background())
        assert.Equal(t, 1.0, result.Status)
    })

    t.Run("端口不可达", func(t *testing.T) {
        c := New(config.HealthCheckConfig{
            Name:    "test",
            Type:    "tcp",
            Address: "192.0.2.1:1", // 不可达
            Timeout: 100 * time.Millisecond,
        })

        result := c.Check(context.Background())
        assert.Equal(t, 0.0, result.Status)
    })
}
```

```go
// alerter/alerter.go
package alerter

import (
    "context"
    "log"
    "time"

    "sre-monitor/config"
)

// AlertEngine 告警引擎
type AlertEngine struct {
    rules []config.AlertRule
}

func New(cfg config.AlertConfig) *AlertEngine {
    return &AlertEngine{
        rules: cfg.Rules,
    }
}

func (e *AlertEngine) Start(ctx context.Context) {
    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            e.evaluate()
        }
    }
}

func (e *AlertEngine) evaluate() {
    for _, rule := range e.rules {
        // 简化实现：实际应从 Collector 获取指标值
        log.Printf("评估告警规则: %s", rule.Name)
    }
}
```

```go
// exporter/exporter.go
package exporter

import (
    "net/http"

    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

// Exporter Prometheus Exporter
type Exporter struct {
    registry *prometheus.Registry
    handler  http.Handler
}

func New(registry *prometheus.Registry) *Exporter {
    return &Exporter{
        registry: registry,
        handler: promhttp.HandlerFor(registry, promhttp.HandlerOpts{
            EnableOpenMetrics: true,
        }),
    }
}

func (e *Exporter) Handler() http.Handler {
    return e.handler
}
```

```go
// server/middleware.go
package server

import (
    "log"
    "net/http"
    "runtime/debug"
    "time"
)

// WithLogging 日志中间件
func WithLogging(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        wrapper := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

        next.ServeHTTP(wrapper, r)

        log.Printf("%s %s %d %v %s",
            r.Method, r.URL.Path, wrapper.statusCode,
            time.Since(start), r.RemoteAddr)
    })
}

// WithRecovery Panic 恢复中间件
func WithRecovery(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if p := recover(); p != nil {
                log.Printf("PANIC: %v\n%s", p, debug.Stack())
                http.Error(w, "Internal Server Error", http.StatusInternalServerError)
            }
        }()
        next.ServeHTTP(w, r)
    })
}

type responseWriter struct {
    http.ResponseWriter
    statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
    rw.statusCode = code
    rw.ResponseWriter.WriteHeader(code)
}

// HealthHandler 健康检查
func HealthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("OK"))
}

// ReadyHandler 就绪检查
func ReadyHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("READY"))
}
```

#### 1.4 配置文件示例

```yaml
# config.example.yaml
server:
  port: 9100
  tls_port: 0        # 设置 > 0 启用 HTTPS
  tls_cert: ""
  tls_key: ""

health_checks:
  - name: web-api
    type: http
    url: "http://web-api:8080/health"
    timeout: 5s
    interval: 30s

  - name: database
    type: tcp
    address: "db-master:3306"
    timeout: 3s

  - name: redis
    type: tcp
    address: "redis:6379"
    timeout: 2s

  - name: elasticsearch
    type: http
    url: "http://es:9200/_cluster/health"
    timeout: 10s

alerts:
  rules:
    - name: high-cpu
      metric: system_cpu_usage_percent
      threshold: 80
      operator: gt
      duration: 5m
      channel: log

    - name: target-down
      metric: sre_health_target_up
      threshold: 1
      operator: lt
      duration: 1m
      channel: webhook
      webhook: "https://hooks.slack.com/services/xxx"

log:
  level: info
  format: json
```

#### 1.5 构建与运行

```bash
# 构建
go build -o sre-monitor .

# 构建（带版本信息）
go build -ldflags "-X sre-monitor/cmd.Version=1.0.0 \
  -X sre-monitor/cmd.GitCommit=$(git rev-parse --short HEAD) \
  -X sre-monitor/cmd.BuildTime=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -o sre-monitor .

# 运行监控服务
./sre-monitor serve --config config.yaml

# 执行一次性健康检查
./sre-monitor check --config config.yaml

# 查看版本
./sre-monitor version

# 测试指标端点
curl http://localhost:9100/metrics

# 健康检查
curl http://localhost:9100/health
curl http://localhost:9100/ready
```

---

### 2. 代码审查标准

#### 2.1 Go 代码审查清单

```
代码审查清单
============

[ ] 代码风格
    - gofmt 格式化
    - golint / golangci-lint 通过
    - 命名规范（驼峰、缩写大写如 HTTP/URL）
    - 注释完整（导出函数必须有注释）

[ ] 错误处理
    - 所有 error 都被处理（不忽略）
    - 错误信息包含上下文
    - 使用 fmt.Errorf 包装错误
    - 使用 errors.Is/As 判断错误类型

[ ] 并发安全
    - 共享数据使用 mutex 或 atomic
    - Channel 使用正确（方向、关闭）
    - Context 正确传播
    - 没有 goroutine 泄漏

[ ] 资源管理
    - defer 关闭文件、连接、锁
    - HTTP Body 正确关闭
    - Context cancel 正确调用
    - 超时设置合理

[ ] 测试覆盖
    - 核心逻辑有测试
    - 边界条件有测试
    - 错误路径有测试
    - 覆盖率 >= 80%

[ ] 安全性
    - 无硬编码密钥
    - 输入已验证
    - SQL 参数化
    - 错误信息不泄露敏感数据

[ ] 性能
    - 无不必要的内存分配
    - 避免 N+1 查询
    - 使用 buffer 减少系统调用
    - 避免在热路径上加锁
```

#### 2.2 使用 golangci-lint

```yaml
# .golangci.yml
run:
  timeout: 5m

linters:
  enable:
    - errcheck      # 检查未处理的错误
    - gosimple      # 简化代码建议
    - govet         # Go vet 检查
    - ineffassign   # 无效赋值
    - staticcheck   # 静态分析
    - unused        # 未使用代码
    - gocritic      # 代码风格
    - gofmt         # 格式检查
    - goimports     # import 排序
    - misspell      # 拼写检查
    - revive        # 代码风格
    - bodyclose     # HTTP Body 关闭检查
    - nilerr        # nil error 返回检查
    - gocyclo       # 圈复杂度
    - dupl          # 重复代码检测

linters-settings:
  gocyclo:
    min-complexity: 15
  revive:
    rules:
      - name: exported
        severity: warning

issues:
  max-issues-per-linter: 50
  max-same-issues: 3
```

```bash
# 运行 linter
golangci-lint run

# 运行特定 linter
golangci-lint run --enable=bodyclose,nilerr

# 输出格式
golangci-lint run --out-format=colored-line-number
```

---

### 3. 性能优化：pprof

#### 3.1 启用 pprof

```go
package main

import (
    "net/http"
    _ "net/http/pprof" // 注册 pprof handler
)

func main() {
    // 方式 1：独立端口
    go func() {
        http.ListenAndServe("localhost:6060", nil)
    }()

    // 方式 2：在现有 mux 上注册
    mux := http.NewServeMux()
    mux.HandleFunc("/debug/pprof/", pprof.Index)
    mux.HandleFunc("/debug/pprof/cmdline", pprof.Cmdline)
    mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
    mux.HandleFunc("/debug/pprof/symbol", pprof.Symbol)
    mux.HandleFunc("/debug/pprof/trace", pprof.Trace)
}
```

#### 3.2 pprof 分析命令

```bash
# CPU 分析（30 秒采样）
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# 内存分析
go tool pprof http://localhost:6060/debug/pprof/heap

# goroutine 分析
go tool pprof http://localhost:6060/debug/pprof/goroutine

# 阻塞分析
go tool pprof http://localhost:6060/debug/pprof/block

# 互斥锁分析
go tool pprof http://localhost:6060/debug/pprof/mutex

# 分析命令
# top: 显示最耗时的函数
# list: 显示函数源码和耗时
# web: 浏览器打开调用图
# tree: 调用树

# 生成火焰图
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/profile?seconds=30
```

#### 3.3 常见性能问题

```go
// 问题 1：不必要的内存分配
// 差
func bad() string {
    s := ""
    for i := 0; i < 1000; i++ {
        s += "a" // 每次都分配新字符串
    }
    return s
}

// 好
func good() string {
    var b strings.Builder
    b.Grow(1000) // 预分配
    for i := 0; i < 1000; i++ {
        b.WriteString("a")
    }
    return b.String()
}

// 问题 2：不必要的锁
// 差
type BadCache struct {
    mu    sync.Mutex
    data  map[string]string
}

func (c *BadCache) Get(key string) string {
    c.mu.Lock()
    defer c.mu.Unlock() // 读操作也加写锁
    return c.data[key]
}

// 好
type GoodCache struct {
    mu    sync.RWMutex
    data  map[string]string
}

func (c *GoodCache) Get(key string) string {
    c.mu.RLock()
    defer c.mu.RUnlock() // 读操作用读锁
    return c.data[key]
}

// 问题 3：goroutine 泄漏
// 差
func leaky() {
    ch := make(chan int)
    go func() {
        ch <- 1 // 如果没有接收者，goroutine 永远阻塞
    }()
    // 忘记从 ch 读取
}

// 好
func notLeaky() {
    ch := make(chan int, 1) // 带缓冲
    go func() {
        ch <- 1
    }()
    <-ch
}
```

---

### 4. 测试覆盖策略

#### 4.1 测试金字塔

```
         /\
        /  \        E2E 测试（少量）
       /    \       - 关键用户流程
      /------\
     /        \     集成测试（适量）
    /          \    - API 端点
   /            \   - 数据库操作
  /--------------\
 /                \ 单元测试（大量）
/                  \- 函数、工具、组件
/------------------\
```

#### 4.2 测试覆盖率目标

```bash
# 生成覆盖率报告
go test -coverprofile=coverage.out ./...

# 查看各包覆盖率
go tool cover -func=coverage.out

# 生成 HTML 报告
go tool cover -html=coverage.out -o coverage.html

# 在 CI 中检查覆盖率
go test -coverprofile=coverage.out ./...
COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | sed 's/%//')
if (( $(echo "$COVERAGE < 80" | bc -l) )); then
    echo "Coverage $COVERAGE% is below 80%"
    exit 1
fi
```

#### 4.3 测试最佳实践

```go
// 1. 测试命名清晰
func TestUserService_Create_WithValidInput_ReturnsUser(t *testing.T) {}
func TestUserService_Create_WithDuplicateEmail_ReturnsError(t *testing.T) {}

// 2. 使用 t.Cleanup 替代 defer
func TestWithCleanup(t *testing.T) {
    db := setupTestDB(t)
    t.Cleanup(func() { db.Close() })
}

// 3. 使用 t.TempDir 替代手动创建
func TestFileOperations(t *testing.T) {
    dir := t.TempDir()
    path := filepath.Join(dir, "test.txt")
    // ...
}

// 4. 并行测试
func TestParallel(t *testing.T) {
    tests := []struct{ name string }{...}
    for _, tt := range tests {
        tt := tt
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel()
            // ...
        })
    }
}
```

---

## 💻 实战练习

### 练习 1：扩展 sre-monitor 功能

```go
// 任务：为 sre-monitor 添加以下功能：
// 1. 添加 /api/v1/status 端点，返回 JSON 格式的系统状态
// 2. 添加 gRPC 健康检查支持
// 3. 添加指标缓存（避免每次请求都采集）
// 4. 添加配置热重载
// 5. 添加结构化日志（JSON 格式）

// 提示：
// - 使用 sync.RWMutex 保护共享状态
// - 使用 fsnotify 监听配置文件变化
// - 使用 slog 包实现结构化日志
```

### 练习 2：性能基准测试

```go
// 任务：为以下组件编写基准测试并优化
// 1. 配置解析性能
// 2. 健康检查并发性能
// 3. 指标采集性能
// 4. HTTP Handler 响应时间

func BenchmarkConfigLoad(b *testing.B) {
    for i := 0; i < b.N; i++ {
        config.Load("config.yaml")
    }
}

func BenchmarkHealthCheckParallel(b *testing.B) {
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            // ...
        }
    })
}
```

### 练习 3：代码审查实践

```go
// 任务：审查以下代码，找出所有问题并修复

package badcode

import (
    "database/sql"
    "fmt"
    "net/http"
)

var db *sql.DB

func init() {
    var err error
    db, err = sql.Open("mysql", "root:password@tcp(localhost:3306)/mydb")
    if err != nil {
        panic(err)
    }
}

func GetUser(w http.ResponseWriter, r *http.Request) {
    id := r.URL.Query().Get("id")
    rows, _ := db.Query("SELECT * FROM users WHERE id = " + id)
    defer rows.Close()

    var name string
    rows.Scan(&name)

    fmt.Fprintf(w, "User: %s", name)
}

// 问题清单：
// 1. 全局数据库连接
// 2. init() 中 panic
// 3. 忽略错误（db.Query）
// 4. SQL 注入（字符串拼接）
// 5. 没有输入验证
// 6. 错误信息泄露
// 7. 没有超时控制
// 8. rows.Next() 未检查
```

---

## 🎯 面试题精选

### 1. 如何设计一个生产级的 SRE 监控工具？

**参考答案：**
生产级监控工具应包含：
- **指标采集**：系统指标（CPU/内存/磁盘/网络）和应用指标
- **健康检查**：支持 HTTP/TCP/gRPC 多种协议，失败阈值和恢复阈值
- **指标暴露**：兼容 Prometheus 的 /metrics 端点
- **告警**：支持阈值告警、多渠道通知（日志、Webhook、邮件）
- **配置管理**：支持热重载、环境变量覆盖
- **可观测性**：结构化日志、链路追踪
- **高可用**：优雅关闭、资源限制、Panic 恢复
- **安全**：TLS 支持、认证鉴权

### 2. Go 中如何进行性能分析？

**参考答案：**
- 使用 `runtime/pprof` 或 `net/http/pprof` 包
- CPU 分析：`go tool pprof profile`，找到 CPU 热点
- 内存分析：`go tool pprof heap`，找到内存分配热点
- goroutine 分析：检查 goroutine 泄漏
- 阻塞分析：找到锁竞争点
- 使用 `go test -bench` 进行基准测试
- 使用 `go test -benchmem` 查看内存分配

### 3. 如何保证 Go 代码质量？

**参考答案：**
- **代码风格**：gofmt、golangci-lint 自动检查
- **错误处理**：所有 error 必须处理，使用 errors.Is/As
- **测试**：单元测试覆盖率 80%+，表驱动测试
- **代码审查**：使用审查清单，关注并发安全和资源管理
- **CI/CD**：自动化 lint、测试、构建
- **文档**：导出函数必须有注释

### 4. 如何实现优雅关闭？

**参考答案：**
1. 捕获 SIGINT/SIGTERM 信号
2. 停止接受新请求
3. 从注册中心注销服务
4. 等待现有请求完成（设置超时）
5. 关闭数据库连接、文件句柄等资源
6. 关闭 HTTP 服务器
7. 进程退出

关键：使用 `context.WithTimeout` 控制关闭超时，避免无限等待。

### 5. 如何避免 goroutine 泄漏？

**参考答案：**
- 总是通过 Context 传递取消信号
- 使用 `defer cancel()` 确保取消函数被调用
- 带缓冲的 channel 避免发送阻塞
- 使用 `select` 和 `ctx.Done()` 监听取消
- 使用 `errgroup` 管理 goroutine 生命周期
- 测试中使用 `goleak` 检测泄漏
- 监控 `runtime.NumGoroutine()` 发现异常增长

### 6. 如何在 CI/CD 中集成 Go 测试？

**参考答案：**
```yaml
# GitHub Actions 示例
- name: Test
  run: |
    go test -race -coverprofile=coverage.out ./...
    go tool cover -func=coverage.out
    
- name: Lint
  uses: golangci/golangci-lint-action@v3

- name: Benchmark
  run: go test -bench=. -benchmem ./...
```

### 7. 如何处理配置热重载？

**参考答案：**
- 使用 `fsnotify` 监听配置文件变化
- 使用 `sync.RWMutex` 保护配置读写
- 原子替换配置指针（`atomic.Value`）
- 验证新配置有效性后再切换
- 通知依赖配置的组件更新
- 记录配置变更日志

### 8. 什么是火焰图？如何使用？

**参考答案：**
火焰图是一种可视化性能分析数据的图表：
- X 轴：采样数量（宽度表示占比）
- Y 轴：调用栈深度
- 颜色：随机区分不同函数
使用：`go tool pprof -http=:8080 profile` 打开 Web UI，选择 "View > Flame Graph"
分析：找到最宽的"平顶"函数，这些是 CPU 热点

### 9. 如何实现指标缓存？

**参考答案：**
- 使用 `sync.Map` 或带 `RWMutex` 的 map 缓存指标值
- 后台 goroutine 定期采集并更新缓存
- HTTP Handler 从缓存读取，不阻塞采集
- 缓存过期时间与采集间隔对齐
- 使用 `atomic.Value` 原子替换整个指标快照

### 10. 如何设计告警规则引擎？

**参考答案：**
- 支持阈值告警（gt、lt、eq、ne）
- 支持时间窗口（持续 N 分钟）
- 支持告警抑制（避免告警风暴）
- 支持告警分组和路由
- 支持多渠道通知（日志、Webhook、PagerDuty）
- 使用 Prometheus Alertmanager 的设计模式
- 告警状态机：Pending → Firing → Resolved

---

## 📚 深入阅读

- [Go 官方文档：性能分析](https://go.dev/blog/pprof)
- [Go 官方文档：测试](https://go.dev/doc/tutorial/add-a-test)
- [golangci-lint 文档](https://golangci-lint.run/)
- [Prometheus 客户端库](https://pkg.go.dev/github.com/prometheus/client_golang)
- [cobra CLI 框架](https://cobra.dev/)
- [Uber Go 风格指南](https://github.com/uber-go/guide)
- [Effective Go](https://go.dev/doc/effective_go)
- 《Go 语言实战》
- 《Concurrency in Go》

---

## ✅ 自检清单

### 理论检查点
- [ ] 能设计完整的 SRE 监控工具架构
- [ ] 能解释代码审查的关键检查点
- [ ] 能说明 pprof 各种分析类型的用途
- [ ] 能描述测试金字塔和覆盖率策略

### 实操检查点
- [ ] 能独立构建 sre-monitor CLI 工具
- [ ] 能使用 golangci-lint 进行代码审查
- [ ] 能使用 pprof 分析性能问题
- [ ] 能达到 80% 以上测试覆盖率

### 能力验证标准
- [ ] sre-monitor 能编译运行，暴露 /metrics 端点
- [ ] 代码通过 golangci-lint 检查（无 error 级别问题）
- [ ] 所有核心组件有测试覆盖
- [ ] 能回答 SRE Go 综合面试题（8/10 正确率）
