# Day 63: Go 标准库与网络编程

> 📅 日期：2026-05-03
> 📖 学习主题：Go 标准库与网络编程 — net/http, encoding/json, os/exec, log/slog, 中间件模式
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 58 (Go 基础语法), Day 59 (函数与错误处理), Day 60 (数据结构), Day 61 (接口与组合)

---

## 🎯 学习目标

- 掌握 net/http 包构建 HTTP 服务端和客户端
- 熟练使用 encoding/json 处理 JSON 序列化与反序列化
- 掌握 os/exec 包执行外部命令和管道操作
- 理解 log/slog 结构化日志库的使用
- 掌握中间件模式构建可扩展的 HTTP 服务
- 能使用 flag/pflag 包解析命令行参数

---

## 📖 核心知识点

### 1. net/http — HTTP 服务端

#### 1.1 基础 HTTP 服务器

```go
package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "time"
)

type HealthResponse struct {
    Status    string    `json:"status"`
    Timestamp time.Time `json:"timestamp"`
    Uptime    string    `json:"uptime"`
}

var startTime = time.Now()

func healthHandler(w http.ResponseWriter, r *http.Request) {
    resp := HealthResponse{
        Status:    "ok",
        Timestamp: time.Now(),
        Uptime:    time.Since(startTime).String(),
    }

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(resp)
}

func main() {
    mux := http.NewServeMux()

    // 注册路由
    mux.HandleFunc("/healthz", healthHandler)
    mux.HandleFunc("/readyz", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        fmt.Fprintln(w, "ready")
    })

    // 创建服务器（带超时配置）
    server := &http.Server{
        Addr:         ":8080",
        Handler:      mux,
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 30 * time.Second,
        IdleTimeout:  120 * time.Second,
    }

    log.Printf("Server starting on %s", server.Addr)
    if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
        log.Fatalf("Server failed: %v", err)
    }
}
```

#### 1.2 路由与请求处理

```go
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
    "strings"
)

type Server struct {
    ID       string   `json:"id"`
    Name     string   `json:"name"`
    Status   string   `json:"status"`
    Tags     []string `json:"tags,omitempty"`
}

// 模拟数据库
var servers = map[string]Server{
    "web-01": {ID: "web-01", Name: "Web Server 1", Status: "running", Tags: []string{"web", "prod"}},
    "db-01":  {ID: "db-01", Name: "Database 1", Status: "running", Tags: []string{"db", "prod"}},
}

// GET /api/servers — 列出所有服务器
func listServersHandler(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }

    // 查询参数过滤
    statusFilter := r.URL.Query().Get("status")
    tagFilter := r.URL.Query().Get("tag")

    var result []Server
    for _, s := range servers {
        if statusFilter != "" && s.Status != statusFilter {
            continue
        }
        if tagFilter != "" {
            found := false
            for _, t := range s.Tags {
                if t == tagFilter {
                    found = true
                    break
                }
            }
            if !found {
                continue
            }
        }
        result = append(result, s)
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(result)
}

// GET /api/servers/{id} — 获取单个服务器
func getServerHandler(w http.ResponseWriter, r *http.Request) {
    // 手动解析路径参数
    parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/servers/"), "/")
    if len(parts) == 0 || parts[0] == "" {
        http.Error(w, "Missing server ID", http.StatusBadRequest)
        return
    }
    id := parts[0]

    server, ok := servers[id]
    if !ok {
        http.Error(w, fmt.Sprintf("Server %q not found", id), http.StatusNotFound)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(server)
}

// POST /api/servers — 创建服务器
func createServerHandler(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }

    var server Server
    if err := json.NewDecoder(r.Body).Decode(&server); err != nil {
        http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
        return
    }

    if server.ID == "" {
        http.Error(w, "Server ID is required", http.StatusBadRequest)
        return
    }

    servers[server.ID] = server

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(server)
}

func main() {
    mux := http.NewServeMux()

    mux.HandleFunc("/api/servers", func(w http.ResponseWriter, r *http.Request) {
        switch r.Method {
        case http.MethodGet:
            listServersHandler(w, r)
        case http.MethodPost:
            createServerHandler(w, r)
        default:
            http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        }
    })

    mux.HandleFunc("/api/servers/", getServerHandler)

    log.Printf("Server starting on :8080")
    http.ListenAndServe(":8080", mux)
}
```

#### 1.3 Go 1.22+ 增强路由

```go
package main

import (
    "encoding/json"
    "fmt"
    "net/http"
)

func main() {
    mux := http.NewServeMux()

    // Go 1.22+ 支持方法和路径参数
    mux.HandleFunc("GET /api/servers", func(w http.ResponseWriter, r *http.Request) {
        json.NewEncoder(w).Encode([]string{"web-01", "db-01"})
    })

    mux.HandleFunc("GET /api/servers/{id}", func(w http.ResponseWriter, r *http.Request) {
        id := r.PathValue("id") // Go 1.22+ 获取路径参数
        json.NewEncoder(w).Encode(map[string]string{"id": id, "status": "running"})
    })

    mux.HandleFunc("POST /api/servers", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusCreated)
        fmt.Fprintln(w, `{"created": true}`)
    })

    mux.HandleFunc("DELETE /api/servers/{id}", func(w http.ResponseWriter, r *http.Request) {
        id := r.PathValue("id")
        fmt.Fprintf(w, `{"deleted": "%s"}`, id)
    })

    http.ListenAndServe(":8080", mux)
}
```

---

### 2. net/http — HTTP 客户端

#### 2.1 基础 HTTP 客户端

```go
package main

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"
)

// SRE 场景：调用内部 API
type APIResponse struct {
    Status  string      `json:"status"`
    Data    interface{} `json:"data,omitempty"`
    Error   string      `json:"error,omitempty"`
}

// 创建带超时的客户端
func newHTTPClient() *http.Client {
    return &http.Client{
        Timeout: 30 * time.Second,
        Transport: &http.Transport{
            MaxIdleConns:        100,
            MaxIdleConnsPerHost: 10,
            IdleConnTimeout:     90 * time.Second,
        },
    }
}

// GET 请求示例
func getServers(ctx context.Context, client *http.Client, baseURL string) ([]Server, error) {
    req, err := http.NewRequestWithContext(ctx, "GET", baseURL+"/api/servers", nil)
    if err != nil {
        return nil, fmt.Errorf("creating request: %w", err)
    }

    req.Header.Set("Accept", "application/json")
    req.Header.Set("X-Request-ID", "req-12345")

    resp, err := client.Do(req)
    if err != nil {
        return nil, fmt.Errorf("executing request: %w", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("API error (%d): %s", resp.StatusCode, string(body))
    }

    var servers []Server
    if err := json.NewDecoder(resp.Body).Decode(&servers); err != nil {
        return nil, fmt.Errorf("decoding response: %w", err)
    }
    return servers, nil
}

// POST 请求示例
func createServer(ctx context.Context, client *http.Client, baseURL string, server Server) error {
    data, err := json.Marshal(server)
    if err != nil {
        return fmt.Errorf("marshaling server: %w", err)
    }

    req, err := http.NewRequestWithContext(ctx, "POST", baseURL+"/api/servers", bytes.NewReader(data))
    if err != nil {
        return fmt.Errorf("creating request: %w", err)
    }

    req.Header.Set("Content-Type", "application/json")

    resp, err := client.Do(req)
    if err != nil {
        return fmt.Errorf("executing request: %w", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusCreated {
        body, _ := io.ReadAll(resp.Body)
        return fmt.Errorf("API error (%d): %s", resp.StatusCode, string(body))
    }
    return nil
}

func main() {
    client := newHTTPClient()
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    servers, err := getServers(ctx, client, "http://localhost:8080")
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    fmt.Printf("Servers: %+v\n", servers)
}
```

#### 2.2 HTTP 客户端最佳实践

```go
package main

import (
    "context"
    "fmt"
    "math"
    "net"
    "net/http"
    "time"
)

// 生产级 HTTP 客户端配置
func ProductionHTTPClient() *http.Client {
    transport := &http.Transport{
        // 连接池配置
        MaxIdleConns:        200,
        MaxIdleConnsPerHost: 20,
        MaxConnsPerHost:     100,
        IdleConnTimeout:     90 * time.Second,

        // TCP 配置
        DialContext: (&net.Dialer{
            Timeout:   5 * time.Second,
            KeepAlive: 30 * time.Second,
        }).DialContext,

        // TLS 配置
        TLSHandshakeTimeout: 5 * time.Second,

        // 响应头超时
        ResponseHeaderTimeout: 10 * time.Second,
    }

    return &http.Client{
        Transport: transport,
        Timeout:   30 * time.Second, // 整体超时（包括重定向）
        // 不跟随重定向
        // CheckRedirect: func(req *http.Request, via []*http.Request) error {
        //     return http.ErrUseLastResponse
        // },
    }
}

// 带重试的请求
func DoWithRetry(ctx context.Context, client *http.Client, req *http.Request, maxRetries int) (*http.Response, error) {
    var lastErr error

    for attempt := 0; attempt <= maxRetries; attempt++ {
        if attempt > 0 {
            // 指数退避
            delay := time.Duration(math.Pow(2, float64(attempt-1))) * 100 * time.Millisecond
            select {
            case <-time.After(delay):
            case <-ctx.Done():
                return nil, ctx.Err()
            }
        }

        // 每次重试需要新的 Body reader
        resp, err := client.Do(req)
        if err != nil {
            lastErr = err
            continue
        }

        // 只对 5xx 错误重试
        if resp.StatusCode >= 500 {
            resp.Body.Close()
            lastErr = fmt.Errorf("server error: %d", resp.StatusCode)
            continue
        }

        return resp, nil
    }

    return nil, fmt.Errorf("max retries exceeded: %w", lastErr)
}

func main() {
    client := ProductionHTTPClient()

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    req, _ := http.NewRequestWithContext(ctx, "GET", "http://httpbin.org/get", nil)
    resp, err := DoWithRetry(ctx, client, req, 3)
    if err != nil {
        fmt.Printf("Failed: %v\n", err)
        return
    }
    defer resp.Body.Close()
    fmt.Printf("Status: %d\n", resp.StatusCode)
}
```

---

### 3. encoding/json

#### 3.1 JSON 序列化与反序列化

```go
package main

import (
    "encoding/json"
    "fmt"
    "time"
)

type MetricReport struct {
    Host      string            `json:"host"`
    Timestamp time.Time         `json:"timestamp"`
    Metrics   map[string]Metric `json:"metrics"`
    Tags      []string          `json:"tags,omitempty"`
    Internal  bool              `json:"-"` // 完全忽略
}

type Metric struct {
    Value float64 `json:"value"`
    Unit  string  `json:"unit"`
}

func main() {
    // 结构体 → JSON
    report := MetricReport{
        Host:      "web-01",
        Timestamp: time.Now(),
        Metrics: map[string]Metric{
            "cpu":    {Value: 85.5, Unit: "percent"},
            "memory": {Value: 72.3, Unit: "percent"},
            "disk":   {Value: 45.0, Unit: "percent"},
        },
        Tags:     []string{"production", "web"},
        Internal: true, // 不会被序列化
    }

    // Marshal: 紧凑 JSON
    data, err := json.Marshal(report)
    if err != nil {
        fmt.Printf("Marshal error: %v\n", err)
        return
    }
    fmt.Println("Compact:", string(data))

    // MarshalIndent: 格式化 JSON
    pretty, err := json.MarshalIndent(report, "", "  ")
    if err != nil {
        fmt.Printf("MarshalIndent error: %v\n", err)
        return
    }
    fmt.Println("Pretty:\n" + string(pretty))

    // JSON → 结构体
    var parsed MetricReport
    if err := json.Unmarshal(data, &parsed); err != nil {
        fmt.Printf("Unmarshal error: %v\n", err)
        return
    }
    fmt.Printf("Parsed: %+v\n", parsed)
}
```

#### 3.2 处理动态 JSON

```go
package main

import (
    "encoding/json"
    "fmt"
)

// 处理结构未知的 JSON
func parseDynamicJSON(data []byte) {
    // 使用 map[string]interface{}
    var result map[string]interface{}
    if err := json.Unmarshal(data, &result); err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    // 安全访问嵌套值
    if metrics, ok := result["metrics"].(map[string]interface{}); ok {
        for name, val := range metrics {
            if m, ok := val.(map[string]interface{}); ok {
                fmt.Printf("  %s: %.2f %s\n", name, m["value"].(float64), m["unit"].(string))
            }
        }
    }
}

// 使用 json.RawMessage 延迟解析
type Event struct {
    Type      string          `json:"type"`
    Timestamp int64           `json:"timestamp"`
    Payload   json.RawMessage `json:"payload"` // 延迟解析
}

type AlertPayload struct {
    Severity string `json:"severity"`
    Message  string `json:"message"`
}

type MetricPayload struct {
    Name  string  `json:"name"`
    Value float64 `json:"value"`
}

func processEvent(data []byte) {
    var event Event
    if err := json.Unmarshal(data, &event); err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    switch event.Type {
    case "alert":
        var payload AlertPayload
        json.Unmarshal(event.Payload, &payload)
        fmt.Printf("Alert [%s]: %s\n", payload.Severity, payload.Message)
    case "metric":
        var payload MetricPayload
        json.Unmarshal(event.Payload, &payload)
        fmt.Printf("Metric %s = %.2f\n", payload.Name, payload.Value)
    }
}

func main() {
    // 动态 JSON
    parseDynamicJSON([]byte(`{
        "host": "web-01",
        "metrics": {
            "cpu": {"value": 85.5, "unit": "percent"},
            "memory": {"value": 72.3, "unit": "percent"}
        }
    }`))

    // 延迟解析
    processEvent([]byte(`{"type":"alert","timestamp":1234567890,"payload":{"severity":"critical","message":"DB down"}}`))
    processEvent([]byte(`{"type":"metric","timestamp":1234567890,"payload":{"name":"cpu","value":85.5}}`))
}
```

#### 3.3 自定义 JSON 序列化

```go
package main

import (
    "encoding/json"
    "fmt"
    "strconv"
    "time"
)

// 自定义 Duration 的 JSON 序列化
type Duration struct {
    time.Duration
}

func (d Duration) MarshalJSON() ([]byte, error) {
    return json.Marshal(d.Duration.String())
}

func (d *Duration) UnmarshalJSON(b []byte) error {
    var v interface{}
    if err := json.Unmarshal(b, &v); err != nil {
        return err
    }
    switch value := v.(type) {
    case float64:
        d.Duration = time.Duration(value)
        return nil
    case string:
        var err error
        d.Duration, err = time.ParseDuration(value)
        return err
    default:
        return fmt.Errorf("invalid duration: %v", v)
    }
}

// 自定义时间格式
type CustomTime struct {
    time.Time
}

const timeFormat = "2006-01-02 15:04:05"

func (ct CustomTime) MarshalJSON() ([]byte, error) {
    return json.Marshal(ct.Format(timeFormat))
}

func (ct *CustomTime) UnmarshalJSON(b []byte) error {
    s, err := strconv.Unquote(string(b))
    if err != nil {
        return err
    }
    t, err := time.Parse(timeFormat, s)
    if err != nil {
        return err
    }
    ct.Time = t
    return nil
}

type ServerConfig struct {
    Name     string   `json:"name"`
    Timeout  Duration `json:"timeout"`
    Started  CustomTime `json:"started"`
}

func main() {
    cfg := ServerConfig{
        Name:    "web-01",
        Timeout: Duration{30 * time.Second},
        Started: CustomTime{time.Date(2026, 5, 3, 10, 30, 0, 0, time.UTC)},
    }

    data, _ := json.MarshalIndent(cfg, "", "  ")
    fmt.Println(string(data))
    // {
    //   "name": "web-01",
    //   "timeout": "30s",
    //   "started": "2026-05-03 10:30:00"
    // }

    // 反序列化
    var parsed ServerConfig
    json.Unmarshal(data, &parsed)
    fmt.Printf("Timeout: %v\n", parsed.Timeout.Duration)
}
```

---

### 4. os/exec — 执行外部命令

#### 4.1 基础命令执行

```go
package main

import (
    "bytes"
    "fmt"
    "os/exec"
)

func main() {
    // 简单命令执行
    out, err := exec.Command("hostname").Output()
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    fmt.Printf("Hostname: %s", out)

    // 带参数的命令
    out, err = exec.Command("uname", "-a").Output()
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    fmt.Printf("System: %s", out)

    // 分别捕获 stdout 和 stderr
    cmd := exec.Command("ls", "-la", "/nonexistent")
    var stdout, stderr bytes.Buffer
    cmd.Stdout = &stdout
    cmd.Stderr = &stderr

    err = cmd.Run()
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        fmt.Printf("Stderr: %s", stderr.String())
    }
}
```

#### 4.2 命令管道与超时

```go
package main

import (
    "bytes"
    "context"
    "fmt"
    "os/exec"
    "strings"
    "time"
)

// 带超时执行命令
func executeWithTimeout(ctx context.Context, name string, args ...string) (string, error) {
    ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
    defer cancel()

    cmd := exec.CommandContext(ctx, name, args...)
    out, err := cmd.CombinedOutput()
    if err != nil {
        return "", fmt.Errorf("command %q failed: %w\nOutput: %s", name, err, string(out))
    }
    return string(out), nil
}

// 管道命令：cmd1 | cmd2
func pipeCommands(cmd1 *exec.Cmd, cmd2 *exec.Cmd) (string, error) {
    // cmd1 的 stdout 连接到 cmd2 的 stdin
    pipe, err := cmd1.StdoutPipe()
    if err != nil {
        return "", err
    }
    cmd2.Stdin = pipe

    var output bytes.Buffer
    cmd2.Stdout = &output

    if err := cmd2.Start(); err != nil {
        return "", err
    }
    if err := cmd1.Run(); err != nil {
        return "", err
    }
    if err := cmd2.Wait(); err != nil {
        return "", err
    }

    return output.String(), nil
}

func main() {
    ctx := context.Background()

    // 获取磁盘使用率
    out, err := executeWithTimeout(ctx, "df", "-h")
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    fmt.Println("Disk usage:")
    fmt.Println(out)

    // 管道：ps aux | grep go | wc -l
    cmd1 := exec.Command("ps", "aux")
    cmd2 := exec.Command("grep", "go")
    cmd3 := exec.Command("wc", "-l")

    pipe1, _ := cmd1.StdoutPipe()
    cmd2.Stdin = pipe1
    pipe2, _ := cmd2.StdoutPipe()
    cmd3.Stdin = pipe2

    var result bytes.Buffer
    cmd3.Stdout = &result

    cmd3.Start()
    cmd2.Start()
    cmd1.Run()
    cmd2.Wait()
    cmd3.Wait()

    fmt.Printf("Go processes: %s", strings.TrimSpace(result.String()))
}
```

#### 4.3 SRE 实战：系统巡检工具

```go
package main

import (
    "context"
    "fmt"
    "os/exec"
    "strings"
    "time"
)

type CheckResult struct {
    Name    string
    Status  string
    Details string
    Error   error
}

func runCheck(ctx context.Context, name string, cmdName string, args ...string) CheckResult {
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    cmd := exec.CommandContext(ctx, cmdName, args...)
    out, err := cmd.CombinedOutput()
    output := strings.TrimSpace(string(out))

    if err != nil {
        return CheckResult{
            Name:    name,
            Status:  "FAIL",
            Details: output,
            Error:   err,
        }
    }
    return CheckResult{
        Name:    name,
        Status:  "OK",
        Details: output,
    }
}

func systemCheck(ctx context.Context) []CheckResult {
    checks := []struct {
        name string
        cmd  string
        args []string
    }{
        {"Disk Usage", "df", []string{"-h", "/"}},
        {"Memory", "free", []string{"-h"}},
        {"Load Average", "cat", []string{"/proc/loadavg"}},
        {"Uptime", "uptime", []string{"-p"}},
        {"Docker Containers", "docker", []string{"ps", "--format", "{{.Names}}: {{.Status}}"}},
    }

    results := make([]CheckResult, len(checks))
    for i, check := range checks {
        results[i] = runCheck(ctx, check.name, check.cmd, check.args...)
    }
    return results
}

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    fmt.Println("=== System Health Check ===")
    fmt.Printf("Time: %s\n\n", time.Now().Format("2006-01-02 15:04:05"))

    results := systemCheck(ctx)
    for _, r := range results {
        status := "[OK]  "
        if r.Status == "FAIL" {
            status = "[FAIL]"
        }
        fmt.Printf("%s %s\n", status, r.Name)
        if r.Details != "" {
            // 缩进输出详情
            for _, line := range strings.Split(r.Details, "\n") {
                if line != "" {
                    fmt.Printf("       %s\n", line)
                }
            }
        }
        if r.Error != nil {
            fmt.Printf("       Error: %v\n", r.Error)
        }
        fmt.Println()
    }
}
```

---

### 5. flag/pflag — 命令行参数

#### 5.1 标准库 flag

```go
package main

import (
    "flag"
    "fmt"
    "os"
)

func main() {
    // 定义命令行参数
    host := flag.String("host", "0.0.0.0", "Server host address")
    port := flag.Int("port", 8080, "Server port")
    debug := flag.Bool("debug", false, "Enable debug mode")
    var tags []string
    flag.Func("tag", "Add a tag (can be repeated)", func(s string) error {
        tags = append(tags, s)
        return nil
    })

    // 自定义 usage
    flag.Usage = func() {
        fmt.Fprintf(os.Stderr, "Usage: %s [options]\n\n", os.Args[0])
        fmt.Fprintf(os.Stderr, "SRE Health Check Tool\n\n")
        fmt.Fprintf(os.Stderr, "Options:\n")
        flag.PrintDefaults()
    }

    flag.Parse()

    // 使用参数
    fmt.Printf("Host: %s\n", *host)
    fmt.Printf("Port: %d\n", *port)
    fmt.Printf("Debug: %v\n", *debug)
    fmt.Printf("Tags: %v\n", tags)
    fmt.Printf("Args: %v\n", flag.Args())
}
```

```bash
# 使用方式
./app -host 127.0.0.1 -port 9090 -debug -tag web -tag prod
./app --help
```

#### 5.2 pflag（POSIX 风格）

```go
package main

import (
    "fmt"
    "os"

    flag "github.com/spf13/pflag"
)

func main() {
    // pflag 支持 -- 长选项和 - 短选项
    host := flag.StringP("host", "H", "0.0.0.0", "Server host address")
    port := flag.IntP("port", "p", 8080, "Server port")
    debug := flag.BoolP("debug", "d", false, "Enable debug mode")
    config := flag.StringP("config", "c", "/etc/app/config.yaml", "Config file path")

    // 绑定到已有变量
    var verbose int
    flag.CountP(&verbose, "verbose", "v", "Verbosity level")

    flag.Parse()

    fmt.Printf("Host: %s\n", *host)
    fmt.Printf("Port: %d\n", *port)
    fmt.Printf("Debug: %v\n", *debug)
    fmt.Printf("Config: %s\n", *config)
    fmt.Printf("Verbose: %d\n", verbose)
    fmt.Printf("Args: %v\n", flag.Args())
}
```

```bash
# pflag 使用方式
./app --host 127.0.0.1 -p 9090 -d -c /tmp/config.yaml -vvv
./app -H 127.0.0.1 -p 9090 --debug
```

---

### 6. log/slog — 结构化日志

#### 6.1 slog 基础

```go
package main

import (
    "log/slog"
    "os"
    "time"
)

func main() {
    // 默认 logger（文本格式）
    slog.Info("server started",
        "host", "0.0.0.0",
        "port", 8080,
    )

    // JSON 格式
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))

    logger.Info("server started",
        "host", "0.0.0.0",
        "port", 8080,
        "timestamp", time.Now(),
    )

    // 带上下文的 logger
    requestLogger := logger.With(
        "request_id", "req-12345",
        "user_id", 42,
    )

    requestLogger.Info("processing request",
        "method", "GET",
        "path", "/api/servers",
    )

    requestLogger.Warn("slow query detected",
        "duration_ms", 1500,
        "query", "SELECT * FROM servers",
    )

    requestLogger.Error("database connection failed",
        "error", "connection refused",
        "retry_count", 3,
    )
}
```

#### 6.2 自定义 Handler

```go
package main

import (
    "context"
    "fmt"
    "log/slog"
    "os"
    "strings"
    "time"
)

// 自定义彩色文本 Handler
type ColorHandler struct {
    opts slog.HandlerOptions
}

func NewColorHandler(opts slog.HandlerOptions) *ColorHandler {
    return &ColorHandler{opts: opts}
}

func (h *ColorHandler) Enabled(_ context.Context, level slog.Level) bool {
    return level >= h.opts.Level.Level()
}

func (h *ColorHandler) Handle(_ context.Context, r slog.Record) error {
    var color string
    switch r.Level {
    case slog.LevelDebug:
        color = "\033[36m" // 青色
    case slog.LevelInfo:
        color = "\033[32m" // 绿色
    case slog.LevelWarn:
        color = "\033[33m" // 黄色
    case slog.LevelError:
        color = "\033[31m" // 红色
    }

    reset := "\033[0m"
    timeStr := r.Time.Format("15:04:05")

    var attrs []string
    r.Attrs(func(a slog.Attr) bool {
        attrs = append(attrs, fmt.Sprintf("%s=%v", a.Key, a.Value))
        return true
    })

    line := fmt.Sprintf("%s%s [%s]%s %s",
        color, timeStr, r.Level, reset, r.Message)
    if len(attrs) > 0 {
        line += " " + strings.Join(attrs, " ")
    }

    fmt.Fprintln(os.Stdout, line)
    return nil
}

func (h *ColorHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
    return h // 简化实现
}

func (h *ColorHandler) WithGroup(name string) slog.Handler {
    return h // 简化实现
}

func main() {
    handler := NewColorHandler(slog.HandlerOptions{Level: slog.LevelDebug})
    logger := slog.New(handler)

    logger.Debug("debug message", "key", "value")
    logger.Info("server started", "port", 8080)
    logger.Warn("high memory", "usage", "85%")
    logger.Error("connection failed", "host", "db-01")
}
```

#### 6.3 SRE 实战：请求日志中间件

```go
package main

import (
    "log/slog"
    "net/http"
    "os"
    "time"
)

type responseWriter struct {
    http.ResponseWriter
    statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
    rw.statusCode = code
    rw.ResponseWriter.WriteHeader(code)
}

func LoggingMiddleware(logger *slog.Logger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()

            // 包装 ResponseWriter 以捕获状态码
            rw := &responseWriter{
                ResponseWriter: w,
                statusCode:     http.StatusOK,
            }

            // 提取请求 ID
            requestID := r.Header.Get("X-Request-ID")
            if requestID == "" {
                requestID = "unknown"
            }

            // 创建请求级 logger
            reqLogger := logger.With(
                "request_id", requestID,
                "method", r.Method,
                "path", r.URL.Path,
                "remote_addr", r.RemoteAddr,
            )

            // 将 logger 存入 context
            ctx := r.Context()
            r = r.WithContext(ctx)

            next.ServeHTTP(rw, r)

            duration := time.Since(start)

            reqLogger.Info("request completed",
                "status", rw.statusCode,
                "duration_ms", duration.Milliseconds(),
                "duration", duration.String(),
            )

            // 慢请求告警
            if duration > 1*time.Second {
                reqLogger.Warn("slow request detected",
                    "duration_ms", duration.Milliseconds(),
                )
            }
        })
    }
}

func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))

    mux := http.NewServeMux()

    mux.HandleFunc("/api/servers", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte(`[{"id":"web-01"}]`))
    })

    mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("ok"))
    })

    handler := LoggingMiddleware(logger)(mux)

    logger.Info("starting server", "addr", ":8080")
    http.ListenAndServe(":8080", handler)
}
```

---

### 7. 中间件模式

#### 7.1 中间件链

```go
package main

import (
    "fmt"
    "net/http"
    "time"
)

// 中间件类型
type Middleware func(http.Handler) http.Handler

// 构建中间件链
func Chain(middlewares ...Middleware) Middleware {
    return func(next http.Handler) http.Handler {
        for i := len(middlewares) - 1; i >= 0; i-- {
            next = middlewares[i](next)
        }
        return next
    }
}

// Recovery 中间件（panic 恢复）
func Recovery() Middleware {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            defer func() {
                if err := recover(); err != nil {
                    w.WriteHeader(http.StatusInternalServerError)
                    fmt.Fprintf(w, `{"error":"internal server error"}`)
                    fmt.Printf("PANIC: %v\n", err)
                }
            }()
            next.ServeHTTP(w, r)
        })
    }
}

// CORS 中间件
func CORS(allowedOrigins []string) Middleware {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            origin := r.Header.Get("Origin")
            for _, allowed := range allowedOrigins {
                if origin == allowed {
                    w.Header().Set("Access-Control-Allow-Origin", origin)
                    w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                    w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
                    break
                }
            }

            if r.Method == "OPTIONS" {
                w.WriteHeader(http.StatusOK)
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}

// Rate Limit 中间件
func RateLimit(requestsPerSecond int) Middleware {
    // 简单的令牌桶实现
    type limiter struct {
        tokens chan struct{}
    }

    l := &limiter{
        tokens: make(chan struct{}, requestsPerSecond),
    }

    // 填充令牌
    for i := 0; i < requestsPerSecond; i++ {
        l.tokens <- struct{}{}
    }

    go func() {
        ticker := time.NewTicker(time.Second / time.Duration(requestsPerSecond))
        for range ticker.C {
            select {
            case l.tokens <- struct{}{}:
            default:
            }
        }
    }()

    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            select {
            case <-l.tokens:
                next.ServeHTTP(w, r)
            default:
                w.WriteHeader(http.StatusTooManyRequests)
                fmt.Fprintln(w, `{"error":"rate limit exceeded"}`)
            }
        })
    }
}

// 认证中间件
func Auth(tokenHeader string, validTokens map[string]bool) Middleware {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            // 健康检查端点跳过认证
            if r.URL.Path == "/healthz" || r.URL.Path == "/readyz" {
                next.ServeHTTP(w, r)
                return
            }

            token := r.Header.Get(tokenHeader)
            if token == "" || !validTokens[token] {
                w.WriteHeader(http.StatusUnauthorized)
                fmt.Fprintln(w, `{"error":"unauthorized"}`)
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}

func main() {
    mux := http.NewServeMux()

    mux.HandleFunc("/api/data", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintln(w, `{"data": "sensitive data"}`)
    })

    mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintln(w, "ok")
    })

    // 组合中间件
    chain := Chain(
        Recovery(),
        CORS([]string{"http://localhost:3000", "https://dashboard.example.com"}),
        RateLimit(100),
        Auth("Authorization", map[string]bool{
            "Bearer token123": true,
            "Bearer token456": true,
        }),
    )

    handler := chain(mux)

    fmt.Println("Server starting on :8080")
    http.ListenAndServe(":8080", handler)
}
```

---

### 8. net/rpc — RPC 服务

```go
package main

import (
    "errors"
    "log"
    "net"
    "net/rpc"
    "time"
)

// 服务定义
type ServerService struct {
    servers map[string]*ServerInfo
}

type ServerInfo struct {
    ID       string
    Name     string
    Status   string
    LastSeen time.Time
}

type GetServerArgs struct {
    ID string
}

type GetServerReply struct {
    Server *ServerInfo
}

type ListServersArgs struct {
    Status string // 过滤条件
}

type ListServersReply struct {
    Servers []*ServerInfo
}

func (s *ServerService) GetServer(args *GetServerArgs, reply *GetServerReply) error {
    server, ok := s.servers[args.ID]
    if !ok {
        return errors.New("server not found: " + args.ID)
    }
    reply.Server = server
    return nil
}

func (s *ServerService) ListServers(args *ListServersArgs, reply *ListServersReply) error {
    for _, server := range s.servers {
        if args.Status != "" && server.Status != args.Status {
            continue
        }
        reply.Servers = append(reply.Servers, server)
    }
    return nil
}

func main() {
    service := &ServerService{
        servers: map[string]*ServerInfo{
            "web-01": {ID: "web-01", Name: "Web Server 1", Status: "running", LastSeen: time.Now()},
            "db-01":  {ID: "db-01", Name: "Database 1", Status: "running", LastSeen: time.Now()},
        },
    }

    rpc.Register(service)
    rpc.HandleHTTP()

    listener, err := net.Listen("tcp", ":9090")
    if err != nil {
        log.Fatalf("Listen error: %v", err)
    }

    log.Println("RPC server starting on :9090")
    rpc.Accept(listener)
}
```

```go
// RPC 客户端
package main

import (
    "fmt"
    "log"
    "net/rpc"
)

func main() {
    client, err := rpc.DialHTTP("tcp", "localhost:9090")
    if err != nil {
        log.Fatalf("Dial error: %v", err)
    }

    // 调用 GetServer
    var reply struct{ Server *struct{ ID, Name, Status string } }
    err = client.Call("ServerService.GetServer", map[string]string{"ID": "web-01"}, &reply)
    if err != nil {
        log.Fatalf("RPC error: %v", err)
    }
    fmt.Printf("Server: %+v\n", reply.Server)

    // 异步调用
    var listReply struct{ Servers []*struct{ ID, Name, Status string } }
    call := client.Go("ServerService.ListServers", map[string]string{}, &listReply, nil)
    <-call.Done
    if call.Error != nil {
        log.Fatalf("RPC error: %v", call.Error)
    }
    fmt.Printf("Servers: %d found\n", len(listReply.Servers))
}
```

---

### 9. SRE 实战案例

#### 9.1 完整的健康检查 HTTP 服务

```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "log/slog"
    "net/http"
    "os"
    "sync"
    "time"
)

type HealthStatus struct {
    Status    string            `json:"status"`
    Timestamp time.Time         `json:"timestamp"`
    Checks    map[string]Check  `json:"checks"`
    Uptime    string            `json:"uptime"`
}

type Check struct {
    Status  string `json:"status"`
    Message string `json:"message,omitempty"`
    Latency int64  `json:"latency_ms"`
}

type HealthChecker struct {
    logger    *slog.Logger
    checks    map[string]func(ctx context.Context) Check
    mu        sync.RWMutex
    startTime time.Time
}

func NewHealthChecker(logger *slog.Logger) *HealthChecker {
    return &HealthChecker{
        logger:    logger,
        checks:    make(map[string]func(ctx context.Context) Check),
        startTime: time.Now(),
    }
}

func (hc *HealthChecker) Register(name string, check func(ctx context.Context) Check) {
    hc.mu.Lock()
    defer hc.mu.Unlock()
    hc.checks[name] = check
}

func (hc *HealthChecker) Handler() http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
        defer cancel()

        hc.mu.RLock()
        checks := make(map[string]func(ctx context.Context) Check, len(hc.checks))
        for k, v := range hc.checks {
            checks[k] = v
        }
        hc.mu.RUnlock()

        results := make(map[string]Check, len(checks))
        var wg sync.WaitGroup
        var mu sync.Mutex

        for name, checkFn := range checks {
            wg.Add(1)
            go func(name string, fn func(ctx context.Context) Check) {
                defer wg.Done()
                result := fn(ctx)
                mu.Lock()
                results[name] = result
                mu.Unlock()
            }(name, checkFn)
        }

        wg.Wait()

        // 计算整体状态
        overallStatus := "ok"
        for _, check := range results {
            if check.Status != "ok" {
                overallStatus = "degraded"
                break
            }
        }

        status := HealthStatus{
            Status:    overallStatus,
            Timestamp: time.Now(),
            Checks:    results,
            Uptime:    time.Since(hc.startTime).String(),
        }

        w.Header().Set("Content-Type", "application/json")
        if overallStatus != "ok" {
            w.WriteHeader(http.StatusServiceUnavailable)
        }
        json.NewEncoder(w).Encode(status)
    }
}

func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))

    hc := NewHealthChecker(logger)

    // 注册健康检查
    hc.Register("database", func(ctx context.Context) Check {
        start := time.Now()
        // 模拟数据库检查
        time.Sleep(10 * time.Millisecond)
        return Check{Status: "ok", Message: "connected", Latency: time.Since(start).Milliseconds()}
    })

    hc.Register("cache", func(ctx context.Context) Check {
        start := time.Now()
        time.Sleep(5 * time.Millisecond)
        return Check{Status: "ok", Message: "connected", Latency: time.Since(start).Milliseconds()}
    })

    hc.Register("disk", func(ctx context.Context) Check {
        start := time.Now()
        return Check{Status: "ok", Message: "/ 45% used", Latency: time.Since(start).Milliseconds()}
    })

    mux := http.NewServeMux()
    mux.HandleFunc("/healthz", hc.Handler())
    mux.HandleFunc("/readyz", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        fmt.Fprintln(w, "ready")
    })

    logger.Info("health check server starting", "addr", ":8080")
    if err := http.ListenAndServe(":8080", mux); err != nil {
        logger.Error("server failed", "error", err)
        os.Exit(1)
    }
}
```

---

## 💻 实战练习

### 练习 1：构建一个简易 HTTP 代理

编写一个 HTTP 代理服务，转发请求到后端服务器并记录日志。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "log"
    "net/http"
    "net/http/httputil"
    "net/url"
    "time"
)

func loggingProxy(target *url.URL) http.Handler {
    proxy := httputil.NewSingleHostReverseProxy(target)

    // 自定义 Transport 添加日志
    originalTransport := http.DefaultTransport.(*http.Transport).Clone()
    proxy.Transport = &loggingTransport{transport: originalTransport}

    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        log.Printf("[PROXY] %s %s -> %s%s", r.Method, r.URL.Path, target, r.URL.Path)

        proxy.ServeHTTP(w, r)

        log.Printf("[PROXY] %s %s completed in %v", r.Method, r.URL.Path, time.Since(start))
    })
}

type loggingTransport struct {
    transport http.RoundTripper
}

func (t *loggingTransport) RoundTrip(req *http.Request) (*http.Response, error) {
    resp, err := t.transport.RoundTrip(req)
    if err != nil {
        log.Printf("[UPSTREAM] Error: %v", err)
    } else {
        log.Printf("[UPSTREAM] %s %s -> %d", req.Method, req.URL.Path, resp.StatusCode)
    }
    return resp, err
}

func main() {
    target, _ := url.Parse("http://httpbin.org")

    log.Println("Proxy starting on :9090")
    if err := http.ListenAndServe(":9090", loggingProxy(target)); err != nil {
        log.Fatalf("Proxy failed: %v", err)
    }
}
```
</details>

### 练习 2：实现一个 JSON 配置验证器

编写一个工具，读取 JSON 配置文件并验证必填字段和数据类型。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
    "reflect"
)

type FieldRule struct {
    Required bool
    Type     string
}

var configRules = map[string]FieldRule{
    "host":    {Required: true, Type: "string"},
    "port":    {Required: true, Type: "float64"}, // JSON 数字默认为 float64
    "debug":   {Required: false, Type: "bool"},
    "tags":    {Required: false, Type: "slice"},
}

func validateConfig(data []byte) ([]string, error) {
    var config map[string]interface{}
    if err := json.Unmarshal(data, &config); err != nil {
        return nil, fmt.Errorf("invalid JSON: %w", err)
    }

    var issues []string

    for field, rule := range configRules {
        value, exists := config[field]

        if rule.Required && !exists {
            issues = append(issues, fmt.Sprintf("missing required field: %s", field))
            continue
        }

        if exists {
            actualType := reflect.TypeOf(value).Kind().String()
            if rule.Type == "slice" {
                if _, ok := value.([]interface{}); !ok {
                    issues = append(issues, fmt.Sprintf("field %s: expected array, got %s", field, actualType))
                }
            } else if actualType != rule.Type {
                issues = append(issues, fmt.Sprintf("field %s: expected %s, got %s", field, rule.Type, actualType))
            }
        }
    }

    return issues, nil
}

func main() {
    if len(os.Args) < 2 {
        fmt.Println("Usage: validator <config.json>")
        os.Exit(1)
    }

    data, err := os.ReadFile(os.Args[1])
    if err != nil {
        fmt.Printf("Error reading file: %v\n", err)
        os.Exit(1)
    }

    issues, err := validateConfig(data)
    if err != nil {
        fmt.Printf("Validation error: %v\n", err)
        os.Exit(1)
    }

    if len(issues) == 0 {
        fmt.Println("Config is valid!")
    } else {
        fmt.Printf("Found %d issues:\n", len(issues))
        for _, issue := range issues {
            fmt.Printf("  - %s\n", issue)
        }
        os.Exit(1)
    }
}
```
</details>

### 练习 3：构建一个简单的指标暴露端点

实现一个 /metrics 端点，以 Prometheus 格式暴露系统指标。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "fmt"
    "net/http"
    "runtime"
    "sync"
    "time"
)

type MetricsRegistry struct {
    mu      sync.RWMutex
    gauges  map[string]float64
    counters map[string]float64
    startTime time.Time
}

func NewMetricsRegistry() *MetricsRegistry {
    return &MetricsRegistry{
        gauges:   make(map[string]float64),
        counters: make(map[string]float64),
        startTime: time.Now(),
    }
}

func (mr *MetricsRegistry) SetGauge(name string, value float64) {
    mr.mu.Lock()
    defer mr.mu.Unlock()
    mr.gauges[name] = value
}

func (mr *MetricsRegistry) IncCounter(name string, delta float64) {
    mr.mu.Lock()
    defer mr.mu.Unlock()
    mr.counters[name] += delta
}

func (mr *MetricsRegistry) PrometheusHandler() http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        mr.mu.RLock()
        defer mr.mu.RUnlock()

        w.Header().Set("Content-Type", "text/plain; version=0.0.4")

        // 系统指标
        var mem runtime.MemStats
        runtime.ReadMemStats(&mem)

        fmt.Fprintf(w, "# HELP go_goroutines Number of goroutines\n")
        fmt.Fprintf(w, "# TYPE go_goroutines gauge\n")
        fmt.Fprintf(w, "go_goroutines %d\n", runtime.NumGoroutine())

        fmt.Fprintf(w, "# HELP go_memstats_alloc_bytes Memory allocated\n")
        fmt.Fprintf(w, "# TYPE go_memstats_alloc_bytes gauge\n")
        fmt.Fprintf(w, "go_memstats_alloc_bytes %d\n", mem.Alloc)

        fmt.Fprintf(w, "# HELP process_uptime_seconds Process uptime\n")
        fmt.Fprintf(w, "# TYPE process_uptime_seconds gauge\n")
        fmt.Fprintf(w, "process_uptime_seconds %f\n", time.Since(mr.startTime).Seconds())

        // 自定义 gauges
        for name, value := range mr.gauges {
            fmt.Fprintf(w, "# TYPE %s gauge\n", name)
            fmt.Fprintf(w, "%s %f\n", name, value)
        }

        // 自定义 counters
        for name, value := range mr.counters {
            fmt.Fprintf(w, "# TYPE %s counter\n", name)
            fmt.Fprintf(w, "%s %f\n", name, value)
        }
    }
}

func main() {
    registry := NewMetricsRegistry()

    // 设置一些示例指标
    registry.SetGauge("app_active_connections", 42)
    registry.SetGauge("app_queue_depth", 128)
    registry.IncCounter("app_requests_total", 12345)

    // 定期更新指标
    go func() {
        ticker := time.NewTicker(5 * time.Second)
        for range ticker.C {
            registry.SetGauge("app_active_connections", float64(runtime.NumGoroutine()))
        }
    }()

    mux := http.NewServeMux()
    mux.HandleFunc("/metrics", registry.PrometheusHandler())
    mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        fmt.Fprintln(w, "ok")
    })

    fmt.Println("Metrics server starting on :9090")
    http.ListenAndServe(":9090", mux)
}
```
</details>

---

## 🎯 面试题精选

### 1. Go 的 http.Server 如何实现优雅关闭？

**答：** 使用 `server.Shutdown(ctx)` 方法：
```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()
if err := server.Shutdown(ctx); err != nil {
    log.Fatalf("Shutdown: %v", err)
}
```
Shutdown 会停止接受新连接，等待现有请求完成（或 context 超时）。通常配合 signal.NotifyContext 监听 SIGTERM/SIGINT。

### 2. http.Client 的 Transport 配置有哪些关键参数？

**答：**
- `MaxIdleConns`: 总连接池大小（默认 100）
- `MaxIdleConnsPerHost`: 每个 host 的空闲连接数（默认 2）
- `MaxConnsPerHost`: 每个 host 的最大连接数（默认不限）
- `IdleConnTimeout`: 空闲连接超时（默认 90s）
- `TLSHandshakeTimeout`: TLS 握手超时（默认 10s）
- `DialContext`: 自定义拨号器（设置 TCP 超时和 KeepAlive）

### 3. json.Marshal 和 json.Encoder 的区别？

**答：**
- `json.Marshal(v)`: 将整个对象序列化为 []byte，适合一次性序列化
- `json.NewEncoder(w).Encode(v)`: 直接写入 io.Writer，适合流式序列化（HTTP 响应、文件），减少内存分配

### 4. 如何处理 JSON 中的未知字段？

**答：** 使用 `json.Decoder` 的 `DisallowUnknownFields()` 方法，或使用 `map[string]interface{}` 接收动态字段。还可以自定义 UnmarshalJSON 方法实现灵活解析。

### 5. os/exec 如何防止命令注入？

**答：**
- 永远不要使用 `exec.Command("sh", "-c", userInput)` 直接拼接用户输入
- 使用 `exec.Command(name, args...)` 分离命令和参数
- 对用户输入进行白名单校验
- 使用 context 设置超时防止命令长时间运行

### 6. log/slog 比标准 log 包有什么优势？

**答：**
- 结构化日志：键值对格式，便于日志系统解析
- 级别控制：Debug/Info/Warn/Error，可在运行时调整
- 自定义 Handler：可输出 JSON、自定义格式、发送到远程
- 性能更好：避免不必要的字符串格式化
- With/WithGroup：创建带上下文的子 logger

### 7. HTTP 中间件的执行顺序是怎样的？

**答：** 中间件是洋葱模型（请求从外到内，响应从内到外）：
```
请求 → Middleware1 → Middleware2 → Handler → Middleware2 → Middleware1 → 响应
```
Chain 函数中从后向前包装，最前面的中间件最先执行（包含错误处理、panic 恢复等）。

### 8. 如何实现 HTTP 请求的幂等性？

**答：** 使用请求 ID（Idempotency-Key header）：
- 客户端生成唯一 ID 并携带在请求头中
- 服务端记录已处理的 ID 和结果
- 重复请求直接返回缓存的结果
- 可以使用 Redis 等存储 ID 映射

### 9. Go 标准库的 http.Get 为什么不推荐在生产环境使用？

**答：** `http.Get` 使用 `http.DefaultClient`，其问题：
- 没有超时限制（Timeout=0 意味着无限等待）
- 默认 Transport 的 MaxIdleConnsPerHost 只有 2
- 共享同一个 Client，无法独立配置
- 生产环境应创建自定义 Client 并设置合理的超时和连接池参数。

### 10. 如何用 Go 实现一个简单的反向代理？

**答：** 使用 `httputil.NewSingleHostReverseProxy`：
```go
target, _ := url.Parse("http://backend:8080")
proxy := httputil.NewSingleHostReverseProxy(target)
http.ListenAndServe(":80", proxy)
```
可以自定义 Director 修改请求、自定义 Transport 修改响应、添加中间件实现负载均衡和熔断。

---

## 📚 深入阅读

- [Go 官方博客：JSON](https://go.dev/blog/json) — JSON 处理详解
- [net/http 包文档](https://pkg.go.dev/net/http) — 完整 API
- [Go 官方博客：HTTP 性能](https://go.dev/blog/http-server-performance) — 服务端性能优化
- [log/slog 包文档](https://pkg.go.dev/log/slog) — 结构化日志
- [Go 标准库概览](https://pkg.go.dev/std) — 所有标准库包
- [《Go 语言圣经》第 5 章](https://books.studygolang.com/gopl-zh/ch5/ch5.html) — 函数和包
- [《Go 语言圣经》第 7 章](https://books.studygolang.com/gopl-zh/ch7/ch7.html) — 接口

---

## ✅ 自检清单

- [ ] 能使用 net/http 构建带中间件的 HTTP 服务
- [ ] 能正确配置 HTTP 客户端的超时和连接池
- [ ] 理解 Go 1.22+ 的增强路由特性
- [ ] 掌握 JSON 序列化/反序列化的各种模式
- [ ] 能使用 os/exec 安全地执行外部命令
- [ ] 能使用 log/slog 输出结构化日志
- [ ] 能实现中间件链（Recovery, CORS, Auth, RateLimit）
- [ ] 能为 SRE 场景构建健康检查服务
