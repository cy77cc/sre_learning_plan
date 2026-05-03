# Day 64: Go CLI 工具开发

> 📅 日期：2026-05-03
> 📖 学习主题：Go CLI 工具开发 — Cobra 框架、Viper 配置、美化输出、跨平台编译
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 58 (Go 基础语法), Day 59 (函数与错误处理), Day 61 (接口与组合), Day 63 (标准库与网络编程)

---

## 🎯 学习目标

- 掌握 Cobra 框架构建多命令 CLI 工具
- 熟练使用 Viper 管理多来源配置（文件、环境变量、命令行参数）
- 了解 pterm 库美化终端输出（表格、进度条、颜色）
- 掌握 Go 交叉编译和打包发布流程
- 能独立开发一个生产级 SRE CLI 工具

---

## 📖 核心知识点

### 1. 为什么选择 Cobra

Cobra 是 Go 生态中最流行的 CLI 框架，被 kubectl、helm、docker CLI、gh 等知名工具采用：

```
Cobra 生态：

┌─────────────────────────────────────────────────────────┐
│                        Cobra                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Command（命令）                                     │  │
│  │ - Use: 命令名                                       │  │
│  │ - Short/Long: 描述                                  │  │
│  │ - RunE: 执行逻辑                                    │  │
│  │ - Args: 参数验证                                    │  │
│  │ - Flags: 参数绑定                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  使用 Cobra 的项目：                                      │
│  - kubectl (Kubernetes CLI)                              │
│  - helm (Kubernetes 包管理)                               │
│  - gh (GitHub CLI)                                       │
│  - docker (Docker CLI)                                   │
│  - hugo (静态站点生成器)                                   │
│  - terraform (部分)                                      │
└─────────────────────────────────────────────────────────┘
```

---

### 2. Cobra 项目结构

#### 2.1 初始化项目

```bash
# 创建项目
mkdir sre-tool && cd sre-tool
go mod init github.com/yourname/sre-tool

# 安装 cobra-cli 工具
go install github.com/spf13/cobra-cli@latest

# 初始化 cobra 项目
cobra-cli init

# 添加子命令
cobra-cli add check
cobra-cli add version
cobra-cli add config
```

标准 Cobra 项目结构：

```
sre-tool/
├── cmd/
│   ├── root.go          # 根命令
│   ├── check.go         # check 子命令
│   ├── version.go       # version 子命令
│   └── config.go        # config 子命令
├── internal/
│   ├── checker/         # 业务逻辑
│   │   └── checker.go
│   └── config/          # 配置管理
│       └── config.go
├── main.go              # 入口
├── go.mod
└── go.sum
```

#### 2.2 根命令 (root.go)

```go
package cmd

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var cfgFile string

// rootCmd 是基础命令
var rootCmd = &cobra.Command{
    Use:   "sre-tool",
    Short: "SRE 工具集 — 服务器健康检查与监控",
    Long: `SRE Tool 是一个用于服务器健康检查、指标采集和告警管理的 CLI 工具。

支持功能：
  - 并发健康检查多个服务器
  - 采集系统和应用指标
  - 管理告警规则
  - 生成巡检报告`,
    // PersistentPreRun 在所有子命令执行前运行
    PersistentPreRun: func(cmd *cobra.Command, args []string) {
        // 初始化配置
        initConfig()
    },
}

// Execute 是入口点
func Execute() {
    if err := rootCmd.Execute(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}

func init() {
    // 全局参数（对所有子命令生效）
    rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "配置文件路径 (默认: $HOME/.sre-tool.yaml)")
    rootCmd.PersistentFlags().BoolP("verbose", "v", false, "详细输出")
    rootCmd.PersistentFlags().StringP("output", "o", "text", "输出格式 (text|json|yaml)")

    // 绑定到 viper
    viper.BindPFlag("verbose", rootCmd.PersistentFlags().Lookup("verbose"))
    viper.BindPFlag("output", rootCmd.PersistentFlags().Lookup("output"))
}

func initConfig() {
    if cfgFile != "" {
        viper.SetConfigFile(cfgFile)
    } else {
        home, err := os.UserHomeDir()
        if err != nil {
            fmt.Fprintln(os.Stderr, err)
            os.Exit(1)
        }

        viper.AddConfigPath(home)
        viper.AddConfigPath(".")
        viper.SetConfigName(".sre-tool")
        viper.SetConfigType("yaml")
    }

    // 环境变量支持
    viper.SetEnvPrefix("SRE")
    viper.AutomaticEnv()

    // 读取配置文件（如果存在）
    if err := viper.ReadInConfig(); err == nil {
        if viper.GetBool("verbose") {
            fmt.Fprintln(os.Stderr, "Using config file:", viper.ConfigFileUsed())
        }
    }
}
```

#### 2.3 main.go 入口

```go
package main

import "github.com/yourname/sre-tool/cmd"

func main() {
    cmd.Execute()
}
```

#### 2.4 子命令示例

```go
// cmd/version.go
package cmd

import (
    "fmt"
    "runtime"

    "github.com/spf13/cobra"
)

var (
    Version   = "dev"
    Commit    = "none"
    BuildDate = "unknown"
)

var versionCmd = &cobra.Command{
    Use:   "version",
    Short: "显示版本信息",
    Run: func(cmd *cobra.Command, args []string) {
        output, _ := cmd.Flags().GetString("output")
        if output == "json" {
            fmt.Printf(`{"version":"%s","commit":"%s","build_date":"%s","go":"%s"}`+"\n",
                Version, Commit, BuildDate, runtime.Version())
        } else {
            fmt.Printf("SRE Tool %s (commit: %s, built: %s, go: %s)\n",
                Version, Commit, BuildDate, runtime.Version())
        }
    },
}

func init() {
    rootCmd.AddCommand(versionCmd)
}
```

```go
// cmd/check.go
package cmd

import (
    "context"
    "fmt"
    "sync"
    "time"

    "github.com/spf13/cobra"
)

type CheckResult struct {
    Host    string        `json:"host"`
    Status  string        `json:"status"`
    Latency time.Duration `json:"latency"`
    Error   string        `json:"error,omitempty"`
}

var checkCmd = &cobra.Command{
    Use:   "check [hosts...]",
    Short: "检查服务器健康状态",
    Long: `并发检查指定服务器的健康状态。

示例:
  sre-tool check web-01 web-02 web-03
  sre-tool check --timeout 5s --parallel 10 db-01 db-02
  sre-tool check --file hosts.txt`,
    Args: cobra.MinimumNArgs(0),
    RunE: func(cmd *cobra.Command, args []string) error {
        timeout, _ := cmd.Flags().GetDuration("timeout")
        parallel, _ := cmd.Flags().GetInt("parallel")
        hostFile, _ := cmd.Flags().GetString("file")

        var hosts []string
        if hostFile != "" {
            // 从文件读取主机列表
            data, err := os.ReadFile(hostFile)
            if err != nil {
                return fmt.Errorf("reading host file: %w", err)
            }
            for _, line := range strings.Split(string(data), "\n") {
                line = strings.TrimSpace(line)
                if line != "" && !strings.HasPrefix(line, "#") {
                    hosts = append(hosts, line)
                }
            }
        }
        hosts = append(hosts, args...)

        if len(hosts) == 0 {
            return fmt.Errorf("no hosts specified")
        }

        return runHealthCheck(hosts, timeout, parallel)
    },
}

func init() {
    checkCmd.Flags().DurationP("timeout", "t", 5*time.Second, "检查超时时间")
    checkCmd.Flags().IntP("parallel", "p", 10, "并发检查数量")
    checkCmd.Flags().StringP("file", "f", "", "主机列表文件")
    rootCmd.AddCommand(checkCmd)
}

func runHealthCheck(hosts []string, timeout time.Duration, parallel int) error {
    ctx, cancel := context.WithTimeout(context.Background(), timeout*time.Duration(len(hosts)/parallel+1))
    defer cancel()

    jobs := make(chan string, len(hosts))
    results := make(chan CheckResult, len(hosts))

    // 启动 worker
    var wg sync.WaitGroup
    for i := 0; i < parallel; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for host := range jobs {
                results <- checkHost(ctx, host, timeout)
            }
        }()
    }

    // 分发任务
    for _, host := range hosts {
        jobs <- host
    }
    close(jobs)

    go func() {
        wg.Wait()
        close(results)
    }()

    // 输出结果
    for result := range results {
        status := "\033[32m✓ UP\033[0m"
        if result.Status != "ok" {
            status = "\033[31m✗ DOWN\033[0m"
        }
        fmt.Printf("  %s %-20s (latency: %v)\n", status, result.Host, result.Latency)
        if result.Error != "" {
            fmt.Printf("    Error: %s\n", result.Error)
        }
    }

    return nil
}

func checkHost(ctx context.Context, host string, timeout time.Duration) CheckResult {
    start := time.Now()
    // 简化：实际实现会进行 HTTP/TCP 检查
    time.Sleep(time.Duration(50+len(host)*10) * time.Millisecond)
    return CheckResult{
        Host:    host,
        Status:  "ok",
        Latency: time.Since(start),
    }
}
```

---

### 3. Cobra 高级特性

#### 3.1 参数验证

```go
package cmd

import (
    "fmt"

    "github.com/spf13/cobra"
)

var validateCmd = &cobra.Command{
    Use:   "validate",
    Short: "验证配置文件",
    // Args 验证参数
    Args: cobra.ExactArgs(1), // 精确 1 个参数
    // 其他验证器：
    // cobra.NoArgs()             — 不允许参数
    // cobra.MinimumNArgs(1)      — 最少 1 个
    // cobra.MaximumNArgs(3)      — 最多 3 个
    // cobra.RangeArgs(1, 3)      — 1-3 个
    // cobra.ExactValidArgs(2)    — 精确 2 个且通过 ValidArgs 验证
    // cobra.ArbitraryArgs        — 任意参数
    RunE: func(cmd *cobra.Command, args []string) error {
        configFile := args[0]
        fmt.Printf("Validating %s...\n", configFile)
        // 验证逻辑
        return nil
    },
}

// 自定义参数验证
var deployCmd = &cobra.Command{
    Use:   "deploy [environment]",
    Short: "部署到指定环境",
    Args:  cobra.MatchAll(cobra.ExactArgs(1), cobra.OnlyValidArgs),
    ValidArgs: []string{"dev", "staging", "production"},
    RunE: func(cmd *cobra.Command, args []string) error {
        env := args[0]
        fmt.Printf("Deploying to %s...\n", env)
        return nil
    },
}

func init() {
    rootCmd.AddCommand(validateCmd)
    rootCmd.AddCommand(deployCmd)
}
```

#### 3.2 子命令分组

```go
package cmd

import (
    "github.com/spf13/cobra"
)

func init() {
    // 命令分组（Go 1.20+ / cobra v1.7+）
    serverGroup := &cobra.Group{
        ID:    "server",
        Title: "服务器管理:",
    }
    alertGroup := &cobra.Group{
        ID:    "alert",
        Title: "告警管理:",
    }

    rootCmd.AddGroup(serverGroup, alertGroup)

    // 将命令分配到组
    checkCmd.GroupID = "server"
    statusCmd.GroupID = "server"
    alertCmd.GroupID = "alert"
    notifyCmd.GroupID = "alert"

    rootCmd.AddCommand(checkCmd, statusCmd, alertCmd, notifyCmd)
}
```

#### 3.3 命令别名与建议

```go
var statusCmd = &cobra.Command{
    Use:     "status",
    Aliases: []string{"st", "stat"},
    Short:   "显示服务器状态",
    SuggestFor: []string{"info", "state"},
    // 当用户输入错误命令时，cobra 会基于 SuggestFor 给出建议
    RunE: func(cmd *cobra.Command, args []string) error {
        // ...
        return nil
    },
}
```

#### 3.4 钩子函数

```go
var rootCmd = &cobra.Command{
    Use: "sre-tool",

    // 执行顺序：PersistentPreRun → PreRun → Run → PostRun → PersistentPostRun

    PersistentPreRun: func(cmd *cobra.Command, args []string) {
        // 对所有子命令生效（初始化配置、日志等）
    },

    PreRun: func(cmd *cobra.Command, args []string) {
        // 仅对当前命令生效
    },

    RunE: func(cmd *cobra.Command, args []string) error {
        // 主逻辑
        return nil
    },

    PostRun: func(cmd *cobra.Command, args []string) {
        // 主逻辑之后执行（清理资源等）
    },

    PersistentPostRun: func(cmd *cobra.Command, args []string) {
        // 对所有子命令生效（关闭连接、输出统计等）
    },
}
```

---

### 4. Viper 配置管理

#### 4.1 多来源配置

```
Viper 配置优先级（从高到低）：

┌─────────────────────────────┐
│ 1. 显式 Set (viper.Set)     │  最高优先级
├─────────────────────────────┤
│ 2. 命令行参数 (flags)        │
├─────────────────────────────┤
│ 3. 环境变量                  │
├─────────────────────────────┤
│ 4. 配置文件                  │
├─────────────────────────────┤
│ 5. Key/Value 存储 (远程)     │
├─────────────────────────────┤
│ 6. 默认值                    │  最低优先级
└─────────────────────────────┘
```

```go
package config

import (
    "fmt"
    "strings"
    "time"

    "github.com/spf13/viper"
)

type Config struct {
    Server   ServerConfig   `mapstructure:"server"`
    Database DatabaseConfig `mapstructure:"database"`
    Logging  LoggingConfig  `mapstructure:"logging"`
    Alerts   AlertsConfig   `mapstructure:"alerts"`
}

type ServerConfig struct {
    Host         string        `mapstructure:"host"`
    Port         int           `mapstructure:"port"`
    ReadTimeout  time.Duration `mapstructure:"read_timeout"`
    WriteTimeout time.Duration `mapstructure:"write_timeout"`
}

type DatabaseConfig struct {
    Host     string `mapstructure:"host"`
    Port     int    `mapstructure:"port"`
    Name     string `mapstructure:"name"`
    User     string `mapstructure:"user"`
    Password string `mapstructure:"password"`
    SSLMode  string `mapstructure:"ssl_mode"`
}

type LoggingConfig struct {
    Level  string `mapstructure:"level"`
    Format string `mapstructure:"format"`
    Output string `mapstructure:"output"`
}

type AlertsConfig struct {
    SlackWebhook  string `mapstructure:"slack_webhook"`
    PagerDutyKey  string `mapstructure:"pagerduty_key"`
    EmailSMTPHost string `mapstructure:"email_smtp_host"`
}

func LoadConfig() (*Config, error) {
    // 设置默认值
    setDefaults()

    // 配置环境变量
    viper.SetEnvPrefix("SRE")
    viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
    viper.AutomaticEnv()

    // 读取配置文件
    viper.SetConfigName("sre-tool")
    viper.SetConfigType("yaml")
    viper.AddConfigPath(".")
    viper.AddConfigPath("$HOME/.config/sre-tool")
    viper.AddConfigPath("/etc/sre-tool")

    if err := viper.ReadInConfig(); err != nil {
        if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
            return nil, fmt.Errorf("reading config: %w", err)
        }
    }

    var config Config
    if err := viper.Unmarshal(&config); err != nil {
        return nil, fmt.Errorf("unmarshaling config: %w", err)
    }

    return &config, nil
}

func setDefaults() {
    // Server defaults
    viper.SetDefault("server.host", "0.0.0.0")
    viper.SetDefault("server.port", 8080)
    viper.SetDefault("server.read_timeout", "10s")
    viper.SetDefault("server.write_timeout", "30s")

    // Database defaults
    viper.SetDefault("database.host", "localhost")
    viper.SetDefault("database.port", 5432)
    viper.SetDefault("database.ssl_mode", "disable")

    // Logging defaults
    viper.SetDefault("logging.level", "info")
    viper.SetDefault("logging.format", "json")
    viper.SetDefault("logging.output", "stdout")
}
```

#### 4.2 配置文件示例

```yaml
# sre-tool.yaml
server:
  host: "0.0.0.0"
  port: 8080
  read_timeout: "10s"
  write_timeout: "30s"

database:
  host: "localhost"
  port: 5432
  name: "sre_tool"
  user: "sre"
  password: "${DB_PASSWORD}"  # 可从环境变量替换
  ssl_mode: "require"

logging:
  level: "info"
  format: "json"
  output: "stdout"

alerts:
  slack_webhook: "https://hooks.slack.com/services/xxx"
  pagerduty_key: "pd-key-xxx"
  email_smtp_host: "smtp.company.com"
```

#### 4.3 配置热重载

```go
package config

import (
    "fmt"
    "log/slog"

    "github.com/fsnotify/fsnotify"
    "github.com/spf13/viper"
)

func WatchConfig(logger *slog.Logger) {
    viper.WatchConfig()
    viper.OnConfigChange(func(e fsnotify.Event) {
        logger.Info("config file changed", "file", e.Name)

        var config Config
        if err := viper.Unmarshal(&config); err != nil {
            logger.Error("failed to reload config", "error", err)
            return
        }

        // 通知各组件配置变更
        logger.Info("config reloaded successfully",
            "server_port", config.Server.Port,
            "log_level", config.Logging.Level,
        )
    })
}
```

---

### 5. pterm 美化终端输出

#### 5.1 基础用法

```go
package main

import (
    "time"

    "github.com/pterm/pterm"
)

func main() {
    // 带颜色的标题
    pterm.DefaultSection.WithLevel(0).Println("SRE Tool v1.0")
    pterm.DefaultSection.WithLevel(1).Println("System Status")

    // 信息/成功/警告/错误消息
    pterm.Info.Println("Starting health check...")
    pterm.Success.Println("All checks passed")
    pterm.Warning.Println("High memory usage detected")
    pterm.Error.Println("Connection to db-01 failed")

    // 带前缀的打印
    pterm.Println()
    pterm.Info.WithPrefix(pterm.Prefix{
        Text:  "CHECK",
        Style: pterm.NewStyle(pterm.FgCyan),
    }).Println("Checking web-01...")

    // 自定义颜色文本
    pterm.Println(pterm.Green("OK") + " " + pterm.Red("FAIL") + " " + pterm.Yellow("WARN"))

    // 加粗/斜体
    pterm.Println(pterm.Bold.Sprint("Bold text"))
    pterm.Println(pterm.Italic.Sprint("Italic text"))

    // Box 文本框
    pterm.DefaultBox.
        WithTitle("Server Status").
        WithTitleTopCenter().
        Println("web-01: UP\ndb-01: UP\ncache-01: DOWN")
}
```

#### 5.2 表格输出

```go
package main

import (
    "github.com/pterm/pterm"
)

func main() {
    // 基础表格
    tableData := pterm.TableData{
        {"Host", "Status", "CPU", "Memory", "Disk"},
        {"web-01", pterm.Green("UP"), "45%", "72%", "38%"},
        {"web-02", pterm.Green("UP"), "62%", "81%", "45%"},
        {"db-01", pterm.Green("UP"), "78%", "65%", "52%"},
        {"cache-01", pterm.Red("DOWN"), "-", "-", "-"},
        {"worker-01", pterm.Yellow("WARN"), "92%", "88%", "67%"},
    }

    pterm.DefaultTable.
        WithHasHeader().
        WithRowSeparator("-").
        WithSeparator("  |  ").
        WithBoxed().
        WithData(tableData).
        Render()

    // 紧凑表格
    pterm.DefaultTable.
        WithHasHeader().
        WithData(pterm.TableData{
            {"Service", "Port", "Status"},
            {"nginx", "80", "active"},
            {"postgres", "5432", "active"},
            {"redis", "6379", "active"},
        }).
        Render()
}
```

#### 5.3 进度条

```go
package main

import (
    "time"

    "github.com/pterm/pterm"
)

func main() {
    // 进度条
    pterm.DefaultSection.Println("Checking Servers")

    // 方式 1：简单进度条
   progressbar, _ := pterm.DefaultProgressbar.
        WithTotal(10).
        WithTitle("Health Check").
        Start()

    for i := 0; i < 10; i++ {
        time.Sleep(200 * time.Millisecond)
        progressbar.Increment()
    }
    progressbar.Stop()

    // 方式 2：带详情的进度条
    pterm.Println()
    multi := pterm.DefaultMultiPrinter
    multi.Start()

    bars := make([]*pterm.ProgressbarPrinter, 3)
    titles := []string{"Web Servers", "Databases", "Cache Servers"}
    totals := []int{5, 3, 2}

    for i := range bars {
        bars[i], _ = pterm.DefaultProgressbar.
            WithTotal(totals[i]).
            WithWriter(multi.NewWriter()).
            WithTitle(titles[i]).
            Start()
    }

    // 模拟并发检查
    done := make(chan bool)
    for i := range bars {
        go func(idx int) {
            for j := 0; j < totals[idx]; j++ {
                time.Sleep(time.Duration(200+idx*100) * time.Millisecond)
                bars[idx].Increment()
            }
            done <- true
        }(i)
    }

    for range bars {
        <-done
    }
    multi.Stop()
}
```

#### 5.4 Spinner (加载动画)

```go
package main

import (
    "time"

    "github.com/pterm/pterm"
)

func main() {
    // Spinner 加载动画
    spinner, _ := pterm.DefaultSpinner.
        WithText("Connecting to database...").
        Start()

    time.Sleep(2 * time.Second)

    // 更新文本
    spinner.UpdateText("Loading configuration...")
    time.Sleep(1 * time.Second)

    spinner.UpdateText("Starting server...")
    time.Sleep(1 * time.Second)

    // 成功
    spinner.Success("Server started successfully on :8080")

    // 失败示例
    spinner2, _ := pterm.DefaultSpinner.
        WithText("Connecting to cache...").
        Start()

    time.Sleep(1 * time.Second)
    spinner2.Fail("Failed to connect to cache at redis://localhost:6379")
}
```

#### 5.5 交互式输入

```go
package main

import (
    "fmt"

    "github.com/pterm/pterm"
)

func main() {
    // 文本输入
    name, _ := pterm.DefaultInteractiveTextInput.
        WithDefaultValue("web-01").
        WithDefaultText("Enter server name").
        Show()

    fmt.Printf("Server: %s\n", name)

    // 确认对话框
    confirm, _ := pterm.DefaultInteractiveConfirm.
        WithDefaultText("Are you sure you want to deploy to production?").
        WithDefaultValue(false).
        Show()

    if confirm {
        fmt.Println("Deploying...")
    } else {
        fmt.Println("Deployment cancelled")
    }

    // 多选
    options := []string{"web-01", "web-02", "db-01", "cache-01", "worker-01"}
    selected, _ := pterm.DefaultInteractiveMultiselect.
        WithOptions(options).
        WithDefaultText("Select servers to check").
        Show()

    fmt.Printf("Selected: %v\n", selected)

    // 单选
    env, _ := pterm.DefaultInteractiveSelect.
        WithOptions([]string{"development", "staging", "production"}).
        WithDefaultText("Select environment").
        Show()

    fmt.Printf("Environment: %s\n", env)
}
```

---

### 6. 实战：完整的 SRE CLI 工具

#### 6.1 项目结构

```
srectl/
├── cmd/
│   ├── root.go           # 根命令
│   ├── check.go          # 健康检查
│   ├── status.go         # 服务器状态
│   ├── deploy.go         # 部署
│   ├── config.go         # 配置管理
│   └── version.go        # 版本信息
├── internal/
│   ├── checker/
│   │   ├── checker.go    # 检查逻辑
│   │   └── checker_test.go
│   ├── deployer/
│   │   ├── deployer.go   # 部署逻辑
│   │   └── deployer_test.go
│   └── output/
│       ├── table.go      # 表格输出
│       └── json.go       # JSON 输出
├── main.go
├── go.mod
└── go.sum
```

#### 6.2 完整的 check 子命令

```go
// cmd/check.go
package cmd

import (
    "context"
    "encoding/json"
    "fmt"
    "os"
    "strings"
    "sync"
    "time"

    "github.com/pterm/pterm"
    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

type CheckOptions struct {
    Hosts    []string
    Timeout  time.Duration
    Parallel int
    Output   string
    File     string
}

type HostResult struct {
    Host    string        `json:"host"`
    Status  string        `json:"status"`
    Latency time.Duration `json:"latency"`
    Details string        `json:"details,omitempty"`
    Error   string        `json:"error,omitempty"`
}

var checkOpts CheckOptions

var checkCmd = &cobra.Command{
    Use:   "check [hosts...]",
    Short: "并发检查服务器健康状态",
    Long: `并发检查指定服务器的健康状态。

支持多种检查方式：
  - HTTP 健康检查
  - TCP 端口检查
  - SSH 连接检查

示例:
  srectl check web-01 web-02 web-03
  srectl check --file hosts.txt --parallel 20
  srectl check --timeout 10s --output json db-01`,
    Args: cobra.MinimumNArgs(0),
    PreRun: func(cmd *cobra.Command, args []string) {
        // 合并主机列表
        if checkOpts.File != "" {
            data, err := os.ReadFile(checkOpts.File)
            if err != nil {
                pterm.Error.Printf("Failed to read host file: %v\n", err)
                os.Exit(1)
            }
            for _, line := range strings.Split(string(data), "\n") {
                line = strings.TrimSpace(line)
                if line != "" && !strings.HasPrefix(line, "#") {
                    checkOpts.Hosts = append(checkOpts.Hosts, line)
                }
            }
        }
        checkOpts.Hosts = append(checkOpts.Hosts, args...)
    },
    RunE: func(cmd *cobra.Command, args []string) error {
        if len(checkOpts.Hosts) == 0 {
            return fmt.Errorf("no hosts specified. Use positional args or --file flag")
        }

        checkOpts.Output = viper.GetString("output")
        return runCheck(checkOpts)
    },
}

func init() {
    checkCmd.Flags().DurationVarP(&checkOpts.Timeout, "timeout", "t", 5*time.Second, "检查超时时间")
    checkCmd.Flags().IntVarP(&checkOpts.Parallel, "parallel", "p", 10, "并发检查数量")
    checkCmd.Flags().StringVarP(&checkOpts.File, "file", "f", "", "主机列表文件（每行一个）")
    rootCmd.AddCommand(checkCmd)
}

func runCheck(opts CheckOptions) error {
    ctx, cancel := context.WithTimeout(context.Background(),
        opts.Timeout*time.Duration(len(opts.Hosts)/opts.Parallel+2))
    defer cancel()

    // 显示开始信息
    if opts.Output == "text" {
        pterm.DefaultSection.Printf("Checking %d hosts (parallel: %d, timeout: %v)\n",
            len(opts.Hosts), opts.Parallel, opts.Timeout)
    }

    // 创建进度条
    var progressbar *pterm.ProgressbarPrinter
    if opts.Output == "text" {
        progressbar, _ = pterm.DefaultProgressbar.
            WithTotal(len(opts.Hosts)).
            WithTitle("Checking").
            Start()
    }

    // 并发检查
    jobs := make(chan string, len(opts.Hosts))
    results := make(chan HostResult, len(opts.Hosts))

    var wg sync.WaitGroup
    for i := 0; i < opts.Parallel; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for host := range jobs {
                results <- checkHost(ctx, host, opts.Timeout)
            }
        }()
    }

    for _, host := range opts.Hosts {
        jobs <- host
    }
    close(jobs)

    go func() {
        wg.Wait()
        close(results)
    }()

    var allResults []HostResult
    for result := range results {
        allResults = append(allResults, result)
        if progressbar != nil {
            progressbar.Increment()
        }
    }

    // 输出结果
    return outputResults(allResults, opts.Output)
}

func checkHost(ctx context.Context, host string, timeout time.Duration) HostResult {
    start := time.Now()

    // 实际实现：这里简化为模拟
    select {
    case <-ctx.Done():
        return HostResult{
            Host:   host,
            Status: "timeout",
            Error:  ctx.Err().Error(),
        }
    default:
    }

    time.Sleep(time.Duration(50+len(host)%200) * time.Millisecond)

    return HostResult{
        Host:    host,
        Status:  "ok",
        Latency: time.Since(start),
    }
}

func outputResults(results []HostResult, format string) error {
    switch format {
    case "json":
        data, err := json.MarshalIndent(results, "", "  ")
        if err != nil {
            return err
        }
        fmt.Println(string(data))

    case "text":
        pterm.Println()
        pterm.DefaultSection.Println("Results")

        tableData := pterm.TableData{
            {"Host", "Status", "Latency", "Error"},
        }

        up, down := 0, 0
        for _, r := range results {
            statusStr := pterm.Green("UP")
            if r.Status != "ok" {
                statusStr = pterm.Red("DOWN")
                down++
            } else {
                up++
            }
            tableData = append(tableData, []string{
                r.Host, statusStr, r.Latency.Round(time.Millisecond).String(), r.Error,
            })
        }

        pterm.DefaultTable.
            WithHasHeader().
            WithSeparator("  |  ").
            WithData(tableData).
            Render()

        pterm.Println()
        summary := fmt.Sprintf("Summary: %s UP, %s DOWN, %d total",
            pterm.Green(fmt.Sprintf("%d", up)),
            pterm.Red(fmt.Sprintf("%d", down)),
            len(results))
        pterm.Info.Println(summary)
    }

    return nil
}
```

---

### 7. 跨平台编译与打包发布

#### 7.1 交叉编译

```bash
# Go 原生支持交叉编译，无需额外工具

# Linux amd64
GOOS=linux GOARCH=amd64 go build -o srectl-linux-amd64 .

# Linux arm64 (ARM 服务器)
GOOS=linux GOARCH=arm64 go build -o srectl-linux-arm64 .

# macOS (Intel)
GOOS=darwin GOARCH=amd64 go build -o srectl-darwin-amd64 .

# macOS (Apple Silicon)
GOOS=darwin GOARCH=arm64 go build -o srectl-darwin-arm64 .

# Windows
GOOS=windows GOARCH=amd64 go build -o srectl-windows-amd64.exe .

# 嵌入版本信息
go build -ldflags "\
  -X github.com/yourname/srectl/cmd.Version=$(git describe --tags --always) \
  -X github.com/yourname/srectl/cmd.Commit=$(git rev-parse --short HEAD) \
  -X github.com/yourname/srectl/cmd.BuildDate=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -o srectl .

# 压缩二进制（使用 UPX）
upx --best srectl
```

#### 7.2 Makefile

```makefile
# Makefile
APP_NAME := srectl
VERSION := $(shell git describe --tags --always --dirty)
COMMIT := $(shell git rev-parse --short HEAD)
BUILD_DATE := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS := -X github.com/yourname/srectl/cmd.Version=$(VERSION) \
           -X github.com/yourname/srectl/cmd.Commit=$(COMMIT) \
           -X github.com/yourname/srectl/cmd.BuildDate=$(BUILD_DATE)

.PHONY: build clean test lint

build:
	go build -ldflags "$(LDFLAGS)" -o bin/$(APP_NAME) .

build-all:
	GOOS=linux   GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(APP_NAME)-linux-amd64 .
	GOOS=linux   GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o bin/$(APP_NAME)-linux-arm64 .
	GOOS=darwin  GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(APP_NAME)-darwin-amd64 .
	GOOS=darwin  GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o bin/$(APP_NAME)-darwin-arm64 .
	GOOS=windows GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o bin/$(APP_NAME)-windows-amd64.exe .

test:
	go test -race -v ./...

lint:
	golangci-lint run ./...

clean:
	rm -rf bin/

install: build
	cp bin/$(APP_NAME) $(GOPATH)/bin/$(APP_NAME)
```

#### 7.3 GoReleaser 配置

```yaml
# .goreleaser.yaml
version: 2

project_name: srectl

before:
  hooks:
    - go mod tidy
    - go generate ./...

builds:
  - id: srectl
    main: .
    binary: srectl
    ldflags:
      - -s -w
      - -X github.com/yourname/srectl/cmd.Version={{.Version}}
      - -X github.com/yourname/srectl/cmd.Commit={{.ShortCommit}}
      - -X github.com/yourname/srectl/cmd.BuildDate={{.Date}}
    env:
      - CGO_ENABLED=0
    goos:
      - linux
      - darwin
      - windows
    goarch:
      - amd64
      - arm64
    ignore:
      - goos: windows
        goarch: arm64

archives:
  - id: default
    format: tar.gz
    name_template: "{{ .ProjectName }}_{{ .Version }}_{{ .Os }}_{{ .Arch }}"
    format_overrides:
      - goos: windows
        format: zip
    files:
      - README.md
      - LICENSE

checksum:
  name_template: "checksums.txt"

snapshot:
  name_template: "{{ incpatch .Version }}-next"

changelog:
  sort: asc
  filters:
    exclude:
      - "^docs:"
      - "^test:"
      - "^chore:"

brews:
  - repository:
      owner: yourname
      name: homebrew-tap
    directory: Formula
    homepage: "https://github.com/yourname/srectl"
    description: "SRE CLI tool for health checks and monitoring"
    license: "MIT"

release:
  github:
    owner: yourname
    name: srectl
  draft: false
  prerelease: auto
```

```bash
# 使用 GoReleaser 发布
# 测试构建
goreleaser release --snapshot --clean

# 正式发布（需要 git tag）
git tag v1.0.0
git push origin v1.0.0
goreleaser release --clean
```

#### 7.4 GitHub Actions CI/CD

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  goreleaser:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'

      - name: Run tests
        run: go test -race ./...

      - name: Run GoReleaser
        uses: goreleaser/goreleaser-action@v5
        with:
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

### 8. SRE 实战：Kubernetes 风格的 CLI 工具

```go
// cmd/get.go — 类似 kubectl get 的命令
package cmd

import (
    "encoding/json"
    "fmt"
    "os"
    "text/tabwriter"

    "github.com/pterm/pterm"
    "github.com/spf13/cobra"
)

var getCmd = &cobra.Command{
    Use:   "get [resource]",
    Short: "获取资源信息",
    Long: `获取指定资源的信息，类似 kubectl get。

支持的资源:
  - servers    : 服务器列表
  - alerts     : 活跃告警
  - metrics    : 指标数据
  - incidents  : 事件列表

示例:
  srectl get servers
  srectl get alerts --severity critical
  srectl get servers --label env=production
  srectl get servers -o json`,
    Args: cobra.ExactArgs(1),
    ValidArgs: []string{"servers", "alerts", "metrics", "incidents"},
    RunE: func(cmd *cobra.Command, args []string) error {
        resource := args[0]
        output, _ := cmd.Flags().GetString("output")
        labelSelector, _ := cmd.Flags().GetString("label")
        namespace, _ := cmd.Flags().GetString("namespace")

        return getResource(resource, output, labelSelector, namespace)
    },
}

func init() {
    getCmd.Flags().StringP("label", "l", "", "标签选择器 (key=value)")
    getCmd.Flags().StringP("namespace", "n", "default", "命名空间")
    rootCmd.AddCommand(getCmd)
}

func getResource(resource, output, labelSelector, namespace string) error {
    // 模拟数据
    type Resource struct {
        Name      string `json:"name"`
        Status    string `json:"status"`
        Age       string `json:"age"`
        Namespace string `json:"namespace"`
    }

    resources := map[string][]Resource{
        "servers": {
            {Name: "web-01", Status: "Running", Age: "5d", Namespace: "production"},
            {Name: "web-02", Status: "Running", Age: "5d", Namespace: "production"},
            {Name: "db-01", Status: "Running", Age: "30d", Namespace: "production"},
            {Name: "cache-01", Status: "Failed", Age: "2d", Namespace: "staging"},
        },
    }

    items, ok := resources[resource]
    if !ok {
        return fmt.Errorf("unknown resource: %s", resource)
    }

    // 过滤
    if namespace != "" {
        var filtered []Resource
        for _, item := range items {
            if item.Namespace == namespace {
                filtered = append(filtered, item)
            }
        }
        items = filtered
    }

    switch output {
    case "json":
        data, _ := json.MarshalIndent(items, "", "  ")
        fmt.Println(string(data))

    case "wide":
        w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
        fmt.Fprintln(w, "NAME\tSTATUS\tAGE\tNAMESPACE")
        for _, item := range items {
            fmt.Fprintf(w, "%s\t%s\t%s\t%s\n", item.Name, item.Status, item.Age, item.Namespace)
        }
        w.Flush()

    default:
        tableData := pterm.TableData{{"NAME", "STATUS", "AGE"}}
        for _, item := range items {
            statusStr := item.Status
            if item.Status == "Running" {
                statusStr = pterm.Green(item.Status)
            } else if item.Status == "Failed" {
                statusStr = pterm.Red(item.Status)
            }
            tableData = append(tableData, []string{item.Name, statusStr, item.Age})
        }

        pterm.DefaultTable.
            WithHasHeader().
            WithSeparator("  ").
            WithData(tableData).
            Render()
    }

    return nil
}
```

---

## 💻 实战练习

### 练习 1：构建一个简单的 CLI 计算器

使用 Cobra 构建一个支持 add/sub/mul/div 子命令的 CLI 计算器。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "fmt"
    "os"
    "strconv"

    "github.com/spf13/cobra"
)

func main() {
    rootCmd := &cobra.Command{
        Use:   "calc",
        Short: "Simple CLI calculator",
    }

    // 共享的参数验证
    validateArgs := func(cmd *cobra.Command, args []string) error {
        if len(args) != 2 {
            return fmt.Errorf("requires exactly 2 arguments, got %d", len(args))
        }
        for _, arg := range args {
            if _, err := strconv.ParseFloat(arg, 64); err != nil {
                return fmt.Errorf("invalid number: %s", arg)
            }
        }
        return nil
    }

    addCmd := &cobra.Command{
        Use:   "add [a] [b]",
        Short: "Add two numbers",
        Args:  validateArgs,
        RunE: func(cmd *cobra.Command, args []string) error {
            a, _ := strconv.ParseFloat(args[0], 64)
            b, _ := strconv.ParseFloat(args[1], 64)
            verbose, _ := cmd.Flags().GetBool("verbose")
            if verbose {
                fmt.Printf("%.2f + %.2f = %.2f\n", a, b, a+b)
            } else {
                fmt.Printf("%.2f\n", a+b)
            }
            return nil
        },
    }

    subCmd := &cobra.Command{
        Use:   "sub [a] [b]",
        Short: "Subtract two numbers",
        Args:  validateArgs,
        RunE: func(cmd *cobra.Command, args []string) error {
            a, _ := strconv.ParseFloat(args[0], 64)
            b, _ := strconv.ParseFloat(args[1], 64)
            fmt.Printf("%.2f\n", a-b)
            return nil
        },
    }

    mulCmd := &cobra.Command{
        Use:   "mul [a] [b]",
        Short: "Multiply two numbers",
        Args:  validateArgs,
        RunE: func(cmd *cobra.Command, args []string) error {
            a, _ := strconv.ParseFloat(args[0], 64)
            b, _ := strconv.ParseFloat(args[1], 64)
            fmt.Printf("%.2f\n", a*b)
            return nil
        },
    }

    divCmd := &cobra.Command{
        Use:   "div [a] [b]",
        Short: "Divide two numbers",
        Args:  validateArgs,
        RunE: func(cmd *cobra.Command, args []string) error {
            a, _ := strconv.ParseFloat(args[0], 64)
            b, _ := strconv.ParseFloat(args[1], 64)
            if b == 0 {
                return fmt.Errorf("division by zero")
            }
            fmt.Printf("%.2f\n", a/b)
            return nil
        },
    }

    addCmd.Flags().BoolP("verbose", "v", false, "Show operation")

    rootCmd.AddCommand(addCmd, subCmd, mulCmd, divCmd)

    if err := rootCmd.Execute(); err != nil {
        os.Exit(1)
    }
}
```
</details>

### 练习 2：使用 Viper 实现配置管理

创建一个支持配置文件、环境变量和命令行参数的配置管理工具。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "fmt"
    "os"
    "strings"

    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

type Config struct {
    Host   string `mapstructure:"host"`
    Port   int    `mapstructure:"port"`
    Debug  bool   `mapstructure:"debug"`
    DBHost string `mapstructure:"db_host"`
    DBPort int    `mapstructure:"db_port"`
}

func main() {
    var cfgFile string

    rootCmd := &cobra.Command{
        Use:   "config-app",
        Short: "Demo app with Viper config",
        Run: func(cmd *cobra.Command, args []string) {
            var config Config
            viper.Unmarshal(&config)

            fmt.Printf("Host: %s\n", config.Host)
            fmt.Printf("Port: %d\n", config.Port)
            fmt.Printf("Debug: %v\n", config.Debug)
            fmt.Printf("DB Host: %s\n", config.DBHost)
            fmt.Printf("DB Port: %d\n", config.DBPort)
            fmt.Printf("\nConfig file used: %s\n", viper.ConfigFileUsed())
        },
    }

    rootCmd.Flags().StringVar(&cfgFile, "config", "", "config file path")
    rootCmd.Flags().String("host", "0.0.0.0", "server host")
    rootCmd.Flags().Int("port", 8080, "server port")
    rootCmd.Flags().Bool("debug", false, "debug mode")

    viper.BindPFlag("host", rootCmd.Flags().Lookup("host"))
    viper.BindPFlag("port", rootCmd.Flags().Lookup("port"))
    viper.BindPFlag("debug", rootCmd.Flags().Lookup("debug"))

    cobra.OnInitialize(func() {
        if cfgFile != "" {
            viper.SetConfigFile(cfgFile)
        } else {
            viper.AddConfigPath(".")
            viper.AddConfigPath("$HOME/.config/app")
            viper.SetConfigName("config")
            viper.SetConfigType("yaml")
        }

        viper.SetEnvPrefix("APP")
        viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
        viper.AutomaticEnv()

        viper.SetDefault("host", "0.0.0.0")
        viper.SetDefault("port", 8080)
        viper.SetDefault("debug", false)
        viper.SetDefault("db_host", "localhost")
        viper.SetDefault("db_port", 5432)

        viper.ReadInConfig()
    })

    if err := rootCmd.Execute(); err != nil {
        os.Exit(1)
    }
}
```
</details>

### 练习 3：构建一个带美化输出的服务器巡检工具

使用 pterm 创建一个带表格、进度条和颜色输出的服务器巡检工具。

<details>
<summary>参考答案</summary>

```go
package main

import (
    "fmt"
    "math/rand"
    "time"

    "github.com/pterm/pterm"
)

type Server struct {
    Name     string
    Type     string
    CPU      float64
    Memory   float64
    Disk     float64
    Status   string
    Uptime   string
}

func main() {
    pterm.DefaultHeader.WithFullWidth().
        WithBackgroundStyle(pterm.NewStyle(pterm.BgDarkGray)).
        WithTextStyle(pterm.NewStyle(pterm.FgLightWhite)).
        Println("SRE Server Inspection Report")

    pterm.Println()
    pterm.Info.Printf("Generated at: %s\n", time.Now().Format("2006-01-02 15:04:05"))
    pterm.Println()

    servers := []Server{
        {"web-01", "Web", 45, 72, 38, "Healthy", "15d 4h"},
        {"web-02", "Web", 62, 81, 45, "Healthy", "15d 4h"},
        {"web-03", "Web", 92, 95, 67, "Warning", "15d 4h"},
        {"api-01", "API", 38, 55, 22, "Healthy", "30d 12h"},
        {"api-02", "API", 41, 58, 24, "Healthy", "30d 12h"},
        {"db-01", "Database", 78, 65, 52, "Healthy", "90d 6h"},
        {"db-02", "Database", 82, 71, 55, "Healthy", "90d 6h"},
        {"cache-01", "Cache", 25, 45, 10, "Healthy", "60d 2h"},
        {"cache-02", "Cache", 0, 0, 0, "Down", "0d 0h"},
    }

    // 模拟检查过程
    spinner, _ := pterm.DefaultSpinner.
        WithText("Running health checks...").
        Start()

    for i := range servers {
        time.Sleep(time.Duration(rand.Intn(200)+100) * time.Millisecond)
        spinner.UpdateText(fmt.Sprintf("Checking %s...", servers[i].Name))
    }
    spinner.Success("Health checks completed")
    pterm.Println()

    // 结果表格
    pterm.DefaultSection.Println("Server Status")

    tableData := pterm.TableData{
        {"Name", "Type", "CPU", "Memory", "Disk", "Status", "Uptime"},
    }

    healthy, warning, down := 0, 0, 0
    for _, s := range servers {
        statusStr := ""
        switch s.Status {
        case "Healthy":
            statusStr = pterm.Green("Healthy")
            healthy++
        case "Warning":
            statusStr = pterm.Yellow("Warning")
            warning++
        case "Down":
            statusStr = pterm.Red("Down")
            down++
        }

        tableData = append(tableData, []string{
            s.Name, s.Type,
            fmt.Sprintf("%.0f%%", s.CPU),
            fmt.Sprintf("%.0f%%", s.Memory),
            fmt.Sprintf("%.0f%%", s.Disk),
            statusStr, s.Uptime,
        })
    }

    pterm.DefaultTable.
        WithHasHeader().
        WithSeparator("  |  ").
        WithBoxed().
        WithData(tableData).
        Render()

    // 资源使用条形图
    pterm.Println()
    pterm.DefaultSection.Println("Resource Usage")

    for _, s := range servers {
        if s.Status == "Down" {
            continue
        }

        pterm.Printf("  %s:\n", s.Name)

        cpuColor := pterm.FgGreen
        if s.CPU > 80 {
            cpuColor = pterm.FgRed
        } else if s.CPU > 60 {
            cpuColor = pterm.FgYellow
        }

        bar, _ := pterm.Defaultprogressbar.
            WithTotal(100).
            WithCurrent(int(s.CPU)).
            WithTitle("    CPU").
            WithRemoveWhenDone().
            Start()
        bar.Stop()

        bar2, _ := pterm.Defaultprogressbar.
            WithTotal(100).
            WithCurrent(int(s.Memory)).
            WithTitle("    Memory").
            WithRemoveWhenDone().
            Start()
        bar2.Stop()

        _ = cpuColor
    }

    // 摘要
    pterm.Println()
    pterm.DefaultSection.Println("Summary")

    summaryData := pterm.TableData{
        {"Status", "Count"},
        {pterm.Green("Healthy"), fmt.Sprintf("%d", healthy)},
        {pterm.Yellow("Warning"), fmt.Sprintf("%d", warning)},
        {pterm.Red("Down"), fmt.Sprintf("%d", down)},
        {"Total", fmt.Sprintf("%d", len(servers))},
    }

    pterm.DefaultTable.
        WithHasHeader().
        WithSeparator("  |  ").
        WithData(summaryData).
        Render()

    // 告警信息
    if down > 0 {
        pterm.Println()
        pterm.Warning.Printf("%d server(s) DOWN - immediate attention required!\n", down)
    }
    if warning > 0 {
        pterm.Warning.Printf("%d server(s) in WARNING state\n", warning)
    }
}
```
</details>

---

## 🎯 面试题精选

### 1. Cobra 的命令执行顺序是怎样的？

**答：** Cobra 命令的钩子执行顺序：
1. `PersistentPreRun` (父命令) — 全局初始化
2. `PersistentPreRun` (当前命令) — 如果当前命令有自己的
3. `PreRun` — 命令级预处理
4. `Run` / `RunE` — 主逻辑
5. `PostRun` — 命令级后处理
6. `PersistentPostRun` (当前命令)
7. `PersistentPostRun` (父命令) — 全局清理

关键点：PersistentPreRun 会被子命令继承，但子命令定义了自己的 PersistentPreRun 会覆盖父命令的。

### 2. Viper 的配置优先级是什么？

**答：** 从高到低：
1. `viper.Set()` 显式设置
2. 命令行参数 (flag)
3. 环境变量
4. 配置文件
5. Key/Value 存储（Consul, etcd 等远程配置）
6. 默认值 (`viper.SetDefault()`)

### 3. 如何在 CLI 工具中实现 --help 的自定义格式？

**答：** 通过设置 cobra.Command 的以下字段：
- `UsageTemplate`: 自定义 usage 模板
- `Example`: 命令示例
- `Long`: 详细描述
- 或使用 `SetUsageFunc()` / `SetUsageTemplate()` 方法

### 4. Go 交叉编译的原理是什么？

**答：** Go 编译器是纯 Go 实现的自举编译器，通过设置 GOOS 和 GOARCH 环境变量改变编译目标：
- `CGO_ENABLED=0` 禁用 CGO（避免依赖目标系统的 C 库）
- 编译器生成目标平台的机器码
- 链接器生成目标平台格式的可执行文件（ELF/Mach-O/PE）

不需要交叉编译工具链，这是 Go 的一大优势。

### 5. 如何为 CLI 工具实现 Shell 自动补全？

**答：** Cobra 内置支持生成 bash/zsh/fish/powershell 补全脚本：
```go
rootCmd.GenBashCompletion(os.Stdout)   // bash
rootCmd.GenZshCompletion(os.Stdout)    // zsh
rootCmd.GenFishCompletion(os.Stdout, true) // fish
rootCmd.GenPowerShellCompletion(os.Stdout) // powershell
```
也可以添加 `completion` 子命令让用户自行生成。

### 6. 如何在 CLI 工具中处理敏感信息（密码、Token）？

**答：**
- 不要在命令行参数中传递敏感信息（会被 shell history 记录）
- 使用环境变量：`os.Getenv("DB_PASSWORD")`
- 使用交互式输入（密码不回显）：`golang.org/x/term.ReadPassword()`
- 使用配置文件（权限设置为 600）
- 使用 secret manager（Vault, AWS Secrets Manager）

### 7. GoReleaser 的作用是什么？它解决了什么问题？

**答：** GoReleaser 自动化了 Go 项目的发布流程：
- 交叉编译多平台二进制
- 生成校验和文件
- 创建 GitHub Release
- 推送到 Homebrew tap
- 生成 Docker 镜像
- 更新 changelog

解决了手动构建、打包、发布的繁琐流程，一条命令完成所有操作。

### 8. 如何测试 CLI 工具？

**答：** 常见方法：
- **单元测试**：直接调用 RunE 函数，捕获输出
- **命令测试**：使用 `cmd.SetArgs()` 设置参数，`cmd.Execute()` 执行
- **集成测试**：编译后使用 `exec.Command` 执行二进制
- **Golden files**：将预期输出保存为文件，与实际输出对比

Cobra 命令的可测试性设计：将业务逻辑提取到独立函数，RunE 只做参数解析和调用。

### 9. 如何实现 CLI 工具的插件机制？

**答：** 类似 kubectl 的插件机制：
- 约定：以 `srectl-` 开头的可执行文件自动成为插件
- 扫描 `$PATH` 中的 `srectl-*` 文件
- 子命令匹配不到时，查找对应的插件执行
- 插件通过环境变量和 stdin/stdout 与主程序通信

### 10. cobra 和 urfave/cli 的对比？

**答：**

| 特性 | Cobra | urfave/cli |
|------|-------|-----------|
| 生态 | kubectl, helm, docker | 较小 |
| 命令嵌套 | 多级子命令 | 有限 |
| 配置集成 | 与 Viper 深度集成 | 需要额外工作 |
| 自动生成 | 文档、shell 补全、man page | 有限 |
| 学习曲线 | 中等 | 低 |
| 代码生成 | cobra-cli 工具 | 无 |

Cobra 是事实标准，适合大型 CLI 工具；urfave/cli 适合简单场景。

---

## 📚 深入阅读

- [Cobra 官方文档](https://cobra.dev/) — 命令框架
- [Viper 官方文档](https://github.com/spf13/viper) — 配置管理
- [pterm 官方文档](https://pterm.sh/) — 终端美化
- [GoReleaser 文档](https://goreleaser.com/) — 发布自动化
- [Go CLI 工具最佳实践](https://github.com/charmbracelet/bubbletea) — TUI 框架
- [kubectl 源码](https://github.com/kubernetes/kubectl) — Cobra 大型项目参考
- [gh CLI 源码](https://github.com/cli/cli) — GitHub CLI 的 Cobra 实践

---

## ✅ 自检清单

- [ ] 能使用 Cobra 创建多级子命令的 CLI 工具
- [ ] 掌握 Cobra 的参数验证、别名、分组等高级特性
- [ ] 能使用 Viper 管理多来源配置（文件、环境变量、参数）
- [ ] 能使用 pterm 创建带颜色、表格、进度条的终端输出
- [ ] 掌握 Go 交叉编译和 GOOS/GOARCH 的使用
- [ ] 能使用 Makefile 或 GoReleaser 自动化构建和发布
- [ ] 理解 CLI 工具的测试策略
- [ ] 能独立开发一个生产级 SRE CLI 工具
