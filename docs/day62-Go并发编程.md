# Day 62: Go 并发编程

> 📅 日期：2026-05-03
> 📖 学习主题：Go 并发编程 — GMP 调度器、Channel、sync 包、并发模式
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 58 (Go 基础语法), Day 59 (函数与错误处理), Day 60 (数据结构)

---

## 🎯 学习目标

- 深入理解 Go GMP 调度器模型的工作原理（面试重点中的重点）
- 掌握 channel 的底层实现和使用模式
- 熟练使用 sync 包的并发原语（Mutex, WaitGroup, Once, Pool）
- 理解 context 包的传播机制和超时控制
- 掌握 fan-in/fan-out/pipeline/worker pool 四大并发模式
- 能使用 race detector 检测并发问题

---

## 📖 核心知识点

### 1. Goroutine 基础

#### 1.1 什么是 Goroutine

Goroutine 是 Go runtime 管理的轻量级线程，由 Go 调度器而非操作系统调度：

```
OS 线程 vs Goroutine 对比：

┌─────────────────┬──────────────────┬──────────────────┐
│     特性         │    OS 线程       │    Goroutine     │
├─────────────────┼──────────────────┼──────────────────┤
│ 初始栈大小       │ 1-2 MB           │ 2 KB (可动态增长) │
│ 创建开销         │ ~10μs (系统调用) │ ~0.3μs           │
│ 切换开销         │ ~1-10μs (内核态) │ ~0.2μs (用户态)  │
│ 最大数量         │ ~千级            │ ~百万级           │
│ 调度方式         │ OS 内核抢占式    │ Go runtime 协作式 │
│ 内存占用         │ 高               │ 极低              │
└─────────────────┴──────────────────┴──────────────────┘
```

```go
package main

import (
    "fmt"
    "runtime"
    "sync"
    "time"
)

func main() {
    fmt.Printf("初始 goroutine 数量: %d\n", runtime.NumGoroutine())
    fmt.Printf("CPU 核心数: %d\n", runtime.NumCPU())

    var wg sync.WaitGroup

    // 批量创建 goroutine
    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            time.Sleep(10 * time.Millisecond)
            // 每个 goroutine 的栈只有 2KB，100 个总共约 200KB
        }(i)
    }

    fmt.Printf("创建后 goroutine 数量: %d\n", runtime.NumGoroutine())
    wg.Wait()
    fmt.Printf("结束后 goroutine 数量: %d\n", runtime.NumGoroutine())
}
```

---

### 2. GMP 调度器模型（核心重点）

#### 2.1 GMP 三要素

GMP 是 Go 并发调度的核心模型，理解它是 Go 并发编程的关键：

```
GMP 模型全景图：

G (Goroutine)          M (Machine/OS Thread)       P (Processor/上下文)
┌──────────────┐       ┌──────────────────┐        ┌─────────────────┐
│ goroutine    │       │ OS 线程           │        │ 本地运行队列     │
│ - 栈 (2KB+)  │       │ - 执行 Go 代码    │        │ - 最多 256 个 G │
│ - 程序计数器  │       │ - 绑定一个 P      │        │                 │
│ - 通道操作    │       │ - 数量可超过 P    │        │ mcache          │
│ - defer 链   │       │ - 有最大限制      │        │ - 内存分配缓存   │
│ - panic 信息 │       │   (默认 10000)    │        │                 │
│ - goroutineID│       │                  │        │ 绑定 G 和 M     │
└──────┬───────┘       └────────┬─────────┘        └────────┬────────┘
       │                        │                           │
       │    本地队列             │    绑定执行               │    调度
       ▼                        ▼                           ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │                    全局运行队列 (Global Run Queue)                │
  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐    │
  │  │ G1  │ │ G2  │ │ G3  │ │ G4  │ │ G5  │ │ G6  │ │ ... │    │
  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘    │
  └─────────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   netpoller          │
                    │  (网络轮询器)         │
                    │  - epoll/kqueue      │
                    │  - 异步 I/O          │
                    └─────────────────────┘
```

- **G (Goroutine):** Go 协程，包含栈、程序计数器、goroutine ID 等状态
- **M (Machine):** OS 线程，真正执行代码的实体，由操作系统管理
- **P (Processor):** 逻辑处理器，持有本地运行队列和内存缓存，数量默认等于 CPU 核心数

#### 2.2 GMP 调度流程

```
正常调度流程：

1. 创建 Goroutine:
   main() → go func() → 创建 G → 放入 P 的本地队列
                          │
                          ▼
                   本地队列满了？
                   ├── 否 → 放入本地队列尾部
                   └── 是 → 将本地队列前半部分 + G 移到全局队列

2. 执行 Goroutine:
   P 绑定 M → M 从 P 的本地队列取 G → 执行 G
              │
              ▼
         本地队列空了？
         ├── 否 → 继续取下一个 G
         └── 是 → 尝试从其他地方获取 G
                   │
                   ├── 1. 从全局队列获取（每 61 次调度检查一次）
                   ├── 2. 从其他 P 的本地队列偷取（work stealing）
                   └── 3. 从 netpoller 获取就绪的 G
                          │
                          └── 都没有 → M 进入休眠

3. Goroutine 让出 CPU:
   - 主动让出: runtime.Gosched()
   - 系统调用: 进入阻塞 → M 释放 P → P 绑定空闲 M
   - channel 阻塞: G 进入等待队列 → M 继续执行其他 G
   - GC 操作: 需要 STW 时暂停所有 G
```

```go
package main

import (
    "fmt"
    "runtime"
    "time"
)

func main() {
    // 设置 P 的数量（逻辑处理器数量）
    // 默认等于 CPU 核心数
    fmt.Printf("P 的数量: %d\n", runtime.GOMAXPROCS(0))

    // 可以手动调整（通常不需要）
    runtime.GOMAXPROCS(4)

    // 查看当前 goroutine 数量
    fmt.Printf("goroutine 数量: %d\n", runtime.NumGoroutine())

    // 让出当前 goroutine 的执行权
    go func() {
        for i := 0; i < 3; i++ {
            fmt.Println("goroutine 执行中")
            runtime.Gosched() // 主动让出
        }
    }()

    time.Sleep(time.Second)
}
```

#### 2.3 Work Stealing 机制

```
Work Stealing（工作窃取）算法：

初始状态：P1 有 4 个 G，P2 空闲
┌─────────────────────┐    ┌─────────────────────┐
│ P1 的本地队列        │    │ P2 的本地队列        │
│ [G1] [G2] [G3] [G4] │    │ [空]                 │
└─────────────────────┘    └─────────────────────┘

P2 的 M 执行完当前 G 后，发现本地队列为空：
  1. 全局队列 → 空
  2. 窃取 P1 的 G → 成功！

窃取后：
┌─────────────────────┐    ┌─────────────────────┐
│ P1 的本地队列        │    │ P2 的本地队列        │
│ [G1] [G2]           │    │ [G3] [G4]           │
└─────────────────────┘    └─────────────────────┘

窃取规则：
- 从目标 P 的本地队列尾部窃取
- 窃取一半的 G（保证负载均衡）
- 优先窃取大任务
```

```go
package main

import (
    "fmt"
    "runtime"
    "sync"
    "time"
)

func main() {
    // 故意设置 1 个 P，观察调度行为
    runtime.GOMAXPROCS(1)

    var wg sync.WaitGroup

    // 创建多个 goroutine
    for i := 0; i < 5; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            fmt.Printf("Goroutine %d 开始执行\n", id)
            time.Sleep(100 * time.Millisecond)
            fmt.Printf("Goroutine %d 执行完毕\n", id)
        }(i)
    }

    wg.Wait()

    // 恢复默认 P 数量
    runtime.GOMAXPROCS(runtime.NumCPU())
}
```

#### 2.4 系统调用与 GMP 交互

```
G 进入系统调用时的调度：

1. G 发起系统调用（如文件读写）
   ┌───┐    ┌───┐    ┌───┐
   │ G │ →  │ M │ →  │ P │
   └───┘    └───┘    └───┘
              │
              │ 系统调用阻塞
              ▼
2. M 阻塞在系统调用上，P 与 M 解绑
   ┌───┐    ┌───┐         ┌───┐
   │ G │ →  │ M │(阻塞)    │ P │(空闲)
   └───┘    └───┘         └───┘
                            │
                            │ 找到或创建空闲 M
                            ▼
3. P 绑定新的 M，继续执行其他 G
   ┌───┐    ┌───┐    ┌───┐
   │G6 │ →  │M2 │ ←  │ P │
   └───┘    └───┘    └───┘

4. 系统调用完成后，G 尝试获取空闲 P
   ┌───┐    ┌───┐
   │ G │ →  │ M │    获取 P → 放入本地队列
   └───┘    └───┘    没有 P → G 放入全局队列
```

```go
package main

import (
    "fmt"
    "os"
    "runtime"
    "sync"
    "time"
)

func main() {
    fmt.Printf("系统调用前 - goroutine 数: %d, M 数: %d\n",
        runtime.NumGoroutine(), runtime.NumCPU())

    var wg sync.WaitGroup

    // 模拟多个系统调用阻塞
    for i := 0; i < 5; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            // 系统调用：文件操作
            f, _ := os.CreateTemp("", fmt.Sprintf("test-%d-*", id))
            defer os.Remove(f.Name())
            defer f.Close()

            time.Sleep(100 * time.Millisecond) // 模拟 I/O 耗时
            fmt.Printf("Goroutine %d 完成系统调用\n", id)
        }(i)
    }

    wg.Wait()
}
```

#### 2.5 Goroutine 栈增长

```
Goroutine 栈增长机制：

初始栈: 2KB
┌──────────────────┐
│  栈空间 (2KB)     │
│  ↓ 栈增长方向     │
│  [函数调用帧]     │
│  [局部变量]       │
│  [ ... ]          │
└──────────────────┘

栈空间不足时 → 分配更大的栈（翻倍）→ 拷贝旧栈 → 更新指针

Go 1.4+ 使用连续栈（contiguous stack）：
- 分配 2 倍大小的新栈
- 将旧栈内容拷贝到新栈
- 调整所有指向旧栈的指针

最大栈大小：默认 1GB（可通过 runtime.SetMaxStack 调整）

常见问题：
- 无限递归导致栈溢出: "runtime: goroutine stack exceeds 1000000000-byte limit"
- 栈增长有微小开销，在极端情况下需要注意
```

```go
package main

import (
    "fmt"
    "runtime"
)

func main() {
    // 查看当前栈大小
    var buf [64]byte
    n := runtime.Stack(buf[:], false)
    fmt.Printf("当前栈信息: %s\n", buf[:n])

    // 演示栈增长
    printStackSize(0)
}

func printStackSize(depth int) {
    var buf [1024]byte
    n := runtime.Stack(buf[:], false)
    if depth == 0 {
        fmt.Printf("初始栈大小: ~%d bytes\n", n)
    }
    if depth < 3 {
        printStackSize(depth + 1)
    }
}
```

#### 2.6 抢占式调度

```
Go 1.14+ 基于信号的异步抢占：

问题：G 长时间占用 P（如死循环），其他 G 饿死
for {
    // 没有任何函数调用，没有让出点
    // 1.13 之前：其他 G 无法调度
}

解决方案：
1. sysmon 后台监控线程（独立于 GMP，不绑定 P）
   - 每 20μs 检查一次
   - 发现运行超过 10ms 的 G → 发送 SIGURG 信号

2. 信号处理：
   SIGURG → 进入 signal handler → 保存 G 状态 → 放回队列 → 调度其他 G

3. 协作式抢占点（仍然优先）：
   - 函数调用时检查抢占标志
   - channel 操作
   - runtime.Gosched()
   - GC 相关操作

时间线：
  G 运行中 → 超过 10ms → sysmon 发送 SIGURG → G 被抢占 → P 执行其他 G
```

```go
package main

import (
    "fmt"
    "runtime"
    "sync/atomic"
    "time"
)

func main() {
    runtime.GOMAXPROCS(1) // 只用 1 个 P

    var count int64

    // 死循环 goroutine — 在 Go 1.14+ 会被异步抢占
    go func() {
        for {
            atomic.AddInt64(&count, 1)
            // 没有主动让出，但 Go 1.14+ 的异步抢占会介入
        }
    }()

    // 主 goroutine 能够被调度（因为异步抢占）
    for i := 0; i < 5; i++ {
        time.Sleep(100 * time.Millisecond)
        fmt.Printf("主 goroutine 运行中, 计数: %d\n", atomic.LoadInt64(&count))
    }
}
```

---

### 3. Channel 原理与使用

#### 3.1 Channel 底层结构

```
Channel 内部结构 (runtime.hchan):

┌───────────────────────────────────────┐
│ hchan                                 │
├───────────────────────────────────────┤
│ qcount   uint    │ 当前队列中的元素数   │
│ dataqsiz uint    │ 环形队列的容量       │
│ buf      unsafe  │ 环形队列的指针       │
│ elemsize uint16  │ 元素大小            │
│ closed   uint32  │ 是否关闭            │
│ elemtype *_type  │ 元素类型            │
│ sendx    uint    │ 发送索引            │
│ recvx    uint    │ 接收索引            │
│ recvq    waitq   │ 接收等待队列 (链表)  │
│ sendq    waitq   │ 发送等待队列 (链表)  │
│ lock     mutex   │ 互斥锁             │
└───────────────────────────────────────┘

无缓冲 channel:
┌──────────────────────────────────────┐
│ send → 直接拷贝到接收者的栈           │
│ recv → 直接从发送者的栈拷贝           │
│ 没有中间缓冲，必须同步                │
└──────────────────────────────────────┘

有缓冲 channel (环形队列):
┌──────────────────────────────────────┐
│  ┌────┬────┬────┬────┬────┐         │
│  │ A  │ B  │ C  │    │    │  环形    │
│  └────┴────┴────┴────┴────┘         │
│      ↑recvx      ↑sendx             │
│                                      │
│  send: 放入 sendx 位置, sendx++      │
│  recv: 取出 recvx 位置, recvx++      │
│  索引到达末尾后回到头部 (模运算)      │
└──────────────────────────────────────┘
```

#### 3.2 Channel 操作

```go
package main

import "fmt"

func main() {
    // 无缓冲 channel（同步通信）
    ch := make(chan string)

    go func() {
        ch <- "hello from goroutine" // 发送（阻塞直到有人接收）
    }()

    msg := <-ch // 接收（阻塞直到有人发送）
    fmt.Println(msg)

    // 有缓冲 channel（异步通信，缓冲区满时阻塞）
    buffered := make(chan int, 3) // 缓冲区大小为 3

    buffered <- 1 // 不阻塞
    buffered <- 2 // 不阻塞
    buffered <- 3 // 不阻塞
    // buffered <- 4 // 阻塞！缓冲区已满

    fmt.Println(<-buffered) // 1
    fmt.Println(<-buffered) // 2
    fmt.Println(<-buffered) // 3

    // 单向 channel（用于类型约束）
    ch2 := make(chan int, 1)
    producer(ch2)
    consumer(ch2)
}

// 只能发送
func producer(ch chan<- int) {
    ch <- 42
}

// 只能接收
func consumer(ch <-chan int) {
    fmt.Println(<-ch)
}
```

#### 3.3 Channel 关闭与 range

```go
package main

import "fmt"

func generateNumbers(n int) <-chan int {
    ch := make(chan int)
    go func() {
        defer close(ch) // 发送完毕后关闭
        for i := 0; i < n; i++ {
            ch <- i
        }
    }()
    return ch
}

func main() {
    // range 自动检测 channel 关闭
    for num := range generateNumbers(5) {
        fmt.Println(num) // 0, 1, 2, 3, 4
    }

    // 手动检测关闭
    ch := make(chan int, 1)
    ch <- 42
    close(ch)

    val, ok := <-ch
    fmt.Printf("val=%d, ok=%v\n", val, ok) // val=42, ok=true

    val, ok = <-ch
    fmt.Printf("val=%d, ok=%v\n", val, ok) // val=0, ok=false（已关闭）

    // 关闭已关闭的 channel → panic
    // 关闭 nil channel → 永久阻塞
    // 向已关闭的 channel 发送 → panic
}
```

#### 3.4 Select 多路复用

```go
package main

import (
    "fmt"
    "time"
)

func main() {
    ch1 := make(chan string)
    ch2 := make(chan string)

    go func() {
        time.Sleep(100 * time.Millisecond)
        ch1 <- "from channel 1"
    }()

    go func() {
        time.Sleep(200 * time.Millisecond)
        ch2 <- "from channel 2"
    }()

    // select 等待多个 channel 中最先就绪的那个
    select {
    case msg := <-ch1:
        fmt.Println("Received:", msg)
    case msg := <-ch2:
        fmt.Println("Received:", msg)
    case <-time.After(300 * time.Millisecond):
        fmt.Println("Timeout!")
    }

    // 非阻塞 select
    ch3 := make(chan int, 1)
    select {
    case val := <-ch3:
        fmt.Println("Got:", val)
    default:
        fmt.Println("No data available") // 立即执行
    }

    // 永久等待（用于 main 保持运行）
    // select {}
}
```

---

### 4. sync 包

#### 4.1 sync.Mutex 互斥锁

```go
package main

import (
    "fmt"
    "sync"
)

// 线程安全的计数器
type SafeCounter struct {
    mu    sync.Mutex
    count int
}

func (c *SafeCounter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

func (c *SafeCounter) Get() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.count
}

func main() {
    counter := &SafeCounter{}
    var wg sync.WaitGroup

    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            counter.Inc()
        }()
    }

    wg.Wait()
    fmt.Printf("Final count: %d\n", counter.Get()) // 总是 1000
}
```

#### 4.2 sync.RWMutex 读写锁

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

// 适用于读多写少场景
type ConfigStore struct {
    mu     sync.RWMutex
    config map[string]string
}

func NewConfigStore() *ConfigStore {
    return &ConfigStore{config: make(map[string]string)}
}

func (cs *ConfigStore) Get(key string) string {
    cs.mu.RLock()         // 读锁：多个读可以并发
    defer cs.mu.RUnlock()
    return cs.config[key]
}

func (cs *ConfigStore) Set(key, value string) {
    cs.mu.Lock()          // 写锁：独占访问
    defer cs.mu.Unlock()
    cs.config[key] = value
}

func (cs *ConfigStore) GetAll() map[string]string {
    cs.mu.RLock()
    defer cs.mu.RUnlock()
    result := make(map[string]string, len(cs.config))
    for k, v := range cs.config {
        result[k] = v
    }
    return result
}

func main() {
    store := NewConfigStore()
    store.Set("host", "0.0.0.0")
    store.Set("port", "8080")

    var wg sync.WaitGroup

    // 并发读取
    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            _ = store.Get("host") // 并发安全
        }(i)
    }

    // 并发写入
    for i := 0; i < 10; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            store.Set(fmt.Sprintf("key-%d", id), fmt.Sprintf("val-%d", id))
        }(i)
    }

    wg.Wait()
    fmt.Println("Config:", store.GetAll())
    _ = time.Now() // 避免 import 未使用
}
```

#### 4.3 sync.WaitGroup

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

func checkServer(name string, duration time.Duration) string {
    time.Sleep(duration)
    return fmt.Sprintf("%s: OK (took %v)", name, duration)
}

func main() {
    servers := []struct {
        name     string
        duration time.Duration
    }{
        {"web-01", 100 * time.Millisecond},
        {"web-02", 200 * time.Millisecond},
        {"db-01", 150 * time.Millisecond},
        {"cache-01", 50 * time.Millisecond},
    }

    var wg sync.WaitGroup
    results := make(chan string, len(servers))

    start := time.Now()

    for _, srv := range servers {
        wg.Add(1)
        go func(name string, dur time.Duration) {
            defer wg.Done()
            results <- checkServer(name, dur)
        }(srv.name, srv.duration)
    }

    // 等待所有检查完成
    go func() {
        wg.Wait()
        close(results)
    }()

    // 收集结果
    for result := range results {
        fmt.Println(result)
    }

    fmt.Printf("所有检查完成，耗时: %v\n", time.Since(start))
    // 总耗时约 200ms（最慢的那个），而非 500ms（串行总和）
}
```

#### 4.4 sync.Once

```go
package main

import (
    "fmt"
    "sync"
)

type Database struct {
    ConnectionString string
}

var (
    dbInstance *Database
    dbOnce     sync.Once
)

// 单例模式：确保只初始化一次
func GetDatabase() *Database {
    dbOnce.Do(func() {
        fmt.Println("Initializing database connection...")
        dbInstance = &Database{
            ConnectionString: "postgres://user:pass@localhost:5432/db",
        }
    })
    return dbInstance
}

func main() {
    var wg sync.WaitGroup

    // 并发调用 GetDatabase，但初始化只执行一次
    for i := 0; i < 10; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            db := GetDatabase()
            fmt.Printf("Goroutine %d got DB: %s\n", id, db.ConnectionString)
        }(i)
    }

    wg.Wait()
}
```

#### 4.5 sync.Pool

```go
package main

import (
    "bytes"
    "fmt"
    "sync"
)

// 对象池：复用对象减少 GC 压力
var bufferPool = sync.Pool{
    New: func() interface{} {
        return new(bytes.Buffer)
    },
}

func processRequest(data string) string {
    // 从池中获取 buffer
    buf := bufferPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()           // 清空内容
        bufferPool.Put(buf)   // 归还到池中
    }()

    // 使用 buffer
    buf.WriteString("processed: ")
    buf.WriteString(data)
    return buf.String()
}

func main() {
    var wg sync.WaitGroup

    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            result := processRequest(fmt.Sprintf("request-%d", id))
            _ = result
        }(i)
    }

    wg.Wait()
    fmt.Println("All requests processed")
}
```

---

### 5. Context 包

#### 5.1 Context 基础

```go
package main

import (
    "context"
    "fmt"
    "time"
)

func main() {
    // Background 是所有 context 的根
    ctx := context.Background()

    // WithCancel：手动取消
    ctx, cancel := context.WithCancel(ctx)
    defer cancel() // 确保资源释放

    go func() {
        time.Sleep(100 * time.Millisecond)
        cancel() // 触发取消
    }()

    select {
    case <-ctx.Done():
        fmt.Println("Cancelled:", ctx.Err())
    case <-time.After(1 * time.Second):
        fmt.Println("Timeout")
    }

    // WithTimeout：自动超时
    ctx2, cancel2 := context.WithTimeout(context.Background(), 200*time.Millisecond)
    defer cancel2()

    select {
    case <-ctx2.Done():
        fmt.Println("Timeout:", ctx2.Err()) // context deadline exceeded
    }

    // WithDeadline：指定截止时间
    deadline := time.Now().Add(300 * time.Millisecond)
    ctx3, cancel3 := context.WithDeadline(context.Background(), deadline)
    defer cancel3()

    select {
    case <-ctx3.Done():
        fmt.Println("Deadline:", ctx3.Err())
    }
}
```

#### 5.2 Context 传值

```go
package main

import (
    "context"
    "fmt"
)

type contextKey string

const (
    RequestIDKey contextKey = "request_id"
    UserIDKey    contextKey = "user_id"
)

func processRequest(ctx context.Context) {
    // 从 context 中取值
    requestID, _ := ctx.Value(RequestIDKey).(string)
    userID, _ := ctx.Value(UserIDKey).(int)

    fmt.Printf("Processing request %s for user %d\n", requestID, userID)

    // 传递给下游调用
    callDatabase(ctx)
}

func callDatabase(ctx context.Context) {
    requestID, _ := ctx.Value(RequestIDKey).(string)
    fmt.Printf("DB query from request %s\n", requestID)
}

func main() {
    ctx := context.Background()

    // 添加值到 context
    ctx = context.WithValue(ctx, RequestIDKey, "req-12345")
    ctx = context.WithValue(ctx, UserIDKey, 42)

    processRequest(ctx)
}
```

#### 5.3 SRE 实战：带超时的健康检查

```go
package main

import (
    "context"
    "fmt"
    "net/http"
    "sync"
    "time"
)

type HealthResult struct {
    Server  string
    Healthy bool
    Latency time.Duration
    Error   error
}

func checkHealth(ctx context.Context, url string) HealthResult {
    start := time.Now()

    req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
    if err != nil {
        return HealthResult{Server: url, Healthy: false, Error: err, Latency: time.Since(start)}
    }

    client := &http.Client{Timeout: 5 * time.Second}
    resp, err := client.Do(req)
    if err != nil {
        return HealthResult{Server: url, Healthy: false, Error: err, Latency: time.Since(start)}
    }
    defer resp.Body.Close()

    return HealthResult{
        Server:  url,
        Healthy: resp.StatusCode == 200,
        Latency: time.Since(start),
    }
}

func checkAllServers(ctx context.Context, urls []string) []HealthResult {
    var wg sync.WaitGroup
    results := make([]HealthResult, len(urls))

    for i, url := range urls {
        wg.Add(1)
        go func(idx int, u string) {
            defer wg.Done()
            results[idx] = checkHealth(ctx, u)
        }(i, url)
    }

    wg.Wait()
    return results
}

func main() {
    // 整体超时：30 秒内完成所有检查
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    servers := []string{
        "http://web-01:8080/healthz",
        "http://web-02:8080/healthz",
        "http://api-01:9090/healthz",
        "http://db-proxy:6432/healthz",
    }

    results := checkAllServers(ctx, servers)

    for _, r := range results {
        status := "UP"
        if !r.Healthy {
            status = "DOWN"
        }
        fmt.Printf("[%s] %s (latency: %v)\n", status, r.Server, r.Latency)
        if r.Error != nil {
            fmt.Printf("  Error: %v\n", r.Error)
        }
    }
}
```

---

### 6. 并发模式

#### 6.1 Fan-Out / Fan-In

```
Fan-Out（扇出）：多个 goroutine 从同一个 channel 读取
Fan-In（扇入）：多个 goroutine 向同一个 channel 写入

┌──────────┐     ┌──────────┐
│ Producer │ ──→ │ Channel  │
└──────────┘     └────┬─────┘
                      │
              ┌───────┼───────┐    Fan-Out
              ▼       ▼       ▼
          ┌──────┐ ┌──────┐ ┌──────┐
          │ W1   │ │ W2   │ │ W3   │    多个 Worker 并行处理
          └──┬───┘ └──┬───┘ └──┬───┘
              │       │       │
              └───────┼───────┘    Fan-In
                      ▼
              ┌──────────────┐
              │ Result Ch    │
              └──────────────┘
                      │
                      ▼
              ┌──────────────┐
              │  Consumer    │
              └──────────────┘
```

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

// Fan-Out: 多个 worker 从 jobs channel 读取
// Fan-In: 所有 worker 将结果写入 results channel

func worker(id int, jobs <-chan int, results chan<- string) {
    for job := range jobs {
        time.Sleep(50 * time.Millisecond) // 模拟工作
        results <- fmt.Sprintf("Worker %d processed job %d", id, job)
    }
}

func main() {
    numJobs := 10
    numWorkers := 3

    jobs := make(chan int, numJobs)
    results := make(chan string, numJobs)

    // 启动 workers（Fan-Out）
    var wg sync.WaitGroup
    for w := 1; w <= numWorkers; w++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            worker(id, jobs, results)
        }(w)
    }

    // 发送任务
    for j := 1; j <= numJobs; j++ {
        jobs <- j
    }
    close(jobs)

    // 等待所有 worker 完成后关闭 results
    go func() {
        wg.Wait()
        close(results)
    }()

    // 收集结果（Fan-In）
    for result := range results {
        fmt.Println(result)
    }
}
```

#### 6.2 Pipeline 模式

```
Pipeline（管道）：多个阶段通过 channel 串联

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Generate │ →  │ Square   │ →  │ Filter   │ →  │ Consume  │
│ 生成数据  │    │ 求平方    │    │ 过滤偶数  │    │ 消费结果  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     ch1             ch2             ch3

每个阶段：
- 从输入 channel 读取
- 处理数据
- 写入输出 channel
```

```go
package main

import (
    "fmt"
)

// 阶段 1：生成数据
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for _, n := range nums {
            out <- n
        }
    }()
    return out
}

// 阶段 2：求平方
func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            out <- n * n
        }
    }()
    return out
}

// 阶段 3：过滤
func filter(in <-chan int, predicate func(int) bool) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            if predicate(n) {
                out <- n
            }
        }
    }()
    return out
}

func main() {
    // 构建管道
    nums := generate(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
    squared := square(nums)
    evens := filter(squared, func(n int) bool { return n%2 == 0 })

    // 消费结果
    for result := range evens {
        fmt.Println(result) // 4, 16, 36, 64, 100
    }
}
```

#### 6.3 Worker Pool 模式

```go
package main

import (
    "context"
    "fmt"
    "math/rand"
    "sync"
    "time"
)

type Task struct {
    ID   int
    Host string
}

type Result struct {
    TaskID  int
    Host    string
    Healthy bool
    Latency time.Duration
    Error   error
}

func healthCheckWorker(ctx context.Context, id int, tasks <-chan Task, results chan<- Result) {
    for task := range tasks {
        select {
        case <-ctx.Done():
            return
        default:
        }

        // 模拟健康检查
        start := time.Now()
        latency := time.Duration(rand.Intn(200)+50) * time.Millisecond
        time.Sleep(latency)

        results <- Result{
            TaskID:  task.ID,
            Host:    task.Host,
            Healthy: rand.Float64() > 0.2, // 80% 成功率
            Latency: latency,
        }
    }
}

func runWorkerPool(ctx context.Context, numWorkers int, tasks []Task) []Result {
    taskChan := make(chan Task, len(tasks))
    resultChan := make(chan Result, len(tasks))

    // 启动 worker pool
    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            healthCheckWorker(ctx, id, taskChan, resultChan)
        }(i)
    }

    // 分发任务
    for _, task := range tasks {
        taskChan <- task
    }
    close(taskChan)

    // 等待所有 worker 完成
    go func() {
        wg.Wait()
        close(resultChan)
    }()

    // 收集结果
    var results []Result
    for result := range resultChan {
        results = append(results, result)
    }
    return results
}

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    hosts := []string{
        "web-01", "web-02", "web-03", "web-04", "web-05",
        "api-01", "api-02", "api-03",
        "db-01", "db-02",
        "cache-01", "cache-02",
    }

    tasks := make([]Task, len(hosts))
    for i, host := range hosts {
        tasks[i] = Task{ID: i, Host: host}
    }

    start := time.Now()
    results := runWorkerPool(ctx, 4, tasks) // 4 个 worker 并发

    healthy := 0
    for _, r := range results {
        status := "DOWN"
        if r.Healthy {
            status = "UP"
            healthy++
        }
        fmt.Printf("[Task %2d] %s: %s (latency: %v)\n", r.TaskID, r.Host, status, r.Latency)
    }

    fmt.Printf("\nSummary: %d/%d healthy, total time: %v\n",
        healthy, len(results), time.Since(start))
}
```

#### 6.4 限流器模式

```go
package main

import (
    "context"
    "fmt"
    "sync"
    "time"
)

// 基于 channel 的令牌桶限流器
type RateLimiter struct {
    ticker *time.Ticker
    tokens chan struct{}
}

func NewRateLimiter(rate int, burst int) *RateLimiter {
    rl := &RateLimiter{
        tokens: make(chan struct{}, burst),
    }

    // 初始化令牌
    for i := 0; i < burst; i++ {
        rl.tokens <- struct{}{}
    }

    // 定时补充令牌
    rl.ticker = time.NewTicker(time.Second / time.Duration(rate))
    go func() {
        for range rl.ticker.C {
            select {
            case rl.tokens <- struct{}{}:
            default: // 桶满，丢弃令牌
            }
        }
    }()

    return rl
}

func (rl *RateLimiter) Allow() bool {
    select {
    case <-rl.tokens:
        return true
    default:
        return false
    }
}

func (rl *RateLimiter) Wait(ctx context.Context) error {
    select {
    case <-rl.tokens:
        return nil
    case <-ctx.Done():
        return ctx.Err()
    }
}

func (rl *RateLimiter) Stop() {
    rl.ticker.Stop()
}

func main() {
    limiter := NewRateLimiter(10, 5) // 10 req/s，突发 5 个

    var wg sync.WaitGroup
    for i := 0; i < 20; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
            defer cancel()

            if err := limiter.Wait(ctx); err != nil {
                fmt.Printf("Request %d: rate limited\n", id)
                return
            }
            fmt.Printf("Request %d: allowed\n", id)
        }(i)
    }

    wg.Wait()
    limiter.Stop()
}
```

---

### 7. Race Detector

#### 7.1 检测数据竞争

```go
package main

import (
    "fmt"
    "sync"
)

// 有竞争的代码
func badCounter() {
    count := 0
    var wg sync.WaitGroup

    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            count++ // 数据竞争！
        }()
    }

    wg.Wait()
    fmt.Println("Bad count:", count) // 结果不确定
}

// 修复后的代码
func goodCounter() {
    count := 0
    var mu sync.Mutex
    var wg sync.WaitGroup

    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            mu.Lock()
            count++
            mu.Unlock()
        }()
    }

    wg.Wait()
    fmt.Println("Good count:", count) // 总是 1000
}

func main() {
    badCounter()
    goodCounter()
}
```

```bash
# 使用 race detector 运行
go run -race main.go

# 输出示例：
# ==================
# WARNING: DATA RACE
# Write at 0x00c0000b4010 by goroutine 8:
#   main.badCounter.func1()
#       /path/to/main.go:15 +0x4e
#
# Previous write at 0x00c0000b4010 by goroutine 7:
#   main.badCounter.func1()
#       /path/to/main.go:15 +0x4e
#
# Goroutine 8 (running) created at:
#   main.badCounter()
#       /path/to/main.go:13 +0x9a
# ==================
# Bad count: 998
# Good count: 1000
# Found 1 data race(s)
# exit status 66
```

#### 7.2 Race Detector 最佳实践

```bash
# 编译时启用 race detector
go build -race -o myapp .

# 测试时启用
go test -race ./...

# 在 CI/CD 中启用（必须！）
# GitHub Actions 示例
# - run: go test -race -v ./...

# 注意事项：
# 1. Race detector 有 5-10x 性能开销，不要在生产环境使用
# 2. Race detector 只能检测到实际执行到的竞争路径
# 3. 即使 -race 测试通过，也不能保证 100% 没有竞争
# 4. 增加测试覆盖率可以提高竞争检测率
```

---

### 8. SRE 实战案例

#### 8.1 并发日志收集器

```go
package main

import (
    "context"
    "fmt"
    "sync"
    "time"
)

type LogEntry struct {
    Timestamp time.Time
    Source    string
    Level     string
    Message   string
}

// 日志收集器：从多个来源并发收集日志
type LogCollector struct {
    sources   []LogSource
    batchSize int
    flushInterval time.Duration
}

type LogSource interface {
    Name() string
    Fetch(ctx context.Context, since time.Time) ([]LogEntry, error)
}

func NewLogCollector(sources []LogSource, batchSize int, flushInterval time.Duration) *LogCollector {
    return &LogCollector{
        sources:       sources,
        batchSize:     batchSize,
        flushInterval: flushInterval,
    }
}

func (lc *LogCollector) Collect(ctx context.Context) ([]LogEntry, error) {
    var (
        mu      sync.Mutex
        wg      sync.WaitGroup
        entries []LogEntry
        errs    []error
    )

    // 并发从所有来源收集日志
    for _, source := range lc.sources {
        wg.Add(1)
        go func(src LogSource) {
            defer wg.Done()

            since := time.Now().Add(-lc.flushInterval)
            logs, err := src.Fetch(ctx, since)
            if err != nil {
                mu.Lock()
                errs = append(errs, fmt.Errorf("%s: %w", src.Name(), err))
                mu.Unlock()
                return
            }

            mu.Lock()
            entries = append(entries, logs...)
            mu.Unlock()
        }(source)
    }

    wg.Wait()

    if len(errs) > 0 {
        return entries, fmt.Errorf("collection errors: %v", errs)
    }
    return entries, nil
}

func main() {
    sources := []LogSource{} // 实际使用时注入具体实现

    collector := NewLogCollector(sources, 100, 1*time.Minute)

    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    entries, err := collector.Collect(ctx)
    if err != nil {
        fmt.Printf("Collection errors: %v\n", err)
    }
    fmt.Printf("Collected %d log entries\n", len(entries))
}
```

#### 8.2 并发指标采集器

```go
package main

import (
    "context"
    "fmt"
    "math/rand"
    "sync"
    "time"
)

type Metric struct {
    Name      string
    Value     float64
    Timestamp time.Time
    Tags      map[string]string
}

type MetricSource interface {
    Name() string
    Collect(ctx context.Context) ([]Metric, error)
}

type PrometheusSource struct {
    Endpoint string
}

func (p *PrometheusSource) Name() string { return "prometheus-" + p.Endpoint }

func (p *PrometheusSource) Collect(ctx context.Context) ([]Metric, error) {
    time.Sleep(time.Duration(rand.Intn(100)) * time.Millisecond)
    return []Metric{
        {Name: "cpu_usage", Value: 85.5, Timestamp: time.Now()},
        {Name: "memory_usage", Value: 72.3, Timestamp: time.Now()},
    }, nil
}

type HostMetricsSource struct {
    Host string
}

func (h *HostMetricsSource) Name() string { return "host-" + h.Host }

func (h *HostMetricsSource) Collect(ctx context.Context) ([]Metric, error) {
    time.Sleep(time.Duration(rand.Intn(50)) * time.Millisecond)
    return []Metric{
        {Name: "disk_usage", Value: 45.0, Timestamp: time.Now()},
        {Name: "load_avg", Value: 2.5, Timestamp: time.Now()},
    }, nil
}

// 并发采集所有指标源
func CollectAllMetrics(ctx context.Context, sources []MetricSource) ([]Metric, error) {
    ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
    defer cancel()

    type sourceResult struct {
        metrics []Metric
        err     error
        source  string
    }

    results := make(chan sourceResult, len(sources))
    var wg sync.WaitGroup

    for _, src := range sources {
        wg.Add(1)
        go func(s MetricSource) {
            defer wg.Done()
            metrics, err := s.Collect(ctx)
            results <- sourceResult{metrics: metrics, err: err, source: s.Name()}
        }(src)
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    var allMetrics []Metric
    var errs []error

    for result := range results {
        if result.err != nil {
            errs = append(errs, fmt.Errorf("%s: %w", result.source, result.err))
            continue
        }
        allMetrics = append(allMetrics, result.metrics...)
    }

    if len(errs) > 0 {
        return allMetrics, fmt.Errorf("collection errors: %v", errs)
    }
    return allMetrics, nil
}

func main() {
    sources := []MetricSource{
        &PrometheusSource{Endpoint: "http://prometheus:9090"},
        &HostMetricsSource{Host: "web-01"},
        &HostMetricsSource{Host: "web-02"},
        &HostMetricsSource{Host: "db-01"},
    }

    ctx := context.Background()
    start := time.Now()

    metrics, err := CollectAllMetrics(ctx, sources)
    if err != nil {
        fmt.Printf("Errors: %v\n", err)
    }

    for _, m := range metrics {
        fmt.Printf("  %s: %.2f (at %s)\n", m.Name, m.Value, m.Timestamp.Format("15:04:05.000"))
    }

    fmt.Printf("\nCollected %d metrics in %v\n", len(metrics), time.Since(start))
}
```

---

## 💻 实战练习

### 练习 1：并发端口扫描器

编写一个并发端口扫描器，使用 worker pool 模式同时扫描多个端口。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "fmt"
    "net"
    "sort"
    "sync"
    "time"
)

type PortResult struct {
    Port   int
    Open   bool
    Error  error
}

func scanPort(host string, port int) PortResult {
    addr := fmt.Sprintf("%s:%d", host, port)
    conn, err := net.DialTimeout("tcp", addr, 2*time.Second)
    if err != nil {
        return PortResult{Port: port, Open: false, Error: err}
    }
    conn.Close()
    return PortResult{Port: port, Open: true}
}

func scanPorts(host string, ports []int, numWorkers int) []PortResult {
    jobs := make(chan int, len(ports))
    results := make(chan PortResult, len(ports))

    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for port := range jobs {
                results <- scanPort(host, port)
            }
        }()
    }

    for _, port := range ports {
        jobs <- port
    }
    close(jobs)

    go func() {
        wg.Wait()
        close(results)
    }()

    var openPorts []PortResult
    for result := range results {
        if result.Open {
            openPorts = append(openPorts, result)
        }
    }

    sort.Slice(openPorts, func(i, j int) bool {
        return openPorts[i].Port < openPorts[j].Port
    })
    return openPorts
}

func main() {
    host := "localhost"
    ports := make([]int, 1024)
    for i := range ports {
        ports[i] = i + 1
    }

    start := time.Now()
    openPorts := scanPorts(host, ports, 100)

    fmt.Printf("Open ports on %s:\n", host)
    for _, p := range openPorts {
        fmt.Printf("  %d\n", p.Port)
    }
    fmt.Printf("Scanned %d ports in %v, found %d open\n",
        len(ports), time.Since(start), len(openPorts))
}
```
</details>

### 练习 2：实现一个带超时和重试的 HTTP 客户端

<details>
<summary>参考答案</summary>

```go
package main

import (
    "context"
    "fmt"
    "io"
    "math"
    "net/http"
    "time"
)

type RetryConfig struct {
    MaxRetries  int
    BaseDelay   time.Duration
    MaxDelay    time.Duration
    Multiplier  float64
}

func DefaultRetryConfig() RetryConfig {
    return RetryConfig{
        MaxRetries: 3,
        BaseDelay:  100 * time.Millisecond,
        MaxDelay:   5 * time.Second,
        Multiplier: 2.0,
    }
}

func (rc RetryConfig) delay(attempt int) time.Duration {
    delay := float64(rc.BaseDelay) * math.Pow(rc.Multiplier, float64(attempt))
    if delay > float64(rc.MaxDelay) {
        delay = float64(rc.MaxDelay)
    }
    return time.Duration(delay)
}

func DoWithRetry(ctx context.Context, url string, retryCfg RetryConfig) (*http.Response, error) {
    var lastErr error

    for attempt := 0; attempt <= retryCfg.MaxRetries; attempt++ {
        if attempt > 0 {
            delay := retryCfg.delay(attempt - 1)
            fmt.Printf("  Retry %d after %v\n", attempt, delay)
            select {
            case <-time.After(delay):
            case <-ctx.Done():
                return nil, ctx.Err()
            }
        }

        req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
        if err != nil {
            return nil, err
        }

        client := &http.Client{Timeout: 10 * time.Second}
        resp, err := client.Do(req)
        if err != nil {
            lastErr = err
            continue
        }

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
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    resp, err := DoWithRetry(ctx, "http://httpbin.org/status/200", DefaultRetryConfig())
    if err != nil {
        fmt.Printf("Request failed: %v\n", err)
        return
    }
    defer resp.Body.Close()

    body, _ := io.ReadAll(resp.Body)
    fmt.Printf("Status: %d\n", resp.StatusCode)
    fmt.Printf("Body: %s\n", string(body[:min(len(body), 200)]))
}

func min(a, b int) int {
    if a < b {
        return a
    }
    return b
}
```
</details>

### 练习 3：并发安全的配置热加载器

实现一个配置热加载器，支持并发读取、后台定期刷新、变更通知。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
    "sync"
    "time"
)

type Config struct {
    Host    string `json:"host"`
    Port    int    `json:"port"`
    Debug   bool   `json:"debug"`
    Updated time.Time
}

type ConfigWatcher struct {
    path     string
    mu       sync.RWMutex
    config   Config
    onChange []func(Config)
    stopCh   chan struct{}
}

func NewConfigWatcher(path string) *ConfigWatcher {
    return &ConfigWatcher{
        path:   path,
        stopCh: make(chan struct{}),
    }
}

func (cw *ConfigWatcher) Get() Config {
    cw.mu.RLock()
    defer cw.mu.RUnlock()
    return cw.config
}

func (cw *ConfigWatcher) OnChange(fn func(Config)) {
    cw.mu.Lock()
    defer cw.mu.Unlock()
    cw.onChange = append(cw.onChange, fn)
}

func (cw *ConfigWatcher) load() error {
    data, err := os.ReadFile(cw.path)
    if err != nil {
        return err
    }

    var config Config
    if err := json.Unmarshal(data, &config); err != nil {
        return err
    }
    config.Updated = time.Now()

    cw.mu.Lock()
    old := cw.config
    cw.config = config
    callbacks := cw.onChange
    cw.mu.Unlock()

    // 触发变更回调
    if old != config {
        for _, fn := range callbacks {
            go fn(config)
        }
    }

    return nil
}

func (cw *ConfigWatcher) Start(interval time.Duration) error {
    if err := cw.load(); err != nil {
        return err
    }

    go func() {
        ticker := time.NewTicker(interval)
        defer ticker.Stop()

        for {
            select {
            case <-ticker.C:
                if err := cw.load(); err != nil {
                    fmt.Printf("Config reload error: %v\n", err)
                }
            case <-cw.stopCh:
                return
            }
        }
    }()

    return nil
}

func (cw *ConfigWatcher) Stop() {
    close(cw.stopCh)
}

func main() {
    // 创建临时配置文件
    configPath := "/tmp/app-config.json"
    initialConfig := Config{Host: "0.0.0.0", Port: 8080, Debug: false}
    data, _ := json.Marshal(initialConfig)
    os.WriteFile(configPath, data, 0644)
    defer os.Remove(configPath)

    watcher := NewConfigWatcher(configPath)

    // 注册变更回调
    watcher.OnChange(func(cfg Config) {
        fmt.Printf("[Callback] Config changed: %+v\n", cfg)
    })

    if err := watcher.Start(1 * time.Second); err != nil {
        fmt.Printf("Start error: %v\n", err)
        return
    }
    defer watcher.Stop()

    // 并发读取配置
    var wg sync.WaitGroup
    for i := 0; i < 5; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for j := 0; j < 3; j++ {
                cfg := watcher.Get()
                fmt.Printf("[Reader %d] Config: %s:%d (updated: %s)\n",
                    id, cfg.Host, cfg.Port, cfg.Updated.Format("15:04:05"))
                time.Sleep(500 * time.Millisecond)
            }
        }(i)
    }

    // 模拟配置变更
    time.Sleep(2 * time.Second)
    newConfig := Config{Host: "0.0.0.0", Port: 9090, Debug: true}
    data, _ = json.Marshal(newConfig)
    os.WriteFile(configPath, data, 0644)
    fmt.Println("Config file updated!")

    wg.Wait()
}
```
</details>

---

## 🎯 面试题精选

### 1. 请详细描述 GMP 调度器模型

**答：** GMP 是 Go 并发调度的核心：
- **G (Goroutine):** 轻量级协程，初始栈 2KB，包含栈、程序计数器、goroutine ID 等
- **M (Machine):** OS 线程，真正执行代码，数量有上限（默认 10000）
- **P (Processor):** 逻辑处理器，持有本地运行队列（最多 256 个 G）和 mcache，数量默认等于 CPU 核心数

调度流程：G 创建后放入 P 的本地队列，M 绑定 P 后从队列取 G 执行。本地队列满时溢出到全局队列。空闲的 M 通过 work stealing 从其他 P 偷取 G。G 进入系统调用时 M 阻塞，P 与 M 解绑并绑定空闲 M 继续工作。

### 2. Goroutine 泄漏的原因和排查方法？

**答：** 常见原因：
- channel 阻塞（发送无接收者，或接收无发送者）
- 死锁（互等对方释放锁）
- 无限循环无退出条件
- context 未传递取消信号

排查方法：
- `runtime.NumGoroutine()` 监控数量变化
- `pprof.Lookup("goroutine")` 获取 goroutine 堆栈
- `go tool pprof http://localhost:6060/debug/pprof/goroutine`
- 使用 `-race` 检测竞争

### 3. 无缓冲 channel 和有缓冲 channel 的区别？

**答：**
- **无缓冲:** 发送和接收必须同时就绪（同步通信），发送方阻塞到接收方准备好
- **有缓冲:** 缓冲区未满时发送不阻塞，缓冲区为空时接收阻塞（异步通信）

选择依据：
- 需要同步保证 → 无缓冲
- 需要解耦生产/消费速率 → 有缓冲
- 信号通知 → `chan struct{}`，容量 0 或 1

### 4. select 语句中多个 case 同时就绪时如何选择？

**答：** 当多个 case 同时就绪时，Go runtime 会**随机选择**一个执行，而不是按顺序。这是为了避免饥饿问题。如果所有 case 都未就绪且有 default，则执行 default；否则 select 阻塞等待。

### 5. sync.Mutex 和 sync.RWMutex 的区别？什么时候用哪个？

**答：**
- **Mutex:** 互斥锁，读写都互斥
- **RWMutex:** 读写锁，读操作共享（多个读可并发），写操作独占

选择：
- 读多写少（如配置读取）→ RWMutex
- 读写均衡 → Mutex（RWMutex 有额外开销）
- 写多 → Mutex

### 6. context.WithCancel 和 context.WithTimeout 的区别？

**答：**
- `WithCancel`: 手动调用 cancel() 取消，适用于需要显式控制取消时机的场景
- `WithTimeout`: 超时自动取消，适用于有明确超时限制的操作（如 HTTP 请求）

两者都返回 cancel 函数，必须调用（通常 defer）以释放资源。超时 context 是 deadline context 的特例。

### 7. 如何实现一个 worker pool？

**答：** 核心组件：
1. 任务 channel：`jobs := make(chan Task, bufferSize)`
2. 结果 channel：`results := make(chan Result, bufferSize)`
3. N 个 worker goroutine 从 jobs 读取、处理、写入 results
4. WaitGroup 等待所有 worker 完成后关闭 results
5. 主 goroutine 从 results 收集结果

关键点：worker 数量根据任务类型调整（CPU 密集型 = NumCPU，I/O 密集型可更多）。

### 8. 什么是数据竞争？如何检测和避免？

**答：** 数据竞争是两个 goroutine 并发访问同一变量且至少一个是写操作。

检测：`go run -race main.go` 或 `go test -race ./...`

避免方法：
- 使用 sync.Mutex/RWMutex 保护共享数据
- 使用 channel 在 goroutine 间传递数据（CSP 模型）
- 使用 sync/atomic 进行原子操作
- 设计无共享架构（每个 goroutine 独占数据）

### 9. Go 1.14 的异步抢占解决了什么问题？

**答：** Go 1.14 之前使用协作式抢占，goroutine 必须在函数调用时检查抢占标志。如果 goroutine 执行一个没有函数调用的死循环，会独占 P，导致其他 goroutine 饿死、GC 无法 STW。

Go 1.14 引入基于 SIGURG 信号的异步抢占：sysmon 线程检测到 G 运行超过 10ms 时发送信号，信号处理函数将 G 抢占并放回队列。

### 10. sync.Pool 的作用和注意事项？

**答：** sync.Pool 用于缓存临时对象，减少 GC 压力。

注意事项：
- Pool 中的对象可能在任意 GC 时被清除（不保证持久性）
- 适合频繁分配/释放的临时对象（如 buffer）
- 不适合用作连接池（连接需要持久保持）
- Get/Put 必须配对，且使用前 Reset

---

## 📚 深入阅读

- [Go 官方博客：Concurrency](https://go.dev/blog/concurrency-is-not-parallelism) — 并发不等于并行
- [Go 官方博客：Share Memory By Communicating](https://go.dev/blog/codelab-share-memory-communicating) — CSP 模型
- [GMP 调度器源码分析](https://github.com/golang/go/blob/master/src/runtime/proc.go) — runtime/proc.go
- [Go 语言设计与实现 - 调度器](https://draveness.me/golang/docs/part3-runtime/ch06-concurrency/golang-goroutine/) — 深入 GMP
- [The Go Memory Model](https://go.dev/ref/mem) — 内存模型
- [《Go 语言圣经》第 9 章](https://books.studygolang.com/gopl-zh/ch9/ch9.html) — Goroutines 和 Channels
- [Go 并发模式](https://go.dev/talks/2012/concurrency.slide) — Rob Pike 的经典演讲

---

## ✅ 自检清单

- [ ] 能画出 GMP 模型架构图并解释调度流程
- [ ] 理解 work stealing 和系统调用时的 P-M 解绑机制
- [ ] 理解 Go 1.14 异步抢占的原理和解决的问题
- [ ] 能正确使用 channel 进行 goroutine 间通信
- [ ] 理解 select 语句的随机选择机制
- [ ] 掌握 sync.Mutex、RWMutex、WaitGroup、Once、Pool 的使用场景
- [ ] 能正确使用 context 传播取消信号和超时
- [ ] 能实现 fan-in/fan-out/pipeline/worker pool 四种并发模式
- [ ] 能使用 -race 检测并修复数据竞争
- [ ] 能为 SRE 场景设计并发健康检查/指标采集系统
