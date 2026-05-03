# Day 22: 脚本调试与信号处理 — set/trap/debug

> 📅 日期：2026-05-02
> 📖 学习主题：脚本调试与信号处理 — set/trap/debug
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 09 (进程控制与信号)、Day 19-21 (脚本编程)

---

## 🎯 学习目标

完成 Day 22 的学习后，你应该掌握：

- 理解 `set` 命令的各种选项及其作用
- 掌握 `set -euo pipefail` 安全模式的每个选项详解
- 熟练使用 `trap` 命令处理信号和进行资源清理
- 掌握脚本调试技巧（`set -x`、`PS4`、`shellcheck`）
- 能够编写具有生产级健壮性的 Bash 脚本

---

## 📖 核心知识点

### 1. set 命令选项详解

#### 1.1 安全模式三件套

```bash
set -euo pipefail
```

这是生产脚本的标准开头，每个选项都有重要作用：

| 选项 | 长名称 | 作用 |
|------|--------|------|
| `-e` | errexit | 命令失败时立即退出 |
| `-u` | nounset | 使用未定义变量时报错 |
| `-o pipefail` | pipefail | 管道中任一命令失败则整体失败 |

#### 1.2 `set -e`（errexit）详解

**原理**：当任何命令返回非零退出码时，立即终止脚本执行。

```bash
set -e

echo "第一行"
false           # 返回退出码 1
echo "这行不会执行"  # 永远不会输出
```

**关键陷阱**：`set -e` 并非对所有命令都生效。以下场景**不会触发退出**：

```bash
set -e

# 1. 在条件判断中的命令
if false; then echo "no"; fi          # 安全：false 在 if 中

# 2. 在 && 或 || 链中的命令
false || echo "backup plan"            # 安全：在 || 右侧
true && false || echo "caught"         # 安全

# 3. 管道中的命令（除非设置 pipefail）
false | true                           # 不触发退出！只看最后一条

# 4. 函数中，如果函数调用在条件中
my_func() { false; }
my_func || echo "handled"              # 不触发退出
```

**生产建议**：`set -e` 很好，但需要理解其边界情况。在关键步骤显式检查：

```bash
set -e

important_command
if [[ $? -ne 0 ]]; then
    echo "命令失败，执行回滚"
    rollback
    exit 1
fi
```

#### 1.3 `set -u`（nounset）详解

**原理**：使用未定义的变量时立即报错退出。

```bash
set -u

name="Alice"
echo "Hello $name"      # 正常
echo "Hello $age"       # 报错：unbound variable
```

**处理可选变量**：

```bash
set -u

# 使用默认值
echo "端口: ${PORT:-8080}"     # PORT 未定义时使用 8080
echo "端口: ${PORT:=8080}"     # 未定义时赋值 8080 给 PORT

# 检查变量是否定义
if [[ -z "${VAR+x}" ]]; then
    echo "VAR 未定义"
fi
```

**`${VAR+x}` vs `${VAR:-default}`**：
- `${VAR+x}`：如果 VAR 被定义（即使为空），返回 `x`；否则返回空
- `${VAR:-default}`：如果 VAR 未定义或为空，返回 `default`

#### 1.4 `set -o pipefail` 详解

**原理**：管道的退出码为最后一个非零的退出码（而非最后一条命令的退出码）。

```bash
# 没有 pipefail
false | true
echo $?    # 0 — 只看最后一条命令 true

# 有了 pipefail
set -o pipefail
false | true
echo $?    # 1 — 检测到管道中 false 的失败
```

**SRE 实战场景**：

```bash
set -euo pipefail

# 没有 pipefail 的危险情况
grep "ERROR" /var/log/syslog | head -5
# 如果日志中没有 ERROR，grep 返回 1，但 head 返回 0
# 没有 pipefail：脚本继续运行
# 有了 pipefail：脚本退出（配合 set -e）
```

#### 1.5 其他有用的 set 选项

| 选项 | 长名称 | 作用 |
|------|--------|------|
| `-x` | xtrace | 打印每条命令（调试用） |
| `-n` | noexec | 只读取命令不执行（语法检查） |
| `-C` | noclobber | 阻止重定向覆盖文件 |
| `-f` | noglob | 禁用通配符展开 |
| `-v` | verbose | 打印读取的每一行 |
| `-a` | allexport | 自动导出所有变量 |
| `-b` | notify | 后台任务完成时通知 |
| `-h` | hashall | 记住命令位置 |

```bash
# 语法检查（不执行）
bash -n script.sh

# 禁止覆盖文件
set -C
echo "hello" > existing_file.txt  # 报错
echo "hello" >| existing_file.txt  # 使用 >| 强制覆盖

# 调试模式
set -x
echo "debug mode"
ls /tmp
set +x
```

#### 1.6 标准安全模式模板

```bash
#!/bin/bash
#============================================================
# 生产脚本标准开头
#============================================================

set -euo pipefail

# 可选：IFS 设置（防止意外的字段分隔）
IFS=$'\n\t'

# 可选：更改 umask（新文件权限为 600）
umask 077

# 可选：设置调试前缀
export PS4='+${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:+${FUNCNAME[0]}():} '
```

---

### 2. trap 命令深入

#### 2.1 信号列表和用途

| 信号 | 编号 | 默认行为 | SRE 常见用途 |
|------|------|----------|-------------|
| SIGHUP | 1 | 终止 | 守护进程重新加载配置 |
| SIGINT | 2 | 终止 | Ctrl+C 中断 |
| SIGQUIT | 3 | 终止+core dump | 调试时强制退出 |
| SIGTERM | 15 | 终止 | 优雅关闭（systemd 默认） |
| SIGKILL | 9 | 强制终止 | **无法被 trap 捕获** |
| SIGUSR1 | 10 | 终止 | 自定义信号（如 nginx reload） |
| SIGUSR2 | 12 | 终止 | 自定义信号 |
| EXIT | — | — | 脚本退出时触发（伪信号） |
| ERR | — | — | 命令失败时触发（伪信号） |
| DEBUG | — | — | 每条命令执行前触发（伪信号） |
| RETURN | — | — | 函数或 source 返回时触发（伪信号） |

#### 2.2 trap 基本语法

```bash
trap '命令' 信号 [信号 ...]
trap 函数名 信号 [信号 ...]
trap - 信号     # 恢复默认行为
trap -p         # 显示当前所有 trap
trap            # 显示 EXIT trap
```

#### 2.3 EXIT 陷阱（清理临时文件）

```bash
#!/bin/bash
set -euo pipefail

# 创建临时文件
TMPDIR=$(mktemp -d /tmp/sre_task.XXXXXX)
TMPFILE="$TMPDIR/data.csv"

# 注册清理函数
cleanup() {
    echo "清理临时文件: $TMPDIR"
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

# 主逻辑
echo "正在处理数据..."
echo "a,b,c" > "$TMPFILE"
sleep 2
echo "处理完成"

# 无论正常退出还是 set -e 触发退出，cleanup 都会执行
```

**EXIT 陷阱的执行时机**：
- 脚本正常结束
- `set -e` 触发退出
- `exit` 命令
- 脚本执行到文件末尾
- 最后一个命令执行完成

#### 2.4 ERR 陷阱（错误处理）

```bash
#!/bin/bash
set -euo pipefail

# ERR trap 会在任何命令失败时触发
error_handler() {
    local exit_code=$?
    local line_number=$1
    echo "错误！命令退出码: $exit_code, 行号: $line_number"
    echo "调用栈: ${BASH_SOURCE[*]}"
    echo "函数调用: ${FUNCNAME[*]}"
}
trap 'error_handler ${LINENO}' ERR

# 测试
echo "正常行"
false    # 触发 ERR trap
echo "不会执行"
```

**ERR 陷阱的注意事项**：
- ERR 陷阱在 `set -e` 退出之前执行
- ERR 陷阱不会被子进程继承（除非使用 `set -o errtrace` 或 `set -E`）
- 管道中的命令失败不会触发 ERR（除非使用 `set -o pipefail`）

```bash
# 让 ERR 陷阱被子进程继承
set -o errtrace  # 或 set -E

trap 'echo "错误发生在子进程"' ERR

# 子 shell 中的错误也会被捕获
(
    false  # 触发 ERR trap
)
```

#### 2.5 INT/TERM 陷阱（优雅关闭）

```bash
#!/bin/bash
set -euo pipefail

RUNNING=true

graceful_shutdown() {
    echo "收到关闭信号，等待当前任务完成..."
    RUNNING=false
}

trap graceful_shutdown SIGTERM SIGINT

echo "服务启动中，PID=$$"
echo "按 Ctrl+C 或发送 SIGTERM 优雅关闭"

while $RUNNING; do
    echo "$(date '+%H:%M:%S') 处理中..."
    # 模拟长时间任务
    sleep 2 &
    wait $! 2>/dev/null || true
done

echo "服务已安全关闭"
```

**关键技巧**：`wait $!` 在收到信号时会返回非零退出码，使用 `|| true` 防止 `set -e` 导致脚本意外退出循环。

#### 2.6 DEBUG 陷阱（命令追踪）

```bash
#!/bin/bash

# 在每条命令执行前触发
trap 'echo "DEBUG: 即将执行 -> $BASH_COMMAND"' DEBUG

echo "第一行"
ls /tmp
echo "完成"

# 关闭 DEBUG trap
trap - DEBUG
```

**DEBUG 陷阱的高级用法**：

```bash
#!/bin/bash
# 带行号的调试输出
debug_trace() {
    echo "DEBUG [${BASH_LINENO[0]}]: $BASH_COMMAND"
}

trap debug_trace DEBUG

echo "Hello"
ls /tmp
echo "Done"

trap - DEBUG
```

#### 2.7 多个 trap 的组合

```bash
#!/bin/bash
set -euo pipefail

# 临时文件
TMPFILE=$(mktemp)

# 清理函数
cleanup() {
    rm -f "$TMPFILE"
    echo "清理完成"
}

# 错误处理函数
error_handler() {
    local exit_code=$?
    echo "错误: 退出码 $exit_code"
    # 可以在这里发送告警
}

# 优雅关闭函数
shutdown_handler() {
    echo "收到关闭信号"
    exit 130
}

# 注册多个 trap
trap cleanup EXIT
trap error_handler ERR
trap shutdown_handler SIGINT SIGTERM

# 主逻辑
echo "临时文件: $TMPFILE"
echo "数据" > "$TMPFILE"
sleep 10
```

---

### 3. 调试技巧

#### 3.1 `bash -x` 调试

```bash
# 方法 1：直接运行
bash -x script.sh

# 方法 2：只追踪特定部分
bash -x script.sh 2>debug.log

# 方法 3：部分追踪
set -x
# 需要调试的代码
set +x
```

**输出格式**：

```bash
set -x

name="Alice"
age=30
echo "Hello $name, age $age"
```

输出：
```
+ name=Alice
+ age=30
+ echo 'Hello Alice, age 30'
Hello Alice, age 30
```

#### 3.2 PS4 自定义调试前缀

默认的调试前缀是 `+`，可以通过 `PS4` 自定义：

```bash
# 设置详细的调试前缀
export PS4='+${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:+${FUNCNAME[0]}():} '

set -x
echo "debug"
```

输出：
```
+script.sh:5:: echo debug
```

**PS4 常用变量**：

| 变量 | 含义 |
|------|------|
| `${BASH_SOURCE}` | 当前脚本文件名 |
| `${LINENO}` | 当前行号 |
| `${FUNCNAME[0]}` | 当前函数名 |
| `${BASH_LINENO[0]}` | 调用者的行号 |

#### 3.3 条件调试

```bash
#!/bin/bash

# 仅在 DEBUG=1 时开启追踪
if [[ "${DEBUG:-0}" == "1" ]]; then
    set -x
fi

# 使用方式：
# ./script.sh              # 正常执行
# DEBUG=1 ./script.sh      # 开启调试追踪
```

**更灵活的调试级别**：

```bash
#!/bin/bash

DEBUG_LEVEL="${DEBUG:-0}"

debug() {
    local level=$1
    shift
    if [[ "$DEBUG_LEVEL" -ge "$level" ]]; then
        echo "DEBUG[$level]: $*" >&2
    fi
}

debug 1 "脚本开始"
debug 2 "详细信息"
debug 3 "非常详细的信息"
```

#### 3.4 选择性调试：将追踪输出重定向

```bash
#!/bin/bash

# 将 set -x 输出重定向到文件，不污染 stdout
exec 5>/tmp/debug_$$  # 打开文件描述符 5
BASH_XTRACEFD=5        # 设置 xtrace 输出到 FD 5
set -x

echo "正常输出到 stdout"
ls /tmp

set +x
exec 5>&-  # 关闭 FD 5
```

#### 3.5 shellcheck 静态分析

`shellcheck` 是 Shell 脚本的静态分析工具，可以发现潜在问题：

```bash
# 安装 shellcheck
# Ubuntu/Debian
sudo apt-get install shellcheck

# macOS
brew install shellcheck

# 使用
shellcheck script.sh

# 输出到文件
shellcheck script.sh > report.txt

# 只显示特定级别
shellcheck -S warning script.sh
```

**shellcheck 常见警告**：

```bash
# SC2086: 变量未加引号
echo $var          # 警告
echo "$var"        # 正确

# SC2046: 命令替换未加引号
rm $(find /tmp -name "*.log")      # 警告
rm "$(find /tmp -name "*.log")"    # 正确

# SC2034: 变量赋值但未使用
unused_var="hello"  # 警告

# SC2155: declare 和赋值分开
local var=$(command)    # 警告
local var
var=$(command)          # 正确
```

#### 3.6 bashdb 调试器

`bashdb` 是 Bash 的调试器，类似 GDB：

```bash
# 安装
sudo apt-get install bashdb

# 启动调试
bashdb script.sh

# 常用命令
# (bashdb) break 10        # 在第 10 行设置断点
# (bashdb) run              # 运行
# (bashdb) next             # 执行下一行
# (bashdb) step             # 进入函数
# (bashdb) print $var       # 打印变量
# (bashdb) continue         # 继续执行
# (bashdb) quit             # 退出
```

---

### 4. 错误处理模式

#### 4.1 错误处理函数

```bash
#!/bin/bash
set -euo pipefail

# 日志函数
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" >&2
}

# 错误处理函数
error_exit() {
    local exit_code="${1:-1}"
    shift
    log "ERROR" "$@"
    exit "$exit_code"
}

# 警告函数
warn() {
    log "WARN" "$@"
}

# 信息函数
info() {
    log "INFO" "$@"
}

# 使用
info "脚本开始"
warn "这是一个警告"
error_exit 1 "致命错误，退出"
```

#### 4.2 带调用栈的错误处理

```bash
#!/bin/bash
set -euo pipefail

# 打印调用栈
print_stack() {
    local i=0
    local stack_depth=${#FUNCNAME[@]}

    echo "调用栈:"
    for ((i = 1; i < stack_depth; i++)); do
        echo "  ${BASH_SOURCE[$i]}:${BASH_LINENO[$i-1]}:${FUNCNAME[$i]}()"
    done
}

# 错误处理函数
error_handler() {
    local exit_code=$?
    local line_number=$1

    echo "=========================================="
    echo "  错误: 退出码 $exit_code"
    echo "  位置: ${BASH_SOURCE[0]}:${line_number}"
    echo "=========================================="
    print_stack
    exit "$exit_code"
}

trap 'error_handler ${LINENO}' ERR

# 测试函数
function_a() {
    echo "在 function_a 中"
    function_b
}

function_b() {
    echo "在 function_b 中"
    false  # 触发错误
}

function_a
```

#### 4.3 日志记录

```bash
#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/myscript.log"
LOG_DIR=$(dirname "$LOG_FILE")

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 日志函数（同时输出到 stdout 和文件）
log() {
    local level="$1"
    shift
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"
    echo "$message" | tee -a "$LOG_FILE"
}

# 日志轮转
rotate_log() {
    local max_size=10485760  # 10MB
    local current_size

    if [[ -f "$LOG_FILE" ]]; then
        current_size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
        if [[ "$current_size" -gt "$max_size" ]]; then
            mv "$LOG_FILE" "${LOG_FILE}.$(date +%Y%m%d_%H%M%S)"
            gzip "${LOG_FILE}."*
            log "INFO" "日志已轮转"
        fi
    fi
}

# 使用
log "INFO" "脚本开始"
log "WARN" "这是一个警告"
log "ERROR" "这是一个错误"

# 定期检查日志轮转
rotate_log
```

#### 4.4 回滚机制

```bash
#!/bin/bash
set -euo pipefail

# 回滚操作列表
declare -a ROLLBACK_STACK=()

# 注册回滚操作
register_rollback() {
    ROLLBACK_STACK+=("$1")
}

# 执行回滚
execute_rollback() {
    local exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        echo "执行回滚..."

        # 逆序执行回滚操作
        for ((i = ${#ROLLBACK_STACK[@]} - 1; i >= 0; i--)); do
            echo "回滚: ${ROLLBACK_STACK[$i]}"
            eval "${ROLLBACK_STACK[$i]}" || true
        done
    fi
}

trap execute_rollback EXIT

# 使用示例
echo "步骤 1: 创建目录"
mkdir -p /tmp/test_dir
register_rollback "rm -rf /tmp/test_dir"

echo "步骤 2: 创建文件"
echo "data" > /tmp/test_dir/file.txt
register_rollback "rm -f /tmp/test_dir/file.txt"

echo "步骤 3: 修改配置"
cp /etc/hosts /etc/hosts.backup
register_rollback "mv /etc/hosts.backup /etc/hosts"

# 模拟错误
false
```

---

### 5. SRE 实战案例

#### 5.1 部署脚本的 trap 清理模式

```bash
#!/bin/bash
#============================================================
# 生产部署脚本（含完整错误处理与清理）
#============================================================

set -euo pipefail

APP_DIR="/opt/myapp"
BACKUP_DIR="/opt/myapp_backup_$(date +%Y%m%d_%H%M%S)"
DEPLOY_URL="https://releases.example.com/myapp-v2.0.tar.gz"
LOG_FILE="/var/log/myapp_deploy.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# 清理函数（无论成功失败都执行）
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log "部署失败！退出码: $exit_code"
        if [[ -d "$BACKUP_DIR" ]]; then
            log "尝试回滚..."
            rm -rf "$APP_DIR/current"
            cp -a "$BACKUP_DIR" "$APP_DIR/current"
            log "回滚完成"
        fi
    else
        log "部署成功"
        # 清理旧备份（保留最近 5 个）
        ls -td /opt/myapp_backup_* 2>/dev/null | tail -n +6 | xargs rm -rf
    fi
}
trap cleanup EXIT

# 优雅关闭处理
shutdown() {
    log "收到中断信号，清理中..."
    exit 130  # Ctrl+C 标准退出码
}
trap shutdown SIGINT SIGTERM

log "开始部署..."

# 1. 备份当前版本
log "创建备份: $BACKUP_DIR"
cp -a "$APP_DIR/current" "$BACKUP_DIR"

# 2. 下载新版本
log "下载: $DEPLOY_URL"
curl -fSL --connect-timeout 10 --max-time 300 \
    -o /tmp/myapp-new.tar.gz "$DEPLOY_URL"

# 3. 解压并部署
log "解压部署..."
tar xzf /tmp/myapp-new.tar.gz -C "$APP_DIR"
rm -f "$APP_DIR/current"
ln -s "$APP_DIR/myapp-v2.0" "$APP_DIR/current"

# 4. 健康检查
log "执行健康检查..."
sleep 2
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8080/health || echo "000")
if [[ "$HTTP_CODE" != "200" ]]; then
    log "健康检查失败！HTTP $HTTP_CODE"
    exit 1
fi

log "部署完成，健康检查通过"
```

#### 5.2 生产脚本的错误处理最佳实践

```bash
#!/bin/bash
#============================================================
# 生产脚本模板 - 包含所有最佳实践
#============================================================

# 1. 安全模式
set -euo pipefail
IFS=$'\n\t'
umask 077

# 2. 全局变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
LOG_FILE="/var/log/${SCRIPT_NAME%.sh}.log"
PID_FILE="/var/run/${SCRIPT_NAME%.sh}.pid"

# 3. 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 4. 日志函数
log() {
    local level="$1"
    shift
    local color
    case "$level" in
        ERROR) color="$RED" ;;
        WARN)  color="$YELLOW" ;;
        INFO)  color="$GREEN" ;;
        *)     color="$NC" ;;
    esac
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*${NC}" | tee -a "$LOG_FILE"
}

# 5. 错误处理
error_handler() {
    local exit_code=$?
    local line_number=$1
    log "ERROR" "脚本错误: 退出码=$exit_code, 行号=$line_number"
    log "ERROR" "调用栈: ${BASH_SOURCE[*]}"
    cleanup
    exit "$exit_code"
}

# 6. 清理函数
cleanup() {
    # 清理临时文件
    rm -f /tmp/${SCRIPT_NAME}.* 2>/dev/null
    # 清理 PID 文件
    rm -f "$PID_FILE" 2>/dev/null
    log "INFO" "清理完成"
}

# 7. 优雅关闭
shutdown_handler() {
    log "INFO" "收到关闭信号"
    cleanup
    exit 0
}

# 8. 注册 trap
trap error_handler ERR
trap cleanup EXIT
trap shutdown_handler SIGINT SIGTERM

# 9. 参数检查
check_args() {
    if [[ $# -lt 1 ]]; then
        echo "用法: $SCRIPT_NAME <参数>"
        exit 1
    fi
}

# 10. 依赖检查
check_dependencies() {
    local deps=("curl" "jq" "awk")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            log "ERROR" "缺少依赖: $dep"
            exit 1
        fi
    done
}

# 11. 锁机制
acquire_lock() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "ERROR" "脚本正在运行 (PID: $pid)"
            exit 1
        fi
    fi
    echo $$ > "$PID_FILE"
}

# 12. 主函数
main() {
    check_args "$@"
    check_dependencies
    acquire_lock

    log "INFO" "脚本开始执行"

    # 主逻辑
    # ...

    log "INFO" "脚本执行完成"
}

# 13. 执行主函数
main "$@"
```

#### 5.3 用 shellcheck 发现脚本中的潜在问题

```bash
#!/bin/bash
#============================================================
# 有问题的脚本示例
#============================================================

# 问题 1: 变量未加引号
file=$1
rm $file

# 问题 2: 命令替换未加引号
files=$(find /tmp -name "*.log")
rm $files

# 问题 3: 数组遍历时未加引号
arr=("file 1.txt" "file 2.txt")
for f in ${arr[@]}; do
    echo $f
done

# 问题 4: cd 后未检查返回值
cd /some/dir
rm *.txt

# 问题 5: 使用了未定义的变量
echo $undefined_var
```

**shellcheck 输出**：

```
In script.sh line 6:
rm $file
   ^--- SC2086: Double quote to prevent globbing and word splitting.

In script.sh line 10:
rm $files
   ^--- SC2086: Double quote to prevent globbing and word splitting.

In script.sh line 14:
for f in ${arr[@]}; do
         ^--- SC2068: Double quote array expansions to avoid re-splitting elements.

In script.sh line 18:
cd /some/dir
^--- SC2164: Use 'cd ... || exit' in case cd fails.

In script.sh line 22:
echo $undefined_var
     ^--- SC2154: undefined_var is referenced but not assigned.
```

**修复后的脚本**：

```bash
#!/bin/bash
set -euo pipefail

# 修复 1: 变量加引号
file="$1"
rm "$file"

# 修复 2: 命令替换加引号
files=$(find /tmp -name "*.log")
rm "$files"

# 修复 3: 数组遍历加引号
arr=("file 1.txt" "file 2.txt")
for f in "${arr[@]}"; do
    echo "$f"
done

# 修复 4: cd 后检查返回值
cd /some/dir || exit 1
rm *.txt

# 修复 5: 使用默认值
echo "${undefined_var:-默认值}"
```

---

## 💻 实战练习

### 练习 1：修复有缺陷的脚本

```bash
# 以下脚本有哪些问题？修复它
#!/bin/bash
files=$1
for f in $files; do
    cp $f /backup/
    echo "备份了 $f"
done
```

**参考答案**：

```bash
#!/bin/bash
set -euo pipefail

# 1. 缺少 set -euo pipefail
# 2. $files 应该加引号
# 3. 没有检查 /backup/ 目录是否存在
# 4. 缺少对 cp 失败的错误处理
# 5. 文件名含空格时会分词错误

backup_dir="/backup"
[[ -d "$backup_dir" ]] || { echo "备份目录不存在"; exit 1; }

for f in "${@}"; do
    if cp "$f" "$backup_dir/"; then
        echo "备份了 $f"
    else
        echo "备份失败: $f" >&2
    fi
done
```

### 练习 2：实现带超时的 trap 处理

```bash
# 编写脚本：trap SIGTERM，但如果 10 秒内没有完成清理，强制退出
```

**参考答案**：

```bash
#!/bin/bash
set -euo pipefail

CLEANUP_DONE=false

forced_exit() {
    echo "清理超时，强制退出"
    exit 1
}

graceful_shutdown() {
    echo "收到 SIGTERM，开始清理..."
    trap forced_exit SIGTERM  # 替换 trap，下次 SIGTERM 强制退出

    # 模拟耗时清理
    sleep 15
    CLEANUP_DONE=true
    echo "清理完成"
    exit 0
}

trap graceful_shutdown SIGTERM

while true; do
    sleep 1
done
```

### 练习 3：调试输出分析

```bash
# 设置 set -x 后，以下脚本的调试输出是什么？
set -x
name="World"
echo "Hello $name"
false || echo "recovered"
```

**参考答案**：

```
+ name=World
+ echo 'Hello World'
Hello World
+ false
+ echo recovered
recovered
```

`set -x` 显示每条命令的执行过程，`$name` 已被展开。注意 `||` 链中的 `false` 也会被追踪。

---

## 🎯 面试题精选

### 1. set -e 的陷阱有哪些？

**参考答案**：

`set -e` 的主要陷阱：

1. **条件判断中的命令**：`if false; then ...` 中的 `false` 不会触发退出
2. **`||` 和 `&&` 链**：`false || echo "ok"` 不会触发退出
3. **管道中的命令**：`false | true` 不会触发退出（除非设置了 `pipefail`）
4. **函数调用在条件中**：`my_func || echo "handled"` 不会触发退出
5. **子 shell**：子 shell 中的错误不会传播到父 shell
6. **某些命令的退出码**：有些命令返回非零退出码但不是真正的错误

**最佳实践**：
- 始终配合 `set -o pipefail` 使用
- 在关键步骤显式检查 `$?`
- 使用 `set -E` 让 ERR 陷阱被子进程继承

### 2. trap EXIT vs trap INT 有什么区别？

**参考答案**：

| 特性 | trap EXIT | trap INT |
|------|-----------|----------|
| 触发时机 | 脚本退出时（任何原因） | 收到 SIGINT 信号（Ctrl+C） |
| 执行次数 | 只执行一次 | 每次收到信号都执行 |
| 用途 | 清理临时文件、释放资源 | 优雅关闭、保存状态 |
| 可见性 | 无论正常退出还是错误退出 | 只在收到信号时 |

```bash
trap cleanup EXIT     # 脚本退出时清理
trap shutdown SIGINT  # Ctrl+C 时优雅关闭
trap reload SIGHUP    # 收到 HUP 时重载配置
```

### 3. 如何调试 Shell 脚本？

**参考答案**：

调试 Shell 脚本的方法：

1. **`set -x`**：打印每条命令
2. **`bash -x script.sh`**：外部调试
3. **`PS4`**：自定义调试前缀
4. **`shellcheck`**：静态分析
5. **`bashdb`**：交互式调试器
6. **`echo` 语句**：简单的调试输出
7. **日志记录**：记录到文件

```bash
# 条件调试
if [[ "${DEBUG:-0}" == "1" ]]; then
    set -x
fi

# 详细调试前缀
export PS4='+${BASH_SOURCE}:${LINENO}:${FUNCNAME[0]:+${FUNCNAME[0]}():} '

# 重定向调试输出到文件
exec 5>/tmp/debug.log
BASH_XTRACEFD=5
set -x
```

### 4. 如何在脚本中实现优雅关闭？

**参考答案**：

```bash
#!/bin/bash
set -euo pipefail

RUNNING=true

cleanup() {
    echo "清理资源..."
    # 关闭连接、释放锁、保存状态
    rm -f /var/run/myscript.pid
}

graceful_shutdown() {
    echo "收到关闭信号，等待当前任务完成..."
    RUNNING=false
}

trap cleanup EXIT
trap graceful_shutdown SIGINT SIGTERM

echo $$ > /var/run/myscript.pid

while $RUNNING; do
    # 执行任务
    do_work

    # 使用 sleep & wait 模式，使 sleep 可被信号中断
    sleep 60 &
    wait $! 2>/dev/null || true
done

echo "服务已安全关闭"
```

### 5. `set -euo pipefail` 每个选项的作用是什么？

**参考答案**：

- **`set -e` (errexit)**：命令返回非零退出码时，立即终止脚本
- **`set -u` (nounset)**：使用未定义的变量时报错退出
- **`set -o pipefail`**：管道中任一命令返回非零，则整个管道返回非零

```bash
# 没有这些选项
false | true    # 退出码 0
echo $undefined # 空
false           # 继续执行

# 有了这些选项
set -euo pipefail
false | true    # 退出码 1（pipefail）
echo $undefined # 报错退出（-u）
false           # 报错退出（-e）
```

### 6. 如何在脚本中实现资源锁？

**参考答案**：

```bash
#!/bin/bash
set -euo pipefail

LOCK_FILE="/var/run/myscript.lock"

acquire_lock() {
    # 使用 flock 获取文件锁
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        echo "脚本正在运行"
        exit 1
    fi
    echo $$ > "$LOCK_FILE"
}

release_lock() {
    flock -u 200
    rm -f "$LOCK_FILE"
}

trap release_lock EXIT

acquire_lock
echo "获取锁成功"

# 主逻辑
sleep 10

release_lock
```

### 7. ERR 陷阱和 set -e 有什么关系？

**参考答案**：

- ERR 陷阱在命令失败时触发，但**早于** `set -e` 的退出
- 如果 ERR 陷阱执行了 `exit`，则 `set -e` 不会再触发
- ERR 陷阱默认不会被子进程继承，需要 `set -E` 或 `set -o errtrace`

```bash
set -e

trap 'echo "ERR triggered"' ERR

false    # ERR 陷阱触发，然后 set -e 退出
echo "不会执行"
```

### 8. 如何在 Bash 脚本中实现日志轮转？

**参考答案**：

```bash
#!/bin/bash

LOG_FILE="/var/log/myscript.log"
MAX_SIZE=10485760  # 10MB
MAX_FILES=5

rotate_log() {
    if [[ ! -f "$LOG_FILE" ]]; then
        return
    fi

    local size
    size=$(stat -c%s "$LOG_FILE" 2>/dev/null || stat -f%z "$LOG_FILE" 2>/dev/null)

    if [[ "$size" -gt "$MAX_SIZE" ]]; then
        # 轮转日志文件
        for ((i = MAX_FILES - 1; i >= 1; i--)); do
            [[ -f "${LOG_FILE}.${i}.gz" ]] && mv "${LOG_FILE}.${i}.gz" "${LOG_FILE}.$((i + 1)).gz"
        done
        mv "$LOG_FILE" "${LOG_FILE}.1"
        gzip "${LOG_FILE}.1"

        # 删除旧日志
        rm -f "${LOG_FILE}.$((MAX_FILES + 1)).gz"
    fi
}

# 定期检查
while true; do
    rotate_log
    sleep 3600
done
```

---

## 📚 深入阅读

### 官方文档
- [Bash Manual - The Set Builtin](https://www.gnu.org/software/bash/manual/bash.html#The-Set-Builtin)
- [Bash Manual - Trap Builtin](https://www.gnu.org/software/bash/manual/bash.html#Trap-Builtin)
- [man 7 signal](https://man7.org/linux/man-pages/man7/signal.7.html)

### 推荐书籍
- 《Bash Cookbook》- Carl Albing, JP Vossen
- 《Shell Scripting: Expert Recipes for Linux, Bash, and More》- Steve Parker

### 在线资源
- [David Pashley: Writing Robust Bash Shell Scripts](http://www.davidpashley.com/articles/writing-robust-shell-scripts/)
- [Greg's Wiki: Bash Pitfalls](http://mywiki.wooledge.org/BashPitfalls)
- [BashFAQ/105: Why doesn't set -e catch errors in pipelines?](http://mywiki.wooledge.org/BashFAQ/105)
- [ShellCheck](https://www.shellcheck.net/)

### set 选项速查表

| 选项 | 简写 | 效果 |
|------|------|------|
| errexit | `-e` | 命令失败时退出 |
| nounset | `-u` | 未定义变量报错 |
| pipefail | `-o pipefail` | 管道中任一命令失败则退出 |
| xtrace | `-x` | 打印每行命令（调试） |
| nounset+errexit | `-eu` | 常用组合 |
| 全部安全模式 | `-euo pipefail` | 生产脚本推荐 |

---

## ✅ 自检清单

### 理论检查点
- [ ] 理解 `set -e` 的工作机制和陷阱
- [ ] 理解 `set -u` 如何防止未定义变量
- [ ] 理解 `set -o pipefail` 的作用
- [ ] 理解各种信号的用途（SIGINT、SIGTERM、SIGHUP）
- [ ] 知道 EXIT、ERR、DEBUG 陷阱的区别
- [ ] 理解 shellcheck 的常见警告

### 实操检查点
- [ ] 能够编写带 `set -euo pipefail` 的安全脚本
- [ ] 能够使用 trap 进行资源清理
- [ ] 能够使用 trap 实现优雅关闭
- [ ] 能够使用 `set -x` 和 PS4 进行调试
- [ ] 能够使用 shellcheck 分析脚本
- [ ] 能够实现完整的错误处理模式
- [ ] 能够编写生产级的部署脚本

---

> 📝 **学习笔记**
>
> 记录你在学习过程中的心得和疑问：
>
> 1. ________________________________________________
> 2. ________________________________________________
> 3. ________________________________________________
