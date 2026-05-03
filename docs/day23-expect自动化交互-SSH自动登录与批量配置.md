# Day 23: expect 自动化交互 — SSH 自动登录/批量配置

> 📅 日期：2026-04-25
> 📖 学习主题：expect 自动化交互 — SSH 自动登录/批量配置
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 22 脚本调试与信号处理

## 🎯 学习目标

完成 Day 23 的学习后，你应该掌握：
- 理解 expect 的工作原理（基于 Tcl 的自动化交互框架）及其内部机制
- 掌握 `spawn`、`expect`、`send`、`interact`、`set timeout` 等核心命令的高级用法
- 能够编写复杂的 SSH 自动登录、批量配置、网络设备管理脚本
- 掌握模式匹配（精确匹配、通配符、正则、`-re` 标志）和超时/错误处理机制
- 了解 expect 的安全风险和现代替代方案（sshpass、paramiko、Ansible）
- 在 SRE 实际工作中合理选择 expect 与现代自动化工具

---

## 📖 核心知识点

### 1. expect 工具原理

#### 1.1 什么是 expect

expect 由 Don Libes 于 1990 年创建，是基于 **Tcl (Tool Command Language)** 的自动化交互工具。它的核心思想是**模式匹配驱动的自动化交互** -- 程序输出什么，expect 就响应什么，完全模拟人类操作终端的行为。

**为什么需要 expect？**

在 SRE 日常工作中，我们经常遇到需要交互式输入的场景：
- SSH 首次连接时的指纹确认（`Are you sure you want to continue connecting?`）
- 密码认证（`password:` 提示）
- `passwd` 命令修改密码
- `sudo` 密码输入
- FTP/SFTP 登录
- 网络设备（交换机/路由器）的 telnet/SSH 配置
- 数据库客户端交互（MySQL、PostgreSQL 命令行）
- 一些老旧系统的管理界面

这些场景的共同特点是：程序会等待用户输入，然后根据输入继续执行。expect 正是为了解决这类问题而生的。

#### 1.2 expect 的架构与工作原理

```
┌─────────────────────────────────────────────────────────┐
│                    expect 进程                           │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │ Tcl 解释器│───>│ 模式匹配  │───>│ 动作执行引擎     │  │
│  │ (脚本解析)│    │ 引擎      │    │ (send/interact)  │  │
│  └──────────┘    └──────────┘    └──────────────────┘  │
│       │               │                    │            │
│       v               v                    v            │
│  ┌──────────────────────────────────────────────────┐  │
│  │              伪终端 (PTY) 管理层                   │  │
│  │  /dev/ptmx (主端)  <──>  /dev/pts/N (从端)       │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                               │
└─────────────────────────┼───────────────────────────────┘
                          │
                          v
┌─────────────────────────────────────────────────────────┐
│                  被控制的子进程                           │
│  (ssh / telnet / ftp / passwd / mysql / 任何交互程序)   │
└─────────────────────────────────────────────────────────┘
```

**工作流程详解**：

```
1. spawn 启动子进程
   ↓
2. 子进程连接到伪终端 (PTY)
   ↓
3. 子进程产生输出（如 "password:"）
   ↓
4. expect 从 PTY 读取输出
   ↓
5. 将输出与 expect 模式列表逐一匹配
   ↓
6a. 匹配成功 ──> send 发送响应到 PTY ──> 子进程接收输入 ──> 回到步骤 3
6b. 匹配超时 ──> 执行 timeout 处理块
6c. 匹配 eof   ──> 子进程已退出
```

**关键概念**：

| 概念 | 说明 |
|------|------|
| **伪终端 (PTY)** | expect 通过 PTY 与子进程通信，模拟真实终端环境。子进程认为自己在与真实用户交互 |
| **模式匹配** | expect 的核心机制，使用 glob 风格或正则表达式匹配程序输出 |
| **超时控制** | 默认超时 10 秒，可通过 `set timeout` 调整。超时后执行 timeout 块 |
| **缓冲区** | expect 维护一个输出缓冲区，匹配时从缓冲区中查找模式 |
| **expect_out** | 匹配成功后，匹配内容存储在 `expect_out` 数组中供后续使用 |

#### 1.3 Tcl 语言基础

expect 脚本使用 Tcl 语法，以下是必须掌握的基础：

```tcl
# 变量设置
set hostname "web01"
set port 22

# 变量引用（使用 $）
puts $hostname

# 字符串拼接
set greeting "Hello, $hostname"

# 数组
set servers(0) "web01"
set servers(1) "web02"

# 条件判断
if {$port == 22} {
    puts "SSH port"
} else {
    puts "Other port"
}

# 循环
foreach host {web01 web02 db01} {
    puts "Processing $host"
}

# 命令替换（使用方括号）
set current_time [exec date]

# 过程（函数）
proc connect_host {host user pass} {
    spawn ssh $user@$host
    expect "password:"
    send "$pass\r"
}

# 注释
# 这是单行注释
;# 这也是注释（行尾风格）
```

#### 1.4 expect 的演进历史

| 年份 | 版本 | 里程碑 |
|------|------|--------|
| 1990 | expect 1.0 | Don Libes 在 NIST 创建 |
| 1994 | expect 5.0 | 重大改进，支持更多 Tcl 特性 |
| 1999 | expect 5.31 | 加入 libexpect 库 |
| 2008 | expect 5.45 | 现代版本基础 |
| 2012 | expect 5.45.4 | 当前最广泛使用的版本 |
| 2018+ | expect-in-rust | 社区探索用 Rust 重写 |

---

### 2. 安装与环境配置

#### 2.1 安装 expect

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install expect -y

# CentOS/RHEL 7
sudo yum install expect -y

# CentOS/RHEL 8+, Rocky/AlmaLinux
sudo dnf install expect -y

# Arch Linux
sudo pacman -S expect

# macOS (Homebrew)
brew install expect

# 验证安装
expect -v
# expect version 5.45.4

# 查看 expect 路径
which expect
# /usr/bin/expect
```

#### 2.2 脚本文件约定

```bash
# expect 脚本通常以 .exp 为扩展名
# 文件头声明解释器
#!/usr/bin/expect -f

# -f 表示从文件读取脚本
# -c 表示从命令行读取脚本
# 也可以写成 #!/usr/bin/env expect
```

---

### 3. 核心命令详解

#### 3.1 spawn — 启动子进程

`spawn` 是 expect 的起点，用于启动一个子进程并将其连接到 expect 的 PTY。

```tcl
# 基本语法
spawn [选项] program [args...]

# 常用选项
spawn -noecho ssh user@host        ;# 不回显 spawn 命令本身
spawn -open $channel               ;# 使用已打开的通道
spawn -pty                         ;# 使用伪终端（默认）

# 示例
spawn ssh admin@192.168.1.100      ;# 启动 SSH 连接
spawn telnet 192.168.1.1           ;# 启动 telnet
spawn ftp ftp.example.com          ;# 启动 FTP
spawn passwd admin                 ;# 修改密码
spawn mysql -u root -p             ;# MySQL 登录
```

**spawn 的内部机制**：
1. 创建一对 PTY（主端和从端）
2. fork 一个子进程
3. 子进程的 stdin/stdout/stderr 连接到从端 PTY
4. expect 通过主端 PTY 读写数据
5. 子进程认为自己在与真实终端交互

**spawn_id 变量**：
```tcl
# spawn 后，子进程 ID 存储在 spawn_id 中
spawn ssh admin@host
puts "子进程 ID: $spawn_id"

# 可以保存多个 spawn_id 实现并发
spawn ssh admin@host1
set spawn_id1 $spawn_id

spawn ssh admin@host2
set spawn_id2 $spawn_id

# 切换到特定进程
set spawn_id $spawn_id1
expect "password:"
send "pass1\r"
```

#### 3.2 expect — 模式匹配

`expect` 是 expect 工具的核心命令，用于等待并匹配子进程的输出。

**基本语法**：
```tcl
expect pattern1 { action1 } \
       pattern2 { action2 } \
       timeout   { timeout_action } \
       eof       { eof_action }
```

**精确匹配**：
```tcl
# 精确匹配字符串
expect "password:"
expect "Are you sure you want to continue connecting"

# 匹配多个模式（按顺序匹配第一个出现的）
expect {
    "password:" {
        send "mypass\r"
    }
    "Permission denied" {
        puts "认证失败"
        exit 1
    }
}
```

**通配符匹配（glob 风格）**：
```tcl
# * 匹配任意字符
expect "Welcome*"          ;# 匹配 "Welcome" 开头的任意内容
expect "*error*"           ;# 包含 "error" 的任意内容

# ? 匹配单个字符
expect "host?"             ;# 匹配 "host1", "hosta" 等

# [...] 字符类
expect "[Pp]assword"       ;# 匹配 "Password" 或 "password"

# 注意：expect 的 glob 匹配默认启用
# 如果模式以 - 开头，需要转义或使用 --
```

**正则表达式匹配（-re 标志）**：
```tcl
# 使用 -re 启用正则匹配
expect -re ".*password:.*" {
    send "mypass\r"
}

# 捕获正则匹配的子组
expect -re "(.*)@(.*)\\\$ " {
    set matched_user $expect_out(1,string)
    set matched_host $expect_out(2,string)
    puts "用户: $matched_user, 主机: $matched_host"
}

# 匹配 IP 地址
expect -re "([0-9]{1,3}\\.){3}[0-9]{1,3}" {
    set ip $expect_out(0,string)
    puts "检测到 IP: $ip"
}
```

**expect_out 数组详解**：
```tcl
# expect_out 包含匹配结果的详细信息
expect -re "password for (.+)@(.+):" {
    # expect_out(0,string)  — 整个匹配的字符串
    # expect_out(1,string)  — 第一个子组
    # expect_out(2,string)  — 第二个子组
    # expect_out(buffer)    — 匹配之前的所有输出（含匹配内容）
    # expect_out(spawn_id)  — 匹配到的进程 ID
    # expect_out(X,start)   — 子组 X 在缓冲区中的起始位置
    # expect_out(X,end)     — 子组 X 在缓冲区中的结束位置

    set user $expect_out(1,string)
    set host $expect_out(2,string)
}
```

**全局标志**：
```tcl
# -nocase — 不区分大小写
expect -nocase "password"

# -timeout — 单次匹配超时
expect -timeout 5 "prompt>"

# -ex — 精确匹配（禁用 glob）
expect -ex "file.txt"    ;# 不会把 . 当通配符

# -gl — 明确指定 glob 匹配（默认）
expect -gl "file*"

# -re — 正则匹配
expect -re "file.*\\.txt"
```

#### 3.3 send — 发送输入

`send` 用于向子进程发送文本（模拟键盘输入）。

```tcl
# 基本用法
send "hello\r"           ;# 发送 "hello" + 回车

# \r 是必须的！因为大多数程序等待回车才处理输入
# \r = 回车 (CR, 0x0D)
# \n = 换行 (LF, 0x0A)
# 在 expect 中，通常使用 \r 而不是 \n

# 发送特殊字符
send "\r"                ;# 回车
send "\n"                ;# 换行
send "\t"                ;# Tab
send "\x03"              ;# Ctrl+C
send "\x1a"              ;# Ctrl+Z
send "\x04"              ;# Ctrl+D (EOF)

# send_user — 发送到标准输出（不是子进程）
send_user "脚本正在运行...\n"

# send_error — 发送到标准错误
send_error "发生错误！\n"

# send_log — 发送到日志文件（如果 log_file 已设置）
send_log "匹配到密码提示\n"
```

**send 的内部机制**：
```
send "password\r"
  ↓
expect 通过 PTY 主端写入数据
  ↓
子进程从 PTY 从端读取数据
  ↓
子进程处理输入（就像用户键入了一样）
```

#### 3.4 interact — 交还控制权

`interact` 将控制权交还给用户，让用户直接与子进程交互。

```tcl
# 基本用法：完全交还控制权
interact

# 交互式模式（部分交还）
# 用户按特定字符时触发 expect 动作
interact {
    \003 {        ;# Ctrl+C 触发
        send_user "\n退出中...\n"
        send "exit\r"
    }
    \004 {        ;# Ctrl+D 触发
        send_user "\n断开连接\n"
        exit
    }
}

# 字符替换
interact {
    -o "exit" {   ;# 用户输入 "exit" 时
        send "logout\r"
        exit
    }
}

# 从文件读取输入（用于测试）
interact -input $file_handle
```

**interact 的典型场景**：
```tcl
#!/usr/bin/expect -f
# 自动登录后交还控制权给用户
set timeout 30
spawn ssh admin@192.168.1.100

expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "mypassword\r" }
    timeout { puts "连接超时"; exit 1 }
}

expect {
    "\$ " { }
    "# " { }
}

puts "\n=== 已自动登录，现在交还控制权 ==="
puts "按 Ctrl+] 退出\n"

interact {
    \035 {        ;# Ctrl+] 退出
        send_user "\n断开连接...\n"
        send "exit\r"
        exit
    }
}
```

#### 3.5 set timeout — 超时控制

```tcl
# 设置全局超时（默认 10 秒）
set timeout 30

# 设置 -1 表示永不超时
set timeout -1

# 设置 0 表示立即超时（非阻塞检查）
set timeout 0

# 单次匹配超时（覆盖全局设置）
expect -timeout 5 "password:"
expect -timeout 10 "prompt>"

# 在 expect 块中处理超时
expect {
    "password:" {
        send "mypass\r"
    }
    timeout {
        puts "等待超时！"
        exit 1
    }
}
```

#### 3.6 exp_continue — 继续匹配

`exp_continue` 是 expect 中最强大的控制流命令之一，它让 expect 在匹配成功后继续尝试匹配，而不是跳出 expect 块。

```tcl
# 典型场景：处理多个连续的交互提示
spawn ssh admin@192.168.1.100

expect {
    "yes/no" {
        send "yes\r"
        exp_continue    ;# 匹配到 yes/no 后继续等待 password
    }
    "password:" {
        send "mypass\r"
        # 不 exp_continue，跳出 expect 块
    }
    timeout {
        puts "超时"
        exit 1
    }
}

# exp_continue -continue_spawn（expect 5.45+）
# 用于 spawn 新进程后继续 expect 循环
```

**exp_continue 的执行流程**：
```
expect 块开始
    ↓
收到 "Are you sure you want to continue connecting (yes/no)?"
    ↓
匹配 "yes/no" → send "yes\r" → exp_continue（回到 expect 块开头）
    ↓
收到 "admin@host's password:"
    ↓
匹配 "password:" → send "mypass\r" → 无 exp_continue（跳出 expect 块）
```

---

### 4. 进阶特性

#### 4.1 日志记录

```tcl
# log_file — 记录整个会话到文件
log_file /tmp/expect_session.log
log_file -a /tmp/expect_session.log    ;# 追加模式
log_file -info /tmp/expect_session.log ;# 包含额外信息
log_file                               ;# 关闭日志

# log_user — 控制是否输出到终端
log_user 0    ;# 关闭终端输出（静默模式）
log_user 1    ;# 开启终端输出（默认）

# 典型用法：静默执行但记录日志
log_user 0
log_file /tmp/session.log
spawn ssh admin@host
expect "password:"
send "mypass\r"
expect "\$ "
send "commands\r"
log_file    ;# 关闭日志
log_user 1  ;# 恢复终端输出
```

#### 4.2 多进程管理

```tcl
#!/usr/bin/expect -f
# 同时管理多个 SSH 会话

set hosts {web01 web02 db01}
set password "S3cur3Pass!"
set timeout 30

# 保存所有 spawn_id
set spawn_ids {}

foreach host $hosts {
    spawn ssh admin@$host
    lappend spawn_ids $spawn_id
}

# 逐个处理
foreach host $hosts spawn_id_list $spawn_ids {
    set spawn_id $spawn_id_list
    expect {
        "yes/no" { send "yes\r"; exp_continue }
        "password:" { send "$password\r" }
    }
    expect "\$ "
    send "hostname\r"
    expect "\$ "
    send "uptime\r"
    expect "\$ "
}

# 等待所有进程结束
foreach id $spawn_ids {
    set spawn_id $id
    expect eof
}
```

#### 4.3 文件传输（通过 expect）

```tcl
#!/usr/bin/expect -f
# 使用 expect 自动化 scp（当密钥不可用时）

set timeout 120
set host "192.168.1.100"
set user "admin"
set password "S3cur3Pass!"
set local_file "/tmp/data.tar.gz"
set remote_dir "/home/admin/"

spawn scp -o StrictHostKeyChecking=no $local_file $user@$host:$remote_dir

expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$password\r" }
    timeout { puts "传输超时"; exit 1 }
}

expect {
    "100%" { puts "传输完成" }
    "error" { puts "传输失败"; exit 1 }
    eof { }
}

expect eof
```

#### 4.4 函数封装

```tcl
#!/usr/bin/expect -f

# 封装 SSH 连接函数
proc ssh_connect {host user password {port 22}} {
    set timeout 30
    spawn -noecho ssh -o StrictHostKeyChecking=no -p $port $user@$host

    expect {
        "yes/no" { send "yes\r"; exp_continue }
        "password:" { send "$password\r" }
        timeout {
            send_user "错误: 连接 $host 超时\n"
            return -1
        }
        eof {
            send_user "错误: 连接 $host 失败\n"
            return -1
        }
    }

    expect {
        "\\$ " - "# " { return 0 }
        "Permission denied" {
            send_user "错误: $host 认证失败\n"
            return -1
        }
        timeout {
            send_user "错误: $host shell 提示符未出现\n"
            return -1
        }
    }
}

# 封装远程命令执行
proc ssh_exec {command} {
    send "$command\r"
    expect {
        "\\$ " - "# " {
            set output $expect_out(buffer)
            # 去掉命令本身和提示符
            regsub ".*\r\n" $output "" output
            regsub "\r\n.*$" $output "" output
            return $output
        }
        timeout {
            send_user "错误: 命令执行超时\n"
            return -1
        }
    }
}

# 使用
if {[ssh_connect "192.168.1.100" "admin" "S3cur3Pass!"] == 0} {
    set hostname [ssh_exec "hostname"]
    send_user "远程主机名: $hostname\n"

    set uptime [ssh_exec "uptime"]
    send_user "运行时间: $uptime\n"

    send "exit\r"
    expect eof
}
```

---

### 5. 从 Bash 调用 expect（推荐方式）

在实际 SRE 工作中，纯 expect 脚本在变量处理、文件操作、错误处理等方面不如 Bash 方便。推荐方案：在 Bash 脚本中通过 **here-document** 嵌入 expect 代码。

#### 5.1 基本模式

```bash
#!/bin/bash
# Bash 中嵌入 expect

HOST="192.168.1.100"
USER="admin"
PASS="S3cur3Pass!"
CMD="uptime && df -h /"

expect << EOF
set timeout 30
spawn ssh -o StrictHostKeyChecking=no $USER@$HOST
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$PASS\r" }
    timeout { exit 1 }
}
expect "\\$ "
send "$CMD\r"
expect "\\$ "
send "exit\r"
expect eof
EOF
```

#### 5.2 捕获 expect 输出

```bash
#!/bin/bash
# 捕获 expect 的输出到变量

HOST="192.168.1.100"
USER="admin"
PASS="S3cur3Pass!"

# 使用 log_user 0 静默 expect 自身输出
# 使用 send_user 输出我们需要的内容
OUTPUT=$(expect << EOF
set timeout 30
log_user 0
spawn ssh -o StrictHostKeyChecking=no $USER@$HOST
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$PASS\r" }
    timeout { exit 1 }
}
expect "\\$ "
send "hostname; uptime; free -h | grep Mem\r"
expect "\\$ "
set output \$expect_out(buffer)
send_user \$output
send "exit\r"
expect eof
EOF
)

echo "远程服务器信息:"
echo "$OUTPUT"
```

#### 5.3 安全地传递密码

```bash
#!/bin/bash
# 方法 1: 从环境变量读取（适合 CI/CD）
export SSH_PASSWORD="S3cur3Pass!"
expect << EOF
set password \$::env(SSH_PASSWORD)
spawn ssh admin@host
expect "password:"
send "\$password\r"
...
EOF

# 方法 2: 从加密文件读取
PASSWORD=$(gpg -dq /etc/credentials/ssh_pass.gpg 2>/dev/null)
expect << EOF
set password "$PASSWORD"
...
EOF

# 方法 3: 从密钥管理服务读取（生产推荐）
PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id prod/ssh/password \
    --query SecretString --output text 2>/dev/null)

# 方法 4: 交互式输入（最安全）
read -s -p "输入密码: " PASSWORD
echo
expect << EOF
set password "$PASSWORD"
...
EOF

# 方法 5: 使用文件描述符（避免命令行暴露密码）
exec 3<<< "$PASSWORD"
expect << EOF
gets stdin password
...
EOF
exec 3>&-
```

---

### 6. SRE 实战案例

#### 6.1 批量服务器初始化（首次 SSH 连接自动接受密钥）

```bash
#!/bin/bash
# batch_ssh_init.sh — 批量服务器首次 SSH 连接初始化
# 功能：自动接受 SSH 密钥指纹、执行初始配置

set -euo pipefail

# 配置
SERVERS_FILE="/etc/sre/servers.conf"
SSH_USER="sre"
SSH_PASSWORD="Temp@Init2026"
LOG_DIR="/var/log/server_init"
REPORT_FILE="$LOG_DIR/init_report_$(date +%Y%m%d_%H%M%S).txt"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "[$(date '+%H:%M:%S')] $1" | tee -a "$REPORT_FILE"; }
ok()  { log "${GREEN}[OK]${NC} $1"; }
warn(){ log "${YELLOW}[WARN]${NC} $1"; }
err() { log "${RED}[ERROR]${NC} $1"; }

mkdir -p "$LOG_DIR"

# 统计变量
TOTAL=0
SUCCESS=0
FAILED=0

log "========== 批量 SSH 初始化开始 =========="
log "时间: $(date)"
log "服务器列表: $SERVERS_FILE"
log ""

while IFS='|' read -r host port role; do
    # 跳过注释和空行
    [[ "$host" =~ ^#.*$ || -z "$host" ]] && continue

    TOTAL=$((TOTAL + 1))
    log "----------------------------------------"
    log "处理: $host (端口: $port, 角色: $role)"

    # 使用 expect 自动接受 SSH 密钥并测试连接
    RESULT=$(expect << EXPECT_EOF 2>&1
set timeout 30
log_user 0

spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
    -p $port $SSH_USER@$host echo "SSH_INIT_OK"

expect {
    "yes/no" {
        send "yes\r"
        exp_continue
    }
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    "SSH_INIT_OK" {
        send_user "SUCCESS"
    }
    "Permission denied" {
        send_user "AUTH_FAILED"
    }
    timeout {
        send_user "TIMEOUT"
    }
    eof {
        send_user "CONNECTION_CLOSED"
    }
}

expect eof
EXPECT_EOF
    )

    case "$RESULT" in
        *SUCCESS*)
            ok "$host: SSH 连接成功"
            SUCCESS=$((SUCCESS + 1))

            # 执行初始化命令
            expect << INIT_EOF > /dev/null 2>&1
set timeout 60
spawn ssh -o StrictHostKeyChecking=no -p $port $SSH_USER@$host
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$SSH_PASSWORD\r" }
}
expect "\\$ "

# 安装基础工具
send "sudo apt update -q && sudo apt install -y curl vim git htop net-tools sysstat 2>&1 | tail -5\r"
expect -timeout 120 "\\$ "

# 设置时区
send "sudo timedatectl set-timezone Asia/Shanghai\r"
expect "\\$ "

# 配置 sysstat
send "sudo sed -i 's/ENABLED=\"false\"/ENABLED=\"true\"/' /etc/default/sysstat 2>/dev/null; sudo systemctl restart sysstat 2>/dev/null; echo 'INIT_DONE'\r"
expect "INIT_DONE"

send "exit\r"
expect eof
INIT_EOF
            ok "$host: 初始化命令执行完成"
            ;;
        *AUTH_FAILED*)
            err "$host: 认证失败"
            FAILED=$((FAILED + 1))
            ;;
        *TIMEOUT*)
            err "$host: 连接超时"
            FAILED=$((FAILED + 1))
            ;;
        *)
            err "$host: 未知错误 - $RESULT"
            FAILED=$((FAILED + 1))
            ;;
    esac
done < "$SERVERS_FILE"

# 生成报告
log ""
log "========== 初始化报告 =========="
log "总计: $TOTAL 台服务器"
log "成功: $SUCCESS 台"
log "失败: $FAILED 台"
log "报告文件: $REPORT_FILE"
```

**服务器列表文件格式** (`/etc/sre/servers.conf`)：
```
# 主机名|端口|角色
192.168.1.10|22|web
192.168.1.11|22|web
192.168.1.20|22|db
192.168.1.30|2222|cache
```

#### 6.2 批量密码修改脚本

```bash
#!/bin/bash
# batch_password_change.sh — 批量修改服务器密码
# 注意：仅适用于必须使用密码认证的环境，生产环境应使用 SSH 密钥

set -euo pipefail

# 配置
SERVERS=(
    "192.168.1.10:admin:OldPass123"
    "192.168.1.11:admin:OldPass123"
    "192.168.1.12:root:RootPass456"
    "192.168.1.20:deploy:DeployPass789"
)

# 新密码（从环境变量或密钥管理服务获取）
NEW_PASS="${NEW_PASSWORD:?错误: 请设置 NEW_PASSWORD 环境变量}"
LOG_FILE="/var/log/batch_passwd_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

TOTAL=0
SUCCESS=0
FAILED=0

for entry in "${SERVERS[@]}"; do
    IFS=':' read -r host user oldpass <<< "$entry"
    TOTAL=$((TOTAL + 1))

    log "处理: $user@$host"

    RESULT=$(expect << EXPECT_EOF 2>&1
set timeout 30
log_user 0

spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $user@$host

expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$oldpass\r" }
    timeout { send_user "TIMEOUT"; exit 1 }
    eof { send_user "CONNECT_FAILED"; exit 1 }
}

expect {
    "\\$ " - "# " { }
    "Permission denied" { send_user "AUTH_FAILED"; exit 1 }
    timeout { send_user "SHELL_TIMEOUT"; exit 1 }
}

# 执行 passwd 命令
send "passwd\r"
expect {
    "Current password:" { send "$oldpass\r" }  ;# 某些系统需要当前密码
    "New password:" { }                          ;# 某些系统直接要求新密码
    timeout { send_user "PASSWD_TIMEOUT"; exit 1 }
}

expect "New password:"
send "$NEW_PASS\r"

expect "Retype new password:"
send "$NEW_PASS\r"

expect {
    "successfully" { send_user "SUCCESS" }
    "password is too" { send_user "WEAK_PASSWORD"; exit 1 }
    "password unchanged" { send_user "SAME_PASSWORD"; exit 1 }
    timeout { send_user "RESULT_TIMEOUT"; exit 1 }
}

send "exit\r"
expect eof
EXPECT_EOF
    )

    case "$RESULT" in
        *SUCCESS*)
            log "  OK: $host 密码修改成功"
            SUCCESS=$((SUCCESS + 1))
            ;;
        *AUTH_FAILED*)
            log "  FAIL: $host 认证失败（旧密码错误）"
            FAILED=$((FAILED + 1))
            ;;
        *WEAK_PASSWORD*)
            log "  FAIL: $host 新密码不符合策略"
            FAILED=$((FAILED + 1))
            ;;
        *TIMEOUT*|*CONNECT_FAILED*)
            log "  FAIL: $host 连接失败"
            FAILED=$((FAILED + 1))
            ;;
        *)
            log "  FAIL: $host 未知错误: $RESULT"
            FAILED=$((FAILED + 1))
            ;;
    esac
done

log ""
log "========== 密码修改报告 =========="
log "总计: $TOTAL | 成功: $SUCCESS | 失败: $FAILED"
```

#### 6.3 网络设备自动化配置

```bash
#!/bin/bash
# network_config.sh — 批量配置网络设备（交换机/路由器）
# 支持 Cisco IOS 风格设备

set -euo pipefail

# 设备列表: 名称|IP|类型|密码
DEVICES=(
    "switch-f1-01|192.168.10.1|cisco|Admin@2026"
    "switch-f1-02|192.168.10.2|cisco|Admin@2026"
    "router-core-01|192.168.10.254|cisco|Admin@2026"
)

BACKUP_DIR="/etc/network_backups/$(date +%Y%m%d)"
CONFIG_DIR="/etc/network_configs"
LOG_FILE="/var/log/network_config_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$BACKUP_DIR" "$CONFIG_DIR"

log() { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_FILE"; }

# 备份配置
backup_device() {
    local name=$1 ip=$2 pass=$3

    log "备份 $name ($ip)..."

    expect << EXPECT_EOF > /dev/null 2>&1
set timeout 60
log_user 0

spawn ssh -o StrictHostKeyChecking=no admin@$ip

expect {
    "yes/no" { send "yes\r"; exp_continue }
    "Password:" { send "$pass\r" }
    timeout { exit 1 }
}

expect ">" - "#"
send "enable\r"
expect "Password:"
send "$pass\r"
expect "#"

# 进入终端配置模式
send "terminal length 0\r"
expect "#"

# 获取运行配置
send "show running-config\r"
expect "#"

# 保存配置到文件
set fp [open "$BACKUP_DIR/${name}.cfg" w]
puts \$fp \$expect_out(buffer)
close \$fp

send "exit\r"
expect eof
EXPECT_EOF

    if [[ -f "$BACKUP_DIR/${name}.cfg" ]]; then
        log "  备份完成: $BACKUP_DIR/${name}.cfg"
    else
        log "  备份失败!"
    fi
}

# 应用配置
apply_config() {
    local name=$1 ip=$2 pass=$3 config_file=$4

    log "应用配置到 $name ($ip)..."

    expect << EXPECT_EOF 2>&1
set timeout 120

spawn ssh -o StrictHostKeyChecking=no admin@$ip

expect {
    "yes/no" { send "yes\r"; exp_continue }
    "Password:" { send "$pass\r" }
    timeout { exit 1 }
}

expect ">" - "#"
send "enable\r"
expect "Password:"
send "$pass\r"
expect "#"

send "configure terminal\r"
expect "(config)#"

# 逐行发送配置
set fp [open "$config_file" r]
while {[gets \$fp line] >= 0} {
    # 跳过注释和空行
    if {[string match "#*" \$line] || [string trim \$line] eq ""} continue
    send "\$line\r"
    expect "(config)#" - "(config-.*\)#" - "#"
}
close \$fp

send "end\r"
expect "#"

# 保存配置
send "write memory\r"
expect "#"

send "exit\r"
expect eof
EXPECT_EOF

    log "  配置应用完成"
}

# 主流程
log "========== 网络设备配置管理 =========="

for device in "${DEVICES[@]}"; do
    IFS='|' read -r name ip type pass <<< "$device"
    backup_device "$name" "$ip" "$pass"
done

log ""
log "备份完成，配置文件保存在: $BACKUP_DIR"
```

#### 6.4 数据库批量操作

```bash
#!/bin/bash
# batch_db_ops.sh — 批量数据库操作（使用 expect 自动登录）

set -euo pipefail

DB_SERVERS=(
    "db-master:192.168.1.20:root:DbRoot@2026"
    "db-slave1:192.168.1.21:root:DbRoot@2026"
    "db-slave2:192.168.1.22:root:DbRoot@2026"
)

QUERY="SHOW SLAVE STATUS\G"

for db in "${DB_SERVERS[@]}"; do
    IFS=':' read -r name ip user pass <<< "$db"
    echo "===== $name ($ip) ====="

    expect << EXPECT_EOF 2>&1
set timeout 30
log_user 1

spawn ssh -o StrictHostKeyChecking=no admin@$ip

expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$pass\r" }
    timeout { exit 1 }
}

expect "\\$ "
send "mysql -u$user -p'$pass' -e '$QUERY' 2>&1 | head -30\r"
expect "\\$ "

send "exit\r"
expect eof
EXPECT_EOF

    echo ""
done
```

---

### 7. expect 的局限性与替代方案

#### 7.1 expect 的局限性

| 问题 | 详细说明 | 影响程度 |
|------|----------|----------|
| **密码明文** | 密码写在脚本或配置文件中，存在严重安全风险 | 高 |
| **依赖 PTY** | 需要伪终端支持，某些环境不可用 | 中 |
| **脆弱匹配** | 提示符变化（不同 OS/版本/语言环境）导致脚本失效 | 高 |
| **难以调试** | 交互过程难以复现和调试 | 中 |
| **并发差** | 单线程，不适合大规模批量操作 | 高 |
| **不可移植** | 依赖 expect 包，不是所有系统都预装 | 中 |
| **超时敏感** | 网络延迟变化导致超时设置难以统一 | 中 |

#### 7.2 现代替代方案对比

| 场景 | expect | sshpass | paramiko | Ansible |
|------|--------|---------|----------|---------|
| 简单 SSH 命令 | 可用 | 更简单 | Python 生态 | 推荐 |
| 交互式程序 | 最佳 | 不适用 | 有限 | 不适用 |
| 批量管理 | 差 | 差 | 好 | 最佳 |
| 安全性 | 差 | 差 | 好 | 好 |
| 学习曲线 | 高 | 低 | 中 | 中 |
| 并发能力 | 差 | 差 | 好 | 好 |
| 网络设备 | 好 | 不适用 | 好 | 好 |

**sshpass — 更简单的密码传递**：
```bash
# 安装
sudo apt install sshpass -y

# 使用
sshpass -p "mypassword" ssh admin@host "hostname"

# 从文件读取密码
sshpass -f /root/.passfile ssh admin@host "uptime"

# 从环境变量读取
export SSHPASS="mypassword"
sshpass -e ssh admin@host "df -h"
```

**paramiko — Python SSH 库**：
```python
#!/usr/bin/env python3
"""paramiko 示例：SSH 自动化"""
import paramiko

def ssh_exec(host, user, password, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, timeout=30)

    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode()
    error = stderr.read().decode()
    client.close()

    return output, error

# 批量执行
hosts = ['192.168.1.10', '192.168.1.11', '192.168.1.12']
for host in hosts:
    output, _ = ssh_exec(host, 'admin', 'password', 'uptime')
    print(f"{host}: {output.strip()}")
```

**Ansible — 企业级方案**：
```yaml
# inventory.yml
all:
  hosts:
    web01:
      ansible_host: 192.168.1.10
    web02:
      ansible_host: 192.168.1.11

# playbook.yml
- name: 批量服务器配置
  hosts: all
  become: yes
  tasks:
    - name: 安装基础工具
      apt:
        name: [curl, vim, git, htop]
        state: present

    - name: 设置时区
      timezone:
        name: Asia/Shanghai
```

#### 7.3 何时仍然使用 expect

尽管有更现代的替代方案，expect 在以下场景仍然是最佳选择：

1. **网络设备管理**：许多老旧交换机/路由器只支持交互式 CLI
2. **遗留系统**：一些老旧系统没有 API，只有交互式管理界面
3. **密码修改**：`passwd` 命令是交互式的，expect 是最直接的方案
4. **一次性任务**：临时需要自动化某个交互操作
5. **CI/CD 中的交互工具**：某些工具的首次配置需要交互

---

### 8. 最佳实践

#### 8.1 密码安全

```bash
# 错误：密码硬编码
PASS="mypassword"  # 永远不要这样做！

# 正确：从安全来源读取
# 1. 环境变量
PASS="$SSH_PASSWORD"

# 2. 加密文件
PASS=$(gpg -dq /etc/secrets/ssh.gpg)

# 3. 密钥管理服务
PASS=$(vault kv get -field=password secret/ssh)

# 4. 交互式输入
read -s -p "Password: " PASS
```

#### 8.2 超时处理

```tcl
# 总是设置合理的超时
set timeout 30

# 对不同操作设置不同超时
expect -timeout 5 "password:"      ;# 密码提示通常很快
expect -timeout 300 "100%"         ;# 文件传输可能很慢
expect -timeout 10 "\\$ "         ;# 命令执行视情况而定

# 总是处理 timeout 和 eof
expect {
    "pattern" { ... }
    timeout {
        send_user "操作超时\n"
        exit 1
    }
    eof {
        send_user "连接意外断开\n"
        exit 1
    }
}
```

#### 8.3 错误处理

```tcl
# 使用返回值判断成功/失败
proc safe_ssh {host user pass} {
    spawn ssh -o ConnectTimeout=10 $user@$host
    expect {
        "yes/no" { send "yes\r"; exp_continue }
        "password:" { send "$pass\r" }
        timeout { return -1 }
        eof { return -1 }
    }
    expect {
        "\\$ " - "# " { return 0 }
        "Permission denied" { return -2 }
        timeout { return -1 }
    }
}
```

#### 8.4 日志记录

```tcl
# 总是记录会话日志
log_file -noappend /tmp/expect_$(date +%Y%m%d_%H%M%S).log

# 在关键步骤添加日志
send_user "[$timestamp] 步骤 1: 连接服务器...\n"
send_user "[$timestamp] 步骤 2: 执行命令...\n"
```

---

## 💻 实战练习

### 练习 1：基础 expect 脚本

编写一个 expect 脚本，实现：
1. SSH 登录到远程服务器
2. 执行 `hostname && uptime && free -h` 命令
3. 将输出保存到本地文件
4. 正常退出

```bash
# 你的代码
```

<details>
<summary>参考答案</summary>

```tcl
#!/usr/bin/expect -f

set timeout 30
set host [lindex $argv 0]
set user [lindex $argv 1]
set password [lindex $argv 2]
set output_file "/tmp/ssh_output_[clock seconds].txt"

spawn ssh -o StrictHostKeyChecking=no $user@$host

expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$password\r" }
    timeout { send_user "连接超时\n"; exit 1 }
}

expect {
    "\\$ " - "# " { }
    "Permission denied" { send_user "认证失败\n"; exit 1 }
}

send "hostname; uptime; free -h | grep Mem\r"
expect "\\$ "

# 保存输出
set output $expect_out(buffer)
set fp [open $output_file w]
puts $fp $output
close $fp

send_user "输出已保存到: $output_file\n"

send "exit\r"
expect eof
```

</details>

### 练习 2：修复有问题的 expect 脚本

以下脚本有 5 个错误，找出并修复：

```tcl
#!/usr/bin/expect -f
spawn ssh user@192.168.1.100
expect "password:"
send "pass123"
expect "$ "
send "ls\r"
expect eof
```

<details>
<summary>参考答案</summary>

```tcl
#!/usr/bin/expect -f

set timeout 30                              ;# 错误 1: 缺少超时设置

spawn ssh user@192.168.1.100

expect {
    "yes/no" { send "yes\r"; exp_continue } ;# 错误 2: 未处理首次连接的 yes/no
    "password:" { send "pass123\r" }         ;# 错误 3: send 缺少 \r（回车）
    timeout { exit 1 }                       ;# 错误 4: 缺少超时处理
}

expect {
    "\\$ " { send "ls\r" }                   ;# 错误 5: $ 需要转义为 \\$
    timeout { exit 1 }
}
expect eof
```

</details>

### 练习 3：编写批量健康检查脚本

编写一个脚本，使用 expect 批量检查多台服务器的：
- 磁盘使用率（超过 80% 告警）
- 内存使用率（超过 90% 告警）
- 系统负载（超过 CPU 核心数告警）

```bash
# 你的代码
```

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# health_check.sh — 批量服务器健康检查

set -euo pipefail

SERVERS=(
    "192.168.1.10:admin:pass123"
    "192.168.1.11:admin:pass123"
    "192.168.1.12:admin:pass123"
)

for entry in "${SERVERS[@]}"; do
    IFS=':' read -r host user pass <<< "$entry"
    echo "===== 检查 $host ====="

    RESULT=$(expect << EXPECT_EOF 2>&1
set timeout 30
log_user 0
spawn ssh -o StrictHostKeyChecking=no $user@$host
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$pass\r" }
    timeout { send_user "TIMEOUT"; exit 1 }
}
expect "\\$ "

# 磁盘检查
send "df -h / | tail -1 | awk '{print \$5}'\r"
expect "\\$ "
set disk_usage \$expect_out(buffer)

# 内存检查
send "free | grep Mem | awk '{printf \"%.0f\", \$3/\$2*100}'\r"
expect "\\$ "
set mem_usage \$expect_out(buffer)

# 负载检查
send "nproc; uptime | awk -F'load average:' '{print \$2}'\r"
expect "\\$ "
set load_info \$expect_out(buffer)

send_user "DISK:\$disk_usage MEM:\$mem_usage LOAD:\$load_info"
send "exit\r"
expect eof
EXPECT_EOF
    )

    echo "$RESULT"
    echo ""
done
```

</details>

### 练习 4：FTP 自动下载脚本

编写 expect 脚本，实现自动 FTP 登录、下载指定文件、退出。

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
# ftp_auto_download.sh

FTP_HOST="ftp.example.com"
FTP_USER="backup"
FTP_PASS="ftp123"
REMOTE_FILE="/data/report.csv"
LOCAL_DIR="/tmp/ftp_downloads"

mkdir -p "$LOCAL_DIR"

expect << EOF
set timeout 60
spawn ftp $FTP_HOST

expect "Name"
send "$FTP_USER\r"
expect "Password:"
send "$FTP_PASS\r"

expect "ftp>"
send "binary\r"       ;# 二进制传输模式
expect "ftp>"
send "get $REMOTE_FILE $LOCAL_DIR/report.csv\r"
expect "ftp>"
send "bye\r"
expect eof
EOF

echo "下载完成: $LOCAL_DIR/report.csv"
```

</details>

---

## 🎯 面试题精选

### 面试题 1：expect 的工作原理是什么？

**参考答案**：

expect 基于 Tcl 语言扩展，通过**伪终端 (PTY)** 技术实现自动化交互。其工作原理：
1. `spawn` 创建一对 PTY（主端和从端），fork 子进程并将子进程的 stdin/stdout/stderr 连接到从端
2. 子进程的输出通过 PTY 主端被 expect 读取
3. expect 将读取到的输出与预定义的模式进行匹配（支持 glob 和正则）
4. 匹配成功后，`send` 通过 PTY 主端向子进程发送输入
5. 子进程认为自己在与真实用户交互

这种机制使得 expect 能够自动化任何交互式程序，而不需要修改程序本身。

### 面试题 2：expect 与 Ansible 各自适合什么场景？如何选择？

**参考答案**：

| 维度 | expect | Ansible |
|------|--------|---------|
| **适用场景** | 交互式程序自动化 | 批量配置管理 |
| **典型用例** | passwd 修改密码、网络设备 CLI | 服务器初始化、应用部署 |
| **并发能力** | 差（单线程） | 好（并行执行） |
| **安全性** | 密码通常明文 | 支持 Vault 加密 |
| **幂等性** | 无 | 天然幂等 |
| **学习曲线** | Tcl 语法较陌生 | YAML 易读 |

**选择原则**：
- 需要与交互式程序对话 → expect
- 批量服务器管理 → Ansible
- 网络设备管理 → 两者结合（Ansible 的 network modules 底层可能使用 expect）
- CI/CD 流水线 → 优先 Ansible，必要时 expect

### 面试题 3：expect 脚本中如何安全地传递密码？

**参考答案**：

1. **环境变量**（适合 CI/CD）：`set password $::env(SSH_PASSWORD)`
2. **加密文件**（适合本地）：通过 gpg 解密后传入
3. **密钥管理服务**（生产推荐）：从 Vault/AWS Secrets Manager 获取
4. **交互式输入**（最安全）：运行时由用户手动输入
5. **文件描述符**：通过 fd 传递，避免命令行暴露

**最佳实践**：生产环境应尽量使用 SSH 密钥认证，避免密码传递问题。

### 面试题 4：expect 中的 `exp_continue` 有什么作用？举一个典型使用场景。

**参考答案**：

`exp_continue` 让 expect 在匹配成功后继续尝试匹配下一个模式，而不是跳出 expect 块。相当于循环中的 `continue`。

典型场景：SSH 首次连接时可能同时遇到指纹确认和密码提示：
```tcl
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "mypass\r" }
}
```

如果没有 `exp_continue`，匹配到 "yes/no" 后就会跳出 expect 块，密码提示就无法被处理。

### 面试题 5：expect 脚本中 `send` 命令为什么需要 `\r` 而不是 `\n`？

**参考答案**：

- `\r` 是回车 (Carriage Return, CR)，`\n` 是换行 (Line Feed, LF)
- 大多数终端和交互式程序在接收到 `\r` 时处理输入（模拟用户按回车键）
- 在 Unix 终端中，通常需要 `\r\n` 或单独的 `\r` 来触发命令处理
- expect 通过 PTY 模拟终端，因此需要发送 `\r` 来模拟回车键
- 发送 `\n` 可能在某些程序中不被识别为"输入完成"

### 面试题 6：如何调试一个复杂的 expect 脚本？

**参考答案**：

1. **开启内部诊断**：`exp_internal 1` 显示详细的匹配过程
2. **日志记录**：`log_file /tmp/debug.log` 记录完整会话
3. **分步测试**：先用 `interact` 验证连接，再逐步添加自动化
4. **增加超时**：临时增大 `set timeout` 排除超时问题
5. **打印变量**：`send_user "变量值: $var\n"` 输出中间状态
6. **使用 `-i` 选项**：`expect -i $spawn_id` 指定进程调试
7. **strace 追踪**：`strace -f expect script.exp` 查看系统调用

### 面试题 7：expect 的 `log_user 0` 和 `log_file` 有什么区别？

**参考答案**：

- `log_user 0`：关闭 expect 输出到终端（标准输出），但不影响 `log_file`
- `log_file`：将会话记录到文件，与 `log_user` 独立
- 两者可以组合使用：`log_user 0` + `log_file /tmp/session.log` = 静默执行但记录日志
- `send_user` 始终输出到终端，不受 `log_user` 影响

### 面试题 8：expect 脚本如何实现超时重试机制？

**参考答案**：

```tcl
proc ssh_with_retry {host user pass {max_retries 3}} {
    for {set i 1} {$i <= $max_retries} {incr i} {
        spawn ssh $user@$host
        expect {
            "password:" {
                send "$pass\r"
                expect {
                    "\\$ " { return 0 }
                    "Permission denied" { break }
                }
            }
            timeout {
                send_user "第 $i 次连接超时\n"
                close
                wait
                if {$i == $max_retries} { return -1 }
                sleep 2
            }
        }
    }
    return -1
}
```

---

## 📚 深入阅读

### 官方文档
- [expect 官方文档](https://core.tcl-lang.org/expect/doc/expect.html)
- [Tcl/Tk 手册](https://www.tcl.tk/man/tcl8.6/TclCmd/contents.htm)
- `man expect` — expect 命令手册
- `man expect_intro` — expect 介绍

### 推荐书籍
- 《Exploring Expect》by Don Libes — expect 的权威书籍（O'Reilly）
- 《Tcl and the Tk Toolkit》by John K. Ousterhout — Tcl 语言权威参考

### 在线资源
- [Ansible 官方文档](https://docs.ansible.com/) — 现代自动化替代方案
- [paramiko 文档](https://www.paramiko.org/) — Python SSH 库
- [sshpass GitHub](https://sourceforge.net/projects/sshpass/) — 简单密码传递工具

### expect 核心命令速查

| 命令 | 语法 | 说明 |
|------|------|------|
| `spawn` | `spawn prog [args]` | 启动子进程 |
| `expect` | `expect pattern {action}` | 等待并匹配输出 |
| `send` | `send "text\r"` | 发送输入到子进程 |
| `send_user` | `send_user "text"` | 输出到终端 |
| `interact` | `interact` | 交还控制权给用户 |
| `set timeout` | `set timeout N` | 设置超时秒数 |
| `exp_continue` | `exp_continue` | 继续当前 expect 循环 |
| `exp_internal` | `exp_internal 1` | 开启调试输出 |
| `log_file` | `log_file file` | 记录会话到文件 |
| `log_user` | `log_user 0/1` | 控制终端输出 |
| `expect_out` | `$expect_out(buffer)` | 获取匹配的输出 |
| `close` | `close` | 关闭当前进程 |
| `wait` | `wait` | 等待子进程退出 |
| `exit` | `exit [code]` | 退出 expect |
| `sleep` | `sleep N` | 等待 N 秒 |

---

## ✅ 自检清单

### 理论检查点
- [ ] 能够解释 expect 的工作原理（PTY、模式匹配、send 机制）
- [ ] 理解 Tcl 语言基础语法（变量、条件、循环、过程）
- [ ] 掌握 expect 的匹配机制（glob、正则、-re 标志）
- [ ] 理解 `exp_continue` 的作用和执行流程
- [ ] 了解 expect 的局限性和替代方案

### 实操检查点
- [ ] 能够编写基本的 SSH 自动登录脚本
- [ ] 能够在 Bash 中通过 here-document 嵌入 expect
- [ ] 能够实现批量服务器操作脚本
- [ ] 能够正确处理超时和错误情况
- [ ] 能够安全地传递密码（不使用明文硬编码）
- [ ] 能够使用 `log_user` 和 `log_file` 管理输出
- [ ] 能够编写网络设备自动化配置脚本

---

*由 SRE 学习计划生成 | 2026-04-25*
