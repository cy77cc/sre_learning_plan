# Day 153: 完整 CI/CD 流程

> 📅 日期：2026-05-03
> 📖 学习主题：端到端 CI/CD 流水线（代码提交 → 测试 → 构建 → 扫描 → 推送 → 部署）、环境管理、审批门控、回滚策略、通知集成
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 150（Jenkins）、Day 151（构建工具集成）、Day 152（CI 中构建和推送镜像）

## 🎯 学习目标

- 能够设计和实现端到端的 CI/CD 流水线
- 掌握多环境管理策略（dev/staging/production）
- 理解审批门控机制与合规要求
- 精通回滚策略（自动/手动、镜像/配置回滚）
- 能够集成通知系统（Slack/钉钉/邮件/Webhook）
- 掌握 GitOps 工作流与传统 CI/CD 的结合
- 能够排查 CI/CD 流水线中的常见问题

---

## 📖 核心知识点

### 1. 端到端 CI/CD 流程全景

#### 1.1 完整 CI/CD 流水线架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    完整 CI/CD 流水线架构                                      │
│                                                                             │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │ 代码提交 │──>│  代码   │──>│  构建   │──>│  安全   │──>│  镜像   │     │
│  │ (Push)  │   │  检查   │   │  编译   │   │  扫描   │   │  推送   │     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘     │
│       │             │             │             │             │            │
│       ▼             ▼             ▼             ▼             ▼            │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │ Git Web │   │ Lint    │   │ Unit    │   │ Trivy   │   │ Harbor/ │     │
│  │ Hook    │   │ Format  │   │ Test    │   │ Scan    │   │ GHCR    │     │
│  │         │   │ SAST    │   │ Build   │   │ SBOM    │   │         │     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘     │
│                                                             │              │
│                                                             ▼              │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                        部署阶段                                       ││
│  │                                                                       ││
│  │  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐    ││
│  │  │   DEV    │────>│ STAGING  │────>│ APPROVAL │────>│   PROD   │    ││
│  │  │  环境    │     │  环境    │     │  审批    │     │  环境    │    ││
│  │  │          │     │          │     │          │     │          │    ││
│  │  │ 自动部署 │     │ 自动部署 │     │ 人工审批 │     │ 自动/手动│    ││
│  │  │ 功能测试 │     │ 集成测试 │     │ 变更单   │     │ 灰度发布 │    ││
│  │  │ 开发自测 │     │ E2E 测试 │     │ 安全评审 │     │ 监控告警 │    ││
│  │  └──────────┘     └──────────┘     └──────────┘     └──────────┘    ││
│  │                                                                       ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                                                             │              │
│                                                             ▼              │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                        反馈循环                                       ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             ││
│  │  │ 通知集成 │  │ 监控告警 │  │ 日志分析 │  │ 回滚机制 │             ││
│  │  │ Slack    │  │Prometheus│  │ ELK/Loki │  │ 自动/手动│             ││
│  │  │ 钉钉     │  │ Grafana  │  │          │  │          │             ││
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘             ││
│  └───────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 1.2 流水线阶段详解

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CI/CD 流水线阶段                                   │
│                                                                     │
│  阶段 1: 代码提交（Commit）                                         │
│  ├── Webhook 触发 CI 流水线                                         │
│  ├── 拉取代码（浅克隆优化）                                         │
│  └── 环境准备（Runner 初始化）                                      │
│                                                                     │
│  阶段 2: 代码检查（Lint & SAST）                                    │
│  ├── 代码格式化检查（gofmt, prettier, black）                       │
│  ├── 静态代码分析（golangci-lint, ESLint, SonarQube）              │
│  ├── 依赖安全检查（npm audit, go vuln check）                      │
│  └── 提交规范检查（commitlint）                                     │
│                                                                     │
│  阶段 3: 测试（Test）                                               │
│  ├── 单元测试（Unit Test）                                          │
│  ├── 集成测试（Integration Test）                                   │
│  ├── 测试覆盖率检查（≥80% 门控）                                    │
│  └── 测试报告生成（JUnit XML）                                      │
│                                                                     │
│  阶段 4: 构建（Build）                                              │
│  ├── Docker 多阶段构建                                              │
│  ├── 多架构镜像构建（amd64 + arm64）                                │
│  ├── 构建元数据注入（版本、SHA、时间戳）                            │
│  └── 构建缓存优化                                                   │
│                                                                     │
│  阶段 5: 安全扫描（Security Scan）                                  │
│  ├── 镜像漏洞扫描（Trivy）                                         │
│  ├── Secret 检测（Trivy/TruffleHog）                               │
│  ├── SBOM 生成（SPDX/CycloneDX）                                   │
│  ├── 镜像签名（Cosign）                                             │
│  └── 安全门控（CRITICAL 漏洞阻断）                                  │
│                                                                     │
│  阶段 6: 镜像推送（Registry Push）                                  │
│  ├── 推送到容器镜像仓库（Harbor/ECR/GHCR）                          │
│  ├── 标签策略应用（SemVer + SHA）                                   │
│  └── 镜像元数据更新（OCI annotations）                              │
│                                                                     │
│  阶段 7: 部署（Deploy）                                             │
│  ├── DEV 环境自动部署                                               │
│  ├── STAGING 环境自动部署 + E2E 测试                                │
│  ├── PRODUCTION 审批门控                                            │
│  ├── PRODUCTION 环境部署（滚动更新/金丝雀）                         │
│  └── 部署验证（健康检查、Smoke Test）                                │
│                                                                     │
│  阶段 8: 监控与反馈（Monitor）                                      │
│  ├── 部署状态通知（Slack/钉钉/邮件）                                │
│  ├── 应用性能监控（Prometheus/Grafana）                              │
│  ├── 错误率监控（自动回滚触发）                                      │
│  └── 用户反馈收集                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 2. 端到端 CI/CD 流水线实现

#### 2.1 GitHub Actions 完整流水线

```yaml
# .github/workflows/ci-cd-pipeline.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop, 'release/**']
    tags: ['v*']
  pull_request:
    branches: [main]

# 全局环境变量
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  GO_VERSION: '1.22'

# 权限配置
permissions:
  contents: read
  packages: write
  security-events: write
  id-token: write  # OIDC 用于无密钥认证

# ===== 阶段 1: 代码检查 =====
jobs:
  lint:
    name: Code Lint & Format
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 获取完整历史用于 commitlint

      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: ${{ env.GO_VERSION }}

      - name: golangci-lint
        uses: golangci/golangci-lint-action@v4
        with:
          version: latest
          args: --timeout=5m

      - name: Check formatting
        run: |
          if [ -n "$(gofmt -l .)" ]; then
            echo "Files not formatted:"
            gofmt -l .
            exit 1
          fi

      - name: Commit lint
        uses: wagoid/commitlint-github-action@v5
        if: github.event_name == 'pull_request'

  # ===== 阶段 2: 单元测试 =====
  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: ${{ env.GO_VERSION }}

      - name: Run tests
        run: |
          go test -v -race -coverprofile=coverage.out -covermode=atomic ./...

      - name: Check coverage
        run: |
          COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | sed 's/%//')
          echo "Coverage: ${COVERAGE}%"
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage ${COVERAGE}% is below 80% threshold"
            exit 1
          fi

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.out

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: coverage.out

  # ===== 阶段 3: 构建镜像 =====
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    outputs:
      image-tag: ${{ steps.meta.outputs.version }}
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
        with:
          platforms: linux/amd64,linux/arm64

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Generate metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix=sha-,format=short
            type=ref,event=branch
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}

      - name: Build and push
        id: build
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
            BUILD_TIME=${{ github.event.head_commit.timestamp }}

  # ===== 阶段 4: 安全扫描 =====
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # CRITICAL 漏洞门控
      - name: Scan CRITICAL vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}
          format: 'table'
          severity: 'CRITICAL'
          exit-code: '1'
          ignore-unfixed: true

      # 全量扫描报告（SARIF 上传到 GitHub Security）
      - name: Full vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH,MEDIUM'

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      # 生成 SBOM
      - name: Generate SBOM
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}
          format: 'spdx-json'
          output: 'sbom.spdx.json'

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json

  # ===== 阶段 5: 部署到 DEV =====
  deploy-dev:
    name: Deploy to DEV
    runs-on: ubuntu-latest
    needs: [build, security-scan]
    if: github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main'
    environment:
      name: development
      url: https://dev.example.com
    steps:
      - name: Checkout (K8s manifests)
        uses: actions/checkout@v4
        with:
          repository: myorg/k8s-manifests
          token: ${{ secrets.GITOPS_TOKEN }}

      - name: Update image tag
        run: |
          cd apps/myapp/overlays/dev
          kustomize edit set image \
            myapp=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}

      - name: Commit and push
        run: |
          git config user.name "CI Bot"
          git config user.email "ci@example.com"
          git add .
          git commit -m "chore(dev): update myapp to ${{ needs.build.outputs.image-tag }}"
          git push

      - name: Wait for ArgoCD sync
        run: |
          # 等待 ArgoCD 同步完成
          kubectl wait --for=condition=Ready pod \
            -l app=myapp -n dev --timeout=300s

  # ===== 阶段 6: 部署到 STAGING =====
  deploy-staging:
    name: Deploy to STAGING
    runs-on: ubuntu-latest
    needs: [build, security-scan, deploy-dev]
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/v')
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - name: Checkout (K8s manifests)
        uses: actions/checkout@v4
        with:
          repository: myorg/k8s-manifests
          token: ${{ secrets.GITOPS_TOKEN }}

      - name: Update image tag
        run: |
          cd apps/myapp/overlays/staging
          kustomize edit set image \
            myapp=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}

      - name: Commit and push
        run: |
          git config user.name "CI Bot"
          git config user.email "ci@example.com"
          git add .
          git commit -m "chore(staging): update myapp to ${{ needs.build.outputs.image-tag }}"
          git push

      - name: Wait for deployment
        run: |
          kubectl wait --for=condition=Ready pod \
            -l app=myapp -n staging --timeout=300s

      # E2E 测试
      - name: Run E2E tests
        run: |
          ./scripts/e2e-tests.sh https://staging.example.com

  # ===== 阶段 7: 审批门控 + 生产部署 =====
  deploy-production:
    name: Deploy to PRODUCTION
    runs-on: ubuntu-latest
    needs: [build, security-scan, deploy-staging]
    if: startsWith(github.ref, 'refs/tags/v')
    environment:
      name: production
      url: https://app.example.com
    steps:
      - name: Checkout (K8s manifests)
        uses: actions/checkout@v4
        with:
          repository: myorg/k8s-manifests
          token: ${{ secrets.GITOPS_TOKEN }}

      - name: Update image tag
        run: |
          cd apps/myapp/overlays/production
          kustomize edit set image \
            myapp=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ needs.build.outputs.image-digest }}

      - name: Commit and push
        run: |
          git config user.name "CI Bot"
          git config user.email "ci@example.com"
          git add .
          git commit -m "release(production): deploy myapp ${{ needs.build.outputs.image-tag }}"
          git push

      - name: Wait for deployment
        run: |
          kubectl wait --for=condition=Ready pod \
            -l app=myapp -n production --timeout=600s

      - name: Smoke test
        run: |
          ./scripts/smoke-test.sh https://app.example.com

  # ===== 阶段 8: 通知 =====
  notify:
    name: Send Notifications
    runs-on: ubuntu-latest
    needs: [build, deploy-production]
    if: always()
    steps:
      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: |
            Pipeline: ${{ github.workflow }}
            Branch: ${{ github.ref_name }}
            Image: ${{ needs.build.outputs.image-tag }}
            Status: ${{ job.status }}
          fields: repo,message,commit,author,action,eventName,ref,workflow
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

### 3. 环境管理

#### 3.1 多环境管理策略

```
┌─────────────────────────────────────────────────────────────────────┐
│                    多环境管理架构                                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Git 仓库（环境配置）                                        │   │
│  │                                                             │   │
│  │  k8s-manifests/                                             │   │
│  │  ├── apps/myapp/                                            │   │
│  │  │   ├── base/                                              │   │
│  │  │   │   ├── deployment.yaml                                │   │
│  │  │   │   ├── service.yaml                                   │   │
│  │  │   │   ├── configmap.yaml                                 │   │
│  │  │   │   └── kustomization.yaml                             │   │
│  │  │   └── overlays/                                          │   │
│  │  │       ├── dev/                                           │   │
│  │  │       │   ├── kustomization.yaml                         │   │
│  │  │       │   └── config-patch.yaml                          │   │
│  │  │       ├── staging/                                       │   │
│  │  │       │   ├── kustomization.yaml                         │   │
│  │  │       │   ├── config-patch.yaml                          │   │
│  │  │       │   └── hpa.yaml                                   │   │
│  │  │       └── production/                                    │   │
│  │  │           ├── kustomization.yaml                         │   │
│  │  │           ├── config-patch.yaml                          │   │
│  │  │           ├── hpa.yaml                                   │   │
│  │  │           └── pdb.yaml                                   │   │
│  │  └── infrastructure/                                        │   │
│  │      ├── monitoring/                                        │   │
│  │      ├── ingress/                                           │   │
│  │      └── cert-manager/                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  环境差异配置：                                                      │
│  ┌──────────────┬──────────┬──────────┬──────────┐                │
│  │   配置项      │   DEV    │ STAGING  │   PROD   │                │
│  ├──────────────┼──────────┼──────────┼──────────┤                │
│  │ 副本数       │ 1        │ 2        │ 3+       │                │
│  │ CPU Request  │ 100m     │ 250m     │ 500m     │                │
│  │ Memory Req   │ 128Mi    │ 256Mi    │ 512Mi    │                │
│  │ HPA          │ 关闭     │ 开启     │ 开启     │                │
│  │ PDB          │ 关闭     │ 关闭     │ 开启     │                │
│  │ 日志级别     │ debug    │ info     │ warn     │                │
│  │ TLS          │ 关闭     │ 开启     │ 开启     │                │
│  │ 备份         │ 关闭     │ 每日     │ 每日+跨区│                │
│  └──────────────┴──────────┴──────────┴──────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.2 Kustomize 环境配置

```yaml
# apps/myapp/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml

commonLabels:
  app: myapp
  team: platform

images:
  - name: myapp
    newName: ghcr.io/myorg/myapp
    newTag: latest
```

```yaml
# apps/myapp/base/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: myapp:latest
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
```

```yaml
# apps/myapp/overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base
  - hpa.yaml
  - pdb.yaml

patches:
  - path: config-patch.yaml
  - target:
      kind: Deployment
      name: myapp

commonLabels:
  environment: production

images:
  - name: myapp
    newName: ghcr.io/myorg/myapp
    newTag: v1.0.0
```

```yaml
# apps/myapp/overlays/production/config-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
        - name: myapp
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: "2"
              memory: 2Gi
          env:
            - name: LOG_LEVEL
              value: "warn"
            - name: ENVIRONMENT
              value: "production"
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: myapp
```

```yaml
# apps/myapp/overlays/production/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myapp
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

```yaml
# apps/myapp/overlays/production/pdb.yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: myapp
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: myapp
```

---

### 4. 审批门控

#### 4.1 审批门控策略

```
┌─────────────────────────────────────────────────────────────────────┐
│                    审批门控策略                                       │
│                                                                     │
│  自动审批（无需人工干预）：                                          │
│  ├── DEV 环境部署                                                   │
│  ├── STAGING 环境部署（main 分支）                                  │
│  ├── 代码检查通过（lint + test）                                    │
│  └── 安全扫描通过（无 CRITICAL 漏洞）                               │
│                                                                     │
│  人工审批（必须经过审批）：                                          │
│  ├── PRODUCTION 部署                                                │
│  │   ├── 技术负责人审批                                            │
│  │   ├── SRE 团队审批                                              │
│  │   └── 变更管理委员会审批（CAB）                                  │
│  ├── 紧急修复（Hotfix）                                             │
│  │   ├── 值班 SRE 审批                                             │
│  │   └── 事后补充变更单                                            │
│  └── 基础设施变更                                                   │
│      ├── 网络策略变更                                               │
│      ├── 存储卷变更                                                 │
│      └── RBAC 权限变更                                              │
│                                                                     │
│  审批工具：                                                          │
│  ├── GitHub Environments（内置审批）                                │
│  ├── ServiceNow（企业变更管理）                                     │
│  ├── Jira Service Management                                       │
│  └── 自建审批系统（Webhook + API）                                  │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2 GitHub Environments 审批配置

```yaml
# GitHub Repository Settings → Environments → production
# 配置以下内容：

# 1. Required reviewers（必需审批人）
#    - sre-team-lead
#    - platform-engineer
#    - security-team

# 2. Wait timer（等待时间）
#    - 0 分钟（立即审批）或 15 分钟（冷静期）

# 3. Deployment branches（部署分支限制）
#    - 仅 main 分支和 v* tag

# 4. Environment secrets（环境级别密钥）
#    - KUBECONFIG_PROD
#    - DATABASE_URL_PROD
```

```yaml
# 在工作流中使用环境审批
jobs:
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [build, security-scan, deploy-staging]
    if: startsWith(github.ref, 'refs/tags/v')
    # 关键：引用需要审批的 environment
    environment:
      name: production
      url: https://app.example.com
    steps:
      - name: Deploy
        run: |
          echo "Deploying to production..."
          # 部署逻辑
```

#### 4.3 变更管理集成

```yaml
# ServiceNow 变更管理集成
name: Change Management

on:
  deployment_status:

jobs:
  create-change-request:
    if: github.event.deployment.environment == 'production'
    runs-on: ubuntu-latest
    steps:
      - name: Create ServiceNow Change Request
        run: |
          curl -X POST "https://instance.servicenow.com/api/now/table/change_request" \
            -H "Authorization: Bearer ${{ secrets.SNOW_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{
              "short_description": "Deploy myapp ${{ github.event.deployment.ref }}",
              "description": "Automated deployment via CI/CD pipeline",
              "type": "normal",
              "risk": "low",
              "impact": "medium",
              "assignment_group": "SRE Team",
              "start_date": "${{ github.event.deployment.created_at }}",
              "end_date": "${{ github.event.deployment.created_at }}"
            }'
```

---

### 5. 回滚策略

#### 5.1 回滚策略全景

```
┌─────────────────────────────────────────────────────────────────────┐
│                    回滚策略                                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  自动回滚                                                    │   │
│  │                                                             │   │
│  │  触发条件：                                                  │   │
│  │  ├── 健康检查失败（Pod CrashLoopBackOff）                   │   │
│  │  ├── 就绪探针持续失败（Readiness Probe）                    │   │
│  │  ├── 错误率超过阈值（>5% 5xx 错误）                         │   │
│  │  ├── 延迟超过阈值（P99 > 2s）                               │   │
│  │  └── 自定义指标异常（队列积压、内存 OOM）                   │   │
│  │                                                             │   │
│  │  回滚动作：                                                  │   │
│  │  ├── Kubernetes: kubectl rollout undo deployment/myapp      │   │
│  │  ├── GitOps: revert Git commit                              │   │
│  │  ├── ArgoCD: rollback to previous Revision                  │   │
│  │  └── Flagger: 自动回滚 Canary                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  手动回滚                                                    │   │
│  │                                                             │   │
│  │  场景：                                                      │   │
│  │  ├── 逻辑 Bug（功能不正确但不崩溃）                         │   │
│  │  ├── 性能退化（延迟升高但未超阈值）                         │   │
│  │  ├── 业务决策回滚（产品要求撤回功能）                       │   │
│  │  └── 合规要求（安全审计发现问题）                           │   │
│  │                                                             │   │
│  │  方式：                                                      │   │
│  │  ├── kubectl rollout undo                                   │   │
│  │  ├── Git revert + ArgoCD sync                               │   │
│  │  ├── Helm rollback                                          │   │
│  │  └── 镜像标签回退到上一个版本                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  回滚策略对比                                                │   │
│  │                                                             │   │
│  │  ┌──────────────┬──────────────┬──────────────┐             │   │
│  │  │   方法       │   速度       │   适用场景   │             │   │
│  │  ├──────────────┼──────────────┼──────────────┤             │   │
│  │  │ 镜像回退     │ 最快（秒级）│ 代码问题     │             │   │
│  │  │ Git revert   │ 中等（分钟）│ 配置+代码    │             │   │
│  │  │ Helm rollback│ 中等（分钟）│ Helm 部署    │             │   │
│  │  │ 数据库回滚   │ 慢（小时级）│ 数据变更     │             │   │
│  │  └──────────────┴──────────────┴──────────────┘             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.2 自动回滚实现

```yaml
# Kubernetes Deployment 自动回滚配置
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  revisionHistoryLimit: 10  # 保留 10 个历史版本用于回滚
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
        - name: myapp
          image: myapp:v1.2.0
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 3
          # 启动探针（防止慢启动被误杀）
          startupProbe:
            httpGet:
              path: /healthz
              port: 8080
            failureThreshold: 30
            periodSeconds: 10
```

```bash
# 手动回滚命令
# 查看部署历史
kubectl rollout history deployment/myapp -n production

# 回滚到上一个版本
kubectl rollout undo deployment/myapp -n production

# 回滚到指定版本
kubectl rollout undo deployment/myapp -n production --to-revision=3

# 查看回滚状态
kubectl rollout status deployment/myapp -n production
```

#### 5.3 GitOps 回滚

```bash
# GitOps 回滚流程
# 1. 查看 Git 历史
git log --oneline -10

# 2. Revert 上一个部署 commit
git revert HEAD

# 3. 推送到 Git 仓库
git push origin main

# 4. ArgoCD 自动同步（如果配置了自动同步）
# 或手动触发同步
argocd app sync myapp

# 5. 验证回滚
argocd app get myapp
kubectl get pods -n production -l app=myapp
```

#### 5.4 自动回滚脚本

```bash
#!/bin/bash
# scripts/auto-rollback.sh
# 自动回滚脚本，用于 CI/CD 流水线

set -euo pipefail

NAMESPACE="${1:-production}"
APP_NAME="${2:-myapp}"
HEALTH_URL="${3:-https://app.example.com/healthz}"
MAX_RETRIES=30
RETRY_INTERVAL=10

echo "=== 部署健康检查 ==="
echo "Namespace: ${NAMESPACE}"
echo "App: ${APP_NAME}"
echo "Health URL: ${HEALTH_URL}"

# 等待部署完成
echo "等待部署完成..."
if ! kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=300s; then
    echo "ERROR: 部署超时，执行回滚"
    kubectl rollout undo deployment/${APP_NAME} -n ${NAMESPACE}
    kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=300s
    echo "回滚完成"
    exit 1
fi

# 健康检查
echo "执行健康检查..."
for i in $(seq 1 ${MAX_RETRIES}); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${HEALTH_URL} || echo "000")
    if [ "${HTTP_CODE}" = "200" ]; then
        echo "健康检查通过 (attempt ${i}/${MAX_RETRIES})"
        exit 0
    fi
    echo "健康检查失败: HTTP ${HTTP_CODE} (attempt ${i}/${MAX_RETRIES})"
    sleep ${RETRY_INTERVAL}
done

echo "ERROR: 健康检查持续失败，执行回滚"
kubectl rollout undo deployment/${APP_NAME} -n ${NAMESPACE}
kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=300s
echo "回滚完成"
exit 1
```

---

### 6. 通知集成

#### 6.1 通知系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    通知集成架构                                       │
│                                                                     │
│  ┌──────────────┐                                                  │
│  │  CI/CD 事件   │                                                  │
│  │  Pipeline     │                                                  │
│  └──────┬───────┘                                                  │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  通知路由引擎                                                │   │
│  │                                                             │   │
│  │  事件类型 → 渠道选择 → 模板渲染 → 发送                      │   │
│  └──────┬──────────────────────────────────────────────────────┘   │
│         │                                                           │
│         ├───────────┬───────────┬───────────┬───────────┐          │
│         ▼           ▼           ▼           ▼           ▼          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │  Slack   │ │  钉钉    │ │  邮件    │ │ PagerDuty│ │ Webhook  ││
│  │          │ │          │ │          │ │          │ │          ││
│  │ 日常通知 │ │ 日常通知 │ │ 正式通知 │ │ 紧急告警 │ │ 自定义   ││
│  │ 开发团队 │ │ 开发团队 │ │ 管理层   │ │ On-call  │ │ 集成     ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘│
│                                                                     │
│  通知规则：                                                          │
│  ├── 部署成功 → Slack #deployments 频道                             │
│  ├── 部署失败 → Slack #alerts + PagerDuty                          │
│  ├── 安全扫描告警 → Slack #security + 邮件                         │
│  ├── 审批请求 → 钉钉/Slack @审批人                                  │
│  └── 生产变更 → 邮件 + 变更管理系统                                │
└─────────────────────────────────────────────────────────────────────┘
```

#### 6.2 Slack 通知配置

```yaml
# GitHub Actions Slack 通知
name: Slack Notification

on:
  workflow_run:
    workflows: ["CI/CD Pipeline"]
    types: [completed]

jobs:
  notify:
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Determine status
        id: status
        run: |
          if [ "${{ github.event.workflow_run.conclusion }}" = "success" ]; then
            echo "emoji=✅" >> $GITHUB_OUTPUT
            echo "color=#36a64f" >> $GITHUB_OUTPUT
            echo "status=SUCCESS" >> $GITHUB_OUTPUT
          else
            echo "emoji=❌" >> $GITHUB_OUTPUT
            echo "color=#dc3545" >> $GITHUB_OUTPUT
            echo "status=FAILED" >> $GITHUB_OUTPUT
          fi

      - name: Send Slack notification
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "attachments": [{
                "color": "${{ steps.status.outputs.color }}",
                "blocks": [
                  {
                    "type": "header",
                    "text": {
                      "type": "plain_text",
                      "text": "${{ steps.status.outputs.emoji }} CI/CD Pipeline ${{ steps.status.outputs.status }}"
                    }
                  },
                  {
                    "type": "section",
                    "fields": [
                      {"type": "mrkdwn", "text": "*Repository:*\n${{ github.repository }}"},
                      {"type": "mrkdwn", "text": "*Branch:*\n${{ github.event.workflow_run.head_branch }}"},
                      {"type": "mrkdwn", "text": "*Commit:*\n${{ github.event.workflow_run.head_sha }}"},
                      {"type": "mrkdwn", "text": "*Triggered by:*\n${{ github.event.workflow_run.actor.login }}"}
                    ]
                  },
                  {
                    "type": "actions",
                    "elements": [
                      {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Pipeline"},
                        "url": "${{ github.event.workflow_run.html_url }}"
                      }
                    ]
                  }
                ]
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK
```

#### 6.3 钉钉通知配置

```yaml
# 钉钉通知
- name: Send DingTalk notification
  uses: zcong1993/setup-dingding@v3
  with:
    dingding-token: ${{ secrets.DINGTALK_TOKEN }}
    notify-every-success: false
    notification-title: |
      ${{ job.status == 'success' && '✅' || '❌' }} CI/CD Pipeline
    notification-content: |
      **Repository:** ${{ github.repository }}
      **Branch:** ${{ github.ref_name }}
      **Commit:** ${{ github.sha }}
      **Status:** ${{ job.status }}
      **Author:** ${{ github.actor }}
```

---

### 7. GitOps 与传统 CI/CD 对比

```
┌─────────────────────────────────────────────────────────────────────┐
│              GitOps vs 传统 CI/CD                                    │
│                                                                     │
│  传统 CI/CD：                                                        │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐             │
│  │  Code  │───>│  CI    │───>│  CD    │───>│  K8s   │             │
│  │  Push  │    │  Build │    │ Deploy │    │ Cluster│             │
│  └────────┘    └────────┘    └────────┘    └────────┘             │
│  CI 直接操作集群，kubectl apply                                      │
│                                                                     │
│  GitOps：                                                            │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐             │
│  │  Code  │───>│  CI    │───>│  Git   │───>│ ArgoCD │             │
│  │  Push  │    │  Build │    │ (Config)│   │ Sync   │             │
│  └────────┘    └────────┘    └────────┘    └───┬────┘             │
│                                                 │                   │
│                                                 ▼                   │
│                                            ┌────────┐             │
│                                            │  K8s   │             │
│                                            │ Cluster│             │
│                                            └────────┘             │
│  Git 是唯一事实来源，ArgoCD 监听 Git 并同步到集群                   │
│                                                                     │
│  GitOps 优势：                                                       │
│  ├── 声明式：期望状态在 Git 中声明                                  │
│  ├── 版本化：所有变更都有 Git 历史                                  │
│  ├── 可审计：谁在什么时候改了什么                                   │
│  ├── 可回滚：Git revert 即可回滚                                    │
│  ├── 安全：CI 不需要集群访问权限                                    │
│  └── 一致性：多集群使用同一配置源                                   │
│                                                                     │
│  GitOps 挑战：                                                       │
│  ├── 学习曲线：需要理解 GitOps 工作流                              │
│  ├── 密钥管理：Secret 不能直接存 Git                                │
│  ├── 镜像标签：需要 Image Updater 自动更新                         │
│  └── 调试困难：同步状态与实际状态可能不一致                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 8. SRE 实战案例

#### 8.1 案例：某电商平台的 CI/CD 流程设计

**背景：** 日均 100+ 次部署，覆盖 50+ 微服务，要求零停机部署。

```
┌─────────────────────────────────────────────────────────────────────┐
│                    电商平台 CI/CD 架构                                │
│                                                                     │
│  开发流程：                                                          │
│  1. 开发者创建 feature 分支                                         │
│  2. 提交 PR → 触发 CI（lint + test + scan）                         │
│  3. PR 合并到 main → 触发构建 + 推送镜像                            │
│  4. 自动部署到 DEV 环境                                             │
│  5. E2E 测试通过 → 自动部署到 STAGING                               │
│  6. STAGING 验证通过 → 创建 Release Tag                             │
│  7. Tag 触发生产部署流程                                             │
│  8. 技术负责人审批 → 金丝雀发布 → 全量发布                          │
│                                                                     │
│  关键指标：                                                          │
│  ├── 提交到部署时间：< 30 分钟                                     │
│  ├── 部署频率：100+/天                                              │
│  ├── 变更失败率：< 5%                                               │
│  ├── 平均回滚时间：< 5 分钟                                        │
│  └── 生产可用性：99.95%                                             │
│                                                                     │
│  技术栈：                                                            │
│  ├── CI: GitHub Actions                                             │
│  ├── CD: ArgoCD (GitOps)                                           │
│  ├── 镜像仓库: Harbor                                              │
│  ├── 配置管理: Kustomize                                            │
│  ├── 金丝雀发布: Argo Rollouts                                      │
│  ├── 监控: Prometheus + Grafana                                     │
│  ├── 通知: Slack + PagerDuty                                        │
│  └── 变更管理: ServiceNow                                           │
└─────────────────────────────────────────────────────────────────────┘
```

#### 8.2 案例：CI/CD 流水线故障排查

**常见问题与排查：**

```
┌─────────────────────────────────────────────────────────────────────┐
│              CI/CD 流水线常见故障排查                                  │
│                                                                     │
│  问题 1: 构建超时                                                   │
│  ├── 原因：依赖下载慢、缓存失效、Runner 资源不足                    │
│  ├── 排查：检查构建日志、缓存命中率、Runner 负载                    │
│  └── 解决：优化缓存策略、使用自托管 Runner、增加超时时间            │
│                                                                     │
│  问题 2: 镜像推送失败                                               │
│  ├── 原因：认证失败、Registry 不可达、镜像过大                      │
│  ├── 排查：检查 Registry 凭证、网络连通性、镜像大小                 │
│  └── 解决：刷新凭证、优化镜像大小、配置 Registry 代理              │
│                                                                     │
│  问题 3: 安全扫描误报                                               │
│  ├── 原因：漏洞库版本、基础镜像误报、开发依赖误报                  │
│  ├── 排查：检查 CVE 详情、评估实际影响、确认误报                    │
│  └── 解决：添加 .trivyignore、升级基础镜像、等待修复               │
│                                                                     │
│  问题 4: 部署同步失败                                               │
│  ├── 原因：K8s 资源不足、镜像拉取失败、配置错误                    │
│  ├── 排查：kubectl describe pod、ArgoCD 同步状态                    │
│  └── 解决：扩容集群、检查镜像、修复配置                             │
│                                                                     │
│  问题 5: 回滚后问题未解决                                           │
│  ├── 原因：数据库 schema 变更、配置缓存、CDN 缓存                  │
│  ├── 排查：检查数据库版本、清理缓存、验证配置                       │
│  └── 解决：前向修复（forward fix）、数据库回滚脚本                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 💻 实战练习

### 练习 1：搭建完整的 CI/CD 流水线

**目标：** 从零搭建一个包含代码检查、测试、构建、扫描、部署的完整流水线

```bash
# 步骤 1: 创建示例项目
mkdir -p cicd-demo && cd cicd-demo
git init

# 步骤 2: 创建 Go 应用
cat > main.go << 'EOF'
package main

import (
    "encoding/json"
    "log"
    "net/http"
    "os"
    "time"
)

type HealthResponse struct {
    Status    string `json:"status"`
    Version   string `json:"version"`
    Timestamp string `json:"timestamp"`
}

func main() {
    version := os.Getenv("APP_VERSION")
    if version == "" {
        version = "dev"
    }

    http.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(HealthResponse{
            Status:    "ok",
            Version:   version,
            Timestamp: time.Now().UTC().Format(time.RFC3339),
        })
    })

    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte("Hello, CI/CD!"))
    })

    log.Println("Server starting on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}
EOF

cat > main_test.go << 'EOF'
package main

import (
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"
)

func TestHealthEndpoint(t *testing.T) {
    req := httptest.NewRequest("GET", "/healthz", nil)
    w := httptest.NewRecorder()

    handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(HealthResponse{Status: "ok"})
    })

    handler.ServeHTTP(w, req)

    if w.Code != http.StatusOK {
        t.Errorf("expected status 200, got %d", w.Code)
    }

    var resp HealthResponse
    json.NewDecoder(w.Body).Decode(&resp)
    if resp.Status != "ok" {
        t.Errorf("expected status ok, got %s", resp.Status)
    }
}
EOF

go mod init cicd-demo

# 步骤 3: 创建 Dockerfile
cat > Dockerfile << 'EOF'
FROM --platform=$BUILDPLATFORM golang:1.22-alpine AS builder
ARG TARGETOS TARGETARCH
WORKDIR /app
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH \
    go build -o server .

FROM scratch
COPY --from=builder /app/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
EOF

# 步骤 4: 创建 GitHub Actions 工作流（参考上述完整配置）
mkdir -p .github/workflows
# 将上述 ci-cd-pipeline.yml 内容写入此文件
```

### 练习 2：配置多环境 Kustomize 配置

**目标：** 创建 dev/staging/production 三个环境的 Kustomize 配置

```bash
# 创建目录结构
mkdir -p k8s-manifests/apps/myapp/{base,overlays/{dev,staging,production}}

# base 配置（参考上述内容）
# 每个 overlay 创建对应的 kustomization.yaml 和环境特定补丁
# 确保三个环境的差异：
# - dev: 1 副本，低资源限制，debug 日志
# - staging: 2 副本，中等资源，info 日志
# - production: 3 副本，高资源限制，warn 日志，HPA + PDB
```

### 练习 3：实现自动回滚机制

**目标：** 创建部署后的健康检查和自动回滚脚本

```bash
# 创建 scripts/deploy-and-verify.sh
cat > scripts/deploy-and-verify.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

NAMESPACE="${1:-production}"
APP_NAME="${2:-myapp}"
EXPECTED_VERSION="${3:-}"
MAX_WAIT=300
CHECK_INTERVAL=10

echo "=== 部署验证 ==="
echo "Namespace: ${NAMESPACE}"
echo "App: ${APP_NAME}"
echo "Expected Version: ${EXPECTED_VERSION}"

# 等待 rollout 完成
echo "等待 Deployment rollout..."
if ! kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=${MAX_WAIT}s; then
    echo "Rollout 超时，执行回滚..."
    kubectl rollout undo deployment/${APP_NAME} -n ${NAMESPACE}
    exit 1
fi

# 检查 Pod 状态
echo "检查 Pod 状态..."
READY_PODS=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} \
    -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | wc -w)
TOTAL_PODS=$(kubectl get deployment ${APP_NAME} -n ${NAMESPACE} \
    -o jsonpath='{.spec.replicas}')

if [ "${READY_PODS}" -lt "${TOTAL_PODS}" ]; then
    echo "Pod 未全部就绪: ${READY_PODS}/${TOTAL_PODS}，执行回滚..."
    kubectl rollout undo deployment/${APP_NAME} -n ${NAMESPACE}
    exit 1
fi

# 检查应用健康端点
echo "检查应用健康..."
for i in $(seq 1 30); do
    POD=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o jsonpath='{.items[0].metadata.name}')
    HTTP_CODE=$(kubectl exec -n ${NAMESPACE} ${POD} -- \
        wget -q -O /dev/null -S http://localhost:8080/healthz 2>&1 | \
        grep "HTTP/" | awk '{print $2}' || echo "000")

    if [ "${HTTP_CODE}" = "200" ]; then
        echo "健康检查通过"
        echo "=== 部署成功 ==="
        exit 0
    fi
    echo "健康检查中... (${i}/30) HTTP ${HTTP_CODE}"
    sleep ${CHECK_INTERVAL}
done

echo "健康检查失败，执行回滚..."
kubectl rollout undo deployment/${APP_NAME} -n ${NAMESPACE}
exit 1
SCRIPT

chmod +x scripts/deploy-and-verify.sh
```

---

## 🎯 面试题精选

### 面试题 1：描述一个完整的 CI/CD 流水线应该包含哪些阶段？

**答案：**

完整的 CI/CD 流水线应包含以下阶段：

1. **代码提交**：Webhook 触发，浅克隆代码
2. **代码检查**：Lint、格式化、静态分析（SAST）、commit 规范检查
3. **测试**：单元测试、集成测试、覆盖率检查（>=80% 门控）
4. **构建**：Docker 多阶段构建、多架构镜像、构建缓存优化
5. **安全扫描**：Trivy 镜像扫描、Secret 检测、SBOM 生成、镜像签名
6. **镜像推送**：推送到 Registry、标签策略应用
7. **部署**：DEV 自动 → STAGING 自动 → PROD 审批门控
8. **验证**：健康检查、Smoke Test、E2E 测试
9. **监控**：部署状态通知、应用性能监控、自动回滚

关键原则：快速反馈（lint/test < 5min）、安全左移（扫描尽早）、不可变镜像（构建一次到处部署）。

### 面试题 2：如何设计多环境管理策略？GitOps 模式下如何管理环境差异？

**答案：**

多环境管理策略：

1. **独立集群/命名空间**：DEV 使用独立集群或 namespace，STAGING 和 PROD 使用独立集群
2. **配置分层**：使用 Kustomize 的 base/overlay 结构
   - base：公共配置（deployment template、service、configmap）
   - overlay/dev：1 副本、低资源、debug 日志
   - overlay/staging：2 副本、中等资源、info 日志
   - overlay/production：3+ 副本、高资源、HPA + PDB、warn 日志
3. **独立 Git 仓库**：应用代码仓库与 K8s 配置仓库分离
4. **环境变量注入**：不同环境的 ConfigMap/Secret 通过 overlay 注入

GitOps 环境差异管理：
- 每个环境对应 Git 的一个目录或分支
- ArgoCD Application 指向不同目录
- 镜像标签通过 Image Updater 自动更新
- 密钥使用 Sealed Secrets 或 Vault

### 面试题 3：什么是审批门控？生产部署需要哪些审批？

**答案：**

审批门控是 CI/CD 流水线中的人工检查点，确保变更在进入下一阶段前经过审核。

**生产部署审批层次：**
1. **CI 自动门控**：代码检查、测试、安全扫描通过
2. **技术审批**：技术负责人 review 代码变更
3. **SRE 审批**：SRE 团队评估部署风险和影响
4. **变更管理审批**：CAB（Change Advisory Board）审批重大变更
5. **安全审批**：安全团队审批涉及安全敏感的变更

**实现方式：**
- GitHub Environments 配置 Required Reviewers
- ServiceNow 集成变更管理
- Slack 通知审批人
- 配置 Wait Timer（冷静期）

### 面试题 4：如何实现零停机回滚？对比不同回滚策略

**答案：**

**零停机回滚策略：**

1. **Kubernetes rollout undo**（最快）：
   - 直接回退 Deployment 到上一个 Revision
   - 秒级完成，适合代码问题
   - 需要 revisionHistoryLimit 配置

2. **Git revert + ArgoCD sync**（最规范）：
   - Git revert 上一个 commit
   - ArgoCD 自动/手动同步
   - 保留完整审计日志

3. **Helm rollback**（Helm 项目）：
   - `helm rollback <release> <revision>`
   - 回退 Helm Release 到指定版本

4. **镜像标签回退**（最灵活）：
   - 修改部署清单中的镜像标签为上一个版本
   - 适用于标签可变的场景

**选择策略：**
- 代码问题 → kubectl rollout undo（最快）
- 配置+代码问题 → Git revert（最安全）
- 数据库变更 → 需要前向修复（forward fix）

### 面试题 5：GitOps 与传统 CI/CD 有什么区别？各自的优缺点是什么？

**答案：**

| 方面 | 传统 CI/CD | GitOps |
|------|-----------|--------|
| 部署方式 | CI 直接 kubectl apply | ArgoCD 监听 Git 同步 |
| 事实来源 | 集群当前状态 | Git 仓库 |
| 审计 | CI 日志 | Git 历史 |
| 回滚 | CI 回滚或 kubectl | Git revert |
| 权限 | CI 需要集群权限 | 只有 ArgoCD 需要 |
| 多集群 | 每个集群单独配置 | 同一 Git 仓库多集群 |

**GitOps 优势：** 声明式、版本化、可审计、可回滚、安全性高
**GitOps 挑战：** 学习曲线、密钥管理、镜像标签更新、调试复杂度

### 面试题 6：如何设计 CI/CD 中的通知策略？

**答案：**

通知策略应根据事件类型和紧急程度分级：

1. **日常通知**（Slack/钉钉）：
   - 部署成功/失败通知
   - PR 状态变更
   - 定期构建状态汇总

2. **紧急告警**（PagerDuty/电话）：
   - 生产部署失败
   - 安全扫描发现 CRITICAL 漏洞
   - 自动回滚触发

3. **正式通知**（邮件）：
   - 生产变更通知
   - 安全漏洞报告
   - 周报/月报

4. **通知内容**：事件类型、影响范围、执行人、时间、相关链接

### 面试题 7：如何确保 CI/CD 流水线的安全性？

**答案：**

1. **Secret 管理**：
   - 使用 CI 平台的 Secrets 功能
   - 使用 OIDC 无密钥认证
   - 定期轮换凭证
   - 不在日志中输出 Secret

2. **代码安全**：
   - SAST 静态代码分析
   - 依赖安全检查（npm audit, go vuln）
   - 提交签名验证

3. **镜像安全**：
   - Trivy 漏洞扫描
   - SBOM 生成
   - Cosign 镜像签名
   - 准入控制验证签名

4. **权限控制**：
   - CI 服务账号最小权限
   - GitHub Environments 审批
   - RBAC 限制集群访问
   - 审计日志记录所有操作

### 面试题 8：描述 GitOps 模式下如何处理数据库 schema 迁移

**答案：**

数据库 schema 迁移是 GitOps 模式下的难点，因为迁移是有状态操作，不能简单声明式管理。

**推荐方案：**

1. **Init Container / Job**：
   - 在应用 Deployment 中添加 Init Container 执行迁移
   - 迁移成功后应用才启动
   - 使用 Flyway、Liquibase、golang-migrate 等工具

2. **ArgoCD Sync Hook**：
   - 使用 `argocd.argoproj.io/hook: PreSync` 注解
   - 在应用部署前自动执行迁移 Job
   - 迁移失败则阻断部署

3. **独立迁移流水线**：
   - 迁移作为独立的 CI/CD 流水线
   - 先迁移数据库，再部署应用
   - 迁移和部署解耦，可独立回滚

4. **关键原则**：
   - 迁移必须是幂等的（可重复执行）
   - 迁移必须是可回滚的（down migration）
   - 先迁移再部署，先回滚部署再回滚迁移
   - 大表迁移使用 online DDL 工具

---

## 📚 深入阅读

1. **Google DORA State of DevOps** - https://dora.dev/
2. **Accelerate (Nicole Forsgren)** - DevOps 关键指标
3. **ArgoCD Best Practices** - https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/
4. **GitHub Actions Documentation** - https://docs.github.com/en/actions
5. **Kustomize Documentation** - https://kustomize.io/
6. **The Phoenix Project** - DevOps 文化
7. **Site Reliability Engineering (Google SRE Book)** - https://sre.google/sre-book/table-of-contents/
8. **Flagger Progressive Delivery** - https://flagger.app/

---

## ✅ 自检清单

- [ ] 能够设计端到端的 CI/CD 流水线（代码提交到生产部署）
- [ ] 理解多环境管理策略（dev/staging/production）
- [ ] 掌握 Kustomize 的 base/overlay 结构
- [ ] 能够配置 GitHub Environments 审批门控
- [ ] 理解自动回滚和手动回滚的场景和方法
- [ ] 能够实现 kubectl rollout undo 和 Git revert 回滚
- [ ] 掌握 Slack/钉钉通知集成配置
- [ ] 理解 GitOps 与传统 CI/CD 的区别和优缺点
- [ ] 能够排查 CI/CD 流水线中的常见故障
- [ ] 掌握安全扫描门控策略设计
- [ ] 理解数据库 schema 迁移在 GitOps 中的处理方式
- [ ] 能够设计 CI/CD 通知分级策略
