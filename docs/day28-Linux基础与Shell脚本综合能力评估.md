# Day 28: Linux 基础与 Shell 脚本综合能力评估

> 📅 日期：2026-05-02
> 📖 学习主题：Linux 基础与 Shell 脚本综合能力评估
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

- 综合运用前三周所学的 Linux 和 Shell 知识
- 能独立编写复杂的运维脚本
- 掌握脚本的最佳实践和常见陷阱

---

## 📖 综合知识回顾

### 1. Linux 核心知识点

| 领域 | 关键命令 | 用途 |
|------|---------|------|
| 文件操作 | find, cp, mv, rm | 搜索和管理文件 |
| 权限管理 | chmod, chown, chgrp | 设置文件权限和所有者 |
| 进程管理 | ps, top, kill, nice | 监控和控制进程 |
| 网络 | netstat, ss, curl, wget | 网络诊断和访问 |
| 磁盘 | df, du, fdisk, mount | 磁盘空间和分区管理 |
| 日志 | journalctl, tail, grep | 查看和分析日志 |

### 2. Shell 脚本最佳实践

```bash
#!/usr/bin/env bash
set -euo pipefail  # 严格模式

# 使用函数组织代码
main() {
    local config_file="${1:-config.yaml}"
    check_prerequisites
    load_config "$config_file"
    run_task
    cleanup
}

# 使用局部变量
process_data() {
    local input_file=$1
    local output_dir=$2
    # ...
}

# 检查依赖
check_prerequisites() {
    for cmd in curl jq rsync; do
        if ! command -v "$cmd" &>/dev/null; then
            echo "Error: $cmd not found" >&2
            exit 1
        fi
    done
}

main "$@"
```

---

## 🏗️ 实战：完整运维脚本

```bash
#!/usr/bin/env bash
# deploy.sh - 完整部署脚本
set -euo pipefail

# 配置
APP_NAME="myapp"
DEPLOY_DIR="/opt/${APP_NAME}"
BACKUP_DIR="/var/backups/${APP_NAME}"
LOG_FILE="/var/log/${APP_NAME}-deploy.log"
MAX_BACKUPS=5

# 日志函数
log() {
    local level=$1; shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# 前置检查
pre_checks() {
    log INFO "Running pre-deployment checks..."

    if [[ ! -f "build/artifact.tar.gz" ]]; then
        log ERROR "Build artifact not found"
        exit 1
    fi

    if ! command -v systemctl &>/dev/null; then
        log ERROR "systemctl not available"
        exit 1
    fi

    local disk_usage
    disk_usage=$(df "$DEPLOY_DIR" --output=pcent | tail -1 | tr -d ' %')
    if (( disk_usage > 85 )); then
        log ERROR "Disk usage at ${disk_usage}%, deployment aborted"
        exit 1
    fi

    log INFO "Pre-checks passed"
}

# 备份当前版本
backup_current() {
    if [[ -d "$DEPLOY_DIR/current" ]]; then
        mkdir -p "$BACKUP_DIR"
        local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
        cp -r "$DEPLOY_DIR/current" "$BACKUP_DIR/$backup_name"
        log INFO "Backed up to $backup_name"

        # 清理旧备份
        ls -dt "$BACKUP_DIR"/backup-* 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -rf
    fi
}

# 部署新版本
deploy() {
    mkdir -p "$DEPLOY_DIR"
    local release_dir="$DEPLOY_DIR/releases/$(date +%Y%m%d-%H%M%S)"

    log INFO "Extracting artifact to $release_dir"
    mkdir -p "$release_dir"
    tar xzf build/artifact.tar.gz -C "$release_dir"

    # 创建符号链接
    ln -sfn "$release_dir" "$DEPLOY_DIR/current"

    log INFO "Deployment complete"
}

# 健康检查
health_check() {
    local max_wait=30
    local elapsed=0

    log INFO "Waiting for service to become healthy..."
    while (( elapsed < max_wait )); do
        if curl -sf "http://localhost:8080/health" &>/dev/null; then
            log INFO "Service is healthy"
            return 0
        fi
        sleep 2
        ((elapsed += 2))
    done

    log ERROR "Health check timed out after ${max_wait}s"
    return 1
}

# 回滚
rollback() {
    local latest_backup
    latest_backup=$(ls -dt "$BACKUP_DIR"/backup-* 2>/dev/null | head -1)

    if [[ -n "$latest_backup" ]]; then
        log WARN "Rolling back to $latest_backup"
        ln -sfn "$latest_backup" "$DEPLOY_DIR/current"
        systemctl restart "$APP_NAME"
    else
        log ERROR "No backup found for rollback"
        exit 1
    fi
}

# 主流程
main() {
    log INFO "Starting deployment of $APP_NAME"

    pre_checks
    backup_current

    if ! deploy; then
        log ERROR "Deployment failed, rolling back"
        rollback
        exit 1
    fi

    systemctl restart "$APP_NAME"

    if ! health_check; then
        log ERROR "Health check failed, rolling back"
        rollback
        exit 1
    fi

    log INFO "Deployment successful"
}

main "$@"
```

---

## 🧪 综合练习

### 练习 1：日志轮转脚本

编写一个脚本，每天凌晨 2 点轮转 /var/log/myapp/ 下的日志文件，保留最近 30 天，压缩旧日志。

<details>
<summary>答案</summary>

```bash
#!/bin/bash
LOG_DIR="/var/log/myapp"
RETAIN_DAYS=30
DATE=$(date +%Y%m%d)

mkdir -p "$LOG_DIR/archive"

for f in "$LOG_DIR"/*.log; do
    [[ -f "$f" ]] || continue
    base=$(basename "$f" .log)
    cp "$f" "$LOG_DIR/archive/${base}-${DATE}.log"
    truncate -s 0 "$f"
done

find "$LOG_DIR/archive" -name "*.log" -mtime +$RETAIN_DAYS -exec gzip {} \;
find "$LOG_DIR/archive" -name "*.gz" -mtime +$((RETAIN_DAYS * 2)) -delete
```
</details>

---

## 📚 扩展阅读

- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- [Bash Best Practices](https://wiki.bash-hackers.org/scripting/bestpractices)


### 3. 常见 Shell 陷阱

hello world
hello world
0
still running

### 4. 脚本调试技巧


