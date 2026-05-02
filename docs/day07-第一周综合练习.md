# Day 07: 复习与实战 — 第一周综合练习

> 📅 日期：2026-04-25
> 📖 学习主题：复习与实战：第一周综合练习
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 07 的学习后，你应该掌握：
- 综合运用 Day 01-06 的知识完成真实的服务器运维任务
- 能独立从零配置一台生产服务器（用户、权限、工具、防火墙）
- 能使用 grep/sed/awk 对日志进行高效分析
- 能排查和修复常见的权限问题（403 Forbidden、Permission Denied）
- 理解 Linux 核心哲学在实际运维中的体现

---

## 📖 回顾：前六天核心知识

### Day 01 — Linux 简介

| 知识点 | 要点 |
|--------|------|
| 什么是 Linux | 开源 Unix-like 内核，Linus Torvalds 1991 年发布 |
| 核心哲学 | 一切皆文件、小而专一工具、开源共享、跨平台兼容 |
| 发行版选择 | 入门用 Ubuntu LTS，生产用 Rocky Linux / Debian |
| 虚拟机环境 | WSL2（Windows）、VirtualBox（全平台）、VMware（专业） |

### Day 02 — FHS 文件系统标准

| 目录 | 用途 | 示例 |
|------|------|------|
| `/` | 根目录，一切从这里开始 | — |
| `/bin` | 用户基础命令 | `ls`, `cp`, `cat` |
| `/sbin` | 系统管理命令 | `fdisk`, `iptables`, `reboot` |
| `/etc` | 配置文件（纯文本） | `/etc/passwd`, `/etc/fstab` |
| `/var` | 可变数据（日志、缓存） | `/var/log/syslog` |
| `/tmp` | 临时文件（重启清除） | 测试文件、临时解压 |
| `/home` | 用户家目录 | `/home/sreuser` |
| `/usr` | 用户程序（只读） | `/usr/local/bin` |
| `/proc` | 虚拟文件系统（进程/内核信息） | `/proc/cpuinfo` |
| `/dev` | 设备文件 | `/dev/sda`, `/dev/null` |

**关键概念：绝对路径 vs 相对路径**
```bash
# 绝对路径 — 从 / 开始，不受当前目录影响
ls /var/log/syslog

# 相对路径 — 相对于当前工作目录
cd /var
ls log/syslog    # 等同于 ls /var/log/syslog

# pwd 确认当前位置
pwd              # 输出: /var
```

### Day 03 — 文件操作命令

| 命令 | 用途 | 常用选项 |
|------|------|---------|
| `cp` | 复制文件/目录 | `-r`（递归）, `-p`（保留属性）, `-a`（归档） |
| `mv` | 移动/重命名 | — |
| `rm` | 删除文件/目录 | `-r`（递归）, `-f`（强制）, `-i`（交互确认） |
| `touch` | 创建空文件/更新时间戳 | `-t`（指定时间） |
| `mkdir` | 创建目录 | `-p`（递归创建父目录）, `-v`（显示创建信息） |
| `find` | 搜索文件 | `-name`, `-type`, `-size`, `-mtime`, `-exec` |

**find 高级用法：**
```bash
# 按时间查找（7天内修改过的文件）
find /var/log -type f -mtime -7

# 按大小查找（大于100MB的文件）
find / -type f -size +100M 2>/dev/null

# 按权限查找（全局可写的危险文件）
find /home -type f -perm -o+w

# 查找并执行操作
find /tmp -name "*.tmp" -mtime +3 -exec rm -f {} \;

# 查找特定扩展名的文件
find . -name "*.log" -o -name "*.txt"

# 查找空文件
find /var -type f -empty
```

### Day 04 — 文本处理三剑客 + 正则

**grep — 搜索文本：**
```bash
# 基本搜索
grep "error" /var/log/syslog

# 忽略大小写 + 显示行号 + 显示前后2行
grep -inC2 "failed" /var/log/auth.log

# 排除匹配的行
grep -v "^#" /etc/nginx/nginx.conf

# 使用正则表达式
grep -E "^[0-9]{1,3}(\.[0-9]{1,3}){3}" /var/log/nginx/access.log

# 统计匹配行数
grep -c "ERROR" /var/log/app.log
```

**sed — 流编辑器：**
```bash
# 替换（默认输出到屏幕，不修改原文件）
sed 's/old/new/g' file.txt

# 原地修改文件
sed -i 's/old/new/g' file.txt

# 删除包含特定内容的行
sed '/pattern/d' file.txt

# 只打印匹配的行
sed -n '/pattern/p' file.txt

# 在第3行后插入
sed '3a\new line' file.txt

# 删除第5到10行
sed '5,10d' file.txt
```

**awk — 列处理工具：**
```bash
# 打印第1列和第7列（默认空格分隔）
awk '{print $1, $7}' /var/log/nginx/access.log

# 按条件过滤（HTTP状态码为500的行）
awk '$9 == 500 {print $1, $7, $9}' /var/log/nginx/access.log

# 使用自定义分隔符（/etc/passwd 用 : 分隔）
awk -F: '$3 >= 1000 {print $1, $3}' /etc/passwd

# 统计每个IP的请求数
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -20

# 计算总和（日志中文件大小列）
awk '{sum += $5} END {print "Total:", sum}' file.log
```

**正则表达式速查：**
| 模式 | 含义 | 示例 |
|------|------|------|
| `^` | 行首 | `^root` 匹配以 root 开头的行 |
| `$` | 行尾 | `bash$` 匹配以 bash 结尾的行 |
| `.` | 任意单个字符 | `gr.y` 匹配 gray/groy |
| `*` | 前一个字符0次或多次 | `ab*c` 匹配 ac/abc/abbc |
| `+` | 前一个字符1次或多次（扩展正则） | `ab+c` 匹配 abc/abbc |
| `[]` | 字符集合 | `[0-9]` 匹配数字 |
| `()` | 分组（扩展正则） | `(abc)+` |
| `\|` | 或（扩展正则） | `error\|warning` |

### Day 05 — 权限管理

**权限模型：**
```
-rwxr-xr-- 1 root root 4096 Jan 1 00:00 file
│  │  │  │
│  │  │  └─ 其他用户权限 (r--)
│  │  └──── 组用户权限 (r-x)
│  └─────── 所有者权限 (rwx)
└────────── 文件类型 (- 文件, d 目录, l 链接)
```

**数字权限速查：**
| 权限 | 数字 | 含义 |
|------|------|------|
| `r` | 4 | 读 |
| `w` | 2 | 写 |
| `x` | 1 | 执行 |
| `rwx` | 7 | 全部 |
| `r-x` | 5 | 读 + 执行 |
| `rw-` | 6 | 读 + 写 |

```bash
# 修改权限
chmod 755 /usr/local/bin/script.sh    # rwxr-xr-x
chmod 644 /etc/config.conf             # rw-r--r--
chmod +x script.sh                     # 添加执行权限

# 修改所有者
chown user:group file.txt

# ACL 精细控制
setfacl -m u:deploy:rwx /var/www/
getfacl /var/www/
```

### Day 06 — 用户与用户组

```bash
# 创建用户
useradd -m -s /bin/bash -G sudo,sre deployer
passwd deployer

# 修改用户
usermod -aG docker deployer
usermod -L deployer      # 锁定账户
usermod -U deployer      # 解锁账户

# 删除用户（保留家目录）
userdel deployer
# 删除用户及家目录
userdel -r deployer

# 用户组
groupadd sre
groupadd -r system-monitor    # 系统组（GID < 1000）

# sudo 配置（编辑 sudoers 必须用 visudo）
visudo
# 添加：deployer ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
```

---

## 🏗️ 实战场景

### 场景 1：新购云服务器从零配置

你刚拿到一台全新的 Ubuntu 22.04 服务器，SSH 进去后需要做以下初始化：

```bash
# ========== 1. 系统更新 ==========
sudo apt update && sudo apt upgrade -y

# 检查系统版本
cat /etc/os-release
uname -r                     # 内核版本
uptime                       # 运行时间和负载

# ========== 2. 创建运维用户（禁用 root 直接登录） ==========
sudo useradd -m -s /bin/bash -G sudo sreuser
sudo passwd sreuser
# 设置强密码后，切换到新用户登录
su - sreuser

# ========== 3. 配置 SSH 密钥登录 ==========
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# 将你的公钥添加到 authorized_keys
echo "ssh-ed25519 AAAA... your@email.com" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 禁止密码登录（提高安全性）
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# ========== 4. 安装基础工具 ==========
sudo apt install -y \
  curl wget vim git tree htop \
  net-tools iproute2 \
  ufw fail2ban \
  unzip jq tmux

# ========== 5. 配置防火墙 ==========
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw --force enable
sudo ufw status numbered

# ========== 6. 安装 fail2ban（防爆破） ==========
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo sed -i 's/bantime  = 10m/bantime  = 1h/' /etc/fail2ban/jail.local
sudo sed -i 's/maxretry = 5/maxretry = 3/' /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
# 查看被 ban 的 IP
sudo fail2ban-client status sshd

# ========== 7. 配置 NTP 时间同步 ==========
sudo timedatectl set-timezone Asia/Shanghai
sudo systemctl enable systemd-timesyncd
sudo systemctl start systemd-timesyncd
timedatectl status

# ========== 8. 系统参数调优 ==========
# 创建 sysctl 配置文件
sudo tee /etc/sysctl.d/99-sre-tuning.conf > /dev/null << 'EOF'
# 增加文件描述符限制
fs.file-max = 65536

# 网络优化
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 600

# 防止 SYN Flood
net.ipv4.tcp_syncookies = 1
EOF
sudo sysctl --system

# ========== 9. 验证配置 ==========
echo "=== 系统信息 ==="
hostname
ip addr show | grep "inet " | awk '{print $2}'
echo "=== 运行时间 ==="
uptime
echo "=== 磁盘使用 ==="
df -h /
echo "=== 内存使用 ==="
free -h
echo "=== 防火墙状态 ==="
sudo ufw status
echo "=== 已安装工具 ==="
which curl git jq htop tmux
echo "=== SSH 安全 ==="
sudo grep -E "PermitRootLogin|PasswordAuthentication" /etc/ssh/sshd_config
```

### 场景 2：Nginx 日志分析挑战

假设服务器跑了 Nginx，日志在 `/var/log/nginx/access.log`：

```bash
# ---------- 问题 1：哪个 IP 访问最多？ ----------
awk '{print $1}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head -10

# 输出示例：
#   15234 192.168.1.100
#    8421 10.0.0.55
#    3102 203.0.113.42

# ---------- 问题 2：有哪些 5xx 错误？ ----------
awk '$9 ~ /^5[0-9][0-9]$/ {print $7, $9}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head -20

# 输出示例：
#     42 /api/users 500
#     18 /api/orders 502
#      7 /health 503

# ---------- 问题 3：找出攻击者（暴力扫描） ----------
# 扫描器特征：大量 404，短时间内请求不同路径
awk '$9 == 404 {print $1}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head -10

# 结合时间分析 — 某个 IP 在 1 分钟内请求了多少次
awk '$9 == 404 {print $1, $4}' /var/log/nginx/access.log \
  | sed 's/\[//' | awk '{print $1, substr($2,1,15)}' \
  | sort | uniq -c | sort -rn | head -10

# ---------- 问题 4：分析请求耗时（如果有 $request_time） ----------
# 自定义 Nginx log_format: $remote_addr - $request_time
awk '{print $1, $NF}' access.log \
  | awk '{sum[$1]+=$2; count[$1]++} END {for(ip in sum) printf "%s avg=%.3f count=%d\n", ip, sum[ip]/count[ip], count[ip]}' \
  | sort -t= -k2 -rn | head -10

# ---------- 问题 5：按小时统计请求量 ----------
awk '{print substr($4,2,12)}' access.log \
  | awk -F: '{print $1":"$2":00"}' \
  | sort | uniq -c \
  | awk '{printf "%s  %d 请求\n", $2, $1}'

# ---------- 问题 6：实时查看最近 10 个请求 ----------
tail -f /var/log/nginx/access.log \
  | awk '{print $1, $6, $7, $9}'
```

### 场景 3：权限排查实战

**问题：用户访问网站出现 403 Forbidden**

```bash
# ---------- 排查步骤 1：检查文件权限 ----------
ls -la /var/www/html/index.html
# 输出：-rw------- 1 root root 1234 Jan 1 00:00 index.html
# 问题：Nginx 用户（www-data）没有读权限！

# 修复：
sudo chmod 644 /var/www/html/index.html
sudo chown www-data:www-data /var/www/html/index.html

# ---------- 排查步骤 2：检查父目录权限 ----------
# 即使文件权限正确，父目录没有 x 权限也无法访问
namei -l /var/www/html/index.html
# 输出显示每一级的权限，检查路径上是否有拒绝访问的目录

# 修复目录权限：
sudo chmod 755 /var/www/html/
sudo chmod 755 /var/www/

# ---------- 排查步骤 3：检查 SELinux/AppArmor（如果启用） ----------
# CentOS/RHEL 检查 SELinux：
sestatus
# 如果 SELinux 是 enforcing 模式：
ls -Z /var/www/html/index.html

# Ubuntu 检查 AppArmor：
sudo aa-status | grep nginx

# ---------- 排查步骤 4：检查 Nginx 配置 ----------
sudo nginx -t                     # 测试配置语法
sudo cat /etc/nginx/nginx.conf | grep -E "user|worker"
# 确认 nginx.conf 中的 user 指令：user www-data;

# ---------- 排查步骤 5：检查 Nginx 错误日志 ----------
sudo tail -20 /var/log/nginx/error.log
# 典型错误：
# "Permission denied" → 文件或目录权限问题
# "open() failed (13: Permission denied)" → SELinux/AppArmor
```

### 场景 4：磁盘空间告警

```bash
# 收到磁盘使用率 > 90% 告警

# 1. 确认是哪个分区满了
df -h
# 输出：/dev/sda1  100G  95G  5G  95% /

# 2. 找出占用最大的目录
sudo du -sh /* 2>/dev/null | sort -rh | head -10
# 假设发现 /var 占了 60G

# 3. 深入分析
sudo du -sh /var/* 2>/dev/null | sort -rh | head -10
# 发现 /var/log 占了 45G

# 4. 找出最大的日志文件
sudo find /var/log -type f -size +100M -exec ls -lh {} \; | sort -k5 -rh

# 5. 安全清理（不要直接 rm 正在写入的日志！）
# 方法 1：truncate 清空文件（保留 inode，不中断写入）
sudo truncate -s 0 /var/log/nginx/access.log
sudo truncate -s 0 /var/log/syslog

# 方法 2：用日志轮转
sudo logrotate -f /etc/logrotate.conf

# 方法 3：清理旧的轮转日志
sudo find /var/log -name "*.gz" -mtime +30 -delete

# 6. 验证
df -h /
du -sh /var/log
```

### 场景 5：Shell 脚本编写练习

编写一个系统健康检查脚本：

```bash
#!/bin/bash
# health_check.sh — 系统健康检查脚本

set -euo pipefail    # 严格模式：错误即退出、未定义变量报错、管道失败传播

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err() { echo -e "${RED}[ERR]${NC} $1"; }

echo "========================================"
echo "  系统健康检查  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  主机: $(hostname)"
echo "========================================"

# --- 1. 磁盘使用 ---
echo ""
echo "--- 磁盘使用 ---"
while read -r usage mount; do
    pct=${usage%\%}
    if (( pct > 90 )); then
        log_err "磁盘 $mount 使用率 ${usage}，超过 90% 阈值"
    elif (( pct > 75 )); then
        log_warn "磁盘 $mount 使用率 ${usage}"
    else
        log_ok "磁盘 $mount 使用率 ${usage}"
    fi
done < <(df -h --output=pcent,target / 2>/dev/null | tail -n +2)

# --- 2. 内存使用 ---
echo ""
echo "--- 内存使用 ---"
mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
mem_available=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
mem_used=$((mem_total - mem_available))
mem_pct=$((mem_used * 100 / mem_total))

if (( mem_pct > 90 )); then
    log_err "内存使用率 ${mem_pct}%"
elif (( mem_pct > 75 )); then
    log_warn "内存使用率 ${mem_pct}%"
else
    log_ok "内存使用率 ${mem_pct}%"
fi

# --- 3. 负载 ---
echo ""
echo "--- 系统负载 ---"
load=$(cat /proc/loadavg | awk '{print $1}')
cpus=$(nproc)
# 负载 > CPU 核心数 表示过载
if (( $(echo "$load > $cpus" | bc -l) )); then
    log_warn "负载 $load 超过 CPU 核心数 $cpus"
else
    log_ok "负载 $load (CPU: $cpus 核心)"
fi

# --- 4. 僵尸进程 ---
echo ""
echo "--- 进程检查 ---"
zombies=$(ps aux | awk '$8 ~ /Z/ {count++} END {print count+0}')
if (( zombies > 0 )); then
    log_warn "发现 $zombies 个僵尸进程"
    ps aux | awk '$8 ~ /Z/ {print $0}'
else
    log_ok "无僵尸进程"
fi

# --- 5. SSH 登录失败 ---
echo ""
echo "--- 安全检查 ---"
if [ -f /var/log/auth.log ]; then
    failed=$(grep -c "Failed password" /var/log/auth.log 2>/dev/null || echo 0)
    if (( failed > 10 )); then
        log_warn "SSH 登录失败 $failed 次"
        grep "Failed password" /var/log/auth.log \
          | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -5
    else
        log_ok "SSH 登录失败 $failed 次（正常）"
    fi
fi

echo ""
echo "========================================"
echo "  检查完成"
echo "========================================"
```

**脚本使用方法：**
```bash
# 赋予执行权限
chmod +x health_check.sh

# 运行
./health_check.sh

# 通过 cron 定时运行（每 15 分钟）
echo "*/15 * * * * /path/to/health_check.sh >> /var/log/health_check.log 2>&1" \
  | sudo tee -a /etc/crontab
```

---

## 🧪 自我评估

完成以下练习来检验掌握程度：

### 练习题 1：文件搜索
在 `/etc` 目录下查找所有 `.conf` 文件，大小超过 10KB，最近 30 天内修改过的：
<details>
<summary>答案</summary>

```bash
find /etc -type f -name "*.conf" -size +10k -mtime -30 -ls
```
</details>

### 练习题 2：日志分析
从 Nginx access.log 中提取所有 POST 请求，统计每个 URL 的请求次数，按降序排列：
<details>
<summary>答案</summary>

```bash
grep '"POST ' /var/log/nginx/access.log \
  | awk '{print $7}' \
  | sort | uniq -c | sort -rn
```
</details>

### 练习题 3：权限修复
将 `/var/www/` 下所有文件设置为 644，所有目录设置为 755，所有者设为 www-data：
<details>
<summary>答案</summary>

```bash
sudo find /var/www/ -type f -exec chmod 644 {} +
sudo find /var/www/ -type d -exec chmod 755 {} +
sudo chown -R www-data:www-data /var/www/
```
</details>

### 练习题 4：文本处理
从 `/etc/passwd` 中筛选出 UID >= 1000 的普通用户，只显示用户名和家目录：
<details>
<summary>答案</summary>

```bash
awk -F: '$3 >= 1000 {print $1, $6}' /etc/passwd
```
</details>

### 练习题 5：综合排错
用户报告无法通过 SSH 登录服务器，列出你的排查步骤（至少 5 步）：
<details>
<summary>答案</summary>

```bash
# 1. 检查 SSH 服务是否在运行
sudo systemctl status sshd

# 2. 检查防火墙是否放行 22 端口
sudo ufw status | grep 22

# 3. 检查 SSH 配置是否允许密码/密钥登录
sudo grep -E "PasswordAuthentication|PubkeyAuthentication" /etc/ssh/sshd_config

# 4. 检查 fail2ban 是否封禁了用户 IP
sudo fail2ban-client status sshd

# 5. 检查认证日志
sudo tail -50 /var/log/auth.log

# 6. 检查用户账户是否被锁定
sudo passwd -S username
```
</details>

### 练习题 6：脚本编写
编写一个脚本，接受一个目录路径作为参数，输出该目录中：
- 文件总数
- 目录总数
- 最大文件及其大小
- 最近修改的文件
<details>
<summary>答案</summary>

```bash
#!/bin/bash
dir="${1:?用法: $0 <目录路径>}"

if [ ! -d "$dir" ]; then
    echo "错误: $dir 不是一个目录"
    exit 1
fi

echo "=== 目录分析: $dir ==="
echo "文件总数: $(find "$dir" -type f | wc -l)"
echo "目录总数: $(find "$dir" -type d | wc -l)"

echo "最大文件:"
find "$dir" -type f -printf '%s %p\n' | sort -rn | head -1

echo "最近修改:"
find "$dir" -type f -printf '%T+ %p\n' | sort -rn | head -1
```
</details>

---

## 📊 评分标准

| 等级 | 标准 |
|------|------|
| ⭐⭐⭐⭐⭐ | 能独立完成所有 6 道练习题，不查阅文档 |
| ⭐⭐⭐⭐ | 能完成 4-5 道，偶尔查阅文档确认命令语法 |
| ⭐⭐⭐ | 能完成 2-3 道，需要查阅文档理解思路 |
| ⭐⭐ | 只能完成基础题，对组合命令不熟悉 |
| ⭐ | 需要参考答案才能理解 |

**目标**：达到 ⭐⭐⭐⭐ 及以上即可进入下一阶段。

---

## 📚 扩展阅读

- [The Linux Command Line (William Shotts)](https://linuxcommand.org/tlcl.php) — 免费电子书，系统学习命令行
- [Explain Shell](https://explainshell.com/) — 在线工具，输入命令逐段解释
- [ShellCheck](https://www.shellcheck.net/) — Shell 脚本静态分析，发现常见错误
- [Linux Journey](https://linuxjourney.com/) — 交互式 Linux 学习平台
