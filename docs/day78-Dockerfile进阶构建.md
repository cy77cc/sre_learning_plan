# Day 78: Dockerfile 进阶构建

> 📅 日期：2026-05-03
> 📖 学习主题：Dockerfile 进阶构建 — 指令详解、多阶段构建、构建缓存优化、ARG vs ENV、.dockerignore、安全扫描
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 76 (Docker 简介与安装), Day 77 (Docker 镜像基础)

---

## 🎯 学习目标

完成 Day 78 的学习后，你应该能够：
- 深入理解每条 Dockerfile 指令的语义和底层行为
- 掌握多阶段构建的原理和最佳实践
- 能够优化 Dockerfile 的构建缓存效率
- 区分 ARG 和 ENV 的使用场景和生命周期
- 编写生产级 Dockerfile，包含安全加固和最小化原则
- 使用 .dockerignore 优化构建上下文

---

## 📖 核心知识点

### 1. Dockerfile 指令详解

#### 1.1 指令总览与分类

```
Dockerfile 指令分类：

  镜像定义指令（影响镜像的元数据和配置）：
  ┌──────────────┬──────────────────────────────────────────────┐
  │ FROM         │ 指定基础镜像（必须是第一条指令）              │
  │ LABEL        │ 添加元数据标签                                │
  │ ENV          │ 设置环境变量（运行时也存在）                  │
  │ ARG          │ 定义构建参数（仅构建时存在）                  │
  │ EXPOSE       │ 声明容器监听的端口（文档性质）                │
  │ VOLUME       │ 声匿名挂载点（文档性质）                      │
  │ WORKDIR      │ 设置工作目录                                  │
  │ USER         │ 设置运行用户                                  │
  │ SHELL        │ 设置默认 shell                                │
  │ ONBUILD      │ 定义触发器指令                                │
  └──────────────┴──────────────────────────────────────────────┘

  文件系统指令（影响镜像的文件内容）：
  ┌──────────────┬──────────────────────────────────────────────┐
  │ COPY         │ 复制文件到镜像（推荐）                        │
  │ ADD          │ 复制文件到镜像（支持 URL 和自动解压 tar）     │
  └──────────────┴──────────────────────────────────────────────┘

  执行指令（在构建过程中运行命令）：
  ┌──────────────┬──────────────────────────────────────────────┐
  │ RUN          │ 执行命令，结果保存为新的镜像层                │
  └──────────────┴──────────────────────────────────────────────┘

  启动指令（定义容器启动时的行为）：
  ┌──────────────┬──────────────────────────────────────────────┐
  │ CMD          │ 设置默认启动命令（可被 docker run 覆盖）      │
  │ ENTRYPOINT   │ 设置入口点（不会被覆盖，CMD 作为参数追加）   │
  │ HEALTHCHECK  │ 定义健康检查命令                              │
  └──────────────┴──────────────────────────────────────────────┘
```

#### 1.2 FROM — 基础镜像选择

```dockerfile
# 基本用法
FROM ubuntu:22.04

# 使用 digest 精确引用（推荐用于生产）
FROM ubuntu@sha256:e4d0e810d54ae10...

# 使用 ARG 动态指定基础镜像
ARG BASE_IMAGE=ubuntu
ARG BASE_TAG=22.04
FROM ${BASE_IMAGE}:${BASE_TAG}

# 多阶段构建中的多个 FROM
FROM golang:1.21 AS builder
# ... 构建阶段
FROM alpine:3.18
# ... 运行阶段

# 使用 scratch（空镜像，用于静态编译的二进制）
FROM scratch
COPY server /server
CMD ["/server"]
```

```
基础镜像选择策略：

┌──────────────┬────────┬──────────────────────────────────────────┐
│ 镜像          │ 大小   │ 适用场景                                 │
├──────────────┼────────┼──────────────────────────────────────────┤
│ ubuntu:22.04 │ ~77MB  │ 需要完整的 Ubuntu 环境                   │
│ debian:slim  │ ~80MB  │ 推荐的通用基础镜像                       │
│ alpine:3.18  │ ~7MB   │ 极简镜像，适合静态编译的应用              │
│ distroless   │ ~2-20MB│ Google 提供，无 shell，最安全             │
│ scratch      │ 0MB    │ 空镜像，适合 Go/Rust 静态编译            │
│ busybox      │ ~1MB   │ 极简工具集，适合简单任务                  │
└──────────────┴────────┴──────────────────────────────────────────┘

选择原则：
1. 优先使用官方镜像
2. 优先使用精简版（slim/alpine）
3. 生产环境考虑使用 distroless
4. 静态二进制使用 scratch
5. 始终指定版本标签，不要用 latest
6. 使用 digest 引用确保不可变性
```

#### 1.3 COPY vs ADD

```dockerfile
# COPY — 推荐使用，行为明确
COPY requirements.txt /app/
COPY src/ /app/src/
COPY --chown=appuser:appuser config/ /app/config/

# ADD — 支持额外功能，但行为复杂
# 1. 自动解压本地 tar 文件
ADD archive.tar.gz /app/

# 2. 支持远程 URL（不推荐，无法利用缓存）
ADD https://example.com/file.tar.gz /tmp/

# 3. 支持 --chmod（BuildKit）
ADD --chmod=755 script.sh /app/
```

```
COPY vs ADD 对比：

┌─────────────────┬──────────────────┬──────────────────────────┐
│ 特性             │ COPY             │ ADD                      │
├─────────────────┼──────────────────┼──────────────────────────┤
│ 复制本地文件     │ 支持             │ 支持                     │
│ 复制远程 URL     │ 不支持           │ 支持（不推荐）           │
│ 自动解压 tar     │ 不支持           │ 支持                     │
│ 透明度          │ 高（行为明确）    │ 低（隐含行为多）         │
│ 缓存效率        │ 高               │ 低（URL 每次重新下载）   │
│ 官方推荐        │ 是               │ 否（除非需要自动解压）   │
└─────────────────┴──────────────────┴──────────────────────────┘

最佳实践：
  - 大多数情况使用 COPY
  - 只在需要自动解压本地 tar 时使用 ADD
  - 永远不要用 ADD 下载远程文件，改用 RUN curl + COPY
```

#### 1.4 RUN — 执行构建命令

```dockerfile
# Shell 格式（默认使用 /bin/sh -c 执行）
RUN apt-get update && apt-get install -y curl

# Exec 格式（直接执行，不经过 shell）
RUN ["/bin/bash", "-c", "echo hello"]

# 合并多个 RUN 减少层数（推荐）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        && rm -rf /var/lib/apt/lists/*

# 使用 heredoc（BuildKit 支持）
RUN <<EOF
apt-get update
apt-get install -y curl
rm -rf /var/lib/apt/lists/*
EOF
```

```
RUN 指令的最佳实践：

1. 合并相关命令减少层数：
   ❌ RUN apt-get update
      RUN apt-get install -y curl
      RUN rm -rf /var/lib/apt/lists/*
   ✅ RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

2. 清理包管理器缓存：
   - apt: rm -rf /var/lib/apt/lists/*
   - yum: yum clean all
   - apk: --no-cache 参数
   - pip: --no-cache-dir 参数
   - npm: npm cache clean --force

3. 使用 --no-install-recommends（apt）减少不必要的依赖

4. Shell 格式 vs Exec 格式：
   - Shell 格式：通过 /bin/sh -c 执行，支持环境变量替换、管道
   - Exec 格式：直接执行，不经过 shell，适合 ENTRYPOINT/CMD
```

#### 1.5 CMD vs ENTRYPOINT 深入解析

```dockerfile
# CMD — 设置默认命令，可被 docker run 参数覆盖
CMD ["nginx", "-g", "daemon off;"]
# docker run myimage              → 启动 nginx
# docker run myimage bash         → 启动 bash（覆盖 CMD）

# ENTRYPOINT — 设置入口点，不会被覆盖
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
# docker run myimage              → nginx -g "daemon off;"
# docker run myimage -t           → nginx -t（CMD 被覆盖，追加为参数）

# Shell 格式的陷阱
CMD nginx -g "daemon off;"
# 实际执行：/bin/sh -c "nginx -g 'daemon off;'"
# 问题：nginx 不是 PID 1，无法接收信号
# 信号发送给 sh，sh 不转发给 nginx

# Exec 格式（推荐）
CMD ["nginx", "-g", "daemon off;"]
# nginx 是 PID 1，可以正确接收信号
```

```
CMD 和 ENTRYPOINT 的组合使用：

┌─────────────────────────────────────────────────────────────────┐
│ 场景               │ ENTRYPOINT     │ CMD                      │
├─────────────────────────────────────────────────────────────────┤
│ 只有 CMD           │ -              │ 默认命令，可被覆盖        │
│ 只有 ENTRYPOINT    │ 固定命令       │ 作为参数追加              │
│ 两者都有           │ 固定命令       │ 默认参数，可被覆盖        │
│ 都没有             │ -              │ 继承基础镜像的设置        │
└─────────────────────────────────────────────────────────────────┘

最佳实践：
  - 使用 ENTRYPOINT 定义容器的主进程
  - 使用 CMD 定义默认参数
  - 始终使用 Exec 格式（JSON 数组）
  - 确保主进程是 PID 1，能正确处理信号

示例：
  ENTRYPOINT ["python"]
  CMD ["app.py"]
  # docker run myimage          → python app.py
  # docker run myimage test.py  → python test.py
```

#### 1.6 ENV vs ARG

```dockerfile
# ENV — 环境变量，构建时和运行时都存在
ENV NODE_ENV=production
ENV APP_HOME=/app
WORKDIR ${APP_HOME}

# ARG — 构建参数，仅构建时存在
ARG VERSION=1.0
ARG BUILD_DATE
RUN echo "Building version ${VERSION} on ${BUILD_DATE}"

# 构建时传入 ARG
# docker build --build-arg VERSION=2.0 --build-arg BUILD_DATE=2026-05-03 .
```

```
ARG vs ENV 详细对比：

┌─────────────────┬──────────────────────┬──────────────────────┐
│ 特性             │ ARG                  │ ENV                  │
├─────────────────┼──────────────────────┼──────────────────────┤
│ 生命周期         │ 仅构建时             │ 构建时 + 运行时      │
│ 设置方式         │ Dockerfile + --build-arg│ Dockerfile + -e     │
│ 运行时可见       │ 否                   │ 是                   │
│ 安全性           │ 较高（不进入镜像）   │ 较低（写入镜像层）   │
│ 缓存影响         │ 值改变会破坏后续缓存 │ 不影响缓存           │
│ 默认值           │ 可选                 │ 必须                 │
│ 作用域           │ 从 ARG 声明到阶段结束│ 从 ENV 声明到镜像结束│
└─────────────────┴──────────────────────┴──────────────────────┘

常见陷阱：
1. ARG 在 FROM 之前声明，可以在 FROM 中使用
   ARG TAG=latest
   FROM nginx:${TAG}
   # 但这个 ARG 在 FROM 之后的阶段中不可用

2. ARG 在 FROM 之后重新声明才能在后续使用
   FROM ubuntu:22.04
   ARG VERSION=1.0  # 必须重新声明

3. ENV 会覆盖同名的 ARG
   ARG MY_VAR=arg_value
   ENV MY_VAR=env_value
   # MY_VAR 的值是 env_value

4. 敏感信息不要用 ARG 或 ENV
   ARG SECRET_KEY=xxx   # 可以通过 docker history 看到
   ENV DB_PASSWORD=xxx  # 写入镜像层，可以被提取
```

#### 1.7 HEALTHCHECK — 健康检查

```dockerfile
# 基本用法
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 禁用基础镜像的健康检查
HEALTHCHECK NONE

# 使用 wget（Alpine 镜像没有 curl）
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8080/health || exit 1

# 使用自定义健康检查脚本
COPY healthcheck.sh /usr/local/bin/
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["healthcheck.sh"]
```

```
HEALTHCHECK 参数说明：

┌──────────────┬────────┬──────────────────────────────────────────┐
│ 参数          │ 默认值 │ 说明                                     │
├──────────────┼────────┼──────────────────────────────────────────┤
│ --interval   │ 30s    │ 检查间隔                                 │
│ --timeout    │ 30s    │ 检查超时时间                             │
│ --start-period│ 0s    │ 容器启动后的宽限期（期间失败不计入重试）│
│ --retries    │ 3      │ 连续失败次数后标记为 unhealthy           │
└──────────────┴────────┴──────────────────────────────────────────┘

健康检查状态：
  starting   → 启动中（在 start-period 内）
  healthy    → 健康（检查通过）
  unhealthy  → 不健康（连续 retries 次失败）

SRE 视角：
  - 健康检查是容器编排的基础（Kubernetes liveness/readiness probe）
  - 检查命令要轻量，不能消耗太多资源
  - 要区分 liveness（进程存活）和 readiness（服务就绪）
  - start-period 要足够长，避免启动慢的应用被标记为不健康
```

#### 1.8 其他指令

```dockerfile
# WORKDIR — 设置工作目录（自动创建）
WORKDIR /app
# 等同于 mkdir -p /app && cd /app
# 支持相对路径（基于上一个 WORKDIR）
WORKDIR /app
WORKDIR src  # 实际是 /app/src

# USER — 设置运行用户
RUN useradd -r -s /bin/false appuser
USER appuser
# 后续所有 RUN/CMD/ENTRYPOINT 都以 appuser 身份执行

# EXPOSE — 声明端口（文档性质，不实际暴露端口）
EXPOSE 8080
EXPOSE 443/tcp
EXPOSE 8443/udp

# VOLUME — 声明挂载点
VOLUME /data
VOLUME ["/data", "/logs"]
# 运行时如果没有显式挂载，会创建匿名 volume

# SHELL — 更改默认 shell
SHELL ["/bin/bash", "-c"]
# 后续的 RUN 指令使用 bash 而非 sh

# LABEL — 添加元数据
LABEL maintainer="sre-team@example.com"
LABEL version="1.0"
LABEL description="My application"
LABEL org.opencontainers.image.source="https://github.com/org/repo"

# ONBUILD — 触发器（在子镜像构建时执行）
ONBUILD COPY . /app
ONBUILD RUN npm install
# 只有当其他 Dockerfile FROM 此镜像时才会执行
```

### 2. 多阶段构建（Multi-Stage Build）

#### 2.1 多阶段构建的原理

```
多阶段构建解决的核心问题：

  问题：构建环境和运行环境需求不同
  
  传统方式（单阶段）：
  ┌─────────────────────────────────────────────────────────────┐
  │ FROM golang:1.21               (800MB)                      │
  │ COPY . /app                    ← 源代码                     │
  │ RUN go build -o server         ← 编译器、依赖都在镜像中     │
  │ CMD ["/app/server"]                                         │
  │                                                              │
  │ 镜像大小：~800MB                                             │
  │ 包含：Go 编译器、源代码、所有构建依赖                        │
  └─────────────────────────────────────────────────────────────┘

  多阶段构建：
  ┌─────────────────────────────────────────────────────────────┐
  │ # 阶段 1：构建                                              │
  │ FROM golang:1.21 AS builder     (800MB)                     │
  │ COPY . /app                                                 │
  │ RUN go build -o server                                       │
  │                                                              │
  │ # 阶段 2：运行                                              │
  │ FROM alpine:3.18                (7MB)                       │
  │ COPY --from=builder /app/server /server                     │
  │ CMD ["/server"]                                             │
  │                                                              │
  │ 镜像大小：~15MB（仅包含二进制和 Alpine 基础）                │
  │ 优势：编译器、源代码、构建依赖都不在最终镜像中               │
  └─────────────────────────────────────────────────────────────┘
```

#### 2.2 多阶段构建实战

**Go 应用多阶段构建**：

```dockerfile
# syntax=docker/dockerfile:1

# ========== 阶段 1：依赖下载 ==========
FROM golang:1.21-alpine AS deps
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download && go mod verify

# ========== 阶段 2：构建 ==========
FROM deps AS builder
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w -X main.version=$(git describe --tags --always)" \
    -o /server ./cmd/server

# ========== 阶段 3：运行 ==========
FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/server"]
```

**Python 应用多阶段构建**：

```dockerfile
# syntax=docker/dockerfile:1

# ========== 阶段 1：构建依赖 ==========
FROM python:3.11-slim AS builder
WORKDIR /app

# 安装编译依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels \
    -r requirements.txt

# ========== 阶段 2：运行 ==========
FROM python:3.11-slim
WORKDIR /app

# 安装运行时依赖（不包含编译工具）
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 wheel 文件
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# 复制应用代码
COPY . .

# 安全加固
RUN useradd -r -s /bin/false appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Node.js 应用多阶段构建**：

```dockerfile
# syntax=docker/dockerfile:1

# ========== 阶段 1：安装依赖 ==========
FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production && \
    cp -R node_modules /prod_modules && \
    npm ci

# ========== 阶段 2：构建 ==========
FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ========== 阶段 3：运行 ==========
FROM node:18-alpine
WORKDIR /app
ENV NODE_ENV=production

# 仅复制生产依赖和构建产物
COPY --from=deps /prod_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY package.json ./

# 安全加固
RUN chown -R node:node /app
USER node

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "dist/server.js"]
```

**Java 应用多阶段构建**：

```dockerfile
# syntax=docker/dockerfile:1

# ========== 阶段 1：构建 ==========
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /app

# 先复制依赖文件（利用缓存）
COPY pom.xml .
RUN mvn dependency:go-offline -B

# 复制源代码并构建
COPY src ./src
RUN mvn package -DskipTests -B && \
    java -Djarmode=layertools -jar target/*.jar extract --destination /extracted

# ========== 阶段 2：运行 ==========
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# 分层复制（利用 Docker 缓存）
COPY --from=builder /extracted/dependencies/ ./
COPY --from=builder /extracted/spring-boot-loader/ ./
COPY --from=builder /extracted/snapshot-dependencies/ ./
COPY --from=builder /extracted/application/ ./

RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["java", "org.springframework.boot.loader.launch.JarLauncher"]
```

#### 2.3 多阶段构建的高级用法

```dockerfile
# 从外部镜像复制文件（不一定要 FROM 同一个基础镜像）
FROM alpine:3.18 AS certs
RUN apk --no-cache add ca-certificates

FROM scratch
COPY --from=certs /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY server /server
CMD ["/server"]

# 从特定阶段复制（命名阶段）
FROM golang:1.21 AS builder
RUN go build -o /server .

FROM alpine:3.18
COPY --from=builder /server /server

# 使用 ARG 控制构建
ARG BUILD_ENV=production
FROM builder AS build-prod
RUN go build -ldflags="-s -w" -o /server .

FROM builder AS build-dev
RUN go build -gcflags="all=-N -l" -o /server .

# 条件选择（需要 BuildKit）
FROM build-${BUILD_ENV} AS final-build

FROM alpine:3.18
COPY --from=final-build /server /server
```

### 3. 构建缓存优化

#### 3.1 缓存失效规则

```
Docker 构建缓存机制：

  每条 Dockerfile 指令执行后，Docker 会缓存该层的结果。
  下次构建时，如果指令和上下文未变化，直接使用缓存。

  缓存检查逻辑：
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. 基础镜像是否有更新？                                      │
  │    ├── 有 → 缓存失效，从此处开始重新构建                     │
  │    └── 没有 → 继续检查下一条指令                             │
  │                                                              │
  │ 2. COPY/ADD 指令的源文件是否变化？                           │
  │    ├── 文件内容 hash 变化 → 缓存失效                         │
  │    └── 文件内容 hash 不变 → 使用缓存                         │
  │                                                              │
  │ 3. RUN 指令是否变化？                                        │
  │    ├── 命令字符串变化 → 缓存失效                             │
  │    └── 命令字符串不变 → 使用缓存                             │
  │    注意：即使命令不变，如果依赖的外部资源变化，结果可能不同   │
  │                                                              │
  │ 4. 缓存失效后，后续所有层都必须重新构建                      │
  └─────────────────────────────────────────────────────────────┘
```

#### 3.2 缓存优化策略

```dockerfile
# ========== 策略 1：将不常变化的指令放在前面 ==========

# ❌ 缓存效率低
FROM node:18-alpine
WORKDIR /app
COPY . .                    # 代码一变，缓存全部失效
RUN npm install             # 每次都重新安装
RUN npm run build

# ✅ 缓存效率高
FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json ./   # 依赖文件先复制
RUN npm ci                                 # 只有依赖变化时才重新安装
COPY . .                                   # 代码变化不影响 npm ci 的缓存
RUN npm run build

# ========== 策略 2：利用 BuildKit 的缓存挂载 ==========

# syntax=docker/dockerfile:1

# apt 缓存挂载
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && apt-get install -y curl

# pip 缓存挂载
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# npm 缓存挂载
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Go module 缓存挂载
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Go build 缓存挂载
RUN --mount=type=cache,target=/root/.cache/go-build \
    go build -o /server .

# ========== 策略 3：使用 --link 选项（BuildKit）==========

# syntax=docker/dockerfile:1

# --link 使 COPY 层独立于基础镜像层，即使基础镜像变化也不影响缓存
COPY --link requirements.txt /app/
COPY --link go.mod go.sum /app/

# ========== 策略 4：合理拆分 RUN 指令 ==========

# 安装系统依赖（很少变化）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 安装应用依赖（偶尔变化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（经常变化）
COPY . .
```

#### 3.3 BuildKit 高级特性

```bash
# 启用 BuildKit（Docker 23.0+ 默认启用）
export DOCKER_BUILDKIT=1
# 或在 daemon.json 中配置
# { "features": { "buildkit": true } }

# 构建时显示详细输出
docker build --progress=plain -t myapp .

# 使用缓存导入导出（CI/CD 场景）
docker build \
    --cache-from type=registry,ref=myregistry.com/myapp:cache \
    --cache-to type=registry,ref=myregistry.com/myapp:cache,mode=max \
    -t myapp:v1 .

# 使用本地缓存目录
docker build \
    --cache-from type=local,src=/tmp/.buildx-cache \
    --cache-to type=local,dest=/tmp/.buildx-cache,mode=max \
    -t myapp:v1 .
```

```dockerfile
# syntax=docker/dockerfile:1

# BuildKit 的 mount 类型：
# 1. cache mount — 持久化缓存目录
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# 2. secret mount — 安全传递敏感信息（不写入镜像层）
RUN --mount=type=secret,id=mytoken \
    TOKEN=$(cat /run/secrets/mytoken) && \
    curl -H "Authorization: Bearer $TOKEN" https://api.example.com/data

# 3. ssh mount — 使用 SSH 密钥（不写入镜像层）
RUN --mount=type=ssh \
    git clone git@github.com:private/repo.git

# 4. bind mount — 挂载构建上下文的特定目录
RUN --mount=type=bind,source=config,target=/build/config \
    cp /build/config/app.conf /etc/app.conf
```

### 4. .dockerignore 文件

#### 4.1 为什么需要 .dockerignore

```
构建上下文 (Build Context)：

  docker build -t myapp .
                         ^-- 这个 "." 就是构建上下文

  构建上下文会被发送到 Docker Daemon
  如果目录中有大量无关文件：
  - 增加构建时间（传输构建上下文）
  - 增加镜像大小（COPY 了不需要的文件）
  - 泄露敏感信息（.env、.git、密钥等）

  .dockerignore 的作用：
  - 排除不需要的文件，减小构建上下文
  - 防止敏感文件进入镜像
  - 提高构建缓存命中率
```

#### 4.2 .dockerignore 语法

```
# .dockerignore 语法说明：

# 注释
*.md               # 排除所有 .md 文件
!README.md         # 但保留 README.md（取反规则）

.git               # 排除 .git 目录
.gitignore         # 排除 .gitignore 文件

**/temp            # 排除任意层级的 temp 目录
**/*.log           # 排除任意层级的 .log 文件

docs/              # 排除 docs 目录（末尾 / 表示目录）
docs               # 排除 docs 文件或目录

*.pyc              # 排除 Python 编译文件
__pycache__/       # 排除 Python 缓存目录
```

#### 4.3 完整的 .dockerignore 模板

```dockerignore
# ===== 版本控制 =====
.git
.gitignore
.gitattributes

# ===== Docker 相关 =====
Dockerfile*
docker-compose*.yml
.dockerignore

# ===== 环境配置和密钥 =====
.env
.env.*
*.pem
*.key
*.crt
*.p12
credentials.json
secrets/

# ===== IDE 和编辑器 =====
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# ===== 依赖目录 =====
node_modules/
vendor/
.venv/
venv/
__pycache__/
*.pyc
*.pyo

# ===== 构建产物 =====
dist/
build/
target/
*.o
*.so
*.a

# ===== 测试和文档 =====
tests/
test/
spec/
*.test.js
*.spec.js
coverage/
.nyc_output/
docs/
*.md
LICENSE

# ===== CI/CD =====
.github/
.gitlab-ci.yml
.travis.yml
Jenkinsfile
.circleci/

# ===== 日志和临时文件 =====
*.log
logs/
tmp/
temp/
```

### 5. 安全扫描与加固

#### 5.1 Dockerfile 安全最佳实践

```dockerfile
# ========== 1. 使用最小基础镜像 ==========
# ❌ 不安全
FROM ubuntu:22.04  # 包含大量不必要的工具

# ✅ 安全
FROM gcr.io/distroless/static-debian12  # 无 shell，最小攻击面
FROM alpine:3.18                          # 极简 Linux

# ========== 2. 不以 root 运行 ==========
RUN useradd -r -s /bin/false -d /app appuser
COPY --chown=appuser:appuser . /app
USER appuser

# ========== 3. 只读文件系统 ==========
# 运行时使用 --read-only
# docker run --read-only --tmpfs /tmp myapp

# ========== 4. 不安装不必要的包 ==========
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# ========== 5. 使用 COPY 而非 ADD ==========
COPY requirements.txt /app/    # 明确的行为
# ADD https://example.com/file /tmp/  # 不推荐

# ========== 6. 固定基础镜像版本 ==========
FROM python:3.11.7-slim-bookworm@sha256:abc123...  # 使用 digest

# ========== 7. 不暴露敏感信息 ==========
# ❌ 不安全
ARG DB_PASSWORD=secret123
ENV API_KEY=sk-xxxxx

# ✅ 安全
# 使用运行时环境变量或挂载 secret
# docker run -e DB_PASSWORD=xxx myapp
# docker secret 或 Kubernetes Secret

# ========== 8. 使用多阶段构建 ==========
# 构建工具不在最终镜像中

# ========== 9. 设置安全的默认值 ==========
# 限制进程
STOPSIGNAL SIGTERM
# 使用非特权端口
EXPOSE 8080
```

#### 5.2 镜像安全扫描

```bash
# 使用 Trivy 扫描 Dockerfile 和镜像
# 安装 Trivy
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# 扫描镜像
trivy image myapp:v1
trivy image --severity HIGH,CRITICAL myapp:v1
trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:v1  # CI/CD 中使用

# 扫描 Dockerfile（SAST）
trivy config Dockerfile

# 扫描文件系统
trivy fs --security-checks config .

# 使用 Docker Scout（Docker 官方）
docker scout cves myapp:v1
docker scout recommendations myapp:v1

# 使用 Grype
grype myapp:v1
grype myapp:v1 --fail-on high
```

```
安全扫描工具对比：

┌──────────────┬──────────┬──────────┬──────────────────────────────┐
│ 工具          │ 类型     │ 开源     │ 特点                         │
├──────────────┼──────────┼──────────┼──────────────────────────────┤
│ Trivy        │ 综合     │ 是       │ 支持镜像/文件系统/Git/配置   │
│ Grype        │ 镜像     │ 是       │ 轻量，速度快                 │
│ Docker Scout │ 镜像     │ 部分     │ Docker 官方，集成度高        │
│ Snyk         │ 综合     │ 部分     │ 商业级，漏洞库全面           │
│ Clair        │ 镜像     │ 是       │ CoreOS 出品，API 友好        │
│ Anchore      │ 综合     │ 部分     │ 企业级，策略引擎强大         │
└──────────────┴──────────┴──────────┴──────────────────────────────┘
```

### 6. 生产级 Dockerfile 模板

#### 6.1 Go 应用完整模板

```dockerfile
# syntax=docker/dockerfile:1

# ============================================================
# Go 应用生产级 Dockerfile
# ============================================================

# ---------- 参数定义 ----------
ARG GO_VERSION=1.21
ARG ALPINE_VERSION=3.18
ARG APP_NAME=server

# ---------- 阶段 1：依赖下载 ----------
FROM golang:${GO_VERSION}-alpine AS deps
RUN apk add --no-cache git
WORKDIR /app
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# ---------- 阶段 2：构建 ----------
FROM deps AS builder
ARG APP_NAME
ARG VERSION=dev
ARG BUILD_TIME
RUN apk add --no-cache ca-certificates tzdata
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build \
    -ldflags="-s -w -X main.version=${VERSION} -X main.buildTime=${BUILD_TIME}" \
    -o /${APP_NAME} ./cmd/server

# ---------- 阶段 3：运行 ----------
FROM alpine:${ALPINE_VERSION}
ARG APP_NAME

# 安全：安装必要的运行时依赖
RUN apk --no-cache add ca-certificates tzdata && \
    addgroup -S appgroup && \
    adduser -S appuser -G appgroup -h /app

WORKDIR /app

# 从构建阶段复制产物
COPY --from=builder /${APP_NAME} ./
COPY --from=builder /app/config ./config

# 安全：切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:8080/health || exit 1

# 暴露端口
EXPOSE 8080

# 启动命令
ENTRYPOINT ["./server"]
```

#### 6.2 Python 应用完整模板

```dockerfile
# syntax=docker/dockerfile:1

# ============================================================
# Python 应用生产级 Dockerfile
# ============================================================

ARG PYTHON_VERSION=3.11

# ---------- 阶段 1：构建依赖 ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels \
    -r requirements.txt

# ---------- 阶段 2：运行 ----------
FROM python:${PYTHON_VERSION}-slim-bookworm

# 安装运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -r -s /bin/false -d /app appuser

WORKDIR /app

# 安装 Python 包
COPY --from=builder /wheels /wheels
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# 复制应用代码
COPY --chown=appuser:appuser . .

# 安全：切换用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
```

### 7. SRE 实战：Dockerfile 故障排查

#### 7.1 常见构建问题

```bash
# 问题 1：构建上下文过大
# 症状：Sending build context to Docker daemon 2.5GB
# 解决：
# 1. 检查当前目录大小
du -sh . --exclude=.git | sort -rh | head -20
# 2. 创建 .dockerignore
# 3. 使用更精确的构建上下文
docker build -t myapp -f Dockerfile .  # 确保只发送必要文件

# 问题 2：缓存失效频繁
# 症状：每次构建都要重新安装依赖
# 解决：
# 1. 检查 Dockerfile 中 COPY 的顺序
# 2. 先复制依赖文件，再复制源代码
# 3. 使用 BuildKit 缓存挂载

# 问题 3：镜像过大
# 症状：构建的镜像有几 GB
# 排查：
docker history myapp:v1 --format "table {{.CreatedBy}}\t{{.Size}}" | head -20
# 解决：
# 1. 使用多阶段构建
# 2. 使用精简基础镜像（alpine/slim/distroless）
# 3. 合并 RUN 指令并清理缓存
# 4. 使用 .dockerignore 排除不需要的文件

# 问题 4：权限问题
# 症状：Permission denied
# 解决：
# 1. 检查文件的 owner
# 2. 使用 COPY --chown 设置正确的权限
# 3. 确保 USER 指令的用户有必要的权限

# 问题 5：构建缓存不生效
# 症状：每次都从头构建
# 排查：
docker build --no-cache -t myapp .  # 对比有缓存和无缓存的构建时间
# 解决：
# 1. 检查是否有 ARG 值变化
# 2. 检查 COPY 的文件是否有变化（包括时间戳）
# 3. 使用 BuildKit 的 --cache-from 从远程加载缓存
```

#### 7.2 镜像大小优化实战

```bash
# 分析镜像层大小
docker history myapp:v1 --format "table {{.CreatedBy}}\t{{.Size}}" --no-trunc

# 使用 dive 工具深入分析（推荐）
# 安装：https://github.com/wagoodman/dive
dive myapp:v1

# dive 界面说明：
# 左侧：镜像层列表
# 右侧：当前层的文件变更
# 空格：切换显示新增/修改/删除的文件
# Tab：切换左右面板

# 使用 docker inspect 分析
docker inspect myapp:v1 | jq '.[0].RootFS.Layers | length'
docker inspect myapp:v1 | jq '.[0].Size'
```

---

## 💻 实战练习

### 练习 1：优化 Dockerfile

**目标**：将一个低效的 Dockerfile 优化为生产级。

```bash
# 原始 Dockerfile（低效版本）
cat > /tmp/Dockerfile.original << 'EOF'
FROM python:3.11
RUN apt-get update
RUN apt-get install -y gcc
RUN apt-get install -y libpq-dev
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN apt-get remove -y gcc
RUN apt-get autoremove -y
EXPOSE 8080
CMD python app.py
EOF

# 分析问题：
# 1. 使用完整 Python 镜像（~900MB），应使用 slim 或 alpine
# 2. 多个 RUN 指令，产生多个层
# 3. COPY . /app 放在 pip install 之前，依赖安装无法利用缓存
# 4. 以 root 用户运行
# 5. 使用 shell 格式的 CMD
# 6. 没有 .dockerignore
# 7. 没有健康检查

# 优化后的 Dockerfile
cat > /tmp/Dockerfile.optimized << 'EOF'
# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm AS builder
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim-bookworm
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -r -s /bin/false -d /app appuser
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

# 创建 .dockerignore
cat > /tmp/.dockerignore << 'EOF'
.git
.gitignore
Dockerfile*
docker-compose*.yml
.dockerignore
.env
.env.*
__pycache__
*.pyc
*.pyo
.pytest_cache
.coverage
htmlcov
tests/
docs/
*.md
.vscode/
.idea/
node_modules/
EOF

echo "原始文件和优化文件已创建在 /tmp/ 目录"
echo "对比两者的差异，理解每一步优化的原因"
```

### 练习 2：多阶段构建 Go 应用

**目标**：为一个 Go 应用编写完整的多阶段 Dockerfile。

```bash
# 1. 创建示例 Go 应用
mkdir -p /tmp/go-app/cmd/server
cat > /tmp/go-app/cmd/server/main.go << 'EOF'
package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "os"
    "runtime"
    "time"
)

type HealthResponse struct {
    Status    string `json:"status"`
    Timestamp string `json:"timestamp"`
    Version   string `json:"version"`
    GoVersion string `json:"go_version"`
}

var version = "dev"

func healthHandler(w http.ResponseWriter, r *http.Request) {
    resp := HealthResponse{
        Status:    "healthy",
        Timestamp: time.Now().UTC().Format(time.RFC3339),
        Version:   version,
        GoVersion: runtime.Version(),
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func rootHandler(w http.ResponseWriter, r *http.Request) {
    fmt.Fprintf(w, "Hello from %s/%s (version: %s)\n", runtime.GOOS, runtime.GOARCH, version)
}

func main() {
    port := os.Getenv("PORT")
    if port == "" {
        port = "8080"
    }

    http.HandleFunc("/", rootHandler)
    http.HandleFunc("/health", healthHandler)

    log.Printf("Starting server on :%s (version: %s)", port, version)
    if err := http.ListenAndServe(":"+port, nil); err != nil {
        log.Fatal(err)
    }
}
EOF

cat > /tmp/go-app/go.mod << 'EOF'
module github.com/example/go-app
go 1.21
EOF

cat > /tmp/go-app/go.sum << 'EOF'
EOF

# 2. 创建 Dockerfile
cat > /tmp/go-app/Dockerfile << 'EOF'
# syntax=docker/dockerfile:1

# 阶段 1：依赖下载
FROM golang:1.21-alpine AS deps
WORKDIR /app
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download

# 阶段 2：构建
FROM deps AS builder
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w" -o /server ./cmd/server

# 阶段 3：运行
FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/server"]
EOF

# 3. 创建 .dockerignore
cat > /tmp/go-app/.dockerignore << 'EOF'
.git
Dockerfile
.dockerignore
*.md
EOF

# 4. 构建镜像
cd /tmp/go-app
docker build -t go-app:v1 .

# 5. 查看镜像大小
docker images go-app:v1
echo "镜像大小应该在 10-20MB 左右"

# 6. 运行测试
docker run --rm -d --name go-test -p 8080:8080 go-app:v1
sleep 2
curl http://localhost:8080/
curl http://localhost:8080/health
docker rm -f go-test

# 7. 清理
rm -rf /tmp/go-app
```

### 练习 3：Dockerfile 安全扫描

**目标**：使用安全扫描工具检查 Dockerfile 和镜像。

```bash
# 1. 创建一个有意包含安全问题的 Dockerfile
mkdir -p /tmp/security-test
cat > /tmp/security-test/Dockerfile << 'EOF'
FROM ubuntu:22.04

# 问题 1：以 root 运行
# 问题 2：安装不必要的包
RUN apt-get update && apt-get install -y \
    curl wget vim nano netcat telnet ssh sudo

# 问题 3：硬编码密钥
ENV API_KEY=sk-1234567890abcdef
ARG DB_PASSWORD=supersecret

# 问题 4：使用 ADD 下载远程文件
ADD https://example.com/app.tar.gz /opt/

# 问题 5：暴露不必要的端口
EXPOSE 22 80 443 3306 5432 6379

CMD ["bash"]
EOF

# 2. 使用 Trivy 扫描 Dockerfile 配置
# 安装 Trivy（如果没有）
# curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

cd /tmp/security-test
# trivy config Dockerfile
echo "使用 trivy config Dockerfile 扫描配置问题"

# 3. 创建安全版本的 Dockerfile
cat > /tmp/security-test/Dockerfile.secure << 'EOF'
FROM python:3.11-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -r -s /bin/false -d /app appuser

WORKDIR /app
COPY --chown=appuser:appuser . .
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "app.py"]
EOF

# 4. 对比两个 Dockerfile
echo "=== 问题 Dockerfile ==="
cat /tmp/security-test/Dockerfile
echo ""
echo "=== 安全 Dockerfile ==="
cat /tmp/security-test/Dockerfile.secure

# 5. 清理
rm -rf /tmp/security-test
```

---

## 🎯 面试题精选

### 面试题 1：解释 Dockerfile 中 CMD 和 ENTRYPOINT 的区别，以及它们如何组合使用。

**参考答案**：

CMD 设置容器启动时的默认命令，可以被 docker run 的参数完全覆盖。ENTRYPOINT 设置容器的入口点，不会被 docker run 的参数覆盖，而是将参数追加到 ENTRYPOINT 之后。两者组合使用时，ENTRYPOINT 定义主命令，CMD 定义默认参数。例如 `ENTRYPOINT ["python"]` 和 `CMD ["app.py"]` 组合，`docker run myimage` 执行 `python app.py`，`docker run myimage test.py` 执行 `python test.py`。关键点是必须使用 Exec 格式（JSON 数组），Shell 格式会导致进程不是 PID 1，无法正确接收信号。

### 面试题 2：什么是多阶段构建？为什么它是生产环境的最佳实践？

**参考答案**：

多阶段构建允许在一个 Dockerfile 中使用多个 FROM 指令，每个 FROM 开始一个新的构建阶段。构建工具和依赖只存在于构建阶段，最终镜像只包含运行所需的最小文件。优势包括：1）镜像体积大幅减小（从数百 MB 降到数十 MB），减少攻击面和存储成本；2）构建工具和源代码不在最终镜像中，提高安全性；3）每个阶段独立缓存，提高构建效率；4）可以在不同阶段使用不同的基础镜像。典型用法是在第一个阶段使用完整 SDK 编译代码，在第二个阶段使用精简运行时镜像（如 Alpine 或 distroless）。

### 面试题 3：ARG 和 ENV 有什么区别？各自的使用场景是什么？

**参考答案**：

ARG 是构建时参数，仅在 docker build 过程中存在，不会进入最终镜像，通过 `--build-arg` 传入。ENV 是环境变量，构建时和运行时都存在，写入镜像层，运行时可以通过 `-e` 覆盖。使用场景：ARG 适合构建时的配置（如版本号、构建时间、代理地址），ENV 适合运行时配置（如数据库连接、日志级别）。注意 ARG 的安全性：虽然不进入运行时环境，但可以通过 `docker history` 看到 ARG 的值，因此敏感信息不应使用 ARG。此外，ARG 在 FROM 之前声明可以在 FROM 中使用，但需要在每个阶段重新声明。

### 面试题 4：如何优化 Dockerfile 的构建缓存？

**参考答案**：

核心原则是将不常变化的指令放在前面，经常变化的放在后面。具体策略：1）先复制依赖文件（如 package.json、go.mod），安装依赖，再复制源代码；2）合并相关的 RUN 指令减少层数；3）使用 BuildKit 的 `--mount=type=cache` 挂载包管理器缓存目录（pip、npm、go mod）；4）使用 `--link` 选项使 COPY 层独立于基础镜像变化；5）在 CI/CD 中使用 `--cache-from` 从远程仓库加载缓存。一个常见的错误是 `COPY . /app` 放在 `RUN pip install` 之前，导致每次代码变更都要重新安装依赖。

### 面试题 5：.dockerignore 文件的作用是什么？应该排除哪些文件？

**参考答案**：

.dockerignore 文件用于排除构建上下文中不需要的文件。作用包括：1）减小构建上下文大小，加快传输速度；2）防止敏感文件（.env、.git、密钥）进入镜像；3）提高缓存命中率（避免无关文件变化触发缓存失效）。应该排除的文件包括：版本控制目录（.git）、Docker 相关文件（Dockerfile、docker-compose）、环境配置和密钥（.env、*.pem）、依赖目录（node_modules、vendor、__pycache__）、构建产物（dist、build、target）、测试和文档（tests、docs、*.md）、IDE 配置（.vscode、.idea）。

### 面试题 6：如何确保 Dockerfile 构建的镜像尽可能安全？

**参考答案**：

安全加固策略：1）使用最小基础镜像（distroless、Alpine），减少攻击面；2）以非 root 用户运行（USER 指令）；3）使用多阶段构建，不将构建工具和源代码包含在最终镜像；4）使用 COPY 而非 ADD，避免隐含行为；5）不硬编码敏感信息（使用运行时环境变量或 secret mount）；6）固定基础镜像版本，使用 digest 引用；7）使用安全扫描工具（Trivy、Grype）检查已知漏洞；8）只安装必要的包，使用 --no-install-recommends；9）清理包管理器缓存；10）设置 HEALTHCHECK 确保容器可被监控。

### 面试题 7：BuildKit 相比传统构建有什么优势？

**参考答案**：

BuildKit 是 Docker 的下一代构建引擎，主要优势：1）并行构建，独立的构建阶段可以并行执行，提高构建速度；2）缓存挂载（--mount=type=cache），可以跨构建持久化包管理器缓存；3）Secret 挂载（--mount=type=secret），敏感信息不写入镜像层；4）SSH 挂载（--mount=type=ssh），安全使用 SSH 密钥；5）构建缓存导入导出（--cache-from/--cache-to），支持 CI/CD 场景的远程缓存；6）更好的 .dockerignore 支持；7）声明式语法（# syntax=docker/dockerfile:1）；8）输出格式更灵活（local、tar、registry 等）。Docker 23.0+ 默认使用 BuildKit。

### 面试题 8：如何分析和优化 Docker 镜像大小？

**参考答案**：

分析方法：1）`docker history` 查看每层大小；2）`dive` 工具可视化分析每层的文件变更；3）`docker system df -v` 查看总体磁盘使用。优化策略：1）使用精简基础镜像（Alpine ~7MB vs Ubuntu ~77MB）；2）多阶段构建，只保留运行时产物；3）合并 RUN 指令并清理缓存（`rm -rf /var/lib/apt/lists/*`、`--no-cache-dir`）；4）使用 `--no-install-recommends` 避免不必要的依赖；5）删除不需要的文件（文档、示例、测试）；6）使用 .dockerignore 排除无关文件；7）使用 `go build -ldflags="-s -w"` 等编译选项减小二进制大小；8）使用 UPX 压缩二进制（但会增加启动时间）。

### 面试题 9：解释 Dockerfile 中的 ONBUILD 指令及其使用场景。

**参考答案**：

ONBUILD 指令定义了一个触发器，当其他镜像以该镜像作为基础镜像（FROM）构建时，ONBUILD 中的指令会在子镜像构建的 FROM 之后自动执行。使用场景：1）创建通用的基础镜像模板，如 Node.js 应用的基础镜像可以预定义 `ONBUILD COPY . /app` 和 `ONBUILD RUN npm install`；2）团队标准化构建流程，基础镜像维护者定义构建步骤，应用开发者只需 FROM 基础镜像。注意事项：ONBUILD 不能嵌套（ONBUILD ONBUILD 无效），不能触发 FROM 或 MAINTAINER，且在子镜像中不会看到父镜像的 ONBUILD 指令。

### 面试题 10：如何在 CI/CD 流水线中优化 Docker 构建速度？

**参考答案**：

优化策略包括：1）使用 BuildKit 并行构建；2）利用缓存：将不常变化的指令放在前面，使用 `--cache-from` 从远程仓库加载缓存；3）使用 `--mount=type=cache` 持久化包管理器缓存；4）使用多阶段构建，只重建变化的阶段；5）减小构建上下文：使用 .dockerignore，避免传输不必要的文件；6）使用远程缓存：`--cache-from type=registry` 和 `--cache-to type=registry`；7）使用构建矩阵并行构建多架构镜像；8）选择合适的构建触发条件，避免不必要的构建；9）使用 `--mount=type=bind` 挂载大文件而非 COPY。

---

## 📚 深入阅读

### 官方文档
- [Dockerfile 参考手册](https://docs.docker.com/engine/reference/builder/)
- [Dockerfile 最佳实践](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [多阶段构建文档](https://docs.docker.com/build/building/multi-stage/)
- [BuildKit 文档](https://docs.docker.com/build/buildkit/)

### 安全相关
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [Docker 安全最佳实践](https://docs.docker.com/develop/security-best-practices/)
- [Trivy 文档](https://aquasecurity.github.io/trivy/)

### 推荐书籍
- 《Docker Deep Dive》— Nigel Poulton
- 《Container Security》— Liz Rice

---

## ✅ 自检清单

### 理论检查点
- [ ] 能解释每条 Dockerfile 指令的作用和底层行为
- [ ] 理解 CMD vs ENTRYPOINT 的区别和组合使用
- [ ] 理解 ARG vs ENV 的生命周期和使用场景
- [ ] 掌握多阶段构建的原理和优势
- [ ] 理解构建缓存的失效规则和优化策略
- [ ] 知道 .dockerignore 的作用和最佳实践

### 实操检查点
- [ ] 能编写 Go/Python/Node.js 的生产级 Dockerfile
- [ ] 能使用多阶段构建优化镜像大小
- [ ] 能配置 .dockerignore 优化构建上下文
- [ ] 能使用安全扫描工具检查镜像漏洞
- [ ] 能使用 BuildKit 缓存挂载加速构建

### 能力验证标准
- [ ] 能将任意应用的 Dockerfile 优化到合理大小（<100MB）
- [ ] 能回答 80% 以上的面试题
- [ ] 能为团队建立 Dockerfile 编写规范
- [ ] 能在 CI/CD 中集成镜像构建和安全扫描
