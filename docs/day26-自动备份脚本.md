# Day 26: 实战项目 -- 自动备份脚本

> 📅 日期：2026-04-26
> 📖 学习主题：实战项目 -- 自动备份脚本
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 25（日志监控告警脚本）、Day 12（磁盘管理）、Day 04（文本处理三剑客）

---

## 🎯 学习目标

完成 Day 26 的学习后，你应该能够：
- 理解并应用 3-2-1 备份原则，设计企业级备份策略
- 掌握 tar 全量备份 + rsync 增量备份的完整实现
- 编写支持完整性校验（MD5/SHA256）、自动清理、远程同步的生产级备份脚本
- 理解 RPO/RTO 概念，能根据业务需求选择合适的备份方案
- 掌握 MySQL（mysqldump/xtrabackup）和 PostgreSQL（pg_dump）的数据库备份方法
- 理解 flock 锁机制，防止备份脚本重复执行
- 能够设计并执行恢复测试，验证备份有效性

---

## 📖 核心知识点

### 1. 备份理论基础

#### 1.1 3-2-1 备份原则

3-2-1 原则是数据备份的黄金法则，由摄影师 Peter Krogh 提出，后被广泛应用于 IT 领域：

```
┌─────────────────────────────────────────────────────────────┐
│                    3-2-1 备份原则                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   3 份数据副本                                               │
│   ├── 1 份：生产数据（原始数据）                              │
│   ├── 2 份：本地备份（快速恢复）                              │
│   └── 3 份：异地备份（灾难恢复）                              │
│                                                             │
│   2 种不同存储介质                                            │
│   ├── 介质 A：本地磁盘 / NAS                                 │
│   └── 介质 B：云对象存储（S3/OSS/COS）                       │
│                                                             │
│   1 份异地/离线备份                                           │
│   └── 跨区域 / 跨机房 / 离线磁带                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

| 原则 | 含义 | SRE 实践 | 反面案例 |
|------|------|----------|----------|
| **3** 份数据副本 | 1 份原始 + 2 份备份 | 生产数据 + 本地备份 + 异地备份 | 只有一份数据，磁盘坏了就没了 |
| **2** 种不同介质 | 不同存储类型 | 本地磁盘 + 云对象存储 | 两份都在同一块磁盘上 |
| **1** 份异地备份 | 地理隔离 | 跨区域复制（如华东 -> 华北） | 所有备份在同一机房，火灾全丢 |

#### 1.2 RPO 与 RTO

这两个指标是备份策略设计的核心约束：

```
时间轴 ──────────────────────────────────────────────────>

     │◄──── RPO ────►│              │◄──── RTO ────►│
     │                │              │                │
     ▼                ▼              ▼                ▼
  最后一次备份    数据丢失点      故障发生        服务恢复
  (恢复点)       (灾难发生)      (开始恢复)      (恢复完成)
```

- **RPO (Recovery Point Objective)**：可容忍的最大数据丢失量
  - RPO = 0：零数据丢失，需要实时同步（如数据库主从复制）
  - RPO = 1h：最多丢失 1 小时数据，需要每小时备份
  - RPO = 24h：最多丢失 1 天数据，每日备份即可

- **RTO (Recovery Time Objective)**：可容忍的最大恢复时间
  - RTO < 15min：需要热备 + 自动切换（如数据库主从 failover）
  - RTO < 1h：需要快速恢复方案（如快照恢复）
  - RTO < 24h：标准备份恢复即可

**RPO/RTO 与备份策略的关系**：

| 业务类型 | RPO | RTO | 推荐策略 |
|----------|-----|-----|----------|
| 核心数据库 | 0 | < 15min | 主从复制 + 实时同步 |
| 应用服务器 | < 1h | < 1h | 每小时增量 + 快照 |
| 文件服务器 | < 24h | < 4h | 每日全量 + 增量 |
| 开发环境 | < 7d | < 24h | 每周全量 |
| 日志数据 | 可丢失 | N/A | 无需备份 |

#### 1.3 备份类型对比

```
全量备份 (Full Backup)
┌──────────────────────────────────────┐
│ Day1: [A][B][C][D][E]  全部备份      │  5 个数据块
│ Day2: [A][B][C][D][E]  全部备份      │  5 个数据块
│ Day3: [A][B][C][D][E]  全部备份      │  5 个数据块
└──────────────────────────────────────┘
总计: 15 个数据块 | 恢复: 只需 1 份

增量备份 (Incremental Backup)
┌──────────────────────────────────────┐
│ Day1: [A][B][C][D][E]  全量          │  5 个数据块
│ Day2: [  ][  ][C']      仅变化       │  1 个数据块
│ Day3: [  ][  ][  ][D']  仅变化       │  1 个数据块
└──────────────────────────────────────┘
总计: 7 个数据块 | 恢复: 需全量 + Day2 + Day3

差异备份 (Differential Backup)
┌──────────────────────────────────────┐
│ Day1: [A][B][C][D][E]  全量          │  5 个数据块
│ Day2: [  ][  ][C']      全量后变化   │  1 个数据块
│ Day3: [  ][  ][C'][D']  全量后变化   │  2 个数据块
└──────────────────────────────────────┘
总计: 8 个数据块 | 恢复: 只需全量 + 最新差异
```

| 类型 | 原理 | 备份速度 | 恢复速度 | 空间占用 | 适用场景 |
|------|------|----------|----------|----------|----------|
| 全量备份 | 每次备份全部数据 | 慢 | 最快 | 最大 | 每周/每月 |
| 增量备份 | 仅备份上次备份后的变化 | 最快 | 慢（逐层） | 最小 | 每日 |
| 差异备份 | 备份上次全量后的所有变化 | 中等 | 较快（两层） | 中等 | 每日 |
| 快照 | 文件系统级时间点拷贝 | 瞬时 | 快 | 依赖去重 | 数据库、VM |

#### 1.4 压缩算法对比

备份文件通常需要压缩以节省存储空间和传输带宽：

| 算法 | 压缩率 | 压缩速度 | 解压速度 | CPU 占用 | 适用场景 |
|------|--------|----------|----------|----------|----------|
| gzip (.tar.gz) | 中等 | 快 | 最快 | 低 | 日常备份（默认选择） |
| bzip2 (.tar.bz2) | 较高 | 慢 | 中等 | 高 | 归档存储（不急的场景） |
| xz (.tar.xz) | 最高 | 最慢 | 中等 | 最高 | 长期归档（空间敏感） |
| lz4 | 较低 | 最快 | 最快 | 最低 | 实时备份、日志压缩 |
| zstd | 高 | 快 | 快 | 中等 | 现代替代方案（推荐） |

```bash
# 压缩率对比（以 1GB 日志文件为例）
time tar czf test.tar.gz /data/logs     # gzip:  ~200MB, 15s
time tar cjf test.tar.bz2 /data/logs    # bzip2: ~170MB, 45s
time tar cJf test.tar.xz /data/logs     # xz:    ~150MB, 90s
time tar --zstd -cf test.tar.zst /data/logs  # zstd:  ~160MB, 10s

# 解压速度对比
time tar xf test.tar.gz     # gzip:  8s
time tar xf test.tar.bz2    # bzip2: 20s
time tar xf test.tar.xz     # xz:    15s
time tar --zstd -xf test.tar.zst  # zstd: 5s
```

**SRE 建议**：日常备份使用 gzip（平衡速度和压缩率），长期归档使用 zstd（最佳综合表现）。

### 2. 核心备份命令详解

#### 2.1 tar 归档工具

tar（tape archive）是 Linux 最基础的归档工具，它将多个文件打包成一个文件，但不压缩（压缩由 gzip/bzip2/xz 完成）。

```bash
# 创建备份
tar czf backup_$(date +%Y%m%d).tar.gz \
    --exclude='*.log' \
    --exclude='cache/' \
    /etc /var/www

# 关键参数解析：
# -c : create，创建归档
# -x : extract，解压归档
# -t : list，列出归档内容
# -z : gzip 压缩
# -j : bzip2 压缩
# -J : xz 压缩
# -v : verbose，详细输出
# -f : file，指定文件名
# -C : 指定解压目录
# --exclude : 排除模式
# --listed-incremental : 增量备份

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
# 第二次（增量）-- 只打包自上次以来变化的文件
tar czf incr_backup.tar.gz --listed-incremental=snapshot.snar /data
# 恢复增量备份（必须按顺序：全量 -> 增量1 -> 增量2）
tar xzf full_backup.tar.gz --listed-incremental=/dev/null
tar xzf incr_backup.tar.gz --listed-incremental=/dev/null
```

**tar 增量备份原理**：

```
Day 0 (周日): 全量备份
├── snapshot.snar 记录所有文件的 inode 信息
└── full_backup.tar.gz 包含所有文件

Day 1 (周一): 增量备份
├── snapshot.snar 更新为 Day 0 后的状态
└── incr_day1.tar.gz 只包含 Day 0 之后变化的文件

Day 2 (周二): 增量备份
├── snapshot.snar 更新为 Day 1 后的状态
└── incr_day2.tar.gz 只包含 Day 1 之后变化的文件

恢复顺序: full -> incr_day1 -> incr_day2
```

#### 2.2 rsync 远程同步

rsync 是 SRE 最常用的同步工具，支持增量传输、压缩、断点续传：

```bash
# 基本同步
rsync -avz /data/ backup@remote:/backup/data/

# 关键参数：
# -a : archive 模式（保留权限、时间、符号链接、设备文件等）
# -v : verbose 详细输出
# -z : 压缩传输
# -P : 等于 --partial --progress（断点续传 + 进度显示）
# --delete : 删除目标端多余文件（镜像同步）
# --backup : 覆盖前备份旧文件
# --backup-dir : 指定旧文件备份目录
# --exclude : 排除模式
# --link-dest : 硬链接到指定目录（实现增量备份）
# --bwlimit : 限速（KB/s）

# 带备份的同步（旧文件移到 backup-dir）
rsync -avz --delete \
    --backup --backup-dir=/backup/old_$(date +%Y%m%d) \
    /data/ backup@remote:/backup/data/

# 限速传输（不影响业务带宽）
rsync -avz --bwlimit=10000 /data/ remote:/backup/  # 10MB/s

# 排除多个模式
rsync -avz --exclude='*.log' --exclude='.git' \
    --exclude='node_modules' \
    /app/ remote:/backup/app/

# SSH 指定端口和密钥
rsync -avz -e "ssh -p 2222 -i /root/.ssh/backup_key" \
    /data/ backup@remote:/backup/
```

**rsync --link-dest 实现高效增量备份**：

```bash
#!/bin/bash
# 使用 rsync --link-dest 实现硬链接增量备份
# 未变化的文件通过硬链接共享，不占用额外空间

BACKUP_ROOT="/backup"
LATEST_LINK="$BACKUP_ROOT/latest"
DATE_DIR="$BACKUP_ROOT/$(date +%Y%m%d)"

rsync -avz --delete \
    --link-dest="$LATEST_LINK" \
    /data/ "$DATE_DIR/"

# 更新 latest 链接指向最新备份
ln -sfn "$DATE_DIR" "$LATEST_LINK"
```

```
目录结构：
/backup/
├── 20260420/     # 全量备份（所有文件都是实体）
│   ├── file1
│   ├── file2
│   └── file3
├── 20260421/     # 增量备份
│   ├── file1     # 硬链接 → 20260420/file1（未变化）
│   ├── file2     # 新实体（已变化）
│   └── file3     # 硬链接 → 20260420/file3（未变化）
├── 20260422/     # 增量备份
│   ├── file1     # 硬链接 → 20260420/file1
│   ├── file2     # 硬链接 → 20260421/file2
│   └── file3     # 新实体（已变化）
└── latest → 20260422  # 符号链接指向最新
```

#### 2.3 校验和验证

备份文件必须验证完整性，否则可能在需要恢复时发现文件损坏：

```bash
# MD5 校验（速度快，但安全性较低）
md5sum backup.tar.gz > backup.tar.gz.md5
md5sum -c backup.tar.gz.md5    # 验证

# SHA256 校验（推荐，安全性高）
sha256sum backup.tar.gz > backup.tar.gz.sha256
sha256sum -c backup.tar.gz.sha256    # 验证

# 批量校验
find /backup -name "*.tar.gz" -exec sha256sum {} \; > /backup/checksums.sha256
sha256sum -c /backup/checksums.sha256

# 校验脚本
verify_checksums() {
    local backup_dir=$1
    local errors=0

    for sha_file in "$backup_dir"/*.sha256; do
        [[ -f "$sha_file" ]] || continue
        if sha256sum -c "$sha_file" &>/dev/null; then
            echo "OK: $sha_file"
        else
            echo "FAIL: $sha_file"
            ((errors++))
        fi
    done

    return $errors
}
```

#### 2.4 自动清理过期备份

```bash
# 使用 find 清理超过 N 天的备份
find /backup -name "*.tar.gz" -mtime +30 -delete

# 更精细的保留策略
cleanup_backups() {
    local backup_root=$1
    local keep_daily=${2:-7}
    local keep_weekly=${3:-4}
    local keep_monthly=${4:-12}

    # 删除超过 keep_daily 天的每日备份
    find "$backup_root/daily" -maxdepth 1 -type d -mtime +$keep_daily \
        -exec rm -rf {} +

    # 删除超过 keep_weekly*7 天的每周备份
    find "$backup_root/weekly" -maxdepth 1 -type d \
        -mtime +$((keep_weekly * 7)) -exec rm -rf {} +

    # 删除超过 keep_monthly*30 天的每月备份
    find "$backup_root/monthly" -maxdepth 1 -type d \
        -mtime +$((keep_monthly * 30)) -exec rm -rf {} +

    # 清理孤立的校验文件
    find "$backup_root" -name "*.sha256" | while read -r sha_file; do
        local data_file="${sha_file%.sha256}"
        [[ -f "$data_file" ]] || rm -f "$sha_file"
    done
}
```

#### 2.5 flock 锁机制

备份脚本必须防止重复执行，否则可能导致数据不一致或备份损坏：

```bash
#!/bin/bash
# 方法 1：使用 flock（推荐）
LOCK_FILE="/tmp/auto_backup.lock"

# flock -n: 非阻塞，获取不到锁立即退出
# flock -x: 独占锁
# flock -w 60: 最多等待 60 秒
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    echo "[$(date)] 备份脚本已在运行，退出" >&2
    exit 1
fi

# 也可以用一行命令包装整个脚本
# flock -n /tmp/backup.lock /opt/scripts/backup.sh

# 方法 2：使用 PID 文件（传统方式）
acquire_lock() {
    local lock_file="/tmp/auto_backup.lock"

    if [[ -f "$lock_file" ]]; then
        local old_pid
        old_pid=$(cat "$lock_file")
        if kill -0 "$old_pid" 2>/dev/null; then
            echo "备份进程已在运行 (PID: $old_pid)" >&2
            exit 1
        else
            echo "发现过期锁文件 (PID: $old_pid 已不存在)，清理中..."
            rm -f "$lock_file"
        fi
    fi

    echo $$ > "$lock_file"
    trap 'rm -f "$lock_file"' EXIT
}
```

**flock 的底层机制**：

```
flock 使用 Linux 内核的文件锁机制 (fcntl/lockf)
├── 锁类型：
│   ├── 排他锁 (LOCK_EX) - 写锁，只有一个进程能持有
│   ├── 共享锁 (LOCK_SH) - 读锁，多个进程可同时持有
│   └── 解锁 (LOCK_UN)
├── 锁粒度：文件级别
└── 锁生命周期：进程退出或显式释放

执行流程：
1. 进程 A 尝试获取锁 -> 成功 -> 执行备份
2. 进程 B 尝试获取锁 -> 失败（A 已持有） -> 退出
3. 进程 A 完成 -> 释放锁 -> 进程 C 可以获取
```

### 3. 数据库备份

#### 3.1 MySQL 备份

**mysqldump（逻辑备份）**：

```bash
# 全库备份
mysqldump -u root -p --all-databases \
    --single-transaction \
    --routines --triggers --events \
    --flush-logs \
    | gzip > mysql_full_$(date +%Y%m%d).sql.gz

# 单库备份
mysqldump -u root -p mydb \
    --single-transaction \
    | gzip > mydb_$(date +%Y%m%d).sql.gz

# 单表备份
mysqldump -u root -p mydb users orders \
    --single-transaction > mydb_tables.sql

# 关键参数说明：
# --single-transaction : InnoDB 一致性快照（不锁表）
# --routines : 包含存储过程
# --triggers : 包含触发器
# --events : 包含定时事件
# --flush-logs : 刷新日志（配合 binlog 做增量恢复）
# --master-data=2 : 记录 binlog 位点（注释形式）

# 恢复
gunzip < mysql_full_20260426.sql.gz | mysql -u root -p
# 或
mysql -u root -p < mysql_full_20260426.sql
```

**xtrabackup（物理备份，适合大型数据库）**：

```bash
# 安装（Percona XtraBackup）
# apt install percona-xtrabackup-80
# 或 yum install percona-xtrabackup-80

# 全量备份
xtrabackup --backup \
    --target-dir=/backup/full \
    --user=root --password=xxx

# 准备备份（应用日志）
xtrabackup --prepare --target-dir=/backup/full

# 增量备份
xtrabackup --backup \
    --target-dir=/backup/incr1 \
    --incremental-basedir=/backup/full \
    --user=root --password=xxx

# 恢复
systemctl stop mysql
rm -rf /var/lib/mysql/*
xtrabackup --copy-back --target-dir=/backup/full
chown -R mysql:mysql /var/lib/mysql
systemctl start mysql
```

**mysqldump vs xtrabackup**：

| 特性 | mysqldump | xtrabackup |
|------|-----------|------------|
| 备份类型 | 逻辑备份（SQL 语句） | 物理备份（文件拷贝） |
| 备份速度 | 慢（大库） | 快 |
| 恢复速度 | 慢（重新执行 SQL） | 快（直接拷贝） |
| 锁表 | --single-transaction 不锁 | 不锁表 |
| 增量备份 | 不支持（需配合 binlog） | 支持 |
| 适用规模 | < 50GB | 任意大小 |
| 备份格式 | SQL 文本 | 二进制文件 |

#### 3.2 PostgreSQL 备份

```bash
# 单库备份
pg_dump -U postgres -d mydb \
    -Fc \
    -f mydb_$(date +%Y%m%d).dump

# -Fc : 自定义格式（可压缩，支持并行恢复）
# -Fp : SQL 文本格式
# -Fd : 目录格式（支持并行备份和恢复）

# 全集群备份
pg_dumpall -U postgres | gzip > pg_all_$(date +%Y%m%d).sql.gz

# 仅备份 schema（不含数据）
pg_dump -U postgres -d mydb --schema-only > schema.sql

# 仅备份数据
pg_dump -U postgres -d mydb --data-only > data.sql

# 恢复（自定义格式）
pg_restore -U postgres -d mydb -Fc mydb_20260426.dump

# 恢复（SQL 格式）
psql -U postgres -d mydb < backup.sql

# 使用 pg_basebackup 做物理备份
pg_basebackup -U replicator -D /backup/pg_base \
    -Fp -Xs -P -R

# -Fp : plain 格式
# -Xs : stream WAL
# -P : 显示进度
# -R : 创建 standby 配置（recovery.conf / standby.signal）
```

### 4. 备份恢复测试

**备份不测试恢复，等于没有备份。** 这是 SRE 的铁律。

```bash
#!/bin/bash
# backup_restore_test.sh — 备份恢复验证脚本
set -euo pipefail

TEST_DIR="/tmp/restore_test_$(date +%Y%m%d)"
BACKUP_FILE="$1"

echo "=== 备份恢复测试 ==="
echo "备份文件: $BACKUP_FILE"
echo "恢复目录: $TEST_DIR"

# 1. 验证备份文件完整性
echo "[1/5] 验证校验和..."
if [[ -f "${BACKUP_FILE}.sha256" ]]; then
    if sha256sum -c "${BACKUP_FILE}.sha256"; then
        echo "  ✅ 校验通过"
    else
        echo "  ❌ 校验失败！备份文件可能已损坏"
        exit 1
    fi
else
    echo "  ⚠️  未找到校验文件，跳过校验"
fi

# 2. 验证归档完整性
echo "[2/5] 验证归档完整性..."
if tar tzf "$BACKUP_FILE" > /dev/null 2>&1; then
    echo "  ✅ 归档结构完整"
else
    echo "  ❌ 归档文件损坏！"
    exit 1
fi

# 3. 恢复到测试目录
echo "[3/5] 执行恢复..."
mkdir -p "$TEST_DIR"
tar xzf "$BACKUP_FILE" -C "$TEST_DIR"
echo "  ✅ 恢复完成"

# 4. 验证关键文件
echo "[4/5] 验证关键文件..."
critical_files=(
    "etc/nginx/nginx.conf"
    "etc/ssh/sshd_config"
    "etc/passwd"
)

for f in "${critical_files[@]}"; do
    if [[ -f "$TEST_DIR/$f" ]]; then
        echo "  ✅ $f 存在"
    else
        echo "  ⚠️  $f 不存在（可能不在备份范围内）"
    fi
done

# 5. 验证文件数量
echo "[5/5] 统计恢复文件..."
file_count=$(find "$TEST_DIR" -type f | wc -l)
echo "  恢复文件数: $file_count"

# 清理
rm -rf "$TEST_DIR"
echo "=== 恢复测试完成 ==="
```

---

## 💻 实战练习

### 练习 1：基础备份脚本

编写一个备份脚本，要求：
- 备份 /etc 和 /var/www 目录
- 使用 gzip 压缩
- 生成 SHA256 校验和
- 备份文件名包含日期
- 保留最近 7 天的备份

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d)
BACKUP_FILE="$BACKUP_DIR/backup_${DATE}.tar.gz"

mkdir -p "$BACKUP_DIR"

# 创建备份
tar czf "$BACKUP_FILE" /etc /var/www 2>/dev/null || true

# 生成校验和
sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"

# 清理 7 天前的备份
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "backup_*.sha256" -mtime +7 -delete

echo "备份完成: $BACKUP_FILE ($(du -sh "$BACKUP_FILE" | cut -f1))"
```
</details>

### 练习 2：增量备份 + 远程同步

在练习 1 的基础上，增加：
- 使用 rsync --link-dest 实现增量备份
- 将备份同步到远程服务器
- 使用 flock 防止重复执行

<details>
<summary>参考答案</summary>

```bash
#!/bin/bash
set -euo pipefail

LOCK_FILE="/tmp/incremental_backup.lock"
BACKUP_ROOT="/backup/data"
LATEST_LINK="$BACKUP_ROOT/latest"
DATE_DIR="$BACKUP_ROOT/$(date +%Y%m%d)"
REMOTE_HOST="backup-server"
REMOTE_PATH="/remote-backup"

# 获取锁
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "备份已在运行"; exit 1; }

# 增量备份
rsync -avz --delete \
    --link-dest="$LATEST_LINK" \
    --exclude='*.log' \
    --exclude='.cache' \
    /etc/ "$DATE_DIR/"

# 更新 latest 链接
ln -sfn "$DATE_DIR" "$LATEST_LINK"

# 生成校验清单
find "$DATE_DIR" -type f -exec sha256sum {} \; > "$DATE_DIR/checksums.sha256"

# 远程同步
rsync -avz -e "ssh -i /root/.ssh/backup_key" \
    "$DATE_DIR/" \
    "${REMOTE_HOST}:${REMOTE_PATH}/$(hostname)/$(date +%Y%m%d)/"

# 清理 30 天前的备份
find "$BACKUP_ROOT" -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +

echo "增量备份 + 远程同步完成"
```
</details>

### 练习 3：故障排查挑战

以下备份脚本有 5 个 Bug，找出并修复：

```bash
#!/bin/bash
BACKUP_DIR=/backup
DATE=$(date %Y%m%d)
tar czf $BACKUP_DIR/backup-$DATE.tar.gz /etc /var/www
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

<details>
<summary>答案</summary>

```bash
#!/bin/bash
set -euo pipefail  # Bug 1: 缺少严格模式

BACKUP_DIR="/backup"  # Bug 2: 路径需要引号
mkdir -p "$BACKUP_DIR"  # Bug 3: 需要先创建目录

DATE=$(date +%Y%m%d)  # Bug 4: date 格式缺少 + 号
tar czf "${BACKUP_DIR}/backup-${DATE}.tar.gz" /etc /var/www  # Bug 5: 变量未加引号

# 清理旧备份时也应该清理对应的 .sha256 文件
find "$BACKUP_DIR" -name "backup-*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "backup-*.sha256" -mtime +7 -delete
```
</details>

---

## 💻 SRE 实战项目：企业级自动备份脚本

### 完整实现

```bash
#!/bin/bash
# =================================================================
# auto_backup.sh — 企业级自动备份脚本
# 支持：全量/增量备份、完整性校验、自动清理、远程同步、通知
# 用法: auto_backup.sh [--full|--incremental] [--dry-run]
# =================================================================
set -euo pipefail
IFS=$'\n\t'

# ===== 版本与元数据 =====
VERSION="2.0.0"
SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ===== 配置区 =====
# 可通过环境变量或配置文件覆盖
CONFIG_FILE="${BACKUP_CONFIG:-/etc/backup/backup.conf}"
BACKUP_BASE="${BACKUP_BASE:-/backup}"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_TYPE="${1:---incremental}"

# 备份源目录
BACKUP_PATHS=(
    "/etc"
    "/var/www"
    "/opt/app/config"
    "/home"
)

# 排除模式
EXCLUDE_PATTERNS=(
    "*.tmp"
    "*.cache"
    "*.swp"
    "node_modules"
    "__pycache__"
    ".git"
    "*.log"
    ".DS_Store"
)

# 保留策略
KEEP_DAILY=7
KEEP_WEEKLY=4
KEEP_MONTHLY=12

# 压缩算法（gzip|bzip2|xz|zstd）
COMPRESS_ALG="gzip"

# 远程备份
REMOTE_ENABLED="${REMOTE_ENABLED:-false}"
REMOTE_HOST="${REMOTE_HOST:-backup-server}"
REMOTE_PATH="${REMOTE_PATH:-/backup}"
REMOTE_USER="${REMOTE_USER:-backup}"
REMOTE_PORT="${REMOTE_PORT:-22}"
SSH_KEY="${SSH_KEY:-/root/.ssh/backup_key}"

# 通知
NOTIFY_ENABLED="${NOTIFY_ENABLED:-false}"
NOTIFY_WEBHOOK="${NOTIFY_WEBHOOK:-}"  # Slack/钉钉 Webhook
NOTIFY_EMAIL="${NOTIFY_EMAIL:-}"

# 日志
LOG_DIR="/var/log/backup"
LOG_FILE="${LOG_DIR}/backup_$(date +%Y%m%d).log"
LOCK_FILE="/tmp/auto_backup.lock"

# 数据库
MYSQL_ENABLED="${MYSQL_ENABLED:-false}"
MYSQL_USER="${MYSQL_USER:-root}"
PG_ENABLED="${PG_ENABLED:-false}"
PG_USER="${PG_USER:-postgres}"

# DRY RUN 模式
DRY_RUN=false
[[ "${2:-}" == "--dry-run" ]] && DRY_RUN=true

# ===== 加载配置文件 =====
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        log INFO "加载配置文件: $CONFIG_FILE"
        # shellcheck source=/dev/null
        source "$CONFIG_FILE"
    fi
}

# ===== 初始化 =====
init() {
    mkdir -p "$LOG_DIR" "$BACKUP_BASE"
    load_config
}

# ===== 日志函数 =====
log() {
    local level=$1; shift
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"
    echo "$msg" | tee -a "$LOG_FILE"
}

# ===== 锁机制 =====
acquire_lock() {
    exec 200>"$LOCK_FILE"
    if ! flock -n 200; then
        log ERROR "备份脚本已在运行（PID: $(cat "$LOCK_FILE" 2>/dev/null)），退出"
        send_notify "ERROR" "备份失败：脚本重复运行"
        exit 1
    fi
    echo $$ > "$LOCK_FILE"
    trap cleanup EXIT
}

cleanup() {
    rm -f "$LOCK_FILE"
    log INFO "清理完成，释放锁"
}

# ===== 通知机制 =====
send_notify() {
    local level=$1
    local message=$2
    local hostname
    hostname=$(hostname)

    if [[ "$NOTIFY_ENABLED" != "true" ]]; then
        return
    fi

    # Slack/钉钉 Webhook 通知
    if [[ -n "$NOTIFY_WEBHOOK" ]]; then
        local payload
        payload=$(cat <<EOF
{
    "text": "[$level] 备份通知 - $hostname",
    "blocks": [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*[$level] 备份通知*\n主机: $hostname\n时间: $(date '+%Y-%m-%d %H:%M:%S')\n$message"
            }
        }
    ]
}
EOF
)
        curl -s -X POST -H 'Content-Type: application/json' \
            -d "$payload" "$NOTIFY_WEBHOOK" >/dev/null 2>&1 || true
    fi

    # 邮件通知
    if [[ -n "$NOTIFY_EMAIL" ]] && command -v mail &>/dev/null; then
        echo "$message" | mail -s "[$level] 备份通知 - $hostname" "$NOTIFY_EMAIL"
    fi

    log INFO "通知已发送: [$level] $message"
}

# ===== 压缩工具选择 =====
get_compress_cmd() {
    case "$COMPRESS_ALG" in
        gzip)  echo "tar czf" ;;
        bzip2) echo "tar cjf" ;;
        xz)    echo "tar cJf" ;;
        zstd)  echo "tar --zstd -cf" ;;
        *)
            log WARN "未知压缩算法: $COMPRESS_ALG，使用 gzip"
            echo "tar czf"
            ;;
    esac
}

get_compress_ext() {
    case "$COMPRESS_ALG" in
        gzip)  echo ".tar.gz" ;;
        bzip2) echo ".tar.bz2" ;;
        xz)    echo ".tar.xz" ;;
        zstd)  echo ".tar.zst" ;;
        *)     echo ".tar.gz" ;;
    esac
}

# ===== 构建排除参数 =====
build_exclude_args() {
    local args=""
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        args="$args --exclude='$pattern'"
    done
    echo "$args"
}

# ===== 文件系统备份 =====
backup_filesystem() {
    log INFO "========== 文件系统备份 =========="

    local compress_cmd
    compress_cmd=$(get_compress_cmd)
    local ext
    ext=$(get_compress_ext)
    local exclude_args
    exclude_args=$(build_exclude_args)

    local total=${#BACKUP_PATHS[@]}
    local current=0
    local failed=0

    for path in "${BACKUP_PATHS[@]}"; do
        ((current++))

        if [[ ! -d "$path" && ! -f "$path" ]]; then
            log WARN "[$current/$total] 跳过不存在的路径: $path"
            continue
        fi

        local safe_name
        safe_name=$(echo "$path" | tr '/' '_' | sed 's/^_//')
        local archive="${BACKUP_BASE}/${safe_name}${ext}"

        log INFO "[$current/$total] 备份 $path ..."

        if [[ "$DRY_RUN" == "true" ]]; then
            log INFO "[DRY-RUN] 将执行: $compress_cmd $archive $path"
            continue
        fi

        # shellcheck disable=SC2086
        if eval $compress_cmd "$archive" $exclude_args \
            -C / "$(echo "$path" | sed 's|^/||')" 2>>"$LOG_FILE"; then
            # 生成校验和
            sha256sum "$archive" > "${archive}.sha256"
            local size
            size=$(du -sh "$archive" | cut -f1)
            log INFO "✅ 完成: $archive ($size)"
        else
            log ERROR "❌ 失败: $path"
            ((failed++))
        fi
    done

    return $failed
}

# ===== 数据库备份 =====
backup_databases() {
    log INFO "========== 数据库备份 =========="

    local db_dir="${BACKUP_BASE}/databases"
    mkdir -p "$db_dir"

    [[ "$DRY_RUN" == "true" ]] && return 0

    # MySQL 备份
    if [[ "$MYSQL_ENABLED" == "true" ]] && command -v mysqldump &>/dev/null; then
        log INFO "备份 MySQL..."
        local mysql_file="$db_dir/mysql_all_$(date +%Y%m%d).sql.gz"

        if mysqldump -u "$MYSQL_USER" --all-databases \
            --single-transaction \
            --routines --triggers --events \
            2>>"$LOG_FILE" | gzip > "$mysql_file"; then
            sha256sum "$mysql_file" > "${mysql_file}.sha256"
            log INFO "✅ MySQL 备份完成 ($(du -sh "$mysql_file" | cut -f1))"
        else
            log ERROR "❌ MySQL 备份失败"
            send_notify "ERROR" "MySQL 备份失败，请检查日志: $LOG_FILE"
        fi
    fi

    # PostgreSQL 备份
    if [[ "$PG_ENABLED" == "true" ]] && command -v pg_dump &>/dev/null; then
        log INFO "备份 PostgreSQL..."
        local pg_file="$db_dir/pg_all_$(date +%Y%m%d).dump"

        if pg_dumpall -U "$PG_USER" -Fc > "$pg_file" 2>>"$LOG_FILE"; then
            sha256sum "$pg_file" > "${pg_file}.sha256"
            log INFO "✅ PostgreSQL 备份完成 ($(du -sh "$pg_file" | cut -f1))"
        else
            log ERROR "❌ PostgreSQL 备份失败"
            send_notify "ERROR" "PostgreSQL 备份失败，请检查日志: $LOG_FILE"
        fi
    fi
}

# ===== 生成备份清单 =====
create_manifest() {
    log INFO "生成备份清单..."

    local manifest="${BACKUP_BASE}/MANIFEST.txt"

    cat > "$manifest" << EOF
=====================================
备份清单 (Backup Manifest)
=====================================
版本: ${VERSION}
日期: $(date '+%Y-%m-%d %H:%M:%S')
主机名: $(hostname)
内核: $(uname -r)
备份类型: ${BACKUP_TYPE}
压缩算法: ${COMPRESS_ALG}

备份路径:
$(printf '  - %s\n' "${BACKUP_PATHS[@]}")

排除模式:
$(printf '  - %s\n' "${EXCLUDE_PATTERNS[@]}")

文件列表:
$(find "$BACKUP_BASE" -type f -name "*.tar.*" -exec ls -lh {} \; 2>/dev/null)

校验和:
$(find "$BACKUP_BASE" -name "*.sha256" -exec cat {} \; 2>/dev/null)
=====================================
EOF

    log INFO "✅ 清单已生成: $manifest"
}

# ===== 验证备份完整性 =====
verify_backup() {
    log INFO "========== 验证备份完整性 =========="

    local errors=0
    local total=0

    while IFS= read -r sha_file; do
        [[ -f "$sha_file" ]] || continue
        ((total++))

        if sha256sum -c "$sha_file" &>/dev/null; then
            log INFO "✅ 校验通过: $(basename "$sha_file" .sha256)"
        else
            log ERROR "❌ 校验失败: $(basename "$sha_file" .sha256)"
            ((errors++))
        fi
    done < <(find "$BACKUP_BASE" -name "*.sha256" -type f)

    log INFO "校验结果: $total 个文件, $errors 个失败"
    return $errors
}

# ===== 远程同步 =====
sync_to_remote() {
    if [[ "$REMOTE_ENABLED" != "true" ]]; then
        log INFO "远程同步未启用，跳过"
        return 0
    fi

    log INFO "========== 远程同步 =========="
    log INFO "目标: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"

    [[ "$DRY_RUN" == "true" ]] && return 0

    local rsync_opts=(
        -avz
        --delete
        -e "ssh -p $REMOTE_PORT -i $SSH_KEY -o StrictHostKeyChecking=no"
    )

    if rsync "${rsync_opts[@]}" \
        "$BACKUP_BASE/" \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/$(hostname)/$(date +%Y%m%d)/" \
        >>"$LOG_FILE" 2>&1; then
        log INFO "✅ 远程同步完成"
    else
        log ERROR "❌ 远程同步失败"
        send_notify "ERROR" "远程同步失败: ${REMOTE_HOST}"
        return 1
    fi
}

# ===== 清理旧备份 =====
cleanup_old_backups() {
    log INFO "========== 清理旧备份 =========="

    [[ "$DRY_RUN" == "true" ]] && return 0

    # 统计清理前大小
    local before_size
    before_size=$(du -sh "$BACKUP_BASE" 2>/dev/null | cut -f1)

    # 按日期目录清理（保留最近 N 天）
    local count=0
    while IFS= read -r old_dir; do
        [[ -d "$old_dir" ]] || continue
        log INFO "删除旧备份: $old_dir"
        rm -rf "$old_dir"
        ((count++))
    done < <(find "$BACKUP_BASE" -maxdepth 1 -type d -name "20*" | sort | head -n -$KEEP_DAILY)

    # 清理孤立的校验文件
    find "$BACKUP_BASE" -name "*.sha256" | while IFS= read -r sha_file; do
        local data_file="${sha_file%.sha256}"
        [[ -f "$data_file" ]] || rm -f "$sha_file"
    done

    # 统计清理后大小
    local after_size
    after_size=$(du -sh "$BACKUP_BASE" 2>/dev/null | cut -f1)

    log INFO "清理完成: 删除 $count 个旧备份, $before_size -> $after_size"
}

# ===== 备份报告 =====
generate_report() {
    local start_time=$1
    local end_time
    end_time=$(date +%s)
    local duration=$(( end_time - start_time ))
    local total_size
    total_size=$(du -sh "$BACKUP_BASE" 2>/dev/null | cut -f1)
    local backup_count
    backup_count=$(find "$BACKUP_BASE" -name "*.tar.*" -type f | wc -l)

    cat << EOF

=====================================
备份报告
=====================================
开始时间: $(date -d "@$start_time" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "$start_time" '+%Y-%m-%d %H:%M:%S')
结束时间: $(date '+%Y-%m-%d %H:%M:%S')
耗时: ${duration} 秒
备份文件数: $backup_count
备份总大小: $total_size
备份目录: $BACKUP_BASE
日志文件: $LOG_FILE
=====================================
EOF
}

# ===== 主入口 =====
main() {
    local start_time
    start_time=$(date +%s)

    init

    log INFO "========================================="
    log INFO "自动备份开始 (v${VERSION})"
    log INFO "类型: $BACKUP_TYPE | 压缩: $COMPRESS_ALG"
    log INFO "========================================="

    acquire_lock

    local exit_code=0

    backup_filesystem || exit_code=$?
    backup_databases || true
    create_manifest
    verify_backup || exit_code=$?
    sync_to_remote || exit_code=$?
    cleanup_old_backups

    generate_report "$start_time"

    if [[ $exit_code -eq 0 ]]; then
        log INFO "✅ 备份全部完成"
        send_notify "SUCCESS" "备份完成，总大小: $(du -sh "$BACKUP_BASE" | cut -f1)"
    else
        log ERROR "❌ 备份过程中存在错误（退出码: $exit_code）"
        send_notify "ERROR" "备份过程中存在错误，请检查日志: $LOG_FILE"
    fi

    return $exit_code
}

main "$@"
```

### Cron 定时任务配置

```bash
# /etc/cron.d/backup
# 每天凌晨 2 点执行增量备份
0 2 * * * root /opt/scripts/auto_backup.sh --incremental >> /var/log/backup/cron.log 2>&1

# 每周日凌晨 1 点执行全量备份
0 1 * * 0 root /opt/scripts/auto_backup.sh --full >> /var/log/backup/cron.log 2>&1

# 每月 1 日凌晨 3 点执行恢复测试
0 3 1 * * root /opt/scripts/backup_restore_test.sh >> /var/log/backup/restore_test.log 2>&1
```

### 备份配置文件

```bash
# /etc/backup/backup.conf
# 自动备份配置文件

# 备份源
BACKUP_PATHS=(
    "/etc"
    "/var/www"
    "/opt/app"
)

# 保留策略
KEEP_DAILY=7
KEEP_WEEKLY=4
KEEP_MONTHLY=12

# 压缩算法
COMPRESS_ALG="zstd"

# 远程备份
REMOTE_ENABLED="true"
REMOTE_HOST="backup-server.example.com"
REMOTE_PATH="/backup"
REMOTE_USER="backup"
REMOTE_PORT="22"
SSH_KEY="/root/.ssh/backup_key"

# 通知
NOTIFY_ENABLED="true"
NOTIFY_WEBHOOK="https://hooks.slack.com/services/xxx/yyy/zzz"
NOTIFY_EMAIL="sre@example.com"

# 数据库
MYSQL_ENABLED="true"
MYSQL_USER="backup_user"
PG_ENABLED="false"
```

---

## 🎯 面试题精选

### 1. 全量备份、增量备份、差异备份有什么区别？各自的优缺点？

**参考答案**：

| 对比项 | 全量备份 | 增量备份 | 差异备份 |
|--------|----------|----------|----------|
| 备份内容 | 所有数据 | 上次备份后的变化 | 上次全量后的所有变化 |
| 备份速度 | 最慢 | 最快 | 中等 |
| 恢复速度 | 最快（1份） | 最慢（N份） | 较快（2份） |
| 空间占用 | 最大 | 最小 | 中等 |
| 恢复复杂度 | 简单 | 复杂（按序恢复） | 较简单 |

典型策略：周日全量 + 周一至周六增量/差异。

### 2. 什么是 RPO 和 RTO？如何根据它们设计备份策略？

**参考答案**：

- **RPO (Recovery Point Objective)**：灾难发生时可容忍的最大数据丢失量。RPO=1h 意味着最多丢失 1 小时数据。
- **RTO (Recovery Time Objective)**：灾难发生后系统恢复所需的最长时间。RTO<1h 意味着 1 小时内必须恢复服务。

设计策略：
- RPO=0 + RTO<15min：数据库主从同步 + 自动 failover
- RPO<1h + RTO<1h：每小时增量备份 + 快照恢复
- RPO<24h + RTO<24h：每日全量备份即可

### 3. 如何防止备份脚本重复执行？

**参考答案**：

使用 `flock` 文件锁机制：
```bash
exec 200>/tmp/backup.lock
flock -n 200 || exit 1
```

或者使用 PID 文件检查进程是否存在。flock 更可靠，因为它由内核管理，即使进程异常退出也会自动释放。

### 4. 备份文件如何验证完整性？

**参考答案**：

1. 生成校验和：`sha256sum backup.tar.gz > backup.tar.gz.sha256`
2. 验证校验和：`sha256sum -c backup.tar.gz.sha256`
3. 定期执行恢复测试：将备份恢复到测试环境，验证数据可用性
4. 自动化验证：cron 定期校验 + 告警

### 5. rsync --link-dest 的原理是什么？为什么能实现高效增量备份？

**参考答案**：

`--link-dest` 指定一个参考目录，rsync 会将未变化的文件通过硬链接指向参考目录中的文件，而不是复制一份新的。由于硬链接共享同一份数据块，不占用额外磁盘空间。

```
/backup/20260420/file1 (实际数据, 100MB)
/backup/20260421/file1 (硬链接, 0 额外空间)
```

### 6. mysqldump --single-transaction 的作用是什么？

**参考答案**：

`--single-transaction` 使 mysqldump 在开始备份前执行 `START TRANSACTION WITH CONSISTENT SNAPSHOT`，获取 InnoDB 的一致性快照。这样备份过程中不需要锁表，不会阻塞业务的读写操作。但它只对 InnoDB 引擎有效，MyISAM 表仍会锁表。

### 7. 如何设计一个 3-2-1 备份策略？

**参考答案**：

以文件服务器为例：
- 3 份副本：生产数据 + 本地 NAS 备份 + 云端 S3 备份
- 2 种介质：本地磁盘（NAS）+ 云对象存储（S3）
- 1 份异地：S3 跨区域复制到另一个 Region

实现：
1. 每日凌晨 2 点 rsync 到本地 NAS
2. 备份完成后同步到 S3（使用 aws s3 sync）
3. S3 配置跨区域复制（CRR）到另一个 Region
4. 每月验证恢复流程

### 8. gzip、bzip2、xz、zstd 应该怎么选择？

**参考答案**：

- **日常备份**：gzip（速度快、兼容性好）或 zstd（更好的压缩比和速度）
- **长期归档**：xz（最高压缩比）或 zstd
- **实时压缩**：lz4（最快）或 zstd
- **跨平台**：gzip（几乎所有系统都支持）

zstd 是现代最佳选择，它在压缩率和速度之间取得了最佳平衡，且支持多线程压缩。

### 9. 备份脚本中如何处理敏感数据（如数据库密码）？

**参考答案**：

1. 不要在脚本中硬编码密码
2. 使用 MySQL 的 `--defaults-file` 或 `~/.my.cnf`（权限 600）
3. 使用 PostgreSQL 的 `.pgpass` 文件
4. 使用环境变量 + secret manager（如 HashiCorp Vault）
5. 备份文件加密：`gpg --encrypt` 或 `openssl enc`

### 10. 如何监控备份任务的健康状态？

**参考答案**：

1. **脚本层面**：检查退出码、校验和验证、日志分析
2. **定时监控**：检查备份文件是否存在且大小合理
3. **告警机制**：备份失败时通过 Webhook/邮件/短信通知
4. **定期恢复测试**：每月自动恢复测试 + 人工验证
5. **监控指标**：备份大小趋势、备份耗时趋势、存储使用率

---

## 📚 深入阅读

- [3-2-1 Backup Strategy - Backblaze](https://www.backblaze.com/blog/the-3-2-1-backup-strategy/)
- [rsync Official Documentation](https://rsync.samba.org/documentation.html)
- [Percona XtraBackup Documentation](https://www.percona.com/doc/percona-xtrabackup/8.0/)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Borg Backup - Deduplicating Backup Tool](https://www.borgbackup.org/)
- [Restic - Fast, Secure, Efficient Backup](https://restic.net/)
- [Google SRE Book - Data Processing Pipelines](https://sre.google/sre-book/data-processing/)
- `man tar`、`man rsync`、`man flock`

---

## ✅ 自检清单

- [ ] 理解 3-2-1 备份原则，能说出每个数字的含义
- [ ] 理解 RPO 和 RTO 的区别，能根据业务场景设计备份策略
- [ ] 掌握 tar 全量备份和 --listed-incremental 增量备份
- [ ] 掌握 rsync --link-dest 硬链接增量备份原理
- [ ] 能使用 flock 防止脚本重复执行
- [ ] 掌握 MD5/SHA256 校验和的生成和验证
- [ ] 了解 gzip/bzip2/xz/zstd 的压缩率和速度差异
- [ ] 掌握 mysqldump --single-transaction 的原理
- [ ] 了解 xtrabackup 物理备份的优势
- [ ] 理解"备份不测试恢复等于没有备份"的理念
- [ ] 能编写包含通知机制的完整备份脚本
- [ ] 能配置 cron 定时备份任务

---

*由 SRE 学习计划生成 | 2026-04-26*
