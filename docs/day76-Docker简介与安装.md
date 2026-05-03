# Day 76: Docker 简介与安装

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 简介与安装 — 容器 vs 虚拟机、OCI 标准、Docker 架构、安装配置、镜像加速、Docker CLI
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 1-6 (Linux 基础), Day 10 (systemd 服务管理), Day 14-15 (网络基础)

---

## 🎯 学习目标

完成 Day 76 的学习后，你应该能够：
- 深入理解容器与虚拟机的本质区别，以及各自的适用场景
- 掌握 Docker 的三层架构（CLI -> Daemon -> containerd/runc）及各组件职责
- 理解 OCI 标准对容器生态的意义
- 在 Ubuntu/CentOS 上独立完成 Docker Engine 的安装与配置
- 配置镜像加速器并理解其工作原理
- 熟练使用 Docker CLI 进行基本操作

---

## 📖 核心知识点

### 1. 容器技术的演进与本质

#### 1.1 从 chroot 到容器

容器并非 Docker 发明的技术，它的根基深植于 Linux 内核。理解这段历史有助于理解容器的本质。

```
容器技术演进时间线：

1979  chroot         ── 文件系统隔离的雏形
2000  FreeBSD Jail   ── 首次实现完整的环境隔离
2001  Linux VServer  ── 资源隔离的早期尝试
2006  cgroups         ── Google 提交到 Linux 内核，实现资源限制
2008  LXC             ── 结合 namespace + cgroups，第一个完整的 Linux 容器方案
2013  Docker          ── 让容器技术走进大众视野，简化了使用体验
2014  Kubernetes      ── 容器编排领域的事实标准
2015  OCI 成立        ── 容器运行时和镜像格式标准化
```

#### 1.2 容器 vs 虚拟机：本质区别

这是面试中的高频题，也是理解容器技术的基础。

```
┌─────────────────────────────────────────────────────────────────────┐
│                    虚拟机 (Virtual Machine)                          │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │
│  │  App A   │  │  App B   │  │  App C   │                         │
│  │  Libs A  │  │  Libs B  │  │  Libs C  │                         │
│  ├──────────┤  ├──────────┤  ├──────────┤                         │
│  │ Guest OS │  │ Guest OS │  │ Guest OS │  ← 每个 VM 独立内核     │
│  │ (Ubuntu) │  │ (CentOS) │  │ (Debian) │     通常 1-4 GB         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                         │
│       │             │             │                                 │
│  ┌────┴─────────────┴─────────────┴──────┐                         │
│  │           Hypervisor                  │  ← 硬件虚拟化层         │
│  │      (KVM / VMware / VirtualBox)      │     有性能开销          │
│  └───────────────────┬───────────────────┘                         │
│  ┌───────────────────┴───────────────────┐                         │
│  │           Host OS (Linux)             │                         │
│  └───────────────────┬───────────────────┘                         │
│  ┌───────────────────┴───────────────────┐                         │
│  │           Hardware                    │                         │
│  └───────────────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    容器 (Container)                                  │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                         │
│  │  App A   │  │  App B   │  │  App C   │                         │
│  │  Libs A  │  │  Libs B  │  │  Libs C  │                         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                         │
│       │             │             │                                 │
│  ┌────┴─────────────┴─────────────┴──────┐                         │
│  │        Container Runtime              │  ← 容器运行时           │
│  │     (containerd / Docker Engine)      │     轻量级              │
│  └───────────────────┬───────────────────┘                         │
│  ┌───────────────────┴───────────────────┐                         │
│  │         Host OS (共享内核)             │  ← 所有容器共享内核     │
│  └───────────────────┬───────────────────┘                         │
│  ┌───────────────────┴───────────────────┐                         │
│  │           Hardware                    │                         │
│  └───────────────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

| 特性 | 容器 (Container) | 虚拟机 (VM) |
|------|------------------|-------------|
| 隔离级别 | 进程级（共享宿主机内核） | 系统级（独立内核） |
| 启动时间 | 毫秒到秒级 | 分钟级 |
| 资源占用 | MB 级（仅包含应用及依赖） | GB 级（完整 OS + 应用） |
| 性能损耗 | 接近原生（<2%） | 5-20%（Hypervisor 开销） |
| 镜像大小 | 通常 10-500 MB | 通常 1-10 GB |
| 隔离安全性 | 较弱（共享内核是攻击面） | 较强（独立内核） |
| 密度 | 单机可运行数百容器 | 单机通常运行数十 VM |
| 运行时开销 | 仅消耗应用所需资源 | 需为 Guest OS 预留资源 |
| 适用场景 | 微服务、CI/CD、开发测试 | 多租户、强隔离、不同内核需求 |

**关键理解**：容器不是轻量级虚拟机，而是被隔离和限制的进程。容器内的进程与宿主机上的其他进程共享同一个内核，只是通过 namespace 看到的是"独立的世界"，通过 cgroup 被限制了可用资源。

#### 1.3 何时选择容器，何时选择虚拟机

```
选择容器的场景：
  + 微服务架构（每个服务独立部署和扩展）
  + CI/CD 流水线（构建、测试、部署环境一致）
  + 开发环境标准化（消除 "在我机器上能跑" 的问题）
  + 资源利用率优化（高密度部署）
  + 快速扩缩容（秒级启动新实例）

选择虚拟机的场景：
  + 运行不同操作系统（需要 Windows + Linux 共存）
  + 强隔离需求（多租户环境、安全敏感场景）
  + 需要自定义内核参数或加载内核模块
  + 运行遗留系统（旧版内核依赖）
  + 合规要求（某些行业要求完整的 OS 隔离）

最佳实践：混合使用
  + 底层用 VM 提供硬件隔离
  + VM 内运行容器，兼顾安全与效率
  + 例如：AWS EC2 实例中运行 Docker 容器
```

### 2. OCI 标准与容器生态

#### 2.1 什么是 OCI

OCI（Open Container Initiative，开放容器计划）于 2015 年由 Docker、CoreOS、Google、Microsoft 等公司联合成立，旨在制定容器行业的开放标准。

```
OCI 两大核心规范：

┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. Runtime Specification (运行时规范)                          │
│     ├── 定义：如何运行一个容器                                   │
│     ├── 内容：容器生命周期、挂载点、CPU/内存限制等               │
│     ├── 实现：runc, crun, kata-containers, gVisor              │
│     └── 意义：同一份镜像可以在任何 OCI 兼容的运行时上运行        │
│                                                                 │
│  2. Image Specification (镜像规范)                               │
│     ├── 定义：如何打包和分发容器镜像                             │
│     ├── 内容：manifest、layer、config 的 JSON 格式              │
│     ├── 实现：Docker 镜像、任何 OCI 兼容镜像                    │
│     └── 意义：镜像格式统一，可在不同平台间自由分发               │
│                                                                 │
│  3. Distribution Specification (分发规范，2021 年新增)           │
│     ├── 定义：如何推送和拉取镜像                                 │
│     ├── 内容：Registry API 协议                                 │
│     ├── 实现：Docker Hub, Harbor, GitHub Container Registry     │
│     └── 意义：统一镜像仓库的交互方式                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 OCI 标准化的实际意义

```
OCI 标准化之前：
  Docker 镜像只能在 Docker 上运行
  Docker Registry 只能由 Docker 使用
  各厂商各自为政

OCI 标准化之后：
  ┌─────────┐   OCI Image    ┌─────────┐
  │  Docker  │ ─────────────▶│  Podman  │
  └─────────┘                └─────────┘
       │                          │
       │ OCI Runtime              │ OCI Runtime
       ▼                          ▼
  ┌─────────┐                ┌─────────┐
  │  runc   │                │  crun   │
  └─────────┘                └─────────┘

  - Docker 构建的镜像可以直接在 Podman、containerd、CRI-O 上运行
  - Kubernetes 不再绑定 Docker，可以使用任何 OCI 兼容的运行时
  - 促进了容器生态的繁荣（Buildah、Skopeo、nerdctl 等工具涌现）
```

#### 2.3 容器运行时的层次

```
容器运行时分层架构：

┌────────────────────────────────────────────────────────────────┐
│  高级运行时 (High-level Runtime)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   Docker     │  │  containerd  │  │  CRI-O               │ │
│  │   Engine     │  │              │  │  (Kubernetes 专用)    │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
│         │                 │                      │             │
│         │    负责镜像管理、存储、网络、日志等     │             │
└─────────┼─────────────────┼──────────────────────┼─────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌────────────────────────────────────────────────────────────────┐
│  低级运行时 (Low-level Runtime / OCI Runtime)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │   runc   │  │   crun   │  │  kata    │  │   gVisor     │  │
│  │ (默认)    │  │ (C 实现)  │  │ (轻量VM) │  │ (用户态内核) │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
│                                                                │
│  负责：创建 namespace、设置 cgroup、启动容器进程                │
└────────────────────────────────────────────────────────────────┘
```

### 3. Docker 架构详解

#### 3.1 Docker 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker 架构全景图                              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Docker CLI (docker)                       │   │
│  │  用户通过命令行与 Docker 交互                                │   │
│  │  docker run / build / push / pull ...                       │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │ REST API (通常是 Unix Socket)           │
│                           │ /var/run/docker.sock                    │
│  ┌────────────────────────┴────────────────────────────────────┐   │
│  │                    Docker Daemon (dockerd)                   │   │
│  │                                                             │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │   │
│  │  │ 镜像管理     │ │ 网络管理     │ │ Volume 管理          │  │   │
│  │  │ (Image      │ │ (libnetwork)│ │ (Volume Driver)     │  │   │
│  │  │  Service)   │ │             │ │                     │  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │ gRPC                                    │
│  ┌────────────────────────┴────────────────────────────────────┐   │
│  │                    containerd                                │   │
│  │  容器生命周期管理：创建、启动、停止、删除                     │   │
│  │  镜像传输和存储                                              │   │
│  │  管理容器的 rootfs                                           │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                        │
│  ┌────────────────────────┴────────────────────────────────────┐   │
│  │                    containerd-shim                           │   │
│  │  每个容器对应一个 shim 进程                                  │   │
│  │  容器进程的直接父进程（PID 1 的父进程）                      │   │
│  │  职责：保持容器 stdin/stdout、上报容器退出状态               │   │
│  │  意义：containerd 可以重启而不影响正在运行的容器              │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                        │
│  ┌────────────────────────┴────────────────────────────────────┐   │
│  │                    runc (OCI Runtime)                        │   │
│  │  实际的容器创建工具                                          │   │
│  │  读取 OCI bundle 配置                                        │   │
│  │  调用内核 API 创建 namespace、cgroup                         │   │
│  │  启动容器内的 init 进程                                      │   │
│  │  创建完成后自身退出（容器由 shim 接管）                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Linux Kernel                              │   │
│  │  Namespaces (隔离) + Cgroups (限制) + UnionFS (分层存储)    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.2 一次 docker run 的完整流程

当你执行 `docker run -d -p 8080:80 nginx:latest` 时，背后发生了什么：

```
docker run -d -p 8080:80 nginx:latest 执行流程：

  用户
   │
   │  1. docker CLI 解析命令，通过 REST API 发送给 dockerd
   ▼
  dockerd (Docker Daemon)
   │
   │  2. 检查本地是否有 nginx:latest 镜像
   │     ├── 没有 → 从 Docker Hub 拉取（通过 Distribution Spec）
   │     └── 有 → 继续
   │
   │  3. 创建容器配置（网络、端口映射、环境变量等）
   │
   │  4. 调用 containerd 创建容器
   ▼
  containerd
   │
   │  5. 准备容器的 rootfs（使用 overlay2 联合挂载镜像层）
   │
   │  6. 启动 containerd-shim 进程
   ▼
  containerd-shim
   │
   │  7. 调用 runc 创建容器
   ▼
  runc
   │
   │  8. 配置 Linux namespace（PID、Network、Mount、UTS、IPC）
   │  9. 配置 cgroup（CPU、内存限制等）
   │  10. 设置 rootfs、网络、路由
   │  11. 启动容器内的 init 进程（nginx master process）
   │  12. runc 退出
   ▼
  containerd-shim 接管
   │
   │  13. 监控容器进程状态
   │  14. 管理容器的 stdin/stdout/stderr
   │  15. 容器进程退出时收集退出码
   ▼
  容器运行中
   │
   │  nginx 在隔离环境中监听 80 端口
   │  宿主机 8080 端口通过 iptables 转发到容器 80 端口
```

#### 3.3 为什么需要 containerd-shim

这是一个常见的面试追问。理解 shim 的设计哲学：

```
没有 shim 的架构（早期 Docker）：
  dockerd ──直接管理──▶ 容器进程

  问题：
  - dockerd 重启时，所有容器都会被杀掉
  - dockerd 成了容器进程的父进程，单点故障

有 shim 的架构（现代 Docker）：
  dockerd ──▶ containerd ──▶ shim ──▶ 容器进程

  优势：
  - dockerd 可以重启，不影响运行中的容器
  - containerd 可以重启，不影响运行中的容器
  - shim 是容器的直接父进程，负责收集退出码
  - 实现了守护进程无关性（daemonless containers）
```

### 4. 容器三大基石：Namespace、Cgroup、UnionFS

#### 4.1 Linux Namespace（命名空间）— 隔离

Namespace 是容器隔离的核心机制。每个 namespace 为进程提供一个独立的"视图"，让进程以为自己独占系统资源。

```
Linux Namespace 六大类型：

┌──────────────┬──────────────────────────────────────────────────┐
│ Namespace    │ 隔离内容                                         │
├──────────────┼──────────────────────────────────────────────────┤
│ PID          │ 进程 ID 空间                                     │
│              │ 容器内 PID 1 是 init 进程                        │
│              │ 容器内看不到宿主机其他进程                        │
├──────────────┼──────────────────────────────────────────────────┤
│ Network      │ 网络栈（IP 地址、端口、路由表、防火墙规则）       │
│              │ 每个容器有独立的 eth0、IP 地址                    │
│              │ 容器间通信通过 Docker 网络                        │
├──────────────┼──────────────────────────────────────────────────┤
│ Mount        │ 文件系统挂载点                                    │
│              │ 容器有独立的根文件系统                            │
│              │ 看不到宿主机的文件系统                            │
├──────────────┼──────────────────────────────────────────────────┤
│ UTS          │ 主机名和域名                                      │
│              │ 容器可以有自己的 hostname                         │
├──────────────┼──────────────────────────────────────────────────┤
│ IPC          │ 进程间通信（信号量、消息队列、共享内存）          │
│              │ 容器间 IPC 相互隔离                               │
├──────────────┼──────────────────────────────────────────────────┤
│ User         │ 用户和组 ID                                       │
│              │ 容器内 root 可映射为宿主机普通用户                │
│              │ 增强安全性                                        │
└──────────────┴──────────────────────────────────────────────────┘

还有一个较新的 namespace：
┌──────────────┬──────────────────────────────────────────────────┐
│ Cgroup       │ Cgroup 根目录视图                                 │
│ (Linux 4.6+) │ 容器只能看到自己的 cgroup 层次结构               │
└──────────────┴──────────────────────────────────────────────────┘
```

**验证 namespace 隔离**：

```bash
# 在宿主机上查看容器的 namespace
# 先启动一个容器
docker run -d --name test-ns nginx:latest

# 查看容器的 PID（在宿主机上的真实 PID）
docker inspect --format '{{.State.Pid}}' test-ns
# 假设输出 12345

# 查看该进程的 namespace
ls -la /proc/12345/ns/
# lrwxrwxrwx 1 root root 0 ... cgroup -> 'cgroup:[4026532XXX]'
# lrwxrwxrwx 1 root root 0 ... ipc -> 'ipc:[4026532XXX]'
# lrwxrwxrwx 1 root root 0 ... mnt -> 'mnt:[4026532XXX]'
# lrwxrwxrwx 1 root root 0 ... net -> 'net:[4026532XXX]'
# lrwxrwxrwx 1 root root 0 ... pid -> 'pid:[4026532XXX]'
# lrwxrwxrwx 1 root root 0 ... uts -> 'uts:[4026532XXX]'

# 在容器内查看进程列表
docker exec test-ns ps aux
# PID 1 是 nginx master process（容器内看到的 PID 与宿主机不同）

# 在宿主机上查看同一个进程
ps -p 12345 -o pid,ppid,cmd
# PID 是 12345（宿主机视角）

# 清理
docker rm -f test-ns
```

#### 4.2 Cgroups（控制组）— 资源限制

Cgroups 是 Linux 内核提供的资源限制机制，Docker 使用它来限制容器可以使用的 CPU、内存、磁盘 I/O 等资源。

```
Cgroups 资源控制器：

┌──────────────┬──────────────────────────────────────────────────┐
│ 控制器        │ 功能                                             │
├──────────────┼──────────────────────────────────────────────────┤
│ cpu          │ 限制 CPU 使用时间                                │
│ cpuacct      │ 统计 CPU 使用情况                                │
│ cpuset       │ 绑定到特定 CPU 核心                              │
│ memory       │ 限制内存使用量                                   │
│ blkio        │ 限制块设备 I/O                                   │
│ devices      │ 控制设备访问权限                                 │
│ freezer      │ 暂停/恢复进程                                    │
│ net_cls      │ 网络流量分类和控制                               │
│ pids         │ 限制进程数量                                     │
└──────────────┴──────────────────────────────────────────────────┘
```

```bash
# Docker 使用 cgroup 限制资源示例

# 限制 CPU：最多使用 1.5 个 CPU 核心
docker run --cpus="1.5" nginx

# 绑定到特定 CPU 核心（0 和 1）
docker run --cpuset-cpus="0,1" nginx

# 限制 CPU 权重（默认 1024，相对权重）
docker run --cpu-shares=512 nginx

# 限制内存：最多 512MB
docker run --memory="512m" nginx

# 限制内存 + swap
docker run --memory="512m" --memory-swap="1g" nginx

# 限制内存（硬限制 + 软限制）
docker run --memory="512m" --memory-reservation="256m" nginx

# 限制 I/O 读写速度
docker run --device-read-bps /dev/sda:10mb nginx
docker run --device-write-bps /dev/sda:10mb nginx

# 限制 I/O 操作次数
docker run --device-read-iops /dev/sda:1000 nginx

# 限制 PID 数量（防止 fork bomb）
docker run --pids-limit=100 nginx

# 查看容器资源使用
docker stats
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

```bash
# 在宿主机上查看容器的 cgroup 配置
# cgroup v2 路径
cat /sys/fs/cgroup/system.slice/docker-<container_id>.scope/memory.max
cat /sys/fs/cgroup/system.slice/docker-<container_id>.scope/cpu.max

# cgroup v1 路径
cat /sys/fs/cgroup/memory/docker/<container_id>/memory.limit_in_bytes
cat /sys/fs/cgroup/cpu/docker/<container_id>/cpu.cfs_quota_us
```

#### 4.3 UnionFS（联合文件系统）— 分层存储

UnionFS 是容器镜像分层存储的基础。它允许将多个目录（层）叠加在一起，形成一个统一的文件系统视图。

```
Overlay2 存储驱动结构：

  ┌─────────────────────────────────────────┐
  │           Container Layer (可写)         │  ← 容器运行时的修改
  │           (Read-Write Layer)             │     Copy-on-Write 机制
  ├─────────────────────────────────────────┤
  │           Image Layer 4 (只读)           │  ← COPY app.py /app/
  ├─────────────────────────────────────────┤
  │           Image Layer 3 (只读)           │  ← RUN pip install
  ├─────────────────────────────────────────┤
  │           Image Layer 2 (只读)           │  ← RUN apt-get install
  ├─────────────────────────────────────────┤
  │           Image Layer 1 (只读)           │  ← FROM ubuntu:22.04
  └─────────────────────────────────────────┘

Overlay2 的四个目录：
  lowerdir  → 只读的镜像层（可以有多个，用 : 分隔）
  upperdir  → 可写的容器层
  workdir   → OverlayFS 内部使用的工作目录
  merged    → 最终的合并视图（容器看到的文件系统）

Copy-on-Write (CoW) 机制：
  - 读取文件：直接从 lowerdir 读取（零拷贝）
  - 修改文件：先从 lowerdir 复制到 upperdir，再修改
  - 删除文件：在 upperdir 创建 whiteout 文件标记删除
  - 创建文件：直接在 upperdir 创建
```

```bash
# 查看 Docker 的存储驱动
docker info | grep "Storage Driver"
# Storage Driver: overlay2

# 查看镜像层信息
docker inspect nginx:latest | grep -A 20 "RootFS"
# "RootFS": {
#     "Type": "layers",
#     "Layers": [
#         "sha256:...",
#         "sha256:...",
#     ]
# }

# 查看镜像构建历史（每层对应一条指令）
docker history nginx:latest

# 查看容器的存储使用
docker system df
docker system df -v
```

### 5. Docker 安装

#### 5.1 Ubuntu/Debian 安装

```bash
#!/bin/bash
# Docker Engine 安装脚本 - Ubuntu/Debian
# 适用于 Ubuntu 22.04/24.04, Debian 12

set -e

echo "=== 1. 卸载旧版本 ==="
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

echo "=== 2. 安装依赖 ==="
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

echo "=== 3. 添加 Docker 官方 GPG 密钥 ==="
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "=== 4. 添加 Docker 官方仓库 ==="
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "=== 5. 安装 Docker Engine ==="
sudo apt-get update
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

echo "=== 6. 配置免 sudo 使用 Docker ==="
sudo usermod -aG docker $USER
echo "注意：需要重新登录或执行 'newgrp docker' 使用户组生效"

echo "=== 7. 验证安装 ==="
sudo docker run --rm hello-world

echo "=== 安装完成 ==="
docker --version
docker compose version
```

#### 5.2 CentOS/RHEL/Rocky Linux 安装

```bash
#!/bin/bash
# Docker Engine 安装脚本 - CentOS/RHEL/Rocky Linux
# 适用于 CentOS 7/8/9, RHEL 8/9, Rocky Linux 8/9

set -e

echo "=== 1. 卸载旧版本 ==="
sudo yum remove -y docker docker-client docker-client-latest \
    docker-common docker-latest docker-latest-logrotate \
    docker-logrotate docker-engine 2>/dev/null || true

echo "=== 2. 安装依赖 ==="
sudo yum install -y yum-utils

echo "=== 3. 添加 Docker 官方仓库 ==="
sudo yum-config-manager --add-repo \
    https://download.docker.com/linux/centos/docker-ce.repo

echo "=== 4. 安装 Docker Engine ==="
sudo yum install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

echo "=== 5. 启动 Docker ==="
sudo systemctl enable docker
sudo systemctl start docker

echo "=== 6. 配置免 sudo ==="
sudo usermod -aG docker $USER
echo "注意：需要重新登录或执行 'newgrp docker' 使用户组生效"

echo "=== 7. 验证安装 ==="
sudo docker run --rm hello-world

echo "=== 安装完成 ==="
docker --version
docker compose version
```

#### 5.3 生产环境 daemon.json 配置

```json
{
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  },
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://registry.docker-cn.com"
  ],
  "insecure-registries": [],
  "live-restore": true,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  },
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 5,
  "default-address-pools": [
    {
      "base": "172.17.0.0/12",
      "size": 24
    }
  ],
  "bip": "172.17.0.1/16",
  "exec-opts": ["native.cgroupdriver=systemd"],
  "data-root": "/var/lib/docker"
}
```

配置文件位置：`/etc/docker/daemon.json`

```bash
# 应用配置
sudo systemctl daemon-reload
sudo systemctl restart docker

# 验证配置
docker info
```

#### 5.4 配置说明与最佳实践

```
关键配置项说明：

storage-driver: "overlay2"
  - 推荐的存储驱动，性能和稳定性最佳
  - 支持 page cache 共享，减少内存占用

log-driver: "json-file"
  - 默认日志驱动，日志存储在宿主机文件系统
  - 生产环境必须配置 max-size 和 max-file 防止日志撑满磁盘

live-restore: true
  - Docker daemon 重启时不影响正在运行的容器
  - 升级 Docker 时无需停机
  - 生产环境强烈推荐

exec-opts: ["native.cgroupdriver=systemd"]
  - 使用 systemd 作为 cgroup 驱动
  - 与 Kubernetes 推荐配置一致
  - 避免 cgroup v1/v2 兼容性问题

max-concurrent-downloads: 10
  - 并发拉取镜像层数
  - 提高镜像拉取速度
  - 网络带宽有限时适当降低

default-address-pools
  - 定义 Docker 网络的 IP 地址池
  - 避免与宿主机网络冲突
  - 生产环境必须规划，避免与内网网段重叠
```

#### 5.5 镜像加速器配置

```bash
# 创建或编辑 daemon.json
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://registry.docker-cn.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF

# 重启 Docker
sudo systemctl daemon-reload
sudo systemctl restart docker

# 验证加速器配置
docker info | grep -A 5 "Registry Mirrors"
```

```
镜像加速器工作原理：

  用户 docker pull nginx
       │
       ▼
  Docker Client
       │
       │ 请求 nginx:latest 的 manifest
       ▼
  镜像加速器 (mirror)
       │
       │ 1. 检查本地缓存
       │    ├── 有 → 直接返回
       │    └── 没有 → 从 Docker Hub 拉取，缓存后返回
       ▼
  Docker Hub (registry-1.docker.io)
       │
       │ 返回镜像层数据
       ▼
  Docker Client 存储镜像

注意：
  - 加速器只缓存公共镜像，私有镜像仍然直接访问原始仓库
  - 加速器可能有延迟（缓存未同步时）
  - 企业环境建议自建私有仓库（Harbor）
```

### 6. Docker CLI 核心命令速查

```bash
# ===== 镜像管理 =====
docker pull nginx:latest          # 拉取镜像
docker images                     # 列出本地镜像
docker rmi nginx:latest           # 删除镜像
docker image prune                # 删除悬空镜像
docker image prune -a             # 删除所有未使用的镜像
docker tag nginx:latest mynginx:v1  # 打标签
docker save nginx:latest -o nginx.tar  # 导出镜像
docker load -i nginx.tar          # 导入镜像
docker inspect nginx:latest       # 查看镜像详情
docker history nginx:latest       # 查看构建历史

# ===== 容器管理 =====
docker run -d --name web -p 8080:80 nginx  # 创建并运行
docker ps                         # 查看运行中的容器
docker ps -a                      # 查看所有容器
docker stop web                   # 停止容器
docker start web                  # 启动容器
docker restart web                # 重启容器
docker rm web                     # 删除容器
docker rm -f web                  # 强制删除（运行中也可）
docker logs web                   # 查看日志
docker logs -f web                # 实时跟踪日志
docker exec -it web /bin/bash     # 进入容器
docker cp web:/etc/nginx/nginx.conf ./  # 从容器复制文件
docker top web                    # 查看容器进程
docker stats                      # 查看资源使用
docker diff web                   # 查看文件系统变更

# ===== 系统管理 =====
docker system df                  # 查看磁盘使用
docker system df -v               # 详细磁盘使用
docker system prune               # 清理未使用的资源
docker system prune -a            # 深度清理
docker info                       # 查看系统信息
docker version                    # 查看版本
```

### 7. SRE 实战：Docker 安装故障排查

#### 7.1 常见安装问题

```bash
# 问题 1：apt-get 安装时 GPG 错误
# 症状：GPG error ... NO_PUBKEY
# 解决：
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys <KEY_ID>
# 或者重新导入 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 问题 2：docker.sock 权限不足
# 症状：Got permission denied while trying to connect to the Docker daemon socket
# 解决：
sudo usermod -aG docker $USER
newgrp docker
# 或者临时使用 sudo

# 问题 3：Docker 启动失败
# 症状：Job for docker.service failed
# 排查：
sudo journalctl -xeu docker.service
sudo dockerd --debug  # 前台运行查看详细错误

# 问题 4：cgroup 驱动不匹配（Kubernetes 环境常见）
# 症状：failed to create container ... cgroupfs
# 解决：统一使用 systemd 作为 cgroup 驱动
# /etc/docker/daemon.json
# { "exec-opts": ["native.cgroupdriver=systemd"] }

# 问题 5：存储空间不足
# 症状：no space left on device
# 排查：
docker system df
df -h /var/lib/docker
# 解决：
docker system prune -a --volumes
# 或者迁移 Docker 数据目录
```

#### 7.2 生产环境健康检查脚本

```bash
#!/bin/bash
# docker-health-check.sh - Docker 环境健康检查

set -e

echo "=========================================="
echo "Docker 环境健康检查"
echo "=========================================="

# 1. Docker 服务状态
echo -e "\n--- Docker 服务状态 ---"
if systemctl is-active docker > /dev/null 2>&1; then
    echo "[OK] Docker 服务运行中"
else
    echo "[FAIL] Docker 服务未运行"
    exit 1
fi

# 2. Docker 版本信息
echo -e "\n--- Docker 版本 ---"
docker version --format 'Client: {{.Client.Version}}, Server: {{.Server.Version}}'

# 3. 存储驱动
echo -e "\n--- 存储配置 ---"
docker info --format 'Storage Driver: {{.Driver}}'
docker info --format 'Docker Root Dir: {{.DockerRootDir}}'
df -h /var/lib/docker | tail -1

# 4. 磁盘使用
echo -e "\n--- 磁盘使用 ---"
docker system df

# 5. 运行中的容器
echo -e "\n--- 运行中的容器 ---"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 6. 镜像加速器
echo -e "\n--- Registry Mirrors ---"
docker info --format '{{.RegistryConfig.Mirrors}}'

# 7. 僵尸容器检查
ZOMBIE_COUNT=$(docker ps -a --filter "status=dead" --format "{{.ID}}" | wc -l)
echo -e "\n--- 僵尸容器: ${ZOMBIE_COUNT} 个 ---"
if [ "$ZOMBIE_COUNT" -gt 0 ]; then
    echo "建议清理: docker container prune"
fi

# 8. 悬空镜像检查
DANGLING_COUNT=$(docker images -f "dangling=true" --format "{{.ID}}" | wc -l)
echo "--- 悬空镜像: ${DANGLING_COUNT} 个 ---"
if [ "$DANGLING_COUNT" -gt 0 ]; then
    echo "建议清理: docker image prune"
fi

echo -e "\n=========================================="
echo "健康检查完成"
echo "=========================================="
```

---

## 💻 实战练习

### 练习 1：Docker 安装与验证

**目标**：在一台 Linux 机器上完成 Docker 的安装、配置和基本验证。

```bash
# 1. 安装 Docker Engine
# 根据你的 Linux 发行版选择对应的安装脚本

# 2. 配置镜像加速器
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker

# 3. 验证安装
docker --version
docker info
docker run --rm hello-world

# 4. 查看 Docker 系统信息
docker info | grep -E "Storage Driver|Cgroup Driver|Docker Root Dir|Live Restore"

# 5. 查看 hello-world 镜像的层信息
docker pull hello-world
docker history hello-world
docker inspect hello-world | grep -A 10 "RootFS"

# 6. 清理
docker rmi hello-world
```

### 练习 2：Namespace 隔离验证

**目标**：通过实际操作验证 Docker 的 namespace 隔离机制。

```bash
# 1. 启动一个容器并获取其宿主机 PID
docker run -d --name ns-test ubuntu:22.04 sleep 3600
CONTAINER_PID=$(docker inspect --format '{{.State.Pid}}' ns-test)
echo "容器在宿主机上的 PID: $CONTAINER_PID"

# 2. 查看容器的 namespace
echo "=== 容器的 namespace ==="
ls -la /proc/$CONTAINER_PID/ns/

# 3. 对比宿主机的 namespace
echo "=== 宿主机的 namespace ==="
ls -la /proc/1/ns/

# 4. 验证 PID 隔离
echo "=== 容器内进程列表 ==="
docker exec ns-test ps aux

echo "=== 宿主机进程列表（对比）==="
ps aux | head -5

# 5. 验证 UTS 隔离（主机名）
echo "=== 容器主机名 ==="
docker exec ns-test hostname

echo "=== 宿主机主机名 ==="
hostname

# 6. 验证 Network 隔离
echo "=== 容器网络 ==="
docker exec ns-test ip addr show

echo "=== 宿主机网络（对比）==="
ip addr show | head -20

# 7. 验证 Mount 隔离
echo "=== 容器挂载点 ==="
docker exec ns-test mount

echo "=== 容器文件系统 ==="
docker exec ns-test ls /

# 8. 清理
docker rm -f ns-test
```

### 练习 3：Cgroup 资源限制验证

**目标**：验证 Docker 使用 cgroup 对容器进行资源限制。

```bash
# 1. CPU 限制验证
echo "=== CPU 限制验证 ==="
docker run --rm --cpus="0.5" --name cpu-test ubuntu:22.04 \
    bash -c "apt-get update > /dev/null 2>&1; apt-get install -y stress-ng > /dev/null 2>&1; stress-ng -c 2 -t 5 --metrics-brief"

# 2. 内存限制验证
echo "=== 内存限制验证 ==="
docker run --rm --memory="256m" --name mem-test ubuntu:22.04 \
    bash -c "
        echo '容器内存限制:';
        cat /sys/fs/cgroup/memory.max 2>/dev/null || cat /sys/fs/cgroup/memory/memory.limit_in_bytes;
        echo '';
        echo '内存使用情况:';
        free -m
    "

# 3. PID 限制验证
echo "=== PID 限制验证 ==="
docker run --rm --pids-limit=10 --name pid-test ubuntu:22.04 \
    bash -c "
        echo 'PID 限制:';
        cat /sys/fs/cgroup/pids.max 2>/dev/null || cat /sys/fs/cgroup/pids/pids.max;
        echo '尝试创建超过限制的进程...';
        for i in \$(seq 1 15); do sleep 100 & done 2>&1 || echo '达到 PID 限制，无法创建更多进程'
    "

# 4. 在宿主机上查看 cgroup 配置
echo "=== 宿主机 cgroup 信息 ==="
docker run -d --name cgroup-test --cpus="1" --memory="512m" nginx
CONTAINER_ID=$(docker inspect --format '{{.Id}}' cgroup-test)

# cgroup v2
if [ -d "/sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope" ]; then
    echo "CPU 限制:"
    cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/cpu.max
    echo "内存限制:"
    cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/memory.max
fi

# 5. 查看容器资源使用
echo "=== 容器资源使用 ==="
docker stats cgroup-test --no-stream

# 6. 清理
docker rm -f cgroup-test
```

---

## 🎯 面试题精选

### 面试题 1：容器和虚拟机的本质区别是什么？

**参考答案**：

容器和虚拟机的核心区别在于隔离层级不同。虚拟机通过 Hypervisor 虚拟出完整的硬件环境，每个 VM 运行独立的操作系统内核，隔离级别是系统级的。容器则共享宿主机的内核，通过 Linux namespace 实现进程、网络、文件系统等资源的隔离，通过 cgroup 实现资源限制。容器本质上是被隔离和限制的进程，而非独立的操作系统实例。这使得容器的启动时间从分钟级缩短到毫秒级，资源开销从 GB 级降低到 MB 级。但容器的隔离性弱于 VM，因为共享内核意味着内核漏洞可能影响所有容器。

### 面试题 2：Docker 的架构是怎样的？各组件的职责是什么？

**参考答案**：

Docker 采用客户端-服务端架构，由四个核心组件组成。Docker CLI 是用户交互的命令行工具，通过 REST API 与 Docker Daemon 通信。Docker Daemon（dockerd）是核心守护进程，负责镜像管理、网络管理、Volume 管理等高级功能。containerd 是容器运行时管理器，负责容器的生命周期管理、镜像传输和存储。runc 是 OCI 标准的低级运行时，负责实际创建容器——调用内核 API 创建 namespace、配置 cgroup、启动容器进程。每个容器还有一个 containerd-shim 进程作为容器的直接父进程，使得 dockerd 和 containerd 可以重启而不影响正在运行的容器。

### 面试题 3：什么是 OCI 标准？它对容器生态有什么意义？

**参考答案**：

OCI（Open Container Initiative）是 2015 年成立的容器行业标准组织，定义了三个核心规范：Runtime Specification 规定如何运行容器，Image Specification 规定如何打包和分发镜像，Distribution Specification 规定如何推送和拉取镜像。OCI 标准的意义在于：首先，它实现了容器运行时的可替换性，Docker 构建的镜像可以在 Podman、containerd、CRI-O 等任何 OCI 兼容运行时上运行；其次，它促进了 Kubernetes 的容器运行时接口（CRI）的发展，K8s 不再绑定 Docker；最后，它催生了丰富的工具生态，如 Buildah、Skopeo、nerdctl 等。

### 面试题 4：Linux Namespace 有哪些类型？各自隔离什么？

**参考答案**：

Linux 有 7 种 namespace：PID namespace 隔离进程 ID 空间，使容器内的 PID 从 1 开始，看不到宿主机其他进程。Network namespace 隔离网络栈，每个容器有独立的 IP 地址、端口空间、路由表和防火墙规则。Mount namespace 隔离文件系统挂载点，使容器有独立的根文件系统。UTS namespace 隔离主机名和域名。IPC namespace 隔离进程间通信资源（信号量、消息队列、共享内存）。User namespace 隔离用户和组 ID，可将容器内 root 映射为宿主机普通用户。Cgroup namespace（Linux 4.6+）隔离 cgroup 根目录视图。Docker 默认使用前 6 种 namespace 来实现容器隔离。

### 面试题 5：解释 Docker 的 Copy-on-Write 机制。

**参考答案**：

Docker 使用 Overlay2 联合文件系统实现 Copy-on-Write（CoW）。镜像由多个只读层叠加组成，容器运行时在最上层添加一个可写层。当读取文件时，直接从只读层读取，无需拷贝，性能与原生文件系统一致。当修改文件时，先将文件从只读层复制到可写层，然后在可写层进行修改，不影响原始镜像层。当删除文件时，在可写层创建一个 whiteout 文件标记该文件已删除。当创建新文件时，直接在可写层创建。这种机制使得多个容器可以共享相同的镜像只读层，只有修改的部分才占用额外存储空间，极大地节省了磁盘和内存。

### 面试题 6：containerd-shim 的作用是什么？为什么需要它？

**参考答案**：

containerd-shim 是每个容器的直接父进程，它的存在解决了容器生命周期管理中的一个关键问题：守护进程重启时如何不影响运行中的容器。如果没有 shim，Docker Daemon 直接管理容器进程，当 dockerd 重启（升级、崩溃）时，所有容器都会失去父进程而被终止。有了 shim 之后，containerd 负责启动 shim，shim 再启动 runc 创建容器，runc 创建完成后退出，shim 成为容器进程的父进程。这样 dockerd 和 containerd 都可以独立重启而不影响运行中的容器。此外，shim 还负责管理容器的 stdin/stdout/stderr 流，以及在容器退出时收集退出码并上报给 containerd。

### 面试题 7：如何限制容器的资源使用？底层原理是什么？

**参考答案**：

Docker 使用 Linux cgroup（控制组）机制来限制容器的资源使用。CPU 限制方面：`--cpus` 设置 CPU 核心数上限（底层使用 cpu.cfs_quota_us/cpu.cfs_period_us），`--cpuset-cpus` 绑定到特定 CPU 核心（使用 cpuset.cpus），`--cpu-shares` 设置 CPU 权重（使用 cpu.shares，相对权重）。内存限制方面：`--memory` 设置内存硬限制（使用 memory.limit_in_bytes），`--memory-reservation` 设置内存软限制（使用 memory.soft_limit_in_bytes），`--memory-swap` 设置内存+swap 总限制。I/O 限制方面：`--device-read-bps`/`--device-write-bps` 限制读写速度，`--device-read-iops`/`--device-write-iops` 限制 IOPS。进程数限制：`--pids-limit` 限制容器内最大进程数，防止 fork bomb。

### 面试题 8：Docker daemon.json 中哪些配置项是生产环境必须的？

**参考答案**：

生产环境必须配置以下项目：1）`log-driver` 和 `log-opts`（max-size、max-file），防止容器日志撑满磁盘，这是最常见的生产事故之一。2）`live-restore: true`，确保 Docker daemon 重启时不影响运行中的容器，实现无缝升级。3）`storage-driver: overlay2`，使用推荐的存储驱动。4）`exec-opts: ["native.cgroupdriver=systemd"]`，与 Kubernetes 推荐配置一致。5）`default-address-pools`，规划 Docker 网络的 IP 地址段，避免与内网网段冲突。6）`default-ulimits` 中设置 nofile，提高文件描述符上限。7）`data-root`，可选地将 Docker 数据目录迁移到更大的磁盘分区。

### 面试题 9：Docker 安装后执行 docker 命令报权限不足，如何解决？为什么需要这样配置？

**参考答案**：

这是因为 Docker Daemon 以 root 用户运行，其 Unix Socket（/var/run/docker.sock）的默认权限是 root:docker 660。非 root 用户且不在 docker 组中的用户无法访问该 socket。解决方法是执行 `sudo usermod -aG docker $USER` 将当前用户加入 docker 组，然后重新登录或执行 `newgrp docker` 使组生效。这样做的本质是用户获得了访问 docker.sock 的权限。需要注意的是，docker 组的用户等同于拥有 root 权限，因为可以通过 Docker 挂载宿主机文件系统来获取 root 权限。生产环境中应谨慎授予 docker 组权限，或使用 rootless Docker 模式。

### 面试题 10：如何将 Docker 数据目录迁移到另一个磁盘？

**参考答案**：

步骤如下：1）停止 Docker 服务：`sudo systemctl stop docker`。2）迁移数据：`sudo rsync -aP /var/lib/docker/ /new-path/docker/`。3）修改配置文件 `/etc/docker/daemon.json`，添加 `"data-root": "/new-path/docker"`。4）重启 Docker：`sudo systemctl start docker`。5）验证：`docker info | grep "Docker Root Dir"`。6）确认一切正常后删除旧数据：`sudo rm -rf /var/lib/docker`。注意事项：迁移前确保新磁盘有足够的空间；使用 rsync 而非 cp 以保留文件权限和属性；如果使用了 systemd 的 docker.socket，可能还需要更新 socket 配置。

---

## 📚 深入阅读

### 官方文档
- [Docker 官方文档 - Get Started](https://docs.docker.com/get-started/)
- [Docker Engine 安装指南](https://docs.docker.com/engine/install/)
- [Docker Daemon 配置参考](https://docs.docker.com/engine/reference/commandline/dockerd/)
- [OCI Runtime Specification](https://github.com/opencontainers/runtime-spec)
- [OCI Image Specification](https://github.com/opencontainers/image-spec)

### 技术深度文章
- [Understanding the Docker Internals](https://medium.com/@nirmaljpatel/understanding-docker-internals-7284579323d9)
- [Linux Namespaces and Cgroups](https://www.nginx.com/blog/what-are-namespaces-cgroups-how-do-they-work/)
- [OverlayFS Documentation](https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html)

### 推荐书籍
- 《Docker Deep Dive》— Nigel Poulton
- 《Container Security》— Liz Rice（安全视角的容器技术）
- 《Docker - Up & Running》— Sean Kane & Karl Matthias

---

## ✅ 自检清单

### 理论检查点
- [ ] 能清晰解释容器与虚拟机的本质区别（进程级隔离 vs 系统级隔离）
- [ ] 理解 Docker 的三层架构（CLI -> Daemon -> containerd -> runc）
- [ ] 知道 OCI 标准的三大规范及其意义
- [ ] 理解 Linux namespace 的 6 种类型及各自隔离的内容
- [ ] 理解 cgroup 的作用及常用资源限制参数
- [ ] 理解 Overlay2 存储驱动和 Copy-on-Write 机制
- [ ] 知道 containerd-shim 存在的原因

### 实操检查点
- [ ] 能在 Ubuntu/CentOS 上独立完成 Docker 安装
- [ ] 能正确配置 daemon.json（日志、存储、网络等）
- [ ] 能配置镜像加速器
- [ ] 能使用 namespace 相关命令验证容器隔离
- [ ] 能使用 cgroup 相关命令验证资源限制
- [ ] 能运行健康检查脚本诊断环境问题

### 能力验证标准
- [ ] 能在 30 分钟内完成一台新机器的 Docker 安装和基础配置
- [ ] 能回答 80% 以上的面试题
- [ ] 能诊断和解决常见的 Docker 安装和配置问题
- [ ] 能为团队编写 Docker 安装和配置的标准化文档
