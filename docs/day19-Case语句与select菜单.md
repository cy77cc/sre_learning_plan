# Day 19: Shell case 语句与 select 菜单

> 📅 日期：2026-04-26
> 📖 学习主题：Shell case 语句与 select 菜单
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 19 的学习后，你应该掌握：
- 掌握 case 语句的语法和模式匹配能力
- 理解 case 与 if/elif/else 的区别和适用场景
- 掌握模式匹配的通配符用法
- 掌握 select 创建交互式数字菜单
- 能编写带菜单的交互式运维脚本
- 理解 case 在 init 脚本和服务脚本中的实际应用

---

## 📖 详细知识点

### 1. case 语句

#### 1.1 基本语法

```bash
case 变量 in
    模式1)
        命令1
        命令2
        ;;            # 必须用 ;; 结束每个分支
    模式2|模式3)       # 多个模式用 | 分隔
        命令
        ;;
    *)                # * 匹配其他所有情况（默认分支）
        默认命令
        ;;
esac                  # case 的反写，标记结束
```

#### 1.2 与 if/elif/else 对比

```bash
# 同一个功能，两种写法

# 写法 1：if/elif（适合复杂条件判断）
os=$(uname)
if [[ "$os" == "Linux" ]]; then
    echo "Linux 系统"
    pkg_mgr="apt"
elif [[ "$os" == "Darwin" ]]; then
    echo "macOS 系统"
    pkg_mgr="brew"
elif [[ "$os" == "FreeBSD" ]]; then
    echo "FreeBSD 系统"
    pkg_mgr="pkg"
else
    echo "未知系统: $os"
    exit 1
fi

# 写法 2：case（适合单一变量的多路分支）
case $(uname) in
    Linux)
        echo "Linux 系统"
        pkg_mgr="apt"
        ;;
    Darwin)
        echo "macOS 系统"
        pkg_mgr="brew"
        ;;
    FreeBSD)
        echo "FreeBSD 系统"
        pkg_mgr="pkg"
        ;;
    *)
        echo "未知系统: $(uname)"
        exit 1
        ;;
esac
```

**选择指南：**
| 场景 | 推荐 |
|------|------|
| 同一个变量，多个固定值匹配 | case |
| 复杂条件组合（多个变量、比较运算） | if/elif |
| 模式匹配（通配符、正则） | case |
| 需要赋值给变量 | if/elif（case 中赋值不够优雅） |

#### 1.3 模式匹配

```bash
# 精确匹配
case "$1" in
    start)
        echo "启动服务"
        ;;
    stop)
        echo "停止服务"
        ;;
esac

# 通配符匹配
case "$filename" in
    *.tar.gz|*.tgz)
        echo "gzip 压缩包"
        tar xzf "$filename"
        ;;
    *.tar.bz2)
        echo "bzip2 压缩包"
        tar xjf "$filename"
        ;;
    *.tar.xz)
        echo "xz 压缩包"
        tar xJf "$filename"
        ;;
    *.zip)
        echo "zip 压缩包"
        unzip "$filename"
        ;;
    *)
        echo "未知格式: $filename"
        exit 1
        ;;
esac

# 字符范围
case "$char" in
    [a-z])
        echo "小写字母"
        ;;
    [A-Z])
        echo "大写字母"
        ;;
    [0-9])
        echo "数字"
        ;;
    [[:punct:]])
        echo "标点符号"
        ;;
    *)
        echo "其他字符"
        ;;
esac

# 字符类
case "$input" in
    [yY]|[yY][eE][sS])
        echo "确认"
        ;;
    [nN]|[nN][oO])
        echo "拒绝"
        ;;
    *)
        echo "请输入 y 或 n"
        ;;
esac

# 空字符串匹配
case "$var" in
    "")
        echo "变量为空"
        ;;
    *)
        echo "变量: $var"
        ;;
esac
```

### 2. select 菜单

#### 2.1 基本用法

```bash
# select 自动创建带编号的菜单
PS3="请选择操作 (1-4): "    # PS3 是 select 的提示符

select choice in "查看状态" "启动服务" "停止服务" "退出"; do
    case $choice in
        "查看状态")
            systemctl status nginx
            ;;
        "启动服务")
            sudo systemctl start nginx
            echo "✅ 已启动"
            ;;
        "停止服务")
            sudo systemctl stop nginx
            echo "✅ 已停止"
            ;;
        "退出")
            echo "再见"
            break
            ;;
        *)
            echo "无效选择，请重试"
            ;;
    esac
done
```

**输出示例：**
```
1) 查看状态
2) 启动服务
3) 停止服务
4) 退出
请选择操作 (1-4): 1

● nginx.service - A high performance web server
   Active: active (running)

请选择操作 (1-4): 5
无效选择，请重试

请选择操作 (1-4):
```

#### 2.2 从数组动态生成菜单

```bash
services=("nginx" "mysql" "redis" "docker" "sshd")

PS3="选择要检查的服务: "
select svc in "${services[@]}" "返回上一级"; do
    if [[ "$svc" == "返回上一级" ]]; then
        break
    elif [[ -n "$svc" ]]; then
        echo "=== $svc 状态 ==="
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            echo "✅ 运行中"
        else
            echo "❌ 未运行"
        fi
        echo ""
    else
        echo "无效选择"
    fi
done
```

#### 2.3 多级菜单

```bash
main_menu() {
    PS3="主菜单: "
    select choice in "系统管理" "服务管理" "退出"; do
        case $choice in
            "系统管理") sys_menu; break ;;
            "服务管理") svc_menu; break ;;
            "退出") exit 0 ;;
            *) echo "无效" ;;
        esac
    done
}

sys_menu() {
    PS3="系统管理: "
    select choice in "查看系统信息" "查看磁盘" "返回"; do
        case $choice in
            "查看系统信息") uname -a; break ;;
            "查看磁盘") df -h; break ;;
            "返回") main_menu; break ;;
            *) echo "无效" ;;
        esac
    done
}

svc_menu() {
    PS3="服务管理: "
    select choice in "Nginx" "MySQL" "返回"; do
        case $choice in
            "Nginx") systemctl status nginx; break ;;
            "MySQL") systemctl status mysql; break ;;
            "返回") main_menu; break ;;
            *) echo "无效" ;;
        esac
    done
}

main_menu
```

### 3. case 在 init 脚本中的应用

```bash
# 传统的 init.d 脚本都用 case 处理 start/stop/restart
# 这是 case 最常见的实际应用场景

#!/bin/bash
# /etc/init.d/myapp

case "$1" in
    start)
        echo "Starting myapp..."
        /usr/bin/myapp --daemon --config /etc/myapp.conf
        pidfile="/var/run/myapp.pid"
        pgrep -f "myapp --daemon" > "$pidfile"
        ;;
    stop)
        echo "Stopping myapp..."
        if [[ -f /var/run/myapp.pid ]]; then
            kill $(cat /var/run/myapp.pid)
            rm -f /var/run/myapp.pid
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    reload)
        echo "Reloading configuration..."
        kill -HUP $(cat /var/run/myapp.pid 2>/dev/null)
        ;;
    status)
        if pgrep -f "myapp --daemon" > /dev/null; then
            echo "myapp is running"
        else
            echo "myapp is stopped"
        fi
        ;;
    *)
        echo "用法: $0 {start|stop|restart|reload|status}"
        exit 1
        ;;
esac
```

---

## 🏗️ 实战：交互式运维工具箱

```bash
#!/usr/bin/env bash
#运维工具箱.sh

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; BLUE='\033[0;34m'
NC='\033[0m'

header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# --- 系统信息 ---
show_sysinfo() {
    header "系统信息"
    echo -e "  主机名:   $(hostname)"
    echo -e "  操作系统: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
    echo -e "  内核:     $(uname -r)"
    echo -e "  CPU:      $(nproc) 核心"
    echo -e "  内存:     $(free -h | awk '/Mem:/ {print $2}')"
    echo -e "  运行时间: $(uptime -p)"
    echo -e "  负载:     $(cat /proc/loadavg | awk '{print $1, $2, $3}')"
}

# --- 进程监控 ---
show_procs() {
    header "CPU Top 5"
    ps aux --sort=-%cpu | head -6
    echo ""
    header "内存 Top 5"
    ps aux --sort=-%mem | head -6
}

# --- 磁盘 ---
show_disk() {
    header "磁盘使用"
    df -h --local
    echo ""
    header "Inode 使用"
    df -i --local
}

# --- 网络 ---
show_network() {
    header "网络接口"
    ip -4 addr show | grep inet
    echo ""
    header "监听端口"
    ss -tlnp
}

# --- 服务状态 ---
show_services() {
    header "服务状态"
    local services=("sshd" "nginx" "mysql" "docker")
    for svc in "${services[@]}"; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            echo -e "  ${GREEN}●${NC} $svc (运行中)"
        else
            echo -e "  ${RED}●${NC} $svc (未运行)"
        fi
    done
}

# --- 主菜单 ---
PS3="选择功能: "
while true; do
    select choice in \
        "系统信息" \
        "进程监控" \
        "磁盘使用" \
        "网络信息" \
        "服务状态" \
        "退出"; do
        case $choice in
            "系统信息") show_sysinfo; break ;;
            "进程监控") show_procs; break ;;
            "磁盘使用") show_disk; break ;;
            "网络信息") show_network; break ;;
            "服务状态") show_services; break ;;
            "退出") echo "再见！"; exit 0 ;;
            *) echo -e "${RED}无效选择${NC}"; break ;;
        esac
    done
done
```

---

## 🧪 练习题

### 练习 1：文件类型判断

用 case 根据扩展名判断文件类型。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
case "$1" in
    *.sh|*.bash)  echo "Shell 脚本" ;;
    *.py)         echo "Python 脚本" ;;
    *.js)         echo "JavaScript" ;;
    *.go)         echo "Go 源码" ;;
    *.rs)         echo "Rust 源码" ;;
    *.md)         echo "Markdown 文档" ;;
    *.yaml|*.yml) echo "YAML 配置" ;;
    *.json)       echo "JSON 数据" ;;
    *.xml)        echo "XML 文件" ;;
    *.log)        echo "日志文件" ;;
    *.conf|*.cfg) echo "配置文件" ;;
    *.tar.gz|*.tgz) echo "gzip 压缩包" ;;
    *.zip)        echo "zip 压缩包" ;;
    *)            echo "其他类型" ;;
esac
```
</details>

### 练习 2：交互式文件管理器

编写一个脚本，列出当前目录内容，让用户选择查看文件或目录。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
PS3="选择操作: "
while true; do
    select action in "列出文件" "列出目录" "查看文件" "退出"; do
        case $action in
            "列出文件")
                ls -la --file-type | grep -v '/$'
                break ;;
            "列出目录")
                ls -la --file-type | grep '/$'
                break ;;
            "查看文件")
                read -p "文件名: " fname
                [[ -f "$fname" ]] && less "$fname" || echo "文件不存在"
                break ;;
            "退出") exit 0 ;;
            *) echo "无效"; break ;;
        esac
    done
done
```
</details>

---

## 📚 扩展阅读

- `man bash` — 搜索 "CONDITIONAL CONSTRUCTS"
- [Bash case 语句教程](https://tldp.org/LDP/abs/html/case.html)
- [Linux 启动脚本惯例](https://tldp.org/LDP/sag/html/serv-script.html)
