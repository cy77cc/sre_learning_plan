
def generate_practice_section(day: int, topic: str) -> str:
    """Generate enterprise-level practice sections"""
    topic_lower = topic.lower()
    
    if day == 1 or 'linux' in topic_lower or '虚拟机' in topic_lower or 'ubuntu' in topic_lower:
        return _practice_linux_intro()
    elif day == 2 or '文件系统' in topic_lower or 'fhs' in topic_lower:
        return _practice_fhs()
    elif day == 3 or '文件操作' in topic_lower:
        return _practice_file_ops()
    elif day == 4 or '文本处理' in topic_lower or 'grep' in topic_lower or 'sed' in topic_lower or 'awk' in topic_lower:
        return _practice_text_processing()
    elif day == 5 or '权限' in topic_lower or 'chmod' in topic_lower:
        return _practice_permissions()
    elif day == 6 or '用户' in topic_lower or 'useradd' in topic_lower:
        return _practice_user_mgmt()
    elif day == 7 or day == 14:
        return _practice_review(day)
    elif day == 8 or '进程管理' in topic_lower or 'ps' in topic_lower or 'top' in topic_lower:
        return _practice_process()
    elif day == 9 or '进程控制' in topic_lower or 'kill' in topic_lower:
        return _practice_process_control()
    elif day == 10 or 'systemd' in topic_lower or '服务' in topic_lower:
        return _practice_systemd()
    elif day == 11 or '监控' in topic_lower or 'uptime' in topic_lower:
        return _practice_monitoring()
    elif day == 12 or '磁盘' in topic_lower or 'fdisk' in topic_lower:
        return _practice_disk()
    elif day == 13 or '日志' in topic_lower or 'journalctl' in topic_lower:
        return _practice_log_mgmt()
    elif day == 15 or ('shell' in topic_lower and '基础' in topic_lower):
        return _practice_shell_basics()
    elif day == 16 or '条件' in topic_lower or '判断' in topic_lower:
        return _practice_shell_condition()
    elif day == 17 or '循环' in topic_lower:
        return _practice_shell_loop()
    elif day == 18 or '函数' in topic_lower:
        return _practice_shell_function()
    elif day == 28:
        return _practice_final_review()
    elif day >= 29 and day <= 42:
        return _practice_networking(day)
    elif day >= 43 and day <= 63:
        return _practice_python(day)
    elif day >= 64 and day <= 70:
        return _practice_go(day)
    elif day >= 71 and day <= 84:
        return _practice_docker(day)
    elif day >= 85 and day <= 99:
        return _practice_k8s(day)
    elif day >= 100 and day <= 114:
        return _practice_aws(day)
    elif day >= 115 and day <= 120:
        return _practice_terraform(day)
    elif day >= 121 and day <= 127:
        return _practice_ansible(day)
    elif day >= 128 and day <= 134:
        return _practice_observability(day)
    elif day >= 135 and day <= 141:
        return _practice_logging_tracing(day)
    elif day >= 142 and day <= 148:
        return _practice_cicd(day)
    elif day >= 149 and day <= 155:
        return _practice_devops_advanced(day)
    elif day >= 156 and day <= 162:
        return _practice_sre_core(day)
    elif day >= 163 and day <= 170:
        return _practice_interview(day)
    else:
        return _practice_generic(topic)


def _practice_linux_intro():
    return """### 练习 1：企业级服务器初始化

**场景**：新购 3 台云服务器，30 分钟内完成初始化并交付。

```bash
#!/bin/bash
# enterprise_server_init.sh
set -euo pipefail

# 1. 系统更新与安全补丁
apt update && apt upgrade -y

# 2. 创建运维用户（禁止 root 直接登录）
useradd -m -s /bin/bash -G sudo ops-admin

# 3. SSH 安全加固
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd

# 4. 防火墙
ufw default deny incoming
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp
ufw enable

# 5. 安装监控基础
apt install -y htop iotop net-tools strace lsof sysstat

echo "服务器初始化完成"
```

### 练习 2：故障排查挑战

**场景**：生产服务器 CPU 持续 100%，10 分钟内定位根因。

```bash
# 定位高 CPU 进程
ps aux --sort=-%cpu | head -5
# 检查进程状态
ps -eo pid,user,%cpu,%mem,stat,comm | sort -k3 -rn | head -10
# 跟踪系统调用
strace -p <PID> -c -s 100
# 检查 IO 等待
iostat -x 1 3
```

### 练习 3：性能基准测试

```bash
# 磁盘性能
dd if=/dev/zero of=/tmp/test bs=1M count=1024 oflag=direct
# 内存性能
sysbench memory --memory-block-size=1M --memory-total-size=10G run
```
"""


def _practice_fhs():
    return """### 练习 1：磁盘空间紧急清理

**场景**：生产服务器 / 分区使用率 98%，立即清理并防止再次发生。

```bash
# 快速定位占用最大的目录
du -sh /* 2>/dev/null | sort -rh | head -10

# 查找大文件（> 100MB）
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null | sort -k5 -rh

# 查找已删除但未释放的文件
lsof +L1 | sort -k7 -rh | head -10

# 安全清理日志
> /var/log/nginx/access.log
journalctl --vacuum-size=500M
apt clean && apt autoremove -y
```

### 练习 2：inode 耗尽排查

```bash
df -i
# 找出大量小文件的目录
for d in /*; do
    count=$(find "$d" -xdev -type f 2>/dev/null | wc -l)
    echo "$count $d"
done | sort -rn | head -10
```

### 练习 3：目录结构审计

```bash
# 检查敏感文件权限
find /etc -name "*.conf" -perm /o+r -ls
find / -name "*.pem" -o -name "*id_rsa*" 2>/dev/null
```
"""


def _practice_file_ops():
    return """### 练习 1：安全批量文件操作

**场景**：备份并迁移 /data/old_app 到 /data/new_app，涉及 10000+ 文件。

```bash
# 使用 rsync 替代 cp（更安全、可断点续传）
BACKUP="/data/backup_$(date +%Y%m%d_%H%M%S)"
rsync -av --progress /data/old_app/ "$BACKUP/"

# 验证备份完整性
diff <(find /data/old_app -type f -exec md5sum {} + | sort) \\
     <(find "$BACKUP" -type f -exec md5sum {} + | sort)

# 安全删除（先 dry run）
rsync -av --delete --dry-run /empty_dir/ /data/old_app/
```

### 练习 2：日志文件生命周期管理

```bash
# 创建 30 天模拟日志
mkdir -p /var/log/test_app
for i in $(seq 1 30); do
    date_str=$(date -d "2026-01-$(printf '%02d' $i)" +%Y-%m-%d)
    echo "[$date_str] INFO: Application started" > "/var/log/test_app/app_${date_str}.log"
done

# 查找 7 天前的日志并压缩
find /var/log/test_app -name "*.log" -mtime +7 -exec gzip {} +
# 删除 30 天前的压缩日志
find /var/log/test_app -name "*.gz" -mtime +30 -delete
```
"""


def _practice_text_processing():
    return """### 练习 1：生产日志分析报告

**场景**：生成 Nginx 每日运营报告，用于早会汇报。

```bash
#!/bin/bash
LOG="/var/log/nginx/access.log"
echo "===== Nginx 日报 $(date +%Y-%m-%d) ====="
echo "总请求数: $(wc -l < $LOG)"
echo "独立 IP:  $(awk '{print $1}' $LOG | sort -u | wc -l)"
echo ""
echo "状态码分布:"
awk '{print $9}' $LOG | sort | uniq -c | sort -rn
echo ""
echo "Top 10 IP:"
awk '{print $1}' $LOG | sort | uniq -c | sort -rn | head -10
echo ""
echo "5xx 错误:"
awk '$9 >= 500 {printf "  %s %s %s\\n", $1, $4, $7}' $LOG | head -20
```

### 练习 2：安全审计脚本

```bash
#!/bin/bash
AUTH_LOG="/var/log/auth.log"
echo "暴力破解尝试:"
grep "Failed password" $AUTH_LOG | \\
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | \\
    awk '$1 > 10 {printf "  %s: %d 次\\n", $2, $1}'

echo "最近登录:"
last -a | head -20
```

### 练习 3：配置文件批量修改

```bash
# 批量替换配置文件中的端口
find /etc/nginx -name "*.conf" -exec sed -i 's/listen 80/listen 8080/' {} +

# 删除所有空行和注释
sed -i '/^#/d; /^$/d' /etc/nginx/nginx.conf
```
"""


def _practice_permissions():
    return """### 练习 1：Web 服务权限配置

**场景**：部署新 Web 应用，配置严格的权限模型。

```bash
# 创建应用专用用户和组
groupadd webapp
useradd -r -g webapp -s /sbin/nologin -d /var/www/webapp webapp

# 设置目录权限（最小权限原则）
mkdir -p /var/www/webapp/{public,private,logs,tmp}
chown -R webapp:webapp /var/www/webapp
chmod 750 /var/www/webapp
chmod 640 /var/www/webapp/.env
chmod 600 /var/www/webapp/.env  # 敏感配置

# 上传目录（SGID 继承用户组）
chmod 2775 /var/www/webapp/public/uploads
```

### 练习 2：权限安全审计

```bash
#!/bin/bash
echo "777 权限文件（安全隐患）:"
find /var/www -type f -perm 777 -ls 2>/dev/null

echo "SUID 文件:"
find / -type f -perm /4000 -ls 2>/dev/null

echo "SSH 密钥权限:"
for f in /home/*/.ssh/id_rsa; do
    [ -f "$f" ] && {
        perm=$(stat -c %a "$f")
        [ "$perm" != "600" ] && echo "  $f: $perm (应为 600)"
    }
done
```
"""


def _practice_user_mgmt():
    return """### 练习 1：企业用户生命周期管理

```bash
#!/bin/bash
# 入职：创建用户
create_user() {
    local username=$1 department=$2
    useradd -m -s /bin/bash -c "$department" "$username"
    case "$department" in
        dev) usermod -aG developers,docker "$username" ;;
        ops) usermod -aG operators,docker,sudo "$username" ;;
    esac
    chage -M 90 -m 7 -W 14 "$username"
}

# 离职：安全清理
offboard_user() {
    local username=$1
    pkill -u "$username" 2>/dev/null || true
    usermod -L "$username"
    tar -czf "/backup/users/${username}_$(date +%Y%m%d).tar.gz" /home/$username
    userdel -r "$username"
}
```

### 练习 2：sudo 权限审计

```bash
grep -E '^%?sudo' /etc/sudoers
visudo -c
grep -r "NOPASSWD" /etc/sudoers /etc/sudoers.d/
grep "sudo:" /var/log/auth.log | tail -20
```
"""


def _practice_review(day):
    if day == 14:
        return """### 综合实战：从零部署生产 LAMP 环境

**任务**：2 小时内从 0 到可交付的完整配置。

#### 1. 系统初始化

```bash
apt update && apt upgrade -y
apt install -y apache2 mysql-server php libapache2-mod-php php-mysql
ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
```

#### 2. 数据库安全

```bash
mysql -e "CREATE DATABASE production CHARACTER SET utf8mb4;"
mysql -e "CREATE USER 'app'@'localhost' IDENTIFIED BY 'StrongPass123!';"
mysql -e "GRANT SELECT,INSERT,UPDATE,DELETE ON production.* TO 'app'@'localhost';"
```

#### 3. 配置日志轮转

```bash
cat > /etc/logrotate.d/myapp << 'EOF'
/var/log/apache2/*.log {
    daily
    rotate 30
    compress
    missingok
    postrotate
        systemctl reload apache2 > /dev/null 2>&1 || true
    endscript
}
EOF
```

#### 4. 健康检查脚本

```bash
cat > /usr/local/bin/health_check.sh << 'SCRIPT'
#!/bin/bash
for svc in apache2 mysql; do
    if ! systemctl is-active --quiet "$svc"; then
        echo "CRIT: $svc down" | mail -s "Alert" admin@example.com
        systemctl restart "$svc"
    fi
done
SCRIPT
chmod +x /usr/local/bin/health_check.sh
echo "*/5 * * * * /usr/local/bin/health_check.sh" | crontab -
```
"""
    else:
        return """### 综合实战：从零部署生产服务器

#### 1. 系统初始化（30 分钟）

```bash
apt update && apt upgrade -y
apt install -y curl wget vim git htop tree net-tools dnsutils sysstat
timedatectl set-timezone Asia/Shanghai
ufw default deny incoming && ufw allow 22/tcp && ufw enable
```

#### 2. 安全加固（30 分钟）

```bash
# SSH 加固 + Fail2ban
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
apt install -y fail2ban
# 内核安全参数
echo "net.ipv4.tcp_syncookies = 1" >> /etc/sysctl.conf
sysctl -p
```

#### 3. 监控部署（30 分钟）

```bash
# 启用 sysstat
sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat

# 创建健康检查
cat > /usr/local/bin/health_check.sh << 'SCRIPT'
#!/bin/bash
services="nginx ssh"
for svc in $services; do
    systemctl is-active --quiet $svc || \\
        echo "CRIT: $svc down"
done
SCRIPT
chmod +x /usr/local/bin/health_check.sh
echo "*/5 * * * * /usr/local/bin/health_check.sh" | crontab -
```
"""


def _practice_process():
    return """### 练习 1：生产环境进程排查

**场景**：服务器响应缓慢，5 分钟内定位问题。

```bash
#!/bin/bash
echo "===== 进程排查报告 $(date) ====="
echo "负载: $(uptime)"
echo ""
echo "Top 10 CPU:"
ps aux --sort=-%cpu | head -11
echo ""
echo "僵尸进程:"
zombies=$(ps aux | awk '$8 ~ /Z/' | wc -l)
echo "数量: $zombies"
[ "$zombies" -gt 0 ] && ps aux | awk '$8 ~ /Z/'
echo ""
echo "进程状态分布:"
ps aux | awk '{print $8}' | sort | uniq -c | sort -rn
```

### 练习 2：进程树分析

```bash
pstree -p -a
ps -o pid,ppid,cmd -f --forest | grep -A5 nginx
cat /proc/$(pgrep nginx | head -1)/status
```
"""


def _practice_process_control():
    return """### 练习 1：优雅的服务重启

```bash
#!/bin/bash
SERVICE="nginx"

# 先测试配置
nginx -t || { echo "配置测试失败"; exit 1; }

# 优雅重启（对比 kill -9）
systemctl reload $SERVICE  # 连接不中断
kill -HUP $(cat /var/run/$SERVICE.pid)  # 发送 SIGHUP
```

### 练习 2：进程信号实战

```bash
# SIGTERM vs SIGKILL
sleep 1000 &
PID=$!
kill -15 $PID  # 优雅终止
sleep 1
kill -0 $PID 2>/dev/null && kill -9 $PID  # 强制终止

# SIGSTOP 和 SIGCONT
sleep 1000 &
PID=$!
kill -STOP $PID
ps -p $PID -o pid,stat
kill -CONT $PID
kill $PID
```
"""


def _practice_systemd():
    return """### 练习 1：编写企业级 systemd 服务

```bash
#!/bin/bash
# 创建应用
mkdir -p /opt/myapp/{logs,config}
useradd -r -s /sbin/nologin myapp

# 创建服务单元
cat > /etc/systemd/system/myapp.service << 'EOF'
[Unit]
Description=My Application Server
After=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
ExecStart=/usr/bin/python3 /opt/myapp/app.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
StartLimitInterval=300
StartLimitBurst=5

# 安全加固
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now myapp
systemctl status myapp
```

### 练习 2：启动性能分析

```bash
systemd-analyze
systemd-analyze blame | head -20
systemd-analyze critical-chain
systemd-analyze plot > /tmp/startup.svg
```
"""


def _practice_monitoring():
    return """### 练习 1：运维实时监控脚本

```bash
#!/bin/bash
# ops_dashboard.sh
while true; do
    clear
    echo "=== SRE OPS DASHBOARD $(date '+%H:%M:%S') ==="
    load=$(cat /proc/loadavg | awk '{print $1", "$2", "$3}')
    cpu_idle=$(vmstat 1 2 | tail -1 | awk '{print $15}')
    echo "CPU Load: $load | Idle: ${cpu_idle}%"
    echo "Memory: $(free -h | grep Mem)"
    echo "Disk:"
    df -h / /data 2>/dev/null | tail -n+2 | \\
        awk '{printf "  %-15s %s/%s (%s)\\n", $6, $3, $2, $5}'
    echo "Top Processes:"
    ps aux --sort=-%cpu | head -4 | tail -3 | \\
        awk '{printf "  PID:%-8s CPU:%5s%% MEM:%5s%% %s\\n", $2, $3, $4, $11}'
    echo "Services:"
    for svc in nginx mysql docker ssh; do
        status=$(systemctl is-active $svc 2>/dev/null)
        [ "$status" = "active" ] && echo "  [OK] $svc" || echo "  [!!] $svc"
    done
    sleep 5
done
```

### 练习 2：历史数据回溯

```bash
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat
systemctl restart sysstat
sar -u          # CPU 历史
sar -r          # 内存历史
sar -d -p       # 磁盘 IO
sar -u -s 14:00 -e 15:00  # 特定时间段
```
"""


def _practice_disk():
    return """### 练习 1：LVM 磁盘管理

```bash
# 创建 LVM
sudo pvcreate /dev/sdb
sudo vgcreate vg_data /dev/sdb
sudo lvcreate -L 100G -n lv_app vg_data
sudo mkfs.ext4 /dev/vg_data/lv_app
sudo mount /dev/vg_data/lv_app /data

# 在线扩容
sudo lvextend -L +50G /dev/vg_data/lv_app
sudo resize2fs /dev/vg_data/lv_app

# 验证
df -h /data
lvs
```

### 练习 2：磁盘健康检查

```bash
#!/bin/bash
echo "磁盘健康检查:"
# SMART 状态
for disk in /dev/sd?; do
    [ -b "$disk" ] && smartctl -H "$disk" 2>/dev/null | grep -i "overall"
done
# IO 性能
iostat -x 1 3
# 高使用率警告
df -h | awk 'NR>1 {gsub(/%/,"",$5); if($5>80) print "WARN: "$6" at "$5"%"}'
```
"""


def _practice_log_mgmt():
    return """### 练习 1：日志生命周期管理

```bash
#!/bin/bash
# 配置 Nginx 日志轮转
cat > /etc/logrotate.d/nginx-custom << 'EOF'
/var/log/nginx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}
EOF

# 配置 journal 限制
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/limits.conf << 'EOF'
[Journal]
SystemMaxUse=500M
MaxRetentionSec=30day
EOF
systemctl restart systemd-journald
```

### 练习 2：安全日志监控

```bash
#!/bin/bash
echo "暴力破解 (过去 1 小时):"
grep "Failed password" /var/log/auth.log | \\
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | \\
    awk '$1 > 5 {printf "  IP: %-15s 失败: %d\\n", $2, $1}'

echo "非工作时间登录:"
grep "Accepted" /var/log/auth.log | \\
    awk -F'[ :]' '{if ($4 >= 22 || $4 < 6) print "  "$0}'
```
"""


def _practice_shell_basics():
    return """### 练习 1：每日系统报告（自动邮件）

```bash
#!/bin/bash
# daily_report.sh
{
    echo "===== 系统报告 $(hostname) ====="
    echo "时间: $(date)"
    echo ""
    echo "CPU & 负载:"
    uptime
    echo ""
    echo "内存:"
    free -h
    echo ""
    echo "磁盘:"
    df -h | grep -v tmpfs
    echo ""
    echo "Top 5 CPU:"
    ps aux --sort=-%cpu | head -6
    echo ""
    echo "服务状态:"
    for svc in nginx mysql docker ssh; do
        status=$(systemctl is-active $svc 2>/dev/null)
        [ "$status" = "active" ] && echo "  [OK] $svc" || echo "  [!!] $svc"
    done
} > /tmp/report_$(date +%Y%m%d).txt
# mail -s "System Report $(hostname)" ops@example.com < /tmp/report.txt
```

### 练习 2：服务健康检查

```bash
#!/bin/bash
set -euo pipefail
for svc in nginx mysql docker; do
    if systemctl is-active --quiet "$svc"; then
        echo "OK: $svc running"
    else
        echo "CRIT: $svc stopped - restarting..."
        systemctl restart "$svc" || echo "FAIL: restart failed"
    fi
done
```
"""


def _practice_shell_condition():
    return """### 练习 1：智能健康检查（带阈值告警）

```bash
#!/bin/bash
set -euo pipefail
CPU_WARN=70; CPU_CRIT=90
MEM_WARN=80; MEM_CRIT=95

cpu_idle=$(vmstat 1 2 | tail -1 | awk '{print $15}')
cpu_used=$((100 - cpu_idle))
if [ $cpu_used -gt $CPU_CRIT ]; then
    echo "CRIT: CPU ${cpu_used}% > ${CPU_CRIT}%"
elif [ $cpu_used -gt $CPU_WARN ]; then
    echo "WARN: CPU ${cpu_used}% > ${CPU_WARN}%"
else
    echo "OK: CPU ${cpu_used}%"
fi

mem_pct=$(free | awk 'NR==2 {printf "%d", $3/$2*100}')
if [ $mem_pct -gt $MEM_CRIT ]; then
    echo "CRIT: Memory ${mem_pct}% > ${MEM_CRIT}%"
elif [ $mem_pct -gt $MEM_WARN ]; then
    echo "WARN: Memory ${mem_pct}% > ${MEM_WARN}%"
else
    echo "OK: Memory ${mem_pct}%"
fi
```
"""


def _practice_shell_loop():
    return """### 练习 1：批量服务器巡检

```bash
#!/bin/bash
SERVERS=("web01" "web02" "db01" "cache01")
for server in "${SERVERS[@]}"; do
    echo "=== $server ==="
    result=$(ssh -o ConnectTimeout=5 "$server" "uptime; df -h / | tail -1" 2>&1)
    echo "$result"
    echo ""
done
```

### 练习 2：并行巡检

```bash
#!/bin/bash
TEMP_DIR=$(mktemp -d)
SERVERS=("web01" "web02" "web03" "db01" "db02")
for server in "${SERVERS[@]}"; do
    (ssh -o ConnectTimeout=5 "$server" "uptime; df -h /" > "$TEMP_DIR/$server" 2>&1) &
done
wait
for server in "${SERVERS[@]}"; do
    echo "=== $server ==="; cat "$TEMP_DIR/$server"; echo ""
done
rm -rf "$TEMP_DIR"
```
"""


def _practice_shell_function():
    return """### 练习 1：运维函数库

```bash
#!/bin/bash
# ops_lib.sh
log() {
    local level=$1; shift
    case $level in
        INFO)  echo -e "\\033[32m[$(date '+%H:%M:%S')] [INFO] $*\\033[0m" ;;
        WARN)  echo -e "\\033[33m[$(date '+%H:%M:%S')] [WARN] $*\\033[0m" ;;
        ERROR) echo -e "\\033[31m[$(date '+%H:%M:%S')] [ERROR] $*\\033[0m" ;;
    esac
}

retry() {
    local max=${1:-3}; local delay=${2:-5}; shift 2
    for i in $(seq 1 $max); do
        log INFO "尝试 $i/$max: $*"
        eval "$@" && return 0
        sleep $delay
    done
    log ERROR "失败（重试 $max 次）: $*"
    return 1
}

# 使用
# source ./ops_lib.sh
# retry 3 5 "curl -f http://localhost/health"
```
"""


def _practice_final_review():
    return """### 综合能力评估

#### 实操测试 1：从零部署 Web 服务（限时 15 分钟）

```bash
# 要求：
# 1. 创建用户并配置 SSH
# 2. 安装并配置 Nginx
# 3. 设置防火墙
# 4. 配置日志轮转
# 5. 编写健康检查脚本
```

#### 实操测试 2：日志分析

```bash
# 1. 分析 Nginx 日志：Top 10 IP、5xx 错误率、平均响应时间
# 2. 检查 auth.log：暴力破解检测
# 3. 系统磁盘：找出占用最大的 5 个目录
```

#### 实操测试 3：故障排查

```bash
# 模拟场景：
# 1. 服务无法启动 → 排查端口占用、配置错误
# 2. 磁盘 100% → 定位并清理
# 3. 进程异常 → 定位高 CPU/内存进程
```

#### 达标标准
- [ ] 能不查阅文档完成 80% 常用命令
- [ ] 能独立排查常见 Linux 问题
- [ ] 能编写基本的运维 Shell 脚本
- [ ] 理解系统架构和各组件关系
"""


def _practice_networking(day):
    return f"""### 练习 1：网络故障排查脚本

**场景**：用户报告"网站访问慢"，系统化排查。

```bash
#!/bin/bash
TARGET="example.com"
echo "=== 网络排查: $TARGET ==="

# 1. DNS
echo "DNS: $(dig +short $TARGET A 2>/dev/null || echo 'FAILED')"

# 2. 连通性
ping -c 3 -W 2 $TARGET 2>&1 | tail -1

# 3. 路由
traceroute -m 15 -w 2 $TARGET 2>/dev/null | head -10

# 4. 端口
for port in 80 443; do
    timeout 2 bash -c "echo > /dev/tcp/$TARGET/$port" 2>/dev/null && \\
        echo "端口 $port: OK" || echo "端口 $port: FAIL"
done

# 5. HTTP
curl -s -o /dev/null -w "HTTP: %{{http_code}}, Time: %{{time_total}}s\\n" "http://$TARGET"

# 6. TCP 状态
ss -tan | awk 'NR>1 {{print $1}}' | sort | uniq -c | sort -rn
```

### 练习 2：抓包分析

```bash
# 抓取 HTTP 流量
sudo tcpdump -i any -n port 80 -A 2>/dev/null | head -50

# 保存到文件用 Wireshark 分析
sudo tcpdump -i any -n port 443 -w /tmp/capture.pcap

# 分析 TCP 握手
sudo tcpdump -i any -n 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0' -c 10
```
"""


def _practice_python(day):
    return f"""### 练习 1：主机监控脚本

```python
#!/usr/bin/env python3
import psutil, json, datetime

def check_system():
    report = {{
        "timestamp": datetime.datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {{
            "total_gb": round(psutil.virtual_memory().total / 1e9, 2),
            "used_percent": psutil.virtual_memory().percent
        }},
        "disk": {{}},
    }}
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            report["disk"][part.mountpoint] = {{
                "total_gb": round(usage.total / 1e9, 2),
                "used_percent": usage.percent
            }}
        except PermissionError:
            pass
    return report

data = check_system()
print(json.dumps(data, indent=2))

# 告警
if data["cpu_percent"] > 80:
    print("ALERT: High CPU usage!")
if data["memory"]["used_percent"] > 90:
    print("ALERT: High memory usage!")
```

### 练习 2：日志分析工具

```python
import re
from collections import Counter

def analyze_nginx_log(log_file):
    pattern = r'(\\S+) \\S+ \\S+ \\[(.+?)\\] "(\\S+)" (\\d+)'
    ips = Counter()
    status_codes = Counter()
    with open(log_file) as f:
        for line in f:
            m = re.match(pattern, line)
            if m:
                ips[m.group(1)] += 1
                status_codes[m.group(4)] += 1
    print("Top 10 IPs:", ips.most_common(10))
    print("Status codes:", dict(status_codes))

analyze_nginx_log("/var/log/nginx/access.log")
```
"""


def _practice_go(day):
    return f"""### 练习 1：HTTP 健康检查服务

```go
package main

import (
    "encoding/json"
    "net/http"
    "runtime"
    "time"
)

type HealthResponse struct {
    Status    string    `json:"status"`
    Uptime    string    `json:"uptime"`
    GoVersion string    `json:"go_version"`
    Goroutines int      `json:"goroutines"`
}

var startTime = time.Now()

func healthHandler(w http.ResponseWriter, r *http.Request) {
    resp := HealthResponse{{
        Status:     "ok",
        Uptime:     time.Since(startTime).String(),
        GoVersion:  runtime.Version(),
        Goroutines: runtime.NumGoroutine(),
    }}
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func main() {
    http.HandleFunc("/health", healthHandler)
    http.ListenAndServe(":8080", nil)
}
```

```bash
go run main.go
curl http://localhost:8080/health
```
"""


def _practice_docker(day):
    return f"""### 练习 1：多阶段构建优化

```dockerfile
# Build stage
FROM golang:1.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o myapp

# Runtime stage
FROM alpine:3.18
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/myapp /usr/local/bin/myapp
USER 1000:1000
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s \\
    CMD wget -qO- http://localhost:8080/health || exit 1
CMD ["myapp"]
```

### 练习 2：docker-compose 编排

```yaml
version: "3.8"
services:
  web:
    build: .
    ports: ["8080:8080"]
    depends_on: [db, redis]
    environment:
      - DB_HOST=db
      - REDIS_URL=redis://redis:6379
  db:
    image: postgres:15-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
volumes:
  pgdata:
```
"""


def _practice_k8s(day):
    return f"""### 练习 1：部署完整应用

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: web-app
        image: myapp:latest
        ports:
        - containerPort: 8080
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
```

```bash
kubectl apply -f deployment.yaml
kubectl get pods -w
kubectl rollout status deployment/web-app
kubectl rollout undo deployment/web-app  # 回滚
```
"""


def _practice_aws(day):
    return f"""### 练习 1：AWS CLI 自动化

```bash
# 查询实例状态
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]' --output table

# 创建 S3 桶并设置生命周期
aws s3api create-bucket --bucket my-backup-bucket --region us-east-1
aws s3api put-bucket-lifecycle-configuration --bucket my-backup-bucket \\
    --lifecycle-configuration '{
        "Rules": [{{
            "ID": "TransitionToGlacier",
            "Status": "Enabled",
            "Prefix": "",
            "Transitions": [{{"Days": 90, "StorageClass": "GLACIER"}}]
        }}]
    }'
```

### 练习 2：高可用架构设计

- 设计多 AZ 部署：ALB + ASG（跨 2 个 AZ）+ RDS Multi-AZ
- 配置 CloudWatch 告警
- 设置自动备份策略
"""


def _practice_terraform(day):
    return f"""### 练习 1：Terraform 基础设施

```hcl
provider "aws" {{
  region = "us-east-1"
}}

resource "aws_instance" "web" {{
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  vpc_security_group_ids = [aws_security_group.web.id]

  tags = {{
    Name        = "web-server"
    Environment = "production"
  }}
}}

resource "aws_security_group" "web" {{
  ingress {{
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }}
}}

output "public_ip" {{
  value = aws_instance.web.public_ip
}}
```

```bash
terraform init
terraform plan
terraform apply
terraform destroy  # 清理
```
"""


def _practice_ansible(day):
    return f"""### 练习 1：Ansible 自动化部署

```yaml
# deploy.yml
- hosts: webservers
  become: true
  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present

    - name: Configure nginx
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      notify: Restart nginx

    - name: Enable nginx
      service:
        name: nginx
        state: started
        enabled: true

  handlers:
    - name: Restart nginx
      service:
        name: nginx
        state: restarted
```

```bash
ansible-playbook -i hosts deploy.yml
```
"""


def _practice_observability(day):
    return f"""### 练习 1：Prometheus + Grafana 部署

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
  - job_name: 'app'
    static_configs:
      - targets: ['localhost:8080']
```

```promql
# PromQL 查询
# CPU 使用率
100 - (avg(rate(node_cpu_seconds_total{{mode="idle"}}[5m])) * 100)

# 内存使用率
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 磁盘使用率
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100

# QPS
rate(http_requests_total[5m])

# P99 延迟
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```
"""


def _practice_logging_tracing(day):
    return f"""### 练习 1：ELK 日志平台

```bash
# Filebeat 配置
cat > /etc/filebeat/filebeat.yml << 'EOF'
filebeat.inputs:
  - type: log
    paths:
      - /var/log/nginx/*.log
    fields:
      service: nginx
output.elasticsearch:
  hosts: ["localhost:9200"]
EOF

# 查询示例（Kibana/ES）
curl -X GET "localhost:9200/filebeat-*/_search" -H 'Content-Type: application/json' -d'
{{
  "query": {{ "match": {{ "http.response.status_code": 500 }} }},
  "size": 10
}}'
```

### 练习 2：Loki 日志

```bash
# LogQL 查询
# 错误日志
{{app="nginx"}} |= "error"

# 按状态码统计
sum by (status) (count_over_time({app="nginx"} |= "" [5m]))
```
"""


def _practice_cicd(day):
    return f"""### 练习 1：GitHub Actions CI/CD

```yaml
name: CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest --cov=.

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:${{ github.sha }} .
      - run: docker push myapp:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
      - run: kubectl set image deployment/web-app app=myapp:${{ github.sha }}
```
"""


def _practice_devops_advanced(day):
    return f"""### 练习 1：ArgoCD GitOps

```yaml
# ArgoCD Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: web-app
spec:
  project: default
  source:
    repoURL: https://github.com/org/k8s-manifests.git
    targetRevision: main
    path: manifests/web-app
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### 练习 2：金丝雀发布

```bash
# Argo Rollouts
kubectl argo rollouts set image web-app \\
    app=myapp:v2.0.0
kubectl argo rollouts promote web-app
kubectl argo rollouts abort web-app  # 发现问题立即中止
```
"""


def _practice_sre_core(day):
    return f"""### 练习 1：定义 SLO 和错误预算

**场景**：为一个 API 服务定义 SLO。

```
服务：REST API
SLO：
  - 可用性：99.95%（每月最多 21.6 分钟不可用）
  - 延迟：P99 < 500ms
  - 错误率：5xx < 0.1%

错误预算：
  - 月度预算：21.6 分钟
  - 已消耗 80% → 暂停新功能发布，专注稳定性
  - 剩余 4.3 分钟
```

### 练习 2：编写 RCA 报告

```markdown
# 事故报告：数据库连接池耗尽

## 时间线
- 14:00 - 监控告警：API 响应时间 > 10s
- 14:05 - 确认：DB 连接池 100% 使用
- 14:10 - 临时修复：重启应用服务
- 14:15 - 恢复正常

## 根因分析（5 Why）
1. 为什么 API 慢？→ DB 连接池耗尽
2. 为什么连接池耗尽？→ 慢查询阻塞连接
3. 为什么有慢查询？→ 新增的索引未优化
4. 为什么没发现？→ 测试环境数据量不足
5. 为什么测试数据少？→ 没有数据脱敏导入流程

## 改进措施
- [ ] 添加慢查询告警（负责人：XXX，截止日期：XX）
- [ ] 建立测试数据同步流程
- [ ] 代码审查增加 SQL 审查项
```
"""


def _practice_interview(day):
    return f"""### 模拟面试

#### Linux 面试

1. 解释 Linux 启动流程（BIOS → Bootloader → Kernel → systemd）
2. 进程状态 R/S/D/Z 各代表什么？Z 状态如何处理？
3. Load Average 的含义？4 核机器 load=8 说明什么？
4. 如何排查磁盘 IO 高的问题？
5. 文件描述符是什么？如何调整 ulimit？

#### 网络面试

1. 输入 URL 到页面显示的完整过程
2. TCP 三次握手为什么是三次？两次可以吗？
3. TIME_WAIT 状态的作用？过多怎么办？
4. HTTP 200/301/302/403/404/500/502/503 的含义
5. DNS 解析的完整过程

#### K8s 面试

1. Pod 的生命周期和探针的区别
2. Service 四种类型及使用场景
3. 如何排查 Pod 一直 Restart 的问题？
4. Deployment 滚动更新的过程
5. PV/PVC/StorageClass 的关系
"""


def _practice_generic(topic):
    return f"""### 练习 1：{topic} 实战

**场景**：将 {topic} 应用到生产环境中。

```bash
# 1. 基础操作 - 查阅官方文档完成
# 2. 进阶操作 - 结合实际场景
# 3. 故障排查 - 模拟常见问题
```

### 练习 2：自动化脚本

```bash
#!/bin/bash
set -euo pipefail
# TODO: 根据主题实现具体的自动化逻辑
echo "自动化任务完成"
```

### 练习 3：监控配置

```bash
# 为 {topic} 配置监控指标
# 设置告警阈值
# 编写健康检查脚本
```
"""
