# Day 76: Docker 简介与安装

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 简介与安装
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 理解 Docker 的核心概念和架构
- 掌握 Docker 与虚拟机的区别
- 能在 Linux 上安装 Docker
- 理解容器、镜像、仓库的关系
- 掌握 Docker 的核心组件（daemon、CLI、containerd）

---

## 📖 详细知识点

### 1. 什么是 Docker

Docker 是一个开源的容器化平台，让开发者可以打包应用及其依赖到一个可移植的容器中。

```
传统部署 vs 容器化部署：

传统：
  物理机/VM
  ├── OS (Ubuntu)
  ├── 运行环境 (Python 3.9, Node 16)
  ├── 应用 A
  └── 应用 B
  问题：依赖冲突、环境不一致、资源浪费

Docker：
  物理机/VM
  └── OS (共享内核)
      ├── 容器 A (Python 3.9 + App A)
      ├── 容器 B (Node 16 + App B)
      └── 容器 C (Redis)
  优势：隔离、轻量、可移植、快速启动
```

### 2. Docker vs 虚拟机

| 特性 | Docker 容器 | 虚拟机 (VM) |
|------|-------------|-------------|
| 启动时间 | 秒级 | 分钟级 |
| 体积 | MB 级 | GB 级 |
| 性能 | 接近原生 | 有虚拟化开销 |
| 隔离级别 | 进程级（共享内核） | 系统级（独立内核） |
| 资源占用 | 低 | 高 |
| 适用场景 | 微服务、CI/CD、开发环境 | 多 OS、强隔离需求 |

```
架构对比：

虚拟机：
  App A → Libs → Guest OS → Hypervisor → Host OS → Hardware
  App B → Libs → Guest OS → Hypervisor → Host OS → Hardware

Docker：
  App A → Libs → Container Engine → Host OS → Hardware
  App B → Libs → Container Engine → Host OS → Hardware

关键差异：
- VM 需要完整的 Guest OS（几百 MB ~ 几 GB）
- 容器共享宿主机内核，只需包含应用和依赖（几 MB ~ 几百 MB）
- VM 隔离更强（独立内核），容器更轻量
```

### 3. Docker 核心概念

```
Docker 三大核心：

镜像 (Image)：
  - 只读模板，包含应用和所有依赖
  - 分层存储，每层可复用
  - 类似虚拟机的"模板"

容器 (Container)：
  - 镜像的运行实例
  - 可创建、启动、停止、删除
  - 类似虚拟机的"运行实例"

仓库 (Registry)：
  - 存储和分发镜像的服务
  - Docker Hub 是公共仓库
  - 可自建私有仓库

工作流程：
  编写 Dockerfile → 构建镜像 (docker build) → 运行容器 (docker run)
```

### 4. Docker 架构

```
Docker 架构：

  docker CLI (用户命令)
      │
      ▼
  Docker Daemon (dockerd)
      ├── containerd (容器运行时管理)
      │     └── containerd-shim (容器进程)
      │           └── runc (OCI 运行时)
      │                 └── 容器进程
      ├── Image Service (镜像管理)
      ├── Network Service (网络管理)
      └── Volume Service (存储管理)

  核心组件：
  - dockerd：主守护进程，处理 API 请求
  - containerd：容器生命周期管理
  - runc：低级别容器运行时（OCI 规范）
  - docker CLI：用户命令行工具
```

### 5. 容器底层技术

```
Linux 内核提供的两大核心技术：

1. Namespaces（命名空间）— 隔离
   - PID Namespace：进程 ID 隔离
   - Network Namespace：网络隔离
   - Mount Namespace：文件系统隔离
   - UTS Namespace：主机名隔离
   - IPC Namespace：进程间通信隔离
   - User Namespace：用户 ID 隔离

2. Cgroups（控制组）— 资源限制
   - CPU：限制 CPU 使用
   - Memory：限制内存使用
   - I/O：限制磁盘 I/O
   - Network：限制网络带宽

3. UnionFS（联合文件系统）— 分层存储
   - Overlay2：Docker 默认存储驱动
   - AUFS：早期使用的存储驱动
   - Btrfs/ZFS：支持快照的存储驱动
```

---

## 🏗️ 安装 Docker

### Ubuntu/Debian

```bash
# 卸载旧版本
sudo apt-get remove docker docker-engine docker.io containerd runc

# 安装依赖
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG 密钥
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 添加仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 验证
sudo docker run hello-world
```

### CentOS/RHEL

```bash
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

### 配置免 sudo

```bash
sudo usermod -aG docker $USER
newgrp docker
docker run hello-world
```

### 配置镜像加速

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://registry.docker-cn.com"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 验证安装

```bash
# 查看版本
docker --version
docker compose version

# 查看系统信息
docker info

# 运行测试容器
docker run hello-world

# 查看容器
docker ps -a
```

---

## 🧪 练习题

### 练习 1：验证安装

运行以下命令验证 Docker 安装正确：

<details>
<summary>答案</summary>

```bash
# 检查 Docker 服务
systemctl status docker

# 运行测试容器
docker run hello-world

# 查看版本
docker --version
docker info

# 查看已下载的镜像
docker images
```
</details>

---

## 📚 扩展阅读

- [Docker 官方文档](https://docs.docker.com/)
- [Docker vs VM 详细对比](https://docs.docker.com/get-started/overview/)
- [容器运行时规范 OCI](https://opencontainers.org/)
