# Day 152: CI 中构建和推送镜像

> 📅 日期：2026-05-03
> 📖 学习主题：Docker buildx、多架构构建、镜像标签策略、缓存优化、BuildKit、镜像扫描 Trivy、Registry 推送
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 150（Jenkins）、Day 151（构建工具集成）

## 🎯 学习目标

- 理解 Docker BuildKit 架构与 buildx 构建流程
- 掌握多架构镜像构建（amd64/arm64/armv7）
- 精通镜像标签策略（语义化版本、Git SHA、分支标签）
- 能够优化 CI 中的镜像构建缓存
- 掌握 Trivy 镜像安全扫描与策略集成
- 理解 Registry 推送流程与认证机制
- 能够设计端到端的 CI 镜像构建流水线

---

## 📖 核心知识点

### 1. Docker BuildKit 与 buildx

#### 1.1 BuildKit 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Docker BuildKit 架构                               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Client (docker buildx)                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ Dockerfile   │  │ Build Context│  │ Build Args   │      │   │
│  │  │ 解析         │  │ 传输         │  │ 传递         │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    BuildKit Daemon                           │   │
│  │                                                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ LLB Graph    │  │ Solver       │  │ Snapshotter   │      │   │
│  │  │ (构建图)     │  │ (执行器)     │  │ (快照管理)    │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  │                                                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ Cache Manager│  │ Exporter     │  │ Op Registry   │      │   │
│  │  │ (缓存管理)   │  │ (导出器)     │  │ (操作注册)    │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Output Targets                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │ Registry │  │ Local    │  │ Tarball  │  │ OCI Dir  │   │   │
│  │  │ (远程)   │  │ (本地)   │  │ (压缩包) │  │ (目录)   │   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

BuildKit 是 Docker 的下一代构建引擎，相比传统构建有以下核心优势：

| 特性 | 传统 Docker Build | BuildKit |
|------|-------------------|----------|
| 并行构建 | 不支持，顺序执行 | 自动分析依赖图并行执行 |
| 缓存机制 | 基于层的简单缓存 | 内联缓存 + 注册表缓存 + 本地缓存 |
| 安全性 | root 构建，secret 不安全 | 无 root 构建，原生 secret mount |
| 多架构 | 需要手动交叉编译 | 原生多平台支持 |
| 导出目标 | 仅本地镜像 | 镜像/tarball/本地目录/OCI |
| 构建前端 | 仅 Dockerfile | 支持 Dockerfile/HCL/Bazel |
| 进度显示 | 简单输出 | 交互式进度条 |

**LLB（Low-Level Build）图：** BuildKit 将 Dockerfile 解析为一个有向无环图（DAG），每个节点是一个操作（Op），包括源操作、执行操作和复制操作。Solver 分析依赖关系，无依赖的节点自动并行执行。

#### 1.2 buildx 基础使用

```bash
# ============ buildx 安装与配置 ============

# 检查 buildx 是否可用（Docker Desktop 默认包含）
docker buildx version

# 创建 buildx builder 实例（支持多架构）
docker buildx create \
  --name multiarch-builder \
  --driver docker-container \
  --bootstrap \
  --use

# 查看 builder 信息
docker buildx inspect --bootstrap

# 查看所有 builder
docker buildx ls

# 查看支持的平台
docker buildx inspect --bootstrap | grep Platforms

# ============ 基础构建命令 ============

# 简单构建（加载到本地 Docker）
docker buildx build -t myapp:latest --load .

# 构建并推送到 Registry
docker buildx build \
  -t registry.example.com/myapp:v1.0.0 \
  --push .

# 指定平台构建
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t registry.example.com/myapp:v1.0.0 \
  --push .

# 使用构建参数
docker buildx build \
  --build-arg VERSION=1.0.0 \
  --build-arg COMMIT_SHA=$(git rev-parse HEAD) \
  -t myapp:v1.0.0 .

# 指定 Dockerfile
docker buildx build \
  -f docker/Dockerfile.prod \
  -t myapp:prod .

# 设置构建上下文大小限制
docker buildx build \
  --ulimit nofile=65536:65536 \
  -t myapp:latest .
```

#### 1.3 Builder Driver 对比

```
┌─────────────────────────────────────────────────────────────────────┐
│                    buildx Builder Driver 对比                        │
│                                                                     │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐     │
│  │   Driver     │  docker      │docker-       │ remote       │     │
│  │              │              │container     │              │     │
│  ├──────────────┼──────────────┼──────────────┼──────────────┤     │
│  │ 构建隔离     │ 共享 Docker  │ 独立容器     │ 独立节点     │     │
│  │ 多架构       │ 仅本地架构   │ 全平台支持   │ 全平台支持   │     │
│  │ 缓存         │ 本地层缓存   │ 独立缓存卷   │ 远程缓存     │     │
│  │ 速度         │ 最快         │ 较快         │ 网络依赖     │     │
│  │ 适用场景     │ 本地开发     │ CI/CD        │ 分布式构建   │     │
│  └──────────────┴──────────────┴──────────────┴──────────────┘     │
│                                                                     │
│  推荐：                                                              │
│  - 本地开发：docker driver（默认）                                  │
│  - CI/CD：docker-container driver（推荐）                           │
│  - 大规模构建：remote driver（BuildKit 集群）                       │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.4 Dockerfile 最佳实践

```dockerfile
# ============ 阶段 1: 依赖安装阶段 ============
# 使用精确版本标签，不使用 latest
FROM golang:1.22.2-alpine3.19 AS deps

# 安装构建依赖（单独一层，利用缓存）
RUN apk add --no-cache \
    git \
    ca-certificates \
    tzdata \
    && update-ca-certificates

# 设置工作目录
WORKDIR /build

# 先复制依赖文件（利用缓存：依赖不变时跳过此层）
COPY go.mod go.sum ./
RUN go mod download && go mod verify

# ============ 阶段 2: 编译阶段 ============
FROM deps AS builder

# 复制全部源代码
COPY . .

# 构建参数
ARG VERSION=dev
ARG COMMIT_SHA=unknown
ARG BUILD_TIME=unknown

# 编译（静态链接，无 CGO，减小二进制大小）
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build \
    -ldflags="\
      -w -s \
      -X main.version=${VERSION} \
      -X main.commit=${COMMIT_SHA} \
      -X main.buildTime=${BUILD_TIME}" \
    -trimpath \
    -o /app/server \
    ./cmd/server

# ============ 阶段 3: 运行阶段 ============
# 使用 scratch（最小镜像，仅包含二进制文件）
FROM scratch

# 从构建阶段复制必要文件
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /app/server /server

# 使用非 root 用户运行
USER 65534:65534

# 健康检查
# HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
#   CMD ["/server", "-health-check"]

# 暴露端口（文档用途）
EXPOSE 8080

# 设置入口点
ENTRYPOINT ["/server"]
```

**Dockerfile 优化原则清单：**

```
┌─────────────────────────────────────────────────────────────────┐
│              Dockerfile 优化检查清单                              │
│                                                                 │
│  1. 多阶段构建（Multi-stage Build）                              │
│     - 构建阶段包含编译工具和源代码                               │
│     - 运行阶段只包含运行时二进制                                 │
│     - 最终镜像使用 scratch 或 distroless                        │
│                                                                 │
│  2. 层缓存优化（Layer Cache）                                   │
│     - 不常变的指令放在 Dockerfile 前面                          │
│     - COPY 依赖文件先于 COPY 源代码                             │
│     - 合并相关 RUN 指令减少层数                                 │
│     - 使用 --mount=type=cache 持久化包管理缓存                  │
│                                                                 │
│  3. 镜像体积最小化                                              │
│     - 使用 alpine 或 distroless 基础镜像                        │
│     - 使用 scratch 最终镜像（Go/Rust 静态编译）                │
│     - 清理包管理器缓存（--no-cache）                           │
│     - 使用 .dockerignore 排除无关文件                           │
│     - 使用 -w -s ldflags 去除调试信息                           │
│                                                                 │
│  4. 安全加固                                                    │
│     - 不以 root 用户运行（USER 指令）                           │
│     - 固定基础镜像版本（不使用 latest）                         │
│     - 使用 COPY 而非 ADD（除非需要解压）                       │
│     - 不在镜像中存储 secrets                                    │
│     - 使用 BuildKit --secret mount 传递敏感信息                 │
│                                                                 │
│  5. 可观测性                                                    │
│     - 添加 LABEL 元数据（版本、维护者、描述）                  │
│     - 设置 HEALTHCHECK                                          │
│     - 暴露必要的端口文档                                        │
│     - 添加构建参数（VERSION、COMMIT_SHA）                       │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. 多架构构建

#### 2.1 多架构构建原理

```
┌─────────────────────────────────────────────────────────────────────┐
│                    多架构镜像构建流程                                  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Dockerfile (统一)                               │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Buildx Builder (docker-container)               │   │
│  │                                                             │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │   │
│  │  │ QEMU Emulator │  │ Native Build  │  │ Cross-compile │   │   │
│  │  │ (模拟构建)    │  │ (原生构建)    │  │ (交叉编译)    │   │   │
│  │  │               │  │               │  │               │   │   │
│  │  │ 通用但较慢    │  │ 最快但需硬件  │  │ 语言特定支持  │   │   │
│  │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘   │   │
│  └──────────┼──────────────────┼──────────────────┼────────────┘   │
│             │                  │                  │                 │
│             ▼                  ▼                  ▼                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ linux/amd64  │  │ linux/arm64  │  │ linux/arm/v7 │             │
│  │ 镜像         │  │ 镜像         │  │ 镜像         │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                 │                      │
│         ▼                 ▼                 ▼                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Manifest List (清单列表)                        │   │
│  │  {                                                          │   │
│  │    "schemaVersion": 2,                                      │   │
│  │    "mediaType": "application/vnd.oci.image.index.v1+json",  │   │
│  │    "manifests": [                                           │   │
│  │      {"digest": "sha256:abc...", "platform": {"architecture": "amd64", "os": "linux"}}, │
│  │      {"digest": "sha256:def...", "platform": {"architecture": "arm64", "os": "linux"}}, │
│  │      {"digest": "sha256:ghi...", "platform": {"architecture": "arm", "variant": "v7"}} │
│  │    ]                                                        │   │
│  │  }                                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  使用者只需 docker pull myapp:v1.0                                  │
│  Docker 自动拉取匹配当前架构的镜像层                                 │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.2 QEMU 模拟构建

```bash
# ============ QEMU 用户态模拟器配置 ============

# 注册 QEMU 用户态模拟器（一次性操作）
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# 验证 QEMU 注册
ls /proc/sys/fs/binfmt_misc/qemu-*

# 使用 QEMU 构建多架构镜像
docker buildx build \
  --platform linux/amd64,linux/arm64,linux/arm/v7 \
  -t myregistry/myapp:v1.0 \
  --push .

# 注意事项：
# 1. QEMU 模拟构建比原生构建慢 5-20 倍
# 2. 某些系统调用可能不完全兼容
# 3. 编译密集型任务（如 Go/Java）特别慢
# 4. 推荐仅在必要时使用，优先考虑交叉编译
```

#### 2.3 交叉编译（推荐方案）

```dockerfile
# ===== Go 项目交叉编译 Dockerfile =====
# 使用 --platform=$BUILDPLATFORM 确保构建阶段在宿主架构运行
FROM --platform=$BUILDPLATFORM golang:1.22-alpine AS builder

# TARGETOS 和 TARGETARCH 由 buildx 自动注入
ARG TARGETOS
ARG TARGETARCH
ARG VERSION
ARG COMMIT_SHA

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .

# 交叉编译：在宿主架构上为目标架构编译
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    go build -ldflags="-w -s -X main.version=${VERSION}" \
    -o /server ./cmd/server

# 运行阶段使用目标平台
FROM scratch
COPY --from=builder /server /server
ENTRYPOINT ["/server"]
```

```yaml
# GitHub Actions 多架构构建
name: Multi-Arch Build

on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
        with:
          platforms: linux/amd64,linux/arm64

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=sha-

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            VERSION=${{ github.ref_name }}
            COMMIT_SHA=${{ github.sha }}
```

#### 2.4 GitLab CI 多架构构建配置

```yaml
# .gitlab-ci.yml
variables:
  DOCKER_BUILDKIT: 1
  DOCKER_CLI_EXPERIMENTAL: enabled
  BUILDX_VERSION: v0.12.1

build-multi-arch:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  before_script:
    - apk add --no-cache curl
    - mkdir -p ~/.docker/cli-plugins
    - curl -SL "https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}/buildx-${BUILDX_VERSION}.linux-amd64"
      -o ~/.docker/cli-plugins/docker-buildx
    - chmod +x ~/.docker/cli-plugins/docker-buildx
    - docker buildx create --use --driver docker-container
    - docker login -u "$CI_REGISTRY_USER" -p "$CI_REGISTRY_PASSWORD" "$CI_REGISTRY"
  script:
    - |
      docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --build-arg VERSION="$CI_COMMIT_TAG" \
        --build-arg COMMIT_SHA="$CI_COMMIT_SHA" \
        --cache-from "type=registry,ref=$CI_REGISTRY_IMAGE:buildcache" \
        --cache-to "type=registry,ref=$CI_REGISTRY_IMAGE:buildcache,mode=max" \
        --tag "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA" \
        --tag "$CI_REGISTRY_IMAGE:$CI_COMMIT_REF_SLUG" \
        --push .
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_COMMIT_TAG
```

---

### 3. 镜像标签策略

#### 3.1 标签策略全景

```
┌─────────────────────────────────────────────────────────────────────┐
│                    镜像标签策略                                       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  语义化版本标签（SemVer）                                     │   │
│  │  myapp:v1.2.3       → 精确版本，用于生产部署（不可变）       │   │
│  │  myapp:v1.2         → 次版本标签，兼容性更新（可变）         │   │
│  │  myapp:v1           → 主版本标签，大版本系列（可变）         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Git 关联标签                                                │   │
│  │  myapp:sha-abc1234   → Git commit SHA（精确回溯，不可变）    │   │
│  │  myapp:main-abc1234  → 分支+SHA（区分分支，不可变）          │   │
│  │  myapp:pr-123        → PR 编号（临时镜像，用于测试）         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  环境标签                                                    │   │
│  │  myapp:latest         → 最新稳定版（仅开发/测试使用）        │   │
│  │  myapp:stable         → 稳定版标签（手动维护）               │   │
│  │  myapp:canary         → 金丝雀版本（新功能测试）             │   │
│  │  myapp:dev            → 开发版本                             │   │
│  │  myapp:rc             → 候选发布版本                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  构建元数据标签                                               │   │
│  │  myapp:build-20260503     → 构建日期                         │   │
│  │  myapp:build-1234         → CI 构建编号                      │   │
│  │  myapp:sha256-abc...      → 内容寻址 digest（完全不可变）    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.2 标签不可变性策略

```
┌─────────────────────────────────────────────────────────────────────┐
│                    标签不可变性策略                                    │
│                                                                     │
│  不可变标签（Immutable Tags）—— 一旦推送，永远不能覆盖：            │
│  ├── v1.2.3          → 精确语义化版本                               │
│  ├── sha-abc1234     → Git SHA，永远指向同一构建                    │
│  ├── build-1234      → CI 构建编号，唯一标识                        │
│  └── sha256:abc...   → 内容 digest，物理层面不可变                  │
│                                                                     │
│  可变标签（Mutable Tags）—— 可以更新指向新的镜像：                  │
│  ├── latest          → 最新稳定版，每次 main 合并更新               │
│  ├── stable          → 最新稳定版，手动维护                        │
│  ├── dev             → 开发分支最新版                              │
│  ├── v1.2            → 次版本系列最新补丁                          │
│  └── v1              → 主版本系列最新版本                          │
│                                                                     │
│  Registry 级别的不可变标签配置：                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Harbor:  项目 → 配置 → 标签保留 → 不可变标签规则            │  │
│  │  ECR:     Lifecycle Policy → 阻止覆盖特定前缀标签            │  │
│  │  GCR:     使用 digest 引用替代标签                           │  │
│  │  ACR:     Portal → Repositories → Lock tag                   │  │
│  │  GHCR:    通过 API 设置 immutability                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  生产部署黄金法则：                                                  │
│  使用 digest（sha256:abc123...）引用镜像，而非标签                  │
│  部署清单中同时记录标签和 digest 以便追溯                            │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.3 docker/metadata-action 标签规则

```yaml
# 完整的标签策略配置
name: Image Tag Strategy

on:
  push:
    branches: [main, develop, 'release/**']
    tags: ['v*']
  pull_request:
    branches: [main]

jobs:
  generate-tags:
    runs-on: ubuntu-latest
    steps:
      - name: Generate metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: |
            ghcr.io/${{ github.repository }}
            registry.example.com/${{ github.repository }}
          tags: |
            # === 语义化版本（从 Git tag 触发）===
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}

            # === Git SHA（所有事件）===
            type=sha,prefix=sha-,format=short

            # === 分支名（push 事件）===
            type=ref,event=branch

            # === PR 编号（PR 事件）===
            type=ref,event=pr

            # === latest 标签（仅 main 分支）===
            type=raw,value=latest,enable=${{ github.ref == format('refs/heads/{0}', 'main') }}

            # === 构建时间戳（定时构建）===
            type=schedule,pattern=build-{{date 'YYYYMMDD-HHmmss'}}

            # === 环境标签 ===
            type=raw,value=dev,enable=${{ github.ref == 'refs/heads/develop' }}
            type=raw,value=stable,enable=${{ startsWith(github.ref, 'refs/tags/v') && !contains(github.ref, '-') }}

      - name: Show generated tags
        run: |
          echo "Tags: ${{ steps.meta.outputs.tags }}"
          echo "Labels: ${{ steps.meta.outputs.labels }}"
```

#### 3.4 标签策略决策树

```
┌─────────────────────────────────────────────────────────────────┐
│              标签策略决策树                                       │
│                                                                 │
│  事件类型？                                                      │
│  ├── Push to main                                               │
│  │   ├── 生成: latest, sha-abc1234, main                        │
│  │   └── 用途: 开发/测试环境自动部署                             │
│  │                                                              │
│  ├── Push to release/* 分支                                     │
│  │   ├── 生成: release-20260503, sha-abc1234                    │
│  │   └── 用途: 预发布环境部署                                    │
│  │                                                              │
│  ├── Push tag v1.2.3                                            │
│  │   ├── 生成: v1.2.3, v1.2, v1, sha-abc1234, stable           │
│  │   └── 用途: 生产环境部署                                      │
│  │                                                              │
│  ├── Pull Request                                               │
│  │   ├── 生成: pr-123, sha-abc1234                              │
│  │   └── 用途: PR 预览环境，合并后清理                           │
│  │                                                              │
│  └── 定时构建                                                   │
│      ├── 生成: build-20260503-143022                            │
│      └── 用途: 定期重建，修补基础镜像漏洞                        │
└─────────────────────────────────────────────────────────────────┘
```

---

### 4. 构建缓存优化

#### 4.1 BuildKit 缓存策略对比

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BuildKit 缓存策略                                  │
│                                                                     │
│  1. 内联缓存（Inline Cache）                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  原理：缓存元数据嵌入镜像层中                                │   │
│  │  配置：                                                      │   │
│  │    --cache-to type=inline,mode=max                         │   │
│  │    --cache-from type=registry,ref=...:buildcache           │   │
│  │  优点：简单，无需额外存储                                    │   │
│  │  缺点：只缓存最终镜像的层，中间阶段不缓存                    │   │
│  │  适用：简单构建，缓存需求不高                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  2. 注册表缓存（Registry Cache）                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  原理：缓存作为独立镜像推送到 Registry                       │   │
│  │  配置：                                                      │   │
│  │    --cache-to type=registry,ref=...:buildcache,mode=max    │   │
│  │    --cache-from type=registry,ref=...:buildcache           │   │
│  │  mode=max：缓存所有层（包括中间阶段）—— 推荐                │   │
│  │  mode=min：只缓存最终镜像的层                               │   │
│  │  优点：完整缓存构建图，跨 CI Runner 共享                    │   │
│  │  缺点：占用 Registry 存储空间                               │   │
│  │  适用：CI/CD，多阶段构建                                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  3. GitHub Actions 缓存（GHA Cache）                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  原理：使用 GitHub Actions 内置缓存后端                      │   │
│  │  配置：                                                      │   │
│  │    --cache-to type=gha,mode=max                            │   │
│  │    --cache-from type=gha                                   │   │
│  │  优点：与 CI 深度集成，自动管理生命周期                      │   │
│  │  缺点：仅限 GitHub Actions，缓存限制 10GB                   │   │
│  │  适用：GitHub Actions 项目                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  4. 本地缓存（Local Cache）                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  原理：缓存存储在 CI Runner 本地文件系统                     │   │
│  │  配置：                                                      │   │
│  │    --cache-to type=local,dest=/tmp/.buildx-cache,mode=max  │   │
│  │    --cache-from type=local,src=/tmp/.buildx-cache          │   │
│  │  优点：最快，无需网络传输                                    │   │
│  │  缺点：仅限当前 Runner，需配合 CI 缓存 action              │   │
│  │  适用：自托管 Runner，单 Runner 构建                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  5. Azure Blob Storage / S3 缓存                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  原理：缓存存储在对象存储中                                  │   │
│  │  配置：                                                      │   │
│  │    --cache-to type=azblob,name=cache,container=buildcache  │   │
│  │    --cache-from type=azblob,name=cache,container=buildcache│   │
│  │  优点：跨 CI 平台共享，无大小限制                           │   │
│  │  缺点：需要配置存储凭证                                     │   │
│  │  适用：多 CI 平台，大规模项目                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2 缓存策略选择决策树

```
┌─────────────────────────────────────────────────────────────┐
│              缓存策略选择决策树                                │
│                                                             │
│  CI 平台是什么？                                             │
│  ├── GitHub Actions                                        │
│  │   └── 使用 GHA Cache (type=gha,mode=max)               │
│  │                                                         │
│  ├── GitLab CI                                             │
│  │   ├── 有 Registry？→ Registry Cache (mode=max)         │
│  │   └── 无 Registry？→ Local Cache + CI cache action     │
│  │                                                         │
│  ├── Jenkins                                               │
│  │   ├── 有 Registry？→ Registry Cache                    │
│  │   └── 自托管？→ Local Cache (SSD 推荐)                 │
│  │                                                         │
│  └── 其他 CI                                               │
│      └── 有共享存储？→ S3/Azure Blob Cache                │
│                                                         │
│  构建类型？                                                 │
│  ├── 多阶段构建 → 必须用 mode=max（缓存所有阶段）        │
│  └── 单阶段构建 → mode=min 即可                           │
│                                                             │
│  镜像变更频率？                                             │
│  ├── 高频变更 → Registry Cache + 分层优化                 │
│  └── 低频变更 → Inline Cache 即可                         │
└─────────────────────────────────────────────────────────────┘
```

#### 4.3 完整缓存优化配置

```yaml
# GitHub Actions 完整的缓存优化构建
name: Optimized Build with Cache

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build with multi-source cache
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          # 多源缓存策略：优先使用 GHA 缓存，回退到 Registry 缓存
          cache-from: |
            type=gha
            type=registry,ref=ghcr.io/${{ github.repository }}:buildcache
          cache-to: |
            type=gha,mode=max
            type=registry,ref=ghcr.io/${{ github.repository }}:buildcache,mode=max
```

#### 4.4 Dockerfile 层缓存优化技巧

```dockerfile
# ===== 优化前（每次代码变更都重新下载依赖）=====
FROM node:20-alpine
WORKDIR /app
COPY . .                    # 每次代码变更都触发此层
RUN npm install             # 依赖下载被跳过，因为上层已失效
RUN npm run build
CMD ["node", "dist/index.js"]

# ===== 优化后（依赖层独立缓存）=====
FROM node:20-alpine AS deps
WORKDIR /app
# 1. 先复制依赖声明文件（变化频率低）
COPY package.json package-lock.json ./
# 2. 安装依赖（此层被缓存，直到 lock 文件变化）
RUN npm ci --only=production

FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
# 3. 源代码变化只影响此层和后续层
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./
USER node
CMD ["node", "dist/index.js"]
```

**Go 项目的高级缓存技巧：**

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app

# 使用 BuildKit mount cache 持久化 Go 模块缓存
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -o /server ./cmd/server

FROM scratch
COPY --from=builder /server /server
ENTRYPOINT ["/server"]
```

---

### 5. Trivy 镜像安全扫描

#### 5.1 Trivy 扫描架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Trivy 镜像扫描流程                                 │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │  目标镜像     │                                                  │
│  └──────┬───────┘                                                  │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  1. 镜像解包（Image Unpacking）                               │   │
│  │     - 解析 manifest 和 config JSON                           │   │
│  │     - 逐层提取文件系统                                       │   │
│  │     - 识别基础 OS（Alpine/Debian/Ubuntu/RHEL...）           │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  2. 内容分析（Content Analysis）                              │   │
│  │     ├── OS 包检测（apk, apt, yum, rpm）                     │   │
│  │     ├── 语言依赖检测                                        │   │
│  │     │   ├── Go (go.mod, go.sum)                             │   │
│  │     │   ├── Node.js (package.json, yarn.lock)               │   │
│  │     │   ├── Java (pom.xml, build.gradle)                    │   │
│  │     │   ├── Python (requirements.txt, Pipfile.lock)         │   │
│  │     │   └── Ruby (Gemfile.lock)                             │   │
│  │     ├── IaC 配置扫描                                        │   │
│  │     │   ├── Dockerfile 指令检查                             │   │
│  │     │   ├── Kubernetes manifests                             │   │
│  │     │   ├── Terraform 文件                                   │   │
│  │     │   └── CloudFormation 模板                              │   │
│  │     └── Secret 检测                                          │   │
│  │         ├── AWS Access Key                                   │   │
│  │         ├── GitHub Token                                     │   │
│  │         ├── Private Key 文件                                 │   │
│  │         └── 数据库连接字符串                                  │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  3. 漏洞匹配（Vulnerability Matching）                        │   │
│  │     - 从 NVD/OSV/Alpine/Debian/Ubuntu 数据库获取 CVE        │   │
│  │     - 与检测到的包版本进行精确匹配                           │   │
│  │     - 评估严重程度（CRITICAL/HIGH/MEDIUM/LOW/UNKNOWN）      │   │
│  │     - 检查是否有修复版本                                     │   │
│  └────────────────────────┬────────────────────────────────────┘   │
│                           │                                         │
│                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  4. 报告生成（Report Generation）                             │   │
│  │     ├── Table 格式（终端可读）                               │   │
│  │     ├── JSON 格式（程序解析）                                │   │
│  │     ├── SARIF 格式（GitHub Security 集成）                  │   │
│  │     ├── CycloneDX/SPDX SBOM                                 │   │
│  │     └── HTML 格式（可视化报告）                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.2 Trivy 基础使用

```bash
# ============ 安装 Trivy ============

# 方式 1: 官方脚本安装
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# 方式 2: 包管理器安装
# Ubuntu/Debian
sudo apt-get install trivy

# macOS
brew install trivy

# Docker 运行（无需安装）
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image myapp:latest

# ============ 镜像扫描 ============

# 基础扫描
trivy image myapp:latest

# 只显示 CRITICAL 和 HIGH 级别
trivy image --severity CRITICAL,HIGH myapp:latest

# JSON 格式输出
trivy image --format json --output result.json myapp:latest

# 设置退出码（发现漏洞时返回非零）
trivy image --exit-code 1 --severity CRITICAL myapp:latest

# 只显示已修复的漏洞
trivy image --ignore-unfixed myapp:latest

# 扫描远程镜像（无需本地 pull）
trivy image registry.example.com/myapp:v1.0

# ============ 其他扫描类型 ============

# 扫描 Dockerfile 配置
trivy config Dockerfile

# 扫描 Kubernetes manifests
trivy config ./k8s/

# 扫描 Terraform 文件
trivy config ./terraform/

# 扫描文件系统（代码中的漏洞）
trivy fs --security-checks vuln,secret .

# 扫描 SBOM
trivy sbom --format cyclonedx sbom.json

# 生成 SBOM
trivy image --format spdx-json --output sbom.json myapp:latest
```

#### 5.3 CI 中集成 Trivy 扫描

```yaml
# GitHub Actions 完整的 Trivy 集成
name: Image Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-and-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build image for scanning
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: myapp:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # ===== 扫描 1: CRITICAL 漏洞门控 =====
      - name: Scan CRITICAL vulnerabilities (gate)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'table'
          severity: 'CRITICAL'
          exit-code: '1'
          ignore-unfixed: true

      # ===== 扫描 2: 全量扫描报告 =====
      - name: Scan all vulnerabilities (report)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH,MEDIUM'

      # ===== 上传到 GitHub Security =====
      - name: Upload scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      # ===== 生成 SBOM =====
      - name: Generate SBOM
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: 'spdx-json'
          output: 'sbom.spdx.json'

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json
```

#### 5.4 Trivy 配置与忽略规则

```yaml
# trivy.yaml - 项目级 Trivy 配置
severity: CRITICAL,HIGH,MEDIUM
format: table
output: trivy-report.txt

scan:
  security-checks: vuln,secret,misconfig
  skip-dirs:
    - test/
    - docs/
    - node_modules/
    - vendor/
  skip-files:
    - "*.test.js"
    - "test_*.py"

db:
  # 自建漏洞数据库（离线环境）
  repository: harbor.example.com/security/trivy-db
  skip-update: false

image:
  platform: linux/amd64
```

```bash
# .trivyignore - 忽略特定漏洞
# 格式：CVE-ID [可选：过期日期]

# 已评估确认无影响的漏洞
CVE-2023-12345
CVE-2023-67890

# 带过期日期的忽略规则（强制定期重新评估）
# Accept: only affects test dependencies, no production impact
CVE-2023-11111 expiry: 2026-12-31

# Accept: requires local access, low risk in container environment
CVE-2023-22222 expiry: 2026-08-31
```

---

### 6. Registry 推送

#### 6.1 主流容器镜像仓库对比

```
┌─────────────────────────────────────────────────────────────────────┐
│                    主流容器镜像仓库                                    │
│                                                                     │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐     │
│  │   Harbor     │   ECR        │   GCR/AR     │   ACR        │     │
│  │   (自建)     │  (AWS)       │  (GCP)       │  (Azure)     │     │
│  ├──────────────┼──────────────┼──────────────┼──────────────┤     │
│  │ 开源免费     │ 全托管       │ 全托管       │ 全托管       │     │
│  │ 本地/私有云  │ AWS 原生集成 │ GCP 原生集成 │ Azure 原生   │     │
│  │ 漏洞扫描     │ IAM 认证     │ IAM 认证     │ AAD 认证     │     │
│  │ 镜像签名     │ 生命周期策略 │ 自动清理     │ 内容信任     │     │
│  │ 镜像复制     │ 跨区域复制   │ 跨区域复制   │ 跨区域复制   │     │
│  │ Webhook      │ EventBridge  │ Pub/Sub      │ Event Grid   │     │
│  │ 配额管理     │ 按量计费     │ 按量计费     │ 按量计费     │     │
│  └──────────────┴──────────────┴──────────────┴──────────────┘     │
│                                                                     │
│  GitHub Container Registry (ghcr.io):                               │
│  - GitHub 原生集成，公开仓库免费                                     │
│  - 权限与 GitHub 仓库/组织联动                                      │
│  - 支持 OCI 标准                                                    │
│                                                                     │
│  GitLab Container Registry:                                         │
│  - GitLab CI/CD 原生集成                                            │
│  - 项目/组/实例三级 Registry                                        │
│  - 标签清理策略支持正则匹配                                         │
└─────────────────────────────────────────────────────────────────────┘
```

#### 6.2 Registry 认证配置

```bash
# ===== Docker Hub =====
# 使用 Personal Access Token（推荐，不要用密码）
echo $DOCKERHUB_TOKEN | docker login -u $DOCKERHUB_USER --password-stdin

# ===== GitHub Container Registry =====
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin

# ===== AWS ECR =====
# 获取临时凭证（12小时有效）
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.us-east-1.amazonaws.com

# 使用 ecr-login credential helper（推荐）
# 安装: go install github.com/awslabs/amazon-ecr-credential-helper/ecr-login/cli/docker-credential-ecr-login@latest
# ~/.docker/config.json:
# {"credHelpers":{"123456789.dkr.ecr.us-east-1.amazonaws.com":"ecr-login"}}

# ===== Google Artifact Registry =====
gcloud auth configure-docker us-docker.pkg.dev --quiet

# ===== Azure ACR =====
az acr login --name myregistry

# ===== Harbor =====
docker login harbor.example.com -u robot$ci-deploy --password-stdin <<< "$HARBOR_TOKEN"

# ===== 使用 Docker credential store（更安全）=====
# ~/.docker/config.json
{
  "credsStore": "desktop"  # macOS Keychain / Windows Credential Manager
}
```

---

### 7. SRE 实战案例

#### 7.1 案例：生产环境镜像构建流水线优化

**背景：** 某公司的 Go 微服务镜像构建时间为 12 分钟，严重影响 CI/CD 效率。

**问题分析：**
```
原始构建流程耗时分解：
  代码检出：     30s
  依赖下载：     3min  （每次都重新下载）
  代码编译：     5min  （QEMU 模拟 arm64）
  镜像推送：     2min  （无缓存，全量推送）
  Trivy 扫描：   1min  （每次都下载漏洞库）
  总计：         ~12min
```

**优化方案：**

```dockerfile
# ===== 优化后的 Dockerfile =====
# 使用 --platform=$BUILDPLATFORM 实现交叉编译
FROM --platform=$BUILDPLATFORM golang:1.22-alpine AS builder

ARG TARGETOS TARGETARCH

WORKDIR /app

# 使用 mount cache 持久化 Go 模块和构建缓存
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    go build -ldflags="-w -s" -o /server ./cmd/server

FROM scratch
COPY --from=builder /server /server
ENTRYPOINT ["/server"]
```

```yaml
# 优化后的 CI 配置
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    context: .
    platforms: linux/amd64,linux/arm64
    push: true
    tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
    cache-from: type=gha,scope=$GITHUB_REF_NAME
    cache-to: type=gha,mode=max,scope=$GITHUB_REF_NAME
```

**优化结果：**
```
优化后构建耗时分解：
  代码检出：     15s   （浅克隆）
  依赖下载：     10s   （mount cache 命中）
  代码编译：     45s   （交叉编译替代 QEMU）
  镜像推送：     30s   （仅推送变化的层）
  Trivy 扫描：   20s   （本地缓存漏洞库）
  总计：         ~2min （提速 6 倍）
```

#### 7.2 案例：镜像安全扫描门控策略

**背景：** 某金融公司要求所有部署的镜像必须通过安全扫描。

**策略设计：**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    镜像安全门控策略                                    │
│                                                                     │
│  阶段 1: 开发阶段（信息性扫描）                                      │
│  ├── 扫描所有漏洞级别（CRITICAL/HIGH/MEDIUM/LOW）                   │
│  ├── 结果仅作参考，不阻塞 CI                                        │
│  └── 上传到 GitHub Security 面板                                    │
│                                                                     │
│  阶段 2: PR 合并（强制门控）                                         │
│  ├── 扫描 CRITICAL + HIGH 级别漏洞                                  │
│  ├── 发现 CRITICAL 漏洞 → 阻塞合并                                  │
│  ├── 发现 HIGH 漏洞 → 要求填写豁免申请                              │
│  └── 忽略已有修复版本的漏洞（--ignore-unfixed）                     │
│                                                                     │
│  阶段 3: 生产部署（最严格门控）                                      │
│  ├── 扫描 CRITICAL 级别漏洞                                         │
│  ├── 零容忍 CRITICAL 漏洞                                           │
│  ├── 验证镜像签名（Cosign）                                         │
│  └── 检查 SBOM 完整性                                               │
│                                                                     │
│  阶段 4: 持续监控（运行时扫描）                                      │
│  ├── 每日扫描已部署镜像                                             │
│  ├── 新 CVE 公告时触发告警                                          │
│  └── 自动触发重建（修补漏洞）                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 💻 实战练习

### 练习 1：构建多架构镜像并推送到 Registry

**目标：** 创建一个 Go Web 应用的多架构镜像，支持 amd64 和 arm64

```bash
# 步骤 1: 创建项目结构
mkdir -p /tmp/multiarch-demo && cd /tmp/multiarch-demo

# 步骤 2: 创建 Go 应用
cat > main.go << 'EOF'
package main

import (
    "fmt"
    "net/http"
    "os"
    "runtime"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        hostname, _ := os.Hostname()
        fmt.Fprintf(w, "Hello from %s/%s! Hostname: %s\n",
            runtime.GOOS, runtime.GOARCH, hostname)
    })
    http.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
    })
    fmt.Printf("Server starting on :8080 (%s/%s)\n", runtime.GOOS, runtime.GOARCH)
    http.ListenAndServe(":8080", nil)
}
EOF

# 步骤 3: 初始化 Go 模块
go mod init multiarch-demo

# 步骤 4: 创建优化的多架构 Dockerfile
cat > Dockerfile << 'EOF'
FROM --platform=$BUILDPLATFORM golang:1.22-alpine AS builder
ARG TARGETOS TARGETARCH
WORKDIR /app
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH \
    go build -ldflags="-w -s" -o server .

FROM scratch
COPY --from=builder /app/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
EOF

# 步骤 5: 创建 buildx builder
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap

# 步骤 6: 构建多架构镜像（本地测试，不推送）
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t multiarch-demo:v1.0.0 \
  --load .

# 注意: --load 只能加载单架构，多架构需要 --push
# 步骤 7: 构建并推送多架构镜像
# 替换为你的 Registry 地址
REGISTRY="your-registry.com"
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ${REGISTRY}/multiarch-demo:v1.0.0 \
  -t ${REGISTRY}/multiarch-demo:latest \
  --push .

# 步骤 8: 验证多架构镜像
docker buildx imagetools inspect ${REGISTRY}/multiarch-demo:v1.0.0
```

**预期输出：** `imagetools inspect` 应显示 Manifest List 包含 linux/amd64 和 linux/arm64 两个平台。

### 练习 2：配置 Trivy 镜像扫描流水线

**目标：** 创建完整的镜像扫描流水线，包含漏洞门控和 SBOM 生成

```yaml
# 创建 .github/workflows/security-scan.yml
name: Security Scan Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-and-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - name: Build image for scanning
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: myapp:test
          cache-from: type=gha
          cache-to: type=gha,mode=max

      # 门控扫描：发现 CRITICAL 漏洞则失败
      - name: Scan CRITICAL vulnerabilities (gate)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:test
          format: 'table'
          severity: 'CRITICAL'
          exit-code: '1'
          ignore-unfixed: true

      # 全量扫描报告
      - name: Full vulnerability report
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:test
          format: 'sarif'
          output: 'trivy.sarif'
          severity: 'CRITICAL,HIGH,MEDIUM'

      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy.sarif'

      # 生成 SBOM
      - name: Generate SBOM
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:test
          format: 'spdx-json'
          output: 'sbom.spdx.json'

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json
```

### 练习 3：实现完整的镜像标签策略

**目标：** 配置 docker/metadata-action 实现生产级标签策略

```yaml
# 创建 .github/workflows/tag-strategy.yml
name: Tag Strategy Demo

on:
  push:
    branches: [main, develop, 'release/**']
    tags: ['v*']
  pull_request:
    branches: [main]

jobs:
  generate-tags:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=sha,prefix=sha-,format=short
            type=ref,event=branch
            type=ref,event=pr
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
            type=raw,value=dev,enable=${{ github.ref == 'refs/heads/develop' }}

      - name: Show tags
        run: |
          echo "=== Generated Tags ==="
          echo "${{ steps.meta.outputs.tags }}"
          echo ""
          echo "=== Generated Labels ==="
          echo "${{ steps.meta.outputs.labels }}"
```

**验证步骤：**
1. 推送到 main 分支 → 检查是否生成 `latest` + `sha-xxx` + `main` 标签
2. 推送 tag `v1.2.3` → 检查是否生成 `v1.2.3` + `v1.2` + `v1` + `sha-xxx`
3. 创建 PR → 检查是否生成 `pr-xxx` + `sha-xxx`
4. 推送到 develop → 检查是否生成 `dev` + `sha-xxx`

---

## 🎯 面试题精选

### 面试题 1：解释 Docker BuildKit 与传统 Docker Build 的区别

**答案：**

BuildKit 是 Docker 的下一代构建引擎（Docker 23.0+ 默认启用），核心改进：

1. **并行构建**：分析 Dockerfile 指令依赖图，无依赖步骤自动并行执行
2. **高效缓存**：支持内联缓存、注册表缓存、GHA 缓存等多种策略，支持 `--mount=type=cache` 持久化构建缓存
3. **安全性**：原生 `--mount=type=secret` 安全传递 secrets，支持无 root 构建
4. **多架构原生支持**：通过 buildx + QEMU/交叉编译实现多平台构建
5. **输出灵活性**：支持输出到镜像、tarball、本地目录、OCI 格式
6. **构建前端可扩展**：支持 Dockerfile、HCL、Bazel 等多种前端

### 面试题 2：如何优化 CI 中的 Docker 构建速度？给出至少 5 种方法

**答案：**

1. **Dockerfile 层缓存优化**：不常变的指令放前面，COPY 依赖文件先于 COPY 源代码
2. **多阶段构建**：减少最终镜像大小，利用中间阶段缓存
3. **BuildKit 远程缓存**：使用 `--cache-from type=gha` 或 `type=registry` 跨 CI Runner 共享缓存
4. **交叉编译替代 QEMU**：Go/Rust 项目使用 `GOOS/GOARCH` 交叉编译，比 QEMU 模拟快 5-20 倍
5. **构建上下文优化**：`.dockerignore` 排除无关文件，减少上下文传输量
6. **使用 `--mount=type=cache`**：持久化包管理器缓存（Go modules、npm、pip）
7. **自托管 Runner**：预装基础镜像和构建工具，减少环境准备时间

### 面试题 3：什么是镜像的多架构构建？Manifest List 的作用是什么？

**答案：**

多架构构建是指从同一个 Dockerfile 为多个 CPU 架构（amd64/arm64/armv7 等）构建镜像。

**Manifest List** 是一个索引文件，包含多个架构特定镜像的 digest 和平台信息。当用户 `docker pull myapp:v1` 时，Docker 客户端根据当前机器的架构自动选择正确的镜像。

实现方式：
- **QEMU 模拟**：通过用户态模拟器在 x86 机器上构建 arm 镜像（通用但慢）
- **交叉编译**：在 x86 上为 arm 架构编译二进制（Go/Rust 推荐，最快）
- **原生构建**：在 arm 硬件上构建 arm 镜像（最快但需要硬件）

### 面试题 4：如何设计生产级的镜像标签策略？

**答案：**

生产级标签策略应包含：

1. **不可变标签**用于精确部署：`v1.2.3`、`sha-abc1234`、`sha256:digest`
2. **可变标签**用于方便引用：`latest`、`stable`、`v1.2`
3. **环境标签**用于区分用途：`dev`、`canary`、`rc`
4. **构建元数据**用于追溯：`build-20260503`、`ci-1234`

最佳实践：
- 生产部署使用 digest（`sha256:abc...`）引用而非标签
- 不可变标签一旦推送永远不能覆盖
- 使用 CI 自动从 Git tag 生成语义化镜像标签
- Registry 级别配置标签不可变性策略

### 面试题 5：Trivy 扫描的原理是什么？如何在 CI 中合理集成？

**答案：**

**原理：** Trivy 解包镜像层，识别 OS 包和语言依赖，与漏洞数据库（NVD/OSV）匹配 CVE，输出报告。

**CI 集成策略：**
- **PR 阶段**：扫描 CRITICAL + HIGH，阻塞合并
- **构建阶段**：扫描所有级别，生成 SARIF 报告上传 GitHub Security
- **部署前**：扫描 CRITICAL 漏洞，零容忍
- **运行时**：每日扫描已部署镜像，新 CVE 触发告警

关键配置：`exit-code: '1'` 让发现漏洞时 CI 步骤失败，`ignore-unfixed: true` 忽略尚无修复的漏洞。

### 面试题 6：什么是镜像的 SBOM？为什么需要它？

**答案：**

SBOM（Software Bill of Materials）是镜像中所有软件组件的完整清单，包括 OS 包、语言依赖、版本和许可证信息。

**需要的原因：**
1. **供应链安全**：追踪每个组件来源，应对供应链攻击
2. **漏洞响应**：新 CVE 公告时，快速确定哪些镜像受影响
3. **合规要求**：满足安全审计和许可证合规
4. **依赖可见性**：了解镜像完整的依赖树

**格式标准：** SPDX（Linux Foundation）、CycloneDX（OWASP）

### 面试题 7：如何在 CI 中安全地处理 Registry 认证？

**答案：**

1. **使用 CI 平台 Secrets**：GitHub Secrets、GitLab CI Variables，不要硬编码
2. **OIDC 认证（推荐）**：配置 OIDC Provider，CI 直接获取短期 Token，无需存储长期凭证
3. **Credential Helper**：使用 ECR Login、GCR Helper 等工具自动管理凭证
4. **短生命周期 Token**：使用 Robot Account（Harbor）、PAT（Docker Hub），定期轮换
5. **最小权限原则**：CI 服务账号只授予 push 权限，不要给 admin 权限

### 面试题 8：对比 Docker buildx 的三种 Driver（docker、docker-container、remote）

**答案：**

| 特性 | docker | docker-container | remote |
|------|--------|-------------------|--------|
| 隔离性 | 共享 Docker daemon | 独立容器 | 独立节点 |
| 多架构 | 仅本地架构 | 全平台支持 | 全平台支持 |
| 缓存 | 本地层缓存 | 独立缓存卷 | 远程缓存 |
| 速度 | 最快（无额外开销） | 较快 | 取决于网络 |
| 适用 | 本地开发 | CI/CD（推荐） | 分布式大规模构建 |

CI/CD 环境推荐 `docker-container` driver，支持多架构和完整缓存功能。

---

## 📚 深入阅读

1. **Docker BuildKit 官方文档** - https://docs.docker.com/build/buildkit/
2. **Docker buildx 参考** - https://docs.docker.com/engine/reference/commandline/buildx/
3. **Trivy 官方文档** - https://aquasecurity.github.io/trivy/
4. **Cosign 镜像签名** - https://github.com/sigstore/cosign
5. **docker/metadata-action** - https://github.com/docker/metadata-action
6. **OCI 镜像规范** - https://github.com/opencontainers/image-spec
7. **SLSA 供应链安全框架** - https://slsa.dev/
8. **NIST SSDF (SP 800-218)** - 安全软件开发框架

---

## ✅ 自检清单

- [ ] 理解 BuildKit 的架构和相比传统构建的优势
- [ ] 能够创建 buildx builder 并构建多架构镜像
- [ ] 掌握 Dockerfile 多阶段构建和层缓存优化
- [ ] 能够设计语义化版本 + Git SHA 的标签策略
- [ ] 理解内联缓存、注册表缓存、GHA 缓存的区别和适用场景
- [ ] 能够在 CI 中集成 Trivy 镜像扫描并配置安全门控
- [ ] 了解 SBOM 生成方法和供应链安全意义
- [ ] 能够配置多种 Registry 的认证和推送
- [ ] 掌握 .dockerignore 和构建上下文优化
- [ ] 能够使用 Cosign 对镜像进行签名验证
- [ ] 理解镜像不可变标签和 digest 引用的重要性
- [ ] 能够设计端到端的 CI 镜像构建推送流水线
