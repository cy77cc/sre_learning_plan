# Day 58: Go 基础语法深度解析

> 📅 日期：2026-05-03
> 📖 学习主题：变量/常量/类型、控制流、数组/切片/映射、字符串处理、指针、iota、自定义类型
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 57 (Go 环境搭建)

## 🎯 学习目标

- 掌握 Go 变量声明的多种方式与零值机制
- 深入理解切片和映射的内部实现（高频面试题）
- 掌握 Go 控制流语句的细微差别和最佳实践
- 理解指针在 Go 中的简化使用方式
- 掌握 iota 和自定义类型的惯用模式

## 📖 核心知识点

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

    fmt.Println(count, name, active, ptr, slice, m)
    fmt.Println(count2, name2, count3, name3, ratio)
    fmt.Println(count4, name4, a, b, c, x, y, z)
    fmt.Println(host, port, timeout, err)
}
```

**声明方式选择指南：**

| 场景 | 推荐方式 | 理由 |
|------|---------|------|
| 包级变量 | `var x Type` | 明确类型，零值语义清晰 |
| 函数内已知值 | `x := value` | 简洁，类型推断 |
| 需要特定类型 | `var x Type = value` | 控制类型（如 int32 vs int64） |
| 多变量批量 | `var (...)` 块 | 结构化，可读性好 |

#### 1.2 零值机制 — Go 的安全网

Go 中所有类型都有零值，声明变量时自动初始化为零值。这是 Go 的重要设计决策，避免了未初始化变量带来的未定义行为。

```
┌─────────────────────────────────────────────────────────────┐
│                     Go 零值全景图                            │
├──────────────────┬──────────────────────────────────────────┤
│ 类型             │ 零值                                      │
├──────────────────┼──────────────────────────────────────────┤
│ bool             │ false                                    │
│ 整数             │ 0 (int, int8, int16, int32, int64, uint) │
│ 浮点             │ 0.0 (float32, float64)                   │
│ 字符串           │ "" (空字符串)                             │
│ 指针             │ nil                                      │
│ 切片             │ nil (与空切片 []T{} 不同！)               │
│ map              │ nil (必须先 make 才能写入！)              │
│ channel          │ nil (必须先 make 才能使用！)              │
│ 函数             │ nil                                      │
│ 接口             │ nil (类型和值都是 nil)                    │
│ struct           │ 各字段零值（递归应用）                    │
│ error            │ nil                                      │
└──────────────────┴──────────────────────────────────────────┘
```

**nil 切片 vs 空切片 — 高频面试题：**

```go
package main

import "fmt"

func main() {
    // nil 切片 — 未分配底层数组
    var s1 []int
    fmt.Println(s1 == nil)    // true
    fmt.Println(len(s1))      // 0
    fmt.Println(cap(s1))      // 0
    s1 = append(s1, 1)        // 可以 append，会自动分配底层数组

    // 空切片 — 已分配底层数组（长度为 0）
    s2 := []int{}
    fmt.Println(s2 == nil)    // false
    fmt.Println(len(s2))      // 0
    fmt.Println(cap(s2))      // 0
    s2 = append(s2, 1)        // 同样可以 append

    // 用 make 创建的空切片
    s3 := make([]int, 0)
    fmt.Println(s3 == nil)    // false
    fmt.Println(len(s3))      // 0

    // JSON 序列化时的区别
    // nil 切片 → null
    // 空切片 → []
    // 这在 API 设计中非常重要！

    // nil map — 读取返回零值，写入会 panic！
    var m1 map[string]int
    fmt.Println(m1["key"])    // 0（零值，不 panic）
    // m1["key"] = 1          // panic: assignment to entry in nil map

    // 正确的 map 初始化
    m2 := make(map[string]int)
    m2["key"] = 1             // OK

    // nil channel — 发送和接收都会永久阻塞！
    var ch chan int
    // ch <- 1                // 永久阻塞
    // <-ch                   // 永久阻塞
    close(ch)                 // panic: close of nil channel
}
```

#### 1.3 类型系统与转换

```go
package main

import "fmt"

func main() {
    // Go 是强类型语言，不同类型不能直接运算
    var a int = 10
    var b int32 = 20
    // c := a + b  // 编译错误！不同类型不能运算

    // 必须显式转换
    c := a + int(b)
    fmt.Println(c) // 30

    // 数值类型转换（可能丢失精度）
    var x float64 = 3.14
    var y int = int(x)  // y = 3（截断，不是四舍五入）
    fmt.Println(y)

    // 常量没有默认类型
    const Pi = 3.14159          // 无类型常量
    var radius float64 = 10
    var area = Pi * radius * radius  // 自动推断为 float64

    // 字符串和字节切片的转换
    s := "Hello, SRE!"
    b := []byte(s)   // string -> []byte
    s2 := string(b)  // []byte -> string
    fmt.Println(s2)

    // 类型断言（接口类型转具体类型）
    var i interface{} = "hello"
    str, ok := i.(string)
    if ok {
        fmt.Println(str) // "hello"
    }
}
```

**为什么 Go 不支持隐式类型转换？**

```
Go 的设计哲学：显式优于隐式

┌────────────────────────────────────────────────────────────┐
│  隐式类型转换的陷阱（C/C++ 示例）：                         │
│                                                            │
│  int a = -1;                                               │
│  unsigned int b = 1;                                       │
│  if (a < b) { /* 这个条件可能是 false！*/ }                │
│  // 因为 -1 被隐式转为 unsigned，变成 4294967295            │
│                                                            │
│  Go 的做法：                                               │
│  var a int = -1                                            │
│  var b uint = 1                                            │
│  // if a < b { }  // 编译错误！必须显式转换                 │
│  if a < int(b) { } // 明确表达意图                         │
│                                                            │
│  这避免了数值溢出、精度丢失等隐蔽 bug                      │
└────────────────────────────────────────────────────────────┘
```

### 2. 常量与 iota

#### 2.1 常量基础

```go
package main

import "fmt"

// 常量在编译时求值，不能是运行时计算结果
const Pi = 3.14159
const MaxRetries = 3
const ServerURL = "https://monitor.sre.internal"

// 批量声明常量
const (
    StatusOK       = 200
    StatusNotFound = 404
    StatusError    = 500
)

// 无类型常量 — 编译器自动推断类型
const (
    MaxInt  = 1<<63 - 1          // 可以是任意大的整数
    BigFloat = 1e1000            // 可以是任意大的浮点数
)

// 类型常量
const (
    TypedMaxInt int64 = 1<<63 - 1  // 有明确类型
)
```

#### 2.2 iota — 自动递增的常量生成器

```go
package main

import "fmt"

// iota 在 const 块中从 0 开始递增
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

// iota 跳值
const (
    _  = iota  // 0，忽略
    KB = 1 << (10 * iota)  // 1 << 10 = 1024
    MB                      // 1 << 20 = 1048576
    GB                      // 1 << 30 = 1073741824
    TB                      // 1 << 40
)

// iota 表达式
const (
    _  = iota             // 0
    a  = iota * 10        // 10
    b                     // 20（表达式 iota * 10 继续）
    c                     // 30
)

// SRE 实战：告警级别
type AlertLevel int

const (
    LevelDebug AlertLevel = iota
    LevelInfo
    LevelWarning
    LevelError
    LevelCritical
    LevelFatal
)

func (l AlertLevel) String() string {
    names := [...]string{
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "FATAL",
    }
    if l < LevelDebug || l > LevelFatal {
        return "UNKNOWN"
    }
    return names[l]
}

// SRE 实战：时间段枚举
type TimeRange int

const (
    Range1h TimeRange = iota
    Range6h
    Range24h
    Range7d
    Range30d
)

func (t TimeRange) Duration() string {
    durations := [...]string{"1h", "6h", "24h", "7d", "30d"}
    if t < Range1h || t > Range30d {
        return "unknown"
    }
    return durations[t]
}

func main() {
    fmt.Println(StatusOK, StatusWarning, StatusCritical, StatusUnknown)
    fmt.Printf("Read=%b Write=%b Execute=%b Admin=%b\n", Read, Write, Execute, Admin)
    fmt.Println(KB, MB, GB, TB)
    fmt.Println(a, b, c)

    level := LevelWarning
    fmt.Printf("Alert level: %s (%d)\n", level, level)

    r := Range24h
    fmt.Printf("Time range: %s\n", r.Duration())
}
```

**iota 的设计哲学：**

```
iota 的本质是一个在 const 块中自动递增的计数器

const (              iota 值
    A = iota          // 0
    B                 // 1  （自动递增）
    C                 // 2
    D = "hello"       // "hello" （表达式变了，但 iota 仍然递增）
    E                 // "hello" （沿用上一个表达式）
    F = iota          // 5  （注意：是 5，不是 3！）
)

// iota 的值取决于它在 const 块中的位置（从 0 开始）
// 而不是上一个使用 iota 的常量
```

### 3. 控制流

#### 3.1 if-else 语句

```go
package main

import "fmt"

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

// if 带初始化语句（Go 特色，推荐用法）
func getConfig(path string) (string, error) {
    // data 和 err 的作用域仅在 if-else 块内
    if data, err := os.ReadFile(path); err != nil {
        return "", fmt.Errorf("read config: %w", err)
    } else {
        return string(data), nil
    }
}

// SRE 实战：阈值检查
type Threshold struct {
    Warning  float64
    Critical float64
}

func (t Threshold) Check(value float64) string {
    // 提前返回模式（guard clause），避免深层嵌套
    if value >= t.Critical {
        return "CRITICAL"
    }
    if value >= t.Warning {
        return "WARNING"
    }
    return "OK"
}

func main() {
    fmt.Println(checkCPU(95.5))  // CRITICAL
    fmt.Println(checkCPU(75.0))  // WARNING
    fmt.Println(checkCPU(50.0))  // OK

    t := Threshold{Warning: 70, Critical: 90}
    fmt.Println(t.Check(95))     // CRITICAL
    fmt.Println(t.Check(75))     // WARNING
    fmt.Println(t.Check(50))     // OK
}
```

#### 3.2 for 循环 — Go 的唯一循环结构

```go
package main

import "fmt"

func main() {
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

    // 无限循环（SRE 监控常用）
    for {
        // 监控循环
        // time.Sleep(10 * time.Second)
        // checkHealth()
        break // 示例中跳出
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
}
```

**Go 1.22 for-range 变量语义修正（重要！）：**

```go
// Go 1.21 及之前：range 循环变量是同一个变量，循环体中的闭包捕获的是同一个变量
// Go 1.22 之后：每次迭代创建新变量

// Go 1.21 的经典 bug：
funcs := make([]func(), 5)
for i := range funcs {
    // Go 1.21：所有闭包共享同一个 i，最终都是 4
    // Go 1.22：每次迭代创建新 i，分别是 0, 1, 2, 3, 4
    funcs[i] = func() { fmt.Println(i) }
}
for _, f := range funcs {
    f()
}
// Go 1.21 输出：4 4 4 4 4
// Go 1.22 输出：0 1 2 3 4

// Go 1.21 的修复方式（现在不需要了）：
for i := range funcs {
    i := i // 重新声明，创建新变量
    funcs[i] = func() { fmt.Println(i) }
}
```

#### 3.3 switch 语句

```go
package main

import "fmt"

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

// 无表达式 switch（替代 if-else 链，更清晰）
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

// 多值匹配
func httpStatusText(code int) string {
    switch code {
    case 200, 201, 204:
        return "Success"
    case 301, 302:
        return "Redirect"
    case 400, 422:
        return "Client Error"
    case 401, 403:
        return "Unauthorized"
    case 500, 502, 503:
        return "Server Error"
    default:
        return "Unknown"
    }
}

// fallthrough（Go 的 case 默认 break）
func describeNumber(n int) {
    switch {
    case n > 0:
        fmt.Print("positive ")
        fallthrough
    case n%2 == 0:
        fmt.Print("even ")
        fallthrough
    default:
        fmt.Println("number:", n)
    }
}

// type switch（类型断言的 switch 形式）
func describeValue(v interface{}) string {
    switch v := v.(type) {
    case int:
        return fmt.Sprintf("int: %d", v)
    case string:
        return fmt.Sprintf("string: %s", v)
    case bool:
        return fmt.Sprintf("bool: %v", v)
    case nil:
        return "nil"
    default:
        return fmt.Sprintf("unknown: %T", v)
    }
}

func main() {
    fmt.Println(statusColor("OK"))           // green
    fmt.Println(checkServer(85, 60))         // WARNING
    fmt.Println(httpStatusText(502))         // Server Error
    describeNumber(4)                        // positive even number: 4
    fmt.Println(describeValue("hello"))      // string: hello
    fmt.Println(describeValue(42))           // int: 42
}
```

### 4. 数组

```go
package main

import "fmt"

func main() {
    // 数组是值类型，长度是类型的一部分
    var a1 [5]int                    // [0 0 0 0 0]
    a2 := [5]int{1, 2, 3, 4, 5}     // [1 2 3 4 5]
    a3 := [...]int{1, 2, 3}          // 编译器推断长度为 3
    a4 := [5]int{1: 10, 3: 30}       // 指定索引初始化 [0 10 0 30 0]

    // 数组是值类型，赋值和传参会复制整个数组
    b := a2
    b[0] = 100
    fmt.Println(a2[0]) // 1，原数组不变
    fmt.Println(b[0])  // 100

    // [3]int 和 [4]int 是不同的类型！
    // var c [4]int = a3  // 编译错误

    // 多维数组
    matrix := [3][3]int{
        {1, 2, 3},
        {4, 5, 6},
        {7, 8, 9},
    }

    // 遍历
    for i, row := range matrix {
        for j, val := range row {
            fmt.Printf("[%d][%d]=%d ", i, j, val)
        }
        fmt.Println()
    }

    fmt.Println(a1, a2, a3, a4)
}
```

**为什么 Go 中很少直接使用数组？**

```
数组的限制：
1. 长度是类型的一部分 — [3]int 和 [4]int 是不同类型
2. 不能用变量指定长度（除非用泛型）
3. 值类型 — 赋值和传参会复制整个数组
4. 不能追加元素

实际开发中几乎总是使用切片（slice）：
- 切片是数组的视图
- 长度可变
- 传参高效（只传指针+长度+容量）
```

### 5. 切片（Slice）— Go 最重要的数据结构

#### 5.1 切片的内部实现

```
切片的内部结构（runtime/slice.go）：

type slice struct {
    array unsafe.Pointer  // 指向底层数组的指针
    len   int             // 切片的长度（当前元素数）
    cap   int             // 切片的容量（底层数组的总容量）
}

切片的内存布局：

    slice header (24 bytes on 64-bit)
    ┌──────────────┬───────┬───────┐
    │  array ptr   │  len  │  cap  │
    │  8 bytes     │ 8 bytes│ 8 bytes│
    └──────┬───────┴───────┴───────┘
           │
           ▼
    底层数组：
    ┌────┬────┬────┬────┬────┬────┬────┬────┐
    │ 10 │ 20 │ 30 │ 40 │ 50 │    │    │    │
    └────┴────┴────┴────┴────┴────┴────┴────┘
     [0]  [1]  [2]  [3]  [4]  [5]  [6]  [7]
     ◄───────── len=5 ──────────►◄── cap=8 ──►

切片操作：
    s := []int{10, 20, 30, 40, 50}

    s[1:3]  →  [20, 30]        底层数组共享，len=2, cap=4
    s[:3]   →  [10, 20, 30]    len=3, cap=8
    s[2:]   →  [30, 40, 50]    len=3, cap=6
    s[:]    →  [10,20,30,40,50] len=5, cap=8
```

#### 5.2 切片的创建与操作

```go
package main

import "fmt"

func main() {
    // 创建切片的三种方式

    // 方式 1：字面量
    s1 := []int{1, 2, 3, 4, 5}

    // 方式 2：make
    s2 := make([]int, 5)         // len=5, cap=5, 值为 [0 0 0 0 0]
    s3 := make([]int, 3, 10)     // len=3, cap=10, 值为 [0 0 0]

    // 方式 3：从数组或切片派生
    arr := [5]int{10, 20, 30, 40, 50}
    s4 := arr[1:4]               // [20, 30, 40], len=3, cap=4

    // append — 追加元素
    s1 = append(s1, 6)           // [1, 2, 3, 4, 5, 6]
    s1 = append(s1, 7, 8, 9)     // [1, 2, 3, 4, 5, 6, 7, 8, 9]

    // append 切片
    s5 := []int{100, 200}
    s1 = append(s1, s5...)       // 展开切片

    // copy — 复制切片
    src := []int{1, 2, 3, 4, 5}
    dst := make([]int, len(src))
    n := copy(dst, src)          // n=5

    // 删除元素（Go 没有内置的删除函数）
    // 删除索引 i 的元素
    s := []int{1, 2, 3, 4, 5}
    i := 2  // 删除索引 2
    s = append(s[:i], s[i+1:]...)  // [1, 2, 4, 5]

    // 切片比较（不能用 ==，除了与 nil 比较）
    // fmt.Println(s1 == s2)  // 编译错误
    fmt.Println(s1 == nil)      // 可以与 nil 比较

    // 使用 slices.Equal（Go 1.21+）比较切片
    // import "slices"
    // slices.Equal(s1, s2)    // true/false

    fmt.Println(s1, s2, s3, s4, s5, dst, n, s)
}
```

#### 5.3 append 的扩容机制（高频面试题）

```
append 扩容流程：

    s := make([]int, 3, 5)  // len=3, cap=5
    ┌────┬────┬────┬────┬────┐
    │ 0  │ 0  │ 0  │    │    │
    └────┴────┴────┴────┴────┘
     [0]  [1]  [2]  [3]  [4]

    s = append(s, 1)
    ┌────┬────┬────┬────┬────┐
    │ 0  │ 0  │ 0  │ 1  │    │  len=4, cap=5
    └────┴────┴────┴────┴────┘

    s = append(s, 2)
    ┌────┬────┬────┬────┬────┐
    │ 0  │ 0  │ 0  │ 1  │ 2  │  len=5, cap=5
    └────┴────┴────┴────┴────┘

    s = append(s, 3)  // 容量不足，触发扩容！
    ┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
    │ 0  │ 0  │ 0  │ 1  │ 2  │ 3  │    │    │    │    │
    └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
    新底层数组：len=6, cap=10（扩容为原来的 2 倍）

Go 1.21+ 扩容策略（runtime/slice.go）：
    1. 如果新容量 > 旧容量的 2 倍，直接使用新容量
    2. 如果旧容量 < 256，新容量 = 旧容量 * 2
    3. 如果旧容量 >= 256，新容量 = 旧容量 * 1.25 + 192
    4. 对齐到内存分配器的 size class

重要：append 可能返回新的切片（底层数组改变）！
所以必须用 s = append(s, x)，而不是 append(s, x)
```

**切片扩容的性能陷阱：**

```go
// 反模式：循环中反复 append，导致多次扩容
func badExample() []int {
    var s []int
    for i := 0; i < 10000; i++ {
        s = append(s, i)  // 可能多次扩容
    }
    return s
}

// 最佳实践：预分配容量
func goodExample() []int {
    s := make([]int, 0, 10000)  // 一次性分配
    for i := 0; i < 10000; i++ {
        s = append(s, i)  // 不会触发扩容
    }
    return s
}
```

#### 5.4 切片的陷阱：共享底层数组

```go
package main

import "fmt"

func main() {
    // 陷阱 1：子切片修改影响原切片
    s := []int{1, 2, 3, 4, 5}
    sub := s[1:3]  // [2, 3]，与 s 共享底层数组
    sub[0] = 200
    fmt.Println(s)   // [1, 200, 3, 4, 5] — s 也被修改了！

    // 陷阱 2：append 可能覆盖原切片的数据
    s2 := []int{1, 2, 3, 4, 5}
    sub2 := s2[1:3:3]  // [2, 3]，len=2, cap=2（限制了容量）
    sub2 = append(sub2, 300)  // 容量不足，分配新数组
    fmt.Println(s2)  // [1, 2, 3, 4, 5] — s2 未被修改

    // 陷阱 3：如果不限制容量，append 会覆盖后续元素
    s3 := []int{1, 2, 3, 4, 5}
    sub3 := s3[1:3]  // [2, 3]，len=2, cap=4（剩余容量）
    sub3 = append(sub3, 300)  // 有足够容量，直接写入
    fmt.Println(s3)  // [1, 2, 3, 300, 5] — s3[3] 被覆盖了！

    // 安全做法：三索引切片 [low:high:max]
    s4 := []int{1, 2, 3, 4, 5}
    sub4 := s4[1:3:3]  // len=2, cap=2（max=3 限制了 cap）
    // sub4 = append(sub4, 300)  // 会分配新数组，不影响 s4
}

// 安全复制子切片
func safeSubslice(s []int, start, end int) []int {
    result := make([]int, end-start)
    copy(result, s[start:end])
    return result
}
```

### 6. 映射（Map）

#### 6.1 Map 的内部实现

```
Map 的内部结构（runtime/map.go）：

    ┌─────────────────────────────────────────────────┐
    │  hmap 结构体                                     │
    │  ├── count     int    // 元素数量                │
    │  ├── B         uint8  // 桶数量的对数（2^B 个桶）│
    │  ├── buckets   unsafe.Pointer // 桶数组指针      │
    │  ├── oldbuckets unsafe.Pointer // 扩容时的旧桶   │
    │  └── overflow  ...    // 溢出桶管理              │
    └─────────────────────────────────────────────────┘

    每个桶（bmap）存储 8 个键值对：

    bucket:
    ┌───────────────────────────────────────┐
    │ tophash[8]  // 每个 key 的哈希高 8 位 │
    │ key[8]      // 8 个 key               │
    │ value[8]    // 8 个 value             │
    │ overflow    // 溢出桶指针             │
    └───────────────────────────────────────┘

    查找流程：
    1. 计算 key 的哈希值
    2. 用哈希值的低 B 位定位桶
    3. 用哈希值的高 8 位（tophash）在桶内快速筛选
    4. 找到 tophash 匹配的槽位，比较完整的 key
    5. 返回对应的 value

    扩容条件：
    - 负载因子 > 6.5（count / 2^B）→ 翻倍扩容
    - 溢出桶过多 → 等量扩容（整理碎片）
```

#### 6.2 Map 操作

```go
package main

import (
    "fmt"
    "sort"
)

func main() {
    // 创建 map
    m1 := map[string]int{"a": 1, "b": 2}
    m2 := make(map[string]int)
    m3 := make(map[string]int, 100)  // 预分配空间

    // 添加/修改
    m2["cpu"] = 85
    m2["mem"] = 72
    m2["disk"] = 45

    // 读取
    cpu := m2["cpu"]

    // 读取并检查 key 是否存在（comma ok 模式）
    val, ok := m2["gpu"]
    if !ok {
        fmt.Println("gpu not found")
    }

    // 删除
    delete(m2, "disk")

    // 遍历（顺序不保证！）
    for k, v := range m2 {
        fmt.Printf("%s: %d\n", k, v)
    }

    // 有序遍历 map（需要手动排序 keys）
    keys := make([]string, 0, len(m2))
    for k := range m2 {
        keys = append(keys, k)
    }
    sort.Strings(keys)
    for _, k := range keys {
        fmt.Printf("%s: %d\n", k, m2[k])
    }

    // len() 获取元素数量
    fmt.Println(len(m2))

    // nil map 的行为
    var nilMap map[string]int
    fmt.Println(nilMap["key"])    // 0（零值，不 panic）
    // nilMap["key"] = 1         // panic: assignment to entry in nil map
    delete(nilMap, "key")         // 安全，不 panic
    fmt.Println(len(nilMap))      // 0

    // map 的 key 类型限制：
    // 可以用作 key 的类型：bool, int, float, string, pointer, channel,
    //                     interface, array, struct（如果所有字段可比较）
    // 不可以用作 key 的类型：slice, map, func

    fmt.Println(m1, m3, cpu, val, ok)
}
```

#### 6.3 Map 的并发安全

```go
package main

import (
    "fmt"
    "sync"
)

// Map 不是并发安全的！并发读写会 panic

// 方案 1：sync.Mutex（适合读写均衡的场景）
type SafeMap struct {
    mu sync.Mutex
    m  map[string]int
}

func (s *SafeMap) Get(key string) (int, bool) {
    s.mu.Lock()
    defer s.mu.Unlock()
    val, ok := s.m[key]
    return val, ok
}

func (s *SafeMap) Set(key string, value int) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.m[key] = value
}

// 方案 2：sync.RWMutex（适合读多写少的场景）
type RWMap struct {
    mu sync.RWMutex
    m  map[string]int
}

func (r *RWMap) Get(key string) (int, bool) {
    r.mu.RLock()         // 读锁，允许并发读
    defer r.mu.RUnlock()
    val, ok := r.m[key]
    return val, ok
}

func (r *RWMap) Set(key string, value int) {
    r.mu.Lock()          // 写锁，独占
    defer r.mu.Unlock()
    r.m[key] = value
}

// 方案 3：sync.Map（Go 1.9+，适合 key 稳定的场景）
// 适用于：key 写入一次，读取多次（如缓存）
func syncMapExample() {
    var m sync.Map

    m.Store("cpu", 85)
    m.Store("mem", 72)

    if val, ok := m.Load("cpu"); ok {
        fmt.Println("cpu:", val)
    }

    m.Range(func(key, value any) bool {
        fmt.Printf("%s: %v\n", key, value)
        return true // 返回 false 停止遍历
    })
}

func main() {
    // 测试并发安全的 map
    rw := &RWMap{m: make(map[string]int)}
    var wg sync.WaitGroup

    // 并发写入
    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(n int) {
            defer wg.Done()
            rw.Set(fmt.Sprintf("key-%d", n), n)
        }(i)
    }

    // 并发读取
    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(n int) {
            defer wg.Done()
            rw.Get(fmt.Sprintf("key-%d", n))
        }(i)
    }

    wg.Wait()
    fmt.Println("Done, no race condition")
}
```

### 7. 字符串处理

#### 7.1 字符串的本质

```
Go 字符串的内部结构：

type stringHeader struct {
    Data unsafe.Pointer  // 指向字节数组的指针
    Len  int             // 字节长度
}

字符串是不可变的字节序列：
    s := "Hello, 世界"

    内存布局：
    ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
    │ H │ e │ l │ l │ o │ , │   │世 │ 界 │    │    │    │    │
    └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
     0   1   2   3   4   5   6   7   8   9  10  11  12  13

    len(s) = 13  （字节数，不是字符数！）
    "世" 占 3 个字节 (UTF-8: E4 B8 96)
    "界" 占 3 个字节 (UTF-8: E7 95 8C)

    rune = int32 = Unicode 码点
    遍历字符串：
    - 按字节：for i := 0; i < len(s); i++ { s[i] }
    - 按 rune：for i, ch := range s { /* ch 是 rune */ }
```

#### 7.2 字符串操作

```go
package main

import (
    "fmt"
    "strings"
    "unicode/utf8"
)

func main() {
    s := "Hello, SRE World!"

    // 长度
    fmt.Println(len(s))                          // 字节长度
    fmt.Println(utf8.RuneCountInString(s))       // 字符（rune）长度

    // 字符串是不可变的
    // s[0] = 'h'  // 编译错误

    // 子串（O(1) 操作，共享底层数组）
    sub := s[7:10]  // "SRE"

    // strings 包常用函数
    fmt.Println(strings.Contains(s, "SRE"))       // true
    fmt.Println(strings.HasPrefix(s, "Hello"))    // true
    fmt.Println(strings.HasSuffix(s, "World!"))   // true
    fmt.Println(strings.Index(s, "SRE"))          // 7
    fmt.Println(strings.Count(s, "l"))            // 3
    fmt.Println(strings.ToUpper(s))               // "HELLO, SRE WORLD!"
    fmt.Println(strings.ToLower(s))               // "hello, sre world!"
    fmt.Println(strings.TrimSpace("  hello  "))   // "hello"
    fmt.Println(strings.Trim(s, "!"))             // "Hello, SRE World"
    fmt.Println(strings.Replace(s, "World", "Engineer", 1))
    fmt.Println(strings.Split("a,b,c", ","))      // ["a" "b" "c"]
    fmt.Println(strings.Join([]string{"a", "b"}, "-")) // "a-b"

    // strings.Builder（高效拼接字符串）
    var b strings.Builder
    for i := 0; i < 1000; i++ {
        fmt.Fprintf(&b, "item-%d,", i)
    }
    result := b.String()

    // 字符串与字节切片的转换（会复制）
    bs := []byte(s)
    s2 := string(bs)

    // unsafe 转换（零拷贝，但有风险）
    // bs2 := unsafe.Slice(unsafe.StringData(s), len(s))

    fmt.Println(sub, result[:20], s2)
}
```

#### 7.3 字符串格式化

```go
package main

import "fmt"

type HostInfo struct {
    Name     string
    IP       string
    Port     int
    CPUUsage float64
}

func (h HostInfo) String() string {
    return fmt.Sprintf("%s (%s:%d) CPU: %.1f%%",
        h.Name, h.IP, h.Port, h.CPUUsage)
}

func main() {
    host := HostInfo{"web-01", "10.0.1.10", 8080, 85.3}

    // fmt.Sprintf 格式化
    fmt.Println(host.String())

    // 常用格式化动词
    fmt.Printf("%%s  字符串:    %s\n", "hello")
    fmt.Printf("%%d  整数:      %d\n", 42)
    fmt.Printf("%%f  浮点:      %f\n", 3.14)
    fmt.Printf("%%.2f 浮点精度: %.2f\n", 3.14159)
    fmt.Printf("%%t  布尔:      %t\n", true)
    fmt.Printf("%%T  类型:      %T\n", 42)
    fmt.Printf("%%v  值:        %v\n", host)
    fmt.Printf("%%+v 结构体:    %+v\n", host)  // 包含字段名
    fmt.Printf("%%#v Go 语法:   %#v\n", host)
    fmt.Printf("%%x  十六进制:  %x\n", 255)
    fmt.Printf("%%b  二进制:    %b\n", 42)
    fmt.Printf("%%p  指针:      %p\n", &host)

    // 宽度和对齐
    fmt.Printf("|%10s|\n", "hello")     // 右对齐
    fmt.Printf("|%-10s|\n", "hello")    // 左对齐
    fmt.Printf("|%010d|\n", 42)         // 零填充
    fmt.Printf("|%*s|\n", 10, "hello")  // 动态宽度
}
```

### 8. 指针

#### 8.1 指针基础

```go
package main

import "fmt"

func main() {
    // Go 的指针比 C 简化很多：没有指针运算，只有 & 和 *
    x := 42
    p := &x           // p 是指向 int 的指针
    fmt.Println(*p)   // 42 — 解引用
    *p = 100          // 修改 x 的值
    fmt.Println(x)    // 100

    // 指针的零值是 nil
    var ptr *int
    fmt.Println(ptr == nil) // true
    // *ptr = 1            // panic: nil pointer dereference

    // new 分配内存并返回指针
    p2 := new(int)    // 分配一个 int，返回 *int
    *p2 = 42

    // 指针的指针
    pp := &p          // pp 是 **int
    fmt.Println(**pp) // 100
}

// 指针作为函数参数 — 允许函数修改外部变量
func increment(n *int) {
    *n++
}

func swap(a, b *int) {
    *a, *b = *b, *a
}
```

#### 8.2 指针在 SRE 中的应用

```go
package main

import "fmt"

// SRE 实战：用指针避免结构体拷贝
type Config struct {
    Timeout    int
    Retries    int
    Endpoints  []string
    Labels     map[string]string
}

// 值传递 — 会拷贝整个结构体（但 slice 和 map 只拷贝 header）
func processConfig(c Config) {
    c.Timeout = 60  // 不影响原始值
}

// 指针传递 — 只传递指针（8 字节），可修改原始值
func updateConfig(c *Config) {
    c.Timeout = 60  // 修改原始值
}

// 指针返回值
func newConfig() *Config {
    return &Config{
        Timeout:   30,
        Retries:   3,
        Endpoints: []string{"http://localhost:8080"},
    }
}

// 方法接收者的选择
type Server struct {
    Name string
    Port int
}

// 值接收者 — 不能修改原始值
func (s Server) GetName() string {
    return s.Name
}

// 指针接收者 — 可以修改原始值
func (s *Server) SetPort(port int) {
    s.Port = port
}

// 指针接收者 — 避免大结构体拷贝
func (s *Server) String() string {
    return fmt.Sprintf("%s:%d", s.Name, s.Port)
}

func main() {
    cfg := &Config{Timeout: 30}
    updateConfig(cfg)
    fmt.Println(cfg.Timeout) // 60

    srv := &Server{Name: "web", Port: 8080}
    srv.SetPort(9090)
    fmt.Println(srv.String()) // web:9090
}
```

**Go 指针 vs C 指针：**

```
┌────────────────────────────────────────────────────────────┐
│              Go 指针 vs C 指针                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Go 没有的：                                               │
│  ✗ 指针运算（p++、p + n）                                  │
│  ✗ 指针和整数之间的转换                                    │
│  ✗ 悬空指针（GC 保证）                                     │
│  ✗ 指针越界（运行时检查）                                  │
│                                                            │
│  Go 有的：                                                  │
│  ✓ 取地址（&）                                             │
│  ✓ 解引用（*）                                             │
│  ✓ 指针作为函数参数和返回值                                │
│  ✓ new 分配                                                │
│                                                            │
│  Go 的指针是"安全的指针"：                                  │
│  - 有垃圾回收，不需要 free                                  │
│  - 不能进行指针运算，避免越界                              │
│  - 不能转换为整数，避免伪造指针                            │
│  - 但仍然需要注意 nil 指针解引用                           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 9. 自定义类型

```go
package main

import "fmt"

// 类型定义 — 创建全新的类型
type Celsius float64
type Fahrenheit float64
type Hostname string
type Port int
type AlertLevel int

// 类型别名 — 与原类型完全相同
type Byte = uint8
type Rune = int32

// 给自定义类型添加方法
func (c Celsius) String() string    { return fmt.Sprintf("%.1f°C", c) }
func (c Celsius) ToFahrenheit() Fahrenheit { return Fahrenheit(c*9/5 + 32) }

func (f Fahrenheit) String() string { return fmt.Sprintf("%.1f°F", f) }
func (f Fahrenheit) ToCelsius() Celsius { return Celsius((f - 32) * 5 / 9) }

// SRE 实战：类型安全的端口号
type ServerAddress struct {
    Host Hostname
    Port Port
}

func (s ServerAddress) String() string {
    return fmt.Sprintf("%s:%d", s.Host, s.Port)
}

// 枚举模式
const (
    LevelDebug AlertLevel = iota
    LevelInfo
    LevelWarning
    LevelError
    LevelCritical
)

func (l AlertLevel) String() string {
    names := [...]string{"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if int(l) < len(names) {
        return names[l]
    }
    return fmt.Sprintf("AlertLevel(%d)", int(l))
}

func (l AlertLevel) Color() string {
    colors := [...]string{"grey", "blue", "yellow", "red", "magenta"}
    if int(l) < len(colors) {
        return colors[l]
    }
    return "white"
}

// 函数类型
type HealthCheckFunc func(host string, port int) error

func checkHTTP(host string, port int) error {
    // 实际的 HTTP 健康检查
    return nil
}

func checkTCP(host string, port int) error {
    // 实际的 TCP 连接检查
    return nil
}

func runHealthCheck(check HealthCheckFunc, host string, port int) error {
    return check(host, port)
}

func main() {
    // 温度转换
    c := Celsius(100)
    f := c.ToFahrenheit()
    fmt.Printf("%s = %s\n", c, f)  // 100.0°C = 212.0°F

    // 服务器地址
    addr := ServerAddress{Host: "web-01", Port: 8080}
    fmt.Println(addr)  // web-01:8080

    // 告警级别
    level := LevelWarning
    fmt.Printf("Level: %s, Color: %s\n", level, level.Color())

    // 函数类型
    err := runHealthCheck(checkHTTP, "web-01", 8080)
    fmt.Println(err)
}
```

### 10. SRE 实战案例：服务健康检查器

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
    return [...]string{"UNKNOWN", "OK", "DEGRADED", "DOWN"}[h]
}

func (h HealthStatus) Emoji() string {
    return [...]string{"⚪", "🟢", "🟡", "🔴"}[h]
}

type Service struct {
    Name       string
    Endpoint   string
    Status     HealthStatus
    LastCheck  time.Time
    ResponseMs int
    Labels     map[string]string
}

type HealthChecker struct {
    services []*Service
    mu       sync.Mutex
}

func NewHealthChecker() *HealthChecker {
    return &HealthChecker{
        services: make([]*Service, 0),
    }
}

func (hc *HealthChecker) AddService(name, endpoint string, labels map[string]string) {
    hc.mu.Lock()
    defer hc.mu.Unlock()
    hc.services = append(hc.services, &Service{
        Name:     name,
        Endpoint: endpoint,
        Status:   HealthUnknown,
        Labels:   labels,
    })
}

func (hc *HealthChecker) CheckAll() {
    hc.mu.Lock()
    services := make([]*Service, len(hc.services))
    copy(services, hc.services)
    hc.mu.Unlock()

    for _, svc := range services {
        hc.checkService(svc)
    }
}

func (hc *HealthChecker) checkService(svc *Service) {
    // 模拟网络请求延迟
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

func (hc *HealthChecker) Summary() {
    hc.mu.Lock()
    defer hc.mu.Unlock()

    counts := map[HealthStatus]int{}
    for _, svc := range hc.services {
        counts[svc.Status]++
    }

    fmt.Println("=== SRE Service Health Dashboard ===")
    fmt.Printf("%-20s %-12s %-10s %-10s %-15s\n",
        "Service", "Status", "Latency", "Last Check", "Env")
    fmt.Println("----------------------------------------------------------------------")

    for _, svc := range hc.services {
        env := svc.Labels["env"]
        fmt.Printf("%-20s %s %-10s %-10dms %-10s %-15s\n",
            svc.Name,
            svc.Status.Emoji(),
            svc.Status.String(),
            svc.ResponseMs,
            svc.LastCheck.Format("15:04:05"),
            env,
        )
    }

    fmt.Println()
    fmt.Printf("Summary: OK=%d  DEGRADED=%d  DOWN=%d  UNKNOWN=%d\n",
        counts[HealthOK], counts[HealthDegraded], counts[HealthDown], counts[HealthUnknown])
}

func main() {
    rand.Seed(time.Now().UnixNano())

    hc := NewHealthChecker()

    hc.AddService("api-gateway", "http://api.internal:8080/health",
        map[string]string{"env": "prod", "team": "platform"})
    hc.AddService("user-service", "http://user.internal:8081/health",
        map[string]string{"env": "prod", "team": "backend"})
    hc.AddService("db-primary", "tcp://db.internal:3306",
        map[string]string{"env": "prod", "team": "dba"})
    hc.AddService("redis-cache", "tcp://redis.internal:6379",
        map[string]string{"env": "prod", "team": "infra"})

    // 模拟多次检查
    for i := 0; i < 3; i++ {
        hc.CheckAll()
        hc.Summary()
        fmt.Println()
        time.Sleep(500 * time.Millisecond)
    }
}
```

## 💻 实战练习

### 练习 1：变量类型推断与零值

**目标：** 声明各类变量并验证零值行为。

```go
package main

import "fmt"

func main() {
    // 声明以下变量（不赋值），打印它们的零值和类型
    var hostname string
    var port int
    var timeout float64
    var enabled bool
    var tags []string
    var labels map[string]string
    var ptr *int

    fmt.Printf("hostname: %q (type: %T)\n", hostname, hostname)
    fmt.Printf("port: %d (type: %T)\n", port, port)
    fmt.Printf("timeout: %f (type: %T)\n", timeout, timeout)
    fmt.Printf("enabled: %t (type: %T)\n", enabled, enabled)
    fmt.Printf("tags: %v (type: %T, nil: %t)\n", tags, tags, tags == nil)
    fmt.Printf("labels: %v (type: %T, nil: %t)\n", labels, labels, labels == nil)
    fmt.Printf("ptr: %v (type: %T, nil: %t)\n", ptr, ptr, ptr == nil)

    // 验证：nil 切片可以 append
    tags = append(tags, "sre", "production")
    fmt.Println("after append:", tags)

    // 验证：nil map 写入会 panic
    // labels["env"] = "prod"  // 取消注释试试

    // 正确初始化 map
    labels = make(map[string]string)
    labels["env"] = "prod"
    fmt.Println("labels:", labels)
}
```

**验证标准：**
- [ ] 能说出所有类型的零值
- [ ] 理解 nil 切片和空切片的区别
- [ ] 知道 nil map 写入会 panic

### 练习 2：切片操作与性能优化

**目标：** 实现一个高效的指标收集器，使用预分配切片。

```go
package main

import (
    "fmt"
    "time"
)

type Metric struct {
    Name      string
    Value     float64
    Timestamp time.Time
}

// 反模式：不预分配
func collectBad(n int) []Metric {
    var metrics []Metric
    for i := 0; i < n; i++ {
        metrics = append(metrics, Metric{
            Name:      fmt.Sprintf("metric_%d", i),
            Value:     float64(i),
            Timestamp: time.Now(),
        })
    }
    return metrics
}

// 最佳实践：预分配
func collectGood(n int) []Metric {
    metrics := make([]Metric, 0, n)
    for i := 0; i < n; i++ {
        metrics = append(metrics, Metric{
            Name:      fmt.Sprintf("metric_%d", i),
            Value:     float64(i),
            Timestamp: time.Now(),
        })
    }
    return metrics
}

func main() {
    n := 100000

    start := time.Now()
    bad := collectBad(n)
    fmt.Printf("不预分配: %v (len=%d, cap=%d)\n",
        time.Since(start), len(bad), cap(bad))

    start = time.Now()
    good := collectGood(n)
    fmt.Printf("预分配:   %v (len=%d, cap=%d)\n",
        time.Since(start), len(good), cap(good))
}
```

**验证标准：**
- [ ] 理解 append 扩容机制
- [ ] 掌握 make 预分配的用法
- [ ] 能用 benchmark 对比性能

### 练习 3：Map 实战 — 告警聚合器

**目标：** 实现一个告警聚合器，按服务和级别统计告警数量。

```go
package main

import (
    "fmt"
    "sort"
)

type Alert struct {
    Service string
    Level   string
    Message string
}

// Aggregate 按服务和级别聚合告警
func Aggregate(alerts []Alert) map[string]map[string]int {
    result := make(map[string]map[string]int)

    for _, a := range alerts {
        if result[a.Service] == nil {
            result[a.Service] = make(map[string]int)
        }
        result[a.Service][a.Level]++
    }

    return result
}

// PrintSummary 按服务名排序打印聚合结果
func PrintSummary(aggregated map[string]map[string]int) {
    // 获取有序的服务列表
    services := make([]string, 0, len(aggregated))
    for svc := range aggregated {
        services = append(services, svc)
    }
    sort.Strings(services)

    fmt.Printf("%-20s %-10s %-10s %-10s\n", "Service", "CRITICAL", "WARNING", "INFO")
    fmt.Println("----------------------------------------------------")

    for _, svc := range services {
        levels := aggregated[svc]
        fmt.Printf("%-20s %-10d %-10d %-10d\n",
            svc,
            levels["CRITICAL"],
            levels["WARNING"],
            levels["INFO"],
        )
    }
}

func main() {
    alerts := []Alert{
        {Service: "api-gateway", Level: "CRITICAL", Message: "5xx rate > 5%"},
        {Service: "api-gateway", Level: "WARNING", Message: "latency > 200ms"},
        {Service: "api-gateway", Level: "WARNING", Message: "latency > 300ms"},
        {Service: "user-service", Level: "CRITICAL", Message: "pod crash loop"},
        {Service: "user-service", Level: "CRITICAL", Message: "OOM killed"},
        {Service: "user-service", Level: "INFO", Message: "deployment started"},
        {Service: "db-primary", Level: "WARNING", Message: "connections > 80%"},
        {Service: "db-primary", Level: "WARNING", Message: "replication lag > 10s"},
        {Service: "redis-cache", Level: "INFO", Message: "key eviction detected"},
    }

    aggregated := Aggregate(alerts)
    PrintSummary(aggregated)
}
```

**验证标准：**
- [ ] 能正确使用 map 的 comma ok 模式
- [ ] 理解 nil map 的行为
- [ ] 能对 map 的 key 进行排序输出

## 🎯 面试题精选

### Q1: nil 切片和空切片有什么区别？

**参考答案：**

| 特性 | nil 切片 | 空切片 |
|------|---------|--------|
| 声明方式 | `var s []int` | `s := []int{}` 或 `s := make([]int, 0)` |
| `s == nil` | true | false |
| `len(s)` | 0 | 0 |
| `cap(s)` | 0 | 0 |
| `append` | 正常工作 | 正常工作 |
| JSON 序列化 | `null` | `[]` |

在大多数场景下两者可以互换使用，但 JSON 序列化时不同：nil 切片序列化为 `null`，空切片序列化为 `[]`。在 API 设计中，通常希望返回 `[]` 而不是 `null`，所以推荐用 `make([]T, 0)` 初始化空切片。

### Q2: 切片的 append 操作什么时候会分配新的底层数组？

**参考答案：**

`append` 在以下情况会分配新的底层数组：
1. 切片的容量不足（`len + 新元素数 > cap`）—— 触发扩容
2. 切片为 nil —— 首次 append 时分配

扩容策略（Go 1.21+）：
- 如果新容量 > 旧容量的 2 倍，直接使用新容量
- 如果旧容量 < 256，新容量 = 旧容量 * 2
- 如果旧容量 >= 256，新容量 = 旧容量 * 1.25 + 192

**关键点：** `append` 返回的切片可能指向新的底层数组，所以必须 `s = append(s, x)`。

### Q3: map 的 key 有什么限制？为什么 slice 不能作为 map 的 key？

**参考答案：**

map 的 key 必须是可比较的类型（支持 `==` 运算符）：
- 可以：bool, int, float, string, pointer, channel, interface, array, struct（所有字段可比较）
- 不可以：slice, map, func

slice 不能作为 key 的原因是 slice 不支持 `==` 比较（只能与 nil 比较）。这是因为 slice 的相等性语义不明确——是引用同一个底层数组算相等，还是元素值相等算相等？

如果需要 slice 作为 key 的场景，可以：
1. 将 slice 转为 string（如 `fmt.Sprint(s)`）作为 key
2. 使用自定义的 hash 函数

### Q4: for-range 循环中的变量是共享的还是每次迭代新建的？

**参考答案：**

- **Go 1.21 及之前**：range 循环变量是同一个变量，每次迭代只是赋值。循环体中的闭包捕获的是同一个变量。
- **Go 1.22 及之后**：每次迭代创建新变量，这是语言规范的修正。

Go 1.21 的经典 bug：
```go
funcs := make([]func(), 5)
for i := range funcs {
    funcs[i] = func() { fmt.Println(i) }
}
for _, f := range funcs { f() }
// Go 1.21 输出：4 4 4 4 4
// Go 1.22 输出：0 1 2 3 4
```

### Q5: Go 的字符串是不可变的，为什么 strings.Builder 高效？

**参考答案：**

字符串不可变意味着每次 `+` 拼接都会分配新的内存并复制内容。拼接 N 次的复杂度是 O(N^2)。

`strings.Builder` 内部使用 `[]byte`（可变的字节切片），通过 `append` 方式追加数据。它只在最终调用 `.String()` 时做一次分配和复制。拼接 N 次的复杂度是 O(N)。

类似地，`fmt.Fprintf(&builder, ...)` 也是高效的，因为它直接写入 builder 的内部缓冲区。

### Q6: 如何理解 Go 指针的逃逸分析？

**参考答案：**

Go 编译器在编译时进行逃逸分析（escape analysis），决定变量分配在栈上还是堆上：

- **栈分配**：变量只在函数内部使用，函数返回后不再需要 —— 分配在栈上，函数返回时自动回收。
- **堆分配**：变量的指针被返回给调用者，或赋值给全局变量 —— "逃逸"到堆上，需要 GC 回收。

```go
func stackAlloc() int {
    x := 42  // x 不逃逸，分配在栈上
    return x
}

func heapAlloc() *int {
    x := 42  // x 逃逸到堆上（指针被返回）
    return &x
}
```

可以用 `go build -gcflags="-m"` 查看逃逸分析结果。

### Q7: 为什么 Go 中很少直接使用数组？

**参考答案：**

数组在 Go 中有以下限制：
1. **长度是类型的一部分**：`[3]int` 和 `[4]int` 是不同类型，不能互相赋值。
2. **值类型**：赋值和传参会复制整个数组，大数组性能差。
3. **长度固定**：不能动态扩展。
4. **不能用变量指定长度**（除非用泛型）。

切片解决了所有这些问题：它是数组的视图，长度可变，传参只复制 24 字节的 slice header。实际开发中几乎总是使用切片。

## 📚 深入阅读

- [Go 语言规范](https://go.dev/ref/spec) — 官方语言规范
- [Effective Go](https://go.dev/doc/effective_go) — Go 官方编程风格指南
- [Go by Example](https://gobyexample.com/) — 交互式语法教程
- [Go 数据结构内部](https://research.swtch.com/godata) — Russ Cox 的经典文章
- [切片内部实现](https://go.dev/blog/slices-intro) — 官方博客
- [Map 内部实现](https://github.com/golang/go/blob/master/src/runtime/map.go) — 源码
- [Go 1.22 Release Notes](https://go.dev/doc/go1.22) — for-range 语义修正

## ✅ 自检清单

### 理论检查点
- [ ] 能说出四种变量声明方式及适用场景
- [ ] 理解所有类型的零值，特别是 nil 切片/map/channel 的行为
- [ ] 理解切片的内部结构（指针+长度+容量）
- [ ] 理解 append 的扩容机制
- [ ] 理解 map 的内部结构（哈希桶）
- [ ] 理解 Go 1.22 for-range 语义修正

### 实操检查点
- [ ] 能熟练使用 range 遍历切片和 map
- [ ] 能用 strings.Builder 高效拼接字符串
- [ ] 能用 iota 定义枚举常量
- [ ] 能正确处理 nil 切片和 nil map
- [ ] 能用三索引切片避免子切片 append 覆盖问题

### 能力验证标准
- [ ] 能解释切片和 map 的内部实现（面试必考）
- [ ] 能识别并避免切片的共享底层数组陷阱
- [ ] 能选择正确的并发 map 方案（Mutex/RWMutex/sync.Map）
