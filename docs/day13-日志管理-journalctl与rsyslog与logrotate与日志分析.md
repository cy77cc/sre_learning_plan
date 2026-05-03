# Day 13: 日志管理 — journalctl/rsyslog/logrotate/日志分析

> 📅 日期：2026-04-29
> 📖 学习主题：日志管理 — journalctl/rsyslog/logrotate/日志分析
> ⏰ 计划学习时间：3-4 小时
> 📋 前置知识：Day 10（systemd 服务管理）、Day 12（磁盘管理）

---

## 🎯 学习目标

完成 Day 13 的学习后，你应该掌握：
- 理解 Linux 日志体系的完整架构（systemd-journald → rsyslog → 文件）
- 精通 journalctl 的高级查询（按服务、优先级、时间、PID、字段过滤）
- 掌握 rsyslog 的配置语法（facility.severity、模板、远程转发）
- 理解 logrotate 的工作原理和配置（postrotate 为什么需要 reload 服务）
- 能够设计集中日志收集方案（rsyslog → Elasticsearch）
- 能够处理生产环境中的日志爆满、磁盘撑满等问题
- 理解结构化日志的优势和实现方式

---

## 📖 核心知识点

### 1. Linux 日志体系架构

Linux 有两套日志系统并行工作，理解它们的关系是日志管理的基础：

```
┌──────────────────────────────────────────────────────────────┐
│                    应用程序                                    │
│  (Nginx, MySQL, SSH, Cron, 自定义应用...)                     │
└──────┬───────────────────────────────┬───────────────────────┘
       │                               │
       │ syslog() API                  │ stdout/stderr
       │ /dev/log socket               │
       ▼                               ▼
┌──────────────┐              ┌────────────────────┐
│  rsyslogd    │◄─────────────│  systemd-journald   │
│  (传统syslog) │              │  (systemd 原生)      │
│              │              │                     │
│  收集来源：   │              │  收集来源：           │
│  - /dev/log  │              │  - /dev/log         │
│  - TCP/UDP   │              │  - /dev/kmsg        │
│  - 文件监控   │              │  - stdout/stderr    │
│              │              │  - audit            │
│      │       │              │         │           │
│      ▼       │              │         ▼           │
│  /var/log/   │              │  /var/log/journal/  │
│  文本文件     │              │  二进制格式          │
│              │              │                     │
│  优势：       │              │  优势：              │
│  - 人类可读   │              │  - 结构化查询        │
│  - 远程转发   │              │  - 自动索引          │
│  - 灵活路由   │              │  - 启动早期日志      │
└──────────────┘              └────────────────────┘
```

**两套系统的关系：**
- journald 是 systemd 的原生日志收集器，优先接收所有日志
- rsyslog 是传统的 syslog 实现，功能更强大（远程转发、灵活路由）
- 两者可以共存，journald 可以将日志转发给 rsyslog
- 生产环境通常两者配合使用：journald 收集 + rsyslog 路由和转发

#### 1.1 /var/log 目录详解

| 日志路径 | 来源 | 用途 | 关键字段 |
|---------|------|------|---------|
| `/var/log/syslog` | rsyslog | 系统综合日志（Ubuntu/Debian） | 所有 syslog 消息 |
| `/var/log/messages` | rsyslog | 系统综合日志（RHEL/CentOS） | 同 syslog |
| `/var/log/auth.log` | PAM/SSH/sudo | 认证与授权（Ubuntu） | 登录、sudo、SSH 密钥 |
| `/var/log/secure` | PAM/SSH/sudo | 认证与授权（RHEL） | 同 auth.log |
| `/var/log/kern.log` | 内核 | 内核消息 | 硬件错误、OOM、驱动 |
| `/var/log/dmesg` | 内核 | 启动时内核消息 | 硬件检测、驱动加载 |
| `/var/log/dpkg.log` | dpkg | 软件包安装/卸载（Debian） | apt install/remove 记录 |
| `/var/log/yum.log` | yum | 软件包安装/卸载（RHEL） | yum install/remove 记录 |
| `/var/log/boot.log` | systemd | 启动过程日志 | 服务启动状态 |
| `/var/log/cron.log` | cron | 定时任务日志 | 任务执行记录 |
| `/var/log/maillog` | postfix/sendmail | 邮件系统日志 | 邮件发送/接收记录 |
| `/var/log/wtmp` | login | 成功登录记录 | 二进制，用 last 读取 |
| `/var/log/btmp` | login | 失败登录记录 | 二进制，用 lastb 读取 |
| `/var/log/lastlog` | login | 最后登录信息 | 二进制，用 lastlog 读取 |
| `/var/log/journal/` | journald | systemd 二进制日志 | 所有 systemd 服务日志 |

```bash
# 查看日志文件大小
du -sh /var/log/* 2>/dev/null | sort -rh | head -20

# 查看哪些日志文件在持续增长
watch -n 5 'ls -lhS /var/log/*.log /var/log/*.log.* 2>/dev/null | head -10'

# 查看被删除但仍被进程占用的日志文件（空间未释放）
sudo lsof +L1 2>/dev/null | grep '/var/log'
```

---

### 2. systemd-journald 深入

#### 2.1 journald 架构

journald 是 systemd 的原生日志收集器，收集所有 systemd 管理的服务的日志：

```
日志来源：
  /dev/kmsg     ← 内核消息
  /dev/log      ← syslog API 消息
  stdout/stderr ← 服务的标准输出/错误
  audit         ← 审计子系统消息
       │
       ▼
┌─────────────────┐
│  systemd-journald │
│  (PID 1 的子进程) │
│                   │
│  处理：            │
│  - 添加元数据      │
│  - 索引            │
│  - 压缩            │
│  - 密封（Seal）    │
└────────┬──────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ /run/log/journal/│     │ /var/log/journal/ │
│ (内存，重启丢失)  │     │ (磁盘，持久化)     │
└─────────────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│ 转发到 rsyslog   │ （可选，通过 ForwardToSyslog=yes）
└─────────────────┘
```

#### 2.2 journalctl 核心用法

```bash
# === 基础查询 ===
journalctl                    # 查看所有日志（分页，从旧到新）
journalctl -r                 # 反向排序（从新到旧）
journalctl -f                 # 实时跟踪（类似 tail -f）
journalctl -n 50              # 最近 50 条
journalctl --no-pager         # 不分页，直接输出（适合脚本）
journalctl -e                 # 跳转到末尾

# === 按启动次数 ===
journalctl -b                 # 当前启动的日志
journalctl -b -1              # 上次启动的日志
journalctl -b -2              # 上上次启动的日志
journalctl --list-boots       # 列出所有启动记录

# === 按时间范围 ===
journalctl --since "2026-05-01 10:00:00" --until "2026-05-01 11:00:00"
journalctl --since "1 hour ago"
journalctl --since "2026-05-01" --until "2026-05-02"
journalctl --since yesterday --until today
journalctl --since "2026-05-01 10:00" --until "30 min ago"

# === 按服务/单元 ===
journalctl -u nginx           # nginx 服务的所有日志
journalctl -u nginx -f        # 实时跟踪 nginx
journalctl -u nginx --since "30 min ago"

# 多个服务同时查看
journalctl -u nginx -u php-fpm --since "1h ago"

# 查看所有 systemd 单元的日志
journalctl -u '*' --since "1h ago"

# === 按日志级别 ===
# emerg(0) > alert(1) > crit(2) > err(3) > warning(4) > notice(5) > info(6) > debug(7)
journalctl -p err             # 错误及以上级别
journalctl -p 3               # 同上（数字形式）
journalctl -p warning..err    # 范围：warning 到 err
journalctl -p info            # info 及以上级别

# === 按进程/PID ===
journalctl _PID=1234
journalctl _COMM=nginx        # 按进程名
journalctl _UID=0             # 按用户 ID（0 = root）
journalctl _GID=1000          # 按组 ID
journalctl _EXE=/usr/sbin/sshd  # 按可执行文件路径

# === 按内核日志 ===
journalctl -k                 # 仅内核消息（等价于 dmesg）
journalctl -k --since "10 min ago"

# === 结构化输出 ===
journalctl -o json            # JSON 格式（适合程序解析）
journalctl -o json-pretty     # 美化的 JSON
journalctl -o verbose         # 显示所有字段（最详细）
journalctl -o cat             # 仅消息内容（无时间/主机前缀）
journalctl -o short-iso       # ISO 8601 时间格式

# 查看某条日志的所有元数据字段
journalctl -n 1 -o verbose
```

#### 2.3 journalctl 高级过滤（字段匹配）

journalctl 支持按任意结构化字段过滤，这是它比传统日志文件强大的地方：

```bash
# 列出所有可用字段
journalctl -F _SYSTEMD_UNIT   # 所有出现过的 systemd 单元名
journalctl -F _COMM           # 所有出现过的进程名
journalctl -F _UID            # 所有出现过的用户 ID

# 组合过滤（AND 关系）
journalctl _SYSTEMD_UNIT=nginx.service _PID=1234
journalctl _SYSTEMD_UNIT=sshd.service PRIORITY=3  # SSH 错误

# 按源文件过滤
journalctl SYSLOG_FACILITY=auth    # 认证相关
journalctl SYSLOG_FACILITY=daemon  # 守护进程相关
journalctl SYSLOG_FACILITY=mail    # 邮件相关

# 按 syslog 标识符
journalctl SYSLOG_IDENTIFIER=mysqld

# 使用 _TRANSPORT 过滤日志来源
journalctl _TRANSPORT=journal    # 通过 journal API
journalctl _TRANSPORT=syslog     # 通过 syslog API
journalctl _TRANSPORT=kernel     # 内核消息
```

**journalctl 输出字段说明：**

| 字段 | 说明 |
|------|------|
| `_PID` | 进程 ID |
| `_COMM` | 进程名（命令名） |
| `_EXE` | 可执行文件路径 |
| `_CMDLINE` | 完整命令行 |
| `_SYSTEMD_UNIT` | systemd 单元名 |
| `_UID` | 用户 ID |
| `_GID` | 组 ID |
| `_HOSTNAME` | 主机名 |
| `_TRANSPORT` | 日志传输方式 |
| `PRIORITY` | 优先级（0-7） |
| `SYSLOG_FACILITY` | syslog 设施 |
| `SYSLOG_IDENTIFIER` | syslog 标识符 |
| `MESSAGE` | 日志消息内容 |
| `_SOURCE_REALTIME_TIMESTAMP` | 源时间戳（微秒） |

#### 2.4 journal 空间管理

```bash
# 查看当前占用
journalctl --disk-usage
# Archives take up: 320.0M in the file system

# 清理策略
sudo journalctl --vacuum-size=500M       # 保留最近 500MB
sudo journalctl --vacuum-time=7d         # 只保留最近 7 天
sudo journalctl --vacuum-files=5         # 只保留 5 个归档文件

# 配置持久化策略
sudo vim /etc/systemd/journald.conf
```

**/etc/systemd/journald.conf 关键配置：**

```ini
[Journal]
Storage=persistent          # persistent|auto|volatile|none
# persistent: 始终写入 /var/log/journal/
# auto: 如果 /var/log/journal/ 存在就写入，否则只写内存
# volatile: 只写内存（重启丢失）
# none: 不记录日志

SystemMaxUse=500M           # 磁盘最大占用（如 500M, 2G）
SystemKeepFree=1G           # 保持至少 1G 可用空间
SystemMaxFileSize=50M       # 单个 journal 文件最大大小
SystemMaxFiles=5            # 最大归档文件数
MaxRetentionSec=30day       # 最长保留时间
MaxFileSec=1day             # 单个 journal 文件最大时长
ForwardToSyslog=yes         # 是否转发到 rsyslog
Compress=yes                # 是否压缩日志
Seal=yes                    # 是否使用 FSS 密封（防篡改）
RateLimitIntervalSec=30s    # 速率限制时间窗口
RateLimitBurst=10000        # 时间窗口内最大消息数
```

```bash
# 修改配置后重启 journald
sudo systemctl restart systemd-journald

# 启用持久化存储
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald

# 验证持久化状态
ls -la /var/log/journal/
```

---

### 3. rsyslog 深入

#### 3.1 rsyslog 工作原理

rsyslog 是 syslog 协议的高性能实现，核心是 **输入 → 过滤 → 输出** 的管道模型：

```
消息来源（输入模块）           过滤器                  输出（动作）
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│ imuxsock         │     │              │     │ omfile            │
│ (本地 /dev/log)  │────>│  facility    │────>│ 写入文件           │
│                  │     │  .severity   │     │                  │
│ imklog           │     │              │     │ omfwd            │
│ (内核日志)        │────>│  属性过滤    │────>│ 转发远程           │
│                  │     │  (property)  │     │                  │
│ imtcp / imudp    │     │              │     │ ommysql          │
│ (远程日志接收)    │────>│  表达式过滤  │────>│ 写入数据库         │
│                  │     │  (expression)│     │                  │
│ imfile           │     │              │     │ omelasticsearch  │
│ (文件监控)        │────>│              │────>│ 写入 ES           │
└─────────────────┘     └──────────────┘     └──────────────────┘
```

#### 3.2 Facility 和 Severity

**Facility（设施）— 日志来源分类：**

| Facility | 数字 | 用途 | 说明 |
|----------|------|------|------|
| `kern` | 0 | 内核消息 | 不能被用户进程产生 |
| `user` | 1 | 用户进程 | 默认 facility |
| `mail` | 2 | 邮件系统 | postfix/sendmail |
| `daemon` | 3 | 系统守护进程 | 大多数服务 |
| `auth` | 4 | 认证/授权 | login, su, sudo |
| `syslog` | 5 | syslog 自身 | rsyslog 内部消息 |
| `lpr` | 6 | 打印系统 | 打印队列 |
| `news` | 7 | 新闻系统 | Usenet |
| `uucp` | 8 | UUCP | Unix-to-Unix Copy |
| `cron` | 9 | 定时任务 | crond |
| `authpriv` | 10 | 私有认证 | SSH, sudo（敏感） |
| `ftp` | 11 | FTP | vsftpd, proftpd |
| `local0-7` | 16-23 | 自定义用途 | 应用程序自定义 |

**Severity（严重级别）— 从高到低：**

| 级别 | 关键字 | 数字 | 说明 |
|------|--------|------|------|
| 0 | emerg | EMERGENCY | 系统不可用 |
| 1 | alert | ALERT | 需要立即处理 |
| 2 | crit | CRITICAL | 严重条件 |
| 3 | err | ERROR | 错误条件 |
| 4 | warning | WARNING | 警告条件 |
| 5 | notice | NOTICE | 正常但重要 |
| 6 | info | INFO | 信息性消息 |
| 7 | debug | DEBUG | 调试级别 |

**选择器语法：`facility.severity`**
```bash
*.info              # 所有 facility 的 info 及以上级别
auth.err            # auth 的 err 及以上
mail.*              # mail 的所有级别
*.info;mail.none    # 所有 info 级别，但排除 mail
*.info;auth,authpriv.none    # 所有 info，排除 auth
local0.*            # local0 的所有级别
kern.*              # 内核的所有级别
```

#### 3.3 rsyslog 配置文件

```bash
# 主配置文件
cat /etc/rsyslog.conf

# 配置文件结构：
# 1. 模块加载区
# 2. 全局配置区
# 3. 规则区
# 4. 包含其他配置文件

# /etc/rsyslog.d/ 下的 *.conf 会按字母顺序加载
# 建议用数字前缀控制加载顺序：
# /etc/rsyslog.d/10-default.conf    ← 默认规则
# /etc/rsyslog.d/50-myapp.conf     ← 应用日志
# /etc/rsyslog.d/99-remote.conf    ← 远程转发
```

#### 3.4 rsyslog 配置语法详解

```bash
# === 传统语法（旧版，仍然支持）===
# 选择器    动作
auth.*                /var/log/auth.log
authpriv.*            /var/log/auth.log
*.info;auth,authpriv.none    /var/log/messages

# === RainerScript 语法（新版，推荐）===
# 基于属性的过滤
if $programname == 'nginx' then {
    action(type="omfile" file="/var/log/nginx/app.log")
    stop
}

# 基于优先级的过滤
if $syslogseverity <= 3 then {
    action(type="omfile" file="/var/log/errors.log")
}

# 基于正则表达式的过滤
if $msg contains 'error' or $msg contains 'fail' then {
    action(type="omfile" file="/var/log/suspicious.log")
}
```

#### 3.5 模板（Template）

模板定义日志的输出格式，是 rsyslog 最强大的功能之一：

```bash
# 在 /etc/rsyslog.d/ 中创建自定义配置
sudo cat > /etc/rsyslog.d/50-templates.conf << 'RSYSLOG'
# 模板定义

# 模板 1：按主机名和程序名分目录存储
template(name="RemotePerHost" type="string"
    string="/var/log/remote/%HOSTNAME%/%PROGRAMNAME%.log")

# 模板 2：JSON 格式（适合发送到 Elasticsearch）
template(name="JSONFormat" type="list") {
    constant(value="{")
    constant(value="\"timestamp\":\"")     property(name="timereported" dateFormat="rfc3339")
    constant(value="\",\"host\":\"")       property(name="hostname")
    constant(value="\",\"program\":\"")    property(name="programname")
    constant(value="\",\"severity\":\"")   property(name="syslogseverity-text")
    constant(value="\",\"facility\":\"")   property(name="syslogfacility-text")
    constant(value="\",\"message\":")      property(name="msg" format="json")
    constant(value="}\n")
}

# 模板 3：带时间戳的文件名
template(name="DailyLogFile" type="string"
    string="/var/log/apps/%programname%-%$year%-%$month%-%$day%.log")

# 使用模板
# 按主机名分目录存储远程日志
*.* action(type="omfile" dynaFile="RemotePerHost")

# JSON 格式输出到文件
*.* action(type="omfile" file="/var/log/all-json.log" template="JSONFormat")

# 按天轮转的应用日志
local0.* action(type="omfile" dynaFile="DailyLogFile")
RSYSLOG
```

#### 3.6 远程日志收集

```bash
# ===== 日志服务器配置（接收端）=====
sudo cat > /etc/rsyslog.d/50-server.conf << 'RSYSLOG'
# 加载 TCP 输入模块
module(load="imtcp")
module(load="imudp")

# 监听端口
input(type="imtcp" port="514")
input(type="imudp" port="514")

# 模板：按主机名分目录存储
template(name="RemoteHost" type="string"
    string="/var/log/remote/%HOSTNAME%/%PROGRAMNAME%.log")

# 所有远程日志写入对应文件
if $fromhost-ip != '127.0.0.1' then {
    action(type="omfile" dynaFile="RemoteHost")
    stop
}
RSYSLOG

# 创建日志目录
sudo mkdir -p /var/log/remote
sudo chown syslog:syslog /var/log/remote

# ===== 客户端配置（发送端）=====
sudo cat > /etc/rsyslog.d/50-client.conf << 'RSYSLOG'
# TCP 转发（可靠，推荐）
*.* action(type="omfwd"
    target="192.168.1.100"
    port="514"
    protocol="tcp"
    queue.type="LinkedList"
    queue.filename="fwd_queue"
    queue.maxdiskspace="1g"
    queue.saveonshutdown="on"
    action.resumeRetryCount="-1"
)
RSYSLOG

# UDP 转发（简单，不可靠）
# *.* @192.168.1.100:514          # @ = UDP
# *.* @@192.168.1.100:514         # @@ = TCP
```

#### 3.7 队列和故障恢复

rsyslog 的队列机制确保在远程服务器不可用时不会丢失日志：

```bash
# 队列配置详解
action(type="omfwd"
    target="log-server.example.com"
    port="514"
    protocol="tcp"

    # 队列类型
    queue.type="LinkedList"       # LinkedList=内存队列, FixedArray=固定数组
    queue.filename="fwd_queue"    # 磁盘队列文件名（启用磁盘队列）
    queue.maxdiskspace="1g"       # 磁盘队列最大空间
    queue.saveonshutdown="on"     # 关机时保存队列到磁盘
    queue.dequeuebatchsize="100"  # 每批发送的消息数

    # 重试策略
    action.resumeRetryCount="-1"  # -1 = 无限重试
    action.resumeinterval="30"    # 重试间隔（秒）

    # 内存队列参数
    queue.size="10000"            # 内存队列大小
    queue.highwatermark="8000"    # 开始写入磁盘的阈值
    queue.lowwatermark="2000"     # 停止写入磁盘的阈值
)
```

#### 3.8 加密传输（TLS）

```bash
# ===== 生成证书 =====
# CA 证书
sudo openssl req -new -x509 -keyout /etc/rsyslog.d/ca.key \
    -out /etc/rsyslog.d/ca.pem -days 365 -nodes \
    -subj "/CN=Log CA"

# 服务器证书
sudo openssl req -new -keyout /etc/rsyslog.d/server.key \
    -out /etc/rsyslog.d/server.csr -nodes \
    -subj "/CN=log-server"
sudo openssl x509 -req -in /etc/rsyslog.d/server.csr \
    -CA /etc/rsyslog.d/ca.pem -CAkey /etc/rsyslog.d/ca.key \
    -CAcreateserial -out /etc/rsyslog.d/server.pem -days 365

# ===== 服务器端配置 =====
sudo cat > /etc/rsyslog.d/51-tls-server.conf << 'RSYSLOG'
module(load="imtcp"
    StreamDriver.Name="gtls"
    StreamDriver.Mode="1"
    StreamDriver.Authmode="x509/certvalid"
)

defaultNetstreamDriverCAFile="/etc/rsyslog.d/ca.pem"
defaultNetstreamDriverCertFile="/etc/rsyslog.d/server.pem"
defaultNetstreamDriverKeyFile="/etc/rsyslog.d/server.key"

input(type="imtcp" port="6514")
RSYSLOG

# ===== 客户端配置 =====
sudo cat > /etc/rsyslog.d/51-tls-client.conf << 'RSYSLOG'
module(load="imtcp"
    StreamDriver.Name="gtls"
    StreamDriver.Mode="1"
    StreamDriver.Authmode="x509/name"
)

defaultNetstreamDriverCAFile="/etc/rsyslog.d/ca.pem"
defaultNetstreamDriverCertFile="/etc/rsyslog.d/client.pem"
defaultNetstreamDriverKeyFile="/etc/rsyslog.d/client.key"

*.* action(type="omfwd"
    target="log-server.example.com"
    port="6514"
    protocol="tcp"
    streamdriver="gtls"
)
RSYSLOG
```

---

### 4. logrotate 深入

#### 4.1 为什么需要 logrotate？

日志文件如果不管理会：
1. **无限增长** → 耗尽磁盘空间
2. **单个文件过大** → 编辑器打不开，分析工具 OOM
3. **无法按时间检索** → 所有日志混在一起

```
logrotate 轮转流程：

access.log (当前)
    ↓ 触发轮转
access.log → access.log.1 (重命名)
    ↓ 再次轮转
access.log.1 → access.log.2
access.log → access.log.1 (新建空文件)
    ↓ ...
access.log.30 → 删除（超出保留数）
```

#### 4.2 logrotate 配置详解

```bash
# 主配置文件
cat /etc/logrotate.conf
# weekly        — 默认每周轮转
# rotate 4      — 保留 4 个旧文件
# create        — 轮转后创建新文件
# include /etc/logrotate.d/

# 查看有哪些服务配置了 logrotate
ls /etc/logrotate.d/
# apache2  mysql  nginx  rsyslog  ufw  apt  dpkg

# 测试配置（dry run，不实际操作）
sudo logrotate -d /etc/logrotate.d/nginx

# 强制轮转（实际操作）
sudo logrotate -f /etc/logrotate.d/nginx
```

#### 4.3 logrotate 配置选项详解

```bash
# 完整的自定义 logrotate 配置示例
sudo cat > /etc/logrotate.d/myapp << 'EOF'
/var/log/myapp/*.log {
    # === 轮转频率 ===
    daily               # 每天轮转（可选：daily/weekly/monthly/yearly）
    # 也可以用 dateext + dateformat 按日期命名

    # === 保留数量 ===
    rotate 30           # 保留 30 个旧文件

    # === 压缩 ===
    compress            # 压缩旧文件（gzip）
    delaycompress       # 延迟一次压缩（最近一个不压缩，方便查看）
    compresscmd gzip    # 压缩命令（默认 gzip）
    compressext .gz     # 压缩后缀
    compressoptions -9  # 压缩选项（最大压缩率）

    # === 文件不存在 ===
    missingok           # 文件不存在不报错

    # === 空文件 ===
    notifempty          # 空文件不轮转

    # === 新文件权限 ===
    create 0640 www-data adm   # 轮转后创建新文件的权限和属主

    # === 轮转后脚本 ===
    sharedscripts       # 多个文件时 postrotate 只执行一次
    postrotate
        # 通知应用重新打开日志文件
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript

    # === 轮转前脚本 ===
    prerotate
        # 例如：备份当前日志到远程
        # rsync -a /var/log/myapp/ backup-server:/logs/
    endscript

    # === 按大小轮转（替代或补充时间轮转）===
    # size 100M        # 文件超过 100M 才轮转
    # minsize 10M      # 最小轮转大小
    # maxsize 200M     # 最大轮转大小（超过立即轮转）

    # === 日期后缀 ===
    dateext             # 用日期代替数字后缀
    dateformat -%Y%m%d  # 日期格式（默认 -%Y%m%d）
    # 生成文件名：access.log-20260501.gz

    # === su 指令（指定日志文件的属主）===
    # su www-data www-data   # 如果日志文件属主不是 root

    # === olddir ===
    # olddir /var/log/myapp/old   # 旧文件移到指定目录
    # olddir archive              # 相对路径
}
EOF

# 验证配置语法
sudo logrotate -d /etc/logrotate.d/myapp
```

#### 4.4 postrotate 为什么需要 reload 服务？

```
问题：为什么 logrotate 轮转后需要通知应用？

场景：
1. Nginx 启动时打开 /var/log/nginx/access.log，获得文件描述符 FD=7
2. Nginx 通过 FD=7 持续写入日志
3. logrotate 将 access.log 重命名为 access.log.1
4. logrotate 创建新的 access.log
5. 但 Nginx 仍然通过 FD=7 写入 → 写入的是 access.log.1！

如果不通知 Nginx：
  - 新的 access.log 永远是空的
  - 所有日志写入旧的 access.log.1
  - 下次轮转时 access.log.1 被删除 → 日志丢失

解决方案：
  - 发送 USR1 信号：Nginx 重新打开日志文件
  - 重新打开后，Nginx 获得新的 FD 指向新的 access.log

各服务的 reload 方式：
┌──────────────┬──────────────────────────────────────┐
│ 服务          │ 重新打开日志的方式                     │
├──────────────┼──────────────────────────────────────┤
│ Nginx        │ kill -USR1 $(cat /var/run/nginx.pid)  │
│ Apache       │ kill -USR1 $(cat /var/run/apache2.pid)│
│ MySQL        │ mysqladmin flush-logs                 │
│ rsyslog      │ systemctl reload rsyslog              │
│ 自定义应用    │ 通常用 HUP 信号或专用命令              │
└──────────────┴──────────────────────────────────────┘
```

#### 4.5 copytruncate vs create 模式

```bash
# create 模式（默认，推荐）
/var/log/myapp/*.log {
    daily
    rotate 7
    create 0640 app app     # 创建新文件
    postrotate
        systemctl reload myapp  # 通知应用重新打开日志
    endscript
}
# 流程：重命名旧文件 → 创建新文件 → 通知应用
# 优点：无日志丢失
# 缺点：应用需要支持重新打开日志

# copytruncate 模式（不推荐，最后手段）
/var/log/myapp/*.log {
    daily
    rotate 7
    copytruncate    # 复制后截断
}
# 流程：复制当前文件 → 清空原文件
# 优点：不需要通知应用
# 缺点：复制和清空之间可能丢失日志；大文件复制耗时

# 选择建议：
# 1. 优先用 create + postrotate
# 2. 应用不支持 reload 时才用 copytruncate
# 3. 永远不要同时使用 create 和 copytruncate
```

#### 4.6 按大小轮转 vs 按时间轮转

```bash
# 按时间轮转（默认）
/var/log/nginx/access.log {
    daily           # 每天轮转
    rotate 30       # 保留 30 天
}
# 适用：访问量稳定的系统

# 按大小轮转
/var/log/nginx/access.log {
    size 100M       # 文件超过 100M 才轮转
    rotate 10       # 保留 10 个
}
# 适用：访问量波动大的系统

# 混合策略（推荐）
/var/log/nginx/access.log {
    daily           # 至少每天轮转一次
    maxsize 200M    # 但如果超过 200M 也立即轮转
    rotate 30
}
# 适用：兼顾时间和大小，防止日志暴涨

# 使用 logrotate 的 timer（systemd 方式，替代 cron）
# /etc/systemd/system/logrotate.timer
# [Timer]
# OnCalendar=*-*-* *:00:00    # 每小时检查一次
# Persistent=true

# /etc/systemd/system/logrotate.service
# [Service]
# Type=oneshot
# ExecStart=/usr/sbin/logrotate /etc/logrotate.conf
```

#### 4.7 logrotate 运行机制

```bash
# logrotate 通过 cron 或 systemd timer 定时执行

# cron 方式（传统）
cat /etc/cron.daily/logrotate
#!/bin/sh
test -x /usr/sbin/logrotate || exit 0
/usr/sbin/logrotate /etc/logrotate.conf

# systemd timer 方式（现代）
systemctl list-timers | grep logrotate

# 状态文件（记录上次轮转时间）
cat /var/lib/logrotate/status
# 如果删除此文件，下次会重新轮转所有文件

# 手动触发（用于测试）
sudo logrotate -f /etc/logrotate.d/nginx

# 详细输出（调试用）
sudo logrotate -d /etc/logrotate.d/nginx
```

---

### 5. 结构化日志

#### 5.1 为什么需要结构化日志？

```
传统纯文本日志：
2026-05-01 10:23:45 ERROR [nginx] connection timeout from 192.168.1.100:54321

结构化 JSON 日志：
{
    "timestamp": "2026-05-01T10:23:45.123Z",
    "level": "ERROR",
    "service": "nginx",
    "message": "connection timeout",
    "client_ip": "192.168.1.100",
    "client_port": 54321,
    "request_id": "abc-123-def",
    "upstream": "10.0.0.5:8080",
    "response_time_ms": 30000
}

优势对比：
┌─────────────┬──────────────────┬────────────────────┐
│ 维度         │ 纯文本日志        │ 结构化日志           │
├─────────────┼──────────────────┼────────────────────┤
│ 解析难度     │ 需要正则表达式     │ 直接 JSON 解析       │
│ 查询效率     │ grep 慢          │ 索引查询快           │
│ 字段提取     │ 容易出错          │ 精确提取             │
│ 聚合分析     │ 困难              │ 简单（group by）     │
│ 存储大小     │ 较小              │ 较大（字段名重复）    │
│ 人类可读     │ 好               │ 差（需要格式化）      │
│ 机器可读     │ 差               │ 好                   │
└─────────────┴──────────────────┴────────────────────┘
```

#### 5.2 实现结构化日志

```bash
# 方法 1：应用程序直接输出 JSON
# Python 示例
import json
import logging
import sys

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.info("User login", extra={"user_id": 123, "ip": "192.168.1.1"})
```

```bash
# 方法 2：rsyslog 将传统日志转为 JSON
# 在 rsyslog 配置中使用 JSON 模板
template(name="JSONFormat" type="list") {
    constant(value="{")
    constant(value="\"timestamp\":\"")     property(name="timereported" dateFormat="rfc3339")
    constant(value="\",\"host\":\"")       property(name="hostname")
    constant(value="\",\"program\":\"")    property(name="programname")
    constant(value="\",\"severity\":\"")   property(name="syslogseverity-text")
    constant(value="\",\"message\":")      property(name="msg" format="json")
    constant(value="}\n")
}

*.* action(type="omfile" file="/var/log/structured.json" template="JSONFormat")
```

```bash
# 方法 3：使用 jq 分析 JSON 日志
# 统计错误日志数量
cat /var/log/app.json | jq 'select(.level == "ERROR")' | wc -l

# 按服务统计
cat /var/log/app.json | jq -r '.service' | sort | uniq -c | sort -rn

# 查找特定时间段的错误
cat /var/log/app.json | jq 'select(.level == "ERROR" and .timestamp > "2026-05-01T10:00:00")'

# 提取特定字段
cat /var/log/app.json | jq -r '[.timestamp, .level, .message] | @tsv'
```

---

### 6. SRE 实战案例

#### 6.1 磁盘被日志撑满的排查和预防

```bash
#!/bin/bash
# log-emergency.sh — 日志爆满应急处理
set -euo pipefail

echo "=== 日志爆满应急检查 $(date) ==="

# 1. 检查磁盘使用率
echo -e "\n📊 磁盘使用率:"
df -h | awk 'NR==1 || $5+0 > 70'

# 2. 检查日志目录大小
echo -e "\n📁 日志目录 Top 10:"
sudo du -sh /var/log/* 2>/dev/null | sort -rh | head -10

# 3. 检查大日志文件
echo -e "\n📄 大于 100MB 的日志文件:"
sudo find /var/log -name "*.log" -size +100M -exec ls -lh {} \; 2>/dev/null

# 4. 检查已删除但未释放的文件
echo -e "\n🗑️ 已删除但未释放的文件:"
sudo lsof +L1 2>/dev/null | grep '/var/log' | head -10

# 5. 紧急清理建议
echo -e "\n🔧 建议操作:"
echo "  1. 清空大日志文件: sudo truncate -s 0 /var/log/large-file.log"
echo "  2. 强制轮转: sudo logrotate -f /etc/logrotate.d/nginx"
echo "  3. 清理旧日志: sudo find /var/log -name '*.gz' -mtime +30 -delete"
echo "  4. 清理 journal: sudo journalctl --vacuum-size=500M"

# 6. 预防措施检查
echo -e "\n✅ 预防措施检查:"
if [ -f /etc/logrotate.d/nginx ]; then
    echo "  [OK] Nginx logrotate 已配置"
else
    echo "  [WARN] Nginx logrotate 未配置！"
fi

if [ -d /var/log/journal ]; then
    echo "  [OK] Journal 持久化已启用"
    journalctl --disk-usage
else
    echo "  [INFO] Journal 未持久化（重启丢失）"
fi

if grep -q "SystemMaxUse" /etc/systemd/journald.conf 2>/dev/null; then
    echo "  [OK] Journal 大小限制已配置"
else
    echo "  [WARN] Journal 大小限制未配置！"
fi
```

**预防措施：**
```bash
# 1. 配置 journal 大小限制
sudo vim /etc/systemd/journald.conf
# SystemMaxUse=500M
# MaxRetentionSec=30day

# 2. 确保所有服务都配置了 logrotate
ls /etc/logrotate.d/

# 3. 设置磁盘使用率监控（Prometheus Node Exporter）
# node_filesystem_avail_bytes{mountpoint="/var/log"} < 5e9  # 小于 5GB

# 4. 日志集中收集，本地只保留最近 N 天
# rsyslog 转发到远程 Elasticsearch/Graylog
```

#### 6.2 集中日志收集方案设计

```
生产环境集中日志架构：

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  App Server 1│  │  App Server 2│  │  App Server N│
│              │  │              │  │              │
│  rsyslog ────┼──┼──→ TCP 514 ─┼──┼──→           │
│  (客户端)     │  │  (客户端)     │  │  (客户端)     │
└─────────────┘  └─────────────┘  └─────────────┘
                          │
                          ▼
                ┌──────────────────┐
                │  Log Server       │
                │  (rsyslog 服务端)  │
                │                   │
                │  接收 → 解析 → 存储 │
                └────────┬──────────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ 本地文件  │  │Elasticsearch│ │ 警报系统  │
    │ /var/log/│  │  (全文索引)  │ │ PagerDuty│
    │ remote/  │  │  Kibana     │ │ Slack    │
    └──────────┘  └──────────┘  └──────────┘
```

```bash
# 方案 1：rsyslog → 本地文件（简单场景）
# 见上面的远程日志收集配置

# 方案 2：rsyslog → Elasticsearch（推荐）
# 服务器端配置
sudo cat > /etc/rsyslog.d/60-elasticsearch.conf << 'RSYSLOG'
module(load="omelasticsearch")

template(name="ESIndex" type="list") {
    constant(value="syslog-")
    property(name="timereported" dateFormat="rfc3339" position.from="1" position.to="4")
    constant(value=".")
    property(name="timereported" dateFormat="rfc3339" position.from="6" position.to="7")
    constant(value=".")
    property(name="timereported" dateFormat="rfc3339" position.from="9" position.to="10")
}

template(name="JSONFormat" type="list") {
    constant(value="{")
    constant(value="\"@timestamp\":\"")   property(name="timereported" dateFormat="rfc3339")
    constant(value="\",\"host\":\"")      property(name="hostname")
    constant(value="\",\"program\":\"")   property(name="programname")
    constant(value="\",\"severity\":\"")  property(name="syslogseverity-text")
    constant(value="\",\"message\":")     property(name="msg" format="json")
    constant(value="}\n")
}

if $fromhost-ip != '127.0.0.1' then {
    action(type="omelasticsearch"
        server="localhost"
        serverport="9200"
        template="JSONFormat"
        dynaIndex="on"
        searchIndex="ESIndex"
        searchType="events"
        bulkmode="on"
        bulkId="id"
    )
}
RSYSLOG

# 方案 3：Filebeat → Elasticsearch（ELK 方案）
# Filebeat 轻量级日志采集器，比 rsyslog 更适合发送到 ES
# 安装：apt install filebeat
# 配置：/etc/filebeat/filebeat.yml
```

#### 6.3 日志保留策略合规要求

```
合规要求对比：
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ 标准          │ 日志保留期限  │ 日志类型      │ 要求          │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ GDPR          │ 最小必要原则  │ 个人数据日志  │ 加密、访问控制 │
│ 等保 2.0      │ ≥6个月       │ 所有安全日志  │ 完整性保护    │
│ PCI DSS       │ ≥1年         │ 访问日志      │ 防篡改        │
│ SOX           │ ≥7年         │ 财务相关日志  │ 不可修改      │
│ HIPAA         │ ≥6年         │ 医疗数据日志  │ 加密存储      │
└──────────────┴──────────────┴──────────────┴──────────────┘

实现策略：
1. 日志分层存储：
   - 热存储（SSD）：最近 7 天，快速查询
   - 温存储（HDD）：7-30 天，较慢查询
   - 冷存储（对象存储/S3）：30 天以上，归档

2. 日志完整性保护：
   - journald 的 Seal 选项（FSS 密封）
   - 远程日志服务器（防本地篡改）
   - 日志哈希链（hash chain）

3. 访问控制：
   - 日志文件权限 640，属主 root:adm
   - 远程日志服务器独立管理
   - 审计日志访问记录
```

---

## 💻 实战练习

### 练习 1：完整的日志管理方案

```bash
#!/bin/bash
# log-management-setup.sh — 生产级日志管理配置
set -euo pipefail

echo "📝 配置日志管理方案..."

# 1. 配置 journald 持久化和大小限制
sudo mkdir -p /etc/systemd/journald.conf.d
sudo cat > /etc/systemd/journald.conf.d/limits.conf << 'EOF'
[Journal]
Storage=persistent
SystemMaxUse=500M
MaxRetentionSec=30day
ForwardToSyslog=yes
Compress=yes
EOF

# 启用持久化
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald

# 2. 配置 rsyslog 分离业务日志
sudo cat > /etc/rsyslog.d/10-webapp.conf << 'EOF'
# 业务应用使用 local0
local0.*    /var/log/webapp/app.log
local0.err  /var/log/webapp/error.log

# 安全日志单独存储
auth,authpriv.*    /var/log/security/auth.log

# JSON 格式输出
template(name="JSONFormat" type="list") {
    constant(value="{")
    constant(value="\"timestamp\":\"")     property(name="timereported" dateFormat="rfc3339")
    constant(value="\",\"host\":\"")       property(name="hostname")
    constant(value="\",\"program\":\"")    property(name="programname")
    constant(value="\",\"severity\":\"")   property(name="syslogseverity-text")
    constant(value="\",\"message\":")      property(name="msg" format="json")
    constant(value="}\n")
}
local0.* action(type="omfile" file="/var/log/webapp/structured.json" template="JSONFormat")
EOF

sudo mkdir -p /var/log/{webapp,security}
sudo chown syslog:syslog /var/log/{webapp,security}
sudo systemctl restart rsyslog

# 3. 配置 Nginx 日志轮转
sudo cat > /etc/logrotate.d/nginx-custom << 'EOF'
/var/log/nginx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
    sharedscripts
    dateext
    dateformat -%Y%m%d
    maxsize 200M
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}
EOF

# 4. 配置应用日志轮转
sudo cat > /etc/logrotate.d/webapp << 'EOF'
/var/log/webapp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 syslog syslog
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
EOF

# 5. 验证
echo "=== 验证配置 ==="
echo "Journal 磁盘占用:"
journalctl --disk-usage

echo -e "\nLogrotate 配置检查:"
sudo logrotate -d /etc/logrotate.d/nginx-custom 2>&1 | tail -5

echo -e "\nrsyslog 配置检查:"
sudo rsyslogd -N1 2>&1

echo "=== 配置完成 ==="
```

### 练习 2：日志安全审计脚本

```bash
#!/bin/bash
# security-audit.sh — 日志安全审计
set -euo pipefail

echo "🔐 安全审计 — $(date '+%Y-%m-%d %H:%M')"

# 1. SSH 暴力破解检测
echo -e "\n🚫 SSH 暴力破解 (过去24小时):"
sudo journalctl -u sshd --since "24 hours ago" 2>/dev/null | \
    grep "Failed password" | \
    awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9.]+$/ && $i != "for") print $i}' | \
    sort | uniq -c | sort -rn | head -10 | \
    while read count ip; do
        if [ "$count" -gt 10 ]; then
            echo "  🔴 $ip: $count 次失败登录"
        else
            echo "  🟡 $ip: $count 次失败登录"
        fi
    done

# 2. sudo 使用记录
echo -e "\n🔑 sudo 使用记录 (过去24小时):"
sudo journalctl _COMM=sudo --since "24 hours ago" 2>/dev/null | \
    grep "COMMAND" | tail -10

# 3. 成功登录记录
echo -e "\n✅ 成功登录:"
last -n 10 2>/dev/null || sudo grep "Accepted" /var/log/auth.log 2>/dev/null | tail -10

# 4. 异常登录时间
echo -e "\n⏰ 非工作时间登录 (22:00-06:00):"
sudo journalctl _COMM=sshd --since "7 days ago" 2>/dev/null | \
    grep "Accepted" | \
    awk -F'[ :]' '{hour=$(NF-7); if (hour >= 22 || hour < 6) print $0}'

# 5. 用户管理操作
echo -e "\n👤 用户管理操作 (过去7天):"
sudo journalctl --since "7 days ago" 2>/dev/null | \
    grep -E "(useradd|userdel|usermod|groupadd)" | tail -10

# 6. 关键文件变更
echo -e "\n📁 关键文件状态:"
for f in /etc/passwd /etc/shadow /etc/sudoers /etc/ssh/sshd_config; do
    if [ -f "$f" ]; then
        echo "  $f: $(stat -c '%a %U %G %y' "$f")"
    fi
done
```

### 练习 3：Nginx 日志分析

```bash
#!/bin/bash
# nginx-log-analysis.sh — Nginx 访问日志分析
LOG="/var/log/nginx/access.log"
[ ! -f "$LOG" ] && { echo "日志文件不存在: $LOG"; exit 1; }

echo "📊 Nginx 日志分析 — $LOG"
total=$(wc -l < "$LOG")
echo "总请求数: $total"

# 1. HTTP 状态码分布
echo -e "\n📈 状态码分布:"
awk '{print $9}' "$LOG" | sort | uniq -c | sort -rn | \
    awk '{printf "  HTTP %s: %6d 次 (%.1f%%)\n", $2, $1, $1/'"$total"'*100}'

# 2. Top 10 访问 IP
echo -e "\n🌐 Top 10 IP:"
awk '{print $1}' "$LOG" | sort | uniq -c | sort -rn | head -10

# 3. Top 10 请求 URL
echo -e "\n🔗 Top 10 URL:"
awk -F'"' '{print $2}' "$LOG" | awk '{print $2}' | sort | uniq -c | sort -rn | head -10

# 4. 5xx 错误详情
echo -e "\n❌ 5xx 错误详情:"
awk '$9 >= 500' "$LOG" | tail -20 | awk '{printf "  [%s] %s %s\n", $9, $7, $1}'

# 5. 每分钟请求量（最近 1 小时）
echo -e "\n📊 最近 1 小时每分钟请求量:"
tail -6000 "$LOG" | awk '{print $4}' | cut -d: -f1-3 | sort | uniq -c | \
    sort -rn | head -10 | awk '{printf "  %s: %d 请求\n", $2, $1}'

# 6. 响应时间分析（如果有 $request_time 字段）
echo -e "\n⏱️ 响应时间分析:"
awk '{print $NF}' "$LOG" | sort -n | awk '
BEGIN { count=0; sum=0 }
{
    count++
    sum += $1
    if (count == 1) min = $1
    if (count % 2 == 1) median = $1
    max = $1
}
END {
    printf "  最小: %.3fs\n", min
    printf "  平均: %.3fs\n", sum/count
    printf "  最大: %.3fs\n", max
}'
```

---

## 🎯 面试题精选

### 1. journalctl 和 rsyslog 有什么区别？

**答：**
- **journalctl**：systemd 的原生日志工具，读取二进制格式的 journal 日志。支持结构化查询（按服务、PID、优先级、时间等），自动索引，查询速度快。日志存储在 `/var/log/journal/` 或 `/run/log/journal/`。
- **rsyslog**：传统的 syslog 实现，处理文本格式日志。功能更强大：支持远程转发（TCP/UDP）、灵活的路由规则、模板系统、多种输出（文件、数据库、Elasticsearch）。
- **关系**：两者可以共存。journald 通过 `ForwardToSyslog=yes` 将日志转发给 rsyslog。生产环境通常两者配合：journald 收集 + rsyslog 路由和转发。

### 2. logrotate 轮转后为什么需要 reload 服务？

**答：** 因为服务进程在启动时打开日志文件，获得文件描述符（FD）。logrotate 轮转时重命名旧文件、创建新文件，但服务进程仍然通过旧的 FD 写入。如果不通知服务重新打开日志文件，新日志会继续写入旧文件（已被重命名），新创建的日志文件永远为空。各服务的 reload 方式不同：Nginx 用 `kill -USR1`，Apache 用 `kill -USR1`，MySQL 用 `mysqladmin flush-logs`。

### 3. 如何设计一个生产级的日志收集架构？

**答：**
- **采集层**：每个应用服务器运行 rsyslog（或 Filebeat），收集本地日志
- **传输层**：使用 TCP 保证可靠传输，配置磁盘队列防止日志丢失
- **存储层**：rsyslog 服务器接收后写入 Elasticsearch（热数据 7 天）+ 对象存储（冷数据长期保留）
- **查询层**：Kibana 提供可视化查询和告警
- **关键点**：加密传输（TLS）、日志完整性保护、保留策略合规、容量规划

### 4. 日志文件被删除但磁盘空间未释放，怎么排查和解决？

**答：**
1. 排查：`sudo lsof +L1 | grep deleted` 找到被删除但仍被进程占用的文件
2. 解决方法 1：`> /proc/<PID>/fd/<FD>` 清空文件内容释放空间
3. 解决方法 2：重启持有该文件的进程（如 `systemctl restart nginx`）
4. 预防：不要 `rm` 正在写入的日志文件，用 `truncate -s 0` 清空内容

### 5. 如何在 rsyslog 中实现按主机名分目录存储远程日志？

**答：** 使用模板和动态文件名：
```
template(name="RemoteHost" type="string"
    string="/var/log/remote/%HOSTNAME%/%PROGRAMNAME%.log")
*.* action(type="omfile" dynaFile="RemoteHost")
```
`%HOSTNAME%` 是发送端的主机名，rsyslog 会自动创建目录（需要 `createDirs="on"`）。

### 6. journald 的 Storage 选项有哪些？分别适用什么场景？

**答：**
- `persistent`：始终写入 `/var/log/journal/`，重启后保留日志。生产环境推荐。
- `auto`：如果 `/var/log/journal/` 存在就写入，否则只写内存。默认值。
- `volatile`：只写内存（`/run/log/journal/`），重启丢失。临时环境。
- `none`：不记录日志。极端安全场景。

### 7. 如何监控日志文件的增长速度？

**答：**
```bash
# 方法 1：watch 命令
watch -n 10 'ls -lhS /var/log/*.log | head -10'

# 方法 2：计算增长速率
# 记录两次大小，计算差值
SIZE1=$(stat -c%s /var/log/nginx/access.log)
sleep 60
SIZE2=$(stat -c%s /var/log/nginx/access.log)
echo "增长率: $(( (SIZE2 - SIZE1) / 1024 )) KB/min"

# 方法 3：Prometheus Node Exporter
# node_filesystem_size_bytes - node_filesystem_avail_bytes
```

### 8. 结构化日志比纯文本日志好在哪里？

**答：**
- **查询效率**：JSON 字段可以直接索引和查询，不需要正则匹配
- **精确提取**：字段名明确，不会因为日志格式变化而解析失败
- **聚合分析**：可以按任意字段 group by（如按服务、按状态码统计）
- **机器友好**：ELK 等工具可以直接解析 JSON，不需要 grok 模式
- **缺点**：存储大小增加（字段名重复）、人类可读性变差

---

## 📚 深入阅读

- [systemd Journal Fields](https://www.freedesktop.org/software/systemd/man/systemd.journal-fields.html) — journal 所有结构化字段
- [rsyslog 官方文档](https://www.rsyslog.com/doc/) — 配置语法和模块详解
- [logrotate 手册](https://linux.die.net/man/8/logrotate) — 所有配置选项
- [rsyslog 队列和故障恢复](https://www.rsyslog.com/doc/v8-stable/concepts/queues.html)
- [Elasticsearch + rsyslog 集成](https://www.rsyslog.com/doc/v8-stable/configuration/modules/omelasticsearch.html)

**最佳实践：**
- journald 启用**持久化存储**，否则重启后日志丢失
- 所有日志轮转使用 **create + postrotate**，避免 copytruncate
- 生产环境部署**远程日志服务器**，本地磁盘满了日志还在
- 日志文件权限设为 **640**，属主 root:adm，禁止普通用户读取
- journal 配置 `SystemMaxUse` 限制大小，防止撑满磁盘
- 结构化日志（JSON）比纯文本更适合大规模日志分析

---

## ✅ 自检清单

- [ ] 理解 Linux 日志体系的双系统架构（journald + rsyslog）
- [ ] 能使用 journalctl 进行高级查询（按服务、优先级、时间、PID、字段）
- [ ] 理解 /etc/systemd/journald.conf 的关键配置项
- [ ] 能配置 rsyslog 的日志路由（facility.severity、模板、远程转发）
- [ ] 理解 logrotate 的 postrotate 为什么需要 reload 服务
- [ ] 能配置按大小和按时间的轮转策略
- [ ] 能处理生产环境的日志爆满问题
- [ ] 理解结构化日志的优势和实现方式
- [ ] 能设计集中日志收集方案
- [ ] 了解日志保留策略的合规要求
