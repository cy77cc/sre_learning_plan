# Day 02: 文件系统与目录结构

> 📅 日期：2026-04-14  
> 📖 学习主题：文件系统与目录结构  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 02 的学习后，你应该掌握：
- 理解 文件系统与目录结构 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. Linux 文件系统概述

Linux 文件系统是 Linux 系统最核心的概念之一，**一切皆文件** 是 Unix/Linux 的设计哲学。

#### 1.1 什么是 FHS？

**FHS (Filesystem Hierarchy Standard)** 是 Linux 文件系统层次结构的标准，定义了类 Unix 系统中各个目录的用途和内容。目前最新版本为 **FHS 3.0**。

> **为什么要学习 FHS？**
> - 理解系统结构，快速定位问题（如日志在哪里？配置文件在哪里？）
> - 作为 SRE，必须知道 `/var/log`、`/etc`、`/home` 等目录的用途
> - 避免误操作（如把文件删到错误位置导致系统故障）

#### 1.2 真实案例：一次因找错日志文件导致的故障

```
某台 Nginx 服务器告警，运维工程师怀疑有恶意访问。
他去找日志：cd /opt/nginx/logs  —— 目录不存在！
实际路径是：/var/log/nginx/
花了 10 分钟才找到，延误了故障处理。
```

**教训**：必须熟悉 FHS 标准，才能在紧急情况下快速响应。

---

### 2. FHS 核心目录详解

#### 2.1 `/` (根目录)

| 目录 | 用途 | SRE 重要性 |
|------|------|-----------|
| `/` | 文件系统起点 | ⭐⭐⭐⭐⭐ 误删根目录 = 系统报废 |

**真实案例**：
```bash
# 某工程师想删 "tmp" 目录里的旧文件
rm -rf /tmp/*        # 正确
rm -rf / tmp/*      # 错误！多了个空格
# 结果：删除了整个 / 目录下的文件，系统报废
```

#### 2.2 `/bin` 和 `/sbin` - 命令二进制文件

| 目录 | 用途 | 内容 |
|------|------|------|
| `/bin` | 普通用户和程序需要的**基本命令** | `ls`, `cp`, `mv`, `rm`, `cat`, `grep` 等 |
| `/sbin` | 系统管理员需要的**系统管理命令** | `fdisk`, `mkfs`, `mount`, `reboot`, `iptables` 等 |
| `/usr/bin` | 用户程序命令（Ubuntu 16.04+ 的新标准） | 第三方软件 |
| `/usr/sbin` | 用户系统管理命令 | 第三方系统工具 |

**实际区分示例**：
```bash
$ ls /bin/ls    # 任何用户都能执行
$ ls /sbin/fdisk  # 通常需要 root 权限
$ ls /usr/bin/python3  # 用户安装的程序
```

#### 2.3 `/etc` - 系统配置文件 ⭐⭐⭐⭐⭐

**这是 SRE 最重要的目录！** 所有服务和系统的配置文件都在这里。

| 子目录/文件 | 用途 |
|------------|------|
| `/etc/nginx/` | Nginx 配置文件 |
| `/etc/systemd/` | systemd 服务配置 |
| `/etc/ssh/sshd_config` | SSH 服务配置 |
| `/etc/docker/daemon.json` | Docker 守护进程配置 |
| `/etc/resolv.conf` | DNS 解析配置 |
| `/etc/fstab` | 开机自动挂载表 |
| `/etc/crontab` | 系统定时任务 |
| `/etc/passwd` | 用户账户信息 |
| `/etc/shadow` | 用户密码（加密） |
| `/etc/group` | 用户组信息 |
| `/etc/hosts` | 主机名到 IP 的映射 |
| `/etc/hostname` | 主机名 |

**真实案例**：
```bash
# 查看 Nginx 配置文件
cat /etc/nginx/sites-enabled/default

# 查看 Docker 配置
cat /etc/docker/daemon.json

# 查看 SSH 端口配置
grep Port /etc/ssh/sshd_config
# 通常是 Port 22，建议改成非标准端口防扫描
```

#### 2.4 `/var` - 经常变化的数据 ⭐⭐⭐⭐⭐

| 子目录 | 用途 |
|--------|------|
| `/var/log` | **系统日志**（SRE 最常看的目录） |
| `/var/log/syslog` | Ubuntu/Debian 系统日志 |
| `/var/log/messages` | RedHat/CentOS 系统日志 |
| `/var/log/nginx/` | Nginx 访问和错误日志 |
| `/var/log/mysql/` | MySQL 数据库日志 |
| `/var/log/auth.log` | 认证日志（登录、sudo） |
| `/var/log/kern.log` | 内核日志 |
| `/var/log/dmesg` | 系统启动时的硬件检测日志 |
| `/var/cache` | 应用程序缓存（如 apt 缓存） |
| `/var/lib` | 应用程序运行时数据（数据库文件等） |
| `/var/spool` | 打印任务、邮件队列 |
| `/var/run` | 运行时 PID 文件（现在软链接到 /run） |

**真实日志分析案例**：
```bash
# 实时查看系统日志
tail -f /var/log/syslog

# 查找登录失败记录（防止暴力破解）
grep "Failed password" /var/log/auth.log

# 统计 IP 访问频率
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head -20

# 查看磁盘告警日志
dmesg | grep -i "disk\|sd\|nfs\|i/o error"
```

#### 2.5 `/home` 和 `/root` - 用户目录

| 目录 | 用途 |
|------|------|
| `/home/<username>` | 普通用户的主目录 |
| `/root` | root 用户（超级管理员）的主目录 |
| `~/.ssh/` | SSH 密钥和配置 |
| `~/.bashrc` | Bash 启动脚本 |
| `~/.profile` | 用户环境变量 |

**实际案例**：
```bash
# 查看所有用户主目录大小
du -sh /home/*

# 查找大文件（清理磁盘）
du -sh /home/*/* | sort -rh | head -10

# 查看 root 用户的 SSH 配置
ls -la /root/.ssh/
```

#### 2.6 `/usr` - 用户程序资源

| 子目录 | 用途 |
|--------|------|
| `/usr/bin` | 用户可执行命令 |
| `/usr/sbin` | 系统管理命令（非必需） |
| `/usr/lib` | 程序库文件 |
| `/usr/local` | 本地编译安装的软件（**常用**） |
| `/usr/share` | 架构无关数据（文档、图标等） |
| `/usr/src` | 源代码（Linux 内核源码常放这里） |

**SRE 实用命令**：
```bash
# 查看 apt 安装的软件位置
dpkg -L nginx | grep bin

# /usr/local 常用于手动安装的软件
ls -la /usr/local/bin/
```

#### 2.7 `/tmp` 和 `/var/tmp` - 临时文件

| 目录 | 特点 |
|------|------|
| `/tmp` | 系统重启后**可能**被清空，所有用户可写 |
| `/var/tmp` | 持久化临时文件，重启后保留 |

**实际案例**：
```bash
# /tmp 常被恶意软件利用，检查最近创建的可疑文件
find /tmp -type f -mtime -1 | head -20

# 查看 /tmp 使用情况
df -h /tmp
du -sh /tmp/*
```

#### 2.8 `/dev` - 设备文件

Linux 把硬件设备映射为文件：

| 设备文件 | 含义 |
|----------|------|
| `/dev/null` | 空设备，丢弃一切写入 |
| `/dev/zero` | 产生无限零字节 |
| `/dev/random` | 随机数生成器 |
| `/dev/sda` | 第一块 SCSI/SATA 磁盘 |
| `/dev/sda1` | 第一块磁盘的第一个分区 |
| `/dev/tty` | 当前终端 |
| `/dev/pts/0` | 伪终端 |

**实用案例**：
```bash
# 测试磁盘写入速度
dd if=/dev/zero of=/tmp/testfile bs=1M count=1024 oflag=direct

# 快速清空文件内容（比 rm 安全）
cat /dev/null > /var/log/nginx/access.log
```

#### 2.9 `/proc` 和 `/sys` - 虚拟文件系统

| 目录 | 用途 |
|------|------|
| `/proc/` | 内核和进程信息（**伪文件系统**） |
| `/proc/cpuinfo` | CPU 信息 |
| `/proc/meminfo` | 内存信息 |
| `/proc/loadavg` | 系统负载 |
| `/proc/uptime` | 系统运行时间 |
| `/proc/<PID>/` | 每个进程的信息 |
| `/sys/` | 硬件设备属性（内核 2.6+） |

**SRE 常用命令**：
```bash
# 查看 CPU 信息
cat /proc/cpuinfo | grep "model name" | head -1

# 查看内存
free -h

# 查看系统负载
cat /proc/loadavg
# 或 uptime

# 查看进程 PID 1234 的内存映射
cat /proc/1234/maps
```

---

### 3. 目录结构可视化

```
/                           # 根目录
├── bin/                    # 基本命令（所有用户可用）
├── sbin/                   # 系统管理命令（root 专用）
├── etc/                    # 配置文件 ⭐⭐⭐⭐⭐
│   ├── nginx/
│   ├── systemd/
│   ├── ssh/
│   ├── docker/
│   └── ...
├── var/                    # 经常变化的数据 ⭐⭐⭐⭐⭐
│   ├── log/                # 日志目录
│   ├── lib/                # 运行时数据
│   ├── cache/
│   ├── spool/
│   └── run/
├── home/                   # 普通用户主目录
│   └── user/
├── root/                   # root 用户主目录
├── usr/                    # 用户程序
│   ├── bin/
│   ├── sbin/
│   ├── local/              # 手动安装的软件
│   └── share/
├── tmp/                    # 临时文件
├── dev/                    # 设备文件
├── proc/                   # 内核/进程信息（虚拟）
├── sys/                    # 硬件属性（虚拟）
└── boot/                   # 启动相关文件
```

---

### 4. 实际工作场景练习

#### 场景 1：作为 SRE，你接到告警 "磁盘空间不足"

```bash
# 第一步：快速定位哪个目录占用最多空间
df -h                    # 查看整体磁盘使用
du -sh /var/log/*        # 查看 /var/log 下各子目录
du -sh /home/*           # 查看用户目录

# 第二步：清理日志（不能删，只能清空）
# 错误做法：
rm /var/log/nginx/access.log    # 会导致 Nginx 持有被删除的文件描述符
# 正确做法：
cat /dev/null > /var/log/nginx/access.log   # 或
> /var/log/nginx/access.log

# 第三步：配置 logrotate 自动轮转
cat /etc/logrotate.d/nginx
```

#### 场景 2：排查 SSH 登录问题

```bash
# 查看 SSH 登录日志（失败尝试）
grep "Failed password" /var/log/auth.log | tail -20

# 查看成功登录
grep "Accepted" /var/log/auth.log | tail -20

# 查看登录统计
last                    # 最近登录记录
lastb                   # 失败的登录尝试
who                     # 当前在线用户
```

#### 场景 3：查找配置文件

```bash
# 快速找到 nginx 配置文件
ls -la /etc/nginx/
ls -la /etc/nginx/sites-enabled/

# 找到 redis 配置文件
find /etc -name "redis*.conf" 2>/dev/null

# 找到所有 .conf 配置文件
find /etc -name "*.conf" | head -30
```

---

### 5. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `/var/log` 占用过高 | 日志没有轮转 | 配置 logrotate 或手动清理旧日志 |
| 磁盘空间显示已满但文件不大 | 被删除文件被进程持有 | `lsof +L1` 查找已删除但未释放的文件 |
| 找不到配置文件 | 不知道 FHS 标准 | 参考本文学好 FHS |
| `/tmp` 文件太多 | 系统或用户创建临时文件 | 定期清理或配置 tmpfs |
| 误删 `/etc/passwd` 中的用户 | 不知道文件用途前随意编辑 | 使用 `userdel` 而不是直接编辑文件 |


---

## 💻 实战练习

### 练习 1：基础命令练习

```bash
# 1. 查看系统信息（根据今日主题调整）
# 例如如果是进程管理，执行：
ps aux | head -10

# 2. 查看相关配置
# 例如：
ls -la /etc/ | grep -E "nginx|ssh"

# 3. 尝试实际操作（测试环境）
```

### 练习 2：实际工作场景

```bash
# 根据今日主题设计一个实际场景
# 例如：日志分析、配置修改、故障排查等

# 场景：排查一个常见问题
# 步骤 1：...
# 步骤 2：...
```

### 练习 3：进阶挑战（选做）

```bash
# 尝试完成一个稍微复杂的任务
# 例如：自动化脚本、批量处理等
```

---

## 📚 最新优质资源

### 官方文档
- [Ubuntu 22.04 LTS 官方文档](https://ubuntu.com/documentation)
- [Linux FHS 标准 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/)
- [Bash 官方手册](https://www.gnu.org/software/bash/manual/)

### 推荐教程
- [MIT The Missing Semester](https://missing.csail.mit.edu/) - 工程师必学但学校不教的技能
- [Linux Journey](https://linuxjourney.com/) - 免费的 Linux 学习路径
- [Ryan's Tutorials - Linux](https://ryanstutorials.net/linuxtutorial/) - 入门到进阶
- [Linux Command Library](https://linuxcommand.org/) - 命令行入门

### 视频课程
- [Bilibili: 鸟哥的Linux私房菜（基础篇）](https://www.bilibili.com/video/BV1Vt411X7y6/)
- [YouTube: NetworkChuck - Linux Basics](https://www.youtube.com/playlist?list=PLI9KFC2-DCX-6LVEU2c2XBGWckzVqKS6j)
- [YouTube: DevOps Journey - Linux for DevOps](https://www.youtube.com/playlist?list=PL2_OBreMn7FqZkvLWn1Br7W1v5E5XKJyI)

### 实战练习平台
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) - 史上最好的 Linux 入门练习
- [KodeKloud Engineer](https://kodekloud.com) - 交互式 K8s 和 DevOps 练习
- [Play with Docker](https://play.docker.com/) - 免费 Docker 练习环境
- [Learn Linux TV](https://www.learnlinux.tv/) - 视频 + 实战

### SRE 相关资源
- [Google SRE Books](https://sre.google/sre-book/table-of-contents/)
- [Linux Performance](http://www.brendangregg.com/linuxperf.html) - Brendan Gregg
- [Ops School](http://www.ops-school.org/) - 运维工程师学习路径


---

## 📝 笔记

### 今日学习总结

（在此记录你的学习心得）

### 遇到的问题与解决

| 问题 | 解决方案 |
|------|----------|
| 问题描述 | 如何解决 |

### 延伸思考

- 思考 1：...
- 思考 2：...

---

## ✅ 完成检查

- [ ] 理解核心概念（能用自己的话解释）
- [ ] 完成所有基础命令练习
- [ ] 完成实战场景练习
- [ ] 阅读了至少一个扩展资源
- [ ] 记录了学习笔记
- [ ] 理解了命令背后的原理

---

*由 SRE 学习计划自动生成 | 2026-04-14 09:23:45*  
*Generated by Hermes Agent with review*
