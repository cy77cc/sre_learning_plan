# Day 114: EKS 弹性 Kubernetes

> 📅 日期：2026-05-03
> 📖 学习主题：EKS 弹性 Kubernetes — EKS 架构、节点组、Fargate、IRSA、Add-ons、监控、日志、费用优化
> ⏰ 预计学习时间：4-5 小时
> 📋 前置知识：Day 105 (AWS 简介), Day 106 (EC2), Day 107 (VPC), Day 100-104 (Kubernetes 基础)

## 🎯 学习目标

- 理解 EKS 的架构设计与控制平面/数据平面分离
- 掌握托管节点组（Managed Node Group）的创建与管理
- 理解 Fargate 与 EC2 节点的选择策略
- 掌握 IRSA（IAM Roles for Service Accounts）的原理与配置
- 能够管理 EKS Add-ons（CoreDNS, kube-proxy, VPC CNI）
- 掌握 EKS 监控与日志方案（CloudWatch Container Insights）
- 能够设计 EKS 费用优化策略

---

## 📖 核心知识点

### 1. EKS 架构概述

EKS（Elastic Kubernetes Service）是 AWS 托管的 Kubernetes 服务，将 K8s 控制平面托管在 AWS 管理的账户中，用户只需管理数据平面（工作节点）。

```
┌──────────────────────────────────────────────────────────────────┐
│                    EKS 架构总览                                    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              AWS 管理的控制平面（Control Plane）                │ │
│  │                                                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │
│  │  │ API      │  │ etcd     │  │ Scheduler│  │Controller│  │ │
│  │  │ Server   │  │ (3 节点)  │  │          │  │ Manager  │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │ │
│  │                                                             │ │
│  │  - 跨 3 个 AZ 部署                                          │ │
│  │  - 自动升级、打补丁                                          │ │
│  │  - 99.95% SLA                                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                          │ ENI                                    │
│                          ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              用户管理的数据平面（Data Plane）                  │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │
│  │  │  AZ-a        │  │  AZ-b        │  │  AZ-c        │     │ │
│  │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │     │ │
│  │  │ │ Node     │ │  │ │ Node     │ │  │ │ Node     │ │     │ │
│  │  │ │ Group    │ │  │ │ Group    │ │  │ │ Group    │ │     │ │
│  │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │     │ │
│  │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │     │ │
│  │  │ │ Fargate  │ │  │ │ Fargate  │ │  │ │ Fargate  │ │     │ │
│  │  │ │ Pod      │ │  │ │ Pod      │ │  │ │ Pod      │ │     │ │
│  │  │ └──────────┘ │  │ └──────────┘ │  │ └──────────┘ │     │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              AWS 服务集成                                     │ │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐            │ │
│  │  │  IAM   │  │  VPC   │  │  ECR   │  │  ELB   │            │ │
│  │  └────────┘  └────────┘  └────────┘  └────────┘            │ │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐            │ │
│  │  │  EBS   │  │  EFS   │  │  S3    │  │CloudWatch│           │ │
│  │  └────────┘  └────────┘  └────────┘  └────────┘            │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### EKS vs 自建 K8s vs ECS

| 特性 | EKS | 自建 K8s | ECS |
|------|-----|---------|-----|
| 控制平面 | AWS 托管 | 自己管理 | AWS 托管 |
| K8s 兼容 | 100% 兼容 | 100% 兼容 | 不兼容 |
| 学习曲线 | 中等 | 高 | 低 |
| 费用 | $0.10/小时 + 节点 | 仅节点费用 | 仅任务费用 |
| 生态系统 | 完整 K8s 生态 | 完整 K8s 生态 | AWS 生态 |
| 适用场景 | 已有 K8s 经验 | 完全控制 | AWS 原生 |
| 升级管理 | AWS 管理 | 自己管理 | AWS 管理 |
| 网络 | VPC CNI | 自选 CNI | awsvpc |

#### EKS 控制平面详解

```
控制平面组件：

API Server：
  - 公有端点：可通过公网访问
  - 私有端点：仅 VPC 内访问
  - 建议：生产环境启用私有端点

etcd：
  - 3 个节点跨 AZ 部署
  - 自动备份
  - 数据持久化

Scheduler：
  - Pod 调度到合适的节点
  - 考虑资源需求、亲和性、污点

Controller Manager：
  - 运行各种控制器
  - 维护集群状态

控制平面费用：
  - $0.10/小时（约 $73/月）
  - 不包含数据平面节点费用
```

### 2. 创建 EKS 集群

#### 使用 eksctl 创建集群

```bash
# 安装 eksctl
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin

# 验证安装
eksctl version

# 创建基础集群（托管节点组）
eksctl create cluster \
  --name my-cluster \
  --version 1.29 \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5 \
  --managed \
  --asg-access \
  --external-dns-access \
  --full-ecr-access \
  --appmesh-access \
  --alb-ingress-access

# 创建多节点组集群
eksctl create cluster \
  --name production-cluster \
  --version 1.29 \
  --region us-east-1 \
  --nodegroup-name general-workers \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed

# 使用配置文件创建集群
cat <<EOF > cluster-config.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: production-cluster
  region: us-east-1
  version: "1.29"

vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: HighlyAvailable

iam:
  withOIDC: true

managedNodeGroups:
  - name: general-workers
    instanceType: m5.large
    minSize: 2
    maxSize: 10
    desiredCapacity: 3
    volumeSize: 100
    volumeType: gp3
    labels:
      role: general
    tags:
      Environment: production
    iam:
      withAddonPolicies:
        autoScaler: true
        cloudWatch: true
        ebs: true

  - name: memory-optimized
    instanceType: r5.xlarge
    minSize: 0
    maxSize: 5
    desiredCapacity: 2
    volumeSize: 100
    labels:
      role: memory-intensive
    taints:
      - key: dedicated
        value: memory-intensive
        effect: NoSchedule

cloudWatch:
  clusterLogging:
    enableTypes:
      - api
      - audit
      - authenticator
      - controllerManager
      - scheduler
EOF

eksctl create cluster -f cluster-config.yaml
```

#### 使用 AWS CLI 创建集群

```bash
# 1. 创建 EKS 集群（控制平面）
aws eks create-cluster \
  --name my-cluster \
  --version 1.29 \
  --role-arn arn:aws:iam::123456789012:role/eks-cluster-role \
  --resources-vpc-config subnetIds=subnet-aaa,subnet-bbb,subnet-ccc,securityGroupIds=sg-12345678 \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# 2. 等待集群创建完成
aws eks wait cluster-active --name my-cluster

# 3. 更新 kubeconfig
aws eks update-kubeconfig --name my-cluster --region us-east-1

# 4. 验证集群连接
kubectl get nodes
kubectl cluster-info

# 5. 创建托管节点组
aws eks create-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name standard-workers \
  --node-role arn:aws:iam::123456789012:role/eks-node-role \
  --subnets subnet-aaa subnet-bbb subnet-ccc \
  --instance-types t3.medium \
  --scaling-config minSize=2,maxSize=5,desiredSize=3 \
  --disk-size 100 \
  --ami-type AL2_x86_64 \
  --capacity-type ON_DEMAND

# 6. 等待节点组创建完成
aws eks wait nodegroup-active \
  --cluster-name my-cluster \
  --nodegroup-name standard-workers
```

### 3. 节点组（Node Groups）

#### 托管节点组 vs 自管理节点组

```
┌──────────────────────────────────────────────────────────────┐
│              节点组类型对比                                     │
│                                                               │
│  托管节点组（Managed Node Group）                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AWS 自动管理：                                       │    │
│  │  - 节点生命周期（创建、更新、销毁）                     │    │
│  │  - AMI 自动更新                                       │    │
│  │  - K8s 版本升级                                       │    │
│  │  - Auto Scaling                                      │    │
│  │  - 节点自动修复                                       │    │
│  │  - 与 EBS/EFS 集成                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  自管理节点组（Self-Managed Node Group）                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  用户自行管理：                                       │    │
│  │  - 使用 CloudFormation 或 Launch Template            │    │
│  │  - 需要手动更新 AMI                                   │    │
│  │  - 需要手动配置 kubelet                               │    │
│  │  - 更灵活的自定义选项                                  │    │
│  │  - 需要手动加入集群                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  Fargate                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  无服务器：                                           │    │
│  │  - 无需管理节点                                        │    │
│  │  - Pod 级别资源隔离                                    │    │
│  │  - 按 Pod 资源付费                                    │    │
│  │  - 启动延迟较高                                        │    │
│  │  - 不支持 DaemonSet                                   │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 节点组管理

```bash
# 列出节点组
aws eks list-nodegroups --cluster-name my-cluster

# 获取节点组详情
aws eks describe-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name standard-workers

# 更新节点组（扩缩容）
aws eks update-nodegroup-config \
  --cluster-name my-cluster \
  --nodegroup-name standard-workers \
  --scaling-config minSize=3,maxSize=10,desiredSize=5

# 更新节点组版本
aws eks update-nodegroup-version \
  --cluster-name my-cluster \
  --nodegroup-name standard-workers

# 删除节点组
aws eks delete-nodegroup \
  --cluster-name my-cluster \
  --nodegroup-name standard-workers

# 节点组标签管理
aws eks tag-resource \
  --resource-arn arn:aws:eks:us-east-1:123456789012:nodegroup/my-cluster/standard-workers/abc123 \
  --tags Environment=production,Team=sre
```

#### 节点组配置最佳实践

```yaml
# eksctl 配置文件中的节点组配置
managedNodeGroups:
  # 通用工作负载
  - name: general-purpose
    instanceType: m5.large
    minSize: 2
    maxSize: 20
    desiredCapacity: 3
    volumeSize: 100
    volumeType: gp3
    volumeIOPS: 3000
    volumeThroughput: 125
    labels:
      workload: general
    tags:
      Environment: production
    # 使用 Spot 实例降低成本
    spot: false
    # 启用 EBS 加密
    ebsOptimized: true
    iam:
      withAddonPolicies:
        autoScaler: true
        cloudWatch: true
        ebs: true
        efs: true

  # 计算密集型工作负载
  - name: compute-optimized
    instanceType: c5.2xlarge
    minSize: 0
    maxSize: 10
    desiredCapacity: 2
    volumeSize: 100
    labels:
      workload: compute
    taints:
      - key: dedicated
        value: compute
        effect: NoSchedule

  # Spot 实例节点组
  - name: spot-workers
    instanceTypes:
      - m5.large
      - m5.xlarge
      - m5a.large
      - m5a.xlarge
    minSize: 0
    maxSize: 20
    desiredCapacity: 5
    spot: true
    labels:
      lifecycle: spot
    taints:
      - key: spot
        value: "true"
        effect: PreferNoSchedule
```

### 4. Fargate 配置

#### Fargate Profile

```bash
# 创建 Fargate Profile
aws eks create-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile \
  --pod-execution-role-arn arn:aws:iam::123456789012:role/eks-fargate-role \
  --subnets subnet-aaa subnet-bbb subnet-ccc \
  --selectors '[
    {
      "namespace": "fargate-namespace",
      "labels": {
        "compute": "fargate"
      }
    }
  ]' \
  --tags Environment=production

# 使用 eksctl 创建 Fargate Profile
eksctl create fargateprofile \
  --cluster my-cluster \
  --name my-fargate-profile \
  --namespace fargate-namespace

# 列出 Fargate Profiles
aws eks list-fargate-profiles --cluster-name my-cluster

# 删除 Fargate Profile
aws eks delete-fargate-profile \
  --cluster-name my-cluster \
  --fargate-profile-name my-fargate-profile
```

#### Fargate vs EC2 节点选择

| 特性 | Fargate | EC2 节点 |
|------|---------|---------|
| 节点管理 | 无服务器 | 需要管理 |
| 启动时间 | 30-60 秒 | 2-5 分钟 |
| 最小计费 | 1 vCPU / 2GB | 按实例计费 |
| Pod 密度 | 低 | 高 |
| DaemonSet | 不支持 | 支持 |
| GPU 支持 | 不支持 | 支持 |
| 适用场景 | 突发负载、批处理 | 稳定负载、高性能 |
| 费用模式 | 按 Pod 资源 | 按实例 |

```
选择决策树：

工作负载特征？
├── 突发性/不可预测 ──> Fargate
├── 稳定/可预测 ──> EC2 节点组
├── 需要 GPU ──> EC2（GPU 实例）
├── 需要 DaemonSet ──> EC2
├── 延迟敏感 ──> EC2（预热节点）
└── 批处理 ──> Fargate（无需管理节点）

混合策略：
- 核心服务：EC2 节点组（稳定、低成本）
- 突发任务：Fargate（弹性、无管理）
- CI/CD Job：Fargate（按需创建）
```

### 5. IRSA（IAM Roles for Service Accounts）

#### IRSA 原理

```
┌──────────────────────────────────────────────────────────────┐
│                    IRSA 工作原理                               │
│                                                               │
│  1. EKS 集群启用 OIDC Provider                               │
│     │                                                        │
│     ▼                                                        │
│  2. 创建 IAM Role，配置 Trust Policy                         │
│     {                                                         │
│       "Condition": {                                          │
│         "StringEquals": {                                     │
│           "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLED539...:sub": |
│             "system:serviceaccount:default:my-sa"             │
│         }                                                     │
│       }                                                       │
│     }                                                         │
│     │                                                        │
│     ▼                                                        │
│  3. 创建 ServiceAccount，关联 IAM Role                        │
│     apiVersion: v1                                            │
│     kind: ServiceAccount                                      │
│     metadata:                                                 │
│       annotations:                                            │
│         eks.amazonaws.com/role-arn: arn:aws:iam::123:role/my-role |
│     │                                                        │
│     ▼                                                        │
│  4. Pod 使用该 ServiceAccount                                │
│     - 自动挂载 STS 临时凭证                                   │
│     - 凭证通过 projected volume 挂载                         │
│     - 自动轮换，无需管理                                      │
└──────────────────────────────────────────────────────────────┘
```

#### IRSA 配置步骤

```bash
# 1. 获取集群 OIDC Provider URL
OIDC_URL=$(aws eks describe-cluster --name my-cluster \
  --query "cluster.identity.oidc.issuer" --output text)
echo $OIDC_URL

# 2. 创建 IAM Role
cat <<EOF > trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/${OIDC_URL#https://}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_URL#https://}:sub": "system:serviceaccount:default:my-sa",
          "${OIDC_URL#https://}:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name my-eks-role \
  --assume-role-policy-document file://trust-policy.json

# 3. 附加权限策略
aws iam attach-role-policy \
  --role-name my-eks-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# 4. 创建 ServiceAccount
cat <<EOF > sa.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-sa
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-eks-role
EOF

kubectl apply -f sa.yaml

# 5. 创建使用该 SA 的 Pod
cat <<EOF > pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: test-irsa
spec:
  serviceAccountName: my-sa
  containers:
  - name: aws-cli
    image: amazon/aws-cli
    command: ["sleep", "3600"]
EOF

kubectl apply -f pod.yaml

# 6. 验证 IRSA 工作
kubectl exec test-irsa -- aws sts get-caller-identity
# 应该返回 Role ARN，而不是 Node 的 IAM Role
```

#### 使用 eksctl 简化 IRSA 配置

```bash
# 使用 eksctl 创建 IRSA
eksctl create iamserviceaccount \
  --name my-sa \
  --namespace default \
  --cluster my-cluster \
  --role-name my-eks-role \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve

# 验证
kubectl get sa my-sa -o yaml
```

### 6. EKS Add-ons

#### 核心 Add-ons

```
┌──────────────────────────────────────────────────────────────┐
│                    EKS 核心 Add-ons                           │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  VPC CNI Plugin                                      │    │
│  │  - 为 Pod 分配 VPC 私有 IP                            │    │
│  │  - 支持 ENI 直连模式                                  │    │
│  │  - 支持 Prefix Delegation（增加 IP 数量）             │    │
│  │  - 默认每个 ENI 可分配 IP 数量取决于实例类型            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  CoreDNS                                             │    │
│  │  - 集群内部 DNS 解析                                  │    │
│  │  - 服务发现                                          │    │
│  │  - Pod 域名解析                                       │    │
│  │  - 支持 NodeLocal DNSCache 优化                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  kube-proxy                                          │    │
│  │  - Service 网络代理                                   │    │
│  │  - iptables/IPVS 模式                                │    │
│  │  - 负载均衡                                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Amazon VPC CNI Metrics Helper                       │    │
│  │  - VPC CNI 指标导出到 CloudWatch                      │    │
│  │  - IP 地址使用情况监控                                │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### Add-on 管理

```bash
# 列出可用 Add-ons
aws eks list-addons --cluster-name my-cluster

# 安装 Add-on
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.16.0-eksbuild.1 \
  --resolve-conflicts OVERWRITE

# 更新 Add-on
aws eks update-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --addon-version v1.17.0-eksbuild.1 \
  --resolve-conflicts OVERWRITE

# 删除 Add-on
aws eks delete-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni

# 获取 Add-on 详情
aws eks describe-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni

# 配置 VPC CNI Prefix Delegation
# 增加每个节点可用的 IP 数量
kubectl set env daemonset aws-node \
  -n kube-system \
  ENABLE_PREFIX_DELEGATION=true

# 查看节点 IP 使用情况
kubectl get nodes -o custom-columns=\
'NAME:.metadata.name,PODS:.status.capacity.pods,ALLOCATABLE_PODS:.status.allocatable.pods'
```

### 7. EKS 网络

#### VPC CNI 网络模式

```
┌──────────────────────────────────────────────────────────────┐
│                    VPC CNI 网络模式                            │
│                                                               │
│  模式 1：ENI 模式（默认）                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  EC2 实例                                             │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ ENI 1 (主)     ENI 2        ENI 3            │  │    │
│  │  │ IP: 10.0.1.10  IP: 10.0.1.11  IP: 10.0.1.12 │  │    │
│  │  │  │               │              │             │  │    │
│  │  │  ▼               ▼              ▼             │  │    │
│  │  │ Pod A          Pod B         Pod C           │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  - 每个 Pod 获得 VPC 私有 IP                        │    │
│  │  - Pod 直接使用 VPC 路由                             │    │
│  │  - IP 数量受限于实例类型                              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  模式 2：Prefix Delegation 模式                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  EC2 实例                                             │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ ENI 1                                          │  │    │
│  │  │ IP Prefix: 10.0.1.0/28 (16 个 IP)             │  │    │
│  │  │  │  │  │  │  ...                               │  │    │
│  │  │  ▼  ▼  ▼  ▼                                    │  │    │
│  │  │ P1 P2 P3 P4 ... P16                           │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  - 每个 ENI 分配 IP 前缀（/28 = 16 个 IP）           │    │
│  │  - 大幅增加每个节点的 Pod 密度                        │    │
│  │  - 减少 ENI 创建开销                                 │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### Service 类型

```yaml
# ClusterIP Service（集群内部访问）
apiVersion: v1
kind: Service
metadata:
  name: my-service
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080

---
# NodePort Service（节点端口访问）
apiVersion: v1
kind: Service
metadata:
  name: my-service-nodeport
spec:
  type: NodePort
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
    nodePort: 30080

---
# LoadBalancer Service（AWS NLB/ALB）
apiVersion: v1
kind: Service
metadata:
  name: my-service-lb
  annotations:
    # 使用 NLB
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
  - port: 80
    targetPort: 8080
```

#### AWS Load Balancer Controller

```bash
# 安装 AWS Load Balancer Controller
eksctl create iamserviceaccount \
  --cluster=my-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# 使用 Helm 安装
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=my-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

```yaml
# Ingress 资源配置
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/abc123
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: "443"
    alb.ingress.kubernetes.io/healthcheck-path: /health
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-service
            port:
              number: 80
```

### 8. EKS 监控与日志

#### CloudWatch Container Insights

```bash
# 安装 CloudWatch Agent 和 Fluent Bit
# 使用 Helm 安装
helm repo add amazon-cloudwatch https://aws.github.io/aws-eks-charts

# 安装 CloudWatch Agent
helm install amazon-cloudwatch-metrics amazon-cloudwatch/amazon-cloudwatch-metrics \
  --namespace amazon-cloudwatch \
  --create-namespace \
  --set clusterName=my-cluster \
  --set region=us-east-1

# 安装 Fluent Bit
helm install aws-for-fluent-bit eks/aws-for-fluent-bit \
  --namespace amazon-cloudwatch \
  --set cloudWatch.enabled=true \
  --set cloudWatch.logGroupName=/aws/eks/my-cluster \
  --set cloudWatch.region=us-east-1
```

#### 启用 EKS 控制平面日志

```bash
# 启用控制平面日志
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# 验证日志配置
aws eks describe-cluster --name my-cluster \
  --query "cluster.logging"
```

#### Prometheus + Grafana 监控

```bash
# 安装 kube-prometheus-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm install kube-prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.enabled=true \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

# 访问 Grafana
kubectl port-forward svc/kube-prometheus-grafana 3000:80 -n monitoring
```

### 9. EKS 费用优化

```
┌──────────────────────────────────────────────────────────────┐
│                    EKS 费用优化策略                            │
│                                                               │
│  1. 控制平面费用                                              │
│     - 固定 $0.10/小时（$73/月）                               │
│     - 无法优化，但可以合并集群                                  │
│                                                               │
│  2. 节点费用优化                                              │
│     ┌─────────────────────────────────────────────────────┐ │
│     │  策略                    节省比例    适用场景          │ │
│     │  ─────────────────────────────────────────────────  │ │
│     │  Spot 实例               60-90%     无状态工作负载    │ │
│     │  Reserved Instances      30-72%     稳定工作负载     │ │
│     │  Savings Plans           20-72%     灵活消费         │ │
│     │  Graviton (ARM)          20%        兼容 ARM 的应用  │ │
│     │  Right-sizing            20-50%     资源过度分配     │ │
│     │  Autoscaling             30-50%     弹性工作负载     │ │
│     └─────────────────────────────────────────────────────┘ │
│                                                               │
│  3. Fargate 费用优化                                          │
│     - 仅用于突发性工作负载                                     │
│     - 稳定负载使用 EC2 更划算                                  │
│                                                               │
│  4. 存储费用优化                                              │
│     - 使用 gp3 替代 gp2                                      │
│     - EBS 快照生命周期策略                                    │
│     - EFS 智能分层                                            │
└──────────────────────────────────────────────────────────────┘
```

#### Cluster Autoscaler 配置

```yaml
# Cluster Autoscaler 部署
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - image: registry.k8s.io/autoscaling/cluster-autoscaler:v1.29.0
        name: cluster-autoscaler
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
```

#### Karpenter（推荐的替代方案）

```bash
# 安装 Karpenter
helm repo add karpenter https://charts.karpenter.sh

helm install karpenter karpenter/karpenter \
  --namespace karpenter \
  --create-namespace \
  --set settings.aws.clusterName=my-cluster \
  --set settings.aws.defaultInstanceProfile=KarpenterNodeInstanceProfile \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::123456789012:role/karpenter-role
```

```yaml
# Karpenter NodePool 配置
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["m5.large", "m5.xlarge", "m5.2xlarge", "m5a.large", "m5a.xlarge"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
      nodeClassRef:
        name: default
  limits:
    cpu: "1000"
    memory: 2000Gi
  disruption:
    consolidationPolicy: WhenUnderutilized
    expireAfter: 720h
---
apiVersion: karpenter.k8s.aws/v1beta1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: AL2
  subnetSelector:
    karpenter.sh/discovery: my-cluster
  securityGroupSelector:
    karpenter.sh/discovery: my-cluster
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
```

### 10. SRE 实战案例

#### 场景：生产级 EKS 集群架构

```
┌──────────────────────────────────────────────────────────────┐
│              生产级 EKS 集群架构                               │
│                                                               │
│  网络层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  VPC (10.0.0.0/16)                                   │    │
│  │  ├── Public Subnet (10.0.1.0/24, 10.0.2.0/24)       │    │
│  │  │   └── ALB/NLB                                     │    │
│  │  └── Private Subnet (10.0.10.0/24, 10.0.11.0/24)    │    │
│  │      └── EKS Nodes & Pods                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  集群层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  EKS Cluster (v1.29)                                  │    │
│  │  ├── Control Plane (AWS 管理, 3 AZ)                  │    │
│  │  ├── Node Group: general (m5.large, 3-10 节点)       │    │
│  │  ├── Node Group: compute (c5.xlarge, 0-5 节点)       │    │
│  │  └── Fargate Profile: batch-jobs                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  应用层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ├── AWS Load Balancer Controller                     │    │
│  │  ├── CoreDNS                                          │    │
│  │  ├── Cluster Autoscaler / Karpenter                   │    │
│  │  ├── CloudWatch Agent + Fluent Bit                    │    │
│  │  └── Prometheus + Grafana                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  安全层                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  ├── IRSA (IAM Roles for Service Accounts)            │    │
│  │  ├── Network Policy (Calico)                          │    │
│  │  ├── Pod Security Standards                           │    │
│  │  ├── Secret Management (Secrets Manager / Sealed)     │    │
│  │  └── Image Scanning (ECR)                             │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### 故障排查链路

```
EKS 故障排查流程：

1. Pod 无法启动（Pending）
   → kubectl describe pod <pod-name>
   → 检查 Events 部分
   → 常见原因：
     - 资源不足：Insufficient cpu/memory
     - 节点选择器不匹配：No nodes match selector
     - 污点容忍：Taint toleration missing
     - PVC 未绑定：PersistentVolumeClaim not found

2. Pod 崩溃（CrashLoopBackOff）
   → kubectl logs <pod-name> --previous
   → 检查应用日志
   → 常见原因：
     - 启动失败：配置错误、依赖不可用
     - OOM Killed：内存限制过低
     - 健康检查失败：Liveness/Readiness probe

3. Service 无法访问
   → kubectl get endpoints <service-name>
   → 检查 Selector 是否匹配
   → 检查 Network Policy
   → 检查 CoreDNS 解析：kubectl run debug --image=busybox -- nslookup my-service

4. 节点问题
   → kubectl describe node <node-name>
   → 检查 Conditions：Ready, MemoryPressure, DiskPressure
   → 检查系统日志：journalctl -u kubelet
   → 检查 AWS 实例状态：aws ec2 describe-instance-status

5. 网络问题
   → 检查 VPC CNI 日志：kubectl logs -n kube-system ds/aws-node
   → 检查 IP 地址分配：aws eks describe-cluster --query "cluster.resourcesVpcConfig"
   → 检查安全组规则
   → 检查路由表
```

---

## 💻 实战练习

### 练习 1：基础操作 — EKS 集群管理

**目标**：使用 eksctl 创建集群、部署应用、验证连接

```bash
# 步骤 1：创建 EKS 集群
eksctl create cluster \
  --name sre-lab-cluster \
  --version 1.29 \
  --region us-east-1 \
  --nodegroup-name lab-workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed

# 步骤 2：验证集群
kubectl get nodes
kubectl cluster-info

# 步骤 3：部署测试应用
kubectl create deployment nginx --image=nginx:latest
kubectl expose deployment nginx --port=80 --type=LoadBalancer

# 步骤 4：验证应用
kubectl get pods
kubectl get svc nginx

# 步骤 5：查看应用日志
kubectl logs -l app=nginx

# 清理
kubectl delete svc nginx
kubectl delete deployment nginx
eksctl delete cluster --name sre-lab-cluster
```

### 练习 2：进阶场景 — IRSA 配置

**目标**：配置 IRSA，让 Pod 使用特定的 IAM Role 访问 AWS 服务

```bash
# 步骤 1：获取 OIDC Provider
OIDC_ID=$(aws eks describe-cluster --name sre-lab-cluster \
  --query "cluster.identity.oidc.issuer" --output text | cut -d '/' -f 5)
echo "OIDC ID: $OIDC_ID"

# 步骤 2：创建 IAM Policy
cat <<EOF > s3-read-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ]
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name S3ReadOnlyPolicy \
  --policy-document file://s3-read-policy.json

# 步骤 3：使用 eksctl 创建 IRSA
eksctl create iamserviceaccount \
  --name s3-reader-sa \
  --namespace default \
  --cluster sre-lab-cluster \
  --role-name S3ReaderRole \
  --attach-policy-arn arn:aws:iam::123456789012:policy/S3ReadOnlyPolicy \
  --approve

# 步骤 4：验证 ServiceAccount
kubectl get sa s3-reader-sa -o yaml

# 步骤 5：部署使用 IRSA 的 Pod
kubectl run aws-cli --image=amazon/aws-cli \
  --serviceaccount=s3-reader-sa \
  --command -- sleep 3600

# 步骤 6：验证 IRSA
kubectl exec aws-cli -- aws sts get-caller-identity

# 清理
kubectl delete pod aws-cli
eksctl delete iamserviceaccount --name s3-reader-sa --cluster sre-lab-cluster
```

### 练习 3：故障排查挑战 — Pod 启动问题

**场景**：Pod 卡在 Pending 或 CrashLoopBackOff 状态

```bash
# 步骤 1：创建一个有问题的 Deployment
cat <<EOF > bad-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bad-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: bad-app
  template:
    metadata:
      labels:
        app: bad-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        resources:
          requests:
            memory: "64Gi"
            cpu: "64"
        readinessProbe:
          httpGet:
            path: /nonexistent
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
EOF

kubectl apply -f bad-deployment.yaml

# 步骤 2：检查 Pod 状态
kubectl get pods -l app=bad-app

# 步骤 3：诊断问题
kubectl describe pod -l app=bad-app

# 步骤 4：修复问题
# 修改资源请求和健康检查路径
kubectl delete -f bad-deployment.yaml

cat <<EOF > good-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: good-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: good-app
  template:
    metadata:
      labels:
        app: good-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
EOF

kubectl apply -f good-deployment.yaml

# 步骤 5：验证修复
kubectl get pods -l app=good-app

# 清理
kubectl delete -f good-deployment.yaml
```

---

## 🎯 面试题精选

### Q1: EKS 的控制平面和数据平面分别包含哪些组件？

**答案**：
- **控制平面**（AWS 管理）：API Server、etcd（3 节点跨 AZ）、Scheduler、Controller Manager
- **数据平面**（用户管理）：Worker Nodes（EC2 或 Fargate）、kubelet、kube-proxy、Container Runtime

### Q2: IRSA 的工作原理是什么？

**答案**：
1. EKS 集群启用 OIDC Provider
2. 创建 IAM Role，Trust Policy 配置 OIDC 条件
3. 创建 ServiceAccount，annotated 关联 IAM Role
4. Pod 使用该 ServiceAccount，自动挂载 STS 临时凭证
5. 凭证通过 projected volume 挂载，自动轮换

### Q3: Fargate 和 EC2 节点组各自的优势是什么？如何选择？

**答案**：
- **Fargate**：无服务器、无需管理节点、按 Pod 计费、适合突发负载
- **EC2**：成本更低（稳定负载）、支持 DaemonSet、支持 GPU、更高的 Pod 密度
- **选择**：稳定负载用 EC2，突发/批处理用 Fargate，混合使用

### Q4: 如何优化 EKS 集群的网络性能？

**答案**：
1. 启用 VPC CNI Prefix Delegation，增加每个节点的 IP 数量
2. 使用 NodeLocal DNSCache 减少 CoreDNS 压力
3. 配置 Pod 反亲和性，分散到不同节点/AZ
4. 使用 NLB 替代 ALB（如果不需要 L7 路由）
5. 启用 VPC Flow Logs 监控网络流量

### Q5: 如何实现 EKS 集群的自动扩缩容？

**答案**：
- **Cluster Autoscaler**：根据 Pod 调度需求自动增减节点
- **Karpenter**（推荐）：更智能的节点供应，支持多种实例类型和 Spot
- **HPA**：根据 CPU/内存/自定义指标自动调整 Pod 副本数
- **VPA**：自动调整 Pod 的资源请求

### Q6: EKS 升级的最佳实践是什么？

**答案**：
1. 先升级控制平面，再升级数据平面
2. 一次只升级一个小版本（如 1.28 → 1.29）
3. 在测试环境验证后再升级生产
4. 使用蓝绿部署方式升级节点组
5. 检查 Add-ons 兼容性
6. 更新 IRSA 和 RBAC 配置

### Q7: 如何监控 EKS 集群的健康状态？

**答案**：
- **CloudWatch Container Insights**：节点、Pod、容器级别指标
- **Prometheus + Grafana**：自定义指标和仪表盘
- **EKS 控制平面日志**：API Server、Audit、Authenticator 日志
- **Fluent Bit**：应用日志收集到 CloudWatch Logs
- **X-Ray**：分布式追踪

### Q8: 如何保护 EKS 集群的安全？

**答案**：
1. 使用 IRSA 而非节点 IAM Role
2. 启用 Pod Security Standards
3. 配置 Network Policy 限制 Pod 间通信
4. 使用 ECR 镜像扫描
5. 启用 Secrets Manager 或 Sealed Secrets
6. 定期更新 K8s 版本和 Add-ons
7. 启用审计日志

---

## 📚 深入阅读

- [EKS 官方文档](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [EKS 最佳实践](https://aws.github.io/aws-eks-best-practices/)
- [EKS 费用优化](https://aws.amazon.com/blogs/containers/cost-optimization-best-practices-for-amazon-eks/)
- [Karpenter 文档](https://karpenter.sh/docs/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)

---

## ✅ 自检清单

- [ ] 能够使用 eksctl 创建和管理 EKS 集群
- [ ] 理解托管节点组、自管理节点组和 Fargate 的区别
- [ ] 能够配置 IRSA 让 Pod 使用特定的 IAM Role
- [ ] 能够管理 EKS Add-ons（VPC CNI, CoreDNS, kube-proxy）
- [ ] 能够部署 AWS Load Balancer Controller
- [ ] 能够配置 CloudWatch Container Insights 监控
- [ ] 理解 EKS 费用优化策略（Spot, Reserved, Graviton, Karpenter）
- [ ] 能够排查常见的 EKS 问题（Pod Pending, CrashLoopBackOff）
