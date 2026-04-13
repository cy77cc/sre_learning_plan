# Day 01: Linux 简介与虚拟机安装

> 📅 日期：2026-04-13  
> 📖 学习主题：Linux 简介与虚拟机安装 - Ubuntu 22.04 LTS 安装与基础配置  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 01 的学习后，你应该掌握：

- [ ] 理解 Linux 的历史、哲学和发行版体系
- [ ] 掌握 VirtualBox/WMWare/WSL2 的安装方法
- [ ] 能够独立完成 Ubuntu 22.04 LTS 的安装
- [ ] 熟悉 Ubuntu 桌面环境的基本操作
- [ ] 学会更新系统并安装基础软件

---

## 📖 第一部分：Linux 简介

### 1.1 什么是 Linux？

Linux 是一个**开源的 Unix-like 操作系统内核**，由 Linus Torvalds 于 1991 年首次发布。如今，Linux 已经成为：

| 领域 | 市场占有率 |
|------|-----------|
| 服务器 | **~96%** 的 Web 服务器 |
| 超级计算机 | **100%** 的 TOP500 超级计算机 |
| 云计算 | AWS、Azure、GCP 等主流云平台 |
| 移动设备 | Android 系统基于 Linux |
| 嵌入式 | 路由器、智能设备等 |

### 1.2 Linux 的历史

```
1991年 - Linus Torvalds 在芬兰赫尔辛基大学开始开发 Linux
1992年 - Linux 采用 GPL 许可证开源
1994年 - Linux 1.0.0 正式发布
2003年 - 进入企业级市场（Red Hat Enterprise Linux）
2007年 - 成立 Linux 基金会
今天   - 已成为全球最重要的开源项目
```

### 1.3 Linux 核心哲学

Linux 遵循 **Unix 哲学**，核心原则包括：

1. **小而专一**：每个程序只做一件事，但做到最好
2. **组合出奇迹**：程序之间通过管道协作
3. **一切皆文件**：设备、进程、配置都通过文件系统呈现
4. **开源共享**：代码自由分发，全世界共同维护

### 1.4 常见 Linux 发行版

#### 发行版家族

| 类型 | 代表发行版 | 特点 | 适用场景 |
|------|-----------|------|---------|
| **Debian 系** | Ubuntu, Linux Mint, Pop!_OS | 稳定、友好 | 桌面、服务器 |
| **Red Hat 系** | RHEL, CentOS Stream, Rocky Linux | 企业级、稳定性 | 生产服务器 |
| **SUSE 系** | openSUSE, SLES | 企业级支持 | 关键业务 |
| **Arch 系** | Arch Linux, Manjaro | 滚动更新、定制化 | 高级用户 |
| **容器化** | Alpine, Flatcar | 轻量级 | 容器、K8s |

#### 主流选择推荐

| 使用场景 | 推荐发行版 | 理由 |
|---------|-----------|------|
| **SRE/运维入门** | Ubuntu Server 22.04 LTS | 文档丰富、社区活跃 |
| **生产服务器** | Ubuntu Server 22.04 LTS / Rocky Linux 9 | 稳定、长期支持 |
| **桌面开发** | Ubuntu Desktop 22.04 LTS | 界面友好、软件丰富 |
| **追求新特性** | Fedora | 最新内核和技术 |
| **极简主义** | Arch Linux | 完全定制 |

---

## 📖 第二部分：虚拟机软件选择

### 2.1 常见虚拟机软件对比

| 软件 | 优点 | 缺点 | 平台 | 推荐度 |
|------|------|------|------|--------|
| **VirtualBox** | 免费开源、跨平台、功能完善 | 性能一般、界面较老 | 全平台 | ⭐⭐⭐⭐ |
| **VMware Workstation Pro** | 性能优秀、功能强大 | 付费、Linux 下免费版功能弱 | Win/Linux | ⭐⭐⭐⭐ |
| **VMware Fusion** | macOS 下最佳选择 | 仅限 macOS、付费 | macOS | ⭐⭐⭐⭐ |
| **Hyper-V** | Windows 内置、性能好 | 仅限 Windows、功能分散 | Windows | ⭐⭐⭐ |
| **WSL2** | 与 Windows 无缝集成、占用资源少 | 不能运行桌面版 Linux、部分功能受限 | Windows 11 | ⭐⭐⭐⭐⭐ |

### 2.2 推荐：Windows 用户使用 WSL2

如果你使用 **Windows 11**，强烈推荐安装 WSL2：

```powershell
# 以管理员身份打开 PowerShell，运行以下命令：

# 1. 启用 WSL 功能
wsl --install

# 2. 安装后重启计算机，然后设置 Ubuntu
wsl --set-default-version 2
wsl --install -d Ubuntu-22.04

# 3. 首次启动设置用户名和密码
```

**WSL2 优势：**
- ✅ 原生集成，体验接近真实 Linux
- ✅ 与 Windows 文件系统无缝互操作
- ✅ 资源占用低，启动快
- ✅ 支持 Docker Desktop 集成
- ✅ 完美满足 SRE 学习需求

### 2.3 macOS 用户推荐

| 选择 | 建议 |
|------|------|
| **VirtualBox** | 免费足够学习使用 |
| **VMware Fusion** | 付费但性能更好 |
| **Colima + Docker** | 如果只需要命令行环境 |

### 2.4 纯虚拟机安装（推荐 VirtualBox）

#### VirtualBox 下载地址

| 组件 | 下载地址 |
|------|---------|
| VirtualBox 7.x | https://www.virtualbox.org/wiki/Downloads |
| VirtualBox Extension Pack | 同上页面（增强功能需要） |

---

## 📖 第三部分：Ubuntu 22.04 LTS 安装详解

### 3.1 Ubuntu 22.04 LTS 介绍

**Ubuntu 22.04 LTS (Jammy Jellyfish)** 是目前最推荐的 Linux 桌面/服务器版本：

| 特性 | 说明 |
|------|------|
| **发布于** | 2022 年 4 月 21 日 |
| **内核** | Linux 5.15 (可升级到 6.x) |
| **桌面环境** | GNOME 42 |
| **支持期限** | 10 年（到 2032 年） |
| **Python 默认** | Python 3.10 |
| **容器支持** | Docker、K8s 支持完善 |

### 3.2 系统要求

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 1 GHz 双核 | 2 GHz 四核 |
| 内存 | 4 GB | 8 GB 或更多 |
| 磁盘 | 25 GB | 50 GB 或更多 |
| 显卡 | 支持 VESA | 支持 3D 加速 |
| 网络 | 可选 | 建议有网卡 |

> ⚠️ **SRE 学习建议**：配置 **2 CPU + 4GB 内存 + 50GB 磁盘** 以上

### 3.3 安装步骤

#### 第一步：下载 Ubuntu 镜像

下载地址（推荐最新 LTS）：

| 版本 | 下载链接 | 文件大小 |
|------|---------|---------|
| **Ubuntu 22.04.4 LTS** | [点击下载](https://ubuntu.com/download/desktop/thank-you?version=22.04.4&architecture=amd64) | ~4.8 GB |
| Ubuntu 24.04 LTS | [点击下载](https://ubuntu.com/download/desktop/thank-you?version=24.04.4&architecture=amd64) | ~5.9 GB |

#### 第二步：创建虚拟机（VirtualBox）

1. 打开 VirtualBox → 点击 **"新建"**
2. 填写虚拟机信息：
   ```
   名称：Ubuntu 22.04 SRE
   类型：Linux
   版本：Ubuntu (64-bit)
   ```
3. 分配内存：至少 **4096 MB**，推荐 **8192 MB**
4. 创建虚拟硬盘：VDI 格式，**动态分配**，容量 **50 GB**
5. 点击创建

#### 第三步：配置虚拟机

1. 选中创建的虚拟机 → **设置**
2. **系统 → 主板**：
   - 启动顺序：仅勾选"光驱"、"硬盘"
   - 芯片组：ICH9
   - 启用 EFI（可选）
3. **系统 → 处理器**：
   - CPU 数量：至少 2
   - 启用 PAE/NX
4. **存储 → 控制器：SATA**：
   - 点击光驱图标 → 选择下载的 Ubuntu ISO 文件
5. **网络 → 桥接模式**（或 NAT）：
   - 桥接模式：虚拟机与宿主机在同一网络
   - NAT：虚拟机可上网但与宿主机隔离

#### 第四步：启动并安装 Ubuntu

1. 启动虚拟机，进入 Ubuntu 启动菜单
2. 选择 **"Install Ubuntu"**
3. 语言选择：**English**（推荐）或简体中文
4. 键盘布局：根据你的键盘选择
5. 安装类型：
   - 选择 **"Erase disk and install Ubuntu"**（仅学习用）
   - 或选择 **"Something else"** 自定义分区
6. 时区选择：上海（Asia/Shanghai）
7. 创建用户：
   ```
   Your name: sre-user
   Your computer's name: sre-server
   Pick a username: sreuser
   ```
8. 等待安装完成（约 10-15 分钟）
9. 安装完成后**重启**，登录系统

### 3.4 Ubuntu 桌面环境介绍

![Ubuntu 22.04 Desktop](https://assets.ubuntu.com/v1/f88058c1-desktop-22-04-lts-default-desktop.png)

#### 桌面布局

| 元素 | 说明 |
|------|------|
| **Activities** | 左上角，点击或按 Super 键打开 |
| **Top Bar** | 顶部栏，显示时间、网络、电源等 |
| **Desktop** | 桌面区域 |
| **Dock** | 左侧启动器栏 |

#### 常用快捷键

| 快捷键 | 功能 |
|--------|------|
| `Super` (Windows 键) | 打开 Activities 概览 |
| `Super + A` | 打开应用程序菜单 |
| `Super + Tab` | 切换应用 |
| `Super + L` | 锁屏 |
| `Ctrl + Alt + T` | 打开终端 |
| `Alt + F4` | 关闭窗口 |
| `Super + D` | 显示桌面 |

---

## 📖 第四部分：安装后的基础配置

### 4.1 系统更新

打开终端（`Ctrl + Alt + T`），执行：

```bash
# 更新软件包列表
sudo apt update

# 升级所有可升级的软件包
sudo apt upgrade -y

# 完整升级（包含内核升级）
sudo apt full-upgrade -y

# 自动清理不再需要的包
sudo apt autoremove -y
```

### 4.2 安装基础软件

```bash
# 安装常用工具
sudo apt install -y \
    curl \
    wget \
    vim \
    git \
    htop \
    tree \
    net-tools \
    dnsutils \
    unzip \
    zip \
    tar \
    gzip

# 安装 Build Essential（编译工具）
sudo apt install -y build-essential
```

### 4.3 安装输入法（中文用户）

```bash
# 安装 fcitx5 中文输入法
sudo apt install -y fcitx5 fcitx5-chinese-addons fcitx5-configtool

# 配置环境变量
echo "export GTK_IM_MODULE=fcitx" >> ~/.profile
echo "export QT_IM_MODULE=fcitx" >> ~/.profile
echo "export XMODIFIERS=@im=fcitx" >> ~/.profile

# 重启后通过右上角输入法设置添加中文拼音
```

### 4.4 配置 Vim（编辑器）

```bash
# 创建用户级 Vim 配置
cat > ~/.vimrc << 'EOF'
" 基本设置
set number          " 显示行号
set relativenumber  " 相对行号
set tabstop=4       " Tab 宽度
set shiftwidth=4    " 缩进宽度
set expandtab       " 用空格代替 Tab
set smartindent     " 智能缩进
set encoding=utf-8  " UTF-8 编码
set showcmd         " 显示命令
set cursorline      " 高亮当前行
set wildmenu        " 命令补全

" 配色方案
syntax on
set background=dark

" 搜索设置
set incsearch       " 增量搜索
set hlsearch        " 高亮搜索结果
hi Search ctermbg=3

" 底部状态栏
set laststatus=2
set statusline=%f\ %m\ %=%(%l:%c%)
EOF

source ~/.vimrc
```

### 4.5 配置 Git

```bash
# 设置全局用户名和邮箱
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 设置默认分支为 main
git config --global init.defaultBranch main

# 设置代理（如果需要）
git config --global https.proxy http://127.0.0.1:7890
git config --global http.proxy http://127.0.0.1:7890

# 查看配置
git config --list
```

### 4.6 安装 VS Code（推荐编辑器）

```bash
# 方式一：通过 Snap 安装
sudo snap install --classic code

# 方式二：通过 apt 安装（Ubuntu Software 商店）
# 搜索 "Visual Studio Code" 并安装

# 方式三：手动安装 .deb 包
wget -O code.deb https://code.visualstudio.com/sha/download?build=stable&os=linux-debian-x64
sudo dpkg -i code.deb
sudo apt --fix-broken install -y
```

---

## 📖 第五部分：VirtualBox 增强功能（可选）

如果使用 VirtualBox，安装增强功能可以获得更好的体验：

### 5.1 增强功能包含

- ✅ 共享剪贴板（宿主机与虚拟机之间复制粘贴）
- ✅ 共享文件夹
- ✅ 更好的图形性能（1920x1080+ 分辨率）
- ✅ 无缝窗口模式

### 5.2 安装步骤

1. 在虚拟机菜单中选择 **设备 → 插入增强功能光盘镜像**
2. 自动弹出安装向导，或手动运行：
   ```bash
   cd /media/sreuser/VBox_GAs_*
   sudo ./VBoxLinuxAdditions.run
   ```
3. 安装完成后**重启虚拟机**

### 5.3 配置共享文件夹

```bash
# VirtualBox 中：设备 → 共享文件夹 → 共享文件夹设置
# 添加一个宿主机文件夹，勾选"自动挂载"

# 在虚拟机中，共享文件夹通常挂载在 /media/sf_xxx
# 或者通过以下方式访问：
sudo usermod -aG vboxsf $USER
# 重新登录后生效
```

---

## 📖 第六部分：Docker 安装（可选但推荐）

作为 SRE 学习者，尽早熟悉 Docker 非常重要：

### 6.1 Ubuntu 22.04 安装 Docker

```bash
# 1. 卸载旧版本（如有）
sudo apt remove docker docker-engine docker.io containerd runc

# 2. 安装依赖
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# 3. 添加 Docker GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 4. 添加 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 5. 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 6. 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER

# 7. 验证安装
docker --version
docker compose version
```

### 6.2 测试 Docker

```bash
# 注销并重新登录后，执行：
docker run hello-world

# 如果看到 "Hello from Docker!" 表示安装成功
```

---

## 💻 实战练习

### 练习 1：完成 Ubuntu 安装

- [ ] 下载 Ubuntu 22.04.4 LTS 镜像
- [ ] 使用 VirtualBox/WSL2 创建虚拟机
- [ ] 完成系统安装
- [ ] 创建普通用户（不要用 root 日常使用）

### 练习 2：系统基础配置

```bash
# 完成以下任务：

# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 安装基础工具（至少安装 5 个）
# sudo apt install -y ...

# 3. 配置 Git 用户信息
git config --global user.name "YourName"
git config --global user.email "your@email.com"

# 4. 创建一个 vim 配置文件
# 按照上面的示例创建 ~/.vimrc

# 5. 创建一个终端配置文件（可选）
cat > ~/.bash_aliases << 'EOF'
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
alias grep='grep --color=auto'
EOF

source ~/.bashrc
```

### 练习 3：探索 Linux 文件系统

```bash
# 使用 tree 或 ls 查看以下目录结构
tree / -L 2 2>/dev/null | head -100

# 重点了解这些目录：
# /bin    - Essential command binaries
# /sbin   - System binaries
# /etc    - Configuration files
# /home   - User home directories
# /root   - Root user home directory
# /var    - Variable data (logs, caches)
# /tmp    - Temporary files
# /usr    - User programs
# /proc   - Virtual filesystem (kernel info)
# /dev    - Device files
```

### 练习 4：了解系统信息

```bash
# 查看内核版本
uname -a

# 查看 Ubuntu 版本
cat /etc/os-release
lsb_release -a

# 查看 CPU 信息
cat /proc/cpuinfo | head -20

# 查看内存信息
free -h

# 查看磁盘使用情况
df -h

# 查看当前用户
whoami
id

# 查看系统运行时间
uptime
```

---

## 🔗 学习资源

### 官方文档

| 资源 | 链接 |
|------|------|
| Ubuntu 官方文档 | https://ubuntu.com/documentation |
| Ubuntu Desktop 教程 | https://documentation.ubuntu.com/desktop/ |
| Ubuntu Server 教程 | https://documentation.ubuntu.com/server/ |
| VirtualBox 文档 | https://www.virtualbox.org/wiki/Documentation |
| WSL2 官方文档 | https://docs.microsoft.com/windows/wsl/ |

### 推荐教程

| 资源 | 链接 | 说明 |
|------|------|------|
| **MIT The Missing Semester** | https://missing.csail.mit.edu/ | 强烈推荐！涵盖命令行、Git、 Vim 等 |
| Linux Journey | https://linuxjourney.com/ | 免费交互式学习 |
| Ryan's Tutorials | https://ryanstutorials.net/linuxtutorial/ | Linux 基础教程 |
| Ubuntu 22.04 安装教程 | https://www.youtube.com/watch?v=fEr18Ao4d4c | 视频教程 |

### 视频课程（B站）

| 课程 | 链接 |
|------|------|
| 鸟哥的Linux私房菜 - 基础学习篇 | https://www.bilibili.com/video/BV1mE411L7QM |
| Linux 入门学习指南 | https://www.bilibili.com/video/BV1St4y1S7pV |
| Ubuntu 22.04 桌面版入门 | https://www.bilibili.com/video/BV1JW4y1R7Fx |

### 练习平台

| 平台 | 链接 | 说明 |
|------|------|------|
| OverTheWire Bandit | https://overthewire.org/wargames/bandit/ | Linux 命令行游戏 |
| KodeKloud | https://kodekloud.com | K8s 和 DevOps 练习 |
| Learn Linux TV | https://youtube.com/@LearnLinuxTV | YouTube 频道 |

---

## ⚠️ 常见问题与解决方案

### Q1: 虚拟机运行缓慢？

**解决方案：**
```bash
# 1. 分配更多 CPU 和内存
# 2. 启用 VirtualBox 增强功能
# 3. 将虚拟机存储设为 SSD
# 4. 使用桥接网络代替 NAT
```

### Q2: WSL2 安装失败？

**解决方案：**
```powershell
# 以管理员身份运行 PowerShell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
# 重启后运行：wsl --install
```

### Q3: apt update 报错？

**解决方案：**
```bash
# 1. 检查网络连接
ping -c 3 ubuntu.com

# 2. 更换国内镜像源
sudo sed -i 's/archive.ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# 3. 重新更新
sudo apt update
```

### Q4: 忘记 sudo 密码？

**解决方案：**
```bash
# 在恢复模式重置（GRUB 菜单选择 recovery mode）
# 选择 root 进入命令行
passwd sreuser
# 输入两次新密码
reboot
```

### Q5: 虚拟机无法上网？

**解决方案：**
```bash
# 1. 检查网络配置
ip addr

# 2. 检查 DNS
cat /etc/resolv.conf

# 3. 重启网络
sudo systemctl restart NetworkManager

# 4. 检查 VirtualBox 网络设置为 NAT 或桥接
```

---

## 📝 笔记

（在此记录你的学习笔记、问题和心得）

---

## ✅ 完成检查

- [ ] 理解 Linux 的历史和重要性
- [ ] 完成 Ubuntu 22.04 安装
- [ ] 系统成功更新
- [ ] 安装基础工具软件
- [ ] 配置好 Git
- [ ] 完成至少 2 个练习题
- [ ] 记录了学习笔记

---

## 下一步预告

**Day 02** 将学习：**Linux 文件系统与目录结构 - FHS 标准详解**

需要掌握：
- Linux 文件系统层次结构（FHS 标准）
- 各目录的作用和用途
- 绝对路径与相对路径
- 文件类型与颜色含义

---

*由 SRE 学习计划自动生成 | 2026-04-13 09:00:00*
