# Day 18: Shell 函数 — 定义、参数、返回值、作用域

> 📅 日期：2026-04-26
> 📖 学习主题：Shell 函数 — 定义、参数传递、返回值、作用域
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 18 的学习后，你应该掌握：
- 掌握函数的两种定义方式和最佳实践
- 理解函数参数传递机制（$1, $2, $@, $#）
- 理解 return（退出码）和 echo（数据输出）的根本区别
- 理解 local 关键字和变量作用域
- 掌握 shift 命令处理不定数量的参数
- 能编写模块化的函数脚本
- 理解函数在管道中的行为

---

## 📖 详细知识点

### 1. 函数的定义

```bash
# 方式 1（推荐，兼容 POSIX）
greet() {
    echo "Hello, $1"
}

# 方式 2（Bash 扩展）
function greet {
    echo "Hello, $1"
}

# 方式 3（混合，不推荐但常见）
function greet() {
    echo "Hello, $1"
}

# 调用（直接写函数名，不需要括号）
greet "Alice"
greet    # 如果没有参数，$1 为空

# 函数必须先定义后调用
# 以下写法会报错：
# hello
# hello() { echo "Hi"; }

# 正确写法：
hello() { echo "Hi"; }
hello
```

### 2. 函数参数

```bash
demo() {
    echo "函数名: $0"         # 注意：$0 是脚本名，不是函数名！
    echo "参数个数: $#"
    echo "第一个: $1"
    echo "第二个: $2"
    echo "所有(@): $@"
    echo "所有(*): $*"
}

demo foo bar baz
# 输出：
# 函数名: ./script.sh    ← 不是 demo！
# 参数个数: 3
# 第一个: foo
# 第二个: bar
# 所有(@): foo bar baz
# 所有(*): foo bar baz

# "$@" vs "$*"
# "$@" 展开为独立的参数："$1" "$2" "$3"
# "$*" 展开为一个字符串："$1 $2 $3"

# 演示差异
args() {
    echo "--- \$@ ---"
    for a in "$@"; do echo "  [$a]"; done
    echo "--- \$* ---"
    for a in "$*"; do echo "  [$a]"; done
}

args "hello world" foo bar
# --- $@ ---
#   [hello world]    ← 保留参数独立性
#   [foo]
#   [bar]
# --- $* ---
#   [hello world foo bar]    ← 合并为一个字符串
```

### 3. 返回值：return vs echo

**这是 Shell 函数最容易混淆的地方！**

```bash
# return 返回的是退出码（0-255），用于条件判断
is_even() {
    local num=$1
    if (( num % 2 == 0 )); then
        return 0    # 退出码 0 = 成功/真
    else
        return 1    # 退出码 1 = 失败/假
    fi
}

# 作为条件使用
if is_even 4; then
    echo "4 是偶数"
fi

# 检查退出码
is_even 5
echo $?    # 1

# echo 返回的是文本数据（通过标准输出）
get_disk_usage() {
    local mount="${1:-/}"
    df "$mount" --output=pcent | tail -1 | tr -d ' %'
}

# 用命令替换捕获输出
usage=$(get_disk_usage /)
echo "磁盘使用率: ${usage}%"

# 同时使用 return 和 echo
find_file() {
    local pattern=$1
    local result
    result=$(find / -name "$pattern" -type f 2>/dev/null | head -1)

    if [[ -n $result ]]; then
        echo "$result"    # 输出数据
        return 0          # 返回成功
    else
        echo "未找到" >&2  # 输出到标准错误
        return 1          # 返回失败
    fi
}

# 使用
if file=$(find_file "*.conf"); then
    echo "找到: $file"
else
    echo "没找到文件"
fi
```

### 4. 局部变量与作用域

```bash
# Shell 变量默认是全局的
name="global"

my_func() {
    name="changed inside"    # 修改了全局变量！
    age=30                    # 创建了新的全局变量
}

my_func
echo "$name"    # changed inside
echo "$age"     # 30
```

**用 local 限制作用域：**
```bash
name="global"

safe_func() {
    local name="local"    # 仅函数内部可见
    local age=30          # 仅函数内部可见
    echo "函数内: $name"
}

safe_func
echo "函数外: $name"    # global（不受影响）
echo "函数外: $age"     # 空（局部变量在外部不可见）

# 一次声明多个局部变量
calc() {
    local a b result
    a=$1
    b=$2
    result=$((a + b))
    echo "$result"
}

# ⚠️ 最佳实践：函数内的所有变量都用 local 声明
# 除非你有意要修改全局变量
```

### 5. shift 命令

```bash
# shift 移除第一个参数，其余参数前移

demo() {
    echo "参数: $@"
    shift
    echo "shift 后: $@"
    shift 2    # 移除前两个
    echo "再 shift 2: $@"
}

demo a b c d
# 输出：
# 参数: a b c d
# shift 后: b c d
# 再 shift 2: d

# 实战：处理命令行选项
parse_args() {
    local verbose=false
    local output="/tmp/output"
    local force=false

    while (( $# > 0 )); do
        case "$1" in
            -v|--verbose)
                verbose=true
                shift
                ;;
            -o|--output)
                output="$2"    # 取下一个参数
                shift 2        # 跳过两个参数
                ;;
            -f|--force)
                force=true
                shift
                ;;
            --)
                shift
                break          # 遇到 -- 停止解析
                ;;
            -*)
                echo "未知选项: $1"
                return 1
                ;;
            *)
                break          # 遇到非选项，停止解析
                ;;
        esac
    done

    # 剩余的是位置参数
    echo "verbose=$verbose, output=$output, force=$force"
    echo "剩余参数: $@"
}

parse_args -v --output /data/backup -f file1 file2
```

### 6. 函数的执行环境

```bash
# 函数在当前 Shell 中执行（不是子进程）
# 所以可以修改全局变量、cd 等

change_dir() {
    cd /tmp
}

change_dir
pwd    # /tmp    ← cd 生效了！

# 这与子进程不同：
# bash -c "cd /tmp"    ← 在子 Shell 中执行，不影响当前目录
# pwd                  ← 还是原来的目录
```

### 7. 函数与管道

```bash
# 函数可以用作管道的一部分
to_upper() {
    tr '[:lower:]' '[:upper:]'
}

echo "hello world" | to_upper    # HELLO WORLD

# 过滤函数
filter_errors() {
    grep -E "ERROR|FATAL|CRITICAL"
}

cat /var/log/app.log | filter_errors

# 函数在管道中的返回值
count_lines() {
    wc -l
}

lines=$(echo -e "a\nb\nc" | count_lines)
echo "$lines"    # 3
```

### 8. 常见陷阱

```bash
# 陷阱 1：用 return 返回字符串
bad_func() {
    return "hello"    # ❌ return 只接受 0-255
}

good_func() {
    echo "hello"    # ✅ 用 echo
}

# 陷阱 2：忘记 local 导致变量污染
counter=0
increment() {
    counter=$((counter + 1))    # 修改了全局！
}
increment
increment
echo $counter    # 2 — 可能不是你期望的

# 陷阱 3：函数名与系统命令冲突
# 不要定义 ls()、cd()、cat() 这样的函数名
# 如果必须覆盖，用 command 调用原命令
ls() {
    echo "=== 自定义 ls ==="
    command ls -la "$@"    # command 绕过函数调用原生命令
}

# 陷阱 4：函数内的 set -e
# set -e 在函数中的行为可能不同
# 建议用 if 显式检查，而不是依赖 set -e
```

---

## 🏗️ 实战

### 实战 1：日志函数

```bash
#!/usr/bin/env bash
LOG_FILE="/var/log/myapp.log"

log() {
    local level=$1; shift
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')

    local color
    case $level in
        INFO)   color='\033[0;32m' ;;
        WARN)   color='\033[1;33m' ;;
        ERROR)  color='\033[0;31m' ;;
        DEBUG)  color='\033[0;36m' ;;
        *)      color='\033[0m' ;;
    esac

    # 终端输出（带颜色）
    echo -e "${color}[${level}]\033[0m $*"

    # 文件输出（不带颜色）
    echo "$ts [$level] $*" >> "$LOG_FILE"
}

log INFO "服务启动"
log WARN "磁盘使用率 85%"
log ERROR "数据库连接失败"
```

### 实战 2：重试函数

```bash
# retry — 自动重试失败的命令
# 用法: retry <最大次数> <间隔秒数> <命令...>
retry() {
    local max_attempts=$1
    local delay=$2
    shift 2
    local attempt=0

    while (( attempt < max_attempts )); do
        if "$@"; then
            return 0
        fi
        ((attempt++))
        echo "⚠️ 第 $attempt/$max_attempts 次失败，${delay}s 后重试..."
        sleep "$delay"
    done

    echo "❌ 失败，已重试 $max_attempts 次"
    return 1
}

# 使用示例
retry 3 5 curl -sf http://api.example.com/health

# 在脚本中使用
if ! retry 5 10 mysqldump -u root mydb > /tmp/backup.sql; then
    echo "备份失败"
    exit 1
fi
```

### 实战 3：配置加载函数

```bash
#!/usr/bin/env bash
# config_loader.sh — 加载 .env 格式的配置文件

load_config() {
    local config_file="${1:-.env}"

    if [[ ! -f "$config_file" ]]; then
        echo "错误: 配置文件 $config_file 不存在"
        return 1
    fi

    local line_num=0
    while IFS= read -r line; do
        ((line_num++))

        # 跳过空行和注释
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

        # 检查格式
        if [[ ! "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
            echo "警告: $config_file:$line_num 格式错误"
            continue
        fi

        # 导出为环境变量
        export "$line"
    done < "$config_file"

    echo "✅ 已加载 $config_file"
}

# 使用
load_config .env
echo "DB_HOST=$DB_HOST"
echo "DB_PORT=$DB_PORT"
```

---

## 🧪 练习题

### 练习 1：求和函数

编写一个函数，接受任意数量的数字参数，返回它们的和。

<details>
<summary>答案</summary>

```bash
sum() {
    local total=0
    for num in "$@"; do
        total=$((total + num))
    done
    echo $total
}

sum 1 2 3 4 5    # 输出: 15
```
</details>

### 练习 2：最大值函数

编写一个函数，返回参数中最大的数字。

<details>
<summary>答案</summary>

```bash
max() {
    local max=$1
    shift
    for num in "$@"; do
        if (( num > max )); then
            max=$num
        fi
    done
    echo $max
}

max 3 7 2 9 1    # 输出: 9
```
</details>

---

## 📚 扩展阅读

- `man bash` — 搜索 "SHELL GRAMMAR" → "Shell Functions"
- [Bash 函数完全指南](https://tldp.org/LDP/abs/html/functions.html)
- [Shell 函数最佳实践](https://google.github.io/styleguide/shellguide.html#functions)
