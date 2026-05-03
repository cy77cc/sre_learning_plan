# Day 160: 完整 GitOps 流水线

> 📅 日期：2026-05-03
> 📖 学习主题：完整 GitOps 流水线（端到端流水线设计, GitOps 最佳实践, 监控集成, 告警, 回滚, 审计, 文档化, 综合项目）
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 154 (ArgoCD), Day 157 (多环境管理), Day 158 (混沌工程), Day 159 (安全扫描集成)

---

## 🎯 学习目标

完成本日学习后，你将能够：

1. 设计和实现端到端的 GitOps 流水线
2. 将安全扫描、多环境管理、监控告警完整集成
3. 实现自动回滚和审计追溯机制
4. 掌握 GitOps 最佳实践和常见陷阱
5. 完成一个综合实战项目，展示完整的 GitOps 能力

---

## 📖 核心知识点

### 1. 完整 GitOps 流水线架构

#### 1.1 端到端流水线总览

```
┌──────────────────────────────────────────────────────────────────────┐
│                    完整 GitOps 流水线架构                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                     开发者工作流                              │    │
│  │                                                              │    │
│  │  本地开发 ──▶ Pre-commit ──▶ Push ──▶ Create PR              │    │
│  │     │            │                        │                  │    │
│  │     │      Secret扫描                   Code Review          │    │
│  │     │      Lint检查                     自动化检查            │    │
│  └─────┼────────────┼────────────────────────┼──────────────────┘    │
│        │            │                        │                       │
│  ┌─────┴────────────┴────────────────────────┴──────────────────┐   │
│  │                     CI 流水线 (GitHub Actions)                 │   │
│  │                                                              │   │
│  │  Stage 1          Stage 2          Stage 3        Stage 4   │   │
│  │  ┌──────┐        ┌──────┐        ┌──────┐       ┌──────┐   │   │
│  │  │Build │───▶    │Test  │───▶    │Scan  │───▶   │Push  │   │   │
│  │  │镜像  │        │单元  │        │Trivy │       │ECR/  │   │   │
│  │  │      │        │集成  │        │Checkov│      │GHCR  │   │   │
│  │  └──────┘        └──────┘        └──────┘       └──────┘   │   │
│  │                                                              │   │
│  │  Stage 5: 更新 GitOps 仓库中的镜像版本                       │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┴───────────────────────────────────┐   │
│  │                     GitOps 仓库                               │   │
│  │                                                              │   │
│  │  apps/my-app/                                                │   │
│  │  ├── base/           基础配置                                │   │
│  │  ├── overlays/       环境覆盖                                │   │
│  │  │   ├── dev/                                              │   │
│  │  │   ├── staging/                                          │   │
│  │  │   └── prod/                                             │   │
│  │  └── charts/         Helm Charts                            │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┴───────────────────────────────────┐   │
│  │                     CD 流水线 (ArgoCD)                        │   │
│  │                                                              │   │
│  │  监听 Git 变更 ──▶ 计算 Diff ──▶ 同步到 K8s ──▶ 验证健康     │   │
│  │       │                                      │               │   │
│  │       │              ┌──────────────┐        │               │   │
│  │       └──────────────│  多环境管理   │────────┘               │   │
│  │                      │  dev → staging → prod                 │   │
│  │                      └──────────────┘                        │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │                                        │
│  ┌──────────────────────────┴───────────────────────────────────┐   │
│  │                     监控 & 告警                                │   │
│  │                                                              │   │
│  │  Prometheus ──▶ Grafana ──▶ Alertmanager ──▶ PagerDuty      │   │
│  │  Loki ──▶ 日志分析                                           │   │
│  │  Jaeger ──▶ 链路追踪                                         │   │
│  │  ArgoCD Events ──▶ 审计日志                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

#### 1.2 流水线各阶段详解

```
┌──────────────────────────────────────────────────────────────────┐
│                    流水线阶段与门控条件                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Stage        检查项              门控条件        失败行为        │
│  ─────        ──────              ────────        ────────       │
│                                                                  │
│  1. Build     Docker 构建         构建成功        阻断            │
│     │         镜像 Tag 格式       符合规范        阻断            │
│     │         构建缓存            命中率 > 50%    警告            │
│     ▼                                                           │
│  2. Test       单元测试            通过率 100%    阻断            │
│     │         集成测试            通过率 100%    阻断            │
│     │         覆盖率              >= 80%         警告            │
│     ▼                                                           │
│  3. Scan       镜像漏洞 (Trivy)   无 CRITICAL    阻断            │
│     │         依赖漏洞 (Snyk)     无 CRITICAL    阻断            │
│     │         IaC 扫描 (Checkov)  无 HIGH+       阻断            │
│     │         秘钥扫描            无泄露         阻断            │
│     ▼                                                           │
│  4. Push       推送到镜像仓库      推送成功       阻断            │
│     │         签名镜像            签名成功       警告            │
│     │         生成 SBOM           生成成功       记录            │
│     ▼                                                           │
│  5. Update     更新 GitOps 仓库   PR 创建成功    通知            │
│     │         自动 Review         检查通过       人工审批        │
│     ▼                                                           │
│  6. Deploy     ArgoCD 同步        同步成功       阻断            │
│     │         健康检查            Pod 就绪       自动回滚        │
│     │         冒烟测试            测试通过       自动回滚        │
│     ▼                                                           │
│  7. Verify     SLO 检查           满足目标       告警            │
│               错误率              < 0.1%         自动回滚        │
│               延迟 P99           < 目标值        告警            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2. GitOps 仓库结构设计

#### 2.1 推荐的仓库结构

```
┌──────────────────────────────────────────────────────────────┐
│              GitOps 仓库结构（推荐）                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  方案一: 单仓库（Monorepo）                                   │
│  ─────────────────────────                                   │
│  gitops-repo/                                                │
│  ├── apps/                                                   │
│  │   ├── my-api/                                             │
│  │   │   ├── base/                                           │
│  │   │   │   ├── kustomization.yaml                          │
│  │   │   │   ├── deployment.yaml                             │
│  │   │   │   ├── service.yaml                                │
│  │   │   │   ├── hpa.yaml                                    │
│  │   │   │   └── pdb.yaml                                    │
│  │   │   └── overlays/                                       │
│  │   │       ├── dev/                                        │
│  │   │       ├── staging/                                    │
│  │   │       └── prod/                                       │
│  │   ├── my-worker/                                          │
│  │   │   ├── base/                                           │
│  │   │   └── overlays/                                       │
│  │   └── my-frontend/                                        │
│  │       ├── base/                                           │
│  │       └── overlays/                                       │
│  ├── infrastructure/                                         │
│  │   ├── cert-manager/                                       │
│  │   ├── ingress-nginx/                                      │
│  │   ├── prometheus-stack/                                   │
│  │   ├── loki-stack/                                         │
│  │   └── argocd/                                             │
│  ├── policies/                                               │
│  │   ├── gatekeeper/                                         │
│  │   └── network-policies/                                   │
│  └── .github/                                                │
│      └── workflows/                                          │
│          ├── validate.yaml                                   │
│          └── auto-approve.yaml                               │
│                                                              │
│  方案二: 多仓库（推荐大型团队）                                │
│  ─────────────────────────────                               │
│  my-api-config/      ─── 应用 A 的配置仓库                    │
│  my-worker-config/   ─── 应用 B 的配置仓库                    │
│  infra-config/       ─── 基础设施配置仓库                     │
│  policies-config/    ─── 策略配置仓库                         │
│                                                              │
│  优势: 权限隔离、独立发布节奏、减少冲突                        │
│  劣势: 跨仓库协调复杂、需要统一规范                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 2.2 ArgoCD ApplicationSet 管理多应用

```yaml
# applicationset.yaml - 使用 ApplicationSet 批量管理应用
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: my-apps
  namespace: argocd
spec:
  generators:
    # 使用 Git 目录生成器自动发现应用
    - git:
        repoURL: https://github.com/org/gitops-repo.git
        revision: main
        directories:
          - path: apps/*
  template:
    metadata:
      name: "{{path.basename}}"
    spec:
      project: default
      source:
        repoURL: https://github.com/org/gitops-repo.git
        targetRevision: main
        path: "{{path}}/overlays/{{metadata.labels.environment}}"
      destination:
        server: https://kubernetes.default.svc
        namespace: "{{path.basename}}-{{metadata.labels.environment}}"
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
          - PrunePropagationPolicy=foreground
        retry:
          limit: 3
          backoff:
            duration: 5s
            factor: 2
            maxDuration: 1m
      # 忽略 HPA 管理的字段
      ignoreDifferences:
        - group: autoscaling
          kind: HorizontalPodAutoscaler
          jsonPointers:
            - /spec/metrics
```

### 3. 完整 CI/CD 流水线实现

#### 3.1 GitHub Actions 完整流水线

```yaml
# .github/workflows/gitops-pipeline.yml
name: GitOps Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  GITOPS_REPO: org/gitops-repo
  APP_NAME: my-app

permissions:
  contents: read
  packages: write
  security-events: write

jobs:
  # ============================================
  # Stage 1: 代码质量检查
  # ============================================
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run linting
        run: |
          # 根据项目语言运行 linter
          # npm run lint
          # golangci-lint run
          echo "Linting passed"

      - name: Run unit tests
        run: |
          # npm test -- --coverage
          # go test ./...
          echo "Tests passed"

  # ============================================
  # Stage 2: 安全扫描
  # ============================================
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Secret scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: SAST scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/owasp-top-ten

      - name: Dependency scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  # ============================================
  # Stage 3: 构建 & 镜像扫描
  # ============================================
  build-and-scan:
    runs-on: ubuntu-latest
    needs: [code-quality, security-scan]
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
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
            type=sha,prefix=
            type=ref,event=branch
            type=ref,event=pr

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: "sarif"
          output: "trivy-results.sarif"
          severity: "CRITICAL,HIGH"
          exit-code: "1"

      - name: Generate SBOM
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: "spdx-json"
          output: "sbom.json"

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.json

  # ============================================
  # Stage 4: IaC 扫描
  # ============================================
  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Scan K8s manifests
        uses: bridgecrewio/checkov-action@master
        with:
          directory: ./k8s
          framework: kubernetes
          soft_fail: false

      - name: Scan Terraform
        uses: aquasecurity/tfsec-action@v1.0.0
        with:
          working_directory: ./terraform
          soft_fail: false

  # ============================================
  # Stage 5: 更新 GitOps 仓库
  # ============================================
  update-gitops:
    runs-on: ubuntu-latest
    needs: [build-and-scan, iac-scan]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - name: Checkout GitOps repo
        uses: actions/checkout@v4
        with:
          repository: ${{ env.GITOPS_REPO }}
          token: ${{ secrets.GITOPS_TOKEN }}
          path: gitops

      - name: Update image tag
        run: |
          cd gitops/apps/${{ env.APP_NAME }}/overlays/dev
          # 使用 kustomize 更新镜像 tag
          kustomize edit set image \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Create PR for dev
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITOPS_TOKEN }}
          path: gitops
          commit-message: "chore: update ${{ env.APP_NAME }} to ${{ github.sha }}"
          title: "chore: deploy ${{ env.APP_NAME }} ${{ github.sha }} to dev"
          body: |
            ## Deployment Details
            - **App**: ${{ env.APP_NAME }}
            - **Image**: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
            - **Commit**: ${{ github.sha }}
            - **Triggered by**: ${{ github.actor }}

            ## Checklist
            - [ ] CI pipeline passed
            - [ ] Security scans passed
            - [ ] Code review approved
          branch: deploy/${{ env.APP_NAME }}/${{ github.sha }}
          labels: |
            automated
            deploy
            dev

  # ============================================
  # Stage 6: 部署后验证
  # ============================================
  post-deploy-verify:
    runs-on: ubuntu-latest
    needs: [update-gitops]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - name: Wait for ArgoCD sync
        run: |
          # 等待 ArgoCD 同步完成
          for i in $(seq 1 30); do
            STATUS=$(argocd app get ${{ env.APP_NAME }}-dev \
              -o json | jq -r '.status.sync.status')
            if [ "$STATUS" = "Synced" ]; then
              echo "ArgoCD sync completed"
              break
            fi
            echo "Waiting for sync... ($i/30)"
            sleep 10
          done

      - name: Run smoke tests
        run: |
          # 运行冒烟测试
          curl -f https://${{ env.APP_NAME }}.dev.example.com/healthz || exit 1
          curl -f https://${{ env.APP_NAME }}.dev.example.com/readyz || exit 1

      - name: Check SLO metrics
        run: |
          # 检查关键指标
          ERROR_RATE=$(curl -s "http://prometheus:9090/api/v1/query?query=rate(http_requests_total{code=~'5..'}[5m]) / rate(http_requests_total[5m])" | jq '.data.result[0].value[1]')
          echo "Error rate: $ERROR_RATE"
```

### 4. 监控集成

#### 4.1 GitOps 监控指标

```
┌──────────────────────────────────────────────────────────────┐
│                    GitOps 监控指标体系                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  流水线指标 (CI/CD)                                  │    │
│  │                                                      │    │
│  │  • 流水线执行时间 (P50/P95/P99)                      │    │
│  │  • 流水线成功率                                       │    │
│  │  • 构建频率 (每日构建次数)                            │    │
│  │  • 变更前置时间 (代码提交到部署的时间)                │    │
│  │  • 变更失败率 (部署后需要回滚的比例)                  │    │
│  │  • 恢复时间 (故障到恢复的时间)                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ArgoCD 指标                                         │    │
│  │                                                      │    │
│  │  • argocd_app_info           应用状态信息             │    │
│  │  • argocd_app_sync_total     同步次数                 │    │
│  │  • argocd_app_sync_duration  同步耗时                 │    │
│  │  • argocd_app_reconcile_count  调谐次数              │    │
│  │  • argocd_cluster_api_resources  集群资源数           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  应用指标                                             │    │
│  │                                                      │    │
│  │  • 请求成功率 (SLI)                                  │    │
│  │  • 响应延迟 P50/P95/P99                              │    │
│  │  • 请求吞吐量 (QPS)                                  │    │
│  │  • Pod 重启次数                                       │    │
│  │  • 资源使用率 (CPU/Memory)                           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 4.2 Prometheus 告警规则

```yaml
# gitops-alerts.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: gitops-alerts
  namespace: monitoring
spec:
  groups:
    # ArgoCD 同步告警
    - name: argocd.sync
      rules:
        - alert: ArgoCDAppOutOfSync
          expr: |
            argocd_app_info{sync_status="OutOfSync"} == 1
          for: 15m
          labels:
            severity: warning
            team: sre
          annotations:
            summary: "ArgoCD 应用 {{ $labels.name }} OutOfSync 超过 15 分钟"
            description: "应用 {{ $labels.name }} 在 namespace {{ $labels.namespace }} 处于 OutOfSync 状态"
            runbook_url: "https://wiki.example.com/runbooks/argocd-oos"

        - alert: ArgoCDAppDegraded
          expr: |
            argocd_app_info{health_status="Degraded"} == 1
          for: 5m
          labels:
            severity: critical
            team: sre
          annotations:
            summary: "ArgoCD 应用 {{ $labels.name }} 健康状态 Degraded"

        - alert: ArgoCDSyncFailed
          expr: |
            increase(argocd_app_sync_total{phase="Failed"}[1h]) > 0
          labels:
            severity: warning
            team: sre
          annotations:
            summary: "ArgoCD 同步失败: {{ $labels.name }}"

    # 应用健康告警
    - name: app.health
      rules:
        - alert: HighErrorRate
          expr: |
            sum(rate(http_requests_total{code=~"5.."}[5m])) by (app)
            /
            sum(rate(http_requests_total[5m])) by (app)
            > 0.01
          for: 5m
          labels:
            severity: critical
            team: sre
          annotations:
            summary: "应用 {{ $labels.app }} 错误率超过 1%"
            description: "当前错误率: {{ $value | humanizePercentage }}"

        - alert: HighLatency
          expr: |
            histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 1
          for: 5m
          labels:
            severity: warning
            team: sre
          annotations:
            summary: "应用 {{ $labels.app }} P99 延迟超过 1 秒"

        - alert: PodRestartLoop
          expr: |
            increase(kube_pod_container_status_restarts_total[1h]) > 5
          for: 10m
          labels:
            severity: critical
            team: sre
          annotations:
            summary: "Pod {{ $labels.pod }} 在过去 1 小时内重启超过 5 次"

    # 安全告警
    - name: security.alerts
      rules:
        - alert: VulnerableImageDeployed
          expr: |
            trivy_vulnerability_count{severity="CRITICAL"} > 0
          for: 0m
          labels:
            severity: critical
            team: security
          annotations:
            summary: "检测到包含 CRITICAL 漏洞的镜像已部署"
            description: "镜像 {{ $labels.image }} 包含 {{ $value }} 个 CRITICAL 漏洞"

        - alert: UnauthorizedImageDeployed
          expr: |
            kube_pod_container_image{image!~"registry.example.com/.*"} == 1
          for: 0m
          labels:
            severity: warning
            team: security
          annotations:
            summary: "检测到非授权镜像仓库的镜像"
```

#### 4.3 Grafana Dashboard

GitOps Pipeline Dashboard 应包含以下面板：

| 面板名称 | 类型 | PromQL 查询 | 用途 |
|----------|------|-------------|------|
| ArgoCD Sync Status | Stat | `count(argocd_app_info{sync_status="Synced"})` | 显示同步/未同步应用数量 |
| Deployment Frequency | Time Series | `sum(increase(argocd_app_sync_total{phase="Succeeded"}[1d]))` | 每日部署频率 |
| Change Lead Time | Heatmap | `histogram_quantile(0.5, rate(deploy_lead_time_seconds_bucket[1d]))` | 变更前置时间分布 |
| Error Rate by Service | Time Series | `sum(rate(http_requests_total{code=~"5.."}[5m])) by (app) / sum(rate(http_requests_total[5m])) by (app)` | 各服务错误率 |
| Pod Restart Count | Stat | `sum(increase(kube_pod_container_status_restarts_total[1h]))` | Pod 重启次数 |

### 5. 自动回滚机制

#### 5.1 基于健康检查的自动回滚

```
┌──────────────────────────────────────────────────────────────┐
│                    自动回滚流程                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  部署新版本                                                   │
│     │                                                         │
│     ▼                                                         │
│  ┌──────────────────┐                                        │
│  │  健康检查         │                                        │
│  │  • Pod Ready?    │                                        │
│  │  • 健康端点 200? │                                        │
│  │  • 就绪端点 200? │                                        │
│  └────────┬─────────┘                                        │
│           │                                                   │
│     ┌─────┴─────┐                                            │
│     │           │                                            │
│  健康        不健康                                           │
│     │           │                                            │
│     ▼           ▼                                            │
│  ┌────────┐  ┌──────────────────┐                            │
│  │  持续  │  │  等待超时         │                            │
│  │  监控  │  │  (默认 5 分钟)    │                            │
│  └────┬───┘  └────────┬─────────┘                            │
│       │               │                                      │
│       ▼               ▼                                      │
│  ┌────────┐  ┌──────────────────┐                            │
│  │ SLO    │  │  自动回滚         │                            │
│  │ 检查   │  │  • git revert    │                            │
│  │        │  │  • argocd sync   │                            │
│  └────┬───┘  │  • 通知团队      │                            │
│       │      └──────────────────┘                            │
│       ▼                                                      │
│  ┌────────┐                                                  │
│  │ 成功   │                                                  │
│  │ 部署完成│                                                  │
│  └────────┘                                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2 ArgoCD Rollback 实现

使用 K8s Job 实现自动回滚的核心步骤：

1. 获取应用当前状态：`argocd app get <app> -o json`
2. 检查健康状态：`.status.health.status`
3. 如果不健康，获取上一个成功的 revision：`.status.history[-2].revision`
4. 执行回滚：`argocd app rollback <app> <revision>`
5. 等待回滚完成并验证新状态
6. 发送通知到 Slack/PagerDuty

Job 需要配置 `serviceAccountName` 具有 ArgoCD 应用管理权限，并通过 Secret 注入通知 Webhook URL。

#### 5.3 基于指标的渐进式回滚

基于 SLO 指标的自动回滚核心逻辑：

1. 定期查询 Prometheus 获取错误率和 P99 延迟
2. 如果连续 3 次检查发现 SLO 违规，触发自动回滚
3. 获取 ArgoCD 部署历史中的上一个版本
4. 执行 `argocd app rollback` 回滚到该版本
5. 验证回滚后应用恢复健康状态

关键查询：
- 错误率: `sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`
- P99 延迟: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))`
- 阈值: 错误率 > 1% 或 P99 > 1s 视为 SLO 违规

### 6. 审计与合规

#### 6.1 GitOps 审计追溯

```
┌──────────────────────────────────────────────────────────────┐
│                    GitOps 审计追溯链                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Git Commit                                                  │
│  ├── 作者: developer@example.com                             │
│  ├── 时间: 2026-05-03 10:30:00                              │
│  ├── PR: #123 "feat: add new API endpoint"                  │
│  ├── Reviewer: tech-lead@example.com                        │
│  └── CI/CD: pipeline-run #456                               │
│      ├── 构建: image tag abc123                              │
│      ├── 测试: all passed                                    │
│      ├── 扫描: no critical vulnerabilities                  │
│      └── 签名: verified                                      │
│           │                                                  │
│           ▼                                                  │
│  GitOps Repo Update                                          │
│  ├── 作者: bot@example.com                                   │
│  ├── Commit: "chore: update my-app to abc123"               │
│  └── PR: #456 "deploy my-app abc123 to dev"                 │
│      ├── 自动创建                                             │
│      └── 自动合并（dev 环境）                                 │
│           │                                                  │
│           ▼                                                  │
│  ArgoCD Sync                                                 │
│  ├── 时间: 2026-05-03 10:35:00                              │
│  ├── 操作: Sync initiated by automated                      │
│  ├── 结果: Synced, Healthy                                   │
│  └── 资源变更:                                                │
│      ├── Deployment/my-app: updated                          │
│      └── ConfigMap/my-app-config: unchanged                  │
│           │                                                  │
│           ▼                                                  │
│  K8s Audit Log                                               │
│  ├── 时间: 2026-05-03 10:35:01                              │
│  ├── 用户: system:serviceaccount:argocd:argocd-application-controller│
│  ├── 操作: update deployments                                │
│  ├── 资源: apps/v1/deployments/my-app                        │
│  └── 结果: success                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 6.2 K8s 审计日志配置

K8s 审计策略定义了记录哪些 API 请求：

| Level | 说明 | 适用场景 |
|-------|------|----------|
| None | 不记录 | kube-proxy 的 watch 请求 |
| Metadata | 仅记录元数据 | secrets、configmaps 的读取 |
| RequestResponse | 记录请求和响应 | 生产 namespace 的 deployments 变更 |

关键配置点：
- 生产 namespace 的所有变更操作设置为 `RequestResponse` 级别
- 使用 `omitStages: ["RequestReceived"]` 减少日志量
- 审计日志发送到集中日志系统（如 Loki/ELK）进行长期存储

#### 6.3 合规性报告

合规性报告应包含以下内容：
- 各应用各环境的同步状态和健康状态
- 镜像漏洞统计（CRITICAL/HIGH 数量）
- 过去 7 天的部署频率
- SLA 达成情况（可用性百分比）
- 未解决问题列表（OutOfSync、Degraded 应用）

报告可以通过定时 Job 自动生成，使用 `argocd app get -o json` 获取状态，结合 `trivy image` 扫描结果汇总。

### 7. GitOps 最佳实践

#### 7.1 十大最佳实践

```
┌──────────────────────────────────────────────────────────────┐
│                  GitOps 十大最佳实践                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Git 是唯一事实来源                                        │
│     ──────────────────                                       │
│     所有配置存储在 Git 中，禁止直接 kubectl edit              │
│     使用 RBAC 限制直接操作集群的权限                          │
│                                                              │
│  2. 声明式而非命令式                                          │
│     ──────────────────                                       │
│     描述"期望状态"而非"执行步骤"                              │
│     使用 Kustomize/Helm 定义配置，而非 shell 脚本            │
│                                                              │
│  3. 不可变镜像                                                │
│     ─────────                                                │
│     镜像一旦构建就不再修改，配置变更通过新镜像实现            │
│     使用语义化版本或 Git SHA 作为镜像 tag                     │
│                                                              │
│  4. 自动化同步                                                │
│     ─────────                                                │
│     启用 ArgoCD automated sync + selfHeal                    │
│     非关键环境全自动，生产环境需要审批                        │
│                                                              │
│  5. 渐进式发布                                                │
│     ─────────                                                │
│     dev → staging → prod 逐步推进                            │
│     每个阶段有门控条件和观察期                                │
│                                                              │
│  6. 安全左移                                                  │
│     ─────────                                                │
│     在 CI 阶段完成所有安全扫描                                │
│     发现 CRITICAL 漏洞阻断部署                                │
│                                                              │
│  7. 可观测性                                                  │
│     ─────────                                                │
│     监控 GitOps 流水线各阶段指标                              │
│     部署后自动验证 SLO                                        │
│                                                              │
│  8. 自动回滚                                                  │
│     ─────────                                                │
│     健康检查失败自动回滚                                      │
│     SLO 违规触发自动回滚                                      │
│     保留手动回滚能力                                          │
│                                                              │
│  9. 审计追溯                                                  │
│     ─────────                                                │
│     Git 历史 = 变更日志                                       │
│     K8s Audit Log 记录所有集群操作                            │
│     定期生成合规性报告                                        │
│                                                              │
│  10. 文档即代码                                               │
│      ─────────                                               │
│      配置文件自文档化（清晰的命名和注释）                      │
│      README 包含部署流程和回滚步骤                            │
│      Runbook 存储在 Git 中                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 7.2 常见陷阱与解决方案

| 陷阱 | 问题描述 | 解决方案 |
|------|----------|----------|
| **Secret 管理** | Secret 存储在 Git 中 | 使用 External Secrets Operator 或 Sealed Secrets |
| **配置漂移** | 手动修改导致不一致 | 启用 selfHeal，限制 RBAC 权限 |
| **镜像 tag 混乱** | 使用 latest 或无意义 tag | 使用 Git SHA 或语义化版本 |
| **同步风暴** | 频繁提交导致频繁同步 | 配置 sync throttle，合并 PR |
| **权限过大** | CI 有集群管理权限 | 最小权限原则，使用 ServiceAccount |
| **缺乏回滚** | 部署失败无法快速恢复 | 保留发布历史，支持一键回滚 |
| **监控缺失** | 不知道部署是否成功 | 集成部署后验证和 SLO 检查 |
| **单点故障** | ArgoCD 不可用导致无法部署 | 多副本部署，备用部署方式 |

### 8. 综合实战项目

#### 8.1 项目概述

搭建一个完整的 GitOps 流水线，管理一个微服务应用的 dev/staging/prod 三个环境。

```
┌──────────────────────────────────────────────────────────────┐
│                    综合项目架构                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  应用组件:                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ API 服务  │  │ Worker   │  │ Frontend │                  │
│  │ (Go)     │  │ (Python) │  │ (React)  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│       │              │              │                        │
│       ▼              ▼              ▼                        │
│  ┌────────────────────────────────────────┐                 │
│  │           共享基础设施                   │                 │
│  │  PostgreSQL | Redis | RabbitMQ          │                 │
│  └────────────────────────────────────────┘                 │
│       │                                                     │
│       ▼                                                     │
│  ┌────────────────────────────────────────┐                 │
│  │           K8s 集群                      │                 │
│  │  EKS (3 AZ, 自动扩缩)                  │                 │
│  └────────────────────────────────────────┘                 │
│       │                                                     │
│       ▼                                                     │
│  ┌────────────────────────────────────────┐                 │
│  │           可观测性                       │                 │
│  │  Prometheus + Grafana + Loki + Jaeger  │                 │
│  └────────────────────────────────────────┘                 │
│                                                              │
│  流水线:                                                     │
│  GitHub Actions (CI) ──▶ ECR (镜像) ──▶ ArgoCD (CD)         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 8.2 实施步骤

**Step 1: 创建 GitOps 仓库结构**
```bash
# 创建仓库结构
mkdir -p gitops-project/{apps/{api,worker,frontend}/{base,overlays/{dev,staging,prod}},infrastructure/{argocd,prometheus,ingress},policies,.github/workflows}

# 初始化 Git 仓库
cd gitops-project
git init
```

**Step 2: 编写 Kustomize 配置**

为 API 服务创建 base 配置（包含 Deployment、Service、HPA、PDB、ServiceMonitor）和 prod overlay（3 副本、资源限制提升、安全上下文）。详细配置参见 Day 157 多环境管理章节。

**Step 3: 配置 ArgoCD Application**

为生产环境创建 ArgoCD Application，配置 automated sync + selfHeal，设置通知订阅（sync-failed、health-degraded 发送到 Slack）。

**Step 4: 完整 CI/CD 流水线**

流水线阶段：test (单元测试) -> build (构建镜像) -> scan (Trivy 扫描) -> deploy-dev (自动) -> deploy-staging (创建 PR) -> deploy-prod (创建 PR + 人工审批)。每个阶段使用 GitHub Actions 实现，详细配置参见本章第 3 节。

---

## 💻 实战练习

### 练习一：搭建完整的 GitOps 流水线

**目标**：为一个简单应用搭建从代码提交到生产部署的完整 GitOps 流水线。

```bash
# 1. 创建应用代码仓库结构
mkdir -p my-app/{src,k8s/{base,overlays/{dev,staging,prod}},.github/workflows}

# 2. 创建简单的 Go 应用（main.go + Dockerfile）

# 3. 创建 Kustomize base（deployment.yaml + service.yaml + kustomization.yaml）

# 4. 创建 dev overlay（1 副本，debug 日志，latest 镜像）

# 5. 创建 prod overlay（3 副本，warn 日志，语义化版本镜像）

# 6. 验证各环境配置
kustomize build my-app/k8s/overlays/dev
kustomize build my-app/k8s/overlays/prod

# 7. 创建 GitHub Actions CI/CD 流水线
#    test -> build -> scan -> deploy-dev -> deploy-staging (PR) -> deploy-prod (PR)

# 8. 配置 ArgoCD 监听 GitOps 仓库，自动同步 dev 环境
```

### 练习二：配置监控和告警

**目标**：为 GitOps 流水线配置 Prometheus 告警规则。

创建 PrometheusRule 资源，包含以下告警：
- ArgoCDAppOutOfSync: 应用 OutOfSync 超过 15 分钟
- ArgoCDAppDegraded: 应用 Degraded 超过 5 分钟
- HighDeploymentFrequency: 1 小时内部署超过 10 次
- DeploymentFailureRate: 部署失败率超过 10%

### 练习三：实现自动回滚脚本

**目标**：编写自动回滚脚本，当部署后健康检查连续失败时自动回滚。

脚本核心逻辑：
1. 定期检查 ArgoCD 应用健康状态（每 10 秒）
2. 如果连续 3 次不健康，获取上一个 revision
3. 执行 `argocd app rollback` 回滚
4. 验证回滚后状态恢复健康
5. 如果超时（5 分钟）无问题，正常退出

---

## 🎯 面试题精选

### 面试题一：什么是 GitOps？它和传统 CI/CD 有什么区别？

**答案要点**：
- GitOps 以 Git 作为唯一事实来源，通过声明式配置管理基础设施和应用
- 传统 CI/CD 是推模式（Push），CI 构建后直接部署到集群
- GitOps 是拉模式（Pull），集群内的 Agent 主动从 Git 拉取期望状态
- GitOps 的优势：可审计（Git 历史）、可回滚（Git revert）、一致性（声明式）
- 核心工具：ArgoCD、Flux

### 面试题二：如何设计一个生产级的 GitOps 流水线？

**答案要点**：
1. CI 阶段：代码扫描、单元测试、镜像构建、漏洞扫描
2. 镜像管理：推送到私有仓库、签名、生成 SBOM
3. GitOps 仓库：更新配置、创建 PR、自动/人工审批
4. CD 阶段：ArgoCD 同步、健康检查、冒烟测试
5. 监控验证：SLO 检查、错误率监控、自动回滚
6. 审计追溯：Git 历史、K8s Audit Log、合规报告

### 面试题三：ArgoCD 的 syncPolicy 如何配置？

**答案要点**：
- `automated.prune`: 自动删除 Git 中已移除的资源
- `automated.selfHeal`: 自动修复集群中的手动修改（漂移修复）
- `syncOptions.CreateNamespace`: 自动创建目标 namespace
- `syncOptions.PrunePropagationPolicy`: 删除级联策略
- `retry`: 同步失败时的重试策略
- 生产环境建议：dev 全自动，staging 半自动，prod 手动审批

### 面试题四：如何实现 GitOps 的自动回滚？

**答案要点**：
- 基于健康状态：ArgoCD 应用 Degraded 时触发回滚
- 基于 SLO 指标：错误率或延迟超过阈值时触发
- 基于冒烟测试：部署后自动运行端到端测试
- 实现方式：K8s CronJob 定期检查、CI/CD Pipeline 集成、ArgoCD Rollout
- 回滚操作：`argocd app rollback <app> <revision>` 或 `git revert`
- 保留历史：ArgoCD 自动保留部署历史，支持查看和回滚

### 面试题五：如何管理 GitOps 中的 Secret？

**答案要点**：
- 不要将 Secret 明文存储在 Git 中
- 方案一：Sealed Secrets - 加密后存储在 Git，控制器在集群中解密
- 方案二：External Secrets Operator - 从外部 Secret 管理器拉取
- 方案三：HashiCorp Vault - 动态 Secret、自动轮转
- 方案四：SOPS + KMS - 使用云 KMS 加密，Git 存储加密后的内容
- 选择建议：已有 Vault 用 ESO，AWS 环境用 ESO + Secrets Manager，简单场景用 Sealed Secrets

### 面试题六：Git Flow 和 Trunk-Based 开发哪个更适合 GitOps？

**答案要点**：
- Trunk-Based 更适合 GitOps，因为 GitOps 通过 overlay 目录而非分支管理环境
- Git Flow 的问题：多分支 merge 冲突、长生命周期分支、环境分支容易漂移
- Trunk-Based 优势：频繁集成、短生命周期 feature branch、通过 overlay 区分环境
- 如果团队必须用 Git Flow：main 对应 prod，develop 对应 dev，release 对应 staging
- 关键原则：无论哪种策略，环境配置都应该存储在 Git 中

### 面试题七：如何衡量 GitOps 的效果？

**答案要点**：
使用 DORA 四个关键指标：
1. **部署频率**：每天部署次数（目标：按需部署）
2. **变更前置时间**：代码提交到生产部署的时间（目标：< 1 小时）
3. **变更失败率**：需要回滚的部署比例（目标：< 5%）
4. **恢复时间**：故障到恢复的时间（目标：< 1 小时）
额外指标：配置漂移频率、安全扫描通过率、审计合规率

### 面试题八：如何处理 GitOps 中的数据库迁移？

**答案要点**：
- 数据库迁移与应用部署解耦
- 使用 Init Container 或 K8s Job 执行迁移
- 迁移脚本存储在 Git 中，与应用代码一起版本控制
- 迁移必须是幂等的（可重复执行）
- 生产环境迁移需要人工审批和回滚方案
- 推荐工具：Flyway、Liquibase、golang-migrate
- 流程：迁移 Job 成功 → 更新应用 Deployment

---

## 📚 深入阅读

1. **OpenGitOps**: https://opengitops.dev/ - GitOps 原则和最佳实践
2. **ArgoCD 最佳实践**: https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/
3. **Flux 文档**: https://fluxcd.io/docs/
4. **GitOps Toolkit**: https://toolkit.fluxcd.io/
5. **DORA Metrics**: https://dora.dev/
6. **CNCF GitOps Working Group**: https://github.com/cncf/tag-app-delivery/tree/main/gitops-working-group
7. **Weaveworks GitOps**: https://www.weave.works/technologies/gitops/
8. **ArgoCD Notifications**: https://argocd-notifications.readthedocs.io/

---

## ✅ 自检清单

- [ ] 能够设计完整的 GitOps 流水线架构
- [ ] 理解 GitOps 仓库结构设计（Monorepo vs 多仓库）
- [ ] 能够配置 ArgoCD ApplicationSet 批量管理应用
- [ ] 掌握 GitHub Actions CI/CD 流水线的完整配置
- [ ] 能够集成监控告警（Prometheus + Grafana）
- [ ] 理解自动回滚机制的设计和实现
- [ ] 知道如何配置 K8s 审计日志实现合规追溯
- [ ] 掌握 GitOps 十大最佳实践
- [ ] 了解常见陷阱和解决方案
- [ ] 能够完成综合实战项目（从代码到生产的完整流程）
- [ ] 掌握 DORA 四个关键指标
- [ ] 理解 GitOps 面试题的回答框架
