# Day 24: 实战项目 — 服务器初始化脚本

> 📅 日期：2026-04-25
> 📖 学习主题：实战项目 — 服务器初始化脚本
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 23 expect 自动化交互、Day 22 脚本调试与信号处理

## 🎯 学习目标

完成 Day 24 的学习后，你应该掌握：
- 能够独立设计和编写生产级服务器初始化脚本
- 掌握参数解析（getopts、长选项 --help/--user/--ssh-key/--env）
- 实现跨发行版兼容性处理（Ubuntu/Debian/Rocky/AlmaLinux）
- 理解幂等性设计原则，确保脚本重复执行不出错
- 掌握脚本工程化实践：set -euo pipefail、函数封装、日志记录、错误处理

---

## 📖 核心知识点

### 1. 服务器初始化脚本的设计原则

#### 1.1 为什么需要服务器初始化脚本？

在 SRE 的日常工作中，服务器初始化是最基础也是最频繁的任务之一。无论是云服务器扩容、机房设备上架，还是容器镜像构建，都需要一个标准化的初始化流程。

**没有标准化初始化脚本的问题**：
- 每次手动操作，容易遗漏步骤
- 不同人初始化的服务器配置不一致
- 排查问题时无法确定服务器的初始状态
- 无法快速响应业务扩容需求

**标准化初始化的价值**：
- 所有服务器配置一致，减少"在我机器上能跑"的问题
- 可审计、可追溯，知道每台服务器做了什么
- 快速交付，新服务器从开机到上线可在分钟级完成
- 减少人为错误，提高系统可靠性

#### 1.2 设计原则

| 原则 | 说明 | 示例 |
|------|------|------|
| **幂等性** | 重复执行不出错 | 检查用户是否存在再创建 |
| **可配置** | 参数外部化 | 通过配置文件或命令行参数控制 |
| **可回滚** | 失败时能恢复 | 记录操作前状态，失败时恢复 |
| **有日志** | 每步操作可追溯 | 带时间戳的日志文件 |
| **跨平台** | 支持多发行版 | 检测 OS 类型选择对应命令 |
| **安全** | 最小权限原则 | 不硬编码密码，使用密钥 |

#### 1.3 脚本架构设计

```
server_init.sh
├── 参数解析层
│   ├── --help        显示帮助
│   ├── --user        指定用户
│   ├── --ssh-key     SSH 公钥路径
│   ├── --env         环境标识 (dev/staging/prod)
│   └── --dry-run     模拟运行
├── 检测层
│   ├── OS 发行版检测
│   ├── 网络连通性检测
│   └── 权限检测
├── 执行层
│   ├── 系统更新
│   ├── 用户创建与 SSH 配置
│   ├── 基础工具安装
│   ├── 防火墙配置
│   ├── NTP 时间同步
│   ├── SSH 安全加固
│   ├── 内核参数优化
│   └── 日志轮转配置
├── 报告层
│   └── 生成初始化报告
└── 工具层
    ├── 日志函数
    ├── 错误处理
    └── 幂等性检查
```

---

### 2. 脚本工程化基础

#### 2.1 安全模式 — set 选项

```bash
#!/bin/bash
# set -euo pipefail 是生产级脚本的标配

set -e  # 任何命令失败立即退出（不忽略错误）
set -u  # 使用未定义变量时报错（防止拼写错误）
set -o pipefail  # 管道中任何命令失败，整个管道失败

# 示例：为什么需要 pipefail
# 没有 pipefail：即使 grep 失败，echo 仍然成功，$? 为 0
cat /nonexistent | grep "pattern" | wc -l
echo $?  # 输出 0（错误！）

# 有 pipefail：grep 失败，整个管道失败，$? 非 0
set -o pipefail
cat /nonexistent | grep "pattern" | wc -l
echo $?  # 输出非 0（正确！）

# 特殊情况：某些命令失败是预期的，用 || 处理
grep "pattern" file.txt || true  # grep 失败不退出
```

#### 2.2 日志系统设计

```bash
# ===== 日志配置 =====
LOG_FILE="/var/log/server_init_$(date +%Y%m%d_%H%M%S).log"
LOG_LEVEL="${LOG_LEVEL:-INFO}"  # DEBUG, INFO, WARN, ERROR

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'  # No Color

# 日志函数
_log() {
    local level=$1
    local message=$2
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # 写入日志文件（无颜色）
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    # 写入终端（带颜色）
    case "$level" in
        DEBUG) [[ "$LOG_LEVEL" == "DEBUG" ]] && echo -e "${BLUE}[$timestamp] [DEBUG] $message${NC}" ;;
        INFO)  echo -e "${GREEN}[$timestamp] [INFO]${NC}  $message" ;;
        WARN)  echo -e "${YELLOW}[$timestamp] [WARN]${NC}  $message" ;;
        ERROR) echo -e "${RED}[$timestamp] [ERROR] $message${NC}" >&2 ;;
    esac
}

log_debug() { _log "DEBUG" "$1"; }
log_info()  { _log "INFO"  "$1"; }
log_warn()  { _log "WARN"  "$1"; }
log_error() { _log "ERROR" "$1"; }

# 使用示例
log_info "服务器初始化开始"
log_warn "磁盘空间不足 20%"
log_error "SSH 密钥文件不存在"
```

#### 2.3 错误处理与回滚

```bash
# ===== 错误处理 =====

# 全局错误处理函数
error_handler() {
    local line_no=$1
    local error_code=$2
    log_error "脚本在第 $line_no 行出错，错误码: $error_code"
    log_error "开始回滚..."

    # 执行回滚操作
    rollback

    log_error "回滚完成，脚本退出"
    exit "$error_code"
}

# 设置 trap 捕获错误
trap 'error_handler ${LINENO} $?' ERR

# 回滚函数（记录每步操作，失败时反向恢复）
declare -a ROLLBACK_STACK=()

# 注册回滚操作
register_rollback() {
    ROLLBACK_STACK+=("$1")
    log_debug "注册回滚操作: $1"
}

# 执行回滚
rollback() {
    log_warn "执行回滚，共 ${#ROLLBACK_STACK[@]} 个操作"
    # 逆序执行
    for ((i=${#ROLLBACK_STACK[@]}-1; i>=0; i--)); do
        log_warn "回滚: ${ROLLBACK_STACK[i]}"
        eval "${ROLLBACK_STACK[i]}" || true
    done
}

# 使用示例
create_user() {
    local username=$1
    useradd -m -s /bin/bash "$username"
    register_rollback "userdel -r $username"
    log_info "用户 $username 创建成功"
}

setup_firewall() {
    ufw enable
    register_rollback "ufw disable"
    ufw allow 22/tcp
    register_rollback "ufw delete allow 22/tcp"
    log_info "防火墙配置完成"
}
```

#### 2.4 幂等性设计

幂等性是服务器初始化脚本最重要的设计原则：**无论执行多少次，结果都是一样的**。

```bash
# ===== 幂等性设计模式 =====

# 模式 1：先检查再操作
create_user() {
    local username=$1
    if id "$username" &>/dev/null; then
        log_info "用户 $username 已存在，跳过创建"
        return 0
    fi
    useradd -m -s /bin/bash "$username"
    log_info "用户 $username 创建成功"
}

# 模式 2：使用工具的幂等选项
install_package() {
    local package=$1
    # apt install 已安装的包不会报错（幂等）
    if command -v apt &>/dev/null; then
        apt install -y "$package"
    elif command -v dnf &>/dev/null; then
        dnf install -y "$package"
    fi
}

# 模式 3：配置文件幂等更新
update_config() {
    local file=$1 key=$2 value=$3
    if grep -q "^${key}=" "$file" 2>/dev/null; then
        # 已存在，更新值
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        # 不存在，追加
        echo "${key}=${value}" >> "$file"
    fi
}

# 模式 4：确保服务状态
ensure_service_running() {
    local service=$1
    if ! systemctl is-active --quiet "$service"; then
        systemctl start "$service"
        log_info "服务 $service 已启动"
    else
        log_info "服务 $service 已在运行"
    fi
}
```

---

### 3. 跨发行版兼容性处理

#### 3.1 OS 检测

```bash
# ===== OS 检测 =====
detect_os() {
    # 优先使用 /etc/os-release（现代发行版标准）
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_ID="$ID"                    # ubuntu, debian, rocky, almalinux
        OS_VERSION="$VERSION_ID"       # 22.04, 12, 9.3
        OS_NAME="$PRETTY_NAME"         # Ubuntu 22.04.3 LTS
        OS_FAMILY=""                   # debian, rhel
    elif [[ -f /etc/redhat-release ]]; then
        OS_NAME=$(cat /etc/redhat-release)
        if [[ "$OS_NAME" == *"CentOS"* ]]; then
            OS_ID="centos"
        elif [[ "$OS_NAME" == *"Rocky"* ]]; then
            OS_ID="rocky"
        fi
        OS_FAMILY="rhel"
    else
        log_error "无法检测操作系统类型"
        exit 1
    fi

    # 推断 OS 家族
    case "$OS_ID" in
        ubuntu|debian|linuxmint|pop)
            OS_FAMILY="debian"
            PKG_MANAGER="apt"
            PKG_UPDATE="apt update"
            PKG_INSTALL="apt install -y"
            ;;
        rocky|almalinux|centos|rhel|fedora)
            OS_FAMILY="rhel"
            if command -v dnf &>/dev/null; then
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf makecache"
                PKG_INSTALL="dnf install -y"
            else
                PKG_MANAGER="yum"
                PKG_UPDATE="yum makecache"
                PKG_INSTALL="yum install -y"
            fi
            ;;
        *)
            log_error "不支持的操作系统: $OS_ID"
            exit 1
            ;;
    esac

    log_info "检测到系统: $OS_NAME (家族: $OS_FAMILY, 包管理器: $PKG_MANAGER)"
}
```

#### 3.2 包安装兼容层

```bash
# ===== 跨发行版包安装 =====
install_packages() {
    local packages=("$@")

    for pkg in "${packages[@]}"; do
        # 获取发行版对应的包名
        local real_pkg
        real_pkg=$(get_package_name "$pkg")

        if is_package_installed "$real_pkg"; then
            log_debug "包 $real_pkg 已安装，跳过"
            continue
        fi

        log_info "安装 $real_pkg..."
        $PKG_INSTALL "$real_pkg" 2>&1 | tail -3
    done
}

# 包名映射（不同发行版包名不同）
get_package_name() {
    local pkg=$1
    case "$pkg" in
        net-tools)
            echo "net-tools"
            ;;
        devscripts)
            [[ "$OS_FAMILY" == "debian" ]] && echo "devscripts" || echo ""
            ;;
        python3-pip)
            [[ "$OS_FAMILY" == "debian" ]] && echo "python3-pip" || echo "python3-pip"
            ;;
        *)
            echo "$pkg"
            ;;
    esac
}

# 检查包是否已安装
is_package_installed() {
    local pkg=$1
    [[ -z "$pkg" ]] && return 0

    case "$PKG_MANAGER" in
        apt)
            dpkg -l "$pkg" 2>/dev/null | grep -q "^ii"
            ;;
        dnf|yum)
            rpm -q "$pkg" &>/dev/null
            ;;
    esac
}
```

---

### 4. 完整的服务器初始化脚本

以下是生产级服务器初始化脚本的完整实现：

```bash
#!/bin/bash
# =============================================================================
# server_init.sh — 生产级服务器初始化脚本
# 支持: Ubuntu/Debian, Rocky/AlmaLinux/CentOS
# 版本: 1.0.0
# =============================================================================

set -euo pipefail

# ===== 版本与元信息 =====
readonly SCRIPT_VERSION="1.0.0"
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ===== 默认配置 =====
DEFAULT_USER="sre"
DEFAULT_SHELL="/bin/bash"
DEFAULT_TIMEZONE="Asia/Shanghai"
DEFAULT_LOCALE="en_US.UTF-8"
BASE_PACKAGES=(
    curl wget vim git htop tmux
    net-tools sysstat iotop
    tree jq unzip lsof
    bash-completion
)

# ===== 全局变量 =====
LOG_FILE="/var/log/server_init_$(date +%Y%m%d_%H%M%S).log"
DRY_RUN=false
VERBOSE=false
ENVIRONMENT="staging"
INIT_USER=""
SSH_KEY_FILE=""
SSH_PORT=22
ROLLBACK_STACK=()
INIT_REPORT=""
ERRORS_COUNT=0
WARNINGS_COUNT=0

# ===== 颜色与日志 =====
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

_log() {
    local level=$1 message=$2
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    case "$level" in
        DEBUG) $VERBOSE && echo -e "${CYAN}[DEBUG]${NC} $message" ;;
        INFO)  echo -e "${GREEN}[INFO]${NC}  $message" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC}  $message"; ((WARNINGS_COUNT++)) || true ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $message" >&2; ((ERRORS_COUNT++)) || true ;;
        STEP)  echo -e "\n${BOLD}${BLUE}==>${NC} ${BOLD}$message${NC}" ;;
    esac
}

log_debug() { _log "DEBUG" "$1"; }
log_info()  { _log "INFO"  "$1"; }
log_warn()  { _log "WARN"  "$1"; }
log_error() { _log "ERROR" "$1"; }
log_step()  { _log "STEP"  "$1"; }

# 添加到报告
add_report() {
    INIT_REPORT+="$(date '+%H:%M:%S') | $1\n"
}

# ===== 错误处理 =====
error_handler() {
    local line_no=$1 error_code=$2
    log_error "脚本在第 $line_no 行出错 (错误码: $error_code)"
    log_error "执行回滚..."
    rollback
    generate_report
    exit "$error_code"
}

trap 'error_handler ${LINENO} $?' ERR
trap 'log_warn "收到中断信号，正在清理..."; rollback; exit 130' INT TERM

register_rollback() { ROLLBACK_STACK+=("$1"); }

rollback() {
    if [[ ${#ROLLBACK_STACK[@]} -eq 0 ]]; then
        log_info "无回滚操作"
        return
    fi
    log_warn "执行回滚 (${#ROLLBACK_STACK[@]} 个操作)..."
    for ((i=${#ROLLBACK_STACK[@]}-1; i>=0; i--)); do
        log_warn "  回滚: ${ROLLBACK_STACK[i]}"
        eval "${ROLLBACK_STACK[i]}" 2>/dev/null || true
    done
}

# ===== 参数解析 =====
usage() {
    cat << EOF
用法: $SCRIPT_NAME [选项]

服务器初始化脚本 v${SCRIPT_VERSION}

选项:
    -u, --user USER         创建的管理员用户 (默认: $DEFAULT_USER)
    -k, --ssh-key FILE      SSH 公钥文件路径
    -e, --env ENV           环境标识: dev/staging/prod (默认: $ENVIRONMENT)
    -p, --port PORT         SSH 端口 (默认: $SSH_PORT)
    -n, --dry-run           模拟运行，不实际执行
    -v, --verbose           详细输出
    -h, --help              显示此帮助信息

示例:
    $SCRIPT_NAME --user deploy --ssh-key ~/.ssh/id_ed25519.pub --env prod
    $SCRIPT_NAME --dry-run --verbose
    $SCRIPT_NAME -u admin -k /root/.ssh/id_rsa.pub -e staging
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -u|--user)
                INIT_USER="$2"; shift 2 ;;
            -k|--ssh-key)
                SSH_KEY_FILE="$2"; shift 2 ;;
            -e|--env)
                ENVIRONMENT="$2"; shift 2 ;;
            -p|--port)
                SSH_PORT="$2"; shift 2 ;;
            -n|--dry-run)
                DRY_RUN=true; shift ;;
            -v|--verbose)
                VERBOSE=true; shift ;;
            -h|--help)
                usage; exit 0 ;;
            *)
                log_error "未知选项: $1"
                usage; exit 1 ;;
        esac
    done

    # 参数验证
    if [[ -n "$SSH_KEY_FILE" && ! -f "$SSH_KEY_FILE" ]]; then
        log_error "SSH 公钥文件不存在: $SSH_KEY_FILE"
        exit 1
    fi

    case "$ENVIRONMENT" in
        dev|staging|prod) ;;
        *)
            log_error "无效的环境: $ENVIRONMENT (可选: dev/staging/prod)"
            exit 1
            ;;
    esac
}

# ===== 预检查 =====
preflight_checks() {
    log_step "预检查"

    # 检查 root 权限
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        exit 1
    fi
    log_info "root 权限检查通过"

    # 检查网络连通性
    if ! ping -c 1 -W 5 8.8.8.8 &>/dev/null; then
        log_warn "无法连接外网，部分功能可能受限"
    else
        log_info "网络连通性检查通过"
    fi

    # 检查磁盘空间
    local root_usage
    root_usage=$(df / | awk 'NR==2 {print $5}' | tr -d '%')
    if [[ $root_usage -gt 90 ]]; then
        log_error "根分区使用率 ${root_usage}%，空间不足"
        exit 1
    fi
    log_info "磁盘空间检查通过 (使用率: ${root_usage}%)"

    # 检查是否已初始化
    if [[ -f /etc/server_init.done ]]; then
        log_warn "服务器已初始化过 ($(cat /etc/server_init.done))"
        log_warn "继续执行将覆盖之前的配置"
    fi
}

# ===== OS 检测 =====
detect_os() {
    log_step "操作系统检测"

    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_ID="${ID:-unknown}"
        OS_VERSION="${VERSION_ID:-unknown}"
        OS_NAME="${PRETTY_NAME:-unknown}"
    else
        log_error "无法检测操作系统 (/etc/os-release 不存在)"
        exit 1
    fi

    case "$OS_ID" in
        ubuntu|debian)
            OS_FAMILY="debian"
            PKG_UPDATE_CMD="apt-get update -qq"
            PKG_INSTALL_CMD="apt-get install -y -qq"
            PKG_CLEAN_CMD="apt-get autoremove -y -qq"
            SERVICE_ENABLE_CMD="systemctl enable"
            FIREWALL_CMD="ufw"
            ;;
        rocky|almalinux|centos|rhel|fedora)
            OS_FAMILY="rhel"
            if command -v dnf &>/dev/null; then
                PKG_UPDATE_CMD="dnf makecache -q"
                PKG_INSTALL_CMD="dnf install -y -q"
                PKG_CLEAN_CMD="dnf autoremove -y -q"
            else
                PKG_UPDATE_CMD="yum makecache"
                PKG_INSTALL_CMD="yum install -y"
                PKG_CLEAN_CMD="yum autoremove -y"
            fi
            SERVICE_ENABLE_CMD="systemctl enable"
            FIREWALL_CMD="firewalld"
            ;;
        *)
            log_error "不支持的操作系统: $OS_ID"
            exit 1
            ;;
    esac

    log_info "系统: $OS_NAME"
    log_info "家族: $OS_FAMILY"
    add_report "系统检测: $OS_NAME ($OS_FAMILY)"
}

# ===== 系统更新 =====
system_update() {
    log_step "系统更新"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将执行: $PKG_UPDATE_CMD"
        return
    fi

    log_info "更新软件包索引..."
    eval "$PKG_UPDATE_CMD" 2>&1 | tail -5
    log_info "软件包索引更新完成"

    # 安全更新（仅 prod 环境自动安装安全更新）
    if [[ "$ENVIRONMENT" == "prod" ]]; then
        log_info "安装安全更新..."
        if [[ "$OS_FAMILY" == "debian" ]]; then
            apt-get install -y -qq unattended-upgrades 2>/dev/null || true
            dpkg-reconfigure -plow unattended-upgrades 2>/dev/null || true
        fi
    fi

    add_report "系统更新: 完成"
}

# ===== 用户创建与 SSH 配置 =====
setup_user() {
    log_step "用户配置"

    local username="${INIT_USER:-$DEFAULT_USER}"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将创建用户: $username"
        return
    fi

    # 创建用户（幂等）
    if id "$username" &>/dev/null; then
        log_info "用户 $username 已存在"
    else
        useradd -m -s "$DEFAULT_SHELL" -G sudo "$username"
        register_rollback "userdel -r $username 2>/dev/null"
        log_info "用户 $username 创建成功"
    fi

    # 配置 sudo 免密（仅 dev/staging 环境）
    if [[ "$ENVIRONMENT" != "prod" ]]; then
        local sudoers_file="/etc/sudoers.d/$username"
        if [[ ! -f "$sudoers_file" ]]; then
            echo "$username ALL=(ALL) NOPASSWD:ALL" > "$sudoers_file"
            chmod 440 "$sudoers_file"
            register_rollback "rm -f $sudoers_file"
            log_info "sudo 免密配置完成 (仅限 $ENVIRONMENT 环境)"
        fi
    fi

    # 配置 SSH 密钥
    local ssh_dir="/home/$username/.ssh"
    if [[ -n "$SSH_KEY_FILE" ]]; then
        mkdir -p "$ssh_dir"
        cat "$SSH_KEY_FILE" >> "$ssh_dir/authorized_keys"
        chmod 700 "$ssh_dir"
        chmod 600 "$ssh_dir/authorized_keys"
        chown -R "$username:$username" "$ssh_dir"
        log_info "SSH 公钥已配置"
    else
        log_warn "未指定 SSH 公钥，请手动配置"
    fi

    # 配置 bash 增强
    local bashrc="/home/$username/.bashrc"
    if [[ -f "$bashrc" ]]; then
        # 添加常用别名（如果不存在）
        grep -q "alias ll=" "$bashrc" 2>/dev/null || cat >> "$bashrc" << 'ALIASES'

# SRE 常用别名
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias grep='grep --color=auto'
alias df='df -h'
alias du='du -h'
alias free='free -m'
alias ports='ss -tlnp'
ALIASES
        chown "$username:$username" "$bashrc"
    fi

    add_report "用户配置: $username (SSH密钥: ${SSH_KEY_FILE:-未配置})"
}

# ===== 基础工具安装 =====
install_base_tools() {
    log_step "安装基础工具"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将安装: ${BASE_PACKAGES[*]}"
        return
    fi

    local installed=0
    local skipped=0

    for pkg in "${BASE_PACKAGES[@]}"; do
        if is_package_installed "$pkg"; then
            ((skipped++)) || true
        else
            log_info "安装 $pkg..."
            $PKG_INSTALL_CMD "$pkg" 2>&1 | tail -2
            ((installed++)) || true
        fi
    done

    log_info "安装完成: 新装 $installed 个，已存在 $skipped 个"
    add_report "基础工具: 安装 $installed 个，跳过 $skipped 个"
}

is_package_installed() {
    local pkg=$1
    case "$OS_FAMILY" in
        debian) dpkg -l "$pkg" 2>/dev/null | grep -q "^ii" ;;
        rhel)   rpm -q "$pkg" &>/dev/null ;;
    esac
}

# ===== 防火墙配置 =====
setup_firewall() {
    log_step "防火墙配置"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将配置防火墙"
        return
    fi

    case "$OS_FAMILY" in
        debian)
            # UFW 防火墙
            if ! command -v ufw &>/dev/null; then
                apt-get install -y -qq ufw
            fi

            # 幂等配置
            ufw --force reset
            ufw default deny incoming
            ufw default allow outgoing
            ufw allow "$SSH_PORT/tcp" comment 'SSH'
            ufw allow 80/tcp comment 'HTTP'
            ufw allow 443/tcp comment 'HTTPS'

            # 根据环境开放不同端口
            case "$ENVIRONMENT" in
                dev)
                    ufw allow 8080/tcp comment 'Dev HTTP'
                    ufw allow 9090/tcp comment 'Dev Metrics'
                    ;;
                staging)
                    ufw allow 9090/tcp comment 'Metrics'
                    ;;
                prod)
                    # 生产环境最小化开放端口
                    ;;
            esac

            ufw --force enable
            register_rollback "ufw disable"
            log_info "UFW 防火墙配置完成"
            ;;
        rhel)
            # firewalld 防火墙
            systemctl enable firewalld
            systemctl start firewalld
            register_rollback "systemctl stop firewalld"

            firewall-cmd --permanent --set-default-zone=public
            firewall-cmd --permanent --add-port="$SSH_PORT/tcp"
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --reload

            log_info "firewalld 防火墙配置完成"
            ;;
    esac

    add_report "防火墙: 已配置 (SSH端口: $SSH_PORT)"
}

# ===== NTP 时间同步 =====
setup_ntp() {
    log_step "NTP 时间同步配置"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将配置 chrony 时间同步"
        return
    fi

    # 安装 chrony
    if ! is_package_installed "chrony"; then
        $PKG_INSTALL_CMD chrony 2>&1 | tail -2
    fi

    # 配置 chrony
    local chrony_conf="/etc/chrony/chrony.conf"
    [[ "$OS_FAMILY" == "rhel" ]] && chrony_conf="/etc/chrony.conf"

    # 备份原配置
    [[ -f "$chrony_conf" ]] && cp "$chrony_conf" "${chrony_conf}.bak"

    # 写入配置
    cat > "$chrony_conf" << 'EOF'
# NTP 服务器配置
server ntp.aliyun.com iburst
server ntp1.aliyun.com iburst
server cn.pool.ntp.org iburst
server time.google.com iburst

# 允许本地网络同步
allow 127.0.0.1/8

# 时间偏移限制
maxdistance 16.0

# RTC 同步
rtcsync

# 时间调整步进阈值（1小时内偏移超过1.0秒会步进调整）
makestep 1.0 3
EOF

    # 启动 chrony
    systemctl enable chronyd
    systemctl restart chronyd

    # 验证同步状态
    sleep 2
    if chronyc tracking &>/dev/null; then
        local offset
        offset=$(chronyc tracking | grep "Last offset" | awk '{print $4}')
        log_info "时间同步正常 (偏移: ${offset} 秒)"
    else
        log_warn "时间同步状态未知"
    fi

    register_rollback "systemctl stop chronyd && systemctl disable chronyd"
    add_report "NTP: chrony 已配置"
}

# ===== sysstat 性能监控配置 =====
setup_sysstat() {
    log_step "sysstat 性能监控配置"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将配置 sysstat"
        return
    fi

    # 安装 sysstat
    if ! is_package_installed "sysstat"; then
        $PKG_INSTALL_CMD sysstat 2>&1 | tail -2
    fi

    # 启用 sysstat 数据收集
    case "$OS_FAMILY" in
        debian)
            sed -i 's/ENABLED="false"/ENABLED="true"/' /etc/default/sysstat 2>/dev/null || true
            ;;
        rhel)
            # RHEL 系默认已启用
            ;;
    esac

    # 配置收集间隔（每 1 分钟收集一次）
    local crontab="/etc/cron.d/sysstat"
    if [[ -f "$crontab" ]]; then
        log_info "sysstat cron 已配置"
    fi

    # 启动服务
    systemctl enable sysstat
    systemctl restart sysstat

    log_info "sysstat 配置完成 (使用 sar 查看性能数据)"
    add_report "sysstat: 已启用"
}

# ===== SSH 安全加固 =====
harden_ssh() {
    log_step "SSH 安全加固"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将加固 SSH 配置"
        return
    fi

    local sshd_config="/etc/ssh/sshd_config"
    local sshd_backup="${sshd_config}.bak.$(date +%Y%m%d)"
    local sshd_hardened="/etc/ssh/sshd_config.d/99-hardened.conf"

    # 备份原配置
    cp "$sshd_config" "$sshd_backup"
    register_rollback "cp $sshd_backup $sshd_config && systemctl restart sshd"

    # 使用 drop-in 配置文件（推荐方式，不修改原文件）
    mkdir -p /etc/ssh/sshd_config.d

    cat > "$sshd_hardened" << EOF
# SSH 安全加固配置
# 生成时间: $(date)

# 禁用密码登录（仅允许密钥认证）
PasswordAuthentication no

# 禁用 root 登录
PermitRootLogin no

# 禁用空密码
PermitEmptyPasswords no

# 使用 SSH 协议 2
Protocol 2

# 修改默认端口（可选，通过参数控制）
# Port $SSH_PORT

# 限制最大认证尝试次数
MaxAuthTries 3

# 登录超时时间
LoginGraceTime 60

# 禁用 X11 转发
X11Forwarding no

# 禁用 TCP 转发（按需开启）
# AllowTcpForwarding no

# 日志级别
LogLevel VERBOSE

# 限制最大会话数
MaxSessions 5

# 客户端活跃检测
ClientAliveInterval 300
ClientAliveCountMax 2

# 允许的用户（根据实际配置）
# AllowUsers $INIT_USER
EOF

    # 确保主配置包含 drop-in 目录
    if ! grep -q "Include /etc/ssh/sshd_config.d/" "$sshd_config"; then
        # 在文件开头添加 Include
        sed -i '1i Include /etc/ssh/sshd_config.d/*.conf' "$sshd_config"
    fi

    # 验证配置
    if sshd -t 2>/dev/null; then
        systemctl restart sshd
        log_info "SSH 加固配置已生效"
    else
        log_error "SSH 配置验证失败，回滚"
        cp "$sshd_backup" "$sshd_config"
        rm -f "$sshd_hardened"
        systemctl restart sshd
        return 1
    fi

    add_report "SSH 加固: 禁用密码登录, 禁用root登录, MaxAuthTries=3"
}

# ===== 内核参数优化 =====
optimize_kernel() {
    log_step "内核参数优化"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将优化内核参数"
        return
    fi

    local sysctl_file="/etc/sysctl.d/99-sre-optimization.conf"

    cat > "$sysctl_file" << 'EOF'
# SRE 内核参数优化
# 生成时间: 自动生成

# ===== 网络优化 =====
# TCP 连接队列大小
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 65535

# TCP 缓冲区
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# TCP 连接复用
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3

# 端口范围
net.ipv4.ip_local_port_range = 1024 65535

# SYN Flood 防护
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 65535

# ===== 内存优化 =====
# 控制 swap 使用倾向（0-100，越低越不倾向使用 swap）
vm.swappiness = 10

# 脏页刷盘策略
vm.dirty_ratio = 60
vm.dirty_background_ratio = 2

# ===== 文件系统优化 =====
# 最大文件句柄数
fs.file-max = 2097152
fs.nr_open = 2097152

# inotify 限制
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512

# ===== 安全加固 =====
# 禁用 ICMP 重定向
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# 开启 SYN Cookie
net.ipv4.tcp_syncookies = 1

# 禁用源路由
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# 开启反向路径过滤
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# 忽略 ICMP 广播
net.ipv4.icmp_echo_ignore_broadcasts = 1
EOF

    # 应用内核参数
    sysctl --system 2>&1 | tail -3

    register_rollback "rm -f $sysctl_file && sysctl --system"
    log_info "内核参数优化完成"
    add_report "内核参数: 已优化 (网络/内存/安全)"
}

# ===== 日志轮转配置 =====
setup_logrotate() {
    log_step "日志轮转配置"

    if $DRY_RUN; then
        log_info "[DRY-RUN] 将配置日志轮转"
        return
    fi

    # 自定义应用日志轮转
    cat > /etc/logrotate.d/sre-apps << 'EOF'
/var/log/sre/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        # 通知 rsyslog 重新打开日志文件
        /usr/lib/rsyslog/rsyslog-rotate 2>/dev/null || true
    endscript
}
EOF

    # 确保日志目录存在
    mkdir -p /var/log/sre

    # 测试 logrotate 配置
    if logrotate -d /etc/logrotate.d/sre-apps &>/dev/null; then
        log_info "日志轮转配置验证通过"
    else
        log_warn "日志轮转配置验证失败"
    fi

    # journalctl 日志大小限制
    mkdir -p /etc/systemd/journald.conf.d
    cat > /etc/systemd/journald.conf.d/size-limit.conf << 'EOF'
[Journal]
SystemMaxUse=500M
MaxRetentionSec=30day
EOF
    systemctl restart systemd-journald

    add_report "日志轮转: 已配置 (保留30天, journal限制500M)"
}

# ===== 生成初始化报告 =====
generate_report() {
    log_step "生成初始化报告"

    local report_file="/etc/server_init_report_$(date +%Y%m%d_%H%M%S).txt"
    local hostname
    hostname=$(hostname)

    cat > "$report_file" << EOF
================================================================================
                    服务器初始化报告
================================================================================

基本信息:
  主机名:       $hostname
  系统:         ${OS_NAME:-未知}
  环境:         $ENVIRONMENT
  初始化时间:   $(date '+%Y-%m-%d %H:%M:%S')
  脚本版本:     $SCRIPT_VERSION
  执行用户:     $(whoami)

初始化结果:
  错误数:       $ERRORS_COUNT
  警告数:       $WARNINGS_COUNT
  状态:         $(if [[ $ERRORS_COUNT -eq 0 ]]; then echo "成功"; else echo "有错误"; fi)

操作明细:
$(echo -e "$INIT_REPORT")

配置文件位置:
  SSH 配置:     /etc/ssh/sshd_config.d/99-hardened.conf
  内核参数:     /etc/sysctl.d/99-sre-optimization.conf
  防火墙:       $(if [[ "$OS_FAMILY" == "debian" ]]; then echo "ufw"; else echo "firewalld"; fi)
  NTP:          chrony
  日志轮转:     /etc/logrotate.d/sre-apps

日志文件:       $LOG_FILE

================================================================================
EOF

    # 标记初始化完成
    echo "$(date '+%Y-%m-%d %H:%M:%S') v${SCRIPT_VERSION}" > /etc/server_init.done

    log_info "初始化报告: $report_file"
    log_info "日志文件: $LOG_FILE"

    # 打印摘要
    echo ""
    echo -e "${BOLD}========================================${NC}"
    echo -e "${BOLD}        服务器初始化完成${NC}"
    echo -e "${BOLD}========================================${NC}"
    echo -e "  系统:    ${OS_NAME:-未知}"
    echo -e "  环境:    $ENVIRONMENT"
    echo -e "  用户:    ${INIT_USER:-$DEFAULT_USER}"
    echo -e "  错误:    ${RED}$ERRORS_COUNT${NC}"
    echo -e "  警告:    ${YELLOW}$WARNINGS_COUNT${NC}"
    echo -e "  报告:    $report_file"
    echo -e "${BOLD}========================================${NC}"
}

# ===== 主入口 =====
main() {
    parse_args "$@"

    echo -e "${BOLD}服务器初始化脚本 v${SCRIPT_VERSION}${NC}"
    echo -e "环境: $ENVIRONMENT | 模式: $(if $DRY_RUN; then echo '模拟运行'; else echo '实际执行'; fi)"
    echo ""

    # 初始化日志
    mkdir -p "$(dirname "$LOG_FILE")"
    log_info "初始化开始 (v${SCRIPT_VERSION}, 环境: $ENVIRONMENT)"

    # 执行初始化步骤
    preflight_checks
    detect_os
    system_update
    setup_user
    install_base_tools
    setup_firewall
    setup_ntp
    setup_sysstat
    harden_ssh
    optimize_kernel
    setup_logrotate

    # 生成报告
    generate_report

    # 返回状态
    if [[ $ERRORS_COUNT -gt 0 ]]; then
        exit 1
    fi
}

main "$@"
```

---

### 5. 脚本使用指南

#### 5.1 基本用法

```bash
# 查看帮助
./server_init.sh --help

# 模拟运行（不实际执行）
./server_init.sh --dry-run --verbose

# 生产环境初始化
./server_init.sh \
    --user deploy \
    --ssh-key /root/.ssh/id_ed25519.pub \
    --env prod \
    --port 22

# 开发环境初始化
./server_init.sh --user dev --env dev --verbose
```

#### 5.2 配置文件支持

除了命令行参数，还可以通过配置文件控制初始化行为：

```bash
# /etc/sre/server_init.conf
# 服务器初始化配置文件

# 用户配置
INIT_USER="sre"
SSH_KEY_FILE="/root/.ssh/id_ed25519.pub"
SSH_PORT=22

# 环境
ENVIRONMENT="staging"

# 时区
TIMEZONE="Asia/Shanghai"

# 额外安装的包
EXTRA_PACKAGES="docker-ce nginx mysql-client"

# 防火墙额外端口
EXTRA_PORTS="3306/tcp 6379/tcp"
```

```bash
# 在脚本中加载配置文件
load_config() {
    local config_file="${1:-/etc/sre/server_init.conf}"
    if [[ -f "$config_file" ]]; then
        log_info "加载配置文件: $config_file"
        # shellcheck source=/dev/null
        source "$config_file"
    fi
}
```

#### 5.3 批量初始化

```bash
#!/bin/bash
# batch_init.sh — 批量服务器初始化

SERVERS=(
    "192.168.1.10"
    "192.168.1.11"
    "192.168.1.12"
)

for host in "${SERVERS[@]}"; do
    echo "===== 初始化 $host ====="

    # 复制脚本到远程服务器
    scp server_init.sh root@$host:/tmp/

    # 远程执行
    ssh root@$host "bash /tmp/server_init.sh \
        --user sre \
        --ssh-key /tmp/sre_key.pub \
        --env staging \
        --verbose"

    echo "$host 初始化完成"
    echo ""
done
```

---

### 6. 脚本工程化进阶

#### 6.1 使用配置模板

```bash
# 使用 Jinja2 风格模板生成配置
render_template() {
    local template=$1
    local output=$2

    sed \
        -e "s/{{HOSTNAME}}/$(hostname)/g" \
        -e "s/{{ENVIRONMENT}}/$ENVIRONMENT/g" \
        -e "s/{{SSH_PORT}}/$SSH_PORT/g" \
        "$template" > "$output"
}
```

#### 6.2 单元测试

```bash
#!/bin/bash
# test_server_init.sh — 初始化脚本测试

# 使用 Docker 容器测试
test_in_container() {
    local distro=$1
    local image=$2

    echo "测试 $distro..."
    docker run --rm -v "$(pwd)/server_init.sh:/tmp/server_init.sh:ro" \
        "$image" bash -c "
            bash /tmp/server_init.sh --dry-run --verbose --env dev
            echo 'EXIT CODE:' \$?
        "
}

# 运行测试
test_in_container "Ubuntu 22.04" "ubuntu:22.04"
test_in_container "Rocky 9" "rockylinux:9"
test_in_container "Debian 12" "debian:12"
```

#### 6.3 CI/CD 集成

```yaml
# .github/workflows/test-init.yml
name: Test Server Init Script

on: [push, pull_request]

jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-22.04, rocky-9, debian-12]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Test init script
        run: |
          docker run --rm -v ${{ github.workspace }}:/workspace \
            ${{ matrix.os }} bash /workspace/server_init.sh --dry-run
```

---

## 💻 实战练习

### 练习 1：基础服务器初始化

编写一个简化的服务器初始化脚本，实现：
1. 检测操作系统类型
2. 更新系统
3. 安装 curl, vim, git, htop
4. 创建一个管理员用户
5. 配置时区为 Asia/Shanghai

```bash
# 你的代码
```

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
set -euo pipefail

# 检查 root
[[ $EUID -ne 0 ]] && { echo "需要 root 权限"; exit 1; }

# 检测 OS
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$ID
else
    echo "无法检测 OS"; exit 1
fi

echo "检测到系统: $OS"

# 更新系统
echo "更新系统..."
case "$OS" in
    ubuntu|debian) apt update -qq && apt install -y curl vim git htop ;;
    rocky|centos|rhel) dnf install -y curl vim git htop ;;
    *) echo "不支持的系统"; exit 1 ;;
esac

# 创建用户
USERNAME="admin"
if ! id "$USERNAME" &>/dev/null; then
    useradd -m -s /bin/bash -G sudo "$USERNAME"
    echo "用户 $USERNAME 创建成功"
else
    echo "用户 $USERNAME 已存在"
fi

# 设置时区
timedatectl set-timezone Asia/Shanghai
echo "时区设置为 Asia/Shanghai"

echo "初始化完成！"
```

</details>

### 练习 2：幂等性改造

以下脚本不是幂等的，执行两次会出错。请改造为幂等版本：

```bash
#!/bin/bash
useradd -m sre
echo "sre ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
mkdir /opt/app
echo "config=value" > /opt/app/config.ini
```

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
set -euo pipefail

# 用户创建（幂等）
if ! id "sre" &>/dev/null; then
    useradd -m -s /bin/bash sre
    echo "用户 sre 创建成功"
else
    echo "用户 sre 已存在，跳过"
fi

# sudoers 配置（幂等）
SUDOERS_LINE="sre ALL=(ALL) NOPASSWD:ALL"
SUDOERS_FILE="/etc/sudoers.d/sre"
if [[ ! -f "$SUDOERS_FILE" ]] || ! grep -qF "$SUDOERS_LINE" "$SUDOERS_FILE" 2>/dev/null; then
    echo "$SUDOERS_LINE" > "$SUDOERS_FILE"
    chmod 440 "$SUDOERS_FILE"
    echo "sudoers 配置完成"
else
    echo "sudoers 已配置，跳过"
fi

# 目录创建（幂等）
mkdir -p /opt/app
echo "目录 /opt/app 已就绪"

# 配置文件（幂等）
CONFIG_FILE="/opt/app/config.ini"
if [[ ! -f "$CONFIG_FILE" ]] || ! grep -q "config=value" "$CONFIG_FILE"; then
    echo "config=value" > "$CONFIG_FILE"
    echo "配置文件已写入"
else
    echo "配置文件已是最新，跳过"
fi

echo "所有操作完成（可安全重复执行）"
```

</details>

### 练习 3：完整初始化脚本

基于本课学到的知识，编写一个完整的服务器初始化脚本，要求：
1. 支持 `--help`、`--user`、`--env` 参数
2. 支持 Ubuntu 和 Rocky Linux
3. 包含用户创建、工具安装、防火墙配置、SSH 加固
4. 幂等设计
5. 生成初始化报告

```bash
# 你的代码（建议 100-200 行）
```

<details>
<summary>参考答案</summary>

参考本课第 4 节的完整脚本实现。关键点：
1. 使用 `set -euo pipefail` 安全模式
2. 函数封装每个步骤
3. `detect_os()` 检测系统类型
4. 每个函数内部检查状态再操作（幂等）
5. `trap` 捕获错误
6. `generate_report()` 生成报告

</details>

### 练习 4：跨发行版兼容性

编写一个函数 `install_package()`，能够：
- 自动检测系统是 Debian 系还是 RHEL 系
- 使用对应的包管理器安装软件
- 检查是否已安装（幂等）

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash

# 检测包管理器
detect_pkg_manager() {
    if command -v apt-get &>/dev/null; then
        PKG_MGR="apt"
        PKG_INSTALL="apt-get install -y -qq"
        PKG_CHECK() { dpkg -l "$1" 2>/dev/null | grep -q "^ii"; }
    elif command -v dnf &>/dev/null; then
        PKG_MGR="dnf"
        PKG_INSTALL="dnf install -y -q"
        PKG_CHECK() { rpm -q "$1" &>/dev/null; }
    elif command -v yum &>/dev/null; then
        PKG_MGR="yum"
        PKG_INSTALL="yum install -y"
        PKG_CHECK() { rpm -q "$1" &>/dev/null; }
    else
        echo "错误: 未找到支持的包管理器"
        return 1
    fi
    echo "包管理器: $PKG_MGR"
}

# 幂等安装
install_package() {
    local pkg=$1
    if PKG_CHECK "$pkg"; then
        echo "[跳过] $pkg 已安装"
        return 0
    fi
    echo "[安装] $pkg..."
    $PKG_INSTALL "$pkg"
    echo "[完成] $pkg 安装成功"
}

# 使用
detect_pkg_manager
install_package "curl"
install_package "vim"
install_package "git"
```

</details>

---

## 🎯 面试题精选

### 面试题 1：什么是幂等性？为什么服务器初始化脚本需要幂等？

**参考答案**：

幂等性（Idempotency）是指一个操作执行一次和执行多次的效果完全相同。在服务器初始化脚本中：

**为什么需要幂等**：
1. **容错重试**：脚本执行到一半失败了，修复后可以重新执行，不需要手动清理
2. **配置漂移修复**：定期执行初始化脚本可以修正配置漂移
3. **批量一致性**：对所有服务器执行相同脚本，确保配置一致
4. **CI/CD 集成**：流水线可能重复触发，脚本必须安全重入

**实现方式**：
- 先检查再操作（如检查用户是否存在再创建）
- 使用工具的幂等选项（如 `apt install` 对已安装的包不报错）
- 使用配置文件的幂等更新（如 `grep + sed` 替换而非追加）
- 使用状态文件记录执行进度

### 面试题 2：如何设计一个通用的服务器初始化方案？

**参考答案**：

一个通用的服务器初始化方案应包含以下层次：

**架构设计**：
```
┌─────────────────────────────────────────┐
│           配置管理层                      │
│  (配置文件/命令行参数/环境变量/CMDB)      │
├─────────────────────────────────────────┤
│           初始化引擎层                    │
│  (参数解析/OS检测/步骤编排/错误处理)      │
├─────────────────────────────────────────┤
│           功能模块层                      │
│  用户管理/安全加固/监控部署/网络配置      │
├─────────────────────────────────────────┤
│           报告与审计层                    │
│  (初始化报告/日志记录/配置快照)           │
└─────────────────────────────────────────┘
```

**关键设计原则**：
1. **模块化**：每个功能独立，可按需组合
2. **幂等性**：重复执行不出错
3. **跨平台**：抽象包管理器和系统服务操作
4. **可配置**：通过配置文件控制行为，而非硬编码
5. **有日志**：每步操作可追溯
6. **可回滚**：失败时能恢复

### 面试题 3：服务器初始化脚本应该包含哪些安全加固步骤？

**参考答案**：

1. **SSH 加固**：禁用密码登录、禁用 root 登录、限制认证尝试次数、修改默认端口
2. **防火墙配置**：默认拒绝入站、仅开放必要端口、按环境差异化配置
3. **用户管理**：创建专用管理用户、配置 sudo 权限、SSH 密钥认证
4. **内核参数**：禁用 ICMP 重定向、开启 SYN Cookie、反向路径过滤
5. **服务最小化**：关闭不必要的服务、仅安装必要软件包
6. **日志审计**：配置审计日志、日志轮转、远程日志收集
7. **时间同步**：确保 NTP 同步，防止日志时间戳混乱

### 面试题 4：如何处理不同 Linux 发行版的差异？

**参考答案**：

```bash
# 1. OS 检测层
detect_os() {
    . /etc/os-release
    OS_ID="$ID"
    case "$OS_ID" in
        ubuntu|debian) OS_FAMILY="debian" ;;
        rocky|centos|rhel) OS_FAMILY="rhel" ;;
    esac
}

# 2. 包管理器抽象
install_pkg() {
    case "$OS_FAMILY" in
        debian) apt-get install -y "$@" ;;
        rhel)   dnf install -y "$@" ;;
    esac
}

# 3. 服务管理抽象
enable_service() {
    systemctl enable "$1"
    systemctl start "$1"
}

# 4. 配置文件路径映射
get_config_path() {
    case "$1" in
        ssh) echo "/etc/ssh/sshd_config" ;;
        chrony)
            [[ "$OS_FAMILY" == "debian" ]] \
                && echo "/etc/chrony/chrony.conf" \
                || echo "/etc/chrony.conf"
            ;;
    esac
}
```

### 面试题 5：`set -euo pipefail` 各选项的作用是什么？

**参考答案**：

- **`set -e`**：任何命令返回非零状态时立即退出脚本。防止错误被忽略继续执行。
- **`set -u`**：引用未定义的变量时报错退出。防止拼写错误导致的变量为空。
- **`set -o pipefail`**：管道中任何命令失败，整个管道返回失败状态。默认情况下只看管道最后一个命令的状态。

组合使用可以最大程度地捕获脚本中的错误，是生产级 Bash 脚本的标配。

**例外处理**：某些命令失败是预期的，用 `|| true` 或 `if` 包裹：
```bash
grep "pattern" file || true  # grep 失败不退出
if command -v tool &>/dev/null; then ... fi
```

### 面试题 6：如何测试服务器初始化脚本？

**参考答案**：

1. **dry-run 模式**：脚本支持 `--dry-run` 参数，只打印将要执行的操作
2. **容器测试**：使用 Docker 容器模拟不同发行版环境
3. **单元测试**：对每个函数编写测试用例
4. **集成测试**：使用 Vagrant/Terraform 创建虚拟机测试完整流程
5. **幂等性测试**：执行两次脚本，验证结果一致
6. **CI/CD 集成**：每次提交自动在多发行版容器中测试

```bash
# Docker 测试示例
docker run --rm -v ./server_init.sh:/tmp/init.sh ubuntu:22.04 \
    bash /tmp/init.sh --dry-run --verbose
```

---

## 📚 深入阅读

### 官方文档
- [Bash 手册](https://www.gnu.org/software/bash/manual/)
- [systemd 服务管理](https://www.freedesktop.org/software/systemd/man/)
- [OpenSSH 配置](https://man.openbsd.org/sshd_config)
- [chrony NTP 配置](https://chrony.tuxfamily.org/documentation.html)

### 推荐资源
- [Google SRE Book](https://sre.google/sre-book/table-of-contents/) — SRE 权威参考
- [The Art of Unix Programming](http://www.catb.org/esr/writings/taoup/) — Unix 编程哲学
- [ShellCheck](https://www.shellcheck.net/) — Shell 脚本静态分析工具
- [Explain Shell](https://explainshell.com/) — Shell 命令解释工具

### 相关工具
- [Ansible](https://docs.ansible.com/) — 配置管理工具（初始化脚本的替代方案）
- [cloud-init](https://cloudinit.readthedocs.io/) — 云服务器初始化标准工具
- [Packer](https://www.packer.io/) — 机器镜像构建工具

---

## ✅ 自检清单

### 理论检查点
- [ ] 理解幂等性设计原则及其在服务器初始化中的重要性
- [ ] 掌握 `set -euo pipefail` 各选项的作用
- [ ] 理解跨发行版兼容性的处理方法
- [ ] 了解服务器初始化脚本的安全加固步骤
- [ ] 理解错误处理和回滚机制的设计

### 实操检查点
- [ ] 能够使用 getopts/长选项解析命令行参数
- [ ] 能够编写带颜色和时间戳的日志函数
- [ ] 能够实现幂等的用户创建和配置写入
- [ ] 能够编写跨发行版的包安装函数
- [ ] 能够配置 SSH 安全加固（禁用密码/禁用 root）
- [ ] 能够配置内核参数优化（sysctl）
- [ ] 能够生成初始化报告
- [ ] 能够使用 `trap` 实现错误处理和回滚

---

*由 SRE 学习计划生成 | 2026-04-25*
