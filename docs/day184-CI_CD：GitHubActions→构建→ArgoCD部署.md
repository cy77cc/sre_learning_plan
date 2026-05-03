# Day 184: CI/CD 流水线 — GitHub Actions + ArgoCD GitOps

> 📅 日期：2026-05-07
> 📖 学习主题：完整 CI/CD 流水线、镜像构建、安全扫描、GitOps 部署
> ⏰ 预计学习时间：6-8 小时
> 📋 前置知识：Day 150-160 (CI/CD), Day 182 (微服务部署), Day 183 (可观测性)

---

## 🎯 学习目标

完成 Day 184 的学习后，你应该能够：

1. 编写完整的 GitHub Actions CI/CD 工作流
2. 实现自动化镜像构建和推送
3. 集成 Trivy 安全扫描
4. 部署和配置 ArgoCD
5. 实现 GitOps 自动化部署
6. 理解 CI/CD 流水线的最佳实践

---

## 📖 核心知识点

### 1. CI/CD 流水线架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      CI/CD Pipeline                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Developer                                                      │
│     │                                                           │
│     ▼                                                           │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│  │   Push   │────→│  GitHub  │────→│  GitHub  │               │
│  │   Code   │     │  Repo    │     │ Actions  │               │
│  └──────────┘     └──────────┘     └────┬─────┘               │
│                                         │                       │
│                    ┌────────────────────┼────────────┐          │
│                    ▼                    ▼            ▼          │
│             ┌──────────┐        ┌──────────┐  ┌──────────┐     │
│             │  Lint &  │        │  Build   │  │ Security │     │
│             │  Test    │        │  Image   │  │  Scan    │     │
│             └────┬─────┘        └────┬─────┘  └────┬─────┘     │
│                  │                   │              │           │
│                  └───────────────────┼──────────────┘           │
│                                      ▼                          │
│                              ┌──────────────┐                   │
│                              │ Push to ECR  │                   │
│                              └──────┬───────┘                   │
│                                     │                           │
│                                     ▼                           │
│                              ┌──────────────┐                   │
│                              │  Update Git  │                   │
│                              │  Manifests   │                   │
│                              └──────┬───────┘                   │
│                                     │                           │
│                                     ▼                           │
│                              ┌──────────────┐                   │
│                              │   ArgoCD     │                   │
│                              │   Sync       │                   │
│                              └──────┬───────┘                   │
│                                     │                           │
│                                     ▼                           │
│                              ┌──────────────┐                   │
│                              │   EKS Prod   │                   │
│                              │   Deploy     │                   │
│                              └──────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. GitHub Actions CI Workflow

```yaml
# ci-cd/.github/workflows/ci.yaml
name: CI - Build and Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY_PREFIX: sre-capstone

jobs:
  # ============================================================
  # Job 1: 代码检查
  # ============================================================
  lint:
    name: Lint Code
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Go Lint (user-service)
        working-directory: services/user-service
        run: |
          go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
          golangci-lint run ./...

      - name: Python Lint (product-service)
        working-directory: services/product-service
        run: |
          pip install ruff mypy
          ruff check .
          mypy app/ --ignore-missing-imports

  # ============================================================
  # Job 2: 单元测试
  # ============================================================
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.22'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Go Tests (user-service)
        working-directory: services/user-service
        run: |
          go test -v -race -coverprofile=coverage.out ./...
          go tool cover -func=coverage.out

      - name: Python Tests (product-service)
        working-directory: services/product-service
        run: |
          pip install -r requirements.txt pytest pytest-cov httpx
          pytest tests/ -v --cov=app --cov-report=xml --cov-report=term

      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./services/user-service/coverage.out,./services/product-service/coverage.xml
          fail_ci_if_error: false

  # ============================================================
  # Job 3: 构建并推送镜像
  # ============================================================
  build:
    name: Build and Push Images
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    strategy:
      matrix:
        service:
          - name: user-service
            context: services/user-service
          - name: product-service
            context: services/product-service

    permissions:
      id-token: write
      contents: read

    outputs:
      user-service-tag: ${{ steps.meta.outputs.version }}
      product-service-tag: ${{ steps.meta.outputs.version }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Generate image metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.login-ecr.outputs.registry }}/${{ env.ECR_REPOSITORY_PREFIX }}/${{ matrix.service.name }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.service.context }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ============================================================
  # Job 4: 安全扫描
  # ============================================================
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: build
    strategy:
      matrix:
        service:
          - user-service
          - product-service

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        uses: aws-actions/amazon-ecr-login@v2

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/${{ env.ECR_REPOSITORY_PREFIX }}/${{ matrix.service.name }}:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
        env:
          TRIVY_USERNAME: AWS
          TRIVY_PASSWORD: ${{ steps.login-ecr.outputs.docker_password_aws }}

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  # ============================================================
  # Job 5: 更新 Git Manifests
  # ============================================================
  update-manifests:
    name: Update Git Manifests
    runs-on: ubuntu-latest
    needs: [build, security-scan]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - name: Checkout manifest repo
        uses: actions/checkout@v4
        with:
          repository: ${{ secrets.MANIFEST_REPO }}
          token: ${{ secrets.MANIFEST_REPO_TOKEN }}
          path: manifests

      - name: Update image tags
        run: |
          cd manifests
          IMAGE_TAG="${{ github.sha }}"

          # Update user-service image tag
          sed -i "s|image: .*/user-service:.*|image: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/${{ env.ECR_REPOSITORY_PREFIX }}/user-service:${IMAGE_TAG:0:7}|" \
            k8s/overlays/prod/user-service-deployment.yaml

          # Update product-service image tag
          sed -i "s|image: .*/product-service:.*|image: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/${{ env.ECR_REPOSITORY_PREFIX }}/product-service:${IMAGE_TAG:0:7}|" \
            k8s/overlays/prod/product-service-deployment.yaml

      - name: Commit and push changes
        run: |
          cd manifests
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add .
          git diff --cached --quiet || git commit -m "chore: update image tags to ${{ github.sha }}"
          git push
```

### 3. GitHub Actions CD Workflow

```yaml
# ci-cd/.github/workflows/cd.yaml
name: CD - Deploy

on:
  workflow_run:
    workflows: ["CI - Build and Test"]
    types: [completed]
    branches: [main]

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment:
      name: staging
      url: https://staging.sre-capstone.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig --name sre-capstone-staging-eks --region us-east-1

      - name: Deploy to staging
        run: |
          kubectl apply -k k8s/overlays/staging/
          kubectl rollout status deployment/user-service -n sre-capstone --timeout=300s
          kubectl rollout status deployment/product-service -n sre-capstone --timeout=300s

      - name: Run smoke tests
        run: |
          INGRESS_ADDR=$(kubectl get svc -n ingress-nginx ingress-nginx-controller \
            -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

          # Health check
          curl -sf "http://${INGRESS_ADDR}/health" -H "Host: api.staging.sre-capstone.com"

          # API test
          curl -sf "http://${INGRESS_ADDR}/api/v1/users" -H "Host: api.staging.sre-capstone.com"

          echo "Smoke tests passed"

      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Staging deployment ${{ job.status }}: ${{ github.sha }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 4. ArgoCD 配置

#### 4.1 ArgoCD 安装

```bash
#!/usr/bin/env bash
# scripts/install-argocd.sh

set -euo pipefail

NAMESPACE="argocd"

echo "=== 安装 ArgoCD ==="
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n "${NAMESPACE}" -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "=== 等待 ArgoCD 就绪 ==="
kubectl wait --for=condition=available deployment/argocd-server -n "${NAMESPACE}" --timeout=300s
kubectl wait --for=condition=available deployment/argocd-repo-server -n "${NAMESPACE}" --timeout=300s
kubectl wait --for=condition=available deployment/argocd-applicationset-controller -n "${NAMESPACE}" --timeout=300s

echo "=== 配置 ArgoCD Server 为 LoadBalancer ==="
kubectl patch svc argocd-server -n "${NAMESPACE}" -p '{"spec": {"type": "LoadBalancer"}}'

echo "=== 获取初始密码 ==="
ARGOCD_PASSWORD=$(kubectl -n "${NAMESPACE}" get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo "ArgoCD 初始密码: ${ARGOCD_PASSWORD}"

echo ""
echo "=== 登录 ArgoCD ==="
ARGOCD_ADDR=$(kubectl get svc argocd-server -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ArgoCD 地址: https://${ARGOCD_ADDR}"
echo "用户名: admin"
echo "密码: ${ARGOCD_PASSWORD}"

echo ""
echo "=== 修改密码 ==="
echo "argocd login ${ARGOCD_ADDR} --username admin --password ${ARGOCD_PASSWORD} --insecure"
echo "argocd account update-password --current-password ${ARGOCD_PASSWORD} --new-password YourNewPassword"
```

#### 4.2 ArgoCD Project

```yaml
# ci-cd/argocd/project.yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: sre-capstone
  namespace: argocd
spec:
  description: SRE Capstone Project

  sourceRepos:
    - 'https://github.com/YOUR_ORG/sre-capstone-manifests.git'

  destinations:
    - namespace: sre-capstone
      server: https://kubernetes.default.svc
    - namespace: observability
      server: https://kubernetes.default.svc

  clusterResourceWhitelist:
    - group: ''
      kind: Namespace

  namespaceResourceWhitelist:
    - group: ''
      kind: '*'
    - group: apps
      kind: '*'
    - group: networking.k8s.io
      kind: '*'
    - group: autoscaling
      kind: '*'
    - group: policy
      kind: '*'

  roles:
    - name: developer
      description: Developer access
      policies:
        - p, proj:sre-capstone:developer, applications, get, sre-capstone/*, allow
        - p, proj:sre-capstone:developer, applications, sync, sre-capstone/*, allow
```

#### 4.3 ArgoCD Application - Dev

```yaml
# ci-cd/argocd/applications/dev.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: sre-capstone-dev
  namespace: argocd
  labels:
    environment: dev
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: sre-capstone

  source:
    repoURL: https://github.com/YOUR_ORG/sre-capstone-manifests.git
    targetRevision: develop
    path: k8s/overlays/dev

  destination:
    server: https://kubernetes.default.svc
    namespace: sre-capstone

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```

#### 4.4 ArgoCD Application - Prod

```yaml
# ci-cd/argocd/applications/prod.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: sre-capstone-prod
  namespace: argocd
  labels:
    environment: prod
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: sre-capstone

  source:
    repoURL: https://github.com/YOUR_ORG/sre-capstone-manifests.git
    targetRevision: main
    path: k8s/overlays/prod

  destination:
    server: https://kubernetes.default.svc
    namespace: sre-capstone

  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true

  # 生产环境需要手动同步
  # 不启用 automated sync

  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```

### 5. AWS IAM Role for GitHub Actions (OIDC)

```hcl
# ci-cd/terraform/github-actions-oidc.tf

data "aws_caller_identity" "current" {}

# ============================================================
# GitHub Actions OIDC Provider
# ============================================================
resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# ============================================================
# IAM Role for GitHub Actions
# ============================================================
resource "aws_iam_role" "github_actions" {
  name = "github-actions-sre-capstone"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github_actions.arn
        }
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:YOUR_ORG/sre-capstone:ref:refs/heads/main"
          }
        }
      }
    ]
  })
}

# ============================================================
# ECR 权限
# ============================================================
resource "aws_iam_role_policy" "github_actions_ecr" {
  name = "github-actions-ecr"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "arn:aws:ecr:${var.aws_region}:${data.aws_caller_identity.current.account_id}:repository/sre-capstone/*"
      }
    ]
  })
}

# ============================================================
# EKS 权限
# ============================================================
resource "aws_iam_role_policy" "github_actions_eks" {
  name = "github-actions-eks"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "eks:DescribeCluster",
          "eks:ListClusters"
        ]
        Resource = "*"
      }
    ]
  })
}
```

---

## 💻 实战练习

### 练习 1：配置 GitHub Actions CI

**目标**：配置 GitHub Actions 自动运行测试和构建镜像。

**步骤**：

```bash
# 1. 创建 GitHub 仓库
gh repo create sre-capstone --private

# 2. 设置 GitHub Secrets
gh secret set AWS_ROLE_ARN --body "arn:aws:iam::123456789012:role/github-actions-sre-capstone"
gh secret set AWS_ACCOUNT_ID --body "123456789012"
gh secret set MANIFEST_REPO --body "YOUR_ORG/sre-capstone-manifests"
gh secret set MANIFEST_REPO_TOKEN --body "ghp_xxxxxxxxxxxx"
gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/services/YOUR/WEBHOOK"

# 3. 推送代码触发 CI
git add .
git commit -m "feat: add CI/CD pipeline"
git push origin main

# 4. 查看 CI 运行状态
gh run list
gh run watch
```

**验证标准**：
- CI 工作流成功运行
- 测试通过
- 镜像构建并推送到 ECR
- 安全扫描通过

### 练习 2：部署 ArgoCD 并配置 GitOps

**目标**：部署 ArgoCD 并配置自动同步。

**步骤**：

```bash
# 1. 安装 ArgoCD
chmod +x scripts/install-argocd.sh
./scripts/install-argocd.sh

# 2. 创建 Manifest 仓库
gh repo create sre-capstone-manifests --private

# 3. 推送 Manifests
git clone https://github.com/YOUR_ORG/sre-capstone-manifests.git
cd sre-capstone-manifests
cp -r ../sre-capstone/k8s .
git add .
git commit -m "feat: initial manifests"
git push

# 4. 创建 ArgoCD Application
kubectl apply -f ci-cd/argocd/project.yaml
kubectl apply -f ci-cd/argocd/applications/dev.yaml

# 5. 验证同步状态
argocd app list
argocd app get sre-capstone-dev
```

**验证标准**：
- ArgoCD 安装成功
- Application 创建成功
- 自动同步正常工作
- 应用在集群中运行

### 练习 3：端到端部署验证

**目标**：修改代码，触发完整的 CI/CD 流水线。

**步骤**：

```bash
# 1. 修改代码
cd services/user-service
# 在 main.go 中添加新的 API 端点

# 2. 提交并推送
git add .
git commit -m "feat: add new API endpoint"
git push origin main

# 3. 观察 CI 流水线
gh run list
gh run watch

# 4. 验证镜像更新
aws ecr describe-images --repository-name sre-capstone/user-service \
  --query 'sort_by(imageDetails,& imagePushedAt)[-1]'

# 5. 验证 ArgoCD 同步
argocd app get sre-capstone-dev

# 6. 验证应用更新
kubectl get pods -n sre-capstone
kubectl logs -n sre-capstone -l app.kubernetes.io/name=user-service --tail=20
```

**验证标准**：
- 代码修改后 CI 自动运行
- 新镜像构建并推送
- ArgoCD 自动同步到集群
- 应用更新无停机

---

## 🎯 面试题精选

### 问题 1：CI 和 CD 的区别是什么？

**参考答案**：

- **CI (Continuous Integration)**：代码提交后自动运行测试、构建、安全扫描
- **CD (Continuous Delivery)**：CI 通过后自动部署到预发布环境
- **CD (Continuous Deployment)**：CI 通过后自动部署到生产环境

本项目使用 CI + GitOps CD：
- CI：GitHub Actions 负责测试和构建
- CD：ArgoCD 负责部署

### 问题 2：GitOps 的原理和优势是什么？

**参考答案**：

**原理**：
- Git 仓库是唯一真实来源
- 声明式配置描述期望状态
- 自动化控制器持续同步

**优势**：
- 版本控制：所有变更可追溯
- 自动回滚：Git revert 即可
- 安全性：不需要直接访问集群
- 协作：PR Review 流程

### 问题 3：ArgoCD 如何实现自动同步？

**参考答案**：

```yaml
syncPolicy:
  automated:
    prune: true      # 删除 Git 中不存在的资源
    selfHeal: true   # 修复手动更改
    allowEmpty: false
```

工作流程：
1. Git 仓库变更
2. ArgoCD 检测到差异
3. 自动同步到集群
4. prune 删除多余资源
5. selfHeal 修复手动更改

### 问题 4：如何实现零停机部署？

**参考答案**：

1. **Rolling Update**：K8s 默认策略
2. **Readiness Probe**：新 Pod 就绪后才接收流量
3. **PDB**：保证最少可用实例
4. **Graceful Shutdown**：处理完当前请求后关闭
5. **Canary Deployment**：渐进式发布
6. **Blue-Green Deployment**：蓝绿部署

### 问题 5：为什么使用 OIDC 而不是 Access Key？

**参考答案**：

| 特性 | OIDC | Access Key |
|------|------|-----------|
| 安全性 | 高 (短期凭证) | 低 (长期凭证) |
| 轮换 | 自动 | 手动 |
| 范围 | 细粒度 | 宽泛 |
| 管理 | 无需存储密钥 | 需要 Secret 管理 |

OIDC 优势：
- 短期临时凭证
- 无需在 GitHub 存储 AWS 密钥
- 细粒度权限控制
- 自动轮换

### 问题 6：如何回滚失败的部署？

**参考答案**：

```bash
# ArgoCD 回滚
argocd app history sre-capstone-dev
argocd app rollback sre-capstone-dev <revision>

# 或者 Git 回滚
git revert HEAD
git push origin main
# ArgoCD 自动同步回滚
```

### 问题 7：安全扫描应该在 CI 的哪个阶段执行？

**参考答案**：

安全扫描应该在镜像构建之后、部署之前执行：

```
代码扫描 (SAST) → 测试 → 构建镜像 → 镜像扫描 (Trivy) → 部署
```

扫描类型：
- **SAST**：代码静态分析 (CodeQL, SonarQube)
- **SCA**：依赖漏洞扫描 (Dependabot)
- **Container Scan**：镜像漏洞扫描 (Trivy)
- **DAST**：运行时安全测试 (OWASP ZAP)

---

## 📚 深入阅读

### 官方文档
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)

### 推荐资源
- [GitOps Guide](https://www.gitops.tech/)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions)

---

## ✅ 自检清单

- [ ] 理解 CI/CD 流水线架构
- [ ] 能编写 GitHub Actions 工作流
- [ ] 能配置镜像构建和推送
- [ ] 能集成 Trivy 安全扫描
- [ ] 能部署和配置 ArgoCD
- [ ] 理解 GitOps 原理和优势
- [ ] 能配置自动同步和回滚
- [ ] 理解 OIDC 认证的优势
- [ ] 完成 3 个实战练习
- [ ] 能回答相关面试题

---

*由 SRE 学习计划自动生成 | 2026-05-03*
