# Day 86: Docker 安全

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 安全基线、权限控制、安全模块、镜像签名
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 80-85 Docker 基础与进阶

---

## 🎯 学习目标

- 理解 Docker 安全架构与威胁模型
- 掌握容器运行时安全配置（seccomp、AppArmor、SELinux）
- 能够实施最小权限原则和安全基线
- 会使用 Docker Bench Security 进行安全审计
- 理解镜像签名与供应链安全

---

## 📖 核心知识点

### 1. Docker 安全架构与威胁模型

#### 1.1 容器安全层次模型

```
┌─────────────────────────────────────────────────────────────┐
│                      应用层安全                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  容器运行时安全                       │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │              宿主机内核安全                   │   │   │
│  │  │  ┌─────────────────────────────────────┐   │   │   │
│  │  │  │          硬件/固件安全               │   │   │   │
│  │  │  └─────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### 1.2 Docker 安全核心原则

| 原则 | 说明 | 实施方法 |
|------|------|----------|
| 最小权限 | 容器只拥有必要的权限 | --cap-drop, --user |
| 攻击面最小化 | 减少潜在攻击入口 | 精简镜像, 只读文件系统 |
| 深度防御 | 多层安全控制 | seccomp + AppArmor + SELinux |
| 默认安全 | 安全配置默认启用 | daemon.json 配置 |
| 不信任原则 | 假设容器已被入侵 | 网络隔离, 资源限制 |

#### 1.3 容器与虚拟机安全对比

```
┌──────────────────────────────────────────────────────────────┐
│                     虚拟机安全模型                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │   VM 1   │  │   VM 2   │  │   VM 3   │                  │
│  │ (内核)   │  │ (内核)   │  │ (内核)   │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Hypervisor                        │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   宿主机内核                         │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    容器安全模型                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │Container1│  │Container2│  │Container3│                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               共享宿主机内核                         │   │
│  │         (Namespace + Cgroup + Security)              │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**关键区别：**
- 虚拟机：硬件级隔离，每个 VM 有独立内核
- 容器：进程级隔离，共享宿主机内核
- 容器逃逸风险：利用内核漏洞可能突破隔离

---

### 2. 容器运行时安全配置

#### 2.1 Root 权限控制

**问题：** 默认容器以 root 运行，存在权限提升风险

```bash
# 查看容器运行用户
docker run --rm alpine id
# uid=0(root) gid=0(root) groups=0(root)

# 创建非 root 用户的 Dockerfile
cat > Dockerfile.secure << 'EOF'
FROM node:18-alpine

# 创建应用用户
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -s /bin/sh -D appuser

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制应用代码
COPY --chown=appuser:appgroup . .

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 3000

# 启动应用
CMD ["node", "server.js"]
EOF

# 构建并验证
docker build -f Dockerfile.secure -t secure-app .
docker run --rm secure-app id
# uid=1001(appuser) gid=1001(appgroup) groups=1001(appgroup)
```

**运行时强制非 root：**

```bash
# 方式 1：使用 --user 参数
docker run --user 1001:1001 myapp

# 方式 2：在 daemon.json 全局配置
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "userns-remap": "default"
}
EOF
sudo systemctl restart docker

# 方式 3：使用 user namespace 重映射
# 创建 subordinate 用户
sudo useradd -r -s /bin/false dockremap
echo "dockremap:100000:65536" | sudo tee -a /etc/subuid
echo "dockremap:100000:65536" | sudo tee -a /etc/subgid
```

#### 2.2 Linux Capabilities 管理

**Docker 默认授予的 Capabilities：**

```
┌─────────────────────────────────────────────────────────────┐
│                Docker 默认 Capabilities                     │
├─────────────────────────────────────────────────────────────┤
│ CAP_CHOWN          - 修改文件所有者                          │
│ CAP_DAC_OVERRIDE   - 绕过文件权限检查                        │
│ CAP_FSETID         - 设置 setuid/setgid 位                  │
│ CAP_FOWNER         - 绕过文件所有者检查                      │
│ CAP_MKNOD          - 创建设备文件                            │
│ CAP_NET_RAW        - 使用 RAW socket                        │
│ CAP_SETGID         - 设置 GID                               │
│ CAP_SETUID         - 设置 UID                               │
│ CAP_SETFCAP        - 设置文件 capabilities                   │
│ CAP_SETPCAP        - 修改进程 capabilities                   │
│ CAP_NET_BIND_SERVICE - 绑定 1024 以下端口                    │
│ CAP_SYS_CHROOT     - 使用 chroot                            │
│ CAP_KILL           - 发送信号                                │
│ CAP_AUDIT_WRITE    - 写入审计日志                            │
└─────────────────────────────────────────────────────────────┘
```

**最佳实践：移除所有 capabilities，按需添加**

```bash
# 移除所有 capabilities，只添加必要的
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE nginx

# Web 应用常用配置
docker run \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --cap-add=CHOWN \
  --cap-add=SETUID \
  --cap-add=SETGID \
  mywebapp

# 查看容器 capabilities
docker inspect --format='{{.HostConfig.CapAdd}}' container_name

# 需要特殊权限的场景
# 1. 网络工具（ping, tcpdump）
docker run --cap-add=NET_ADMIN --cap-add=NET_RAW nicolaka/netshoot

# 2. 修改内核参数
docker run --cap-add=SYS_ADMIN myapp

# 3. 调试容器
docker run --cap-add=SYS_PTRACE --security-opt seccomp=unconfined debug-image
```

#### 2.3 只读文件系统

```bash
# 创建只读容器
docker run --read-only myapp

# 只读 + 临时目录
docker run \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  --tmpfs /var/run:rw,noexec,nosuid,size=10m \
  myapp

# 只读 + 挂载卷
docker run \
  --read-only \
  --volume app-data:/app/data:rw \
  --tmpfs /tmp:rw \
  myapp

# Dockerfile 中设置只读
cat > Dockerfile.readonly << 'EOF'
FROM python:3.11-slim

RUN useradd -r -s /bin/false appuser

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p /tmp/app && chown appuser:appuser /tmp/app

USER appuser
ENV TMPDIR=/tmp/app

CMD ["python", "app.py"]
EOF
```

**只读文件系统的影响与解决方案：**

| 问题 | 解决方案 |
|------|----------|
| 应用需要写入临时文件 | 挂载 tmpfs 到 /tmp |
| 日志写入 | 使用 stdout/stderr 或挂载日志卷 |
| 配置文件修改 | 使用环境变量或配置中心 |
| 数据库数据 | 挂载持久化卷 |
| PID 文件 | 挂载 tmpfs 到 /var/run |

---

### 3. Seccomp 安全配置

#### 3.1 Seccomp 基础

Seccomp（Secure Computing Mode）限制容器可以调用的系统调用。

```
┌─────────────────────────────────────────────────────────────┐
│                    Seccomp 工作流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Container Process                                         │
│        │                                                    │
│        ▼                                                    │
│   System Call                                               │
│        │                                                    │
│        ▼                                                    │
│   ┌─────────────┐                                          │
│   │ Seccomp     │ ──→  检查系统调用是否允许                  │
│   │ Filter      │                                          │
│   └─────────────┘                                          │
│        │                                                    │
│   ┌────┴────┐                                              │
│   ▼         ▼                                              │
│ Allow     Deny (返回 EPERM)                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2 Docker 默认 Seccomp 配置

```bash
# 查看默认 seccomp 配置
wget https://raw.githubusercontent.com/moby/moby/master/profiles/seccomp/default.json
cat default.json | python3 -m json.tool | head -50

# 默认配置阻止的危险系统调用：
# - kexec_load: 加载新内核
# - open_by_handle_at: 绕过文件系统权限
# - init_module/finit_module: 加载内核模块
# - bpf: eBPF 操作
# - mount: 挂载文件系统
# - ptrace: 进程跟踪
# - reboot: 重启系统
# - keyctl: 内核密钥管理
```

#### 3.3 自定义 Seccomp 配置

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "archMap": [
    {
      "architecture": "SCMP_ARCH_X86_64",
      "subArchitectures": [
        "SCMP_ARCH_X86",
        "SCMP_ARCH_X32"
      ]
    }
  ],
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "arch_prctl", "bind", "brk",
        "clock_gettime", "close", "connect", "dup", "dup2", "dup3",
        "epoll_create", "epoll_create1", "epoll_ctl", "epoll_wait",
        "execve", "exit", "exit_group", "fcntl", "fstat", "futex",
        "getcwd", "getdents64", "getpid", "getsockname", "gettid",
        "ioctl", "listen", "lseek", "madvise", "mmap", "mprotect",
        "munmap", "nanosleep", "newfstatat", "openat", "pipe",
        "poll", "prctl", "pread64", "pwrite64", "read", "readlink",
        "recvfrom", "recvmsg", "rename", "rt_sigaction", "rt_sigprocmask",
        "sendmsg", "sendto", "set_robust_list", "set_tid_address",
        "setsockopt", "shutdown", "sigaltstack", "socket", "stat",
        "tgkill", "uname", "unlink", "wait4", "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

```bash
# 使用自定义 seccomp 配置
docker run --security-opt seccomp=custom-seccomp.json myapp

# 禁用 seccomp（不推荐，仅用于调试）
docker run --security-opt seccomp=unconfined myapp

# 测试 seccomp 配置
docker run --security-opt seccomp=custom-seccomp.json alpine sh -c "mount /dev/sda /mnt" 2>&1
# mount: permission denied (are you root?)
```

#### 3.4 Seccomp 配置生成工具

```bash
# 使用 strace 追踪应用系统调用
strace -f -o /tmp/trace.log python app.py
cat /tmp/trace.log | awk -F'(' '{print $1}' | sort -u

# 使用 oci-seccomp-bpf-hook 自动生成
# https://github.com/containers/oci-seccomp-bpf-hook

# 安装
sudo dnf install oci-seccomp-bpf-hook

# 使用
sudo podman run --annotation io.containers.trace-syscall=log:seccomp.json myapp
```

---

### 4. AppArmor 配置

#### 4.1 AppArmor 基础

AppArmor 是 Linux 安全模块，通过配置文件限制程序的访问权限。

```
┌─────────────────────────────────────────────────────────────┐
│                    AppArmor 工作原理                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Process                                                   │
│      │                                                      │
│      ▼                                                      │
│   Access Request (文件, 网络, capabilities)                 │
│      │                                                      │
│      ▼                                                      │
│   ┌─────────────┐                                          │
│   │  AppArmor   │ ──→  加载的 Profile                       │
│   │  Enforcer   │                                          │
│   └─────────────┘                                          │
│      │                                                      │
│   ┌──┴───┐                                                 │
│   ▼      ▼                                                 │
│ Allow   Deny (记录日志 + 拒绝)                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2 Docker 默认 AppArmor 配置

```bash
# 查看 Docker 默认 AppArmor profile
cat /etc/apparmor.d/docker-default

# 查看加载的 profile
sudo aa-status | grep docker

# Docker 默认 profile 主要限制：
# - 禁止写入 /proc 和 /sys 的大部分文件
# - 禁止挂载操作
# - 禁止访问 /sys/fs/cgroup
# - 禁止加载内核模块
# - 禁止修改网络配置
```

#### 4.3 自定义 AppArmor Profile

```bash
# 创建自定义 profile
cat > /etc/apparmor.d/docker-custom << 'EOF'
#include <tunables/global>

profile docker-custom flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>

  # 禁止所有文件写入
  deny /** w,

  # 允许读取必要文件
  /etc/ld.so.cache r,
  /etc/ld.so.preload r,
  /lib/** r,
  /usr/lib/** r,
  /etc/ssl/** r,
  /etc/resolv.conf r,
  /etc/hosts r,
  /etc/nsswitch.conf r,

  # 允许应用目录读写
  /app/** rw,
  /tmp/** rw,
  /var/log/** rw,

  # 允许网络访问
  network inet stream,
  network inet dgram,
  network inet6 stream,
  network inet6 dgram,

  # 禁止危险操作
  deny mount,
  deny umount,
  deny pivot_root,
  deny ptrace,
  deny /proc/sys/** w,
  deny /sys/** w,
  deny /dev/mem rw,
  deny /dev/kmem rw,
  deny /dev/sd* rw,

  # 允许信号
  signal (receive) set=(term, kill),

  # 允许 ptrace（调试用，生产环境应删除）
  # ptrace (read, trace) peer=docker-custom,
}
EOF

# 加载 profile
sudo apparmor_parser -r /etc/apparmor.d/docker-custom

# 使用自定义 profile 运行容器
docker run --security-opt apparmor=docker-custom myapp

# 验证 profile 已应用
docker inspect --format='{{.AppArmorProfile}}' container_name
```

#### 4.4 AppArmor Profile 调试

```bash
# 查看 AppArmor 拒绝日志
sudo dmesg | grep apparmor
sudo journalctl -k | grep apparmor

# 使用 aa-logprof 从日志生成 profile
sudo aa-logprof

# 使用 aa-genprof 交互式生成 profile
sudo aa-genprof /path/to/program

# 运行在 complain 模式（记录但不阻止）
sudo aa-complain /etc/apparmor.d/docker-custom

# 切换回 enforce 模式
sudo aa-enforce /etc/apparmor.d/docker-custom
```

---

### 5. SELinux 配置

#### 5.1 SELinux 基础

```
┌─────────────────────────────────────────────────────────────┐
│                    SELinux 安全模型                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Subject (进程)                                            │
│      │                                                      │
│      ▼                                                      │
│   Access Request                                            │
│      │                                                      │
│      ▼                                                      │
│   ┌─────────────┐     ┌─────────────┐                     │
│   │ SELinux     │ ──→ │ Policy      │                     │
│   │ Security    │     │ Database    │                     │
│   │ Server      │     └─────────────┘                     │
│   └─────────────┘                                          │
│      │                                                      │
│   ┌──┴───┐                                                 │
│   ▼      ▼                                                 │
│ Allow   Deny (记录 AVC 日志)                                │
│                                                             │
│   Object (文件, 套接字, 进程)                               │
│   - 标签: user:role:type:level                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 Docker SELinux 配置

```bash
# 检查 SELinux 状态
getenforce
# Enforcing

sestatus
# SELinux status:                 enabled
# SELinuxfs mount:                /sys/fs/selinux
# Current mode:                   enforcing

# 启用 Docker SELinux 支持
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "selinux-enabled": true
}
EOF
sudo systemctl restart docker

# 使用 SELinux 标签运行容器
docker run --security-opt label=type:svirt_sandbox_file_t myapp

# 禁用容器的 SELinux 标签（不推荐）
docker run --security-opt label=disable myapp

# 设置容器的 SELinux 级别
docker run --security-opt label=level:s0:c100,c200 myapp
```

#### 5.3 SELinux 容器策略

```bash
# 查看容器相关 SELinux 上下文
ps auxZ | grep docker
# system_u:system_r:container_t:s0:c100,c200 root ...

# 查看文件上下文
ls -Z /var/lib/docker/
# system_u:object_r:container_var_lib_t:s0 ...

# 容器 volume 标签
docker run -v /data:/data:Z myapp  # 重新标签为容器可访问
docker run -v /data:/data:z myapp  # 共享标签（多个容器可访问）

# 创建自定义 SELinux 策略模块
cat > docker_container.te << 'EOF'
module docker_container 1.0;

require {
    type container_t;
    type sysctl_t;
    class file { read open };
}

# 允许容器读取特定 sysctl
allow container_t sysctl_t:file { read open };
EOF

# 编译和安装策略
checkmodule -M -m -o docker_container.mod docker_container.te
semodule_package -o docker_container.pp -m docker_container.mod
sudo semodule -i docker_container.pp
```

---

### 6. Docker Bench Security

#### 6.1 工具介绍

Docker Bench for Security 是一个脚本，用于检查生产环境中的 Docker 部署是否符合 CIS Docker Benchmark。

```bash
# 运行 Docker Bench Security
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
  -v /etc:/etc:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /usr/lib/systemd:/usr/lib/systemd:ro \
  docker/docker-bench-security

# 输出示例
# [INFO] 1 - Host Configuration
# [WARN] 1.1.1 - Ensure a separate partition for containers has been created
# [PASS] 1.1.2 - Ensure only trusted users are allowed to control Docker daemon
# [WARN] 1.2.1 - Ensure the container host has been hardened
# ...

# 保存报告到文件
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -v /etc:/etc:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /usr/lib/systemd:/usr/lib/systemd:ro \
  docker/docker-bench-security -l /tmp/docker-bench.log
```

#### 6.2 CIS Benchmark 关键检查项

```
┌─────────────────────────────────────────────────────────────┐
│                CIS Docker Benchmark 检查项                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Host Configuration                                      │
│     ├── 1.1 Linux Host Hardening                           │
│     ├── 1.2 Docker Daemon Configuration                     │
│     └── 1.3 Docker Daemon Configuration Files               │
│                                                             │
│  2. Docker Daemon Configuration                             │
│     ├── 2.1 Network Configuration                          │
│     ├── 2.2 Logging                                        │
│     ├── 2.3 Storage                                        │
│     └── 2.4 Runtime                                        │
│                                                             │
│  3. Docker Daemon Configuration Files                       │
│     ├── 3.1 systemd Service File                           │
│     └── 3.2 Docker daemon.json                             │
│                                                             │
│  4. Container Images and Build                              │
│     ├── 4.1 Container User                                 │
│     ├── 4.2 Content Trust                                  │
│     └── 4.3 Container Hardening                            │
│                                                             │
│  5. Container Runtime                                       │
│     ├── 5.1 Runtime Configuration                          │
│     ├── 5.2 Container Network                              │
│     └── 5.3 Container Resources                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 6.3 常见问题修复

```bash
# 1.1.1 - 确保为容器创建独立分区
# 在 /etc/fstab 中添加：
# /dev/sdb1 /var/lib/docker ext4 defaults 0 2

# 1.2.1 - 确保 Docker 版本是最新的
docker version
# 如需更新：
sudo apt-get update && sudo apt-get install docker-ce

# 2.1 - 网络配置
# 限制容器间通信
sudo tee -a /etc/docker/daemon.json << 'EOF'
{
  "icc": false
}
EOF

# 2.2 - 日志配置
sudo tee -a /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

# 2.4 - 运行时配置
sudo tee -a /etc/docker/daemon.json << 'EOF'
{
  "no-new-privileges": true,
  "userland-proxy": false,
  "live-restore": true
}
EOF

# 重启 Docker
sudo systemctl restart docker
```

#### 6.4 安全基线配置模板

```json
{
  "icc": false,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "no-new-privileges": true,
  "userland-proxy": false,
  "live-restore": true,
  "userns-remap": "default",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    },
    "nproc": {
      "Name": "nproc",
      "Hard": 65536,
      "Soft": 65536
    }
  },
  "storage-driver": "overlay2",
  "selinux-enabled": true
}
```

---

### 7. 镜像签名与供应链安全

#### 7.1 Docker Content Trust (DCT)

```bash
# 启用 Content Trust
export DOCKER_CONTENT_TRUST=1

# 推送签名镜像
docker push myregistry/myapp:v1
# 系统会提示创建签名密钥

# 拉取签名镜像
docker pull myregistry/myapp:v1
# 只能拉取签名的镜像

# 查看签名信息
docker trust inspect --pretty myregistry/myapp

# 签名密钥管理
docker trust key generate my-signing-key
docker trust signer add --key my-signing-key my-signer myregistry/myapp

# 撤销签名
docker trust revoke myregistry/myapp:v1
```

#### 7.2 Notary 服务器

```bash
# 部署 Notary 服务器
git clone https://github.com/notaryproject/notary.git
cd notary

# 使用 Docker Compose 部署
docker-compose up -d

# 配置 Docker 使用 Notary
export DOCKER_CONTENT_TRUST_SERVER=https://notary.example.com

# 验证 Notary 服务器
notary -s https://notary.example.com list myregistry/myapp
```

#### 7.3 Cosign 签名（推荐）

```bash
# 安装 cosign
go install github.com/sigstore/cosign/v2/cmd/cosign@latest

# 生成密钥对
cosign generate-key-pair

# 签名镜像
cosign sign --key cosign.key myregistry/myapp:v1

# 验证签名
cosign verify --key cosign.pub myregistry/myapp:v1

# 使用 keyless 签名（OIDC）
cosign sign myregistry/myapp:v1
# 浏览器会打开进行身份验证

# 验证 keyless 签名
cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://accounts.google.com \
  myregistry/myapp:v1
```

#### 7.4 镜像 SBOM（软件物料清单）

```bash
# 使用 syft 生成 SBOM
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  anchore/syft packages myregistry/myapp:v1

# 保存 SBOM
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd):/output \
  anchore/syft packages myregistry/myapp:v1 -o spdx-json > sbom.json

# 使用 cosign 附加 SBOM
cosign attach sbom --sbom sbom.json myregistry/myapp:v1

# 验证 SBOM
cosign verify-attestation --type spdxjson --key cosign.pub myregistry/myapp:v1
```

---

## 💻 实战练习

### 练习 1：创建安全加固的容器

**目标：** 创建一个符合安全基线的 Web 应用容器

```bash
# 1. 创建安全的 Dockerfile
cat > Dockerfile.secure << 'EOF'
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine

# 安装安全更新
RUN apk update && apk upgrade && apk add --no-cache dumb-init

# 创建非 root 用户
RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -s /bin/sh -D appuser

WORKDIR /app

# 从 builder 阶段复制依赖
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --chown=appuser:appgroup . .

# 移除不必要的文件
RUN rm -rf tests docs .git .github

USER appuser

EXPOSE 3000

# 使用 dumb-init 作为 PID 1
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server.js"]
EOF

# 2. 构建镜像
docker build -f Dockerfile.secure -t secure-webapp:v1 .

# 3. 运行安全容器
docker run -d \
  --name secure-webapp \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=50m \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --security-opt no-new-privileges:true \
  --security-opt seccomp=default \
  --memory 256m \
  --cpus 0.5 \
  --restart unless-stopped \
  -p 8080:3000 \
  secure-webapp:v1

# 4. 验证安全配置
docker inspect secure-webapp | jq '.[0].HostConfig | {
  ReadonlyRootfs: .ReadonlyRootfs,
  CapAdd: .CapAdd,
  CapDrop: .CapDrop,
  SecurityOpt: .SecurityOpt,
  Memory: .Memory,
  CpuQuota: .CpuQuota
}'
```

### 练习 2：配置自定义 Seccomp Profile

**目标：** 为特定应用创建最小权限的 seccomp 配置

```bash
# 1. 追踪应用系统调用
docker run --rm --name trace-app \
  --security-opt seccomp=unconfined \
  myapp &

# 获取容器 PID
PID=$(docker inspect --format='{{.State.Pid}}' trace-app)

# 使用 strace 追踪
sudo strace -f -p $PID -e trace=network -o /tmp/trace.log &
sleep 10
kill %1

# 2. 分析系统调用
cat /tmp/trace.log | awk -F'(' '{print $1}' | sort -u | \
  sed 's/^[0-9]* //' | sort -u

# 3. 生成 seccomp profile
cat > app-seccomp.json << 'EOF'
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "bind", "brk", "clock_gettime",
        "close", "connect", "dup", "dup2", "epoll_create", "epoll_ctl",
        "epoll_wait", "execve", "exit", "exit_group", "fcntl", "fstat",
        "futex", "getcwd", "getpid", "getsockname", "getsockopt",
        "ioctl", "listen", "lseek", "mmap", "mprotect", "munmap",
        "nanosleep", "newfstatat", "openat", "pipe", "poll", "prctl",
        "read", "recvfrom", "recvmsg", "rt_sigaction", "rt_sigprocmask",
        "sendmsg", "sendto", "setsockopt", "shutdown", "sigaltstack",
        "socket", "stat", "uname", "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
EOF

# 4. 测试 seccomp profile
docker run --rm --security-opt seccomp=app-seccomp.json myapp
```

### 练习 3：Docker Bench Security 审计

**目标：** 运行安全审计并修复发现的问题

```bash
# 1. 运行 Docker Bench Security
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
  -v /etc:/etc:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /usr/lib/systemd:/usr/lib/systemd:ro \
  docker/docker-bench-security 2>&1 | tee /tmp/bench-report.txt

# 2. 分析报告
echo "=== 警告项 ==="
grep -E "\[WARN\]" /tmp/bench-report.txt | wc -l
echo "=== 通过项 ==="
grep -E "\[PASS\]" /tmp/bench-report.txt | wc -l

# 3. 修复常见问题

# 修复：禁用容器间通信
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "icc": false,
  "no-new-privileges": true,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,
  "userland-proxy": false
}
EOF

sudo systemctl restart docker

# 4. 重新运行审计
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -v /etc:/etc:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  docker/docker-bench-security 2>&1 | grep -E "\[WARN\]" | wc -l
```

---

## 🎯 面试题精选

### 1. Docker 容器与虚拟机在安全性上有什么区别？

**参考答案：**

| 方面 | 容器 | 虚拟机 |
|------|------|--------|
| 隔离级别 | 进程级（Namespace + Cgroup） | 硬件级（Hypervisor） |
| 内核 | 共享宿主机内核 | 独立内核 |
| 攻击面 | 较大（内核漏洞可逃逸） | 较小（需要突破 Hypervisor） |
| 启动开销 | 毫秒级 | 秒到分钟级 |
| 资源占用 | 轻量 | 重量 |

**容器安全风险：**
- 内核漏洞可能导致容器逃逸
- 共享内核的系统调用是攻击面
- 默认以 root 运行存在权限提升风险

**缓解措施：**
- 使用 seccomp/AppArmor/SELinux 限制系统调用
- 非 root 用户运行容器
- 使用 gVisor/Kata Containers 增强隔离

### 2. 解释 Docker 的 seccomp、AppArmor 和 SELinux 的作用和区别

**参考答案：**

```
┌─────────────────────────────────────────────────────────────┐
│                    安全模块对比                              │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ 特性         │ seccomp      │ AppArmor     │ SELinux       │
├──────────────┼──────────────┼──────────────┼───────────────┤
│ 控制对象     │ 系统调用     │ 文件/网络    │ 所有资源      │
│ 粒度         │ 系统调用级   │ 路径级       │ 类型/角色级   │
│ 配置复杂度   │ 中等         │ 简单         │ 复杂          │
│ 默认启用     │ 是(Docker)   │ 是(Ubuntu)   │ 否(CentOS)    │
│ 粒度         │ 细           │ 中           │ 粗            │
│ 性能影响     │ 低           │ 低           │ 中            │
└──────────────┴──────────────┴──────────────┴───────────────┘
```

**使用场景：**
- seccomp：限制容器可调用的系统调用，防止内核漏洞利用
- AppArmor：限制文件访问和网络操作，适合 Ubuntu 环境
- SELinux：强制访问控制，适合 RHEL/CentOS 环境

### 3. 如何实现 Docker 容器的最小权限原则？

**参考答案：**

```bash
# 1. 非 root 用户运行
USER appuser

# 2. 移除所有 capabilities，按需添加
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myapp

# 3. 只读文件系统
docker run --read-only --tmpfs /tmp myapp

# 4. 安全模块限制
docker run \
  --security-opt no-new-privileges:true \
  --security-opt seccomp=default \
  --security-opt apparmor=docker-default \
  myapp

# 5. 资源限制
docker run \
  --memory 256m \
  --cpus 0.5 \
  --pids-limit 100 \
  myapp

# 6. 网络隔离
docker run --network none myapp  # 无网络
docker run --network internal-net myapp  # 内部网络
```

### 4. 什么是容器逃逸？如何防范？

**参考答案：**

**容器逃逸类型：**
1. **内核漏洞利用**：利用内核漏洞突破 namespace 隔离
2. **配置错误**：特权容器、危险的 capabilities
3. **运行时漏洞**：Docker/runc 漏洞
4. **共享卷攻击**：通过挂载的卷访问宿主机

**防范措施：**

```bash
# 1. 避免特权容器
docker run --privileged  # 危险！

# 2. 限制危险 capabilities
docker run --cap-drop=ALL myapp
# 避免添加: SYS_ADMIN, SYS_PTRACE, SYS_RAWIO

# 3. 使用安全模块
docker run --security-opt seccomp=default myapp

# 4. 及时更新
# 更新 Docker
sudo apt-get update && sudo apt-get install docker-ce

# 更新内核
sudo apt-get update && sudo apt-get upgrade linux-image-generic

# 5. 使用 rootless Docker
dockerd-rootless-setuptool.sh install

# 6. 使用更强的隔离
# gVisor (应用内核)
docker run --runtime=runsc myapp

# Kata Containers (轻量级 VM)
docker run --runtime=kata-runtime myapp
```

### 5. Docker Content Trust 如何工作？

**参考答案：**

Docker Content Trust (DCT) 使用 Notary 进行镜像签名和验证：

```
┌─────────────────────────────────────────────────────────────┐
│                Docker Content Trust 流程                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   开发者                    Registry              用户      │
│      │                         │                    │       │
│      │  1. 构建镜像            │                    │       │
│      │─────────────────────────┼────────────────────>       │
│      │                         │                    │       │
│      │  2. 签名 (TUF)          │                    │       │
│      │──────┐                  │                    │       │
│      │      │ 生成签名         │                    │       │
│      │<─────┘                  │                    │       │
│      │                         │                    │       │
│      │  3. 推送 + 签名         │                    │       │
│      │────────────────────────>│                    │       │
│      │                         │                    │       │
│      │                         │  4. 拉取            │       │
│      │                         │<───────────────────│       │
│      │                         │                    │       │
│      │                         │  5. 验证签名        │       │
│      │                         │────────────────────>       │
│      │                         │                    │       │
│      │                         │  6. 返回镜像        │       │
│      │                         │────────────────────>       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**TUF (The Update Framework) 角色：**
- **root**：信任根，签名其他角色
- **targets**：镜像标签到摘要的映射
- **snapshot**：捕获 targets 的当前状态
- **timestamp**：标记仓库的最后更新时间

### 6. 如何扫描 Docker 镜像漏洞？

**参考答案：**

```bash
# 1. Trivy（推荐）
trivy image myapp:latest
trivy image --severity HIGH,CRITICAL myapp:latest
trivy image --format json -o report.json myapp:latest

# 2. Grype
grype myapp:latest
grype myapp:latest --output json > report.json

# 3. Docker Scout
docker scout cves myapp:latest
docker scout recommendations myapp:latest

# 4. Snyk
snyk container test myapp:latest
snyk container monitor myapp:latest

# CI/CD 集成示例（GitHub Actions）
# .github/workflows/security.yml
name: Container Security Scan
on: [push]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
```

### 7. 什么是 user namespace 重映射？有什么作用？

**参考答案：**

User namespace 重映射将容器内的 root (UID 0) 映射为宿主机上的非特权用户：

```bash
# 配置 user namespace 重映射
# 1. 创建映射用户
sudo useradd -r -s /bin/false dockremap

# 2. 配置 subordinate UID/GID
echo "dockremap:100000:65536" | sudo tee -a /etc/subuid
echo "dockremap:100000:65536" | sudo tee -a /etc/subgid

# 3. 启用 Docker userns-remap
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "userns-remap": "default"
}
EOF

sudo systemctl restart docker

# 4. 验证
docker run --rm alpine id
# uid=0(root) gid=0(root)  (容器内)

# 查看宿主机上的实际 UID
ps aux | grep container_process
# 显示为 100000 而非 0
```

**作用：**
- 即使容器逃逸，攻击者也只是宿主机上的非特权用户
- 减少内核攻击面
- 符合最小权限原则

### 8. 如何保护 Docker daemon 的安全？

**参考答案：**

```bash
# 1. 使用 TLS 认证
# 生成 CA 证书
openssl genrsa -aes256 -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem

# 生成服务器证书
openssl genrsa -out server-key.pem 4096
openssl req -subj "/CN=docker.example.com" -sha256 \
  -new -key server-key.pem -out server.csr

# 签署证书
openssl x509 -req -days 365 -sha256 \
  -in server.csr -CA ca.pem -CAkey ca-key.pem -CAcreateserial \
  -out server-cert.pem

# 配置 Docker daemon
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "tls": true,
  "tlscacert": "/etc/docker/ca.pem",
  "tlscert": "/etc/docker/server-cert.pem",
  "tlskey": "/etc/docker/server-key.pem",
  "tlsverify": true
}
EOF

# 2. 限制 Docker socket 访问权限
sudo chmod 660 /var/run/docker.sock
sudo chown root:docker /var/run/docker.sock

# 3. 使用 systemd 限制 Docker 服务
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf << 'EOF'
[Service]
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/docker
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker

# 4. 启用审计日志
sudo auditctl -w /usr/bin/docker -p rwxa -k docker
sudo auditctl -w /var/lib/docker -p rwxa -k docker
sudo auditctl -w /etc/docker -p rwxa -k docker
sudo auditctl -w /var/run/docker.sock -p rwxa -k docker
```

### 9. Docker 安全扫描工具有哪些？如何选择？

**参考答案：**

| 工具 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| Trivy | 快速、免费、支持多格式 | 误报率较高 | CI/CD 集成 |
| Grype | 准确、SBOM 集成 | 社区较小 | 精确扫描 |
| Docker Scout | 官方支持、集成好 | 需要登录 | Docker 生态 |
| Snyk | 修复建议好 | 付费功能多 | 企业环境 |
| Clair | 老牌、稳定 | 配置复杂 | Harbor 集成 |

**选择建议：**
- 个人/小团队：Trivy（免费、快速）
- 企业环境：Snyk 或 Docker Scout（支持、修复建议）
- 已有 Harbor：Clair（原生集成）
- 需要 SBOM：Grype + Syft

### 10. 如何实现 Docker 镜像的供应链安全？

**参考答案：**

```
┌─────────────────────────────────────────────────────────────┐
│                镜像供应链安全流程                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. 基础镜像                                               │
│      ├── 使用官方镜像                                       │
│      ├── 定期更新                                           │
│      └── 扫描漏洞                                           │
│                                                             │
│   2. 构建过程                                               │
│      ├── 多阶段构建                                         │
│      ├── 最小化安装                                         │
│      └── 固定版本                                           │
│                                                             │
│   3. 镜像签名                                               │
│      ├── Cosign 签名                                        │
│      ├── 生成 SBOM                                          │
│      └── 附加签名元数据                                     │
│                                                             │
│   4. 镜像扫描                                               │
│      ├── 漏洞扫描                                           │
│      ├── 配置审计                                           │
│      └── 合规检查                                           │
│                                                             │
│   5. 运行时保护                                             │
│      ├── 只允许签名镜像                                     │
│      ├── 运行时安全策略                                     │
│      └── 异常检测                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**实施步骤：**

```bash
# 1. 启用 Content Trust
export DOCKER_CONTENT_TRUST=1

# 2. 使用 Cosign 签名
cosign sign --key cosign.key registry.example.com/myapp:v1

# 3. 生成 SBOM
syft registry.example.com/myapp:v1 -o spdx-json > sbom.json

# 4. 附加 SBOM
cosign attach sbom --sbom sbom.json registry.example.com/myapp:v1

# 5. 验证签名和 SBOM
cosign verify --key cosign.pub registry.example.com/myapp:v1
cosign verify-attestation --type spdxjson --key cosign.pub \
  registry.example.com/myapp:v1

# 6. CI/CD 策略
# 只部署签名的镜像
if ! cosign verify --key cosign.pub $IMAGE; then
  echo "Image not signed, rejecting deployment"
  exit 1
fi
```

---

## 📚 深入阅读

### 官方文档
- [Docker Security Documentation](https://docs.docker.com/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [Docker Content Trust](https://docs.docker.com/engine/security/trust/)
- [Seccomp Security Profiles](https://docs.docker.com/engine/security/seccomp/)

### 工具资源
- [Docker Bench for Security](https://github.com/docker/docker-bench-security)
- [Trivy](https://github.com/aquasecurity/trivy)
- [Grype](https://github.com/anchore/grype)
- [Cosign](https://github.com/sigstore/cosign)
- [Syft](https://github.com/anchore/syft)

### 最佳实践
- [NIST Container Security Guide](https://csrc.nist.gov/publications/detail/sp/800-190/final)
- [Aqua Security Best Practices](https://blog.aquasec.com/docker-security-best-practices)
- [Snyk Docker Security](https://snyk.io/blog/10-docker-image-security-best-practices/)

---

## ✅ 自检清单

### 基础安全配置
- [ ] 容器以非 root 用户运行
- [ ] 移除不必要的 Linux capabilities
- [ ] 启用只读文件系统
- [ ] 设置 no-new-privileges
- [ ] 配置 seccomp profile

### 高级安全配置
- [ ] 配置 AppArmor 或 SELinux
- [ ] 启用 user namespace 重映射
- [ ] 配置资源限制（CPU、内存、PID）
- [ ] 隔离容器网络

### 镜像安全
- [ ] 使用官方或可信基础镜像
- [ ] 定期扫描镜像漏洞
- [ ] 启用 Docker Content Trust
- [ ] 生成并验证 SBOM

### 运维安全
- [ ] 运行 Docker Bench Security 审计
- [ ] 配置审计日志
- [ ] 限制 Docker socket 访问
- [ ] 定期更新 Docker 和内核

### 供应链安全
- [ ] 镜像签名（Cosign/Notary）
- [ ] CI/CD 安全扫描集成
- [ ] 只部署签名镜像
- [ ] 监控新发现的漏洞

---

## 🔧 常见问题与故障排查

### 问题 1：容器无法写入文件

```bash
# 错误信息
# Error: EACCES: permission denied, open '/app/data/file.txt'

# 原因：只读文件系统或权限不足

# 解决方案 1：挂载可写卷
docker run --read-only \
  --volume app-data:/app/data:rw \
  myapp

# 解决方案 2：使用 tmpfs
docker run --read-only \
  --tmpfs /app/data:rw,size=100m \
  myapp

# 解决方案 3：调整文件权限
RUN chown -R appuser:appgroup /app/data
```

### 问题 2：容器被 seccomp 阻止

```bash
# 错误信息
# OCI runtime exec failed: unable to start container process:
# seccomp: filter load: operation not permitted: unknown

# 解决方案 1：检查系统调用需求
strace -f -e trace=process docker exec container_name command

# 解决方案 2：自定义 seccomp profile
# 添加所需的系统调用到 profile

# 解决方案 3：临时禁用（仅用于调试）
docker run --security-opt seccomp=unconfined myapp
```

### 问题 3：AppArmor 阻止容器访问

```bash
# 错误信息
# apparmor="DENIED" operation="open" profile="docker-custom"

# 查看 AppArmor 日志
sudo dmesg | grep apparmor
sudo journalctl -k | grep apparmor

# 解决方案 1：更新 AppArmor profile
# 添加允许的路径和操作

# 解决方案 2：切换到 complain 模式
sudo aa-complain /etc/apparmor.d/docker-custom

# 解决方案 3：禁用 AppArmor（不推荐）
docker run --security-opt apparmor=unconfined myapp
```

---

**下一阶段：** Day 87 将学习 Docker 网络进阶，包括 macvlan、VXLAN 和容器网络方案。
