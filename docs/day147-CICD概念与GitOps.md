# Day 147: CI/CD 概念与 GitOps

> 📅 日期：2026-05-05
> 📖 学习主题：CI/CD 三阶段、DevOps vs SRE、GitOps 原则、ArgoCD vs Flux、部署策略、流水线设计
> ⏰ 预计学习时间：3-4 小时
> 📋 前置知识：Day 131（自动化部署）、Day 132（Terraform 与 Ansible 综合实践）

---

## 🎯 学习目标

- 理解 CI、CD（持续交付）、CD（持续部署）三个阶段的区别与联系
- 掌握 DevOps 与 SRE 的异同，明确 SRE 在 CI/CD 中的职责
- 深入理解 GitOps 四原则及其在生产环境中的实践
- 对比 ArgoCD 与 Flux 两大 GitOps 工具的架构与适用场景
- 掌握蓝绿部署、金丝雀发布、滚动更新等部署策略
- 能设计一条完整的 CI/CD 流水线

---

## 📖 核心知识点

### 1. CI/CD 三阶段详解

#### 1.1 持续集成（Continuous Integration）

持续集成是开发人员频繁（每天至少一次）将代码合并到共享仓库的实践。每次合并都会触发自动构建和测试，以便尽早发现集成错误。

```
持续集成工作流：

┌─────────────────────────────────────────────────────────────┐
│                     持续集成（CI）                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  开发者 A ──┐                                                │
│  开发者 B ──┼──► 共享仓库（main branch）                      │
│  开发者 C ──┘         │                                      │
│                       ▼                                      │
│              ┌─────────────────┐                             │
│              │  触发 CI 流水线   │                             │
│              └────────┬────────┘                             │
│                       │                                      │
│         ┌─────────────┼─────────────┐                        │
│         ▼             ▼             ▼                        │
│    ┌─────────┐  ┌──────────┐  ┌──────────┐                  │
│    │  编译    │  │  单元测试  │  │  代码扫描 │                  │
│    │  Build   │  │  Unit     │  │  Lint    │                  │
│    └────┬────┘  └────┬─────┘  └────┬─────┘                  │
│         │            │             │                         │
│         └────────────┼─────────────┘                         │
│                      ▼                                       │
│              ┌──────────────┐                                │
│              │  构建产物      │                                │
│              │  Artifacts    │                                │
│              └──────┬───────┘                                │
│                     ▼                                        │
│              ┌──────────────┐                                │
│              │  反馈报告      │                                │
│              │  ✅ 或 ❌     │                                │
│              └──────────────┘                                │
└─────────────────────────────────────────────────────────────┘
```

CI 的核心实践：

| 实践 | 说明 | SRE 关注点 |
|------|------|-----------|
| 频繁提交 | 每天至少一次合并到主干 | 减少合并冲突，降低集成风险 |
| 自动化构建 | 代码提交后自动编译 | 构建时间 < 10 分钟 |
| 自动化测试 | 单元测试 + 集成测试 | 测试覆盖率 > 80% |
| 快速反馈 | 构建失败立即通知 | 5 分钟内通知责任人 |
| 修复优先 | 构建失败是最高优先级 | 主干分支始终可部署 |
| 代码审查 | PR 必须经过 Review | 自动化检查 + 人工审查 |

#### 1.2 持续交付（Continuous Delivery）

持续交付是 CI 的延伸，确保代码随时可以部署到生产环境。部署到生产环境需要手动触发（人工审批门禁）。

```
持续交付流水线：

┌────────────────────────────────────────────────────────────────────┐
│                       持续交付（CD - Delivery）                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────┐   ┌──────┐   ┌──────────┐   ┌──────────┐   ┌────────┐ │
│  │ 提交  │──►│ 构建  │──►│ 测试环境   │──►│ 预发布    │──►│ 生产   │ │
│  │Commit │   │Build │   │ Staging  │   │ Pre-prod │   │ 门禁   │ │
│  └──────┘   └──────┘   └──────────┘   └──────────┘   └───┬────┘ │
│                                                           │      │
│                                                    ┌──────┴────┐ │
│                                                    │ 手动审批   │ │
│                                                    │ Manual    │ │
│                                                    │ Approval  │ │
│                                                    └──────┬────┘ │
│                                                           │      │
│                                                           ▼      │
│                                                     ┌──────────┐ │
│                                                     │ 生产部署  │ │
│                                                     │ Deploy   │ │
│                                                     └──────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

#### 1.3 持续部署（Continuous Deployment）

持续部署是持续交付的进一步延伸，代码通过所有测试后自动部署到生产环境，无需人工干预。

```
持续部署 vs 持续交付 对比：

┌──────────────────────────────────────────────────────────────┐
│                    持续交付 vs 持续部署                         │
├────────────────────┬─────────────────────────────────────────┤
│                    │  持续交付            持续部署              │
├────────────────────┼─────────────────────────────────────────┤
│ 自动构建           │  ✅ 是              ✅ 是                │
│ 自动测试           │  ✅ 是              ✅ 是                │
│ 自动部署到 Staging │  ✅ 是              ✅ 是                │
│ 自动部署到生产     │  ❌ 手动触发         ✅ 全自动             │
│ 人工审批门禁       │  ✅ 需要             ❌ 不需要             │
│ 风险控制           │  高（人工把关）       低（依赖自动化测试）  │
│ 适用场景           │  传统企业、金融       互联网、SaaS         │
│ 发布频率           │  每周/每月           每天/每次提交          │
│ 回滚速度           │  较慢               极快（秒级）           │
└────────────────────┴─────────────────────────────────────────┘
```

#### 1.4 CI/CD 完整流水线全景

```
完整的 CI/CD 流水线：

┌─────────────────────────────────────────────────────────────────────────┐
│                        完整 CI/CD 流水线                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐ │
│  │  源码    │   │  构建    │   │  测试    │   │  发布    │   │  部署    │ │
│  │ Source   │──►│ Build   │──►│ Test    │──►│ Release │──►│ Deploy  │ │
│  └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘   └────┬────┘ │
│       │             │             │             │             │       │
│  ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐ │
│  │Git Push │   │Compile  │   │Unit Test│   │Tag      │   │Canary   │ │
│  │PR Merge │   │Docker   │   │Int Test │   │Docker   │   │Blue/    │ │
│  │Webhook  │   │Build    │   │E2E Test │   │Push     │   │Green    │ │
│  │         │   │SAST     │   │Perf Test│   │Helm     │   │Rolling  │ │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘ │
│                                                                         │
│  ◄────────────────── 持续集成 (CI) ──────────────────►                  │
│                                    ◄──────── 持续交付/部署 (CD) ────────►│
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. DevOps vs SRE

#### 2.1 概念对比

```
DevOps 与 SRE 的关系：

┌─────────────────────────────────────────────────────────┐
│                                                         │
│              ┌─────────────────────┐                    │
│              │      DevOps         │                    │
│              │   (文化/方法论)      │                    │
│              │                     │                    │
│              │  ┌───────────────┐  │                    │
│              │  │     SRE       │  │                    │
│              │  │  (实践/工程)   │  │                    │
│              │  │               │  │                    │
│              │  │  Google 提出   │  │                    │
│              │  │  的具体实践    │  │                    │
│              │  └───────────────┘  │                    │
│              │                     │                    │
│              │  ┌───────────────┐  │                    │
│              │  │  Platform     │  │                    │
│              │  │  Engineering  │  │                    │
│              │  └───────────────┘  │                    │
│              └─────────────────────┘                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

| 维度 | DevOps | SRE |
|------|--------|-----|
| 起源 | 2009 年 DevOps 运动 | 2003 年 Google 内部实践 |
| 定义 | 文化理念和方法论 | 具体的工程实践 |
| 核心目标 | 打破开发与运维壁垒 | 用工程方法解决运维问题 |
| 关键指标 | 部署频率、变更前置时间 | SLO、SLI、错误预算 |
| 故障态度 | 接受失败，快速恢复 | 错误预算驱动决策 |
| 自动化 | CI/CD 流水线 | 消除手工操作（Toil） |
| 监控 | 可观测性三大支柱 | SLO-based 监控 |
| 发布 | 持续部署 | 渐进式发布 + 回滚 |
| 团队结构 | 跨职能团队 | SRE 团队（50% 开发 + 50% 运维） |

#### 2.2 SRE 在 CI/CD 中的职责

```
SRE 在 CI/CD 中的职责图：

┌──────────────────────────────────────────────────────────────┐
│                    SRE 在 CI/CD 中的职责                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  流水线设计    │  │  发布策略     │  │  可靠性保障   │       │
│  │              │  │              │  │              │       │
│  │ • 构建优化    │  │ • 金丝雀发布  │  │ • SLO 监控   │       │
│  │ • 缓存策略    │  │ • 蓝绿部署    │  │ • 错误预算   │       │
│  │ • 并行执行    │  │ • 渐进式发布  │  │ • 自动回滚   │       │
│  │ • 安全扫描    │  │ • 特性开关    │  │ • 告警配置   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  平台工程     │  │  GitOps      │  │  故障响应     │       │
│  │              │  │              │  │              │       │
│  │ • Runner 管理│  │ • ArgoCD     │  │ • 快速回滚   │       │
│  │ • 共享库     │  │ • Flux       │  │ • 根因分析   │       │
│  │ • 模板化     │  │ • 声明式管理  │  │ • 事后复盘   │       │
│  │ • 权限控制   │  │ • 自动同步    │  │ • 改进项跟踪 │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

### 3. GitOps 原则

#### 3.1 GitOps 四原则

GitOps 是由 Weaveworks 在 2017 年提出的，以 Git 仓库作为基础设施和应用配置的唯一事实来源。

```
GitOps 四原则：

┌──────────────────────────────────────────────────────────────┐
│                     GitOps 四原则                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  原则 1: 声明式（Declarative）                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 系统的期望状态必须以声明式方式描述                      │    │
│  │ • Kubernetes YAML、Helm Charts、Kustomize            │    │
│  │ • 不描述"如何做"，只描述"要什么"                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  原则 2: 版本化与不可变（Versioned and Immutable）              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 所有期望状态存储在 Git 中                             │    │
│  │ • 每次变更有完整的审计记录                               │    │
│  │ • 可以回滚到任意历史版本                                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  原则 3: 自动拉取（Pulled Automatically）                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • Agent 主动从 Git 拉取期望状态                        │    │
│  │ • 不是 push 部署，而是 pull 同步                        │    │
│  │ • 减少对 CI 系统的权限依赖                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  原则 4: 持续调谐（Continuously Reconciled）                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 持续观察实际状态，与期望状态对比                       │    │
│  │ • 发现漂移时自动修复                                    │    │
│  │ • 确保系统始终处于期望状态                               │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 3.2 GitOps 工作流

```
GitOps 完整工作流：

┌──────────────────────────────────────────────────────────────────────┐
│                        GitOps 工作流                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐     ┌──────────┐     ┌──────────────────┐             │
│  │ 开发者    │────►│ App Repo │────►│   CI Pipeline    │             │
│  │          │     │ (源代码)  │     │ (构建/测试/推送)   │             │
│  └──────────┘     └──────────┘     └────────┬─────────┘             │
│                                              │                       │
│                                    更新镜像 Tag                       │
│                                              │                       │
│                                              ▼                       │
│                                    ┌──────────────────┐             │
│                                    │  Config Repo     │             │
│                                    │  (部署清单)       │             │
│                                    │                  │             │
│                                    │ deployment.yaml: │             │
│                                    │   image: v1.2.3  │             │
│                                    └────────┬─────────┘             │
│                                              │                       │
│                                    GitOps Controller 监听            │
│                                              │                       │
│                                              ▼                       │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │                    Kubernetes Cluster                      │       │
│  │                                                          │       │
│  │  ┌──────────────┐    ┌──────────────┐                    │       │
│  │  │ ArgoCD/Flux  │───►│  Application │                    │       │
│  │  │ (拉取+调谐)   │    │  (实际运行)   │                    │       │
│  │  └──────────────┘    └──────────────┘                    │       │
│  │         ▲                                                │       │
│  │         │ 持续对比                                        │       │
│  │         │                                                │       │
│  │  期望状态 = Git 中的配置                                   │       │
│  │  实际状态 = 集群中运行的资源                                │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│  GitOps Controller 定期（默认 3-5 分钟）检查：                        │
│  1. Git 仓库是否有新提交？                                            │
│  2. 集群实际状态是否与期望状态一致？                                    │
│  3. 不一致时自动同步修复                                               │
└──────────────────────────────────────────────────────────────────────┘
```

#### 3.3 GitOps vs 传统 CI/CD

| 维度 | 传统 CI/CD（Push） | GitOps（Pull） |
|------|-------------------|----------------|
| 部署触发 | CI 系统 push 到集群 | Agent 从 Git pull |
| 凭证管理 | CI 系统需要集群凭证 | Agent 在集群内部，无需外部凭证 |
| 审计追踪 | CI 日志（可能丢失） | Git 历史（永久保存） |
| 回滚方式 | 重新部署旧版本 | `git revert` |
| 漂移检测 | 无自动检测 | 持续调谐，自动修复 |
| 安全模型 | CI 系统有高权限 | 最小权限原则 |
| 灾难恢复 | 依赖 CI 系统状态 | Git clone 即可恢复 |
| 多集群管理 | 每个集群单独配置 | 一个 Repo 管理多集群 |

### 4. ArgoCD vs Flux

#### 4.1 ArgoCD 架构

```
ArgoCD 架构：

┌──────────────────────────────────────────────────────────────┐
│                      ArgoCD 架构                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    ArgoCD Server                       │   │
│  │                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ API      │  │ Web UI   │  │ gRPC     │           │   │
│  │  │ Server   │  │ (CLI)    │  │ Server   │           │   │
│  │  └────┬─────┘  └──────────┘  └──────────┘           │   │
│  │       │                                              │   │
│  │  ┌────┴──────────────────────────────────┐           │   │
│  │  │         Application Controller         │           │   │
│  │  │                                       │           │   │
│  │  │  ┌────────────┐  ┌────────────────┐   │           │   │
│  │  │  │ Repo       │  │ Application    │   │           │   │
│  │  │  │ Server     │  │ Controller     │   │           │   │
│  │  │  │ (拉取Git)   │  │ (同步调谐)     │   │           │   │
│  │  │  └────────────┘  └────────────────┘   │           │   │
│  │  │                                       │           │   │
│  │  │  ┌────────────┐  ┌────────────────┐   │           │   │
│  │  │  │ Dex        │  │ Notification   │   │           │   │
│  │  │  │ (SSO认证)   │  │ Controller     │   │           │   │
│  │  │  └────────────┘  └────────────────┘   │           │   │
│  │  └───────────────────────────────────────┘           │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 Kubernetes Cluster                     │   │
│  │                                                      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐              │   │
│  │  │ App A   │  │ App B   │  │ App C   │              │   │
│  │  │ v1.2.3  │  │ v2.0.1  │  │ v1.0.0  │              │   │
│  │  └─────────┘  └─────────┘  └─────────┘              │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

ArgoCD 核心概念：

| 概念 | 说明 |
|------|------|
| Application | 定义 Git 仓库到 Kubernetes 集群的映射关系 |
| Project | Application 的逻辑分组，用于权限控制 |
| AppSet | ApplicationSet，自动生成 Application（多集群场景） |
| Sync | 将 Git 中的期望状态同步到集群 |
| Health | 资源的健康状态（Healthy、Degraded、Progressing） |
| Sync Status | 同步状态（Synced、OutOfSync） |

ArgoCD Application 定义示例：

```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/org/k8s-manifests.git
    targetRevision: main
    path: apps/my-app/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      prune: true        # 删除 Git 中已移除的资源
      selfHeal: true     # 自动修复手动修改
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

#### 4.2 Flux 架构

```
Flux v2 架构：

┌──────────────────────────────────────────────────────────────┐
│                       Flux v2 架构                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   Flux Controllers                       ││
│  │                                                         ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     ││
│  │  │  Source      │  │  Kustomize  │  │  Helm       │     ││
│  │  │  Controller  │  │  Controller │  │  Controller │     ││
│  │  │             │  │             │  │             │     ││
│  │  │ 管理 Git/   │  │ 应用        │  │ 管理 Helm   │     ││
│  │  │ Helm/OCI    │  │ Kustomize   │  │ Releases    │     ││
│  │  │ 源          │  │ 覆盖        │  │             │     ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘     ││
│  │                                                         ││
│  │  ┌─────────────┐  ┌─────────────┐                      ││
│  │  │  Image      │  │  Notification│                      ││
│  │  │  Reflector  │  │  Controller │                      ││
│  │  │  Controller │  │             │                      ││
│  │  │             │  │ 处理告警和   │                      ││
│  │  │ 自动更新    │  │ Webhook     │                      ││
│  │  │ 镜像 Tag    │  │             │                      ││
│  │  └─────────────┘  └─────────────┘                      ││
│  └─────────────────────────────────────────────────────────┘│
│                           │                                  │
│                           ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 Kubernetes Cluster                     │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Flux 核心 CRD：

```yaml
# flux-git-source.yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 1m
  url: https://github.com/org/k8s-manifests.git
  ref:
    branch: main
  secretRef:
    name: git-credentials

---
# flux-kustomization.yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  interval: 5m
  path: ./apps/my-app/production
  prune: true
  sourceRef:
    kind: GitRepository
    name: my-app
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: my-app
      namespace: my-app
  timeout: 3m
```

#### 4.3 ArgoCD vs Flux 对比

| 维度 | ArgoCD | Flux |
|------|--------|------|
| 开发商 | Intuit（现 CNCF 毕业项目） | Weaveworks（现 CNCF 毕业项目） |
| UI | 内置强大的 Web UI | 无内置 UI（需 Weave GitOps） |
| 架构 | 单体（集中式控制器） | 微内核（独立控制器） |
| 配置管理 | Kustomize、Helm、Jsonnet、目录 | Kustomize、Helm、OCI |
| 多集群 | ApplicationSet 原生支持 | 需要额外配置 |
| SSO | 内置 Dex 支持 | 需要外部实现 |
| RBAC | 内置精细权限控制 | 依赖 K8s RBAC |
| 通知 | 内置 Notification Controller | 依赖 Notification Controller |
| 学习曲线 | 较低（有 UI） | 较高（纯 YAML） |
| 资源消耗 | 较高 | 较低 |
| 自动镜像更新 | 需要 Image Updater | 内置 Image Automation |
| 推荐场景 | 需要 UI、多集群、团队协作 | 轻量级、纯 Git 工作流 |

### 5. 部署策略

#### 5.1 部署策略全景

```
部署策略对比：

┌──────────────────────────────────────────────────────────────┐
│                      部署策略全景                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 滚动更新（Rolling Update）                                │
│  ┌────────────────────────────────────────────────────┐     │
│  │ v1 v1 v1 v1 v1 v1                                   │     │
│  │  ↓  ↓  ↓  ↓  ↓  ↓                                   │     │
│  │ v2 v1 v1 v1 v1 v1  → v2 v2 v1 v1 v1 v1              │     │
│  │                    → v2 v2 v2 v1 v1 v1              │     │
│  │                    → v2 v2 v2 v2 v2 v2              │     │
│  │                                                     │     │
│  │ 优点: 零停机，资源消耗少                               │     │
│  │ 缺点: 新旧版本共存，回滚较慢                           │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  2. 蓝绿部署（Blue-Green）                                    │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                     │     │
│  │  蓝（当前）: v1 v1 v1 v1 v1 v1  ◄── 流量           │     │
│  │  绿（新版）: v2 v2 v2 v2 v2 v2  (空闲)             │     │
│  │                                                     │     │
│  │  切换: 流量从蓝 → 绿（秒级）                         │     │
│  │                                                     │     │
│  │  蓝（旧版）: v1 v1 v1 v1 v1 v1  (待命)             │     │
│  │  绿（新版）: v2 v2 v2 v2 v2 v2  ◄── 流量           │     │
│  │                                                     │     │
│  │ 优点: 零停机，秒级切换，快速回滚                      │     │
│  │ 缺点: 需要双倍资源                                   │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  3. 金丝雀发布（Canary）                                      │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                     │     │
│  │  阶段 1: v1 v1 v1 v1 v1 │ v2  (5% 流量到 v2)       │     │
│  │  阶段 2: v1 v1 v1 v1    │ v2 v2 (20% 流量到 v2)    │     │
│  │  阶段 3: v1 v1          │ v2 v2 v2 v2 (50%)        │     │
│  │  阶段 4: v2 v2 v2 v2 v2 v2 (100%)                  │     │
│  │                                                     │     │
│  │ 优点: 风险最低，逐步验证                              │     │
│  │ 缺点: 发布周期长，需要流量控制                         │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  4. A/B 测试                                                 │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                     │     │
│  │  用户 A（Chrome）──► v1                              │     │
│  │  用户 B（Firefox）──► v2                             │     │
│  │                                                     │     │
│  │  按用户特征（浏览器、地区、用户ID）分流                │     │
│  │  用于功能实验和用户行为分析                            │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

#### 5.2 Kubernetes 中的部署策略实现

```yaml
# 滚动更新 - Kubernetes 原生支持
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 6
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2        # 最多多出 2 个 Pod
      maxUnavailable: 1  # 最多 1 个 Pod 不可用
  template:
    spec:
      containers:
        - name: my-app
          image: my-app:v2

---
# 金丝雀发布 - 使用 Istio VirtualService
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app
spec:
  hosts:
    - my-app.example.com
  http:
    - route:
        - destination:
            host: my-app
            subset: stable
          weight: 90
        - destination:
            host: my-app
            subset: canary
          weight: 10

---
# 蓝绿部署 - 使用两个 Service
# Blue (当前)
apiVersion: v1
kind: Service
metadata:
  name: my-app-blue
spec:
  selector:
    app: my-app
    version: blue
  ports:
    - port: 80

# Green (新版)
apiVersion: v1
kind: Service
metadata:
  name: my-app-green
spec:
  selector:
    app: my-app
    version: green
  ports:
    - port: 80

# 主 Service - 切换 selector 即可切换版本
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  selector:
    app: my-app
    version: blue  # 改为 green 即切换
  ports:
    - port: 80
```

#### 5.3 Argo Rollouts - 高级部署策略

```yaml
# Argo Rollouts - 金丝雀发布
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  replicas: 6
  strategy:
    canary:
      steps:
        - setWeight: 5
        - pause: { duration: 5m }    # 观察 5 分钟
        - setWeight: 20
        - pause: { duration: 10m }   # 观察 10 分钟
        - setWeight: 50
        - pause: { duration: 10m }
        - setWeight: 80
        - pause: { duration: 5m }
      analysis:
        templates:
          - templateName: success-rate
        startingStep: 1
        args:
          - name: service-name
            value: my-app
      canaryService: my-app-canary
      stableService: my-app-stable
      trafficRouting:
        istio:
          virtualService:
            name: my-app-vsvc

---
# 分析模板 - 基于 Prometheus 指标自动判断
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  args:
    - name: service-name
  metrics:
    - name: success-rate
      interval: 1m
      successCondition: result[0] >= 0.99
      failureLimit: 3
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(http_requests_total{
              service="{{args.service-name}}",
              status=~"2.*"
            }[5m])) /
            sum(rate(http_requests_total{
              service="{{args.service-name}}"
            }[5m]))
```

### 6. 流水线设计

#### 6.1 流水线设计原则

```
流水线设计原则：

┌──────────────────────────────────────────────────────────────┐
│                    流水线设计原则                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 快速反馈（Fast Feedback）                                 │
│     • 构建时间 < 10 分钟                                      │
│     • 失败时立即通知                                          │
│     • 分阶段执行（先跑快测试，再跑慢测试）                      │
│                                                              │
│  2. 幂等性（Idempotency）                                     │
│     • 相同输入产生相同输出                                     │
│     • 可重复执行不影响结果                                     │
│     • 无副作用                                                │
│                                                              │
│  3. 最小权限（Least Privilege）                               │
│     • 每个阶段只授予必要的权限                                 │
│     • Secrets 不硬编码                                        │
│     • 使用 OIDC/Workload Identity                            │
│                                                              │
│  4. 可观测性（Observability）                                 │
│     • 每个步骤有明确的状态                                     │
│     • 构建日志完整保留                                         │
│     • 指标采集（构建时间、成功率、频率）                       │
│                                                              │
│  5. 并行执行（Parallelism）                                   │
│     • 无依赖的任务并行执行                                     │
│     • 矩阵构建覆盖多环境                                      │
│     • 合理使用缓存                                            │
│                                                              │
│  6. 故障隔离（Fault Isolation）                               │
│     • 单个任务失败不影响其他任务                               │
│     • 超时机制                                                │
│     • 重试策略                                                │
└──────────────────────────────────────────────────────────────┘
```

#### 6.2 流水线阶段设计

```
标准 CI/CD 流水线阶段：

┌──────────────────────────────────────────────────────────────────────┐
│                    标准 CI/CD 流水线                                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  阶段 1: 代码质量                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐             │ │
│  │ │ Lint │  │Format│  │ SAST │  │ Deps │  │ Vuln │             │ │
│  │ │检查  │  │格式化│  │静态  │  │依赖  │  │漏洞  │             │ │
│  │ │      │  │      │  │扫描  │  │检查  │  │扫描  │             │ │
│  │ └──────┘  └──────┘  └──────┘  └──────┘  └──────┘             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  阶段 2: 构建与测试                                                   │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │ │
│  │ │  编译     │  │ 单元测试  │  │ 集成测试  │  │  E2E 测试 │       │ │
│  │ │  Build   │  │ Unit     │  │  Int     │  │  E2E     │       │ │
│  │ └──────────┘  └──────────┘  └──────────┘  └──────────┘       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  阶段 3: 制品发布                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │ │
│  │ │ Docker   │  │  签名     │  │  推送     │  │ SBOM     │       │ │
│  │ │ Build    │  │  Sign    │  │  Push    │  │ 生成     │       │ │
│  │ └──────────┘  └──────────┘  └──────────┘  └──────────┘       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  阶段 4: 部署                                                        │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │ │
│  │ │ 更新     │  │ ArgoCD   │  │ 健康检查  │  │ 冒烟测试  │       │ │
│  │ │ Manifest │  │ Sync     │  │ Health   │  │ Smoke    │       │ │
│  │ └──────────┘  └──────────┘  └──────────┘  └──────────┘       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  阶段 5: 验证与监控                                                   │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ ┌──────────┐  ┌──────────┐  ┌──────────┐                     │ │
│  │ │ SLO      │  │ 错误率   │  │ 告警     │                     │ │
│  │ │ 验证     │  │ 监控     │  │ 配置     │                     │ │
│  │ └──────────┘  └──────────┘  └──────────┘                     │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

#### 6.3 SRE 流水线最佳实践

```yaml
# 完整的 CI/CD 流水线设计示例（伪代码）
# 展示 SRE 关注的关键点

pipeline:
  name: production-release
  triggers:
    - push: [main]
    - tag: ["v*"]
    - manual: true

  stages:
    # 阶段 1: 代码质量门禁
    - name: quality-gate
      parallel:
        - lint:          # 代码风格检查
            timeout: 5m
            tools: [eslint, prettier, golangci-lint]
        - security-scan: # 安全扫描
            timeout: 10m
            tools: [trivy, snyk, sonarqube]
        - dependency-check: # 依赖漏洞
            timeout: 5m
            tools: [npm-audit, govulncheck]

    # 阶段 2: 测试
    - name: test
      parallel:
        - unit-test:
            timeout: 10m
            coverage-threshold: 80%
        - integration-test:
            timeout: 20m
            services: [postgres, redis]
        - contract-test:
            timeout: 10m
            tool: pact

    # 阶段 3: 构建与发布
    - name: build
      steps:
        - docker-build:
            context: .
            tags: ["${REGISTRY}/${IMAGE}:${SHA}", "${REGISTRY}/${IMAGE}:latest"]
            cache-from: type=gha
            cache-to: type=gha,mode=max
        - sign-image:
            tool: cosign
            key: ${COSIGN_KEY}
        - push-image:
            registry: ${REGISTRY}
        - generate-sbom:
            tool: syft

    # 阶段 4: 部署到 Staging
    - name: deploy-staging
      environment: staging
      steps:
        - update-manifest:
            repo: org/k8s-manifests
            path: apps/my-app/overlays/staging
            field: spec.template.spec.containers[0].image
            value: ${IMAGE_TAG}
        - argocd-sync:
            app: my-app-staging
            wait: true
            timeout: 5m
        - smoke-test:
            url: https://staging.my-app.com
            checks: [health, api, critical-path]

    # 阶段 5: 生产部署（需要审批）
    - name: deploy-production
      environment: production
      approval: true   # SRE 审批门禁
      steps:
        - update-manifest:
            repo: org/k8s-manifests
            path: apps/my-app/overlays/production
            field: spec.template.spec.containers[0].image
            value: ${IMAGE_TAG}
        - argocd-sync:
            app: my-app-production
            strategy: canary   # 金丝雀发布
            wait: true
            timeout: 30m

    # 阶段 6: 部署后验证
    - name: post-deploy
      steps:
        - slo-check:
            window: 15m
            thresholds:
              availability: 99.9%
              latency_p99: 200ms
              error_rate: 0.1%
        - rollback-if-needed:
            condition: slo-check-failed
            action: argocd-rollback
```

---

## 💻 实战练习

### 练习 1：设计 GitOps 工作流

**目标**：为一个微服务应用设计完整的 GitOps 工作流

**步骤**：

1. 创建两个 Git 仓库结构：
   - `app-repo`：应用源代码 + Dockerfile
   - `config-repo`：Kubernetes 清单 + Kustomize overlays

2. 设计分支策略：
   - `main`：生产环境配置
   - `staging`：预发布环境配置
   - `dev`：开发环境配置

3. 编写 Kustomize overlay 结构：
```
config-repo/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── hpa.yaml
├── overlays/
│   ├── dev/
│   │   ├── kustomization.yaml
│   │   └── patch-replicas.yaml
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── patch-replicas.yaml
│   └── production/
│       ├── kustomization.yaml
│       ├── patch-replicas.yaml
│       └── patch-resources.yaml
```

4. 编写 ArgoCD Application 定义，配置自动同步和自我修复

**验证**：模拟一次代码变更，追踪从 commit 到部署的完整流程

### 练习 2：实现金丝雀发布

**目标**：使用 Argo Rollouts 实现金丝雀发布策略

**步骤**：

1. 安装 Argo Rollouts：
```bash
kubectl create namespace argo-rollouts
kubectl apply -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
```

2. 创建 Rollout 资源：
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: demo-app
spec:
  replicas: 4
  selector:
    matchLabels:
      app: demo-app
  template:
    metadata:
      labels:
        app: demo-app
    spec:
      containers:
        - name: demo-app
          image: nginx:1.24
          ports:
            - containerPort: 80
  strategy:
    canary:
      steps:
        - setWeight: 25
        - pause: { duration: 30s }
        - setWeight: 50
        - pause: { duration: 30s }
        - setWeight: 75
        - pause: { duration: 30s }
```

3. 更新镜像触发金丝雀发布：
```bash
kubectl argo rollouts set image demo-app demo-app=nginx:1.25
kubectl argo rollouts get rollout demo-app --watch
```

4. 验证金丝雀发布过程中的流量分配

**验证**：观察 Pod 逐步更新，确认每个阶段的流量比例

### 练习 3：故障排查 - GitOps 同步失败

**场景**：ArgoCD 显示应用 OutOfSync 且同步失败

**排查步骤**：

1. 检查 ArgoCD 应用状态：
```bash
argocd app get my-app
argocd app history my-app
```

2. 查看同步错误详情：
```bash
argocd app sync my-app --dry-run
kubectl logs -n argocd deployment/argocd-application-controller
```

3. 常见原因排查：
   - Git 仓库不可达 → 检查网络和凭证
   - YAML 语法错误 → `kubectl apply --dry-run=client`
   - CRD 不存在 → 检查依赖安装
   - 权限不足 → 检查 ServiceAccount RBAC
   - 资源冲突 → 检查是否有手动修改

4. 修复后验证：
```bash
argocd app sync my-app --force
argocd app wait my-app --health
```

---

## 🎯 面试题精选

### 1. CI 和 CD 的区别是什么？持续交付和持续部署有什么不同？

**参考答案**：
- CI（持续集成）：开发人员频繁将代码合并到主干，每次合并自动触发构建和测试
- CD（持续交付）：CI 的延伸，确保代码随时可部署到生产，但部署到生产需要手动触发
- CD（持续部署）：持续交付的进一步延伸，代码通过所有测试后自动部署到生产，无需人工干预

关键区别：持续交付有"人工审批门禁"，持续部署完全自动化。持续交付适合金融等对风险控制要求高的场景，持续部署适合互联网快速迭代场景。

### 2. 解释 GitOps 的四个原则

**参考答案**：
1. **声明式**：系统期望状态以声明式方式描述（如 K8s YAML），不描述执行步骤
2. **版本化与不可变**：所有配置存储在 Git 中，每次变更有完整审计记录，可回滚到任意版本
3. **自动拉取**：Agent 从 Git 主动拉取期望状态（Pull 模式），而非 CI 系统 Push 部署
4. **持续调谐**：持续对比实际状态与期望状态，发现漂移自动修复

### 3. GitOps 的 Pull 模式相比传统 Push 模式有什么优势？

**参考答案**：
- **安全性**：Agent 在集群内部运行，CI 系统不需要集群凭证
- **审计性**：所有变更记录在 Git 历史中，永久保存
- **可恢复性**：灾难恢复只需 `git clone`
- **漂移检测**：持续调谐机制自动发现和修复配置漂移
- **回滚简便**：`git revert` 即可回滚

### 4. ArgoCD 和 Flux 各自适合什么场景？

**参考答案**：
- **ArgoCD 适合**：需要 Web UI 的团队、多集群管理、需要精细 RBAC、初次接触 GitOps
- **Flux 适合**：偏好纯 Git 工作流、轻量级部署、需要自动镜像更新、与现有 K8s 工具链深度集成

ArgoCD 学习曲线较低（有 UI），Flux 更加 K8s 原生（CRD 驱动）。大型团队推荐 ArgoCD，小型团队或纯 GitOps 场景推荐 Flux。

### 5. 金丝雀发布和蓝绿部署的区别？各自适用什么场景？

**参考答案**：
- **金丝雀发布**：逐步将流量从旧版本转移到新版本（5% → 20% → 50% → 100%），风险最低，但发布周期长。适合关键业务系统、用户量大的服务。
- **蓝绿部署**：同时运行新旧两个完整环境，通过切换流量秒级完成发布，回滚极快，但需要双倍资源。适合无状态服务、需要快速回滚的场景。

### 6. 如何设计一个安全的 CI/CD 流水线？

**参考答案**：
- **Secrets 管理**：使用 Vault 或 CI 平台内置 Secrets，不硬编码
- **最小权限**：每个阶段只授予必要权限，使用 OIDC/Workload Identity
- **供应链安全**：镜像签名（Cosign）、SBOM 生成、依赖漏洞扫描
- **代码扫描**：SAST（静态应用安全测试）、DAST（动态应用安全测试）
- **审计日志**：所有操作可追溯
- **审批门禁**：生产部署需要人工审批

### 7. 什么是错误预算？它如何影响 CI/CD？

**参考答案**：
错误预算 = 1 - SLO 目标。例如 SLO 为 99.9%，则错误预算为 0.1%（每月约 43 分钟）。

当错误预算充足时，可以加快发布频率、尝试新功能。当错误预算紧张时，应降低发布频率、优先修复可靠性问题、增加测试覆盖率。错误预算是 SRE 平衡可靠性与迭代速度的核心机制。

### 8. 如何实现 CI/CD 流水线的可观测性？

**参考答案**：
- **指标**：构建时间、成功率、部署频率、变更前置时间、回滚率
- **日志**：每个步骤的完整日志，结构化存储
- **追踪**：从代码提交到部署的完整链路追踪
- **告警**：构建失败、部署失败、SLO 违规告警
- **仪表盘**：DASHBOARD 展示 DORA 指标

---

## 📚 深入阅读

- [GitOps 原则](https://opengitops.dev/)
- [ArgoCD 官方文档](https://argo-cd.readthedocs.io/)
- [Flux 官方文档](https://fluxcd.io/docs/)
- [Argo Rollouts 文档](https://argoproj.github.io/argo-rollouts/)
- [Google SRE Book - Release Engineering](https://sre.google/sre-book/release-engineering/)
- [DORA 指标](https://dora.dev/)
- [Weaveworks GitOps](https://www.weave.works/technologies/gitops/)

---

## ✅ 自检清单

- [ ] 能清楚区分 CI、持续交付、持续部署三个概念
- [ ] 理解 DevOps 与 SRE 的关系和区别
- [ ] 掌握 GitOps 四原则并能解释每个原则的含义
- [ ] 了解 ArgoCD 和 Flux 的架构差异和适用场景
- [ ] 能描述至少三种部署策略及其优缺点
- [ ] 理解金丝雀发布的实现方式（原生 K8s + Argo Rollouts）
- [ ] 能设计一条包含代码质量门禁的完整 CI/CD 流水线
- [ ] 理解 GitOps Pull 模式相比传统 Push 模式的优势
- [ ] 了解错误预算如何影响发布策略
- [ ] 能排查 GitOps 同步失败的常见原因
