# Day 149: GitLab CI

> 📅 日期：2026-05-07
> 📖 学习主题：.gitlab-ci.yml 语法、Stages/Jobs、Runner、Variables、Artifacts、Cache、环境、Review Apps、Auto DevOps
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 147（CI/CD 概念与 GitOps）、Day 148（GitHub Actions）

---

## 🎯 学习目标

- 掌握 `.gitlab-ci.yml` 完整语法和核心组件
- 理解 Stages、Jobs、Keywords 的层级关系
- 掌握 GitLab Runner 的类型、配置和注册
- 能使用 Variables、Artifacts、Cache 优化流水线
- 理解 GitLab 环境管理和 Review Apps
- 掌握 Auto DevOps 的原理和自定义

---

## 📖 核心知识点

### 1. GitLab CI/CD 架构

```
GitLab CI/CD 整体架构：

┌──────────────────────────────────────────────────────────────┐
│                    GitLab CI/CD 架构                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  GitLab Server                        │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │  Git     │  │ CI/CD    │  │ Registry │           │   │
│  │  │  Repo    │  │ Engine   │  │ (镜像)   │           │   │
│  │  └────┬─────┘  └────┬─────┘  └──────────┘           │   │
│  │       │             │                                │   │
│  │       │     ┌───────┴───────┐                        │   │
│  │       │     │ Pipeline      │                        │   │
│  │       │     │ Coordinator   │                        │   │
│  │       │     └───────┬───────┘                        │   │
│  │       │             │                                │   │
│  │       │    ┌────────┼────────┐                       │   │
│  │       │    │        │        │                       │   │
│  └───────┼────┼────────┼────────┼───────────────────────┘   │
│          │    │        │        │                            │
│          ▼    ▼        ▼        ▼                            │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐               │
│  │Runner 1│ │Runner 2│ │Runner 3│ │Runner N│               │
│  │(Shell) │ │(Docker)│ │(Docker)│ │(K8s)   │               │
│  │        │ │        │ │        │ │        │               │
│  │ Shared │ │ Project│ │ Group  │ │Custom  │               │
│  │ Runner │ │ Runner │ │ Runner │ │ Runner │               │
│  └────────┘ └────────┘ └────────┘ └────────┘               │
│                                                              │
│  Runner 执行器类型：                                         │
│  • Shell: 直接在主机执行                                     │
│  • Docker: 在容器中执行（推荐）                               │
│  • Docker Machine: 自动伸缩 Runner                          │
│  • Kubernetes: 在 K8s Pod 中执行                             │
│  • VirtualBox/Parallels: 虚拟机隔离                          │
└──────────────────────────────────────────────────────────────┘
```

### 2. .gitlab-ci.yml 基础语法

#### 2.1 文件结构总览

```yaml
# .gitlab-ci.yml 完整结构

# ── 全局配置 ──────────────────────────────────────────────
# 指定 Docker 镜像
image: node:20-alpine

# 指定自定义镜像仓库
# image: name: my-registry.com/my-image:latest

# 默认执行器
# default:
#   image: node:20-alpine
#   before_script:
#     - npm ci

# 全局变量
variables:
  NODE_ENV: production
  npm_config_cache: "$CI_PROJECT_DIR/.npm"

# 全局 before_script（每个 Job 执行前）
before_script:
  - echo "Pipeline ID: $CI_PIPELINE_ID"
  - echo "Commit: $CI_COMMIT_SHA"

# 全局 after_script（每个 Job 执行后，即使失败）
after_script:
  - echo "Job finished"

# ── Stages 定义 ───────────────────────────────────────────
# 同一 Stage 的 Job 并行执行，不同 Stage 顺序执行
stages:
  - build
  - test
  - security
  - deploy

# ── 隐藏 Job（以 . 开头，不会被执行） ─────────────────────
.job_template: &job_template
  image: node:20-alpine
  before_script:
    - npm ci --cache .npm --prefer-offline

# ── Jobs 定义 ─────────────────────────────────────────────
build:
  stage: build
  script:
    - npm run build
  artifacts:
    paths:
      - dist/

unit_test:
  <<: *job_template                # YAML 锚点引用
  stage: test
  script:
    - npm test
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'

lint:
  <<: *job_template
  stage: test
  script:
    - npm run lint
  allow_failure: true              # 失败不阻塞流水线

deploy_staging:
  stage: deploy
  script:
    - ./deploy.sh staging
  environment:
    name: staging
    url: https://staging.example.com
  only:
    - main

deploy_production:
  stage: deploy
  script:
    - ./deploy.sh production
  environment:
    name: production
    url: https://example.com
  when: manual                     # 手动触发
  only:
    - main
```

#### 2.2 Job Keywords 详解

```yaml
# ── Job Keywords 完整参考 ─────────────────────────────────

job_name:
  # 基础配置
  stage: test                      # 所属阶段
  image: python:3.12               # Job 级别镜像（覆盖全局）
  tags:
    - docker                       # Runner 标签匹配
    - linux

  # 脚本执行
  before_script:                   # 主脚本前执行
    - echo "Preparing..."
  script:                          # 主脚本（必需）
    - echo "Running tests"
    - pytest
  after_script:                    # 主脚本后执行（即使失败）
    - echo "Cleanup..."

  # 变量
  variables:
    DB_HOST: localhost
    DB_PORT: "5432"

  # 条件控制
  rules:                           # 推荐方式（替代 only/except）
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: always
    - if: $CI_COMMIT_BRANCH == "main"
      when: always
    - if: $CI_COMMIT_TAG
      when: always
    - when: never

  # 旧方式（仍可用）
  only:
    - main
    - tags
  except:
    - schedules

  # 执行控制
  when: on_success                 # on_success | on_failure | always | manual | delayed | never
  allow_failure: false             # 失败是否阻塞流水线
  timeout: 30m                     # 超时时间
  retry:                           # 重试策略
    max: 2
    when:
      - runner_system_failure
      - stuck_or_timeout_failure

  # 依赖与产物
  needs:                           # DAG 依赖（可跨 Stage）
    - build
    - lint
  dependencies:                    # 从哪些 Job 获取 artifacts
    - build
  artifacts:
    name: "test-results-$CI_COMMIT_SHA"
    paths:
      - test-results/
      - coverage/
    exclude:
      - "*.tmp"
    expire_in: 1 week
    reports:
      junit: test-results/junit.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura.xml

  # 缓存
  cache:
    key:
      files:
        - package-lock.json        # 基于文件内容生成 key
      prefix: $CI_JOB_NAME
    paths:
      - node_modules/
      - .npm/
    policy: pull-push               # pull | push | pull-push

  # 服务容器
  services:
    - name: postgres:15
      alias: db                    # 主机名别名
      variables:
        POSTGRES_DB: test
        POSTGRES_PASSWORD: secret

  # 并行（矩阵构建）
  parallel: 3                      # 并行运行 3 个实例

  # 覆盖默认行为
  interruptible: true              # 可被新 Pipeline 中断

  # 资源限制（Kubernetes Runner）
  resource_group: production       # 资源组（互斥访问）

  # 产物发布（Release）
  release:
    tag_name: v$CI_COMMIT_TAG
    description: "Release $CI_COMMIT_TAG"
    assets:
      links:
        - name: "Binary"
          url: "https://example.com/binaries/$CI_COMMIT_TAG"
```

#### 2.3 Stages 与 DAG

```
Stages 顺序执行 vs DAG 并行执行：

┌──────────────────────────────────────────────────────────────┐
│                    传统 Stages 模型                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Stage 1: Build                                              │
│  ┌──────┐ ┌──────┐                                          │
│  │Job A │ │Job B │  (同 Stage 并行)                          │
│  └──┬───┘ └──┬───┘                                          │
│     │        │                                               │
│     ▼        ▼                                               │
│  Stage 2: Test                                               │
│  ┌──────┐ ┌──────┐                                          │
│  │Job C │ │Job D │  (等待 Stage 1 完成)                      │
│  └──┬───┘ └──┬───┘                                          │
│     │        │                                               │
│     ▼        ▼                                               │
│  Stage 3: Deploy                                             │
│  ┌──────┐                                                    │
│  │Job E │  (等待 Stage 2 完成)                                │
│  └──────┘                                                    │
│                                                              │
│  问题: Job D 不依赖 Job A，但必须等待 Stage 1 全部完成         │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    DAG 模型（needs 关键字）                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────┐ ┌──────┐                                          │
│  │Job A │ │Job B │  (立即并行)                               │
│  └──┬───┘ └──┬───┘                                          │
│     │        │                                               │
│     │        ▼                                               │
│     │     ┌──────┐                                           │
│     │     │Job D │  (只等 Job B)                              │
│     │     └──────┘                                           │
│     │                                                        │
│     ▼                                                        │
│  ┌──────┐                                                    │
│  │Job C │  (只等 Job A)                                      │
│  └──┬───┘                                                    │
│     │                                                        │
│     ▼                                                        │
│  ┌──────┐                                                    │
│  │Job E │  (等 Job C 和 Job D)                               │
│  └──────┘                                                    │
│                                                              │
│  优势: Job D 不再等待 Job A，整体执行时间缩短                  │
└──────────────────────────────────────────────────────────────┘
```

DAG 配置示例：

```yaml
stages:
  - build
  - test
  - deploy

build_frontend:
  stage: build
  script: npm run build:frontend
  artifacts:
    paths: [dist/frontend]

build_backend:
  stage: build
  script: go build -o app ./cmd/server
  artifacts:
    paths: [app]

test_frontend:
  stage: test
  needs: [build_frontend]          # 只依赖前端构建
  script: npm test

test_backend:
  stage: test
  needs: [build_backend]           # 只依赖后端构建
  script: go test ./...

deploy:
  stage: deploy
  needs: [test_frontend, test_backend]  # 依赖所有测试
  script: ./deploy.sh

# 使用 needs:project 跨项目依赖
deploy_docs:
  stage: deploy
  needs:
    - project: org/docs
      job: build
      ref: main
      artifacts: true
  script: cp ../docs/dist/* public/
```

### 3. GitLab Runner

#### 3.1 Runner 类型与注册

```
GitLab Runner 类型：

┌──────────────────────────────────────────────────────────────┐
│                    GitLab Runner 类型                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Shared Runner（共享 Runner）                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • 由 GitLab 管理员配置                                │   │
│  │ • 所有项目可用                                        │   │
│  │ • 有免费额度限制（GitLab.com）                        │   │
│  │ • 适合通用任务                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  2. Group Runner（组 Runner）                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • 绑定到 GitLab Group                                │   │
│  │ • Group 下所有项目可用                                │   │
│  │ • 适合团队专用                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  3. Project Runner（项目 Runner）                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • 绑定到特定项目                                      │   │
│  │ • 只有该项目可用                                      │   │
│  │ • 适合特殊需求（GPU、特定环境）                        │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Runner 注册与配置：

```toml
# /etc/gitlab-runner/config.toml

concurrent = 10                    # 最大并发 Job 数
check_interval = 3                 # 检查新 Job 的间隔（秒）

[[runners]]
  name = "docker-runner-1"
  url = "https://gitlab.com/"
  token = "xxxxx"
  executor = "docker"

  [runners.docker]
    tls_verify = false
    image = "alpine:latest"        # 默认镜像
    privileged = false             # 是否特权模式
    disable_entrypoint_overwrite = false
    oom_kill_disable = false
    disable_cache = false
    volumes = ["/cache"]           # 缓存卷
    shm_size = 0                   # 共享内存大小
    pull_policy = ["if-not-present"]  # 镜像拉取策略

    # 安全配置
    allowed_images = ["ruby:*", "python:*", "node:*"]
    allowed_services = ["postgres:*", "redis:*"]

  [runners.cache]
    Type = "s3"                    # 缓存后端
    Shared = true
    [runners.cache.s3]
      ServerAddress = "s3.amazonaws.com"
      BucketName = "gitlab-runner-cache"
      BucketLocation = "us-east-1"

  # Kubernetes Runner 配置
  # [runners.kubernetes]
  #   namespace = "gitlab-ci"
  #   image = "alpine:latest"
  #   cpu_request = "500m"
  #   memory_request = "1Gi"
  #   cpu_limit = "2"
  #   memory_limit = "4Gi"
```

```bash
# 注册 Runner
gitlab-runner register \
  --non-interactive \
  --url "https://gitlab.com/" \
  --token "PROJECT_TOKEN" \
  --executor "docker" \
  --docker-image "alpine:latest" \
  --description "my-docker-runner" \
  --tag-list "docker,linux" \
  --run-untagged="true" \
  --locked="false"

# 验证 Runner
gitlab-runner verify

# 运行 Runner
gitlab-runner run

# 作为服务安装
gitlab-runner install --user=gitlab-runner --working-directory=/home/gitlab-runner
gitlab-runner start
```

### 4. Variables 变量

#### 4.1 变量层级与类型

```
GitLab CI/CD 变量层级：

┌──────────────────────────────────────────────────────────────┐
│                    变量层级（优先级从高到低）                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 手动触发时的变量（Pipeline 手动运行时输入）                │
│  2. Job 级别 variables                                       │
│  3. Pipeline 级别 variables                                  │
│  4. Project Variables（Settings > CI/CD > Variables）         │
│  5. Group Variables                                         │
│  6. Instance Variables（管理员设置）                          │
│  7. .gitlab-ci.yml 中的 variables                            │
│  8. 预定义变量（CI_COMMIT_SHA 等）                            │
│                                                              │
│  变量保护：                                                   │
│  • Protected: 只在受保护分支/标签上可用                        │
│  • Masked: 在日志中被遮罩（****）                             │
│  • Expanded: 支持变量引用 $OTHER_VAR                         │
│  • Raw: 不展开变量                                           │
│                                                              │
│  变量类型：                                                   │
│  • Variable: 直接值                                          │
│  • File: 值写入临时文件，变量名成为文件路径                    │
└──────────────────────────────────────────────────────────────┘
```

#### 4.2 变量使用

```yaml
# .gitlab-ci.yml 中的变量

# 全局变量
variables:
  # 普通变量
  APP_NAME: "my-application"
  VERSION: "1.0.0"

  # 变量引用
  IMAGE_TAG: "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA"
  FULL_NAME: "$APP_NAME-$VERSION"

  # 多行变量
  DOCKER_OPTIONS: |
    --build-arg NODE_ENV=production
    --label version=$VERSION

  # 文件类型变量（用于证书等）
  # 在 UI 中设置: Type = File, Key = KUBE_CONFIG, Value = <kubeconfig内容>
  # Job 中: KUBE_CONFIG 变量包含文件路径

  # 动态变量（使用规则）
  DEPLOY_ENV: "staging"

# Job 级别变量（覆盖全局）
test:
  stage: test
  variables:
    TEST_ENV: "ci"
    DATABASE_URL: "postgresql://postgres:secret@postgres:5432/test"
  script:
    - echo "App: $APP_NAME"         # 引用全局变量
    - echo "Test env: $TEST_ENV"     # 引用 Job 变量
    - echo "Image: $IMAGE_TAG"       # 变量链式引用
    - echo "File content:"           # 文件变量
    - cat $KUBE_CONFIG

# 规则中使用变量
deploy:
  stage: deploy
  variables:
    DEPLOY_ENV: "production"
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      variables:
        DEPLOY_ENV: "production"     # 规则级别变量覆盖
    - if: $CI_COMMIT_BRANCH == "develop"
      variables:
        DEPLOY_ENV: "staging"
  script:
    - echo "Deploying to $DEPLOY_ENV"
```

#### 4.3 预定义变量

```yaml
# 常用预定义变量
debug_job:
  script:
    # Pipeline 信息
    - echo "Pipeline ID: $CI_PIPELINE_ID"
    - echo "Pipeline URL: $CI_PIPELINE_URL"
    - echo "Pipeline Source: $CI_PIPELINE_SOURCE"

    # Commit 信息
    - echo "Commit SHA: $CI_COMMIT_SHA"
    - echo "Commit Short SHA: $CI_COMMIT_SHORT_SHA"
    - echo "Commit Branch: $CI_COMMIT_BRANCH"
    - echo "Commit Tag: $CI_COMMIT_TAG"
    - echo "Commit Message: $CI_COMMIT_MESSAGE"
    - echo "Commit Author: $CI_COMMIT_AUTHOR"

    # 项目信息
    - echo "Project: $CI_PROJECT_NAME"
    - echo "Project Path: $CI_PROJECT_PATH"
    - echo "Project URL: $CI_PROJECT_URL"
    - echo "Default Branch: $CI_DEFAULT_BRANCH"

    # Runner 信息
    - echo "Runner ID: $CI_RUNNER_ID"
    - echo "Runner Description: $CI_RUNNER_DESCRIPTION"

    # Job 信息
    - echo "Job ID: $CI_JOB_ID"
    - echo "Job Name: $CI_JOB_NAME"
    - echo "Job Stage: $CI_JOB_STAGE"
    - echo "Job URL: $CI_JOB_URL"

    # Registry
    - echo "Registry: $CI_REGISTRY"
    - echo "Registry Image: $CI_REGISTRY_IMAGE"

    # Merge Request
    - echo "MR IID: $CI_MERGE_REQUEST_IID"
    - echo "MR Source Branch: $CI_MERGE_REQUEST_SOURCE_BRANCH_NAME"
    - echo "MR Target Branch: $CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
```

### 5. Artifacts 产物

#### 5.1 Artifacts 配置

```yaml
# 基础 Artifacts
build:
  stage: build
  script:
    - npm run build
    - npm run generate-docs
  artifacts:
    paths:
      - dist/                       # 目录
      - build/*.jar                 # 通配符
      - reports/coverage.xml        # 单文件
    exclude:
      - dist/**/*.map               # 排除 source map
    expire_in: 30 days              # 过期时间

# 跨 Job 传递 Artifacts
test:
  stage: test
  dependencies:
    - build                         # 只获取 build 的 artifacts
  script:
    - ls dist/                      # 可以访问 build 的产物

# 禁用 Artifacts 传递
lint:
  stage: test
  dependencies: []                  # 不获取任何 artifacts
  script:
    - npm run lint

# 测试报告 Artifacts
test_with_reports:
  stage: test
  script:
    - npm test -- --reporter=junit --output-file=junit.xml
    - npm test -- --coverage
  artifacts:
    when: always                    # 即使失败也收集
    reports:
      junit: junit.xml              # JUnit 测试报告
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura.xml
      codequality:
        - gl-code-quality-report.json
      sast:
        - gl-sast-report.json
      dependency_scanning:
        - gl-dependency-scanning-report.json
      terraform:                    # Terraform 状态
        - tfplan.json
    paths:
      - coverage/

# Release Artifacts
release_job:
  stage: release
  script:
    - make build-all
  artifacts:
    name: "app-$CI_COMMIT_TAG"
    paths:
      - binaries/
  release:
    tag_name: $CI_COMMIT_TAG
    description: "Release $CI_COMMIT_TAG"
    assets:
      links:
        - name: "Linux Binary"
          url: "https://$CI_PROJECT_URL/-/jobs/$CI_JOB_ID/artifacts/raw/binaries/app-linux-amd64"
        - name: "macOS Binary"
          url: "https://$CI_PROJECT_URL/-/jobs/$CI_JOB_ID/artifacts/raw/binaries/app-darwin-amd64"
```

### 6. Cache 缓存

#### 6.1 Cache vs Artifacts

```
Cache vs Artifacts 对比：

┌──────────────────┬────────────────────┬────────────────────┐
│                  │      Cache         │     Artifacts       │
├──────────────────┼────────────────────┼────────────────────┤
│ 用途             │ 加速构建（依赖缓存）│ Job 间传递产物       │
│ 存储位置         │ Runner 缓存存储    │ GitLab 服务器       │
│ 可靠性           │ 可能丢失           │ 可靠存储             │
│ 跨 Pipeline      │ ✅ 是             │ ❌ 否（同 Pipeline） │
│ 跨 Job           │ ✅ 是（需配置）    │ ✅ 是（需配置）      │
│ 典型内容         │ node_modules,.npm  │ build/, reports/    │
│ 大小限制         │ 无硬性限制         │ 可配置               │
│ 过期             │ 未访问 2 周后清除  │ 按 expire_in 设置   │
└──────────────────┴────────────────────┴────────────────────┘
```

#### 6.2 Cache 高级配置

```yaml
# 全局缓存配置
default:
  cache:
    key: ${CI_COMMIT_REF_SLUG}      # 基于分支名
    paths:
      - node_modules/
      - .npm/

# 基于文件内容的缓存 key（推荐）
install:
  stage: .pre
  script: npm ci
  cache:
    key:
      files:
        - package-lock.json          # lock 文件变化时更新缓存
      prefix: $CI_JOB_NAME           # Job 名称前缀
    paths:
      - node_modules/
      - .npm/
    policy: push                     # 只写入缓存

test:
  stage: test
  script: npm test
  cache:
    key:
      files:
        - package-lock.json
      prefix: $CI_JOB_NAME
    paths:
      - node_modules/
    policy: pull                     # 只读取缓存

# 多缓存配置
build:
  stage: build
  script: npm run build
  cache:
    - key: deps-$CI_COMMIT_REF_SLUG
      paths:
        - node_modules/
      policy: pull
    - key: build-$CI_COMMIT_REF_SLUG
      paths:
        - dist/
      policy: push

# Go 缓存
go_build:
  image: golang:1.22
  variables:
    GOPATH: "$CI_PROJECT_DIR/.go"
  cache:
    key: go-$CI_COMMIT_REF_SLUG
    paths:
      - .go/pkg/mod/                 # Go modules
      - .cache/go-build/             # Go build cache

# Python 缓存
python_test:
  image: python:3.12
  variables:
    PIP_CACHE_DIR: "$CI_PROJECT_DIR/.pip-cache"
  cache:
    key: python-$CI_COMMIT_REF_SLUG
    paths:
      - .pip-cache/

# Maven 缓存
java_build:
  image: maven:3.9-eclipse-temurin-21
  cache:
    key: maven-$CI_COMMIT_REF_SLUG
    paths:
      - .m2/repository/
```

### 7. 环境与 Review Apps

#### 7.1 环境管理

```yaml
# 环境定义
deploy_staging:
  stage: deploy
  script:
    - kubectl apply -f k8s/staging/
  environment:
    name: staging
    url: https://staging.example.com
    on_stop: stop_staging            # 关联停止 Job
    auto_stop_in: 1 week             # 自动停止时间
    deployment_tier: staging          # 环境层级

# 停止环境
stop_staging:
  stage: deploy
  script:
    - kubectl delete -f k8s/staging/
  environment:
    name: staging
    action: stop
  when: manual

# 动态环境（Review Apps）
review_app:
  stage: deploy
  script:
    - NAMESPACE="review-$CI_COMMIT_REF_SLUG"
    - kubectl create namespace $NAMESPACE || true
    - kubectl apply -f k8s/review/ -n $NAMESPACE
  environment:
    name: review/$CI_COMMIT_REF_SLUG
    url: https://$CI_COMMIT_REF_SLUG.review.example.com
    on_stop: stop_review_app
    auto_stop_in: 2 days

stop_review_app:
  stage: deploy
  script:
    - NAMESPACE="review-$CI_COMMIT_REF_SLUG"
    - kubectl delete namespace $NAMESPACE
  environment:
    name: review/$CI_COMMIT_REF_SLUG
    action: stop
```

#### 7.2 Review Apps 完整示例

```yaml
# 完整的 Review Apps 配置

stages:
  - build
  - test
  - deploy
  - cleanup

variables:
  REVIEW_DOMAIN: "review.example.com"

build_review:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE/review:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE/review:$CI_COMMIT_SHA
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

test_review:
  stage: test
  needs: [build_review]
  script:
    - npm test

deploy_review:
  stage: deploy
  needs: [test_review]
  script:
    - |
      cat <<EOF | kubectl apply -f -
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: review-$CI_COMMIT_REF_SLUG
        namespace: review-apps
      spec:
        replicas: 1
        selector:
          matchLabels:
            app: review-$CI_COMMIT_REF_SLUG
        template:
          metadata:
            labels:
              app: review-$CI_COMMIT_REF_SLUG
          spec:
            containers:
              - name: app
                image: $CI_REGISTRY_IMAGE/review:$CI_COMMIT_SHA
                ports:
                  - containerPort: 8080
      ---
      apiVersion: v1
      kind: Service
      metadata:
        name: review-$CI_COMMIT_REF_SLUG
        namespace: review-apps
      spec:
        selector:
          app: review-$CI_COMMIT_REF_SLUG
        ports:
          - port: 80
            targetPort: 8080
      ---
      apiVersion: networking.k8s.io/v1
      kind: Ingress
      metadata:
        name: review-$CI_COMMIT_REF_SLUG
        namespace: review-apps
      spec:
        rules:
          - host: $CI_COMMIT_REF_SLUG.$REVIEW_DOMAIN
            http:
              paths:
                - path: /
                  pathType: Prefix
                  backend:
                    service:
                      name: review-$CI_COMMIT_REF_SLUG
                      port:
                        number: 80
      EOF
  environment:
    name: review/$CI_COMMIT_REF_SLUG
    url: https://$CI_COMMIT_REF_SLUG.$REVIEW_DOMAIN
    on_stop: stop_review
    auto_stop_in: 3 days
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

stop_review:
  stage: cleanup
  script:
    - kubectl delete namespace review-apps --ignore-not-found
  environment:
    name: review/$CI_COMMIT_REF_SLUG
    action: stop
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: manual
```

### 8. Auto DevOps

#### 8.1 Auto DevOps 概述

```
Auto DevOps 流水线：

┌──────────────────────────────────────────────────────────────┐
│                    Auto DevOps 流水线                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐         │
│  │Build │─►│ Test │─►│ Code │─►│Review│─►│ Deploy│         │
│  │      │  │      │  │ Qlty │  │ App  │  │      │         │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘         │
│     │         │         │         │         │               │
│     │         │         │         │         │               │
│  Docker    单元测试   SAST     MR 环境    Staging            │
│  Build     集成测试   DAST     预览 URL   Production         │
│  Push      覆盖率    依赖扫描              (手动)            │
│                      密钥扫描                               │
│                                                              │
│  Auto DevOps 自动检测：                                      │
│  • 语言和框架                                                │
│  • 构建工具                                                  │
│  • 测试框架                                                  │
│  • 容器化                                                    │
│                                                              │
│  支持的语言：                                                │
│  • Java (Maven/Gradle)                                      │
│  • Node.js (npm/yarn)                                       │
│  • Python (pip/poetry)                                      │
│  • Ruby (Bundler)                                           │
│  • Go                                                        │
│  • PHP (Composer)                                           │
│  • .NET                                                     │
│  • Rust (Cargo)                                             │
└──────────────────────────────────────────────────────────────┘
```

#### 8.2 自定义 Auto DevOps

```yaml
# .gitlab-ci.yml 覆盖 Auto DevOps 默认行为

# 禁用 Auto DevOps 的特定 Job
test:
  variables:
    DISABLE_DATABASE_INIT: "true"    # 禁用数据库初始化

# 自定义构建阶段
build:
  stage: build
  script:
    - docker build --build-arg NODE_ENV=production -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# 覆盖部署配置
production:
  variables:
    K8S_NAMESPACE: "production"
    HELM_VALUES: |
      replicas: 3
      resources:
        limits:
          cpu: "2"
          memory: 4Gi
```

### 9. 高级特性

#### 9.1 include 与模板

```yaml
# 使用 include 引入外部配置

# 引入模板
include:
  # GitLab 官方模板
  - template: Security/SAST.gitlab-ci.yml
  - template: Security/Dependency-Scanning.gitlab-ci.yml
  - template: Security/Secret-Detection.gitlab-ci.yml

  # 同项目文件
  - local: .gitlab/ci/build.yml
  - local: .gitlab/ci/deploy.yml

  # 其他项目文件
  - project: org/ci-templates
    ref: main
    file: /templates/go.yml

  # 远程 URL
  - remote: https://example.com/ci/template.yml

# .gitlab/ci/build.yml
.build_template:
  image: golang:1.22
  cache:
    key: go-$CI_COMMIT_REF_SLUG
    paths:
      - .go/pkg/mod/
  before_script:
    - go mod download
```

#### 9.2 extends 与锚点

```yaml
# 使用 extends（推荐，比锚点更清晰）
.base_job:
  image: golang:1.22
  before_script:
    - go mod download
  cache:
    key: go-$CI_COMMIT_REF_SLUG
    paths:
      - .go/pkg/mod/

test:
  extends: .base_job
  stage: test
  script:
    - go test ./...
  coverage: '/total:\s+\(statements\)\s+(\d+\.\d+)%/'

build:
  extends: .base_job
  stage: build
  script:
    - go build -o app ./cmd/server
  artifacts:
    paths:
      - app

# 多重继承（后面的覆盖前面的）
.integration_test:
  extends: .base_job
  services:
    - postgres:15
    - redis:7

api_test:
  extends: .integration_test
  stage: test
  script:
    - go test -tags=integration ./...
  variables:
    DATABASE_URL: "postgresql://postgres:secret@postgres:5432/test"
```

#### 9.3 Pipeline 类型

```yaml
# Merge Request Pipeline（推荐）
# 只在 MR 上运行
test:
  stage: test
  script: npm test
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

# Branch Pipeline
# 在分支 push 时运行
build:
  stage: build
  script: npm run build
  rules:
    - if: $CI_COMMIT_BRANCH

# Tag Pipeline
# 在创建标签时运行
release:
  stage: release
  script: make release
  rules:
    - if: $CI_COMMIT_TAG

# Scheduled Pipeline
# 定时触发
nightly_test:
  stage: test
  script: npm run test:nightly
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"

# Parent-Child Pipeline
# 父 Pipeline 触发子 Pipeline
trigger_child:
  stage: trigger
  trigger:
    include: child-pipeline.yml
    strategy: depend                # 等待子 Pipeline 完成
  rules:
    - if: $CI_COMMIT_BRANCH == "main"

# Multi-Project Pipeline
trigger_other:
  stage: trigger
  trigger:
    project: org/other-repo
    branch: main
    strategy: depend
```

---

## 💻 实战练习

### 练习 1：编写完整 CI/CD 流水线

**目标**：为一个 Python Flask 应用编写完整的 GitLab CI/CD 流水线

**步骤**：

1. 创建 `.gitlab-ci.yml`：
   - `.pre` 阶段：依赖安装（带缓存）
   - `test` 阶段：单元测试（带覆盖率报告）、lint
   - `build` 阶段：Docker 镜像构建并推送到 GitLab Registry
   - `deploy` 阶段：部署到 staging（自动）和 production（手动）

2. 配置变量（Settings > CI/CD > Variables）：
   - `STAGING_HOST`
   - `PRODUCTION_HOST`
   - `SSH_PRIVATE_KEY`（File 类型，Protected）

3. 使用 DAG 优化流水线执行时间

**验证**：Push 代码后观察流水线执行，确认缓存生效、覆盖率报告显示

### 练习 2：配置 Review Apps

**目标**：为 MR 自动创建预览环境

**步骤**：

1. 创建 Review App 部署脚本
2. 配置动态环境（使用 `$CI_COMMIT_REF_SLUG`）
3. 配置自动停止（`auto_stop_in`）
4. 在 MR 描述中显示预览 URL

**验证**：创建 MR 后自动部署 Review App，MR 合并后自动清理

### 练习 3：故障排查 - Runner 问题

**场景**：Pipeline 卡在 pending 状态

**排查步骤**：

1. 检查 Runner 状态：
```bash
gitlab-runner verify
gitlab-runner status
```

2. 检查 Runner 日志：
```bash
journalctl -u gitlab-runner -f
```

3. 常见原因：
   - Runner 离线或未注册
   - tags 不匹配
   - Runner 并发数已满
   - 镜像拉取失败
   - Runner 版本过旧

4. 检查 Runner 配置：
```bash
cat /etc/gitlab-runner/config.toml
```

**验证**：修复后 Pipeline 正常运行

---

## 🎯 面试题精选

### 1. GitLab CI 中 stages 和 needs 的区别是什么？

**参考答案**：
- `stages`：定义 Job 的执行顺序，同 Stage 并行，不同 Stage 顺序执行。Job 必须等待前面所有 Stage 完成。
- `needs`：定义 Job 的依赖关系（DAG 模式），可以跨 Stage 依赖，实现更灵活的并行执行。

使用 `needs` 可以显著缩短 Pipeline 执行时间，因为它允许不相关的 Job 提前执行。

### 2. Cache 和 Artifacts 有什么区别？

**参考答案**：
- `Cache`：用于加速构建，存储依赖等可再生内容。可能丢失，跨 Pipeline 可用。存储在 Runner 缓存中。
- `Artifacts`：用于 Job 间传递产物，如构建结果、测试报告。可靠存储在 GitLab 服务器，只在同一 Pipeline 内传递。

典型用法：Cache 缓存 `node_modules`，Artifacts 传递 `dist/` 目录。

### 3. 如何优化 GitLab CI Pipeline 的执行速度？

**参考答案**：
- 使用 `needs` 实现 DAG 并行执行
- 配置 Cache 缓存依赖
- 使用 `rules` 跳过不必要的 Job
- 使用 `parallel` 并行执行测试
- 使用 `resource_group` 避免部署冲突
- 使用 `interruptible` 允许中断旧 Pipeline
- 固定镜像版本避免重复拉取
- 使用 `include` 复用模板

### 4. GitLab Runner 的执行器有哪些？各自适用什么场景？

**参考答案**：
- `Shell`：直接在主机执行，简单但不隔离，适合特殊环境需求
- `Docker`：在容器中执行，隔离性好，最常用
- `Kubernetes`：在 K8s Pod 中执行，自动伸缩，适合大规模 CI
- `Docker Machine`：自动创建/销毁 Runner 实例，适合弹性需求

推荐大多数场景使用 Docker 执行器，大规模场景使用 Kubernetes 执行器。

### 5. 如何在 GitLab CI 中安全地管理 Secrets？

**参考答案**：
- 使用 CI/CD Variables（Settings > CI/CD > Variables）
- 敏感变量设置为 Protected（只在受保护分支可用）
- 敏感变量设置为 Masked（日志中遮罩）
- 使用 File 类型变量传递证书等文件
- 使用 Vault 集成动态获取 Secrets
- 不要在 script 中 echo 敏感变量
- 使用 `dotenv` report 传递变量

### 6. 解释 GitLab CI 中的 `rules` 和 `only/except` 的区别

**参考答案**：
- `only/except`：旧语法，基于分支和标签的简单过滤
- `rules`：新语法，支持更复杂的条件表达式，可以组合多个条件，支持 `when` 控制执行时机

`rules` 是推荐方式，支持：
- `if`：条件表达式
- `exists`：文件是否存在
- `changes`：文件是否变更
- `when`：执行时机（always/never/on_success/manual）
- `allow_failure`：是否允许失败

---

## 📚 深入阅读

- [GitLab CI/CD 官方文档](https://docs.gitlab.com/ee/ci/)
- [GitLab CI/CD YAML 语法参考](https://docs.gitlab.com/ee/ci/yaml/)
- [GitLab Runner 文档](https://docs.gitlab.com/runner/)
- [GitLab Auto DevOps](https://docs.gitlab.com/ee/topics/autodevops/)
- [GitLab CI 最佳实践](https://docs.gitlab.com/ee/ci/best_practices/)

---

## ✅ 自检清单

- [ ] 能编写完整的 `.gitlab-ci.yml` 文件
- [ ] 理解 Stages、Jobs、needs 的层级关系
- [ ] 掌握 DAG 模式优化 Pipeline 执行时间
- [ ] 能配置和管理 GitLab Runner
- [ ] 理解 Variables 的层级和类型
- [ ] 能使用 Artifacts 传递 Job 产物
- [ ] 能配置 Cache 加速构建
- [ ] 理解环境管理和 Review Apps
- [ ] 掌握 include 和 extends 模板复用
- [ ] 能排查常见的 Pipeline 和 Runner 问题
