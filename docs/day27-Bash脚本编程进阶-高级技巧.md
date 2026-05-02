# Day 27: Bash 脚本编程进阶 — 高级技巧

> 📅 日期：2026-04-25
> 📖 学习主题：Bash 脚本编程进阶 — 高级技巧
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 27 的学习后，你应该掌握：
- 掌握 Bash 函数的高级用法（局部变量、返回值、命名参数）
- 理解进程替换（Process Substitution）的原理与应用
- 掌握 Here-Document 和 Here-String 的高级技巧
- 熟练使用 `eval`、`declare`、`printf` 等高级内置命令
- 能够编写生产级 Bash 脚本（参数解析、菜单、进度条）

---

## 📖 底层原理详解

### 1. Bash 函数进阶

#### 1.1 函数基础与作用域

```bash
# 基本函数定义
my_function() {
    echo "Hello from function"
}

# 另一种定义方式（等价）
function my_function() {
    echo "Same thing"
}

# 参数传递（无括号！）
greet() {
    local name=$1        # 第一个参数
    local greeting=$2    # 第二个参数
    echo "$greeting, $name!"
}
greet "Alice" "Good morning"
# 输出: Good morning, Alice!
```

**参数变量**：
| 变量 | 含义 |
|------|------|
| `$0` | 脚本/函数名 |
| `$1` - `$9` | 第 1-9 个参数 |
| `${10}` | 第 10 个参数（需花括号） |
| `$#` | 参数个数 |
| `$@` | 所有参数（独立词） |
| `$*` | 所有参数（单个词） |
| `$?` | 上一条命令退出码 |

#### 1.2 返回值与局部变量

```bash
# Bash 函数返回值是退出码（0-255），不是字符串！
check_disk() {
    local usage=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
    if [[ $usage -gt 90 ]]; then
        echo "磁盘使用率: ${usage}%"
        return 1    # 异常退出码
    else
        echo "磁盘使用率: ${usage}%"
        return 0    # 正常
    fi
}

# 调用
if check_disk; then
    echo "✅ 磁盘正常"
else
    echo "❌ 磁盘告警"
fi

# local 关键字（限制变量作用域）
counter_test() {
    local count=0    # 局部变量
    count=5
    echo "函数内: $count"
}
count=10
counter_test
echo "函数外: $count"    # 仍然是 10
```

#### 1.3 命名参数模拟

Bash 不支持命名参数，但可以通过 `shift` 和模式匹配模拟：

```bash
deploy() {
    local env="staging"    # 默认值
    local version="latest"
    local dry_run=false

    # 解析命名参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)     env="$2"; shift 2 ;;
            --version) version="$2"; shift 2 ;;
            --dry-run) dry_run=true; shift ;;
            *) echo "未知参数: $1"; return 1 ;;
        esac
    done

    echo "部署: env=$env, version=$version, dry_run=$dry_run"
}

deploy --env production --version v2.1.0 --dry-run
```

### 2. 进程替换（Process Substitution）

**原理**：`<(command)` 创建一个包含命令输出的临时文件描述符（`/dev/fd/N`），可以作为文件参数传递给其他命令。

```bash
# 比较两个命令的输出
diff <(ls /etc) <(ls /var)

# 同时读取两个排序文件的交集
comm <(sort file1.txt) <(sort file2.txt)

# 替代管道，避免子 shell 问题
# 管道中的变量在子 shell 中，外部不可见
echo "test" | read var; echo "$var"    # 空！

# 进程替换中变量在父 shell
read var < <(echo "test"); echo "$var" # test ✅

# 多路输出（tee 到多个进程）
ls /etc | tee >(wc -l > /tmp/count) >(grep conf > /tmp/conf) > /dev/null
```

**实际应用 — 日志对比**：
```bash
# 对比两台服务器的已安装包
diff <(ssh server1 "dpkg -l" 2>/dev/null) \
     <(ssh server2 "dpkg -l" 2>/dev/null)
```

### 3. Here-Document 与 Here-String

#### 3.1 Here-Document

```bash
# 基本用法
cat << EOF
Hello, $USER
Today is $(date +%Y-%m-%d)
EOF

# 禁止变量展开（引号包裹分隔符）
cat << 'EOF'
$HOME 不会被展开
$(date) 不会被执行
EOF

# 去除前导制表符（- 前缀）
cat <<-'EOF'
	这行前面的 tab 会被删除
	这行也是
EOF

# 重定向到文件
cat << EOF > /tmp/config.yaml
server:
  host: 0.0.0.0
  port: 8080
  debug: false
EOF
```

#### 3.2 Here-String

```bash
# <<< 将字符串作为标准输入
grep "root" <<< "$(cat /etc/passwd)"

# 传递给 read
read -r host port <<< "192.168.1.100:8080"
echo "Host: $host, Port: $port"

# 传递给 while
while IFS=: read -r user pass uid gid; do
    echo "用户: $user, UID: $uid"
done <<< "root:x:0:0"
```

### 4. printf 格式化输出

```bash
# 基本用法（类似 C 的 printf）
printf "名称: %-15s 大小: %8d MB\n" "database" 2048
# 输出: 名称: database        大小:     2048 MB

# 常用格式符
printf "%s\n" "字符串"        # 字符串
printf "%d\n" 42             # 整数
printf "%f\n" 3.14           # 浮点数
printf "%x\n" 255            # 十六进制 (ff)
printf "%o\n" 255            # 八进制 (377)

# 宽度与对齐
printf "|%-10s|%10s|\n" "左对齐" "右对齐"
# |左对齐      |     右对齐|

# 转义序列
printf "行1\n行2\n"          # \n 换行
printf "Tab\there\n"         # \t 制表符
printf "颜色: \033[31m红色\033[0m\n"
```

### 5. eval 命令（谨慎使用）

```bash
# eval 将字符串作为命令执行
cmd="ls -la /tmp"
eval $cmd

# 动态变量名
var_prefix="SERVER"
for i in 1 2 3; do
    varname="${var_prefix}_${i}"
    eval "${varname}=\"server${i}.example.com\""
done

echo "$SERVER_1"    # server1.example.com
echo "$SERVER_2"    # server2.example.com
echo "$SERVER_3"    # server3.example.com
```

**⚠️ 安全警告**：`eval` 会执行任意代码，如果输入来自用户，可能导致命令注入。永远不要对未信任的输入使用 `eval`。

---

## 💻 SRE 实战场景

### 场景 1：通用参数解析框架

```bash
#!/bin/bash
# 生产脚本的标准参数解析模板
set -euo pipefail

# 默认配置
declare -A config=(
    [host]="localhost"
    [port]="8080"
    [timeout]="30"
    [verbose]="false"
    [config_file]=""
)

usage() {
    cat << EOF
用法: $(basename "$0") [选项]

选项:
  -h, --host HOST        目标主机 (默认: localhost)
  -p, --port PORT        目标端口 (默认: 8080)
  -t, --timeout SECS     超时秒数 (默认: 30)
  -c, --config FILE      配置文件路径
  -v, --verbose          详细输出
  --help                 显示帮助
  --version              显示版本

示例:
  $(basename "$0") -h 192.168.1.100 -p 9090 -t 60
  $(basename "$0") --config /etc/app.conf --verbose
EOF
}

VERSION="1.0.0"

# 参数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)     config[host]="$2"; shift 2 ;;
        -p|--port)     config[port]="$2"; shift 2 ;;
        -t|--timeout)  config[timeout]="$2"; shift 2 ;;
        -c|--config)   config[config_file]="$2"; shift 2 ;;
        -v|--verbose)  config[verbose]="true"; shift ;;
        --help)        usage; exit 0 ;;
        --version)     echo "$VERSION"; exit 0 ;;
        *)
            echo "❌ 未知参数: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

# 加载配置文件
if [[ -n "${config[config_file]}" ]]; then
    if [[ -f "${config[config_file]}" ]]; then
        echo "加载配置: ${config[config_file]}"
        source "${config[config_file]}"
    else
        echo "❌ 配置文件不存在: ${config[config_file]}" >&2
        exit 1
    fi
fi

# 主逻辑
if [[ "${config[verbose]}" == "true" ]]; then
    echo "详细模式已启用"
    echo "配置:"
    for key in "${!config[@]}"; do
        echo "  $key = ${config[$key]}"
    done
fi

echo "连接到 ${config[host]}:${config[port]} (超时: ${config[timeout]}s)"
```

### 场景 2：进度条实现

```bash
#!/bin/bash
# progress_bar.sh — 带进度条的备份脚本

progress_bar() {
    local current=$1
    local total=$2
    local width=40

    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))

    printf "\r["
    printf "%${filled}s" '' | tr ' ' '█'
    printf "%${empty}s" '' | tr ' ' '░'
    printf "] %3d%% (%d/%d)" "$percent" "$current" "$total"
}

# 模拟长任务
total_files=50
for ((i=1; i<=total_files; i++)); do
    progress_bar "$i" "$total_files"
    sleep 0.1  # 模拟处理时间
done
echo ""  # 换行
echo "✅ 所有文件处理完成"
```

### 场景 3：交互式菜单

```bash
#!/bin/bash
# menu.sh — 运维交互式菜单

SRE_MENU() {
    local choice
    while true; do
        clear
        cat << 'EOF'
╔═══════════════════════════════════════╗
║       SRE 运维工具箱 v1.0             ║
╠═══════════════════════════════════════╣
║  1. 查看系统负载                      ║
║  2. 查看磁盘使用                      ║
║  3. 查看内存使用                      ║
║  4. 查看网络状态                      ║
║  5. 查看服务状态                      ║
║  6. 清理日志                          ║
║  7. 查看最近登录                      ║
║  0. 退出                              ║
╚═══════════════════════════════════════╝
EOF

        read -rp "请选择 [0-7]: " choice

        case $choice in
            1) uptime; read -rp "按回车继续..." ;;
            2) df -h; read -rp "按回车继续..." ;;
            3) free -h; read -rp "按回车继续..." ;;
            4) ss -tuln; read -rp "按回车继续..." ;;
            5)
                for svc in nginx mysql docker ssh; do
                    status=$(systemctl is-active "$svc" 2>/dev/null || echo "not found")
                    printf "  %-15s %s\n" "$svc" "$status"
                done
                read -rp "按回车继续..."
                ;;
            6)
                read -rp "确认清理 /var/log 中的旧日志? (y/N): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    find /var/log -name "*.gz" -mtime +30 -delete -print
                    echo "清理完成"
                fi
                read -rp "按回车继续..."
                ;;
            7) last -20; read -rp "按回车继续..." ;;
            0) echo "再见！"; exit 0 ;;
            *) echo "无效选择"; sleep 1 ;;
        esac
    done
}

SRE_MENU
```

---

## 🧪 练习题

### 练习 1：函数返回多个值
```bash
# Bash 函数只能返回退出码，如何返回多个值？
# 实现 get_system_info 函数，返回 CPU 核数、总内存 GB、磁盘使用率
```

<details>
<summary>答案</summary>

```bash
get_system_info() {
    local cpu_cores=$(nproc)
    local mem_gb=$(free -g | awk '/Mem:/ {print $2}')
    local disk_pct=$(df / | tail -1 | awk '{print $5}')

    # 通过全局变量返回
    INFO_CPU=$cpu_cores
    INFO_MEM=$mem_gb
    INFO_DISK=$disk_pct
}

get_system_info
echo "CPU: $INFO_CPU 核, 内存: $INFO_MEM GB, 磁盘: $INFO_DISK"
```
</details>

### 练习 2：动态函数调用
```bash
# 实现：根据输入的命令名动态调用对应函数
# 如输入 "start" 调用 start_service，输入 "stop" 调用 stop_service
```

<details>
<summary>答案</summary>

```bash
start_service() { echo "启动服务..."; }
stop_service()  { echo "停止服务..."; }
restart_service() { echo "重启服务..."; }

action="${1:-}"
if declare -f "${action}_service" >/dev/null; then
    "${action}_service"
else
    echo "未知操作: $action"
    echo "可用操作: start stop restart"
    exit 1
fi
```
</details>

---

## 📚 扩展阅读

- [Bash Hackers Wiki](https://wiki.bash-hackers.org/) — 深度 Bash 知识
- [Advanced Bash-Scripting Guide](https://tldp.org/LDP/abs/htm/) — 经典 Bash 教程
- [Greg's Wiki](http://mywiki.wooledge.org/) — Bash 最佳实践
- [ShellCheck](https://www.shellcheck.net/) — Bash 脚本静态分析工具

---

*由 SRE 学习计划自动生成 | 2026-04-25*
*Generated by Hermes Agent with review*
