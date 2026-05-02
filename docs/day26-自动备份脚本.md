# Day 26: 实战项目 — 自动备份脚本

> 📅 日期：2026-04-25
> 📖 学习主题：实战项目：自动备份脚本
> ⏰ 计划学习时间：2-3 小时

---

## 🎯 学习目标

完成 Day 26 的学习后，你应该掌握：
- 理解备份的 3-2-1 原则和 RPO/RTO 概念
- 掌握 tar/rsync 在备份中的最佳实践
- 能够编写支持增量备份、完整性校验、自动清理的备份脚本
- 理解数据库热备份与冷备份的区别
- 掌握备份到远程存储（SSH/S3）的方法

---

## 📖 底层原理详解

### 1. 备份理论基础

#### 1.1 3-2-1 备份原则

| 原则 | 含义 | SRE 实践 |
|------|------|----------|
| **3** 份数据副本 | 1 份原始 + 2 份备份 | 生产数据 + 本地备份 + 异地备份 |
| **2** 种不同介质 | 不同存储类型 | 本地磁盘 + 云对象存储（S3/OSS） |
| **1** 份异地备份 | 地理隔离 | 跨区域复制（如华东 → 华北） |

#### 1.2 RPO 与 RTO

- **RPO (Recovery Point Objective)**：可容忍的最大数据丢失量
  - RPO = 0：需要实时同步（如数据库主从）
  - RPO = 24h：每日备份即可
- **RTO (Recovery Time Objective)**：可容忍的最大恢复时间
  - RTO < 1h：需要热备/快速恢复方案
  - RTO < 24h：标准备份恢复即可

#### 1.3 备份类型对比

| 类型 | 原理 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|----------|
| 全量备份 | 每次备份全部数据 | 恢复简单 | 耗时长、占用大 | 每周/每月 |
| 增量备份 | 仅备份上次备份后的变化 | 快速、省空间 | 恢复需逐层 | 每日 |
| 差异备份 | 备份上次全量后的所有变化 | 恢复只需两层 | 随时间增长 | 每日 |
| 快照 | 文件系统级时间点拷贝 | 瞬时完成 | 依赖存储支持 | 数据库、VM |

### 2. 核心备份命令

#### 2.1 tar 备份

```bash
# 创建备份
tar czf backup_$(date +%Y%m%d).tar.gz \
    --exclude='*.log' \
    --exclude='cache/' \
    /etc /var/www

# 带校验的备份（生成 SHA256）
tar czf backup.tar.gz /data
sha256sum backup.tar.gz > backup.tar.gz.sha256

# 验证备份完整性
sha256sum -c backup.tar.gz.sha256

# 列出备份内容（不解压）
tar tzf backup.tar.gz

# 恢复单个文件
tar xzf backup.tar.gz etc/nginx/nginx.conf

# 增量备份（使用 --listed-incremental）
# 第一次（全量）
tar czf full_backup.tar.gz --listed-incremental=snapshot.snar /data
# 第二次（增量）
tar czf incr_backup.tar.gz --listed-incremental=snapshot.snar /data
```

#### 2.2 rsync 同步备份

```bash
# 基本同步
rsync -avz /data/ backup@remote:/backup/data/

# 关键参数：
# -a : 归档模式（保留权限、时间、链接）
# -v : 详细输出
# -z : 压缩传输
# --delete : 删除目标端多余文件（镜像同步）
# --backup : 覆盖时创建备份
# --backup-dir : 指定备份目录
# --exclude : 排除模式

# 带备份的同步（旧文件移到 backup-dir）
rsync -avz --delete \
    --backup --backup-dir=/backup/old_$(date +%Y%m%d) \
    /data/ backup@remote:/backup/data/

# 限速传输
rsync -avz --bwlimit=10000 /data/ remote:/backup/  # 10MB/s
```

#### 2.3 数据库备份

```bash
# MySQL 热备份
mysqldump -u root -p --all-databases \
    --single-transaction \
    --routines --triggers \
    --events \
    | gzip > mysql_backup_$(date +%Y%m%d).sql.gz

# MySQL 单库备份
mysqldump -u root -p mydb \
    --single-transaction \
    | gzip > mydb_backup_$(date +%Y%m%d).sql.gz

# PostgreSQL 备份
pg_dump -U postgres mydb | gzip > pg_backup_$(date +%Y%m%d).sql.gz

# PostgreSQL 全集群备份
pg_dumpall -U postgres | gzip > pg_all_backup_$(date +%Y%m%d).sql.gz

# Redis 备份（RDB 快照）
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/redis_$(date +%Y%m%d).rdb
```

---

## 💻 实战项目：企业级自动备份脚本

### 完整实现

```bash
#!/bin/bash
# auto_backup.sh — 企业级自动备份脚本
# 支持：全量/增量、完整性校验、自动清理、远程同步
set -euo pipefail

# ===== 配置区 =====
BACKUP_BASE="/backup"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE/$BACKUP_DATE"

# 备份源
BACKUP_PATHS=(
    "/etc"
    "/var/www"
    "/opt/app/config"
)

# 排除模式
EXCLUDE_PATTERNS=(
    "*.tmp"
    "*.cache"
    "node_modules"
    "__pycache__"
    ".git"
)

# 保留策略
KEEP_DAILY=7
KEEP_WEEKLY=4
KEEP_MONTHLY=12

# 远程备份（可选）
REMOTE_BACKUP_ENABLED="${REMOTE_BACKUP_ENABLED:-false}"
REMOTE_HOST="${REMOTE_HOST:-backup-server}"
REMOTE_PATH="${REMOTE_PATH:-/backup}"
REMOTE_USER="${REMOTE_USER:-backup}"

# 日志
LOG_FILE="/var/log/auto_backup.log"
LOCK_FILE="/tmp/auto_backup.lock"

# ===== 函数区 =====

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# 防止重复运行
acquire_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "❌ 备份进程已在运行 (PID: $pid)"
            exit 1
        else
            log "⚠️  发现过期锁文件，清理中..."
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"' EXIT
}

# 创建备份目录
prepare_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    log "📁 备份目录: $BACKUP_DIR"
}

# 构建 tar 排除参数
build_exclude_args() {
    local args=""
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        args="$args --exclude=$pattern"
    done
    echo "$args"
}

# 文件系统备份
backup_filesystem() {
    log "📦 开始文件系统备份..."

    local exclude_args
    exclude_args=$(build_exclude_args)

    local total=${#BACKUP_PATHS[@]}
    local current=0

    for path in "${BACKUP_PATHS[@]}"; do
        ((current++))
        local safe_name=$(echo "$path" | tr '/' '_')
        local archive="$BACKUP_DIR/fs_${safe_name}.tar.gz"

        if [[ ! -d "$path" && ! -f "$path" ]]; then
            log "⚠️  跳过不存在的路径: $path"
            continue
        fi

        log "[$current/$total] 备份 $path ..."
        eval tar czf "$archive" $exclude_args \
            -C / "$(echo "$path" | sed 's|^/||')"

        # 生成校验和
        sha256sum "$archive" > "${archive}.sha256"

        local size=$(du -sh "$archive" | cut -f1)
        log "✅ 完成: $archive ($size)"
    done
}

# 数据库备份
backup_databases() {
    log "🗄️  开始数据库备份..."

    local db_backup_dir="$BACKUP_DIR/databases"
    mkdir -p "$db_backup_dir"

    # MySQL 备份
    if command -v mysqldump &>/dev/null; then
        log "备份 MySQL..."
        local mysql_file="$db_backup_dir/mysql_all.sql.gz"

        if mysqldump -u root --all-databases \
            --single-transaction \
            --routines --triggers \
            2>/dev/null | gzip > "$mysql_file"; then
            sha256sum "$mysql_file" > "${mysql_file}.sha256"
            local size=$(du -sh "$mysql_file" | cut -f1)
            log "✅ MySQL 备份完成 ($size)"
        else
            log "❌ MySQL 备份失败（可能未运行或权限不足）"
        fi
    fi

    # Redis 备份
    if command -v redis-cli &>/dev/null; then
        log "备份 Redis..."
        if redis-cli BGSAVE 2>/dev/null; then
            sleep 2  # 等待 BGSAVE 完成
            local redis_file="$db_backup_dir/redis_dump.rdb"
            if cp /var/lib/redis/dump.rdb "$redis_file" 2>/dev/null; then
                gzip "$redis_file"
                log "✅ Redis 备份完成"
            fi
        fi
    fi
}

# 生成备份清单
create_manifest() {
    log "📋 生成备份清单..."

    local manifest="$BACKUP_DIR/MANIFEST.txt"

    cat > "$manifest" << EOF
=====================================
备份清单
=====================================
日期: $(date '+%Y-%m-%d %H:%M:%S')
主机名: $(hostname)
内核: $(uname -r)

备份路径:
EOF

    for path in "${BACKUP_PATHS[@]}"; do
        echo "  - $path" >> "$manifest"
    done

    echo "" >> "$manifest"
    echo "文件列表:" >> "$manifest"
    find "$BACKUP_DIR" -type f -exec ls -lh {} \; >> "$manifest"

    echo "" >> "$manifest"
    echo "校验和:" >> "$manifest"
    find "$BACKUP_DIR" -name "*.sha256" -exec cat {} \; >> "$manifest"

    log "✅ 清单已生成: $manifest"
}

# 远程同步
sync_to_remote() {
    if [[ "$REMOTE_BACKUP_ENABLED" != "true" ]]; then
        return
    fi

    log "🌐 同步到远程存储: $REMOTE_HOST:$REMOTE_PATH"

    rsync -avz --delete \
        -e "ssh -o StrictHostKeyChecking=no" \
        "$BACKUP_DIR/" \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/${BACKUP_DATE}/"

    log "✅ 远程同步完成"
}

# 清理旧备份
cleanup_old_backups() {
    log "🧹 清理旧备份..."

    # 按日保留
    local daily_count
    daily_count=$(find "$BACKUP_BASE" -maxdepth 1 -type d -name "20*" | \
                  sort | head -n -$KEEP_DAILY | wc -l)

    if [[ $daily_count -gt 0 ]]; then
        find "$BACKUP_BASE" -maxdepth 1 -type d -name "20*" | \
            sort | head -n -$KEEP_DAILY | \
        while read -r old_dir; do
            log "删除旧备份: $old_dir"
            rm -rf "$old_dir"
        done
    fi

    # 计算当前备份总大小
    local total_size
    total_size=$(du -sh "$BACKUP_BASE" 2>/dev/null | cut -f1)
    log "📊 备份总大小: $total_size"
}

# 验证备份完整性
verify_backup() {
    log "🔍 验证备份完整性..."

    local errors=0
    for sha_file in "$BACKUP_DIR"/*.sha256; do
        if [[ -f "$sha_file" ]]; then
            if ! sha256sum -c "$sha_file" &>/dev/null; then
                log "❌ 校验失败: $sha_file"
                ((errors++))
            fi
        fi
    done

    if [[ $errors -eq 0 ]]; then
        log "✅ 所有备份文件校验通过"
    else
        log "❌ $errors 个文件校验失败！"
        return 1
    fi
}

# ===== 主入口 =====

main() {
    log "========================================="
    log "🚀 自动备份开始"
    log "========================================="

    acquire_lock
    prepare_backup_dir
    backup_filesystem
    backup_databases
    create_manifest
    verify_backup
    sync_to_remote
    cleanup_old_backups

    local total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "========================================="
    log "✅ 备份完成: $BACKUP_DIR ($total_size)"
    log "========================================="
}

main "$@"
```

### Cron 定时任务

```bash
# 每天凌晨 2 点执行全量备份
0 2 * * * /opt/scripts/auto_backup.sh >> /var/log/auto_backup_cron.log 2>&1

# 每周日检查备份完整性
0 4 * * 0 find /backup -name "*.sha256" -exec sha256sum -c {} \; >> /var/log/backup_verify.log 2>&1
```

---

## 🧪 练习题

### 练习 1：实现增量备份
```bash
# 修改脚本，支持增量备份：
# - 每周日全量，周一至周六增量
# - 使用 rsync 的 --link-dest 实现硬链接增量
```

<details>
<summary>答案</summary>

```bash
# 找到最近的全量备份
latest_full=$(ls -d /backup/20*full 2>/dev/null | sort | tail -1)

if [[ -z "$latest_full" ]]; then
    backup_type="full"
    backup_dir="/backup/$(date +%Y%m%d)_full"
else
    backup_type="incremental"
    backup_dir="/backup/$(date +%Y%m%d)_incr"
    rsync -avz --delete --link-dest="$latest_full" \
        /data/ "$backup_dir/"
fi
```
</details>

### 练习 2：备份到 S3
```bash
# 使用 aws cli 将备份上传到 S3
```

<details>
<summary>答案</summary>

```bash
aws s3 sync "$BACKUP_DIR" \
    s3://my-backup-bucket/$(hostname)/$BACKUP_DATE/ \
    --storage-class STANDARD_IA \
    --sse AES256

# 设置生命周期策略（自动转 Glacier）
# 在 AWS Console 或通过 CLI 设置：
# 30 天后 → STANDARD_IA
# 90 天后 → GLACIER
# 365 天后 → 删除
```
</details>

---

## 📚 扩展阅读

- [3-2-1 备份原则](https://www.backblaze.com/blog/the-3-2-1-backup-strategy/) — Backblaze 经典文章
- `man tar`、`man rsync` — 命令手册
- [Borg Backup](https://www.borgbackup.org/) — 现代去重备份工具
- [Restic](https://restic.net/) — 安全高效的备份工具
- [Google SRE: Data Processing Pipelines](https://sre.google/sre-book/data-processing/)

---

*由 SRE 学习计划自动生成 | 2026-04-25*
*Generated by Hermes Agent with review*
