# Day 148: GitHub Actions

> 📅 日期：2026-05-06
> 📖 学习主题：Workflow 语法、触发器、Jobs/Steps、Secrets、矩阵构建、自定义 Action、复用 Workflow、Runner、最佳实践
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 147（CI/CD 概念与 GitOps）

---

## 🎯 学习目标

- 掌握 GitHub Actions Workflow YAML 语法和核心组件
- 理解各种触发器（triggers）的使用场景和配置方式
- 能编写包含矩阵构建的复杂 CI/CD 流水线
- 掌握 Secrets 管理和 OIDC 集成
- 能创建自定义 Action 和复用 Workflow
- 理解 Self-hosted Runner 的配置和安全考虑

---

## 📖 核心知识点

### 1. Workflow 语法与核心概念

#### 1.1 GitHub Actions 架构

```
GitHub Actions 架构：

┌──────────────────────────────────────────────────────────────┐
│                   GitHub Actions 架构                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  GitHub Cloud                         │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ Workflow  │  │ Actions  │  │ Secrets  │           │   │
│  │  │ Engine   │  │ Market   │  │ Store    │           │   │
│  │  └────┬─────┘  └──────────┘  └──────────┘           │   │
│  │       │                                              │   │
│  │       ▼                                              │   │
│  │  ┌──────────────────────────────────────┐            │   │
│  │  │           Job Scheduler               │            │   │
│  │  └────┬──────────┬──────────┬───────────┘            │   │
│  │       │          │          │                        │   │
│  └───────┼──────────┼──────────┼────────────────────────┘   │
│          │          │          │                             │
│          ▼          ▼          ▼                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ Runner 1 │ │ Runner 2 │ │ Runner 3 │                    │
│  │ (Ubuntu) │ │ (macOS)  │ │ (Windows)│                    │
│  │          │ │          │ │          │                    │
│  │ Job A    │ │ Job B    │ │ Job C    │                    │
│  │ Step 1   │ │ Step 1   │ │ Step 1   │                    │
│  │ Step 2   │ │ Step 2   │ │ Step 2   │                    │
│  │ Step 3   │ │ Step 3   │ │ Step 3   │                    │
│  └──────────┘ └──────────┘ └──────────┘                    │
│                                                              │
│  Runner 类型：                                               │
│  • GitHub-hosted: 由 GitHub 托管，免费额度                   │
│  • Self-hosted: 用户自建，无使用限制                         │
│  • Larger runners: 付费增强配置                              │
└──────────────────────────────────────────────────────────────┘
```

#### 1.2 Workflow 文件结构

```yaml
# .github/workflows/ci.yml
# Workflow 完整结构

name: CI Pipeline                    # Workflow 名称（显示在 GitHub UI）

on:                                  # 触发条件
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:                 # 手动触发
    inputs:
      environment:
        description: 'Deploy target'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

permissions:                         # 工作流级别权限
  contents: read
  packages: write
  id-token: write                    # OIDC 所需

env:                                 # 全局环境变量
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

concurrency:                         # 并发控制
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:                                # 作业定义
  build:                             # Job ID
    name: Build and Test             # Job 显示名称
    runs-on: ubuntu-latest           # Runner 标签
    timeout-minutes: 30              # 超时时间

    outputs:                         # Job 输出
      image-tag: ${{ steps.meta.outputs.tags }}

    strategy:                        # 矩阵策略
      matrix:
        node-version: [18, 20, 22]
        os: [ubuntu-latest, windows-latest]
      fail-fast: false               # 一个失败不取消其他
      max-parallel: 4                # 最大并行数

    services:                        # 服务容器
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:                           # 步骤列表
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0             # 完整历史（用于版本计算）

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test

      - name: Build
        run: npm run build

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ matrix.node-version }}
          path: dist/
          retention-days: 7

  deploy:
    name: Deploy
    needs: build                     # 依赖 build job
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment:                     # 部署环境
      name: production
      url: https://my-app.com

    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: build-20
          path: dist/

      - name: Deploy
        run: echo "Deploying..."
```

### 2. 触发器（Triggers）详解

#### 2.1 事件触发器

```yaml
# 完整的触发器配置

on:
  # Push 事件
  push:
    branches:
      - main
      - 'release/**'           # 通配符匹配
      - 'releases/202[4-6]/**' # 正则匹配
    branches-ignore:           # 排除分支
      - 'experiment/**'
    tags:
      - 'v*'                   # 版本标签
      - '!v*-rc*'             # 排除 RC 标签
    paths:                     # 文件路径过滤
      - 'src/**'
      - 'package.json'
      - '!docs/**'            # 排除文档变更
    paths-ignore:
      - '**.md'

  # Pull Request 事件
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
    branches: [main]
    paths:
      - 'src/**'

  # 定时触发（Cron）
  schedule:
    - cron: '0 2 * * 1-5'     # 工作日 UTC 2:00
    - cron: '0 6 * * 0'       # 周日 UTC 6:00

  # 手动触发
  workflow_dispatch:
    inputs:
      logLevel:
        description: 'Log level'
        required: true
        default: 'warning'
        type: choice
        options:
          - info
          - warning
          - debug
      tags:
        description: 'Test scenario tags'
        required: false
        type: boolean

  # 其他 Workflow 完成后触发
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]
    branches: [main]

  # Webhook 事件
  repository_dispatch:
    types: [deploy-command]     # 自定义事件类型

  # Release 事件
  release:
    types: [published, edited]

  # Issue/PR 评论触发
  issue_comment:
    types: [created]

  # Watch（Star）事件
  watch:
    types: [started]
```

#### 2.2 事件过滤与条件

```yaml
# 使用 activity type 和过滤器

on:
  pull_request:
    types: [labeled, synchronize]
    branches:
      - main

jobs:
  check-label:
    runs-on: ubuntu-latest
    # 只在特定 label 存在时运行
    if: contains(github.event.pull_request.labels.*.name, 'safe-to-test')

  deploy-preview:
    runs-on: ubuntu-latest
    # 复杂条件表达式
    if: >-
      github.event_name == 'pull_request' &&
      github.event.pull_request.draft == false &&
      !contains(github.event.pull_request.title, '[skip ci]') &&
      (github.event.action == 'labeled' || github.event.action == 'synchronize')
```

### 3. Jobs 与 Steps

#### 3.1 Job 依赖与并行

```yaml
jobs:
  # 并行执行的 Job
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm audit

  # 依赖前面三个 Job（并行完成后执行）
  build:
    needs: [lint, test, security-scan]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run build

  # 条件依赖
  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploy to staging"

  deploy-production:
    needs: deploy-staging
    if: success()                    # 前置 Job 成功
    runs-on: ubuntu-latest
    environment: production          # 需要审批
    steps:
      - run: echo "Deploy to production"

  # 失败后执行
  notify-failure:
    needs: [build, deploy-staging]
    if: failure()                    # 前置 Job 失败
    runs-on: ubuntu-latest
    steps:
      - run: echo "Send failure notification"
```

#### 3.2 Steps 高级用法

```yaml
steps:
  # 基础步骤
  - name: Simple command
    run: echo "Hello World"

  # 多行命令
  - name: Multi-line script
    run: |
      echo "Step 1: Check environment"
      node --version
      npm --version
      echo "Step 2: Install deps"
      npm ci

  # 条件步骤
  - name: Conditional step
    if: success() && github.ref == 'refs/heads/main'
    run: echo "Only on main branch success"

  # 失败时执行
  - name: On failure
    if: failure()
    run: echo "Previous step failed"

  # 始终执行（类似 finally）
  - name: Always run
    if: always()
    run: echo "This always runs"

  # 取消时执行
  - name: On cancellation
    if: cancelled()
    run: echo "Workflow was cancelled"

  # 使用 Action
  - name: Checkout
    uses: actions/checkout@v4
    with:
      ref: main
      token: ${{ secrets.GITHUB_TOKEN }}
      fetch-depth: 0

  # 带 ID 的步骤（用于后续引用输出）
  - name: Get version
    id: version
    run: echo "version=$(date +%Y%m%d-%H%M%S)" >> $GITHUB_OUTPUT

  - name: Use version
    run: echo "Version is ${{ steps.version.outputs.version }}"

  # 环境变量
  - name: With env
    run: echo "Registry is $REGISTRY"
    env:
      REGISTRY: ghcr.io

  # Continue on error
  - name: May fail
    continue-on-error: true
    run: exit 1

  # Working directory
  - name: In subdirectory
    run: make build
    working-directory: ./backend
```

### 4. Secrets 管理

#### 4.1 Secrets 层级

```
Secrets 层级与作用域：

┌──────────────────────────────────────────────────────────────┐
│                    Secrets 层级                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Organization Secrets（组织级）                        │   │
│  │  • 所有仓库可见（可选择性授权）                         │   │
│  │  • 适合共享凭证（Docker Hub、npm Token）               │   │
│  │  └──────────────────────────────────────────────────┘   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────────┐   │
│  │  │  Repository Secrets（仓库级）                      │   │
│  │  │  • 仅当前仓库可见                                  │   │
│  │  │  • 适合项目特有凭证                                │   │
│  │  │  └──────────────────────────────────────────────┘   │   │
│  │  │                                                  │   │
│  │  │  ┌──────────────────────────────────────────────┐   │
│  │  │  │  Environment Secrets（环境级）                 │   │
│  │  │  │  • 绑定到特定环境（staging/production）        │   │
│  │  │  │  • 支持审批门禁                               │   │
│  │  │  │  • 最细粒度控制                               │   │
│  │  │  └──────────────────────────────────────────────┘   │
│  │  └──────────────────────────────────────────────────┘   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  优先级：Environment > Repository > Organization             │
└──────────────────────────────────────────────────────────────┘
```

#### 4.2 Secrets 使用方式

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      # 方式 1: 环境变量引用
      - name: Deploy with secret
        env:
          API_KEY: ${{ secrets.API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          echo "Deploying with API key..."
          # API_KEY 不会出现在日志中（自动遮罩）
          ./deploy.sh

      # 方式 2: 文件方式传递
      - name: Write kubeconfig
        run: echo "${{ secrets.KUBECONFIG }}" > $HOME/.kube/config

      # 方式 3: 作为 Action 输入
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_TOKEN }}
```

#### 4.3 OIDC 认证（推荐方式）

```yaml
# 使用 OIDC 代替长期凭证（更安全）

permissions:
  id-token: write    # 必须
  contents: read

jobs:
  deploy-aws:
    runs-on: ubuntu-latest
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
          aws-region: us-east-1
          # 无需 Access Key / Secret Key

      - name: Deploy to S3
        run: aws s3 sync dist/ s3://my-bucket/

  deploy-azure:
    runs-on: ubuntu-latest
    steps:
      - name: Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

  deploy-gcp:
    runs-on: ubuntu-latest
    steps:
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/123456/locations/global/workloadIdentityPools/my-pool/providers/my-provider
          service_account: github-actions@my-project.iam.gserviceaccount.com

  push-to-ghcr:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}  # 自动提供

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:latest
```

### 5. 矩阵构建（Matrix Build）

#### 5.1 基础矩阵

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18, 20, 22]
        exclude:                     # 排除组合
          - os: windows-latest
            node-version: 18
        include:                     # 额外组合
          - os: ubuntu-latest
            node-version: 22
            experimental: true       # 自定义变量

    continue-on-error: ${{ matrix.experimental == true }}

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm ci
      - run: npm test
```

#### 5.2 高级矩阵

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      max-parallel: 6
      matrix:
        # 复杂矩阵定义
        include:
          - node-version: 18
            database: postgres
            os: ubuntu-22.04
          - node-version: 18
            database: mysql
            os: ubuntu-22.04
          - node-version: 20
            database: postgres
            os: ubuntu-22.04
          - node-version: 20
            database: mysql
            os: ubuntu-24.04

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
        if: matrix.database == 'postgres'

      mysql:
        image: mysql:8
        env:
          MYSQL_ROOT_PASSWORD: test
        ports: ['3306:3306']
        options: --health-cmd "mysqladmin ping" --health-interval 10s --health-timeout 5s --health-retries 5
        if: matrix.database == 'mysql'

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm ci
      - run: npm test
        env:
          DB_TYPE: ${{ matrix.database }}

  # 动态矩阵 - 从上一个 Job 的输出生成矩阵
  prepare:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: |
          echo 'matrix={"service":["api","web","worker"],"region":["us-east-1","eu-west-1"]}' >> $GITHUB_OUTPUT

  deploy:
    needs: prepare
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.prepare.outputs.matrix) }}
    steps:
      - run: echo "Deploying ${{ matrix.service }} to ${{ matrix.region }}"
```

### 6. 自定义 Action

#### 6.1 Action 类型

```
GitHub Actions 三种类型：

┌──────────────────────────────────────────────────────────────┐
│                    Action 三种类型                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. JavaScript Action（Node.js）                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • 运行在 Node.js 环境                                 │   │
│  │ • 执行速度快（无需容器构建）                            │   │
│  │ • 可以使用 npm 生态                                   │   │
│  │ • action.yml + index.js + package.json                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  2. Docker Action                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • 运行在 Docker 容器中                                │   │
│  │ • 可以使用任何语言/工具                                │   │
│  │ • 启动较慢（需要构建容器）                              │   │
│  │ • action.yml + Dockerfile                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  3. Composite Action                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ • 组合多个步骤                                        │   │
│  │ • 类似"宏"或"模板"                                    │   │
│  │ • 最轻量，无需额外运行时                                │   │
│  │ • action.yml（使用 runs: composite）                  │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

#### 6.2 Composite Action 示例

```yaml
# .github/actions/setup-project/action.yml
name: 'Setup Project'
description: 'Setup project with dependencies and caching'
inputs:
  node-version:
    description: 'Node.js version'
    required: false
    default: '20'
  package-manager:
    description: 'Package manager (npm, yarn, pnpm)'
    required: false
    default: 'npm'

runs:
  using: 'composite'
  steps:
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: ${{ inputs.package-manager }}

    - name: Install dependencies (npm)
      if: inputs.package-manager == 'npm'
      run: npm ci
      shell: bash

    - name: Install dependencies (pnpm)
      if: inputs.package-manager == 'pnpm'
      run: |
        corepack enable
        pnpm install --frozen-lockfile
      shell: bash

    - name: Install dependencies (yarn)
      if: inputs.package-manager == 'yarn'
      run: yarn install --frozen-lockfile
      shell: bash

# 使用方式：
# steps:
#   - uses: actions/checkout@v4
#   - uses: ./.github/actions/setup-project
#     with:
#       node-version: '20'
#       package-manager: 'pnpm'
```

#### 6.3 JavaScript Action 示例

```yaml
# my-action/action.yml
name: 'Custom Notification'
description: 'Send deployment notification'
inputs:
  webhook-url:
    description: 'Slack webhook URL'
    required: true
  message:
    description: 'Notification message'
    required: true
  status:
    description: 'Deployment status'
    required: true
    default: 'success'

outputs:
  timestamp:
    description: 'Notification timestamp'

runs:
  using: 'node20'
  main: 'dist/index.js'

---
# my-action/src/index.js
const core = require('@actions/core');
const github = require('@actions/github');

async function run() {
  try {
    const webhookUrl = core.getInput('webhook-url', { required: true });
    const message = core.getInput('message', { required: true });
    const status = core.getInput('status');

    const payload = {
      text: `${status === 'success' ? '✅' : '❌'} ${message}`,
      blocks: [
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `*Deployment ${status}*\n${message}\nRepo: ${github.context.repo.owner}/${github.context.repo.repo}\nRef: ${github.context.ref}`
          }
        }
      ]
    };

    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    core.setOutput('timestamp', new Date().toISOString());
    core.info('Notification sent successfully');
  } catch (error) {
    core.setFailed(error.message);
  }
}

run();
```

### 7. 复用 Workflow（Reusable Workflows）

#### 7.1 可调用 Workflow

```yaml
# .github/workflows/reusable-build.yml
name: Reusable Build

on:
  workflow_call:                     # 声明为可调用
    inputs:
      environment:
        required: true
        type: string
      node-version:
        required: false
        type: string
        default: '20'
      run-e2e:
        required: false
        type: boolean
        default: false
    secrets:
      NPM_TOKEN:
        required: true
      DEPLOY_KEY:
        required: false
    outputs:
      build-result:
        description: "Build result"
        value: ${{ jobs.build.outputs.result }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.build.outputs.result }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          registry-url: 'https://registry.npmjs.org'

      - run: npm ci
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

      - run: npm run build

      - run: npm test

      - name: Run E2E tests
        if: inputs.run-e2e
        run: npm run test:e2e

      - id: build
        run: echo "result=success" >> $GITHUB_OUTPUT
```

#### 7.2 调用复用 Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # 调用复用 Workflow
  build-staging:
    uses: ./.github/workflows/reusable-build.yml
    with:
      environment: staging
      node-version: '20'
      run-e2e: false
    secrets:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}

  build-production:
    uses: ./.github/workflows/reusable-build.yml
    with:
      environment: production
      node-version: '20'
      run-e2e: true
    secrets:
      NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
      DEPLOY_KEY: ${{ secrets.PROD_DEPLOY_KEY }}

  # 调用外部仓库的复用 Workflow
  security-scan:
    uses: org/security-workflows/.github/workflows/scan.yml@main
    with:
      scan-type: 'sast'
    secrets:
      SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### 8. Runner 配置

#### 8.1 GitHub-hosted vs Self-hosted

```
Runner 对比：

┌──────────────────────────────────────────────────────────────┐
│                    Runner 类型对比                             │
├──────────────────┬───────────────────────────────────────────┤
│                  │  GitHub-hosted      Self-hosted           │
├──────────────────┼───────────────────────────────────────────┤
│ 维护             │  GitHub 管理        用户自行维护            │
│ 成本             │  免费额度+付费       硬件/云成本             │
│ 启动时间         │  30-60 秒           即时（常驻）            │
│ 环境一致性       │  每次全新环境        可能有状态漂移          │
│ 定制化           │  有限               完全自定义              │
│ 安全性           │  隔离环境           需要额外安全措施        │
│ 性能             │  标准配置           可选高性能硬件          │
│ 网络             │  公网               可访问内网              │
│ 适用场景         │  开源项目、小型项目  大型企业、特殊需求      │
└──────────────────┴───────────────────────────────────────────┘
```

#### 8.2 Self-hosted Runner 配置

```yaml
# 使用 Self-hosted Runner
jobs:
  build:
    runs-on: [self-hosted, linux, x64, gpu]  # 标签匹配
    steps:
      - uses: actions/checkout@v4
      - run: make build

  # Runner 组
  deploy:
    runs-on: [self-hosted, production]
    environment: production
    steps:
      - run: ./deploy.sh
```

Self-hosted Runner 安装：

```bash
# 在 Runner 机器上执行
# 从 GitHub 仓库 Settings > Actions > Runners 获取

mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf actions-runner-linux-x64.tar.gz

# 配置
./config.sh --url https://github.com/org/repo \
  --token YOUR_TOKEN \
  --labels self-hosted,linux,x64 \
  --name my-runner \
  --work _work

# 作为服务运行
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

#### 8.3 Runner 安全最佳实践

```yaml
# 使用 Runner Hooks 进行安全检查
# 文件: .github/runners/.env
# ACTIONS_RUNNER_HOOK_JOB_STARTED=/opt/runner-hooks/job-started.sh
# ACTIONS_RUNNER_HOOK_JOB_COMPLETED=/opt/runner-hooks/job-completed.sh

# job-started.sh 示例
#!/bin/bash
echo "Job started at $(date)"
echo "Runner: $(hostname)"
echo "Cleaning workspace..."
rm -rf /home/runner/actions-runner/_work/*/*
echo "Workspace cleaned"

# 使用 ephemeral 模式（一次性 Runner）
# 配置时添加 --ephemeral 标志
./config.sh --ephemeral
# Runner 完成一个 Job 后自动退出，需要外部系统重新注册
```

### 9. 最佳实践

#### 9.1 性能优化

```yaml
# 1. 缓存依赖
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-

# 2. 使用 setup-* action 内置缓存
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'                    # 自动缓存

# 3. Docker 层缓存
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: ghcr.io/myapp:latest
    cache-from: type=gha            # GitHub Actions 缓存
    cache-to: type=gha,mode=max

# 4. 并行执行无依赖步骤
jobs:
  lint:
    runs-on: ubuntu-latest
    steps: [...]
  test:
    runs-on: ubuntu-latest
    steps: [...]
  build:
    runs-on: ubuntu-latest
    steps: [...]

# 5. 条件跳过不必要的步骤
- name: Deploy
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: ./deploy.sh
```

#### 9.2 安全最佳实践

```yaml
# 1. 固定 Action 版本到 SHA（防止供应链攻击）
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
  # 而非 actions/checkout@v4（可被篡改）

# 2. 最小权限
permissions:
  contents: read          # 只读权限
  packages: write         # 仅在需要时授予写权限

# 3. 使用 GITHUB_TOKEN 而非 PAT
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.GITHUB_TOKEN }}  # 自动提供的临时 token

# 4. 避免在日志中泄露 Secrets
- name: Safe logging
  run: |
    echo "::add-mask::${{ secrets.MY_SECRET }}"
    echo "Using secret to deploy..."

# 5. 使用环境保护规则
deploy:
  environment:
    name: production
    url: https://my-app.com
  # 在 GitHub 设置中配置：
  # - Required reviewers
  # - Wait timer
  # - Branch restrictions
```

#### 9.3 常见 Workflow 模板

```yaml
# 完整的 Node.js CI/CD 流水线
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  packages: write
  id-token: write

env:
  NODE_VERSION: '20'
  REGISTRY: ghcr.io

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  ci:
    name: CI
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports: ['6379:6379']
        options: --health-cmd "redis-cli ping" --health-interval 10s --health-timeout 5s --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npm run typecheck

      - name: Unit tests
        run: npm test -- --coverage

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

      - name: Build
        run: npm run build

  build-image:
    name: Build Docker Image
    needs: ci
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

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

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ github.repository }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    name: Deploy
    needs: build-image
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4
        with:
          repository: org/k8s-manifests
          token: ${{ secrets.MANIFESTS_TOKEN }}

      - name: Update image tag
        run: |
          cd apps/my-app/overlays/production
          kustomize edit set image my-app=${{ env.REGISTRY }}/${{ github.repository }}:${{ github.sha }}

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add .
          git commit -m "chore: update my-app to ${{ github.sha }}"
          git push
```

---

## 💻 实战练习

### 练习 1：编写多环境 CI/CD 流水线

**目标**：为一个 Go Web 应用编写完整的 CI/CD 流水线

**步骤**：

1. 创建 `.github/workflows/ci.yml`：
   - 代码质量检查（golangci-lint）
   - 单元测试（带覆盖率）
   - 安全扫描（govulncheck）
   - 构建 Docker 镜像

2. 创建 `.github/workflows/deploy.yml`：
   - 部署到 staging（自动）
   - 部署到 production（需要审批）
   - 使用 OIDC 认证访问云服务

3. 创建复用 Workflow `.github/workflows/reusable-test.yml`：
   - 接受 Go 版本和测试命令作为输入
   - 被多个 Workflow 调用

**验证**：Push 代码后观察流水线执行，确认矩阵构建和并行执行正常

### 练习 2：创建自定义 Action

**目标**：创建一个 Composite Action 用于标准化项目初始化

**步骤**：

1. 创建 `.github/actions/setup-go/action.yml`：
   - 安装指定版本的 Go
   - 配置 Go module 缓存
   - 下载依赖

2. 创建 `.github/actions/notify/action.yml`：
   - 发送 Slack 通知
   - 包含构建状态、分支、提交信息

3. 在 Workflow 中使用自定义 Action

**验证**：确认 Action 被正确调用，缓存生效

### 练习 3：故障排查 - Workflow 失败

**场景**：Workflow 运行失败，需要排查原因

**步骤**：

1. 检查常见失败原因：
   - Secret 未配置或过期
   - 权限不足（permissions 配置）
   - Runner 标签不匹配
   - 依赖安装失败
   - 测试超时

2. 使用调试技巧：
```yaml
# 启用调试日志
# 在仓库 Settings > Secrets 中添加：
# ACTIONS_RUNNER_DEBUG: true
# ACTIONS_STEP_DEBUG: true

# 或在 URL 中添加 ?debug=true
```

3. 排查矩阵构建中的特定组合失败

**验证**：修复问题后流水线成功运行

---

## 🎯 面试题精选

### 1. GitHub Actions 中 `workflow_call` 和 `workflow_dispatch` 有什么区别？

**参考答案**：
- `workflow_dispatch`：手动触发，允许用户通过 GitHub UI 或 API 手动运行 Workflow，可以定义输入参数
- `workflow_call`：被其他 Workflow 调用，用于创建可复用的 Workflow，可以定义输入和输出

关键区别：`workflow_dispatch` 是人触发，`workflow_call` 是 Workflow 触发 Workflow。

### 2. 如何安全地在 GitHub Actions 中管理 Secrets？

**参考答案**：
- 使用 GitHub 内置 Secrets（组织级/仓库级/环境级）
- 优先使用 OIDC 认证代替长期凭证
- 使用环境保护规则（审批门禁、等待时间）
- 固定 Action 版本到 SHA（防止供应链攻击）
- 最小权限原则（permissions 字段）
- 避免在日志中打印 Secret（使用 `::add-mask::`）

### 3. 解释 GitHub Actions 中的 `concurrency` 配置

**参考答案**：
`concurrency` 用于控制 Workflow 的并发执行。配置 `group` 后，同一 group 内的 Workflow 运行会互斥。`cancel-in-progress: true` 会在新运行开始时取消之前的运行。

典型用途：PR 的多次 push 只保留最新的构建；同一环境的部署互斥执行。

### 4. Self-hosted Runner 的安全风险有哪些？如何缓解？

**参考答案**：
风险：
- 恶意代码可能访问 Runner 机器的文件系统和网络
- Runner 可能有持久化状态（前一次构建的残留）
- Runner 可以访问内网资源

缓解措施：
- 使用 ephemeral 模式（一次性 Runner）
- 使用 Docker 容器隔离
- 限制 Runner 标签（只有特定 Workflow 可以使用）
- 定期清理工作目录
- 使用 Runner Hooks 进行环境检查
- 网络隔离（Runner 不应访问敏感内网）

### 5. 矩阵构建中 `fail-fast` 和 `max-parallel` 的作用是什么？

**参考答案**：
- `fail-fast`：默认 true，当矩阵中某个组合失败时，取消其他正在运行的组合。设为 false 可以让所有组合运行完毕，便于全面了解失败情况。
- `max-parallel`：限制矩阵中同时运行的 Job 数量，用于控制资源使用和避免触发 API 限流。

### 6. 如何优化 GitHub Actions 的运行速度？

**参考答案**：
- 缓存依赖（actions/cache 或 setup-* 内置缓存）
- Docker 层缓存（type=gha）
- 并行执行无依赖步骤
- 条件跳过不必要的步骤
- 使用 Self-hosted Runner（更快硬件）
- 减少 `fetch-depth`（浅克隆）
- 使用 matrix 的 `fail-fast` 快速失败

### 7. GitHub Actions 的 `GITHUB_TOKEN` 有什么限制？

**参考答案**：
- 每个 Workflow 运行自动生成，无需手动配置
- 权限范围限于当前仓库
- PR 来自 fork 时权限受限（只读）
- 不能触发新的 Workflow 迎（防止无限循环）
- 有 API 调用限流

如需跨仓库操作或触发 Workflow，需要使用 PAT 或 GitHub App。

---

## 📚 深入阅读

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [GitHub Actions 安全最佳实践](https://docs.github.com/en/actions/security-guides)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [GitHub Actions 缓存](https://docs.github.com/en/actions/caching)
- [OIDC 与云服务集成](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)

---

## ✅ 自检清单

- [ ] 能编写完整的 Workflow YAML 文件
- [ ] 理解各种触发器的使用场景
- [ ] 掌握 Job 依赖和并行执行配置
- [ ] 能配置 Secrets 和 OIDC 认证
- [ ] 能使用矩阵构建覆盖多环境
- [ ] 能创建 Composite Action 和复用 Workflow
- [ ] 理解 GitHub-hosted 和 Self-hosted Runner 的区别
- [ ] 掌握缓存策略优化构建速度
- [ ] 了解安全最佳实践（版本固定、最小权限）
- [ ] 能排查常见的 Workflow 失败问题
