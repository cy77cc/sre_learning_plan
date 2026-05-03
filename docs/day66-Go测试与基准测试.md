# Day 66: Go 测试与基准测试

> 📅 日期：2026-05-03
> 📖 学习主题：Go 测试体系、表驱动测试、基准测试、模糊测试、覆盖率与 SRE 测试实战
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 58 Go 基础语法、Day 59 函数与错误处理

## 🎯 学习目标

完成 Day 66 的学习后，你应该能够：
1. 熟练使用 `testing` 包编写单元测试、表驱动测试、子测试
2. 掌握 `TestMain` 进行测试初始化和清理
3. 编写基准测试并分析性能数据
4. 使用 `httptest` 和 `sqlmock` 测试 HTTP 处理器和数据库操作
5. 理解模糊测试（Fuzz Testing）并应用于 SRE 工具验证
6. 达到 80% 以上的测试覆盖率

---

## 📖 核心知识点

### 1. Go 测试基础

#### 1.1 测试文件规范

Go 测试遵循严格的命名规范：

```
项目结构：
myproject/
├── main.go
├── handler.go
├── handler_test.go      ← handler.go 的测试
├── db/
│   ├── query.go
│   └── query_test.go    ← query.go 的测试
└── internal/
    ├── utils.go
    └── utils_test.go    ← utils.go 的测试
```

**规范要求：**
- 测试文件以 `_test.go` 结尾
- 测试函数以 `Test` 开头，参数为 `*testing.T`
- 基准函数以 `Benchmark` 开头，参数为 `*testing.B`
- 模糊测试函数以 `Fuzz` 开头，参数为 `*testing.F`
- 示例函数以 `Example` 开头，无参数

```go
// calculator.go
package calculator

func Add(a, b int) int {
    return a + b
}

func Divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, ErrDivisionByZero
    }
    return a / b, nil
}
```

```go
// calculator_test.go
package calculator

import (
    "errors"
    "testing"
)

func TestAdd(t *testing.T) {
    result := Add(2, 3)
    if result != 5 {
        t.Errorf("Add(2, 3) = %d; want 5", result)
    }
}

func TestDivide(t *testing.T) {
    result, err := Divide(10, 2)
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if result != 5.0 {
        t.Errorf("Divide(10, 2) = %f; want 5.0", result)
    }
}

func TestDivideByZero(t *testing.T) {
    _, err := Divide(10, 0)
    if !errors.Is(err, ErrDivisionByZero) {
        t.Errorf("expected ErrDivisionByZero, got %v", err)
    }
}
```

#### 1.2 testing.T 核心方法

| 方法 | 作用 | 继续执行 |
|------|------|----------|
| `t.Log(args...)` | 输出日志（-v 时显示） | 是 |
| `t.Logf(format, args...)` | 格式化日志 | 是 |
| `t.Error(args...)` | 标记失败，继续执行 | 是 |
| `t.Errorf(format, args...)` | 格式化失败信息 | 是 |
| `t.Fatal(args...)` | 标记失败，立即停止当前测试 | 否 |
| `t.Fatalf(format, args...)` | 格式化失败并停止 | 否 |
| `t.Skip(args...)` | 跳过测试 | 否 |
| `t.Skipf(format, args...)` | 格式化跳过信息 | 否 |
| `t.Parallel()` | 标记为可并行执行 | 是 |
| `t.Run(name, func)` | 运行子测试 | 是 |
| `t.Helper()` | 标记为辅助函数 | - |
| `t.Cleanup(func)` | 注册清理函数 | - |
| `t.TempDir()` | 创建临时目录 | - |

```go
func TestExample(t *testing.T) {
    t.Log("这是一条日志")             // -v 时显示
    t.Error("标记失败但继续执行")      // 测试继续
    t.Fatal("标记失败并立即停止")      // 不会执行到这里
    t.Log("这行不会执行")
}
```

#### 1.3 运行测试

```bash
# 运行当前包的所有测试
go test

# 运行当前目录及子目录的所有测试
go test ./...

# 运行指定测试函数
go test -run TestAdd

# 使用正则匹配
go test -run "TestDivide.*"

# 详细输出
go test -v

# 运行基准测试
go test -bench=.

# 显示测试覆盖率
go test -cover

# 生成覆盖率报告
go test -coverprofile=coverage.out
go tool cover -html=coverage.out -o coverage.html

# 运行模糊测试
go test -fuzz=FuzzParseInput

# 设置超时
go test -timeout 30s

# 并行度
go test -parallel 4

# 运行指定包
go test ./pkg/...
go test github.com/user/project/pkg/...
```

---

### 2. 表驱动测试（Table-Driven Tests）

#### 2.1 标准模式

表驱动测试是 Go 社区推荐的标准测试模式，用一个切片存放测试用例，循环执行：

```go
package calculator

import (
    "testing"
)

func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"正数相加", 2, 3, 5},
        {"负数相加", -2, -3, -5},
        {"零值", 0, 0, 0},
        {"正负混合", 5, -3, 2},
        {"大数", 1000000, 2000000, 3000000},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Add(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```

#### 2.2 带错误处理的表驱动测试

```go
func TestDivide(t *testing.T) {
    tests := []struct {
        name        string
        a, b        float64
        expected    float64
        expectedErr error
    }{
        {"正常除法", 10, 2, 5.0, nil},
        {"除以零", 10, 0, 0, ErrDivisionByZero},
        {"负数除法", -10, 2, -5.0, nil},
        {"小数除法", 1, 3, 0.333333, nil},
        {"零除以数", 0, 5, 0, nil},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result, err := Divide(tt.a, tt.b)

            // 检查错误
            if tt.expectedErr != nil {
                if !errors.Is(err, tt.expectedErr) {
                    t.Fatalf("expected error %v, got %v", tt.expectedErr, err)
                }
                return // 有错误就不检查结果
            }

            if err != nil {
                t.Fatalf("unexpected error: %v", err)
            }

            // 浮点数比较需要容差
            if diff := result - tt.expected; diff > 0.001 || diff < -0.001 {
                t.Errorf("Divide(%f, %f) = %f; want %f", tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```

#### 2.3 并行表驱动测试

```go
func TestAddParallel(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"case1", 1, 2, 3},
        {"case2", 3, 4, 7},
        {"case3", 5, 6, 11},
        {"case4", 7, 8, 15},
    }

    for _, tt := range tests {
        tt := tt // 重要：捕获循环变量
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel() // 标记为可并行
            result := Add(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d", tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```

> **注意：** Go 1.22+ 不再需要 `tt := tt` 来捕获循环变量，因为 range 循环变量的语义已经改变。但对于 Go 1.21 及以下版本，这行代码是必须的。

---

### 3. 子测试与测试组织

#### 3.1 子测试嵌套

```go
func TestUserValidation(t *testing.T) {
    t.Run("用户名验证", func(t *testing.T) {
        t.Run("长度", func(t *testing.T) {
            tests := []struct {
                name  string
                input string
                valid bool
            }{
                {"空字符串", "", false},
                {"太短", "ab", false},
                {"正常", "alice", true},
                {"太长", strings.Repeat("a", 256), false},
            }
            for _, tt := range tests {
                t.Run(tt.name, func(t *testing.T) {
                    got := ValidateUsername(tt.input)
                    if got != tt.valid {
                        t.Errorf("ValidateUsername(%q) = %v; want %v", tt.input, got, tt.valid)
                    }
                })
            }
        })

        t.Run("字符", func(t *testing.T) {
            tests := []struct {
                name  string
                input string
                valid bool
            }{
                {"纯字母", "alice", true},
                {"含数字", "alice123", true},
                {"含特殊字符", "alice@123", false},
                {"含空格", "alice bob", false},
            }
            for _, tt := range tests {
                t.Run(tt.name, func(t *testing.T) {
                    got := ValidateUsername(tt.input)
                    if got != tt.valid {
                        t.Errorf("ValidateUsername(%q) = %v; want %v", tt.input, got, tt.valid)
                    }
                })
            }
        })
    })

    t.Run("邮箱验证", func(t *testing.T) {
        // ...
    })
}
```

#### 3.2 Helper 函数与 t.Helper()

```go
// t.Helper() 标记函数为辅助函数
// 当测试失败时，错误信息会指向调用辅助函数的行，而不是辅助函数内部
func assertEqual(t *testing.T, got, want interface{}) {
    t.Helper() // 关键：标记为辅助函数
    if got != want {
        t.Errorf("got %v; want %v", got, want)
    }
}

func assertNoError(t *testing.T, err error) {
    t.Helper()
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
}

func assertError(t *testing.T, err error) {
    t.Helper()
    if err == nil {
        t.Fatal("expected error, got nil")
    }
}

func TestSomething(t *testing.T) {
    result, err := DoSomething()
    assertNoError(t, err)
    assertEqual(t, result, "expected")
}
```

#### 3.3 t.Cleanup 与 t.TempDir

```go
func TestWithCleanup(t *testing.T) {
    // t.Cleanup 注册清理函数，测试结束后自动执行（即使测试失败）
    t.Cleanup(func() {
        fmt.Println("清理资源...")
    })

    // t.TempDir 创建临时目录，测试结束后自动删除
    dir := t.TempDir()
    filepath := filepath.Join(dir, "test.txt")
    os.WriteFile(filepath, []byte("test data"), 0644)
}
```

---

### 4. TestMain：测试入口

#### 4.1 使用场景

`TestMain` 用于全局的测试初始化和清理，例如：
- 设置测试数据库
- 启动测试服务器
- 加载测试配置
- 全局清理

```go
package db

import (
    "database/sql"
    "fmt"
    "os"
    "testing"

    _ "github.com/go-sql-driver/mysql"
)

var testDB *sql.DB

func TestMain(m *testing.M) {
    // 测试前的初始化
    fmt.Println("=== 测试初始化 ===")

    var err error
    testDB, err = sql.Open("mysql", "test:test@tcp(localhost:3306)/testdb")
    if err != nil {
        fmt.Printf("连接测试数据库失败: %v\n", err)
        os.Exit(1)
    }

    // 确保数据库连接正常
    if err := testDB.Ping(); err != nil {
        fmt.Printf("数据库 ping 失败: %v\n", err)
        os.Exit(1)
    }

    // 执行测试
    code := m.Run()

    // 测试后的清理
    fmt.Println("=== 测试清理 ===")
    testDB.Close()

    os.Exit(code)
}

func TestQueryUser(t *testing.T) {
    if testDB == nil {
        t.Fatal("测试数据库未初始化")
    }

    var name string
    err := testDB.QueryRow("SELECT name FROM users WHERE id = ?", 1).Scan(&name)
    if err != nil {
        t.Fatalf("查询失败: %v", err)
    }

    if name == "" {
        t.Error("用户名不应为空")
    }
}
```

#### 4.2 TestMain 注意事项

```go
// 每个包只能有一个 TestMain
// TestMain 中必须调用 m.Run()
// 使用 os.Exit 退出，因为 m.Run() 返回退出码
// defer 在 os.Exit 前不会执行，需要手动调用清理函数

func TestMain(m *testing.M) {
    setup()
    code := m.Run()
    teardown()
    os.Exit(code)
}
```

---

### 5. 基准测试（Benchmark）

#### 5.1 基准测试基础

```go
package performance

import (
    "fmt"
    "strings"
    "testing"
)

// 基准测试函数以 Benchmark 开头
func BenchmarkStringConcat(b *testing.B) {
    for i := 0; i < b.N; i++ {
        s := ""
        for j := 0; j < 100; j++ {
            s += "a"
        }
    }
}

func BenchmarkStringBuilder(b *testing.B) {
    for i := 0; i < b.N; i++ {
        var sb strings.Builder
        for j := 0; j < 100; j++ {
            sb.WriteString("a")
        }
        _ = sb.String()
    }
}

func BenchmarkFmtSprintf(b *testing.B) {
    for i := 0; i < b.N; i++ {
        _ = fmt.Sprintf("hello %s %d", "world", 42)
    }
}
```

**运行基准测试：**
```bash
# 运行所有基准测试
go test -bench=.

# 运行指定基准测试
go test -bench=BenchmarkStringConcat

# 设置运行时间（默认 1 秒）
go test -bench=. -benchtime=5s

# 设置迭代次数
go test -bench=. -benchtime=10000x

# 内存分配统计
go test -bench=. -benchmem

# 输出示例：
# BenchmarkStringConcat-8     100000    12345 ns/op    5024 B/op    99 allocs/op
# BenchmarkStringBuilder-8   1000000     1234 ns/op     512 B/op     8 allocs/op
```

#### 5.2 基准测试结果解读

```
BenchmarkStringConcat-8     100000    12345 ns/op    5024 B/op    99 allocs/op
│                           │         │              │            │
│                           │         │              │            └─ 内存分配次数
│                           │         │              └─ 每次操作分配的字节数
│                           │         └─ 每次操作耗时（纳秒）
│                           └─ 迭代次数
└─ 基准测试名称-GOMAXPROCS
```

#### 5.3 使用 b.ResetTimer

```go
func BenchmarkWithSetup(b *testing.B) {
    // 耗时的初始化
    data := makeLargeDataset()

    b.ResetTimer() // 重置计时器，排除初始化时间

    for i := 0; i < b.N; i++ {
        process(data)
    }
}

func BenchmarkWithParallel(b *testing.B) {
    data := makeLargeDataset()

    b.ResetTimer()
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            process(data)
        }
    })
}
```

#### 5.4 比较基准测试

```go
func BenchmarkMapLookup(b *testing.B) {
    m := make(map[string]int)
    for i := 0; i < 1000; i++ {
        m[fmt.Sprintf("key%d", i)] = i
    }

    b.Run("小map", func(b *testing.B) {
        small := make(map[string]int)
        for i := 0; i < 10; i++ {
            small[fmt.Sprintf("key%d", i)] = i
        }
        b.ResetTimer()
        for i := 0; i < b.N; i++ {
            _ = small["key5"]
        }
    })

    b.Run("大map", func(b *testing.B) {
        b.ResetTimer()
        for i := 0; i < b.N; i++ {
            _ = m["key500"]
        }
    })
}
```

---

### 6. 模糊测试（Fuzz Testing）

#### 6.1 模糊测试基础

Go 1.18 引入了原生模糊测试支持。模糊测试自动生成随机输入，发现代码中的边界情况和崩溃：

```go
package parser

import (
    "testing"
)

// ParseInput 解析输入字符串
func ParseInput(s string) (int, error) {
    if len(s) == 0 {
        return 0, ErrEmptyInput
    }
    // 简单的整数解析
    result := 0
    negative := false
    start := 0
    if s[0] == '-' {
        negative = true
        start = 1
    }
    for i := start; i < len(s); i++ {
        if s[i] < '0' || s[i] > '9' {
            return 0, ErrInvalidInput
        }
        result = result*10 + int(s[i]-'0')
    }
    if negative {
        result = -result
    }
    return result, nil
}

// 模糊测试函数以 Fuzz 开头
func FuzzParseInput(f *testing.F) {
    // 添加种子语料库（seed corpus）
    f.Add("123")
    f.Add("-456")
    f.Add("0")
    f.Add("")

    // 模糊测试核心逻辑
    f.Fuzz(func(t *testing.T, input string) {
        result, err := ParseInput(input)

        // 不变量检查
        if err == nil {
            // 如果解析成功，将结果转回字符串应该得到相同的结果
            // 这里我们只检查不会 panic
            _ = result
        }
    })
}
```

**运行模糊测试：**
```bash
# 运行模糊测试（持续运行直到发现失败或手动停止）
go test -fuzz=FuzzParseInput

# 运行模糊测试指定时间
go test -fuzz=FuzzParseInput -fuzztime=30s

# 运行种子语料库（不进行模糊）
go test -run=FuzzParseInput
```

#### 6.2 SRE 场景：配置解析模糊测试

```go
package config

import (
    "encoding/json"
    "testing"
)

type Config struct {
    Host    string `json:"host"`
    Port    int    `json:"port"`
    Timeout int    `json:"timeout"`
    Debug   bool   `json:"debug"`
}

func ParseConfig(data []byte) (*Config, error) {
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return nil, err
    }
    if cfg.Port < 0 || cfg.Port > 65535 {
        return nil, ErrInvalidPort
    }
    if cfg.Timeout < 0 {
        return nil, ErrInvalidTimeout
    }
    return &cfg, nil
}

func FuzzParseConfig(f *testing.F) {
    // 种子语料
    f.Add([]byte(`{"host":"localhost","port":8080,"timeout":30}`))
    f.Add([]byte(`{}`))
    f.Add([]byte(`{"port":-1}`))
    f.Add([]byte(`{"port":99999}`))

    f.Fuzz(func(t *testing.T, data []byte) {
        cfg, err := ParseConfig(data)
        if err != nil {
            return // 有错误就跳过
        }

        // 不变量：端口必须在合法范围
        if cfg.Port < 0 || cfg.Port > 65535 {
            t.Errorf("端口超出范围: %d", cfg.Port)
        }

        // 不变量：超时不能为负
        if cfg.Timeout < 0 {
            t.Errorf("超时不能为负: %d", cfg.Timeout)
        }
    })
}
```

---

### 7. HTTP 测试：httptest 包

#### 7.1 测试 HTTP Handler

```go
package handler

import (
    "encoding/json"
    "io"
    "net/http"
    "net/http/httptest"
    "testing"
)

// HealthHandler 健康检查处理器
func HealthHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

// UserHandler 用户查询处理器
func UserHandler(w http.ResponseWriter, r *http.Request) {
    id := r.URL.Query().Get("id")
    if id == "" {
        http.Error(w, `{"error": "missing id"}`, http.StatusBadRequest)
        return
    }

    user := map[string]string{
        "id":   id,
        "name": "testuser",
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}

func TestHealthHandler(t *testing.T) {
    // 创建请求
    req := httptest.NewRequest("GET", "/health", nil)
    // 创建响应记录器
    w := httptest.NewRecorder()

    // 调用处理器
    HealthHandler(w, req)

    // 检查响应
    resp := w.Result()
    if resp.StatusCode != http.StatusOK {
        t.Errorf("状态码 = %d; want %d", resp.StatusCode, http.StatusOK)
    }

    body, _ := io.ReadAll(resp.Body)
    expected := `{"status":"ok"}`
    if string(body) != expected+"\n" {
        t.Errorf("响应体 = %s; want %s", body, expected)
    }
}

func TestUserHandler(t *testing.T) {
    tests := []struct {
        name       string
        query      string
        wantCode   int
        wantBody   string
    }{
        {"正常请求", "id=123", http.StatusOK, `"id":"123"`},
        {"缺少 id", "", http.StatusBadRequest, "missing id"},
        {"空 id", "id=", http.StatusOK, `"id":""`},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            url := "/user"
            if tt.query != "" {
                url += "?" + tt.query
            }
            req := httptest.NewRequest("GET", url, nil)
            w := httptest.NewRecorder()

            UserHandler(w, req)

            resp := w.Result()
            if resp.StatusCode != tt.wantCode {
                t.Errorf("状态码 = %d; want %d", resp.StatusCode, tt.wantCode)
            }

            body, _ := io.ReadAll(resp.Body)
            if !contains(string(body), tt.wantBody) {
                t.Errorf("响应体 = %s; 不包含 %s", body, tt.wantBody)
            }
        })
    }
}

func contains(s, substr string) bool {
    return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsSubstr(s, substr))
}

func containsSubstr(s, substr string) bool {
    for i := 0; i <= len(s)-len(substr); i++ {
        if s[i:i+len(substr)] == substr {
            return true
        }
    }
    return false
}
```

#### 7.2 使用 httptest.Server 测试完整 HTTP 客户端

```go
package client

import (
    "encoding/json"
    "io"
    "net/http"
    "net/http/httptest"
    "testing"
)

// APIClient API 客户端
type APIClient struct {
    BaseURL    string
    HTTPClient *http.Client
}

func (c *APIClient) GetUser(id string) (map[string]string, error) {
    resp, err := c.HTTPClient.Get(c.BaseURL + "/user?id=" + id)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var user map[string]string
    if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
        return nil, err
    }
    return user, nil
}

func TestAPIClient_GetUser(t *testing.T) {
    // 创建模拟服务器
    server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        id := r.URL.Query().Get("id")
        if id == "" {
            http.Error(w, "missing id", http.StatusBadRequest)
            return
        }

        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(map[string]string{
            "id":   id,
            "name": "MockUser",
        })
    }))
    defer server.Close() // 测试结束后关闭

    // 创建使用模拟服务器的客户端
    client := &APIClient{
        BaseURL:    server.URL,
        HTTPClient: server.Client(),
    }

    // 测试正常请求
    user, err := client.GetUser("123")
    if err != nil {
        t.Fatalf("GetUser failed: %v", err)
    }
    if user["name"] != "MockUser" {
        t.Errorf("name = %s; want MockUser", user["name"])
    }
}
```

---

### 8. sqlmock：数据库测试

#### 8.1 安装与基础使用

```go
package db

import (
    "context"
    "database/sql"
    "testing"

    "github.com/DATA-DOG/go-sqlmock"
)

// UserRepository 用户仓库
type UserRepository struct {
    db *sql.DB
}

func (r *UserRepository) GetByID(ctx context.Context, id int) (string, error) {
    var name string
    err := r.db.QueryRowContext(ctx, "SELECT name FROM users WHERE id = ?", id).Scan(&name)
    if err != nil {
        return "", err
    }
    return name, nil
}

func (r *UserRepository) Create(ctx context.Context, name, email string) (int64, error) {
    result, err := r.db.ExecContext(ctx, "INSERT INTO users (name, email) VALUES (?, ?)", name, email)
    if err != nil {
        return 0, err
    }
    return result.LastInsertId()
}

func TestUserRepository_GetByID(t *testing.T) {
    // 创建 mock 数据库连接
    db, mock, err := sqlmock.New()
    if err != nil {
        t.Fatalf("创建 mock 失败: %v", err)
    }
    defer db.Close()

    repo := &UserRepository{db: db}

    t.Run("正常查询", func(t *testing.T) {
        // 设置期望的查询和结果
        rows := sqlmock.NewRows([]string{"name"}).AddRow("Alice")
        mock.ExpectQuery("SELECT name FROM users WHERE id = ?").
            WithArgs(1).
            WillReturnRows(rows)

        name, err := repo.GetByID(context.Background(), 1)
        if err != nil {
            t.Fatalf("查询失败: %v", err)
        }
        if name != "Alice" {
            t.Errorf("name = %s; want Alice", name)
        }
    })

    t.Run("用户不存在", func(t *testing.T) {
        mock.ExpectQuery("SELECT name FROM users WHERE id = ?").
            WithArgs(999).
            WillReturnError(sql.ErrNoRows)

        _, err := repo.GetByID(context.Background(), 999)
        if err != sql.ErrNoRows {
            t.Errorf("expected ErrNoRows, got %v", err)
        }
    })

    // 验证所有期望都已满足
    if err := mock.ExpectationsWereMet(); err != nil {
        t.Errorf("有未满足的期望: %v", err)
    }
}

func TestUserRepository_Create(t *testing.T) {
    db, mock, err := sqlmock.New()
    if err != nil {
        t.Fatalf("创建 mock 失败: %v", err)
    }
    defer db.Close()

    repo := &UserRepository{db: db}

    mock.ExpectExec("INSERT INTO users").
        WithArgs("Bob", "bob@example.com").
        WillReturnResult(sqlmock.NewResult(1, 1))

    id, err := repo.Create(context.Background(), "Bob", "bob@example.com")
    if err != nil {
        t.Fatalf("创建失败: %v", err)
    }
    if id != 1 {
        t.Errorf("id = %d; want 1", id)
    }

    if err := mock.ExpectationsWereMet(); err != nil {
        t.Errorf("有未满足的期望: %v", err)
    }
}
```

---

### 9. 测试覆盖率

#### 9.1 查看覆盖率

```bash
# 生成覆盖率统计
go test -coverprofile=coverage.out ./...

# 查看文本报告
go tool cover -func=coverage.out

# 输出示例：
# github.com/user/project/handler.go:15    HealthHandler    100.0%
# github.com/user/project/handler.go:22    UserHandler      85.7%
# github.com/user/project/db.go:10         QueryUser        100.0%
# total:                                    (statements)     92.3%

# 生成 HTML 报告（浏览器打开）
go tool cover -html=coverage.out -o coverage.html

# 只统计特定包
go test -coverprofile=coverage.out ./pkg/...

# 覆盖率模式
go test -coverprofile=coverage.out -covermode=count    # 计数模式
go test -coverprofile=coverage.out -covermode=atomic   # 原子计数（并发安全）
go test -coverprofile=coverage.out -covermode=set      # 只记录是否覆盖
```

#### 9.2 覆盖率最佳实践

```go
// 难以测试的代码：使用接口解耦

// 不好：直接依赖具体实现
type Service struct {
    db *sql.DB
}

// 好：依赖接口
type DB interface {
    QueryRowContext(ctx context.Context, query string, args ...any) *sql.Row
    ExecContext(ctx context.Context, query string, args ...any) (sql.Result, error)
}

type Service struct {
    db DB
}

// 测试时可以轻松 mock
func TestService(t *testing.T) {
    mockDB := &MockDB{}
    svc := &Service{db: mockDB}
    // ...
}
```

---

### 10. testify 测试框架

#### 10.1 assert 包

```go
package service

import (
    "testing"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestWithTestify(t *testing.T) {
    // assert 失败后继续执行
    assert := assert.New(t)

    assert.Equal(5, Add(2, 3), "2 + 3 应该等于 5")
    assert.NotZero(len("hello"))
    assert.Contains("hello world", "world")
    assert.Nil(nil)
    assert.NotNil("not nil")
    assert.True(1 < 2)
    assert.False(1 > 2)
    assert.Error(ErrSomething)
    assert.NoError(nil)

    // require 失败后立即停止
    req := require.New(t)
    req.NoError(criticalOperation(), "关键操作不能失败")
    req.Equal(42, answer)
}

func TestSliceAssertions(t *testing.T) {
    assert := assert.New(t)

    nums := []int{1, 2, 3, 4, 5}
    assert.Len(nums, 5)
    assert.Contains(nums, 3)
    assert.NotContains(nums, 6)
    assert.ElementsMatch([]int{1, 2, 3}, []int{3, 1, 2}) // 忽略顺序
}

func TestMapAssertions(t *testing.T) {
    assert := assert.New(t)

    m := map[string]int{"a": 1, "b": 2}
    assert.Equal(1, m["a"])
    assert.ContainsKey(m, "a")
    assert.NotContainsKey(m, "c")
}
```

#### 10.2 suite 包

```go
package service

import (
    "testing"

    "github.com/stretchr/testify/suite"
)

type ServiceTestSuite struct {
    suite.Suite
    service *Service
}

// SetupTest 在每个测试前运行
func (s *ServiceTestSuite) SetupTest() {
    s.service = NewService()
}

// TearDownTest 在每个测试后运行
func (s *ServiceTestSuite) TearDownTest() {
    s.service.Close()
}

func (s *ServiceTestSuite) TestCreate() {
    err := s.service.Create("test")
    s.NoError(err)
}

func (s *ServiceTestSuite) TestGet() {
    s.service.Create("test")
    item, err := s.service.Get("test")
    s.NoError(err)
    s.Equal("test", item.Name)
}

func (s *ServiceTestSuite) TestGetNotFound() {
    _, err := s.service.Get("nonexistent")
    s.Error(err)
}

// 运行测试套件
func TestServiceSuite(t *testing.T) {
    suite.Run(t, new(ServiceTestSuite))
}
```

---

### 11. 测试替身（Test Doubles）

#### 11.1 接口 Mock

```go
// 依赖接口
type MetricsCollector interface {
    IncrCounter(name string, value float64)
    RecordLatency(name string, duration time.Duration)
    SetGauge(name string, value float64)
}

// Mock 实现
type MockMetrics struct {
    Counters   map[string]float64
    Latencies  map[string]time.Duration
    Gauges     map[string]float64
}

func NewMockMetrics() *MockMetrics {
    return &MockMetrics{
        Counters:  make(map[string]float64),
        Latencies: make(map[string]time.Duration),
        Gauges:    make(map[string]float64),
    }
}

func (m *MockMetrics) IncrCounter(name string, value float64) {
    m.Counters[name] += value
}

func (m *MockMetrics) RecordLatency(name string, duration time.Duration) {
    m.Latencies[name] = duration
}

func (m *MockMetrics) SetGauge(name string, value float64) {
    m.Gauges[name] = value
}

// 测试中使用
func TestRequestHandler(t *testing.T) {
    mock := NewMockMetrics()
    handler := NewHandler(mock)

    handler.HandleRequest()

    assert.Equal(t, 1.0, mock.Counters["requests_total"])
    assert.Contains(t, mock.Latencies, "request_duration")
}
```

#### 11.2 使用函数作为 Mock

```go
// 函数类型实现接口
type CheckFunc func(ctx context.Context, host string) error

func (f CheckFunc) Check(ctx context.Context, host string) error {
    return f(ctx, host)
}

func TestHealthChecker(t *testing.T) {
    // 使用函数字面量创建 mock
    mockCheck := CheckFunc(func(ctx context.Context, host string) error {
        if host == "down.example.com" {
            return errors.New("connection refused")
        }
        return nil
    })

    checker := NewHealthChecker(mockCheck)

    results := checker.CheckAll(context.Background(), []string{
        "up.example.com",
        "down.example.com",
    })

    assert.Len(t, results, 2)
    assert.NoError(t, results[0].Error)
    assert.Error(t, results[1].Error)
}
```

---

## 💻 实战练习

### 练习 1：为 SRE 配置解析器编写完整测试

```go
package config

import (
    "os"
    "testing"
    "time"

    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

type MonitorConfig struct {
    Host       string        `json:"host"`
    Port       int           `json:"port"`
    Interval   time.Duration `json:"interval"`
    Threshold  float64       `json:"threshold"`
    Endpoints  []string      `json:"endpoints"`
    AlertEmail string        `json:"alert_email"`
}

func ParseConfig(data []byte) (*MonitorConfig, error) {
    // 实现略
    return nil, nil
}

func ValidateConfig(cfg *MonitorConfig) error {
    // 实现略
    return nil
}

// 任务：编写以下测试
func TestParseConfig(t *testing.T) {
    // 1. 测试正常 JSON 解析
    // 2. 测试无效 JSON
    // 3. 测试空输入
    // 4. 测试缺失字段使用默认值
}

func TestValidateConfig(t *testing.T) {
    // 1. 测试端口范围（1-65535）
    // 2. 测试 interval 最小值
    // 3. 测试 threshold 范围
    // 4. 测试 endpoints 非空
    // 5. 测试 email 格式
}

func TestParseConfigFromFile(t *testing.T) {
    // 使用 t.TempDir() 创建临时配置文件
    dir := t.TempDir()
    configPath := dir + "/config.json"
    // 写入测试配置并解析
}

func FuzzParseConfig(f *testing.F) {
    // 模糊测试
    f.Add([]byte(`{"host":"localhost","port":8080}`))
    f.Add([]byte(`{}`))
    f.Add([]byte(`invalid json`))

    f.Fuzz(func(t *testing.T, data []byte) {
        cfg, err := ParseConfig(data)
        if err != nil {
            return
        }
        // 不变量检查
        if cfg.Port < 0 || cfg.Port > 65535 {
            t.Errorf("port out of range: %d", cfg.Port)
        }
    })
}
```

### 练习 2：为 HTTP API 编写集成测试

```go
package api

import (
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/stretchr/testify/assert"
)

// 任务：测试以下 API 端点
// GET  /health          → 200 {"status":"ok"}
// GET  /api/v1/users    → 200 [用户列表]
// POST /api/v1/users    → 201 创建用户
// GET  /api/v1/users/:id → 200 用户详情
// PUT  /api/v1/users/:id → 200 更新用户
// DELETE /api/v1/users/:id → 204 删除用户

func TestHealthEndpoint(t *testing.T) {
    // 使用 httptest 测试
}

func TestUserCRUD(t *testing.T) {
    // 测试完整的 CRUD 流程
    // 1. 创建用户
    // 2. 获取用户
    // 3. 更新用户
    // 4. 删除用户
    // 5. 确认删除
}

func TestUserErrors(t *testing.T) {
    // 测试错误场景
    // 1. 获取不存在的用户 → 404
    // 2. 创建无效用户 → 400
    // 3. 更新不存在的用户 → 404
}
```

### 练习 3：基准测试优化

```go
package cache

import "testing"

// 当前实现（慢）
type SlowCache struct {
    data map[string]string
}

func (c *SlowCache) Get(key string) (string, bool) {
    // 存在性能问题，通过基准测试发现
    for k, v := range c.data {
        if k == key {
            return v, true
        }
    }
    return "", false
}

// 任务：
// 1. 为 SlowCache.Get 编写基准测试
// 2. 使用 go test -bench=. -benchmem 分析性能
// 3. 优化为 O(1) 查找
// 4. 对比优化前后的基准测试结果

func BenchmarkSlowCacheGet(b *testing.B) {
    // 实现基准测试
}

func BenchmarkFastCacheGet(b *testing.B) {
    // 优化版本的基准测试
}
```

---

## 🎯 面试题精选

### 1. Go 的表驱动测试是什么？为什么推荐使用？

**参考答案：**
表驱动测试是将测试用例组织在一个切片中，每个元素包含输入和期望输出，然后循环执行。推荐原因：
- 添加新用例只需增加一行数据
- 测试逻辑与数据分离，更清晰
- 容易覆盖边界情况
- Go 社区标准模式，便于团队协作
- 子测试命名清晰，失败时容易定位

### 2. t.Fatal 和 t.Error 的区别？

**参考答案：**
- `t.Error` 标记测试失败但继续执行后续代码
- `t.Fatal` 标记测试失败并立即停止当前测试函数（调用 `t.FailNow()`）
- 场景：`t.Fatal` 用于必须满足的前置条件（如数据库连接），失败后继续执行无意义
- `t.Error` 用于检查多个独立条件，希望一次运行发现所有问题

### 3. 基准测试中 b.N 是如何确定的？

**参考答案：**
Go 测试框架自动调整 b.N 以获得稳定的测量结果。初始值较小（如 1），如果运行时间不够长（默认 1 秒），会增加 b.N 重新运行，直到测量时间足够长以获得可靠的统计数据。用户不能直接设置 b.N，但可以用 `-benchtime` 控制最小运行时间或固定迭代次数。

### 4. 如何测试并发代码？

**参考答案：**
- 使用 `t.Parallel()` 并行运行独立测试
- 使用 `-race` 标志检测数据竞争：`go test -race`
- 使用 `sync.WaitGroup` 等待并发操作完成
- 使用 channel 进行同步
- 使用 `atomic` 包进行并发安全的计数
- 基准测试使用 `b.RunParallel()` 测试并发性能

### 5. httptest 包的主要用途是什么？

**参考答案：**
`httptest` 提供了两个主要工具：
- `httptest.NewRequest` 和 `httptest.NewRecorder`：直接测试 HTTP Handler，不需要启动真实服务器
- `httptest.NewServer`：创建一个临时 HTTP 服务器，用于测试 HTTP 客户端代码
优势：测试速度快、不占用端口、可精确控制响应、易于模拟错误场景。

### 6. 什么是模糊测试？Go 如何支持？

**参考答案：**
模糊测试自动生成随机输入来发现代码中的 bug、崩溃和安全漏洞。Go 1.18 原生支持：
- 使用 `f.Add()` 添加种子语料库
- 使用 `f.Fuzz()` 定义模糊测试逻辑
- Go 会自动变异种子语料生成新输入
- 发现的失败用例保存在 `testdata/fuzz/` 目录
- 适合测试解析器、验证器、编解码器等

### 7. 如何达到 80% 测试覆盖率？

**参考答案：**
- 使用 `go test -coverprofile` 生成覆盖率报告
- 用 `go tool cover -html` 可视化未覆盖的代码
- 重点覆盖：错误处理路径、边界条件、核心业务逻辑
- 使用接口解耦外部依赖（数据库、网络），便于 mock
- 不必追求 100%，关注关键路径
- 将覆盖率检查集成到 CI 流程

### 8. TestMain 的注意事项？

**参考答案：**
- 每个包只能有一个 TestMain
- 必须调用 `m.Run()` 执行测试
- 使用 `os.Exit(m.Run())` 退出
- `defer` 在 `os.Exit` 前不会执行，清理代码需要在 `os.Exit` 前手动调用
- 适用于全局初始化（测试数据库、Redis 等）
- 过度使用 TestMain 会降低测试隔离性

### 9. assert 和 require 的区别？

**参考答案：**
`testify/assert` 和 `testify/require` 提供相同的断言方法，区别在于：
- `assert` 失败后继续执行（类似 `t.Error`）
- `require` 失败后立即停止（类似 `t.Fatal`）
使用场景：`require` 用于前置条件（如创建资源），`require` 失败后继续执行会导致 panic；`assert` 用于独立的检查点。

### 10. 如何 mock 数据库操作？

**参考答案：**
- 使用 `go-sqlmock` 包 mock `database/sql` 接口
- 定义期望的 SQL 查询和返回结果
- 验证所有期望是否满足
- 替代方案：使用接口抽象数据库层，测试时注入 mock 实现
- 推荐分层架构：Handler → Service → Repository，Repository 层 mock 数据库

---

## 📚 深入阅读

- [Go 官方文档：testing 包](https://pkg.go.dev/testing)
- [Go Blog：Using Subtests and Sub-benchmarks](https://go.dev/blog/subtests)
- [Go Blog：Fuzzing is Beta](https://go.dev/blog/fuzz-beta)
- [Go 官方文档：go test 命令](https://pkg.go.dev/cmd/go#hdr-Testing_functions)
- [testify 文档](https://pkg.go.dev/github.com/stretchr/testify)
- [go-sqlmock 文档](https://github.com/DATA-DOG/go-sqlmock)
- 《Go 语言实战》第 9 章：测试
- 《Learn Go with Tests》https://quii.gitbook.io/learn-go-with-tests/

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 `testing.T` 和 `testing.B` 的核心方法
- [ ] 能说明表驱动测试的优势和标准模式
- [ ] 能解释基准测试中 b.N 的自动调整机制
- [ ] 能说明 TestMain 的使用场景和注意事项

### 实操检查点
- [ ] 能编写表驱动测试并使用子测试组织
- [ ] 能使用 httptest 测试 HTTP Handler
- [ ] 能使用 sqlmock 测试数据库操作
- [ ] 能编写基准测试并分析 -benchmem 结果

### 能力验证标准
- [ ] 项目测试覆盖率达到 80% 以上
- [ ] 能使用模糊测试发现边界情况
- [ ] 能使用 testify 提高测试效率
