# Day 62: 并发编程（核心）

> 📅 日期：2026-05-02  
> 📖 学习主题：并发编程（核心）  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 62 的学习后，你应该掌握：
- 理解 并发编程（核心） 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. Goroutine — Go 的并发原语

#### 1.1 什么是 Goroutine？

Goroutine 是 Go 的轻量级线程，由 Go runtime 调度管理：

| 特性 | OS 线程 | Goroutine |
|------|---------|-----------|
| 大小 | 1-2 MB | 2 KB（动态增长） |
| 创建开销 | 慢（系统调用） | 快（~2μs） |
| 数量 | ~几千 | ~百万 |
| 调度 | OS 内核 | Go runtime（M:P:G 模型） |
| 切换 | 内核态 | 用户态 |

```go
package main

import (
    "fmt"
    "time"
)

func checkServer(name string) {
    fmt.Printf("Checking %s...\n", name)
    time.Sleep(1 * time.Second) // 模拟网络请求
    fmt.Printf("%s is UP\n", name)
}

func main() {
    servers := []string{"web-01", "web-02", "db-01", "cache-01"}

    // 串行执行（4 秒）
    // for _, s := range servers {
    //     checkServer(s)
    // }

    // 并发执行（~1 秒）
    for _, s := range servers {
        go checkServer(s) // 启动 goroutine
    }

    // 等待 goroutine 完成
    time.Sleep(2 * time.Second)
}
```

#### 1.2 WaitGroup — 等待多个 Goroutine

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

func main() {
    servers := []string{"web-01", "web-02", "db-01", "cache-01"}
    var wg sync.WaitGroup

    for _, s := range servers {
        wg.Add(1) // 增加计数
        go func(name string) {
            defer wg.Done() // 完成时减少计数
            checkServer(name)
        }(s)
    }

    wg.Wait() // 等待所有完成
    fmt.Println("All checks done!")
}

func checkServer(name string) {
    time.Sleep(1 * time.Second)
    fmt.Printf("%s checked\n", name)
}
```

### 2. Channel — Goroutine 间通信

> **Go 的并发哲学：不要通过共享内存来通信，而要通过通信来共享内存**

#### 2.1 基础 Channel

```go
package main

import "fmt"

func main() {
    // 创建 channel
    ch := make(chan string)

    // 发送
    go func() {
        ch <- "health check result"
    }()

    // 接收（阻塞直到有数据）
    result := <-ch
    fmt.Println(result)
}
```

#### 2.2 带缓冲的 Channel

```go
// 无缓冲（同步）
ch := make(chan int)       // 发送和接收必须配对

// 带缓冲（异步）
ch := make(chan int, 10)   // 最多存 10 个值不阻塞
ch <- 1
ch <- 2
// ... 前 10 个不会阻塞
```

#### 2.3 Worker Pool 模式（SRE 常用）

```go
package main

import (
    "fmt"
    "sync"
    "time"
)

func main() {
    servers := []string{}
    for i := 1; i <= 20; i++ {
        servers = append(servers, fmt.Sprintf("web-%02d", i))
    }

    // 工作通道
    jobs := make(chan string, len(servers))
    results := make(chan string, len(servers))

    // 启动 5 个 worker
    var wg sync.WaitGroup
    for w := 1; w <= 5; w++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for server := range jobs {
                time.Sleep(200 * time.Millisecond) // 模拟检查
                results <- fmt.Sprintf("[Worker %d] %s: OK", id, server)
            }
        }(w)
    }

    // 发送任务
    for _, s := range servers {
        jobs <- s
    }
    close(jobs) // 关闭通道，通知 worker 没有更多任务

    // 等待完成
    go func() {
        wg.Wait()
        close(results)
    }()

    // 收集结果
    for r := range results {
        fmt.Println(r)
    }
}
```

### 3. Select — 多路复用

```go
func main() {
    ch1 := make(chan string)
    ch2 := make(chan string)
    done := make(chan bool)

    go func() { ch1 <- "from ch1" }()
    go func() { ch2 <- "from ch2" }()

    for {
        select {
        case msg := <-ch1:
            fmt.Println(msg)
        case msg := <-ch2:
            fmt.Println(msg)
        case <-done:
            fmt.Println("Done!")
            return
        case <-time.After(5 * time.Second):
            fmt.Println("Timeout!")
            return
        }
    }
}
```

### 4. Sync — 互斥锁

```go
var (
    mu      sync.RWMutex
    metrics = make(map[string]float64)
)

func updateMetric(name string, value float64) {
    mu.Lock()
    defer mu.Unlock()
    metrics[name] = value
}

func getMetric(name string) float64 {
    mu.RLock()
    defer mu.RUnlock()
    return metrics[name]
}

func getSnapshot() map[string]float64 {
    mu.RLock()
    defer mu.RUnlock()
    snapshot := make(map[string]float64)
    for k, v := range metrics {
        snapshot[k] = v
    }
    return snapshot
}
```

### 5. SRE 实战：并发服务器巡检

```go
func inspectServers(servers []ServerConfig) []InspectionResult {
    var (
        mu      sync.Mutex
        results []InspectionResult
        wg      sync.WaitGroup
    )

    // 限制并发数
    sem := make(chan struct{}, 10)

    for _, srv := range servers {
        wg.Add(1)
        go func(s ServerConfig) {
            defer wg.Done()
            sem <- struct{}{}        // 获取信号量
            defer func() { <-sem }() // 释放信号量

            res := inspectSingle(s)
            mu.Lock()
            results = append(results, res)
            mu.Unlock()
        }(srv)
    }

    wg.Wait()
    return results
}
```

### 6. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| goroutine 泄漏 | channel 无人接收 | 确保有消费方，或用 context 取消 |
| deadlock | 无缓冲 channel 发送/接收不配对 | 检查 channel 操作逻辑 |
| 数据竞争 | 多个 goroutine 写同一变量 | 用 mutex 或 channel |
| panic: send on closed channel | 向已关闭的 channel 发送 | 确保发送方负责关闭 |


---

## 💻 实战练习

### 练习 1：主机监控脚本

```python
#!/usr/bin/env python3
import psutil, json, datetime

def check_system():
    report = {{
        "timestamp": datetime.datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {{
            "total_gb": round(psutil.virtual_memory().total / 1e9, 2),
            "used_percent": psutil.virtual_memory().percent
        }},
        "disk": {{}},
    }}
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            report["disk"][part.mountpoint] = {{
                "total_gb": round(usage.total / 1e9, 2),
                "used_percent": usage.percent
            }}
        except PermissionError:
            pass
    return report

data = check_system()
print(json.dumps(data, indent=2))

# 告警
if data["cpu_percent"] > 80:
    print("ALERT: High CPU usage!")
if data["memory"]["used_percent"] > 90:
    print("ALERT: High memory usage!")
```

### 练习 2：日志分析工具

```python
import re
from collections import Counter

def analyze_nginx_log(log_file):
    pattern = r'(\S+) \S+ \S+ \[(.+?)\] "(\S+)" (\d+)'
    ips = Counter()
    status_codes = Counter()
    with open(log_file) as f:
        for line in f:
            m = re.match(pattern, line)
            if m:
                ips[m.group(1)] += 1
                status_codes[m.group(4)] += 1
    print("Top 10 IPs:", ips.most_common(10))
    print("Status codes:", dict(status_codes))

analyze_nginx_log("/var/log/nginx/access.log")
```


---

## 📚 最新优质资源

### 官方文档
- [Ubuntu 22.04 LTS 官方文档](https://ubuntu.com/documentation)
- [Linux FHS 标准 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/)
- [Bash 官方手册](https://www.gnu.org/software/bash/manual/)

### 推荐教程
- [MIT The Missing Semester](https://missing.csail.mit.edu/) - 工程师必学但学校不教的技能
- [Linux Journey](https://linuxjourney.com/) - 免费的 Linux 学习路径
- [Ryan's Tutorials - Linux](https://ryanstutorials.net/linuxtutorial/) - 入门到进阶
- [Linux Command Library](https://linuxcommand.org/) - 命令行入门

### 视频课程
- [Bilibili: 鸟哥的Linux私房菜（基础篇）](https://www.bilibili.com/video/BV1Vt411X7y6/)
- [YouTube: NetworkChuck - Linux Basics](https://www.youtube.com/playlist?list=PLI9KFC2-DCX-6LVEU2c2XBGWckzVqKS6j)
- [YouTube: DevOps Journey - Linux for DevOps](https://www.youtube.com/playlist?list=PL2_OBreMn7FqZkvLWn1Br7W1v5E5XKJyI)

### 实战练习平台
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) - 史上最好的 Linux 入门练习
- [KodeKloud Engineer](https://kodekloud.com) - 交互式 K8s 和 DevOps 练习
- [Play with Docker](https://play.docker.com/) - 免费 Docker 练习环境
- [Learn Linux TV](https://www.learnlinux.tv/) - 视频 + 实战

### SRE 相关资源
- [Google SRE Books](https://sre.google/sre-book/table-of-contents/)
- [Linux Performance](http://www.brendangregg.com/linuxperf.html) - Brendan Gregg
- [Ops School](http://www.ops-school.org/) - 运维工程师学习路径


---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| 问题描述 | 如何解决 |

### 延伸思考

- 思考 1：...
- 思考 2：...

---

## ✅ 完成检查

- [ ] 理解核心概念（能用自己的话解释）
- [ ] 完成所有基础命令练习
- [ ] 完成实战场景练习
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记
- [ ] 理解了命令背后的原理

---

*由 SRE 学习计划自动生成 | 2026-05-02 15:29:03*  
*Generated by Hermes Agent with review*
