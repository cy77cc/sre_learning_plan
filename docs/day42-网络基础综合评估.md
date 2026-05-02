# Day 42: 网络基础综合评估

> 📅 日期：2026-05-02
> 📖 学习主题：网络基础综合评估
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 综合评估前三周网络知识（OSI 模型、TCP/IP、DNS、HTTP）
- 能独立完成网络故障排查
- 掌握网络工具的实战组合使用

---

## 📖 综合知识回顾

### 1. 网络分层回顾

```
应用层 (7)    HTTP, DNS, SMTP, FTP        ← 用户看到的协议
表示层 (6)    TLS, SSL, JPEG              ← 数据格式和加密
会话层 (5)    NetBIOS, RPC                ← 会话管理
传输层 (4)    TCP, UDP                    ← 端到端传输
网络层 (3)    IP, ICMP, ARP               ← 路由和寻址
数据链路层(2)  Ethernet, WiFi              ← 帧传输
物理层 (1)    光纤, 电缆, 无线电            ← 比特流
```

### 2. TCP vs UDP 对比

| 特性 | TCP | UDP |
|------|-----|-----|
| 连接 | 面向连接（三次握手） | 无连接 |
| 可靠性 | 可靠（重传、排序、确认） | 不可靠 |
| 拥塞控制 | 有 | 无 |
| 头部开销 | 20 字节 | 8 字节 |
| 速度 | 较慢 | 较快 |
| 适用场景 | 文件传输、Web、邮件 | 视频、游戏、DNS |

### 3. 常见端口速查

| 端口 | 协议 | 用途 |
|------|------|------|
| 21 | FTP | 文件传输 |
| 22 | SSH | 安全远程登录 |
| 25 | SMTP | 邮件发送 |
| 53 | DNS | 域名解析 |
| 80 | HTTP | Web 服务 |
| 443 | HTTPS | 安全 Web |
| 3306 | MySQL | 数据库 |
| 6379 | Redis | 缓存 |
| 8080 | HTTP Alt | Web 代理 |

### 4. TCP 三次握手与四次挥手

```
三次握手（建立连接）：
  Client                    Server
    │                         │
    │ ─── SYN (seq=x) ──────→│
    │                         │
    │ ←── SYN+ACK (seq=y,    │
    │      ack=x+1) ─────────│
    │                         │
    │ ─── ACK (ack=y+1) ───→│
    │                         │
    │ ←── 数据传输 ──→        │

四次挥手（关闭连接）：
  Client                    Server
    │                         │
    │ ─── FIN ──────────────→│
    │ ←── ACK ───────────────│
    │                         │
    │ ←── FIN ───────────────│
    │ ─── ACK ──────────────→│
    │                         │
    │        TIME_WAIT (2MSL) │
```

---

## 🏗️ 网络故障排查流程

```bash
# 接到告警：服务不可达

# 第 1 步：DNS 解析
dig example.com +short
nslookup example.com
# 如果解析失败 → DNS 问题

# 第 2 步：连通性
ping example.com
# 如果不通 → 网络不通或 ICMP 被禁

# 第 3 步：端口连通性
nc -zv example.com 443
# 如果不通 → 防火墙或服务未启动

# 第 4 步：HTTP 层面
curl -v https://example.com
# 如果返回 5xx → 服务端错误
# 如果返回 4xx → 客户端/认证问题
# 如果超时 → 服务挂起或网络慢

# 第 5 步：路由跟踪
mtr example.com
# 查看在哪一跳丢包

# 第 6 步：抓包分析
sudo tcpdump -i eth0 host example.com -w /tmp/capture.pcap
# 用 wireshark 打开分析

# 第 7 步：检查本地状态
ss -tlnp          # 本地监听端口
ss -tnp           # 已建立的连接
ip addr show      # IP 地址配置
ip route show     # 路由表
```

---

## 🧪 综合练习

### 练习 1：诊断脚本

编写一个脚本，自动诊断网络连通性问题。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
TARGET="${1:?用法: $0 <hostname>}"

echo "=== 网络诊断: $TARGET ==="

# DNS
echo -n "DNS 解析: "
if ip=$(dig +short "$TARGET" | head -1); then
    echo "✅ $ip"
else
    echo "❌ 解析失败"; exit 1
fi

# Ping
echo -n "Ping: "
if ping -c 1 -W 2 "$TARGET" &>/dev/null; then
    echo "✅ 通"
else
    echo "❌ 不通"
fi

# Port 443
echo -n "端口 443: "
if nc -zv "$TARGET" 443 2>&1 | grep -q succeeded; then
    echo "✅ 开放"
else
    echo "❌ 关闭"
fi

# HTTP
echo -n "HTTP: "
code=$(curl -s -o /dev/null -w "%{http_code}" "https://$TARGET" 2>/dev/null)
if [[ "$code" == "200" ]]; then
    echo "✅ $code"
else
    echo "❌ $code"
fi

# 时间分解
echo ""
echo "=== 时间分解 ==="
curl -s -o /dev/null -w "DNS: %{time_namelookup}s\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" "https://$TARGET"
```
</details>

---

## 📚 扩展阅读

- [TCP/IP Illustrated](https://www.pearson.com/en-us/subject-catalog/p/tcp-ip-illustrated-volume-1-the-protocols/P200000003057/9780134927883)
- [Wireshark 官方教程](https://www.wireshark.org/docs/)
- [mtr 文档](https://github.com/traviscross/mtr)
