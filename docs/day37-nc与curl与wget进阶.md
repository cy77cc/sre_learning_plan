# Day 37: 网络工具进阶 — nc / curl / wget

> 📅 日期：2026-05-01
> 📖 学习主题：nc / curl / wget 进阶用法与 SRE 实战
> ⏰ 计划学习时间：2-3 小时

## 🎯 学习目标

- [ ] 掌握 nc (netcat) 的进阶用法：端口测试、文件传输、简单服务
- [ ] 深入理解 curl 时间分解：-w 格式化输出各阶段耗时
- [ ] 掌握 wget 的高级用法：断点续传、限速、批量下载
- [ ] 通过 SRE 实战案例：nc 测试端口通但应用连不上 → bind-address 问题
- [ ] 编写健康检查脚本，支持 HTTP/TCP/自定义协议
- [ ] 扩展：用 curl --resolve 强制解析进行服务测试

---

## 📖 详细知识点

### 1. nc (netcat) — 网络瑞士军刀

#### 1.1 nc 简介

nc (netcat) 被称为"网络瑞士军刀"，可以读取和写入 TCP/UDP 连接，是 SRE 必备的网络工具。

**两个主要版本：**

| 版本 | 包名 | 特点 |
|------|------|------|
| GNU netcat | `netcat` / `ncat` | 功能丰富，支持 SSL、IPv6 |
| OpenBSD netcat | `netcat-openbsd` | Linux 默认，简洁稳定 |

```bash
# 检查版本
nc -h 2>&1 | head -3

# Ubuntu 查看默认版本
dpkg -l | grep netcat
```

#### 1.2 端口连通性测试（SRE 最常用）

```bash
# TCP 端口测试 (OpenBSD netcat)
nc -zv 192.168.1.100 80        # -z: 扫描模式, -v: 详细输出
nc -zv 192.168.1.100 443
nc -zv 192.168.1.100 8080

# 指定超时时间
nc -zv -w 5 192.168.1.100 80

# 端口范围扫描
nc -zv 192.168.1.100 1-1024

# UDP 端口测试
nc -zvu 192.168.1.100 53

# 同时测试多个端口
for port in 80 443 8080 8443 3306 6379; do
    nc -zv -w 3 192.168.1.100 $port 2>&1
done
```

#### 1.3 nc 作为简易服务器

```bash
# 启动 TCP 监听
nc -lvnp 8080

# 接收文件 (服务端)
nc -lvnp 9000 > received_file.txt

# 发送文件 (客户端)
nc -vn 192.168.1.100 9000 < file_to_send.txt

# 简易 HTTP 服务器
while true; do
    echo -e "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<h1>Hello from nc!</h1>" | nc -lvnp 8080
done

# 简易聊天室
# 机器 A: nc -lvnp 5555
# 机器 B: nc <IP_A> 5555
```

#### 1.4 网络带宽测试

```bash
# 带宽测试 (服务端)
nc -lvnp 5000 > /dev/null

# 带宽测试 (客户端)
dd if=/dev/zero bs=1M count=100 2>/dev/null | nc -vn <server_ip> 5000
# 通过传输时间和数据量估算带宽
```

### 2. curl — HTTP 客户端之王

#### 2.1 curl 时间分解（SRE 核心技能）

curl 的 `-w` (--write-out) 参数可以输出请求各阶段的耗时，是性能分析的利器。

```bash
# 完整时间分解
curl -s -o /dev/null -w '
  ┌──────────────────────────────────────┐
  │        curl 时间分解报告              │
  ├──────────────────────────────────────┤
  │  DNS 解析:    %{time_namelookup}s    │
  │  TCP 连接:    %{time_connect}s       │
  │  TLS 握手:    %{time_appconnect}s    │
  │  准备传输:    %{time_pretransfer}s   │
  │  TTFB:        %{time_starttransfer}s │
  │  总耗时:      %{time_total}s         │
  ├──────────────────────────────────────┤
  │  下载速度:    %{speed_download} B/s  │
  │  上传速度:    %{speed_upload} B/s    │
  │  下载大小:    %{size_download} bytes │
  │  HTTP 状态:   %{http_code}           │
  │  HTTP 版本:   %{http_version}        │
  │  远程IP:      %{remote_ip}           │
  │  本地IP:      %{local_ip}            │
  │  远程端口:    %{remote_port}         │
  │  重定向次数:  %{num_redirects}       │
  │  SSL 验证:    %{ssl_verify_result}   │
  │  内容类型:    %{content_type}        │
  └──────────────────────────────────────┘
' https://www.example.com
```

#### 2.2 各阶段时间详解

| 字段 | 含义 | 包含阶段 | 计算公式 |
|------|------|---------|---------|
| time_namelookup | DNS 解析时间 | DNS 查询 | - |
| time_connect | TCP 连接时间 | DNS + TCP 握手 | time_connect - time_namelookup = TCP 耗时 |
| time_appconnect | TLS 连接时间 | DNS + TCP + TLS | time_appconnect - time_connect = TLS 耗时 |
| time_pretransfer | 准备传输时间 | DNS + TCP + TLS + 请求准备 | - |
| time_starttransfer | 首字节时间 (TTFB) | DNS + TCP + TLS + 服务端处理 | time_starttransfer - time_appconnect = 服务端处理 + 请求发送 |
| time_total | 总时间 | 全部 | - |
| time_redirect | 重定向总时间 | 所有重定向阶段 | - |

**各阶段耗时计算：**

```bash
# 计算各阶段独立耗时
curl -s -o /dev/null -w '
DNS 解析:    %{time_namelookup}s
TCP 握手:    $(echo "%{time_connect} - %{time_namelookup}" | bc)s
TLS 握手:    $(echo "%{time_appconnect} - %{time_connect}" | bc)s
服务端处理:  $(echo "%{time_starttransfer} - %{time_appconnect}" | bc)s
响应下载:    $(echo "%{time_total} - %{time_starttransfer}" | bc)s
' https://www.example.com
```

#### 2.3 curl 进阶用法

```bash
# 指定 HTTP 方法
curl -X GET https://api.example.com/data
curl -X POST -H "Content-Type: application/json" -d '{"key":"value"}' https://api.example.com/data
curl -X PUT -H "Content-Type: application/json" -d '{"id":1}' https://api.example.com/data/1
curl -X DELETE https://api.example.com/data/1

# 下载文件
curl -O https://example.com/file.tar.gz          # 保留原文件名
curl -o custom_name.tar.gz https://example.com/file.tar.gz  # 自定义文件名

# 断点续传
curl -C - -O https://example.com/large_file.zip

# 限速下载
curl --limit-rate 1M -O https://example.com/file.zip

# 重试机制
curl --retry 3 --retry-delay 5 --retry-max-time 30 https://api.example.com

# Cookie 处理
curl -b cookies.txt -c cookies.txt https://example.com

# 请求头自定义
curl -H "Authorization: Bearer token123" \
     -H "Accept: application/json" \
     -H "User-Agent: MySRETool/1.0" \
     https://api.example.com/data

# 代理使用
curl -x http://proxy.example.com:8080 https://api.example.com
curl -x socks5://proxy.example.com:1080 https://api.example.com

# 静默模式 + 错误码检查
curl -sS -f -o /dev/null https://api.example.com/health || echo "请求失败，退出码: $?"

# 并行请求 (curl 7.66+)
curl --parallel https://a.example.com https://b.example.com https://c.example.com
```

#### 2.4 curl 退出码

| 退出码 | 含义 | SRE 处理 |
|--------|------|---------|
| 0 | 成功 | 正常 |
| 6 | 无法解析主机 | DNS 问题 |
| 7 | 连接失败 | 目标服务不可达 |
| 28 | 操作超时 | 网络慢或服务无响应 |
| 35 | TLS 握手失败 | 证书或加密问题 |
| 51 | 证书验证失败 | 证书不受信任 |
| 52 | 服务器返回空响应 | 服务端异常 |
| 56 | 接收数据失败 | 网络中断 |

### 3. wget — 下载利器

#### 3.1 wget 常用命令

```bash
# 基础下载
wget https://example.com/file.tar.gz

# 保存到指定文件
wget -O output.tar.gz https://example.com/file.tar.gz

# 后台下载
wget -b https://example.com/large_file.zip

# 限速下载
wget --limit-rate=2m https://example.com/file.zip

# 断点续传
wget -c https://example.com/large_file.zip

# 指定重试次数和间隔
wget --tries=5 --waitretry=10 https://example.com/file.zip

# 静默模式
wget -q https://example.com/file.zip

# 递归下载 (镜像)
wget -r -l 3 -p -k https://example.com

# 批量下载 (从文件读取 URL)
wget -i urls.txt

# 下载时跳过证书验证
wget --no-check-certificate https://example.com/file.zip

# 仅检查文件是否存在 (不下载)
wget --spider https://example.com/file.zip
```

#### 3.2 curl vs wget 对比

| 特性 | curl | wget |
|------|------|------|
| 协议支持 | HTTP/HTTPS/FTP/SMTP/POP3/IMAP/LDAP 等 | HTTP/HTTPS/FTP |
| 默认行为 | 输出到 stdout | 保存到文件 |
| 递归下载 | 不支持 | 支持 (-r) |
| 进度条 | 简洁进度 | 详细进度 |
| 管道支持 | 优秀 | 一般 |
| 脚本友好 | 非常友好 | 友好 |
| 表单提交 | 支持 (-F) | 有限 |
| Cookie | 支持 | 支持 |
| 代理 | 支持 | 支持 |
| SRE 推荐 | ⭐⭐⭐⭐⭐ (API 测试/诊断) | ⭐⭐⭐ (文件下载) |

---

## 🛠️ SRE 实战案例

### 案例：nc 测试端口通但应用连不上 → bind-address 问题

#### 背景

某 SRE 值班人员收到告警：应用服务报"连接数据库超时"，但网络层面检测一切正常。

#### 排查过程

**Step 1：确认网络连通性**

```bash
# 网络层检测 — 正常
$ nc -zv db-server.example.com 3306
Connection to db-server.example.com 3306 port [tcp/mysql] succeeded! ✅

$ telnet db-server.example.com 3306
Trying 10.0.1.50...
Connected to db-server.example.com. ✅

$ curl -v telnet://db-server.example.com:3306
*   Trying 10.0.1.50:3306...
* Connected to db-server.example.com (10.0.1.50) port 3306 ✅
```

**Step 2：确认端口监听状态**

```bash
# 登录数据库服务器检查
ssh db-server.example.com

$ netstat -tlnp | grep 3306
tcp        0      0 127.0.0.1:3306          0.0.0.0:*               LISTEN      1234/mysqld
```

**发现问题！** MySQL 绑定在 `127.0.0.1`（localhost），而不是 `0.0.0.0`。

**Step 3：分析为什么 nc 能通但应用连不上**

```bash
# nc -zv 测试的是从客户端机器到服务器 3306 端口的 TCP 连接
# 但如果 nc 在数据库服务器本地执行，连 127.0.0.1:3306 当然可以！

# 关键区别:
# nc 在数据库服务器上执行 → 连接 127.0.0.1:3306 → ✅ 成功
# 应用在另一台服务器上 → 连接 10.0.1.50:3306 → ❌ 被拒绝
```

**验证方法：**

```bash
# 从应用服务器测试
$ nc -zv db-server.example.com 3306
nc: connect to db-server.example.com port 3306 (tcp) failed: Connection refused ❌

# 从数据库服务器本地测试
$ nc -zv 127.0.0.1 3306
Connection to 127.0.0.1 3306 port [tcp/mysql] succeeded! ✅

$ nc -zv 10.0.1.50 3306   # 从本地连自己的外网 IP
nc: connect to 10.0.1.50 port 3306 (tcp) failed: Connection refused ❌
```

**结论：**

```
bind-address = 127.0.0.1 只允许本地连接
bind-address = 0.0.0.0  允许所有 IP 连接
bind-address = 10.0.1.50 只允许指定 IP 连接
```

**解决方案：**

```bash
# 修改 MySQL 配置
sudo vim /etc/mysql/mysql.conf.d/mysqld.cnf

# 找到 bind-address 行
# bind-address = 127.0.0.1    ← 原来的
bind-address = 0.0.0.0        ← 修改后 (允许所有连接)
# 或
bind-address = 10.0.1.0/24    ← 修改后 (仅允许子网)

# 重启 MySQL
sudo systemctl restart mysql

# 验证
$ netstat -tlnp | grep 3306
tcp        0      0 0.0.0.0:3306            0.0.0.0:*               LISTEN      1234/mysqld  ✅

# 授权远程用户
mysql -u root -p
mysql> CREATE USER 'app_user'@'10.0.1.%' IDENTIFIED BY 'password';
mysql> GRANT ALL PRIVILEGES ON app_db.* TO 'app_user'@'10.0.1.%';
mysql> FLUSH PRIVILEGES;
```

#### 经验总结

| 排查步骤 | 工具 | 判断 |
|---------|------|------|
| 网络是否可达 | ping | ICMP 通 = 网络层正常 |
| TCP 端口是否开放 | nc -zv | Connection refused = 端口关闭 |
| 服务是否监听正确地址 | netstat/ss | bind-address 决定监听范围 |
| 从正确位置测试 | nc -zv | **必须在客户端位置测试** |

**SRE 最佳实践：**

```bash
# 永远从客户端角度测试，而不是在服务器本地测试
# 错误做法: ssh db-server && nc -zv localhost 3306
# 正确做法: nc -zv db-server 3306  (从应用服务器执行)

# 使用 ss 查看监听地址
ss -tlnp | grep 3306
# LISTEN  0  128  127.0.0.1:3306  *:*    ← 仅本地
# LISTEN  0  128  0.0.0.0:3306   *:*    ← 所有地址
# LISTEN  0  128  10.0.1.50:3306 *:*    ← 指定地址
```

---

## 🛠️ 实战练习

### 练习 1：编写健康检查脚本

```bash
#!/bin/bash
# health_check.sh - SRE 服务健康检查脚本
# 用法: ./health_check.sh <配置文件> 或 ./health_check.sh

set -uo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志文件
LOG_FILE="health_check_$(date +%Y%m%d_%H%M%S).log"

log() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] $1" | tee -a "$LOG_FILE"
}

check_http() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"
    local timeout="${4:-5}"
    
    local start_time
    start_time=$(date +%s%N)
    
    local response
    response=$(curl -s -o /dev/null -w '%{http_code}' --max-time "$timeout" "$url" 2>/dev/null)
    local exit_code=$?
    
    local end_time
    end_time=$(date +%s%N)
    local elapsed=$(( (end_time - start_time) / 1000000 ))
    
    if [ "$exit_code" -ne 0 ]; then
        log "${RED}[FAIL]${NC} HTTP - $name: 请求失败 (退出码: $exit_code, 耗时: ${elapsed}ms)"
        return 1
    elif [ "$response" = "$expected_code" ]; then
        log "${GREEN}[OK]${NC}   HTTP - $name: HTTP $response (耗时: ${elapsed}ms)"
        return 0
    else
        log "${YELLOW}[WARN]${NC} HTTP - $name: 期望 $expected_code, 实际 $response (耗时: ${elapsed}ms)"
        return 1
    fi
}

check_tcp() {
    local name="$1"
    local host="$2"
    local port="$3"
    local timeout="${4:-3}"
    
    local start_time
    start_time=$(date +%s%N)
    
    if nc -z -w "$timeout" "$host" "$port" 2>/dev/null; then
        local end_time
        end_time=$(date +%s%N)
        local elapsed=$(( (end_time - start_time) / 1000000 ))
        log "${GREEN}[OK]${NC}   TCP  - $name: $host:$port 可达 (耗时: ${elapsed}ms)"
        return 0
    else
        log "${RED}[FAIL]${NC} TCP  - $name: $host:$port 不可达"
        return 1
    fi
}

check_dns() {
    local name="$1"
    local domain="$2"
    
    local ip
    ip=$(dig +short "$domain" 2>/dev/null | head -1)
    
    if [ -n "$ip" ]; then
        log "${GREEN}[OK]${NC}   DNS  - $name: $domain → $ip"
        return 0
    else
        log "${RED}[FAIL]${NC} DNS  - $name: $domain 解析失败"
        return 1
    fi
}

check_curl_timing() {
    local name="$1"
    local url="$2"
    local threshold="${3:-1.0}"  # TTFB 阈值 (秒)
    
    local timing
    timing=$(curl -s -o /dev/null -w '%{time_starttransfer}' --max-time 10 "$url" 2>/dev/null)
    
    if [ -z "$timing" ]; then
        log "${RED}[FAIL]${NC} TIME - $name: 无法获取时序数据"
        return 1
    fi
    
    # 使用 awk 比较浮点数
    local is_slow
    is_slow=$(awk "BEGIN {print ($timing > $threshold) ? 1 : 0}")
    
    if [ "$is_slow" -eq 1 ]; then
        log "${YELLOW}[SLOW]${NC} TIME - $name: TTFB=${timing}s (阈值: ${threshold}s)"
        return 1
    else
        log "${GREEN}[OK]${NC}   TIME - $name: TTFB=${timing}s (阈值: ${threshold}s)"
        return 0
    fi
}

# ============================================
# 主检查逻辑
# ============================================

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║            SRE 服务健康检查                        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
log "开始健康检查..."
echo ""

TOTAL=0
PASSED=0
FAILED=0

# 定义检查项 (名称|类型|参数1|参数2|参数3|参数4)
CHECKS=(
    # HTTP 检查
    "Nginx 首页|HTTP|https://www.example.com|200|5"
    "API 健康端点|HTTP|https://api.example.com/health|200|10"
    "API 性能|TIME|https://api.example.com/health|0.5"
    
    # TCP 检查
    "MySQL 数据库|TCP|db-server.example.com|3306|5"
    "Redis 缓存|TCP|redis-server.example.com|6379|3"
    "消息队列|TCP|mq-server.example.com|5672|3"
    
    # DNS 检查
    "主域名 DNS|DNS|www.example.com"
    "API 域名 DNS|DNS|api.example.com"
)

for check_str in "${CHECKS[@]}"; do
    IFS='|' read -r name type param1 param2 param3 param4 <<< "$check_str"
    TOTAL=$((TOTAL + 1))
    
    case "$type" in
        HTTP)
            check_http "$name" "$param1" "$param2" "$param3" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
            ;;
        TCP)
            check_tcp "$name" "$param1" "$param2" "$param3" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
            ;;
        DNS)
            check_dns "$name" "$param1" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
            ;;
        TIME)
            check_curl_timing "$name" "$param1" "$param2" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
            ;;
    esac
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "检查完成: 总计=$TOTAL 通过=$PASSED 失败=$FAILED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAILED" -gt 0 ]; then
    log "${RED}⚠️  有 $FAILED 项检查未通过，请及时处理！${NC}"
    exit 1
else
    log "${GREEN}✅ 所有检查项均通过！${NC}"
    exit 0
fi
```

**使用方法：**

```bash
chmod +x health_check.sh
./health_check.sh
```

### 练习 2：用 curl --resolve 强制解析测试

```bash
#!/bin/bash
# curl_resolve_test.sh - 使用 curl --resolve 强制解析测试
# 用于在不修改 DNS 的情况下测试新服务器或新配置

# 场景: 你的域名 www.example.com 指向 1.2.3.4
#       你新部署了一台服务器 5.6.7.8
#       你想在切换 DNS 之前测试新服务器

NEW_IP="5.6.7.8"
DOMAIN="www.example.com"
PORT=443

echo ">>> 使用 curl --resolve 强制解析 $DOMAIN 到 $NEW_IP"
echo ""

# 正常访问 (使用真实 DNS)
echo "[1] 正常 DNS 解析:"
curl -s -o /dev/null -w '  IP: %{remote_ip}\n  TTFB: %{time_starttransfer}s\n  HTTP: %{http_code}\n' "https://$DOMAIN"

echo ""

# 强制解析到新 IP
echo "[2] 强制解析到 $NEW_IP:"
curl -s -o /dev/null -w '  IP: %{remote_ip}\n  TTFB: %{time_starttransfer}s\n  HTTP: %{http_code}\n' \
    --resolve "$DOMAIN:$PORT:$NEW_IP" \
    "https://$DOMAIN"

echo ""

# 批量测试多个端点
echo "[3] 批量测试多个端点:"
ENDPOINTS=(
    "/"
    "/health"
    "/api/v1/status"
    "/favicon.ico"
)

for endpoint in "${ENDPOINTS[@]}"; do
    STATUS=$(curl -s -o /dev/null -w '%{http_code}' \
        --resolve "$DOMAIN:$PORT:$NEW_IP" \
        "https://$DOMAIN$endpoint")
    printf "  %-25s HTTP %s\n" "$DOMAIN$endpoint" "$STATUS"
done
```

### 练习 3：TCP 端口批量扫描脚本

```bash
#!/bin/bash
# port_scanner.sh - 快速 TCP 端口扫描
# 用法: ./port_scanner.sh <目标主机> [端口范围]

HOST="${1:?用法: $0 <目标主机> [起始端口] [结束端口]}"
START_PORT="${2:-1}"
END_PORT="${3:-1024}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TCP 端口扫描: $HOST ($START_PORT-$END_PORT)"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

OPEN_PORTS=()

for port in $(seq "$START_PORT" "$END_PORT"); do
    if nc -z -w 1 "$HOST" "$port" 2>/dev/null; then
        echo "  ✅ 端口 $port: 开放"
        OPEN_PORTS+=("$port")
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  扫描完成，开放端口: ${#OPEN_PORTS[@]}"
if [ ${#OPEN_PORTS[@]} -gt 0 ]; then
    echo "  开放端口列表: ${OPEN_PORTS[*]}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 📚 最新优质资源

### 官方文档
- [curl 官方文档](https://curl.se/docs/) - 完整的 curl 使用手册和教程
- [curl 手册页](https://curl.se/docs/manpage.html) - 在线 man page
- [ncat 官方文档](https://nmap.org/ncat/) - Nmap 团队的 nc 实现
- [wget 官方文档](https://www.gnu.org/software/wget/manual/) - GNU wget 手册
- [HTTP 状态码 RFC 7231](https://datatracker.ietf.org/doc/html/rfc7231#section-6) - HTTP 状态码规范

### 教程与文章
- [curl 高级用法大全](https://everything.curl.dev/) - curl 作者编写的终极指南
- [The Art of Command Line - curl 部分](https://github.com/jlevy/the-art-of-command-line) - 命令行艺术
- [Linux nc 命令详解](https://www.geeksforgeeks.org/nc-command-in-linux-with-examples/) - nc 详细教程
- [HTTP 调试技巧](https://httptoolkit.com/blog/http-debugging-guide/) - HTTP 调试指南

### 工具
- [httpie](https://httpie.io/) - 更友好的 HTTP 客户端 (curl 替代)
- [httpstat](https://github.com/reorx/httpstat) - curl 时间分解的可视化工具
- [curlconverter](https://curlconverter.com/) - curl 命令转 Python/Go/Node.js 代码
- [postman](https://www.postman.com/) - API 测试工具
- [insomnia](https://insomnia.rest/) - 开源 API 客户端
- [websocat](https://github.com/vi/websocat) - WebSocket 版的 nc

### SRE 相关
- [Google SRE - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/) - SRE 监控章节
- [Health Check Best Practices](https://aws.amazon.com/blogs/architecture/overview-of-health-checks-in-aws/) - AWS 健康检查最佳实践
- [Load Testing with curl](https://www.cloudflare.com/learning/performance/load-testing/) - Cloudflare 负载测试指南
- [API Monitoring Guide](https://docs.newrelic.com/docs/apis/intro-apis/introduction-api-monitoring/) - New Relic API 监控指南

---

## 📝 笔记

### 今日总结

1. **nc (netcat)** 是 SRE 排查网络问题最常用的工具之一，可以用于端口测试、文件传输、简易服务搭建、带宽测试等场景。关键是理解 **从正确的位置测试** — 必须在客户端位置进行端口连通性测试。

2. **curl 时间分解** 是性能分析的核心技能。通过 `-w` 参数可以精确测量 DNS、TCP、TLS、TTFB 等各阶段的耗时，帮助快速定位性能瓶颈。

3. **bind-address 问题** 是 SRE 经常遇到的经典问题：网络通但服务连不上。排查要点：
   - 永远从客户端角度测试
   - 检查服务的监听地址 (`netstat`/`ss`)
   - 理解 `127.0.0.1` vs `0.0.0.0` vs 具体 IP 的区别

4. **curl --resolve** 是测试新服务器/新配置的利器，无需修改 DNS 或 `/etc/hosts` 即可强制指定解析结果。

### 问题记录

- [ ] httpstat 工具的深入使用 (curl 时间分解可视化)
- [ ] httpie 与 curl 的对比，何时使用哪个
- [ ] 如何用 curl 进行简单的负载测试

### 延伸思考

- 如何设计一个分布式的健康检查系统？→ 多地域探测节点 + 集中式告警
- 如何用 eBPF 监控网络连接建立过程？→ bpftrace + kprobe
- 服务网格 (Istio) 如何影响健康检查？→ sidecar 代理拦截流量

---

## ✅ 完成检查

- [x] 掌握了 nc 的端口测试、文件传输、简易服务等用法
- [x] 深入理解 curl 时间分解：-w 格式化输出各阶段耗时
- [x] 掌握了 wget 的高级用法
- [x] 完成了 SRE 实战案例：bind-address 问题排查
- [x] 编写了健康检查脚本，支持 HTTP/TCP/DNS/TIME 多种检查
- [x] 完成了扩展：curl --resolve 强制解析测试
- [x] 完成了端口批量扫描脚本

### 技能评估

| 技能 | 掌握程度 | 验证方式 |
|------|---------|---------|
| nc 端口测试 | ⭐⭐⭐⭐⭐ | 能快速定位端口问题 |
| curl 时间分解 | ⭐⭐⭐⭐⭐ | 能分析各阶段性能瓶颈 |
| curl 高级用法 | ⭐⭐⭐⭐ | 能完成各种 HTTP 操作 |
| wget 高级用法 | ⭐⭐⭐⭐ | 能完成复杂下载任务 |
| 健康检查脚本 | ⭐⭐⭐⭐ | 能编写多类型检查脚本 |
| bind-address 排查 | ⭐⭐⭐⭐⭐ | 能快速定位监听问题 |

### 三日复习检查

| Day | 主题 | 掌握程度 |
|-----|------|---------|
| Day 35 | 从 URL 到页面的完整过程 | ⭐⭐⭐⭐ |
| Day 36 | ping/traceroute/mtr/dig | ⭐⭐⭐⭐ |
| Day 37 | nc/curl/wget 进阶 | ⭐⭐⭐⭐ |

---

> 📌 **下一阶段预告**：网络层工具掌握完成，下一步将进入系统层监控 — Linux 性能分析、进程管理、内存诊断、I/O 分析等核心 SRE 技能。
