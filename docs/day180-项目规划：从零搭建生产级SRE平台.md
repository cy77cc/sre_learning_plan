# Day 180: 从零搭建生产级 SRE 平台 — 项目概述与架构设计

> 📅 日期：2026-05-03
> 📖 学习主题：Capstone 综合项目规划、架构设计、技术选型、仓库结构、开发环境搭建
> ⏰ 预计学习时间：6-8 小时
> 📋 前置知识：Day 105-119 (AWS), Day 120-129 (Terraform), Day 90-104 (Kubernetes), Day 150-160 (CI/CD), Day 173-179 (SRE 实践)

---

## 🎯 学习目标

完成 Day 180 的学习后，你应该能够：

1. 理解生产级 SRE 平台的完整架构设计
2. 掌握技术选型的决策方法论
3. 设计清晰的仓库结构和模块划分
4. 搭建本地开发环境用于后续实验
5. 制定 7 天 Capstone 项目的详细计划
6. 理解各组件之间的依赖关系和数据流

---

## 📖 核心知识点

### 1. 项目目标与范围

本 Capstone 项目的目标是从零搭建一个生产级 SRE 平台，涵盖 SRE 工程师日常工作的所有核心领域：

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SRE Capstone 项目范围                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Day 180  ──→  项目规划与架构设计                                     │
│  Day 181  ──→  基础设施即代码 (Terraform VPC + EKS)                   │
│  Day 182  ──→  微服务部署 (K8s 资源编排)                               │
│  Day 183  ──→  可观测性栈 (Prometheus + Grafana + Loki + Jaeger)      │
│  Day 184  ──→  CI/CD 流水线 (GitHub Actions + ArgoCD)                │
│  Day 185  ──→  混沌工程 (故障注入与恢复验证)                            │
│  Day 186  ──→  文档化 (架构文档、运维手册、RCA 报告)                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. 整体架构设计

#### 2.1 架构总览

```
                         Internet
                            │
                     ┌──────┴──────┐
                     │  CloudFront │  CDN 加速
                     │   (CDN)     │
                     └──────┬──────┘
                            │
                     ┌──────┴──────┐
                     │  AWS WAF    │  Web 应用防火墙
                     └──────┬──────┘
                            │
                     ┌──────┴──────┐
                     │    ALB      │  应用负载均衡器
                     │ (Ingress)   │
                     └──────┬──────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────┴───────┐  ┌────────┴────────┐  ┌───────┴───────┐
│  Frontend     │  │  API Gateway    │  │  Admin Panel  │
│  (React)      │  │  (Kong/Nginx)   │  │  (React)      │
└───────────────┘  └────────┬────────┘  └───────────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
    ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
    │    User     │  │   Order     │  │  Product    │
    │   Service   │  │   Service   │  │  Service    │
    │  (Go/Python)│  │  (Go/Python)│  │  (Go/Python)│
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │                │
    ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
    │ PostgreSQL  │  │  RabbitMQ   │  │    Redis    │
    │  (RDS)      │  │  (MQ)       │  │(ElastiCache)│
    └─────────────┘  └─────────────┘  └─────────────┘
```

#### 2.2 网络架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        VPC (10.0.0.0/16)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Public Subnets (NAT Gateway)                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ 10.0.1.0/24 │  │ 10.0.2.0/24 │  │ 10.0.3.0/24 │     │   │
│  │  │  us-east-1a │  │  us-east-1b │  │  us-east-1c │     │   │
│  │  │  ALB + NAT  │  │  ALB + NAT  │  │  ALB + NAT  │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Private Subnets (EKS Nodes)                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ 10.0.10.0/24│  │ 10.0.11.0/24│  │ 10.0.12.0/24│     │   │
│  │  │  us-east-1a │  │  us-east-1b │  │  us-east-1c │     │   │
│  │  │  EKS Nodes  │  │  EKS Nodes  │  │  EKS Nodes  │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Database Subnets (RDS)                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ 10.0.20.0/24│  │ 10.0.21.0/24│  │ 10.0.22.0/24│     │   │
│  │  │  us-east-1a │  │  us-east-1b │  │  us-east-1c │     │   │
│  │  │  RDS Primary│  │  RDS Standby│  │  RDS Read   │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3 可观测性架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Observability Stack                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Grafana (Dashboard)                     │   │
│  │    Metrics ←──→ Logs ←──→ Traces (三支柱联动)             │   │
│  └────────┬──────────────┬──────────────┬──────────────────┘   │
│           │              │              │                       │
│  ┌────────┴───────┐ ┌────┴────┐ ┌──────┴──────┐               │
│  │  Prometheus    │ │  Loki   │ │   Jaeger    │               │
│  │  (Metrics)     │ │ (Logs)  │ │  (Traces)   │               │
│  └────────┬───────┘ └────┬────┘ └──────┬──────┘               │
│           │              │              │                       │
│  ┌────────┴───────┐ ┌────┴────┐ ┌──────┴──────┐               │
│  │ AlertManager   │ │Promtail │ │  OTel Coll. │               │
│  │ (Alerting)     │ │(Agents) │ │ (Collectors)│               │
│  └────────────────┘ └─────────┘ └─────────────┘               │
│                                                                 │
│  数据流:                                                        │
│  App → /metrics → Prometheus → AlertManager → Slack/PagerDuty  │
│  App → stdout → Promtail → Loki → Grafana Logs                 │
│  App → OTLP → OTel Collector → Jaeger → Grafana Traces         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.4 CI/CD 流水线架构

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

### 3. 技术选型

#### 3.1 基础设施层

| 组件 | 选型 | 选型理由 |
|------|------|---------|
| 云平台 | AWS | 全球覆盖，EKS 托管 K8s 成熟 |
| IaC 工具 | Terraform | 多云支持，社区生态最大 |
| 容器编排 | Amazon EKS | 托管 K8s，减少运维负担 |
| 网络 | Amazon VPC | 原生集成，安全组灵活 |
| 数据库 | Amazon RDS (PostgreSQL) | 托管服务，自动备份 |
| 缓存 | Amazon ElastiCache (Redis) | 托管 Redis，低延迟 |
| 消息队列 | Amazon SQS / 自建 RabbitMQ | 根据场景选择 |
| CDN | Amazon CloudFront | 全球边缘节点 |
| DNS | Amazon Route 53 | 健康检查 + 故障转移 |

#### 3.2 应用层

| 组件 | 选型 | 选型理由 |
|------|------|---------|
| 前端 | React + Nginx | 成熟生态，SSR 可选 |
| API 网关 | Kong / Nginx Ingress | 插件丰富，性能好 |
| 微服务框架 | Go (Gin) / Python (FastAPI) | Go 高性能，Python 快速开发 |
| ORM | GORM / SQLAlchemy | 成熟稳定 |
| 配置管理 | K8s ConfigMap + Secret | 原生集成 |

#### 3.3 可观测性层

| 组件 | 选型 | 选型理由 |
|------|------|---------|
| 指标 | Prometheus | K8s 原生，PromQL 强大 |
| 可视化 | Grafana | 多数据源支持，Dashboard 丰富 |
| 日志 | Loki + Promtail | 轻量级，与 Grafana 深度集成 |
| 链路追踪 | Jaeger + OpenTelemetry | CNCF 项目，标准协议 |
| 告警 | AlertManager | Prometheus 原生，路由灵活 |

#### 3.4 CI/CD 层

| 组件 | 选型 | 选型理由 |
|------|------|---------|
| CI | GitHub Actions | 与 GitHub 深度集成 |
| CD | ArgoCD | GitOps 标准实现 |
| 镜像仓库 | Amazon ECR | 与 EKS 原生集成 |
| 安全扫描 | Trivy | 容器安全扫描首选 |
| 代码质量 | SonarQube / GitHub CodeQL | 静态分析 |

### 4. 仓库结构设计

```
sre-capstone/
├── README.md
├── docs/
│   ├── architecture.md           # 架构文档
│   ├── runbook.md                # 运维手册
│   └── rca-templates.md          # RCA 报告模板
│
├── infrastructure/               # 基础设施代码
│   ├── terraform/
│   │   ├── modules/
│   │   │   ├── vpc/
│   │   │   │   ├── main.tf
│   │   │   │   ├── variables.tf
│   │   │   │   └── outputs.tf
│   │   │   ├── eks/
│   │   │   │   ├── main.tf
│   │   │   │   ├── variables.tf
│   │   │   │   └── outputs.tf
│   │   │   ├── rds/
│   │   │   │   ├── main.tf
│   │   │   │   ├── variables.tf
│   │   │   │   └── outputs.tf
│   │   │   └── elasticache/
│   │   │       ├── main.tf
│   │   │       ├── variables.tf
│   │   │       └── outputs.tf
│   │   ├── environments/
│   │   │   ├── dev/
│   │   │   │   ├── main.tf
│   │   │   │   ├── variables.tf
│   │   │   │   ├── terraform.tfvars
│   │   │   │   └── backend.tf
│   │   │   ├── staging/
│   │   │   │   ├── main.tf
│   │   │   │   ├── variables.tf
│   │   │   │   ├── terraform.tfvars
│   │   │   │   └── backend.tf
│   │   │   └── prod/
│   │   │       ├── main.tf
│   │   │       ├── variables.tf
│   │   │       ├── terraform.tfvars
│   │   │       └── backend.tf
│   │   └── versions.tf
│   └── helm/
│       ├── prometheus/
│       │   └── values.yaml
│       ├── grafana/
│       │   └── values.yaml
│       ├── loki/
│       │   └── values.yaml
│       └── jaeger/
│           └── values.yaml
│
├── services/                     # 微服务代码
│   ├── user-service/
│   │   ├── Dockerfile
│   │   ├── main.go
│   │   ├── go.mod
│   │   ├── handlers/
│   │   ├── models/
│   │   ├── repository/
│   │   └── tests/
│   ├── order-service/
│   │   ├── Dockerfile
│   │   ├── main.go
│   │   ├── go.mod
│   │   ├── handlers/
│   │   ├── models/
│   │   ├── repository/
│   │   └── tests/
│   └── product-service/
│       ├── Dockerfile
│       ├── main.py
│       ├── requirements.txt
│       ├── app/
│       └── tests/
│
├── k8s/                          # Kubernetes 资源
│   ├── base/
│   │   ├── namespace.yaml
│   │   ├── user-service/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   ├── ingress.yaml
│   │   │   ├── hpa.yaml
│   │   │   ├── pdb.yaml
│   │   │   ├── configmap.yaml
│   │   │   └── secret.yaml
│   │   ├── order-service/
│   │   │   └── ...
│   │   └── product-service/
│   │       └── ...
│   └── overlays/
│       ├── dev/
│       │   └── kustomization.yaml
│       ├── staging/
│       │   └── kustomization.yaml
│       └── prod/
│           └── kustomization.yaml
│
├── observability/                # 可观测性配置
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   ├── rules/
│   │   │   ├── node-alerts.yml
│   │   │   ├── pod-alerts.yml
│   │   │   └── application-alerts.yml
│   │   └── recording-rules.yml
│   ├── grafana/
│   │   ├── dashboards/
│   │   │   ├── cluster-overview.json
│   │   │   ├── node-exporter.json
│   │   │   └── application.json
│   │   └── provisioning/
│   │       ├── datasources.yaml
│   │       └── dashboards.yaml
│   ├── loki/
│   │   └── loki-config.yaml
│   ├── promtail/
│   │   └── promtail-config.yaml
│   └── jaeger/
│       └── jaeger-config.yaml
│
├── ci-cd/                        # CI/CD 配置
│   ├── .github/
│   │   └── workflows/
│   │       ├── ci.yaml
│   │       ├── cd.yaml
│   │       └── security-scan.yaml
│   └── argocd/
│       ├── applications/
│       │   ├── dev.yaml
│       │   ├── staging.yaml
│       │   └── prod.yaml
│       └── project.yaml
│
├── chaos/                        # 混沌工程
│   ├── experiments/
│   │   ├── pod-kill.yaml
│   │   ├── network-delay.yaml
│   │   ├── cpu-stress.yaml
│   │   └── memory-stress.yaml
│   └── scripts/
│       ├── run-experiment.sh
│       └── verify-recovery.sh
│
└── scripts/                      # 工具脚本
    ├── setup-dev.sh              # 开发环境搭建
    ├── deploy.sh                 # 部署脚本
    ├── cleanup.sh                # 清理脚本
    └── health-check.sh           # 健康检查
```

### 5. 开发环境搭建

#### 5.1 前置工具安装

```bash
#!/usr/bin/env bash
# setup-dev.sh - 开发环境搭建脚本
# 用法: chmod +x scripts/setup-dev.sh && ./scripts/setup-dev.sh

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log_info "$1 已安装: $(${1} --version 2>/dev/null || ${1} version 2>/dev/null || echo 'installed')"
        return 0
    else
        log_warn "$1 未安装"
        return 1
    fi
}

# ============================================================
# 1. 检查并安装基础工具
# ============================================================
log_info "=========================================="
log_info "  SRE Capstone 项目 - 开发环境搭建"
log_info "=========================================="

# 检查操作系统
OS="$(uname -s)"
ARCH="$(uname -m)"
log_info "操作系统: ${OS} ${ARCH}"

# ============================================================
# 2. AWS CLI
# ============================================================
if ! check_command aws; then
    log_info "安装 AWS CLI v2..."
    if [[ "${OS}" == "Linux" ]]; then
        curl "https://awscli.amazonaws.com/awscli-exe-linux-${ARCH}.zip" -o "awscliv2.zip"
        unzip -q awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    elif [[ "${OS}" == "Darwin" ]]; then
        curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
        sudo installer -pkg AWSCLIV2.pkg -target /
        rm -f AWSCLIV2.pkg
    fi
fi

# ============================================================
# 3. Terraform
# ============================================================
if ! check_command terraform; then
    log_info "安装 Terraform..."
    TERRAFORM_VERSION="1.7.5"
    if [[ "${OS}" == "Linux" ]]; then
        curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" -o terraform.zip
        unzip -q terraform.zip
        sudo mv terraform /usr/local/bin/
        rm -f terraform.zip
    elif [[ "${OS}" == "Darwin" ]]; then
        brew tap hashicorp/tap
        brew install hashicorp/tap/terraform
    fi
fi

# ============================================================
# 4. kubectl
# ============================================================
if ! check_command kubectl; then
    log_info "安装 kubectl..."
    if [[ "${OS}" == "Linux" ]]; then
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/${ARCH}/kubectl"
        sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
        rm -f kubectl
    elif [[ "${OS}" == "Darwin" ]]; then
        brew install kubectl
    fi
fi

# ============================================================
# 5. Helm
# ============================================================
if ! check_command helm; then
    log_info "安装 Helm..."
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# ============================================================
# 6. Docker
# ============================================================
if ! check_command docker; then
    log_info "Docker 未安装，请手动安装:"
    log_info "  Linux: https://docs.docker.com/engine/install/"
    log_info "  macOS: https://docs.docker.com/desktop/install/mac-install/"
fi

# ============================================================
# 7. ArgoCD CLI
# ============================================================
if ! check_command argocd; then
    log_info "安装 ArgoCD CLI..."
    if [[ "${OS}" == "Linux" ]]; then
        curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-${ARCH}
        sudo install -m 555 argocd /usr/local/bin/argocd
        rm -f argocd
    elif [[ "${OS}" == "Darwin" ]]; then
        brew install argocd
    fi
fi

# ============================================================
# 8. Kustomize
# ============================================================
if ! check_command kustomize; then
    log_info "安装 Kustomize..."
    curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
    sudo mv kustomize /usr/local/bin/
fi

# ============================================================
# 9. Chaos Mesh CLI (chaosctl)
# ============================================================
if ! check_command chaosctl; then
    log_info "Chaos Mesh 将在 Day 185 通过 Helm 安装"
fi

# ============================================================
# 10. Go 开发环境
# ============================================================
if ! check_command go; then
    log_info "安装 Go..."
    GO_VERSION="1.22.2"
    if [[ "${OS}" == "Linux" ]]; then
        curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${ARCH}.tar.gz" | sudo tar -C /usr/local -xz
        echo 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin' >> ~/.bashrc
        export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin
    elif [[ "${OS}" == "Darwin" ]]; then
        brew install go
    fi
fi

# ============================================================
# 11. Python 环境
# ============================================================
if ! check_command python3; then
    log_info "安装 Python 3..."
    if [[ "${OS}" == "Linux" ]]; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
    elif [[ "${OS}" == "Darwin" ]]; then
        brew install python3
    fi
fi

# ============================================================
# 12. 验证安装
# ============================================================
log_info ""
log_info "=========================================="
log_info "  环境验证"
log_info "=========================================="

TOOLS=("aws" "terraform" "kubectl" "helm" "docker" "argocd" "kustomize" "go" "python3")
ALL_OK=true

for tool in "${TOOLS[@]}"; do
    if check_command "${tool}"; then
        :
    else
        ALL_OK=false
    fi
done

if [[ "${ALL_OK}" == "true" ]]; then
    log_info ""
    log_info "所有工具安装完成！可以开始 Capstone 项目。"
else
    log_warn ""
    log_warn "部分工具未安装，请根据上述提示手动安装。"
fi

# ============================================================
# 13. 配置 AWS 凭证
# ============================================================
log_info ""
log_info "=========================================="
log_info "  AWS 凭证配置"
log_info "=========================================="

if aws sts get-caller-identity &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "AWS 账户已配置: ${ACCOUNT_ID}"
else
    log_warn "AWS 凭证未配置，请运行:"
    log_warn "  aws configure"
    log_warn "  或设置环境变量:"
    log_warn "  export AWS_ACCESS_KEY_ID=your-key"
    log_warn "  export AWS_SECRET_ACCESS_KEY=your-secret"
    log_warn "  export AWS_DEFAULT_REGION=us-east-1"
fi

# ============================================================
# 14. 创建项目目录结构
# ============================================================
log_info ""
log_info "=========================================="
log_info "  创建项目目录结构"
log_info "=========================================="

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${PROJECT_ROOT}"

mkdir -p infrastructure/terraform/modules/{vpc,eks,rds,elasticache}
mkdir -p infrastructure/terraform/environments/{dev,staging,prod}
mkdir -p infrastructure/helm/{prometheus,grafana,loki,jaeger}
mkdir -p services/{user-service,order-service,product-service}
mkdir -p k8s/base/{user-service,order-service,product-service}
mkdir -p k8s/overlays/{dev,staging,prod}
mkdir -p observability/{prometheus/rules,grafana/{dashboards,provisioning},loki,promtail,jaeger}
mkdir -p ci-cd/.github/workflows
mkdir -p ci-cd/argocd/applications
mkdir -p chaos/{experiments,scripts}
mkdir -p scripts
mkdir -p docs

log_info "目录结构创建完成"

log_info ""
log_info "=========================================="
log_info "  环境搭建完成！"
log_info "=========================================="
```

### 6. 项目规划与里程碑

#### 6.1 七天计划

```
┌─────────────────────────────────────────────────────────────────┐
│                    Capstone 项目 7 天计划                         │
├────────┬─────────────────────────────────────┬──────────────────┤
│  Day   │  任务                                │  交付物           │
├────────┼─────────────────────────────────────┼──────────────────┤
│  180   │  架构设计 + 环境搭建                   │  架构文档          │
│  181   │  Terraform 基础设施                   │  VPC + EKS 就绪   │
│  182   │  微服务部署                            │  应用可访问        │
│  183   │  可观测性栈                            │  Dashboard 可用   │
│  184   │  CI/CD 流水线                         │  自动化部署生效     │
│  185   │  混沌工程实验                           │  恢复验证通过      │
│  186   │  文档化 + 复盘                         │  完整文档集        │
└────────┴─────────────────────────────────────┴──────────────────┘
```

#### 6.2 每日详细任务

**Day 180 — 项目规划**
- [x] 设计整体架构
- [x] 确定技术选型
- [x] 设计仓库结构
- [x] 搭建开发环境
- [x] 编写架构文档

**Day 181 — 基础设施**
- [ ] 编写 VPC Terraform 模块
- [ ] 编写 EKS Terraform 模块
- [ ] 配置多环境 (dev/staging/prod)
- [ ] 配置 S3 后端状态管理
- [ ] 执行 terraform apply 验证

**Day 182 — 微服务部署**
- [ ] 编写微服务代码骨架
- [ ] 创建 Dockerfile
- [ ] 编写 K8s Deployment/Service
- [ ] 配置 Ingress 路由
- [ ] 配置 HPA 和 PDB
- [ ] 验证服务可访问

**Day 183 — 可观测性**
- [ ] 部署 Prometheus + AlertManager
- [ ] 部署 Grafana + 数据源
- [ ] 部署 Loki + Promtail
- [ ] 部署 Jaeger + OTel Collector
- [ ] 配置告警规则
- [ ] 创建 Dashboard
- [ ] 验证三支柱联动

**Day 184 — CI/CD**
- [ ] 编写 GitHub Actions CI workflow
- [ ] 编写镜像构建和推送 workflow
- [ ] 配置 Trivy 安全扫描
- [ ] 部署 ArgoCD
- [ ] 配置 GitOps 自动同步
- [ ] 验证端到端部署

**Day 185 — 混沌工程**
- [ ] 安装 Chaos Mesh
- [ ] 设计故障场景
- [ ] 执行 Pod Kill 实验
- [ ] 执行网络延迟实验
- [ ] 执行资源压力实验
- [ ] 验证自动恢复
- [ ] 验证告警触发

**Day 186 — 文档化**
- [ ] 完善架构文档
- [ ] 编写运维手册
- [ ] 编写 RCA 报告模板
- [ ] 编写故障处理 Runbook
- [ ] 项目复盘总结

### 7. 成本估算

```
┌─────────────────────────────────────────────────────────────────┐
│                    预估月度成本 (us-east-1)                        │
├──────────────────────┬──────────────────────┬───────────────────┤
│  服务                 │  规格                │  月成本 (USD)      │
├──────────────────────┼──────────────────────┼───────────────────┤
│  EKS Control Plane   │  1 cluster           │  $73              │
│  EC2 (EKS Nodes)     │  3x t3.medium        │  $120             │
│  NAT Gateway         │  1x + 数据传输        │  $45              │
│  ALB                 │  1x + LCU 费用       │  $25              │
│  RDS PostgreSQL      │  db.t3.micro         │  $15              │
│  ElastiCache Redis   │  cache.t3.micro      │  $15              │
│  ECR                 │  存储 + 传输         │  $5               │
│  CloudWatch          │  日志 + 指标         │  $10              │
│  S3 (Terraform 状态)  │  < 1GB              │  $1               │
│  数据传输             │  估算               │  $20              │
├──────────────────────┼──────────────────────┼───────────────────┤
│  总计                 │                      │  ~$329/月         │
└──────────────────────┴──────────────────────┴───────────────────┘

注: 使用 AWS Free Tier 可大幅降低成本
    - EC2: 750 小时/月 (t2.micro, 12 个月)
    - RDS: 750 小时/月 (db.t2.micro, 12 个月)
    - 数据传输: 100GB/月 (12 个月)
```

### 8. SLO 定义

```yaml
# 项目 SLO 定义
slos:
  - name: "API 可用性"
    sli: "成功请求数 / 总请求数"
    slo: "99.9%"
    error_budget: "每月 43.8 分钟"

  - name: "API 延迟"
    sli: "P95 响应时间"
    slo: "< 500ms"
    error_budget: "5% 请求可超过阈值"

  - name: "部署成功率"
    sli: "成功部署数 / 总部署数"
    slo: "99%"
    error_budget: "每月 1 次失败部署"

  - name: "MTTR"
    sli: "从告警到恢复的时间"
    slo: "< 30 分钟"
    error_budget: "不超过 30 分钟"
```

---

## 💻 实战练习

### 练习 1：搭建本地开发环境

**目标**：完成开发环境搭建，确保所有工具可用。

**步骤**：

```bash
# 1. 克隆项目仓库
mkdir -p ~/sre-capstone && cd ~/sre-capstone
git init

# 2. 运行环境搭建脚本
chmod +x scripts/setup-dev.sh
./scripts/setup-dev.sh

# 3. 验证所有工具
echo "=== 工具版本验证 ==="
aws --version
terraform --version
kubectl version --client
helm version
docker --version
argocd version --client
kustomize version
go version
python3 --version

# 4. 配置 AWS 凭证
aws configure
# 输入 Access Key ID
# 输入 Secret Access Key
# 输入 Default region: us-east-1
# 输入 Default output format: json

# 5. 验证 AWS 连接
aws sts get-caller-identity
```

**验证标准**：
- 所有工具版本正确输出
- AWS 身份验证成功
- 项目目录结构创建完成

### 练习 2：绘制架构图

**目标**：使用 Mermaid 或 ASCII 绘制完整的系统架构图。

**步骤**：

```bash
# 1. 创建架构文档
cat > docs/architecture.md << 'DOCEOF'
# SRE Capstone 项目架构文档

## 系统架构

### 网络层
- VPC: 10.0.0.0/16
- 公有子网: 10.0.1-3.0/24 (ALB, NAT Gateway)
- 私有子网: 10.0.10-12.0/24 (EKS Nodes)
- 数据库子网: 10.0.20-22.0/24 (RDS)

### 计算层
- EKS Cluster: v1.29
- Node Group: t3.medium x3 (可扩展到 10)
- 命名空间: default, monitoring, argocd, chaos

### 应用层
- Frontend: React (Nginx)
- API Gateway: Kong
- User Service: Go (Gin)
- Order Service: Go (Gin)
- Product Service: Python (FastAPI)

### 数据层
- PostgreSQL 15 (RDS)
- Redis 7 (ElastiCache)
- RabbitMQ 3.12 (自建)

### 可观测性层
- Metrics: Prometheus
- Logs: Loki + Promtail
- Traces: Jaeger + OTel Collector
- Dashboard: Grafana
- Alerts: AlertManager

### CI/CD 层
- CI: GitHub Actions
- CD: ArgoCD (GitOps)
- Registry: Amazon ECR
- Security: Trivy
DOCEOF

echo "架构文档创建完成"
```

**验证标准**：
- 架构图包含所有组件
- 数据流方向清晰
- 网络分层明确

### 练习 3：编写项目 README

**目标**：编写项目 README 文档，包含项目介绍、架构概览、快速开始等内容。

**步骤**：

```bash
cat > README.md << 'READMEEOF'
# SRE Capstone Project

Production-grade SRE platform built from scratch.

## Architecture

Internet → CloudFront → WAF → ALB → EKS → Microservices

## Components

| Layer | Components |
|-------|-----------|
| Infrastructure | VPC, EKS, RDS, ElastiCache |
| Application | User Service, Order Service, Product Service |
| Observability | Prometheus, Grafana, Loki, Jaeger |
| CI/CD | GitHub Actions, ArgoCD |
| Chaos | Chaos Mesh |

## Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.7
- kubectl >= 1.29
- Helm >= 3.14
- Docker >= 24.0

### Deploy Infrastructure

```bash
cd infrastructure/terraform/environments/dev
terraform init
terraform plan
terraform apply
```

### Deploy Applications

```bash
# Configure kubectl
aws eks update-kubeconfig --name sre-capstone-dev --region us-east-1

# Deploy with Kustomize
kubectl apply -k k8s/overlays/dev/
```

### Deploy Observability Stack

```bash
# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f infrastructure/helm/prometheus/values.yaml

# Install Loki
helm install loki grafana/loki-stack \
  -n monitoring \
  -f infrastructure/helm/loki/values.yaml

# Install Jaeger
helm install jaeger jaegertracing/jaeger \
  -n monitoring \
  -f infrastructure/helm/jaeger/values.yaml
```

### Access Services

```bash
# Grafana
kubectl port-forward svc/grafana 3000:80 -n monitoring

# Jaeger UI
kubectl port-forward svc/jaeger-query 16686:16686 -n monitoring

# Application
kubectl port-forward svc/api-gateway 8080:80
```

## Documentation

- [Architecture](docs/architecture.md)
- [Runbook](docs/runbook.md)
- [RCA Template](docs/rca-templates.md)

## License

MIT
READMEEOF

echo "README 创建完成"
```

**验证标准**：
- README 包含项目简介
- 包含架构概览
- 包含快速开始步骤
- 所有命令可执行

---

## 🎯 面试题精选

### 问题 1：如何设计一个生产级 SRE 平台的架构？

**参考答案**：

生产级 SRE 平台架构设计应遵循以下原则：

1. **分层设计**：基础设施层、应用层、数据层、可观测性层、CI/CD 层各自独立
2. **高可用**：多 AZ 部署，无单点故障
3. **可扩展**：水平扩展优先，使用 HPA 和 Cluster Autoscaler
4. **可观测**：Metrics、Logs、Traces 三支柱完整覆盖
5. **安全性**：网络隔离、最小权限、加密传输
6. **自动化**：IaC 管理基础设施，GitOps 管理应用部署
7. **容错**：熔断、限流、降级策略

### 问题 2：解释 IaC (Infrastructure as Code) 的优势和最佳实践

**参考答案**：

**优势**：
- 版本控制：基础设施变更可追溯
- 可重复：相同代码产生相同环境
- 自动化：减少手动操作错误
- 协作：团队成员可以 Code Review 基础设施变更
- 文档化：代码本身就是文档

**最佳实践**：
- 使用 Terraform 等声明式工具
- 状态文件存储在远程后端 (S3 + DynamoDB Lock)
- 模块化设计，避免代码重复
- 多环境隔离 (dev/staging/prod)
- 变更前执行 plan，人工确认后 apply
- 敏感信息使用 variables + 敏感标记

### 问题 3：如何选择容器编排平台？EKS vs ECS vs 自建 K8s

**参考答案**：

| 维度 | EKS | ECS | 自建 K8s |
|------|-----|-----|---------|
| 运维负担 | 低 (托管控制面) | 最低 | 高 |
| 灵活性 | 高 | 中 | 最高 |
| 生态 | K8s 生态 | AWS 生态 | K8s 生态 |
| 成本 | 控制面 $73/月 | 按需付费 | EC2 成本 |
| 学习曲线 | 中 | 低 | 高 |

**选择建议**：
- 已有 K8s 经验 → EKS
- 纯 AWS 生态 → ECS
- 需要深度定制 → 自建 K8s
- 本项目选择 EKS：平衡运维负担和灵活性

### 问题 4：解释 GitOps 的原理和优势

**参考答案**：

**原理**：
- Git 仓库是唯一真实来源 (Single Source of Truth)
- 声明式配置描述期望状态
- 自动化控制器持续同步实际状态与期望状态
- 所有变更通过 Git PR，可审计可回滚

**优势**：
- 版本控制：所有变更可追溯
- 自动回滚：Git revert 即可回滚
- 安全性：不需要直接访问集群
- 协作：PR Review 流程
- 一致性：所有环境配置一致

### 问题 5：如何估算云资源成本？

**参考答案**：

1. **计算资源**：根据流量估算 CPU/内存需求，选择合适实例类型
2. **存储资源**：数据库存储、对象存储、日志存储
3. **网络资源**：数据传输费、NAT Gateway 费、负载均衡器费
4. **托管服务**：EKS 控制面、RDS 实例费
5. **优化策略**：
   - 使用 Reserved Instances 或 Savings Plans
   - 非生产环境使用 Spot Instances
   - 自动扩缩容避免资源浪费
   - 定期审查闲置资源

### 问题 6：解释 SLO、SLI、SLA 的区别和关系

**参考答案**：

- **SLI (Service Level Indicator)**：服务级别的量化指标，如可用性、延迟
- **SLO (Service Level Objective)**：SLI 的目标值，如 99.9% 可用性
- **SLA (Service Level Agreement)**：与客户签订的服务级别协议，包含违约赔偿

**关系**：
- SLI 是测量值
- SLO 是目标值
- SLA 是商业承诺

**Error Budget**：
- Error Budget = 1 - SLO
- 例如 SLO 99.9%，Error Budget = 0.1% = 每月 43.8 分钟
- Error Budget 用完时，停止功能发布，专注稳定性

### 问题 7：如何设计多环境策略？

**参考答案**：

```
环境策略:
┌─────────┬─────────────┬─────────────┬─────────────┐
│  维度    │    Dev      │   Staging   │    Prod     │
├─────────┼─────────────┼─────────────┼─────────────┤
│  用途    │  开发测试    │  预发布验证   │  生产环境    │
│  规模    │  最小化      │  接近生产    │  完整规模    │
│  数据    │  模拟数据    │  脱敏数据    │  真实数据    │
│  访问    │  开放        │  受限       │  严格控制    │
│  变更    │  自动部署    │  手动审批    │  变更管理    │
│  监控    │  基础        │  完整       │  完整 + 告警 │
└─────────┴─────────────┴─────────────┴─────────────┘
```

### 问题 8：什么是可观测性的三支柱？它们如何协同工作？

**参考答案**：

**三支柱**：
1. **Metrics (指标)**：数值型时间序列数据，用于监控趋势和告警
2. **Logs (日志)**：离散事件记录，用于调试和审计
3. **Traces (链路)**：请求在分布式系统中的完整路径，用于定位性能瓶颈

**协同工作**：
```
告警触发 (Metrics)
    ↓
查看相关日志 (Logs)
    ↓
追踪请求链路 (Traces)
    ↓
定位根因并修复
```

---

## 📚 深入阅读

### 官方文档
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)

### 推荐书籍
- [Site Reliability Engineering](https://sre.google/sre-book/table-of-contents/) - Google SRE Book
- [The Site Reliability Workbook](https://sre.google/workbook/table-of-contents/) - SRE 实践手册
- [Terraform: Up & Running](https://www.terraformupandrunning.com/) - Terraform 权威指南
- [Kubernetes in Action](https://www.manning.com/books/kubernetes-in-action-second-edition) - K8s 实战

### 视频课程
- [AWS re:Invent - EKS Best Practices](https://www.youtube.com/results?search_query=aws+reinvent+eks+best+practices)
- [KubeCon - SRE Practices](https://www.youtube.com/results?search_query=kubecon+sre)
- [HashiConf - Terraform Advanced](https://www.youtube.com/results?search_query=hashiconf+terraform)

---

## ✅ 自检清单

- [ ] 理解生产级 SRE 平台的完整架构
- [ ] 能解释每个技术选型的理由
- [ ] 理解仓库结构的设计原则
- [ ] 开发环境搭建完成，所有工具可用
- [ ] 理解 7 天项目的详细计划
- [ ] 理解各组件之间的依赖关系
- [ ] 能回答 SLO/SLI/SLA 相关面试题
- [ ] 理解 GitOps 的原理和优势
- [ ] 理解可观测性三支柱的协同工作方式
- [ ] 完成 3 个实战练习

---

*由 SRE 学习计划自动生成 | 2026-05-03*
