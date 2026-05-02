# Day 12: 磁盘管理 — fdisk / mkfs / mount / LVM

> 📅 日期：2026-04-25
> 📖 学习主题：磁盘管理 — fdisk / mkfs / mount / LVM
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Linux 磁盘设备命名规则和内核块设备抽象
- 掌握 MBR/GPT 分区表原理与 fdisk/parted 操作
- 理解文件系统 inode/superblock 数据结构
- 掌握 mount/VFS 挂载机制与 fstab 配置
- 深入 LVM 三层架构（PV/VG/LV）与在线扩容
- 具备磁盘告警、inode 耗尽、I/O 瓶颈的排障能力

---

## 📖 磁盘设备命名与内核抽象

### 1.1 设备命名规则

Linux 通过设备文件抽象所有存储介质，位于 `/dev/` 下：

| 前缀 | 含义 | 内核子系统 | 示例 |
|------|------|-----------|------|
| `sd` | SCSI/SATA/SAS | SCSI 子系统 | `/dev/sda`, `/dev/sdb` |
| `nvme` | NVMe SSD | NVMe 子系统 | `/dev/nvme0n1p1` (控制器0,命名空间1,分区1) |
| `vd` | VirtIO 半虚拟化 | VirtIO | `/dev/vda` (KVM) |
| `xvd` | Xen 虚拟磁盘 | Xen | `/dev/xvda` (AWS EC2) |
| `dm-` | Device Mapper | dm 模块 | `/dev/dm-0` (LVM 底层) |
| `loop` | 回环设备 | loop 模块 | `/dev/loop0` (挂载 ISO) |

**块设备 vs 字符设备**：磁盘是**块设备**（`b` 类型），以固定大小数据块为单位读写，支持随机访问，内核做 I/O 调度和缓存。

```bash
ls -la /dev/sda
# brw-rw---- 1 root disk 8, 0 /dev/sda
# ↑ 'b'=块设备，'8,0'=主设备号,从设备号
```

### 1.2 查看磁盘信息

```bash
# 最推荐：树状展示
lsblk -f
# NAME   FSTYPE LABEL UUID          MOUNTPOINT
# sda
# ├─sda1 ext4         xxxx-xxxx     /boot
# ├─sda2 swap         yyyy-yyyy     [SWAP]
# └─sda3 LVM2         zzzz-zzzz
#   ├─vg0-root ext4    aaaa-aaaa    /
#   └─vg0-data ext4    bbbb-bbbb    /data

# 只看物理盘，区分 HDD/SSD
lsblk -d -o NAME,SIZE,ROTA,MODEL
# ROTA=1 → 旋转磁盘(HDD)，ROTA=0 → 固态硬盘(SSD/NVMe)

# 查看分区表类型（gpt 或 dos/MBR）
sudo fdisk -l /dev/sda | grep "Disklabel type"

# 查看文件系统 UUID（fstab 推荐用 UUID 而非设备名）
sudo blkid
```

---

## 📖 MBR 与 GPT 分区表原理

### 2.1 结构对比

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
| 最大分区数 | 4 主分区 | 128 分区 | 多分区选 GPT |
| 最大磁盘 | 2TB | 9.4ZB | >2TB 必须 GPT |
| 数据校验 | 无 | CRC32 | GPT 更安全 |
| 备份机制 | 无 | 头尾各一份 | GPT 可恢复 |
| UEFI 启动 | 兼容模式 | 原生支持 | UEFI 选 GPT |

### 2.2 fdisk 分区操作

```bash
# 进入交互模式
sudo fdisk /dev/sdb
# 常用命令：
# g  → 创建 GPT 分区表
# o  → 创建 MBR 分区表
# n  → 新建分区（选 p=主分区, 指定起止扇区或大小如 +100G）
# t  → 修改分区类型（L 列出所有类型代码）
# p  → 打印分区表
# d  → 删除分区
# w  → 写入磁盘（⚠️ 不可逆）
# q  → 不保存退出

# 让内核重新读取分区表
sudo partprobe /dev/sdb

# 脚本化分区（非交互）
sudo sfdisk /dev/sdb <<EOF
label: gpt
name=boot,size=512M,type=EFI
name=root,size=50G,type=Linux
name=data,size=100%,type=Linux
EOF
```

---

## 📖 文件系统原理与 mkfs

### 3.1 Ext4 内部结构

```
磁盘物理结构                文件系统逻辑结构
┌────────────┐              ┌──────────────────────────┐
│ Boot Block │              │ Superblock               │
│ (引导扇区)  │              │ (块大小、总块数、inode总数)│
├────────────┤              ├──────────────────────────┤
│ Block Group│              │ Block/Inode Bitmap       │
│  块组0      │              │ (位图标记已分配块/inode)   │
│ - Superblock│             ├──────────────────────────┤
│ - Bitmap    │              │ Inode Table              │
│ - Inode Table│             │ (文件元数据：权限、大小、  │
│ - Data Blocks│             │  时间戳、数据块指针)      │
└────────────┘              ├──────────────────────────┤
                             │ Data Blocks              │
                             │ (文件实际内容)           │
                             └──────────────────────────┘
```

**关键概念**：
- **inode**：存储文件元数据，**不存文件名**。每个文件 1 个 inode。
- **目录**：本质是 `{inode 号 → 文件名}` 的映射表，存储在 Data Block 中。
- **硬链接**：多个目录项指向同一个 inode。
- **符号链接**：独立的 inode，内容是目标路径字符串。

### 3.2 mkfs 格式化

```bash
# ext4 格式化
sudo mkfs.ext4 -L "data_disk" /dev/sdb1
# -L: 设置卷标，可用 mount LABEL=data_disk /mnt 挂载

# 高级参数
sudo mkfs.ext4 \
    -b 4096 \           # 块大小 4KB（大文件选 4K，小文件可选 1K）
    -i 16384 \          # 每 16KB 一个 inode（小文件场景调小此值）
    -m 1 \              # root 保留块 1%（默认 5%，大磁盘可降为 1-2%）
    -E lazy_itable_init=0 \  # 立即初始化 inode 表
    /dev/sdb1

# XFS 格式化（RHEL/CentOS 默认，适合大文件高并发）
sudo mkfs.xfs -f /dev/sdb1

# 查看文件系统信息
sudo dumpe2fs -h /dev/sdb1

# inode 耗尽排查（症状：df -h 有空余但无法创建文件）
df -i
# Filesystem  Inodes IUsed  IFree IUse% Mounted on
# /dev/sdb1  6144000 6144000 0     100%  /data
# 原因：大量小文件占满 inode → 删除不必要的小文件
```

---

## 📖 挂载机制与 /etc/fstab

### 4.1 mount 命令

```bash
# 基本挂载
sudo mount /dev/sdb1 /data

# 挂载选项详解
# ┌──────────────┬─────────────────────────────────────────┐
# │ 选项          │ 说明                                    │
# ├──────────────┼─────────────────────────────────────────┤
# │ noatime      │ 不更新访问时间（显著提升读性能，推荐！）   │
# │ discard      │ 启用 TRIM（SSD 必备，防止性能退化）       │
# │ noexec       │ 禁止执行（安全：/tmp 目录）              │
# │ nosuid       │ 忽略 setuid/setgid 位                   │
# │ ro           │ 只读挂载（数据恢复场景）                  │
# │ remount,rw   │ 重新挂载为读写（不卸载直接改）            │
# │ errors=remount │ 出错时自动 remount 为只读               │
# └──────────────┴─────────────────────────────────────────┘

sudo mount -o rw,noatime,discard /dev/sdb1 /data

# 重新挂载（修改选项而不卸载）
sudo mount -o remount,rw /data

# 挂载 ISO
sudo mount -o loop ubuntu.iso /mnt/iso

# 绑定挂载（一个目录映射到另一位置）
sudo mount --bind /home/user/public /var/www/html
```

### 4.2 /etc/fstab 详解

```bash
# 格式：设备  挂载点  文件系统  选项  dump  fsck
# dump: 0=不备份；fsck: 0=不检查,1=根分区优先,2=其他分区

# ⚠️ 强烈建议用 UUID（设备名可能变化）
# 查看 UUID：sudo blkid
UUID=aaaa-bbbb-cccc  /data  ext4  defaults,noatime,discard  0 2

# 挂载 fstab 所有条目（修改后必须测试！）
sudo mount -a

# 验证 fstab 语法（不实际挂载）
sudo findmnt --verify
```

**fstab 写错导致无法开机的修复方法**：
1. GRUB 菜单按 `e` 编辑启动参数
2. 在 linux 行末尾添加 `init=/bin/bash`
3. `Ctrl+X` 启动进入单用户 shell
4. `mount -o remount,rw /`
5. 编辑 `/etc/fstab` 注释错误行
6. `exec /sbin/init` 继续启动

---

## 📖 LVM 逻辑卷管理

### 5.1 三层架构

```
物理磁盘 ──→ PV(物理卷) ──→ VG(卷组=空间池) ──→ LV(逻辑卷)
/dev/sdb      pvcreate         vgcreate            lvcreate
/dev/sdc      ────────────→    vgextend     ──→    lvextend
/dev/sdd                                              │
                                                      ▼
                                               mkfs → mount
```

### 5.2 LVM 完整操作

```bash
# === 创建 ===
sudo pvcreate /dev/sdb1 /dev/sdc1         # 初始化物理卷
sudo vgcreate vg_data /dev/sdb1 /dev/sdc1  # 创建卷组
sudo lvcreate -L 100G -n lv_app vg_data   # 创建 100G 逻辑卷
sudo mkfs.ext4 /dev/vg_data/lv_app        # 格式化
sudo mount /dev/vg_data/lv_app /data      # 挂载

# === 扩容（在线，无需卸载）===
# VG 有剩余空间时：
sudo lvextend -L +50G -r /dev/vg_data/lv_app
# -r 自动调用 resize2fs（ext4）或 xfs_growfs（XFS）

# VG 空间不够，添加新磁盘：
sudo pvcreate /dev/sdd1
sudo vgextend vg_data /dev/sdd1
sudo lvextend -l +100%FREE -r /dev/vg_data/lv_app

# === 缩容（⚠️ 必须先卸载，有数据丢失风险）===
sudo umount /data
sudo e2fsck -f /dev/vg_data/lv_app         # 检查文件系统
sudo resize2fs /dev/vg_data/lv_app 50G     # 先缩文件系统
sudo lvreduce -L 50G /dev/vg_data/lv_app   # 再缩 LV
sudo mount /dev/vg_data/lv_app /data

# === 快照（CoW 写时复制）===
sudo lvcreate -L 10G -s -n lv_snap /dev/vg_data/lv_app
sudo mount -o ro /dev/vg_data/lv_snap /mnt/snap
sudo lvremove /dev/vg_data/lv_snap         # 用完删除

# 查看信息
pvs    # PV 简要信息
vgs    # VG 简要信息
lvs    # LV 简要信息（加 -o +snap_percent 查看快照使用率）
```

### 5.3 LVM 快照注意事项

快照使用 **CoW (Copy-on-Write)** 机制：创建快照时不复制数据，只有当原始 LV 的数据块被修改时，才将旧数据复制到快照空间。

- 快照空间用尽 → **快照自动失效**，必须监控使用率
- 快照保留期间会轻微影响写性能
- 适用于：备份前的数据一致性保证、升级前回滚点

---

## 📖 Swap 交换空间

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

## 🔧 SRE 实战排障

### 场景 1：磁盘空间告警排查

```bash
#!/bin/bash
# disk_emergency.sh — 磁盘告警应急脚本
set -euo pipefail

echo "🚨 磁盘应急检查 $(date)"

# 1. 使用率 > 80% 的分区
df -h | awk 'NR==1 || $5+0 > 80'

# 2. inode 耗尽检查
df -i | awk 'NR==1 || $5+0 > 80'

# 3. 最大目录 Top 10
du -sh /* 2>/dev/null | sort -rh | head -10

# 4. 大于 1GB 的文件
find / -type f -size +1G -exec ls -lh {} + 2>/dev/null | \
    awk '{print $5, $9}' | sort -rh | head -10

# 5. 已删除但被进程占用的文件（空间未释放的常见原因）
sudo lsof +L1 2>/dev/null | \
    awk '{printf "PID:%-8s SIZE:%-10s FILE:%s\n", $2, $7, $9}' | \
    sort -t: -k3 -rn | head -10
# 解决：重启对应进程，或 echo > /proc/<pid>/fd/<fd>
```

### 场景 2：磁盘变只读

症状：写入文件报错 "Read-only file system"
原因：文件系统检测到严重错误，内核自动 remount 为只读保护数据。

```bash
# 排查步骤：
# 1. 查看内核日志中的错误
sudo dmesg | grep -i "EXT4-fs error\|I/O error\|Buffer I/O"

# 2. 确认挂载状态
findmnt / | grep ro  # 如果显示 ro 说明只读

# 3. 尝试重新挂载为读写
sudo mount -o remount,rw /

# 4. 如果失败，需要 fsck（根分区需从 Live CD 或救援模式启动）
# 启动参数添加：fsck.mode=force fsck.repair=yes
```

### 场景 3：I/O 性能瓶颈

```bash
# 1. I/O 统计（重点关注 %util 和 await）
iostat -x 1 3
# %util 接近 100% → I/O 饱和
# await > 20ms → I/O 等待过长

# 2. 哪个进程在大量读写
sudo iotop -o

# 3. 检查脏页缓存（等待写回磁盘的数据）
cat /proc/vmstat | grep -E "nr_dirty|nr_writeback"
```

---

## 💻 实战练习

### 练习 1：生产级 LVM 存储池搭建

```bash
#!/bin/bash
# lvm_setup.sh — 3 块新盘的 LVM 配置
set -euo pipefail

DISKS=(sdb sdc sdd)

echo "1. 创建 GPT 分区..."
for disk in "${DISKS[@]}"; do
    sudo parted /dev/$disk mklabel gpt
    sudo parted /dev/$disk mkpart primary 1MiB 100%
    sudo parted /dev/$disk set 1 lvm on
done

echo "2. LVM 配置..."
sudo pvcreate /dev/sd{b,c,d}1
sudo vgcreate vg_storage /dev/sd{b,c,d}1
sudo lvcreate -L 1T -n lv_database vg_storage
sudo lvcreate -L 2T -n lv_media vg_storage
sudo lvcreate -l 100%FREE -n lv_backup vg_storage

echo "3. 格式化并挂载..."
sudo mkfs.ext4 /dev/vg_storage/lv_database
sudo mkfs.xfs /dev/vg_storage/lv_media
sudo mkfs.ext4 /dev/vg_storage/lv_backup

sudo mkdir -p /data/{database,media,backup}
sudo mount -o noatime,discard /dev/vg_storage/lv_database /data/database
sudo mount -o noatime,discard /dev/vg_storage/lv_media /data/media
sudo mount -o noatime /dev/vg_storage/lv_backup /data/backup

echo "4. 写入 fstab（使用 UUID）..."
for lv in lv_database lv_media lv_backup; do
    uuid=$(blkid -s UUID -o value "/dev/vg_storage/$lv")
    fstype=$(blkid -s TYPE -o value "/dev/vg_storage/$lv")
    mp="/data/${lv#lv_}"
    opts="defaults,noatime"
    [ "$fstype" = "xfs" ] && opts="$opts,discard"
    echo "UUID=$uuid $mp $fstype $opts 0 2" | sudo tee -a /etc/fstab
done

sudo mount -a
echo "✅ 完成"
lvs
df -h /data
```

### 练习 2：磁盘健康巡检脚本

```bash
#!/bin/bash
# disk_health.sh — 每日巡检
set -euo pipefail

echo "💾 磁盘健康巡检 — $(date '+%Y-%m-%d %H:%M')"

# 磁盘使用率检查
echo -e "\n📊 磁盘空间:"
while IFS= read -r line; do
    pct=$(echo "$line" | awk '{gsub(/%/,"",$5); print $5}')
    mp=$(echo "$line" | awk '{print $6}')
    if [ "$pct" -ge 90 ]; then
        echo "  🔴 CRIT: $mp = ${pct}%"
    elif [ "$pct" -ge 80 ]; then
        echo "  🟡 WARN: $mp = ${pct}%"
    else
        echo "  🟢 OK:   $mp = ${pct}%"
    fi
done < <(df -h | grep -v -E "tmpfs|devtmpfs|Filesystem" | sort -k5 -rn)

# inode 检查
echo -e "\n📋 inode:"
df -i | awk 'NR>1 && $5+0>80 {printf "  ⚠️ %s: %s\n", $6, $5}'

# SMART 健康
echo -e "\n🔍 SMART:"
for disk in /dev/sd?; do
    [ -b "$disk" ] && sudo smartctl -H "$disk" 2>/dev/null | \
        grep -i "overall" | sed "s/^/  $disk: /"
done

# 僵尸文件
echo -e "\n🗑️ 已删除未释放:"
count=$(sudo lsof +L1 2>/dev/null | wc -l)
[ "$count" -gt 0 ] && echo "  ⚠️ $count 个僵尸文件" || echo "  ✅ 无"
```

---

## 🧩 练习题

### Q1：删除正在写入的日志文件后磁盘空间未释放，为什么？如何解决？

<details>
<summary>点击查看答案</summary>

**原因**：`rm` 只是删除了目录中的文件名条目，但只要进程还持有文件描述符 (FD)，inode 的引用计数 > 0，磁盘块就不会被回收。

**解决**：
```bash
# 方法 1：清空内容（保留 inode）
> /var/log/app/access.log

# 方法 2：让进程重新打开文件
kill -USR1 $(cat /var/run/nginx.pid)
```
</details>

### Q2：LVM 缩容的正确顺序是什么？顺序反了会怎样？

<details>
<summary>点击查看答案</summary>

**正确顺序**：卸载 → fsck → resize2fs（缩小文件系统）→ lvreduce（缩小 LV）→ 重新挂载

**顺序反了会怎样**：如果先 lvreduce 再 resize2fs，LV 空间小于文件系统所需空间，文件系统元数据被截断，**数据损坏**。

</details>

### Q3：磁盘空间充足但无法创建新文件，最可能的原因是什么？

<details>
<summary>点击查看答案</summary>

**原因**：inode 耗尽。大量小文件（如缓存、session、临时文件）占满了 inode 表。

**验证**：`df -i` 查看 IUse% 是否为 100%。

**解决**：删除大量小文件，或重新格式化时调小 `-i` 参数（每字节数创建 1 个 inode）。

</details>

---

## 📚 扩展阅读

- [Ext4 文件系统 Wiki](https://ext4.wiki.kernel.org/) — 内核官方文档
- [LVM2 项目文档](https://sourceware.org/lvm2/) — Red Hat 维护
- [Brendan Gregg: Linux I/O 性能](https://www.brendangregg.com/linuxperf.html) — 权威调优指南

**最佳实践**：
- fstab 始终用 **UUID** 而非 `/dev/sdX`
- SSD 必须开启 `discard` 或定期 `fstrim`
- 大文件用 XFS，小文件用 ext4
- LVM 快照及时清理，空间用尽会直接失效
