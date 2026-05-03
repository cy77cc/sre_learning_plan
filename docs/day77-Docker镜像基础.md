# Day 77: Docker 镜像基础

> 📅 日期：2026-05-03
> 📖 学习主题：Docker 镜像基础 — 镜像分层原理、UnionFS、镜像拉取/查看/删除/导出导入、镜像标签、多架构镜像
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 76 (Docker 简介与安装)

---

## 🎯 学习目标

完成 Day 77 的学习后，你应该能够：
- 深入理解 Docker 镜像的分层存储原理和 OverlayFS 的工作机制
- 掌握镜像的完整生命周期管理（拉取、查看、标签、删除、导出导入）
- 理解镜像命名规范和标签策略
- 掌握多架构镜像的概念和 buildx 使用方法
- 能够诊断和解决镜像相关的常见问题

---

## 📖 核心知识点

### 1. 镜像分层存储原理

#### 1.1 镜像的本质

Docker 镜像不是一个单一的文件，而是由多个只读层（layer）叠加而成的联合文件系统。每一层记录了相对于上一层的文件系统变更（增加、修改、删除文件）。

```
Docker 镜像的层次结构：

  ┌─────────────────────────────────────────┐
  │  Layer 5: CMD ["nginx", "-g", "..."]    │  ← 元数据层（不产生实际文件）
  ├─────────────────────────────────────────┤
  │  Layer 4: COPY nginx.conf /etc/nginx/   │  ← 新增/修改文件
  │           (3.2 KB)                      │
  ├─────────────────────────────────────────┤
  │  Layer 3: RUN apt-get install nginx     │  ← 安装软件包
  │           (28.5 MB)                     │
  ├─────────────────────────────────────────┤
  │  Layer 2: RUN apt-get update            │  ← 更新包索引
  │           (22.1 MB)                     │
  ├─────────────────────────────────────────┤
  │  Layer 1: FROM ubuntu:22.04             │  ← 基础镜像
  │           (77.8 MB)                     │
  └─────────────────────────────────────────┘

  镜像总大小 = 所有层大小之和（去重后）
  注意：相同内容的层在存储中只保留一份
```

#### 1.2 层的存储格式

每一层在宿主机上以一个目录的形式存在，目录名是该层内容的 SHA256 哈希值。

```bash
# 查看 Docker 数据目录结构
sudo ls /var/lib/docker/
# overlay2/  image/  containers/  volumes/  network/  ...

# 查看 overlay2 目录（存储层的实际数据）
sudo ls /var/lib/docker/overlay2/
# 每个层对应一个以 SHA256 命名的目录

# 查看某个镜像的层信息
docker inspect nginx:latest | jq '.[0].RootFS'
# {
#   "Type": "layers",
#   "Layers": [
#     "sha256:e4d0e810d54a...",
#     "sha256:4713cb24eeff...",
#     "sha256:5b1e27e74313...",
#     ...
#   ]
# }
```

#### 1.3 Content Addressable Storage（内容寻址存储）

Docker 使用 SHA256 哈希值来标识每一层的内容，这意味着：
- 相同内容的层具有相同的哈希值，天然去重
- 任何内容变更都会产生新的哈希值，保证完整性
- 镜像的分发可以通过哈希值校验数据完整性

```
内容寻址存储的工作原理：

  Layer 内容 (文件集合)
       │
       │ 计算 SHA256
       ▼
  sha256:abc123...  ── 作为层的唯一标识
       │
       ├── 存储路径：/var/lib/docker/overlay2/sha256_abc123.../
       ├── 如果已存在相同哈希的层 → 直接复用（去重）
       └── 如果不存在 → 创建新目录存储

  实际存储结构：
  /var/lib/docker/overlay2/
  ├── l/                    ← 符号链接目录（短名称指向实际目录）
  │   ├── ABC123 -> ../sha256_abc123.../diff
  │   └── DEF456 -> ../sha256_def456.../diff
  ├── sha256_abc123.../
  │   ├── diff/             ← 该层实际的文件内容
  │   ├── link              ← 短名称（对应 l/ 中的符号链接）
  │   └── lower             ← 指向下层的指针
  └── sha256_def456.../
      ├── diff/
      ├── link
      └── lower
```

#### 1.4 镜像层与容器层的关系

```
一个镜像可以创建多个容器，每个容器有自己的可写层：

  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  镜像 nginx:latest                                          │
  │  ┌─────────────────────────────────────────────────────┐   │
  │  │ Container A (可写层)                                 │   │
  │  ├─────────────────────────────────────────────────────┤   │
  │  │ Container B (可写层)                                 │   │
  │  ├─────────────────────────────────────────────────────┤   │
  │  │ Container C (可写层)                                 │   │
  │  ├─────────────────────────────────────────────────────┤   │
  │  │ 镜像 Layer 4 (只读)                                  │   │
  │  ├─────────────────────────────────────────────────────┤   │
  │  │ 镜像 Layer 3 (只读)                                  │   │
  │  ├─────────────────────────────────────────────────────┤   │
  │  │ 镜像 Layer 2 (只读)                                  │   │
  │  ├─────────────────────────────────────────────────────┤   │
  │  │ 镜像 Layer 1 (只读)                                  │   │
  │  └─────────────────────────────────────────────────────┘   │
  │                                                             │
  │  关键点：                                                    │
  │  - 镜像层是只读的，所有容器共享                              │
  │  - 每个容器有自己的可写层（容器层）                          │
  │  - 容器删除后，其可写层也被删除                              │
  │  - 镜像层不会因为容器的修改而改变                            │
  │                                                             │
  └─────────────────────────────────────────────────────────────┘
```

### 2. OverlayFS 深入解析

#### 2.1 OverlayFS 的工作原理

OverlayFS 是 Docker 默认的存储驱动（overlay2），它将多个目录叠加挂载为一个统一的文件系统。

```
OverlayFS 挂载结构：

  ┌─────────────────────────────────────────────────────────────┐
  │                   merged (合并视图)                          │
  │                   容器看到的文件系统                          │
  │                                                             │
  │  /bin/  /etc/  /lib/  /tmp/  /var/  /usr/  ...             │
  └───────────────────────┬─────────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
            ▼             ▼             ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │  upperdir    │ │   workdir    │ │   lowerdir   │
  │  (可写层)     │ │  (工作目录)   │ │  (只读层)     │
  │              │ │              │ │              │
  │  新增/修改   │ │  OverlayFS   │ │  基础镜像     │
  │  的文件      │ │  内部使用     │ │  的各层       │
  └──────────────┘ └──────────────┘ └──────────────┘

  文件操作行为：
  ┌──────────────┬──────────────────────────────────────────────┐
  │ 操作         │ OverlayFS 行为                                │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 读取文件     │ 先查 upperdir，没有则从 lowerdir 读取         │
  │              │ 读取性能与原生文件系统一致                     │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 创建文件     │ 直接在 upperdir 创建                         │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 修改文件     │ 从 lowerdir 复制到 upperdir（Copy-on-Write） │
  │              │ 在 upperdir 中修改                           │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 删除文件     │ 在 upperdir 创建 character device 文件       │
  │              │ (whiteout)，标记该文件已删除                  │
  ├──────────────┼──────────────────────────────────────────────┤
  │ 删除目录     │ 在 upperdir 创建 opaque 目录                 │
  │              │ (overlayfs.whiteout 类型)                    │
  └──────────────┴──────────────────────────────────────────────┘
```

#### 2.2 验证 OverlayFS 行为

```bash
# 启动一个容器
docker run -d --name overlay-test nginx:latest

# 获取容器的 OverlayFS 挂载信息
docker inspect overlay-test | jq '.[0].GraphDriver'
# {
#   "Data": {
#     "LowerDir": "/var/lib/docker/overlay2/xxx/diff:/var/lib/docker/overlay2/yyy/diff:...",
#     "MergedDir": "/var/lib/docker/overlay2/zzz/merged",
#     "UpperDir": "/var/lib/docker/overlay2/zzz/diff",
#     "WorkDir": "/var/lib/docker/overlay2/zzz/work"
#   },
#   "Name": "overlay2"
# }

# 在容器中创建文件，观察 upperdir 的变化
docker exec overlay-test touch /tmp/new-file.txt
UPPER_DIR=$(docker inspect --format '{{.GraphDriver.Data.UpperDir}}' overlay-test)
ls -la ${UPPER_DIR}/tmp/new-file.txt
# 文件出现在 upperdir 中

# 在容器中修改已存在的文件（来自镜像层），观察 Copy-on-Write
docker exec overlay-test sh -c 'echo "modified" >> /etc/nginx/nginx.conf'
# nginx.conf 从 lowerdir 复制到 upperdir，然后在 upperdir 中修改
ls -la ${UPPER_DIR}/etc/nginx/nginx.conf

# 清理
docker rm -f overlay-test
```

#### 2.3 存储驱动对比

```
Docker 支持的存储驱动对比：

┌─────────────┬────────┬────────┬──────────┬──────────────────────┐
│ 存储驱动     │ 性能   │ 稳定性 │ 内核要求 │ 说明                 │
├─────────────┼────────┼────────┼──────────┼──────────────────────┤
│ overlay2    │ 优秀   │ 优秀   │ 4.0+     │ 推荐，Docker 默认    │
│ fuse-overlay│ 良好   │ 良好   │ 4.18+    │ Rootless Docker 用   │
│ btrfs       │ 良好   │ 良好   │ 3.13+    │ 需要 btrfs 文件系统  │
│ zfs         │ 良好   │ 良好   │ -        │ 需要 ZFS 文件系统    │
│ vfs         │ 差     │ 优秀   │ 无要求   │ 无 CoW，调试用       │
│ devicemapper│ 一般   │ 一般   │ 3.10+    │ 已弃用               │
│ aufs        │ 良好   │ 一般   │ 需补丁   │ 已弃用，仅 Ubuntu    │
└─────────────┴────────┴────────┴──────────┴──────────────────────┘

生产环境建议：overlay2（默认且推荐）
```

### 3. 镜像拉取与查看

#### 3.1 镜像命名规范

```
Docker 镜像完整命名格式：

  [registry_host[:port]/][namespace/]name[:tag|@digest]

  各部分说明：
  ┌────────────────────┬───────────────────────────────────────────┐
  │ 组件               │ 说明                                      │
  ├────────────────────┼───────────────────────────────────────────┤
  │ registry_host      │ 仓库地址，默认 docker.io                  │
  │ :port              │ 仓库端口，默认 443 (HTTPS)                │
  │ namespace          │ 命名空间/组织名                            │
  │   - 官方镜像       │ library（可省略）                         │
  │   - 用户镜像       │ 用户名或组织名                            │
  │ name               │ 镜像名称                                  │
  │ :tag               │ 标签，默认 latest                         │
  │ @digest            │ SHA256 哈希值，精确标识                    │
  └────────────────────┴───────────────────────────────────────────┘

  示例：
  nginx                          → docker.io/library/nginx:latest
  nginx:1.25                     → docker.io/library/nginx:1.25
  myuser/myapp:v1.0              → docker.io/myuser/myapp:v1.0
  gcr.io/google-containers/pause:3.9  → Google Container Registry
  registry.example.com/app:v2    → 私有仓库
  nginx@sha256:abc123...         → 通过 digest 精确引用
```

#### 3.2 镜像拉取详解

```bash
# 拉取默认标签（latest）
docker pull nginx
# 等同于 docker pull docker.io/library/nginx:latest

# 拉取指定标签
docker pull nginx:1.25-alpine

# 拉取指定平台的镜像（多架构场景）
docker pull --platform linux/amd64 nginx:latest
docker pull --platform linux/arm64 nginx:latest

# 拉取指定 digest（精确版本，不可变）
docker pull nginx@sha256:e4d0e810d54ae10...

# 从私有仓库拉取
docker login registry.example.com
docker pull registry.example.com/myteam/myapp:v1.0

# 拉取所有标签（慎用，会拉取大量数据）
# 没有直接的命令，需要脚本实现
```

```
镜像拉取的底层流程：

  docker pull nginx:1.25-alpine
       │
       │ 1. 解析镜像名称
       │    registry: docker.io
       │    repository: library/nginx
       │    tag: 1.25-alpine
       ▼
  Docker Daemon
       │
       │ 2. 获取认证 token（如果是私有仓库）
       ▼
  Docker Registry (registry-1.docker.io)
       │
       │ 3. 获取 manifest（镜像清单）
       │    - manifest list（多架构）→ 选择匹配平台
       │    - manifest（单架构）→ 包含 config 和 layers 列表
       ▼
  Docker Daemon
       │
       │ 4. 检查本地已有哪些层
       │    对比 manifest 中的 layer digest
       ▼
  Docker Registry
       │
       │ 5. 下载缺失的层（并行下载）
       │    每层通过 digest 校验完整性
       ▼
  Docker Daemon
       │
       │ 6. 解压层到 overlay2 目录
       │ 7. 注册镜像到本地数据库
       ▼
  镜像可用
```

#### 3.3 镜像查看与检查

```bash
# 列出本地镜像
docker images
# REPOSITORY   TAG       IMAGE ID       CREATED      SIZE
# nginx        latest    a6bd71f48f68   2 weeks ago  187MB
# ubuntu       22.04     8a3cdc4d1ad3   3 weeks ago  77.8MB

# 格式化输出
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"

# 只显示镜像 ID
docker images -q

# 包含中间层镜像
docker images -a

# 过滤镜像
docker images --filter "dangling=true"        # 悬空镜像（无标签）
docker images --filter "reference=nginx*"     # 匹配名称
docker images --filter "before=nginx:latest"  # 在某镜像之前创建的
docker images --filter "since=ubuntu:22.04"   # 在某镜像之后创建的

# 查看镜像详细信息
docker inspect nginx:latest

# 查看镜像构建历史
docker history nginx:latest
docker history --no-trunc nginx:latest  # 显示完整命令

# 查看镜像占用的磁盘空间
docker system df
docker system df -v  # 详细信息，包括每个镜像的大小

# 查看镜像的层信息
docker inspect nginx:latest | jq '.[0].RootFS.Layers'

# 查看镜像的环境变量
docker inspect nginx:latest | jq '.[0].Config.Env'

# 查看镜像暴露的端口
docker inspect nginx:latest | jq '.[0].Config.ExposedPorts'

# 查看镜像的入口点和命令
docker inspect nginx:latest | jq '.[0].Config | {Entrypoint, Cmd}'
```

### 4. 镜像标签管理

#### 4.1 标签的作用与策略

```
镜像标签的本质：
  标签是指向某个镜像 ID 的"指针"
  同一个镜像 ID 可以有多个标签
  标签可以被移动（指向新的镜像 ID）

  示例：
  nginx:latest    ──→ sha256:a6bd71f48f68
  nginx:1.25      ──→ sha256:a6bd71f48f68  (同一个镜像)
  nginx:1.25.3    ──→ sha256:a6bd71f48f68  (同一个镜像)

  当新版本发布后：
  nginx:latest    ──→ sha256:b7c8e9f12345  (指向新镜像)
  nginx:1.25      ──→ sha256:a6bd71f48f68  (保持不变)
  nginx:1.26      ──→ sha256:b7c8e9f12345  (新标签)
```

```bash
# 给镜像打标签
docker tag nginx:latest myregistry.com/myapp:v1.0
docker tag nginx:latest myregistry.com/myapp:latest
docker tag nginx:latest myregistry.com/myapp:1.25

# 查看标签指向的镜像 ID
docker inspect --format '{{.Id}}' nginx:latest
docker inspect --format '{{.Id}}' nginx:1.25
# 两者应该相同

# 推送带标签的镜像
docker push myregistry.com/myapp:v1.0
docker push myregistry.com/myapp:latest
```

#### 4.2 生产环境标签最佳实践

```
标签策略对比：

┌─────────────────┬─────────────────────────────────────────────────┐
│ 标签类型         │ 说明                                            │
├─────────────────┼─────────────────────────────────────────────────┤
│ latest          │ 不推荐用于生产                                   │
│                 │ 会随新版本发布而改变                              │
│                 │ 适合开发/测试环境                                │
├─────────────────┼─────────────────────────────────────────────────┤
│ 语义化版本       │ 推荐用于生产                                     │
│ v1.2.3          │ 精确标识版本，不可变                             │
│                 │ 便于回滚和审计                                   │
├─────────────────┼─────────────────────────────────────────────────┤
│ Git SHA         │ 推荐用于 CI/CD                                  │
│ abc1234         │ 与代码提交关联                                   │
│                 │ 便于追溯到具体的代码变更                          │
├─────────────────┼─────────────────────────────────────────────────┤
│ 构建号          │ 推荐用于 CI/CD                                  │
│ build-1234      │ 与构建流水线关联                                 │
│                 │ 便于追踪构建历史                                 │
├─────────────────┼─────────────────────────────────────────────────┤
│ 分支名          │ 适合开发环境                                     │
│ feature-xxx     │ 标识功能分支的构建                               │
├─────────────────┼─────────────────────────────────────────────────┤
│ 环境标识        │ 不推荐（应通过部署配置区分环境）                  │
│ prod/staging    │ 标签应标识镜像内容，而非部署目标                  │
└─────────────────┴─────────────────────────────────────────────────┘

推荐的标签组合策略：
  myapp:v1.2.3           ← 语义化版本（生产部署）
  myapp:abc1234          ← Git commit SHA（CI/CD 追溯）
  myapp:latest           ← 最新稳定版（开发环境便捷使用）
```

### 5. 镜像删除与清理

#### 5.1 删除镜像

```bash
# 删除指定镜像
docker rmi nginx:latest
docker image rm nginx:latest

# 通过 IMAGE ID 删除
docker rmi a6bd71f48f68

# 强制删除（即使有容器在使用）
docker rmi -f nginx:latest

# 删除多个镜像
docker rmi nginx:latest ubuntu:22.04 redis:7

# 删除所有镜像（慎用）
docker rmi $(docker images -q)

# 删除悬空镜像（无标签的镜像）
docker image prune

# 删除所有未使用的镜像
docker image prune -a

# 过滤删除（7天前创建的未使用镜像）
docker image prune -a --filter "until=168h"
```

```
镜像删除的注意事项：

1. 同一个 IMAGE ID 有多个标签时：
   docker rmi myapp:v1  → 只删除标签，不删除镜像数据
   docker rmi myapp:v2  → 删除最后一个标签后，镜像数据才被删除

2. 有容器在使用镜像时：
   docker rmi myapp:v1  → 报错：image is being used
   解决：先删除容器，或使用 -f 强制删除

3. 镜像层被多个镜像共享时：
   删除一个镜像不会删除共享的层
   只有当没有任何镜像引用某层时，该层才会被删除

4. 悬空镜像 (dangling image)：
   指没有标签且不被任何镜像引用的镜像层
   通常在重新构建镜像时产生（旧的中间层变成悬空）
   定期清理：docker image prune
```

#### 5.2 系统级清理

```bash
# 查看磁盘使用情况
docker system df
# TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
# Images          15        5         2.5GB     1.2GB (48%)
# Containers      3         2         100MB     50MB (50%)
# Local Volumes   8         3         500MB     300MB (60%)
# Build Cache     20        0         800MB     800MB (100%)

# 详细信息
docker system df -v

# 清理所有未使用的资源
docker system prune

# 深度清理（包括未使用的镜像和构建缓存）
docker system prune -a

# 清理所有内容（包括 Volume，数据会丢失！）
docker system prune -a --volumes

# 按时间清理
docker system prune --filter "until=72h"  # 清理 3 天前的资源
```

### 6. 镜像导出与导入

#### 6.1 docker save / docker load

`docker save` 和 `docker load` 用于镜像的离线传输，保留完整的镜像元数据（标签、层信息等）。

```bash
# 导出镜像为 tar 文件
docker save nginx:latest -o nginx-latest.tar
docker save nginx:latest | gzip > nginx-latest.tar.gz

# 导出多个镜像到一个文件
docker save nginx:latest redis:7 -o my-images.tar

# 通过 stdout 导出（适合管道传输）
docker save nginx:latest | ssh user@remote "docker load"

# 导入镜像
docker load -i nginx-latest.tar
docker load < nginx-latest.tar
gunzip -c nginx-latest.tar.gz | docker load

# 验证导入
docker images nginx
```

```
docker save/load vs docker export/import 的区别：

┌────────────────┬──────────────────────┬──────────────────────┐
│                │ docker save/load     │ docker export/import │
├────────────────┼──────────────────────┼──────────────────────┤
│ 操作对象       │ 镜像 (Image)         │ 容器 (Container)     │
│ 保留层信息     │ 是（保留完整分层）    │ 否（合并为单层）     │
│ 保留元数据     │ 是（标签、ENV 等）    │ 否                   │
│ 文件大小       │ 较小（层可以压缩）    │ 较大（所有文件）     │
│ 用途           │ 镜像离线传输         │ 容器文件系统快照     │
│ 可 docker build│ 否                   │ 可作为 FROM 的基础   │
│ 典型场景       │ 离线环境部署         │ 容器调试、文件提取   │
└────────────────┴──────────────────────┴──────────────────────┘
```

#### 6.2 docker export / docker import

```bash
# 导出容器的文件系统
docker export my-container > container-fs.tar
docker export my-container | gzip > container-fs.tar.gz

# 导入为镜像（注意：会丢失所有元数据）
docker import container-fs.tar myimage:v1
cat container-fs.tar | docker import - myimage:v1

# 导入时指定启动命令
docker import - myimage:v1 --change 'CMD ["nginx", "-g", "daemon off;"]' < container-fs.tar
docker import container-fs.tar myimage:v1 \
    --change 'EXPOSE 80' \
    --change 'CMD ["nginx", "-g", "daemon off;"]'

# 使用场景：从运行中的容器创建快照
docker run -d --name snap-test nginx
docker exec snap-test sh -c 'echo "custom content" > /usr/share/nginx/html/index.html'
docker export snap-test > nginx-snapshot.tar
docker import nginx-snapshot.tar my-nginx:v1 --change 'CMD ["nginx", "-g", "daemon off;"]'
docker rm -f snap-test
```

### 7. 多架构镜像

#### 7.1 什么是多架构镜像

随着 ARM 服务器（AWS Graviton、Apple Silicon）的普及，多架构镜像变得越来越重要。

```
多架构镜像（Multi-Architecture Image）：

  用户执行：docker pull nginx:latest
       │
       ▼
  Docker 检测当前平台：linux/amd64
       │
       ▼
  Registry 返回 manifest list（镜像清单列表）
  ┌─────────────────────────────────────────────────────────┐
  │  Manifest List (nginx:latest)                            │
  │  ┌─────────────────────────────────────────────────────┐│
  │  │ platform: linux/amd64                               ││
  │  │ digest: sha256:abc123...                            ││
  │  │ size: 187MB                                         ││
  │  └─────────────────────────────────────────────────────┘│
  │  ┌─────────────────────────────────────────────────────┐│
  │  │ platform: linux/arm64                               ││
  │  │ digest: sha256:def456...                            ││
  │  │ size: 182MB                                         ││
  │  └─────────────────────────────────────────────────────┘│
  │  ┌─────────────────────────────────────────────────────┐│
  │  │ platform: linux/arm/v7                              ││
  │  │ digest: sha256:ghi789...                            ││
  │  │ size: 175MB                                         ││
  │  └─────────────────────────────────────────────────────┘│
  └─────────────────────────────────────────────────────────┘
       │
       │ 选择匹配的平台
       ▼
  拉取 linux/amd64 对应的镜像层
```

#### 7.2 使用 Docker Buildx 构建多架构镜像

```bash
# 1. 创建 buildx builder（支持多平台构建）
docker buildx create --name mybuilder --use
docker buildx ls

# 2. 构建多架构镜像并推送到仓库
docker buildx build \
    --platform linux/amd64,linux/arm64,linux/arm/v7 \
    -t myregistry.com/myapp:v1.0 \
    --push \
    .

# 3. 只构建不推送（需要 QEMU 模拟器）
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t myapp:v1.0 \
    --load \
    .
# 注意：--load 只支持单平台

# 4. 查看多架构镜像的 manifest
docker buildx imagetools inspect myregistry.com/myapp:v1.0

# 5. 查看远程仓库中的 manifest
docker manifest inspect nginx:latest
```

#### 7.3 多架构 Dockerfile 最佳实践

```dockerfile
# 使用多架构基础镜像
FROM --platform=$BUILDPLATFORM golang:1.21-alpine AS builder

# 声明目标平台参数
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETOS
ARG TARGETARCH

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .

# 根据目标平台编译
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    go build -ldflags="-s -w" -o /server .

# 运行阶段使用目标平台的基础镜像
FROM alpine:3.18
RUN apk --no-cache add ca-certificates tzdata
COPY --from=builder /server /server
USER nobody
EXPOSE 8080
ENTRYPOINT ["/server"]
```

```
Buildx 构建多架构镜像的流程：

  开发者机器 (linux/amd64)
       │
       │ docker buildx build --platform linux/amd64,linux/arm64
       ▼
  Docker BuildKit
       │
       ├── linux/amd64 构建
       │   ├── 直接在本机构建（原生）
       │   ├── 运行 golang:1.21-alpine (amd64)
       │   └── 编译出 amd64 二进制
       │
       └── linux/arm64 构建
           ├── 通过 QEMU 模拟器构建
           ├── 运行 golang:1.21-alpine (arm64)
           └── 编译出 arm64 二进制
       │
       │ 生成 manifest list
       ▼
  推送到 Registry
       │
       │ 包含两个平台的镜像层 + manifest list
       ▼
  用户拉取时自动选择匹配的平台
```

### 8. 镜像安全基础

#### 8.1 镜像签名与验证

```bash
# 使用 Docker Content Trust (DCT) 验证镜像签名
export DOCKER_CONTENT_TRUST=1

# 拉取时自动验证签名
docker pull nginx:latest
# 如果镜像未签名，拉取会失败

# 签名镜像（需要先生成密钥对）
docker trust key generate my-signing-key
docker trust signer add --key my-signing-key my-signer myregistry.com/myapp
docker push myregistry.com/myapp:v1.0  # 推送时自动签名

# 查看镜像签名信息
docker trust inspect --pretty myregistry.com/myapp:v1.0

# 禁用 DCT（恢复默认行为）
export DOCKER_CONTENT_TRUST=0
```

#### 8.2 镜像漏洞扫描

```bash
# 使用 Docker Scout 扫描镜像漏洞（Docker 官方工具）
docker scout cves nginx:latest
docker scout recommendations nginx:latest

# 使用 Trivy 扫描（开源工具，推荐）
trivy image nginx:latest
trivy image --severity HIGH,CRITICAL nginx:latest

# 扫描结果示例
# nginx:latest (debian 12.4)
# Total: 150 (UNKNOWN: 0, LOW: 80, MEDIUM: 50, HIGH: 15, CRITICAL: 5)
#
# ┌──────────────┬───────────────┬──────────┬─────────────────┐
# │   Library    │   Vulnerability│  Severity│  Fixed Version  │
# ├──────────────┼───────────────┼──────────┼─────────────────┤
# │ libssl3      │ CVE-2024-XXX  │ CRITICAL │ 3.0.13-1~deb12  │
# │ openssl      │ CVE-2024-YYY  │ HIGH     │ 3.0.13-1~deb12  │
# └──────────────┴───────────────┴──────────┴─────────────────┘

# 使用 Docker Desktop 的漏洞扫描
docker scan nginx:latest
```

### 9. SRE 实战：镜像管理故障排查

#### 9.1 磁盘空间不足

```bash
# 问题：Docker 占用大量磁盘空间
# 排查步骤：

# 1. 查看 Docker 整体磁盘使用
docker system df
docker system df -v

# 2. 查找最大的镜像
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | sort -k3 -h

# 3. 查找悬空镜像
docker images -f "dangling=true"

# 4. 查找未使用的容器
docker ps -a --filter "status=exited" --filter "status=dead"

# 5. 清理策略（从保守到激进）
docker image prune                    # 清理悬空镜像
docker container prune                # 清理已停止的容器
docker system prune                   # 清理所有未使用的资源
docker system prune -a                # 包括未使用的镜像
docker system prune -a --volumes      # 包括未使用的 Volume（慎用！）

# 6. 自动清理脚本（加入 crontab）
cat > /usr/local/bin/docker-cleanup.sh << 'EOF'
#!/bin/bash
# 清理 7 天前的已停止容器
docker container prune -f --filter "until=168h"
# 清理悬空镜像
docker image prune -f
# 清理未使用的网络
docker network prune -f --filter "until=168h"
EOF
chmod +x /usr/local/bin/docker-cleanup.sh
# crontab: 0 2 * * * /usr/local/bin/docker-cleanup.sh
```

#### 9.2 镜像拉取失败

```bash
# 问题 1：网络超时
# 症状：Error response from daemon: Get https://registry-1.docker.io/v2/: net/http: timeout
# 解决：
# - 配置镜像加速器
# - 检查网络连通性：curl -v https://registry-1.docker.io/v2/
# - 使用代理：export HTTP_PROXY=http://proxy:8080

# 问题 2：认证失败
# 症状：unauthorized: authentication required
# 解决：
docker login
# 或者使用 token
docker login -u <username> --password-stdin < <(echo $TOKEN)

# 问题 3：镜像不存在
# 症状：manifest for xxx not found
# 排查：
# - 检查镜像名称和标签是否正确
# - 确认镜像是否在目标仓库中
docker search <image_name>
# 或者在 Docker Hub 网站上搜索

# 问题 4：架构不匹配
# 症状：exec format error / image with reference ... not found
# 排查：
docker manifest inspect <image>:<tag>
# 解决：指定正确的平台
docker pull --platform linux/arm64 <image>:<tag>
```

#### 9.3 镜像层损坏

```bash
# 问题：镜像层数据损坏
# 症状：failed to register layer / error creating overlay mount

# 排查：
# 1. 检查 Docker 数据目录的文件系统
df -h /var/lib/docker
# 检查是否有 I/O 错误
dmesg | grep -i "error\|fail\|corrupt"

# 2. 尝试重新拉取镜像
docker rmi <image>
docker pull <image>

# 3. 如果问题持续，清理并重建存储
sudo systemctl stop docker
sudo rm -rf /var/lib/docker/overlay2/*  # 慎用！会丢失所有镜像
sudo systemctl start docker
docker pull <image>

# 4. 检查存储驱动一致性
docker info | grep "Storage Driver"
# 确保 daemon.json 中的配置与实际一致
```

---

## 💻 实战练习

### 练习 1：镜像分层分析

**目标**：深入理解镜像的分层结构，分析层的复用情况。

```bash
# 1. 拉取基础镜像
docker pull ubuntu:22.04
docker pull nginx:latest

# 2. 查看 ubuntu 镜像的层信息
echo "=== Ubuntu 镜像层 ==="
docker history ubuntu:22.04
echo ""
echo "Ubuntu 层摘要："
docker inspect ubuntu:22.04 | jq '.[0].RootFS.Layers | length'
echo "层数"

# 3. 查看 nginx 镜像的层信息
echo "=== Nginx 镜像层 ==="
docker history nginx:latest
echo ""
echo "Nginx 层摘要："
docker inspect nginx:latest | jq '.[0].RootFS.Layers | length'
echo "层数"

# 4. 构建一个基于 ubuntu 的镜像，观察层复用
cat > /tmp/Dockerfile.test << 'EOF'
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl
COPY /tmp/test-file.txt /tmp/
EOF
echo "test content" > /tmp/test-file.txt

docker build -t layer-test:v1 -f /tmp/Dockerfile.test /tmp/
docker history layer-test:v1

# 5. 修改 test-file.txt 重新构建，观察缓存
echo "modified content" > /tmp/test-file.txt
docker build -t layer-test:v2 -f /tmp/Dockerfile.test /tmp/
# 注意：apt-get update 层使用了缓存，只有 COPY 层重新构建

# 6. 验证层共享
echo "=== 层复用验证 ==="
docker system df -v | grep -E "ubuntu|layer-test"

# 7. 清理
docker rmi layer-test:v1 layer-test:v2
rm /tmp/test-file.txt /tmp/Dockerfile.test
```

### 练习 2：镜像导出导入与离线传输

**目标**：模拟离线环境下的镜像传输场景。

```bash
# 场景：在没有网络的环境中部署 Docker 镜像

# 1. 在有网络的机器上导出镜像
docker pull redis:7-alpine
docker save redis:7-alpine -o redis-7-alpine.tar
ls -lh redis-7-alpine.tar

# 2. 查看导出的 tar 内容
tar tf redis-7-alpine.tar | head -20
# 包含 manifest.json、repositories、各层的目录

# 3. 压缩传输（适合通过 scp/rsync 传输）
gzip redis-7-alpine.tar
ls -lh redis-7-alpine.tar.gz

# 4. 在目标机器上导入
gunzip redis-7-alpine.tar.gz
docker load -i redis-7-alpine.tar
docker images redis

# 5. 验证导入的镜像可以正常运行
docker run --rm redis:7-alpine redis-cli ping
# 应输出 PONG

# 6. 对比 save/load 和 export/import 的区别
# 使用 export/import
docker run -d --name export-test redis:7-alpine sleep 300
docker export export-test > redis-fs.tar
docker import redis-fs.tar redis-imported:v1
docker images | grep redis
# 注意：import 的镜像没有 ENTRYPOINT 和 CMD

# 7. 清理
docker rm -f export-test
docker rmi redis-imported:v1
rm -f redis-7-alpine.tar redis-fs.tar
```

### 练习 3：多架构镜像构建

**目标**：使用 Docker Buildx 构建多架构镜像。

```bash
# 1. 准备一个简单的应用
mkdir -p /tmp/multi-arch-test
cat > /tmp/multi-arch-test/main.go << 'EOF'
package main

import (
    "fmt"
    "net/http"
    "runtime"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "Hello from %s/%s\n", runtime.GOOS, runtime.GOARCH)
    })
    http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        fmt.Fprint(w, "ok")
    })
    fmt.Println("Server starting on :8080")
    http.ListenAndServe(":8080", nil)
}
EOF

cat > /tmp/multi-arch-test/Dockerfile << 'EOF'
FROM --platform=$BUILDPLATFORM golang:1.21-alpine AS builder
ARG TARGETOS
ARG TARGETARCH
WORKDIR /app
COPY main.go .
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -o /server main.go

FROM alpine:3.18
COPY --from=builder /server /server
EXPOSE 8080
CMD ["/server"]
EOF

# 2. 创建 buildx builder
docker buildx create --name multiarch-builder --use 2>/dev/null || docker buildx use multiarch-builder
docker buildx inspect --bootstrap

# 3. 构建多架构镜像（本地查看，不推送）
cd /tmp/multi-arch-test
docker buildx build --platform linux/amd64,linux/arm64 -t multi-arch-test:v1 .

# 4. 只构建当前平台并加载到本地
docker buildx build --platform linux/amd64 -t multi-arch-test:amd64 --load .
docker buildx build --platform linux/arm64 -t multi-arch-test:arm64 --load . 2>/dev/null || echo "ARM64 需要 QEMU 支持"

# 5. 查看镜像信息
docker images multi-arch-test

# 6. 清理
docker buildx rm multiarch-builder 2>/dev/null || true
docker rmi multi-arch-test:v1 multi-arch-test:amd64 multi-arch-test:arm64 2>/dev/null || true
rm -rf /tmp/multi-arch-test
```

---

## 🎯 面试题精选

### 面试题 1：解释 Docker 镜像的分层存储原理，为什么这样设计？

**参考答案**：

Docker 镜像由多个只读层叠加组成，每一层记录了相对于上一层的文件系统变更。这种设计基于联合文件系统（UnionFS），Docker 默认使用 Overlay2 驱动。分层存储的优势在于：1）层复用，多个镜像可以共享相同的基础层（如 ubuntu:22.04），节省存储空间；2）加速构建，未变更的层可以使用缓存，只需重新构建变化的层；3）高效分发，拉取镜像时只需下载本地缺失的层；4）快速启动，容器只需在镜像层上添加一个薄薄的可写层。每一层通过 SHA256 哈希值标识，实现了内容寻址存储，保证了数据的完整性和去重。

### 面试题 2：Overlay2 存储驱动如何实现 Copy-on-Write？

**参考答案**：

Overlay2 使用 lowerdir（只读层）和 upperdir（可写层）的概念。当容器读取文件时，先查 upperdir，没有则从 lowerdir 读取，性能与原生一致。当修改文件时，OverlayFS 先将文件从 lowerdir 复制到 upperdir（这就是 Copy-on-Write），然后在 upperdir 中修改，原始层不受影响。当删除文件时，在 upperdir 创建一个 whiteout 文件（特殊字符设备），标记该文件已删除。当创建新文件时，直接在 upperdir 创建。workdir 是 OverlayFS 内部使用的临时目录。merged 是最终的合并视图，容器看到的是所有层叠加后的统一文件系统。

### 面试题 3：docker save/load 和 docker export/import 有什么区别？

**参考答案**：

两者的核心区别在于操作对象和保留信息不同。docker save/load 操作的是镜像，保留完整的分层结构、元数据（标签、环境变量、入口点、命令等），导出的 tar 文件中包含 manifest.json 和各层的目录结构。docker export/import 操作的是容器，导出的是容器的文件系统快照，所有层合并为单层，丢失所有元数据（标签、ENV、CMD、ENTRYPOINT 等），import 后需要手动指定启动命令。在使用场景上，save/load 用于镜像的离线传输和备份，export/import 用于容器调试和文件系统提取。文件大小方面，save 导出的文件通常更小（保留层结构和压缩）。

### 面试题 4：什么是多架构镜像？如何构建？

**参考答案**：

多架构镜像（Multi-Architecture Image）是指同一个镜像标签下包含多个平台（如 linux/amd64、linux/arm64、linux/arm/v7）的版本。当用户执行 docker pull 时，Docker 自动根据当前平台选择匹配的镜像。构建多架构镜像需要使用 Docker Buildx 工具，命令为 `docker buildx build --platform linux/amd64,linux/arm64 -t myapp:v1 --push .`。Buildx 会为每个目标平台分别构建镜像层，然后创建一个 manifest list 指向各平台的 manifest。在非本机平台的构建中，依赖 QEMU 用户态模拟器。Dockerfile 中可以使用 `$BUILDPLATFORM`、`$TARGETPLATFORM`、`$TARGETOS`、`$TARGETARCH` 等变量来优化构建过程。

### 面试题 5：如何清理 Docker 占用的磁盘空间？

**参考答案**：

清理 Docker 磁盘空间分层级进行：1）悬空镜像清理：`docker image prune`，删除没有标签且不被引用的镜像层。2）已停止容器清理：`docker container prune`。3）未使用的网络清理：`docker network prune`。4）综合清理：`docker system prune`，清理所有未使用的容器、网络、悬空镜像。5）深度清理：`docker system prune -a`，包括所有未使用的镜像（不仅仅是悬空的）。6）完整清理：`docker system prune -a --volumes`，还包括未使用的 Volume（慎用，数据不可恢复）。生产环境建议设置定时任务，每天清理 3 天前的未使用资源。同时在 daemon.json 中配置日志轮转（max-size、max-file），防止容器日志撑满磁盘。

### 面试题 6：镜像标签的本质是什么？latest 标签有什么特殊之处？

**参考答案**：

镜像标签本质上是指向某个镜像 ID 的可变指针（mutable reference）。同一个镜像 ID 可以有多个标签，标签可以被移动到新的镜像 ID 上。latest 标签没有任何特殊的技术含义，它只是默认标签——当用户不指定标签时，Docker 自动使用 latest。latest 不一定代表最新版本，它只是最后一次被推送到该标签的镜像。生产环境中不应使用 latest，因为它会导致不可重现的部署——今天拉取的 latest 和明天拉取的可能是不同的镜像。推荐使用语义化版本（v1.2.3）或 Git SHA 作为标签，确保每次部署的镜像内容一致。

### 面试题 7：什么是悬空镜像？如何产生的？

**参考答案**：

悬空镜像（dangling image）是指没有标签且不被任何镜像引用的镜像层。最常见的产生方式是重新构建镜像时——当你用相同的标签（如 myapp:latest）重新构建镜像，新镜像获得该标签，旧镜像的标签被移除，但镜像数据仍然存在，就变成了悬空镜像。可以通过 `docker images -f "dangling=true"` 查看，通过 `docker image prune` 清理。在 CI/CD 流水线中，频繁构建会积累大量悬空镜像，应设置定期清理。另外，多阶段构建中的中间阶段镜像也可能是悬空的。

### 面试题 8：如何确保拉取的镜像是安全的？

**参考答案**：

确保镜像安全有多个层次：1）使用官方镜像或可信来源的镜像，避免使用来路不明的镜像。2）启用 Docker Content Trust（DCT），设置 `DOCKER_CONTENT_TRUST=1`，只拉取签名的镜像。3）使用镜像漏洞扫描工具（如 Trivy、Docker Scout、Grype）扫描镜像中的已知漏洞。4）使用最小基础镜像（Alpine、distroless）减少攻击面。5）在 Dockerfile 中使用非 root 用户运行应用。6）使用多阶段构建，不将构建工具和源代码包含在最终镜像中。7）在 CI/CD 流水线中集成镜像扫描，阻止有高危漏洞的镜像部署。

### 面试题 9：解释镜像的 digest 和 tag 有什么区别？

**参考答案**：

Tag 是镜像的人类可读标签（如 v1.0、latest），是可变的——同名标签可以指向不同的镜像。Digest 是镜像内容的 SHA256 哈希值（如 sha256:abc123...），是不可变的——同一 digest 永远指向同一内容。在生产环境中，使用 digest 引用镜像可以确保部署的精确性：`docker pull nginx@sha256:e4d0e810d54a...`。tag 适合人类使用，digest 适合自动化流水线。最佳实践是在 CI/CD 中同时记录 tag 和 digest，部署时使用 digest 引用，同时保留 tag 作为人类可读的标识。

### 面试题 10：Docker 镜像和容器的关系是什么？删除镜像会影响正在运行的容器吗？

**参考答案**：

镜像是只读模板，容器是镜像的运行实例。一个镜像可以创建多个容器，每个容器在镜像层之上添加一个可写层。删除镜像时，如果有容器（包括已停止的）在使用该镜像，Docker 会拒绝删除，报错"image is being used by running container"。使用 `docker rmi -f` 可以强制删除镜像，但正在运行的容器不受影响——因为容器已经将镜像层加载到了 OverlayFS 中，删除镜像只是删除了本地的镜像引用，不会影响正在使用的层数据。但已停止的容器如果需要重启，会因为找不到镜像而失败。最佳实践是先删除容器，再删除镜像。

---

## 📚 深入阅读

### 官方文档
- [Docker 镜像文档](https://docs.docker.com/engine/reference/commandline/images/)
- [Docker 存储驱动文档](https://docs.docker.com/storage/storagedriver/)
- [OverlayFS 文档](https://docs.docker.com/storage/storagedriver/overlayfs-driver/)
- [Docker Buildx 文档](https://docs.docker.com/build/buildx/)
- [OCI Image Specification](https://github.com/opencontainers/image-spec)

### 技术深度文章
- [Docker 镜像规范详解](https://www.docker.com/blog/docker-oci-image-specification/)
- [深入理解 Docker 存储驱动](https://www.projectatomic.io/blog/2015/06/notes-on-fedora-centos-and-docker-storage-drivers/)
- [BuildKit 和多阶段构建](https://docs.docker.com/build/buildkit/)

### 推荐书籍
- 《Docker Deep Dive》— Nigel Poulton（第 7-9 章：镜像、存储驱动）
- 《Docker - Up & Running》— Sean Kane & Karl Matthias

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释 Docker 镜像的分层存储原理和优势
- [ ] 理解 OverlayFS（overlay2）的工作机制和 CoW 原理
- [ ] 知道镜像命名规范的各个组成部分
- [ ] 理解 docker save/load 与 docker export/import 的区别
- [ ] 理解多架构镜像的概念和构建方式
- [ ] 知道镜像标签的本质（可变指针）和 latest 的特殊性

### 实操检查点
- [ ] 能使用 docker images/inspect/history 查看镜像信息
- [ ] 能正确使用标签策略管理镜像版本
- [ ] 能执行镜像的导出导入操作
- [ ] 能使用 docker system prune 清理磁盘空间
- [ ] 能使用 Buildx 构建多架构镜像
- [ ] 能使用 Trivy 或 Docker Scout 扫描镜像漏洞

### 能力验证标准
- [ ] 能独立分析任意镜像的分层结构和大小分布
- [ ] 能设计适合团队的镜像标签管理策略
- [ ] 能诊断和解决镜像相关的磁盘空间问题
- [ ] 能回答 80% 以上的面试题
