
# ============ Additional Content Generators ============
# Added during review and revision - covers topics that previously fell back to generic template

def generate_monitoring_content(day, topic):
    """System monitoring commands - Day 11"""
    return """### 1. 系统负载监控

#### 1.1 uptime 与 Load Average

Load Average 表示 1/5/15 分钟内的平均负载（运行队列中的进程数）。

**SRE 经验法则**：load < CPU 核数 = 健康；load > CPU 核数 = 过载。

```bash
$ uptime
 14:30:25 up 30 days, 2:15,  load average: 0.50, 1.20, 0.80
```

**SRE 实战排查**：
```bash
# 生产告警：load 15.2（4 核机器）→ 严重过载！

# 定位高 CPU 进程
ps aux --sort=-%cpu | head -10

# 查看进程状态分布
ps aux | awk '{print $8}' | sort | uniq -c
# D（不可中断睡眠）太多 = IO 等待
# R（运行）太多 = CPU 瓶颈

# 查看 IO 等待
vmstat 1 5
# wa 高 = 磁盘瓶颈
```

#### 1.2 free — 内存监控

**关键**：看 `available` 而非 `free`！Linux 会用空闲内存做缓存。

```bash
$ free -h
              total   used   free   buff/cache   available
Mem:           16Gi   8.2Gi  1.1Gi     6.7Gi       7.3Gi
```

```bash
# 真正的内存问题：available 很低 + swap 持续增加 = OOM 风险
dmesg | grep -i "out of memory"
dmesg | grep -i "killed process"
```

#### 1.3 df/du — 磁盘

```bash
df -h                    # 磁盘使用率
df -i                    # inode 使用率
du -sh /* 2>/dev/null | sort -rh | head -10  # 大目录
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null  # 大文件
```

#### 1.4 vmstat — 综合性能

```bash
vmstat 1 5
# r > CPU 核数 = CPU 瓶颈
# b > 0 = 磁盘瓶颈
# si/so > 0 = 内存不足
# wa 高 = IO 等待
```

#### 1.5 sar — 历史数据回溯

```bash
# 启用 sysstat
sudo sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat

sar -u    # CPU 历史
sar -r    # 内存历史
sar -d    # 磁盘 IO 历史
sar -n DEV  # 网络历史
```

---

### 2. SRE 实战：一键健康检查脚本

```bash
#!/bin/bash
echo "=== 健康检查 $(date) ==="
echo "负载: $(uptime | awk -F'load average:' '{print $2}')"
echo "内存:"; free -h | grep Mem
echo "磁盘:"; df -h / | tail -1
echo "Top CPU:"; ps aux --sort=-%cpu | head -4
echo "Top MEM:"; ps aux --sort=-%mem | head -4
echo "IO 等待:"; vmstat 1 1 | tail -1
echo "错误日志:"; journalctl -p err --since "5 min ago" --no-pager | tail -3
```

---

### 3. 常见问题

| 问题 | 排查思路 |
|------|---------|
| Load 高但 CPU 使用率低 | 检查 vmstat 的 wa，可能是磁盘瓶颈 |
| 内存告警但 available 充足 | 正常！Linux 用空闲内存做缓存 |
| Swap 持续增加 | 内存不足，排查内存泄漏 |
| 磁盘使用率持续增长 | 检查日志轮转配置、临时文件 |
"""


def generate_disk_content(day, topic):
    """Disk management - Day 12"""
    return """### 1. 磁盘设备与分区

#### 1.1 磁盘设备命名

| 类型 | 命名 | 说明 |
|------|------|------|
| SATA | `/dev/sda` | 传统磁盘 |
| NVMe | `/dev/nvme0n1` | 高速 SSD |
| 云盘 | `/dev/vda` | KVM 虚拟化 |

```bash
lsblk              # 查看磁盘和分区
sudo fdisk -l      # 详细信息
```

#### 1.2 分区与格式化

```bash
# MBR 分区（< 2TB）
sudo fdisk /dev/sdb
# n → p → 1 → Enter → Enter → w

# GPT 分区（> 2TB）
sudo parted /dev/sdb mklabel gpt
sudo parted /dev/sdb mkpart primary ext4 0% 100%

# 格式化
sudo mkfs.ext4 /dev/sdb1
```

#### 1.3 挂载管理

```bash
# 挂载
sudo mount /dev/sdb1 /data

# 开机自动挂载（编辑 /etc/fstab）
echo '/dev/sdb1 /data ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
sudo mount -a   # 测试（重要！）

# 查看挂载
findmnt /data
```

#### 1.4 LVM 逻辑卷

```bash
sudo pvcreate /dev/sdb /dev/sdc
sudo vgcreate vg_data /dev/sdb /dev/sdc
sudo lvcreate -L 100G -n lv_app vg_data
sudo mkfs.ext4 /dev/vg_data/lv_app

# 在线扩容
sudo lvextend -L +50G /dev/vg_data/lv_app
sudo resize2fs /dev/vg_data/lv_app
```

---

### 2. SRE 实战

**磁盘告警排查**：
```bash
# 1. 定位大目录
du -sh /* 2>/dev/null | sort -rh | head -5

# 2. inode 耗尽
df -i

# 3. 已删除但未释放的文件
lsof +L1

# 4. 找出 > 100MB 的文件
find / -type f -size +100M -exec ls -lh {} + 2>/dev/null
```
"""


def generate_log_mgmt_content(day, topic):
    """Log management - Day 13"""
    return """### 1. 日志体系

#### 1.1 重要日志文件

| 日志 | 用途 |
|------|------|
| `/var/log/syslog` | 系统日志（Ubuntu） |
| `/var/log/auth.log` | 认证/登录日志 |
| `/var/log/kern.log` | 内核日志 |
| `/var/log/nginx/` | Nginx 访问和错误日志 |
| `/var/log/journal/` | systemd journal |

#### 1.2 journalctl 高级用法

```bash
journalctl -f                          # 实时跟踪
journalctl -u nginx --since "1h ago"   # 服务日志
journalctl -p err                      # 错误级别
journalctl --disk-usage                # 占用空间
sudo journalctl --vacuum-size=500M    # 清理
```

#### 1.3 logrotate 日志轮转

```bash
# 查看现有配置
ls /etc/logrotate.d/

# 常用参数：
# daily/weekly/monthly  — 轮转频率
# rotate N              — 保留 N 个旧文件
# compress              — 压缩旧文件
# size 100M             — 超过此大小才轮转
# missingok             — 文件不存在不报错
```

---

### 2. SRE 实战

**日志爆满应急**：
```bash
# 不能直接 rm！（进程持有文件描述符，空间不释放）
# 正确做法：清空文件
> /var/log/nginx/access.log

# 安全审计：暴力破解检测
grep "Failed password" /var/log/auth.log | \
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -10

# Nginx 日志分析
awk '{print $9}' /var/log/nginx/access.log | sort | uniq -c | sort -rn
awk '$9 >= 500' /var/log/nginx/access.log | head -20
```
"""


def generate_shell_basics_content(day, topic):
    """Shell script basics - Day 15"""
    return """### 1. Shell 脚本入门

#### 1.1 第一个脚本

```bash
#!/bin/bash
echo "主机名: $(hostname)"
echo "当前用户: $(whoami)"
echo "当前时间: $(date)"
echo "内核版本: $(uname -r)"
```

#### 1.2 变量与引号

```bash
NAME="SRE Engineer"
echo "欢迎 $NAME"           # 双引号：变量展开
echo '欢迎 $NAME'           # 单引号：字面量
echo "时间: $(date)"        # 命令替换

# 安全做法（防止变量为空导致灾难）
DIR="/backup"
rm -rf "${DIR:?Variable DIR is not set}"/*

# 默认值
echo "服务器: ${SERVER:-localhost}"
```

#### 1.3 环境变量

```bash
export MY_VAR="hello"
env | grep MY_VAR
```

---

### 2. SRE 实战

**系统信息报告**：
```bash
#!/bin/bash
{
    echo "===== 系统报告 $(date) ====="
    echo "负载:"; uptime
    echo "内存:"; free -h
    echo "磁盘:"; df -h | grep -v tmpfs
    echo "Top CPU:"; ps aux --sort=-%cpu | head -4
} > "/tmp/report_$(date +%Y%m%d).txt"
```

**服务健康检查**：
```bash
#!/bin/bash
for svc in nginx mysql docker; do
    if systemctl is-active --quiet "$svc"; then
        echo "✅ $svc: running"
    else
        echo "❌ $svc: stopped"
    fi
done
```

**调试技巧**：`bash -x script.sh` / `set -euo pipefail`
"""


def generate_shell_condition_content(day, topic):
    """Shell conditionals - Day 16"""
    return """### 1. 条件判断基础

#### 1.1 文件测试

```bash
[ -f /etc/nginx/nginx.conf ]    # 文件存在
[ -d /var/log/nginx ]           # 目录存在
[ -s /var/log/syslog ]          # 文件非空
[ -r /etc/shadow ]              # 可读
[ -x /usr/bin/nginx ]           # 可执行
```

#### 1.2 字符串和数值比较

```bash
# 字符串
[ "$STATUS" = "running" ]
[ -z "$VAR" ]       # 空
[ -n "$VAR" ]       # 非空

# 数值：-eq(等于) -ne -gt(大于) -ge -lt -le
[ "$CPU" -gt 80 ]

# 推荐 [[ ]]（支持 && || 和正则）
[[ "$STATUS" == "running" && "$CPU" -gt 80 ]]
```

---

### 2. SRE 实战

**磁盘检查脚本**：
```bash
#!/bin/bash
set -euo pipefail
THRESHOLD=90
USAGE=$(df / | awk 'NR==2 {print $5}' | tr -d '%')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    echo "❌ 磁盘 ${USAGE}% > ${THRESHOLD}%，立即清理！"
elif [ "$USAGE" -gt 80 ]; then
    echo "⚠️ 磁盘 ${USAGE}%，请关注"
else
    echo "✅ 磁盘 ${USAGE}%，正常"
fi
```

**服务健康检查**：
```bash
#!/bin/bash
check_service() {
    local service=$1
    if ! systemctl is-active --quiet "$service"; then
        echo "❌ $service 未运行！尝试重启..."
        systemctl restart "$service" || {
            echo "❌ 重启失败！"
            return 1
        }
        echo "✅ $service 已重启"
    else
        echo "✅ $service 运行正常"
    fi
}
for svc in nginx mysql docker; do
    check_service "$svc"
done
```
"""


def generate_shell_loop_content(day, topic):
    """Shell loops - Day 17"""
    return """### 1. 循环基础

#### 1.1 for 循环

```bash
# 遍历列表
for server in web01 web02 db01; do
    echo "检查 $server..."
    ssh "$server" "uptime"
done

# 数字范围
for i in $(seq 1 10); do
    echo "服务器 $i"
done

# 遍历文件
for log in /var/log/nginx/*.log; do
    echo "处理: $(basename $log)"
    wc -l "$log"
done
```

#### 1.2 while 循环

```bash
# 逐行读取文件
while IFS= read -r line; do
    echo "用户: $line"
done < /etc/passwd
```

---

### 2. SRE 实战

**批量服务器巡检**：
```bash
#!/bin/bash
for server in $(cat servers.txt); do
    echo "=== $server ==="
    ssh "$server" "uptime; df -h / | tail -1"
    echo ""
done
```

**并行巡检（加速）**：
```bash
#!/bin/bash
for server in $(cat servers.txt); do
    (
        echo "=== $server ==="
        ssh "$server" "uptime; df -h /"
    ) &
done
wait  # 等待所有后台任务完成
```
"""


def generate_shell_function_content(day, topic):
    """Shell functions - Day 18"""
    return """### 1. 函数基础

```bash
# 定义函数
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $1" >&2
}

# 使用
log_info "服务启动中..."
log_error "连接失败！"

# 带参数和返回值
check_port() {
    local host=$1
    local port=$2
    if ss -tlnp | grep -q ":$port "; then
        return 0
    else
        return 1
    fi
}
```

---

### 2. SRE 实战

**服务管理菜单**：
```bash
#!/bin/bash
manage_service() {
    local svc=$1
    case "$2" in
        start)   systemctl start "$svc" ;;
        stop)    systemctl stop "$svc" ;;
        restart) systemctl restart "$svc" ;;
        status)  systemctl status "$svc" --no-pager ;;
        *)       echo "Unknown action: $2" ;;
    esac
}

manage_service nginx restart
```
"""


def generate_shell_advanced_content(day, topic):
    """Shell advanced - Day 21, 22"""
    return """### 1. 字符串处理

```bash
STR="Hello World from SRE"

echo ${#STR}                    # 长度: 21
echo ${STR:0:5}                 # 截取: Hello
echo ${STR/World/Linux}         # 替换: Hello Linux from SRE
echo ${STR// /_}                # 全部替换: Hello_World_from_SRE

# 路径处理
FILE="/var/log/nginx/access.log"
echo ${FILE##*/}                # 文件名: access.log
echo ${FILE%/*}                 # 目录: /var/log/nginx
```

### 2. 调试与信号处理

```bash
# 安全模式（每个脚本开头使用）
set -euo pipefail
# -e: 命令失败时退出
# -u: 使用未定义变量时退出
# -o pipefail: 管道中任何命令失败则退出

# 调试
bash -x script.sh        # 显示每行命令
set -x                   # 开启调试
set +x                   # 关闭调试

# trap 信号处理
cleanup() {
    echo "清理临时文件..."
    rm -f /tmp/my_script_*
}
trap cleanup EXIT

trap 'echo "被中断！"; exit 1' INT TERM
```
"""


def generate_review_content(day, topic):
    """Review and practice - Day 7, 14, 28"""
    return f"""### Day {day} 复习与实战

#### 场景 1：新购云服务器从零配置

```bash
# 1. 系统更新
sudo apt update && sudo apt upgrade -y

# 2. 创建用户
sudo useradd -m -s /bin/bash -G sudo sreuser

# 3. 安装基础工具
sudo apt install -y curl wget vim git htop tree net-tools

# 4. 配置防火墙
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### 场景 2：日志分析挑战

```bash
# 找出暴力破解的 IP
grep "Failed password" /var/log/auth.log | \\
    awk '{{print $(NF-3)}}' | sort | uniq -c | sort -rn | head -10

# 分析 Nginx 日志
awk '{{print $9}}' /var/log/nginx/access.log | sort | uniq -c | sort -rn

# 统计磁盘使用
du -sh /var/log/* | sort -rh | head -10
```

#### 场景 3：权限排查

```bash
# 排查 403 Forbidden
ls -la /var/www/html/
namei -l /var/www/html/index.html
getfacl /var/www/html/
```

#### 自我评估

- [ ] 能否不查阅文档完成常用文件操作？
- [ ] 能否独立排查权限问题？
- [ ] 能否编写基本的 Shell 脚本？
- [ ] 能否分析日志找出问题？
"""


def generate_lamp_content(day, topic):
    """LAMP setup - Day 14"""
    return """### 1. LAMP 环境搭建

#### 1.1 安装 Apache

```bash
sudo apt update
sudo apt install -y apache2
sudo systemctl enable apache2
sudo systemctl start apache2

# 验证
curl -s -o /dev/null -w "%{http_code}" http://localhost
# 应返回 200
```

#### 1.2 安装 MySQL

```bash
sudo apt install -y mysql-server
sudo systemctl enable mysql
sudo mysql -e "CREATE DATABASE myapp CHARACTER SET utf8mb4;"
sudo mysql -e "CREATE USER 'myapp'@'localhost' IDENTIFIED BY 'strong_password';"
sudo mysql -e "GRANT ALL ON myapp.* TO 'myapp'@'localhost';"
```

#### 1.3 安装 PHP

```bash
sudo apt install -y php libapache2-mod-php php-mysql php-curl php-gd
sudo systemctl restart apache2

# 测试
echo '<?php phpinfo(); ?>' | sudo tee /var/www/html/info.php
curl http://localhost/info.php | head -5
```

---

### 2. SRE 最佳实践

```bash
# 安全加固
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 监控脚本
#!/bin/bash
for svc in apache2 mysql; do
    if ! systemctl is-active --quiet "$svc"; then
        echo "❌ $svc 未运行！"
        systemctl restart "$svc"
    else
        echo "✅ $svc 运行正常"
    fi
done
```
"""


# ============ Phase 2-8 Stub Content Generators ============

def generate_network_osi_content(day, topic):
    """Network OSI model - Day 29"""
    return f"""### Day {day}: OSI 七层模型

#### 1. OSI 七层模型

| 层 | 名称 | 典型协议 | 设备 |
|----|------|---------|------|
| 7 | 应用层 | HTTP/DNS/SSH | 网关 |
| 6 | 表示层 | SSL/TLS/JSON | - |
| 5 | 会话层 | NetBIOS/RPC | - |
| 4 | 传输层 | TCP/UDP | 防火墙 |
| 3 | 网络层 | IP/ICMP | 路由器 |
| 2 | 数据链路层 | Ethernet/ARP | 交换机 |
| 1 | 物理层 | 电缆/光纤 | 集线器 |

**SRE 实战案例**：用户反馈"网站打不开"→ ping 通（网络层 OK）→ telnet 端口不通（传输层/应用层问题）→ 定位到防火墙规则。

#### 2. 数据封装过程

```
应用数据 → TCP 段 → IP 包 → Ethernet 帧 → 比特流
```

#### 3. 练习

- 画出 OSI 模型，标注一次 HTTP 请求经过的每一层
- 用 `ping` 测试网络层连通性
- 用 `traceroute` 追踪数据包路径
"""


def generate_network_tcp_content(day, topic):
    """TCP protocol - Day 30"""
    return f"""### Day {day}: TCP 协议详解

#### 1. 三次握手与四次挥手

```
三次握手：
Client → SYN → Server
Client ← SYN+ACK ← Server
Client → ACK → Server  (连接建立)

四次挥手：
Client → FIN → Server
Client ← ACK ← Server
Client ← FIN ← Server
Client → ACK → Server  (连接关闭)
```

#### 2. TCP 状态

```bash
# 查看 TCP 连接状态
ss -tan | awk 'NR>1 {print $1}' | sort | uniq -c
```

**SRE 实战案例**：服务器大量 CLOSE_WAIT → 应用代码未正确关闭连接 → 文件描述符耗尽。

#### 3. 练习

- 用 `ss -tan` 查看 TCP 状态统计
- 用 `tcpdump` 观察三次握手
"""


def generate_network_dns_content(day, topic):
    """DNS - Day 34"""
    return f"""### Day {day}: DNS 协议

#### 1. DNS 查询过程

```
浏览器缓存 → OS 缓存 → 递归 DNS → 根 DNS → TLD DNS → 权威 DNS
```

#### 2. DNS 记录类型

| 类型 | 用途 | 示例 |
|------|------|------|
| A | IPv4 地址 | 93.184.216.34 |
| AAAA | IPv6 地址 | 2606:2800:220:1:248:1893:25c8:1946 |
| CNAME | 别名 | www → example.com |
| MX | 邮件 | mail.example.com |
| TXT | 验证 | v=spf1 ... |

#### 3. 实用命令

```bash
dig example.com A +short          # 查询 A 记录
dig example.com MX                # 查询 MX 记录
dig example.com +trace            # 追踪完整解析链
nslookup example.com              # 传统查询
```

**SRE 实战案例**：服务调用失败 → nslookup 发现 DNS 解析到错误 IP → 排查到 DNS 缓存未刷新。
"""


def generate_network_basic_content(day, topic):
    """Generic network content"""
    return f"""### Day {day}: {topic}

#### 1. 基础知识

{topic} 是网络通信的重要组成部分。

#### 2. 常用命令

```bash
# 网络诊断工具
ping -c 4 example.com           # 测试连通性
traceroute example.com          # 追踪路径
mtr example.com                 # 综合诊断
```

#### 3. SRE 实战

- 网络故障排查流程：ping → traceroute → telnet/nc → curl
- 编写网络诊断脚本

#### 4. 练习

- 使用相关命令进行网络诊断
- 分析网络延迟和丢包
"""


def generate_python_basic_content(day, topic):
    """Python basic content"""
    return f"""### Day {day}: {topic}

#### 1. 基础知识

Python 是 SRE 最常用的脚本语言之一。

#### 2. 核心概念

- 变量和数据结构（列表、字典、元组、集合）
- 控制流程（if/for/while）
- 函数和模块
- 异常处理（try/except）
- 文件和 I/O 操作

```python
# 示例：读取配置文件
import json

with open('config.json') as f:
    config = json.load(f)

print(f"Server: {config['host']}:{config['port']}")
```

#### 3. SRE 实战

- 主机监控脚本（psutil 库）
- 日志分析工具
- API 调用（requests 库）

#### 4. 练习

- 编写 Python 脚本监控系统资源
- 解析 JSON 配置文件
- 调用 REST API
"""


def generate_docker_basic_content(day, topic):
    """Docker basic content"""
    return f"""### Day {day}: {topic}

#### 1. 基础知识

Docker 是容器化技术的核心工具。

#### 2. 常用命令

```bash
docker run -d -p 80:80 --name web nginx
docker ps
docker logs -f web
docker exec -it web bash
docker stop web && docker rm web
```

#### 3. Dockerfile 示例

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

#### 4. SRE 实战

- 容器资源限制（--memory, --cpus）
- 日志轮转配置
- 健康检查

#### 5. 练习

- 编写 Dockerfile 部署应用
- 使用 docker-compose 编排多容器
"""


def generate_cloud_basic_content(day, topic):
    """Cloud/AWS basic content"""
    return f"""### Day {day}: {topic}

#### 1. 基础知识

云平台是现代 SRE 的基础设施。

#### 2. 核心服务

- 计算：EC2（虚拟机）
- 存储：S3（对象存储）、EBS（块存储）
- 网络：VPC（虚拟私有云）
- 数据库：RDS

#### 3. AWS CLI

```bash
aws ec2 describe-instances
aws s3 ls
aws s3 cp local.txt s3://my-bucket/
```

#### 4. SRE 实战

- 使用 IAM 最小权限原则
- 配置安全组和网络 ACL
- 设置 CloudWatch 告警

#### 5. 练习

- 使用 AWS CLI 管理资源
- 设计高可用架构
"""


def generate_iac_basic_content(day, topic):
    """IaC basic content"""
    return f"""### Day {day}: {topic}

#### 1. 基础知识

Infrastructure as Code（IaC）是现代运维的核心实践。

#### 2. Terraform 示例

```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name = "web-server"
  }
}
```

```bash
terraform init
terraform plan
terraform apply
```

#### 3. Ansible 示例

```yaml
- hosts: webservers
  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present
    - name: Start nginx
      service:
        name: nginx
        state: started
```

```bash
ansible-playbook deploy.yml
```

#### 4. SRE 实战

- 版本控制基础设施配置
- 多环境管理（dev/staging/prod）
- 模块化和可复用配置
"""


def generate_observability_basic_content(day, topic):
    """Observability basic content"""
    return f"""### Day {day}: {topic}

#### 1. 基础知识

可观测性三大支柱：Metrics（指标）、Logs（日志）、Traces（链路追踪）。

#### 2. 关键概念

- **SLO**（服务级别目标）：可用性 99.9%
- **错误预算**：100% - SLO = 可接受的故障时间
- **黄金指标**：延迟、流量、错误、饱和度

#### 3. Prometheus 查询示例

```promql
# CPU 使用率
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# QPS
rate(http_requests_total[5m])

# P99 延迟
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

#### 4. SRE 实战

- 定义服务的 SLO
- 配置告警规则
- 创建 Grafana 仪表盘

#### 5. 练习

- 部署 Prometheus + Grafana
- 编写 PromQL 查询
- 配置告警通知
"""


def generate_cicd_basic_content(day, topic):
    """CI/CD basic content"""
    return f"""### Day {day}: {topic}

#### 1. 基础知识

CI/CD 实现自动化构建、测试和部署。

#### 2. GitHub Actions 示例

```yaml
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: pytest
```

#### 3. 部署策略

- **滚动部署**：逐步替换，零停机
- **Blue-Green**：两套环境切换，秒级回滚
- **Canary**：小流量验证，逐步放量

#### 4. SRE 实战

- 代码推送 → 自动构建 → 测试 → 部署
- ArgoCD GitOps 实践
- 金丝雀发布

#### 5. 练习

- 编写 CI Pipeline
- 配置自动部署
"""


def generate_sre_practice_content(day, topic):
    """SRE practice content"""
    return f"""### Day {day}: {topic}

#### 1. 基础知识

SRE（Site Reliability Engineering）是 Google 提出的运维方法论。

#### 2. 核心概念

- **On-Call**：告警分级（P0/P1/P2/P3）
- **事故管理**：分级、响应、RCA 事后复盘
- **SLO**：服务级别目标与错误预算
- **容量规划**：性能测试与扩缩容
- **灾备**：RPO/RTO 指标

#### 3. 实战场景

**事故响应流程**：
1. 告警接收 → 确认故障
2. 快速恢复（回滚/重启/扩容）
3. 根因分析（5 Why 方法）
4. 事后复盘（RCA 报告）
5. 改进措施

**RCA 报告模板**：
- 时间线
- 影响范围
- 根因分析
- 改进措施
- 负责人和截止日期

#### 4. 练习

- 设计 On-Call 流程
- 编写 RCA 报告
- 定义服务的 SLO
"""
