# Day 28: Linux 基础与 Shell 脚本综合能力评估

> 📅 日期：2026-04-28
> 📖 学习主题：Linux 基础与 Shell 脚本综合能力评估
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 1-27 全部内容

---

## 🎯 学习目标

- 通过理论测试检验前三周的 Linux 和 Shell 知识掌握程度
- 通过 5 个实操场景评估综合运用能力
- 明确自身能力等级（入门/中级/高级 SRE）
- 制定下一步学习路线图

---

## 📖 综合知识回顾

### 1. Linux 核心知识速查表

| 领域 | 关键命令 | 核心概念 |
|------|---------|----------|
| 文件操作 | find, cp, mv, rm, touch, mkdir | 硬链接 vs 软链接、inode、FHS 标准 |
| 文本处理 | grep, sed, awk, sort, uniq, wc | 正则表达式、管道组合、流编辑 |
| 权限管理 | chmod, chown, chgrp, umask | 数字权限、特殊权限（SUID/SGID/Sticky） |
| 用户管理 | useradd, usermod, userdel, sudo | /etc/passwd、/etc/shadow、sudoers |
| 进程管理 | ps, top, kill, nice, nohup | 信号机制、进程状态、僵尸进程 |
| 系统监控 | uptime, free, df, vmstat, sar, iostat | 负载均衡、内存管理、I/O 分析 |
| 网络 | ss, netstat, curl, wget, ping, traceroute | TCP/IP、端口、DNS |
| 磁盘 | fdisk, mkfs, mount, lvm | 分区、文件系统、LVM 逻辑卷 |
| 日志 | journalctl, rsyslog, logrotate | syslog 协议、日志轮转 |
| 服务管理 | systemctl, unit 文件 | systemd 目标、依赖关系 |
| Shell 脚本 | bash, set, trap, 函数, 循环 | 变量作用域、错误处理、严格模式 |

### 2. Shell 脚本最佳实践清单

```bash
#!/usr/bin/env bash
# ===== 生产级脚本模板 =====
set -euo pipefail  # 严格模式
IFS=$'\n\t'

# 版本信息
readonly VERSION="1.0.0"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 依赖检查
check_deps() {
    local deps=(curl jq rsync)
    for dep in "${deps[@]}"; do
        command -v "$dep" &>/dev/null || {
            echo "错误: 缺少依赖 $dep" >&2
            exit 1
        }
    done
}

# 日志函数
log() {
    local level=$1; shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" >&2
}

# 错误处理
trap 'log ERROR "脚本异常退出，行号: $LINENO"' ERR
trap 'cleanup' EXIT

cleanup() {
    # 清理临时文件
    rm -f /tmp/myscript_$$.*
}

# 主函数
main() {
    check_deps
    log INFO "脚本启动"
    # ... 主逻辑 ...
    log INFO "脚本完成"
}

main "$@"
```

---

## 🧪 理论测试（20 道题）

每题 5 分，满分 100 分。建议时间：30 分钟。

### 第一部分：Linux 基础（10 题）

**Q1. 文件权限 `chmod 755 file` 设置的权限是什么？对应的符号表示是什么？**

<details>
<summary>查看答案</summary>

- 所有者：读+写+执行（rwx = 7）
- 同组用户：读+执行（r-x = 5）
- 其他用户：读+执行（r-x = 5）
- 符号表示：`chmod u=rwx,go=rx file`
</details>

**Q2. 硬链接和软链接（符号链接）有什么区别？**

<details>
<summary>查看答案</summary>

| 特性 | 硬链接 | 软链接 |
|------|--------|--------|
| 本质 | 指向同一 inode 的另一个目录项 | 独立文件，内容是目标路径 |
| 跨文件系统 | 不可以 | 可以 |
| 链接目录 | 不可以 | 可以 |
| 原文件删除 | 不影响（数据仍在） | 链接失效（悬空链接） |
| inode | 与原文件相同 | 不同 |
| 创建命令 | `ln file link` | `ln -s file link` |
</details>

**Q3. `ps aux` 和 `ps -ef` 有什么区别？输出中各列的含义是什么？**

<details>
<summary>查看答案</summary>

- `ps aux`：BSD 风格，显示所有用户的进程
  - USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
- `ps -ef`：System V 风格，显示所有进程
  - UID, PID, PPID, C, STIME, TTY, TIME, CMD

主要区别：`aux` 显示 %CPU 和 %MEM，`-ef` 显示 PPID（父进程 ID）。
</details>

**Q4. 解释 Linux 中的信号机制。SIGTERM (15) 和 SIGKILL (9) 有什么区别？**

<details>
<summary>查看答案</summary>

- **SIGTERM (15)**：请求进程终止，进程可以捕获并优雅退出（清理资源、关闭连接）
- **SIGKILL (9)**：强制终止进程，进程无法捕获或忽略，内核直接终止

关键区别：SIGTERM 允许优雅关闭，SIGKILL 是最后手段。SRE 中应该先 SIGTERM，等待超时后再 SIGKILL。

常用信号：
- SIGHUP (1)：终端挂起，常用于重新加载配置
- SIGINT (2)：Ctrl+C 中断
- SIGQUIT (3)：Ctrl+\ 退出并生成 core dump
- SIGUSR1/2 (10/12)：用户自定义信号
</details>

**Q5. `systemd` 中 `Type=simple`、`Type=forking`、`Type=oneshot` 有什么区别？**

<details>
<summary>查看答案</summary>

| Type | 含义 | 适用场景 |
|------|------|----------|
| simple | 主进程就是服务进程，systemd 认为启动立即完成 | 前台运行的程序（默认） |
| forking | 服务进程会 fork 后父进程退出，systemd 通过 PID 文件跟踪 | 传统守护进程（如 nginx） |
| oneshot | 执行一次就退出，可配合 RemainAfterExit=yes | 初始化任务、一次性脚本 |
| notify | 服务通过 sd_notify() 通知 systemd 就绪状态 | 支持 notify 协议的程序 |
| idle | 等待其他任务完成后才启动 | 控制台输出服务 |
</details>

**Q6. 如何查看系统中哪些进程打开了某个文件？**

<details>
<summary>查看答案</summary>

```bash
# 方法 1：lsof
lsof /var/log/syslog

# 方法 2：fuser
fuser -v /var/log/syslog

# 方法 3：查找特定进程打开的文件
lsof -p <PID>

# 方法 4：查找打开某端口的进程
lsof -i :80
ss -tlnp | grep :80
```
</details>

**Q7. 解释 `/etc/fstab` 中一行的含义：`/dev/sda1 / ext4 defaults 0 1`**

<details>
<summary>查看答案</summary>

| 字段 | 值 | 含义 |
|------|-----|------|
| 设备 | /dev/sda1 | 要挂载的设备 |
| 挂载点 | / | 挂载到的目录 |
| 文件系统 | ext4 | 文件系统类型 |
| 选项 | defaults | rw,suid,dev,exec,auto,nouser,async |
| dump | 0 | dump 备份频率（0=不备份） |
| fsck | 1 | 开机检查顺序（1=根文件系统，2=其他，0=不检查） |
</details>

**Q8. `nohup`、`screen`、`tmux` 的区别是什么？什么时候用哪个？**

<details>
<summary>查看答案</summary>

| 工具 | 特点 | 适用场景 |
|------|------|----------|
| nohup | 忽略 SIGHUP，输出重定向到 nohup.out | 简单的后台长时间任务 |
| screen | 终端复用，可分离/重连 | 需要交互的长任务 |
| tmux | 现代终端复用，功能更丰富 | 需要多窗口/面板的复杂场景 |

SRE 实践：
- 一次性后台任务：`nohup command &`
- 需要断开重连的运维操作：`tmux`
- 多人协作调试：`tmux` 多人共享会话
</details>

**Q9. 如何排查系统负载高的问题？给出完整的排查思路。**

<details>
<summary>查看答案</summary>

```bash
# 1. 查看负载概况
uptime                    # 1/5/15 分钟负载
cat /proc/loadavg         # 更详细的负载信息

# 2. 判断是 CPU、内存还是 I/O 瓶颈
vmstat 1 5                # 查看 r(运行队列)、b(阻塞)、wa(I/O等待)
top                       # 查看 %CPU、%MEM、%wa
iostat -x 1 5             # 查看磁盘 I/O

# 3. CPU 高：找到占用最高的进程
top -bn1 | head -20
ps aux --sort=-%cpu | head -10

# 4. 内存高：查看内存使用
free -h
ps aux --sort=-%mem | head -10
cat /proc/meminfo

# 5. I/O 高：找到 I/O 最多的进程
iotop -aoP
pidstat -d 1 5

# 6. 网络问题
ss -s                     # 连接统计
ss -tnp | wc -l           # 活跃连接数
```
</details>

**Q10. LVM 的基本概念是什么？如何创建一个 LVM 逻辑卷？**

<details>
<summary>查看答案</summary>

LVM（Logical Volume Manager）三层架构：
- **PV (Physical Volume)**：物理卷，实际的磁盘/分区
- **VG (Volume Group)**：卷组，由多个 PV 组成的存储池
- **LV (Logical Volume)**：逻辑卷，从 VG 中分配的逻辑分区

```bash
# 创建 LVM
pvcreate /dev/sdb /dev/sdc           # 创建物理卷
vgcreate my_vg /dev/sdb /dev/sdc     # 创建卷组
lvcreate -L 50G -n my_lv my_vg       # 创建逻辑卷
mkfs.ext4 /dev/my_vg/my_lv           # 格式化
mount /dev/my_vg/my_lv /data          # 挂载

# 扩容
lvextend -L +20G /dev/my_vg/my_lv   # 扩展逻辑卷
resize2fs /dev/my_vg/my_lv           # 扩展文件系统
```
</details>

### 第二部分：Shell 脚本（10 题）

**Q11. `set -euo pipefail` 每个选项的作用是什么？**

<details>
<summary>查看答案</summary>

- `set -e`：任何命令返回非零退出码时立即退出脚本
- `set -u`：使用未定义的变量时报错并退出（代替静默返回空字符串）
- `set -o pipefail`：管道中任意命令失败时，整个管道返回失败的退出码

```bash
# 没有 pipefail 时：
false | true | echo "ok"
echo $?  # 0（只看最后一个命令的退出码）

# 有 pipefail 时：
set -o pipefail
false | true | echo "ok"
echo $?  # 1（管道中 false 失败了）
```

注意：`set -e` 有一些例外情况（如 if 条件中的命令、|| 连接的命令等），需要特别注意。
</details>

**Q12. `"$@"` 和 `"$*"` 有什么区别？为什么推荐使用 `"$@"`？**

<details>
<summary>查看答案</summary>

```bash
# 假设调用: script.sh "hello world" "foo bar"

# "$*" — 所有参数作为一个字符串
# 结果: "hello world foo bar"（2 个参数变成了 1 个）

# "$@" — 每个参数独立保留
# 结果: "hello world" "foo bar"（仍然是 2 个参数）

# 引号非常重要！
$*  → hello world foo bar（4 个词）
$@  → hello world foo bar（4 个词）
"$*" → "hello world foo bar"（1 个词）
"$@" → "hello world" "foo bar"（2 个词）
```

推荐使用 `"$@"` 因为它能正确保留每个参数中的空格和特殊字符。
</details>

**Q13. 如何在 Bash 函数中返回字符串？**

<details>
<summary>查看答案</summary>

Bash 函数只能返回 0-255 的退出码。返回字符串的方法：

```bash
# 方法 1: 通过 echo + 命令替换（最常用）
get_hostname() {
    echo "$(hostname)"
}
result=$(get_hostname)

# 方法 2: 通过全局变量（nameref 方式）
get_info() {
    local -n _ref=$1
    _ref="some value"
}
get_info my_result
echo "$my_result"

# 方法 3: 通过全局变量（传统方式）
get_info() {
    RESULT="some value"
}
get_info
echo "$RESULT"
```
</details>

**Q14. `trap` 命令的作用是什么？有哪些常用场景？**

<details>
<summary>查看答案</summary>

`trap` 用于在接收到信号或脚本退出时执行指定的命令。

```bash
# 语法: trap 'command' SIGNAL

# 常用场景：

# 1. 清理临时文件
trap 'rm -f /tmp/myscript_*.$$' EXIT

# 2. 优雅关闭（处理 Ctrl+C）
trap 'echo "收到中断信号，正在清理..."; cleanup; exit 1' INT TERM

# 3. 忽略信号
trap '' HUP    # 忽略 SIGHUP（类似 nohup）

# 4. 错误处理
trap 'echo "错误发生在第 $LINENO 行"' ERR

# 5. 重新加载配置
trap 'reload_config' HUP

# 6. 调试
trap 'echo "DEBUG: 执行命令 $BASH_COMMAND"' DEBUG
```
</details>

**Q15. 解释 `IFS` 变量的作用。默认值是什么？为什么有时需要修改它？**

<details>
<summary>查看答案</summary>

`IFS`（Internal Field Separator）是 Bash 的内部字段分隔符，用于：
- 字符串分词
- `read` 命令分割输入
- `$*` 和 `${array[*]}` 的连接符

默认值：空格、制表符、换行符（`$' \t\n'`）

```bash
# 修改 IFS 解析 CSV
IFS=',' read -r name age city <<< "John,30,Beijing"

# 修改 IFS 处理带空格的文件名
IFS=$'\n'
for file in $(find /tmp -name "*.txt"); do
    echo "$file"
done

# 安全做法：临时修改
OLD_IFS=$IFS
IFS=','
# ... 处理 ...
IFS=$OLD_IFS

# 或者使用局部方式
while IFS=',' read -r col1 col2 col3; do
    echo "$col1 - $col2 - $col3"
done < data.csv
```
</details>

**Q16. 数组在 Bash 中如何使用？关联数组和索引数组有什么区别？**

<details>
<summary>查看答案</summary>

```bash
# 索引数组（Bash 默认）
arr=(apple banana cherry)
echo "${arr[0]}"      # apple
echo "${arr[@]}"      # apple banana cherry
echo "${#arr[@]}"     # 3（数组长度）
arr+=("date")         # 追加元素

# 关联数组（Bash 4.0+，需要 declare -A）
declare -A map
map[name]="Alice"
map[age]=30
echo "${map[name]}"   # Alice
echo "${!map[@]}"     # name age（所有键）
echo "${map[@]}"      # Alice 30（所有值）

# 遍历关联数组
for key in "${!map[@]}"; do
    echo "$key = ${map[$key]}"
done

# 注意：声明关联数组必须用 declare -A，否则会被当作索引数组
```
</details>

**Q17. `eval` 命令的作用是什么？为什么说它危险？**

<details>
<summary>查看答案</summary>

`eval` 将字符串作为 Bash 命令执行，会进行两次展开（变量替换 + 命令执行）。

```bash
# 用途：动态变量名
var_prefix="SERVER"
for i in 1 2 3; do
    eval "${var_prefix}_${i}=\"server${i}.example.com\""
done
echo "$SERVER_1"  # server1.example.com

# 危险：命令注入
user_input='"; rm -rf / #'
eval "echo $user_input"  # 执行了 rm -rf /！

# 更安全的替代方案：
# 1. 使用 nameref（Bash 4.3+）
declare -n ref="SERVER_1"
echo "$ref"

# 2. 使用关联数组
declare -A servers
servers[1]="server1.example.com"
echo "${servers[1]}"
```
</details>

**Q18. 如何实现一个带超时的命令执行？**

<details>
<summary>查看答案</summary>

```bash
# 方法 1: timeout 命令（推荐）
timeout 10 long_running_command
if [[ $? -eq 124 ]]; then
    echo "命令超时"
fi

# 方法 2: Bash 内置方式
run_with_timeout() {
    local timeout=$1; shift
    "$@" &
    local pid=$!

    ( sleep "$timeout" && kill "$pid" 2>/dev/null ) &
    local watchdog=$!

    wait "$pid"
    local exit_code=$?

    kill "$watchdog" 2>/dev/null
    wait "$watchdog" 2>/dev/null

    return $exit_code
}

# 方法 3: 超时 + 重试
retry_with_timeout() {
    local max_retries=$1
    local timeout=$2
    shift 2

    for ((i=1; i<=max_retries; i++)); do
        if timeout "$timeout" "$@"; then
            return 0
        fi
        echo "重试 $i/$max_retries..."
        sleep 2
    done
    return 1
}
```
</details>

**Q19. 解释 `here document` 和 `here string` 的区别和用法。**

<details>
<summary>查看答案</summary>

```bash
# Here Document (<<) — 多行文本输入
cat << EOF
Line 1
Line 2
$HOME 会被展开
EOF

cat << 'EOF'
$HOME 不会展开（引号包裹分隔符）
EOF

# Here String (<<<) — 单行文本输入
grep "root" <<< "$(cat /etc/passwd)"
read -r first last <<< "John Doe"

# 区别：
# Here Document: 多行，适合大段文本、配置文件生成
# Here String: 单行，适合简单的字符串传递
```
</details>

**Q20. 编写脚本时，如何处理包含空格的文件名？**

<details>
<summary>查看答案</summary>

```bash
# 错误：不加引号
for file in $(find /tmp -name "*.txt"); do
    cat $file  # 如果文件名有空格会出错
done

# 正确：加引号
for file in $(find /tmp -name "*.txt"); do
    cat "$file"
done

# 更安全：使用 while read + find -print0
find /tmp -name "*.txt" -print0 | while IFS= read -r -d '' file; do
    cat "$file"
done

# 使用 glob 替代 find（如果可以）
for file in /tmp/*.txt; do
    [[ -f "$file" ]] || continue
    cat "$file"
done
```
</details>

---

## 💻 实操测试（5 个场景）

每个场景建议时间 15-20 分钟。

### 场景 1：服务器快速初始化（10 分钟内完成）

**任务**：在一台全新的 Ubuntu/ Rocky Linux 服务器上完成以下操作：
1. 创建用户 `deploy`，配置 SSH 密钥登录
2. 安装 nginx
3. 编写 systemd 服务文件
4. 验证服务可访问

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# server_init.sh — 服务器快速初始化脚本
set -euo pipefail

# 检测发行版
if [[ -f /etc/debian_version ]]; then
    PKG_MGR="apt"
    PKG_UPDATE="apt update -y"
    PKG_INSTALL="apt install -y"
elif [[ -f /etc/redhat-release ]]; then
    PKG_MGR="yum"
    PKG_UPDATE="yum makecache"
    PKG_INSTALL="yum install -y"
else
    echo "不支持的发行版" >&2
    exit 1
fi

echo "=== 1. 创建用户 ==="
useradd -m -s /bin/bash deploy
mkdir -p /home/deploy/.ssh
ssh-keygen -t ed25519 -f /home/deploy/.ssh/id_ed25519 -N "" -q
cat /home/deploy/.ssh/id_ed25519.pub >> /home/deploy/.ssh/authorized_keys
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
echo "deploy ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/deploy
echo "用户 deploy 创建完成"

echo "=== 2. 安装 nginx ==="
$PKG_UPDATE
$PKG_INSTALL nginx
systemctl enable nginx
systemctl start nginx

echo "=== 3. 创建自定义服务 ==="
cat > /etc/systemd/system/myapp.service << 'EOF'
[Unit]
Description=My Application
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/start.sh
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /opt/myapp
cat > /opt/myapp/start.sh << 'EOF'
#!/bin/bash
while true; do
    echo "[$(date)] myapp is running"
    sleep 60
done
EOF
chmod +x /opt/myapp/start.sh
chown -R deploy:deploy /opt/myapp

systemctl daemon-reload
systemctl enable myapp
systemctl start myapp

echo "=== 4. 验证 ==="
systemctl status nginx --no-pager
systemctl status myapp --no-pager
curl -sf http://localhost/ > /dev/null && echo "nginx 访问正常" || echo "nginx 访问失败"

echo "=== 初始化完成 ==="
```
</details>

### 场景 2：Nginx 日志分析

**任务**：分析 Nginx 访问日志，输出：
1. Top 10 访问 IP
2. 5xx 错误率
3. 平均响应时间（如有 `$request_time` 字段）

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# nginx_log_analysis.sh — Nginx 日志分析
set -euo pipefail

LOG_FILE="${1:-/var/log/nginx/access.log}"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "日志文件不存在: $LOG_FILE" >&2
    exit 1
fi

echo "=============================="
echo " Nginx 日志分析报告"
echo " 日志: $LOG_FILE"
echo " 时间: $(date)"
echo "=============================="

total_requests=$(wc -l < "$LOG_FILE")
echo ""
echo "总请求数: $total_requests"

echo ""
echo "--- Top 10 访问 IP ---"
awk '{print $1}' "$LOG_FILE" | sort | uniq -c | sort -rn | head -10 | \
    awk '{printf "  %-16s %s 次\n", $2, $1}'

echo ""
echo "--- HTTP 状态码分布 ---"
awk '{print $9}' "$LOG_FILE" | sort | uniq -c | sort -rn | \
    awk '{printf "  %-6s %s 次\n", $2, $1}'

echo ""
echo "--- 5xx 错误率 ---"
count_5xx=$(awk '$9 ~ /^5/ {count++} END {print count+0}' "$LOG_FILE")
if (( total_requests > 0 )); then
    rate=$(awk "BEGIN {printf \"%.2f\", $count_5xx / $total_requests * 100}")
    echo "  5xx 错误数: $count_5xx"
    echo "  5xx 错误率: ${rate}%"
else
    echo "  无请求"
fi

echo ""
echo "--- Top 10 请求路径 ---"
awk '{print $7}' "$LOG_FILE" | sort | uniq -c | sort -rn | head -10 | \
    awk '{printf "  %-6s %s\n", $1, $2}'

echo ""
echo "--- Top 10 User-Agent ---"
awk -F'"' '{print $6}' "$LOG_FILE" | sort | uniq -c | sort -rn | head -10 | \
    awk '{printf "  %-6s %s\n", $1, substr($0, index($0,$2))}'

echo ""
echo "=============================="
```
</details>

### 场景 3：磁盘使用率监控告警脚本

**任务**：编写 Shell 脚本，检查所有挂载点的磁盘使用率，超过 90% 发送告警。

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# disk_monitor.sh — 磁盘使用率监控告警
set -euo pipefail

THRESHOLD=${1:-90}
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
LOG_FILE="/var/log/disk_monitor.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

send_alert() {
    local mount=$1
    local usage=$2
    local message="磁盘告警: $mount 使用率 ${usage}% 超过阈值 ${THRESHOLD}%"

    log "ALERT: $message"

    # Webhook 通知
    if [[ -n "$ALERT_WEBHOOK" ]]; then
        curl -s -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"$message\", \"host\": \"$(hostname)\"}" \
            >/dev/null 2>&1 || true
    fi
}

log "开始磁盘检查 (阈值: ${THRESHOLD}%)"

alert_count=0

# 检查所有挂载点
while IFS= read -r line; do
    # 跳过标题行
    [[ "$line" == Filesystem* ]] && continue

    mount_point=$(echo "$line" | awk '{print $NF}')
    usage_pct=$(echo "$line" | awk '{print $(NF-1)}' | tr -d '%')

    # 跳过非数字
    [[ "$usage_pct" =~ ^[0-9]+$ ]] || continue

    if (( usage_pct >= THRESHOLD )); then
        send_alert "$mount_point" "$usage_pct"
        ((alert_count++))
    else
        log "OK: $mount_point ${usage_pct}%"
    fi
done < <(df -h --output=source,size,used,avail,pcent,target 2>/dev/null || df -h)

if (( alert_count > 0 )); then
    log "共 $alert_count 个磁盘超过阈值"
    exit 1
else
    log "所有磁盘使用率正常"
    exit 0
fi
```
</details>

### 场景 4：跨发行版服务器初始化脚本

**任务**：编写一个同时支持 Ubuntu 和 Rocky Linux 的服务器初始化脚本。

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# server_setup.sh — 跨发行版服务器初始化
set -euo pipefail

# ===== 检测发行版 =====
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        # shellcheck source=/dev/null
        source /etc/os-release
        DISTRO_ID="$ID"
        DISTRO_VERSION="$VERSION_ID"
    elif [[ -f /etc/redhat-release ]]; then
        DISTRO_ID="rhel"
        DISTRO_VERSION=$(grep -oP '[0-9]+\.[0-9]+' /etc/redhat-release)
    else
        echo "无法检测发行版" >&2
        exit 1
    fi

    case "$DISTRO_ID" in
        ubuntu|debian)
            PKG_UPDATE="apt-get update -y"
            PKG_INSTALL="apt-get install -y"
            PKG_MANAGER="apt"
            ;;
        rocky|rhel|centos|fedora)
            PKG_UPDATE="yum makecache -y"
            PKG_INSTALL="yum install -y"
            PKG_MANAGER="yum"
            ;;
        *)
            echo "不支持的发行版: $DISTRO_ID" >&2
            exit 1
            ;;
    esac

    echo "检测到: $DISTRO_ID $DISTRO_VERSION (包管理器: $PKG_MANAGER)"
}

# ===== 基础配置 =====
setup_basics() {
    echo "=== 基础配置 ==="

    # 设置时区
    timedatectl set-timezone Asia/Shanghai

    # 设置主机名
    local hostname="${1:-$(hostname)}"
    hostnamectl set-hostname "$hostname"

    # 配置 sysctl
    cat > /etc/sysctl.d/99-custom.conf << 'EOF'
# 网络优化
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30

# 内存优化
vm.swappiness = 10
vm.overcommit_memory = 1

# 文件描述符
fs.file-max = 1000000
fs.inotify.max_user_watches = 524288
EOF
    sysctl --system

    # 配置 ulimit
    cat > /etc/security/limits.d/99-custom.conf << 'EOF'
* soft nofile 1000000
* hard nofile 1000000
* soft nproc 65535
* hard nproc 65535
EOF
}

# ===== 安装基础软件 =====
install_packages() {
    echo "=== 安装基础软件 ==="
    $PKG_UPDATE

    local packages=(
        curl wget vim htop tmux
        net-tools bind-utils
        tree jq
        git
        unzip
        cronie
        rsyslog
        logrotate
    )

    # 根据发行版添加特定包
    case "$DISTRO_ID" in
        ubuntu|debian)
            packages+=(apt-transport-https ca-certificates gnupg lsb-release)
            ;;
        rocky|rhel|centos)
            packages+=(epel-release yum-utils)
            ;;
    esac

    $PKG_INSTALL "${packages[@]}"
}

# ===== 安全配置 =====
setup_security() {
    echo "=== 安全配置 ==="

    # 配置 SSH
    if [[ -f /etc/ssh/sshd_config ]]; then
        sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
        sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
        sed -i 's/^#\?MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config

        case "$DISTRO_ID" in
            ubuntu|debian)
                systemctl restart ssh
                ;;
            rocky|rhel|centos)
                systemctl restart sshd
                ;;
        esac
    fi

    # 配置防火墙
    case "$DISTRO_ID" in
        ubuntu|debian)
            if command -v ufw &>/dev/null; then
                ufw default deny incoming
                ufw default allow outgoing
                ufw allow ssh
                ufw allow 80/tcp
                ufw allow 443/tcp
                ufw --force enable
            fi
            ;;
        rocky|rhel|centos)
            if command -v firewall-cmd &>/dev/null; then
                systemctl enable firewalld
                systemctl start firewalld
                firewall-cmd --permanent --add-service=ssh
                firewall-cmd --permanent --add-service=http
                firewall-cmd --permanent --add-service=https
                firewall-cmd --reload
            fi
            ;;
    esac
}

# ===== 配置日志 =====
setup_logging() {
    echo "=== 配置日志 ==="

    # 配置 logrotate
    cat > /etc/logrotate.d/custom << 'EOF'
/var/log/custom/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root root
}
EOF

    mkdir -p /var/log/custom
}

# ===== 主函数 =====
main() {
    echo "======================================"
    echo " 服务器初始化脚本"
    echo "======================================"

    detect_distro
    setup_basics
    install_packages
    setup_security
    setup_logging

    echo ""
    echo "======================================"
    echo " 初始化完成！"
    echo "======================================"
    echo "  发行版: $DISTRO_ID $DISTRO_VERSION"
    echo "  时区: $(timedatectl | grep 'Time zone' | awk '{print $3}')"
    echo "  SSH: 密钥认证已启用，密码登录已禁用"
    echo "======================================"
}

main "$@"
```
</details>

### 场景 5：日志监控告警脚本（支持多日志文件、告警去重）

**任务**：编写一个日志监控脚本，支持同时监控多个日志文件，检测异常模式，并实现告警去重（相同告警在 N 分钟内不重复发送）。

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# log_monitor.sh — 多日志文件监控 + 告警去重
set -euo pipefail

# ===== 配置 =====
LOG_FILES=(
    "/var/log/syslog"
    "/var/log/auth.log"
    "/var/log/nginx/error.log"
)

PATTERNS=(
    "ERROR"
    "CRITICAL"
    "FATAL"
    "Failed password"
    "Out of memory"
    "Disk full"
)

ALERT_COOLDOWN=300  # 告警冷却时间（秒），同一告警 5 分钟内不重复
STATE_DIR="/tmp/log_monitor_state"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
CHECK_INTERVAL=10   # 检查间隔（秒）

# ===== 初始化 =====
mkdir -p "$STATE_DIR"

# ===== 日志函数 =====
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# ===== 告警去重 =====
should_alert() {
    local alert_key=$1
    local state_file="$STATE_DIR/$alert_key"

    if [[ -f "$state_file" ]]; then
        local last_alert
        last_alert=$(cat "$state_file")
        local now
        now=$(date +%s)
        local elapsed=$(( now - last_alert ))

        if (( elapsed < ALERT_COOLDOWN )); then
            return 1  # 冷却中，不告警
        fi
    fi

    # 更新告警时间
    date +%s > "$state_file"
    return 0
}

# ===== 发送告警 =====
send_alert() {
    local log_file=$1
    local pattern=$2
    local line=$3

    # 生成告警 key（基于日志文件和模式）
    local alert_key
    alert_key=$(echo "${log_file}_${pattern}" | md5sum | cut -d' ' -f1)

    if ! should_alert "$alert_key"; then
        return 0  # 冷却中
    fi

    local message="[日志告警] $(hostname) - $log_file 匹配 $pattern"
    log "ALERT: $message"

    # 发送 Webhook 通知
    if [[ -n "$ALERT_WEBHOOK" ]]; then
        curl -s -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"$message\",
                \"host\": \"$(hostname)\",
                \"log_file\": \"$log_file\",
                \"pattern\": \"$pattern\",
                \"sample\": \"$(echo "$line" | head -c 200)\",
                \"time\": \"$(date -Iseconds)\"
            }" >/dev/null 2>&1 || true
    fi
}

# ===== 监控单个日志文件 =====
monitor_log() {
    local log_file=$1
    shift
    local patterns=("$@")

    if [[ ! -f "$log_file" ]]; then
        log "WARN: 日志文件不存在: $log_file"
        return 0
    fi

    # 构建 grep 模式
    local grep_pattern
    grep_pattern=$(IFS='|'; echo "${patterns[*]}")

    # 监控新日志行
    tail -n 0 -f "$log_file" | while IFS= read -r line; do
        for pattern in "${patterns[@]}"; do
            if echo "$line" | grep -qi "$pattern"; then
                send_alert "$log_file" "$pattern" "$line"
                break  # 一行只匹配一个模式
            fi
        done
    done
}

# ===== 清理过期状态 =====
cleanup_state() {
    local now
    now=$(date +%s)
    local max_age=$((ALERT_COOLDOWN * 2))

    for state_file in "$STATE_DIR"/*; do
        [[ -f "$state_file" ]] || continue
        local file_time
        file_time=$(cat "$state_file")
        local age=$(( now - file_time ))

        if (( age > max_age )); then
            rm -f "$state_file"
        fi
    done
}

# ===== 主函数 =====
main() {
    log "=============================="
    log " 日志监控启动"
    log " 监控文件: ${LOG_FILES[*]}"
    log " 匹配模式: ${PATTERNS[*]}"
    log " 告警冷却: ${ALERT_COOLDOWN}s"
    log "=============================="

    trap 'log "监控停止"; kill 0; exit 0' INT TERM

    # 为每个日志文件启动监控
    for log_file in "${LOG_FILES[@]}"; do
        if [[ -f "$log_file" ]]; then
            log "开始监控: $log_file"
            monitor_log "$log_file" "${PATTERNS[@]}" &
        else
            log "跳过不存在的文件: $log_file"
        fi
    done

    # 定期清理过期状态
    while true; do
        sleep "$CHECK_INTERVAL"
        cleanup_state
    done
}

main "$@"
```
</details>

---

## 📋 项目回顾检查清单

完成 Day 1-27 的学习后，用以下清单检验自己的掌握程度：

### 服务器初始化脚本

- [ ] 能否在全新的 Ubuntu 系统上一键完成初始化？
- [ ] 能否在全新的 Rocky Linux 系统上一键完成初始化？
- [ ] 是否包含安全配置（SSH 加固、防火墙、用户权限）？
- [ ] 是否支持自定义配置（主机名、时区、软件包列表）？
- [ ] 是否有幂等性（重复执行不出错）？

### 日志监控脚本

- [ ] 是否支持多个日志文件同时监控？
- [ ] 是否有告警去重机制（避免告警风暴）？
- [ ] 是否支持多种告警通知方式（Webhook、邮件）？
- [ ] 长时间运行是否稳定（无内存泄漏、无僵尸进程）？
- [ ] 是否有优雅退出机制（trap + cleanup）？

### 备份脚本

- [ ] 是否支持全量和增量备份？
- [ ] 是否有完整性校验（SHA256）？
- [ ] 是否有自动清理过期备份的机制？
- [ ] 是否支持远程同步？
- [ ] 恢复流程是否验证过（备份不测试等于没备份）？
- [ ] 是否有防重复执行机制（flock）？

---

## 📊 能力评估标准

### 入门级 SRE（Level 1）

**知识要求**：
- 掌握 Linux 基本命令（文件操作、权限、进程、网络）
- 能编写简单的 Shell 脚本（变量、条件、循环、函数）
- 理解 systemd 服务管理
- 了解日志查看和基本分析

**能力标志**：
- 能在指导下完成服务器初始化
- 能编写简单的自动化脚本
- 能使用已有脚本进行日常运维
- 能排查简单的服务故障

### 中级 SRE（Level 2）

**知识要求**：
- 深入理解 Linux 系统（内核参数、性能调优、安全加固）
- 熟练编写生产级 Shell 脚本（错误处理、日志、通知）
- 掌握监控和告警系统
- 了解网络协议和故障排查

**能力标志**：
- 能独立编写企业级运维脚本（备份、监控、部署）
- 能设计和实施监控告警体系
- 能进行系统性能分析和调优
- 能处理常见的生产故障
- 能编写跨平台（Ubuntu/CentOS）脚本

### 高级 SRE（Level 3）

**知识要求**：
- 精通 Linux 内核和系统编程
- 掌握容器化和编排技术（Docker、Kubernetes）
- 熟悉云原生架构和 IaC 工具
- 了解分布式系统设计和可靠性工程

**能力标志**：
- 能设计和实施 SRE 体系（SLO/SLI/SLA）
- 能进行容量规划和成本优化
- 能主导重大故障的排查和恢复
- 能推动自动化和工具链建设
- 能指导初中级 SRE 成长

---

## 🗺️ 下一步学习路线图

```
当前位置: Day 28 (Linux 基础与 Shell 脚本)
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
 网络基础         容器化          监控体系
 (Day 29-35)    (Day 56-70)     (Day 134-146)
    │               │               │
    │               │               │
    ▼               ▼               ▼
 TCP/IP          Docker         Prometheus
 DNS/HTTP        Kubernetes     Grafana
 负载均衡        Helm           Alertmanager
 VPN/代理        服务网格       ELK/Loki
    │               │               │
    └───────┬───────┘               │
            ▼                       │
      CI/CD 流水线                  │
      (Day 147-160)                │
            │                       │
            ▼                       │
      GitOps + IaC                 │
      (Day 120-132)                │
            │                       │
            └───────────┬───────────┘
                        ▼
                  SRE 实践
                  (Day 174-194)
                        │
                        ▼
                  ┌─────────────┐
                  │ SLO/SLI/SLA │
                  │ 事故管理    │
                  │ 混沌工程    │
                  │ 容量规划    │
                  │ 成本优化    │
                  └─────────────┘
```

### 推荐学习优先级

1. **网络基础**（Day 29-35）：TCP/IP、DNS、HTTP、负载均衡 -- SRE 的必备基础
2. **容器化**（Day 56-70）：Docker、Kubernetes -- 现代 SRE 的核心技能
3. **监控体系**（Day 134-146）：Prometheus、Grafana、ELK -- 可观测性三支柱
4. **CI/CD**（Day 147-160）：GitHub Actions、Jenkins、GitOps -- 自动化部署
5. **IaC**（Day 120-132）：Terraform、Ansible -- 基础设施即代码
6. **SRE 实践**（Day 174-194）：SLO、事故管理、混沌工程 -- SRE 核心方法论

### 推荐阅读

- 《Site Reliability Engineering》-- Google SRE 团队
- 《The Site Reliability Workbook》-- Google SRE 实践手册
- 《Unix and Linux System Administration Handbook》-- 系统管理圣经
- 《Bash Cookbook》-- Shell 脚本实战
- 《Networking for Systems Administrators》-- 网络基础

---

## ✅ 自检清单

- [ ] 理论测试得分 >= 80 分（20 道题中答对 16 道以上）
- [ ] 能在 10 分钟内完成服务器初始化场景
- [ ] 能独立编写 Nginx 日志分析脚本
- [ ] 能编写带告警的磁盘监控脚本
- [ ] 能编写跨发行版的初始化脚本
- [ ] 能实现带去重机制的日志监控脚本
- [ ] 理解自己的能力等级和下一步学习方向
- [ ] 项目回顾检查清单全部通过

---

*由 SRE 学习计划生成 | 2026-04-28*
