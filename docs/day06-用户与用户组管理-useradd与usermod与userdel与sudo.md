# Day 06: 用户与用户组管理 -- useradd/usermod/userdel/sudo

> 📅 日期：2026-04-26
> 📖 学习主题：用户与用户组管理 -- useradd/usermod/userdel/sudo
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 01-05（Linux 基础、文件操作、文本处理、权限管理）

## 🎯 学习目标

完成 Day 06 的学习后，你应该能够：
- 深入理解 Linux 用户体系（root、系统用户、普通用户、UID/GID 分配规则）
- 解析 `/etc/passwd`、`/etc/shadow`、`/etc/group`、`/etc/gshadow` 每个字段的含义
- 掌握 sudo 工作原理、`/etc/sudoers` 语法和安全配置
- 了解 PAM 认证框架的基本架构
- 能够设计和实施用户生命周期管理方案（入职到离职全流程）
- 配置密码策略（过期、复杂度、历史）

---

## 📖 核心知识点

### 1. Linux 用户体系深入

#### 1.1 用户分类与 UID/GID 分配规则

```
┌──────────────────────────────────────────────────────────────────┐
│  Linux 用户分类                                                   │
├──────────────┬────────────┬───────────────────────────────────────┤
│  用户类型     │  UID 范围   │  说明                                 │
├──────────────┼────────────┼───────────────────────────────────────┤
│  root        │  0         │  超级管理员，拥有最高权限               │
│  系统用户     │  1-999     │  服务运行使用，通常不能登录             │
│  (daemon)    │  (CentOS:  │  如 nginx(999), mysql(998),            │
│              │  1-499)    │  www-data(33), nobody(65534)            │
│  普通用户     │  1000+     │  人类用户，日常使用                     │
│  (human)     │  (CentOS:  │  如 alice(1000), bob(1001)             │
│              │  500+)     │                                        │
├──────────────┼────────────┼───────────────────────────────────────┤
│  nobody      │  65534     │  权限最低的用户，用于 NFS、降权运行     │
└──────────────┴────────────┴───────────────────────────────────────┘

UID 分配配置文件：/etc/login.defs
  UID_MIN  1000    # 普通用户最小 UID
  UID_MAX  60000   # 普通用户最大 UID
  SYS_UID_MIN 100  # 系统用户最小 UID
  SYS_UID_MAX 999  # 系统用户最大 UID
```

**UID 的重要性**：

```bash
# 内核只认 UID，不认用户名
# 用户名只是 /etc/passwd 中的人类可读标签

# 这意味着：
# 1. 删除用户后重新创建同名用户，UID 可能不同，权限不继承
# 2. 文件的 owner 是 UID，不是用户名
# 3. 如果 /etc/passwd 被破坏，UID 仍然有效

# 查看 UID
id alice
# uid=1000(alice) gid=1000(alice) groups=1000(alice),27(sudo),999(docker)

# 查看文件的 UID（即使用户已被删除）
ls -ln /home/alice/file.txt
# -rw-r--r-- 1 1000 1000 ... file.txt
# 显示 UID 1000，而不是用户名（因为用户可能已不存在）
```

#### 1.2 用户组的类型

```bash
# 主组（Primary Group）
# - 每个用户必须有一个主组
# - 创建用户时自动创建同名组（默认行为）
# - 新建文件的组继承用户的主组
# - 在 /etc/passwd 的第 4 列

# 附加组（Supplementary Groups）
# - 用户可以属于多个附加组
# - 在 /etc/group 中定义
# - 用于授予额外权限（如 sudo、docker）
# - usermod -aG 添加附加组

# 查看用户的所有组
id alice
# uid=1000(alice) gid=1000(alice) groups=1000(alice),27(sudo),999(docker)
#                               ^主组                ^附加组
```

---

### 2. 关键配置文件详解

#### 2.1 /etc/passwd -- 用户账户信息

```bash
# 每行一个用户，冒号分隔 7 个字段
cat /etc/passwd | head -5
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
alice:x:1000:1000:Alice Chen:/home/alice:/bin/bash

# 字段解析：
# alice : x : 1000 : 1000 : Alice Chen : /home/alice : /bin/bash
#   1     2    3      4       5            6             7
#
# 1. 用户名（login name）
# 2. 密码占位符（x 表示密码在 /etc/shadow 中）
#    历史上密码直接存在这里，现在用 x 代替
#    如果是 !! 或 * 表示账户被锁定
# 3. UID（用户 ID）
# 4. GID（主组 ID）
# 5. GECOS/注释（通常包含全名、联系方式等）
# 6. 家目录（Home Directory）
# 7. 登录 Shell（Login Shell）
#    /bin/bash -- 正常可登录
#    /bin/zsh -- zsh shell
#    /sbin/nologin -- 不允许交互登录（服务用户）
#    /bin/false -- 不允许登录（与 nologin 类似）

# passwd 文件权限
ls -l /etc/passwd
# -rw-r--r-- 1 root root ... /etc/passwd
# 644：所有人可读（因为很多程序需要查询用户信息）
# 只有 root 可以写入
```

#### 2.2 /etc/shadow -- 密码安全信息

```bash
# 权限：只有 root 和 shadow 组可读
ls -l /etc/shadow
# -rw-r----- 1 root shadow ... /etc/shadow

# 每行一个用户，冒号分隔 9 个字段
cat /etc/shadow | head -3
root:$y$j9T$...:19845:0:99999:7:::
alice:$6$salt$hash...:19845:7:90:14:10:::

# 字段解析：
# alice : $6$salt$hash... : 19845 : 7 : 90 : 14 : 10 : : :
#   1          2              3     4   5    6    7   8 9
#
# 1. 用户名（与 /etc/passwd 对应）
# 2. 加密密码（格式：$id$salt$hash）
#    $1$ = MD5（已废弃）
#    $5$ = SHA-256
#    $6$ = SHA-512（目前常用）
#    $y$ = yescrypt（新系统默认，如 Ubuntu 22.04+）
#    !! 或 * = 账户锁定（无法密码登录）
#    空字符串 = 无密码登录（极不安全）
# 3. 最后修改日期（自 1970-01-01 的天数）
# 4. 最小修改间隔天数（0 = 随时可改）
# 5. 最大有效天数（99999 = 永不过期）
# 6. 过期警告天数（过期前 N 天提醒）
# 7. 密码过期后的宽限天数
# 8. 账户过期日期（自 1970-01-01 的天数，空 = 永不过期）
# 9. 保留字段
```

**密码哈希算法详解**：

```
$6$rounds=5000$saltsalt$hashhashhash...
 │  │            │        │
 │  │            │        └── 加密后的密码哈希
 │  │            └── 盐值（salt，随机字符串）
 │  └── 迭代次数（rounds，越大越安全但越慢）
 └── 算法 ID
      $1$ = MD5（128位，已不安全）
      $5$ = SHA-256（256位）
      $6$ = SHA-512（512位，目前主流）
      $y$ = yescrypt（新标准，抗 GPU/ASIC 攻击）

验证密码：
$ openssl passwd -6 -salt mysalt "mypassword"
$6$mysalt$...hash...

# 用 Python 验证
$ python3 -c "
import crypt
print(crypt.crypt('mypassword', '\$6\$salt\$'))
"
```

#### 2.3 /etc/group -- 组信息

```bash
# 权限：644（所有人可读）
cat /etc/group | head -5
root:x:0:
sudo:x:27:alice,bob
docker:x:999:alice
alice:x:1000:

# 字段解析：
# sudo : x : 27 : alice,bob
#  1     2   3      4
#
# 1. 组名
# 2. 组密码（x 表示在 /etc/gshadow，通常不设）
# 3. GID（组 ID）
# 4. 组成员列表（逗号分隔）
#    注意：这里只列附加成员，不列主组成员
#    用户 alice 的主组是 alice (GID 1000)，
#    即使 alice 也在 sudo 组中，alice 行不会出现
```

#### 2.4 /etc/gshadow -- 组密码安全

```bash
# 权限：600（只有 root 可读）
cat /etc/gshadow | head -3
root:*::
sudo:*::alice,bob
alice:!::

# 字段解析：
# sudo : * : : alice,bob
#   1    2   3    4
#
# 1. 组名
# 2. 加密密码（* 或 ! 表示无密码/锁定）
#    组密码允许非组成员通过 newgrp 临时切换到该组
#    实际上很少使用
# 3. 组管理员（可以添加/删除成员）
# 4. 组成员（与 /etc/group 相同）
```

**四个文件的关系**：

```
┌──────────────────────────────────────────────────────────────┐
│  /etc/passwd              /etc/shadow                        │
│  ┌─────────────────┐      ┌──────────────────┐               │
│  │ alice:x:1000:...│      │ alice:$6$salt:...│               │
│  └────────┬────────┘      └──────────────────┘               │
│           │ (用户名关联)                                     │
│           ▼                                                  │
│  /etc/group               /etc/gshadow                       │
│  ┌─────────────────┐      ┌──────────────────┐               │
│  │ sudo:x:27:alice │      │ sudo:*::alice    │               │
│  │ alice:x:1000:   │      │ alice:!::        │               │
│  └─────────────────┘      └──────────────────┘               │
└──────────────────────────────────────────────────────────────┘
```

---

### 3. 用户管理命令详解

#### 3.1 useradd -- 创建用户

```bash
# 基本语法
useradd [选项] 用户名

# 完整示例：创建一个 SRE 用户
useradd \
    -m \                    # 创建家目录 /home/username
    -u 1005 \               # 指定 UID
    -g users \              # 指定主组（默认创建同名组）
    -G sudo,docker,adm \    # 附加组列表
    -s /bin/bash \          # 登录 Shell
    -c "SRE Engineer" \     # 注释（通常是全名/职位）
    -d /home/sreuser \      # 指定家目录路径
    -e 2027-12-31 \         # 账户过期日期
    -f 90 \                 # 密码过期后宽限天数（-1 永不锁定）
    -k /etc/skel \          # 骨架目录（家目录模板）
    -r \                    # 创建系统用户（UID 自动分配）
    sreuser

# 常用简写
useradd -m -s /bin/bash sreuser                    # 最简形式
useradd -m -s /bin/bash -G sudo sreuser            # 加 sudo 权限
useradd -r -s /sbin/nologin -d /var/lib/app appuser # 系统服务用户
```

**useradd 默认值配置**：

```bash
# /etc/default/useradd
GROUP=100           # 默认 GID
HOME=/home          # 家目录父路径
INACTIVE=-1         # 密码过期后不锁定
EXPIRE=             # 账户不过期
SHELL=/bin/bash     # 默认 Shell
SKEL=/etc/skel      # 骨架目录
CREATE_MAIL_SPOOL=yes # 创建邮件 spool

# /etc/login.defs（更全面的默认配置）
MAIL_DIR /var/mail
PASS_MAX_DAYS 99999    # 密码最大有效期
PASS_MIN_DAYS 0        # 密码最小修改间隔
PASS_MIN_LEN 8         # 密码最小长度（pam_pwquality 会覆盖）
PASS_WARN_AGE 7        # 过期警告天数
UID_MIN 1000           # 普通用户最小 UID
UID_MAX 60000          # 普通用户最大 UID
ENCRYPT_METHOD SHA512  # 密码哈希算法
CREATE_HOME yes        # 是否默认创建家目录
```

**骨架目录（/etc/skel）**：

```bash
# /etc/skel 中的文件会在创建用户时复制到新家目录
ls -la /etc/skel/
# .bash_logout    # 退出时执行
# .bashrc         # 每次打开 bash 时执行
# .profile        # 登录时执行

# 自定义骨架目录
# 添加公司特定的配置文件
cat > /etc/skel/.vimrc << 'EOF'
set number
set tabstop=4
set expandtab
EOF

# 添加 .ssh 目录模板
mkdir -p /etc/skel/.ssh
chmod 700 /etc/skel/.ssh
```

#### 3.2 usermod -- 修改用户

```bash
# 语法
usermod [选项] 用户名

# 常用操作
usermod -aG docker alice        # 添加到 docker 组（-a 必须配合 -G）
usermod -G docker,sudo alice    # 设置附加组（覆盖！不加 -a 会移除其他组）
usermod -s /sbin/nologin alice  # 禁止交互登录
usermod -d /new/home -m alice   # 移动家目录（-m 迁移文件）
usermod -l newname alice        # 修改用户名
usermod -L alice                # 锁定账户（密码前加 !）
usermod -U alice                # 解锁账户
usermod -e 2027-12-31 alice     # 设置账户过期日期
usermod -c "New Comment" alice  # 修改注释
usermod -u 2000 alice           # 修改 UID

# ⚠️ 危险操作：-G 不带 -a 会覆盖所有附加组！
usermod -G docker alice         # alice 只剩 docker 组，sudo 组被移除！
usermod -aG docker alice        # 正确：追加 docker 组，保留其他组
```

#### 3.3 userdel -- 删除用户

```bash
# 基本删除（保留家目录）
userdel alice

# 完全删除（家目录 + 邮件 spool）
userdel -r alice

# 强制删除（即使用户正在登录）
userdel -rf alice

# 删除前的安全检查清单
# 1. 检查用户正在运行的进程
ps -u alice
pgrep -u alice

# 2. 检查用户的 crontab
crontab -u alice -l

# 3. 检查用户的 at 任务
atq | grep alice

# 4. 检查用户的邮件
ls /var/mail/alice 2>/dev/null

# 5. 检查用户拥有的文件
find / -user alice -not -path "/proc/*" 2>/dev/null | head -20

# 6. 备份家目录
tar -czf /backup/alice_home_$(date +%Y%m%d).tar.gz /home/alice/
```

#### 3.4 组管理命令

```bash
# 创建组
groupadd developers                    # 创建普通组
groupadd -r systemgroup                # 创建系统组（GID < 1000）
groupadd -g 1500 customgroup           # 指定 GID

# 修改组
groupmod -n newname oldname            # 修改组名
groupmod -g 1501 groupname             # 修改 GID

# 删除组
groupdel groupname                     # 删除组（确保没有用户以它为主组）

# 管理组成员
gpasswd -a alice developers            # 添加用户到组
gpasswd -d alice developers            # 从组中移除用户
gpasswd -A alice developers            # 设置组管理员

# 查看组信息
getent group developers                # 查看组信息
getent group | grep alice              # 查看用户所属的所有组
lid -g developers                      # 显示组成员（需要 libuser）
```

---

### 4. sudo 工作原理与配置

#### 4.1 sudo 的工作原理

```
用户执行 sudo 命令
       │
       ▼
  sudo 检查 /etc/sudoers
  检查用户是否有权执行该命令
       │
       ├── 无权限 → 拒绝，记录日志
       │
       ├── 有权限，需要密码 → 提示输入密码
       │    │
       │    ├── 密码正确 → 执行命令
       │    └── 密码错误 → 拒绝，记录日志
       │
       └── 有权限，NOPASSWD → 直接执行命令
            │
            ▼
       命令以指定的用户身份（通常是 root）运行
       同时记录到 /var/log/auth.log 或 /var/log/secure
            │
            ▼
       sudo 缓存认证结果（默认 15 分钟内免密）
```

**sudo 与 su 的核心区别**：

```
┌────────────────┬────────────────────────┬─────────────────────────┐
│  特性           │  sudo                   │  su                      │
├────────────────┼────────────────────────┼─────────────────────────┤
│  认证方式       │  当前用户自己的密码      │  目标用户的密码           │
│  权限范围       │  单条命令               │  完整的 shell 会话        │
│  审计日志       │  详细记录每个命令        │  只记录 su 本身           │
│  配置粒度       │  可精确到单个命令        │  全有或全无               │
│  密码缓存       │  15 分钟有效            │  无缓存                   │
│  root 密码      │  不需要知道 root 密码    │  需要知道 root 密码       │
│  安全性         │  更安全（最小权限）      │  较差（暴露 root 密码）    │
│  推荐程度       │  ⭐⭐⭐⭐⭐ 生产环境必用  │  ⭐⭐ 仅紧急场景           │
└────────────────┴────────────────────────┴─────────────────────────┘
```

#### 4.2 /etc/sudoers 语法详解

**重要**：永远使用 `visudo` 编辑 sudoers 文件，它会在保存时检查语法错误。

```bash
# 基本语法格式
# 用户  主机=(运行身份:运行组)  命令列表

# 示例解析
alice  ALL=(ALL:ALL)  ALL
# │    │   │   │     │
# │    │   │   │     └── 可以执行所有命令
# │    │   │   └── 可以切换到任何组
# │    │   └── 可以切换到任何用户
# │    └── 在任何主机上
# └── 用户 alice

# 常用配置示例

# 1. 完全 sudo 权限（需输入密码）
alice  ALL=(ALL:ALL)  ALL

# 2. 完全 sudo 权限（免密码）
alice  ALL=(ALL:ALL)  NOPASSWD: ALL

# 3. 用户组权限
%sudo   ALL=(ALL:ALL)  ALL
%devops ALL=(ALL:ALL)  ALL

# 4. 只允许执行特定命令
alice  ALL=(ALL)  /usr/bin/systemctl restart nginx, \
                  /usr/bin/systemctl status nginx

# 5. 只允许以特定用户身份执行
alice  ALL=(www-data)  /usr/bin/kill

# 6. 命令别名（简化配置）
Cmnd_Alias WEB_CMDS = /usr/bin/systemctl restart nginx, \
                       /usr/bin/systemctl reload nginx, \
                       /usr/bin/systemctl status nginx, \
                       /usr/bin/tail -f /var/log/nginx/*.log
Cmnd_Alias DOCKER_CMDS = /usr/bin/docker, /usr/bin/docker-compose

%webteam ALL=(ALL)  NOPASSWD: WEB_CMDS
%devteam ALL=(ALL)  NOPASSWD: DOCKER_CMDS

# 7. 用户别名
User_Alias ADMINS = alice, bob, charlie
User_Alias DEVS = dev1, dev2, dev3

# 8. 主机别名
Host_Alias WEBSERVERS = web01, web02, web03
Host_Alias DBSERVERS = db01, db02

ADMINS WEBSERVERS=(ALL) ALL
DEVS WEBSERVERS=(ALL) NOPASSWD: WEB_CMDS

# 9. 限制 sudo 命令不能带参数
alice ALL=(ALL) /usr/bin/passwd [A-Za-z]*, !/usr/bin/passwd root
# 允许修改其他用户密码，但不能修改 root 密码

# 10. sudoers 中的通配符
alice ALL=(ALL) /usr/bin/systemctl restart *
# 允许重启任何服务（谨慎使用）

# 11. sudoers Include 机制
# /etc/sudoers 可以包含其他文件
@includedir /etc/sudoers.d    # 包含目录下所有文件
#includedir /etc/sudoers.d    # 同上（旧语法）

# 推荐做法：在 /etc/sudoers.d/ 下创建独立文件
echo "alice ALL=(ALL) NOPASSWD: /usr/bin/docker" > /etc/sudoers.d/alice
chmod 440 /etc/sudoers.d/alice
```

#### 4.3 sudo 日志审计

```bash
# sudo 日志位置
# Ubuntu/Debian: /var/log/auth.log
# CentOS/RHEL: /var/log/secure

# 查看 sudo 使用记录
grep "sudo:" /var/log/auth.log | tail -20

# 日志格式示例：
# Apr 26 10:30:15 server sudo: alice : TTY=pts/0 ; PWD=/home/alice ;
#   USER=root ; COMMAND=/usr/bin/systemctl restart nginx

# 统计用户 sudo 使用频率
grep "sudo:" /var/log/auth.log \
  | awk '{print $6}' \
  | sort | uniq -c | sort -rn

# 查看失败的 sudo 尝试（可能的安全事件）
grep "sudo.*NOT_ALLOWED\|sudo.*authentication failure" /var/log/auth.log

# 查看特定用户的 sudo 历史
grep "sudo.*alice" /var/log/auth.log | tail -20

# 配置 sudo 日志到独立文件
# 在 /etc/sudoers 中添加：
Defaults logfile=/var/log/sudo.log
Defaults log_input, log_output    # 记录输入输出（更详细）
Defaults iolog_dir=/var/log/sudo-io/%{user}
```

#### 4.4 sudo 安全配置最佳实践

```bash
# /etc/sudoers 安全配置

# 1. 密码超时设置
Defaults timestamp_timeout=5     # 5 分钟后重新要求密码（默认 15）
Defaults timestamp_timeout=0     # 每次都要求密码（最安全）

# 2. 密码重试次数
Defaults passwd_tries=3          # 最多尝试 3 次

# 3. sudo 操作日志
Defaults logfile=/var/log/sudo.log
Defaults log_input, log_output
Defaults iolog_dir=/var/log/sudo-io

# 4. 安全限制
Defaults requiretty              # 要求有 TTY（防止 cron 中误用 sudo）
Defaults use_pty                 # 使用伪终端
Defaults env_reset               # 重置环境变量
Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 5. 禁止危险操作
Defaults !visiblepw              # 不显示密码输入
Defaults !env_editor             # 禁止使用环境变量指定编辑器

# 6. 审计配置
Defaults!/usr/bin/visudo  log_output   # 记录 visudo 的使用
```

---

### 5. PAM（Pluggable Authentication Modules）框架

#### 5.1 PAM 架构概述

```
┌──────────────────────────────────────────────────────────────┐
│  PAM 架构                                                    │
│                                                              │
│  应用程序层                                                   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │
│  │ sshd │ │ sudo │ │ login│ │ su   │ │ passwd│              │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘              │
│     │        │        │        │        │                    │
│     └────────┴────────┴────────┴────────┘                    │
│                    │                                         │
│              PAM API（libpam）                                │
│                    │                                         │
│  ┌─────────────────────────────────────────────┐            │
│  │  PAM 配置层（/etc/pam.d/）                   │            │
│  │  ┌─────┐ ┌──────┐ ┌────────┐ ┌──────────┐  │            │
│  │  │sshd │ │ sudo │ │ login  │ │ common-  │  │            │
│  │  │     │ │      │ │        │ │ auth     │  │            │
│  │  └─────┘ └──────┘ └────────┘ └──────────┘  │            │
│  └─────────────────────────────────────────────┘            │
│                    │                                         │
│  ┌─────────────────────────────────────────────┐            │
│  │  PAM 模块层（/lib/security/ 或 /lib/x86_64- │            │
│  │  linux-gnu/security/）                       │            │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────┐ │            │
│  │  │pam_unix.so │ │pam_ldap.so │ │pam_      │ │            │
│  │  │（本地认证） │ │（LDAP认证） │ │tally2.so│ │            │
│  │  └────────────┘ └────────────┘ │（登录失败│ │            │
│  │  ┌────────────┐ ┌────────────┐ │ 计数）   │ │            │
│  │  │pam_pwquality││pam_limits.so│└──────────┘ │            │
│  │  │（密码强度） │ │（资源限制） │              │            │
│  │  └────────────┘ └────────────┘              │            │
│  └─────────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2 PAM 配置文件

```bash
# PAM 配置目录
ls /etc/pam.d/
# common-auth     # 通用认证配置
# common-account  # 通用账户配置
# common-password # 通用密码配置
# common-session  # 通用会话配置
# sshd            # SSH 专用
# sudo            # sudo 专用
# login           # 登录专用

# 每个 PAM 配置文件的四种管理组：
# auth      - 认证（验证用户身份）
# account   - 账户（检查账户是否有效/过期）
# password  - 密码（密码修改策略）
# session   - 会话（登录前后的操作）

# 每行格式：
# 类型  控制标志  模块路径  [参数]
# auth  required  pam_unix.so  nullok

# 控制标志：
# required    - 必须通过，失败后继续检查其他模块（最终失败）
# requisite   - 必须通过，失败后立即返回（不继续检查）
# sufficient  - 通过则立即成功（如果前面没有 required 失败）
# optional    - 可选，不影响最终结果
# include     - 包含其他配置文件
```

#### 5.3 常用 PAM 模块

```bash
# 1. pam_unix.so -- 传统 Unix 认证
auth     required   pam_unix.so nullok
# nullok 允许空密码用户登录（安全环境应去掉）

# 2. pam_pwquality.so -- 密码复杂度检查
password required   pam_pwquality.so retry=3 minlen=12 \
         dcredit=-1 ucredit=-1 ocredit=-1 lcredit=-1
# dcredit=-1: 至少 1 个数字
# ucredit=-1: 至少 1 个大写字母
# ocredit=-1: 至少 1 个特殊字符
# lcredit=-1: 至少 1 个小写字母

# 3. pam_tally2.so / pam_faillock.so -- 登录失败计数
auth     required   pam_faillock.so preauth deny=5 unlock_time=900
auth     required   pam_faillock.so authfail deny=5 unlock_time=900
# 5 次失败后锁定 900 秒（15 分钟）

# 4. pam_limits.so -- 资源限制
session  required   pam_limits.so
# 配置文件：/etc/security/limits.conf

# 5. pam_umask.so -- umask 设置
session  optional   pam_umask.so umask=0027

# 6. pam_wheel.so -- 限制 su 命令
auth     required   pam_wheel.so use_uid
# 只有 wheel 组的用户才能使用 su 切换到 root
```

#### 5.4 PAM 实战配置

```bash
# 企业级 SSH 安全 PAM 配置
cat > /etc/pam.d/sshd << 'EOF'
# 认证
auth    required    pam_env.so
auth    required    pam_faillock.so preauth deny=5 unlock_time=900
auth    required    pam_unix.so
auth    required    pam_faillock.so authfail deny=5 unlock_time=900

# 账户
account required    pam_nologin.so
account required    pam_unix.so

# 密码
password required   pam_pwquality.so retry=3 minlen=12
password required   pam_unix.so sha512 shadow

# 会话
session required    pam_limits.so
session required    pam_unix.so
session optional    pam_umask.so umask=0027
EOF
```

---

### 6. 密码策略配置

#### 6.1 chage -- 密码过期管理

```bash
# 查看用户密码策略
chage -l alice
# Last password change                    : Apr 26, 2026
# Password expires                        : Jul 25, 2026
# Password inactive                       : never
# Account expires                         : never
# Minimum number of days between change   : 7
# Maximum number of days between change   : 90
# Number of days of warning before expiry : 14

# 设置密码策略
chage -M 90 alice          # 密码最长有效期 90 天
chage -m 7 alice           # 密码最短使用 7 天才能修改
chage -W 14 alice          # 过期前 14 天开始警告
chage -I 30 alice          # 密码过期 30 天后自动锁定
chage -E 2027-12-31 alice  # 账户过期日期
chage -d 2026-04-26 alice  # 强制在指定日期修改密码
chage -d 0 alice           # 下次登录强制修改密码

# 交互式设置（适合批量管理）
chage alice
# 依次提示输入各个参数
```

#### 6.2 /etc/login.defs 全局默认策略

```bash
# /etc/login.defs 关键配置项

# 密码策略
PASS_MAX_DAYS   90       # 密码最长有效期
PASS_MIN_DAYS   7        # 密码最短使用天数
PASS_MIN_LEN    12       # 密码最小长度（pam_pwquality 会覆盖）
PASS_WARN_AGE   14       # 过期警告天数

# UID/GID 范围
UID_MIN         1000
UID_MAX         60000
GID_MIN         1000
GID_MAX         60000
SYS_UID_MIN     100
SYS_UID_MAX     999
SYS_GID_MIN     100
SYS_GID_MAX     999

# 用户创建
CREATE_HOME     yes      # 是否默认创建家目录
USERGROUPS_ENAB yes      # 创建用户时创建同名组
UMASK           027      # 默认 umask

# 密码加密
ENCRYPT_METHOD  SHA512   # 密码哈希算法
SHA_CRYPT_MIN_ROUNDS 5000  # SHA 最小迭代次数
SHA_CRYPT_MAX_ROUNDS 5000  # SHA 最大迭代次数
```

#### 6.3 pam_pwquality 密码复杂度

```bash
# 配置文件：/etc/security/pwquality.conf

# 密码最小长度
minlen = 12

# 字符类要求（负数表示"至少 N 个"，正数表示"最多缺少 N 个"）
dcredit = -1     # 至少 1 个数字
ucredit = -1     # 至少 1 个大写字母
lcredit = -1     # 至少 1 个小写字母
ocredit = -1     # 至少 1 个特殊字符

# 密码历史（不允许重用最近 N 个密码）
remember = 5     # 需要在 PAM 中配合 pam_pwhistory.so

# 密码重试次数
retry = 3

# 最大连续相同字符
maxrepeat = 3

# 最大字符序列（如 abc, 123）
maxsequence = 3

# 新旧密码最少不同字符数
difok = 5

# 检查是否包含用户名
usercheck = 1

# 密码强度检查（基于字典）
# dictcheck = 1

# 完整配置示例
cat > /etc/security/pwquality.conf << 'EOF'
minlen = 12
dcredit = -1
ucredit = -1
lcredit = -1
ocredit = -1
maxrepeat = 3
maxsequence = 3
difok = 5
retry = 3
EOF
```

---

### 7. 用户生命周期管理

#### 7.1 入职流程

```bash
#!/bin/bash
# onboarding.sh -- 新员工入职脚本

set -euo pipefail

USERNAME="${1:?用法: $0 <用户名> <全名> <部门> <SSH公钥文件>}"
FULLNAME="${2:?缺少全名}"
DEPARTMENT="${3:?缺少部门(dev/ops/qa)}"
SSH_PUBKEY="${4:-}"

# 验证部门
case "$DEPARTMENT" in
    dev|ops|qa) ;;
    *) echo "错误：部门必须是 dev/ops/qa"; exit 1 ;;
esac

echo "=== 新员工入职: $USERNAME ($FULLNAME) ==="

# 1. 创建用户
useradd -m -s /bin/bash -c "$FULLNAME" "$USERNAME"

# 2. 设置初始密码（首次登录强制修改）
TEMP_PASS=$(openssl rand -base64 12)
echo "$USERNAME:$TEMP_PASS" | chpasswd
chage -d 0 "$USERNAME"    # 下次登录强制修改密码

# 3. 根据部门分配权限
case "$DEPARTMENT" in
    dev)
        usermod -aG developers,docker "$USERNAME"
        cat > /etc/sudoers.d/$USERNAME << SUDO
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose
SUDO
        ;;
    ops)
        usermod -aG operators,docker "$USERNAME"
        cat > /etc/sudoers.d/$USERNAME << SUDO
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart *, \
                              /usr/bin/systemctl stop *, \
                              /usr/bin/systemctl start *, \
                              /usr/bin/systemctl status *, \
                              /usr/bin/journalctl, \
                              /usr/bin/docker
SUDO
        ;;
    qa)
        usermod -aG testers "$USERNAME"
        # QA 通常不需要 sudo
        ;;
esac
chmod 440 /etc/sudoers.d/$USERNAME

# 4. 配置 SSH 密钥
mkdir -p /home/$USERNAME/.ssh
chmod 700 /home/$USERNAME/.ssh
if [ -n "$SSH_PUBKEY" ] && [ -f "$SSH_PUBKEY" ]; then
    cp "$SSH_PUBKEY" /home/$USERNAME/.ssh/authorized_keys
fi
chmod 600 /home/$USERNAME/.ssh/authorized_keys 2>/dev/null || true
chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh

# 5. 设置密码策略
chage -M 90 -m 7 -W 14 "$USERNAME"

# 6. 配置 umask
echo "umask 0027" >> /home/$USERNAME/.bashrc

# 7. 记录日志
echo "$(date '+%Y-%m-%d %H:%M:%S') ONBOARD $USERNAME $FULLNAME $DEPARTMENT" \
  >> /var/log/user_management.log

echo ""
echo "=== 入职完成 ==="
echo "用户名: $USERNAME"
echo "初始密码: $TEMP_PASS"
echo "部门: $DEPARTMENT"
echo "注意：首次登录需修改密码"
```

#### 7.2 离职流程

```bash
#!/bin/bash
# offboarding.sh -- 员工离职清理脚本

set -euo pipefail

USERNAME="${1:?用法: $0 <用户名>}"
BACKUP_DIR="/backup/users"
RETENTION_DAYS=90

echo "=== 员工离职处理: $USERNAME ==="

# 1. 验证用户存在
id "$USERNAME" &>/dev/null || { echo "错误：用户不存在"; exit 1; }

# 2. 记录当前状态
echo "--- 当前用户信息 ---"
id "$USERNAME"
ps -u "$USERNAME" 2>/dev/null || echo "无运行进程"
crontab -u "$USERNAME" -l 2>/dev/null || echo "无 crontab"

# 3. 终止用户所有进程
echo ""
echo "--- 终止用户进程 ---"
pkill -u "$USERNAME" 2>/dev/null || true
sleep 2
pkill -9 -u "$USERNAME" 2>/dev/null || true
echo "已终止所有进程"

# 4. 立即锁定账户（第一步：禁止登录）
echo ""
echo "--- 锁定账户 ---"
usermod -L "$USERNAME"
passwd -l "$USERNAME"    # 双重锁定
echo "账户已锁定"

# 5. 清理 SSH 密钥
echo ""
echo "--- 清理 SSH 密钥 ---"
if [ -f /home/$USERNAME/.ssh/authorized_keys ]; then
    mv /home/$USERNAME/.ssh/authorized_keys \
       /home/$USERNAME/.ssh/authorized_keys.disabled
    echo "已禁用 SSH 密钥"
fi

# 6. 备份家目录
echo ""
echo "--- 备份家目录 ---"
mkdir -p "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/${USERNAME}_$(date +%Y%m%d).tar.gz"
if [ -d /home/$USERNAME ]; then
    tar -czf "$BACKUP_FILE" /home/$USERNAME/
    chmod 600 "$BACKUP_FILE"
    echo "备份已保存到: $BACKUP_FILE"
fi

# 7. 清理 crontab
echo ""
echo "--- 清理定时任务 ---"
crontab -u "$USERNAME" -r 2>/dev/null && echo "已清除 crontab" || echo "无 crontab"

# 8. 移除 sudo 权限
echo ""
echo "--- 移除 sudo 权限 ---"
if [ -f /etc/sudoers.d/$USERNAME ]; then
    rm -f /etc/sudoers.d/$USERNAME
    echo "已移除 sudoers 配置"
fi

# 9. 删除用户（保留家目录 30 天后再清理）
echo ""
echo "--- 删除用户账户 ---"
userdel "$USERNAME"
echo "用户账户已删除"
echo "家目录将在 $RETENTION_DAYS 天后清理"
echo "备份位置: $BACKUP_FILE"

# 10. 设置家目录清理定时任务
echo "0 2 * * * find /home/$USERNAME -maxdepth 0 -mtime +$RETENTION_DAYS -exec rm -rf {} +" \
  | crontab - 2>/dev/null || true

# 11. 记录日志
echo "$(date '+%Y-%m-%d %H:%M:%S') OFFBOARD $USERNAME $BACKUP_FILE" \
  >> /var/log/user_management.log

echo ""
echo "=== 离职处理完成 ==="
echo "后续操作："
echo "  1. 通知相关系统移除该用户的访问权限"
echo "  2. 检查 CI/CD 系统中的关联账户"
echo "  3. 通知云服务提供商移除 IAM 用户（如有）"
```

#### 7.3 定期审计脚本

```bash
#!/bin/bash
# user_audit.sh -- 用户安全审计脚本

set -euo pipefail

echo "========================================"
echo "  用户安全审计报告  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 1. 检查空密码用户
echo ""
echo "=== 空密码用户（严重风险）==="
while IFS=: read -r user pass rest; do
    if [ "$pass" = "" ] || [ "$pass" = "!" ] || [ "$pass" = "*" ]; then
        continue
    fi
    # 检查密码字段是否为空
    if [ ${#pass} -eq 0 ]; then
        echo "  RISK: $user 没有密码！"
    fi
done < /etc/shadow 2>/dev/null

# 更准确的检查：使用 passwd -S
echo "密码状态检查："
for user in $(cut -d: -f1 /etc/passwd); do
    status=$(passwd -S "$user" 2>/dev/null | awk '{print $2}')
    [ "$status" = "NP" ] && echo "  RISK: $user 无密码"
    [ "$status" = "L" ] && echo "  INFO: $user 已锁定"
done

# 2. 检查 UID 0 用户（非 root 的超级用户）
echo ""
echo "=== UID 0 用户（严重风险）==="
awk -F: '$3 == 0 && $1 != "root" {print "  RISK: " $1 " has UID 0"}' /etc/passwd

# 3. 检查可登录的系统用户
echo ""
echo "=== 可登录的系统用户（UID < 1000 且有 shell）==="
awk -F: '$3 < 1000 && $3 > 0 && $7 !~ /nologin|false|sync|halt|shutdown/ {
    print "  WARN: " $1 " (UID=" $3 ", Shell=" $7 ")"
}' /etc/passwd

# 4. 检查密码过期
echo ""
echo "=== 密码即将过期（30 天内）==="
for user in $(awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' /etc/passwd); do
    expire=$(chage -l "$user" 2>/dev/null | grep "Password expires" | cut -d: -f2)
    if [[ "$expire" != "never" ]] && [ -n "$expire" ]; then
        expire_epoch=$(date -d "$expire" +%s 2>/dev/null || echo 0)
        now_epoch=$(date +%s)
        days_left=$(( (expire_epoch - now_epoch) / 86400 ))
        [ "$days_left" -lt 30 ] && [ "$days_left" -gt 0 ] && \
            echo "  WARN: $user 密码将在 $days_left 天后过期"
        [ "$days_left" -le 0 ] && echo "  RISK: $user 密码已过期"
    fi
done

# 5. 检查 SUID 文件
echo ""
echo "=== SUID 文件（安全审计）==="
find / -type f -perm /4000 -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null \
  | while read -r f; do
    owner=$(stat -c '%U' "$f")
    echo "  $f (owner: $owner)"
done

# 6. 检查无主文件
echo ""
echo "=== 无主文件（UID/GID 不存在）==="
find /home -nouser -o -nogroup 2>/dev/null | head -10

# 7. 检查 sudo 配置
echo ""
echo "=== sudo NOPASSWD 配置 ==="
grep -r "NOPASSWD" /etc/sudoers /etc/sudoers.d/ 2>/dev/null

# 8. 检查 SSH 配置安全
echo ""
echo "=== SSH 安全配置 ==="
echo "PasswordAuthentication: $(grep -E '^PasswordAuthentication' /etc/ssh/sshd_config || echo '未设置')"
echo "PermitRootLogin: $(grep -E '^PermitRootLogin' /etc/ssh/sshd_config || echo '未设置')"

# 9. 最近登录失败
echo ""
echo "=== 最近登录失败（前 10 个 IP）==="
grep "Failed password" /var/log/auth.log 2>/dev/null \
  | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -10

echo ""
echo "========================================"
echo "  审计完成"
echo "========================================"
```

---

### 8. SRE 实战案例

#### 8.1 案例一：员工离职后账户未清理导致安全事件

**事件描述**：某公司开发人员离职后，其账户未被及时清理。三个月后，该账户的 SSH 密钥被泄露，攻击者利用该账户登录服务器并植入了挖矿程序。

**排查过程**：

```bash
# 1. 发现异常：CPU 使用率持续 100%
top -bn1 | head -20
# 发现 minerd 进程占用大量 CPU

# 2. 查找进程所属用户
ps aux | grep minerd
# 发现以已离职员工的账户运行

# 3. 检查登录记录
last | grep departed_user
# 显示最近有从异常 IP 登录

# 4. 检查 SSH 密钥
cat /home/departed_user/.ssh/authorized_keys
# 发现密钥仍然有效

# 5. 紧急处理
# a. 终止恶意进程
pkill -9 -u departed_user

# b. 锁定账户
usermod -L departed_user

# c. 删除 SSH 密钥
rm /home/departed_user/.ssh/authorized_keys

# d. 检查是否有后门
find / -user departed_user -perm -u+x -type f 2>/dev/null
crontab -u departed_user -l
```

**预防措施**：

```bash
# 1. 建立离职流程检查清单
# 2. 使用自动化脚本处理离职
# 3. 定期审计用户账户
# 4. 配置账户过期策略
# 5. 集成 HR 系统自动触发账户清理
```

#### 8.2 案例二：sudo 权限过大导致的误操作

**事件描述**：SRE 工程师拥有 `ALL=(ALL) NOPASSWD: ALL` 权限，在排查问题时误执行了 `rm -rf /var/lib/docker/` 而非 `/var/lib/docker/tmp/`，导致所有容器数据丢失。

**根因分析**：

```bash
# 1. sudo 权限过于宽泛
grep "engineer" /etc/sudoers
# engineer ALL=(ALL) NOPASSWD: ALL    ← 应该限制具体命令

# 2. 没有启用 sudo 日志
# 无法追溯具体执行了什么命令

# 3. 没有使用 --preserve-env 或 safe-rm 等防护工具
```

**改进方案**：

```bash
# 1. 限制 sudo 命令范围
cat > /etc/sudoers.d/engineer << 'EOF'
# SRE 权限 - 只允许服务管理
engineer ALL=(ALL) NOPASSWD: \
    /usr/bin/systemctl restart *, \
    /usr/bin/systemctl stop *, \
    /usr/bin/systemctl start *, \
    /usr/bin/systemctl status *, \
    /usr/bin/journalctl *, \
    /usr/bin/docker restart *, \
    /usr/bin/docker logs *
EOF

# 2. 对危险命令要求密码
Defaults:engineer timestamp_timeout=0

# 3. 启用 sudo 日志
Defaults logfile=/var/log/sudo.log
Defaults log_input, log_output

# 4. 使用 safe-rm 替代 rm
apt install safe-rm
# safe-rm 会阻止删除关键目录

# 5. 使用 trash-cli 替代 rm
apt install trash-cli
alias rm='trash-put'
```

#### 8.3 案例三：批量用户管理脚本

**场景**：需要从 CSV 文件批量创建/管理用户。

```bash
#!/bin/bash
# batch_user_mgmt.sh -- 批量用户管理

# CSV 格式：username,fullname,department,email,ssh_pubkey
CSV_FILE="${1:?用法: $0 <users.csv>}"

while IFS=, read -r username fullname department email sshkey; do
    # 跳过标题行
    [[ "$username" == "username" ]] && continue
    # 跳过空行
    [[ -z "$username" ]] && continue

    echo "处理用户: $username ($fullname)"

    # 检查用户是否已存在
    if id "$username" &>/dev/null; then
        echo "  用户已存在，跳过创建"
        continue
    fi

    # 创建用户
    useradd -m -s /bin/bash -c "$fullname - $email" "$username"

    # 设置初始密码
    temp_pass=$(openssl rand -base64 12)
    echo "$username:$temp_pass" | chpasswd
    chage -d 0 "$username"

    # 部门权限
    case "$department" in
        dev) usermod -aG developers,docker "$username" ;;
        ops) usermod -aG operators,docker,sudo "$username" ;;
        qa)  usermod -aG testers "$username" ;;
    esac

    # SSH 密钥
    if [ -n "$sshkey" ]; then
        mkdir -p /home/$username/.ssh
        echo "$sshkey" > /home/$username/.ssh/authorized_keys
        chmod 700 /home/$username/.ssh
        chmod 600 /home/$username/.ssh/authorized_keys
        chown -R $username:$username /home/$username/.ssh
    fi

    # 密码策略
    chage -M 90 -m 7 -W 14 "$username"

    echo "  创建完成: $username / $temp_pass"

done < "$CSV_FILE"
```

---

## 💻 实战练习

### 练习 1：解析 /etc/passwd 和 /etc/shadow

```bash
# 解析以下 /etc/passwd 行，说明每个字段的含义
nginx:x:101:101:nginx web server:/var/www:/usr/sbin/nologin

# 解析以下 /etc/shadow 行
alice:$6$rounds=5000$abcdefgh$XYZ123...:19845:7:90:14:10::
```

<details>
<summary>答案</summary>

**/etc/passwd 解析**：
- `nginx` -- 用户名
- `x` -- 密码在 /etc/shadow 中
- `101` -- UID 101（系统用户）
- `101` -- GID 101（主组）
- `nginx web server` -- 注释/描述
- `/var/www` -- 家目录
- `/usr/sbin/nologin` -- 不允许交互登录

**/etc/shadow 解析**：
- `alice` -- 用户名
- `$6$rounds=5000$abcdefgh$XYZ123...` -- SHA-512 加密密码
- `19845` -- 最后修改密码日期（2024-04-25，自 1970-01-01 的天数）
- `7` -- 密码最短使用 7 天
- `90` -- 密码最长有效 90 天
- `14` -- 过期前 14 天警告
- `10` -- 过期后 10 天宽限期
</details>

### 练习 2：配置 sudo 权限

为以下场景编写 /etc/sudoers 配置：
1. 用户 `deployer` 只能重启 nginx 和 docker 服务
2. 组 `webteam` 可以查看日志和重启 web 服务
3. 用户 `auditor` 只能执行只读命令（ps, top, cat, tail, less）

<details>
<summary>参考答案</summary>

```bash
# /etc/sudoers.d/deploy
Cmnd_Alias DEPLOY_CMDS = /usr/bin/systemctl restart nginx, \
                          /usr/bin/systemctl restart docker, \
                          /usr/bin/systemctl reload nginx

deployer ALL=(ALL) NOPASSWD: DEPLOY_CMDS

# /etc/sudoers.d/webteam
Cmnd_Alias WEB_CMDS = /usr/bin/systemctl restart nginx, \
                       /usr/bin/systemctl reload nginx, \
                       /usr/bin/systemctl status nginx, \
                       /usr/bin/journalctl -u nginx, \
                       /usr/bin/tail -f /var/log/nginx/*.log

%webteam ALL=(ALL) NOPASSWD: WEB_CMDS

# /etc/sudoers.d/auditor
Cmnd_Alias READONLY_CMDS = /usr/bin/ps, /usr/bin/top, /usr/bin/cat, \
                            /usr/bin/tail, /usr/bin/less, /usr/bin/head, \
                            /usr/bin/systemctl status *, \
                            /usr/bin/journalctl

auditor ALL=(ALL) NOPASSWD: READONLY_CMDS
Defaults:auditor timestamp_timeout=0
```
</details>

### 练习 3：编写完整的用户生命周期管理方案

设计一个包含入职、在职（权限变更、密码轮换）、离职全流程的用户管理方案。

<details>
<summary>参考方案要点</summary>

**入职**：
1. HR 系统触发 → 自动调用入职脚本
2. 创建用户 + 设置部门权限 + 配置 SSH 密钥
3. 生成临时密码，首次登录强制修改
4. 记录到 CMDB/用户管理台账

**在职**：
1. 每季度密码轮换（chage -M 90）
2. 权限变更通过审批流程 → 自动化脚本执行
3. 每月审计用户权限（user_audit.sh）
4. 密码过期前 14 天邮件提醒

**离职**：
1. HR 系统触发 → 自动调用离职脚本
2. 立即锁定账户 + 清理 SSH 密钥
3. 备份家目录（保留 90 天）
4. 清理 crontab + sudo 配置
5. 通知相关系统移除访问权限
6. 30 天后删除用户和家目录
</details>

---

## 🎯 面试题精选

### 面试题 1：/etc/shadow 文件为什么权限是 640 而不是 644？

**参考答案**：
`/etc/shadow` 存储了用户的加密密码哈希。如果权限是 644（所有人可读），任何本地用户都可以获取密码哈希并进行离线暴力破解（使用 hashcat、John the Ripper 等工具）。

640 权限意味着只有 root 和 shadow 组成员可以读取，大大降低了密码泄露风险。shadow 组通常是空的，所以实际上只有 root 可以读取。

### 面试题 2：sudo 和 su 的核心区别是什么？

**参考答案**：

| 维度 | sudo | su |
|------|------|-----|
| 认证 | 当前用户密码 | 目标用户密码 |
| 范围 | 单条命令 | 完整 shell |
| 日志 | 详细记录每个命令 | 只记录 su 本身 |
| 配置 | 可精确到命令级别 | 全有或全无 |
| 安全 | 更好（最小权限 + 审计） | 较差（暴露 root 密码） |

生产环境应该使用 sudo，避免使用 su 切换到 root。

### 面试题 3：PAM 的四种管理组是什么？

**参考答案**：
- **auth**：认证，验证用户身份（如密码验证、指纹验证）
- **account**：账户管理，检查账户是否有效（如是否过期、是否允许登录）
- **password**：密码管理，密码修改时的策略（如复杂度检查、历史检查）
- **session**：会话管理，登录前后的操作（如设置资源限制、挂载目录、记录日志）

### 面试题 4：如何防止用户使用弱密码？

**参考答案**：
多层防护策略：
1. **PAM 层**：使用 `pam_pwquality.so` 设置复杂度要求（长度、字符类、重复、序列）
2. **系统层**：在 `/etc/login.defs` 设置 `PASS_MIN_LEN`、`PASS_MAX_DAYS`
3. **历史检查**：使用 `pam_pwhistory.so` 防止重用旧密码
4. **字典检查**：`pam_pwquality.so` 的 `dictcheck` 选项
5. **定期轮换**：`chage -M 90` 强制 90 天更换

### 面试题 5：UID 0 用户有什么安全隐患？

**参考答案**：
UID 0 在 Linux 中意味着 root 权限。如果系统中存在多个 UID 0 用户（除了 root），这些用户都拥有完全的 root 权限，但：
1. 审计时可能被忽视（只检查 root 用户）
2. 可能是攻击者创建的后门账户
3. 绕过了 sudo 的审计日志

检查命令：`awk -F: '$3 == 0 {print $1}' /etc/passwd`，结果应该只有 root。

### 面试题 6：usermod -aG 和 usermod -G 的区别？

**参考答案**：
- `usermod -aG group user`：将用户**追加**到指定组，保留原有的附加组
- `usermod -G group user`：**覆盖**用户的附加组列表，只保留指定的组

如果忘记加 `-a`，用户会丢失所有原有的附加组权限（包括 sudo），这在生产环境中可能造成严重问题。

### 面试题 7：/etc/passwd 中密码字段为 x 是什么意思？

**参考答案**：
`x` 表示加密密码不存储在 `/etc/passwd` 中，而是存储在 `/etc/shadow` 中。这是一种安全措施：`/etc/passwd` 权限是 644（所有人可读），如果密码存在这里，任何人都可以获取密码哈希。

历史上密码确实存在 `/etc/passwd` 中，后来分离到 `/etc/shadow`（权限 640）以提高安全性。

---

## 📚 深入阅读

### 官方文档
- [Linux man page: useradd(8)](https://man7.org/linux/man-pages/man8/useradd.8.html)
- [Linux man page: sudoers(5)](https://man7.org/linux/man-pages/man5/sudoers.5.html)
- [Linux man page: pam(8)](https://man7.org/linux/man-pages/man8/pam.8.html)
- [Linux man page: shadow(5)](https://man7.org/linux/man-pages/man5/shadow.5.html)
- [Red Hat: Managing Users and Groups](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_users_and_groups)

### 推荐书籍
- 《鸟哥的 Linux 私房菜》第 14 章 -- 账号管理
- 《Linux 系统管理与网络管理》-- 用户管理章节
- 《How Linux Works》第 7 笠 -- 用户空间

### 在线资源
- [Sudo Manual](https://www.sudo.ws/docs/man/sudoers.man/)
- [Linux PAM Administrator Guide](http://www.linux-pam.org/Linux-PAM-html/Linux-PAM_SAG.html)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks) -- 安全基线

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 /etc/passwd 每个字段的含义
- [ ] 能解释 /etc/shadow 每个字段的含义
- [ ] 理解密码哈希算法（SHA-512、yescrypt）的工作原理
- [ ] 知道 sudo 和 su 的区别及各自的适用场景
- [ ] 理解 PAM 四种管理组的作用
- [ ] 知道 UID 0 的安全含义

### 实操检查点
- [ ] 能用 useradd/usermod/userdel 管理用户
- [ ] 能正确配置 /etc/sudoers（使用 visudo）
- [ ] 能配置密码策略（chage、pam_pwquality）
- [ ] 能编写入职/离职自动化脚本
- [ ] 能编写用户安全审计脚本
- [ ] 能分析 /var/log/auth.log 中的 sudo 记录

---

*由 SRE 学习计划生成 | 2026-04-26*
