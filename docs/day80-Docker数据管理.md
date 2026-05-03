# Day 80: Docker 数据管理

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 数据管理 — Volume、bind mount、tmpfs、数据卷生命周期、备份恢复、存储驱动 overlay2
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 76 (Docker 简介与安装), Day 77 (Docker 镜像基础), Day 79 (Docker 容器管理)

---

## 🎯 学习目标

完成 Day 80 的学习后，你应该能够：
- 深入理解 Docker 三种数据持久化方式的原理和适用场景
- 掌握 Docker Volume 的完整生命周期管理
- 理解 bind mount 和 tmpfs 的使用场景和注意事项
- 能够设计和实现容器数据的备份与恢复方案
- 理解 overlay2 存储驱动的工作原理
- 能够解决生产环境中的数据持久化问题

---

## 📖 核心知识点

### 1. 为什么需要数据持久化

#### 1.1 容器数据的临时性

```
容器数据的本质问题：

  容器 = 可写层 + 镜像只读层

  ┌─────────────────────────────────────────────────────────────┐
  │                    容器文件系统                               │
  │                                                             │
  │  ┌─────────────────────────────────────────────────────┐   │
  │  │           Container Layer (可写层)                   │   │
  │  │           - 运行时产生的所有数据                      │   │
  │  │           - 数据库写入的数据                          │   │
  │  │           - 应用生成的日志文件                        │   │
  │  │           - 用户上传的文件                            │   │
  │  │                                                      │   │
  │  │  问题：容器删除后，可写层也被删除！                  │   │
  │  │        所有数据永久丢失！                             │   │
  │  └─────────────────────────────────────────────────────┘   │
  │  ┌─────────────────────────────────────────────────────┐   │
  │  │           Image Layers (只读层)                      │   │
  │  │           - 镜像中的文件                              │   │
  │  │           - 不可修改                                  │   │
  │  └─────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────┘

  解决方案：将数据存储在容器外部
  - Docker Volume（推荐）
  - Bind Mount
  - tmpfs
```

#### 1.2 三种数据持久化方式概览

```
Docker 三种数据持久化方式：

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  1. Docker Volume（数据卷）                                         │
│     ┌───────────────────────────────────────────────────────────┐  │
│     │  Docker 管理的存储区域                                      │  │
│     │  位置：/var/lib/docker/volumes/<volume_name>/_data/        │  │
│     │  特点：Docker 完全管理，可移植性好                          │  │
│     │  适用：数据库数据、应用状态、需要持久化的数据               │  │
│     └───────────────────────────────────────────────────────────┘  │
│                                                                     │
│  2. Bind Mount（绑定挂载）                                          │
│     ┌───────────────────────────────────────────────────────────┐  │
│     │  将宿主机的目录/文件挂载到容器中                            │  │
│     │  位置：宿主机上的任意路径                                   │  │
│     │  特点：直接访问宿主机文件系统，开发时常用                   │  │
│     │  适用：开发环境代码挂载、配置文件挂载、日志收集             │  │
│     └───────────────────────────────────────────────────────────┘  │
│                                                                     │
│  3. tmpfs Mount（临时文件系统）                                     │
│     ┌───────────────────────────────────────────────────────────┐  │
│     │  存储在宿主机内存中                                        │  │
│     │  位置：内存                                                │  │
│     │  特点：高性能，容器停止后数据丢失                          │  │
│     │  适用：临时数据、敏感信息（密钥、token）、高速缓存         │  │
│     └───────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

| 特性 | Docker Volume | Bind Mount | tmpfs |
|------|---------------|------------|-------|
| 存储位置 | Docker 管理的目录 | 宿主机任意路径 | 内存 |
| 持久化 | 是（容器删除后保留） | 是 | 否（容器停止后丢失） |
| Docker 管理 | 是 | 否 | 否 |
| 可移植性 | 高 | 低（依赖宿主机路径） | - |
| 性能 | 高 | 高（取决于磁盘） | 最高 |
| 多容器共享 | 支持 | 支持 | 不支持 |
| 备份 | docker volume 命令 | 宿主机工具 | 不需要 |
| 适用场景 | 数据库、应用数据 | 开发环境、配置文件 | 临时数据、密钥 |

### 2. Docker Volume 详解

#### 2.1 Volume 的创建与管理

```bash
# 创建数据卷
docker volume create mydata

# 创建带标签的数据卷
docker volume create --label env=production --label app=mysql mydata

# 创建带驱动选项的数据卷
docker volume create --driver local \
    --opt type=none \
    --opt device=/data/mysql \
    --opt o=bind \
    mysql_data

# 列出所有数据卷
docker volume ls

# 过滤数据卷
docker volume ls --filter "dangling=true"  # 未使用的数据卷
docker volume ls --filter "label=env=production"

# 查看数据卷详情
docker volume inspect mydata
# [
#     {
#         "CreatedAt": "2024-01-01T00:00:00Z",
#         "Driver": "local",
#         "Labels": {},
#         "Mountpoint": "/var/lib/docker/volumes/mydata/_data",
#         "Name": "mydata",
#         "Options": {},
#         "Scope": "local"
#     }
# ]

# 删除数据卷
docker volume rm mydata

# 删除所有未使用的数据卷（慎用！）
docker volume prune

# 带过滤条件删除
docker volume prune --filter "label=env=test"
```

#### 2.2 使用 Volume 运行容器

```bash
# 基本用法：命名数据卷
docker run -d --name mysql \
    -v mysql_data:/var/lib/mysql \
    -e MYSQL_ROOT_PASSWORD=secret \
    mysql:8.0

# 使用 --mount 语法（更明确，推荐）
docker run -d --name mysql \
    --mount source=mysql_data,target=/var/lib/mysql \
    -e MYSQL_ROOT_PASSWORD=secret \
    mysql:8.0

# 只读挂载
docker run -d --name app \
    -v config_data:/app/config:ro \
    myapp:v1

# 使用 --mount 的只读选项
docker run -d --name app \
    --mount source=config_data,target=/app/config,readonly \
    myapp:v1

# 匿名数据卷（自动生成随机名称）
docker run -d --name mysql \
    -v /var/lib/mysql \
    mysql:8.0
# 会创建一个随机名称的数据卷

# 挂载多个数据卷
docker run -d --name mysql \
    -v mysql_data:/var/lib/mysql \
    -v mysql_config:/etc/mysql \
    -v mysql_logs:/var/log/mysql \
    mysql:8.0
```

```
-v vs --mount 语法对比：

  -v (--volume):
    docker run -v mysql_data:/var/lib/mysql:ro myapp
    格式：name:destination:options
    优点：简洁
    缺点：语法不够清晰，容易混淆

  --mount:
    docker run --mount source=mysql_data,target=/var/lib/mysql,readonly myapp
    格式：key=value 逗号分隔
    优点：语义清晰，不易出错
    缺点：较长

  推荐：生产环境使用 --mount，开发环境可用 -v
```

#### 2.3 Volume 的存储原理

```
Docker Volume 的底层存储：

  /var/lib/docker/volumes/
  ├── mysql_data/                    ← 命名数据卷
  │   ├── _data/                     ← 实际数据目录
  │   │   ├── ibdata1
  │   │   ├── ib_logfile0
  │   │   ├── mysql/
  │   │   └── ...
  │   └── _metadata/                 ← 元数据（如果使用）
  │
  ├── a1b2c3d4e5f6.../               ← 匿名数据卷（随机 ID）
  │   └── _data/
  │
  └── ...

  Volume 的创建过程：
  1. docker volume create mydata
  2. Docker 在 /var/lib/docker/volumes/ 下创建 mydata 目录
  3. 在 mydata 下创建 _data 目录
  4. 记录数据卷元数据到本地数据库

  容器挂载 Volume 的过程：
  1. docker run -v mydata:/app/data myimage
  2. Docker 查找 mydata 数据卷
  3. 使用 bind mount 将 _data 目录挂载到容器的 /app/data
  4. 容器读写 /app/data 实际操作的是 _data 目录
```

#### 2.4 Volume 驱动

```bash
# 查看可用的 volume 驱动
docker plugin ls

# 使用本地 NFS 驱动
docker volume create --driver local \
    --opt type=nfs \
    --opt o=addr=10.0.1.100,rw,nfsvers=4 \
    --opt device=:/exports/data \
    nfs_data

# 使用 CIFS/SMB 驱动
docker volume create --driver local \
    --opt type=cifs \
    --opt device=//10.0.1.100/share \
    --opt o=username=user,password=pass \
    cifs_data

# 使用 tmpfs 驱动（创建基于内存的 volume）
docker volume create --driver local \
    --opt type=tmpfs \
    --opt device=tmpfs \
    --opt o=size=100m,uid=1000 \
    tmpfs_vol

# 常见的第三方 volume 驱动：
# - Rex-Ray: 支持 AWS EBS、GCE PD、Azure Disk 等
# - Portworx: 分布式存储
# - Convoy: 支持多种后端存储
# - Azure File Storage: Azure 文件共享
# - Netapp: NetApp 存储
```

### 3. Bind Mount 详解

#### 3.1 Bind Mount 的使用

```bash
# 基本用法：挂载宿主机目录
docker run -d --name nginx \
    -v /home/user/html:/usr/share/nginx/html \
    nginx:latest

# 使用 --mount 语法（推荐）
docker run -d --name nginx \
    --mount type=bind,source=/home/user/html,target=/usr/share/nginx/html \
    nginx:latest

# 只读挂载
docker run -d --name nginx \
    -v /home/user/nginx.conf:/etc/nginx/nginx.conf:ro \
    nginx:latest

# 挂载单个文件
docker run -d --name nginx \
    --mount type=bind,source=/home/user/nginx.conf,target=/etc/nginx/nginx.conf,readonly \
    nginx:latest

# SELinux 环境下的挂载
docker run -d --name nginx \
    -v /home/user/html:/usr/share/nginx/html:Z \
    nginx:latest
# :Z 自动设置正确的 SELinux 标签

# 多个 bind mount
docker run -d --name myapp \
    -v /home/user/app:/app \
    -v /home/user/config:/app/config:ro \
    -v /var/log/myapp:/app/logs \
    myapp:v1
```

```
Bind Mount 的注意事项：

1. 宿主机路径必须是绝对路径
   ❌ docker run -v ./data:/app/data myimage
   ✅ docker run -v /home/user/data:/app/data myimage

2. 如果宿主机目录不存在，Docker 会自动创建
   - 创建的目录归 root 所有
   - 可能导致权限问题

3. 容器内的权限由宿主机上的文件权限决定
   - 如果容器以 root 运行，可以读写所有文件
   - 如果容器以非 root 运行，需要确保文件权限正确

4. Bind mount 不受 docker volume 生命周期管理
   - 删除容器不会删除宿主机上的目录
   - 但删除宿主机上的目录会导致容器读取失败

5. 性能取决于宿主机的文件系统
   - Linux 本地文件系统：性能最好
   - NFS：性能取决于网络
   - macOS/Windows（Docker Desktop）：有性能损耗
```

#### 3.2 Bind Mount 的典型场景

```bash
# 场景 1：开发环境代码热重载
docker run -d --name dev-app \
    -v $(pwd)/src:/app/src \
    -v $(pwd)/package.json:/app/package.json \
    -p 3000:3000 \
    node:18-alpine \
    npm run dev

# 场景 2：挂载配置文件
docker run -d --name nginx \
    -v /etc/nginx/nginx.conf:/etc/nginx/nginx.conf:ro \
    -v /etc/nginx/conf.d:/etc/nginx/conf.d:ro \
    -v /var/www/html:/usr/share/nginx/html \
    -p 80:80 \
    nginx:latest

# 场景 3：日志收集
docker run -d --name app \
    -v /var/log/myapp:/app/logs \
    myapp:v1
# Filebeat/Promtail 可以从 /var/log/myapp 收集日志

# 场景 4：Docker Socket 挂载（Docker-in-Docker）
docker run -d --name portainer \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v portainer_data:/data \
    portainer/portainer

# 场景 5：挂载宿主机的 SSL 证书
docker run -d --name nginx \
    -v /etc/letsencrypt/live/example.com:/etc/ssl/certs:ro \
    nginx:latest
```

### 4. tmpfs Mount 详解

#### 4.1 tmpfs 的使用

```bash
# 基本用法
docker run -d --name app \
    --tmpfs /tmp \
    myapp:v1

# 使用 --mount 语法
docker run -d --name app \
    --mount type=tmpfs,target=/tmp \
    myapp:v1

# 设置大小限制
docker run -d --name app \
    --tmpfs /tmp:rw,size=100m \
    myapp:v1

# 使用 --mount 设置更多选项
docker run -d --name app \
    --mount type=tmpfs,target=/tmp,tmpfs-size=100m,tmpfs-mode=1777 \
    myapp:v1

# 多个 tmpfs 挂载
docker run -d --name app \
    --tmpfs /tmp:rw,size=100m \
    --tmpfs /run:rw,size=50m \
    myapp:v1
```

```
tmpfs 的使用场景：

1. 敏感信息临时存储
   docker run --tmpfs /run/secrets:ro,size=1m myapp
   - API key、token 等敏感信息只存在于内存中
   - 容器停止后数据自动清除
   - 不会写入磁盘，不会进入镜像层

2. 高速缓存
   docker run --tmpfs /app/cache:rw,size=500m myapp
   - 内存读写速度远快于磁盘
   - 适合不需要持久化的缓存数据

3. 临时文件
   docker run --tmpfs /tmp:rw,size=100m myapp
   - 应用运行时产生的临时文件
   - 容器重启后自动清理

4. 只读文件系统配合 tmpfs
   docker run --read-only --tmpfs /tmp:rw,size=100m --tmpfs /run:rw,size=50m myapp
   - 增强安全性
   - 只有 /tmp 和 /run 可写
```

### 5. 数据卷生命周期管理

#### 5.1 容器与 Volume 的关系

```
Volume 的生命周期独立于容器：

  时间线：
  ─────────────────────────────────────────────────────────────▶

  docker volume create mydata    (创建数据卷)
       │
       │  docker run -v mydata:/data myapp:v1
       │  (容器 A 使用 mydata)
       ▼
  ┌─────────────────────┐
  │  Container A        │
  │  读写 mydata        │───▶ mydata 中有数据
  └─────────────────────┘
       │
       │  docker rm container_a
       │  (容器 A 被删除)
       ▼
  mydata 数据卷仍然存在，数据不丢失
       │
       │  docker run -v mydata:/data myapp:v2
       │  (容器 B 使用 mydata)
       ▼
  ┌─────────────────────┐
  │  Container B        │
  │  读写 mydata        │───▶ mydata 中的数据对容器 B 可见
  └─────────────────────┘
       │
       │  docker volume rm mydata
       │  (数据卷被删除，数据永久丢失)
       ▼
  数据卷被删除

  关键点：
  - Volume 的生命周期独立于容器
  - 删除容器不会删除 Volume
  - 删除 Volume 会永久丢失数据
  - 多个容器可以同时使用同一个 Volume（需要注意并发访问）
```

#### 5.2 Volume 的共享

```bash
# 场景：多个容器共享同一个数据卷

# 创建共享数据卷
docker volume create shared_data

# 容器 A：写入数据
docker run -d --name writer \
    -v shared_data:/data \
    alpine \
    sh -c 'while true; do echo "$(date)" >> /data/log.txt; sleep 5; done'

# 容器 B：读取数据
docker run -d --name reader \
    -v shared_data:/data:ro \
    alpine \
    sh -c 'while true; do cat /data/log.txt 2>/dev/null | tail -5; sleep 5; done'

# 查看数据
docker logs reader

# 清理
docker rm -f writer reader
docker volume rm shared_data
```

```
Volume 共享的注意事项：

1. 写冲突
   - 多个容器同时写入同一个文件可能导致数据损坏
   - 使用文件锁或协调机制

2. 读一致性
   - 一个容器写入的数据可能不是立即对另一个容器可见
   - 取决于文件系统缓存

3. 推荐模式
   - 一个容器写，多个容器读
   - 使用消息队列代替文件共享
   - 每个容器使用独立的 Volume

4. 跨主机共享
   - 使用 NFS、CIFS 等网络存储
   - 使用分布式 Volume 驱动（Portworx、GlusterFS）
```

#### 5.3 孤立数据卷（Dangling Volumes）

```bash
# 查看孤立数据卷（未被任何容器使用的数据卷）
docker volume ls --filter "dangling=true"

# 删除孤立数据卷
docker volume prune

# 带确认的删除
docker volume prune --force

# 带过滤条件的删除
docker volume prune --filter "label!=keep"
```

```
孤立数据卷的产生原因：

1. 匿名数据卷
   docker run -v /data myapp  # 创建匿名数据卷
   docker rm myapp             # 删除容器后，匿名数据卷变成孤立的

2. 容器重建
   docker-compose down         # 删除容器
   docker-compose up           # 创建新容器（但旧的匿名卷可能残留）

3. 手动删除容器但未删除数据卷
   docker rm myapp
   # myapp 使用的数据卷仍然存在

预防措施：
  - 始终使用命名数据卷（而非匿名数据卷）
  - 使用 docker-compose 管理生命周期
  - 定期运行 docker volume prune
  - 给重要数据卷打标签，避免误删
```

### 6. 数据备份与恢复

#### 6.1 Volume 备份

```bash
# 方法 1：使用临时容器备份数据卷
docker run --rm \
    -v mydata:/source:ro \
    -v $(pwd):/backup \
    alpine \
    tar czf /backup/mydata-$(date +%Y%m%d%H%M%S).tar.gz -C /source .

# 方法 2：使用 docker cp 备份（需要运行中的容器）
docker cp myapp:/var/lib/mysql ./mysql-backup

# 方法 3：使用数据库原生工具备份
docker exec mysql mysqldump -u root -p'password' --all-databases > backup.sql

# 方法 4：备份数据卷到另一个数据卷
docker volume create mydata_backup
docker run --rm \
    -v mydata:/source:ro \
    -v mydata_backup:/dest \
    alpine \
    sh -c 'rm -rf /dest/* && cp -a /source/. /dest/'
```

```bash
# 完整的备份脚本
#!/bin/bash
# backup-volumes.sh - Docker 数据卷备份脚本

set -e

BACKUP_DIR="/backup/docker-volumes"
DATE=$(date +%Y%m%d%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "=== Docker Volume 备份 ==="
echo "备份目录: $BACKUP_DIR"
echo "备份时间: $DATE"

# 获取所有命名数据卷
VOLUMES=$(docker volume ls --format '{{.Name}}')

for VOL in $VOLUMES; do
    # 跳过匿名数据卷
    if [[ ${#VOL} -eq 64 ]]; then
        echo "跳过匿名数据卷: $VOL"
        continue
    fi

    echo "备份数据卷: $VOL"
    BACKUP_FILE="${BACKUP_DIR}/${VOL}-${DATE}.tar.gz"

    docker run --rm \
        -v "${VOL}:/source:ro" \
        -v "${BACKUP_DIR}:/backup" \
        alpine \
        tar czf "/backup/${VOL}-${DATE}.tar.gz" -C /source .

    echo "  备份文件: $BACKUP_FILE"
    echo "  文件大小: $(ls -lh "$BACKUP_FILE" | awk '{print $5}')"
done

# 清理旧备份
echo ""
echo "清理 ${RETENTION_DAYS} 天前的备份..."
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete

echo ""
echo "=== 备份完成 ==="
ls -lh "$BACKUP_DIR"
```

#### 6.2 Volume 恢复

```bash
# 恢复数据卷
docker volume create mydata_restored
docker run --rm \
    -v mydata_restored:/dest \
    -v $(pwd):/backup:ro \
    alpine \
    tar xzf /backup/mydata-20240101000000.tar.gz -C /dest

# 验证恢复
docker run --rm -v mydata_restored:/data alpine ls -la /data

# 恢复 MySQL 数据库
# 方法 1：从 SQL 备份恢复
docker exec -i mysql mysql -u root -p'password' < backup.sql

# 方法 2：从数据卷备份恢复
docker stop mysql
docker run --rm \
    -v mysql_data:/var/lib/mysql \
    -v $(pwd):/backup:ro \
    alpine \
    sh -c 'rm -rf /var/lib/mysql/* && tar xzf /backup/mysql_data-backup.tar.gz -C /var/lib/mysql'
docker start mysql
```

```bash
# 完整的恢复脚本
#!/bin/bash
# restore-volume.sh - Docker 数据卷恢复脚本

set -e

if [ $# -lt 2 ]; then
    echo "用法: $0 <backup_file> <volume_name>"
    echo "示例: $0 /backup/docker-volumes/mydata-20240101000000.tar.gz mydata"
    exit 1
fi

BACKUP_FILE="$1"
VOLUME_NAME="$2"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "=== Docker Volume 恢复 ==="
echo "备份文件: $BACKUP_FILE"
echo "目标数据卷: $VOLUME_NAME"

# 检查数据卷是否已存在
if docker volume inspect "$VOLUME_NAME" > /dev/null 2>&1; then
    echo "警告: 数据卷 $VOLUME_NAME 已存在"
    read -p "是否覆盖？(y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "操作取消"
        exit 0
    fi
else
    echo "创建数据卷: $VOLUME_NAME"
    docker volume create "$VOLUME_NAME"
fi

echo "恢复数据..."
docker run --rm \
    -v "${VOLUME_NAME}:/dest" \
    -v "$(dirname ${BACKUP_FILE}):/backup:ro" \
    alpine \
    tar xzf "/backup/$(basename ${BACKUP_FILE})" -C /dest

echo ""
echo "恢复完成！"
echo "数据卷内容："
docker run --rm -v "${VOLUME_NAME}:/data" alpine ls -la /data
```

#### 6.3 自动化备份方案

```yaml
# docker-compose.yml - 带自动备份的 MySQL
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: myapp
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backup:
    image: alpine:3.18
    volumes:
      - mysql_data:/source:ro
      - /backup/mysql:/backup
    entrypoint: /bin/sh
    command:
      - -c
      - |
        while true; do
          echo "Starting backup at $$(date)"
          tar czf /backup/mysql-$$(date +%Y%m%d%H%M%S).tar.gz -C /source .
          echo "Backup completed"
          # 保留最近 7 天的备份
          find /backup -name "mysql-*.tar.gz" -mtime +7 -delete
          sleep 86400
        done
    restart: unless-stopped

volumes:
  mysql_data:
```

### 7. overlay2 存储驱动深入

#### 7.1 overlay2 的目录结构

```bash
# 查看 Docker 的存储根目录
docker info --format '{{.DockerRootDir}}'
# 通常是 /var/lib/docker

# 查看 overlay2 目录结构
sudo ls -la /var/lib/docker/overlay2/
```

```
overlay2 目录结构详解：

/var/lib/docker/overlay2/
├── l/                              ← 符号链接目录（短名称）
│   ├── ABC123DEF456 -> ../long_sha256_hash/diff
│   ├── GHI789JKL012 -> ../another_sha256_hash/diff
│   └── ...
│
├── <sha256_hash_1>/                ← 镜像层或容器层
│   ├── diff/                       ← 该层的实际文件内容
│   │   ├── bin/
│   │   ├── etc/
│   │   └── ...
│   ├── link                        ← 短名称（对应 l/ 中的符号链接）
│   ├── lower                       ← 指向下层的指针（只有非底层才有）
│   ├── merged/                     ← 合并后的视图（只有容器才有）
│   ├── work/                       ← OverlayFS 工作目录
│   └── committed                   ← 标记该层已提交
│
├── <sha256_hash_2>/
│   ├── diff/
│   ├── link
│   └── lower -> sha256_hash_1     ← 指向上一层
│
└── ...
```

#### 7.2 overlay2 的挂载过程

```bash
# 查看容器的 overlay2 挂载信息
docker inspect myapp | jq '.[0].GraphDriver'
# {
#   "Data": {
#     "LowerDir": "/var/lib/docker/overlay2/xxx/diff:/var/lib/docker/overlay2/yyy/diff",
#     "MergedDir": "/var/lib/docker/overlay2/zzz/merged",
#     "UpperDir": "/var/lib/docker/overlay2/zzz/diff",
#     "WorkDir": "/var/lib/docker/overlay2/zzz/work"
#   },
#   "Name": "overlay2"
# }

# 查看实际的 mount 信息
mount | grep overlay
# overlay on /var/lib/docker/overlay2/zzz/merged type overlay
# (rw,relatime,lowerdir=...,upperdir=...,workdir=...)
```

```
overlay2 挂载过程：

  docker run -d --name myapp nginx:latest

  1. Docker 查找 nginx:latest 的所有层
     Layer 1 (sha256:aaa...) -> /var/lib/docker/overlay2/aaa/diff
     Layer 2 (sha256:bbb...) -> /var/lib/docker/overlay2/bbb/diff
     Layer 3 (sha256:ccc...) -> /var/lib/docker/overlay2/ccc/diff

  2. 创建容器的可写层
     mkdir /var/lib/docker/overlay2/zzz/diff    (upperdir)
     mkdir /var/lib/docker/overlay2/zzz/work    (workdir)
     mkdir /var/lib/docker/overlay2/zzz/merged  (merged)

  3. 挂载 OverlayFS
     mount -t overlay overlay \
       -o lowerdir=/var/lib/docker/overlay2/ccc/diff:/var/lib/docker/overlay2/bbb/diff:/var/lib/docker/overlay2/aaa/diff,upperdir=/var/lib/docker/overlay2/zzz/diff,workdir=/var/lib/docker/overlay2/zzz/work \
       /var/lib/docker/overlay2/zzz/merged

  4. 容器进程看到的文件系统就是 merged 目录

  文件操作行为：
  ┌────────────────┬──────────────────────────────────────────────┐
  │ 操作           │ 行为                                         │
  ├────────────────┼──────────────────────────────────────────────┤
  │ 读取已有文件   │ 从 lowerdir 读取（直接读，零拷贝）           │
  │ 修改已有文件   │ CoW: 从 lowerdir 复制到 upperdir，再修改     │
  │ 创建新文件     │ 直接在 upperdir 创建                         │
  │ 删除文件       │ 在 upperdir 创建 whiteout 文件标记删除       │
  │ 创建目录       │ 直接在 upperdir 创建                         │
  │ 删除目录       │ 在 upperdir 创建 opaque 目录标记删除        │
  └────────────────┴──────────────────────────────────────────────┘
```

#### 7.3 存储驱动性能优化

```bash
# 1. 使用 SSD 存储 Docker 数据目录
# /etc/docker/daemon.json
{
  "data-root": "/ssd/docker"
}

# 2. 监控 Docker 数据目录的磁盘使用
df -h /var/lib/docker
du -sh /var/lib/docker/*
du -sh /var/lib/docker/overlay2/* | sort -rh | head -20

# 3. 定期清理未使用的资源
docker system prune -a --volumes

# 4. 使用较小的基础镜像减少层大小
# alpine (~7MB) vs ubuntu (~77MB)

# 5. 合理设计 Dockerfile 层
# 将不常变化的指令放在前面
# 合并相关的 RUN 指令
```

### 8. 生产环境数据管理最佳实践

#### 8.1 数据库容器数据管理

```yaml
# docker-compose.yml - 生产级 MySQL 部署
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: mysql
    environment:
      MYSQL_ROOT_PASSWORD_FILE: /run/secrets/mysql_root_password
      MYSQL_DATABASE: myapp
      MYSQL_USER: appuser
      MYSQL_PASSWORD_FILE: /run/secrets/mysql_password
    volumes:
      # 使用命名数据卷持久化数据库数据
      - mysql_data:/var/lib/mysql
      # 挂载自定义配置
      - ./mysql/conf.d:/etc/mysql/conf.d:ro
      # 挂载初始化脚本
      - ./mysql/initdb.d:/docker-entrypoint-initdb.d:ro
      # 挂载备份目录（用于恢复）
      - /backup/mysql:/backup:ro
    ports:
      - "3306:3306"
    secrets:
      - mysql_root_password
      - mysql_password
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p$$(cat /run/secrets/mysql_root_password)"]
      interval: 10s
      timeout: 5s
      start-period: 30s
      retries: 5
    restart: unless-stopped
    # 资源限制
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

secrets:
  mysql_root_password:
    file: ./secrets/mysql_root_password.txt
  mysql_password:
    file: ./secrets/mysql_password.txt

volumes:
  mysql_data:
    driver: local
    labels:
      com.example.description: "MySQL data volume"
      com.example.backup: "daily"
```

#### 8.2 应用日志数据管理

```yaml
# docker-compose.yml - 带日志管理的应用
version: '3.8'

services:
  app:
    image: myapp:v1
    volumes:
      # 应用日志目录
      - app_logs:/app/logs
      # 临时文件目录
      - tmp_data:/tmp
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"
    restart: unless-stopped

  # 日志收集器
  filebeat:
    image: elastic/filebeat:8.11.0
    volumes:
      - app_logs:/var/log/app:ro
      - filebeat_data:/usr/share/filebeat/data
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
    user: root
    restart: unless-stopped

volumes:
  app_logs:
  tmp_data:
  filebeat_data:
```

#### 8.3 数据安全与加密

```bash
# 1. 使用加密的 volume 驱动
# 使用 LUKS 加密的本地 volume
docker volume create --driver local \
    --opt type=luks \
    --opt device=/dev/sdb1 \
    --opt o=key-file=/etc/luks/key \
    encrypted_vol

# 2. 使用 tmpfs 存储敏感数据
docker run --tmpfs /run/secrets:ro,size=1m myapp

# 3. 使用 Docker secrets（Swarm mode）
echo "my_secret_password" | docker secret create db_password -

# 4. 使用 Kubernetes secrets（K8s 环境）
# 参考 K8s 文档

# 5. 文件系统级别的加密
# 使用 eCryptfs、dm-crypt 等
```

### 9. SRE 实战：数据管理故障排查

#### 9.1 磁盘空间不足

```bash
# 排查 Docker 磁盘使用
docker system df
docker system df -v

# 查看各数据卷大小
for vol in $(docker volume ls -q); do
    size=$(docker run --rm -v ${vol}:/data alpine du -sh /data 2>/dev/null | awk '{print $1}')
    echo "$vol: $size"
done

# 查看容器层大小
docker ps -s --format "table {{.Names}}\t{{.Size}}"

# 清理策略
docker volume prune           # 清理未使用的 volume
docker system prune -a        # 清理所有未使用的资源
docker system prune -a --volumes  # 包括 volume（慎用！）

# 迁移 Docker 数据目录到更大的磁盘
sudo systemctl stop docker
sudo rsync -aP /var/lib/docker/ /new-path/docker/
# 修改 /etc/docker/daemon.json 的 data-root
sudo systemctl start docker
```

#### 9.2 数据卷权限问题

```bash
# 问题：容器以非 root 用户运行，但数据卷是 root 创建的
# 症状：Permission denied

# 解决方案 1：修改数据卷权限
docker run --rm -v mydata:/data alpine chown -R 1000:1000 /data

# 解决方案 2：运行时指定用户
docker run -v mydata:/data -u $(id -u):$(id -g) myapp

# 解决方案 3：Dockerfile 中设置正确权限
RUN useradd -r -s /bin/false appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app
COPY --chown=appuser:appuser . /app
USER appuser

# 解决方案 4：使用 init 容器设置权限
docker run --rm -v mydata:/data alpine sh -c 'chown -R 1000:1000 /data && chmod -R 755 /data'
```

#### 9.3 数据卷损坏

```bash
# 问题：数据卷中的数据损坏
# 场景：MySQL 数据文件损坏

# 排查：
# 1. 检查文件系统错误
docker run --rm -v mysql_data:/data alpine ls -la /data

# 2. 检查 MySQL 错误日志
docker logs mysql | grep -i error

# 3. 尝试 MySQL 修复
docker exec mysql mysqlcheck -u root -p'password' --all-databases --repair

# 恢复策略：
# 1. 从备份恢复（最佳方案）
# 2. 使用数据库的修复工具
# 3. 如果有主从复制，从从库恢复

# 预防措施：
# - 定期备份
# - 使用 RAID 或分布式存储
# - 监控磁盘健康状态
# - 使用数据库的复制功能
```

---

## 💻 实战练习

### 练习 1：Volume 完整生命周期

**目标**：掌握 Docker Volume 的创建、使用、共享、备份和恢复。

```bash
# 1. 创建命名数据卷
docker volume create app_data
docker volume create app_config

# 2. 查看数据卷
docker volume ls
docker volume inspect app_data

# 3. 使用数据卷运行容器
docker run -d --name app-v1 \
    -v app_data:/app/data \
    -v app_config:/app/config:ro \
    alpine:3.18 \
    sh -c 'echo "Hello from app-v1" > /app/data/message.txt && sleep 3600'

# 4. 验证数据写入
docker exec app-v1 cat /app/data/message.txt

# 5. 删除容器（数据卷保留）
docker rm -f app-v1
echo "容器已删除，数据卷仍存在："
docker volume ls | grep app_

# 6. 用新容器读取数据
docker run --rm -v app_data:/data:ro alpine cat /data/message.txt
# 应该输出 "Hello from app-v1"

# 7. 备份数据卷
docker run --rm \
    -v app_data:/source:ro \
    -v $(pwd):/backup \
    alpine \
    tar czf /backup/app_data_backup.tar.gz -C /source .

ls -lh app_data_backup.tar.gz

# 8. 删除原数据卷
docker volume rm app_data
echo "原数据卷已删除"

# 9. 恢复数据卷
docker volume create app_data_restored
docker run --rm \
    -v app_data_restored:/dest \
    -v $(pwd):/backup:ro \
    alpine \
    tar xzf /backup/app_data_backup.tar.gz -C /dest

# 10. 验证恢复
docker run --rm -v app_data_restored:/data:ro alpine cat /data/message.txt
# 应该输出 "Hello from app-v1"

# 11. 清理
docker volume rm app_data_restored app_config
rm app_data_backup.tar.gz
```

### 练习 2：Bind Mount 开发环境

**目标**：使用 Bind Mount 搭建开发环境，实现代码热重载。

```bash
# 1. 创建示例 Python 应用
mkdir -p /tmp/dev-app/src
cat > /tmp/dev-app/requirements.txt << 'EOF'
flask==3.0.0
EOF

cat > /tmp/dev-app/src/app.py << 'EOF'
from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Docker! (version 1)"

@app.route('/health')
def health():
    return {"status": "healthy"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
EOF

cat > /tmp/dev-app/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "src/app.py"]
EOF

# 2. 构建镜像
cd /tmp/dev-app
docker build -t dev-app:v1 .

# 3. 使用 bind mount 运行（代码热重载）
docker run -d --name dev-app \
    -v $(pwd)/src:/app/src \
    -p 5000:5000 \
    dev-app:v1

# 4. 访问应用
curl http://localhost:5000/
# 输出: Hello from Docker! (version 1)

# 5. 修改代码（模拟开发）
cat > /tmp/dev-app/src/app.py << 'EOF'
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Hello from Docker! (version 2 - updated!)"

@app.route('/health')
def health():
    return {"status": "healthy"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
EOF

# 6. 验证代码更新（Flask debug 模式会自动重载）
sleep 3
curl http://localhost:5000/
# 输出: Hello from Docker! (version 2 - updated!)

# 7. 清理
docker rm -f dev-app
docker rmi dev-app:v1
rm -rf /tmp/dev-app
```

### 练习 3：生产级数据持久化方案

**目标**：设计和实现一个包含备份、监控的生产级数据持久化方案。

```bash
# 1. 创建完整的 docker-compose 方案
mkdir -p /tmp/prod-data/{mysql/conf.d,mysql/initdb.d,backup}

# MySQL 配置
cat > /tmp/prod-data/mysql/conf.d/custom.cnf << 'EOF'
[mysqld]
innodb_buffer_pool_size = 256M
max_connections = 200
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
EOF

# 初始化脚本
cat > /tmp/prod-data/mysql/initdb.d/init.sql << 'EOF'
CREATE DATABASE IF NOT EXISTS myapp;
USE myapp;
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO users (name, email) VALUES ('test', 'test@example.com');
EOF

# docker-compose.yml
cat > /tmp/prod-data/docker-compose.yml << 'EOF'
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: prod-mysql
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: myapp
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql/conf.d:/etc/mysql/conf.d:ro
      - ./mysql/initdb.d:/docker-entrypoint-initdb.d:ro
      - mysql_logs:/var/log/mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      start-period: 30s
      retries: 5
    restart: unless-stopped

  backup:
    image: alpine:3.18
    container_name: prod-backup
    volumes:
      - mysql_data:/source/mysql:ro
      - ./backup:/backup
    entrypoint: /bin/sh
    command:
      - -c
      - |
        apk add --no-cache mysql-client
        while true; do
          echo "=== 开始备份 $$(date) ==="
          mysqldump -h mysql -u root -prootpassword --all-databases > /backup/all_databases_$$(date +%Y%m%d%H%M%S).sql
          tar czf /backup/mysql_volume_$$(date +%Y%m%d%H%M%S).tar.gz -C /source/mysql .
          # 清理 7 天前的备份
          find /backup -mtime +7 -delete
          echo "=== 备份完成 ==="
          sleep 86400
        done
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped

volumes:
  mysql_data:
    labels:
      com.example.description: "MySQL production data"
  mysql_logs:
    labels:
      com.example.description: "MySQL logs"
EOF

# 2. 启动服务
cd /tmp/prod-data
docker compose up -d

# 3. 等待 MySQL 就绪
echo "等待 MySQL 启动..."
sleep 30

# 4. 验证数据
docker exec prod-mysql mysql -u root -prootpassword -e "SELECT * FROM myapp.users;"

# 5. 查看数据卷
docker volume ls | grep prod-data

# 6. 手动触发备份
docker exec prod-backup /bin/sh -c '
    mysqldump -h mysql -u root -prootpassword --all-databases > /backup/manual_backup.sql
    echo "手动备份完成"
'

# 7. 查看备份文件
ls -lh /tmp/prod-data/backup/

# 8. 模拟数据丢失并恢复
docker exec prod-mysql mysql -u root -prootpassword -e "DELETE FROM myapp.users;"
docker exec prod-mysql mysql -u root -prootpassword -e "SELECT * FROM myapp.users;"

# 从备份恢复
docker exec -i prod-mysql mysql -u root -prootpassword < /tmp/prod-data/backup/manual_backup.sql
docker exec prod-mysql mysql -u root -prootpassword -e "SELECT * FROM myapp.users;"

# 9. 清理
cd /tmp/prod-data
docker compose down -v
rm -rf /tmp/prod-data
```

---

## 🎯 面试题精选

### 面试题 1：Docker Volume、Bind Mount 和 tmpfs 有什么区别？各自的使用场景是什么？

**参考答案**：

三者的核心区别在于存储位置和生命周期。Docker Volume 由 Docker 管理，存储在 /var/lib/docker/volumes/ 下，生命周期独立于容器，适合数据库数据等需要持久化的场景。Bind Mount 将宿主机的目录挂载到容器，直接访问宿主机文件系统，适合开发环境代码挂载和配置文件挂载。tmpfs 存储在内存中，容器停止后数据丢失，适合临时数据和敏感信息。从可移植性看，Volume 最高（Docker 管理），Bind Mount 依赖宿主机路径，tmpfs 无持久性。从性能看，tmpfs 最高（内存），Volume 和 Bind Mount 取决于磁盘。生产环境中数据库数据用 Volume，配置文件用 Bind Mount，临时缓存用 tmpfs。

### 面试题 2：如何备份和恢复 Docker Volume？

**参考答案**：

备份 Volume 的标准方法是使用临时容器：`docker run --rm -v mydata:/source:ro -v /backup:/backup alpine tar czf /backup/mydata.tar.gz -C /source .`。这会将 Volume 中的数据打包为 tar.gz 文件。恢复时创建新的 Volume 并解压：`docker volume create mydata_restored && docker run --rm -v mydata_restored:/dest -v /backup:/backup:ro alpine tar xzf /backup/mydata.tar.gz -C /dest`。对于数据库，更推荐使用原生工具（如 mysqldump）备份，因为直接备份数据文件可能在数据库运行时产生不一致。自动化备份可以使用 cron 定时任务配合备份脚本，保留最近 N 天的备份并自动清理旧备份。

### 面试题 3：什么是孤立数据卷？如何管理？

**参考答案**：

孤立数据卷（dangling volume）是指未被任何容器使用的数据卷。常见产生原因：使用匿名数据卷的容器被删除后，数据卷仍存在；docker-compose down 未使用 -v 参数；手动删除容器但未清理数据卷。管理方法：`docker volume ls --filter "dangling=true"` 查看孤立数据卷，`docker volume prune` 删除所有未使用的数据卷。预防措施：始终使用命名数据卷而非匿名数据卷；docker-compose down 时使用 -v 参数清理相关 Volume；给重要数据卷打标签避免误删；设置定期清理策略。需要注意的是 docker volume prune 会删除所有未使用的 Volume，生产环境应谨慎使用。

### 面试题 4：如何在多个容器之间共享数据？

**参考答案**：

最直接的方式是多个容器挂载同一个 Volume：`docker run -v shared_data:/data writer_app` 和 `docker run -v shared_data:/data reader_app`。需要注意：多个容器同时写入同一文件可能导致数据损坏，建议一个容器写多个容器读，或使用文件锁。对于跨主机的数据共享，需要使用网络存储（NFS、CIFS）或分布式 Volume 驱动（Portworx、GlusterFS）。更推荐的方案是使用消息队列（Redis、RabbitMQ）代替文件共享，或使用对象存储（S3、MinIO）存储共享文件。

### 面试题 5：overlay2 存储驱动如何工作？什么是 Copy-on-Write？

**参考答案**：

overlay2 是 Docker 默认的存储驱动，基于 Linux OverlayFS。它将多个只读层（lowerdir）和一个可写层（upperdir）叠加挂载为一个统一的文件系统视图（merged）。Copy-on-Write（CoW）是其核心机制：读取文件时直接从 lowerdir 读取，性能与原生一致；修改文件时先将文件从 lowerdir 复制到 upperdir，然后在 upperdir 中修改，原始层不受影响；删除文件时在 upperdir 创建 whiteout 文件标记删除。这种设计使得多个容器可以共享相同的镜像只读层，只有修改的部分才占用额外存储。容器删除后其 upperdir 也被删除，但镜像层不受影响。

### 面试题 6：如何解决容器中的文件权限问题？

**参考答案**：

容器中常见的权限问题是：以非 root 用户运行的容器无法读写 Volume 中的文件，因为 Volume 通常由 root 创建。解决方案：1）在 Dockerfile 中使用 `COPY --chown=user:group` 设置文件权限；2）在容器启动前使用 init 容器修改权限：`docker run --rm -v mydata:/data alpine chown -R 1000:1000 /data`；3）在 docker run 时指定用户：`docker run -u $(id -u):$(id -g) myapp`；4）使用 User Namespace 重映射；5）在 Dockerfile 中创建目录并设置权限。最佳实践是在 Dockerfile 中完成所有权限设置，避免运行时修改。

### 面试题 7：如何防止 Docker 日志撑满磁盘？

**参考答案**：

这是最常见的 Docker 生产事故之一。解决方案：1）在 /etc/docker/daemon.json 中配置全局日志轮转：`{"log-driver":"json-file","log-opts":{"max-size":"100m","max-file":"5"}}`；2）单个容器配置：`docker run --log-opt max-size=50m --log-opt max-file=3`；3）使用集中日志系统（ELK、Loki、Splunk），日志收集后清理本地日志；4）监控日志文件大小；5）应用层面控制日志输出量，生产环境使用 INFO 或 WARN 级别。max-size 设置单个文件大小上限，max-file 设置最大文件数，总空间约等于 max-size * max-file。

### 面试题 8：tmpfs 在容器中的使用场景是什么？

**参考答案**：

tmpfs 将数据存储在宿主机内存中，适合以下场景：1）敏感信息临时存储，如 API key、token、证书密钥等，数据只存在于内存中，容器停止后自动清除，不会写入磁盘或进入镜像层；2）高速缓存，内存读写速度远快于磁盘，适合不需要持久化的缓存数据；3）临时文件，应用运行时产生的临时文件，容器重启后自动清理；4）配合只读文件系统使用，`docker run --read-only --tmpfs /tmp:rw,size=100m` 增强安全性。注意事项：tmpfs 会消耗宿主机内存，应设置大小限制（size 参数）；容器停止后数据丢失，不要用于需要持久化的数据。

### 面试题 9：如何设计容器化数据库的存储方案？

**参考答案**：

设计要点：1）使用 Docker Volume 持久化数据库数据，不要依赖容器可写层；2）使用命名 Volume 而非匿名 Volume，便于管理和备份；3）配置数据库的日志和数据使用独立的 Volume，避免日志占满数据盘；4）设置定期备份策略，使用数据库原生工具（mysqldump、pg_dump）或 Volume 快照；5）配置健康检查和重启策略；6）设置合理的资源限制（CPU、内存）；7）生产环境考虑使用网络存储或分布式存储；8）使用 Docker Compose 或 Kubernetes 管理生命周期。关键原则：数据库的生命周期应独立于容器，容器可以重建，但数据必须持久化。

### 面试题 10：如何监控 Docker Volume 的使用情况？

**参考答案**：

监控方法：1）`docker system df -v` 查看所有 Volume 的大小和使用情况；2）`docker volume inspect` 查看 Volume 的详细信息；3）编写脚本遍历所有 Volume 统计大小；4）监控宿主机 /var/lib/docker/volumes/ 目录的磁盘使用；5）使用 Prometheus + Grafana 监控 Docker 指标；6）设置告警阈值，磁盘使用超过 80% 时告警。清理策略：定期运行 `docker volume prune` 清理未使用的 Volume；给重要 Volume 打标签，避免误删；自动化备份脚本中加入清理逻辑。

---

## 📚 深入阅读

### 官方文档
- [Docker 存储文档](https://docs.docker.com/storage/)
- [Docker Volume 文档](https://docs.docker.com/storage/volumes/)
- [Bind Mount 文档](https://docs.docker.com/storage/bind-mounts/)
- [tmpfs Mount 文档](https://docs.docker.com/storage/tmpfs/)
- [OverlayFS 存储驱动](https://docs.docker.com/storage/storagedriver/overlayfs-driver/)

### Linux 内核相关
- [OverlayFS 文档](https://www.kernel.org/doc/html/latest/filesystems/overlayfs.html)
- [Linux 存储管理](https://www.kernel.org/doc/html/latest/admin-guide/blockdev/index.html)

### 推荐书籍
- 《Docker Deep Dive》— Nigel Poulton
- 《Docker - Up & Running》— Sean Kane & Karl Matthias

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 Docker Volume、Bind Mount、tmpfs 的区别和适用场景
- [ ] 理解 Docker Volume 的生命周期（独立于容器）
- [ ] 理解 overlay2 存储驱动的工作原理和 CoW 机制
- [ ] 掌握数据卷备份与恢复的方法
- [ ] 理解孤立数据卷的产生原因和管理方法
- [ ] 知道如何防止日志撑满磁盘

### 实操检查点
- [ ] 能创建、查看、删除 Docker Volume
- [ ] 能使用 Volume 持久化数据库数据
- [ ] 能使用 Bind Mount 搭建开发环境
- [ ] 能编写 Volume 备份和恢复脚本
- [ ] 能配置日志轮转防止磁盘问题
- [ ] 能解决容器文件权限问题

### 能力验证标准
- [ ] 能设计生产级的容器数据持久化方案
- [ ] 能编写自动化备份脚本并设置定时任务
- [ ] 能回答 80% 以上的面试题
- [ ] 能诊断和解决数据相关的生产问题
