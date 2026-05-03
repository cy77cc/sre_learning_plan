# Day 11: 系统监控命令 — uptime/free/df/vmstat/sar/iostat

> 📅 日期：2026-05-02
> 📖 学习主题：系统监控命令 — uptime/free/df/vmstat/sar/iostat
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 08-10（进程管理与 systemd）

## 🎯 学习目标

完成 Day 11 的学习后，你应该能够：
- 深入理解 Load Average 的真正含义（不只是 CPU，还包括 D 状态进程）
- 使用 free 准确解读内存使用（buff/cache vs available、内存回收机制）
- 使用 df/du 分析磁盘空间，理解 inode 耗尽和已删除未释放文件
- 使用 vmstat 分析系统整体性能瓶颈（重点关注 si/so、wa）
- 使用 sar 回溯历史性能数据（事后排障利器）
- 使用 iostat 分析磁盘 I/O 瓶颈（%util vs await vs svctm）
- 掌握 USE 方法论（Utilization、Saturation、Errors）
- 独立完成服务器响应变慢的完整排查链路

---

## 📖 核心知识点

### 1. Linux 性能指标体系

```
Brendan Gregg 的 Linux 性能分析工具图（简化版）：

  ┌─────────────────────────────────────────────────────────────┐
  │                    应用程序                                  │
  │         (strace, perf, gdb, flame graphs)                   │
  ├─────────────────────────────────────────────────────────────┤
  │                    系统库                                    │
  │              (ltrace, LD_PRELOAD)                           │
  ├─────────────────────────────────────────────────────────────┤
  │                    系统调用                                  │
  │         (strace, perf trace, bpftrace)                     │
  ├──────────┬──────────┬──────────┬────────────────────────────┤
  │   VFS    │  调度器   │   内存    │  网络栈                    │
  │          │          │  管理器   │                            │
  ├──────────┼──────────┼──────────┼────────────────────────────┤
  │ 文件系统 │ 进程调度 │ 页面回收  │  TCP/IP                    │
  │ ext4/xfs │   CFS    │  kswapd  │  socket                   │
  ├──────────┴──────────┴──────────┴────────────────────────────┤
  │                    块设备层                                  │
  │              (iostat, iotop, blktrace)                      │
  ├─────────────────────────────────────────────────────────────┤
  │                    硬件层                                    │
  │    CPU │ 内存 │ 磁盘 │ 网卡 │ (perf, turbostat)            │
  └─────────────────────────────────────────────────────────────┘

  四大资源：
  ┌──────────┬───────────────┬──────────────────┐
  │  资源     │  利用率(U)     │  饱和度(S)        │
  ├──────────┼───────────────┼──────────────────┤
  │  CPU     │  us+sy        │  run queue (r)    │
  │  内存    │  used/total   │  swap I/O (si/so) │
  │  磁盘 I/O│  %util        │  queue length     │
  │  网络    │  bandwidth    │  drops            │
  └──────────┴───────────────┴──────────────────┘
```

### 2. USE 方法论

USE（Utilization、Saturation、Errors）是 Brendan Gregg 提出的性能分析方法论：

```
USE 方法：

  U — Utilization（利用率）
    资源繁忙的时间百分比
    例如：CPU 使用率 80%

  S — Saturation（饱和度）
    资源过载的程度（排队等待的程度）
    例如：运行队列中有 5 个进程等待 CPU

  E — Errors（错误数）
    资源发生的错误次数
    例如：磁盘 I/O 错误 3 次

排查顺序：Errors → Saturation → Utilization
  先查错误（最严重）
  再查饱和（性能问题）
  最后查利用率（容量规划）
```

### 3. uptime / load average

#### 3.1 输出解读

```bash
uptime
# 14:30:25 up 30 days, 2:15,  2 users,  load average: 0.52, 0.38, 0.29
```

| 字段 | 含义 |
|------|------|
| 14:30:25 | 当前时间 |
| up 30 days, 2:15 | 系统运行时间 |
| 2 users | 当前登录的终端用户数 |
| load average: 0.52, 0.38, 0.29 | 1/5/15 分钟平均负载 |

#### 3.2 Load Average 的深层含义

```
load average = 采样周期内处于以下状态的进程数的指数加权移动平均：

  R（Running / Runnable）
    → 正在使用 CPU 或在运行队列中等待 CPU
    → CPU 密集型任务导致

  D（Uninterruptible Sleep）
    → 等待 I/O 完成（磁盘、NFS、内核锁）
    → I/O 密集型任务导致

关键：Load Average 不包含 S（可中断睡眠）状态的进程！
→ 等待网络请求的进程不计入负载
→ 等待用户输入的进程不计入负载
→ 只有"正在消耗资源"的进程才计入
```

#### 3.3 与 CPU 核数的关系

```bash
# 查看 CPU 核心数
nproc
grep -c ^processor /proc/cpuinfo
lscpu | grep "^CPU(s):"
```

```
解读指南：

  负载/核心数比值    含义
  ─────────────────  ──────────────────────
  < 0.5              健康，CPU 充足
  0.5 - 0.7          正常，CPU 有一定余量
  0.7 - 1.0          注意，CPU 开始紧张
  = 1.0              满载，CPU 刚好饱和
  > 1.0              过载，进程在排队
  > 3.0              严重过载，需要立即处理

  示例：
    4 核 CPU，load = 2.0
    → 比值 = 2.0 / 4 = 0.5 → 健康

    4 核 CPU，load = 8.0
    → 比值 = 8.0 / 4 = 2.0 → 严重过载

  趋势分析：
    load average: 0.52, 0.38, 0.29
    → 1min (0.52) > 5min (0.38) > 15min (0.29)
    → 负载在上升（问题在恶化）

    load average: 0.29, 0.38, 0.52
    → 1min (0.29) < 5min (0.38) < 15min (0.52)
    → 负载在下降（问题在缓解）
```

#### 3.4 Load Average 的常见误区

```
误区 1："Load Average 高 = CPU 不够"
  → 错！如果 wa（I/O wait）高，Load 也可能高但 CPU 很空闲
  → 此时瓶颈在磁盘/网络，不是 CPU
  → 结合 top 的 wa 列一起判断

误区 2："Load Average 是百分比"
  → 错！它是绝对值。4 核机器 load=4 才满载，不是 load=1

误区 3："15 分钟平均值比 1 分钟的更可靠"
  → 不一定！15 分钟的平均会"稀释"短时高峰
  → 对实时告警，1 分钟更有价值
  → 对趋势分析，15 分钟更平滑
  → 最佳实践：同时监控 1min 和 15min

误区 4："load = CPU 使用率"
  → 错！load 包含 D 状态进程，不只是 CPU
  → load 高可能是 I/O 问题，不是 CPU 问题
```

```bash
# 综合判断脚本
#!/bin/bash
cores=$(nproc)
read l1 l5 l15 _ < /proc/loadavg

echo "核心数: $cores"
echo "1min: $l1 ($(echo "scale=0; $l1 * 100 / $cores" | bc)%)"
echo "5min: $l5 ($(echo "scale=0; $l5 * 100 / $cores" | bc)%)"
echo "15min: $l15 ($(echo "scale=0; $l15 * 100 / $cores" | bc)%)"

# 结合 CPU 使用率判断
eval $(top -b -n 1 | awk '/^%Cpu/ {printf "us=%s sy=%s wa=%s id=%s", $2, $4, $10, $8}')
echo "CPU: us=$us% sy=$sy% wa=$wa% id=$id%"

if (( $(echo "$wa > 20" | bc -l) )); then
    echo "警告：I/O 等待高，瓶颈可能在磁盘"
fi
```

### 4. free — 内存使用

#### 4.1 输出解读

```bash
free -h
#                total     used     free   shared  buff/cache  available
# Mem:           16Gi     4.2Gi    1.8Gi    256Mi     10Gi      11Gi
# Swap:         2.0Gi       0B    2.0Gi
```

| 列名 | 含义 | 说明 |
|------|------|------|
| **total** | 总物理内存 | 系统安装的总内存 |
| **used** | 已使用 | total - free - buff/cache |
| **free** | 完全未使用的内存 | **不代表可用内存！** |
| **shared** | tmpfs/共享内存 | 通常是 /dev/shm |
| **buff/cache** | 缓冲区 + 页面缓存 | 内核用来加速磁盘 I/O |
| **available** | **真正可用的内存** | free + 可回收的 buff/cache |

```
关键认知：Linux 的内存管理哲学

  "空闲的内存就是浪费的内存"

  Linux 会把未使用的内存自动用作磁盘缓存（buff/cache），
  这不会减少应用程序可用内存。当应用程序需要内存时，
  内核会自动回收缓存。

  所以判断内存是否紧张，看 available 而不是 free！

  free 列很小是正常的，说明 Linux 在充分利用内存
  available 列很小才说明内存紧张

  内存紧张的标志：
    → available < 总内存的 10%
    → Swap 使用持续增长
    → dmesg 中有 OOM Killer 记录
    → kswapd 进程持续活跃（CPU 占用高）
```

#### 4.2 buff/cache 详解

```
Buffers（缓冲区）：
  → 块设备的读写缓冲
  → 缓存文件系统的元数据（inode、目录项）
  → 通常较小（几百 MB）

Cached（页面缓存）：
  → 缓存文件内容
  → 读文件时，数据先到 Cached，再复制给应用
  → 写文件时，数据先到 Cached，再异步写回磁盘
  → 通常较大（几 GB）

buff/cache 可以被回收：
  → 当应用需要内存时，内核会自动回收
  → 回收优先级：Cached > Buffers > SReclaimable
  → 回收过程对应用透明（除了性能暂时下降）
```

#### 4.3 内存回收机制

```
内存回收流程：

  1. 应用申请内存
     → 内核检查是否有空闲页面
     → 有 → 直接分配
     → 没有 → 进入回收流程

  2. 后台回收（kswapd）
     → 当空闲页面低于 low watermark 时触发
     → 异步回收页面缓存
     → 不影响应用性能

  3. 同步回收（direct reclaim）
     → 当空闲页面低于 min watermark 时触发
     → 应用同步等待内存回收
     → 严重影响性能！

  4. OOM Killer
     → 内存完全耗尽（physical + swap）
     → 选择一个进程杀死
     → 最后的手段

  水位线：
    ┌─────────────────┐
    │   free pages    │
    ├─────────────────┤ ← high watermark
    │   kswapd 活跃   │
    ├─────────────────┤ ← low watermark
    │   direct reclaim│
    ├─────────────────┤ ← min watermark
    │   OOM Killer    │
    └─────────────────┘
```

#### 4.4 内存泄漏排查

```bash
# 方法 1：持续监控内存趋势
watch -n 5 'free -h | grep Mem'

# 方法 2：记录特定进程的 RSS 变化
PID=$(pgrep myapp | head -1)
while true; do
    echo "$(date '+%H:%M:%S') $(ps -p $PID -o rss= --no-headers)" >> /tmp/mem_monitor.log
    sleep 60
done

# 方法 3：查看详细的内存使用
cat /proc/meminfo | grep -E "^(MemTotal|MemFree|MemAvailable|Buffers|Cached|Slab|SReclaimable|Dirty|Writeback)"

# 方法 4：查看哪些进程占内存最多
ps aux --sort=-%mem | head -10

# 方法 5：使用 pmap 查看进程内存分布
pmap -x $(pgrep java | head -1) | tail -5

# 方法 6：使用 smem 查看更准确的内存使用
sudo apt install smem
smem -rs pss | head -10
# PSS（Proportional Set Size）比 RSS 更准确

# 方法 7：查看内核 slab 缓存
slabtop -s c | head -20

# 方法 8：查看共享内存
ipcs -m
df -h /dev/shm
```

### 5. df/du — 磁盘空间

#### 5.1 df — 文件系统级别

```bash
# 人类可读格式
df -h

# 输出：
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/sda1       100G   65G   35G  66% /
# tmpfs           7.8G     0  7.8G   0% /dev/shm
# /dev/sdb1       500G  450G   50G  90% /data

# 只显示本地文件系统
df -h --local

# 显示文件系统类型
df -hT

# 按使用率排序
df -h | sort -t'%' -k1 -rn | head -5

# 显示 inode 使用情况
df -i

# 输出示例：
# Filesystem      Inodes  IUsed   IFree IUse% Mounted on
# /dev/sda1      6553600 123456 6430144    2% /
```

#### 5.2 du — 目录级别

```bash
# 查看当前目录下每个子目录的大小
du -sh *

# 查看指定目录的深度为 1 的子目录大小
du -sh /var/*/

# 找出占用最大的 10 个目录
du -ah / 2>/dev/null | sort -rh | head -10

# 更高效的方法
sudo apt install ncdu
ncdu /     # 交互式浏览

# 找出最近修改的大文件
find / -type f -size +100M -mtime -7 -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh

# 找出最大的文件
find / -type f -printf '%s %p\n' 2>/dev/null | sort -rn | head -20
```

#### 5.3 已删除但未释放的文件

```bash
# 场景：df 显示磁盘满了，但 du 统计不出来
# 原因：文件被删除但进程还在持有文件句柄

# 找出已删除但未释放的文件
sudo lsof +L1 | grep deleted
# 或
sudo lsof | grep "(deleted)"

# 输出示例：
# nginx   1234  root  5w  REG  8,1  5368709120  0 /var/log/nginx/access.log (deleted)
# → nginx 进程持有已删除的 5GB 日志文件

# 修复方法：
# 方法 1：重启持有文件的进程
sudo systemctl restart nginx

# 方法 2：截断文件（不重启进程）
sudo truncate -s 0 /proc/<PID>/fd/<FD>
# 例如：
sudo truncate -s 0 /proc/1234/fd/5

# 方法 3：让进程重新打开日志
# Nginx：kill -USR1 $(cat /var/run/nginx.pid)
# 其他：配置 logrotate 使用 copytruncate
```

#### 5.4 Inode 耗尽

```bash
# 磁盘空间够但无法创建文件？可能是 inode 用完了！
df -i

# 输出示例：
# Filesystem      Inodes  IUsed   IFree IUse% Mounted on
# /dev/sda1      6553600 6553600      0  100% /

# 即使 df -h 显示还有 35G 空间，inode 用完也无法创建新文件！

# 找出哪个目录有最多文件
sudo find / -xdev -printf '%h\n' 2>/dev/null | sort | uniq -c | sort -rn | head -10

# 常见原因：
# 1. 大量小文件（如 session 文件、缓存文件）
# 2. mail 队列堆积（/var/spool/mail）
# 3. 日志文件未轮转，产生大量分割文件
# 4. 容器镜像层过多

# 清理大量小文件（比 rm 更快）
find /tmp/sessions -type f -delete
# 或
find /tmp/sessions -type f -print0 | xargs -0 rm -f
```

### 6. vmstat — 虚拟内存统计

#### 6.1 输出解读

```bash
vmstat 1 5
# 每 1 秒采样一次，共 5 次

# procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
#  r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
#  1  0      0 1843200  51200 10240000    0    0    12    35  120  350  8  2 89  1  0
#  0  0      0 1842000  51200 10241000    0    0     0     0  115  340  5  1 93  1  0
```

**procs 列：**

| 列 | 含义 | 正常值 | 异常值 | 说明 |
|----|------|--------|--------|------|
| **r** | 运行队列中的进程数 | 0-核心数 | > 核心数 | CPU 瓶颈指标 |
| **b** | 不可中断睡眠的进程数 | 0 | > 0 | I/O 瓶颈指标 |

**memory 列：**

| 列 | 含义 | 说明 |
|----|------|------|
| swpd | 使用的 swap（KB） | 持续增长 → 内存不足 |
| free | 空闲内存（KB） | — |
| buff | 缓冲区（KB） | — |
| cache | 页面缓存（KB） | — |

**swap 列 — 最关键的内存指标：**

| 列 | 含义 | 正常值 | 异常值 | 说明 |
|----|------|--------|--------|------|
| **si** | swap in（从磁盘读入，KB/s） | 0 | > 0 且持续 | 严重内存不足 |
| **so** | swap out（写入磁盘，KB/s） | 0 | > 0 且持续 | 严重内存不足 |

```
si/so 的含义：
  si > 0：内核正在把 swap 中的数据读回物理内存
    → 说明之前有数据被换出，现在又需要了
    → 性能影响：磁盘读取比内存慢 10000 倍

  so > 0：内核正在把物理内存中的数据写入 swap
    → 说明物理内存不足，正在腾出空间
    → 性能影响：大量 swap out 会导致系统极度卡顿

  si/so 持续 > 0 = 严重内存不足
  si/so 偶尔 > 0 = 内存紧张但还可以
  si/so = 0 = 内存充足
```

**io 列：**

| 列 | 含义 | 说明 |
|----|------|------|
| bi | 块设备读入（块/秒） | — |
| bo | 块设备写出（块/秒） | — |

**system 列：**

| 列 | 含义 | 正常值 | 异常值 | 说明 |
|----|------|--------|--------|------|
| **in** | 中断数/秒 | 几百到几千 | > 100000 | 硬件或驱动问题 |
| **cs** | 上下文切换/秒 | 5000-30000 | > 100000 | 进程/线程过多 |

```
上下文切换（context switch）过多的原因：
  → 大量线程/进程竞争 CPU
  → 锁竞争激烈
  → 网络包处理压力大（软中断）

排查方法：
  pidstat -w 1 5    # 按进程查看上下文切换
  perf stat -e context-switches -p <PID> sleep 5
```

**cpu 列：**

| 列 | 含义 | 正常值 | 异常值 | 说明 |
|----|------|--------|--------|------|
| **us** | 用户空间 | < 70% | > 80% | 应用代码 CPU 密集 |
| **sy** | 内核空间 | < 20% | > 30% | 系统调用过多 |
| **id** | 空闲 | > 30% | < 10% | CPU 紧张 |
| **wa** | I/O 等待 | < 5% | > 20% | 磁盘瓶颈 |
| **st** | 被偷（虚拟化） | 0% | > 5% | 宿主机过载 |

#### 6.2 vmstat 排障速查表

```
症状                    可能原因              排查方法
──────────────────────  ──────────────────    ──────────────────
r 持续 > CPU 核心数     CPU 瓶颈              top → ps aux --sort=-%cpu
b > 0                   I/O 瓶颈              iostat -x → iotop
si/so 持续 > 0          内存不足              free -h → ps aux --sort=-%mem
wa > 20%                磁盘瓶颈              iostat -x → dmesg
cs > 100000/s           上下文切换过多         pidstat -w → perf
sy > 30%                系统调用过多           strace -c → perf top
st > 5%                 虚拟化争抢            联系云服务商
```

### 7. sar — 系统活动报告

#### 7.1 安装与配置

```bash
# 安装 sysstat 包（包含 sar、iostat、mpstat、pidstat 等）
sudo apt install sysstat

# 启用数据收集（默认关闭）
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat
sudo systemctl restart sysstat
sudo systemctl enable sysstat

# 数据收集配置
cat /etc/cron.d/sysstat
# 默认每 10 分钟收集一次
# */10 * * * * root command -v debian-sa1 > /dev/null && debian-sa1 1 1

# 修改收集频率（每 1 分钟）
# */1 * * * * root command -v debian-sa1 > /dev/null && debian-sa1 1 1

# 数据存储位置
ls /var/log/sysstat/
# sa01, sa02, ... sa31  （按日期命名）
```

#### 7.2 查看历史数据

```bash
# 今天的 CPU 使用率
sar

# 指定时间范围
sar -s 10:00:00 -e 12:00:00

# 昨天的数据
sar -f /var/log/sysstat/sa$(date -d yesterday +%d)

# 前天的数据
sar -f /var/log/sysstat/sa$(date -d "2 days ago" +%d)

# 指定日期
sar -f /var/log/sysstat/sa01  # 1 号的数据
```

#### 7.3 各种监控模式

```bash
# === CPU 使用率 ===
sar -u 1 5
# %user: 用户空间 CPU
# %system: 内核空间 CPU
# %iowait: I/O 等待
# %idle: 空闲

# === 内存使用 ===
sar -r 1 5
# kbmemfree: 空闲内存
# kbavail: 可用内存
# %memused: 内存使用率
# kbbuffers/kbcached: 缓存

# === Swap 使用 ===
sar -S 1 5
# kbswpfree/kbswpused: Swap 使用
# kbswpin/kbswpout: Swap I/O 速率

# === I/O 统计 ===
sar -b 1 5
# tps: 每秒传输次数（IOPS）
# rtps/wtps: 读/写 IOPS
# bread/s/bwrtn/s: 读/写块数

# === 网络接口 ===
sar -n DEV 1 5
# rxpck/s: 每秒接收包数
# txpck/s: 每秒发送包数
# rxkB/s: 每秒接收 KB
# txkB/s: 每秒发送 KB
# rxdrop/s: 丢弃的接收包

# === 网络错误 ===
sar -n EDEV 1 5

# === TCP 连接 ===
sar -n TCP 1 5
# active/s: 主动连接
# passive/s: 被动连接

# === 上下文切换 ===
sar -w 1 5
# cswch/s: 上下文切换次数

# === 负载 ===
sar -q 1 5
# runq-sz: 运行队列长度
# plist-sz: 进程总数
# ldavg-1/5/15: 负载平均值

# === 磁盘统计 ===
sar -d 1 5
# 每个磁盘的 IOPS、吞吐量、利用率

# === 所有统计 ===
sar -A 1 5
# 输出所有可用的统计信息
```

#### 7.4 事后排障

```bash
# 场景：昨天下午 3 点系统很慢，发生了什么？

YESTERDAY=$(date -d yesterday +%d)

# 查看昨天 14:00-16:00 的 CPU
sar -u -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 查看内存
sar -r -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 查看 I/O
sar -b -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 查看网络
sar -n DEV -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 查看负载
sar -q -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 查看磁盘
sar -d -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 生成图表（需要安装 gnuplot 或 kSar）
# sar -A -f /var/log/sysstat/sa$YESTERDAY > /tmp/sar_data.txt
# 用 kSar 打开生成图表
```

### 8. iostat — 磁盘 I/O 统计

#### 8.1 输出解读

```bash
# 安装（sysstat 包含 iostat）
sudo apt install sysstat

# 显示扩展信息，每 1 秒采样，共 3 次
iostat -x 1 3

# 输出：
# Device    r/s     w/s     rkB/s   wkB/s   rrqm/s  wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz  rareq-sz wareq-sz  svctm  %util
# sda      12.50   45.20   256.00  1024.00  0.50   2.10   3.85   4.43   2.10    5.30   0.25    20.48    22.65   0.80   4.62
```

**核心指标详解：**

| 列 | 含义 | 说明 |
|----|------|------|
| **r/s** | 每秒读次数（读 IOPS） | — |
| **w/s** | 每秒写次数（写 IOPS） | — |
| **rkB/s** | 每秒读吞吐量 | — |
| **wkB/s** | 每秒写吞吐量 | — |
| **rrqm/s** | 每秒合并的读请求数 | 合并多 → 顺序 I/O |
| **wrqm/s** | 每秒合并的写请求数 | 合并多 → 顺序 I/O |
| **r_await** | 平均读响应时间（ms） | **< 1ms 正常，> 10ms 有问题** |
| **w_await** | 平均写响应时间（ms） | **< 1ms 正常，> 10ms 有问题** |
| **aqu-sz** | 平均队列长度 | **> 1 表示有请求在排队** |
| **svctm** | 平均服务时间（ms） | 已废弃，不准确 |
| **%util** | 设备利用率 | **接近 100% 表示饱和** |

#### 8.2 %util vs await vs svctm 的区别

```
%util（利用率）：
  → 设备繁忙时间的百分比
  → 计算方式：(设备繁忙时间 / 总时间) × 100%
  → 对于传统磁盘（HDD）：接近 100% 确实表示饱和
  → 对于 SSD/NVMe：可能不到 100% 就已经饱和了
    （因为 SSD 支持并行 I/O，%util 计算方式有局限）

await（响应时间）：
  → 从请求发出到完成的总时间
  → 包含排队时间 + 服务时间
  → 最直接的性能指标

  SSD 正常值：< 1ms
  HDD 正常值：< 10ms
  异常值：> 50ms（严重性能问题）

svctm（服务时间）：
  → 已废弃！man iostat 明确说明不准确
  → 不要使用这个指标

最佳判断指标：
  1. await（响应时间）— 最直观
  2. aqu-sz（队列长度）— 反映饱和度
  3. %util（利用率）— 辅助判断
```

#### 8.3 I/O 瓶颈判断

```bash
# 判断标准：
# 1. r_await 或 w_await > 10ms → 响应慢
# 2. aqu-sz > 1 → 有请求在排队
# 3. %util 接近 100% → 磁盘饱和
# 4. svctm（已废弃）远小于 await → 等待时间长

# 实时监控磁盘 I/O
watch -n 1 'iostat -x 1 1 | grep -E "^Device|^sda"'

# 找出哪个进程在做大量 I/O
sudo iotop -o
# -o: 只显示正在做 I/O 的进程
# -d 1: 每 1 秒刷新
# -P: 显示进程而非线程

# 按设备查看 I/O
iostat -x -d sda sdb 1 5
```

### 9. Brendan Gregg 的 60 秒性能排查清单

```bash
# Brendan Gregg 推荐的前 60 秒排查步骤：

# 1. 系统概览（10 秒）
uptime                          # load average
dmesg -T | tail -20             # 内核消息（硬件错误、OOM）

# 2. CPU 和内存（10 秒）
vmstat 1 5                      # r/b/si/so/us/sy/wa
mpstat -P ALL 1 5               # 每个 CPU 核心的使用率

# 3. 进程（10 秒）
pidstat 1 5                     # 按进程的 CPU 使用
top -b -n 1 | head -20          # 进程概览

# 4. 磁盘（10 秒）
iostat -xz 1 5                  # 磁盘 I/O 统计

# 5. 网络（10 秒）
sar -n DEV 1 5                  # 网络接口统计
sar -n TCP 1 5                  # TCP 连接统计

# 6. 内存（10 秒）
free -h                         # 内存使用
cat /proc/meminfo | head -20    # 详细内存信息
```

---

## 🏗️ SRE 实战案例

### 案例 1：服务器响应变慢完整排查链路

```bash
# 接到告警：服务响应时间从 50ms 飙升到 2s

# ===== 第 1 步：快速概览（30 秒内完成） =====

# 1a. 看负载和运行时间
uptime
# 如果 load 远高于 CPU 核心数 → 有过载

# 1b. 看内存
free -h
# 如果 available 很少 → 内存压力

# 1c. 看磁盘空间
df -h
# 如果 Use% > 90% → 磁盘空间不足

# 1d. 看 CPU 分布
vmstat 1 5
# 关注 r/b/si/us/wa

# ===== 第 2 步：定位瓶颈（1-2 分钟） =====

# 如果 wa 高（I/O 等待）
iostat -x 1 3
# 看 %util 和 await

# 如果 us 高（用户 CPU）
ps aux --sort=-%cpu | head -10

# 如果 sy 高（内核 CPU）
vmstat 1 5
# 看 cs（上下文切换）是否异常

# 如果 si/so > 0（Swap）
ps aux --sort=-%mem | head -10
# 检查是否有内存泄漏

# ===== 第 3 步：深挖根因 =====

# 如果是 I/O 问题
sudo iotop -o                    # 谁在做 I/O？
sudo lsof +D /data               # 谁在访问这个目录？

# 如果是网络问题
sar -n DEV 1 5                   # 网络流量是否异常？
ss -s                            # 连接统计
ss -tnp | wc -l                  # TCP 连接数

# 如果是 CPU 问题
perf top                         # 实时函数级 CPU 采样
pidstat 1 5                      # 按进程统计 CPU

# ===== 第 4 步：查看历史趋势 =====

# 问题是突然出现的还是渐进的？
sar -u -s 08:00 -e $(date +%H:%M)
sar -r -s 08:00 -e $(date +%H:%M)
sar -b -s 08:00 -e $(date +%H:%M)
```

### 案例 2：内存泄漏排查

```bash
# 场景：服务器内存使用率持续上升，3 天从 40% 升到 90%

# 第 1 步：确认内存使用情况
free -h
cat /proc/meminfo | grep -E "^(MemTotal|MemFree|MemAvailable|Cached|Slab|SReclaimable)"

# 第 2 步：找出内存使用最多的进程
ps aux --sort=-%mem | head -10

# 第 3 步：监控可疑进程的内存变化
PID=$(pgrep myapp | head -1)
while true; do
    echo "$(date '+%H:%M:%S') RSS=$(ps -p $PID -o rss= --no-headers)KB"
    sleep 60
done | tee /tmp/mem_leak.log

# 第 4 步：查看进程的详细内存分布
pmap -x $PID | tail -10
# 或
cat /proc/$PID/smaps_rollup

# 第 5 步：使用 smem 查看更准确的内存使用
sudo smem -rs pss | head -10

# 第 6 步：检查是否有已删除但未释放的文件
sudo lsof +L1 | grep deleted

# 第 7 步：检查内核 slab 缓存
slabtop -s c | head -10
# 如果 slab 很大，可能是内核内存泄漏

# 第 8 步：检查共享内存
ipcs -m
df -h /dev/shm

# 第 9 步：检查 OOM 日志
dmesg -T | grep -i oom
journalctl -k | grep -i oom
```

### 案例 3：磁盘 I/O 瓶颈定位

```bash
# 场景：数据库查询变慢，iowait 持续 > 30%

# 第 1 步：确认 I/O 问题
vmstat 1 5
# 关注 wa、b、si/so

# 第 2 步：查看磁盘 I/O 详情
iostat -x 1 5
# 关注 %util、await、aqu-sz

# 第 3 步：找出 I/O 最多的进程
sudo iotop -o -d 1

# 第 4 步：检查磁盘健康
sudo smartctl -a /dev/sda
sudo dmesg | tail -20 | grep -i "error\|I/O\|fail"

# 第 5 步：检查文件系统
sudo tune2fs -l /dev/sda1 | grep "Mount count\|Check interval"

# 第 6 步：分析 I/O 模式（顺序 vs 随机）
sudo blktrace -d /dev/sda -o - | blkparse -i -
# 或使用 iostat 的 rrqm/wrqm 判断
# 高合并率 → 顺序 I/O
# 低合并率 → 随机 I/O

# 第 7 步：优化方案
# 如果是随机 I/O：
#   → 增加内存（更多缓存）
#   → 使用 SSD
#   → 优化索引（减少全表扫描）
# 如果是顺序 I/O：
#   → 增加磁盘带宽（RAID、多磁盘）
#   → 压缩数据
```

### 案例 4：容量规划报告

```bash
#!/bin/bash
# capacity_report.sh — 生成容量规划报告

echo "=========================================="
echo "  服务器容量规划报告"
echo "  主机: $(hostname)"
echo "  时间: $(date)"
echo "=========================================="

echo ""
echo "--- 硬件配置 ---"
echo "CPU: $(nproc) 核心 ($(lscpu | grep 'Model name' | cut -d: -f2 | xargs))"
echo "内存: $(free -h | awk '/Mem:/ {print $2}')"
echo "磁盘:"
df -h --local | grep -v "^Filesystem"

echo ""
echo "--- 当前使用率 ---"
cpu_load=$(cat /proc/loadavg | awk '{print $1}')
cpu_cores=$(nproc)
echo "CPU 负载: $cpu_load / $cpu_cores 核心"
echo "内存: $(free -h | awk '/Mem:/ {printf "已用 %s / 总共 %s (可用 %s)", $3, $2, $7}')"

echo ""
echo "--- 30 天趋势（基于 sar 数据） ---"
echo "平均 CPU 使用率:"
sar -u | awk 'NR>3 && $NF != "idle" {sum+=$NF; count++} END {printf "  %.1f%%\n", (100 - sum/count)}'

echo "平均内存使用率:"
sar -r | awk 'NR>3 && /Average/ {printf "  %.1f%%\n", $5}'

echo ""
echo "--- 容量预警 ---"
# CPU
cpu_pct=$(echo "$cpu_load * 100 / $cpu_cores" | bc)
if (( cpu_pct > 80 )); then
    echo "WARNING: CPU 使用率 ${cpu_pct}%，建议扩容"
else
    echo "OK: CPU 使用率正常"
fi

# 磁盘
max_disk=$(df -h --local | awk 'NR>1 {gsub(/%/,"",$5); if($5+0 > max) max=$5+0} END {print max}')
if (( max_disk > 85 )); then
    echo "WARNING: 磁盘最大使用率 ${max_disk}%，建议扩容或清理"
else
    echo "OK: 磁盘使用率正常"
fi

# 内存
avail_pct=$(free | awk '/Mem:/ {printf "%.0f", ($7/$2)*100}')
if (( avail_pct < 20 )); then
    echo "WARNING: 可用内存仅 ${avail_pct}%，建议扩容"
else
    echo "OK: 可用内存 ${avail_pct}%"
fi
```

---

## 💻 实战练习

### 练习 1：解读 free 输出

某服务器 `free -h` 输出如下，判断内存是否紧张：

```
              total   used   free   shared  buff/cache  available
Mem:           32Gi   28Gi   512Mi    128Mi      3.4Gi      12Gi
Swap:         8.0Gi   2.0Gi   6.0Gi
```

<details>
<summary>答案</summary>

**内存不紧张。**

关键看 **available = 12Gi**（不是 free = 512Mi）。
free 列很小是正常的，Linux 会把空闲内存用作缓存。

Swap 使用了 2.0Gi，这可能表明过去有过内存压力，但只要不是持续增长就没问题。

建议关注：
- available 是否持续下降
- Swap 使用是否持续增长
- 是否有进程的内存使用在异常增长
</details>

### 练习 2：iostat 排障

`iostat -x 1` 显示 `/dev/sda` 的 `%util = 98%`，`r_await = 150ms`。这是什么问题？如何排查？

<details>
<summary>答案</summary>

**分析**：
- %util = 98% → 磁盘几乎一直在工作，接近饱和
- r_await = 150ms → 每次读操作平均需要 150 毫秒（正常应 < 10ms）
- **结论**：磁盘 I/O 严重瓶颈

**排查步骤**：
```bash
# 1. 找出谁在做大量 I/O
sudo iotop -o

# 2. 检查磁盘健康
sudo smartctl -a /dev/sda
sudo dmesg | tail -20 | grep -i "error\|I/O"

# 3. 检查是否有大量随机读
iostat -x 1 5
# 看 rrqm（读合并率），低合并率 = 随机 I/O

# 4. 检查文件系统
sudo tune2fs -l /dev/sda1 | grep "Mount count\|Check interval"
```
</details>

### 练习 3：使用 sar 回溯问题

昨天下午 2-4 点系统很慢，请用 sar 查看当时的 CPU、内存、I/O 情况。

<details>
<summary>答案</summary>

```bash
YESTERDAY=$(date -d yesterday +%d)

# CPU 使用率
sar -u -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 内存
sar -r -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# I/O
sar -b -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 负载
sar -q -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 网络
sar -n DEV -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00

# 磁盘
sar -d -f /var/log/sysstat/sa$YESTERDAY -s 14:00 -e 16:00
```
</details>

### 练习 4：综合性能分析

使用以下命令组合，分析当前系统的性能瓶颈：

```bash
# 1. 系统概览
uptime
free -h
df -h

# 2. CPU 和内存
vmstat 1 5

# 3. 磁盘 I/O
iostat -x 1 3

# 4. 进程
top -b -n 1 | head -20

# 5. 网络
sar -n DEV 1 3
```

---

## 🎯 面试题精选

### 面试题 1：load average 高如何排查？

**参考答案：**

1. 先看 CPU 使用率（top/vmstat）：
   - 如果 us 高 → CPU 密集型，查 top 进程列表
   - 如果 wa 高 → I/O 瓶颈，查 iostat/iotop
   - 如果 id 高但 load 高 → D 状态进程多

2. 查看 D 状态进程：
   ```bash
   ps aux | awk '$8 ~ /^D/'
   ```

3. 检查磁盘：
   ```bash
   iostat -x 1 5
   sudo smartctl -a /dev/sda
   ```

4. 检查 NFS（如果有挂载）：
   ```bash
   mount | grep nfs
   dmesg | grep -i nfs
   ```

5. 检查内核日志：
   ```bash
   dmesg -T | tail -30
   ```

### 面试题 2：如何判断内存是否不足？

**参考答案：**

1. 看 free -h 的 available 列（不是 free 列）：available < 10% 总内存 → 内存紧张

2. 看 Swap 使用：持续增长 → 内存不足

3. 看 vmstat 的 si/so：持续 > 0 → 正在使用 Swap，性能严重下降

4. 看 dmesg：有 OOM Killer 记录 → 内存已耗尽

5. 看 kswapd 活跃度：`ps aux | grep kswapd`，持续高 CPU → 内核在积极回收内存

### 面试题 3：iowait 高怎么办？

**参考答案：**

iowait 高说明 CPU 在等待 I/O，瓶颈在磁盘。

排查步骤：
1. `iostat -x 1 5` → 看 %util 和 await
2. `sudo iotop -o` → 找出 I/O 最多的进程
3. `sudo smartctl -a /dev/sda` → 检查磁盘健康
4. `dmesg | tail -20` → 检查硬件错误

优化方案：
1. 增加内存（更多页面缓存）
2. 使用 SSD 替代 HDD
3. 优化应用（减少不必要的 I/O、使用缓存）
4. 使用 RAID 提高 I/O 性能
5. 调整 I/O 调度器

### 面试题 4：buff/cache 和 available 有什么区别？

**参考答案：**

buff/cache 是内核用作缓冲区和页面缓存的内存，包括 Buffers（块设备缓冲）和 Cached（文件内容缓存）。

available 是应用程序真正可用的内存，等于 free + 可回收的 buff/cache。当应用需要内存时，内核会自动回收缓存。

判断内存是否紧张应该看 available 而不是 free。free 列很小是正常的，说明 Linux 在充分利用内存做缓存。

### 面试题 5：如何用 sar 做事后排障？

**参考答案：**

sar 是事后排障的利器，因为它会自动记录历史数据。

```bash
# 查看昨天某个时间段的 CPU
sar -u -f /var/log/sysstat/sa$(date -d yesterday +%d) -s 14:00 -e 16:00

# 查看内存
sar -r -f /var/log/sysstat/saXX -s 14:00 -e 16:00

# 查看 I/O
sar -b -f /var/log/sysstat/saXX -s 14:00 -e 16:00

# 查看网络
sar -n DEV -f /var/log/sysstat/saXX -s 14:00 -e 16:00
```

需要先启用 sysstat 数据收集（默认可能关闭）。

### 面试题 6：已删除但未释放的文件如何处理？

**参考答案：**

文件被删除但进程还在持有文件句柄时，磁盘空间不会释放。

排查：
```bash
sudo lsof +L1 | grep deleted
```

修复：
```bash
# 方法 1：重启持有文件的进程
sudo systemctl restart <service>

# 方法 2：截断文件（不重启进程）
sudo truncate -s 0 /proc/<PID>/fd/<FD>
```

### 面试题 7：USE 方法是什么？

**参考答案：**

USE（Utilization、Saturation、Errors）是 Brendan Gregg 提出的性能分析方法论：
- U（Utilization）：资源繁忙的时间百分比
- S（Saturation）：资源过载的程度（排队）
- E（Errors）：资源发生的错误次数

对每种资源（CPU、内存、磁盘、网络）都检查 U/S/E，可以系统性地发现性能瓶颈。

排查顺序：Errors → Saturation → Utilization（先查最严重的）。

---

## 📚 深入阅读

- [Brendan Gregg — USE Method](http://www.brendangregg.com/usemethod.html) — 性能分析方法论
- [Brendan Gregg — Linux Performance Tools](http://www.brendangregg.com/blog/2015-06-17/linux-perf-tools.html) — 60 秒性能排查流程图
- [Brendan Gregg — Linux Performance](http://www.brendangregg.com/linuxperf.html) — Linux 性能分析权威指南
- `man vmstat`, `man sar`, `man iostat` — 官方手册
- [The Art of Capacity Planning](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43505.pdf) — Google 的容量规划论文
- [Systems Performance](https://www.brendangregg.com/systems-performance.html) — Brendan Gregg 的性能分析书籍

---

## ✅ 自检清单

- [ ] 理解 Load Average 包含 D 状态进程，不只是 CPU 负载
- [ ] 能解释 free 输出中 buff/cache 和 available 的区别
- [ ] 理解 Linux 内存回收机制（kswapd、direct reclaim、OOM Killer）
- [ ] 能使用 df/du 分析磁盘空间，处理 inode 耗尽和已删除未释放文件
- [ ] 能解读 vmstat 每列含义，重点关注 si/so（swap）和 wa（iowait）
- [ ] 能使用 sar 回溯历史性能数据
- [ ] 能解读 iostat 的 %util、await、aqu-sz 指标
- [ ] 掌握 USE 方法论
- [ ] 能独立完成服务器响应变慢的完整排查链路
- [ ] 能编写容量规划报告脚本
