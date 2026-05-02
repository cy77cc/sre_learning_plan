# Day 11: 系统监控命令 — uptime/free/df/vmstat/sar/iostat

> 📅 日期：2026-04-25
> 📖 学习主题：系统监控命令 — uptime/free/df/vmstat/sar/iostat
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 11 的学习后，你应该掌握：
- 深入理解 Load Average 的含义（不仅是"CPU 负载"，还包括 D 状态进程）
- 使用 free 准确解读内存使用（理解 buff/cache vs available 的区别）
- 使用 df/du 分析磁盘空间，理解 inode 耗尽问题
- 使用 vmstat 分析系统整体性能瓶颈
- 使用 sar 查看历史性能数据（事前监控，事后回溯）
- 使用 iostat 分析磁盘 I/O 瓶颈

---

## 📖 详细知识点

### 1. uptime — 系统负载

#### 1.1 输出解读

```bash
uptime
# 输出：14:30:25 up 30 days, 2:15,  2 users,  load average: 0.52, 0.38, 0.29
```

| 字段 | 含义 |
|------|------|
| 14:30:25 | 当前时间 |
| up 30 days, 2:15 | 系统运行时间（30 天 2 小时 15 分钟） |
| 2 users | 当前登录的终端用户数 |
| **load average** | 1/5/15 分钟平均负载 |

#### 1.2 Load Average 的深层含义

```
load average = 处于以下状态的进程数（在采样周期内的平均）：
  R（Running/Runnable）→ 正在使用或等待使用 CPU
  D（Uninterruptible Sleep）→ 等待 I/O 完成（不可中断）

注意：Load Average 不包含 S（可中断睡眠）状态的进程！
这就是为什么等待网络请求的进程不计入负载。
```

**解读指南：**

| 情况 | 含义 |
|------|------|
| load < CPU 核心数 | CPU 有空闲，系统健康 |
| load ≈ CPU 核心数 | CPU 刚好满载 |
| load > CPU 核心数 | 进程在排队，有性能瓶颈 |
| 1min > 5min > 15min | 负载在上升（问题在恶化） |
| 1min < 5min < 15min | 负载在下降（问题在缓解） |

```bash
# 查看 CPU 核心数
nproc
# 或
grep -c ^processor /proc/cpuinfo
# 或
lscpu | grep "^CPU(s):"

# 结合判断
echo "核心数: $(nproc), 当前负载: $(cat /proc/loadavg | awk '{print $1}')"
# 输出示例：核心数: 4, 当前负载: 3.85

# 更好的方式：用负载/核心数的比值
awk '{printf "核心数: %d\n1min: %.2f (%.0f%%)\n5min: %.2f (%.0f%%)\n15min: %.2f (%.0f%%)\n", \
  NR==FNR{cores=$0; next} \
  {printf "  %s: %.2f (%.0f%%)\n", (NR==1?"1min":NR==2?"5min":"15min"), \
   $NR, $NR/cores*100}' \
  <(nproc) <(cat /proc/loadavg)
```

#### 1.3 Load Average 的常见误区

```
误区 1："Load Average 高 = CPU 不够"
→ 错！如果 wa（I/O wait）高，Load 也可能高但 CPU 很空闲
→ 此时瓶颈在磁盘/网络，不是 CPU

误区 2："Load Average 是百分比"
→ 错！它是绝对值。4 核机器 load=4 才满载，不是 load=1

误区 3："15 分钟平均值比 1 分钟的更可靠"
→ 不一定！15 分钟的平均会"稀释"短时高峰
→ 对实时告警，1 分钟更有价值
→ 对趋势分析，15 分钟更平滑
```

### 2. free — 内存使用

#### 2.1 输出解读

```bash
free -h
#                total     used     free   shared  buff/cache  available
# Mem:           16Gi     4.2Gi    1.8Gi    256Mi     10Gi      11Gi
# Swap:         2.0Gi       0B    2.0Gi
```

| 列名 | 含义 | 说明 |
|------|------|------|
| **total** | 总物理内存 | — |
| **used** | 已使用 | total - free - buff/cache |
| **free** | 完全未使用的内存 | **不代表可用内存！** |
| **shared** | tmpfs/共享内存 | 通常是 /dev/shm |
| **buff/cache** | 缓冲区+页面缓存 | 内核用来加速磁盘 I/O 的 |
| **available** | **真正可用的内存** | free + 可回收的 buff/cache |

**关键认知：Linux 的内存管理哲学**
```
"空闲的内存就是浪费的内存"

Linux 会把未使用的内存自动用作磁盘缓存（buff/cache），
这不会减少应用程序可用内存。当应用程序需要内存时，
内核会自动回收缓存。

所以判断内存是否紧张，看 available 而不是 free！
```

#### 2.2 内存不足排查

```bash
# 查看详细的内存使用
cat /proc/meminfo | head -20

# 关键字段：
# MemTotal:     16384000 kB
# MemFree:       1843200 kB   ← 完全空闲
# MemAvailable: 11264000 kB  ← 真正可用
# Buffers:         51200 kB
# Cached:       10240000 kB   ← 页面缓存
# SwapTotal:     2097152 kB
# SwapFree:      2097152 kB
# Dirty:            1024 kB   ← 等待写回磁盘的数据
# Slab:           512000 kB   ← 内核数据结构缓存
# SReclaimable:   256000 kB   ← 可回收的 slab

# 查看哪些进程占内存最多
ps aux --sort=-%mem | head -10

# 查看某个进程的详细内存
cat /proc/$(pgrep java | head -1)/smaps_rollup

# 查看 slab 使用（内核内存）
slabtop -s c | head -20

# 查看共享内存
ipcs -m
df -h /dev/shm
```

#### 2.3 内存泄漏排查

```bash
# 方法 1：持续监控内存趋势
watch -n 5 'free -h | grep Mem'

# 方法 2：记录特定进程的 RSS 变化
while true; do
    date '+%H:%M:%S'
    ps -p $(pgrep myapp | head -1) -o rss --no-headers
    sleep 60
done | tee /tmp/mem_monitor.log

# 方法 3：查看内核是否杀了进程（OOM）
sudo dmesg | grep -i "oom\|killed"

# 方法 4：分析 /proc 中的内存分布
cat /proc/meminfo | grep -E "^(MemTotal|MemFree|MemAvailable|Buffers|Cached|Slab|SReclaimable|VmallocTotal)"
```

### 3. df/du — 磁盘空间

#### 3.1 df — 文件系统级别

```bash
# 人类可读格式
df -h

# 输出：
# Filesystem      Size  Used Avail Use% Mounted on
# /dev/sda1       100G   65G   35G  66% /
# tmpfs           7.8G     0  7.8G   0% /dev/shm
# /dev/sdb1       500G  450G   50G  90% /data

# 只显示本地文件系统（排除 tmpfs, devtmpfs 等虚拟文件系统）
df -h --local

# 显示文件系统类型
df -hT

# 按使用率排序
df -h | sort -t'%' -k1 -rn | head -5
```

#### 3.2 du — 目录级别

```bash
# 查看当前目录下每个子目录的大小
du -sh *

# 查看指定目录的深度为 1 的子目录大小
du -sh /var/*/

# 找出占用最大的 10 个目录
du -ah / 2>/dev/null | sort -rh | head -10

# 更高效的方法（使用 ncdu，需要安装）
sudo apt install ncdu
ncdu /     # 交互式浏览

# 对比：找出最近修改的大文件
find / -type f -size +100M -mtime -7 -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh
```

#### 3.3 Inode 耗尽

```bash
# 磁盘空间够但无法创建文件？可能是 inode 用完了！
df -i

# 输出示例：
# Filesystem      Inodes  IUsed   IFree IUse% Mounted on
# /dev/sda1      6553600 6553600      0  100% /

# 即使 df -h 显示还有 35G 空间，inode 用完也无法创建新文件！

# 找出哪个目录有最多文件
for d in /*; do
    count=$(find "$d" -maxdepth 1 -type f 2>/dev/null | wc -l)
    echo "$count $d"
done | sort -rn | head -10

# 更高效的命令（需要 root）
sudo find / -xdev -printf '%h\n' | sort | uniq -c | sort -rn | head -10

# 常见场景：
# 1. 大量小文件（如 session 文件、缓存文件）
# 2. mail 队列堆积（/var/spool/mail）
# 3. 日志文件未轮转，产生大量分割文件

# 清理大量小文件（比 rm 更快）
find /tmp/sessions -type f -delete
# 或
find /tmp/sessions -type f -print0 | xargs -0 rm -f
```

### 4. vmstat — 虚拟内存统计

#### 4.1 输出解读

```bash
vmstat 1 5
# 每 1 秒采样一次，共 5 次

# procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
#  r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
#  1  0      0 1843200  51200 10240000    0    0    12    35  120  350  8  2 89  1  0
#  0  0      0 1842000  51200 10241000    0    0     0     0  115  340  5  1 93  1  0
```

| 列 | 含义 | 说明 |
|----|------|------|
| **procs** | | |
| r | 运行队列中的进程数 | r > CPU 核心数 → CPU 瓶颈 |
| b | 不可中断睡眠的进程数 | b > 0 → I/O 瓶颈 |
| **memory** | | |
| swpd | 使用的 swap | 持续增长 → 内存不足 |
| free | 空闲内存 | — |
| buff | 缓冲区 | — |
| cache | 页面缓存 | — |
| **swap** | | |
| si | swap in（从磁盘读入） | > 0 且持续 → 严重内存不足 |
| so | swap out（写入磁盘） | > 0 且持续 → 严重内存不足 |
| **io** | | |
| bi | 块设备读入（块/秒） | — |
| bo | 块设备写出（块/秒） | — |
| **system** | | |
| in | 中断数/秒 | 过高 → 硬件或驱动问题 |
| cs | 上下文切换/秒 | 过高 → 进程/线程过多 |
| **cpu** | 百分比 | |
| us | 用户空间 | — |
| sy | 内核空间 | sy > 20% → 系统调用过多 |
| id | 空闲 | — |
| wa | I/O 等待 | wa > 20% → 磁盘瓶颈 |
| st | 被偷（虚拟化） | st > 0 → 邻居 VM 争抢资源 |

#### 4.2 vmstat 排障速查

```bash
# CPU 瓶颈：r 列持续 > CPU 核心数
# 内存瓶颈：si/so 持续 > 0，free 持续很低
# I/O 瓶颈：b 列 > 0，wa 列 > 20%
# 上下文切换过多：cs > 100000/s（正常几千到几万）

# 对比正常值和异常值
# 正常：r=1-3, b=0, si=0, so=0, wa=0-5, cs=5000-30000
# 异常：r=20+, b=5+, si=100+, so=100+, wa=30+, cs=200000+
```

### 5. sar — 系统活动报告

#### 5.1 安装与配置

```bash
# sysstat 包包含 sar
sudo apt install sysstat

# 启用数据收集（默认关闭）
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat
sudo systemctl restart sysstat

# 数据收集间隔（默认 10 分钟）
# 修改 /etc/cron.d/sysstat 中的 crontab
# */10 * * * * root command -v debian-sa1 > /dev/null && debian-sa1 1 1
```

#### 5.2 查看历史数据

```bash
# 今天的 CPU 使用率（每 10 分钟一条）
sar

# 指定时间范围
sar -s 10:00:00 -e 12:00:00

# 昨天的数据
sar -f /var/log/sysstat/sa$(date -d yesterday +%d)

# 前天的数据
sar -f /var/log/sysstat/sa$(date -d "2 days ago" +%d)
```

#### 5.3 各种监控模式

```bash
# CPU 使用率
sar -u 1 5

# 内存使用
sar -r 1 5
# 关键字段：
# kbmemfree: 空闲内存
# kbavail:   可用内存（包含可回收缓存）
# %memused:  内存使用率
# kbbuffers: 缓冲区
# kbcached:  页面缓存
# kbcommit:  已承诺的内存（含 swap）
# %commit:   承诺比率（> 100% 表示过度承诺）

# Swap 使用
sar -S 1 5
# 关键字段：
# kbswpfree: 空闲 swap
# %swpused:  swap 使用率
# kbswpin:   swap in 速率
# kbswpout:  swap out 速率

# I/O 和传输速率
sar -b 1 5
# 关键字段：
# tps:       每秒传输次数（IOPS）
# rtps:      每秒读传输
# wtps:      每秒写传输
# bread/s:   每秒读取块数
# bwrtn/s:   每秒写入块数

# 网络接口
sar -n DEV 1 5
# 关键字段：
# rxpck/s:   每秒接收包数
# txpck/s:   每秒发送包数
# rxkB/s:    每秒接收 KB
# txkB/s:    每秒发送 KB
# rxdrop/s:  每秒丢弃的接收包

# 网络错误
sar -n EDEV 1 5

# 网络 TCP 连接
sar -n TCP 1 5
# 关键字段：
# active/s:  主动连接数
# passive/s: 被动连接数（被连接）
# iseg/s:    接收的 TCP 段
# oseg/s:    发送的 TCP 段

# 上下文切换和中断
sar -w 1 5    # 上下文切换
sar -I ALL 1 5  # 每个中断

# 负载
sar -q 1 5
# 关键字段：
# runq-sz:   运行队列长度（等价于 vmstat 的 r）
# plist-sz:  进程和线程总数
# ldavg-1/5/15: 负载平均值
```

#### 5.4 事后排障

```bash
# 问题：昨天下午 3 点系统很慢，发生了什么？

# 查看昨天的 CPU
sar -u -f /var/log/sysstat/sa$(date -d yesterday +%d) -s 14:00 -e 16:00

# 查看昨天的内存
sar -r -f /var/log/sysstat/sa$(date -d yesterday +%d) -s 14:00 -e 16:00

# 查看昨天的 I/O
sar -b -f /var/log/sysstat/sa$(date -d yesterday +%d) -s 14:00 -e 16:00

# 查看昨天的网络
sar -n DEV -f /var/log/sysstat/sa$(date -d yesterday +%d) -s 14:00 -e 16:00

# 用图形化方式查看（需要安装 ksar）
# LC_ALL=C sar -A -f /var/log/sysstat/saXX > /tmp/sar_data.txt
# 然后用 ksar 打开生成图表
```

### 6. iostat — 磁盘 I/O 统计

#### 6.1 输出解读

```bash
# 安装
sudo apt install sysstat

# 每 1 秒采样一次，共 3 次，显示扩展信息
iostat -x 1 3

# 输出：
# Device    r/s     w/s     rkB/s   wkB/s   rrqm/s  wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz  rareq-sz wareq-sz  svctm  %util
# sda      12.50   45.20   256.00  1024.00  0.50   2.10   3.85   4.43   2.10    5.30   0.25    20.48    22.65   0.80   4.62
```

| 列 | 含义 | 说明 |
|----|------|------|
| r/s | 每秒读次数（IOPS） | — |
| w/s | 每秒写次数（IOPS） | — |
| rkB/s / wkB/s | 每秒读写吞吐量 | — |
| rrqm/s / wrqm/s | 每秒合并的请求数 | 合并多意味着顺序 I/O |
| **r_await / w_await** | 平均响应时间（毫秒） | **> 10ms 有性能问题，> 50ms 严重** |
| **aqu-sz** | 平均队列长度 | > 1 表示有请求在排队 |
| **%util** | 设备利用率 | **接近 100% 表示饱和** |

#### 6.2 I/O 瓶颈判断

```bash
# 判断标准：
# 1. %util 接近 100% → 磁盘饱和
# 2. r_await 或 w_await > 10ms → 响应慢
# 3. aqu-sz > 1 → 有排队
# 4. svctm 远小于 await → 等待时间长，磁盘是瓶颈

# 实时监控磁盘 I/O
watch -n 1 'iostat -x 1 1 | grep -E "^Device|^sda"'

# 找出哪个进程在做大量 I/O
sudo iotop -o
# 需要安装：sudo apt install iotop
# -o: 只显示正在做 I/O 的进程
# -d 1: 每 1 秒刷新
# -P: 显示进程而非线程
```

---

## 🏗️ 实战场景

### 场景 1：服务器响应慢的完整排查流程

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
top -b -n 1 | head -5
# 关注 us/sy/wa/id 的值

# ===== 第 2 步：定位瓶颈（1-2 分钟） =====

# 如果 wa 高（I/O 等待）
iostat -x 1 3
# 看 %util 和 await

# 如果 us 高（用户 CPU）
ps aux --sort=-%cpu | head -10

# 如果 sy 高（内核 CPU）
vmstat 1 5
# 看 cs（上下文切换）和 in（中断）是否异常

# 如果内存紧张
ps aux --sort=-%mem | head -10
# 检查是否有内存泄漏

# ===== 第 3 步：深挖根因 =====

# 如果是 I/O 问题
sudo iotop -o    # 谁在做 I/O？
sudo lsof +D /data  # 谁在访问这个目录？

# 如果是网络问题
sar -n DEV 1 5   # 网络流量是否异常？
ss -s            # 连接统计
ss -tnp | wc -l  # TCP 连接数

# 如果是 CPU 问题
perf top         # 实时函数级 CPU 采样（需要安装 perf）
pidstat 1 5      # 按进程统计 CPU（需要安装 sysstat）

# ===== 第 4 步：查看历史趋势 =====

# 问题是突然出现的还是渐进的？
sar -u -s 08:00 -e $(date +%H:%M)
# 查看从今天 8 点到现在的 CPU 趋势

sar -r -s 08:00 -e $(date +%H:%M)
# 查看内存趋势
```

### 场景 2：容量规划报告

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
echo "CPU: $(nproc) 核心"
echo "内存: $(free -h | awk '/Mem:/ {print $2}')"
echo "磁盘:"
df -h --local | grep -v "^Filesystem"

echo ""
echo "--- 当前使用率 ---"
cpu_load=$(cat /proc/loadavg | awk '{print $1}')
cpu_cores=$(nproc)
echo "CPU 负载: $cpu_load / $cpu_cores 核心 ($(( $(echo "$cpu_load * 100 / $cpu_cores" | bc) )%)"
echo "内存可用: $(free -h | awk '/Mem:/ {print $7}')"

echo ""
echo "--- 30 天趋势（基于 sar 数据） ---"
# 假设 sar 数据可用
echo "平均 CPU 使用率:"
sar -u | awk 'NR>3 && $NF != "idle" {sum+=$NF; count++} END {printf "  %.1f%%\n", (100 - sum/count)}'

echo "平均内存使用率:"
sar -r | awk 'NR>3 {sum+=$5; count++} END {printf "  %.1f%%\n", sum/count}'

echo ""
echo "--- 容量预警 ---"
# CPU
cpu_pct=$(echo "$cpu_load * 100 / $cpu_cores" | bc)
if (( cpu_pct > 80 )); then
    echo "⚠️  CPU 使用率 $cpu_pct%，建议扩容"
else
    echo "✅ CPU 使用率正常"
fi

# 磁盘
max_disk=$(df -h --local | awk 'NR>1 {gsub(/%/,"",$5); if($5>max) max=$5} END {print max+0}')
if (( max_disk > 85 )); then
    echo "⚠️  磁盘最大使用率 ${max_disk}%，建议扩容或清理"
else
    echo "✅ 磁盘使用率正常"
fi

# 内存
avail=$(free -h | awk '/Mem:/ {print $7}')
echo "✅ 可用内存: $avail"
```

---

## 🧪 练习题

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
buff/cache 的 3.4Gi 是可以被回收的，所以真正可用的是 12Gi。

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

# 3. 检查是否有大量随机读（数据库？）
iostat -x 1 5
# 如果 w/s 也很高，可能是数据库在做大量写

# 4. 检查文件系统
sudo tune2fs -l /dev/sda1 | grep "Mount count\|Check interval"
```
</details>

### 练习 3：使用 sar 回溯问题

昨天下午 2-4 点系统很慢，请用 sar 查看当时的 CPU、内存、I/O 情况。

<details>
<summary>答案</summary>

```bash
# 昨天的日期
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
```
</details>

---

## 📚 扩展阅读

- [Brendan Gregg — USE Method](http://www.brendangregg.com/usemethod.html) — Utilization, Saturation, Errors 性能分析方法论
- [Brendan Gregg — Linux Performance Tools](http://www.brendangregg.com/blog/2015-06-17/linux-perf-tools.html) — 60 秒性能排查流程图
- `man vmstat`, `man sar`, `man iostat` — 官方手册
- [The Art of Capacity Planning](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43505.pdf) — Google 的容量规划论文
