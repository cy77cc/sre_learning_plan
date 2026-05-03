# Day 27: Bash 脚本编程进阶 -- 高级技巧

> 📅 日期：2026-04-27
> 📖 学习主题：Bash 脚本编程进阶 -- 高级技巧
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 18（Shell 函数）、Day 17（循环结构）、Day 16（条件判断）

---

## 🎯 学习目标

完成 Day 27 的学习后，你应该能够：
- 深入理解子 shell 与命令分组 `( )` vs `{ }` 的区别和性能影响
- 掌握进程替换 `<( )` 和 `>( )` 的原理与实际应用
- 使用命名管道 `mkfifo` 实现进程间通信（IPC）
- 熟练运用 `&` + `wait`、`xargs -P`、GNU parallel 实现并行执行
- 掌握文件描述符和重定向的高级用法（网络连接、here document）
- 了解 Bash 4/5 新特性（mapfile、coprocess、nameref）
- 掌握性能优化技巧，编写高效的 SRE 运维脚本

---

## 📖 核心知识点

### 1. 子 Shell 与命令分组

#### 1.1 子 Shell `( )`

小括号 `( )` 会创建一个子 shell 来执行其中的命令。子 shell 是当前 shell 的一个副本，它继承了父 shell 的环境变量，但子 shell 中的修改不会影响父 shell。

```bash
# 子 shell 中的变量修改不影响父 shell
x=10
(x=20; echo "子 shell 中: x=$x")  # 输出: 子 shell 中: x=20
echo "父 shell 中: x=$x"           # 输出: 父 shell 中: x=10

# 子 shell 继承父 shell 的环境变量
export MY_VAR="hello"
(echo "子 shell: $MY_VAR")  # 输出: hello

# 子 shell 中的 cd 不影响父 shell
pwd
(cd /tmp; pwd)  # /tmp
pwd             # 仍然是原目录

# 常见陷阱：管道中的命令在子 shell 中执行
count=0
echo -e "1\n2\n3" | while read -r line; do
    ((count++))
done
echo "count=$count"  # count=0 !!! 管道创建了子 shell

# 解决方案 1：使用进程替换
count=0
while read -r line; do
    ((count++))
done < <(echo -e "1\n2\n3")
echo "count=$count"  # count=3

# 解决方案 2：使用 lastpipe（Bash 4.2+）
shopt -s lastpipe
count=0
echo -e "1\n2\n3" | while read -r line; do
    ((count++))
done
echo "count=$count"  # count=3
```

#### 1.2 命令分组 `{ }`

花括号 `{ }` 在当前 shell 中执行命令，不会创建子 shell。注意 `{` 后面和 `}` 前面必须有空格，且最后必须有分号。

```bash
# 命令分组中的变量修改影响父 shell
x=10
{ x=20; echo "命令分组中: x=$x"; }
echo "父 shell 中: x=$x"  # x=20

# 命令分组可以重定向所有输出
{
    echo "Line 1"
    echo "Line 2"
    echo "Line 3"
} > /tmp/output.txt

# 对比：子 shell 重定向（效果相同，但机制不同）
(
    echo "Line 1"
    echo "Line 2"
    echo "Line 3"
) > /tmp/output.txt

# 性能对比
# ( ) : 需要 fork 子进程，有性能开销
# { } : 不需要 fork，性能更好
```

#### 1.3 `( )` vs `{ }` 对比

```
┌─────────────────────────────────────────────────────────┐
│                    ( ) vs { } 对比                       │
├──────────────┬─────────────────┬─────────────────────────┤
│ 特性         │ ( ) 子 shell    │ { } 命令分组             │
├──────────────┼─────────────────┼─────────────────────────┤
│ 执行环境     │ 新的子进程      │ 当前 shell              │
│ 变量修改     │ 不影响父 shell  │ 影响当前 shell          │
│ 性能         │ 较慢（fork）    │ 较快（无 fork）          │
│ 语法         │ 无特殊要求      │ { 后需空格, } 前需分号   │
│ 适用场景     │ 隔离操作        │ 批量重定向、分组执行      │
└──────────────┴─────────────────┴─────────────────────────┘
```

```bash
# 实际应用：批量重定向
{
    echo "服务器巡检报告"
    echo "时间: $(date)"
    echo "主机: $(hostname)"
    echo "---"
    uptime
    free -h
    df -h
} > /tmp/report.txt

# 实际应用：错误处理
{
    command1
    command2
    command3
} || {
    echo "上述命令中有失败的"
    send_alert
}
```

### 2. 进程替换

#### 2.1 进程替换原理

进程替换 `<( )` 和 `>( )` 是 Bash 的高级特性，它将命令的输出/输入映射为一个文件描述符（`/dev/fd/N`），使得需要文件参数的命令可以直接使用命令输出。

```
┌─────────────────────────────────────────────────────────┐
│                   进程替换原理                            │
│                                                         │
│  <(command) ──→ /dev/fd/63 (只读) ──→ 作为输入文件       │
│  >(command) ──→ /dev/fd/62 (只写) ──→ 作为输出文件       │
│                                                         │
│  等价于创建了一个临时的命名管道 (FIFO)                    │
└─────────────────────────────────────────────────────────┘
```

```bash
# 基本用法：将命令输出作为文件参数
diff <(ls /etc) <(ls /var)

# 等价于：
mkfifo /tmp/fifo1 /tmp/fifo2
ls /etc > /tmp/fifo1 &
ls /var > /tmp/fifo2 &
diff /tmp/fifo1 /tmp/fifo2
rm /tmp/fifo1 /tmp/fifo2

# 多路输出
ls /etc | tee >(wc -l > /tmp/count.txt) \
               >(grep conf > /tmp/conf.txt) \
               > /dev/null

# 避免子 shell 变量问题
# 管道方式（变量在子 shell 中，丢失）
echo "test" | read var
echo "$var"  # 空！

# 进程替换方式（变量在当前 shell）
read var < <(echo "test")
echo "$var"  # test
```

#### 2.2 进程替换实战

```bash
# 场景 1：对比两台服务器的已安装包
diff <(ssh server1 "dpkg -l 2>/dev/null" | awk '{print $2, $3}') \
     <(ssh server2 "dpkg -l 2>/dev/null" | awk '{print $2, $3}')

# 场景 2：对比两个目录的文件列表
diff <(find /app/v1 -type f | sort) \
     <(find /app/v2 -type f | sort)

# 场景 3：合并多个排序文件（归并排序思想）
sort -m <(sort file1.txt) <(sort file2.txt) <(sort file3.txt)

# 场景 4：同时监控多个日志文件
tail -f <(ssh server1 "tail -f /var/log/app.log") \
        <(ssh server2 "tail -f /var/log/app.log")

# 场景 5：使用 comm 找两个文件的差异
comm -23 <(sort servers_all.txt) <(sort servers_online.txt)
# 输出：离线服务器列表
```

### 3. 命名管道 (mkfifo) 与 IPC

#### 3.1 命名管道基础

命名管道（FIFO）是一种特殊的文件类型，用于不相关进程之间的通信。与匿名管道 `|` 不同，命名管道有文件系统路径，任意进程都可以读写。

```bash
# 创建命名管道
mkfifo /tmp/my_pipe

# 验证文件类型
ls -la /tmp/my_pipe
# prw-r--r-- 1 root root 0 Apr 27 10:00 /tmp/my_pipe
# 注意开头的 'p' 表示 pipe

# 写入端（阻塞直到有读者）
echo "Hello from writer" > /tmp/my_pipe &

# 读取端
cat /tmp/my_pipe
# 输出: Hello from writer

# 清理
rm /tmp/my_pipe
```

#### 3.2 命名管道的特性

```
命名管道工作流程：
                                          
  Writer 进程                    Reader 进程
  ┌──────────┐                  ┌──────────┐
  │ echo     │    ┌────────┐    │ cat      │
  │ "data" ──┼───►│ FIFO   │───►│ 读取数据 │
  │          │    │(缓冲区) │    │          │
  └──────────┘    └────────┘    └──────────┘
       │                              │
       └── 阻塞直到有读者 ────────────┘── 阻塞直到有写者

特性：
1. 数据先进先出（FIFO）
2. 数据不持久化（读完即消失）
3. 写入阻塞直到有读者
4. 读取阻塞直到有写者
5. 数据大小限制：PIPE_BUF（通常 64KB）
```

#### 3.3 命名管道实战

```bash
# 场景 1：实现简单的生产者-消费者模式
#!/bin/bash
# producer.sh — 生产者
PIPE="/tmp/data_pipe"
mkfifo "$PIPE" 2>/dev/null

for i in $(seq 1 10); do
    echo "数据包 $i: $(date +%s)"
    sleep 1
done > "$PIPE"

# consumer.sh — 消费者
PIPE="/tmp/data_pipe"
while IFS= read -r line; do
    echo "处理: $line"
done < "$PIPE"

# 场景 2：实现实时日志处理管道
#!/bin/bash
# log_processor.sh
INPUT_PIPE="/tmp/log_input"
OUTPUT_PIPE="/tmp/log_output"

mkfifo "$INPUT_PIPE" "$OUTPUT_PIPE" 2>/dev/null

# 后台启动处理管道
tail -f /var/log/syslog > "$INPUT_PIPE" &
TAIL_PID=$!

# 处理：提取 ERROR 行并计数
grep --line-buffered "ERROR" "$INPUT_PIPE" | \
    tee >(wc -l > /tmp/error_count.txt) > "$OUTPUT_PIPE" &

# 清理
trap "kill $TAIL_PID; rm -f $INPUT_PIPE $OUTPUT_PIPE" EXIT

echo "日志处理器已启动，错误日志输出到 $OUTPUT_PIPE"
echo "查看错误日志: cat $OUTPUT_PIPE"
wait

# 场景 3：多进程结果汇总
#!/bin/bash
RESULT_PIPE="/tmp/results_$$"
mkfifo "$RESULT_PIPE" 2>/dev/null
trap "rm -f $RESULT_PIPE" EXIT

# 启动多个后台检查任务，结果写入管道
check_disk()  { echo "DISK: $(df / | tail -1 | awk '{print $5}')" > "$RESULT_PIPE"; }
check_memory(){ echo "MEM: $(free | awk '/Mem:/ {printf "%.1f%%", $3/$2*100}')" > "$RESULT_PIPE"; }
check_load()  { echo "LOAD: $(uptime | awk -F'load average:' '{print $2}')" > "$RESULT_PIPE"; }

check_disk &
check_memory &
check_load &

# 读取所有结果
echo "=== 服务器巡检 ==="
for _ in 1 2 3; do
    read -r result < "$RESULT_PIPE"
    echo "$result"
done
```

### 4. 并行执行模式

#### 4.1 `&` 后台执行 + `wait`

最简单的并行方式，适合数量不多的并发任务：

```bash
#!/bin/bash
# 基本并行执行
task() {
    local server=$1
    echo "[$(date +%H:%M:%S)] 开始检查 $server"
    ssh "$server" "uptime; free -h; df -h" > "/tmp/report_${server}.txt" 2>&1
    echo "[$(date +%H:%M:%S)] 完成检查 $server"
}

# 并行启动所有任务
servers=("web01" "web02" "web03" "db01" "db02")
for server in "${servers[@]}"; do
    task "$server" &
done

# 等待所有后台任务完成
wait
echo "所有服务器检查完成"

# 带超时的 wait
wait -n  # 等待任意一个子进程完成（Bash 4.3+）
wait %1  # 等待特定的后台任务
```

#### 4.2 限制并发数

无限制的并行可能耗尽系统资源，需要控制并发数：

```bash
#!/bin/bash
# 手动实现并发池（限制并发数）
MAX_PARALLEL=5
RUNNING=0

for server in $(cat servers.txt); do
    # 等待直到有空闲槽位
    while (( RUNNING >= MAX_PARALLEL )); do
        wait -n  # 等待任意一个子进程完成
        ((RUNNING--))
    done

    # 启动后台任务
    (
        ssh "$server" "uptime" > "/tmp/${server}.txt" 2>&1
    ) &
    ((RUNNING++))
done

# 等待剩余任务
wait
echo "全部完成"
```

#### 4.3 xargs -P 并行执行

`xargs -P` 是最简单高效的并行工具，适合对大量输入执行相同命令：

```bash
# -P N : 最多 N 个并行进程
# -I {} : 占位符

# 并行 ping 检查
cat servers.txt | xargs -P 10 -I {} sh -c 'ping -c 1 -W 1 {} > /dev/null && echo "UP: {}" || echo "DOWN: {}"'

# 并行 SSH 执行命令
cat servers.txt | xargs -P 20 -I {} ssh -o ConnectTimeout=5 {} "hostname; uptime"

# 并行文件处理
find /var/log -name "*.log" -mtime +30 | xargs -P 4 gzip

# 并行下载
cat urls.txt | xargs -P 8 -I {} curl -sO {}

# 注意：xargs -P 的输出可能交错，建议重定向到文件
cat servers.txt | xargs -P 10 -I {} sh -c \
    'ssh {} "hostname; uptime" > /tmp/{}.txt 2>&1'
```

#### 4.4 GNU parallel（高级并行工具）

GNU parallel 是最强大的并行执行工具，支持远程执行、进度显示、作业调度：

```bash
# 安装
# apt install parallel 或 yum install parallel

# 基本用法
parallel echo ::: server1 server2 server3

# 从文件读取输入
parallel -j 10 ssh {} hostname :::: servers.txt

# 多个参数组合
parallel echo {1} {2} ::: A B C ::: 1 2 3
# A 1, A 2, A 3, B 1, B 2, B 3, C 1, C 2, C 3

# 进度显示
parallel --progress ssh {} hostname :::: servers.txt

# 作业日志
parallel --joblog /tmp/parallel.log ssh {} hostname :::: servers.txt

# 失败重试
parallel --retries 3 ssh {} hostname :::: servers.txt

# 限速（每秒最多 5 个新任务）
parallel --delay 0.2 -j 5 ssh {} hostname :::: servers.txt

# 远程执行（在多台服务器上并行执行）
parallel -S server1,server2,server3 echo "Hello from {}" ::: task1 task2 task3

# 使用 SSH 远程执行
parallel --sshloginfile servers.txt -j 1 hostname

# 结果以 JSON 格式输出
parallel --results /tmp/results/ --json ssh {} hostname :::: servers.txt

# 带超时
parallel --timeout 30 ssh {} "sleep 60" :::: servers.txt
```

**SRE 实战：用 parallel 并发巡检 100 台服务器**：

```bash
#!/bin/bash
# parallel_inspect.sh — 使用 GNU parallel 并发巡检服务器
set -euo pipefail

SERVERS_FILE="servers.txt"
OUTPUT_DIR="/tmp/inspect_$(date +%Y%m%d)"
MAX_PARALLEL=20

mkdir -p "$OUTPUT_DIR"

# 定义巡检函数
inspect_server() {
    local server=$1
    local output="$OUTPUT_DIR/${server}.txt"

    {
        echo "=== 服务器巡检: $server ==="
        echo "时间: $(date)"
        echo ""

        # SSH 执行巡检命令
        ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$server" bash -s << 'REMOTE'
echo "--- 系统信息 ---"
hostname
uname -r
uptime

echo "--- 内存使用 ---"
free -h

echo "--- 磁盘使用 ---"
df -h | grep -v tmpfs

echo "--- CPU 负载 ---"
top -bn1 | head -5

echo "--- 网络连接 ---"
ss -tuln | head -20

echo "--- 最近登录 ---"
last -5
REMOTE
    } > "$output" 2>&1

    if [[ $? -eq 0 ]]; then
        echo "OK: $server"
    else
        echo "FAIL: $server"
    fi
}

export -f inspect_server
export OUTPUT_DIR

# 使用 parallel 并发执行
parallel -j "$MAX_PARALLEL" \
    --progress \
    --joblog "$OUTPUT_DIR/joblog.txt" \
    --retries 2 \
    inspect_server {} :::: "$SERVERS_FILE"

# 汇总报告
echo ""
echo "=== 巡检汇总 ==="
total=$(wc -l < "$SERVERS_FILE")
success=$(grep -c "^OK" "$OUTPUT_DIR/joblog.txt" || echo 0)
fail=$(grep -c "^FAIL" "$OUTPUT_DIR/joblog.txt" || echo 0)
echo "总计: $total, 成功: $success, 失败: $fail"
echo "报告目录: $OUTPUT_DIR"
```

### 5. 文件描述符和重定向深入

#### 5.1 文件描述符基础

```
文件描述符 (File Descriptor) 是操作系统对打开文件的抽象引用：

┌─────────────────────────────────────┐
│ 标准文件描述符                       │
├──────┬──────────────────────────────┤
│ FD 0 │ stdin  (标准输入)             │
│ FD 1 │ stdout (标准输出)             │
│ FD 2 │ stderr (标准错误)             │
├──────┴──────────────────────────────┤
│ 自定义文件描述符 (3-9)               │
│ 可用于复杂的 I/O 重定向              │
└─────────────────────────────────────┘
```

```bash
# 基本重定向
command > file      # stdout 重定向到文件（覆盖）
command >> file     # stdout 追加到文件
command 2> file     # stderr 重定向到文件
command &> file     # stdout + stderr 都重定向到文件
command 2>&1        # stderr 重定向到 stdout（顺序重要！）
command > file 2>&1 # 同上，stdout 到文件，stderr 也到文件

# 重定向顺序的重要性
command 2>&1 > file  # ！！错误！stderr 到终端，stdout 到文件
command > file 2>&1  # 正确！stdout 和 stderr 都到文件

# 解释：
# 2>&1 : 将 stderr(2) 重定向到 stdout(1) 当前指向的地方
# > file : 将 stdout(1) 重定向到 file
# 如果先 2>&1 再 > file，stderr 已经指向了原来的 stdout（终端）
```

#### 5.2 自定义文件描述符

```bash
# 打开文件描述符 3 用于写入
exec 3>/tmp/output.txt
echo "写入到 FD 3" >&3
echo "另一行" >&3
exec 3>&-  # 关闭 FD 3

# 打开文件描述符 4 用于读取
exec 4</tmp/output.txt
read -r line <&4
echo "读取: $line"
exec 4<&-  # 关闭 FD 4

# 同时读写
exec 5<>/tmp/data.txt
echo "写入数据" >&5
read -r line <&5
exec 5>&-

# 保存和恢复 stdout
exec 7>&1           # 保存原始 stdout 到 FD 7
exec 1>/tmp/log.txt # stdout 重定向到文件
echo "这行写入文件"
echo "这也写入文件"
exec 1>&7           # 恢复 stdout
exec 7>&-           # 关闭 FD 7
echo "这行输出到终端"
```

#### 5.3 网络连接（/dev/tcp 和 /dev/udp）

Bash 可以通过文件描述符直接建立 TCP 连接，无需额外工具：

```bash
# TCP 端口检查
check_port() {
    local host=$1
    local port=$2
    local timeout=${3:-5}

    # 尝试建立 TCP 连接
    if timeout "$timeout" bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
        echo "OPEN: $host:$port"
        return 0
    else
        echo "CLOSED: $host:$port"
        return 1
    fi
}

# 使用示例
check_port google.com 80
check_port 192.168.1.100 22

# 批量端口扫描
scan_ports() {
    local host=$1
    local ports=(22 80 443 3306 6379 8080)

    for port in "${ports[@]}"; do
        check_port "$host" "$port" &
    done
    wait
}
scan_ports 192.168.1.100

# 简单 HTTP 请求
exec 3</dev/tcp/httpbin.org/80
echo -e "GET /ip HTTP/1.1\r\nHost: httpbin.org\r\nConnection: close\r\n\r\n" >&3
cat <&3
exec 3<&-

# SMTP 交互（调试邮件发送）
exec 3</dev/tcp/smtp.example.com/25
read -r banner <&3
echo "EHLO test" >&3
read -r response <&3
echo "QUIT" >&3
exec 3<&-
```

#### 5.4 Here Document 与 Here String

```bash
# Here Document — 多行文本输入
cat << EOF
服务器: $(hostname)
时间: $(date)
用户: $USER
EOF

# 禁止变量展开（引号包裹分隔符）
cat << 'EOF'
$HOME 不会展开
$(date) 不会执行
EOF

# 去除前导 tab（- 前缀）
cat <<-EOF
	这行前面的 tab 会被删除
	这行也是
EOF

# Here Document 用于多行命令
mysql -u root -p << SQL
CREATE DATABASE IF NOT EXISTS mydb;
USE mydb;
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100)
);
SQL

# Here Document 重定向到文件
cat << EOF > /etc/nginx/conf.d/app.conf
server {
    listen 80;
    server_name example.com;
    root /var/www/html;
}
EOF

# Here String — 单行文本输入
grep "root" <<< "$(cat /etc/passwd)"

# 读取变量
read -r first last <<< "John Doe"
echo "名: $first, 姓: $last"

# 数值比较
if (( $(wc -w <<< "$text") > 100 )); then
    echo "文本超过 100 个单词"
fi
```

### 6. 高级参数展开和模式匹配

```bash
# ===== 参数展开 =====

# 默认值
${var:-default}     # var 为空或未设置时返回 default
${var:=default}     # var 为空或未设置时赋值为 default
${var:?error_msg}   # var 为空或未设置时打印错误并退出
${var:+alternate}   # var 非空时返回 alternate

# 字符串操作
${#var}             # 字符串长度
${var:offset}       # 从 offset 开始的子串
${var:offset:length}# 从 offset 开始，长度为 length 的子串
${var#pattern}      # 删除左边最短匹配
${var##pattern}     # 删除左边最长匹配
${var%pattern}      # 删除右边最短匹配
${var%%pattern}     # 删除右边最长匹配
${var/old/new}      # 替换第一个匹配
${var//old/new}     # 替换所有匹配
${var^}             # 首字母大写
${var^^}            # 全部大写
${var,}             # 首字母小写
${var,,}            # 全部小写

# 实际应用
filepath="/var/log/nginx/access.log"

echo "${filepath##*/}"     # access.log    (文件名)
echo "${filepath%/*}"      # /var/log/nginx (目录)
echo "${filepath##*.}"     # log           (扩展名)
echo "${filepath%.log}"    # /var/log/nginx/access (去掉扩展名)

# 大小写转换（Bash 4+）
name="hello world"
echo "${name^}"     # Hello world
echo "${name^^}"    # HELLO WORLD

# 数组操作
arr=(apple banana cherry)
echo "${#arr[@]}"   # 3 (数组长度)
echo "${arr[0]}"    # apple
echo "${arr[@]:1}"  # banana cherry (从索引 1 开始)
echo "${arr[@]/a/A}" # Apple bAnAnA cherry (替换)

# ===== 模式匹配 =====

# [[ ]] 支持扩展模式匹配
str="hello_world_2026"
[[ $str == hello_* ]] && echo "匹配 hello_ 前缀"
[[ $str =~ ^[a-z]+_[a-z]+_[0-9]+$ ]] && echo "正则匹配成功"

# 提取正则匹配组（Bash 3.0+）
if [[ "2026-04-27" =~ ^([0-9]{4})-([0-9]{2})-([0-9]{2})$ ]]; then
    echo "年: ${BASH_REMATCH[1]}"  # 2026
    echo "月: ${BASH_REMATCH[2]}"  # 04
    echo "日: ${BASH_REMATCH[3]}"  # 27
fi
```

### 7. Bash 4/5 新特性

#### 7.1 mapfile / readarray

`mapfile` 将标准输入按行读入数组，比 `while read` 循环更高效：

```bash
# 基本用法：将文件读入数组
mapfile -t lines < /etc/passwd
echo "共 ${#lines[@]} 行"
echo "第一行: ${lines[0]}"

# 跳过前 N 行
mapfile -t -s 2 lines < /etc/passwd  # 跳过前 2 行

# 限制读取行数
mapfile -t -n 5 lines < /etc/passwd  # 只读 5 行

# 从命令输出读入
mapfile -t processes < <(ps aux | awk '{print $11}' | sort -u)

# 带回调函数（每行处理）
process_line() {
    printf "处理第 %d 行: %s\n" "$1" "$2"
}
mapfile -t -C process_line -c 1 lines < /etc/passwd

# 性能对比
# while read: 每次循环 fork 一次（慢）
# mapfile: 批量读入（快），适合大文件
```

#### 7.2 Coprocess（协程）

Bash 4.0 引入的协程功能，可以启动一个后台进程并与其双向通信：

```bash
# 启动协程
coproc myproc { bc -l; }

# 向协程写入
echo "2+3" >&"${myproc[1]}"

# 从协程读取
read -r result <&"${myproc[0]}"
echo "结果: $result"  # 结果: 5

# 关闭协程
exec {myproc[1]}>&-
exec {myproc[0]}<&-
wait "$myproc_PID"

# 实际应用：与 bc 交互做浮点计算
coproc calc { bc -l; }

calculate() {
    echo "$1" >&"${calc[1]}"
    read -r result <&"${calc[0]}"
    echo "$result"
}

echo "pi = $(calculate "4*a(1)")"
echo "sqrt(2) = $(calculate "sqrt(2)")"
echo "sin(45) = $(calculate "s(45*4*a(1)/180)")"

exec {calc[1]}>&-
exec {calc[0]}<&-
wait "$calc_PID"
```

#### 7.3 Nameref（nameref 变量引用）

Bash 4.3 引入的 nameref 允许通过引用操作其他变量：

```bash
# 基本用法
declare -n ref=original_var
original_var="Hello"
echo "$ref"  # Hello

ref="World"
echo "$original_var"  # World

# 函数中通过引用返回多个值
get_system_info() {
    local -n _cpu_ref=$1
    local -n _mem_ref=$2
    local -n _disk_ref=$3

    _cpu_ref=$(nproc)
    _mem_ref=$(free -g | awk '/Mem:/ {print $2}')
    _disk_ref=$(df / | tail -1 | awk '{print $5}')
}

get_system_info cpu cores mem_gb disk_pct
echo "CPU: $cpu 核, 内存: ${mem_gb}GB, 磁盘: $disk_pct"

# 安全注意：nameref 不能引用自身
# declare -n ref=ref  # 错误！
```

#### 7.4 其他 Bash 4/5 特性

```bash
# Bash 4.0: associative arrays（关联数组）
declare -A config
config[host]="localhost"
config[port]="8080"
config[timeout]="30"

for key in "${!config[@]}"; do
    echo "$key = ${config[$key]}"
done

# Bash 4.2: lastpipe（管道最后一个命令在当前 shell 执行）
shopt -s lastpipe
count=0
echo -e "1\n2\n3" | while read -r line; do
    ((count++))
done
echo "count=$count"  # 3（不是 0）

# Bash 4.3: wait -n（等待任意一个子进程）
for i in {1..5}; do
    sleep $((i * 2)) &
done
wait -n  # 等待第一个完成的子进程
echo "第一个任务完成了"

# Bash 4.4: ${var@Q}（引号转义）
var="it's a test"
echo "${var@Q}"  # 'it's a test'

# Bash 5.0: EPOCHSECONDS（秒级时间戳）
echo "$EPOCHSECONDS"  # 1682592000

# Bash 5.1: ${var,} ${var,,} 首字母/全部小写（已在前面介绍）
```

### 8. 性能优化技巧

#### 8.1 避免不必要的子 shell

```bash
# 慢：每次 $( ) 都 fork 子进程
for i in $(seq 1 1000); do
    echo "$i"
done

# 快：使用 Bash 内置算术
for ((i=1; i<=1000; i++)); do
    echo "$i"
done

# 慢：外部命令
result=$(expr $a + $b)

# 快：内置算术
result=$((a + b))

# 慢：cat file | grep（无用的 cat）
cat /etc/passwd | grep root

# 快：直接重定向
grep root /etc/passwd
```

#### 8.2 减少外部命令调用

```bash
# 慢：使用外部命令
echo "$var" | grep -q "pattern"       # fork grep
echo "$var" | sed 's/old/new/'        # fork sed
len=$(echo -n "$var" | wc -c)         # fork wc

# 快：使用 Bash 内置功能
[[ "$var" == *pattern* ]]              # 内置模式匹配
new="${var/old/new}"                    # 内置参数替换
len=${#var}                            # 内置长度计算

# 慢：使用外部命令排序
echo -e "c\na\nb" | sort

# 快：如果只是比较，用内置
[[ "$a" < "$b" ]] && echo "a < b"
```

#### 8.3 批量操作

```bash
# 慢：逐行处理大文件
while read -r line; do
    process_line "$line"
done < big_file.txt

# 快：使用 awk 批量处理
awk '{process_here}' big_file.txt

# 慢：循环中多次 SSH
for server in $(cat servers.txt); do
    ssh "$server" "uptime"
done

# 快：并行 SSH
xargs -P 20 -I {} ssh {} "uptime" < servers.txt

# 慢：多次写文件
for item in "${list[@]}"; do
    echo "$item" >> output.txt
done

# 快：一次性写入
printf '%s\n' "${list[@]}" > output.txt
```

#### 8.4 性能测试示例

```bash
#!/bin/bash
# 性能对比测试

echo "=== 测试 1: seq vs {1..1000} ==="
time (for i in $(seq 1 10000); do :; done)
time (for i in {1..10000}; do :; done)
time (for ((i=1; i<=10000; i++)); do :; done)

echo ""
echo "=== 测试 2: cat file | grep vs grep file ==="
dd if=/dev/urandom bs=1M count=10 2>/dev/null | base64 > /tmp/bigfile.txt
time (cat /tmp/bigfile.txt | grep "AAA" | wc -l)
time (grep -c "AAA" /tmp/bigfile.txt)

echo ""
echo "=== 测试 3: echo | wc -c vs ${#var} ==="
var="Hello, World! This is a test string."
time (for i in {1..10000}; do echo -n "$var" | wc -c; done)
time (for i in {1..10000}; do len=${#var}; done)
```

### 9. 脚本打包和分发

#### 9.1 Self-Extracting Archive

```bash
#!/bin/bash
# create_self_extracting.sh — 创建自解压安装包

PACKAGE_NAME="myapp"
VERSION="1.0.0"
OUTPUT="${PACKAGE_NAME}-${VERSION}-installer.sh"

# 1. 打包应用文件
tar czf /tmp/app_payload.tar.gz \
    -C /opt/myapp .

# 2. 创建自解压脚本
cat > "$OUTPUT" << 'HEADER'
#!/bin/bash
# Self-extracting installer
set -euo pipefail

echo "================================"
echo " 安装程序 v__VERSION__"
echo "================================"

# 查找 payload 位置
ARCHIVE=$(awk '/^__ARCHIVE__$/{print NR + 1; exit 0}' "$0")

# 解压到目标目录
INSTALL_DIR="/opt/__PACKAGE_NAME__"
mkdir -p "$INSTALL_DIR"
tail -n +"$ARCHIVE" "$0" | tar xz -C "$INSTALL_DIR"

echo "安装完成: $INSTALL_DIR"
echo "启动: systemctl start __PACKAGE_NAME__"
exit 0

__ARCHIVE__
HEADER

# 替换变量
sed -i "s/__VERSION__/$VERSION/g" "$OUTPUT"
sed -i "s/__PACKAGE_NAME__/$PACKAGE_NAME/g" "$OUTPUT"

# 3. 追加 payload
cat /tmp/app_payload.tar.gz >> "$OUTPUT"
chmod +x "$OUTPUT"

echo "自解压包已创建: $OUTPUT"
echo "使用方法: ./$OUTPUT"
```

#### 9.2 脚本分发最佳实践

```bash
# 1. 添加 shebang 和严格模式
#!/usr/bin/env bash
set -euo pipefail

# 2. 添加版本信息和帮助
VERSION="1.0.0"
show_help() {
    cat << EOF
用法: $(basename "$0") [选项]

选项:
  -h, --help     显示帮助
  -v, --version  显示版本
  -c, --config   指定配置文件
EOF
}

# 3. 依赖检查
check_dependencies() {
    local deps=(curl jq rsync)
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            echo "错误: 缺少依赖 $dep" >&2
            echo "请安装: apt install $dep 或 yum install $dep"
            exit 1
        fi
    done
}

# 4. 最低 Bash 版本检查
if ((BASH_VERSINFO[0] < 4)); then
    echo "错误: 需要 Bash 4.0+，当前版本: ${BASH_VERSION}" >&2
    exit 1
fi
```

---

## 💻 SRE 实战场景

### 场景 1：用 parallel 加速 100 台服务器并发巡检

```bash
#!/bin/bash
# parallel_health_check.sh — 并发健康检查
set -euo pipefail

SERVERS_FILE="${1:-servers.txt}"
MAX_PARALLEL=25
OUTPUT_DIR="/tmp/health_$(date +%Y%m%d_%H%M%S)"
TIMEOUT=15

mkdir -p "$OUTPUT_DIR"

# 巡检函数（导出给 parallel 使用）
check_server() {
    local server=$1
    local result_file="$OUTPUT_DIR/${server}.json"
    local status="UNKNOWN"
    local details=""

    # SSH 执行检查
    if details=$(ssh -o ConnectTimeout="$TIMEOUT" \
                     -o StrictHostKeyChecking=no \
                     "$server" bash -s << 'CHECK' 2>&1
hostname=$(hostname)
uptime=$(uptime -p)
load=$(cat /proc/loadavg | awk '{print $1}')
mem_total=$(free -m | awk '/Mem:/ {print $2}')
mem_used=$(free -m | awk '/Mem:/ {print $3}')
mem_pct=$((mem_used * 100 / mem_total))
disk_pct=$(df / | tail -1 | awk '{print $5}' | tr -d '%')

echo "{\"host\":\"$hostname\",\"uptime\":\"$uptime\",\"load\":$load,\"mem_pct\":$mem_pct,\"disk_pct\":$disk_pct}"
CHECK
    ); then
        status="OK"
    else
        status="FAIL"
        details="SSH 连接失败"
    fi

    # 输出 JSON 结果
    cat > "$result_file" << EOF
{
    "server": "$server",
    "status": "$status",
    "time": "$(date -Iseconds)",
    "details": $details
}
EOF
    echo "$status: $server"
}

export -f check_server
export OUTPUT_DIR TIMEOUT

# 并发执行
parallel -j "$MAX_PARALLEL" \
    --progress \
    --joblog "$OUTPUT_DIR/joblog.txt" \
    --timeout "$((TIMEOUT * 2))" \
    check_server {} :::: "$SERVERS_FILE"

# 汇总报告
echo ""
echo "=============================="
echo " 健康检查汇总报告"
echo "=============================="
total=$(wc -l < "$SERVERS_FILE")
ok_count=$(find "$OUTPUT_DIR" -name "*.json" -exec grep -l '"OK"' {} \; | wc -l)
fail_count=$((total - ok_count))
echo "总计: $total | 正常: $ok_count | 异常: $fail_count"
echo "详细报告: $OUTPUT_DIR/"
```

### 场景 2：用命名管道实现实时日志处理管道

```bash
#!/bin/bash
# realtime_log_pipeline.sh — 实时日志处理管道
set -euo pipefail

LOG_FILE="${1:-/var/log/syslog}"
PIPE_DIR="/tmp/log_pipeline_$$"
mkdir -p "$PIPE_DIR"

# 创建命名管道
mkfifo "$PIPE_DIR/input"
mkfifo "$PIPE_DIR/errors"
mkfifo "$PIPE_DIR/stats"

cleanup() {
    rm -rf "$PIPE_DIR"
    jobs -p | xargs -r kill 2>/dev/null
}
trap cleanup EXIT

# 阶段 1: 日志输入（tail -f）
tail -f "$LOG_FILE" > "$PIPE_DIR/input" &
TAIL_PID=$!

# 阶段 2: 过滤 ERROR 行
grep --line-buffered -i "error\|critical\|fatal" < "$PIPE_DIR/input" > "$PIPE_DIR/errors" &
GREP_PID=$!

# 阶段 3: 统计错误类型
awk '{print $NF}' < "$PIPE_DIR/errors" | \
    sort | uniq -c | sort -rn > "$PIPE_DIR/stats" &
STATS_PID=$!

# 阶段 4: 实时显示
echo "=== 实时日志监控 ==="
echo "日志文件: $LOG_FILE"
echo "按 Ctrl+C 停止"
echo ""

# 使用 tee 同时输出到终端和文件
tail -f "$PIPE_DIR/errors" | while IFS= read -r line; do
    echo "[$(date +%H:%M:%S)] $line"
done
```

### 场景 3：用文件描述符实现 TCP 连接检查

```bash
#!/bin/bash
# tcp_check.sh — TCP 端口检查工具
set -euo pipefail

check_tcp() {
    local host=$1
    local port=$2
    local timeout=${3:-3}

    # 使用 /dev/tcp 检查
    (echo > "/dev/tcp/$host/$port") 2>/dev/null
    return $?
}

batch_check() {
    local targets=(
        "web01:80"
        "web01:443"
        "db01:3306"
        "cache01:6379"
        "mq01:5672"
    )

    echo "=== TCP 端口批量检查 ==="
    printf "%-15s %-8s %s\n" "主机" "端口" "状态"
    printf "%-15s %-8s %s\n" "----" "----" "----"

    for target in "${targets[@]}"; do
        local host="${target%%:*}"
        local port="${target##*:}"

        check_tcp "$host" "$port" &
    done | sort

    wait
}

# HTTP 健康检查（使用 /dev/tcp）
http_check() {
    local host=$1
    local port=${2:-80}
    local path=${3:-/health}

    exec 3</dev/tcp/"$host"/"$port"
    echo -e "GET $path HTTP/1.0\r\nHost: $host\r\n\r\n" >&3

    local status_line
    read -r status_line <&3
    local status_code
    status_code=$(echo "$status_line" | awk '{print $2}')

    exec 3<&-

    if [[ "$status_code" == "200" ]]; then
        echo "OK: $host:$port$path ($status_code)"
    else
        echo "FAIL: $host:$port$path ($status_code)"
    fi
}

# 使用示例
http_check "example.com" 80 "/"
```

---

## 🧪 练习题

### 练习 1：子 Shell 与命令分组

```bash
# 预测以下代码的输出
x=1
(x=2; echo "A: $x")
echo "B: $x"
{ x=3; echo "C: $x"; }
echo "D: $x"
```

<details>
<summary>答案</summary>

```
A: 2    （子 shell 中修改，不影响父 shell）
B: 1    （父 shell 的 x 仍然是 1）
C: 3    （命令分组在当前 shell 中执行）
D: 3    （x 已被修改为 3）
```
</details>

### 练习 2：进程替换

```bash
# 使用进程替换比较两个目录的文件列表
# 列出 /etc 中有但 /usr/etc 中没有的文件
```

<details>
<summary>答案</summary>

```bash
comm -23 <(ls /etc | sort) <(ls /usr/etc 2>/dev/null | sort)

# 或者使用 diff
diff <(ls /etc | sort) <(ls /usr/etc 2>/dev/null | sort) | grep "^<"
```
</details>

### 练习 3：并行执行

```bash
# 编写脚本，使用 xargs -P 并行 ping 检查 20 台服务器
# 要求：限制并发数为 10，超时 3 秒，输出 UP/DOWN 状态
```

<details>
<summary>答案</summary>

```bash
#!/bin/bash
SERVERS_FILE="servers.txt"

ping_check() {
    local host=$1
    if ping -c 1 -W 3 "$host" &>/dev/null; then
        echo "UP: $host"
    else
        echo "DOWN: $host"
    fi
}

export -f ping_check
xargs -P 10 -I {} bash -c 'ping_check "$@"' _ {} < "$SERVERS_FILE" | sort
```
</details>

### 练习 4：命名管道

```bash
# 使用命名管道实现一个简单的任务队列
# 生产者生成任务，消费者处理任务
```

<details>
<summary>答案</summary>

```bash
#!/bin/bash
PIPE="/tmp/task_queue"
mkfifo "$PIPE" 2>/dev/null
trap "rm -f $PIPE" EXIT

# 消费者（后台运行）
(
    while IFS= read -r task; do
        echo "[消费者] 处理任务: $task"
        sleep 1  # 模拟处理
    done < "$PIPE"
) &
CONSUMER_PID=$!

# 生产者
for i in {1..10}; do
    echo "任务-$i" > "$PIPE"
    echo "[生产者] 提交任务-$i"
done

wait $CONSUMER_PID
```
</details>

### 练习 5：文件描述符

```bash
# 使用文件描述符实现一个简单的日志函数
# 同时输出到终端和文件
```

<details>
<summary>答案</summary>

```bash
#!/bin/bash
LOG_FILE="/var/log/myapp.log"

# 保存原始 stdout
exec 7>&1

# 打开日志文件（追加模式）
exec 8>>"$LOG_FILE"

log() {
    local level=$1; shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"

    # 同时输出到终端(FD7)和文件(FD8)
    echo "$msg" | tee -a /dev/fd/8 >&7
}

# 使用
log INFO "应用启动"
log ERROR "发生错误"

# 清理
exec 7>&-
exec 8>&-
```
</details>

---

## 🎯 面试题精选

### 1. `( )` 和 `{ }` 有什么区别？

**参考答案**：

- `( )` 创建子 shell 执行，变量修改不影响父 shell，有 fork 开销
- `{ }` 在当前 shell 执行，变量修改影响当前 shell，无 fork 开销
- `{ }` 要求 `{` 后有空格，`}` 前有分号
- 适用场景：`( )` 用于隔离操作，`{ }` 用于批量重定向

### 2. 什么是进程替换？与管道有什么区别？

**参考答案**：

进程替换 `<( )` 将命令输出映射为文件描述符（`/dev/fd/N`），可作为文件参数传递给命令。

与管道的区别：
- 管道 `|` 只能连接两个命令的 stdout->stdin
- 进程替换可以同时使用多个命令输出作为参数（如 `diff <(cmd1) <(cmd2)`）
- 管道中的变量在子 shell 中丢失，进程替换不会

### 3. 如何实现 Bash 脚本的并行执行？有哪些方式？

**参考答案**：

1. `&` + `wait`：最简单，适合少量任务
2. `xargs -P N`：简单高效，适合批量执行相同命令
3. `GNU parallel`：最强大，支持远程执行、进度显示、作业日志
4. 手动并发池：控制 `RUNNING` 计数器 + `wait -n`

### 4. 命名管道有什么用途？

**参考答案**：

命名管道（FIFO）用于不相关进程之间的通信：
- 生产者-消费者模式
- 实时日志处理管道
- 多进程结果汇总
- 进程间数据传递

特点：数据先进先出、不持久化、读写阻塞。

### 5. 重定向 `2>&1` 和 `&>2` 有什么区别？

**参考答案**：

- `2>&1`：将 stderr(2) 重定向到 stdout(1) 当前指向的地方
- `&>file`：将 stdout 和 stderr 都重定向到 file（等价于 `>file 2>&1`）
- `command > file 2>&1`：stdout 和 stderr 都到 file
- `command 2>&1 > file`：stderr 到终端，stdout 到 file（注意顺序！）

### 6. mapfile 比 while read 循环好在哪里？

**参考答案**：

- `mapfile` 是 Bash 内置命令，直接将输入按行读入数组，没有子 shell 开销
- `while read` 需要管道或重定向，在管道中会在子 shell 中执行
- `mapfile` 支持跳过行（`-s`）、限制行数（`-n`）、回调函数（`-C`）
- 大文件场景下 `mapfile` 性能更好

### 7. 如何优化 Bash 脚本的性能？

**参考答案**：

1. 避免不必要的子 shell：用 `{ }` 替代 `( )`，用内置命令替代外部命令
2. 减少 fork：用 `${var/old/new}` 替代 `echo $var | sed`，用 `[[ ]]` 替代 `[ ]`
3. 批量操作：用 `printf` 一次性写入替代循环 `echo >>`，用 `awk` 替代 `while read + grep`
4. 并行执行：用 `xargs -P` 或 `parallel` 替代顺序循环
5. 使用 `mapfile` 替代 `while read` 循环

### 8. 如何在 Bash 中建立 TCP 连接？

**参考答案**：

使用 `/dev/tcp/host/port` 伪文件系统：
```bash
exec 3</dev/tcp/example.com/80
echo -e "GET / HTTP/1.0\r\nHost: example.com\r\n\r\n" >&3
cat <&3
exec 3<&-
```

需要编译 Bash 时启用 `--enable-net-redirections`。

---

## 📚 深入阅读

- [Bash Hackers Wiki](https://wiki.bash-hackers.org/) -- 深度 Bash 知识库
- [Advanced Bash-Scripting Guide](https://tldp.org/LDP/abs/htm/) -- 经典 Bash 教程
- [Greg's Wiki](http://mywiki.wooledge.org/) -- Bash 最佳实践
- [ShellCheck](https://www.shellcheck.net/) -- Bash 脚本静态分析工具
- [GNU Parallel Tutorial](https://www.gnu.org/software/parallel/tutorial.html) -- parallel 官方教程
- [Bash Reference Manual](https://www.gnu.org/software/bash/manual/bash.html) -- Bash 官方手册
- [Bash 5 Changelog](https://ftp.gnu.org/gnu/bash/) -- Bash 版本变更日志

---

## ✅ 自检清单

- [ ] 理解 `( )` 和 `{ }` 的区别：子 shell vs 当前 shell
- [ ] 掌握进程替换 `<( )` 和 `>( )` 的原理和用法
- [ ] 能使用 `mkfifo` 创建命名管道并实现 IPC
- [ ] 掌握 `&` + `wait`、`xargs -P`、`GNU parallel` 三种并行模式
- [ ] 理解文件描述符的概念，能自定义 FD 进行重定向
- [ ] 掌握 `2>&1` 的正确用法和顺序
- [ ] 了解 Bash 4/5 新特性：mapfile、coprocess、nameref、关联数组
- [ ] 能使用 `/dev/tcp` 进行 TCP 连接检查
- [ ] 掌握 Here Document 和 Here String 的用法
- [ ] 了解性能优化技巧：减少 fork、使用内置命令、批量操作

---

*由 SRE 学习计划生成 | 2026-04-27*
