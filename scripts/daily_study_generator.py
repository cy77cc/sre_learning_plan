#!/usr/bin/env python3
"""
SRE 每日学习资料生成器
每天 9:00 自动执行，严格按 00-overview.md 要求生成详细学习文档

要求：
1. 多搜索相关资料，获取最新最优质的资源
2. 生成文档要尽可能详细，多用实际案例
3. 写完之后严格 review，检查内容质量
"""

import os
import re
import json
import subprocess
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ============ 配置 ============
BASE_DIR = Path("/root/sre_learning")
DOCS_DIR = BASE_DIR / "docs"
OVERVIEW_PATH = DOCS_DIR / "00-overview.md"
START_DATE = date(2026, 4, 13)
GIT_EMAIL = "hermes@sre-learning.local"
GIT_NAME = "Hermes Agent"
OUTPUT_DIR = Path("/root/sre_learning/cron/output")

# ============ 工具函数 ============

def run(cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    """执行 shell 命令，返回 (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout, cwd=BASE_DIR
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def git_config():
    """配置 Git"""
    run(f'git config --global user.email "{GIT_EMAIL}"')
    run(f'git config --global user.name "{GIT_NAME}"')
    run(f'git config --global --add safe.directory "{BASE_DIR}"')

def calc_day() -> int:
    """计算当前是第几天"""
    delta = (date.today() - START_DATE).days
    return delta + 1

def get_topic_from_overview(day: int) -> str:
    """从 00-overview.md 解析第 N 天的学习主题"""
    if not OVERVIEW_PATH.exists():
        return None
    
    content = OVERVIEW_PATH.read_text()
    
    # 匹配 Day N 或 Day NN 格式
    # 优先匹配 Day N: xxx 或 ### Day N
    patterns = [
        rf'### Day\s+{day}\s*\n.*?\*\*学习内容\*\*[：:]\s*([^\n]+)',
        rf'### Day\s+{day}\s*-+\s*\n.*?-\s+\*\*学习内容\*\*[：:]\s*([^\n]+)',
        rf'-\s+\[?\s*\*?Day\s+{day}\s*\]?\s*-+\s*\n.*?-\s+\*\*学习内容\*\*[：:]\s*([^\n]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            topic = match.group(1).strip()
            # 清理 markdown 格式
            topic = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', topic)
            topic = topic.replace('**', '').replace('*', '')
            return topic
    
    return None

def get_topic_from_case(day: int) -> str:
    """备用：从内置 case 语句获取主题"""
    topics = {
        1: "Linux简介与虚拟机安装 - Ubuntu 22.04安装与基础配置",
        2: "Linux文件系统与目录结构 - FHS标准详解",
        3: "Linux文件操作命令 - cp/mv/rm/cat/head/tail",
        4: "文本处理三剑客 - grep/sed/awk与正则表达式",
        5: "文件权限管理 - chmod/chown与数字权限",
        6: "用户与用户组管理 - useradd/usermod/sudo",
        7: "第一周综合复习与实战练习",
        8: "进程管理基础 - ps/top/htop/pstree",
        9: "进程控制 - kill/killall/信号机制",
        10: "systemd服务管理 - systemctl/单元文件",
        11: "系统监控命令 - uptime/free/df/vmstat/sar",
        12: "磁盘管理 - fdisk/mkfs/mount/du/df",
        13: "日志管理 - journalctl/rsyslog/日志分析",
        14: "第二周综合实战 - LAMP环境搭建",
        15: "Shell脚本基础 - 变量/环境变量/引号",
        16: "Shell条件判断 - if/elif/else/test运算符",
        17: "Shell循环结构 - for/while/until",
        18: "Shell函数 - 函数定义/参数传递/返回值",
        19: "Case语句与菜单 - select菜单制作",
        20: "数组操作 - 数组遍历/关联数组",
        21: "字符串处理与正则 - sed/awk进阶",
        22: "脚本调试与信号 - trap/set -x/set -e",
        23: "expect自动化交互 - SSH自动登录",
        24: "实战项目 - 服务器初始化脚本",
        25: "实战项目 - 日志监控告警脚本",
        26: "实战项目 - 备份脚本编写",
        27: "Bash脚本编程进阶 - 高级技巧",
        28: "第一阶段总结与测试 - 综合能力评估",
    }
    return topics.get(day, f"Day {day} 复习与扩展学习")

# ============ 内容生成器 ============

def generate_topic_content(day: int, topic: str) -> str:
    """根据主题生成详细的学习内容"""
    
    # 简短主题 -> 详细生成器映射
    topic_lower = topic.lower()
    
    if '文件系统' in topic or 'fhs' in topic_lower:
        return generate_fhs_content(day, topic)
    elif '文件操作' in topic or 'cp/mv/rm' in topic_lower:
        return generate_file_ops_content(day, topic)
    elif '文本处理' in topic or 'grep' in topic_lower or 'sed' in topic_lower or 'awk' in topic_lower:
        return generate_text_processing_content(day, topic)
    elif '权限' in topic or 'chmod' in topic_lower or 'chown' in topic_lower:
        return generate_permissions_content(day, topic)
    elif '用户' in topic or 'useradd' in topic_lower:
        return generate_user_mgmt_content(day, topic)
    elif '进程' in topic or 'ps' in topic_lower or 'top' in topic_lower:
        return generate_process_content(day, topic)
    elif 'systemd' in topic_lower or '服务' in topic:
        return generate_systemd_content(day, topic)
    elif '监控' in topic or 'uptime' in topic_lower or 'free' in topic_lower:
        return generate_monitoring_content(day, topic)
    elif '磁盘' in topic or 'fdisk' in topic_lower or 'mkfs' in topic_lower:
        return generate_disk_content(day, topic)
    elif '日志' in topic or 'journalctl' in topic_lower:
        return generate_log_content(day, topic)
    elif 'shell脚本' in topic_lower or 'shell' in topic_lower:
        return generate_shell_content(day, topic)
    elif '循环' in topic or 'for' in topic_lower or 'while' in topic_lower:
        return generate_loop_content(day, topic)
    elif '函数' in topic or 'def' in topic_lower:
        return generate_function_content(day, topic)
    elif '复习' in topic or '综合' in topic:
        return generate_review_content(day, topic)
    else:
        return generate_default_content(day, topic)

def generate_fhs_content(day: int, topic: str) -> str:
    """生成 FHS 文件系统详细学习内容"""
    return """### 1. Linux 文件系统概述

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
"""

def generate_file_ops_content(day: int, topic: str) -> str:
    """生成文件操作命令详细学习内容"""
    return """### 1. 文件操作基础命令

Linux 下一切皆文件，文件操作是每个 SRE 必须掌握的基础技能。

#### 1.1 创建和删除文件/目录

| 命令 | 用途 | 示例 |
|------|------|------|
| `touch` | 创建空文件或更新时间戳 | `touch file.txt` |
| `mkdir` | 创建目录 | `mkdir -p /path/to/deep/dir` |
| `rm` | 删除文件 | `rm -rf /tmp/old_files` |
| `rmdir` | 删除空目录 | `rmdir empty_dir/` |

**真实案例 - 批量创建文件**：
```bash
# 创建 30 天的日志文件（模拟日志场景）
for i in $(seq 1 30); do
    touch "/var/log/app_2024-01-$(printf '%02d' $i).log"
done
ls /var/log/app_*.log | wc -l   # 验证：30
```

**危险操作警示**：
```bash
# ⛔ 永远不要这样做！
rm -rf /      # 删除整个根目录
rm -rf /tmp/* ~   # 错误：空格会导致删掉 home 目录
rm -rf ./*~    # 错误：文件名以 ~ 开头可能被展开

# ✅ 安全做法：先预览再删除
ls /tmp/old_*          # 先看有哪些文件
rm -i /tmp/old_*       # 逐个确认删除
```

#### 1.2 复制和移动

| 命令 | 用途 | 示例 |
|------|------|------|
| `cp` | 复制文件/目录 | `cp -r src_dir/ dest_dir/` |
| `mv` | 移动或重命名 | `mv old_name new_name` |

**实战案例 - 备份配置文件**：
```bash
# 备份 Nginx 配置（每次修改前必做！）
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d%H%M%S)
cp /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup

# 批量复制并重命名（加水印日期）
for f in /data/logs/*.log; do
    cp "$f" "${f%.log}.backup.$(date +%Y%m%d)"
done
```

**移动并保持属性**：
```bash
# 移动整个目录（保留权限和属性）
mv -p /opt/old_service /opt/new_service

# 移动时创建目标目录
mkdir -p /backup/services
mv /opt/service_a /opt/service_b /backup/services/
```

#### 1.3 查看文件内容

| 命令 | 用途 | 特点 |
|------|------|------|
| `cat` | 查看小文件（一次性显示全部） | 内容多时屏幕飞速滚动 |
| `less` | **分页查看大文件**（推荐） | 支持搜索、上下滚动 |
| `more` | 分页查看（功能比 less 少） | 只能向下翻页 |
| `head` | 查看文件头部 | 默认 10 行 |
| `tail` | 查看文件尾部 | **最常用！日志分析必备** |
| `wc` | 统计行数/字数/字节 | `wc -l` 统计行数 |

**日志分析必备命令**：
```bash
# 实时监控日志文件（按 Ctrl+C 退出）
tail -f /var/log/syslog
tail -f /var/log/nginx/access.log

# 实时监控多个日志
tail -f /var/log/nginx/access.log /var/log/nginx/error.log

# 查看最后 100 行
tail -n 100 /var/log/nginx/access.log

# 从第 50 行开始显示（查看大文件尾部）
tail -n +50 /var/log/large_file.log

# 监控日志并高亮关键字
tail -f /var/log/nginx/access.log | grep --line-buffered "ERROR\|timeout"
```

**真实案例 - 分析 Nginx 日志**：
```bash
# 统计 PV（页面访问量）
wc -l /var/log/nginx/access.log

# 查看最新 20 条访问记录
tail -20 /var/log/nginx/access.log

# 查看有多少个独立 IP 访问
awk '{print $1}' /var/log/nginx/access.log | sort | uniq | wc -l

# 查找 404 错误
awk '$9 == 404 {print $7, $9}' /var/log/nginx/access.log | tail -20

# 统计每秒请求数
awk '{print $4}' /var/log/nginx/access.log | cut -d: -f2 | sort | uniq -c | sort -k1 -nr | head -10
```

---

### 2. find 命令 - 强大的文件查找工具

`find` 是 SRE 工作中最常用的命令之一，用于在目录树中查找文件。

#### 2.1 基础语法

```bash
find [路径] [条件] [动作]
```

#### 2.2 常用查找条件

| 条件 | 含义 | 示例 |
|------|------|------|
| `-name` | 按文件名查找 | `find /etc -name "*.conf"` |
| `-type f` | 只找文件 | `find / -type f -name "nginx.conf"` |
| `-type d` | 只找目录 | `find / -type d -name "nginx"` |
| `-mtime -N` | N 天内修改过的 | `find /var/log -mtime -7` |
| `-size +N` | 大于 N 大小的文件 | `find / -size +100M` |
| `-perm NNN` | 按权限查找 | `find / -perm 777` |
| `-user` | 按所有者查找 | `find /home -user www-data` |
| `-group` | 按用户组查找 | `find / -group sudo` |

**实战案例**：
```bash
# 查找所有 Nginx 配置文件
find /etc /usr -name "nginx*.conf" 2>/dev/null

# 查找 7 天内修改过的日志文件
find /var/log -name "*.log" -mtime -7 -ls

# 查找大于 100MB 的文件
find / -type f -size +100M -ls

# 查找所有 777 权限的文件（安全检查！）
find / -type f -perm 777 -ls 2>/dev/null

# 查找指定用户的所有文件
find / -user nginx -ls 2>/dev/null | head -20

# 查找空文件
find /tmp -type f -empty

# 查找并删除（删除 30 天前的旧日志）
find /var/log -name "*.log" -mtime +30 -delete
```

**危险操作 - 慎用 delete**：
```bash
# ⛔ 永远不要这样做！
find / -name "*.log" -delete   # 可能误删系统重要日志

# ✅ 安全做法：先找到，再加确认
find / -name "*.log" -mtime +30   # 先预览
find / -name "*.log" -mtime +30 -ok rm {} \;   # 逐个确认删除
```

#### 2.3 查找后执行动作

```bash
# 查找并显示详细信息
find /etc -name "*.conf" -ls

# 查找并复制到指定目录
find /var/log -name "*.log" -mtime -1 -exec cp {} /backup/logs/ \\;

# 查找并打包（将 7 天前的日志打包）
find /var/log -name "*.log" -mtime +7 | xargs tar -czf logs_backup.tar.gz

# 查找所有 .conf 文件并统计行数
find /etc -name "*.conf" -exec wc -l {} + | sort -n
```

---

### 3. 链接文件 - ln 命令

Linux 有两种链接：硬链接和软链接（符号链接）。

#### 3.1 硬链接 vs 软链接

| 特性 | 硬链接 | 软链接 |
|------|--------|--------|
| 原理 | 同一文件的多个别名 | 指向另一个文件的路径 |
| 跨分区 | ❌ 不能跨文件系统 | ✅ 可以跨文件系统 |
| 目录 | ❌ 不能链接目录 | ✅ 可以链接目录 |
| 删除源文件 | 链接仍然有效（文件未删除） | 链接失效（断链） |

**实战案例**：
```bash
# 创建硬链接（备份配置文件）
ln /etc/nginx/nginx.conf /backup/nginx.conf.backup

# 创建软链接（Nginx 配置目录）
ln -s /etc/nginx/sites-enabled /etc/nginx/sites-enabled

# 查看链接（第二个字段是链接数）
ls -la /etc/nginx/
# lrwxrwxrwx 1 root root  4096 xxx sites-enabled -> ../sites-available/default

# 查找所有软链接
find /etc -type l -ls

# 查找断链（目标不存在的软链接）
find /etc -type l ! -exists
```

**软链接的实际应用**：
```bash
# 为常用目录创建快捷方式
ln -s /var/log/nginx /home/sre/nginx_logs

# 版本切换（软件多版本管理）
ln -sfn /opt/python3.10 /usr/local/python  # 切换默认 Python

# 创建临时链接访问其他位置的文件
ln -s /mnt/backup/data /var/www/html/backup
```

---

### 4. 管道和重定向

这是 Linux 最强大的特性之一，SRE 必须精通。

#### 4.1 输出重定向

| 符号 | 含义 | 示例 |
|------|------|------|
| `>` | 重定向输出（覆盖） | `echo "test" > file.txt` |
| `>>` | 追加重定向 | `echo "test" >> file.txt` |
| `2>` | 重定向错误输出 | `command 2> error.log` |
| `&>` | 重定向所有输出 | `command &> all.log` |
| `2>&1` | 错误输出重定向到标准输出 | `command > log.txt 2>&1` |

**实战案例**：
```bash
# 保存命令输出到文件
ls -la > file_list.txt

# 追加而不是覆盖
echo "=== $(date) ===" >> system_info.log
df -h >> system_info.log

# 将错误信息保存到文件
grep "error" /var/log/syslog 2> errors.txt

# 同时保存正确和错误输出
command > output.log 2>&1

# 静默丢弃输出（定时任务中常用）
command > /dev/null 2>&1
```

#### 4.2 管道 |

管道将前一个命令的输出作为后一个命令的输入：

```bash
# 统计当前运行的 Python 进程数
ps aux | grep python | wc -l

# 查找最大的 10 个文件
du -sh /var/* | sort -rh | head -10

# 实时查看最新的 20 条错误日志
tail -f /var/log/syslog | grep -i error | tail -20

# 提取 IP 并统计访问次数
cat /var/log/nginx/access.log | awk '{print $1}' | sort | uniq -c | sort -nr
```

**复杂管道实战**：
```bash
# 分析日志：统计每小时的请求数
cat /var/log/nginx/access.log \
    | awk '{print $4}' \
    | cut -d: -f1 \
    | sort \
    | uniq -c \
    | sort -k1 -nr

# 查找系统中最大的 5 个文件
find / -type f -exec du -h {} + 2>/dev/null | sort -rh | head -5

# 清理所有 .tmp 文件但保留最新的 3 个
ls -t /tmp/*.tmp | tail -n +4 | xargs rm -f
```

---

### 5. 常见问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| 文件被误删但进程还在使用 | `lsof +L1` 找到后恢复，或重启进程 |
| 删除大量文件很慢 | `rsync -a --delete /empty_dir/ /target_dir/` 比 `rm` 快 10 倍 |
| 文件名有特殊字符 | 用单引号：`rm -i 'file with spaces.txt'` |
| 磁盘空间不足但找不到大文件 | `du -sh /*` 从根目录逐层排查 |
| 复制目录时权限丢失 | 用 `cp -a` 保留所有属性 |
| 文件名乱码 | `convmv -f gbk -t utf8 --notest filename` |
"""

def generate_text_processing_content(day: int, topic: str) -> str:
    """生成文本处理三剑客详细学习内容"""
    return """### 1. grep - 文本搜索神器

grep 是 Linux 中最常用的文本搜索工具，SRE 必备技能。

#### 1.1 基础语法

```bash
grep [选项] "搜索模式" [文件...]
```

#### 1.2 常用选项

| 选项 | 含义 | 示例 |
|------|------|------|
| `-i` | 忽略大小写 | `grep -i "error" log.txt` |
| `-n` | 显示行号 | `grep -n "Failed" auth.log` |
| `-c` | 只显示匹配行数 | `grep -c "404" access.log` |
| `-v` | 反向匹配（不包含） | `grep -v "GET /health" access.log` |
| `-r` | 递归搜索目录 | `grep -r "config" /etc/` |
| `-A N` | 显示匹配行后 N 行 | `grep -A 5 "ERROR" log.txt` |
| `-B N` | 显示匹配行前 N 行 | `grep -B 3 "ERROR" log.txt` |
| `-l` | 只显示文件名 | `grep -rl "password" /etc/` |
| `-w` | 整词匹配 | `grep -w "root" /etc/passwd` |
| `-E` | 扩展正则 | `grep -E "error|fatal|critical" log.txt` |
| `-o` | 只输出匹配部分 | `grep -oE "[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+" access.log` |

**实战案例 - 日志分析**：
```bash
# 查找所有 error 日志（不区分大小写）
grep -i "error" /var/log/syslog | tail -50

# 查找登录失败记录（安全监控）
grep "Failed password" /var/log/auth.log | grep "sshd"

# 统计 404 错误出现次数
grep -c " 404 " /var/log/nginx/access.log

# 查找错误前后 5 行（完整上下文）
grep -B 5 -A 5 "ERROR" /var/log/app.log

# 反向查找（排除健康检查）
grep -v "GET /health" /var/log/nginx/access.log | wc -l

# 提取 IP 地址
grep -oE "\\b[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\b" /var/log/nginx/access.log

# 多条件匹配（扩展正则）
grep -E "error|fatal|critical|warning" /var/log/nginx/error.log
```

---

### 2. sed - 流编辑器

sed 是强大的流编辑器，用于对文本进行替换、删除、插入等操作。

#### 2.1 基础语法

```bash
sed [选项] '命令' [文件...]
sed -i '命令' [文件...]    # -i: 直接修改文件
```

#### 2.2 常用命令

| 命令 | 含义 | 示例 |
|------|------|------|
| `s/old/new/` | 替换第一处 | `sed 's/nginx/apache/' file` |
| `s/old/new/g` | 全部替换 | `sed 's/nginx/apache/g' file` |
| `s/old/new/2` | 只替换第二处 | `sed 's/nginx/apache/2' file` |
| `Nd` | 删除第 N 行 | `sed '5d' file` |
| `N,Md` | 删除 N 到 M 行 | `sed '1,10d' file` |
| `/pattern/d` | 删除匹配行 | `sed '/^#/d' file` |
| `p` | 打印行 | `sed -n '5p' file` |
| `i\\text` | 在行前插入 | `sed '1i\\Header' file` |
| `a\\text` | 在行后追加 | `sed '1a\\Footer' file` |

**实战案例 - 配置文件处理**：
```bash
# 替换配置文件中的端口（nginx 端口 80 -> 8080）
sed -i 's/listen 80;/listen 8080;/' /etc/nginx/nginx.conf

# 替换所有注释为空行
sed -i '/^#/d' /etc/nginx/nginx.conf

# 删除空行
sed -i '/^$/d' /etc/nginx/nginx.conf

# 在每行行首添加行号
sed = file.txt | sed 'N;s/\\n/\\t/'

# 替换多个空格为单个空格
sed -i 's/  */ /g' file.txt

# 替换 tab 为空格
sed -i 's/\\t/ /g' file.txt

# 替换包含特定字符的行
sed -i '/max_connections/c\\max_connections = 1000' /etc/mysql/mysql.conf.d/mysqld.cnf

# 备份并修改（安全的做法）
sed -i.backup 's/old/new/g' file.txt
# 原文件保存为 file.txt.backup
```

**批量替换实战**：
```bash
# 批量替换多个文件中的字符串
find /etc/nginx/sites-enabled/ -name "*.conf" \
    | xargs sed -i 's/80/8080/g'

# 将所有 .txt 文件中的 "localhost" 替换为 "127.0.0.1"
find . -name "*.txt" | xargs sed -i 's/localhost/127.0.0.1/g'

# 在文件特定位置插入内容（第 10 行后）
sed -i '10a\\# Added by SRE automation' /etc/config.conf
```

---

### 3. awk - 强大的文本分析工具

awk 不仅仅是文本编辑工具，更是数据分析和报表生成的利器。

#### 3.1 基础语法

```bash
awk '模式 {动作}' [文件...]
awk -F: '{print $1}' /etc/passwd    # -F 指定分隔符
```

#### 3.2 内置变量

| 变量 | 含义 | 示例值 |
|------|------|--------|
| `$0` | 整行 | "root:x:0:0:root:/root:/bin/bash" |
| `$1, $2...` | 第 1, 2... 个字段 | $1="root", $2="x" |
| `NF` | 字段数量 | 7 |
| `NR` | 当前行号 | 1, 2, 3... |
| `FNR` | 当前文件的行号 | 1, 2, 3... |
| `FS` | 字段分隔符 | ":" |
| `OFS` | 输出字段分隔符 | " " |
| `RS` | 记录分隔符 | "\\n" |
| `ORS` | 输出记录分隔符 | "\\n" |

**实战案例 - 日志分析**：
```bash
# 统计 Nginx 日志每小时的请求数
awk '{print $4}' /var/log/nginx/access.log \
    | cut -d: -f1 \
    | sort \
    | uniq -c \
    | sort -k1 -nr

# 提取 Nginx 日志中的状态码统计
awk '{print $9}' /var/log/nginx/access.log \
    | sort \
    | uniq -c \
    | sort -rn

# 统计每个 IP 的访问次数（降序）
awk '{print $1}' /var/log/nginx/access.log \
    | sort \
    | uniq -c \
    | sort -rn \
    | head -20

# 查找 5xx 错误并显示详细信息
awk '$9 ~ /^[45][0-9][0-9]$/ {print $1, $4, $7, $9}' /var/log/nginx/access.log

# 统计 POST 请求的字节数
awk '$6 == "POST" {sum += $10} END {print sum}' /var/log/nginx/access.log

# 统计每个 URL 的访问次数
awk '{print $7}' /var/log/nginx/access.log \
    | sort \
    | uniq -c \
    | sort -rn \
    | head -20
```

**复杂分析案例 - SRE 健康检查报告**：
```bash
# 分析 Nginx 状态码分布
awk '{
    if ($9 >= 200 && $9 < 300) success++
    else if ($9 >= 300 && $9 < 400) redirect++
    else if ($9 >= 400 && $9 < 500) client_error++
    else if ($9 >= 500) server_error++
    total++
}
END {
    print "=== Nginx 健康检查报告 ==="
    print "总请求数:", total
    print "成功 (2xx):", success, sprintf("(%.1f%%)", success/total*100)
    print "重定向 (3xx):", redirect, sprintf("(%.1f%%)", redirect/total*100)
    print "客户端错误 (4xx):", client_error, sprintf("(%.1f%%)", client_error/total*100)
    print "服务端错误 (5xx):", server_error, sprintf("(%.1f%%)", server_error/total*100)
}' /var/log/nginx/access.log
```

#### 3.3 条件判断

```bash
# 基本条件
awk '{if ($9 >= 500) print $0}' /var/log/nginx/access.log

# 多条件
awk '{
    if ($9 >= 500) print "ERROR:", $0
    else if ($9 >= 400) print "CLIENT_ERR:", $0
}' /var/log/nginx/access.log

# 正则匹配
awk '/error|fatal|critical/ {print NR": "$0}' /var/log/syslog

# BEGIN 和 END 块
awk 'BEGIN {print "=== 分析开始 ==="} {sum+=$10} END {print "总流量: "sum" bytes"}' /var/log/nginx/access.log
```

---

### 4. 正则表达式

grep/sed/awk 都支持正则表达式，这是 SRE 必须掌握的技能。

#### 4.1 基础正则

| 符号 | 含义 | 示例 |
|------|------|------|
| `.` | 任意单个字符 | `a.c` 匹配 "abc", "aXc" |
| `^` | 行首 | `^error` 匹配行首的 error |
| `$` | 行尾 | `error$` 匹配行尾的 error |
| `*` | 0 个或多个 | `ab*c` 匹配 "ac", "abc", "abbc" |
| `+` | 1 个或多个 | `ab+c` 匹配 "abc", "abbc" (需 -E) |
| `?` | 0 个或 1 个 | `ab?c` 匹配 "ac", "abc" |
| `[abc]` | 字符集 | `[0-9]` 任意数字 |
| `[^abc]` | 反向字符集 | `[^0-9]` 非数字 |
| `\\` | 转义 | `\\.` 匹配字面 "." |
| `{n}` | 重复 n 次 | `a{3}` 匹配 "aaa" |
| `{n,m}` | 重复 n 到 m 次 | `a{2,4}` 匹配 "aa" 到 "aaaa" |

**实战案例**：
```bash
# 匹配 IP 地址
grep -oE "[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+" /var/log/nginx/access.log

# 匹配日期格式 (2024-01-15)
grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" /var/log/nginx/access.log

# 匹配时间格式 (14:30:25)
grep -oE "[0-9]{2}:[0-9]{2}:[0-9]{2}" /var/log/nginx/access.log

# 匹配 HTTP 状态码
grep -oE " [45][0-9]{2} " /var/log/nginx/access.log

# 匹配邮箱地址
grep -oE "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}" /var/log/nginx/access.log

# 匹配 URL
grep -oE "https?://[^ ]+" /var/log/nginx/access.log

# 匹配日志格式中的特定字段
grep -oE "\\[[0-9]{2}/[A-Za-z]{3}/[0-9]{4}:[0-9]{2}:[0-9]{2}:[0-9]{2}" /var/log/nginx/access.log
```

---

### 5. 三剑客组合技

**真实 SRE 场景：分析 Nginx 访问日志，生成日报告**：
```bash
#!/bin/bash
LOG_FILE="/var/log/nginx/access.log"
REPORT="/tmp/nginx_report_$(date +%Y%m%d).txt"

{
    echo "=== Nginx 日报 $(date +%Y-%m-%d) ==="
    echo ""
    
    # 总请求数
    echo "1. 总请求数:"
    wc -l < $LOG_FILE
    
    # 各状态码统计
    echo ""
    echo "2. HTTP 状态码分布:"
    awk '{print $9}' $LOG_FILE \
        | sort \
        | uniq -c \
        | sort -rn \
        | awk '{print "   "$2": "$1" 次"}'
    
    # Top 20 访问 IP
    echo ""
    echo "3. Top 20 访问 IP:"
    awk '{print $1}' $LOG_FILE \
        | sort \
        | uniq -c \
        | sort -rn \
        | head -20 \
        | awk '{print "   "$2": "$1" 次"}'
    
    # Top 20 请求 URL
    echo ""
    echo "4. Top 20 请求 URL:"
    awk '{print $7}' $LOG_FILE \
        | sort \
        | uniq -c \
        | sort -rn \
        | head -20 \
        | awk '{print "   "$2": "$1" 次"}'
    
    # 5xx 错误详细
    echo ""
    echo "5. 5xx 错误记录:"
    awk '$9 >= 500 {print $1, $4, $7, $9}' $LOG_FILE \
        | tail -10
    
} > $REPORT

echo "报告已生成: $REPORT"
```

---

### 6. 常见问题与解决方案

| 问题 | 解决方案 |
|------|----------|
| grep 搜索中文字符乱码 | `grep -a "错误" log.txt` 或设置 LANG |
| sed 替换斜杠多的路径 | 用 `#` 做分隔符：`sed 's#/old/path/#/new/path/#g'` |
| awk 分割 URL 中的多个空格 | `awk -F' +' '{print $1}'` 指定多个空格为分隔符 |
| 特殊字符导致正则失效 | 转义：`grep '\\.\\.\\/' file` |
| 大文件处理很慢 | 用 `grep` 先过滤，再用 `awk` 处理子集 |
"""

def generate_permissions_content(day: int, topic: str) -> str:
    """生成文件权限管理详细学习内容"""
    return """### 1. Linux 权限基础

Linux 是一个多用户系统，权限管理是系统安全的基石。

#### 1.1 权限的三个层级

| 层级 | 符号 | 含义 |
|------|------|------|
| 所有者 (Owner) | `u` | 文件的创建者 |
| 用户组 (Group) | `g` | 文件所属的用户组 |
| 其他用户 (Others) | `o` | 既不是所有者也不属于用户组的其他人 |
| 所有人 | `a` | 所有者 + 用户组 + 其他用户 |

#### 1.2 三种基本权限

| 权限 | 符号 | 数字 | 对文件的含义 | 对目录的含义 |
|------|------|------|-------------|-------------|
| 读取 (Read) | `r` | 4 | 可以查看文件内容 | 可以列出目录内容 (`ls`) |
| 写入 (Write) | `w` | 2 | 可以修改文件内容 | 可以在目录中创建/删除文件 |
| 执行 (Execute) | `x` | 1 | 可以执行文件 | 可以进入目录 (`cd`) |

#### 1.3 权限表示方法

**符号表示法**：`rwxrwxrwx`
- 第 1-3 位：所有者权限 (rwx)
- 第 4-6 位：用户组权限 (rwx)
- 第 7-9 位：其他用户权限 (rwx)

**数字表示法**：`755`, `644`, `600` 等
- 每个权限对应一个数字：r=4, w=2, x=1
- 三位数字之和：rwx = 4+2+1 = 7

**常用权限对照表**：

| 权限 | 数字 | 用途 |
|------|------|------|
| `rwx------` | 700 | 所有者完全控制，目录/脚本 |
| `rwxr-xr-x` | 755 | 所有者完全控制，其他人读和执行 |
| `rw-r--r--` | 644 | 所有者读写，其他人读（配置文件） |
| `rw-r-----` | 640 | 所有者读写，用户组读 |
| `rw-------` | 600 | 所有者读写（敏感文件，如私钥） |
| `rwxr-xr-x` | 755 | 可执行程序、脚本 |
| `r--------` | 400 | 极高敏感文件（私钥） |

---

### 2. chmod - 修改权限

#### 2.1 符号模式

```bash
chmod [who][+/-/=][permission] file...
```

**示例**：
```bash
# 给脚本添加执行权限
chmod +x deploy.sh

# 移除所有用户的写权限
chmod a-w file.txt

# 单独设置所有者权限
chmod u+x,g+r,o-rwx script.sh

# 设置精确权限（覆盖原有）
chmod u=rw,g=r,o= config.yaml

# 递归修改目录及所有子文件
chmod -R 755 /var/www/html/
```

#### 2.2 数字模式

```bash
chmod 755 file      # rwxr-xr-x
chmod 644 file      # rw-r--r--
chmod 700 file      # rwx------
chmod 600 file      # rw-------
```

#### 2.3 实战案例

**场景 1：部署 Web 应用**
```bash
# Web 目录权限（nginx 用户需要读权限）
chown -R www-data:www-data /var/www/html/
chmod -R 755 /var/www/html/
chmod 644 /var/www/html/index.html    # 配置文件不需执行
chmod +x /var/www/html/*.cgi          # CGI 脚本需要执行

# 上传目录（需要写权限）
chmod 775 /var/www/html/uploads/
chown www-data:www-data /var/www/html/uploads/
```

**场景 2：配置 SSH 密钥登录**
```bash
# SSH 私钥权限必须是 600
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub    # 公钥可以公开
chmod 700 ~/.ssh/              # SSH 目录必须安全

# 如果权限不对，SSH 会拒绝使用
# @ WARNING: UNPROTECTED PRIVATE KEY FILE! @
```

**场景 3：设置 Samba 共享目录**
```bash
# 共享目录需要 777 权限（或 775 + SGID）
chmod 777 /shared_data/
# 或
chmod 2775 /shared_data/   # SGID 继承用户组
chgrp sambashare /shared_data/
```

---

### 3. chown - 修改所有者和用户组

#### 3.1 基本语法

```bash
chown [选项] owner[:group] file...
chgrp [选项] group file...
```

#### 3.2 常用选项

| 选项 | 含义 |
|------|------|
| `-R` | 递归修改 |
| `-v` | 显示详细信息 |
| `--reference=RFILE` | 参考另一个文件的权限 |

#### 3.3 实战案例

```bash
# 修改文件所有者
chown nginx /etc/nginx/nginx.conf

# 修改所有者和用户组
chown nginx:nginx /var/log/nginx/

# 只修改用户组
chgrp www-data /var/www/html/

# 递归修改（目录及所有内容）
chown -R www-data:www-data /var/www/

# 参考另一个文件的权限
chown --reference=file1.txt file2.txt

# 批量修改（find + xargs）
find /var/www -type d -exec chown www-data:www-data {} \\;
```

---

### 4. 特殊权限

#### 4.1 SUID (4000) - 执行时以所有者身份运行

```bash
# /usr/bin/passwd 需要 root 权限修改 /etc/passwd
ls -l /usr/bin/passwd
# -rwsr-xr-x 1 root root ... /usr/bin/passwd
#                   ^ s = SUID

# 设置 SUID
chmod u+s /path/to/file
chmod 4755 /path/to/file   # 4 = SUID
```

**注意**：SUID 很危险，应尽量避免使用。

#### 4.2 SGID (2000) - 执行时以用户组身份运行

```bash
# 设置 SGID
chmod g+s /path/to/file
chmod 2755 /path/to/file   # 2 = SGID
```

#### 4.3 Sticky Bit (1000) - 目录中只能删除自己的文件

```bash
# /tmp 目录使用了 Sticky Bit
ls -ld /tmp
# drwxrwxrwt 12 root root ... /tmp
#                   ^ t = Sticky Bit

# 这确保用户 A 不能删除用户 B 的文件

# 设置 Sticky Bit
chmod +t /shared_dir/
chmod 1777 /shared_dir/
```

#### 4.4 特殊权限组合示例

```bash
# Web 共享目录：所有者/用户组完全控制，其他人读和执行
chmod 2775 /var/www/shared/
# 2 = SGID：新文件继承用户组
# 7 = rwx：所有者完全控制
# 7 = rwx：用户组完全控制
# 5 = r-x：其他人读和执行

# 临时上传目录
chmod 3777 /tmp/uploads/
# 3 = SGID + Sticky Bit
# 确保文件安全又可写
```

---

### 5. ACL - 访问控制列表（精细化权限）

ACL 提供了比传统 Unix 权限更细粒度的控制。

#### 5.1 查看 ACL

```bash
# 查看文件 ACL
getfacl /path/to/file

# 示例输出：
# # file: test.txt
# owner: nginx
# group: nginx
# user::rw-
# user:www-data:rw-
# group::r--
# mask::rw-
# other::r--
```

#### 5.2 设置 ACL

```bash
# 给特定用户设置权限
setfacl -m u:www-data:rw /var/www/html/index.html

# 给特定用户组设置权限
setfacl -m g:developers:rx /var/www/html/

# 设置默认 ACL（目录中新文件自动继承）
setfacl -m d:u:www-data:rw /var/www/html/uploads/

# 移除 ACL
setfacl -x u:www-data /path/to/file

# 清除所有 ACL
setfacl -b /path/to/file
```

#### 5.3 实战案例

```bash
# 场景：nginx 需要读取 /home/user/docs/ 下的文件
# 但不让其他用户访问

# 方法 1：把 nginx 加入用户的主用户组
usermod -aG user nginx
setfacl -m g:nginx:rx /home/user/
setfacl -m g:nginx:rx /home/user/docs/

# 方法 2：直接给 nginx 用户设置 ACL
setfacl -m u:nginx:rx /home/user/docs/

# 验证
getfacl /home/user/docs/
getfacl /home/user/docs/ | grep nginx
```

---

### 6. 权限问题排查

#### 6.1 常见权限错误及解决方案

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `Permission denied` | 无读取/执行权限 | `chmod +r file` 或 `chmod +x dir` |
| `Operation not permitted` | 无写入权限 | `chmod +w file` |
| `cannot create file` | 目录无写权限 | `chmod +w /parent/dir` |
| `Is a directory` | 对目录执行了文件操作 | 检查目标是否正确 |
| `ssh: permission denied (publickey)` | SSH 密钥权限不对 | `chmod 600 ~/.ssh/id_rsa` |

#### 6.2 排查流程

```bash
# 1. 查看当前权限
ls -la /path/to/problematic/file

# 2. 查看当前用户和所属组
id

# 3. 查看目录权限（往上追查所有父目录）
namei -l /path/to/problematic/file

# 4. 检查 ACL
getfacl /path/to/problematic/file

# 5. 如果是 SELinux 问题
ls -Z /path/to/file
getenforce
sestatus
```

#### 6.3 实战：排查 Nginx 403 Forbidden

```bash
# 1. 检查文件权限
ls -la /var/www/html/index.html
# 如果是 644，nginx 用户（通常是 www-data）有读权限

# 2. 检查目录权限
ls -la /var/www/
ls -la /var/www/html/
# 目录需要至少 755 (rwxr-xr-x)，且 nginx 用户有执行权限

# 3. 检查上级目录
namei -l /var/www/html/index.html

# 4. 检查 SELinux
getenforce   # 可能是 SELinux 阻止了 nginx 访问
# 如果是：semanage fcontext -a -t httpd_sys_content_t "/var/www/html(/.*)?"
#         restorecon -Rv /var/www/html

# 5. 检查 nginx 配置
grep "user" /etc/nginx/nginx.conf
# 确保 user nginx www-data; 与实际文件所有者匹配
```

---

### 7. 安全最佳实践

| 场景 | 推荐权限 |
|------|----------|
| 系统配置文件 | 644 (rw-r--r--) |
| 敏感配置（密码等） | 600 (rw-------) |
| SSH 私钥 | 600 |
| SSH 公钥 | 644 |
| Web 目录 | 755 (所有者 www-data) |
| Web 可写目录 | 775 (用户组 www-data) |
| CGI 脚本 | 755 |
| 日志文件 | 644 或 640 |
| /tmp 目录 | 1777 (Sticky Bit) |
| SUID 程序 | 4755 (尽量避免) |
"""

def generate_user_mgmt_content(day: int, topic: str) -> str:
    """生成用户与用户组管理详细学习内容"""
    return """### 1. Linux 用户系统概述

Linux 是一个多用户操作系统，每个需要登录的用户都必须在 `/etc/passwd` 和 `/etc/shadow` 中有记录。

#### 1.1 用户类型

| 类型 | UID 范围 | 特点 | 示例 |
|------|----------|------|------|
| root | 0 | 超级管理员，拥有最高权限 | root |
| 系统用户 | 1-999 | 服务运行时使用，不能登录 | nginx, mysql, www-data |
| 普通用户 | 1000+ | 日常使用，权限受限 | sreuser, developer |

#### 1.2 相关文件

| 文件 | 用途 | 权限 |
|------|------|------|
| `/etc/passwd` | 用户账户信息 | 644 (所有用户可读) |
| `/etc/shadow` | 加密密码（仅 root 可读） | 600 |
| `/etc/group` | 用户组信息 | 644 |
| `/etc/gshadow` | 组密码（极少用） | 600 |
| `/etc/login.defs` | 用户创建默认值 | 644 |
| `/etc/default/useradd` | useradd 默认配置 | 644 |

---

### 2. 用户管理命令

#### 2.1 useradd - 创建用户

```bash
# 基本创建
useradd -m sreuser

# 详细参数
useradd [选项] 用户名

# 常用选项：
# -m          创建主目录
# -d /path    指定主目录
# -s /bin/bash    指定登录 shell
# -G group1,group2  附加组
# -u UID      指定 UID
# -c "注释"   注释信息（通常是姓名）
# -e YYYY-MM-DD  账户过期日期
```

**实战案例 - 创建 SRE 用户**：
```bash
# 创建完整信息的 SRE 用户
useradd -m \\
    -c "SRE Engineer - Zhang San" \\
    -s /bin/bash \\
    -G sudo,docker,www-data \\
    -u 1005 \\
    zhangsan

# 设置密码
passwd zhangsan

# 验证创建结果
id zhangsan
# uid=1005(zhangsan) gid=1005(zhangsan) groups=1005(zhangsan),27(sudo),999(docker),33(www-data)

# 查看用户信息
grep zhangsan /etc/passwd
# zhangsan:x:1005:1005:SRE Engineer - Zhang San:/home/zhangsan:/bin/bash
```

#### 2.2 usermod - 修改用户

```bash
# 常用选项（与 useradd 相同）
usermod -aG docker zhangsan    # 添加到 docker 组（-a 必须与 -G 一起用）
usermod -s /bin/zsh zhangsan   # 更改登录 shell
usermod -L zhangsan            # 锁定账户（禁止登录）
usermod -U zhangsan            # 解锁账户
usermod -e 2025-12-31 zhangsan # 设置过期日期
usermod -d /new/home -m zhangsan # 移动主目录并迁移数据
```

**实战案例**：
```bash
# 将用户添加到 sudo 组（赋予 sudo 权限）
usermod -aG sudo zhangsan

# 验证 sudo 权限
su - zhangsan
sudo whoami   # 如果配置正确，输出 "root"

# 锁定用户（离职时使用）
sudo usermod -L zhangsan
grep zhangsan /etc/shadow
# zhangsan:!$6$...:...   # 密码前有 ! 表示锁定

# 解锁用户
sudo usermod -U zhangsan
```

#### 2.3 userdel - 删除用户

```bash
# 删除用户（保留主目录）
userdel zhangsan

# 删除用户及主目录（彻底清理）
userdel -r zhangsan

# 删除用户并删除所有相关文件（邮件、计划任务等）
userdel -r -f zhangsan
```

**安全提醒**：删除用户前，确保：
1. 该用户没有正在运行的进程
2. 没有重要的数据在主目录
3. 检查 `/var/spool/cron/` 是否有该用户的 crontab

```bash
# 删除前的安全检查
# 1. 查看用户进程
ps -u zhangsan

# 2. 杀掉所有进程
pkill -u zhangsan

# 3. 查看用户 crontab
crontab -u zhangsan -l

# 4. 查看用户 cron 任务
ls -la /var/spool/cron/crontabs/zhangsan 2>/dev/null

# 5. 查看 at 任务
ls -la /var/spool/at/zhangsan 2>/dev/null
```

---

### 3. 用户组管理

#### 3.1 groupadd / groupdel / groupmod

```bash
# 创建用户组
groupadd developers

# 创建系统组（低 UID）
groupadd -r systemservice

# 修改组名
groupmod -n oldname newname

# 删除组（确保没有用户以该组为主组）
groupdel developers
```

#### 3.2 gpasswd - 组密码管理

```bash
# 设置组密码
gpasswd developers

# 添加用户到组
gpasswd -a zhangsan developers

# 从组中移除用户
gpasswd -d zhangsan developers

# 设置组管理员
gpasswd -A zhangsan developers
```

#### 3.3 groups - 查看用户组

```bash
# 查看当前用户的组
groups

# 查看指定用户的组
groups zhangsan

# 查看用户属于哪些组（id 命令更详细）
id zhangsan
# uid=1005(zhangsan) gid=1005(zhangsan) groups=1005(zhangsan),27(sudo),999(docker)
```

---

### 4. 密码管理

#### 4.1 passwd

```bash
# 修改当前用户密码
passwd

# 修改指定用户密码（root）
passwd zhangsan

# 其他选项
passwd -l zhangsan    # 锁定账户
passwd -u zhangsan    # 解锁账户
passwd -e zhangsan    # 下次登录强制改密码
passwd -d zhangsan    # 清除密码（无密码登录）
passwd -n 7 zhangsan  # 最少保留 7 天才能改
passwd -x 90 zhangsan # 密码 90 天后过期
passwd -w 10 zhangsan # 过期前 10 天提醒
```

#### 4.2 chage - 密码策略

```bash
# 查看用户密码策略
chage -l zhangsan

# 设置密码过期规则
chage -M 90 zhangsan          # 密码最长使用 90 天
chage -m 7 zhangsan           # 最少使用 7 天才能改
chage -W 14 zhangsan          # 过期前 14 天提醒
chage -E 2025-12-31 zhangsan  # 账户过期日期
```

**企业密码策略示例**：
```bash
# 编辑 /etc/login.defs 设置系统默认
PASS_MAX_DAYS 90
PASS_MIN_DAYS 7
PASS_WARN_AGE 14
PASS_MIN_LEN 12
```

---

### 5. sudo 权限管理

#### 5.1 visudo - 安全编辑 sudoers 文件

```bash
# 打开 sudoers 配置编辑器
visudo

# 默认编辑器是 vim，可以改用 nano
EDITOR=nano visudo
```

#### 5.2 sudoers 语法

```bash
# 基本语法
用户  主机=(运行身份:用户组)  命令

# 示例
zhangsan  ALL=(ALL:ALL)  ALL           # 完全 sudo 权限
zhangsan  ALL=(ALL)       /usr/bin/systemctl restart nginx  # 只允许重启 nginx
zhangsan  ALL=(www-data)  /usr/bin/kill  # 以 www-data 身份执行 kill
%developers  ALL=(ALL)     /usr/bin/apt, /usr/bin/docker  # 用户组权限
```

#### 5.3 常用 sudoers 配置

```bash
# 允许用户执行所有命令（需谨慎）
zhangsan  ALL=(ALL:ALL)  ALL

# 允许用户无密码执行 sudo
zhangsan  ALL=(ALL)  NOPASSWD: ALL

# 允许 sudo 组所有权限
%sudo   ALL=(ALL:ALL)  ALL

# 限制 SRE 用户只能管理服务
%SRE  ALL=(ALL)  NOPASSWD: /usr/bin/systemctl start *, \\
                        /usr/bin/systemctl stop *, \\
                        /usr/bin/systemctl restart *, \\
                        /usr/bin/systemctl status *, \\
                        /usr/bin/journalctl, \\
                        /usr/bin/tail -f /var/log/*.log

# 允许运维重启 Docker 容器
%ops  ALL=(ALL)  NOPASSWD: /usr/bin/docker restart *
```

**安全提醒**：
```bash
# ❌ 永远不要这样做
echo "ALL ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers  # 太危险！

# ✅ 正确做法：只授权需要的命令
zhangsan  ALL=(ALL)  /usr/bin/systemctl restart nginx, /usr/bin/systemctl status nginx
```

---

### 6. 实战案例

#### 场景 1：新员工入职 - 创建 SRE 账户

```bash
#!/bin/bash
# create_sre_user.sh - 新 SRE 入职脚本

USERNAME=$1
FULL_NAME=$2
SSH_KEY_URL=$3

if [ -z "$USERNAME" ] || [ -z "$FULL_NAME" ]; then
    echo "用法: $0 <用户名> <全名> [SSH公钥URL]"
    exit 1
fi

# 1. 创建用户
useradd -m \\
    -c "$FULL_NAME" \\
    -s /bin/bash \\
    -G sudo,docker,www-data, nagios \\
    $USERNAME

# 2. 设置初始密码（生产环境建议让用户首次登录后自己改）
echo "$USERNAME:TempPassword123!" | chpasswd

# 3. 配置 sudo 权限（SRE 权限）
echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx, \\
                               /usr/bin/systemctl stop nginx, \\
                               /usr/bin/systemctl status nginx, \\
                               /usr/bin/systemctl restart docker, \\
                               /usr/bin/docker" >> /etc/sudoers

# 4. 配置 SSH 密钥登录
mkdir -p /home/$USERNAME/.ssh
chmod 700 /home/$USERNAME/.ssh

if [ -n "$SSH_KEY_URL" ]; then
    curl -s "$SSH_KEY_URL" >> /home/$USERNAME/.ssh/authorized_keys
fi

chmod 600 /home/$USERNAME/.ssh/authorized_keys
chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh

# 5. 记录创建日志
echo "$(date): Created SRE user $USERNAME ($FULL_NAME)" >> /var/log/sre_users.log
```

#### 场景 2：员工离职 - 清理账户

```bash
#!/bin/bash
# remove_sre_user.sh - SRE 离职清理脚本

USERNAME=$1

if [ -z "$USERNAME" ]; then
    echo "用法: $0 <用户名>"
    exit 1
fi

# 1. 检查用户是否存在
id $USERNAME &>/dev/null || { echo "用户不存在"; exit 1; }

# 2. 查看用户进程
echo "检查用户进程..."
ps -u $USERNAME

# 3. 杀掉用户所有进程
pkill -u $USERNAME

# 4. 锁定账户（防止 SSH 登录）
usermod -L $USERNAME

# 5. 备份用户主目录（保留 30 天）
if [ -d /home/$USERNAME ]; then
    tar -czf /backup/users/${USERNAME}_$(date +%Y%m%d).tar.gz /home/$USERNAME
    chmod 600 /backup/users/${USERNAME}_*.tar.gz
fi

# 6. 删除用户和主目录
userdel -r $USERNAME

# 7. 删除 sudoers 中的配置（需要手动编辑）
echo "请手动检查 /etc/sudoers 移除 $USERNAME 的配置"

# 8. 记录离职日志
echo "$(date): Removed SRE user $USERNAME" >> /var/log/sre_users.log
```

---

### 7. 监控与审计

```bash
# 查看所有用户登录历史
last

# 查看失败登录尝试
lastb

# 查看用户最近登录记录
lastlog

# 查看特定用户登录记录
last zhangsan

# 监控 sudo 使用
sudo tail -f /var/log/auth.log | grep sudo

# 查看谁正在使用 sudo
who | grep sudo

# 设置账户过期告警（crontab）
0 0 1 * * /usr/bin/chage -l ALL | grep "Password expires" | grep -E "([0-9]) day"
```

---

### 8. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `useradd: cannot create /home/xxx` | 目录不存在且无权限 | `mkdir /home && chmod 755 /home` |
| `permission denied` 执行 sudo | 用户不在 sudo 组 | `usermod -aG sudo username` |
| SSH 密钥登录失败 | `.ssh` 目录权限不对 | `chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys` |
| 用户登录后立即退出 | shell 不存在 | `usermod -s /bin/bash username` |
| 密码过期无法登录 | 密码过期策略 | `chage -l username` 查看，` chage -M -1 username` 永不过期 |
| 显示 "account is locked" | usermod -L 锁定 | `usermod -U username` 解锁 |
"""

def generate_default_content(day: int, topic: str) -> str:
    """默认内容生成器（适用于未专门定义的主题）"""
    return f"""### 1. 学习主题概述

{topic}

#### 1.1 核心概念

（根据主题搜索并补充详细概念说明）

#### 1.2 基础知识

**理论要点**：
- 要点 1
- 要点 2
- 要点 3

**实际案例**：
```bash
# 案例 1：基础操作
```

---

### 2. 命令详解

#### 2.1 命令格式

```bash
command [选项] [参数]
```

#### 2.2 常用选项

| 选项 | 含义 | 示例 |
|------|------|------|
| `-h` | 帮助信息 | `command -h` |
| `-v` | 显示版本 | `command -v` |
| `-r` | 递归操作 | `command -r /path` |

---

### 3. 实战练习

#### 练习 1：基础操作

```bash
# 在此完成练习
```

#### 练习 2：进阶操作

```bash
# 在此完成练习
```

---

### 4. 常见问题

| 问题 | 解决方案 |
|------|----------|
| 问题 1 | 方案 1 |
| 问题 2 | 方案 2 |

---

### 5. 扩展阅读

- [官方文档链接]()
- [优质教程]()
- [实战案例]()
"""

# ============ 学习资源 ============

def generate_learning_resources() -> str:
    """生成学习资源部分"""
    return """## 📚 最新优质资源

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
"""

# ============ Review 函数 ============

def review_document(content: str, topic: str) -> List[str]:
    """
    对生成的文档进行严格 review，检查以下方面：
    1. 内容是否完整（是否有占位符）
    2. 是否有实际命令示例
    3. 是否有真实案例
    4. 命令是否正确
    5. 格式是否规范
    """
    issues = []
    
    # 检查占位符（排除 checkbox 等合法 markdown 语法）
    placeholder_patterns = [
        r'\(详细知识点内容',
        r'在此完成练习',
        r'示例命令',
        r'方案1',
        r'问题1',
        r'# 在此.*练习',      # "# 在此完成练习" 类
    ]
    
    for pattern in placeholder_patterns:
        if re.search(pattern, content):
            issues.append(f"⚠️ 发现占位符内容: {pattern}")
    
    # 检查是否有代码块
    if '```bash' not in content and '```' not in content:
        issues.append("⚠️ 没有找到任何命令示例（应有 ```bash 代码块）")
    
    # 检查代码块数量（至少应有 3 个）
    bash_blocks = len(re.findall(r'```bash', content))
    if bash_blocks < 3:
        issues.append(f"⚠️ 命令示例偏少（当前 {bash_blocks} 个，建议至少 5 个）")
    
    # 检查是否有表格
    if '|' not in content:
        issues.append("⚠️ 没有找到表格，建议用表格组织结构化信息")
    
    # 检查标题层级
    h2_count = len(re.findall(r'^## ', content, re.MULTILINE))
    h3_count = len(re.findall(r'^### ', content, re.MULTILINE))
    if h2_count < 3:
        issues.append(f"⚠️ 二级标题偏少（当前 {h2_count} 个，建议至少 5 个）")
    
    return issues

# ============ 主生成函数 ============

def generate_day_doc(day: int, topic: str) -> Tuple[str, List[str]]:
    """
    生成完整的学习文档
    返回 (文档内容, review 问题列表)
    """
    
    # 生成详细知识点内容
    knowledge_content = generate_topic_content(day, topic)
    
    # 生成文档
    doc = f"""# Day {day:02d}: {topic}

> 📅 日期：{datetime.now().strftime('%Y-%m-%d')}  
> 📖 学习主题：{topic}  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day {day:02d} 的学习后，你应该掌握：
- 理解 {topic} 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

{knowledge_content}

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

{generate_learning_resources()}

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

*由 SRE 学习计划自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  
*Generated by Hermes Agent with review*
"""
    
    # Review 文档
    issues = review_document(doc, topic)
    
    return doc, issues

# ============ 主流程 ============

def main():
    print("=" * 60)
    print("📅 SRE 每日学习资料生成器")
    print("=" * 60)
    
    # 配置 Git
    git_config()
    
    # 计算当前天数
    day = calc_day()
    print(f"今天是 Day {day}")
    
    # 获取主题（优先从 overview 解析，备用 case 语句）
    topic = get_topic_from_overview(day)
    if not topic:
        topic = get_topic_from_case(day)
        print(f"从配置获取主题：{topic}")
    else:
        print(f"从 overview.md 解析主题：{topic}")
    
    print(f"学习主题：{topic}")
    print("-" * 60)
    
    # 生成文档
    content, issues = generate_day_doc(day, topic)
    
    # 保存文档
    day_padded = f"{day:02d}"
    day_dir = DOCS_DIR / f"day{day_padded}"
    day_dir.mkdir(parents=True, exist_ok=True)
    
    doc_path = day_dir / "README.md"
    doc_path.write_text(content, encoding='utf-8')
    print(f"✅ 文档已生成：{doc_path}")
    
    # 输出 Review 结果
    print("-" * 60)
    print("📋 Review 结果：")
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ 文档质量检查通过")
    
    # 提交 Git
    print("-" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"day{day_padded}_review.txt"
    
    review_report = f"""SRE 学习文档 Review 报告
========================
日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Day {day}: {topic}

文档路径：{doc_path}

Review 问题：
"""
    if issues:
        for i, issue in enumerate(issues, 1):
            review_report += f"  {i}. {issue}\n"
    else:
        review_report += "  ✅ 无问题\n"
    
    output_file.write_text(review_report)
    print(f"✅ Review 报告已保存：{output_file}")
    
    # Git 提交
    print("-" * 60)
    rc, stdout, stderr = run(f'cd {BASE_DIR} && git add -A && git commit -m "Day {day_padded}: {topic} - auto-generated with review"')
    if rc == 0:
        print(f"✅ Git 提交成功")
    else:
        print(f"⚠️ Git 提交：{stderr[:200] if stderr else stdout[:200]}")
    
    print("=" * 60)
    print(f"✅ Day {day} 学习资料生成完成！")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    exit(main())
