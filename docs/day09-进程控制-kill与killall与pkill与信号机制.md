# Day 09: 进程控制 — kill/killall/pkill/信号机制

> 📅 日期：2026-05-02
> 📖 学习主题：进程控制 — kill/killall/pkill/信号机制
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 08（进程管理基础）

## 🎯 学习目标

完成 Day 09 的学习后，你应该能够：
- 深入理解 Linux 信号机制的完整流程（产生→传递→处理）
- 掌握所有常用信号的含义、默认行为和使用场景
- 熟练使用 kill/killall/pkill/killall5 精确控制进程
- 理解进程优先级（nice/renice）和 CFS 调度器原理
- 掌握后台作业管理（&/jobs/fg/bg/nohup/disown）
- 理解进程组、会话和守护进程化（setsid）
- 独立完成优雅关闭、配置重载、D 状态进程排查等实战任务

---

## 📖 核心知识点

### 1. Linux 信号机制深入

#### 1.1 什么是信号

信号是 Linux 内核向进程发送的**异步通知机制**。它是进程间通信（IPC）最古老、最简单的方式。信号可以在任何时候发送给进程，进程不需要轮询。

```
信号的生命周期：

  ┌─────────────────────────────────────────────────────────────┐
  │                    信号的产生                                │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
  │  │ 用户按键  │  │ kill()   │  │ 内核异常  │  │ 定时器    │   │
  │  │ Ctrl+C   │  │ 系统调用  │  │ SIGSEGV  │  │ SIGALRM  │   │
  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
  │       └──────────────┴──────────────┴──────────────┘        │
  │                          │                                  │
  │                    信号被生成                                │
  └──────────────────────────┼──────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                    信号的传递                                │
  │                                                             │
  │  内核将信号信息写入目标进程的 task_struct                    │
  │  → sigpending 队列中增加一个待处理信号                       │
  │  → 如果信号被阻塞（blocked），信号留在队列中等待             │
  │  → 如果信号未被阻塞，在进程返回用户态时触发处理             │
  │                                                             │
  └──────────────────────────┼──────────────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                    信号的处理                                │
  │                                                             │
  │  进程在返回用户态前检查 sigpending                           │
  │  → 如果有信号处理函数（signal handler）：执行自定义函数     │
  │  → 如果是默认行为：内核执行（终止/忽略/停止/继续/core dump）│
  │  → 如果是忽略：丢弃信号                                     │
  │                                                             │
  │  SIGKILL 和 SIGSTOP 不能被捕获或忽略（内核硬编码）           │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

#### 1.2 信号的三种处理方式

| 处理方式 | 说明 | 示例 |
|---------|------|------|
| **默认处理** | 内核执行预定义行为 | SIGTERM 默认终止进程 |
| **捕获处理** | 进程注册信号处理函数 | trap 'cleanup' SIGTERM |
| **忽略** | 进程显式忽略该信号 | trap '' SIGINT |

```
默认行为的分类：

  终止（Terminate）：
    → 进程被杀死
    → SIGTERM, SIGINT, SIGHUP, SIGKILL, SIGPIPE, SIGALRM...

  终止 + Core Dump：
    → 进程被杀死，同时生成核心转储文件
    → SIGQUIT, SIGABRT, SIGSEGV, SIGBUS, SIGFPE, SIGILL...

  停止（Stop）：
    → 进程暂停执行
    → SIGSTOP, SIGTSTP, SIGTTIN, SIGTTOU

  继续（Continue）：
    → 恢复被停止的进程
    → SIGCONT

  忽略（Ignore）：
    → 信号被丢弃
    → SIGCHLD（默认忽略）, SIGURG, SIGWINCH...
```

#### 1.3 查看所有信号

```bash
kill -l
# 输出（共 64 个信号）：
#  1) SIGHUP    2) SIGINT    3) SIGQUIT   4) SIGILL    5) SIGTRAP
#  6) SIGABRT   7) SIGBUS    8) SIGFPE    9) SIGKILL  10) SIGUSR1
# 11) SIGSEGV  12) SIGUSR2  13) SIGPIPE  14) SIGALRM  15) SIGTERM
# 16) SIGSTKFLT 17) SIGCHLD  18) SIGCONT  19) SIGSTOP  20) SIGTSTP
# 21) SIGTTIN   22) SIGTTOU  23) SIGURG   24) SIGXCPU  25) SIGXFSZ
# 26) SIGVTALRM 27) SIGPROF  28) SIGWINCH 29) SIGIO    30) SIGPWR
# 31) SIGSYS    33) SIGRTMIN 34) SIGRTMIN+1 ... 64) SIGRTMAX

# 带描述的查看
kill -l | tr ' ' '\n' | while read sig; do
    if [[ "$sig" =~ ^[0-9]+$ ]]; then
        echo "$sig: $(kill -l $sig)"
    fi
done
```

#### 1.4 所有信号详解

**用户常用信号：**

| 编号 | 名称 | 默认行为 | 可否捕获 | 触发方式 | 典型用途 |
|------|------|---------|---------|---------|---------|
| **1** | SIGHUP | 终止 | Yes | 终端断开 / kill -1 | 守护进程重载配置 |
| **2** | SIGINT | 终止 | Yes | Ctrl+C | 中断前台进程 |
| **3** | SIGQUIT | 终止+Core | Yes | Ctrl+\ | 生成 core dump |
| **9** | SIGKILL | 终止 | **No** | kill -9 | 强制杀死（内核直接处理） |
| **15** | SIGTERM | 终止 | Yes | kill（默认） | 优雅关闭（通知进程清理） |
| **17** | SIGCHLD | 忽略 | Yes | 子进程终止 | 通知父进程回收僵尸 |
| **18** | SIGCONT | 继续 | No | kill -18 | 恢复被停止的进程 |
| **19** | SIGSTOP | 停止 | **No** | kill -19 | 暂停进程（不可捕获） |
| **20** | SIGTSTP | 停止 | Yes | Ctrl+Z | 用户暂停前台进程 |

**用户自定义信号：**

| 编号 | 名称 | 默认行为 | 说明 |
|------|------|---------|------|
| **10** | SIGUSR1 | 终止 | 用户自定义，应用可赋予特殊含义 |
| **12** | SIGUSR2 | 终止 | 用户自定义，应用可赋予特殊含义 |
| **13** | SIGPIPE | 终止 | 向无读者的管道/socket 写数据 |
| **14** | SIGALRM | 终止 | alarm()/setitimer() 定时器到期 |

**资源限制信号：**

| 编号 | 名称 | 说明 |
|------|------|------|
| **24** | SIGXCPU | CPU 时间超过 RLIMIT_CPU |
| **25** | SIGXFSZ | 文件大小超过 RLIMIT_FSIZE |

**调试相关信号：**

| 编号 | 名称 | 说明 |
|------|------|------|
| **4** | SIGILL | 非法指令 |
| **5** | SIGTRAP | 断点/跟踪陷阱（gdb 使用） |
| **6** | SIGABRT | abort() 调用 |
| **7** | SIGBUS | 总线错误（内存对齐问题） |
| **8** | SIGFPE | 浮点异常（除零） |
| **11** | SIGSEGV | 段错误（非法内存访问） |
| **31** | SIGSYS | 非法系统调用 |

**实时信号（SIGRTMIN ~ SIGRTMAX）：**

```bash
# 实时信号（34-64）的特点：
# 1. 编号不固定（SIGRTMIN 在不同系统可能不同）
# 2. 支持排队（同一信号可以多次传递）
# 3. 传递顺序有保证
# 4. 可以携带附加数据（sigqueue()）

# 普通信号（1-31）的问题：
# 如果同一信号发送多次，可能只收到一次（信号丢失）
# 传递顺序不保证

# 使用实时信号
kill -SIGRTMIN+1 <PID>
# 或
kill -35 <PID>
```

**SIGHUP 详解 — 远不止"终端断开"：**

```
SIGHUP 的三种含义：

1. 终端断开时发送给终端的前台进程组
   → SSH 连接断开、终端窗口关闭
   → 所有关联到该终端的进程都会收到 SIGHUP

2. 守护进程的"重载配置"信号
   → nginx -s reload = kill -HUP <nginx_pid>
   → 让进程重新读取配置文件而不中断服务
   → 这是约定俗成，不是内核强制的

3. nohup/disown 的作用
   → nohup: 启动时忽略 SIGHUP
   → disown: 从 shell 作业列表中移除，shell 退出时不发 SIGHUP
```

**SIGPIPE 详解 — 常被忽略的杀手：**

```bash
# SIGPIPE 在以下情况触发：
# 向一个已经关闭读端的管道或 socket 写数据

# 典型场景：
# 1. 管道下游进程已退出
echo "test" | head -1  # head 读完一行退出，echo 写第二次时收到 SIGPIPE

# 2. 客户端断开连接后服务端继续写
# nginx 访问一个已断开的客户端 → 收到 SIGPIPE → 默认终止

# 3. 很多程序忽略 SIGPIPE
# Python 默认忽略 SIGPIPE
# Java 默认忽略 SIGPIPE
# Nginx 忽略 SIGPIPE

# 忽略 SIGPIPE 的方法：
trap '' SIGPIPE        # Shell
signal(SIGPIPE, SIG_IGN)  # C
```

### 2. 信号发送工具

#### 2.1 kill — 按 PID 发送信号

```bash
# 默认发送 SIGTERM (15)
kill 1234

# 发送指定信号（三种等价写法）
kill -9 1234
kill -SIGKILL 1234
kill -KILL 1234

# 发送 SIGHUP（让 nginx 重新加载配置）
kill -HUP $(cat /var/run/nginx.pid)

# 发送 SIGUSR1（很多程序有特殊含义）
# nginx：重新打开日志文件（日志轮转后使用）
kill -USR1 $(cat /var/run/nginx.pid)

# 发送 SIGUSR2（Go 程序：触发 GC）
kill -USR2 $(pgrep myapp | head -1)

# 向进程组发信号（注意负号）
kill -TERM -<PGID>   # 杀死整个进程组

# 检查进程是否存活（不发送任何信号）
kill -0 1234 && echo "进程存在" || echo "进程不存在"
```

**kill -0 的陷阱：**

```bash
# kill -0 不发送信号，只检查进程是否存在
# 返回 0 = 进程存在且你有权限
# 返回非 0 = 进程不存在或无权限

# 陷阱：PID 可能被复用！
# 进程 A (PID 1234) 退出后，新进程 B 可能获得 PID 1234
# kill -0 1234 会返回 true，但已经不是原来的进程了

# 更安全的做法：结合 /proc 和进程名
check_pid() {
    local pid=$1
    local expected_name=$2
    if [ -f "/proc/$pid/comm" ]; then
        local actual_name=$(cat /proc/$pid/comm 2>/dev/null)
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
killall -s SIGUSR1 nginx

# 交互式确认
killall -i nginx
# 输出：Kill nginx(1234) ? (y/N)

# 等待所有目标进程终止（阻塞直到没有匹配的进程）
killall -w nginx

# 按用户终止所有进程
killall -u sreuser

# 精确匹配进程名（不是部分匹配）
killall -exact nginx

# 匹配不完整的名称
killall --regexp "java|node"

# 只对最旧的进程发送信号
killall -o nginx    # o = oldest

# 只对最新的进程发送信号
killall -y nginx    # y = youngest
```

**killall 的平台差异：**

```bash
# Linux 上的 killall（来自 psmisc 包）只按名称匹配，是安全的
# Solaris/HP-UX 上的 killall 会杀死所有进程（包括 init）！

# 确认你用的是 Linux 版本：
which killall
killall --version
# 应该显示：killall (PSmisc) 23.x

# 跨平台脚本中避免使用 killall，用 pkill 替代
```

#### 2.3 pkill — 按模式匹配发送信号

```bash
# 按名称（支持正则）
pkill nginx

# 按完整命令行匹配（-f）—— 非常有用！
pkill -f "python manage.py runserver"
pkill -f "java -jar.*myapp"

# 按用户
pkill -u sreuser
pkill -u sreuser,deployer  # 多个用户

# 按终端
pkill -t pts/0

# 按进程年龄（只 kill 运行超过 1 小时的）
pkill --older 1h -f "java -jar"

# 按会话 ID
pkill -s <SID>

# 只匹配精确名称（-x）
pkill -x bash       # 只匹配名为 "bash" 的进程
pkill bash          # 匹配任何包含 "bash" 的进程名

# 预览会匹配哪些进程（不实际发送信号）
pgrep -la nginx     # 显示 PID 和完整命令
pgrep -la -f "python"

# 信号 + 匹配
pkill -SIGUSR1 -f "myapp"
pkill -s SIGHUP nginx
```

#### 2.4 killall5 — 杀死所有进程（慎用）

```bash
# killall5 是 SysV init 系统的一部分
# 向除自己和特殊进程外的所有进程发送信号

# 发送 SIGTERM 给所有进程
killall5 -15

# 不要杀死的进程（通过 PID 文件）
killall5 -o /run/my.pid   # 排除 PID 文件中的进程

# 通常只在系统关机/重启时使用
# 日常管理中不要使用！
```

#### 2.5 kill vs killall vs pkill 对比

| 工具 | 匹配方式 | 精确度 | 典型场景 |
|------|---------|--------|---------|
| `kill` | PID | 最高（单个进程） | 知道确切 PID |
| `killall` | 精确进程名 | 中（所有同名进程） | 终止某个服务的所有实例 |
| `pkill` | 正则/命令行/用户 | 灵活（多种条件） | 按条件批量操作 |
| `killall5` | 所有进程 | 最低（全部） | 系统关机 |

```bash
# 选择指南：
# 知道 PID → kill
# 知道进程名 → killall 或 pkill -x
# 需要按命令行/用户/年龄匹配 → pkill -f
# 需要等待进程终止 → killall -w
```

### 3. 进程优先级 — nice/renice 和 CFS 调度器

#### 3.1 Nice 值

Nice 值是 Linux 调度器用来决定**进程相对优先级**的数值：

| Nice 值 | 范围 | 含义 | 权限 |
|---------|------|------|------|
| -20 | 最低 | 最高优先级 | 仅 root |
| 0 | 默认 | 正常优先级 | 所有用户 |
| 19 | 最高 | 最低优先级 | 所有用户 |

**Nice 值越小，优先级越高。** 名字来自 "be nice to other processes"（对其他进程友好 = 降低自己的优先级）。

#### 3.2 CFS 调度器简介

Linux 默认使用 CFS（Completely Fair Scheduler，完全公平调度器）：

```
CFS 的核心思想：
  → 每个进程获得的 CPU 时间与其权重成正比
  → 权重由 nice 值决定
  → 使用红黑树组织所有可运行进程
  → 每次调度选择"虚拟运行时间"最小的进程

权重映射表（kernel/sched/core.c）：
  nice -20 → 权重 88768
  nice -10 → 权重 26937
  nice   0 → 权重 1024  （基准）
  nice   5 → 权重 335
  nice  10 → 权重 110
  nice  19 → 权重 15

CPU 时间分配：
  进程 A (nice 0, 权重 1024) 和 进程 B (nice 10, 权重 110)
  → A 获得 1024/(1024+110) = 90.3% 的 CPU
  → B 获得 110/(1024+110) = 9.7% 的 CPU
```

#### 3.3 使用 nice 和 renice

```bash
# 启动时设置 nice 值
nice -n 10 ./backup.sh        # 低优先级运行备份
nice -n -5 ./realtime-app     # 高优先级运行（需要 sudo）
sudo nice -n -10 ./critical-job

# 调整运行中进程的 nice 值
renice -n 5 -p 1234           # 将 PID 1234 的 nice 调为 5
renice -n -5 -p 1234          # 调为 -5（需要 root）
renice -n 10 -u sreuser       # 将某用户所有进程调为 10
renice -n 10 -g <PGID>        # 调整进程组的优先级

# 查看当前 nice 值
ps -eo pid,ni,comm | head -10

# 批量调整（降低所有 Java 进程的优先级）
pgrep java | xargs -I{} renice -n 10 -p {}
```

#### 3.4 实时调度策略

```bash
# 除了 CFS 的 nice 值，还有实时调度策略
# SCHED_FIFO  - 先来先服务，不抢占同优先级进程
# SCHED_RR    - 轮转调度，同优先级进程轮流执行

# 使用 chrt 命令设置实时调度
sudo chrt -f 50 ./realtime-app    # FIFO 策略，优先级 50
sudo chrt -r 50 ./realtime-app    # RR 策略，优先级 50

# 查看进程的调度策略
chrt -p <PID>

# 实时进程优先级范围：1-99（99 最高）
# 注意：实时进程会抢占所有普通进程，慎用！
```

### 4. 后台作业管理

#### 4.1 后台启动

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

# 使用 disown 从 shell 的作业列表中移除
./long-running-script.sh &
disown    # 移除最后一个后台作业
disown %1 # 移除作业 1
disown -a # 移除所有作业
```

**nohup vs disown vs setsid 的区别：**

```
nohup：
  → 在启动时就设置忽略 SIGHUP
  → 自动将 stdout/stderr 重定向到 nohup.out
  → 作业仍在 shell 的作业列表中

disown：
  → 在进程启动后从作业列表中移除
  → 不会自动重定向输出
  → 终端关闭后，shell 退出时不会向该进程发送 SIGHUP

setsid：
  → 创建新的会话（session），进程成为新会话的 leader
  → 完全脱离当前终端
  → 即使当前终端关闭，进程也不会收到 SIGHUP

推荐：
  简单场景 → nohup
  已经启动的进程 → disown
  需要完全脱离终端 → setsid
  生产环境 → 使用 systemd 管理
```

#### 4.2 作业控制命令

```bash
# 查看当前 shell 的后台作业
jobs
# 输出示例：
# [1]   Running    sleep 300 &
# [2]-  Stopped    vim config.yaml
# [3]+  Running    tail -f /var/log/syslog &

# 符号说明：
# +  = 当前作业（fg 默认选择的）
# -  = 下一个作业
# 无标记 = 其他作业

# 详细信息（含 PID）
jobs -l

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
kill -9 %1  # 向作业 1 发送 SIGKILL

# 删除作业记录（不终止进程）
jobs -d %1
```

#### 4.3 前台/后台状态转换图

```
前台运行中 (R+)
   │
   │ Ctrl+Z (发送 SIGTSTP)
   ▼
后台 Stopped (T)
   │
   │ bg (发送 SIGCONT)
   ▼
后台 Running (R)
   │
   │ fg
   ▼
前台运行中 (R+)
   │
   │ Ctrl+C (发送 SIGINT)
   ▼
终止
```

### 5. 进程组和会话

#### 5.1 进程组（Process Group）

```
进程组是一组相关进程的集合，通常是一个管道中的所有进程。

示例：ls | grep foo | wc -l
  → ls 进程（PID 100）
  → grep 进程（PID 101）
  → wc 进程（PID 102）
  → 三个进程属于同一个进程组
  → 进程组 ID（PGID）= 领头进程的 PID = 100

信号可以发送给整个进程组：
  kill -TERM -<PGID>  # 注意负号
  kill -TERM -100     # 杀死 PID 100 所在的进程组
```

#### 5.2 会话（Session）

```
会话是一个或多个进程组的集合。

  ┌─────────────────────────────────────────┐
  │                会话（Session）            │
  │                                          │
  │  ┌────────────────┐  ┌────────────────┐  │
  │  │ 前台进程组      │  │ 后台进程组      │  │
  │  │ ls | grep foo  │  │ sleep 300 &    │  │
  │  │ PGID = 100     │  │ PGID = 200     │  │
  │  └────────────────┘  └────────────────┘  │
  │                                          │
  │  会话首进程（Session Leader）= shell      │
  │  控制终端（Controlling Terminal）= pts/0  │
  │                                          │
  └─────────────────────────────────────────┘

会话首进程（通常是 shell）退出时：
  → 向所有前台进程组发送 SIGHUP
  → 后台进程组也会收到 SIGHUP（取决于 shell 配置）
```

#### 5.3 setsid — 创建新会话

```bash
# setsid 创建新的会话，进程成为会话首进程
# 完全脱离当前终端

# 在脚本中使用
#!/bin/bash
# daemonize.sh — 将进程转为守护进程

# 第一步：fork，父进程退出
if [ "$(id -u)" -ne 0 ]; then
    setsid "$0" "$@" &
    exit 0
fi

# 第二步：创建新会话（setsid 已完成）
# 第三步：再次 fork（防止会话首进程获取控制终端）
# 第四步：改变工作目录
cd /

# 第五步：关闭标准文件描述符
exec 0>/dev/null
exec 1>/dev/null
exec 2>/dev/null

# 现在是一个标准的守护进程了
exec /opt/myapp/server
```

#### 5.4 守护进程（Daemon）的特征

```
守护进程的标准特征：
  1. 父进程是 PID 1（systemd/init）
  2. 是会话首进程（SID = PID）
  3. 没有关联的控制终端（TTY = ?）
  4. 工作目录是 /（或某个特定目录）
  5. 标准文件描述符指向 /dev/null
  6. 在后台运行

# 查看守护进程
ps -eo pid,sid,tty,comm | awk '$3 == "?"' | head -20

# 创建简单守护进程的两种方式：
# 方式 1：使用 daemon() 函数（C 语言）
# 方式 2：使用 systemd（推荐，Day 10 详细讲解）
# 方式 3：使用 nohup + disown（临时方案）
```

### 6. Trap — Shell 脚本中的信号捕获

#### 6.1 基本用法

```bash
# trap 语法
trap '命令' 信号列表

# 示例：捕获 SIGINT（Ctrl+C）和 SIGTERM
trap 'echo "收到终止信号，正在清理..."; rm -f /tmp/my_script_*; exit 0' SIGINT SIGTERM

# 清理 trap（取消捕获，恢复默认行为）
trap - SIGINT SIGTERM
```

#### 6.2 优雅关闭脚本的模板

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

#### 6.3 Trap 的常见模式

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
trap 'echo "脚本退出，退出码: $?"; rm -f /tmp/lockfile' EXIT

# 模式 4：ERR 伪信号（命令失败时触发）
set -euo pipefail
trap 'echo "第 $LINENO 行命令失败：$BASH_COMMAND"' ERR

# 模式 5：DEBUG 伪信号（每个命令执行前触发）
trap 'echo "DEBUG: 执行 $BASH_COMMAND"' DEBUG
```

### 7. 部署脚本中的信号处理

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
    echo "脚本异常退出（退出码: $exit_code）"

    if $DEPLOYED; then
        echo "执行回滚..."
        # 回滚逻辑
        rm -rf /opt/app/current
        ln -s /opt/app/backup /opt/app/current
        systemctl restart myapp
        echo "回滚完成"
    else
        echo "部署未完成，无需回滚"
    fi

    # 清理临时文件
    rm -rf "$TEMP_DIR"
    echo "临时文件已清理"

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

echo "部署成功"
```

---

## 🏗️ SRE 实战案例

### 案例 1：服务升级时的优雅关闭（Graceful Shutdown）

```bash
# 标准的优雅关闭流程：
# SIGTERM → 等待 → 检查 → SIGKILL

# 实现优雅关闭脚本
#!/bin/bash
graceful_stop() {
    local service_name=$1
    local pid=$(pgrep -x "$service_name")
    local timeout=${2:-30}  # 默认等待 30 秒

    if [ -z "$pid" ]; then
        echo "$service_name 未运行"
        return 0
    fi

    echo "发送 SIGTERM 给 $service_name (PID: $pid)"
    kill -TERM "$pid"

    # 等待进程退出
    local elapsed=0
    while kill -0 "$pid" 2>/dev/null; do
        if [ $elapsed -ge $timeout ]; then
            echo "等待超时（${timeout}s），发送 SIGKILL"
            kill -9 "$pid"
            sleep 1
            break
        fi
        sleep 1
        ((elapsed++))
    done

    if ! kill -0 "$pid" 2>/dev/null; then
        echo "$service_name 已停止"
    else
        echo "$service_name 停止失败！"
        return 1
    fi
}

# 使用
graceful_stop "nginx" 10
graceful_stop "java" 60   # Java 应用可能需要更长时间
```

### 案例 2：SIGHUP 重载配置 vs 重启服务

```bash
# Nginx 重载配置（零停机）
# 方法 1：systemctl（推荐）
sudo systemctl reload nginx

# 方法 2：发送 SIGHUP
sudo kill -HUP $(cat /var/run/nginx.pid)

# Nginx 收到 SIGHUP 后的行为：
# 1. 检查新配置是否有效
# 2. 无效则继续使用旧配置，记录错误日志
# 3. 有效则启动新的 worker 进程
# 4. 旧的 worker 处理完已有连接后优雅退出
# 5. 整个过程服务不中断

# 验证配置后再重载
sudo nginx -t && sudo nginx -s reload

# 对比：重启 vs 重载
# 重载（reload）：零停机，已有连接不受影响
# 重启（restart）：有短暂停机，所有连接断开
```

### 案例 3：kill -9 无法杀掉 D 状态进程

```bash
# 场景：进程处于 D 状态，kill -9 无效

# 原因：D 状态（TASK_UNINTERRUPTIBLE）的进程不响应任何信号
# 包括 SIGKILL（信号 9）

# 排查步骤：
# 1. 找出 D 状态进程
ps aux | awk '$8 ~ /^D/ {print $2, $8, $11, $12}'

# 2. 查看进程在等待什么内核函数
cat /proc/<PID>/wchan
# 例如：nfs_wait、blk_mq_get_tag、wait_on_page_bit

# 3. 查看内核栈（需要 root）
cat /proc/<PID>/stack

# 4. 检查磁盘
iostat -x 1 5
sudo smartctl -a /dev/sda
dmesg | tail -30

# 5. 检查 NFS（如果是 NFS 挂载）
mount | grep nfs
showmount -e <nfs-server>

# 6. 处理方案
# 如果是 NFS：umount -f -l /mount/point
# 如果是磁盘故障：更换磁盘
# 如果是内核 Bug：升级内核或重启系统
# D 状态进程只能等 I/O 完成或重启系统
```

### 案例 4：批量终止异常进程

```bash
# 场景：Bug 导致系统产生大量卡死的 python 进程

# 方法 1：pkill（最简单）
pkill -f "python worker.py"

# 方法 2：kill + pgrep（更灵活）
pgrep -f "python worker.py" | xargs kill -15

# 方法 3：两阶段终止（优雅 + 强制）
# 先 SIGTERM，等待 5 秒，还活着的用 SIGKILL
pgrep -f "python worker.py" | while read pid; do
    kill -15 "$pid"
done
sleep 5
pgrep -f "python worker.py" | while read pid; do
    echo "强制杀死 PID $pid"
    kill -9 "$pid"
done

# 方法 4：使用 timeout 命令
timeout 10 bash -c '
    kill $(pgrep -f "python worker.py") 2>/dev/null
    while pgrep -f "python worker.py" > /dev/null; do
        sleep 0.5
    done
'
# 如果 10 秒后还有进程存活，timeout 会终止等待循环
```

### 案例 5：日志轮转后让服务重新打开日志文件

```bash
# 场景：logrotate 轮转了日志文件，但服务还在写旧文件

# Nginx：发送 SIGUSR1
kill -USR1 $(cat /var/run/nginx.pid)
# Nginx 收到 SIGUSR1 后会重新打开日志文件

# Java 应用（如果实现了 SIGUSR1 处理）
kill -USR1 $(pgrep java | head -1)

# 通用方案：使用 copytruncate
# 在 logrotate 配置中使用 copytruncate 选项
# 这样 logrotate 会复制日志文件后清空，服务无需重新打开

# /etc/logrotate.d/myapp
# /var/log/myapp/*.log {
#     daily
#     rotate 7
#     compress
#     copytruncate    # 关键选项
#     missingok
#     notifempty
# }
```

---

## 💻 实战练习

### 练习 1：信号识别

以下场景分别应该发送什么信号？

1. 让 Nginx 重新加载配置而不中断现有连接
2. 强制杀死一个无响应的进程
3. 暂停一个正在运行的前台进程
4. 让进程在后台继续运行（从暂停状态恢复）
5. 优雅关闭一个数据库进程（让它先刷盘再退出）
6. 让 nginx 重新打开日志文件
7. 检查某个进程是否还活着

<details>
<summary>答案</summary>

1. `kill -HUP <PID>` 或 `systemctl reload nginx`
2. `kill -9 <PID>` 或 `kill -KILL <PID>`
3. `Ctrl+Z`（发送 SIGTSTP）或 `kill -STOP <PID>`
4. `bg`（发送 SIGCONT）或 `kill -CONT <PID>`
5. `kill -TERM <PID>`（让进程执行 cleanup 后自行退出）
6. `kill -USR1 <PID>`
7. `kill -0 <PID>`（不发送信号，只检查存在性）
</details>

### 练习 2：trap 脚本

编写一个脚本，创建一个临时文件，运行 `sleep 100`，如果脚本被中断（Ctrl+C 或 kill），删除临时文件后退出。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
TMPFILE=$(mktemp /tmp/myapp.XXXXXX)
echo "临时文件: $TMPFILE"

trap 'echo "收到中断信号，清理临时文件..."; rm -f "$TMPFILE"; exit 0' SIGINT SIGTERM EXIT

echo "运行中... (PID: $$)"
sleep 100
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

# 5. 查看进程的 OOM 评分
ps -eo pid,comm,%mem,oom_score --sort=-oom_score | head -10

# 6. 修复方案：
# - 增加 -Xmx 参数限制 Java 堆大小
# - 增加容器内存限制
# - 设置 OOMScoreAdjust 保护关键进程
# - 安装 earlyoom 提前干预
```
</details>

### 练习 4：编写一个优雅关闭的服务脚本

编写一个 shell 脚本，模拟一个长期运行的服务。要求：
- 收到 SIGTERM 后优雅关闭（输出关闭日志，等待 5 秒）
- 收到 SIGINT 后立即退出
- 退出时清理临时文件

<details>
<summary>答案</summary>

```bash
#!/bin/bash
PIDFILE=/tmp/myservice.pid
TMPDIR=$(mktemp -d)
echo $$ > "$PIDFILE"

cleanup() {
    echo "$(date): 开始清理..."
    sleep 5
    rm -f "$PIDFILE"
    rm -rf "$TMPDIR"
    echo "$(date): 清理完成"
    exit 0
}

trap cleanup SIGTERM
trap 'echo "收到 SIGINT，立即退出"; rm -f "$PIDFILE"; rm -rf "$TMPDIR"; exit 1' SIGINT

echo "服务启动 (PID: $$)"
while true; do
    echo "$(date): 服务运行中..."
    sleep 10
done
```
</details>

---

## 🎯 面试题精选

### 面试题 1：SIGTERM 和 SIGKILL 的区别是什么？

**参考答案：**

SIGTERM (15) 是"请求"进程自行终止的信号，进程可以捕获它并执行清理逻辑（保存数据、关闭连接、删除临时文件等）。它是 kill 命令的默认信号。

SIGKILL (9) 是内核强制终止进程的信号，进程无法捕获或忽略。内核直接回收进程资源，不给进程任何清理机会。可能导致数据丢失、连接泄漏、锁文件残留等问题。

最佳实践：先发 SIGTERM，等待一定时间（如 30 秒），如果进程仍未退出，再发 SIGKILL。这就是"两阶段终止"策略。

### 面试题 2：如何写一个守护进程？

**参考答案：**

标准的守护进程化步骤（daemonize）：
1. fork()，父进程退出，子进程继续（脱离原终端）
2. setsid()，创建新会话，成为会话首进程
3. 再次 fork()，防止会话首进程获取控制终端
4. 改变工作目录到 /
5. 关闭标准文件描述符（stdin/stdout/stderr），重定向到 /dev/null
6. 设置文件创建掩码 umask(0)

现代 Linux 推荐使用 systemd 管理服务（Day 10 详细讲解），不需要手动 daemonize。

### 面试题 3：信号是可靠的吗？

**参考答案：**

不可靠。标准信号（1-31）有两个可靠性问题：
1. 信号可能丢失：如果同一信号发送多次但进程还未处理，可能只收到一次
2. 顺序不保证：多个信号同时待处理时，处理顺序不确定

实时信号（SIGRTMIN ~ SIGRTMAX）是可靠的：
1. 支持排队：同一信号可以多次传递，不会丢失
2. 顺序有保证
3. 可以携带附加数据（通过 sigqueue() 系统调用）

### 面试题 4：nohup、disown 和 setsid 有什么区别？

**参考答案：**

nohup 在启动时就设置忽略 SIGHUP，并自动重定向输出到 nohup.out。进程仍在 shell 作业列表中。

disown 在进程已经启动后，从 shell 作业列表中移除。shell 退出时不会向该进程发送 SIGHUP。不会自动重定向输出。

setsid 创建全新的会话，进程成为新会话的 leader，完全脱离当前终端。即使终端关闭也不会收到 SIGHUP。

### 面试题 5：什么是进程组和会话？

**参考答案：**

进程组是一组相关进程的集合，通常是一个管道命令中的所有进程。进程组 ID（PGID）是领头进程的 PID。信号可以发送给整个进程组（kill -TERM -PGID）。

会话是一个或多个进程组的集合，通常对应一个终端登录会话。会话有一个控制终端和一个会话首进程（通常是 shell）。当会话首进程退出时，会向前台进程组发送 SIGHUP。

### 面试题 6：如何让一个进程忽略 SIGHUP？

**参考答案：**

三种方法：
1. nohup：`nohup ./script.sh &`，启动时就设置忽略 SIGHUP
2. disown：`./script.sh & disown`，从作业列表移除
3. trap：`trap '' SIGHUP`，在脚本中显式忽略
4. setsid：`setsid ./script.sh`，创建新会话

### 面试题 7：CFS 调度器是如何工作的？

**参考答案：**

CFS（Completely Fair Scheduler）使用红黑树组织所有可运行进程，以"虚拟运行时间"（vruntime）为键。每次调度时选择 vruntime 最小的进程（红黑树最左节点）。

nice 值通过权重映射表影响 CPU 时间分配。nice 0 的权重是 1024，nice 10 的权重是 110。两个进程的 CPU 时间比 = 权重比。

CFS 使用 sched_min_granularity_ns 控制最小调度粒度（通常 0.75-3ms），避免频繁上下文切换。

---

## 📚 深入阅读

- `man 7 signal` — Linux 信号的完整文档
- [Julia Evans — Linux Signals](https://jvns.ca/blog/2014/07/31/what-happens-when-you-ctrl-c/) — 通俗易懂的信号入门
- [The Linux Programming Interface — Chapter 20-22](https://www.nostarch.com/tlpi.htm) — 信号和进程管理章节
- [Systemd OOMScoreAdjust](https://www.freedesktop.org/software/systemd/man/systemd.exec.html#OOMScoreAdjust=) — systemd 的 OOM 保护
- [earlyoom](https://github.com/rfjakob/earlyoom) — 用户态 OOM 预防工具
- [Understanding the Linux Kernel — Chapter 3-4](https://www.oreilly.com/library/view/understanding-the-linux/0596005652/) — 进程调度和信号

---

## ✅ 自检清单

- [ ] 理解信号的完整生命周期（产生→传递→处理）
- [ ] 能区分 SIGTERM 和 SIGKILL 的使用场景
- [ ] 知道哪些信号可以被捕获，哪些不能
- [ ] 熟练使用 kill/killall/pkill 发送信号
- [ ] 理解 nice/renice 和 CFS 调度器的原理
- [ ] 掌握 nohup/disown/setsid 的区别和使用场景
- [ ] 能编写带 trap 的优雅关闭脚本
- [ ] 理解进程组和会话的概念
- [ ] 能排查 D 状态进程无法杀死的问题
- [ ] 能实现服务的优雅关闭流程
