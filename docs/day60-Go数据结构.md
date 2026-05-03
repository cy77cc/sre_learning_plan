# Day 60: Go 数据结构 — struct 深入与高级特性

> 📅 日期：2026-05-03
> 📖 学习主题：struct 深入、方法、嵌入/组合、JSON 序列化、标签、内存对齐、零值语义
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 57 (Go 环境搭建), Day 58 (Go 基础语法), Day 59 (Go 函数与错误处理)

## 🎯 学习目标

- 深入理解 struct 的内存布局和对齐机制
- 掌握方法的值接收者与指针接收者的区别
- 理解嵌入（embedding）与组合的设计哲学
- 掌握 JSON 序列化/反序列化及标签的高级用法
- 理解零值语义在 SRE 工具中的实际应用

## 📖 核心知识点

### 1. struct 内部机制

#### 1.1 struct 的内存布局

```
struct 的内存布局：

type Example struct {
    a bool    // 1 byte
    b int64   // 8 bytes
    c int32   // 4 bytes
    d bool    // 1 byte
}

无对齐的布局（假设）：
┌──┬────────┬──────┬──┐
│a │b       │c     │d │
│1B│ 8B     │ 4B   │1B│ = 14 bytes
└──┴────────┴──────┴──┘

实际对齐后的布局（Go 默认对齐）：
┌──┬────┬────────┬──────┬────┬──┐
│a │pad │b       │c     │d   │pad│
│1B│7B  │ 8B     │ 4B   │1B  │3B │ = 24 bytes
└──┴────┴────────┴──────┴────┴──┘

对齐规则：
- bool:     对齐到 1 byte 边界
- int8:     对齐到 1 byte 边界
- int16:    对齐到 2 byte 边界
- int32:    对齐到 4 byte 边界
- int64:    对齐到 8 byte 边界
- float32:  对齐到 4 byte 边界
- float64:  对齐到 8 byte 边界
- pointer:  对齐到 8 byte 边界（64 位系统）
- string:   对齐到 8 byte 边界（pointer + len）
- slice:    对齐到 8 byte 边界（pointer + len + cap）
- struct:   对齐到其最大字段的对齐边界

优化后的布局：
type ExampleOptimized struct {
    b int64   // 8 bytes — 最大对齐字段放最前面
    c int32   // 4 bytes
    a bool    // 1 byte
    d bool    // 1 byte
}

┌────────┬──────┬──┬──┬────┐
│b       │c     │a │d │pad │
│ 8B     │ 4B   │1B│1B│2B  │ = 16 bytes
└────────┴──────┴──┴──┴────┘

节省了 8 bytes（33% 的内存节省！）
```

#### 1.2 struct 内存对齐验证

```go
package main

import (
    "fmt"
    "unsafe"
)

// 未优化的布局
type BadLayout struct {
    a bool    // 1 byte + 7 padding
    b int64   // 8 bytes
    c int32   // 4 bytes
    d bool    // 1 byte + 3 padding
}

// 优化后的布局
type GoodLayout struct {
    b int64   // 8 bytes
    c int32   // 4 bytes
    a bool    // 1 byte
    d bool    // 1 byte + 2 padding
}

// SRE 实战：监控指标结构体
type Metric struct {
    Name      string    // 16 bytes (ptr + len)
    Value     float64   // 8 bytes
    Timestamp int64     // 8 bytes
    Labels    []string  // 24 bytes (ptr + len + cap)
    IsGauge   bool      // 1 byte
}

// 优化版本
type MetricOptimized struct {
    Value     float64   // 8 bytes
    Timestamp int64     // 8 bytes
    Name      string    // 16 bytes
    Labels    []string  // 24 bytes
    IsGauge   bool      // 1 byte + 7 padding
}

func main() {
    fmt.Printf("BadLayout:  size=%d, align=%d\n",
        unsafe.Sizeof(BadLayout{}), unsafe.Alignof(BadLayout{}))
    fmt.Printf("GoodLayout: size=%d, align=%d\n",
        unsafe.Sizeof(GoodLayout{}), unsafe.Alignof(GoodLayout{}))
    fmt.Printf("Metric:     size=%d\n", unsafe.Sizeof(Metric{}))
    fmt.Printf("MetricOpt:  size=%d\n", unsafe.Sizeof(MetricOptimized{}))

    // 查看每个字段的偏移量
    var m Metric
    fmt.Printf("  Name offset:      %d\n", unsafe.Offsetof(m.Name))
    fmt.Printf("  Value offset:     %d\n", unsafe.Offsetof(m.Value))
    fmt.Printf("  Timestamp offset: %d\n", unsafe.Offsetof(m.Timestamp))
    fmt.Printf("  Labels offset:    %d\n", unsafe.Offsetof(m.Labels))
    fmt.Printf("  IsGauge offset:   %d\n", unsafe.Offsetof(m.IsGauge))
}
```

**内存对齐的影响：**

```
为什么内存对齐重要？

CPU 读取内存的方式：
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  CPU 按"字"（word）读取内存，通常是 4 或 8 字节            │
│                                                            │
│  对齐的读取：                                               │
│  ┌────────┬────────┬────────┬────────┐                     │
│  │ word 0 │ word 1 │ word 2 │ word 3 │                     │
│  │ 8 bytes│ 8 bytes│ 8 bytes│ 8 bytes│                     │
│  └────────┴────────┴────────┴────────┘                     │
│  int64 在 word 1 的起始位置 → 一次读取完成                 │
│                                                            │
│  未对齐的读取：                                             │
│  ┌────────┬────────┬────────┬────────┐                     │
│  │ word 0 │ word 1 │ word 2 │ word 3 │                     │
│  │ ...│int64 值│int64 值的剩余部分│...│                     │
│  └────────┴────────┴────────┴────────┘                     │
│  int64 跨越两个 word → 需要两次读取 + 合并                 │
│                                                            │
│  性能影响：                                                 │
│  - 对齐：1 次内存访问                                      │
│  - 未对齐：2 次内存访问 + 合并操作（可能慢 2-3 倍）        │
│  - 某些架构（ARM）未对齐访问甚至会触发异常                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 2. struct 的基本操作

#### 2.1 创建与初始化

```go
package main

import "fmt"

type Server struct {
    Name    string
    IP      string
    Port    int
    Tags    []string
    Config  map[string]string
}

func main() {
    // 方式 1：字段名初始化（推荐）
    s1 := Server{
        Name: "web-01",
        IP:   "10.0.1.10",
        Port: 8080,
    }

    // 方式 2：顺序初始化（不推荐，字段顺序变化会出错）
    s2 := Server{"web-02", "10.0.1.11", 8081, nil, nil}

    // 方式 3：new 分配（返回指针）
    s3 := new(Server)
    s3.Name = "web-03"
    s3.Port = 8082

    // 方式 4：零值可用
    var s4 Server
    s4.Name = "web-04"
    s4.Port = 8083

    // 方式 5：工厂函数（推荐复杂结构体）
    s5 := NewServer("web-05", "10.0.1.15", 8084)

    // 结构体比较（所有字段可比较时）
    s6 := Server{Name: "web-01", IP: "10.0.1.10", Port: 8080}
    fmt.Println(s1 == s6) // true

    // 包含不可比较字段（slice, map）时不能用 ==
    // fmt.Println(s1 == s2) // 编译错误

    fmt.Println(s1, s2, s3, s4, s5)
}

// 工厂函数
func NewServer(name, ip string, port int) *Server {
    return &Server{
        Name:   name,
        IP:     ip,
        Port:   port,
        Tags:   make([]string, 0),
        Config: make(map[string]string),
    }
}
```

#### 2.2 方法

```go
package main

import "fmt"

type Point struct {
    X, Y float64
}

// 值接收者 — 不能修改原始值
func (p Point) Distance() float64 {
    return p.X*p.X + p.Y*p.Y
}

// 指针接收者 — 可以修改原始值
func (p *Point) Translate(dx, dy float64) {
    p.X += dx
    p.Y += dy
}

// 指针接收者 — 避免大结构体拷贝
func (p *Point) String() string {
    return fmt.Sprintf("(%f, %f)", p.X, p.Y)
}

// SRE 实战：Server 方法
type Server struct {
    Name     string
    IP       string
    Port     int
    Status   string
    Tags     []string
    Metadata map[string]string
}

// 值接收者 — 只读操作
func (s Server) Address() string {
    return fmt.Sprintf("%s:%d", s.IP, s.Port)
}

func (s Server) IsHealthy() bool {
    return s.Status == "healthy"
}

// 指针接收者 — 修改操作
func (s *Server) SetStatus(status string) {
    s.Status = status
}

func (s *Server) AddTag(tag string) {
    s.Tags = append(s.Tags, tag)
}

func (s *Server) SetMetadata(key, value string) {
    if s.Metadata == nil {
        s.Metadata = make(map[string]string)
    }
    s.Metadata[key] = value
}

// 接口实现
type Stringer interface {
    String() string
}

func (s Server) String() string {
    return fmt.Sprintf("Server{Name: %s, Address: %s, Status: %s}",
        s.Name, s.Address(), s.Status)
}

func main() {
    p := Point{3, 4}
    fmt.Println(p.Distance()) // 25
    p.Translate(1, 1)
    fmt.Println(p.String()) // (4, 5)

    s := &Server{
        Name:   "web-01",
        IP:     "10.0.1.10",
        Port:   8080,
        Status: "healthy",
    }
    fmt.Println(s.Address())
    s.SetStatus("degraded")
    s.AddTag("production")
    s.SetMetadata("team", "platform")
    fmt.Println(s)
}
```

**值接收者 vs 指针接收者的选择指南：**

```
┌────────────────────────────────────────────────────────────┐
│              接收者选择指南                                  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  使用指针接收者的情况：                                     │
│  ├── 方法需要修改接收者                                    │
│  ├── 接收者是大结构体（避免拷贝开销）                      │
│  ├── 结构体包含不可复制的字段（sync.Mutex 等）             │
│  ├── 结构体的零值不可用（需要初始化）                      │
│  └── 一致性：如果一个方法需要指针接收者，所有方法都用指针  │
│                                                            │
│  使用值接收者的情况：                                       │
│  ├── 方法不需要修改接收者                                  │
│  ├── 接收者是小结构体（几个基本类型字段）                  │
│  ├── 结构体是值类型（int, string, bool 等）               │
│  ├── 需要方法集的副本（不影响原始值）                      │
│  └── 结构体的零值可用                                      │
│                                                            │
│  常见错误：                                                 │
│  func (s Server) SetStatus(status string) {                │
│      s.Status = status  // 修改的是副本，原始值不变！      │
│  }                                                        │
│                                                            │
│  正确做法：                                                 │
│  func (s *Server) SetStatus(status string) {               │
│      s.Status = status  // 修改原始值                      │
│  }                                                        │
│                                                            │
│  接口实现的注意事项：                                       │
│  - 值接收者实现的方法，值和指针都能匹配接口               │
│  - 指针接收者实现的方法，只有指针能匹配接口               │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 3. 嵌入（Embedding）与组合

#### 3.1 嵌入基础

```go
package main

import "fmt"

// Go 没有继承，只有组合（embedding）

// 基础结构体
type Base struct {
    ID        string
    CreatedAt time.Time
    UpdatedAt time.Time
}

func (b *Base) Touch() {
    b.UpdatedAt = time.Now()
}

func (b *Base) GetID() string {
    return b.ID
}

// 嵌入 Base
type Server struct {
    Base          // 嵌入（匿名字段）
    Name    string
    IP      string
    Port    int
    Status  string
}

// 嵌入的方法被提升（promoted）
// Server 自动获得 Base 的 Touch() 和 GetID() 方法

// 可以直接访问嵌入字段的字段
func (s *Server) SetStatus(status string) {
    s.Status = status
    s.Touch() // 调用嵌入的方法
}

// 嵌入接口
type Logger interface {
    Log(msg string)
}

type ConsoleLogger struct{}

func (l ConsoleLogger) Log(msg string) {
    fmt.Println("[LOG]", msg)
}

type Service struct {
    Base
    Logger // 嵌入接口
    Name   string
}

func (s *Service) Start() {
    s.Log("Service " + s.Name + " started") // 调用嵌入接口的方法
    s.Touch()
}

func main() {
    s := &Server{
        Base: Base{
            ID:        "srv-001",
            CreatedAt: time.Now(),
        },
        Name:   "web-01",
        IP:     "10.0.1.10",
        Port:   8080,
        Status: "healthy",
    }

    // 直接访问嵌入字段
    fmt.Println(s.ID)         // 等价于 s.Base.ID
    fmt.Println(s.GetID())    // 调用嵌入的方法

    s.SetStatus("degraded")
    fmt.Println(s.Status)

    // 嵌入接口
    svc := &Service{
        Base:   Base{ID: "svc-001"},
        Logger: ConsoleLogger{},
        Name:   "my-service",
    }
    svc.Start()
}
```

#### 3.2 嵌入的歧义与解决

```go
package main

import "fmt"

// 当多个嵌入有同名字段/方法时，需要显式指定

type A struct {
    Name string
}

func (a A) Hello() string {
    return "Hello from A: " + a.Name
}

type B struct {
    Name string
}

func (b B) Hello() string {
    return "Hello from B: " + b.Name
}

type C struct {
    A
    B
    // Name string  // 如果 C 自己有 Name，则优先使用 C 的
}

func main() {
    c := C{
        A: A{Name: "Alice"},
        B: B{Name: "Bob"},
    }

    // 歧义：c.Name 编译错误（两个嵌入都有 Name）
    // fmt.Println(c.Name)

    // 必须显式指定
    fmt.Println(c.A.Name) // Alice
    fmt.Println(c.B.Name) // Bob

    // 方法同理
    // fmt.Println(c.Hello()) // 编译错误
    fmt.Println(c.A.Hello()) // Hello from A: Alice
    fmt.Println(c.B.Hello()) // Hello from B: Bob
}
```

#### 3.3 组合 vs 继承

```
┌────────────────────────────────────────────────────────────┐
│              组合 vs 继承                                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  继承（Java/C++）：                                        │
│  class Animal {                                            │
│      void speak() { ... }                                 │
│  }                                                        │
│  class Dog extends Animal {                               │
│      void speak() { ... }  // 覆盖父类方法                │
│  }                                                        │
│  - 建立 "is-a" 关系                                       │
│  - 强耦合：子类依赖父类实现                               │
│  - 菱形继承问题                                           │
│                                                            │
│  组合（Go）：                                               │
│  type Animal struct {                                      │
│      Name string                                          │
│  }                                                        │
│  func (a Animal) Speak() string { return "..." }          │
│                                                            │
│  type Dog struct {                                         │
│      Animal  // 嵌入                                       │
│      Breed string                                         │
│  }                                                        │
│  - 建立 "has-a" 关系                                      │
│  - 松耦合：可以轻松替换嵌入的组件                         │
│  - 没有菱形继承问题                                       │
│                                                            │
│  Go 的设计哲学：                                           │
│  "Composition over inheritance"                           │
│  "Accept interfaces, return structs"                      │
│                                                            │
│  SRE 中的优势：                                            │
│  - 可以组合多个功能（如 Base + Logger + Metrics）          │
│  - 测试时可以替换嵌入的组件（mock）                       │
│  - 代码复用更灵活                                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 4. struct 标签（Tags）

#### 4.1 标签基础

```go
package main

import (
    "encoding/json"
    "fmt"
    "reflect"
)

// 标签是附在 struct 字段上的元数据
// 格式：`key:"value" key2:"value2"`

type User struct {
    ID       int    `json:"id"         db:"id"         validate:"required"`
    Name     string `json:"name"       db:"name"       validate:"required,min=1,max=100"`
    Email    string `json:"email"      db:"email"      validate:"required,email"`
    Password string `json:"-"          db:"password"   validate:"required,min=8"`
    Age      int    `json:"age,omitempty" db:"age"     validate:"gte=0,lte=150"`
    Tags     []string `json:"tags,omitempty" db:"-"    validate:""`
    internal string // 未导出字段，标签也未导出
}

func main() {
    // 反射读取标签
    t := reflect.TypeOf(User{})
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        fmt.Printf("Field: %-12s\n", field.Name)
        fmt.Printf("  json:     %s\n", field.Tag.Get("json"))
        fmt.Printf("  db:       %s\n", field.Tag.Get("db"))
        fmt.Printf("  validate: %s\n", field.Tag.Get("validate"))
        fmt.Println()
    }
}
```

#### 4.2 JSON 标签详解

```go
package main

import (
    "encoding/json"
    "fmt"
    "time"
)

// JSON 标签的完整格式：`json:"name,omitempty,string"`

type Config struct {
    // 基本映射
    Host string `json:"host"`
    Port int    `json:"port"`

    // 忽略字段
    Password string `json:"-"`

    // omitempty — 零值时省略
    Timeout time.Duration `json:"timeout,omitempty"`
    Retries int           `json:"retries,omitempty"` // 0 时省略
    Debug   bool          `json:"debug,omitempty"`   // false 时省略

    // string — 将值编码为 JSON 字符串
    Count int `json:"count,string"` // 编码为 "42" 而不是 42

    // 嵌入字段
    Metadata `json:"metadata"` // 内联或嵌套
}

type Metadata struct {
    Team  string `json:"team"`
    Env   string `json:"env"`
}

// SRE 实战：Prometheus 指标格式
type MetricFamily struct {
    Name   string   `json:"name"`
    Help   string   `json:"help"`
    Type   string   `json:"type"`
    Metrics []Metric `json:"metrics"`
}

type Metric struct {
    Labels map[string]string `json:"labels"`
    Value  float64           `json:"value"`
}

// SRE 实战：Kubernetes 风格的配置
type K8sResource struct {
    APIVersion string            `json:"apiVersion"`
    Kind       string            `json:"kind"`
    Metadata   K8sMetadata       `json:"metadata"`
    Spec       json.RawMessage   `json:"spec,omitempty"` // 延迟解析
}

type K8sMetadata struct {
    Name        string            `json:"name"`
    Namespace   string            `json:"namespace,omitempty"`
    Labels      map[string]string `json:"labels,omitempty"`
    Annotations map[string]string `json:"annotations,omitempty"`
}

func main() {
    // 编码
    cfg := Config{
        Host:    "localhost",
        Port:    8080,
        Password: "secret", // 会被忽略
        Retries: 0,         // omitempty，不会出现
        Debug:   false,     // omitempty，不会出现
        Count:   42,
        Metadata: Metadata{
            Team: "platform",
            Env:  "prod",
        },
    }

    data, _ := json.MarshalIndent(cfg, "", "  ")
    fmt.Println(string(data))
    // 输出：
    // {
    //   "host": "localhost",
    //   "port": 8080,
    //   "count": "42",
    //   "metadata": {
    //     "team": "platform",
    //     "env": "prod"
    //   }
    // }

    // 解码
    jsonStr := `{"host":"10.0.1.10","port":9090,"count":"100"}`
    var cfg2 Config
    json.Unmarshal([]byte(jsonStr), &cfg2)
    fmt.Printf("Host: %s, Port: %d, Count: %d\n",
        cfg2.Host, cfg2.Port, cfg2.Count)
}
```

#### 4.3 其他常用标签

```go
package main

import (
    "fmt"
    "reflect"
)

// db 标签 — 数据库映射
type User struct {
    ID        int    `db:"id"`
    Username  string `db:"username"`
    Email     string `db:"email"`
    CreatedAt string `db:"created_at"`
}

// yaml 标签 — YAML 配置
type AppConfig struct {
    Server ServerConfig `yaml:"server"`
    DB     DBConfig     `yaml:"db"`
}

type ServerConfig struct {
    Host string `yaml:"host"`
    Port int    `yaml:"port"`
}

type DBConfig struct {
    Host     string `yaml:"host"`
    Port     int    `yaml:"port"`
    Name     string `yaml:"name"`
    User     string `yaml:"user"`
    Password string `yaml:"password"`
}

// validate 标签 — 输入验证
type CreateRequest struct {
    Name  string `json:"name"  validate:"required,min=1,max=100"`
    Email string `json:"email" validate:"required,email"`
    Age   int    `json:"age"   validate:"gte=0,lte=150"`
}

// mapstructure 标签 — 配置映射
type Config struct {
    Port    int    `mapstructure:"port"`
    Host    string `mapstructure:"host"`
    Debug   bool   `mapstructure:"debug"`
}

// 自定义标签解析
func parseStructTags(obj interface{}) {
    t := reflect.TypeOf(obj)
    v := reflect.ValueOf(obj)

    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        value := v.Field(i)

        // 获取所有标签
        tag := field.Tag
        fmt.Printf("Field: %s\n", field.Name)
        fmt.Printf("  Type: %s\n", field.Type)
        fmt.Printf("  Value: %v\n", value.Interface())

        // 遍历所有标签
        for _, key := range []string{"json", "db", "yaml", "validate", "mapstructure"} {
            if val, ok := tag.Lookup(key); ok {
                fmt.Printf("  %s: %s\n", key, val)
            }
        }
        fmt.Println()
    }
}

func main() {
    cfg := Config{
        Port: 8080,
        Host: "localhost",
        Debug: true,
    }
    parseStructTags(cfg)
}
```

#### 4.4 标签的底层原理

```
标签的存储和解析：

struct 字段的标签存储在 reflect.StructField.Tag 中
类型是 reflect.StructTag（本质是 string）

标签格式：
`key1:"value1" key2:"value2" key3:"value3"`

解析流程：
1. reflect.StructTag.Lookup("key") 查找指定 key 的值
2. 返回 (value, ok) — value 是标签值，ok 表示是否存在
3. 如果标签格式错误（缺少引号等），Lookup 会 panic

注意事项：
1. 标签是编译时确定的，不能动态修改
2. 标签值必须用双引号包裹
3. 标签中不能包含反引号（`）
4. 标签的解析是 O(n) 的（线性扫描）
5. 大量反射操作有性能开销
```

### 5. JSON 序列化深入

#### 5.1 自定义 JSON 序列化

```go
package main

import (
    "encoding/json"
    "fmt"
    "time"
)

// 实现 json.Marshaler 接口
type Duration struct {
    time.Duration
}

func (d Duration) MarshalJSON() ([]byte, error) {
    return json.Marshal(d.String())
}

func (d *Duration) UnmarshalJSON(b []byte) error {
    var s string
    if err := json.Unmarshal(b, &s); err != nil {
        return err
    }
    dur, err := time.ParseDuration(s)
    if err != nil {
        return err
    }
    d.Duration = dur
    return nil
}

// SRE 实战：时间戳格式化
type Event struct {
    Name      string   `json:"name"`
    Timestamp UnixTime `json:"timestamp"`
    Duration  Duration `json:"duration"`
}

type UnixTime struct {
    time.Time
}

func (t UnixTime) MarshalJSON() ([]byte, error) {
    return json.Marshal(t.Unix())
}

func (t *UnixTime) UnmarshalJSON(b []byte) error {
    var ts int64
    if err := json.Unmarshal(b, &ts); err != nil {
        return err
    }
    t.Time = time.Unix(ts, 0)
    return nil
}

// SRE 实战：灵活的 JSON 输出
type APIResponse struct {
    Success bool        `json:"success"`
    Data    interface{} `json:"data,omitempty"`
    Error   *ErrorInfo  `json:"error,omitempty"`
}

type ErrorInfo struct {
    Code    int    `json:"code"`
    Message string `json:"message"`
    Details string `json:"details,omitempty"`
}

// 条件序列化
type Server struct {
    Name     string `json:"name"`
    IP       string `json:"ip"`
    Port     int    `json:"port"`
    Password string `json:"-"` // 永远不序列化
    internal string           // 未导出字段，不会序列化
}

func main() {
    event := Event{
        Name:      "deploy",
        Timestamp: UnixTime{time.Now()},
        Duration:  Duration{5 * time.Minute},
    }

    data, _ := json.MarshalIndent(event, "", "  ")
    fmt.Println(string(data))
    // {
    //   "name": "deploy",
    //   "timestamp": 1714742400,
    //   "duration": "5m0s"
    // }

    // 成功响应
    resp := APIResponse{
        Success: true,
        Data:    map[string]string{"status": "ok"},
    }
    data, _ = json.MarshalIndent(resp, "", "  ")
    fmt.Println(string(data))

    // 错误响应
    errResp := APIResponse{
        Success: false,
        Error: &ErrorInfo{
            Code:    404,
            Message: "not found",
        },
    }
    data, _ = json.MarshalIndent(errResp, "", "  ")
    fmt.Println(string(data))
}
```

#### 5.2 json.RawMessage 延迟解析

```go
package main

import (
    "encoding/json"
    "fmt"
)

// json.RawMessage 允许延迟解析 JSON
// 场景：你不知道 "data" 字段的具体类型

type Envelope struct {
    Type    string          `json:"type"`
    Data    json.RawMessage `json:"data"` // 延迟解析
    Version int             `json:"version"`
}

type MetricsData struct {
    CPU    float64 `json:"cpu"`
    Memory float64 `json:"memory"`
    Disk   float64 `json:"disk"`
}

type AlertData struct {
    Name    string `json:"name"`
    Level   string `json:"level"`
    Message string `json:"message"`
}

func processEnvelope(raw []byte) error {
    // 先解析外层
    var env Envelope
    if err := json.Unmarshal(raw, &env); err != nil {
        return fmt.Errorf("parse envelope: %w", err)
    }

    // 根据类型解析内层
    switch env.Type {
    case "metrics":
        var data MetricsData
        if err := json.Unmarshal(env.Data, &data); err != nil {
            return fmt.Errorf("parse metrics: %w", err)
        }
        fmt.Printf("Metrics: CPU=%.1f%%, Mem=%.1f%%\n", data.CPU, data.Memory)

    case "alert":
        var data AlertData
        if err := json.Unmarshal(env.Data, &data); err != nil {
            return fmt.Errorf("parse alert: %w", err)
        }
        fmt.Printf("Alert: %s [%s] %s\n", data.Name, data.Level, data.Message)

    default:
        return fmt.Errorf("unknown type: %s", env.Type)
    }

    return nil
}

func main() {
    // 指标消息
    metricsJSON := `{
        "type": "metrics",
        "data": {"cpu": 85.2, "memory": 72.1, "disk": 45.0},
        "version": 1
    }`
    processEnvelope([]byte(metricsJSON))

    // 告警消息
    alertJSON := `{
        "type": "alert",
        "data": {"name": "HighCPU", "level": "critical", "message": "CPU > 90%"},
        "version": 1
    }`
    processEnvelope([]byte(alertJSON))
}
```

#### 5.3 JSON 编解码的性能优化

```go
package main

import (
    "encoding/json"
    "fmt"
    "strings"
)

// 方式 1：预分配 Buffer
func marshalFast(v interface{}) ([]byte, error) {
    var buf strings.Builder
    enc := json.NewEncoder(&buf)
    if err := enc.Encode(v); err != nil {
        return nil, err
    }
    // 去掉末尾的换行符（Encoder 会添加）
    s := buf.String()
    return []byte(strings.TrimRight(s, "\n")), nil
}

// 方式 2：流式处理大量数据
func processLargeJSON(reader io.Reader) error {
    dec := json.NewDecoder(reader)

    // 读取开始的 [
    token, err := dec.Token()
    if err != nil {
        return err
    }
    if delim, ok := token.(json.Delim); !ok || delim != '[' {
        return fmt.Errorf("expected [, got %v", token)
    }

    // 逐个解析数组元素
    for dec.More() {
        var item map[string]interface{}
        if err := dec.Decode(&item); err != nil {
            return err
        }
        // 处理每个元素
        fmt.Println(item)
    }

    // 读取结束的 ]
    token, err = dec.Token()
    if err != nil {
        return err
    }
    if delim, ok := token.(json.Delim); !ok || delim != ']' {
        return fmt.Errorf("expected ], got %v", token)
    }

    return nil
}

// 方式 3：使用 sync.Pool 复用 Buffer
var bufferPool = sync.Pool{
    New: func() interface{} {
        return new(bytes.Buffer)
    },
}

func marshalWithPool(v interface{}) ([]byte, error) {
    buf := bufferPool.Get().(*bytes.Buffer)
    buf.Reset()
    defer bufferPool.Put(buf)

    enc := json.NewEncoder(buf)
    if err := enc.Encode(v); err != nil {
        return nil, err
    }

    result := make([]byte, buf.Len())
    copy(result, buf.Bytes())
    return result, nil
}

func main() {
    data := map[string]interface{}{
        "host": "web-01",
        "cpu":  85.2,
        "mem":  72.1,
    }

    result, _ := marshalFast(data)
    fmt.Println(string(result))
}
```

### 6. 零值语义

#### 6.1 零值的设计哲学

```
Go 零值的设计哲学：

┌────────────────────────────────────────────────────────────┐
│              零值语义                                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  "Make the zero value useful." — Rob Pike                  │
│                                                            │
│  Go 的零值不是"未初始化的垃圾值"，而是有意义的默认值：     │
│                                                            │
│  - int 的零值是 0 — 一个有效的数值                        │
│  - string 的零值是 "" — 一个有效的空字符串                │
│  - bool 的零值是 false — 一个有效的布尔值                 │
│  - slice 的零值是 nil — 可以安全地 append                  │
│  - map 的零值是 nil — 可以安全地读取（返回零值）          │
│  - chan 的零值是 nil — 读写都会阻塞                       │
│  - mutex 的零值是未锁定状态 — 可以直接使用                │
│  - struct 的零值是各字段的零值 — 通常可以安全使用          │
│                                                            │
│  这意味着：                                                │
│  1. 不需要显式初始化（var m sync.Mutex 就能用）            │
│  2. 不需要构造函数（var s Server 就能用）                  │
│  3. 零值通常是安全的（不会 panic 或产生未定义行为）        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

#### 6.2 零值在 SRE 中的应用

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

// 零值可用的结构体
type Config struct {
    Host    string // 零值 "" 可以用默认值
    Port    int    // 零值 0 可以用默认端口
    Timeout time.Duration // 零值 0 表示无超时
    Debug   bool   // 零值 false 表示关闭调试
}

// 零值可用的选项模式
type Option func(*Config)

func WithHost(host string) Option {
    return func(c *Config) { c.Host = host }
}

func WithPort(port int) Option {
    return func(c *Config) { c.Port = port }
}

func WithTimeout(d time.Duration) Option {
    return func(c *Config) { c.Timeout = d }
}

func NewConfig(opts ...Option) *Config {
    cfg := &Config{
        Host: "localhost", // 默认值
        Port: 8080,       // 默认值
    }
    for _, opt := range opts {
        opt(cfg)
    }
    return cfg
}

// 零值可用的缓存
type Cache struct {
    mu    sync.RWMutex      // 零值可用，不需要初始化
    items map[string]Item   // 零值 nil，需要在使用前初始化
}

type Item struct {
    Value     interface{}
    ExpiresAt time.Time
}

func NewCache() *Cache {
    return &Cache{
        items: make(map[string]Item),
    }
}

func (c *Cache) Get(key string) (interface{}, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()

    item, ok := c.items[key]
    if !ok {
        return nil, false
    }
    if !item.ExpiresAt.IsZero() && time.Now().After(item.ExpiresAt) {
        return nil, false // 过期
    }
    return item.Value, true
}

func (c *Cache) Set(key string, value interface{}, ttl time.Duration) {
    c.mu.Lock()
    defer c.mu.Unlock()

    var expiresAt time.Time
    if ttl > 0 {
        expiresAt = time.Now().Add(ttl)
    }
    // expiresAt 的零值表示永不过期

    c.items[key] = Item{
        Value:     value,
        ExpiresAt: expiresAt,
    }
}

// 零值可用的计数器
type Counter struct {
    mu    sync.Mutex // 零值可用
    value int64      // 零值 0
}

func (c *Counter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.value++
}

func (c *Counter) Value() int64 {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.value
}

func main() {
    // 配置选项模式
    cfg := NewConfig(
        WithHost("10.0.1.10"),
        WithPort(9090),
        WithTimeout(30 * time.Second),
    )
    fmt.Printf("Config: %+v\n", cfg)

    // 计数器 — 零值可用
    var counter Counter // 不需要 NewCounter()
    counter.Inc()
    counter.Inc()
    counter.Inc()
    fmt.Println("Counter:", counter.Value())

    // 缓存
    cache := NewCache()
    cache.Set("key1", "value1", 5*time.Minute)
    cache.Set("key2", "value2", 0) // 永不过期
    if val, ok := cache.Get("key1"); ok {
        fmt.Println("Cache:", val)
    }
}
```

### 7. SRE 实战案例

#### 7.1 结构化的监控指标

```go
package main

import (
    "encoding/json"
    "fmt"
    "math"
    "sync"
    "time"
)

// 指标类型
type MetricType string

const (
    MetricTypeGauge     MetricType = "gauge"
    MetricTypeCounter   MetricType = "counter"
    MetricTypeHistogram MetricType = "histogram"
)

// 指标定义
type MetricDef struct {
    Name      string            `json:"name"`
    Help      string            `json:"help"`
    Type      MetricType        `json:"type"`
    Labels    []string          `json:"labels"`
}

// 指标值
type MetricValue struct {
    Def       *MetricDef        `json:"-"`
    Labels    map[string]string `json:"labels"`
    Value     float64           `json:"value"`
    Timestamp time.Time         `json:"timestamp"`
}

// 指标收集器
type Collector struct {
    mu      sync.RWMutex
    defs    map[string]*MetricDef
    values  map[string][]*MetricValue
}

func NewCollector() *Collector {
    return &Collector{
        defs:   make(map[string]*MetricDef),
        values: make(map[string][]*MetricValue),
    }
}

func (c *Collector) Register(def MetricDef) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.defs[def.Name] = &def
}

func (c *Collector) Set(name string, value float64, labels map[string]string) {
    c.mu.Lock()
    defer c.mu.Unlock()

    def, ok := c.defs[name]
    if !ok {
        return
    }

    key := metricKey(name, labels)
    c.values[key] = append(c.values[key], &MetricValue{
        Def:       def,
        Labels:    labels,
        Value:     value,
        Timestamp: time.Now(),
    })
}

func metricKey(name string, labels map[string]string) string {
    data, _ := json.Marshal(labels)
    return name + string(data)
}

func (c *Collector) Export() []MetricValue {
    c.mu.RLock()
    defer c.mu.RUnlock()

    var result []MetricValue
    for _, values := range c.values {
        if len(values) > 0 {
            // 只导出最新的值
            latest := values[len(values)-1]
            result = append(result, *latest)
        }
    }
    return result
}

func (c *Collector) ExportPrometheus() string {
    c.mu.RLock()
    defer c.mu.RUnlock()

    var buf strings.Builder
    for _, def := range c.defs {
        fmt.Fprintf(&buf, "# HELP %s %s\n", def.Name, def.Help)
        fmt.Fprintf(&buf, "# TYPE %s %s\n", def.Name, def.Type)
    }

    for _, values := range c.values {
        if len(values) > 0 {
            latest := values[len(values)-1]
            fmt.Fprintf(&buf, "%s%s %f %d\n",
                latest.Def.Name,
                formatLabels(latest.Labels),
                latest.Value,
                latest.Timestamp.UnixMilli(),
            )
        }
    }
    return buf.String()
}

func formatLabels(labels map[string]string) string {
    if len(labels) == 0 {
        return ""
    }
    var parts []string
    for k, v := range labels {
        parts = append(parts, fmt.Sprintf("%s=%q", k, v))
    }
    return "{" + strings.Join(parts, ",") + "}"
}

func main() {
    collector := NewCollector()

    // 注册指标
    collector.Register(MetricDef{
        Name:   "http_requests_total",
        Help:   "Total HTTP requests",
        Type:   MetricTypeCounter,
        Labels: []string{"method", "path", "status"},
    })

    collector.Register(MetricDef{
        Name:   "cpu_usage_percent",
        Help:   "CPU usage percentage",
        Type:   MetricTypeGauge,
        Labels: []string{"instance"},
    })

    // 记录指标
    collector.Set("http_requests_total", 100, map[string]string{
        "method": "GET", "path": "/api/metrics", "status": "200",
    })
    collector.Set("cpu_usage_percent", 85.2, map[string]string{
        "instance": "web-01",
    })

    // 导出 Prometheus 格式
    fmt.Println(collector.ExportPrometheus())

    // 导出 JSON 格式
    metrics := collector.Export()
    data, _ := json.MarshalIndent(metrics, "", "  ")
    fmt.Println(string(data))
}
```

#### 7.2 配置管理

```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
    "time"
)

// 分层配置结构
type AppConfig struct {
    Server ServerConfig `json:"server"`
    DB     DBConfig     `json:"db"`
    Redis  RedisConfig  `json:"redis"`
    Log    LogConfig    `json:"log"`
}

type ServerConfig struct {
    Host         string        `json:"host"          env:"SERVER_HOST"     default:"0.0.0.0"`
    Port         int           `json:"port"          env:"SERVER_PORT"     default:"8080"`
    ReadTimeout  time.Duration `json:"read_timeout"  env:"READ_TIMEOUT"    default:"10s"`
    WriteTimeout time.Duration `json:"write_timeout" env:"WRITE_TIMEOUT"   default:"30s"`
    IdleTimeout  time.Duration `json:"idle_timeout"  env:"IDLE_TIMEOUT"    default:"60s"`
}

type DBConfig struct {
    Host     string `json:"host"     env:"DB_HOST"     default:"localhost"`
    Port     int    `json:"port"     env:"DB_PORT"     default:"5432"`
    Name     string `json:"name"     env:"DB_NAME"     default:"app"`
    User     string `json:"user"     env:"DB_USER"     default:"app"`
    Password string `json:"password" env:"DB_PASSWORD" default:""`
    MaxConns int    `json:"max_conns" env:"DB_MAX_CONNS" default:"10"`
}

type RedisConfig struct {
    Host     string `json:"host"     env:"REDIS_HOST"     default:"localhost"`
    Port     int    `json:"port"     env:"REDIS_PORT"     default:"6379"`
    Password string `json:"password" env:"REDIS_PASSWORD" default:""`
    DB       int    `json:"db"       env:"REDIS_DB"       default:"0"`
}

type LogConfig struct {
    Level  string `json:"level"  env:"LOG_LEVEL"  default:"info"`
    Format string `json:"format" env:"LOG_FORMAT" default:"json"`
    Output string `json:"output" env:"LOG_OUTPUT" default:"stdout"`
}

// 配置加载器
func LoadConfig(path string) (*AppConfig, error) {
    // 默认配置
    cfg := &AppConfig{
        Server: ServerConfig{
            Host:         "0.0.0.0",
            Port:         8080,
            ReadTimeout:  10 * time.Second,
            WriteTimeout: 30 * time.Second,
            IdleTimeout:  60 * time.Second,
        },
        DB: DBConfig{
            Host:     "localhost",
            Port:     5432,
            Name:     "app",
            User:     "app",
            MaxConns: 10,
        },
        Redis: RedisConfig{
            Host: "localhost",
            Port: 6379,
        },
        Log: LogConfig{
            Level:  "info",
            Format: "json",
            Output: "stdout",
        },
    }

    // 从文件加载
    if path != "" {
        data, err := os.ReadFile(path)
        if err != nil {
            return nil, fmt.Errorf("read config file: %w", err)
        }
        if err := json.Unmarshal(data, cfg); err != nil {
            return nil, fmt.Errorf("parse config file: %w", err)
        }
    }

    // 从环境变量覆盖（需要额外的库支持，这里简化展示）
    if host := os.Getenv("SERVER_HOST"); host != "" {
        cfg.Server.Host = host
    }
    if port := os.Getenv("SERVER_PORT"); port != "" {
        fmt.Sscanf(port, "%d", &cfg.Server.Port)
    }

    return cfg, nil
}

// 配置验证
func (c *AppConfig) Validate() error {
    if c.Server.Port < 1 || c.Server.Port > 65535 {
        return fmt.Errorf("invalid server port: %d", c.Server.Port)
    }
    if c.DB.MaxConns < 1 {
        return fmt.Errorf("invalid db max connections: %d", c.DB.MaxConns)
    }
    return nil
}

func main() {
    cfg, err := LoadConfig("")
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        os.Exit(1)
    }

    if err := cfg.Validate(); err != nil {
        fmt.Printf("Validation error: %v\n", err)
        os.Exit(1)
    }

    data, _ := json.MarshalIndent(cfg, "", "  ")
    fmt.Println(string(data))
}
```

### 8. struct 的高级模式

#### 8.1 选项模式（Functional Options）

```go
package main

import (
    "fmt"
    "time"
)

// 选项模式 — Go 中最优雅的配置方式

type Server struct {
    host         string
    port         int
    readTimeout  time.Duration
    writeTimeout time.Duration
    maxConns     int
    debug        bool
}

type Option func(*Server)

func WithHost(host string) Option {
    return func(s *Server) { s.host = host }
}

func WithPort(port int) Option {
    return func(s *Server) { s.port = port }
}

func WithReadTimeout(d time.Duration) Option {
    return func(s *Server) { s.readTimeout = d }
}

func WithWriteTimeout(d time.Duration) Option {
    return func(s *Server) { s.writeTimeout = d }
}

func WithMaxConns(n int) Option {
    return func(s *Server) { s.maxConns = n }
}

func WithDebug(debug bool) Option {
    return func(s *Server) { s.debug = debug }
}

func NewServer(opts ...Option) *Server {
    s := &Server{
        host:         "0.0.0.0",
        port:         8080,
        readTimeout:  10 * time.Second,
        writeTimeout: 30 * time.Second,
        maxConns:     100,
    }
    for _, opt := range opts {
        opt(s)
    }
    return s
}

func (s *Server) String() string {
    return fmt.Sprintf("Server{host=%s, port=%d, read=%v, write=%v, maxConns=%d, debug=%v}",
        s.host, s.port, s.readTimeout, s.writeTimeout, s.maxConns, s.debug)
}

func main() {
    // 使用默认配置
    s1 := NewServer()
    fmt.Println(s1)

    // 自定义配置
    s2 := NewServer(
        WithHost("10.0.1.10"),
        WithPort(9090),
        WithReadTimeout(5*time.Second),
        WithDebug(true),
    )
    fmt.Println(s2)
}
```

#### 8.2 Builder 模式

```go
package main

import "fmt"

type Query struct {
    table      string
    conditions []string
    orderBy    string
    limit      int
    offset     int
    fields     []string
}

type QueryBuilder struct {
    q Query
}

func NewQuery(table string) *QueryBuilder {
    return &QueryBuilder{
        q: Query{table: table},
    }
}

func (b *QueryBuilder) Where(condition string) *QueryBuilder {
    b.q.conditions = append(b.q.conditions, condition)
    return b
}

func (b *QueryBuilder) OrderBy(field string) *QueryBuilder {
    b.q.orderBy = field
    return b
}

func (b *QueryBuilder) Limit(n int) *QueryBuilder {
    b.q.limit = n
    return b
}

func (b *QueryBuilder) Offset(n int) *QueryBuilder {
    b.q.offset = n
    return b
}

func (b *QueryBuilder) Select(fields ...string) *QueryBuilder {
    b.q.fields = fields
    return b
}

func (b *QueryBuilder) Build() string {
    query := "SELECT "
    if len(b.q.fields) > 0 {
        query += strings.Join(b.q.fields, ", ")
    } else {
        query += "*"
    }
    query += " FROM " + b.q.table

    if len(b.q.conditions) > 0 {
        query += " WHERE " + strings.Join(b.q.conditions, " AND ")
    }
    if b.q.orderBy != "" {
        query += " ORDER BY " + b.q.orderBy
    }
    if b.q.limit > 0 {
        query += fmt.Sprintf(" LIMIT %d", b.q.limit)
    }
    if b.q.offset > 0 {
        query += fmt.Sprintf(" OFFSET %d", b.q.offset)
    }

    return query
}

func main() {
    query := NewQuery("servers").
        Where("status = 'healthy'").
        Where("env = 'prod'").
        Select("name", "ip", "port").
        OrderBy("name").
        Limit(10).
        Build()

    fmt.Println(query)
    // SELECT name, ip, port FROM servers WHERE status = 'healthy' AND env = 'prod' ORDER BY name LIMIT 10
}
```

#### 8.3 struct 嵌入实现接口组合

```go
package main

import "fmt"

// 接口定义
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type Closer interface {
    Close() error
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

// 通过嵌入实现接口组合
type File struct {
    name   string
    data   []byte
    offset int
    closed bool
}

func (f *File) Read(p []byte) (n int, err error) {
    if f.closed {
        return 0, fmt.Errorf("file closed")
    }
    n = copy(p, f.data[f.offset:])
    f.offset += n
    return n, nil
}

func (f *File) Write(p []byte) (n int, err error) {
    if f.closed {
        return 0, fmt.Errorf("file closed")
    }
    f.data = append(f.data, p...)
    return len(p), nil
}

func (f *File) Close() error {
    f.closed = true
    return nil
}

// 嵌入实现中间件模式
type BufferedReadWriter struct {
    ReadWriter // 嵌入接口
    buf        []byte
}

func NewBufferedReadWriter(rw ReadWriter) *BufferedReadWriter {
    return &BufferedReadWriter{
        ReadWriter: rw,
        buf:        make([]byte, 0, 4096),
    }
}

func (brw *BufferedReadWriter) Flush() error {
    if len(brw.buf) > 0 {
        _, err := brw.Write(brw.buf)
        brw.buf = brw.buf[:0]
        return err
    }
    return nil
}

func main() {
    f := &File{name: "test.txt"}
    f.Write([]byte("Hello, SRE!"))

    buf := make([]byte, 1024)
    n, _ := f.Read(buf)
    fmt.Println(string(buf[:n]))

    f.Close()
}
```

## 💻 实战练习

### 练习 1：基础操作 — 结构体内存对齐优化

**目标：** 优化一个结构体的内存布局，减少内存占用。

```go
package main

import (
    "fmt"
    "unsafe"
)

// 优化前
type BadMetric struct {
    Name      string   // 16 bytes
    IsGauge   bool     // 1 byte + 7 padding
    Value     float64  // 8 bytes
    Labels    []string // 24 bytes
    Timestamp int64    // 8 bytes
    Active    bool     // 1 byte + 7 padding
}

// 优化后
type GoodMetric struct {
    Value     float64  // 8 bytes
    Timestamp int64    // 8 bytes
    Name      string   // 16 bytes
    Labels    []string // 24 bytes
    IsGauge   bool     // 1 byte
    Active    bool     // 1 byte + 6 padding
}

func main() {
    fmt.Printf("BadMetric:  %d bytes\n", unsafe.Sizeof(BadMetric{}))
    fmt.Printf("GoodMetric: %d bytes\n", unsafe.Sizeof(GoodMetric{}))

    // 查看字段偏移量
    var m BadMetric
    fmt.Println("\nBadMetric field offsets:")
    fmt.Printf("  Name:      %d\n", unsafe.Offsetof(m.Name))
    fmt.Printf("  IsGauge:   %d\n", unsafe.Offsetof(m.IsGauge))
    fmt.Printf("  Value:     %d\n", unsafe.Offsetof(m.Value))
    fmt.Printf("  Labels:    %d\n", unsafe.Offsetof(m.Labels))
    fmt.Printf("  Timestamp: %d\n", unsafe.Offsetof(m.Timestamp))
    fmt.Printf("  Active:    %d\n", unsafe.Offsetof(m.Active))
}
```

**验证标准：**
- [ ] 能计算结构体的内存大小
- [ ] 理解字段对齐规则
- [ ] 能优化结构体布局减少内存占用

### 练习 2：进阶场景 — JSON 序列化与反序列化

**目标：** 实现一个配置文件的加载和验证系统。

```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
    "time"
)

type Config struct {
    Server ServerConfig `json:"server"`
    Cache  CacheConfig  `json:"cache"`
    Log    LogConfig    `json:"log"`
}

type ServerConfig struct {
    Host    string        `json:"host"`
    Port    int           `json:"port"`
    Timeout time.Duration `json:"timeout"`
}

type CacheConfig struct {
    TTL     time.Duration `json:"ttl"`
    MaxSize int           `json:"max_size"`
}

type LogConfig struct {
    Level  string `json:"level"`
    Format string `json:"format"`
}

func (c *Config) Validate() error {
    if c.Server.Port < 1 || c.Server.Port > 65535 {
        return fmt.Errorf("invalid port: %d", c.Server.Port)
    }
    if c.Cache.MaxSize < 0 {
        return fmt.Errorf("invalid cache max_size: %d", c.Cache.MaxSize)
    }
    return nil
}

// 自定义 Duration 的 JSON 序列化
type Duration struct {
    time.Duration
}

func (d Duration) MarshalJSON() ([]byte, error) {
    return json.Marshal(d.String())
}

func (d *Duration) UnmarshalJSON(b []byte) error {
    var s string
    if err := json.Unmarshal(b, &s); err != nil {
        return err
    }
    dur, err := time.ParseDuration(s)
    if err != nil {
        return err
    }
    d.Duration = dur
    return nil
}

func loadConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("read config: %w", err)
    }

    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("parse config: %w", err)
    }

    if err := cfg.Validate(); err != nil {
        return nil, fmt.Errorf("validate config: %w", err)
    }

    return &cfg, nil
}

func main() {
    // 创建示例配置
    configJSON := `{
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "timeout": "30s"
        },
        "cache": {
            "ttl": "5m",
            "max_size": 1000
        },
        "log": {
            "level": "info",
            "format": "json"
        }
    }`

    // 写入临时文件
    tmpFile := "/tmp/config.json"
    os.WriteFile(tmpFile, []byte(configJSON), 0644)

    // 加载配置
    cfg, err := loadConfig(tmpFile)
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }

    fmt.Printf("Server: %s:%d (timeout: %v)\n",
        cfg.Server.Host, cfg.Server.Port, cfg.Server.Timeout)
    fmt.Printf("Cache:  TTL=%v, MaxSize=%d\n",
        cfg.Cache.TTL, cfg.Cache.MaxSize)
    fmt.Printf("Log:    Level=%s, Format=%s\n",
        cfg.Log.Level, cfg.Log.Format)
}
```

**验证标准：**
- [ ] 能正确使用 JSON 标签
- [ ] 能实现自定义类型的 JSON 序列化
- [ ] 能实现配置验证逻辑

### 练习 3：故障排查挑战

**场景：** 以下代码有多个问题，请找出并修复。

```go
package main

import (
    "encoding/json"
    "fmt"
)

// 问题 1：JSON 标签错误
type User struct {
    ID       int    `json:"id"`
    Name     string `json:"name"`
    Email    string `json:"email"`
    Password string `json:"password"` // 应该被忽略
    internal string                   // 未导出，不会被序列化
}

// 问题 2：方法接收者选择错误
type Counter struct {
    value int
}

func (c Counter) Increment() { // 应该用指针接收者
    c.value++
}

func (c Counter) Value() int {
    return c.value
}

// 问题 3：嵌入冲突
type A struct {
    Name string
}

type B struct {
    Name string
}

type C struct {
    A
    B
}

// 问题 4：零值不可用
type Cache struct {
    items map[string]string // nil map，写入会 panic
}

func (c *Cache) Set(key, value string) {
    c.items[key] = value // panic!
}

// 问题 5：JSON 序列化丢失精度
type Metrics struct {
    CPU    float64 `json:"cpu"`
    Memory float64 `json:"memory"`
}

func main() {
    // 测试问题 1
    user := User{ID: 1, Name: "test", Password: "secret"}
    data, _ := json.Marshal(user)
    fmt.Println(string(data))

    // 测试问题 2
    counter := Counter{}
    counter.Increment()
    counter.Increment()
    fmt.Println("Counter:", counter.Value())

    // 测试问题 3
    c := C{A: A{Name: "Alice"}, B: B{Name: "Bob"}}
    fmt.Println(c.Name) // 歧义

    // 测试问题 4
    cache := &Cache{}
    cache.Set("key", "value")

    // 测试问题 5
    metrics := Metrics{CPU: 85.123456789, Memory: 72.987654321}
    data, _ = json.Marshal(metrics)
    fmt.Println(string(data))
}
```

**任务：**
1. 修复 JSON 标签，使 password 不被序列化
2. 修复方法接收者，使 Increment 能修改原始值
3. 解决嵌入冲突
4. 使 Cache 的零值可用
5. 控制 JSON 序列化的精度

## 🎯 面试题精选

### Q1: Go 的 struct 和 class 有什么区别？

**参考答案：**

Go 没有 class，只有 struct。主要区别：
1. **没有继承**：Go 使用嵌入（embedding）实现组合，不是 "is-a" 关系而是 "has-a" 关系。
2. **没有构造函数**：Go 使用工厂函数（NewXxx）或零值可用的设计。
3. **方法定义在类型外部**：Go 的方法定义在 struct 之外，通过接收者关联。
4. **值类型**：struct 是值类型，赋值和传参会复制；class 通常是引用类型。
5. **没有访问修饰符**：Go 通过大小写控制可见性（大写导出，小写未导出）。

### Q2: 值接收者和指针接收者有什么区别？什么时候用哪个？

**参考答案：**

| 特性 | 值接收者 | 指针接收者 |
|------|---------|-----------|
| 修改原始值 | 不能 | 能 |
| 拷贝开销 | 有（大结构体高） | 无（只传指针） |
| 接口实现 | 值和指针都能匹配 | 只有指针能匹配 |
| 并发安全 | 每个调用操作副本 | 需要自己加锁 |

选择指南：
- 需要修改接收者 → 指针接收者
- 结构体很大 → 指针接收者
- 包含 sync.Mutex 等不可复制字段 → 指针接收者
- 其他情况 → 值接收者
- 一致性：如果一个方法需要指针，所有方法都用指针

### Q3: struct 的内存对齐是什么？为什么要关心它？

**参考答案：**

内存对齐是 CPU 读取内存的优化机制。CPU 按"字"（word，通常是 4 或 8 字节）读取内存，对齐的数据可以一次读取完成，未对齐的数据可能需要两次读取。

struct 的字段按照对齐规则排列，可能导致字段之间有填充（padding）。通过合理排列字段顺序，可以减少填充，节省内存。

```go
// 未优化：24 bytes
type Bad struct {
    a bool    // 1 + 7 padding
    b int64   // 8
    c int32   // 4 + 4 padding
}

// 优化后：16 bytes
type Good struct {
    b int64   // 8
    c int32   // 4
    a bool    // 1 + 3 padding
}
```

### Q4: Go 的嵌入（embedding）和继承有什么区别？

**参考答案：**

| 特性 | 继承 | 嵌入 |
|------|------|------|
| 关系 | is-a | has-a |
| 耦合 | 强耦合 | 松耦合 |
| 多重继承 | 受限/复杂 | 自然支持 |
| 方法覆盖 | 显式覆盖 | 需要显式定义同名方法 |
| 类型关系 | 子类是父类的特化 | 嵌入类型是独立的类型 |

Go 的嵌入是"组合优于继承"原则的体现：
- 嵌入的字段和方法被"提升"到外层结构体
- 可以同时嵌入多个类型
- 没有菱形继承问题
- 测试时可以轻松替换嵌入的组件

### Q5: JSON 标签中的 omitempty 是什么意思？零值有哪些？

**参考答案：**

`omitempty` 表示当字段值为零值时，在 JSON 编码中省略该字段。

各类型的零值：
- `int/float`: 0/0.0
- `string`: ""
- `bool`: false
- `slice/map/pointer`: nil
- `time.Time`: 零值时间
- `struct`: 所有字段都是零值

注意事项：
- `int` 的 0 会被省略（如果需要保留 0，不要用 omitempty）
- `bool` 的 false 会被省略
- 空 slice `[]int{}` 不会被省略（只有 nil 会）

### Q6: struct 的标签是怎么存储和解析的？

**参考答案：**

struct 标签存储在 `reflect.StructField.Tag` 中，类型是 `reflect.StructTag`（本质是 string）。

标签格式：`key1:"value1" key2:"value2"`

解析方式：
```go
field, _ := reflect.TypeOf(MyStruct{}).FieldByName("MyField")
tag := field.Tag.Get("json")        // 获取 json 标签
tag, ok := field.Tag.Lookup("json") // 获取并检查是否存在
```

注意事项：
- 标签在编译时确定，不能动态修改
- 标签值必须用双引号包裹
- 反射解析有性能开销，应缓存结果

### Q7: 什么是零值可用？为什么 Go 的设计强调这一点？

**参考答案：**

"零值可用"（zero value useful）是 Go 的设计哲学之一，意思是类型的零值应该是一个合法的、可安全使用的状态。

例子：
- `sync.Mutex` 的零值是未锁定状态，可以直接使用
- `bytes.Buffer` 的零值是空缓冲区，可以直接写入
- `[]int` 的零值是 nil，可以安全地 append

这样设计的好处：
1. **不需要构造函数**：`var m sync.Mutex` 就能用
2. **减少初始化代码**：不需要 `new()` 或 `make()`
3. **更安全**：忘记初始化不会导致 panic（大部分情况）
4. **更简洁**：代码更少，意图更清晰

## 📚 深入阅读

- [Go 语言规范 - Struct](https://go.dev/ref/spec#Struct_types) — 官方规范
- [Effective Go - Composite types](https://go.dev/doc/effective_go#composite_types) — 官方指南
- [JSON and Go](https://go.dev/blog/json) — 官方 JSON 博客
- [Go Struct Tag 详解](https://github.com/fatih/structs) — 结构体操作库
- [Go 内存对齐](https://pkg.go.dev/unsafe#Sizeof) — unsafe 包文档
- [Go 设计哲学](https://go.dev/doc/effective_go) — Effective Go
- [Struct 嵌入与组合](https://go.dev/doc/effective_go#embedding) — 嵌入详解

## ✅ 自检清单

### 理论检查点
- [ ] 理解 struct 的内存布局和对齐机制
- [ ] 掌握值接收者和指针接收者的区别
- [ ] 理解嵌入（embedding）与继承的区别
- [ ] 掌握 JSON 标签的完整用法
- [ ] 理解零值语义的设计哲学

### 实操检查点
- [ ] 能优化 struct 的内存布局
- [ ] 能正确实现 JSON 序列化/反序列化
- [ ] 能使用选项模式创建灵活的构造函数
- [ ] 能实现自定义类型的 JSON 序列化
- [ ] 能正确使用 struct 标签

### 能力验证标准
- [ ] 能解释 struct 的内存对齐规则并优化布局
- [ ] 能设计零值可用的数据结构
- [ ] 能实现完整的配置管理系统（加载、验证、序列化）
