# Day 25: 实战项目 — 日志监控告警脚本

> 📅 日期：2026-04-25
> 📖 学习主题：实战项目：日志监控告警脚本
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 25 的学习后，你应该掌握：
- 理解 Linux 日志体系结构（rsyslog、journalctl、应用日志）
- 掌握 grep/awk/sed 在日志分析中的高级组合用法
- 能够编写实时日志监控脚本，检测异常模式并触发告警
- 理解日志轮转（logrotate）与监控脚本的协作关系
- 了解从脚本告警到现代日志管理（ELK/Loki）的演进路径

---

## 📖 底层原理详解

### 1. Linux 日志体系架构

```
应用层 → 日志输出
    ↓
syslog 协议 (RFC 5424)
    ↓
┌─────────────────────────────────────┐
│ rsyslog / syslog-ng                 │
│  - 接收、过滤、路由、存储            │
│  - 规则: /etc/rsyslog.conf          │
│  - 目录: /etc/rsyslog.d/*.conf      │
└─────────────────────────────────────┘
    ↓
┌─────────────────┐    ┌──────────────────┐
│ /var/log/syslog │    │ /var/log/journal │
│ (文本日志)       │    │ (systemd journal) │
└─────────────────┘    └──────────────────┘
```

#### 1.1 关键日志文件速查

| 日志文件 | 内容 | 重要级别 |
|----------|------|----------|
| `/var/log/syslog` | 系统综合日志 | ⭐⭐⭐ |
| `/var/log/auth.log` | 认证/授权/登录 | ⭐⭐⭐⭐⭐ |
| `/var/log/kern.log` | 内核消息 | ⭐⭐⭐⭐ |
| `/var/log/dmesg` | 启动时内核消息 | ⭐⭐⭐ |
| `/var/log/nginx/access.log` | Nginx 访问日志 | ⭐⭐⭐⭐ |
| `/var/log/nginx/error.log` | Nginx 错误日志 | ⭐⭐⭐⭐⭐ |
| `/var/log/mysql/error.log` | MySQL 错误日志 | ⭐⭐⭐⭐ |
| `/var/log/cron.log` | 定时任务日志 | ⭐⭐⭐ |
| `/var/log/apt/` | 包管理日志 | ⭐⭐ |

#### 1.2 日志格式

**Nginx Combined Log Format**（最常见）：
```
192.168.1.50 - frank [25/Apr/2026:14:30:25 +0800] "GET /api/users HTTP/1.1" 200 1234 "https://example.com" "Mozilla/5.0"
```

字段分解：
- `$remote_addr` — 客户端 IP
- `$remote_user` — 认证用户（通常 `-`）
- `$time_local` — 时间戳
- `$request` — 请求行
- `$status` — HTTP 状态码
- `$body_bytes_sent` — 响应大小
- `$http_referer` — 来源页
- `$http_user_agent` — 浏览器 UA

**syslog 标准格式**：
```
Apr 25 14:30:25 hostname sshd[12345]: Failed password for root from 10.0.0.1 port 22 ssh2
```

### 2. 日志分析核心命令

#### 2.1 grep 高级用法

```bash
# 基础搜索
grep "ERROR" /var/log/syslog

# 多模式搜索（任一匹配）
grep -E "ERROR|CRITICAL|FATAL" /var/log/syslog

# 多模式搜索（全部匹配）
grep "ERROR" /var/log/syslog | grep "database"

# 反向匹配（排除）
grep -v "DEBUG" /var/log/app.log

# 上下文（前后行）
grep -C 3 "OutOfMemory" /var/log/app.log

# 只输出匹配的文件名
grep -rl "ERROR" /var/log/

# 计数
grep -c "Failed password" /var/log/auth.log

# 高亮显示（默认启用）
grep --color=auto "ERROR" /var/log/syslog
```

#### 2.2 awk 在日志分析中的威力

```bash
# Nginx 日志：统计各 HTTP 状态码数量
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# Nginx 日志：找出访问最多的 IP
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# Nginx 日志：计算平均响应大小
awk '{sum += $10; count++} END {print sum/count " bytes"}' access.log

# auth.log：暴力破解检测
awk '/Failed password/ {print $(NF-3)}' /var/log/auth.log | \
    sort | uniq -c | sort -rn | \
    awk '$1 > 10 {print "IP: "$2", 失败: "$1" 次"}'

# syslog：按小时统计错误数
awk '/ERROR/ {split($3, t, ":"); print t[1]":00"}' /var/log/syslog | \
    sort | uniq -c
```

#### 2.3 sed 在日志处理中的应用

```bash
# 删除注释行和空行
sed '/^#/d; /^$/d' /etc/nginx/nginx.conf

# 提取时间戳
sed -n 's/.*\[\(.*\)\].*/\1/p' /var/log/nginx/access.log

# 将 IP 替换为匿名化
sed -E 's/([0-9]{1,3}\.){3}[0-9]{1,3}/x.x.x.x/g' access.log

# 提取特定时间段（假设日志已按时间排序）
sed -n '/Apr 25 14:/,/Apr 25 15:/p' /var/log/syslog
```

---

## 💻 实战项目：日志监控告警脚本

### 项目架构

```
log_monitor.sh
├── 实时监控模式（tail -f 管道）
├── 定时扫描模式（cron 驱动）
└── 告警输出（终端/邮件/webhook）
```

### 完整实现

```bash
#!/bin/bash
# log_monitor.sh — 生产级日志监控告警脚本
set -euo pipefail

# ===== 配置区 =====
CONFIG_FILE="${LOG_MONITOR_CONFIG:-/etc/log_monitor.conf}"

# 默认配置
LOG_FILES=(
    "/var/log/syslog"
    "/var/log/auth.log"
    "/var/log/nginx/error.log"
)

# 告警规则（模式:严重级别:描述）
declare -a ALERT_PATTERNS=(
    "ERROR:warning:通用错误"
    "CRITICAL:critical:严重错误"
    "Failed password:warning:SSH 认证失败"
    "Accepted password:info:SSH 登录成功"
    "segfault:critical:段错误"
    "Out of memory:critical:OOM 事件"
    "TCP: Possible SYN flooding:critical:SYN Flood 攻击"
    "kernel:.*BUG:critical:内核 BUG"
)

# 告警频率限制（同一规则 N 秒内只告警一次）
ALERT_COOLDOWN=300
ALERT_STATE_DIR="/tmp/log_monitor_state"
WEBHOOK_URL="${WEBHOOK_URL:-}"
EMAIL_TO="${ALERT_EMAIL:-}"

# 颜色输出
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# ===== 函数区 =====

init() {
    mkdir -p "$ALERT_STATE_DIR"

    # 检查日志文件是否存在
    for log_file in "${LOG_FILES[@]}"; do
        if [[ ! -f "$log_file" ]]; then
            echo -e "${YELLOW}⚠️  日志文件不存在: $log_file${NC}"
        elif [[ ! -r "$log_file" ]]; then
            echo -e "${RED}❌ 无权限读取: $log_file${NC}"
            exit 1
        fi
    done
}

# 检查告警频率限制
should_alert() {
    local rule_hash=$1
    local state_file="$ALERT_STATE_DIR/$rule_hash"
    local now=$(date +%s)

    if [[ -f "$state_file" ]]; then
        local last_alert=$(cat "$state_file")
        local diff=$((now - last_alert))
        if [[ $diff -lt $ALERT_COOLDOWN ]]; then
            return 1  # 不应告警
        fi
    fi

    echo "$now" > "$state_file"
    return 0
}

# 发送告警
send_alert() {
    local level=$1
    local message=$2
    local log_file=$3
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # 终端输出
    case "$level" in
        critical) echo -e "${RED}🚨 [$level] $message${NC}" ;;
        warning)  echo -e "${YELLOW}⚠️  [$level] $message${NC}" ;;
        info)     echo -e "${GREEN}ℹ️  [$level] $message${NC}" ;;
    esac

    # Webhook 告警（如钉钉/企业微信/Slack）
    if [[ -n "$WEBHOOK_URL" ]]; then
        curl -sS -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$(cat <<EOF
{
    "text": "[$level] $message\n日志: $log_file\n时间: $timestamp",
    "level": "$level"
}
EOF
)" &>/dev/null || true
    fi

    # 邮件告警
    if [[ -n "$EMAIL_TO" && "$level" != "info" ]]; then
        echo "[$level] $message (来自 $log_file)" | \
            mail -s "🚨 日志告警: $message" "$EMAIL_TO" 2>/dev/null || true
    fi

    # 写入告警日志
    echo "[$timestamp] [$level] $message | 来源: $log_file" >> /var/log/log_monitor_alerts.log
}

# 处理单行日志
process_line() {
    local line="$1"
    local log_file="$2"

    for rule in "${ALERT_PATTERNS[@]}"; do
        IFS=':' read -r pattern level description <<< "$rule"

        if echo "$line" | grep -qiE "$pattern"; then
            local rule_hash=$(echo "$rule" | md5sum | cut -d' ' -f1)

            if should_alert "$rule_hash"; then
                # 提取关键信息（如 IP）
                local ip=$(echo "$line" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
                local ip_info=""
                [[ -n "$ip" ]] && ip_info=" (来源IP: $ip)"

                send_alert "$level" "$description${ip_info}" "$log_file"
            fi
        fi
    done
}

# 实时监控模式
monitor_realtime() {
    echo "🔍 开始实时监控日志..."
    echo "监控文件: ${LOG_FILES[*]}"
    echo "按 Ctrl+C 停止"
    echo "---"

    # 使用 tail -f 监控多个文件
    tail -f "${LOG_FILES[@]}" 2>/dev/null | while IFS= read -r line; do
        # tail -f 多文件时会输出 ==> 文件名 <== 分隔行
        if [[ "$line" == "==>"*"<=="* ]]; then
            current_log=$(echo "$line" | sed 's/==> \(.*\) <==/\1/')
            continue
        fi
        [[ -z "$line" ]] && continue

        process_line "$line" "${current_log:-unknown}"
    done
}

# 定时扫描模式（适合 cron）
scan_logs() {
    local since_minutes=${1:-5}
    echo "📋 扫描过去 ${since_minutes} 分钟的日志..."

    for log_file in "${LOG_FILES[@]}"; do
        [[ ! -f "$log_file" ]] && continue

        local cutoff_time=$(date -d "${since_minutes} minutes ago" '+%b %_d %H:%M' 2>/dev/null || \
                            date -v-${since_minutes}M '+%b %_d %H:%M' 2>/dev/null || echo "")

        if [[ -n "$cutoff_time" ]]; then
            # 读取从指定时间开始的日志行
            sed -n "/$cutoff_time/,\$p" "$log_file" 2>/dev/null | \
            while IFS= read -r line; do
                process_line "$line" "$log_file"
            done
        fi
    done

    echo "✅ 扫描完成"
}

# 暴力破解专项检测
detect_brute_force() {
    echo "🔒 SSH 暴力破解检测..."
    local threshold=5

    awk '/Failed password/ {print $(NF-3)}' /var/log/auth.log 2>/dev/null | \
        sort | uniq -c | sort -rn | \
    while read -r count ip; do
        if [[ $count -gt $threshold ]]; then
            local rule_hash="bruteforce_$(echo $ip | md5sum | cut -d' ' -f1)"
            if should_alert "$rule_hash"; then
                send_alert "critical" "SSH 暴力破解: IP $ip 失败 $count 次" "/var/log/auth.log"
            fi
        fi
    done
}

# ===== 主入口 =====

usage() {
    echo "用法: $0 {monitor|scan|bruteforce}"
    echo ""
    echo "  monitor          实时监控模式（tail -f）"
    echo "  scan [分钟]       扫描模式，默认过去 5 分钟"
    echo "  bruteforce       SSH 暴力破解检测"
    echo ""
    echo "环境变量:"
    echo "  WEBHOOK_URL      Webhook 告警地址"
    echo "  ALERT_EMAIL      邮件告警地址"
    echo "  LOG_MONITOR_CONFIG  配置文件路径"
}

case "${1:-}" in
    monitor)
        init
        monitor_realtime
        ;;
    scan)
        init
        scan_logs "${2:-5}"
        ;;
    bruteforce)
        init
        detect_brute_force
        ;;
    *)
        usage
        exit 1
        ;;
esac
```

### 部署到 cron

```bash
# 每 5 分钟扫描一次日志
*/5 * * * * /opt/scripts/log_monitor.sh scan 5 >> /var/log/log_monitor_cron.log 2>&1

# 每 30 分钟检测暴力破解
*/30 * * * * /opt/scripts/log_monitor.sh bruteforce >> /var/log/log_monitor_cron.log 2>&1
```

---

## 🧪 练习题

### 练习 1：编写 Nginx 5xx 错误率监控
```bash
# 编写脚本：每 5 分钟检查 Nginx 5xx 错误率
# 如果过去 5 分钟内 5xx 占比 > 5%，发送告警
```

<details>
<summary>答案</summary>

```bash
#!/bin/bash
LOG="/var/log/nginx/access.log"
THRESHOLD=5

# 获取最近 5 分钟的日志（简化：取最后 1000 行）
total=$(tail -1000 "$LOG" | wc -l)
errors=$(tail -1000 "$LOG" | awk '$9 >= 500' | wc -l)

if [[ $total -gt 0 ]]; then
    rate=$((errors * 100 / total))
    if [[ $rate -gt $THRESHOLD ]]; then
        echo "🚨 Nginx 5xx 错误率: ${rate}% ($errors/$total) 超过阈值 ${THRESHOLD}%"
        # 触发告警...
    fi
fi
```
</details>

### 练习 2：日志轮转兼容性

```bash
# 日志轮转后，tail -f 会丢失新日志。如何修复？
```

<details>
<summary>答案</summary>

使用 `tail -F`（大写 F）代替 `tail -f`：
```bash
# -f: 跟踪文件描述符（轮转后失效）
# -F: 跟踪文件名（轮转后自动重新打开）
tail -F /var/log/syslog
```
或在 logrotate 配置中添加 `copytruncate` 而非 `create`。
</details>

---

## 📚 扩展阅读

- [rsyslog 官方文档](https://www.rsyslog.com/doc/)
- [systemd journal 文档](https://www.freedesktop.org/software/systemd/man/journald.conf.html)
- 《日志管理最佳实践》— Google SRE Book
- ELK Stack (Elasticsearch + Logstash + Kibana)
- Grafana Loki — 轻量级日志聚合系统

---

*由 SRE 学习计划自动生成 | 2026-04-25*
*Generated by Hermes Agent with review*
