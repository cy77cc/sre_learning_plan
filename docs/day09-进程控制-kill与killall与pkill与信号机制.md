# Day 09: 进程控制 — kill/killall/pkill/信号机制

> 📅 日期：2026-04-25
> 📖 学习主题：进程控制 — kill/killall/pkill/信号机制
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 09 的学习后，你应该掌握：
- 理解 Linux 信号（Signal）的本质：内核向进程发送的异步通知机制
- 掌握所有常用信号的含义和使用场景（不只是 SIGTERM 和 SIGKILL）
- 熟练使用 kill/killall/pkill 精确控制进程
- 理解前台/后台进程管理（`&`、`jobs`、`fg`、`bg`、`Ctrl+Z`）
- 掌握 Shell 脚本中的信号捕获（trap）
- 理解 OOM Killer 的工作原理和排障方法

---

## 📖 详细知识点

### 1. 信号（Signal）的本质

#### 1.1 什么是信号

信号是 Linux 内核向进程发送的**异步通知**。进程收到信号后有三选择：
1. **默认处理**（Default）：内核执行默认行为（终止/忽略/停止/继续）
2. **捕获处理**（Catch）：进程注册了信号处理函数（signal handler），执行自定义逻辑
3. **忽略**（Ignore）：进程显式忽略该信号

```
    内核                    进程
     │                       │
     │  ┌─────────────┐      │
     │  │ 事件触发     │      │
     │  │ (用户按键    │      │
     │  │  定时器超时   │      │
     │  │  硬件异常    │      │
     │  │  kill 调用)  │      │
     │  └──────┬──────┘      │
     │         │              │
     │    发送信号 ──────────→│
     │                       │ 检查信号
     │                       │ 执行处理函数/默认行为
     │                       │
```

#### 1.2 查看所有信号

```bash
kill -l
# 输出（共 64 个信号）：
#  1) SIGHUP    2) SIGINT    3) SIGQUIT   4) SIGILL    5) SIGTRAP
#  6) SIGABRT   7) SIGBUS    8) SIGFPE    9) SIGKILL  10) SIGUSR1
# 11) SIGSEGV  12) SIGUSR2  13) SIGPIPE  14) SIGALRM  15) SIGTERM
# 16) SIGSTKFLT 17) SIGCHLD  18) SIGCONT  19) SIGSTOP  20) SIGTSTP
# ...
# 31) SIGSYS   ...           64) SIGRTMAX
```

#### 1.3 常用信号详解

| 编号 | 名称 | 默认行为 | 可否捕获 | 触发方式 | 典型用途 |
|------|------|---------|---------|---------|---------|
| **1** | SIGHUP | 终止 | ✅ | 终端断开 | 守护进程重新加载配置 |
| **2** | SIGINT | 终止 | ✅ | `Ctrl+C` | 中断前台进程 |
| **3** | SIGQUIT | 终止+Core | ✅ | `Ctrl+\` | 生成 core dump |
| **9** | SIGKILL | 终止 | ❌ | kill -9 | 强制杀死（内核直接回收） |
| **15** | SIGTERM | 终止 | ✅ | kill（默认） | 优雅关闭（通知进程自行清理） |
| **17** | SIGCHLD | 忽略 | ✅ | 子进程终止 | 通知父进程回收僵尸 |
| **18** | SIGCONT | 继续 | ❌ | kill -CONT | 恢复被停止的进程 |
| **19** | SIGSTOP | 停止 | ❌ | kill -STOP | 暂停进程执行 |
| **20** | SIGTSTP | 停止 | ✅ | `Ctrl+Z` | 用户暂停前台进程 |
| **24** | SIGXCPU | 终止+Core | ✅ | CPU 时间超限 | 资源限制触发 |

**重要区别：SIGKILL vs SIGTERM**

```
SIGTERM (15) — "请关闭"
  → 进程可以捕获 → 保存数据 → 关闭连接 → 清理临时文件 → 退出
  → 进程可以不处理 → 默认行为是终止

SIGKILL (9) — "立即消失"
  → 进程无法捕获（内核层面拦截）
  → 进程无法清理资源
  → 可能导致：数据丢失、连接泄漏、锁文件残留、共享内存未释放
  → 只用于 SIGTERM 无效的情况
```

#### 1.4 不能被捕获/忽略的信号

| 信号 | 原因 |
|------|------|
| SIGKILL (9) | 内核保证总能终止进程 |
| SIGSTOP (19) | 内核保证总能暂停进程 |

这两个信号是内核硬编码的，任何进程都无法改变它们的默认行为。这是 Linux 安全模型的基础——如果进程可以忽略 SIGKILL，恶意程序就无法被终止。

### 2. 信号发送工具

#### 2.1 kill — 按 PID 发送信号

```bash
# 默认发送 SIGTERM
kill 1234

# 发送指定信号（三种等价写法）
kill -9 1234
kill -SIGKILL 1234
kill -KILL 1234

# 发送 SIGHUP（让 nginx 重新加载配置）
kill -HUP $(cat /var/run/nginx.pid)

# 发送 SIGUSR1（自定义信号，很多程序有特殊含义）
# 例如：让 nginx 重新打开日志文件（日志轮转后使用）
kill -USR1 $(cat /var/run/nginx.pid)

# 检查进程是否存活（不发送任何信号）
kill -0 1234 && echo "进程存在" || echo "进程不存在"
# kill -0 会检查你是否有权限向该进程发信号
# 返回 0 = 进程存在且你有权限
# 返回非 0 = 进程不存在或无权限
```

**kill -0 的陷阱：**
```bash
# 问题：PID 可能被复用！
# 进程 A (PID 1234) 退出后，新进程 B 可能获得 PID 1234
# kill -0 1234 会返回 true，但已经不是原来的进程了

# 更安全的做法：结合 PID 文件和进程名
check_pid() {
    local pid=$1
    local expected_name=$2
    if [ -f "/proc/$pid/comm" ]; then
        local actual_name=$(cat /proc/$pid/comm)
        [ "$actual_name" = "$expected_name" ]
    else
        return 1
    fi
}

if check_pid 1234 "nginx"; then
    echo "nginx 进程 1234 正在运行"
fi
```

#### 2.2 killall — 按进程名发送信号

```bash
# 终止所有名为 nginx 的进程
killall nginx

# 发送指定信号
killall -HUP nginx

# 交互式确认
killall -i nginx
# 输出：Kill nginx(1234) ? (y/N)

# 等待所有目标进程终止（阻塞直到没有匹配的进程）
killall -w nginx

# 按用户终止所有进程
killall -u sreuser

# 匹配不完整的名称（--regexp）
killall --regexp "java|node"
```

**killall 的陷阱：**
```bash
# 在某些系统上（如 Solaris），killall 会杀死所有进程（包括 init）！
# Linux 上的 killall（来自 psmisc 包）只按名称匹配，是安全的

# 确认你用的是 Linux 版本：
which killall
killall --version
# 应该显示：killall (PSmisc) 23.x
```

#### 2.3 pkill — 按模式匹配发送信号

```bash
# 按名称（支持正则）
pkill nginx

# 按完整命令行匹配（-f）
pkill -f "python manage.py runserver"

# 按用户
pkill -u sreuser

# 按终端
pkill -t pts/0

# 按进程年龄（只 kill 运行超过 1 小时的）
pkill --older 1h -f "java -jar"

# 按 CPU 使用率（kill 超过 90% 的）
pkill --signal SIGTERM --oldest -f "java"

# 预览会匹配哪些进程（不实际发送，用 -l 显示）
pkill -l -f "python"
# 输出：
# 1234 python3
# 5678 python

# 只匹配精确名称（-x）
pkill -x bash       # 只匹配名为 "bash" 的进程
pkill bash          # 匹配任何包含 "bash" 的进程名
```

**kill vs killall vs pkill 对比：**

| 工具 | 匹配方式 | 精确度 | 典型场景 |
|------|---------|--------|---------|
| `kill` | PID | 最高（精准到单个进程） | 知道确切 PID |
| `killall` | 精确进程名 | 中（所有同名进程） | 终止某个服务的所有实例 |
| `pkill` | 正则/命令行/用户 | 灵活（支持多种条件） | 按条件批量操作 |

### 3. 前台/后台进程管理

#### 3.1 后台启动

```bash
# 在命令末尾加 & 启动后台进程
sleep 300 &
# 输出：[1] 1234
# [1] = 作业号（job number）
# 1234 = PID

# 后台启动且忽略 SIGHUP（终端关闭后不终止）
nohup ./long-running-script.sh &
# 输出重定向到 nohup.out
nohup ./long-running-script.sh > output.log 2>&1 &

# 使用 disown 从 shell 的作业列表中移除（终端关闭不影响）
./long-running-script.sh &
disown    # 移除最后一个后台作业
disown %1 # 移除作业 1
```

**nohup vs disown 的区别：**
```
nohup：
  → 在启动时就设置忽略 SIGHUP
  → 自动将 stdout/stderr 重定向到 nohup.out
  → 作业仍在 shell 的作业列表中

disown：
  → 在进程启动后从作业列表中移除
  → 不会自动重定向输出
  → 终端关闭后，进程不会被 SIGHUP 杀死
```

#### 3.2 作业控制命令

```bash
# 查看当前 shell 的后台作业
jobs
# 输出示例：
# [1]   Running    sleep 300 &
# [2]-  Stopped    vim config.yaml
# [3]+  Running    tail -f /var/log/syslog &

# 详细信息（含 PID）
jobs -l
# 输出示例：
# [1]  1234 Running    sleep 300 &
# [2]- 5678 Stopped    vim config.yaml

# 将后台作业调到前台
fg          # 默认调最后一个（+ 号标记的）
fg %1       # 调作业 1
fg %2       # 调作业 2

# 在前台运行时：
# Ctrl+Z → 暂停并放回后台（状态变为 Stopped）
# Ctrl+C → 发送 SIGINT 终止进程

# 将暂停的作业在后台继续运行
bg          # 继续最后一个暂停的作业
bg %2       # 继续作业 2

# 终止作业
kill %1     # 向作业 1 发送 SIGTERM
kill %2     # 向作业 2 发送 SIGTERM
```

#### 3.3 前台/后台状态转换图

```
前台运行中
   │
   │ Ctrl+Z (发送 SIGTSTP)
   ▼
后台 Stopped
   │
   │ bg (发送 SIGCONT)
   ▼
后台 Running
   │
   │ fg
   ▼
前台运行中
   │
   │ Ctrl+C (发送 SIGINT)
   ▼
终止
```

### 4. Trap — Shell 脚本中的信号捕获

#### 4.1 基本用法

```bash
# trap 语法
trap '命令' 信号列表

# 示例：捕获 SIGINT（Ctrl+C）和 SIGTERM
trap 'echo "收到终止信号，正在清理..."; rm -f /tmp/my_script_*; exit 0' SIGINT SIGTERM

# 你的主逻辑
for i in {1..100}; do
    echo "处理第 $i 项..."
    touch "/tmp/my_script_$i"
    sleep 1
done

# 清理 trap（取消捕获，恢复默认行为）
trap - SIGINT SIGTERM
```

#### 4.2 优雅关闭脚本的模板

```bash
#!/bin/bash
# graceful_shutdown.sh — 优雅关闭示例

RUNNING=true

cleanup() {
    echo ""
    echo "$(date): 收到终止信号，开始优雅关闭..."
    RUNNING=false

    # 1. 停止接受新请求
    echo "→ 停止监听新连接"

    # 2. 等待正在处理的任务完成
    echo "→ 等待当前任务完成（最多 30 秒）"
    timeout=30
    while [ $timeout -gt 0 ] && pgrep -f "worker" > /dev/null; do
        sleep 1
        ((timeout--))
    done

    # 3. 如果还有残留，强制终止
    if pgrep -f "worker" > /dev/null; then
        echo "→ 强制终止残留进程"
        pkill -9 -f "worker"
    fi

    # 4. 清理临时文件
    rm -f /tmp/worker_*.pid
    rm -f /tmp/worker_*.sock

    # 5. 记录关闭
    echo "$(date): 关闭完成" >> /var/log/myapp.log

    exit 0
}

# 注册信号处理
trap cleanup SIGTERM SIGINT SIGHUP

echo "PID: $$"
echo "启动中... (按 Ctrl+C 优雅关闭)"

# 主循环
while $RUNNING; do
    echo "$(date): 运行中..."
    sleep 5
done
```

#### 4.3 Trap 的常见模式

```bash
# 模式 1：临时禁用信号（关键操作不被中断）
trap '' SIGINT SIGTERM    # 忽略信号
# ... 执行关键操作 ...
trap - SIGINT SIGTERM     # 恢复默认

# 模式 2：只清理一次（防止重复执行）
cleanup_done=false
cleanup() {
    if $cleanup_done; then
        echo "已在清理中，忽略重复信号"
        return
    fi
    cleanup_done=true
    echo "开始清理..."
    # 清理逻辑
}
trap cleanup SIGTERM SIGINT

# 模式 3：EXIT 伪信号（无论正常退出还是异常都执行）
trap 'echo "脚本退出，退出码: $?"' EXIT
# EXIT 在以下情况都会触发：
# - 脚本正常结束
# - exit 命令
# - 收到信号导致终止
# - set -e 触发错误退出

# 模式 4：ERR 伪信号（命令失败时触发）
set -e
trap 'echo "第 $LINENO 行命令失败：$BASH_COMMAND"' ERR
```

### 5. 进程的优先级 — Nice 值

#### 5.1 什么是 Nice 值

Nice 值是 Linux 调度器用来决定**进程相对优先级**的数值：

| Nice 值 | 范围 | 含义 | 权限 |
|---------|------|------|------|
| -20 | 最低 | 最高优先级 | 仅 root |
| 0 | 默认 | 正常优先级 | 所有用户 |
| 19 | 最高 | 最低优先级 | 所有用户 |

**Nice 值越小，优先级越高。** 名字来自 "be nice to other processes"（对其他进程友好 = 降低自己的优先级）。

#### 5.2 使用 nice 和 renice

```bash
# 启动时设置 nice 值
nice -n 10 ./backup.sh        # 低优先级运行备份
nice -n -5 ./realtime-app     # 高优先级运行（需要 sudo）
sudo nice -n -10 ./critical-job

# 调整运行中进程的 nice 值
renice -n 5 -p 1234           # 将 PID 1234 的 nice 调为 5
renice -n -5 -p 1234          # 调为 -5（需要 root）
renice -n 10 -u sreuser       # 将某用户所有进程调为 10

# 查看当前 nice 值
ps -eo pid,ni,comm | head -10

# 批量调整（降低所有 Java 进程的优先级）
pgrep java | xargs -I{} renice -n 10 -p {}
```

**调度器如何使用 Nice 值：**
```
内核的 CFS（完全公平调度器）将 nice 值转换为时间片权重：
  nice 0  → 权重 1024（基准）
  nice -1 → 权重 1277
  nice +1 → 权重 820
  nice +10 → 权重 110

权重决定进程获得 CPU 时间的比例。
nice +19 的进程获得的 CPU 时间只有 nice 0 进程的约 1/100。
```

### 6. OOM Killer — 内存耗尽时的杀手

#### 6.1 什么是 OOM Killer

当系统物理内存 + swap 全部耗尽时，内核的 **Out-Of-Memory Killer** 会选择一个进程杀死，释放内存。

```bash
# OOM Killer 的选择标准（评分越高越容易被杀）：
cat /proc/<PID>/oom_score
# 输出：一个 0~1000 的数字，越大越容易被杀

# 查看评分和调整值
cat /proc/<PID>/oom_score      # 当前评分
cat /proc/<PID>/oom_score_adj  # 用户调整值（-1000 ~ +1000）
```

#### 6.2 OOM Score 计算

```
oom_score ≈ (进程使用内存 / 总内存) × 1000 + oom_score_adj

调整值 oom_score_adj：
  -1000 = 永远不被 OOM Killer 杀死
  0 = 默认
  +1000 = 总是最先被杀
```

```bash
# 保护关键进程（如 sshd）不被 OOM Killer 杀死
echo -1000 > /proc/$(pgrep sshd)/oom_score_adj

# 让某个进程优先被杀（如测试进程）
echo 1000 > /proc/1234/oom_score_adj

# 查看系统中所有进程的 OOM 评分
ps -eo pid,comm,%mem,oom_score --sort=-oom_score | head -20
```

#### 6.3 OOM Killer 日志分析

```bash
# 查看 OOM Killer 历史记录
sudo dmesg -T | grep -i "oom\|killed process\|out of memory"

# 输出示例：
# [Mon Apr 25 14:30:00 2026] java invoked oom-killer: gfp_mask=0x280da, order=0, oom_score_adj=0
# [Mon Apr 25 14:30:00 2026] Out of memory: Killed process 1234 (java) total-vm:2048000kB, anon-rss:1024000kB
# [Mon Apr 25 14:30:00 2026] oom_reaper: reaped process 1234 (java), now anon-rss:0kB

# 解读：
# - java 进程占用了 1GB 物理内存（anon-rss）
# - OOM Killer 选择了它并成功终止
# - oom_reaper 回收了它的内存

# 系统日志中查看
sudo grep -i "oom\|killed process" /var/log/syslog
sudo journalctl -k | grep -i oom
```

#### 6.4 防止 OOM Killer 的 SRE 实践

```bash
# 1. 设置 cgroup 内存限制（Docker 自动使用）
# 限制 Java 进程最多使用 2GB 内存
docker run --memory=2g --memory-swap=2g java-app

# 2. 为关键服务设置低 oom_score_adj
# 在 systemd 单元文件中：
# [Service]
# OOMScoreAdjust=-500

# 3. 配置 earlyoom（比内核 OOM Killer 更早干预）
sudo apt install earlyoom
sudo systemctl enable earlyoom
sudo systemctl start earlyoom
# earlyoom 在内存低于 10% 时主动 kill 最高评分的进程
# 避免系统完全卡死后才能触发 OOM

# 4. 应用程序层面的内存限制
# Java: -Xmx2g
# Python: resource.setrlimit(resource.RLIMIT_AS, (2*1024*1024*1024, -1))
```

---

## 🏗️ 实战场景

### 场景 1：优雅重启 Nginx（零停机）

```bash
# Nginx 支持优雅重启：新配置对新连接生效，已有连接不受影响

# 方法 1：使用 systemctl（推荐）
sudo systemctl reload nginx

# 方法 2：直接发信号
sudo kill -HUP $(cat /var/run/nginx.pid)

# Nginx 收到 SIGHUP 后：
# 1. 检查新配置是否有效（无效则继续使用旧配置）
# 2. 启动新的 worker 进程（使用新配置）
# 3. 旧的 worker 进程处理完已有连接后退出
# 4. 整个过程服务不中断

# 验证是否成功
nginx -t          # 先测试配置
sudo nginx -s reload  # nginx 自带的 reload 命令（等价于 kill -HUP）

# 观察旧 worker 退出
watch -n 1 'ps aux | grep "nginx: worker" | grep -v grep'
# 你会看到旧的 worker PID 消失，新的 PID 出现
```

### 场景 2：批量终止异常进程

```bash
# 场景：某 Bug 导致系统产生了 100+ 个卡死的 python 进程

# 方法 1：pkill（最简单）
pkill -f "python worker.py"

# 方法 2：kill + pgrep（更灵活）
pgrep -f "python worker.py" | xargs kill -15

# 如果部分进程不响应 SIGTERM，用 SIGKILL
pgrep -f "python worker.py" | xargs kill -9

# 方法 3：两阶段终止（优雅 + 强制）
# 先 SIGTERM，等待 5 秒，还活着的用 SIGKILL
pgrep -f "python worker.py" | while read pid; do
    kill -15 "$pid"
done
sleep 5
# 检查还有没有活着的
pgrep -f "python worker.py" | while read pid; do
    echo "强制杀死 PID $pid"
    kill -9 "$pid"
done

# 方法 4：使用 timeout
timeout 5 bash -c 'kill $(pgrep -f "python worker.py"); while pgrep -f "python worker.py" > /dev/null; do sleep 0.5; done'
# 5 秒后如果还有进程存活，timeout 会终止这个等待循环
# 然后你再手动 SIGKILL
```

### 场景 3：脚本被意外中断时的自我保护

```bash
#!/bin/bash
# safe_deploy.sh — 部署脚本，确保被中断时回滚

set -euo pipefail

DEPLOYED=false
TEMP_DIR=$(mktemp -d)

# 清理函数
rollback() {
    local exit_code=$?
    echo ""
    echo "⚠️  脚本异常退出（退出码: $exit_code）"

    if $DEPLOYED; then
        echo "🔄 执行回滚..."
        # 回滚逻辑
        rm -rf /opt/app/current
        ln -s /opt/app/backup /opt/app/current
        systemctl restart myapp
        echo "✅ 回滚完成"
    else
        echo "⏹️ 部署未完成，无需回滚"
    fi

    # 清理临时文件
    rm -rf "$TEMP_DIR"
    echo "🧹 临时文件已清理"

    exit $exit_code
}

# 注册退出时的清理（无论什么原因退出都会执行）
trap rollback EXIT
# 注册信号处理（提前捕获并正常退出，触发上面的 EXIT trap）
trap 'exit 130' SIGINT
trap 'exit 143' SIGTERM

# 主部署逻辑
echo "开始部署..."
cp -r /opt/app/build/* "$TEMP_DIR/"
echo "备份当前版本..."
rm -rf /opt/app/backup
cp -r /opt/app/current /opt/app/backup
echo "切换新版本..."
rm -rf /opt/app/current
ln -s "$TEMP_DIR" /opt/app/current
DEPLOYED=true
echo "重启服务..."
systemctl restart myapp
echo "健康检查..."
curl -sf http://localhost:8080/health || { echo "健康检查失败"; exit 1; }

echo "✅ 部署成功"
```

---

## 🧪 练习题

### 练习 1：信号识别

以下场景分别应该发送什么信号？

1. 让 Nginx 重新加载配置而不中断现有连接
2. 强制杀死一个无响应的进程
3. 暂停一个正在运行的前台进程
4. 让进程在后台继续运行（从暂停状态恢复）
5. 优雅关闭一个数据库进程（让它先刷盘再退出）

<details>
<summary>答案</summary>

1. `kill -HUP <PID>` 或 `systemctl reload nginx`
2. `kill -9 <PID>` 或 `kill -KILL <PID>`
3. `Ctrl+Z`（发送 SIGTSTP）或 `kill -STOP <PID>`
4. `bg`（发送 SIGCONT）或 `kill -CONT <PID>`
5. `kill -TERM <PID>`（让进程执行 cleanup 后自行退出）
</details>

### 练习 2：trap 脚本

编写一个脚本，创建一个临时文件，运行 `sleep 100`，如果脚本被中断（Ctrl+C 或 kill），删除临时文件后退出。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
TMPFILE=$(mktemp /tmp/myapp.XXXXXX)
echo "临时文件: $TMPFILE"

trap 'echo "收到中断信号，清理临时文件..."; rm -f "$TMPFILE"; exit 0' SIGINT SIGTERM

echo "运行中... (PID: $$)"
sleep 100
rm -f "$TMPFILE"
```
</details>

### 练习 3：OOM 排查

服务器上的 Java 进程突然消失，怀疑是 OOM Killer。请写出排查步骤。

<details>
<summary>答案</summary>

```bash
# 1. 查看内核日志
sudo dmesg -T | grep -i "oom\|killed process"

# 2. 查看 syslog
sudo grep -i "out of memory\|oom" /var/log/syslog

# 3. 查看 journal
sudo journalctl -k --since "1 hour ago" | grep -i oom

# 4. 确认是 OOM 后，检查系统内存
free -h

# 5. 检查 Java 进程的内存限制
# 如果是容器环境：
cat /sys/fs/cgroup/memory/memory.limit_in_bytes

# 6. 修复方案：
# - 增加 -Xmx 参数限制 Java 堆大小
# - 增加容器内存限制
# - 设置 OOMScoreAdjust 保护关键进程
```
</details>

---

## 📚 扩展阅读

- `man 7 signal` — Linux 信号的完整文档
- [Julia Evans — Linux Signals](https://jvns.ca/blog/2014/07/31/what-happens-when-you-ctrl-c/) — 通俗易懂的信号入门
- [The Linux Programming Interface — Chapter 20](https://www.nostarch.com/tlpi.htm) — 信号章节（Michael Kerrisk）
- [Systemd OOMScoreAdjust](https://www.freedesktop.org/software/systemd/man/systemd.exec.html#OOMScoreAdjust=) — systemd 的 OOM 保护
- [earlyoom](https://github.com/rfjakob/earlyoom) — 用户态 OOM 预防工具
