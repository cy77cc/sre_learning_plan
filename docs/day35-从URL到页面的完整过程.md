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

### 2. 使用 curl 分析完整链路

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

### 问题记录

- [ ] 需要深入了解 HTTP/3 和 QUIC 协议的区别
- [ ] DNS over HTTPS (DoH) 和 DNS over TLS (DoT) 的对比
- [ ] TCP 拥塞控制算法 (BBR vs CUBIC) 对网络性能的影响

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
