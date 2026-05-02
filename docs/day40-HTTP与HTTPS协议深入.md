# Day 40: HTTP 与 HTTPS 协议深入

> 📅 日期：2026-04-27
> 📖 学习主题：HTTP 与 HTTPS 协议深入
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 HTTP 协议的工作原理（请求/响应模型）
- 掌握 HTTP 方法、状态码、头部字段的含义
- 理解 HTTPS 的 TLS 握手过程
- 能使用 curl 进行 HTTP 调试
- 理解 HTTP/1.1、HTTP/2、HTTP/3 的演进

---

## 📖 HTTP 协议基础

### 1. HTTP 请求/响应模型

```
客户端                    服务器
  │                         │
  │  HTTP Request           │
  │ ──────────────────────→│
  │  GET /index.html HTTP/1.1│
  │  Host: example.com      │
  │                         │
  │  HTTP Response          │
  │ ←────────────────────── │
  │  HTTP/1.1 200 OK        │
  │  Content-Type: text/html │
  │  Content-Length: 1234    │
  │                         │
  │  <html>...</html>        │
```

### 2. HTTP 方法

| 方法 | 用途 | 幂等 | 安全 | 示例 |
|------|------|------|------|------|
| GET | 获取资源 | ✅ | ✅ | `GET /api/users` |
| POST | 创建资源 | ❌ | ❌ | `POST /api/users` |
| PUT | 替换资源 | ✅ | ❌ | `PUT /api/users/1` |
| PATCH | 部分更新 | ❌ | ❌ | `PATCH /api/users/1` |
| DELETE | 删除资源 | ✅ | ❌ | `DELETE /api/users/1` |
| HEAD | 获取头部（无体） | ✅ | ✅ | `HEAD /api/health` |
| OPTIONS | 查询支持的方法 | ✅ | ✅ | `OPTIONS /api/users` |

**幂等性**：同一请求执行多次与执行一次效果相同。
**安全性**：请求不会修改服务器状态。

### 3. HTTP 状态码

| 范围 | 含义 | 常见状态码 |
|------|------|-----------|
| 1xx | 信息 | 100 Continue |
| 2xx | 成功 | 200 OK, 201 Created, 204 No Content |
| 3xx | 重定向 | 301 Moved, 302 Found, 304 Not Modified |
| 4xx | 客户端错误 | 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found |
| 5xx | 服务器错误 | 500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable |

### 4. 常用头部

```
请求头：
  Host: example.com          # 目标主机（HTTP/1.1 必需）
  User-Agent: curl/7.68.0    # 客户端标识
  Accept: application/json    # 期望的响应格式
  Authorization: Bearer xxx   # 认证令牌
  Content-Type: application/json  # 请求体格式
  Content-Length: 123         # 请求体长度
  Connection: keep-alive      # 保持连接

响应头：
  Content-Type: text/html; charset=utf-8
  Content-Length: 1234
  Cache-Control: max-age=3600
  Set-Cookie: session=abc123; HttpOnly; Secure
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
```

---

## HTTPS 与 TLS

### 5. TLS 握手过程

```
客户端                              服务器
  │                                   │
  │  ClientHello                      │
  │  (支持的TLS版本、加密套件)         │
  │ ────────────────────────────────→│
  │                                   │
  │  ServerHello                      │
  │  (选择的TLS版本、加密套件)         │
  │  Certificate (服务器证书)          │
  │  ServerKeyExchange                │
  │ ←─────────────────────────────── │
  │                                   │
  │  ClientKeyExchange                │
  │  ChangeCipherSpec                 │
  │  Finished                         │
  │ ────────────────────────────────→│
  │                                   │
  │  ChangeCipherSpec                 │
  │  Finished                         │
  │ ←─────────────────────────────── │
  │                                   │
  │  ←── 加密通信开始 ──→              │
```

### 6. SRE 中的 HTTP 调试

```bash
# curl 调试技巧
curl -v https://example.com        # 显示完整请求/响应
curl -I https://example.com        # 只显示响应头
curl -s -o /dev/null -w "%{http_code}" https://example.com  # 只输出状态码
curl -s -o /dev/null -w "DNS: %{time_namelookup}s\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" https://example.com

# 时间指标：
# time_namelookup: DNS 解析时间
# time_connect: TCP 连接时间
# time_starttransfer: TTFB（首字节时间）
# time_total: 总时间

# 查看证书信息
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates -subject -issuer
```

---

## 🧪 练习题

<details>
<summary>301 vs 302 的区别？</summary>

301 是永久重定向（浏览器会缓存），302 是临时重定向（每次都问服务器）。
SEO 角度：301 会转移权重，302 不会。
</details>

---

## 📚 扩展阅读

- [MDN HTTP 文档](https://developer.mozilla.org/en-US/docs/Web/HTTP)
- [TLS 1.3 RFC 8446](https://datatracker.ietf.org/doc/html/rfc8446)
