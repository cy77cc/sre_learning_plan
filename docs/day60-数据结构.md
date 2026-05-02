# Day 60: 数据结构 — 切片、Map 与结构体

> 📅 日期：2026-05-02
> 📖 学习主题：数据结构
> ⏰ 计划学习时间：3-4 小时

---

## 🎯 学习目标

- 深入理解切片的底层结构、扩容机制和性能陷阱
- 掌握 map 的实现原理、并发安全问题和解决方案
- 熟练运用结构体、结构体标签和 JSON 序列化
- 能在 SRE 场景中高效选择和操作数据结构

---

## 📖 详细知识点

### 1. 切片（Slice）深度解析

#### 1.1 切片的底层结构

切片不是数组，而是一个包含三个字段的描述符：

```go
// 切片的内部表示（runtime.slice）
type slice struct {
    array unsafe.Pointer  // 指向底层数组的指针
    len   int             // 当前长度（可用元素数量）
    cap   int             // 容量（从指针位置到数组末尾）
}
```

```go
package main

import "fmt"

func main() {
    // 从数组创建切片
    arr := [5]int{10, 20, 30, 40, 50}
    s := arr[1:4]  // [20, 30, 40]
    fmt.Printf("len=%d cap=%d %v\n", len(s), cap(s), s)
    // len=3, cap=4（从索引1到数组末尾共4个元素）

    // 切片共享底层数组
    s[0] = 200
    fmt.Println(arr)  // [10, 200, 30, 40, 50] — 原数组被修改！

    // 完整切片表达式 s[i:j:k]，k 控制容量
    s2 := arr[1:3:3]  // len=2, cap=2
    // s2 = append(s2, 999)  // 会分配新数组，不影响原数组
}
```

#### 1.2 切片扩容机制

当 append 超出容量时，Go 会分配新数组并拷贝：

```go
// Go 1.21+ 的扩容策略：
// - cap < 256：容量翻倍
// - cap >= 256：容量增长 ~1.25 倍（逐步调整）

func demonstrateGrowth() {
    s := make([]int, 0)
    prevCap := 0
    for i := 0; i < 20; i++ {
        s = append(s, i)
        if cap(s) != prevCap {
            fmt.Printf("len=%2d cap=%2d (grew from %d)\n", len(s), cap(s), prevCap)
            prevCap = cap(s)
        }
    }
}
// 输出示例：
// len= 1 cap= 1 (grew from 0)
// len= 2 cap= 2 (grew from 1)
// len= 3 cap= 4 (grew from 2)
// len= 5 cap= 8 (grew from 4)
// len= 9 cap=16 (grew from 8)
```

**性能优化：预分配容量**

```go
// ❌ 不预分配 — 反复扩容和拷贝
func bad() []int {
    s := []int{}
    for i := 0; i < 10000; i++ {
        s = append(s, i)  // 触发约 14 次扩容
    }
    return s
}

// ✅ 预分配容量 — 零扩容
func good() []int {
    s := make([]int, 0, 10000)  // 一次分配
    for i := 0; i < 10000; i++ {
        s = append(s, i)
    }
    return s
}

// SRE 实战：预分配用于批量采集
func collectMetrics(hosts []string) []*Metric {
    result := make([]*Metric, 0, len(hosts))  // 预分配
    for _, h := range hosts {
        if m, err := fetchMetric(h); err == nil {
            result = append(result, m)
        }
    }
    return result
}
```

#### 1.3 切片操作陷阱

```go
// 陷阱 1：子切片修改影响原切片
original := []int{1, 2, 3, 4, 5}
sub := original[2:4]  // [3, 4]
sub[0] = 300
fmt.Println(original)  // [1, 2, 300, 4, 5]

// 解决方案：用 copy 创建独立副本
independent := make([]int, len(sub))
copy(independent, sub)

// 陷阱 2：大切片取子切片导致内存泄漏
func processLogFile() error {
    data, err := os.ReadFile("huge.log")  // 1GB
    if err != nil { return err }
    // 只取前 100 字节，但 data 的底层数组不会被 GC！
    header := data[:100]
    saveHeader(header)
    return nil  // data 仍然被 header 引用，1GB 内存不释放
}

// 解决方案：拷贝需要的部分
func processLogFileFixed() error {
    data, err := os.ReadFile("huge.log")
    if err != nil { return err }
    header := make([]byte, 100)
    copy(header, data[:100])  // 拷贝后 data 可以被 GC
    saveHeader(header)
    return nil
}
```

### 2. Map 深度解析

#### 2.1 Map 创建与基本操作

```go
// 创建方式
m1 := make(map[string]int)                // 空 map
m2 := make(map[string]int, 100)           // 预分配 100 个桶
m3 := map[string]int{"cpu": 85, "mem": 72} // 字面量

// 安全访问
val, exists := m["disk"]
if !exists {
    val = 0  // 默认值
}

// 遍历（注意：顺序随机！每次运行可能不同）
for key, val := range m {
    fmt.Printf("%s: %d\n", key, val)
}

// 需要有序遍历时：先提取 key 排序
keys := make([]string, 0, len(m))
for k := range m {
    keys = append(keys, k)
}
sort.Strings(keys)
for _, k := range keys {
    fmt.Printf("%s: %d\n", k, m[k])
}

// 删除
delete(m, "cpu")
```

#### 2.2 Map 并发安全问题

```go
// ❌ 并发读写会 panic: concurrent map writes
func concurrentMapBug() {
    m := make(map[string]int)
    var wg sync.WaitGroup
    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            key := fmt.Sprintf("server-%d", id)
            m[key] = id  // panic!
        }(i)
    }
    wg.Wait()
}

// ✅ 方案 1：sync.RWMutex（通用场景，推荐）
type SafeMap struct {
    mu sync.RWMutex
    m  map[string]int
}

func (sm *SafeMap) Set(key string, val int) {
    sm.mu.Lock()
    defer sm.mu.Unlock()
    sm.m[key] = val
}

func (sm *SafeMap) Get(key string) (int, bool) {
    sm.mu.RLock()
    defer sm.mu.RUnlock()
    val, ok := sm.m[key]
    return val, ok
}

// ✅ 方案 2：sync.Map（读多写少场景）
func syncMapExample() {
    var m sync.Map
    m.Store("web-01", 85)
    m.Store("web-02", 72)

    val, ok := m.Load("web-01")
    if ok {
        fmt.Println(val)
    }

    m.Range(func(key, value interface{}) bool {
        fmt.Printf("%s: %v\n", key, value)
        return true  // 返回 false 停止遍历
    })

    m.Delete("web-02")
}
```

### 3. 结构体与 JSON 序列化

#### 3.1 结构体定义与初始化

```go
type Server struct {
    ID        int               `json:"id"`
    Name      string            `json:"name"`
    IPAddress string            `json:"ip_address"`
    Port      int               `json:"port,omitempty"`
    Tags      []string          `json:"tags,omitempty"`
    Metadata  map[string]string `json:"metadata,omitempty"`
    IsHealthy bool              `json:"is_healthy"`
}

// 初始化方式
s1 := Server{ID: 1, Name: "web-01", IPAddress: "10.0.1.10", IsHealthy: true}
s2 := Server{  // 顺序必须与定义一致
    1, "web-01", "10.0.1.10", 0, nil, nil, true,
}
s3 := &Server{ID: 2, Name: "db-01"}  // 指针
```

#### 3.2 JSON 序列化

```go
func jsonExample() {
    // 结构体 → JSON
    srv := Server{
        ID: 1, Name: "web-01", IPAddress: "10.0.1.10",
        Tags: []string{"production", "web"},
        IsHealthy: true,
    }
    data, err := json.MarshalIndent(srv, "", "  ")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(string(data))
    // {
    //   "id": 1,
    //   "name": "web-01",
    //   "ip_address": "10.0.1.10",
    //   "is_healthy": true,
    //   "tags": ["production", "web"]
    // }

    // JSON → 结构体
    var parsed Server
    if err := json.Unmarshal(data, &parsed); err != nil {
        log.Fatal(err)
    }

    // 解码 JSON 流（从 HTTP 响应或文件）
    resp, _ := http.Get("http://api.internal/servers")
    defer resp.Body.Close()
    var servers []Server
    if err := json.NewDecoder(resp.Body).Decode(&servers); err != nil {
        log.Fatal(err)
    }
}
```

#### 3.3 SRE 实战：监控配置结构体

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

// 从 YAML 文件加载配置
func LoadConfig(path string) (*MonitorConfig, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("reading config: %w", err)
    }
    var cfg MonitorConfig
    if err := yaml.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("parsing config: %w", err)
    }
    return &cfg, nil
}
```

---

## 💻 实战练习

### 练习 1：切片去重

编写函数，对字符串切片去重并保持原顺序。

<details>
<summary>参考答案</summary>

```go
func dedup(items []string) []string {
    seen := make(map[string]struct{})
    result := make([]string, 0, len(items))
    for _, item := range items {
        if _, exists := seen[item]; !exists {
            seen[item] = struct{}{}
            result = append(result, item)
        }
    }
    return result
}
```
</details>

### 练习 2：并发安全计数器

实现一个支持并发增减的计数器，使用 sync.RWMutex。

<details>
<summary>参考答案</summary>

```go
type Counter struct {
    mu sync.RWMutex
    m  map[string]int
}
func (c *Counter) Inc(key string) {
    c.mu.Lock(); defer c.mu.Unlock()
    c.m[key]++
}
func (c *Counter) Get(key string) int {
    c.mu.RLock(); defer c.mu.RUnlock()
    return c.m[key]
}
```
</details>

### 练习 3：JSON 配置验证

从 JSON 文件加载 Server 列表，过滤掉不健康的服务器并输出剩余服务器的名称。

<details>
<summary>参考答案</summary>

```go
data, _ := os.ReadFile("servers.json")
var servers []Server
json.Unmarshal(data, &servers)
healthy := make([]string, 0)
for _, s := range servers {
    if s.IsHealthy { healthy = append(healthy, s.Name) }
}
fmt.Println("Healthy servers:", healthy)
```
</details>

---

## 📚 扩展阅读

- [Go Slices: usage and internals](https://go.dev/blog/slices) — 官方博客：切片原理
- [Go Maps in action](https://go.dev/blog/maps) — 官方博客：map 原理
- [JSON and Go](https://go.dev/blog/json) — 官方博客：JSON 处理
- [《Go 语言圣经》第 4 章](https://github.com/gopl-zh/gopl-zh.github.com) — 复合数据类型

---

## 📝 笔记

### 延伸思考

- 为什么 Go map 遍历顺序是随机的？这对程序设计有什么影响？
- 在什么场景下应该选择 sync.Map 而非 RWMutex + map？
- 切片容量预分配对 SRE 批量采集工具的性能影响有多大？

---

## ✅ 完成检查

- [ ] 理解切片的底层结构和扩容策略
- [ ] 掌握切片操作的内存泄漏陷阱
- [ ] 理解 map 的并发安全问题及三种解决方案
- [ ] 能使用结构体标签控制 JSON 序列化
- [ ] 能设计 SRE 监控配置的结构体模型

---

*由 SRE 学习计划自动生成 | 2026-05-02*
