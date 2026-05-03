# Day 59: Go 函数与错误处理

> 📅 日期：2026-05-03
> 📖 学习主题：多返回值、命名返回值、可变参数、闭包、defer/panic/recover、error 接口、自定义错误、errors.Is/As、错误链
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 57 (Go 环境搭建), Day 58 (Go 基础语法)

## 🎯 学习目标

- 掌握 Go 函数的高级特性：多返回值、命名返回值、可变参数、闭包
- 深入理解 defer/panic/recover 的执行机制
- 掌握 Go 的错误处理哲学和最佳实践
- 理解 error 接口、自定义错误、errors.Is/As、错误链
- 能在 SRE 场景中编写健壮的错误处理代码

## 📖 核心知识点

### 1. Go 的错误处理哲学

在学习具体语法之前，先理解 Go 为什么选择显式错误处理。

```
┌─────────────────────────────────────────────────────────────┐
│              Go 错误处理的设计哲学                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  其他语言的做法：                                            │
│  ├── Java/C++/Python: try-catch 异常机制                    │
│  │   优点：代码简洁，错误处理集中在一处                       │
│  │   缺点：异常可以穿越多层调用栈，控制流不清晰              │
│  │         开发者容易忽略异常，导致运行时崩溃                 │
│  │         异常的性能开销（栈展开）                          │
│  │                                                          │
│  Go 的做法：                                                │
│  ├── 错误是值（error 是普通接口），不是异常                  │
│  ├── 函数返回 error，调用者必须显式检查                     │
│  ├── 没有 try-catch，没有 exception 关键字                  │
│  │                                                          │
│  为什么这样设计？                                            │
│  ├── 1. 显式优于隐式：错误处理逻辑一目了然                   │
│  ├── 2. 强制处理：编译器会警告未使用的返回值                 │
│  ├── 3. 控制流清晰：错误沿调用链向上传递                     │
│  ├── 4. 性能好：没有异常的栈展开开销                        │
│  └── 5. 可组合：错误可以被包装、检查、分类                   │
│                                                             │
│  Go 的谚语：                                                │
│  "Errors are values." — Rob Pike                           │
│  "Don't just check errors, handle them gracefully."        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. 函数基础与高级特性

#### 2.1 函数签名与多返回值

```go
package main

import (
    "fmt"
    "os"
)

// 基本函数
func add(a, b int) int {
    return a + b
}

// 多返回值（Go 最重要的特性之一）
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, fmt.Errorf("division by zero")
    }
    return a / b, nil
}

// 多个相同类型参数可以简写
func multiply(a, b int) int {
    return a * b
}

// 返回值类型用括号包裹（多个返回值）
func swap(a, b string) (string, string) {
    return b, a
}

// 函数作为值
type HandlerFunc func(w http.ResponseWriter, r *http.Request)

// 函数作为参数
func processFiles(dir string, fn func(os.FileInfo) error) error {
    entries, err := os.ReadDir(dir)
    if err != nil {
        return err
    }
    for _, entry := range entries {
        info, err := entry.Info()
        if err != nil {
            return err
        }
        if err := fn(info); err != nil {
            return err
        }
    }
    return nil
}

func main() {
    result, err := divide(10, 3)
    if err != nil {
        fmt.Println("Error:", err)
        return
    }
    fmt.Printf("10 / 3 = %.2f\n", result)

    a, b := swap("hello", "world")
    fmt.Println(a, b)
}
```

#### 2.2 命名返回值

```go
package main

import "fmt"

// 命名返回值 — 返回值在函数声明中命名
// 好处：文档化返回值的含义，可以在 return 语句中省略返回值
func parseEndpoint(url string) (host string, port int, err error) {
    // 命名返回值作为局部变量使用，初始值为零值
    // host = "", port = 0, err = nil

    // 简单的 URL 解析示例
    // 格式：host:port
    for i := len(url) - 1; i >= 0; i-- {
        if url[i] == ':' {
            host = url[:i]
            portStr := url[i+1:]
            // 简单的端口解析
            port = 0
            for _, c := range portStr {
                port = port*10 + int(c-'0')
            }
            return // 裸 return，返回命名返回值的当前值
        }
    }

    err = fmt.Errorf("invalid endpoint: %s", url)
    return // 裸 return
}

// 命名返回值在 defer 中很有用
func readFile(path string) (data []byte, err error) {
    defer func() {
        if err != nil {
            fmt.Printf("readFile error for %s: %v\n", path, err)
        }
    }()

    data, err = os.ReadFile(path)
    return // defer 可以修改命名返回值
}

// SRE 实战：带重试的 HTTP 请求
type Result struct {
    StatusCode int
    Body       string
    Error      error
}

func httpGetWithRetry(url string, maxRetries int) (result Result, err error) {
    for i := 0; i <= maxRetries; i++ {
        // 模拟 HTTP 请求
        result.StatusCode = 200
        result.Body = "ok"

        if result.StatusCode >= 200 && result.StatusCode < 300 {
            return // 成功，返回
        }

        err = fmt.Errorf("HTTP %d on attempt %d", result.StatusCode, i+1)
        // 继续重试
    }
    return // 所有重试都失败
}

func main() {
    host, port, err := parseEndpoint("localhost:8080")
    if err != nil {
        fmt.Println("Error:", err)
        return
    }
    fmt.Printf("Host: %s, Port: %d\n", host, port)
}
```

**命名返回值的最佳实践：**

```
┌────────────────────────────────────────────────────────────┐
│              命名返回值使用指南                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  推荐使用：                                                │
│  ├── 多返回值时，用于文档化含义                            │
│  ├── defer 中需要修改返回值时                              │
│  └── 函数较长时，帮助理解返回值用途                        │
│                                                            │
│  不推荐使用：                                              │
│  ├── 短函数（< 20 行），直接 return 更清晰                 │
│  ├── 裸 return 滥用会降低可读性                            │
│  └── 如果函数有多个 return 路径，裸 return 可能造成混淆    │
│                                                            │
│  推荐模式：                                                │
│  func foo() (result int, err error) {                     │
│      // 使用命名返回值作为文档                             │
│      // 但仍然显式 return result, err                     │
│  }                                                        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### 2.3 可变参数函数

```go
package main

import (
    "fmt"
    "strings"
)

// 可变参数（variadic）— 类型前加 ...
func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}

// 可变参数与其他参数混合
func logMessage(level string, args ...interface{}) {
    msg := fmt.Sprint(args...)
    fmt.Printf("[%s] %s\n", level, msg)
}

// SRE 实战：构建标签字符串
func buildLabels(pairs ...string) map[string]string {
    if len(pairs)%2 != 0 {
        panic("buildLabels: odd number of arguments")
    }
    labels := make(map[string]string, len(pairs)/2)
    for i := 0; i < len(pairs); i += 2 {
        labels[pairs[i]] = pairs[i+1]
    }
    return labels
}

// SRE 实战：格式化告警消息
func formatAlert(alertName string, labels ...string) string {
    var b strings.Builder
    fmt.Fprintf(&b, "ALERT: %s", alertName)
    for i := 0; i < len(labels); i += 2 {
        if i+1 < len(labels) {
            fmt.Fprintf(&b, " %s=%s", labels[i], labels[i+1])
        }
    }
    return b.String()
}

func main() {
    // 基本用法
    fmt.Println(sum(1, 2, 3, 4, 5)) // 15

    // 展开切片传入
    nums := []int{10, 20, 30}
    fmt.Println(sum(nums...)) // 60

    // 日志
    logMessage("INFO", "Server started on port ", 8080)

    // 标签
    labels := buildLabels("env", "prod", "team", "sre", "service", "api")
    fmt.Println(labels)

    // 告警
    alert := formatAlert("HighCPU", "instance", "web-01", "cpu", "95%")
    fmt.Println(alert)
}
```

#### 2.4 闭包

```go
package main

import (
    "fmt"
    "sync"
)

// 闭包 = 函数 + 引用环境
// 闭包可以捕获其所在作用域的变量

// 计数器
func counter() func() int {
    count := 0
    return func() int {
        count++ // 捕获了 count 变量
        return count
    }
}

// SRE 实战：带状态的重试函数
func retryFunc(maxRetries int, fn func() error) error {
    var err error
    for i := 0; i <= maxRetries; i++ {
        err = fn()
        if err == nil {
            return nil
        }
        fmt.Printf("  Attempt %d failed: %v\n", i+1, err)
    }
    return fmt.Errorf("all %d retries failed: %w", maxRetries, err)
}

// SRE 实战：中间件模式（闭包的经典应用）
type HandlerFunc func(request string) string

func loggingMiddleware(next HandlerFunc) HandlerFunc {
    return func(request string) string {
        fmt.Printf("[LOG] Request: %s\n", request)
        result := next(request)
        fmt.Printf("[LOG] Response: %s\n", result)
        return result
    }
}

func authMiddleware(next HandlerFunc) HandlerFunc {
    return func(request string) string {
        // 模拟认证检查
        fmt.Printf("[AUTH] Checking auth for: %s\n", request)
        return next(request)
    }
}

// SRE 实战：once 模式（只执行一次的初始化）
func newOnceInit(initFn func() interface{}) func() interface{} {
    var once sync.Once
    var result interface{}
    return func() interface{} {
        once.Do(func() {
            result = initFn()
        })
        return result
    }
}

// SRE 实战：防抖（debounce）
func debounce(interval time.Duration, fn func()) func() {
    var timer *time.Timer
    return func() {
        if timer != nil {
            timer.Stop()
        }
        timer = time.AfterFunc(interval, fn)
    }
}

func main() {
    // 计数器闭包
    c := counter()
    fmt.Println(c()) // 1
    fmt.Println(c()) // 2
    fmt.Println(c()) // 3

    // 另一个独立的计数器
    c2 := counter()
    fmt.Println(c2()) // 1（独立的状态）

    // 中间件链
    handler := func(request string) string {
        return fmt.Sprintf("Response for: %s", request)
    }

    chain := loggingMiddleware(authMiddleware(handler))
    result := chain("GET /api/metrics")
    fmt.Println("Result:", result)
}
```

**闭包的内存模型：**

```
闭包的内存布局：

counter() 函数执行时：
┌──────────────────────────────────────┐
│ counter 栈帧                          │
│ ├── count = 0  (局部变量)             │
│ └── 返回匿名函数                      │
└──────────────────────────────────────┘

counter() 返回后：
┌──────────────────────────────────────┐
│ 匿名函数（闭包）                      │
│ ├── 函数代码指针                      │
│ └── 引用环境：                        │
│     └── count (已逃逸到堆上)          │
└──────────────────────────────────────┘

关键点：
1. 被闭包捕获的变量会逃逸到堆上
2. 闭包持有变量的引用，不是值的拷贝
3. 多个闭包可以共享同一个变量
4. 闭包的生命周期可能比创建它的函数更长
```

### 3. defer 机制

#### 3.1 defer 基础

```go
package main

import (
    "fmt"
    "os"
)

func main() {
    // defer 语句会在函数返回前执行
    fmt.Println("start")
    defer fmt.Println("deferred 1")
    defer fmt.println("deferred 2")
    fmt.Println("end")
    // 输出：
    // start
    // end
    // deferred 2
    // deferred 1

    // defer 是 LIFO（后进先出）栈
}

// 经典用法：资源释放
func readFile(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close() // 确保文件被关闭，即使后续代码出错

    // 读取文件内容
    buf := make([]byte, 1024)
    n, err := f.Read(buf)
    if err != nil {
        return err
    }
    fmt.Println(string(buf[:n]))
    return nil
}

// 多个资源的 defer
func copyFile(src, dst string) error {
    in, err := os.Open(src)
    if err != nil {
        return err
    }
    defer in.Close()

    out, err := os.Create(dst)
    if err != nil {
        return err
    }
    defer out.Close()

    _, err = io.Copy(out, in)
    return err
}
```

#### 3.2 defer 的执行时机

```
defer 的执行时机（重要！）：

┌─────────────────────────────────────────────────────────────┐
│              defer 执行顺序                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. defer 语句的参数在声明时求值（不是执行时）               │
│  2. defer 语句按 LIFO 顺序执行                              │
│  3. defer 在 return 语句之后、函数返回之前执行              │
│  4. defer 可以修改命名返回值                                │
│                                                             │
│  函数执行流程：                                              │
│  ┌─────────────────────────────────────────────┐            │
│  │ 1. 执行函数体                                │            │
│  │ 2. 遇到 return 语句                          │            │
│  │ 3. 将返回值赋值给返回变量                     │            │
│  │ 4. 按 LIFO 顺序执行 defer 语句               │            │
│  │ 5. 函数返回                                  │            │
│  └─────────────────────────────────────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

```go
package main

import "fmt"

// defer 参数在声明时求值
func deferEval() {
    x := 10
    defer fmt.Println("defer x =", x) // x=10 在声明时求值
    x = 20
    fmt.Println("x =", x)
    // 输出：
    // x = 20
    // defer x = 10（不是 20！）
}

// defer 修改命名返回值
func deferModifyReturn() (result int) {
    defer func() {
        result++ // 修改命名返回值
    }()
    return 1
    // 实际返回 2（1 + 1）
}

// defer 闭包捕获变量
func deferClosure() {
    x := 10
    defer func() {
        fmt.Println("defer x =", x) // 闭包捕获变量引用
    }()
    x = 20
    // 输出：defer x = 20（因为闭包捕获的是变量引用）

// defer 与循环的陷阱
func deferLoop() {
    for i := 0; i < 5; i++ {
        defer fmt.Println(i) // 参数在声明时求值
    }
    // 输出：4 3 2 1 0
}

// 在循环中正确使用 defer
func deferLoopCorrect() {
    for i := 0; i < 5; i++ {
        i := i // 重新声明，创建新变量
        defer func() {
            fmt.Println(i)
        }()
    }
    // 输出：4 3 2 1 0
}

func main() {
    deferEval()
    fmt.Println("result:", deferModifyReturn())
    deferClosure()
    deferLoop()
}
```

#### 3.3 defer 的常见模式

```go
package main

import (
    "fmt"
    "log"
    "time"
)

// 模式 1：计时器
func timeTrack(name string) func() {
    start := time.Now()
    return func() {
        fmt.Printf("%s took %v\n", name, time.Since(start))
    }
}

func slowOperation() {
    defer timeTrack("slowOperation")()
    time.Sleep(100 * time.Millisecond)
}

// 模式 2：互斥锁
// mu.Lock()
// defer mu.Unlock()

// 模式 3：错误日志
func riskyOperation() (err error) {
    defer func() {
        if err != nil {
            log.Printf("riskyOperation failed: %v", err)
        }
    }()
    // ... 操作
    return fmt.Errorf("something went wrong")
}

// 模式 4：修改返回值
func readValue() (result int, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("recovered from panic: %v", r)
            result = -1
        }
    }()
    // ... 可能 panic 的代码
    return 42, nil
}

// 模式 5：批量 defer（资源清理）
func cleanup() {
    var closers []func()
    defer func() {
        for i := len(closers) - 1; i >= 0; i-- {
            closers[i]()
        }
    }()

    // 注册清理函数
    closers = append(closers, func() { fmt.Println("cleanup 1") })
    closers = append(closers, func() { fmt.Println("cleanup 2") })
    closers = append(closers, func() { fmt.Println("cleanup 3") })
}

func main() {
    slowOperation()
    cleanup()
}
```

### 4. panic 与 recover

#### 4.1 panic 机制

```
panic 的执行流程：

┌─────────────────────────────────────────────────────────────┐
│              panic 执行流程                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 当前函数停止执行                                        │
│  2. 执行当前函数的所有 defer 语句（LIFO）                   │
│  3. 返回到调用者，执行调用者的 defer                        │
│  4. 沿调用栈向上传播                                        │
│  5. 如果没有被 recover 捕获，程序崩溃                       │
│  6. 打印 panic 信息和堆栈跟踪                              │
│                                                             │
│  调用栈示例：                                                │
│  main() → foo() → bar() → baz() [panic!]                  │
│                                                             │
│  baz 的 defer 执行                                          │
│       ↓                                                     │
│  bar 的 defer 执行                                          │
│       ↓                                                     │
│  foo 的 defer 执行                                          │
│       ↓                                                     │
│  main 的 defer 执行                                         │
│       ↓                                                     │
│  程序崩溃，打印堆栈跟踪                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

```go
package main

import "fmt"

func divide(a, b int) int {
    if b == 0 {
        panic("division by zero") // 主动 panic
    }
    return a / b
}

func riskyFunction() {
    defer fmt.Println("riskyFunction: deferred")
    panic("something went wrong")
    fmt.Println("this line never executes")
}

func main() {
    defer fmt.Println("main: deferred")

    // recover 可以捕获 panic
    result := safeDivide(10, 0)
    fmt.Println("result:", result)

    // 没有 recover 的 panic 会崩溃
    // riskyFunction()
}

func safeDivide(a, b int) (result int) {
    defer func() {
        if r := recover(); r != nil {
            fmt.Println("Recovered:", r)
            result = 0
        }
    }()
    return divide(a, b)
}
```

#### 4.2 recover 机制

```go
package main

import (
    "fmt"
    "log"
    "runtime/debug"
)

// recover 只能在 defer 函数中调用
func safeFunction(fn func()) (err error) {
    defer func() {
        if r := recover(); r != nil {
            // 获取堆栈跟踪
            stack := debug.Stack()
            err = fmt.Errorf("panic recovered: %v\n%s", r, stack)
        }
    }()

    fn()
    return nil
}

// SRE 实战：HTTP handler 的 panic 恢复
func recoveryMiddleware(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if r := recover(); r != nil {
                stack := debug.Stack()
                log.Printf("PANIC in handler: %v\n%s", r, stack)

                w.Header().Set("Content-Type", "application/json")
                w.WriteHeader(http.StatusInternalServerError)
                fmt.Fprintf(w, `{"error":"internal server error"}`)
            }
        }()
        next(w, r)
    }
}

// SRE 实战：goroutine 中的 panic 恢复
func safeGo(fn func()) {
    go func() {
        defer func() {
            if r := recover(); r != nil {
                stack := debug.Stack()
                log.Printf("goroutine panic: %v\n%s", r, stack)
            }
        }()
        fn()
    }()
}

// recover 的最佳实践
func processItem(item interface{}) (err error) {
    defer func() {
        if r := recover(); r != nil {
            // 将 panic 转为 error
            switch v := r.(type) {
            case error:
                err = v
            case string:
                err = fmt.Errorf("%s", v)
            default:
                err = fmt.Errorf("unknown panic: %v", r)
            }
        }
    }()

    // ... 处理逻辑
    return nil
}

func main() {
    // 测试 recover
    err := safeFunction(func() {
        panic("test panic")
    })
    if err != nil {
        fmt.Println("Error:", err)
    }

    // 测试 safeGo
    safeGo(func() {
        panic("goroutine panic")
    })

    time.Sleep(100 * time.Millisecond)
    fmt.Println("main continues after goroutine panic")
}
```

**panic/recover 使用指南：**

```
┌────────────────────────────────────────────────────────────┐
│              panic/recover 使用指南                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  应该 panic 的情况（程序不可恢复）：                        │
│  ├── 程序初始化失败（配置文件不存在、数据库连接失败）       │
│  ├── 不可能发生的情况（逻辑上不可能到达的代码路径）         │
│  ├── 开发者错误（传入 nil 参数、违反前置条件）             │
│  └── 包级 init 函数中的错误                                │
│                                                            │
│  不应该 panic 的情况（应该返回 error）：                    │
│  ├── 用户输入错误                                          │
│  ├── 网络请求失败                                          │
│  ├── 文件读写错误                                          │
│  ├── 任何可以预期和恢复的错误                              │
│  └── 第三方库返回的错误                                    │
│                                                            │
│  recover 的使用场景：                                       │
│  ├── HTTP handler 中间件（防止一个 handler 崩溃整个服务）  │
│  ├── goroutine 中的 panic 恢复                             │
│  ├── 插件系统（防止插件崩溃宿主程序）                      │
│  └── 将第三方库的 panic 转为 error                         │
│                                                            │
│  核心原则：                                                │
│  "panic 是最后的手段，error 是常规手段"                    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 5. error 接口

#### 5.1 error 接口基础

```go
package main

import (
    "errors"
    "fmt"
    "os"
)

// error 是一个内置接口
// type error interface {
//     Error() string
// }

// 最简单的 error 实现
type MyError struct {
    Code    int
    Message string
}

func (e *MyError) Error() string {
    return fmt.Sprintf("[%d] %s", e.Code, e.Message)
}

// 使用 errors.New 创建简单错误
var ErrNotFound = errors.New("not found")
var ErrUnauthorized = errors.New("unauthorized")
var ErrTimeout = errors.New("timeout")

// 使用 fmt.Errorf 创建带格式的错误
func getUser(id int) (string, error) {
    if id <= 0 {
        return "", fmt.Errorf("invalid user id: %d", id)
    }
    if id == 999 {
        return "", ErrNotFound
    }
    return "user", nil
}

// 错误检查
func processUser(id int) error {
    name, err := getUser(id)
    if err != nil {
        return err // 向上传递
    }
    fmt.Println("User:", name)
    return nil
}

func main() {
    // 基本错误处理
    err := processUser(999)
    if err != nil {
        fmt.Println("Error:", err)
    }

    // 检查特定错误
    err = processUser(999)
    if errors.Is(err, ErrNotFound) {
        fmt.Println("User not found")
    }

    // 类型断言获取错误详情
    var myErr *MyError
    if errors.As(err, &myErr) {
        fmt.Printf("Code: %d, Message: %s\n", myErr.Code, myErr.Message)
    }

    // os 包的错误检查
    _, err = os.Open("/nonexistent")
    if errors.Is(err, os.ErrNotExist) {
        fmt.Println("File does not exist")
    }
}
```

#### 5.2 自定义错误类型

```go
package main

import (
    "fmt"
    "time"
)

// SRE 实战：结构化错误
type ServiceError struct {
    Service   string
    Operation string
    Err       error
    Timestamp time.Time
    Metadata  map[string]interface{}
}

func (e *ServiceError) Error() string {
    return fmt.Sprintf("[%s] %s failed: %v",
        e.Service, e.Operation, e.Err)
}

func (e *ServiceError) Unwrap() error {
    return e.Err
}

// 构造函数
func NewServiceError(service, operation string, err error, metadata map[string]interface{}) *ServiceError {
    return &ServiceError{
        Service:   service,
        Operation: operation,
        Err:       err,
        Timestamp: time.Now(),
        Metadata:  metadata,
    }
}

// SRE 实战：可重试错误
type RetryableError struct {
    Err       error
    Retryable bool
    After     time.Duration
}

func (e *RetryableError) Error() string {
    return e.Err.Error()
}

func (e *RetryableError) Unwrap() error {
    return e.Err
}

func (e *RetryableError) IsRetryable() bool {
    return e.Retryable
}

// SRE 实战：HTTP 错误
type HTTPError struct {
    StatusCode int
    Message    string
    URL        string
}

func (e *HTTPError) Error() string {
    return fmt.Sprintf("HTTP %d: %s (url=%s)",
        e.StatusCode, e.Message, e.URL)
}

// 检查是否为客户端错误（4xx）
func (e *HTTPError) IsClientError() bool {
    return e.StatusCode >= 400 && e.StatusCode < 500
}

// 检查是否为服务端错误（5xx）
func (e *HTTPError) IsServerError() bool {
    return e.StatusCode >= 500
}

func main() {
    // 创建结构化错误
    svcErr := NewServiceError("user-service", "GetUser",
        fmt.Errorf("connection refused"),
        map[string]interface{}{
            "host": "db.internal",
            "port": 5432,
        },
    )
    fmt.Println(svcErr)
    fmt.Printf("Service: %s, Operation: %s\n", svcErr.Service, svcErr.Operation)

    // HTTP 错误
    httpErr := &HTTPError{
        StatusCode: 503,
        Message:    "Service Unavailable",
        URL:        "http://api.internal:8080/health",
    }
    fmt.Println(httpErr)
    fmt.Println("Is server error:", httpErr.IsServerError())
}
```

#### 5.3 errors.Is 和 errors.As（Go 1.13+）

```go
package main

import (
    "errors"
    "fmt"
    "os"
)

// errors.Is — 检查错误链中是否包含特定错误
// 等价于遍历错误链，对每个错误调用 == 比较

// errors.As — 从错误链中提取特定类型的错误
// 等价于遍历错误链，对每个错误进行类型断言

// 错误链的构建（使用 %w 动词）
func readConfig(path string) error {
    data, err := os.ReadFile(path)
    if err != nil {
        // %w 包装错误，保留原始错误
        return fmt.Errorf("read config file %s: %w", path, err)
    }
    _ = data
    return nil
}

func loadConfig() error {
    err := readConfig("/etc/app/config.yaml")
    if err != nil {
        return fmt.Errorf("load config: %w", err)
    }
    return nil
}

// 多错误包装
func initialize() error {
    var errs []error

    if err := loadConfig(); err != nil {
        errs = append(errs, fmt.Errorf("config: %w", err))
    }

    if err := connectDatabase(); err != nil {
        errs = append(errs, fmt.Errorf("database: %w", err))
    }

    if len(errs) > 0 {
        return errors.Join(errs...) // Go 1.20+ errors.Join
    }
    return nil
}

func main() {
    err := initialize()
    if err != nil {
        fmt.Println("Error:", err)

        // errors.Is — 检查错误链
        if errors.Is(err, os.ErrNotExist) {
            fmt.Println("Config file not found")
        }

        // errors.As — 提取特定类型
        var pathErr *os.PathError
        if errors.As(err, &pathErr) {
            fmt.Printf("Path: %s, Op: %s, Err: %v\n",
                pathErr.Path, pathErr.Op, pathErr.Err)
        }
    }
}
```

**errors.Is vs == 的区别：**

```go
// == 只比较最外层错误
err := fmt.Errorf("wrap: %w", os.ErrNotExist)
fmt.Println(err == os.ErrNotExist)           // false
fmt.Println(errors.Is(err, os.ErrNotExist))  // true

// errors.Is 会遍历整个错误链
// 它调用每个错误的 Is(error) bool 方法（如果有的话）
// 然后用 == 比较

// 自定义错误可以实现 Is 方法
type MyError struct {
    Code int
}

func (e *MyError) Error() string {
    return fmt.Sprintf("error code: %d", e.Code)
}

func (e *MyError) Is(target error) bool {
    t, ok := target.(*MyError)
    return ok && t.Code == e.Code
}

// 这样即使错误被包装，也能通过 Is 匹配
```

#### 5.4 错误链与错误包装

```
错误链的结构：

    fmt.Errorf("wrap3: %w", err3)
         │
         ▼
    fmt.Errorf("wrap2: %w", err2)
         │
         ▼
    fmt.Errorf("wrap1: %w", err1)
         │
         ▼
    errors.New("root cause")

    errors.Is 检查链中的每一层：
    "wrap3: wrap2: wrap1: root cause"
                              ↑
                        这里匹配 errors.New("root cause")

    errors.As 提取链中特定类型的错误：
    遍历链中的每个错误，找到第一个可以转换为目标类型的错误
```

```go
package main

import (
    "errors"
    "fmt"
)

// 多层错误包装
func level3() error {
    return errors.New("root cause: connection refused")
}

func level2() error {
    err := level3()
    if err != nil {
        return fmt.Errorf("database query failed: %w", err)
    }
    return nil
}

func level1() error {
    err := level2()
    if err != nil {
        return fmt.Errorf("user service error: %w", err)
    }
    return nil
}

// Go 1.20+ 的 errors.Join（多错误）
func multiError() error {
    err1 := errors.New("error 1")
    err2 := errors.New("error 2")
    err3 := errors.New("error 3")
    return errors.Join(err1, err2, err3)
}

// 自定义错误包装器
type WrapError struct {
    Msg string
    Err error
}

func (e *WrapError) Error() string {
    if e.Err != nil {
        return fmt.Sprintf("%s: %v", e.Msg, e.Err)
    }
    return e.Msg
}

func (e *WrapError) Unwrap() error {
    return e.Err
}

func (e *WrapError) Is(target error) bool {
    t, ok := target.(*WrapError)
    return ok && t.Msg == e.Msg
}

func main() {
    err := level1()
    fmt.Println("Full error:", err)

    // errors.Is 检查
    fmt.Println("Is root cause?", errors.Is(err, errors.New("root cause: connection refused")))

    // errors.As 提取
    var wrapErr *WrapError
    if errors.As(err, &wrapErr) {
        fmt.Println("WrapError:", wrapErr.Msg)
    }

    // 多错误
    multiErr := multiError()
    fmt.Println("Multi error:", multiErr)

    // errors.Is 对多错误的检查
    fmt.Println("Contains error 2?", errors.Is(multiErr, errors.New("error 2")))
}
```

### 6. SRE 错误处理最佳实践

#### 6.1 错误处理模式

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "log"
    "time"
)

// 模式 1：错误包装（添加上下文）
func fetchMetrics(ctx context.Context, endpoint string) ([]byte, error) {
    // 模拟 HTTP 请求
    return nil, fmt.Errorf("fetch metrics from %s: %w", endpoint,
        errors.New("connection timeout"))
}

// 模式 2：错误分类（可重试/不可重试）
var (
    ErrTransient  = errors.New("transient error")
    ErrPermanent  = errors.New("permanent error")
    ErrRateLimit  = errors.New("rate limit exceeded")
)

func classifyError(err error) error {
    if err == nil {
        return nil
    }
    // 根据错误类型分类
    if errors.Is(err, context.DeadlineExceeded) {
        return fmt.Errorf("%w: %w", ErrTransient, err)
    }
    if errors.Is(err, context.Canceled) {
        return fmt.Errorf("%w: %w", ErrPermanent, err)
    }
    return err
}

// 模式 3：带指数退避的重试
func retryWithBackoff(ctx context.Context, maxRetries int, fn func() error) error {
    var lastErr error
    for i := 0; i <= maxRetries; i++ {
        err := fn()
        if err == nil {
            return nil
        }
        lastErr = err

        // 检查是否可重试
        if errors.Is(err, ErrPermanent) {
            return fmt.Errorf("permanent error, not retrying: %w", err)
        }

        // 指数退避
        if i < maxRetries {
            backoff := time.Duration(1<<uint(i)) * time.Second
            select {
            case <-ctx.Done():
                return fmt.Errorf("context canceled during retry: %w", ctx.Err())
            case <-time.After(backoff):
                log.Printf("Retry %d/%d after %v", i+1, maxRetries, backoff)
            }
        }
    }
    return fmt.Errorf("all %d retries exhausted: %w", maxRetries, lastErr)
}

// 模式 4：错误聚合
type ErrorCollector struct {
    errs []error
}

func (c *ErrorCollector) Add(err error) {
    if err != nil {
        c.errs = append(c.errs, err)
    }
}

func (c *ErrorCollector) Error() error {
    if len(c.errs) == 0 {
        return nil
    }
    return fmt.Errorf("collected %d errors: %w", len(c.errs),
        errors.Join(c.errs...))
}

func (c *ErrorCollector) HasErrors() bool {
    return len(c.errs) > 0
}

// 模式 5：结果类型（Rust 风格）
type Result[T any] struct {
    Value T
    Err   error
}

func Ok[T any](value T) Result[T] {
    return Result[T]{Value: value}
}

func Err[T any](err error) Result[T] {
    return Result[T]{Err: err}
}

func (r Result[T]) Unwrap() (T, error) {
    return r.Value, r.Err
}

func (r Result[T]) IsOk() bool {
    return r.Err == nil
}

func main() {
    ctx := context.Background()

    // 重试示例
    err := retryWithBackoff(ctx, 3, func() error {
        return fetchMetrics(ctx, "http://metrics.internal:9090")
    })
    if err != nil {
        log.Printf("Failed: %v", err)
    }

    // 错误聚合示例
    collector := &ErrorCollector{}
    collector.Add(fmt.Errorf("check 1 failed"))
    collector.Add(fmt.Errorf("check 2 failed"))
    if collector.HasErrors() {
        log.Printf("Health checks failed: %v", collector.Error())
    }

    // Result 示例
    result := Ok(42)
    if result.IsOk() {
        val, _ := result.Unwrap()
        fmt.Println("Value:", val)
    }
}
```

#### 6.2 SRE 实战：健壮的健康检查

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "log"
    "net/http"
    "sync"
    "time"
)

var (
    ErrServiceDown    = errors.New("service is down")
    ErrServiceDegraded = errors.New("service is degraded")
    ErrTimeout        = errors.New("health check timed out")
)

type HealthCheckResult struct {
    Service   string
    Status    string
    Latency   time.Duration
    Error     error
    Timestamp time.Time
}

type HealthChecker struct {
    services map[string]string // name -> endpoint
    mu       sync.RWMutex
}

func NewHealthChecker() *HealthChecker {
    return &HealthChecker{
        services: make(map[string]string),
    }
}

func (hc *HealthChecker) AddService(name, endpoint string) {
    hc.mu.Lock()
    defer hc.mu.Unlock()
    hc.services[name] = endpoint
}

func (hc *HealthChecker) CheckAll(ctx context.Context) []HealthCheckResult {
    hc.mu.RLock()
    services := make(map[string]string, len(hc.services))
    for k, v := range hc.services {
        services[k] = v
    }
    hc.mu.RUnlock()

    results := make([]HealthCheckResult, 0, len(services))
    var mu sync.Mutex
    var wg sync.WaitGroup

    for name, endpoint := range services {
        wg.Add(1)
        go func(name, endpoint string) {
            defer wg.Done()
            result := hc.checkOne(ctx, name, endpoint)
            mu.Lock()
            results = append(results, result)
            mu.Unlock()
        }(name, endpoint)
    }

    wg.Wait()
    return results
}

func (hc *HealthChecker) checkOne(ctx context.Context, name, endpoint string) HealthCheckResult {
    start := time.Now()
    result := HealthCheckResult{
        Service:   name,
        Timestamp: start,
    }

    // 带超时的健康检查
    checkCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    err := hc.doCheck(checkCtx, endpoint)
    result.Latency = time.Since(start)

    if err != nil {
        result.Error = err
        if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, ErrTimeout) {
            result.Status = "TIMEOUT"
        } else if errors.Is(err, ErrServiceDown) {
            result.Status = "DOWN"
        } else {
            result.Status = "ERROR"
        }
    } else if result.Latency > 2*time.Second {
        result.Status = "DEGRADED"
        result.Error = ErrServiceDegraded
    } else {
        result.Status = "OK"
    }

    return result
}

func (hc *HealthChecker) doCheck(ctx context.Context, endpoint string) error {
    req, err := http.NewRequestWithContext(ctx, "GET", endpoint+"/healthz", nil)
    if err != nil {
        return fmt.Errorf("create request: %w", err)
    }

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            return fmt.Errorf("health check timeout: %w", ErrTimeout)
        }
        return fmt.Errorf("health check failed: %w", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode >= 500 {
        return fmt.Errorf("service returned %d: %w", resp.StatusCode, ErrServiceDown)
    }
    if resp.StatusCode >= 400 {
        return fmt.Errorf("service returned %d", resp.StatusCode)
    }

    return nil
}

func (hc *HealthChecker) PrintReport(results []HealthCheckResult) {
    fmt.Println("=== Health Check Report ===")
    fmt.Printf("%-20s %-10s %-12s %-30s\n", "Service", "Status", "Latency", "Error")
    fmt.Println("----------------------------------------------------------------------")

    okCount, degradedCount, downCount := 0, 0, 0
    for _, r := range results {
        errStr := ""
        if r.Error != nil {
            errStr = r.Error.Error()
        }
        fmt.Printf("%-20s %-10s %-12v %-30s\n",
            r.Service, r.Status, r.Latency.Round(time.Millisecond), errStr)

        switch r.Status {
        case "OK":
            okCount++
        case "DEGRADED":
            degradedCount++
        default:
            downCount++
        }
    }

    fmt.Println()
    fmt.Printf("Summary: OK=%d DEGRADED=%d DOWN=%d\n",
        okCount, degradedCount, downCount)
}

func main() {
    hc := NewHealthChecker()
    hc.AddService("api-gateway", "http://api.internal:8080")
    hc.AddService("user-service", "http://user.internal:8081")
    hc.AddService("db-proxy", "http://db.internal:3306")

    ctx := context.Background()
    results := hc.CheckAll(ctx)
    hc.PrintReport(results)
}
```

#### 6.3 SRE 实战：错误处理在 CLI 工具中的应用

```go
package main

import (
    "errors"
    "fmt"
    "os"
    "os/exec"
    "strings"
)

var (
    ErrCommandFailed  = errors.New("command execution failed")
    ErrInvalidInput   = errors.New("invalid input")
    ErrPermission     = errors.New("permission denied")
)

type CLIError struct {
    Command  string
    ExitCode int
    Stderr   string
    Err      error
}

func (e *CLIError) Error() string {
    var b strings.Builder
    fmt.Fprintf(&b, "command %q failed (exit code %d)", e.Command, e.ExitCode)
    if e.Stderr != "" {
        fmt.Fprintf(&b, ": %s", e.Stderr)
    }
    if e.Err != nil {
        fmt.Fprintf(&b, ": %v", e.Err)
    }
    return b.String()
}

func (e *CLIError) Unwrap() error {
    return e.Err
}

func runCommand(name string, args ...string) error {
    cmd := exec.Command(name, args...)
    output, err := cmd.CombinedOutput()
    if err != nil {
        exitCode := 1
        var exitErr *exec.ExitError
        if errors.As(err, &exitErr) {
            exitCode = exitErr.ExitCode()
        }
        return &CLIError{
            Command:  fmt.Sprintf("%s %s", name, strings.Join(args, " ")),
            ExitCode: exitCode,
            Stderr:   strings.TrimSpace(string(output)),
            Err:      ErrCommandFailed,
        }
    }
    return nil
}

func main() {
    // 运行可能失败的命令
    err := runCommand("kubectl", "get", "pods", "-n", "default")
    if err != nil {
        var cliErr *CLIError
        if errors.As(err, &cliErr) {
            fmt.Printf("CLI Error: command=%s exit_code=%d stderr=%s\n",
                cliErr.Command, cliErr.ExitCode, cliErr.Stderr)

            // 根据错误类型给出建议
            switch cliErr.ExitCode {
            case 1:
                fmt.Println("Hint: Check if the resource exists")
            case 2:
                fmt.Println("Hint: Check command syntax")
            case 126:
                fmt.Println("Hint: Permission denied, check file permissions")
            case 127:
                fmt.Println("Hint: Command not found, check PATH")
            }
        } else {
            fmt.Printf("Error: %v\n", err)
        }
        os.Exit(1)
    }

    fmt.Println("Command succeeded")
}
```

### 7. 错误处理的反模式

```go
// 反模式 1：忽略错误
data, _ := os.ReadFile("config.yaml")  // 不要这样做！

// 反模式 2：只打印错误，不返回
func bad() {
    err := doSomething()
    if err != nil {
        fmt.Println(err)  // 打印了，但调用者不知道出错了
    }
}

// 反模式 3：过早 panic
func bad2() {
    err := doSomething()
    if err != nil {
        panic(err)  // 不必要的 panic
    }
}

// 反模式 4：错误信息重复
func bad3() error {
    err := doSomething()
    if err != nil {
        return fmt.Errorf("error: %v", err)  // "error: error: ..."
    }
    return nil
}

// 反模式 5：不包装错误（丢失上下文）
func bad4() error {
    err := doSomething()
    if err != nil {
        return err  // 丢失了 doSomething 的上下文
    }
    return nil
}

// 正确做法
func good() error {
    err := doSomething()
    if err != nil {
        return fmt.Errorf("good: doSomething failed: %w", err)
    }
    return nil
}
```

## 💻 实战练习

### 练习 1：基础操作 — 带重试的 HTTP 客户端

**目标：** 实现一个带重试和错误分类的 HTTP 客户端。

```go
package main

import (
    "context"
    "errors"
    "fmt"
    "time"
)

var (
    ErrTransient = errors.New("transient error")
    ErrPermanent = errors.New("permanent error")
)

type HTTPClient struct {
    MaxRetries int
    BaseURL    string
}

func (c *HTTPClient) Get(ctx context.Context, path string) (string, error) {
    var lastErr error

    for i := 0; i <= c.MaxRetries; i++ {
        result, err := c.doRequest(ctx, path)
        if err == nil {
            return result, nil
        }
        lastErr = err

        // 不可重试的错误直接返回
        if errors.Is(err, ErrPermanent) {
            return "", fmt.Errorf("permanent error, not retrying: %w", err)
        }

        // 等待后重试
        if i < c.MaxRetries {
            backoff := time.Duration(1<<uint(i)) * 100 * time.Millisecond
            select {
            case <-ctx.Done():
                return "", fmt.Errorf("context canceled: %w", ctx.Err())
            case <-time.After(backoff):
                fmt.Printf("  Retry %d/%d after %v\n", i+1, c.MaxRetries, backoff)
            }
        }
    }

    return "", fmt.Errorf("all retries exhausted: %w", lastErr)
}

func (c *HTTPClient) doRequest(ctx context.Context, path string) (string, error) {
    // 模拟请求
    select {
    case <-ctx.Done():
        return "", ctx.Err()
    default:
    }

    // 模拟成功
    return fmt.Sprintf("Response from %s%s", c.BaseURL, path), nil
}

func main() {
    client := &HTTPClient{
        MaxRetries: 3,
        BaseURL:    "http://api.internal:8080",
    }

    ctx := context.Background()
    result, err := client.Get(ctx, "/metrics")
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    fmt.Println(result)
}
```

**验证标准：**
- [ ] 理解错误包装（%w）的用法
- [ ] 掌握 errors.Is 和 errors.As 的使用
- [ ] 能实现带重试的错误处理逻辑

### 练习 2：进阶场景 — 错误聚合与报告

**目标：** 实现一个批量操作的错误聚合器。

```go
package main

import (
    "errors"
    "fmt"
)

type OperationResult struct {
    Name  string
    Error error
}

type BatchResult struct {
    Results []OperationResult
}

func (br *BatchResult) AddResult(name string, err error) {
    br.Results = append(br.Results, OperationResult{Name: name, Error: err})
}

func (br *BatchResult) Errors() []OperationResult {
    var errs []OperationResult
    for _, r := range br.Results {
        if r.Error != nil {
            errs = append(errs, r)
        }
    }
    return errs
}

func (br *BatchResult) HasErrors() bool {
    return len(br.Errors()) > 0
}

func (br *BatchResult) Error() error {
    errs := br.Errors()
    if len(errs) == 0 {
        return nil
    }

    var errMsgs []error
    for _, e := range errs {
        errMsgs = append(errMsgs, fmt.Errorf("%s: %w", e.Name, e.Error))
    }
    return errors.Join(errMsgs...)
}

func (br *BatchResult) Summary() string {
    total := len(br.Results)
    failed := len(br.Errors())
    succeeded := total - failed
    return fmt.Sprintf("Total: %d, Succeeded: %d, Failed: %d",
        total, succeeded, failed)
}

// 模拟批量健康检查
func batchHealthCheck(services []string) *BatchResult {
    result := &BatchResult{}
    for _, svc := range services {
        err := checkService(svc)
        result.AddResult(svc, err)
    }
    return result
}

func checkService(name string) error {
    // 模拟：某些服务失败
    switch name {
    case "api-gateway":
        return nil
    case "user-service":
        return errors.New("connection refused")
    case "db-primary":
        return nil
    case "redis-cache":
        return errors.New("timeout")
    default:
        return errors.New("unknown service")
    }
}

func main() {
    services := []string{"api-gateway", "user-service", "db-primary", "redis-cache"}
    result := batchHealthCheck(services)

    fmt.Println(result.Summary())

    if result.HasErrors() {
        fmt.Println("\nFailed services:")
        for _, e := range result.Errors() {
            fmt.Printf("  - %s: %v\n", e.Name, e.Error)
        }
        fmt.Printf("\nAggregated error: %v\n", result.Error())
    }
}
```

**验证标准：**
- [ ] 能实现错误聚合模式
- [ ] 理解 errors.Join 的用法
- [ ] 能生成清晰的错误报告

### 练习 3：故障排查挑战

**场景：** 以下代码有多个错误处理问题，请找出并修复。

```go
package main

import (
    "errors"
    "fmt"
    "os"
)

// 问题 1：错误被忽略
func readConfig(path string) map[string]string {
    data, _ := os.ReadFile(path)
    config := make(map[string]string)
    config["raw"] = string(data)
    return config
}

// 问题 2：错误信息没有上下文
func processFile(path string) error {
    data, err := os.ReadFile(path)
    if err != nil {
        return err
    }
    // 处理数据
    _ = data
    return nil
}

// 问题 3：不必要地 panic
func mustParse(s string) int {
    var n int
    _, err := fmt.Sscanf(s, "%d", &n)
    if err != nil {
        panic(err) // 不应该 panic
    }
    return n
}

// 问题 4：错误类型断言不安全
func handleError(err error) {
    pathErr := err.(*os.PathError) // 不安全的类型断言
    fmt.Println(pathErr.Path)
}

// 问题 5：错误链断裂
func doWork() error {
    err := step1()
    if err != nil {
        return errors.New("step1 failed") // 丢失了原始错误
    }
    return nil
}

func step1() error {
    return errors.New("connection refused")
}

func main() {
    // 修复后的调用示例
    config := readConfig("config.yaml")
    fmt.Println(config)

    err := processFile("test.txt")
    if err != nil {
        fmt.Println(err)
    }

    n := mustParse("42")
    fmt.Println(n)

    handleError(&os.PathError{Path: "/tmp/test", Op: "open", Err: errors.New("no such file")})

    err = doWork()
    if err != nil {
        fmt.Println(err)
    }
}
```

**任务：**
1. 修复所有错误被忽略的问题
2. 为错误添加上下文信息
3. 将 panic 改为返回 error
4. 使用安全的类型断言（errors.As）
5. 保留错误链（使用 %w）

## 🎯 面试题精选

### Q1: Go 的 error 接口是什么？为什么 Go 选择这种设计？

**参考答案：**

error 是一个内置接口：
```go
type error interface {
    Error() string
}
```

Go 选择显式错误处理（而不是异常机制）的原因：
1. **显式优于隐式**：错误处理逻辑在代码中一目了然。
2. **强制处理**：编译器会警告未使用的返回值。
3. **控制流清晰**：错误沿调用链向上传递，没有隐藏的跳转。
4. **性能好**：没有异常的栈展开开销。
5. **可组合**：错误可以被包装、检查、分类。

### Q2: errors.Is 和 errors.As 有什么区别？

**参考答案：**

- `errors.Is(err, target)`：检查错误链中是否包含 `target`。等价于遍历错误链，对每个错误调用 `==` 比较（或调用 `Is(error) bool` 方法）。
- `errors.As(err, &target)`：从错误链中提取特定类型的错误。等价于遍历错误链，对每个错误进行类型断言（或调用 `As(interface{}) bool` 方法）。

关键区别：
- `Is` 用于比较错误值（常量错误）
- `As` 用于提取错误类型（结构化错误）

### Q3: 什么时候应该用 panic，什么时候应该返回 error？

**参考答案：**

应该 panic 的情况：
- 程序初始化失败（配置文件不存在、数据库连接失败）
- 不可能发生的情况（逻辑上不可能到达的代码路径）
- 开发者错误（传入 nil 参数、违反前置条件）

应该返回 error 的情况：
- 用户输入错误
- 网络请求失败
- 文件读写错误
- 任何可以预期和恢复的错误

核心原则："panic 是最后的手段，error 是常规手段"。

### Q4: defer 的执行顺序是什么？defer 参数什么时候求值？

**参考答案：**

defer 的执行顺序：
1. defer 语句的参数在声明时求值（不是执行时）
2. defer 语句按 LIFO（后进先出）顺序执行
3. defer 在 return 语句之后、函数返回之前执行
4. defer 可以修改命名返回值

```go
func example() {
    x := 10
    defer fmt.Println("x =", x) // x=10 在声明时求值
    x = 20
}
// 输出：x = 10（不是 20）
```

### Q5: 如何在 Go 中实现错误链？%w 和 %v 有什么区别？

**参考答案：**

错误链通过 `fmt.Errorf` 的 `%w` 动词实现：
- `%w` 包装错误，保留原始错误，支持 `errors.Is` 和 `errors.As` 遍历链
- `%v` 格式化错误，丢失原始错误的类型信息，不支持链遍历

```go
err := errors.New("root cause")
// %w 包装 — 保留错误链
wrapped := fmt.Errorf("context: %w", err)
errors.Is(wrapped, err) // true

// %v 格式化 — 丢失错误链
formatted := fmt.Errorf("context: %v", err)
errors.Is(formatted, err) // false
```

### Q6: recover 只能在 defer 中调用，为什么？

**参考答案：**

recover 的设计意图是捕获当前 goroutine 中正在传播的 panic。它只能在 defer 函数中调用，因为：

1. **时序保证**：panic 发生时，Go 运行时会沿调用栈执行 defer 函数。如果 recover 在 defer 中调用，它可以捕获到当前正在传播的 panic。
2. **作用域限制**：如果 recover 可以在任意位置调用，它可能捕获到不相关的 panic，导致错误被误处理。
3. **语义清晰**：defer + recover 的组合明确表达了"我在清理阶段处理错误"的意图。

### Q7: Go 1.20 引入的 errors.Join 解决了什么问题？

**参考答案：**

`errors.Join` 解决了多个错误同时发生时的聚合问题。之前需要自定义实现多错误聚合，现在可以直接使用标准库。

```go
err1 := errors.New("check 1 failed")
err2 := errors.New("check 2 failed")
combined := errors.Join(err1, err2)
fmt.Println(combined) // "check 1 failed\ncheck 2 failed"

errors.Is(combined, err1) // true
errors.Is(combined, err2) // true
```

`errors.Join` 返回的错误实现了 `Unwrap() []error` 方法（多错误展开），而 `fmt.Errorf("%w", err)` 只支持单错误包装。

## 📚 淾入阅读

- [Go Error Handling 文档](https://go.dev/blog/error-handling-and-go) — 官方博客
- [Go Error Wrapping](https://go.dev/blog/go1.13-errors) — Go 1.13 错误包装
- [Working with Errors in Go 1.13](https://go.dev/blog/go1.13-errors) — 官方文档
- [Errors Are Values](https://go.dev/blog/errors-are-values) — Rob Pike 的经典文章
- [Defer, Panic, and Recover](https://go.dev/blog/defer-panic-recover) — 官方博客
- [Go 错误处理最佳实践](https://dave.cheney.net/2016/04/27/dont-just-check-errors-handle-them-gracefully) — Dave Cheney

## ✅ 自检清单

### 理论检查点
- [ ] 理解 Go 错误处理的设计哲学（errors are values）
- [ ] 理解 error 接口的定义和实现
- [ ] 掌握 errors.Is 和 errors.As 的区别
- [ ] 理解 defer 的执行顺序和参数求值时机
- [ ] 理解 panic/recover 的传播机制
- [ ] 掌握错误链的构建和遍历

### 实操检查点
- [ ] 能用 fmt.Errorf + %w 包装错误
- [ ] 能用 errors.Is 检查特定错误
- [ ] 能用 errors.As 提取特定错误类型
- [ ] 能正确使用 defer 进行资源清理
- [ ] 能实现带重试的错误处理逻辑
- [ ] 能编写 panic-safe 的 HTTP handler

### 能力验证标准
- [ ] 能设计结构化的错误类型（ServiceError、HTTPError）
- [ ] 能实现错误聚合和批量操作的错误处理
- [ ] 能识别并避免常见的错误处理反模式
