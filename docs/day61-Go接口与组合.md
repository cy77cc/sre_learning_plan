# Day 61: Go 接口与组合

> 📅 日期：2026-05-03
> 📖 学习主题：Go 接口与组合 — 隐式实现、类型断言、接口设计与 io 生态
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 58 (Go 基础语法), Day 59 (函数与错误处理), Day 60 (数据结构)

---

## 🎯 学习目标

- 深入理解 Go 接口的隐式实现机制及底层 iface 结构
- 掌握空接口 `interface{}`、类型断言和类型 switch 的使用
- 理解接口设计原则：小接口、面向行为抽象、依赖反转
- 掌握结构体组合与嵌入（embedding）的用法和优先级规则
- 熟练使用 io.Reader/Writer 生态构建 SRE 数据处理管道

---

## 📖 核心知识点

### 1. 接口的本质与隐式实现

#### 1.1 什么是接口

Go 的接口是一组方法签名的集合。与其他语言不同，Go 的接口是**隐式实现**的 — 不需要 `implements` 关键字，只要类型拥有接口要求的所有方法，就自动满足该接口。

```go
package main

import "fmt"

// 定义接口：行为抽象
type HealthChecker interface {
    Check() (Status, error)
    Name() string
}

type Status struct {
    Healthy bool
    Message string
    Latency int64 // 毫秒
}

// HTTP 健康检查器 — 隐式实现 HealthChecker
type HTTPChecker struct {
    URL     string
    Timeout int
}

func (h *HTTPChecker) Check() (Status, error) {
    // 模拟 HTTP 健康检查
    return Status{Healthy: true, Message: "200 OK", Latency: 42}, nil
}

func (h *HTTPChecker) Name() string {
    return fmt.Sprintf("http-%s", h.URL)
}

// TCP 健康检查器 — 同样隐式实现 HealthChecker
type TCPChecker struct {
    Address string
}

func (t *TCPChecker) Check() (Status, error) {
    return Status{Healthy: true, Message: "port open", Latency: 5}, nil
}

func (t *TCPChecker) Name() string {
    return fmt.Sprintf("tcp-%s", t.Address)
}

func main() {
    // 接口切片：不同类型放在同一个集合中
    checkers := []HealthChecker{
        &HTTPChecker{URL: "http://web-01:8080/healthz"},
        &HTTPChecker{URL: "http://api-01:9090/healthz"},
        &TCPChecker{Address: "db-01:5432"},
    }

    for _, c := range checkers {
        status, err := c.Check()
        if err != nil {
            fmt.Printf("[FAIL] %s: %v\n", c.Name(), err)
            continue
        }
        fmt.Printf("[OK] %s: %s (latency: %dms)\n", c.Name(), status.Message, status.Latency)
    }
}
```

#### 1.2 为什么选择隐式实现

Go 设计者 Rob Pike 说："如果它走起来像鸭子，那它就是鸭子。" 隐式实现的核心优势：

| 特性 | 显式实现 (Java/C#) | 隐式实现 (Go) |
|------|-------------------|--------------|
| 定义位置 | 接口和实现必须在一起 | 接口可以在使用方定义 |
| 耦合度 | 实现方依赖接口包 | 实现方无需知道接口存在 |
| 可测试性 | 需要 mock 框架 | 天然支持 mock |
| 第三方适配 | 需要 wrapper/adapter | 直接满足接口即可 |
| 接口所有权 | 由库作者定义 | 由消费者定义 |

```go
// 隐式实现的威力：为第三方类型创建接口
// 假设我们使用第三方的 AWS SDK 客户端
// 我们可以在自己的包中定义需要的接口，而不必修改 SDK

// 我们的接口 — 只需要我们需要的行为
type EC2Describer interface {
    DescribeInstances(ctx context.Context, input *ec2.DescribeInstancesInput) (*ec2.DescribeInstancesOutput, error)
}

// 传入接口而非具体实现 — 测试时可以轻松 mock
func ListRunningInstances(ctx context.Context, client EC2Describer) ([]string, error) {
    output, err := client.DescribeInstances(ctx, &ec2.DescribeInstancesInput{})
    if err != nil {
        return nil, err
    }
    var names []string
    for _, reservation := range output.Reservations {
        for _, instance := range reservation.Instances {
            if *instance.State.Name == "running" {
                names = append(names, *instance.InstanceId)
            }
        }
    }
    return names, nil
}
```

#### 1.3 接口的底层结构

Go 接口在运行时有两种内部表示：

```
空接口 interface{} 的结构 (eface):
┌──────────────────────┐
│  _type  *_type       │  ← 指向类型元数据
├──────────────────────┤
│  data   unsafe.Pointer │  ← 指向实际数据
└──────────────────────┘

非空接口的结构 (iface):
┌──────────────────────┐
│  tab    *itab         │  ← 接口表（类型+方法）
├──────────────────────┤
│  data   unsafe.Pointer │  ← 指向实际数据
└──────────────────────┘

itab 结构:
┌──────────────────────┐
│  inter  *interfacetype │  ← 接口类型信息
├──────────────────────┤
│  _type  *_type         │  ← 具体类型信息
├──────────────────────┤
│  hash   uint32         │  ← 类型 hash（用于 switch）
├──────────────────────┤
│  fun     [1]uintptr    │  ← 方法地址数组（动态派发）
└──────────────────────┘
```

```go
package main

import (
    "fmt"
    "unsafe"
)

// 验证接口大小
func main() {
    var i interface{} = 42
    var s string = "hello"

    // 空接口 = 2 个机器字（16 字节 on 64-bit）
    fmt.Printf("empty interface size: %d bytes\n", unsafe.Sizeof(i))
    // string size = 2 个机器字（16 字节 on 64-bit）
    fmt.Printf("string size: %d bytes\n", unsafe.Sizeof(s))
}
```

**接口动态派发的性能影响：**

```go
// 直接调用 — 编译时确定地址，可内联
func directCall(s *HTTPChecker) Status {
    status, _ := s.Check()
    return status
}

// 接口调用 — 运行时通过 itab 查找方法地址（动态派发）
func interfaceCall(c HealthChecker) Status {
    status, _ := c.Check()
    return status
}

// 性能差异通常在 1-2ns，在热点路径上需要注意
// 但对于 I/O 密集型的 SRE 工具，这点开销可以忽略
```

---

### 2. 空接口与类型断言

#### 2.1 空接口 `interface{}` (Go 1.18+ 可用 `any`)

空接口没有方法要求，因此**任何类型都满足空接口**：

```go
package main

import "fmt"

// 空接口可以接收任意类型
func printAny(v interface{}) {
    fmt.Printf("type=%T, value=%v\n", v, v)
}

// Go 1.18+ 使用 any（interface{} 的别名）
func printAnyNew(v any) {
    fmt.Printf("type=%T, value=%v\n", v, v)
}

func main() {
    printAny(42)           // type=int, value=42
    printAny("hello")      // type=string, value=hello
    printAny(true)          // type=bool, value=true
    printAny([]int{1,2,3}) // type=[]int, value=[1 2 3]
}
```

**SRE 场景：通用配置解析器**

```go
// 解析任意 JSON 配置
func parseConfig(data []byte) (map[string]any, error) {
    var config map[string]any
    if err := json.Unmarshal(data, &config); err != nil {
        return nil, fmt.Errorf("parsing config: %w", err)
    }
    return config, nil
}

// 从配置中安全获取值
func getConfigString(config map[string]any, key string) (string, bool) {
    val, ok := config[key]
    if !ok {
        return "", false
    }
    s, ok := val.(string)
    return s, ok
}

func getConfigInt(config map[string]any, key string) (int, bool) {
    val, ok := config[key]
    if !ok {
        return 0, false
    }
    // JSON 数字默认解码为 float64
    f, ok := val.(float64)
    if !ok {
        return 0, false
    }
    return int(f), true
}
```

#### 2.2 类型断言

类型断言用于从接口值中提取具体类型：

```go
package main

import "fmt"

func processValue(v interface{}) {
    // 方式 1：直接断言（panic 风险）
    // s := v.(string)  // 如果 v 不是 string，panic!

    // 方式 2：安全断言（推荐）
    s, ok := v.(string)
    if ok {
        fmt.Println("It's a string:", s)
        return
    }

    i, ok := v.(int)
    if ok {
        fmt.Println("It's an int:", i)
        return
    }

    fmt.Printf("Unknown type: %T\n", v)
}

func main() {
    processValue("hello")  // It's a string: hello
    processValue(42)        // It's an int: 42
    processValue(3.14)      // Unknown type: float64
}
```

#### 2.3 类型 switch

当需要处理多种类型时，类型 switch 比多个 if-else 更清晰：

```go
package main

import "fmt"

// SRE 场景：解析不同格式的监控指标值
func formatMetricValue(name string, value interface{}) string {
    switch v := value.(type) {
    case int:
        return fmt.Sprintf("%s=%d", name, v)
    case float64:
        return fmt.Sprintf("%s=%.2f", name, v)
    case string:
        return fmt.Sprintf("%s=%q", name, v)
    case bool:
        if v {
            return fmt.Sprintf("%s=1", name)
        }
        return fmt.Sprintf("%s=0", name)
    case []interface{}:
        return fmt.Sprintf("%s=[%d items]", name, len(v))
    case map[string]interface{}:
        return fmt.Sprintf("%s={%d keys}", name, len(v))
    case nil:
        return fmt.Sprintf("%s=null", name)
    default:
        return fmt.Sprintf("%s=(%T)", name, v)
    }
}

func main() {
    metrics := map[string]interface{}{
        "cpu_usage":    85.5,
        "memory_mb":    4096,
        "hostname":     "web-01",
        "is_healthy":   true,
        "disk_devices": []interface{}{"/dev/sda1", "/dev/sdb1"},
        "tags":         map[string]interface{}{"env": "prod", "region": "us-east-1"},
        "last_backup":  nil,
    }

    for name, val := range metrics {
        fmt.Println(formatMetricValue(name, val))
    }
}
```

---

### 3. 接口设计原则

#### 3.1 小接口原则

Go 社区推崇小接口。标准库中最常用的接口通常只有 1-2 个方法：

```go
// 标准库中的小接口示例
type Reader interface {
    Read(p []byte) (n int, err error)   // 1 个方法
}

type Writer interface {
    Write(p []byte) (n int, err error)  // 1 个方法
}

type Closer interface {
    Close() error                        // 1 个方法
}

type Stringer interface {
    String() string                      // 1 个方法
}

type Error interface {
    Error() string                       // 1 个方法
}

// 组合接口
type ReadCloser interface {
    Reader
    Closer
}

type ReadWriteCloser interface {
    Reader
    Writer
    Closer
}
```

**经验法则：**
- 1 个方法的接口：通常只需要一个函数类型
- 2-3 个方法的接口：最常见、最好用
- 超过 5 个方法的接口：考虑是否可以拆分

#### 3.2 接口命名约定

```go
// 单方法接口：方法名 + er 后缀
type Reader interface { Read(p []byte) (int, error) }
type Writer interface { Write(p []byte) (int, error) }
type Formatter interface { Format(s string) string }
type Checker interface { Check() error }
type Serializer interface { Serialize() ([]byte, error) }

// 如果方法名本身是动词 + er，可以简写
// type Singler 不如 type Singer 好看

// 多方法接口：描述行为
type ReadWriter interface { ... }
type ReadWriteCloser interface { ... }
```

#### 3.3 面向行为抽象

好的接口定义行为，而不是数据：

```go
// ❌ 不好：面向数据的接口（太具体）
type ServerInfo interface {
    GetID() int
    GetName() string
    GetIPAddress() string
    GetPort() int
}

// ✅ 好：面向行为的接口（抽象能力）
type HealthChecker interface {
    Check() (Status, error)
}

type MetricsCollector interface {
    Collect() (map[string]float64, error)
}

type LogProvider interface {
    Logs(since time.Time) ([]LogEntry, error)
}

// 一个类型可以同时实现多个行为接口
type Server struct {
    ID        int
    Name      string
    IPAddress string
    Port      int
}

func (s *Server) Check() (Status, error)       { /* ... */ return Status{}, nil }
func (s *Server) Collect() (map[string]float64, error) { /* ... */ return nil, nil }
func (s *Server) Logs(since time.Time) ([]LogEntry, error) { /* ... */ return nil, nil }
```

#### 3.4 依赖反转原则 (DIP)

```go
// ❌ 不好：高层模块依赖低层模块的具体实现
type AlertManager struct {
    slack *SlackClient     // 依赖具体实现
    email *EmailClient     // 依赖具体实现
}

// ✅ 好：高层模块依赖抽象接口
type Notifier interface {
    Notify(alert Alert) error
}

type AlertManager struct {
    notifiers []Notifier  // 依赖接口
}

func NewAlertManager(notifiers ...Notifier) *AlertManager {
    return &AlertManager{notifiers: notifiers}
}

func (am *AlertManager) SendAlert(alert Alert) error {
    var errs []error
    for _, n := range am.notifiers {
        if err := n.Notify(alert); err != nil {
            errs = append(errs, fmt.Errorf("%T: %w", n, err))
        }
    }
    if len(errs) > 0 {
        return fmt.Errorf("alert delivery failures: %v", errs)
    }
    return nil
}

// 使用时注入具体实现
func main() {
    am := NewAlertManager(
        &SlackNotifier{Webhook: "https://hooks.slack.com/..."},
        &PagerDutyNotifier{Key: "pd-key-..."},
        &EmailNotifier{SMTPHost: "smtp.company.com"},
    )

    alert := Alert{
        Severity: "critical",
        Message:  "DB connection pool exhausted",
        Source:   "db-01",
    }
    if err := am.SendAlert(alert); err != nil {
        log.Printf("alert failed: %v", err)
    }
}
```

---

### 4. 组合与嵌入（Composition over Inheritance）

#### 4.1 结构体嵌入

Go 没有类继承，但通过结构体嵌入实现组合：

```go
package main

import (
    "fmt"
    "time"
)

// 基础类型
type BaseModel struct {
    ID        int       `json:"id"`
    CreatedAt time.Time `json:"created_at"`
    UpdatedAt time.Time `json:"updated_at"`
}

func (b *BaseModel) Touch() {
    b.UpdatedAt = time.Now()
}

// 嵌入 BaseModel — 获得它的字段和方法
type Server struct {
    BaseModel                    // 嵌入（匿名字段）
    Name      string `json:"name"`
    IPAddress string `json:"ip_address"`
    Status    string `json:"status"`
}

type Alert struct {
    BaseModel
    Severity string `json:"severity"`
    Message  string `json:"message"`
    Source   string `json:"source"`
}

func main() {
    s := Server{
        BaseModel: BaseModel{ID: 1, CreatedAt: time.Now()},
        Name:      "web-01",
        IPAddress: "10.0.1.10",
        Status:    "running",
    }

    // 直接访问嵌入字段
    fmt.Println(s.ID)         // 1（来自 BaseModel）
    fmt.Println(s.CreatedAt)  // 时间（来自 BaseModel）

    // 直接调用嵌入方法
    s.Touch()                  // 等同于 s.BaseModel.Touch()
    fmt.Println(s.UpdatedAt)  // 更新后的时间
}
```

#### 4.2 嵌入的提升（Promotion）规则

```go
type Logger struct {
    Prefix string
}

func (l *Logger) Log(msg string) {
    fmt.Printf("[%s] %s\n", l.Prefix, msg)
}

type MetricsCollector struct {
    Prefix string  // 与 Logger 的 Prefix 同名
}

func (m *MetricsCollector) Collect(name string, value float64) {
    fmt.Printf("[%s] %s=%.2f\n", m.Prefix, name, value)
}

// 嵌入多个类型
type SRETool struct {
    Logger
    MetricsCollector
    Name string
}

func main() {
    tool := SRETool{
        Logger:          Logger{Prefix: "LOG"},
        MetricsCollector: MetricsCollector{Prefix: "METRIC"},
        Name:            "monitor",
    }

    // 方法提升 — 直接调用
    tool.Log("server started")       // [LOG] server started
    tool.Collect("cpu", 85.5)        // [METRIC] cpu=85.5

    // 同名字段冲突 — 必须显式指定
    // tool.Prefix  // 编译错误：ambiguous selector tool.Prefix
    fmt.Println(tool.Logger.Prefix)          // LOG
    fmt.Println(tool.MetricsCollector.Prefix) // METRIC
}
```

#### 4.3 组合 vs 继承

```go
// Java 风格的继承（Go 不支持）
// class HTTPHealthChecker extends HealthChecker { ... }

// Go 风格的组合
type HTTPClient interface {
    Get(url string) (*http.Response, error)
}

type HTTPHealthChecker struct {
    client HTTPClient   // 组合接口
    url    string
}

func NewHTTPHealthChecker(client HTTPClient, url string) *HTTPHealthChecker {
    return &HTTPHealthChecker{client: client, url: url}
}

func (h *HTTPHealthChecker) Check() (Status, error) {
    resp, err := h.client.Get(h.url)
    if err != nil {
        return Status{Healthy: false, Message: err.Error()}, err
    }
    defer resp.Body.Close()
    return Status{
        Healthy: resp.StatusCode == 200,
        Message: resp.Status,
    }, nil
}

// 测试时注入 mock client
type mockClient struct {
    response *http.Response
    err      error
}

func (m *mockClient) Get(url string) (*http.Response, error) {
    return m.response, m.err
}
```

**组合 vs 继承对比表：**

| 特性 | 继承 (Java/C++) | 组合 (Go) |
|------|----------------|----------|
| 关系 | "is-a" (是一个) | "has-a" (有一个) |
| 耦合度 | 强耦合 | 松耦合 |
| 灵活性 | 编译时确定 | 运行时可替换 |
| 可测试性 | 需要 mock 框架 | 依赖注入天然支持 |
| 菱形问题 | 存在（需虚继承） | 不存在 |
| 代码复用 | 通过继承链 | 通过嵌入和委托 |

---

### 5. io.Reader/Writer 生态

#### 5.1 Reader 和 Writer 接口

```go
// io.Reader — 所有可读数据源的抽象
type Reader interface {
    Read(p []byte) (n int, err error)
}

// io.Writer — 所有可写数据目标的抽象
type Writer interface {
    Write(p []byte) (n int, err error)
}
```

```
io 生态架构图：

┌─────────────────────────────────────────────────┐
│                  io.Reader                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │os.File   │  │bytes.Buffer│ │strings.Reader│   │
│  │*os.File  │  │*bytes.Buffer││*strings.Reader│  │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                                                  │
│  ┌──────────────┐  ┌───────────────────────┐     │
│  │*http.Response│  │*gzip.Reader           │     │
│  │  .Body       │  │(io.Reader 的包装器)    │     │
│  └──────────────┘  └───────────────────────┘     │
│                                                  │
│  组合接口:                                        │
│  io.ReadCloser   = Reader + Closer               │
│  io.ReadSeeker   = Reader + Seeker               │
│  io.ReadWriter   = Reader + Writer               │
│  io.ReadWriteCloser = Reader + Writer + Closer   │
└─────────────────────────────────────────────────┘

         │
         │  io.Copy(dst Writer, src Reader)
         ▼

┌─────────────────────────────────────────────────┐
│                  io.Writer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │os.File   │  │bytes.Buffer│ │*http.Request │   │
│  │os.Stdout │  │*bytes.Buffer││  .Body       │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                                                  │
│  ┌──────────────┐  ┌───────────────────────┐     │
│  │*gzip.Writer  │  │*json.Encoder          │     │
│  │(io.Writer包装)│  │(接受 io.Writer)       │     │
│  └──────────────┘  └───────────────────────┘     │
└─────────────────────────────────────────────────┘
```

#### 5.2 组合 Reader/Writer 的力量

```go
package main

import (
    "bytes"
    "compress/gzip"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "os"
    "strings"
)

// 所有这些都实现了 io.Reader：
func readerExamples() {
    // 1. 字符串 → Reader
    r1 := strings.NewReader("hello world")

    // 2. 字节切片 → Reader
    r2 := bytes.NewReader([]byte{72, 101, 108, 108, 111})

    // 3. 文件 → Reader
    r3, _ := os.Open("/etc/hostname")

    // 4. HTTP 响应体 → Reader
    resp, _ := http.Get("http://httpbin.org/get")
    r4 := resp.Body // io.ReadCloser

    // 全部都可以用同一个方式读取
    readers := []io.Reader{r1, r2, r3, r4}
    for _, r := range readers {
        data, _ := io.ReadAll(r)
        fmt.Printf("Read %d bytes\n", len(data))
    }
}

// io.Copy 是连接 Reader 和 Writer 的桥梁
func copyExample() {
    // 从 Reader 拷贝到 Writer
    src := strings.NewReader("log data here")
    dst := os.Stdout
    io.Copy(dst, src) // 输出: log data here
}
```

#### 5.3 SRE 实战：日志压缩传输管道

```go
package main

import (
    "compress/gzip"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "os"
    "time"
)

type LogEntry struct {
    Timestamp time.Time `json:"timestamp"`
    Level     string    `json:"level"`
    Message   string    `json:"message"`
    Source    string    `json:"source"`
}

// 构建处理管道：JSON编码 → Gzip压缩 → HTTP上传
func uploadLogs(entries []LogEntry, uploadURL string) error {
    // 管道：pr (读端) ← pw (写端)
    pr, pw := io.Pipe()

    // goroutine 负责写入（生产者）
    go func() {
        defer pw.Close()

        // 创建 gzip writer，目标是 pipe 的写端
        gz := gzip.NewWriter(pw)
        defer gz.Close()

        // 创建 JSON encoder，目标是 gzip writer
        encoder := json.NewEncoder(gz)

        for _, entry := range entries {
            if err := encoder.Encode(entry); err != nil {
                pw.CloseWithError(fmt.Errorf("encoding log: %w", err))
                return
            }
        }
    }()

    // 主 goroutine 读取并上传（消费者）
    req, err := http.NewRequest("POST", uploadURL, pr)
    if err != nil {
        return fmt.Errorf("creating request: %w", err)
    }
    req.Header.Set("Content-Encoding", "gzip")
    req.Header.Set("Content-Type", "application/json")

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return fmt.Errorf("uploading logs: %w", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(resp.Body)
        return fmt.Errorf("upload failed (%d): %s", resp.StatusCode, string(body))
    }

    return nil
}

// 读取并解压日志
func downloadAndDecompress(url string) ([]LogEntry, error) {
    resp, err := http.Get(url)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    // 自动检测 gzip 并解压
    var reader io.Reader = resp.Body
    gz, err := gzip.NewReader(resp.Body)
    if err == nil {
        reader = gz
        defer gz.Close()
    }

    var entries []LogEntry
    decoder := json.NewDecoder(reader)
    for decoder.More() {
        var entry LogEntry
        if err := decoder.Decode(&entry); err != nil {
            return nil, fmt.Errorf("decoding log: %w", err)
        }
        entries = append(entries, entry)
    }
    return entries, nil
}

func main() {
    logs := []LogEntry{
        {Timestamp: time.Now(), Level: "ERROR", Message: "connection refused", Source: "web-01"},
        {Timestamp: time.Now(), Level: "WARN", Message: "high memory usage", Source: "db-01"},
    }

    if err := uploadLogs(logs, "http://log-collector.internal/upload"); err != nil {
        fmt.Fprintf(os.Stderr, "upload failed: %v\n", err)
        os.Exit(1)
    }
    fmt.Println("Logs uploaded successfully")
}
```

#### 5.4 自定义 Reader/Writer

```go
package main

import (
    "fmt"
    "io"
    "strings"
    "time"
)

// 自定义 Reader：带限速的 Reader（用于控制上传速率）
type ThrottledReader struct {
    reader    io.Reader
    bytesPerSec int
    lastRead  time.Time
}

func NewThrottledReader(r io.Reader, bytesPerSec int) *ThrottledReader {
    return &ThrottledReader{
        reader:      r,
        bytesPerSec: bytesPerSec,
        lastRead:    time.Now(),
    }
}

func (t *ThrottledReader) Read(p []byte) (int, error) {
    // 限制每次读取的字节数
    maxBytes := t.bytesPerSec / 10 // 每 100ms 的配额
    if maxBytes < 1 {
        maxBytes = 1
    }
    if maxBytes > len(p) {
        maxBytes = len(p)
    }

    n, err := t.reader.Read(p[:maxBytes])

    // 简单限速：等待适当时间
    elapsed := time.Since(t.lastRead)
    expected := time.Duration(n) * time.Second / time.Duration(t.bytesPerSec)
    if elapsed < expected {
        time.Sleep(expected - elapsed)
    }
    t.lastRead = time.Now()

    return n, err
}

// 自定义 Writer：带前缀的 Writer（用于给日志加时间戳）
type PrefixedWriter struct {
    writer io.Writer
    prefix string
}

func (p *PrefixedWriter) Write(data []byte) (int, error) {
    prefix := []byte(fmt.Sprintf("[%s] ", p.prefix))
    _, err := p.writer.Write(prefix)
    if err != nil {
        return 0, err
    }
    return p.writer.Write(data)
}

// 自定义 Writer：多路复用（同时写入多个目标）
type MultiWriter struct {
    writers []io.Writer
}

func (mw *MultiWriter) Write(p []byte) (int, error) {
    for _, w := range mw.writers {
        n, err := w.Write(p)
        if err != nil {
            return n, err
        }
    }
    return len(p), nil
}

func main() {
    // 使用限速 Reader
    source := strings.NewReader("这是一段很长的日志数据，需要限速上传...")
    throttled := NewThrottledReader(source, 100) // 100 bytes/sec
    data, _ := io.ReadAll(throttled)
    fmt.Printf("Read %d bytes with throttling\n", len(data))

    // 使用多路复用 Writer（同时输出到 stdout 和 buffer）
    var buf strings.Builder
    mw := &MultiWriter{writers: []io.Writer{&buf, os.Stdout}}
    fmt.Fprintln(mw, "log line 1")
    fmt.Fprintln(mw, "log line 2")
    // buf 和 stdout 都收到了日志
}
```

#### 5.5 接口断言与 WriterTo

```go
// io.WriterTo 接口：优化大数据传输
type WriterTo interface {
    WriteTo(w Writer) (n int64, err error)
}

// 如果 Reader 实现了 WriterTo，io.Copy 会使用它
// 而不是 Read + Write 循环（避免额外的缓冲区拷贝）

func optimizedCopy(dst io.Writer, src io.Reader) (int64, error) {
    // io.Copy 内部会检查 src 是否实现了 WriterTo
    // 如果实现了，直接调用 WriteTo 避免中间缓冲
    return io.Copy(dst, src)
}

// 检查接口实现的编译时断言
var _ io.Reader = (*ThrottledReader)(nil)     // 编译时检查
var _ io.Writer = (*PrefixedWriter)(nil)       // 编译时检查
var _ io.WriterTo = (*bytes.Buffer)(nil)       // bytes.Buffer 实现了 WriterTo
```

---

### 6. SRE 实战案例

#### 6.1 可插拔的通知系统

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
    "sync"
    "time"
)

// 通知接口
type Notifier interface {
    Notify(alert Alert) error
    Name() string
}

type Alert struct {
    Severity  string            `json:"severity"`
    Title     string            `json:"title"`
    Message   string            `json:"message"`
    Source    string            `json:"source"`
    Timestamp time.Time         `json:"timestamp"`
    Labels    map[string]string `json:"labels,omitempty"`
}

// Slack 通知器
type SlackNotifier struct {
    WebhookURL string
    Channel    string
}

func (s *SlackNotifier) Name() string { return "slack" }

func (s *SlackNotifier) Notify(alert Alert) error {
    payload := map[string]interface{}{
        "channel": s.Channel,
        "text":    fmt.Sprintf("*[%s]* %s\n%s", alert.Severity, alert.Title, alert.Message),
        "attachments": []map[string]interface{}{
            {
                "color": severityColor(alert.Severity),
                "fields": []map[string]interface{}{
                    {"title": "Source", "value": alert.Source, "short": true},
                    {"title": "Time", "value": alert.Timestamp.Format(time.RFC3339), "short": true},
                },
            },
        },
    }
    data, _ := json.Marshal(payload)
    resp, err := http.Post(s.WebhookURL, "application/json", bytes.NewReader(data))
    if err != nil {
        return fmt.Errorf("slack notify: %w", err)
    }
    defer resp.Body.Close()
    if resp.StatusCode != 200 {
        return fmt.Errorf("slack returned %d", resp.StatusCode)
    }
    return nil
}

func severityColor(severity string) string {
    switch severity {
    case "critical":
        return "#FF0000"
    case "warning":
        return "#FFA500"
    default:
        return "#36A64F"
    }
}

// PagerDuty 通知器
type PagerDutyNotifier struct {
    RoutingKey string
}

func (p *PagerDutyNotifier) Name() string { return "pagerduty" }

func (p *PagerDutyNotifier) Notify(alert Alert) error {
    payload := map[string]interface{}{
        "routing_key":  p.RoutingKey,
        "event_action": "trigger",
        "payload": map[string]interface{}{
            "summary":   fmt.Sprintf("[%s] %s", alert.Severity, alert.Title),
            "severity":  alert.Severity,
            "source":    alert.Source,
            "timestamp": alert.Timestamp.Format(time.RFC3339),
            "custom_details": map[string]interface{}{
                "message": alert.Message,
                "labels":  alert.Labels,
            },
        },
    }
    data, _ := json.Marshal(payload)
    resp, err := http.Post("https://events.pagerduty.com/v2/enqueue",
        "application/json", bytes.NewReader(data))
    if err != nil {
        return fmt.Errorf("pagerduty notify: %w", err)
    }
    defer resp.Body.Close()
    if resp.StatusCode != 202 {
        return fmt.Errorf("pagerduty returned %d", resp.StatusCode)
    }
    return nil
}

// 告警管理器（依赖接口，不依赖具体实现）
type AlertManager struct {
    notifiers []Notifier
    mu        sync.RWMutex
}

func NewAlertManager(notifiers ...Notifier) *AlertManager {
    return &AlertManager{notifiers: notifiers}
}

func (am *AlertManager) AddNotifier(n Notifier) {
    am.mu.Lock()
    defer am.mu.Unlock()
    am.notifiers = append(am.notifiers, n)
}

// 扇出模式：并发通知所有渠道
func (am *AlertManager) Dispatch(alert Alert) error {
    am.mu.RLock()
    notifiers := make([]Notifier, len(am.notifiers))
    copy(notifiers, am.notifiers)
    am.mu.RUnlock()

    var wg sync.WaitGroup
    errs := make(chan error, len(notifiers))

    for _, n := range notifiers {
        wg.Add(1)
        go func(notifier Notifier) {
            defer wg.Done()
            if err := notifier.Notify(alert); err != nil {
                errs <- fmt.Errorf("%s: %w", notifier.Name(), err)
            }
        }(n)
    }

    wg.Wait()
    close(errs)

    var failures []error
    for err := range errs {
        failures = append(failures, err)
    }
    if len(failures) > 0 {
        return fmt.Errorf("%d/%d notifications failed: %v",
            len(failures), len(notifiers), failures)
    }
    return nil
}

func main() {
    am := NewAlertManager(
        &SlackNotifier{WebhookURL: "https://hooks.slack.com/xxx", Channel: "#alerts"},
        &PagerDutyNotifier{RoutingKey: "pd-key-xxx"},
    )

    alert := Alert{
        Severity:  "critical",
        Title:     "Database connection pool exhausted",
        Message:   "All 100 connections in pool are in use. Last error: connection timeout",
        Source:    "db-pool-monitor",
        Timestamp: time.Now(),
        Labels:    map[string]string{"service": "postgres", "env": "production"},
    }

    if err := am.Dispatch(alert); err != nil {
        fmt.Printf("Alert dispatch partially failed: %v\n", err)
    }
}
```

#### 6.2 接口驱动的多云监控

```go
package main

import (
    "context"
    "fmt"
    "time"
)

// 云平台抽象接口
type CloudProvider interface {
    Name() string
    ListInstances(ctx context.Context) ([]Instance, error)
    GetInstanceMetrics(ctx context.Context, id string) (*Metrics, error)
}

type Instance struct {
    ID       string
    Name     string
    Status   string
    Provider string
}

type Metrics struct {
    CPU    float64
    Memory float64
    Disk   float64
}

// AWS 实现
type AWSProvider struct {
    Region string
}

func (a *AWSProvider) Name() string { return "aws-" + a.Region }

func (a *AWSProvider) ListInstances(ctx context.Context) ([]Instance, error) {
    // 实际实现会调用 AWS SDK
    return []Instance{
        {ID: "i-abc123", Name: "web-01", Status: "running", Provider: "aws"},
    }, nil
}

func (a *AWSProvider) GetInstanceMetrics(ctx context.Context, id string) (*Metrics, error) {
    return &Metrics{CPU: 65.5, Memory: 72.3, Disk: 45.0}, nil
}

// GCP 实现
type GCPProvider struct {
    Project string
}

func (g *GCPProvider) Name() string { return "gcp-" + g.Project }

func (g *GCPProvider) ListInstances(ctx context.Context) ([]Instance, error) {
    return []Instance{
        {ID: "gcp-instance-1", Name: "api-01", Status: "running", Provider: "gcp"},
    }, nil
}

func (g *GCPProvider) GetInstanceMetrics(ctx context.Context, id string) (*Metrics, error) {
    return &Metrics{CPU: 45.2, Memory: 60.1, Disk: 30.5}, nil
}

// 统一监控器
type MultiCloudMonitor struct {
    providers []CloudProvider
}

func NewMultiCloudMonitor(providers ...CloudProvider) *MultiCloudMonitor {
    return &MultiCloudMonitor{providers: providers}
}

func (m *MultiCloudMonitor) ScanAll(ctx context.Context) {
    for _, provider := range m.providers {
        instances, err := provider.ListInstances(ctx)
        if err != nil {
            fmt.Printf("Error listing %s: %v\n", provider.Name(), err)
            continue
        }
        for _, inst := range instances {
            metrics, err := provider.GetInstanceMetrics(ctx, inst.ID)
            if err != nil {
                fmt.Printf("  [%s] %s: metrics error: %v\n", provider.Name(), inst.Name, err)
                continue
            }
            fmt.Printf("  [%s] %s: cpu=%.1f%% mem=%.1f%% disk=%.1f%%\n",
                provider.Name(), inst.Name, metrics.CPU, metrics.Memory, metrics.Disk)
        }
    }
}

func main() {
    monitor := NewMultiCloudMonitor(
        &AWSProvider{Region: "us-east-1"},
        &GCPProvider{Project: "my-project"},
    )

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    monitor.ScanAll(ctx)
}
```

---

## 💻 实战练习

### 练习 1：实现 Stringer 接口

为一个 `Server` 结构体实现 `fmt.Stringer` 接口，使其输出格式为 `web-01 (10.0.1.10:8080) [running]`。

<details>
<summary>参考答案</summary>

```go
package main

import "fmt"

type Server struct {
    Name      string
    IPAddress string
    Port      int
    Status    string
}

func (s Server) String() string {
    return fmt.Sprintf("%s (%s:%d) [%s]", s.Name, s.IPAddress, s.Port, s.Status)
}

func main() {
    s := Server{Name: "web-01", IPAddress: "10.0.1.10", Port: 8080, Status: "running"}
    fmt.Println(s) // web-01 (10.0.1.10:8080) [running]
}
```
</details>

### 练习 2：构建日志过滤管道

使用 `io.Reader` 和 `io.Writer` 构建一个日志过滤管道：从 stdin 读取日志行，过滤掉 DEBUG 级别的日志，将结果写入 stdout。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "bufio"
    "fmt"
    "io"
    "os"
    "strings"
)

type FilterWriter struct {
    writer    io.Writer
    minLevel  string
    levels    map[string]int
}

func NewFilterWriter(w io.Writer, minLevel string) *FilterWriter {
    return &FilterWriter{
        writer:   w,
        minLevel: minLevel,
        levels: map[string]int{
            "DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3, "FATAL": 4,
        },
    }
}

func (fw *FilterWriter) Write(p []byte) (int, error) {
    line := string(p)
    for level, priority := range fw.levels {
        if strings.Contains(line, level) {
            minPriority := fw.levels[fw.minLevel]
            if priority < minPriority {
                return len(p), nil // 过滤掉
            }
            break
        }
    }
    return fw.writer.Write(p)
}

func filterLogs(reader io.Reader, writer io.Writer, minLevel string) error {
    scanner := bufio.NewScanner(reader)
    for scanner.Scan() {
        line := scanner.Text()
        shouldWrite := true
        for level, priority := range map[string]int{
            "DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3,
        } {
            minPri := map[string]int{
                "DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3,
            }[minLevel]
            if strings.Contains(line, level) && priority < minPri {
                shouldWrite = false
                break
            }
        }
        if shouldWrite {
            fmt.Fprintln(writer, line)
        }
    }
    return scanner.Err()
}

func main() {
    logs := `2026-05-03 DEBUG: connecting to db
2026-05-03 INFO: server started
2026-05-03 DEBUG: query took 5ms
2026-05-03 WARN: high memory usage
2026-05-03 ERROR: connection refused`

    filterLogs(strings.NewReader(logs), os.Stdout, "INFO")
    // 输出 INFO/WARN/ERROR，过滤 DEBUG
}
```
</details>

### 练习 3：接口驱动的存储后端

设计一个 `Storage` 接口，包含 `Get`、`Put`、`Delete`、`List` 方法，并实现 `MemoryStorage` 和 `FileStorage` 两个版本。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
    "sync"
)

type Storage interface {
    Get(key string) ([]byte, error)
    Put(key string, value []byte) error
    Delete(key string) error
    List() ([]string, error)
}

// 内存存储实现
type MemoryStorage struct {
    mu   sync.RWMutex
    data map[string][]byte
}

func NewMemoryStorage() *MemoryStorage {
    return &MemoryStorage{data: make(map[string][]byte)}
}

func (m *MemoryStorage) Get(key string) ([]byte, error) {
    m.mu.RLock()
    defer m.mu.RUnlock()
    val, ok := m.data[key]
    if !ok {
        return nil, fmt.Errorf("key %q not found", key)
    }
    return val, nil
}

func (m *MemoryStorage) Put(key string, value []byte) error {
    m.mu.Lock()
    defer m.mu.Unlock()
    m.data[key] = value
    return nil
}

func (m *MemoryStorage) Delete(key string) error {
    m.mu.Lock()
    defer m.mu.Unlock()
    delete(m.data, key)
    return nil
}

func (m *MemoryStorage) List() ([]string, error) {
    m.mu.RLock()
    defer m.mu.RUnlock()
    keys := make([]string, 0, len(m.data))
    for k := range m.data {
        keys = append(keys, k)
    }
    return keys, nil
}

// 文件存储实现
type FileStorage struct {
    dir string
    mu  sync.RWMutex
}

func NewFileStorage(dir string) (*FileStorage, error) {
    if err := os.MkdirAll(dir, 0755); err != nil {
        return nil, err
    }
    return &FileStorage{dir: dir}, nil
}

func (f *FileStorage) path(key string) string {
    return f.dir + "/" + key + ".json"
}

func (f *FileStorage) Get(key string) ([]byte, error) {
    f.mu.RLock()
    defer f.mu.RUnlock()
    return os.ReadFile(f.path(key))
}

func (f *FileStorage) Put(key string, value []byte) error {
    f.mu.Lock()
    defer f.mu.Unlock()
    return os.WriteFile(f.path(key), value, 0644)
}

func (f *FileStorage) Delete(key string) error {
    f.mu.Lock()
    defer f.mu.Unlock()
    return os.Remove(f.path(key))
}

func (f *FileStorage) List() ([]string, error) {
    f.mu.RLock()
    defer f.mu.RUnlock()
    entries, err := os.ReadDir(f.dir)
    if err != nil {
        return nil, err
    }
    var keys []string
    for _, e := range entries {
        name := e.Name()
        if len(name) > 5 && name[len(name)-5:] == ".json" {
            keys = append(keys, name[:len(name)-5])
        }
    }
    return keys, nil
}

// 使用接口的通用函数
func SaveConfig(store Storage, name string, config interface{}) error {
    data, err := json.MarshalIndent(config, "", "  ")
    if err != nil {
        return err
    }
    return store.Put(name, data)
}

func LoadConfig(store Storage, name string, config interface{}) error {
    data, err := store.Get(name)
    if err != nil {
        return err
    }
    return json.Unmarshal(data, config)
}

func main() {
    // 可以轻松切换存储后端
    var store Storage

    // 使用内存存储
    store = NewMemoryStorage()

    // 使用文件存储（取消注释切换）
    // store, _ = NewFileStorage("/tmp/configs")

    type AppConfig struct {
        Host string `json:"host"`
        Port int    `json:"port"`
    }

    SaveConfig(store, "app", AppConfig{Host: "0.0.0.0", Port: 8080})

    var cfg AppConfig
    LoadConfig(store, "app", &cfg)
    fmt.Printf("Config: %+v\n", cfg)

    keys, _ := store.List()
    fmt.Println("Keys:", keys)
}
```
</details>

---

## 🎯 面试题精选

### 1. Go 的接口是如何实现的？底层数据结构是什么？

**答：** Go 接口在运行时使用两种结构：
- **eface (empty interface):** 包含 `_type`（类型元数据指针）和 `data`（数据指针）两个字段。
- **iface (non-empty interface):** 包含 `tab`（itab 指针）和 `data`（数据指针）两个字段。itab 包含接口类型、具体类型、类型 hash 和方法地址数组。

接口赋值时，runtime 会创建 itab 并缓存。方法调用通过 itab 中的方法地址数组进行动态派发。

### 2. 接口的零值是什么？nil 接口和持有 nil 值的接口有什么区别？

**答：** 接口的零值是 `nil`。关键区别：

```go
var err error         // nil 接口：type 和 data 都是 nil
err == nil            // true

var p *MyError = nil
err = p              // 非 nil 接口：type 是 *MyError，data 是 nil
err == nil            // false! 这是常见的坑
```

判断接口是否为 nil 时，必须同时考虑 type 和 data 都为 nil 的情况。

### 3. 为什么 Go 的接口是隐式实现的？有什么优势？

**答：** 隐式实现的核心优势是**解耦**：
- 实现方不需要知道接口的存在，可以在不同包中定义接口
- 为第三方类型定义接口变得很容易（适配器模式天然支持）
- 测试时可以轻松 mock（只需实现相同方法签名）
- 支持 "消费者驱动的契约" — 使用方定义需要什么，而非提供方决定暴露什么

### 4. 类型断言和类型 switch 的区别是什么？什么时候用哪个？

**答：**
- **类型断言** `v.(T)`：当你只关心一种具体类型时使用，返回值和布尔值
- **类型 switch** `switch v.(type)`：当你需要处理多种类型时使用，更清晰且可扩展

类型 switch 编译后会使用 itab 中的 hash 值进行快速比较，性能优于多个 if-else 类型断言。

### 5. 接口的动态派发有性能开销吗？如何优化？

**答：** 有，每次接口方法调用需要通过 itab 查找方法地址（约 1-2ns）。优化方法：
- 在热点路径中使用具体类型而非接口
- 编译器无法对接口调用内联优化
- 对于 I/O 密集型场景（SRE 工具常见），这点开销可以忽略
- 使用 `go tool compile -m` 检查内联情况

### 6. 什么是空结构体 `struct{}`？它在接口中有什么用途？

**答：** 空结构体 `struct{}` 大小为 0 字节，常用于：
- 信号通道：`done := make(chan struct{})`
- 集合实现：`set := make(map[string]struct{})`
- 接口的方法标记：`type Locker interface { Lock(); Unlock() }` 中不需要返回值的方法

### 7. 结构体嵌入和组合有什么区别？嵌入字段的方法集如何确定？

**答：** 嵌入是组合的语法糖。嵌入字段的方法会被"提升"到外层结构体：
- 指针接收者的方法：只有当嵌入字段为指针类型时才提升
- 值接收者的方法：嵌入值或指针都会提升
- 同名方法冲突：外层方法优先于嵌入方法
- 多个嵌入有同名方法：编译错误，必须显式指定

### 8. io.Reader 的 `Read` 方法返回 `n` 和 `err`，当 `n > 0` 且 `err != nil` 时如何处理？

**答：** 根据 io.Reader 契约：
- `n > 0` 且 `err != nil` 是合法的（例如读到 EOF 时仍有数据）
- 调用者必须先处理 `n` 个字节的数据，再处理 err
- `io.ReadAll` 等工具函数已正确处理这种情况
- 自己实现 Reader 时，应先写入数据再返回错误

### 9. 如何在编译时检查一个类型是否实现了某个接口？

**答：** 使用类型断言的编译时检查：

```go
var _ io.Reader = (*MyReader)(nil)      // 编译时检查 *MyReader 是否实现 io.Reader
var _ io.Writer = (*MyWriter)(nil)       // 编译时检查 *MyWriter 是否实现 io.Writer
var _ HealthChecker = (*Server)(nil)     // 编译时检查 *Server 是否实现 HealthChecker
```

如果类型没有实现接口，编译器会报错。这是 Go 社区的最佳实践。

### 10. 接口在什么时候应该返回指针类型？什么时候返回值类型？

**答：** 这取决于语义：
- **返回指针**：当调用者需要修改状态、或类型很大拷贝开销高时
- **返回值**：当返回的是不可变数据、或类型很小时

通常接口方法的接收者决定了行为：如果实现用了指针接收者，接口变量通常存指针。

---

## 📚 深入阅读

- [Go 官方博客：Interface](https://go.dev/doc/effective_go#interfaces) — Effective Go 接口章节
- [Go Data Structures: Interfaces](https://research.swtch.com/interfaces) — Russ Cox 详解接口底层
- [io 包文档](https://pkg.go.dev/io) — 标准库 io 包完整文档
- [《Go 语言圣经》第 7 章](https://books.studygolang.com/gopl-zh/ch7/ch7.html) — 接口详解
- [Go Proverbs](https://go-proverbs.github.io/) — Go 设计哲学
- [The Power of Go: Interfaces](https://bitfieldconsulting.com/books/interfaces) — 接口设计实战

---

## ✅ 自检清单

- [ ] 能解释 Go 接口的隐式实现机制和底层 iface/eface 结构
- [ ] 能正确使用类型断言和类型 switch，避免 nil 接口陷阱
- [ ] 能设计小而精的接口，遵循依赖反转原则
- [ ] 理解结构体嵌入的提升规则和同名冲突处理
- [ ] 能使用 io.Reader/Writer 构建数据处理管道
- [ ] 能为 SRE 场景设计可插拔的通知系统或存储后端
- [ ] 理解接口动态派发的性能影响和优化策略
- [ ] 能通过编译时断言检查接口实现
