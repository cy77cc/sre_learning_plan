# Day 25: 实战项目 — 日志监控告警脚本

> 📅 日期：2026-04-25
> 📖 学习主题：实战项目 — 日志监控告警脚本
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 24 服务器初始化脚本、Day 21 字符串处理与正则

## 🎯 学习目标

完成 Day 25 的学习后，你应该掌握：
- 能够设计和实现生产级日志监控告警脚本
- 掌握实时日志监控（tail -f + 逐行处理）的实现原理
- 理解告警规则引擎设计（关键字匹配、正则匹配、频率统计）
- 实现告警去重机制，避免告警风暴
- 掌握多日志文件同时监控的技术方案
- 了解日志轮转感知和性能优化策略

---

## 📖 核心知识点

### 1. 日志监控告警系统架构

#### 1.1 为什么需要日志监控？

在 SRE 的日常工作中，日志是最基础也是最重要的可观测性数据之一。当系统出现问题时，日志往往是第一个提供线索的数据源。

**没有日志监控的问题**：
- 故障发生后才发现问题，被动响应
- 需要人工登录服务器查看日志，效率低下
- 多台服务器的日志无法集中分析
- 错误模式难以统计和追踪

**日志监控的价值**：
- 实时发现问题，主动告警
- 自动化分析，减少人工干预
- 趋势分析，提前发现潜在风险
- 故障快速定位，缩短 MTTR（平均修复时间）

#### 1.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    日志监控告警系统                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ /var/log/    │  │ /var/log/    │  │ /var/log/    │          │
│  │ syslog       │  │ auth.log     │  │ nginx/error  │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│                           v                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              实时日志采集层                                │  │
│  │  tail -F (跟踪文件名，支持日志轮转)                       │  │
│  │  多文件 select 模型                                       │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│                             v                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              告警规则引擎                                  │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │ 关键字匹配  │ │ 正则匹配    │ │ 频率统计    │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│                             v                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              告警处理层                                    │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐            │  │
│  │  │ 告警去重    │ │ 频率限制    │ │ 告警升级    │            │  │
│  │  └────────────┘ └────────────┘ └────────────┘            │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                             │                                   │
│                             v                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              通知渠道                                      │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐            │  │
│  │  │ 终端    │ │ Webhook│ │ 邮件    │ │ 日志    │            │  │
│  │  └────────┘ └────────┘ └────────┘ └────────┘            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### 1.3 关键设计决策

| 决策点 | 选项 | 推荐 |
|--------|------|------|
| 日志采集方式 | tail -f / inotify / read 循环 | tail -F（简单可靠） |
| 模式匹配 | grep / awk / 正则 | 正则（灵活强大） |
| 并发模型 | 多进程 / select / 多线程 | Bash select / 多进程 |
| 告警去重 | 文件锁 / 内存 / Redis | 文件（简单场景） |
| 通知方式 | 终端 / Webhook / 邮件 | 多渠道组合 |
| 运行方式 | 前台 / nohup / systemd | systemd service |

---

### 2. 实时日志监控原理

#### 2.1 tail -f 的工作原理

`tail -f` 是最常用的实时日志监控工具，它通过 **inotify** 机制监控文件变化。

```
tail -f 的内部机制:
┌─────────────┐
│ tail 进程    │
│             │
│ 1. 打开文件  │
│ 2. seek 到末尾│
│ 3. inotify   │──── 监控文件的 IN_MODIFY 事件
│    wait      │
│ 4. 事件触发  │──── 读取新增内容
│ 5. 输出到    │──── stdout
│    stdout    │
│ 6. 回到步骤 3│
└─────────────┘
```

**tail -f vs tail -F**：
```bash
# -f: 跟踪文件描述符（文件被轮转后失效）
tail -f /var/log/syslog

# -F: 跟踪文件名（文件被轮转后自动重新打开）
# -F = --follow=name --retry
tail -F /var/log/syslog
```

**日志轮转场景**：
```
tail -f 的问题:
1. logrotate 将 syslog 轮转为 syslog.1
2. 创建新的空 syslog 文件
3. tail -f 仍然跟踪旧的 syslog.1（通过文件描述符）
4. 新日志写入新的 syslog，tail -f 看不到

tail -F 的解决方案:
1. logrotate 将 syslog 轮转为 syslog.1
2. tail -F 检测到文件名对应的 inode 变化
3. 自动重新打开新的 syslog 文件
4. 继续监控新日志
```

#### 2.2 日志轮转感知

```bash
#!/bin/bash
# 日志轮转感知的监控脚本

monitor_with_rotation() {
    local log_file=$1

    while true; do
        # 检查文件是否存在
        if [[ ! -f "$log_file" ]]; then
            sleep 1
            continue
        fi

        # 使用 tail -F 监控（自动处理轮转）
        tail -F "$log_file" 2>/dev/null | while IFS= read -r line; do
            process_line "$line" "$log_file"
        done

        # tail -F 退出时（文件被删除且重试超时），等待后重新开始
        sleep 1
    done
}
```

#### 2.3 多文件监控方案

**方案 1：多进程（简单但资源消耗大）**：
```bash
#!/bin/bash
# 每个日志文件启动一个 tail 进程
monitor_multiple() {
    local pids=()
    local files=("/var/log/syslog" "/var/log/auth.log" "/var/log/nginx/error.log")

    for file in "${files[@]}"; do
        tail -F "$file" 2>/dev/null | while IFS= read -r line; do
            process_line "$line" "$file"
        done &
        pids+=($!)
    done

    # 等待所有进程
    trap 'kill "${pids[@]}" 2>/dev/null; exit' INT TERM
    wait
}
```

**方案 2：tail -F 多文件（推荐）**：
```bash
#!/bin/bash
# tail -F 原生支持多文件，输出时会显示文件名切换
monitor_multiple_single() {
    local files=("/var/log/syslog" "/var/log/auth.log" "/var/log/nginx/error.log")
    local current_file=""

    tail -F "${files[@]}" 2>/dev/null | while IFS= read -r line; do
        # tail -F 多文件输出格式: ==> filename <==
        if [[ "$line" =~ ^==>\ (.*)\ \<==$ ]]; then
            current_file="${BASH_REMATCH[1]}"
            continue
        fi
        [[ -z "$line" ]] && continue
        process_line "$line" "$current_file"
    done
}
```

**方案 3：select 模型（高级，Bash 4+）**：
```bash
#!/bin/bash
# 使用文件描述符和 select 实现多路复用
monitor_select() {
    local files=("/var/log/syslog" "/var/log/auth.log")
    local fds=()
    local fd_files=()

    # 为每个文件打开一个文件描述符
    for i in "${!files[@]}"; do
        local fd=$((63 - i))  # 使用高位 fd
        exec 3< <(tail -F "${files[$i]}" 2>/dev/null)
        fds+=($fd)
        fd_files[$fd]="${files[$i]}"
    done

    # 使用 select 监控所有 fd
    while true; do
        # Bash 不原生支持 select for fd，使用 read -t 替代
        for fd in "${fds[@]}"; do
            if read -t 0.1 -r line <&$fd; then
                [[ -n "$line" ]] && process_line "$line" "${fd_files[$fd]}"
            fi
        done
    done
}
```

---

### 3. 告警规则引擎

#### 3.1 规则设计

告警规则是日志监控系统的核心，好的规则设计能够准确发现问题同时避免误报。

**规则类型**：

| 类型 | 说明 | 示例 |
|------|------|------|
| **关键字匹配** | 简单字符串匹配 | 包含 "ERROR" |
| **正则匹配** | 模式匹配 | 匹配 "5\d{2}" (5xx 错误) |
| **频率告警** | 同一错误 N 分钟内出现 M 次 | ERROR 5分钟内>10次 |
| **趋势告警** | 错误率上升 | 5xx 比率从 1% 上升到 5% |
| **复合规则** | 多条件组合 | ERROR + 特定服务名 |

#### 3.2 规则引擎实现

```bash
#!/bin/bash
# ===== 告警规则引擎 =====

# 规则定义格式: ID|模式|级别|描述|类型
# 类型: keyword(关键字), regex(正则), frequency(频率)
declare -a ALERT_RULES=(
    # 关键字规则
    "RULE001|CRITICAL|critical|严重错误|keyword"
    "RULE002|FATAL|critical|致命错误|keyword"
    "RULE003|segfault|critical|段错误|keyword"
    "RULE004|Out of memory|critical|OOM 事件|keyword"
    "RULE005|OOM|critical|OOM Killer 触发|keyword"
    "RULE006|kernel panic|critical|内核恐慌|keyword"

    # 认证安全规则
    "RULE010|Failed password|warning|SSH 登录失败|keyword"
    "RULE011|Failed sudo|warning|sudo 认证失败|keyword"
    "RULE012|Accepted password|info|SSH 密码登录成功|keyword"
    "RULE013|Invalid user|warning|无效用户登录尝试|keyword"

    # Nginx 规则
    "RULE020| 5[0-9]{2} |critical|HTTP 5xx 错误|regex"
    "RULE021| 429 |warning|请求被限流|keyword"
    "RULE022|upstream timed out|critical|上游超时|keyword"

    # 系统规则
    "RULE030|SYN flooding|critical|SYN Flood 攻击|keyword"
    "RULE031|TCP: Possible SYN flooding|critical|SYN Flood 疑似|keyword"
    "RULE032|Disk quota exceeded|critical|磁盘配额超限|keyword"
    "RULE033|No space left on device|critical|磁盘空间耗尽|keyword"
    "RULE034|filesystem read-only|critical|文件系统只读|keyword"
)

# 频率规则定义: ID|模式|级别|描述|窗口秒数|阈值
declare -a FREQUENCY_RULES=(
    "FREQ001|Failed password|warning|SSH 暴力破解|300|5"
    "FREQ002|ERROR|warning|错误频率过高|300|20"
    "FREQ003|connection refused|warning|连接拒绝过多|600|10"
)

# 匹配函数
match_rule() {
    local line="$1"
    local pattern="$2"
    local match_type="$3"

    case "$match_type" in
        keyword)
            echo "$line" | grep -qi "$pattern"
            ;;
        regex)
            echo "$line" | grep -qE "$pattern"
            ;;
        *)
            return 1
            ;;
    esac
}

# 规则引擎主函数
evaluate_rules() {
    local line="$1"
    local log_file="$2"

    # 检查每条关键字/正则规则
    for rule in "${ALERT_RULES[@]}"; do
        IFS='|' read -r rule_id pattern level description match_type <<< "$rule"

        if match_rule "$line" "$pattern" "$match_type"; then
            # 提取上下文信息
            local context
            context=$(extract_context "$line")

            # 触发告警（带去重检查）
            trigger_alert "$rule_id" "$level" "$description" "$log_file" "$context"
            return 0  # 匹配到第一条规则就返回
        fi
    done
}

# 提取上下文信息
extract_context() {
    local line="$1"
    local context=""

    # 提取 IP 地址
    local ip
    ip=$(echo "$line" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1)
    [[ -n "$ip" ]] && context+="IP: $ip "

    # 提取进程名
    local proc
    proc=$(echo "$line" | grep -oP '\w+(?=\[\d+\]:)' | head -1)
    [[ -n "$proc" ]] && context+="进程: $proc "

    # 提取时间戳
    local ts
    ts=$(echo "$line" | grep -oP '^\w{3}\s+\d+\s+\d+:\d+:\d+' | head -1)
    [[ -n "$ts" ]] && context+="时间: $ts"

    echo "$context"
}
```

#### 3.3 频率告警实现

```bash
#!/bin/bash
# ===== 频率告警统计 =====

# 使用关联数组存储频率数据
declare -A FREQUENCY_COUNT    # key: rule_id|时间窗口, value: 计数
declare -A FREQUENCY_FIRST    # key: rule_id|时间窗口, value: 首次时间

check_frequency() {
    local rule_id=$1
    local window=$2
    local threshold=$3
    local current_time
    current_time=$(date +%s)

    local key="${rule_id}"

    # 初始化
    if [[ -z "${FREQUENCY_COUNT[$key]:-}" ]]; then
        FREQUENCY_COUNT[$key]=0
        FREQUENCY_FIRST[$key]=$current_time
    fi

    # 检查是否在同一个时间窗口内
    local elapsed=$((current_time - FREQUENCY_FIRST[$key]))

    if [[ $elapsed -gt $window ]]; then
        # 新的时间窗口，重置计数
        FREQUENCY_COUNT[$key]=1
        FREQUENCY_FIRST[$key]=$current_time
        return 1  # 未达到阈值
    fi

    # 在同一窗口内，增加计数
    FREQUENCY_COUNT[$key]=$(( ${FREQUENCY_COUNT[$key]} + 1 ))

    if [[ ${FREQUENCY_COUNT[$key]} -ge $threshold ]]; then
        # 达到阈值，触发告警并重置
        FREQUENCY_COUNT[$key]=0
        FREQUENCY_FIRST[$key]=$current_time
        return 0  # 触发告警
    fi

    return 1  # 未达到阈值
}

# 频率规则评估
evaluate_frequency_rules() {
    local line="$1"
    local log_file="$2"

    for rule in "${FREQUENCY_RULES[@]}"; do
        IFS='|' read -r rule_id pattern level description window threshold <<< "$rule"

        if echo "$line" | grep -qi "$pattern"; then
            if check_frequency "$rule_id" "$window" "$threshold"; then
                trigger_alert "$rule_id" "$level" \
                    "${description} (${FREQUENCY_COUNT[$rule_id]:-?}次/${window}秒)" \
                    "$log_file" ""
            fi
        fi
    done
}
```

---

### 4. 告警去重与限流

#### 4.1 告警风暴问题

告警风暴是指短时间内产生大量重复告警，导致：
- 通知渠道被淹没，重要告警被忽略
- 接收人产生"告警疲劳"，不再关注告警
- 系统资源被大量告警消耗

#### 4.2 去重机制实现

```bash
#!/bin/bash
# ===== 告警去重与限流 =====

ALERT_COOLDOWN=300        # 同一规则 300 秒内不重复告警
ALERT_STATE_DIR="/tmp/log_monitor_alerts"
MAX_ALERTS_PER_MINUTE=10  # 每分钟最多告警次数（全局）

mkdir -p "$ALERT_STATE_DIR"

# 全局告警计数器
declare -A GLOBAL_ALERT_COUNT
GLOBAL_ALERT_WINDOW_START=$(date +%s)

# 检查是否应该发送告警（去重 + 限流）
should_alert() {
    local rule_id=$1
    local now
    now=$(date +%s)

    # === 去重检查：同一规则 N 秒内不重复 ===
    local state_file="$ALERT_STATE_DIR/$rule_id"
    if [[ -f "$state_file" ]]; then
        local last_alert
        last_alert=$(cat "$state_file")
        local diff=$((now - last_alert))
        if [[ $diff -lt $ALERT_COOLDOWN ]]; then
            return 1  # 在冷却期内，不告警
        fi
    fi

    # === 全局限流检查 ===
    local window_elapsed=$((now - GLOBAL_ALERT_WINDOW_START))
    if [[ $window_elapsed -ge 60 ]]; then
        # 新的一分钟，重置计数
        GLOBAL_ALERT_WINDOW_START=$now
        GLOBAL_ALERT_COUNT=()
    fi

    local global_key="global"
    GLOBAL_ALERT_COUNT[$global_key]=$(( ${GLOBAL_ALERT_COUNT[$global_key]:-0} + 1 ))

    if [[ ${GLOBAL_ALERT_COUNT[$global_key]} -gt $MAX_ALERTS_PER_MINUTE ]]; then
        return 1  # 超过全局限流
    fi

    # === 通过检查，更新状态 ===
    echo "$now" > "$state_file"
    return 0
}

# 清理过期的状态文件
cleanup_alert_state() {
    local max_age=3600  # 清理 1 小时前的状态
    local now
    now=$(date +%s)

    for state_file in "$ALERT_STATE_DIR"/*; do
        [[ -f "$state_file" ]] || continue
        local file_time
        file_time=$(cat "$state_file")
        if (( now - file_time > max_age )); then
            rm -f "$state_file"
        fi
    done
}
```

#### 4.3 告警升级机制

```bash
#!/bin/bash
# ===== 告警升级 =====

# 告警升级规则：同一问题持续 N 分钟未解决，升级告警级别
declare -A ESCALATION_COUNT
ESCALATION_THRESHOLD=3  # 升级阈值

trigger_alert_with_escalation() {
    local rule_id=$1
    local level=$2
    local message=$3
    local log_file=$4
    local context=$5

    # 统计同一规则的触发次数
    ESCALATION_COUNT[$rule_id]=$(( ${ESCALATION_COUNT[$rule_id]:-0} + 1 ))

    # 告警升级
    local final_level="$level"
    if [[ ${ESCALATION_COUNT[$rule_id]} -ge $ESCALATION_THRESHOLD ]]; then
        case "$level" in
            info)    final_level="warning" ;;
            warning) final_level="critical" ;;
        esac
        message="[升级] $message (已触发 ${ESCALATION_COUNT[$rule_id]} 次)"
    fi

    # 发送告警
    send_alert "$final_level" "$message" "$log_file" "$context"
}
```

---

### 5. 通知渠道实现

#### 5.1 终端通知

```bash
# ===== 终端输出 =====
send_terminal_alert() {
    local level=$1
    local message=$2
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    local color
    local icon
    case "$level" in
        critical) color='\033[0;31m'; icon='[CRIT]' ;;
        warning)  color='\033[1;33m'; icon='[WARN]' ;;
        info)     color='\033[0;32m'; icon='[INFO]' ;;
        *)        color='\033[0m'; icon='[????]' ;;
    esac

    echo -e "${color}${icon} [${timestamp}] ${message}\033[0m"
}
```

#### 5.2 企业微信 Webhook

```bash
# ===== 企业微信 Webhook 通知 =====
send_wechat_alert() {
    local level=$1
    local message=$2
    local log_file=$3
    local webhook_url="${WECHAT_WEBHOOK_URL:-}"

    [[ -z "$webhook_url" ]] && return 0

    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local hostname
    hostname=$(hostname)

    # 构建消息体
    local json
    json=$(cat << EOF
{
    "msgtype": "markdown",
    "markdown": {
        "content": "## 日志告警通知\n\n\
> **级别**: ${level}\n\
> **主机**: ${hostname}\n\
> **时间**: ${timestamp}\n\
> **来源**: ${log_file}\n\
> **详情**: ${message}"
    }
}
EOF
    )

    # 发送请求
    curl -sS -X POST "$webhook_url" \
        -H "Content-Type: application/json" \
        -d "$json" \
        --connect-timeout 5 \
        --max-time 10 \
        2>/dev/null || true
}
```

#### 5.3 钉钉 Webhook

```bash
# ===== 钉钉 Webhook 通知 =====
send_dingtalk_alert() {
    local level=$1
    local message=$2
    local webhook_url="${DINGTALK_WEBHOOK_URL:-}"

    [[ -z "$webhook_url" ]] && return 0

    local hostname
    hostname=$(hostname)
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    local json
    json=$(cat << EOF
{
    "msgtype": "markdown",
    "markdown": {
        "title": "日志告警: ${level}",
        "text": "## 日志告警: ${level}\n\n\
- **主机**: ${hostname}\n\
- **时间**: ${timestamp}\n\
- **详情**: ${message}\n\n\
请及时处理！"
    }
}
EOF
    )

    curl -sS -X POST "$webhook_url" \
        -H "Content-Type: application/json" \
        -d "$json" \
        --connect-timeout 5 \
        --max-time 10 \
        2>/dev/null || true
}
```

#### 5.4 邮件通知

```bash
# ===== 邮件通知 =====
send_email_alert() {
    local level=$1
    local message=$2
    local log_file=$3
    local email_to="${ALERT_EMAIL:-}"

    [[ -z "$email_to" ]] && return 0

    # 只对 warning 和 critical 发送邮件
    [[ "$level" == "info" ]] && return 0

    local hostname
    hostname=$(hostname)
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    local subject="[${level^^}] 日志告警: ${message:0:50}"
    local body="告警详情:\n\n级别: ${level}\n主机: ${hostname}\n时间: ${timestamp}\n来源: ${log_file}\n详情: ${message}"

    echo -e "$body" | mail -s "$subject" "$email_to" 2>/dev/null || true
}
```

#### 5.5 统一告警分发

```bash
# ===== 统一告警入口 =====
trigger_alert() {
    local rule_id=$1
    local level=$2
    local message=$3
    local log_file=$4
    local context="${5:-}"

    # 去重检查
    if ! should_alert "$rule_id"; then
        return 0
    fi

    # 构建完整消息
    local full_message="$message"
    [[ -n "$context" ]] && full_message+=" | $context"

    # 分发到各渠道
    send_terminal_alert "$level" "$full_message"
    send_wechat_alert "$level" "$full_message" "$log_file"
    send_dingtalk_alert "$level" "$full_message"
    send_email_alert "$level" "$full_message" "$log_file"

    # 记录到告警日志
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] [$rule_id] $full_message | 来源: $log_file" \
        >> /var/log/log_monitor_alerts.log
}
```

---

### 6. 守护进程化

#### 6.1 使用 systemd 管理

```ini
# /etc/systemd/system/log-monitor.service
[Unit]
Description=Log Monitor and Alert Service
Documentation=https://internal.wiki/log-monitor
After=network-online.target syslog.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
ExecStart=/opt/scripts/log_monitor.sh monitor
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# 资源限制
MemoryMax=256M
CPUQuota=20%

# 安全加固
ProtectSystem=strict
ReadWritePaths=/var/log /tmp/log_monitor_alerts
NoNewPrivileges=true
PrivateTmp=true

# 环境变量
Environment=WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
Environment=ALERT_EMAIL=sre@company.com

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=log-monitor

[Install]
WantedBy=multi-user.target
```

```bash
# 安装和管理
sudo systemctl daemon-reload
sudo systemctl enable log-monitor
sudo systemctl start log-monitor
sudo systemctl status log-monitor

# 查看日志
journalctl -u log-monitor -f
```

#### 6.2 使用 nohup 后台运行（简单场景）

```bash
#!/bin/bash
# start_monitor.sh — 后台启动日志监控

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="/var/run/log_monitor.pid"
LOG_FILE="/var/log/log_monitor.log"

# 检查是否已运行
if [[ -f "$PID_FILE" ]]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        echo "日志监控已在运行 (PID: $old_pid)"
        exit 1
    fi
fi

# 启动
nohup "$SCRIPT_DIR/log_monitor.sh" monitor >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "日志监控已启动 (PID: $!)"
```

```bash
#!/bin/bash
# stop_monitor.sh — 停止日志监控

PID_FILE="/var/run/log_monitor.pid"

if [[ -f "$PID_FILE" ]]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        rm -f "$PID_FILE"
        echo "日志监控已停止 (PID: $pid)"
    else
        rm -f "$PID_FILE"
        echo "进程不存在，已清理 PID 文件"
    fi
else
    echo "日志监控未运行"
fi
```

---

### 7. 完整的日志监控告警脚本

以下是生产级日志监控告警脚本的完整实现：

```bash
#!/bin/bash
# =============================================================================
# log_monitor.sh — 生产级日志监控告警脚本
# 版本: 2.0.0
# 支持: 实时监控、定时扫描、暴力破解检测
# =============================================================================

set -euo pipefail

# ===== 版本与配置 =====
readonly SCRIPT_VERSION="2.0.0"
readonly SCRIPT_NAME="$(basename "$0")"

# 默认配置（可通过配置文件或环境变量覆盖）
CONFIG_FILE="${LOG_MONITOR_CONFIG:-/etc/log_monitor.conf}"

# 日志文件列表
declare -a LOG_FILES=(
    "/var/log/syslog"
    "/var/log/auth.log"
    "/var/log/nginx/error.log"
    "/var/log/kern.log"
)

# 告警规则: ID|模式|级别|描述|类型
declare -a ALERT_RULES=(
    "R001|CRITICAL|critical|严重错误|keyword"
    "R002|FATAL|critical|致命错误|keyword"
    "R003|segfault|critical|段错误|keyword"
    "R004|Out of memory|critical|OOM 事件|keyword"
    "R005|kernel panic|critical|内核恐慌|keyword"
    "R006|Failed password|warning|SSH 登录失败|keyword"
    "R007|Invalid user|warning|无效用户登录|keyword"
    "R008|Accepted password|info|SSH 密码登录|keyword"
    "R009|upstream timed out|critical|上游超时|keyword"
    "R010|Connection refused|warning|连接被拒绝|keyword"
    "R011|No space left|critical|磁盘空间耗尽|keyword"
    "R012|filesystem read-only|critical|文件系统只读|keyword"
    "R013|SYN flooding|critical|SYN Flood|keyword"
)

# 频率规则: ID|模式|级别|描述|窗口秒|阈值
declare -a FREQ_RULES=(
    "F001|Failed password|warning|SSH 暴力破解|300|5"
    "F002|ERROR|warning|错误频率过高|300|20"
    "F003|connection refused|warning|连接拒绝过多|600|10"
)

# 告警配置
ALERT_COOLDOWN=300
ALERT_STATE_DIR="/tmp/log_monitor_state"
MAX_ALERTS_PER_MINUTE=20
WEBHOOK_URL="${WEBHOOK_URL:-}"
DINGTALK_URL="${DINGTALK_URL:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"
LOG_MONITOR_LOG="/var/log/log_monitor_alerts.log"

# 颜色
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# 频率统计
declare -A FREQ_COUNT
declare -A FREQ_START

# 全局限流
declare -A GLOBAL_COUNT
GLOBAL_WINDOW_START=$(date +%s)

# ===== 加载配置文件 =====
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$CONFIG_FILE"
    fi
}

# ===== 日志函数 =====
log_msg() {
    local level=$1 msg=$2
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        INFO)  echo -e "${GREEN}[INFO]${NC}  [$ts] $msg" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC}  [$ts] $msg" ;;
        ERROR) echo -e "${RED}[ERROR] [$ts] $msg${NC}" >&2 ;;
        DEBUG) [[ "${VERBOSE:-false}" == "true" ]] && echo -e "${CYAN}[DEBUG] [$ts] $msg${NC}" ;;
    esac
}

# ===== 初始化 =====
init() {
    mkdir -p "$ALERT_STATE_DIR"
    load_config

    # 检查日志文件
    for log_file in "${LOG_FILES[@]}"; do
        if [[ ! -f "$log_file" ]]; then
            log_msg WARN "日志文件不存在: $log_file"
        elif [[ ! -r "$log_file" ]]; then
            log_msg ERROR "无权限读取: $log_file"
            exit 1
        fi
    done

    log_msg INFO "初始化完成，监控 ${#LOG_FILES[@]} 个日志文件"
}

# ===== 告警去重 =====
should_alert() {
    local rule_id=$1
    local now
    now=$(date +%s)

    # 冷却期检查
    local state_file="$ALERT_STATE_DIR/$rule_id"
    if [[ -f "$state_file" ]]; then
        local last_alert
        last_alert=$(cat "$state_file")
        if (( now - last_alert < ALERT_COOLDOWN )); then
            return 1
        fi
    fi

    # 全局限流
    local window_elapsed=$((now - GLOBAL_WINDOW_START))
    if (( window_elapsed >= 60 )); then
        GLOBAL_WINDOW_START=$now
        GLOBAL_COUNT=()
    fi

    GLOBAL_COUNT["global"]=$(( ${GLOBAL_COUNT["global"]:-0} + 1 ))
    if (( ${GLOBAL_COUNT["global"]} > MAX_ALERTS_PER_MINUTE )); then
        return 1
    fi

    echo "$now" > "$state_file"
    return 0
}

# ===== 发送告警 =====
send_alert() {
    local level=$1 message=$2 log_file=$3
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    local host
    host=$(hostname)

    # 终端输出
    case "$level" in
        critical) echo -e "${RED}[CRIT] [$ts] $message${NC}" ;;
        warning)  echo -e "${YELLOW}[WARN] [$ts] $message${NC}" ;;
        info)     echo -e "${GREEN}[INFO] [$ts] $message${NC}" ;;
    esac

    # 企业微信
    if [[ -n "$WEBHOOK_URL" ]]; then
        curl -sS -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"[$level] $message\n主机: $host\n时间: $ts\"}}" \
            --connect-timeout 5 --max-time 10 2>/dev/null &
    fi

    # 钉钉
    if [[ -n "$DINGTALK_URL" ]]; then
        curl -sS -X POST "$DINGTALK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"[$level] $message\n主机: $host\n时间: $ts\"}}" \
            --connect-timeout 5 --max-time 10 2>/dev/null &
    fi

    # 邮件
    if [[ -n "$ALERT_EMAIL" && "$level" != "info" ]]; then
        echo "[$level] $message (主机: $host, 时间: $ts)" | \
            mail -s "[${level^^}] 日志告警" "$ALERT_EMAIL" 2>/dev/null &
    fi

    # 告警日志
    echo "[$ts] [$level] $message | 来源: $log_file" >> "$LOG_MONITOR_LOG" 2>/dev/null || true
}

# ===== 规则匹配 =====
match_pattern() {
    local line="$1" pattern="$2" match_type="$3"

    case "$match_type" in
        keyword) echo "$line" | grep -qi "$pattern" ;;
        regex)   echo "$line" | grep -qE "$pattern" ;;
        *)       return 1 ;;
    esac
}

# ===== 提取上下文 =====
extract_context() {
    local line="$1" ctx=""
    local ip
    ip=$(echo "$line" | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' | head -1 || true)
    [[ -n "$ip" ]] && ctx+="IP: $ip"
    echo "$ctx"
}

# ===== 频率检查 =====
check_frequency() {
    local rule_id=$1 window=$2 threshold=$3
    local now
    now=$(date +%s)

    if [[ -z "${FREQ_START[$rule_id]:-}" ]]; then
        FREQ_COUNT[$rule_id]=1
        FREQ_START[$rule_id]=$now
        return 1
    fi

    local elapsed=$((now - FREQ_START[$rule_id]))
    if (( elapsed > window )); then
        FREQ_COUNT[$rule_id]=1
        FREQ_START[$rule_id]=$now
        return 1
    fi

    FREQ_COUNT[$rule_id]=$(( ${FREQ_COUNT[$rule_id]} + 1 ))
    if (( ${FREQ_COUNT[$rule_id]} >= threshold )); then
        FREQ_COUNT[$rule_id]=0
        FREQ_START[$rule_id]=$now
        return 0
    fi

    return 1
}

# ===== 处理单行日志 =====
process_line() {
    local line="$1" log_file="$2"

    # 检查关键字/正则规则
    for rule in "${ALERT_RULES[@]}"; do
        IFS='|' read -r rule_id pattern level desc match_type <<< "$rule"

        if match_pattern "$line" "$pattern" "$match_type"; then
            local ctx
            ctx=$(extract_context "$line")

            if should_alert "$rule_id"; then
                send_alert "$level" "$desc${ctx:+ | $ctx}" "$log_file"
            fi
            return 0
        fi
    done

    # 检查频率规则
    for rule in "${FREQ_RULES[@]}"; do
        IFS='|' read -r rule_id pattern level desc window threshold <<< "$rule"

        if match_pattern "$line" "$pattern" "keyword"; then
            if check_frequency "$rule_id" "$window" "$threshold"; then
                send_alert "$level" "${desc} (${FREQ_COUNT[$rule_id]:-?}次/${window}秒)" "$log_file"
            fi
        fi
    done
}

# ===== 实时监控模式 =====
monitor_realtime() {
    log_msg INFO "启动实时监控模式"
    log_msg INFO "监控文件: ${LOG_FILES[*]}"
    log_msg INFO "按 Ctrl+C 停止"

    local current_log=""

    # 使用 tail -F 监控（支持日志轮转）
    tail -F "${LOG_FILES[@]}" 2>/dev/null | while IFS= read -r line; do
        # 多文件切换标识
        if [[ "$line" =~ ^==>\ (.*)\ \<==$ ]]; then
            current_log="${BASH_REMATCH[1]}"
            continue
        fi
        [[ -z "$line" ]] && continue

        process_line "$line" "${current_log:-unknown}"
    done
}

# ===== 定时扫描模式 =====
scan_logs() {
    local minutes=${1:-5}
    log_msg INFO "扫描过去 ${minutes} 分钟的日志..."

    local total_alerts=0

    for log_file in "${LOG_FILES[@]}"; do
        [[ ! -f "$log_file" ]] && continue

        # 计算截止时间
        local cutoff
        cutoff=$(date -d "${minutes} minutes ago" '+%b %_d %H:%M' 2>/dev/null || \
                 date -v-${minutes}M '+%b %_d %H:%M' 2>/dev/null || echo "")

        if [[ -n "$cutoff" ]]; then
            while IFS= read -r line; do
                [[ -z "$line" ]] && continue
                process_line "$line" "$log_file"
                ((total_alerts++)) || true
            done < <(sed -n "/$cutoff/,\$p" "$log_file" 2>/dev/null || true)
        fi
    done

    log_msg INFO "扫描完成，处理 $total_alerts 行日志"
}

# ===== SSH 暴力破解检测 =====
detect_brute_force() {
    log_msg INFO "SSH 暴力破解检测..."

    local auth_log="/var/log/auth.log"
    [[ ! -f "$auth_log" ]] && auth_log="/var/log/secure"
    [[ ! -f "$auth_log" ]] && { log_msg ERROR "找不到认证日志"; return 1; }

    local threshold=${1:-5}

    awk '/Failed password/ {print $(NF-3)}' "$auth_log" 2>/dev/null | \
        sort | uniq -c | sort -rn | \
    while read -r count ip; do
        if (( count > threshold )); then
            local rule_id="BF_$(echo "$ip" | md5sum | cut -d' ' -f1)"
            if should_alert "$rule_id"; then
                send_alert "critical" "SSH 暴力破解: IP $ip 失败 $count 次" "$auth_log"
            fi
        fi
    done

    log_msg INFO "暴力破解检测完成"
}

# ===== Nginx 5xx 错误率检测 =====
detect_nginx_5xx() {
    log_msg INFO "Nginx 5xx 错误率检测..."

    local access_log="/var/log/nginx/access.log"
    [[ ! -f "$access_log" ]] && { log_msg WARN "Nginx 访问日志不存在"; return 0; }

    local threshold=${1:-5}  # 5% 阈值
    local sample_size=1000

    local total errors rate
    total=$(tail -"$sample_size" "$access_log" 2>/dev/null | wc -l)
    errors=$(tail -"$sample_size" "$access_log" 2>/dev/null | awk '$9 >= 500 && $9 < 600' | wc -l)

    if (( total > 0 )); then
        rate=$((errors * 100 / total))
        if (( rate > threshold )); then
            local rule_id="NGX5XX"
            if should_alert "$rule_id"; then
                send_alert "critical" \
                    "Nginx 5xx 错误率 ${rate}% (${errors}/${total}) 超过阈值 ${threshold}%" \
                    "$access_log"
            fi
        else
            log_msg INFO "Nginx 5xx 错误率: ${rate}% (正常)"
        fi
    fi
}

# ===== 状态查看 =====
show_status() {
    echo "===== 日志监控状态 ====="
    echo ""

    # PID 检查
    local pid_file="/var/run/log_monitor.pid"
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "运行状态: 运行中 (PID: $pid)"
        else
            echo "运行状态: 已停止 (PID 文件过期)"
        fi
    else
        echo "运行状态: 未运行"
    fi

    echo ""
    echo "监控文件:"
    for f in "${LOG_FILES[@]}"; do
        if [[ -f "$f" ]]; then
            local size
            size=$(du -h "$f" | awk '{print $1}')
            echo "  [OK] $f ($size)"
        else
            echo "  [--] $f (不存在)"
        fi
    done

    echo ""
    echo "告警规则: ${#ALERT_RULES[@]} 条关键字规则, ${#FREQ_RULES[@]} 条频率规则"
    echo "告警冷却: ${ALERT_COOLDOWN} 秒"
    echo "全局限流: ${MAX_ALERTS_PER_MINUTE} 次/分钟"

    if [[ -f "$LOG_MONITOR_LOG" ]]; then
        local alert_count
        alert_count=$(wc -l < "$LOG_MONITOR_LOG")
        echo ""
        echo "历史告警: ${alert_count} 条"
        echo "最近 5 条告警:"
        tail -5 "$LOG_MONITOR_LOG" 2>/dev/null | sed 's/^/  /'
    fi

    echo ""
    echo "通知渠道:"
    [[ -n "$WEBHOOK_URL" ]] && echo "  企业微信: 已配置" || echo "  企业微信: 未配置"
    [[ -n "$DINGTALK_URL" ]] && echo "  钉钉: 已配置" || echo "  钉钉: 未配置"
    [[ -n "$ALERT_EMAIL" ]] && echo "  邮件: $ALERT_EMAIL" || echo "  邮件: 未配置"
}

# ===== 帮助信息 =====
usage() {
    cat << EOF
用法: $SCRIPT_NAME <命令> [参数]

日志监控告警脚本 v${SCRIPT_VERSION}

命令:
    monitor              实时监控模式 (tail -F)
    scan [分钟]          扫描过去 N 分钟的日志 (默认 5)
    bruteforce [阈值]    SSH 暴力破解检测 (默认 5 次)
    nginx5xx [阈值]      Nginx 5xx 错误率检测 (默认 5%)
    status               查看监控状态
    help                 显示帮助

环境变量:
    WECHAT_WEBHOOK_URL   企业微信 Webhook 地址
    DINGTALK_URL         钉钉 Webhook 地址
    ALERT_EMAIL          告警邮件地址
    LOG_MONITOR_CONFIG   配置文件路径
    VERBOSE              详细输出 (true/false)

配置文件: $CONFIG_FILE
告警日志: $LOG_MONITOR_LOG

示例:
    $SCRIPT_NAME monitor                    # 实时监控
    $SCRIPT_NAME scan 10                    # 扫描过去 10 分钟
    $SCRIPT_NAME bruteforce 10              # 暴力破解检测 (阈值 10 次)
    WEBHOOK_URL=https://... $SCRIPT_NAME monitor  # 带 Webhook 的实时监控
EOF
}

# ===== 主入口 =====
main() {
    local command="${1:-help}"

    case "$command" in
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
            detect_brute_force "${2:-5}"
            ;;
        nginx5xx)
            init
            detect_nginx_5xx "${2:-5}"
            ;;
        status)
            load_config
            show_status
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            echo "未知命令: $command"
            usage
            exit 1
            ;;
    esac
}

main "$@"
```

---

### 8. 性能优化

#### 8.1 大日志文件处理

```bash
# ===== 性能优化策略 =====

# 1. 避免逐行 grep（使用 awk 替代）
# 慢: cat big.log | grep "ERROR" | awk '{print $1}'
# 快: awk '/ERROR/ {print $1}' big.log

# 2. 使用 -m 限制匹配次数
grep -m 100 "ERROR" huge.log  # 只找前 100 个

# 3. 使用 tail 限制扫描范围
tail -10000 /var/log/syslog | grep "ERROR"

# 4. 使用 sed 限制时间范围
sed -n '/May  1 14:/,/May  1 15:/p' /var/log/syslog | grep "ERROR"

# 5. 并行处理多个文件
parallel grep "ERROR" {} ::: /var/log/*.log
```

#### 8.2 内存控制

```bash
# ===== 内存优化 =====

# 1. 避免将整个文件读入内存
# 慢: content=$(cat huge.log)
# 快: while IFS= read -r line; do ... done < huge.log

# 2. 使用关联数组有界增长
# 定期清理过期的频率统计
cleanup_frequency_data() {
    local now
    now=$(date +%s)
    for key in "${!FREQ_START[@]}"; do
        if (( now - FREQ_START[$key] > 3600 )); then
            unset "FREQ_START[$key]"
            unset "FREQ_COUNT[$key]"
        fi
    done
}

# 3. 限制告警状态文件数量
cleanup_alert_state() {
    local max_files=1000
    local count
    count=$(find "$ALERT_STATE_DIR" -type f | wc -l)
    if (( count > max_files )); then
        # 删除最旧的文件
        find "$ALERT_STATE_DIR" -type f -printf '%T+ %p\n' | \
            sort | head -$((count - max_files)) | \
            awk '{print $2}' | xargs rm -f
    fi
}
```

#### 8.3 进程管理优化

```bash
# ===== 进程优化 =====

# 1. 使用 exec 重定向（减少子进程）
exec 3< <(tail -F /var/log/syslog)
while read -r line <&3; do
    process_line "$line" "syslog"
done

# 2. 批量处理（减少 fork 次数）
# 慢: 每行都 fork grep
while read -r line; do
    echo "$line" | grep "ERROR"
done < logfile

# 快: 使用 Bash 内置正则
while read -r line; do
    if [[ "$line" =~ ERROR ]]; then
        ...
    fi
done < logfile

# 3. 使用 noclobber 避免竞争
set -o noclobber
```

---

### 9. 监控脚本自身的健康检查

```bash
#!/bin/bash
# monitor_health.sh — 监控日志监控脚本自身的健康状态

check_monitor_health() {
    local pid_file="/var/run/log_monitor.pid"
    local max_memory_mb=256
    local max_cpu_percent=20

    # 1. 检查进程是否存在
    if [[ ! -f "$pid_file" ]]; then
        echo "CRITICAL: 监控进程 PID 文件不存在"
        return 1
    fi

    local pid
    pid=$(cat "$pid_file")
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "CRITICAL: 监控进程已退出 (PID: $pid)"
        # 自动重启
        /opt/scripts/log_monitor.sh monitor &
        echo "INFO: 已自动重启监控进程"
        return 1
    fi

    # 2. 检查内存使用
    local mem_kb
    mem_kb=$(ps -o rss= -p "$pid" 2>/dev/null || echo 0)
    local mem_mb=$((mem_kb / 1024))
    if (( mem_mb > max_memory_mb )); then
        echo "WARNING: 监控进程内存使用过高: ${mem_mb}MB (阈值: ${max_memory_mb}MB)"
    fi

    # 3. 检查 CPU 使用
    local cpu
    cpu=$(ps -o %cpu= -p "$pid" 2>/dev/null || echo 0)
    if (( ${cpu%.*} > max_cpu_percent )); then
        echo "WARNING: 监控进程 CPU 使用过高: ${cpu}%"
    fi

    # 4. 检查日志文件是否有更新
    local alert_log="/var/log/log_monitor_alerts.log"
    if [[ -f "$alert_log" ]]; then
        local last_modified
        last_modified=$(stat -c %Y "$alert_log" 2>/dev/null || echo 0)
        local now
        now=$(date +%s)
        local age=$((now - last_modified))
        if (( age > 86400 )); then
            echo "WARNING: 告警日志超过 24 小时未更新"
        fi
    fi

    echo "OK: 监控进程正常运行 (PID: $pid, MEM: ${mem_mb}MB, CPU: ${cpu}%)"
}

check_monitor_health
```

---

## 💻 实战练习

### 练习 1：基础日志监控

编写一个脚本，实时监控 `/var/log/syslog`，当出现 "ERROR" 时在终端显示红色告警。

```bash
# 你的代码
```

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
NC='\033[0m'

echo "开始监控 /var/log/syslog，出现 ERROR 将告警..."
echo "按 Ctrl+C 停止"

tail -F /var/log/syslog 2>/dev/null | while IFS= read -r line; do
    if echo "$line" | grep -qi "ERROR"; then
        echo -e "${RED}[ALERT] $(date '+%H:%M:%S') $line${NC}"
    fi
done
```

</details>

### 练习 2：告警去重

为练习 1 的脚本添加去重功能：同一类型的错误在 5 分钟内只告警一次。

```bash
# 你的代码
```

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
NC='\033[0m'
COOLDOWN=300
STATE_DIR="/tmp/alert_dedup"
mkdir -p "$STATE_DIR"

should_alert() {
    local key=$1
    local now
    now=$(date +%s)
    local state_file="$STATE_DIR/$key"

    if [[ -f "$state_file" ]]; then
        local last
        last=$(cat "$state_file")
        if (( now - last < COOLDOWN )); then
            return 1
        fi
    fi

    echo "$now" > "$state_file"
    return 0
}

echo "开始监控 /var/log/syslog (5 分钟去重)..."

tail -F /var/log/syslog 2>/dev/null | while IFS= read -r line; do
    if echo "$line" | grep -qi "ERROR"; then
        # 使用错误内容的 md5 作为去重 key
        local key
        key=$(echo "$line" | md5sum | cut -d' ' -f1)
        if should_alert "$key"; then
            echo -e "${RED}[ALERT] $(date '+%H:%M:%S') $line${NC}"
        fi
    fi
done
```

</details>

### 练习 3：SSH 暴力破解检测

编写脚本分析 `/var/log/auth.log`，找出 5 分钟内失败登录超过 5 次的 IP，并自动封禁（使用 iptables 或 ufw）。

```bash
# 你的代码
```

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
set -euo pipefail

AUTH_LOG="/var/log/auth.log"
THRESHOLD=5
BAN_DURATION=3600  # 封禁 1 小时

echo "SSH 暴力破解检测..."
echo "阈值: 5 分钟内失败超过 $THRESHOLD 次"

# 统计最近 5 分钟的失败登录
cutoff=$(date -d '5 minutes ago' '+%b %_d %H:%M' 2>/dev/null || \
         date -v-5M '+%b %_d %H:%M' 2>/dev/null)

if [[ -n "$cutoff" ]]; then
    sed -n "/$cutoff/,\$p" "$AUTH_LOG" | \
        awk '/Failed password/ {print $(NF-3)}' | \
        sort | uniq -c | sort -rn | \
    while read -r count ip; do
        if (( count > THRESHOLD )); then
            echo "检测到暴力破解: IP $ip (失败 $count 次)"

            # 检查是否已封禁
            if ufw status | grep -q "$ip"; then
                echo "  已封禁，跳过"
            else
                echo "  封禁 IP: $ip"
                ufw deny from "$ip" to any
                echo "  $ip 已封禁 ($BAN_DURATION 秒后自动解封)"

                # 后台定时解封
                (sleep "$BAN_DURATION" && ufw delete deny from "$ip" to any) &
            fi
        fi
    done
fi

echo "检测完成"
```

</details>

### 练习 4：完整告警系统

基于本课学到的知识，编写一个支持以下功能的日志监控脚本：
1. 实时监控多个日志文件
2. 关键字告警 + 频率告警
3. 告警去重（5 分钟内不重复）
4. 企业微信 Webhook 通知
5. systemd 服务化部署

```bash
# 你的代码（参考第 7 节的完整实现）
```

---

## 🎯 面试题精选

### 面试题 1：如何设计一个日志告警系统？

**参考答案**：

一个完整的日志告警系统应包含以下组件：

**架构设计**：
```
日志源 → 采集层 → 规则引擎 → 告警处理 → 通知渠道
```

**关键设计点**：

1. **采集层**：使用 `tail -F`（而非 `tail -f`）支持日志轮转，支持多文件并行监控
2. **规则引擎**：支持关键字匹配、正则匹配、频率告警、趋势告警等多维度规则
3. **告警去重**：同一规则 N 秒内不重复告警，避免告警风暴
4. **限流机制**：全局每分钟最多 N 条告警，保护通知渠道
5. **告警升级**：同一问题持续未解决，自动升级告警级别
6. **多渠道通知**：终端、Webhook、邮件、短信等多渠道分发
7. **可配置性**：通过配置文件管理规则，支持热加载
8. **自监控**：监控脚本自身的健康状态，支持自动重启

### 面试题 2：如何处理日志轮转？

**参考答案**：

日志轮转（logrotate）是 Linux 系统管理日志文件大小的标准机制。监控脚本需要感知日志轮转，否则会丢失新日志。

**问题场景**：
```
1. logrotate 将 syslog 轮转为 syslog.1
2. 创建新的空 syslog 文件
3. tail -f 仍然跟踪旧的文件描述符
4. 新日志写入新的 syslog，tail -f 看不到
```

**解决方案**：

1. **使用 tail -F**（推荐）：`tail -F` = `tail --follow=name --retry`，它跟踪文件名而非文件描述符，文件被轮转后自动重新打开

2. **使用 inotifywait**：直接监控文件系统的 inotify 事件
```bash
inotifywait -m -e modify /var/log/syslog | while read; do
    tail -1 /var/log/syslog | process_line
done
```

3. **轮转钩子**：在 logrotate 的 postrotate 脚本中通知监控进程重新打开文件
```bash
# /etc/logrotate.d/syslog
postrotate
    /bin/kill -HUP $(cat /var/run/log_monitor.pid)
endscript
```

4. **copytruncate 策略**：在 logrotate 配置中使用 `copytruncate` 而非 `create`，先复制再清空，不需要重新打开文件

### 面试题 3：如何避免告警风暴？

**参考答案**：

告警风暴是指短时间内产生大量重复告警，导致通知渠道被淹没。

**避免策略**：

1. **去重**：同一规则在 N 秒内只告警一次
```bash
# 使用状态文件记录上次告警时间
if (( now - last_alert < cooldown )); then
    return  # 跳过
fi
```

2. **限流**：全局每分钟最多 N 条告警
```bash
# 全局计数器
if (( alerts_this_minute > MAX )); then
    return  # 跳过
fi
```

3. **告警合并**：将多条相同类型的告警合并为一条
```
# 原始: 100 条 "Failed password from 1.2.3.4"
# 合并: "SSH 暴力破解: IP 1.2.3.4 失败 100 次 (5分钟内)"
```

4. **告警升级**：频繁告警自动升级级别，而非增加告警数量

5. **静默期**：维护窗口期间自动静默

6. **告警抑制**：当高级别告警触发时，抑制相关的低级别告警

### 面试题 4：tail -f 和 tail -F 的区别是什么？

**参考答案**：

| 特性 | tail -f | tail -F |
|------|---------|---------|
| 跟踪方式 | 跟踪文件描述符 | 跟踪文件名 |
| 日志轮转 | 文件轮转后失效 | 文件轮转后自动重新打开 |
| 文件不存在 | 报错退出 | 等待文件创建（--retry） |
| 适用场景 | 短期查看 | 长期监控 |
| 别名 | --follow=descriptor | --follow=name --retry |

**在日志监控脚本中应始终使用 `tail -F`**，因为它能正确处理日志轮转场景。

### 面试题 5：如何监控多个日志文件？

**参考答案**：

1. **tail -F 多文件**（简单场景）：
```bash
tail -F /var/log/syslog /var/log/auth.log | while read line; do
    # 注意：tail 会输出 ==> filename <== 分隔行
    process_line "$line"
done
```

2. **多进程**（每个文件一个进程）：
```bash
for file in "${files[@]}"; do
    tail -F "$file" | while read line; do
        process_line "$line" "$file"
    done &
done
wait
```

3. **命名管道**（高级场景）：
```bash
mkfifo /tmp/log_pipe
tail -F /var/log/syslog > /tmp/log_pipe &
while read line < /tmp/log_pipe; do
    process_line "$line"
done
```

4. **inotifywait**（文件系统事件）：
```bash
inotifywait -m -e modify /var/log/*.log | while read; do
    # 处理变化的文件
done
```

### 面试题 6：日志监控脚本如何保证自身高可用？

**参考答案**：

1. **systemd 托管**：使用 systemd service 管理进程，配置 `Restart=on-failure` 自动重启
2. **健康检查**：定期检查进程状态、内存使用、CPU 使用
3. **自动恢复**：检测到异常时自动重启
4. **资源限制**：使用 systemd 的 `MemoryMax`、`CPUQuota` 防止资源耗尽
5. **日志记录**：记录监控脚本自身的运行日志
6. **告警**：监控脚本自身故障时通过其他渠道告警
7. **无状态设计**：脚本重启后不影响告警逻辑（状态持久化到文件）

### 面试题 7：如何设计告警规则以减少误报？

**参考答案**：

1. **使用正则而非宽泛关键字**：`grep -E " 5[0-9]{2} "` 比 `grep "5"` 更精确
2. **排除已知模式**：排除健康检查、测试请求等已知的"正常错误"
3. **频率阈值**：单次出现不告警，连续出现 N 次才告警
4. **时间窗口**：只在特定时间段内告警（如排除维护窗口）
5. **上下文验证**：结合多个字段判断（如 HTTP 5xx + 非测试路径）
6. **基线对比**：与历史数据对比，只在偏离基线时告警
7. **人工确认**：新规则先用"观察模式"运行一段时间，确认无误后再开启告警

---

## 📚 深入阅读

### 官方文档
- [rsyslog 官方文档](https://www.rsyslog.com/doc/)
- [systemd journal 文档](https://www.freedesktop.org/software/systemd/man/journald.conf.html)
- [logrotate 手册](https://man7.org/linux/man-pages/man8/logrotate.8.html)
- [tail 手册](https://man7.org/linux/man-pages/man1/tail.1.html)
- [inotify 手册](https://man7.org/linux/man-pages/man7/inotify.7.html)

### 推荐资源
- [Google SRE Book - Monitoring](https://sre.google/sre-book/practical-alerting/) — 告警最佳实践
- [Prometheus Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) — 现代告警规则设计
- [Grafana Loki](https://grafana.com/oss/loki/) — 轻量级日志聚合系统
- [ELK Stack](https://www.elastic.co/elastic-stack) — 企业级日志管理平台

### 相关工具
- [Fluentd](https://www.fluentd.org/) — 统一日志层
- [Filebeat](https://www.elastic.co/beats/filebeat) — 轻量级日志采集器
- [Vector](https://vector.dev/) — 高性能日志处理管道
- [GoAccess](https://goaccess.io/) — 实时 Web 日志分析

---

## ✅ 自检清单

### 理论检查点
- [ ] 理解 tail -f 和 tail -F 的区别及日志轮转感知机制
- [ ] 掌握告警规则引擎的设计（关键字、正则、频率、趋势）
- [ ] 理解告警去重和限流的实现原理
- [ ] 了解多日志文件监控的技术方案
- [ ] 理解日志监控脚本的性能优化策略

### 实操检查点
- [ ] 能够编写实时日志监控脚本（tail -F + 逐行处理）
- [ ] 实现关键字告警和正则告警
- [ ] 实现频率告警（同一错误 N 分钟内超过 M 次）
- [ ] 实现告警去重（同一规则 N 秒内不重复告警）
- [ ] 实现企业微信/钉钉 Webhook 通知
- [ ] 使用 systemd 将脚本部署为服务
- [ ] 编写 SSH 暴力破解检测脚本
- [ ] 编写 Nginx 5xx 错误率监控脚本

---

*由 SRE 学习计划生成 | 2026-04-25*
