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
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ============ 配置 ============
BASE_DIR = Path("/root/sre_learning")
DOCS_DIR = BASE_DIR / "docs"
OVERVIEW_PATH = DOCS_DIR / "00-overview.md"
START_DATE = date(2026, 3, 18)
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
    
    # 先提取当前 Day 的整块内容（到下一个 ### Day 或 ## 为止）
    # 这样可以避免 .*? 跨越到下一个 Day
    block_pattern = rf'(?:^|\n)### Day\s+{day}\s*\n(.*?)(?=^### Day|^## |\Z)'
    block_match = re.search(block_pattern, content, re.DOTALL | re.MULTILINE)
    if not block_match:
        return None
    
    block = block_match.group(1)
    
    # 在当前 Day 块内查找 **学习内容** 标签
    label_pattern = re.compile(r'\*\*([^*]+)\*\*[：:]\s*([^\n-][^\n]*)', re.MULTILINE)
    
    for m in label_pattern.finditer(block):
        label = m.group(1).strip()
        text = m.group(2).strip()
        # 清理 markdown 格式
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = text.replace('**', '').replace('*', '').strip()
        if text:
            # 清理 "学习内容：" 前缀（如果标签本身就是"学习内容"）
            if label == '学习内容':
                return text
            topic = f"{label}：{text}"
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

def generate_linux_intro_content(day: int, topic: str) -> str:
    """生成 Linux 简介与虚拟机安装详细学习内容"""
    return """### 1. Linux 简介

#### 1.1 什么是 Linux？

Linux 是一个**开源的 Unix-like 操作系统内核**，由 Linus Torvalds 于 1991 年首次发布。如今 Linux 几乎运行在所有关键基础设施上：

| 领域 | 市场份额 | 代表场景 |
|------|---------|---------|
| 服务器 | **~96%** | AWS EC2、GCP、阿里云等 |
| 超级计算机 | **100%** | TOP500 全部运行 Linux |
| 云计算 | **90%+** | Docker、Kubernetes、云原生 |
| 移动设备 | **85%+** | Android 系统基于 Linux 内核 |
| 嵌入式 | **60%+** | 路由器、智能电视、汽车 |

#### 1.2 Linux 核心哲学

```
一切皆文件        — 硬件设备、进程、配置都用文件抽象
小而专一工具       — 每个命令只做一件事，通过管道组合
开源共享          — GPL 许可证，全球开发者共同维护
跨平台兼容        — x86、ARM、RISC-V、MIPS 等全支持
```

#### 1.3 常见 Linux 发行版对比

| 发行版 | 家族 | 特点 | 适用场景 |
|--------|------|------|---------|
| **Ubuntu Server/Desktop** | Debian | 社区活跃、文档丰富 | SRE 入门首选 |
| **Rocky Linux / AlmaLinux** | RHEL | 100% 兼容 RHEL、长期支持 | 生产服务器 |
| **Debian** | Debian | 极其稳定、软件版本偏保守 | 追求稳定的服务器 |
| **Arch Linux** | Arch | 滚动更新、配置灵活 | 高级用户、定制系统 |
| **Alpine** | Independent | 极简镜像（5MB） | 容器化、嵌入式 |
| **Flatcar Container Linux** | CoreOS | 容器优化、自动更新 | Kubernetes 节点 |

**SRE 推荐**：入门用 **Ubuntu 22.04 LTS**，生产用 **Rocky Linux 9** 或 **Ubuntu LTS**。

---

### 2. 虚拟机软件选择

#### 2.1 主流虚拟机软件对比

| 软件 | 费用 | 平台 | 性能 | 推荐度 |
|------|------|------|------|--------|
| **WSL2** | 免费 | Windows 11 | 接近原生 | ⭐⭐⭐⭐⭐ (Windows 用户) |
| **VirtualBox** | 免费开源 | 全平台 | 中等 | ⭐⭐⭐⭐ (通用学习) |
| **VMware Workstation Pro** | 付费 | Win/Linux | 优秀 | ⭐⭐⭐⭐ (Windows 专业用户) |
| **VMware Fusion** | 付费 | macOS | 优秀 | ⭐⭐⭐⭐ (macOS 专业用户) |
| **Hyper-V** | 免费 | Windows | 优秀 | ⭐⭐⭐ (Windows Pro) |

#### 2.2 Windows 用户：WSL2 实战

**WSL2 (Windows Subsystem for Linux 2)** 是 Windows 11 自带的 Linux 子系统，体验接近原生：

```powershell
# 管理员 PowerShell 一键安装
wsl --install

# 安装后重启，首次启动设置用户名密码
# 默认安装 Ubuntu 22.04 LTS

# 常用 WSL2 命令
wsl --list -v              # 查看已安装的发行版
wsl --set-default-version 2  # 设置默认 WSL 版本为 2
wsl -d Ubuntu-22.04        # 启动指定发行版
wsl --shutdown             # 关闭所有 WSL 实例
wsl -t Ubuntu-22.04       # 停止指定发行版
```

**WSL2 的优势**：
```
✅ 与 Windows 文件系统无缝互操作（/mnt/c/）
✅ 支持 Docker Desktop 集成
✅ 资源占用低（比虚拟机少 50%+）
✅ 启动快（2-3 秒 vs 虚拟机 30 秒+）
✅ 可直接访问 Windows 剪贴板
```

**WSL2 的局限**：
```
⚠️ 不能运行桌面版 Linux（无 GUI）
⚠️ 不支持 Systemd（需要用 service 或手动启动）
⚠️ 不支持内核模块
⚠️ 文件 I/O 性能比原生 Linux 略低
```

**解决 WSL2 Systemd 问题**：
```bash
# 在 WSL2 中启用 Systemd
sudo vim /etc/wsl.conf
# 添加以下内容：
# [boot]
# systemd=true

# 重启 WSL2
wsl --shutdown
wsl -d Ubuntu-22.04
```

#### 2.3 VirtualBox 安装实战

**VirtualBox 下载**：
- 官网：https://www.virtualbox.org/wiki/Downloads
- 推荐版本：VirtualBox 7.x
- 同时下载 **Extension Pack**（支持 USB 3.0、剪贴板共享等）

**创建虚拟机配置**：

| 配置项 | 最低要求 | 推荐配置 | 说明 |
|--------|---------|---------|------|
| CPU | 2 核 | 4 核 | 开启 PAE/NX |
| 内存 | 4 GB | 8 GB | 桌面版建议 4GB+ |
| 硬盘 | 25 GB | 50 GB+ | 动态分配 VDI |
| 网络 | NAT | 桥接 | 桥接可获得独立 IP |

**桥接网络 vs NAT**：
```
NAT：         虚拟机可以上网，宿主机可以访问虚拟机（端口转发）
桥接网络：    虚拟机与宿主机在同一网络段，有独立 IP
仅主机网络：  虚拟机与宿主机私有网络，外部无法访问
```

**VirtualBox 增强功能**：
```bash
# 1. 设备 → 插入增强功能镜像
# 2. 在虚拟机中挂载并安装
sudo mkdir -p /mnt/cdrom
sudo mount /dev/cdrom /mnt/cdrom
sudo /mnt/cdrom/VBoxLinuxAdditions.run

# 3. 添加共享剪贴板和拖放
#    设备 → 共享剪贴板 → 双向
#    设备 → 拖放 → 双向
```

---

### 3. Ubuntu 22.04 LTS 安装详解

#### 3.1 Ubuntu 22.04 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 1 GHz 双核 | 2 GHz 四核 |
| 内存 | 4 GB | 8 GB+ |
| 硬盘 | 25 GB | 50 GB+ |
| 显卡 | VESA | 支持 3D 加速 |
| 启动 | UEFI/BIOS | UEFI（推荐） |

#### 3.2 Ubuntu 安装步骤

**第一步：下载镜像**
```
官方下载：https://ubuntu.com/download/desktop
国内镜像：https://mirrors.tuna.tsinghua.edu.cn/ubuntu-releases/22.04/
文件大小：约 4.8 GB（ubuntu-22.04.4-desktop-amd64.iso）
```

**第二步：创建 VirtualBox 虚拟机**
```
1. 点击 "新建"
2. 名称：Ubuntu 22.04 SRE
   类型：Linux
   版本：Ubuntu (64-bit)
3. 内存：4096 MB（或 8192 MB）
4. 硬盘：VDI 动态分配，50 GB
5. 设置 → 系统 → 处理器：2 CPU
6. 设置 → 存储 → SATA 控制器 → 选择 ISO 镜像
7. 设置 → 网络 → 桥接网卡
8. 点击 "启动"
```

**第三步：Ubuntu 安装过程**
```
1. 选择语言 → English（推荐，避免locale问题）
2. 选择 "Install Ubuntu"
3. 键盘布局 → Chinese（如果用中文键盘）或 English US
4. 安装类型：
   - "Erase disk and install Ubuntu"（仅学习用，干净整洁）
   - "Something else"（自定义分区，生产推荐）
5. 时区 → Asia/Shanghai
6. 用户信息：
   - Your name: SRE User
   - Your computer's name: sre-server
   - Pick a username: sreuser
   - 密码：设置强密码
7. 等待安装（约 10-15 分钟）
8. 安装完成后重启
```

**第四步：安装后必做配置**

```bash
# 1. 系统更新（第一步必须做！）
sudo apt update
sudo apt upgrade -y
sudo apt full-upgrade -y

# 2. 安装基础工具
sudo apt install -y \\
    curl wget vim git htop tree \\
    net-tools dnsutils unzip zip \\
    build-essential man-db

# 3. 配置 Vim（如果习惯用 Vim）
echo 'set number relativenumber' >> ~/.vimrc
echo 'set tabstop=4 shiftwidth=4 expandtab' >> ~/.vimrc

# 4. 配置 Git
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
git config --global init.defaultBranch main

# 5. 安装 Docker（可选但强烈推荐）
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 退出重新登录使组成员生效

# 6. 创建别名（方便日常使用）
echo 'alias ll="ls -la"' >> ~/.bashrc
echo 'alias la="ls -A"' >> ~/.bashrc
echo 'alias ..="cd .."' >> ~/.bashrc
source ~/.bashrc
```

#### 3.3 Ubuntu 桌面环境快速入门

**常用快捷键**：
| 快捷键 | 功能 |
|--------|------|
| `Super` (Win 键) | 打开 Activities 概览 |
| `Ctrl + Alt + T` | 打开终端（**最常用**） |
| `Super + L` | 锁屏 |
| `Super + D` | 显示桌面 |
| `Alt + F4` | 关闭窗口 |
| `Super + Tab` | 切换应用 |
| `Ctrl + Shift + T` | 在终端中打开新标签页 |

**常用命令**：
```bash
# 打开终端后
pwd                    # 当前目录
ls -la                 # 详细列表
cd ~/Documents         # 切换目录
sudo apt update        # 更新软件包
sudo systemctl status nginx  # 查看服务状态
```

---

### 4. SRE 视角：Linux 在生产环境中的角色

#### 4.1 云服务器 Linux 发行版选择

| 场景 | 推荐发行版 | 原因 |
|------|-----------|------|
| 阿里云/腾讯云 ECS | Ubuntu 22.04 LTS / Rocky Linux 9 | 镜像丰富、社区支持好 |
| AWS EC2 | Amazon Linux 2023 / Ubuntu LTS | AWS 官方优化 |
| GCP | Ubuntu LTS / Container-Optimized OS | 镜像完善 |
| 追求稳定性 | Rocky Linux 9 / Debian | 长期支持、版本稳定 |

#### 4.2 真实案例：选错发行版导致的问题

```
案例：某团队用 Ubuntu 16.04 跑生产服务
问题 1：2021 年停止支持，安全漏洞无法修复
问题 2：Python 3.5 停止维护，很多新库装不上
问题 3：Docker 版本太老，不支持最新特性

教训：生产环境必须用 LTS 版本，并关注 EOL 日期
      Ubuntu LTS 10 年支持，Rocky Linux 10 年支持
```

#### 4.3 云服务器初始化清单

```bash
#!/bin/bash
# 服务器初始化脚本 - 适用于新购 Ubuntu/Rocky 服务器

# 1. 系统更新
apt update && apt upgrade -y   # Ubuntu
dnf update -y                  # Rocky/AlmaLinux

# 2. 创建普通用户（禁止直接用 root）
useradd -m -s /bin/bash sreuser
usermod -aG wheel sreuser   # CentOS/Rocky 用 wheel 组
passwd sreuser

# 3. 配置 SSH 密钥登录
mkdir /home/sreuser/.ssh
chmod 700 /home/sreuser/.ssh
# 将公钥添加到 authorized_keys
vim /home/sreuser/.ssh/authorized_keys
chmod 600 /home/sreuser/.ssh/authorized_keys
chown -R sreuser:sreuser /home/sreuser/.ssh

# 4. 禁用密码登录和 root 登录
vim /etc/ssh/sshd_config
# 设置：
# PasswordAuthentication no
# PermitRootLogin no
# PubkeyAuthentication yes
systemctl restart sshd

# 5. 配置防火墙
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable

# 6. 安装基础监控
apt install -y htop nmon iotop
```

---

### 5. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| WSL2 安装失败 | BIOS 未开启虚拟化 | 重启 → 进入 BIOS → 启用 Virtualization |
| VirtualBox 虚拟机卡顿 | 内存/CPU 分配不足 | 增加到 4GB+ 内存，2+ CPU |
| Ubuntu 安装黑屏 | 显卡驱动问题 | 添加 `nomodeset` 启动参数 |
| 虚拟机无法联网 | 网络模式不对 | 检查 NAT/桥接模式设置 |
| 共享文件夹不可见 | 未安装增强功能 | 安装 VirtualBox Guest Additions |
| apt update 很慢 | 默认源在国内慢 | 换清华/阿里云镜像源 |
| SSH 连接被拒绝 | 防火墙阻止或服务未启动 | `sudo ufw allow 22/tcp` |
| root 密码遗忘 | - | 单用户模式重置密码 |
"""

def generate_topic_content(day: int, topic: str) -> str:
    """根据主题生成详细的学习内容"""
    
    # 简短主题 -> 详细生成器映射
    topic_lower = topic.lower()
    
    if 'linux简介' in topic_lower or '虚拟机安装' in topic_lower or 'ubuntu' in topic_lower:
        return generate_linux_intro_content(day, topic)
    elif '文件系统' in topic or 'fhs' in topic_lower:
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
    elif '复习' in topic or '综合' in topic or '练习' in topic:
        if day == 7 or day == 14:
            return generate_review_content(day, topic)
        elif day == 28:
            return generate_review_content(day, topic)
        else:
            return generate_review_content(day, topic)
    elif '监控' in topic or 'uptime' in topic_lower or 'free' in topic_lower or 'vmstat' in topic_lower:
        return generate_monitoring_content(day, topic)
    elif '磁盘' in topic or 'fdisk' in topic_lower or 'mkfs' in topic_lower or 'lvm' in topic_lower:
        return generate_disk_content(day, topic)
    elif '日志' in topic or 'journalctl' in topic_lower or 'logrotate' in topic_lower:
        return generate_log_mgmt_content(day, topic)
    elif 'shell脚本' in topic_lower or 'shell' in topic_lower and '基础' in topic:
        return generate_shell_basics_content(day, topic)
    elif '条件' in topic or 'if' in topic_lower or 'elif' in topic_lower or '判断' in topic:
        return generate_shell_condition_content(day, topic)
    elif '循环' in topic or 'for' in topic_lower and '循环' in topic:
        return generate_shell_loop_content(day, topic)
    elif '函数' in topic or 'def' in topic_lower or 'function' in topic_lower:
        return generate_shell_function_content(day, topic)
    elif '字符串' in topic or '调试' in topic or 'trap' in topic_lower or 'set -x' in topic_lower:
        return generate_shell_advanced_content(day, topic)
    elif 'lamp' in topic_lower or 'apache' in topic_lower or 'mysql' in topic_lower:
        return generate_lamp_content(day, topic)
    elif 'socket' in topic_lower or '套接字' in topic:
        return generate_socket_content(day, topic)
    else:
        return generate_default_content(day, topic)

def generate_process_content(day: int, topic: str) -> str:
    """进程管理基础内容生成器"""
    return f"""### 1. 学习主题概述

{topic}

#### 1.1 什么是进程

进程（Process）是运行中的程序，是操作系统进行资源分配和调度的基本单位。每个进程都有独立的内存空间、文件描述符和进程ID（PID）。

#### 1.2 进程的状态

| 状态 | 含义 |
|------|------|
| R (Running) | 正在运行或就绪运行 |
| S (Sleeping) | 可中断的睡眠状态 |
| D (Disk Sleep) | 不可中断的睡眠状态 |
| T (Stopped) | 停止状态 |
| Z (Zombie) | 僵尸进程 |

---

### 2. 进程管理命令

#### 2.1 查看进程

```bash
# 查看所有进程（完整格式）
ps aux

# 查看进程树
ps -ef --forest

# 实时显示进程（类似任务管理器）
top
htop

# 查看特定进程
ps aux | grep nginx
pgrep -f nginx
```

#### 2.2 进程状态与信号

| 信号 | 编号 | 含义 |
|------|------|------|
| SIGTERM | 15 | 请求终止（优雅退出） |
| SIGKILL | 9 | 强制终止 |
| SIGSTOP | 19 | 暂停进程 |
| SIGCONT | 18 | 继续运行 |

```bash
# 发送信号
kill -15 <PID>    # 优雅终止
kill -9 <PID>     # 强制终止
kill -STOP <PID>  # 暂停进程
kill -CONT <PID>  # 继续运行

# 批量操作
killall nginx       # 按名称终止
pkill -f nginx      # 按名称终止（支持正则）
```

#### 2.3 进程优先级

```bash
# 查看优先级
ps -eo pid,ni,cmd

# 启动低优先级进程
nice -n 10 ./script.sh

# 调整运行中进程优先级
renice -n 5 -p <PID>
```

---

### 3. 实战练习

#### 练习 1：基础进程查看

```bash
# 1. 列出当前用户的所有进程
ps -u $USER

# 2. 按CPU使用率排序
ps aux --sort=-%cpu

# 3. 查看进程的父子关系
ps -ef | head -20
```

#### 练习 2：进程控制

```bash
# 1. 启动一个后台进程
sleep 300 &

# 2. 查看后台任务
jobs -l

# 3. 将后台任务调到前台
fg %1

# 4. 暂停当前任务，按Ctrl+Z
```

#### 练习 3：进程监控

```bash
# 1. 实时监控进程，按内存排序
top -o %MEM

# 2. 查看某个用户的进程统计
ps -U www-data -o pid,vsz,rss,pcpu,pmem,comm

# 3. 计算进程数
ps aux | wc -l
```

---

### 4. 常见问题

| 问题 | 解决方案 |
|------|----------|
| 进程僵死无法终止 | 使用 `kill -9`，检查父进程是否未wait |
| 僵尸进程过多 | 找到父进程并修复或终止父进程 |
| CPU 100% | 使用 `top` 定位高CPU进程，分析代码 |
| 进程意外退出 | 检查 dmesg 日志、OOM Killer |

---

### 5. 扩展阅读

- `man ps`、`man top`、`man kill` — 命令手册
- `/proc/<PID>/` — 进程详细信息目录
- `pstree` — 进程树形视图
- 进程组与会话：`ps -o pid,pgid,sid,comm`
"""

def generate_systemd_content(day: int, topic: str) -> str:
    """systemd 基础内容生成器"""
    return f"""### 1. 学习主题概述

{topic}

#### 1.1 什么是 systemd

systemd 是 Linux 系统中主要的系统和服务管理器，取代了传统的 SysV init 系统。它采用并行启动机制，大大加快了系统启动速度。systemd 的核心概念是**单元（Unit）**，包括服务单元、挂载单元、套接字单元等。

#### 1.2 systemd 架构

| 组件 | 说明 |
|------|------|
| systemd | 主进程（PID 1），管理系统生命周期 |
| systemctl | 命令行管理工具 |
| systemd-analyze | 分析启动性能 |
| journalctl | 查看日志 |
| systemd-run | 运行临时或瞬态单元 |

---

### 2. systemctl 基础命令

#### 2.1 服务管理

```bash
# 启动服务
sudo systemctl start nginx

# 停止服务
sudo systemctl stop nginx

# 重启服务
sudo systemctl restart nginx

# 重新加载配置（不中断连接）
sudo systemctl reload nginx

# 查看服务状态
sudo systemctl status nginx
```

#### 2.2 开机自启管理

```bash
# 启用开机自启
sudo systemctl enable nginx

# 禁用开机自启
sudo systemctl disable nginx

# 检查是否启用
systemctl is-enabled nginx

# 重新加载 systemd 配置
sudo systemctl daemon-reload
```

#### 2.3 查看系统状态

```bash
# 查看所有运行中的单元
systemctl list-units --type=service --state=running

# 查看失败的单元
systemctl --failed --type=service

# 查看所有已加载的单元
systemctl list-unit-files
```

---

### 3. systemd 单元文件

#### 3.1 单元文件位置

| 路径 | 说明 |
|------|------|
| `/etc/systemd/system/` | 系统管理员创建的服务 |
| `/run/systemd/system/` | 运行时生成的服务 |
| `/usr/lib/systemd/system/` | 软件包安装的服务 |

#### 3.2 服务单元文件示例

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application Server
Documentation=https://myapp.example.com
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=www-data
Group=www-data
ExecStart=/usr/bin/python3 /opt/myapp/server.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=30
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 3.3 常用 [Service] 类型

| Type | 说明 | 适用场景 |
|------|------|---------|
| simple | 主进程即为服务进程 | 大多数服务 |
| forking | 主进程 fork 子进程 | 传统守护进程 |
| oneshot | 执行一次就退出 | 一次性任务 |
| notify | 进程启动后发送就绪通知 | 复杂服务 |
| dbus | 依赖 D-Bus 信号 | 需要 D-Bus 的服务 |

#### 3.4 常用 [Unit] 指令

| 指令 | 说明 |
|------|------|
| Description | 单元描述 |
| Documentation | 文档链接 |
| After | 在哪些单元之后启动 |
| Before | 在哪些单元之前启动 |
| Wants | 弱依赖（启动此单元时也启动所列单元） |
| Requires | 强依赖（所列单元失败则此单元也失败） |
| WantedBy | 哪个 target 包含此单元 |

---

### 4. systemd 常用 target

```bash
# 查看当前 target
systemctl get-default

# 切换 target（临时）
sudo systemctl isolate multi-user.target

# 设置默认 target
sudo systemctl set-default multi-user.target

# 列出所有 target
systemctl list-units --type=target --all
```

| Target | 说明 | 对应 SysV 运行级别 |
|--------|------|-------------------|
| poweroff.target | 系统关机 | runlevel 0 |
| rescue.target | 救援模式 | runlevel 1 |
| multi-user.target | 多用户（无图形） | runlevel 3 |
| graphical.target | 多用户（带图形） | runlevel 5 |
| reboot.target | 重启 | runlevel 6 |

---

### 5. 日志管理（journalctl）

```bash
# 查看所有日志
sudo journalctl

# 查看当前启动日志
journalctl -b

# 查看上次启动日志
journalctl -b -1

# 实时跟踪日志
journalctl -f

# 查看特定服务的日志
journalctl -u nginx

# 按时间范围过滤
journalctl --since "10 minutes ago"
journalctl --since "2024-01-01 00:00:00" --until "2024-01-01 12:00:00"

# 查看错误级别日志
journalctl -p err

# 日志占用空间
journalctl --disk-usage

# 清理旧日志
sudo journalctl --vacuum-size=500M
```

---

### 6. 实战练习

#### 练习 1：创建一个简单的 systemd 服务

```bash
# 1. 创建 Python 测试脚本
sudo tee /opt/hello.py << 'EOF'
#!/usr/bin/env python3
import time
while True:
    print("Hello from systemd service!")
    time.sleep(30)
EOF
sudo chmod +x /opt/hello.py

# 2. 创建服务单元文件
sudo tee /etc/systemd/system/hello.service << 'EOF'
[Unit]
Description=Hello World Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/hello.py
Restart=on-failure
User=www-data

[Install]
WantedBy=multi-user.target
EOF

# 3. 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable hello
sudo systemctl start hello

# 4. 检查状态
systemctl status hello
journalctl -u hello -f
```

#### 练习 2：分析系统启动性能

```bash
# 查看启动时间分析
systemd-analyze

# 查看各服务启动耗时
systemd-analyze blame

# 查看关键链（最耗时路径）
systemd-analyze critical-chain

# 保存启动报告
systemd-analyze plot > startup.svg
```

#### 练习 3：服务管理实战

```bash
# 1. 查看 nginx 服务状态
systemctl status nginx

# 2. 查看 nginx 的依赖关系
systemctl list-dependencies nginx

# 3. 强制重启服务（模拟故障恢复）
sudo systemctl try-restart nginx

# 4. 查看服务是否配置为开机自启
systemctl is-enabled nginx
```

---

### 7. 常见问题

| 问题 | 解决方案 |
|------|----------|
| 服务启动失败 | `journalctl -u <服务名>` 查看日志 |
| 服务一直重启 | 检查 `Restart=on-failure` 配置，增加 `RestartSec` |
| 开机未自启 | `systemctl enable <服务>` 并 `daemon-reload` |
| 端口被占用 | `ss -tlnp` 或 `lsof -i :端口` 查找冲突进程 |
| 服务卡住无法停止 | `sudo systemctl kill -s KILL <服务名>` |

---

### 8. 扩展阅读

- `man systemctl` — systemctl 完整手册
- `man systemd.unit` — 单元文件格式
- `man journalctl` — 日志查看器手册
- `man systemd.service` — 服务单元配置
- systemd 官方文档：https://www.freedesktop.org/wiki/Software/systemd/
"""

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

def generate_socket_content(day: int, topic: str) -> str:
    """Socket 编程基础 — Python socket 模块详解"""
    content = """### 1. Socket 编程概述

#### 1.1 什么是 Socket

Socket（套接字）是操作系统提供的**网络通信端点抽象**，是进程间网络通信的基础。可以理解为网络通信的"插座"——一端插着客户端，一端插着服务端，数据通过它们流动。

```
客户端 Socket                    服务端 Socket
   │                                │
   ├── connect() ───────────────────►│
   │         SYN                    │
   │◄───────────────────────────────┤
   │         SYN+ACK                │
   │                                │
   ├── ACK ─────────────────────────►│
   │                                │
   ├── send(data) ─────────────────►│
   │                                ├── recv(data)
   │◄───────────────────────────────┤
   │         response               │
   │                                │
   └── close() ────────────────────►│
```

#### 1.2 Socket 的类型

| 类型 | 常量 | 协议 | 特点 | SRE 场景 |
|------|------|------|------|----------|
| 流式 Socket | `SOCK_STREAM` | TCP | 可靠、有序、面向连接 | Web 服务、数据库连接 |
| 数据报 Socket | `SOCK_DGRAM` | UDP | 无连接、不可靠、低延迟 | DNS 查询、监控指标上报 |
| 原始 Socket | `SOCK_RAW` | Raw IP | 直接操作 IP 层 | 抓包工具、网络诊断 |

#### 1.3 Socket 地址族

| 地址族 | 常量 | 说明 | 示例 |
|--------|------|------|------|
| IPv4 | `AF_INET` | 最常用的地址族 | `('192.168.1.1', 8080)` |
| IPv6 | `AF_INET6` | 下一代 IP 协议 | `('::1', 8080)` |
| Unix 域 | `AF_UNIX` | 本地进程间通信 | `/var/run/app.sock` |

---

### 2. TCP Socket 编程（面向连接）

#### 2.1 服务端 Socket 生命周期

```
socket() → bind() → listen() → accept() → recv()/send() → close()
```

```python
# === TCP 服务端 ===
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 避免 Address already in use

server.bind(('0.0.0.0', 9999))  # 监听所有网卡
server.listen(5)                # 最多 5 个连接排队
print("Server listening on port 9999...")

while True:
    client_socket, client_addr = server.accept()
    print(f"Connection from {client_addr}")

    data = client_socket.recv(4096)  # 接收最多 4096 字节
    print(f"Received: {data.decode()}")

    client_socket.sendall(b"Hello from server!")
    client_socket.close()
```

#### 2.2 客户端 Socket

```python
# === TCP 客户端 ===
import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 9999))

client.sendall(b"Hello from client!")
response = client.recv(4096)
print(f"Server replied: {response.decode()}")

client.close()
```

#### 2.3 关键 API 详解

| 方法 | 说明 | 参数/返回值 |
|------|------|-------------|
| `socket(family, type)` | 创建 socket | 返回 socket 对象 |
| `bind((host, port))` | 绑定地址和端口 | 无返回值 |
| `listen(backlog)` | 开始监听 | backlog=等待队列长度 |
| `accept()` | 接受连接 | 返回 `(client_socket, address)` |
| `connect((host, port))` | 连接服务端 | 无返回值 |
| `recv(bufsize)` | 接收数据 | 返回 bytes |
| `send(data)` | 发送数据 | 返回发送字节数 |
| `sendall(data)` | 发送全部数据 | 确保所有数据发出 |
| `close()` | 关闭连接 | 无返回值 |
| `settimeout(seconds)` | 设置超时 | 避免永久阻塞 |

---

### 3. UDP Socket 编程（无连接）

```python
# === UDP 服务端 ===
import socket

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind(('0.0.0.0', 9998))

while True:
    data, client_addr = server.recvfrom(4096)
    print(f"From {client_addr}: {data.decode()}")
    server.sendto(b"ACK", client_addr)

# === UDP 客户端 ===
import socket

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.sendto(b"Hello UDP!", ('127.0.0.1', 9998))
data, server = client.recvfrom(4096)
print(f"Server: {data.decode()}")
client.close()
```

**TCP vs UDP 对比**：

| 特性 | TCP (SOCK_STREAM) | UDP (SOCK_DGRAM) |
|------|-------------------|-------------------|
| 连接 | 需要三次握手 | 无需连接 |
| 可靠性 | 保证送达、有序 | 不保证送达、可能乱序 |
| 速度 | 较慢（握手+确认） | 快（直接发送） |
| 流量控制 | 滑动窗口 | 无 |
| 适用场景 | HTTP、SSH、数据库 | DNS、监控、视频流 |

---

### 4. SRE 实战：Socket 编程应用场景

#### 4.1 健康检查探针

```python
#!/usr/bin/env python3
# SRE 健康检查工具 — 检测服务端口连通性
import socket
import sys
from datetime import datetime

def check_port(host, port, timeout=3.0):
    # 检测端口是否可达
    start = datetime.now()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        elapsed = (datetime.now() - start).total_seconds() * 1000
        sock.close()
        return {"host": host, "port": port, "status": "UP", "latency_ms": "%.1f" % elapsed}
    except socket.timeout:
        return {"host": host, "port": port, "status": "TIMEOUT", "latency_ms": ">3000"}
    except ConnectionRefusedError:
        return {"host": host, "port": port, "status": "REFUSED", "latency_ms": "-"}
    except Exception as e:
        return {"host": host, "port": port, "status": "ERROR", "latency_ms": "-", "error": str(e)}

# 检查一组关键服务
services = [
    ("127.0.0.1", 80),    # Nginx
    ("127.0.0.1", 443),   # HTTPS
    ("127.0.0.1", 3306),  # MySQL
    ("127.0.0.1", 6379),  # Redis
    ("127.0.0.1", 8080),  # App Server
]

for host, port in services:
    result = check_port(host, port)
    status_icon = "OK" if result["status"] == "UP" else "FAIL"
    print("%s %s:%s - %s (%sms)" % (
        status_icon, result['host'], result['port'],
        result['status'], result['latency_ms']))
```

#### 4.2 简易 HTTP 客户端（原始 Socket）

```python
import socket

def http_get(host, port, path="/"):
    # 用原始 Socket 发送 HTTP GET 请求
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((host, port))

    request = "GET %s HTTP/1.1\\r\\nHost: %s\\r\\nConnection: close\\r\\n\\r\\n" % (path, host)
    sock.sendall(request.encode())

    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

    sock.close()
    return response.decode()

# 使用示例
resp = http_get("example.com", 80, "/")
print(resp[:500])  # 打印前 500 字符
```

#### 4.3 Unix Domain Socket — 进程间通信

```python
import socket
import os

SOCK_PATH = "/tmp/sre_app.sock"

# 服务端
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
if os.path.exists(SOCK_PATH):
    os.unlink(SOCK_PATH)
server.bind(SOCK_PATH)
server.listen(1)
conn, _ = server.accept()
data = conn.recv(1024)
conn.sendall(b"ACK from Unix socket")
conn.close()

# 客户端（同一台机器上更快，无需网络栈）
client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client.connect(SOCK_PATH)
client.sendall(b"Hello via Unix socket")
print(client.recv(1024).decode())
client.close()
```

**Unix Domain Socket vs TCP localhost**：
- Unix Domain Socket 不需要经过 TCP/IP 协议栈
- 性能比 TCP localhost 高 **2-5 倍**
- 适合微服务间本地通信（如 Nginx → uWSGI）

---

### 5. Socket 选项与调优

#### 5.1 常用 Socket 选项

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 地址复用 — 避免 TIME_WAIT 导致的 "Address already in use"
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 发送/接收缓冲区大小
sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)

# TCP Keepalive — 检测死连接
sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)    # 空闲 60 秒后开始探测
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)   # 每 10 秒探测一次
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)      # 最多探测 6 次

# 禁用 Nagle 算法 — 降低延迟（适合实时应用）
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
```

#### 5.2 TIME_WAIT 问题

```bash
# 查看 TIME_WAIT 连接数量
ss -tan state time-wait | wc -l

# 查看连接状态分布
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn

# 内核调优（/etc/sysctl.conf）
# net.ipv4.tcp_tw_reuse = 1     # 允许重用 TIME_WAIT 连接
# net.ipv4.tcp_max_tw_buckets = 262144  # TIME_WAIT 桶大小
# net.ipv4.tcp_fin_timeout = 30 # FIN-WAIT-2 超时
```

---

### 6. 常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `Address already in use` | 端口被占用或 TIME_WAIT | 设置 `SO_REUSEADDR`，或换端口 |
| `Connection refused` | 目标端口没有监听 | 检查服务是否启动、防火墙规则 |
| `Connection timed out` | 网络不通或防火墙拦截 | `ping` 测试，检查 `iptables`/安全组 |
| `Broken pipe` | 对端已关闭连接 | 检查连接状态，处理异常 |
| 中文乱码 | 编码不一致 | 统一使用 UTF-8，`data.decode('utf-8')` |
| 接收数据不完整 | TCP 是流协议，一次 recv 不等于一次 send | 循环 recv 直到收到完整消息 |

---

### 7. 扩展阅读

- **Python 官方文档**: `socket` module — https://docs.python.org/3/library/socket.html
- **Beej's Guide to Network Programming**: 经典网络编程教程 — https://beej.us/guide/bgnet/
- **`selectors` 模块**: Python 多路复用 I/O（适合高并发服务端）
- **`asyncio`**: Python 异步网络编程（现代推荐方案）
"""
    # No f-string interpolation needed for this content
    return content

def generate_default_content(day: int, topic: str) -> str:
    """改进的默认内容生成器（适用于未专门定义的主题）"""

    # Topic-based content mapping for Phase 2-8
    topic_content_map = {
        # Phase 2: Networking
        'osi': generate_network_osi_content,
        'tcp': generate_network_tcp_content,
        'udp': generate_network_basic_content,
        'ip': generate_network_basic_content,
        'dns': generate_network_dns_content,
        'ping': generate_network_basic_content,
        'tcpdump': generate_network_basic_content,
        'iptables': generate_network_basic_content,
        'http': generate_network_basic_content,
        'socket': generate_network_basic_content,

        # Phase 3: Python
        'python': generate_python_basic_content,
        '函数': generate_python_basic_content,
        '模块': generate_python_basic_content,
        '文件': generate_python_basic_content,
        '异常': generate_python_basic_content,
        '正则': generate_python_basic_content,
        '面向对象': generate_python_basic_content,
        '装饰器': generate_python_basic_content,
        '多线程': generate_python_basic_content,
        '网络编程': generate_python_basic_content,
        'requests': generate_python_basic_content,

        # Phase 4: Docker
        'docker': generate_docker_basic_content,
        '镜像': generate_docker_basic_content,
        '容器': generate_docker_basic_content,
        'compose': generate_docker_basic_content,
        '私有': generate_docker_basic_content,
        '安全': generate_docker_basic_content,

        # Phase 5: AWS & IaC
        'aws': generate_cloud_basic_content,
        'ec2': generate_cloud_basic_content,
        'vpc': generate_cloud_basic_content,
        'terraform': generate_iac_basic_content,
        'ansible': generate_iac_basic_content,

        # Phase 6: Observability
        'prometheus': generate_observability_basic_content,
        'grafana': generate_observability_basic_content,
        'alertmanager': generate_observability_basic_content,
        'elk': generate_observability_basic_content,
        'loki': generate_observability_basic_content,
        'jaeger': generate_observability_basic_content,

        # Phase 7: CI/CD
        'ci/cd': generate_cicd_basic_content,
        'github': generate_cicd_basic_content,
        'jenkins': generate_cicd_basic_content,
        'argocd': generate_cicd_basic_content,
        '部署': generate_cicd_basic_content,
        'vault': generate_cicd_basic_content,

        # Phase 8: SRE Practice
        'on-call': generate_sre_practice_content,
        '事故': generate_sre_practice_content,
        'slo': generate_sre_practice_content,
        '容量': generate_sre_practice_content,
        '灾备': generate_sre_practice_content,
        '面试': generate_sre_practice_content,
    }

    topic_lower = topic.lower()
    for keyword, generator in topic_content_map.items():
        if keyword in topic_lower:
            return generator(day, topic)

    # Fallback: improved generic template
    return f"""### 1. {topic} — 核心概念

{topic} 是 SRE 工程师必须掌握的重要技能。

#### 1.1 基础知识

- 理解{topic}的基本原理和架构
- 掌握常用命令和操作方式
- 能够在实际工作场景中应用

#### 1.2 SRE 实战场景

在生产环境中，{topic}的应用场景包括：
- **日常运维**：定期检查和维护
- **故障排查**：快速定位和解决问题
- **自动化**：编写脚本实现自动化管理

```bash
# 基础操作示例
# 根据{topic}主题执行相关命令
# 参考官方文档获取详细信息
```

---

### 2. 实际操作

#### 2.1 基础练习

```bash
# 练习 1：基础命令
# 查阅官方文档，完成基本操作
```

#### 2.2 进阶练习

```bash
# 练习 2：结合实际场景
# 尝试在测试环境中模拟生产问题
```

---

### 3. 常见问题

| 问题 | 排查思路 |
|------|---------|
| 服务无法启动 | 检查日志、端口占用、配置文件 |
| 性能下降 | 监控资源使用、检查瓶颈 |
| 连接失败 | 检查网络、防火墙、服务状态 |

---

### 4. 扩展阅读

- 查阅官方文档获取最准确的信息
- 参考相关技术博客和教程
- 在测试环境中反复练习
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

{generate_practice_section(day, topic)}

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
    parser = argparse.ArgumentParser(description="SRE 每日学习资料生成器")
    parser.add_argument('--day', type=int, default=None,
                        help='指定 Day 编号（不指定则自动计算当天）')
    parser.add_argument('--date', type=str, default=None,
                        help='指定日期（格式: YYYY-MM-DD），用于计算 Day 编号')
    args = parser.parse_args()
    
    print("=" * 60)
    print("📅 SRE 每日学习资料生成器")
    print("=" * 60)
    
    # 配置 Git
    git_config()
    
    # 计算天数
    if args.day is not None:
        day = args.day
        print(f"指定 Day {day}")
    elif args.date:
        target = datetime.strptime(args.date, '%Y-%m-%d').date()
        day = (target - START_DATE).days + 1
        print(f"指定日期 {args.date} -> Day {day}")
    else:
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


# ============ Additional Content Generators ============
# Added during review and revision - covers topics that previously fell back to generic template

def generate_monitoring_content(day, topic):
    """System monitoring commands - Day 11"""
    return """### 1. 系统负载监控

#### 1.1 uptime 与 Load Average

Load Average 表示 1/5/15 分钟内的平均负载（运行队列中的进程数）。

**SRE 经验法则**：load < CPU 核数 = 健康；load > CPU 核数 = 过载。

```bash
$ uptime
 14:30:25 up 30 days, 2:15,  load average: 0.50, 1.20, 0.80
```

**SRE 实战排查**：
```bash
# 生产告警：load 15.2（4 核机器）→ 严重过载！

# 定位高 CPU 进程
ps aux --sort=-%cpu | head -10

# 查看进程状态分布
ps aux | awk '{print $8}' | sort | uniq -c
# D（不可中断睡眠）太多 = IO 等待
# R（运行）太多 = CPU 瓶颈

# 查看 IO 等待
vmstat 1 5
# wa 高 = 磁盘瓶颈
```

#### 1.2 free — 内存监控

**关键**：看 `available` 而非 `free`！Linux 会用空闲内存做缓存。

```bash
$ free -h
              total   used   free   buff/cache   available
Mem:           16Gi   8.2Gi  1.1Gi     6.7Gi       7.3Gi
```

```bash
# 真正的内存问题：available 很低 + swap 持续增加 = OOM 风险
dmesg | grep -i "out of memory"
dmesg | grep -i "killed process"
```

#### 1.3 df/du — 磁盘

```bash
df -h                    # 磁盘使用率
df -i                    # inode 使用率
du -sh /* 2>/dev/null | sort -rh | head -10  # 大目录
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null  # 大文件
```

#### 1.4 vmstat — 综合性能

```bash
vmstat 1 5
# r > CPU 核数 = CPU 瓶颈
# b > 0 = 磁盘瓶颈
# si/so > 0 = 内存不足
# wa 高 = IO 等待
```

#### 1.5 sar — 历史数据回溯

```bash
# 启用 sysstat
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat

sar -u    # CPU 历史
sar -r    # 内存历史
sar -d    # 磁盘 IO 历史
sar -n DEV  # 网络历史
```

---

### 2. SRE 实战：一键健康检查脚本

```bash
#!/bin/bash
echo "=== 健康检查 $(date) ==="
echo "负载: $(uptime | awk -F'load average:' '{print $2}')"
echo "内存:"; free -h | grep Mem
echo "磁盘:"; df -h / | tail -1
echo "Top CPU:"; ps aux --sort=-%cpu | head -4
echo "Top MEM:"; ps aux --sort=-%mem | head -4
echo "IO 等待:"; vmstat 1 1 | tail -1
echo "错误日志:"; journalctl -p err --since "5 min ago" --no-pager | tail -3
```

---

### 3. 常见问题

| 问题 | 排查思路 |
|------|---------|
| Load 高但 CPU 使用率低 | 检查 vmstat 的 wa，可能是磁盘瓶颈 |
| 内存告警但 available 充足 | 正常！Linux 用空闲内存做缓存 |
| Swap 持续增加 | 内存不足，排查内存泄漏 |
| 磁盘使用率持续增长 | 检查日志轮转配置、临时文件 |
"""


def generate_disk_content(day, topic):
    """Disk management - Day 12"""
    return """### 1. 磁盘设备与分区

#### 1.1 磁盘设备命名

| 类型 | 命名 | 说明 |
|------|------|------|
| SATA | `/dev/sda` | 传统磁盘 |
| NVMe | `/dev/nvme0n1` | 高速 SSD |
| 云盘 | `/dev/vda` | KVM 虚拟化 |

```bash
lsblk              # 查看磁盘和分区
sudo fdisk -l      # 详细信息
```

#### 1.2 分区与格式化

```bash
# MBR 分区（< 2TB）
sudo fdisk /dev/sdb
# n → p → 1 → Enter → Enter → w

# GPT 分区（> 2TB）
sudo parted /dev/sdb mklabel gpt
sudo parted /dev/sdb mkpart primary ext4 0% 100%

# 格式化
sudo mkfs.ext4 /dev/sdb1
```

#### 1.3 挂载管理

```bash
# 挂载
sudo mount /dev/sdb1 /data

# 开机自动挂载（编辑 /etc/fstab）
echo '/dev/sdb1 /data ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
sudo mount -a   # 测试（重要！）

# 查看挂载
findmnt /data
```

#### 1.4 LVM 逻辑卷

```bash
sudo pvcreate /dev/sdb /dev/sdc
sudo vgcreate vg_data /dev/sdb /dev/sdc
sudo lvcreate -L 100G -n lv_app vg_data
sudo mkfs.ext4 /dev/vg_data/lv_app

# 在线扩容
sudo lvextend -L +50G /dev/vg_data/lv_app
sudo resize2fs /dev/vg_data/lv_app
```

---

### 2. SRE 实战

**磁盘告警排查**：
```bash
# 1. 定位大目录
du -sh /* 2>/dev/null | sort -rh | head -5

# 2. inode 耗尽
df -i

# 3. 已删除但未释放的文件
lsof +L1

# 4. 找出 > 100MB 的文件
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null
```
"""


def generate_log_mgmt_content(day, topic):
    """Log management - Day 13"""
    return """### 1. 日志体系

#### 1.1 重要日志文件

| 日志 | 用途 |
|------|------|
| `/var/log/syslog` | 系统日志（Ubuntu） |
| `/var/log/auth.log` | 认证/登录日志 |
| `/var/log/kern.log` | 内核日志 |
| `/var/log/nginx/` | Nginx 访问和错误日志 |
| `/var/log/journal/` | systemd journal |

#### 1.2 journalctl 高级用法

```bash
journalctl -f                          # 实时跟踪
journalctl -u nginx --since "1h ago"   # 服务日志
journalctl -p err                      # 错误级别
journalctl --disk-usage                # 占用空间
sudo journalctl --vacuum-size=500M    # 清理
```

#### 1.3 logrotate 日志轮转

```bash
# 查看现有配置
ls /etc/logrotate.d/

# 常用参数：
# daily/weekly/monthly  — 轮转频率
# rotate N              — 保留 N 个旧文件
# compress              — 压缩旧文件
# size 100M             — 超过此大小才轮转
# missingok             — 文件不存在不报错
```

---

### 2. SRE 实战

**日志爆满应急**：
```bash
# 不能直接 rm！（进程持有文件描述符，空间不释放）
# 正确做法：清空文件
> /var/log/nginx/access.log

# 安全审计：暴力破解检测
grep "Failed password" /var/log/auth.log | \
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -10

# Nginx 日志分析
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn
awk '$9 >= 500' /var/log/nginx/access.log | head -20
```
"""


def generate_shell_basics_content(day, topic):
    """Shell script basics - Day 15"""
    return """### 1. Shell 脚本入门

#### 1.1 第一个脚本

```bash
#!/bin/bash
echo "主机名: $(hostname)"
echo "当前用户: $(whoami)"
echo "当前时间: $(date)"
echo "内核版本: $(uname -r)"
```

#### 1.2 变量与引号

```bash
NAME="SRE Engineer"
echo "欢迎 $NAME"           # 双引号：变量展开
echo '欢迎 $NAME'           # 单引号：字面量
echo "时间: $(date)"        # 命令替换

# 安全做法（防止变量为空导致灾难）
DIR="/backup"
rm -rf "${DIR:?Variable DIR is not set}"/*

# 默认值
echo "服务器: ${SERVER:-localhost}"
```

#### 1.3 环境变量

```bash
export MY_VAR="hello"
env | grep MY_VAR
```

---

### 2. SRE 实战

**系统信息报告**：
```bash
#!/bin/bash
{
    echo "===== 系统报告 $(date) ====="
    echo "负载:"; uptime
    echo "内存:"; free -h
    echo "磁盘:"; df -h | grep -v tmpfs
    echo "Top CPU:"; ps aux --sort=-%cpu | head -4
} > "/tmp/report_$(date +%Y%m%d).txt"
```

**服务健康检查**：
```bash
#!/bin/bash
for svc in nginx mysql docker; do
    if systemctl is-active --quiet "$svc"; then
        echo "✅ $svc: running"
    else
        echo "❌ $svc: stopped"
    fi
done
```

**调试技巧**：`bash -x script.sh` / `set -euo pipefail`
"""


def generate_shell_condition_content(day, topic):
    """Shell conditionals - Day 16"""
    return """### 1. 条件判断基础

#### 1.1 文件测试

```bash
[ -f /etc/nginx/nginx.conf ]    # 文件存在
[ -d /var/log/nginx ]           # 目录存在
[ -s /var/log/syslog ]          # 文件非空
[ -r /etc/shadow ]              # 可读
[ -x /usr/bin/nginx ]           # 可执行
```

#### 1.2 字符串和数值比较

```bash
# 字符串
[ "$STATUS" = "running" ]
[ -z "$VAR" ]       # 空
[ -n "$VAR" ]       # 非空

# 数值：-eq(等于) -ne -gt(大于) -ge -lt -le
[ "$CPU" -gt 80 ]

# 推荐 [[ ]]（支持 && || 和正则）
[[ "$STATUS" == "running" && "$CPU" -gt 80 ]]
```

---

### 2. SRE 实战

**磁盘检查脚本**：
```bash
#!/bin/bash
set -euo pipefail
THRESHOLD=90
USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    echo "❌ 磁盘 ${USAGE}% > ${THRESHOLD}%，立即清理！"
elif [ "$USAGE" -gt 80 ]; then
    echo "⚠️ 磁盘 ${USAGE}%，请关注"
else
    echo "✅ 磁盘 ${USAGE}%，正常"
fi
```

**服务健康检查**：
```bash
#!/bin/bash
check_service() {
    local service=$1
    if ! systemctl is-active --quiet "$service"; then
        echo "❌ $service 未运行！尝试重启..."
        systemctl restart "$service" || {
            echo "❌ 重启失败！"
            return 1
        }
        echo "✅ $service 已重启"
    else
        echo "✅ $service 运行正常"
    fi
}
for svc in nginx mysql docker; do
    check_service "$svc"
done
```
"""


def generate_shell_loop_content(day, topic):
    """Shell loops - Day 17"""
    return """### 1. 循环基础

#### 1.1 for 循环

```bash
# 遍历列表
for server in web01 web02 db01; do
    echo "检查 $server..."
    ssh "$server" "uptime"
done

# 数字范围
for i in $(seq 1 10); do
    echo "服务器 $i"
done

# 遍历文件
for log in /var/log/nginx/*.log; do
    echo "处理: $(basename $log)"
    wc -l "$log"
done
```

#### 1.2 while 循环

```bash
# 逐行读取文件
while IFS= read -r line; do
    echo "用户: $line"
done < /etc/passwd
```

---

### 2. SRE 实战

**批量服务器巡检**：
```bash
#!/bin/bash
for server in $(cat servers.txt); do
    echo "=== $server ==="
    ssh "$server" "uptime; df -h / | tail -1"
    echo ""
done
```

**并行巡检（加速）**：
```bash
#!/bin/bash
for server in $(cat servers.txt); do
    (
        echo "=== $server ==="
        ssh "$server" "uptime; df -h /"
    ) &
done
wait  # 等待所有后台任务完成
```
"""


def generate_shell_function_content(day, topic):
    """Shell functions - Day 18"""
    return """### 1. 函数基础

```bash
# 定义函数
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
}

# 使用
log_info "服务启动中..."
log_error "连接失败！"

# 带参数和返回值
check_port() {
    local host=$1
    local port=$2
    if ss -tlnp | grep -q ":$port "; then
        return 0
    else
        return 1
    fi
}
```

---

### 2. SRE 实战

**服务管理菜单**：
```bash
#!/bin/bash
manage_service() {
    local svc=$1
    case "$2" in
        start)   systemctl start "$svc" ;;
        stop)    systemctl stop "$svc" ;;
        restart) systemctl restart "$svc" ;;
        status)  systemctl status "$svc" --no-pager ;;
        *)       echo "Unknown action: $2" ;;
    esac
}

manage_service nginx restart
```
"""


def generate_shell_advanced_content(day, topic):
    """Shell advanced - Day 21, 22"""
    return """### 1. 字符串处理

```bash
STR="Hello World from SRE"

echo ${#STR}                    # 长度: 21
echo ${STR:0:5}                 # 截取: Hello
echo ${STR/World/Linux}         # 替换: Hello Linux from SRE
echo ${STR// /_}                # 全部替换: Hello_World_from_SRE

# 路径处理
FILE="/var/log/nginx/access.log"
echo ${FILE##*/}                # 文件名: access.log
echo ${FILE%/*}                 # 目录: /var/log/nginx
```

### 2. 调试与信号处理

```bash
# 安全模式（每个脚本开头使用）
set -euo pipefail
# -e: 命令失败时退出
# -u: 使用未定义变量时退出
# -o pipefail: 管道中任何命令失败则退出

# 调试
bash -x script.sh        # 显示每行命令
set -x                   # 开启调试
set +x                   # 关闭调试

# trap 信号处理
cleanup() {
    echo "清理临时文件..."
    rm -f /tmp/my_script_*
}
trap cleanup EXIT

trap 'echo "被中断！"; exit 1' INT TERM
```
"""


def generate_review_content(day, topic):
    """Review and practice - Day 7, 14, 28"""
    return """### Day {day} 复习与实战

#### 场景 1：新购云服务器从零配置

```bash
# 1. 系统更新
sudo apt update && sudo apt upgrade -y

# 2. 创建用户
sudo useradd -m -s /bin/bash -G sudo sreuser

# 3. 安装基础工具
sudo apt install -y curl wget vim git htop tree net-tools

# 4. 配置防火墙
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### 场景 2：日志分析挑战

```bash
# 找出暴力破解的 IP
grep "Failed password" /var/log/auth.log | \\
    awk '{{print $(NF-3)}}' | sort | uniq -c | sort -rn | head -10

# 分析 Nginx 日志
awk '{{print $9}}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# 统计磁盘使用
du -sh /var/log/* | sort -rh | head -10
```

#### 场景 3：权限排查

```bash
# 排查 403 Forbidden
ls -la /var/www/html/
namei -l /var/www/html/index.html
getfacl /var/www/html/
```

#### 自我评估

- [ ] 能否不查阅文档完成常用文件操作？
- [ ] 能否独立排查权限问题？
- [ ] 能否编写基本的 Shell 脚本？
- [ ] 能否分析日志找出问题？
"""


def generate_lamp_content(day, topic):
    """LAMP setup - Day 14"""
    return """### 1. LAMP 环境搭建

#### 1.1 安装 Apache

```bash
sudo apt update
sudo apt install -y apache2
sudo systemctl enable apache2
sudo systemctl start apache2

# 验证
curl -s -o /dev/null -w "%{http_code}" http://localhost
# 应返回 200
```

#### 1.2 安装 MySQL

```bash
sudo apt install -y mysql-server
sudo systemctl enable mysql
sudo mysql -e "CREATE DATABASE myapp CHARACTER SET utf8mb4;"
sudo mysql -e "CREATE USER 'myapp'@'localhost' IDENTIFIED BY 'strong_password';"
sudo mysql -e "GRANT ALL ON myapp.* TO 'myapp'@'localhost';"
```

#### 1.3 安装 PHP

```bash
sudo apt install -y php libapache2-mod-php php-mysql php-curl php-gd
sudo systemctl restart apache2

# 测试
echo '<?php phpinfo(); ?>' | sudo tee /var/www/html/info.php
curl http://localhost/info.php | head -5
```

---

### 2. SRE 最佳实践

```bash
# 安全加固
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 监控脚本
#!/bin/bash
for svc in apache2 mysql; do
    if ! systemctl is-active --quiet "$svc"; then
        echo "❌ $svc 未运行！"
        systemctl restart "$svc"
    else
        echo "✅ $svc 运行正常"
    fi
done
```
"""


# ============ Phase 2-8 Stub Content Generators ============

def generate_network_osi_content(day, topic):
    """Network OSI model - Day 29"""
    return """### Day {day}: OSI 七层模型

#### 1. OSI 七层模型

| 层 | 名称 | 典型协议 | 设备 |
|----|------|---------|------|
| 7 | 应用层 | HTTP/DNS/SSH | 网关 |
| 6 | 表示层 | SSL/TLS/JSON | - |
| 5 | 会话层 | NetBIOS/RPC | - |
| 4 | 传输层 | TCP/UDP | 防火墙 |
| 3 | 网络层 | IP/ICMP | 路由器 |
| 2 | 数据链路层 | Ethernet/ARP | 交换机 |
| 1 | 物理层 | 电缆/光纤 | 集线器 |

**SRE 实战案例**：用户反馈"网站打不开"→ ping 通（网络层 OK）→ telnet 端口不通（传输层/应用层问题）→ 定位到防火墙规则。

#### 2. 数据封装过程

```
应用数据 → TCP 段 → IP 包 → Ethernet 帧 → 比特流
```

#### 3. 练习

- 画出 OSI 模型，标注一次 HTTP 请求经过的每一层
- 用 `ping` 测试网络层连通性
- 用 `traceroute` 追踪数据包路径
"""


def generate_network_tcp_content(day, topic):
    """TCP protocol - Day 30"""
    return """### Day {day}: TCP 协议详解

#### 1. 三次握手与四次挥手

```
三次握手：
Client → SYN → Server
Client ← SYN+ACK ← Server
Client → ACK → Server  (连接建立)

四次挥手：
Client → FIN → Server
Client ← ACK ← Server
Client ← FIN ← Server
Client → ACK → Server  (连接关闭)
```

#### 2. TCP 状态

```bash
# 查看 TCP 连接状态
ss -tan | awk 'NR>1 {print $1}}' | sort | uniq -c
```

**SRE 实战案例**：服务器大量 CLOSE_WAIT → 应用代码未正确关闭连接 → 文件描述符耗尽。

#### 3. 练习

- 用 `ss -tan` 查看 TCP 状态统计
- 用 `tcpdump` 观察三次握手
"""


def generate_network_dns_content(day, topic):
    """DNS - Day 34"""
    return """### Day {day}: DNS 协议

#### 1. DNS 查询过程

```
浏览器缓存 → OS 缓存 → 递归 DNS → 根 DNS → TLD DNS → 权威 DNS
```

#### 2. DNS 记录类型

| 类型 | 用途 | 示例 |
|------|------|------|
| A | IPv4 地址 | 93.184.216.34 |
| AAAA | IPv6 地址 | 2606:2800:220:1:248:1893:25c8:1946 |
| CNAME | 别名 | www → example.com |
| MX | 邮件 | mail.example.com |
| TXT | 验证 | v=spf1 ... |

#### 3. 实用命令

```bash
dig example.com A +short          # 查询 A 记录
dig example.com MX                # 查询 MX 记录
dig example.com +trace            # 追踪完整解析链
nslookup example.com              # 传统查询
```

**SRE 实战案例**：服务调用失败 → nslookup 发现 DNS 解析到错误 IP → 排查到 DNS 缓存未刷新。
"""


def generate_network_basic_content(day, topic):
    """Generic network content"""
    return f"""### 1. {topic}

#### 1.1 基础概念

{topic} 是网络通信的重要组成部分。

#### 1.2 常用命令

```bash
# 网络诊断工具
ping -c 4 example.com           # 测试连通性
traceroute example.com          # 追踪路径
mtr example.com                 # 综合诊断
```

#### 1.3 SRE 实战

- 网络故障排查流程：ping → traceroute → telnet/nc → curl
- 编写网络诊断脚本

#### 1.4 练习

- 使用相关命令进行网络诊断
- 分析网络延迟和丢包
"""


def generate_python_basic_content(day, topic):
    """Python basic content"""
    return f"""### 1. {topic}

#### 1. 基础知识

Python 是 SRE 最常用的脚本语言之一。

#### 2. 核心概念

- 变量和数据结构（列表、字典、元组、集合）
- 控制流程（if/for/while）
- 函数和模块
- 异常处理（try/except）
- 文件和 I/O 操作

```python
# 示例：读取配置文件
import json

with open('config.json') as f:
    config = json.load(f)

print(f"Server: {config['host']}:{config['port']}")
```

#### 3. SRE 实战

- 主机监控脚本（psutil 库）
- 日志分析工具
- API 调用（requests 库）

#### 4. 练习

- 编写 Python 脚本监控系统资源
- 解析 JSON 配置文件
- 调用 REST API
"""


def generate_docker_basic_content(day, topic):
    """Docker basic content"""
    return f"""### 1. {topic}

#### 1. 基础知识

Docker 是容器化技术的核心工具。

#### 2. 常用命令

```bash
docker run -d -p 80:80 --name web nginx
docker ps
docker logs -f web
docker exec -it web bash
docker stop web && docker rm web
```

#### 3. Dockerfile 示例

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

#### 4. SRE 实战

- 容器资源限制（--memory, --cpus）
- 日志轮转配置
- 健康检查

#### 5. 练习

- 编写 Dockerfile 部署应用
- 使用 docker-compose 编排多容器
"""


def generate_cloud_basic_content(day, topic):
    """Cloud/AWS basic content"""
    return f"""### 1. {topic}

#### 1. 基础知识

云平台是现代 SRE 的基础设施。

#### 2. 核心服务

- 计算：EC2（虚拟机）
- 存储：S3（对象存储）、EBS（块存储）
- 网络：VPC（虚拟私有云）
- 数据库：RDS

#### 3. AWS CLI

```bash
aws ec2 describe-instances
aws s3 ls
aws s3 cp local.txt s3://my-bucket/
```

#### 4. SRE 实战

- 使用 IAM 最小权限原则
- 配置安全组和网络 ACL
- 设置 CloudWatch 告警

#### 5. 练习

- 使用 AWS CLI 管理资源
- 设计高可用架构
"""


def generate_iac_basic_content(day, topic):
    """IaC basic content"""
    return "### 1. " + topic + """

#### 1. 基础知识

Infrastructure as Code（IaC）是现代运维的核心实践。

#### 2. Terraform 示例

```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name = "web-server"
  }
}
```

```bash
terraform init
terraform plan
terraform apply
```

#### 3. Ansible 示例

```yaml
- hosts: webservers
  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present
    - name: Start nginx
      service:
        name: nginx
        state: started
```

```bash
ansible-playbook deploy.yml
```

#### 4. SRE 实战

- 版本控制基础设施配置
- 多环境管理（dev/staging/prod）
- 模块化和可复用配置
"""


def generate_observability_basic_content(day, topic):
    """Observability basic content"""
    return "### 1. " + topic + """

#### 1. 基础知识

可观测性三大支柱：Metrics（指标）、Logs（日志）、Traces（链路追踪）。

#### 2. 关键概念

- **SLO**（服务级别目标）：可用性 99.9%
- **错误预算**：100% - SLO = 可接受的故障时间
- **黄金指标**：延迟、流量、错误、饱和度

#### 3. Prometheus 查询示例

```promql
# CPU 使用率
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# QPS
rate(http_requests_total[5m])

# P99 延迟
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

#### 4. SRE 实战

- 定义服务的 SLO
- 配置告警规则
- 创建 Grafana 仪表盘

#### 5. 练习

- 部署 Prometheus + Grafana
- 编写 PromQL 查询
- 配置告警通知
"""


def generate_cicd_basic_content(day, topic):
    """CI/CD basic content"""
    return f"""### 1. {topic}

#### 1. 基础知识

CI/CD 实现自动化构建、测试和部署。

#### 2. GitHub Actions 示例

```yaml
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest
```

#### 3. 部署策略

- **滚动部署**：逐步替换，零停机
- **Blue-Green**：两套环境切换，秒级回滚
- **Canary**：小流量验证，逐步放量

#### 4. SRE 实战

- 代码推送 → 自动构建 → 测试 → 部署
- ArgoCD GitOps 实践
- 金丝雀发布

#### 5. 练习

- 编写 CI Pipeline
- 配置自动部署
"""


def generate_sre_practice_content(day, topic):
    """SRE practice content"""
    return f"""### 1. {topic}

#### 1. 基础知识

SRE（Site Reliability Engineering）是 Google 提出的运维方法论。

#### 2. 核心概念

- **On-Call**：告警分级（P0/P1/P2/P3）
- **事故管理**：分级、响应、RCA 事后复盘
- **SLO**：服务级别目标与错误预算
- **容量规划**：性能测试与扩缩容
- **灾备**：RPO/RTO 指标

#### 3. 实战场景

**事故响应流程**：
1. 告警接收 → 确认故障
2. 快速恢复（回滚/重启/扩容）
3. 根因分析（5 Why 方法）
4. 事后复盘（RCA 报告）
5. 改进措施

**RCA 报告模板**：
- 时间线
- 影响范围
- 根因分析
- 改进措施
- 负责人和截止日期

#### 4. 练习

- 设计 On-Call 流程
- 编写 RCA 报告
- 定义服务的 SLO
"""


# ============ Entry Point ============



def generate_practice_section(day: int, topic: str) -> str:
    """Generate enterprise-level practice sections"""
    topic_lower = topic.lower()
    
    if day == 1 or 'linux' in topic_lower or '虚拟机' in topic_lower or 'ubuntu' in topic_lower:
        return _practice_linux_intro()
    elif day == 2 or '文件系统' in topic_lower or 'fhs' in topic_lower:
        return _practice_fhs()
    elif day == 3 or '文件操作' in topic_lower:
        return _practice_file_ops()
    elif day == 4 or '文本处理' in topic_lower or 'grep' in topic_lower or 'sed' in topic_lower or 'awk' in topic_lower:
        return _practice_text_processing()
    elif day == 5 or '权限' in topic_lower or 'chmod' in topic_lower:
        return _practice_permissions()
    elif day == 6 or '用户' in topic_lower or 'useradd' in topic_lower:
        return _practice_user_mgmt()
    elif day == 7 or day == 14:
        return _practice_review(day)
    elif day == 8 or '进程管理' in topic_lower or 'ps' in topic_lower or 'top' in topic_lower:
        return _practice_process()
    elif day == 9 or '进程控制' in topic_lower or 'kill' in topic_lower:
        return _practice_process_control()
    elif day == 10 or 'systemd' in topic_lower or '服务' in topic_lower:
        return _practice_systemd()
    elif day == 11 or '监控' in topic_lower or 'uptime' in topic_lower:
        return _practice_monitoring()
    elif day == 12 or '磁盘' in topic_lower or 'fdisk' in topic_lower:
        return _practice_disk()
    elif day == 13 or '日志' in topic_lower or 'journalctl' in topic_lower:
        return _practice_log_mgmt()
    elif day == 15 or ('shell' in topic_lower and '基础' in topic_lower):
        return _practice_shell_basics()
    elif day == 16 or '条件' in topic_lower or '判断' in topic_lower:
        return _practice_shell_condition()
    elif day == 17 or '循环' in topic_lower:
        return _practice_shell_loop()
    elif day == 18 or '函数' in topic_lower:
        return _practice_shell_function()
    elif day == 28:
        return _practice_final_review()
    elif day >= 29 and day <= 42:
        return _practice_networking(day)
    elif day >= 43 and day <= 63:
        return _practice_python(day)
    elif day >= 64 and day <= 70:
        return _practice_go(day)
    elif day >= 71 and day <= 84:
        return _practice_docker(day)
    elif day >= 85 and day <= 99:
        return _practice_k8s(day)
    elif day >= 100 and day <= 114:
        return _practice_aws(day)
    elif day >= 115 and day <= 120:
        return _practice_terraform(day)
    elif day >= 121 and day <= 127:
        return _practice_ansible(day)
    elif day >= 128 and day <= 134:
        return _practice_observability(day)
    elif day >= 135 and day <= 141:
        return _practice_logging_tracing(day)
    elif day >= 142 and day <= 148:
        return _practice_cicd(day)
    elif day >= 149 and day <= 155:
        return _practice_devops_advanced(day)
    elif day >= 156 and day <= 162:
        return _practice_sre_core(day)
    elif day >= 163 and day <= 170:
        return _practice_interview(day)
    else:
        return _practice_generic(topic)


def _practice_linux_intro():
    return """### 练习 1：企业级服务器初始化

**场景**：新购 3 台云服务器，30 分钟内完成初始化并交付。

```bash
#!/bin/bash
# enterprise_server_init.sh
set -euo pipefail

# 1. 系统更新与安全补丁
apt update && apt upgrade -y

# 2. 创建运维用户（禁止 root 直接登录）
useradd -m -s /bin/bash -G sudo ops-admin

# 3. SSH 安全加固
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# 4. 防火墙
ufw default deny incoming
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp
ufw enable

# 5. 安装监控基础
apt install -y htop iotop net-tools strace lsof sysstat

echo "服务器初始化完成"
```

### 练习 2：故障排查挑战

**场景**：生产服务器 CPU 持续 100%，10 分钟内定位根因。

```bash
# 定位高 CPU 进程
ps aux --sort=-%cpu | head -5
# 检查进程状态
ps -eo pid,user,%cpu,%mem,stat,comm | sort -k3 -rn | head -10
# 跟踪系统调用
strace -p <PID> -c -s 100
# 检查 IO 等待
iostat -x 1 3
```

### 练习 3：性能基准测试

```bash
# 磁盘性能
dd if=/dev/zero of=/tmp/test bs=1M count=1024 oflag=direct
# 内存性能
sysbench memory --memory-block-size=1M --memory-total-size=10G run
```
"""


def _practice_fhs():
    return """### 练习 1：磁盘空间紧急清理

**场景**：生产服务器 / 分区使用率 98%，立即清理并防止再次发生。

```bash
# 快速定位占用最大的目录
du -sh /* 2>/dev/null | sort -rh | head -10

# 查找大文件（> 100MB）
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null | sort -k5 -rh

# 查找已删除但未释放的文件
lsof +L1 | sort -k7 -rh | head -10

# 安全清理日志
> /var/log/nginx/access.log
journalctl --vacuum-size=500M
apt clean && apt autoremove -y
```

### 练习 2：inode 耗尽排查

```bash
df -i
# 找出大量小文件的目录
for d in /*; do
    count=$(find "$d" -xdev -type f 2>/dev/null | wc -l)
    echo "$count $d"
done | sort -rn | head -10
```

### 练习 3：目录结构审计

```bash
# 检查敏感文件权限
find /etc -name "*.conf" -perm /o+r -ls
find / -name "*.pem" -o -name "*id_rsa*" 2>/dev/null
```
"""


def _practice_file_ops():
    return """### 练习 1：安全批量文件操作

**场景**：备份并迁移 /data/old_app 到 /data/new_app，涉及 10000+ 文件。

```bash
# 使用 rsync 替代 cp（更安全、可断点续传）
BACKUP="/data/backup_$(date +%Y%m%d_%H%M%S)"
rsync -av --progress /data/old_app/ "$BACKUP/"

# 验证备份完整性
diff <(find /data/old_app -type f -exec md5sum {} + | sort) \\
     <(find "$BACKUP" -type f -exec md5sum {} + | sort)

# 安全删除（先 dry run）
rsync -av --delete --dry-run /empty_dir/ /data/old_app/
```

### 练习 2：日志文件生命周期管理

```bash
# 创建 30 天模拟日志
mkdir -p /var/log/test_app
for i in $(seq 1 30); do
    date_str=$(date -d "2026-01-$(printf '%02d' $i)" +%Y-%m-%d)
    echo "[$date_str] INFO: Application started" > "/var/log/test_app/app_${date_str}.log"
done

# 查找 7 天前的日志并压缩
find /var/log/test_app -name "*.log" -mtime +7 -exec gzip {} +
# 删除 30 天前的压缩日志
find /var/log/test_app -name "*.gz" -mtime +30 -delete
```
"""


def _practice_text_processing():
    return """### 练习 1：生产日志分析报告

**场景**：生成 Nginx 每日运营报告，用于早会汇报。

```bash
#!/bin/bash
LOG="/var/log/nginx/access.log"
echo "===== Nginx 日报 $(date +%Y-%m-%d) ====="
echo "总请求数: $(wc -l < $LOG)"
echo "独立 IP:  $(awk '{print $1}' $LOG | sort -u | wc -l)"
echo ""
echo "状态码分布:"
awk '{print $9}' $LOG | sort | uniq -c | sort -rn
echo ""
echo "Top 10 IP:"
awk '{print $1}' $LOG | sort | uniq -c | sort -rn | head -10
echo ""
echo "5xx 错误:"
awk '$9 >= 500 {printf "  %s %s %s\\n", $1, $4, $7}' $LOG | head -20
```

### 练习 2：安全审计脚本

```bash
#!/bin/bash
AUTH_LOG="/var/log/auth.log"
echo "暴力破解尝试:"
grep "Failed password" $AUTH_LOG | \\
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | \\
    awk '$1 > 10 {printf "  %s: %d 次\\n", $2, $1}'

echo "最近登录:"
last -a | head -20
```

### 练习 3：配置文件批量修改

```bash
# 批量替换配置文件中的端口
find /etc/nginx -name "*.conf" -exec sed -i 's/listen 80/listen 8080/' {} +

# 删除所有空行和注释
sed -i '/^#/d; /^$/d' /etc/nginx/nginx.conf
```
"""


def _practice_permissions():
    return """### 练习 1：Web 服务权限配置

**场景**：部署新 Web 应用，配置严格的权限模型。

```bash
# 创建应用专用用户和组
groupadd webapp
useradd -r -g webapp -s /sbin/nologin -d /var/www/webapp webapp

# 设置目录权限（最小权限原则）
mkdir -p /var/www/webapp/{public,private,logs,tmp}
chown -R webapp:webapp /var/www/webapp
chmod 750 /var/www/webapp
chmod 640 /var/www/webapp/.env
chmod 600 /var/www/webapp/.env  # 敏感配置

# 上传目录（SGID 继承用户组）
chmod 2775 /var/www/webapp/public/uploads
```

### 练习 2：权限安全审计

```bash
#!/bin/bash
echo "777 权限文件（安全隐患）:"
find /var/www -type f -perm 777 -ls 2>/dev/null

echo "SUID 文件:"
find / -type f -perm /4000 -ls 2>/dev/null

echo "SSH 密钥权限:"
for f in /home/*/.ssh/id_rsa; do
    [ -f "$f" ] && {
        perm=$(stat -c %a "$f")
        [ "$perm" != "600" ] && echo "  $f: $perm (应为 600)"
    }
done
```
"""


def _practice_user_mgmt():
    return """### 练习 1：企业用户生命周期管理

```bash
#!/bin/bash
# 入职：创建用户
create_user() {
    local username=$1 department=$2
    useradd -m -s /bin/bash -c "$department" "$username"
    case "$department" in
        dev) usermod -aG developers,docker "$username" ;;
        ops) usermod -aG operators,docker,sudo "$username" ;;
    esac
    chage -M 90 -m 7 -W 14 "$username"
}

# 离职：安全清理
offboard_user() {
    local username=$1
    pkill -u "$username" 2>/dev/null || true
    usermod -L "$username"
    tar -czf "/backup/users/${username}_$(date +%Y%m%d).tar.gz" /home/$username
    userdel -r "$username"
}
```

### 练习 2：sudo 权限审计

```bash
grep -E '^%?sudo' /etc/sudoers
visudo -c
grep -r "NOPASSWD" /etc/sudoers /etc/sudoers.d/
grep "sudo:" /var/log/auth.log | tail -20
```
"""


def _practice_review(day):
    if day == 14:
        return """### 综合实战：从零部署生产 LAMP 环境

**任务**：2 小时内从 0 到可交付的完整配置。

#### 1. 系统初始化

```bash
apt update && apt upgrade -y
apt install -y apache2 mysql-server php libapache2-mod-php php-mysql
ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
```

#### 2. 数据库安全

```bash
mysql -e "CREATE DATABASE production CHARACTER SET utf8mb4;"
mysql -e "CREATE USER 'app'@'localhost' IDENTIFIED BY 'StrongPass123!';"
mysql -e "GRANT SELECT,INSERT,UPDATE,DELETE ON production.* TO 'app'@'localhost';"
```

#### 3. 配置日志轮转

```bash
cat > /etc/logrotate.d/myapp << 'EOF'
/var/log/apache2/*.log {
    daily
    rotate 30
    compress
    missingok
    postrotate
        systemctl reload apache2 > /dev/null 2>&1 || true
    endscript
}
EOF
```

#### 4. 健康检查脚本

```bash
cat > /usr/local/bin/health_check.sh << 'SCRIPT'
#!/bin/bash
for svc in apache2 mysql; do
    if ! systemctl is-active --quiet "$svc"; then
        echo "CRIT: $svc down" | mail -s "Alert" admin@example.com
        systemctl restart "$svc"
    fi
done
SCRIPT
chmod +x /usr/local/bin/health_check.sh
echo "*/5 * * * * /usr/local/bin/health_check.sh" | crontab -
```
"""
    else:
        return """### 综合实战：从零部署生产服务器

#### 1. 系统初始化（30 分钟）

```bash
apt update && apt upgrade -y
apt install -y curl wget vim git htop tree net-tools dnsutils sysstat
timedatectl set-timezone Asia/Shanghai
ufw default deny incoming && ufw allow 22/tcp && ufw enable
```

#### 2. 安全加固（30 分钟）

```bash
# SSH 加固 + Fail2ban
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
apt install -y fail2ban
# 内核安全参数
echo "net.ipv4.tcp_syncookies = 1" >> /etc/sysctl.conf
sysctl -p
```

#### 3. 监控部署（30 分钟）

```bash
# 启用 sysstat
sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat

# 创建健康检查
cat > /usr/local/bin/health_check.sh << 'SCRIPT'
#!/bin/bash
services="nginx ssh"
for svc in $services; do
    systemctl is-active --quiet $svc || \\
        echo "CRIT: $svc down"
done
SCRIPT
chmod +x /usr/local/bin/health_check.sh
echo "*/5 * * * * /usr/local/bin/health_check.sh" | crontab -
```
"""


def _practice_process():
    return """### 练习 1：生产环境进程排查

**场景**：服务器响应缓慢，5 分钟内定位问题。

```bash
#!/bin/bash
echo "===== 进程排查报告 $(date) ====="
echo "负载: $(uptime)"
echo ""
echo "Top 10 CPU:"
ps aux --sort=-%cpu | head -11
echo ""
echo "僵尸进程:"
zombies=$(ps aux | awk '$8 ~ /Z/' | wc -l)
echo "数量: $zombies"
[ "$zombies" -gt 0 ] && ps aux | awk '$8 ~ /Z/'
echo ""
echo "进程状态分布:"
ps aux | awk '{print $8}' | sort | uniq -c | sort -rn
```

### 练习 2：进程树分析

```bash
pstree -p -a
ps -o pid,ppid,cmd -f --forest | grep -A5 nginx
cat /proc/$(pgrep nginx | head -1)/status
```
"""


def _practice_process_control():
    return """### 练习 1：优雅的服务重启

```bash
#!/bin/bash
SERVICE="nginx"

# 先测试配置
nginx -t || { echo "配置测试失败"; exit 1; }

# 优雅重启（对比 kill -9）
systemctl reload $SERVICE  # 连接不中断
kill -HUP $(cat /var/run/$SERVICE.pid)  # 发送 SIGHUP
```

### 练习 2：进程信号实战

```bash
# SIGTERM vs SIGKILL
sleep 1000 &
PID=$!
kill -15 $PID  # 优雅终止
sleep 1
kill -0 $PID 2>/dev/null && kill -9 $PID  # 强制终止

# SIGSTOP 和 SIGCONT
sleep 1000 &
PID=$!
kill -STOP $PID
ps -p $PID -o pid,stat
kill -CONT $PID
kill $PID
```
"""


def _practice_systemd():
    return """### 练习 1：编写企业级 systemd 服务

```bash
#!/bin/bash
# 创建应用
mkdir -p /opt/myapp/{logs,config}
useradd -r -s /sbin/nologin myapp

# 创建服务单元
cat > /etc/systemd/system/myapp.service << 'EOF'
[Unit]
Description=My Application Server
After=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/python3 /opt/myapp/app.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
StartLimitInterval=300
StartLimitBurst=5

# 安全加固
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now myapp
systemctl status myapp
```

### 练习 2：启动性能分析

```bash
systemd-analyze
systemd-analyze blame | head -20
systemd-analyze critical-chain
systemd-analyze plot > /tmp/startup.svg
```
"""


def _practice_monitoring():
    return """### 练习 1：运维实时监控脚本

```bash
#!/bin/bash
# ops_dashboard.sh
while true; do
    clear
    echo "=== SRE OPS DASHBOARD $(date '+%H:%M:%S') ==="
    load=$(cat /proc/loadavg | awk '{print $1", "$2", "$3}')
    cpu_idle=$(vmstat 1 2 | tail -1 | awk '{print $15}')
    echo "CPU Load: $load | Idle: ${cpu_idle}%"
    echo "Memory: $(free -h | grep Mem)"
    echo "Disk:"
    df -h / /data 2>/dev/null | tail -n+2 | \\
        awk '{printf "  %-15s %s/%s (%s)\\n", $6, $3, $2, $5}'
    echo "Top Processes:"
    ps aux --sort=-%cpu | head -4 | tail -3 | \\
        awk '{printf "  PID:%-8s CPU:%5s%% MEM:%5s%% %s\\n", $2, $3, $4, $11}'
    echo "Services:"
    for svc in nginx mysql docker ssh; do
        status=$(systemctl is-active $svc 2>/dev/null)
        [ "$status" = "active" ] && echo "  [OK] $svc" || echo "  [!!] $svc"
    done
    sleep 5
done
```

### 练习 2：历史数据回溯

```bash
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat
systemctl restart sysstat
sar -u          # CPU 历史
sar -r          # 内存历史
sar -d -p       # 磁盘 IO
sar -u -s 14:00 -e 15:00  # 特定时间段
```
"""


def _practice_disk():
    return """### 练习 1：LVM 磁盘管理

```bash
# 创建 LVM
sudo pvcreate /dev/sdb
sudo vgcreate vg_data /dev/sdb
sudo lvcreate -L 100G -n lv_app vg_data
sudo mkfs.ext4 /dev/vg_data/lv_app
sudo mount /dev/vg_data/lv_app /data

# 在线扩容
sudo lvextend -L +50G /dev/vg_data/lv_app
sudo resize2fs /dev/vg_data/lv_app

# 验证
df -h /data
lvs
```

### 练习 2：磁盘健康检查

```bash
#!/bin/bash
echo "磁盘健康检查:"
# SMART 状态
for disk in /dev/sd?; do
    [ -b "$disk" ] && smartctl -H "$disk" 2>/dev/null | grep -i "overall"
done
# IO 性能
iostat -x 1 3
# 高使用率警告
df -h | awk 'NR>1 {gsub(/%/,"",$5); if($5>80) print "WARN: "$6" at "$5"%"}'
```
"""


def _practice_log_mgmt():
    return """### 练习 1：日志生命周期管理

```bash
#!/bin/bash
# 配置 Nginx 日志轮转
cat > /etc/logrotate.d/nginx-custom << 'EOF'
/var/log/nginx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}
EOF

# 配置 journal 限制
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/limits.conf << 'EOF'
[Journal]
SystemMaxUse=500M
MaxRetentionSec=30day
EOF
systemctl restart systemd-journald
```

### 练习 2：安全日志监控

```bash
#!/bin/bash
echo "暴力破解 (过去 1 小时):"
grep "Failed password" /var/log/auth.log | \\
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | \\
    awk '$1 > 5 {printf "  IP: %-15s 失败: %d\\n", $2, $1}'

echo "非工作时间登录:"
grep "Accepted" /var/log/auth.log | \\
    awk -F'[ :]' '{if ($4 >= 22 || $4 < 6) print "  "$0}'
```
"""


def _practice_shell_basics():
    return """### 练习 1：每日系统报告（自动邮件）

```bash
#!/bin/bash
# daily_report.sh
{
    echo "===== 系统报告 $(hostname) ====="
    echo "时间: $(date)"
    echo ""
    echo "CPU & 负载:"
    uptime
    echo ""
    echo "内存:"
    free -h
    echo ""
    echo "磁盘:"
    df -h | grep -v tmpfs
    echo ""
    echo "Top 5 CPU:"
    ps aux --sort=-%cpu | head -6
    echo ""
    echo "服务状态:"
    for svc in nginx mysql docker ssh; do
        status=$(systemctl is-active $svc 2>/dev/null)
        [ "$status" = "active" ] && echo "  [OK] $svc" || echo "  [!!] $svc"
    done
} > /tmp/report_$(date +%Y%m%d).txt
# mail -s "System Report $(hostname)" ops@example.com < /tmp/report.txt
```

### 练习 2：服务健康检查

```bash
#!/bin/bash
set -euo pipefail
for svc in nginx mysql docker; do
    if systemctl is-active --quiet "$svc"; then
        echo "OK: $svc running"
    else
        echo "CRIT: $svc stopped - restarting..."
        systemctl restart "$svc" || echo "FAIL: restart failed"
    fi
done
```
"""


def _practice_shell_condition():
    return """### 练习 1：智能健康检查（带阈值告警）

```bash
#!/bin/bash
set -euo pipefail
CPU_WARN=70; CPU_CRIT=90
MEM_WARN=80; MEM_CRIT=95

cpu_idle=$(vmstat 1 2 | tail -1 | awk '{print $15}')
cpu_used=$((100 - cpu_idle))
if [ $cpu_used -gt $CPU_CRIT ]; then
    echo "CRIT: CPU ${cpu_used}% > ${CPU_CRIT}%"
elif [ $cpu_used -gt $CPU_WARN ]; then
    echo "WARN: CPU ${cpu_used}% > ${CPU_WARN}%"
else
    echo "OK: CPU ${cpu_used}%"
fi

mem_pct=$(free | awk 'NR==2 {printf "%d", $3/$2*100}')
if [ $mem_pct -gt $MEM_CRIT ]; then
    echo "CRIT: Memory ${mem_pct}% > ${MEM_CRIT}%"
elif [ $mem_pct -gt $MEM_WARN ]; then
    echo "WARN: Memory ${mem_pct}% > ${MEM_WARN}%"
else
    echo "OK: Memory ${mem_pct}%"
fi
```
"""


def _practice_shell_loop():
    return """### 练习 1：批量服务器巡检

```bash
#!/bin/bash
SERVERS=("web01" "web02" "db01" "cache01")
for server in "${SERVERS[@]}"; do
    echo "=== $server ==="
    result=$(ssh -o ConnectTimeout=5 "$server" "uptime; df -h / | tail -1" 2>&1)
    echo "$result"
    echo ""
done
```

### 练习 2：并行巡检

```bash
#!/bin/bash
TEMP_DIR=$(mktemp -d)
SERVERS=("web01" "web02" "web03" "db01" "db02")
for server in "${SERVERS[@]}"; do
    (ssh -o ConnectTimeout=5 "$server" "uptime; df -h /" > "$TEMP_DIR/$server" 2>&1) &
done
wait
for server in "${SERVERS[@]}"; do
    echo "=== $server ==="; cat "$TEMP_DIR/$server"; echo ""
done
rm -rf "$TEMP_DIR"
```
"""


def _practice_shell_function():
    return """### 练习 1：运维函数库

```bash
#!/bin/bash
# ops_lib.sh
log() {
    local level=$1; shift
    case $level in
        INFO)  echo -e "\\033[32m[$(date '+%H:%M:%S')] [INFO] $*\\033[0m" ;;
        WARN)  echo -e "\\033[33m[$(date '+%H:%M:%S')] [WARN] $*\\033[0m" ;;
        ERROR) echo -e "\\033[31m[$(date '+%H:%M:%S')] [ERROR] $*\\033[0m" ;;
    esac
}

retry() {
    local max=${1:-3}; local delay=${2:-5}; shift 2
    for i in $(seq 1 $max); do
        log INFO "尝试 $i/$max: $*"
        eval "$@" && return 0
        sleep $delay
    done
    log ERROR "失败（重试 $max 次）: $*"
    return 1
}

# 使用
# source ./ops_lib.sh
# retry 3 5 "curl -f http://localhost/health"
```
"""


def _practice_final_review():
    return """### 综合能力评估

#### 实操测试 1：从零部署 Web 服务（限时 15 分钟）

```bash
# 要求：
# 1. 创建用户并配置 SSH
# 2. 安装并配置 Nginx
# 3. 设置防火墙
# 4. 配置日志轮转
# 5. 编写健康检查脚本
```

#### 实操测试 2：日志分析

```bash
# 1. 分析 Nginx 日志：Top 10 IP、5xx 错误率、平均响应时间
# 2. 检查 auth.log：暴力破解检测
# 3. 系统磁盘：找出占用最大的 5 个目录
```

#### 实操测试 3：故障排查

```bash
# 模拟场景：
# 1. 服务无法启动 → 排查端口占用、配置错误
# 2. 磁盘 100% → 定位并清理
# 3. 进程异常 → 定位高 CPU/内存进程
```

#### 达标标准
- [ ] 能不查阅文档完成 80% 常用命令
- [ ] 能独立排查常见 Linux 问题
- [ ] 能编写基本的运维 Shell 脚本
- [ ] 理解系统架构和各组件关系
"""


def _practice_networking(day):
    return """### 练习 1：网络故障排查脚本

**场景**：用户报告"网站访问慢"，系统化排查。

```bash
#!/bin/bash
TARGET="example.com"
echo "=== 网络排查: $TARGET ==="

# 1. DNS
echo "DNS: $(dig +short $TARGET A 2>/dev/null || echo 'FAILED')"

# 2. 连通性
ping -c 3 -W 2 $TARGET 2>&1 | tail -1

# 3. 路由
traceroute -m 15 -w 2 $TARGET 2>/dev/null | head -10

# 4. 端口
for port in 80 443; do
    timeout 2 bash -c "echo > /dev/tcp/$TARGET/$port" 2>/dev/null && \\
        echo "端口 $port: OK" || echo "端口 $port: FAIL"
done

# 5. HTTP
curl -s -o /dev/null -w "HTTP: %{{http_code}}, Time: %{{time_total}}s\\n" "http://$TARGET"

# 6. TCP 状态
ss -tan | awk 'NR>1 {{print $1}}' | sort | uniq -c | sort -rn
```

### 练习 2：抓包分析

```bash
# 抓取 HTTP 流量
sudo tcpdump -i any -n port 80 -A 2>/dev/null | head -50

# 保存到文件用 Wireshark 分析
sudo tcpdump -i any -n port 443 -w /tmp/capture.pcap

# 分析 TCP 握手
sudo tcpdump -i any -n 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0' -c 10
```
"""


def _practice_python(day):
    return """### 练习 1：主机监控脚本

```python
#!/usr/bin/env python3
import psutil, json, datetime

def check_system():
    report = {{
        "timestamp": datetime.datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {{
            "total_gb": round(psutil.virtual_memory().total / 1e9, 2),
            "used_percent": psutil.virtual_memory().percent
        }},
        "disk": {{}},
    }}
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            report["disk"][part.mountpoint] = {{
                "total_gb": round(usage.total / 1e9, 2),
                "used_percent": usage.percent
            }}
        except PermissionError:
            pass
    return report

data = check_system()
print(json.dumps(data, indent=2))

# 告警
if data["cpu_percent"] > 80:
    print("ALERT: High CPU usage!")
if data["memory"]["used_percent"] > 90:
    print("ALERT: High memory usage!")
```

### 练习 2：日志分析工具

```python
import re
from collections import Counter

def analyze_nginx_log(log_file):
    pattern = r'(\\S+) \\S+ \\S+ \\[(.+?)\\] "(\\S+)" (\\d+)'
    ips = Counter()
    status_codes = Counter()
    with open(log_file) as f:
        for line in f:
            m = re.match(pattern, line)
            if m:
                ips[m.group(1)] += 1
                status_codes[m.group(4)] += 1
    print("Top 10 IPs:", ips.most_common(10))
    print("Status codes:", dict(status_codes))

analyze_nginx_log("/var/log/nginx/access.log")
```
"""


def _practice_go(day):
    return """### 练习 1：HTTP 健康检查服务

```go
package main

import (
    "encoding/json"
    "net/http"
    "runtime"
    "time"
)

type HealthResponse struct {
    Status     string `json:"status"`
    Uptime     string `json:"uptime"`
    GoVersion  string `json:"go_version"`
    Goroutines int    `json:"goroutines"`
}

var startTime = time.Now()

func healthHandler(w http.ResponseWriter, r *http.Request) {
    resp := HealthResponse{
        Status:     "ok",
        Uptime:     time.Since(startTime).String(),
        GoVersion:  runtime.Version(),
        Goroutines: runtime.NumGoroutine(),
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func main() {
    http.HandleFunc("/health", healthHandler)
    http.ListenAndServe(":8080", nil)
}
```

```bash
go run main.go
curl http://localhost:8080/health
```
"""


def _practice_docker(day):
    return """### 练习 1：多阶段构建优化

```dockerfile
# Build stage
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o myapp

# Runtime stage
FROM alpine:3.18
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/myapp /usr/local/bin/myapp
USER 1000:1000
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s \\
    CMD wget -qO- http://localhost:8080/health || exit 1
CMD ["myapp"]
```

### 练习 2：docker-compose 编排

```yaml
version: "3.8"
services:
  web:
    build: .
    ports: ["8080:8080"]
    depends_on: [db, redis]
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379
  db:
    image: postgres:15-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
volumes:
  pgdata:
```
"""


def _practice_k8s(day):
    return """### 练习 1：部署完整应用

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: myapp:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
```

```bash
kubectl apply -f deployment.yaml
kubectl get pods -w
kubectl rollout status deployment/web-app
kubectl rollout undo deployment/web-app  # 回滚
```
"""


def _practice_aws(day):
    return """### 练习 1：AWS CLI 自动化

```bash
# 查询实例状态
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]' --output table

# 创建 S3 桶并设置生命周期
aws s3api create-bucket --bucket my-backup-bucket --region us-east-1
aws s3api put-bucket-lifecycle-configuration --bucket my-backup-bucket \\
    --lifecycle-configuration '{
        "Rules": [{{
            "ID": "TransitionToGlacier",
            "Status": "Enabled",
            "Prefix": "",
            "Transitions": [{{"Days": 90, "StorageClass": "GLACIER"}}]
        }}]
    }'
```

### 练习 2：高可用架构设计

- 设计多 AZ 部署：ALB + ASG（跨 2 个 AZ）+ RDS Multi-AZ
- 配置 CloudWatch 告警
- 设置自动备份策略
"""


def _practice_terraform(day):
    return """### 练习 1：Terraform 基础设施

```hcl
provider "aws" {{
  region = "us-east-1"
}}

resource "aws_instance" "web" {{
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  vpc_security_group_ids = [aws_security_group.web.id]

  tags = {{
    Name        = "web-server"
    Environment = "production"
  }}
}}

resource "aws_security_group" "web" {{
  ingress {{
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}
}}

output "public_ip" {{
  value = aws_instance.web.public_ip
}}
```

```bash
terraform init
terraform plan
terraform apply
terraform destroy  # 清理
```
"""


def _practice_ansible(day):
    return """### 练习 1：Ansible 自动化部署

```yaml
# deploy.yml
- hosts: webservers
  become: true
  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present

    - name: Configure nginx
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      notify: Restart nginx

    - name: Enable nginx
      service:
        name: nginx
        state: started
        enabled: true

  handlers:
    - name: Restart nginx
      service:
        name: nginx
        state: restarted
```

```bash
ansible-playbook -i hosts deploy.yml
```
"""


def _practice_observability(day):
    return """### 练习 1：Prometheus + Grafana 部署

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
  - job_name: 'app'
    static_configs:
      - targets: ['localhost:8080']
```

```promql
# PromQL 查询
# CPU 使用率
100 - (avg(rate(node_cpu_seconds_total{{mode="idle"}}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 磁盘使用率
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100

# QPS
rate(http_requests_total[5m])

# P99 延迟
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```
"""


def _practice_logging_tracing(day):
    return """### 练习 1：ELK 日志平台

```bash
# Filebeat 配置
cat > /etc/filebeat/filebeat.yml << 'EOF'
filebeat.inputs:
  - type: log
    paths:
      - /var/log/nginx/*.log
    fields:
      service: nginx
output.elasticsearch:
  hosts: ["localhost:9200"]
EOF

# 查询示例（Kibana/ES）
curl -X GET "localhost:9200/filebeat-*/_search" -H 'Content-Type: application/json' -d'
{{
  "query": {{ "match": {{ "http.response.status_code": 500 }} }},
  "size": 10
}}'
```

### 练习 2：Loki 日志

```bash
# LogQL 查询
# 错误日志
{{app="nginx"}} |= "error"

# 按状态码统计
sum by (status) (count_over_time({app="nginx"} |= "" [5m]))
```
"""


def _practice_cicd(day):
    return """### 练习 1：GitHub Actions CI/CD

```yaml
name: CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest --cov=.

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:${{ github.sha }} .
      - run: docker push myapp:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
      - run: kubectl set image deployment/web-app app=myapp:${{ github.sha }}
```
"""


def _practice_devops_advanced(day):
    return """### 练习 1：ArgoCD GitOps

```yaml
# ArgoCD Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: web-app
spec:
  project: default
  source:
    repoURL: https://github.com/org/k8s-manifests.git
    targetRevision: main
    path: manifests/web-app
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 练习 2：金丝雀发布

```bash
# Argo Rollouts
kubectl argo rollouts set image web-app \\
    app=myapp:v2.0.0
kubectl argo rollouts promote web-app
kubectl argo rollouts abort web-app  # 发现问题立即中止
```
"""


def _practice_sre_core(day):
    return """### 练习 1：定义 SLO 和错误预算

**场景**：为一个 API 服务定义 SLO。

```
服务：REST API
SLO：
  - 可用性：99.95%（每月最多 21.6 分钟不可用）
  - 延迟：P99 < 500ms
  - 错误率：5xx < 0.1%

错误预算：
  - 月度预算：21.6 分钟
  - 已消耗 80% → 暂停新功能发布，专注稳定性
  - 剩余 4.3 分钟
```

### 练习 2：编写 RCA 报告

```markdown
# 事故报告：数据库连接池耗尽

## 时间线
- 14:00 - 监控告警：API 响应时间 > 10s
- 14:05 - 确认：DB 连接池 100% 使用
- 14:10 - 临时修复：重启应用服务
- 14:15 - 恢复正常

## 根因分析（5 Why）
1. 为什么 API 慢？→ DB 连接池耗尽
2. 为什么连接池耗尽？→ 慢查询阻塞连接
3. 为什么有慢查询？→ 新增的索引未优化
4. 为什么没发现？→ 测试环境数据量不足
5. 为什么测试数据少？→ 没有数据脱敏导入流程

## 改进措施
- [ ] 添加慢查询告警（负责人：XXX，截止日期：XX）
- [ ] 建立测试数据同步流程
- [ ] 代码审查增加 SQL 审查项
```
"""


def _practice_interview(day):
    return """### 模拟面试

#### Linux 面试

1. 解释 Linux 启动流程（BIOS → Bootloader → Kernel → systemd）
2. 进程状态 R/S/D/Z 各代表什么？Z 状态如何处理？
3. Load Average 的含义？4 核机器 load=8 说明什么？
4. 如何排查磁盘 IO 高的问题？
5. 文件描述符是什么？如何调整 ulimit？

#### 网络面试

1. 输入 URL 到页面显示的完整过程
2. TCP 三次握手为什么是三次？两次可以吗？
3. TIME_WAIT 状态的作用？过多怎么办？
4. HTTP 200/301/302/403/404/500/502/503 的含义
5. DNS 解析的完整过程

#### K8s 面试

1. Pod 的生命周期和探针的区别
2. Service 四种类型及使用场景
3. 如何排查 Pod 一直 Restart 的问题？
4. Deployment 滚动更新的过程
5. PV/PVC/StorageClass 的关系
"""


def _practice_generic(topic):
    return f"""### 练习 1：{topic} 实战

**场景**：将 {topic} 应用到生产环境中。

```bash
# 1. 基础操作 - 查阅官方文档完成
# 2. 进阶操作 - 结合实际场景
# 3. 故障排查 - 模拟常见问题
```

### 练习 2：自动化脚本

```bash
#!/bin/bash
set -euo pipefail
# TODO: 根据主题实现具体的自动化逻辑
echo "自动化任务完成"
```

### 练习 3：监控配置

```bash
# 为 {topic} 配置监控指标
# 设置告警阈值
# 编写健康检查脚本
```
"""



if __name__ == "__main__":
    exit(main())
