# Day 23: expect 自动化交互 — SSH 自动登录与批量配置

> 📅 日期：2026-04-25
> 📖 学习主题：expect 自动化交互 — SSH 自动登录/批量配置
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 23 的学习后，你应该掌握：
- 理解 expect 的工作原理和 Tcl 语法基础
- 掌握 `spawn`、`expect`、`send`、`interact` 核心命令
- 能够编写 SSH 自动登录、密码交互、批量配置脚本
- 了解 expect 的安全风险和替代方案（SSH key、ansible）
- 理解 expect 在 SRE 自动化中的适用边界

---

## 📖 底层原理详解

### 1. expect 的工作原理

expect 由 Don Libes 于 1990 年创建，基于 **Tcl (Tool Command Language)** 扩展。其核心思想是**模式匹配驱动的自动化交互**。

**工作流程**：
```
spawn 启动程序
    ↓
程序输出到伪终端（PTY）
    ↓
expect 匹配输出模式
    ↓
匹配成功 → send 发送响应
    ↓
继续 expect/send 循环或 interact 交还控制权
```

**关键概念**：
- **伪终端（PTY）**：expect 通过 PTY 与子进程通信，模拟真实终端
- **模式匹配**：使用 glob 或正则表达式匹配程序输出
- **超时控制**：默认超时 10 秒，可自定义

### 2. 安装与基础语法

```bash
# 安装 expect
sudo apt install expect -y       # Debian/Ubuntu
sudo yum install expect -y       # CentOS/RHEL

# 检查版本
expect -v
# expect version 5.45.4
```

#### 2.1 核心命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `spawn` | 启动子进程 | `spawn ssh user@host` |
| `expect` | 等待匹配输出 | `expect "password:"` |
| `send` | 发送文本 | `send "mypassword\r"` |
| `interact` | 交还控制权给用户 | `interact` |
| `set timeout` | 设置超时 | `set timeout 30` |
| `exp_continue` | 继续当前 expect | 在 expect 块内使用 |

#### 2.2 第一个 expect 脚本

```tcl
#!/usr/bin/expect -f
# auto_ssh.exp — 自动 SSH 登录

set timeout 30
set host "192.168.1.100"
set user "admin"
set password "S3cur3Pass!"

# 启动 SSH 连接
spawn ssh -o StrictHostKeyChecking=no $user@$host

# 匹配密码提示
expect {
    "yes/no" {
        send "yes\r"
        exp_continue   # 继续等待下一个匹配
    }
    "password:" {
        send "$password\r"
    }
    timeout {
        send_user "连接超时！\n"
        exit 1
    }
}

# 匹配登录成功标志
expect {
    "$ " -o "# " {
        send_user "登录成功！\n"
    }
    "Permission denied" {
        send_user "密码错误！\n"
        exit 1
    }
    timeout {
        send_user "登录超时！\n"
        exit 1
    }
}

# 交还控制权（可选：去掉这行会在命令执行后自动退出）
interact
```

**运行方式**：
```bash
# 方法 1：直接执行（需要 +x）
chmod +x auto_ssh.exp
./auto_ssh.exp

# 方法 2：通过 expect 解释器
expect auto_ssh.exp
```

### 3. 进阶用法

#### 3.1 从 Bash 调用 expect（推荐方式）

纯 expect 脚本处理变量和循环不如 Bash 方便。推荐方案：在 Bash 中使用 **here-document** 嵌入 expect。

```bash
#!/bin/bash
# ssh_with_expect.sh

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
expect {
    "\$ " -o "# " { send "$CMD\r" }
}
expect {
    "\$ " -o "# " { send "exit\r" }
}
expect eof
EOF
```

**关键点**：`expect eof` 表示等待子进程结束（SSH 会话关闭）。

#### 3.2 正则表达式匹配

```tcl
#!/usr/bin/expect -f

# 使用 -re 启用正则匹配
spawn ssh admin@192.168.1.100

expect {
    -re ".*password:.*" {
        send "mypassword\r"
    }
    -re ".*\\\$ " {
        send_user "已登录到 shell\n"
    }
    timeout {
        exit 1
    }
}
```

#### 3.3 捕获命令输出

```tcl
#!/usr/bin/expect -f

spawn ssh admin@192.168.1.100
expect "password:"
send "mypassword\r"
expect "\$ "

# 发送命令
send "cat /etc/os-release\r"

# 捕获输出（匹配到下一个提示符之间的内容）
expect "\$ "
set output $expect_out(buffer)

# 输出到文件
set fp [open "/tmp/os_info.txt" w]
puts $fp $output
close $fp

send "exit\r"
expect eof
```

#### 3.4 `exp_continue` 的妙用

```tcl
#!/usr/bin/expect -f
# 处理多种可能的交互提示

spawn ssh admin@192.168.1.100

expect {
    "Are you sure you want to continue" {
        send "yes\r"
        exp_continue   # 继续匹配（可能还需要密码）
    }
    "(yes/no)" {
        send "yes\r"
        exp_continue
    }
    "password:" {
        send "mypassword\r"
        exp_continue
    }
    "Last login:" {
        # 登录成功标志
        send_user "✅ 登录成功\n"
    }
    "Permission denied" {
        send_user "❌ 认证失败\n"
        exit 1
    }
    timeout {
        send_user "⏰ 超时\n"
        exit 1
    }
}

# 继续执行命令
send "hostname && uname -r\r"
expect "\$ "
send "exit\r"
expect eof
```

---

## 💻 SRE 实战场景

### 场景 1：批量服务器密码修改

```bash
#!/bin/bash
# batch_password_change.sh — 批量修改服务器密码
# ⚠️ 仅适用于必须使用密码认证的环境

set -euo pipefail

# 服务器列表
SERVERS=(
    "192.168.1.10:admin:oldpass123"
    "192.168.1.11:admin:oldpass123"
    "192.168.1.12:root:rootpass456"
)

NEW_PASS="N3wS3cur3P@ss!"
LOG_FILE="/var/log/batch_passwd_change.log"

for entry in "${SERVERS[@]}"; do
    IFS=':' read -r host user oldpass <<< "$entry"

    echo "[$(date)] 处理 $user@$host" | tee -a "$LOG_FILE"

    expect << EXPECT_EOF
set timeout 30
log_user 0  ;# 关闭 expect 自身的日志输出

spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $user@$host
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$oldpass\r" }
    timeout {
        puts "❌ $host: 连接超时"
        exit 1
    }
}

expect {
    "\$ " -o "# " { }
    "Permission denied" {
        puts "❌ $host: 密码错误"
        exit 1
    }
}

# 修改密码
send "passwd\r"
expect "New password:"
send "$NEW_PASS\r"
expect "Retype new password:"
send "$NEW_PASS\r"

expect {
    "successfully" {
        puts "✅ $host: 密码修改成功"
    }
    "password is too" {
        puts "❌ $host: 密码不符合策略"
        exit 1
    }
}

send "exit\r"
expect eof
EXPECT_EOF

    echo "[$(date)] 完成 $user@$host" | tee -a "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
done
```

### 场景 2：批量执行命令并收集结果

```bash
#!/bin/bash
# batch_command.sh — 批量在远程服务器执行命令并汇总结果

set -euo pipefail

HOSTS=("web01" "web02" "db01" "cache01")
USER="sre"
PASSWORD="SRE_p@ss!"
COMMAND="uptime; echo '---'; free -h | grep Mem; echo '---'; df -h / | tail -1"
RESULTS_DIR="/tmp/sre_batch_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

for host in "${HOSTS[@]}"; do
    echo "📡 连接 $host..."

    expect << EXPECT_EOF > "$RESULTS_DIR/${host}.log" 2>&1
set timeout 15
log_user 0

spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $USER@$host
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$PASSWORD\r" }
    timeout {
        puts "TIMEOUT"
        exit 1
    }
}

expect "\$ "
send "$COMMAND\r"
expect "\$ "
send "echo BATCH_END_MARKER\r"
expect "BATCH_END_MARKER"
send "exit\r"
expect eof
EXPECT_EOF

    if [[ $? -eq 0 ]]; then
        echo "✅ $host 完成"
    else
        echo "❌ $host 失败"
    fi
done

# 汇总报告
echo ""
echo "========== 批量执行报告 =========="
for host in "${HOSTS[@]}"; do
    echo ""
    echo "【$host】"
    cat "$RESULTS_DIR/${host}.log"
    echo "---"
done
```

### 场景 3：交换机/路由器配置备份

```bash
#!/bin/bash
# network_backup.sh — 备份网络设备配置

set -euo pipefail

NETWORK_DEVICES=(
    "switch01:192.168.10.1:admin:switch_pass"
    "router01:192.168.10.254:admin:router_pass"
)

BACKUP_DIR="/etc/network_backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

for device in "${NETWORK_DEVICES[@]}"; do
    IFS=':' read -r name ip user pass <<< "$device"

    expect << EXPECT_EOF
set timeout 60
log_user 0

spawn telnet $ip
expect "Username:"
send "$user\r"
expect "Password:"
send "$pass\r"

expect ">"
send "enable\r"
expect "Password:"
send "$pass\r"
expect "#"

# 显示配置
send "show running-config\r"
expect "show running-config\r\n"
set config ""
expect {
    -re "(.*)#" {
        set config \$expect_out(1,string)
    }
}

# 保存到文件
set fp [open "$BACKUP_DIR/${name}.cfg" w]
puts \$fp \$config
close \$fp
puts "✅ $name 配置已备份"

send "exit\r"
expect eof
EXPECT_EOF
done
```

---

## ⚠️ expect 的局限性与替代方案

### 为什么不推荐在生产中大量使用 expect？

| 问题 | 说明 |
|------|------|
| 密码明文 | 密码写在脚本或配置文件中，安全风险高 |
| 不可移植 | 依赖 expect 包，不是所有系统都预装 |
| 脆弱匹配 | 提示符变化（不同 OS/版本）导致脚本失效 |
| 难以调试 | 交互过程难以日志化 |
| 并发差 | 不适合大规模批量操作 |

### 推荐的替代方案

| 场景 | 推荐方案 |
|------|---------|
| SSH 登录 | SSH 密钥认证 + ssh-agent |
| 批量命令执行 | Ansible / Fabric / Parallel-SSH |
| 配置管理 | Ansible / SaltStack / Puppet |
| 网络设备管理 | Ansible (network modules) / Nornir |
| 交互式程序 | SSH key + 标准 Bash |

**SSH 密钥认证（强烈推荐替代 expect）**：

```bash
# 生成密钥对
ssh-keygen -t ed25519 -C "sre@company.com"

# 分发公钥（免密码登录）
ssh-copy-id user@host

# 验证免密登录
ssh user@host "hostname"
```

---

## 🧪 练习题

### 练习 1：修复 expect 脚本

```tcl
# 以下 expect 脚本有什么问题？
#!/usr/bin/expect -f
spawn ssh user@192.168.1.100
expect "password:"
send "pass123"
expect "$ "
send "ls\r"
expect eof
```

<details>
<summary>答案</summary>

```tcl
#!/usr/bin/expect -f
set timeout 30  ;# 1. 缺少超时设置
spawn ssh user@192.168.1.100
expect {
    "yes/no" { send "yes\r"; exp_continue }  ;# 2. 未处理首次连接的 yes/no
    "password:" { send "pass123\r" }           ;# 3. send 缺少 \r（回车）
}
expect {
    "\$ " { send "ls\r" }                      ;# 4. $ 需要转义或使用 -re
    timeout { exit 1 }                          ;# 5. 缺少超时处理
}
expect eof
```
</details>

### 练习 2：编写 FTP 自动登录脚本

```bash
# 使用 expect 实现自动 FTP 登录、下载文件、退出
# FTP 服务器: ftp.example.com, 用户: backup, 密码: ftp123
# 需要下载 /data/report.csv
```

<details>
<summary>答案</summary>

```bash
#!/bin/bash
expect << EOF
set timeout 30
spawn ftp ftp.example.com

expect "Name"
send "backup\r"
expect "Password:"
send "ftp123\r"

expect "ftp>"
send "cd /data\r"
expect "ftp>"
send "get report.csv\r"
expect "ftp>"
send "bye\r"
expect eof
EOF
```
</details>

### 练习 3：安全地传递密码（不使用明文）

```bash
# 如何避免在 expect 脚本中硬编码密码？
```

<details>
<summary>答案</summary>

```bash
# 方法 1：从环境变量读取
expect << EOF
set password \$::env(MY_PASSWORD)
...
send "\$password\r"
EOF

# 方法 2：从加密文件读取
PASSWORD=\$(gpg -dq /etc/credentials/pass.gpg 2>/dev/null)

# 方法 3：从密钥管理服务读取（生产推荐）
PASSWORD=\$(aws secretsmanager get-secret-value \
    --secret-id ssh_password \
    --query SecretString --output text)
```
</details>

---

## 📚 扩展阅读

- [expect 官方文档](https://core.tcl-lang.org/expect/doc/expect.html)
- [Tcl/Tk 教程](https://www.tcl.tk/man/tcl8.6/TclCmd/contents.htm)
- [Ansible vs expect — When to use what](https://docs.ansible.com/)
- `man expect` — expect 命令手册
- 《Exploring Expect》by Don Libes — expect 的权威书籍

### expect 核心命令速查

| 命令 | 语法 | 说明 |
|------|------|------|
| spawn | `spawn prog [args]` | 启动进程 |
| expect | `expect pattern` | 等待匹配 |
| send | `send "text\r"` | 发送文本 |
| interact | `interact` | 交还控制 |
| set timeout | `set timeout N` | 设置超时秒数 |
| exp_continue | `exp_continue` | 继续当前 expect |
| log_file | `log_file file` | 记录会话到文件 |
| log_user | `log_user 0/1` | 控制是否输出到终端 |

---

*由 SRE 学习计划自动生成 | 2026-04-25*
*Generated by Hermes Agent with review*
