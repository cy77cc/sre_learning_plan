# Day 13: 日志管理 — journalctl / rsyslog / logrotate / 日志分析

> 📅 日期：2026-04-25
> 📖 学习主题：日志管理 — journalctl / rsyslog / logrotate / 日志分析
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Linux 日志体系架构与 syslog 协议
- 掌握 systemd-journald 二进制日志管理与 journalctl 高级查询
- 理解 rsyslog 的消息路由机制与配置语法
- 掌握 logrotate 日志轮转原理与自定义配置
- 具备日志爆满应急处理和安全日志分析能力
- 能用 awk/grep/sed 高效分析 Nginx/系统日志

---

## 📖 Linux 日志体系架构

### 1.1 日志体系概览

Linux 有**两套日志系统**并行工作：

```
┌──────────────────────────────────────────────────────┐
│                    应用程序                           │
│  (Nginx, MySQL, SSH, Cron, 自定义应用...)             │
└──────┬───────────────────────────┬───────────────────┘
       │                           │
       ▼                           ▼
┌──────────────┐         ┌────────────────────┐
│  syslog API   │         │  systemd-journald   │
│  (传统方式)    │         │  (systemd 原生)      │
│      │        │         │         │           │
│      ▼        │         │         ▼           │
│  rsyslogd     │◄────────│  /dev/log (socket)  │
│      │        │         │                     │
│      ▼        │         │  /var/log/journal/   │
│  /var/log/    │         │  (二进制格式)         │
│  文本文件      │         └────────────────────┘
└──────────────┘
```

### 1.2 重要日志文件速查表

| 日志路径 | 来源 | 用途 | 关键字段 |
|---------|------|------|---------|
| `/var/log/syslog` | rsyslog | 系统综合日志（Ubuntu） | 所有 syslog 消息 |
| `/var/log/messages` | rsyslog | 系统综合日志（RHEL） | 同 syslog |
| `/var/log/auth.log` | PAM/SSH/sudo | 认证与授权 | 登录、sudo、SSH 密钥 |
| `/var/log/kern.log` | 内核 | 内核消息 | 硬件错误、OOM、驱动 |
| `/var/log/dpkg.log` | dpkg | 软件包安装/卸载 | apt install/remove 记录 |
| `/var/log/boot.log` | systemd | 启动过程日志 | 服务启动状态 |
| `/var/log/journal/` | journald | systemd 二进制日志 | 所有 systemd 服务日志 |
| `/var/log/nginx/access.log` | Nginx | HTTP 访问日志 | 请求方法、状态码、UA |
| `/var/log/nginx/error.log` | Nginx | HTTP 错误日志 | 配置错误、5xx 根因 |
| `/var/log/mysql/error.log` | MySQL | 数据库错误日志 | 慢查询、崩溃恢复 |
| `/var/log/cron.log` | cron | 定时任务日志 | 任务执行记录 |

---

## 📖 systemd-journald 与 journalctl

### 2.1 journald 架构

journald 是 systemd 的原生日志收集器，替代了传统的 syslog 部分功能：

- **收集来源**：内核日志 (kmsg)、系统服务 (stdout/stderr)、syslog 消息、审计日志
- **存储格式**：二进制 (structured journal)，支持索引和快速查询
- **存储位置**：`/run/log/journal/` (易失) 或 `/var/log/journal/` (持久)
- **转发机制**：可通过配置将日志转发到 rsyslog

```bash
# 检查 journal 状态
sudo systemctl status systemd-journald

# 查看 journal 持久化状态
# 如果 /var/log/journal/ 不存在，日志仅在内存中（重启丢失）
ls -la /var/log/journal/ 2>/dev/null || echo "未启用持久化"

# 启用持久化（重启后保留日志）
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
```

### 2.2 journalctl 核心用法

```bash
# === 基础查询 ===
journalctl                    # 查看所有日志（分页）
journalctl -f                 # 实时跟踪（类似 tail -f）
journalctl -n 50              # 最近 50 条
journalctl --no-pager         # 不分页，直接输出

# === 按时间范围 ===
journalctl --since "2026-05-01 10:00:00" --until "2026-05-01 11:00:00"
journalctl --since "1 hour ago"
journalctl --since "2026-05-01" --until "2026-05-02"
journalctl --since yesterday --until today

# === 按服务/单元 ===
journalctl -u nginx           # nginx 服务的所有日志
journalctl -u nginx -f        # 实时跟踪 nginx
journalctl -u nginx --since "30 min ago"

# 多个服务同时查看
journalctl -u nginx -u php-fpm --since "1h ago"

# === 按日志级别 ===
# emerg(0) > alert(1) > crit(2) > err(3) > warning(4) > notice(5) > info(6) > debug(7)
journalctl -p err             # 错误及以上级别
journalctl -p 3               # 同上（数字形式）
journalctl -p warning..err    # 范围：warning 到 err

# === 按进程/PID ===
journalctl _PID=1234
journalctl _COMM=nginx        # 按进程名
journalctl _UID=0             # 按用户 ID（0 = root）

# === 按内核日志 ===
journalctl -k                 # 仅内核消息 (dmesg)
journalctl -k --since "10 min ago"

# === 结构化输出 ===
journalctl -o json            # JSON 格式（适合程序解析）
journalctl -o json-pretty     # 美化的 JSON
journalctl -o verbose         # 显示所有字段
journalctl -o cat             # 仅消息内容（无时间/主机前缀）

# 查看某条日志的所有元数据字段
journalctl -n 1 -o verbose
```

### 2.3 journalctl 高级过滤（字段匹配）

journalctl 支持按任意结构化字段过滤：

```bash
# 列出所有可用字段
journalctl -F _SYSTEMD_UNIT
# 输出所有出现过的 systemd 单元名

journalctl -F _COMM
# 输出所有出现过的进程名

# 组合过滤
journalctl _SYSTEMD_UNIT=nginx.service _PID=1234
journalctl _SYSTEMD_UNIT=sshd.service PRIORITY=3  # SSH 错误

# 按可执行路径过滤
journalctl _EXE=/usr/sbin/sshd

# 按源文件过滤
journalctl SYSLOG_FACILITY=auth    # 认证相关
journalctl SYSLOG_FACILITY=daemon  # 守护进程相关
```

### 2.4 journal 空间管理

```bash
# 查看当前占用
journalctl --disk-usage
# Archives take up: 320.0M in the file system

# 清理策略
sudo journalctl --vacuum-size=500M       # 保留最近 500MB
sudo journalctl --vacuum-time=7d         # 只保留最近 7 天
sudo journalctl --vacuum-files=5         # 只保留 5 个归档文件

# 配置持久化策略
sudo vim /etc/systemd/journald.conf
# [Journal]
# Storage=persistent          # persistent|auto|volatile|none
# SystemMaxUse=500M           # 磁盘最大占用
# SystemMaxFiles=5            # 最大归档文件数
# MaxRetentionSec=30day       # 最长保留时间
# ForwardToSyslog=no          # 是否转发到 rsyslog
# MaxFileSec=1day             # 单个 journal 文件最大时长

sudo systemctl restart systemd-journald
```

---

## 📖 rsyslog 配置与消息路由

### 3.1 rsyslog 工作原理

rsyslog 是 syslog 协议的高性能实现，核心概念：

```
消息来源 ──→ 输入模块 (imuxsock/imtcp/imfile) ──→ 过滤器 ──→ 输出模块 (omfile/omfwd)
    │              │                              │              │
  应用日志       /dev/log                    按 facility       写入文件
  内核日志       TCP/UDP                     和 priority       转发远程
  远程日志       文件尾                     过滤消息           写入数据库
```

**Facility（设施）和 Priority（优先级）**：

| Facility | 数字 | 用途 |
|----------|------|------|
| `kern` | 0 | 内核消息 |
| `user` | 1 | 用户进程 |
| `mail` | 2 | 邮件系统 |
| `daemon` | 3 | 系统守护进程 |
| `auth` | 4 | 认证/授权 |
| `syslog` | 5 | syslog 自身 |
| `lpr` | 6 | 打印系统 |
| `cron` | 9 | 定时任务 |
| `local0-7` | 16-23 | 自定义用途 |

**选择器语法**：`facility.priority`
```
*.info              # 所有 facility 的 info 及以上级别
auth.err            # auth 的 err 及以上
mail.*              # mail 的所有级别
*.info;mail.none    # 所有 info 级别，但排除 mail
```

### 3.2 rsyslog 配置文件

```bash
# 主配置文件
cat /etc/rsyslog.conf

# 核心配置段：
# module(load="imuxsock")        # 本地 syslog socket
# module(load="imklog")          # 内核日志
# module(load="imtcp")           # TCP 输入（接收远程日志）
#   input(type="imtcp" port="514")

# 规则段（/etc/rsyslog.d/ 下的 *.conf 会按字母顺序加载）
```

```bash
# === 示例：自定义日志路由 ===
sudo cat > /etc/rsyslog.d/10-myapp.conf << 'EOF'
# 将所有 local0 设施的日志写到独立文件
local0.*    /var/log/myapp/all.log

# 将 local0 的 error 及以上单独存放（方便告警监控）
local0.err  /var/log/myapp/errors.log

# 将所有认证日志转发到远程日志服务器
auth.*      @@192.168.1.100:514    # @@ = TCP, @ = UDP

# 按程序名过滤（imfile 模块可以监控任意文本文件）
# 将 Nginx 错误日志也写到统一位置
$InputFileName /var/log/nginx/error.log
$InputFileTag nginx-error:
$InputFileStateFile stat-nginx-error
$InputFileSeverity error
$InputRunFileMonitor
EOF

sudo systemctl restart rsyslog
```

### 3.3 远程日志集中收集

```bash
# 日志服务器配置（接收端）
sudo cat > /etc/rsyslog.d/50-server.conf << 'EOF'
module(load="imtcp")
input(type="imtcp" port="514")
$template RemoteLogs,"/var/log/remote/%HOSTNAME%/%PROGRAMNAME%.log"
*.* ?RemoteLogs
& ~
EOF

# 客户端配置（发送端）
echo '*.* @@192.168.1.100:514' | sudo tee /etc/rsyslog.d/50-client.conf

sudo systemctl restart rsyslog
```

---

## 📖 logrotate 日志轮转

### 4.1 为什么需要 logrotate？

日志文件如果不管理会：
1. **无限增长** → 耗尽磁盘空间
2. **单个文件过大** → 编辑器打不开，分析工具 OOM
3. **无法按时间检索** → 所有日志混在一起

logrotate 的解决方案：
```
access.log (当前)
    ↓ 触发轮转
access.log → access.log.1 (重命名)
    ↓ 再次轮转
access.log.1 → access.log.2
access.log → access.log.1 (新建空文件)
    ↓ ...
access.log.30 → 删除（超出保留数）
```

### 4.2 logrotate 配置详解

```bash
# 主配置
cat /etc/logrotate.conf
# weekly        — 默认每周轮转
# rotate 4      — 保留 4 个旧文件
# create        — 轮转后创建新文件
# include /etc/logrotate.d/

# 查看有哪些服务配置了 logrotate
ls /etc/logrotate.d/
# apache2  mysql  nginx  rsyslog  ufw

# 强制测试（dry run，不实际操作）
sudo logrotate -d /etc/logrotate.d/nginx
# 输出会显示会执行什么操作

# 强制轮转（实际操作）
sudo logrotate -f /etc/logrotate.d/nginx
```

### 4.3 自定义 logrotate 配置

```bash
# 为自定义应用配置日志轮转
sudo cat > /etc/logrotate.d/myapp << 'EOF'
/var/log/myapp/*.log {
    daily               # 每天轮转
    rotate 30           # 保留 30 个旧文件
    compress            # 压缩旧文件（.gz）
    delaycompress       # 延迟一次压缩（最近一个不压缩，方便查看）
    missingok           # 文件不存在不报错
    notifempty          # 空文件不轮转
    create 0640 www-data adm   # 新文件权限和属主
    sharedscripts       # postrotate 只执行一次（多个文件时）
    dateext             # 用日期代替数字后缀（如 access.log-20260501）
    dateformat -%Y%m%d  # 日期格式

    # 轮转后通知应用重新打开日志文件
    postrotate
        # 方法 1：发送信号（Nginx 收到 USR1 重新打开日志）
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
        # 方法 2：重启服务（不推荐，会造成短暂中断）
        # systemctl reload nginx > /dev/null 2>&1 || true
    endscript

    # 轮转前可以做的事情
    prerotate
        # 例如：备份当前日志到远程
        # rsync -a /var/log/myapp/ backup-server:/logs/
    endscript
}
EOF

# 验证配置语法
sudo logrotate -d /etc/logrotate.d/myapp
```

### 4.4 logrotate 运行机制

```bash
# logrotate 通过 cron 定时执行
cat /etc/cron.daily/logrotate
#!/bin/sh
test -x /usr/sbin/logrotate || exit 0
/usr/sbin/logrotate /etc/logrotate.conf

# 状态文件（记录上次轮转时间）
cat /var/lib/logrotate/status
# 如果删除此文件，下次会重新轮转所有文件

# 手动触发（用于测试）
sudo logrotate -f /etc/logrotate.d/nginx
```

**logrotate 的 copytruncate vs create 模式**：

| 模式 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| `create`（默认）| 重命名旧文件 → 创建新文件 → 通知应用 | 无日志丢失 | 应用需支持重新打开文件 |
| `copytruncate` | 复制文件内容 → 清空原文件 | 不需要通知应用 | 两次操作间可能丢日志 |

```bash
# copytruncate 用法（应用不支持 reload 时）
/var/log/myapp/*.log {
    daily
    rotate 7
    copytruncate    # 不推荐，可能丢失轮转瞬间的日志
    compress
}
```

---

## 🔧 SRE 实战排障

### 场景 1：日志爆满应急处理

```bash
# ⚠️ 错误做法：直接 rm！
# rm /var/log/nginx/access.log
# 问题：进程仍持有文件描述符，磁盘空间不会释放！
# 验证：lsof | grep deleted → 显示已删除但被占用的文件

# ✅ 正确做法 1：清空文件内容（保留 inode）
> /var/log/nginx/access.log
# 或
truncate -s 0 /var/log/nginx/access.log

# ✅ 正确做法 2：触发 logrotate
sudo logrotate -f /etc/logrotate.d/nginx

# ✅ 正确做法 3：如果文件已被 rm，找到并释放
sudo lsof +L1 | grep access.log
# nginx  1234  www-data  7w  REG  8,1  5368709120  /var/log/nginx/access.log (deleted)
# 释放空间：
echo > /proc/1234/fd/7
# 或重启 nginx
sudo systemctl restart nginx
```

### 场景 2：SSH 暴力破解检测

```bash
#!/bin/bash
# ssh_brute_detect.sh — 检测 SSH 暴力破解
set -euo pipefail

echo "🔒 SSH 暴力破解检测 — $(date)"

# 方法 1：从 auth.log 统计失败登录
echo -e "\n失败登录 Top 10:"
sudo grep "Failed password" /var/log/auth.log | \
    awk '{print $(NF-3)}' | \
    sort | uniq -c | sort -rn | head -10 | \
    awk '{printf "  IP: %-18s  失败次数: %d\n", $2, $1}'

# 方法 2：从 journal 统计（适用于用 journal 的系统）
echo -e "\njournal 统计:"
sudo journalctl -u sshd --since "24 hours ago" | \
    grep "Failed password" | \
    awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/) print $i}' | \
    sort | uniq -c | sort -rn | head -10

# 方法 3：检查被阻止的 IP（如果装了 fail2ban）
echo -e "\nfail2ban 状态:"
sudo fail2ban-client status sshd 2>/dev/null || echo "  fail2ban 未安装"

# 自动封禁建议
echo -e "\n💡 建议："
echo "  1. 安装 fail2ban: sudo apt install fail2ban"
echo "  2. 禁用密码登录，改用 SSH 密钥"
echo "  3. 修改 SSH 端口: /etc/ssh/sshd_config → Port 2222"
```

### 场景 3：Nginx 日志分析

```bash
#!/bin/bash
# nginx_log_analysis.sh — Nginx 访问日志分析

LOG="/var/log/nginx/access.log"
[ ! -f "$LOG" ] && { echo "日志文件不存在: $LOG"; exit 1; }

echo "📊 Nginx 日志分析 — $LOG"
total=$(wc -l < "$LOG")
echo "总请求数: $total"

# 1. HTTP 状态码分布
echo -e "\n📈 状态码分布:"
awk '{print $9}' "$LOG" | sort | uniq -c | sort -rn | \
    awk '{printf "  HTTP %s: %6d 次 (%.1f%%)\n", $2, $1, $1/'"$total"'*100}'

# 2. 请求方法分布
echo -e "\n📋 请求方法:"
awk -F'"' '{print $2}' "$LOG" | awk '{print $1}' | sort | uniq -c | sort -rn

# 3. Top 10 访问 IP
echo -e "\n🌐 Top 10 IP:"
awk '{print $1}' "$LOG" | sort | uniq -c | sort -rn | head -10

# 4. Top 10 请求 URL
echo -e "\n🔗 Top 10 URL:"
awk -F'"' '{print $2}' "$LOG" | awk '{print $2}' | sort | uniq -c | sort -rn | head -10

# 5. 5xx 错误详情
echo -e "\n❌ 5xx 错误详情:"
awk '$9 >= 500' "$LOG" | head -20 | awk '{printf "  [%s] %s %s\n", $9, $7, $1}'

# 6. 每分钟请求量
echo -e "\n📊 每分钟请求量:"
awk '{print $4}' "$LOG" | cut -d: -f1-3 | sort | uniq -c | \
    sort -rn | head -10 | awk '{printf "  %s: %d 请求\n", $2, $1}'
```

---

## 💻 实战练习

### 练习 1：完整的日志管理方案

```bash
#!/bin/bash
# log_management_setup.sh — 生产级日志管理配置
set -euo pipefail

echo "📝 配置日志管理方案..."

# 1. 配置 journald 持久化和大小限制
sudo mkdir -p /etc/systemd/journald.conf.d
sudo cat > /etc/systemd/journald.conf.d/limits.conf << 'EOF'
[Journal]
Storage=persistent
SystemMaxUse=500M
MaxRetentionSec=30day
ForwardToSyslog=yes
EOF

# 2. 配置 rsyslog 分离业务日志
sudo cat > /etc/rsyslog.d/10-webapp.conf << 'EOF'
# 业务应用使用 local0
local0.*    /var/log/webapp/app.log
local0.err  /var/log/webapp/error.log

# 安全日志单独存储
auth,authpriv.*    /var/log/security/auth.log
EOF
sudo mkdir -p /var/log/{webapp,security}
sudo systemctl restart rsyslog

# 3. 配置 Nginx 日志轮转
sudo cat > /etc/logrotate.d/nginx-custom << 'EOF'
/var/log/nginx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
    sharedscripts
    dateext
    dateformat -%Y%m%d
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}
EOF

# 4. 配置 journal 自动清理
sudo journalctl --vacuum-size=500M
sudo journalctl --vacuum-time=7d

echo "✅ 日志管理方案配置完成"
echo "验证命令:"
echo "  journalctl --disk-usage"
echo "  sudo logrotate -d /etc/logrotate.d/nginx-custom"
echo "  logger -p local0.info '测试消息'"
```

### 练习 2：日志安全审计脚本

```bash
#!/bin/bash
# security_audit.sh — 日志安全审计
set -euo pipefail

echo "🔐 安全审计 — $(date '+%Y-%m-%d %H:%M')"

# 1. 暴力破解
echo -e "\n🚫 SSH 暴力破解 (过去24小时):"
sudo journalctl -u sshd --since "24 hours ago" | \
    grep "Failed password" | \
    awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9.]+$/ && $i != "for") print $i}' | \
    sort | uniq -c | sort -rn | head -10 | \
    while read count ip; do
        if [ "$count" -gt 10 ]; then
            echo "  🔴 $ip: $count 次失败登录"
        else
            echo "  🟡 $ip: $count 次失败登录"
        fi
    done

# 2. sudo 使用记录
echo -e "\n🔑 sudo 使用记录:"
sudo grep "sudo:" /var/log/auth.log 2>/dev/null | tail -10 | \
    while read line; do
        echo "  $line"
    done

# 3. 异常登录时间（非工作时间 22:00-06:00）
echo -e "\n⏰ 非工作时间成功登录:"
sudo grep "Accepted" /var/log/auth.log 2>/dev/null | \
    awk -F'[ :]' '{
        hour=$(NF-7);
        if (hour >= 22 || hour < 6)
            printf "  [%s:%s] %s 从 %s 登录\n", hour, $(NF-6), $(NF-13), $(NF-3)
    }'

# 4. 新建用户
echo -e "\n👤 新建用户:"
sudo grep "new user" /var/log/auth.log 2>/dev/null | tail -5

# 5. 文件完整性（可选：需要安装 aide 或 tripwire）
echo -e "\n📁 关键文件变更:"
for f in /etc/passwd /etc/shadow /etc/sudoers; do
    if [ -f "$f" ]; then
        echo "  $f: $(stat -c '%a %U %G %y' "$f")"
    fi
done
```

---

## 🧩 练习题

### Q1：删除正在写入的日志文件后空间未释放，怎么排查和解决？

<details>
<summary>点击查看答案</summary>

**排查**：
```bash
sudo lsof +L1 | grep access.log
# 输出显示进程 PID 和文件描述符 FD
```

**解决**（两种方法）：
```bash
# 方法 1：清空文件内容（推荐，不中断服务）
> /var/log/nginx/access.log

# 方法 2：如果文件已被 rm，通过 proc 释放
echo > /proc/<PID>/fd/<FD>

# 方法 3：发送 USR1 信号让 Nginx 重新打开日志
kill -USR1 $(cat /var/run/nginx.pid)
```
</details>

### Q2：logrotate 的 copytruncate 和 create 模式有什么区别？

<details>
<summary>点击查看答案</summary>

- **create**（默认）：重命名旧文件 → 创建新的空文件 → 通过 `postrotate` 通知应用重新打开文件。**无日志丢失**，但应用需支持 reload 信号。
- **copytruncate**：复制当前文件内容到 `.1` → 清空原文件。**不需要通知应用**，但复制和清空之间可能丢失日志，且复制大文件时占用额外磁盘空间。

**结论**：优先用 `create + postrotate`，只有不支持 reload 的应用才用 `copytruncate`。

</details>

### Q3：如何查看特定服务过去 2 小时的所有错误日志？

<details>
<summary>点击查看答案</summary>

```bash
# 方法 1：journalctl（推荐）
journalctl -u nginx --since "2 hours ago" -p err

# 方法 2：传统日志文件
grep -E "^\S+\s+\S+\s+\S+\s+nginx\[" /var/log/syslog | \
    grep -i error | tail -50

# 方法 3：Nginx 错误日志
tail -100 /var/log/nginx/error.log | grep -v "^\s*$"
```
</details>

---

## 📚 扩展阅读

- [systemd.journal-fields 手册](https://www.freedesktop.org/software/systemd/man/systemd.journal-fields.html) — journal 所有结构化字段
- [rsyslog 官方文档](https://www.rsyslog.com/doc/) — 配置语法和模块详解
- [logrotate 手册](https://linux.die.net/man/8/logrotate) — 所有配置选项

**最佳实践**：
- journald 启用**持久化存储**，否则重启后日志丢失
- 所有日志轮转使用 **create + postrotate**，避免 copytruncate
- 生产环境部署**远程日志服务器**，本地磁盘满了日志还在
- 日志文件权限设为 **640**，属主 root:adm，禁止普通用户读取
