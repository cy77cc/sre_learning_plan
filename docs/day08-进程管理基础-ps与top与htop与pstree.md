# Day 08: 进程管理基础 — ps/top/htop/pstree

> 📅 日期：2026-04-25
> 📖 学习主题：进程管理基础 — ps/top/htop/pstree
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 08 的学习后，你应该掌握：
- 理解 Linux 进程的本质：fork/exec 机制、进程描述符、进程状态机
- 熟练使用 ps 查看进程快照，理解 BSD 和 POSIX 格式的区别
- 使用 top/htop 实时监控进程资源占用，能定位高 CPU/高内存问题
- 使用 pstree 分析进程父子关系，理解 init/systemd 作为 PID 1 的角色
- 理解 `/proc` 文件系统的结构，能直接读取进程信息
- 掌握进程优先级（nice/renice）对调度的影响

---

## 📖 详细知识点

### 1. 进程的本质

#### 1.1 什么是进程

进程（Process）是**正在执行的程序实例**。当你在终端输入 `ls` 时，shell 通过以下步骤创建进程：

```
用户输入 "ls"
  → shell 调用 fork()      ← 复制当前进程，创建子进程
  → 子进程调用 execve()     ← 用 /bin/ls 替换子进程的内存空间
  → /bin/ls 执行
  → 子进程调用 exit()       ← 终止，向父进程返回退出码
  → shell 调用 wait()       ← 回收子进程资源
```

这就是经典的 **fork-exec 模型**。Linux 中每个进程都是通过 fork 从父进程"分裂"出来的。

#### 1.2 进程描述符（task_struct）

内核用 `task_struct` 结构体跟踪每个进程的所有信息：

```c
// 内核源码 include/linux/sched.h（简化版）
struct task_struct {
    pid_t pid;              // 进程 ID
    pid_t tgid;             // 线程组 ID（等于主线程的 PID）
    struct task_struct *parent;   // 父进程指针
    unsigned int state;     // 进程状态
    void *stack;            // 内核栈
    struct files_struct *files;   // 打开的文件描述符表
    struct mm_struct *mm;   // 内存描述符（虚拟地址空间）
    char comm[TASK_COMM_LEN];     // 进程名（16 字符）
    // ... 还有 100+ 字段
};
```

#### 1.3 进程 ID 分配

- **PID 范围**：1 ~ 4194304（默认，可通过 `/proc/sys/kernel/pid_max` 调整）
- **PID 0**：idle/swapper 进程，内核调度器的一部分，不算真正的进程
- **PID 1**：init/systemd，所有用户空间进程的祖先
- **PID 2**：kthreadd，内核线程的父进程
- **分配规则**：线性递增，到达上限后循环复用（跳过正在使用的 PID）

#### 1.4 进程类型

| 类型 | 创建方式 | 父进程 | 特点 |
|------|---------|--------|------|
| 用户进程 | fork + exec | 当前 shell | 有独立内存空间 |
| 内核线程 | kthread_create | kthreadd (PID 2) | 共享内核地址空间，名称用 `[]` 包裹 |
| 守护进程 | fork + setsid | 最终被 systemd 收养 | 脱离终端，后台运行 |

```bash
# 查看内核线程（名称带方括号）
ps aux | grep '\[.*\]' | head -5

# 输出示例：
# root         2  0.0  0.0      0     0 ?  S  00:00  0:00 [kthreadd]
# root         3  0.0  0.0      0     0 ?  I< 00:00  0:00 [rcu_gp]
# root        10  0.0  0.0      0     0 ?  I< 00:00  0:00 [mm_percpu_wq]
```

### 2. 进程状态机

Linux 进程的状态是一个精细的状态机，不是简单的"运行/停止"：

#### 2.1 核心状态

```
        ┌─────────┐
        │  创建    │ fork()
        └────┬────┘
             ▼
        ┌─────────┐
  ┌─────│ 就绪(R)  │
  │     └────┬────┘
  │          │ 获得 CPU
  │          ▼
  │     ┌─────────┐
  │     │ 运行(R)  │
  │     └────┬────┘
  │          │ 时间片用完 / 主动让出
  │          ▼
  │     ┌─────────┐
  │─────│ 睡眠(S)  │ 等待 I/O 或事件
  │     └────┬────┘
  │          │ 事件到达
  │          ▼
  │     ┌─────────┐
  │     │  就绪(R) │
  │     └─────────┘
  │
  │     ┌─────────┐
  │     │ D (不可中断睡眠) │
  │     │ 等待磁盘 I/O，不能被 kill │
  │     └─────────┘
  │
  │     ┌─────────┐
  │     │ T (停止) │ ← SIGSTOP 或调试器断点
  │     └─────────┘
  │
  │     ┌─────────┐
  │     │ Z (僵尸) │ ← 已退出，父进程未 wait()
  │     └─────────┘
```

#### 2.2 ps 中的状态代码详解

`ps aux` 的 STAT 列包含状态字符和修饰符：

| 字符 | 含义 | 示例 |
|------|------|------|
| **主状态** | | |
| R | Running / Runnable | `R+` 表示前台运行中 |
| S | Interruptible Sleep（可中断睡眠）| `Ss` systemd 的常态 |
| D | Uninterruptible Sleep（不可中断睡眠）| `Dl` 等待 NFS 响应 |
| Z | Zombie（僵尸） | `Z` 父进程未回收 |
| T | Stopped（停止） | `T` 被 SIGSTOP 暂停 |
| X | Dead（死亡） | 极短暂，几乎看不到 |
| **修饰符** | | |
| s | session leader（会话首进程） | `Ss` 说明是会话首进程 |
| l | multi-threaded（多线程） | `Sl` 说明有子线程 |
| + | foreground process group（前台进程组）| `R+` 正在前台运行 |
| < | high priority（高优先级） | `S<` nice 值为负 |
| N | low priority（低优先级） | `SN` nice 值为正 |
| L | has pages locked in memory（内存锁定）| `SL` 实时系统常用 |

```bash
# 解读示例
# Ss  → 可中断睡眠 + 会话首进程（通常是服务进程）
# Sl  → 可中断睡眠 + 多线程
# S<s → 高优先级 + 可中断睡眠 + 会话首进程
# R+  → 正在运行 + 在前台
# D   → 不可中断睡眠（可能在等待磁盘 I/O 或 NFS，此时 kill 无效）
```

#### 2.3 D 状态（不可中断睡眠）排障

```bash
# 找到所有 D 状态的进程
ps aux | awk '$8 ~ /^D/ {print $0}'

# D 状态通常是 I/O 问题，检查磁盘
dmesg | tail -20
iostat -x 1 5

# 常见原因：
# 1. NFS 服务器无响应
# 2. 磁盘故障（bad sector）
# 3. 设备驱动 Bug
# 4. 存储控制器异常

# 解决方案：
# 如果 NFS 卡住：umount -f -l /mount/point
# 如果磁盘故障：更换磁盘
# D 状态进程不能用 kill 终止（因为不响应信号）
```

#### 2.4 僵尸进程

```bash
# 什么是僵尸进程？
# 进程已调用 exit() 终止，但父进程未调用 wait() 回收资源
# 僵尸进程不消耗 CPU/内存，但占用 PID 表项

# 查找僵尸进程
ps aux | awk '$8 ~ /^Z/ {print $0}'

# 找到僵尸进程的父进程
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /^Z/ {print "僵尸 PID:", $1, "父进程 PPID:", $2}'

# 修复方法 1：通知父进程回收
kill -SIGCHLD <父进程PID>

# 修复方法 2：如果父进程不配合，杀死父进程
# 父进程死亡后，僵尸进程会被 init(PID 1) 收养并自动回收
kill <父进程PID>

# 实战示例：大量僵尸进程
# 假设某个 Bug 导致每分钟产生 100 个僵尸
# 不处理会导致 PID 耗尽，无法创建新进程
echo 4194304 > /proc/sys/kernel/pid_max  # 临时增大上限
```

### 3. ps 命令深度解析

#### 3.1 两种语法风格

ps 支持两种不兼容的语法，这也是初学者最容易混淆的地方：

| 风格 | 选项格式 | 示例 | 说明 |
|------|---------|------|------|
| BSD | 不带 `-` | `ps aux` | 源自 Berkeley Software Distribution |
| POSIX | 带 `-` | `ps -ef` | 来自 POSIX 标准 |

**可以混用但推荐选择一种风格保持一致。**

#### 3.2 ps aux 输出详解

```bash
ps aux
# USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
# root         1  0.0  0.1 169396 11940 ?        Ss   Apr25   0:05 /sbin/init
# root       512  0.0  0.0  18184  6272 ?        Ss   Apr25   0:00 /usr/sbin/sshd
# sreuser   1234  0.5  2.1 456780 85432 pts/0    Sl+  10:00   0:30 java -jar app.jar
```

| 列名 | 含义 | 说明 |
|------|------|------|
| USER | 启动用户 | — |
| PID | 进程 ID | — |
| %CPU | CPU 使用率 | 采样周期内的平均值 |
| %MEM | 内存占比 | RSS / 总物理内存 |
| **VSZ** | 虚拟内存大小（KB）| 进程申请的总地址空间（含未分配的） |
| **RSS** | 常驻内存大小（KB） | 实际使用的物理内存 |
| TTY | 关联的终端 | `?` 表示无终端（守护进程） |
| STAT | 状态 | 见上文状态码表 |
| START | 启动时间 | — |
| TIME | CPU 累计使用 | 进程从启动到现在的 CPU 时间（不含睡眠时间） |
| COMMAND | 命令行 | `[]` 包裹的是内核线程 |

**VSZ vs RSS 的区别：**
```
VSZ（虚拟内存） = 代码段 + 数据段 + 堆 + 栈 + 共享库映射 + 内存映射文件
RSS（物理内存） = 实际加载到 RAM 中的页面

类比：
VSZ 是你银行卡的信用额度（可以申请但未必使用）
RSS 是你实际从 ATM 取出的现金（真正占用的物理资源）
```

#### 3.3 自定义输出格式

```bash
# 显示 PID、PPID、状态、命令（自定义列）
ps -eo pid,ppid,stat,comm --sort=-%cpu | head -10

# 显示进程的用户、PID、CPU、内存、启动时间、命令
ps -eo user,pid,%cpu,%mem,start,time,comm --sort=-%cpu | head -15

# 按内存使用排序
ps aux --sort=-%mem | head -10

# 按运行时间排序
ps -eo pid,etime,comm --sort=-etime | head -10

# etime 格式说明：[[DD-]hh:]mm:ss
# 00:30    = 30 秒
# 12:30:45 = 12 小时 30 分 45 秒
# 02-12:30 = 2 天 12 小时 30 分

# 筛选特定用户的所有进程
ps -u www-data -o pid,%cpu,%mem,rss,comm

# 查看进程的完整命令行（默认可能被截断）
ps auxww              # ww 表示不截断
ps -eo pid,args       # args = 完整命令行

# 查找某个程序的所有实例
ps aux | grep -E '[n]ginx'    # 用正则排除 grep 自身
pgrep -la nginx               # 更简洁的方式
```

#### 3.4 ps + awk 实用组合

```bash
# 找出 CPU 使用超过 50% 的进程
ps aux | awk 'NR>1 && $3 > 50 {print $1, $2, $3"%", $11}'

# 统计每个用户的进程数
ps aux | awk 'NR>1 {count[$1]++} END {for(u in count) print count[u], u}' | sort -rn

# 统计各状态的进程数
ps aux | awk 'NR>1 {split($8,a,""); count[a[1]]++} END {for(s in count) print count[s], s}'

# 输出示例：
# 45 S
# 3 R
# 1 Z
# 1 D

# 查找运行超过 24 小时的进程
ps -eo pid,etime,comm | awk 'NR>1 && $2 ~ /-/ {print}'

# 查找没有终端的守护进程
ps -eo pid,tty,comm | awk '$2 == "?" && $3 != "" {print}'
```

### 4. top 命令详解

#### 4.1 top 输出解读

```
top - 14:30:25 up 5 days,  3:22,  2 users,  load average: 0.52, 0.38, 0.29
Tasks: 186 total,   1 running, 185 sleeping,   0 stopped,   0 zombie
%Cpu(s): 12.3 us,  3.2 sy,  0.0 ni, 83.5 id,  0.8 wa,  0.0 hi,  0.2 si,  0.0 st
MiB Mem :  16043.2 total,   2156.8 free,   8432.1 used,   5454.3 buff/cache
MiB Swap:   2048.0 total,   2048.0 free,      0.0 used.   7611.1 avail Mem

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 1234 sreuser   20   0  456780  85432  12345 S   8.3   0.5   1:23.45 java
  567 root      20   0  234560  45678   8901 S   2.1   0.3   0:45.67 nginx
    1 root      20   0  169396  11940   8765 S   0.0   0.1   0:05.12 systemd
```

| 区域 | 字段 | 含义 |
|------|------|------|
| **第一行** | up 5 days | 系统运行时间 |
| | load average: 0.52, 0.38, 0.29 | 1/5/15 分钟平均负载 |
| **第二行** | Tasks | 进程总数及各状态数量 |
| **第三行** | us | 用户空间 CPU 时间 |
| | sy | 内核空间 CPU 时间 |
| | ni | nice 调整的时间 |
| | id | 空闲时间 |
| | wa | I/O 等待时间（关键指标！） |
| | hi/si | 硬中断/软中断 |
| | st | 被虚拟机偷走的时间（steal time） |
| **第四行** | Mem | 内存使用概况 |
| | buff/cache | 可回收的缓存（不算真正占用） |
| **第五行** | Swap | 交换空间使用 |

**Load Average 的含义：**
```
load average = 处于运行态(R) + 不可中断睡眠态(D) 的进程数（在采样周期内的平均）

对于单核 CPU：
  0.5 = CPU 一半时间空闲
  1.0 = CPU 刚好满载
  2.0 = CPU 过载，有进程在排队

对于 4 核 CPU：
  4.0 = 刚好满载
  > 4.0 = 有过载风险

关键：load average 包含 D 状态的进程，所以 I/O 瓶颈也会导致负载升高！
这就是为什么磁盘故障时，即使 CPU 空闲，load average 也可能很高。
```

#### 4.2 top 交互命令

进入 top 后按以下快捷键：

| 按键 | 功能 |
|------|------|
| `P` | 按 CPU 排序（默认） |
| `M` | 按内存排序 |
| `N` | 按 PID 排序 |
| `T` | 按累计 CPU 时间排序 |
| `c` | 切换显示完整命令 |
| `1` | 展开/折叠所有 CPU 核心 |
| `k` | 杀死进程（输入 PID 和信号） |
| `r` | 重新设置 nice 值 |
| `f` | 自定义显示的列 |
| `o` | 设置过滤条件（如 `CPU>5.0`） |
| `W` | 保存当前配置到 `~/.toprc` |
| `q` | 退出 |

#### 4.3 top 批处理模式（脚本中使用）

```bash
# 运行一次就退出（适合脚本）
top -b -n 1

# 每 2 秒采样一次，共 3 次，输出到文件
top -b -d 2 -n 3 > /tmp/top_output.txt

# 只监控特定进程
top -b -n 1 -p $(pgrep -d',' nginx)

# 抓取 CPU 排名前 10 的进程
top -b -n 1 | head -17 | tail -10

# 持续监控（每 5 秒），匹配特定关键字
top -b -d 5 | grep --line-buffered "java"
```

### 5. htop — 增强版 top

```bash
# 安装
sudo apt install htop       # Debian/Ubuntu
sudo yum install htop       # RHEL/CentOS

# 启动
htop
```

**htop 的优势：**
```
✅ 彩色显示，可读性更好
✅ 支持鼠标点击操作
✅ 树形视图（F5 切换）
✅ 支持进程多选（空格键）
✅ 内置搜索（F3）
✅ 不需要输入 PID，直接选择操作
✅ 显示完整的 CPU/内存/swap 使用条
✅ 支持过滤器（F4）
```

**htop 配置（`~/.config/htop/htoprc`）：**
```ini
# 显示列（可自定义顺序）
fields=0 48 17 18 38 39 40 2 46 47 49 1

# 高亮行
highlight_base_on=0

# 颜色方案
color_scheme=6

# 默认按 CPU 排序，降序
sort_key=PERCENT_CPU
sort_direction=-1
```

### 6. pstree — 进程树

```bash
# 显示完整进程树
pstree

# 显示 PID（非常有用）
pstree -p

# 显示进程命令行参数
pstree -a

# 显示 PID + 参数
pstree -ap

# 显示某个进程的子树
pstree -ap $(pgrep nginx | head -1)

# 输出示例：
# systemd,1
#   ├─sshd,512
#   │   └─sshd,1234
#   │       └─bash,1235
#   │           └─java,1236 -jar /opt/app.jar
#   ├─nginx,567
#   │   ├─nginx,568
#   │   └─nginx,569
#   └─dockerd,890
#       └─containerd,891
```

### 7. /proc 文件系统

`/proc` 是内核向用户空间暴露信息的虚拟文件系统，每个进程有独立目录：

```bash
# 查看进程的详细信息
cat /proc/1/status       # 状态信息
cat /proc/1/cmdline      # 命令行参数（\0 分隔）
cat /proc/1/environ      # 环境变量（\0 分隔，可能包含敏感信息）
cat /proc/1/limits       # 资源限制
cat /proc/1/fd/          # 打开的文件描述符（符号链接）
cat /proc/1/maps         # 内存映射
cat /proc/1/stat         # 数字格式的状态（脚本解析用）
cat /proc/1/io           # I/O 统计

# 实用示例
# 查看进程的工作目录（符号链接）
ls -l /proc/1234/cwd

# 查看进程的可执行文件路径
ls -l /proc/1234/exe

# 查看进程打开的所有文件
ls -l /proc/1234/fd/

# 统计每个进程打开的文件数
for pid in /proc/[0-9]*/fd; do
    count=$(ls "$pid" 2>/dev/null | wc -l)
    ppid=$(basename $(dirname $pid))
    echo "$count $ppid $(cat /proc/$ppid/comm 2>/dev/null)"
done | sort -rn | head -10

# 全局文件描述符统计
cat /proc/sys/fs/file-nr
# 输出：已分配  未使用  最大值
# 例如：4096    0       9223372036854775807
```

---

## 🏗️ 实战场景

### 场景 1：服务器响应缓慢排查

```bash
# 收到告警：服务器响应慢，按以下顺序排查

# 第一步：看整体负载
uptime
# 如果 load average > CPU 核心数 → 有过载

# 第二步：看 top 摘要
top -b -n 1 | head -5

# 关键判断：
# - us 高（> 70%）→ 用户程序占用 CPU，查 top 进程列表
# - wa 高（> 20%）→ I/O 瓶颈，查 iostat
# - si 高 → 大量软中断，可能网络包处理问题

# 第三步：找出具体的问题进程
ps aux --sort=-%cpu | head -10
# 或者
top -b -n 1 | awk 'NR>7 {print $1, $9, $12}' | head -20

# 第四步：分析进程在做什么
# 查看进程打开的文件（可能在大量写日志？）
ls -l /proc/<PID>/fd/ | wc -l

# 查看进程的网络连接
sudo ss -tnp | grep <PID>

# 查看进程的 I/O
sudo cat /proc/<PID>/io

# 第五步：如果是 Java 进程，dump 线程
kill -3 <PID>    # 线程 dump 到日志（不是杀死！）
```

### 场景 2：监控进程资源变化

```bash
# 持续监控某个进程的 CPU 和内存变化，每 2 秒记录一次
while true; do
    date '+%Y-%m-%d %H:%M:%S'
    ps -p $(pgrep app | head -1) -o pid,%cpu,%mem,rss,vsz --no-headers
    sleep 2
done

# 输出到文件以便后续分析
while true; do
    echo "$(date '+%H:%M:%S'),$(ps -p $(pgrep app | head -1) \
        -o %cpu,%mem,rss --no-headers | tr -s ' ' ',')" >> /tmp/proc_monitor.csv
    sleep 5
done &

# 使用 gnuplot 绘制趋势图（需要安装 gnuplot）
gnuplot -e "set datafile separator ','; set xdata time; set timefmt '%H:%M:%S'; \
    plot '/tmp/proc_monitor.csv' using 1:3 with lines title 'RSS'"
```

### 场景 3：僵尸进程排查

```bash
# 发现系统有僵尸进程
ps aux | awk '$8 ~ /^Z/'

# 统计僵尸进程数量
ps aux | awk '$8 ~ /^Z/ {count++} END {print "僵尸进程:", count+0}'

# 找到产生僵尸的父进程
ps -eo pid,ppid,stat,comm | awk '$3 ~ /^Z/ {ppid[$2]++} END {for(p in ppid) print "PPID:", p, "产生", ppid[p], "个僵尸"}'

# 查看父进程的详细信息
ps -p <PPID> -o pid,ppid,comm,%cpu,%mem,rss

# 查看父进程的代码（如果有的话）
ls -l /proc/<PPID>/exe

# 修复方案：
# 方案 1：发送 SIGCHLD 让父进程回收
kill -SIGCHLD <PPID>

# 方案 2：如果是 Bug 进程，重启服务
sudo systemctl restart <service-name>

# 方案 3：终极方案 — 杀掉父进程（让 init 收养僵尸）
# ⚠️ 谨慎操作，可能导致服务中断
kill <PPID>
```

---

## 🧪 练习题

### 练习 1：解读 ps 输出

解释以下 `ps aux` 输出行的每个字段：
```
sreuser  2345  12.5  3.2  1234567  512345  pts/1  Sl+  10:00  0:45  node server.js
```

<details>
<summary>答案</summary>

| 字段 | 值 | 含义 |
|------|------|------|
| USER | sreuser | 启动用户 |
| PID | 2345 | 进程 ID |
| %CPU | 12.5 | CPU 使用率 12.5% |
| %MEM | 3.2 | 内存占比 3.2% |
| VSZ | 1234567 | 虚拟内存 ~1.2 GB |
| RSS | 512345 | 物理内存 ~500 MB |
| TTY | pts/1 | 运行在伪终端 1 |
| STAT | Sl+ | 多线程 + 可中断睡眠 + 前台进程组 |
| START | 10:00 | 10 点启动 |
| TIME | 0:45 | 累计使用 45 秒 CPU |
| COMMAND | node server.js | 启动命令 |
</details>

### 练习 2：进程状态分析

某服务器 top 显示 `load average: 8.5, 6.2, 4.1`，`%Cpu(s)` 显示 `wa: 35.2`。请分析可能的问题。

<details>
<summary>答案</summary>

**分析**：
- load average 持续升高（4.1 → 6.2 → 8.5），说明问题在恶化
- `wa: 35.2%` 表示 35% 的 CPU 时间在等待 I/O 完成
- **结论**：这是 I/O 瓶颈，不是 CPU 瓶颈

**排查步骤**：
```bash
# 确认 I/O 问题
iostat -x 1 5
# 查看 %util 接近 100% 的磁盘

# 找出大量读写的进程
iotop -o

# 检查磁盘健康状态
sudo smartctl -a /dev/sda
```
</details>

### 练习 3：编写进程监控脚本

编写一个脚本，每 10 秒检查一次，当有任何进程的 CPU 使用率超过 80% 时，输出该进程的 PID、名称和 CPU 使用率，并记录到日志文件。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
LOG="/var/log/high_cpu.log"

while true; do
    ps aux | awk 'NR>1 && $3 > 80 {
        printf "%s PID=%s CPU=%s%% CMD=%s\n", strftime("%Y-%m-%d %H:%M:%S"), $2, $3, $11
    }' >> "$LOG"
    sleep 10
done
```
</details>

---

## 📚 扩展阅读

- [Brendan Gregg — Linux Performance](http://www.brendangregg.com/linuxperf.html) — Linux 性能分析权威指南
- `/proc` 文件系统文档：`man 5 proc`
- [The Linux Programming Interface](https://www.nostarch.com/tlpi.htm) — Michael Kerrisk，进程章节极为详细
- [strace 教程](https://jvns.ca/blog/2014/10/05/why-debugging-is-fun/) — Julia Evans 的调试博客
