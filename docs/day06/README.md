# Day 06: 用户与用户组管理

> 📅 日期：2026-04-18  
> 📖 学习主题：用户与用户组管理  
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 06 的学习后，你应该掌握：
- 理解 用户与用户组管理 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

### 1. Linux 用户系统概述

Linux 是一个多用户操作系统，每个需要登录的用户都必须在 `/etc/passwd` 和 `/etc/shadow` 中有记录。

#### 1.1 用户类型

| 类型 | UID 范围 | 特点 | 示例 |
|------|----------|------|------|
| root | 0 | 超级管理员，拥有最高权限 | root |
| 系统用户 | 1-999 | 服务运行时使用，不能登录 | nginx, mysql, www-data |
| 普通用户 | 1000+ | 日常使用，权限受限 | sreuser, developer |

#### 1.2 相关文件

| 文件 | 用途 | 权限 |
|------|------|------|
| `/etc/passwd` | 用户账户信息 | 644 (所有用户可读) |
| `/etc/shadow` | 加密密码（仅 root 可读） | 600 |
| `/etc/group` | 用户组信息 | 644 |
| `/etc/gshadow` | 组密码（极少用） | 600 |
| `/etc/login.defs` | 用户创建默认值 | 644 |
| `/etc/default/useradd` | useradd 默认配置 | 644 |

---

### 2. 用户管理命令

#### 2.1 useradd - 创建用户

```bash
# 基本创建
useradd -m sreuser

# 详细参数
useradd [选项] 用户名

# 常用选项：
# -m          创建主目录
# -d /path    指定主目录
# -s /bin/bash    指定登录 shell
# -G group1,group2  附加组
# -u UID      指定 UID
# -c "注释"   注释信息（通常是姓名）
# -e YYYY-MM-DD  账户过期日期
```

**实战案例 - 创建 SRE 用户**：
```bash
# 创建完整信息的 SRE 用户
useradd -m \
    -c "SRE Engineer - Zhang San" \
    -s /bin/bash \
    -G sudo,docker,www-data \
    -u 1005 \
    zhangsan

# 设置密码
passwd zhangsan

# 验证创建结果
id zhangsan
# uid=1005(zhangsan) gid=1005(zhangsan) groups=1005(zhangsan),27(sudo),999(docker),33(www-data)

# 查看用户信息
grep zhangsan /etc/passwd
# zhangsan:x:1005:1005:SRE Engineer - Zhang San:/home/zhangsan:/bin/bash
```

#### 2.2 usermod - 修改用户

```bash
# 常用选项（与 useradd 相同）
usermod -aG docker zhangsan    # 添加到 docker 组（-a 必须与 -G 一起用）
usermod -s /bin/zsh zhangsan   # 更改登录 shell
usermod -L zhangsan            # 锁定账户（禁止登录）
usermod -U zhangsan            # 解锁账户
usermod -e 2025-12-31 zhangsan # 设置过期日期
usermod -d /new/home -m zhangsan # 移动主目录并迁移数据
```

**实战案例**：
```bash
# 将用户添加到 sudo 组（赋予 sudo 权限）
usermod -aG sudo zhangsan

# 验证 sudo 权限
su - zhangsan
sudo whoami   # 如果配置正确，输出 "root"

# 锁定用户（离职时使用）
sudo usermod -L zhangsan
grep zhangsan /etc/shadow
# zhangsan:!$6$...:...   # 密码前有 ! 表示锁定

# 解锁用户
sudo usermod -U zhangsan
```

#### 2.3 userdel - 删除用户

```bash
# 删除用户（保留主目录）
userdel zhangsan

# 删除用户及主目录（彻底清理）
userdel -r zhangsan

# 删除用户并删除所有相关文件（邮件、计划任务等）
userdel -r -f zhangsan
```

**安全提醒**：删除用户前，确保：
1. 该用户没有正在运行的进程
2. 没有重要的数据在主目录
3. 检查 `/var/spool/cron/` 是否有该用户的 crontab

```bash
# 删除前的安全检查
# 1. 查看用户进程
ps -u zhangsan

# 2. 杀掉所有进程
pkill -u zhangsan

# 3. 查看用户 crontab
crontab -u zhangsan -l

# 4. 查看用户 cron 任务
ls -la /var/spool/cron/crontabs/zhangsan 2>/dev/null

# 5. 查看 at 任务
ls -la /var/spool/at/zhangsan 2>/dev/null
```

---

### 3. 用户组管理

#### 3.1 groupadd / groupdel / groupmod

```bash
# 创建用户组
groupadd developers

# 创建系统组（低 UID）
groupadd -r systemservice

# 修改组名
groupmod -n oldname newname

# 删除组（确保没有用户以该组为主组）
groupdel developers
```

#### 3.2 gpasswd - 组密码管理

```bash
# 设置组密码
gpasswd developers

# 添加用户到组
gpasswd -a zhangsan developers

# 从组中移除用户
gpasswd -d zhangsan developers

# 设置组管理员
gpasswd -A zhangsan developers
```

#### 3.3 groups - 查看用户组

```bash
# 查看当前用户的组
groups

# 查看指定用户的组
groups zhangsan

# 查看用户属于哪些组（id 命令更详细）
id zhangsan
# uid=1005(zhangsan) gid=1005(zhangsan) groups=1005(zhangsan),27(sudo),999(docker)
```

---

### 4. 密码管理

#### 4.1 passwd

```bash
# 修改当前用户密码
passwd

# 修改指定用户密码（root）
passwd zhangsan

# 其他选项
passwd -l zhangsan    # 锁定账户
passwd -u zhangsan    # 解锁账户
passwd -e zhangsan    # 下次登录强制改密码
passwd -d zhangsan    # 清除密码（无密码登录）
passwd -n 7 zhangsan  # 最少保留 7 天才能改
passwd -x 90 zhangsan # 密码 90 天后过期
passwd -w 10 zhangsan # 过期前 10 天提醒
```

#### 4.2 chage - 密码策略

```bash
# 查看用户密码策略
chage -l zhangsan

# 设置密码过期规则
chage -M 90 zhangsan          # 密码最长使用 90 天
chage -m 7 zhangsan           # 最少使用 7 天才能改
chage -W 14 zhangsan          # 过期前 14 天提醒
chage -E 2025-12-31 zhangsan  # 账户过期日期
```

**企业密码策略示例**：
```bash
# 编辑 /etc/login.defs 设置系统默认
PASS_MAX_DAYS 90
PASS_MIN_DAYS 7
PASS_WARN_AGE 14
PASS_MIN_LEN 12
```

---

### 5. sudo 权限管理

#### 5.1 visudo - 安全编辑 sudoers 文件

```bash
# 打开 sudoers 配置编辑器
visudo

# 默认编辑器是 vim，可以改用 nano
EDITOR=nano visudo
```

#### 5.2 sudoers 语法

```bash
# 基本语法
用户  主机=(运行身份:用户组)  命令

# 示例
zhangsan  ALL=(ALL:ALL)  ALL           # 完全 sudo 权限
zhangsan  ALL=(ALL)       /usr/bin/systemctl restart nginx  # 只允许重启 nginx
zhangsan  ALL=(www-data)  /usr/bin/kill  # 以 www-data 身份执行 kill
%developers  ALL=(ALL)     /usr/bin/apt, /usr/bin/docker  # 用户组权限
```

#### 5.3 常用 sudoers 配置

```bash
# 允许用户执行所有命令（需谨慎）
zhangsan  ALL=(ALL:ALL)  ALL

# 允许用户无密码执行 sudo
zhangsan  ALL=(ALL)  NOPASSWD: ALL

# 允许 sudo 组所有权限
%sudo   ALL=(ALL:ALL)  ALL

# 限制 SRE 用户只能管理服务
%SRE  ALL=(ALL)  NOPASSWD: /usr/bin/systemctl start *, \
                        /usr/bin/systemctl stop *, \
                        /usr/bin/systemctl restart *, \
                        /usr/bin/systemctl status *, \
                        /usr/bin/journalctl, \
                        /usr/bin/tail -f /var/log/*.log

# 允许运维重启 Docker 容器
%ops  ALL=(ALL)  NOPASSWD: /usr/bin/docker restart *
```

**安全提醒**：
```bash
# ❌ 永远不要这样做
echo "ALL ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers  # 太危险！

# ✅ 正确做法：只授权需要的命令
zhangsan  ALL=(ALL)  /usr/bin/systemctl restart nginx, /usr/bin/systemctl status nginx
```

---

### 6. 实战案例

#### 场景 1：新员工入职 - 创建 SRE 账户

```bash
#!/bin/bash
# create_sre_user.sh - 新 SRE 入职脚本

USERNAME=$1
FULL_NAME=$2
SSH_KEY_URL=$3

if [ -z "$USERNAME" ] || [ -z "$FULL_NAME" ]; then
    echo "用法: $0 <用户名> <全名> [SSH公钥URL]"
    exit 1
fi

# 1. 创建用户
useradd -m \
    -c "$FULL_NAME" \
    -s /bin/bash \
    -G sudo,docker,www-data, nagios \
    $USERNAME

# 2. 设置初始密码（生产环境建议让用户首次登录后自己改）
echo "$USERNAME:TempPassword123!" | chpasswd

# 3. 配置 sudo 权限（SRE 权限）
echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx, \
                               /usr/bin/systemctl stop nginx, \
                               /usr/bin/systemctl status nginx, \
                               /usr/bin/systemctl restart docker, \
                               /usr/bin/docker" >> /etc/sudoers

# 4. 配置 SSH 密钥登录
mkdir -p /home/$USERNAME/.ssh
chmod 700 /home/$USERNAME/.ssh

if [ -n "$SSH_KEY_URL" ]; then
    curl -s "$SSH_KEY_URL" >> /home/$USERNAME/.ssh/authorized_keys
fi

chmod 600 /home/$USERNAME/.ssh/authorized_keys
chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh

# 5. 记录创建日志
echo "$(date): Created SRE user $USERNAME ($FULL_NAME)" >> /var/log/sre_users.log
```

#### 场景 2：员工离职 - 清理账户

```bash
#!/bin/bash
# remove_sre_user.sh - SRE 离职清理脚本

USERNAME=$1

if [ -z "$USERNAME" ]; then
    echo "用法: $0 <用户名>"
    exit 1
fi

# 1. 检查用户是否存在
id $USERNAME &>/dev/null || { echo "用户不存在"; exit 1; }

# 2. 查看用户进程
echo "检查用户进程..."
ps -u $USERNAME

# 3. 杀掉用户所有进程
pkill -u $USERNAME

# 4. 锁定账户（防止 SSH 登录）
usermod -L $USERNAME

# 5. 备份用户主目录（保留 30 天）
if [ -d /home/$USERNAME ]; then
    tar -czf /backup/users/${USERNAME}_$(date +%Y%m%d).tar.gz /home/$USERNAME
    chmod 600 /backup/users/${USERNAME}_*.tar.gz
fi

# 6. 删除用户和主目录
userdel -r $USERNAME

# 7. 删除 sudoers 中的配置（需要手动编辑）
echo "请手动检查 /etc/sudoers 移除 $USERNAME 的配置"

# 8. 记录离职日志
echo "$(date): Removed SRE user $USERNAME" >> /var/log/sre_users.log
```

---

### 7. 监控与审计

```bash
# 查看所有用户登录历史
last

# 查看失败登录尝试
lastb

# 查看用户最近登录记录
lastlog

# 查看特定用户登录记录
last zhangsan

# 监控 sudo 使用
sudo tail -f /var/log/auth.log | grep sudo

# 查看谁正在使用 sudo
who | grep sudo

# 设置账户过期告警（crontab）
0 0 1 * * /usr/bin/chage -l ALL | grep "Password expires" | grep -E "([0-9]) day"
```

---

### 8. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `useradd: cannot create /home/xxx` | 目录不存在且无权限 | `mkdir /home && chmod 755 /home` |
| `permission denied` 执行 sudo | 用户不在 sudo 组 | `usermod -aG sudo username` |
| SSH 密钥登录失败 | `.ssh` 目录权限不对 | `chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys` |
| 用户登录后立即退出 | shell 不存在 | `usermod -s /bin/bash username` |
| 密码过期无法登录 | 密码过期策略 | `chage -l username` 查看，` chage -M -1 username` 永不过期 |
| 显示 "account is locked" | usermod -L 锁定 | `usermod -U username` 解锁 |


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

*由 SRE 学习计划自动生成 | 2026-04-18 09:37:46*  
*Generated by Hermes Agent with review*
