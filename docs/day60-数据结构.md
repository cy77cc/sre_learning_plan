# Day 60: 数据结构

> 📅 日期：2026-05-02  
> 📖 学习主题：数据结构  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 60 的学习后，你应该掌握：
- 理解 数据结构 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. Go 切片深入

#### 1.1 切片内部结构

切片是一个三字段结构体：
```go
type slice struct {
    array unsafe.Pointer  // 指向底层数组的指针
    len   int             // 当前长度
    cap   int             // 容量（从指针位置到数组末尾）
}
```

```go
package main

import "fmt"

func main() {
    // 创建切片
    s := []int{1, 2, 3, 4, 5}
    fmt.Printf("len=%d cap=%d %v\n", len(s), cap(s), s)

    // 切片共享底层数组
    s2 := s[1:3] // [2, 3]
    fmt.Printf("s2: len=%d cap=%d %v\n", len(s2), cap(s2), s2)

    // 修改 s2 会影响 s
    s2[0] = 200
    fmt.Println(s) // [1, 200, 3, 4, 5]

    // append 可能分配新数组
    s3 := append(s2, 300, 400, 500, 600)
    // cap(s2)=4, 追加 4 个元素后超出容量，分配新数组
    s3[0] = 999
    fmt.Println(s2) // [999, 3] — s2 和 s3 现在独立
}
```

#### 1.2 切片操作性能

```go
// 预分配容量（避免反复扩容）
data := make([]int, 0, 1000) // len=0, cap=1000
for i := 0; i < 1000; i++ {
    data = append(data, i)
}

// 不预分配（会反复分配+拷贝）
data := []int{}
for i := 0; i < 1000; i++ {
    data = append(data, i) // 触发 ~10 次扩容
}
```

### 2. Map 深入

#### 2.1 Map 原理

Go 的 map 基于哈希表实现：
```go
// 创建
m := make(map[string]int)
m["cpu"] = 85
m["mem"] = 72

// 安全访问
val, exists := m["disk"]
if !exists {
    fmt.Println("key not found")
}

// 遍历（注意：顺序不保证！）
for key, val := range m {
    fmt.Printf("%s: %d\n", key, val)
}

// 删除
delete(m, "cpu")

// 嵌套 map
servers := map[string]map[string]float64{
    "web-01": {"cpu": 45.2, "mem": 72.1},
    "db-01":  {"cpu": 88.5, "mem": 91.3},
}
```

**Map 注意事项**：
```
❌ map 不是并发安全的！
   多个 goroutine 同时读写会 panic: concurrent map writes

✅ 解决方案：
   1. sync.Map（读多写少）
   2. sync.RWMutex + 普通 map（通用）
   3. channel 传递数据
```

#### 2.2 sync.Map（并发安全）

```go
package main

import (
    "fmt"
    "sync"
)

func main() {
    var m sync.Map

    // 存储
    m.Store("web-01", map[string]int{"cpu": 45, "mem": 72})
    m.Store("web-02", map[string]int{"cpu": 38, "mem": 65})

    // 读取
    val, ok := m.Load("web-01")
    if ok {
        fmt.Printf("Found: %v\n", val)
    }

    // 遍历
    m.Range(func(key, value interface{}) bool {
        fmt.Printf("%s: %v\n", key, value)
        return true
    })

    // 删除
    m.Delete("web-02")
}
```

### 3. 结构体标签与 JSON 序列化

```go
package main

import (
    "encoding/json"
    "fmt"
)

type Server struct {
    ID        int               `json:"id"`
    Name      string            `json:"name"`
    IPAddress string            `json:"ip_address"`
    Port      int               `json:"port,omitempty"`
    Tags      []string          `json:"tags,omitempty"`
    Metadata  map[string]string `json:"metadata,omitempty"`
}

func main() {
    // 结构体 → JSON
    srv := Server{
        ID:        1,
        Name:      "web-01",
        IPAddress: "10.0.1.10",
        Tags:      []string{"production", "web"},
    }

    data, _ := json.MarshalIndent(srv, "", "  ")
    fmt.Println(string(data))
    // {
    //   "id": 1,
    //   "name": "web-01",
    //   "ip_address": "10.0.1.10",
    //   "tags": ["production", "web"]
    // }

    // JSON → 结构体
    var parsed Server
    json.Unmarshal(data, &parsed)
    fmt.Printf("%+v\n", parsed)
}
```

### 4. SRE 实战：用结构体表示监控配置

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
```

### 5. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 切片 append 后原数据变了 | 超出容量分配了新数组 | 检查 cap，用 copy 创建独立副本 |
| map 并发写 panic | 非线程安全 | 用 sync.RWMutex 或 sync.Map |
| JSON 序列化空字段 | 零值也会被序列化 | 用 `omitempty` 标签 |
| 结构体比较报错 | 含不可比较字段 | 用 reflect.DeepEqual 或逐字段比较 |


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

*由 SRE 学习计划自动生成 | 2026-05-02 15:05:12*  
*Generated by Hermes Agent with review*
