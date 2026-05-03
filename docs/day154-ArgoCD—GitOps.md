# Day 154: ArgoCD — GitOps

> 📅 日期：2026-05-03
> 📖 学习主题：ArgoCD 架构、Application/Project、同步策略、自动同步、多集群、ApplicationSet、通知、回滚、最佳实践
> ⏰ 预计学习时间：5-6 小时
> 📋 前置知识：Day 93-104（K8s 基础）、Day 102（Helm）、Day 152-153（CI/CD 基础与流程）

## 🎯 学习目标

- 理解 ArgoCD 的架构和 GitOps 工作原理
- 掌握 Application 和 Project 的配置与管理
- 精通同步策略（手动/自动、Sync Options、Sync Hooks）
- 能够配置多集群管理与 ApplicationSet
- 掌握 ArgoCD 通知与告警集成
- 理解回滚机制与灾难恢复
- 掌握 ArgoCD 生产级最佳实践

---

## 📖 核心知识点

### 1. ArgoCD 架构

#### 1.1 GitOps 原理

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GitOps 工作原理                                    │
│                                                                     │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐  │
│  │  开发者   │────>│  Git 仓库 │────>│  ArgoCD  │────>│  K8s 集群 │  │
│  │          │     │  (期望状态)│     │  (控制器) │     │  (实际状态)│  │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘  │
│       │                                   │               │        │
│       │           Pull Request            │    Reconcile  │        │
│       │ ─────────────────────────────────>│<──────────────┘        │
│       │                                   │                        │
│       │                                   │  比较期望状态与实际状态 │
│       │                                   │  如果不一致 → 同步     │
│                                                                     │
│  核心原则：                                                          │
│  1. 声明式（Declarative）：期望状态在 Git 中声明                    │
│  2. 版本化（Versioned）：所有变更有 Git 历史                        │
│  3. 自动化（Automated）：Git 变更自动同步到集群                     │
│  4. 持续收敛（Continuously Converged）：持续确保实际=期望           │
│  5. 自愈（Self-healing）：手动变更会被自动回退                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.2 ArgoCD 组件架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ArgoCD 组件架构                                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    ArgoCD Server (API Server)                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ REST API     │  │ gRPC API     │  │ Web UI       │      │   │
│  │  │ (应用管理)   │  │ (CLI 通信)   │  │ (可视化面板) │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ SSO/OIDC     │  │ RBAC         │  │ Webhook      │      │   │
│  │  │ (身份认证)   │  │ (权限控制)   │  │ (事件接收)   │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Repo Server (仓库服务器)                   │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ Git Clone    │  │ Helm Template│  │ Kustomize    │      │   │
│  │  │ (仓库克隆)   │  │ (Helm 渲染)  │  │ Build        │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  │  ┌──────────────┐  ┌──────────────┐                        │   │
│  │  │ Config Mgmt  │  │ Manifest     │                        │   │
│  │  │ Plugins      │  │ Generation   │                        │   │
│  │  └──────────────┘  └──────────────┘                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Application Controller (应用控制器)        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ Reconciler   │  │ Sync Engine  │  │ Health Check │      │   │
│  │  │ (状态协调)   │  │ (同步引擎)   │  │ (健康检查)   │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ Diff Engine  │  │ Sync Hooks   │  │ Rollback     │      │   │
│  │  │ (差异比较)   │  │ (同步钩子)   │  │ (回滚)       │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Dex (身份认证)                              │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │ OIDC     │  │ LDAP     │  │ GitHub   │  │ SAML     │   │   │
│  │  │ Provider │  │          │  │ OAuth    │  │          │   │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Redis (缓存)                               │   │
│  │  - 应用状态缓存                                              │   │
│  │  - Git 仓库缓存                                              │   │
│  │  - Manifest 缓存                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  数据流：                                                           │
│  1. 用户通过 API/UI/CLI 创建 Application                          │
│  2. Application Controller 检测到新 Application                    │
│  3. Controller 请求 Repo Server 获取 Git 仓库中的 manifests        │
│  4. Repo Server 克隆 Git 仓库，渲染模板（Helm/Kustomize）         │
│  5. Controller 比较 Git 期望状态与集群实际状态                      │
│  6. 如果不一致且配置了自动同步，执行同步操作                        │
│  7. 同步完成后，更新 Application 状态                               │
└─────────────────────────────────────────────────────────────────────┘
```

#### 1.3 安装 ArgoCD

```bash
# ===== 使用 kubectl 安装 =====

# 创建命名空间
kubectl create namespace argocd

# 安装 ArgoCD（生产环境推荐使用 HA 模式）
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/ha/install.yaml

# 等待所有 Pod 就绪
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# 获取初始管理员密码
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# 安装 argocd CLI
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd
sudo mv argocd /usr/local/bin/argocd

# 登录
argocd login argocd.example.com --username admin --password <password>

# 修改密码
argocd account update-password

# ===== 使用 Helm 安装（推荐生产环境）=====
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --set server.service.type=LoadBalancer \
  --set server.metrics.enabled=true \
  --set controller.metrics.enabled=true \
  --set redis-ha.enabled=true \
  --set server.autoscaling.enabled=true \
  --set server.autoscaling.minReplicas=2 \
  --set controller.replicas=2
```

---

### 2. Application 与 Project

#### 2.1 Application CRD

```yaml
# Application 定义
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-production
  namespace: argocd
  # 级联删除：删除 Application 时是否删除 K8s 资源
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  # 项目归属（用于权限隔离）
  project: production

  # 源配置（Git 仓库）
  source:
    # 仓库 URL
    repoURL: https://github.com/myorg/k8s-manifests.git
    # 目标分支/标签/commit
    targetRevision: main
    # 路径（Kustomize/Helm charts 所在目录）
    path: apps/myapp/overlays/production

    # Kustomize 特定配置（如果使用 Kustomize）
    kustomize:
      images:
        - myapp=ghcr.io/myorg/myapp:v1.2.3

    # Helm 特定配置（如果使用 Helm）
    # helm:
    #   releaseName: myapp
    #   values: |
    #     replicaCount: 3
    #     image:
    #       tag: v1.2.3

  # 目标集群和命名空间
  destination:
    server: https://kubernetes.default.svc
    namespace: production

  # 同步策略
  syncPolicy:
    # 自动同步
    automated:
      # 启用自愈（回退手动变更）
      selfHeal: true
      # 允许删除 Git 中不存在的资源
      prune: true
      # 允许空命名空间删除
      allowEmpty: false
    # 同步选项
    syncOptions:
      # 创建命名空间
      - CreateNamespace=true
      # 使用 Server-Side Apply（推荐）
      - ServerSideApply=true
      # 不尊重 Prune Last 注解
      - RespectIgnoreDifferences=true
      # 校验 manifests
      - Validate=true
      # 在同步前执行 Prune
      - PruneLast=true
      # 替换而非更新（对于不可变资源如 Job）
      - Replace=true
      # 应用前进行差异比较
      - ApplyOutOfSyncOnly=true
    # 重试策略
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  # 忽略差异配置（某些字段不参与比较）
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas  # 忽略副本数差异（HPA 管理）
    - kind: MutatingWebhookConfiguration
      jqPathExpressions:
        - '.webhooks[]?.clientConfig.caBundle'
```

#### 2.2 Application 状态

```bash
# 查看 Application 状态
argocd app get myapp-production

# 状态示例输出：
# Name:               myapp-production
# Project:            production
# Server:             https://kubernetes.default.svc
# Namespace:          production
# URL:                https://argocd.example.com/applications/myapp-production
# Repository:         https://github.com/myorg/k8s-manifests.git
# Target:             main
# Path:               apps/myapp/overlays/production
#
# Sync Status:        Synced
# Health Status:      Healthy
#
# GROUP  KIND        NAMESPACE   NAME          STATUS   HEALTH   HOOK  MESSAGE
# apps   Deployment  production  myapp         Synced   Healthy        deployment.apps/myapp unchanged
#        Service     production  myapp         Synced   Healthy        service/myapp unchanged
# autoscaling HPA    production  myapp         Synced   Healthy        horizontalpodautoscaler.autoscaling/myapp unchanged

# Application 状态说明：
# Sync Status:
#   Synced    → Git 期望状态与集群实际状态一致
#   OutOfSync → Git 期望状态与集群实际状态不一致
#   Unknown   → 无法确定状态
#
# Health Status:
#   Healthy   → 所有资源健康
#   Progressing → 正在部署中
#   Degraded  → 部分资源不健康
#   Suspended → 资源已暂停（如 Deployment replicas=0）
#   Missing   → 资源不存在
#   Unknown   → 无法确定健康状态
```

#### 2.3 AppProject CRD

```yaml
# AppProject 定义（项目级别的权限和资源隔离）
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  # 项目描述
  description: Production environment applications

  # 允许的 Git 源仓库
  sourceRepos:
    - 'https://github.com/myorg/k8s-manifests.git'
    - 'https://github.com/myorg/helm-charts.git'
    - 'https://charts.bitnami.com/bitnami'

  # 允许的目标集群和命名空间
  destinations:
    - server: https://kubernetes.default.svc
      namespace: production
    - server: https://kubernetes.default.svc
      namespace: monitoring
    - server: https://staging-cluster.example.com
      namespace: '*'

  # 集群范围资源白名单
  clusterResourceWhitelist:
    - group: ''
      kind: Namespace
    - group: rbac.authorization.k8s.io
      kind: ClusterRole
    - group: rbac.authorization.k8s.io
      kind: ClusterRoleBinding

  # 命名空间范围资源白名单
  namespaceResourceWhitelist:
    - group: ''
      kind: '*'
    - group: apps
      kind: '*'
    - group: networking.k8s.io
      kind: Ingress
    - group: autoscaling
      kind: HorizontalPodAutoscaler

  # 禁止的资源
  namespaceResourceBlacklist:
    - group: ''
      kind: ResourceQuota
    - group: ''
      kind: LimitRange

  # 角色定义
  roles:
    - name: developer
      description: Developer access
      policies:
        - p, proj:production:developer, applications, get, production/*, allow
        - p, proj:production:developer, applications, sync, production/*, allow
      groups:
        - myorg:developers

    - name: sre
      description: SRE full access
      policies:
        - p, proj:production:sre, applications, *, production/*, allow
      groups:
        - myorg:sre-team

  # Sync Windows（同步窗口，限制自动同步时间）
  syncWindows:
    - kind: allow
      schedule: '0 8-18 * * 1-5'  # 工作日 8:00-18:00
      duration: 10h
      applications:
        - '*'
      namespaces:
        - production
    - kind: deny
      schedule: '0 0 * * 0'  # 周日禁止
      duration: 24h
      applications:
        - '*'
```

---

### 3. 同步策略

#### 3.1 同步策略详解

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ArgoCD 同步策略                                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  手动同步（Manual Sync）                                     │   │
│  │                                                             │   │
│  │  - 默认模式，需要人工触发同步                                │   │
│  │  - 适用于生产环境，需要审批                                  │   │
│  │  - 触发方式：UI / CLI / API                                  │   │
│  │                                                             │   │
│  │  argocd app sync myapp                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  自动同步（Auto Sync）                                       │   │
│  │                                                             │   │
│  │  - Git 仓库变更时自动触发同步                                │   │
│  │  - 适用于开发/测试环境                                       │   │
│  │                                                             │   │
│  │  配置：                                                      │   │
│  │  syncPolicy:                                                │   │
│  │    automated:                                               │   │
│  │      selfHeal: true    # 自愈：回退手动变更                  │   │
│  │      prune: true       # 清理：删除 Git 中不存在的资源       │   │
│  │                                                             │   │
│  │  检测机制：                                                  │   │
│  │  ├── Git Webhook（实时触发）                                │   │
│  │  ├── 轮询（默认 3 分钟间隔）                                │   │
│  │  └── 两者结合使用                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Sync Options（同步选项）                                    │   │
│  │                                                             │   │
│  │  - CreateNamespace=true      创建目标命名空间                │   │
│  │  - PruneLast=true            最后执行删除操作                │   │
│  │  - Replace=true              替换而非更新（不可变资源）      │   │
│  │  - ServerSideApply=true      使用 SSA 更新（推荐）           │   │
│  │  - Validate=true             执行 K8s 校验                   │   │
│  │  - ApplyOutOfSyncOnly=true   只同步有差异的资源              │   │
│  │  - RespectIgnoreDifferences  尊重 ignoreDifferences 配置     │   │
│  │  - Force=true                强制同步（解决冲突）            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Sync Phases（同步阶段）                                     │   │
│  │                                                             │   │
│  │  PreSync → Sync → PostSync → SyncFail                      │   │
│  │                                                             │   │
│  │  PreSync:                                                   │   │
│  │  ├── 数据库迁移 Job                                         │   │
│  │  ├── 配置预检                                               │   │
│  │  └── 依赖资源创建                                           │   │
│  │                                                             │   │
│  │  Sync:                                                      │   │
│  │  ├── 应用 K8s 资源                                          │   │
│  │  └── 默认阶段                                               │   │
│  │                                                             │   │
│  │  PostSync:                                                  │   │
│  │  ├── Smoke Test Job                                         │   │
│  │  ├── 通知发送                                               │   │
│  │  └── 清理操作                                               │   │
│  │                                                             │   │
│  │  SyncFail:                                                  │   │
│  │  ├── 失败通知                                               │   │
│  │  ├── 回滚操作                                               │   │
│  │  └── 告警触发                                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 3.2 Sync Hooks（同步钩子）

```yaml
# PreSync Hook: 数据库迁移
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    # 指定同步阶段
    argocd.argoproj.io/hook: PreSync
    # 删除策略：Hook 成功后删除
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: myapp:v1.2.3
          command: ["./migrate", "up"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: db-credentials
                  key: url
      restartPolicy: Never
  backoffLimit: 1
```

```yaml
# PostSync Hook: Smoke Test
apiVersion: batch/v1
kind: Job
metadata:
  name: smoke-test
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
        - name: test
          image: curlimages/curl:latest
          command:
            - sh
            - -c
            - |
              for i in $(seq 1 10); do
                HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://myapp.production.svc/healthz)
                if [ "$HTTP_CODE" = "200" ]; then
                  echo "Smoke test passed"
                  exit 0
                fi
                echo "Attempt $i: HTTP $HTTP_CODE"
                sleep 5
              done
              echo "Smoke test failed"
              exit 1
      restartPolicy: Never
  backoffLimit: 0
```

```yaml
# SyncFail Hook: 失败通知
apiVersion: batch/v1
kind: Job
metadata:
  name: sync-fail-notify
  annotations:
    argocd.argoproj.io/hook: SyncFail
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
        - name: notify
          image: curlimages/curl:latest
          command:
            - curl
            - -X
            - POST
            - -H
            - "Content-Type: application/json"
            - -d
            - '{"text": "ArgoCD sync failed for myapp"}'
            - $(SLACK_WEBHOOK)
      restartPolicy: Never
  backoffLimit: 0
```

#### 3.3 Sync Windows（同步窗口）

```yaml
# AppProject 中的同步窗口配置
spec:
  syncWindows:
    # 允许窗口：工作时间自动同步
    - kind: allow
      schedule: '0 8-18 * * 1-5'  # 周一到周五 8:00-18:00
      duration: 10h
      applications:
        - '*'
      namespaces:
        - production
      manualSync: true  # 允许手动同步

    # 禁止窗口：周末禁止同步
    - kind: deny
      schedule: '0 0 * * 0,6'  # 周末
      duration: 24h
      applications:
        - '*'
      namespaces:
        - production

    # 禁止窗口：维护窗口期间
    - kind: deny
      schedule: '0 2 * * 3'  # 周三凌晨 2:00
      duration: 2h
      applications:
        - '*'
      namespaces:
        - production
```

---

### 4. 多集群管理

#### 4.1 多集群架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ArgoCD 多集群管理                                  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    ArgoCD Control Plane                       │   │
│  │                    (管理集群)                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ Application  │  │ Application  │  │ Application  │      │   │
│  │  │ Controller   │  │ Server       │  │ Set          │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                              │                                      │
│          ┌───────────────────┼───────────────────┐                 │
│          │                   │                   │                  │
│          ▼                   ▼                   ▼                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Cluster A  │  │   Cluster B  │  │   Cluster C  │             │
│  │  (生产-华东) │  │  (生产-华南) │  │  (灾备)      │             │
│  │              │  │              │  │              │             │
│  │ ┌──────────┐│  │ ┌──────────┐│  │ ┌──────────┐│             │
│  │ │  App A1  ││  │ │  App B1  ││  │ │  App C1  ││             │
│  │ │  App A2  ││  │ │  App B2  ││  │ │  App C2  ││             │
│  │ │  App A3  ││  │ │  App B3  ││  │ │  App C3  ││             │
│  │ └──────────┘│  │ └──────────┘│  │ └──────────┘│             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                     │
│  多集群策略：                                                        │
│  1. 集中管理：一个 ArgoCD 管理多个集群                              │
│  2. Git 统一：所有集群的配置在同一个 Git 仓库                      │
│  3. 差异化配置：每个集群有不同的 overlay                           │
│  4. ApplicationSet：模板化创建多个 Application                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.2 注册远程集群

```bash
# 方式 1: 使用 argocd CLI 注册
# 添加远程集群
argocd cluster add staging-cluster-context --name staging
argocd cluster add production-cluster-context --name production

# 列出已注册集群
argocd cluster list

# 方式 2: 使用 Secret 手动注册
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: staging-cluster
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: cluster
type: Opaque
stringData:
  name: staging
  server: https://staging-cluster.example.com:6443
  config: |
    {
      "bearerToken": "<token>",
      "tlsClientConfig": {
        "insecure": false,
        "caData": "<base64-ca-cert>"
      }
    }
EOF
```

#### 4.3 多集群 Application

```yaml
# 部署到远程集群
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-staging
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/k8s-manifests.git
    targetRevision: main
    path: apps/myapp/overlays/staging
  destination:
    # 指定远程集群
    server: https://staging-cluster.example.com:6443
    namespace: myapp
  syncPolicy:
    automated:
      selfHeal: true
      prune: true
```

---

### 5. ApplicationSet

#### 5.1 ApplicationSet 概念

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ApplicationSet                                    │
│                                                                     │
│  ApplicationSet = Application 模板 + 生成器                         │
│                                                                     │
│  ┌──────────────────┐                                              │
│  │  ApplicationSet   │                                              │
│  │  (模板定义)       │                                              │
│  └────────┬─────────┘                                              │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────┐                                              │
│  │  Generator        │  ← 决定生成哪些 Application                 │
│  │  (生成器)         │                                              │
│  │                   │                                              │
│  │  ├── List         │  ← 静态列表                                 │
│  │  ├── Cluster      │  ← 集群列表                                 │
│  │  ├── Git          │  ← Git 目录/文件                            │
│  │  ├── Matrix       │  ← 组合多个生成器                           │
│  │  ├── Merge        │  ← 合并多个生成器                           │
│  │  └── SCM Provider │  ← GitHub/GitLab 仓库                      │
│  └────────┬─────────┘                                              │
│           │                                                         │
│           ▼                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Application A   │  │  Application B   │  │  Application C   │ │
│  │  (自动生成)      │  │  (自动生成)      │  │  (自动生成)      │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

#### 5.2 List Generator（列表生成器）

```yaml
# 使用 List Generator 为多个环境创建 Application
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-multi-env
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: dev
            cluster: https://kubernetes.default.svc
            namespace: dev
            revision: develop
          - env: staging
            cluster: https://staging.example.com
            namespace: staging
            revision: main
          - env: production
            cluster: https://production.example.com
            namespace: production
            revision: main

  template:
    metadata:
      name: 'myapp-{{env}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/k8s-manifests.git
        targetRevision: '{{revision}}'
        path: 'apps/myapp/overlays/{{env}}'
      destination:
        server: '{{cluster}}'
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          selfHeal: true
          prune: true
        syncOptions:
          - CreateNamespace=true

  # 同步策略
  strategy:
    type: RollingSync
    rollingSync:
      steps:
        - matchExpressions:
            - key: env
              operator: In
              values:
                - dev
        - matchExpressions:
            - key: env
              operator: In
              values:
                - staging
        - matchExpressions:
            - key: env
              operator: In
              values:
                - production
```

#### 5.3 Git Generator（Git 目录生成器）

```yaml
# 使用 Git Generator 自动发现目录并创建 Application
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: auto-apps
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/myorg/k8s-manifests.git
        revision: main
        directories:
          - path: apps/*
          # 排除特定目录
          - path: apps/_templates

  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/k8s-manifests.git
        targetRevision: main
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
      syncPolicy:
        automated:
          selfHeal: true
          prune: true
        syncOptions:
          - CreateNamespace=true
```

#### 5.4 Matrix Generator（矩阵生成器）

```yaml
# 组合集群和环境生成 Application
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-matrix
  namespace: argocd
spec:
  generators:
    - matrix:
        generators:
          # 第一个维度：集群列表
          - clusters:
              selector:
                matchLabels:
                  environment: production
          # 第二个维度：应用列表
          - list:
              elements:
                - appName: api-server
                  port: 8080
                - appName: web-frontend
                  port: 3000
                - appName: worker
                  port: 9090

  template:
    metadata:
      name: '{{appName}}-{{name}}'
    spec:
      project: production
      source:
        repoURL: https://github.com/myorg/k8s-manifests.git
        targetRevision: main
        path: 'apps/{{appName}}/overlays/production'
      destination:
        server: '{{server}}'
        namespace: '{{appName}}'
```

---

### 6. 通知与告警

#### 6.1 ArgoCD Notifications

```yaml
# 安装 ArgoCD Notifications
# ArgoCD 2.3+ 默认包含 notifications-controller

# 配置通知服务（Slack）
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  # Slack 服务配置
  service.slack: |
    token: $slack-token
    signingSecret: $slack-signing-secret

  # 邮件服务配置
  service.email: |
    host: smtp.example.com
    port: 587
    from: argocd@example.com
    username: $email-username
    password: $email-password

  # 模板定义
  template.app-sync-succeeded: |
    message: |
      ✅ Application {{.app.metadata.name}} sync succeeded.
      Revision: {{.app.status.sync.revision}}
      URL: {{.context.argocdUrl}}/applications/{{.app.metadata.name}}

  template.app-sync-failed: |
    message: |
      ❌ Application {{.app.metadata.name}} sync failed.
      Error: {{.app.status.operationState.message}}
      URL: {{.context.argocdUrl}}/applications/{{.app.metadata.name}}

  template.app-health-degraded: |
    message: |
      ⚠️ Application {{.app.metadata.name}} health is degraded.
      Status: {{.app.status.health.status}}
      URL: {{.context.argocdUrl}}/applications/{{.app.metadata.name}}

  # 触发器定义
  trigger.on-sync-succeeded: |
    - when: app.status.operationState.phase in ['Succeeded']
      send: [app-sync-succeeded]

  trigger.on-sync-failed: |
    - when: app.status.operationState.phase in ['Error', 'Failed']
      send: [app-sync-failed]

  trigger.on-health-degraded: |
    - when: app.status.health.status == 'Degraded'
      send: [app-health-degraded]
```

#### 6.2 Application 级别通知配置

```yaml
# 在 Application 上启用通知
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp-production
  namespace: argocd
  annotations:
    # 启用通知触发器
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: production-alerts
    notifications.argoproj.io/subscribe.on-sync-failed.slack: production-alerts
    notifications.argoproj.io/subscribe.on-health-degraded.slack: production-alerts
    # 自定义通知内容
    notifications.argoproj.io/summary: "Production myapp deployment"
spec:
  # ...
```

---

### 7. 回滚

#### 7.1 ArgoCD 回滚机制

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ArgoCD 回滚策略                                    │
│                                                                     │
│  方式 1: Git 回滚（推荐）                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  git revert HEAD                                            │   │
│  │  git push origin main                                       │   │
│  │  → ArgoCD 检测到 Git 变更 → 自动/手动同步                   │   │
│  │                                                             │   │
│  │  优点：                                                      │   │
│  │  - Git 保留完整历史                                          │   │
│  │  - 可审计，可追溯                                            │   │
│  │  - 配置和代码一起回滚                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  方式 2: ArgoCD Revision 回滚                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  argocd app rollback myapp <revision-number>                │   │
│  │  → 回滚到指定的 Git revision                                 │   │
│  │                                                             │   │
│  │  优点：                                                      │   │
│  │  - 快速回滚，无需 Git 操作                                   │   │
│  │  - 可以回滚到任意历史 revision                               │   │
│  │                                                             │   │
│  │  缺点：                                                      │   │
│  │  - Git 仓库状态与集群不一致                                  │   │
│  │  - 下次 Git 变更会覆盖回滚                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  方式 3: 手动同步到指定版本                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  argocd app sync myapp --revision <git-commit-sha>          │   │
│  │  → 同步到指定的 Git commit                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

#### 7.2 回滚操作

```bash
# 查看 Application 历史
argocd app history myapp-production

# 输出示例：
# ID  DATE                           REVISION
# 0   2026-05-03 10:00:00 +0000 UTC  abc1234 (v1.2.3)
# 1   2026-05-02 15:30:00 +0000 UTC  def5678 (v1.2.2)
# 2   2026-05-01 09:00:00 +0000 UTC  ghi9012 (v1.2.1)

# 回滚到上一个版本
argocd app rollback myapp-production 1

# 回滚到指定版本
argocd app rollback myapp-production 2

# 查看当前状态
argocd app get myapp-production
```

---

### 8. 最佳实践

#### 8.1 ArgoCD 生产级最佳实践

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ArgoCD 生产级最佳实践                              │
│                                                                     │
│  1. Git 仓库结构                                                    │
│  ├── 应用代码仓库（源代码 + Dockerfile）                           │
│  ├── K8s 配置仓库（manifests + overlays）                          │
│  ├── 环境分离（目录或分支）                                        │
│  └── 模板化（Kustomize/Helm）                                      │
│                                                                     │
│  2. 安全配置                                                        │
│  ├── SSO/OIDC 身份认证                                             │
│  ├── RBAC 细粒度权限控制                                           │
│  ├── AppProject 资源隔离                                           │
│  ├── Secret 管理（Sealed Secrets / Vault / ESO）                   │
│  └── 网络策略限制 ArgoCD 组件通信                                  │
│                                                                     │
│  3. 同步策略                                                        │
│  ├── DEV: 自动同步 + selfHeal + prune                              │
│  ├── STAGING: 自动同步（main 分支）                                │
│  ├── PRODUCTION: 手动同步 + 审批                                   │
│  ├── Sync Windows 限制同步时间                                     │
│  └── Sync Hooks 处理有状态操作                                     │
│                                                                     │
│  4. 高可用配置                                                      │
│  ├── Controller: 2 副本（Active-Standby）                          │
│  ├── Server: 2+ 副本（负载均衡）                                   │
│  ├── Repo Server: 2+ 副本                                          │
│  ├── Redis: HA 模式（Sentinel/Cluster）                            │
│  └── etcd: 外部高可用 etcd                                         │
│                                                                     │
│  5. 监控与告警                                                      │
│  ├── Prometheus metrics 指标采集                                   │
│  ├── Grafana Dashboard 可视化                                      │
│  ├── Notifications Controller 通知集成                             │
│  ├── 同步失败/健康异常告警                                         │
│  └── Application 状态仪表盘                                        │
│                                                                     │
│  6. 灾难恢复                                                        │
│  ├── etcd 定期备份                                                 │
│  ├── Git 仓库作为配置源（天然备份）                                │
│  ├── ArgoCD 配置定期导出                                           │
│  └── 跨集群 ArgoCD 灾备                                            │
└─────────────────────────────────────────────────────────────────────┘
```

#### 8.2 ArgoCD 监控配置

```yaml
# Prometheus ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: argocd-metrics
  namespace: argocd
spec:
  selector:
    matchLabels:
      app.kubernetes.io/part-of: argocd
  endpoints:
    - port: metrics
      interval: 30s
```

```yaml
# PrometheusRule 告警规则
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: argocd-alerts
  namespace: argocd
spec:
  groups:
    - name: argocd
      rules:
        # 应用同步失败
        - alert: ArgoAppSyncFailed
          expr: |
            argocd_app_info{sync_status="OutOfSync"} == 1
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Application {{ $labels.name }} is out of sync"
            description: "Application {{ $labels.name }} has been out of sync for 10 minutes"

        # 应用健康异常
        - alert: ArgoAppUnhealthy
          expr: |
            argocd_app_info{health_status!="Healthy"} == 1
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "Application {{ $labels.name }} is unhealthy"
            description: "Application {{ $labels.name }} health status: {{ $labels.health_status }}"

        # ArgoCD Controller 指标
        - alert: ArgoControllerHighMemory
          expr: |
            container_memory_usage_bytes{container="argocd-application-controller"} / 1024 / 1024 > 2048
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "ArgoCD Controller high memory usage"
```

#### 8.3 SRE 实战案例：GitOps 迁移

**背景：** 某公司从传统 CI/CD（kubectl apply）迁移到 GitOps（ArgoCD）。

```
┌─────────────────────────────────────────────────────────────────────┐
│              GitOps 迁移步骤                                         │
│                                                                     │
│  阶段 1: 准备（1-2 周）                                             │
│  ├── 评估现有 CI/CD 流程                                           │
│  ├── 设计 Git 仓库结构                                             │
│  ├── 创建 Kustomize base/overlay                                   │
│  ├── 部署 ArgoCD 到管理集群                                        │
│  └── 配置 SSO、RBAC、Projects                                      │
│                                                                     │
│  阶段 2: 试点（2-4 周）                                             │
│  ├── 选择 1-2 个无状态服务试点                                     │
│  ├── 创建 Application 配置                                         │
│  ├── 配置自动同步和通知                                            │
│  ├── 验证同步和回滚流程                                            │
│  └── 培训开发团队                                                  │
│                                                                     │
│  阶段 3: 推广（4-8 周）                                             │
│  ├── 逐步迁移更多服务                                              │
│  ├── 使用 ApplicationSet 批量管理                                  │
│  ├── 配置 Sync Windows                                             │
│  ├── 集成监控和告警                                                │
│  └── 处理有状态服务（DB migration）                                │
│                                                                     │
│  阶段 4: 优化（持续）                                               │
│  ├── 多集群管理                                                    │
│  ├── 渐进式交付（Argo Rollouts）                                   │
│  ├── Secret 管理（Vault/ESO）                                      │
│  ├── 安全加固（镜像签名、准入控制）                                │
│  └── 定期评审和优化                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 💻 实战练习

### 练习 1：安装 ArgoCD 并创建第一个 Application

**目标：** 在本地 K8s 集群安装 ArgoCD，部署一个示例应用

```bash
# 步骤 1: 安装 ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 等待就绪
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# 步骤 2: 访问 ArgoCD UI
# 端口转发
kubectl port-forward svc/argocd-server -n argocd 8080:443 &

# 获取初始密码
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# 步骤 3: 创建 Application
cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
  syncPolicy:
    automated:
      selfHeal: true
      prune: true
    syncOptions:
      - CreateNamespace=true
EOF

# 步骤 4: 检查状态
argocd app get guestbook
kubectl get pods -n guestbook
```

### 练习 2：配置 ApplicationSet 批量管理

**目标：** 使用 ApplicationSet 为 dev/staging/prod 三个环境创建 Application

```yaml
# 创建 appset-multi-env.yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: myapp-envs
  namespace: argocd
spec:
  generators:
    - list:
        elements:
          - env: dev
            revision: develop
            autoSync: "true"
          - env: staging
            revision: main
            autoSync: "true"
          - env: production
            revision: main
            autoSync: "false"
  template:
    metadata:
      name: 'myapp-{{env}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/argoproj/argocd-example-apps.git
        targetRevision: '{{revision}}'
        path: guestbook
      destination:
        server: https://kubernetes.default.svc
        namespace: 'myapp-{{env}}'
      syncPolicy:
        syncOptions:
          - CreateNamespace=true
```

### 练习 3：配置 Sync Hooks 和通知

**目标：** 为应用配置 PreSync（数据库迁移）和 PostSync（Smoke Test）钩子

```yaml
# 创建 pre-sync-migration Job
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  namespace: myapp
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: myapp:latest
          command: ["echo", "Migration completed"]
      restartPolicy: Never
  backoffLimit: 1
---
# 创建 post-sync smoke test Job
apiVersion: batch/v1
kind: Job
metadata:
  name: smoke-test
  namespace: myapp
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
        - name: test
          image: curlimages/curl:latest
          command:
            - sh
            - -c
            - |
              echo "Running smoke test..."
              sleep 10
              echo "Smoke test passed!"
      restartPolicy: Never
  backoffLimit: 0
```

---

## 🎯 面试题精选

### 面试题 1：解释 ArgoCD 的架构和核心组件

**答案：**

ArgoCD 由以下核心组件组成：

1. **API Server**：提供 REST/gRPC API 和 Web UI，处理用户请求
2. **Repo Server**：克隆 Git 仓库，渲染 Helm/Kustomize 模板，生成 K8s manifests
3. **Application Controller**：核心控制器，比较 Git 期望状态与集群实际状态，执行同步操作
4. **Dex**：身份认证代理，支持 OIDC/LDAP/GitHub OAuth 等
5. **Redis**：缓存应用状态和 Git 仓库数据
6. **Notifications Controller**：发送同步状态通知

数据流：用户创建 Application → Controller 检测 → Repo Server 获取 manifests → Controller 比较差异 → 执行同步。

### 面试题 2：ArgoCD 的同步策略有哪些？什么时候用自动同步，什么时候用手动同步？

**答案：**

**同步策略：**
- **手动同步**：需要人工触发，适合生产环境
- **自动同步**：Git 变更自动触发，适合开发/测试环境
- **自动同步 + selfHeal**：自动回退手动变更，确保 Git 是唯一事实来源
- **自动同步 + prune**：自动删除 Git 中不存在的资源

**选择策略：**
- DEV：自动同步 + selfHeal + prune（快速迭代）
- STAGING：自动同步（main 分支触发，用于验证）
- PRODUCTION：手动同步 + 审批门控（控制风险）
- Sync Windows：限制自动同步时间窗口（避免非工作时间部署）

### 面试题 3：什么是 ApplicationSet？它的使用场景是什么？

**答案：**

ApplicationSet 是 ArgoCD 的 Application 模板引擎，可以根据模板和生成器自动创建多个 Application。

**使用场景：**
1. **多环境管理**：一个 ApplicationSet 为 dev/staging/prod 创建 Application
2. **多集群管理**：为每个集群创建相同的 Application
3. **多租户**：为每个团队/项目自动创建 Application
4. **微服务批量管理**：为每个微服务创建 Application

**生成器类型：**
- List：静态列表
- Cluster：集群列表
- Git：Git 目录/文件
- Matrix：组合多个生成器
- Merge：合并多个生成器

### 面试题 4：ArgoCD 如何处理多集群部署？

**答案：**

ArgoCD 通过以下机制支持多集群部署：

1. **集群注册**：通过 CLI 或 Secret 注册远程集群
2. **Application 目标**：destination.server 指定远程集群地址
3. **ApplicationSet**：使用 Cluster Generator 自动为多个集群创建 Application
4. **差异化配置**：每个集群使用不同的 overlay 目录

**最佳实践：**
- 使用 ApplicationSet 批量管理多集群 Application
- 使用 Git 目录结构分离集群配置
- 配置集群级别的 RBAC 权限
- 使用 Sync Windows 控制部署时间

### 面试题 5：ArgoCD 的回滚机制是什么？推荐使用哪种方式？

**答案：**

**回滚方式：**
1. **Git 回滚**（推荐）：git revert + push → ArgoCD 自动同步
2. **Revision 回滚**：`argocd app rollback <revision>` → 回到指定版本
3. **手动同步**：`argocd app sync --revision <sha>` → 同步到指定 commit

**推荐使用 Git 回滚：**
- 保留完整审计日志
- Git 状态与集群状态一致
- 下次部署不会覆盖回滚
- 可以回滚配置和代码

### 面试题 6：什么是 Sync Windows？如何使用它来控制部署时间？

**答案：**

Sync Windows 是 ArgoCD 的同步时间窗口机制，用于限制自动同步的时间范围。

**窗口类型：**
- **allow**：允许自动同步的时间窗口
- **deny**：禁止自动同步的时间窗口

**使用场景：**
- 工作时间允许同步：`schedule: '0 8-18 * * 1-5'`
- 周末禁止同步：`schedule: '0 0 * * 0,6'`
- 维护窗口禁止同步：特定时间段

**配置方式：** 在 AppProject 中定义 syncWindows

### 面试题 7：ArgoCD 如何处理有状态应用的部署（如数据库迁移）？

**答案：**

ArgoCD 通过 Sync Hooks 处理有状态操作：

1. **PreSync Hook**：在同步前执行，用于数据库迁移、配置预检
2. **PostSync Hook**：在同步后执行，用于 Smoke Test、通知
3. **SyncFail Hook**：同步失败时执行，用于告警、回滚

**数据库迁移最佳实践：**
- 使用 PreSync Hook 执行迁移 Job
- 迁移必须是幂等的（可重复执行）
- 迁移必须是可回滚的（down migration）
- 配置 hook-delete-policy 自动清理
- 使用 golang-migrate/Flyway/Liquibase 等工具

### 面试题 8：如何确保 ArgoCD 本身的高可用？

**答案：**

1. **Application Controller**：2 副本，Active-Standby 模式
2. **API Server**：2+ 副本，负载均衡
3. **Repo Server**：2+ 副本，水平扩展
4. **Redis**：使用 redis-ha（Sentinel 或 Cluster 模式）
5. **etcd**：使用外部高可用 etcd（如果 K8s 使用外部 etcd）
6. **持久化存储**：使用高可用存储后端
7. **监控告警**：Prometheus + Grafana 监控 ArgoCD 指标
8. **备份恢复**：定期备份 ArgoCD 配置和 etcd 数据

---

## 📚 深入阅读

1. **ArgoCD 官方文档** - https://argo-cd.readthedocs.io/
2. **ArgoCD Best Practices** - https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/
3. **ApplicationSet 文档** - https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/
4. **ArgoCD Notifications** - https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/
5. **GitOps 原则** - https://opengitops.dev/
6. **ArgoCD Helm Chart** - https://github.com/argoproj/argo-helm
7. **Argo Rollouts** - https://argoproj.github.io/rollouts/
8. **Flux CD vs ArgoCD 对比** - GitOps 工具选型

---

## ✅ 自检清单

- [ ] 理解 ArgoCD 的架构和核心组件（API Server、Repo Server、Controller）
- [ ] 能够安装和配置 ArgoCD
- [ ] 掌握 Application 和 AppProject 的配置
- [ ] 理解手动同步、自动同步、selfHeal、prune 的区别
- [ ] 能够配置 Sync Hooks（PreSync、PostSync、SyncFail）
- [ ] 理解 Sync Windows 的使用场景
- [ ] 能够配置多集群管理和 ApplicationSet
- [ ] 掌握 ArgoCD 通知集成配置
- [ ] 理解 Git 回滚和 Revision 回滚的区别
- [ ] 能够设计 ArgoCD 生产级部署方案
- [ ] 掌握 ArgoCD 监控和告警配置
- [ ] 能够处理有状态应用的 GitOps 部署
