# Day 40: HTTP/HTTPS 协议深入

> 📅 日期：2026-05-02
> 📖 学习主题：HTTP/HTTPS 协议深入 — 从报文结构到 TLS 握手
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 30 TCP 协议、Day 35 从 URL 到页面

## 🎯 学习目标

- 深入理解 HTTP 请求/响应报文结构
- 掌握 HTTP 方法语义、状态码含义、请求头/响应头详解
- 理解 HTTP/1.0 → HTTP/1.1 → HTTP/2 → HTTP/3 的演进
- 掌握 TLS 握手流程（RSA vs ECDHE）和证书验证链
- 理解 HTTP 缓存机制（强缓存 vs 协商缓存）
- 能独立排查 HTTPS 证书问题和 HTTP 缓存问题

---

## 📖 核心知识点

### 1. HTTP 协议深入

#### 1.1 HTTP 请求报文结构

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP 请求报文                              │
├─────────────────────────────────────────────────────────────┤
│ 请求行 (Request Line)                                        │
│   GET /api/users?page=1 HTTP/1.1                            │
│   │       │               │                                  │
│   │       │               └─ HTTP 版本                        │
│   │       └─ 请求 URI（路径 + 查询参数）                      │
│   └─ 请求方法                                                 │
├─────────────────────────────────────────────────────────────┤
│ 请求头 (Request Headers)                                     │
│   Host: api.example.com                                     │
│   User-Agent: Mozilla/5.0 ...                               │
│   Accept: application/json                                   │
│   Accept-Language: zh-CN,zh;q=0.9,en;q=0.8                 │
│   Accept-Encoding: gzip, deflate, br                        │
│   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...             │
│   Content-Type: application/json                             │
│   Content-Length: 128                                         │
│   Connection: keep-alive                                     │
│   Cookie: session=abc123; theme=dark                         │
├─────────────────────────────────────────────────────────────┤
│ 空行 (CRLF)                                                  │
├─────────────────────────────────────────────────────────────┤
│ 请求体 (Request Body) — 仅 POST/PUT/PATCH 有                │
│   {"name":"Alice","email":"alice@example.com"}               │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 HTTP 响应报文结构

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP 响应报文                              │
├─────────────────────────────────────────────────────────────┤
│ 状态行 (Status Line)                                         │
│   HTTP/1.1 200 OK                                           │
│   │       │   │                                              │
│   │       │   └─ 原因短语                                     │
│   │       └─ 状态码                                          │
│   └─ HTTP 版本                                               │
├─────────────────────────────────────────────────────────────┤
│ 响应头 (Response Headers)                                    │
│   Content-Type: application/json; charset=utf-8             │
│   Content-Length: 256                                         │
│   Cache-Control: max-age=3600                                │
│   ETag: "abc123"                                             │
│   Last-Modified: Wed, 01 May 2026 12:00:00 GMT              │
│   Set-Cookie: session=xyz789; HttpOnly; Secure; SameSite=Lax│
│   X-Request-Id: 550e8400-e29b-41d4-a716-446655440000       │
│   X-Content-Type-Options: nosniff                            │
│   X-Frame-Options: DENY                                      │
│   Strict-Transport-Security: max-age=31536000               │
│   Access-Control-Allow-Origin: https://frontend.example.com │
│   Date: Wed, 01 May 2026 12:00:00 GMT                       │
│   Server: nginx/1.24.0                                       │
├─────────────────────────────────────────────────────────────┤
│ 空行 (CRLF)                                                  │
├─────────────────────────────────────────────────────────────┤
│ 响应体 (Response Body)                                       │
│   {"id":1,"name":"Alice","email":"alice@example.com"}       │
└─────────────────────────────────────────────────────────────┘
```

#### 1.3 HTTP 方法语义详解

| 方法 | 语义 | 幂等 | 安全 | 请求体 | 响应体 | 典型场景 |
|------|------|------|------|--------|--------|----------|
| GET | 获取资源 | Yes | Yes | No | Yes | 获取用户列表、页面 |
| HEAD | 获取元数据 | Yes | Yes | No | No | 检查资源是否存在、获取 Content-Length |
| POST | 创建资源/提交数据 | No | No | Yes | Yes | 创建用户、提交表单、上传文件 |
| PUT | 替换整个资源 | Yes | No | Yes | Yes | 更新用户全部信息 |
| PATCH | 部分更新资源 | No | No | Yes | Yes | 更新用户部分字段 |
| DELETE | 删除资源 | Yes | No | Optional | Optional | 删除用户 |
| OPTIONS | 查询支持的方法 | Yes | Yes | No | Yes | CORS 预检请求 |
| TRACE | 回显请求 | Yes | Yes | No | Yes | 调试（生产环境应禁用） |
| CONNECT | 建立隧道 | No | No | No | Yes | HTTPS 代理 |

**幂等性（Idempotent）**：同一请求执行多次与执行一次效果相同。
- GET：多次获取同一资源，结果不变
- PUT：多次替换同一资源，结果相同
- DELETE：多次删除同一资源，效果相同（第一次删除成功，后续返回 404）
- POST：多次提交可能创建多个资源（不幂等）

**安全性（Safe）**：请求不会修改服务器状态。
- 只有 GET、HEAD、OPTIONS、TRACE 是安全的

#### 1.4 状态码详解

**1xx — 信息性状态码**：

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 100 Continue | 继续 | 客户端发送 `Expect: 100-continue`，服务器确认可以继续发送请求体 |
| 101 Switching Protocols | 切换协议 | WebSocket 升级 |
| 102 Processing | 处理中 | WebDAV，服务器正在处理 |
| 103 Early Hints | 预提示 | 服务器提前发送 Link 头，用于预加载资源 |

```bash
# 100 Continue 示例
curl -v -H "Expect: 100-continue" -d '{"name":"Alice"}' http://api.example.com/users
# 服务器返回 100 Continue 后，客户端继续发送请求体

# 101 Switching Protocols 示例（WebSocket）
# 客户端发送 Upgrade: websocket 头，服务器返回 101 切换协议
```

**2xx — 成功状态码**：

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 OK | 成功 | GET 请求成功返回资源 |
| 201 Created | 已创建 | POST 创建资源成功 |
| 202 Accepted | 已接受 | 请求已接受但尚未处理完成（异步处理） |
| 204 No Content | 无内容 | DELETE 成功，无需返回内容 |
| 206 Partial Content | 部分内容 | 断点续传、视频分段加载 |

```bash
# 200 OK
curl -s -o /dev/null -w "%{http_code}" http://api.example.com/users
# 200

# 201 Created
curl -s -o /dev/null -w "%{http_code}" -X POST -d '{"name":"Alice"}' http://api.example.com/users
# 201

# 204 No Content
curl -s -o /dev/null -w "%{http_code}" -X DELETE http://api.example.com/users/1
# 204

# 206 Partial Content（断点续传）
curl -s -o /dev/null -w "%{http_code}" -H "Range: bytes=0-1023" http://example.com/large-file.zip
# 206
```

**3xx — 重定向状态码**：

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 301 Moved Permanently | 永久重定向 | 域名更换、URL 结构调整（浏览器缓存） |
| 302 Found | 临时重定向 | 临时跳转（不缓存） |
| 303 See Other | 查看其他 | POST 后重定向到结果页面 |
| 304 Not Modified | 未修改 | 协商缓存命中 |
| 307 Temporary Redirect | 临时重定向 | 保持请求方法的临时重定向 |
| 308 Permanent Redirect | 永久重定向 | 保持请求方法的永久重定向 |

```bash
# 301 永久重定向
curl -s -I http://old.example.com
# HTTP/1.1 301 Moved Permanently
# Location: https://new.example.com

# 302 临时重定向
curl -s -I http://example.com/login
# HTTP/1.1 302 Found
# Location: /login?return=/dashboard

# 304 Not Modified（协商缓存）
curl -s -o /dev/null -w "%{http_code}" -H "If-None-Match: \"abc123\"" http://api.example.com/data
# 304

# 301 vs 302 vs 307 vs 308 的区别：
# 301/308：永久重定向
# 302/307：临时重定向
# 301/302：浏览器可能将 POST 改为 GET
# 307/308：严格保持原始请求方法
```

**4xx — 客户端错误状态码**：

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 400 Bad Request | 请求错误 | 参数格式错误、JSON 解析失败 |
| 401 Unauthorized | 未认证 | 缺少或无效的认证令牌 |
| 403 Forbidden | 无权限 | 已认证但无权访问 |
| 404 Not Found | 未找到 | 资源不存在 |
| 405 Method Not Allowed | 方法不允许 | 对只读资源使用 POST |
| 408 Request Timeout | 请求超时 | 客户端发送请求太慢 |
| 409 Conflict | 冲突 | 资源状态冲突（如重复创建） |
| 413 Payload Too Large | 请求体过大 | 上传文件超过限制 |
| 429 Too Many Requests | 请求过多 | 触发限流 |

```bash
# 400 Bad Request
curl -s -X POST -d 'invalid json' http://api.example.com/users
# {"error":"Invalid JSON in request body"}

# 401 Unauthorized
curl -s http://api.example.com/users
# {"error":"Authentication required"}

# 403 Forbidden
curl -s -H "Authorization: Bearer valid-token" http://api.example.com/admin
# {"error":"Insufficient permissions"}

# 404 Not Found
curl -s http://api.example.com/users/99999
# {"error":"User not found"}

# 429 Too Many Requests
curl -s http://api.example.com/data
# HTTP/1.1 429 Too Many Requests
# Retry-After: 60
# {"error":"Rate limit exceeded"}
```

**5xx — 服务器错误状态码**：

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 500 Internal Server Error | 服务器内部错误 | 代码 Bug、未捕获异常 |
| 502 Bad Gateway | 网关错误 | 上游服务返回无效响应 |
| 503 Service Unavailable | 服务不可用 | 服务器过载、维护中 |
| 504 Gateway Timeout | 网关超时 | 上游服务响应超时 |

```bash
# 500 Internal Server Error
# 通常是代码 Bug，查看应用日志

# 502 Bad Gateway
# Nginx 作为反向代理时，上游服务崩溃或返回无效响应
# 排查：检查上游服务是否存活、端口是否正确

# 503 Service Unavailable
# 服务器过载或维护中
curl -s -I http://example.com
# HTTP/1.1 503 Service Unavailable
# Retry-After: 3600

# 504 Gateway Timeout
# Nginx 等待上游响应超时
# 排查：检查上游服务响应时间、调整 proxy_read_timeout
```

#### 1.5 请求头/响应头详解

**常用请求头**：

| 头部 | 说明 | 示例 |
|------|------|------|
| Host | 目标主机（HTTP/1.1 必需） | `Host: api.example.com` |
| User-Agent | 客户端标识 | `User-Agent: curl/7.68.0` |
| Accept | 期望的响应格式 | `Accept: application/json` |
| Accept-Encoding | 支持的压缩 | `Accept-Encoding: gzip, deflate, br` |
| Accept-Language | 语言偏好 | `Accept-Language: zh-CN,zh;q=0.9` |
| Authorization | 认证信息 | `Authorization: Bearer eyJhb...` |
| Content-Type | 请求体格式 | `Content-Type: application/json` |
| Content-Length | 请求体长度 | `Content-Length: 128` |
| Connection | 连接管理 | `Connection: keep-alive` |
| Cookie | Cookie | `Cookie: session=abc123` |
| Cache-Control | 缓存控制 | `Cache-Control: no-cache` |
| If-None-Match | 协商缓存（ETag） | `If-None-Match: "abc123"` |
| If-Modified-Since | 协商缓存（时间） | `If-Modified-Since: Wed, 01 May 2026 12:00:00 GMT` |
| Range | 范围请求 | `Range: bytes=0-1023` |
| X-Request-Id | 请求追踪 ID | `X-Request-Id: 550e8400-...` |

**常用响应头**：

| 头部 | 说明 | 示例 |
|------|------|------|
| Content-Type | 响应体格式 | `Content-Type: application/json; charset=utf-8` |
| Content-Length | 响应体长度 | `Content-Length: 256` |
| Content-Encoding | 压缩方式 | `Content-Encoding: gzip` |
| Cache-Control | 缓存策略 | `Cache-Control: max-age=3600` |
| ETag | 资源标识 | `ETag: "abc123"` |
| Last-Modified | 最后修改时间 | `Last-Modified: Wed, 01 May 2026 12:00:00 GMT` |
| Set-Cookie | 设置 Cookie | `Set-Cookie: session=xyz; HttpOnly; Secure` |
| Location | 重定向地址 | `Location: https://example.com/new` |
| X-Content-Type-Options | 防止 MIME 嗅探 | `X-Content-Type-Options: nosniff` |
| X-Frame-Options | 防止点击劫持 | `X-Frame-Options: DENY` |
| Strict-Transport-Security | HSTS | `Strict-Transport-Security: max-age=31536000` |
| Access-Control-Allow-Origin | CORS | `Access-Control-Allow-Origin: *` |
| X-Request-Id | 请求追踪 | `X-Request-Id: 550e8400-...` |

#### 1.6 HTTP/1.0 vs HTTP/1.1 vs HTTP/2 vs HTTP/3

| 特性 | HTTP/1.0 | HTTP/1.1 | HTTP/2 | HTTP/3 |
|------|----------|----------|--------|--------|
| 连接管理 | 每请求一个连接 | Keep-Alive 复用 | 多路复用 | 多路复用 |
| 传输协议 | TCP | TCP | TCP | QUIC (UDP) |
| 头部压缩 | 无 | 无 | HPACK | QPACK |
| 服务器推送 | 不支持 | 不支持 | 支持 | 支持 |
| 二进制分帧 | 否 | 否 | 是 | 是 |
| 队头阻塞 | 有 | 有 | TCP 层有 | 无 |
| TLS | 可选 | 可选 | 实际必需 | 内置 |

**HTTP/1.0 的问题**：
- 每个请求都需要建立新的 TCP 连接
- 不支持 Host 头（一个 IP 只能托管一个站点）

**HTTP/1.1 的改进**：
- Keep-Alive：连接复用
- Host 头：虚拟主机支持
- Chunked Transfer：分块传输
- Pipeline：请求管道化（但有队头阻塞问题）

**HTTP/2 的改进**：
- 二进制分帧：更高效的数据传输
- 多路复用：一个连接上并行多个请求
- 头部压缩（HPACK）：减少头部开销
- 服务器推送：主动推送资源
- 流优先级：重要资源优先传输

**HTTP/3 的改进**：
- 基于 QUIC（UDP）：解决 TCP 队头阻塞
- 0-RTT 连接建立：更快的首次连接
- 内置 TLS 1.3：安全性更强
- 连接迁移：网络切换不断连

---

### 2. HTTPS 深入

#### 2.1 TLS 握手流程

**RSA 握手（传统，不推荐）**：

```
客户端                                    服务器
  │                                         │
  │  ClientHello                            │
  │  - 支持的 TLS 版本                      │
  │  - 支持的加密套件列表                    │
  │  - 客户端随机数 (Client Random)          │
  │ ───────────────────────────────────────→│
  │                                         │
  │  ServerHello                            │
  │  - 选择的 TLS 版本                      │
  │  - 选择的加密套件                        │
  │  - 服务器随机数 (Server Random)          │
  │  Certificate (服务器证书)                │
  │  ServerHelloDone                        │
  │ ←─────────────────────────────────────── │
  │                                         │
  │  客户端验证证书                          │
  │  生成预主密钥 (Pre-Master Secret)        │
  │  用服务器公钥加密预主密钥                │
  │  ClientKeyExchange                      │
  │  ChangeCipherSpec                       │
  │  Finished                               │
  │ ───────────────────────────────────────→│
  │                                         │
  │  ChangeCipherSpec                       │
  │  Finished                               │
  │ ←─────────────────────────────────────── │
  │                                         │
  │  ←── 使用对称密钥加密通信 ──→             │
```

**ECDHE 握手（推荐，前向安全）**：

```
客户端                                    服务器
  │                                         │
  │  ClientHello                            │
  │  - 支持的 TLS 版本                      │
  │  - 支持的加密套件列表                    │
  │  - 客户端随机数                          │
  │ ───────────────────────────────────────→│
  │                                         │
  │  ServerHello                            │
  │  - 选择的 TLS 版本                      │
  │  - 选择的加密套件 (ECDHE)               │
  │  - 服务器随机数                          │
  │  Certificate (服务器证书)                │
  │  ServerKeyExchange                      │
  │  - 服务器 ECDH 公钥                     │
  │  - 签名（证明拥有私钥）                  │
  │  ServerHelloDone                        │
  │ ←─────────────────────────────────────── │
  │                                         │
  │  客户端验证证书和签名                    │
  │  客户端生成 ECDH 密钥对                  │
  │  ClientKeyExchange                      │
  │  - 客户端 ECDH 公钥                     │
  │  ChangeCipherSpec                       │
  │  Finished                               │
  │ ───────────────────────────────────────→│
  │                                         │
  │  双方通过 ECDH 计算预主密钥              │
  │  ChangeCipherSpec                       │
  │  Finished                               │
  │ ←─────────────────────────────────────── │
  │                                         │
  │  ←── 使用对称密钥加密通信 ──→             │
```

**RSA vs ECDHE 对比**：

| 特性 | RSA | ECDHE |
|------|-----|-------|
| 前向安全性 | 无 | 有 |
| 密钥交换 | 服务器公钥加密 | ECDH 协商 |
| 握手次数 | 2-RTT | 2-RTT |
| 安全性 | 私钥泄露 → 历史流量可解密 | 私钥泄露 → 历史流量安全 |
| 推荐 | 不推荐 | 推荐 |

#### 2.2 TLS 1.3 的改进

```
TLS 1.3 握手（1-RTT）：

客户端                                    服务器
  │                                         │
  │  ClientHello                            │
  │  - 支持的加密套件                        │
  │  - 密钥共享 (Key Share)                  │
  │  - 支持的版本                            │
  │ ───────────────────────────────────────→│
  │                                         │
  │  ServerHello                            │
  │  - 选择的加密套件                        │
  │  - 密钥共享 (Key Share)                  │
  │  {EncryptedExtensions}                  │
  │  {Certificate}                          │
  │  {CertificateVerify}                    │
  │  {Finished}                             │
  │ ←─────────────────────────────────────── │
  │                                         │
  │  {Finished}                             │
  │ ───────────────────────────────────────→│
  │                                         │
  │  ←── 加密通信 ──→                        │
```

**TLS 1.3 关键改进**：

| 改进 | 说明 |
|------|------|
| 1-RTT 握手 | 减少一次往返时间 |
| 0-RTT 恢复 | 会话恢复时可以 0-RTT 发送数据 |
| 移除不安全算法 | 只保留 AEAD 加密（AES-GCM、ChaCha20） |
| 加密握手 | Certificate 之后的消息全部加密 |
| 前向安全 | 强制使用 (EC)DHE 密钥交换 |

#### 2.3 证书验证链

```
根证书颁发机构 (Root CA)
│  例：DigiCert Global Root G2
│  自签名，预装在操作系统/浏览器中
│
├── 中间证书 (Intermediate CA)
│   │  例：DigiCert SHA2 Secure Server CA
│   │  由 Root CA 签发
│   │
│   ├── 服务器证书 (Server Certificate)
│   │   │  例：*.example.com
│   │   │  由 Intermediate CA 签发
│   │   │  包含公钥、域名、有效期、签名
│   │   │
│   │   └── 客户端验证过程：
│   │       1. 检查域名是否匹配
│   │       2. 检查证书是否过期
│   │       3. 用中间证书公钥验证服务器证书签名
│   │       4. 用根证书公钥验证中间证书签名
│   │       5. 检查证书是否被吊销（CRL/OCSP）
│   │
│   └── 其他服务器证书
│
└── 其他中间证书
```

```bash
# 查看证书信息
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -text

# 查看证书链
echo | openssl s_client -connect example.com:443 -showcerts 2>/dev/null

# 查看证书有效期
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates

# 检查证书是否匹配域名
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null | openssl x509 -noout -text | grep -A1 "Subject Alternative Name"

# 验证证书链
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt certificate.pem
```

#### 2.4 证书管理

**Let's Encrypt + Certbot**：

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取证书（Nginx 插件）
sudo certbot --nginx -d example.com -d www.example.com

# 获取证书（Webroot 模式）
sudo certbot certonly --webroot -w /var/www/html -d example.com

# 查看证书
sudo certbot certificates

# 手动续期
sudo certbot renew

# 测试续期
sudo certbot renew --dry-run

# 自动续期（cron）
echo "0 0,12 * * * root python3 -c 'import random; import time; time.sleep(random.random() * 3600)' && certbot renew -q" | sudo tee -a /etc/crontab > /dev/null
```

**Nginx HTTPS 配置**：

```nginx
server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # TLS 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_chain /etc/letsencrypt/live/example.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;

    # Session 缓存
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
}

# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$server_name$request_uri;
}
```

---

### 3. HTTP 缓存机制

#### 3.1 缓存类型

```
┌─────────────────────────────────────────────────────────────────┐
│                        HTTP 缓存架构                             │
│                                                                 │
│   浏览器缓存        CDN/代理缓存         服务器                  │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐             │
│   │  强缓存   │ ──→  │  强缓存   │ ──→  │  源站    │             │
│   │  协商缓存 │ ←──  │  协商缓存 │ ←──  │          │             │
│   └──────────┘      └──────────┘      └──────────┘             │
│                                                                 │
│   强缓存命中 → 直接使用本地缓存（不发请求）                      │
│   协商缓存命中 → 服务器返回 304（不传 body）                     │
│   缓存未命中 → 服务器返回 200 + 新资源                           │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.2 强缓存

强缓存不需要向服务器发送请求，直接使用本地缓存。

**相关头部**：

| 头部 | 说明 | 优先级 |
|------|------|--------|
| `Cache-Control: max-age=3600` | 缓存有效期（秒） | 高（HTTP/1.1） |
| `Expires: Thu, 01 May 2026 12:00:00 GMT` | 过期时间 | 低（HTTP/1.0） |
| `Cache-Control: no-cache` | 不使用强缓存，走协商缓存 | - |
| `Cache-Control: no-store` | 完全不缓存 | - |
| `Cache-Control: public` | 公共缓存（CDN 可缓存） | - |
| `Cache-Control: private` | 私有缓存（仅浏览器） | - |

```bash
# 强缓存示例
curl -s -I http://example.com/static/app.js
# Cache-Control: max-age=31536000
# ETag: "abc123"

# 不缓存
curl -s -I http://api.example.com/data
# Cache-Control: no-store
```

#### 3.3 协商缓存

协商缓存需要向服务器验证资源是否过期。

**相关头部**：

| 头部 | 说明 | 服务器响应 |
|------|------|-----------|
| `If-None-Match: "abc123"` | 与 ETag 对比 | 304 Not Modified 或 200 |
| `If-Modified-Since: Wed, 01 May 2026 12:00:00 GMT` | 与 Last-Modified 对比 | 304 Not Modified 或 200 |

**ETag vs Last-Modified**：

| 特性 | ETag | Last-Modified |
|------|------|---------------|
| 精确度 | 精确（内容哈希） | 秒级 |
| 优先级 | 高 | 低 |
| 开销 | 需要计算哈希 | 读取文件修改时间 |
| 场景 | 内容频繁变化 | 静态资源 |

```bash
# 协商缓存流程
# 1. 首次请求
curl -s -I http://example.com/data.json
# HTTP/1.1 200 OK
# ETag: "abc123"
# Last-Modified: Wed, 01 May 2026 12:00:00 GMT
# Cache-Control: no-cache

# 2. 后续请求（带条件）
curl -s -I -H 'If-None-Match: "abc123"' http://example.com/data.json
# HTTP/1.1 304 Not Modified

# 3. 资源已更新
curl -s -I -H 'If-None-Match: "abc123"' http://example.com/data.json
# HTTP/1.1 200 OK
# ETag: "def456"
```

#### 3.4 缓存策略最佳实践

| 资源类型 | 策略 | 原因 |
|----------|------|------|
| HTML | `no-cache` | 需要验证最新版本 |
| CSS/JS（带 hash） | `max-age=31536000, immutable` | 文件名变化=新版本 |
| 图片 | `max-age=86400` | 一天内不变 |
| API 响应 | `no-store` | 数据实时变化 |
| 字体 | `max-age=31536000` | 很少变化 |

---

### 4. CORS（跨域资源共享）

#### 4.1 同源策略

同源策略限制了一个源的文档或脚本如何与另一个源的资源交互。

**同源判断**：协议 + 域名 + 端口 都相同

| URL | 是否同源 | 原因 |
|-----|----------|------|
| `http://example.com/a` vs `http://example.com/b` | 同源 | 路径不同不影响 |
| `http://example.com` vs `https://example.com` | 不同源 | 协议不同 |
| `http://example.com` vs `http://api.example.com` | 不同源 | 域名不同 |
| `http://example.com:80` vs `http://example.com:8080` | 不同源 | 端口不同 |

#### 4.2 CORS 请求类型

**简单请求**（Simple Request）：
- 方法：GET、HEAD、POST
- 头部限制：只有安全的头部
- Content-Type：text/plain、multipart/form-data、application/x-www-form-urlencoded

**预检请求**（Preflight Request）：
- 使用 OPTIONS 方法
- 服务器返回允许的方法和头部
- 浏览器收到允许后才发送实际请求

```
浏览器                                    服务器
  │                                         │
  │  OPTIONS /api/data                      │
  │  Origin: https://frontend.com           │
  │  Access-Control-Request-Method: PUT     │
  │  Access-Control-Request-Headers:        │
  │    Content-Type, Authorization          │
  │ ───────────────────────────────────────→│
  │                                         │
  │  204 No Content                         │
  │  Access-Control-Allow-Origin:           │
  │    https://frontend.com                 │
  │  Access-Control-Allow-Methods:          │
  │    GET, POST, PUT, DELETE               │
  │  Access-Control-Allow-Headers:          │
  │    Content-Type, Authorization          │
  │  Access-Control-Max-Age: 86400          │
  │ ←─────────────────────────────────────── │
  │                                         │
  │  PUT /api/data                          │
  │  Origin: https://frontend.com           │
  │  Content-Type: application/json         │
  │  Authorization: Bearer xxx              │
  │ ───────────────────────────────────────→│
  │                                         │
  │  200 OK                                 │
  │  Access-Control-Allow-Origin:           │
  │    https://frontend.com                 │
  │ ←─────────────────────────────────────── │
```

#### 4.3 CORS 响应头

| 头部 | 说明 |
|------|------|
| `Access-Control-Allow-Origin` | 允许的源（`*` 或具体域名） |
| `Access-Control-Allow-Methods` | 允许的方法 |
| `Access-Control-Allow-Headers` | 允许的请求头 |
| `Access-Control-Allow-Credentials` | 是否允许携带 Cookie |
| `Access-Control-Max-Age` | 预检结果缓存时间（秒） |
| `Access-Control-Expose-Headers` | 允许前端访问的响应头 |

```nginx
# Nginx CORS 配置
server {
    location /api/ {
        # 允许的源（不要用 * 配合 credentials）
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Request-Id" always;
        add_header Access-Control-Allow-Credentials "true" always;
        add_header Access-Control-Max-Age 86400 always;

        # 处理预检请求
        if ($request_method = 'OPTIONS') {
            return 204;
        }

        proxy_pass http://backend;
    }
}
```

---

### 5. SRE 实战案例

#### 5.1 案例一：502 Bad Gateway → Nginx 上游崩溃

**背景**：Nginx 反向代理返回 502 Bad Gateway。

**排查过程**：

```bash
# 步骤 1：检查 Nginx 错误日志
sudo tail -f /var/log/nginx/error.log
# 2026/05/01 14:23:45 [error] 1234#1234: *5678 connect() failed (111: Connection refused)
#   while connecting to upstream, upstream: "http://127.0.0.1:8080"

# 步骤 2：检查上游服务
curl -s http://127.0.0.1:8080/health
# curl: (7) Failed to connect to 127.0.0.1 port 8080: Connection refused

# 步骤 3：检查服务状态
sudo systemctl status myapp
# Active: failed

# 步骤 4：检查端口监听
ss -tlnp | grep 8080
# 空（没有进程监听）

# 步骤 5：检查应用日志
sudo journalctl -u myapp --since "5 minutes ago"
# 发现 OOM Killed
```

**根因**：上游应用因 OOM 被 Kill，端口不再监听，Nginx 连接被拒绝返回 502。

**解决方案**：

```bash
# 1. 重启应用
sudo systemctl restart myapp

# 2. 增加内存限制或优化内存使用

# 3. 配置 Nginx 自动重试
upstream backend {
    server 127.0.0.1:8080 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8081 max_fails=3 fail_timeout=30s backup;
}

# 4. 配置健康检查
```

#### 5.2 案例二：HTTPS 证书过期

**背景**：用户报告网站显示"连接不安全"。

```bash
# 步骤 1：检查证书有效期
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates
# notBefore=May  1 00:00:00 2025 GMT
# notAfter=Apr 30 23:59:59 2026 GMT
# 证书已过期！

# 步骤 2：检查 Certbot 自动续期
sudo certbot certificates
# 发现证书已过期

# 步骤 3：手动续期
sudo certbot renew --force-renewal

# 步骤 4：重载 Nginx
sudo systemctl reload nginx

# 步骤 5：验证
curl -s -I https://example.com
# HTTP/1.1 200 OK
```

**预防措施**：

```bash
# 配置证书过期监控
# Prometheus + blackbox_exporter
# 或简单的 cron 检查脚本

# 检查脚本
echo | openssl s_client -connect example.com:443 2>/dev/null | \
  openssl x509 -noout -enddate | \
  awk -F= '{cmd="date -d \""$2"\" +%s"; cmd | getline expire; close(cmd); print int((expire-systime())/86400)}'
# 输出：30（还剩 30 天）
```

#### 5.3 案例三：HTTP 缓存配置不当

**背景**：用户反馈看到旧版本的页面内容。

```bash
# 步骤 1：检查响应头
curl -s -I http://example.com/
# Cache-Control: max-age=86400
# ETag: "v1.0"
# Last-Modified: Wed, 01 May 2026 12:00:00 GMT

# 问题：HTML 页面设置了 max-age=86400（1天），
# 部署新版本后，浏览器在 24 小时内仍使用缓存

# 步骤 2：检查部署时间
ls -la /var/www/html/index.html
# May 01 14:00 index.html  ← 刚部署

# 步骤 3：确认缓存问题
curl -s -I -H "Cache-Control: no-cache" http://example.com/
# 返回新版本内容
```

**解决方案**：

```nginx
# HTML 页面：no-cache（每次验证）
location ~* \.html$ {
    add_header Cache-Control "no-cache, must-revalidate";
    add_header ETag "";
}

# 静态资源（CSS/JS/图片）：长期缓存 + 文件名 hash
location ~* \.(css|js|png|jpg|gif|ico|svg|woff2)$ {
    add_header Cache-Control "max-age=31536000, immutable";
}

# API 响应：不缓存
location /api/ {
    add_header Cache-Control "no-store";
}
```

---

## 💻 实战练习

### 练习 1：HTTP 请求分析

```bash
# 使用 curl 时间分解分析 API 延迟
curl -o /dev/null -s -w \
  "DNS:       %{time_namelookup}s\n\
   TCP:       %{time_connect}s\n\
   TLS:       %{time_appconnect}s\n\
   TTFB:      %{time_starttransfer}s\n\
   Total:     %{time_total}s\n\
   Size:      %{size_download} bytes\n\
   Speed:     %{speed_download} bytes/sec\n\
   HTTP Code: %{http_code}\n" \
  https://httpbin.org/get

# 分析各阶段耗时
# DNS: 0.012s      ← DNS 解析
# TCP: 0.045s      ← TCP 连接（包含 DNS）
# TLS: 0.123s      ← TLS 握手（包含 TCP）
# TTFB: 0.234s     ← 首字节时间（包含 TLS）
# Total: 0.256s    ← 总时间
```

### 练习 2：TLS 握手分析

```bash
# 查看 TLS 版本和加密套件
echo | openssl s_client -connect example.com:443 -brief 2>&1 | head -10

# 详细查看证书
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -text | head -30

# 查看支持的 TLS 版本
openssl s_client -connect example.com:443 -tls1_2 2>&1 | grep "Protocol"
openssl s_client -connect example.com:443 -tls1_3 2>&1 | grep "Protocol"
```

### 练习 3：缓存行为验证

```bash
# 1. 首次请求
curl -s -I http://httpbin.org/cache/60
# Cache-Control: public, max-age=60

# 2. 带条件请求
curl -s -I -H 'If-None-Match: "etag-value"' http://httpbin.org/etag/etag-value
# 304 Not Modified

# 3. 过期后请求
curl -s -I http://httpbin.org/response-headers?Cache-Control=no-cache
# 200 OK（无缓存）
```

### 练习 4：CORS 调试

```bash
# 模拟 CORS 请求
curl -s -I -H "Origin: https://frontend.example.com" http://api.example.com/data
# 检查 Access-Control-Allow-Origin 头

# 模拟预检请求
curl -s -X OPTIONS \
  -H "Origin: https://frontend.example.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: Content-Type" \
  http://api.example.com/data -I
```

---

## 🎯 面试题精选

### Q1：HTTPS 的握手过程是怎样的？

**参考答案**：

HTTPS = HTTP over TLS，握手过程如下（以 TLS 1.2 ECDHE 为例）：

1. **ClientHello**：客户端发送支持的 TLS 版本、加密套件列表、客户端随机数
2. **ServerHello**：服务器选择 TLS 版本和加密套件，发送服务器随机数
3. **Certificate**：服务器发送证书链
4. **ServerKeyExchange**：服务器发送 ECDH 公钥和签名
5. **ClientKeyExchange**：客户端发送 ECDH 公钥
6. **双方计算预主密钥**：通过 ECDH 协商生成共享密钥
7. **ChangeCipherSpec + Finished**：双方切换到加密通信

TLS 1.3 将握手优化为 1-RTT，且 Certificate 之后的消息全部加密。

### Q2：HTTP/2 相比 HTTP/1.1 有什么改进？

**参考答案**：

1. **二进制分帧**：将数据分成更小的帧，更高效
2. **多路复用**：一个 TCP 连接上并行多个请求，解决队头阻塞
3. **头部压缩（HPACK）**：使用静态表和动态表压缩头部
4. **服务器推送**：服务器可以主动推送资源
5. **流优先级**：重要资源可以优先传输

**注意**：HTTP/2 仍然基于 TCP，在 TCP 层仍有队头阻塞。HTTP/3 使用 QUIC（UDP）解决了这个问题。

### Q3：什么是 CORS？为什么需要预检请求？

**参考答案**：

CORS（Cross-Origin Resource Sharing）是浏览器的安全机制，允许跨域请求。

**为什么需要预检请求**：
- 非简单请求（如 PUT、DELETE，或带自定义头部）可能对服务器产生副作用
- 浏览器先发送 OPTIONS 请求，询问服务器是否允许
- 服务器返回允许的方法和头部
- 浏览器确认后才发送实际请求

**简单请求不需要预检**：GET、HEAD、POST（特定 Content-Type）。

### Q4：强缓存和协商缓存有什么区别？

**参考答案**：

| 维度 | 强缓存 | 协商缓存 |
|------|--------|----------|
| 是否发请求 | 不发 | 发（条件请求） |
| 状态码 | 200 (from cache) | 304 Not Modified |
| 头部 | Cache-Control/Expires | ETag/Last-Modified |
| 优先级 | 先检查强缓存 | 强缓存失效后检查 |

流程：先检查强缓存 → 命中直接使用 → 未命中检查协商缓存 → 命中返回 304 → 未命中返回 200 + 新资源。

### Q5：502 和 504 的区别是什么？

**参考答案**：

- **502 Bad Gateway**：网关/代理从上游收到**无效响应**
  - 原因：上游服务崩溃、返回了不完整的响应
  - 排查：检查上游服务状态和日志

- **504 Gateway Timeout**：网关/代理等待上游响应**超时**
  - 原因：上游服务处理太慢
  - 排查：检查上游服务性能、调整超时配置

---

## 📚 深入阅读

| 资源 | 链接 |
|------|------|
| MDN HTTP 文档 | https://developer.mozilla.org/en-US/docs/Web/HTTP |
| RFC 7230-7235 (HTTP/1.1) | https://tools.ietf.org/html/rfc7230 |
| RFC 7540 (HTTP/2) | https://tools.ietf.org/html/rfc7540 |
| RFC 9000 (HTTP/3) | https://tools.ietf.org/html/rfc9000 |
| RFC 8446 (TLS 1.3) | https://tools.ietf.org/html/rfc8446 |
| Let's Encrypt 文档 | https://letsencrypt.org/docs/ |
| web.dev 缓存指南 | https://web.dev/http-cache/ |

---

## ✅ 自检清单

- [ ] 理解 HTTP 请求/响应报文结构
- [ ] 掌握 HTTP 方法语义（GET/POST/PUT/DELETE/PATCH）
- [ ] 熟悉常用状态码（1xx-5xx）的含义
- [ ] 理解 HTTP/1.1 → HTTP/2 → HTTP/3 的演进
- [ ] 掌握 TLS 握手流程（RSA vs ECDHE）
- [ ] 理解证书验证链（CA → 中间证书 → 服务器证书）
- [ ] 掌握 HTTP 缓存机制（强缓存 vs 协商缓存）
- [ ] 理解 CORS 原理和预检请求
- [ ] 能排查 502/504 错误
- [ ] 能配置 HTTPS 和证书管理
