# Day 01: Linux 简介与虚拟机安装

> 📅 日期：2026-04-14  
> 📖 学习主题：Linux 简介与虚拟机安装  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 01 的学习后，你应该掌握：
- 理解 Linux 简介与虚拟机安装 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. Linux 简介

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
sudo apt install -y \
    curl wget vim git htop tree \
    net-tools dnsutils unzip zip \
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

*由 SRE 学习计划自动生成 | 2026-04-14 10:24:10*  
*Generated by Hermes Agent with review*
