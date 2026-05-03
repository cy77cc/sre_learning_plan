# Day 07: 第一周综合练习

> 📅 日期：2026-04-26
> 📖 学习主题：第一周综合练习 -- 综合运用 Day 01-06 所有知识
> ⏰ 预计学习时间：4-6 小时
> 📋 前置知识：Day 01-06 全部内容

## 🎯 学习目标

完成 Day 07 的学习后，你应该能够：
- 综合运用 Linux 基础、文件操作、文本处理、权限管理、用户管理完成真实运维任务
- 独立从零配置一台生产服务器（SSH 加固、防火墙、用户创建、软件安装）
- 使用 grep/sed/awk 对日志进行高效分析，定位安全问题
- 排查和修复常见的权限问题（403 Forbidden、SSH 登录失败、共享目录权限）
- 编写跨发行版的服务器初始化脚本

---

## 📖 第一周核心知识回顾

### Day 01-06 知识图谱

```
┌─────────────────────────────────────────────────────────────────┐
│                    第一周知识体系                                 │
│                                                                 │
│  Day 01: Linux 基础                                             │
│  ├── Linux 哲学：一切皆文件、小工具组合                          │
│  ├── 发行版选择：Ubuntu LTS / Rocky Linux / Debian              │
│  └── 虚拟机环境：WSL2 / VirtualBox                              │
│                                                                 │
│  Day 02: FHS 文件系统                                           │
│  ├── /etc 配置文件、/var 可变数据、/tmp 临时文件                │
│  ├── /home 用户目录、/root root 家目录                          │
│  └── /proc 虚拟文件系统、/dev 设备文件                          │
│                                                                 │
│  Day 03: 文件操作                                               │
│  ├── cp/mv/rm/touch/mkdir 基础操作                              │
│  ├── find 高级搜索（-name, -type, -size, -mtime, -perm, -exec） │
│  └── 文件属性：stat, file, ln                                   │
│                                                                 │
│  Day 04: 文本处理                                               │
│  ├── grep 搜索（-i, -r, -E, -o, -c, -v, -A, -B）              │
│  ├── sed 流编辑（s/old/new/g, /pattern/d, -i）                 │
│  ├── awk 列处理（$1, $NF, -F:, BEGIN/END）                     │
│  └── 正则表达式（^, $, ., *, +, [], (), |）                    │
│                                                                 │
│  Day 05: 权限管理                                               │
│  ├── rwx 在文件/目录上的不同含义                                │
│  ├── chmod/chown/chgrp 数字和符号模式                           │
│  ├── SUID(4000)/SGID(2000)/Sticky Bit(1000)                    │
│  ├── ACL 精细权限控制（setfacl/getfacl/mask/default ACL）       │
│  └── umask 默认权限计算                                         │
│                                                                 │
│  Day 06: 用户管理                                               │
│  ├── /etc/passwd、/etc/shadow、/etc/group 文件解析              │
│  ├── useradd/usermod/userdel 命令                               │
│  ├── sudo 工作原理和 /etc/sudoers 配置                          │
│  ├── PAM 认证框架                                               │
│  └── 密码策略和用户生命周期管理                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ 综合实战场景

### 场景一：新购云服务器从零到可用

你刚入职一家互联网公司，公司新购了一台 Ubuntu 22.04 云服务器。你的第一个任务是完成服务器初始化，使其达到生产可用状态。

#### 步骤 1：系统基础配置

```bash
# ========== 连接服务器 ==========
# 首次通过 root + 密码登录
ssh root@<服务器IP>

# ========== 系统更新 ==========
apt update && apt upgrade -y

# 查看系统信息
cat /etc/os-release          # 发行版信息
uname -r                     # 内核版本
hostnamectl                  # 主机名和操作系统信息
uptime                       # 运行时间和负载
free -h                      # 内存信息
df -h                        # 磁盘信息

# 设置主机名
hostnamectl set-hostname sre-prod-01

# 设置时区
timedatectl set-timezone Asia/Shanghai
timedatectl status
```

#### 步骤 2：创建运维用户并加固 SSH

```bash
# ========== 创建 SRE 用户 ==========
useradd -m -s /bin/bash -c "SRE Engineer" sreuser
passwd sreuser               # 设置强密码

# 添加到 sudo 组
usermod -aG sudo sreuser

# 配置 sudo 权限（限制范围）
cat > /etc/sudoers.d/sreuser << 'EOF'
sreuser ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart *, \
                            /usr/bin/systemctl stop *, \
                            /usr/bin/systemctl start *, \
                            /usr/bin/systemctl status *, \
                            /usr/bin/journalctl, \
                            /usr/bin/tail -f /var/log/*.log, \
                            /usr/bin/docker
Defaults:sreuser timestamp_timeout=5
EOF
chmod 440 /etc/sudoers.d/sreuser

# ========== SSH 加固 ==========
# 切换到 sreuser 配置密钥
su - sreuser

# 在本地机器生成密钥（如果还没有）
# ssh-keygen -t ed25519 -C "sre@company.com"

# 在服务器上配置密钥登录
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "ssh-ed25519 AAAA... your_key_comment" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 退出 sreuser，回到 root 配置 sshd
exit

# SSH 安全加固
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d)

cat > /etc/ssh/sshd_config.d/hardening.conf << 'EOF'
# SSH 安全加固配置
Port 22222                           # 修改默认端口
PermitRootLogin no                   # 禁止 root 登录
PasswordAuthentication no            # 禁止密码登录（只允许密钥）
PubkeyAuthentication yes             # 允许公钥认证
MaxAuthTries 3                       # 最大尝试次数
LoginGraceTime 60                    # 登录超时时间
ClientAliveInterval 300              # 客户端心跳间隔
ClientAliveCountMax 2                # 心跳失败次数
AllowUsers sreuser                   # 只允许特定用户
X11Forwarding no                     # 禁止 X11 转发
MaxSessions 3                        # 最大并发会话
EOF

# 测试配置
sshd -t

# 重启 SSH（注意：先确保新配置可用再重启！）
systemctl restart sshd
```

#### 步骤 3：防火墙配置

```bash
# ========== UFW 防火墙 ==========
apt install -y ufw

# 默认策略
ufw default deny incoming
ufw default allow outgoing

# 允许必要端口
ufw allow 22222/tcp comment 'SSH (custom port)'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# 启用防火墙
ufw --force enable
ufw status verbose

# ========== fail2ban 防爆破 ==========
apt install -y fail2ban

cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3
backend  = systemd

[sshd]
enabled  = true
port     = 22222
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 3
bantime  = 3600
EOF

systemctl enable fail2ban
systemctl start fail2ban

# 查看 fail2ban 状态
fail2ban-client status sshd
```

#### 步骤 4：安装基础工具

```bash
# ========== 基础工具 ==========
apt install -y \
    curl wget vim git tree htop tmux \
    net-tools iproute2 dnsutils \
    unzip jq \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# 配置 vim
cat > /etc/vim/vimrc.local << 'EOF'
set number
set tabstop=4
set shiftwidth=4
set expandtab
set autoindent
set hlsearch
syntax on
EOF

# 配置 tmux
cat > /etc/tmux.conf << 'EOF'
set -g default-terminal "screen-256color"
set -g history-limit 10000
set -g mouse on
EOF
```

#### 步骤 5：系统参数调优

```bash
cat > /etc/sysctl.d/99-sre-tuning.conf << 'EOF'
# 文件描述符
fs.file-max = 65536
fs.inotify.max_user_watches = 524288

# 网络优化
net.core.somaxconn = 1024
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.tcp_tw_reuse = 1

# 防止 SYN Flood
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_tw_buckets = 36000

# 虚拟内存
vm.swappiness = 10
vm.overcommit_memory = 0
EOF

sysctl --system

# 用户资源限制
cat > /etc/security/limits.d/99-sre.conf << 'EOF'
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF
```

#### 步骤 6：NTP 时间同步

```bash
systemctl enable systemd-timesyncd
systemctl start systemd-timesyncd
timedatectl status
```

#### 步骤 7：验证配置

```bash
echo "========================================"
echo "  服务器初始化验证报告"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

echo ""
echo "--- 系统信息 ---"
echo "主机名: $(hostname)"
echo "系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "内核: $(uname -r)"
echo "IP: $(ip -4 addr show | grep inet | grep -v 127 | awk '{print $2}')"
echo "时区: $(timedatectl | grep "Time zone" | awk '{print $3}')"

echo ""
echo "--- 资源使用 ---"
echo "CPU: $(nproc) 核心"
echo "内存: $(free -h | awk '/Mem:/ {print $2}')"
echo "磁盘: $(df -h / | awk 'NR==2 {print $2 " (" $5 " used)"}')"
echo "负载: $(cat /proc/loadavg | awk '{print $1, $2, $3}')"

echo ""
echo "--- 安全配置 ---"
echo "SSH 端口: $(grep -E '^Port' /etc/ssh/sshd_config.d/*.conf 2>/dev/null | awk '{print $2}')"
echo "Root 登录: $(grep -E '^PermitRootLogin' /etc/ssh/sshd_config.d/*.conf 2>/dev/null | awk '{print $2}')"
echo "密码认证: $(grep -E '^PasswordAuthentication' /etc/ssh/sshd_config.d/*.conf 2>/dev/null | awk '{print $2}')"
echo "防火墙: $(ufw status | head -1)"
echo "fail2ban: $(systemctl is-active fail2ban)"

echo ""
echo "--- 用户信息 ---"
echo "可登录用户:"
awk -F: '$7 !~ /nologin|false|sync|halt|shutdown/ && $3 >= 1000 {print "  " $1 " (UID=" $3 ")"}' /etc/passwd
echo "sudo 用户:"
grep -r "" /etc/sudoers.d/ 2>/dev/null | grep -v "^#" | awk '{print "  " $1}'

echo ""
echo "--- 已安装工具 ---"
for tool in curl wget vim git htop tmux jq ufw fail2ban; do
    which $tool &>/dev/null && echo "  ✓ $tool" || echo "  ✗ $tool (未安装)"
done

echo ""
echo "========================================"
echo "  初始化完成"
echo "========================================"
```

---

### 场景二：权限问题排查

#### 问题 2.1：Nginx 403 Forbidden

```bash
# 场景：部署新网站后访问出现 403 Forbidden
# 错误日志显示："/var/www/mysite/index.html" is forbidden (13: Permission denied)

# 排查步骤 1：检查文件权限
ls -la /var/www/mysite/
# 输出：-rw------- 1 root root ... index.html
# 问题：nginx 用户（www-data）没有读权限

# 排查步骤 2：检查目录权限
namei -l /var/www/mysite/index.html
# 检查路径上每级目录的 x 权限

# 排查步骤 3：检查 nginx 运行用户
grep user /etc/nginx/nginx.conf
# 确认是 user www-data;

# 排查步骤 4：检查 SELinux
getenforce
# 如果是 Enforcing：
ls -Z /var/www/mysite/
# 修复 SELinux 上下文
semanage fcontext -a -t httpd_sys_content_t "/var/www/mysite(/.*)?"
restorecon -Rv /var/www/mysite/

# 排查步骤 5：检查 AppArmor
aa-status | grep nginx

# 修复方案
# 方案 A：修改文件权限和所有者
chown -R www-data:www-data /var/www/mysite/
find /var/www/mysite -type f -exec chmod 644 {} +
find /var/www/mysite -type d -exec chmod 755 {} +

# 方案 B：使用 ACL（更精细）
setfacl -R -m u:www-data:rx /var/www/mysite/
setfacl -d -m u:www-data:rx /var/www/mysite/

# 验证修复
curl -I http://localhost/
sudo -u www-data cat /var/www/mysite/index.html
```

#### 问题 2.2：SSH 密钥登录失败

```bash
# 场景：配置了 SSH 密钥但仍然提示输入密码
# 本地执行：ssh -vvv sreuser@server

# 排查步骤 1：检查服务器端 SSH 配置
grep -E "^(PubkeyAuthentication|AuthorizedKeysFile|PasswordAuthentication)" /etc/ssh/sshd_config

# 排查步骤 2：检查密钥权限（服务器端）
namei -l /home/sreuser/.ssh/authorized_keys
# 每级权限要求：
# /home/sreuser/      → 755（不能 group-writable）
# /home/sreuser/.ssh/ → 700
# authorized_keys     → 600

# 排查步骤 3：检查密钥内容
cat /home/sreuser/.ssh/authorized_keys
# 确认公钥格式正确（ssh-ed25519 AAAA... 或 ssh-rsa AAAA...）
# 确认没有多余的空格或换行

# 排查步骤 4：检查 SELinux 上下文
ls -Z /home/sreuser/.ssh/
# 如果上下文不正确：
restorecon -Rv /home/sreuser/.ssh/

# 排查步骤 5：检查认证日志
tail -50 /var/log/auth.log | grep sshd

# 排查步骤 6：检查 fail2ban
fail2ban-client status sshd

# 排查步骤 7：检查目录所有权
ls -la /home/sreuser/
# 确保 .ssh 目录和文件的 owner 都是 sreuser

# 一键修复脚本
#!/bin/bash
USERNAME="sreuser"
chmod 755 /home/$USERNAME
chmod 700 /home/$USERNAME/.ssh
chmod 600 /home/$USERNAME/.ssh/authorized_keys
chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh
restorecon -Rv /home/$USERNAME/.ssh/ 2>/dev/null
systemctl restart sshd
```

#### 问题 2.3：共享目录权限冲突

```bash
# 场景：开发团队共享目录，alice 创建的文件 bob 无法编辑

# 排查步骤 1：检查目录权限
ls -ld /shared/project/
# 输出：drwxr-xr-x root root ...
# 问题：没有组写权限，没有 SGID

# 排查步骤 2：检查文件权限
ls -la /shared/project/
# 输出：-rw-r--r-- alice alice ... file.txt
# 问题：文件属于 alice 的主组，不是共享组

# 排查步骤 3：检查用户组
id alice   # 确认 alice 在 devteam 组中
id bob     # 确认 bob 在 devteam 组中

# 修复方案：使用 SGID + ACL
groupadd devteam
usermod -aG devteam alice
usermod -aG devteam bob

chown :devteam /shared/project/
chmod 2775 /shared/project/    # SGID + 组写权限

# 修复已有文件的组
chgrp -R devteam /shared/project/

# 设置默认 ACL（新文件自动继承权限）
setfacl -d -m g:devteam:rw /shared/project/

# 验证
su - alice -c "echo test > /shared/project/newfile.txt"
ls -l /shared/project/newfile.txt
# 应该显示：-rw-rw-r-- alice devteam ... newfile.txt
```

---

### 场景三：日志分析挑战

#### 问题 3.1：SSH 暴力破解分析

```bash
# 场景：/var/log/auth.log 显示大量登录失败，分析攻击来源

# 步骤 1：统计登录失败总数
grep -c "Failed password" /var/log/auth.log
# 输出：1547

# 步骤 2：按 IP 统计攻击次数（Top 20 攻击者）
grep "Failed password" /var/log/auth.log \
  | awk '{print $(NF-3)}' \
  | sort | uniq -c | sort -rn | head -20
# 输出示例：
#    523 203.0.113.42
#    312 198.51.100.15
#    187 192.0.2.33

# 步骤 3：分析攻击的用户名（攻击者尝试了哪些用户名）
grep "Failed password" /var/log/auth.log \
  | grep -oP 'for (invalid user )?\K\S+' \
  | sort | uniq -c | sort -rn | head -20
# 输出示例：
#    892 root
#    234 admin
#    156 test
#     89 user

# 步骤 4：按时间分析攻击趋势（按小时）
grep "Failed password" /var/log/auth.log \
  | awk '{print $1, $2, substr($3,1,2)":00"}' \
  | sort | uniq -c | sort -rn | head -10

# 步骤 5：分析攻击时间窗口（某个 IP 的攻击频率）
grep "203.0.113.42" /var/log/auth.log \
  | grep "Failed password" \
  | awk '{print $1, $2, $3}' \
  | head -20
# 输出示例：显示每分钟的攻击次数

# 步骤 6：检查是否有成功的暴力破解
grep "Accepted password" /var/log/auth.log \
  | awk '{print $1, $2, $3, $9, $11}'
# 如果有来自未知 IP 的成功登录，立即处理！

# 步骤 7：生成攻击报告
cat > /tmp/bruteforce_report.txt << 'EOF'
=== SSH 暴力破解分析报告 ===
生成时间: $(date)

1. 攻击概况
   总失败次数: $(grep -c "Failed password" /var/log/auth.log)
   攻击 IP 数: $(grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort -u | wc -l)

2. Top 10 攻击 IP
$(grep "Failed password" /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -10)

3. Top 10 尝试用户名
$(grep "Failed password" /var/log/auth.log | grep -oP 'for (invalid user )?\K\S+' | sort | uniq -c | sort -rn | head -10)

4. 成功登录记录
$(grep "Accepted" /var/log/auth.log | tail -20)

5. 建议措施
   - 确认 fail2ban 已启用
   - 禁止密码登录（PasswordAuthentication no）
   - 修改 SSH 默认端口
   - 封禁高频攻击 IP
EOF

# 步骤 8：自动封禁高频攻击 IP
grep "Failed password" /var/log/auth.log \
  | awk '{print $(NF-3)}' \
  | sort | uniq -c | sort -rn \
  | awk '$1 > 10 {print $2}' \
  | while read ip; do
    ufw deny from "$ip" comment "Brute force block"
done
```

#### 问题 3.2：Nginx 日志统计

```bash
# 场景：分析 Nginx 访问日志，了解网站流量和错误情况

# 步骤 1：统计总请求数
wc -l /var/log/nginx/access.log

# 步骤 2：按 HTTP 状态码统计
awk '{print $9}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn
# 输出示例：
#  125430 200
#    3421 304
#    1234 404
#     456 500
#     123 502

# 步骤 3：Top 20 访问 IP
awk '{print $1}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head -20

# 步骤 4：Top 20 请求 URL
awk '{print $7}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head -20

# 步骤 5：分析 5xx 错误
awk '$9 ~ /^5/ {print $7, $9}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head -20

# 步骤 6：分析 404 错误（可能是扫描器）
awk '$9 == 404 {print $1, $7}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head -20

# 步骤 7：按小时统计请求量（流量趋势）
awk '{print substr($4,2,12)}' /var/log/nginx/access.log \
  | awk -F: '{print $1":"$2":00"}' \
  | sort | uniq -c \
  | awk '{printf "%s  %d 请求\n", $2, $1}'

# 步骤 8：分析慢请求（如果有 request_time）
# 假设自定义 log_format 包含 $request_time
awk '{if ($NF > 1.0) print $7, $NF"s"}' /var/log/nginx/access.log \
  | sort -t' ' -k2 -rn | head -20

# 步骤 9：生成流量报告
cat > /tmp/nginx_report.txt << 'EOF'
=== Nginx 流量分析报告 ===
时间范围: $(head -1 /var/log/nginx/access.log | awk '{print $4}') - $(tail -1 /var/log/nginx/access.log | awk '{print $4}')

1. 总请求数: $(wc -l < /var/log/nginx/access.log)
2. 独立 IP 数: $(awk '{print $1}' /var/log/nginx/access.log | sort -u | wc -l)

3. 状态码分布:
$(awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn)

4. Top 10 URL:
$(awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10)

5. Top 10 404:
$(awk '$9 == 404 {print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10)
EOF
```

---

### 场景四：服务器安全审计

```bash
#!/bin/bash
# security_audit.sh -- 服务器安全审计脚本

set -euo pipefail

REPORT_FILE="/tmp/security_audit_$(date +%Y%m%d_%H%M%S).txt"

{
echo "========================================"
echo "  服务器安全审计报告"
echo "  生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  主机名: $(hostname)"
echo "  系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "========================================"

# ========== 1. 用户和权限审计 ==========
echo ""
echo "=== 1. 用户和权限审计 ==="

echo ""
echo "--- 1.1 UID 0 用户（应只有 root）---"
awk -F: '$3 == 0 {print "  " $1 " (UID=0)"}' /etc/passwd

echo ""
echo "--- 1.2 可登录用户 ---"
awk -F: '$7 !~ /nologin|false|sync|halt|shutdown/ && $3 >= 1000 {
    print "  " $1 " (UID=" $3 ", Shell=" $7 ")"
}' /etc/passwd

echo ""
echo "--- 1.3 系统用户（UID < 1000）但有 Shell ---"
awk -F: '$3 < 1000 && $3 > 0 && $7 !~ /nologin|false|sync|halt|shutdown/ {
    print "  WARN: " $1 " (UID=" $3 ", Shell=" $7 ")"
}' /etc/passwd

echo ""
echo "--- 1.4 空密码账户 ---"
for user in $(cut -d: -f1 /etc/passwd); do
    status=$(passwd -S "$user" 2>/dev/null | awk '{print $2}')
    [ "$status" = "NP" ] && echo "  RISK: $user 无密码"
done

echo ""
echo "--- 1.5 sudo 配置 ---"
echo "  /etc/sudoers:"
grep -v "^#" /etc/sudoers 2>/dev/null | grep -v "^$" | grep -v "^Defaults" | while read -r line; do
    echo "    $line"
done
echo "  /etc/sudoers.d/:"
for f in /etc/sudoers.d/*; do
    [ -f "$f" ] && echo "    $f:" && grep -v "^#" "$f" | grep -v "^$" | while read -r line; do
        echo "      $line"
    done
done

echo ""
echo "--- 1.6 NOPASSWD sudo 配置 ---"
grep -r "NOPASSWD" /etc/sudoers /etc/sudoers.d/ 2>/dev/null | while read -r line; do
    echo "  $line"
done

# ========== 2. SSH 安全审计 ==========
echo ""
echo "=== 2. SSH 安全审计 ==="

echo ""
echo "--- 2.1 SSH 配置关键项 ---"
for key in Port PermitRootLogin PasswordAuthentication PubkeyAuthentication MaxAuthTries; do
    value=$(grep -E "^${key}\b" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/*.conf 2>/dev/null | tail -1 | awk '{print $2}')
    [ -z "$value" ] && value="(未设置)"
    echo "  $key: $value"
done

echo ""
echo "--- 2.2 SSH 密钥权限检查 ---"
for home_dir in /home/*/; do
    username=$(basename "$home_dir")
    ssh_dir="$home_dir.ssh"
    if [ -d "$ssh_dir" ]; then
        perm=$(stat -c %a "$ssh_dir")
        [[ "$perm" != "700" ]] && echo "  WARN: $ssh_dir 权限 $perm (应为 700)"

        auth="$ssh_dir/authorized_keys"
        if [ -f "$auth" ]; then
            perm=$(stat -c %a "$auth")
            [[ "$perm" != "600" ]] && echo "  WARN: $auth 权限 $perm (应为 600)"
            key_count=$(wc -l < "$auth")
            echo "  INFO: $username 有 $key_count 个 SSH 公钥"
        fi
    fi
done

echo ""
echo "--- 2.3 SSH 登录失败（最近 7 天）---"
if [ -f /var/log/auth.log ]; then
    failed=$(grep -c "Failed password" /var/log/auth.log 2>/dev/null || echo "0")
    echo "  失败次数: $failed"
    echo "  Top 5 攻击 IP:"
    grep "Failed password" /var/log/auth.log 2>/dev/null \
      | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -5 | while read -r count ip; do
        echo "    $ip ($count 次)"
    done
fi

# ========== 3. 文件系统安全 ==========
echo ""
echo "=== 3. 文件系统安全 ==="

echo ""
echo "--- 3.1 SUID 文件 ---"
find / -type f -perm /4000 -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null | while read -r f; do
    owner=$(stat -c '%U' "$f")
    echo "  $f (owner: $owner)"
done

echo ""
echo "--- 3.2 SGID 文件 ---"
find / -type f -perm /2000 -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null | while read -r f; do
    owner=$(stat -c '%U' "$f")
    echo "  $f (owner: $owner)"
done

echo ""
echo "--- 3.3 全局可写文件（不包括 /tmp /var/tmp）---"
find / -type f -perm -o+w \
  -not -path "/proc/*" -not -path "/sys/*" \
  -not -path "/tmp/*" -not -path "/var/tmp/*" 2>/dev/null | head -20

echo ""
echo "--- 3.4 全局可写目录（无 Sticky Bit）---"
find / -type d -perm -o+w -not -perm -1000 \
  -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null | head -10

echo ""
echo "--- 3.5 无主文件 ---"
find /home -nouser -o -nogroup 2>/dev/null | head -10

# ========== 4. 服务和进程 ==========
echo ""
echo "=== 4. 服务和进程 ==="

echo ""
echo "--- 4.1 监听端口 ---"
ss -tlnp | while read -r line; do
    echo "  $line"
done

echo ""
echo "--- 4.2 启用的 systemd 服务 ---"
systemctl list-unit-files --type=service --state=enabled 2>/dev/null | grep enabled | while read -r line; do
    echo "  $line"
done

echo ""
echo "--- 4.3 僵尸进程 ---"
zombies=$(ps aux | awk '$8 ~ /Z/ {count++} END {print count+0}')
echo "  僵尸进程数: $zombies"
[ "$zombies" -gt 0 ] && ps aux | awk '$8 ~ /Z/ {print "  " $0}'

# ========== 5. 防火墙和安全工具 ==========
echo ""
echo "=== 5. 防火墙和安全工具 ==="

echo ""
echo "--- 5.1 UFW 状态 ---"
if command -v ufw &>/dev/null; then
    ufw status verbose 2>/dev/null | while read -r line; do
        echo "  $line"
    done
else
    echo "  UFW 未安装"
fi

echo ""
echo "--- 5.2 fail2ban 状态 ---"
if command -v fail2ban-client &>/dev/null; then
    fail2ban-client status 2>/dev/null | while read -r line; do
        echo "  $line"
    done
else
    echo "  fail2ban 未安装"
fi

echo ""
echo "--- 5.3 SELinux 状态 ---"
if command -v getenforce &>/dev/null; then
    echo "  SELinux: $(getenforce)"
else
    echo "  SELinux 未安装"
fi

echo ""
echo "--- 5.4 AppArmor 状态 ---"
if command -v aa-status &>/dev/null; then
    echo "  AppArmor profiles: $(aa-status 2>/dev/null | grep "profiles are defined" || echo "未知")"
else
    echo "  AppArmor 未安装"
fi

# ========== 6. 密码策略 ==========
echo ""
echo "=== 6. 密码策略 ==="

echo ""
echo "--- 6.1 系统默认策略 (/etc/login.defs) ---"
grep -E "^PASS_" /etc/login.defs 2>/dev/null | while read -r line; do
    echo "  $line"
done

echo ""
echo "--- 6.2 密码即将过期的用户 ---"
for user in $(awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' /etc/passwd); do
    expire=$(chage -l "$user" 2>/dev/null | grep "Password expires" | cut -d: -f2 | xargs)
    if [[ "$expire" != "never" ]] && [ -n "$expire" ]; then
        expire_epoch=$(date -d "$expire" +%s 2>/dev/null || echo 0)
        now_epoch=$(date +%s)
        days_left=$(( (expire_epoch - now_epoch) / 86400 ))
        [ "$days_left" -lt 30 ] && echo "  WARN: $user 密码将在 $days_left 天后过期"
    fi
done

echo ""
echo "========================================"
echo "  审计完成"
echo "========================================"
echo ""
echo "报告已保存到: $REPORT_FILE"

} 2>&1 | tee "$REPORT_FILE"
```

---

### 场景五：编写服务器初始化脚本

编写一个支持 Ubuntu 和 Rocky Linux 的服务器初始化脚本：

```bash
#!/bin/bash
# server_init.sh -- 跨发行版服务器初始化脚本
# 支持：Ubuntu 20.04/22.04、Rocky Linux 8/9

set -euo pipefail

# ========== 配置变量 ==========
SRE_USER="sreuser"
SSH_PORT="22222"
TIMEZONE="Asia/Shanghai"
ADMIN_EMAIL="sre@company.com"

# ========== 颜色输出 ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ========== 检测发行版 ==========
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    elif [ -f /etc/centos-release ]; then
        DISTRO="centos"
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    else
        log_error "不支持的发行版"
        exit 1
    fi
    log_info "检测到发行版: $DISTRO $VERSION"
}

# ========== 检查 root 权限 ==========
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "此脚本需要 root 权限运行"
        exit 1
    fi
}

# ========== 系统更新 ==========
update_system() {
    log_info "更新系统..."
    case "$DISTRO" in
        ubuntu|debian)
            apt update && apt upgrade -y
            ;;
        rocky|centos|rhel)
            dnf update -y
            ;;
    esac
}

# ========== 安装基础工具 ==========
install_tools() {
    log_info "安装基础工具..."
    case "$DISTRO" in
        ubuntu|debian)
            apt install -y \
                curl wget vim git tree htop tmux \
                net-tools iproute2 dnsutils \
                unzip jq \
                ufw fail2ban \
                software-properties-common \
                ca-certificates gnupg lsb-release
            ;;
        rocky|centos|rhel)
            dnf install -y \
                curl wget vim git tree htop tmux \
                net-tools iproute bind-utils \
                unzip jq \
                epel-release
            dnf install -y fail2ban
            ;;
    esac
}

# ========== 创建 SRE 用户 ==========
create_sre_user() {
    log_info "创建 SRE 用户: $SRE_USER"

    if id "$SRE_USER" &>/dev/null; then
        log_warn "用户 $SRE_USER 已存在"
        return
    fi

    useradd -m -s /bin/bash -c "SRE Engineer" "$SRE_USER"
    echo "$SRE_USER:$(openssl rand -base64 12)" | chpasswd
    chage -d 0 "$SRE_USER"

    # 添加到 sudo 组
    case "$DISTRO" in
        ubuntu|debian)
            usermod -aG sudo "$SRE_USER"
            ;;
        rocky|centos|rhel)
            usermod -aG wheel "$SRE_USER"
            ;;
    esac

    # 配置 sudo 权限
    cat > "/etc/sudoers.d/$SRE_USER" << EOF
$SRE_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart *, \
                              /usr/bin/systemctl stop *, \
                              /usr/bin/systemctl start *, \
                              /usr/bin/systemctl status *, \
                              /usr/bin/journalctl, \
                              /usr/bin/docker
EOF
    chmod 440 "/etc/sudoers.d/$SRE_USER"
    log_info "SRE 用户创建完成"
}

# ========== SSH 加固 ==========
harden_ssh() {
    log_info "加固 SSH..."

    # 备份原配置
    cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d)

    # 创建加固配置
    mkdir -p /etc/ssh/sshd_config.d
    cat > /etc/ssh/sshd_config.d/hardening.conf << EOF
Port $SSH_PORT
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
LoginGraceTime 60
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
MaxSessions 3
EOF

    # 测试配置
    if sshd -t; then
        systemctl restart sshd
        log_info "SSH 加固完成，新端口: $SSH_PORT"
    else
        log_error "SSH 配置有误，回滚"
        cp /etc/ssh/sshd_config.bak.$(date +%Y%m%d) /etc/ssh/sshd_config
        rm -f /etc/ssh/sshd_config.d/hardening.conf
    fi
}

# ========== 防火墙配置 ==========
setup_firewall() {
    log_info "配置防火墙..."

    case "$DISTRO" in
        ubuntu|debian)
            ufw default deny incoming
            ufw default allow outgoing
            ufw allow "$SSH_PORT/tcp" comment 'SSH'
            ufw allow 80/tcp comment 'HTTP'
            ufw allow 443/tcp comment 'HTTPS'
            ufw --force enable
            ;;
        rocky|centos|rhel)
            systemctl enable firewalld
            systemctl start firewalld
            firewall-cmd --permanent --add-port="$SSH_PORT/tcp"
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --reload
            ;;
    esac
    log_info "防火墙配置完成"
}

# ========== fail2ban 配置 ==========
setup_fail2ban() {
    log_info "配置 fail2ban..."

    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3
backend  = systemd

[sshd]
enabled  = true
port     = $SSH_PORT
filter   = sshd
maxretry = 3
bantime  = 3600
EOF

    systemctl enable fail2ban
    systemctl start fail2ban
    log_info "fail2ban 配置完成"
}

# ========== 系统调优 ==========
tune_system() {
    log_info "系统参数调优..."

    cat > /etc/sysctl.d/99-sre-tuning.conf << 'EOF'
fs.file-max = 65536
fs.inotify.max_user_watches = 524288
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_syncookies = 1
vm.swappiness = 10
EOF

    sysctl --system

    # 用户资源限制
    cat > /etc/security/limits.d/99-sre.conf << 'EOF'
* soft nofile 65536
* hard nofile 65536
* soft nproc 65536
* hard nproc 65536
EOF

    log_info "系统调优完成"
}

# ========== 设置时区和 NTP ==========
setup_time() {
    log_info "设置时区: $TIMEZONE"
    timedatectl set-timezone "$TIMEZONE"

    if systemctl is-active systemd-timesyncd &>/dev/null; then
        systemctl enable systemd-timesyncd
        systemctl start systemd-timesyncd
    elif systemctl is-active chronyd &>/dev/null; then
        systemctl enable chronyd
        systemctl start chronyd
    fi
    log_info "时间同步已配置"
}

# ========== 配置 vim 和 tmux ==========
configure_tools() {
    log_info "配置基础工具..."

    cat > /etc/vim/vimrc.local << 'EOF'
set number
set tabstop=4
set shiftwidth=4
set expandtab
set autoindent
set hlsearch
syntax on
EOF

    log_info "工具配置完成"
}

# ========== 安全加固（密码策略） ==========
setup_password_policy() {
    log_info "配置密码策略..."

    # 修改 /etc/login.defs
    sed -i 's/^PASS_MAX_DAYS.*/PASS_MAX_DAYS   90/' /etc/login.defs
    sed -i 's/^PASS_MIN_DAYS.*/PASS_MIN_DAYS   7/' /etc/login.defs
    sed -i 's/^PASS_MIN_LEN.*/PASS_MIN_LEN    12/' /etc/login.defs
    sed -i 's/^PASS_WARN_AGE.*/PASS_WARN_AGE   14/' /etc/login.defs

    # 配置密码复杂度（如果 pam_pwquality 存在）
    if [ -f /etc/security/pwquality.conf ]; then
        cat > /etc/security/pwquality.conf << 'EOF'
minlen = 12
dcredit = -1
ucredit = -1
lcredit = -1
ocredit = -1
maxrepeat = 3
difok = 5
retry = 3
EOF
    fi

    log_info "密码策略配置完成"
}

# ========== 生成验证报告 ==========
generate_report() {
    log_info "生成初始化报告..."

    echo ""
    echo "========================================"
    echo "  服务器初始化完成报告"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================"
    echo ""
    echo "系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
    echo "内核: $(uname -r)"
    echo "主机名: $(hostname)"
    echo "IP: $(ip -4 addr show | grep inet | grep -v 127 | awk '{print $2}')"
    echo "时区: $(timedatectl | grep "Time zone" | awk '{print $3}')"
    echo ""
    echo "SRE 用户: $SRE_USER"
    echo "SSH 端口: $SSH_PORT"
    echo ""
    echo "后续步骤:"
    echo "  1. 将 SSH 公钥添加到 /home/$SRE_USER/.ssh/authorized_keys"
    echo "  2. 测试 SSH 密钥登录后再禁用密码登录"
    echo "  3. 验证 sudo 权限是否正确"
    echo ""
    echo "========================================"
}

# ========== 主流程 ==========
main() {
    log_info "开始服务器初始化..."
    echo ""

    check_root
    detect_distro
    update_system
    install_tools
    create_sre_user
    harden_ssh
    setup_firewall
    setup_fail2ban
    tune_system
    setup_time
    configure_tools
    setup_password_policy
    generate_report

    log_info "初始化完成！"
}

main "$@"
```

---

## 🧪 自我评估

### 综合练习题

#### 练习题 1：文件搜索与处理
在 `/var/log` 目录下找到所有超过 100MB 的 `.log` 文件，统计每个文件的行数，按大小降序排列：

<details>
<summary>答案</summary>

```bash
find /var/log -type f -name "*.log" -size +100M -exec sh -c '
    for f; do
        lines=$(wc -l < "$f")
        size=$(stat -c %s "$f")
        echo "$size $lines $f"
    done
' sh {} + | sort -rn | awk '{
    printf "%s %d lines %s\n", 
    $1 > 1048576 ? sprintf("%.1fGB", $1/1073741824) : sprintf("%.1fMB", $1/1048576),
    $2, $3
}'
```
</details>

#### 练习题 2：日志分析
从 `/var/log/auth.log` 中找出所有失败的 sudo 尝试，提取用户名和尝试执行的命令：

<details>
<summary>答案</summary>

```bash
grep "sudo.*NOT_ALLOWED\|sudo.*authentication failure" /var/log/auth.log \
  | awk '{
    for(i=1;i<=NF;i++) {
        if($i ~ /USER=/) user=substr($i,6)
        if($i ~ /COMMAND=/) cmd=substr($i,9)
    }
    print user, cmd
}' | sort | uniq -c | sort -rn
```
</details>

#### 练习题 3：权限修复
编写一个脚本，接受一个目录路径作为参数，将该目录的安全权限恢复到标准状态：
- 目录权限 755，文件权限 644
- 敏感文件（.env, .key, .pem）权限 600
- .ssh 目录权限 700，authorized_keys 权限 600

<details>
<summary>答案</summary>

```bash
#!/bin/bash
dir="${1:?用法: $0 <目录路径>}"

[ -d "$dir" ] || { echo "错误: $dir 不是目录"; exit 1; }

echo "修复目录权限: $dir"

# 目录权限 755
find "$dir" -type d -exec chmod 755 {} +
echo "已设置目录权限为 755"

# 文件权限 644
find "$dir" -type f -exec chmod 644 {} +
echo "已设置文件权限为 644"

# 敏感文件 600
find "$dir" -type f \( -name "*.env" -o -name "*.key" -o -name "*.pem" \
  -o -name "*.secret" -o -name "id_rsa" -o -name "id_ed25519" \) \
  -exec chmod 600 {} +
echo "已设置敏感文件权限为 600"

# .ssh 目录
find "$dir" -type d -name ".ssh" -exec chmod 700 {} + \
  -exec sh -c 'chmod 600 "$1/authorized_keys" 2>/dev/null' _ {} \;
echo "已修复 .ssh 目录权限"

echo "修复完成"
```
</details>

#### 练习题 4：用户审计
编写一个脚本，找出系统中所有"可疑"用户（UID 0 但非 root、有 shell 的系统用户、空密码用户）：

<details>
<summary>答案</summary>

```bash
#!/bin/bash
echo "=== 可疑用户审计 ==="

echo ""
echo "--- UID 0 用户（应只有 root）---"
awk -F: '$3 == 0 && $1 != "root" {print "  RISK: " $1}' /etc/passwd
awk -F: '$3 == 0 && $1 != "root" {print "  RISK: " $1}' /etc/passwd | grep -c "RISK" | \
  xargs -I{} sh -c '[ {} -eq 0 ] && echo "  OK: 只有 root 拥有 UID 0"'

echo ""
echo "--- 有 Shell 的系统用户 (UID < 1000) ---"
awk -F: '$3 < 1000 && $3 > 0 && $7 !~ /nologin|false|sync|halt|shutdown/ {
    print "  WARN: " $1 " (UID=" $3 ", Shell=" $7 ")"
}' /etc/passwd

echo ""
echo "--- 空密码用户 ---"
for user in $(cut -d: -f1 /etc/passwd); do
    shadow_pass=$(getent shadow "$user" 2>/dev/null | cut -d: -f2)
    if [ -z "$shadow_pass" ]; then
        echo "  RISK: $user 密码字段为空"
    elif [ "$shadow_pass" = "!" ] || [ "$shadow_pass" = "*" ]; then
        : # 正常：锁定或无密码登录
    fi
done

echo ""
echo "--- 最近修改的用户（7天内）---"
find /etc/passwd /etc/shadow -mtime -7 -exec stat -c '%y %n' {} \; 2>/dev/null
```
</details>

#### 练习题 5：综合排错
用户报告无法通过 SSH 登录服务器，且网站出现 403 错误。列出你的完整排查步骤（至少 8 步）：

<details>
<summary>答案</summary>

```bash
# === SSH 登录失败排查 ===
# 1. 检查 SSH 服务状态
sudo systemctl status sshd

# 2. 检查防火墙端口
sudo ufw status | grep 22
# 或
sudo firewall-cmd --list-ports

# 3. 检查 SSH 配置
grep -E "^(Port|PermitRootLogin|PasswordAuthentication|PubkeyAuthentication)" /etc/ssh/sshd_config

# 4. 检查 fail2ban 是否封禁
sudo fail2ban-client status sshd

# 5. 检查认证日志
sudo tail -50 /var/log/auth.log | grep sshd

# 6. 检查用户账户状态
sudo passwd -S username

# 7. 检查 SSH 密钥权限
namei -l /home/username/.ssh/authorized_keys

# === 403 错误排查 ===
# 8. 检查 Nginx 错误日志
sudo tail -20 /var/log/nginx/error.log

# 9. 检查 Web 目录权限
ls -la /var/www/html/
namei -l /var/www/html/index.html

# 10. 检查 SELinux/AppArmor
getenforce
sudo aa-status | grep nginx

# 11. 检查 Nginx 运行用户
grep user /etc/nginx/nginx.conf

# 12. 修复权限
sudo chown -R www-data:www-data /var/www/html/
sudo find /var/www/html -type f -exec chmod 644 {} +
sudo find /var/www/html -type d -exec chmod 755 {} +
```
</details>

#### 练习题 6：脚本编写
编写一个脚本，接受一个用户名作为参数，输出该用户的完整安全报告（密码策略、sudo 权限、SSH 密钥、最近登录）：

<details>
<summary>答案</summary>

```bash
#!/bin/bash
username="${1:?用法: $0 <用户名>}"

id "$username" &>/dev/null || { echo "用户不存在"; exit 1; }

echo "=== 用户安全报告: $username ==="
echo "生成时间: $(date)"

echo ""
echo "--- 基本信息 ---"
echo "UID/GID: $(id "$username")"
echo "Shell: $(getent passwd "$username" | cut -d: -f7)"
echo "Home: $(eval echo ~"$username")"
echo "注释: $(getent passwd "$username" | cut -d: -f5)"

echo ""
echo "--- 密码策略 ---"
chage -l "$username"

echo ""
echo "--- sudo 权限 ---"
sudo -l -U "$username" 2>/dev/null || echo "无 sudo 权限"
echo "sudoers.d 配置:"
[ -f "/etc/sudoers.d/$username" ] && cat "/etc/sudoers.d/$username" || echo "  无独立配置"

echo ""
echo "--- SSH 密钥 ---"
ssh_dir="$(eval echo ~"$username")/.ssh"
if [ -d "$ssh_dir" ]; then
    echo ".ssh 目录权限: $(stat -c %a "$ssh_dir")"
    [ -f "$ssh_dir/authorized_keys" ] && \
        echo "公钥数量: $(wc -l < "$ssh_dir/authorized_keys")" || \
        echo "无 authorized_keys"
else
    echo "无 .ssh 目录"
fi

echo ""
echo "--- 最近登录 ---"
last -n 10 "$username" 2>/dev/null || echo "无登录记录"

echo ""
echo "--- 最近 sudo 使用 ---"
grep "sudo.*$username" /var/log/auth.log 2>/dev/null | tail -10 || echo "无 sudo 记录"

echo ""
echo "--- 运行中的进程 ---"
ps -u "$username" 2>/dev/null || echo "无运行进程"

echo ""
echo "--- crontab ---"
crontab -u "$username" -l 2>/dev/null || echo "无 crontab"
```
</details>

---

## 📊 第一周自我评估表

完成以下自评，了解自己的掌握程度：

| 知识领域 | 评估标准 | 掌握程度 |
|---------|---------|---------|
| **Day 01: Linux 基础** | 能解释 Linux 哲学、选择合适的发行版 | ⭐⭐⭐⭐⭐ |
| **Day 02: FHS 文件系统** | 能说出 /etc /var /tmp /proc 的作用 | ⭐⭐⭐⭐⭐ |
| **Day 03: 文件操作** | 能熟练使用 cp/mv/rm/find | ⭐⭐⭐⭐⭐ |
| **Day 04: 文本处理** | 能用 grep/sed/awk 分析日志 | ⭐⭐⭐⭐⭐ |
| **Day 05: 权限管理** | 能解释 rwx/SUID/ACL/umask | ⭐⭐⭐⭐⭐ |
| **Day 06: 用户管理** | 能配置用户/sudo/密码策略 | ⭐⭐⭐⭐⭐ |
| **Day 07: 综合实战** | 能独立完成服务器初始化 | ⭐⭐⭐⭐⭐ |

**评分标准**：
- ⭐ 需要参考答案才能理解
- ⭐⭐ 只能完成基础操作
- ⭐⭐⭐ 能完成大部分，偶尔需要查阅文档
- ⭐⭐⭐⭐ 能独立完成，偶尔确认命令语法
- ⭐⭐⭐⭐⭐ 能不查阅文档完成所有任务，并能解释原理

**目标**：达到 ⭐⭐⭐⭐ 及以上即可进入第二阶段（进程与服务管理）。

---

## 📚 扩展阅读

### 在线资源
- [The Linux Command Line (William Shotts)](https://linuxcommand.org/tlcl.php) -- 免费电子书
- [Explain Shell](https://explainshell.com/) -- 命令解释工具
- [ShellCheck](https://www.shellcheck.net/) -- Shell 脚本静态分析
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) -- Linux 安全练习
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks) -- 安全基线

### 推荐书籍
- 《鸟哥的 Linux 私房菜》-- 全面的 Linux 入门
- 《How Linux Works》-- 深入理解 Linux 原理
- 《Linux 命令行与 Shell 脚本编程大全》-- Shell 脚本进阶
- 《Linux 系统管理与网络管理》-- 系统管理实战

### SRE 相关
- [Google SRE Books](https://sre.google/sre-book/table-of-contents/) -- SRE 圣经
- [Ops School](http://www.ops-school.org/) -- 运维学习路径
- [Linux Performance](http://www.brendangregg.com/linuxperf.html) -- 性能分析

---

## ✅ 自检清单

### 综合能力检查
- [ ] 能独立完成新服务器从零到可用的初始化
- [ ] 能使用 grep/sed/awk 分析 auth.log 和 Nginx 日志
- [ ] 能排查 Nginx 403 Forbidden 权限问题
- [ ] 能排查 SSH 密钥登录失败问题
- [ ] 能设计多团队共享目录的权限方案
- [ ] 能编写服务器安全审计脚本
- [ ] 能编写跨发行版的初始化脚本
- [ ] 理解 SUID/SGID/Sticky Bit 的安全影响
- [ ] 能正确配置 sudo 权限（最小权限原则）
- [ ] 能配置密码策略和用户生命周期管理

### 下一步
完成第一周的学习后，你将进入第二阶段：**进程与服务管理**
- Day 08: 进程管理基础 -- ps/top/htop/pstree
- Day 09: 进程控制 -- kill/killall/pkill/信号机制
- Day 10: systemd 服务管理 -- systemctl 与单元文件

---

*由 SRE 学习计划生成 | 2026-04-26*
