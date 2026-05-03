# Day 18: Shell 函数 — 函数定义、参数传递、返回值、作用域

> 📅 日期：2026-04-29
> 📖 学习主题：Shell 函数 — 函数定义、参数传递、返回值、作用域
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 17（Shell 循环结构 — for/while/until）

## 🎯 学习目标

完成 Day 18 的学习后，你应该能够：
- 掌握函数定义的两种语法及区别
- 熟练使用函数参数（$1-$9、${10}、$@、$#、shift）
- 理解 Shell 函数的返回值机制（return vs echo）
- 掌握 local 关键字和变量作用域
- 能编写函数库并通过 source 引入
- 理解递归函数和 fork 炸弹
- 能编写生产级的日志函数库、错误处理函数库和服务管理函数

---

## 📖 核心知识点

### 1. 函数定义语法

#### 1.1 两种定义方式

```bash
# 方式 1：POSIX 格式（推荐，兼容性最好）
function_name() {
    commands
}

# 方式 2：function 关键字（Bash 扩展）
function function_name {
    commands
}

# 方式 3：function 关键字 + 括号（冗余但合法）
function function_name() {
    commands
}
```

```bash
# 三种方式的区别

# 方式 1：POSIX 格式
greet() {
    echo "Hello, $1"
}

# 方式 2：function 关键字
function greet {
    echo "Hello, $1"
}

# 方式 3：两者结合
function greet() {
    echo "Hello, $1"
}

# 关键区别：
# 1. POSIX 格式在所有 Shell 中都能工作
# 2. function 关键字只能在 bash/zsh/ksh 中使用
# 3. function 关键字可以省略括号
# 4. 在 POSIX 模式下（set -o posix），function 关键字不可用

# 推荐：使用 POSIX 格式（方式 1）
# 原因：兼容性最好，即使在 sh (dash) 中也能工作
```

#### 1.2 函数定义的位置

```bash
#!/usr/bin/env bash
# 函数必须在调用之前定义

# ❌ 错误：函数在调用之后定义
main
main() {
    echo "Hello"
}
# 输出：main: command not found

# ✅ 正确：函数在调用之前定义
main() {
    echo "Hello"
}
main

# 常见模式：先定义所有函数，最后调用 main
#!/usr/bin/env bash

# 函数定义
log() { ... }
check_deps() { ... }
deploy() { ... }

# 主函数
main() {
    log "Starting deployment"
    check_deps
    deploy
}

# 执行
main "$@"
```

#### 1.3 函数的元信息

```bash
# 查看函数定义
declare -f greet
# 输出：
# greet ()
# {
#     echo "Hello, $1"
# }

# 查看所有已定义的函数
declare -F

# 查看函数是否存在
declare -F greet &>/dev/null && echo "greet 存在" || echo "greet 不存在"

# 删除函数
unset -f greet

# 函数的属性
declare -f -F greet    # 只显示函数名，不显示定义
```

---

### 2. 参数传递

#### 2.1 位置参数

```bash
# 函数的参数通过 $1, $2, $3... 访问
# 与脚本的参数机制相同

greet() {
    echo "Hello, $1!"
    echo "You are $2 years old."
}

greet "Alice" 30
# 输出：
# Hello, Alice!
# You are 30 years old.

# 超过 9 个参数，必须用大括号
many_args() {
    echo "Arg 1: $1"
    echo "Arg 9: $9"
    echo "Arg 10: ${10}"    # 必须用大括号
    echo "Arg 11: ${11}"
}

many_args a b c d e f g h i j k
```

#### 2.2 参数数量和所有参数

```bash
# $# — 参数个数
# $@ — 所有参数（独立字符串）
# $* — 所有参数（一个字符串）

show_args() {
    echo "参数个数: $#"
    echo "所有参数(\$@): $@"
    echo "所有参数(\$*): $*"
    echo ""
    echo "遍历 \$@:"
    for arg in "$@"; do
        echo "  [$arg]"
    done
    echo ""
    echo "遍历 \$*:"
    for arg in "$*"; do
        echo "  [$arg]"
    done
}

show_args "hello world" "foo bar" "baz"
# 输出：
# 参数个数: 3
# 所有参数($@): hello world foo bar baz
# 所有参数($*): hello world foo bar baz
#
# 遍历 $@:
#   [hello world]
#   [foo bar]
#   [baz]
#
# 遍历 $*:
#   [hello world foo bar baz]

# 最佳实践：遍历参数时始终使用 "$@"
process_files() {
    for file in "$@"; do
        echo "Processing: $file"
    done
}
```

#### 2.3 shift 命令

```bash
# shift — 向左移动参数

process_options() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose)
                verbose=true
                shift
                ;;
            -o|--output)
                output="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                return 0
                ;;
            --)
                shift
                break
                ;;
            -*)
                echo "Unknown option: $1" >&2
                return 1
                ;;
            *)
                break
                ;;
        esac
    done

    # 剩余的参数
    echo "Remaining args: $@"
}

# 使用
process_options -v -o output.txt file1.txt file2.txt
```

#### 2.4 参数传递的最佳实践

```bash
# 1. 始终用 "$@" 传递参数
wrapper_function() {
    actual_function "$@"    # ✅ 保持参数原样
}

# ❌ 错误
wrapper_function() {
    actual_function $*    # 会分词！
}

# 2. 验证必需参数
deploy() {
    local target="${1:?Usage: deploy <target>}"
    local version="${2:?Usage: deploy <target> <version>}"

    echo "Deploying $version to $target"
}

# 3. 使用默认值
greet() {
    local name="${1:-World}"
    echo "Hello, $name!"
}

# 4. 参数数量检查
backup() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: backup <source> [destination]" >&2
        return 1
    fi

    local source="$1"
    local dest="${2:-/backup}"

    echo "Backing up $source to $dest"
}
```

---

### 3. 返回值机制

#### 3.1 return 语句

```bash
# return 只能返回 0-255 的整数
# 0 表示成功，非 0 表示失败
# 这与命令的退出码相同

is_even() {
    if (( $1 % 2 == 0 )); then
        return 0    # 成功（真）
    else
        return 1    # 失败（假）
    fi
}

# 使用
if is_even 42; then
    echo "42 是偶数"
fi

# 获取返回值
is_even 42
echo "返回值: $?"    # 0

is_even 43
echo "返回值: $?"    # 1

# 注意：return 只能返回 0-255
# 如果返回值大于 255，会取模
big_number() {
    return 300
}
big_number
echo "返回值: $?"    # 44 (300 % 256)
```

#### 3.2 echo 输出（返回数据）

```bash
# 使用 echo 输出函数结果，通过命令替换捕获

get_hostname() {
    echo "$(hostname)"
}

# 捕获输出
result=$(get_hostname)
echo "Hostname: $result"

# 多行输出
get_system_info() {
    echo "Hostname: $(hostname)"
    echo "OS: $(uname -s)"
    echo "Kernel: $(uname -r)"
}

# 捕获多行输出
info=$(get_system_info)
echo "$info"

# 逐行处理
while IFS= read -r line; do
    echo "Line: $line"
done <<< "$(get_system_info)"

# 注意：echo 会删除尾部的换行符
get_lines() {
    echo "line1"
    echo "line2"
    echo "line3"
}

result=$(get_lines)
echo "Result: [$result]"
# 输出：Result: [line1
# line2
# line3]
```

#### 3.3 return vs echo 对比

```bash
# 场景 1：检查函数（返回成功/失败）→ 使用 return
is_root() {
    [[ $(id -u) -eq 0 ]]
}

if is_root; then
    echo "是 root"
fi

# 场景 2：数据获取函数 → 使用 echo
get_ip() {
    hostname -I | awk '{print $1}'
}

ip=$(get_ip)
echo "IP: $ip"

# 场景 3：混合使用
check_and_get() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        echo "ERROR: 文件不存在" >&2    # 错误信息输出到 stderr
        return 1
    fi

    echo "$(cat "$file")"    # 正常数据输出到 stdout
    return 0
}

# 使用
if content=$(check_and_get "/etc/hostname"); then
    echo "内容: $content"
else
    echo "获取失败"
fi
```

#### 3.4 全局变量方式

```bash
# 通过全局变量返回复杂数据

declare -A RESULT    # 关联数组

get_user_info() {
    local username="$1"

    if ! id "$username" &>/dev/null; then
        return 1
    fi

    RESULT[name]=$(getent passwd "$username" | cut -d: -f5)
    RESULT[uid]=$(id -u "$username")
    RESULT[gid]=$(id -g "$username")
    RESULT[home]=$(getent passwd "$username" | cut -d: -f6)
    RESULT[shell]=$(getent passwd "$username" | cut -d: -f7)

    return 0
}

# 使用
if get_user_info "root"; then
    echo "Name: ${RESULT[name]}"
    echo "UID: ${RESULT[uid]}"
    echo "Home: ${RESULT[home]}"
fi

# 另一种方式：使用 nameref（Bash 4.3+）
get_user_info_nameref() {
    local -n result_ref=$1    # nameref
    local username="$2"

    result_ref[name]=$(getent passwd "$username" | cut -d: -f5)
    result_ref[uid]=$(id -u "$username")
}

declare -A user_info
get_user_info_nameref user_info "root"
echo "Name: ${user_info[name]}"
```

---

### 4. 变量作用域

#### 4.1 全局变量 vs 局部变量

```bash
# 默认情况下，Shell 函数中的变量是全局的

global_var="I am global"

modify_vars() {
    global_var="Modified"
    new_var="Created in function"
}

modify_vars
echo "$global_var"    # Modified
echo "$new_var"       # Created in function

# 这可能导致意外的副作用！
```

#### 4.2 local 关键字

```bash
# local 关键字声明局部变量
# 局部变量只在函数内部可见

global_var="I am global"

my_function() {
    local local_var="I am local"
    global_var="Modified"

    echo "In function: $local_var"
    echo "In function: $global_var"
}

my_function
echo "Outside: $global_var"    # Modified
echo "Outside: ${local_var:-未定义}"    # 未定义

# local 的作用域是"动态"的
# 嵌套函数可以访问外层函数的局部变量

outer() {
    local outer_var="outer"

    inner() {
        echo "inner sees: $outer_var"
    }

    inner
}

outer    # 输出：inner sees: outer
```

#### 4.3 local 的陷阱

```bash
# 陷阱 1：local 会影响 $? 的值

my_function() {
    false
    local x=$?    # 这里 $? 是 local 命令的退出码（0），不是 false 的退出码！
    echo "x = $x" # 输出：x = 0
}

# 修复方案
my_function_fixed() {
    local x
    x=$?    # 先获取 $?，再赋值给 local 变量
    echo "x = $x" # 输出：x = 1
}

# 陷阱 2：local -a 数组（Bash 3.1 之前的 bug）

my_function() {
    local -a arr=("$@")    # 在某些 Bash 版本中可能有问题
    echo "${arr[0]}"
}

# 陷阱 3：local 变量在子 Shell 中不可见

my_function() {
    local x=42
    echo "In function: $x"

    # 子 Shell
    (echo "In subshell: $x")    # 可以访问（继承了环境）
}

# 但管道中的子 Shell 不能修改父 Shell 的 local 变量
my_function() {
    local count=0
    echo -e "a\nb\nc" | while read line; do
        (( count++ ))    # 不会影响函数的 count
    done
    echo "count = $count"    # 0
}
```

#### 4.4 最佳实践

```bash
# 始终使用 local 声明函数内部变量

calculate() {
    local num1="$1"
    local num2="$2"
    local sum=$((num1 + num2))
    local product=$((num1 * num2))

    echo "Sum: $sum"
    echo "Product: $product"
}

# 避免使用全局变量
# 如果需要返回多个值，使用关联数组或 nameref

# 使用 readonly 防止意外修改
init_config() {
    readonly CONFIG_FILE="/etc/myapp/config.yaml"
    readonly LOG_DIR="/var/log/myapp"
}

# 清理函数（使用 trap）
cleanup() {
    rm -f "$TEMP_FILE"
    echo "Cleanup done"
}

main() {
    local TEMP_FILE=$(mktemp)
    trap cleanup EXIT

    # ... 主逻辑 ...
}
```

---

### 5. 函数库模式

#### 5.1 创建函数库

```bash
# 函数库就是一个包含函数定义的 Shell 文件
# 通常以 .sh 结尾

# /usr/local/lib/sre_utils.sh
#!/usr/bin/env bash
# SRE 工具函数库

# 日志函数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WARN] $*" >&2
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2
}

# 检查命令是否存在
require_command() {
    local cmd="$1"
    if ! command -v "$cmd" &>/dev/null; then
        log_error "Required command not found: $cmd"
        return 1
    fi
}

# 检查是否为 root
require_root() {
    if [[ $(id -u) -ne 0 ]]; then
        log_error "This script must be run as root"
        return 1
    fi
}

# 确保目录存在
ensure_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    fi
}
```

#### 5.2 引入函数库

```bash
# 方法 1：source（推荐）
source /usr/local/lib/sre_utils.sh
# 或简写
. /usr/local/lib/sre_utils.sh

# 方法 2：通过环境变量指定库路径
SRE_LIB="${SRE_LIB:-/usr/local/lib/sre_utils.sh}"
if [[ ! -f "$SRE_LIB" ]]; then
    echo "ERROR: SRE library not found: $SRE_LIB" >&2
    exit 1
fi
source "$SRE_LIB"

# 方法 3：自动查找库文件
find_library() {
    local lib_name="$1"
    local search_paths=(
        "$(dirname "${BASH_SOURCE[0]}")/lib"
        "$(dirname "${BASH_SOURCE[0]}")/../lib"
        "/usr/local/lib"
        "$HOME/.local/lib"
    )

    for path in "${search_paths[@]}"; do
        if [[ -f "$path/$lib_name" ]]; then
            echo "$path/$lib_name"
            return 0
        fi
    done

    return 1
}

LIB_PATH=$(find_library "sre_utils.sh")
if [[ -n "$LIB_PATH" ]]; then
    source "$LIB_PATH"
else
    echo "ERROR: Cannot find sre_utils.sh" >&2
    exit 1
fi
```

#### 5.3 防止重复加载

```bash
# 使用守卫变量防止重复加载

# /usr/local/lib/sre_utils.sh
[[ "${_SRE_UTILS_LOADED:-}" == "true" ]] && return 0
_SRE_UTILS_LOADED=true

# 函数定义...
log_info() { ... }
log_warn() { ... }
log_error() { ... }
```

#### 5.4 模块化架构

```bash
# 推荐的项目结构
# /opt/myapp/
# ├── bin/
# │   └── myapp.sh          # 主脚本
# ├── lib/
# │   ├── common.sh         # 通用函数
# │   ├── logging.sh        # 日志函数
# │   ├── network.sh        # 网络函数
# │   └── config.sh         # 配置函数
# └── etc/
#     └── config.yaml       # 配置文件

# bin/myapp.sh
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${SCRIPT_DIR}/../lib"
CONFIG_DIR="${SCRIPT_DIR}/../etc"

# 加载库
source "${LIB_DIR}/common.sh"
source "${LIB_DIR}/logging.sh"
source "${LIB_DIR}/network.sh"
source "${LIB_DIR}/config.sh"

# 主函数
main() {
    log_info "Starting application..."

    load_config "${CONFIG_DIR}/config.yaml"
    check_network
    # ... 主逻辑 ...
}

main "$@"
```

---

### 6. 递归函数

#### 6.1 基本递归

```bash
# 阶乘
factorial() {
    local n="$1"
    if (( n <= 1 )); then
        echo 1
    else
        local prev=$(factorial $((n - 1)))
        echo $((n * prev))
    fi
}

result=$(factorial 5)
echo "5! = $result"    # 120

# 斐波那契
fibonacci() {
    local n="$1"
    if (( n <= 1 )); then
        echo "$n"
    else
        local a=$(fibonacci $((n - 1)))
        local b=$(fibonacci $((n - 2)))
        echo $((a + b))
    fi
}

# 目录大小递归计算
dir_size() {
    local dir="$1"
    local size=0

    for item in "$dir"/*; do
        if [[ -f "$item" ]]; then
            size=$((size + $(stat -c %s "$item")))
        elif [[ -d "$item" ]]; then
            size=$((size + $(dir_size "$item")))
        fi
    done

    echo "$size"
}
```

#### 6.2 Fork 炸弹

```bash
# ⚠️ 警告：不要在生产系统上运行！

# Fork 炸弹的原理
:(){ :|:& };:

# 解析：
# :()     — 定义函数名为 :
# { :|:& } — 函数体：调用自己两次（:|:），并放到后台（&）
# ;       — 函数定义结束
# :       — 调用函数

# 等价于：
fork_bomb() {
    fork_bomb | fork_bomb &
}
fork_bomb

# 为什么危险？
# 每次调用创建 2 个子进程
# 进程数指数级增长：1, 2, 4, 8, 16, 32, 64, ...
# 很快耗尽系统的 PID 和内存
# 系统会变得无法响应

# 防护措施：
# 1. 限制用户的最大进程数
#    /etc/security/limits.conf
#    username hard nproc 1000

# 2. 使用 ulimit
#    ulimit -u 1000

# 3. 使用 cgroup 限制进程数
```

---

### 7. 函数在管道中的行为

#### 7.1 子 Shell 问题

```bash
# 管道中的每个命令都在子 Shell 中执行

count=0
echo -e "a\nb\nc" | while read line; do
    (( count++ ))
done
echo "count = $count"    # 0（不是 3！）

# 原因：
# while read 在子 Shell 中执行
# count++ 的修改不影响父 Shell

# 解决方案 1：进程替换
count=0
while read line; do
    (( count++ ))
done < <(echo -e "a\nb\nc")
echo "count = $count"    # 3

# 解决方案 2：lastpipe（Bash 4.2+）
shopt -s lastpipe
count=0
echo -e "a\nb\nc" | while read line; do
    (( count++ ))
done
echo "count = $count"    # 3
shopt -u lastpipe
```

#### 7.2 函数与管道

```bash
# 函数在管道中也会在子 Shell 中执行

my_function() {
    echo "PID in function: $$"
    x=42
}

x=0
my_function | cat
echo "x = $x"    # 0（不是 42！）

# 但如果函数不在管道中，就在当前 Shell 执行
x=0
my_function
echo "x = $x"    # 42

# 使用 process substitution 避免子 Shell
my_function() {
    x=42
}

x=0
my_function    # 不在管道中，直接执行
echo "x = $x"    # 42
```

#### 7.3 管道中的错误处理

```bash
# set -o pipefail：管道中任意命令失败，整个管道失败
set -o pipefail

# 默认行为：只有最后一个命令的退出码被检查
false | true
echo $?    # 0（true 的退出码）

# 开启 pipefail 后
set -o pipefail
false | true
echo $?    # 1（false 的退出码）

# 在脚本中使用
#!/usr/bin/env bash
set -euo pipefail

# 现在管道中的错误也会导致脚本退出
cat nonexistent_file | grep "pattern"
```

---

### 8. SRE 实战案例

#### 8.1 日志记录函数库

```bash
#!/usr/bin/env bash
# logging.sh — 日志记录函数库

# 颜色定义
readonly LOG_RED='\033[0;31m'
readonly LOG_GREEN='\033[0;32m'
readonly LOG_YELLOW='\033[1;33m'
readonly LOG_BLUE='\033[0;34m'
readonly LOG_PURPLE='\033[0;35m'
readonly LOG_CYAN='\033[0;36m'
readonly LOG_NC='\033[0m'    # No Color

# 日志级别
readonly LOG_LEVEL_DEBUG=0
readonly LOG_LEVEL_INFO=1
readonly LOG_LEVEL_WARN=2
readonly LOG_LEVEL_ERROR=3
readonly LOG_LEVEL_FATAL=4

# 当前日志级别（默认 INFO）
LOG_CURRENT_LEVEL="${LOG_LEVEL:-$LOG_LEVEL_INFO}"

# 日志输出目标
LOG_OUTPUT="${LOG_OUTPUT:-/dev/stderr}"

# 日志文件
LOG_FILE="${LOG_FILE:-}"

# 是否显示颜色
LOG_COLOR="${LOG_COLOR:-true}"

# 内部函数：格式化日志消息
_log_format() {
    local level="$1"
    local color="$2"
    local message="$3"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    local caller_info=""
    if [[ "${LOG_SHOW_CALLER:-false}" == "true" ]]; then
        caller_info=" [${FUNCNAME[2]:-main}:${BASH_LINENO[1]:-0}]"
    fi

    if [[ "$LOG_COLOR" == "true" ]]; then
        echo -e "${color}[${timestamp}] [${level}]${LOG_NC}${caller_info} ${message}"
    else
        echo "[${timestamp}] [${level}]${caller_info} ${message}"
    fi
}

# 内部函数：写入日志
_log_write() {
    local level_num="$1"
    local message="$2"

    # 检查日志级别
    if (( level_num < LOG_CURRENT_LEVEL )); then
        return 0
    fi

    # 输出到 stderr
    echo "$message" >&2

    # 输出到日志文件
    if [[ -n "$LOG_FILE" ]]; then
        echo "$message" >> "$LOG_FILE"
    fi
}

# 公共函数
log_debug() {
    [[ "$LOG_CURRENT_LEVEL" -le "$LOG_LEVEL_DEBUG" ]] || return 0
    local msg
    msg=$(_log_format "DEBUG" "$LOG_CYAN" "$*")
    _log_write "$LOG_LEVEL_DEBUG" "$msg"
}

log_info() {
    [[ "$LOG_CURRENT_LEVEL" -le "$LOG_LEVEL_INFO" ]] || return 0
    local msg
    msg=$(_log_format "INFO" "$LOG_GREEN" "$*")
    _log_write "$LOG_LEVEL_INFO" "$msg"
}

log_warn() {
    [[ "$LOG_CURRENT_LEVEL" -le "$LOG_LEVEL_WARN" ]] || return 0
    local msg
    msg=$(_log_format "WARN" "$LOG_YELLOW" "$*")
    _log_write "$LOG_LEVEL_WARN" "$msg"
}

log_error() {
    [[ "$LOG_CURRENT_LEVEL" -le "$LOG_LEVEL_ERROR" ]] || return 0
    local msg
    msg=$(_log_format "ERROR" "$LOG_RED" "$*")
    _log_write "$LOG_LEVEL_ERROR" "$msg"
}

log_fatal() {
    local msg
    msg=$(_log_format "FATAL" "$LOG_PURPLE" "$*")
    _log_write "$LOG_LEVEL_FATAL" "$msg"
    exit 1
}

# 设置日志级别
set_log_level() {
    local level="$1"
    case "$level" in
        debug|DEBUG) LOG_CURRENT_LEVEL=$LOG_LEVEL_DEBUG ;;
        info|INFO)   LOG_CURRENT_LEVEL=$LOG_LEVEL_INFO ;;
        warn|WARN)   LOG_CURRENT_LEVEL=$LOG_LEVEL_WARN ;;
        error|ERROR) LOG_CURRENT_LEVEL=$LOG_LEVEL_ERROR ;;
        fatal|FATAL) LOG_CURRENT_LEVEL=$LOG_LEVEL_FATAL ;;
        *)           log_error "Unknown log level: $level"; return 1 ;;
    esac
}

# 使用示例：
# source logging.sh
# LOG_LEVEL=DEBUG
# LOG_FILE="/var/log/myapp.log"
# log_info "Application started"
# log_error "Something went wrong"
```

#### 8.2 错误处理函数库

```bash
#!/usr/bin/env bash
# error_handling.sh — 错误处理函数库

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

# 错误处理函数
error_exit() {
    local message="$1"
    local code="${2:-1}"
    echo -e "${RED}ERROR: ${message}${NC}" >&2
    exit "$code"
}

# 警告函数
warn() {
    echo -e "${YELLOW}WARNING: $*${NC}" >&2
}

# 成功函数
success() {
    echo -e "${GREEN}SUCCESS: $*${NC}" >&2
}

# 清理函数（用于 trap）
_cleanup() {
    local exit_code=$?
    # 清理临时文件
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
        echo "Cleaned up: $TEMP_DIR"
    fi
    exit "$exit_code"
}

# 设置 trap
setup_cleanup() {
    trap _cleanup EXIT ERR INT TERM
}

# 重试函数
retry() {
    local max_attempts="$1"
    local delay="$2"
    shift 2
    local cmd="$*"

    local attempt=1
    while (( attempt <= max_attempts )); do
        if eval "$cmd"; then
            return 0
        fi

        if (( attempt < max_attempts )); then
            echo "Attempt $attempt/$max_attempts failed, retrying in ${delay}s..."
            sleep "$delay"
        fi

        (( attempt++ ))
    done

    echo "ERROR: All $max_attempts attempts failed" >&2
    return 1
}

# 确保命令存在
require_command() {
    local cmd="$1"
    if ! command -v "$cmd" &>/dev/null; then
        error_exit "Required command not found: $cmd"
    fi
}

# 确保以 root 运行
require_root() {
    if [[ $(id -u) -ne 0 ]]; then
        error_exit "This script must be run as root"
    fi
}

# 确保文件存在
require_file() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        error_exit "Required file not found: $file"
    fi
}

# 确保目录存在
require_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        error_exit "Required directory not found: $dir"
    fi
}

# 确保服务正在运行
require_service() {
    local service="$1"
    if ! systemctl is-active "$service" &>/dev/null; then
        error_exit "Required service not running: $service"
    fi
}

# 使用示例：
# source error_handling.sh
# setup_cleanup
# TEMP_DIR=$(mktemp -d)
# require_command "docker"
# require_root
```

#### 8.3 服务管理函数

```bash
#!/usr/bin/env bash
# service_manager.sh — 服务管理函数库

# 服务配置
declare -A SERVICE_CONFIG
SERVICE_CONFIG=(
    [nginx]="Nginx Web Server"
    [mysql]="MySQL Database"
    [redis]="Redis Cache"
    [myapp]="My Application"
)

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# 检查服务是否存在
service_exists() {
    local service="$1"
    systemctl list-unit-files | grep -q "^${service}.service"
}

# 启动服务
service_start() {
    local service="$1"
    local desc="${SERVICE_CONFIG[$service]:-$service}"

    if ! service_exists "$service"; then
        log "ERROR: 服务不存在: $service"
        return 1
    fi

    if systemctl is-active "$service" &>/dev/null; then
        log "WARN: $desc 已经在运行"
        return 0
    fi

    log "启动 $desc..."
    if systemctl start "$service"; then
        log "OK: $desc 启动成功"
        return 0
    else
        log "ERROR: $desc 启动失败"
        return 1
    fi
}

# 停止服务
service_stop() {
    local service="$1"
    local desc="${SERVICE_CONFIG[$service]:-$service}"

    if ! service_exists "$service"; then
        log "ERROR: 服务不存在: $service"
        return 1
    fi

    if ! systemctl is-active "$service" &>/dev/null; then
        log "WARN: $desc 未在运行"
        return 0
    fi

    log "停止 $desc..."
    if systemctl stop "$service"; then
        log "OK: $desc 停止成功"
        return 0
    else
        log "ERROR: $desc 停止失败"
        return 1
    fi
}

# 重启服务
service_restart() {
    local service="$1"
    local desc="${SERVICE_CONFIG[$service]:-$service}"

    log "重启 $desc..."
    if systemctl restart "$service"; then
        log "OK: $desc 重启成功"
        return 0
    else
        log "ERROR: $desc 重启失败"
        return 1
    fi
}

# 查看服务状态
service_status() {
    local service="$1"
    local desc="${SERVICE_CONFIG[$service]:-$service}"

    echo "=== $desc 状态 ==="
    systemctl status "$service" --no-pager
}

# 等待服务启动
wait_for_service() {
    local service="$1"
    local timeout="${2:-30}"
    local count=0

    while ! systemctl is-active "$service" &>/dev/null; do
        if (( count >= timeout )); then
            log "ERROR: $service 启动超时 (${timeout}s)"
            return 1
        fi
        sleep 1
        (( count++ ))
    done

    log "OK: $service 已启动"
    return 0
}

# 批量操作
service_batch_action() {
    local action="$1"
    shift
    local services=("$@")

    local success=0
    local fail=0

    for service in "${services[@]}"; do
        if service_"$action" "$service"; then
            (( success++ ))
        else
            (( fail++ ))
        fi
    done

    log "批量操作完成: 成功=$success, 失败=$fail"
}

# 使用示例：
# source service_manager.sh
# service_start nginx
# service_restart mysql
# service_batch_action start nginx mysql redis
```

---

## 💻 实战练习

### 练习 1：编写工具函数库

```bash
# 创建一个工具函数库，包含以下函数：
# 1. confirm() — 确认操作（y/n）
# 2. select_option() — 选择菜单
# 3. progress_bar() — 进度条
# 4. spinner() — 加载动画

cat > utils.sh << 'SCRIPT'
#!/usr/bin/env bash
# 你的实现...
SCRIPT
```

### 练习 2：编写配置文件解析器

```bash
# 编写一个函数库，解析 YAML/INI 配置文件
# 1. parse_config() — 解析配置文件
# 2. get_config() — 获取配置值
# 3. set_config() — 设置配置值

cat > config_parser.sh << 'SCRIPT'
#!/usr/bin/env bash
# 你的实现...
SCRIPT
```

### 练习 3：编写服务健康检查库

```bash
# 编写一个健康检查函数库：
# 1. check_http() — 检查 HTTP 端点
# 2. check_tcp() — 检查 TCP 端口
# 3. check_disk() — 检查磁盘使用率
# 4. check_memory() — 检查内存使用率
# 5. check_load() — 检查系统负载
# 6. run_checks() — 运行所有检查

cat > health_check.sh << 'SCRIPT'
#!/usr/bin/env bash
# 你的实现...
SCRIPT
```

<details>
<summary>答案</summary>

```bash
#!/usr/bin/env bash
# health_check.sh

# 检查 HTTP 端点
check_http() {
    local url="$1"
    local expected_code="${2:-200}"
    local timeout="${3:-5}"

    local http_code
    http_code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null || echo "000")

    if [[ "$http_code" -eq "$expected_code" ]]; then
        echo "OK: $url ($http_code)"
        return 0
    else
        echo "FAIL: $url (expected $expected_code, got $http_code)"
        return 1
    fi
}

# 检查 TCP 端口
check_tcp() {
    local host="$1"
    local port="$2"
    local timeout="${3:-5}"

    if timeout "$timeout" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
        echo "OK: $host:$port"
        return 0
    else
        echo "FAIL: $host:$port"
        return 1
    fi
}

# 检查磁盘使用率
check_disk() {
    local path="$1"
    local threshold="${2:-80}"

    local usage
    usage=$(df "$path" | awk 'NR==2{print $5}' | tr -d '%')

    if (( usage <= threshold )); then
        echo "OK: $path disk usage ${usage}%"
        return 0
    else
        echo "FAIL: $path disk usage ${usage}% > ${threshold}%"
        return 1
    fi
}

# 运行所有检查
run_checks() {
    local failed=0

    check_http "http://localhost:8080/health" || (( failed++ ))
    check_tcp "localhost" 3306 || (( failed++ ))
    check_tcp "localhost" 6379 || (( failed++ ))
    check_disk "/" 80 || (( failed++ ))
    check_disk "/var/log" 90 || (( failed++ ))

    return "$failed"
}
```
</details>

---

## 🎯 面试题精选

### 1. Shell 函数如何返回值？

**答：**
Shell 函数有三种返回值方式：

1. **return 语句**：返回 0-255 的整数（退出码），0 表示成功
   ```bash
   is_root() { [[ $(id -u) -eq 0 ]]; }
   ```

2. **echo 输出**：通过命令替换捕获任意数据
   ```bash
   get_hostname() { echo "$(hostname)"; }
   result=$(get_hostname)
   ```

3. **全局变量**：通过关联数组或 nameref 返回多个值
   ```bash
   declare -A RESULT
   get_info() { RESULT[name]="Alice"; RESULT[age]=30; }
   ```

### 2. local 关键字的作用是什么？

**答：**
- `local` 声明函数内部的局部变量
- 局部变量只在函数内部和其调用的子函数中可见
- 函数返回后，局部变量自动销毁
- 防止变量污染全局命名空间
- **注意**：`local` 会影响 `$?` 的值（`local x=$?` 中 `$?` 是 `local` 的退出码）

### 3. source 和 bash 执行脚本有什么区别？

**答：**
```bash
# source（或 .）：在当前 Shell 中执行
source script.sh    # 脚本中的变量和函数在当前 Shell 可见
. script.sh         # 同上

# bash：在新的子 Shell 中执行
bash script.sh      # 脚本中的变量和函数不影响当前 Shell
./script.sh         # 同上（如果脚本有执行权限）
```

**关键区别：**
- `source` 不创建子进程，在当前 Shell 环境中执行
- `bash` 创建新的子进程，继承当前 Shell 的环境变量
- `source` 常用于加载配置文件或函数库
- `bash` 常用于执行独立的脚本任务

### 4. 以下代码有什么问题？

```bash
my_function() {
    local result=$(some_command)
    return $result
}
```

**答：**
1. `return` 只能返回 0-255 的整数，如果 `result` 大于 255，会取模
2. 如果 `result` 包含非数字字符，会导致错误

**修复：**
```bash
# 如果只需要返回成功/失败
my_function() {
    local result
    result=$(some_command)
    [[ "$result" == "expected" ]]
}

# 如果需要返回数据
my_function() {
    some_command
}
result=$(my_function)
```

### 5. 什么是 fork 炸弹？如何防护？

**答：**
Fork 炸弹是一个递归函数，不断创建子进程直到系统资源耗尽：
```bash
:(){ :|:& };:
```

**防护措施：**
```bash
# 1. 限制用户最大进程数
# /etc/security/limits.conf
username hard nproc 1000

# 2. 使用 ulimit
ulimit -u 1000

# 3. 使用 cgroup
# 在 systemd 中配置 TasksMax
```

### 6. 函数在管道中的行为是什么？

**答：**
管道中的每个命令都在子 Shell 中执行，因此：
- 函数内部的变量修改不影响父 Shell
- 函数的退出码是管道中最后一个命令的退出码

```bash
# 问题
count=0
echo -e "a\nb\nc" | while read line; do
    (( count++ ))
done
echo "$count"    # 0（不是 3）

# 解决方案
count=0
while read line; do
    (( count++ ))
done < <(echo -e "a\nb\nc")
echo "$count"    # 3
```

### 7. 如何编写可复用的 Shell 函数库？

**答：**
```bash
# 1. 创建函数库文件
# /usr/local/lib/mylib.sh
log_info() { echo "[INFO] $*"; }
log_error() { echo "[ERROR] $*" >&2; }

# 2. 防止重复加载
[[ "${_MYLIB_LOADED:-}" == "true" ]] && return 0
_MYLIB_LOADED=true

# 3. 在脚本中加载
source /usr/local/lib/mylib.sh

# 4. 或自动查找库路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../lib/mylib.sh"
```

---

## 📚 深入阅读

- [Bash Functions](https://www.gnu.org/software/bash/manual/bash.html#Shell-Functions) — GNU 官方文档
- [Bash Guide: Functions](https://mywiki.wooledge.org/BashGuide/Practices#Functions) — 函数最佳实践
- [Advanced Bash-Scripting Guide: Functions](https://tldp.org/LDP/abs/html/functions.html) — 高级函数技巧

---

## ✅ 自检清单

### 理论检查点
- [ ] 掌握函数定义的两种语法（POSIX 和 function 关键字）
- [ ] 理解函数参数的传递机制（$1-$9、${10}、$@、$#）
- [ ] 掌握 return 和 echo 返回值的区别
- [ ] 理解 local 关键字和变量作用域
- [ ] 理解 source 和 bash 执行脚本的区别
- [ ] 理解函数在管道中的子 Shell 行为
- [ ] 了解 fork 炸弹的原理和防护

### 实操检查点
- [ ] 能编写日志记录函数库（支持颜色和级别）
- [ ] 能编写错误处理函数库（trap + cleanup 模式）
- [ ] 能编写服务管理函数（start/stop/restart/status）
- [ ] 能编写可复用的函数库并通过 source 引入
- [ ] 能正确处理函数参数和返回值
