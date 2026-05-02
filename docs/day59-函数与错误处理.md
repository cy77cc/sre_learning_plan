# Day 59: 函数与错误处理

> 📅 日期：2026-05-02
> 📖 学习主题：函数与错误处理
> ⏰ 计划学习时间：3-4 小时

---

## 🎯 学习目标

- 掌握 Go 函数声明、多返回值和命名返回值的用法
- 深入理解 defer 的执行机制和经典陷阱
- 掌握 Go 错误处理模式和自定义错误
- 理解 panic/recover 的正确使用场景
- 能编写健壮的 SRE 工具函数

---

## 📖 详细知识点

### 1. 函数基础

#### 1.1 函数声明与调用

```go
package main

import "fmt"

// 基本函数
func add(a, b int) int {
    return a + b
}

// 多返回值（Go 的特色）
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, fmt.Errorf("division by zero")
    }
    return a / b, nil
}

// 命名返回值
func getServerInfo() (hostname string, ip string, err error) {
    hostname = "sre-server-01"
    ip = "10.0.1.10"
    // err 自动初始化为零值 nil
    return  // 裸返回，返回所有命名返回值
}

// 可变参数
func sum(numbers ...int) int {
    total := 0
    for _, n := range numbers {
        total += n
    }
    return total
}

func main() {
    // 基本调用
    result := add(3, 5)
    fmt.Println(result) // 8

    // 多返回值
    val, err := divide(10, 3)
    if err != nil {
        fmt.Println("Error:", err)
    } else {
        fmt.Printf("%.2f\n", val)
    }

    // 忽略不需要的返回值
    val2, _ := divide(10, 2)

    // 命名返回值
    h, ip, _ := getServerInfo()
    fmt.Printf("%s @ %s\n", h, ip)

    // 可变参数
    fmt.Println(sum(1, 2, 3, 4, 5))     // 15
    nums := []int{10, 20, 30}
    fmt.Println(sum(nums...))            // 60 — 切片展开
}
```

#### 1.2 函数是一等公民

```go
// 函数类型可以作为参数和返回值
type HandlerFunc func(string) string

func process(name string, handler HandlerFunc) string {
    return handler(name)
}

// 返回函数（闭包）
func multiplier(factor int) func(int) int {
    return func(x int) int {
        return x * factor
    }
}

func main() {
    double := multiplier(2)
    triple := multiplier(3)
    fmt.Println(double(5))  // 10
    fmt.Println(triple(5))  // 15
}
```

### 2. defer 深度解析

#### 2.1 defer 的执行机制

defer 将函数调用压入栈中，在 surrounding 函数返回时按 LIFO 顺序执行：

```go
package main

import "fmt"

func main() {
    defer fmt.Println("first deferred — executed LAST")
    defer fmt.Println("second deferred — executed MIDDLE")
    defer fmt.Println("third deferred — executed FIRST")

    fmt.Println("normal execution")
}
// 输出:
// normal execution
// third deferred — executed FIRST
// second deferred — executed MIDDLE
// first deferred — executed LAST
```

**defer 参数的求值时机：在 defer 语句执行时求值，而非函数返回时：**

```go
func deferValueTiming() {
    i := 0
    defer fmt.Println("deferred:", i)  // i 在这里求值 → 0
    i++
    fmt.Println("current:", i)          // 1
}
// 输出:
// current: 1
// deferred: 0
```

**如果想延迟求值，用闭包：**

```go
func deferClosureTiming() {
    i := 0
    defer func() { fmt.Println("deferred:", i) }()  // 闭包延迟求值
    i++
    fmt.Println("current:", i)
}
// 输出:
// current: 1
// deferred: 1
```

#### 2.2 defer 经典应用场景

```go
// 场景 1：资源释放（文件、连接、锁）
func readFile(path string) ([]byte, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer f.Close()  // 确保文件被关闭，无论后续是否出错
    return io.ReadAll(f)
}

// 场景 2：解锁互斥锁
var mu sync.Mutex
var cache map[string]string

func getCached(key string) string {
    mu.Lock()
    defer mu.Unlock()  // 确保锁被释放
    return cache[key]
}

// 场景 3：计时
func timedOperation(name string) func() {
    start := time.Now()
    fmt.Printf("[%s] started\n", name)
    return func() {
        elapsed := time.Since(start)
        fmt.Printf("[%s] finished in %v\n", name, elapsed)
    }
}

func processData() {
    defer timedOperation("processData")()
    // ... 处理逻辑 ...
    time.Sleep(100 * time.Millisecond)
}
```

#### 2.3 defer 修改命名返回值

```go
func trickyReturn() (result int) {
    defer func() {
        result++  // defer 可以修改命名返回值
    }()
    return 1  // 先将 1 赋给 result，然后 defer 执行 result++，最终返回 2
}

func noNamedReturn() int {
    result := 1
    defer func() {
        result++  // 不影响返回值！
    }()
    return result  // 返回值在 defer 之前已确定
}
```

### 3. 错误处理

#### 3.1 错误处理基础模式

Go 没有 try-catch，错误通过返回值显式传递：

```go
// 基础错误检查
func fetchConfig(path string) (Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return Config{}, fmt.Errorf("reading config %s: %w", path, err)
    }

    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return Config{}, fmt.Errorf("parsing config %s: %w", path, err)
    }

    if cfg.Timeout <= 0 {
        return Config{}, fmt.Errorf("invalid timeout: %d (must be > 0)", cfg.Timeout)
    }

    return cfg, nil
}
```

**错误处理包装规范：**
```
%w — 包装错误（可用 errors.Unwrap 解包）
%v — 格式化错误消息（不可解包）
```

#### 3.2 自定义错误类型

```go
// 方式 1：sentinel error（哨兵错误）
var (
    ErrNotFound     = errors.New("resource not found")
    ErrUnauthorized = errors.New("unauthorized")
    ErrTimeout      = errors.New("operation timed out")
)

// 方式 2：自定义错误类型（携带更多信息）
type ConnectionError struct {
    Host    string
    Port    int
    Reason  string
    Cause   error
}

func (e *ConnectionError) Error() string {
    return fmt.Sprintf("connection failed to %s:%d: %s (%v)",
        e.Host, e.Port, e.Reason, e.Cause)
}

func (e *ConnectionError) Unwrap() error {
    return e.Cause
}

func connectToDB(host string, port int) error {
    conn, err := net.DialTimeout("tcp",
        fmt.Sprintf("%s:%d", host, port), 5*time.Second)
    if err != nil {
        return &ConnectionError{
            Host:   host,
            Port:   port,
            Reason: "dial failed",
            Cause:  err,
        }
    }
    defer conn.Close()
    return nil
}
```

#### 3.3 错误检查与判断

```go
func handleConnection(host string, port int) {
    err := connectToDB(host, port)
    if err != nil {
        // 判断具体错误类型
        var connErr *ConnectionError
        if errors.As(err, &connErr) {
            fmt.Printf("Connection error: %s\n", connErr.Reason)
            // 重试逻辑
            if connErr.Port == 3306 {
                fmt.Println("Trying fallback port...")
            }
        }

        // 判断哨兵错误
        if errors.Is(err, ErrTimeout) {
            fmt.Println("Timeout — retrying...")
        }

        // 早期写法（Go 1.13 前）
        if err == ErrNotFound { /* ... */ }
    }
}
```

### 4. panic 与 recover

#### 4.1 panic 的使用场景

panic 用于不可恢复的严重错误：

```go
func init() {
    // 初始化失败应该 panic
    if _, err := loadRequiredConfig(); err != nil {
        panic("failed to load required config: " + err.Error())
    }
}

func getConfigValue(key string) string {
    val, ok := config[key]
    if !ok {
        // 必需的配置不存在 — panic
        panic("missing required config key: " + key)
    }
    return val
}
```

#### 4.2 recover 捕获 panic

recover 必须在 defer 中调用才有效：

```go
func safeDivide(a, b float64) (result float64, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("panic recovered: %v", r)
        }
    }()

    if b == 0 {
        panic("division by zero")
    }
    return a / b, nil
}

// SRE 实战：HTTP handler 中的 panic 恢复
func withRecovery(handler http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if r := recover(); r != nil {
                log.Printf("panic in %s: %v", r.URL.Path, r)
                debug.PrintStack()
                http.Error(w, "Internal Server Error", 500)
            }
        }()
        handler(w, r)
    }
}
```

### 5. SRE 实战：健壮的日志采集函数

```go
package main

import (
    "fmt"
    "os"
    "time"
)

type LogEntry struct {
    Timestamp time.Time
    Level     string
    Message   string
}

func CollectLogs(path string) ([]LogEntry, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("opening log file: %w", err)
    }
    defer f.Close()

    var entries []LogEntry
    scanner := bufio.NewScanner(f)
    // 设置更大的缓冲区以处理长行
    scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)

    lineNum := 0
    for scanner.Scan() {
        lineNum++
        line := scanner.Text()
        entry, err := parseLine(line)
        if err != nil {
            fmt.Fprintf(os.Stderr, "warning: line %d: %v\n", lineNum, err)
            continue  // 跳过解析失败的行
        }
        entries = append(entries, entry)
    }

    if err := scanner.Err(); err != nil {
        return entries, fmt.Errorf("reading log file: %w", err)
    }

    return entries, nil
}

func parseLine(line string) (LogEntry, error) {
    if len(line) < 20 {
        return LogEntry{}, fmt.Errorf("line too short")
    }
    ts, err := time.Parse("2006-01-02 15:04:05", line[:19])
    if err != nil {
        return LogEntry{}, fmt.Errorf("parsing timestamp: %w", err)
    }
    return LogEntry{Timestamp: ts, Message: line[20:]}, nil
}
```

---

## 💻 实战练习

### 练习 1：defer 执行顺序

写出以下代码的输出顺序。

<details>
<summary>参考答案</summary>

```go
func main() {
    for i := 0; i < 3; i++ {
        defer fmt.Print(i)
    }
}
// 输出: 210（LIFO 顺序）
```
</details>

### 练习 2：自定义错误类型

创建 TimeoutError 类型，包含操作名、超时时长，实现 Error() 方法。

<details>
<summary>参考答案</summary>

```go
type TimeoutError struct {
    Operation string
    Duration  time.Duration
}
func (e *TimeoutError) Error() string {
    return fmt.Sprintf("operation %q timed out after %v", e.Operation, e.Duration)
}
```
</details>

### 练习 3：安全执行函数

编写 safeExec 函数，接受一个可能 panic 的函数，返回错误而非 panic。

<details>
<summary>参考答案</summary>

```go
func safeExec(fn func()) (err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("panic: %v", r)
        }
    }()
    fn()
    return nil
}
```
</details>

---

## 📚 扩展阅读

- [Effective Go — Errors](https://go.dev/doc/effective_go#errors) — 官方错误处理指南
- [Go 1.13 错误处理](https://go.dev/blog/go1.13-errors) — errors.Is/As 的设计
- [Defer, Panic, and Recover](https://go.dev/blog/defer-panic-and-recover) — 官方博客
- [《Go 语言圣经》第 5 章](https://github.com/gopl-zh/gopl-zh.github.com) — 函数详解

---

## 📝 笔记

### 延伸思考

- 为什么 Go 选择返回值错误而非异常机制？
- defer 的 LIFO 顺序在什么场景下特别重要？
- panic/recover 应该在业务代码中使用吗？

---

## ✅ 完成检查

- [ ] 理解多返回值和命名返回值的使用场景
- [ ] 掌握 defer 的执行时机和参数求值规则
- [ ] 能使用 %w 包装错误并用 errors.Is/As 判断
- [ ] 理解自定义错误类型的实现方式
- [ ] 掌握 panic/recover 的正确使用场景

---

*由 SRE 学习计划自动生成 | 2026-05-02*
