# Day 65: Go Context 与超时控制

> 📅 日期：2026-05-03
> 📖 学习主题：Go Context 机制、超时控制、取消传播与 SRE 实战
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 62 并发编程、Day 63 标准库与网络编程

## 🎯 学习目标

完成 Day 65 的学习后，你应该能够：
1. 深入理解 `context.Context` 接口的四个方法及其语义
2. 熟练使用 `WithCancel`、`WithTimeout`、`WithDeadline`、`WithValue` 创建派生 Context
3. 掌握 Context 在 goroutine 树中的传播规则与取消机制
4. 实现 HTTP 服务、数据库查询、RPC 调用中的超时控制
5. 识别并避免 Context 的常见误用模式，回答相关高频面试题

---

## 📖 核心知识点

### 1. Context 接口与设计哲学

#### 1.1 为什么需要 Context？

在 Go 的并发编程中，我们经常面临以下问题：

- 一个 HTTP 请求触发多个下游调用（数据库、RPC、缓存），请求取消时如何通知所有下游？
- 后台 goroutine 泄漏：请求结束后 goroutine 仍在运行，消耗资源
- 级联超时：用户请求超时 5s，但数据库查询超时 30s，导致资源浪费
- 请求范围数据传递：trace ID、认证信息如何在调用链中传递？

`context.Context` 就是 Go 官方提供的解决方案，它在 Go 1.7 引入标准库。

#### 1.2 Context 接口定义

```go
// context.Context 是一个接口，定义在 context 包中
type Context interface {
    // Deadline 返回 context 被取消的截止时间
    // 如果没有设置截止时间，ok 返回 false
    Deadline() (deadline time.Time, ok bool)

    // Done 返回一个 channel，当 context 被取消或超时时关闭
    // Done channel 关闭后，所有监听该 channel 的 goroutine 应该停止工作并返回
    Done() <-chan struct{}

    // Err 返回 context 被取消的原因
    // 如果 Done 尚未关闭，Err 返回 nil
    // 如果 context 被取消，返回 Canceled
    // 如果 context 超时，返回 DeadlineExceeded
    Err() error

    // Value 返回与 key 关联的值，不存在返回 nil
    // 用于传递请求范围的数据（如 trace ID、认证信息）
    Value(key any) any
}
```

#### 1.3 Context 树形结构

Context 采用树形结构，父 Context 取消时，所有子 Context 自动取消：

```
                    context.Background()
                           │
              ┌────────────┼────────────┐
              │            │            │
         WithCancel   WithTimeout  WithDeadline
              │            │            │
         ┌────┴────┐       │       ┌────┴────┐
         │         │       │       │         │
     WithValue  WithCancel │   WithValue  WithCancel
                           │
                      WithValue

取消传播方向：父 → 子（单向，子取消不影响父）
Value 查找方向：子 → 父（向上查找）
```

#### 1.4 四种创建方式对比

| 函数 | 用途 | 取消方式 | 典型场景 |
|------|------|----------|----------|
| `Background()` | 根 Context | 永不取消 | main 函数、初始化、顶层测试 |
| `TODO()` | 占位符 | 永不取消 | 不确定用哪个 Context 时的临时占位 |
| `WithCancel(parent)` | 手动取消 | 调用 cancel 函数 | 并发任务任一完成时取消其余 |
| `WithTimeout(parent, d)` | 超时取消 | 超时或调用 cancel | HTTP 请求、数据库查询 |
| `WithDeadline(parent, t)` | 截止时间 | 到达时间或调用 cancel | 需要精确截止时间的场景 |
| `WithValue(parent, k, v)` | 附加数据 | 随父取消 | trace ID、认证信息 |

---

### 2. WithCancel 深入理解

#### 2.1 基本用法

```go
package main

import (
    "context"
    "fmt"
    "time"
)

func main() {
    // 创建一个可取消的 Context
    ctx, cancel := context.WithCancel(context.Background())

    // 启动一个监听 Context 的 goroutine
    go func(ctx context.Context) {
        for {
            select {
            case <-ctx.Done():
                fmt.Println("goroutine 收到取消信号:", ctx.Err())
                return
            default:
                fmt.Println("goroutine 正在工作...")
                time.Sleep(500 * time.Millisecond)
            }
        }
    }(ctx)

    time.Sleep(2 * time.Second)
    fmt.Println("主 goroutine 发送取消信号")
    cancel() // 发送取消信号

    time.Sleep(1 * time.Second) // 等待 goroutine 退出
    fmt.Println("程序结束")
}
```

**输出：**
```
goroutine 正在工作...
goroutine 正在工作...
goroutine 正在工作...
goroutine 正在工作...
主 goroutine 发送取消信号
goroutine 收到取消信号: context canceled
程序结束
```

#### 2.2 cancel 必须调用 — 资源泄漏防护

`WithCancel`（以及 `WithTimeout`、`WithDeadline`）返回的 `cancel` 函数**必须被调用**，否则子 Context 会一直挂在父 Context 上，导致资源泄漏。

```go
// 错误示范：忘记调用 cancel
func badExample() {
    ctx, _ := context.WithCancel(context.Background()) // 忽略 cancel
    go doWork(ctx)
    // ... 函数返回后，子 Context 仍然挂在 Background 上
    // 如果 Background 是全局的，这个子 Context 永远不会被回收
}

// 正确做法：使用 defer 确保 cancel 被调用
func goodExample() {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel() // 确保函数返回时取消
    go doWork(ctx)
}
```

#### 2.3 取消传播链

```go
package main

import (
    "context"
    "fmt"
    "time"
)

func main() {
    // 创建 Context 链
    ctx1, cancel1 := context.WithCancel(context.Background())
    ctx2, _ := context.WithCancel(ctx1)  // ctx2 是 ctx1 的子
    ctx3, _ := context.WithCancel(ctx2)  // ctx3 是 ctx2 的子

    // 监听所有 Context
    go watchContext("ctx1", ctx1)
    go watchContext("ctx2", ctx2)
    go watchContext("ctx3", ctx3)

    time.Sleep(1 * time.Second)
    fmt.Println("取消 ctx1...")
    cancel1() // 取消 ctx1，ctx2 和 ctx3 也会被取消

    time.Sleep(500 * time.Millisecond)
}

func watchContext(name string, ctx context.Context) {
    <-ctx.Done()
    fmt.Printf("%s 被取消: %v\n", name, ctx.Err())
}
```

**输出：**
```
取消 ctx1...
ctx1 被取消: context canceled
ctx2 被取消: context canceled
ctx3 被取消: context canceled
```

---

### 3. WithTimeout 与 WithDeadline

#### 3.1 WithTimeout 原理

`WithTimeout` 本质是 `WithDeadline` 的语法糖：

```go
// WithTimeout 的内部实现
func WithTimeout(parent Context, timeout time.Duration) (Context, CancelFunc) {
    return WithDeadline(parent, time.Now().Add(timeout))
}
```

#### 3.2 WithTimeout 基本用法

```go
package main

import (
    "context"
    "fmt"
    "time"
)

func main() {
    // 创建一个 2 秒超时的 Context
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel() // 即使超时，也建议调用 cancel 释放资源

    // 模拟一个耗时 3 秒的操作
    result, err := slowOperation(ctx)
    if err != nil {
        fmt.Println("操作失败:", err)
        return
    }
    fmt.Println("操作成功:", result)
}

func slowOperation(ctx context.Context) (string, error) {
    select {
    case <-time.After(3 * time.Second):
        return "操作完成", nil
    case <-ctx.Done():
        return "", ctx.Err() // 返回 DeadlineExceeded
    }
}
```

**输出：**
```
操作失败: context deadline exceeded
```

#### 3.3 WithDeadline 精确截止时间

```go
package main

import (
    "context"
    "fmt"
    "time"
)

func main() {
    // 设置一个精确的截止时间
    deadline := time.Now().Add(3 * time.Second)
    ctx, cancel := context.WithDeadline(context.Background(), deadline)
    defer cancel()

    fmt.Printf("截止时间: %v\n", ctx.Deadline())

    // 启动多个并发任务
    for i := 0; i < 5; i++ {
        go func(id int) {
            select {
            case <-time.After(time.Duration(id+1) * time.Second):
                fmt.Printf("任务 %d 完成\n", id)
            case <-ctx.Done():
                fmt.Printf("任务 %d 超时: %v\n", id, ctx.Err())
            }
        }(i)
    }

    <-ctx.Done()
    fmt.Println("Context 已过期:", ctx.Err())
    time.Sleep(1 * time.Second) // 等待 goroutine 输出
}
```

**输出：**
```
截止时间: 2026-05-03 xx:xx:xx.xxxxxxxxxx +0800 CST m=+3.00xxxxxxx
任务 0 完成
任务 1 完成
任务 2 完成
任务 3 超时: context deadline exceeded
任务 4 超时: context deadline exceeded
Context 已过期: context deadline exceeded
```

#### 3.4 超时叠加与级联控制

在微服务架构中，超时需要逐层递减：

```
用户请求 (timeout: 5s)
    │
    ├── API Gateway (timeout: 4s)
    │       │
    │       ├── 服务 A (timeout: 3s)
    │       │       │
    │       │       ├── 数据库查询 (timeout: 2s)
    │       │       └── 缓存查询 (timeout: 500ms)
    │       │
    │       └── 服务 B (timeout: 3s)
    │
    └── 静态资源 (timeout: 2s)
```

```go
package main

import (
    "context"
    "fmt"
    "time"
)

// 模拟级联调用
func apiGateway(ctx context.Context) error {
    // 从用户请求的 Context 派生，超时更短
    ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
    defer cancel()

    // 并发调用两个下游服务
    errCh := make(chan error, 2)

    go func() {
        errCh <- callServiceA(ctx)
    }()
    go func() {
        errCh <- callServiceB(ctx)
    }()

    for i := 0; i < 2; i++ {
        if err := <-errCh; err != nil {
            return fmt.Errorf("下游服务失败: %w", err)
        }
    }
    return nil
}

func callServiceA(ctx context.Context) error {
    // 再次派生，超时更短
    ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
    defer cancel()

    return queryDatabase(ctx)
}

func callServiceB(ctx context.Context) error {
    select {
    case <-time.After(1 * time.Second):
        return nil
    case <-ctx.Done():
        return ctx.Err()
    }
}

func queryDatabase(ctx context.Context) error {
    select {
    case <-time.After(3 * time.Second): // 模拟慢查询
        return nil
    case <-ctx.Done():
        return fmt.Errorf("数据库查询超时: %w", ctx.Err())
    }
}

func main() {
    // 模拟用户请求，总超时 5 秒
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    start := time.Now()
    err := apiGateway(ctx)
    fmt.Printf("耗时: %v, 错误: %v\n", time.Since(start), err)
}
```

**输出：**
```
耗时: 2.001xxxxxs, 错误: 下游服务失败: 数据库查询超时: context deadline exceeded
```

---

### 4. WithValue 与请求范围数据

#### 4.1 WithValue 使用规范

`WithValue` 用于在 Context 中存储请求范围的元数据，**不用于传递可选参数**。

```go
package main

import (
    "context"
    "fmt"
)

// 定义自定义类型作为 key，避免冲突
type contextKey string

const (
    traceIDKey   contextKey = "traceID"
    userIDKey    contextKey = "userID"
    requestIDKey contextKey = "requestID"
)

func main() {
    // 设置值
    ctx := context.Background()
    ctx = context.WithValue(ctx, traceIDKey, "abc-123-def")
    ctx = context.WithValue(ctx, userIDKey, "user-456")

    // 读取值
    processRequest(ctx)
}

func processRequest(ctx context.Context) {
    // 类型断言获取值
    traceID, ok := ctx.Value(traceIDKey).(string)
    if !ok {
        fmt.Println("traceID 不存在")
        return
    }

    userID, _ := ctx.Value(userIDKey).(string)
    fmt.Printf("处理请求: traceID=%s, userID=%s\n", traceID, userID)

    // 向下传递
    callDownstream(ctx)
}

func callDownstream(ctx context.Context) {
    traceID := ctx.Value(traceIDKey).(string)
    fmt.Printf("调用下游: traceID=%s\n", traceID)
}
```

#### 4.2 WithValue 最佳实践

```go
// 正确：使用自定义类型作为 key
type contextKey string
const myKey contextKey = "myKey"

// 错误：使用内置类型作为 key（可能与其他包冲突）
const myKey2 = "myKey"  // string 类型，容易冲突

// 正确：存储不可变数据
ctx = context.WithValue(ctx, traceIDKey, "abc-123")

// 错误：存储可变数据或大数据
ctx = context.WithValue(ctx, "requestBody", largeByteBuffer) // 浪费内存
ctx = context.WithValue(ctx, "dbConn", db) // 可变状态不应放 Context
```

#### 4.3 Context Value 查找链

```
ctx3 (key1=value1, key2=value2)
  └── ctx2 (key3=value3)
        └── ctx1 (key1=value_original)
              └── Background()

查找 key1: ctx3 → 找到 value1，返回
查找 key3: ctx3 → ctx2 → 找到 value3，返回
查找 key4: ctx3 → ctx2 → ctx1 → Background → 返回 nil
```

```go
package main

import (
    "context"
    "fmt"
)

type key string

func main() {
    ctx1 := context.WithValue(context.Background(), key("name"), "ctx1-value")
    ctx2 := context.WithValue(ctx1, key("name"), "ctx2-value") // 覆盖同名 key
    ctx3 := context.WithValue(ctx2, key("extra"), "ctx3-extra")

    // 查找 "name"：从 ctx3 开始，找到 ctx2 设置的值
    fmt.Println("name =", ctx3.Value(key("name")))    // ctx2-value
    fmt.Println("extra =", ctx3.Value(key("extra")))   // ctx3-extra

    // 直接从 ctx1 查找
    fmt.Println("ctx1.name =", ctx1.Value(key("name"))) // ctx1-value
}
```

---

### 5. Context 在 HTTP 服务中的超时控制

#### 5.1 HTTP Server 的 Context

Go 的 `http.Request` 自带 Context（Go 1.7+），通过 `r.Context()` 获取：

```go
package main

import (
    "context"
    "fmt"
    "io"
    "net/http"
    "time"
)

func main() {
    http.HandleFunc("/api/data", handleData)
    http.HandleFunc("/api/timeout", handleWithTimeout)

    fmt.Println("服务器启动在 :8080")
    http.ListenAndServe(":8080", nil)
}

// handleData 使用请求自带的 Context
func handleData(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context() // 请求的 Context，客户端断开时自动取消

    // 模拟数据库查询
    data, err := queryWithContext(ctx)
    if err != nil {
        http.Error(w, err.Error(), http.StatusGatewayTimeout)
        return
    }

    io.WriteString(w, data)
}

// handleWithTimeout 创建更短超时的 Context
func handleWithTimeout(w http.ResponseWriter, r *http.Request) {
    // 从请求 Context 派生，设置 2 秒超时
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()

    result, err := slowDownstreamCall(ctx)
    if err != nil {
        http.Error(w, fmt.Sprintf("下游超时: %v", err), http.StatusGatewayTimeout)
        return
    }

    io.WriteString(w, result)
}

func queryWithContext(ctx context.Context) (string, error) {
    select {
    case <-time.After(100 * time.Millisecond):
        return `{"status": "ok"}`, nil
    case <-ctx.Done():
        return "", ctx.Err()
    }
}

func slowDownstreamCall(ctx context.Context) (string, error) {
    select {
    case <-time.After(3 * time.Second): // 模拟慢调用
        return "slow result", nil
    case <-ctx.Done():
        return "", ctx.Err()
    }
}
```

#### 5.2 HTTP Client 超时控制

```go
package main

import (
    "context"
    "fmt"
    "io"
    "net/http"
    "time"
)

func main() {
    // 方式 1：Client 级别超时（适用于所有请求）
    client := &http.Client{
        Timeout: 10 * time.Second,
    }

    // 方式 2：Request 级别超时（更灵活）
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, "GET", "http://localhost:8080/api/data", nil)
    if err != nil {
        fmt.Println("创建请求失败:", err)
        return
    }

    resp, err := client.Do(req)
    if err != nil {
        fmt.Println("请求失败:", err)
        return
    }
    defer resp.Body.Close()

    body, _ := io.ReadAll(resp.Body)
    fmt.Printf("状态码: %d, 响应: %s\n", resp.StatusCode, body)
}
```

#### 5.3 中间件模式：请求超时

```go
package main

import (
    "context"
    "fmt"
    "net/http"
    "time"
)

// TimeoutMiddleware 为每个请求设置超时
func TimeoutMiddleware(timeout time.Duration) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            ctx, cancel := context.WithTimeout(r.Context(), timeout)
            defer cancel()

            // 用带超时的 Context 替换请求的 Context
            r = r.WithContext(ctx)

            // 使用 channel 捕获 panic 和完成信号
            done := make(chan struct{})
            go func() {
                defer func() {
                    if p := recover(); p != nil {
                        // 处理 panic
                        http.Error(w, "Internal Server Error", http.StatusInternalServerError)
                    }
                    close(done)
                }()
                next.ServeHTTP(w, r)
            }()

            select {
            case <-done:
                // 请求正常完成
            case <-ctx.Done():
                // 超时
                if !r.Context().Done() != nil {
                    http.Error(w, "Request Timeout", http.StatusGatewayTimeout)
                }
            }
        })
    }
}

func main() {
    mux := http.NewServeMux()

    mux.HandleFunc("/fast", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "fast response")
    })

    mux.HandleFunc("/slow", func(w http.ResponseWriter, r *http.Request) {
        select {
        case <-time.After(5 * time.Second):
            fmt.Fprintf(w, "slow response")
        case <-r.Context().Done():
            // 请求已取消，不需要写响应
            return
        }
    })

    // 应用超时中间件
    handler := TimeoutMiddleware(3 * time.Second)(mux)

    fmt.Println("服务器启动在 :8080")
    http.ListenAndServe(":8080", handler)
}
```

#### 5.4 生产级 HTTP Server 配置

```go
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", healthHandler)
    mux.HandleFunc("/api/data", dataHandler)

    server := &http.Server{
        Addr:         ":8080",
        Handler:      mux,
        ReadTimeout:  5 * time.Second,  // 读取请求体的超时
        WriteTimeout: 10 * time.Second, // 写响应的超时
        IdleTimeout:  120 * time.Second, // Keep-Alive 空闲超时
    }

    // 优雅关闭
    go func() {
        sigCh := make(chan os.Signal, 1)
        signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
        <-sigCh

        log.Println("收到关闭信号，开始优雅关闭...")

        // 创建关闭超时的 Context
        ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()

        // 停止接受新连接，等待现有请求完成
        if err := server.Shutdown(ctx); err != nil {
            log.Printf("关闭超时: %v", err)
        }
        log.Println("服务器已关闭")
    }()

    log.Printf("服务器启动在 %s", server.Addr)
    if err := server.ListenAndServe(); err != http.ErrServerClosed {
        log.Fatalf("服务器异常: %v", err)
    }
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("OK"))
}

func dataHandler(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    // ... 业务逻辑
    select {
    case <-ctx.Done():
        return
    default:
        w.Write([]byte(`{"data": "value"}`))
    }
}
```

---

### 6. Context 与数据库查询超时

#### 6.1 database/sql 的 Context 支持

Go 标准库的 `database/sql` 提供了 Context 感知的方法：

```go
package main

import (
    "context"
    "database/sql"
    "fmt"
    "log"
    "time"

    _ "github.com/go-sql-driver/mysql"
)

func main() {
    db, err := sql.Open("mysql", "user:password@tcp(localhost:3306)/mydb")
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()

    // 设置连接池参数
    db.SetMaxOpenConns(25)
    db.SetMaxIdleConns(5)
    db.SetConnMaxLifetime(5 * time.Minute)
    db.SetConnMaxIdleTime(1 * time.Minute)

    // 使用 Context 的查询
    ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
    defer cancel()

    var name string
    err = db.QueryRowContext(ctx, "SELECT name FROM users WHERE id = ?", 1).Scan(&name)
    if err != nil {
        if err == context.DeadlineExceeded {
            log.Println("查询超时")
        } else {
            log.Printf("查询失败: %v", err)
        }
        return
    }

    fmt.Printf("用户名: %s\n", name)
}

// 查询所有 Context 感知的方法：
// db.QueryContext(ctx, query, args...)
// db.QueryRowContext(ctx, query, args...)
// db.ExecContext(ctx, query, args...)
// db.PrepareContext(ctx, query)
// tx.ExecContext(ctx, query, args...)
// tx.QueryContext(ctx, query, args...)
// rows.Close() // 不接受 Context，但应在 Context 取消时调用
```

#### 6.2 事务超时控制

```go
package main

import (
    "context"
    "database/sql"
    "fmt"
    "log"
    "time"

    _ "github.com/go-sql-driver/mysql"
)

func transferMoney(ctx context.Context, db *sql.DB, fromID, toID int, amount float64) error {
    // 事务超时
    txCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    tx, err := db.BeginTx(txCtx, nil)
    if err != nil {
        return fmt.Errorf("开始事务失败: %w", err)
    }
    defer tx.Rollback() // 如果 Commit 成功，Rollback 是 no-op

    // 扣款
    _, err = tx.ExecContext(txCtx,
        "UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?",
        amount, fromID, amount)
    if err != nil {
        return fmt.Errorf("扣款失败: %w", err)
    }

    // 入账
    _, err = tx.ExecContext(txCtx,
        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
        amount, toID)
    if err != nil {
        return fmt.Errorf("入账失败: %w", err)
    }

    // 提交事务
    if err := tx.Commit(); err != nil {
        return fmt.Errorf("提交事务失败: %w", err)
    }

    return nil
}
```

---

### 7. Context 常见误用与陷阱

#### 7.1 误用 1：将 Context 存储在结构体中

```go
// 错误：Context 不应存储在结构体中
type Service struct {
    ctx context.Context // 错误！
    db  *sql.DB
}

// 正确：Context 作为函数参数传递，通常是第一个参数
type Service struct {
    db *sql.DB
}

func (s *Service) GetUser(ctx context.Context, id int) (*User, error) {
    // 使用传入的 Context
    return s.db.QueryRowContext(ctx, "SELECT * FROM users WHERE id = ?", id)
}
```

#### 7.2 误用 2：不检查 ctx.Done()

```go
// 错误：不检查取消信号
func badWorker(ctx context.Context) {
    for i := 0; ; i++ {
        doWork() // 即使 ctx 已取消，仍在工作
    }
}

// 正确：定期检查取消信号
func goodWorker(ctx context.Context) error {
    for i := 0; ; i++ {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }
        doWork()
    }
}
```

#### 7.3 误用 3：忽略 cancel 函数

```go
// 错误：忽略 cancel
func bad() {
    ctx, _ := context.WithTimeout(context.Background(), 5*time.Second)
    // cancel 永远不会被调用，子 Context 泄漏
    doSomething(ctx)
}

// 正确：defer cancel
func good() {
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    doSomething(ctx)
}
```

#### 7.4 误用 4：在 WithValue 中传递业务参数

```go
// 错误：用 WithValue 传递业务参数
ctx = context.WithValue(ctx, "userID", userID)     // 可以
ctx = context.WithValue(ctx, "pageSize", 20)        // 错误！这是业务参数
ctx = context.WithValue(ctx, "sortBy", "name")      // 错误！这是业务参数

// 正确：业务参数应作为函数参数
func ListUsers(ctx context.Context, pageSize int, sortBy string) ([]User, error) {
    // ...
}
```

#### 7.5 误用 5：使用 nil Context

```go
// 错误：传入 nil Context
func bad() {
    doSomething(nil) // panic!
}

// 正确：如果不确定用哪个 Context，使用 context.TODO()
func maybeGood() {
    doSomething(context.TODO()) // 明确表示"暂时不确定"
}
```

---

### 8. SRE 实战：多服务调用超时编排

#### 8.1 微服务聚合请求

```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "sync"
    "time"
)

// ServiceResponse 服务调用结果
type ServiceResponse struct {
    Service string `json:"service"`
    Data    string `json:"data,omitempty"`
    Error   string `json:"error,omitempty"`
    Latency int64  `json:"latency_ms"`
}

// AggregatedResponse 聚合响应
type AggregatedResponse struct {
    Services []ServiceResponse `json:"services"`
    TotalMs  int64             `json:"total_ms"`
}

// callService 调用下游服务，支持超时
func callService(ctx context.Context, name, url string) ServiceResponse {
    start := time.Now()

    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return ServiceResponse{
            Service: name,
            Error:   err.Error(),
            Latency: time.Since(start).Milliseconds(),
        }
    }

    client := &http.Client{Timeout: 10 * time.Second}
    resp, err := client.Do(req)
    if err != nil {
        return ServiceResponse{
            Service: name,
            Error:   err.Error(),
            Latency: time.Since(start).Milliseconds(),
        }
    }
    defer resp.Body.Close()

    var data string
    json.NewDecoder(resp.Body).Decode(&data)
    return ServiceResponse{
        Service: name,
        Data:    data,
        Latency: time.Since(start).Milliseconds(),
    }
}

// aggregateHandler 聚合多个服务的响应
func aggregateHandler(w http.ResponseWriter, r *http.Request) {
    // 从请求派生 Context，设置 3 秒超时
    ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
    defer cancel()

    services := map[string]string{
        "user-service":    "http://user-service:8080/api/user",
        "order-service":   "http://order-service:8080/api/orders",
        "product-service": "http://product-service:8080/api/products",
    }

    var (
        mu       sync.Mutex
        wg       sync.WaitGroup
        responses []ServiceResponse
    )

    start := time.Now()

    for name, url := range services {
        wg.Add(1)
        go func(name, url string) {
            defer wg.Done()
            resp := callService(ctx, name, url)
            mu.Lock()
            responses = append(responses, resp)
            mu.Unlock()
        }(name, url)
    }

    wg.Wait()

    result := AggregatedResponse{
        Services: responses,
        TotalMs:  time.Since(start).Milliseconds(),
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(result)
}

func main() {
    http.HandleFunc("/api/aggregate", aggregateHandler)
    fmt.Println("聚合服务启动在 :8080")
    http.ListenAndServe(":8080", nil)
}
```

#### 8.2 SRE 巡检脚本中的超时控制

```go
package main

import (
    "context"
    "fmt"
    "net"
    "sync"
    "time"
)

// CheckResult 巡检结果
type CheckResult struct {
    Host    string
    Port    int
    Status  string
    Latency time.Duration
    Error   error
}

// checkPort 检查端口是否可达
func checkPort(ctx context.Context, host string, port int) CheckResult {
    start := time.Now()
    addr := fmt.Sprintf("%s:%d", host, port)

    // 使用 DialContext 支持超时
    var d net.Dialer
    conn, err := d.DialContext(ctx, "tcp", addr)
    if err != nil {
        return CheckResult{
            Host:    host,
            Port:    port,
            Status:  "DOWN",
            Latency: time.Since(start),
            Error:   err,
        }
    }
    conn.Close()

    return CheckResult{
        Host:    host,
        Port:    port,
        Status:  "UP",
        Latency: time.Since(start),
    }
}

// runHealthCheck 批量健康检查
func runHealthCheck() {
    // 总超时 30 秒
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    targets := []struct {
        host string
        port int
    }{
        {"web-01", 80},
        {"web-02", 80},
        {"db-01", 3306},
        {"cache-01", 6379},
        {"mq-01", 5672},
    }

    var (
        wg      sync.WaitGroup
        mu      sync.Mutex
        results []CheckResult
    )

    for _, t := range targets {
        wg.Add(1)
        go func(host string, port int) {
            defer wg.Done()
            result := checkPort(ctx, host, port)
            mu.Lock()
            results = append(results, result)
            mu.Unlock()
        }(t.host, t.port)
    }

    wg.Wait()

    // 输出结果
    fmt.Println("=== 健康检查结果 ===")
    for _, r := range results {
        status := "✓"
        if r.Status == "DOWN" {
            status = "✗"
        }
        fmt.Printf("%s %s:%d  %s  %v\n", status, r.Host, r.Port, r.Status, r.Latency)
    }
}

func main() {
    runHealthCheck()
}
```

---

## 💻 实战练习

### 练习 1：实现一个带超时的 HTTP 下载器

要求：
- 支持设置总超时和单次重试超时
- 支持 Context 取消
- 下载进度回调

```go
package main

import (
    "context"
    "fmt"
    "io"
    "net/http"
    "os"
    "time"
)

// DownloadConfig 下载配置
type DownloadConfig struct {
    URL         string
    Dest        string
    TotalTimeout time.Duration
    RetryTimeout time.Duration
    MaxRetries  int
    OnProgress  func(bytesRead int64)
}

// Download 带超时和重试的下载
func Download(ctx context.Context, cfg DownloadConfig) error {
    var lastErr error

    for attempt := 0; attempt <= cfg.MaxRetries; attempt++ {
        if attempt > 0 {
            fmt.Printf("第 %d 次重试...\n", attempt)
            select {
            case <-time.After(time.Duration(attempt) * time.Second):
            case <-ctx.Done():
                return ctx.Err()
            }
        }

        // 每次重试创建新的超时 Context
        retryCtx, cancel := context.WithTimeout(ctx, cfg.RetryTimeout)
        lastErr = downloadOnce(retryCtx, cfg)
        cancel()

        if lastErr == nil {
            return nil
        }

        fmt.Printf("下载失败: %v\n", lastErr)
    }

    return fmt.Errorf("重试 %d 次后仍失败: %w", cfg.MaxRetries, lastErr)
}

func downloadOnce(ctx context.Context, cfg DownloadConfig) error {
    req, err := http.NewRequestWithContext(ctx, "GET", cfg.URL, nil)
    if err != nil {
        return err
    }

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        return fmt.Errorf("HTTP %d", resp.StatusCode)
    }

    f, err := os.Create(cfg.Dest)
    if err != nil {
        return err
    }
    defer f.Close()

    buf := make([]byte, 32*1024)
    var totalRead int64

    for {
        n, err := resp.Body.Read(buf)
        if n > 0 {
            if _, wErr := f.Write(buf[:n]); wErr != nil {
                return wErr
            }
            totalRead += int64(n)
            if cfg.OnProgress != nil {
                cfg.OnProgress(totalRead)
            }
        }
        if err != nil {
            if err == io.EOF {
                return nil
            }
            return err
        }
    }
}

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    cfg := DownloadConfig{
        URL:          "https://example.com/largefile.tar.gz",
        Dest:         "/tmp/largefile.tar.gz",
        TotalTimeout: 30 * time.Second,
        RetryTimeout: 10 * time.Second,
        MaxRetries:   3,
        OnProgress: func(bytesRead int64) {
            fmt.Printf("\r已下载: %d bytes", bytesRead)
        },
    }

    if err := Download(ctx, cfg); err != nil {
        fmt.Printf("下载失败: %v\n", err)
        return
    }
    fmt.Println("\n下载完成")
}
```

### 练习 2：实现请求链路追踪

要求：
- 使用 WithValue 传递 trace ID
- 每个服务调用记录耗时
- 支持取消传播

```go
package main

import (
    "context"
    "fmt"
    "math/rand"
    "time"
)

type traceKey struct{}

// TraceInfo 链路追踪信息
type TraceInfo struct {
    TraceID   string
    Spans     []Span
}

type Span struct {
    Name      string
    Start     time.Time
    Duration  time.Duration
    Status    string
}

// WithTrace 在 Context 中注入 trace 信息
func WithTrace(ctx context.Context) context.Context {
    traceID := fmt.Sprintf("trace-%016x", rand.Int63())
    info := &TraceInfo{TraceID: traceID}
    return context.WithValue(ctx, traceKey{}, info)
}

// GetTrace 从 Context 获取 trace 信息
func GetTrace(ctx context.Context) *TraceInfo {
    if info, ok := ctx.Value(traceKey{}).(*TraceInfo); ok {
        return info
    }
    return nil
}

// StartSpan 开始一个新的 span
func StartSpan(ctx context.Context, name string) (context.Context, func()) {
    info := GetTrace(ctx)
    if info == nil {
        return ctx, func() {}
    }

    start := time.Now()
    span := Span{Name: name, Start: start}
    info.Spans = append(info.Spans, span)
    idx := len(info.Spans) - 1

    return ctx, func() {
        info.Spans[idx].Duration = time.Since(start)
        info.Spans[idx].Status = "OK"
    }
}

// 模拟服务调用
func callUserService(ctx context.Context) error {
    _, done := StartSpan(ctx, "user-service")
    defer done()
    time.Sleep(100 * time.Millisecond)
    return nil
}

func callOrderService(ctx context.Context) error {
    _, done := StartSpan(ctx, "order-service")
    defer done()
    time.Sleep(150 * time.Millisecond)
    return nil
}

func callPaymentService(ctx context.Context) error {
    _, done := StartSpan(ctx, "payment-service")
    defer done()
    time.Sleep(200 * time.Millisecond)
    return nil
}

func main() {
    ctx := WithTrace(context.Background())
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    _, done := StartSpan(ctx, "api-gateway")
    defer done()

    callUserService(ctx)
    callOrderService(ctx)
    callPaymentService(ctx)

    info := GetTrace(ctx)
    fmt.Printf("Trace ID: %s\n", info.TraceID)
    for _, span := range info.Spans {
        fmt.Printf("  %s: %v [%s]\n", span.Name, span.Duration, span.Status)
    }
}
```

### 练习 3：Context 泄漏检测

找出以下代码中的 Context 泄漏问题并修复：

```go
package main

import (
    "context"
    "fmt"
    "time"
)

// 问题代码：找出泄漏点
func leakyFunction() {
    for i := 0; i < 1000; i++ {
        ctx, _ := context.WithTimeout(context.Background(), 5*time.Second)
        go doBackgroundWork(ctx)
    }
}

func doBackgroundWork(ctx context.Context) {
    select {
    case <-time.After(10 * time.Second):
        fmt.Println("完成")
    case <-ctx.Done():
        fmt.Println("取消")
    }
}

// 修复版本
func fixedFunction() {
    for i := 0; i < 1000; i++ {
        ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
        // 不要在这里 defer cancel()，因为循环会积累大量 defer

        go func(ctx context.Context, cancel context.CancelFunc) {
            defer cancel() // 在 goroutine 内部 defer
            doBackgroundWork(ctx)
        }(ctx, cancel)
    }
}
```

---

## 🎯 面试题精选

### 1. Context 的 Done() channel 什么时候关闭？

**参考答案：**
Done() channel 在以下情况关闭：
- 调用了 WithCancel 返回的 cancel 函数
- WithTimeout 或 WithDeadline 设置的时间到达
- 父 Context 的 Done channel 关闭（取消传播）

Background() 和 TODO() 的 Done() 返回 nil，永远不会关闭。

### 2. Context.Value 的查找是线程安全的吗？

**参考答案：**
是的。Context 的实现保证了 Value 查找是线程安全的。Context 是不可变的（immutable），WithValue 创建新的 Context 节点，不修改已有节点。多个 goroutine 可以同时读取同一个 Context 的值。

### 3. 为什么 Context 应该作为函数的第一个参数？

**参考答案：**
- 这是 Go 官方推荐的惯例（idiomatic Go）
- 明确标识函数支持取消和超时
- 便于静态分析工具检查
- 保持一致性，降低代码阅读成本
- Context 不应存储在结构体中，因为它代表的是请求级别的生命周期

### 4. WithTimeout 和 WithDeadline 的区别是什么？

**参考答案：**
- `WithTimeout(parent, timeout)` 是 `WithDeadline(parent, time.Now().Add(timeout))` 的语法糖
- WithTimeout 指定相对时间（持续时间）
- WithDeadline 指定绝对时间（截止时间点）
- 当需要精确控制截止时间时用 WithDeadline，一般场景用 WithTimeout 更直观

### 5. 如果一个 goroutine 忽略了 Context 的取消信号会怎样？

**参考答案：**
goroutine 会继续运行直到自然结束，导致资源泄漏。在高并发场景下，大量泄漏的 goroutine 会消耗内存和 CPU。正确做法是定期检查 `ctx.Done()`，收到信号后清理资源并返回。如果 goroutine 执行的是不可中断的操作（如文件 I/O），应使用带 Context 的 API 版本。

### 6. 如何调试 Context 泄漏？

**参考答案：**
- 使用 `runtime.NumGoroutine()` 监控 goroutine 数量
- 使用 pprof 的 goroutine profile：`go tool pprof http://localhost:6060/debug/pprof/goroutine`
- 检查代码中是否有 `WithCancel/WithTimeout/WithDeadline` 忽略了 cancel 函数
- 使用 goleak（uber出品）在测试中检测 goroutine 泄漏

### 7. Context 的 Err() 返回值有哪些？

**参考答案：**
- `nil`：Done channel 尚未关闭
- `context.Canceled`：Context 被主动取消（调用了 cancel 函数）
- `context.DeadlineExceeded`：超过了截止时间

### 8. 在 HTTP Handler 中，r.Context() 什么时候会被取消？

**参考答案：**
- 客户端断开连接（客户端取消请求）
- Server.Shutdown() 被调用时
- 从 r.Context() 派生的 WithTimeout/WithDeadline 超时
- 但 Server.ReadTimeout 和 Server.WriteTimeout 不会取消 Context

### 9. WithValue 的 key 为什么建议用自定义类型？

**参考答案：**
如果使用 `string` 等内置类型作为 key，不同包可能使用相同的字符串值，导致 key 冲突。使用自定义类型（如 `type contextKey string`）可以利用 Go 的类型系统避免冲突。即使两个包使用相同的字符串值，不同类型也是不同的 key。

### 10. 如何实现 Context 的链路追踪？

**参考答案：**
使用 WithValue 存储 trace ID（通常是第一个中间件设置），然后在每个服务调用时从 Context 中提取 trace ID 并传递给下游。可以结合 OpenTelemetry 等框架，它们的 Span Context 也是通过 Go Context 传播的。

---

## 📚 深入阅读

- [Go 官方文档：context 包](https://pkg.go.dev/context)
- [Go Blog：Contexts and Cancellation](https://go.dev/blog/context)
- [Go 标准库源码：context.go](https://github.com/golang/go/blob/master/src/context/context.go)
- [Effective Go: Concurrency](https://go.dev/doc/effective_go#concurrency)
- [Go Concurrency Patterns: Context](https://www.youtube.com/watch?v=LSzR0VEaWnY)
- 《Go 语言实战》第 7 章：并发模式
- 《Concurrency in Go》第 4 章：Concurrency Patterns

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出 Context 树形结构，说明取消传播方向
- [ ] 能解释 WithCancel、WithTimeout、WithDeadline 的区别和底层实现
- [ ] 能说明 WithValue 的查找机制和 key 设计规范
- [ ] 能解释 Context 与 goroutine 泄漏的关系

### 实操检查点
- [ ] 能实现 HTTP 请求的超时控制（Server 和 Client 端）
- [ ] 能实现数据库查询的超时控制
- [ ] 能实现多服务并发调用的超时编排
- [ ] 能使用 Context 传递请求范围数据（trace ID 等）

### 能力验证标准
- [ ] 能识别并修复 Context 泄漏代码
- [ ] 能设计微服务架构的超时策略（级联超时递减）
- [ ] 能回答 Context 相关的面试题（8/10 正确率）
