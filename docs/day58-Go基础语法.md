# Day 58: Go 基础语法深度解析

> 📅 日期：2026-05-02
> 📖 学习主题：Go 基础语法
> ⏰ 计划学习时间：3-4 小时

---

## 🎯 学习目标

- 掌握 Go 变量声明的多种方式与零值机制
- 理解 Go 控制流语句的细微差别
- 掌握数组、切片、map 的区别与使用场景
- 理解指针在 Go 中的简化使用方式

---

## 📖 详细知识点

### 1. 变量声明与类型系统

#### 1.1 变量声明的四种方式

```go
package main

import "fmt"

func main() {
    // 方式 1：var 声明（零值初始化）
    var count int          // 零值：0
    var name string        // 零值：""
    var active bool        // 零值：false
    var ptr *int           // 零值：nil
    var slice []int        // 零值：nil（不是空切片！）
    var m map[string]int   // 零值：nil

    // 方式 2：var 带初始化
    var count2 int = 10
    var name2 string = "sre"

    // 方式 3：类型推断
    var count3 = 10        // 推断为 int
    var name3 = "sre"      // 推断为 string
    var ratio = 0.95       // 推断为 float64

    // 方式 4：短变量声明（仅限函数体内）
    count4 := 10
    name4 := "sre"

    // 多变量声明
    var a, b, c int = 1, 2, 3
    x, y, z := 10, 20, 30

    // 批量声明
    var (
        host    = "10.0.1.10"
        port    = 8080
        timeout = 30
    )

    // 多重赋值与交换
    a, b = b, a

    // 空白标识符 _ 用于忽略不需要的值
    _, err := fmt.Println("hello")
    if err != nil {
        // 处理错误
    }

    fmt.Println(count, name, active, ptr)
}
```

#### 1.2 零值机制

Go 中所有类型都有零值，声明变量时自动初始化为零值：

| 类型 | 零值 | 说明 |
|------|------|------|
| bool | false | - |
| 整数 | 0 | int, int8, int16, int32, int64, uint 等 |
| 浮点 | 0.0 | float32, float64 |
| 字符串 | "" | 空字符串 |
| 指针 | nil | - |
| 切片 | nil | 与空切片 []T{} 不同 |
| map | nil | 必须先 make 才能写入 |
| channel | nil | 必须先 make 才能使用 |
| 函数 | nil | - |
| 接口 | nil | 类型和值都是 nil |
| struct | 各字段零值 | 递归应用 |

**nil 切片的坑：**
```go
// nil 切片
var s []int
fmt.Println(s == nil)  // true
s = append(s, 1)       // 可以 append，会自动分配底层数组

// 空切片
s2 := []int{}
fmt.Println(s2 == nil) // false
s2 = append(s2, 1)     // 同样可以 append

// nil map — 写入会 panic！
var m map[string]int
m["key"] = 1           // panic: assignment to entry in nil map
m2 := make(map[string]int)
m2["key"] = 1          // OK
```

#### 1.3 类型系统与转换

```go
// Go 是强类型语言，不同类型不能直接运算
var a int = 10
var b int32 = 20
// c := a + b  // 编译错误！

// 必须显式转换
c := a + int(b)

// 数值类型转换（可能丢失精度）
var x float64 = 3.14
var y int = int(x)  // y = 3（截断，不是四舍五入）

// 常量没有默认类型
const Pi = 3.14159          // 无类型常量
var radius float64 = 10
var area = Pi * radius * radius  // 自动推断为 float64

// 类型别名（Go 1.9+）
type StatusCode int
type Hostname string

// 结构体嵌入（组合而非继承）
type Server struct {
    Name    string
    IP      string
    Port    int
}

type WebServer struct {
    Server           // 嵌入 Server，提升字段和方法
    CertPath string
    VHosts   []string
}

ws := WebServer{
    Server: Server{Name: "web-01", IP: "10.0.1.10", Port: 443},
    CertPath: "/etc/ssl/cert.pem",
}
fmt.Println(ws.Name)     // 访问嵌入字段
fmt.Println(ws.IP)       // 等价于 ws.Server.IP
```

### 2. 控制流

#### 2.1 if-else 语句

```go
// 基本形式
func checkCPU(cpu float64) string {
    if cpu > 90 {
        return "CRITICAL"
    } else if cpu > 70 {
        return "WARNING"
    } else {
        return "OK"
    }
}

// if 带初始化语句（推荐用法）
func getHostStatus(hostname string) (string, error) {
    if host, err := lookupHost(hostname); err != nil {
        return "", fmt.Errorf("lookup failed: %w", err)
    } else if !host.IsHealthy {
        return "UNHEALTHY", nil
    } else {
        return "HEALTHY", nil
    }
}

// SRE 实战：阈值检查
type Threshold struct {
    Warning  float64
    Critical float64
}

func (t Threshold) Check(value float64) string {
    if value >= t.Critical {
        return "CRITICAL"
    }
    if value >= t.Warning {
        return "WARNING"
    }
    return "OK"
}
```

#### 2.2 for 循环

Go 只有 for 一种循环结构，但可以模拟其他语言的各种循环：

```go
// 经典 C 风格
for i := 0; i < 10; i++ {
    fmt.Println(i)
}

// while 风格
count := 0
for count < 5 {
    fmt.Println(count)
    count++
}

// 无限循环
for {
    // 监控循环
    time.Sleep(10 * time.Second)
    checkHealth()
}

// range 遍历切片
servers := []string{"web-01", "web-02", "db-01"}
for i, server := range servers {
    fmt.Printf("[%d] %s\n", i, server)
}

// range 遍历 map（顺序不保证！）
metrics := map[string]float64{"cpu": 85.2, "mem": 72.1}
for key, value := range metrics {
    fmt.Printf("%s: %.1f%%\n", key, value)
}

// range 遍历字符串（按 rune 迭代）
for i, ch := range "监控" {
    fmt.Printf("index: %d, char: %c\n", i, ch)
}

// 只关心索引或值
for i := range servers { /* 只需索引 */ }
for _, v := range servers { /* 只需值 */ }

// continue 和 break
for i := 0; i < 100; i++ {
    if i%2 == 0 {
        continue  // 跳过偶数
    }
    if i > 50 {
        break     // 超过 50 退出
    }
    fmt.Println(i)
}

// 带标签的 break（跳出嵌套循环）
Outer:
for i := 0; i < 10; i++ {
    for j := 0; j < 10; j++ {
        if i+j > 15 {
            break Outer  // 跳出外层循环
        }
    }
}
```

#### 2.3 switch 语句

```go
// 基本 switch
func statusColor(status string) string {
    switch status {
    case "OK":
        return "green"
    case "WARNING":
        return "yellow"
    case "CRITICAL":
        return "red"
    default:
        return "grey"
    }
}

// 无表达式 switch（替代 if-else 链）
func checkServer(cpu, mem float64) string {
    switch {
    case cpu > 95 || mem > 95:
        return "CRITICAL"
    case cpu > 80 || mem > 80:
        return "WARNING"
    case cpu > 60 || mem > 60:
        return "INFO"
    default:
        return "OK"
    }
}

// fallthrough（Go 的 case 默认 break）
switch n := 2; n {
case 1:
    fmt.Println("one")
    fallthrough
case 2:
    fmt.Println("two")
    fallthrough
case 3:
    fmt.Println("three")
}
// 输出: two → three
```

### 3. 指针

Go 的指针比 C 简化很多：没有指针运算，只有取地址 `&` 和解引用 `*`。

```go
package main

import "fmt"

func main() {
    x := 42
    p := &x           // p 是指向 int 的指针
    fmt.Println(*p)   // 42 — 解引用
    *p = 100          // 修改 x 的值
    fmt.Println(x)    // 100

    // 指针的零值是 nil
    var ptr *int
    fmt.Println(ptr == nil) // true
}

// 指针作为函数参数 — 允许函数修改外部变量
func increment(n *int) {
    *n++
}

func swap(a, b *int) {
    *a, *b = *b, *a
}

// SRE 实战：用指针避免结构体拷贝
type Config struct {
    Timeout    int
    Retries    int
    Endpoints  []string
}

// 值传递 — 会拷贝整个结构体
func processConfig(c Config) {
    c.Timeout = 60  // 不影响原始值
}

// 指针传递 — 只传递指针（8 字节）
func updateConfig(c *Config) {
    c.Timeout = 60  // 修改原始值
}
```

### 4. 常量与 iota

```go
// 常量在编译时求值，不能是运行时计算结果
const Pi = 3.14159
const MaxRetries = 3
const ServerURL = "https://monitor.sre.internal"

// iota — 自动递增的常量生成器
const (
    StatusOK = iota       // 0
    StatusWarning          // 1
    StatusCritical         // 2
    StatusUnknown          // 3
)

// 位运算常量（常见于权限标志）
const (
    Read  = 1 << iota     // 0001 = 1
    Write                 // 0010 = 2
    Execute               // 0100 = 4
    Admin                 // 1000 = 8
)

// SRE 实战：告警级别
const (
    LevelDebug = iota
    LevelInfo
    LevelWarning
    LevelError
    LevelCritical
    LevelFatal
)

func (l int) String() string {
    return []string{"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "FATAL"}[l]
}
```

### 5. SRE 实战：服务健康检查器

```go
package main

import (
    "fmt"
    "math/rand"
    "time"
)

type HealthStatus int

const (
    HealthUnknown HealthStatus = iota
    HealthOK
    HealthDegraded
    HealthDown
)

func (h HealthStatus) String() string {
    return []string{"UNKNOWN", "OK", "DEGRADED", "DOWN"}[h]
}

func (h HealthStatus) Emoji() string {
    return []string{"⚪", "🟢", "🟡", "🔴"}[h]
}

type Service struct {
    Name        string
    Endpoint    string
    Status      HealthStatus
    LastCheck   time.Time
    ResponseMs  int
}

func checkService(svc *Service) {
    // 模拟网络请求
    latency := rand.Intn(500) + 50
    svc.LastCheck = time.Now()
    svc.ResponseMs = latency

    switch {
    case latency > 400:
        svc.Status = HealthDown
    case latency > 200:
        svc.Status = HealthDegraded
    default:
        svc.Status = HealthOK
    }
}

func main() {
    services := []*Service{
        {Name: "api-gateway", Endpoint: "http://api.internal:8080/health"},
        {Name: "user-service", Endpoint: "http://user.internal:8081/health"},
        {Name: "db-primary", Endpoint: "tcp://db.internal:3306"},
    }

    fmt.Println("=== SRE Service Health Dashboard ===")
    fmt.Printf("%-20s %-8s %-8s %-10s\n", "Service", "Status", "Latency", "Last Check")
    fmt.Println("------------------------------------------------------------")

    for _, svc := range services {
        checkService(svc)
        fmt.Printf("%-20s %-8s %-8dms %-10s\n",
            svc.Name,
            svc.Status.Emoji()+" "+svc.Status.String(),
            svc.ResponseMs,
            svc.LastCheck.Format("15:04:05"),
        )
    }
}
```

---

## 💻 实战练习

### 练习 1：变量类型推断

声明以下变量并打印类型和值：主机名字符串、端口号整数、超时时间浮点数、是否启用布尔值、标签映射。

<details>
<summary>参考答案</summary>

```go
hostname := "sre-monitor-01"
port := 9090
timeout := 30.5
enabled := true
labels := map[string]string{"env": "prod", "team": "infra"}
fmt.Printf("%T: %v\n", hostname, hostname)
fmt.Printf("%T: %v\n", port, port)
```
</details>

### 练习 2：阈值分级函数

编写函数，输入 CPU 使用率，返回告警级别：>90 CRITICAL, >70 WARNING, >50 INFO, 其余 OK。

<details>
<summary>参考答案</summary>

```go
func cpuAlertLevel(cpu float64) string {
    switch {
    case cpu > 90: return "CRITICAL"
    case cpu > 70: return "WARNING"
    case cpu > 50: return "INFO"
    default: return "OK"
    }
}
```
</details>

### 练习 3：用 iota 定义日志级别

定义 DEBUG/INFO/WARNING/ERROR/CRITICAL 五个常量，并为每个级别添加 String() 方法。

<details>
<summary>参考答案</summary>

```go
type LogLevel int
const (
    DEBUG LogLevel = iota
    INFO
    WARNING
    ERROR
    CRITICAL
)
func (l LogLevel) String() string {
    names := []string{"DEBUG","INFO","WARNING","ERROR","CRITICAL"}
    return names[l]
}
```
</details>

---

## 📚 扩展阅读

- [Go 语言规范](https://go.dev/ref/spec) — 官方语言规范
- [Effective Go](https://go.dev/doc/effective_go) — Go 官方编程风格指南
- [Go by Example](https://gobyexample.com/) — 交互式语法教程
- [《Go 语言圣经》](https://github.com/gopl-zh/gopl-zh.github.com) — 经典教材中文版

---

## 📝 笔记

### 延伸思考

- 为什么 Go 只有 for 一种循环？这种设计带来了什么好处？
- nil 切片和空切片的区别在什么场景下会产生实际影响？
- Go 不支持隐式类型转换是好事还是坏事？

---

## ✅ 完成检查

- [ ] 理解四种变量声明方式的使用场景
- [ ] 掌握各类型的零值，特别是 nil 切片的陷阱
- [ ] 能熟练使用 if 带初始化语句
- [ ] 掌握 switch 的多种用法（含 fallthrough）
- [ ] 理解指针的基本操作和作为函数参数的意义
- [ ] 能用 iota 定义一组相关常量

---

*由 SRE 学习计划自动生成 | 2026-05-02*
