# Day 61: 接口与组合

> 📅 日期：2026-05-02
> 📖 学习主题：接口与组合
> ⏰ 计划学习时间：3-4 小时

---

## 🎯 学习目标

- 理解 Go 接口的隐式实现机制和底层原理
- 掌握接口作为函数参数和返回值的最佳实践
- 理解结构体组合与嵌入的用法
- 掌握接口在 SRE 工具中的抽象设计模式

---

## 📖 详细知识点

### 1. 接口基础

#### 1.1 隐式实现

Go 的接口不需要显式声明 `implements`，只要方法签名匹配就自动满足：

```go
package main

import "fmt"

// 定义接口
type Notifier interface {
    Notify(message string) error
}

// 定义具体类型
type SlackNotifier struct {
    WebhookURL string
    Channel    string
}

// 实现 Notifier 接口（无需显式声明）
func (s *SlackNotifier) Notify(message string) error {
    payload := fmt.Sprintf(`{"channel":"%s","text":"%s"}`, s.Channel, message)
    _, err := http.Post(s.WebhookURL, "application/json", strings.NewReader(payload))
    return err
}

type EmailNotifier struct {
    SMTPHost string
    To       string
}

func (e *EmailNotifier) Notify(message string) error {
    // SMTP 发送逻辑
    return nil
}

// 使用接口
func alertAll(notifiers []Notifier, msg string) {
    for _, n := range notifiers {
        if err := n.Notify(msg); err != nil {
            fmt.Printf("alert failed: %v\n", err)
        }
    }
}

func main() {
    notifiers := []Notifier{
        &SlackNotifier{WebhookURL: "https://hooks.slack.com/...", Channel: "#alerts"},
        &EmailNotifier{SMTPHost: "smtp.company.com", To: "oncall@company.com"},
    }
    alertAll(notifiers, "CRITICAL: db-01 CPU at 95%")
}
```

#### 1.2 接口的底层结构

接口在运行时由两个字组成：

```go
// 接口的运行时表示
type iface struct {
    tab  *itab      // 类型描述：具体类型 + 方法表
    data unsafe.Pointer  // 指向实际数据的指针
}

// itab 包含类型信息和方法分发指针
type itab struct {
    inter *interfacetype  // 接口类型
    _type *_type          // 具体类型
    hash  uint32
    bad   bool
    inhash bool
    unused [2]byte
    fun   [1]uintptr  // 方法指针数组
}
```

```go
// 接口变量存储的是 (类型, 值) 对
var n Notifier = &SlackNotifier{WebhookURL: "...", Channel: "#alerts"}
// n 的内部表示: (type=*SlackNotifier, value=&SlackNotifier{...})

// 检查接口是否为 nil
var x Notifier
fmt.Println(x == nil)  // true — 类型和值都是 nil

// 常见陷阱
var s *SlackNotifier  // nil 指针
n = s                 // 接口不是 nil！类型是 *SlackNotifier，值是 nil
fmt.Println(n == nil) // false — 类型非 nil
```

### 2. 常用标准库接口

#### 2.1 io.Reader 和 io.Writer

```go
// io.Reader — 所有可读事物的抽象
type Reader interface {
    Read(p []byte) (n int, err error)
}

// io.Writer — 所有可写事物的抽象
type Writer interface {
    Write(p []byte) (n int, err error)
}

// SRE 实战：统一处理不同来源的日志数据
func processLogs(r io.Reader) error {
    scanner := bufio.NewScanner(r)
    for scanner.Scan() {
        line := scanner.Text()
        if strings.Contains(line, "ERROR") {
            fmt.Println("[ALERT]", line)
        }
    }
    return scanner.Err()
}

// 同一个函数可以处理多种来源
file, _ := os.Open("/var/log/app.log")
processLogs(file)                // 从文件读取

resp, _ := http.Get("http://api/logs")
processLogs(resp.Body)           // 从 HTTP 响应读取

processLogs(strings.NewReader("ERROR: disk full"))  // 从字符串读取
```

#### 2.2 fmt.Stringer

```go
type Stringer interface {
    String() string
}

type ServerState int
const (
    StateRunning ServerState = iota
    StateStopped
    StateDegraded
)

func (s ServerState) String() string {
    return [...]string{"RUNNING", "STOPPED", "DEGRADED"}[s]
}

// fmt 包自动调用 String() 方法
state := StateRunning
fmt.Println(state)  // RUNNING（而非 0）
```

#### 2.3 error 接口

```go
// error 是最简单的接口
type error interface {
    Error() string
}

// 自定义错误实现
type DeployError struct {
    Service string
    Reason  string
    Code    int
}

func (e *DeployError) Error() string {
    return fmt.Sprintf("deploy failed for %s (code %d): %s",
        e.Service, e.Code, e.Reason)
}

func deploy(service string) error {
    // ...
    return &DeployError{Service: service, Reason: "health check failed", Code: 503}
}
```

### 3. 空接口与类型断言

#### 3.1 interface{}（any）

```go
// Go 1.18+ 可以用 any 代替 interface{}
func printAny(v any) {
    fmt.Println(v)
}

printAny(42)          // int
printAny("hello")     // string
printAny([]int{1,2})  // []int
```

#### 3.2 类型断言与类型开关

```go
// 类型断言
func handleValue(v interface{}) {
    s, ok := v.(string)
    if ok {
        fmt.Println("string:", s)
        return
    }
    n, ok := v.(int)
    if ok {
        fmt.Println("int:", n)
        return
    }
    fmt.Println("unknown type")
}

// 类型开关（更优雅）
func handleValueSwitch(v interface{}) {
    switch t := v.(type) {
    case string:
        fmt.Println("string:", t)
    case int:
        fmt.Println("int:", t)
    case float64:
        fmt.Println("float64:", t)
    case []string:
        fmt.Println("string slice:", t)
    default:
        fmt.Printf("unknown: %T\n", v)
    }
}
```

### 4. 组合优于继承

Go 没有继承，通过结构体嵌入实现组合：

```go
// 基础组件
type Logger struct {
    Prefix string
    Level  string
}

func (l *Logger) Info(msg string) {
    fmt.Printf("[%s] INFO: %s\n", l.Prefix, msg)
}

func (l *Logger) Error(msg string) {
    fmt.Printf("[%s] ERROR: %s\n", l.Prefix, msg)
}

// 组合：嵌入 Logger
type Server struct {
    Logger           // 嵌入 — Server 自动拥有 Info/Error 方法
    Name    string
    Port    int
}

func main() {
    s := Server{
        Logger: Logger{Prefix: "web-01", Level: "info"},
        Name:   "web-01",
        Port:   8080,
    }
    s.Info("server started")  // [web-01] INFO: server started
    s.Error("connection refused")
}

// 接口组合
type ReadWriter interface {
    io.Reader
    io.Writer
}

// ReadWriter 自动拥有 Read 和 Write 方法
// 等价于：
// type ReadWriter interface {
//     Read(p []byte) (n int, err error)
//     Write(p []byte) (n int, err error)
// }
```

### 5. SRE 实战：可插拔的健康检查器

```go
package main

import (
    "fmt"
    "net"
    "net/http"
    "time"
)

// Checker 接口 — 所有健康检查器必须实现
type Checker interface {
    Name() string
    Check() (bool, time.Duration, error)
}

// TCP 检查器
type TCPChecker struct {
    Addr    string
    Timeout time.Duration
}

func (t *TCPChecker) Name() string { return "tcp:" + t.Addr }

func (t *TCPChecker) Check() (bool, time.Duration, error) {
    start := time.Now()
    conn, err := net.DialTimeout("tcp", t.Addr, t.Timeout)
    if err != nil {
        return false, time.Since(start), err
    }
    conn.Close()
    return true, time.Since(start), nil
}

// HTTP 检查器
type HTTPChecker struct {
    URL        string
    Timeout    time.Duration
    ExpectCode int
}

func (h *HTTPChecker) Name() string { return "http:" + h.URL }

func (h *HTTPChecker) Check() (bool, time.Duration, error) {
    start := time.Now()
    client := &http.Client{Timeout: h.Timeout}
    resp, err := client.Get(h.URL)
    if err != nil {
        return false, time.Since(start), err
    }
    defer resp.Body.Close()
    ok := resp.StatusCode == h.ExpectCode
    return ok, time.Since(start), nil
}

// 运行所有检查器
func runChecks(checkers []Checker) {
    fmt.Printf("%-30s %-8s %-10s %s\n", "Checker", "Result", "Latency", "Error")
    fmt.Println(strings.Repeat("-", 70))
    for _, c := range checkers {
        ok, dur, err := c.Check()
        result := "✅ OK"
        errMsg := ""
        if !ok {
            result = "❌ FAIL"
        }
        if err != nil {
            errMsg = err.Error()
        }
        fmt.Printf("%-30s %-8s %-10v %s\n", c.Name(), result, dur.Round(time.Millisecond), errMsg)
    }
}

func main() {
    checkers := []Checker{
        &TCPChecker{Addr: "10.0.1.10:3306", Timeout: 3 * time.Second},
        &HTTPChecker{URL: "http://10.0.1.10:8080/health", Timeout: 5 * time.Second, ExpectCode: 200},
        &TCPChecker{Addr: "10.0.1.10:6379", Timeout: 3 * time.Second},
    }
    runChecks(checkers)
}
```

---

## 💻 实战练习

### 练习 1：实现 io.Writer

创建一个 CountingWriter，包装另一个 io.Writer 并统计写入的字节数。

<details>
<summary>参考答案</summary>

```go
type CountingWriter struct {
    Writer io.Writer
    Count  int64
}
func (cw *CountingWriter) Write(p []byte) (int, error) {
    n, err := cw.Writer.Write(p)
    cw.Count += int64(n)
    return n, err
}
```
</details>

### 练习 2：接口组合设计

设计 MetricCollector 接口，包含 Collect() 和 Name() 方法，实现 CPU 和内存两个采集器。

<details>
<summary>参考答案</summary>

```go
type MetricCollector interface {
    Name() string
    Collect() (float64, error)
}
type CPUCollector struct{}
func (c *CPUCollector) Name() string { return "cpu" }
func (c *CPUCollector) Collect() (float64, error) { /* ... */ return 0, nil }
type MemCollector struct{}
func (m *MemCollector) Name() string { return "memory" }
func (m *MemCollector) Collect() (float64, error) { /* ... */ return 0, nil }
```
</details>

### 练习 3：类型开关处理

编写函数，接受 interface{} 参数，用 type switch 区分 int、string、[]byte 并做不同处理。

<details>
<summary>参考答案</summary>

```go
func process(v interface{}) string {
    switch t := v.(type) {
    case int:
        return fmt.Sprintf("number: %d", t)
    case string:
        return fmt.Sprintf("text: %s", t)
    case []byte:
        return fmt.Sprintf("binary: %d bytes", len(t))
    default:
        return fmt.Sprintf("unknown: %T", v)
    }
}
```
</details>

---

## 📚 扩展阅读

- [Effective Go — Interfaces](https://go.dev/doc/effective_go#interfaces) — 官方接口指南
- [Go Data Structures: Interfaces](https://research.swtch.com/interfaces) — Russ Cox 的深度解析
- [Accept interfaces, return structs](https://go.dev/wiki/CodeReviewComments) — Go 代码审查建议

---

## 📝 笔记

### 延伸思考

- 为什么 Go 选择隐式接口实现而非显式？
- 空接口和类型开关的使用场景是什么？是否有更好的替代方案？
- "Accept interfaces, return structs" 原则在实际项目中如何应用？

---

## ✅ 完成检查

- [ ] 理解接口隐式实现机制和底层结构
- [ ] 掌握 io.Reader/io.Writer 的抽象用法
- [ ] 能使用类型断言和类型开关
- [ ] 理解结构体嵌入与组合的设计模式
- [ ] 能设计可插拔的 SRE 工具接口

---

*由 SRE 学习计划自动生成 | 2026-05-02*
