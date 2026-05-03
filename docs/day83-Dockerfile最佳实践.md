# Day 83: Dockerfile 最佳实践

> 📅 日期：2026-05-03
> 📖 学习主题：Dockerfile 最佳实践
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 77 (Docker 镜像基础), Day 78 (Dockerfile 进阶构建), Day 82 (Docker 化 Web 应用)

## 🎯 学习目标

- 掌握镜像瘦身的核心策略，能将镜像体积减少 80% 以上
- 理解 Dockerfile 安全加固的所有关键措施
- 能配置非 root 用户运行容器并理解其安全意义
- 掌握 Trivy 和 Grype 镜像扫描工具的使用
- 理解镜像签名（Cosign/Notary）的原理与配置
- 能将 Dockerfile 构建集成到 CI/CD 流水线中

---

## 📖 核心知识点

### 1. 镜像瘦身策略

#### 1.1 镜像层与体积的关系

```
Docker 镜像层结构:

┌─────────────────────────────────────────┐
│  Layer 5: COPY app.py          2 KB     │  ← 可写层 (容器层)
├─────────────────────────────────────────┤
│  Layer 4: RUN pip install     50 MB     │  ← 可缓存
├─────────────────────────────────────────┤
│  Layer 3: COPY requirements   0.5 KB    │
├─────────────────────────────────────────┤
│  Layer 2: RUN apt-get install 30 MB     │  ← 应清理缓存
├─────────────────────────────────────────┤
│  Layer 1: FROM python:3.12   900 MB     │  ← 基础镜像
└─────────────────────────────────────────┘

优化原则:
1. 减少层数（合并 RUN 指令）
2. 清理每层的缓存和临时文件
3. 使用更小的基础镜像
4. 多阶段构建分离构建和运行环境
5. 利用 .dockerignore 减少上下文大小
```

#### 1.2 基础镜像选择对比

| 基础镜像 | 大小 | 包管理器 | Shell | 适用场景 |
|----------|------|---------|-------|---------|
| ubuntu:22.04 | ~77MB | apt | bash | 通用，兼容性最好 |
| debian:bookworm-slim | ~80MB | apt | bash | 生产推荐，平衡大小和兼容 |
| alpine:3.19 | ~7MB | apk | ash | 最小，但 musl 兼容问题 |
| python:3.12 | ~1GB | apt | bash | 开发环境 |
| python:3.12-slim | ~150MB | apt | bash | Python 生产推荐 |
| python:3.12-alpine | ~50MB | apk | ash | Python 最小镜像 |
| node:20 | ~1GB | apt | bash | Node.js 开发 |
| node:20-slim | ~180MB | apt | bash | Node.js 生产推荐 |
| node:20-alpine | ~130MB | apk | ash | Node.js 最小镜像 |
| golang:1.22 | ~800MB | apt | bash | Go 构建阶段 |
| scratch | 0MB | 无 | 无 | Go 静态二进制 |
| gcr.io/distroless/static | ~2MB | 无 | 无 | Go/静态程序生产 |
| cgr.dev/chainguard/wolfi-base | ~12MB | apk | ash | 安全优先 |

#### 1.3 多阶段构建详解

```dockerfile
# 示例: Java Spring Boot 应用
# Stage 1: 构建
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app
COPY pom.xml .
# 下载依赖（利用缓存，依赖不变时不重新下载）
RUN mvn dependency:go-offline -B
COPY src/ ./src/
RUN mvn package -DskipTests -B

# Stage 2: 运行
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
# 只复制构建产物
COPY --from=builder /app/target/*.jar app.jar
# 创建非 root 用户
RUN useradd -r -s /bin/false appuser
USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]

# 对比:
# 单阶段: ~1.2GB (包含 Maven、JDK、源码、依赖缓存)
# 多阶段: ~280MB (仅 JRE + JAR)
```

```dockerfile
# 示例: Go 应用 - scratch 镜像
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o server ./cmd/server

FROM scratch
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /app/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]

# 最终镜像: ~10MB (仅包含静态二进制和 CA 证书)
```

```dockerfile
# 示例: React 前端 + Nginx
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.25-alpine
# 自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf
# 从构建阶段复制产物
COPY --from=builder /app/dist /usr/share/nginx/html
# 设置正确权限
RUN chown -R nginx:nginx /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# 对比:
# node:20 全量: ~1GB
# 多阶段 (nginx:alpine): ~45MB
```

#### 1.4 RUN 指令优化

```dockerfile
# 错误示范: 多个 RUN 指令，每层都有缓存
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y wget
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

# 正确示范: 合并为一个 RUN，清理缓存
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        ca-certificates \
        tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python pip 优化
RUN pip install --no-cache-dir -r requirements.txt
# --no-cache-dir 避免保留 pip 缓存

# npm 优化
RUN npm ci --only=production && npm cache clean --force
# ci 比 install 更快且确定性更高

# Go 模块缓存优化
RUN go mod download
# 单独下载依赖层，代码变化时不重新下载

# 使用 BuildKit mount cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
```

#### 1.5 .dockerignore 文件

```gitignore
# .dockerignore
# 版本控制
.git
.gitignore
.svn

# 依赖目录
node_modules
vendor
__pycache__
*.pyc
*.pyo
.venv
env

# IDE 和编辑器
.vscode
.idea
*.swp
*.swo
*~

# Docker 相关
Dockerfile
docker-compose*.yml
.dockerignore

# 文档
README.md
docs/
*.md
LICENSE

# 测试
tests/
test/
*_test.go
.coverage
htmlcov/
.pytest_cache

# 构建产物（应该在容器内构建）
dist/
build/
*.egg-info/

# 环境变量和密钥
.env
.env.*
*.pem
*.key
*.crt

# 系统文件
.DS_Store
Thumbs.db

# CI/CD
.github/
.gitlab-ci.yml
Jenkinsfile
.circleci/
```

---

### 2. 安全加固

#### 2.1 Dockerfile 安全检查清单

```
Dockerfile 安全最佳实践:

┌─────────────────────────────────────────────────────┐
│                    安全层次                          │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Layer 1: 基础镜像安全                        │   │
│  │  - 使用可信的基础镜像源                        │   │
│  │  - 固定版本标签 (不使用 latest)                │   │
│  │  - 定期更新基础镜像                            │   │
│  │  - 使用 distroless/chainguard 等安全镜像       │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Layer 2: 构建过程安全                        │   │
│  │  - 使用多阶段构建                             │   │
│  │  - 不安装不必要的包                            │   │
│  │  - 使用 --no-install-recommends               │   │
│  │  - 清理包管理器缓存                            │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Layer 3: 运行时安全                          │   │
│  │  - 非 root 用户运行                           │   │
│  │  - 只读文件系统 (read_only)                    │   │
│  │  - 删除 setuid/setgid 位                      │   │
│  │  - 使用 HEALTHCHECK                           │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  Layer 4: 敏感信息保护                        │   │
│  │  - 不在 ENV/ARG 中存储密码                     │   │
│  │  - 使用 BuildKit secrets                      │   │
│  │  - 不在镜像中留下密钥文件                      │   │
│  │  - 使用 .dockerignore 排除敏感文件             │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

#### 2.2 安全基础镜像

```dockerfile
# 使用固定版本和摘要 (digest)
FROM python:3.12.1-slim-bookworm@sha256:abc123...

# 使用 Chainguard 镜像 (安全优先)
FROM cgr.dev/chainguard/python:latest-dev AS builder
FROM cgr.dev/chainguard/python:latest

# 使用 Google Distroless
FROM gcr.io/distroless/python3-debian12
# 不包含 shell、包管理器等，攻击面最小

# 使用 Red Hat Universal Base Image (UBI)
FROM registry.access.redhat.com/ubi9/ubi-minimal:9.3
```

#### 2.3 非 root 用户详解

```dockerfile
# 完整的非 root 用户配置

FROM python:3.12-slim-bookworm

# 1. 创建用户和组
# -r: 系统用户 (无密码过期)
# -s /bin/false: 禁止登录 shell
# -d /app: 指定主目录
# -M: 不创建主目录
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -s /bin/false -d /app -M appuser

# 2. 创建应用目录并设置权限
WORKDIR /app
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser . .

# 3. 处理需要写入的目录
# 创建日志目录
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs
# 创建临时文件目录
RUN mkdir -p /tmp/app && chown appuser:appuser /tmp/app

# 4. 删除不必要的 setuid/setgid 二进制文件
RUN find / -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

# 5. 切换到非 root 用户
USER appuser

# 6. 设置合理的默认值
ENV HOME=/app \
    TMPDIR=/tmp/app

EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:create_app()"]
```

```dockerfile
# 对于 Alpine 镜像
FROM node:20-alpine

RUN addgroup -g 1000 appgroup && \
    adduser -u 1000 -G appgroup -s /bin/sh -D appuser

WORKDIR /app
COPY --chown=appuser:appgroup package*.json ./
RUN npm ci --only=production
COPY --chown=appuser:appgroup . .

USER appuser
CMD ["node", "src/index.js"]
```

```dockerfile
# 对于 Go scratch 镜像
FROM golang:1.22-alpine AS builder
# ... 编译 ...

FROM scratch
# scratch 没有 useradd，需要在构建阶段处理
# 方案: 使用数字 UID/GID
COPY --from=builder --chown=1000:1000 /app/server /server
USER 1000:1000
ENTRYPOINT ["/server"]
```

#### 2.4 BuildKit Secrets

```dockerfile
# 使用 BuildKit secrets 安全地使用私有仓库
# syntax=docker/dockerfile:1

FROM python:3.12-slim

# 安装私有 pip 包
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    pip install --no-cache-dir -r requirements.txt

# 使用私有 Git 仓库
RUN --mount=type=secret,id=git_token \
    GIT_TOKEN=$(cat /run/secrets/git_token) && \
    git clone https://${GIT_TOKEN}@github.com/private/repo.git /tmp/repo

# 使用 npm 私有仓库
RUN --mount=type=secret,id=npmrc,target=/app/.npmrc \
    npm ci --only=production
```

```bash
# 构建时传递 secrets
DOCKER_BUILDKIT=1 docker build \
  --secret id=pip_conf,src=$HOME/.pip/pip.conf \
  --secret id=git_token,src=./git_token \
  --secret id=npmrc,src=$HOME/.npmrc \
  -t myapp:latest .

# secrets 不会被保存在镜像层中
```

#### 2.5 其他安全措施

```dockerfile
# 1. 使用 LABEL 添加元数据
LABEL org.opencontainers.image.title="My App" \
      org.opencontainers.image.description="Production web application" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="My Company" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/my/app"

# 2. 不要暴露不必要的端口
# 仅 EXPOSE 实际需要的端口
EXPOSE 8080

# 3. 使用 STOPSIGNAL
STOPSIGNAL SIGTERM

# 4. 使用 --no-install-recommends
RUN apt-get update && apt-get install -y --no-install-recommends \
    package1 \
    package2 \
    && rm -rf /var/lib/apt/lists/*

# 5. 固定 GPG 密钥验证
RUN curl -fsSL https://example.com/gpg.key | gpg --dearmor -o /usr/share/keyrings/example.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/example.gpg] https://example.com/repo stable main" \
    > /etc/apt/sources.list.d/example.list

# 6. 使用 WORKDIR 而非 RUN cd
WORKDIR /app
# 而非
# RUN cd /app && ...
```

---

### 3. 镜像扫描: Trivy

#### 3.1 Trivy 简介与安装

```bash
# 安装 Trivy
# Debian/Ubuntu
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | sudo tee /usr/share/keyrings/trivy.gpg > /dev/null
echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy

# RHEL/CentOS
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://aquasecurity.github.io/trivy-repo/rpm/trivy.repo
sudo yum install trivy

# macOS
brew install trivy

# Docker 方式运行
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy:latest image nginx:latest

# 二进制安装
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
```

#### 3.2 Trivy 扫描命令

```bash
# === 基本扫描 ===
# 扫描本地镜像
trivy image myapp:latest

# 扫描远程镜像
trivy image nginx:1.25
trivy image registry.example.com/myapp:v1

# === 输出格式 ===
# 表格输出 (默认)
trivy image myapp:latest

# JSON 输出 (适合自动化)
trivy image --format json --output result.json myapp:latest

# SARIF 输出 (集成 GitHub Code Scanning)
trivy image --format sarif --output result.sarif myapp:latest

# 只显示严重级别
trivy image --severity HIGH,CRITICAL myapp:latest

# === 扫描类型 ===
# 漏洞扫描 (默认)
trivy image myapp:latest

# 配置扫描 (Dockerfile, K8s YAML 等)
trivy config ./Dockerfile
trivy config ./k8s/

# 文件系统扫描
trivy fs --security-checks vuln,secret .

# 仓库扫描
trivy repo https://github.com/my/app

# Secret 扫描
trivy fs --security-checks secret .

# === CI/CD 集成 ===
# 仅在发现高危以上漏洞时失败 (exit code 1)
trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest

# 忽略未修复的漏洞
trivy image --ignore-unfixed myapp:latest

# 使用自定义漏洞数据库
trivy image --db-repository ghcr.io/aquasecurity/trivy-db myapp:latest

# === 跳过特定漏洞 ===
# 使用 .trivyignore 文件
cat > .trivyignore << 'EOF'
# 临时忽略，等待上游修复
CVE-2023-12345
# 已评估风险可接受
CVE-2023-67890
EOF

trivy image --ignorefile .trivyignore myapp:latest
```

#### 3.3 Trivy 扫描结果解读

```bash
$ trivy image --severity HIGH,CRITICAL myapp:latest

myapp:latest (debian 12.4)
Total: 5 (HIGH: 3, CRITICAL: 2)

┌──────────────┬────────────────┬──────────┬─────────────────────────┬─────────────────────────────────────┬───────────────────────┐
│   Library    │ Vulnerability  │ Severity │  Installed Version      │          Fixed Version              │        Title          │
├──────────────┼────────────────┼──────────┼─────────────────────────┼─────────────────────────────────────┼───────────────────────┤
│ libssl3      │ CVE-2023-XXXXX │ CRITICAL │ 3.0.11-1~deb12u1       │ 3.0.13-1~deb12u1                    │ OpenSSL: buffer       │
│              │                │          │                         │                                     │ overflow              │
├──────────────┼────────────────┼──────────┼─────────────────────────┼─────────────────────────────────────┼───────────────────────┤
│ curl         │ CVE-2024-YYYYY │ HIGH     │ 7.88.1-10+deb12u5      │ 7.88.1-10+deb12u7                   │ curl: use-after-free  │
└──────────────┴────────────────┴──────────┴─────────────────────────┴─────────────────────────────────────┴───────────────────────┘

解读:
- Library: 受影响的库
- Vulnerability: CVE 编号
- Severity: 严重程度 (CRITICAL > HIGH > MEDIUM > LOW)
- Installed Version: 当前安装的版本
- Fixed Version: 修复该漏洞的版本
- Title: 漏洞标题

处理策略:
- CRITICAL: 必须立即修复
- HIGH: 应尽快修复
- MEDIUM: 评估后决定是否修复
- LOW: 记录但通常不需要紧急处理
```

#### 3.4 Trivy 在 CI/CD 中的使用

```yaml
# GitHub Actions 示例
name: Docker Image Scan
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

```yaml
# GitLab CI 示例
stages:
  - build
  - scan

build:
  stage: build
  script:
    - docker build -t myapp:$CI_COMMIT_SHA .

trivy-scan:
  stage: scan
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy image --exit-code 1 --severity HIGH,CRITICAL --no-progress myapp:$CI_COMMIT_SHA
  allow_failure: false
```

---

### 4. 镜像扫描: Grype

#### 4.1 Grype 安装与使用

```bash
# 安装 Grype
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# macOS
brew install grype

# Docker 方式
docker run --rm anchore/grype:latest myapp:latest

# 基本使用
grype myapp:latest
grype nginx:1.25
grype registry.example.com/myapp:v1

# 输出格式
grype myapp:latest -o json > result.json
grype myapp:latest -o table  # 默认
grype myapp:latest -o cyclonedx  # SBOM 格式

# 只显示特定严重级别
grype myapp:latest --fail-on critical
grype myapp:latest --only-fixed  # 只显示有修复的漏洞

# 扫描文件系统
grype dir:./my-project
grype file:./package-lock.json

# 扫描 SBOM
grype sbom:./sbom.json

# 忽略特定漏洞
cat > .grype.yaml << 'EOF'
ignore:
  - vulnerability: CVE-2023-12345
    reason: "Risk accepted - not exploitable in our context"
  - package:
      name: libxml2
      type: deb
EOF
```

#### 4.2 Trivy vs Grype 对比

| 特性 | Trivy | Grype |
|------|-------|-------|
| 开发者 | Aqua Security | Anchore |
| 扫描范围 | 镜像/文件系统/仓库/配置/密钥 | 镜像/文件系统/SBOM |
| 数据源 | NVD, Red Hat, Debian, Alpine 等 | NVD, 多个发行版安全数据库 |
| SBOM 生成 | 支持 (CycloneDX, SPDX) | 依赖 Syft 生成 SBOM |
| CI/CD 集成 | GitHub Actions, GitLab CI, Jenkins | GitHub Actions, Jenkins |
| 扫描速度 | 快 | 中等 |
| Dockerfile 扫描 | 支持 (misconfiguration) | 不支持 |
| Secret 扫描 | 支持 | 不支持 |
| 推荐场景 | 全能型，CI/CD 首选 | SBOM 驱动的安全扫描 |

---

### 5. 镜像签名

#### 5.1 Cosign 镜像签名

```bash
# 安装 Cosign
# Linux
curl -fsSL https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64 -o /usr/local/bin/cosign
chmod +x /usr/local/bin/cosign

# macOS
brew install cosign

# === 生成密钥对 ===
cosign generate-key-pair
# 生成 cosign.key (私钥) 和 cosign.pub (公钥)
# 安全存储私钥，分发公钥

# === 签名镜像 ===
# 先推送镜像到仓库
docker push registry.example.com/myapp:v1

# 签名
cosign sign --key cosign.key registry.example.com/myapp:v1
# 会提示输入密码保护私钥

# === 验证签名 ===
cosign verify --key cosign.pub registry.example.com/myapp:v1
# 输出:
# The following checks were performed:
#   - The cosign claims were validated
#   - The signatures were verified against the specified public key

# === 无密钥签名 (Keyless Signing) ===
# 使用 Fulcio (免费的短期证书颁发) 和 Rekor (透明日志)
cosign sign registry.example.com/myapp:v1
# 使用 OIDC 身份 (GitHub Actions, Google Cloud 等)
# 不需要管理长期密钥

# 验证 keyless 签名
cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://accounts.google.com \
  registry.example.com/myapp:v1
```

#### 5.2 Docker Content Trust (DCT)

```bash
# 启用 Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# 推送时自动签名
docker push registry.example.com/myapp:v1
# 首次会生成签名密钥

# 拉取时自动验证签名
docker pull registry.example.com/myapp:v1
# 如果签名不匹配，拉取失败

# 查看签名信息
docker trust inspect --pretty registry.example.com/myapp:v1

# 禁用 DCT
export DOCKER_CONTENT_TRUST=0
```

#### 5.3 镜像签名在 CI/CD 中的集成

```yaml
# GitHub Actions: 构建、签名、推送
name: Build, Sign, and Push
on:
  push:
    tags: ['v*']

jobs:
  build-and-sign:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write  # 用于 keyless signing
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Install Cosign
        uses: sigstore/cosign-installer@v3

      - name: Sign image
        run: |
          cosign sign --yes ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Verify signature
        run: |
          cosign verify \
            --certificate-identity-regexp=".*" \
            --certificate-oidc-issuer-regexp=".*" \
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

---

### 6. CI/CD 集成

#### 6.1 完整的 Docker CI/CD 流水线

```
CI/CD 流水线:

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  代码提交  │───▶│  构建镜像  │───▶│  安全扫描  │───▶│  镜像签名  │───▶│  推送仓库  │
│          │    │          │    │          │    │          │    │          │
│ git push │    │ docker   │    │ trivy/   │    │ cosign   │    │ registry │
│          │    │ buildx   │    │ grype    │    │ sign     │    │ push     │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                        │
                                        ▼
                                 ┌──────────┐
                                 │  阈值检查  │
                                 │  CRITICAL │
                                 │  > 0 ?    │
                                 │  BLOCK    │
                                 └──────────┘

┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  拉取镜像  │───▶│  验证签名  │───▶│  部署应用  │───▶│  健康检查  │
│          │    │          │    │          │    │          │
│ pull     │    │ cosign   │    │ k8s/     │    │ readiness│
│          │    │ verify   │    │ compose  │    │ probe    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

#### 6.2 GitHub Actions 完整流水线

```yaml
name: Docker CI/CD Pipeline
on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
      security-events: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload scan results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Block on critical vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          exit-code: '1'
          severity: 'CRITICAL'
          ignore-unfixed: true

      - name: Install Cosign
        if: startsWith(github.ref, 'refs/tags/')
        uses: sigstore/cosign-installer@v3

      - name: Sign image
        if: startsWith(github.ref, 'refs/tags/')
        run: |
          cosign sign --yes ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.ref_name }}

  deploy:
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Deploy to production
        run: |
          echo "Deploying ${{ github.ref_name }} to production..."
          # kubectl set image deployment/myapp app=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.ref_name }}
```

#### 6.3 本地开发中的 Dockerfile 检查

```bash
# 使用 hadolint 检查 Dockerfile 语法和最佳实践
docker run --rm -i hadolint/hadolint < Dockerfile

# 使用 dockle 检查镜像安全
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    goodwithtech/dockle:latest myapp:latest

# 构建时使用 BuildKit 前端检查
# syntax=docker/dockerfile:1
# 启用 BuildKit
DOCKER_BUILDKIT=1 docker build -t myapp:latest .

# 使用 dive 分析镜像层
docker run --rm -it \
    -v /var/run/docker.sock:/var/run/docker.sock \
    wagoodman/dive:latest myapp:latest
```

---

### 7. 综合示例: 生产级 Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

# ============================================================
# 生产级 Python 应用 Dockerfile
# 遵循所有最佳实践: 多阶段构建、安全加固、镜像瘦身
# ============================================================

# --- Stage 1: 依赖安装 ---
FROM python:3.12-slim-bookworm AS deps

# 设置 pip 镜像源 (可选, 国内加速)
# ARG PIP_INDEX_URL=https://pypi.org/simple

WORKDIR /build

# 安装构建依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libpq-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖 (利用缓存)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 2: 生产镜像 ---
FROM python:3.12-slim-bookworm AS production

# OCI 元数据
LABEL org.opencontainers.image.title="Production Python App" \
      org.opencontainers.image.description="Docker best practices example" \
      org.opencontainers.image.vendor="SRE Learning" \
      org.opencontainers.image.source="https://github.com/example/app"

# 安装运行时依赖 (仅必要库)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
        ca-certificates \
        tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone

# 创建非 root 用户
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -s /bin/false -d /app -M appuser

# 创建必要目录
RUN mkdir -p /app /app/logs /tmp/app && \
    chown -R appuser:appuser /app /tmp/app

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=deps --chown=appuser:appuser /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    TMPDIR=/tmp/app

# 复制应用代码
COPY --chown=appuser:appuser . .

# 删除不需要的 setuid/setgid 二进制
RUN find / -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

# 切换用户
USER appuser

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8080/health || exit 1

# 使用 tini 作为 PID 1 (正确处理信号)
STOPSIGNAL SIGTERM
ENTRYPOINT ["tini", "--"]
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--worker-tmp-dir", "/dev/shm", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "app:create_app()"]
```

---

## 💻 实战练习

### 练习 1: 镜像瘦身挑战

**目标:** 将一个未优化的 Dockerfile 镜像从 ~1GB 优化到 ~100MB 以下。

```bash
# 原始 Dockerfile (未优化)
cat > Dockerfile.bloated << 'EOF'
FROM python:3.12
WORKDIR /app
COPY . .
RUN apt-get update
RUN apt-get install -y vim curl wget git
RUN pip install flask gunicorn redis pymysql
RUN pip install pytest black flake8
RUN rm -rf /app/.git
CMD ["python", "app.py"]
EOF

# 构建并检查大小
docker build -f Dockerfile.bloated -t app:bloated .
docker images app:bloated

# 你的任务: 创建优化版本 Dockerfile
# 要求:
# 1. 使用多阶段构建
# 2. 使用 slim/alpine 基础镜像
# 3. 合并 RUN 指令并清理缓存
# 4. 只安装生产依赖
# 5. 使用 .dockerignore

# 验证
docker build -t app:optimized .
docker images app:optimized
# 目标: < 100MB
```

### 练习 2: 安全扫描与修复

**目标:** 使用 Trivy 扫描镜像并修复发现的漏洞。

```bash
# 构建一个包含已知漏洞的镜像
cat > Dockerfile.vulnerable << 'EOF'
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
EOF

docker build -t app:vulnerable .

# 使用 Trivy 扫描
trivy image app:vulnerable

# 你的任务:
# 1. 分析扫描结果中的 CRITICAL 和 HIGH 漏洞
# 2. 更新基础镜像版本
# 3. 更新依赖版本
# 4. 重新构建并验证漏洞已修复

# 验证修复
trivy image --severity CRITICAL app:fixed
# 目标: 0 CRITICAL 漏洞
```

### 练习 3: Dockerfile 安全加固

**目标:** 将一个以 root 运行的 Dockerfile 改为安全加固版本。

```bash
# 原始 Dockerfile (不安全)
cat > Dockerfile.insecure << 'EOF'
FROM node:20
WORKDIR /app
COPY . .
RUN npm install
EXPOSE 3000
CMD ["node", "server.js"]
EOF

# 你的任务: 创建安全加固版本
# 要求:
# 1. 使用非 root 用户
# 2. 使用多阶段构建
# 3. 固定基础镜像版本
# 4. 添加健康检查
# 5. 使用 tini 作为 PID 1
# 6. 添加 .dockerignore
# 7. 设置正确的文件权限

# 验证
docker build -t app:secure .
docker run --rm app:secure whoami  # 应输出 appuser
```

---

## 🎯 面试题精选

### 1. 什么是多阶段构建？为什么它很重要？

**参考答案:**

多阶段构建允许在一个 Dockerfile 中使用多个 `FROM` 指令，每个阶段可以独立构建。最终镜像只包含最后一个阶段的内容。

优势:
- **镜像瘦身**: 构建工具、源码、中间产物不进入最终镜像
- **安全性**: 减少攻击面，不需要编译器和开发工具
- **效率**: 利用 Docker 层缓存，加速构建

例如 Go 应用: golang:1.22 (~800MB) + 源码编译 → scratch (~10MB) + 二进制文件。

### 2. 如何选择合适的基础镜像？

**参考答案:**

按优先级考虑:
1. **安全性**: 选择有持续安全更新的镜像（官方镜像优先）
2. **大小**: 优先选择 slim/alpine/distroless 变体
3. **兼容性**: alpine 使用 musl libc 可能有兼容问题，slim 基于 glibc 兼容性好
4. **固定版本**: 使用具体版本号或 SHA 摘要，避免 latest
5. **组织策略**: 企业可使用内部基础镜像仓库

推荐: Go 用 scratch/distroless，Python/Node.js 用 slim，Java 用 distroless。

### 3. 为什么要在 Dockerfile 中使用非 root 用户？

**参考答案:**

安全原因:
- 容器逃逸漏洞如果以 root 身份运行，攻击者可获得宿主机 root 权限
- 符合最小权限原则，限制容器内进程的能力
- 某些 Kubernetes 安全策略要求 `runAsNonRoot: true`
- 部分合规标准（如 PCI-DSS）要求非特权运行

实现: 创建专用用户/组，设置正确的文件权限，使用 `USER` 指令切换。

### 4. ARG 和 ENV 有什么区别？

**参考答案:**

- **ARG**: 仅在构建时可用（`docker build --build-arg`），运行时不存在。适合传递构建参数如版本号、构建日期。
- **ENV**: 构建时和运行时都可用，会成为容器的环境变量。适合设置应用配置默认值。
- ARG 定义的变量如果在 FROM 之前，可以在 FROM 中使用（多阶段构建选择基础镜像）。
- ENV 会覆盖 ARG 同名变量的值。

### 5. Trivy 和 Grype 有什么区别？应该如何选择？

**参考答案:**

两者都是开源镜像扫描工具:
- **Trivy** (Aqua Security): 功能更全面，支持镜像/文件系统/仓库/配置/密钥扫描，CI/CD 集成成熟
- **Grype** (Anchore): 与 Syft 配合生成 SBOM 后扫描，SBOM 驱动的安全管理

选择建议:
- CI/CD 环境推荐 Trivy（功能全面、速度快、集成好）
- 需要 SBOM 管理的场景推荐 Grype + Syft
- 生产环境建议同时使用两种工具交叉验证

### 6. 什么是镜像签名？为什么需要它？

**参考答案:**

镜像签名通过加密技术验证镜像的来源和完整性:
- **来源验证**: 确认镜像由可信方构建和推送
- **完整性验证**: 确认镜像在传输过程中未被篡改
- **不可否认性**: 签名者无法否认签名行为

工具:
- **Cosign** (Sigstore): 现代无密钥签名方案，与 OIDC 集成
- **Docker Content Trust**: Docker 原生签名方案
- **Notary**: CNCF 项目，DCT 的底层实现

### 7. .dockerignore 文件的作用是什么？

**参考答案:**

.dockerignore 类似 .gitignore，用于排除发送到 Docker 构建上下文的文件:
- **安全性**: 排除 .env、密钥文件、.git 目录
- **性能**: 减少构建上下文大小，加速构建
- **正确性**: 避免本地依赖（node_modules）进入容器
- **缓存效率**: 减少不必要的缓存失效

必须排除: .git、node_modules、.env、*.key、Dockerfile、docker-compose*.yml。

### 8. 如何减少 Docker 构建时间？

**参考答案:**

1. **层缓存**: 将不常变化的指令放在前面（依赖安装在代码复制之前）
2. **.dockerignore**: 排除不必要的文件减少上下文
3. **BuildKit**: 使用 `--mount=type=cache` 缓存包管理器缓存
4. **多阶段构建**: 依赖层和代码层分离
5. **并行构建**: BuildKit 支持并行执行无依赖的层
6. **精简依赖**: 只安装必要的包
7. **预构建基础镜像**: 维护包含常用依赖的内部基础镜像

### 9. 什么是 BuildKit？它比传统构建有什么优势？

**参考答案:**

BuildKit 是 Docker 的下一代构建引擎:
- **并行构建**: 自动分析依赖关系，并行执行独立步骤
- **缓存优化**: 支持挂载缓存（`--mount=type=cache`）、缓存导入导出
- **安全**: 支持 `--secret` 安全传递敏感信息，不保存在镜像层
- **输出格式**: 支持多种输出（镜像、tar、本地目录）
- **前端扩展**: 支持自定义 Dockerfile 语法

启用: `DOCKER_BUILDKIT=1 docker build` 或 Docker 23.0+ 默认启用。

### 10. 生产环境 Dockerfile 的关键检查项有哪些？

**参考答案:**

1. 使用多阶段构建
2. 使用 slim/alpine/distroless 基础镜像
3. 固定基础镜像版本（非 latest）
4. 合并 RUN 指令并清理缓存
5. 使用 .dockerignore
6. 创建并使用非 root 用户
7. 不在 ENV/ARG 中存储敏感信息
8. 使用 BuildKit secrets
9. 添加 HEALTHCHECK
10. 使用 tini/dumb-init 作为 PID 1
11. 设置 STOPSIGNAL
12. 添加 OCI 标签
13. 删除不必要的 setuid/setgid 二进制
14. 镜像扫描无 CRITICAL 漏洞

---

## 📚 深入阅读

- [Dockerfile 最佳实践 (官方)](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [BuildKit 文档](https://github.com/moby/buildkit)
- [Trivy 文档](https://aquasecurity.github.io/trivy/)
- [Grype 文档](https://github.com/anchore/grype)
- [Cosign 文档](https://docs.sigstore.dev/cosign/overview/)
- [Docker Content Trust](https://docs.docker.com/engine/security/trust/)
- [Hadolint - Dockerfile linter](https://github.com/hadolint/hadolint)
- [Dive - 镜像层分析](https://github.com/wagoodman/dive)
- [Chainguard Images](https://www.chainguard.dev/chainguard-images)
- [Google Distroless Images](https://github.com/GoogleContainerTools/distroless)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)

---

## ✅ 自检清单

- [ ] 理解 Docker 镜像层机制及其对构建缓存的影响
- [ ] 能使用多阶段构建将镜像体积减少 80% 以上
- [ ] 掌握 .dockerignore 的配置
- [ ] 能为不同语言选择最优基础镜像
- [ ] 理解非 root 用户运行的安全意义和实现方法
- [ ] 能使用 Trivy 扫描镜像并解读结果
- [ ] 能使用 Grype 进行 SBOM 驱动的安全扫描
- [ ] 理解 Cosign 镜像签名的原理和使用方法
- [ ] 能将安全扫描集成到 CI/CD 流水线
- [ ] 理解 BuildKit 的高级特性（secrets、cache mount）
- [ ] 掌握 Dockerfile 安全加固的所有关键措施
- [ ] 能编写生产级的 Dockerfile
