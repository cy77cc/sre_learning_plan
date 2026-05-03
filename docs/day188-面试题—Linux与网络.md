# Day 188: 面试题 — Linux 与网络（30 道高频题 + 详细解析）

> 📅 日期：2026-05-02
> 📖 学习主题：Linux 与网络高频面试题
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 1-30（Linux 基础）、Day 31-45（网络基础）

---

## 🎯 学习目标

完成 Day 188 的学习后，你应该能够：

- 流利回答 30 道 Linux 与网络高频面试题
- 掌握面试中展示技术深度的表达技巧
- 能够将理论知识与实际工作经验结合
- 应对开放性和场景类面试题

---

## 📖 核心知识点

### 第一部分：Linux 系统基础（10 题）

---

#### 题目 1：请描述 Linux 系统的启动流程

**难度**：⭐⭐⭐

**详细解析**：

Linux 启动流程是面试高频题，考察对系统底层的理解。

```
完整启动流程：

1. BIOS/UEFI 阶段
   - POST（Power-On Self-Test）硬件自检
   - 选择启动设备（硬盘/网络/USB）
   - 加载 Bootloader

2. Bootloader 阶段（GRUB2）
   - 读取 /boot/grub2/grub.cfg 配置
   - 显示启动菜单（多内核选择）
   - 加载内核镜像（vmlinuz）和 initramfs

3. 内核初始化阶段
   - 解压内核镜像，初始化内核子系统
   - 挂载 initramfs（临时根文件系统）
   - 加载必要的内核模块（驱动）
   - 挂载真正的根文件系统
   - 启动 PID 1 进程（systemd）

4. systemd 初始化阶段
   - 读取 /etc/systemd/system/default.target 确定运行级别
   - 并行启动各个 target 和 service
   - 执行 /etc/rc.local（兼容 SysVinit）
   - 启动 getty/登录管理器

5. 用户登录阶段
   - 显示登录提示符
   - 验证用户名密码
   - 加载用户环境（/etc/profile, ~/.bashrc）
```

**面试加分点**：

```
深入理解：
- initramfs 的作用：提供临时根文件系统，加载存储驱动
- systemd vs SysVinit：systemd 支持并行启动、依赖管理、socket 激活
- 查看启动耗时：systemd-analyze blame
- 内核参数调整：/proc/cmdline, /etc/default/grub
```

---

#### 题目 2：Linux 中查看系统负载的命令有哪些？如何判断系统是否过载？

**难度**：⭐⭐⭐

**详细解析**：

```
核心命令：

1. uptime / w
   $ uptime
    14:30:00 up 120 days, 3:45, 2 users, load average: 2.50, 1.80, 1.20
                                    1分钟  5分钟   15分钟

2. top / htop
   - 查看 CPU、内存、进程实时状态
   - 按 1 查看每个 CPU 核心的使用率

3. vmstat
   $ vmstat 1 5
   procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
    r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa
    2  0      0 512000  64000 2048000    0    0     5    20  500 1000 15  5 78  2

4. mpstat（CPU 详细信息）
   $ mpstat -P ALL 1

5. iostat（IO 详细信息）
   $ iostat -xz 1

6. sar（历史数据）
   $ sar -u 1 10    # CPU 使用率
   $ sar -r 1 10    # 内存使用率
   $ sar -d 1 10    # 磁盘 IO
```

**判断系统是否过载的方法**：

```
Load Average 解读：
- Load < CPU 核心数：系统空闲
- Load = CPU 核心数：系统刚好满载
- Load > CPU 核心数：系统过载，有进程在等待

判断维度：
1. CPU 过载：
   - us（用户态）> 70%：应用计算密集
   - sy（内核态）> 30%：系统调用过多，可能是 IO 问题
   - wa（IO 等待）> 20%：磁盘 IO 瓶颈
   - id（空闲）< 10%：CPU 资源紧张

2. 内存不足：
   - free 内存接近 0
   - swap 使用量持续增长（si/so > 0）
   - OOM Killer 日志（dmesg | grep -i oom）

3. IO 瓶颈：
   - await > 10ms（SSD）或 > 20ms（HDD）
   - %util > 90%：磁盘饱和
   - 队列长度（avgqu-sz）> 2
```

---

#### 题目 3：解释 Linux 文件权限，chmod 755 是什么意思？

**难度**：⭐⭐

**详细解析**：

```
Linux 文件权限模型：

权限类型：
r (read)    = 4  读权限
w (write)   = 2  写权限
x (execute) = 1  执行权限

权限分组：
所有者(u)  |  所属组(g)  |  其他人(o)
  rwx      |    rwx      |    rwx
  7        |     5       |     5

chmod 755 分解：
- 所有者：7 = 4+2+1 = rwx（读+写+执行）
- 所属组：5 = 4+0+1 = r-x（读+执行）
- 其他人：5 = 4+0+1 = r-x（读+执行）

常见权限组合：
- 755：目录默认权限，所有者可读写执行，其他人可读和执行
- 644：文件默认权限，所有者可读写，其他人只读
- 700：私有目录，只有所有者可访问
- 600：私有文件，如 SSH 密钥
- 4755：SUID 权限，执行时以文件所有者身份运行
```

**特殊权限位**：

```
SUID (4)：执行时以文件所有者身份运行
  例：/usr/bin/passwd（普通用户修改密码时需要 root 权限）
  $ ls -l /usr/bin/passwd
  -rwsr-xr-x 1 root root 68208 ... /usr/bin/passwd

SGID (2)：执行时以文件所属组身份运行；目录下新建文件继承目录的组
  例：/usr/bin/wall

Sticky Bit (1)：目录中只有文件所有者才能删除自己的文件
  例：/tmp 目录
  $ ls -ld /tmp
  drwxrwxrwt 10 root root 4096 ... /tmp
```

---

#### 题目 4：什么是 inode？inode 耗尽了怎么办？

**难度**：⭐⭐⭐

**详细解析**：

```
inode（索引节点）是文件系统中存储文件元数据的数据结构。

inode 存储的信息：
- 文件类型（普通文件、目录、链接等）
- 文件权限（rwx）
- 文件所有者（UID/GID）
- 文件大小
- 时间戳（创建、修改、访问）
- 数据块指针（指向实际数据存储位置）
- 链接数

注意：inode 不存储文件名！文件名存储在目录的数据块中。

查看 inode 信息：
$ df -i                    # 查看各分区 inode 使用情况
$ stat filename            # 查看单个文件的 inode 信息
$ ls -i filename           # 查看文件的 inode 号
```

**inode 耗尽的场景和解决**：

```
场景：df -h 显示磁盘空间充足，但 df -i 显示 inode 使用率 100%

常见原因：
- 大量小文件（如邮件队列、临时文件、session 文件）
- 程序 bug 产生大量零字节文件
- /tmp 或 /var/spool 下堆积大量文件

排查方法：
# 找到 inode 使用最多的目录
$ df -i
$ find / -xdev -printf '%h\n' | sort | uniq -c | sort -rn | head -20

# 找到某个目录下的文件数量
$ ls -la /var/spool/clientmqueue/ | wc -l

解决方法：
1. 删除不需要的小文件
   $ find /var/spool/clientmqueue -type f -mtime +7 -delete

2. 如果是邮件队列问题，修复邮件配置
3. 如果经常遇到 inode 耗尽，重新格式化磁盘时增加 inode 数量
   $ mkfs.ext4 -N 10000000 /dev/sdb1

预防措施：
- 监控 inode 使用率（Prometheus node_exporter 已支持）
- 定期清理临时文件
- 对于大量小文件场景，考虑使用 XFS 文件系统（动态分配 inode）
```

---

#### 题目 5：解释 Linux 进程的几种状态

**难度**：⭐⭐⭐

**详细解析**：

```
Linux 进程状态（ps/stat 输出）：

R (Running/Runnable)：
  正在运行或在运行队列中等待 CPU 时间片
  - R 状态表示正在 CPU 上执行
  - R+ 表示前台运行

S (Interruptible Sleep)：
  可中断睡眠，等待事件完成
  - 大部分时间进程都在这个状态
  - 等待 IO、等待信号、等待锁
  - 可以被信号唤醒

D (Uninterruptible Sleep)：
  不可中断睡眠，通常在等待 IO
  - 不能被信号中断
  - kill -9 也无法杀死
  - 常见于磁盘 IO 问题
  - 如果大量 D 状态进程，说明 IO 有问题

Z (Zombie)：
  僵尸进程，子进程已退出但父进程未回收
  - 不占用资源，但占用 PID
  - 大量僵尸进程可能是父进程 bug
  - 解决：杀死父进程或修复父进程代码

T (Stopped)：
  进程被信号停止
  - SIGSTOP 或 Ctrl+Z 触发
  - SIGCONT 恢复运行

t (Traced)：
  进程被调试器跟踪
  - GDB 调试时出现

查看进程状态：
$ ps aux
$ ps -eo pid,ppid,stat,cmd
$ cat /proc/<pid>/status
```

---

#### 题目 6：如何排查 Linux 服务器 CPU 使用率过高的问题？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
排查步骤（标准化流程）：

Step 1：确认 CPU 使用情况
$ top                          # 查看整体 CPU 使用率和进程列表
$ mpstat -P ALL 1              # 查看每个核心的使用率
$ uptime                       # 查看 load average

Step 2：定位占用 CPU 的进程
$ ps aux --sort=-%cpu | head -10    # 按 CPU 使用率排序
$ top -Hp <pid>                     # 查看进程内各线程的 CPU 使用

Step 3：分析进程在做什么
$ strace -cp <pid>                  # 统计系统调用耗时
$ strace -p <pid> -e trace=all      # 跟踪系统调用
$ perf top -p <pid>                 # 查看热点函数
$ perf record -p <pid> -g -- sleep 30  # 采样 30 秒

Step 4：如果是 Java 应用
$ jstack <pid>                      # 线程 dump
$ jstat -gcutil <pid> 1000          # GC 统计
$ arthas thread -n 3                # 阿里 Arthas 工具

Step 5：如果是 Go 应用
$ curl http://localhost:6060/debug/pprof/profile?seconds=30 > cpu.prof
$ go tool pprof cpu.prof

常见原因：
- 死循环或无限递归
- 正则表达式回溯（ReDoS）
- GC 频繁（Java/Go）
- 密集计算任务
- 锁竞争导致的 CPU 空转
```

---

#### 题目 7：解释 Linux 中的文件描述符（File Descriptor）

**难度**：⭐⭐⭐

**详细解析**：

```
文件描述符（FD）是操作系统为每个打开的文件分配的非负整数。

标准文件描述符：
- 0 - stdin（标准输入）
- 1 - stdout（标准输出）
- 2 - stderr（标准错误）

查看文件描述符：
$ ls -l /proc/<pid>/fd           # 查看进程打开的所有 FD
$ lsof -p <pid>                  # 列出进程打开的文件
$ cat /proc/<pid>/limits         # 查看进程的 FD 限制

FD 限制：
$ ulimit -n                      # 当前用户的 FD 限制
$ cat /proc/sys/fs/file-nr       # 系统级 FD 使用情况

常见问题：Too many open files
原因：程序打开文件过多未关闭，或 FD 限制太低

解决方法：
1. 临时修改
   $ ulimit -n 65535

2. 永久修改
   /etc/security/limits.conf:
   * soft nofile 65535
   * hard nofile 65535

3. 系统级修改
   /etc/sysctl.conf:
   fs.file-max = 2097152
   $ sysctl -p

4. Systemd 服务修改
   [Service]
   LimitNOFILE=65535
```

---

#### 题目 8：什么是 Linux 的 cgroup？在容器中如何使用？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
cgroup（Control Groups）是 Linux 内核提供的资源限制机制。

cgroup 可以限制的资源：
- CPU：限制 CPU 使用份额、绑定 CPU 核心
- 内存：限制内存使用量、OOM 策略
- IO：限制磁盘读写带宽和 IOPS
- 网络：网络带宽限制（通过 tc 配合）
- PID：限制进程数量

cgroup v1 vs v2：
- v1：每个资源类型独立的层级树，配置复杂
- v2：统一层级树，配置更简洁，功能更强

查看 cgroup：
$ cat /proc/self/cgroup           # 当前进程所属的 cgroup
$ systemd-cgls                    # 查看 cgroup 树
$ systemd-cgtop                   # 类似 top 的 cgroup 监控

Docker 容器中的 cgroup：
$ docker inspect <container> | grep -i cgroup
$ cat /sys/fs/cgroup/memory/docker/<container-id>/memory.limit_in_bytes

Kubernetes 中的 cgroup：
# Pod 的资源限制会转化为 cgroup 配置
resources:
  requests:
    cpu: "250m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "256Mi"

# 对应的 cgroup 配置：
# cpu.cfs_quota_us = 50000 (500m = 0.5 core)
# memory.limit_in_bytes = 268435456 (256Mi)
```

---

#### 题目 9：解释 Linux 中的信号（Signal）机制

**难度**：⭐⭐⭐

**详细解析**：

```
信号是进程间通信（IPC）的一种方式，用于通知进程发生了某个事件。

常用信号：
SIGHUP  (1)   终端挂起或控制进程终止（常用于让服务重新加载配置）
SIGINT  (2)   键盘中断（Ctrl+C）
SIGQUIT (3)   键盘退出（Ctrl+\）
SIGKILL (9)   强制杀死进程（不可捕获、不可忽略）
SIGSEGV (11)  段错误（非法内存访问）
SIGTERM (15)  终止进程（默认的 kill 信号，可被捕获）
SIGCHLD (17)  子进程状态改变
SIGSTOP (19)  暂停进程（不可捕获）
SIGCONT (18)  继续执行暂停的进程
SIGUSR1 (10)  用户自定义信号 1
SIGUSR2 (12)  用户自定义信号 2

发送信号：
$ kill -<signal> <pid>
$ kill -9 <pid>                  # 强制杀死
$ killall -HUP nginx             # 向所有 nginx 进程发送 HUP
$ pkill -f "python app.py"       # 按进程名匹配

SRE 面试重点：
- 为什么 kill -9 要慎用？
  - 进程没有机会做清理操作
  - 可能导致数据不一致
  - 应该先尝试 kill (SIGTERM)，等待一段时间后再 kill -9

- Nginx 信号管理：
  - nginx -s reload -> 发送 SIGHUP -> 优雅重新加载配置
  - nginx -s quit  -> 发送 SIGQUIT -> 优雅关闭
  - nginx -s stop  -> 发送 SIGTERM -> 快速关闭

- 优雅关闭（Graceful Shutdown）：
  - 停止接受新请求
  - 等待现有请求处理完成
  - 关闭连接、释放资源
  - 最后退出进程
```

---

#### 题目 10：解释 Linux 中的 namespaces 和它们在容器中的作用

**难度**：⭐⭐⭐⭐

**详细解析**：

```
Namespace 是 Linux 内核提供的资源隔离机制，是容器技术的基石。

8 种 Namespace：

1. PID Namespace
   - 隔离进程 ID
   - 容器内 PID 从 1 开始
   - 容器内看不到宿主机的进程

2. Network Namespace
   - 隔离网络栈（IP、端口、路由表、防火墙规则）
   - 每个容器有独立的网络接口
   - Docker 默认使用 veth pair 连接容器和宿主机

3. Mount Namespace
   - 隔离文件系统挂载点
   - 容器有自己的根文件系统
   - 实现容器的分层镜像（UnionFS）

4. UTS Namespace
   - 隔离主机名和域名
   - 容器可以有自己的 hostname

5. IPC Namespace
   - 隔离进程间通信资源
   - 共享内存、信号量、消息队列

6. User Namespace
   - 隔离用户和组 ID
   - 容器内 root 映射为宿主机普通用户

7. Cgroup Namespace
   - 隔离 cgroup 根目录
   - 容器内看不到宿主机的 cgroup 层级

8. Time Namespace（Linux 5.6+）
   - 隔离系统时钟

查看 Namespace：
$ ls -la /proc/<pid>/ns/
$ nsenter -t <pid> -n             # 进入进程的网络 namespace
$ unshare --pid --fork bash       # 创建新的 PID namespace
```

---

### 第二部分：网络基础（10 题）

---

#### 题目 11：请描述 TCP 三次握手和四次挥手的过程

**难度**：⭐⭐⭐

**详细解析**：

```
三次握手（建立连接）：

Client                    Server
  |                         |
  |--- SYN (seq=x) -------->|  第 1 次：客户端发送 SYN
  |                         |
  |<-- SYN+ACK (seq=y,      |  第 2 次：服务端回复 SYN+ACK
  |    ack=x+1) ------------|
  |                         |
  |--- ACK (ack=y+1) ------>|  第 3 次：客户端发送 ACK
  |                         |
  |    连接建立              |

为什么需要三次？
- 两次不够：服务端无法确认客户端收到了 SYN+ACK
- 防止历史重复连接：旧的 SYN 报文到达服务端，三次握手可以让客户端
  发送 RST 拒绝这个过期连接

四次挥手（关闭连接）：

Client                    Server
  |                         |
  |--- FIN (seq=u) -------->|  第 1 次：客户端发送 FIN
  |                         |
  |<-- ACK (ack=u+1) -------|  第 2 次：服务端回复 ACK
  |                         |  （此时服务端可能还有数据要发送）
  |<-- FIN (seq=w) ---------|  第 3 次：服务端发送 FIN
  |                         |
  |--- ACK (ack=w+1) ------>|  第 4 次：客户端发送 ACK
  |                         |
  |  TIME_WAIT (2MSL)       |
  |    连接关闭              |

为什么需要四次？
- TCP 是全双工通信，每个方向需要单独关闭
- 服务端收到 FIN 后可能还有数据要发送，不能立即关闭

TIME_WAIT 状态：
- 持续 2MSL（Maximum Segment Lifetime，通常 60 秒）
- 作用 1：确保最后的 ACK 能到达服务端
- 作用 2：让旧连接的报文在网络中过期

TIME_WAIT 过多的处理：
$ sysctl net.ipv4.tcp_tw_reuse=1         # 允许复用 TIME_WAIT 连接
$ sysctl net.ipv4.tcp_fin_timeout=30     # 缩短 FIN_WAIT_2 超时
```

---

#### 题目 12：HTTP 和 HTTPS 有什么区别？HTTPS 的握手过程是什么？

**难度**：⭐⭐⭐

**详细解析**：

```
HTTP vs HTTPS：

| 特性     | HTTP         | HTTPS              |
|---------|--------------|---------------------|
| 端口     | 80           | 443                 |
| 加密     | 明文传输      | SSL/TLS 加密        |
| 证书     | 不需要        | 需要 CA 签发的证书   |
| 性能     | 快           | 略慢（握手开销）     |
| SEO      | 不加分        | 搜索引擎优先收录     |

HTTPS 握手过程（TLS 1.2）：

Client                           Server
  |                                |
  |--- ClientHello --------------->|  发送支持的加密套件、随机数
  |                                |
  |<-- ServerHello ----------------|  选择加密套件、随机数
  |<-- Certificate ----------------|  发送服务器证书
  |<-- ServerKeyExchange ----------|  密钥交换参数
  |<-- ServerHelloDone ------------|
  |                                |
  |--- ClientKeyExchange --------->|  客户端密钥交换
  |--- ChangeCipherSpec ---------->|  切换到加密通信
  |--- Finished ------------------>|  验证握手完整性
  |                                |
  |<-- ChangeCipherSpec -----------|  切换到加密通信
  |<-- Finished -------------------|  验证握手完整性
  |                                |
  |    加密数据传输                 |

TLS 1.3 改进：
- 握手从 2-RTT 降至 1-RTT
- 0-RTT 恢复模式（有安全风险）
- 移除不安全的加密算法
- 更强的安全性
```

---

#### 题目 13：DNS 解析的完整流程是什么？

**难度**：⭐⭐⭐

**详细解析**：

```
DNS 解析流程（以访问 www.example.com 为例）：

1. 浏览器缓存
   - 浏览器先检查自身 DNS 缓存
   - Chrome: chrome://net-internals/#dns

2. 操作系统缓存
   - 检查 /etc/hosts 文件
   - 检查系统 DNS 缓存（systemd-resolved / nscd）

3. 本地 DNS 服务器（递归解析器）
   - 向配置的 DNS 服务器发送请求（如 8.8.8.8）
   - 本地 DNS 服务器负责递归查询

4. 根域名服务器（.）
   - 全球 13 组根服务器（A-M）
   - 返回 .com 顶级域名服务器地址

5. 顶级域名服务器（.com）
   - 返回 example.com 权威域名服务器地址

6. 权威域名服务器（example.com）
   - 返回 www.example.com 的 IP 地址

7. 本地 DNS 服务器缓存结果并返回给客户端

DNS 记录类型：
A      - IPv4 地址
AAAA   - IPv6 地址
CNAME  - 别名记录
MX     - 邮件交换记录
NS     - 域名服务器记录
TXT    - 文本记录（SPF、DKIM、验证）
SRV    - 服务记录
SOA    - 权威记录起始

DNS 排查命令：
$ dig www.example.com            # 查询 DNS 记录
$ dig +trace www.example.com     # 追踪完整解析路径
$ nslookup www.example.com 8.8.8.8  # 指定 DNS 服务器查询
$ host www.example.com           # 简单查询
```

---

#### 题目 14：什么是 TCP 的拥塞控制？常见的拥塞控制算法有哪些？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
拥塞控制是 TCP 防止网络拥塞的机制，通过控制发送速率避免网络过载。

核心概念：
- 拥塞窗口（cwnd）：发送方维护的窗口大小
- 慢启动阈值（ssthresh）：慢启动和拥塞避免的分界点
- 发送窗口 = min(cwnd, 接收窗口 rwnd)

四个阶段：

1. 慢启动（Slow Start）
   - cwnd 从 1 MSS 开始
   - 每收到一个 ACK，cwnd 增加 1 MSS
   - 指数增长：1 -> 2 -> 4 -> 8 -> 16...
   - 达到 ssthresh 时进入拥塞避免

2. 拥塞避免（Congestion Avoidance）
   - cwnd 每个 RTT 增加 1 MSS
   - 线性增长
   - 检测到丢包时进入快速恢复或超时重传

3. 快速重传（Fast Retransmit）
   - 收到 3 个重复 ACK 时立即重传
   - 不等待超时

4. 快速恢复（Fast Recovery）
   - ssthresh = cwnd / 2
   - cwnd = ssthresh + 3
   - 进入拥塞避免阶段

常见拥塞控制算法：

Reno：经典的拥塞控制算法
  - 慢启动 + 拥塞避免 + 快速重传 + 快速恢复

Cubic（Linux 默认）：
  - 使用三次函数计算 cwnd
  - 更适合高带宽网络
  - 更好的公平性

BBR（Google）：
  - 基于带宽和 RTT 的模型
  - 不依赖丢包作为拥塞信号
  - 在高延迟和丢包环境下表现更好
  - 适合跨国网络和视频传输

查看和配置：
$ sysctl net.ipv4.tcp_congestion_control    # 查看当前算法
$ sysctl net.ipv4.tcp_available_congestion_control  # 可用算法
$ sysctl -w net.ipv4.tcp_congestion_control=bbr     # 切换到 BBR
```

---

#### 题目 15：解释 OSI 七层模型和 TCP/IP 四层模型

**难度**：⭐⭐

**详细解析**：

```
OSI 七层模型 vs TCP/IP 四层模型：

+---------------+--------------+----------------------------+
| OSI 模型       | TCP/IP 模型   | 协议/技术                   |
+---------------+--------------+----------------------------+
| 7. 应用层      |              | HTTP, HTTPS, FTP, DNS,     |
|               |              | SMTP, SSH, DHCP            |
+---------------+ 4. 应用层     |                            |
| 6. 表示层      |              | SSL/TLS, JPEG, ASCII       |
+---------------+              |                            |
| 5. 会话层      |              | NetBIOS, RPC               |
+---------------+--------------+----------------------------+
| 4. 传输层      | 3. 传输层     | TCP, UDP                   |
+---------------+--------------+----------------------------+
| 3. 网络层      | 2. 网际层     | IP, ICMP, ARP, OSPF, BGP  |
+---------------+--------------+----------------------------+
| 2. 数据链路层  | 1. 网络接口层 | Ethernet, Wi-Fi, PPP       |
+---------------+              |                            |
| 1. 物理层      |              | 光纤、双绞线、无线电波       |
+---------------+--------------+----------------------------+

数据封装过程：
应用层数据 -> [TCP/UDP 头 + 数据] -> [IP 头 + TCP 头 + 数据] -> [帧头 + IP 头 + TCP 头 + 数据 + 帧尾]

每层的作用：
- 应用层：为应用程序提供网络服务
- 传输层：提供端到端的可靠传输（TCP）或不可靠传输（UDP）
- 网络层：路由和寻址（IP 地址）
- 链路层：相邻节点之间的数据传输（MAC 地址）

SRE 面试技巧：
- 不需要死记硬背七层名称，理解每层的作用更重要
- 重点理解数据在各层的封装和解封装过程
- 能举例说明每层的协议即可
```

---

#### 题目 16：如何排查网络连接问题？

**难度**：⭐⭐⭐⭐

**详细解析**：

```
网络排查标准化流程（自底向上）：

Step 1：物理层检查
$ ip link show                     # 检查网卡状态（UP/DOWN）
$ ethtool eth0                     # 检查网卡连接状态、速度
$ dmesg | grep -i eth              # 检查网卡驱动日志

Step 2：数据链路层检查
$ ip addr show                     # 检查 IP 地址配置
$ arp -n                           # 检查 ARP 表
$ bridge link show                 # 检查网桥配置（Docker/K8s）

Step 3：网络层检查
$ ping <目标IP>                    # 测试 IP 连通性
$ ping -c 3 -W 2 8.8.8.8          # 指定次数和超时
$ ip route show                    # 检查路由表
$ traceroute <目标IP>              # 追踪路由路径
$ mtr <目标IP>                     # 实时路由追踪（结合 ping + traceroute）

Step 4：传输层检查
$ ss -tlnp                         # 查看监听的 TCP 端口
$ ss -s                            # 查看连接统计
$ telnet <IP> <端口>               # 测试端口连通性
$ nc -zv <IP> <端口>               # 更好的端口测试工具
$ nmap -p <端口> <IP>              # 端口扫描

Step 5：应用层检查
$ curl -v http://<URL>             # HTTP 请求详细信息
$ dig <域名>                       # DNS 解析
$ openssl s_client -connect <host>:443  # TLS 连接测试

Step 6：抓包分析
$ tcpdump -i eth0 host <IP>        # 抓取指定主机的包
$ tcpdump -i eth0 port 80          # 抓取指定端口的包
$ tcpdump -i eth0 -w capture.pcap  # 保存为 pcap 文件
$ wireshark capture.pcap           # 使用 Wireshark 分析

常用网络排查组合拳：
$ ping -> telnet -> curl -> tcpdump
```

---

#### 题目 17：什么是 NAT？Docker 的网络模式有哪些？

**难度**：⭐⭐⭐

**详细解析**：

```
NAT（Network Address Translation）网络地址转换：

NAT 类型：
1. SNAT（Source NAT）：修改源 IP 地址
   - 场景：内网服务器访问外网
   - iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE

2. DNAT（Destination NAT）：修改目标 IP 地址
   - 场景：外网访问内网服务器（端口映射）
   - iptables -t nat -A PREROUTING -p tcp --dport 80 -j DNAT --to 10.0.0.1:8080

3. PAT（Port Address Transport）：端口地址转换
   - 多个内网 IP 共用一个外网 IP
   - 通过不同端口号区分

Docker 网络模式：

1. bridge（默认）
   - 容器有独立的 Network Namespace
   - 通过 docker0 网桥与宿主机通信
   - 容器之间可以互相访问
   - 端口映射：-p 8080:80

2. host
   - 容器与宿主机共享 Network Namespace
   - 容器直接使用宿主机的 IP 和端口
   - 性能最好，但有端口冲突风险

3. none
   - 容器没有网络
   - 用于安全隔离场景

4. overlay
   - 跨主机容器通信
   - Docker Swarm 和 Kubernetes 使用

5. macvlan
   - 容器有独立的 MAC 地址
   - 像物理机一样直接接入网络

Kubernetes 网络模型：
- 每个 Pod 有独立 IP
- 所有 Pod 可以直接互相通信（不需要 NAT）
- Node 上的进程可以直接访问 Pod
- Pod 看到的自己的 IP 就是其他 Pod 看到的它的 IP
```

---

#### 题目 18：什么是负载均衡？L4 和 L7 负载均衡有什么区别？

**难度**：⭐⭐⭐

**详细解析**：

```
负载均衡（Load Balancing）是将请求分发到多个服务器的技术。

L4 负载均衡（传输层）：
- 工作在 TCP/UDP 层
- 基于 IP + 端口进行转发
- 不解析应用层内容
- 性能高，延迟低
- 代表：LVS、HAProxy（TCP 模式）、Nginx（stream 模块）

L7 负载均衡（应用层）：
- 工作在 HTTP/HTTPS 层
- 可以解析 HTTP 头、URL、Cookie 等
- 支持 URL 路径分流、Header 改写、SSL 终止
- 功能丰富，但性能略低
- 代表：Nginx、HAProxy（HTTP 模式）、Envoy、Traefik

常见负载均衡算法：
1. 轮询（Round Robin）：按顺序依次分发
2. 加权轮询（Weighted RR）：按权重分发
3. 最少连接（Least Connections）：发给连接数最少的服务器
4. IP Hash：同一 IP 的请求发给同一服务器（会话保持）
5. 一致性哈希：分布式缓存场景常用

Nginx 负载均衡配置示例：
upstream backend {
    least_conn;                          # 最少连接算法
    server 10.0.0.1:8080 weight=3;       # 权重 3
    server 10.0.0.2:8080 weight=2;       # 权重 2
    server 10.0.0.3:8080 backup;         # 备用服务器
    keepalive 32;                        # 连接池
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

#### 题目 19：解释 Linux 中的 iptables/nftables 防火墙

**难度**：⭐⭐⭐⭐

**详细解析**：

```
iptables 是 Linux 传统的防火墙工具，基于 netfilter 框架。

iptables 四表五链：

四表（按优先级排列）：
1. raw 表：连接跟踪（conntrack）豁免
2. mangle 表：修改数据包（TTL、TOS 等）
3. nat 表：网络地址转换
4. filter 表：过滤数据包（默认表）

五链：
1. PREROUTING：数据包进入路由决策之前
2. INPUT：数据包目的为本机
3. FORWARD：数据包需要转发
4. OUTPUT：本机产生的数据包
5. POSTROUTING：数据包离开路由决策之后

表和链的关系：
- raw：PREROUTING, OUTPUT
- mangle：所有 5 个链
- nat：PREROUTING, INPUT, OUTPUT, POSTROUTING
- filter：INPUT, FORWARD, OUTPUT

常见操作：
# 查看规则
$ iptables -L -n -v
$ iptables -t nat -L -n -v

# 允许 SSH
$ iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许 HTTP/HTTPS
$ iptables -A INPUT -p tcp -m multiport --dports 80,443 -j ACCEPT

# 禁止某个 IP
$ iptables -A INPUT -s 192.168.1.100 -j DROP

# 端口转发
$ iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080

# 保存规则
$ iptables-save > /etc/iptables/rules.v4

nftables（iptables 的继任者）：
- Linux 3.13 引入，CentOS 8+ / Debian 10+ 默认使用
- 语法更简洁，性能更好
- 统一了 iptables、ip6tables、arptables、ebtables
```

---

#### 题目 20：什么是 CDN？CDN 的工作原理是什么？

**难度**：⭐⭐

**详细解析**：

```
CDN（Content Delivery Network）内容分发网络。

CDN 的核心思想：
将内容缓存到离用户最近的节点，减少网络延迟，提高访问速度。

工作原理：
1. 用户访问 www.example.com
2. DNS 解析时，CDN 的 DNS 服务器根据用户 IP 返回最近的边缘节点
3. 用户从边缘节点获取内容
4. 如果边缘节点没有缓存，回源站获取并缓存

CDN 的关键技术：
- DNS 智能解析：根据用户 IP 返回最近的节点
- 缓存策略：静态资源缓存（图片、CSS、JS、视频）
- 回源策略：缓存未命中时从源站获取
- 负载均衡：多个边缘节点之间的负载分配
- 安全防护：DDoS 防护、WAF、CC 防护

CDN 缓存配置（Nginx）：
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 30d;                    # 缓存 30 天
    add_header Cache-Control "public, immutable";
}

CDN 排查：
$ curl -I https://www.example.com/image.jpg
# 查看响应头中的 CDN 相关字段
# X-Cache: HIT（命中缓存）/ MISS（未命中）
# X-Cdn-Provider: CloudFlare/AWS CloudFront/阿里云 CDN

SRE 关注点：
- CDN 命中率监控
- 回源带宽成本
- 缓存刷新策略
- 多 CDN 切换（故障转移）
```

---

### 第三部分：场景题和故障排查题（10 题）

---

#### 题目 21：服务器 SSH 连不上，如何排查？

**难度**：⭐⭐⭐⭐

**场景**：凌晨 3 点，你收到告警说某台服务器无法 SSH 登录，需要紧急处理。

```
排查思路：

Step 1：确认问题范围
- 是所有服务器都连不上，还是只有一台？
- 是所有人都连不上，还是只有你？
- 服务器是否在监控中？监控指标是否正常？

Step 2：网络层排查
$ ping <服务器IP>                           # 测试网络连通性
$ traceroute <服务器IP>                     # 追踪路由
$ nc -zv <服务器IP> 22                      # 测试 22 端口

如果 ping 不通：
- 检查安全组/防火墙规则
- 检查服务器是否宕机（通过云控制台查看）
- 检查网络是否中断（联系网络团队）

如果 ping 通但端口不通：
- 检查 SSH 服务是否运行
- 检查防火墙规则（iptables/nftables）
- 检查安全组配置

Step 3：SSH 服务排查
$ ssh -v <服务器IP>                         # 详细模式，查看握手过程

常见 SSH 连接失败原因：
1. Connection refused：
   - SSH 服务未启动：systemctl start sshd
   - SSH 端口被修改：检查 /etc/ssh/sshd_config 的 Port 配置
   - 防火墙阻止：iptables -L -n | grep 22

2. Connection timed out：
   - 网络不可达
   - 防火墙丢弃（DROP 而非 REJECT）
   - 安全组未开放 22 端口

3. Permission denied：
   - 密码错误
   - 密钥不匹配
   - SSH 配置禁止密码登录
   - 用户被锁定

4. Too many authentication failures：
   - SSH 密钥过多导致超过 MaxAuthTries
   - 使用 ssh -o IdentitiesOnly=yes

Step 4：通过其他方式登录
- 通过云控制台的 VNC 控制台登录
- 通过 IPMI/iLO/iDRAC 远程管理
- 通过跳板机/堡垒机
- 请现场同事帮忙检查

Step 5：常见修复操作
# 重启 SSH 服务
$ systemctl restart sshd

# 检查 SSH 配置
$ sshd -T | grep -i "port\|permitroot\|passwordauth"

# 查看 SSH 日志
$ journalctl -u sshd -n 50
$ tail -f /var/log/auth.log    # Debian/Ubuntu
$ tail -f /var/log/secure      # CentOS/RHEL

# 重置 SSH 配置
$ cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config
$ systemctl restart sshd
```

---

#### 题目 22：磁盘空间满了，如何快速定位和处理？

**难度**：⭐⭐⭐⭐

**场景**：监控告警显示某服务器磁盘使用率 95%，需要立即处理。

```
排查流程：

Step 1：确认磁盘使用情况
$ df -h                              # 查看各分区使用率
$ df -i                              # 查看 inode 使用率

Step 2：找到占用空间最大的目录
$ du -sh /* 2>/dev/null | sort -rh | head -10
$ du -sh /var/* | sort -rh | head -10
$ du -sh /var/log/* | sort -rh | head -10

Step 3：找到大文件
$ find / -xdev -type f -size +100M -exec ls -lh {} \; 2>/dev/null | sort -k5 -rh | head -20

Step 4：检查已删除但未释放的文件
$ lsof +L1                           # 查找已删除但被进程占用的文件
# 文件被删除但进程还在写入，空间不会释放

常见原因和处理：

1. 日志文件过大
   # 清空日志（不删除，避免影响正在写入的进程）
   $ > /var/log/messages
   $ > /var/log/syslog

   # 配置 logrotate 自动轮转
   /etc/logrotate.d/custom {
       daily
       rotate 7
       compress
       missingok
       notifempty
   }

2. Docker 数据过大
   $ docker system df                  # 查看 Docker 磁盘使用
   $ docker system prune -a            # 清理未使用的镜像、容器、网络
   $ docker volume prune               # 清理未使用的卷

3. 已删除但未释放的文件
   $ lsof +L1 | grep deleted
   $ # 找到 PID 后重启对应进程
   $ kill -HUP <pid>                   # 或重启服务

4. 临时文件堆积
   $ find /tmp -type f -mtime +7 -delete
   $ find /var/tmp -type f -mtime +30 -delete

5. journal 日志过大
   $ journalctl --disk-usage
   $ journalctl --vacuum-size=500M     # 保留最近 500M
   $ journalctl --vacuum-time=7d       # 保留最近 7 天

预防措施：
- 配置磁盘使用率告警（80% 预警，90% 告警）
- 配置 logrotate 定期轮转日志
- 定期清理 Docker 资源
- 监控 inode 使用率
- 使用单独的分区存放日志（/var/log）
```

---

#### 题目 23：如何排查内存泄漏问题？

**难度**：⭐⭐⭐⭐⭐

```
排查流程：

Step 1：确认内存使用情况
$ free -h                            # 查看内存使用
$ cat /proc/meminfo                  # 详细内存信息
$ top -o %MEM                        # 按内存排序查看进程

Step 2：识别内存占用异常的进程
$ ps aux --sort=-%mem | head -10
$ smem -tk                           # 更准确的内存统计（PSS）

Step 3：分析进程内存使用
# 查看进程内存映射
$ pmap -x <pid> | sort -k3 -rn | head -20

# 查看进程内存详细信息
$ cat /proc/<pid>/status | grep -i mem
$ cat /proc/<pid>/smaps_rollup

# 持续监控内存增长
$ while true; do
    ps -p <pid> -o pid,rss,vsz,comm
    sleep 5
done

Step 4：针对不同语言的排查

Java 应用：
$ jmap -heap <pid>                   # 堆内存使用
$ jmap -histo <pid> | head -20       # 对象统计
$ jstat -gcutil <pid> 1000           # GC 统计
$ # 生成 heap dump
$ jmap -dump:live,format=b,file=heap.bin <pid>

Go 应用：
$ curl http://localhost:6060/debug/pprof/heap > heap.prof
$ go tool pprof heap.prof
$ (pprof) top
$ (pprof) web

Python 应用：
$ import tracemalloc
$ tracemalloc.start()
$ # ... 运行代码 ...
$ snapshot = tracemalloc.take_snapshot()
$ for stat in snapshot.statistics('lineno')[:10]:
$     print(stat)

Step 5：内核内存泄漏
$ slabtop                            # 查看 slab 缓存
$ vmstat -w 1                        # 观察内存变化
$ dmesg | grep -i "out of memory"    # OOM 日志

常见原因：
- 应用未释放不再使用的对象
- 缓存未设置过期策略
- 连接池未正确关闭
- 全局变量持续增长
- 正则表达式编译未复用
```

---

#### 题目 24：解释 Linux 的 OOM Killer 机制

**难度**：⭐⭐⭐⭐

```
OOM（Out of Memory）Killer 是 Linux 内核在内存不足时杀死进程的机制。

触发条件：
- 系统内存耗尽
- swap 空间用完
- 内核无法回收足够的内存

OOM 评分机制：
- 每个进程有一个 oom_score（0-1000）
- 分数越高越容易被杀死
- /proc/<pid>/oom_score：当前评分
- /proc/<pid>/oom_score_adj：手动调整（-1000 到 1000）

查看 OOM 事件：
$ dmesg | grep -i "oom\|out of memory"
$ journalctl -k | grep -i "oom"
$ grep -i "oom" /var/log/messages

保护关键进程不被 OOM 杀死：
# 设置 oom_score_adj 为 -1000（永远不会被杀）
$ echo -1000 > /proc/<pid>/oom_score_adj

# 对于 systemd 服务
[Service]
OOMScoreAdjust=-1000

允许 OOM 杀死某个进程：
$ echo 1000 > /proc/<pid>/oom_score_adj

Kubernetes 中的 OOM：
- Pod 的 memory limit 对应 cgroup 的内存限制
- 超出 limit 时，容器内进程被 cgroup OOM 杀死
- Pod 状态显示 OOMKilled
- 需要调整 resources.limits.memory

预防 OOM：
- 设置合理的内存限制（cgroup/systemd）
- 监控内存使用率，提前预警
- 配置 swap 空间（但不要依赖 swap）
- 应用层面做好内存管理
- 使用 MemoryOvercommit 关闭过度承诺
```

---

#### 题目 25：如何优化 Linux 服务器的网络性能？

**难度**：⭐⭐⭐⭐

```
网络性能优化清单：

1. 内核参数优化（/etc/sysctl.conf）

# TCP 连接优化
net.core.somaxconn = 65535             # 监听队列最大长度
net.ipv4.tcp_max_syn_backlog = 65535   # SYN 队列长度
net.ipv4.tcp_tw_reuse = 1              # 复用 TIME_WAIT 连接
net.ipv4.tcp_fin_timeout = 30          # FIN_WAIT_2 超时时间
net.ipv4.tcp_keepalive_time = 600      # TCP 保活时间
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3

# 缓冲区优化
net.core.rmem_max = 16777216           # 接收缓冲区最大值
net.core.wmem_max = 16777216           # 发送缓冲区最大值
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# 端口范围
net.ipv4.ip_local_port_range = 1024 65535

# 连接跟踪
net.netfilter.nf_conntrack_max = 1048576
net.netfilter.nf_conntrack_tcp_timeout_established = 3600

2. 网卡优化
# 查看网卡队列
$ ethtool -l eth0

# 设置多队列
$ ethtool -L eth0 combined 8

# 开启网卡 offload
$ ethtool -K eth0 tso on
$ ethtool -K eth0 gro on
$ ethtool -K eth0 gso on

# 中断亲和性
$ cat /proc/interrupts | grep eth0
# 将中断绑定到不同的 CPU 核心

3. Nginx 优化
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 65535;
    use epoll;
    multi_accept on;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 1000;
}

4. 监控工具
$ sar -n DEV 1                        # 网络接口统计
$ sar -n TCP 1                        # TCP 统计
$ ss -s                               # 连接统计
$ nstat                               # 网络统计
$ iftop                               # 实时流量监控
```

---

#### 题目 26：什么是 Linux 的系统调用？常见的系统调用有哪些？

**难度**：⭐⭐⭐

```
系统调用（System Call）是用户程序请求内核服务的接口。

常见系统调用分类：

进程管理：
- fork()：创建子进程
- exec()：执行程序
- exit()：终止进程
- wait()：等待子进程
- getpid()：获取进程 ID

文件操作：
- open()：打开文件
- read()：读取文件
- write()：写入文件
- close()：关闭文件
- stat()：获取文件信息
- ioctl()：设备控制

内存管理：
- brk()/sbrk()：调整堆大小
- mmap()：内存映射
- munmap()：取消内存映射

网络：
- socket()：创建套接字
- bind()：绑定地址
- listen()：监听连接
- accept()：接受连接
- connect()：建立连接
- send()/recv()：发送/接收数据

进程间通信：
- pipe()：创建管道
- shmget()：共享内存
- semget()：信号量
- msgget()：消息队列

查看系统调用：
$ strace -p <pid>                    # 跟踪进程的系统调用
$ strace -c -p <pid>                 # 统计系统调用
$ strace -e trace=network -p <pid>   # 只跟踪网络相关的系统调用

SRE 面试重点：
- 理解用户态和内核态的切换
- 系统调用的开销（上下文切换）
- 为什么频繁的系统调用会影响性能
- 如何减少系统调用（批量操作、缓冲区）
```

---

#### 题目 27：解释 Linux 的虚拟内存机制

**难度**：⭐⭐⭐⭐

```
虚拟内存是操作系统为每个进程提供的独立地址空间。

虚拟内存的作用：
1. 进程隔离：每个进程有独立的地址空间
2. 内存保护：防止进程访问其他进程的内存
3. 内存超分：虚拟内存 > 物理内存（通过 swap）
4. 共享内存：多个进程可以共享相同的物理内存

地址转换过程：
虚拟地址 -> 页表（Page Table）-> 物理地址
                    |
              TLB（Translation Lookaside Buffer）缓存

内存分页：
- 4KB 标准页大小
- 大页（Huge Pages）：2MB 或 1GB
- 大页可以减少 TLB miss，提升性能

Swap 机制：
- 当物理内存不足时，将不活跃的页面换出到磁盘
- 查看：swapon -s, /proc/swaps
- 配置：/etc/fstab 中的 swap 分区

查看虚拟内存：
$ vmstat 1                           # 虚拟内存统计
$ /proc/<pid>/maps                   # 进程内存映射
$ /proc/<pid>/smaps                  # 详细内存映射
$ pmap <pid>                         # 进程内存地图

SRE 优化建议：
- 数据库服务器建议关闭 swap（避免性能抖动）
  $ swapoff -a
  $ echo "vm.swappiness = 0" >> /etc/sysctl.conf

- 使用大页（Huge Pages）优化数据库性能
  $ echo 1024 > /proc/sys/vm/nr_hugepages

- 合理设置 swappiness
  $ sysctl vm.swappiness=10          # 尽量使用物理内存
```

---

#### 题目 28：如何进行 Linux 系统的安全加固？

**难度**：⭐⭐⭐⭐

```
Linux 安全加固清单：

1. 账户安全
# 禁用 root 远程登录
$ sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# 使用密钥认证，禁用密码登录
$ sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# 设置密码策略
$ vim /etc/security/pwquality.conf
  minlen = 12
  dcredit = -1
  ucredit = -1
  lcredit = -1
  ocredit = -1

# 账户锁定策略
$ vim /etc/pam.d/common-auth
  auth required pam_tally2.so deny=5 unlock_time=600

2. 网络安全
# 配置防火墙
$ iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
$ iptables -A INPUT -p tcp --dport 22 -j ACCEPT
$ iptables -A INPUT -p tcp --dport 80 -j ACCEPT
$ iptables -A INPUT -p tcp --dport 443 -j ACCEPT
$ iptables -A INPUT -i lo -j ACCEPT
$ iptables -P INPUT DROP

# 禁用不需要的服务
$ systemctl disable telnet
$ systemctl disable rsh
$ systemctl disable rlogin

3. 文件系统安全
# 设置关键目录权限
$ chmod 700 /root
$ chmod 600 /etc/shadow
$ chmod 644 /etc/passwd

# 设置文件属性
$ chattr +i /etc/passwd              # 防止修改
$ chattr +i /etc/shadow

# 启用审计
$ systemctl enable auditd
$ auditctl -w /etc/passwd -p wa -k passwd_changes
$ auditctl -w /etc/shadow -p wa -k shadow_changes

4. 内核安全
# 禁用 IP 转发（如果不是路由器）
$ echo "net.ipv4.ip_forward = 0" >> /etc/sysctl.conf

# 禁用 ICMP 重定向
$ echo "net.ipv4.conf.all.accept_redirects = 0" >> /etc/sysctl.conf

# 启用 SYN Cookie
$ echo "net.ipv4.tcp_syncookies = 1" >> /etc/sysctl.conf

5. 日志和审计
# 配置 rsyslog 远程日志
$ vim /etc/rsyslog.conf
  *.* @logserver.example.com:514

# 查看安全日志
$ last                              # 登录历史
$ lastb                             # 失败登录
$ who                               # 当前登录用户
$ w                                 # 登录用户及活动

6. 自动化安全扫描
# Lynis 安全审计工具
$ lynis audit system

# OpenSCAP
$ oscap xccdf eval --profile standard --results results.xml ssg-centos7-ds.xml
```

---

#### 题目 29：什么是 Linux 的 LVM？如何扩容？

**难度**：⭐⭐⭐

```
LVM（Logical Volume Manager）逻辑卷管理器。

LVM 的三个层次：
1. PV（Physical Volume）：物理卷，物理磁盘或分区
2. VG（Volume Group）：卷组，由多个 PV 组成的存储池
3. LV（Logical Volume）：逻辑卷，从 VG 中分配的逻辑分区

+---------------------------------------------+
|              Volume Group (VG)               |
|  +----------+  +----------+                 |
|  |  LV: /   |  | LV: /data|                 |
|  +----------+  +----------+                 |
|  +----------+  +----------+  +--------+     |
|  |   PV1    |  |   PV2    |  |  PV3   |     |
|  |  /dev/sda|  |  /dev/sdb|  |/dev/sdc|     |
|  +----------+  +----------+  +--------+     |
+---------------------------------------------+

LVM 扩容步骤：

# 1. 创建物理卷
$ pvcreate /dev/sdb

# 2. 创建卷组
$ vgcreate data_vg /dev/sdb

# 3. 创建逻辑卷
$ lvcreate -L 100G -n data_lv data_vg

# 4. 格式化并挂载
$ mkfs.ext4 /dev/data_vg/data_lv
$ mount /dev/data_vg/data_lv /data

扩容操作：

# 方法 1：添加新磁盘
$ pvcreate /dev/sdc
$ vgextend data_vg /dev/sdc
$ lvextend -L +50G /dev/data_vg/data_lv
$ resize2fs /dev/data_vg/data_lv            # ext4
$ xfs_growfs /data                           # xfs

# 方法 2：在线扩容（无需卸载）
$ lvextend -l +100%FREE /dev/data_vg/data_lv
$ resize2fs /dev/data_vg/data_lv

查看 LVM 状态：
$ pvs                                        # 物理卷
$ vgs                                        # 卷组
$ lvs                                        # 逻辑卷
$ pvdisplay / vgdisplay / lvdisplay          # 详细信息

LVM 快照：
$ lvcreate -L 1G -s -n data_snap /dev/data_vg/data_lv
$ mount -o ro /dev/data_vg/data_snap /mnt/snap
```

---

#### 题目 30：设计一个高可用的 Linux 服务器架构

**难度**：⭐⭐⭐⭐⭐（开放性设计题）

```
设计目标：99.99% 可用性（年停机时间 < 52 分钟）

架构层次：

                    +-------------+
                    |   CDN/WAF   |
                    +------+------+
                           |
                    +------+------+
                    | DNS 轮询/GSLB|
                    +------+------+
                           |
              +------------+------------+
              |            |            |
        +-----+-----+ +---+-----+ +---+-----+
        |  LB (主)   | | LB (备) | | LB (备) |  <- Keepalived VIP
        +-----+-----+ +----+----+ +----+----+
              |            |            |
     +--------+------------+------------+--------+
     |        |            |            |        |
  +--+--+ +--+--+    +---+--+   +----+--+ +---+--+
  |App-1| |App-2|    |App-3 |   |App-4  | |App-5 |
  +--+--+ +--+--+    +---+--+   +----+--+ +---+--+
     |       |           |           |        |
     +-------+-------+---+-----------+--------+
                      |
              +-------+------+
              |   数据库集群  |
              |  (主从/集群)  |
              +--------------+

关键技术点：

1. 负载均衡层
   - LVS + Keepalived（L4 负载均衡）
   - Nginx/HAProxy（L7 负载均衡）
   - 双活或主备模式

2. 应用层
   - 无状态设计（Session 存 Redis）
   - 滚动更新（零停机部署）
   - 健康检查 + 自动摘除
   - 优雅关闭（Graceful Shutdown）

3. 数据层
   - MySQL 主从复制 + 读写分离
   - Redis Cluster（哨兵模式）
   - 定期备份 + 异地容灾

4. 监控告警
   - Prometheus + Grafana 监控
   - ELK 日志集中管理
   - 分级告警（P0-P3）
   - On-Call 轮值

5. 容灾设计
   - 同城双活
   - 异地灾备
   - RTO < 5 分钟，RPO < 1 分钟

6. 安全防护
   - WAF 防护
   - DDoS 防护
   - 堡垒机 + 审计
   - 最小权限原则
```

---

## 💻 实战练习

### 练习 1：Linux 系统性能排查

**场景**：模拟生产环境性能问题，练习排查流程。

```bash
# 1. 模拟 CPU 压力
$ stress --cpu 4 --timeout 60s
$ top -Hp $(pgrep stress)

# 2. 模拟内存压力
$ stress --vm 2 --vm-bytes 512M --timeout 60s
$ free -h
$ vmstat 1

# 3. 模拟 IO 压力
$ stress --io 4 --timeout 60s
$ iostat -xz 1

# 4. 模拟网络问题
$ tc qdisc add dev lo root netem delay 100ms
$ ping localhost
$ tc qdisc del dev lo root

# 5. 综合排查
$ dstat -cdnmgy 1                    # 综合监控
$ sar -A 1 10                        # 全面系统统计
```

### 练习 2：网络故障排查

**场景**：模拟网络故障，练习排查和修复。

```bash
# 1. 模拟 DNS 故障
$ echo "nameserver 1.2.3.4" > /etc/resolv.conf
$ nslookup www.google.com            # 应该失败
$ # 修复：恢复正确的 DNS 配置

# 2. 模拟端口不通
$ iptables -A INPUT -p tcp --dport 8080 -j DROP
$ nc -zv localhost 8080              # 应该超时
$ # 修复：删除 iptables 规则

# 3. 抓包分析
$ tcpdump -i lo port 8080 -w /tmp/capture.pcap &
$ curl http://localhost:8080
$ kill %1
$ tcpdump -r /tmp/capture.pcap       # 读取抓包文件
```

### 练习 3：安全加固实践

**场景**：对一台新安装的 Linux 服务器进行安全加固。

```bash
#!/bin/bash
# 安全加固脚本

# 1. 更新系统
apt update && apt upgrade -y

# 2. 配置 SSH
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# 3. 配置防火墙
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# 4. 配置自动更新
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades

# 5. 安装安全工具
apt install fail2ban lynis -y
systemctl enable fail2ban

# 6. 运行安全审计
lynis audit system --quick
```

---

## 📚 深入阅读

### 书籍
- 《Linux 性能优化实战》- 倪朋飞（极客时间）
- 《UNIX 网络编程 卷1：套接字联网 API》- W.Richard Stevens
- 《TCP/IP 详解 卷1：协议》- W.Richard Stevens
- 《鸟哥的 Linux 私房菜》- 鸟哥

### 在线资源
- [Brendan Gregg 的 Linux 性能工具图](http://www.brendangregg.com/linuxperf.html)
- [Linux Performance](https://linuxperformance.com/)
- [Julia Evans 的网络博客](https://jvns.ca/)

### 工具
- [BCC/BPF 工具集](https://github.com/iovisor/bcc)
- [perf](https://perf.wiki.kernel.org/)
- [sysdig](https://sysdig.com/)

---

## ✅ 自检清单

- [ ] 能流畅描述 Linux 启动流程
- [ ] 能解释进程状态（R/S/D/Z/T）的含义
- [ ] 能使用 top/vmstat/iostat/sar 分析系统性能
- [ ] 能解释 TCP 三次握手和四次挥手
- [ ] 能描述 HTTPS 的握手过程
- [ ] 能完整描述 DNS 解析流程
- [ ] 能使用 iptables/nftables 配置防火墙
- [ ] 能解释 Docker 的网络模式
- [ ] 能排查 SSH 连接、磁盘空间、内存泄漏等问题
- [ ] 能描述 Linux 安全加固的最佳实践
- [ ] 能解释 cgroup 和 namespace 的作用
- [ ] 能设计高可用服务器架构

---

*Day 188 完成。Linux 和网络是 SRE 面试的基础，务必扎实掌握。*
*明天我们将进入容器与 Kubernetes 高频面试题。*
