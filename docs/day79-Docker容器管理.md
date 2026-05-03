# Day 79: Docker 容器管理

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 容器管理 — 生命周期、常用命令、资源限制 cgroups、日志管理、exec/attach、信号处理、健康检查
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 76 (Docker 简介与安装), Day 77 (Docker 镜像基础), Day 78 (Dockerfile 进阶构建)

---

## 🎯 学习目标

完成 Day 79 的学习后，你应该能够：
- 深入理解容器的完整生命周期及其状态转换
- 熟练使用容器管理的各类命令
- 掌握 cgroup 资源限制的原理和配置方法
- 理解容器日志管理的最佳实践
- 掌握 exec 和 attach 的区别及使用场景
- 理解容器的信号处理机制和优雅停止
- 能够配置和使用容器健康检查

---

## 📖 核心知识点

### 1. 容器生命周期

#### 1.1 容器状态与转换

```
容器生命周期状态机：

                    docker create
                         │
                         ▼
                 ┌───────────────┐
                 │   Created     │ ← 已创建但未启动
                 │  (已创建)      │
                 └───────┬───────┘
                         │
              docker start / docker run
                         │
                         ▼
                 ┌───────────────┐
                 │   Running     │ ← 正在运行
          ┌─────│  (运行中)      │─────┐
          │     └───────┬───────┘     │
          │             │             │
  docker pause   docker stop    docker kill
          │             │             │
          ▼             ▼             ▼
   ┌───────────┐ ┌───────────┐ ┌───────────┐
   │  Paused   │ │ Stopping  │ │  Killed   │
   │  (已暂停)  │ │ (停止中)   │ │ (已杀死)  │
   └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
         │              │              │
  docker unpause        │              │
         │              ▼              ▼
         │     ┌───────────────────────────┐
         └────▶│        Exited             │
               │        (已退出)            │
               └─────────────┬─────────────┘
                             │
                    docker start (重启)
                             │
                             ▼
                       Running
                             │
                    docker rm (删除)
                             │
                             ▼
                       (已删除)
```

```bash
# 容器生命周期命令详解

# 1. 创建容器（不启动）
docker create --name myapp -p 8080:80 nginx:latest
# 容器状态：Created

# 2. 启动已创建的容器
docker start myapp
# 容器状态：Created → Running

# 3. 创建并运行（create + start 的组合）
docker run -d --name myapp -p 8080:80 nginx:latest
# -d: 后台运行（detach 模式）

# 4. 暂停容器（冻结进程，使用 cgroup freezer）
docker pause myapp
# 容器状态：Running → Paused
# 进程被冻结，不消耗 CPU，但保持内存占用

# 5. 恢复暂停的容器
docker unpause myapp
# 容器状态：Paused → Running

# 6. 停止容器（优雅停止）
docker stop myapp
# 发送 SIGTERM → 等待 10 秒 → 发送 SIGKILL
# 容器状态：Running → Exited

# 7. 强制停止容器（立即杀死）
docker kill myapp
# 发送 SIGKILL（默认）或指定信号
docker kill --signal=SIGTERM myapp
# 容器状态：Running → Exited

# 8. 重启容器
docker restart myapp
# 等同于 stop + start

# 9. 删除容器
docker rm myapp
# 只能删除已停止的容器
docker rm -f myapp
# 强制删除（先 kill 再 rm）
```

#### 1.2 容器退出码与含义

```bash
# 查看容器退出码
docker inspect myapp --format '{{.State.ExitCode}}'

# 查看容器状态详情
docker inspect myapp --format '{{.State}}'
```

```
常见退出码及其含义：

┌──────────┬──────────────────────────────────────────────────────┐
│ 退出码    │ 含义                                                │
├──────────┼──────────────────────────────────────────────────────┤
│ 0        │ 正常退出（容器内进程主动调用 exit(0)）               │
│ 1        │ 应用错误（通用错误）                                 │
│ 2        │ Shell 内建命令误用                                   │
│ 126      │ 命令无法执行（权限问题）                             │
│ 127      │ 命令未找到（路径错误或命令不存在）                   │
│ 128+N    │ 被信号 N 杀死                                        │
│   130    │ 128+2 = SIGINT（Ctrl+C）                            │
│   137    │ 128+9 = SIGKILL（被 docker kill 或 OOM）            │
│   143    │ 128+15 = SIGTERM（docker stop 默认）                │
│ 139      │ 128+11 = SIGSEGV（段错误）                          │
│ 134      │ 128+6 = SIGABRT（程序异常终止）                     │
└──────────┴──────────────────────────────────────────────────────┘

SRE 排查思路：
  退出码 0   → 歾认退出（可能是一次性任务，或者程序逻辑错误提前退出）
  退出码 1   → 查看 docker logs，通常是应用层错误
  退出码 137 → 检查是否被 OOM killer 杀死（docker inspect 看 OOMKilled 字段）
  退出码 139 → 段错误，可能是 C/C++ 扩展或内存问题
  退出码 143 → 正常的 docker stop，如果频繁出现可能是健康检查失败
```

```bash
# 检查是否因 OOM 被杀
docker inspect myapp --format '{{.State.OOMKilled}}'
# true 表示因内存不足被杀

# 查看系统 OOM 日志
dmesg | grep -i "oom\|killed"
journalctl -k | grep -i "oom"
```

#### 1.3 重启策略

```bash
# 重启策略配置
# no - 默认，不自动重启
docker run --restart no nginx

# always - 总是重启（包括手动停止后 Docker 重启时）
docker run --restart always nginx

# unless-stopped - 除非手动停止（推荐用于生产）
docker run --restart unless-stopped nginx

# on-failure - 仅在非零退出码时重启
docker run --restart on-failure nginx

# on-failure:5 - 最多重试 5 次
docker run --restart on-failure:5 nginx

# 修改已运行容器的重启策略
docker update --restart unless-stopped myapp

# 批量修改所有容器的重启策略
docker update --restart unless-stopped $(docker ps -q)
```

```
重启策略对比：

┌──────────────────┬────────────┬────────────┬──────────────────────┐
│ 策略              │ 非零退出   │ 零退出     │ Docker 重启后         │
├──────────────────┼────────────┼────────────┼──────────────────────┤
│ no               │ 不重启     │ 不重启     │ 不启动               │
│ always           │ 重启       │ 重启       │ 启动                 │
│ unless-stopped   │ 重启       │ 重启       │ 启动（除非手动停止） │
│ on-failure       │ 重启       │ 不重启     │ 不启动               │
│ on-failure:N     │ 重启(N次)  │ 不重启     │ 不启动               │
└──────────────────┴────────────┴────────────┴──────────────────────┘

生产环境建议：
  - 长期运行的服务：unless-stopped
  - 一次性任务：no（默认）
  - 可能失败的任务：on-failure:5
  - 需要极高可用性：always + 健康检查
```

### 2. 容器常用命令详解

#### 2.1 容器查看与过滤

```bash
# 查看运行中的容器
docker ps
# CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES

# 查看所有容器（包括已停止的）
docker ps -a

# 格式化输出
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"
docker ps --format "json" | jq .

# 只显示容器 ID（常用于批量操作）
docker ps -q
docker ps -aq

# 过滤容器
docker ps --filter "status=running"
docker ps --filter "status=exited"
docker ps --filter "name=web"
docker ps --filter "ancestor=nginx:latest"
docker ps --filter "label=env=production"
docker ps --filter "exited=137"  # 被 OOM 杀死的容器

# 组合过滤
docker ps --filter "status=exited" --filter "ancestor=nginx"

# 显示容器大小
docker ps -s
# SIZE 列显示可写层大小
```

#### 2.2 容器信息查看

```bash
# 查看容器详细信息（JSON 格式）
docker inspect myapp

# 使用 Go template 提取特定信息
docker inspect --format '{{.State.Status}}' myapp
docker inspect --format '{{.State.Pid}}' myapp
docker inspect --format '{{.NetworkSettings.IPAddress}}' myapp
docker inspect --format '{{.HostConfig.Memory}}' myapp
docker inspect --format '{{json .State}}' myapp | jq .
docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' myapp

# 查看容器进程
docker top myapp
docker top myapp -o pid,ppid,cmd

# 查看容器资源使用
docker stats
docker stats --no-stream  # 单次输出
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# 查看容器文件系统变更
docker diff myapp
# A = 新增, C = 修改, D = 删除

# 查看容器日志（不跟踪）
docker logs myapp
docker logs --tail 100 myapp
docker logs --since 2024-01-01T00:00:00 myapp
docker logs --until 2024-01-02T00:00:00 myapp
```

#### 2.3 容器文件操作

```bash
# 从容器复制文件到宿主机
docker cp myapp:/etc/nginx/nginx.conf ./nginx.conf
docker cp myapp:/var/log/nginx/ ./nginx-logs/

# 从宿主机复制文件到容器
docker cp ./config.yml myapp:/app/config.yml
docker cp ./html/ myapp:/usr/share/nginx/html/

# 注意：docker cp 对运行中的容器也能使用
# 复制操作是原子的，不会影响正在运行的进程
```

### 3. 资源限制（cgroups 深入）

#### 3.1 CPU 限制

```bash
# 限制 CPU 核心数（最常用）
docker run --cpus="1.5" nginx
# 限制容器最多使用 1.5 个 CPU 核心

# 绑定到特定 CPU 核心
docker run --cpuset-cpus="0,1" nginx
# 只使用 CPU 0 和 CPU 1

# CPU 权重（相对权重，默认 1024）
docker run --cpu-shares=512 nginx
# 当 CPU 资源紧张时，此容器获得的 CPU 时间是一般容器的 50%

# 实时调度限制（cgroup RT 调度器）
docker run --cpu-rt-runtime=950000 nginx
```

```
CPU 限制的底层实现：

  --cpus="1.5"
  ┌──────────────────────────────────────────────────────────────┐
  │ 实际设置 cgroup 参数：                                        │
  │   cpu.cfs_period_us = 100000  (100ms，调度周期)              │
  │   cpu.cfs_quota_us  = 150000  (150ms，每个周期可用的时间)    │
  │                                                              │
  │ 计算：quota / period = 150000 / 100000 = 1.5 个 CPU          │
  └──────────────────────────────────────────────────────────────┘

  --cpuset-cpus="0,1"
  ┌──────────────────────────────────────────────────────────────┐
  │ 实际设置 cgroup 参数：                                        │
  │   cpuset.cpus = "0-1"                                        │
  │                                                              │
  │ 进程只能在 CPU 0 和 CPU 1 上调度                              │
  └──────────────────────────────────────────────────────────────┘

  --cpu-shares=512
  ┌──────────────────────────────────────────────────────────────┐
  │ 实际设置 cgroup 参数：                                        │
  │   cpu.shares = 512                                           │
  │                                                              │
  │ 权重机制：只有在 CPU 资源紧张时才生效                         │
  │ 容器 A: shares=1024, 容器 B: shares=512                      │
  │ A 获得 2/3 的 CPU 时间，B 获得 1/3                           │
  │ 如果只有一个容器在运行，它可以使用 100% CPU                   │
  └──────────────────────────────────────────────────────────────┘
```

#### 3.2 内存限制

```bash
# 内存硬限制
docker run --memory="512m" nginx
# 容器最多使用 512MB 内存

# 内存 + swap 限制
docker run --memory="512m" --memory-swap="1g" nginx
# 内存 512MB + swap 512MB = 总共 1GB

# 禁用 swap
docker run --memory="512m" --memory-swap="512m" nginx
# memory-swap 等于 memory 时，swap 被禁用

# 内存软限制
docker run --memory="512m" --memory-reservation="256m" nginx
# 内存紧张时，系统会尝试将容器内存降到 256MB 以下

# OOM 控制
docker run --memory="512m" --oom-kill-disable nginx
# 禁用 OOM killer（慎用！可能导致系统不稳定）

docker run --memory="512m" --oom-score-adj=-500 nginx
# 调整 OOM 优先级（-1000 到 1000，越低越不容易被杀）
```

```
内存限制的底层实现：

  --memory="512m"
  ┌──────────────────────────────────────────────────────────────┐
  │ 实际设置 cgroup 参数（cgroup v2）：                           │
  │   memory.max = 536870912  (512MB)                            │
  │                                                              │
  │ 当容器内存使用超过限制时：                                    │
  │   1. 内核尝试回收容器的页面缓存                               │
  │   2. 如果无法回收足够内存，触发 OOM killer                    │
  │   3. OOM killer 杀死容器内的进程                              │
  │   4. 容器退出码为 137 (128+9=SIGKILL)                        │
  │   5. docker inspect 显示 OOMKilled=true                      │
  └──────────────────────────────────────────────────────────────┘

  --memory-reservation="256m"
  ┌──────────────────────────────────────────────────────────────┐
  │ 实际设置 cgroup 参数（cgroup v2）：                           │
  │   memory.low = 268435456  (256MB)                            │
  │                                                              │
  │ 软限制：内存紧张时的保护线                                    │
  │ 不会强制杀死进程，但内核会优先回收超过此值的内存              │
  └──────────────────────────────────────────────────────────────┘
```

#### 3.3 I/O 限制

```bash
# 限制块设备读写速度
docker run --device-read-bps /dev/sda:10mb nginx
docker run --device-write-bps /dev/sda:10mb nginx

# 限制 IOPS
docker run --device-read-iops /dev/sda:1000 nginx
docker run --device-write-iops /dev/sda:1000 nginx

# 限制所有块设备的 I/O 权重（默认 500，范围 10-1000）
docker run --blkio-weight=300 nginx
```

#### 3.4 PID 和其他限制

```bash
# 限制容器内最大进程数（防止 fork bomb）
docker run --pids-limit=100 nginx

# 限制容器的 ulimit
docker run --ulimit nofile=65536:65536 nginx
docker run --ulimit nproc=4096:4096 nginx
docker run --ulimit memlock=-1:-1 nginx  # 不限制锁定内存

# 只读文件系统
docker run --read-only nginx
# 容器无法写入任何文件，需要配合 tmpfs 使用
docker run --read-only --tmpfs /tmp:rw,size=100m nginx

# 限制容器可以添加的能力
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE nginx
# 只保留绑定低端口的能力

# 禁用容器提权
docker run --security-opt no-new-privileges nginx
```

#### 3.5 资源监控与分析

```bash
# 实时资源监控
docker stats

# 单次输出
docker stats --no-stream

# 格式化输出
docker stats --no-stream --format \
    "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}"

# 查看容器的 cgroup 信息（cgroup v2）
CONTAINER_ID=$(docker inspect --format '{{.Id}}' myapp)
cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/cpu.max
cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/memory.max
cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/memory.current
cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/pids.max
cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/pids.current

# 使用 cgroup 事件监控
docker events --filter container=myapp --filter event=oom
# 监控 OOM 事件
```

### 4. 容器日志管理

#### 4.1 日志驱动

```
Docker 日志驱动类型：

┌──────────────────┬──────────────────────────────────────────────────┐
│ 日志驱动          │ 说明                                             │
├──────────────────┼──────────────────────────────────────────────────┤
│ json-file        │ 默认驱动，日志存储为 JSON 文件                   │
│                  │ 位于 /var/lib/docker/containers/<id>/<id>-json.log│
│ syslog           │ 发送到 syslog 服务                               │
│ journald         │ 发送到 systemd journal                           │
│ fluentd          │ 发送到 Fluentd 收集器                            │
│ awslogs          │ 发送到 AWS CloudWatch                            │
│ gcplogs          │ 发送到 Google Cloud Logging                      │
│ splunk           │ 发送到 Splunk                                    │
│ etwlogs          │ Windows ETW 日志                                 │
│ gelf             │ 发送到 GELF 端点（Graylog）                      │
│ local            │ 本地日志驱动（优化了性能和压缩）                 │
│ none             │ 禁用日志                                         │
└──────────────────┴──────────────────────────────────────────────────┘
```

```bash
# 全局配置日志驱动（/etc/docker/daemon.json）
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5",
    "labels": "env,service",
    "tag": "{{.Name}}/{{.ID}}"
  }
}

# 单个容器配置日志驱动
docker run --log-driver=json-file \
    --log-opt max-size=50m \
    --log-opt max-file=3 \
    nginx

# 使用 journald（systemd 环境推荐）
docker run --log-driver=journald nginx

# 禁用日志（不推荐，无法排查问题）
docker run --log-driver=none nginx
```

#### 4.2 日志查看与分析

```bash
# 查看容器日志
docker logs myapp

# 实时跟踪日志
docker logs -f myapp
docker logs --follow myapp

# 显示时间戳
docker logs -t myapp

# 只显示最后 N 行
docker logs --tail 100 myapp

# 按时间过滤
docker logs --since 2024-01-01T00:00:00 myapp
docker logs --since 30m myapp  # 最近 30 分钟
docker logs --until 2024-01-02T00:00:00 myapp

# 组合使用
docker logs -f --tail 50 --since 10m myapp

# 日志搜索
docker logs myapp 2>&1 | grep "ERROR"
docker logs myapp 2>&1 | grep -c "ERROR"  # 统计错误数

# 查看日志文件大小
docker inspect --format '{{.LogPath}}' myapp
ls -lh $(docker inspect --format '{{.LogPath}}' myapp)

# 查看所有容器的日志大小
for c in $(docker ps -q); do
    size=$(ls -lh $(docker inspect --format '{{.LogPath}}' $c) 2>/dev/null | awk '{print $5}')
    name=$(docker inspect --format '{{.Name}}' $c)
    echo "$name: $size"
done
```

#### 4.3 日志轮转最佳实践

```json
// /etc/docker/daemon.json - 生产环境日志配置
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5",
    "compress": "true"
  }
}
```

```
日志轮转配置说明：

max-size: "100m"
  - 单个日志文件最大 100MB
  - 超过后自动轮转（创建新文件）

max-file: "5"
  - 最多保留 5 个日志文件
  - 总日志大小最多约 500MB

compress: "true"（local 驱动支持）
  - 轮转后的日志文件自动压缩

生产环境建议：
  - 根据磁盘空间和日志量设置合理的 max-size
  - max-file 建议 3-10
  - 总日志空间 = max-size * max-file
  - 定期监控日志文件大小
  - 考虑使用集中日志系统（ELK、Loki、Splunk）
```

#### 4.4 集中日志方案

```bash
# 方案 1：使用 journald + journalctl
docker run --log-driver=journald \
    --log-opt tag="{{.Name}}" \
    nginx

# 查看日志
journalctl CONTAINER_NAME=myapp
journalctl CONTAINER_NAME=myapp --since "1 hour ago"

# 方案 2：使用 Fluentd 收集
# 先启动 Fluentd
docker run -d --name fluentd \
    -p 24224:24224 \
    -v /fluentd/log:/fluentd/log \
    fluent/fluentd

# 应用容器将日志发送到 Fluentd
docker run --log-driver=fluentd \
    --log-opt fluentd-address=localhost:24224 \
    --log-opt tag="app.nginx" \
    nginx

# 方案 3：应用层直接写日志到文件，使用 volume 挂载
docker run -v /var/log/myapp:/app/logs nginx
# 然后用 Filebeat/Promtail 等工具收集
```

### 5. exec 与 attach

#### 5.1 docker exec — 在运行中的容器中执行命令

```bash
# 交互式 shell（最常用）
docker exec -it myapp /bin/bash
docker exec -it myapp /bin/sh  # Alpine 镜像

# 以特定用户执行
docker exec -it -u root myapp /bin/bash
docker exec -it -u 1000:1000 myapp /bin/sh

# 设置环境变量
docker exec -it -e DEBUG=true myapp /bin/bash

# 在特定目录执行
docker exec -it -w /etc/nginx myapp cat nginx.conf

# 非交互式执行（一次性命令）
docker exec myapp ls /app
docker exec myapp cat /etc/os-release
docker exec myapp ps aux

# 后台执行
docker exec -d myapp touch /tmp/test-file

# 传递 stdin
echo "hello" | docker exec -i myapp cat
```

```
docker exec 的底层实现：

  docker exec -it myapp /bin/bash
       │
       │ 1. Docker CLI 发送 exec 创建请求给 dockerd
       │ 2. dockerd 调用 containerd 在目标容器中创建新进程
       │ 3. containerd-shim 在容器的 namespace 中启动新进程
       │ 4. 新进程与容器共享 PID namespace、Network namespace 等
       │ 5. 新进程的 PID 不是 1（是容器 init 进程的子进程）
       │
       ▼
  容器内运行：
    PID 1: nginx master (容器主进程)
    PID 2: nginx worker
    PID 3: nginx worker
    PID N: /bin/bash (exec 进入的 shell)  ← 你的 exec 进程
```

#### 5.2 docker attach — 附加到容器的主进程

```bash
# 附加到容器的主进程（PID 1）
docker attach myapp

# 分离（不杀死容器）
# 按 Ctrl+P, Ctrl+Q 分离

# 使用 --sig-proxy 控制信号转发
docker attach --sig-proxy=true myapp
# 默认 true，Ctrl+C 会发送信号给容器
docker attach --sig-proxy=false myapp
# Ctrl+C 只影响 attach 客户端，不影响容器
```

```
exec vs attach 对比：

┌─────────────────┬──────────────────────┬──────────────────────┐
│ 特性             │ docker exec          │ docker attach        │
├─────────────────┼──────────────────────┼──────────────────────┤
│ 目标进程         │ 容器内任意进程       │ 容器主进程 (PID 1)   │
│ 创建新进程       │ 是                   │ 否（附加到已有进程） │
│ 退出影响容器     │ 否（只影响 exec 进程）│ 可能（取决于信号）   │
│ 多个同时使用     │ 支持                 │ 可能冲突             │
│ 典型场景         │ 调试、执行一次性命令 │ 查看主进程输出       │
│ 推荐度           │ 推荐                 │ 谨慎使用             │
└─────────────────┴──────────────────────┴──────────────────────┘

SRE 建议：
  - 优先使用 docker exec 而非 attach
  - attach 到主进程可能意外发送信号导致容器停止
  - 如果只是想看日志，用 docker logs 而非 attach
```

### 6. 信号处理与优雅停止

#### 6.1 容器信号处理机制

```
Docker 停止容器的信号流程：

  docker stop myapp
       │
       │ 1. 发送 SIGTERM 给容器的 PID 1 进程
       │
       │ 2. 等待一段时间（默认 10 秒）
       │    期间容器进程可以：
       │    - 清理资源
       │    - 关闭连接
       │    - 保存状态
       │    - 完成正在处理的请求
       │
       │ 3. 如果超时仍未退出，发送 SIGKILL
       │    强制杀死所有进程
       ▼
  容器停止

  自定义超时：
  docker stop -t 30 myapp  # 等待 30 秒
  docker stop --time 30 myapp

  直接发送信号：
  docker kill --signal=SIGTERM myapp
  docker kill --signal=SIGHUP myapp
```

#### 6.2 PID 1 问题

```
PID 1 问题的核心：

  Shell 格式的 CMD/ENTRYPOINT：
  ┌──────────────────────────────────────────────────────────────┐
  │ CMD nginx -g "daemon off;"                                   │
  │ 实际执行：/bin/sh -c "nginx -g 'daemon off;'"               │
  │                                                              │
  │ 进程树：                                                     │
  │   PID 1: /bin/sh                                             │
  │     └── PID N: nginx                                         │
  │                                                              │
  │ 问题：                                                       │
  │   1. SIGTERM 发送给 PID 1 (sh)，sh 不转发信号给 nginx       │
  │   2. nginx 无法优雅停止，10 秒后被 SIGKILL 强制杀死         │
  │   3. 正在处理的请求被中断，可能丢失数据                      │
  └──────────────────────────────────────────────────────────────┘

  Exec 格式的 CMD/ENTRYPOINT：
  ┌──────────────────────────────────────────────────────────────┐
  │ CMD ["nginx", "-g", "daemon off;"]                           │
  │ 实际执行：nginx -g "daemon off;"                             │
  │                                                              │
  │ 进程树：                                                     │
  │   PID 1: nginx                                               │
  │     └── PID N: nginx worker                                  │
  │                                                              │
  │ 正确行为：                                                   │
  │   1. SIGTERM 直接发送给 PID 1 (nginx)                       │
  │   2. nginx 执行优雅停止：停止接受新请求，完成现有请求        │
  │   3. 干净退出                                                │
  └──────────────────────────────────────────────────────────────┘

  解决方案：
  1. 始终使用 Exec 格式
  2. 或者使用 tini/dumb-init 作为 init 进程
     ENTRYPOINT ["tini", "--"]
     CMD ["nginx", "-g", "daemon off;"]
```

#### 6.3 STOPSIGNAL 指令

```dockerfile
# 设置容器停止时的默认信号
STOPSIGNAL SIGQUIT
# docker stop 发送 SIGQUIT 而非 SIGTERM

# 常见的自定义停止信号：
# Nginx: SIGQUIT（优雅关闭）
# PostgreSQL: SIGTERM（正常关闭）
# Redis: SIGTERM
# MySQL: SIGTERM
```

#### 6.4 优雅停止最佳实践

```dockerfile
# Go 应用优雅停止示例
# main.go
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
    })

    server := &http.Server{Addr: ":8080", Handler: mux}

    // 启动服务器
    go func() {
        if err := server.ListenAndServe(); err != http.ErrServerClosed {
            log.Fatal(err)
        }
    }()

    // 监听信号
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGTERM, syscall.SIGINT)
    <-quit

    // 优雅关闭
    log.Println("Shutting down server...")
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    server.Shutdown(ctx)
    log.Println("Server stopped")
}
```

```python
# Python (FastAPI) 优雅停止示例
import signal
import sys
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

def handle_signal(signum, frame):
    print(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### 7. 健康检查

#### 7.1 Dockerfile 中定义健康检查

```dockerfile
# HTTP 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# TCP 端口检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD nc -z localhost 8080 || exit 1

# 进程检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD pgrep -x nginx || exit 1

# 自定义脚本
COPY healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/healthcheck.sh
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["healthcheck.sh"]
```

```bash
# healthcheck.sh 示例
#!/bin/bash
set -e

# 检查 HTTP 端点
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
if [ "$HTTP_CODE" != "200" ]; then
    echo "Health check failed: HTTP $HTTP_CODE"
    exit 1
fi

# 检查关键进程
if ! pgrep -x nginx > /dev/null; then
    echo "Health check failed: nginx not running"
    exit 1
fi

# 检查磁盘空间
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "Health check failed: disk usage ${DISK_USAGE}%"
    exit 1
fi

echo "Health check passed"
exit 0
```

#### 7.2 运行时健康检查配置

```bash
# 覆盖 Dockerfile 中的健康检查
docker run --health-cmd="curl -f http://localhost:8080/health || exit 1" \
    --health-interval=15s \
    --health-timeout=5s \
    --health-start-period=30s \
    --health-retries=3 \
    nginx

# 禁用健康检查
docker run --no-healthcheck nginx

# 查看健康检查状态
docker inspect --format '{{.State.Health.Status}}' myapp
# starting / healthy / unhealthy

# 查看健康检查日志
docker inspect --format '{{json .State.Health}}' myapp | jq .

# 查看健康检查历史
docker inspect --format '{{range .State.Health.Log}}{{.ExitCode}} {{.Output}}{{end}}' myapp
```

```
健康检查状态转换：

  容器启动
       │
       ▼
  ┌───────────┐
  │ starting  │ ← start-period 内的状态
  │           │   期间失败不计入 retries
  └─────┬─────┘
        │ start-period 结束
        ▼
  ┌───────────┐     检查成功      ┌───────────┐
  │           │ ────────────────▶│  healthy  │
  │           │                   │           │
  │           │     检查失败      └─────┬─────┘
  │           │ ◀──────────────────────│
  │           │                        │
  └─────┬─────┘                        │
        │ 连续 retries 次失败          │
        ▼                              │
  ┌───────────┐                        │
  │ unhealthy │ ◀──────────────────────┘
  └───────────┘     连续 retries 次失败

  与 Docker Swarm / Kubernetes 的集成：
  - unhealthy 的容器会被自动替换（Swarm mode）
  - Kubernetes 使用 livenessProbe 和 readinessProbe
  - 健康检查是自动故障恢复的基础
```

### 8. SRE 实战：容器故障排查

#### 8.1 容器启动失败排查流程

```bash
# 容器故障排查完整流程

# Step 1: 查看容器状态
docker ps -a
# 如果容器不在列表中，可能被删除了

# Step 2: 查看退出码
docker inspect --format '{{.State.ExitCode}}' myapp
docker inspect --format '{{.State.Error}}' myapp

# Step 3: 查看日志
docker logs myapp
docker logs --tail 50 myapp

# Step 4: 查看详细状态
docker inspect --format '{{json .State}}' myapp | jq .

# Step 5: 根据退出码分析
# 退出码 0: 进程主动退出
#   - 检查是否是一次性任务
#   - 检查应用是否有提前退出的逻辑
#   - 检查 CMD 是否正确

# 退出码 1: 应用错误
#   - 查看 docker logs 的错误信息
#   - 检查配置文件是否正确
#   - 检查依赖服务是否可用

# 退出码 126: 权限问题
#   - 检查文件权限
#   - 检查 USER 指令

# 退出码 127: 命令未找到
#   - 检查 ENTRYPOINT/CMD 是否正确
#   - 检查 PATH 环境变量
#   - 检查是否使用了正确的 shell

# 退出码 137: 被 SIGKILL 杀死
#   - 检查 OOMKilled: docker inspect --format '{{.State.OOMKilled}}' myapp
#   - 检查内存限制是否合理
#   - 查看 dmesg | grep oom

# Step 6: 交互式调试
# 如果镜像中没有 shell，使用 debug 镜像
docker run -it --rm --pid=container:myapp --net=container:myapp busybox

# 如果容器能启动但行为异常
docker exec -it myapp /bin/bash

# Step 7: 检查资源限制
docker inspect --format '{{.HostConfig.Memory}}' myapp
docker inspect --format '{{.HostConfig.NanoCpus}}' myapp
docker stats myapp --no-stream
```

#### 8.2 常见问题排查

```bash
# 问题 1：容器启动后立即退出
# 排查：
docker logs myapp
docker inspect myapp --format '{{.State}}'
# 常见原因：
# - CMD/ENTRYPOINT 使用了 shell 格式，shell 执行完就退出
# - 应用启动失败
# - 前台进程退出（daemon 模式）
# 解决：确保主进程在前台运行（如 nginx -g "daemon off;"）

# 问题 2：容器 OOM 被杀
# 排查：
docker inspect myapp --format '{{.State.OOMKilled}}'
dmesg | grep -i oom
docker stats myapp --no-stream
# 解决：
docker update --memory=1g myapp  # 增加内存限制
# 或优化应用内存使用

# 问题 3：容器健康检查失败
# 排查：
docker inspect --format '{{json .State.Health}}' myapp | jq .
# 查看健康检查日志
docker inspect --format '{{range .State.Health.Log}}{{.ExitCode}} {{.Output}}{{end}}' myapp
# 常见原因：
# - 健康检查命令不正确
# - start-period 太短，应用还没启动完成
# - 应用响应不正确

# 问题 4：容器无法停止
# 排查：
docker stop myapp  # 等待 10 秒
docker kill myapp  # 强制杀死
# 常见原因：
# - PID 1 进程不处理 SIGTERM（使用了 shell 格式）
# - 应用无法优雅停止
# 解决：使用 Exec 格式的 CMD，或使用 tini

# 问题 5：容器网络不通
# 排查：
docker exec myapp ping google.com
docker exec myapp cat /etc/resolv.conf
docker inspect myapp --format '{{json .NetworkSettings}}' | jq .
# 常见原因：
# - DNS 配置错误
# - 网络模式问题
# - 防火墙规则
```

---

## 💻 实战练习

### 练习 1：容器生命周期管理

**目标**：完整体验容器的生命周期，理解每个状态的含义。

```bash
# 1. 创建容器（不启动）
docker create --name lifecycle-test nginx:latest
docker ps -a --filter "name=lifecycle-test"
# 状态：Created

# 2. 启动容器
docker start lifecycle-test
docker ps --filter "name=lifecycle-test"
# 状态：Running

# 3. 暂停容器
docker pause lifecycle-test
docker ps --filter "name=lifecycle-test"
# 状态：Paused

# 4. 恢复容器
docker unpause lifecycle-test
docker ps --filter "name=lifecycle-test"
# 状态：Running

# 5. 优雅停止
docker stop -t 5 lifecycle-test
docker ps -a --filter "name=lifecycle-test"
# 状态：Exited (0) 或 (143=128+15=SIGTERM)

# 6. 重启
docker start lifecycle-test
docker ps --filter "name=lifecycle-test"
# 状态：Running

# 7. 查看详细状态
docker inspect --format '{{json .State}}' lifecycle-test | jq .

# 8. 删除
docker rm -f lifecycle-test
```

### 练习 2：资源限制与监控

**目标**：配置和验证容器的资源限制。

```bash
# 1. 创建有资源限制的容器
docker run -d --name resource-test \
    --cpus="0.5" \
    --memory="256m" \
    --memory-swap="256m" \
    --pids-limit=50 \
    nginx:latest

# 2. 查看资源使用
docker stats resource-test --no-stream

# 3. 查看 cgroup 配置
CONTAINER_ID=$(docker inspect --format '{{.Id}}' resource-test)

# cgroup v2
echo "CPU 限制:"
cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/cpu.max
echo "内存限制:"
cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/memory.max
echo "PID 限制:"
cat /sys/fs/cgroup/system.slice/docker-${CONTAINER_ID}.scope/pids.max

# 4. 测试内存限制
docker exec resource-test sh -c '
    # 安装 stress 工具（如果可用）
    apt-get update > /dev/null 2>&1 && apt-get install -y stress > /dev/null 2>&1 || true
    # 尝试分配超过限制的内存
    stress --vm 1 --vm-bytes 300m --timeout 10 2>&1 || echo "Memory limit enforced"
'

# 5. 查看容器是否因 OOM 被杀
docker inspect --format '{{.State.OOMKilled}}' resource-test
docker logs resource-test --tail 20

# 6. 更新资源限制
docker update --memory=512m resource-test
docker inspect --format '{{.HostConfig.Memory}}' resource-test

# 7. 清理
docker rm -f resource-test
```

### 练习 3：日志管理与信号处理

**目标**：掌握容器日志管理和信号处理机制。

```bash
# 1. 创建带日志配置的容器
docker run -d --name log-test \
    --log-driver=json-file \
    --log-opt max-size=1m \
    --log-opt max-file=3 \
    nginx:latest

# 2. 生成日志
for i in $(seq 1 1000); do
    docker exec log-test sh -c "echo 'Log entry $i at $(date)'"
done

# 3. 查看日志
docker logs log-test | head -5
docker logs --tail 10 log-test
docker logs -t log-test | tail -5  # 带时间戳

# 4. 查看日志文件
LOG_PATH=$(docker inspect --format '{{.LogPath}}' log-test)
ls -lh $LOG_PATH

# 5. 测试信号处理
# 创建一个能处理信号的容器
docker run -d --name signal-test --stop-timeout 30 \
    python:3.11-slim python3 -c "
import signal, time, sys

def handler(signum, frame):
    print(f'Received signal {signum}, cleaning up...')
    time.sleep(2)
    print('Cleanup done, exiting')
    sys.exit(0)

signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

print('Starting, waiting for signals...')
while True:
    time.sleep(1)
"

# 6. 发送信号
docker logs -f signal-test &
docker stop -t 10 signal-test
# 观察优雅停止过程

# 7. 测试 PID 1 问题
docker run -d --name shell-test --stop-timeout 5 \
    nginx:latest sh -c "nginx -g 'daemon off;'"
# 使用了 shell 格式，信号不会传递给 nginx

docker stop -t 5 shell-test
# 可能需要等待超时才能停止

# 8. 对比：使用 exec 格式
docker run -d --name exec-test --stop-timeout 5 \
    nginx:latest nginx -g "daemon off;"
# 或者在 Dockerfile 中使用 CMD ["nginx", "-g", "daemon off;"]

docker stop -t 5 exec-test
# 立即优雅停止

# 9. 清理
docker rm -f log-test signal-test shell-test exec-test 2>/dev/null
```

---

## 🎯 面试题精选

### 面试题 1：解释 Docker 容器的完整生命周期，包括所有状态和转换。

**参考答案**：

容器生命周期包括以下状态：Created（已创建未启动）、Running（运行中）、Paused（已暂停，使用 cgroup freezer 冻结进程）、Stopped/Exited（已退出）、Removing（正在删除）。状态转换包括：create 创建容器进入 Created 状态；start 启动进入 Running；run 等于 create+start；pause 使用 cgroup freezer 冻结进程进入 Paused；unpause 解冻恢复到 Running；stop 发送 SIGTERM 等待后发送 SIGKILL 进入 Exited；kill 直接发送信号进入 Exited；restart 等于 stop+start；rm 删除容器。容器退出后可以通过 start 重新启动，但删除后不可恢复。

### 面试题 2：docker stop 和 docker kill 有什么区别？

**参考答案**：

docker stop 是优雅停止，先发送 SIGTERM 信号给容器的 PID 1 进程，等待一段时间（默认 10 秒，可通过 -t 参数调整），如果进程仍未退出则发送 SIGKILL 强制杀死。docker kill 默认直接发送 SIGKILL 强制杀死进程，也可以通过 --signal 参数指定其他信号（如 `docker kill --signal=SIGTERM`）。生产环境中应优先使用 docker stop，给应用足够的时间完成清理工作（关闭连接、保存状态、完成正在处理的请求）。只有在应用无法正常停止时才使用 docker kill。

### 面试题 3：什么是 PID 1 问题？如何解决？

**参考答案**：

PID 1 问题是指当 Dockerfile 中使用 Shell 格式的 CMD 或 ENTRYPOINT 时，实际的进程树中 PID 1 是 /bin/sh 而非应用进程。这导致两个问题：1）docker stop 发送的 SIGTERM 被 sh 接收，sh 不会转发给子进程，应用无法优雅停止；2）僵尸进程问题，sh 不会自动回收子进程。解决方案：1）使用 Exec 格式（JSON 数组）的 CMD 和 ENTRYPOINT，如 `CMD ["nginx", "-g", "daemon off;"]`；2）使用轻量级 init 进程如 tini（`ENTRYPOINT ["tini", "--"]`），tini 会正确转发信号并回收僵尸进程。

### 面试题 4：如何限制容器的资源使用？底层原理是什么？

**参考答案**：

Docker 使用 Linux cgroup（控制组）来限制容器的资源使用。CPU 限制：`--cpus` 设置 CPU 核心数上限，底层使用 cpu.cfs_quota_us/cpu.cfs_period_us；`--cpuset-cpus` 绑定到特定 CPU 核心，使用 cpuset.cpus；`--cpu-shares` 设置相对权重，使用 cpu.shares。内存限制：`--memory` 设置硬限制，使用 memory.max（cgroup v2）；`--memory-reservation` 设置软限制，使用 memory.low。I/O 限制：`--device-read-bps`/`--device-write-bps` 限制读写速度。进程限制：`--pids-limit` 限制最大进程数，防止 fork bomb。当内存超过限制时触发 OOM killer，容器退出码为 137。

### 面试题 5：如何排查容器启动后立即退出的问题？

**参考答案**：

排查步骤：1）查看退出码：`docker inspect --format '{{.State.ExitCode}}' myapp`。退出码 0 表示进程主动退出（可能是一次性任务或应用逻辑问题），127 表示命令未找到（检查 ENTRYPOINT/CMD），126 表示权限问题。2）查看日志：`docker logs myapp`，通常能找到错误原因。3）查看详细状态：`docker inspect --format '{{json .State}}' myapp | jq .`。4）交互式调试：`docker run -it --rm myimage /bin/bash` 进入容器手动排查。5）检查 OOM：`docker inspect --format '{{.State.OOMKilled}}' myapp`。6）常见原因：CMD 使用 Shell 格式导致 shell 执行完就退出、应用缺少必要的环境变量、依赖服务不可用、配置文件错误。

### 面试题 6：docker exec 和 docker attach 有什么区别？

**参考答案**：

docker exec 在运行中的容器里创建新进程，该进程与容器共享 namespace 但不是 PID 1，退出时不影响容器。docker attach 附加到容器的主进程（PID 1），可以看到主进程的输出，但分离时可能影响容器（取决于信号配置）。关键区别：exec 创建新进程，attach 连接已有进程；exec 退出不影响容器，attach 可能影响；exec 可以同时多个，attach 多个可能冲突。生产环境建议：调试用 exec，查看日志用 docker logs，避免使用 attach。

### 面试题 7：如何配置容器的优雅停止？

**参考答案**：

配置优雅停止需要多个层面配合：1）Dockerfile 中使用 Exec 格式的 CMD/ENTRYPOINT，确保应用是 PID 1；2）应用代码中正确处理 SIGTERM 信号，完成清理工作后退出；3）设置合理的停止超时：`docker stop -t 30 myapp` 或 Dockerfile 中 `STOPSIGNAL`；4）对于不处理信号的遗留应用，使用 tini 作为 init 进程；5）健康检查配合重启策略，确保不健康的容器被自动替换。Go 应用使用 `signal.Notify` 监听 SIGTERM，Python 应用使用 `signal.signal`，Node.js 应用使用 `process.on('SIGTERM')`。

### 面试题 8：Docker 日志的最佳实践是什么？

**参考答案**：

Docker 日志管理最佳实践：1）在 daemon.json 中配置全局日志轮转（max-size 和 max-file），防止日志撑满磁盘——这是最常见的生产事故之一；2）选择合适的日志驱动：本地开发用 json-file，生产环境考虑 journald 或集中日志系统；3）应用日志输出到 stdout/stderr（Docker 默认收集），而非写文件；4）使用集中日志方案（ELK、Loki、Splunk）收集和分析日志；5）日志格式使用 JSON，便于解析和查询；6）设置合理的日志级别，避免 DEBUG 日志在生产环境输出过多。

### 面试题 9：什么是容器的 OOM Killer？如何避免？

**参考答案**：

OOM Killer 是 Linux 内核的内存保护机制。当系统内存不足且无法回收时，内核会选择一个进程杀死以释放内存。在容器中，当容器内存使用超过 `--memory` 限制时，内核会优先尝试回收容器的页面缓存，如果仍然不足则触发 OOM Killer 杀死容器进程，容器退出码为 137。避免方法：1）设置合理的内存限制，不要过小；2）设置 `--memory-reservation` 软限制，让内核提前回收；3）优化应用内存使用，避免内存泄漏；4）监控容器内存使用（`docker stats`），及时发现内存异常；5）对于关键服务，设置 `--oom-score-adj=-500` 降低被杀的优先级。

### 面试题 10：如何在不停止容器的情况下进入容器调试？

**参考答案**：

使用 `docker exec -it myapp /bin/bash` 进入容器（Alpine 镜像用 /bin/sh）。exec 会在容器中创建一个新进程，与容器共享 namespace 但不影响主进程。如果容器中没有 bash 或 sh（如 distroless 镜像），可以使用 debug 容器：`docker run -it --rm --pid=container:myapp --net=container:myapp --privileged busybox`，这会共享目标容器的 PID 和网络 namespace。其他调试工具：`docker logs` 查看日志、`docker top` 查看进程、`docker stats` 查看资源使用、`docker diff` 查看文件变更、`docker cp` 复制文件、`docker inspect` 查看详细配置。

---

## 📚 深入阅读

### 官方文档
- [Docker 容器文档](https://docs.docker.com/engine/containers/)
- [Docker 资源限制](https://docs.docker.com/config/containers/resource_constraints/)
- [Docker 日志驱动](https://docs.docker.com/config/containers/logging/configure/)
- [Docker 健康检查](https://docs.docker.com/engine/reference/builder/#healthcheck)

### Linux 内核相关
- [cgroups v2 文档](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
- [Linux Namespace 文档](https://man7.org/linux/man-pages/man7/namespaces.7.html)

### 推荐书籍
- 《Docker Deep Dive》— Nigel Poulton
- 《Container Security》— Liz Rice

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释容器的完整生命周期和状态转换
- [ ] 理解 docker stop 的信号发送机制（SIGTERM -> 等待 -> SIGKILL）
- [ ] 理解 PID 1 问题及其解决方案
- [ ] 掌握 cgroup 资源限制的原理和配置方法
- [ ] 理解容器日志驱动和日志管理策略
- [ ] 理解 exec 和 attach 的区别
- [ ] 理解健康检查的工作机制

### 实操检查点
- [ ] 能熟练使用容器管理命令（ps、inspect、logs、exec、stats）
- [ ] 能配置容器的 CPU、内存、I/O 资源限制
- [ ] 能配置容器日志轮转防止磁盘撑满
- [ ] 能使用 exec 进入容器调试
- [ ] 能配置和使用健康检查
- [ ] 能排查容器启动失败、OOM 等常见问题

### 能力验证标准
- [ ] 能在 5 分钟内诊断容器启动失败的原因
- [ ] 能回答 80% 以上的面试题
- [ ] 能为团队建立容器管理规范
- [ ] 能设计容器的资源限制策略
