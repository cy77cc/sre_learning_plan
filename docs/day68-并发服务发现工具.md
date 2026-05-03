# Day 68: 并发服务发现工具

> 📅 日期：2026-05-03
> 📖 学习主题：服务发现原理、DNS/Consul/etcd 服务发现、健康检查、负载均衡策略、一致性哈希与完整实现
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 62 并发编程、Day 63 标准库与网络编程、Day 65 Context 与超时控制

## 🎯 学习目标

完成 Day 68 的学习后，你应该能够：
1. 理解服务发现的核心原理和架构模式
2. 实现基于 DNS、Consul、etcd 的服务发现
3. 实现健康检查机制（主动探测、被动通知）
4. 掌握负载均衡策略（轮询、加权、最少连接、一致性哈希）
5. 深入理解一致性哈希算法及其在分布式系统中的应用
6. 编写完整的并发服务发现工具

---

## 📖 核心知识点

### 1. 服务发现原理

#### 1.1 为什么需要服务发现？

在传统架构中，服务地址是静态配置的。在微服务和云原生架构中：

```
传统架构（静态配置）：
┌──────────┐     配置文件: db-host:3306     ┌──────────┐
│  应用 A   │ ──────────────────────────────→ │  MySQL   │
└──────────┘     固定 IP 地址                 └──────────┘

微服务架构（动态服务发现）：
┌──────────┐     查询服务地址               ┌──────────────┐
│  应用 A   │ ──────────────────────────→ │  服务注册中心  │
└──────────┘                               │  (Consul/etcd) │
     │                                      └───────┬────────┘
     │         获取服务实例列表                       │
     │◄──────────────────────────────────────────────┘
     │
     │     选择一个实例（负载均衡）
     ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  实例 1   │  │  实例 2   │  │  实例 3   │
└──────────┘  └──────────┘  └──────────┘
```

#### 1.2 服务发现模式

| 模式 | 方向 | 代表 | 适用场景 |
|------|------|------|----------|
| 客户端发现 | 客户端查询注册中心 | Eureka、Consul（SDK） | 客户端可修改 |
| 服务端发现 | 负载均衡器查询注册中心 | K8s Service、AWS ELB | 客户端不可修改 |
| DNS 发现 | 通过 DNS 解析 | CoreDNS、Consul DNS | 通用，兼容性好 |

#### 1.3 服务注册与发现流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    服务注册与发现流程                              │
│                                                                   │
│  1. 注册阶段：                                                    │
│  ┌──────────┐  Register   ┌──────────────┐                       │
│  │  服务实例  │ ──────────→ │  服务注册中心  │                       │
│  │ (Service) │  (host:port) │  (Registry)  │                       │
│  └──────────┘              └──────────────┘                       │
│                                                                   │
│  2. 健康检查：                                                    │
│  ┌──────────────┐  Health Check  ┌──────────┐                   │
│  │  服务注册中心  │ ──────────────→ │  服务实例  │                   │
│  └──────────────┘  (定期探测)      └──────────┘                   │
│                                                                   │
│  3. 发现阶段：                                                    │
│  ┌──────────┐  Discover    ┌──────────────┐                     │
│  │  客户端   │ ────────────→ │  服务注册中心  │                     │
│  └──────────┘               └──────────────┘                     │
│       │                                                           │
│       ▼                                                           │
│  获取实例列表 [instance1, instance2, instance3]                   │
│       │                                                           │
│       ▼                                                           │
│  负载均衡选择 → 调用目标实例                                       │
│                                                                   │
│  4. 注销阶段：                                                    │
│  ┌──────────┐  Deregister  ┌──────────────┐                     │
│  │  服务实例  │ ────────────→ │  服务注册中心  │                     │
│  └──────────┘ (优雅关闭)     └──────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. 基于 DNS 的服务发现

#### 2.1 DNS SRV 记录

DNS SRV 记录可以存储服务的主机名和端口：

```
_service._proto.name. TTL class SRV priority weight port target
_http._tcp.api.example.com. 300 IN SRV 10 60 8080 api-1.example.com.
_http._tcp.api.example.com. 300 IN SRV 10 30 8080 api-2.example.com.
_http._tcp.api.example.com. 300 IN SRV 10 10 8080 api-3.example.com.
```

#### 2.2 Go 实现 DNS 服务发现

```go
package servicediscovery

import (
    "context"
    "fmt"
    "net"
    "sync"
    "time"
)

// ServiceInstance 服务实例
type ServiceInstance struct {
    Host     string
    Port     int
    Weight   int
    Priority int
}

// DNSDiscoverer DNS 服务发现
type DNSDiscoverer struct {
    domain   string
    resolver *net.Resolver
    mu       sync.RWMutex
    instances []ServiceInstance
    lastUpdate time.Time
    ttl        time.Duration
}

func NewDNSDiscoverer(domain string, ttl time.Duration) *DNSDiscoverer {
    return &DNSDiscoverer{
        domain:   domain,
        resolver: net.DefaultResolver,
        ttl:      ttl,
    }
}

// Discover 发现服务实例
func (d *DNSDiscoverer) Discover(ctx context.Context) ([]ServiceInstance, error) {
    d.mu.RLock()
    if time.Since(d.lastUpdate) < d.ttl {
        instances := d.instances
        d.mu.RUnlock()
        return instances, nil
    }
    d.mu.RUnlock()

    return d.refresh(ctx)
}

// refresh 刷新实例列表
func (d *DNSDiscoverer) refresh(ctx context.Context) ([]ServiceInstance, error) {
    d.mu.Lock()
    defer d.mu.Unlock()

    // 使用 SRV 记录发现
    _, addrs, err := d.resolver.LookupSRV(ctx, "http", "tcp", d.domain)
    if err != nil {
        // 回退到 A 记录
        ips, err := d.resolver.LookupHost(ctx, d.domain)
        if err != nil {
            return nil, fmt.Errorf("DNS 解析失败: %w", err)
        }

        var instances []ServiceInstance
        for _, ip := range ips {
            instances = append(instances, ServiceInstance{
                Host:   ip,
                Port:   80, // 默认端口
                Weight: 1,
            })
        }
        d.instances = instances
        d.lastUpdate = time.Now()
        return instances, nil
    }

    var instances []ServiceInstance
    for _, addr := range addrs {
        instances = append(instances, ServiceInstance{
            Host:     addr.Target,
            Port:     int(addr.Port),
            Weight:   int(addr.Weight),
            Priority: int(addr.Priority),
        })
    }

    d.instances = instances
    d.lastUpdate = time.Now()
    return instances, nil
}

// StartWatching 启动后台监听
func (d *DNSDiscoverer) StartWatching(ctx context.Context, interval time.Duration) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            d.refresh(ctx)
        }
    }
}
```

---

### 3. 基于 Consul 的服务发现

#### 3.1 Consul 核心概念

```
┌──────────────────────────────────────────────────────────────┐
│                     Consul 架构                                │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Consul      │  │ Consul      │  │ Consul      │          │
│  │ Server 1    │  │ Server 2    │  │ Server 3    │          │
│  │ (Leader)    │  │ (Follower)  │  │ (Follower)  │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                   │
│         └────────────────┼────────────────┘                   │
│                          │                                     │
│                    Raft 一致性                                  │
│                          │                                     │
│  ┌─────────────┐  ┌─────┴───────┐  ┌─────────────┐          │
│  │ Consul      │  │ Consul      │  │ Consul      │          │
│  │ Agent 1     │  │ Agent 2     │  │ Agent 3     │          │
│  │ (Client)    │  │ (Client)    │  │ (Client)    │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                   │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐          │
│  │  服务实例    │  │  服务实例    │  │  服务实例    │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

**Consul 核心功能：**
- **服务注册**：服务启动时向 Consul Agent 注册
- **健康检查**：Consul 定期检查服务健康状态
- **服务发现**：通过 HTTP API 或 DNS 查询服务
- **KV 存储**：分布式键值存储
- **多数据中心**：支持跨数据中心的服务发现

#### 3.2 Go 实现 Consul 服务发现

```go
package servicediscovery

import (
    "context"
    "fmt"
    "log"
    "sync"
    "time"

    "github.com/hashicorp/consul/api"
)

// ConsulInstance Consul 服务实例
type ConsulInstance struct {
    ID      string
    Name    string
    Address string
    Port    int
    Tags    []string
    Meta    map[string]string
    Healthy bool
}

// ConsulDiscoverer Consul 服务发现
type ConsulDiscoverer struct {
    client    *api.Client
    serviceName string
    lastIndex uint64

    mu        sync.RWMutex
    instances []ConsulInstance
    watchers  []chan []ConsulInstance
}

func NewConsulDiscoverer(addr, serviceName string) (*ConsulDiscoverer, error) {
    config := api.DefaultConfig()
    config.Address = addr

    client, err := api.NewClient(config)
    if err != nil {
        return nil, fmt.Errorf("创建 Consul 客户端失败: %w", err)
    }

    return &ConsulDiscoverer{
        client:      client,
        serviceName: serviceName,
    }, nil
}

// Discover 发现服务实例
func (d *ConsulDiscoverer) Discover(ctx context.Context) ([]ConsulInstance, error) {
    d.mu.RLock()
    if d.instances != nil {
        instances := d.instances
        d.mu.RUnlock()
        return instances, nil
    }
    d.mu.RUnlock()

    return d.refresh(ctx)
}

// refresh 刷新实例列表
func (d *ConsulDiscoverer) refresh(ctx context.Context) ([]ConsulInstance, error) {
    services, meta, err := d.client.Health().Service(
        d.serviceName,
        "",    // tag filter
        true,  // only passing
        &api.QueryOptions{
            WaitIndex: d.lastIndex,
            WaitTime:  30 * time.Second,
        },
    )
    if err != nil {
        return nil, fmt.Errorf("查询服务失败: %w", err)
    }

    d.lastIndex = meta.LastIndex

    var instances []ConsulInstance
    for _, svc := range services {
        instances = append(instances, ConsulInstance{
            ID:      svc.Service.ID,
            Name:    svc.Service.Service,
            Address: svc.Service.Address,
            Port:    svc.Service.Port,
            Tags:    svc.Service.Tags,
            Meta:    svc.Service.Meta,
            Healthy: true,
        })
    }

    d.mu.Lock()
    d.instances = instances
    d.mu.Unlock()

    // 通知观察者
    d.notifyWatchers(instances)

    return instances, nil
}

// Watch 监听服务变化
func (d *ConsulDiscoverer) Watch(ctx context.Context) <-chan []ConsulInstance {
    ch := make(chan []ConsulInstance, 1)

    d.mu.Lock()
    d.watchers = append(d.watchers, ch)
    d.mu.Unlock()

    return ch
}

func (d *ConsulDiscoverer) notifyWatchers(instances []ConsulInstance) {
    d.mu.RLock()
    defer d.mu.RUnlock()

    for _, ch := range d.watchers {
        select {
        case ch <- instances:
        default:
            // channel 满，跳过
        }
    }
}

// StartWatching 启动后台监听（阻塞查询）
func (d *ConsulDiscoverer) StartWatching(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            return
        default:
        }

        _, err := d.refresh(ctx)
        if err != nil {
            log.Printf("刷新服务列表失败: %v", err)
            time.Sleep(5 * time.Second)
        }
    }
}

// Register 注册服务
func RegisterService(client *api.Client, svc *api.AgentServiceRegistration) error {
    return client.Agent().ServiceRegister(svc)
}

// Deregister 注销服务
func DeregisterService(client *api.Client, serviceID string) error {
    return client.Agent().ServiceDeregister(serviceID)
}
```

#### 3.3 Consul 服务注册

```go
package main

import (
    "fmt"
    "log"
    "os"
    "os/signal"
    "syscall"

    "github.com/hashicorp/consul/api"
)

func main() {
    // 创建 Consul 客户端
    client, err := api.NewClient(api.DefaultConfig())
    if err != nil {
        log.Fatal(err)
    }

    // 注册服务
    registration := &api.AgentServiceRegistration{
        ID:      "web-api-1",
        Name:    "web-api",
        Address: "10.0.0.1",
        Port:    8080,
        Tags:    []string{"v1", "production"},
        Meta: map[string]string{
            "version": "1.0.0",
        },
        Check: &api.AgentServiceCheck{
            HTTP:                           "http://10.0.0.1:8080/health",
            Interval:                       "10s",
            Timeout:                        "3s",
            DeregisterCriticalServiceAfter: "60s",
        },
    }

    if err := client.Agent().ServiceRegister(registration); err != nil {
        log.Fatalf("注册服务失败: %v", err)
    }
    log.Println("服务注册成功")

    // 优雅关闭时注销服务
    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
    <-sigCh

    log.Println("注销服务...")
    if err := client.Agent().ServiceDeregister("web-api-1"); err != nil {
        log.Printf("注销服务失败: %v", err)
    }
    log.Println("服务已注销")
}
```

---

### 4. 基于 etcd 的服务发现

#### 4.1 etcd 核心概念

etcd 是一个分布式键值存储，常用于配置管理和服务发现。它使用 Raft 共识算法保证一致性。

```
┌─────────────────────────────────────────────────────────┐
│                     etcd 集群                             │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ etcd-1   │  │ etcd-2   │  │ etcd-3   │              │
│  │ (Leader) │  │(Follower)│  │(Follower)│              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       │              │              │                     │
│       └──────────────┼──────────────┘                     │
│                      │                                    │
│               Raft 共识协议                                │
│                                                           │
│  KV 存储结构：                                            │
│  /services/web-api/instance-1 → {"host":"10.0.0.1",...} │
│  /services/web-api/instance-2 → {"host":"10.0.0.2",...} │
│  /services/db/instance-1 → {"host":"10.0.0.3",...}      │
└─────────────────────────────────────────────────────────┘
```

#### 4.2 Go 实现 etcd 服务发现

```go
package servicediscovery

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "path"
    "sync"
    "time"

    clientv3 "go.etcd.io/etcd/client/v3"
)

// EtcdInstance etcd 服务实例
type EtcdInstance struct {
    ID      string            `json:"id"`
    Name    string            `json:"name"`
    Address string            `json:"address"`
    Port    int               `json:"port"`
    Meta    map[string]string `json:"meta,omitempty"`
}

// EtcdDiscoverer etcd 服务发现
type EtcdDiscoverer struct {
    client    *clientv3.Client
    prefix    string // key 前缀，如 /services/web-api

    mu        sync.RWMutex
    instances map[string]EtcdInstance
    watchers  []chan []EtcdInstance
}

func NewEtcdDiscoverer(endpoints []string, serviceName string) (*EtcdDiscoverer, error) {
    client, err := clientv3.New(clientv3.Config{
        Endpoints:   endpoints,
        DialTimeout: 5 * time.Second,
    })
    if err != nil {
        return nil, fmt.Errorf("连接 etcd 失败: %w", err)
    }

    return &EtcdDiscoverer{
        client:    client,
        prefix:    path.Join("/services", serviceName),
        instances: make(map[string]EtcdInstance),
    }, nil
}

// Discover 发现服务实例
func (d *EtcdDiscoverer) Discover(ctx context.Context) ([]EtcdInstance, error) {
    d.mu.RLock()
    if len(d.instances) > 0 {
        instances := make([]EtcdInstance, 0, len(d.instances))
        for _, inst := range d.instances {
            instances = append(instances, inst)
        }
        d.mu.RUnlock()
        return instances, nil
    }
    d.mu.RUnlock()

    return d.refresh(ctx)
}

// refresh 刷新实例列表
func (d *EtcdDiscoverer) refresh(ctx context.Context) ([]EtcdInstance, error) {
    resp, err := d.client.Get(ctx, d.prefix, clientv3.WithPrefix())
    if err != nil {
        return nil, fmt.Errorf("获取服务列表失败: %w", err)
    }

    d.mu.Lock()
    d.instances = make(map[string]EtcdInstance)
    for _, kv := range resp.Kvs {
        var inst EtcdInstance
        if err := json.Unmarshal(kv.Value, &inst); err != nil {
            log.Printf("解析实例数据失败: %v", err)
            continue
        }
        d.instances[string(kv.Key)] = inst
    }

    instances := make([]EtcdInstance, 0, len(d.instances))
    for _, inst := range d.instances {
        instances = append(instances, inst)
    }
    d.mu.Unlock()

    d.notifyWatchers(instances)
    return instances, nil
}

// Watch 监听服务变化
func (d *EtcdDiscoverer) Watch(ctx context.Context) {
    watchCh := d.client.Watch(ctx, d.prefix, clientv3.WithPrefix())

    for resp := range watchCh {
        for _, event := range resp.Events {
            key := string(event.Kv.Key)

            switch event.Type {
            case clientv3.EventTypePut:
                var inst EtcdInstance
                if err := json.Unmarshal(event.Kv.Value, &inst); err != nil {
                    log.Printf("解析实例数据失败: %v", err)
                    continue
                }
                d.mu.Lock()
                d.instances[key] = inst
                d.mu.Unlock()

            case clientv3.EventTypeDelete:
                d.mu.Lock()
                delete(d.instances, key)
                d.mu.Unlock()
            }
        }

        // 通知观察者
        d.mu.RLock()
        instances := make([]EtcdInstance, 0, len(d.instances))
        for _, inst := range d.instances {
            instances = append(instances, inst)
        }
        d.mu.RUnlock()
        d.notifyWatchers(instances)
    }
}

func (d *EtcdDiscoverer) notifyWatchers(instances []EtcdInstance) {
    d.mu.RLock()
    defer d.mu.RUnlock()

    for _, ch := range d.watchers {
        select {
        case ch <- instances:
        default:
        }
    }
}

// Register 注册服务（带租约）
func (d *EtcdDiscoverer) Register(ctx context.Context, inst EtcdInstance, ttl time.Duration) error {
    // 创建租约
    leaseResp, err := d.client.Grant(ctx, int64(ttl.Seconds()))
    if err != nil {
        return fmt.Errorf("创建租约失败: %w", err)
    }

    // 序列化实例数据
    data, err := json.Marshal(inst)
    if err != nil {
        return fmt.Errorf("序列化实例失败: %w", err)
    }

    key := path.Join(d.prefix, inst.ID)

    // 注册服务（带租约）
    _, err = d.client.Put(ctx, key, string(data), clientv3.WithLease(leaseResp.ID))
    if err != nil {
        return fmt.Errorf("注册服务失败: %w", err)
    }

    // 保持租约（自动续期）
    keepAliveCh, err := d.client.KeepAlive(ctx, leaseResp.ID)
    if err != nil {
        return fmt.Errorf("保持租约失败: %w", err)
    }

    // 消费 keepalive 响应
    go func() {
        for {
            select {
            case <-ctx.Done():
                return
            case _, ok := <-keepAliveCh:
                if !ok {
                    log.Println("租约续期 channel 关闭")
                    return
                }
            }
        }
    }()

    return nil
}

// Deregister 注销服务
func (d *EtcdDiscoverer) Deregister(ctx context.Context, instanceID string) error {
    key := path.Join(d.prefix, instanceID)
    _, err := d.client.Delete(ctx, key)
    return err
}

// Close 关闭连接
func (d *EtcdDiscoverer) Close() error {
    return d.client.Close()
}
```

---

### 5. 健康检查机制

#### 5.1 健康检查模式

```
┌──────────────────────────────────────────────────────────────┐
│                    健康检查模式                                 │
│                                                                │
│  1. 主动探测（Pull）：                                          │
│     Registry ──HTTP GET /health──→ Service                    │
│     Registry ──TCP Connect──→ Service                         │
│     Registry ──gRPC Health Check──→ Service                   │
│                                                                │
│  2. 被动通知（Push）：                                          │
│     Service ──Heartbeat──→ Registry                           │
│     Service ──TTL 续期──→ Registry (etcd lease)              │
│                                                                │
│  3. 混合模式：                                                  │
│     Service 注册 + TTL                                         │
│     Registry 定期检查 + 检测心跳超时                             │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2 完整健康检查实现

```go
package servicediscovery

import (
    "context"
    "fmt"
    "net"
    "net/http"
    "sync"
    "time"
)

// HealthCheckType 健康检查类型
type HealthCheckType string

const (
    HealthCheckHTTP HealthCheckType = "http"
    HealthCheckTCP  HealthCheckType = "tcp"
    HealthCheckGRPC HealthCheckType = "grpc"
    HealthCheckTTL  HealthCheckType = "ttl"
)

// HealthCheckConfig 健康检查配置
type HealthCheckConfig struct {
    Type     HealthCheckType
    URL      string        // HTTP 检查 URL
    Address  string        // TCP 检查地址
    Interval time.Duration // 检查间隔
    Timeout  time.Duration // 检查超时
    // 连续失败/成功阈值
    FailureThreshold int
    SuccessThreshold int
}

// HealthChecker 健康检查器
type HealthChecker struct {
    config HealthCheckConfig
    client *http.Client

    mu             sync.RWMutex
    status         HealthStatus
    consecutiveOK  int
    consecutiveErr int
    lastCheck      time.Time
    lastError      error
}

// HealthStatus 健康状态
type HealthStatus int

const (
    StatusUnknown HealthStatus = iota
    StatusHealthy
    StatusUnhealthy
    StatusDegraded
)

func (s HealthStatus) String() string {
    switch s {
    case StatusHealthy:
        return "healthy"
    case StatusUnhealthy:
        return "unhealthy"
    case StatusDegraded:
        return "degraded"
    default:
        return "unknown"
    }
}

func NewHealthChecker(config HealthCheckConfig) *HealthChecker {
    return &HealthChecker{
        config: config,
        client: &http.Client{
            Timeout: config.Timeout,
        },
        status: StatusUnknown,
    }
}

// Check 执行一次健康检查
func (c *HealthChecker) Check(ctx context.Context) HealthStatus {
    var err error

    switch c.config.Type {
    case HealthCheckHTTP:
        err = c.checkHTTP(ctx)
    case HealthCheckTCP:
        err = c.checkTCP(ctx)
    case HealthCheckTTL:
        // TTL 检查由外部处理
        return c.getStatus()
    }

    c.mu.Lock()
    defer c.mu.Unlock()

    c.lastCheck = time.Now()

    if err != nil {
        c.consecutiveErr++
        c.consecutiveOK = 0
        c.lastError = err

        if c.consecutiveErr >= c.config.FailureThreshold {
            c.status = StatusUnhealthy
        } else {
            c.status = StatusDegraded
        }
    } else {
        c.consecutiveOK++
        c.consecutiveErr = 0
        c.lastError = nil

        if c.consecutiveOK >= c.config.SuccessThreshold {
            c.status = StatusHealthy
        } else {
            c.status = StatusDegraded
        }
    }

    return c.status
}

func (c *HealthChecker) checkHTTP(ctx context.Context) error {
    req, err := http.NewRequestWithContext(ctx, "GET", c.config.URL, nil)
    if err != nil {
        return fmt.Errorf("创建请求失败: %w", err)
    }

    resp, err := c.client.Do(req)
    if err != nil {
        return fmt.Errorf("HTTP 请求失败: %w", err)
    }
    defer resp.Body.Close()

    if resp.StatusCode < 200 || resp.StatusCode >= 300 {
        return fmt.Errorf("HTTP 状态码: %d", resp.StatusCode)
    }

    return nil
}

func (c *HealthChecker) checkTCP(ctx context.Context) error {
    var d net.Dialer
    conn, err := d.DialContext(ctx, "tcp", c.config.Address)
    if err != nil {
        return fmt.Errorf("TCP 连接失败: %w", err)
    }
    conn.Close()
    return nil
}

func (c *HealthChecker) getStatus() HealthStatus {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.status
}

// Start 启动定期健康检查
func (c *HealthChecker) Start(ctx context.Context, onChange func(HealthStatus)) {
    ticker := time.NewTicker(c.config.Interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            oldStatus := c.getStatus()
            newStatus := c.Check(ctx)
            if oldStatus != newStatus && onChange != nil {
                onChange(newStatus)
            }
        }
    }
}
```

---

### 6. 负载均衡策略

#### 6.1 策略对比

```
┌──────────────────────────────────────────────────────────────┐
│                    负载均衡策略对比                             │
│                                                                │
│  轮询 (Round Robin)：                                         │
│  请求 → A → B → C → A → B → C → ...                        │
│  优点：简单公平                                                │
│  缺点：不考虑实例负载差异                                       │
│                                                                │
│  加权轮询 (Weighted Round Robin)：                             │
│  权重 A:3, B:2, C:1                                          │
│  请求 → A → A → A → B → B → C → ...                        │
│  优点：考虑实例能力差异                                        │
│  缺点：权重需要手动配置                                        │
│                                                                │
│  最少连接 (Least Connections)：                                │
│  选择当前连接数最少的实例                                       │
│  优点：自动适应负载变化                                        │
│  缺点：需要维护连接计数                                        │
│                                                                │
│  一致性哈希 (Consistent Hashing)：                             │
│  根据请求 key 的哈希值选择实例                                  │
│  优点：相同 key 总是路由到同一实例（缓存友好）                    │
│  缺点：可能不均匀分布                                          │
│                                                                │
│  随机 (Random)：                                              │
│  随机选择一个实例                                              │
│  优点：简单                                                    │
│  缺点：可能不均匀                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 6.2 负载均衡器实现

```go
package servicediscovery

import (
    "errors"
    "math/rand"
    "sync"
    "sync/atomic"
)

var (
    ErrNoInstances = errors.New("没有可用的服务实例")
)

// LoadBalancer 负载均衡器接口
type LoadBalancer interface {
    // Select 选择一个实例
    Select(instances []ServiceInstance) (ServiceInstance, error)
}

// ServiceInstance 通用服务实例
type ServiceInstance struct {
    ID       string
    Address  string
    Port     int
    Weight   int
    Metadata map[string]string
}

// RoundRobinBalancer 轮询负载均衡器
type RoundRobinBalancer struct {
    counter uint64
}

func NewRoundRobinBalancer() *RoundRobinBalancer {
    return &RoundRobinBalancer{}
}

func (b *RoundRobinBalancer) Select(instances []ServiceInstance) (ServiceInstance, error) {
    if len(instances) == 0 {
        return ServiceInstance{}, ErrNoInstances
    }

    idx := atomic.AddUint64(&b.counter, 1)
    return instances[idx%uint64(len(instances))], nil
}

// WeightedRoundRobinBalancer 加权轮询负载均衡器
type WeightedRoundRobinBalancer struct {
    mu          sync.Mutex
    currentWeights []int
}

func NewWeightedRoundRobinBalancer() *WeightedRoundRobinBalancer {
    return &WeightedRoundRobinBalancer{}
}

func (b *WeightedRoundRobinBalancer) Select(instances []ServiceInstance) (ServiceInstance, error) {
    if len(instances) == 0 {
        return ServiceInstance{}, ErrNoInstances
    }

    b.mu.Lock()
    defer b.mu.Unlock()

    // 初始化当前权重
    if len(b.currentWeights) != len(instances) {
        b.currentWeights = make([]int, len(instances))
    }

    // 计算总权重
    totalWeight := 0
    for _, inst := range instances {
        totalWeight += inst.Weight
    }

    // 平滑加权轮询（Smooth Weighted Round Robin）
    maxIdx := 0
    maxWeight := 0
    for i, inst := range instances {
        b.currentWeights[i] += inst.Weight
        if b.currentWeights[i] > maxWeight {
            maxWeight = b.currentWeights[i]
            maxIdx = i
        }
    }

    b.currentWeights[maxIdx] -= totalWeight

    return instances[maxIdx], nil
}

// LeastConnectionsBalancer 最少连接负载均衡器
type LeastConnectionsBalancer struct {
    connections sync.Map // instanceID -> *int64
}

func NewLeastConnectionsBalancer() *LeastConnectionsBalancer {
    return &LeastConnectionsBalancer{}
}

func (b *LeastConnectionsBalancer) Select(instances []ServiceInstance) (ServiceInstance, error) {
    if len(instances) == 0 {
        return ServiceInstance{}, ErrNoInstances
    }

    var selected ServiceInstance
    minConns := int64(^uint64(0) >> 1) // MaxInt64

    for _, inst := range instances {
        conns := b.getConns(inst.ID)
        if conns < minConns {
            minConns = conns
            selected = inst
        }
    }

    return selected, nil
}

func (b *LeastConnectionsBalancer) getConns(id string) int64 {
    if v, ok := b.connections.Load(id); ok {
        return atomic.LoadInt64(v.(*int64))
    }
    return 0
}

// IncrConns 增加连接数
func (b *LeastConnectionsBalancer) IncrConns(id string) {
    val, _ := b.connections.LoadOrStore(id, new(int64))
    atomic.AddInt64(val.(*int64), 1)
}

// DecrConns 减少连接数
func (b *LeastConnectionsBalancer) DecrConns(id string) {
    if val, ok := b.connections.Load(id); ok {
        atomic.AddInt64(val.(*int64), -1)
    }
}

// RandomBalancer 随机负载均衡器
type RandomBalancer struct{}

func NewRandomBalancer() *RandomBalancer {
    return &RandomBalancer{}
}

func (b *RandomBalancer) Select(instances []ServiceInstance) (ServiceInstance, error) {
    if len(instances) == 0 {
        return ServiceInstance{}, ErrNoInstances
    }

    idx := rand.Intn(len(instances))
    return instances[idx], nil
}
```

---

### 7. 一致性哈希

#### 7.1 一致性哈希原理

一致性哈希解决了传统哈希在节点增减时大量数据迁移的问题：

```
传统哈希（取模）：
  hash(key) % N
  N=3: key1 → 1, key2 → 2, key3 → 0
  N=4: key1 → 1, key2 → 2, key3 → 3  ← key3 的位置变了！

一致性哈希：
  将节点和 key 都映射到同一个哈希环上
  key 顺时针找到的第一个节点就是目标

  哈希环 (0 ~ 2^32-1)：

           Node A (0°)
            │
    ────────┼────────
   │                 │
  Node C            Node B
  (120°)            (240°)
   │                 │
    ────────┼────────
            │

  key1 hash → 30° → 顺时针 → Node B
  key2 hash → 150° → 顺时针 → Node C
  key3 hash → 250° → 顺时针 → Node A

  新增 Node D (180°):
  只有 key2 (150°) 需要迁移到 Node D
  key1 和 key3 不受影响
```

#### 7.2 虚拟节点

为了解决数据分布不均匀的问题，引入虚拟节点：

```
每个物理节点对应多个虚拟节点：

物理节点 A → 虚拟节点 A-0, A-1, A-2, ..., A-149
物理节点 B → 虚拟节点 B-0, B-1, B-2, ..., B-149
物理节点 C → 虚拟节点 C-0, C-1, C-2, ..., C-149

哈希环上分布更均匀：

  A-42  B-17  C-88  A-103  B-55  C-12  A-78  ...
  ─────┼──────┼──────┼──────┼──────┼──────┼──────→

  虚拟节点数量越多，分布越均匀
  典型值：100-200 个虚拟节点/物理节点
```

#### 7.3 完整一致性哈希实现

```go
package consistent

import (
    "errors"
    "hash/crc32"
    "sort"
    "sync"
)

var (
    ErrEmptyRing = errors.New("哈希环为空")
)

// ConsistentHash 一致性哈希
type ConsistentHash struct {
    mu             sync.RWMutex
    ring           map[uint32]string // hash -> node
    sortedKeys     []uint32          // 排序后的哈希值
    replicas       int               // 每个节点的虚拟节点数
    hashFunc       func(data []byte) uint32
}

// New 创建一致性哈希
func New(replicas int) *ConsistentHash {
    return &ConsistentHash{
        ring:     make(map[uint32]string),
        replicas: replicas,
        hashFunc: crc32.ChecksumIEEE,
    }
}

// NewWithHash 使用自定义哈希函数创建一致性哈希
func NewWithHash(replicas int, hashFunc func(data []byte) uint32) *ConsistentHash {
    return &ConsistentHash{
        ring:     make(map[uint32]string),
        replicas: replicas,
        hashFunc: hashFunc,
    }
}

// Add 添加节点
func (h *ConsistentHash) Add(nodes ...string) {
    h.mu.Lock()
    defer h.mu.Unlock()

    for _, node := range nodes {
        for i := 0; i < h.replicas; i++ {
            key := h.hashFunc([]byte(node + "-" + itoa(i)))
            h.ring[key] = node
            h.sortedKeys = append(h.sortedKeys, key)
        }
    }

    sort.Slice(h.sortedKeys, func(i, j int) bool {
        return h.sortedKeys[i] < h.sortedKeys[j]
    })
}

// Remove 移除节点
func (h *ConsistentHash) Remove(nodes ...string) {
    h.mu.Lock()
    defer h.mu.Unlock()

    for _, node := range nodes {
        for i := 0; i < h.replicas; i++ {
            key := h.hashFunc([]byte(node + "-" + itoa(i)))
            delete(h.ring, key)
        }
    }

    // 重建排序的 keys
    h.sortedKeys = h.sortedKeys[:0]
    for k := range h.ring {
        h.sortedKeys = append(h.sortedKeys, k)
    }
    sort.Slice(h.sortedKeys, func(i, j int) bool {
        return h.sortedKeys[i] < h.sortedKeys[j]
    })
}

// Get 获取 key 对应的节点
func (h *ConsistentHash) Get(key string) (string, error) {
    h.mu.RLock()
    defer h.mu.RUnlock()

    if len(h.ring) == 0 {
        return "", ErrEmptyRing
    }

    hash := h.hashFunc([]byte(key))

    // 二分查找：找到第一个 >= hash 的节点
    idx := sort.Search(len(h.sortedKeys), func(i int) bool {
        return h.sortedKeys[i] >= hash
    })

    // 如果没找到，回到环的开头
    if idx >= len(h.sortedKeys) {
        idx = 0
    }

    return h.ring[h.sortedKeys[idx]], nil
}

// GetN 获取 key 对应的 N 个不同节点
func (h *ConsistentHash) GetN(key string, n int) ([]string, error) {
    h.mu.RLock()
    defer h.mu.RUnlock()

    if len(h.ring) == 0 {
        return nil, ErrEmptyRing
    }

    hash := h.hashFunc([]byte(key))

    var result []string
    seen := make(map[string]bool)

    idx := sort.Search(len(h.sortedKeys), func(i int) bool {
        return h.sortedKeys[i] >= hash
    })

    for len(result) < n && len(seen) < len(h.ring)/h.replicas {
        if idx >= len(h.sortedKeys) {
            idx = 0
        }

        node := h.ring[h.sortedKeys[idx]]
        if !seen[node] {
            seen[node] = true
            result = append(result, node)
        }
        idx++
    }

    return result, nil
}

// Nodes 获取所有节点
func (h *ConsistentHash) Nodes() []string {
    h.mu.RLock()
    defer h.mu.RUnlock()

    seen := make(map[string]bool)
    var nodes []string
    for _, node := range h.ring {
        if !seen[node] {
            seen[node] = true
            nodes = append(nodes, node)
        }
    }
    return nodes
}

// itoa 简单的 int 转 string
func itoa(i int) string {
    if i == 0 {
        return "0"
    }
    var buf [20]byte
    pos := len(buf)
    for i > 0 {
        pos--
        buf[pos] = byte('0' + i%10)
        i /= 10
    }
    return string(buf[pos:])
}
```

#### 7.4 一致性哈希测试

```go
package consistent

import (
    "fmt"
    "testing"
)

func TestConsistentHash_Basic(t *testing.T) {
    h := New(150)
    h.Add("node-A", "node-B", "node-C")

    // 同一个 key 应该总是返回同一个节点
    node1, _ := h.Get("my-key")
    node2, _ := h.Get("my-key")
    if node1 != node2 {
        t.Errorf("same key should return same node: %s != %s", node1, node2)
    }

    // 不同 key 应该分布到不同节点
    distribution := make(map[string]int)
    for i := 0; i < 10000; i++ {
        key := fmt.Sprintf("key-%d", i)
        node, err := h.Get(key)
        if err != nil {
            t.Fatal(err)
        }
        distribution[node]++
    }

    // 验证分布相对均匀（每个节点至少 20%）
    for node, count := range distribution {
        pct := float64(count) / 10000 * 100
        t.Logf("节点 %s: %d (%.1f%%)", node, count, pct)
        if pct < 20 {
            t.Errorf("节点 %s 分布不均匀: %.1f%%", node, pct)
        }
    }
}

func TestConsistentHash_AddRemove(t *testing.T) {
    h := New(150)
    h.Add("node-A", "node-B", "node-C")

    // 记录原始映射
    original := make(map[string]string)
    for i := 0; i < 10000; i++ {
        key := fmt.Sprintf("key-%d", i)
        node, _ := h.Get(key)
        original[key] = node
    }

    // 添加新节点
    h.Add("node-D")

    // 统计迁移数量
    migrated := 0
    for i := 0; i < 10000; i++ {
        key := fmt.Sprintf("key-%d", i)
        node, _ := h.Get(key)
        if original[key] != node {
            migrated++
        }
    }

    // 迁移比例应该接近 1/4 (25%)
    pct := float64(migrated) / 10000 * 100
    t.Logf("添加节点后迁移比例: %.1f%%", pct)
    if pct < 15 || pct > 35 {
        t.Errorf("迁移比例异常: %.1f%% (期望 15%%-35%%)", pct)
    }
}

func TestConsistentHash_GetN(t *testing.T) {
    h := New(150)
    h.Add("node-A", "node-B", "node-C", "node-D")

    nodes, err := h.GetN("my-key", 3)
    if err != nil {
        t.Fatal(err)
    }

    if len(nodes) != 3 {
        t.Errorf("期望 3 个节点，得到 %d", len(nodes))
    }

    // 验证返回的是不同节点
    seen := make(map[string]bool)
    for _, node := range nodes {
        if seen[node] {
            t.Errorf("重复节点: %s", node)
        }
        seen[node] = true
    }
}
```

---

### 8. 完整服务发现客户端

#### 8.1 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                  ServiceDiscovery 客户端架构                    │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   DiscoveryClient                        │ │
│  │                                                           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │ │
│  │  │ Registry │  │ Health   │  │ Load     │              │ │
│  │  │ Adapter  │  │ Checker  │  │ Balancer │              │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘              │ │
│  │       │              │              │                     │ │
│  │       ▼              ▼              ▼                     │ │
│  │  ┌─────────────────────────────────────────────────────┐│ │
│  │  │              InstanceManager                         ││ │
│  │  │  - 维护健康实例列表                                    ││ │
│  │  │  - 处理实例变更事件                                    ││ │
│  │  │  - 通知负载均衡器更新                                  ││ │
│  │  └─────────────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                │
│  使用方式：                                                     │
│  client := NewDiscoveryClient(consulAddr, "web-api")           │
│  instance, err := client.Select()                              │
│  client.Call(instance, request)                                │
└──────────────────────────────────────────────────────────────┘
```

#### 8.2 完整实现

```go
package servicediscovery

import (
    "context"
    "fmt"
    "log"
    "sync"
    "time"
)

// RegistryAdapter 注册中心适配器接口
type RegistryAdapter interface {
    // Discover 发现服务实例
    Discover(ctx context.Context) ([]ServiceInstance, error)
    // Watch 监听服务变化
    Watch(ctx context.Context) (<-chan []ServiceInstance, error)
    // Register 注册服务
    Register(ctx context.Context, instance ServiceInstance) error
    // Deregister 注销服务
    Deregister(ctx context.Context, instanceID string) error
}

// DiscoveryConfig 服务发现配置
type DiscoveryConfig struct {
    RegistryType string // consul, etcd, dns
    RegistryAddr string
    ServiceName  string
    HealthCheck  HealthCheckConfig
    LBStrategy   string // round-robin, weighted, least-conn, random, consistent-hash
    RefreshInterval time.Duration
}

// DiscoveryClient 服务发现客户端
type DiscoveryClient struct {
    config    DiscoveryConfig
    registry  RegistryAdapter
    balancer  LoadBalancer
    healthChk *HealthChecker

    mu        sync.RWMutex
    instances []ServiceInstance
    healthy   []ServiceInstance
}

// NewDiscoveryClient 创建服务发现客户端
func NewDiscoveryClient(config DiscoveryConfig) (*DiscoveryClient, error) {
    // 创建注册中心适配器
    var registry RegistryAdapter
    switch config.RegistryType {
    case "consul":
        var err error
        registry, err = NewConsulAdapter(config.RegistryAddr, config.ServiceName)
        if err != nil {
            return nil, err
        }
    case "etcd":
        var err error
        registry, err = NewEtcdAdapter([]string{config.RegistryAddr}, config.ServiceName)
        if err != nil {
            return nil, err
        }
    case "dns":
        registry = NewDNSAdapter(config.ServiceName, config.RefreshInterval)
    default:
        return nil, fmt.Errorf("不支持的注册中心类型: %s", config.RegistryType)
    }

    // 创建负载均衡器
    var balancer LoadBalancer
    switch config.LBStrategy {
    case "round-robin":
        balancer = NewRoundRobinBalancer()
    case "weighted":
        balancer = NewWeightedRoundRobinBalancer()
    case "least-conn":
        balancer = NewLeastConnectionsBalancer()
    case "random":
        balancer = NewRandomBalancer()
    case "consistent-hash":
        balancer = nil // 使用一致性哈希时需要特殊处理
    default:
        balancer = NewRoundRobinBalancer()
    }

    client := &DiscoveryClient{
        config:    config,
        registry:  registry,
        balancer:  balancer,
        healthChk: NewHealthChecker(config.HealthCheck),
    }

    return client, nil
}

// Start 启动服务发现
func (c *DiscoveryClient) Start(ctx context.Context) error {
    // 首次发现
    instances, err := c.registry.Discover(ctx)
    if err != nil {
        return fmt.Errorf("首次发现失败: %w", err)
    }
    c.updateInstances(instances)

    // 启动监听
    watchCh, err := c.registry.Watch(ctx)
    if err != nil {
        return fmt.Errorf("启动监听失败: %w", err)
    }

    // 处理实例变更
    go func() {
        for {
            select {
            case <-ctx.Done():
                return
            case instances := <-watchCh:
                c.updateInstances(instances)
            }
        }
    }()

    // 启动健康检查
    go c.healthCheckLoop(ctx)

    return nil
}

// updateInstances 更新实例列表
func (c *DiscoveryClient) updateInstances(instances []ServiceInstance) {
    c.mu.Lock()
    c.instances = instances
    c.mu.Unlock()

    log.Printf("更新服务实例列表: %d 个实例", len(instances))
}

// healthCheckLoop 健康检查循环
func (c *DiscoveryClient) healthCheckLoop(ctx context.Context) {
    ticker := time.NewTicker(c.config.HealthCheck.Interval)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            c.checkAllHealth(ctx)
        }
    }
}

// checkAllHealth 检查所有实例健康状态
func (c *DiscoveryClient) checkAllHealth(ctx context.Context) {
    c.mu.RLock()
    instances := c.instances
    c.mu.RUnlock()

    var healthy []ServiceInstance
    for _, inst := range instances {
        status := c.healthCheck(ctx, inst)
        if status == StatusHealthy {
            healthy = append(healthy, inst)
        }
    }

    c.mu.Lock()
    c.healthy = healthy
    c.mu.Unlock()
}

func (c *DiscoveryClient) healthCheck(ctx context.Context, inst ServiceInstance) HealthStatus {
    cfg := c.config.HealthCheck
    cfg.URL = fmt.Sprintf("http://%s:%d/health", inst.Address, inst.Port)
    cfg.Address = fmt.Sprintf("%s:%d", inst.Address, inst.Port)

    checker := NewHealthChecker(cfg)
    return checker.Check(ctx)
}

// Select 选择一个健康的实例
func (c *DiscoveryClient) Select(key ...string) (ServiceInstance, error) {
    c.mu.RLock()
    healthy := c.healthy
    c.mu.RUnlock()

    if len(healthy) == 0 {
        return ServiceInstance{}, fmt.Errorf("没有可用的健康实例")
    }

    if c.balancer != nil {
        return c.balancer.Select(healthy)
    }

    // 一致性哈希
    if len(key) > 0 && c.config.LBStrategy == "consistent-hash" {
        ch := New(150)
        for _, inst := range healthy {
            ch.Add(inst.ID)
        }
        nodeID, err := ch.Get(key[0])
        if err != nil {
            return ServiceInstance{}, err
        }
        for _, inst := range healthy {
            if inst.ID == nodeID {
                return inst, nil
            }
        }
    }

    // 默认随机
    return NewRandomBalancer().Select(healthy)
}

// GetInstances 获取所有实例
func (c *DiscoveryClient) GetInstances() []ServiceInstance {
    c.mu.RLock()
    defer c.mu.RUnlock()
    return c.healthy
}

// Register 注册当前服务
func (c *DiscoveryClient) Register(ctx context.Context, instance ServiceInstance) error {
    return c.registry.Register(ctx, instance)
}

// Deregister 注销当前服务
func (c *DiscoveryClient) Deregister(ctx context.Context, instanceID string) error {
    return c.registry.Deregister(ctx, instanceID)
}

// 适配器实现（简化）
type ConsulAdapter struct {
    discoverer *ConsulDiscoverer
}

func NewConsulAdapter(addr, serviceName string) (*ConsulAdapter, error) {
    d, err := NewConsulDiscoverer(addr, serviceName)
    if err != nil {
        return nil, err
    }
    return &ConsulAdapter{discoverer: d}, nil
}

func (a *ConsulAdapter) Discover(ctx context.Context) ([]ServiceInstance, error) {
    consulInstances, err := a.discoverer.Discover(ctx)
    if err != nil {
        return nil, err
    }
    var instances []ServiceInstance
    for _, ci := range consulInstances {
        instances = append(instances, ServiceInstance{
            ID:      ci.ID,
            Address: ci.Address,
            Port:    ci.Port,
        })
    }
    return instances, nil
}

func (a *ConsulAdapter) Watch(ctx context.Context) (<-chan []ServiceInstance, error) {
    ch := a.discoverer.Watch(ctx)
    outCh := make(chan []ServiceInstance)
    go func() {
        for instances := range ch {
            var out []ServiceInstance
            for _, ci := range instances {
                out = append(out, ServiceInstance{
                    ID:      ci.ID,
                    Address: ci.Address,
                    Port:    ci.Port,
                })
            }
            outCh <- out
        }
    }()
    return outCh, nil
}

func (a *ConsulAdapter) Register(ctx context.Context, instance ServiceInstance) error {
    return nil // 简化实现
}

func (a *ConsulAdapter) Deregister(ctx context.Context, instanceID string) error {
    return nil
}

type EtcdAdapter struct {
    discoverer *EtcdDiscoverer
}

func NewEtcdAdapter(endpoints []string, serviceName string) (*EtcdAdapter, error) {
    d, err := NewEtcdDiscoverer(endpoints, serviceName)
    if err != nil {
        return nil, err
    }
    return &EtcdAdapter{discoverer: d}, nil
}

func (a *EtcdAdapter) Discover(ctx context.Context) ([]ServiceInstance, error) {
    etcdInstances, err := a.discoverer.Discover(ctx)
    if err != nil {
        return nil, err
    }
    var instances []ServiceInstance
    for _, ei := range etcdInstances {
        instances = append(instances, ServiceInstance{
            ID:      ei.ID,
            Address: ei.Address,
            Port:    ei.Port,
        })
    }
    return instances, nil
}

func (a *EtcdAdapter) Watch(ctx context.Context) (<-chan []ServiceInstance, error) {
    outCh := make(chan []ServiceInstance)
    go a.discoverer.Watch(ctx)
    return outCh, nil
}

func (a *EtcdAdapter) Register(ctx context.Context, instance ServiceInstance) error {
    return a.discoverer.Register(ctx, EtcdInstance{
        ID:      instance.ID,
        Address: instance.Address,
        Port:    instance.Port,
    }, 30*time.Second)
}

func (a *EtcdAdapter) Deregister(ctx context.Context, instanceID string) error {
    return a.discoverer.Deregister(ctx, instanceID)
}

type DNSAdapter struct {
    discoverer *DNSDiscoverer
}

func NewDNSAdapter(domain string, ttl time.Duration) *DNSAdapter {
    return &DNSAdapter{
        discoverer: NewDNSDiscoverer(domain, ttl),
    }
}

func (a *DNSAdapter) Discover(ctx context.Context) ([]ServiceInstance, error) {
    dnsInstances, err := a.discoverer.Discover(ctx)
    if err != nil {
        return nil, err
    }
    var instances []ServiceInstance
    for _, di := range dnsInstances {
        instances = append(instances, ServiceInstance{
            ID:      fmt.Sprintf("%s:%d", di.Host, di.Port),
            Address: di.Host,
            Port:    di.Port,
            Weight:  di.Weight,
        })
    }
    return instances, nil
}

func (a *DNSAdapter) Watch(ctx context.Context) (<-chan []ServiceInstance, error) {
    outCh := make(chan []ServiceInstance)
    go func() {
        ticker := time.NewTicker(30 * time.Second)
        defer ticker.Stop()
        for {
            select {
            case <-ctx.Done():
                return
            case <-ticker.C:
                instances, err := a.Discover(ctx)
                if err == nil {
                    outCh <- instances
                }
            }
        }
    }()
    return outCh, nil
}

func (a *DNSAdapter) Register(ctx context.Context, instance ServiceInstance) error {
    return fmt.Errorf("DNS 适配器不支持注册")
}

func (a *DNSAdapter) Deregister(ctx context.Context, instanceID string) error {
    return fmt.Errorf("DNS 适配器不支持注销")
}
```

---

## 💻 实战练习

### 练习 1：实现本地文件配置的服务发现

```go
// 任务：实现一个基于配置文件的服务发现
// 配置文件格式 (services.json):
// {
//   "services": {
//     "web-api": {
//       "instances": [
//         {"id": "web-1", "address": "10.0.0.1", "port": 8080, "weight": 3},
//         {"id": "web-2", "address": "10.0.0.2", "port": 8080, "weight": 2}
//       ]
//     }
//   }
// }
//
// 要求：
// 1. 实现 RegistryAdapter 接口
// 2. 支持热重载（监听文件变化）
// 3. 支持健康检查
package servicediscovery

type FileRegistryAdapter struct {
    // 实现
}
```

### 练习 2：实现一致性哈希的有界负载版本

```go
// 任务：实现有界负载一致性哈希（Bounded-Load Consistent Hashing）
// 论文：https://research.googleblog.com/2017/04/consistent-hashing-with-bounded-loads.html
//
// 核心思想：在一致性哈希的基础上，限制每个节点的最大负载
// 如果首选节点负载已满，尝试下一个节点
package consistent

type BoundedLoadConsistentHash struct {
    // 基础一致性哈希
    ch *ConsistentHash

    // 每个节点的当前负载
    loads map[string]int

    // 平均负载的倍数上限
    epsilon float64
}

func (b *BoundedLoadConsistentHash) Get(key string) (string, error) {
    // 实现有界负载选择逻辑
    return "", nil
}
```

### 练习 3：编写完整的服务发现集成测试

```go
// 任务：编写集成测试，验证以下场景：
// 1. 服务注册和发现
// 2. 实例上下线通知
// 3. 健康检查失败后的实例剔除
// 4. 负载均衡分布均匀性
// 5. 一致性哈希的稳定性
package servicediscovery

func TestDiscoveryIntegration(t *testing.T) {
    // 设置测试环境（使用内存实现的 RegistryAdapter）
    // 测试完整流程
}
```

---

## 🎯 面试题精选

### 1. 服务发现的核心组件是什么？

**参考答案：**
服务发现的核心组件包括：
- **服务注册中心**：存储服务实例信息（Consul、etcd、ZooKeeper）
- **服务注册**：服务启动时向注册中心注册自己的地址和端口
- **健康检查**：定期检测服务实例是否健康
- **服务发现**：客户端从注册中心获取服务实例列表
- **负载均衡**：从实例列表中选择一个实例进行调用

### 2. 一致性哈希解决了什么问题？

**参考答案：**
一致性哈希解决了传统哈希（取模）在节点增减时大量数据迁移的问题。传统方式 `hash(key) % N`，当 N 变化时，几乎所有 key 的映射都会改变。一致性哈希将节点和 key 映射到同一个哈希环上，节点增减时只有少量 key 需要迁移（约 1/N）。

### 3. 虚拟节点的作用是什么？

**参考答案：**
虚拟节点解决数据分布不均匀的问题。在一致性哈希中，如果节点数量少，可能出现某些节点承担大量请求。虚拟节点让每个物理节点对应多个虚拟节点（如 100-200 个），在哈希环上分布更均匀，从而使请求分配更平衡。

### 4. Consul 和 etcd 的区别？

**参考答案：**
- **Consul**：原生支持服务发现、健康检查、KV 存储、多数据中心，API 更丰富
- **etcd**：通用分布式键值存储，使用 Raft 共识，更轻量，Kubernetes 使用 etcd
- 选择建议：需要完整服务发现功能用 Consul，需要简单 KV 存储或与 K8s 集成用 etcd

### 5. 客户端发现和服务端发现的区别？

**参考答案：**
- **客户端发现**：客户端直接查询注册中心，获取实例列表后自己做负载均衡（如 Eureka + Ribbon）
- **服务端发现**：客户端通过负载均衡器/代理访问服务，负载均衡器查询注册中心（如 K8s Service、AWS ELB）
- 客户端发现延迟更低但客户端逻辑更复杂；服务端发现客户端简单但多一跳

### 6. 如何处理服务注册中心自身的高可用？

**参考答案：**
- Consul：部署 3-5 个 Server 节点，使用 Raft 共识
- etcd：部署 3-5 个节点的集群，使用 Raft 共识
- 避免脑裂：使用奇数个节点
- 跨数据中心：Consul 原生支持，etcd 需要额外配置
- 客户端缓存：服务发现客户端缓存实例列表，注册中心不可用时使用缓存

### 7. 健康检查失败后应该怎么处理？

**参考答案：**
- 设置失败阈值：连续 N 次失败才标记为不健康，避免网络抖动导致误判
- 设置恢复阈值：连续 M 次成功才标记为健康
- 渐进式流量切换：不健康实例先减少流量，而不是立即摘除
- 告警通知：健康检查失败时发送告警
- 自动摘除：超过阈值后从注册中心注销

### 8. 最少连接和轮询策略的适用场景？

**参考答案：**
- **轮询**：适用于请求处理时间相对均匀的场景，实现简单
- **最少连接**：适用于请求处理时间差异大的场景（如 CPU 密集型和 IO 密集型混合），自动适应负载变化
- 最少连接需要维护每个实例的连接计数，有一定开销

### 9. 如何实现服务优雅下线？

**参考答案：**
1. 收到关闭信号（SIGTERM）
2. 停止接受新请求
3. 从注册中心注销服务
4. 等待现有请求处理完成（设置超时）
5. 关闭数据库连接等资源
6. 进程退出

关键是第 3 步要先于第 2 步通知注册中心，让客户端不再将新请求路由过来。

### 10. DNS 服务发现的优缺点？

**参考答案：**
- 优点：通用性强，任何语言和平台都支持 DNS；无需额外 SDK；兼容性好
- 缺点：DNS 缓存导致变更生效慢；TTL 设置是权衡（太短增加 DNS 服务器压力，太长变更不及时）；不支持丰富的元数据和健康检查
- 适用场景：简单的服务发现需求，或作为其他服务发现机制的补充

---

## 📚 深入阅读

- [Consul 官方文档](https://www.consul.io/docs)
- [etcd 官方文档](https://etcd.io/docs/)
- [Consistent Hashing 论文](https://www.cs.princeton.edu/courses/archive/fall07/cos518/papers/chash.pdf)
- [Google: Consistent Hashing with Bounded Loads](https://research.googleblog.com/2017/04/consistent-hashing-with-bounded-loads.html)
- [Microservices Patterns: Service Discovery](https://microservices.io/patterns/server-side-discovery.html)
- [Netflix Eureka 架构](https://github.com/Netflix/eureka/wiki/Eureka-at-a-glance)
- 《分布式系统：概念与设计》第 16 章：分布式文件系统

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出服务发现架构图，说明客户端发现和服务端发现的区别
- [ ] 能解释一致性哈希的原理、虚拟节点的作用
- [ ] 能对比 DNS、Consul、etcd 三种服务发现方式的优缺点
- [ ] 能说明健康检查的主动探测和被动通知模式

### 实操检查点
- [ ] 能实现基于 DNS 的服务发现
- [ ] 能实现 Consul/etcd 的服务注册和发现
- [ ] 能实现一致性哈希算法（含虚拟节点）
- [ ] 能实现多种负载均衡策略

### 能力验证标准
- [ ] 能设计完整的服务发现方案（注册、发现、健康检查、负载均衡）
- [ ] 能解释一致性哈希在分布式缓存中的应用
- [ ] 能编写并发安全的服务发现客户端
