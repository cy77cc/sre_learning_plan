# Day 02: 文件系统与目录结构 — FHS 标准详解

> 📅 日期：2026-04-25
> 📖 学习主题：VFS 架构、文件系统对比、FHS 标准、/proc 与 /sys 深入讲解
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 01（Linux 简介与虚拟机安装）

## 🎯 学习目标

完成 Day 02 的学习后，你应该能够：
1. 画出 VFS（虚拟文件系统）架构图，解释 superblock、inode、dentry、file 四大对象的作用
2. 对比 ext4、xfs、btrfs 的日志机制、inode 管理、性能特征，并能根据业务场景选择合适的文件系统
3. 详细说明 FHS 标准中每个目录的用途，特别是 SRE 需要关注的目录
4. 深入理解 /proc 和 /sys 虚拟文件系统，能通过它们获取系统和进程信息
5. 解释硬链接和软链接在 inode 层面的区别
6. 排查磁盘满和 inode 耗尽问题

---

## 📖 核心知识点

### 1. VFS（虚拟文件系统）架构原理

VFS 是 Linux 内核中的一个抽象层，它为所有文件系统提供统一的接口，使得用户程序可以用相同的方式访问不同的文件系统。

#### 1.1 为什么需要 VFS

```
没有 VFS 的情况：
┌─────────────────────────────────────────────────┐
│  应用程序需要针对每种文件系统写不同的代码          │
│                                                    │
│  读 ext4 文件：ext4_open() → ext4_read()          │
│  读 xfs 文件：  xfs_open()  → xfs_read()          │
│  读 NFS 文件：  nfs_open()  → nfs_read()          │
│  读 proc 文件：proc_open() → proc_read()          │
│                                                    │
│  问题：代码重复，每加一种文件系统都要改应用        │
└─────────────────────────────────────────────────┘

有 VFS 的情况：
┌─────────────────────────────────────────────────┐
│  应用程序只需调用标准接口                          │
│                                                    │
│  读文件：open() → read() → close()                │
│                                                    │
│  VFS 层负责分发到具体的文件系统实现                │
│                                                    │
│  ┌───────────┐                                    │
│  │    VFS    │                                    │
│  └─────┬─────┘                                    │
│   ┌────┼────┬────┬────┬────┐                     │
│   ▼    ▼    ▼    ▼    ▼    ▼                     │
│  ext4  xfs  btrfs nfs  proc tmpfs                │
└─────────────────────────────────────────────────┘
```

#### 1.2 VFS 四大核心对象

```
VFS 核心数据结构：

┌─────────────────────────────────────────────────────────┐
│                                                           │
│  1. superblock（超级块）                                  │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 描述一个已挂载的文件系统                              │ │
│  │ • 文件系统类型（ext4, xfs, ...）                      │ │
│  │ • 块大小、块数量                                      │ │
│  │ • 脏标志（是否有修改未写回磁盘）                      │ │
│  │ • 指向根 dentry 的指针                                │ │
│  │ 存储位置：磁盘上的固定位置 + 内存副本                 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  2. inode（索引节点）                                     │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 描述一个文件的元数据                                  │ │
│  │ • inode 编号（唯一标识）                              │ │
│  │ • 文件类型（普通文件、目录、链接、设备...）           │ │
│  │ • 权限（rwxrwxrwx）                                  │ │
│  │ • 所有者（UID, GID）                                  │ │
│  │ • 大小、时间戳（atime, mtime, ctime）                │ │
│  │ • 数据块指针（直接/间接/双间接/三间接）              │ │
│  │ • 不包含文件名！（文件名在 dentry 中）               │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  3. dentry（目录项）                                      │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 描述一个目录项（文件名与 inode 的映射）               │ │
│  │ • 文件名                                              │ │
│  │ • 指向 inode 的指针                                   │ │
│  │ • 父 dentry 指针                                      │ │
│  │ • 子 dentry 链表                                      │ │
│  │ • 存储在 dentry cache 中（加速路径查找）             │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  4. file（打开的文件）                                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 描述一个被进程打开的文件                              │ │
│  │ • 文件打开模式（读、写、追加）                        │ │
│  │ • 当前读写位置（f_pos）                               │ │
│  │ • 指向 dentry 的指针                                  │ │
│  │ • 指向 file_operations 的函数指针表                   │ │
│  │ • 每个 open() 调用创建一个 file 对象                  │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
└─────────────────────────────────────────────────────────┘

关系图：
进程 fd 表 → file → dentry → inode → 数据块
                ↑
            file_operations（函数指针表，指向具体文件系统的实现）
```

#### 1.3 文件打开的完整流程

```
应用程序调用 open("/etc/nginx/nginx.conf", O_RDONLY)：

1. 路径查找（Path Lookup）
   "/" → 根 dentry
   "etc" → 在根 dentry 的子项中查找 → etc dentry
   "nginx" → 在 etc dentry 的子项中查找 → nginx dentry
   "nginx.conf" → 在 nginx dentry 的子项中查找 → nginx.conf dentry

2. 权限检查
   检查进程是否有权限访问该 inode
   检查 DAC（自主访问控制）权限位

3. 分配 file 对象
   设置 f_op 指向具体文件系统的 file_operations
   设置 f_pos = 0（读写位置）

4. 返回文件描述符（fd）
   在进程的 fd 表中分配一个空闲的 fd 编号
   将 fd 与 file 对象关联
   返回 fd 给应用程序

5. 后续操作
   read(fd, buf, size) → file->f_op->read()
   write(fd, buf, size) → file->f_op->write()
   close(fd) → 释放 file 对象，回收 fd
```

**SRE 实用命令**：
```bash
# 查看文件系统类型
df -T

# 查看挂载信息
mount | column -t
findmnt

# 查看文件的 inode 信息
stat /etc/nginx/nginx.conf
#   File: /etc/nginx/nginx.conf
#   Size: 1234       Blocks: 8          IO Block: 4096   regular file
#   Device: 801h/2049d  Inode: 1234567     Links: 1
#   Access: (0644/-rw-r--r--)  Uid: (    0/    root)   Gid: (    0/    root)

# 查看文件系统的超级块信息
sudo dumpe2fs /dev/sda1 | head -50    # ext4
sudo xfs_info /dev/sda1               # xfs

# 查看 dentry cache 使用情况
cat /proc/slabinfo | grep dentry
```

---

### 2. ext4/xfs/btrfs 文件系统对比

#### 2.1 ext4 文件系统

ext4 是 Linux 最成熟、最广泛使用的文件系统。

```
ext4 磁盘布局：
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│  Boot    │  Block   │  Block   │   Data   │   Data   │
│  Block   │  Group 0 │  Group 1 │   Group  │   Group  │
│  (1KB)   │          │          │    ...   │    ...   │
└──────────┴──────────┴──────────┴──────────┴──────────┘

Block Group 内部结构：
┌────────────────────────────────────────────┐
│  Super Block (副本)                         │
│  Group Descriptors                          │
│  Block Bitmap (块位图，标记哪些块已使用)     │
│  inode Bitmap (inode 位图)                  │
│  inode Table (inode 表)                     │
│  Data Blocks (实际数据)                     │
└────────────────────────────────────────────┘

ext4 inode 结构：
┌────────────────────────────────────────────┐
│  inode 编号、文件类型、权限                 │
│  UID、GID                                  │
│  大小、时间戳                               │
│  直接块指针 ×12  (直接指向数据块)           │
│  一级间接指针 ×1  (指向一个指针块)          │
│  二级间接指针 ×1  (指向指针的指针块)        │
│  三级间接指针 ×1  (指向指针的指针的指针块)  │
│  Extended Attributes (扩展属性)             │
│  Inline Data (小文件直接存在 inode 中)      │
└────────────────────────────────────────────┘

ext4 日志机制（Journaled）：
1. 数据写入日志区（Write-Ahead Log）
2. 日志写入完成 → 标记事务完成
3. 数据写入最终位置
4. 清除日志

日志模式：
┌──────────────┬──────────────────────────────────┐
│ data=journal │ 数据和元数据都写日志（最安全）    │
│ data=ordered │ 只有元数据写日志（默认，推荐）    │
│ data=writeback│ 只有元数据写日志（最快）         │
└──────────────┴──────────────────────────────────┘
```

**ext4 常用命令**：
```bash
# 创建 ext4 文件系统
mkfs.ext4 /dev/sdb1

# 调整 ext4 文件系统大小
resize2fs /dev/sdb1

# 查看 ext4 文件系统信息
dumpe2fs /dev/sda1 | head -100
tune2fs -l /dev/sda1

# 修复 ext4 文件系统
fsck.ext4 /dev/sda1
e2fsck -f /dev/sda1

# 调整 ext4 参数
tune2fs -c 30 /dev/sda1       # 每 30 次挂载后强制检查
tune2fs -i 180d /dev/sda1     # 每 180 天强制检查
tune2fs -m 1 /dev/sda1        # 预留空间改为 1%（默认 5%）
```

#### 2.2 xfs 文件系统

xfs 是 RHEL/CentOS 7+ 的默认文件系统，擅长处理大文件和高并发 I/O。

```
xfs 架构：
┌─────────────────────────────────────────────────┐
│                                                   │
│  ┌─────────────┐  ┌─────────────┐               │
│  │  Data       │  │  Log        │               │
│  │  Section    │  │  Section    │               │
│  │  (数据区)    │  │  (日志区)    │               │
│  │             │  │             │               │
│  │  AG 0      │  │  循环日志    │               │
│  │  AG 1      │  │             │               │
│  │  AG 2      │  │             │               │
│  │  ...       │  │             │               │
│  └─────────────┘  └─────────────┘               │
│                                                   │
│  ┌─────────────┐                                 │
│  │  Realtime   │                                 │
│  │  Section    │  (可选，用于实时 I/O)           │
│  │  (实时区)    │                                 │
│  └─────────────┘                                 │
│                                                   │
│  AG = Allocation Group（分配组）                  │
│  每个 AG 有独立的空闲空间管理，支持并行 I/O      │
└─────────────────────────────────────────────────┘
```

**xfs 常用命令**：
```bash
# 创建 xfs 文件系统
mkfs.xfs /dev/sdb1

# 查看 xfs 信息
xfs_info /dev/sda1

# 扩大 xfs 文件系统（只能扩大，不能缩小）
xfs_growfs /mount/point

# 修复 xfs 文件系统
xfs_repair /dev/sda1

# 查看 xfs 使用情况
xfs_db -r /dev/sda1 -c "freesp -s"

# 冻结/解冻文件系统（用于一致性快照）
xfs_freeze -f /mount/point
xfs_freeze -u /mount/point
```

#### 2.3 btrfs 文件系统

btrfs 是下一代文件系统，支持快照、压缩、校验等高级特性。

```
btrfs 核心特性：

┌─────────────────────────────────────────────────┐
│  btrfs 特性：                                    │
│                                                   │
│  1. Copy-on-Write (COW)                         │
│     写入时不覆盖原数据，而是写到新位置           │
│     → 天然支持快照                               │
│                                                   │
│  2. 快照 (Snapshot)                              │
│     瞬间创建文件系统的只读/可写副本              │
│     → 用于备份、回滚                             │
│                                                   │
│  3. 内置 RAID                                   │
│     支持 RAID 0, 1, 10, 5, 6                    │
│     不需要 mdadm                                 │
│                                                   │
│  4. 透明压缩                                    │
│     zlib / lzo / zstd 压缩                      │
│     节省磁盘空间，某些场景提升 I/O              │
│                                                   │
│  5. 数据校验                                    │
│     每个数据块都有校验和                         │
│     自动检测和修复数据损坏                       │
│                                                   │
│  6. 子卷 (Subvolume)                             │
│     类似于轻量级分区                             │
│     可以独立挂载、快照                           │
│                                                   │
│  7. 在线碎片整理                                 │
│     不需要卸载即可整理碎片                       │
└─────────────────────────────────────────────────┘
```

**btrfs 常用命令**：
```bash
# 创建 btrfs 文件系统
mkfs.btrfs /dev/sdb1

# 创建多设备 btrfs（RAID1）
mkfs.btrfs -d raid1 -m raid1 /dev/sdb1 /dev/sdc1

# 查看 btrfs 信息
btrfs filesystem show
btrfs filesystem usage /mount/point

# 创建子卷
btrfs subvolume create /mnt/data/subvol1

# 创建快照
btrfs subvolume snapshot /mnt/data /mnt/data/snap_$(date +%Y%m%d)

# 创建只读快照
btrfs subvolume snapshot -r /mnt/data /mnt/data/snap_readonly

# 压缩
btrfs filesystem defragment -r -zstd /mount/point

# 添加设备
btrfs device add /dev/sdd1 /mount/point

# 均衡数据
btrfs balance start /mount/point
```

#### 2.4 三种文件系统对比

| 特性 | ext4 | xfs | btrfs |
|------|------|-----|-------|
| 最大文件大小 | 16 TB | 8 EB | 16 EB |
| 最大文件系统大小 | 1 EB | 8 EB | 16 EB |
| 日志机制 | 元数据日志 | 元数据日志 | COW（无传统日志） |
| inode 管理 | 静态分配 | 动态分配 | 动态分配 |
| 快照 | 不支持 | 不支持 | 原生支持 |
| 压缩 | 不支持 | 不支持 | 支持（zlib/lzo/zstd） |
| RAID | 需要 mdadm | 需要 mdadm | 内置 |
| 数据校验 | 不支持 | CRC32 | 多种算法 |
| 碎片整理 | 离线（e4defrag） | 不需要 | 在线 |
| 缩小文件系统 | 支持 | 不支持 | 支持 |
| 成熟度 | 非常成熟 | 成熟 | 较新，持续改进 |
| 适用场景 | 通用服务器 | 大文件、高并发 | 需要快照/压缩的场景 |
| RHEL 默认 | RHEL 6 | RHEL 7+ | 不默认（实验性） |
| Ubuntu 默认 | 是 | 可选 | 可选 |

#### 2.5 SRE 文件系统选型指南

```
文件系统选型决策：

你的需求是什么？
│
├── 通用服务器（Web、API）
│   └── ext4（成熟稳定，文档最多）
│
├── 大文件处理（视频、大数据）
│   └── xfs（大文件性能优秀）
│
├── 数据库服务器
│   ├── MySQL/PostgreSQL → ext4 或 xfs
│   └── 需要快照备份 → btrfs
│
├── 需要频繁快照
│   └── btrfs（原生快照支持）
│
├── NAS/文件服务器
│   └── btrfs（数据校验、RAID、压缩）
│
└── 容器存储
    ├── Docker → ext4 或 xfs（overlay2）
    └── 需要快照 → btrfs
```

---

### 3. FHS 标准详解

FHS（Filesystem Hierarchy Standard）定义了 Linux 目录结构的标准，目前版本为 3.0。

#### 3.1 完整目录结构

```
/                                    # 根目录（所有目录的起点）
├── bin/ → usr/bin                   # 基本命令（符号链接，FHS 3.0+）
├── sbin/ → usr/sbin                 # 系统管理命令（符号链接）
├── lib/ → usr/lib                   # 基本库文件（符号链接）
├── lib64/ → usr/lib64               # 64 位库文件（符号链接）
├── etc/                             # 系统配置文件 ⭐⭐⭐⭐⭐
├── boot/                            # 启动文件（内核、initramfs）
├── dev/                             # 设备文件
├── proc/                            # 进程和内核信息（虚拟）
├── sys/                             # 硬件设备信息（虚拟）
├── run/                             # 运行时数据（重启后清空）
├── tmp/                             # 临时文件（所有用户可写）
├── var/                             # 可变数据 ⭐⭐⭐⭐⭐
│   ├── log/                         # 系统日志
│   ├── lib/                         # 应用运行时数据
│   ├── cache/                       # 应用缓存
│   ├── spool/                       # 队列数据（邮件、打印）
│   ├── tmp/                         # 持久化临时文件
│   └── run/ → /run                  # 运行时数据
├── home/                            # 普通用户主目录
├── root/                            # root 用户主目录
├── usr/                             # 用户程序资源 ⭐⭐⭐⭐
│   ├── bin/                         # 用户命令
│   ├── sbin/                        # 系统管理命令
│   ├── lib/                         # 库文件
│   ├── local/                       # 本地安装的软件
│   │   ├── bin/                     # 本地命令
│   │   ├── sbin/                    # 本地系统命令
│   │   ├── lib/                     # 本地库文件
│   │   └── share/                   # 本地共享数据
│   ├── share/                       # 架构无关数据
│   │   ├── man/                     # 手册页
│   │   ├── doc/                     # 文档
│   │   └── zoneinfo/               # 时区数据
│   └── src/                         # 源代码
├── opt/                             # 可选软件包
├── mnt/                             # 临时挂载点
├── media/                           # 可移动媒体挂载点
├── srv/                             # 服务数据
└── lost+found/                      # fsck 恢复的文件
```

#### 3.2 SRE 高频关注目录详解

**/etc — 系统配置中心**：

```bash
# 网络配置
/etc/hosts                    # 主机名解析
/etc/resolv.conf              # DNS 配置
/etc/network/interfaces       # 网络接口配置（Debian）
/etc/sysconfig/network-scripts/  # 网络配置（RHEL）
/etc/hostname                 # 主机名
/etc/netplan/*.yaml           # Netplan 网络配置（Ubuntu 18.04+）

# SSH 配置
/etc/ssh/sshd_config          # SSH 服务端配置
/etc/ssh/ssh_config           # SSH 客户端配置
/etc/ssh/ssh_host_*_key       # SSH 主机密钥

# 用户和权限
/etc/passwd                   # 用户账户信息
/etc/shadow                   # 用户密码（加密）
/etc/group                    # 用户组信息
/etc/sudoers                  # sudo 权限配置
/etc/pam.d/                   # PAM 认证配置

# 服务配置
/etc/nginx/                   # Nginx 配置
/etc/mysql/                   # MySQL 配置
/etc/redis/                   # Redis 配置
/etc/systemd/                 # systemd 配置
/etc/cron.d/                  # 定时任务
/etc/crontab                  # 系统定时任务
/etc/logrotate.d/             # 日志轮转配置

# 系统配置
/etc/fstab                    # 文件系统挂载表
/etc/os-release               # 操作系统版本信息
/etc/sysctl.conf              # 内核参数配置
/etc/security/limits.conf     # 资源限制配置
```

**/var/log — 日志目录（SRE 最常访问）**：

```bash
# 系统日志
/var/log/syslog               # Ubuntu/Debian 系统日志
/var/log/messages             # RHEL/CentOS 系统日志
/var/log/auth.log             # 认证日志（登录、sudo）
/var/log/kern.log             # 内核日志
/var/log/dmesg                # 启动硬件检测日志
/var/log/boot.log             # 启动服务日志

# 服务日志
/var/log/nginx/access.log     # Nginx 访问日志
/var/log/nginx/error.log      # Nginx 错误日志
/var/log/mysql/error.log      # MySQL 错误日志
/var/log/redis/redis.log      # Redis 日志

# 日志分析实战
# 查找 SSH 暴力破解
grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -20

# 查找 OOM Kill 事件
grep -i "oom\|killed" /var/log/syslog

# 查找磁盘错误
grep -i "i/o error\|disk\|sector" /var/log/syslog
```

**/proc — 进程和内核信息**：

```bash
# 系统信息
/proc/cpuinfo                  # CPU 详细信息
/proc/meminfo                  # 内存详细信息
/proc/loadavg                  # 系统负载
/proc/uptime                   # 系统运行时间
/proc/version                  # 内核版本
/proc/filesystems              # 支持的文件系统
/proc/mounts                   # 当前挂载信息
/proc/net/                     # 网络信息

# 进程信息（每个进程一个目录）
/proc/<PID>/
├── cmdline                    # 启动命令行
├── cwd -> /path               # 当前工作目录（符号链接）
├── environ                    # 环境变量
├── exe -> /path/to/binary     # 可执行文件（符号链接）
├── fd/                        # 文件描述符目录
│   ├── 0 -> /dev/pts/0        # stdin
│   ├── 1 -> /dev/pts/0        # stdout
│   └── 3 -> socket:[12345]    # 网络连接
├── maps                       # 内存映射
├── status                     # 进程状态摘要
├── stat                       # 进程状态（机器可读）
├── io                         # I/O 统计
├── limits                     # 资源限制
├── cgroup                     # cgroup 信息
└── net/                       # 进程网络信息

# 实用示例
# 查看进程打开了哪些文件
ls -la /proc/<PID>/fd

# 查看进程的环境变量
cat /proc/<PID>/environ | tr '\0' '\n'

# 查看进程的内存使用
cat /proc/<PID>/status | grep -i "vm\|rss"
```

**/sys — 硬件和内核对象信息**：

```bash
# CPU 信息
/sys/devices/system/cpu/cpu*/cpufreq/   # CPU 频率
/sys/devices/system/cpu/cpu*/online     # CPU 是否在线

# 块设备信息
/sys/block/sda/queue/scheduler          # I/O 调度器
/sys/block/sda/queue/nr_requests        # 队列深度
/sys/block/sda/queue/read_ahead_kb      # 预读大小

# 网络设备信息
/sys/class/net/eth0/speed               # 网卡速度
/sys/class/net/eth0/mtu                 # MTU
/sys/class/net/eth0/statistics/         # 网卡统计

# 内存管理
/sys/kernel/mm/transparent_hugepage/    # 大页配置
/sys/module/compaction/                 # 内存压缩

# 实用示例
# 查看 I/O 调度器
cat /sys/block/sda/queue/scheduler
# [mq-deadline] kyber bfq none

# 查看网卡速度
cat /sys/class/net/eth0/speed
# 1000

# 修改 I/O 调度器
echo "bfq" > /sys/block/sda/queue/scheduler
```

---

### 4. 硬链接 vs 软链接的 inode 层面原理

#### 4.1 inode 层面的区别

```
硬链接 (Hard Link)：
┌─────────────────────────────────────────────────┐
│                                                   │
│  目录项 A                目录项 B                  │
│  ┌──────────┐           ┌──────────┐             │
│  │ 文件名:  │           │ 文件名:  │             │
│  │ file.txt │           │ link.txt │             │
│  └────┬─────┘           └────┬─────┘             │
│       │                      │                    │
│       └──────────┬───────────┘                    │
│                  │                                 │
│                  ▼                                 │
│           ┌──────────┐                            │
│           │  inode    │                            │
│           │  #123456  │                            │
│           │  Links: 2 │  ← 链接计数               │
│           │  Size: 1KB│                            │
│           └──────────┘                            │
│                                                   │
│  特点：                                           │
│  • 多个文件名指向同一个 inode                     │
│  • 共享同一份数据                                 │
│  • 删除一个链接，链接计数 -1                      │
│  • 链接计数为 0 时，数据才被删除                  │
│  • 不能跨文件系统                                 │
│  • 不能链接目录                                   │
└─────────────────────────────────────────────────┘

软链接 (Symbolic Link / Symlink)：
┌─────────────────────────────────────────────────┐
│                                                   │
│  目录项 A                目录项 B                  │
│  ┌──────────┐           ┌──────────┐             │
│  │ 文件名:  │           │ 文件名:  │             │
│  │ file.txt │           │ link.txt │             │
│  └────┬─────┘           └────┬─────┘             │
│       │                      │                    │
│       ▼                      ▼                    │
│  ┌──────────┐           ┌──────────┐             │
│  │  inode    │           │  inode    │             │
│  │  #123456  │           │  #789012  │             │
│  │  Links: 1 │           │  Links: 1 │             │
│  │  Size: 1KB│           │  Size: 7B │             │
│  └──────────┘           │ 存储路径: │             │
│       │                  │"./file.txt"│            │
│       ▼                  └────┬─────┘             │
│  ┌──────────┐                 │                    │
│  │ 数据块   │                 │ 读取时跟随路径     │
│  │ (实际内容)│                 └──────────►        │
│  └──────────┘                                      │
│                                                   │
│  特点：                                           │
│  • 软链接有自己的 inode，存储目标路径             │
│  • 读取时需要解析路径找到目标文件                 │
│  • 删除源文件 → 软链接失效（悬空链接）           │
│  • 可以跨文件系统                                 │
│  • 可以链接目录                                   │
└─────────────────────────────────────────────────┘
```

#### 4.2 操作命令对比

```bash
# 创建硬链接
ln /etc/nginx/nginx.conf /backup/nginx.conf.hardlink
# 验证：两个文件 inode 相同
ls -li /etc/nginx/nginx.conf /backup/nginx.conf.hardlink
# 123456 -rw-r--r-- 2 root root 1234 ... /etc/nginx/nginx.conf
# 123456 -rw-r--r-- 2 root root 1234 ... /backup/nginx.conf.hardlink

# 创建软链接
ln -s /etc/nginx/nginx.conf /backup/nginx.conf.symlink
# 验证：不同 inode，软链接有自己的 inode
ls -li /etc/nginx/nginx.conf /backup/nginx.conf.symlink
# 123456 -rw-r--r-- 1 root root 1234 ... /etc/nginx/nginx.conf
# 789012 lrwxrwxrwx 1 root root   25 ... /backup/nginx.conf.symlink -> /etc/nginx/nginx.conf

# 查找所有硬链接（相同 inode）
find / -inum 123456 2>/dev/null

# 查找断链（目标不存在的软链接）
find / -type l ! -exec test -e {} \; -print

# 删除操作的影响
# 硬链接：删除一个，其他链接仍然有效
rm /backup/nginx.conf.hardlink    # 原文件仍然存在

# 软链接：删除源文件，软链接失效
rm /etc/nginx/nginx.conf           # 软链接变成断链
```

#### 4.3 SRE 实际应用场景

```bash
# 场景1：配置文件版本管理（硬链接）
# 硬链接可以节省磁盘空间，因为共享同一份数据
cp /etc/nginx/nginx.conf /backup/nginx.conf.v1
cp /etc/nginx/nginx.conf /backup/nginx.conf.v2
# 以上占用两份空间

ln /etc/nginx/nginx.conf /backup/nginx.conf.v1
# 硬链接不额外占用空间

# 场景2：软件版本切换（软链接）
ln -sfn /opt/node-v18.17.0 /usr/local/node    # 切换到 v18
ln -sfn /opt/node-v20.9.0 /usr/local/node     # 切换到 v20
export PATH=/usr/local/node/bin:$PATH

# 场景3：Nginx 站点启用（软链接）
ln -s /etc/nginx/sites-available/mysite.conf /etc/nginx/sites-enabled/mysite.conf
# 禁用站点：删除软链接即可，不影响原配置
rm /etc/nginx/sites-enabled/mysite.conf

# 场景4：日志文件管理
# 当进程持有文件描述符时，rm 删除文件不会释放空间
# 正确做法：
# 1. 先创建新文件
cp /var/log/app.log /var/log/app.log.1
# 2. 通知进程重新打开日志（如 nginx -s reopen）
# 3. 删除旧文件
rm /var/log/app.log.1
```

---

### 5. 文件系统挂载流程

#### 5.1 挂载原理

```
Linux 文件系统挂载流程：

1. 准备块设备
   /dev/sdb1 (未挂载的分区)

2. 创建挂载点
   mkdir -p /data

3. 挂载操作
   mount /dev/sdb1 /data

4. 挂载后效果
   /data 目录的内容 = /dev/sdb1 分区的根目录
   原来 /data 目录中的文件被"隐藏"

5. 卸载操作
   umount /data
   或
   umount /dev/sdb1

挂载的本质：
把一个文件系统的根目录（dentry）嫁接到另一个文件系统的某个目录上
```

#### 5.2 fstab 文件详解

```bash
# /etc/fstab 文件格式
# <设备>            <挂载点>  <文件系统>  <选项>    <dump> <fsck>
UUID=xxx-xxx        /         ext4        errors=remount-ro 0     1
UUID=yyy-yyy        /boot     ext4        defaults          0     2
UUID=zzz-zzz        /data     xfs         defaults,noatime  0     2
tmpfs               /tmp      tmpfs       defaults,size=2G  0     0
//nas/share         /mnt/nas  cifs        credentials=/etc/nas.cred 0 0

# 常用挂载选项
defaults          = rw,suid,dev,exec,auto,nouser,async
noatime           = 不更新访问时间（性能优化）
nodiratime        = 不更新目录访问时间
noexec            = 禁止执行文件（安全加固）
nosuid            = 禁止 SUID（安全加固）
ro                = 只读挂载
rw                = 读写挂载
discard           = SSD TRIM 支持

# 验证 fstab 配置
mount -a                  # 挂载 fstab 中所有未挂载的设备
findmnt --verify          # 验证 fstab 语法

# 获取设备 UUID
blkid /dev/sda1
lsblk -f
```

#### 5.3 挂载实战

```bash
# 1. 查看当前挂载
df -hT
findmnt
mount | column -t

# 2. 挂载新磁盘
# 查看可用磁盘
lsblk
fdisk -l

# 创建分区
fdisk /dev/sdb
# n → p → 1 → 回车 → 回车 → w

# 创建文件系统
mkfs.ext4 /dev/sdb1

# 创建挂载点并挂载
mkdir -p /data
mount /dev/sdb1 /data

# 添加到 fstab（开机自动挂载）
echo "UUID=$(blkid -s UUID -o value /dev/sdb1) /data ext4 defaults,noatime 0 2" >> /etc/fstab

# 3. 绑定挂载（Bind Mount）
mount --bind /source/dir /target/dir
# 将一个目录挂载到另一个位置

# 4. tmpfs 挂载
mount -t tmpfs -o size=2G tmpfs /tmp
# 内存文件系统，重启后清空

# 5. NFS 挂载
apt install nfs-common
mount -t nfs server:/share /mnt/nfs

# 6. 查看挂载选项
cat /proc/mounts | grep /data
findmnt /data
```

---

### 6. SRE 实战：磁盘满排查

#### 6.1 磁盘满的常见原因

```
磁盘满排查思路：

磁盘满
├── 1. 文件太大
│   ├── 日志文件过大（/var/log/）
│   ├── 数据库文件过大（/var/lib/mysql/）
│   ├── 临时文件过大（/tmp/）
│   └── 用户上传文件过多（/home/）
│
├── 2. 被删除的文件未释放
│   └── 进程持有已删除文件的文件描述符
│       → 文件空间不会释放
│       → du 看不到，但 df 显示满
│
├── 3. inode 耗尽
│   └── 磁盘空间还有，但 inode 用完了
│       → 通常是大量小文件导致
│
└── 4. 挂载问题
    └── 某个目录被当作挂载点，原有文件被"隐藏"
```

#### 6.2 完整排查流程

```bash
#!/bin/bash
# disk_check.sh - 磁盘空间排查脚本

echo "===== 磁盘使用概览 ====="
df -hT

echo ""
echo "===== inode 使用情况 ====="
df -i

echo ""
echo "===== 各分区使用率 TOP 10 ====="
df -h | awk 'NR>1 {print $5, $6}' | sort -rn | head -10

echo ""
echo "===== 根目录下各目录占用 ====="
du -sh /* 2>/dev/null | sort -rh | head -15

echo ""
echo "===== /var/log 下文件大小 TOP 20 ====="
find /var/log -type f -exec ls -lhS {} + 2>/dev/null | head -20

echo ""
echo "===== 大于 100MB 的文件 TOP 20 ====="
find / -type f -size +100M -exec ls -lhS {} + 2>/dev/null | head -20

echo ""
echo "===== 已删除但未释放的文件 ====="
lsof +L1 2>/dev/null | awk '$7 > 1048576 {print $2, $1, $7, $9}' | sort -k3 -rn | head -10

echo ""
echo "===== /tmp 目录占用 ====="
du -sh /tmp/* 2>/dev/null | sort -rh | head -10

echo ""
echo "===== Docker 占用 ====="
docker system df 2>/dev/null || echo "Docker 未安装"

echo ""
echo "===== apt/yum 缓存 ====="
du -sh /var/cache/apt 2>/dev/null || du -sh /var/cache/yum 2>/dev/null
```

#### 6.3 清理策略

```bash
# 1. 清理日志（不删除，清空内容）
> /var/log/nginx/access.log
> /var/log/nginx/error.log
cat /dev/null > /var/log/syslog

# 2. 清理 journal 日志
journalctl --vacuum-size=500M      # 保留最近 500MB
journalctl --vacuum-time=7d        # 保留最近 7 天

# 3. 清理包管理器缓存
apt clean                          # 清理所有下载的包
apt autoremove -y                  # 清理不需要的依赖
dnf clean all                      # RHEL 系

# 4. 清理已删除但未释放的文件
# 找到进程
lsof +L1 | grep deleted
# 方法1：重启进程
systemctl restart nginx
# 方法2：截断文件
echo > /proc/<PID>/fd/<FD>

# 5. 清理 Docker
docker system prune -a             # 清理所有未使用的资源
docker volume prune                # 清理未使用的卷

# 6. 查找并清理大文件
find /var/log -name "*.gz" -mtime +30 -delete
find /tmp -type f -mtime +7 -delete

# 7. 配置 logrotate 防止再次发生
cat > /etc/logrotate.d/myapp << 'EOF'
/var/log/myapp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 www-data www-data
    postrotate
        systemctl reload myapp
    endscript
}
EOF
```

---

### 7. SRE 实战：/var/log 管理

#### 7.1 日志轮转配置

```bash
# logrotate 配置文件位置
/etc/logrotate.conf              # 全局配置
/etc/logrotate.d/                # 各服务的配置

# Nginx 日志轮转配置
cat /etc/logrotate.d/nginx
/var/log/nginx/*.log {
    daily                        # 每天轮转
    missingok                    # 日志不存在时不报错
    rotate 14                    # 保留 14 份
    compress                     # 压缩旧日志
    delaycompress                # 延迟一天压缩
    notifempty                   # 空日志不轮转
    create 0640 www-data adm     # 创建新日志的权限
    sharedscripts                # 所有日志轮转后只执行一次脚本
    postrotate                   # 轮转后执行
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}

# 手动测试 logrotate
logrotate -d /etc/logrotate.d/nginx    # 调试模式（不实际执行）
logrotate -f /etc/logrotate.d/nginx    # 强制执行
logrotate -v /etc/logrotate.conf       # 详细输出

# 查看 logrotate 状态
cat /var/lib/logrotate/status
```

#### 7.2 journalctl 日志管理

```bash
# 查看日志
journalctl                          # 所有日志
journalctl -u nginx                 # Nginx 服务日志
journalctl -u nginx --since "1 hour ago"
journalctl -u nginx --since "2024-01-01" --until "2024-01-02"
journalctl -p err                   # 错误级别以上
journalctl -k                       # 内核日志
journalctl -b                       # 当前启动的日志
journalctl -f                       # 实时跟踪

# 日志级别
# emerg(0) > alert(1) > crit(2) > err(3) > warning(4) > notice(5) > info(6) > debug(7)

# 配置 journal 持久化
mkdir -p /var/log/journal
systemd-tmpfiles --create --prefix /var/log/journal
systemctl restart systemd-journald

# 配置 journal 大小限制
cat > /etc/systemd/journald.conf << 'EOF'
[Journal]
SystemMaxUse=1G            # 最大使用 1GB
SystemMaxFileSize=100M     # 单个日志文件最大 100MB
MaxRetentionSec=30day      # 保留 30 天
Compress=yes               # 压缩日志
EOF

systemctl restart systemd-journald
```

---

## 💻 实战练习

### 练习 1：文件系统探索

**目标**：通过命令行探索文件系统的各种信息。

```bash
# 1. 查看所有已挂载的文件系统及其类型
df -Th

# 2. 查看 / 目录的 inode 使用情况
df -i /

# 3. 查看 /etc/passwd 文件的详细 inode 信息
stat /etc/passwd

# 4. 创建一个文件并查看其 inode
touch /tmp/test_inode.txt
ls -li /tmp/test_inode.txt

# 5. 创建硬链接并验证 inode 相同
ln /tmp/test_inode.txt /tmp/test_hardlink.txt
ls -li /tmp/test_inode.txt /tmp/test_hardlink.txt

# 6. 创建软链接并验证 inode 不同
ln -s /tmp/test_inode.txt /tmp/test_symlink.txt
ls -li /tmp/test_inode.txt /tmp/test_symlink.txt

# 7. 删除源文件，观察硬链接和软链接的行为
rm /tmp/test_inode.txt
cat /tmp/test_hardlink.txt    # 仍然可以读取
cat /tmp/test_symlink.txt     # 报错：No such file or directory
```

### 练习 2：磁盘满排查实战

**目标**：模拟磁盘满场景并进行排查。

```bash
# 1. 创建一个测试分区（使用 loop 设备）
dd if=/dev/zero of=/tmp/test_disk.img bs=1M count=100
mkfs.ext4 /tmp/test_disk.img
mkdir -p /mnt/test
mount /tmp/test_disk.img /mnt/test

# 2. 模拟磁盘满
dd if=/dev/zero of=/mnt/test/fill.txt bs=1M count=95

# 3. 验证磁盘满
df -h /mnt/test

# 4. 排查大文件
du -sh /mnt/test/* | sort -rh
find /mnt/test -type f -size +10M -exec ls -lh {} +

# 5. 清理
rm /mnt/test/fill.txt
umount /mnt/test
rm /tmp/test_disk.img
```

### 练习 3：FHS 目录结构探索

**目标**：了解系统中各个目录的作用。

```bash
# 1. 列出 /etc 下的配置文件
ls /etc/ | head -30

# 2. 查看 /var/log 下的日志文件
ls -lhS /var/log/ | head -20

# 3. 查看 /proc/cpuinfo 中的 CPU 信息
grep -c processor /proc/cpuinfo    # CPU 核心数
grep "model name" /proc/cpuinfo | head -1

# 4. 查看 /proc/meminfo 中的内存信息
grep -E "MemTotal|MemFree|MemAvailable" /proc/meminfo

# 5. 查看 /proc/loadavg
cat /proc/loadavg

# 6. 查看 /proc/<PID>/ 目录结构（用 bash 的 PID）
ls /proc/$$/ 

# 7. 查看系统支持的文件系统
cat /proc/filesystems
```

---

## 🎯 面试题精选

### 面试题 1：什么是 inode？inode 耗尽怎么排查？

**参考答案**：

**inode 是什么**：
inode（索引节点）是文件系统中用于存储文件元数据的数据结构。每个文件/目录都有一个唯一的 inode，包含文件类型、权限、所有者、大小、时间戳、数据块指针等信息，但不包含文件名（文件名存储在目录的 dentry 中）。

**inode 耗尽排查**：
```bash
# 1. 确认 inode 使用情况
df -i

# 2. 找出占用 inode 最多的目录
for d in /*; do
    echo "$(find "$d" -xdev 2>/dev/null | wc -l) $d"
done | sort -rn | head -10

# 3. 常见原因
# - /var/spool/mail/ 或 /var/spool/postfix/ 大量小文件
# - /tmp/ 大量临时文件
# - session 文件（/var/lib/php/sessions/）
# - 小文件过多的应用

# 4. 清理
find /var/spool/mail -type f -mtime +30 -delete
find /tmp -type f -mtime +7 -delete
```

### 面试题 2：硬链接和软链接有什么区别？

**参考答案**：

| 特性 | 硬链接 | 软链接 |
|------|--------|--------|
| inode | 共享同一个 inode | 有独立的 inode |
| 跨文件系统 | 不能 | 可以 |
| 链接目录 | 不能 | 可以 |
| 源文件删除 | 链接仍有效 | 链接失效（断链） |
| 存储内容 | 不额外占用空间 | 存储目标路径 |
| 文件大小 | 与源文件相同 | 路径字符串长度 |

### 面试题 3：ext4、xfs、btrfs 各自适合什么场景？

**参考答案**：

- **ext4**：通用场景，成熟稳定，适合 Web 服务器、应用服务器
- **xfs**：大文件和高并发 I/O 场景，如视频存储、大数据处理、数据库
- **btrfs**：需要快照、压缩、数据校验的场景，如 NAS、备份服务器

### 面试题 4：如何排查"磁盘满但找不到大文件"的问题？

**参考答案**：

这种情况通常是"已删除但未释放"的文件导致的。

```bash
# 找到已删除但被进程持有的文件
lsof +L1 | sort -k7 -rn | head -10

# 解决方法
# 方法1：重启持有文件的进程
systemctl restart <service>

# 方法2：截断文件描述符
echo > /proc/<PID>/fd/<FD>

# 方法3：使用 gdb 截断（不推荐，但可以不重启进程）
gdb -p <PID> -ex "call close(<FD>)" -ex quit
```

### 面试题 5：/proc 文件系统有什么作用？

**参考答案**：

/proc 是一个虚拟文件系统，不占用磁盘空间，由内核动态生成。主要作用：

1. **查看系统信息**：`/proc/cpuinfo`（CPU）、`/proc/meminfo`（内存）、`/proc/loadavg`（负载）
2. **查看进程信息**：`/proc/<PID>/` 目录下有进程的详细信息（命令行、环境变量、文件描述符等）
3. **修改内核参数**：通过 `/proc/sys/` 动态修改内核参数（如 `net.core.somaxconn`）
4. **系统监控**：`top`、`free`、`vmstat` 等工具底层都读取 /proc

### 面试题 6：VFS 的作用是什么？

**参考答案**：

VFS（虚拟文件系统）是 Linux 内核中的抽象层，作用是：

1. **统一接口**：为所有文件系统提供统一的系统调用接口（open、read、write、close）
2. **文件系统无关**：应用程序不需要知道底层使用的是什么文件系统
3. **支持多种文件系统**：ext4、xfs、btrfs、NFS、proc、sysfs 等
4. **路径解析**：通过 dentry cache 加速文件路径查找

VFS 的四大对象：superblock（文件系统）、inode（文件元数据）、dentry（目录项）、file（打开的文件）。

### 面试题 7：如何优化文件系统性能？

**参考答案**：

1. **选择合适的文件系统**：大文件用 xfs，通用用 ext4
2. **调整挂载选项**：`noatime`（不更新访问时间）、`nodiratime`
3. **调整 I/O 调度器**：SSD 用 `none`/`noop`，HDD 用 `mq-deadline`
4. **调整 readahead**：`blockdev --setra 4096 /dev/sda`
5. **使用 SSD**：启用 TRIM（`discard` 挂载选项）
6. **调整 inode 缓存**：增加 `vm.vfs_cache_pressure`
7. **定期碎片整理**：ext4 用 `e4defrag`

---

## 📚 深入阅读

### 官方文档
- [Linux Kernel Documentation - Filesystems](https://www.kernel.org/doc/html/latest/filesystems/)
- [ext4 Wiki](https://ext4.wiki.kernel.org/)
- [XFS Documentation](https://xfs.org/index.php/Documentation)
- [btrfs Wiki](https://btrfs.wiki.kernel.org/)
- [FHS 3.0 Specification](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)

### 推荐书籍
- 《Linux 内核设计与实现》- 文件系统章节
- 《深入理解 Linux 内核》- VFS 和 ext4 章节
- 《鸟哥的 Linux 私房菜》- 文件系统和磁盘管理

### 技术博客
- [Brendan Gregg - Linux File Systems](http://www.brendangregg.com/linuxperf.html)
- [LWN.net - Filesystem topics](https://lwn.net/Kernel/Index/)

---

## ✅ 自检清单

### 理论检查点
- [ ] 能画出 VFS 架构图，说明 superblock、inode、dentry、file 四大对象
- [ ] 能解释文件打开的完整流程
- [ ] 能对比 ext4、xfs、btrfs 的特性和适用场景
- [ ] 能说明 ext4 的日志机制（data=journal/ordered/writeback）
- [ ] 能详细说明 FHS 标准中各目录的用途
- [ ] 能解释 /proc 和 /sys 的作用和常用文件
- [ ] 能从 inode 层面解释硬链接和软链接的区别
- [ ] 能描述文件系统挂载的原理

### 实操检查点
- [ ] 能使用 df、du、stat 等命令查看文件系统信息
- [ ] 能创建和管理 ext4、xfs、btrfs 文件系统
- [ ] 能配置 /etc/fstab 实现开机自动挂载
- [ ] 能排查磁盘满和 inode 耗尽问题
- [ ] 能配置 logrotate 进行日志轮转
- [ ] 能使用 journalctl 查看和管理日志
- [ ] 能创建和管理硬链接和软链接
- [ ] 能通过 /proc 获取系统和进程信息

---

*Day 02 完成 | 2026-04-25*
