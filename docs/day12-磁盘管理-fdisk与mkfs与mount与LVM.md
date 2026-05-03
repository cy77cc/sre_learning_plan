# Day 12: 磁盘管理 — fdisk/mkfs/mount/LVM

> 📅 日期：2026-04-28
> 📖 学习主题：磁盘管理 — fdisk/mkfs/mount/LVM
> ⏰ 计划学习时间：3-4 小时
> 📋 前置知识：Day 01-11（Linux 基础命令、文件系统、用户管理、systemd）

---

## 🎯 学习目标

完成 Day 12 的学习后，你应该掌握：
- 理解 Linux 存储栈的完整架构（块设备层 → 分区层 → 文件系统层 → VFS 层）
- 能够使用 fdisk/parted 对磁盘进行分区（MBR 和 GPT）
- 掌握 ext4/xfs/btrfs 三种文件系统的差异和适用场景
- 精通 mount/umount 和 /etc/fstab 的配置（理解每个字段的含义）
- 掌握 LVM 的完整工作流程：PV → VG → LV 创建、扩容、快照
- 理解 RAID 级别（0/1/5/6/10）的原理和选择策略
- 能够处理生产环境中的磁盘报警、扩容、I/O 调优问题

---

## 📖 核心知识点

### 1. Linux 存储栈架构

Linux 的存储 I/O 路径是一个分层架构，从应用程序到物理磁盘需要经过多个层次：

```
  ┌─────────────────────────────────────────────────┐
  │            用户空间应用程序                        │
  │         (read() / write() 系统调用)               │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │              VFS 层（虚拟文件系统）                │
  │    统一接口：vfs_read() / vfs_write()             │
  │    支持 ext4, xfs, btrfs, nfs 等                  │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │           文件系统层（ext4 / xfs / btrfs）         │
  │    负责：元数据管理、日志、块分配、inode 管理       │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │              块设备层（Block Layer）               │
  │    ├── 通用块层：I/O 调度、合并、请求队列          │
  │    ├── Device Mapper：LVM、RAID、加密（dm-crypt）  │
  │    └── 多路径（multipath）                        │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │           设备驱动层（AHCI/NVMe/SCSI/MegaRAID）   │
  └──────────────────────┬──────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────┐
  │           物理存储（HDD / SSD / NVMe）            │
  └─────────────────────────────────────────────────┘
```

#### 1.1 关键层次说明

| 层次 | 组件 | 职责 |
|------|------|------|
| VFS 层 | 虚拟文件系统 | 提供统一的文件操作接口，屏蔽底层文件系统差异 |
| 文件系统层 | ext4/xfs/btrfs | 管理文件元数据、目录结构、数据块分配、日志 |
| 通用块层 | I/O 调度器 | 请求合并、排序、调度，优化磁盘访问模式 |
| Device Mapper | LVM/RAID/dm-crypt | 块设备的逻辑抽象（卷管理、冗余、加密） |
| 设备驱动 | ahci/nvme/megaraid | 与硬件通信的驱动程序 |

#### 1.2 查看存储栈信息

```bash
# 查看所有块设备
lsblk

# 输出示例：
# NAME   MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT
# sda      8:0    0   100G  0 disk
# ├─sda1   8:1    0     1G  0 part /boot
# ├─sda2   8:2    0    50G  0 part /
# └─sda3   8:3    0    49G  0 part
#   └─vg0-lv_data 253:0  0  49G  0 lvm  /data
# sdb      8:16   0   500G  0 disk
# sr0     11:0    1  1024M  0 rom

# 查看块设备详细信息（文件系统类型和 UUID）
lsblk -f
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,UUID

# 区分 HDD 和 SSD
lsblk -d -o NAME,SIZE,ROTA,MODEL
# ROTA=1 → 旋转磁盘(HDD)，ROTA=0 → 固态硬盘(SSD/NVMe)

# 查看磁盘分区表类型
sudo fdisk -l /dev/sda | grep "Disklabel type"
# Disklabel type: gpt  或  dos (MBR)

# 查看设备的 sysfs 属性
ls -la /sys/block/sda/
cat /sys/block/sda/queue/scheduler          # I/O 调度器
cat /sys/block/sda/queue/nr_requests        # 队列深度
cat /sys/block/sda/queue/rotational         # 是否旋转盘（1=HDD, 0=SSD）
cat /sys/block/sda/queue/hw_sector_size     # 硬件扇区大小

# 查看 I/O 统计
iostat -x 1 5       # 每秒刷新，共 5 次
cat /proc/diskstats  # 内核级磁盘统计

# 查看 SCSI 设备信息
cat /proc/scsi/scsi
lsscsi               # 更友好的输出
```

#### 1.3 设备命名规则

```
/dev/sda    ← 第一块 SCSI/SATA 磁盘（a, b, c...）
/dev/sda1   ← 第一块磁盘的第一个分区
/dev/nvme0n1     ← 第一块 NVMe 控制器的第一块命名空间
/dev/nvme0n1p1   ← NVMe 磁盘的第一个分区
/dev/vda    ← virtio 磁盘（虚拟机常见）
/dev/xvda   ← Xen 虚拟磁盘（AWS EC2 早期实例）
/dev/md0    ← 软件 RAID 设备
/dev/dm-0   ← Device Mapper 设备（LVM）
/dev/mapper/vg0-lv_root  ← LVM 逻辑卷（符号链接）
/dev/loop0  ← 回环设备（挂载 ISO、虚拟磁盘文件）
```

**块设备 vs 字符设备**：磁盘是块设备（`b` 类型），以固定大小数据块为单位读写，支持随机访问，内核做 I/O 调度和缓存。

```bash
ls -la /dev/sda
# brw-rw---- 1 root disk 8, 0 /dev/sda
# ↑ 'b'=块设备，'8,0'=主设备号,从设备号
```

---

### 2. 磁盘分区：fdisk vs parted

#### 2.1 MBR vs GPT 对比

```
MBR (512 字节，第 1 扇区)：
┌─────────────────┬──────────────┬──────────┐
│ Boot Code (446B)│ 分区表 (64B) │ 0x55AA   │
│                 │ 4×16B = 4分区│ 签名     │
└─────────────────┴──────────────┴──────────┘

GPT (多扇区，有备份)：
┌──────────────┬──────────────┬──────────────┬─────────────┐
│ 保护性 MBR    │ GPT Header    │ 128分区表项  │ 用户数据区   │
│              │ (LBA 1)       │ (LBA 2-33)   │             │
│              │ CRC32 校验    │ 含 GUID      │ 备份表+头部  │
└──────────────┴──────────────┴──────────────┴─────────────┘
```

| 维度 | MBR | GPT | 建议 |
|------|-----|-----|------|
| 最大分区数 | 4 主分区（或 3 主+1 扩展） | 128 分区（默认） | 多分区选 GPT |
| 最大磁盘 | 2 TB | 9.4 ZB | >2TB 必须 GPT |
| 数据校验 | 无 | CRC32 | GPT 更安全 |
| 备份机制 | 无 | 头尾各一份 | GPT 可恢复 |
| UEFI 启动 | 兼容模式 | 原生支持 | UEFI 选 GPT |
| 引导代码 | 446 字节 | 专用 EFI 分区 | GPT 更灵活 |

**MBR 分区表每条记录 16 字节：**
```
  - 1 字节：引导标志（0x80=活动分区）
  - 3 字节：CHS 起始地址
  - 1 字节：分区类型（0x83=Linux, 0x8e=LVM, 0x82=swap, 0xfd=RAID）
  - 3 字节：CHS 结束地址
  - 4 字节：LBA 起始扇区
  - 4 字节：分区大小（扇区数）
```

#### 2.2 fdisk 详解（MBR 首选工具）

```bash
# 交互式操作磁盘
sudo fdisk /dev/sdb

# 常用交互命令：
# m    - 显示帮助
# p    - 打印分区表
# n    - 新建分区（选 p=主分区, e=扩展分区, 指定起止扇区或大小如 +100G）
# d    - 删除分区
# t    - 更改分区类型（L 列出所有类型代码）
# w    - 写入并退出（不可逆！）
# q    - 不保存退出

# 非交互式创建分区（脚本中使用）
echo -e "n\np\n1\n\n+20G\nw" | sudo fdisk /dev/sdb

# 更推荐的脚本化分区方式
sudo sfdisk /dev/sdb <<EOF
label: gpt
name=boot,size=512M,type=EFI
name=root,size=50G,type=Linux
name=data,size=100%,type=Linux
EOF

# 让内核重新读取分区表
sudo partprobe /dev/sdb

# 查看分区信息
sudo fdisk -l /dev/sdb
```

#### 2.3 parted 详解（GPT 首选工具）

```bash
# 交互式操作
sudo parted /dev/sdb

# parted 交互命令：
# print                    - 显示分区表
# mklabel gpt              - 创建 GPT 分区表
# mkpart primary ext4 0% 100%  - 创建分区
# rm 1                     - 删除分区 1
# resizepart 1 100%        - 调整分区大小
# set 1 lvm on             - 设置 LVM 标志

# 非交互式创建 GPT 分区
sudo parted /dev/sdb mklabel gpt
sudo parted /dev/sdb mkpart primary ext4 0% 50%
sudo parted /dev/sdb mkpart primary xfs 50% 100%

# 查看信息
sudo parted /dev/sdb print

# 输出示例：
# Model: ATA VBOX HARDDISK (scsi)
# Disk /dev/sdb: 107GB
# Sector size (logical/physical): 512B/512B
# Partition Table: gpt
# Disk Flags:
#
# Number  Start   End     Size    File system  Name     Flags
#  1      1049kB  53.7GB  53.7GB  ext4         primary
#  2      53.7GB  107GB   53.7GB  xfs          primary
```

#### 2.4 分区方案最佳实践

```
生产服务器推荐分区方案（GPT）：
┌──────────┬──────────────┬─────────────────────────────┐
│ 分区      │ 挂载点       │ 说明                         │
├──────────┼──────────────┼─────────────────────────────┤
│ /dev/sda1 │ /boot/efi    │ 512MB，EFI 系统分区（UEFI）   │
│ /dev/sda2 │ /boot        │ 1GB，存放内核和引导文件       │
│ /dev/sda3 │ (swap)       │ 内存的 1-2 倍或固定 8-16GB   │
│ /dev/sda4 │ /            │ 20-50GB，系统根分区           │
│ /dev/sda5 │ /var         │ 日志、临时数据，大小按需      │
│ /dev/sda6 │ /var/log     │ 日志分区，单独隔离            │
│ /dev/sda7 │ /home        │ 用户数据（可选）              │
│ /dev/sda8 │ /data        │ 应用数据，使用 LVM 管理       │
└──────────┴──────────────┴─────────────────────────────┘

为什么分开？
- /var/log 单独分区：日志暴涨不会影响根分区
- /tmp 单独分区（或 tmpfs）：临时文件不占用系统空间
- /data 使用 LVM：方便后续在线扩容
- /boot 独立分区：内核更新不受其他分区影响
```

---

### 3. 文件系统格式化：mkfs

#### 3.1 ext4 vs xfs vs btrfs 对比

| 特性 | ext4 | xfs | btrfs |
|------|------|-----|-------|
| 最大文件大小 | 16 TB | 8 EB | 16 EB |
| 最大分区大小 | 1 EB | 8 EB | 16 EB |
| 日志机制 | 数据日志 / 有序日志 | 元数据日志 | Copy-on-Write（无传统日志） |
| 在线扩容 | 支持 | 支持 | 支持 |
| 在线缩容 | 支持 | **不支持** | 支持 |
| 快照 | 不支持（需 LVM） | 不支持 | 原生支持 |
| 透明压缩 | 不支持 | 不支持 | 支持（zstd/lzo） |
| 校验和 | 仅元数据 | 不支持 | 数据+元数据 |
| 碎片整理 | e4defrag | xfs_fsr | btrfs balance |
| 适用场景 | 通用、传统服务器 | 大文件、数据库 | 需要快照/压缩/校验 |
| CentOS/RHEL 默认 | CentOS 6 | CentOS 7+ | 不推荐生产使用 |

#### 3.2 日志机制深入

**ext4 日志模式：**
```bash
# 三种日志模式
# journal   - 数据和元数据都写日志（最安全，最慢）
# ordered   - 只写元数据日志，数据先于元数据提交（默认，推荐）
# writeback - 只写元数据日志，数据顺序不保证（最快，风险较高）

# 挂载时指定日志模式
sudo mount -o data=ordered /dev/sdb1 /data
sudo mount -o data=journal /dev/sdb1 /data

# 查看当前日志模式
sudo tune2fs -l /dev/sdb1 | grep "Filesystem features"
# 或
mount | grep sdb1   # 输出中的 data=ordered 就是日志模式
```

**XFS 日志：**
```bash
# XFS 使用元数据日志（journal），日志可以放在外部设备
# 内部日志（默认）：日志在同一个分区
# 外部日志：日志放在高速设备（如 SSD），提升性能

# 创建带外部日志的 XFS
sudo mkfs.xfs -l logdev=/dev/sdc1 /dev/sdb1
```

**Btrfs Copy-on-Write：**
```
Btrfs 不使用传统日志，而是使用 Copy-on-Write（CoW）机制：

传统文件系统写入流程：
  1. 数据写入日志区
  2. 数据写入实际位置
  3. 更新元数据
  4. 清除日志

Btrfs CoW 写入流程：
  1. 数据写入新位置（不覆盖旧数据）
  2. 更新元数据指针（指向新位置）
  3. 原子提交

优势：写入中断时，旧数据仍然完好，无需日志回放
```

#### 3.3 mkfs 命令详解

```bash
# 格式化为 ext4
sudo mkfs.ext4 /dev/sdb1
sudo mkfs.ext4 -L "data" -b 4096 -i 8192 /dev/sdb1
# -L 卷标    -b 块大小    -i 每多少字节一个 inode

# 高级参数
sudo mkfs.ext4 \
    -b 4096 \           # 块大小 4KB（大文件选 4K，小文件可选 1K）
    -i 16384 \          # 每 16KB 一个 inode（小文件场景调小此值）
    -m 1 \              # root 保留块 1%（默认 5%，大磁盘可降为 1-2%）
    -E lazy_itable_init=0 \  # 立即初始化 inode 表
    /dev/sdb1

# 格式化为 XFS
sudo mkfs.xfs /dev/sdb1
sudo mkfs.xfs -L "data" -f /dev/sdb1      # -f 强制覆盖

# 格式化为 Btrfs
sudo mkfs.btrfs /dev/sdb1
sudo mkfs.btrfs -L "data" -d single -m single /dev/sdb1
# -d 数据配置   -m 元数据配置   single=无冗余, raid1=镜像

# 调整文件系统参数
sudo tune2fs -c 30 /dev/sdb1           # 每 30 次挂载后强制检查
sudo tune2fs -i 604800 /dev/sdb1       # 每 604800 秒（7 天）检查一次
sudo tune2fs -m 2 /dev/sdb1            # 预留空间比例设为 2%（默认 5%）
sudo tune2fs -l /dev/sdb1              # 查看文件系统超级块信息

# 查看 XFS 参数
sudo xfs_info /dev/sdb1

# 查看 Btrfs 参数
sudo btrfs filesystem show /dev/sdb1
```

#### 3.4 inode 与磁盘空间

```bash
# inode 耗尽问题
# 每个文件/目录占用一个 inode，inode 用完后即使有空间也无法创建文件

# 查看 inode 使用情况
df -i

# 输出示例：
# Filesystem      Inodes  IUsed   IFree IUse% Mounted on
# /dev/sda1      6553600  12345 6541255    1% /
# /dev/sdb1      3276800 3276800       0  100% /data  ← inode 耗尽！

# 常见原因：大量小文件（邮件队列、session 文件、缓存）
# 解决：删除小文件或重新格式化时增加 inode 数

# 重新格式化时指定 inode 比例
sudo mkfs.ext4 -i 4096 /dev/sdb1   # 每 4096 字节一个 inode（增加 inode 数量）
```

---

### 4. 挂载管理：mount/umount

#### 4.1 mount 命令详解

```bash
# 基本挂载
sudo mount /dev/sdb1 /mnt/data

# 指定文件系统类型
sudo mount -t ext4 /dev/sdb1 /mnt/data
sudo mount -t xfs /dev/sdb1 /mnt/data

# 挂载选项
sudo mount -o rw,noatime,nodiratime /dev/sdb1 /mnt/data

# 查看所有挂载
mount                  # 传统输出
findmnt                # 树形输出（推荐）
findmnt -t ext4        # 只显示特定文件系统类型

# 卸载
sudo umount /mnt/data
sudo umount -l /mnt/data    # 懒卸载（busy 时先断开，进程结束后真正卸载）
sudo umount -f /mnt/data    # 强制卸载（NFS 场景）
```

#### 4.2 常用挂载选项

| 选项 | 说明 | 适用场景 |
|------|------|---------|
| rw/ro | 读写/只读 | ro 用于只读数据卷 |
| noatime | 不更新文件访问时间 | 性能优化（减少写操作） |
| nodiratime | 不更新目录访问时间 | 性能优化 |
| noexec | 禁止执行文件 | /tmp、/var/tmp 安全加固 |
| nosuid | 忽略 SUID/SGID 位 | /home、/tmp 安全加固 |
| nodev | 不解释设备文件 | /tmp、/home 安全加固 |
| discard | 启用 SSD TRIM | SSD 磁盘必备 |
| barrier=0/1 | 禁用/启用写屏障 | 数据库临时分区（谨慎） |
| data=journal/ordered/writeback | ext4 日志模式 | 按可靠性需求选择 |
| errors=continue/remount-ro/panic | 错误处理策略 | 生产环境建议 remount-ro |

#### 4.3 Bind Mount（绑定挂载）

```bash
# 将一个目录挂载到另一个位置（两个路径看到相同内容）
sudo mount --bind /data/web /var/www/html

# 只读绑定挂载
sudo mount --bind /data/web /var/www/html
sudo mount -o remount,ro,bind /var/www/html

# 常见用途：
# 1. chroot 环境中提供 /proc、/dev、/sys
# 2. 容器中挂载宿主机目录
# 3. 将不同分区的目录映射到标准路径

# 在 chroot 中使用 bind mount
sudo mount --bind /proc  /mnt/chroot/proc
sudo mount --bind /dev   /mnt/chroot/dev
sudo mount --bind /sys   /mnt/chroot/sys
```

#### 4.4 tmpfs（内存文件系统）

```bash
# 创建 tmpfs（数据存储在内存中，重启丢失）
sudo mount -t tmpfs -o size=2G tmpfs /mnt/ramdisk

# 常见用途：
# /tmp        - 临时文件
# /run        - 运行时数据
# /dev/shm    - 共享内存

# 查看系统 tmpfs 挂载
df -hT | grep tmpfs

# 查看 tmpfs 使用情况
cat /proc/mounts | grep tmpfs
```

#### 4.5 /etc/fstab 详解

```bash
# fstab 文件格式（6 个字段）：
# <设备>    <挂载点>    <文件系统>    <选项>    <dump>    <fsck>

# 示例：
UUID=a1b2c3d4-e5f6-7890-abcd-ef1234567890  /        ext4  defaults        1 1
UUID=f6e5d4c3-b2a1-0987-fedc-ba0987654321  /boot    ext4  defaults        1 2
UUID=12345678-abcd-ef01-2345-6789abcdef01  /data    xfs   defaults,noatime 0 0
UUID=abcdef01-2345-6789-abcd-ef0123456789  none     swap  sw              0 0
tmpfs                                      /tmp     tmpfs defaults,size=2G 0 0
```

**fstab 各字段含义：**

| 字段 | 说明 | 常见值 |
|------|------|--------|
| 设备 | 要挂载的设备 | UUID=xxx, /dev/sdb1, LABEL=data, //server/share |
| 挂载点 | 目录路径 | /, /data, /mnt/nas（swap 用 none） |
| 文件系统 | 文件系统类型 | ext4, xfs, btrfs, nfs, cifs, tmpfs, swap |
| 选项 | 挂载选项 | defaults, noatime, ro, rw, nosuid, noexec |
| dump | dump 备份标志 | 0=不备份, 1=需要备份（现在很少用） |
| fsck | 检查顺序 | 0=不检查, 1=首先检查（仅根分区）, 2=其次检查 |

```bash
# 测试 fstab（不实际挂载，检查语法错误）
sudo mount -a            # 挂载 fstab 中所有未挂载的条目
sudo findmnt --verify    # 验证 fstab 语法（systemd 工具）

# 使用 UUID 而非设备名（设备名可能变化）
sudo blkid               # 查看所有设备的 UUID
sudo blkid /dev/sdb1     # 查看特定设备
```

**fstab 常见错误和修复：**
```bash
# 错误：fstab 配置错误导致系统无法启动
# 修复步骤：
# 1. 启动进入救援模式或 Live CD
# 2. 挂载根分区
sudo mount /dev/sda2 /mnt
# 3. 编辑 fstab
sudo vim /mnt/etc/fstab
# 4. 注释掉错误行，保存退出
# 5. 重启
sudo reboot

# 另一种方法（GRUB 菜单编辑）：
# 1. GRUB 菜单按 'e' 编辑启动参数
# 2. 在 linux 行末尾添加 init=/bin/bash
# 3. Ctrl+X 启动进入单用户 shell
# 4. mount -o remount,rw /
# 5. 编辑 /etc/fstab 注释错误行
# 6. exec /sbin/init 继续启动

# 错误：fstab 中的 NFS 挂载失败导致启动卡住
# 解决：添加 nofail 选项
# server:/share  /mnt/nfs  nfs  defaults,nofail,_netdev  0 0
# nofail  - 挂载失败不阻止启动
# _netdev - 等待网络就绪后再挂载
```

---

### 5. LVM 深入讲解

#### 5.1 LVM 架构

```
  ┌─────────────────────────────────────────────────────────────┐
  │                        应用层                                │
  │               /home    /var    /data    /backup              │
  └───────┬─────────┬────────┬─────────┬───────────────────────┘
          │         │        │         │
  ┌───────┴─────────┴────────┴─────────┴───────────────────────┐
  │                    逻辑卷 (LV)                               │
  │    lv_home   lv_var   lv_data   lv_backup                   │
  │    50GB      20GB     100GB     200GB                        │
  └───────────────┬─────────────────────┬──────────────────────┘
                  │                     │
  ┌───────────────┴─────────────────────┴──────────────────────┐
  │                    卷组 (VG)                                 │
  │                    vg0 (总容量 500GB)                         │
  │    ┌─────────────────────────────────────────────┐          │
  │    │  物理区域 (PE) - 分配单元                      │          │
  │    │  PE 大小默认 4MB，可配置                      │          │
  │    └─────────────────────────────────────────────┘          │
  └──────────┬───────────────┬───────────────┬─────────────────┘
             │               │               │
  ┌──────────┴───────┐ ┌────┴────────┐ ┌───┴──────────┐
  │   物理卷 (PV)     │ │   物理卷     │ │   物理卷      │
  │   /dev/sda3      │ │  /dev/sdb1  │ │  /dev/sdc1   │
  │   100GB          │ │  200GB      │ │  200GB       │
  └──────────────────┘ └─────────────┘ └──────────────┘
         │                   │                │
  ┌──────┴───────────────────┴────────────────┴───────────┐
  │              物理磁盘                                    │
  │    /dev/sda        /dev/sdb        /dev/sdc            │
  └───────────────────────────────────────────────────────┘
```

**LVM 三层结构：**

| 层次 | 组件 | 说明 |
|------|------|------|
| 物理卷（PV） | Physical Volume | 物理磁盘或分区，被 LVM 识别 |
| 卷组（VG） | Volume Group | 一个或多个 PV 的集合，类似"存储池" |
| 逻辑卷（LV） | Logical Volume | 从 VG 中分配的逻辑分区，可动态调整大小 |

#### 5.2 LVM 创建完整流程

```bash
# ===== 第一步：准备物理卷 (PV) =====

# 1. 创建分区（以 parted 为例）
sudo parted /dev/sdb mklabel gpt
sudo parted /dev/sdb mkpart primary 0% 100%

# 2. 设置分区类型为 LVM
sudo fdisk /dev/sdb
# 在 fdisk 中: t → 8e（Linux LVM）→ w

# 3. 创建物理卷
sudo pvcreate /dev/sdb1
sudo pvcreate /dev/sdb1 /dev/sdc1    # 同时创建多个

# 查看物理卷
sudo pvs
sudo pvdisplay /dev/sdb1

# 输出示例：
#   --- Physical volume ---
#   PV Name               /dev/sdb1
#   VG Name               vg0
#   PV Size               100.00 GiB
#   Allocatable           yes
#   PE Size               4.00 MiB
#   Total PE              25599
#   Free PE               5119
#   Allocated PE          20480

# ===== 第二步：创建卷组 (VG) =====

# 创建卷组（将多个 PV 合并为一个存储池）
sudo vgcreate vg0 /dev/sdb1
sudo vgcreate vg0 /dev/sdb1 /dev/sdc1    # 包含多个 PV

# 扩展卷组（添加新的 PV）
sudo vgextend vg0 /dev/sdd1

# 查看卷组
sudo vgs
sudo vgdisplay vg0

# ===== 第三步：创建逻辑卷 (LV) =====

# 按大小创建
sudo lvcreate -L 50G -n lv_data vg0

# 按 PE 数量创建
sudo lvcreate -l 100%FREE -n lv_data vg0    # 使用所有剩余空间
sudo lvcreate -l 50%VG -n lv_data vg0       # 使用 VG 的 50%

# 查看逻辑卷
sudo lvs
sudo lvdisplay /dev/vg0/lv_data

# ===== 第四步：格式化和挂载 =====

sudo mkfs.xfs /dev/vg0/lv_data
sudo mkdir -p /data
sudo mount /dev/vg0/lv_data /data

# 添加到 fstab（使用设备路径或 UUID）
echo "/dev/vg0/lv_data /data xfs defaults 0 2" | sudo tee -a /etc/fstab

# 或使用 UUID
UUID=$(sudo blkid -s UUID -o value /dev/vg0/lv_data)
echo "UUID=$UUID /data xfs defaults 0 2" | sudo tee -a /etc/fstab
```

#### 5.3 LVM 在线扩容流程

这是 SRE 最常用的操作之一——不停机扩展磁盘空间：

```
扩容流程图：

  云平台扩容磁盘          pvresize             lvextend          resize2fs/xfs_growfs
  ──────────────→    ──────────────→    ──────────────→    ────────────────→
  (磁盘从100G扩到200G)   (PV识别新空间)     (LV增加空间)       (文件系统扩展)
```

```bash
# ===== 场景：/data 空间不足，需要从 100G 扩容到 200G =====

# 前提：LVM 已经配置好，/data 挂载在 /dev/vg0/lv_data

# ---- 步骤 1：云平台扩容磁盘 ----
# 在阿里云/AWS 控制台将云盘从 100G 扩容到 200G

# ---- 步骤 2：内核识别新容量 ----
# 重新扫描 SCSI 设备（不重启）
echo 1 | sudo tee /sys/class/block/sdb/device/rescan

# 验证磁盘大小
sudo fdisk -l /dev/sdb
lsblk /dev/sdb

# ---- 步骤 3：如果分区未使用全部空间，扩展分区 ----
# 使用 growpart（cloud-init 工具）
sudo growpart /dev/sdb 1
# 或使用 parted
sudo parted /dev/sdb resizepart 1 100%

# ---- 步骤 4：扩展物理卷 (PV) ----
sudo pvresize /dev/sdb1
sudo pvs    # 确认 PV 大小已更新

# ---- 步骤 5：扩展逻辑卷 (LV) ----
# 使用 VG 中所有可用空间
sudo lvextend -l +100%FREE /dev/vg0/lv_data

# 或指定增量
sudo lvextend -L +100G /dev/vg0/lv_data

# 或一步完成（自动扩展文件系统）
sudo lvextend -L +100G -r /dev/vg0/lv_data
# -r 自动调用 resize2fs（ext4）或 xfs_growfs（XFS）

# ---- 步骤 6：扩展文件系统 ----
# ext4 文件系统
sudo resize2fs /dev/vg0/lv_data

# XFS 文件系统
sudo xfs_growfs /data                    # 注意：XFS 使用挂载点

# ---- 步骤 7：验证 ----
df -h /data
# /dev/mapper/vg0-lv_data  200G   80G  120G  40% /data
```

**完整的自动化扩容脚本：**
```bash
#!/bin/bash
# lvm-expand.sh — LVM 在线扩容脚本
set -euo pipefail

VG_NAME="${1:-vg0}"
LV_NAME="${2:-lv_data}"
MOUNT_POINT="${3:-/data}"

echo "=== LVM 在线扩容开始 ==="
echo "VG: $VG_NAME, LV: $LV_NAME, 挂载点: $MOUNT_POINT"

# 重新扫描所有 SCSI 设备
for host in /sys/class/scsi_host/*/scan; do
    echo "- - -" > "$host" 2>/dev/null || true
done
sleep 2

# 扩展 PV
echo ">>> 扩展物理卷..."
pvresize /dev/sdb1 2>/dev/null || echo "PV 扩展无需更改"

# 扩展 LV
echo ">>> 扩展逻辑卷..."
lvextend -l +100%FREE "/dev/${VG_NAME}/${LV_NAME}"

# 扩展文件系统
FSTYPE=$(findmnt -n -o FSTYPE "$MOUNT_POINT")
echo ">>> 文件系统类型: $FSTYPE"
case "$FSTYPE" in
    ext4)   resize2fs "/dev/${VG_NAME}/${LV_NAME}" ;;
    xfs)    xfs_growfs "$MOUNT_POINT" ;;
    *)      echo "不支持的文件系统: $FSTYPE" ; exit 1 ;;
esac

echo "=== 扩容完成 ==="
df -h "$MOUNT_POINT"
```

#### 5.4 LVM 缩容（有风险）

```bash
# 缩容必须先卸载，有数据丢失风险
# 正确顺序：卸载 → fsck → resize2fs（缩小文件系统）→ lvreduce（缩小 LV）→ 重新挂载

sudo umount /data
sudo e2fsck -f /dev/vg_data/lv_app         # 检查文件系统
sudo resize2fs /dev/vg_data/lv_app 50G     # 先缩文件系统
sudo lvreduce -L 50G /dev/vg_data/lv_app   # 再缩 LV
sudo mount /dev/vg_data/lv_app /data

# 顺序反了会怎样？
# 如果先 lvreduce 再 resize2fs，LV 空间小于文件系统所需空间
# 文件系统元数据被截断 → 数据损坏
```

#### 5.5 LVM 快照

```bash
# ===== LVM 快照原理 =====
# LVM 快照使用 Copy-on-Write（CoW）机制：
#
# 初始状态：
#   快照卷（空）  ←── 指向原始卷的数据
#   原始卷 [A][B][C][D]
#
# 修改原始卷的块 B：
#   1. 将块 B 的旧数据复制到快照卷
#   2. 在原始卷上写入新数据 B'
#   快照卷 [B_old]  ←── 保存了修改前的数据
#   原始卷 [A][B'][C][D]
#
# 读取快照时看到的是创建快照那一刻的数据一致性视图

# 创建快照（原始卷 50GB，快照卷 10GB 通常够用）
sudo lvcreate -L 10G -s -n lv_data_snap /dev/vg0/lv_data
# -s 表示创建快照  -n 快照名称

# 查看快照
sudo lvs
# LV            VG   Attr       LSize   Pool Origin  Data%
# lv_data       vg0  owi-aos---  50.00g
# lv_data_snap  vg0  swi-aos---  10.00g      lv_data  0.00

# 挂载快照（用于备份，不影响原始卷）
sudo mkdir -p /mnt/snapshot
sudo mount /dev/vg0/lv_data_snap /mnt/snapshot

# 使用快照进行备份
sudo tar czf /backup/data-$(date +%Y%m%d).tar.gz -C /mnt/snapshot .

# 备份完成后卸载并删除快照
sudo umount /mnt/snapshot
sudo lvremove /dev/vg0/lv_data_snap

# 快照注意事项：
# - 快照空间用尽 → 快照自动失效，必须监控使用率
# - 快照保留期间会轻微影响写性能
# - 适用于：备份前的数据一致性保证、升级前回滚点
```

#### 5.6 LVM 条带化（Striping）

```bash
# 条带化将数据分散到多个 PV，提升并行 I/O 性能
#
# 无条带化：
#   写入: [数据块1] → PV1
#         [数据块2] → PV1
#         [数据块3] → PV1
#
# 条带化（2 个 PV）：
#   写入: [数据块1] → PV1
#         [数据块2] → PV2    ← 并行写入
#         [数据块3] → PV1
#         [数据块4] → PV2    ← 并行写入

# 创建条带化 LV（跨 2 个 PV，条带大小 64KB）
sudo lvcreate -L 100G -i 2 -I 64 -n lv_stripe vg0
# -i 2   条带数（必须 ≤ PV 数量）
# -I 64  条带大小（4K, 8K, 16K, 32K, 64K, 128K, 256K, 512K）

# 验证条带化
sudo lvdisplay -m /dev/vg0/lv_stripe
```

---

### 6. Swap 交换空间

```bash
# 创建 swap 文件（比分区更灵活）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 调整 swappiness（0-100，默认 60）
# 值越低越倾向用物理内存，数据库服务器建议 10
cat /proc/sys/vm/swappiness
sudo sysctl vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf

# 查看哪些进程在用 swap
for pid in $(ls /proc/ | grep -E '^[0-9]+$'); do
    swap=$(awk '/Swap/{sum+=$2} END{print sum}' /proc/$pid/smaps 2>/dev/null)
    [ "$swap" != "" ] && [ "$swap" != "0" ] && echo "PID $pid: ${swap}kB"
done | sort -t: -k2 -rn | head -10
```

---

### 7. RAID 级别对比

#### 7.1 RAID 级别详解

```
RAID 0（条带化，最少 2 块盘）
┌──────────┐ ┌──────────┐
│   Disk 0 │ │   Disk 1 │
│ [A0][A2] │ │ [A1][A3] │
└──────────┘ └──────────┘
特点：高性能，无冗余，一块盘坏全丢
容量：N × 单盘容量
适用：临时数据、缓存

RAID 1（镜像，最少 2 块盘）
┌──────────┐ ┌──────────┐
│   Disk 0 │ │   Disk 1 │
│ [A][B][C]│ │ [A][B][C]│
└──────────┘ └──────────┘
特点：高冗余，读性能好，写性能一般
容量：1 × 单盘容量
适用：系统盘、小容量高可靠场景

RAID 5（分布式奇偶校验，最少 3 块盘）
┌──────────┐ ┌──────────┐ ┌──────────┐
│   Disk 0 │ │   Disk 1 │ │   Disk 2 │
│ [A0][A3] │ │ [A1][P]  │ │ [P ][A2] │
└──────────┘ └──────────┘ └──────────┘
P = 奇偶校验（分布在不同盘上）
特点：读性能好，写性能因校验计算降低，允许坏 1 块盘
容量：(N-1) × 单盘容量
适用：通用存储、文件服务器

RAID 6（双重分布式奇偶校验，最少 4 块盘）
┌────┐ ┌────┐ ┌────┐ ┌────┐
│D0  │ │D1  │ │P   │ │P   │
│D4  │ │P   │ │D3  │ │P   │
│P   │ │D6  │ │D5  │ │P   │
└────┘ └────┘ └────┘ └────┘
特点：允许坏 2 块盘，写性能更差
容量：(N-2) × 单盘容量
适用：大容量、高可靠性需求

RAID 10（镜像+条带化，最少 4 块盘）
┌──────────────────────────┐  RAID 0
│    RAID 1       RAID 1   │
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐
│ │D0  │ │D0  │ │D1  │ │D1  │
│ └────┘ └────┘ └────┘ └────┘
│  Disk0  Disk1  Disk2  Disk3
└──────────────────────────┘
特点：高性能 + 高冗余，允许每组坏 1 块盘
容量：N/2 × 单盘容量
适用：数据库、高 I/O 负载
```

#### 7.2 RAID 级别选择表

| RAID | 最少盘数 | 可用容量 | 读性能 | 写性能 | 容错 | 适用场景 |
|------|---------|---------|--------|--------|------|---------|
| 0 | 2 | N×单盘 | N 倍 | N 倍 | 0（无冗余） | 临时数据、视频编辑 |
| 1 | 2 | 1×单盘 | N 倍 | 1 倍 | N-1 块 | 系统盘、日志盘 |
| 5 | 3 | (N-1)×单盘 | (N-1)倍 | 较低 | 1 块 | 文件服务器、归档 |
| 6 | 4 | (N-2)×单盘 | (N-2)倍 | 更低 | 2 块 | 大容量归档 |
| 10 | 4 | N/2×单盘 | N 倍 | N/2 倍 | 每组1块 | 数据库、关键业务 |

#### 7.3 软件 RAID 配置

```bash
# 使用 mdadm 创建软件 RAID 10
sudo mdadm --create /dev/md0 --level=10 --raid-devices=4 \
    /dev/sdb1 /dev/sdc1 /dev/sdd1 /dev/sde1

# 查看 RAID 状态
cat /proc/mdstat
sudo mdadm --detail /dev/md0

# 保存 RAID 配置
sudo mdadm --detail --scan >> /etc/mdadm/mdadm.conf

# 模拟磁盘故障
sudo mdadm --manage /dev/md0 --fail /dev/sdc1

# 移除故障磁盘
sudo mdadm --manage /dev/md0 --remove /dev/sdc1

# 添加新磁盘（自动重建）
sudo mdadm --manage /dev/md0 --add /dev/sdf1
```

---

### 8. I/O 调度器

#### 8.1 调度器对比

| 调度器 | 适用场景 | 特点 |
|--------|---------|------|
| mq-deadline | 通用、数据库 | 基于截止时间的调度，保证请求在期限内完成 |
| bfq | 桌面、交互式 | 保证公平带宽分配，适合多用户场景 |
| kyber | 快速设备（NVMe） | 轻量级，低延迟，适配快速存储 |
| none/noop | NVMe、虚拟化 | 不做调度，直接发送请求，适合快速设备 |

```bash
# 查看当前调度器
cat /sys/block/sda/queue/scheduler
# [mq-deadline] kyber bfq none

# 临时更改调度器
echo "bfq" | sudo tee /sys/block/sda/queue/scheduler

# 永久更改（GRUB 配置）
# 编辑 /etc/default/grub，在 GRUB_CMDLINE_LINUX 中添加：
# elevator=mq-deadline
# 然后 sudo update-grub

# 使用 udev 规则按设备类型设置（推荐）
cat << 'EOF' | sudo tee /etc/udev/rules.d/60-ioscheduler.rules
# HDD 使用 mq-deadline
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="1", \
    ATTR{queue/scheduler}="mq-deadline"

# SSD/NVMe 使用 none
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="0", \
    ATTR{queue/scheduler}="none"

# NVMe 使用 none
ACTION=="add|change", KERNEL=="nvme[0-9]*", \
    ATTR{queue/scheduler}="none"
EOF

sudo udevadm control --reload-rules
```

---

### 9. SRE 实战案例

#### 9.1 生产服务器磁盘报警处理流程

```
收到报警：磁盘使用率超过 85%

处理步骤：

1. 确认报警 → 登录服务器
   $ ssh production-server
   $ df -h

2. 定位大文件/大目录
   $ du -sh /* 2>/dev/null | sort -rh | head -10
   $ du -sh /var/log/* | sort -rh | head -10

3. 找到具体原因
   # 情况 A：日志文件过大
   $ find /var/log -name "*.log" -size +1G -exec ls -lh {} \;

   # 情况 B：临时文件积累
   $ find /tmp -type f -mtime +7 | wc -l

   # 情况 C：应用数据增长
   $ du -sh /data/app/* | sort -rh | head -10

   # 情况 D：已删除但被进程占用的文件（空间未释放）
   $ sudo lsof +L1 2>/dev/null | head -10

4. 紧急处理
   # 清理日志（不删除，先清空）
   $ sudo truncate -s 0 /var/log/large-app.log

   # 清理旧日志
   $ sudo find /var/log -name "*.gz" -mtime +30 -delete

   # 清理临时文件
   $ sudo find /tmp -type f -mtime +7 -delete

5. 长期解决
   - 配置 logrotate
   - 扩容磁盘（LVM 在线扩容）
   - 设置监控预警阈值（70% 预警，85% 告警）
```

#### 9.2 数据盘在线扩容完整流程

```bash
#!/bin/bash
# cloud-disk-expand.sh — 云盘在线扩容脚本（阿里云/AWS 通用）
# 场景：/data 从 100G 扩容到 200G

set -euo pipefail

echo "========== 云盘在线扩容 =========="

# 1. 重新扫描磁盘
echo "[1/6] 重新扫描 SCSI 设备..."
for host in /sys/class/scsi_host/*/scan; do
    echo "- - -" > "$host" 2>/dev/null || true
done
sleep 2

# 2. 检查磁盘大小
echo "[2/6] 检查磁盘大小..."
lsblk /dev/sdb

# 3. 扩展分区
echo "[3/6] 扩展分区..."
growpart /dev/sdb 1 || echo "分区无需扩展"

# 4. 扩展 PV
echo "[4/6] 扩展物理卷..."
pvresize /dev/sdb1
pvs

# 5. 扩展 LV
echo "[5/6] 扩展逻辑卷..."
lvextend -l +100%FREE /dev/vg0/lv_data

# 6. 扩展文件系统
echo "[6/6] 扩展文件系统..."
FSTYPE=$(findmnt -n -o FSTYPE /data)
if [ "$FSTYPE" = "xfs" ]; then
    xfs_growfs /data
elif [ "$FSTYPE" = "ext4" ]; then
    resize2fs /dev/vg0/lv_data
fi

echo "========== 扩容完成 =========="
df -h /data
```

#### 9.3 磁盘 I/O 性能调优

```bash
# 使用 fio 进行磁盘性能测试
# 顺序读测试
fio --name=seq-read --ioengine=libaio --direct=1 --bs=1M \
    --size=1G --numjobs=1 --rw=read --filename=/data/testfile

# 随机读测试（模拟数据库）
fio --name=rand-read --ioengine=libaio --direct=1 --bs=4k \
    --size=1G --numjobs=8 --iodepth=32 --rw=randread --filename=/data/testfile

# 随机读写混合测试
fio --name=rand-rw --ioengine=libaio --direct=1 --bs=4k \
    --size=1G --numjobs=8 --iodepth=32 --rw=randrw --rwmixread=70 \
    --filename=/data/testfile

# I/O 监控工具
iostat -x 1 5         # 查看 I/O 使用率、等待时间
iotop -oP             # 实时查看哪些进程在做 I/O
pidstat -d 1 5        # 按进程查看 I/O 统计

# I/O 调优参数
# 1. 调整队列深度
echo 256 | sudo tee /sys/block/sda/queue/nr_requests

# 2. 调整 readahead（预读）
sudo blockdev --setra 4096 /dev/sda    # 设置预读 4096 个扇区（2MB）

# 3. 调整脏页刷新策略
sudo sysctl -w vm.dirty_ratio=10               # 脏页占内存比例
sudo sysctl -w vm.dirty_background_ratio=5      # 后台刷新阈值
sudo sysctl -w vm.dirty_expire_centisecs=3000   # 脏页过期时间
```

---

## 💻 实战练习

### 练习 1：磁盘分区和文件系统

```bash
# 1. 创建一个 1GB 的虚拟磁盘文件
dd if=/dev/zero of=/tmp/disk.img bs=1M count=1024

# 2. 关联为 loop 设备
sudo losetup -f --show /tmp/disk.img
# 输出类似 /dev/loop0

# 3. 使用 fdisk 创建两个分区（300MB + 700MB）
sudo fdisk /dev/loop0
# n → p → 1 → 回车 → +300M
# n → p → 2 → 回车 → 回车
# w

# 4. 格式化分区
sudo mkfs.ext4 /dev/loop0p1
sudo mkfs.xfs /dev/loop0p2

# 5. 挂载并测试
sudo mkdir -p /mnt/test-ext4 /mnt/test-xfs
sudo mount /dev/loop0p1 /mnt/test-ext4
sudo mount /dev/loop0p2 /mnt/test-xfs

# 6. 测试写入
echo "Hello ext4" | sudo tee /mnt/test-ext4/test.txt
echo "Hello xfs" | sudo tee /mnt/test-xfs/test.txt

# 7. 查看文件系统信息
df -hT /mnt/test-ext4 /mnt/test-xfs
sudo tune2fs -l /dev/loop0p1 | head -20
sudo xfs_info /dev/loop0p2

# 8. 清理
sudo umount /mnt/test-ext4 /mnt/test-xfs
sudo losetup -d /dev/loop0
rm /tmp/disk.img
```

### 练习 2：LVM 完整操作

```bash
# 1. 创建 3 个虚拟磁盘
for i in 1 2 3; do
    dd if=/dev/zero of=/tmp/disk${i}.img bs=1M count=512
    sudo losetup /dev/loop${i} /tmp/disk${i}.img
done

# 2. 创建 PV
sudo pvcreate /dev/loop1 /dev/loop2 /dev/loop3
sudo pvs

# 3. 创建 VG
sudo vgcreate test-vg /dev/loop1 /dev/loop2
sudo vgs

# 4. 创建 LV
sudo lvcreate -L 500M -n test-lv test-vg
sudo lvs

# 5. 格式化挂载
sudo mkfs.ext4 /dev/test-vg/test-lv
sudo mkdir -p /mnt/lvm-test
sudo mount /dev/test-vg/test-lv /mnt/lvm-test

# 6. 写入测试数据
sudo dd if=/dev/urandom of=/mnt/lvm-test/data.bin bs=1M count=100

# 7. 创建快照
sudo lvcreate -L 100M -s -n test-snap /dev/test-vg/test-lv
sudo lvs

# 8. 修改原始数据
sudo dd if=/dev/urandom of=/mnt/lvm-test/data2.bin bs=1M count=50

# 9. 挂载快照验证数据一致性
sudo mkdir -p /mnt/snap-test
sudo mount /dev/test-vg/test-snap /mnt/snap-test
ls -lh /mnt/snap-test/    # 只看到 data.bin，没有 data2.bin

# 10. 扩展 VG 和 LV
sudo vgextend test-vg /dev/loop3
sudo lvextend -L +400M /dev/test-vg/test-lv
sudo resize2fs /dev/test-vg/test-lv
df -h /mnt/lvm-test      # 验证空间增加

# 11. 清理
sudo umount /mnt/lvm-test /mnt/snap-test
sudo lvremove -f test-vg/test-snap
sudo lvremove -f test-vg/test-lv
sudo vgremove test-vg
sudo pvremove /dev/loop1 /dev/loop2 /dev/loop3
for i in 1 2 3; do
    sudo losetup -d /dev/loop${i}
    rm /tmp/disk${i}.img
done
```

### 练习 3：故障排查挑战

```bash
# 场景：服务器突然无法写入文件，df -h 显示空间充足
# 请排查可能的原因

# 排查步骤：
# 1. 检查 inode
df -i

# 2. 检查只读挂载
mount | grep "ro,"

# 3. 检查磁盘错误
dmesg | grep -i "error\|fault\|readonly"

# 4. 检查 quota
quota -u $(whoami)

# 5. 检查已删除但未释放的文件
sudo lsof +L1 | head -10
```

---

## 🎯 面试题精选

### 1. LVM 扩容的完整流程是什么？

**答：** LVM 在线扩容需要 6 个步骤：
1. 物理层扩容：在云平台或存储阵列扩展磁盘大小
2. 内核识别：`echo 1 > /sys/class/block/sdX/device/rescan` 或重启
3. 扩展分区：`growpart /dev/sdX 1`（如果需要）
4. 扩展 PV：`pvresize /dev/sdX1`（让 LVM 识别新空间）
5. 扩展 LV：`lvextend -l +100%FREE /dev/vg0/lv_data`
6. 扩展文件系统：`resize2fs`（ext4）或 `xfs_growfs`（xfs）

关键点：整个过程可以在线完成，不需要卸载文件系统。

### 2. RAID 5 和 RAID 10 如何选择？

**答：**
- **RAID 5**：适合读多写少、容量优先的场景（文件服务器、归档）。3 块盘起步，可用容量 (N-1)×单盘。写性能受奇偶校验计算影响，重建时间长（大容量盘重建可能需要数小时，期间再次故障会丢数据）。
- **RAID 10**：适合读写均衡、性能优先的场景（数据库、关键业务）。4 块盘起步，可用容量 N/2×单盘。读写性能都好，重建速度快（只需镜像复制）。
- **选择建议**：数据库用 RAID 10，文件存储用 RAID 5/6。容量大于 4TB 的盘不建议 RAID 5（重建时间太长）。

### 3. fstab 配置错误导致无法启动怎么修复？

**答：**
1. 进入救援模式（GRUB 菜单选择 recovery mode，或使用 Live CD）
2. 挂载根分区：`mount /dev/sdaX /mnt`
3. 编辑 fstab：`vim /mnt/etc/fstab`
4. 注释掉或修复错误行
5. 重启：`reboot`
6. 预防措施：添加 `nofail` 选项（非关键分区）、使用 UUID 而非设备名、修改前先用 `mount -a` 测试

### 4. ext4 和 XFS 的主要区别是什么？

**答：**
- **ext4**：支持在线扩容和缩容，适合中小文件，`tune2fs` 可调参数多，兼容性最好
- **XFS**：擅长处理大文件和高并发 I/O，不支持缩容，适合数据库和大容量存储
- **选择**：CentOS 7+ 默认 XFS，数据库首选 XFS，需要缩容的场景用 ext4

### 5. LVM 快照的原理是什么？

**答：** LVM 快照使用 Copy-on-Write（CoW）机制。创建快照时并不复制数据，快照卷初始为空。当原始卷的某个数据块被修改时，先把原始数据块复制到快照卷，然后才在原始卷上写入新数据。因此快照创建是瞬间的，空间使用量随修改量增长。快照卷大小取决于创建期间原始卷的修改量。

### 6. 磁盘 inode 耗尽但空间充足怎么处理？

**答：** inode 在格式化时确定，无法动态增加。处理步骤：
1. `df -i` 确认 inode 耗尽
2. `find /path -type f | wc -l` 找到文件最多的目录
3. 清理小文件（session、缓存、邮件队列）
4. 如果无法清理，只能备份数据、重新格式化（`mkfs.ext4 -i 4096` 增加 inode 密度）

### 7. 删除正在写入的日志文件后空间未释放，为什么？

**答：** `rm` 只是删除了目录中的文件名条目（unlink），但只要进程还持有文件描述符（FD），inode 的引用计数 > 0，磁盘块就不会被回收。解决方法：`> /var/log/app/access.log`（清空内容而非删除），或 `kill -USR1 $(cat /var/run/nginx.pid)`（让进程重新打开文件）。

### 8. 如何规划生产服务器的分区方案？

**答：** 推荐方案：
- `/boot`：1GB（独立分区，防止根分区问题影响启动）
- `/`：20-50GB（系统根目录）
- `/var`：独立分区（日志和临时数据，防止撑满根分区）
- `/var/log`：独立分区（日志隔离）
- `/tmp`：tmpfs 或独立分区（noexec,nosuid,nodev）
- `/data`：使用 LVM（方便扩容）
- Swap：内存 <= 8GB 时设为 2 倍内存，> 8GB 时设为 8-16GB

---

## 📚 深入阅读

- [Red Hat Storage Administration Guide](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_file_systems/index)
- [LVM HOWTO](https://tldp.org/HOWTO/LVM-HOWTO/)
- [Arch Linux Wiki: LVM](https://wiki.archlinux.org/title/LVM)
- [Arch Linux Wiki: RAID](https://wiki.archlinux.org/title/RAID)
- [Arch Linux Wiki: fstab](https://wiki.archlinux.org/title/Fstab)
- [Linux I/O Scheduler Comparison](https://www.kernel.org/doc/html/latest/block/)
- [Btrfs Wiki](https://btrfs.wiki.kernel.org/index.php/Main_Page)
- [Brendan Gregg: Linux I/O Performance](https://www.brendangregg.com/linuxperf.html)

---

## ✅ 自检清单

- [ ] 能画出 Linux 存储栈的完整架构图
- [ ] 能使用 fdisk 和 parted 创建 MBR 和 GPT 分区
- [ ] 能区分 ext4/xfs/btrfs 的特性和适用场景
- [ ] 能正确配置 /etc/fstab（理解每个字段含义）
- [ ] 能完成 LVM 的 PV → VG → LV 创建和扩容流程
- [ ] 能创建和使用 LVM 快照进行备份
- [ ] 能区分 RAID 0/1/5/6/10 并正确选择
- [ ] 能为不同存储类型选择合适的 I/O 调度器
- [ ] 能处理生产环境的磁盘报警和扩容需求
- [ ] 能使用 fio 测试磁盘性能并分析 I/O 瓶颈
