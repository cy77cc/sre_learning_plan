# Day 19: Case 语句与 select 菜单

> 📅 日期：2026-05-02
> 📖 学习主题：Case 语句与 select 菜单
> ⏰ 预计学习时间：2-3 小时
> 📋 前置知识：Day 03 (文件操作)、Day 04 (文本处理)、Day 11 (循环与条件)

---

## 🎯 学习目标

完成 Day 19 的学习后，你应该掌握：

- 理解 `case` 语句的语法结构和模式匹配机制
- 掌握 `select` 菜单的创建和交互式脚本设计
- 能够使用通配符模式（`*`、`?`、`[abc]`、`|`）进行复杂匹配
- 实现生产级的交互式运维工具菜单
- 在 SRE 工作中正确应用 case/select 构建自动化工具

---

## 📖 核心知识点

### 1. Case 语句深入

#### 1.1 语法结构

`case` 语句是 Bash 中的模式匹配结构，类似于其他语言中的 `switch` 语句，但功能更强大。

```bash
case 变量 in
    模式1)
        命令 ;;
    模式2)
        命令 ;;
    *)
        默认命令 ;;
esac
```

**基本结构图**：

```
case 变量 in
    ┌─────────────────────────────┐
    │  模式1) 命令1 ;;            │  ← 第一个匹配分支
    │  模式2) 命令2 ;;            │  ← 第二个匹配分支
    │  模式3|模式4) 命令3 ;;      │  ← 多模式分支（OR）
    │  *) 默认命令 ;;             │  ← 默认分支（可选）
    └─────────────────────────────┘
esac
```

**关键语法元素**：

| 元素 | 含义 | 示例 |
|------|------|------|
| `case` | 开始 case 语句 | `case $action in` |
| `in` | 分隔变量和模式 | `$action in` |
| `)` | 模式结束标记 | `start)` |
| `;;` | 分支终止符（必须） | `echo "started" ;;` |
| `;&` | 继续执行下一个分支（无条件） | `echo "started" ;&` |
| `;;&` | 继续匹配下一个模式 | `echo "started" ;;&` |
| `esac` | 结束 case 语句（case 反写） | `esac` |

#### 1.2 模式匹配详解

`case` 使用 shell 通配符模式（不是正则表达式）进行匹配：

**通配符对照表**：

| 通配符 | 含义 | 示例 | 匹配 |
|--------|------|------|------|
| `*` | 任意字符（包括空） | `*.log` | access.log, error.log |
| `?` | 单个字符 | `?.txt` | a.txt, 1.txt |
| `[abc]` | 括号内任一字符 | `[0-9]` | 0-9 |
| `[!abc]` | 非括号内字符 | `[!0-9]` | 非数字 |
| `\|` | 或（多模式） | `y\|Y\|yes` | yes/Yes/YES |

**模式匹配实战**：

```bash
#!/bin/bash
# 文件类型判断脚本
filename="$1"

case "$filename" in
    *.tar.gz|*.tgz)
        echo "tar.gz 压缩包"
        ;;
    *.tar.bz2|*.tbz2)
        echo "tar.bz2 压缩包"
        ;;
    *.tar.xz|*.txz)
        echo "tar.xz 压缩包"
        ;;
    *.zip)
        echo "zip 压缩包"
        ;;
    *.gz)
        echo "gzip 压缩文件"
        ;;
    *.log)
        echo "日志文件"
        ;;
    *.conf|*.cfg)
        echo "配置文件"
        ;;
    [0-9]*)
        echo "以数字开头的文件"
        ;;
    *)
        echo "未知文件类型: $filename"
        ;;
esac
```

#### 1.3 Case vs If/elif 选择

**对比表格**：

| 特性 | case | if/elif |
|------|------|---------|
| 匹配方式 | 模式匹配（通配符） | 条件表达式 |
| 可读性 | 多分支时更清晰 | 复杂逻辑时更灵活 |
| 性能 | 匹配效率高 | 需要逐个评估 |
| 适用场景 | 单变量多值匹配 | 复杂条件组合 |
| 字符串匹配 | 原生支持通配符 | 需要 `[[ ]]` 配合 |
| 数值比较 | 不支持原生 | 原生支持 |

**选择指南**：

```
使用 case 当：
├── 单个变量有多个可能的值
├── 需要模式匹配（通配符）
├── 分支数量 >= 3
└── 字符串比较为主

使用 if/elif 当：
├── 需要数值比较
├── 需要逻辑组合（&&, ||）
├── 条件复杂（文件测试、命令退出码）
└── 分支数量 <= 2
```

**等价示例**：

```bash
# 使用 if/elif
if [[ "$1" == "start" ]]; then
    start_service
elif [[ "$1" == "stop" ]]; then
    stop_service
elif [[ "$1" == "restart" ]]; then
    restart_service
elif [[ "$1" == "status" ]]; then
    show_status
else
    echo "Unknown command: $1"
fi

# 使用 case（更清晰）
case "$1" in
    start)   start_service ;;
    stop)    stop_service ;;
    restart) restart_service ;;
    status)  show_status ;;
    *)       echo "Unknown command: $1" ;;
esac
```

#### 1.4 高级模式匹配

**正则风格匹配（使用 [[ ]] + case）**：

```bash
#!/bin/bash
# IP 地址格式验证
validate_ip() {
    local ip="$1"

    # case 不支持正则，使用 [[ ]] 验证格式
    if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        echo "格式错误: IP 地址格式不正确"
        return 1
    fi

    # 使用 case 验证每个八位字节
    IFS='.' read -r o1 o2 o3 o4 <<< "$ip"

    for octet in $o1 $o2 $o3 $o4; do
        case "$octet" in
            [0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])
                continue ;;
            *)
                echo "范围错误: $octet 不在 0-255 范围内"
                return 1 ;;
        esac
    done

    echo "有效 IP 地址: $ip"
    return 0
}

# 测试
validate_ip "192.168.1.1"    # 有效
validate_ip "256.1.1.1"      # 无效
validate_ip "192.168.1"      # 无效
```

**嵌套 Case**：

```bash
#!/bin/bash
# 服务管理脚本 - 嵌套 case 示例
service_name="$1"
action="$2"

case "$service_name" in
    nginx|httpd)
        case "$action" in
            start)
                systemctl start "$service_name"
                echo "$service_name 已启动"
                ;;
            stop)
                systemctl stop "$service_name"
                echo "$service_name 已停止"
                ;;
            reload)
                systemctl reload "$service_name"
                echo "$service_name 已重载配置"
                ;;
            configtest)
                if [[ "$service_name" == "nginx" ]]; then
                    nginx -t
                else
                    apachectl configtest
                fi
                ;;
            *)
                echo "用法: $0 {nginx|httpd} {start|stop|reload|configtest}"
                ;;
        esac
        ;;
    mysql|mariadb)
        case "$action" in
            start)
                systemctl start "$service_name"
                ;;
            stop)
                # MySQL 需要特殊处理
                mysqladmin shutdown
                ;;
            status)
                mysqladmin status
                ;;
            *)
                echo "用法: $0 {mysql|mariadb} {start|stop|status}"
                ;;
        esac
        ;;
    *)
        echo "不支持的服务: $service_name"
        echo "支持: nginx, httpd, mysql, mariadb"
        exit 1
        ;;
esac
```

#### 1.5 Case 的特殊用法

**作为函数返回值**：

```bash
#!/bin/bash
# 将 case 结果赋值给变量
get_service_status() {
    local service="$1"
    local status

    status=$(systemctl is-active "$service" 2>/dev/null)

    case "$status" in
        active)    echo "running" ;;
        inactive)  echo "stopped" ;;
        failed)    echo "failed" ;;
        activating) echo "starting" ;;
        deactivating) echo "stopping" ;;
        *)         echo "unknown" ;;
    esac
}

# 使用
app_status=$(get_service_status "nginx")
echo "Nginx 状态: $app_status"
```

**在循环中使用 case**：

```bash
#!/bin/bash
# 批量处理不同类型的日志文件
process_logs() {
    local log_dir="$1"

    for file in "$log_dir"/*; do
        case "$file" in
            *.gz)
                echo "解压: $file"
                gunzip "$file"
                ;;
            *.bz2)
                echo "解压: $file"
                bunzip2 "$file"
                ;;
            *.tar)
                echo "解包: $file"
                tar xf "$file" -C "$log_dir"
                ;;
            *.log)
                echo "处理日志: $file"
                # 归档超过 7 天的日志
                if [[ $(find "$file" -mtime +7 -print) ]]; then
                    gzip "$file"
                fi
                ;;
            *)
                echo "跳过: $file"
                ;;
        esac
    done
}
```

---

### 2. Select 菜单

#### 2.1 基本语法

`select` 是 Bash 内置的菜单生成结构，自动创建编号菜单并等待用户选择。

```bash
select 变量 in 列表; do
    命令
    break  # 必须显式 break 退出循环
done
```

**语法解析**：

```
select 变量 in item1 item2 item3; do
    ┌─────────────────────────────────────────┐
    │  1) item1                               │  ← 自动生成的菜单
    │  2) item2                               │
    │  3) item3                               │
    │  #?                                     │  ← PS3 提示符
    └─────────────────────────────────────────┘
    命令                                      │  ← 用户输入后执行
    break                                     │  ← 退出循环
done
```

#### 2.2 PS3 提示符

`PS3` 是 `select` 专用的提示符变量，默认值是 `#?`。

```bash
#!/bin/bash
# 自定义提示符
PS3="请选择操作 [1-5]: "

select opt in "启动服务" "停止服务" "重启服务" "查看状态" "退出"; do
    case "$opt" in
        "启动服务")
            echo "启动所有服务..."
            ;;
        "停止服务")
            echo "停止所有服务..."
            ;;
        "重启服务")
            echo "重启所有服务..."
            ;;
        "查看状态")
            echo "显示服务状态..."
            ;;
        "退出")
            echo "再见！"
            break
            ;;
        *)
            echo "无效选择，请重新输入"
            ;;
    esac
done
```

#### 2.3 Select 与 Case 结合

**标准模式**：

```bash
#!/bin/bash
# 交互式环境选择菜单
PS3="请选择环境: "

select env in "开发环境" "测试环境" "预发布环境" "生产环境" "退出"; do
    case "$env" in
        "开发环境")
            export APP_ENV="development"
            export DB_HOST="dev-db.internal"
            export LOG_LEVEL="debug"
            echo "已切换到开发环境"
            break
            ;;
        "测试环境")
            export APP_ENV="testing"
            export DB_HOST="test-db.internal"
            export LOG_LEVEL="info"
            echo "已切换到测试环境"
            break
            ;;
        "预发布环境")
            export APP_ENV="staging"
            export DB_HOST="staging-db.internal"
            export LOG_LEVEL="warn"
            echo "已切换到预发布环境"
            break
            ;;
        "生产环境")
            read -rp "确认切换到生产环境? (yes/no): " confirm
            if [[ "$confirm" == "yes" ]]; then
                export APP_ENV="production"
                export DB_HOST="prod-db.internal"
                export LOG_LEVEL="error"
                echo "已切换到生产环境"
            else
                echo "已取消"
            fi
            break
            ;;
        "退出")
            echo "退出程序"
            exit 0
            ;;
        *)
            echo "无效选择: $REPLY"
            ;;
    esac
done
```

#### 2.4 菜单循环和退出机制

**无限循环菜单**：

```bash
#!/bin/bash
# 带退出的无限循环菜单
show_menu() {
    echo ""
    echo "=========================="
    echo "  SRE 运维工具箱 v1.0"
    echo "=========================="
    echo "1. 服务管理"
    echo "2. 日志分析"
    echo "3. 磁盘检查"
    echo "4. 网络诊断"
    echo "5. 系统信息"
    echo "0. 退出"
    echo "=========================="
}

while true; do
    show_menu
    read -rp "请选择操作 [0-5]: " choice

    case "$choice" in
        1)
            echo "进入服务管理..."
            # 调用服务管理子函数
            ;;
        2)
            echo "进入日志分析..."
            ;;
        3)
            echo "进入磁盘检查..."
            ;;
        4)
            echo "进入网络诊断..."
            ;;
        5)
            echo "显示系统信息..."
            ;;
        0)
            echo "退出程序，再见！"
            exit 0
            ;;
        *)
            echo "无效选择: $choice"
            sleep 1
            ;;
    esac
done
```

**带超时的菜单**：

```bash
#!/bin/bash
# 超时自动选择默认选项
TIMEOUT=30
DEFAULT=1

echo "请选择操作 (等待 ${TIMEOUT} 秒后自动选择默认):"
select opt in "启动" "停止" "重启" "退出"; do
    # select 不支持超时，使用 read 替代
    break
done

# 使用 read -t 实现超时
read -t "$TIMEOUT" -rp "请选择 [1-4, 默认=$DEFAULT]: " choice
choice=${choice:-$DEFAULT}

case "$choice" in
    1) echo "启动服务" ;;
    2) echo "停止服务" ;;
    3) echo "重启服务" ;;
    4) exit 0 ;;
    *) echo "无效选择" ;;
esac
```

#### 2.5 Select 的局限性

| 局限 | 说明 | 替代方案 |
|------|------|---------|
| 不支持超时 | 无法设置等待时间 | 使用 `read -t` |
| 不支持默认值 | 必须用户输入 | 使用 `read` + 默认值 |
| 不支持方向键 | 纯文本交互 | 使用 dialog/whiptail |
| 不支持多选 | 只能单选 | 使用 checkbox 工具 |
| 输入验证弱 | 无效输入需要循环 | 使用 read + case 验证 |

---

### 3. 实战模式：交互式运维工具菜单

#### 3.1 完整的服务管理菜单脚本

```bash
#!/bin/bash
#============================================================
# 服务管理菜单脚本
# 用法: ./service_menu.sh [service_name]
#============================================================

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务名称（默认或参数）
SERVICE="${1:-nginx}"

#------------------------------------------------------------
# 辅助函数
#------------------------------------------------------------
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

check_service_exists() {
    if ! systemctl list-unit-files | grep -q "^${SERVICE}"; then
        log_error "服务 '$SERVICE' 不存在"
        exit 1
    fi
}

get_service_status() {
    systemctl is-active "$SERVICE" 2>/dev/null || echo "inactive"
}

#------------------------------------------------------------
# 服务操作函数
#------------------------------------------------------------
start_service() {
    local status
    status=$(get_service_status)

    if [[ "$status" == "active" ]]; then
        log_warn "服务 '$SERVICE' 已经在运行"
        return 0
    fi

    log_info "启动服务 '$SERVICE'..."
    if sudo systemctl start "$SERVICE"; then
        log_info "服务 '$SERVICE' 启动成功"
    else
        log_error "服务 '$SERVICE' 启动失败"
        return 1
    fi
}

stop_service() {
    local status
    status=$(get_service_status)

    if [[ "$status" != "active" ]]; then
        log_warn "服务 '$SERVICE' 未在运行"
        return 0
    fi

    log_info "停止服务 '$SERVICE'..."
    if sudo systemctl stop "$SERVICE"; then
        log_info "服务 '$SERVICE' 停止成功"
    else
        log_error "服务 '$SERVICE' 停止失败"
        return 1
    fi
}

restart_service() {
    log_info "重启服务 '$SERVICE'..."
    if sudo systemctl restart "$SERVICE"; then
        log_info "服务 '$SERVICE' 重启成功"
    else
        log_error "服务 '$SERVICE' 重启失败"
        return 1
    fi
}

reload_service() {
    log_info "重载服务 '$SERVICE' 配置..."
    if sudo systemctl reload "$SERVICE"; then
        log_info "服务 '$SERVICE' 配置重载成功"
    else
        log_warn "服务 '$SERVICE' 不支持 reload，尝试 restart..."
        restart_service
    fi
}

show_status() {
    echo ""
    echo "=========================================="
    echo "  服务状态: $SERVICE"
    echo "=========================================="
    systemctl status "$SERVICE" --no-pager
    echo "=========================================="
}

show_logs() {
    local lines="${1:-50}"
    echo ""
    echo "最近 ${lines} 行日志:"
    echo "------------------------------------------"
    journalctl -u "$SERVICE" -n "$lines" --no-pager
}

follow_logs() {
    log_info "实时跟踪日志 (Ctrl+C 退出)..."
    journalctl -u "$SERVICE" -f
}

enable_service() {
    log_info "启用服务 '$SERVICE' 开机自启..."
    sudo systemctl enable "$SERVICE"
    log_info "已设置开机自启"
}

disable_service() {
    log_info "禁用服务 '$SERVICE' 开机自启..."
    sudo systemctl disable "$SERVICE"
    log_info "已禁用开机自启"
}

#------------------------------------------------------------
# 显示菜单
#------------------------------------------------------------
show_menu() {
    local status
    status=$(get_service_status)

    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  服务管理菜单 - ${SERVICE}${NC}"
    echo -e "${BLUE}  当前状态: ${GREEN}${status}${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo "  1. 启动服务"
    echo "  2. 停止服务"
    echo "  3. 重启服务"
    echo "  4. 重载配置"
    echo "  5. 查看状态"
    echo "  6. 查看日志"
    echo "  7. 实时日志"
    echo "  8. 开机自启"
    echo "  9. 禁用自启"
    echo "  0. 退出"
    echo -e "${BLUE}============================================${NC}"
}

#------------------------------------------------------------
# 主程序
#------------------------------------------------------------
main() {
    # 检查服务是否存在
    check_service_exists

    while true; do
        show_menu
        read -rp "请选择操作 [0-9]: " choice

        case "$choice" in
            1) start_service ;;
            2) stop_service ;;
            3) restart_service ;;
            4) reload_service ;;
            5) show_status ;;
            6)
                read -rp "显示多少行日志 [默认 50]: " log_lines
                show_logs "${log_lines:-50}"
                ;;
            7) follow_logs ;;
            8) enable_service ;;
            9) disable_service ;;
            0)
                log_info "退出服务管理"
                exit 0
                ;;
            *)
                log_error "无效选择: $choice"
                sleep 1
                ;;
        esac

        echo ""
        read -rp "按 Enter 继续..."
    done
}

# 运行主程序
main
```

#### 3.2 环境选择与切换菜单

```bash
#!/bin/bash
#============================================================
# 环境选择与配置脚本
# 用法: ./env_switcher.sh
#============================================================

set -euo pipefail

CONFIG_FILE="/etc/app/config.env"
BACKUP_DIR="/etc/app/backups"

# 环境配置
declare -A ENV_CONFIGS=(
    ["development"]="dev-db.internal:5432:dev_user:debug"
    ["testing"]="test-db.internal:5432:test_user:info"
    ["staging"]="staging-db.internal:5432:staging_user:warn"
    ["production"]="prod-db.internal:5432:prod_user:error"
)

# 显示当前配置
show_current_config() {
    echo ""
    echo "当前环境配置:"
    echo "------------------------------------------"
    if [[ -f "$CONFIG_FILE" ]]; then
        cat "$CONFIG_FILE"
    else
        echo "(未配置)"
    fi
    echo "------------------------------------------"
}

# 备份当前配置
backup_config() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"

    if [[ -f "$CONFIG_FILE" ]]; then
        cp "$CONFIG_FILE" "${BACKUP_DIR}/config_${timestamp}.env"
        echo "已备份配置到 ${BACKUP_DIR}/config_${timestamp}.env"
    fi
}

# 应用环境配置
apply_env_config() {
    local env="$1"
    local config="${ENV_CONFIGS[$env]}"

    IFS=':' read -r db_host db_port db_user log_level <<< "$config"

    cat > "$CONFIG_FILE" <<EOF
APP_ENV=${env}
DB_HOST=${db_host}
DB_PORT=${db_port}
DB_USER=${db_user}
LOG_LEVEL=${log_level}
CONFIGURED_AT=$(date -Iseconds)
EOF

    echo "已应用 ${env} 环境配置"
}

# 验证配置
validate_config() {
    local env="$1"
    local config="${ENV_CONFIGS[$env]}"
    IFS=':' read -r db_host _ _ _ <<< "$config"

    echo "验证 ${env} 环境连接..."
    if ping -c 1 -W 2 "$db_host" &>/dev/null; then
        echo "数据库主机 $db_host 可达"
    else
        echo "警告: 数据库主机 $db_host 不可达"
        read -rp "是否继续? (yes/no): " confirm
        [[ "$confirm" == "yes" ]] || return 1
    fi
}

# 主菜单
PS3="请选择目标环境: "

echo "=========================================="
echo "  环境配置管理工具"
echo "=========================================="

show_current_config

select env in "开发环境" "测试环境" "预发布环境" "生产环境" "查看历史" "退出"; do
    case "$env" in
        "开发环境")
            backup_config
            validate_config "development"
            apply_env_config "development"
            show_current_config
            break
            ;;
        "测试环境")
            backup_config
            validate_config "testing"
            apply_env_config "testing"
            show_current_config
            break
            ;;
        "预发布环境")
            backup_config
            validate_config "staging"
            apply_env_config "staging"
            show_current_config
            break
            ;;
        "生产环境")
            echo ""
            echo "警告: 生产环境操作需要额外确认"
            read -rp "请输入 'PRODUCTION' 确认: " confirm
            if [[ "$confirm" == "PRODUCTION" ]]; then
                backup_config
                validate_config "production"
                apply_env_config "production"
                show_current_config
            else
                echo "已取消"
            fi
            break
            ;;
        "查看历史")
            echo ""
            echo "配置备份历史:"
            ls -lt "$BACKUP_DIR"/*.env 2>/dev/null || echo "(无备份)"
            ;;
        "退出")
            echo "退出环境配置工具"
            exit 0
            ;;
        *)
            echo "无效选择: $REPLY"
            ;;
    esac
done
```

#### 3.3 自动化部署菜单

```bash
#!/bin/bash
#============================================================
# 自动化部署菜单脚本
# 用法: ./deploy_menu.sh
#============================================================

set -euo pipefail

# 配置
DEPLOY_DIR="/opt/deploy"
LOG_DIR="/var/log/deploy"
REPO_URL="git@github.com:example/app.git"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 创建目录
mkdir -p "$DEPLOY_DIR" "$LOG_DIR"

# 日志函数
log() {
    local level="$1"
    shift
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [$level] $*" | tee -a "${LOG_DIR}/deploy.log"
}

# 选择部署版本
select_version() {
    echo ""
    echo "可用版本:"
    echo "  1) 最新版本 (latest)"
    echo "  2) 指定标签 (tag)"
    echo "  3) 指定分支 (branch)"
    echo "  4) 指定提交 (commit)"

    read -rp "选择版本类型 [1-4]: " version_type

    case "$version_type" in
        1) echo "latest" ;;
        2)
            read -rp "输入标签名: " tag
            echo "tag:$tag"
            ;;
        3)
            read -rp "输入分支名: " branch
            echo "branch:$branch"
            ;;
        4)
            read -rp "输入提交哈希: " commit
            echo "commit:$commit"
            ;;
        *)
            echo "无效选择"
            return 1
            ;;
    esac
}

# 选择目标环境
select_target() {
    echo ""
    PS3="选择部署目标: "

    select target in "开发服务器" "测试服务器" "预发布服务器" "生产集群" "取消"; do
        case "$target" in
            "开发服务器")   echo "dev" ;;
            "测试服务器")   echo "test" ;;
            "预发布服务器") echo "staging" ;;
            "生产集群")     echo "production" ;;
            "取消")         return 1 ;;
            *)              echo "无效选择" ;;
        esac
        break
    done
}

# 拉取代码
pull_code() {
    local version="$1"
    log "INFO" "拉取代码: $version"

    cd "$DEPLOY_DIR"

    case "$version" in
        latest)
            git pull origin main
            ;;
        tag:*)
            local tag="${version#tag:}"
            git fetch --tags
            git checkout "$tag"
            ;;
        branch:*)
            local branch="${version#branch:}"
            git fetch origin
            git checkout "$branch"
            git pull origin "$branch"
            ;;
        commit:*)
            local commit="${version#commit:}"
            git fetch origin
            git checkout "$commit"
            ;;
    esac

    log "INFO" "代码拉取完成"
}

# 构建应用
build_app() {
    log "INFO" "开始构建应用..."

    cd "$DEPLOY_DIR"

    # 运行构建命令
    if make build 2>&1 | tee -a "${LOG_DIR}/build.log"; then
        log "INFO" "构建成功"
    else
        log "ERROR" "构建失败"
        return 1
    fi
}

# 运行测试
run_tests() {
    log "INFO" "运行测试套件..."

    cd "$DEPLOY_DIR"

    if make test 2>&1 | tee -a "${LOG_DIR}/test.log"; then
        log "INFO" "测试通过"
    else
        log "ERROR" "测试失败"
        return 1
    fi
}

# 部署到目标环境
deploy_to_target() {
    local target="$1"
    log "INFO" "部署到 $target 环境..."

    case "$target" in
        dev)
            ansible-playbook deploy.yml -l dev
            ;;
        test)
            ansible-playbook deploy.yml -l test
            ;;
        staging)
            ansible-playbook deploy.yml -l staging
            ;;
        production)
            # 生产环境蓝绿部署
            ansible-playbook deploy.yml -l prod --extra-vars "strategy=blue-green"
            ;;
    esac

    log "INFO" "部署完成"
}

# 回滚
rollback() {
    log "WARN" "开始回滚..."

    cd "$DEPLOY_DIR"

    # 获取上一个版本
    local prev_version
    prev_version=$(git log --oneline -2 | tail -1 | awk '{print $1}')

    log "INFO" "回滚到版本: $prev_version"
    git checkout "$prev_version"
    build_app
    deploy_to_target "production"

    log "INFO" "回滚完成"
}

# 部署菜单
show_deploy_menu() {
    echo ""
    echo "=========================================="
    echo "  自动化部署系统"
    echo "=========================================="
    echo "  1. 完整部署流程"
    echo "  2. 仅拉取代码"
    echo "  3. 仅构建"
    echo "  4. 仅运行测试"
    echo "  5. 仅部署"
    echo "  6. 回滚"
    echo "  7. 查看部署日志"
    echo "  0. 退出"
    echo "=========================================="
}

# 主程序
main() {
    while true; do
        show_deploy_menu
        read -rp "选择操作 [0-7]: " choice

        case "$choice" in
            1)
                # 完整部署流程
                version=$(select_version) || continue
                target=$(select_target) || continue

                echo ""
                echo "部署计划:"
                echo "  版本: $version"
                echo "  目标: $target"
                echo ""
                read -rp "确认部署? (yes/no): " confirm

                if [[ "$confirm" == "yes" ]]; then
                    pull_code "$version"
                    run_tests
                    build_app
                    deploy_to_target "$target"
                    log "INFO" "完整部署流程完成"
                else
                    log "INFO" "部署已取消"
                fi
                ;;
            2)
                version=$(select_version) || continue
                pull_code "$version"
                ;;
            3)
                build_app
                ;;
            4)
                run_tests
                ;;
            5)
                target=$(select_target) || continue
                deploy_to_target "$target"
                ;;
            6)
                read -rp "确认回滚? (yes/no): " confirm
                if [[ "$confirm" == "yes" ]]; then
                    rollback
                fi
                ;;
            7)
                echo ""
                echo "最近 50 行部署日志:"
                tail -50 "${LOG_DIR}/deploy.log"
                ;;
            0)
                log "INFO" "退出部署系统"
                exit 0
                ;;
            *)
                echo "无效选择: $choice"
                ;;
        esac

        read -rp "按 Enter 继续..."
    done
}

main
```

---

### 4. SRE 实战案例

#### 4.1 服务器健康检查脚本

```bash
#!/bin/bash
#============================================================
# 服务器健康检查脚本
# 用法: ./health_check.sh [server_ip]
#============================================================

set -euo pipefail

SERVER="${1:-localhost}"
TIMEOUT=5
REPORT_FILE="/tmp/health_check_$(date +%Y%m%d_%H%M%S).txt"

# 检查函数
check_port() {
    local port="$1"
    local service="$2"

    if nc -z -w "$TIMEOUT" "$SERVER" "$port" 2>/dev/null; then
        echo "[PASS] $service (端口 $port) - 正常"
        return 0
    else
        echo "[FAIL] $service (端口 $port) - 不可达"
        return 1
    fi
}

check_http() {
    local url="$1"
    local expected_code="$2"
    local service="$3"

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" "$url" 2>/dev/null || echo "000")

    case "$http_code" in
        "$expected_code")
            echo "[PASS] $service HTTP ($http_code) - 正常"
            return 0
            ;;
        000)
            echo "[FAIL] $service HTTP - 连接失败"
            return 1
            ;;
        *)
            echo "[WARN] $service HTTP ($http_code) - 预期 $expected_code"
            return 1
            ;;
    esac
}

check_disk() {
    local threshold=80
    local usage

    usage=$(ssh "$SERVER" "df -h / | awk 'NR==2 {print \$5}' | tr -d '%'")

    if [[ "$usage" -lt "$threshold" ]]; then
        echo "[PASS] 磁盘使用率 ($usage%) - 正常"
        return 0
    else
        echo "[WARN] 磁盘使用率 ($usage%) - 超过阈值 $threshold%"
        return 1
    fi
}

check_memory() {
    local threshold=90
    local usage

    usage=$(ssh "$SERVER" "free | awk '/Mem:/ {printf \"%.0f\", \$3/\$2 * 100}'")

    if [[ "$usage" -lt "$threshold" ]]; then
        echo "[PASS] 内存使用率 ($usage%) - 正常"
        return 0
    else
        echo "[WARN] 内存使用率 ($usage%) - 超过阈值 $threshold%"
        return 1
    fi
}

# 执行检查
{
    echo "=========================================="
    echo "  服务器健康检查报告"
    echo "  服务器: $SERVER"
    echo "  时间: $(date)"
    echo "=========================================="
    echo ""

    total=0
    passed=0
    failed=0

    # 端口检查
    echo "--- 端口检查 ---"
    for check in "22:SSH" "80:HTTP" "443:HTTPS" "3306:MySQL" "6379:Redis"; do
        IFS=':' read -r port service <<< "$check"
        ((total++))
        if check_port "$port" "$service"; then
            ((passed++))
        else
            ((failed++))
        fi
    done

    # HTTP 检查
    echo ""
    echo "--- HTTP 检查 ---"
    for check in "http://$SERVER/:200:首页" "http://$SERVER/health:200:健康检查" "http://$SERVER/api/status:200:API状态"; do
        IFS=':' read -r url expected service <<< "$check"
        ((total++))
        if check_http "$url" "$expected" "$service"; then
            ((passed++))
        else
            ((failed++))
        fi
    done

    # 系统资源检查
    echo ""
    echo "--- 系统资源检查 ---"
    ((total++))
    if check_disk; then ((passed++)); else ((failed++)); fi

    ((total++))
    if check_memory; then ((passed++)); else ((failed++)); fi

    # 汇总
    echo ""
    echo "=========================================="
    echo "  检查汇总"
    echo "  总计: $total"
    echo "  通过: $passed"
    echo "  失败: $failed"
    echo "  通过率: $((passed * 100 / total))%"
    echo "=========================================="

} 2>&1 | tee "$REPORT_FILE"

echo ""
echo "报告已保存到: $REPORT_FILE"
```

#### 4.2 多服务器批量管理脚本

```bash
#!/bin/bash
#============================================================
# 多服务器批量管理脚本
# 用法: ./batch_manage.sh
#============================================================

set -euo pipefail

# 服务器列表
SERVERS_FILE="/etc/sre/servers.conf"

# 读取服务器列表
load_servers() {
    if [[ ! -f "$SERVERS_FILE" ]]; then
        echo "错误: 服务器配置文件不存在: $SERVERS_FILE"
        exit 1
    fi

    mapfile -t servers < "$SERVERS_FILE"
    echo "已加载 ${#servers[@]} 台服务器"
}

# 执行远程命令
execute_remote() {
    local server="$1"
    local command="$2"

    echo "--- [$server] ---"
    if ssh -o ConnectTimeout=5 "$server" "$command" 2>&1; then
        return 0
    else
        echo "执行失败"
        return 1
    fi
}

# 批量执行
batch_execute() {
    local command="$1"
    local description="$2"

    echo ""
    echo "=========================================="
    echo "  批量执行: $description"
    echo "  命令: $command"
    echo "  服务器数量: ${#servers[@]}"
    echo "=========================================="
    echo ""

    read -rp "确认执行? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo "已取消"
        return
    fi

    local success=0
    local failure=0

    for server in "${servers[@]}"; do
        if execute_remote "$server" "$command"; then
            ((success++))
        else
            ((failure++))
        fi
        echo ""
    done

    echo "=========================================="
    echo "  执行结果: 成功=$success, 失败=$failure"
    echo "=========================================="
}

# 主菜单
main() {
    load_servers

    while true; do
        echo ""
        echo "=========================================="
        echo "  多服务器批量管理"
        echo "  服务器数量: ${#servers[@]}"
        echo "=========================================="
        echo "  1. 系统信息"
        echo "  2. 磁盘使用"
        echo "  3. 内存使用"
        echo "  4. 进程状态"
        echo "  5. 服务状态"
        echo "  6. 执行自定义命令"
        echo "  7. 同步文件"
        echo "  0. 退出"
        echo "=========================================="

        read -rp "选择操作 [0-7]: " choice

        case "$choice" in
            1)
                batch_execute "uname -a && uptime" "系统信息"
                ;;
            2)
                batch_execute "df -h" "磁盘使用"
                ;;
            3)
                batch_execute "free -h" "内存使用"
                ;;
            4)
                batch_execute "ps aux --sort=-%mem | head -20" "内存 Top 20 进程"
                ;;
            5)
                read -rp "服务名称: " service
                batch_execute "systemctl status $service" "服务状态: $service"
                ;;
            6)
                read -rp "自定义命令: " cmd
                batch_execute "$cmd" "自定义命令"
                ;;
            7)
                read -rp "本地文件路径: " local_file
                read -rp "远程目标路径: " remote_path
                for server in "${servers[@]}"; do
                    echo "同步到 $server..."
                    scp "$local_file" "$server:$remote_path"
                done
                ;;
            0)
                echo "退出"
                exit 0
                ;;
            *)
                echo "无效选择"
                ;;
        esac

        read -rp "按 Enter 继续..."
    done
}

main
```

---

## 💻 实战练习

### 练习 1：基础 Case 语句

**目标**：编写一个脚本，根据文件扩展名执行不同的操作。

```bash
#!/bin/bash
# 练习: 文件操作脚本
# 用法: ./file_ops.sh <文件名>

file="$1"

case "$file" in
    *.tar.gz)
        # 解压 tar.gz
        tar -xzf "$file"
        ;;
    *.gz)
        # 解压 gz
        gunzip "$file"
        ;;
    *.txt)
        # 显示文件内容
        cat "$file"
        ;;
    *.sh)
        # 执行脚本
        bash "$file"
        ;;
    *)
        echo "不支持的文件类型: $file"
        ;;
esac
```

**练习要求**：
1. 添加对 `.zip`、`.tar.bz2`、`.jpg` 等文件类型的支持
2. 添加文件存在性检查
3. 添加操作确认提示

### 练习 2：交互式菜单

**目标**：创建一个系统监控仪表板菜单。

```bash
#!/bin/bash
# 练习: 系统监控仪表板
# 实现以下功能:
# 1. CPU 使用率
# 2. 内存使用率
# 3. 磁盘使用率
# 4. 网络连接数
# 5. 进程 Top 10
# 6. 实时监控
```

**练习要求**：
1. 使用 `select` 或 `while read` 实现菜单
2. 每个选项调用相应的监控命令
3. 添加退出功能
4. 添加刷新间隔设置

### 练习 3：故障排查挑战

**场景**：编写一个交互式故障排查脚本。

```bash
#!/bin/bash
# 练习: 交互式故障排查
# 脚本应引导用户逐步排查:
# 1. 服务无法启动
# 2. 网络连接问题
# 3. 磁盘空间不足
# 4. 内存不足
```

**挑战要求**：
1. 使用 case/select 实现多级菜单
2. 每个排查步骤给出建议
3. 记录排查过程到日志文件
4. 生成排查报告

---

## 🎯 面试题精选

### 1. case 和 if/elif 的主要区别是什么？什么时候应该使用 case？

**参考答案**：

`case` 和 `if/elif` 的主要区别：

| 方面 | case | if/elif |
|------|------|---------|
| 匹配方式 | 模式匹配（通配符） | 条件表达式 |
| 性能 | 单变量多值时更高效 | 需要逐个评估 |
| 可读性 | 多分支时更清晰 | 复杂逻辑时更灵活 |

**使用 case 的场景**：
- 单个变量有多个可能的值
- 需要模式匹配（通配符）
- 分支数量 >= 3
- 字符串比较为主

**使用 if/elif 的场景**：
- 需要数值比较
- 需要逻辑组合（`&&`、`||`）
- 条件复杂（文件测试、命令退出码）
- 分支数量 <= 2

### 2. select 语句的 PS3 变量有什么作用？

**参考答案**：

`PS3` 是 `select` 语句专用的提示符变量。默认值是 `#?`，用户可以通过设置 `PS3` 来自定义菜单提示信息。

```bash
PS3="请选择操作 [1-5]: "
select opt in "选项1" "选项2" "选项3"; do
    # ...
done
```

`PS3` 只在 `select` 循环中生效，不影响 `read` 命令的提示。

### 3. 如何实现一个带超时的菜单选择？

**参考答案**：

`select` 本身不支持超时，需要使用 `read -t` 实现：

```bash
#!/bin/bash
TIMEOUT=10
DEFAULT=1

echo "请选择操作 (默认选项 $DEFAULT，等待 ${TIMEOUT} 秒):"
echo "1. 启动"
echo "2. 停止"
echo "3. 重启"

read -t "$TIMEOUT" -rp "请选择 [1-3]: " choice
choice=${choice:-$DEFAULT}  # 设置默认值

case "$choice" in
    1) echo "启动" ;;
    2) echo "停止" ;;
    3) echo "重启" ;;
    *) echo "无效选择" ;;
esac
```

### 4. case 语句中的 `;;`、`;&` 和 `;;&` 有什么区别？

**参考答案**：

- `;;`：标准终止符，执行完当前分支后退出 case 语句
- `;&`：无条件继续执行下一个分支的命令（不再进行模式匹配）
- `;;&`：继续匹配下一个模式，如果匹配则执行对应分支

```bash
case "$1" in
    start)
        echo "Starting..."
        ;;&    # 继续匹配
    start|restart)
        echo "Starting or restarting..."
        ;;     # 终止
    stop)
        echo "Stopping..."
        ;&     # 无条件继续
    cleanup)
        echo "Cleaning up..."
        ;;
esac
```

### 5. 如何在 case 中使用正则表达式？

**参考答案**：

`case` 语句本身不支持正则表达式，只支持 shell 通配符模式。要使用正则表达式，需要结合 `[[ ]]` 和 `=~` 操作符：

```bash
#!/bin/bash
input="$1"

# 使用 [[ ]] 进行正则匹配
if [[ "$input" =~ ^[0-9]+$ ]]; then
    echo "纯数字"
elif [[ "$input" =~ ^[a-zA-Z]+$ ]]; then
    echo "纯字母"
elif [[ "$input" =~ ^[a-zA-Z0-9]+$ ]]; then
    echo "字母数字组合"
else
    echo "包含特殊字符"
fi

# 如果必须用 case，需要先转换
validate_input() {
    local input="$1"

    # 对于简单的模式，case 仍然适用
    case "$input" in
        [0-9]*)          echo "以数字开头" ;;
        [a-zA-Z]*)       echo "以字母开头" ;;
        *[@#\$%]*)       echo "包含特殊字符" ;;
        *)               echo "其他" ;;
    esac
}
```

### 6. 编写一个脚本，接受 start/stop/restart/status 参数来管理服务。

**参考答案**：

```bash
#!/bin/bash
# 服务管理脚本

SERVICE="${2:-nginx}"
ACTION="$1"

# 检查参数
if [[ -z "$ACTION" ]]; then
    echo "用法: $0 {start|stop|restart|status} [service_name]"
    exit 1
fi

# 检查服务是否存在
check_service() {
    if ! systemctl list-unit-files | grep -q "^${SERVICE}"; then
        echo "错误: 服务 '$SERVICE' 不存在"
        exit 1
    fi
}

# 主逻辑
case "$ACTION" in
    start)
        check_service
        echo "启动 $SERVICE..."
        sudo systemctl start "$SERVICE"
        systemctl status "$SERVICE" --no-pager
        ;;
    stop)
        check_service
        echo "停止 $SERVICE..."
        sudo systemctl stop "$SERVICE"
        echo "$SERVICE 已停止"
        ;;
    restart)
        check_service
        echo "重启 $SERVICE..."
        sudo systemctl restart "$SERVICE"
        systemctl status "$SERVICE" --no-pager
        ;;
    status)
        check_service
        systemctl status "$SERVICE" --no-pager
        ;;
    *)
        echo "错误: 未知操作 '$ACTION'"
        echo "用法: $0 {start|stop|restart|status} [service_name]"
        exit 1
        ;;
esac
```

### 7. select 循环中，用户输入无效选择时会发生什么？

**参考答案**：

当用户输入无效选择（如输入非数字或超出范围的数字）时：
- `REPLY` 变量保存用户原始输入
- `变量` 被设置为空
- 需要在 case 或 if 中处理空值情况

```bash
select opt in "选项1" "选项2" "退出"; do
    case "$opt" in
        "选项1") echo "选择了1" ;;
        "选项2") echo "选择了2" ;;
        "退出") break ;;
        *)
            echo "无效选择，你输入了: $REPLY"
            echo "请输入 1-3 之间的数字"
            ;;
    esac
done
```

### 8. 如何在 case 中匹配空字符串？

**参考答案**：

```bash
case "$var" in
    "")
        echo "变量为空"
        ;;
    *)
        echo "变量值: $var"
        ;;
esac
```

或者使用 `?` 匹配非空：

```bash
case "$var" in
    "")    echo "空" ;;
    ?*)    echo "非空: $var" ;;
esac
```

---

## 📚 深入阅读

### 官方文档
- [Bash Manual - Conditional Constructs](https://www.gnu.org/software/bash/manual/bash.html#Conditional-Constructs)
- [Bash Manual - Case](https://www.gnu.org/software/bash/manual/bash.html#index-case)
- [Bash Manual - Select](https://www.gnu.org/software/bash/manual/bash.html#index-select)

### 推荐书籍
- 《Bash Cookbook》- Carl Albing, JP Vossen
- 《Shell Scripting: Expert Recipes for Linux, Bash, and More》- Steve Parker
- 《Wicked Cool Shell Scripts》- Dave Taylor

### 在线资源
- [Advanced Bash-Scripting Guide](https://tldp.org/LDP/abs/html/)
- [ShellCheck](https://www.shellcheck.net/) - Shell 脚本静态分析工具
- [Explain Shell](https://explainshell.com/) - Shell 命令解释工具

---

## ✅ 自检清单

### 理论检查点
- [ ] 能够解释 case 语句的语法结构（case/in/esac）
- [ ] 理解通配符模式匹配（*、?、[abc]、|）
- [ ] 知道 `;;`、`;&`、`;;&` 的区别
- [ ] 理解 select 语句的工作原理
- [ ] 知道 PS3 变量的作用
- [ ] 能够区分 case 和 if/elif 的使用场景

### 实操检查点
- [ ] 能够编写基本的 case 语句
- [ ] 能够使用通配符进行模式匹配
- [ ] 能够创建交互式 select 菜单
- [ ] 能够实现带循环的菜单系统
- [ ] 能够编写服务管理脚本
- [ ] 能够实现环境选择菜单
- [ ] 能够处理用户输入验证

---

> 📝 **学习笔记**
>
> 记录你在学习过程中的心得和疑问：
>
> 1. ________________________________________________
> 2. ________________________________________________
> 3. ________________________________________________
