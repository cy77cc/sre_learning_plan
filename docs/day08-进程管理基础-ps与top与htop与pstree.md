# Day 08: 进程管理基础 — ps/top/htop/pstree

> 📅 日期：2026-05-02
> 📖 学习主题：进程管理基础 — ps/top/htop/pstree
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 01-07（Linux 基础、文件系统、用户管理）

## 🎯 学习目标

完成 Day 08 的学习后，你应该能够：
- 深入理解 Linux 进程模型：task_struct、fork/exec、写时复制（COW）
- 熟练解读进程状态机（R/S/D/Z/T）及 ps 中的状态修饰符
- 精通 ps 命令的 BSD 和 POSIX 两种语法风格，自定义输出格式
- 使用 top/htop 实时监控系统，准确解读 load average、CPU、内存指标
- 通过 /proc/[PID]/ 目录直接读取进程的底层信息
- 独立完成 OOM Kill 排查、CPU 100% 排查、文件描述符耗尽排查

---

## 📖 核心知识点

### 1. Linux 进程模型深入

#### 1.1 什么是进程

进程（Process）是**正在执行的程序实例**。Linux 中每个进程都是通过 fork 从父进程"分裂"出来的。当你在终端输入 `ls` 时，shell 通过以下步骤创建进程：

```
用户输入 "ls"
  → shell 调用 fork()      ← 复制当前进程，创建子进程（写时复制）
  → 子进程调用 execve()     ← 用 /bin/ls 替换子进程的内存空间
  → /bin/ls 执行，输出结果
  → 子进程调用 exit()       ← 终止，向父进程发送 SIGCHLD
  → shell 调用 wait()/waitpid() ← 回收子进程资源，读取退出码
```

这就是经典的 **fork-exec 模型**，是 Unix/Linux 进程创建的基石。

#### 1.2 进程描述符（task_struct）

内核用 `task_struct` 结构体跟踪每个进程的所有信息。这是 Linux 内核中最重要的数据结构之一：

```c
// 内核源码 include/linux/sched.h（简化版）
struct task_struct {
    // === 标识信息 ===
    pid_t pid;              // 进程 ID（线程唯一的标识符）
    pid_t tgid;             // 线程组 ID（等于主线程的 PID）
    struct task_struct *parent;   // 父进程指针
    struct list_head children;    // 子进程链表
    struct list_head sibling;     // 兄弟进程链表

    // === 调度信息 ===
    unsigned int state;     // 进程状态（R/S/D/Z/T 等）
    int prio;               // 动态优先级
    int static_prio;        // 静态优先级（nice 值计算得来）
    unsigned int policy;    // 调度策略（SCHED_NORMAL/SCHED_FIFO/SCHED_RR）
    unsigned int rt_priority; // 实时优先级

    // === 内存信息 ===
    struct mm_struct *mm;   // 内存描述符（虚拟地址空间）
    struct mm_struct *active_mm; // 当前活跃的内存描述符

    // === 文件信息 ===
    struct files_struct *files;   // 打开的文件描述符表
    struct fs_struct *fs;   // 文件系统信息（当前目录、根目录）

    // === 信号信息 ===
    struct signal_struct *signal; // 信号处理结构
    struct sighand_struct *sighand; // 信号处理函数表
    sigset_t blocked;       // 被阻塞的信号掩码

    // === 其他 ===
    void *stack;            // 内核栈指针
    char comm[TASK_COMM_LEN];     // 进程名（最多 16 字符）
    struct task_struct *group_leader; // 线程组领头线程
    // ... 还有 100+ 字段
};
```

```
task_struct 在内核中的组织方式：

     ┌─────────────┐
     │  PID 1       │ (systemd/init)
     │  task_struct  │
     └──────┬───────┘
            │ children 链表
     ┌──────┴───────┐
     │              │
  ┌──▼──┐      ┌───▼──┐
  │PID 2│      │PID 512│ (sshd)
  │kthreadd│   │task_struct│
  └──────┘     └───┬───┘
                   │ children
              ┌────┴────┐
              │         │
           ┌──▼──┐  ┌──▼──┐
           │PID   │  │PID   │
           │1234  │  │1235  │
           │sshd  │  │bash  │
           └──────┘  └──────┘
```

每个 task_struct 约占用 6-10 KB 内存（取决于内核版本和配置）。在 `/proc/sys/kernel/pid_max` 中可以查看最大 PID 值，默认 32768（64 位系统可调到 4194304）。

#### 1.3 进程创建原理：fork + exec + COW

**fork() 系统调用：**

fork 的核心特点是"调用一次，返回两次"：
- 父进程：返回子进程的 PID
- 子进程：返回 0

```
fork() 的内部实现（简化）：

1. 分配新的 task_struct
2. 复制父进程的 mm_struct（内存描述符）
3. 将父子进程的页表都标记为"只读"（COW 标记）
4. 复制父进程的 files_struct（文件描述符表）的引用计数 +1
5. 复制父进程的 fs_struct
6. 设置子进程的 pid、ppid
7. 将子进程加入调度队列
8. 返回：父进程返回子 pid，子进程返回 0
```

**写时复制（Copy-On-Write, COW）：**

fork 不会立即复制父进程的物理内存页，而是让父子进程共享同一份物理内存，只在某一方尝试写入时才复制：

```
fork 后的状态：
  父进程页表 ──→ [物理页 A] ←── 子进程页表
                 (标记为只读/COW)

子进程调用 execve() 后：
  父进程页表 ──→ [物理页 A]     （父进程独占）
  子进程页表 ──→ [物理页 B]     （execve 加载新程序，全新内存）

如果子进程先写入（不 exec）：
  父进程页表 ──→ [物理页 A]     （父进程独占）
  子进程页表 ──→ [物理页 A']    （COW 复制的新副本）
```

COW 的好处：
- fork 后立即 exec 的场景（最常见），不需要复制无用的内存
- 节省内存：父子进程共享只读的代码段和共享库
- 减少 fork 延迟：从 O(内存大小) 降到 O(页表大小)

**execve() 系统调用：**

```bash
# execve 做了什么：
# 1. 验证文件权限和格式（ELF magic number）
# 2. 释放旧的内存映射（mm_struct）
# 3. 创建新的 mm_struct
# 4. 加载 ELF 程序段到内存（代码段、数据段）
# 5. 设置新的用户栈
# 6. 设置入口点（ELF header 中的 e_entry）
# 7. 信号处理函数重置为默认（除非设置了 SA_RESTART）
# 8. 如果设置了 setuid/setgid，切换有效 UID/GID
```

#### 1.4 进程 ID 分配

| PID | 归属 | 说明 |
|-----|------|------|
| 0 | idle/swapper | 内核调度器的一部分，不算真正的进程 |
| 1 | init/systemd | 所有用户空间进程的祖先，第一个用户态进程 |
| 2 | kthreadd | 内核线程的父进程，负责创建内核线程 |

```bash
# 查看 PID 范围
cat /proc/sys/kernel/pid_max
# 默认：32768（32 位）或 4194304（64 位）

# 查看已使用的 PID 数量
ls /proc/ | grep -c '^[0-9]'

# PID 分配规则：线性递增，到达上限后循环复用
# 跳过正在使用的 PID
```

#### 1.5 进程类型

| 类型 | 创建方式 | 父进程 | 特点 | 示例 |
|------|---------|--------|------|------|
| 用户进程 | fork + exec | shell 或其他进程 | 有独立内存空间 | nginx, java, python |
| 内核线程 | kthread_create | kthreadd (PID 2) | 共享内核地址空间，名称用 `[]` 包裹 | kworker, ksoftirqd |
| 守护进程 | fork + setsid | 被 systemd 收养 | 脱离终端，后台运行 | sshd, crond, dockerd |

```bash
# 查看内核线程（名称带方括号）
ps -eo pid,ppid,comm | grep '\[.*\]' | head -10

# 输出示例：
# PID  PPID  COMMAND
#    2     0  [kthreadd]
#    3     2  [rcu_gp]
#   10     2  [mm_percpu_wq]
#   11     2  [ksoftirqd/0]

# 查看守护进程（无终端关联）
ps -eo pid,tty,comm | awk '$2 == "?"' | head -10
```

### 2. 进程状态机详解

Linux 进程的状态是一个精细的状态机，不是简单的"运行/停止"：

#### 2.1 核心状态

```
                    fork()
        ┌──────────────────────┐
        │                      │
        ▼                      │
   ┌─────────┐                 │
   │ 创建态   │                 │
   └────┬────┘                 │
        │ 内核初始化完成         │
        ▼                      │
   ┌─────────┐    调度器选中    │
   │ 就绪(R)  │◄───────────────┘
   └────┬────┘
        │ 获得 CPU 时间片
        ▼
   ┌─────────┐
   │ 运行(R)  │──────────────────────────┐
   └────┬────┘                           │
        │                                │
        │ 等待事件（I/O、信号、锁）       │ 时间片用完
        ▼                                │
   ┌─────────┐                           │
   │ 睡眠(S)  │                           │
   └────┬────┘                           │
        │ 事件到达/信号唤醒               │
        ▼                                │
   ┌─────────┐◄─────────────────────────┘
   │ 就绪(R)  │
   └─────────┘

   ┌─────────┐
   │ D (不可中断睡眠) │  等待磁盘 I/O / NFS / 内核锁
   │ kill 无效！      │  只能等 I/O 完成或重启
   └─────────┘

   ┌─────────┐
   │ T (停止) │  SIGSTOP / 调试器断点 / Ctrl+Z
   └─────────┘

   ┌─────────┐
   │ Z (僵尸) │  已 exit()，父进程未 wait() 回收
   │ 不消耗资源│  但占用 PID 表项
   └─────────┘
```

#### 2.2 ps 中的状态代码详解

`ps aux` 的 STAT 列包含状态字符和修饰符：

**主状态字符：**

| 字符 | 内核状态 | 含义 | 典型场景 |
|------|---------|------|---------|
| **R** | TASK_RUNNING | 正在运行或在运行队列中等待 | CPU 密集型任务 |
| **S** | TASK_INTERRUPTIBLE | 可中断睡眠（等待事件） | 等待网络请求、用户输入、定时器 |
| **D** | TASK_UNINTERRUPTIBLE | 不可中断睡眠（等待 I/O） | 磁盘 I/O、NFS、内核锁 |
| **Z** | EXIT_ZOMBIE | 僵尸进程（已退出，未被回收） | 父进程未调用 wait() |
| **T** | TASK_STOPPED / TASK_TRACED | 被信号停止或被调试器跟踪 | SIGSTOP、gdb 调试 |
| **X** | EXIT_DEAD | 死亡态 | 极短暂，ps 几乎看不到 |
| **I** | TASK_IDLE | 空闲内核线程 | 内核 4.x+ 新增 |

**状态修饰符（跟在主状态字符后面）：**

| 修饰符 | 含义 | 示例 | 解读 |
|--------|------|------|------|
| **s** | session leader（会话首进程） | `Ss` | 通常是 shell 或服务主进程 |
| **l** | multi-threaded（多线程） | `Sl` | 使用了 pthread 或 clone(CLONE_THREAD) |
| **+** | foreground process group（前台进程组） | `R+` | 正在前台终端运行 |
| **<** | high-priority（高优先级） | `S<` | nice 值为负（优先级高于普通） |
| **N** | low-priority（低优先级） | `SN` | nice 值为正（优先级低于普通） |
| **L** | pages locked in memory（内存锁定） | `SL` | mlock() 锁定了内存页，不会被 swap |
| **E** | exiting（正在退出） | `RE` | 进程正在被杀死的过程中 |
| **k** | wakekill（存在唤醒杀死标志） | `Dk` | 内核 5.x+ 新增 |

```bash
# 解读示例
# Ss   → 可中断睡眠 + 会话首进程（nginx 的 master 进程）
# Sl   → 可中断睡眠 + 多线程（Java 应用的典型状态）
# S<s  → 高优先级 + 可中断睡眠 + 会话首进程
# R+   → 正在运行 + 在前台（当前正在执行的命令）
# D    → 不可中断睡眠（等待磁盘 I/O，kill 无效）
# Z    → 僵尸进程（父进程未回收）

# 找出所有 D 状态进程
ps aux | awk '$8 ~ /^D/'

# 找出所有 Z 状态进程
ps aux | awk '$8 ~ /^Z/'
```

#### 2.3 D 状态（不可中断睡眠）深入

D 状态是 SRE 排障中最棘手的状态之一：

```bash
# D 状态进程的特点：
# 1. 不响应任何信号（包括 SIGKILL）
# 2. 通常在等待硬件 I/O 完成
# 3. 如果 I/O 永远不完成，进程将永远卡住

# 常见原因：
# - NFS 服务器无响应（最常见的 D 状态原因）
# - 磁盘硬件故障（坏道、控制器故障）
# - 内核驱动 Bug
# - 存储阵列故障
# - USB 设备无响应

# 排查方法：
# 1. 找到 D 状态进程
ps aux | awk '$8 ~ /^D/ {print $2, $8, $11, $12}'

# 2. 查看进程在等待什么
cat /proc/<PID>/wchan   # 等待的内核函数名
cat /proc/<PID>/stack   # 内核栈（需要 root）

# 3. 查看系统日志
dmesg | tail -30
sudo journalctl -k --since "5 minutes ago"

# 4. 检查磁盘健康
sudo smartctl -a /dev/sda
iostat -x 1 5

# 5. 如果是 NFS 问题
mount | grep nfs
# 强制卸载卡住的 NFS
sudo umount -f -l /mount/point

# 6. D 状态进程不能用 kill 终止
# 只能等 I/O 完成，或者重启系统
```

#### 2.4 僵尸进程和孤儿进程

**僵尸进程（Zombie Process）：**

```bash
# 产生原因：
# 1. 子进程调用 exit() 终止
# 2. 内核保留子进程的退出状态（exit code + 资源使用统计）
# 3. 父进程未调用 wait()/waitpid() 回收
# 4. 子进程变成 Z 状态，保留在进程表中

# 僵尸进程不消耗 CPU 和内存，但占用 PID 表项
# 大量僵尸进程会导致 PID 耗尽，无法创建新进程

# 查找僵尸进程
ps aux | awk '$8 ~ /^Z/'

# 找到僵尸进程的父进程
ps -eo pid,ppid,stat,comm | awk '$3 ~ /^Z/ {
    print "僵尸 PID:", $1, "父进程 PPID:", $2, "命令:", $4
}'

# 统计每个父进程产生的僵尸数量
ps -eo ppid,stat | awk '$2 ~ /^Z/ {count[$1]++} END {
    for(ppid in count) print "PPID", ppid, "产生", count[ppid], "个僵尸"
}'
```

**僵尸进程的处理方法：**

```bash
# 方法 1：发送 SIGCHLD 让父进程回收
kill -SIGCHLD <父进程PID>
# 只有父进程正确实现了 SIGCHLD 处理才有效

# 方法 2：杀死父进程
# 父进程死亡后，僵尸进程被 init/systemd (PID 1) 收养
# init 会自动调用 wait() 回收所有收养的僵尸
kill <父进程PID>

# 方法 3：如果父进程是 systemd 管理的服务
sudo systemctl restart <service-name>

# 方法 4：批量清理僵尸（终极方案）
# 找到产生僵尸的父进程并重启
for ppid in $(ps -eo ppid,stat | awk '$2=="Z" {print $1}' | sort -u); do
    echo "父进程 $ppid 产生僵尸，命令: $(ps -p $ppid -o comm=)"
    # 决定是否需要重启该父进程
done
```

**孤儿进程（Orphan Process）：**

```bash
# 产生原因：父进程先于子进程退出
# 子进程成为孤儿，被 init/systemd (PID 1) 收养

# 孤儿进程是正常现象，不需要特别处理
# 守护进程就是通过有意制造"孤儿"来实现的（fork 两次）

# 查看被 systemd 收养的进程
ps -eo pid,ppid,comm | awk '$2 == 1' | head -20
```

### 3. ps 命令深入

#### 3.1 两种语法风格

ps 支持两种不兼容的语法，这是初学者最容易混淆的地方：

```
BSD 风格（不带 -）：    ps aux
  → 来自 Berkeley Software Distribution
  → 选项不带 - 前缀
  → 合并选项：aux（不是 a u x）

POSIX 风格（带 -）：    ps -ef
  → 来自 POSIX/SUS 标准
  → 选项带 - 前缀
  → 可分开写：ps -e -f
```

| 风格 | 列出所有进程 | 完整格式 | 自定义格式 |
|------|------------|---------|-----------|
| BSD | `ps aux` | `ps aux` | `ps -eo pid,comm` |
| POSIX | `ps -ef` | `ps -ef` | `ps -eo pid,comm` |

**推荐使用 POSIX 风格 `ps -eo` 自定义格式，更灵活。**

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
| USER | 启动用户 | 实际 UID |
| PID | 进程 ID | — |
| %CPU | CPU 使用率 | 采样周期内的平均值，多线程可超过 100% |
| %MEM | 内存占比 | RSS / 总物理内存 |
| **VSZ** | 虚拟内存大小（KB）| 进程申请的总地址空间（含未分配的） |
| **RSS** | 常驻内存大小（KB） | 实际使用的物理内存 |
| TTY | 关联的终端 | `?` 表示无终端（守护进程） |
| STAT | 状态码 | 包含主状态 + 修饰符 |
| START | 启动时间 | — |
| TIME | CPU 累计使用 | 进程从启动到现在的 CPU 时间（不含睡眠） |
| COMMAND | 命令行 | 可能被截断，加 `ww` 或用 `-eo args` |

**VSZ vs RSS vs PSS vs USS 的区别：**

```
VSZ（虚拟内存） = 代码段 + 数据段 + 堆 + 栈 + 共享库映射 + mmap
  → 包含未分配的虚拟地址空间
  → 数值通常很大，参考意义有限

RSS（常驻内存） = 实际加载到 RAM 中的页面
  → 包含共享库（多个进程共享的部分重复计算）
  → 比 VSZ 更有意义，但共享部分被重复计算

PSS（比例共享内存） = 私有内存 + 共享内存/共享进程数
  → 最准确的内存使用衡量
  → 查看：cat /proc/<PID>/smaps_rollup

USS（独占内存） = 只属于该进程的物理内存
  → 进程退出后能释放的内存量
```

#### 3.3 ps -ef 输出详解

```bash
ps -ef
# UID        PID  PPID  C STIME TTY          TIME CMD
# root         1     0  0 Apr25 ?        00:00:05 /sbin/init
# root       512     1  0 Apr25 ?        00:00:00 /usr/sbin/sshd
# sreuser   1234   567  0 10:00 pts/0    00:00:30 java -jar app.jar
```

| 列名 | 含义 |
|------|------|
| UID | 启动用户 |
| PID | 进程 ID |
| PPID | 父进程 ID |
| C | CPU 使用率的整数近似值（旧版调度用，现在基本忽略） |
| STIME | 启动时间 |
| TTY | 关联终端 |
| TIME | CPU 累计时间 |
| CMD | 完整命令行 |

#### 3.4 自定义输出格式（-o 选项）

```bash
# 自定义列名（POSIX 风格）
ps -eo pid,ppid,user,stat,%cpu,%mem,rss,comm

# 常用的自定义列名
# pid      - 进程 ID
# ppid     - 父进程 ID
# user     - 启动用户
# stat     - 状态码
# %cpu     - CPU 使用率
# %mem     - 内存占比
# rss      - 常驻内存（KB）
# vsz      - 虚拟内存（KB）
# comm     - 命令名（短）
# args     - 完整命令行（长）
# start    - 启动时间
# time     - CPU 累计时间
# etime    - 运行时间（elapsed time）
# tty      - 关联终端
# nlwp     - 线程数
# pri      - 优先级
# ni       - nice 值
# pgid     - 进程组 ID
# sid      - 会话 ID
# uid      - 启动用户 UID
# euid     - 有效用户 UID
# ruid     - 实际用户 UID
# oom      - OOM 评分
# oom_adj  - OOM 调整值

# 带表头的自定义格式
ps -eo pid,ppid,user,stat,%cpu,%mem,rss,nlwp,etime,comm --sort=-%cpu | head -20

# 带自定义表头
ps -eo pid=PID,ppid=PPID,user=USER,stat=STAT,%cpu=CPU,%mem=MEM,rss=RSS_KB,comm=COMMAND
```

#### 3.5 排序（--sort）

```bash
# 按 CPU 使用率降序
ps aux --sort=-%cpu | head -10

# 按内存使用降序
ps aux --sort=-%mem | head -10

# 按运行时间降序
ps -eo pid,etime,comm --sort=-etime | head -10

# 按 PID 排序
ps aux --sort=pid | head -10

# 多字段排序（先按 CPU 降序，再按内存降序）
ps aux --sort=-%cpu,-%mem | head -10

# 按线程数排序（找多线程进程）
ps -eo pid,nlwp,comm --sort=-nlwp | head -10

# 按 RSS 排序（找占用内存最多的进程）
ps -eo pid,rss,comm --sort=-rss | head -10
```

#### 3.6 ps + awk 实用组合

```bash
# 找出 CPU 使用超过 50% 的进程
ps aux | awk 'NR>1 && $3 > 50 {printf "PID=%s CPU=%s%% CMD=%s\n", $2, $3, $11}'

# 统计每个用户的进程数
ps aux | awk 'NR>1 {count[$1]++} END {for(u in count) printf "%4d %s\n", count[u], u}' | sort -rn

# 统计各状态的进程数
ps aux | awk 'NR>1 {
    state = substr($8, 1, 1)
    count[state]++
} END {
    for(s in count) printf "%4d %s\n", count[s], s
}'

# 查找运行超过 24 小时的进程
ps -eo pid,etime,comm | awk 'NR>1 && $2 ~ /-/ {print}'

# 查找线程数超过 100 的进程
ps -eo pid,nlwp,comm --sort=-nlwp | awk 'NR>1 && $2 > 100 {print}'

# 查找内存使用超过 1GB 的进程
ps -eo pid,rss,comm --sort=-rss | awk 'NR>1 && $2 > 1048576 {printf "PID=%s RSS=%dMB CMD=%s\n", $1, $2/1024, $3}'
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

**第一行（概览行）：**

| 字段 | 含义 |
|------|------|
| 14:30:25 | 当前时间 |
| up 5 days, 3:22 | 系统运行时间 |
| 2 users | 当前登录终端数 |
| load average: 0.52, 0.38, 0.29 | 1/5/15 分钟平均负载 |

**第二行（Tasks 行）：**

| 字段 | 含义 |
|------|------|
| 186 total | 进程总数 |
| 1 running | 正在运行的进程数 |
| 185 sleeping | 睡眠中的进程数 |
| 0 stopped | 被停止的进程数 |
| 0 zombie | 僵尸进程数 |

**第三行（CPU 行）— 最关键的一行：**

| 字段 | 含义 | 阈值 |
|------|------|------|
| **us** | 用户空间 CPU 时间（应用代码） | > 70% 说明应用 CPU 密集 |
| **sy** | 内核空间 CPU 时间（系统调用、中断） | > 20% 说明系统调用过多 |
| **ni** | nice 调整后的用户空间时间 | — |
| **id** | 空闲时间 | < 10% 说明 CPU 紧张 |
| **wa** | I/O 等待时间 | > 20% 说明 I/O 瓶颈 |
| **hi** | 硬件中断时间 | > 5% 说明中断处理开销大 |
| **si** | 软件中断时间 | > 10% 说明网络包处理压力大 |
| **st** | 被虚拟化平台偷走的时间（steal time） | > 5% 说明宿主机过载 |

**第四行（Mem 行）和第五行（Swap 行）：**

| 字段 | 含义 |
|------|------|
| total | 总物理内存 |
| free | 完全未使用的内存（不代表可用！） |
| used | 已使用的内存 |
| buff/cache | 缓冲区 + 页面缓存（可回收） |
| avail Mem | 真正可用的内存（free + 可回收的缓存） |
| Swap total/free/used | 交换空间使用情况 |

**进程列表列：**

| 列名 | 含义 | 说明 |
|------|------|------|
| PID | 进程 ID | — |
| USER | 启动用户 | — |
| PR | 优先级 | rt = 实时优先级，20 = 默认 |
| NI | nice 值 | -20 ~ 19 |
| VIRT | 虚拟内存 | VSZ |
| RES | 常驻内存 | RSS |
| SHR | 共享内存 | 共享库、共享内存段 |
| S | 状态 | R/S/D/Z/T |
| %CPU | CPU 使用率 | — |
| %MEM | 内存占比 | — |
| TIME+ | CPU 累计时间 | — |
| COMMAND | 命令行 | — |

#### 4.2 Load Average 的真正含义

```
load average = 处于以下状态的进程数（在采样周期内的指数加权移动平均）：
  R（Running/Runnable）→ 正在使用或等待使用 CPU
  D（Uninterruptible Sleep）→ 等待 I/O 完成（不可中断）

注意：Load Average 不包含 S（可中断睡眠）状态的进程！
这就是为什么等待网络请求的进程不计入负载。
```

**与 CPU 核数的关系：**

```
单核 CPU：
  load = 0.5  → CPU 一半时间空闲
  load = 1.0  → CPU 刚好满载
  load = 2.0  → CPU 过载，1 个进程在排队

4 核 CPU：
  load = 2.0  → CPU 使用率约 50%
  load = 4.0  → CPU 刚好满载
  load = 8.0  → CPU 过载，4 个进程在排队

经验法则：
  load < 核数 × 0.7  → 健康
  load ≈ 核数         → 满载，需要关注
  load > 核数 × 1.5  → 过载，需要处理
  load > 核数 × 3.0  → 严重过载
```

**常见误区：**

```
误区 1："Load Average 高 = CPU 不够"
→ 错！如果 wa（I/O wait）高，Load 也可能高但 CPU 很空闲
→ 此时瓶颈在磁盘/网络，不是 CPU
→ 关键：结合 CPU 的 id/wa 列一起判断

误区 2："Load Average 是百分比"
→ 错！它是绝对值。4 核机器 load=4 才满载，不是 load=1

误区 3："15 分钟平均值比 1 分钟的更可靠"
→ 不一定！15 分钟的平均会"稀释"短时高峰
→ 对实时告警，1 分钟更有价值
→ 对趋势分析，15 分钟更平滑
→ 最佳实践：同时监控 1min 和 15min
```

```bash
# 查看 CPU 核心数
nproc
# 或
grep -c ^processor /proc/cpuinfo
# 或
lscpu | grep "^CPU(s):"

# 计算负载/核心数比值
cores=$(nproc)
load=$(cat /proc/loadavg | awk '{print $1}')
echo "核心数: $cores, 负载: $load, 比值: $(echo "scale=2; $load/$cores" | bc)"
```

#### 4.3 top 交互命令

进入 top 后按以下快捷键：

| 按键 | 功能 | 说明 |
|------|------|------|
| `P` | 按 CPU 排序 | 默认排序方式 |
| `M` | 按内存排序 | 找内存大户 |
| `N` | 按 PID 排序 | — |
| `T` | 按累计 CPU 时间排序 | — |
| `R` | 反转排序 | 切换升序/降序 |
| `c` | 切换显示完整命令 | — |
| `1` | 展开/折叠所有 CPU 核心 | 看每个核心的使用率 |
| `k` | 杀死进程 | 输入 PID 和信号编号 |
| `r` | 重新设置 nice 值 | 调整进程优先级 |
| `f` | 自定义显示的列 | 选择/排序列 |
| `o` | 设置过滤条件 | 如 `%CPU>5.0` |
| `H` | 切换显示线程 | 显示线程而非进程 |
| `V` | 树形视图 | 显示父子关系 |
| `W` | 保存当前配置 | 写入 `~/.toprc` |
| `d` | 修改刷新间隔 | 默认 3 秒 |
| `q` | 退出 | — |
| `?` | 帮助 | — |

#### 4.4 top 批处理模式

```bash
# 运行一次就退出（适合脚本和监控系统）
top -b -n 1

# 每 2 秒采样一次，共 3 次，输出到文件
top -b -d 2 -n 3 > /tmp/top_output.txt

# 只监控特定进程
top -b -n 1 -p $(pgrep -d',' nginx)

# 监控多个进程
top -b -n 1 -p 1234,5678,9012

# 持续监控 CPU 排名前 10 的进程
top -b -d 5 | grep --line-buffered -A 10 "^top"

# 提取关键指标到 CSV
top -b -n 1 | head -5 | awk '/^%Cpu/ {print "CPU:", $2+$4+$6, "used"}'
```

### 5. htop — 增强版 top

#### 5.1 htop 优势

```bash
# 安装
sudo apt install htop       # Debian/Ubuntu
sudo yum install htop       # RHEL/CentOS
sudo dnf install htop       # Fedora

# 启动
htop
```

```
htop 相比 top 的优势：
  ✅ 彩色显示，可读性更好
  ✅ 支持鼠标点击操作
  ✅ 树形视图（F5 切换）
  ✅ 支持进程多选（空格键标记）
  ✅ 内置搜索（F3）
  ✅ 内置过滤（F4）
  ✅ 不需要输入 PID，直接选择操作
  ✅ 显示完整的 CPU/内存/Swap 使用条
  ✅ 支持横向滚动查看完整命令
  ✅ 可以直接调整 nice 值（F7/F8）
```

#### 5.2 htop 快捷键

| 按键 | 功能 |
|------|------|
| `F1` | 帮助 |
| `F2` | 设置（显示列、颜色方案等） |
| `F3` | 搜索进程名 |
| `F4` | 过滤（只显示匹配的进程） |
| `F5` | 树形视图 |
| `F6` | 选择排序列 |
| `F7` | 增加 nice 值（降低优先级） |
| `F8` | 减少 nice 值（提高优先级） |
| `F9` | 发送信号（kill） |
| `F10` | 退出 |
| `空格` | 标记进程（可多选后批量操作） |
| `t` | 树形/列表切换 |
| `H` | 隐藏/显示用户线程 |
| `K` | 隐藏/显示内核线程 |
| `u` | 按用户过滤 |

#### 5.3 htop 配置

```bash
# htop 配置文件
~/.config/htop/htoprc

# 常用配置项
# fields=0 48 17 18 38 39 40 2 46 47 49 1  # 显示的列
# sort_key=48                                 # 默认排序列（48=%CPU）
# sort_direction=-1                           # 降序
# tree_view=1                                 # 默认树形视图
# highlight_changes=1                         # 高亮变化的数值
# color_scheme=6                              # 颜色方案
```

### 6. pstree — 进程树

#### 6.1 基本用法

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

# 显示特定用户的进程树
pstree -ap sreuser

# 输出示例：
# systemd,1
#   ├─sshd,512
#   │   └─sshd,1234
#   │       └─bash,1235
#   │           └─java,1236 -jar /opt/app.jar
#   ├─nginx,567
#   │   ├─nginx,568 (worker)
#   │   └─nginx,569 (worker)
#   ├─dockerd,890
#   │   └─containerd,891
#   │       └─containerd-shim,892
#   │           └─app,893
#   └─cron,456
```

#### 6.2 pstree 实用场景

```bash
# 场景 1：查看 nginx 的进程架构
pstree -ap $(pgrep nginx | head -1)
# 输出：
# nginx,567
#   ├─nginx,568
#   └─nginx,569
# 说明：567 是 master，568/569 是 worker

# 场景 2：查看 Java 应用的线程
pstree -ap $(pgrep java | head -1) | head -30

# 场景 3：查看 Docker 容器内的进程关系
pstree -ap $(docker inspect --format '{{.State.Pid}}' <container_id>)

# 场景 4：找出某个服务的所有子进程
pstree -ap $(systemctl show -p MainPID <service> --value)

# 场景 5：检查是否有异常的进程树深度
pstree -c | awk -F'─' '{print NF, $0}' | sort -rn | head -5
```

### 7. /proc/[PID]/ 目录详解

`/proc` 是内核向用户空间暴露信息的虚拟文件系统（procfs），每个进程有独立目录：

#### 7.1 常用文件详解

```bash
# === 基本信息 ===
cat /proc/1/status       # 结构化的状态信息（Name、State、Pid、PPid、VmRSS 等）
cat /proc/1/cmdline      # 命令行参数（\0 分隔，用 tr '\0' ' ' 转换）
cat /proc/1/environ      # 环境变量（\0 分隔，可能包含密码等敏感信息！）
cat /proc/1/comm         # 进程名（短，最多 16 字符）
cat /proc/1/exe          # 可执行文件的符号链接
cat /proc/1/cwd          # 当前工作目录的符号链接
cat /proc/1/root         # 进程的根目录（chroot 场景下不同于系统根目录）

# === 资源限制 ===
cat /proc/1/limits       # 资源限制（Max open files、Max processes 等）

# === 文件描述符 ===
ls -la /proc/1/fd/       # 打开的文件描述符列表
# 每个 fd 是一个符号链接，指向实际的文件/socket/pipe
# 0 -> /dev/null (stdin)
# 1 -> /dev/null (stdout)
# 2 -> /dev/null (stderr)
# 3 -> socket:[12345]
# 4 -> /var/log/app.log

# === 内存信息 ===
cat /proc/1/maps         # 内存映射（详细的虚拟地址空间布局）
cat /proc/1/smaps        # 增强版 maps（包含每段的 RSS、PSS、Swap 等）
cat /proc/1/smaps_rollup # 汇总的内存使用统计
cat /proc/1/statm        # 内存使用统计（数字格式）

# === 调度信息 ===
cat /proc/1/stat         # 进程状态（数字格式，脚本解析用）
cat /proc/1/stat         # 包含：PID、状态、PPID、CPU 时间、优先级等
cat /proc/1/sched        # 调度统计信息

# === I/O 信息 ===
cat /proc/1/io           # I/O 统计（读写字节数、系统调用次数）
# rchar: 读取的字节数（含缓存）
# wchar: 写入的字节数（含缓存）
# read_bytes: 从存储设备读取的字节数
# write_bytes: 写入存储设备的字节数

# === 网络信息 ===
cat /proc/1/net/tcp      # 进程的 TCP 连接
cat /proc/1/net/udp      # 进程的 UDP 连接

# === 信号信息 ===
cat /proc/1/status | grep -i sig
# SigPnd: 待处理的信号
# SigBlk: 被阻塞的信号
# SigIgn: 被忽略的信号
# SigCgt: 被捕获的信号
```

#### 7.2 实用的 /proc 查询技巧

```bash
# 查看进程的工作目录
readlink /proc/<PID>/cwd

# 查看进程的可执行文件路径
readlink /proc/<PID>/exe

# 查看进程打开的所有文件
ls -la /proc/<PID>/fd/

# 统计每个进程打开的文件数
for pid in /proc/[0-9]*/fd; do
    count=$(ls "$pid" 2>/dev/null | wc -l)
    ppid=$(basename $(dirname "$pid"))
    comm=$(cat /proc/$ppid/comm 2>/dev/null)
    echo "$count $ppid $comm"
done | sort -rn | head -10

# 全局文件描述符统计
cat /proc/sys/fs/file-nr
# 输出：已分配  未使用  最大值

# 查看某个进程的 OOM 评分
cat /proc/<PID>/oom_score

# 查看进程的命名空间
ls -la /proc/<PID>/ns/

# 查看进程的 cgroup
cat /proc/<PID>/cgroup

# 查看进程的挂载信息
cat /proc/<PID>/mounts

# 查看线程信息
ls /proc/<PID>/task/
# 每个子目录就是一个线程，目录名就是线程 ID（TID）
```

#### 7.3 /proc 系统级信息

```bash
# === CPU 信息 ===
cat /proc/cpuinfo         # CPU 详细信息
cat /proc/stat            # CPU 使用统计（系统级）

# === 内存信息 ===
cat /proc/meminfo         # 内存详细信息
cat /proc/vmstat          # 虚拟内存统计
cat /proc/zoneinfo        # 内存区域信息

# === 磁盘和文件系统 ===
cat /proc/diskstats       # 磁盘 I/O 统计
cat /proc/mounts          # 挂载信息
cat /proc/filesystems     # 支持的文件系统

# === 网络 ===
cat /proc/net/dev         # 网络接口统计
cat /proc/net/tcp         # TCP 连接表
cat /proc/net/udp         # UDP 连接表
cat /proc/net/sockstat    # Socket 统计

# === 系统配置 ===
cat /proc/sys/kernel/pid_max       # 最大 PID 值
cat /proc/sys/fs/file-max          # 系统最大文件描述符数
cat /proc/sys/fs/file-nr           # 当前已分配/未使用/最大
cat /proc/sys/net/core/somaxconn   # TCP 监听队列最大长度
cat /proc/sys/vm/swappiness        # Swap 使用倾向（0-100）
```

---

## 💻 实战练习

### 练习 1：基础操作

```bash
# 1. 查看系统中所有进程，按 CPU 使用率排序，取前 10
ps aux --sort=-%cpu | head -10

# 2. 查看系统中所有进程，按内存使用排序，取前 10
ps aux --sort=-%mem | head -10

# 3. 查看 nginx 相关的所有进程
ps aux | grep '[n]ginx'
# 或
pgrep -la nginx

# 4. 查看 PID 1 的详细信息
cat /proc/1/status | head -20

# 5. 查看系统中有多少个进程
ps aux | wc -l

# 6. 统计各状态的进程数
ps -eo stat | awk 'NR>1 {state=substr($1,1,1); count[state]++} END {for(s in count) print s, count[s]}'
```

### 练习 2：进阶场景

```bash
# 1. 找出占用内存最多的 5 个进程，显示 PID、内存、命令
ps -eo pid,rss,comm --sort=-rss | head -6

# 2. 找出线程数最多的 5 个进程
ps -eo pid,nlwp,comm --sort=-nlwp | head -6

# 3. 找出运行时间最长的 5 个进程
ps -eo pid,etime,comm --sort=-etime | head -6

# 4. 查看某个进程的内存映射
pmap -x $(pgrep nginx | head -1) | tail -5

# 5. 查看某个进程打开的文件描述符数量
ls /proc/$(pgrep nginx | head -1)/fd/ | wc -l

# 6. 监控某个进程的 CPU 和内存变化（每 5 秒）
while true; do
    ps -p $(pgrep nginx | head -1) -o pid,%cpu,%mem,rss,etime --no-headers
    sleep 5
done
```

### 练习 3：故障排查挑战

**挑战 1：服务器 load average 很高，但 CPU 使用率很低**

```bash
# 可能原因：D 状态进程过多（I/O 瓶颈）
# 排查步骤：
ps aux | awk '$8 ~ /^D/ {print}'     # 找 D 状态进程
iostat -x 1 5                          # 检查磁盘 I/O
dmesg | tail -20                       # 检查内核日志
```

**挑战 2：某进程 CPU 100%，如何排查**

```bash
# 排查步骤：
top -b -n 1 -p <PID>                   # 确认 CPU 使用率
cat /proc/<PID>/status | grep Threads  # 查看线程数
strace -c -p <PID> -t 10              # 统计系统调用（10 秒）
# 或
perf top -p <PID>                      # 实时函数级 CPU 采样
```

**挑战 3：文件描述符耗尽**

```bash
# 排查步骤：
cat /proc/sys/fs/file-nr               # 查看系统级 FD 使用
ls /proc/<PID>/fd/ | wc -l            # 查看进程级 FD 数量
cat /proc/<PID>/limits                 # 查看进程 FD 限制
lsof -p <PID> | wc -l                 # 统计打开的文件数
lsof -p <PID> | awk '{print $5}' | sort | uniq -c | sort -rn  # 按类型统计
```

---

## 🏗️ SRE 实战案例

### 案例 1：OOM Kill 排查

```bash
# 场景：Java 应用突然消失，怀疑被 OOM Killer 杀死

# 第一步：查看内核日志
sudo dmesg -T | grep -i "oom\|killed process\|out of memory"

# 输出示例：
# [Mon May 02 14:30:00 2026] java invoked oom-killer: gfp_mask=0x280da, order=0, oom_score_adj=0
# [Mon May 02 14:30:00 2026] Out of memory: Killed process 1234 (java) total-vm:2048000kB, anon-rss:1024000kB
# [Mon May 02 14:30:00 2026] oom_reaper: reaped process 1234 (java), now anon-rss:0kB

# 第二步：查看系统日志
sudo journalctl -k --since "1 hour ago" | grep -i oom
sudo grep -i "oom\|killed process" /var/log/kern.log

# 第三步：分析内存使用情况
free -h
cat /proc/meminfo | grep -E "^(MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree)"

# 第四步：查看当前进程的 OOM 评分
ps -eo pid,comm,%mem,oom_score --sort=-oom_score | head -20

# 第五步：保护关键进程
echo -1000 > /proc/$(pgrep sshd)/oom_score_adj  # 保护 sshd
echo -500 > /proc/$(pgrep nginx | head -1)/oom_score_adj  # 保护 nginx

# 第六步：长期方案
# 1. 设置 cgroup 内存限制
# 2. 在 systemd 服务文件中配置 OOMScoreAdjust
# 3. 安装 earlyoom 提前干预
```

### 案例 2：进程 CPU 100% 排查

```bash
# 场景：某 Java 进程 CPU 持续 100%

# 第一步：确认问题进程
top -b -n 1 | head -15

# 第二步：查看进程的线程
ps -T -p <PID> | head -20

# 第三步：找出 CPU 最高的线程
top -H -b -n 1 -p <PID> | head -10

# 第四步：使用 strace 查看系统调用
sudo strace -c -p <PID> -t 30
# 输出示例：
# % time     seconds  usecs/call     calls    errors syscall
# ------ ----------- ----------- --------- --------- ----------------
#  95.00    2.850000          28     100000           read
#   3.00    0.090000           9      10000           write
# → 大量 read 系统调用，可能是死循环读取

# 第五步：使用 perf 进行函数级分析
sudo perf top -p <PID>
# 或生成火焰图
sudo perf record -p <PID> -g -- sleep 30
sudo perf script | stackcollapse-perf.pl | flamegraph.pl > flamegraph.svg

# 第六步：如果是 Java 进程
kill -3 <PID>   # 线程 dump 到 stdout（不杀死进程）
jstack <PID>    # 或使用 jstack
```

### 案例 3：文件描述符耗尽排查

```bash
# 场景：应用报错 "Too many open files"

# 第一步：检查系统级 FD 使用
cat /proc/sys/fs/file-nr
# 输出：已分配  未使用  最大值
# 例如：65536   0       9223372036854775807

# 第二步：检查进程级 FD 使用
PID=$(pgrep myapp | head -1)
ls /proc/$PID/fd/ | wc -l
# 与限制比较
cat /proc/$PID/limits | grep "Max open files"

# 第三步：找出打开最多 FD 的进程
for pid in /proc/[0-9]*/fd; do
    count=$(ls "$pid" 2>/dev/null | wc -l)
    ppid=$(basename $(dirname "$pid"))
    comm=$(cat /proc/$ppid/comm 2>/dev/null)
    echo "$count $ppid $comm"
done | sort -rn | head -10

# 第四步：分析 FD 指向什么
lsof -p <PID> | awk '{print $5}' | sort | uniq -c | sort -rn
# 输出示例：
# 50000 IPv4  → 大量 socket 连接未关闭
# 100  REG   → 打开的文件
# 5   FIFO  → 管道

# 第五步：临时修复
ulimit -n 65535  # 当前 shell 会话
# 或修改 /etc/security/limits.conf

# 第六步：永久修复
# 在 systemd 服务文件中：
# [Service]
# LimitNOFILE=65535
```

---

## 🎯 面试题精选

### 面试题 1：fork 和 exec 的区别是什么？

**参考答案：**

fork 创建当前进程的副本（子进程），父子进程共享代码段但有独立的数据段和栈。exec 用新程序替换当前进程的内存空间，保留 PID 和文件描述符（除非设置了 close-on-exec）。

典型流程：shell 先 fork 创建子进程，子进程再 exec 加载要执行的程序。fork 采用写时复制（COW）技术，只有在某一方写入时才复制物理页面，大幅提高了效率。

fork 返回两次：父进程返回子进程 PID，子进程返回 0。exec 不返回（除非出错），因为进程的代码已被替换。

### 面试题 2：什么是僵尸进程？如何处理？

**参考答案：**

僵尸进程是已调用 exit() 但父进程未调用 wait()/waitpid() 回收的子进程。它不消耗 CPU 和内存，但占用 PID 表项。大量僵尸进程会导致 PID 耗尽。

处理方法：
1. 发送 SIGCHLD 给父进程，通知它回收子进程
2. 如果父进程不响应，杀死父进程，僵尸被 init (PID 1) 收养并自动回收
3. 如果父进程是 systemd 管理的服务，重启该服务

根本解决：父进程应正确处理 SIGCHLD 信号，或使用 signal(SIGCHLD, SIG_IGN) 让内核自动回收。

### 面试题 3：load average 高但 CPU 空闲，怎么回事？

**参考答案：**

load average 包含 R 状态（运行/可运行）和 D 状态（不可中断睡眠）的进程。CPU 空闲但 load 高，说明有大量 D 状态进程。

常见原因：
1. 磁盘 I/O 瓶颈（最常见）：大量进程等待磁盘读写完成
2. NFS 挂载问题：NFS 服务器无响应导致客户端进程卡在 D 状态
3. 内核锁竞争：某些内核操作需要等待锁
4. 存储硬件故障：磁盘或控制器故障

排查方法：用 iostat 检查磁盘 I/O，用 dmesg 检查内核日志，用 ps aux | awk '$8 ~ /^D/' 找出 D 状态进程。

### 面试题 4：VSZ 和 RSS 的区别是什么？

**参考答案：**

VSZ（Virtual Size）是进程申请的虚拟地址空间总量，包括代码段、数据段、堆、栈、共享库映射、mmap 映射等。它包含尚未分配物理页面的虚拟地址，所以数值通常很大。

RSS（Resident Set Size）是进程实际使用的物理内存，即已加载到 RAM 中的页面。RSS 包含与其他进程共享的库，因此多个进程的 RSS 之和会大于实际物理内存使用量。

更准确的指标是 PSS（Proportional Set Size），它将共享内存按共享进程数均分。

### 面试题 5：如何查看某个进程打开了哪些文件？

**参考答案：**

三种方法：
1. `ls -la /proc/<PID>/fd/` — 查看文件描述符符号链接
2. `lsof -p <PID>` — 查看详细的打开文件列表
3. `ls -la /proc/<PID>/fd/ | wc -l` — 统计打开的文件数量

`/proc/<PID>/fd/` 中每个条目都是符号链接，指向实际的文件、socket 或 pipe。0/1/2 分别对应 stdin/stdout/stderr。

### 面试题 6：top 命令中的 wa 是什么？什么情况下会变高？

**参考答案：**

wa（iowait）是 CPU 空闲且有未完成的磁盘 I/O 请求的时间百分比。wa 高说明 CPU 在等磁盘，瓶颈在 I/O 而不是 CPU。

wa 变高的场景：
1. 数据库大量查询导致磁盘 I/O 飙升
2. 日志大量写入
3. 磁盘性能下降（坏道、SSD 寿命到期）
4. NFS 远程文件系统延迟

注意：wa 高不代表 CPU 忙，只是说 CPU 在等 I/O。如果同时 id 也高，说明 CPU 本身不忙，瓶颈确实在磁盘。

### 面试题 7：如何判断一个进程是 CPU 密集型还是 I/O 密集型？

**参考答案：**

1. 用 top 看 %CPU 列：持续 > 80% 是 CPU 密集型
2. 用 top 看 wa：> 20% 且进程在等 I/O 是 I/O 密集型
3. 用 strace -c 统计系统调用：大量 read/write 是 I/O 密集型，大量计算是 CPU 密集型
4. 用 vmstat 看 r 和 b 列：r 大说明 CPU 排队，b 大说明 I/O 排队
5. 用 iostat 看 %util：接近 100% 说明磁盘饱和

### 面试题 8：/proc 文件系统有什么作用？

**参考答案：**

/proc 是内核向用户空间暴露信息的虚拟文件系统（procfs），不在磁盘上，只存在于内存中。

主要用途：
1. 进程信息：`/proc/[PID]/status`、`cmdline`、`fd/`、`maps`
2. 系统信息：`/proc/cpuinfo`、`meminfo`、`stat`
3. 内核参数：`/proc/sys/` 下的可读写文件，用于调优
4. 网络信息：`/proc/net/tcp`、`dev`、`sockstat`

SRE 可以直接读取 /proc 获取进程状态，无需额外工具。例如 `/proc/[PID]/oom_score` 查看 OOM 评分，`/proc/sys/fs/file-nr` 查看文件描述符使用情况。

---

## 📚 深入阅读

- [Brendan Gregg — Linux Performance](http://www.brendangregg.com/linuxperf.html) — Linux 性能分析权威指南
- [The Linux Programming Interface](https://www.nostarch.com/tlpi.htm) — Michael Kerrisk，进程章节极为详细
- `/proc` 文件系统文档：`man 5 proc`
- [strace 教程](https://jvns.ca/blog/2014/10/05/why-debugging-is-fun/) — Julia Evans 的调试博客
- [Understanding the Linux Kernel](https://www.oreilly.com/library/view/understanding-the-linux/0596005652/) — 进程调度和内存管理深入
- [Linux 内核设计与实现](https://www.kernel.org/doc/html/latest/) — 内核文档
- [perf Examples](http://www.brendangregg.com/perf.html) — Brendan Gregg 的 perf 使用示例

---

## ✅ 自检清单

- [ ] 理解 task_struct 包含哪些关键字段
- [ ] 能画出 fork + exec + COW 的完整流程图
- [ ] 能解释 R/S/D/Z/T 每种状态的含义和产生原因
- [ ] 熟练使用 ps aux 和 ps -eo 自定义格式输出
- [ ] 能解释 top 中 us/sy/wa/id 的含义
- [ ] 理解 load average 包含 D 状态进程，不只是 CPU 负载
- [ ] 知道 VSZ/RSS/PSS 的区别
- [ ] 能通过 /proc/[PID]/fd/ 排查文件描述符问题
- [ ] 能独立完成 OOM Kill 排查流程
- [ ] 能独立完成 CPU 100% 排查流程
- [ ] 能处理僵尸进程问题
