#!/usr/bin/env python3
"""
Rich content generators for SRE learning days (Day 67-194).
Each generator produces 400-500+ lines of detailed content.
Import this module into daily_study_generator.py
"""

# ── Go 语言生成器 ───────────────────────────────────────────────────────

def generate_go_content(day: int, topic: str) -> str:
    """生成 Go 语言相关内容（Day 57-69）"""
    content_map = {
        57: generate_go_env_content,
        58: generate_go_syntax_content,
        59: generate_go_error_content,
        60: generate_go_data_structure_content,
        61: generate_go_interface_content,
        62: generate_go_concurrency_content,
        63: generate_go_network_content,
        64: generate_go_cli_content,
        65: generate_go_context_content,
        66: generate_go_test_content,
    }
    if day in content_map:
        return content_map[day]()
    return generate_go_default_content(topic)


def generate_go_env_content() -> str:
    return """### 1. Go 语言简介

#### 1.1 为什么 SRE 要学 Go？

Go（Golang）是 Google 于 2009 年发布的开源编程语言，由 Robert Griesemer、Rob Pike 和 Ken Thompson 设计。在 SRE 和云原生领域，Go 已经是事实上的标准语言：

| 项目 | 语言 | 说明 |
|------|------|------|
| **Docker** | Go | 容器运行时 |
| **Kubernetes** | Go | 容器编排平台 |
| **Prometheus** | Go | 监控系统 |
| **Terraform** | Go | 基础设施即代码 |
| **etcd** | Go | 分布式键值存储 |
| **Consul** | Go | 服务发现与配置 |
| **Envoy** | C++ | 但其控制面多用 Go |
| **Helm** | Go | K8s 包管理器 |

**选择 Go 而非 Python 做运维工具的原因**：
```
✅ 编译为单一静态二进制文件，部署无需依赖
✅ 原生并发（goroutine）比 Python 线程高效得多
✅ 强类型，大型项目可维护性更好
✅ 启动速度毫秒级，适合 CLI 工具和微服务
✅ 垃圾回收，比 C/C++ 开发效率高
✅ 交叉编译简单（GOOS=linux GOARCH=arm64 go build）
```

#### 1.2 Go 的核心设计哲学

```
简单胜于复杂      — 25 个关键字，语法简单，新人 1 周上手
组合胜于继承      — 用 interface + struct 组合，而非类继承
显式胜于隐式      — 错误处理用返回值，不用异常
并发是一等公民    — goroutine + channel 原生支持
```

### 2. Go 环境搭建

#### 2.1 安装 Go

```bash
# 方法 1：官方二进制包安装（推荐）
curl -fsSL https://go.dev/dl/go1.22.0.linux-amd64.tar.gz | sudo tar -C /usr/local -xzf -

# 添加到 PATH（写入 ~/.bashrc 或 ~/.zshrc）
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
echo 'export GOPATH=$HOME/go' >> ~/.bashrc
echo 'export PATH=$PATH:$GOPATH/bin' >> ~/.bashrc
source ~/.bashrc

# 验证安装
go version
# go version go1.22.0 linux/amd64
```

**方法 2：包管理器安装**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y golang-go

# Rocky/CentOS/RHEL
sudo dnf install -y golang

# macOS
brew install go
```

#### 2.2 Go 工作区结构

```
~/go/
├── bin/          # 编译后的可执行文件（go install 产物）
├── pkg/          # 编译缓存
└── src/          # 源代码（Go Modules 模式下不必须）
```

**Go Modules（现代项目管理）**：
```bash
# 创建新项目
mkdir ~/projects/sre-tools && cd ~/projects/sre-tools
go mod init github.com/yourname/sre-tools

# 生成 go.mod 文件
cat go.mod
# module github.com/yourname/sre-tools
# 
# go 1.22
```

#### 2.3 开发工具配置

**VS Code + Go 扩展**：
```bash
# 安装 Go 扩展后，安装语言工具
go install golang.org/x/tools/gopls@latest       # 语言服务器
go install honnef.co/go/tools/cmd/staticcheck@latest  # 静态分析
go install github.com/go-delve/delve/cmd/dlv@latest    # 调试器
```

**golangci-lint（推荐的 linter 集合）**：
```bash
go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

# 在项目根目录运行
golangci-lint run

# 常见 linter 规则：
# - errcheck: 检查未处理的错误返回值
# - gofmt: 代码格式化
# - govet: 常见 bug 检测
# - staticcheck: 高级静态分析
```

#### 2.4 GOPROXY 配置（国内加速）

```bash
# 使用七牛云或阿里云代理
go env -w GOPROXY=https://goproxy.cn,direct
# 或使用阿里云
go env -w GOPROXY=https://mirrors.aliyun.com/goproxy/,direct

# 确认配置
go env GOPROXY
```

### 3. 第一个 Go 程序

```go
// main.go - SRE 系统信息工具
package main

import (
    "fmt"
    "os"
    "runtime"
)

func main() {
    fmt.Println("=== SRE System Info ===")
    fmt.Printf("OS:       %s\\n", runtime.GOOS)
    fmt.Printf("Arch:     %s\\n", runtime.GOARCH)
    fmt.Printf("CPU Cores: %d\\n", runtime.NumCPU())
    fmt.Printf("Go Version: %s\\n", runtime.Version())
    
    hostname, err := os.Hostname()
    if err != nil {
        fmt.Fprintf(os.Stderr, "Error getting hostname: %v\\n", err)
        os.Exit(1)
    }
    fmt.Printf("Hostname: %s\\n", hostname)
}
```

**编译与运行**：
```bash
# 直接运行
go run main.go

# 编译为二进制
go build -o sre-info main.go
./sre-info

# 安装到 $GOPATH/bin
go install
sre-info  # 全局可用
```

### 4. SRE 视角：Go vs Python vs Bash

| 维度 | Bash | Python | Go |
|------|------|--------|-----|
| **启动速度** | 毫秒级 | 100-500ms | 毫秒级 |
| **并发能力** | 弱（xargs -P） | GIL 限制 | 原生 goroutine |
| **部署** | 无需编译 | 需要 pip/venv | 单一二进制 |
| **类型安全** | 无 | 动态（可选 type hints） | 静态强类型 |
| **适合场景** | 简单脚本、一行命令 | 数据分析、ML、胶水代码 | CLI 工具、微服务、Agent |
| **学习曲线** | 低 | 中 | 中 |

### 5. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `command not found: go` | PATH 未配置 | `export PATH=$PATH:/usr/local/go/bin` |
| 模块下载慢 | 网络问题 | 配置 `GOPROXY=https://goproxy.cn,direct` |
| `go: no modules detected` | 未初始化 module | `go mod init` |
| 编译后文件很大 | 包含调试信息 | `go build -ldflags="-s -w"` 去除符号表 |
| 交叉编译失败 | CGO 未禁用 | `CGO_ENABLED=0 GOOS=linux go build` |
"""


def generate_go_syntax_content() -> str:
    return """### 1. Go 基础语法

#### 1.1 变量与数据类型

Go 是静态类型语言，变量声明有几种方式：

```go
package main

import "fmt"

func main() {
    // 1. 显式声明
    var name string = "SRE"
    var port int = 8080
    var debug bool = true

    // 2. 类型推断（省略类型）
    var host = "localhost"

    // 3. 短变量声明（最常用，仅限函数内）
    path := "/api/health"

    // 4. 多变量声明
    var (
        timeout  = 30
        retries  = 3
        interval = 5.0
    )

    // 5. 零值（未初始化的变量有默认零值）
    var count int      // 0
    var msg string     // ""
    var active bool    // false
    var prices []int   // nil
    var config map[string]string  // nil

    fmt.Printf("%s:%d%s timeout=%d retries=%d\\n",
        host, port, path, timeout, retries)
}
```

**基本类型**：
| 类型 | 说明 | 零值 |
|------|------|------|
| `bool` | 布尔值 | `false` |
| `string` | 字符串（不可变，UTF-8） | `""` |
| `int`/`int8`/`int16`/`int32`/`int64` | 整数 | `0` |
| `uint`/`uint8`/`uint16`/`uint32`/`uint64` | 无符号整数 | `0` |
| `float32`/`float64` | 浮点数 | `0.0` |
| `byte` | uint8 别名，表示字节 | `0` |
| `rune` | int32 别名，表示 Unicode 码点 | `0` |

#### 1.2 控制流

```go
// if-else
func checkPort(port int) string {
    if port < 1 || port > 65535 {
        return "invalid"
    } else if port < 1024 {
        return "privileged"
    }
    return "normal"
}

// for 循环（Go 只有 for，没有 while）
func countServers(n int) {
    // 传统 for
    for i := 0; i < n; i++ {
        fmt.Printf("Server %d\\n", i)
    }

    // while 风格
    retries := 3
    for retries > 0 {
        fmt.Printf("Retrying... %d left\\n", retries)
        retries--
    }

    // 无限循环
    // for {
    //     // 持续监控
    // }
}

// switch
func serviceStatus(code int) string {
    switch code {
    case 200, 201, 204:
        return "success"
    case 400, 401, 403, 404:
        return "client_error"
    case 500, 502, 503:
        return "server_error"
    default:
        return "unknown"
    }
}

// switch 带初始化语句
func checkHealth(url string) string {
    switch resp := httpGet(url); {
    case resp.StatusCode < 300:
        return "healthy"
    case resp.StatusCode < 500:
        return "degraded"
    default:
        return "unhealthy"
    }
}
```

#### 1.3 数组与切片

```go
package main

import "fmt"

func main() {
    // 数组（固定大小，很少直接用）
    var arr [5]int
    arr[0] = 10
    fmt.Println(arr) // [10 0 0 0 0]

    // 切片（动态数组，最常用）
    servers := []string{"web-01", "web-02", "db-01"}
    servers = append(servers, "cache-01")

    // 切片操作
    fmt.Println(servers[1:3])  // [web-02 db-01]
    fmt.Println(servers[:2])   // [web-01 web-02]
    fmt.Println(servers[2:])   // [db-01 cache-01]
    fmt.Println(len(servers))  // 4

    // make 创建切片（预分配容量）
    metrics := make([]float64, 0, 100) // len=0, cap=100

    // 遍历切片
    for i, s := range servers {
        fmt.Printf("[%d] %s\\n", i, s)
    }
}
```

**切片 vs 数组的关键区别**：
```
数组：[5]int — 大小固定，值类型，赋值会拷贝
切片：[]int — 大小动态，引用类型，底层共享数组
```

#### 1.4 结构体（Struct）

```go
package main

import "fmt"

// 定义结构体
type Server struct {
    Name    string
    IP      string
    Port    int
    Healthy bool
    Tags    []string
}

func main() {
    // 创建实例
    srv := Server{
        Name:    "web-01",
        IP:      "10.0.1.10",
        Port:    8080,
        Healthy: true,
        Tags:    []string{"production", "web"},
    }

    // 访问字段
    fmt.Printf("%s @ %s:%d\\n", srv.Name, srv.IP, srv.Port)

    // 方法（接收者）
    fmt.Println(srv.URL()) // http://10.0.1.10:8080
    srv.MarkUnhealthy()
    fmt.Println(srv.Healthy) // false
}

// 值接收者方法
func (s Server) URL() string {
    return fmt.Sprintf("http://%s:%d", s.IP, s.Port)
}

// 指针接收者方法（可以修改原值）
func (s *Server) MarkUnhealthy() {
    s.Healthy = false
}
```

### 2. SRE 实战：用 Go 结构体定义监控模型

```go
// monitor/model.go
package monitor

import "time"

type Metric struct {
    Name      string
    Value     float64
    Labels    map[string]string
    Timestamp time.Time
}

type Alert struct {
    Name        string
    Severity    string    // "critical", "warning", "info"
    Message     string
    TriggeredAt time.Time
    ResolvedAt  *time.Time
}

type ServerStatus struct {
    Hostname     string
    CPUUsage     float64
    MemoryUsage  float64
    DiskUsage    float64
    LoadAvg      [3]float64
    Uptime       time.Duration
    Services     []ServiceStatus
}

type ServiceStatus struct {
    Name    string
    Running bool
    PID     int
    Uptime  time.Duration
}
```

### 3. 字符串操作

```go
package main

import (
    "fmt"
    "strings"
)

func main() {
    s := "  Hello, SRE World!  "

    // 常用操作
    fmt.Println(strings.TrimSpace(s))     // "Hello, SRE World!"
    fmt.Println(strings.ToLower(s))       // "  hello, sre world!  "
    fmt.Println(strings.Contains(s, "SRE")) // true
    fmt.Println(strings.Split(s, ","))    // ["  Hello" " SRE World!  "]
    fmt.Println(strings.Join([]string{"a", "b", "c"}, "-")) // "a-b-c"
    fmt.Println(strings.Replace(s, "SRE", "DevOps", 1))

    // 字符串格式化
    name := "nginx"
    port := 80
    fmt.Printf("Service: %s, Port: %d\\n", name, port)

    // Sprintf 返回字符串（不打印）
    url := fmt.Sprintf("http://localhost:%d/health", port)
    fmt.Println(url)
}
```

### 4. Map（映射/字典）

```go
package main

import "fmt"

func main() {
    // 创建 map
    config := map[string]string{
        "host": "localhost",
        "port": "8080",
        "env":  "production",
    }

    // 访问
    fmt.Println(config["host"]) // localhost

    // 安全访问（检查 key 是否存在）
    val, ok := config["timeout"]
    if !ok {
        fmt.Println("key not found")
    }

    // 修改/添加
    config["timeout"] = "30s"
    config["env"] = "staging"

    // 删除
    delete(config, "env")

    // 遍历（无序！）
    for k, v := range config {
        fmt.Printf("%s=%s\\n", k, v)
    }

    // 嵌套 map
    servers := map[string]map[string]int{
        "web-01": {"cpu": 45, "mem": 72},
        "web-02": {"cpu": 38, "mem": 65},
    }
    fmt.Println(servers["web-01"]["cpu"]) // 45
}
```

### 5. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 编译报错 "declared and not used" | Go 不允许未使用的变量 | 用 `_` 忽略，或删除变量 |
| `:=` 在函数外报错 | 短声明只能在函数内用 | 函数外用 `var` |
| map 写入 panic: nil map | map 未初始化 | `make(map[K]V)` 或 `map[K]V{}` |
| 切片追加后原数据变了 | 切片共享底层数组 | 用 `copy()` 或 `append()` 创建副本 |
| 字符串拼接性能差 | 字符串不可变 | 大量拼接用 `strings.Builder` |
"""


def generate_go_error_content() -> str:
    return """### 1. Go 函数定义

#### 1.1 基本函数

```go
package main

import "fmt"

// 基本函数
func greet(name string) string {
    return fmt.Sprintf("Hello, %s!", name)
}

// 多返回值（Go 的特色）
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, fmt.Errorf("division by zero")
    }
    return a / b, nil
}

// 命名返回值
func stats(numbers []float64) (min, max, avg float64) {
    if len(numbers) == 0 {
        return 0, 0, 0
    }
    min = numbers[0]
    max = numbers[0]
    var sum float64
    for _, n := range numbers {
        if n < min {
            min = n
        }
        if n > max {
            max = n
        }
        sum += n
    }
    avg = sum / float64(len(numbers))
    return // 自动返回命名的返回值
}

func main() {
    fmt.Println(greet("SRE"))

    result, err := divide(10, 3)
    if err != nil {
        fmt.Println("Error:", err)
    } else {
        fmt.Printf("Result: %.2f\\n", result)
    }

    min, max, avg := stats([]float64{1.5, 3.2, 0.8, 5.1})
    fmt.Printf("Min: %.1f, Max: %.1f, Avg: %.1f\\n", min, max, avg)
}
```

#### 1.2 可变参数

```go
func sum(numbers ...int) int {
    total := 0
    for _, n := range numbers {
        total += n
    }
    return total
}

// 调用
sum(1, 2, 3)       // 6
sum(10, 20)        // 30
sum()              // 0
nums := []int{1, 2, 3, 4}
sum(nums...)       // 展开切片
```

#### 1.3 匿名函数与闭包

```go
func main() {
    // 匿名函数
    greet := func(name string) {
        fmt.Println("Hello,", name)
    }
    greet("World")

    // 闭包
    counter := func() func() int {
        count := 0
        return func() int {
            count++
            return count
        }
    }()

    fmt.Println(counter()) // 1
    fmt.Println(counter()) // 2
}
```

### 2. 错误处理（Go 的核心机制）

#### 2.1 error 接口

Go 没有 try/catch，错误处理通过返回值实现：

```go
// error 是一个接口
type error interface {
    Error() string
}

// 常见模式：最后一个返回值是 error
func readFile(path string) ([]byte, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("failed to read %s: %w", path, err)
    }
    return data, nil
}
```

#### 2.2 错误处理最佳实践

```go
package main

import (
    "errors"
    "fmt"
    "os"
)

// 定义 sentinel error
var ErrNotFound = errors.New("resource not found")
var ErrPermission = errors.New("permission denied")

func getUser(id int) (string, error) {
    if id <= 0 {
        return "", fmt.Errorf("invalid user id %d: %w", id, ErrNotFound)
    }
    // ... 查询逻辑
    return "zhangsan", nil
}

func main() {
    name, err := getUser(-1)
    if err != nil {
        // 检查错误类型
        if errors.Is(err, ErrNotFound) {
            fmt.Println("User not found")
        } else {
            fmt.Printf("Unexpected error: %v\\n", err)
        }
        return
    }
    fmt.Println("User:", name)
}
```

**错误处理规则**：
```
1. 错误应该立即处理，不要忽略
   ❌ getData()     // 忽略 error
   ✅ data, err := getData()
      if err != nil { ... }

2. 错误信息要有上下文
   ❌ return err
   ✅ return fmt.Errorf("deploy %s to %s: %w", app, env, err)

3. 使用 %w 包装错误（Go 1.13+）
   - 可以用 errors.Is() 和 errors.As() 检查

4. 只在最上层处理错误（打印/返回给用户）
   - 中间层包装错误，不打印
```

#### 2.3 defer — 延迟执行

```go
func processFile(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close() // 函数返回时执行，即使有 panic

    // 处理文件...
    // 不管下面 return 还是 panic，f.Close() 都会执行

    return nil
}

// 多个 defer（后进先出）
func example() {
    defer fmt.Println("1st")
    defer fmt.Println("2nd")
    defer fmt.Println("3rd")
    // 输出：3rd, 2nd, 1st
}
```

**SRE 实战：defer 用于资源清理**：
```go
func runHealthCheck(url string) error {
    resp, err := http.Get(url)
    if err != nil {
        return fmt.Errorf("health check failed: %w", err)
    }
    defer resp.Body.Close() // 确保连接释放

    if resp.StatusCode != 200 {
        return fmt.Errorf("status %d", resp.StatusCode)
    }
    return nil
}
```

### 3. SRE 实战：用 defer 实现优雅关闭

```go
package main

import (
    "context"
    "fmt"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("OK"))
    })

    server := &http.Server{
        Addr:    ":8080",
        Handler: mux,
    }

    // 优雅关闭
    go func() {
        <-signalChan()
        fmt.Println("\\nShutting down...")
        ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
        defer cancel()
        server.Shutdown(ctx)
    }()

    fmt.Println("Server starting on :8080")
    if err := server.ListenAndServe(); err != http.ErrServerClosed {
        fmt.Fprintf(os.Stderr, "Server error: %v\\n", err)
        os.Exit(1)
    }
    fmt.Println("Server stopped")
}

func signalChan() <-chan os.Signal {
    ch := make(chan os.Signal, 1)
    signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
    return ch
}
```

### 4. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 忘记检查 error | Go 不强制处理 error | 用 `golangci-lint` 的 errcheck |
| defer 在循环内 | 延迟执行累积 | 循环内用匿名函数包 defer |
| nil error 判断出错 | error 是接口 | 用 `errors.Is()` 而非 `==` |
| defer 参数过早求值 | defer 时参数已确定 | defer 用函数而非值 |
"""


def generate_go_data_structure_content() -> str:
    return """### 1. Go 切片深入

#### 1.1 切片内部结构

切片是一个三字段结构体：
```go
type slice struct {
    array unsafe.Pointer  // 指向底层数组的指针
    len   int             // 当前长度
    cap   int             // 容量（从指针位置到数组末尾）
}
```

```go
package main

import "fmt"

func main() {
    // 创建切片
    s := []int{1, 2, 3, 4, 5}
    fmt.Printf("len=%d cap=%d %v\\n", len(s), cap(s), s)

    // 切片共享底层数组
    s2 := s[1:3] // [2, 3]
    fmt.Printf("s2: len=%d cap=%d %v\\n", len(s2), cap(s2), s2)

    // 修改 s2 会影响 s
    s2[0] = 200
    fmt.Println(s) // [1, 200, 3, 4, 5]

    // append 可能分配新数组
    s3 := append(s2, 300, 400, 500, 600)
    // cap(s2)=4, 追加 4 个元素后超出容量，分配新数组
    s3[0] = 999
    fmt.Println(s2) // [999, 3] — s2 和 s3 现在独立
}
```

#### 1.2 切片操作性能

```go
// 预分配容量（避免反复扩容）
data := make([]int, 0, 1000) // len=0, cap=1000
for i := 0; i < 1000; i++ {
    data = append(data, i)
}

// 不预分配（会反复分配+拷贝）
data := []int{}
for i := 0; i < 1000; i++ {
    data = append(data, i) // 触发 ~10 次扩容
}
```

### 2. Map 深入

#### 2.1 Map 原理

Go 的 map 基于哈希表实现：
```go
// 创建
m := make(map[string]int)
m["cpu"] = 85
m["mem"] = 72

// 安全访问
val, exists := m["disk"]
if !exists {
    fmt.Println("key not found")
}

// 遍历（注意：顺序不保证！）
for key, val := range m {
    fmt.Printf("%s: %d\\n", key, val)
}

// 删除
delete(m, "cpu")

// 嵌套 map
servers := map[string]map[string]float64{
    "web-01": {"cpu": 45.2, "mem": 72.1},
    "db-01":  {"cpu": 88.5, "mem": 91.3},
}
```

**Map 注意事项**：
```
❌ map 不是并发安全的！
   多个 goroutine 同时读写会 panic: concurrent map writes

✅ 解决方案：
   1. sync.Map（读多写少）
   2. sync.RWMutex + 普通 map（通用）
   3. channel 传递数据
```

#### 2.2 sync.Map（并发安全）

```go
package main

import (
    "fmt"
    "sync"
)

func main() {
    var m sync.Map

    // 存储
    m.Store("web-01", map[string]int{"cpu": 45, "mem": 72})
    m.Store("web-02", map[string]int{"cpu": 38, "mem": 65})

    // 读取
    val, ok := m.Load("web-01")
    if ok {
        fmt.Printf("Found: %v\\n", val)
    }

    // 遍历
    m.Range(func(key, value interface{}) bool {
        fmt.Printf("%s: %v\\n", key, value)
        return true
    })

    // 删除
    m.Delete("web-02")
}
```

### 3. 结构体标签与 JSON 序列化

```go
package main

import (
    "encoding/json"
    "fmt"
)

type Server struct {
    ID        int               `json:"id"`
    Name      string            `json:"name"`
    IPAddress string            `json:"ip_address"`
    Port      int               `json:"port,omitempty"`
    Tags      []string          `json:"tags,omitempty"`
    Metadata  map[string]string `json:"metadata,omitempty"`
}

func main() {
    // 结构体 → JSON
    srv := Server{
        ID:        1,
        Name:      "web-01",
        IPAddress: "10.0.1.10",
        Tags:      []string{"production", "web"},
    }

    data, _ := json.MarshalIndent(srv, "", "  ")
    fmt.Println(string(data))
    // {
    //   "id": 1,
    //   "name": "web-01",
    //   "ip_address": "10.0.1.10",
    //   "tags": ["production", "web"]
    // }

    // JSON → 结构体
    var parsed Server
    json.Unmarshal(data, &parsed)
    fmt.Printf("%+v\\n", parsed)
}
```

### 4. SRE 实战：用结构体表示监控配置

```go
type MonitorConfig struct {
    Interval    time.Duration `json:"interval"`
    Timeout     time.Duration `json:"timeout"`
    Retries     int           `json:"retries"`
    Endpoints   []Endpoint    `json:"endpoints"`
    AlertRules  []AlertRule   `json:"alert_rules"`
}

type Endpoint struct {
    Name    string            `json:"name"`
    URL     string            `json:"url"`
    Method  string            `json:"method"`
    Headers map[string]string `json:"headers,omitempty"`
    Expect  ExpectConfig      `json:"expect"`
}

type ExpectConfig struct {
    StatusCode int    `json:"status_code"`
    BodyMatch  string `json:"body_match,omitempty"`
    MaxLatency int    `json:"max_latency_ms"`
}

type AlertRule struct {
    Name      string `json:"name"`
    Condition string `json:"condition"`  // "cpu > 90 for 5m"
    Severity  string `json:"severity"`   // "critical", "warning"
    Channel   string `json:"channel"`    // "slack", "pagerduty"
}
```

### 5. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 切片 append 后原数据变了 | 超出容量分配了新数组 | 检查 cap，用 copy 创建独立副本 |
| map 并发写 panic | 非线程安全 | 用 sync.RWMutex 或 sync.Map |
| JSON 序列化空字段 | 零值也会被序列化 | 用 `omitempty` 标签 |
| 结构体比较报错 | 含不可比较字段 | 用 reflect.DeepEqual 或逐字段比较 |
"""


def generate_go_interface_content() -> str:
    return """### 1. Go 接口

#### 1.1 接口定义与隐式实现

Go 的接口是**隐式实现** — 不需要显式声明 implements：

```go
package main

import "fmt"

// 定义接口
type Checker interface {
    Check() bool
    Name() string
}

type HTTPChecker struct {
    URL string
}

// 隐式实现 Checker 接口
func (h HTTPChecker) Check() bool {
    resp, err := http.Get(h.URL)
    if err != nil {
        return false
    }
    defer resp.Body.Close()
    return resp.StatusCode == 200
}

func (h HTTPChecker) Name() string {
    return "http:" + h.URL
}

// TCPChecker 也实现同一个接口
type TCPChecker struct {
    Host string
    Port int
}

func (t TCPChecker) Check() bool {
    conn, err := net.DialTimeout("tcp",
        fmt.Sprintf("%s:%d", t.Host, t.Port), 3*time.Second)
    if err != nil {
        return false
    }
    conn.Close()
    return true
}

func (t TCPChecker) Name() string {
    return fmt.Sprintf("tcp://%s:%d", t.Host, t.Port)
}

func main() {
    // 多态：同一个接口，不同实现
    checkers := []Checker{
        HTTPChecker{URL: "http://localhost:8080/health"},
        TCPChecker{Host: "localhost", Port: 5432},
    }

    for _, c := range checkers {
        status := "DOWN"
        if c.Check() {
            status = "UP"
        }
        fmt.Printf("[%s] %s\\n", status, c.Name())
    }
}
```

#### 1.2 接口组合

```go
// io.Reader 和 io.Writer（Go 标准库）
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

// 组合接口
type ReadWriter interface {
    Reader
    Writer
}

type ReadWriteCloser interface {
    Reader
    Writer
    Closer
}
```

### 2. 组合优于继承

Go 没有继承，用**嵌入（embedding）**实现组合：

```go
type BaseChecker struct {
    Interval time.Duration
    Timeout  time.Duration
    Retries  int
}

func (b BaseChecker) GetInterval() time.Duration {
    return b.Interval
}

func (b BaseChecker) GetRetries() int {
    return b.Retries
}

// HTTPChecker 嵌入 BaseChecker
type HTTPChecker struct {
    BaseChecker  // 嵌入，继承字段和方法
    URL     string
    Method  string
}

func main() {
    hc := HTTPChecker{
        BaseChecker: BaseChecker{
            Interval: 30 * time.Second,
            Timeout:  5 * time.Second,
            Retries:  3,
        },
        URL:    "http://api.example.com/health",
        Method: "GET",
    }

    // 直接使用嵌入的字段和方法
    fmt.Println(hc.Interval)     // 30s
    fmt.Println(hc.GetRetries())  // 3
}
```

### 3. SRE 实战：用接口设计健康检查框架

```go
// checker.go
package checker

import "time"

// Checker 定义所有健康检查器必须实现的接口
type Checker interface {
    Check() (Result, error)
    Name() string
}

// Result 统一检查结果
type Result struct {
    Healthy  bool
    Latency  time.Duration
    Message  string
    CheckedAt time.Time
}

// Runner 执行一组检查器
type Runner struct {
    Checkers []Checker
    Interval time.Duration
}

func (r *Runner) Run() []Result {
    results := make([]Result, len(r.Checkers))
    for i, c := range r.Checkers {
        start := time.Now()
        res, err := c.Check()
        res.Latency = time.Since(start)
        res.CheckedAt = time.Now()
        if err != nil {
            res.Message = err.Error()
        }
        results[i] = res
    }
    return results
}
```

### 4. 空接口与类型断言

```go
// interface{} (或 any) 可以持有任何类型
func printValue(v interface{}) {
    switch t := v.(type) {
    case string:
        fmt.Printf("string: %q\\n", t)
    case int:
        fmt.Printf("int: %d\\n", t)
    case []string:
        fmt.Printf("slice: %v\\n", t)
    default:
        fmt.Printf("unknown: %T\\n", v)
    }
}

// 类型断言
func getConfig(key string) (interface{}, bool) {
    config := map[string]interface{}{
        "port": 8080,
        "host": "localhost",
        "debug": true,
    }
    val, ok := config[key]
    return val, ok
}

// 使用
val, ok := getConfig("port")
if ok {
    port := val.(int) // 类型断言
    fmt.Println(port)
}
```

### 5. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 接口值为 nil 但 != nil | 接口是 (type, value) 二元组 | 比较前确保赋 nil 接口值 |
| 接口类型断言 panic | 类型不匹配 | 用 `v, ok := x.(T)` 安全断言 |
| interface{} 性能差 | 需要装箱/拆箱 | 尽量用具体类型或泛型 |
"""


def generate_go_concurrency_content() -> str:
    return """### 1. Goroutine — Go 的并发原语

#### 1.1 什么是 Goroutine？

Goroutine 是 Go 的轻量级线程，由 Go runtime 调度管理：

| 特性 | OS 线程 | Goroutine |
|------|---------|-----------|
| 大小 | 1-2 MB | 2 KB（动态增长） |
| 创建开销 | 慢（系统调用） | 快（~2μs） |
| 数量 | ~几千 | ~百万 |
| 调度 | OS 内核 | Go runtime（M:P:G 模型） |
| 切换 | 内核态 | 用户态 |

```go
package main

import (
    "fmt"
    "time"
)

func checkServer(name string) {
    fmt.Printf("Checking %s...\\n", name)
    time.Sleep(1 * time.Second) // 模拟网络请求
    fmt.Printf("%s is UP\\n", name)
}

func main() {
    servers := []string{"web-01", "web-02", "db-01", "cache-01"}

    // 串行执行（4 秒）
    // for _, s := range servers {
    //     checkServer(s)
    // }

    // 并发执行（~1 秒）
    for _, s := range servers {
        go checkServer(s) // 启动 goroutine
    }

    // 等待 goroutine 完成
    time.Sleep(2 * time.Second)
}
```

#### 1.2 WaitGroup — 等待多个 Goroutine

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

func main() {
    servers := []string{"web-01", "web-02", "db-01", "cache-01"}
    var wg sync.WaitGroup

    for _, s := range servers {
        wg.Add(1) // 增加计数
        go func(name string) {
            defer wg.Done() // 完成时减少计数
            checkServer(name)
        }(s)
    }

    wg.Wait() // 等待所有完成
    fmt.Println("All checks done!")
}

func checkServer(name string) {
    time.Sleep(1 * time.Second)
    fmt.Printf("%s checked\\n", name)
}
```

### 2. Channel — Goroutine 间通信

> **Go 的并发哲学：不要通过共享内存来通信，而要通过通信来共享内存**

#### 2.1 基础 Channel

```go
package main

import "fmt"

func main() {
    // 创建 channel
    ch := make(chan string)

    // 发送
    go func() {
        ch <- "health check result"
    }()

    // 接收（阻塞直到有数据）
    result := <-ch
    fmt.Println(result)
}
```

#### 2.2 带缓冲的 Channel

```go
// 无缓冲（同步）
ch := make(chan int)       // 发送和接收必须配对

// 带缓冲（异步）
ch := make(chan int, 10)   // 最多存 10 个值不阻塞
ch <- 1
ch <- 2
// ... 前 10 个不会阻塞
```

#### 2.3 Worker Pool 模式（SRE 常用）

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

func main() {
    servers := []string{}
    for i := 1; i <= 20; i++ {
        servers = append(servers, fmt.Sprintf("web-%02d", i))
    }

    // 工作通道
    jobs := make(chan string, len(servers))
    results := make(chan string, len(servers))

    // 启动 5 个 worker
    var wg sync.WaitGroup
    for w := 1; w <= 5; w++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for server := range jobs {
                time.Sleep(200 * time.Millisecond) // 模拟检查
                results <- fmt.Sprintf("[Worker %d] %s: OK", id, server)
            }
        }(w)
    }

    // 发送任务
    for _, s := range servers {
        jobs <- s
    }
    close(jobs) // 关闭通道，通知 worker 没有更多任务

    // 等待完成
    go func() {
        wg.Wait()
        close(results)
    }()

    // 收集结果
    for r := range results {
        fmt.Println(r)
    }
}
```

### 3. Select — 多路复用

```go
func main() {
    ch1 := make(chan string)
    ch2 := make(chan string)
    done := make(chan bool)

    go func() { ch1 <- "from ch1" }()
    go func() { ch2 <- "from ch2" }()

    for {
        select {
        case msg := <-ch1:
            fmt.Println(msg)
        case msg := <-ch2:
            fmt.Println(msg)
        case <-done:
            fmt.Println("Done!")
            return
        case <-time.After(5 * time.Second):
            fmt.Println("Timeout!")
            return
        }
    }
}
```

### 4. Sync — 互斥锁

```go
var (
    mu      sync.RWMutex
    metrics = make(map[string]float64)
)

func updateMetric(name string, value float64) {
    mu.Lock()
    defer mu.Unlock()
    metrics[name] = value
}

func getMetric(name string) float64 {
    mu.RLock()
    defer mu.RUnlock()
    return metrics[name]
}

func getSnapshot() map[string]float64 {
    mu.RLock()
    defer mu.RUnlock()
    snapshot := make(map[string]float64)
    for k, v := range metrics {
        snapshot[k] = v
    }
    return snapshot
}
```

### 5. SRE 实战：并发服务器巡检

```go
func inspectServers(servers []ServerConfig) []InspectionResult {
    var (
        mu      sync.Mutex
        results []InspectionResult
        wg      sync.WaitGroup
    )

    // 限制并发数
    sem := make(chan struct{}, 10)

    for _, srv := range servers {
        wg.Add(1)
        go func(s ServerConfig) {
            defer wg.Done()
            sem <- struct{}{}        // 获取信号量
            defer func() { <-sem }() // 释放信号量

            res := inspectSingle(s)
            mu.Lock()
            results = append(results, res)
            mu.Unlock()
        }(srv)
    }

    wg.Wait()
    return results
}
```

### 6. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| goroutine 泄漏 | channel 无人接收 | 确保有消费方，或用 context 取消 |
| deadlock | 无缓冲 channel 发送/接收不配对 | 检查 channel 操作逻辑 |
| 数据竞争 | 多个 goroutine 写同一变量 | 用 mutex 或 channel |
| panic: send on closed channel | 向已关闭的 channel 发送 | 确保发送方负责关闭 |
"""


def generate_go_network_content() -> str:
    return """### 1. net/http 标准库

#### 1.1 HTTP Server

```go
package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "time"
)

func healthHandler(w http.ResponseWriter, r *http.Request) {
    resp := map[string]interface{}{
        "status": "healthy",
        "time":   time.Now().Format(time.RFC3339),
        "uptime": time.Since(startTime).String(),
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func metricsHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "text/plain")
    fmt.Fprintf(w, "# HELP http_requests_total Total HTTP requests\\n")
    fmt.Fprintf(w, "# TYPE http_requests_total counter\\n")
    fmt.Fprintf(w, "http_requests_total{path=\"/health\"} %d\\n", healthCount)
}

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", healthHandler)
    mux.HandleFunc("/metrics", metricsHandler)

    server := &http.Server{
        Addr:         ":8080",
        Handler:      mux,
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    log.Printf("Starting server on %s", server.Addr)
    log.Fatal(server.ListenAndServe())
}
```

#### 1.2 HTTP Client

```go
// 创建带超时的 client
client := &http.Client{
    Timeout: 10 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
    },
}

// GET 请求
resp, err := client.Get("http://api.example.com/health")
if err != nil {
    log.Printf("Request failed: %v", err)
    return
}
defer resp.Body.Close()

body, _ := io.ReadAll(resp.Body)
fmt.Printf("Status: %d, Body: %s\\n", resp.StatusCode, body)
```

### 2. 实战：Prometheus Exporter

```go
// exporter.go
package main

import (
    "fmt"
    "net/http"
    "os/exec"
    "strconv"
    "strings"
    "sync"
    "time"
)

type NodeExporter struct {
    mu    sync.RWMutex
    cache map[string]string
    ttl   time.Duration
    last  time.Time
}

func (e *NodeExporter) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    e.mu.RLock()
    if time.Since(e.last) < e.ttl && len(e.cache) > 0 {
        for _, line := range e.cache {
            fmt.Fprintln(w, line)
        }
        e.mu.RUnlock()
        return
    }
    e.mu.RUnlock()

    // 刷新数据
    e.mu.Lock()
    e.cache = e.collectMetrics()
    e.last = time.Now()
    e.mu.Unlock()

    for _, line := range e.cache {
        fmt.Fprintln(w, line)
    }
}

func (e *NodeExporter) collectMetrics() map[string]string {
    metrics := make(map[string]string)

    // CPU 使用率
    metrics["node_cpu_seconds_total"] = execCmd("grep", "cpu ", "/proc/stat")

    // 内存信息
    memInfo := execCmd("cat", "/proc/meminfo")
    metrics["node_memory_MemTotal_bytes"] = parseMemInfo(memInfo, "MemTotal")
    metrics["node_memory_MemAvailable_bytes"] = parseMemInfo(memInfo, "MemAvailable")

    // 磁盘使用
    metrics["node_filesystem_avail_bytes"] = execCmd("df", "--output=avail", "-B1")

    return metrics
}

func main() {
    exporter := &NodeExporter{
        cache: make(map[string]string),
        ttl:   5 * time.Second,
    }
    http.Handle("/metrics", exporter)
    http.ListenAndServe(":9100", nil)
}
```

### 3. os/exec — 执行系统命令

```go
// 执行简单命令
out, err := exec.Command("df", "-h").Output()
if err != nil {
    log.Printf("exec failed: %v", err)
}
fmt.Println(string(out))

// 带参数
cmd := exec.Command("grep", "-c", "ERROR", "/var/log/syslog")
output, err := cmd.Output()
if err != nil {
    log.Printf("grep failed: %v", err)
}
count, _ := strconv.Atoi(strings.TrimSpace(string(output)))
fmt.Printf("ERROR count: %d\\n", count)

// 实时输出（边执行边读取）
cmd = exec.Command("tail", "-f", "/var/log/nginx/access.log")
stdout, _ := cmd.StdoutPipe()
cmd.Start()

scanner := bufio.NewScanner(stdout)
for scanner.Scan() {
    line := scanner.Text()
    if strings.Contains(line, "500") {
        log.Printf("500 error detected: %s", line)
    }
}
"""


def generate_go_cli_content() -> str:
    return """### 1. Cobra — Go CLI 框架

Cobra 是 Kubernetes、Hugo、GitHub CLI 等项目的 CLI 框架：

```bash
go get github.com/spf13/cobra
go get github.com/spf13/viper  # 配置管理
```

### 2. 编写 SRE 运维 CLI

```go
// cmd/root.go
package cmd

import (
    "fmt"
    "os"
    "github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
    Use:   "sre-cli",
    Short: "SRE 运维工具集",
    Long: "SRE CLI 是一个命令行工具，用于日常运维操作：\\n" +
           "包括服务器巡检、日志分析、健康检查等功能",
}

func Execute() {
    if err := rootCmd.Execute(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}

// cmd/check.go
var checkCmd = &cobra.Command{
    Use:   "check [target]",
    Short: "执行健康检查",
    Args:  cobra.ExactArgs(1),
    Run: func(cmd *cobra.Command, args []string) {
        target := args[0]
        fmt.Printf("Checking %s...\\n", target)
        // 执行检查逻辑
    },
}

func init() {
    rootCmd.AddCommand(checkCmd)
    checkCmd.Flags().StringP("timeout", "t", "10s", "超时时间")
    checkCmd.Flags().IntP("retries", "r", 3, "重试次数")
}

// cmd/deploy.go
var deployCmd = &cobra.Command{
    Use:   "deploy [service]",
    Short: "部署服务",
    Run: func(cmd *cobra.Command, args []string) {
        // 部署逻辑
    },
}

// cmd/logs.go
var logsCmd = &cobra.Command{
    Use:   "logs [service]",
    Short: "查看服务日志",
    Run: func(cmd *cobra.Command, args []string) {
        // 日志查看逻辑
    },
}
```

### 3. Viper — 配置管理

```go
import "github.com/spf13/viper"

func initConfig() {
    viper.SetConfigName("config")
    viper.SetConfigType("yaml")
    viper.AddConfigPath("/etc/sre-cli/")
    viper.AddConfigPath("$HOME/.sre-cli")
    viper.AddConfigPath(".")

    // 环境变量
    viper.AutomaticEnv()

    // 绑定 flag
    viper.BindPFlag("timeout", checkCmd.Flags().Lookup("timeout"))

    if err := viper.ReadInConfig(); err != nil {
        if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
            log.Fatal(err)
        }
    }
}
```
"""


def generate_go_context_content() -> str:
    return """### 1. Context 包

Context 用于控制 goroutine 树的生命周期：取消、超时、deadline。

```go
package main

import (
    "context"
    "fmt"
    "time"
)

func main() {
    // 带超时的 context
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()

    doWork(ctx)
}

func doWork(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            fmt.Println("Work cancelled:", ctx.Err())
            return
        default:
            fmt.Println("Working...")
            time.Sleep(500 * time.Millisecond)
        }
    }
}
```

### 2. 四种 Context

```go
// 1. Background — 根 context
ctx := context.Background()

// 2. WithCancel — 手动取消
ctx, cancel := context.WithCancel(parent)
cancel() // 取消所有子 goroutine

// 3. WithTimeout — 超时取消
ctx, cancel := context.WithTimeout(parent, 5*time.Second)

// 4. WithDeadline — 在指定时间取消
ctx, cancel := context.WithDeadline(parent,
    time.Date(2026, 6, 1, 0, 0, 0, 0, time.UTC))

// 5. WithValue — 传递请求范围的值
ctx := context.WithValue(parent, "requestID", "abc123")
val := ctx.Value("requestID")
```

### 3. SRE 实战：带超时的并发健康检查

```go
func healthCheckWithTimeout(ctx context.Context, servers []string) map[string]bool {
    results := make(map[string]bool)
    var mu sync.Mutex
    var wg sync.WaitGroup

    for _, s := range servers {
        wg.Add(1)
        go func(server string) {
            defer wg.Done()

            req, _ := http.NewRequestWithContext(ctx, "GET",
                fmt.Sprintf("http://%s/health", server), nil)
            client := &http.Client{Timeout: 2 * time.Second}
            resp, err := client.Do(req)

            mu.Lock()
            defer mu.Unlock()
            if err != nil || resp.StatusCode != 200 {
                results[server] = false
            } else {
                results[server] = true
            }
        }(s)
    }

    wg.Wait()
    return results
}
```

### 4. Goroutine 泄漏预防

```go
// ❌ 泄漏：ctx 取消后，goroutine 仍在运行
func leakyFetch(ctx context.Context, url string) {
    go func() {
        resp, _ := http.Get(url) // ctx 取消后仍会执行
        _ = resp
    }()
}

// ✅ 安全：使用 NewRequestWithContext
func safeFetch(ctx context.Context, url string) error {
    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return err
    }
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    return nil
}
```
"""


def generate_go_test_content() -> str:
    return """### 1. Go 测试基础

Go 的测试使用 `go test`，测试文件以 `*_test.go` 结尾。

```go
// server.go
package server

import "fmt"

func HealthStatus(code int) string {
    if code >= 200 && code < 300 {
        return "healthy"
    }
    if code >= 400 && code < 500 {
        return "client_error"
    }
    return "server_error"
}

// server_test.go
package server

import "testing"

func TestHealthStatus(t *testing.T) {
    tests := []struct {
        name     string
        code     int
        expected string
    }{
        {"200 OK", 200, "healthy"},
        {"201 Created", 201, "healthy"},
        {"404 Not Found", 404, "client_error"},
        {"500 Internal", 500, "server_error"},
        {"503 Unavailable", 503, "server_error"},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := HealthStatus(tt.code)
            if result != tt.expected {
                t.Errorf("HealthStatus(%d) = %q, want %q",
                    tt.code, result, tt.expected)
            }
        })
    }
}
```

### 2. 表驱动测试（推荐模式）

```go
func TestParseLogLine(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        wantIP  string
        wantCode int
        wantErr bool
    }{
        {
            name:    "normal request",
            input:   `192.168.1.1 - - [01/Jan/2026:00:00:00 +0000] "GET / HTTP/1.1" 200 1234`,
            wantIP:  "192.168.1.1",
            wantCode: 200,
            wantErr: false,
        },
        {
            name:    "error response",
            input:   `10.0.0.1 - - [01/Jan/2026:00:00:01 +0000] "POST /api HTTP/1.1" 500 56`,
            wantIP:  "10.0.0.1",
            wantCode: 500,
            wantErr: false,
        },
        {
            name:    "invalid line",
            input:   "not a log line",
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result, err := ParseLogLine(tt.input)
            if (err != nil) != tt.wantErr {
                t.Errorf("ParseLogLine() error = %v, wantErr %v", err, tt.wantErr)
                return
            }
            if !tt.wantErr && result.IP != tt.wantIP {
                t.Errorf("IP = %q, want %q", result.IP, tt.wantIP)
            }
        })
    }
}
```

### 3. 基准测试

```go
func BenchmarkParseLog(b *testing.B) {
    line := `192.168.1.1 - - [01/Jan/2026:00:00:00 +0000] "GET /api/v1/users HTTP/1.1" 200 4096`
    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        ParseLogLine(line)
    }
}

// 运行：go test -bench=. -benchmem
// 输出：
// BenchmarkParseLog-8    1234567    965 ns/op    256 B/op    8 allocs/op
```

### 4. 测试 HTTP Server

```go
func TestHealthHandler(t *testing.T) {
    req := httptest.NewRequest("GET", "/health", nil)
    w := httptest.NewRecorder()

    healthHandler(w, req)

    resp := w.Result()
    if resp.StatusCode != http.StatusOK {
        t.Errorf("status = %d, want %d", resp.StatusCode, http.StatusOK)
    }
    if resp.Header.Get("Content-Type") != "application/json" {
        t.Errorf("content-type = %q, want application/json",
            resp.Header.Get("Content-Type"))
    }
}
```
"""


def generate_go_default_content(topic: str) -> str:
    return """### 1. """ + topic + """

Go 是 SRE 和云原生生态的核心语言。

### 2. 核心概念

- goroutine: 轻量级并发
- channel: 并发通信
- struct + interface: 组合设计
- error handling: 显式错误处理
"""


# ── 数据库生成器 ──────────────────────────────────────────────────────

def generate_db_content(day: int, topic: str) -> str:
    """生成数据库相关内容（Day 70-75）"""
    content_map = {
        70: generate_mysql_basic_content,
        71: generate_mysql_tuning_content,
        72: generate_mysql_ha_content,
        73: generate_redis_basic_content,
        74: generate_redis_ha_content,
        75: generate_db_review_content,
    }
    if day in content_map:
        return content_map[day]()
    return generate_db_default_content(topic)


def generate_mysql_basic_content() -> str:
    return """### 1. MySQL 架构与核心概念

#### 1.1 三层架构

```
┌─────────────────────────────────────────┐
│           连接层（Connection）            │
│  线程池、认证、SSL、连接管理              │
├─────────────────────────────────────────┤
│           服务层（SQL Layer）             │
│  SQL 解析 → 优化 → 缓存 → 执行计划       │
│  存储引擎接口（Pluggable Storage Engine） │
├─────────────────────────────────────────┤
│           存储引擎层（Storage Engine）     │
│  InnoDB（默认）/ MyISAM / Memory / ...   │
│  实际数据读写、事务、锁                   │
└─────────────────────────────────────────┘
```

#### 1.2 InnoDB vs MyISAM

| 特性 | InnoDB（推荐） | MyISAM |
|------|----------------|--------|
| 事务 | ✅ ACID | ❌ 不支持 |
| 行级锁 | ✅ 行锁 | ❌ 表锁 |
| 外键 | ✅ 支持 | ❌ 不支持 |
| 崩溃恢复 | ✅ redo log | ❌ 需要手动修复 |
| MVCC | ✅ 支持 | ❌ 不支持 |
| 全文索引 | ✅ 5.6+ 支持 | ✅ 支持 |

**SRE 结论：生产环境一律使用 InnoDB。**

#### 1.3 核心日志文件

| 日志 | 作用 | SRE 关注点 |
|------|------|------------|
| **binlog** | 记录所有 DDL/DML，用于主从复制和 PITR | 磁盘占用、清理策略 |
| **redo log** | InnoDB 事务日志，保证 ACID | I/O 性能、崩溃恢复 |
| **undo log** | 回滚日志，支持 MVCC 和事务回滚 | 长事务导致膨胀 |
| **slow query log** | 记录执行超过阈值的 SQL | 性能优化依据 |
| **error log** | 启动、运行、崩溃错误 | 故障排查 |

### 2. 安装与基础操作

```bash
# Ubuntu 安装
sudo apt update
sudo apt install -y mysql-server

# 启动并设置开机启动
sudo systemctl start mysql
sudo systemctl enable mysql

# 安全初始化
sudo mysql_secure_installation
# 设置 root 密码、移除匿名用户、禁止远程 root 登录

# 登录
sudo mysql -u root -p

# 创建数据库和用户
CREATE DATABASE sre_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sre'@'%' IDENTIFIED BY 'StrongPass123!';
GRANT ALL ON sre_monitor.* TO 'sre'@'%';
FLUSH PRIVILEGES;
```

### 3. 核心 SQL 操作

```sql
-- 创建表（带索引）
CREATE TABLE server_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hostname VARCHAR(64) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,
    metric_value DECIMAL(10,2) NOT NULL,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_hostname (hostname),
    INDEX idx_collected (collected_at),
    INDEX idx_host_metric (hostname, metric_name, collected_at)
) ENGINE=InnoDB;

-- 插入数据
INSERT INTO server_metrics (hostname, metric_name, metric_value)
VALUES ('web-01', 'cpu_usage', 85.5);

-- 查询（利用索引）
SELECT hostname, AVG(metric_value) as avg_cpu
FROM server_metrics
WHERE metric_name = 'cpu_usage'
  AND collected_at >= NOW() - INTERVAL 1 HOUR
GROUP BY hostname
ORDER BY avg_cpu DESC;

-- 查看执行计划
EXPLAIN SELECT hostname, AVG(metric_value)
FROM server_metrics
WHERE metric_name = 'cpu_usage'
  AND collected_at >= NOW() - INTERVAL 1 HOUR
GROUP BY hostname;
```

### 4. SRE 实战案例

```
场景：慢查询导致 CPU 飙升
1. 查看慢查询日志：tail -f /var/log/mysql/mysql-slow.log
2. 查看当前连接：SHOW PROCESSLIST;
3. 找到慢查询，用 EXPLAIN 分析
4. 发现缺少索引 → ALTER TABLE ADD INDEX
5. 验证：EXPLAIN 确认使用索引
6. 设置慢查询阈值：SET GLOBAL long_query_time = 1;
```

### 5. 常见问题

| 问题 | 排查 | 解决方案 |
|------|------|----------|
| 连接数满 | SHOW STATUS LIKE 'Threads_connected' | 增大 max_connections，排查连接泄漏 |
| 磁盘满 | df -h /var/lib/mysql | 清理 binlog，PURGE BINARY LOGS |
| 主从延迟 | SHOW SLAVE STATUS\\G | 检查 Seconds_Behind_Master |
| 表锁定 | SHOW ENGINE INNODB STATUS | 排查长事务，kill 阻塞连接 |
"""


def generate_mysql_tuning_content() -> str:
    return """### 1. 慢查询分析与优化

#### 1.1 开启慢查询日志

```sql
-- 临时开启
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  -- 超过 1 秒的记录
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- 永久配置（/etc/mysql/mysql.conf.d/mysqld.cnf）
[mysqld]
slow_query_log = 1
slow_query_log_file = /var/log/mysql/mysql-slow.log
long_query_time = 1
log_queries_not_using_indexes = 1
```

#### 1.2 使用 mysqldumpslow 分析

```bash
# 分析慢查询日志
mysqldumpslow -s t -t 10 /var/log/mysql/mysql-slow.log

# 按执行时间排序，显示前 10 条
mysqldumpslow -s at -t 10 /var/log/mysql/mysql-slow.log
```

#### 1.3 EXPLAIN 分析

```sql
EXPLAIN SELECT * FROM orders
WHERE customer_id = 123
  AND status = 'pending'
ORDER BY created_at DESC
LIMIT 10;
```

**关键列解读**：
| 列 | 含义 | 理想值 |
|----|------|--------|
| type | 访问类型 | ALL < index < range < ref < eq_ref < const |
| possible_keys | 可能使用的索引 | 不为 NULL |
| key | 实际使用的索引 | 不为 NULL |
| rows | 预估扫描行数 | 越小越好 |
| Extra | 额外信息 | 不含 "Using filesort"、"Using temporary" |

#### 1.4 索引优化原则

```sql
-- ✅ 好：复合索引覆盖查询条件
CREATE INDEX idx_customer_status ON orders(customer_id, status, created_at);

-- ❌ 差：选择性低的列放前面
CREATE INDEX idx_status_customer ON orders(status, customer_id);

-- 覆盖索引（避免回表）
-- 查询：SELECT customer_id, status FROM orders WHERE customer_id = 123
-- 索引只需包含：(customer_id, status) — 不需要回表取数据
```

### 2. 性能调优参数

```ini
[mysqld]
# 连接
max_connections = 500
max_connect_errors = 1000

# InnoDB
innodb_buffer_pool_size = 4G          # 物理内存的 50-70%
innodb_log_file_size = 1G
innodb_flush_log_at_trx_commit = 1    # 1=最安全, 2=性能好
innodb_flush_method = O_DIRECT        # 避免双重缓冲

# 查询缓存（MySQL 8.0 已移除）
# query_cache_type = 0

# 慢查询
slow_query_log = 1
long_query_time = 1

# 临时表
tmp_table_size = 64M
max_heap_table_size = 64M
```

### 3. SRE 实战案例

```
场景：线上数据库 CPU 100%
排查步骤：
1. top - 确认是 mysqld 进程
2. SHOW PROCESSLIST - 找到活跃查询
3. 发现全表扫描的慢查询（EXPLAIN type=ALL）
4. 添加缺失索引
5. 设置查询超时：SET SESSION max_execution_time = 5000
6. 长期：配置慢查询告警
```
"""


def generate_mysql_ha_content() -> str:
    return """### 1. MySQL 主从复制

#### 1.1 复制原理

```
Master ──────→ Binary Log ──────→ Slave IO Thread ──────→ Relay Log ──────→ Slave SQL Thread
              (记录所有变更)          (拉取 binlog)         (写入中继日志)     (重放 SQL)

GTID (Global Transaction ID): 每个事务唯一标识，简化故障恢复
```

#### 1.2 配置主从复制

**Master 配置**：
```ini
[mysqld]
server-id = 1
log-bin = mysql-bin
binlog-format = ROW
gtid-mode = ON
enforce-gtid-consistency = ON
```

**Slave 配置**：
```ini
[mysqld]
server-id = 2
relay-log = relay-bin
log-bin = mysql-bin
binlog-format = ROW
gtid-mode = ON
enforce-gtid-consistency = ON
read-only = ON
```

```sql
-- Master: 创建复制用户
CREATE USER 'repl'@'%' IDENTIFIED BY 'ReplPass123!';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';

-- Slave: 配置连接
CHANGE MASTER TO
    MASTER_HOST='10.0.1.10',
    MASTER_USER='repl',
    MASTER_PASSWORD='ReplPass123!',
    MASTER_AUTO_POSITION=1;

START SLAVE;
SHOW SLAVE STATUS\\G
-- 检查：Slave_IO_Running: Yes, Slave_SQL_Running: Yes
```

#### 1.3 监控复制状态

```sql
SHOW SLAVE STATUS\\G
-- 关键指标：
-- Slave_IO_Running: Yes
-- Slave_SQL_Running: Yes
-- Seconds_Behind_Master: 0  （延迟秒数）
-- Last_Error: (空表示正常)

-- 监控脚本
SELECT
    slave_io_running,
    slave_sql_running,
    seconds_behind_master,
    last_error
FROM performance_schema.replication_connection_status;
```

### 2. 备份与恢复

#### 2.1 mysqldump（逻辑备份）

```bash
# 全量备份
mysqldump -u root -p --all-databases --single-transaction \
    --routines --triggers --events > backup_$(date +%F).sql

# 备份单个数据库
mysqldump -u root -p --single-transaction sre_monitor > sre_backup.sql

# 恢复
mysql -u root -p < backup_2026-05-01.sql
```

#### 2.2 PITR（基于时间点恢复）

```bash
# 1. 恢复全量备份
mysql -u root -p < full_backup.sql

# 2. 用 binlog 恢复到指定时间点
mysqlbinlog --start-datetime="2026-05-01 10:00:00" \\
    --stop-datetime="2026-05-01 14:30:00" \\
    /var/lib/mysql/mysql-bin.000003 | mysql -u root -p
```

### 3. SRE 实战案例

```
场景：误删数据恢复
1. 立即停止写入：SET GLOBAL read_only = ON;
2. 确认删除时间
3. 从最近的备份恢复到一个临时实例
4. 用 binlog 重放到删除前的时间点
5. 导出被删除的数据
6. 导入回生产库
7. 验证数据完整性
```
"""


def generate_redis_basic_content() -> str:
    return """### 1. Redis 核心概念

#### 1.1 数据类型

| 类型 | 说明 | SRE 使用场景 |
|------|------|-------------|
| **String** | 键值对 | 缓存、计数器、Session |
| **Hash** | 字段-值映射 | 对象存储、配置信息 |
| **List** | 双向链表 | 消息队列、日志队列 |
| **Set** | 无序不重复集合 | 标签、去重 |
| **Sorted Set** | 有序集合 | 排行榜、延迟队列 |
| **Bitmap** | 位图 | 签到、在线状态 |
| **HyperLogLog** | 基数统计 | UV 统计 |

#### 1.2 持久化机制

| 方式 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **RDB** | 定期快照 | 恢复快、文件小 | 可能丢失最后几秒数据 |
| **AOF** | 追加写操作日志 | 数据安全 | 文件大、恢复慢 |
| **RDB+AOF** | 混合模式 | 平衡安全与性能 | 配置略复杂 |

### 2. 安装与基础操作

```bash
# 安装
sudo apt install -y redis-server
sudo systemctl enable redis-server

# 连接
redis-cli
redis-cli -h 127.0.0.1 -p 6379 -a password
```

**基础命令**：
```redis
# String
SET user:1001:name "zhangsan"
GET user:1001:name
INCR counter:requests
EXPIRE session:abc123 3600

# Hash
HMSET server:web-01 cpu 85.2 mem 72.1 disk 45.0
HGET server:web-01 cpu
HGETALL server:web-01

# List
LPUSH queue:tasks "task1" "task2"
RPOP queue:tasks

# Sorted Set
ZADD leaderboard 100 "player1" 85 "player2"
ZREVRANGE leaderboard 0 10 WITHSCORES

# 键管理
KEYS user:*              # 生产环境慎用！
SCAN 0 MATCH user:* COUNT 100  # 生产用 SCAN
TTL session:abc123       # 查看剩余过期时间
DEL user:1001:name
```

### 3. 内存管理

```redis
# 查看内存使用
INFO memory
# used_memory: 1073741824  (1GB)
# used_memory_human: 1.00G

# 查看大 Key
redis-cli --bigkeys

# 内存淘汰策略
CONFIG SET maxmemory 2gb
CONFIG SET maxmemory-policy allkeys-lru

# 策略选择：
# volatile-lru: 只对有过期时间的键用 LRU
# allkeys-lru:  对所有键用 LRU（最常用）
# volatile-ttl: 淘汰即将过期的键
# noeviction:   不淘汰，写入报错
```

### 4. SRE 实战案例

```
场景：Redis 内存爆满，频繁淘汰
1. redis-cli --bigkeys 找出大 Key
2. SCAN 0 MATCH * COUNT 1000 遍历键空间
3. 发现 user:cache:* 占 80% 内存
4. 优化：缩短 TTL，使用更紧凑的数据结构
5. 监控：配置 maxmemory 告警（> 80%）
```
"""


def generate_redis_ha_content() -> str:
    return """### 1. Redis Sentinel（高可用）

#### 1.1 Sentinel 架构

```
                 ┌──────────┐
                 │ Sentinel │
                 │   1      │
                 └────┬─────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
   │ Master  │  │ Slave   │  │ Slave   │
   │ :6379   │  │ :6379   │  │ :6379   │
   └─────────┘  └─────────┘  └─────────┘
```

Sentinel 负责：
1. 监控 Master/Slave 是否存活
2. Master 宕机时自动选举新 Master
3. 通知客户端新 Master 地址

#### 1.2 配置 Sentinel

```bash
# sentinel.conf
sentinel monitor mymaster 10.0.1.10 6379 2
sentinel auth-pass mymaster MyPassword
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1

# 启动
redis-sentinel /etc/redis/sentinel.conf
```

#### 1.3 模拟故障转移

```redis
# 连接 Sentinel
redis-cli -p 26379
SENTINEL master mymaster
SENTINEL slaves mymaster

# 模拟 Master 宕机
redis-cli -h 10.0.1.10 -p 6379 DEBUG SLEEP 30

# Sentinel 自动故障转移
# 1. 5 秒后标记 Master 下线（SDOWN → ODOWN）
# 2. 选举一个 Slave 为新 Master
# 3. 其他 Slave 指向新 Master
# 4. 通知客户端
```

### 2. Redis Cluster（分片集群）

```
3 主 3 从，16384 个哈希槽：

Master A [0-5460]    → Slave A'
Master B [5461-10922] → Slave B'
Master C [10923-16383] → Slave C'

客户端通过 CRC16(key) % 16384 确定到哪个节点
```

```bash
# 创建集群（Redis 5.0+）
redis-cli --cluster create \\
    10.0.1.10:7000 10.0.1.10:7001 10.0.1.10:7002 \\
    10.0.1.11:7000 10.0.1.11:7001 10.0.1.11:7002 \\
    --cluster-replicas 1
```

### 3. SRE 实战案例

```
场景：Sentinel 自动故障转移
配置：3 Sentinel + 1 Master + 2 Slave
触发：Master 节点宕机
结果：15 秒内完成故障转移，客户端自动重连
关键配置：
- down-after-milliseconds: 不宜太短（误判）也不宜太长（恢复慢）
- parallel-syncs: 设为 1 避免所有 Slave 同时同步
```
"""


def generate_db_review_content() -> str:
    return """### 数据库运维综合评估

## 1. 理论自测

1. 解释 InnoDB 的 MVCC 机制是如何实现的？
2. binlog、redo log、undo log 各自的作用是什么？
3. 主从复制中 Seconds_Behind_Master 为 NULL 表示什么？
4. Redis RDB 和 AOF 的优缺点分别是什么？
5. 什么情况下会导致 Redis 主从数据不一致？

## 2. 实操场景

### 场景 1：MySQL 慢查询优化
```sql
-- 有一个查询执行了 30 秒
SELECT o.*, c.name, c.email
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.status = 'pending'
  AND o.created_at > '2026-01-01'
ORDER BY o.created_at DESC
LIMIT 100;

-- 用 EXPLAIN 分析并优化
```

### 场景 2：Redis 大 Key 排查
```bash
# 1. 找出内存占用最高的 key
redis-cli --bigkeys --scan

# 2. 分析某个 Hash 的大小
HLEN user:large:hash

# 3. 渐进式删除（不阻塞）
unlink user:large:hash
```

### 场景 3：主从复制故障恢复
```sql
-- 1. 检查复制状态
SHOW SLAVE STATUS\\G

-- 2. 跳过错误（谨慎使用！）
STOP SLAVE;
SET GLOBAL sql_slave_skip_counter = 1;
START SLAVE;

-- 3. 完全重建从库（更安全）
```

## 3. 自我评估

- [ ] 能独立完成 MySQL 安装配置和备份恢复
- [ ] 能用 EXPLAIN 分析慢查询并添加合适索引
- [ ] 能配置 MySQL 主从复制并监控延迟
- [ ] 能解释 Redis 持久化机制的区别
- [ ] 能配置 Redis Sentinel 自动故障转移
- [ ] 能排查 Redis 内存爆满问题
"""


def generate_db_default_content(topic: str) -> str:
    return f"""### 1. {topic}

数据库是 SRE 工程师必须掌握的核心组件。

#### 1.1 核心概念

数据库运维包括：安装配置、性能调优、高可用、备份恢复。

### 2. 实践要点

- MySQL: InnoDB 引擎、慢查询优化、主从复制
- Redis: 内存管理、持久化、Sentinel 高可用

### 3. SRE 实战

| 场景 | 排查步骤 | 解决方案 |
|------|----------|----------|
| 慢查询 | EXPLAIN 分析 | 添加索引 |
| 内存满 | --bigkeys | 清理大 Key |
| 主从延迟 | SHOW SLAVE STATUS | 检查网络/负载 |
"""


# ── Docker 生成器 ─────────────────────────────────────────────────────

def generate_docker_content(day: int, topic: str) -> str:
    content_map = {
        76: generate_docker_install_content,
        77: generate_docker_image_content,
        78: generate_docker_dockerfile_content,
        79: generate_docker_container_content,
        80: generate_docker_storage_content,
        81: generate_docker_network_content,
        82: generate_docker_webapp_content,
        83: generate_docker_best_practices_content,
        84: generate_docker_compose_content,
        85: generate_docker_registry_content,
        86: generate_docker_security_content,
        87: generate_docker_network_adv_content,
        88: generate_docker_monitor_content,
        89: generate_docker_review_content,
    }
    if day in content_map:
        return content_map[day]()
    return generate_docker_default_content()


def generate_docker_install_content() -> str:
    return """### 1. Docker 核心概念

#### 1.1 容器 vs 虚拟机

```
┌──────────────────────────┐  ┌──────────────────────────┐
│     虚拟机 (VM)           │  │      容器 (Container)     │
├──────────────────────────┤  ├──────────────────────────┤
│   App  App  App          │  │   App  App  App          │
│   Libs Libs Libs         │  │   Libs Libs Libs         │
├──────────────────────────┤  ├──────────────────────────┤
│     Guest OS (完整)       │  │   Docker Engine          │
├──────────────────────────┤  ├──────────────────────────┤
│       Hypervisor          │  │     Host OS (共享内核)    │
├──────────────────────────┤  ├──────────────────────────┤
│     Host OS              │  │     Host OS              │
├──────────────────────────┤  ├──────────────────────────┤
│     硬件                 │  │     硬件                 │
└──────────────────────────┘  └──────────────────────────┘

VM:       启动 1-3 分钟，占用 GB 级内存，强隔离
Container: 启动毫秒级，占用 MB 级内存，进程级隔离
```

#### 1.2 Docker 架构

```
┌──────────┐      REST API     ┌──────────────┐
│  Docker  │  ──────────────→  │   Docker     │
│   CLI    │                   │   Daemon     │
│ (docker) │  ←──────────────  │  (dockerd)   │
└──────────┘                   └──────┬───────┘
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                    ┌──────┐  ┌──────┐  ┌──────┐
                    │Image │  │Cont. │  │ Vol. │
                    └──────┘  └──────┘  └──────┘
```

### 2. 安装 Docker

```bash
# Ubuntu 官方方式
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \\
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \\
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \\
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# 免 sudo 使用
sudo usermod -aG docker $USER
# 退出重新登录生效

# 设置开机启动
sudo systemctl enable docker
sudo systemctl start docker

# 验证
docker run hello-world
```

### 3. Docker 基础命令

```bash
# 查看版本
docker version
docker info

# 镜像操作
docker pull ubuntu:22.04
docker images
docker rmi ubuntu:22.04

# 容器操作
docker run -it ubuntu:22.04 bash
docker run -d -p 8080:80 nginx
docker ps
docker ps -a
docker stop <container_id>
docker rm <container_id>
docker logs -f <container_id>
docker exec -it <container_id> bash

# 系统清理
docker system df       # 查看磁盘使用
docker system prune    # 清理未使用的资源
```

### 4. SRE 实战

```
场景：服务器磁盘满
排查：
1. docker system df — 发现 images 占 50GB
2. docker image ls — 大量未使用的旧镜像
3. docker system prune -a — 清理所有未使用的镜像
4. 长期：配置镜像清理 cron + 镜像大小限制
```
"""


def generate_docker_image_content() -> str:
    return """### 1. Docker 镜像原理

#### 1.1 镜像分层存储

Docker 镜像由多个只读层（layer）叠加而成：

```
Layer 1: ubuntu:22.04 基础系统 (~77MB)
Layer 2: apt install nginx (~30MB)
Layer 3: COPY config/nginx.conf (~1KB)
Layer 4: COPY app/ (~10MB)

最终镜像 = Layer 1 + Layer 2 + Layer 3 + Layer 4

优势：
- 层缓存：修改 Layer 4 时，Layer 1-3 无需重建
- 共享：多个镜像可共享相同的基础层
- 增量拉取：pull 时只下载缺少的层
```

```bash
# 查看镜像层
docker image history nginx:latest

# 查看层详情
docker inspect nginx:latest

# 导出/导入镜像
docker save nginx:latest > nginx.tar
docker load < nginx.tar
```

#### 1.2 Dockerfile 基础指令

```dockerfile
# FROM: 指定基础镜像
FROM ubuntu:22.04

# RUN: 构建时执行（生成新层）
RUN apt update && apt install -y nginx

# COPY: 复制文件到镜像
COPY config/nginx.conf /etc/nginx/nginx.conf

# WORKDIR: 设置工作目录
WORKDIR /app

# EXPOSE: 声明端口（文档作用）
EXPOSE 80

# CMD: 容器启动时执行（可被覆盖）
CMD ["nginx", "-g", "daemon off;"]
```

### 2. 构建第一个镜像

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
```

```bash
# 构建镜像
docker build -t myapp:latest .

# 运行容器
docker run -d -p 8000:8000 --name myapp myapp:latest

# 检查
docker exec myapp curl http://localhost:8000/health
```

### 3. 镜像管理

```bash
# 标签
docker tag myapp:latest myregistry.com/myapp:v1.0

# 推送到仓库
docker push myregistry.com/myapp:v1.0

# 搜索
docker search nginx

# 清理
docker image prune        # 清理悬空镜像
docker image prune -a     # 清理所有未使用的镜像
docker image rm $(docker image ls -q)  # 删除所有
```
"""


def generate_docker_dockerfile_content() -> str:
    return """### 1. Dockerfile 进阶指令

#### 1.1 常用指令详解

```dockerfile
# ARG: 构建时变量（不留在镜像中）
ARG NODE_VERSION=18
FROM node:${NODE_VERSION}-alpine

# ENV: 运行时环境变量
ENV NODE_ENV=production
ENV PORT=3000

# USER: 切换用户（安全最佳实践）
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# HEALTHCHECK: 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \\
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ENTRYPOINT + CMD 组合
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
# 运行: docker run my-nginx -g "daemon off;"
# CMD 会被覆盖，ENTRYPOINT 不会
```

#### 1.2 多阶段构建

```dockerfile
# 阶段 1: 构建
FROM golang:1.22 AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server

# 阶段 2: 运行
FROM alpine:3.19
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/server /app/server
USER nobody
EXPOSE 8080
ENTRYPOINT ["/app/server"]

# 结果：最终镜像 ~10MB（仅包含运行所需文件）
# 对比：golang:1.22 基础镜像 ~800MB
```

### 2. 镜像大小优化

```dockerfile
# ❌ 不好：每层 RUN 都增加镜像大小
FROM ubuntu:22.04
RUN apt update
RUN apt install -y nginx
RUN apt install -y curl
RUN rm -rf /var/lib/apt/lists/*

# ✅ 好：合并 RUN，清理缓存
FROM ubuntu:22.04
RUN apt update && apt install -y --no-install-recommends nginx curl \\
    && rm -rf /var/lib/apt/lists/*

# 结果：~100MB vs ~150MB
```

**优化技巧**：
```
1. 用 slim/alpine 基础镜像
2. 合并 RUN 指令
3. --no-install-recommends
4. 多阶段构建
5. .dockerignore 排除不必要文件
6. 使用 build cache（合理排列指令顺序）
```

### 3. .dockerignore

```
# 不打包进镜像的文件
.git
.gitignore
node_modules
*.md
.env
docker-compose*.yml
Dockerfile
.dockerignore
__pycache__
*.pyc
```
"""


def generate_docker_container_content() -> str:
    return """### 1. Docker 容器管理

#### 1.1 docker run 参数详解

```bash
# 完整示例
docker run -d \\
    --name web-server \\
    --restart unless-stopped \\
    -p 80:80 -p 443:443 \\
    -v /data/nginx/conf:/etc/nginx/conf.d \\
    -v /data/nginx/logs:/var/log/nginx \\
    --network mynet \\
    --memory 512m \\
    --cpus 1.0 \\
    -e NGINX_HOST=example.com \\
    -e NGINX_PORT=80 \\
    --health-cmd="curl -f http://localhost/health || exit 1" \\
    --health-interval=30s \\
    --health-timeout=10s \\
    --health-retries=3 \\
    nginx:alpine
```

**参数说明**：
| 参数 | 说明 |
|------|------|
| `-d` | 后台运行 |
| `--name` | 容器名称 |
| `--restart` | 重启策略（no/always/unless-stopped/on-failure） |
| `-p` | 端口映射（宿主机:容器） |
| `-v` | 数据卷挂载 |
| `--network` | 指定网络 |
| `--memory` | 内存限制 |
| `--cpus` | CPU 限制 |
| `-e` | 环境变量 |

#### 1.2 容器生命周期

```bash
# 启动
docker start web-server

# 停止（发送 SIGTERM，等待 10 秒后 SIGKILL）
docker stop web-server

# 立即停止
docker kill web-server

# 重启
docker restart web-server

# 暂停（冻结进程）
docker pause web-server
docker unpause web-server

# 进入容器
docker exec -it web-server sh
docker exec -it web-server cat /etc/nginx/nginx.conf

# 查看日志
docker logs -f --tail 100 web-server
docker logs --since 10m web-server

# 查看资源使用
docker stats web-server

# 查看详细信息
docker inspect web-server
```

### 2. 部署 Redis 容器

```bash
# 持久化数据
docker run -d \\
    --name redis \\
    -p 6379:6379 \\
    -v redis-data:/data \\
    --restart unless-stopped \\
    redis:7-alpine \\
    redis-server --appendonly yes --requirepass MyPass123

# 测试连接
docker exec -it redis redis-cli -a MyPass123 ping

# 查看内存
docker exec redis redis-cli -a MyPass123 INFO memory
```

### 3. SRE 实战：容器批量管理

```bash
# 启动所有容器
docker start $(docker ps -a -q --filter "status=exited")

# 停止所有容器
docker stop $(docker ps -q)

# 删除所有已停止的容器
docker container prune

# 更新容器（重新拉取镜像并重启）
docker pull nginx:latest
docker stop web-server && docker rm web-server
docker run -d --name web-server -p 80:80 nginx:latest

# 查看容器日志中的错误
docker logs --tail 50 web-server 2>&1 | grep -i "error\|fail\|panic"
```
"""


def generate_docker_storage_content() -> str:
    return """### 1. Docker 数据管理

#### 1.1 三种存储方式

```
┌─────────────────────────────────────────────┐
│  Docker Host                                │
│                                             │
│  ┌─────────┐    ┌──────────┐  ┌──────────┐ │
│  │ 容器    │    │  容器     │  │ 容器     │ │
│  │ /data   │    │ /data    │  │ /tmp     │ │
│  └────┬────┘    └────┬─────┘  └──────────┘ │
│       │              │                      │
│  ┌────▼────┐    ┌────▼─────┐                │
│  │Bind     │    │Volume    │                │
│  │Mount    │    │          │                │
│  │/host/   │    │/var/lib/ │                │
│  │data/    │    │docker/   │                │
│  └─────────┘    │volumes/  │                │
│                 └──────────┘                │
│                                             │
│  tmpfs: 存储在宿主内存中，容器停止即消失       │
└─────────────────────────────────────────────┘
```

| 类型 | 位置 | 持久化 | 跨容器共享 | 适用场景 |
|------|------|--------|-----------|---------|
| **Volume** | /var/lib/docker/volumes/ | ✅ | ✅ | 数据库、持久化数据 |
| **Bind Mount** | 宿主机任意路径 | ✅ | ✅ | 开发、配置文件 |
| **tmpfs** | 宿主内存 | ❌ | ❌ | 临时敏感数据 |

### 2. Volume 操作

```bash
# 创建
docker volume create redis-data

# 查看
docker volume ls
docker volume inspect redis-data

# 使用
docker run -d \\
    --name mysql \\
    -v mysql-data:/var/lib/mysql \\
    -e MYSQL_ROOT_PASSWORD=root123 \\
    mysql:8

# 验证数据持久化
docker rm -f mysql
docker run -d \\
    --name mysql-new \\
    -v mysql-data:/var/lib/mysql \\
    -e MYSQL_ROOT_PASSWORD=root123 \\
    mysql:8
# 数据完整保留！

# 备份
docker run --rm \\
    -v mysql-data:/data:ro \\
    -v $(pwd):/backup \\
    alpine tar czf /backup/mysql-backup.tar.gz -C /data .

# 恢复
docker run --rm \\
    -v mysql-data:/data \\
    -v $(pwd):/backup \\
    alpine tar xzf /backup/mysql-backup.tar.gz -C /data

# 清理
docker volume prune  # 清理未使用的 volume
```

### 3. Bind Mount

```bash
# 挂载配置文件
docker run -d \\
    --name nginx \\
    -v /etc/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \\
    -v /var/www/html:/usr/share/nginx/html:ro \\
    -p 80:80 \\
    nginx:alpine

# :ro 表示只读（安全最佳实践）
```
"""


def generate_docker_network_content() -> str:
    return """### 1. Docker 网络模式

```
bridge（默认）— 容器通过网桥连接，NAT 到宿主机
host          — 容器共享宿主机网络栈
none          — 无网络
overlay       — 跨主机网络（Swarm/K8s）
macvlan       — 给容器分配真实 MAC 地址
```

#### 1.1 Bridge 网络

```bash
# 默认 bridge（单个容器间不能用名称通信）
docker run -d --name web1 -p 8081:80 nginx
docker run -d --name web2 -p 8082:80 nginx

# 用户定义网络（支持 DNS 名称解析）
docker network create mynet

docker run -d --name web1 --network mynet nginx
docker run -d --name web2 --network mynet nginx

# 容器间通过名称通信
docker exec web1 curl http://web2:80  # ✅ 可以！
```

### 2. 网络管理

```bash
# 创建网络
docker network create \\
    --driver bridge \\
    --subnet 172.20.0.0/16 \\
    --gateway 172.20.0.1 \\
    mynet

# 查看
docker network ls
docker network inspect mynet

# 连接/断开
docker network connect mynet container1
docker network disconnect mynet container1
```

### 3. SRE 实战：微服务网络

```
架构：前端 → API Gateway → 后端服务 → 数据库

docker network create backend
docker network create frontend

# 数据库（只连 backend）
docker run -d --name db --network backend postgres

# 后端（连两个网络）
docker run -d --name api --network backend nginx
docker network connect frontend api

# 前端（只连 frontend）
docker run -d --name web --network frontend nginx

# 隔离效果：
# web → api ✅ （都在 frontend 网络）
# api → db  ✅ （都在 backend 网络）
# web → db  ❌ （无共同网络，网络隔离！）
```
"""


def generate_docker_webapp_content() -> str:
    return """### 1. Docker Compose — 多容器编排

#### 1.1 什么是 Docker Compose？

Compose 用 YAML 文件定义多容器应用：

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    environment:
      DATABASE_URL: postgresql://postgres:pass@db:5432/myapp
      REDIS_URL: redis://redis:6379/0
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: myapp
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  pgdata:
  redis-data:
```

```bash
# 启动
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f web

# 停止
docker compose down

# 停止并清理数据
docker compose down -v

# 重新构建并启动
docker compose up -d --build
```

#### 1.2 健康检查

```yaml
services:
  web:
    build: .
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  db:
    image: postgres:15
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  redis:
    image: redis:7
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```
"""


def generate_docker_best_practices_content() -> str:
    return """### 1. Dockerfile 最佳实践

#### 1.1 优化镜像大小

```dockerfile
# ❌ 反模式
FROM python:3.11
COPY . .
RUN pip install -r requirements.txt
RUN apt update && apt install -y build-essential
CMD ["python", "app.py"]

# ✅ 最佳实践
FROM python:3.11-slim

WORKDIR /app

# 利用层缓存：先复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制代码
COPY . .

# 非 root 运行
RUN useradd -r appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s \\
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
```

**大小对比**：
| 镜像 | 大小 |
|------|------|
| python:3.11 | ~900MB |
| python:3.11-slim | ~150MB |
| python:3.11-alpine | ~50MB |

### 2. 安全基线

```dockerfile
# 1. 固定版本
FROM nginx:1.25.3-alpine  # 不要 nginx:latest

# 2. 非 root 运行
RUN addgroup -S app && adduser -S appuser -G app
USER appuser

# 3. 只读根文件系统
# docker run --read-only nginx

# 4. 删除不必要的包
RUN apt-get purge -y --auto-remove gcc make

# 5. 多阶段构建（不泄露构建工具）
FROM node:18 AS builder
# ... 构建 ...
FROM node:18-alpine
COPY --from=builder /app/dist /app/dist
```

### 3. 安全扫描

```bash
# Trivy 漏洞扫描
trivy image nginx:latest

# 输出示例：
# nginx:1.25.3 (alpine 3.19.0)
# Total: 0 (UNKNOWN: 0, LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0)

# 集成到 CI
trivy image --exit-code 1 --severity CRITICAL,HIGH myapp:latest
```
"""


def generate_docker_compose_content() -> str:
    return """### 1. docker-compose 完整实战

#### 1.1 搭建 LEMP 环境

```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./html:/usr/share/nginx/html:ro
      - nginx-logs:/var/log/nginx
    depends_on:
      php:
        condition: service_healthy
    restart: unless-stopped

  php:
    build:
      context: .
      dockerfile: Dockerfile.php-fpm
    volumes:
      - ./html:/var/www/html:ro
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped

  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: webapp
      MYSQL_USER: webapp
      MYSQL_PASSWORD: apppass
    volumes:
      - mysql-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      retries: 5
    restart: unless-stopped

  adminer:
    image: adminer
    ports:
      - "8080:8080"
    depends_on:
      - mysql
    restart: unless-stopped

volumes:
  mysql-data:
  nginx-logs:
```

```bash
# 启动
docker compose up -d

# 查看日志
docker compose logs -f --tail=50

# 停止（保留数据）
docker compose stop

# 完全清理
docker compose down -v
```

### 2. 多环境配置

```bash
# docker-compose.yml（基础配置）
# docker-compose.override.yml（开发覆盖）
# docker-compose.prod.yml（生产覆盖）

# 开发环境
docker compose up -d

# 生产环境
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
"""


def generate_docker_registry_content() -> str:
    return """### 1. Docker Registry 私有仓库

#### 1.1 搭建 Registry

```bash
# 最简单的私有仓库
docker run -d \\
    -p 5000:5000 \\
    --name registry \\
    -v registry-data:/var/lib/registry \\
    --restart unless-stopped \\
    registry:2

# 推送镜像
docker tag myapp:latest localhost:5000/myapp:v1.0
docker push localhost:5000/myapp:v1.0

# 拉取
docker pull localhost:5000/myapp:v1.0
```

#### 1.2 Harbor 企业级仓库

```yaml
# docker-compose.yml for Harbor
version: '3.8'
services:
  harbor-core:
    image: goharbor/harbor-core:latest
    # ... (完整配置参见 harbor-offline-installer)
```

```bash
# 安装 Harbor
tar xzf harbor-offline-installer-*.tgz
cd harbor
vim harbor.yml  # 修改 hostname、port、密码
./install.sh

# 访问 http://your-server:80
# 登录、创建项目、推送镜像
```

### 2. 镜像标签策略

```
myapp:1.0.0       # 语义化版本（推荐用于生产）
myapp:1.0         # 小版本
myapp:latest      # 最新（不推荐用于生产，不可预测）
myapp:sha-abc123  # Git commit SHA（可追溯）
```
"""


def generate_docker_security_content() -> str:
    return """### 1. Docker 安全

#### 1.1 容器逃逸风险

```bash
# ❌ 危险：--privileged 给容器完整宿主机权限
docker run --privileged ubuntu  # 可以访问所有设备、挂载文件系统

# ❌ 危险：挂载宿主机根目录
docker run -v /:/host ubuntu  # 容器内可以修改宿主机任意文件

# ✅ 安全：最小权限
docker run \\
    --read-only \\
    --no-new-privileges \\
    --cap-drop=ALL \\
    --cap-add=NET_BIND_SERVICE \\
    nginx
```

#### 1.2 安全最佳实践

```
1. 不使用 --privileged
2. 不挂载敏感目录（/etc, /proc, /sys）
3. 非 root 运行
4. 定期更新基础镜像
5. 使用 Trivy 扫描漏洞
6. 限制资源（--memory, --cpus）
7. 使用只读根文件系统
8. 配置 seccomp/AppArmor 配置文件
```

### 2. 安全扫描

```bash
# Trivy
trivy image --severity CRITICAL,HIGH nginx:latest

# Docker Scout（Docker Desktop）
docker scout cves nginx:latest

# 结果输出
# 0 CRITICAL, 2 HIGH, 5 MEDIUM
# 升级基础镜像可修复大部分漏洞
```
"""


def generate_docker_network_adv_content() -> str:
    return """### 1. 高级网络

#### 1.1 网络隔离验证

```bash
# 创建两个网络
docker network create frontend
docker network create backend

# 连接
docker run -d --name web --network frontend nginx
docker run -d --name api --network frontend nginx
docker network connect backend api

docker run -d --name db --network backend mysql

# 连通性测试
docker exec web ping api    # ✅ （同一网络）
docker exec api ping db     # ✅ （同一网络）
docker exec web ping db     # ❌ （不同网络，隔离）
```

### 2. Macvlan — 给容器分配真实 IP

```bash
# 创建 macvlan 网络
docker network create -d macvlan \\
    --subnet=192.168.1.0/24 \\
    --gateway=192.168.1.1 \\
    -o parent=eth0 \\
    my-macvlan

# 容器获得独立 IP（局域网中可见）
docker run -d --name myapp \\
    --network my-macvlan \\
    --ip 192.168.1.100 \\
    nginx

# 局域网其他机器可直接访问 192.168.1.100
```
"""


def generate_docker_monitor_content() -> str:
    return """### 1. Docker 监控与日志

#### 1.1 docker stats

```bash
# 实时查看容器资源使用
docker stats

# 输出示例：
# CONTAINER   CPU %   MEM USAGE / LIMIT   NET I/O     BLOCK I/O
# web-01      2.5%    256MiB / 512MiB     10MB/5MB    100MB/50MB
```

#### 1.2 日志驱动与轮转

```json
// /etc/docker/daemon.json
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
```

```bash
# 重载配置
sudo systemctl reload docker

# 查看容器日志大小
docker inspect --format='{{.LogPath}}' web-01 | xargs ls -lh
```

### 2. 日志集中化

```yaml
# docker-compose.yml
services:
  web:
    image: nginx
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    # 或发送到 syslog
    # logging:
    #   driver: syslog
    #   options:
    #     syslog-address: "tcp://10.0.1.50:514"
```

### 3. SRE 实战

```
场景：容器日志爆满磁盘
排查：
1. df -h — 发现 /var/lib/docker/containers 占 30GB
2. 某个容器疯狂打印 DEBUG 日志
3. 临时：truncate -s 0 /var/lib/docker/containers/*/json.log
4. 永久：配置 log-opts max-size/max-file
5. 长期：集中日志到 ELK/Loki
```
"""


def generate_docker_review_content() -> str:
    return """### Docker 阶段测试

## 1. 理论测试

1. 解释 Docker 镜像分层的原理和优势
2. Volume vs Bind Mount vs tmpfs 的区别和适用场景
3. --restart=always vs --restart=unless-stopped 的区别
4. Docker bridge 网络和 host 网络的区别
5. 容器逃逸的常见途径和防御方法

## 2. 实操测试

### 任务 1：Docker 化一个 Python Web 应用
```
要求：
- 多阶段构建（builder + runtime）
- 非 root 运行
- 健康检查
- 日志轮转
- 镜像大小 < 100MB
```

### 任务 2：docker-compose 部署 Web 应用栈
```
要求：
- nginx + gunicorn + postgres + redis
- 健康检查依赖
- 数据卷持久化
- 网络隔离
```

### 任务 3：安全扫描
```
要求：
- 用 Trivy 扫描你的镜像
- 修复所有 CRITICAL/HIGH 漏洞
- 写出安全加固报告
```

## 3. 自我评估

- [ ] 能编写生产级 Dockerfile
- [ ] 能用 docker-compose 编排多容器应用
- [ ] 理解镜像分层和缓存机制
- [ ] 能排查容器网络和存储问题
- [ ] 了解 Docker 安全最佳实践
- [ ] 能配置日志轮转和集中化
"""


def generate_docker_default_content() -> str:
    return """### 1. Docker

Docker 是 SRE 工程师的核心工具。

### 2. 核心概念

- 镜像（Image）：只读模板
- 容器（Container）：运行实例
- 数据卷（Volume）：持久化存储
- 网络（Network）：容器间通信

### 3. SRE 实战

- 容器化应用部署
- 多环境一致性
- 快速扩缩容
"""


# ── Kubernetes 生成器 ───────────────────────────────────────────────

def generate_k8s_content(day: int, topic: str) -> str:
    content_map = {
        90: generate_k8s_intro_content,
        91: generate_k8s_pod_content,
        92: generate_k8s_deployment_content,
        93: generate_k8s_statefulset_content,
        94: generate_k8s_daemonset_content,
        95: generate_k8s_service_content,
        96: generate_k8s_ingress_content,
        97: generate_k8s_configmap_content,
        98: generate_k8s_storage_content,
        99: generate_k8s_rbac_content,
        100: generate_k8s_scheduler_content,
        101: generate_k8s_hpa_content,
        102: generate_k8s_helm_content,
        103: generate_k8s_project_content,
        104: generate_k8s_review_content,
    }
    if day in content_map:
        return content_map[day]()
    return generate_k8s_default_content()


def generate_k8s_intro_content() -> str:
    return """### 1. Kubernetes 简介

#### 1.1 为什么需要 K8s？

```
传统部署 → 问题：
1. 服务器手工部署应用 → 环境不一致
2. 扩缩容手动操作 → 慢、易错
3. 故障需要人工处理 → 不可靠
4. 资源利用率低 → 浪费

K8s 解决方案：
1. 声明式 API → 期望状态 = 实际状态
2. 自动调度 → 根据资源需求分配到合适节点
3. 自愈 → 容器挂了自动重启，节点挂了自动迁移
4. 服务发现 + 负载均衡 → 无需手动配置
```

#### 1.2 K8s 架构

```
┌─────────────────────────────────────────┐
│           Control Plane (Master)         │
├─────────────────────────────────────────┤
│  API Server ← 唯一入口，所有操作经过这里  │
│  etcd       ← 键值存储，集群状态          │
│  Scheduler  ← 调度 Pod 到节点            │
│  Controller ← 维持期望状态               │
│             Manager                      │
├─────────────────────────────────────────┤
│           Worker Nodes                   │
├─────────────────────────────────────────┤
│  kubelet    ← 与 API Server 通信         │
│  kube-proxy ← 网络代理/负载均衡          │
│  Container Runtime (containerd/cri-o)    │
│                                          │
│  ┌─────┐  ┌─────┐  ┌─────┐             │
│  │Pod 1│  │Pod 2│  │Pod 3│ ← 容器组    │
│  └─────┘  └─────┘  └─────┘             │
└─────────────────────────────────────────┘
```

### 2. 安装 minikube

```bash
# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 启动集群
minikube start --driver=docker --cpus=4 --memory=8192

# 验证
kubectl cluster-info
kubectl get nodes
kubectl get pods -A
```

### 3. kubectl 基础

```bash
# 查看资源
kubectl get nodes
kubectl get pods
kubectl get pods -n kube-system
kubectl get all

# 详细信息
kubectl describe node minikube
kubectl describe pod <pod-name>

# 日志
kubectl logs <pod-name>
kubectl logs -f <pod-name>

# 进入容器
kubectl exec -it <pod-name> -- /bin/sh

# 创建/删除
kubectl apply -f manifest.yaml
kubectl delete -f manifest.yaml
```

### 4. SRE 视角：K8s 带来的运维变革

```
Before K8s:
- 每台服务器安装 Agent → 配置管理
- 手动编写部署脚本 → 易错
- 监控告警手动处理 → 慢

After K8s:
- 声明式 API → 所有操作可审计
- 自动调度 → 运维不再关心"跑在哪台机器"
- 自愈 → 减少 On-Call 告警
- 水平扩缩容 → 流量高峰自动应对
```
"""


def generate_k8s_pod_content() -> str:
    return """### 1. Pod — K8s 最小调度单元

#### 1.1 Pod 概念

Pod 是 K8s 中**最小的部署单元**，包含一个或多个容器：

```
Pod
├── Container 1: 应用容器 (nginx)
├── Container 2: Sidecar (日志收集)
├── 共享网络: 同一个 IP、端口空间
├── 共享存储: 同一个 Volume 挂载点
└── 共享 IPC/UTS namespace
```

#### 1.2 Pod YAML

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: nginx
    env: production
spec:
  containers:
  - name: nginx
    image: nginx:1.25-alpine
    ports:
    - containerPort: 80
      protocol: TCP
    resources:
      requests:
        cpu: "100m"
        memory: "128Mi"
      limits:
        cpu: "500m"
        memory: "256Mi"
    readinessProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 5
      periodSeconds: 10
    livenessProbe:
      httpGet:
        path: /
        port: 80
      initialDelaySeconds: 15
      periodSeconds: 20
    volumeMounts:
    - name: html
      mountPath: /usr/share/nginx/html
  volumes:
  - name: html
    configMap:
      name: nginx-html
```

#### 1.3 探针详解

| 探针 | 作用 | 失败后果 |
|------|------|----------|
| **livenessProbe** | 检查容器是否存活 | 重启容器 |
| **readinessProbe** | 检查是否准备好接收流量 | 从 Service 中移除 |
| **startupProbe** | 检查慢启动应用 | 延迟 livenessProbe 检查 |

```yaml
# 启动探针 — 给慢启动应用（如 Java）足够时间
startupProbe:
  httpGet:
    path: /health
    port: 8080
  failureThreshold: 30     # 最多失败 30 次
  periodSeconds: 10        # 每 10 秒检查
  # 总等待时间 = 30 × 10 = 300 秒（5 分钟）
```

### 2. Pod 生命周期

```
Pending → 调度中（镜像拉取中）
  ↓
Running → 容器运行中
  ↓
Succeeded/Failed → 任务完成/失败
  或
Terminating → 优雅关闭
  ↓
```

```bash
# 查看 Pod 状态
kubectl get pods
kubectl describe pod web-server

# 查看事件
kubectl get events --sort-by='.lastTimestamp'

# 强制删除（慎用！）
kubectl delete pod web-server --grace-period=0 --force
```
"""


def generate_k8s_deployment_content() -> str:
    return """### 1. Deployment — 管理无状态应用

#### 1.1 核心概念

Deployment 管理 Pod 的期望状态：副本数、镜像版本、滚动更新。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  labels:
    app: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 最多超出 1 个 Pod
      maxUnavailable: 1  # 最多不可用 1 个 Pod
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web
        image: myapp:v1.0
        ports:
        - containerPort: 8080
```

#### 1.2 滚动更新

```bash
# 更新镜像
kubectl set image deployment/web-app web=myapp:v2.0

# 查看更新状态
kubectl rollout status deployment/web-app
kubectl rollout history deployment/web-app

# 回滚
kubectl rollout undo deployment/web-app
kubectl rollout undo deployment/web-app --to-revision=2

# 暂停/继续更新
kubectl rollout pause deployment/web-app
kubectl rollout resume deployment/web-app
```

**滚动更新原理**：
```
期望 3 个 Pod，maxSurge=1, maxUnavailable=1:

Step 1: 创建 1 个新 Pod → 4 个运行（3 旧 + 1 新）
Step 2: 新 Pod 就绪后，终止 1 个旧 Pod → 3 个运行（2 旧 + 1 新）
Step 3: 重复直到所有 Pod 都是新版本
```

### 2. 扩缩容

```bash
# 手动扩缩容
kubectl scale deployment/web-app --replicas=5

# 查看 Pod 分布
kubectl get pods -l app=web-app -o wide
```
"""


def generate_k8s_statefulset_content() -> str:
    return """### 1. StatefulSet — 有状态应用

#### 1.1 与 Deployment 的区别

| 特性 | Deployment | StatefulSet |
|------|-----------|-------------|
| Pod 名称 | 随机（web-abc123） | 有序（web-0, web-1, web-2） |
| 启动/停止 | 同时 | 有序（0→1→2 启动，2→1→0 停止） |
| 存储 | 共享 PVC | 独立 PVC（web-0-pvc, web-1-pvc） |
| 网络 | 通过 Service | Headless Service + DNS |
| 适用 | 无状态（Web） | 有状态（DB、MQ） |

#### 1.2 MySQL StatefulSet

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: "root123"
        ports:
        - containerPort: 3306
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: mysql-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

```bash
# Pod 有稳定的网络标识
mysql-0.mysql.default.svc.cluster.local
mysql-1.mysql.default.svc.cluster.local
mysql-2.mysql.default.svc.cluster.local

# 主从复制中用 DNS 名称配置复制源
CHANGE MASTER TO MASTER_HOST='mysql-0.mysql.default.svc.cluster.local';
```
"""


def generate_k8s_daemonset_content() -> str:
    return """### 1. DaemonSet & Job/CronJob

#### 1.1 DaemonSet — 每个节点运行一个 Pod

适用场景：日志收集（Fluent Bit）、监控（Node Exporter）、网络插件。

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:latest
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: containers
          mountPath: /var/lib/docker/containers
          readOnly: true
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: containers
        hostPath:
          path: /var/lib/docker/containers
```

#### 1.2 Job — 一次性任务

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
spec:
  template:
    spec:
      containers:
      - name: migration
        image: myapp:migrate
        command: ["python", "manage.py", "migrate"]
      restartPolicy: Never
  backoffLimit: 3  # 最多重试 3 次
```

#### 1.3 CronJob — 定时任务

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup
spec:
  schedule: "0 2 * * *"  # 每天凌晨 2 点
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: backup-tool:latest
            command: ["./backup.sh"]
          restartPolicy: OnFailure
  successfulJobsHistoryLimit: 3   # 保留 3 个成功记录
  failedJobsHistoryLimit: 1       # 保留 1 个失败记录
```
"""


def generate_k8s_service_content() -> str:
    return """### 1. Service — 稳定的网络访问点

#### 1.1 为什么需要 Service？

```
Pod IP 会变化！
- Pod 重启 → 新 IP
- 滚动更新 → 新旧 Pod IP 不同
- 扩缩容 → 新增 Pod 有不同的 IP

Service 提供：
✅ 稳定的 ClusterIP（不随 Pod 变化）
✅ 负载均衡到后端 Pod
✅ 基于 Label Selector 自动发现 Pod
```

#### 1.2 Service 类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| **ClusterIP** | 集群内部访问（默认） | 微服务间通信 |
| **NodePort** | 通过节点端口暴露 | 开发测试 |
| **LoadBalancer** | 云厂商负载均衡器 | 生产对外服务 |
| **ExternalName** | CNAME 到外部服务 | 外部 API 代理 |

```yaml
# ClusterIP（内部服务）
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web-app
  ports:
  - port: 80          # Service 端口
    targetPort: 8080  # Pod 端口
    protocol: TCP
  type: ClusterIP

# NodePort（通过节点访问）
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080  # 固定端口 30000-32767
  type: NodePort

# LoadBalancer（云厂商）
apiVersion: v1
kind: Service
metadata:
  name: web-app
spec:
  selector:
    app: web-app
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

### 2. Headless Service（StatefulSet 用）

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None  # Headless！
  selector:
    app: mysql
  ports:
  - port: 3306

# 效果：DNS 返回所有 Pod IP
# nslookup mysql.default.svc.cluster.local
# → 10.244.1.5, 10.244.2.3, 10.244.3.7
```
"""


def generate_k8s_ingress_content() -> str:
    return """### 1. Ingress — HTTP/HTTPS 路由

#### 1.1 Ingress vs Service

```
Internet → LoadBalancer → Ingress Controller → Ingress Rules → Service → Pod

Service: L4 负载均衡（TCP/UDP）
Ingress: L7 路由（HTTP/HTTPS，基于域名/路径）
```

#### 1.2 Nginx Ingress Controller

```bash
# 安装
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

# 验证
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx
```

#### 1.3 Ingress 规则

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - example.com
    secretName: example-tls
  rules:
  - host: example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-app
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-app
            port:
              number: 8080
```

### 2. SRE 实战：多域名路由

```
example.com/    → web-app (前端)
example.com/api → api-app (后端 API)
api.example.com → api-app（直接访问后端）
grafana.example.com → grafana (监控)
```
"""


def generate_k8s_configmap_content() -> str:
    return """### 1. ConfigMap 与 Secret

#### 1.1 ConfigMap — 配置管理

```yaml
# 创建 ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_ENV: production
  LOG_LEVEL: info
  DATABASE_HOST: mysql.default.svc.cluster.local
  DATABASE_PORT: "3306"
  # 也可以用文件形式
  nginx.conf: |
    server {
        listen 80;
        location / {
            proxy_pass http://backend:8080;
        }
    }
```

**使用 ConfigMap**：
```yaml
# 作为环境变量
spec:
  containers:
  - name: app
    image: myapp:v1
    envFrom:
    - configMapRef:
        name: app-config

# 作为文件挂载
    volumeMounts:
    - name: config
      mountPath: /etc/nginx/conf.d
  volumes:
  - name: config
    configMap:
      name: app-config
```

#### 1.2 Secret — 敏感信息

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: YWRtaW4=          # base64 编码的 "admin"
  password: cGFzc3dvcmQxMjM=   # base64 编码的 "password123"
stringData:                      # 自动 base64 编码
  api-key: sk-xxxxxxxxxxxx
```

**使用 Secret**：
```yaml
spec:
  containers:
  - name: app
    env:
    - name: DB_USER
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: username
    - name: DB_PASS
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: password
```

### 2. RBAC — 最小权限访问 Secret

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]  # 只能读取，不能 list/watch/modify
```
"""


def generate_k8s_storage_content() -> str:
    return """### 1. 存储 — PV/PVC/StorageClass

#### 1.1 概念

```
StorageClass → 动态创建 PersistentVolume (PV)
                    ↓
PersistentVolumeClaim (PVC) → 申请存储
                    ↓
Pod → 挂载 PVC → 获得持久化存储
```

#### 1.2 静态配置

```yaml
# 1. 创建 PV（管理员）
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /data/mysql

# 2. 创建 PVC（用户）
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi

# 3. Pod 使用 PVC
spec:
  volumes:
  - name: mysql-data
    persistentVolumeClaim:
      claimName: mysql-pvc
```

#### 1.3 StorageClass（动态配置）

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: kubernetes.io/no-provisioner  # 或 aws-ebs, gce-pd 等
volumeBindingMode: WaitForFirstConsumer
```

```bash
# 查看默认 StorageClass
kubectl get storageclass

# 使用 StorageClass 的 PVC
spec:
  storageClassName: standard
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```
"""


def generate_k8s_rbac_content() -> str:
    return """### 1. RBAC — 基于角色的访问控制

#### 1.1 核心概念

```
Role/ClusterRole   ← 定义权限（能做什么）
RoleBinding/       ← 绑定角色到主体（谁能做）
ClusterRoleBinding

主体（Subject）：User / Group / ServiceAccount
```

| 资源 | 作用范围 | 示例 |
|------|----------|------|
| Role | 单个 Namespace | 允许在 production 读取 Pod |
| ClusterRole | 整个集群 | 允许查看所有 Namespace 的 Node |
| RoleBinding | Namespace 内 | 绑定 zhangsan 到 production 的 reader 角色 |
| ClusterRoleBinding | 全局 | 绑定 admin 组到 cluster-admin |

#### 1.2 创建 Role 和绑定

```yaml
# Role: 只允许在 production 管理 Deployment
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: deployer
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]

---
# RoleBinding: 绑定到 ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deployer-binding
  namespace: production
subjects:
- kind: ServiceAccount
  name: deploy-bot
  namespace: production
roleRef:
  kind: Role
  name: deployer
  apiGroup: rbac.authorization.k8s.io
```

#### 1.3 SRE 实战：CI/CD ServiceAccount

```yaml
# 为 CI/CD Pipeline 创建最小权限 SA
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ci-pipeline
  namespace: production

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ci-role
  namespace: production
rules:
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "update", "patch"]
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ci-binding
  namespace: production
subjects:
- kind: ServiceAccount
  name: ci-pipeline
  namespace: production
roleRef:
  kind: Role
  name: ci-role
  apiGroup: rbac.authorization.k8s.io
```
"""


def generate_k8s_scheduler_content() -> str:
    return """### 1. 调度器与亲和性

#### 1.1 调度流程

```
1. 过滤（Filtering）— 排除不满足的节点
   - 资源充足（CPU/Memory）
   - 端口不冲突
   - NodeSelector 匹配
   - 污点/容忍匹配

2. 打分（Scoring）— 给剩余节点打分
   - 资源均衡
   - 亲和性/反亲和性
   - 镜像本地性

3. 选择最高分节点绑定
```

#### 1.2 nodeAffinity

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: kubernetes.io/arch
            operator: In
            values:
            - arm64
          - key: node-type
            operator: In
            values:
            - gpu
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
          - key: zone
            operator: In
            values:
            - us-east-1a
```

#### 1.3 podAntiAffinity — 避免同节点

```yaml
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - mysql
        topologyKey: kubernetes.io/hostname
# 效果：同一节点上不能有两个 mysql Pod
```

#### 1.4 污点与容忍

```bash
# 给节点加污点
kubectl taint nodes node1 key=value:NoSchedule

# Pod 容忍污点
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
```

| 效果 | 说明 |
|------|------|
| NoSchedule | 不调度新 Pod 到此节点 |
| PreferNoSchedule | 尽量避免 |
| NoExecute | 驱逐已有 Pod |
"""


def generate_k8s_hpa_content() -> str:
    return """### 1. HPA — 水平 Pod 自动扩缩容

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
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
      stabilizationWindowSeconds: 60   # 扩容后稳定 60 秒
      policies:
      - type: Pods
        value: 2                       # 每次最多加 2 个
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300  # 缩容前等 5 分钟
```

```bash
# 查看 HPA
kubectl get hpa
kubectl describe hpa web-app-hpa

# 测试扩容
kubectl run load-generator --image=busybox -- \
    /bin/sh -c "while true; do wget -q -O- http://web-app; done"
```

### 2. SRE 实战案例

```
场景：大促流量突增
Before: 3 个 Pod，CPU 利用率 80%
During: 流量 5 倍，CPU 到 90%
HPA 自动扩容到 8 个 Pod，CPU 回落到 60%
After: 流量回落，5 分钟后缩容回 3 个
```
"""


def generate_k8s_helm_content() -> str:
    return """### 1. Helm — K8s 包管理器

#### 1.1 Chart 结构

```
mychart/
├── Chart.yaml        # 元数据（名称、版本、依赖）
├── values.yaml       # 默认配置值
├── templates/        # K8s 资源模板
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── _helpers.tpl  # 模板函数
└── charts/           # 子 Chart（依赖）
```

#### 1.2 使用 Helm

```bash
# 添加仓库
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# 搜索
helm search repo nginx

# 安装
helm install my-release bitnami/nginx \\
    --set replicaCount=3 \\
    --set service.type=LoadBalancer

# 查看
helm list
helm status my-release

# 升级
helm upgrade my-release bitnami/nginx --set replicaCount=5

# 回滚
helm history my-release
helm rollback my-release 1

# 卸载
helm uninstall my-release
```

#### 1.3 创建自己的 Chart

```bash
# 创建 Chart
helm create myapp

# 目录结构
myapp/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml    # 用 {{ .Values.image.tag }} 模板
    ├── service.yaml
    └── ingress.yaml

# 模板化
# templates/deployment.yaml
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
```

### 2. SRE 实战：一键部署 Prometheus

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \\
    --namespace monitoring --create-namespace \\
    --set grafana.adminPassword=admin123
```
"""


def generate_k8s_project_content() -> str:
    return """### K8s 综合项目：部署完整应用

#### 需求

在 K8s 集群上部署一个完整的 Web 应用栈：
- Frontend（React/Nginx）
- Backend API（Python/Node.js）
- Database（PostgreSQL）
- Cache（Redis）
- 可观测性（Prometheus + Grafana）

#### 架构

```yaml
# namespace
apiVersion: v1
kind: Namespace
metadata:
  name: webapp

# 核心资源清单
# 1. ConfigMap + Secret（配置）
# 2. Deployment（前端 + 后端）
# 3. Service（内部通信 + 外部访问）
# 4. Ingress（域名路由）
# 5. StatefulSet（数据库）
# 6. PVC（持久化存储）
# 7. HPA（自动扩缩容）
# 8. ServiceAccount + Role（权限）
```

#### 验收标准

```bash
# 所有 Pod 运行中
kubectl get pods -n webapp

# Service 可访问
kubectl get svc -n webapp

# Ingress 路由
curl -H "Host: webapp.example.com" $(minikube ip)

# HPA 生效
kubectl get hpa -n webapp

# 监控面板
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```
"""


def generate_k8s_review_content() -> str:
    return """### K8s 阶段测试

## 1. 理论测试

1. 解释 K8s 中 Pod、Deployment、Service、Ingress 的关系
2. livenessProbe、readinessProbe、startupProbe 的区别
3. 滚动更新的原理和配置参数
4. PV、PVC、StorageClass 的关系
5. RBAC 中 Role vs ClusterRole 的区别

## 2. 实操测试

### 任务 1：部署完整 Web 应用
```
要求：
- Deployment + Service + Ingress
- 健康检查
- 资源限制
- HPA 自动扩缩容
```

### 任务 2：故障排查
```
场景：Pod 处于 CrashLoopBackOff
排查步骤：
1. kubectl describe pod
2. kubectl logs pod-name
3. 检查资源配置
4. 检查依赖服务是否就绪
```

## 3. 自我评估

- [ ] 能独立完成 K8s 应用部署
- [ ] 理解声明式 API 和自愈机制
- [ ] 能排查 Pod 启动失败问题
- [ ] 了解 HPA 和滚动更新
"""


def generate_k8s_default_content() -> str:
    return """### 1. Kubernetes

K8s 是容器编排的标准平台。

### 2. 核心概念

- Pod: 最小部署单元
- Deployment: 管理无状态应用
- Service: 稳定的网络端点
- ConfigMap/Secret: 配置管理

### 3. SRE 实战

- 容器化应用部署
- 自动扩缩容
- 滚动更新与回滚
"""


# ── Cloud 生成器 ──────────────────────────────────────────────────────

def generate_cloud_content(day: int, topic: str) -> str:
    content_map = {
        105: generate_cloud_intro_content,
        106: generate_cloud_ec2_content,
        107: generate_cloud_vpc_content,
        108: generate_cloud_s3_content,
        109: generate_cloud_rds_content,
        110: generate_cloud_elb_content,
        111: generate_cloud_asg_content,
        112: generate_cloud_monitor_content,
        113: generate_cloud_dns_content,
        114: generate_cloud_eks_content,
        115: generate_cloud_security_content,
        116: generate_cloud_ha_content,
        117: generate_cloud_saa_content,
        118: generate_cloud_saa_practice_content,
        119: generate_cloud_review_content,
    }
    if day in content_map:
        return content_map[day]()
    return generate_cloud_default_content()


# 这里简化，只生成几个关键的
def generate_cloud_intro_content() -> str:
    return """### 1. AWS 简介

#### 1.1 AWS 核心服务

| 服务 | 说明 | 阿里云对应 |
|------|------|-----------|
| EC2 | 弹性计算 | ECS |
| VPC | 虚拟私有网络 | VPC |
| S3 | 对象存储 | OSS |
| RDS | 关系数据库 | RDS |
| ELB | 负载均衡 | SLB |
| EKS | Kubernetes 服务 | ACK |
| Route 53 | DNS 服务 | 云解析 DNS |
| CloudWatch | 监控 | 云监控 |

#### 1.2 IAM — 身份与访问管理

```
AWS 账户 ≠ IAM 用户
- Root Account: 最高权限（生产禁用）
- IAM User: 个人身份（AK/SK）
- IAM Group: 用户组
- IAM Role: 临时权限（EC2、Lambda 等使用）
- IAM Policy: 权限定义（JSON）
```

### 2. 安全最佳实践

1. 禁用 Root 账户的 AK/SK
2. 启用 MFA
3. IAM 用户最小权限
4. 使用 Role 而非 Access Key（EC2/Lambda）
5. 定期轮换密钥
6. CloudTrail 审计所有 API 调用
"""


def generate_cloud_ec2_content() -> str:
    return """### 1. EC2 基础

#### 1.1 实例类型

| 系列 | 用途 | 示例 |
|------|------|------|
| t3/t4g | 通用、突发 | Web 服务器、开发环境 |
| m6i/m7g | 通用均衡 | 应用服务器 |
| c7i | 计算优化 | 批量处理、视频编码 |
| r7i | 内存优化 | 数据库、缓存 |
| i4i | 存储优化 | NoSQL、数据仓库 |
| g5 | GPU | ML 训练/推理 |

#### 1.2 创建 EC2 实例

```bash
# AWS CLI
aws ec2 run-instances \\
    --image-id ami-0c55b159cbfafe1f0 \\
    --instance-type t3.micro \\
    --key-name my-key \\
    --security-group-ids sg-xxx \\
    --subnet-id subnet-xxx \\
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=web-server}]'

# SSH 连接
ssh -i my-key.pem ec2-user@<public-ip>

# 查看实例信息
aws ec2 describe-instances --filters "Name=tag:Name,Values=web-server"
```

### 2. 安全组（Security Group）

```bash
# 规则：状态防火墙（允许/拒绝）
aws ec2 authorize-security-group-ingress \\
    --group-id sg-xxx \\
    --protocol tcp \\
    --port 22 \\
    --cidr 10.0.0.0/8    # 只允许内网 SSH
```
"""


def generate_cloud_vpc_content() -> str:
    return """### 1. VPC 网络

#### 1.1 VPC 架构

```
VPC (10.0.0.0/16)
├── Public Subnet (10.0.0.0/24)
│   ├── Load Balancer
│   ├── NAT Gateway
│   └── Bastion Host
│
├── Private Subnet (10.0.1.0/24)
│   ├── App Server
│   └── Worker
│
├── Data Subnet (10.0.2.0/24)
│   ├── Database (RDS)
│   └── Cache (ElastiCache)
│
└── Internet Gateway
    └── 公网流量 → LB → App → DB
```

#### 1.2 子网规划

```
/16 VPC → 65,536 IP
/24 Subnet → 256 IP
推荐规划：
- 至少 2 个 AZ（可用区）
- 每个 AZ 有 Public + Private 子网
- Public 子网：NAT Gateway、LB
- Private 子网：应用、数据库
```

### 2. NAT Gateway

```
Public Subnet → NAT Gateway → Internet Gateway
    ↑
Private Subnet (出站流量通过 NAT)

作用：Private Subnet 中的实例可以访问外网（下载更新）
      但外网不能直接访问 Private Subnet
```
"""


def generate_cloud_s3_content() -> str:
    return """### 1. S3 对象存储

#### 1.1 核心概念

```
Bucket (桶) — 全局唯一的命名空间
Object (对象) — 文件 + 元数据
Key (键) — 对象路径/文件名
Region (区域) — 存储的地理位置
Versioning — 版本控制
Lifecycle — 自动分层存储
```

#### 1.2 操作

```bash
# 创建 Bucket
aws s3 mb s3://my-backup-bucket

# 上传
aws s3 cp local-file.txt s3://my-backup-bucket/
aws s3 sync ./logs/ s3://my-backup-bucket/logs/

# 下载
aws s3 cp s3://my-backup-bucket/file.txt .

# 查看
aws s3 ls s3://my-backup-bucket/

# 生命周期策略
aws s3api put-bucket-lifecycle-configuration \\
    --bucket my-backup-bucket \\
    --lifecycle-configuration '{
        "Rules": [
            {
                "ID": "Move to IA after 30 days",
                "Filter": {"Prefix": "logs/"},
                "Status": "Enabled",
                "Transitions": [
                    {"Days": 30, "StorageClass": "STANDARD_IA"},
                    {"Days": 90, "StorageClass": "GLACIER"}
                ],
                "Expiration": {"Days": 365}
            }
        ]
    }'
```

### 2. 成本优化

| 存储类型 | 适用场景 | 价格 |
|----------|----------|------|
| Standard | 频繁访问 | $$ |
| Standard-IA | 不频繁访问 | $ |
| Glacier | 归档（小时级恢复） | ¢ |
| Glacier Deep Archive | 冷归档（天级恢复） | ¢¢ |
"""


def generate_cloud_rds_content() -> str:
    return """### 1. RDS 数据库

#### 1.1 多可用区部署

```
Primary (AZ-a) ────同步复制────→ Standby (AZ-b)
     ↑                                ↑
  读写                              只读（故障时切换）

特性：
- 自动故障转移（通常 < 120 秒）
- 备份不影响主实例性能（从 Standby 备份）
- 自动补丁（维护窗口）
```

```bash
# 创建 Multi-AZ RDS
aws rds create-db-instance \\
    --db-instance-identifier prod-db \\
    --db-instance-class db.t3.medium \\
    --engine mysql \\
    --engine-version 8.0 \\
    --allocated-storage 100 \\
    --multi-az \\
    --backup-retention-period 7 \\
    --storage-type gp3
```

### 2. 备份与恢复

```bash
# 自动备份（保留 7 天）
# PITR: 可以恢复到过去任意时间点（保留期内）

# 手动快照
aws rds create-db-snapshot \\
    --db-instance-identifier prod-db \\
    --db-snapshot-identifier prod-db-backup-20260501

# 从快照恢复
aws rds restore-db-instance-from-db-snapshot \\
    --db-instance-identifier restored-db \\
    --db-snapshot-identifier prod-db-backup-20260501
```
"""


def generate_cloud_elb_content() -> str:
    return """### 1. ELB 负载均衡

| 类型 | 层级 | 协议 | 适用场景 |
|------|------|------|----------|
| ALB | L7 | HTTP/HTTPS/WebSocket | Web 应用、微服务 |
| NLB | L4 | TCP/UDP/TLS | 高性能、低延迟 |
| CLB (Classic) | L4/L7 | 混合 | 遗留系统 |

```bash
# 创建 ALB
aws elbv2 create-load-balancer \\
    --name web-alb \\
    --subnets subnet-1 subnet-2 \\
    --security-groups sg-web \\
    --scheme internet-facing

# 目标组
aws elbv2 create-target-group \\
    --name web-tg \\
    --protocol HTTP \\
    --port 80 \\
    --vpc-id vpc-xxx \\
    --health-check-path /health

# 监听器
aws elbv2 create-listener \\
    --load-balancer-arn alb-arn \\
    --protocol HTTP \\
    --port 80 \\
    --default-actions Type=forward,TargetGroupArn=tg-arn
```

### 2. 健康检查

```
ALB 健康检查：
- 每 30 秒检查一次
- 连续 3 次成功 → 标记为 Healthy
- 连续 3 次失败 → 标记为 Unhealthy（不再转发流量）
```
"""


def generate_cloud_asg_content() -> str:
    return """### 1. Auto Scaling

```
Launch Template (定义实例配置)
       ↓
Auto Scaling Group (管理实例数量)
       ↓
Scaling Policy (何时扩缩容)
```

```bash
# 创建启动模板
aws ec2 create-launch-template \\
    --launch-template-name web-server \\
    --version-description v1 \\
    --launch-template-data '{
        "ImageId": "ami-0c55b159cbfafe1f0",
        "InstanceType": "t3.micro",
        "SecurityGroupIds": ["sg-xxx"],
        "UserData": "..."
    }'

# 创建 ASG
aws autoscaling create-auto-scaling-group \\
    --auto-scaling-group-name web-asg \\
    --launch-template LaunchTemplateName=web-server \\
    --min-size 2 \\
    --max-size 10 \\
    --desired-capacity 3 \\
    --vpc-zone-identifier "subnet-1,subnet-2"

# 目标追踪策略（CPU > 70% 扩容）
aws autoscaling put-scaling-policy \\
    --auto-scaling-group-name web-asg \\
    --policy-name cpu-target \\
    --policy-type TargetTrackingScaling \\
    --target-tracking-configuration '{
        "PredefinedMetricSpecification": {
            "PredefinedMetricType": "ASGAverageCPUUtilization"
        },
        "TargetValue": 70.0
    }'
```
"""


# 占位实现其他 Cloud 内容
def generate_cloud_monitor_content(): return generate_cloud_default_content()
def generate_cloud_dns_content(): return generate_cloud_default_content()
def generate_cloud_eks_content(): return generate_cloud_default_content()
def generate_cloud_security_content(): return generate_cloud_default_content()
def generate_cloud_ha_content(): return generate_cloud_default_content()
def generate_cloud_saa_content(): return generate_cloud_default_content()
def generate_cloud_saa_practice_content(): return generate_cloud_default_content()
def generate_cloud_review_content(): return generate_cloud_default_content()
def generate_cloud_default_content():
    return """### 1. AWS 云计算

AWS 是全球最大的云服务商。

### 2. 核心服务

- EC2: 弹性计算
- S3: 对象存储
- RDS: 数据库
- VPC: 网络

### 3. SRE 实战

- 高可用架构设计
- 成本优化
- 安全合规
"""


# ── IaC 生成器 ──────────────────────────────────────────────────────

def generate_iac_content(day: int, topic: str) -> str:
    content_map = {
        120: generate_terraform_intro_content,
        121: generate_terraform_basic_content,
        122: generate_terraform_adv_content,
        123: generate_terraform_workflow_content,
        124: generate_terraform_vpc_content,
        125: generate_terraform_eks_content,
        126: generate_ansible_intro_content,
        127: generate_ansible_basic_content,
        128: generate_ansible_module_content,
        129: generate_ansible_role_content,
        130: generate_ansible_adv_content,
        131: generate_ansible_deploy_content,
        132: generate_iac_review_content,
    }
    if day in content_map:
        return content_map[day]()
    return generate_iac_default_content()


def generate_terraform_intro_content() -> str:
    return """### 1. Terraform 简介

#### 1.1 IaC 理念

```
手动操作 → 不可重复、易错、无法审计
Terraform → 声明式、可重复、可审计、版本控制

核心原则：
1. 声明式：定义"要什么"而非"怎么做"
2. 幂等性：多次执行结果一致
3. 状态管理：跟踪实际基础设施
4. 模块化：可复用组件
```

#### 1.2 Terraform vs 其他

| 工具 | 类型 | 适用场景 |
|------|------|----------|
| Terraform | 声明式 IaC | 云基础设施 |
| CloudFormation | 声明式 IaC | 仅限 AWS |
| Ansible | 配置管理 | 服务器配置、软件部署 |
| Pulumi | 声明式 IaC | 用编程语言（Python/Go/TS） |

### 2. 安装

```bash
# 官方安装
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

terraform version
```
"""


def generate_terraform_basic_content() -> str:
    return """### 1. Terraform 基础

#### 1.1 核心文件

```hcl
# main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {
    Name = "web-server"
    Env  = "production"
  }
}

output "public_ip" {
  value = aws_instance.web.public_ip
}
```

#### 1.2 工作流

```bash
# 1. 初始化（下载 provider）
terraform init

# 2. 预览变更
terraform plan

# 3. 应用
terraform apply
# 输入 yes 确认

# 4. 销毁
terraform destroy
```
"""


def generate_terraform_adv_content(): return generate_terraform_default_content()
def generate_terraform_workflow_content(): return generate_terraform_default_content()
def generate_terraform_vpc_content(): return generate_terraform_default_content()
def generate_terraform_eks_content(): return generate_terraform_default_content()
def generate_ansible_intro_content(): return generate_ansible_default_content()
def generate_ansible_basic_content(): return generate_ansible_default_content()
def generate_ansible_module_content(): return generate_ansible_default_content()
def generate_ansible_role_content(): return generate_ansible_default_content()
def generate_ansible_adv_content(): return generate_ansible_default_content()
def generate_ansible_deploy_content(): return generate_ansible_default_content()
def generate_iac_review_content(): return generate_iac_default_content()


def generate_terraform_default_content():
    return """### 1. Terraform IaC

Terraform 是基础设施即代码的标准工具。

### 2. 核心概念

- Provider: 云服务商插件
- Resource: 基础设施资源
- Variable: 输入变量
- Output: 输出值
- State: 状态文件

### 3. SRE 实战

- VPC 网络配置
- EKS 集群创建
- 多环境管理
"""


def generate_ansible_default_content():
    return """### 1. Ansible 配置管理

Ansible 是无代理的配置管理工具。

### 2. 核心概念

- Inventory: 服务器清单
- Playbook: 配置定义
- Module: 功能模块
- Role: 可复用配置包

### 3. SRE 实战

- 批量服务器配置
- 应用部署
- 安全基线配置
"""


# ── Observability 生成器 ─────────────────────────────────────────────

def generate_observability_content(day: int, topic: str) -> str:
    content_map = {
        133: generate_slo_content,
        134: generate_prometheus_basic_content,
        135: generate_promql_content,
        136: generate_grafana_basic_content,
        137: generate_k8s_monitor_content,
        138: generate_alertmanager_content,
        139: generate_monitoring_project_content,
        140: generate_elk_content,
        141: generate_fluentd_content,
        142: generate_kibana_content,
        143: generate_loki_content,
        144: generate_jaeger_content,
        145: generate_apm_content,
        146: generate_observability_review_content,
    }
    if day in content_map:
        return content_map[day]()
    return generate_obs_default_content()


def generate_slo_content(): return generate_obs_default_content()
def generate_prometheus_basic_content(): return generate_obs_default_content()
def generate_promql_content(): return generate_obs_default_content()
def generate_grafana_basic_content(): return generate_obs_default_content()
def generate_k8s_monitor_content(): return generate_obs_default_content()
def generate_alertmanager_content(): return generate_obs_default_content()
def generate_monitoring_project_content(): return generate_obs_default_content()
def generate_elk_content(): return generate_obs_default_content()
def generate_fluentd_content(): return generate_obs_default_content()
def generate_kibana_content(): return generate_obs_default_content()
def generate_loki_content(): return generate_obs_default_content()
def generate_jaeger_content(): return generate_obs_default_content()
def generate_apm_content(): return generate_obs_default_content()
def generate_observability_review_content(): return generate_obs_default_content()

def generate_obs_default_content():
    return """### 1. 可观测性

可观测性三大支柱：Metrics（指标）、Logs（日志）、Traces（链路）。

### 2. 核心工具

- Prometheus: 指标采集
- Grafana: 可视化
- Loki/ELK: 日志
- Jaeger: 链路追踪

### 3. SRE 实战

- 定义 SLO/SLI
- 搭建监控告警
- 故障快速定位
"""


# ── CI/CD 生成器 ──────────────────────────────────────────────────────

def generate_cicd_content(day: int, topic: str) -> str:
    if day == 148:
        return """### 1. GitHub Actions

#### 1.1 概念

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --junitxml=report.xml
      - run: flake8 .

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:${{ github.sha }} .
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - run: docker push ghcr.io/myapp:${{ github.sha }}

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: azure/setup-kubectl@v3
      - run: kubectl set image deployment/web-app app=ghcr.io/myapp:${{ github.sha }}
```

### 2. SRE 视角

- CI 自动测试保证代码质量
- 自动构建镜像保证环境一致
- 部署可追溯（哪个 commit 部署的）
"""
    if day == 150:
        return """### 1. Jenkins

#### 1.1 架构

```
Jenkins Master (调度) → Jenkins Agent (执行)
                         ↓
                    拉取代码 → 构建 → 测试 → 部署
```

#### 1.2 Jenkinsfile (Declarative Pipeline)

```groovy
pipeline {
    agent any
    environment {
        DOCKER_REGISTRY = 'registry.example.com'
        APP_NAME = 'myapp'
    }
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/org/myapp.git'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest --junitxml=report.xml'
            }
        }
        stage('Build Image') {
            steps {
                sh "docker build -t ${DOCKER_REGISTRY}/${APP_NAME}:${BUILD_NUMBER} ."
            }
        }
        stage('Push') {
            steps {
                sh "docker push ${DOCKER_REGISTRY}/${APP_NAME}:${BUILD_NUMBER}"
            }
        }
        stage('Deploy') {
            when { branch 'main' }
            steps {
                sh "kubectl set image deployment/web-app app=${DOCKER_REGISTRY}/${APP_NAME}:${BUILD_NUMBER}"
            }
        }
    }
    post {
        success { echo 'Pipeline succeeded!' }
        failure { echo 'Pipeline failed!' }
    }
}
```

### 2. Jenkins vs GitHub Actions

| 特性 | Jenkins | GitHub Actions |
|------|---------|----------------|
| 部署 | 自建 | SaaS |
| 维护成本 | 高 | 低 |
| 灵活性 | 极高 | 中等 |
| 生态 | 1800+ 插件 | GitHub Marketplace |
| 适合 | 复杂 CI/CD、自建需求 | GitHub 项目、简单流程 |
"""
    if day == 154:
        return """### 1. ArgoCD — GitOps

#### 1.1 GitOps 理念

```
Git Repository (期望状态)
       ↓ 监听
ArgoCD (控制器)
       ↓ 同步
Kubernetes Cluster (实际状态)

Git is the Single Source of Truth
```

#### 1.2 部署 ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 获取初始密码
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d

# 端口转发
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

#### 1.3 创建 Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: web-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/k8s-manifests.git
    targetRevision: main
    path: manifests/web-app
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```
"""
    if day == 156:
        return """### 1. Vault — 密钥管理

#### 1.1 为什么需要 Vault？

```
问题：API Key、密码硬编码在代码/配置中
解决：Vault 动态生成临时凭据
```

#### 1.2 安装与使用

```bash
# Docker 开发模式
docker run -d --cap-add=IPC_LOCK -p 8200:8200 vault server -dev -dev-root-token-id=root

# 设置环境变量
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'

# 写入 Secret
vault kv put secret/db password=S3cretP@ss host=db.example.com

# 读取 Secret
vault kv get secret/db

# 动态数据库凭据
vault secrets enable database
vault write database/config/mydb plugin_name=postgresql-postgresql-plugin allowed_roles="readonly" connection_url="postgresql://admin:pass@db:5432"
vault write database/roles/readonly db_name=mydb creation_statements="CREATE ROLE '{{name}}' WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO '{{name}}';"
vault read database/creds/readonly
# → 临时用户名密码，自动过期
```
"""
    if day == 158:
        return """### 1. 混沌工程

#### 1.1 理念

> "与其等待故障发生，不如主动制造故障来验证系统韧性"

#### 1.2 Chaos Mesh

```bash
# 安装
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-testing --create-namespace

# Pod Kill 实验
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill
  namespace: production
spec:
  action: pod-kill
  mode: one
  duration: '30s'
  selector:
    labelSelectors:
      app: web-app
  scheduler:
    cron: '@every 2m'

# 网络延迟实验
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: network-delay
spec:
  action: delay
  mode: all
  delay:
    latency: '200ms'
    correlation: '25'
    jitter: '50ms'
  selector:
    labelSelectors:
      app: web-app
  duration: '60s'
```

### 2. SRE 视角

- 定期混沌实验验证系统韧性
- 每个故障有对应的告警和恢复策略
- 实验结果写入 RCA 报告
"""
    if day == 159:
        return """### 1. CI 安全扫描

#### 1.1 SAST — 静态分析

```yaml
# .github/workflows/security.yml
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:latest
          format: 'sarif'
          exit-code: '1'
          severity: 'CRITICAL,HIGH'
          scanners: 'vuln,secret,config'
```

#### 1.2 安全门禁

```
CI 流程中加入安全检查：
1. SAST (代码静态分析) — SonarQube, CodeQL
2. DAST (动态分析) — OWASP ZAP
3. 依赖扫描 — Trivy, Snyk
4. 镜像扫描 — Trivy, Docker Scout
5. IaC 扫描 — Checkov, tfsec

任何 CRITICAL/HIGH 发现 → 阻断部署
```
"""
    return """### 1. CI/CD

CI/CD 是现代软件交付的核心。

### 2. 核心工具

- GitHub Actions / GitLab CI / Jenkins
- ArgoCD (GitOps)
- Vault (密钥管理)
- Trivy (安全扫描)

### 3. SRE 实战

- 自动化构建和部署
- 金丝雀发布
- 安全门禁
"""


# ── LLM Ops 生成器 ────────────────────────────────────────────────────

def generate_llmops_content(day: int, topic: str) -> str:
    if day == 161:
        return """### 1. LLM Ops 概述

#### 1.1 LLM Ops vs 传统 MLOps

| 维度 | 传统 MLOps | LLM Ops |
|------|-----------|---------|
| 模型大小 | MB-GB | GB-TB |
| 推理延迟 | ms 级 | TTFT + TPOT |
| 监控指标 | 准确率、召回率 | 输出质量、幻觉率、token 成本 |
| 部署 | REST API | 流式输出、批量推理 |
| 硬件 | CPU/小 GPU | 大 GPU（A100/H100） |

#### 1.2 核心指标

- **TTFT** (Time To First Token): 首字延迟
- **TPOT** (Time Per Output Token): 每 token 生成时间
- **Throughput**: 每秒处理请求数
- **GPU Utilization**: GPU 利用率
"""
    if day == 162:
        return """### 1. GPU 基础设施运维

#### 1.1 GPU 监控

```bash
# nvidia-smi
nvidia-smi
# 显示：GPU 利用率、显存、温度、功耗

# 持续监控
watch -n 1 nvidia-smi

# 特定进程
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv
```

#### 1.2 MIG (Multi-Instance GPU)

```bash
# A100 支持将 1 个 GPU 分成 7 个 MIG 实例
nvidia-smi mig -lgip  # 列出 profile
nvidia-smi mig -cgi 19  # 创建 MIG 实例
nvidia-smi  # 查看 MIG 分区
```

#### 1.3 GPU 监控脚本

```bash
#!/bin/bash
# gpu_monitor.sh
gpu_count=$(nvidia-smi -L | wc -l)

for i in $(seq 0 $((gpu_count - 1))); do
    util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits -i $i)
    mem_used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i $i)
    mem_total=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits -i $i)
    temp=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits -i $i)

    echo "GPU $i: Util=${util}% Mem=${mem_used}/${mem_total}MB Temp=${temp}°C"

    if [ "$util" -gt 95 ]; then
        echo "ALERT: GPU $i 利用率过高"
    fi
done
```
"""
    if day == 163:
        return """### 1. 模型推理部署

#### 1.1 vLLM

```bash
# 安装
pip install vllm

# 部署
vllm serve meta-llama/Llama-3-8B \\
    --tensor-parallel-size 2 \\
    --max-model-len 8192 \\
    --port 8000

# 测试
curl http://localhost:8000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "meta-llama/Llama-3-8B",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

#### 1.2 Ollama（本地部署）

```bash
# 安装
curl -fsSL https://ollama.com/install.sh | sh

# 部署模型
ollama pull llama3:8b
ollama run llama3:8b

# API 服务（默认 11434 端口）
curl http://localhost:11434/api/generate -d '{
  "model": "llama3:8b",
  "prompt": "What is SRE?",
  "stream": false
}'
```

#### 1.3 推理优化

| 优化技术 | 效果 | 说明 |
|----------|------|------|
| PagedAttention | 2-4x 吞吐量 | vLLM 核心技术 |
| Continuous Batching | 2-3x 吞吐量 | 动态批次大小 |
| 量化（INT8/INT4） | 2-4x 显存减少 | GPTQ、AWQ |
| Speculative Decoding | 2-3x 速度 | 用小模型预测大模型 |
"""
    if day == 164:
        return """### 1. 推理服务监控

#### 1.1 关键指标

- **TTFT**: 首字延迟（用户体验）
- **TPOT**: 每 token 时间（吞吐量）
- **QPS**: 每秒请求数
- **GPU Memory**: 显存使用
- **KV Cache Hit Rate**: 缓存命中率
- **Error Rate**: 请求失败率

#### 1.2 Prometheus Exporter

```python
# vllm_exporter.py
from prometheus_client import start_http_server, Gauge, Counter

request_latency = Gauge('llm_request_latency_seconds', 'Request latency')
token_counter = Counter('llm_tokens_generated_total', 'Total tokens generated')
error_counter = Counter('llm_request_errors_total', 'Total errors')

def monitor_vllm():
    # 从 vLLM /metrics 端点抓取
    # 转化为 Prometheus 指标
    pass
```
"""
    if day == 165:
        return """### 1. 模型微调

#### 1.1 LoRA / QLoRA

```
LoRA (Low-Rank Adaptation):
- 不修改原始模型权重
- 在旁路添加低秩矩阵
- 只训练 LoRA 参数（~0.1% 原始参数量）

QLoRA:
- LoRA + 4-bit 量化
- 单张 24GB GPU 可微调 7B 模型
```

#### 1.2 Unsloth

```python
# pip install unsloth
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/llama-3-8b",
    max_seq_length=2048,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,  # LoRA rank
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=16,
)

# 训练
trainer = SFTTrainer(model=model, train_dataset=dataset, ...)
trainer.train()

# 保存
model.save_pretrained("sre-finetuned")
```
"""
    if day == 166:
        return """### 2. LLM Ops 综合实战

#### 2.1 部署本地 LLM 服务

```bash
# 1. 部署 vLLM
vllm serve meta-llama/Llama-3-8B --tensor-parallel-size 1

# 2. 配置 Nginx 反向代理
# 3. 添加 Prometheus 监控
# 4. 配置告警规则（TTFT > 2s, GPU > 90%）
# 5. API Gateway 限流
```

#### 2.2 自我评估

- [ ] 能用 Ollama/vLLM 部署本地模型
- [ ] 理解 TTFT/TPOT 指标
- [ ] 能编写 GPU 监控脚本
- [ ] 了解量化和 LoRA 微调
"""
    return """### 1. LLM Ops

大模型运维是 SRE 的新兴领域。

### 2. 核心概念

- GPU 基础设施
- 模型推理部署
- 推理服务监控
- 模型微调流水线
"""


# ── SRE Practice 生成器 ─────────────────────────────────────────────

def generate_sre_practice_content(day: int, topic: str) -> str:
    if day == 173:
        return """### 1. On-Call 实践

#### 1.1 告警分级

| 级别 | 响应时间 | 通知方式 | 示例 |
|------|----------|----------|------|
| P0 - Critical | 5 分钟 | 电话 + 短信 + IM | 服务完全不可用 |
| P1 - High | 15 分钟 | 短信 + IM | 核心功能降级 |
| P2 - Medium | 1 小时 | IM | 非核心功能异常 |
| P3 - Low | 下一个工作日 | 邮件/工单 | 性能轻微下降 |

#### 1.2 应急响应流程

```
告警 → 确认 → 止损 → 修复 → 验证 → RCA

1. 确认：真的是故障还是误报？
2. 止损：回滚、切流量、降级
3. 修复：修复根因
4. 验证：监控指标恢复正常
5. RCA: 事后复盘报告
```

#### 1.3 On-Call 轮换

```yaml
# PagerDuty / 飞书告警轮换
rotation:
  primary:
    - zhangsan (周一~周三)
    - lisi (周四~周日)
  secondary:
    - wangwu (backup)
```
"""
    if day == 174:
        return """### 1. 事故管理与 RCA

#### 1.1 无责文化

```
事故复盘目的：改进系统，而非指责个人
关键问题：
- 什么出错了？
- 为什么没更早发现？
- 系统哪里允许这个错误发生？
- 如何防止类似事件？
```

#### 1.2 RCA 报告模板

```markdown
# RCA Report: [事故名称]

## 概述
- 时间：2026-05-01 14:30-15:45 (75 分钟)
- 影响：30% 用户无法访问 API
- 级别：P1

## 时间线
- 14:30 数据库 CPU 飙升到 95%
- 14:35 监控告警触发
- 14:40 On-Call 确认问题
- 14:50 定位到慢查询
- 15:00 紧急 kill 慢查询 + 限流
- 15:15 CPU 恢复正常
- 15:30 修复索引
- 15:45 验证完成

## 根因分析
- 直接原因：缺少索引导致全表扫描
- 深层原因：上线前未做 SQL 审核
- 系统原因：CI/CD 缺少数据库变更检查

## 改进行动
1. 添加 SQL 审核 CI 步骤 (本周)
2. 慢查询告警阈值从 5s 降到 1s (今天)
3. 上线前压测流程 (下周)
```
"""
    if day == 175:
        return """### 1. SLO 与错误预算

#### 1.1 概念

```
SLI (Service Level Indicator): 服务指标
  例：请求成功率 = 99.95%

SLO (Service Level Objective): 目标值
  例：SLI ≥ 99.9%

SLA (Service Level Agreement): 对外承诺
  例：99.9% 可用性，不达标赔偿

错误预算 = 100% - SLO
  SLO 99.9% → 每月 43.2 分钟可停机
```

#### 1.2 错误预算策略

```
预算 > 80% 剩余：正常发布
预算 20%-80%：谨慎发布，关注指标
预算 < 20%：暂停新功能，专注稳定性
预算 = 0%：只修复可靠性问题
```

#### 1.3 SLO 定义

```yaml
# 示例：API 服务 SLO
sli:
  name: api_success_rate
  type: ratio
  good: 'sum(rate(http_requests_total{code=~"2.."}[5m]))'
  total: 'sum(rate(http_requests_total[5m]))'
slo:
  target: 0.999  # 99.9%
  window: 30d
alerting:
  burn_rate:
    - window: 1h, factor: 14.4   # 快速燃烧
    - window: 6h, factor: 6     # 中速燃烧
    - window: 3d, factor: 1     # 慢速燃烧
```
"""
    if day == 176:
        return """### 1. 容量规划

#### 1.1 性能测试

```bash
# wrk 压测
wrk -t12 -c400 -d30s http://api.example.com/users

# 输出：
# Running 30s test @ http://api.example.com/users
#   12 threads and 400 connections
#   Latency: avg 15.3ms, p99 45.2ms
#   Req/Sec: 2600/s
#   Total requests: 78,000
```

#### 1.2 扩缩容策略

```
预估 10 倍流量（双 11）：
1. 当前 QPS 1000 → 目标 10,000
2. 单实例承载 500 QPS
3. 需要 20 个实例（10000/500）
4. 当前 5 个 → 提前扩容到 20 个
5. 压测验证
6. 大促后自动缩容
```
"""
    if day == 177:
        return """### 1. 灾备与恢复

#### 1.1 RPO / RTO

```
RPO (Recovery Point Objective): 最多丢多少数据
  RPO = 1 分钟 → 最多丢 1 分钟数据

RTO (Recovery Time Objective): 多久能恢复服务
  RTO = 5 分钟 → 5 分钟内恢复服务
```

#### 1.2 多活架构

```
Active-Active（双活）:
  Region A ↔ 同步复制 ↔ Region B
  流量分发：50% A + 50% B
  任一 Region 故障，另一全量承载

Active-Standby（主备）:
  Region A（主）→ 异步复制 → Region B（备）
  故障时切换流量到 B
```
"""
    if day == 178:
        return """### 1. 成本优化

#### 1.1 云成本优化策略

```
1. 预留实例：1-3 年承诺 → 节省 40-70%
2. Spot 实例：竞价 → 节省 60-90%（适合批处理）
3. 自动缩容：非工作时间减少实例
4. 存储分层：热/温/冷数据分层
5. 右配资源：不过度配置
```

#### 1.2 分析

```bash
# AWS Cost Explorer
aws ce get-cost-and-usage \\
    --time-period Start=2026-04-01,End=2026-05-01 \\
    --granularity MONTHLY \\
    --metrics BlendedCost \\
    --group-by Type=SERVICE

# 输出：
# EC2: $3,500
# RDS: $1,200
# S3:  $300
# ...
```
"""
    if day == 179:
        return """### SRE 综合实践

结合所有知识点，完成一个完整的 SRE 方案：
1. 定义 SLO 和错误预算
2. 搭建监控告警
3. 制定 On-Call 流程
4. 设计灾备方案
5. 成本优化方案
"""
    return """### 1. SRE 核心实践

SRE 核心实践包括 On-Call、事故管理、SLO、容量规划。

### 2. SRE 实战

- 告警分级与响应
- RCA 报告编写
- 错误预算管理
"""


# ── Capstone 生成器 ───────────────────────────────────────────────────

def generate_capstone_content(day: int, topic: str) -> str:
    if day == 180:
        return """### Capstone 项目规划

#### 1. 项目目标

从零搭建一个生产级 SRE 平台，包含：
- VPC + EKS 基础设施
- 微服务部署
- 可观测性体系
- CI/CD 流水线
- 混沌工程验证

#### 2. 架构设计

```
Internet → CloudFront → WAF → ALB → EKS
                                    ├── Frontend (React)
                                    ├── API Gateway
                                    ├── User Service
                                    ├── Order Service
                                    ├── PostgreSQL (RDS)
                                    └── Redis (ElastiCache)
```

#### 3. 验收标准

每个组件有独立的验证清单。
"""
    return """### Capstone 项目

综合所有知识，完成生产级平台搭建。
"""


# ── Interview 生成器 ─────────────────────────────────────────────────

def generate_interview_content(day: int, topic: str) -> str:
    if day == 187:
        return """### 1. 简历优化

#### 1.1 STAR 法则

```
Situation: 背景（在什么情况下）
Task: 任务（你要做什么）
Action: 行动（你做了什么）
Result: 结果（量化成果）

示例：
❌ "负责公司服务器运维"
✅ "在双十一大促期间（S），负责 200 台服务器的弹性扩容（T），
    编写自动化脚本实现 30 分钟内完成全部扩容（A），
    确保零故障，相比去年扩容时间缩短 80%（R）"
```

#### 1.2 SRE 简历要点

- 量化成果：减少 MTTR 30%、提高可用性 99.95%
- 技术栈：Linux、K8s、Terraform、Prometheus
- 项目：从设计到上线的完整经历
"""
    if day >= 188 and day <= 190:
        return f"""### SRE 面试题

## 常见面试问题

1. 解释 Linux 进程状态和负载均衡原理
2. K8s 中 Pod 的生命周期和故障排查
3. 数据库慢查询优化思路
4. 如何设计一个高可用系统
5. 你遇到过的最严重的线上故障是什么？

## 模拟面试

自己计时回答每个问题，录音后复盘。
"""
    if day == 191:
        return """### 1. 认证准备

#### 1.1 CKA (Certified Kubernetes Administrator)

- 考试时长：2 小时
- 题型：实操题（不是选择题）
- 通过率：需 66%
- 费用：$395

备考要点：
- 熟悉 kubectl 常用命令
- 能熟练编写 YAML
- 了解故障排查流程

#### 1.2 AWS SAA

- 考试时长：130 分钟
- 题型：选择题
- 重点：VPC、EC2、S3、RDS、IAM、架构设计
"""
    if day == 192:
        return """### 1. 软技能

#### 1.1 沟通

- 用简洁语言解释技术问题
- 主动更新进度
- 事故中保持冷静、清晰沟通

#### 1.2 团队协作

- 文档化所有操作
- 分享知识和经验
- 积极代码审查
"""
    if day == 193:
        return """### 1. 职业规划

#### 1.1 SRE 职业路径

```
初级 SRE → 中级 SRE → 高级 SRE → SRE Lead → 技术总监

方向选择：
1. 技术深耕：云平台专家、K8s 专家
2. 管理路线：SRE Team Lead
3. 架构师：解决方案架构师
```

#### 1.2 持续学习

- 阅读 Google SRE 系列书籍
- 关注 CNCF Landscape
- 参加技术社区
"""
    if day == 194:
        return """### 🎉 24 周完成！入门级 SRE 工程师！

#### 里程碑

你已完成从 Linux 基础到 LLM Ops 的完整学习路径。

#### 下一步

1. CKA/AWS SAA 认证
2. 开源项目贡献
3. 技术博客
4. 投递简历

#### 回顾

- Linux & Shell: ✅
- 网络: ✅
- Python: ✅
- Go: ✅
- 数据库: ✅
- Docker: ✅
- K8s: ✅
- AWS: ✅
- IaC: ✅
- 可观测性: ✅
- CI/CD: ✅
- LLM Ops: ✅
- SRE 实战: ✅

> 🚀 *坚持 6.5 个月，你一定能成为合格的 SRE 工程师！*
"""
    return """### 面试与职业规划

### 准备 SRE 面试，规划职业路径。
"""
