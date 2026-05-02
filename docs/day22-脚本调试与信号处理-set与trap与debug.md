# Day 22: 脚本调试与信号处理 — set、trap 与 Debug

> 📅 日期：2026-04-25
> 📖 学习主题：脚本调试与信号处理 — set、trap 与 Debug
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 22 的学习后，你应该掌握：
- 理解 `set -e`、`set -u`、`set -o pipefail` 的工作机制和陷阱
- 掌握 `trap` 命令处理信号和 EXIT 清理的完整用法
- 熟练使用 `set -x`、`BASH_XTRACEFD` 进行脚本调试
- 理解 Linux 信号模型（SIGINT、SIGTERM、SIGHUP 等）与进程行为
- 能够编写具有生产级健壮性的 Bash 脚本

---

## 📖 底层原理详解

### 1. set 选项：脚本安全模式

#### 1.1 `set -e`（errexit）

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

#### 1.2 `set -u`（nounset）

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

#### 1.3 `set -o pipefail`

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

#### 1.4 标准安全模式模板

```bash
#!/bin/bash
# 每个生产脚本的标准开头
set -euo pipefail

# 可选：IFS 设置
IFS=$'\n\t'

# 可选：更改 umask
umask 077  # 新文件权限为 700
```

### 2. trap：信号处理与清理

#### 2.1 Linux 信号模型

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

#### 2.2 trap 基本语法

```bash
trap '命令' 信号 [信号 ...]
trap 函数名 信号 [信号 ...]
trap - 信号     # 恢复默认行为
trap -p         # 显示当前所有 trap
trap            # 显示 EXIT trap
```

#### 2.3 EXIT 清理

```bash
#!/bin/bash
set -euo pipefail

# 创建临时文件
TMPDIR=$(mktemp -d /tmp/sre_task.XXXXXX)
TMPFILE="$TMPDIR/data.csv"

# 注册清理函数
cleanup() {
    echo "🧹 清理临时文件: $TMPDIR"
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

#### 2.4 优雅关闭（Graceful Shutdown）

```bash
#!/bin/bash
set -euo pipefail

RUNNING=true

graceful_shutdown() {
    echo "📥 收到关闭信号，等待当前任务完成..."
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

echo "👋 服务已安全关闭"
```

**关键技巧**：`wait $!` 在收到信号时会返回非零退出码，使用 `|| true` 防止 `set -e` 导致脚本意外退出循环。

#### 2.5 ERR trap：全局错误处理

```bash
#!/bin/bash
set -euo pipefail

# ERR trap 会在任何命令失败时触发
error_handler() {
    local exit_code=$?
    local line_number=$1
    echo "❌ 错误！命令退出码: $exit_code, 行号: $line_number"
    echo "   调用栈: ${BASH_SOURCE[@]}"
    echo "   函数调用: ${FUNCNAME[@]}"
}
trap 'error_handler ${LINENO}' ERR

# 测试
echo "正常行"
false    # 触发 ERR trap
echo "不会执行"
```

#### 2.6 DEBUG trap：逐行追踪

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

### 3. 调试技巧

#### 3.1 set -x（xtrace）

```bash
#!/bin/bash
set -x  # 开启调试

name="Alice"
age=30
echo "Hello $name, age $age"

set +x  # 关闭调试

echo "这行不会被追踪"
```

输出：
```
+ name=Alice
+ age=30
+ echo 'Hello Alice, age 30'
Hello Alice, age 30
+ set +x
这行不会被追踪
```

#### 3.2 选择性调试：将追踪输出重定向

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

#### 3.3 条件调试：仅在环境变量存在时开启

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

#### 3.4 使用 bash -x 运行脚本

```bash
# 方法 1：直接运行
bash -x script.sh

# 方法 2：只追踪特定部分
bash -x script.sh 2>debug.log

# 方法 3：部分追踪
bash -x script.sh -  # 从 stdin 读取（结合 heredoc）
```

---

## 💻 SRE 实战场景

### 场景 1：生产部署脚本（含完整错误处理与清理）

```bash
#!/bin/bash
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
        log "❌ 部署失败！退出码: $exit_code"
        if [[ -d "$BACKUP_DIR" ]]; then
            log "🔄 尝试回滚..."
            rm -rf "$APP_DIR/current"
            cp -a "$BACKUP_DIR" "$APP_DIR/current"
            log "✅ 回滚完成"
        fi
    else
        log "✅ 部署成功"
        # 清理旧备份（保留最近 5 个）
        ls -td /opt/myapp_backup_* 2>/dev/null | tail -n +6 | xargs rm -rf
    fi
}
trap cleanup EXIT

# 优雅关闭处理
shutdown() {
    log "📥 收到中断信号，清理中..."
    exit 130  # Ctrl+C 标准退出码
}
trap shutdown SIGINT SIGTERM

log "🚀 开始部署..."

# 1. 备份当前版本
log "📦 创建备份: $BACKUP_DIR"
cp -a "$APP_DIR/current" "$BACKUP_DIR"

# 2. 下载新版本
log "📥 下载: $DEPLOY_URL"
curl -fSL --connect-timeout 10 --max-time 300 \
    -o /tmp/myapp-new.tar.gz "$DEPLOY_URL"

# 3. 解压并部署
log "📂 解压部署..."
tar xzf /tmp/myapp-new.tar.gz -C "$APP_DIR"
rm -f "$APP_DIR/current"
ln -s "$APP_DIR/myapp-v2.0" "$APP_DIR/current"

# 4. 健康检查
log "🏥 执行健康检查..."
sleep 2
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8080/health || echo "000")
if [[ "$HTTP_CODE" != "200" ]]; then
    log "❌ 健康检查失败！HTTP $HTTP_CODE"
    exit 1
fi

log "🎉 部署完成，健康检查通过"
```

### 场景 2：信号处理守护进程

```bash
#!/bin/bash
set -euo pipefail

# 模拟一个 SRE 监控守护进程
PID_FILE="/var/run/sre_monitor.pid"

cleanup() {
    echo "清理 PID 文件并退出"
    rm -f "$PID_FILE"
    exit 0
}

reload_config() {
    echo "🔄 重新加载配置文件..."
    # 实际场景：重新读取配置文件
}

# 写入 PID
echo $$ > "$PID_FILE"

# 注册信号处理
trap cleanup EXIT SIGTERM SIGINT
trap reload_config SIGHUP

echo "监控守护进程启动，PID=$$"

while true; do
    # 使用 sleep 等待，可被信号中断
    sleep 60 &
    wait $! 2>/dev/null || true

    # 执行监控任务
    echo "$(date) 检查完成"
done
```

---

## 🧪 练习题

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

<details>
<summary>答案</summary>

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
        echo "✅ 备份了 $f"
    else
        echo "❌ 备份失败: $f" >&2
    fi
done
```
</details>

### 练习 2：实现带超时的 trap 处理
```bash
# 编写脚本：trap SIGTERM，但如果 10 秒内没有完成清理，强制退出
```

<details>
<summary>答案</summary>

```bash
#!/bin/bash
set -euo pipefail

CLEANUP_DONE=false

forced_exit() {
    echo "⏰ 清理超时，强制退出"
    exit 1
}

graceful_shutdown() {
    echo "📥 收到 SIGTERM，开始清理..."
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
</details>

### 练习 3：调试输出分析
```bash
# 设置 set -x 后，以下脚本的调试输出是什么？
set -x
name="World"
echo "Hello $name"
false || echo "recovered"
```

<details>
<summary>答案</summary>

```
+ name=World
+ echo 'Hello World'
Hello World
+ false
+ echo recovered
recovered
```

`set -x` 显示每条命令的执行过程，`$name` 已被展开。注意 `||` 链中的 `false` 也会被追踪。
</details>

---

## 📚 扩展阅读

- [Bash Manual — The Set Builtin](https://www.gnu.org/software/bash/manual/bash.html#The-Set-Builtin)
- [Bash Manual — Trap Builtin](https://www.gnu.org/software/bash/manual/bash.html#Trap-Builtin)
- [David Pashley: Writing Robust Bash Shell Scripts](http://www.davidpashley.com/articles/writing-robust-shell-scripts/) — 经典文章
- [Greg's Wiki: Bash Pitfalls](http://mywiki.wooledge.org/BashPitfalls) — Bash 常见陷阱汇总
- [BashFAQ/105: Why doesn't set -e catch errors in pipelines?](http://mywiki.wooledge.org/BashFAQ/105)
- `man 7 signal` — Linux 信号手册页

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

*由 SRE 学习计划自动生成 | 2026-04-25*
*Generated by Hermes Agent with review*
