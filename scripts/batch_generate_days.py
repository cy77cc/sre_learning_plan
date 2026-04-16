#!/usr/bin/env python3
"""
批量生成 SRE 学习文档 Day 1-28
对每个缺失的 dayN/README.md，运行 generate_day_doc() 填充内容
"""

import os
import sys
import re
import subprocess
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple, Optional

BASE_DIR = Path("/root/sre_learning")
DOCS_DIR = BASE_DIR / "docs"
OUTPUT_DIR = Path("/root/sre_learning/cron/output")
START_DATE = date(2026, 4, 13)

# ── 从 daily_study_generator.py 复制的辅助函数 ──────────────────────────────

def run(cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout, cwd=BASE_DIR
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def git_config():
    run(f'git config --global user.email "hermes@sre-learning.local"')
    run(f'git config --global user.name "Hermes Agent"')
    run(f'git config --global --add safe.directory "{BASE_DIR}"')

def get_topic_from_overview(day: int) -> Optional[str]:
    overview = DOCS_DIR / "00-overview.md"
    if not overview.exists():
        return None
    content = overview.read_text()
    patterns = [
        rf'### Day\s+{day}\s*\n.*?\*\*学习内容\*\*[：:]\s*([^\n]+)',
        rf'### Day\s+{day}\s*-+\s*\n.*?-\s+\*\*学习内容\*\*[：:]\s*([^\n]+)',
        rf'-\s+\[?\s*\*?Day\s+{day}\s*\]?\s*-+\s*\n.*?-\s+\*\*学习内容\*\*[：:]\s*([^\n]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            topic = match.group(1).strip()
            topic = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', topic)
            topic = topic.replace('**', '').replace('*', '')
            return topic
    return None

def get_topic_fallback(day: int) -> str:
    topics = {
        1: "Linux简介与虚拟机安装 - Ubuntu 22.04安装与基础配置",
        2: "Linux文件系统与目录结构 - FHS标准详解",
        3: "Linux文件操作命令 - cp/mv/rm/cat/head/tail",
        4: "文本处理三剑客 - grep/sed/awk与正则表达式",
        5: "文件权限管理 - chmod/chown与数字权限",
        6: "用户与用户组管理 - useradd/usermod/sudo",
        7: "第一周综合复习与实战练习",
        8: "进程管理基础 - ps/top/htop/pstree",
        9: "进程控制 - kill/killall/信号机制",
        10: "systemd服务管理 - systemctl/单元文件",
        11: "系统监控命令 - uptime/free/df/vmstat/sar",
        12: "磁盘管理 - fdisk/mkfs/mount/du/df",
        13: "日志管理 - journalctl/rsyslog/日志分析",
        14: "第二周综合实战 - LAMP环境搭建",
        15: "Shell脚本基础 - 变量/环境变量/引号",
        16: "Shell条件判断 - if/elif/else/test运算符",
        17: "Shell循环结构 - for/while/until",
        18: "Shell函数 - 函数定义/参数传递/返回值",
        19: "Case语句与菜单 - select菜单制作",
        20: "数组操作 - 数组遍历/关联数组",
        21: "字符串处理与正则 - sed/awk进阶",
        22: "脚本调试与信号 - trap/set -x/set -e",
        23: "expect自动化交互 - SSH自动登录",
        24: "实战项目 - 服务器初始化脚本",
        25: "实战项目 - 日志监控告警脚本",
        26: "实战项目 - 备份脚本编写",
        27: "Bash脚本编程进阶 - 高级技巧",
        28: "第一阶段总结与测试 - 综合能力评估",
    }
    return topics.get(day, f"Day {day} 复习与扩展学习")

# ── 内容生成器（从 daily_study_generator.py 提取/精简） ───────────────────

def gen_common_resources() -> str:
    return """## 📚 最新优质资源

### 官方文档
- [Ubuntu 22.04 LTS 官方文档](https://ubuntu.com/documentation)
- [Linux FHS 标准 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [GNU Coreutils 手册](https://www.gnu.org/software/coreutils/manual/)
- [Bash 官方手册](https://www.gnu.org/software/bash/manual/)

### 推荐教程
- [MIT The Missing Semester](https://missing.csail.mit.edu/)
- [Linux Journey](https://linuxjourney.com/)
- [Ryan's Tutorials - Linux](https://ryanstutorials.net/linuxtutorial/)
- [Linux Command Library](https://linuxcommand.org/)

### 视频课程
- [Bilibili: 鸟哥的Linux私房菜（基础篇）](https://www.bilibili.com/video/BV1Vt411X7y6/)
- [YouTube: NetworkChuck - Linux Basics](https://www.youtube.com/playlist?list=PLI9KFC2-DCX-6LVEU2c2XBGWckzVqKS6j)

### 实战练习平台
- [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) - 史上最好的 Linux 入门练习
- [KodeKloud Engineer](https://kodekloud.com) - 交互式 K8s 和 DevOps 练习
- [Learn Linux TV](https://www.learnlinux.tv/) - 视频 + 实战

### SRE 相关资源
- [Google SRE Books](https://sre.google/sre-book/table-of-contents/)
- [Linux Performance](http://www.brendangregg.com/linuxperf.html) - Brendan Gregg
"""

def gen_week1_review(day: int) -> str:
    return f"""## 📋 第一周综合复习

### 本周知识点回顾

**Day 1-3 核心要点**：
- Linux 历史、发行版分类、Ubuntu 安装
- FHS 文件系统标准：/bin, /etc, /home, /var, /usr 等
- 文件操作命令：cp, mv, rm, cat, head, tail, wc

**Day 4-6 核心要点**：
- grep/sed/awk 文本处理三剑客
- chmod/chown 权限管理（755, 644, 数字权限）
- useradd/usermod/sudo 用户管理

### 综合练习

#### 练习 1：搭建练习环境
```bash
# 1. 在 VirtualBox/WSL2 中确认 Ubuntu 22.04 可用
lsb_release -a
uname -r

# 2. 更新系统
sudo apt update && sudo apt upgrade -y

# 3. 安装常用工具
sudo apt install -y vim git htop tree net-tools
```

#### 练习 2：文件管理实战
```bash
# 创建测试目录结构
mkdir -p ~/sre_practice/{{configs,logs,scripts,data}}

# 模拟配置文件
echo "# Nginx config" > ~/sre_practice/configs/nginx.conf
echo "error log" > ~/sre_practice/logs/error.log

# 用 find 查找所有文件
find ~/sre_practice -type f

# 用 grep 在日志中搜索
echo "2026-04-15 ERROR: disk full" >> ~/sre_practice/logs/error.log
echo "2026-04-15 INFO: service started" >> ~/sre_practice/logs/error.log
grep "ERROR" ~/sre_practice/logs/error.log
```

#### 练习 3：权限与用户
```bash
# 创建开发组和开发用户
sudo groupadd developers
sudo useradd -m -s /bin/bash -G developers devuser

# 创建共享目录
sudo mkdir /shared
sudo chgrp developers /shared
sudo chmod 2775 /shared

# 验证
ls -ld /shared
id devuser
```

#### 练习 4：文本处理挑战
```bash
# 用 awk 统计日志中各状态码出现次数
# 模拟 access.log
cat > /tmp/access.log << 'EOF'
192.168.1.1 - - [15/Apr/2026:10:00:00 +0800] "GET /index.html HTTP/1.1" 200 1234
192.168.1.2 - - [15/Apr/2026:10:01:00 +0800] "GET /api/users HTTP/1.1" 404 234
192.168.1.1 - - [15/Apr/2026:10:02:00 +0800] "POST /api/login HTTP/1.1" 500 512
EOF

awk '{{print $9}}' /tmp/access.log | sort | uniq -c | sort -rn
```

### 自我测试

回答以下问题：
1. Linux 中一切皆文件，/dev/null 和 /dev/zero 是什么？有什么用途？
2. FHS 标准中，/var/log、/etc、/home 各存放什么内容？
3. 解释 Linux 权限模型：rwx 对文件和目录的区别是什么？
4. 如何让一个目录被多个用户共享，但各用户只能删除自己的文件？
5. 如何排查 "Permission denied" 错误？

### 答案参考

**Q1**: `/dev/null` 是空设备（黑洞），写入的数据被丢弃，读取返回 EOF；`/dev/zero` 是零字节源。用途：
```bash
# 丢弃不需要的输出
command > /dev/null 2>&1

# 创建空文件
dd if=/dev/zero of=/tmp/testfile bs=1M count=100

# 测试读取
cat /dev/zero | head -c 1024 > /dev/null
```

**Q4**: 使用 Sticky Bit：
```bash
chmod 1777 /shared      # 或 chmod +t /shared
# 其他用户的写入权限仍在，但不能删除别人的文件
```

---

## 💻 实战项目：文件管理脚本

### 项目目标
编写一个 `file_manager.sh` 脚本，实现以下功能：
1. 创建标准的 SRE 工作目录结构
2. 按日期归档日志文件
3. 查找指定天数前的旧文件
4. 生成磁盘使用报告

```bash
#!/bin/bash
# file_manager.sh - SRE 文件管理工具

set -e

SRE_ROOT="${{HOME}}/sre_work"
DAYS=7

usage() {{
    echo "用法: $0 <命令> [参数]"
    echo "命令:"
    echo "  init        - 初始化目录结构"
    echo "  archive     - 归档 $DAYS 天前的日志"
    echo "  oldfiles    - 查找 $DAYS 天前的文件"
    echo "  disk-report - 生成磁盘使用报告"
}}

init_structure() {{
    mkdir -p "$SRE_ROOT"/{{configs,logs,scripts,data,backups}}
    echo "✅ 目录结构已创建: $SRE_ROOT"
    tree "$SRE_ROOT"
}}

archive_old_logs() {{
    find "$SRE_ROOT/logs" -name "*.log" -mtime +$DAYS -exec gzip {{}} \\;
    mkdir -p "$SRE_ROOT/backups"
    tar -czf "$SRE_ROOT/backups/logs_archive_$(date +%Y%m%d).tar.gz" \\
        "$SRE_ROOT/logs"/*.gz 2>/dev/null || true
    echo "✅ 旧日志已归档"
}}

find_old_files() {{
    echo "查找 $DAYS 天前的文件..."
    find "$SRE_ROOT" -type f -mtime +$DAYS
}}

disk_report() {{
    echo "=== 磁盘使用报告 $(date) ==="
    echo ""
    echo "各目录大小:"
    du -sh "$SRE_ROOT"/* 2>/dev/null | sort -rh
    echo ""
    echo "磁盘总体:"
    df -h "$SRE_ROOT"
}}

case "$1" in
    init)        init_structure ;;
    archive)     archive_old_logs ;;
    oldfiles)    find_old_files ;;
    disk-report) disk_report ;;
    *)           usage; exit 1 ;;
esac
```

### 课后延伸
1. 给脚本添加日志功能（记录所有操作）
2. 添加 email 告警（当磁盘使用超过 80% 时）
3. 用 cron 定时执行 archive 命令
"""

def gen_week2_review(day: int) -> str:
    return f"""## 📋 第二周综合实战 - LAMP 环境搭建

### LAMP 架构概述

LAMP = Linux + Apache/Nginx + MySQL/PostgreSQL + PHP/Python/Perl

| 组件 | 常见选择 | SRE 关注点 |
|------|---------|-----------|
| Linux | Ubuntu 22.04 LTS | 稳定性、安全更新 |
| Web Server | Nginx | 高并发、内存效率 |
| Database | MySQL 8.0 / PostgreSQL 14 | 性能优化、备份 |
| Scripting | PHP 8.x / Python 3.10 | 安全版本选择 |

### 实战：使用 Docker 快速搭建 LAMP

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 2. 创建网络
docker network create lamp-net

# 3. 启动 MySQL
docker run -d \\
    --name mysql8 \\
    --network lamp-net \\
    -e MYSQL_ROOT_PASSWORD=StrongPassword123 \\
    -e MYSQL_DATABASE=myapp \\
    mysql:8

# 4. 启动 Nginx + PHP
docker run -d \\
    --name web \\
    --network lamp-net \\
    -p 80:80 \\
    -v ~/lamp/html:/var/www/html \\
    nginx:alpine

# 5. 进入容器安装 PHP
docker exec -it web apk add php php-fpm php-mysql
```

### 传统方式：直接安装 LAMP（Ubuntu）

```bash
# 1. 安装 Apache
sudo apt update
sudo apt install -y apache2

# 2. 安装 MySQL
sudo apt install -y mysql-server
sudo mysql_secure_installation

# 3. 安装 PHP
sudo apt install -y php libapache2-mod-php php-mysql

# 4. 配置虚拟主机
sudo vim /etc/apache2/sites-available/myapp.conf
# 内容：
# <VirtualHost *:80>
#     ServerName myapp.local
#     DocumentRoot /var/www/myapp
#     <Directory /var/www/myapp>
#         Options Indexes FollowSymLinks
#         AllowOverride All
#     </Directory>
# </VirtualHost>

sudo a2ensite myapp.conf
sudo a2enmod rewrite
sudo systemctl restart apache2

# 5. 测试 PHP
echo "<?php phpinfo(); ?>" | sudo tee /var/www/myapp/info.php
# 访问 http://your_ip/info.php
```

### 服务管理实战

```bash
# 查看所有服务状态
systemctl list-units --type=service --state=running

# 设置服务开机自启
sudo systemctl enable apache2 mysql

# 查看服务日志
journalctl -u apache2 -n 50 --no-pager
journalctl -u mysql -f

# 服务故障排查
sudo systemctl status apache2
sudo systemctl restart apache2
sudo apachectl configtest  # 测试配置语法
```

### 日志分析实战

```bash
# Apache/Nginx 访问日志分析
# 查看最新 20 条访问记录
tail -20 /var/log/apache2/access.log

# 统计每小时的请求数
awk '{{print $4}}' /var/log/apache2/access.log \\
    | cut -d: -f1 | sort | uniq -c

# 找出最常访问的页面
awk '{{print $7}}' /var/log/apache2/access.log \\
    | sort | uniq -c | sort -rn | head -10

# 找出访问量最大的 IP
awk '{{print $1}}' /var/log/apache2/access.log \\
    | sort | uniq -c | sort -rn | head -10

# 统计 404/500 错误
grep " 404 " /var/log/apache2/access.log | wc -l
grep " 500 " /var/log/apache2/access.log | wc -l
```

### 综合练习

#### 练习 1：自动化 LAMP 部署脚本
```bash
#!/bin/bash
# lamp_deploy.sh - LAMP 环境自动部署

set -e

DOMAIN=${1:-myapp.local}
DB_NAME=${2:-myapp}
DB_USER=${3:-myappuser}
DB_PASS=$(openssl rand -base64 24)

echo "=== LAMP 部署开始 ==="
echo "域名: $DOMAIN"
echo "数据库: $DB_NAME"

# 安装软件
sudo apt update
sudo apt install -y apache2 mysql-server php libapache2-mod-php php-mysql php-cli

# 配置防火墙
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 创建虚拟主机
sudo mkdir -p /var/www/$DOMAIN
cat | sudo tee /var/www/$DOMAIN/index.php << 'EOF'
<?php
echo "<h1>Welcome to <?= '$DOMAIN' ?></h1>";
echo "<p>PHP Version: " . phpversion() . "</p>";
phpinfo();
EOF

sudo tee /etc/apache2/sites-available/$DOMAIN.conf << EOF
<VirtualHost *:80>
    ServerName $DOMAIN
    DocumentRoot /var/www/$DOMAIN
    <Directory /var/www/$DOMAIN>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
EOF

sudo a2ensite $DOMAIN
sudo a2dissite 000-default.conf
sudo systemctl restart apache2

echo "=== 部署完成 ==="
echo "访问: http://$(hostname -I | awk '{{print $1}}')/"
```

#### 练习 2：MySQL 数据库备份脚本
```bash
#!/bin/bash
# backup_mysql.sh - MySQL 自动备份

BACKUP_DIR="/backups/mysql"
MYSQL_USER="root"
MYSQL_PASS="YourPassword"
DAYS_TO_KEEP=30

mkdir -p $BACKUP_DIR

# 备份所有数据库
for db in $(mysql -u$MYSQL_USER -p$MYSQL_PASS -e "SHOW DATABASES;" | grep -v Database); do
    mysqldump -u$MYSQL_USER -p$MYSQL_PASS \\
        --single-transaction --routines --triggers \\
        $db | gzip > "$BACKUP_DIR/${db}_$(date +%Y%m%d).sql.gz"
done

# 清理旧备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +$DAYS_TO_KEEP -delete

echo "备份完成: $(date)"
ls -lh $BACKUP_DIR/
```

### 第二周知识点总结

| 知识点 | 关键命令 |
|--------|---------|
| 进程查看 | `ps aux`, `top`, `htop`, `pstree` |
| 进程控制 | `kill`, `killall`, `pkill`, `SIGTERM/SIGKILL` |
| systemd | `systemctl start/stop/restart/enable`, `journalctl` |
| 磁盘管理 | `fdisk`, `mkfs`, `mount`, `df -h`, `du -sh` |
| 日志分析 | `journalctl`, `grep`, `awk`, `tail -f` |
| LAMP 部署 | `apt install`, `systemctl`, `apache/nginx` config |
"""

def gen_phase1_summary(day: int) -> str:
    return f"""## 📋 第一阶段总结与综合测试

### 第一阶段知识点全景图

```
第一阶段：Linux 基础与 Shell 脚本
├── Week 1：Linux 入门
│   ├── Day 1-3：Linux 基础 / 文件系统 / 文件操作
│   └── Day 4-6：文本处理 / 权限管理 / 用户管理
├── Week 2：进程管理与系统监控
│   ├── Day 8-9：进程管理 / 信号机制
│   ├── Day 10-11：systemd / 系统监控
│   ├── Day 12-13：磁盘管理 / 日志管理
│   └── Day 14：LAMP 综合实战
├── Week 3：Shell 脚本（上）
│   ├── Day 15-16：变量与引号
│   ├── Day 17-18：条件判断 / 循环结构
│   ├── Day 19-20：Case 语句 / 函数
│   └── Day 21：数组操作
└── Week 4：Shell 脚本（下）+ 实战
    ├── Day 22-23：字符串处理 / 信号与 trap
    ├── Day 24：expect 自动化
    └── Day 25-27：三大实战项目
```

### 综合能力自测

#### 基础命令（必须熟练）
```bash
# 文件操作
ls -la /var/log/     # 详细列表查看日志目录
find /etc -name "*.conf" -type f  # 查找配置文件
du -sh /*             # 查看各目录大小
df -h                 # 查看磁盘空间

# 文本处理
grep -r "error" /var/log/ --include="*.log"
awk '$9 >= 500 {{print $1, $9}}' /var/log/nginx/access.log
sed -i 's/old/new/g' /etc/nginx/nginx.conf

# 进程与服务
ps aux | grep nginx
systemctl status nginx
journalctl -u nginx -n 100 --no-pager
```

#### Shell 脚本能力测试
```bash
# 测试 1：编写服务监控脚本
#!/bin/bash
# 监控 Nginx 服务，如果挂了则重启并告警

SERVICE="nginx"
EMAIL="sre@example.com"

if ! systemctl is-active --quiet $SERVICE; then
    echo "$(date): $SERVICE is DOWN, restarting..." | tee /var/log/monitor.log
    systemctl restart $SERVICE
    sleep 3
    if systemctl is-active --quiet $SERVICE; then
        echo "$(date): $SERVICE restarted successfully" >> /var/log/monitor.log
    else
        echo "$(date): $SERVICE restart FAILED" | mail -s "ALERT" $EMAIL
    fi
fi

# 测试 2：日志分析脚本
#!/bin/bash
# 分析 access.log，输出 Top 10 IP、URL、状态码

LOG=${1:-/var/log/nginx/access.log}

echo "=== 日志分析报告 $(date) ==="
echo ""

echo "📊 Top 10 访问 IP:"
awk '{{print $1}}' $LOG | sort | uniq -c | sort -rn | head -10

echo ""
echo "📊 Top 10 请求 URL:"
awk '{{print $7}}' $LOG | sort | uniq -c | sort -rn | head -10

echo ""
echo "📊 HTTP 状态码分布:"
awk '{{print $9}}' $LOG | sort | uniq -c | sort -rn
```

### 实战项目验收

完成以下三个项目（选做，但强烈建议）：

#### 项目 A：服务器初始化脚本（Day 25）
```bash
#!/bin/bash
# init_server.sh - 新服务器初始化

# 1. 系统更新
apt update && apt upgrade -y

# 2. 创建 SRE 用户
useradd -m -s /bin/bash -G sudo,adm sre
echo "sre:NewPassword123" | chpasswd

# 3. 配置 SSH（禁用密码登录）
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd

# 4. 配置防火墙
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 5. 安装基础工具
apt install -y vim git htop tree curl wget net-tools dnsutils

# 6. 配置日志轮转
cat > /etc/logrotate.d/myapp << 'EOF'
/var/log/myapp/*.log {{
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
}}
EOF

echo "✅ 服务器初始化完成！"
```

#### 项目 B：日志监控告警脚本（Day 26）
```bash
#!/bin/bash
# log_monitor.sh - 实时日志关键词监控

LOG_FILE=${1:-/var/log/syslog}
KEYWORDS=${2:-"error|fatal|critical|failed"}
ALERT_EMAIL="sre@example.com"
STATE_FILE="/tmp/log_monitor.state"

# 获取上次读取位置
LAST_POS=$(cat $STATE_FILE 2>/dev/null || echo 0)

# 读取新日志
tail -c +$LAST_POS "$LOG_FILE" 2>/dev/null | \\
    grep -E "$KEYWORDS" | while read line; do
        echo "$(date): $line" | mail -s "[ALERT] Log Alert" $ALERT_EMAIL
    done

# 保存当前位置
stat -c %s "$LOG_FILE" > $STATE_FILE
```

#### 项目 C：备份脚本（Day 27）
```bash
#!/bin/bash
# backup.sh - 增量备份脚本

SRC="/home/www"
DEST="/backups/www"
DATE=$(date +%Y%m%d_%H%M%S)
LINK_DEST="/backups/www/latest"

# 创建备份（使用 rsync 的 --link-dest 实现增量）
rsync -av --delete \\
    --link-dest="$LINK_DEST" \\
    "$SRC/" "$DEST/backup_$DATE/"

# 更新 latest 软链接
rm -f "$LINK_DEST"
ln -s "$DEST/backup_$DATE" "$LINK_DEST"

# 清理 7 天前的备份
find "$DEST" -maxdepth 1 -type d -name "backup_*" -mtime +7 -exec rm -rf {{}} +

echo "✅ 备份完成: $DATE"
du -sh "$DEST"/*
```

### 自我评估标准

| 技能 | 达标标准 | 练习平台 |
|------|---------|---------|
| Linux 基础 | 能独立安装 Ubuntu 并完成基础配置 | OverTheWire Bandit Lv 1-10 |
| 文件操作 | 熟练使用 cp/mv/rm/find/grep | Bandit Lv 11-20 |
| 权限管理 | 能正确设置 755/644/600，能排查权限问题 | 搭建 Samba 共享 |
| 用户管理 | 能创建用户、配置 sudo、设置 SSH 密钥 | 用户管理练习 |
| 进程管理 | 能用 ps/top/kill 管理进程，理解信号 | 运行后台服务并管理 |
| systemd | 能编写简单的 systemd 单元文件 | 编写 nginx 自定义单元 |
| Shell 脚本 | 能独立编写 50-100 行的实用脚本 | 完成 Day 25-27 实战 |
| 日志分析 | 能用 grep/awk/sed 分析日志 | 分析真实 access.log |

### 扩展学习资源

- 📖 [Linux Performance](http://www.brendangregg.com/linuxperf.html) - Brendan Gregg
- 📖 [GNU Coreutils 完整文档](https://www.gnu.org/software/coreutils/manual/)
- 🎥 [Linux Journey](https://linuxjourney.com/) - 免费学习路径
- 🎥 [Learn Linux TV](https://www.learnlinux.tv/) - YouTube 视频教程
- 🔧 [ShellCheck](https://www.shellcheck.net/) - Shell 脚本静态分析工具
- 🔧 [explainshell.com](https://explainshell.com/) - 命令行参数解释

### 第二阶段预告

下一阶段将学习 **计算机网络**，包括：
- OSI 七层模型
- TCP/UDP 协议详解
- IP 地址与子网划分
- DNS 协议
- HTTP/HTTPS 协议
- tcpdump 抓包分析
- 防火墙 iptables/nftables

---

**恭喜你完成第一阶段！坚持学习，SRE 之路上你已迈出坚实的第一步。** 🚀
"""

def gen_process_content(day: int) -> str:
    return """## 📖 详细知识点

### 1. 进程基础

#### 1.1 什么是进程？

**进程 (Process)** 是操作系统中正在运行的程序的实例。每个进程都有唯一的 **PID (Process ID)**。

| 概念 | 说明 |
|------|------|
| PID | 进程 ID，每个进程唯一 |
| PPID | 父进程 ID |
| UID/GID | 进程所有者的用户 ID / 组 ID |
| 状态 | 运行、睡眠、僵尸等 |

```bash
# 查看当前 bash 进程
echo $$

# 查看进程 PID
ps -ef | head -5
ps aux | head -10
```

#### 1.2 进程与程序的区别

```
程序：磁盘上的可执行文件（静态）
进程：程序在内存中运行时的实例（动态）
```

一个程序可以对应多个进程（例如：打开多个终端窗口，都是 bash 进程）。

#### 1.3 进程状态详解

| 状态 | 符号 | 含义 |
|------|------|------|
| Running | R | 正在运行或等待 CPU |
| Sleeping | S | 可中断的睡眠（等待事件） |
| Uninterruptible | D | 不可中断的睡眠（通常等待 I/O） |
| Stopped | T | 被暂停（Ctrl+Z） |
| Zombie | Z | 僵尸进程（已结束但未被回收） |

**实战案例**：
```bash
# 挂起当前进程（Ctrl+Z）
sleep 100 &
# 按 Ctrl+Z

# 查看状态
ps aux | grep sleep

# 查看 T 状态的进程
ps aux | awk '$8 ~ /T/'

# 恢复到前台
fg
```

---

### 2. 进程查看命令

#### 2.1 ps - 静态进程快照

```bash
# BSD 风格（最常用）
ps aux              # 显示所有进程（详细）
ps aux --sort=-%cpu # 按 CPU 使用率降序
ps aux --sort=-%mem # 按内存使用率降序

# Linux 风格
ps -ef              # 标准格式
ps -eLf             # 显示线程

# 查找特定进程
ps aux | grep nginx
ps -ef | grep "[n]ginx"

# 查看进程树
ps -ef --forest | head -30
```

**ps aux 输出详解**：
```
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root      1234  0.0   0.1  12345  5678 ?       Ss   09:00   0:00 /usr/sbin/sshd -D
```
- **VSZ**: 虚拟内存大小 (KB)
- **RSS**: 实际物理内存大小 (KB)
- **STAT**: 进程状态（R/S/D/T/Z）

#### 2.2 top / htop - 动态监控

```bash
# top 基本操作
top                  # 启动 top
P                    # 按 CPU 排序（shift+p）
M                    # 按内存排序（shift+m）
k                    # 杀掉进程（输入 PID）
r                    # 调整优先级 (renice)
1                    # 显示每个 CPU 核心
h                    # 帮助
q                    # 退出

# top 高级用法
top -d 1             # 每秒刷新（默认 3 秒）
top -p 1234          # 只监控指定 PID
top -u www-data      # 只显示指定用户的进程
top -b -n 5 > /tmp/top.log  # 批量输出

# top 输出字段
# PID: 进程 ID
# USER: 用户
# PR: 优先级
# NI: nice 值
# VIRT: 虚拟内存
# RES: 实际物理内存
# SHR: 共享内存
# S: 状态
```

**htop（更友好的 top）**：
```bash
# 安装
sudo apt install -y htop

# htop 优势
# - 彩色显示
# - 鼠标操作
# - 树形视图（F5）
# - 直接杀掉进程（F9）
# - 搜索进程（F3）

htop                   # 启动
F5                     # 树形视图
F3                     # 搜索
F9                     # 终止进程
```

#### 2.3 pstree - 进程树

```bash
# 显示进程树
pstree

# 显示特定用户的进程树
pstree -u www-data

# 显示完整 PID
pstree -p

# 简洁格式
pstree -pc
```

---

### 3. 进程控制

#### 3.1 kill - 发送信号

```bash
# 基本语法
kill [信号] PID

# 常用信号
kill -l              # 列出所有信号
kill -SIGTERM 1234   # 优雅终止（推荐，首先使用）
kill -SIGKILL 1234   # 强制杀死（最后手段）
kill -SIGSTOP 1234   # 暂停进程（Ctrl+Z）
kill -SIGCONT 1234   # 继续运行
kill -SIGHUP 1234    # 挂起（常用于重载配置）
```

**信号详解**：

| 信号 | 编号 | 含义 | 用途 |
|------|------|------|------|
| SIGTERM | 15 | 优雅终止 | 推荐首选，会清理资源 |
| SIGKILL | 9 | 强制杀死 | 最后手段，无法拦截 |
| SIGHUP | 1 | 挂起 | 常用于重载配置 |
| SIGINT | 2 | 中断 | Ctrl+C |
| SIGSTOP | 19 | 暂停 | Ctrl+Z |
| SIGCONT | 18 | 继续 | 恢复暂停的进程 |

#### 3.2 killall / pkill

```bash
# killall - 按名字杀死进程
killall nginx           # 杀死所有 nginx 进程
killall -9 nginx        # 强制杀死
killall -u www-data nginx  # 杀死 www-data 用户的 nginx

# pkill - 按模式杀死进程
pkill nginx             # 杀死匹配 nginx 的进程
pkill -f "python scan"  # 杀死命令行含 "python scan" 的进程
pkill -u www-data       # 杀死 www-data 用户的所有进程（危险！）
```

**实战案例**：
```bash
# 场景：Nginx 配置修改后重载
sudo nginx -t              # 测试配置语法
sudo kill -HUP $(cat /var/run/nginx.pid)  # 重载配置（不中断连接）
# 或
sudo systemctl reload nginx

# 场景：杀死僵死的 Python 进程
pkill -f "python script.py"
ps aux | grep python      # 确认

# 场景：重启卡死的服务
killall -9 -w myservice   # -w 等待进程退出
```

#### 3.3 nice 和 renice - 调整优先级

```bash
# nice - 启动时设置优先级（-20 到 19，越低优先级越高）
nice -n 10 ./backup.sh              # 低优先级运行
nice -n -5 ./priority_task.sh      # 高优先级（需 root）

# renice - 调整运行中进程的优先级
renice 10 -p 12345                  # 将 PID 12345 设为 nice=10
renice -n 5 -u www-data             # 调整 www-data 用户所有进程
renice +5 $(pgrep -f "python")      # 批量调整

# 查看 nice 值
ps -eo pid,ni,cmd | grep nginx
```

---

### 4. 后台进程与 nohup

#### 4.1 后台运行

```bash
# 后台运行
./long_task.sh &              # 直接后台运行
./long_task.sh &>/dev/null & # 丢弃输出

# nohup - 防止 SIGHUP 信号
nohup ./script.sh &           # 关闭终端后继续运行
nohup ./script.sh > output.log 2>&1 &

# screen - 真正的终端会话（推荐）
screen -S mytask              # 创建名为 mytask 的会话
# 在 screen 中运行任务
# 按 Ctrl+A, D 解绑（detach）
screen -r mytask              # 重新连接
screen -ls                    # 列出所有会话
screen -X -S mytask quit      # 删除会话

# tmux（更现代的替代）
tmux new -s mytask
# Ctrl+b, D 解绑
tmux attach -t mytask
tmux ls
```

#### 4.2 disown 和 wait

```bash
# disown - 将进程从当前会话脱离
./background_task.sh &
disown %1                    # 脱离最近的后台任务
disown -h %1                # 标记为不可被 SIGHUP 终止

# wait - 等待后台任务完成
./task1.sh &
./task2.sh &
wait                         # 等待所有后台任务完成
```

---

### 5. /proc 文件系统

Linux 把进程信息以文件形式暴露在 `/proc/` 目录下。

```bash
# 查看进程 PID 的详细信息
ls /proc/1234/

# 常用文件
cat /proc/1234/cmdline       # 命令行（含参数，NULL 分隔）
cat /proc/1234/environ       # 环境变量
cat /proc/1234/status        # 进程状态（人读）
cat /proc/1234/maps          # 内存映射
cat /proc/1234/fd/           # 打开的文件描述符
lsof -p 1234                  # 同上，更易读

# 查看系统内存
cat /proc/meminfo
cat /proc/cpuinfo

# 查看进程打开的文件
ls -la /proc/1234/fd/
lsof -p 1234

# 查看进程的网络连接
cat /proc/1234/net/tcp
# 更推荐
ss -tp | grep 1234
```

---

### 6. 实战案例

#### 案例 1：排查高 CPU 占用进程

```bash
# 1. 查看整体 CPU 使用
top
# 按 P 排序查看最高 CPU

# 2. 查看 CPU 密集型进程
ps aux --sort=-%cpu | head -10

# 3. 查看进程的 CPU 使用历史
pidstat -p 1234 1 5          # 每秒采样 5 次

# 4. 查看进程的系统调用
strace -p 1234 -c             # 统计系统调用
strace -p 1234 -f             # 跟踪 fork/vfork

# 5. 如果是 Python/Node 等解释型语言
python -m cProfile -s cumtime script.py
```

#### 案例 2：排查内存泄漏

```bash
# 1. 查看内存使用
free -h
ps aux --sort=-%mem | head -10

# 2. 监控内存变化
vmstat 1 10                   # 每秒采样 10 次
# si/so: swap in/out

# 3. 查看进程内存详情
pmap -x 1234                  # 详细内存映射
cat /proc/1234/smaps

# 4. 持续监控
while true; do
    ps -o pid,vsz,rss,pmem,comm -p 1234
    sleep 5
done
```

#### 案例 3：安全排查 - 查找隐藏进程

```bash
# 查找异常进程
ps aux | awk '$2 > 10000 {print}'  # 异常高的 PID

# 查找可疑的未授权进程
ps -eo pid,user,comm,wchan | grep -v root

# 检查被隐藏的进程（rookit 风险）
cat /proc/[1-9]*/comm         # 检查 1-9 号进程（init 不应该有子进程）
diff <(ls /proc | grep '^[0-9]*$') <(ps -eo pid --no-headers)
```

---

### 7. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 进程变僵尸 (Z) | 父进程未调用 wait() | 杀死父进程，init 会回收 |
| 进程无法杀死 | 处于 D 状态等待 I/O | 等待 I/O 完成，或重启 |
| 内存持续增长 | 内存泄漏 | 重启进程，定位泄漏代码 |
| CPU 100% | 死循环或高负载 | top 定位，kill 或优化 |
| 进程消失 | OOM Killer 或信号 | `dmesg | grep -i kill` |
| SSH 断开后进程死 | 未用 nohup/screen | 重启并用 screen 运行 |
"""
    return r

def gen_systemd_content(day: int) -> str:
    return """## 📖 详细知识点

### 1. systemd 概述

#### 1.1 为什么需要 systemd？

传统的 SysV init（/etc/init.d/）采用顺序启动，串行执行，速度慢。systemd 的优势：

| 特性 | 说明 |
|------|------|
| 并行启动 | 充分利用多核，加速启动 |
| 按需激活 | 服务不用时不占用资源 |
| 事务管理 | 保证服务依赖关系的一致性 |
| 日志管理 | 内置 journald 日志系统 |
| 单元文件 | 统一的配置文件格式 |

#### 1.2 核心概念

```
systemd
├── Unit（单元） - 服务、挂载、设备、socket 等
├── Target（目标） - 一组单元的组合（类似运行级别）
├── Service（服务） - 后台进程
├── Socket（套接字） - 通信端点
├── Mount（挂载） - 文件系统挂载点
└── Timer（定时器） - 替代 cron 的定时任务
```

#### 1.3 systemd 架构

```bash
systemctl          # 管理单元
journalctl         # 查看日志
systemd-analyze    # 分析启动性能
timedatectl        # 时间和时区
localectl          # 本地化设置
hostnamectl        # 主机名
loginctl           # 用户会话管理
```

---

### 2. systemctl 核心命令

#### 2.1 服务管理

```bash
# 启动/停止/重启
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx        # 重启（先停后启）
sudo systemctl reload nginx         # 重载配置（不中断连接）
sudo systemctl try-restart nginx    # 支持则重载，否则跳过

# 启用/禁用（开机自启）
sudo systemctl enable nginx         # 开机自启
sudo systemctl disable nginx        # 关闭开机自启
sudo systemctl is-enabled nginx    # 查看是否启用

# 查看状态
sudo systemctl status nginx
sudo systemctl status nginx --no-pager  # 不分页

# 查看所有服务
systemctl list-units --type=service --state=running

# 查看失败的服务
systemctl --failed --type=service
```

#### 2.2 systemctl 输出解读

```
● nginx.service - A high performance web server
   Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
   Active: active (running) since Wed 2026-04-15 09:00:00 CST; 1 day 1min ago
 Main PID: 1234 (nginx)
   CGroup: /system.slice/nginx.service
           ├─1234 nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
           └─1235 nginx: worker process
```

- **Loaded**: 配置文件路径，`enabled` 表示开机自启
- **Active**: 运行状态和时间
- **Main PID**: 主进程 PID
- **CGroup**: 控制组，显示所有相关进程

---

### 3. systemd 单元文件

#### 3.1 服务单元文件结构

```bash
# 路径（优先级从高到低）
/etc/systemd/system/    # 最高（用户自定义）
/run/systemd/system/    # 运行时
/lib/systemd/system/    # 包提供的默认（Ubuntu）
~/.config/systemd/user/  # 用户级服务
```

#### 3.2 最小服务单元示例

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application Service
Documentation=https://myapp.com/docs
After=network.target    # 网络就绪后启动
Wants=network-online.target

[Service]
Type=simple             # 简单进程（默认）
ExecStart=/opt/myapp/myapp --config /etc/myapp/config.yaml
ExecStop=/bin/kill -SIGTERM $MAINPID
ExecReload=/bin/kill -SIGHUP $MAINPID
Restart=on-failure       # 失败时重启
RestartSec=5             # 重启前等待 5 秒
StandardOutput=journal   # 输出到 journal
StandardError=journal
User=myappuser           # 运行用户
Group=myappgroup
Environment=NODE_ENV=production
EnvironmentFile=/etc/myapp/env

# 安全加固
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/myapp /tmp
PrivateTmp=true
```

#### 3.3 Type 类型详解

| Type | 说明 | 适用场景 |
|------|------|---------|
| simple | 主进程即服务（默认） | 大多数服务 |
| exec | 同 simple，但 exec 后才认为启动 | 启动脚本 |
| forking | fork() 后父进程退出 | 传统守护进程 |
| oneshot | 一次性的任务，执行完就停止 | 初始化脚本 |
| dbus | 依赖 D-Bus 总线名称 | 需要 D-Bus 的服务 |
| notify | 启动完成发送 sd_notify() | systemd 通知机制 |
| idle | 等待所有任务完成才运行 | 辅助服务 |

#### 3.4 常用指令

```ini
[Unit]
Description=描述
Documentation=文档 URL
After=network.target mysql.service    # 依赖关系（之后启动）
Requires=mysql.service              # 强依赖（都启动才算成功）
Wants=redis.service                 # 弱依赖（失败不影响）
Conflicts=shutdown.target           # 与某服务互斥

[Service]
ExecStartPre=/usr/bin/myapp-check   # 启动前检查
ExecStart=/usr/bin/myapp
ExecStopPost=/usr/bin/cleanup       # 停止后清理
TimeoutStartSec=30                   # 启动超时
TimeoutStopSec=60                    # 停止超时

[Install]
WantedBy=multi-user.target          # 哪个 target 下启用
```

---

### 4. 实战案例

#### 案例 1：编写 Nginx systemd 单元

```ini
# /etc/systemd/system/nginx-custom.service
[Unit]
Description=Nginx Web Server (Custom)
Documentation=https://nginx.org/en/docs/
After=network.target

[Service]
Type=forking
PIDFile=/run/nginx.pid
ExecStart=/usr/sbin/nginx
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 使用
sudo systemctl daemon-reload          # 重载配置（必须）
sudo systemctl enable nginx-custom
sudo systemctl start nginx-custom
```

#### 案例 2：Python Flask 应用服务

```ini
# /etc/systemd/system/flask-app.service
[Unit]
Description=Flask API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/flaskapp
Environment="FLASK_ENV=production"
Environment="PATH=/opt/flaskapp/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/flaskapp/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# 安全
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/flaskapp/logs
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### 案例 3：使用 systemd_timer 替代 cron

```ini
# /etc/systemd/system/daily-backup.timer
[Unit]
Description=Daily Backup Timer

[Timer]
OnCalendar=daily
AccuracySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/daily-backup.service
[Unit]
Description=Daily Backup Service
[Service]
Type=oneshot
ExecStart=/opt/scripts/backup.sh
StandardOutput=journal
StandardError=journal
```

```bash
# 启用定时器
sudo systemctl daemon-reload
sudo systemctl enable --now daily-backup.timer
systemctl list-timers --all
```

---

### 5. journalctl - 日志管理

#### 5.1 基本用法

```bash
# 查看所有日志（默认保留最近启动的）
journalctl

# 查看实时新日志
journalctl -f

# 查看特定服务的日志
journalctl -u nginx
journalctl -u nginx -u mysql --since "1 hour ago"

# 查看最近 50 行
journalctl -n 50 --no-pager

# 查看今天的日志
journalctl --since today

# 查看指定时间范围
journalctl --since "2026-04-15 09:00:00" --until "2026-04-15 10:00:00"

# 查看错误以上的日志
journalctl -p err -b                 # -b: 本次启动

# 查看磁盘使用
journalctl --disk-usage
```

#### 5.2 高级用法

```bash
# 查看启动过程日志
journalctl -b -1                     # 上次启动
journalctl -b -2                     # 上上次启动
journalctl --list-boots              # 列出所有启动记录

# 查看特定 PID 的日志
journalctl _PID=1234

# 查看特定用户的日志
journalctl _UID=1000

# 追踪特定进程（实时）
journalctl _PID=1234 -f

# 清理旧日志
journalctl --vacuum-size=500M        # 保留最近 500M
journalctl --vacuum-time=30days      # 保留 30 天
```

---

### 6. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `Failed to start` | 服务启动失败 | `journalctl -u <service> -n 50` |
| `Refused to start` | 配置错误 | `systemctl edit` 或 `systemd-analyze verify` |
| 开机后服务未启动 | 未 enable | `systemctl enable <service>` |
| 服务启动太慢 | 依赖过多或超时 | 检查 `After`/`Wants`，调整 TimeoutStartSec |
| 日志太大 | 没有轮转 | `journalctl --vacuum-size` |
| 进程变成 D 状态 | 等待 I/O | `iotop`/`iostat` 排查 I/O |
| 重启后服务状态丢失 | `WantedBy` 错误 | 检查 target 是否激活 `systemctl get-default` |
"""
    return r

def gen_monitoring_content(day: int) -> str:
    return """## 📖 详细知识点

### 1. 系统监控概述

作为 SRE，监控是核心技能之一。Linux 提供丰富的监控命令。

#### 1.1 监控层次

```
应用层  →  进程占用（CPU/内存/文件描述符）
系统层  →  CPU、内存、磁盘 I/O、网络
内核层  →  负载、上下文切换、 slab 分配器
硬件层  →  温度、功耗、硬件错误（mcelog）
```

#### 1.2 监控黄金指标

```
延迟（Latency）  → 用户请求响应时间
流量（Traffic）   → QPS、带宽
错误（Errors）    → 5xx 错误率
饱和度（Saturation）→ CPU/内存/磁盘使用率
```

---

### 2. uptime 和负载

#### 2.1 uptime

```bash
uptime
# 09:00:00 up 10 days,  3:22,  2 users,  load average: 0.52, 0.58, 0.59
```

**解读**：
- `09:00:00` - 当前时间
- `up 10 days` - 运行时长
- `2 users` - 当前登录用户数
- `load average: 0.52, 0.58, 0.59` - 1/5/15 分钟平均负载

**什么是负载？**
负载表示**等待 CPU 或 I/O 的进程平均数**：
- 0.52 = 平均 0.52 个进程在等待 CPU 或 I/O
- 单核 CPU 满载 = 负载 1.0
- 4 核 CPU 满载 = 负载 4.0

```bash
# 理想负载参考（单核）
负载 < 0.7    ✅ 良好
负载 0.7-1.0  ⚠️ 轻微压力
负载 1.0-2.0  🔴 压力较大
负载 > 2.0    🚨 严重过载（4 核以下）
```

#### 2.2 w 和 who

```bash
# 查看谁登录了系统
who
# root     pts/0    2026-04-15 09:00 (192.168.1.100)
# www-data pts/1    2026-04-15 09:05 (192.168.1.101)

# w - 更详细的用户信息
w
# 09:00:00 up 10 days,  3:22,  2 users,  load average: 0.52, 0.58, 0.59
# USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT
# root     pts/0    192.168.1.100    09:00    0.00s  0.00s  0.00s w
# www-data pts/1    192.168.1.101    09:05   10.00s  0.01s  0.01s bash
```

---

### 3. free - 内存监控

#### 3.1 free 输出详解

```bash
free -h
#               total        used        free      shared  buff/cache   available
# Mem:          7.7Gi       2.1Gi       1.2Gi       50Mi       4.4Gi       5.2Gi
# Swap:         2.0Gi       0.0Gi       2.0Gi
```

| 字段 | 含义 |
|------|------|
| total | 总物理内存 |
| used | 已使用 = total - free - buff/cache |
| free | 完全未使用的内存 |
| shared | 共享内存（tmpfs） |
| buff/cache | 缓冲区 + 页面缓存（可回收） |
| available | 可用内存（free + 可回收的 cache）**重要** |
| Swap | 虚拟内存（磁盘） |

**关键理解**：
- `available` 是判断内存是否够用的标准，而非 `free`
- Linux 会尽可能用内存做缓存（buff/cache），提升 I/O 性能
- 当 `available` 接近 0 时，系统会开始 OOM Killer

#### 3.2 内存监控技巧

```bash
# 持续监控（每秒刷新）
watch -n 1 free -h

# 查看内存详情
cat /proc/meminfo

# 查看进程的内存使用
ps aux --sort=-%mem | head -10

# 查看 OOM Killer 日志
dmesg | grep -i "out of memory"
dmesg | grep -i "killed process"
```

#### 3.3 内存泄漏排查

```bash
# 1. 查看整体内存趋势（多次 free 输出对比）
free -h >> /tmp/memory.log
sleep 60
free -h >> /tmp/memory.log

# 2. 查看进程内存使用变化
ps -o pid,vsz,rss,pmem,comm -p <PID>

# 3. 使用 smem 报告（更详细）
sudo apt install smem
smem -r -k | head -10
smem -u | head -10

# 4. 使用 valgrind 排查（应用层）
valgrind --tool=memcheck ./myapp
```

---

### 4. df 和 du - 磁盘监控

#### 4.1 df - 文件系统使用

```bash
df -h                        # 人类可读格式
df -hT                       # 显示文件系统类型
df -h /home                  # 查看特定挂载点
df -i                       # 显示 inode 使用情况
```

**解读**：
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       100G   45G   55G  45% /
tmpfs           2.0G   10M  2.0G   1% /dev/shm
/dev/sdb1       500G  200G  300G  40% /data
```

**Use% 告警阈值**：
- < 80%  ✅ 正常
- 80-90% ⚠️ 关注
- > 90%  🔴 紧急，需要清理或扩容

#### 4.2 du - 目录/文件大小

```bash
# 当前目录总大小
du -sh .

# 各子目录大小（降序）
du -sh /* | sort -rh | head -10

# 特定目录
du -sh /var/log

# 深度限制（只显示第一层）
du -h --max-depth=1 /home

# 找最大文件
find / -type f -exec du -h {} + 2>/dev/null | sort -rh | head -10

# 排除特定目录
du -sh --exclude=proc --exclude=sys /*
```

#### 4.3 磁盘 I/O 监控

```bash
# iostat（需安装 sysstat）
sudo apt install sysstat
iostat -x 1 5               # 每秒采样 5 次（扩展格式）

# iotop（进程级 I/O）
sudo apt install iotop
sudo iotop                   # 实时 I/O 监控
sudo iotop -o               # 只显示有 I/O 的进程

# pidstat
pidstat -d 1 5               # 进程 I/O 统计
pidstat -r 1 5               # 进程内存统计
```

---

### 5. vmstat 和 sar

#### 5.1 vmstat - 虚拟内存统计

```bash
vmstat 1 5                   # 每秒采样 5 次
# procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
#  r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
#  1  0      0 1234567 123456 456789    0    0     0     0   100   50  5  2 90  3  0
```

**字段说明**：

| 字段 | 含义 |
|------|------|
| r | 运行中的进程数（等待 CPU） |
| b | 阻塞的进程数（等待 I/O） |
| swpd/si/so | Swap 使用和交换速度 |
| bi/bo | 块设备读/写速度 (KB/s) |
| in | 中断数/秒 |
| cs | 上下文切换/秒 |
| us/sy/id/wa | CPU 时间：用户/系统/空闲/等待 I/O |

**快速诊断**：
```
r 很多 + id 很低  → CPU 瓶颈
b 很多 + wa 很高  → I/O 瓶颈
si/so 非零        → 内存不足，使用 Swap
```

#### 5.2 sar - 系统活动报告

```bash
# 安装并启用
sudo apt install sysstat
sudo systemctl enable sysstat
sudo systemctl start sysstat

# CPU 使用率
sar -u 1 3

# 内存使用
sar -r 1 3

# I/O 速率
sar -b 1 3

# 网络流量
sar -n DEV 1 3

# 完整历史数据（/var/log/sa/）
sar -u -f /var/log/sa/sa15     # 15 号的历史数据
```

---

### 6. 综合监控脚本

```bash
#!/bin/bash
# system_monitor.sh - 综合系统监控脚本

echo "======================================"
echo "系统监控报告 $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================"
echo ""

# 1. 系统基本信息
echo "【系统信息】"
uname -a
echo ""

# 2. 运行时长和负载
echo "【运行时间 & 负载】"
uptime
echo ""

# 3. CPU 使用
echo "【CPU 使用】"
top -bn1 | grep "Cpu(s)" || mpstat 1 1 | tail -1
echo ""

# 4. 内存
echo "【内存使用】"
free -h
echo ""

# 5. 磁盘
echo "【磁盘使用 (Use% > 80%)】"
df -hT | awk '$6+0 > 80 {print}'
echo ""

# 6. 网络连接状态
echo "【网络连接统计】"
ss -s || netstat -s | head -10
echo ""

# 7. Top 5 CPU 进程
echo "【Top 5 CPU 进程】"
ps aux --sort=-%cpu | head -6
echo ""

# 8. Top 5 内存进程
echo "【Top 5 内存进程】"
ps aux --sort=-%mem | head -6
echo ""

# 9. 服务状态
echo "【关键服务状态】"
for svc in nginx mysql sshd docker; do
    if systemctl is-active --quiet $svc 2>/dev/null; then
        echo "  ✅ $svc: running"
    else
        echo "  ❌ $svc: NOT running"
    fi
done
echo ""

# 10. 最近错误日志
echo "【最近系统错误】"
journalctl -p err -n 5 --no-pager 2>/dev/null || \
    tail -5 /var/log/syslog | grep -i error
echo ""

echo "======================================"
echo "监控报告生成完成"
echo "======================================"
```

---

### 7. 告警阈值参考

| 指标 | 警告阈值 | 紧急阈值 | 处理方法 |
|------|---------|---------|---------|
| CPU 使用率 | > 80% | > 95% | 扩容/优化 |
| 内存使用率 | > 80% | > 95% | OOM 前杀进程 |
| 磁盘使用率 | > 80% | > 90% | 清理或扩容 |
| 磁盘 inode | > 80% | > 90% | 删除小文件 |
| Swap 使用率 | > 50% | > 80% | 增加内存 |
| 负载 | > CPU核数 | > 2x 核数 | 排查 CPU 密集 |
| 网络延迟 | > 100ms | > 500ms | 检查网络 |
| 磁盘 I/O wait | > 20% | > 50% | 优化 I/O |
"""
    return r

def gen_disk_content(day: int) -> str:
    return """## 📖 详细知识点

### 1. 磁盘管理基础

#### 1.1 磁盘结构

```
磁盘 (Physical Disk)
├── 磁头 (Head)
├── 磁道 (Track)
├── 扇区 (Sector) - 通常 512B 或 4KB
└── 柱面 (Cylinder)

分区 (Partition)
├── 主分区 (Primary) - 最多 4 个
├── 扩展分区 (Extended) - 最多 1 个
└── 逻辑分区 (Logical) - 在扩展分区内

MBR vs GPT
├── MBR: 2TB 最大磁盘，4 个主分区
└── GPT: 9.4ZB 最大磁盘，无主分区限制，UEFI 启动
```

#### 1.2 Linux 存储设备命名

```bash
# IDE/PATA 硬盘
/dev/hda, /dev/hdb

# SCSI/SATA/USB 硬盘
/dev/sda, /dev/sdb, /dev/sdc

# NVMe 固态硬盘
/dev/nvme0n1, /dev/nvme0n1p1

# Virtual Block Device（虚拟机）
/dev/vda, /dev/vdb (VirtIO)
```

**分区命名**：
```
/dev/sda          # 第一块硬盘
/dev/sda1         # 第一个分区
/dev/sda2         # 第二个分区
/dev/nvme0n1p1    # NVMe 设备第一个分区
```

---

### 2. fdisk 和 parted - 分区管理

#### 2.1 fdisk（MBR 分区）

```bash
# 查看分区表
sudo fdisk -l /dev/sda

# 进入交互模式
sudo fdisk /dev/sdb
```

**fdisk 交互命令**：
```
m - 帮助
p - 打印分区表
n - 新建分区
d - 删除分区
t - 改变分区类型
w - 保存退出
q - 不保存退出
```

**实战：创建新分区**：
```bash
# 1. 创建 100GB 分区
sudo fdisk /dev/sdb
# 输入：n, p, 回车, 回车, +100G, w

# 2. 查看结果
sudo fdisk -l /dev/sdb

# 3. 格式化
sudo mkfs.ext4 /dev/sdb1

# 4. 挂载
sudo mkdir /data
sudo mount /dev/sdb1 /data

# 5. 开机自动挂载
echo '/dev/sdb1 /data ext4 defaults 0 2' | sudo tee -a /etc/fstab

# 6. 验证
df -h /data
```

#### 2.2 parted（GPT 分区）

```bash
# 交互模式
sudo parted /dev/sdb

# 命令行模式（脚本化）
sudo parted /dev/sdb mklabel gpt
sudo parted /dev/sdb mkpart primary ext4 0% 100%
sudo parted /dev/sdb print
```

**parted vs fdisk**：
| 特性 | fdisk | parted |
|------|-------|--------|
| MBR | ✅ | ✅ |
| GPT | ❌ | ✅ |
| 2TB+ 磁盘 | ❌ | ✅ |
| 脚本化 | 较难 | 容易 |

---

### 3. mkfs - 文件系统创建

#### 3.1 常见文件系统

| 文件系统 | 特点 | 适用场景 |
|---------|------|---------|
| ext4 | Linux 最常用，稳定 | 通用 |
| xfs | 大文件，高性能 | 日志、大文件存储 |
| btrfs | 快照、压缩 | 高级功能需求 |
| vfat | 跨平台兼容 | U 盘（兼容性） |
| ntfs | Windows 兼容 | 读取 Windows 分区 |

#### 3.2 格式化操作

```bash
# ext4（最常用）
sudo mkfs.ext4 /dev/sdb1
sudo mkfs.ext4 -L mydata -b 4096 /dev/sdb1   # 带卷标和块大小

# xfs
sudo mkfs.xfs /dev/sdb1

# btrfs（带高级特性）
sudo mkfs.btrfs /dev/sdb1

# 快速格式化（不擦除数据，仅重建元数据）
sudo mkfs.ext4 -E lazy_itable_init=1 /dev/sdb1
```

#### 3.3 文件系统检查

```bash
# ext4 文件系统检查（需先卸载）
sudo fsck.ext4 /dev/sdb1
sudo fsck.ext4 -f /dev/sdb1        # 强制检查
sudo e2fsck -p /dev/sdb1          # 自动修复

# xfs 文件系统检查
sudo xfs_repair /dev/sdb1

# 查看文件系统详情
sudo tune2fs -l /dev/sdb1          # ext4 详细信息
sudo dumpe2fs /dev/sdb1 | head -30
```

---

### 4. mount - 挂载管理

#### 4.1 基本挂载

```bash
# 挂载
sudo mount /dev/sdb1 /data

# 卸载
sudo umount /data
sudo umount -l /data               # 懒卸载（强制）
sudo umount -f /data               # 强制卸载（远程文件系统）

# 重新挂载（修改选项）
sudo mount -o remount,rw /

# 查看所有挂载
mount
df -h
```

#### 4.2 /etc/fstab 配置

```bash
# 格式：<device> <mount_point> <type> <options> <dump> <pass>
# 示例：
/dev/sdb1       /data           ext4    defaults        0       2
UUID=xxx         /backup         xfs     defaults        0       2
tmpfs           /tmp            tmpfs   defaults,noexec,nodev,nosuid,size=2G  0  0
192.168.1.100:/nfs/share /nfs      nfs     defaults,_netdev  0  0
```

**字段说明**：
| 字段 | 说明 |
|------|------|
| device | 设备名、UUID、LABEL |
| mount_point | 挂载点 |
| type | 文件系统类型 |
| options | 挂载选项 |
| dump | 是否被 dump 备份（0/1） |
| pass | fsck 检查顺序（0=不检查，1=根，2=其他） |

**常用挂载选项**：
```
defaults  - 默认选项（rw, suid, dev, exec, auto）
ro        - 只读
rw        - 读写
noexec    - 禁止执行程序
nodev     - 不解释设备文件
nosuid    - 不执行 SUID
noatime   - 不更新访问时间（提升性能）
nodiratime - 不更新目录访问时间
```

#### 4.3 获取设备 UUID

```bash
# blkid（推荐）
sudo blkid
sudo blkid /dev/sdb1

# lsblk
lsblk -f

# /dev/disk/
ls -la /dev/disk/by-uuid/
```

**fstab 使用 UUID（更可靠）**：
```bash
# 获取 UUID
UUID=$(sudo blkid -o value -s UUID /dev/sdb1)

# 写入 fstab
echo "UUID=$UUID /data ext4 defaults 0 2" | sudo tee -a /etc/fstab

# 验证
sudo mount -a
```

---

### 5. 实战案例

#### 案例 1：新增硬盘并创建 LVM

```bash
# 1. 创建物理卷
sudo pvcreate /dev/sdb

# 2. 创建卷组
sudo vgcreate vgdata /dev/sdb

# 3. 创建逻辑卷
sudo lvcreate -L 200G -n lvdata vgdata

# 4. 格式化
sudo mkfs.ext4 /dev/vgdata/lvdata

# 5. 挂载
sudo mkdir /data
sudo mount /dev/vgdata/lvdata /data

# 扩展逻辑卷（将来扩容）
sudo lvextend -L +100G /dev/vgdata/lvdata
sudo resize2fs /dev/vgdata/lvdata

# 查看
sudo pvs
sudo vgs
sudo lvs
```

#### 案例 2：NFS 网络挂载

```bash
# 安装客户端
sudo apt install -y nfs-common

# 临时挂载
sudo mount -t nfs 192.168.1.100:/shared /mnt/nfs

# 自动挂载（fstab）
# 编辑 /etc/fstab：
192.168.1.100:/shared /mnt/nfs nfs defaults,_netdev 0 0

# 验证
mount -a
df -h /mnt/nfs
```

#### 案例 3：tmpfs（内存文件系统）

```bash
# 创建 2GB tmpfs
sudo mkdir -p /tmp/large_space
sudo mount -t tmpfs -o size=2G tmpfs /tmp/large_space

# 写入 fstab 永久生效
tmpfs /tmp/large_space tmpfs size=2G,mode=1777 0 0

# 查看 tmpfs 使用
df -h | grep tmpfs
mount | grep tmpfs
```

---

### 6. 磁盘配额 (Quota)

```bash
# 安装
sudo apt install -y quota

# 启用配额（ext4）
sudo quotaoff -a
sudo quotacheck -cum /home
sudo quotaon /home

# 设置用户配额
sudo edquota -u username
# 编辑：
# Filesystem  blocks  soft  hard  inodes  soft  hard
# /dev/sda1    10000   15000 20000  100     200   300

# 查看配额
sudo quota -u username
sudo repquota /home

# 设置组配额
sudo edquota -g developers
```

---

### 7. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 磁盘空间足够但写入失败 | inode 耗尽 | `df -i` 检查；删除小文件 |
| 分区无法删除 | 分区忙 | `umount` 后重试 |
| mount 报 "already mounted" | 重复挂载 | `umount` 或 `mount --bind` |
| 文件系统损坏 | 非正常卸载 | `fsck` 修复（可能丢数据） |
| 扩容后 df 不显示新空间 | 未 resize2fs | `resize2fs /dev/sdb1` |
| NFS 挂载超时 | 网络问题 | 检查网络，添加 `_netdev` 选项 |
"""
    return r

def gen_log_mgmt_content(day: int) -> str:
    return """## 📖 详细知识点

### 1. Linux 日志系统概述

Linux 日志体系：

```
应用日志
├── rsyslogd     - 传统 syslog 服务
├── journald      - systemd 内置日志
└── 应用自身日志  - Nginx/MySQL 等

日志查看
├── journalctl    - systemd 日志
├── rsyslog       - 传统 /var/log
└── 专用工具      - logrotate, lnav, grep/awk
```

#### 1.1 /var/log 目录结构

```bash
ls /var/log/
# syslog         - 通用系统日志（Ubuntu/Debian）
# messages       - 通用系统日志（RHEL/CentOS）
# auth.log       - 认证日志（登录、sudo）
# daemon.log     - 守护进程日志
# kern.log       - 内核日志
# cron.log       - 定时任务日志
# nginx/
#     access.log - 访问日志
#     error.log - 错误日志
# mysql/
# apache2/ 或 httpd/
```

---

### 2. journalctl 实战

#### 2.1 基础查询

```bash
# 查看所有日志
journalctl

# 查看最新日志
journalctl -e                 # 跳到最后
journalctl -n 50              # 最近 50 行

# 实时跟踪
journalctl -f

# 按服务
journalctl -u nginx
journalctl -u nginx -u mysql   # 多个服务

# 按时间
journalctl --since "1 hour ago"
journalctl --since "2026-04-15 09:00"
journalctl --since yesterday
journalctl --until "2026-04-15 10:00"

# 按优先级
journalctl -p err              # 错误
journalctl -p warning          # 警告
journalctl -p info             # 信息
journalctl -p debug            # 调试
journalctl -p err..crit        # 范围
```

#### 2.2 高级查询

```bash
# 按用户/进程
journalctl _UID=1000
journalctl _PID=1234
journalctl _COMM=nginx

# 按命令行匹配
journalctl /usr/sbin/nginx
journalctl /usr/bin/python3

# 查看启动日志
journalctl -b                  # 本次启动
journalctl -b -1              # 上次启动
journalctl --list-boots       # 列出所有启动

# 导出日志
journalctl --no-pager > system.log

# 日志大小管理
journalctl --disk-usage
journalctl --vacuum-size=500M
journalctl --vacuum-time=30days
```

---

### 3. rsyslog 配置

#### 3.1 rsyslog 基础

```bash
# 服务管理
sudo systemctl status rsyslog
sudo systemctl restart rsyslog

# 主配置文件
/etc/rsyslog.conf
/etc/rsyslog.d/*.conf
```

#### 3.2 rsyslog 规则

```bash
# /etc/rsyslog.d/50-default.conf 示例

# 认证日志（单独存放）
auth.*         /var/log/auth.log
authpriv.*     /var/log/auth.log

# 内核日志
kern.*         /var/log/kern.log

# 所有 info 级别以上（不含 mail/authpriv）
*.info;mail.none;authpriv.none  /var/log/syslog

# mail 日志
mail.*         -/var/log/mail.log
```

**规则格式**：
```
设施.优先级        动作
mail.info         /var/log/mail.log
kern.!info         /var/log/kern_debug.log
*.*               @192.168.1.100:514   # 远程日志
```

#### 3.3 远程日志（loganalyzer 架构）

```bash
# 客户端配置（/etc/rsyslog.conf）
*.* @@remote-server:514

# 服务端配置（接收端）
module(load="imtcp")
input(type="imtcp" port="514")
```

---

### 4. logrotate - 日志轮转

#### 4.1 配置

```bash
# 主配置
/etc/logrotate.conf           # 全局配置
/etc/logrotate.d/             # 各服务配置

# 查看 Nginx 配置
cat /etc/logrotate.d/nginx
```

**示例配置**：
```bash
/var/log/nginx/*.log {
    daily                 # 每天轮转
    missingok             # 丢失不报错
    rotate 14             # 保留 14 份
    compress              # 压缩旧日志
    delaycompress          # 延迟压缩（保留最近一个不压缩）
    notifempty            # 空日志不轮转
    create 0640 www-data adm  # 新日志权限
    sharedscripts         # 多个日志共用一次 postrotate
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

#### 4.2 手动执行和调试

```bash
# 手动轮转（测试配置）
sudo logrotate -f /etc/logrotate.d/nginx

# 查看轮转状态
cat /var/lib/logrotate/status

# 调试模式（不实际轮转）
sudo logrotate -d /etc/logrotate.d/nginx
```

---

### 5. 日志分析实战

#### 5.1 Nginx 日志分析

```bash
# access.log 格式（默认 combined）
# 192.168.1.1 - - [15/Apr/2026:10:00:00 +0800] "GET /index.html HTTP/1.1" 200 1234 "http://referer.com" "Mozilla/5.0"

# 统计总请求数
wc -l /var/log/nginx/access.log

# 统计各状态码
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# 统计 5xx 错误
awk '$9 >= 500 {count++} END {print "5xx count:", count}' /var/log/nginx/access.log

# Top 10 IP
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# Top 10 URL
awk '{print $7}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -10

# 按小时统计请求
awk '{print $4}' /var/log/nginx/access.log | cut -d: -f2 | sort | uniq -c

# 查找慢请求（响应时间，取决于日志格式）
awk '{if ($NF ~ /[0-9]+/) print $NF, $7}' /var/log/nginx/access.log | sort -rn | head -10
```

#### 5.2 认证日志分析

```bash
# 查看登录成功
grep "Accepted" /var/log/auth.log

# 查看登录失败（暴力破解检测）
grep "Failed password" /var/log/auth.log
grep "BREAK-IN" /var/log/auth.log

# 查看 sudo 使用
grep "sudo" /var/log/auth.log

# 统计登录次数
last -10                   # 最近登录
lastb                      # 失败登录
lastlog                     # 所有用户最后登录
```

#### 5.3 综合日志分析脚本

```bash
#!/bin/bash
# log_analysis.sh - 日志综合分析

LOG_DIR="/var/log"
REPORT="/tmp/log_report_$(date +%Y%m%d_%H%M%S).txt"

{
    echo "=== 系统日志分析报告 $(date) ==="
    echo ""

    # 系统概览
    echo "【系统运行时间】"
    uptime
    echo ""

    # 最近错误
    echo "【最近系统错误 (journalctl -p err)】"
    journalctl -p err -n 10 --no-pager 2>/dev/null || echo "journalctl 不可用"
    echo ""

    # 认证日志
    echo "【认证失败次数（最近 24h）】"
    if [ -f /var/log/auth.log ]; then
        grep "Failed password" /var/log/auth.log | grep -v "sudo" | wc -l
    fi
    echo ""

    # Nginx 日志（如果存在）
    if [ -f /var/log/nginx/access.log ]; then
        echo "【Nginx 请求统计】"
        echo "总请求: $(wc -l < /var/log/nginx/access.log)"
        echo "5xx 错误: $(awk '$9 >= 500 {c++} END {print c+0}' /var/log/nginx/access.log)"
        echo "4xx 错误: $(awk '$9 >= 400 && $9 < 500 {c++} END {print c+0}' /var/log/nginx/access.log)"
        echo "Top 3 IP: $(awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -3)"
        echo ""
    fi

    # 磁盘空间
    echo "【磁盘使用 (Use% > 80%)】"
    df -h | awk '$5+0 > 80 {print}'
    echo ""

    # 内存
    echo "【内存使用】"
    free -h
    echo ""

} > "$REPORT"

echo "报告已生成: $REPORT"
cat "$REPORT"
```

---

### 6. 实时监控告警

```bash
#!/bin/bash
# real_time_monitor.sh - 实时日志关键词告警

LOG_FILE=${1:-/var/log/syslog}
KEYWORDS="error|fatal|critical|failed|denied"
ALERT_EMAIL="sre@example.com"
STATE_FILE="/tmp/monitor.state"

LAST_LINE=$(cat $STATE_FILE 2>/dev/null || echo 0)

tail -n +$LAST_LINE "$LOG_FILE" 2>/dev/null | \\
    grep -iE "$KEYWORDS" | while read line; do
        echo "$(date): ALERT - $line"
        echo "$line" | mail -s "[ALERT] $HOSTNAME log alert" "$ALERT_EMAIL"
    done

# 更新读取位置
wc -l < "$LOG_FILE" > "$STATE_FILE"
```

---

### 7. 常见问题与解决方案

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 日志占用大量磁盘 | 无 logrotate 或轮转失效 | 检查 logrotate 配置和 cron |
| journald 日志消失 | 日志超过保留策略 | `journalctl --vacuum-time` |
| auth.log 过大 | 频繁 sudo 或 SSH 暴力破解 | 检查来源；fail2ban |
| 应用日志不写入 | rsyslog 分类错误 | 检查 rsyslog 配置 |
| 无法实时查看日志 | 权限问题 | `sudo journalctl -u <svc>` |
"""
    return r

# ── 主题 → 生成器映射 ──────────────────────────────────────────────────────

TOPIC_GENERATORS = {
    # Week 1
    "文本处理": "grep/sed/awk",
    "文本处理三剑客": "grep/sed/awk",
    "权限": "chmod/chown",
    "文件权限": "chmod/chown",
    "权限管理": "chmod/chown",
    "用户": "useradd/usermod",
    "用户与用户组": "useradd/usermod",
    "用户与用户组管理": "useradd/usermod",
    "第一周综合复习": "week1_review",
    "第一周综合复习与实战练习": "week1_review",
    # Week 2
    "进程管理基础": "process",
    "进程控制": "kill/killall",
    "systemd": "systemd",
    "systemd服务": "systemd",
    "服务管理": "systemd",
    "监控": "monitoring",
    "系统监控": "monitoring",
    "磁盘": "disk",
    "磁盘管理": "fdisk/mkfs",
    "日志": "journalctl",
    "日志管理": "journalctl",
    "第二周综合": "week2_review",
    "LAMP": "lamp",
    # Week 3-4
    "shell脚本": "shell_basic",
    "shell脚本基础": "shell_basic",
    "变量": "shell_basic",
    "shell": "shell_basic",
    "条件判断": "shell_if",
    "循环": "shell_loop",
    "for": "shell_loop",
    "while": "shell_loop",
    "函数": "shell_function",
    "case": "shell_case",
    "select": "shell_case",
    "数组": "shell_array",
    "expect": "shell_expect",
    "trap": "shell_trap",
    "调试": "shell_trap",
    "复习": "week1_review",
    "综合复习": "week1_review",
    "总结": "phase1_summary",
    "第一阶段总结": "phase1_summary",
    "测试": "phase1_summary",
}

def gen_content_for_topic(day: int, topic: str) -> str:
    """根据主题返回详细的学习内容"""
    topic_lower = topic.lower()

    # 精确匹配
    for key, gen_key in TOPIC_GENERATORS.items():
        if key.lower() in topic_lower or topic_lower.startswith(key.lower()):
            break
    else:
        gen_key = "generic"

    # Week 1 Review
    if "第一周综合复习" in topic:
        return gen_week1_review(day)

    # Week 2 Review
    if "第二周综合实战" in topic or "第二周综合复习" in topic:
        return gen_week2_review(day)

    # 第一阶段总结
    if "第一阶段总结" in topic or "第一阶段测试" in topic or "阶段总结" in topic:
        return gen_phase1_summary(day)

    # 具体内容生成器
    generators = {
        "grep/sed/awk": _gen_text_processing,
        "chmod/chown": _gen_permissions_short,
        "useradd/usermod": _gen_user_mgmt_short,
        "process": gen_process_content,
        "kill/killall": gen_process_content,
        "systemd": gen_systemd_content,
        "monitoring": gen_monitoring_content,
        "fdisk/mkfs": gen_disk_content,
        "journalctl": gen_log_mgmt_content,
        "shell_basic": _gen_shell_basic,
        "shell_if": _gen_shell_if,
        "shell_loop": _gen_shell_loop,
        "shell_function": _gen_shell_function,
        "shell_case": _gen_shell_case,
        "shell_array": _gen_shell_array,
        "shell_expect": _gen_shell_expect,
        "shell_trap": _gen_shell_trap,
        "generic": _gen_generic,
    }

    gen = generators.get(gen_key, generators["generic"])
    return gen(day, topic)


def _gen_generic(day: int, topic: str) -> str:
    return f"""## 📖 详细知识点

### 主题：{topic}

#### 核心概念

（本主题详细内容，请参考官方文档和推荐教程）

#### 常用命令

```bash
# 基础命令
command --help
man command
```

#### 实战练习

```bash
# 练习 1
```

#### 常见问题

| 问题 | 解决方案 |
|------|----------|
|  | |
"""


def _gen_text_processing(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. grep - 文本搜索神器

grep 是 Linux 中最常用的文本搜索工具，SRE 必备技能。

#### 1.1 基础语法

```bash
grep [选项] "搜索模式" [文件...]
```

#### 1.2 常用选项

| 选项 | 含义 | 示例 |
|------|------|------|
| `-i` | 忽略大小写 | `grep -i "error" log.txt` |
| `-n` | 显示行号 | `grep -n "Failed" auth.log` |
| `-c` | 只显示匹配行数 | `grep -c "404" access.log` |
| `-v` | 反向匹配（不包含） | `grep -v "GET /health" access.log` |
| `-r` | 递归搜索目录 | `grep -r "config" /etc/` |
| `-A N` | 显示匹配行后 N 行 | `grep -A 5 "ERROR" log.txt` |
| `-B N` | 显示匹配行前 N 行 | `grep -B 3 "ERROR" log.txt` |
| `-l` | 只显示文件名 | `grep -rl "password" /etc/` |
| `-w` | 整词匹配 | `grep -w "root" /etc/passwd` |
| `-E` | 扩展正则 | `grep -E "error|fatal|critical" log.txt` |
| `-o` | 只输出匹配部分 | `grep -oE "[0-9]+\\\\.[0-9]+\\\\.[0-9]+\\\\.[0-9]+" access.log` |

**实战案例 - 日志分析**：
```bash
# 查找所有 error 日志（不区分大小写）
grep -i "error" /var/log/syslog | tail -50

# 查找登录失败记录（安全监控）
grep "Failed password" /var/log/auth.log | grep "sshd"

# 统计 404 错误出现次数
grep -c " 404 " /var/log/nginx/access.log

# 查找错误前后 5 行（完整上下文）
grep -B 5 -A 5 "ERROR" /var/log/app.log

# 反向查找（排除健康检查）
grep -v "GET /health" /var/log/nginx/access.log | wc -l

# 提取 IP 地址
grep -oE "\\\\b[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}\\\\.[0-9]{1,3}\\\\b" /var/log/nginx/access.log

# 多条件匹配（扩展正则）
grep -E "error|fatal|critical|warning" /var/log/nginx/error.log
```

---

### 2. sed - 流编辑器

sed 是强大的流编辑器，用于对文本进行替换、删除、插入等操作。

#### 2.1 基础语法

```bash
sed [选项] '命令' [文件...]
sed -i '命令' [文件...]    # -i: 直接修改文件
```

#### 2.2 常用命令

| 命令 | 含义 | 示例 |
|------|------|------|
| `s/old/new/` | 替换第一处 | `sed 's/nginx/apache/' file` |
| `s/old/new/g` | 全部替换 | `sed 's/nginx/apache/g' file` |
| `s/old/new/2` | 只替换第二处 | `sed 's/nginx/apache/2' file` |
| `Nd` | 删除第 N 行 | `sed '5d' file` |
| `N,Md` | 删除 N 到 M 行 | `sed '1,10d' file` |
| `/pattern/d` | 删除匹配行 | `sed '/^#/d' file` |
| `p` | 打印行 | `sed -n '5p' file` |
| `i\\\\text` | 在行前插入 | `sed '1i\\\\Header' file` |
| `a\\\\text` | 在行后追加 | `sed '1a\\\\Footer' file` |

**实战案例 - 配置文件处理**：
```bash
# 替换配置文件中的端口（nginx 端口 80 -> 8080）
sed -i 's/listen 80;/listen 8080;/' /etc/nginx/nginx.conf

# 删除所有空行
sed -i '/^$/d' /etc/nginx/nginx.conf

# 在文件特定位置插入内容（第 10 行后）
sed -i '10a\\\\# Added by SRE automation' /etc/config.conf

# 备份并修改（安全的做法）
sed -i.backup 's/old/new/g' file.txt
# 原文件保存为 file.txt.backup

# 将所有 .txt 文件中的 "localhost" 替换为 "127.0.0.1"
find . -name "*.txt" | xargs sed -i 's/localhost/127.0.0.1/g'
```

---

### 3. awk - 强大的文本分析工具

awk 不仅仅是文本编辑工具，更是数据分析和报表生成的利器。

#### 3.1 基础语法

```bash
awk '模式 {动作}' [文件...]
awk -F: '{print $1}' /etc/passwd    # -F 指定分隔符
```

#### 3.2 内置变量

| 变量 | 含义 | 示例值 |
|------|------|--------|
| `$0` | 整行 | "root:x:0:0:root:/root:/bin/bash" |
| `$1, $2...` | 第 1, 2... 个字段 | $1="root", $2="x" |
| `NF` | 字段数量 | 7 |
| `NR` | 当前行号 | 1, 2, 3... |
| `FNR` | 当前文件的行号 | 1, 2, 3... |
| `FS` | 字段分隔符 | ":" |
| `OFS` | 输出字段分隔符 | " " |

**实战案例 - 日志分析**：
```bash
# 统计 Nginx 日志每小时的请求数
awk '{print $4}' /var/log/nginx/access.log \\
    | cut -d: -f1 | sort | uniq -c | sort -k1 -nr

# 提取 Nginx 日志中的状态码统计
awk '{print $9}' /var/log/nginx/access.log \\
    | sort | uniq -c | sort -rn

# 统计每个 IP 的访问次数（降序）
awk '{print $1}' /var/log/nginx/access.log \\
    | sort | uniq -c | sort -rn | head -20

# 查找 5xx 错误并显示详细信息
awk '$9 ~ /^[45][0-9][0-9]$/ {print $1, $4, $7, $9}' /var/log/nginx/access.log

# 统计 POST 请求的字节数
awk '$6 == "POST" {sum += $10} END {print sum}' /var/log/nginx/access.log
```

**Nginx 健康检查报告**：
```bash
awk '{
    if ($9 >= 200 && $9 < 300) success++
    else if ($9 >= 300 && $9 < 400) redirect++
    else if ($9 >= 400 && $9 < 500) client_error++
    else if ($9 >= 500) server_error++
    total++
}
END {
    print "=== Nginx 健康检查报告 ==="
    print "总请求数:", total
    print "成功 (2xx):", success, sprintf("(%.1f%%)", success/total*100)
    print "服务端错误 (5xx):", server_error, sprintf("(%.1f%%)", server_error/total*100)
}' /var/log/nginx/access.log
```

---

### 4. 正则表达式

#### 4.1 基础正则

| 符号 | 含义 | 示例 |
|------|------|------|
| `.` | 任意单个字符 | `a.c` 匹配 "abc", "aXc" |
| `^` | 行首 | `^error` 匹配行首的 error |
| `$` | 行尾 | `error$` 匹配行尾的 error |
| `*` | 0 个或多个 | `ab*c` 匹配 "ac", "abc", "abbc" |
| `+` | 1 个或多个 | `ab+c` 匹配 "abc", "abbc" (需 -E) |
| `?` | 0 个或 1 个 | `ab?c` 匹配 "ac", "abc" |
| `[abc]` | 字符集 | `[0-9]` 任意数字 |
| `[^abc]` | 反向字符集 | `[^0-9]` 非数字 |
| `{n}` | 重复 n 次 | `a{3}` 匹配 "aaa" |

**实战案例**：
```bash
# 匹配 IP 地址
grep -oE "[0-9]+\\\\.[0-9]+\\\\.[0-9]+\\\\.[0-9]+" /var/log/nginx/access.log

# 匹配日期格式 (2024-01-15)
grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" /var/log/nginx/access.log

# 匹配 HTTP 状态码
grep -oE " [45][0-9]{2} " /var/log/nginx/access.log

# 匹配邮箱地址
grep -oE "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}" /var/log/nginx/access.log
```

---

### 5. 三剑客组合技

**SRE 场景：分析 Nginx 访问日志，生成日报**：
```bash
#!/bin/bash
LOG_FILE="/var/log/nginx/access.log"

echo "=== Nginx 日报 $(date +%Y-%m-%d) ==="
echo "总请求数: $(wc -l < $LOG_FILE)"
echo ""
echo "HTTP 状态码分布:"
awk '{print $9}' $LOG_FILE | sort | uniq -c | sort -rn
echo ""
echo "Top 10 访问 IP:"
awk '{print $1}' $LOG_FILE | sort | uniq -c | sort -rn | head -10
echo ""
echo "Top 10 请求 URL:"
awk '{print $7}' $LOG_FILE | sort | uniq -c | sort -rn | head -10
echo ""
echo "5xx 错误:"
awk '$9 >= 500 {print $1, $4, $7, $9}' $LOG_FILE | tail -20
```

---

### 6. 常见问题

| 问题 | 解决方案 |
|------|----------|
| grep 搜索中文字符乱码 | `grep -a "错误" log.txt` 或设置 LANG |
| sed 替换斜杠多的路径 | 用 `#` 做分隔符：`sed 's#/old/path/#/new/path/#g'` |
| awk 分割 URL 中的多个空格 | `awk -F' +' '{print $1}'` |
| 特殊字符导致正则失效 | 转义：`grep '\\\\.\\\\.\\\\/' file` |
"""


def _gen_permissions_short(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. Linux 权限基础

Linux 是一个多用户系统，权限管理是系统安全的基石。

#### 1.1 权限的三个层级

| 层级 | 符号 | 含义 |
|------|------|------|
| 所有者 (Owner) | `u` | 文件的创建者 |
| 用户组 (Group) | `g` | 文件所属的用户组 |
| 其他用户 (Others) | `o` | 既不是所有者也不属于用户组的其他人 |
| 所有人 | `a` | 所有者 + 用户组 + 其他用户 |

#### 1.2 三种基本权限

| 权限 | 符号 | 数字 | 对文件的含义 | 对目录的含义 |
|------|------|------|-------------|-------------|
| 读取 (Read) | `r` | 4 | 可以查看文件内容 | 可以列出目录内容 |
| 写入 (Write) | `w` | 2 | 可以修改文件内容 | 可以在目录中创建/删除文件 |
| 执行 (Execute) | `x` | 1 | 可以执行文件 | 可以进入目录 |

#### 1.3 常用权限对照表

| 权限 | 数字 | 用途 |
|------|------|------|
| `rwx------` | 700 | 所有者完全控制，目录/脚本 |
| `rwxr-xr-x` | 755 | 所有者完全控制，其他人读和执行 |
| `rw-r--r--` | 644 | 所有者读写，其他人读（配置文件） |
| `rw-------` | 600 | 所有者读写（敏感文件，如私钥） |

---

### 2. chmod - 修改权限

```bash
# 符号模式
chmod +x deploy.sh           # 添加执行权限
chmod a-w file.txt           # 移除所有用户的写权限
chmod u+x,g+r,o-rwx script.sh

# 数字模式
chmod 755 file               # rwxr-xr-x
chmod 644 file               # rw-r--r--
chmod 700 file               # rwx------
chmod 600 file               # rw-------

# 递归修改
chmod -R 755 /var/www/html/
```

**实战场景 - Web 目录权限**：
```bash
# Web 目录权限（nginx 用户需要读权限）
chown -R www-data:www-data /var/www/html/
chmod -R 755 /var/www/html/
chmod 644 /var/www/html/index.html    # 配置文件不需执行

# 上传目录（需要写权限）
chmod 775 /var/www/html/uploads/
chown www-data:www-data /var/www/html/uploads/
```

---

### 3. chown - 修改所有者和用户组

```bash
# 修改文件所有者
chown nginx /etc/nginx/nginx.conf

# 修改所有者和用户组
chown nginx:nginx /var/log/nginx/

# 只修改用户组
chgrp www-data /var/www/html/

# 递归修改
chown -R www-data:www-data /var/www/
```

---

### 4. 特殊权限

**Sticky Bit** - 目录中只能删除自己的文件：
```bash
# /tmp 目录使用了 Sticky Bit
chmod 1777 /tmp
# 确保用户 A 不能删除用户 B 的文件
```

**SUID** - 执行时以所有者身份运行（危险，慎用）：
```bash
chmod u+s /path/to/file
chmod 4755 /path/to/file   # 4 = SUID
```

---

### 5. ACL - 访问控制列表（精细化权限）

```bash
# 查看 ACL
getfacl /path/to/file

# 给特定用户设置权限
setfacl -m u:www-data:rw /var/www/html/index.html

# 给特定用户组设置权限
setfacl -m g:developers:rx /var/www/html/

# 移除 ACL
setfacl -x u:www-data /path/to/file
```

---

### 6. 权限问题排查

```bash
# 1. 查看当前权限
ls -la /path/to/problematic/file

# 2. 查看目录权限（往上追查所有父目录）
namei -l /path/to/problematic/file

# 3. 如果是 SELinux 问题
getenforce
ls -Z /path/to/file

# Nginx 403 Forbidden 排查：
# 1. 检查文件权限 ls -la
# 2. 检查目录权限（需要 x 执行权限才能访问）
# 3. namei -l /var/www/html/index.html
# 4. 检查 SELinux
```

---

### 7. 安全最佳实践

| 场景 | 推荐权限 |
|------|----------|
| 系统配置文件 | 644 |
| 敏感配置（密码等） | 600 |
| SSH 私钥 | 600 |
| Web 目录 | 755 (所有者 www-data) |
| Web 可写目录 | 775 |
| CGI 脚本 | 755 |
| /tmp 目录 | 1777 (Sticky Bit) |
"""
    return r


def _gen_user_mgmt_short(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. Linux 用户系统概述

Linux 是一个多用户操作系统，每个需要登录的用户都必须在 `/etc/passwd` 和 `/etc/shadow` 中有记录。

#### 1.1 用户类型

| 类型 | UID 范围 | 特点 |
|------|----------|------|
| root | 0 | 超级管理员，拥有最高权限 |
| 系统用户 | 1-999 | 服务运行时使用，不能登录 |
| 普通用户 | 1000+ | 日常使用，权限受限 |

---

### 2. 用户管理命令

#### 2.1 useradd - 创建用户

```bash
# 基本创建
useradd -m sreuser

# 详细参数
useradd -m \\
    -c "SRE Engineer - Zhang San" \\
    -s /bin/bash \\
    -G sudo,docker,www-data \\
    -u 1005 \\
    zhangsan

# 设置密码
passwd zhangsan

# 验证
id zhangsan
# uid=1005(zhangsan) gid=1005(zhangsan) groups=1005(zhangsan),27(sudo),999(docker),33(www-data)
```

#### 2.2 usermod - 修改用户

```bash
usermod -aG docker zhangsan    # 添加到 docker 组（-a 必须与 -G 一起用）
usermod -s /bin/zsh zhangsan   # 更改登录 shell
usermod -L zhangsan            # 锁定账户（禁止登录）
usermod -U zhangsan            # 解锁账户
```

#### 2.3 userdel - 删除用户

```bash
userdel -r zhangsan    # 删除用户及主目录
```

---

### 3. 用户组管理

```bash
# 创建用户组
groupadd developers

# 添加用户到组
usermod -aG developers zhangsan

# 查看用户组
groups zhangsan
id zhangsan
```

---

### 4. sudo 权限管理

**visudo - 安全编辑 sudoers**：
```bash
visudo
```

**sudoers 语法示例**：
```bash
# 允许用户执行所有命令
zhangsan  ALL=(ALL:ALL)  ALL

# 允许无密码执行 sudo
zhangsan  ALL=(ALL)  NOPASSWD: ALL

# SRE 用户权限（推荐）
%SRE  ALL=(ALL)  NOPASSWD: /usr/bin/systemctl restart nginx, \\
                              /usr/bin/systemctl stop nginx, \\
                              /usr/bin/systemctl status nginx, \\
                              /usr/bin/journalctl, \\
                              /usr/bin/tail -f /var/log/*.log
```

**安全提醒**：
```bash
# ❌ 永远不要这样做
echo "ALL ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers  # 太危险！

# ✅ 正确做法：只授权需要的命令
zhangsan  ALL=(ALL)  /usr/bin/systemctl restart nginx, /usr/bin/systemctl status nginx
```

---

### 5. 密码管理

```bash
# 修改密码
passwd                    # 当前用户
passwd zhangsan           # root 修改他人密码

# 查看密码策略
chage -l zhangsan

# 设置密码过期
chage -M 90 zhangsan       # 密码 90 天后过期
chage -W 14 zhangsan       # 过期前 14 天提醒
```

---

### 6. 新员工入职 - 完整脚本

```bash
#!/bin/bash
USERNAME=$1
FULL_NAME=$2

if [ -z "$USERNAME" ] || [ -z "$FULL_NAME" ]; then
    echo "用法: $0 <用户名> <全名>"
    exit 1
fi

# 1. 创建用户
useradd -m -c "$FULL_NAME" -s /bin/bash -G sudo,docker,www-data $USERNAME

# 2. 设置初始密码
echo "$USERNAME:TempPassword123!" | chpasswd

# 3. 配置 sudo 权限（SRE 权限）
echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx, \\
                               /usr/bin/systemctl stop nginx, \\
                               /usr/bin/systemctl status nginx, \\
                               /usr/bin/systemctl restart docker" >> /etc/sudoers

# 4. 配置 SSH 密钥登录
mkdir -p /home/$USERNAME/.ssh
chmod 700 /home/$USERNAME/.ssh
# 将公钥添加到 authorized_keys
chmod 600 /home/$USERNAME/.ssh/authorized_keys
chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh

echo "✅ SRE 用户 $USERNAME 创建完成"
```

---

### 7. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `permission denied` 执行 sudo | 用户不在 sudo 组 | `usermod -aG sudo username` |
| SSH 密钥登录失败 | `.ssh` 目录权限不对 | `chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys` |
| 用户登录后立即退出 | shell 不存在 | `usermod -s /bin/bash username` |
| 密码过期无法登录 | 密码过期策略 | `chage -M -1 username` 永不过期 |
"""
    return r


def _gen_shell_basic(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. Shell 脚本基础

#### 1.1 第一个 Shell 脚本

```bash
#!/bin/bash
# 我的第一个脚本

echo "Hello, SRE!"

# 变量
NAME="SRE Engineer"
echo "Welcome, $NAME"

# 日期
echo "Today is $(date +%Y-%m-%d)"
```

```bash
# 运行脚本
chmod +x hello.sh
./hello.sh
# 或
bash hello.sh
```

#### 1.2 shebang

```bash
#!/bin/bash        # 最常用
#!/bin/sh          # 更通用（但 bashism 不可用）
#!/usr/bin/env bash # 跨平台（推荐）
```

---

### 2. 变量

#### 2.1 变量定义与使用

```bash
# 定义变量（等号两边不能有空格）
NAME="value"
AGE=25
PI=3.14

# 使用变量（$ 符号）
echo $NAME
echo "${NAME}"        # 推荐写法，避免歧义

# 整数运算
a=10
b=20
c=$((a + b))
echo "$a + $b = $c"   # 10 + 20 = 30

# 字符串操作
str="Hello SRE"
echo ${#str}          # 字符串长度 = 9
echo ${str:0:5}       # 切片 = Hello
echo ${str/SRE/SRE!}  # 替换 = Hello SRE!
```

#### 2.2 环境变量 vs 本地变量

```bash
# 本地变量（只在当前 shell 有效）
LOCAL_VAR="hello"

# 环境变量（导出后子进程可见）
export ENV_VAR="world"

# 查看所有环境变量
env
printenv

# 查看特定变量
echo $HOME
echo $PATH
echo $USER
```

---

### 3. 引号区别

| 类型 | 特点 | 示例 |
|------|------|------|
| 单引号 `''` | 完全保留原样，不解释变量 | `echo '$NAME'` → `$NAME` |
| 双引号 `""` | 解释变量和转义 | `echo "$NAME"` → `value` |
| 反引号 \`\` | 执行命令并返回结果（等价于 `$()`） | `echo \`date\`` |

```bash
NAME="SRE"
echo '$NAME'      # 输出: $NAME（单引号不解释变量）
echo "$NAME"      # 输出: SRE
echo "$(date)"    # 输出: 当前日期（推荐写法）
echo `date`       # 同上（反引号，简洁但可读性差）
```

---

### 4. read 命令 - 读取用户输入

```bash
# 基本用法
echo "Enter your name:"
read name
echo "Hello, $name"

# 一行写法
read -p "Enter your name: " name
read -sp "Enter password: " password   # -s 静默输入
read -t 5 -p "Enter value: " val       # -t 超时 5 秒

# 读取多个值
read -p "Enter name and age: " name age
echo "$name is $age years old"
```

---

### 5. 练习 1：交互式问候脚本

```bash
#!/bin/bash
# greeting.sh - 交互式问候

read -p "What's your name? " name
read -p "What's your role? (SRE/DevOps/Dev) " role

echo ""
echo "Hello, $name!"
echo "Role: $role"

case "$role" in
    [Ss][Rr][Ee]|SRE)
        echo "Welcome to SRE team!" ;;
    [Dd]ev)
        echo "Thanks for joining!" ;;
    *)
        echo "Nice to meet you!" ;;
esac

echo "Today is $(date '+%Y-%m-%d %H:%M:%S')"
```

---

### 6. 练习 2：系统信息报告

```bash
#!/bin/bash
# sysinfo.sh - 系统信息报告

echo "=== 系统信息报告 ==="
echo ""
echo "主机名: $(hostname)"
echo "操作系统: $(uname -s)"
echo "内核版本: $(uname -r)"
echo "运行时间: $(uptime -p)"
echo "当前用户: $USER"
echo "Shell: $SHELL"
echo "当前目录: $(pwd)"
echo ""
echo "=== 资源使用 ==="
echo "CPU: $(top -bn1 | grep '%Cpu' | awk '{print $2}')%"
echo "内存: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "磁盘: $(df -h / | awk 'NR==2 {print $3 "/" $2}')"
echo ""
echo "=== 网络 ==="
ip -br addr show | awk '{print $1, $3}'
```
"""
    return r


def _gen_shell_if(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. 条件判断基础

#### 1.1 test 和 [ ] 语法

```bash
# test 表达式
test $age -ge 18

# [ ] 语法（等价，推荐）
[ $age -ge 18 ]

# 注意：[] 内的变量要用引号包裹，防止空值报错
[ "$name" = "root" ]
```

#### 1.2 数字比较运算符

| 运算符 | 含义 |
|--------|------|
| `-eq` | 等于 (equal) |
| `-ne` | 不等于 (not equal) |
| `-lt` | 小于 (less than) |
| `-gt` | 大于 (greater than) |
| `-le` | 小于等于 |
| `-ge` | 大于等于 |

```bash
a=10
b=20

[ $a -eq 10 ] && echo "a equals 10"
[ $b -gt $a ] && echo "b is greater than a"
[ $a -ne $b ] && echo "a and b are different"
```

#### 1.3 字符串比较

| 运算符 | 含义 |
|--------|------|
| `=` 或 `==` | 字符串相等 |
| `!=` | 字符串不相等 |
| `-z` | 字符串为空 |
| `-n` | 字符串非空 |

```bash
name="SRE"

[ "$name" = "SRE" ] && echo "It's SRE"
[ -z "$name" ] && echo "name is empty"
[ -n "$name" ] && echo "name is not empty"
[ "$name" != "Dev" ] && echo "name is not Dev"
```

#### 1.4 文件测试

| 运算符 | 含义 |
|--------|------|
| `-f` | 普通文件存在 |
| `-d` | 目录存在 |
| `-e` | 文件或目录存在 |
| `-r/w/x` | 可读/可写/可执行 |
| `-L` | 符号链接 |
| `-s` | 文件非空 |

```bash
[ -f "/etc/passwd" ] && echo "passwd exists"
[ -d "/tmp" ] && echo "tmp is a directory"
[ -r "/var/log/syslog" ] && echo "syslog is readable"
[ -w "/tmp/test.txt" ] && echo "test.txt is writable"
```

---

### 2. if/elif/else 结构

#### 2.1 基本语法

```bash
if [ 条件 ]; then
    # commands
elif [ 条件 ]; then
    # commands
else
    # commands
fi
```

#### 2.2 实战示例

```bash
#!/bin/bash
# check_service.sh - 检查服务状态

SERVICE=${1:-nginx}

if systemctl is-active --quiet $SERVICE; then
    echo "✅ $SERVICE is running"
else
    echo "❌ $SERVICE is NOT running"
    read -p "Restart now? (y/n) " answer
    if [ "$answer" = "y" ]; then
        sudo systemctl restart $SERVICE
        echo "✅ $SERVICE restarted"
    fi
fi
```

```bash
#!/bin/bash
# disk_check.sh - 磁盘空间检查

THRESHOLD=${1:-80}
USAGE=$(df / | awk 'NR==2 {print $5+0}')

echo "磁盘使用率: ${USAGE}%"

if [ $USAGE -ge 95 ]; then
    echo "🚨 CRITICAL: 磁盘即将用尽！立即清理！"
    exit 2
elif [ $USAGE -ge 80 ]; then
    echo "⚠️ WARNING: 磁盘使用率超过 ${THRESHOLD}%"
    exit 1
else
    echo "✅ 磁盘使用正常"
    exit 0
fi
```

```bash
#!/bin/bash
# access_control.sh - 简易访问控制

echo "Enter your username:"
read username

if [ "$username" = "admin" ]; then
    echo "Welcome, Administrator!"
elif [ "$username" = "sre" ]; then
    echo "Welcome, SRE Engineer!"
elif [ "$username" = "guest" ]; then
    echo "Welcome, Guest! (read-only access)"
else
    echo "Access denied: Unknown user"
    exit 1
fi
```

---

### 3. 逻辑运算符

```bash
# && (AND) - 前一个成功后执行后一个
[ -f /etc/nginx/nginx.conf ] && echo "Nginx config exists"

# || (OR) - 前一个失败后执行后一个
[ -f /etc/nginx/nginx.conf ] || echo "Config not found"

# ! (NOT)
[ ! -f /tmp/lock ] && echo "No lock, proceeding..."

# 组合使用（需要双层括号）
if [ "$status" -eq 200 ] || [ "$status" -eq 201 ]; then
    echo "Success"
fi
```

---

### 4. 实战：服务健康检查脚本

```bash
#!/bin/bash
# health_check.sh - 综合健康检查

ERRORS=0

check_service() {
    local svc=$1
    if systemctl is-active --quiet $svc; then
        echo "✅ $svc: OK"
    else
        echo "❌ $svc: FAILED"
        ERRORS=$((ERRORS + 1))
    fi
}

check_port() {
    local port=$1
    local name=$2
    if ss -tlnp | grep -q ":$port "; then
        echo "✅ $name (port $port): listening"
    else
        echo "❌ $name (port $port): NOT listening"
        ERRORS=$((ERRORS + 1))
    fi
}

echo "=== 健康检查 $(date) ==="
echo ""

echo "【服务状态】"
check_service nginx
check_service mysql
check_service redis

echo ""
echo "【端口检查】"
check_port 80  "HTTP"
check_port 443 "HTTPS"
check_port 3306 "MySQL"

echo ""
echo "【磁盘检查】"
df -h | awk 'NR>1 {
    usage=$5+0
    if (usage > 80) print "⚠️ " $1 ": " usage "% used"
    else if (usage > 90) print "🚨 " $1 ": " usage "% used - CRITICAL"
}'

echo ""
echo "【内存检查】"
FREE_PCT=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
if [ "$FREE_PCT" -gt 90 ]; then
    echo "⚠️ 内存使用率: ${FREE_PCT}%"
fi

exit $ERRORS
```

---

### 5. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `[ "$var" = "value" ]` 报错 | var 为空或含空格 | `[ "$var" = "value" ]` 加引号 |
| `unary operator expected` | 变量为空时 `[]` 语法错误 | 用 `[[ ]]` 或加引号 |
| `integer expression expected` | 用数字运算符比较字符串 | 用 `=` 比较字符串 |
"""
    return r


def _gen_shell_loop(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. for 循环

#### 1.1 基本语法

```bash
for 变量 in 列表; do
    # commands
done

# 单行写法
for f in *.log; do echo "Processing $f"; done
```

#### 1.2 常用列表形式

```bash
# 数字序列
for i in {1..5}; do echo "Number: $i"; done
for i in {0..10..2}; do echo "$i"; done  # 步进 2

# 字符串列表
for color in red green blue; do
    echo "Color: $color"
done

# 命令输出
for f in $(ls *.txt); do echo "File: $f"; done
for h in $(hostname -I); do echo "IP: $h"; done

# 文件通配符
for conf in /etc/nginx/*.conf; do
    echo "Config: $conf"
done
```

#### 1.3 C 风格 for 循环

```bash
for ((i=0; i<10; i++)); do
    echo "i = $i"
done

for ((a=1, b=10; a<=10; a++, b--)); do
    echo "$a - $b"
done
```

---

### 2. while 循环

#### 2.1 基本语法

```bash
while 条件; do
    # commands
done
```

#### 2.2 实战示例

```bash
#!/bin/bash
# count_down.sh - 倒计时

count=5
while [ $count -gt 0 ]; do
    echo "$count..."
    sleep 1
    count=$((count - 1))
done
echo "Done!"
```

```bash
#!/bin/bash
# read_file.sh - 逐行读取文件

while read -r line; do
    echo "Line: $line"
done < /etc/hosts

# 跳过空行和注释
while read -r line; do
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    echo "Config: $line"
done < /etc/nginx/nginx.conf
```

---

### 3. until 循环

```bash
# until：条件为 false 时继续执行
count=1
until [ $count -gt 5 ]; do
    echo "Count: $count"
    count=$((count + 1))
done
```

---

### 4. 循环控制

```bash
# break - 跳出循环
for i in {1..10}; do
    if [ $i -eq 5 ]; then
        echo "Breaking at $i"
        break
    fi
    echo $i
done

# continue - 跳过当前迭代
for i in {1..10}; do
    if [ $i -eq 5 ]; then
        echo "Skipping $i"
        continue
    fi
    echo $i
done
```

---

### 5. 实战：批量创建用户

```bash
#!/bin/bash
# batch_user.sh - 批量创建用户

USER_FILE="/tmp/users.txt"

if [ ! -f "$USER_FILE" ]; then
    echo "错误: 用户文件不存在"
    exit 1
fi

COUNT=0
while IFS=: read -r username groups; do
    # 检查用户是否已存在
    if id "$username" &>/dev/null; then
        echo "⏭️  $username 已存在，跳过"
        continue
    fi

    # 创建用户
    useradd -m -s /bin/bash -G "$groups" "$username"
    echo "$username:TempPass123!" | chpasswd
    echo "$username:$(date)" >> /var/log/new_users.log
    COUNT=$((COUNT + 1))
    echo "✅ Created: $username (groups: $groups)"
done < "$USER_FILE"

echo ""
echo "✅ 完成！共创建 $COUNT 个用户"
```

**user.txt 格式**：
```
alice:sudo,docker,www-data
bob:developers
charlie:adm,docker
```

---

### 6. 实战：批量处理日志

```bash
#!/bin/bash
# archive_old_logs.sh - 归档旧日志

LOG_DIR="/var/log/myapp"
DAYS=${1:-30}
ARCHIVE_DIR="/archive/logs"
DATE=$(date +%Y%m%d)

mkdir -p "$ARCHIVE_DIR"

COUNT=0
for logfile in $(find "$LOG_DIR" -name "*.log" -mtime +$DAYS 2>/dev/null); do
    FILENAME=$(basename "$logfile")
    SIZE=$(du -h "$logfile" | cut -f1)

    # 压缩
    gzip -c "$logfile" > "$ARCHIVE_DIR/${FILENAME%.log}_${DATE}.log.gz"
    rm "$logfile"

    echo "✅ Archived: $FILENAME (size: $SIZE)"
    COUNT=$((COUNT + 1))
done

echo ""
echo "✅ 完成！归档 $COUNT 个文件"
du -sh "$ARCHIVE_DIR"
```

---

### 7. 实战：并行处理（并发控制）

```bash
#!/bin/bash
# parallel_download.sh - 简单并发控制

MAX_JOBS=4
URLS=(
    "https://example.com/file1.tar.gz"
    "https://example.com/file2.tar.gz"
    "https://example.com/file3.tar.gz"
    "https://example.com/file4.tar.gz"
    "https://example.com/file5.tar.gz"
    "https://example.com/file6.tar.gz"
)

download() {
    local url=$1
    local file=$(basename "$url")
    echo "Starting: $file"
    # curl -s -o "$file" "$url"
    sleep 2  # 模拟下载
    echo "Done: $file"
}

for url in "${URLS[@]}"; do
    download "$url" &

    # 并发控制：超过 MAX_JOBS 时等待
    while [ $(jobs -r | wc -l) -ge $MAX_JOBS ]; do
        wait -n
    done
done

wait
echo "✅ All downloads complete!"
```
"""
    return r


def _gen_shell_function(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. 函数基础

#### 1.1 定义和调用

```bash
# 定义函数
hello() {
    echo "Hello, World!"
}

# 调用函数
hello
```

#### 1.2 带参数的函数

```bash
greet() {
    echo "Hello, $1!"   # $1 是第一个参数
    echo "Hello, $2!"   # $2 是第二个参数
    echo "Total args: $#"  # 参数个数
    echo "All args: $@"    # 所有参数
}

greet "Alice" "Bob"
# Hello, Alice!
# Hello, Bob!
# Total args: 2
# All args: Alice Bob
```

---

### 2. 参数传递

| 变量 | 含义 |
|------|------|
| `$1-$9` | 第 1-9 个参数 |
| `${10}` | 第 10 个及以上参数 |
| `$#` | 参数个数 |
| `$@` | 所有参数（各自独立） |
| `$*` | 所有参数（合并为一个） |
| `$0` | 脚本名称 |
| `$$` | 当前进程 PID |

#### 2.1 默认值

```bash
greet() {
    local name=${1:-"Guest"}   # 默认值 "Guest"
    echo "Hello, $name"
}

greet           # Hello, Guest!
greet "Alice"   # Hello, Alice!
```

#### 2.2 返回值处理

```bash
# return：返回退出码（0-255）
is_root() {
    [ "$EUID" -eq 0 ]
}

if is_root; then
    echo "Running as root"
else
    echo "Not root"
fi

# 函数返回值通过 $? 获取（立即使用）
get_sum() {
    local a=$1
    local b=$2
    echo $((a + b))    # 用 echo 返回数值
}

result=$(get_sum 10 20)
echo "Sum: $result"    # Sum: 30
```

---

### 3. 变量作用域

```bash
# 全局变量（默认）
VAR="global"

# 局部变量（推荐）
demo() {
    local VAR="local"  # local 关键字
    echo "Inside: $VAR"
}

demo
echo "Outside: $VAR"
# Inside: local
# Outside: global
```

---

### 4. 实战：菜单系统（Day 20）

```bash
#!/bin/bash
# service_manager.sh - 服务管理菜单

source ~/.bashrc &>/dev/null

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

service_status() {
    local svc=$1
    if systemctl is-active --quiet $svc; then
        echo "✅ $svc"
    else
        echo "❌ $svc"
    fi
}

show_menu() {
    echo ""
    echo "=== 服务管理菜单 ==="
    echo "1. 查看所有服务状态"
    echo "2. 重启 Nginx"
    echo "3. 重启 MySQL"
    echo "4. 重启 Redis"
    echo "5. 重启所有 Web 服务"
    echo "6. 查看日志"
    echo "0. 退出"
    echo ""
    echo -n "请选择: "
}

show_all_status() {
    echo ""
    log "检查服务状态..."
    for svc in nginx mysql redis php-fpm; do
        service_status $svc
    done
}

restart_nginx() {
    log "重启 Nginx..."
    sudo systemctl restart nginx
    service_status nginx
}

restart_mysql() {
    log "重启 MySQL..."
    sudo systemctl restart mysql
    service_status mysql
}

restart_redis() {
    log "重启 Redis..."
    sudo systemctl restart redis
    service_status redis
}

restart_all_web() {
    log "重启所有 Web 服务..."
    sudo systemctl restart nginx mysql redis php-fpm
    sleep 1
    show_all_status
}

show_logs() {
    echo ""
    log "最近 Nginx 错误..."
    sudo journalctl -u nginx --no-pager -n 5
}

while true; do
    show_menu
    read choice
    case "$choice" in
        1) show_all_status ;;
        2) restart_nginx ;;
        3) restart_mysql ;;
        4) restart_redis ;;
        5) restart_all_web ;;
        6) show_logs ;;
        0) log "退出"; exit 0 ;;
        *) log "无效选择: $choice" ;;
    esac
done
```

---

### 5. 实战：日志分析函数库

```bash
#!/bin/bash
# loglib.sh - 日志分析函数库

# 统计日志文件中各状态码数量
count_status_codes() {
    local logfile=$1
    if [ ! -f "$logfile" ]; then
        echo "Error: file not found"
        return 1
    fi

    echo "状态码分布:"
    awk '{print $9}' "$logfile" | sort | uniq -c | sort -rn
}

# 查找异常 IP（访问超过阈值）
find_suspicious_ips() {
    local logfile=$1
    local threshold=${2:-100}

    echo "可疑 IP (访问 > $threshold):"
    awk '{print $1}' "$logfile" | sort | uniq -c | sort -rn |
        awk -v t=$threshold '$1 > t {print $2": "$1" requests"}'
}

# 提取 5xx 错误记录
extract_errors() {
    local logfile=$1
    local output=${2:-"/tmp/errors.txt"}

    awk '$9 >= 500 {print $1, $4, $7, $9}' "$logfile" > "$output"
    echo "5xx 错误已保存到: $output ($(wc -l < "$output") 条)"
}

# 使用示例
# source ./loglib.sh
# count_status_codes /var/log/nginx/access.log
# find_suspicious_ips /var/log/nginx/access.log 50
# extract_errors /var/log/nginx/access.log
```
"""
    return r


def _gen_shell_case(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. case 语句

#### 1.1 基本语法

```bash
case 变量 in
    模式1)
        # commands
        ;;
    模式2)
        # commands
        ;;
    *)
        # 默认命令（可选）
        ;;
esac
```

#### 1.2 通配符模式

| 模式 | 含义 |
|------|------|
| `a)` | 精确匹配 "a" |
| `a\|b)` | 匹配 "a" 或 "b" |
| `[abc])` | 匹配 a、b 或 c |
| `[0-9])` | 匹配单个数字 |
| `*.txt)` | 匹配 .txt 结尾 |
| `?)` | 匹配单个任意字符 |
| `*)` | 匹配任意字符（默认） |

---

### 2. 实战示例

```bash
#!/bin/bash
# system_control.sh - 系统控制脚本

ACTION=${1:-"status"}

case "$ACTION" in
    start)
        echo "Starting services..."
        sudo systemctl start nginx mysql
        ;;
    stop)
        echo "Stopping services..."
        sudo systemctl stop nginx mysql
        ;;
    restart)
        echo "Restarting services..."
        sudo systemctl restart nginx mysql
        ;;
    status)
        systemctl status nginx --no-pager
        systemctl status mysql --no-pager
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
```

```bash
#!/bin/bash
# file_type.sh - 判断文件类型

FILE=${1:-"/etc/passwd"}

case "$(file -b "$FILE")" in
    *directory*)
        echo "Directory: $FILE"
        ls -ld "$FILE"
        ;;
    *symbolic\ link*)
        echo "Symbolic link to: $(readlink -f "$FILE")"
        ;;
    *ASCII\ text*)
        echo "Text file: $FILE"
        wc -l "$FILE"
        ;;
    *empty*)
        echo "Empty file: $FILE"
        ;;
    *)
        echo "Other type: $FILE"
        file "$FILE"
        ;;
esac
```

---

### 3. select 菜单

```bash
#!/bin/bash
# interactive_menu.sh - 交互式菜单

PS3="请选择服务器 (1-4): "
options=("Web Server" "Database Server" "Cache Server" "Exit")

select opt in "${options[@]}"; do
    case $opt in
        "Web Server")
            echo "Selected: Web Server (Nginx)"
            sudo systemctl status nginx --no-pager
            ;;
        "Database Server")
            echo "Selected: Database Server (MySQL)"
            sudo systemctl status mysql --no-pager
            ;;
        "Cache Server")
            echo "Selected: Cache Server (Redis)"
            sudo systemctl status redis --no-pager
            ;;
        "Exit")
            echo "Goodbye!"
            break
            ;;
        *)
            echo "Invalid option: $REPLY"
            ;;
    esac
done
```

**PS3 提示符变量**：
```bash
# 默认提示
select opt in A B C; do echo $opt; done
# 输出：
# 1) A
# 2) B
# 3) C
# #? _
```

---

### 4. 实战：服务管理菜单

```bash
#!/bin/bash
# menu_service.sh - SRE 服务管理菜单

SERVICES="nginx mysql redis php-fpm apache2 docker"

show_status() {
    echo ""
    echo "=== 服务状态 ==="
    for svc in $SERVICES; do
        if systemctl is-active --quiet $svc 2>/dev/null; then
            echo "  ✅ $svc"
        else
            echo "  ❌ $svc"
        fi
    done
}

restart_service() {
    local svc=$1
    echo "Restarting $svc..."
    sudo systemctl restart $svc
    sleep 1
    if systemctl is-active --quiet $svc; then
        echo "  ✅ $svc restarted successfully"
    else
        echo "  ❌ $svc restart failed"
    fi
}

echo "========================================="
echo "       SRE 服务管理工具"
echo "========================================="

PS3="请选择操作: "
options=("查看所有服务" "重启 Nginx" "重启 MySQL" "重启 Redis" "重启全部" "退出")

select opt in "${options[@]}"; do
    case $REPLY in
        1) show_status ;;
        2) restart_service nginx ;;
        3) restart_service mysql ;;
        4) restart_service redis ;;
        5)
            for svc in $SERVICES; do
                restart_service $svc
            done
            ;;
        6) echo "再见!"; break ;;
        *) echo "无效选择: $REPLY" ;;
    esac
done
```
"""
    return r


def _gen_shell_array(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. 数组基础

#### 1.1 定义数组

```bash
# 方式 1：括号
arr=(one two three four)

# 方式 2：按索引
arr[0]=one
arr[1]=two
arr[5]=five    # 跳跃赋值

# 方式 3：读取命令输出
files=($(ls *.log))
```

#### 1.2 访问数组

```bash
arr=(apple banana cherry)

echo "${arr[0]}"      # apple
echo "${arr[@]}"      # 全部元素
echo "${#arr[@]}"     # 数组长度 = 3
echo "${!arr[@]}"     # 所有索引 = 0 1 2

# 切片
echo "${arr[@]:1:2}"  # banana cherry
```

---

### 2. 数组操作

```bash
# 添加元素
arr+=(orange)           # 追加到末尾
arr=( "${arr[@]}" "grape" )

# 删除元素
unset arr[1]            # 删除索引 1
unset arr               # 删除整个数组

# 重新赋值
arr=("${arr[@]/banana/pear}")  # 替换
```

---

### 3. 关联数组（字典）

```bash
# 必须先声明
declare -A user

user[name]="Alice"
user[role]="SRE"
user[level]=3

# 访问
echo "${user[name]}"    # Alice
echo "${!user[@]}"      # 所有键 = name role level
echo "${#user[@]}"       # 键数量 = 3

# 遍历
for key in "${!user[@]}"; do
    echo "$key: ${user[$key]}"
done
```

---

### 4. 实战：日志分析统计

```bash
#!/bin/bash
# log_stats.sh - Nginx 日志统计分析

declare -A status_count
declare -A ip_count
declare -A url_count
TOTAL=0

while read -r line; do
    # 解析 access.log（combined 格式）
    ip=$(echo "$line" | awk '{print $1}')
    status=$(echo "$line" | awk '{print $9}')
    url=$(echo "$line" | awk '{print $7}')

    # 统计状态码
    ((status_count[$status]++))

    # 统计 IP
    ((ip_count[$ip]++))

    # 统计 URL
    ((url_count[$url]++))

    ((TOTAL++))
done < /var/log/nginx/access.log

echo "=== Nginx 日志统计 (总计 $TOTAL 请求) ==="
echo ""

echo "【状态码分布】"
for status in "${!status_count[@]}"; do
    pct=$((status_count[$status] * 100 / TOTAL))
    printf "  %s: %d (%d%%)\n" "$status" "${status_count[$status]}" "$pct"
done | sort -t: -k2 -rn

echo ""
echo "【Top 10 IP】"
for ip in "${!ip_count[@]}"; do
    echo "$ip: ${ip_count[$ip]}"
done | sort -t: -k2 -rn | head -10

echo ""
echo "【Top 10 URL】"
for url in "${!url_count[@]}"; do
    echo "$url: ${url_count[$url]}"
done | sort -t: -k2 -rn | head -10
```

---

### 5. 实战：配置管理

```bash
#!/bin/bash
# config_manager.sh - 配置文件管理

declare -A config

# 加载配置
load_config() {
    local cfg_file=$1
    while IFS='=' read -r key value; do
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        config[$key]=$value
    done < "$cfg_file"
}

# 保存配置
save_config() {
    local cfg_file=$1
    for key in "${!config[@]}"; do
        echo "$key=${config[$key]}"
    done > "$cfg_file"
}

# 使用
load_config /etc/myapp.conf
echo "DB Host: ${config[db_host]}"
echo "DB Port: ${config[db_port]}"

config[db_host]="new-host.local"
save_config /etc/myapp.conf
```
"""
    return r


def _gen_shell_expect(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. expect 基础

expect 是自动化交互工具，适合 SSH、telnet、ftp 等需要交互输入的场景。

```bash
# 安装
sudo apt install -y expect
```

---

### 2. 核心命令

| 命令 | 含义 |
|------|------|
| `spawn` | 启动进程 |
| `expect` | 等待特定输出 |
| `send` | 发送输入 |
| `interact` | 交出控制权给用户 |
| `exp_send` | send 的别名 |

---

### 3. 实战：SSH 自动登录

```bash
#!/usr/bin/expect -f
# ssh_auto.exp - SSH 自动登录

set timeout 30
set host [lindex $argv 0]
set user [lindex $argv 1]
set password [lindex $argv 2]

spawn ssh "$user@$host"

expect {
    "password:" {
        send "$password\\r"
    }
    "yes/no" {
        send "yes\\r"
        exp_continue
    }
    timeout {
        puts "Connection timeout"
        exit 1
    }
}

interact
```

**改进版（执行命令后退出）**：
```bash
#!/usr/bin/expect -f

set timeout 60
set host [lindex $argv 0]
set user [lindex $argv 1]
set password [lindex $argv 2]
set cmd [lindex $argv 3]

spawn ssh "$user@$host"

expect {
    "password:" {
        send "$password\\r"
    }
    "yes/no" {
        send "yes\\r"
        exp_continue
    }
}

expect "$ "
send "$cmd\\r"
expect "$ "
send "exit\\r"
expect eof
```

**使用**：
```bash
chmod +x ssh_auto.exp
./ssh_auto.exp 192.168.1.100 root "password" "uptime"
./ssh_auto.exp 192.168.1.100 root "password" "df -h"
```

---

### 4. 实战：批量 SSH 执行命令

```bash
#!/bin/bash
# batch_ssh.sh - 批量 SSH 执行

HOSTS_FILE="hosts.txt"
CMD=${1:-"uptime"}

if [ ! -f "$HOSTS_FILE" ]; then
    echo "错误: $HOSTS_FILE 不存在"
    exit 1
fi

while IFS=: read -r host user password; do
    echo "=== $host ==="
    ./ssh_auto.exp "$host" "$user" "$password" "$CMD"
    echo ""
done < "$HOSTS_FILE"
```

**hosts.txt 格式**：
```
192.168.1.100:root:password123
192.168.1.101:admin:admin456
192.168.1.102:sre:sre789
```

---

### 5. 实战：自动 SCP 传输文件

```bash
#!/usr/bin/expect -f
# scp_auto.exp - 自动 SCP 传输

set timeout 120
set src [lindex $argv 0]
set dst [lindex $argv 1]
set host [lindex $argv 2]
set user [lindex $argv 3]
set password [lindex $argv 4]

spawn scp "$src" "$user@$host:$dst"

expect {
    "password:" {
        send "$password\\r"
    }
    "yes/no" {
        send "yes\\r"
        exp_continue
    }
}

expect eof
```

---

### 6. 实战：mysql 自动执行

```bash
#!/usr/bin/expect -f
# mysql_auto.exp - MySQL 自动登录

set timeout 30
set mysql_user [lindex $argv 0]
set mysql_pass [lindex $argv 1]
set sql_cmd [lindex $argv 2]

spawn mysql -u "$mysql_user" -p

expect {
    "password:" {
        send "$mysql_pass\\r"
    }
}

expect "mysql>"
send "$sql_cmd;\\r"
expect "mysql>"
send "exit\\r"
expect eof
```

**使用**：
```bash
chmod +x mysql_auto.exp
./mysql_auto.exp root "password123" "SHOW DATABASES;"
./mysql_auto.exp root "password123" "SELECT COUNT(*) FROM mydb.users;"
```

---

### 7. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| spawn 无效 | shebang 写错 | 必须用 `#!/usr/bin/expect -f` |
| 超时 | 命令执行慢 | 调大 `set timeout` |
| 密码含特殊字符 | 转义问题 | 用单引号包裹 |
| 交互失败 | expect 匹配模式不准确 | 用 `expect -d` 调试 |
"""
    return r


def _gen_shell_trap(day: int, topic: str) -> str:
    return """## 📖 详细知识点

### 1. trap - 信号处理

trap 用于捕获信号并执行指定命令，常用于：
- 脚本退出时清理临时文件
- 忽略 Ctrl+C
- 优雅处理中断

#### 1.1 常用信号

| 信号 | 含义 | Ctrl 快捷键 |
|------|------|------------|
| SIGTERM (15) | 优雅终止 | |
| SIGINT (2) | 中断 | Ctrl+C |
| SIGQUIT (3) | 退出 | Ctrl+\\ |
| SIGHUP (1) | 挂起 | |
| EXIT (0) | 脚本退出 | |

#### 1.2 基本语法

```bash
trap 'commands' signals
trap 'cleanup' EXIT          # 脚本退出时清理
trap '' SIGINT               # 忽略 Ctrl+C
trap - SIGINT                # 恢复默认
```

---

### 2. 实战：脚本退出清理

```bash
#!/bin/bash
# cleanup_demo.sh - 清理示例

TEMP_FILES=()
LOG_FILE="/tmp/script_$$.log"

cleanup() {
    echo "执行清理..."
    rm -f "${TEMP_FILES[@]}"
    rm -f "$LOG_FILE"
    echo "清理完成"
}

trap cleanup EXIT

# 创建临时文件
TEMP_FILES=("/tmp/file1_$$.txt" "/tmp/file2_$$.txt")
touch "${TEMP_FILES[@]}"

echo "开始处理..." | tee "$LOG_FILE"
# 模拟处理
sleep 5
echo "完成"
```

---

### 3. 实战：调试模式

```bash
#!/bin/bash
# debug_demo.sh - 调试示例

set -x                    # 打印执行的命令
set -e                    # 遇错误立即退出
# set -u                    # 使用未定义变量时报错
# set -o pipefail          # 管道中任何一个失败则整个失败

echo "Starting..."
ls non_existent_file     # set -e 会导致退出
echo "This won't print"
```

**调试技巧**：
```bash
# 局部调试
set -x
echo "Debug section"
set +x                    # 关闭调试

# 打印变量值
set -x
echo "Variable: $myvar"
set +x
```

---

### 4. 实战：优雅处理中断

```bash
#!/bin/bash
# graceful_shutdown.sh - 优雅关闭

WORK_DIR="/tmp/task_$$"
PID_FILE="/tmp/task_$$.pid"

cleanup() {
    echo "收到退出信号，正在优雅关闭..."
    # 停止后台任务
    if [ -f "$PID_FILE" ]; then
        kill -TERM $(cat "$PID_FILE") 2>/dev/null
        rm -f "$PID_FILE"
    fi
    # 清理临时文件
    rm -rf "$WORK_DIR"
    echo "清理完成，退出"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# 启动
mkdir -p "$WORK_DIR"
echo $$ > "$PID_FILE"

echo "服务运行中 (PID: $$)..."
echo "按 Ctrl+C 退出"

# 模拟长时间任务
while true; do
    sleep 1
done
```

---

### 5. set 内置选项

| 选项 | 命令 | 含义 |
|------|------|------|
| `-x` | `set -x` | 打印命令（调试） |
| `-e` | `set -e` | 命令失败即退出 |
| `-u` | `set -u` | 未定义变量报错 |
| `-o pipefail` | `set -o pipefail` | 管道失败检测 |
| `-n` | `set -n` | 语法检查（不执行） |

```bash
#!/bin/bash
# 严格模式（推荐在脚本开头使用）
set -euo pipefail
IFS=$'\\n\\t'

# 好处：
# -e: 错误立即停止
# -u: 变量未定义立即报错
# -o pipefail: 管道中任一失败则失败
```

---

### 6. 实战：带错误处理的脚本

```bash
#!/bin/bash
# robust_script.sh - 健壮的脚本

set -euo pipefail
IFS=$'\\n\\t'

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

error_exit() {
    log "ERROR: $1" >&2
    exit 1
}

# 检查依赖
check_deps() {
    for cmd in curl jq python3; do
        command -v $cmd &>/dev/null || error_exit "缺少命令: $cmd"
    done
}

# 检查参数
check_args() {
    if [ $# -lt 1 ]; then
        echo "用法: $0 <参数>"
        exit 1
    fi
}

main() {
    check_deps
    check_args "$@"

    log "开始处理: $1"
    # 处理逻辑
    log "完成"
}

main "$@"
```

---

### 7. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 脚本无法 Ctrl+C 退出 | trap 捕获了 SIGINT | `trap - SIGINT` 恢复默认 |
| 清理函数未执行 | 未 trap EXIT | `trap cleanup EXIT` |
| 调试输出太多 | set -x 输出大 | 用 `set +x` 局部关闭 |
| 管道命令失败但脚本继续 | 未用 pipefail | `set -o pipefail` |
"""
    return r


# ── 主生成逻辑 ───────────────────────────────────────────────────────────────

def make_day_doc(day: int, topic: str) -> Tuple[str, List[str]]:
    """生成完整的学习文档"""

    knowledge_content = gen_content_for_topic(day, topic)

    # 生成阶段标识
    if day <= 7:
        phase = "Week 1：Linux 入门"
    elif day <= 14:
        phase = "Week 2：进程管理与系统监控"
    elif day <= 21:
        phase = "Week 3：Shell 脚本编程（上）"
    else:
        phase = "Week 4：Shell 脚本编程（下）+ 实战项目"

    doc = f"""# Day {day:02d}: {topic}

> 📅 日期：{datetime.now().strftime('%Y-%m-%d')}
> 📖 学习主题：{topic}
> 📚 所属阶段：{phase}
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day {day:02d} 的学习后，你应该掌握：
- 理解 {topic} 的核心概念和原理
- 能够独立完成相关命令的操作练习
- 在实际工作中正确应用这些知识
- 为 SRE 进阶打下坚实基础

---

## 📖 详细知识点

{knowledge_content}

---

## 💻 实战练习

### 练习 1：基础命令练习

```bash
# 根据今日主题，在自己的 Linux 环境中练习相关命令
# 例如：如果是进程管理，执行 ps, top, kill 等命令
# 如果是文本处理，用 grep/sed/awk 分析实际日志

# 1. 查看系统信息
# ...
```

### 练习 2：实际工作场景

```bash
# 设计一个与今日主题相关的实际工作场景
# 例如：日志分析、服务管理、故障排查等

# 场景：...
# 步骤 1：...
# 步骤 2：...
```

### 练习 3：进阶挑战（选做）

```bash
# 尝试完成一个稍微复杂的任务
# 例如：自动化脚本、批量处理等
```

---

## 📚 学习资源

{gen_common_resources()}

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

*由 SRE 学习计划自动生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Generated by Hermes Agent*
"""

    issues = []
    # 检查占位符
    placeholders = re.findall(r'在此[^"]*', doc)
    # 过滤合法占位符
    real_placeholders = [p for p in placeholders if '在此记录' not in p and '在此完成' not in p and '在此设计' not in p]
    if real_placeholders:
        issues.append(f"发现占位符: {real_placeholders[:3]}")

    code_blocks = len(re.findall(r'```', doc))
    if code_blocks < 4:
        issues.append(f"代码块偏少 ({code_blocks//2} 个，建议 8+ 个)")

    h2_count = len(re.findall(r'^## ', doc, re.MULTILINE))
    if h2_count < 3:
        issues.append(f"二级标题偏少 ({h2_count} 个，建议 5+ 个)")

    return doc, issues


# ── 主流程 ──────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=str, default='1-28', help='范围，如 1-28 或 4-14')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    # 解析范围
    if '-' in args.days:
        start, end = map(int, args.days.split('-'))
    else:
        start = end = int(args.days)

    git_config()

    for day in range(start, end + 1):
        topic = get_topic_from_overview(day)
        if not topic:
            topic = get_topic_fallback(day)

        content, issues = make_day_doc(day, topic)

        day_padded = f"{day:02d}"
        day_dir = DOCS_DIR / f"day{day_padded}"
        day_dir.mkdir(exist_ok=True)
        doc_path = day_dir / "README.md"

        if args.dry_run:
            print(f"[dry-run] day{day_padded}: {topic} | issues: {issues}")
            continue

        doc_path.write_text(content, encoding='utf-8')

        # Git commit
        run(f'git add -A && git commit -m "Day {day_padded}: {topic} - auto-generated"', timeout=30)

        if issues:
            print(f"⚠️  day{day_padded}: {topic} | issues: {issues}")
        else:
            print(f"✅  day{day_padded}: {topic}")

    print(f"\n完成！生成了 Day {start}-{end} 的学习文档。")


if __name__ == "__main__":
    main()
