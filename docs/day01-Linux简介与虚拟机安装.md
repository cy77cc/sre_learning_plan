# Day 01: Linux 简介与虚拟机安装

> 📅 日期：2026-04-25
> 📖 学习主题：Linux 内核架构、发行版选型、虚拟化技术与服务器初始化
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：无（第一天）

## 🎯 学习目标

完成 Day 01 的学习后，你应该能够：
1. 画出 Linux 内核架构图，解释进程调度、内存管理、VFS、网络栈四大子系统的工作原理
2. 对比主流发行版的包管理器、init 系统、适用场景，并能根据业务需求做出选型决策
3. 理解虚拟化技术原理（VT-x/AMD-V、KVM、容器），能在 WSL2 或 VirtualBox 中搭建 Linux 环境
4. 编写完整的服务器初始化脚本（SSH 加固、防火墙、NTP、sysctl 调优）
5. 回答 Linux 启动流程、内核态 vs 用户态、/proc 文件系统等高频面试题

---

## 📖 核心知识点

### 1. Linux 内核架构深入讲解

Linux 内核是操作系统的核心，它管理硬件资源并为用户空间程序提供服务。理解内核架构是 SRE 进阶的基础。

#### 1.1 内核整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户空间 (User Space)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Nginx   │  │  MySQL   │  │  Python  │  │   bash   │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │              │              │              │          │
│  ═════╪══════════════╪══════════════╪══════════════╪═══════  │
│       │    系统调用 (System Call Interface)        │          │
│  ═════╪══════════════╪══════════════╪══════════════╪═══════  │
│       │              │              │              │          │
│       ▼              ▼              ▼              ▼          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              内核空间 (Kernel Space)                   │    │
│  │                                                       │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │    │
│  │  │ 进程调度器   │  │ 内存管理     │  │  VFS 层      │ │    │
│  │  │ (Scheduler)  │  │ (MM)         │  │ (Virtual FS) │ │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘ │    │
│  │         │                │                  │         │    │
│  │  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴───────┐ │    │
│  │  │ 网络协议栈   │  │ 设备驱动     │  │  安全模块     │ │    │
│  │  │ (Net Stack)  │  │ (Drivers)    │  │  (LSM)       │ │    │
│  │  └─────────────┘  └─────────────┘  └──────────────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌───────────────────────────┴───────────────────────────┐  │
│  │                    硬件 (Hardware)                      │  │
│  │  CPU    Memory    Disk    Network    USB    GPU        │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 进程调度器 (Process Scheduler)

进程调度器决定哪个进程在哪个 CPU 核心上运行，以及运行多长时间。

**CFS 调度器 (Completely Fair Scheduler)**：

Linux 默认使用 CFS 调度器（2.6.23 内核引入），核心思想是"完全公平"——每个进程获得与其权重成比例的 CPU 时间。

```
CFS 的工作原理：
┌──────────────────────────────────────────────┐
│              红黑树 (Red-Black Tree)            │
│                                                │
│              vruntime 最小的进程                │
│             （下一个被调度的进程）               │
│                    │                           │
│            ┌───────┴───────┐                   │
│            │               │                   │
│       vruntime 较小    vruntime 较大            │
│       优先级较高        优先级较低               │
│                                                │
│  vruntime = 实际运行时间 × (NICE_0_LOAD/权重)   │
│  nice 值越低 → 权重越高 → vruntime 增长越慢     │
│  → 被调度的频率越高                             │
└──────────────────────────────────────────────┘
```

**SRE 关注点**：
```bash
# 查看进程调度策略
chrt -p <PID>

# 查看进程的 nice 值（-20 到 19，越低优先级越高）
ps -eo pid,ni,comm | head -20

# 调整进程优先级
nice -n 10 ./my_program       # 以较低优先级启动
renice -n -5 -p <PID>         # 调整已运行进程的优先级

# 实时调度策略（SRE 中较少使用，但面试常考）
chrt -f 50 ./my_program       # FIFO 实时调度，优先级 50
chrt -r 50 ./my_program       # Round-Robin 实时调度
```

**NUMA 感知调度**：
```
现代服务器通常有多个 NUMA 节点：

NUMA Node 0          NUMA Node 1
┌──────────────┐    ┌──────────────┐
│  CPU 0-7     │    │  CPU 8-15    │
│  Local Memory│◄──►│ Local Memory │  (跨节点访问慢 2-3 倍)
│  64 GB       │    │  64 GB       │
└──────────────┘    └──────────────┘

# 查看 NUMA 拓扑
numactl --hardware

# 绑定进程到特定 NUMA 节点（数据库优化常用）
numactl --cpunodebind=0 --membind=0 mysqld
```

#### 1.3 内存管理 (Memory Management)

Linux 内存管理是 SRE 最需要深入理解的子系统之一，直接影响系统性能和稳定性。

**虚拟内存架构**：
```
进程虚拟地址空间 (64位，最大 256TB)
┌──────────────────────────────────────┐
│  0xFFFF...                           │
│  ┌──────────────────────────────────┐│
│  │  内核空间 (Kernel Space)          ││  ← 所有进程共享同一份
│  │  映射内核代码和数据               ││
│  ├──────────────────────────────────┤│  ← 0xFFFF800000000000
│  │  栈 (Stack)                       ││  ← 向下增长
│  │  ↓                               ││
│  │  ...                             ││
│  │  ↑                               ││
│  │  堆 (Heap)                        ││  ← 向上增长（malloc）
│  ├──────────────────────────────────┤│
│  │  BSS 段（未初始化全局变量）       ││
│  │  Data 段（已初始化全局变量）      ││
│  │  Text 段（代码）                  ││
│  └──────────────────────────────────┘│
│  0x0000...                           │
└──────────────────────────────────────┘
```

**页表与 TLB**：
```
虚拟地址 → 物理地址的转换过程：

虚拟地址
┌──────────┬──────────┬──────────┬──────────┐
│ PGD 索引 │ PUD 索引 │ PMD 索引 │ 页内偏移  │  (4 级页表)
└────┬─────┴────┬─────┴────┬─────┴────┬─────┘
     │          │          │          │
     ▼          ▼          ▼          │
  ┌──────┐  ┌──────┐  ┌──────┐       │
  │ PGD  │→ │ PUD  │→ │ PMD  │→ PTE  │
  └──────┘  └──────┘  └──────┘  └──┬──┘
                                    │
                                    ▼
                              ┌──────────┐
                              │ 物理页框  │ + 页内偏移 = 物理地址
                              └──────────┘

TLB (Translation Lookaside Buffer)：页表缓存，加速地址转换
TLB miss → 需要遍历页表 → 性能下降
```

**SRE 必知的内存概念**：
```bash
# 查看内存使用
free -h
#               total        used        free      shared  buff/cache   available
# Mem:           15Gi       4.2Gi       1.3Gi       256Mi       9.8Gi        10Gi

# 关键指标解释：
# total    = 物理总内存
# used     = 已使用的内存（不含 buff/cache）
# free     = 完全空闲的内存
# buff/cache = 缓冲区/缓存（可回收）
# available = 可用内存（free + 可回收的 buff/cache）

# 查看详细的内存信息
cat /proc/meminfo

# 关键字段：
# MemTotal      - 物理内存总量
# MemFree       - 空闲内存
# MemAvailable  - 可用内存（估算值）
# Buffers       - 块设备缓冲区
# Cached        - 页面缓存
# SwapTotal     - 交换分区总量
# SwapFree      - 交换分区空闲量
# Dirty         - 等待写回磁盘的脏页
```

**OOM Killer (Out-of-Memory Killer)**：
```
当内存严重不足时，内核会杀死进程来释放内存。

OOM 评分机制：
┌───────────────────────────────────────────┐
│  oom_score = 进程内存占用 + oom_score_adj  │
│                                            │
│  oom_score_adj: -1000 到 1000              │
│  -1000 = 永远不会被 OOM Kill               │
│  1000  = 最容易被杀死                       │
│                                            │
│  常见设置：                                 │
│  SSHD:      -900 （保持 SSH 连接）          │
│  数据库:    -500 （重要服务）               │
│  应用:      0    （默认值）                 │
└───────────────────────────────────────────┘

# 查看进程 OOM 评分
cat /proc/<PID>/oom_score
cat /proc/<PID>/oom_score_adj

# 设置进程 OOM 保护
echo -500 > /proc/<PID>/oom_score_adj

# 查看 OOM Kill 日志
dmesg | grep -i "oom\|killed"
journalctl -k | grep -i "oom"
```

#### 1.4 虚拟文件系统 (VFS)

VFS 是内核中的抽象层，为所有文件系统提供统一接口。

```
VFS 架构：

用户空间
    │  open(), read(), write(), close()
    ▼
┌─────────────────────────────────────────┐
│              VFS 层                      │
│  ┌───────────┐  ┌───────────┐           │
│  │ superblock│  │  inode     │           │
│  │ (文件系统  │  │ (文件元数据│           │
│  │  信息)     │  │  权限/大小)│           │
│  └───────────┘  └───────────┘           │
│  ┌───────────┐  ┌───────────┐           │
│  │   dentry  │  │   file    │           │
│  │ (目录项)   │  │ (打开文件) │           │
│  └───────────┘  └───────────┘           │
└────────────┬────────────────────────────┘
             │
    ┌────────┼────────┬────────┬────────┐
    ▼        ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ ext4 │ │ xfs  │ │btrfs │ │ tmpfs│ │ proc │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

**SRE 实用命令**：
```bash
# 查看文件系统类型
df -T
mount | grep "type"

# 查看 inode 使用情况
df -i

# 查看 VFS 缓存状态
cat /proc/slabinfo | head -20
vmstat -s | grep -i "cache"
```

#### 1.5 网络协议栈

Linux 网络栈是 SRE 必须精通的领域，直接影响服务的可用性和性能。

```
Linux 网络栈分层：

┌──────────────────────────────────────────────┐
│  应用层    │  Nginx, MySQL, Python            │
├───────────┤                                   │
│  Socket层  │  TCP/UDP socket API              │
├───────────┤                                   │
│  传输层    │  TCP (可靠) / UDP (快速)          │
├───────────┤                                   │
│  网络层    │  IP, ICMP, 路由表                │
├───────────┤                                   │
│  链路层    │  ARP, 邻居表                     │
├───────────┤                                   │
│  设备层    │  网卡驱动, Netfilter/iptables    │
├───────────┤                                   │
│  硬件层    │  网卡 (NIC), DMA, Ring Buffer    │
└──────────────────────────────────────────────┘

数据包接收流程：
1. 网卡收到数据包 → DMA 写入 Ring Buffer
2. 网卡触发硬中断 → ksoftirqd 软中断处理
3. 数据包经过 Netfilter 钩子 (PREROUTING)
4. 路由判断：本机 or 转发
5. 经过 INPUT 链 → 交付 Socket 层
6. 应用程序 read() 读取数据
```

**SRE 网络诊断命令**：
```bash
# 查看网络连接状态
ss -tunlp              # 查看监听端口
ss -s                  # 连接统计摘要
ss -tn state established | wc -l   # 已建立连接数

# 查看网络统计
cat /proc/net/snmp     # TCP/IP 协议统计
cat /proc/net/netstat  # 扩展网络统计

# 关键 TCP 参数（/proc/sys/net/）
cat /proc/sys/net/core/somaxconn          # 监听队列最大长度
cat /proc/sys/net/ipv4/tcp_max_syn_backlog  # SYN 队列最大长度
cat /proc/sys/net/ipv4/tcp_tw_reuse        # TIME_WAIT 复用
```

---

### 2. 各发行版详细对比

#### 2.1 包管理器差异

包管理器是发行版最核心的差异之一，直接影响软件安装、更新和依赖管理。

```
包管理器家族树：

Debian 系 (dpkg/apt)                Red Hat 系 (rpm)
┌─────────────────────┐            ┌─────────────────────┐
│  dpkg               │            │  rpm                │
│  ├── apt-get        │            │  ├── yum (CentOS 7) │
│  ├── apt            │            │  ├── dnf (RHEL 8+)  │
│  ├── apt-cache      │            │  └── zypper (SUSE)  │
│  └── aptitude       │            │                     │
└─────────────────────┘            └─────────────────────┘

Alpine (apk)           Arch (pacman)
┌──────────────┐       ┌──────────────┐
│  apk         │       │  pacman      │
│  (musl libc) │       │  (滚动更新)  │
└──────────────┘       └──────────────┘
```

**apt vs dnf 详细对比**：

| 特性 | apt (Debian/Ubuntu) | dnf (RHEL/Rocky) |
|------|---------------------|-------------------|
| 包格式 | `.deb` | `.rpm` |
| 源配置 | `/etc/apt/sources.list` | `/etc/yum.repos.d/*.repo` |
| 更新索引 | `apt update` | `dnf makecache` |
| 安装软件 | `apt install nginx` | `dnf install nginx` |
| 搜索软件 | `apt search nginx` | `dnf search nginx` |
| 查看信息 | `apt show nginx` | `dnf info nginx` |
| 卸载软件 | `apt remove nginx` | `dnf remove nginx` |
| 自动清理 | `apt autoremove` | `dnf autoremove` |
| 清理缓存 | `apt clean` | `dnf clean all` |
| 版本锁定 | `apt-mark hold nginx` | `dnf versionlock add nginx` |
| 本地安装 | `dpkg -i pkg.deb` | `rpm -i pkg.rpm` |
| 查找文件属于哪个包 | `dpkg -S /usr/bin/nginx` | `rpm -qf /usr/bin/nginx` |

#### 2.2 init 系统差异

init 系统是 PID 1 进程，负责启动和管理所有服务。

```
init 系统演进：

SysVinit (1992)  →  Upstart (2006)  →  systemd (2010)
   │                   │                    │
   │ CentOS 6          │ Ubuntu 6-14       │ 现代主流
   │ 串行启动          │ 并行启动          │ 并行+按需启动
   │ Shell 脚本        │ 事件驱动          │ 声明式配置
   └───────────────────┴────────────────────┘

systemd 核心概念：
┌────────────────────────────────────────────┐
│  Unit 类型：                                │
│  ├── .service  服务（Nginx, MySQL）        │
│  ├── .socket   Socket 激活                  │
│  ├── .timer    定时器（替代 cron）          │
│  ├── .mount    挂载点                       │
│  ├── .target   目标（类似运行级别）         │
│  └── .slice    cgroup 资源控制              │
└────────────────────────────────────────────┘
```

**systemd 常用命令**：
```bash
# 服务管理
systemctl start nginx       # 启动服务
systemctl stop nginx        # 停止服务
systemctl restart nginx     # 重启服务
systemctl reload nginx      # 重新加载配置（不中断服务）
systemctl status nginx      # 查看状态
systemctl enable nginx      # 设置开机自启
systemctl disable nginx     # 取消开机自启

# 查看所有服务
systemctl list-units --type=service
systemctl list-unit-files --type=service

# 查看服务日志
journalctl -u nginx         # 查看 Nginx 日志
journalctl -u nginx -f      # 实时跟踪
journalctl -u nginx --since "1 hour ago"  # 最近 1 小时

# 系统启动分析
systemd-analyze             # 启动总时间
systemd-analyze blame       # 各服务启动耗时
systemd-analyze critical-chain  # 关键路径
```

#### 2.3 发行版选型决策树

```
你的需求是什么？
│
├── 学习/入门
│   └── Ubuntu 22.04 LTS（文档最多、社区最活跃）
│
├── 生产服务器
│   ├── 需要 RHEL 兼容（企业级支持）
│   │   └── Rocky Linux 9 / AlmaLinux 9
│   ├── 需要最新软件包
│   │   └── Ubuntu 24.04 LTS
│   ├── 追求极致稳定
│   │   └── Debian 12
│   └── 云原生/容器
│       └── Flatcar Container Linux / Bottlerocket
│
├── 容器基础镜像
│   ├── 最小体积
│   │   └── Alpine Linux (5MB)
│   ├── 需要 glibc
│   │   └── Ubuntu Minimal / Debian Slim
│   └── 安全优先
│       └── Google Distroless
│
└── 嵌入式/IoT
    └── Buildroot / Yocto
```

---

### 3. 虚拟化技术原理

#### 3.1 硬件虚拟化基础

```
CPU 虚拟化 (VT-x/AMD-V)：

无虚拟化时的问题（敏感指令问题）：
┌──────────────────────────────────────────────┐
│  Guest OS 执行特权指令 → 直接操作硬件         │
│  → 破坏隔离性 → 安全灾难                      │
└──────────────────────────────────────────────┘

VT-x/AMD-V 解决方案（硬件辅助虚拟化）：
┌──────────────────────────────────────────────┐
│  引入两个新的 CPU 模式：                       │
│                                                │
│  VMX Root Mode    = Host OS / Hypervisor       │
│  VMX Non-Root Mode = Guest OS                  │
│                                                │
│  VM Entry: Root → Non-Root（进入虚拟机）       │
│  VM Exit:  Non-Root → Root（退出虚拟机）       │
│                                                │
│  Guest 执行特权指令 → 触发 VM Exit             │
│  → Hypervisor 处理 → VM Entry 返回             │
└──────────────────────────────────────────────┘
```

#### 3.2 KVM vs Xen vs VirtualBox

| 特性 | KVM | Xen | VirtualBox |
|------|-----|-----|------------|
| 类型 | Type 1 (内核模块) | Type 1 | Type 2 |
| 性能 | 接近原生 | 接近原生 | 中等 |
| CPU 开销 | < 5% | < 5% | 10-15% |
| 内存管理 | 硬件 EPT | 硬件 EPT | 软件影子页表 |
| 适用场景 | 服务器虚拟化 | 云计算 (AWS) | 桌面开发 |
| 管理工具 | libvirt, virsh | xl, xm | GUI, VBoxManage |
| 嵌套虚拟化 | 支持 | 支持 | 支持 |
| 热迁移 | 支持 | 支持 | 不支持 |
| 主要用户 | 企业服务器 | AWS, Citrix | 开发者 |

```
KVM 架构：

┌───────────────────────────────────────────┐
│              用户空间                       │
│  ┌──────────┐  ┌──────────┐               │
│  │  QEMU    │  │ libvirt  │               │
│  │(设备模拟) │  │ (管理API) │               │
│  └────┬─────┘  └──────────┘               │
│       │                                     │
│  ═════╪═══════════════════════════════════ │
│       │  /dev/kvm                          │
│  ┌────┴───────────────────────────────┐   │
│  │           KVM 内核模块              │   │
│  │  ├── vCPU 管理                     │   │
│  │  ├── 内存虚拟化 (EPT/NPT)          │   │
│  │  ├── 中断虚拟化 (APICv)            │   │
│  │  └── I/O 虚拟化 (virtio)           │   │
│  └────────────────────────────────────┘   │
│              Linux Kernel                   │
└───────────────────────────────────────────┘
```

#### 3.3 WSL2 架构原理

WSL2 不是传统的兼容层，而是一个真正的轻量级虚拟机。

```
WSL2 架构：

┌─────────────────────────────────────────────┐
│               Windows 11                      │
│  ┌─────────────────────────────────────────┐ │
│  │          Hyper-V 轻量级虚拟机            │ │
│  │  ┌───────────────────────────────────┐  │ │
│  │  │         WSL2 Linux Kernel         │  │ │
│  │  │  ┌─────────┐  ┌──────────────┐   │  │ │
│  │  │  │ Ubuntu  │  │   Alpine     │   │  │ │
│  │  │  │ 22.04   │  │   ...        │   │  │ │
│  │  │  └────┬────┘  └──────────────┘   │  │ │
│  │  │       │                           │  │ │
│  │  │  ┌────┴──────────────────────┐   │  │ │
│  │  │  │  9P 文件协议              │   │  │ │
│  │  │  │  (Plan 9 File Protocol)   │   │  │ │
│  │  │  └────┬──────────────────────┘   │  │ │
│  │  └───────┼──────────────────────────┘  │ │
│  └──────────┼─────────────────────────────┘ │
│             │                                │
│  ┌──────────┴─────────────────────────────┐ │
│  │  Windows 文件系统                       │ │
│  │  C:\  ←→  /mnt/c/                      │ │
│  │  D:\  ←→  /mnt/d/                      │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘

Plan 9 文件协议：
- WSL2 通过 9P 协议访问 Windows 文件
- /mnt/c/ 实际是通过 9P 挂载的 Windows C: 盘
- 跨文件系统访问有性能损耗（~50%）
- 建议：把项目放在 Linux 文件系统内（~/）
```

**WSL2 性能优化**：
```powershell
# Windows 用户目录下创建 .wslconfig
# C:\Users\<username>\.wslconfig
[wsl2]
memory=8GB           # 限制内存使用
processors=4         # 限制 CPU 核数
swap=4GB             # 交换空间
localhostForwarding=true  # 端口转发到 localhost

# 在 Linux 内创建 /etc/wsl.conf
[boot]
systemd=true         # 启用 systemd

[automount]
enabled=true         # 自动挂载 Windows 驱动器
options="metadata,umask=22,fmask=11"

[network]
generateResolvConf=true  # 自动生成 DNS 配置
```

---

### 4. 云服务器 Linux 选型实战

#### 4.1 主流云平台默认镜像

| 云平台 | 推荐发行版 | 默认镜像 | LTS 支持年限 |
|--------|-----------|---------|-------------|
| AWS | Amazon Linux 2023 | Amazon Linux 2023 | 5 年 |
| AWS | Ubuntu | Ubuntu 22.04/24.04 LTS | 10 年 |
| 阿里云 | Ubuntu/CentOS | Ubuntu 22.04, CentOS 7 | 10 年/已 EOL |
| 腾讯云 | Ubuntu/CentOS | Ubuntu 22.04, CentOS 7 | 10 年/已 EOL |
| GCP | Container-Optimized OS | COS | 滚动更新 |
| GCP | Ubuntu | Ubuntu 22.04 LTS | 10 年 |

#### 4.2 CentOS EOL 替代方案

```
CentOS 8 于 2021 年 12 月 31 日 EOL，CentOS 7 于 2024 年 6 月 30 日 EOL。

替代方案对比：
┌──────────────┬───────────┬───────────┬──────────────┐
│ 替代方案      │ 兼容性    │ 支持周期   │ 特点         │
├──────────────┼───────────┼───────────┼──────────────┤
│ Rocky Linux  │ 100%      │ 10 年     │ 社区驱动     │
│ AlmaLinux    │ 100%      │ 10 年     │ CloudLinux 出品 │
│ Oracle Linux │ 100%      │ 10 年     │ 免费但 Oracle │
│ Debian       │ 不兼容    │ 5 年      │ 极其稳定     │
│ Ubuntu LTS   │ 不兼容    │ 10 年     │ 社区最活跃   │
└──────────────┴───────────┴───────────┴──────────────┘

迁移步骤（CentOS → Rocky Linux）：
1. 备份所有数据和配置
2. 使用 migrate2rocky 脚本（原地迁移）
3. 或者新建 Rocky 服务器，迁移服务
4. 验证所有服务正常运行
5. 切换 DNS/负载均衡器
```

---

### 5. 服务器初始化完整脚本

以下是一个生产级的服务器初始化脚本，涵盖 SSH 加固、防火墙、NTP、sysctl 调优。

#### 5.1 完整初始化脚本

```bash
#!/bin/bash
# server_init.sh - 生产服务器初始化脚本
# 适用系统：Ubuntu 22.04 LTS / Rocky Linux 9
# 使用方法：sudo bash server_init.sh
set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查是否以 root 运行
if [[ $EUID -ne 0 ]]; then
    log_error "请使用 sudo 运行此脚本"
    exit 1
fi

# 检测发行版
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    else
        log_error "无法检测发行版"
        exit 1
    fi
    log_info "检测到系统: $DISTRO $VERSION"
}

# ==================== 系统更新 ====================
system_update() {
    log_info "正在更新系统..."
    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]]; then
        apt update -qq && apt upgrade -y -qq
        apt install -y -qq curl wget vim git htop iotop \
            net-tools dnsutils unzip zip jq tree \
            build-essential sysstat lsof strace
    elif [[ "$DISTRO" == "rocky" || "$DISTRO" == "almalinux" || "$DISTRO" == "centos" ]]; then
        dnf update -y -q
        dnf install -y -q curl wget vim git htop iotop \
            net-tools bind-utils unzip zip jq tree \
            gcc make sysstat lsof strace
    fi
    log_info "系统更新完成"
}

# ==================== 时区和 NTP ====================
setup_timezone_ntp() {
    log_info "配置时区和 NTP..."
    timedatectl set-timezone Asia/Shanghai

    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]]; then
        apt install -y -qq chrony
    else
        dnf install -y -q chrony
    fi

    systemctl enable chronyd
    systemctl start chronyd

    # 验证 NTP 同步
    chronyc sources -v
    timedatectl status | grep -i "synchronized"
    log_info "NTP 配置完成"
}

# ==================== 创建运维用户 ====================
create_ops_user() {
    local USERNAME="ops-admin"
    log_info "创建运维用户: $USERNAME"

    useradd -m -s /bin/bash -G sudo "$USERNAME" 2>/dev/null || \
    useradd -m -s /bin/bash -G wheel "$USERNAME" 2>/dev/null || true

    # 生成随机密码
    PASSWORD=$(openssl rand -base64 16)
    echo "$USERNAME:$PASSWORD" | chpasswd
    log_warn "用户 $USERNAME 密码: $PASSWORD (请立即修改并配置 SSH 密钥)"

    # 创建 .ssh 目录
    mkdir -p /home/$USERNAME/.ssh
    chmod 700 /home/$USERNAME/.ssh
    touch /home/$USERNAME/.ssh/authorized_keys
    chmod 600 /home/$USERNAME/.ssh/authorized_keys
    chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh
}

# ==================== SSH 加固 ====================
harden_ssh() {
    log_info "加固 SSH 配置..."

    # 备份原配置
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d)

    cat > /etc/ssh/sshd_config.d/hardening.conf << 'EOF'
# SSH 加固配置
Port 22                          # 生产环境建议改为非标准端口
PermitRootLogin no               # 禁止 root 直接登录
PasswordAuthentication no        # 禁用密码认证（仅密钥）
PubkeyAuthentication yes         # 启用公钥认证
MaxAuthTries 3                   # 最大认证尝试次数
LoginGraceTime 60                # 登录超时时间（秒）
ClientAliveInterval 300          # 客户端心跳间隔
ClientAliveCountMax 2            # 心跳失败次数
AllowUsers ops-admin             # 只允许特定用户登录
X11Forwarding no                 # 禁用 X11 转发
UseDNS no                        # 禁用 DNS 反向解析（加速登录）
PermitEmptyPasswords no          # 禁止空密码
Protocol 2                       # 只使用 SSHv2
MaxSessions 5                    # 最大并发会话数
Banner /etc/ssh/banner           # 登录横幅
EOF

    # 创建登录横幅
    cat > /etc/ssh/banner << 'EOF'
*************************************************************
*  WARNING: Authorized users only. All activity is logged.  *
*  Unauthorized access will be prosecuted.                  *
*************************************************************
EOF

    # 验证配置
    sshd -t
    systemctl restart sshd
    log_info "SSH 加固完成"
}

# ==================== 防火墙配置 ====================
setup_firewall() {
    log_info "配置防火墙..."

    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]]; then
        # UFW
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow 22/tcp comment "SSH"
        ufw allow 80/tcp comment "HTTP"
        ufw allow 443/tcp comment "HTTPS"
        ufw --force enable
        ufw status verbose
    else
        # firewalld
        systemctl enable firewalld
        systemctl start firewalld
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        firewall-cmd --permanent --set-default-zone=public
        firewall-cmd --reload
        firewall-cmd --list-all
    fi
    log_info "防火墙配置完成"
}

# ==================== sysctl 内核参数调优 ====================
tune_sysctl() {
    log_info "调优 sysctl 内核参数..."

    cat > /etc/sysctl.d/99-sre-tuning.conf << 'EOF'
# ============ 网络参数调优 ============
# TCP 连接队列
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535

# TIME_WAIT 复用
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15

# TCP 缓冲区
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# TCP keepalive
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3

# 本地端口范围
net.ipv4.ip_local_port_range = 1024 65535

# ============ 内存参数调优 ============
# 虚拟内存
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
vm.overcommit_memory = 0

# ============ 文件系统调优 ============
# 文件描述符
fs.file-max = 1000000
fs.inotify.max_user_watches = 524288

# ============ 安全参数 ============
# 禁用 IP 转发（除非是路由器/容器宿主机）
# net.ipv4.ip_forward = 0
# 防止 SYN Flood
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_tw_buckets = 36000
# 禁用 ICMP 重定向
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
EOF

    sysctl -p /etc/sysctl.d/99-sre-tuning.conf
    log_info "sysctl 调优完成"
}

# ==================== 文件描述符限制 ====================
setup_limits() {
    log_info "配置文件描述符限制..."

    cat > /etc/security/limits.d/99-sre-limits.conf << 'EOF'
# 文件描述符限制
*         soft    nofile    65535
*         hard    nofile    65535
root      soft    nofile    65535
root      hard    nofile    65535

# 进程数限制
*         soft    nproc     65535
*         hard    nproc     65535

# 核心转储大小
*         soft    core      unlimited
*         hard    core      unlimited
EOF

    log_info "文件描述符限制配置完成"
}

# ==================== 安装基础监控工具 ====================
install_monitoring() {
    log_info "安装基础监控工具..."

    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]]; then
        apt install -y -qq prometheus-node-exporter 2>/dev/null || true
    else
        dnf install -y -q prometheus-node-exporter 2>/dev/null || true
    fi
    log_info "监控工具安装完成"
}

# ==================== 主函数 ====================
main() {
    log_info "===== 服务器初始化开始 ====="
    detect_distro
    system_update
    setup_timezone_ntp
    create_ops_user
    harden_ssh
    setup_firewall
    tune_sysctl
    setup_limits
    install_monitoring
    log_info "===== 服务器初始化完成 ====="
    log_warn "请务必："
    log_warn "1. 配置 SSH 密钥登录"
    log_warn "2. 修改 ops-admin 用户密码"
    log_warn "3. 测试 SSH 连接后再关闭当前会话"
}

main "$@"
```

---

### 6. Linux 启动流程详解

#### 6.1 完整启动流程

```
Linux 启动流程（以 systemd 为例）：

1. BIOS/UEFI
   │  POST 自检 → 选择启动设备
   ▼
2. Bootloader (GRUB2)
   │  加载内核和 initramfs
   │  grub.cfg 配置
   ▼
3. 内核初始化
   │  解压内核 → 初始化硬件驱动
   │  挂载 initramfs（临时根文件系统）
   │  挂载真正的根文件系统
   ▼
4. systemd (PID 1)
   │  读取 /etc/systemd/system/default.target
   │  并行启动各个 target 和 service
   ▼
5. 默认 Target (multi-user.target 或 graphical.target)
   │  ├── sysinit.target    (系统初始化)
   │  ├── basic.target      (基础服务)
   │  ├── multi-user.target (多用户模式)
   │  └── graphical.target  (图形界面，如果启用)
   ▼
6. 登录界面
   │  getty / login
   ▼
7. 用户 Shell
   │  /etc/profile → ~/.bashrc → 用户环境
   ▼
8. 用户操作
```

**SRE 启动排查命令**：
```bash
# 查看启动耗时
systemd-analyze
# Startup finished in 2.123s (kernel) + 5.456s (initrd) + 12.789s (userspace) = 20.368s

# 查看各服务启动耗时（找出慢服务）
systemd-analyze blame | head -20

# 查看启动关键路径
systemd-analyze critical-chain

# 查看内核启动日志
dmesg | head -50
dmesg | grep -i "error\|fail\|warn"

# 查看 systemd 日志
journalctl -b                  # 当前启动的所有日志
journalctl -b -p err           # 当前启动的错误日志
journalctl --list-boots        # 列出所有启动记录
```

#### 6.2 GRUB2 救援模式

```
当系统无法正常启动时，可以通过 GRUB 进入救援模式：

1. 重启系统，在 GRUB 菜单按 'e' 编辑启动项
2. 找到 linux 行，末尾添加：
   init=/bin/bash       # 直接进入 bash（绕过 systemd）
   或
   single               # 进入单用户模式
   或
   systemd.unit=rescue.target  # 进入救援模式
3. 按 Ctrl+X 启动
4. 重新挂载根文件系统为读写：
   mount -o remount,rw /
5. 进行修复（如重置 root 密码）：
   passwd root
6. 重启：
   exec /sbin/init
```

---

### 7. 内核态 vs 用户态

```
内核态 (Kernel Mode) vs 用户态 (User Mode)：

┌──────────────────────────────────────────────────┐
│                  用户态 (Ring 3)                    │
│                                                    │
│  进程只能访问自己的虚拟内存空间                     │
│  不能直接访问硬件                                   │
│  不能直接访问内核数据                               │
│  通过系统调用请求内核服务                            │
│                                                    │
│  常见系统调用：                                     │
│  open()    - 打开文件                               │
│  read()    - 读取数据                               │
│  write()   - 写入数据                               │
│  fork()    - 创建进程                               │
│  exec()    - 执行程序                               │
│  mmap()    - 内存映射                               │
│  socket()  - 创建网络连接                           │
│  ioctl()   - 设备控制                               │
├──────────────────────────────────────────────────┤
│              系统调用接口 (syscall)                  │
├──────────────────────────────────────────────────┤
│                  内核态 (Ring 0)                    │
│                                                    │
│  可以访问所有内存                                   │
│  可以执行所有 CPU 指令                              │
│  可以直接操作硬件                                   │
│  可以访问所有进程的数据                              │
└──────────────────────────────────────────────────┘

上下文切换开销：
用户态 → 内核态 → 用户态 约 1-2 微秒
频繁的系统调用会显著影响性能
```

**SRE 实用命令**：
```bash
# 查看系统调用统计
strace -c ls /tmp
# % time     seconds  usecs/call     calls    errors syscall
# ------ ----------- ----------- --------- --------- ----------------
#  45.00    0.001234          10       123           open
#  30.00    0.000821           8       102           read
#  ...

# 跟踪进程的系统调用
strace -p <PID> -e trace=network   # 只跟踪网络相关
strace -p <PID> -e trace=file      # 只跟踪文件相关

# 查看系统调用表
ausyscall --dump                   # 需要安装 auditd
```

---

## 💻 实战练习

### 练习 1：内核信息探索

**目标**：通过 /proc 文件系统了解你的系统。

```bash
# 1. 查看 CPU 信息
cat /proc/cpuinfo | grep -E "model name|cpu cores|siblings" | head -5

# 2. 查看内存使用
cat /proc/meminfo | head -20

# 3. 查看系统负载
cat /proc/loadavg
# 输出：0.50 0.40 0.35 2/500 12345
# 含义：1分钟/5分钟/15分钟平均负载  运行/总进程数  最新PID

# 4. 查看内核版本
uname -a
cat /proc/version

# 5. 查看已加载的内核模块
lsmod | head -20

# 6. 查看磁盘信息
cat /proc/diskstats
lsblk

# 7. 查看网络接口
cat /proc/net/dev
ip addr show
```

### 练习 2：服务器初始化实战

**目标**：在虚拟机或 WSL2 中运行初始化脚本。

```bash
# 1. 创建脚本文件
vim /tmp/server_init.sh

# 2. 将上面的初始化脚本内容复制进去

# 3. 添加执行权限
chmod +x /tmp/server_init.sh

# 4. 运行脚本
sudo bash /tmp/server_init.sh

# 5. 验证各配置
systemctl status chronyd          # NTP
ufw status                        # 防火墙
sysctl net.core.somaxconn         # 内核参数
ulimit -n                         # 文件描述符限制
```

### 练习 3：启动流程分析

**目标**：分析系统启动流程，找出可以优化的地方。

```bash
# 1. 分析启动总时间
systemd-analyze

# 2. 找出启动最慢的服务
systemd-analyze blame | head -20

# 3. 查看启动关键路径
systemd-analyze critical-chain

# 4. 检查是否有不必要的服务
systemctl list-unit-files --state=enabled

# 5. 禁用不需要的服务（示例）
# sudo systemctl disable bluetooth
# sudo systemctl disable cups

# 6. 查看内核启动日志中的错误
dmesg | grep -i "error\|fail" | head -20
```

---

## 🎯 面试题精选

### 面试题 1：请描述 Linux 系统的完整启动流程

**参考答案**：

Linux 启动流程分为 6 个阶段：

1. **BIOS/UEFI 阶段**：执行 POST 自检，检测硬件，选择启动设备
2. **Bootloader 阶段**：GRUB2 加载内核镜像（vmlinuz）和 initramfs（初始内存文件系统）
3. **内核初始化阶段**：内核解压自身，初始化硬件驱动，挂载 initramfs 作为临时根文件系统，然后切换到真正的根文件系统
4. **init 进程阶段**：内核启动第一个用户空间进程 systemd（PID 1），它读取配置确定默认 target
5. **服务启动阶段**：systemd 按依赖关系并行启动各个服务单元（.service），到达默认 target
6. **用户登录阶段**：启动 getty/login 进程，显示登录界面，用户登录后启动 shell

### 面试题 2：内核态和用户态有什么区别？为什么要区分？

**参考答案**：

**区别**：
- **内核态 (Ring 0)**：可以执行所有 CPU 指令，访问所有内存和硬件资源
- **用户态 (Ring 3)**：只能访问自己的虚拟内存空间，不能直接操作硬件

**为什么要区分**：
- **安全性**：防止用户程序直接操作硬件，避免恶意程序破坏系统
- **稳定性**：用户程序崩溃不会影响内核和其他程序
- **隔离性**：不同进程之间互不干扰

**切换方式**：用户态通过系统调用（syscall）进入内核态，内核完成操作后返回用户态。

### 面试题 3：/proc 文件系统是什么？有什么作用？

**参考答案**：

/proc 是一个虚拟文件系统（伪文件系统），它不占用磁盘空间，而是内核在内存中动态生成的。

**作用**：
- 查看内核参数：`/proc/cpuinfo`、`/proc/meminfo`、`/proc/loadavg`
- 查看进程信息：`/proc/<PID>/` 目录下有进程的详细信息
- 修改内核参数：通过 `/proc/sys/` 可以动态修改内核参数
- 系统监控：各种监控工具（top、free、vmstat）底层都读取 /proc

### 面试题 4：CFS 调度器是如何工作的？

**参考答案**：

CFS（Completely Fair Scheduler，完全公平调度器）使用红黑树数据结构来管理可运行进程。

**核心原理**：
- 每个进程有一个虚拟运行时间（vruntime），记录该进程已经使用了多少 CPU 时间
- vruntime 越小的进程，在红黑树中越靠左，越优先被调度
- 新进程或刚被唤醒的进程 vruntime 较小，会优先获得 CPU
- nice 值影响 vruntime 的增长速度：nice 值越低（优先级越高），vruntime 增长越慢

**优点**：公平性好，交互式进程响应快，实现相对简单。

### 面试题 5：什么是 OOM Killer？如何防止关键进程被杀死？

**参考答案**：

OOM Killer 是 Linux 内核在内存严重不足时的自我保护机制。

**工作原理**：
1. 当系统内存严重不足，且无法通过回收缓存、swap 等方式释放内存时
2. 内核选择一个进程杀死来释放内存
3. 选择标准是 oom_score（0-1000），得分越高越容易被杀死
4. oom_score 主要基于进程的内存使用量计算

**防止关键进程被杀**：
```bash
# 方法1：设置 oom_score_adj（-1000 到 1000）
echo -500 > /proc/<PID>/oom_score_adj

# 方法2：在 systemd 服务中设置
[Service]
OOMScoreAdjust=-500

# 方法3：使用 mlock 锁定内存
# 在程序中调用 mlock() 系统调用
```

### 面试题 6：systemd 和 SysVinit 有什么区别？

**参考答案**：

| 特性 | SysVinit | systemd |
|------|----------|---------|
| 启动方式 | 串行启动 | 并行启动 |
| 依赖管理 | 手动配置优先级 | 自动解析依赖 |
| 服务定义 | Shell 脚本 | 声明式 Unit 文件 |
| 日志管理 | syslog | journalctl |
| 守护进程管理 | 启动后不管 | 持续监控、自动重启 |
| 资源控制 | 不支持 | 内置 cgroup 支持 |
| 启动速度 | 慢 | 快 |

**systemd 的优势**：启动速度快、服务管理方便、日志集中管理、支持资源限制。

### 面试题 7：WSL2 和 WSL1 有什么区别？

**参考答案**：

| 特性 | WSL1 | WSL2 |
|------|------|------|
| 架构 | 系统调用翻译层 | 真正的 Linux 内核（轻量级 VM） |
| 内核 | Windows 内核模拟 | 原生 Linux 内核 |
| 性能 | 文件 I/O 快（Windows 文件） | 计算密集型任务快 |
| 系统调用 | 部分支持（翻译） | 完全支持 |
| Docker | 不支持原生 | 完全支持 |
| 内核模块 | 不支持 | 不支持 |
| 文件系统 | NTFS | ext4（虚拟磁盘） |

**选择建议**：开发用 WSL2（Docker 支持好），如果大量操作 Windows 文件系统用 WSL1。

### 面试题 8：如何排查 Linux 启动卡住的问题？

**参考答案**：

1. **查看内核日志**：`dmesg | grep -i error`
2. **查看 systemd 日志**：`journalctl -b -p err`
3. **分析启动耗时**：`systemd-analyze blame`
4. **进入救援模式**：GRUB 编辑启动参数添加 `systemd.unit=rescue.target`
5. **检查 fstab**：错误的挂载配置会导致启动卡住
6. **检查磁盘**：`fsck /dev/sda1`
7. **禁用可疑服务**：`systemctl disable <service>`

---

## 📚 深入阅读

### 官方文档
- [Linux Kernel Documentation](https://www.kernel.org/doc/html/latest/)
- [systemd Documentation](https://systemd.io/DOCUMENTATION/)
- [Ubuntu Server Guide](https://ubuntu.com/server/docs)
- [Rocky Linux Documentation](https://docs.rockylinux.org/)
- [WSL2 Documentation](https://learn.microsoft.com/en-us/windows/wsl/)

### 推荐书籍
- 《Linux 内核设计与实现》(Robert Love) - 内核架构入门经典
- 《深入理解 Linux 内核》(Daniel P. Bovet) - 内核深入分析
- 《UNIX 环境高级编程》(APUE) - 系统编程圣经
- 《鸟哥的 Linux 私房菜》- 中文入门经典

### 技术博客
- [Brendan Gregg's Linux Performance](http://www.brendangregg.com/linuxperf.html)
- [LWN.net](https://lwn.net/) - Linux 内核新闻
- [The Linux Documentation Project](https://tldp.org/)

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出 Linux 内核架构图，说明四大子系统
- [ ] 能解释 CFS 调度器的工作原理和 vruntime 概念
- [ ] 能说明虚拟内存、页表、TLB 的工作原理
- [ ] 能解释 VFS 的作用和架构
- [ ] 能描述 Linux 网络栈的分层结构
- [ ] 能对比 apt 和 dnf 的常用命令
- [ ] 能解释 systemd 的 Unit 类型和管理命令
- [ ] 能说明 VT-x/AMD-V 硬件虚拟化原理
- [ ] 能描述 WSL2 的架构和 Plan 9 文件协议
- [ ] 能完整描述 Linux 启动流程

### 实操检查点
- [ ] 能在 WSL2 或 VirtualBox 中安装 Linux
- [ ] 能编写服务器初始化脚本
- [ ] 能配置 SSH 加固（禁用密码登录、root 登录）
- [ ] 能配置防火墙规则
- [ ] 能调优 sysctl 内核参数
- [ ] 能使用 systemd-analyze 分析启动流程
- [ ] 能通过 /proc 文件系统查看系统信息
- [ ] 能使用 strace 跟踪系统调用

---

*Day 01 完成 | 2026-04-25*
