# Day 10: systemd 服务管理 — systemctl/单元文件

> 📅 日期：2026-05-02
> 📖 学习主题：systemd 服务管理 — systemctl/单元文件
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 08-09（进程管理与信号机制）

## 🎯 学习目标

完成 Day 10 的学习后，你应该能够：
- 理解 systemd 的架构设计和为什么取代 SysV init
- 精通 Unit 文件的每个字段含义和最佳实践
- 区分 Service 类型（simple/forking/oneshot/notify/idle）并正确选择
- 使用 Timer 单元替代 cron 实现定时任务
- 使用 systemd-journal 进行高级日志查询和管理
- 使用 cgroup 资源限制控制 CPU、内存、I/O
- 独立编写生产级 systemd 服务文件

---

## 📖 核心知识点

### 1. systemd 架构深入

#### 1.1 为什么取代 SysV init

```
SysV init 的问题：

  1. 串行启动 → 启动慢
     服务按编号顺序依次启动，即使没有依赖关系
     一个服务卡住，后面的服务都得等

  2. 启动脚本复杂 → 维护困难
     /etc/init.d/ 下的脚本需要自己处理：
     start/stop/restart/reload/status
     PID 文件管理、日志重定向、环境变量...

  3. 只管理服务启动 → 功能有限
     不管理 socket、挂载点、定时器等
     无法做资源限制、安全沙箱

  4. 依赖管理弱 → 容易出问题
     只有简单的编号顺序（S01, S02...）
     无法表达复杂的依赖关系

systemd 的优势：

  1. 并行启动 → 启动快
     通过依赖关系和 socket 激活实现并行
     系统启动时间从分钟级降到秒级

  2. 声明式配置 → 维护简单
     一个 INI 格式的 unit 文件搞定一切
     不需要写 shell 脚本

  3. 全面管理 → 功能强大
     管理服务、挂载点、socket、定时器、设备等
     内置资源限制、安全沙箱、日志管理

  4. 依赖管理强 → 可靠
     声明式依赖（Requires/Wants/After/Before）
     自动解决依赖顺序
```

#### 1.2 systemd 架构图

```
                    ┌─────────────────────────────┐
                    │        systemd (PID 1)       │
                    │   系统和服务管理器            │
                    └──────────────┬───────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │              │           │           │              │
        ▼              ▼           ▼           ▼              ▼
   ┌─────────┐  ┌──────────┐ ┌─────────┐ ┌─────────┐  ┌──────────┐
   │systemd  │  │systemd   │ │systemd  │ │systemd  │  │systemd   │
   │-manager │  │-journald │ │-udevd   │  │-logind  │  │-resolved │
   │单元管理  │  │日志管理   │ │设备管理  │ │登录管理  │  │DNS解析    │
   └─────────┘  └──────────┘ └─────────┘ └─────────┘  └──────────┘

   Unit 类型：
   ┌──────────────────────────────────────────────────────┐
   │ .service  服务单元    （最常用）                       │
   │ .socket   套接字单元  （socket 激活）                  │
   │ .timer    定时器单元  （替代 cron）                    │
   │ .target   目标单元    （同步点/分组）                  │
   │ .mount    挂载单元    （文件系统挂载）                 │
   │ .automount 自动挂载   （按需挂载）                     │
   │ .swap     交换单元    （swap 管理）                    │
   │ .device   设备单元    （设备管理）                     │
   │ .path     路径单元    （路径监控）                     │
   │ .scope    范围单元    （外部创建的进程组）              │
   │ .slice    切片单元    （cgroup 资源分组）              │
   └──────────────────────────────────────────────────────┘
```

#### 1.3 并行启动原理

```
systemd 如何实现并行启动：

1. 分析所有 unit 文件的依赖关系
2. 构建依赖关系图（DAG，有向无环图）
3. 没有依赖关系的 unit 可以并行启动
4. 使用 socket 激活延迟服务初始化

socket 激活的妙处：
  → systemd 先创建 socket 并监听
  → 客户端连接时，systemd 才启动对应服务
  → 服务启动期间，连接请求在 socket 队列中等待
  → 对客户端来说，服务"立即可用"

  传统方式：
    启动 sshd → 创建 socket → 监听 → 接受连接
    （只有启动完成后才能接受连接）

  socket 激活：
    systemd 创建 socket → 监听 → 连接到达 → 启动 sshd
    （socket 创建和监听可以并行，服务按需启动）
```

### 2. Unit 文件详解

#### 2.1 Unit 文件位置

| 路径 | 优先级 | 说明 |
|------|--------|------|
| `/etc/systemd/system/` | 最高 | 管理员自定义的服务（推荐） |
| `/run/systemd/system/` | 中 | 运行时生成的服务（重启后丢失） |
| `/usr/lib/systemd/system/` | 最低 | 软件包安装的服务 |

```bash
# 查看 unit 文件的位置
systemctl cat nginx.service
# 显示实际使用的文件路径和内容

# 查看 unit 文件的加载顺序
systemd-analyze verify nginx.service
# 检查语法错误

# 覆盖软件包的默认配置（推荐方式）
sudo systemctl edit nginx.service
# 创建 /etc/systemd/system/nginx.service.d/override.conf
# 不修改原始文件，方便升级
```

#### 2.2 [Unit] 段详解

```ini
[Unit]
# === 基本信息 ===
Description=My Application Server          # 描述（systemctl status 显示）
Documentation=https://myapp.example.com    # 文档链接（可多个）
Documentation=man:myapp(8)

# === 依赖关系 ===
Requires=network.target                    # 强依赖：network 失败则 myapp 也失败
Wants=redis.service                        # 弱依赖：redis 失败不影响 myapp
After=network.target redis.service         # 启动顺序：在这些 unit 之后启动
Before=nginx.service                       # 启动顺序：在 nginx 之前启动
BindsTo=postgresql.service                 # 绑定依赖：postgresql 停止则 myapp 也停止

# === 条件检查 ===
ConditionPathExists=/opt/myapp/config.yml  # 条件：文件存在才启动
ConditionMemory=1G                         # 条件：内存 >= 1G 才启动
ConditionACPower=true                      # 条件：接通电源才启动

# === 冲突管理 ===
Conflicts=iptables.service                 # 冲突：不能与 iptables 同时运行
```

**依赖关系详解：**

| 指令 | 含义 | 失败时的行为 |
|------|------|-------------|
| `Requires` | 强依赖 | 依赖失败，本 unit 也失败 |
| `Wants` | 弱依赖 | 依赖失败，本 unit 继续运行 |
| `BindsTo` | 绑定依赖 | 依赖停止，本 unit 也停止 |
| `Conflicts` | 冲突 | 依赖运行，本 unit 不能运行 |
| `After` | 启动顺序 | 在依赖之后启动（不建立依赖关系） |
| `Before` | 启动顺序 | 在依赖之前启动（不建立依赖关系） |

```
依赖关系最佳实践：

  Requires + After：
    强依赖 + 启动顺序
    → 先启动依赖，再启动本服务
    → 依赖失败，本服务不启动

  Wants + After：
    弱依赖 + 启动顺序
    → 先启动依赖，再启动本服务
    → 依赖失败，本服务仍然启动

  推荐组合：
    → 大多数情况用 Wants + After
    → 只有确实需要强依赖时才用 Requires
    → 避免循环依赖
```

#### 2.3 [Service] 段详解

```ini
[Service]
# === 服务类型 ===
Type=simple                               # 服务类型（见下文详解）

# === 进程管理 ===
ExecStartPre=/usr/bin/myapp check-config  # 启动前执行的命令
ExecStart=/usr/bin/myapp serve            # 启动命令
ExecStartPost=/usr/bin/myapp post-init    # 启动后执行的命令
ExecReload=/bin/kill -HUP $MAINPID        # 重载命令
ExecStop=/usr/bin/myapp graceful-stop     # 停止命令
ExecStopPost=/usr/bin/myapp cleanup       # 停止后执行的命令

# === 进程标识 ===
PIDFile=/run/myapp.pid                    # PID 文件路径（forking 类型需要）

# === 重启策略 ===
Restart=on-failure                        # 重启条件
RestartSec=5                              # 重启前等待秒数
StartLimitInterval=300                    # 重启限制时间窗口（秒）
StartLimitBurst=5                         # 时间窗口内最多重启次数

# === 超时控制 ===
TimeoutStartSec=300                       # 启动超时（默认 90 秒）
TimeoutStopSec=30                         # 停止超时（默认 90 秒）
TimeoutSec=300                            # 同时设置启动和停止超时
WatchdogSec=0                             # 看门狗超时（0 = 禁用）

# === 运行身份 ===
User=myapp                                # 运行用户
Group=myapp                               # 运行组
SupplementaryGroups=www-data docker       # 附加组

# === 工作目录 ===
WorkingDirectory=/opt/myapp               # 工作目录
RootDirectory=/opt/myapp                  # 根目录（chroot）

# === 环境变量 ===
Environment=NODE_ENV=production           # 设置环境变量
EnvironmentFile=/opt/myapp/.env           # 从文件读取环境变量

# === 输出重定向 ===
StandardOutput=journal                    # stdout → journal
StandardError=journal                     # stderr → journal
SyslogIdentifier=myapp                    # journal 中的标识符

# === 资源限制 ===
LimitNOFILE=65535                         # 文件描述符限制
LimitNPROC=4096                           # 进程数限制
LimitCORE=infinity                        # core dump 大小限制

# === cgroup 资源限制（systemd v232+）===
CPUQuota=200%                             # CPU 配额（200% = 2 核）
CPUWeight=100                             # CPU 权重（默认 100）
MemoryMax=2G                              # 内存硬限制
MemoryHigh=1G                             # 内存软限制（超过后被回收）
MemorySwapMax=0                           # Swap 限制（0 = 禁用 Swap）
IOWeight=100                              # I/O 权重
TasksMax=512                              # 最大进程/线程数

# === 安全加固 ===
ProtectSystem=full                        # 只读挂载 /usr 和 /boot
ProtectHome=true                          # 隐藏 /home、/root、/run/user
NoNewPrivileges=true                      # 禁止获取新权限（setuid 等）
PrivateTmp=true                           # 独立的 /tmp 目录
PrivateDevices=true                       # 独立的设备命名空间
ProtectKernelTunables=true                # 禁止修改内核参数
ProtectKernelModules=true                 # 禁止加载内核模块
ProtectControlGroups=true                 # 禁止修改 cgroup
RestrictNamespaces=true                   # 限制命名空间操作
RestrictRealtime=true                     # 限制实时调度
RestrictSUIDSGID=true                     # 限制 setuid/setgid
SystemCallFilter=@system-service          # 系统调用白名单
CapabilityBoundingSet=CAP_NET_BIND_SERVICE # 能力限制
ReadWritePaths=/var/lib/myapp /var/log/myapp  # 可写路径

# === OOM 控制 ===
OOMScoreAdjust=-500                       # OOM 评分调整（-1000 ~ 1000）
OOMPolicy=stop                            # OOM 时的行为（stop/continue/kill）
```

#### 2.4 [Install] 段详解

```ini
[Install]
WantedBy=multi-user.target               # 被哪个 target 引用
RequiredBy=graphical.target              # 被哪个 target 强依赖
Also=myapp-monitor.service               # 启用本服务时同时启用的服务
Alias=my-application.service             # 别名
DefaultInstance=%i                       # 模板实例的默认值
```

```bash
# WantedBy 的作用：
# systemctl enable myapp.service 时：
# → 在 /etc/systemd/system/multi-user.target.wants/ 下
# → 创建指向 /usr/lib/systemd/system/myapp.service 的符号链接
# → 系统进入 multi-user.target 时自动启动 myapp

# 常用的 target：
# multi-user.target  → 无图形界面的多用户模式（服务器常用）
# graphical.target   → 带图形界面的多用户模式（桌面用）
# network-online.target → 网络完全就绪（比 network.target 更严格）
```

### 3. Service 类型详解

| Type | 含义 | 适用场景 | 特点 |
|------|------|---------|------|
| **simple** | ExecStart 启动的进程就是主进程 | 大多数现代服务 | 默认类型，最简单 |
| **forking** | ExecStart 启动的进程会 fork 并退出 | 传统守护进程（nginx、httpd） | 需要 PIDFile |
| **oneshot** | 执行一次就退出 | 初始化脚本、一次性任务 | 配合 RemainAfterExit |
| **notify** | 进程启动完成后通知 systemd | 需要精确就绪检测的服务 | sd_notify() |
| **idle** | 等待其他任务完成后才启动 | 控制台输出服务 | 很少使用 |
| **exec** | 类似 simple，但等待 execve() 完成 | 需要确认程序已开始执行 | 比 simple 更精确 |

```
如何选择 Service 类型：

  程序在前台运行，不 fork？
    → Type=simple（最常用）

  程序会 fork 成后台进程（daemonize）？
    → Type=forking + 设置 PIDFile
    → 或者用 -fg 参数让程序在前台运行，用 Type=simple

  只执行一次就退出？
    → Type=oneshot
    → 配合 RemainAfterExit=yes（退出后仍显示 active）

  程序支持 sd_notify 协议？
    → Type=notify（最精确的就绪检测）

  不确定？
    → Type=simple（默认，适用于大多数情况）
```

**simple vs exec 的区别：**

```
simple：systemd 在 fork() 后立即认为服务已启动
  → 即使 execve() 还没完成
  → 如果程序文件不存在，可能显示启动成功但实际失败

exec：systemd 等待 execve() 完成后才认为服务已启动
  → 确认程序已经开始执行
  → 更精确的就绪检测
  → systemd v240+ 支持
```

### 4. 依赖管理最佳实践

```bash
# === 常见的依赖组合 ===

# 数据库服务（被其他服务依赖）
[Unit]
Description=PostgreSQL Database
After=network.target
Wants=network.target

# Web 应用（依赖数据库）
[Unit]
Description=My Web Application
After=network.target postgresql.service
Wants=network.target
Requires=postgresql.service   # 强依赖数据库

# Nginx 反向代理（依赖 Web 应用）
[Unit]
Description=Nginx Reverse Proxy
After=network.target myapp.service
Wants=network.target
```

```bash
# 查看依赖关系
systemctl list-dependencies nginx.service      # 正向依赖（nginx 依赖什么）
systemctl list-dependencies nginx.service --reverse  # 反向依赖（谁依赖 nginx）

# 查看启动顺序
systemd-analyze critical-chain                  # 关键路径
systemd-analyze critical-chain nginx.service    # 指定服务的关键路径
```

### 5. Timer 单元（替代 cron）

#### 5.1 Timer 文件详解

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Daily Backup Timer

[Timer]
# === 触发时间 ===
OnCalendar=*-*-* 02:00:00          # 每天凌晨 2 点
# OnCalendar=Mon..Fri *-*-* 09:00:00  # 工作日 9 点
# OnCalendar=*-*-01 00:00:00         # 每月 1 号
# OnCalendar=hourly                   # 每小时
# OnCalendar=daily                    # 每天
# OnCalendar=weekly                   # 每周
# OnCalendar=monthly                  # 每月

# === 相对触发 ===
OnBootSec=5min                      # 系统启动后 5 分钟
OnUnitActiveSec=1h                  # 上次运行后 1 小时
OnUnitInactiveSec=30min             # 上次空闲后 30 分钟

# === 精度和随机化 ===
AccuracySec=1us                     # 触发精度（默认 1min）
RandomizedDelaySec=30min            # 随机延迟（避免同时触发）

# === 持久化 ===
Persistent=true                     # 错过的触发在下次启动时补上

# === 其他 ===
Unit=backup.service                 # 触发的服务（默认同名 .service）

[Install]
WantedBy=timers.target
```

#### 5.2 OnCalendar 时间格式

```
格式：DayOfWeek Year-Month-Day Hour:Minute:Second

示例：
  *-*-* 02:00:00          每天 02:00
  Mon *-*-* 02:00:00      每周一 02:00
  Mon..Fri *-*-* 09:00:00 工作日 09:00
  *-*-01 00:00:00         每月 1 号
  *-01,04,07,10-01 00:00:00  每季度第一天
  *-01-01 00:00:00        每年 1 月 1 号
  hourly                  每小时（0 分 0 秒）
  daily                   每天（00:00:00）
  weekly                  每周一（00:00:00）
  monthly                 每月 1 号（00:00:00）
  quarterly               每季度第一天
  yearly                  每年 1 月 1 号

特殊值：
  *       任何值
  1..5    范围（1 到 5）
  1,3,5   列表
  Mon..Fri  星期范围
```

#### 5.3 Timer 管理

```bash
# 创建 timer 文件
sudo tee /etc/systemd/system/backup.timer << 'EOF'
[Unit]
Description=Daily Backup Timer

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
RandomizedDelaySec=5min

[Install]
WantedBy=timers.target
EOF

# 创建对应的服务文件
sudo tee /etc/systemd/system/backup.service << 'EOF'
[Unit]
Description=Daily Backup

[Service]
Type=oneshot
ExecStart=/opt/scripts/backup.sh
User=backup
StandardOutput=journal
StandardError=journal
EOF

# 启用并启动 timer
sudo systemctl daemon-reload
sudo systemctl enable backup.timer
sudo systemctl start backup.timer

# 查看 timer 状态
systemctl status backup.timer
systemctl list-timers                    # 所有 timer
systemctl list-timers --all              # 包括未激活的

# 查看 timer 的下次触发时间
systemctl show backup.timer --property=NextElapseUSecRealtime
```

### 6. systemd-journal 日志管理

#### 6.1 journalctl 高级查询

```bash
# === 基本查询 ===
journalctl                              # 所有日志
journalctl -b                           # 当前启动
journalctl -b -1                        # 上次启动
journalctl --list-boots                 # 列出所有启动记录

# === 按服务过滤 ===
journalctl -u nginx.service             # 指定服务
journalctl -u nginx -u php-fpm          # 多个服务
journalctl _SYSTEMD_UNIT=nginx.service  # 使用字段过滤

# === 按时间过滤 ===
journalctl --since "10 minutes ago"
journalctl --since "2026-05-01 00:00" --until "2026-05-02 12:00"
journalctl --since today
journalctl --since yesterday

# === 按级别过滤 ===
journalctl -p err                       # 错误及以上
journalctl -p warning                   # 警告及以上
journalctl -p 0..3                      # emerg/alert/crit/err
# 级别：0=emerg 1=alert 2=crit 3=err 4=warning 5=notice 6=info 7=debug

# === 按进程过滤 ===
journalctl _PID=1234
journalctl _UID=1000
journalctl _COMM=nginx                  # 按命令名

# === 内核日志 ===
journalctl -k                           # 等价于 dmesg
journalctl -k -p err                    # 内核错误

# === 输出格式 ===
journalctl -o short                     # 默认（类似 syslog）
journalctl -o short-iso                 # ISO 时间格式
journalctl -o verbose                   # 完整字段
journalctl -o json                      # JSON 格式
journalctl -o json-pretty               # 格式化 JSON
journalctl -o cat                       # 只输出消息（无元数据）

# === 实时跟踪 ===
journalctl -f                           # 等价于 tail -f
journalctl -u nginx -f                  # 实时跟踪指定服务

# === 磁盘使用 ===
journalctl --disk-usage                 # 日志占用空间
journalctl --vacuum-size=500M           # 清理到 500M
journalctl --vacuum-time=30d            # 保留 30 天
journalctl --vacuum-files=10            # 最多 10 个文件

# === 高级过滤 ===
journalctl + _COMM=nginx + _COMM=php    # OR 逻辑
journalctl _COMM=nginx _PRIORITY=3      # AND 逻辑（nginx 且 error）
```

#### 6.2 日志持久化配置

```bash
# 默认情况下，journal 日志存储在 /run/log/journal/（内存，重启丢失）
# 持久化配置：

sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal

# 或编辑配置文件
sudo tee /etc/systemd/journald.conf << 'EOF'
[Journal]
Storage=persistent          # 持久化存储到 /var/log/journal/
Compress=yes                # 压缩日志
SystemMaxUse=2G             # 最大使用 2G 磁盘
SystemKeepFree=1G           # 保留 1G 可用空间
SystemMaxFileSize=50M       # 单个文件最大 50M
MaxRetentionSec=30day       # 保留 30 天
MaxFileSec=1day             # 每天轮转
ForwardToSyslog=yes         # 转发到 syslog
RateLimitIntervalSec=30s    # 速率限制时间窗口
RateLimitBurst=10000        # 时间窗口内最大日志条数
EOF

sudo systemctl restart systemd-journald
```

#### 6.3 日志转发到远程服务器

```bash
# 方法 1：使用 systemd-journal-remote
# 接收端：
sudo apt install systemd-journal-remote
sudo systemctl enable systemd-journal-remote.socket
sudo systemctl start systemd-journal-remote.socket

# 发送端：
sudo tee /etc/systemd/journal-upload.conf << 'EOF'
[Upload]
URL=http://logserver:19532
ServerKeyFile=/etc/ssl/private/journal-upload.pem
ServerCertificateFile=/etc/ssl/certs/journal-upload.pem
TrustedCertificateFile=/etc/ssl/ca/trusted.pem
EOF
sudo systemctl enable systemd-journal-upload
sudo systemctl start systemd-journal-upload

# 方法 2：使用 rsyslog 转发（更传统）
# 在 /etc/rsyslog.d/ 中配置转发规则
```

### 7. cgroup 资源限制

#### 7.1 什么是 cgroup

```
cgroup（Control Group）是 Linux 内核提供的资源管理机制：

  功能：
    → 限制进程组的资源使用（CPU、内存、I/O、网络等）
    → 统计资源使用情况
    → 控制进程组的行为（冻结、挂起等）

  systemd 集成：
    → systemd 自动为每个 service 创建 cgroup
    → 可以在 unit 文件中直接设置资源限制
    → 使用 systemctl set-property 动态调整

  cgroup v2（统一层级）：
    → 现代 Linux 发行版默认使用
    → 所有资源控制器在一个层级中
    → /sys/fs/cgroup/ 下查看
```

#### 7.2 CPU 资源限制

```ini
[Service]
# CPU 配额（百分比）
CPUQuota=200%          # 最多使用 2 个 CPU 核心
CPUQuota=50%           # 最多使用 0.5 个 CPU 核心

# CPU 权重（相对值，默认 100）
CPUWeight=200          # 获得 2 倍于默认的 CPU 时间
CPUWeight=50           # 获得 0.5 倍于默认的 CPU 时间

# 绑定到特定 CPU 核心
AllowedCPUs=0-3        # 只使用 CPU 0-3
AllowedCPUs=0,2        # 只使用 CPU 0 和 2

# CPU 亲和性（影响调度器选择）
CPUAffinity=0 1 2 3    # 设置 CPU 亲和性掩码
```

#### 7.3 内存资源限制

```ini
[Service]
# 内存硬限制（超过则触发 OOM）
MemoryMax=2G

# 内存软限制（超过后内核积极回收）
MemoryHigh=1G

# Swap 限制
MemorySwapMax=0        # 禁止使用 Swap
MemorySwapMax=1G       # 最多使用 1G Swap

# 最小内存保证
MemoryMin=512M         # 保证至少 512M

# 内存高水位（低版本兼容）
MemoryLimit=2G         # 旧版 cgroup v1 的写法
```

```
MemoryMax vs MemoryHigh：

  MemoryHigh = 软限制
    → 超过后，内核会积极回收该 cgroup 的内存
    → 进程不会被杀死，但性能会下降（因为内存被回收）
    → 类似于"建议不要超过这个值"

  MemoryMax = 硬限制
    → 超过后，触发 OOM Killer
    → 进程可能被杀死
    → 类似于"绝对不能超过这个值"

  推荐配置：
    MemoryHigh = 80% 的预期最大内存
    MemoryMax = 100% 的预期最大内存
    → 先触发软限制，给进程一个缓冲区
```

#### 7.4 I/O 资源限制

```ini
[Service]
# I/O 权重（相对值，默认 100）
IOWeight=200           # 获得 2 倍于默认的 I/O 带宽
IOWeight=50            # 获得 0.5 倍于默认的 I/O 带宽

# 设备级 I/O 限制
IOReadBandwidthMax=/dev/sda 10M    # 读带宽限制 10MB/s
IOWriteBandwidthMax=/dev/sda 5M    # 写带宽限制 5MB/s
IOReadIOPSMax=/dev/sda 1000        # 读 IOPS 限制
IOWriteIOPSMax=/dev/sda 500        # 写 IOPS 限制
```

#### 7.5 动态调整资源限制

```bash
# 运行时调整资源限制（不需要重启服务）
sudo systemctl set-property myapp.service CPUQuota=300%
sudo systemctl set-property myapp.service MemoryMax=4G

# 持久化（写入 unit 文件）
sudo systemctl set-property --runtime myapp.service CPUQuota=300%  # 运行时
sudo systemctl set-property myapp.service CPUQuota=300%            # 持久化

# 查看当前资源限制
systemctl show myapp.service --property=CPUQuota
systemctl show myapp.service --property=MemoryMax

# 查看资源使用情况
systemd-cgtop                               # 类似 top 的 cgroup 监控
systemd-cgls                                # cgroup 树形结构
```

### 8. systemd-analyze 启动分析

```bash
# === 启动时间分析 ===
systemd-analyze                         # 总启动时间
# Output: Startup finished in 2.150s (kernel) + 12.345s (userspace) = 14.495s

# === 最慢的服务 ===
systemd-analyze blame | head -20
# 输出示例：
#          12.345s apt-daily.service
#           5.678s NetworkManager-wait-online.service
#           2.345s snapd.service
#           1.234s accounts-daemon.service

# === 关键路径 ===
systemd-analyze critical-chain
# 显示启动时间线中最长的依赖链

systemd-analyze critical-chain nginx.service
# 指定服务的关键路径

# === 生成启动图表 ===
systemd-analyze plot > /tmp/startup.svg
# 生成 SVG 格式的启动时间线

# === 验证 unit 文件 ===
systemd-analyze verify /etc/systemd/system/myapp.service
# 检查语法和依赖关系

# === 安全评分 ===
systemd-analyze security nginx.service
# 输出安全评分（0-10，越低越安全）
```

---

## 🏗️ SRE 实战案例

### 案例 1：编写生产级 systemd 服务文件

```ini
# /etc/systemd/system/myapp.service
# 生产级 Web 应用服务配置

[Unit]
Description=My Web Application Server
Documentation=https://docs.myapp.example.com
After=network-online.target postgresql.service redis.service
Wants=network-online.target
Requires=postgresql.service

[Service]
Type=notify
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp

# 环境变量
Environment=NODE_ENV=production
Environment=PORT=8080
EnvironmentFile=-/opt/myapp/.env

# 启动命令
ExecStartPre=/usr/bin/node /opt/myapp/scripts/pre-start.js
ExecStart=/usr/bin/node /opt/myapp/server.js
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/usr/bin/node /opt/myapp/scripts/graceful-stop.js

# 重启策略
Restart=on-failure
RestartSec=5
StartLimitInterval=300
StartLimitBurst=5

# 超时
TimeoutStartSec=60
TimeoutStopSec=30
WatchdogSec=30

# 资源限制
CPUQuota=200%
MemoryMax=2G
MemoryHigh=1536M
MemorySwapMax=0
TasksMax=512
LimitNOFILE=65535

# 安全加固
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
RestrictRealtime=true
RestrictSUIDSGID=true
SystemCallFilter=@system-service
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
ReadWritePaths=/var/lib/myapp /var/log/myapp /tmp/myapp

# OOM 控制
OOMScoreAdjust=-500

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=myapp

[Install]
WantedBy=multi-user.target
```

### 案例 2：服务启动失败排查流程

```bash
# 标准排查流程：

# 第 1 步：查看服务状态
systemctl status myapp.service
# 关注：
# - Active: failed (Result: exit-code)
# - Process: exit-code=1/FAILURE
# - 日志输出

# 第 2 步：查看详细日志
journalctl -u myapp.service -n 50 --no-pager
journalctl -u myapp.service --since "5 minutes ago"

# 第 3 步：检查 unit 文件语法
systemd-analyze verify /etc/systemd/system/myapp.service

# 第 4 步：检查依赖关系
systemctl list-dependencies myapp.service
# 确认所有依赖都是 active 状态

# 第 5 步：手动启动测试
sudo -u myapp /usr/bin/node /opt/myapp/server.js
# 看是否有报错

# 第 6 步：检查文件权限
ls -la /opt/myapp/
ls -la /var/log/myapp/
id myapp

# 第 7 步：检查端口占用
ss -tlnp | grep 8080

# 第 8 步：检查 SELinux/AppArmor
sudo ausearch -m avc -ts recent
sudo dmesg | grep -i "apparmor\|selinux"
```

### 案例 3：定时任务从 cron 迁移到 systemd timer

```bash
# 原始 cron 任务：
# 0 2 * * * /opt/scripts/backup.sh >> /var/log/backup.log 2>&1

# 步骤 1：创建 service 文件
sudo tee /etc/systemd/system/backup.service << 'EOF'
[Unit]
Description=Daily Backup
After=network-online.target

[Service]
Type=oneshot
User=backup
ExecStart=/opt/scripts/backup.sh
StandardOutput=journal
StandardError=journal
Nice=19
IOWeight=10

[Install]
WantedBy=multi-user.target
EOF

# 步骤 2：创建 timer 文件
sudo tee /etc/systemd/system/backup.timer << 'EOF'
[Unit]
Description=Daily Backup Timer

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
RandomizedDelaySec=5min

[Install]
WantedBy=timers.target
EOF

# 步骤 3：启用并启动
sudo systemctl daemon-reload
sudo systemctl enable backup.timer
sudo systemctl start backup.timer

# 步骤 4：验证
systemctl list-timers backup.timer
journalctl -u backup.service -n 20

# 步骤 5：移除旧的 cron 任务
crontab -e  # 删除对应行
```

---

## 💻 实战练习

### 练习 1：创建一个简单的 systemd 服务

```bash
# 1. 创建 Python 测试脚本
sudo tee /opt/hello.py << 'EOF'
#!/usr/bin/env python3
import time
import signal
import sys

def handler(signum, frame):
    print("收到终止信号，正在清理...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGHUP, handler)

print("服务启动")
while True:
    print("服务运行中...")
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
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 3. 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable hello
sudo systemctl start hello

# 4. 检查状态
systemctl status hello
journalctl -u hello -f
```

### 练习 2：分析启动性能

```bash
# 查看启动时间
systemd-analyze

# 查看各服务启动耗时
systemd-analyze blame | head -20

# 查看关键链
systemd-analyze critical-chain

# 生成启动图表
systemd-analyze plot > /tmp/startup.svg

# 安全评分
systemd-analyze security ssh.service
```

### 练习 3：创建定时任务

```bash
# 创建一个每 5 分钟执行的定时任务

# 1. 创建服务
sudo tee /etc/systemd/system/heartbeat.service << 'EOF'
[Unit]
Description=Heartbeat Check

[Service]
Type=oneshot
ExecStart=/bin/echo "Heartbeat at $(date)"
EOF

# 2. 创建 timer
sudo tee /etc/systemd/system/heartbeat.timer << 'EOF'
[Unit]
Description=Heartbeat Timer

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

# 3. 启用
sudo systemctl daemon-reload
sudo systemctl enable heartbeat.timer
sudo systemctl start heartbeat.timer

# 4. 验证
systemctl list-timers heartbeat.timer
journalctl -u heartbeat.service -f
```

---

## 🎯 面试题精选

### 面试题 1：systemd 和 SysV init 的区别是什么？

**参考答案：**

1. **启动方式**：SysV init 串行启动，systemd 并行启动（通过依赖图和 socket 激活）
2. **配置方式**：SysV init 用 shell 脚本（/etc/init.d/），systemd 用声明式 unit 文件
3. **依赖管理**：SysV init 用编号顺序，systemd 用 Requires/Wants/After 等声明式依赖
4. **功能范围**：SysV init 只管服务启动，systemd 管理服务、挂载、socket、定时器等
5. **资源管理**：systemd 内置 cgroup 资源限制
6. **日志管理**：systemd 内置 journald
7. **进程监控**：systemd 自动重启失败的服务

### 面试题 2：如何实现服务自动重启？

**参考答案：**

在 [Service] 段配置：
```ini
Restart=on-failure     # 失败时重启
RestartSec=5           # 等待 5 秒后重启
StartLimitInterval=300 # 5 分钟内
StartLimitBurst=5      # 最多重启 5 次
```

Restart 选项：
- no：不重启（默认）
- on-success：正常退出时重启
- on-failure：异常退出时重启
- on-abnormal：信号/超时/看门狗时重启
- on-abort：收到未捕获信号时重启
- always：总是重启

### 面试题 3：cgroup 的作用是什么？

**参考答案：**

cgroup（Control Group）是 Linux 内核的资源管理机制，用于：
1. **资源限制**：限制进程组的 CPU、内存、I/O 使用
2. **资源统计**：统计进程组的资源使用情况
3. **进程控制**：冻结、挂起进程组

systemd 自动为每个 service 创建 cgroup，可以在 unit 文件中直接设置 CPUQuota、MemoryMax、IOWeight 等资源限制。容器技术（Docker）也基于 cgroup 实现资源隔离。

### 面试题 4：Type=simple 和 Type=forking 有什么区别？

**参考答案：**

Type=simple：ExecStart 启动的进程就是主进程，systemd 认为服务在 fork 后立即启动。适用于前台运行的程序。

Type=forking：ExecStart 启动的进程会 fork 出子进程然后退出，子进程才是真正的服务进程。需要设置 PIDFile 指向子进程的 PID。适用于传统的守护进程（如 nginx 默认模式）。

现代实践：让程序在前台运行（如 nginx -g 'daemon off;'），使用 Type=simple。

### 面试题 5：如何查看服务的日志？

**参考答案：**

```bash
journalctl -u <service>.service           # 查看所有日志
journalctl -u <service> -f                # 实时跟踪
journalctl -u <service> --since today     # 今天的日志
journalctl -u <service> -p err            # 只看错误
journalctl -u <service> -n 100            # 最近 100 行
```

### 面试题 6：Timer 和 cron 有什么区别？

**参考答案：**

1. **集成性**：Timer 与 systemd 深度集成，可以使用 systemd 的依赖管理、日志、资源限制
2. **精度**：Timer 支持毫秒级精度，cron 只能到分钟
3. **随机化**：Timer 支持 RandomizedDelaySec 避免同时触发
4. **持久化**：Persistent=true 可以在系统启动后补上错过的触发
5. **日志**：Timer 的输出自动进入 journal，方便查询
6. **管理**：使用 systemctl 统一管理，比 crontab 更直观

---

## 📚 深入阅读

- [systemd 官方文档](https://www.freedesktop.org/wiki/Software/systemd/) — 最权威的参考
- `man systemd.service` — 服务单元配置
- `man systemd.timer` — 定时器单元
- `man systemd.exec` — 执行环境配置
- `man systemd.resource-control` — 资源控制
- `man journalctl` — 日志查询
- [systemd by Example](https://systemd-by-example.com/) — 交互式学习
- [Lennart Poettering — systemd for Administrators](https://0pointer.de/blog/projects/systemd-for-admins-1.html) — 作者系列文章

---

## ✅ 自检清单

- [ ] 理解 systemd 的架构和并行启动原理
- [ ] 能解释 [Unit]、[Service]、[Install] 每个字段的含义
- [ ] 能区分 simple/forking/oneshot/notify 并正确选择
- [ ] 掌握 Requires/Wants/After/Before 依赖管理
- [ ] 能创建和管理 Timer 定时任务
- [ ] 能使用 journalctl 进行高级日志查询
- [ ] 理解 cgroup 资源限制（CPUQuota、MemoryMax）
- [ ] 能编写生产级 systemd 服务文件
- [ ] 能独立排查服务启动失败问题
- [ ] 能将 cron 任务迁移到 systemd timer
