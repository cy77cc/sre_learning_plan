# Day 17: Shell 循环结构 — for/while/until

> 📅 日期：2026-04-28
> 📖 学习主题：Shell 循环结构 — for/while/until
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 16（Shell 条件判断 — if/elif/else/test）

## 🎯 学习目标

完成 Day 17 的学习后，你应该能够：
- 熟练使用 for 循环的多种形式（列表、C 风格、文件遍历）
- 掌握 while read line 模式安全读取文件
- 理解 until 循环的使用场景
- 掌握循环控制（break、continue、shift）
- 避免循环中的常见陷阱（文件名空格、命令替换分割）
- 能编写并行循环脚本（& + wait、xargs -P、GNU parallel）
- 能编写批量服务器巡检和日志处理脚本

---

## 📖 核心知识点

### 1. for 循环

#### 1.1 列表遍历

```bash
# 基本语法
for variable in list; do
    commands
done

# 最简单的形式
for name in Alice Bob Charlie; do
    echo "Hello, $name"
done
# 输出：
# Hello, Alice
# Hello, Bob
# Hello, Charlie

# 使用变量作为列表
servers="web01 web02 web03"
for server in $servers; do
    echo "Checking $server"
done

# 使用数组
fruits=("apple" "banana" "cherry")
for fruit in "${fruits[@]}"; do
    echo "I like $fruit"
done

# 范围表达式（Bash 扩展）
for i in {1..5}; do
    echo "Number: $i"
done

# 带步长的范围（Bash 4.0+）
for i in {0..20..5}; do
    echo "Number: $i"
done
# 输出：0 5 10 15 20

# 字符范围
for letter in {a..z}; do
    printf "%s " "$letter"
done
echo ""

# 使用命令输出作为列表
for user in $(cat /etc/passwd | cut -d: -f1); do
    echo "User: $user"
done

# ⚠️ 注意：命令输出会按空格和换行分词
# 如果列表项包含空格，需要用 while read 代替
```

#### 1.2 C 风格 for 循环

```bash
# C 风格语法（Bash 专用）
for ((initialization; condition; increment)); do
    commands
done

# 基本示例
for ((i=0; i<5; i++)); do
    echo "i = $i"
done
# 输出：0 1 2 3 4

# 递减
for ((i=10; i>0; i--)); do
    echo "Countdown: $i"
done

# 多变量
for ((i=0, j=10; i<j; i++, j--)); do
    echo "i=$i, j=$j"
done
# 输出：
# i=0, j=10
# i=1, j=9
# i=2, j=8
# i=3, j=7
# i=4, j=6

# 无限循环
for ((;;)); do
    echo "无限循环（Ctrl+C 退出）"
    sleep 1
done
```

#### 1.3 文件遍历

```bash
# 使用 glob 模式遍历文件
for file in /var/log/*.log; do
    echo "Log file: $file"
done

# 递归遍历（Bash 4.0+，需要开启 globstar）
shopt -s globstar
for file in /var/log/**/*.log; do
    echo "Log file: $file"
done
shopt -u globstar

# 多个 glob 模式
for file in *.txt *.md *.log; do
    [[ -f "$file" ]] || continue    # 跳过不存在的模式
    echo "File: $file"
done

# 遍历目录
for dir in /home/*/; do
    echo "Home directory: $dir"
done

# 遍历特定类型的文件
for file in *.{sh,bash}; do
    [[ -f "$file" ]] || continue
    echo "Script: $file"
done
```

#### 1.4 for 循环的陷阱

```bash
# 陷阱 1：for line in $(cat file) 会按空格分词
# ❌ 错误
for line in $(cat /etc/hosts); do
    echo "$line"
done
# 输出会把每行按空格拆开

# ✅ 正确：使用 while read
while IFS= read -r line; do
    echo "$line"
done < /etc/hosts

# 陷阱 2：文件名包含空格
# ❌ 错误
for file in $(ls); do
    echo "$file"
done
# 如果有文件名为 "my file.txt"，会被拆成 "my" 和 "file.txt"

# ✅ 正确：使用 glob
for file in *; do
    echo "$file"
done

# 陷阱 3：数组遍历时不加引号
files=("file 1.txt" "file 2.txt" "file 3.txt")

# ❌ 错误
for file in ${files[@]}; do
    echo "$file"
done
# 输出：
# file
# 1.txt
# file
# 2.txt
# file
# 3.txt

# ✅ 正确
for file in "${files[@]}"; do
    echo "$file"
done
# 输出：
# file 1.txt
# file 2.txt
# file 3.txt
```

---

### 2. while 循环

#### 2.1 基本语法

```bash
# 基本语法
while condition; do
    commands
done

# 条件为真时继续循环
count=0
while [[ $count -lt 5 ]]; do
    echo "count = $count"
    (( count++ ))
done
# 输出：0 1 2 3 4

# 使用 (( )) 简化数值比较
count=0
while (( count < 5 )); do
    echo "count = $count"
    (( count++ ))
done

# 无限循环
while true; do
    echo "Running..."
    sleep 1
done

# 等价写法
while :; do
    echo "Running..."
    sleep 1
done

# 读取命令输出
while read -r line; do
    echo "Line: $line"
done < <(ls -la)
```

#### 2.2 while read line（逐行读取文件）

```bash
# 这是 Shell 中逐行读取文件的最佳实践

# 基本用法
while read -r line; do
    echo "$line"
done < /etc/hosts

# -r 选项：禁止反斜杠转义
# 不加 -r 的话，\n 会被解释为续行符

# 保留前导空格和尾部空格
while IFS= read -r line; do
    echo "$line"
done < /etc/hosts

# IFS= 的作用：
# 默认 IFS 包含空格、制表符、换行符
# 读取时会自动删除前导和尾部的 IFS 字符
# 设置 IFS= 可以保留这些空格

# 按分隔符读取字段
while IFS=: read -r user _ uid gid _ home shell; do
    echo "User: $user, UID: $uid, Shell: $shell"
done < /etc/passwd

# 读取 CSV 文件
while IFS=, read -r name age city; do
    echo "Name: $name, Age: $age, City: $city"
done < data.csv

# 处理可能没有换行符结尾的文件
while IFS= read -r line || [[ -n "$line" ]]; do
    echo "$line"
done < file.txt
# || [[ -n "$line" ]] 确保最后一行（如果没有换行符）也被处理
```

#### 2.3 while read 的高级用法

```bash
# 读取命令输出
while IFS= read -r line; do
    echo "Processing: $line"
done < <(find /var/log -name "*.log" -mtime +7)

# 读取文件描述符
exec 3< /etc/hosts
while IFS= read -r line <&3; do
    echo "$line"
done
exec 3<&-

# 读取多列数据
while read -r ip hostname aliases; do
    echo "IP: $ip, Hostname: $hostname"
done < /etc/hosts

# 处理带注释的配置文件
while IFS= read -r line; do
    # 跳过空行和注释
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    echo "Config: $line"
done < /etc/ssh/sshd_config

# 读取并修改文件
while IFS= read -r line; do
    # 替换某些内容
    echo "${line/old/new}"
done < input.txt > output.txt
```

#### 2.4 while 的实际应用场景

```bash
# 场景 1：等待服务启动
wait_for_service() {
    local service="$1"
    local timeout="${2:-30}"
    local count=0

    while ! systemctl is-active "$service" &>/dev/null; do
        if (( count >= timeout )); then
            echo "ERROR: $service 启动超时" >&2
            return 1
        fi
        sleep 1
        (( count++ ))
    done

    echo "OK: $service 已启动"
}

# 场景 2：重试机制
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
        echo "Attempt $attempt failed, retrying in ${delay}s..."
        sleep "$delay"
        (( attempt++ ))
    done

    echo "ERROR: 所有重试都失败了" >&2
    return 1
}

# 使用
retry 3 5 "curl -sf https://api.example.com/health"

# 场景 3：处理管道数据
ps aux | while read -r user pid cpu mem vsz rss tty stat start time command; do
    if (( $(echo "$cpu > 50" | bc -l) )); then
        echo "HIGH CPU: PID=$pid CPU=$cpu CMD=$command"
    fi
done

# 场景 4：交互式菜单
while true; do
    echo "===== 菜单 ====="
    echo "1. 查看状态"
    echo "2. 重启服务"
    echo "3. 查看日志"
    echo "0. 退出"
    read -p "请选择: " choice

    case "$choice" in
        1) show_status ;;
        2) restart_service ;;
        3) view_logs ;;
        0) break ;;
        *) echo "无效选择" ;;
    esac
done
```

---

### 3. until 循环

#### 3.1 基本语法

```bash
# until 循环：条件为假时继续循环
# 等价于 while ! condition

until condition; do
    commands
done

# 基本示例
count=0
until [[ $count -ge 5 ]]; do
    echo "count = $count"
    (( count++ ))
done
# 输出：0 1 2 3 4

# 等价的 while 写法
count=0
while [[ $count -lt 5 ]]; do
    echo "count = $count"
    (( count++ ))
done
```

#### 3.2 until vs while

```bash
# until 和 while 的选择取决于哪个更易读

# 场景 1：等待条件成立
# 使用 until（更自然）
until ping -c 1 8.8.8.8 &>/dev/null; do
    echo "等待网络..."
    sleep 1
done
echo "网络已连通"

# 使用 while（等价）
while ! ping -c 1 8.8.8.8 &>/dev/null; do
    echo "等待网络..."
    sleep 1
done
echo "网络已连通"

# 场景 2：轮询任务完成
until [[ -f /tmp/task_done ]]; do
    echo "等待任务完成..."
    sleep 5
done
echo "任务已完成"

# 场景 3：读取用户输入
until [[ "$answer" =~ ^(yes|no)$ ]]; do
    read -p "请输入 yes 或 no: " answer
done
echo "你选择了: $answer"
```

---

### 4. 循环控制

#### 4.1 break

```bash
# break：跳出当前循环

# 基本用法
for i in {1..10}; do
    if [[ $i -eq 5 ]]; then
        break    # 跳出循环
    fi
    echo "i = $i"
done
# 输出：1 2 3 4

# break N：跳出 N 层循环
for i in {1..3}; do
    for j in {1..3}; do
        if [[ $j -eq 2 ]]; then
            break 2    # 跳出两层循环
        fi
        echo "i=$i, j=$j"
    done
done
# 输出：
# i=1, j=1

# 实际应用：查找文件
find_in_paths() {
    local filename="$1"
    local paths=("/usr/local/bin" "/usr/bin" "/bin" "/usr/sbin" "/sbin")

    for path in "${paths[@]}"; do
        if [[ -x "$path/$filename" ]]; then
            echo "$path/$filename"
            return 0
        fi
    done
    return 1
}
```

#### 4.2 continue

```bash
# continue：跳过本次循环，继续下一次

# 基本用法
for i in {1..10}; do
    if (( i % 2 == 0 )); then
        continue    # 跳过偶数
    fi
    echo "奇数: $i"
done
# 输出：1 3 5 7 9

# continue N：跳过 N 层循环的当前迭代
for i in {1..3}; do
    for j in {1..3}; do
        if [[ $j -eq 2 ]]; then
            continue 2    # 跳过外层循环的当前迭代
        fi
        echo "i=$i, j=$j"
    done
done
# 输出：
# i=1, j=1
# i=2, j=1
# i=3, j=1

# 实际应用：处理文件列表
for file in *; do
    # 跳过目录
    [[ -d "$file" ]] && continue

    # 跳过非 .log 文件
    [[ "$file" != *.log ]] && continue

    echo "Processing: $file"
done
```

#### 4.3 shift

```bash
# shift：移动位置参数（通常用于命令行参数解析）

# 基本用法
#!/usr/bin/env bash
echo "参数: $@"
while [[ $# -gt 0 ]]; do
    echo "处理: $1"
    shift
done

# 运行：./script.sh a b c
# 输出：
# 参数: a b c
# 处理: a
# 处理: b
# 处理: c

# shift N：移动 N 个位置
#!/usr/bin/env bash
echo "初始: $@"
shift 2
echo "shift 2 后: $@"

# 运行：./script.sh a b c d e
# 输出：
# 初始: a b c d e
# shift 2 后: c d e

# 实际应用：解析命令行选项
#!/usr/bin/env bash
verbose=false
output=""
files=()

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
        --)
            shift
            files=("$@")
            break
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            files+=("$1")
            shift
            ;;
    esac
done

echo "verbose=$verbose"
echo "output=$output"
echo "files=${files[*]}"
```

---

### 5. 循环中的陷阱

#### 5.1 文件名含空格的问题

```bash
# 问题演示
# 假设当前目录有文件："file 1.txt" "file 2.txt" "file 3.txt"

# ❌ 错误 1：for file in $(ls)
for file in $(ls); do
    echo "[$file]"
done
# 输出：
# [file]
# [1.txt]
# [file]
# [2.txt]
# [file]
# [3.txt]

# ❌ 错误 2：for file in $(find ...)
for file in $(find . -name "*.txt"); do
    echo "[$file]"
done
# 同样会按空格分词

# ✅ 正确 1：使用 glob
for file in *.txt; do
    echo "[$file]"
done

# ✅ 正确 2：使用 while read + find
while IFS= read -r -d '' file; do
    echo "[$file]"
done < <(find . -name "*.txt" -print0)
# -print0 使用 null 字符分隔，-d '' 以 null 字符作为分隔符

# ✅ 正确 3：使用 while read + find（不支持 -print0 的系统）
find . -name "*.txt" -print0 | while IFS= read -r -d '' file; do
    echo "[$file]"
done
```

#### 5.2 命令替换中的换行分割

```bash
# 问题演示
files=$(ls)
echo "$files"
# 输出：
# file 1.txt
# file 2.txt
# file 3.txt

# ❌ 错误：直接 for 遍历
for file in $files; do
    echo "[$file]"
end
# 会按空格分词

# ✅ 正确：使用数组
files=(*)
for file in "${files[@]}"; do
    echo "[$file]"
done

# ✅ 正确：使用 while read
ls | while IFS= read -r file; do
    echo "[$file]"
done
```

#### 5.3 循环变量作用域

```bash
# 问题演示：管道中的 while 循环在子 Shell 中执行

count=0
echo -e "a\nb\nc" | while read -r line; do
    (( count++ ))
done
echo "count = $count"
# 输出：count = 0（不是 3！）
# 因为管道创建了子 Shell，count 的修改不影响父 Shell

# 解决方案 1：使用进程替换
count=0
while read -r line; do
    (( count++ ))
done < <(echo -e "a\nb\nc")
echo "count = $count"
# 输出：count = 3

# 解决方案 2：使用临时文件
count=0
echo -e "a\nb\nc" > /tmp/input.txt
while read -r line; do
    (( count++ ))
done < /tmp/input.txt
echo "count = $count"
# 输出：count = 3
rm -f /tmp/input.txt

# 解决方案 3：使用 lastpipe（Bash 4.2+）
shopt -s lastpipe    # 最后一个管道命令在当前 Shell 执行
count=0
echo -e "a\nb\nc" | while read -r line; do
    (( count++ ))
done
echo "count = $count"
# 输出：count = 3
shopt -u lastpipe
```

#### 5.4 循环中的 I/O 重定向

```bash
# 问题演示：循环中的重定向

# ❌ 错误：每次迭代都覆盖文件
for i in {1..5}; do
    echo "Line $i" > output.txt
done
cat output.txt
# 只有 "Line 5"

# ✅ 正确：使用 >> 追加
> output.txt    # 清空文件
for i in {1..5}; do
    echo "Line $i" >> output.txt
done
cat output.txt
# 有 5 行

# ✅ 更好：整个循环的输出重定向一次
for i in {1..5}; do
    echo "Line $i"
done > output.txt

# 或使用 { } 代码块
{
    for i in {1..5}; do
        echo "Line $i"
    done
} > output.txt
```

---

### 6. 并行循环

#### 6.1 后台进程 + wait

```bash
# 基本模式：使用 & 将任务放到后台，wait 等待所有任务完成

# 基本示例
for i in {1..5}; do
    (
        echo "Task $i 开始"
        sleep $((RANDOM % 3 + 1))
        echo "Task $i 完成"
    ) &
done
wait    # 等待所有后台任务完成
echo "所有任务完成"

# 控制并发数
MAX_JOBS=3
running=0

for task in task1 task2 task3 task4 task5 task6; do
    (
        echo "处理 $task"
        sleep 2
        echo "完成 $task"
    ) &

    (( running++ ))
    if (( running >= MAX_JOBS )); then
        wait -n    # 等待任意一个后台任务完成（Bash 4.3+）
        (( running-- ))
    fi
done
wait
echo "所有任务完成"

# 带错误处理的并行执行
pids=()
errors=0

for server in web01 web02 web03; do
    (
        ssh "$server" "uptime"
    ) &
    pids+=($!)
done

for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
        (( errors++ ))
    fi
done

if (( errors > 0 )); then
    echo "有 $errors 个任务失败"
    exit 1
fi
```

#### 6.2 xargs 并行

```bash
# xargs -P：并行执行命令

# 基本用法
echo -e "web01\nweb02\nweb03" | xargs -P 3 -I {} ssh {} "uptime"

# -P 3：最多 3 个并行进程
# -I {}：用 {} 作为占位符

# 并行下载
cat urls.txt | xargs -P 5 -I {} curl -sO {}

# 并行处理文件
find /var/log -name "*.log" -mtime +7 | xargs -P 4 gzip

# 限制每次传递的参数数量
echo -e "1\n2\n3\n4\n5" | xargs -P 2 -n 2 echo "Processing:"
# -n 2：每次传递 2 个参数

# 实际应用：批量服务器操作
servers=("web01" "web02" "web03" "db01" "db02")
printf '%s\n' "${servers[@]}" | xargs -P 5 -I {} ssh {} "
    echo '=== {} ==='
    uptime
    free -h
    df -h
"
```

#### 6.3 GNU parallel

```bash
# GNU parallel：功能最强大的并行执行工具
# 安装：apt install parallel 或 yum install parallel

# 基本用法
parallel echo "Processing {}" ::: file1 file2 file3 file4

# 从文件读取参数
cat servers.txt | parallel ssh {} "uptime"

# 多个参数组合
parallel echo {1} {2} ::: A B C ::: 1 2 3
# 输出：A 1, A 2, A 3, B 1, B 2, B 3, C 1, C 2, C 3

# 控制并发数
parallel -j 4 echo "Processing {}" ::: {1..20}

# 进度显示
parallel --progress echo "Processing {}" ::: {1..20}

# 保持输出顺序
parallel -k echo "Processing {}" ::: {1..10}

# 错误处理
parallel --halt soon,fail=1 echo "Processing {}" ::: {1..10}
# 如果有 1 个任务失败，立即停止

# 实际应用：批量服务器巡检
cat servers.txt | parallel -j 10 --tag ssh {} "
    echo 'Hostname: {}'
    echo 'Uptime:' \$(uptime)
    echo 'Memory:' \$(free -h | awk '/Mem:/{print \$3\"/\"\$2}')
    echo 'Disk:' \$(df -h / | awk 'NR==2{print \$5}')
"
```

#### 6.4 并行循环的最佳实践

```bash
# 选择合适的并行工具

# 1. 简单任务：& + wait
for server in "${servers[@]}"; do
    ssh "$server" "uptime" &
done
wait

# 2. 需要控制并发数：xargs -P
printf '%s\n' "${servers[@]}" | xargs -P 5 -I {} ssh {} "uptime"

# 3. 复杂任务：GNU parallel
parallel -j 5 --tag ssh {} "uptime" ::: "${servers[@]}"

# 最佳实践：
# 1. 始终控制并发数（不要无限并发）
# 2. 处理错误（检查每个任务的退出码）
# 3. 设置超时（防止任务卡住）
# 4. 记录日志（每个任务的输出）
# 5. 使用锁文件（如果需要互斥访问共享资源）
```

---

### 7. SRE 实战案例

#### 7.1 批量服务器巡检脚本

```bash
#!/usr/bin/env bash
# server_audit.sh — 批量服务器巡检

set -euo pipefail

# 配置
SERVERS_FILE="${1:-servers.txt}"
OUTPUT_DIR="/tmp/audit_$(date +%Y%m%d_%H%M%S)"
MAX_PARALLEL=10

# 日志
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# 检查单台服务器
audit_server() {
    local server="$1"
    local output_file="$OUTPUT_DIR/${server}.txt"

    {
        echo "===== 服务器巡检: $server ====="
        echo "巡检时间: $(date)"
        echo ""

        # 系统信息
        echo "--- 系统信息 ---"
        ssh -o ConnectTimeout=10 "$server" "
            echo 'Hostname:' \$(hostname)
            echo 'OS:' \$(cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2)
            echo 'Kernel:' \$(uname -r)
            echo 'Uptime:' \$(uptime -p)
            echo 'Load:' \$(cat /proc/loadavg | awk '{print \$1, \$2, \$3}')
        " 2>&1 || echo "ERROR: 无法连接到 $server"

        echo ""

        # 资源使用
        echo "--- 资源使用 ---"
        ssh -o ConnectTimeout=10 "$server" "
            echo 'CPU 使用率:' \$(top -bn1 | grep 'Cpu(s)' | awk '{print \$2}')%
            echo '内存使用:' \$(free -h | awk '/Mem:/{print \$3\"/\"\$2}')
            echo '磁盘使用:' \$(df -h / | awk 'NR==2{print \$5}')
        " 2>&1 || echo "ERROR: 无法获取资源信息"

        echo ""

        # 服务状态
        echo "--- 关键服务 ---"
        ssh -o ConnectTimeout=10 "$server" "
            for svc in nginx mysql redis docker; do
                if systemctl is-active \$svc &>/dev/null; then
                    echo \"\$svc: running\"
                elif systemctl is-enabled \$svc &>/dev/null; then
                    echo \"\$svc: stopped\"
                fi
            done
        " 2>&1 || echo "ERROR: 无法获取服务状态"

        echo ""

        # 最近错误日志
        echo "--- 最近错误日志 ---"
        ssh -o ConnectTimeout=10 "$server" "
            journalctl -p err --since '1 hour ago' --no-pager | tail -10
        " 2>&1 || echo "ERROR: 无法获取日志"

    } > "$output_file" 2>&1

    log "完成: $server"
}

# 主流程
main() {
    mkdir -p "$OUTPUT_DIR"

    if [[ ! -f "$SERVERS_FILE" ]]; then
        echo "ERROR: 服务器列表文件不存在: $SERVERS_FILE" >&2
        exit 1
    fi

    log "开始巡检..."
    log "服务器列表: $SERVERS_FILE"
    log "输出目录: $OUTPUT_DIR"

    # 并行巡检
    while IFS= read -r server; do
        [[ -z "$server" || "$server" =~ ^# ]] && continue

        # 控制并发数
        while (( $(jobs -r | wc -l) >= MAX_PARALLEL )); do
            sleep 0.5
        done

        audit_server "$server" &
    done < "$SERVERS_FILE"

    wait
    log "巡检完成"
    log "报告目录: $OUTPUT_DIR"

    # 生成汇总报告
    log "生成汇总报告..."
    {
        echo "===== 服务器巡检汇总 ====="
        echo "巡检时间: $(date)"
        echo "服务器数量: $(ls "$OUTPUT_DIR"/*.txt | wc -l)"
        echo ""
        echo "=== 异常服务器 ==="
        for report in "$OUTPUT_DIR"/*.txt; do
            server=$(basename "$report" .txt)
            if grep -q "ERROR" "$report"; then
                echo "- $server: 有错误"
            fi
        done
    } > "$OUTPUT_DIR/summary.txt"

    log "汇总报告: $OUTPUT_DIR/summary.txt"
}

main "$@"
```

#### 7.2 批量用户创建脚本

```bash
#!/usr/bin/env bash
# batch_create_users.sh — 批量创建用户

set -euo pipefail

USERS_FILE="${1:?Usage: $0 <users.csv>}"
DEFAULT_SHELL="/bin/bash"
DEFAULT_GROUP="users"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

create_user() {
    local username="$1"
    local fullname="$2"
    local email="$3"

    # 检查用户是否已存在
    if id "$username" &>/dev/null; then
        log "SKIP: 用户 $username 已存在"
        return 0
    fi

    # 创建用户
    useradd -m -s "$DEFAULT_SHELL" -c "$fullname" "$username"

    # 生成随机密码
    password=$(openssl rand -base64 12)
    echo "$username:$password" | chpasswd

    # 强制首次登录修改密码
    chage -d 0 "$username"

    # 创建 SSH 目录
    mkdir -p "/home/$username/.ssh"
    chmod 700 "/home/$username/.ssh"
    chown "$username:$username" "/home/$username/.ssh"

    log "OK: 创建用户 $username ($fullname)"
    log "  密码: $password"
    log "  邮箱: $email"
}

# 主流程
main() {
    if [[ ! -f "$USERS_FILE" ]]; then
        echo "ERROR: 用户文件不存在: $USERS_FILE" >&2
        exit 1
    fi

    if [[ $(id -u) -ne 0 ]]; then
        echo "ERROR: 必须以 root 用户运行" >&2
        exit 1
    fi

    log "开始批量创建用户..."
    log "用户文件: $USERS_FILE"

    success=0
    fail=0

    while IFS=, read -r username fullname email; do
        # 跳过标题行和空行
        [[ "$username" == "username" || -z "$username" ]] && continue

        if create_user "$username" "$fullname" "$email"; then
            (( success++ ))
        else
            (( fail++ ))
        fi
    done < "$USERS_FILE"

    log "完成: 成功=$success, 失败=$fail"
}

main "$@"
```

#### 7.3 日志文件批量处理

```bash
#!/usr/bin/env bash
# log_processor.sh — 日志文件批量处理

set -euo pipefail

LOG_DIR="${1:-/var/log}"
PATTERN="${2:-ERROR|WARN}"
DAYS="${3:-7}"
OUTPUT_DIR="/tmp/log_analysis_$(date +%Y%m%d_%H%M%S)"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

analyze_log() {
    local logfile="$1"
    local output_file="$OUTPUT_DIR/$(basename "$logfile").analysis"

    {
        echo "===== 日志分析: $logfile ====="
        echo "分析时间: $(date)"
        echo ""

        # 文件信息
        echo "--- 文件信息 ---"
        echo "大小: $(stat -c %s "$logfile" 2>/dev/null || echo 'N/A') bytes"
        echo "最后修改: $(stat -c %y "$logfile" 2>/dev/null || echo 'N/A')"
        echo "行数: $(wc -l < "$logfile")"
        echo ""

        # 错误统计
        echo "--- 错误统计 ---"
        echo "ERROR: $(grep -c "ERROR" "$logfile" 2>/dev/null || echo 0)"
        echo "WARN: $(grep -c "WARN" "$logfile" 2>/dev/null || echo 0)"
        echo "FATAL: $(grep -c "FATAL" "$logfile" 2>/dev/null || echo 0)"
        echo ""

        # 最近错误
        echo "--- 最近错误 (最近 $DAYS 天) ---"
        grep -E "$PATTERN" "$logfile" | tail -20 || echo "无匹配记录"
        echo ""

        # 错误趋势
        echo "--- 错误趋势 (按小时) ---"
        grep "ERROR" "$logfile" | awk '{print $1, $2}' | cut -d: -f1,2 | sort | uniq -c | sort -rn | head -10 || echo "无数据"

    } > "$output_file" 2>&1

    log "完成: $logfile"
}

# 主流程
main() {
    mkdir -p "$OUTPUT_DIR"

    log "开始日志分析..."
    log "日志目录: $LOG_DIR"
    log "匹配模式: $PATTERN"
    log "时间范围: 最近 $DAYS 天"

    # 查找日志文件
    log_files=()
    while IFS= read -r -d '' file; do
        log_files+=("$file")
    done < <(find "$LOG_DIR" -name "*.log" -mtime -"$DAYS" -type f -print0 2>/dev/null)

    log "找到 ${#log_files[@]} 个日志文件"

    # 并行分析
    for logfile in "${log_files[@]}"; do
        analyze_log "$logfile" &
    done

    wait

    # 生成汇总
    {
        echo "===== 日志分析汇总 ====="
        echo "分析时间: $(date)"
        echo "日志目录: $LOG_DIR"
        echo "日志文件数: ${#log_files[@]}"
        echo ""

        echo "=== 各文件错误统计 ==="
        for analysis in "$OUTPUT_DIR"/*.analysis; do
            logfile=$(basename "$analysis" .analysis)
            errors=$(grep "^ERROR:" "$analysis" | awk '{print $2}')
            warns=$(grep "^WARN:" "$analysis" | awk '{print $2}')
            echo "$logfile: ERROR=$errors, WARN=$warns"
        done
    } > "$OUTPUT_DIR/summary.txt"

    log "分析完成"
    log "报告目录: $OUTPUT_DIR"
}

main "$@"
```

---

## 💻 实战练习

### 练习 1：数字猜谜游戏

```bash
# 编写一个猜数字游戏：
# 1. 随机生成 1-100 的数字
# 2. 用户猜测，提示"大了"或"小了"
# 3. 记录猜测次数
# 4. 最多 7 次机会

cat > guess_number.sh << 'SCRIPT'
#!/usr/bin/env bash
# 你的实现...
SCRIPT
```

### 练习 2：文件批量重命名

```bash
# 编写一个脚本，将目录中的文件批量重命名：
# 1. 将空格替换为下划线
# 2. 将大写转为小写
# 3. 添加日期前缀

cat > batch_rename.sh << 'SCRIPT'
#!/usr/bin/env bash
# 你的实现...
SCRIPT
```

### 练习 3：并行 ping 扫描

```bash
# 编写一个脚本，并行 ping 扫描一个网段：
# 1. 输入网段（如 192.168.1）
# 2. 并行 ping 1-254 的所有 IP
# 3. 输出在线的主机列表
# 4. 控制并发数（如最多 50 个）

cat > ping_scan.sh << 'SCRIPT'
#!/usr/bin/env bash
# 你的实现...
SCRIPT
```

<details>
<summary>答案</summary>

```bash
#!/usr/bin/env bash
# ping_scan.sh

SUBNET="${1:?Usage: $0 <subnet> (e.g., 192.168.1)}"
MAX_JOBS=50

online_hosts=()

for i in {1..254}; do
    ip="${SUBNET}.${i}"
    (
        if ping -c 1 -W 1 "$ip" &>/dev/null; then
            echo "$ip"
        fi
    ) &

    # 控制并发数
    if (( $(jobs -r | wc -l) >= MAX_JOBS )); then
        wait -n
    fi
done

# 收集结果
wait
```
</details>

---

## 🎯 面试题精选

### 1. for 和 while 循环如何选择？

**答：**
- **for 循环**：已知迭代次数或迭代集合
  - 遍历列表：`for i in 1 2 3`
  - 遍历文件：`for file in *.txt`
  - C 风格计数：`for ((i=0; i<10; i++))`
- **while 循环**：条件驱动，不知道迭代次数
  - 读取文件：`while read line`
  - 等待条件：`while ! condition`
  - 无限循环：`while true`

### 2. 如何安全地逐行读取文件？

**答：**
```bash
# 最佳实践
while IFS= read -r line; do
    echo "$line"
done < file.txt

# IFS=    — 保留前导和尾部空格
# -r      — 禁止反斜杠转义
# < file  — 重定向输入

# 处理最后一行没有换行符的情况
while IFS= read -r line || [[ -n "$line" ]]; do
    echo "$line"
done < file.txt
```

### 3. read 命令的 IFS 有什么作用？

**答：**
- IFS（Internal Field Separator）是内部字段分隔符
- 默认值：空格、制表符、换行符
- 影响 read 命令如何分割输入行
- `IFS= read -r line` 保留原始格式
- `IFS=: read -r user _ uid` 按冒号分割

### 4. 如何在 Shell 中实现并行执行？

**答：**
```bash
# 方法 1：& + wait
for task in tasks; do
    do_something "$task" &
done
wait

# 方法 2：xargs -P
cat tasks.txt | xargs -P 5 -I {} do_something {}

# 方法 3：GNU parallel
parallel -j 5 do_something {} ::: tasks
```

### 5. 以下代码有什么问题？

```bash
count=0
cat file.txt | while read line; do
    (( count++ ))
done
echo "Total: $count"
```

**答：**
输出 `Total: 0`。因为管道 `|` 创建了子 Shell，`while` 循环在子 Shell 中执行，`count++` 的修改不影响父 Shell 的 `count` 变量。

**修复：**
```bash
# 使用进程替换
count=0
while read line; do
    (( count++ ))
done < file.txt
echo "Total: $count"
```

### 6. break 和 continue 的区别？

**答：**
- `break` — 跳出整个循环
- `continue` — 跳过当前迭代，继续下一次
- `break N` — 跳出 N 层循环
- `continue N` — 跳过 N 层循环的当前迭代

### 7. 如何处理文件名中包含空格的情况？

**答：**
```bash
# ❌ 错误
for file in $(ls); do
    echo "$file"
done

# ✅ 正确 1：使用 glob
for file in *; do
    echo "$file"
done

# ✅ 正确 2：使用 while read -d ''
while IFS= read -r -d '' file; do
    echo "$file"
done < <(find . -print0)
```

---

## 📚 深入阅读

- [Bash Looping Constructs](https://www.gnu.org/software/bash/manual/bash.html#Looping-Constructs) — GNU 官方文档
- [GNU Parallel Tutorial](https://www.gnu.org/software/parallel/parallel_tutorial.html) — 并行执行教程
- [Bash Guide: Loops](https://mywiki.wooledge.org/BashGuide/Practices) — 循环最佳实践
- [xargs Manual](https://man7.org/linux/man-pages/man1/xargs.1.html) — xargs 手册

---

## ✅ 自检清单

### 理论检查点
- [ ] 掌握 for 循环的多种形式（列表、C 风格、glob）
- [ ] 理解 while read line 的 IFS 和 -r 选项
- [ ] 理解 until 和 while 的区别
- [ ] 掌握 break、continue、shift 的用法
- [ ] 理解循环变量在管道中的作用域问题
- [ ] 掌握并行循环的实现方式

### 实操检查点
- [ ] 能编写批量服务器巡检脚本
- [ ] 能编写批量用户创建脚本
- [ ] 能编写日志文件批量处理脚本
- [ ] 能正确处理文件名含空格的情况
- [ ] 能控制并行任务的并发数
