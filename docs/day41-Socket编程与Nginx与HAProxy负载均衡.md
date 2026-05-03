# Day 41: Socket 编程与 Nginx/HAProxy 负载均衡

> 📅 日期：2026-05-02
> 📖 学习主题：Socket 编程基础、I/O 模型、Nginx/HAProxy 负载均衡
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 30 TCP 协议、Day 38 tcpdump、Day 40 HTTP/HTTPS

## 🎯 学习目标

- 理解 Socket 编程基础（TCP/UDP/Unix Socket）
- 掌握 I/O 模型（阻塞、非阻塞、I/O 多路复用 select/poll/epoll）
- 深入理解 Nginx 架构和反向代理配置
- 掌握负载均衡算法和健康检查
- 能排查 Nginx 502/504 等常见问题
- 理解 HAProxy 与 Nginx 的对比和选择

---

## 📖 核心知识点

### 1. Socket 编程基础

#### 1.1 什么是 Socket

Socket（套接字）是操作系统提供的**网络通信端点抽象**，是进程间网络通信的基础。

```
客户端 Socket                    服务端 Socket
   │                                │
   ├── socket() ────────────────────┤  创建套接字
   │                                ├── bind()      绑定地址
   │                                ├── listen()    开始监听
   ├── connect() ──────────────────►│  建立连接
   │                                ├── accept()    接受连接
   │                                │
   ├── send()/write() ────────────►│  发送数据
   │                                ├── recv()/read()  接收数据
   │                                │
   │◄─────────────────── send() ───┤  发送响应
   ├── recv()/read() ──────────────┤
   │                                │
   ├── close() ─────────────────────┤  关闭连接
```

#### 1.2 Socket 类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| SOCK_STREAM | 面向连接的可靠传输（TCP） | HTTP、数据库连接、文件传输 |
| SOCK_DGRAM | 无连接的不可靠传输（UDP） | DNS 查询、视频流、游戏 |
| SOCK_RAW | 原始套接字 | 抓包（tcpdump）、自定义协议 |
| AF_UNIX | 本地进程间通信 | Docker Socket、进程间通信 |

#### 1.3 TCP Socket 编程示例

```python
# TCP 服务端
import socket

# 1. 创建 Socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. 允许端口复用
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 3. 绑定地址
server.bind(('0.0.0.0', 8080))

# 4. 开始监听（backlog=128）
server.listen(128)
print("Server listening on :8080")

while True:
    # 5. 接受连接
    client, addr = server.accept()
    print(f"Connection from {addr}")

    # 6. 接收数据
    data = client.recv(4096)
    print(f"Received: {data.decode()}")

    # 7. 发送响应
    client.send(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nHello")

    # 8. 关闭连接
    client.close()
```

```python
# TCP 客户端
import socket

# 1. 创建 Socket
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. 连接服务器
client.connect(('127.0.0.1', 8080))

# 3. 发送数据
client.send(b"Hello, Server!")

# 4. 接收响应
data = client.recv(4096)
print(f"Received: {data.decode()}")

# 5. 关闭
client.close()
```

#### 1.4 Unix Socket 示例

```python
# Unix Socket 服务端
import socket
import os

SOCKET_PATH = "/tmp/myapp.sock"

# 清理旧的 socket 文件
if os.path.exists(SOCKET_PATH):
    os.unlink(SOCKET_PATH)

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(SOCKET_PATH)
server.listen(5)

while True:
    client, _ = server.accept()
    data = client.recv(4096)
    client.send(b"Pong")
    client.close()
```

**Unix Socket 优势**：
- 不经过网络协议栈，性能更高
- 使用文件系统权限控制访问
- 适合同一主机上的进程间通信

**SRE 常见场景**：
- Nginx 与 PHP-FPM 通过 Unix Socket 通信
- Docker 守护进程的 `/var/run/docker.sock`
- PostgreSQL 的 `/var/run/postgresql/.s.PGSQL.5432`

---

### 2. I/O 模型

#### 2.1 五种 I/O 模型

```
┌─────────────────────────────────────────────────────────────────┐
│                    I/O 模型对比                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 阻塞 I/O (Blocking I/O)                                    │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│     │ 等待数据  │───→│ 数据拷贝  │───→│ 处理数据  │               │
│     │ (阻塞)   │    │ (阻塞)   │    │          │               │
│     └──────────┘    └──────────┘    └──────────┘               │
│                                                                 │
│  2. 非阻塞 I/O (Non-blocking I/O)                              │
│     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│     │ 检查数据  │→│ 检查数据  │→│ 检查数据  │→│ 数据拷贝  │       │
│     │ (无数据) │ │ (无数据) │ │ (有数据) │ │          │       │
│     └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│     (轮询，CPU 空转)                                            │
│                                                                 │
│  3. I/O 多路复用 (I/O Multiplexing)                            │
│     ┌──────────────────────────────┐    ┌──────────┐           │
│     │ select/poll/epoll 等待       │───→│ 数据拷贝  │           │
│     │ (同时监听多个 fd)             │    │          │           │
│     └──────────────────────────────┘    └──────────┘           │
│                                                                 │
│  4. 信号驱动 I/O (Signal-driven I/O)                           │
│     ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│     │ 注册信号  │───→│ 等待信号  │───→│ 数据拷贝  │               │
│     └──────────┘    │ (非阻塞) │    └──────────┘               │
│                     └──────────┘                                │
│                                                                 │
│  5. 异步 I/O (Asynchronous I/O)                                │
│     ┌──────────┐    ┌──────────────────────┐                   │
│     │ 发起请求  │───→│ 内核完成数据拷贝后通知│                   │
│     │ (非阻塞) │    │ (全程非阻塞)          │                   │
│     └──────────┘    └──────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 select/poll/epoll 对比

| 特性 | select | poll | epoll |
|------|--------|------|-------|
| 数据结构 | fd_set（位图） | pollfd 数组 | 红黑树 + 就绪链表 |
| 最大连接数 | FD_SETSIZE (1024) | 无限制 | 无限制 |
| 检查方式 | 线性扫描 | 线性扫描 | 回调通知 |
| 时间复杂度 | O(n) | O(n) | O(1) |
| fd 拷贝 | 每次调用都拷贝 | 每次调用都拷贝 | 注册一次，无需拷贝 |
| 触发模式 | 水平触发 | 水平触发 | 水平/边缘触发 |
| 性能 | 连接多时差 | 连接多时差 | 连接多时优秀 |

**select 的问题**：

```c
// select 最大监听 FD_SETSIZE = 1024
fd_set read_fds;
FD_ZERO(&read_fds);
FD_SET(fd1, &read_fds);
FD_SET(fd2, &read_fds);

// 每次调用都需要拷贝整个 fd_set 到内核
// 内核需要线性扫描所有 fd 检查状态
select(max_fd + 1, &read_fds, NULL, NULL, NULL);
```

**epoll 的优势**：

```c
// 创建 epoll 实例
int epfd = epoll_create1(0);

// 注册 fd（只需要一次）
struct epoll_event ev;
ev.events = EPOLLIN;
ev.data.fd = fd1;
epoll_ctl(epfd, EPOLL_CTL_ADD, fd1, &ev);

// 等待事件（只返回就绪的 fd）
struct epoll_event events[1024];
int nfds = epoll_wait(epfd, events, 1024, -1);
// nfds 是就绪的 fd 数量，不需要遍历所有 fd
```

**epoll 的触发模式**：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 水平触发 (LT) | 只要 fd 可读/可写就通知 | 默认模式，编程简单 |
| 边缘触发 (ET) | 只在状态变化时通知 | 高性能，需要一次性读完 |

```
水平触发 (Level Triggered)：
  数据到达 → 通知 → 没读完 → 继续通知 → 读完 → 停止通知

边缘触发 (Edge Triggered)：
  数据到达 → 通知 → 没读完 → 不通知 → 新数据到达 → 通知
  (必须配合非阻塞 I/O，一次性读完所有数据)
```

---

### 3. Nginx 深入

#### 3.1 Nginx 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Nginx 进程模型                            │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    Master 进程                           │   │
│   │  - 读取配置文件                                          │   │
│   │  - 管理 Worker 进程                                      │   │
│   │  - 处理信号（reload、stop）                               │   │
│   └──────────────────────────┬──────────────────────────────┘   │
│                              │                                  │
│          ┌───────────────────┼───────────────────┐              │
│          │                   │                   │              │
│          ▼                   ▼                   ▼              │
│   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐      │
│   │ Worker 进程 1│   │ Worker 进程 2│   │ Worker 进程 N│      │
│   │  (epoll)     │   │  (epoll)     │   │  (epoll)     │      │
│   │  事件驱动    │   │  事件驱动    │   │  事件驱动    │      │
│   │  非阻塞 I/O  │   │  非阻塞 I/O  │   │  非阻塞 I/O  │      │
│   └──────────────┘   └──────────────┘   └──────────────┘      │
│          │                   │                   │              │
│          ▼                   ▼                   ▼              │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              共享内存（缓存、会话、限流）                  │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Nginx 高性能的关键**：
- **Master-Worker 模型**：Master 管理配置，Worker 处理请求
- **事件驱动**：基于 epoll 的异步非阻塞 I/O
- **每个 Worker 是单线程**：避免锁竞争，上下文切换少
- **连接数限制**：每个 Worker 最多处理 worker_connections 个连接

#### 3.2 Nginx 配置结构

```nginx
# /etc/nginx/nginx.conf

# 全局配置
user nginx;
worker_processes auto;              # 自动匹配 CPU 核心数
worker_rlimit_nofile 65535;         # 每个 Worker 最大文件描述符数
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 10240;       # 每个 Worker 最大连接数
    use epoll;                      # 使用 epoll
    multi_accept on;                # 一次 accept 多个连接
}

http {
    # 基础配置
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time';

    access_log /var/log/nginx/access.log main;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 1000;

    # 压缩
    gzip on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_vary on;

    # 引入其他配置
    include /etc/nginx/conf.d/*.conf;
}
```

#### 3.3 反向代理配置

```nginx
# /etc/nginx/conf.d/reverse-proxy.conf

# 上游服务定义
upstream backend {
    # 负载均衡算法：默认轮询
    server 10.0.1.10:8080 weight=3;
    server 10.0.1.11:8080 weight=2;
    server 10.0.1.12:8080 weight=1;

    # 健康检查（被动）
    server 10.0.1.13:8080 backup;      # 备用服务器

    # 连接池
    keepalive 32;                       # 保持 32 个长连接
}

server {
    listen 80;
    server_name api.example.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL 配置
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # 反向代理
    location / {
        proxy_pass http://backend;

        # 传递客户端信息
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;

        # 超时配置
        proxy_connect_timeout 5s;       # 连接上游超时
        proxy_send_timeout 60s;         # 发送请求超时
        proxy_read_timeout 60s;         # 读取响应超时

        # 缓冲配置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;

        # 重试配置
        proxy_next_upstream error timeout http_502 http_503;
        proxy_next_upstream_tries 3;
        proxy_next_upstream_timeout 10s;

        # 长连接
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # 静态文件
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 3.4 负载均衡算法

| 算法 | 配置 | 说明 | 适用场景 |
|------|------|------|----------|
| 轮询 | 默认 | 依次分配请求 | 服务器性能相同 |
| 加权轮询 | `weight=N` | 按权重分配 | 服务器性能不同 |
| IP Hash | `ip_hash` | 同一 IP 固定到同一服务器 | 需要会话保持 |
| 最少连接 | `least_conn` | 分配到连接数最少的服务器 | 长连接场景 |
| 随机 | `random two least_conn` | 随机选择 | 通用 |

```nginx
# 轮询（默认）
upstream backend {
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
}

# 加权轮询
upstream backend {
    server 10.0.1.10:8080 weight=3;  # 接收 3/4 的请求
    server 10.0.1.11:8080 weight=1;  # 接收 1/4 的请求
}

# IP Hash（会话保持）
upstream backend {
    ip_hash;
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
}

# 最少连接
upstream backend {
    least_conn;
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
}

# Hash（自定义 key）
upstream backend {
    hash $request_uri consistent;  # 一致性哈希
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
}
```

#### 3.5 健康检查

```nginx
# 被动健康检查（Nginx 开源版）
upstream backend {
    server 10.0.1.10:8080 max_fails=3 fail_timeout=30s;
    # max_fails: 最大失败次数
    # fail_timeout: 失败后暂停时间
    server 10.0.1.11:8080 max_fails=3 fail_timeout=30s;
}

# 主动健康检查（Nginx Plus 商业版）
# upstream backend {
#     zone backend 64k;
#     server 10.0.1.10:8080;
#     server 10.0.1.11:8080;
# }
#
# server {
#     location / {
#         proxy_pass http://backend;
#         health_check interval=5s fails=3 passes=2 uri=/health;
#     }
# }
```

#### 3.6 性能调优

```nginx
# /etc/nginx/nginx.conf

# Worker 进程数（匹配 CPU 核心数）
worker_processes auto;

# 每个 Worker 最大连接数
events {
    worker_connections 10240;
    use epoll;
    multi_accept on;
}

http {
    # 开启 sendfile（零拷贝）
    sendfile on;
    tcp_nopush on;      # 合并小包
    tcp_nodelay on;     # 禁用 Nagle 算法

    # Keep-Alive
    keepalive_timeout 65;
    keepalive_requests 1000;

    # 缓冲区
    client_body_buffer_size 16k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;
    client_max_body_size 100m;

    # 代理缓冲
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 16k;
    proxy_busy_buffers_size 32k;

    # 文件缓存
    open_file_cache max=10000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
}
```

#### 3.7 日志配置和分析

```nginx
# 自定义日志格式
log_format json_combined escape=json
  '{'
    '"time":"$time_iso8601",'
    '"remote_addr":"$remote_addr",'
    '"request":"$request",'
    '"status":$status,'
    '"body_bytes_sent":$body_bytes_sent,'
    '"request_time":$request_time,'
    '"upstream_response_time":"$upstream_response_time",'
    '"http_referer":"$http_referer",'
    '"http_user_agent":"$http_user_agent",'
    '"request_id":"$request_id"'
  '}';

access_log /var/log/nginx/access.log json_combined;

# 日志轮转（logrotate）
# /etc/logrotate.d/nginx
# /var/log/nginx/*.log {
#     daily
#     missingok
#     rotate 14
#     compress
#     delaycompress
#     notifempty
#     create 0640 nginx adm
#     sharedscripts
#     postrotate
#         [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
#     endscript
# }
```

```bash
# 日志分析常用命令

# 统计状态码分布
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# 统计请求时间最长的 URL
awk '{print $7, $NF}' /var/log/nginx/access.log | sort -k2 -rn | head -20

# 统计每秒请求数（QPS）
awk '{print $4}' /var/log/nginx/access.log | cut -c14-21 | uniq -c

# 统计 IP 访问量
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# 统计 5xx 错误
awk '$9 >= 500 && $9 < 600' /var/log/nginx/access.log | wc -l

# 实时监控 QPS
tail -f /var/log/nginx/access.log | pv -l -i 1 -r > /dev/null
```

---

### 4. HAProxy 深入

#### 4.1 HAProxy 简介

HAProxy 是一个高性能的 TCP/HTTP 负载均衡器和代理服务器，专注于高可用性和高性能。

#### 4.2 Nginx vs HAProxy 对比

| 特性 | Nginx | HAProxy |
|------|-------|---------|
| 主要功能 | Web 服务器 + 反向代理 | 专业负载均衡器 |
| 四层负载 | 支持（stream 模块） | 原生支持，更强大 |
| 七层负载 | 支持 | 支持，ACL 更灵活 |
| 健康检查 | 被动（开源版） | 主动 + 被动 |
| 会话保持 | ip_hash、sticky cookie | 多种方式 |
| 统计页面 | 商业版 | 内置（免费） |
| 配置热加载 | reload | reload |
| 性能 | 极高 | 极高（专注代理） |
| 学习曲线 | 中等 | 中等 |
| 适用场景 | Web 服务器 + 反向代理 | 专业负载均衡 |

#### 4.3 HAProxy 配置

```bash
# 安装
sudo apt-get install -y haproxy  # Debian/Ubuntu
sudo yum install -y haproxy      # RHEL/CentOS

# 配置文件
sudo nano /etc/haproxy/haproxy.cfg
```

```bash
# /etc/haproxy/haproxy.cfg

global
    # 进程管理
    daemon
    nbthread 4                      # 线程数
    maxconn 50000                   # 最大连接数

    # 日志
    log /dev/log local0
    log /dev/log local1 notice

    # 统计 socket
    stats socket /var/run/haproxy.sock mode 660 level admin

    # SSL 证书
    ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256
    ssl-default-bind-options ssl-min-ver TLSv1.2

defaults
    # 全局默认
    mode http
    log global
    option httplog
    option dontlognull
    option forwardfor
    option http-server-close

    # 超时
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    timeout http-request 10s
    timeout http-keep-alive 10s
    timeout queue 30s
    timeout check 5s

    # 重试
    retries 3
    option redispatch

    # 错误页面
    errorfile 400 /etc/haproxy/errors/400.http
    errorfile 403 /etc/haproxy/errors/403.http
    errorfile 500 /etc/haproxy/errors/500.http
    errorfile 502 /etc/haproxy/errors/502.http
    errorfile 503 /etc/haproxy/errors/503.http

# ===== 前端（接收请求） =====
frontend http-in
    bind *:80
    bind *:443 ssl crt /etc/haproxy/certs/

    # ACL 规则
    acl is_api path_beg /api/
    acl is_static path_end .css .js .png .jpg
    acl is_websocket hdr(Upgrade) -i websocket

    # 路由规则
    use_backend api_servers if is_api
    use_backend static_servers if is_static
    use_backend ws_servers if is_websocket
    default_backend web_servers

# ===== 后端（处理请求） =====
backend web_servers
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200

    server web1 10.0.1.10:8080 check inter 5s fall 3 rise 2 weight 3
    server web2 10.0.1.11:8080 check inter 5s fall 3 rise 2 weight 2
    server web3 10.0.1.12:8080 check inter 5s fall 3 rise 2 backup

backend api_servers
    balance leastconn
    option httpchk GET /api/health
    http-check expect status 200

    # Cookie 会话保持
    cookie SERVERID insert indirect nocache

    server api1 10.0.1.20:9090 check cookie api1
    server api2 10.0.1.21:9090 check cookie api2

backend static_servers
    balance uri                     # 按 URI 哈希（缓存友好）
    server static1 10.0.1.30:80 check
    server static2 10.0.1.31:80 check

backend ws_servers
    balance source                  # 按源 IP（WebSocket 会话保持）
    option httpchk GET /ws/health
    timeout server 3600s            # WebSocket 长连接超时
    timeout tunnel 3600s

    server ws1 10.0.1.40:8081 check
    server ws2 10.0.1.41:8081 check

# ===== 四层（TCP）负载均衡 =====
frontend mysql-in
    mode tcp
    bind *:3306
    default_backend mysql_servers

backend mysql_servers
    mode tcp
    balance roundrobin
    option mysql-check user haproxy

    server mysql1 10.0.1.50:3306 check
    server mysql2 10.0.1.51:3306 check

# ===== 统计页面 =====
listen stats
    bind *:8404
    mode http
    stats enable
    stats uri /stats
    stats refresh 10s
    stats auth admin:password
    stats admin if TRUE
```

#### 4.4 HAProxy 负载均衡算法

| 算法 | 配置 | 说明 | 适用场景 |
|------|------|------|----------|
| 轮询 | `roundrobin` | 依次分配 | 通用 |
| 加权轮询 | `roundrobin` + weight | 按权重分配 | 服务器性能不同 |
| 最少连接 | `leastconn` | 分配到连接数最少的 | 长连接 |
| 源地址哈希 | `source` | 同一源 IP 到同一服务器 | 会话保持 |
| URI 哈希 | `uri` | 同一 URI 到同一服务器 | 缓存友好 |
| HTTP Header | `hdr(name)` | 按头部值哈希 | 按租户路由 |
| 随机 | `random` | 随机选择 | 通用 |

#### 4.5 HAProxy 健康检查

```bash
# HTTP 健康检查
option httpchk GET /health
http-check expect status 200

# TCP 健康检查（默认）
option tcp-check

# MySQL 健康检查
option mysql-check user haproxy

# Redis 健康检查
option redis-check

# 自定义检查间隔
server web1 10.0.1.10:8080 check inter 5s fall 3 rise 2
# inter: 检查间隔
# fall: 连续失败次数后标记为 down
# rise: 连续成功次数后标记为 up
```

#### 4.6 HAProxy 统计页面

```bash
# 访问统计页面
curl -u admin:password http://localhost:8404/stats

# 通过 Unix Socket 管理
echo "show stat" | socat stdio /var/run/haproxy.sock
echo "show info" | socat stdio /var/run/haproxy.sock

# 动态上下线服务器
echo "set server web_servers/web1 state drain" | socat stdio /var/run/haproxy.sock
echo "set server web_servers/web1 state ready" | socat stdio /var/run/haproxy.sock
```

---

### 5. 四层 vs 七层负载均衡

| 维度 | 四层（L4） | 七层（L7） |
|------|-----------|-----------|
| 工作层级 | 传输层（TCP/UDP） | 应用层（HTTP） |
| 路由依据 | IP + 端口 | URL、Header、Cookie 等 |
| 性能 | 更高（不解析应用层） | 稍低（需要解析 HTTP） |
| 功能 | 简单转发 | 内容路由、缓存、压缩 |
| 适用场景 | 数据库、Redis、自定义协议 | Web 应用、API、微服务 |
| Nginx 配置 | stream 模块 | http 模块 |
| HAProxy 配置 | mode tcp | mode http |

```nginx
# Nginx 四层负载均衡（stream 模块）
stream {
    upstream mysql_backend {
        server 10.0.1.50:3306;
        server 10.0.1.51:3306;
    }

    server {
        listen 3306;
        proxy_pass mysql_backend;
    }
}

# Nginx 七层负载均衡（http 模块）
http {
    upstream web_backend {
        server 10.0.1.10:8080;
        server 10.0.1.11:8080;
    }

    server {
        listen 80;
        location / {
            proxy_pass http://web_backend;
        }
    }
}
```

---

### 6. SRE 实战案例

#### 6.1 案例一：Nginx "Too many open files"

**背景**：Nginx 错误日志出现 `worker_connections are not enough` 和 `too many open files`。

```bash
# 步骤 1：查看 Nginx 错误日志
sudo tail -f /var/log/nginx/error.log
# [alert] 1234#1234: 1024 worker_connections are not enough
# [crit] 1234#1234: accept() failed (24: Too many open files)

# 步骤 2：查看当前限制
ulimit -n
# 1024（默认值太低）

# 步骤 3：查看 Nginx Worker 的限制
cat /proc/$(pgrep -f "nginx: worker" | head -1)/limits | grep "Max open files"
# Max open files            1024                 1048576              files

# 步骤 4：调整系统限制
# /etc/security/limits.conf
# nginx soft nofile 65535
# nginx hard nofile 65535

# /etc/nginx/nginx.conf
# worker_rlimit_nofile 65535;
# events {
#     worker_connections 10240;
# }

# 步骤 5：调整 systemd 限制
# /etc/systemd/system/nginx.service.d/override.conf
# [Service]
# LimitNOFILE=65535

# 步骤 6：重载配置
sudo systemctl daemon-reload
sudo systemctl reload nginx

# 步骤 7：验证
cat /proc/$(pgrep -f "nginx: worker" | head -1)/limits | grep "Max open files"
# Max open files            65535                65535                files
```

#### 6.2 案例二：负载不均

**背景**：三台后端服务器，其中一台 CPU 使用率 90%，另外两台只有 30%。

```bash
# 步骤 1：检查 Nginx 负载均衡配置
cat /etc/nginx/conf.d/upstream.conf
# upstream backend {
#     server 10.0.1.10:8080;
#     server 10.0.1.11:8080;
#     server 10.0.1.12:8080;
# }

# 问题：默认轮询算法，但某些请求（如 WebSocket）是长连接，
# 一旦建立就不会切换到其他服务器

# 步骤 2：查看各服务器连接数
for ip in 10.0.1.10 10.0.1.11 10.0.1.12; do
    echo -n "$ip: "
    ss -s | grep -i estab  # 在各服务器上执行
done

# 步骤 3：调整负载均衡算法
# 如果是长连接场景，使用 least_conn
upstream backend {
    least_conn;
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
    server 10.0.1.12:8080;
}

# 步骤 4：重载配置
sudo nginx -t && sudo systemctl reload nginx

# 步骤 5：验证负载均衡效果
# 使用 curl 测试
for i in $(seq 1 100); do
    curl -s http://api.example.com/whoami
done | sort | uniq -c
```

#### 6.3 案例三：Nginx 502/504 排查

```bash
# ===== 502 Bad Gateway =====
# 原因：上游服务不可达

# 检查 Nginx 错误日志
sudo grep "502" /var/log/nginx/error.log | tail -5
# upstream prematurely closed connection while reading response header

# 检查上游服务
curl -s http://10.0.1.10:8080/health
# 如果返回连接拒绝 → 服务未启动
# 如果返回超时 → 服务过载

# 检查端口
ss -tlnp | grep 8080

# ===== 504 Gateway Timeout =====
# 原因：上游响应超时

# 检查超时配置
grep -E "proxy_read_timeout|proxy_connect_timeout" /etc/nginx/conf.d/*.conf

# 调整超时
location /api/ {
    proxy_pass http://backend;
    proxy_read_timeout 120s;      # 从 60s 增加到 120s
    proxy_connect_timeout 10s;
}

# 检查上游服务性能
# 可能需要优化查询、增加缓存等
```

---

## 💻 实战练习

### 练习 1：编写简单的 TCP 服务器

```python
#!/usr/bin/env python3
# simple_tcp_server.py

import socket
import threading

def handle_client(client, addr):
    print(f"Connection from {addr}")
    try:
        while True:
            data = client.recv(4096)
            if not data:
                break
            print(f"Received from {addr}: {data.decode()}")
            client.send(f"Echo: {data.decode()}".encode())
    except ConnectionResetError:
        pass
    finally:
        client.close()
        print(f"Connection closed: {addr}")

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 8080))
server.listen(128)
print("Server listening on :8080")

while True:
    client, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(client, addr))
    thread.daemon = True
    thread.start()
```

### 练习 2：配置 Nginx 反向代理

```bash
# 1. 安装 Nginx
sudo apt-get install -y nginx

# 2. 创建配置
sudo tee /etc/nginx/conf.d/proxy.conf > /dev/null << 'EOF'
upstream backend {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# 3. 测试配置
sudo nginx -t

# 4. 重载
sudo systemctl reload nginx

# 5. 测试
curl -I http://localhost/
```

### 练习 3：配置 HAProxy 负载均衡

```bash
# 1. 安装 HAProxy
sudo apt-get install -y haproxy

# 2. 配置
sudo tee /etc/haproxy/haproxy.cfg > /dev/null << 'EOF'
global
    daemon
    maxconn 10000

defaults
    mode http
    timeout connect 5s
    timeout client 30s
    timeout server 30s

frontend http-in
    bind *:8080
    default_backend web_servers

backend web_servers
    balance roundrobin
    option httpchk GET /health
    server web1 127.0.0.1:9001 check
    server web2 127.0.0.1:9002 check

listen stats
    bind *:8404
    stats enable
    stats uri /stats
EOF

# 3. 启动后端服务
python3 -m http.server 9001 &
python3 -m http.server 9002 &

# 4. 启动 HAProxy
sudo systemctl restart haproxy

# 5. 测试
for i in $(seq 1 10); do curl -s http://localhost:8080/; done

# 6. 查看统计页面
curl -s http://localhost:8404/stats
```

---

## 🎯 面试题精选

### Q1：Nginx 和 HAProxy 应该如何选择？

**参考答案**：

| 场景 | 推荐 | 原因 |
|------|------|------|
| Web 服务器 + 反向代理 | Nginx | 能同时处理静态文件和代理 |
| 专业负载均衡 | HAProxy | 功能更专业，ACL 更灵活 |
| 四层负载均衡 | HAProxy | 原生支持，性能更好 |
| 需要统计页面 | HAProxy | 内置免费统计页面 |
| 已有 Nginx | Nginx | 不需要额外组件 |
| WebSocket | 两者都行 | 都支持 |

**简单原则**：如果只需要做 Web 服务器 + 反向代理，用 Nginx。如果需要专业负载均衡（特别是四层），用 HAProxy。

### Q2：epoll 的原理是什么？为什么比 select 高效？

**参考答案**：

epoll 使用**红黑树**管理所有注册的 fd，使用**就绪链表**存储就绪的 fd。

**高效原因**：
1. **事件注册**：fd 只需要注册一次（select 每次都要拷贝）
2. **回调通知**：当 fd 就绪时，通过回调函数加入就绪链表（select 需要遍历所有 fd）
3. **只返回就绪的 fd**：epoll_wait 只返回就绪的 fd（select 返回所有 fd，需要遍历）

**时间复杂度**：
- select/poll：O(n)，n 是 fd 数量
- epoll：O(1)，只处理就绪的 fd

### Q3：四层和七层负载均衡的区别是什么？

**参考答案**：

- **四层**：工作在传输层（TCP/UDP），根据 IP + 端口转发，不解析应用层数据
  - 优点：性能高、支持任何 TCP/UDP 协议
  - 缺点：不能根据内容路由

- **七层**：工作在应用层（HTTP），可以根据 URL、Header、Cookie 等路由
  - 优点：功能强大、支持内容路由、缓存、压缩
  - 缺点：性能稍低（需要解析 HTTP）

**选择**：
- 数据库、Redis 等：四层
- Web 应用、API：七层
- 需要按 URL 路由：七层
- 需要最高性能：四层

### Q4：Nginx 的 502 和 504 分别是什么原因？如何排查？

**参考答案**：

**502 Bad Gateway**：Nginx 从上游收到无效响应
- 原因：上游服务崩溃、端口未监听、连接被拒绝
- 排查：`curl http://upstream:port/health`，检查服务状态

**504 Gateway Timeout**：Nginx 等待上游响应超时
- 原因：上游处理太慢、查询超时
- 排查：检查 `proxy_read_timeout` 配置，检查上游性能

### Q5：Nginx 如何实现会话保持（Sticky Session）？

**参考答案**：

```nginx
# 方法 1：ip_hash（开源版）
upstream backend {
    ip_hash;
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
}

# 方法 2：hash（一致性哈希）
upstream backend {
    hash $cookie_jsessionid consistent;
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
}

# 方法 3：sticky（Nginx Plus 商业版）
# upstream backend {
#     sticky cookie srv_id expires=1h;
#     server 10.0.1.10:8080;
#     server 10.0.1.11:8080;
# }
```

**建议**：优先使用无状态设计（共享 Session 存储），避免会话保持。

---

## 📚 深入阅读

| 资源 | 链接 |
|------|------|
| Nginx 官方文档 | https://nginx.org/en/docs/ |
| Nginx 负载均衡 | https://nginx.org/en/docs/http/load_balancing.html |
| HAProxy 官方文档 | https://www.haproxy.org/#docs |
| HAProxy 配置手册 | https://www.haproxy.org/download/2.8/doc/configuration.txt |
| epoll 原理 | https://man7.org/linux/man-pages/man7/epoll.7.html |
| 《Unix Network Programming》 | W. Richard Stevens 著，网络编程经典 |

---

## ✅ 自检清单

- [ ] 理解 Socket 编程基础（TCP/UDP/Unix Socket）
- [ ] 掌握 I/O 模型（阻塞、非阻塞、I/O 多路复用）
- [ ] 理解 epoll 的原理和优势
- [ ] 掌握 Nginx 的架构（Master/Worker、事件驱动）
- [ ] 能配置 Nginx 反向代理和负载均衡
- [ ] 掌握负载均衡算法（轮询、加权、IP Hash、最少连接）
- [ ] 能配置 HAProxy 负载均衡
- [ ] 理解四层 vs 七层负载均衡的区别
- [ ] 能排查 Nginx 502/504 错误
- [ ] 能调整 Nginx 性能参数（worker_connections、ulimit）
