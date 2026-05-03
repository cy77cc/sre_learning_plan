# Day 35: 复习与实战 — 从 URL 到页面的完整过程

> 📅 日期：2026-04-29
> 📖 学习主题：复习与实战 — 从 URL 到页面的完整过程
> ⏰ 计划学习时间：2-3 小时

## 🎯 学习目标

- [ ] 梳理从输入 URL 到页面渲染的完整技术链路，包括 DNS、TCP、TLS、HTTP 各阶段
- [ ] 手写/绘制 DNS → TCP → TLS → HTTP 流程图，标注关键时序和协议细节
- [ ] 编写一个网络诊断脚本，自动化检测目标站点的网络可达性与性能指标
- [ ] 分析 `curl -vvv` 的输出，能识别每个阶段的关键信息
- [ ] 完成自我评估：能否独立解释「网站打不开」的 5 种可能原因并给出排查方法

---

## 📖 详细知识点

### 1. 从 URL 到页面渲染的完整链路

#### 1.1 整体概览

当用户在浏览器地址栏输入 `https://www.example.com/path?query=1` 并按下回车后，会经历以下阶段：

| 阶段 | 协议/技术 | 主要任务 | 典型耗时 | SRE 关注点 |
|------|----------|----------|----------|-----------|
| URL 解析 | 浏览器内置 | 拆分协议、域名、路径、端口 | < 1ms | 无效 URL 导致请求失败 |
| DNS 解析 | DNS (UDP/TCP 53) | 域名 → IP 地址 | 1-100ms | DNS 超时、缓存污染、权威服务器不可达 |
| TCP 连接 | TCP (三次握手) | 建立可靠传输通道 | 1-200ms (1×RTT) | 握手失败、SYN 丢包、防火墙拦截 |
| TLS 握手 | TLS 1.2/1.3 | 加密协商、证书验证 | 1-200ms (1-2×RTT) | 证书过期、SNI 不匹配、加密套件不支持 |
| HTTP 请求 | HTTP/1.1/2/3 | 发送请求报文 | < 1ms | 请求头过大、超时、限流 |
| 服务端处理 | 应用层 | 业务逻辑、数据库查询 | 10ms-10s+ | CPU 瓶颈、慢查询、级联故障 |
| HTTP 响应 | HTTP | 返回状态码和响应体 | 取决于服务端 | 5xx 错误、超时、响应过大 |
| 页面渲染 | 浏览器引擎 | HTML 解析、CSS 渲染、JS 执行 | 100ms-5s+ | 首字节时间(TTFB)、首屏时间(FCP) |

#### 1.2 DNS 解析阶段详解

DNS 解析是一个递归查询过程：

```
浏览器缓存 → 操作系统缓存 → 本地 DNS 服务器 → 根 DNS → TLD DNS → 权威 DNS → 返回 IP
```

**DNS 查询类型：**

| 记录类型 | 用途 | 示例 |
|---------|------|------|
| A | IPv4 地址 | `93.184.216.34` |
| AAAA | IPv6 地址 | `2606:2800:220:1:248:1893:25c8:1946` |
| CNAME | 别名记录 | `www.example.com → example.com` |
| MX | 邮件交换 | `mail.example.com` |
| NS | 名称服务器 | `ns1.example.com` |
| TXT | 文本记录 | SPF、DKIM 验证 |

**DNS 缓存机制：**

```bash
# 查看本地 DNS 缓存 (macOS)
sudo dscacheutil -statistics

# 刷新 DNS 缓存
# Linux (systemd-resolved)
sudo systemctl restart systemd-resolved

# Linux (nscd)
sudo systemctl restart nscd

# macOS
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Windows
ipconfig /flushdns
```

#### 1.3 TCP 三次握手

```
Client                          Server
  |                               |
  |-------- SYN (seq=x) -------->|  1. 客户端发送 SYN
  |                               |
  |<------- SYN-ACK (seq=y,      |  2. 服务端回应 SYN+ACK
  |         ack=x+1) ------------|
  |                               |
  |-------- ACK (ack=y+1) ------>|  3. 客户端确认
  |                               |
  |        [数据传输开始]          |
```

**SRE 排查要点：**

```bash
# 查看 TCP 连接状态统计
netstat -an | awk '/^tcp/ {print $6}' | sort | uniq -c | sort -rn

# 查看 SYN 半连接数 (SYN Flood 攻击排查)
netstat -an | grep SYN_RECV | wc -l

# 查看 TCP 重传统计
cat /proc/net/snmp | grep Tcp

# 使用 ss 查看更详细的连接信息
ss -tan state established | head -20
ss -tan state time-wait | wc -l
ss -tan state syn-recv | wc -l
```

#### 1.4 TLS 握手过程

**TLS 1.2 握手流程：**

```
Client Hello
  ├─ 支持的 TLS 版本
  ├─ 客户端随机数
  ├─ 加密套件列表
  └─ SNI (Server Name Indication)
       ↓
Server Hello
  ├─ 选择的 TLS 版本
  ├─ 服务端随机数
  ├─ 选择的加密套件
  └─ 服务器证书
       ↓
密钥交换 (Diffie-Hellman / RSA)
       ↓
Change Cipher Spec + Finished (双向)
       ↓
[加密数据传输]
```

**TLS 1.3 优化：** 减少到 1-RTT（完整握手）或 0-RTT（会话恢复）。

#### 1.4.1 HTTPS 完整握手流程：RSA vs ECDHE

**RSA 密钥交换（TLS 1.2，已不推荐）：**

```
Client                                    Server
  |                                          |
  |── Client Hello ──────────────────────>   |
  |   (支持的密码套件、随机数 ClientRandom)    |
  |                                          |
  |<──── Server Hello ─────────────────────  |
  |   (选定密码套件、随机数 ServerRandom)      |
  |<──── Certificate ──────────────────────  |
  |   (服务器公钥证书)                        |
  |                                          |
  |── Client Key Exchange ───────────────>   |
  |   (用服务器公钥加密 PreMasterSecret)      |
  |                                          |
  |   双方根据 ClientRandom + ServerRandom    |
  |   + PreMasterSecret 计算 MasterSecret    |
  |                                          |
  |── Change Cipher Spec ────────────────>   |
  |── Finished ──────────────────────────>   |
  |                                          |
  |<──── Change Cipher Spec ──────────────  |
  |<──── Finished ────────────────────────   |
  |                                          |
  |   [加密数据传输]                          |
```

RSA 握手的问题：
- **不支持前向保密（Forward Secrecy）**：如果服务器私钥泄露，所有历史流量都可以被解密
- **需要 2-RTT**：完整握手需要 2 个往返

**ECDHE 密钥交换（TLS 1.2/1.3，推荐）：**

```
Client                                    Server
  |                                          |
  |── Client Hello ──────────────────────>   |
  |   (支持的密码套件、ClientRandom、         |
  |    支持的椭圆曲线、客户端公钥)             |
  |                                          |
  |<──── Server Hello ─────────────────────  |
  |   (选定密码套件、ServerRandom、           |
  |    选定椭圆曲线、服务端公钥)               |
  |<──── Certificate ──────────────────────  |
  |<──── Server Key Exchange ──────────────  |
  |   (签名的 ECDH 参数)                     |
  |<──── Server Hello Done ───────────────   |
  |                                          |
  |   双方根据 ECDH 公钥计算 PreMasterSecret  |
  |                                          |
  |── Client Key Exchange ───────────────>   |
  |── Change Cipher Spec ────────────────>   |
  |── Finished ──────────────────────────>   |
  |                                          |
  |<──── Change Cipher Spec ──────────────  |
  |<──── Finished ────────────────────────   |
  |                                          |
  |   [加密数据传输]                          |
```

ECDHE 的优势：
- **支持前向保密**：每次会话使用临时密钥对，即使服务器私钥泄露也无法解密历史流量
- **性能更好**：ECDHE 比传统 DHE 快 10 倍以上

**TLS 1.3 握手（1-RTT）：**

```
Client                                    Server
  |                                          |
  |── Client Hello ──────────────────────>   |
  |   (支持的密码套件、ClientRandom、         |
  |    密钥共享：多个椭圆曲线的公钥)           |
  |                                          |
  |<──── Server Hello ─────────────────────  |
  |   (选定密码套件、密钥共享：服务端公钥)     |
  |<──── Encrypted Extensions ────────────  |
  |<──── Certificate ──────────────────────  |
  |<──── Certificate Verify ──────────────  |
  |<──── Finished ────────────────────────   |
  |                                          |
  |   此时双方已计算出会话密钥                 |
  |   后续消息全部加密                        |
  |                                          |
  |── Finished ──────────────────────────>   |
  |                                          |
  |   [加密数据传输]                          |
```

TLS 1.3 的关键改进：
- **1-RTT 握手**：比 TLS 1.2 少一个往返
- **0-RTT 恢复**：会话恢复时可以立即发送数据（有重放攻击风险）
- **移除不安全算法**：禁止 RSA 密钥交换、CBC 模式、SHA-1 等
- **加密握手**：Certificate 之后的消息全部加密

```bash
# 检查服务器是否支持 TLS 1.3
openssl s_client -connect www.example.com:443 -tls1_3 < /dev/null 2>/dev/null | grep "Protocol"

# 查看支持的密码套件
openssl s_client -connect www.example.com:443 < /dev/null 2>/dev/null | grep "Cipher"

# 对比 TLS 1.2 和 1.3 的握手时间
echo "=== TLS 1.2 ==="
curl -s -o /dev/null -w 'TLS 握手: %{time_appconnect}s\n' --tlsv1.2 --tls-max 1.2 https://www.example.com

echo "=== TLS 1.3 ==="
curl -s -o /dev/null -w 'TLS 握手: %{time_appconnect}s\n' --tlsv1.3 https://www.example.com
```

#### 1.4.2 证书验证过程

浏览器/客户端验证证书的完整流程：

```
1. 检查证书是否过期
   notBefore ≤ 当前时间 ≤ notAfter

2. 检查证书域名是否匹配
   CN (Common Name) 或 SAN (Subject Alternative Name) 匹配请求域名

3. 验证证书链
   服务器证书 → 中间 CA → 根 CA
   每一级都需要验证签名

4. 检查证书是否被吊销
   CRL (Certificate Revocation List) 或 OCSP (Online Certificate Status Protocol)

5. 检查根 CA 是否在信任列表中
   操作系统或浏览器内置的根证书列表
```

```bash
# 查看完整证书链
openssl s_client -connect www.example.com:443 -showcerts < /dev/null 2>/dev/null | \
  awk '/Certificate chain/,/---/'

# 检查 OCSP 响应
openssl s_client -connect www.example.com:443 -status < /dev/null 2>/dev/null | \
  grep -A 5 "OCSP response"

# 检查证书 SAN (Subject Alternative Name)
echo | openssl s_client -connect www.example.com:443 2>/dev/null | \
  openssl x509 -noout -ext subjectAltName
```

```bash
# 检查服务端支持的 TLS 版本和加密套件
openssl s_client -connect www.example.com:443 -tls1_2 < /dev/null 2>/dev/null | grep "Protocol\|Cipher"

# 查看证书详情
openssl s_client -connect www.example.com:443 < /dev/null 2>/dev/null | openssl x509 -noout -dates -subject -issuer

# 检查证书有效期剩余天数
echo | openssl s_client -connect www.example.com:443 2>/dev/null | \
  openssl x509 -noout -enddate | \
  sed 's/notAfter=//' | \
  xargs -I{} date -d "{}" +%s | \
  xargs -I{} bash -c 'echo $(( ({} - $(date +%s)) / 86400 )) 天'
```

#### 1.5 HTTP 请求与响应

**HTTP 状态码分类：**

| 状态码范围 | 含义 | 常见状态码 | SRE 应对 |
|-----------|------|-----------|---------|
| 1xx | 信息性 | 100 Continue | 一般无需关注 |
| 2xx | 成功 | 200 OK, 201 Created | 正常 |
| 3xx | 重定向 | 301, 302, 304 | 检查重定向链是否过长 |
| 4xx | 客户端错误 | 400, 401, 403, 404 | 检查请求格式、权限、路径 |
| 5xx | 服务端错误 | 500, 502, 503, 504 | **SRE 重点关注**：后端服务状态 |

**SRE 关键指标：**

```
TTFB (Time To First Byte):
  TTFB = DNS + TCP + TLS + 服务端处理时间
  
  优秀: < 200ms
  一般: 200-800ms
  差: > 800ms
```

### 2. HTTP/2 多路复用与 HTTP/3 改进

#### 2.1 HTTP/1.1 的问题

```
HTTP/1.1 的队头阻塞 (Head-of-Line Blocking):

请求 1: [======]
请求 2:       [======]      ← 必须等请求 1 完成
请求 3:             [======] ← 必须等请求 2 完成

浏览器的解决方案: 开启 6-8 个 TCP 连接
但每个连接仍然有队头阻塞问题
```

**HTTP/1.1 的其他限制：**
- 文本协议，解析效率低
- 无服务器推送能力
- Header 未压缩，冗余严重
- 每个连接只能处理一个请求-响应

#### 2.2 HTTP/2 多路复用

```
HTTP/2 的多路复用 (Multiplexing):

同一个 TCP 连接上，多个请求/响应可以交错传输:

Stream 1: [==]    [====]    [==]
Stream 2:   [===]    [==]     [====]
Stream 3:     [====]    [===]    [==]
          ─────────────────────────────> 时间
          
所有 Stream 共享一个 TCP 连接，互不阻塞
```

**HTTP/2 核心特性：**

| 特性 | 说明 | 性能影响 |
|------|------|---------|
| 多路复用 | 一个 TCP 连接并行处理多个请求 | 消除 HTTP 层队头阻塞 |
| 头部压缩 | HPACK 算法压缩 Header | 减少 50-90% Header 开销 |
| 二进制分帧 | 数据以二进制帧传输 | 解析效率提升 |
| 服务器推送 | 服务器主动推送资源 | 减少往返次数 |
| 流优先级 | 客户端指定资源优先级 | 优化加载顺序 |

**HTTP/2 帧结构：**

```
+-----------------------------------------------+
|                 Length (24)                    |
+---------------+---------------+---------------+
|   Type (8)    |   Flags (8)   |
+-+-------------+---------------+---------------+
|R|                 Stream ID (31)              |
+-+---------------------------------------------+
|                   Frame Payload               |
+-----------------------------------------------+

帧类型:
  DATA (0x00)     - 传输数据
  HEADERS (0x01)  - 传输 Header
  PRIORITY (0x02) - 设置优先级
  RST_STREAM (0x03) - 终止流
  SETTINGS (0x04) - 设置参数
  PUSH_PROMISE (0x05) - 服务器推送
  GOAWAY (0x07)   - 通知关闭连接
```

**HTTP/2 仍然存在的问题：**

```
TCP 层的队头阻塞:

虽然 HTTP/2 解决了 HTTP 层的队头阻塞，
但 TCP 层仍然有队头阻塞:

TCP 包: [1] [2] [3] [4] [5]
如果包 3 丢失:
  即使包 4、5 已到达，也必须等包 3 重传完成
  所有 HTTP/2 流都会被阻塞
```

#### 2.3 HTTP/3 与 QUIC 协议

```
HTTP/3 使用 QUIC 协议 (基于 UDP):

┌─────────────────────────────────────┐
│           HTTP/3                    │
├─────────────────────────────────────┤
│           QUIC                      │
│  (集成 TLS 1.3 + 多路复用 + 拥塞控制) │
├─────────────────────────────────────┤
│           UDP                       │
├─────────────────────────────────────┤
│           IP                        │
└─────────────────────────────────────┘
```

**HTTP/3 解决的问题：**

| 问题 | HTTP/2 | HTTP/3 |
|------|--------|--------|
| TCP 队头阻塞 | 存在 | 完全消除（每个 Stream 独立） |
| 连接建立延迟 | TCP + TLS = 2-3 RTT | QUIC = 0-1 RTT |
| 连接迁移 | IP 变化需重建连接 | Connection ID 迁移 |
| 加密范围 | 仅 Header+Body | 几乎所有内容加密 |

```bash
# 检查服务器是否支持 HTTP/3
curl --http3 -s -o /dev/null -w 'HTTP 版本: %{http_version}\n' https://www.example.com

# 使用 Alt-Svc 头检查 HTTP/3 支持
curl -sI https://www.example.com | grep -i alt-svc

# DNS 记录检查 HTTP/3 (HTTPS 记录)
dig +short HTTPS www.example.com
```

### 3. 服务器处理流程

#### 3.1 请求到达服务器后的处理链路

```
客户端请求
    │
    ▼
┌──────────────────┐
│   CDN 边缘节点   │  ← 静态资源缓存、DDoS 防护
└────────┬─────────┘
         │ (缓存未命中)
         ▼
┌──────────────────┐
│   负载均衡器      │  ← Nginx/HAProxy/ALB/NLB
│   (L4/L7)        │     健康检查、会话保持
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Web 服务器      │  ← Nginx/Apache/Caddy
│   (反向代理)      │     SSL 卸载、静态文件
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   应用服务器      │  ← Node.js/Python/Go/Java
│   (业务逻辑)      │     路由、中间件、业务处理
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   缓存层         │  ← Redis/Memcached
│                  │     热点数据缓存
└────────┬─────────┘
         │ (缓存未命中)
         ▼
┌──────────────────┐
│   数据库         │  ← MySQL/PostgreSQL/MongoDB
│                  │     持久化存储
└──────────────────┘
```

#### 3.2 每一层的性能指标

| 层级 | 关键指标 | 正常范围 | 告警阈值 |
|------|---------|---------|---------|
| CDN | 缓存命中率 | > 90% | < 80% |
| 负载均衡 | 连接数、健康节点数 | 全部健康 | 有节点不健康 |
| Web 服务器 | QPS、活跃连接数 | 视业务而定 | 突增 200% |
| 应用服务器 | 响应时间、错误率 | < 200ms, < 0.1% | > 500ms, > 1% |
| 缓存 | 命中率、内存使用 | > 95% | < 90% |
| 数据库 | 查询时间、连接池使用 | < 50ms | > 200ms |

### 4. 浏览器渲染流程

#### 4.1 从 HTML 到像素的完整渲染流水线

```
HTML 文本
    │
    ▼
┌──────────────────┐
│   HTML 解析器     │  解析 HTML 标记
│                  │  构建 DOM 树
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   CSS 解析器      │  解析 CSS 规则
│                  │  构建 CSSOM 树
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   合并 DOM+CSSOM │  构建 Render Tree
│                  │  (只包含可见元素)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Layout (布局)   │  计算每个元素的
│                  │  位置和大小
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Paint (绘制)    │  填充像素
│                  │  颜色、边框、阴影
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Composite      │  合成图层
│   (合成)         │  GPU 加速渲染
└──────────────────┘
```

#### 4.2 关键渲染路径 (Critical Rendering Path)

```
关键资源: 阻塞渲染的资源
  - CSS (同步加载，阻塞渲染)
  - JS (同步加载，阻塞 HTML 解析)
  - 字体 (FOIT/FOUT 问题)

优化策略:
  1. 内联关键 CSS
  2. 异步加载非关键 JS (async/defer)
  3. 预加载关键资源 (<link rel="preload">)
  4. 字体显示策略 (font-display: swap)
```

```bash
# 检查页面的关键渲染路径
curl -s https://www.example.com | grep -E '<link|<script' | head -20

# 检查资源加载顺序 (使用 Chrome DevTools)
# 打开 Chrome DevTools → Network → 查看瀑布图

# 检查是否使用了 preload/prefetch
curl -sI https://www.example.com | grep -i 'link'
```

#### 4.3 性能关键指标

| 指标 | 含义 | 目标值 | 测量工具 |
|------|------|--------|---------|
| FCP (First Contentful Paint) | 首次内容绘制 | < 1.8s | Lighthouse |
| LCP (Largest Contentful Paint) | 最大内容绘制 | < 2.5s | Lighthouse |
| FID (First Input Delay) | 首次输入延迟 | < 100ms | RUM |
| CLS (Cumulative Layout Shift) | 累积布局偏移 | < 0.1 | Lighthouse |
| TTFB (Time To First Byte) | 首字节时间 | < 200ms | curl |
| TTI (Time to Interactive) | 可交互时间 | < 3.8s | Lighthouse |

### 5. 资源加载优化

#### 5.1 资源加载策略

```html
<!-- 预加载关键资源 -->
<link rel="preload" href="/fonts/main.woff2" as="font" crossorigin>
<link rel="preload" href="/css/critical.css" as="style">
<link rel="preload" href="/js/app.js" as="script">

<!-- 预连接到第三方源 -->
<link rel="preconnect" href="https://cdn.example.com">
<link rel="dns-prefetch" href="https://analytics.example.com">

<!-- 异步加载非关键 JS -->
<script src="/js/analytics.js" async></script>
<script src="/js/utils.js" defer></script>
```

#### 5.2 并行下载优化

```
HTTP/1.1: 域名分片 (Domain Sharding)
  - 浏览器对同一域名限制 6-8 个连接
  - 将资源分散到多个子域名
  - img1.example.com, img2.example.com

HTTP/2: 不再需要域名分片
  - 单连接多路复用
  - 域名分片反而有害（增加 DNS 解析和连接开销）

HTTP/3: 连接复用更高效
  - 0-RTT 连接建立
  - 无 TCP 队头阻塞
```

### 6. 使用 curl 分析完整链路

#### 2.1 curl -vvv 输出解读

```bash
curl -vvv https://www.example.com
```

**输出结构分析：**

```text
*   Trying 93.184.216.34:443...          ← DNS 解析完成，开始 TCP 连接
* Connected to www.example.com (93.184.216.34) port 443 (#0)  ← TCP 连接建立
* ALPN: offers h2, http/1.1              ← TLS ALPN 协商
*  TLSv1.3 (OUT), TLS handshake, Client hello (1):  ← TLS 握手开始
*  TLSv1.3 (IN), TLS handshake, Server hello (2):
*  TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
*  TLSv1.3 (IN), TLS handshake, Certificate (11):      ← 证书验证
*  TLSv1.3 (IN), TLS handshake, CERT verify (15):
*  TLSv1.3 (IN), TLS handshake, Finished (20):
*  TLSv1.3 (OUT), TLS change cipher, Change cipher spec (1):
*  TLSv1.3 (OUT), TLS handshake, Finished (20):        ← TLS 握手完成
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* Server certificate:
*  subject: CN=www.example.com
*  start date: Jan  1 00:00:00 2024 GMT
*  expire date: Dec 31 23:59:59 2025 GMT              ← 证书过期时间
* Using HTTP2, server supports multiplexing
> GET / HTTP/2                        ← HTTP 请求发送
> Host: www.example.com
> User-Agent: curl/7.81.0
> Accept: */*
>
< HTTP/2 200                          ← HTTP 响应状态码
< date: Mon, 29 Apr 2026 06:00:00 GMT
< content-type: text/html
< content-length: 1256
<
<!DOCTYPE html>                       ← 响应体
```

#### 2.2 curl 时间分解（SRE 必备）

```bash
# 格式化输出各阶段耗时
curl -s -o /dev/null -w '
  DNS 解析:    %{time_namelookup}s
  TCP 连接:    %{time_connect}s
  TLS 握手:    %{time_appconnect}s
  开始传输:    %{time_starttransfer}s (TTFB)
  总耗时:      %{time_total}s
  下载速度:    %{speed_download} bytes/s
  响应码:      %{http_code}
  远程IP:      %{remote_ip}:%{remote_port}
  远程主机:    %{remote_ip}
  本地IP:      %{local_ip}
' https://www.example.com
```

**各时间字段含义：**

| 字段 | 含义 | 计算方式 |
|------|------|----------|
| time_namelookup | DNS 解析耗时 | 从开始到 DNS 完成 |
| time_connect | TCP 连接耗时 | 从开始到 TCP 握手完成 |
| time_appconnect | TLS 握手耗时 | 从开始到 TLS 握手完成 |
| time_pretransfer | 准备传输耗时 | TTFB 前的所有准备 |
| time_starttransfer | TTFB | 从开始到收到第一个字节 |
| time_total | 总耗时 | 从开始到传输完成 |
| time_redirect | 重定向耗时 | 所有重定向的总时间 |

### 3. DNS → TCP → TLS → HTTP 流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        从 URL 到页面完整流程                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  用户输入 URL: https://www.example.com/api/data                     │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 1. URL 解析   │  协议: https | 域名: www.example.com | 路径: /api/data │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 2. DNS 解析   │  Browser Cache → OS Cache → Recursive DNS         │
│  │              │  → Root (.) → TLD (.com) → Authoritative DNS      │
│  │              │  Result: 93.184.216.34                            │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 3. TCP 握手   │  Client ──SYN──> Server                          │
│  │  (三次握手)   │  Client <--SYN+ACK-- Server                       │
│  │              │  Client ──ACK──> Server    → ESTABLISHED           │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 4. TLS 握手   │  Client Hello → Server Hello + Certificate       │
│  │  (加密协商)   │  Key Exchange → Change Cipher Spec → Finished    │
│  │              │  Result: 加密通道建立 (TLS 1.3: 1-RTT)            │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 5. HTTP 请求  │  GET /api/data HTTP/2                            │
│  │              │  Headers: Host, Authorization, Accept...          │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 6. 服务端处理 │  Load Balancer → Web Server → App → Database     │
│  │              │  Processing: 50ms (business logic)                │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 7. HTTP 响应  │  HTTP/2 200 OK                                   │
│  │              │  Content-Type: application/json                   │
│  │              │  Body: {"status": "ok", "data": [...]}            │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ 8. 浏览器渲染 │  Parse HTML → CSSOM + DOM → Render Tree → Paint  │
│  └──────────────┘                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**各阶段关键时序标注：**

```
时间线 (假设理想网络, RTT=50ms):

|--DNS--|---TCP---|-----TLS-----|---HTTP Req---|---Server---|---Resp---|
  ~10ms    ~50ms     ~50ms(TLS1.3)   ~1ms          ~50ms        ~20ms
  |         |          |               |             |            |
  ▼         ▼          ▼               ▼             ▼            ▼
  [0ms]    [60ms]     [110ms]         [111ms]       [161ms]      [181ms]
  
  TTFB ≈ DNS + TCP + TLS + Server_Process ≈ 161ms
```

---

## 🛠️ 实战练习

### 练习 1：编写网络诊断脚本

编写一个综合网络诊断脚本，对目标站点进行多维度检测：

```bash
#!/bin/bash
# network_diagnose.sh - SRE 网络诊断脚本
# 用法: ./network_diagnose.sh <URL>

set -euo pipefail

TARGET="${1:?用法: $0 <URL>}"

echo "=========================================="
echo "  SRE 网络诊断报告"
echo "  目标: $TARGET"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. DNS 解析检测
echo ""
echo "[1/6] DNS 解析检测..."
echo "------------------------------------------"
if command -v dig &>/dev/null; then
    echo ">>> dig 结果:"
    dig +short "$TARGET" 2>/dev/null || echo "DNS 解析失败"
    echo ""
    echo ">>> 解析耗时:"
    dig +stats "$TARGET" 2>/dev/null | grep "Query time" || true
elif command -v nslookup &>/dev/null; then
    nslookup "$TARGET" 2>/dev/null || echo "DNS 解析失败"
fi

# 2. TCP 连通性检测
echo ""
echo "[2/6] TCP 连通性检测..."
echo "------------------------------------------"
HOST=$(echo "$TARGET" | sed -E 's|https?://||' | cut -d'/' -f1 | cut -d':' -f1)
PORT=$(echo "$TARGET" | grep -oP ':\K[0-9]+' || echo "443")

if command -v nc &>/dev/null; then
    START=$(date +%s%N)
    if nc -z -w5 "$HOST" "$PORT" 2>/dev/null; then
        END=$(date +%s%N)
        ELAPSED=$(( (END - START) / 1000000 ))
        echo "✅ TCP 连接成功: $HOST:$PORT (耗时: ${ELAPSED}ms)"
    else
        echo "❌ TCP 连接失败: $HOST:$PORT"
    fi
else
    timeout 5 bash -c "echo >/dev/tcp/$HOST/$PORT" 2>/dev/null && \
        echo "✅ TCP 连接成功: $HOST:$PORT" || \
        echo "❌ TCP 连接失败: $HOST:$PORT"
fi

# 3. TLS 证书检测
echo ""
echo "[3/6] TLS 证书检测..."
echo "------------------------------------------"
if command -v openssl &>/dev/null; then
    CERT_INFO=$(echo | openssl s_client -connect "$HOST:443" -servername "$HOST" 2>/dev/null | \
        openssl x509 -noout -subject -enddate -issuer 2>/dev/null)
    if [ -n "$CERT_INFO" ]; then
        echo "$CERT_INFO"
    else
        echo "⚠️ 无法获取证书信息"
    fi
fi

# 4. curl 时间分解
echo ""
echo "[4/6] curl 时间分解..."
echo "------------------------------------------"
curl -s -o /dev/null -w "
  DNS 解析:    %{time_namelookup}s
  TCP 连接:    %{time_connect}s
  TLS 握手:    %{time_appconnect}s
  TTFB:        %{time_starttransfer}s
  总耗时:      %{time_total}s
  下载速度:    %{speed_download} bytes/s
  HTTP 状态码: %{http_code}
  远程IP:      %{remote_ip}
" "$TARGET" 2>/dev/null || echo "❌ curl 请求失败"

# 5. HTTP 响应头分析
echo ""
echo "[5/6] HTTP 响应头分析..."
echo "------------------------------------------"
curl -sI -o /dev/null -w "
  HTTP/2 支持:    %{http_version}
  远程IP:         %{remote_ip}
  重定向次数:     %{num_redirects}
  SSL 验证:       %{ssl_verify_result}
" "$TARGET" 2>/dev/null || echo "❌ 无法获取响应头"

# 6. 连续 5 次延迟测试
echo ""
echo "[6/6] 连续延迟测试 (5次)..."
echo "------------------------------------------"
declare -a TIMES
for i in $(seq 1 5); do
    T=$(curl -s -o /dev/null -w '%{time_total}' "$TARGET" 2>/dev/null || echo "0")
    TIMES+=("$T")
    echo "  第 $i 次: ${T}s"
done

# 计算平均值
SUM=0
COUNT=0
for t in "${TIMES[@]}"; do
    if [[ "$t" != "0" ]]; then
        SUM=$(echo "$SUM + $t" | bc 2>/dev/null || echo "$SUM")
        COUNT=$((COUNT + 1))
    fi
done
if [ "$COUNT" -gt 0 ]; then
    AVG=$(echo "scale=3; $SUM / $COUNT" | bc 2>/dev/null || echo "N/A")
    echo "  平均延迟: ${AVG}s"
fi

echo ""
echo "=========================================="
echo "  诊断完成"
echo "=========================================="
```

**保存并运行：**

```bash
chmod +x network_diagnose.sh
./network_diagnose.sh https://www.example.com
```

### 练习 2：分析 curl -vvv 输出

```bash
# 保存详细输出到文件
curl -vvv --trace-time https://www.example.com 2>&1 | tee /tmp/curl_trace.log

# 关键信息提取
echo ""
echo "=== 关键信息提取 ==="
echo ""

# 1. DNS 解析 IP
grep "Trying" /tmp/curl_trace.log | head -5

# 2. TLS 版本和加密套件
grep "SSL connection using\|TLSv" /tmp/curl_trace.log | head -5

# 3. 证书信息
grep "subject:\|expire date:\|issuer:" /tmp/curl_trace.log

# 4. HTTP 状态码
grep "HTTP/" /tmp/curl_trace.log | head -5

# 5. 响应头
grep -E "^< " /tmp/curl_trace.log | head -20
```

### 练习 3：模拟故障排查

```bash
# 场景 1：DNS 污染/劫持
# 使用公共 DNS 对比
dig @8.8.8.8 www.example.com +short
dig @1.1.1.1 www.example.com +short
dig @114.114.114.114 www.example.com +short

# 场景 2：TCP 连接被拒绝
# 检查防火墙规则
sudo iptables -L -n | grep -E "DROP|REJECT"

# 场景 3：TLS 证书问题
# 检查证书链是否完整
openssl s_client -connect www.example.com:443 -showcerts < /dev/null 2>/dev/null | \
  grep -E "Certificate chain|s:|i:"

# 场景 4：HTTP 502 错误
# 检查上游服务状态
curl -s -o /dev/null -w '%{http_code}' https://www.example.com
```

---

## 📚 最新优质资源

### 官方文档
- [curl 官方文档](https://curl.se/docs/) - 完整的 curl 使用手册
- [OpenSSL 文档](https://www.openssl.org/docs/) - TLS/SSL 技术参考
- [DNS RFC 1035](https://datatracker.ietf.org/doc/html/rfc1035) - DNS 协议规范
- [HTTP/2 RFC 7540](https://datatracker.ietf.org/doc/html/rfc7540) - HTTP/2 规范
- [TLS 1.3 RFC 8446](https://datatracker.ietf.org/doc/html/rfc8446) - TLS 1.3 规范

### 教程与文章
- [从输入 URL 到页面加载完成发生了什么](https://github.com/skyline75489/what-happens-when-zh_CN) - 经典面试题详解
- [Mozilla TLS 配置指南](https://wiki.mozilla.org/Security/Server_Side_TLS) - TLS 最佳实践
- [Cloudflare DNS 学习中心](https://www.cloudflare.com/learning/dns/) - DNS 原理通俗讲解
- [HTTP/3 与 QUIC 协议](https://blog.cloudflare.com/http3-the-past-present-and-future/) - Cloudflare 技术博客

### 工具与在线服务
- [curl.haxx.se](https://curl.se/) - curl 官方主页
- [SSL Labs 测试](https://www.ssllabs.com/ssltest/) - TLS 配置在线检测
- [DNSViz](https://dnsviz.net/) - DNS 链路可视化工具
- [DNS Propagation Checker](https://dnschecker.org/) - 全球 DNS 传播检测

### SRE 相关
- [Google SRE Book - Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) - SRE 监控章节
- [Network Troubleshooting for SREs](https://www.oreilly.com/library/view/learning-sre/9781492076070/ch04.html) - O'Reilly 学习 SRE 第4章

---

## 🎯 面试题精选

### 面试题 1：从输入 URL 到页面展示，中间经历了哪些过程？

**参考答案：**

完整过程可以分为以下几个阶段：

**网络阶段：**
1. **URL 解析**：浏览器解析 URL，提取协议、域名、端口、路径、查询参数
2. **DNS 解析**：浏览器缓存 → 操作系统缓存 → 本地 DNS 服务器 → 递归查询（根 DNS → TLD DNS → 权威 DNS）→ 返回 IP 地址
3. **TCP 三次握手**：客户端发送 SYN → 服务端回复 SYN+ACK → 客户端发送 ACK，建立可靠连接
4. **TLS 握手**（HTTPS）：Client Hello → Server Hello + Certificate → 密钥交换 → 加密通道建立
5. **HTTP 请求**：构建请求报文（方法、URL、Header、Body），发送到服务器

**服务端阶段：**
6. **负载均衡**：请求到达负载均衡器，根据算法转发到后端服务器
7. **Web 服务器处理**：Nginx 反向代理、SSL 卸载、静态文件服务
8. **应用处理**：业务逻辑执行、数据库查询、缓存读写
9. **HTTP 响应**：返回状态码、响应头、响应体

**浏览器阶段：**
10. **HTML 解析**：构建 DOM 树
11. **CSS 解析**：构建 CSSOM 树
12. **合成渲染树**：DOM + CSSOM → Render Tree
13. **布局（Layout）**：计算元素位置和大小
14. **绘制（Paint）**：填充像素
15. **合成（Composite）**：GPU 合成图层
16. **资源加载**：JS、CSS、图片等资源并行下载和执行

### 面试题 2：每一步可以做什么优化？

**参考答案：**

| 阶段 | 优化手段 |
|------|---------|
| DNS | DNS 预解析、DNS 缓存、使用 CDN 就近解析、HTTPDNS |
| TCP | TCP 连接复用、TCP Fast Open、调整内核参数（somaxconn、backlog） |
| TLS | TLS 1.3（1-RTT）、OCSP Stapling、会话恢复、ECDHE |
| HTTP | HTTP/2 多路复用、HTTP/3（QUIC）、Header 压缩、资源合并 |
| 服务端 | 缓存（Redis/CDN）、数据库优化、异步处理、水平扩展 |
| 浏览器 | 关键 CSS 内联、JS 异步加载、图片懒加载、资源预加载 |

### 面试题 3：TCP 三次握手为什么是三次而不是两次？

**参考答案：**

两次握手的问题：如果客户端发送的 SYN 报文在网络中滞留，客户端会重发 SYN 并建立连接，数据传输完成后关闭连接。此时滞留的 SYN 到达服务端，服务端会误以为是新的连接请求，回复 SYN+ACK 并进入 ESTABLISHED 状态，但客户端不会回复，造成服务端资源浪费（半连接）。

三次握手的核心目的是**同步双方的初始序列号（ISN）**：
- 第一次：客户端告诉服务端自己的 ISN
- 第二次：服务端告诉客户端自己的 ISN，并确认客户端的 ISN
- 第三次：客户端确认服务端的 ISN

### 面试题 4：HTTPS 的完整握手过程是怎样的？

**参考答案：**

以 TLS 1.3 为例（1-RTT 握手）：
1. **Client Hello**：客户端发送支持的密码套件列表、ClientRandom、密钥共享（多个椭圆曲线的公钥）
2. **Server Hello**：服务端选择密码套件、生成 ServerRandom、选择密钥共享
3. **Encrypted Extensions**：服务端发送加密扩展
4. **Certificate**：服务端发送证书（此消息开始加密）
5. **Certificate Verify**：服务端证明拥有证书对应的私钥
6. **Finished**：服务端握手完成确认
7. **Finished**：客户端握手完成确认

此后双方使用协商的对称密钥加密通信。

### 面试题 5：HTTP/2 相比 HTTP/1.1 有哪些改进？

**参考答案：**

1. **多路复用**：一个 TCP 连接上可以并行处理多个请求-响应，解决了 HTTP 层的队头阻塞
2. **头部压缩**：使用 HPACK 算法压缩 Header，减少冗余
3. **二进制分帧**：数据以二进制帧传输，解析效率更高
4. **服务器推送**：服务器可以主动推送资源给客户端
5. **流优先级**：客户端可以指定资源加载优先级

### 面试题 6：HTTP/3 为什么选择基于 UDP 而不是 TCP？

**参考答案：**

TCP 的队头阻塞问题在传输层无法解决。当 TCP 包丢失时，即使后续包已到达也必须等待重传，这会阻塞所有 HTTP/2 流。

HTTP/3 使用 QUIC 协议（基于 UDP）的优势：
1. **消除队头阻塞**：每个 Stream 独立，丢包只影响当前 Stream
2. **更快的连接建立**：QUIC 集成 TLS 1.3，0-1 RTT 建立连接
3. **连接迁移**：基于 Connection ID 而非 IP+Port，网络切换不断连
4. **更好的拥塞控制**：可自定义拥塞控制算法

### 面试题 7：什么是 TTFB？如何优化？

**参考答案：**

TTFB（Time To First Byte）是从发起请求到收到第一个字节的时间，包括：
- DNS 解析时间
- TCP 连接时间
- TLS 握手时间
- 服务端处理时间

优化方法：
1. 使用 CDN 减少网络距离
2. 优化 DNS 解析（DNS 预解析、HTTPDNS）
3. 使用 HTTP/2 或 HTTP/3 减少连接开销
4. 优化服务端处理（缓存、数据库优化、异步处理）
5. 使用连接复用（Keep-Alive）

### 面试 8：浏览器渲染过程中，什么情况会触发回流（Reflow）和重绘（Repaint）？

**参考答案：**

**回流（Reflow）**：元素的布局发生变化，需要重新计算位置和大小
- 触发条件：DOM 增删、元素尺寸改变、窗口大小改变、字体大小改变
- 影响范围：回流会触发重绘

**重绘（Repaint）**：元素的外观变化，不影响布局
- 触发条件：颜色改变、背景色改变、边框样式改变
- 影响范围：只影响当前元素

优化建议：
- 使用 `transform` 代替 `top/left`（只触发合成，不触发回流）
- 批量修改 DOM（使用 DocumentFragment）
- 使用 `will-change` 提示浏览器优化

---

## 📝 笔记

### 今日总结

1. **完整链路回顾**：从 URL 输入到页面展示，经历了 URL 解析 → DNS → TCP → TLS → HTTP → 服务端处理 → 响应 → 渲染 八个阶段。每个阶段都可能成为性能瓶颈或故障点。

2. **SRE 核心视角**：
   - **可观测性**：每个阶段都需要有对应的监控指标
   - **快速定位**：通过分层排查，快速隔离故障发生在哪个阶段
   - **自动化**：将常用排查命令封装成脚本，提升效率

3. **关键性能指标**：
   - DNS 解析 < 50ms
   - TCP 握手 < 1×RTT
   - TLS 握手 < 2×RTT (TLS 1.3: 1×RTT)
   - TTFB < 200ms (优秀)
   - 页面加载 < 3s

4. **协议演进路线**：
   - HTTP/1.1 → HTTP/2：解决 HTTP 层队头阻塞
   - HTTP/2 → HTTP/3：解决 TCP 层队头阻塞
   - TLS 1.2 → TLS 1.3：减少握手 RTT，移除不安全算法

### 问题记录

- [ ] DNS over HTTPS (DoH) 和 DNS over TLS (DoT) 的对比
- [ ] TCP 拥塞控制算法 (BBR vs CUBIC) 对网络性能的影响
- [ ] QUIC 协议的连接迁移机制细节
- [ ] HTTP/3 0-RTT 的重放攻击防护

### 延伸思考

- 如何在微服务架构中追踪完整的请求链路？→ 分布式追踪 (Jaeger/Zipkin)
- CDN 如何改变这个流程？→ CDN 边缘节点提前终止 TLS 和 HTTP
- 如何设计一个端到端的网络可用性监控系统？→ 多地域探测 + 多协议检测

---

## ✅ 完成检查

- [x] 复习了从 URL 到页面的完整技术链路
- [x] 绘制了 DNS → TCP → TLS → HTTP 流程图
- [x] 编写了网络诊断脚本 (network_diagnose.sh)
- [x] 学习了 curl -vvv 输出的逐行分析方法
- [x] 掌握了 curl 时间分解的各阶段含义
- [ ] **自我评估**：能独立解释「网站打不开」的 5 种可能原因

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释从 URL 到页面的完整 20+ 步骤
- [ ] 能说明 DNS 解析的完整流程（浏览器缓存 → OS 缓存 → 递归查询）
- [ ] 能解释 TCP 三次握手的原因和过程
- [ ] 能区分 TLS 1.2 和 TLS 1.3 的握手流程
- [ ] 能说明 RSA 和 ECDHE 密钥交换的区别
- [ ] 能解释 HTTP/2 多路复用的原理
- [ ] 能说明 HTTP/3 为什么基于 UDP
- [ ] 能描述浏览器渲染流水线（DOM → CSSOM → Render Tree → Layout → Paint）

### 实操检查点
- [ ] 能用 curl -vvv 分析完整请求过程
- [ ] 能用 curl -w 输出各阶段耗时
- [ ] 能用 openssl 检查 TLS 证书和握手
- [ ] 能用 dig 追踪 DNS 解析链
- [ ] 能编写网络诊断脚本
- [ ] 能分析 TTFB 并定位性能瓶颈

### 故障排查能力检查
- [ ] 能快速判断「网站打不开」的原因在哪一层
- [ ] 能通过 curl 时间分解定位 TLS 性能问题
- [ ] 能通过 DNS 对比排查 DNS 劫持/污染
- [ ] 能通过抓包分析 TCP 握手失败原因

### 自我评估答案参考

「网站打不开」的 5 种可能原因：

| 序号 | 可能原因 | 排查命令 | 判断依据 |
|------|---------|---------|---------|
| 1 | **DNS 解析失败** | `dig www.example.com` | 无法获取 IP 或返回错误 |
| 2 | **TCP 连接失败** | `nc -zv www.example.com 443` | Connection refused / Timeout |
| 3 | **TLS 证书问题** | `openssl s_client -connect` | 证书过期、不受信任、不匹配 |
| 4 | **HTTP 服务端错误** | `curl -v https://www.example.com` | 返回 5xx 状态码 |
| 5 | **客户端网络问题** | `ping 8.8.8.8` / `traceroute` | 本地网络不通或路由异常 |

---

> 📌 **明日预告**：Day 36 将深入学习网络诊断工具 — ping、traceroute、mtr、dig，并通过实战案例分析运营商丢包问题。
